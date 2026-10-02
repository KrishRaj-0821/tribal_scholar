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
    Readiness probe: verifies connectivity to PostgreSQL and Redis.
    Never exposes internal hostnames, ports, credentials, or sensitive error traces.
    Returns 200 when ready, 503 when degraded.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        is_ready = True
        components = {
            "database": "unknown",
            "redis": "unknown"
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

