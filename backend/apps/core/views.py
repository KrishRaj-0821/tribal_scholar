import logging
from django.db import connection
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

logger = logging.getLogger('apps.core')


class HealthLiveView(APIView):
    """
    Liveness probe: returns 200 if the WSGI/ASGI application process is responsive.
    Does not inspect downstream dependencies.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "service": "tribal-scholar-api"
            },
            status=status.HTTP_200_OK
        )


class HealthReadyView(APIView):
    """
    Production readiness probe: verifies connectivity to all required platform dependencies:
    - DATABASE: PostgreSQL relational store for schemes, users, workflows, and audit trails.
    - REDIS: High-performance message broker and cache layer.
    - CELERY: Distributed worker fleet for asynchronous OCR and document intelligence.
    - OBJECT_STORAGE: S3-compatible multi-tier storage separating quarantine and safe documents.
    - CLAMAV: Anti-malware daemon protecting applicant uploads from viruses/EICAR payloads.

    Never exposes internal hostnames, ports, credentials, bucket names, or stack traces.
    Returns 200 when ready, 503 when degraded.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        is_ready = True
        components = {
            "database": "unknown",
            "redis": "unknown",
            "celery": "unknown",
            "object_storage": "unknown",
            "clamav": "unknown",
        }

        # 1. Database check
        try:
            connection.ensure_connection()
            components["database"] = "connected"
        except Exception as db_exc:
            logger.error(f"Readiness database probe failed: {db_exc}")
            components["database"] = "unavailable"
            is_ready = False

        # 2. Redis check
        redis_url = getattr(settings, 'REDIS_URL', None) or getattr(settings, 'CELERY_BROKER_URL', None)
        if redis_url:
            try:
                import redis
                client = redis.from_url(redis_url, socket_timeout=2.0)
                if client.ping():
                    components["redis"] = "connected"
                else:
                    components["redis"] = "unresponsive"
                    is_ready = False
            except Exception as redis_exc:
                logger.error(f"Readiness Redis probe failed: {redis_exc}")
                components["redis"] = "unavailable"
                is_ready = False
        else:
            components["redis"] = "not_configured"
            is_ready = False

        # 3. Celery worker check
        try:
            from tribel_scholar.celery import app as celery_app
            ping_responses = celery_app.control.ping(timeout=1.5)
            if ping_responses:
                components["celery"] = "connected"
            else:
                logger.warning("Readiness Celery probe: No active workers responded to ping.")
                components["celery"] = "unresponsive"
                is_ready = False
        except Exception as celery_exc:
            logger.error(f"Readiness Celery probe failed: {celery_exc}")
            components["celery"] = "unavailable"
            is_ready = False

        # 4. Object storage check
        try:
            from apps.documents.storage import get_object_storage, S3CompatibleObjectStorage, LocalObjectStorage
            storage = get_object_storage()
            if isinstance(storage, S3CompatibleObjectStorage):
                storage.client.head_bucket(Bucket=storage.bucket_name)
                components["object_storage"] = "connected"
            elif isinstance(storage, LocalObjectStorage):
                if storage.quarantine_dir.exists() and storage.safe_dir.exists():
                    components["object_storage"] = "connected"
                else:
                    components["object_storage"] = "degraded"
                    is_ready = False
            else:
                components["object_storage"] = "connected"
        except Exception as storage_exc:
            logger.error(f"Readiness Object Storage probe failed: {storage_exc}")
            components["object_storage"] = "unavailable"
            is_ready = False

        # 5. ClamAV check
        try:
            from apps.documents.malware_scanner import get_malware_scanner
            scanner = get_malware_scanner()
            if scanner.ping():
                components["clamav"] = "connected"
            else:
                logger.warning("Readiness ClamAV probe: Daemon did not respond to ping.")
                components["clamav"] = "unavailable"
                is_ready = False
        except Exception as clamav_exc:
            logger.error(f"Readiness ClamAV probe failed: {clamav_exc}")
            components["clamav"] = "unavailable"
            is_ready = False

        http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                "status": "ready" if is_ready else "degraded",
                "components": components
            },
            status=http_status
        )


def custom_exception_handler(exc, context):
    """
    Production-safe DRF exception handler.
    Prevents leakage of stack traces, filesystem paths, credentials, or SQL details in 500 errors.
    Logs the full traceback internally with sensitive data redaction.
    """
    from rest_framework.views import exception_handler as drf_exception_handler
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        if getattr(settings, 'DEBUG', False):
            return Response(
                {"error": str(exc), "code": "INTERNAL_SERVER_ERROR"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response(
            {
                "error": "An internal server error occurred. Please contact system support.",
                "code": "INTERNAL_SERVER_ERROR"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response

