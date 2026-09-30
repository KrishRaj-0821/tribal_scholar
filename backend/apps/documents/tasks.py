import json
import time
import uuid
import logging
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from .services import DocumentIngestionService
from .models import DocumentLifecycleStatus, DocumentProcessingJob

logger = logging.getLogger('apps.documents')


def log_structured_task_event(
    correlation_id: str,
    document_id: str,
    job_id: str,
    task_id: str,
    job_type: str,
    attempt: int,
    duration_ms: float,
    result_status: str,
    error: str = None
):
    """
    Emits structured, machine-parsable task logs adhering to Requirement 15.
    Never logs document binary bytes, OCR text, passwords, tokens, certificate numbers,
    passport numbers, or bank account numbers.
    """
    event = {
        "event_type": "celery_task_execution",
        "correlation_id": correlation_id or "UNKNOWN",
        "document_id": str(document_id),
        "job_id": str(job_id or "UNKNOWN"),
        "task_id": str(task_id),
        "job_type": job_type,
        "attempt": attempt,
        "duration_ms": round(duration_ms, 2),
        "result_status": result_status,
    }
    if error:
        event["error_summary"] = error[:200]
    logger.info(json.dumps(event))


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_document_pipeline_task(self, document_id: str, correlation_id: str = None):
    """
    Asynchronous Celery worker task that executes security scanning and deep content validation.
    Guarantees deterministic idempotency and structured observability.
    """
    task_id = self.request.id or str(uuid.uuid4())
    worker_id = getattr(self.request, 'hostname', 'celery-worker')
    attempt = getattr(self.request, 'retries', 0) + 1
    corr_id = correlation_id or f"CORR-{document_id}-{task_id[:8]}"
    start_time = time.monotonic()

    job_id = None
    try:
        # Pre-fetch or discover job_id for structured logging
        job = DocumentProcessingJob.objects.filter(document_id=document_id).order_by('-created_at').first()
        job_id = str(job.id) if job else "PENDING_DISCOVERY"

        doc = DocumentIngestionService.process_document(
            document_id=document_id,
            correlation_id=corr_id,
            task_id=task_id,
            worker_id=worker_id
        )

        duration_ms = (time.monotonic() - start_time) * 1000

        # Transient scan error -> retry
        if doc.lifecycle_status == DocumentLifecycleStatus.QUARANTINED and "SCAN_ERROR" in (doc.rejection_reason or ""):
            log_structured_task_event(
                correlation_id=corr_id,
                document_id=document_id,
                job_id=job_id,
                task_id=task_id,
                job_type="SECURITY_SCAN",
                attempt=attempt,
                duration_ms=duration_ms,
                result_status="TRANSIENT_FAILURE_RETRYING",
                error=doc.rejection_reason
            )
            if self.request.retries < self.max_retries:
                raise self.retry()

        result_status = "SUCCESS" if doc.lifecycle_status == DocumentLifecycleStatus.SAFE else "REJECTED"
        log_structured_task_event(
            correlation_id=corr_id,
            document_id=document_id,
            job_id=job_id,
            task_id=task_id,
            job_type="SECURITY_SCAN",
            attempt=attempt,
            duration_ms=duration_ms,
            result_status=result_status
        )

        return {
            "document_id": str(doc.id),
            "status": doc.lifecycle_status,
            "scan_status": doc.malware_scan_status,
            "validation_status": doc.content_validation_status,
            "correlation_id": corr_id,
            "task_id": task_id,
        }

    except ObjectDoesNotExist:
        duration_ms = (time.monotonic() - start_time) * 1000
        log_structured_task_event(
            correlation_id=corr_id,
            document_id=document_id,
            job_id=job_id or "NONE",
            task_id=task_id,
            job_type="SECURITY_SCAN",
            attempt=attempt,
            duration_ms=duration_ms,
            result_status="DOCUMENT_NOT_FOUND",
            error="Document does not exist in database"
        )
        return {"error": "DOCUMENT_NOT_FOUND"}

    except Exception as exc:
        duration_ms = (time.monotonic() - start_time) * 1000
        log_structured_task_event(
            correlation_id=corr_id,
            document_id=document_id,
            job_id=job_id or "NONE",
            task_id=task_id,
            job_type="SECURITY_SCAN",
            attempt=attempt,
            duration_ms=duration_ms,
            result_status="UNEXPECTED_ERROR",
            error=str(exc)
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"error": str(exc)}


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_ocr_task(self, ocr_job_id: str, correlation_id: str = None):
    """
    Asynchronous Celery task executing OCR, classification, and provisional field extraction.
    Guarantees deterministic idempotency, bounded retries, and structured observability.
    Preserves document SAFE security status regardless of OCR outcome.
    """
    from .models import OCRJob, OCRJobStatus
    from .ocr_service import OCRService, OCRError

    task_id = self.request.id or str(uuid.uuid4())
    worker_id = getattr(self.request, 'hostname', 'celery-ocr-worker')
    attempt = getattr(self.request, 'retries', 0) + 1
    start_time = time.monotonic()

    job = OCRJob.objects.filter(id=ocr_job_id).select_related('document').first()
    if not job:
        duration_ms = (time.monotonic() - start_time) * 1000
        log_structured_task_event(
            correlation_id=correlation_id or "UNKNOWN",
            document_id="UNKNOWN",
            job_id=ocr_job_id,
            task_id=task_id,
            job_type="OCR_EXTRACTION",
            attempt=attempt,
            duration_ms=duration_ms,
            result_status="JOB_NOT_FOUND",
            error="OCRJob does not exist in database"
        )
        return {"error": "OCR_JOB_NOT_FOUND"}

    corr_id = correlation_id or job.correlation_id or f"CORR-OCR-{job.document_id}-{task_id[:8]}"
    document_id = str(job.document_id)

    try:
        ocr_result = OCRService.execute_ocr_pipeline(
            ocr_job_id=ocr_job_id,
            task_id=task_id,
            worker_id=worker_id,
            correlation_id=corr_id
        )

        duration_ms = (time.monotonic() - start_time) * 1000
        log_structured_task_event(
            correlation_id=corr_id,
            document_id=document_id,
            job_id=str(job.id),
            task_id=task_id,
            job_type="OCR_EXTRACTION",
            attempt=attempt,
            duration_ms=duration_ms,
            result_status="SUCCESS"
        )

        return {
            "job_id": str(job.id),
            "document_id": document_id,
            "status": "COMPLETED",
            "page_count": ocr_result.page_count,
            "result_hash": ocr_result.result_hash,
            "correlation_id": corr_id,
            "task_id": task_id,
        }

    except OCRError as ocr_exc:
        duration_ms = (time.monotonic() - start_time) * 1000
        log_structured_task_event(
            correlation_id=corr_id,
            document_id=document_id,
            job_id=str(job.id),
            task_id=task_id,
            job_type="OCR_EXTRACTION",
            attempt=attempt,
            duration_ms=duration_ms,
            result_status=f"FAILED_{ocr_exc.code}",
            error=ocr_exc.message
        )
        # Permanent OCR error (resource exhaustion, invalid format, non-SAFE document) -> do not retry
        return {
            "job_id": str(job.id),
            "document_id": document_id,
            "status": "FAILED",
            "error_code": ocr_exc.code,
            "error_message": ocr_exc.message,
            "correlation_id": corr_id,
        }

    except Exception as exc:
        duration_ms = (time.monotonic() - start_time) * 1000
        log_structured_task_event(
            correlation_id=corr_id,
            document_id=document_id,
            job_id=str(job.id),
            task_id=task_id,
            job_type="OCR_EXTRACTION",
            attempt=attempt,
            duration_ms=duration_ms,
            result_status="UNEXPECTED_ERROR",
            error=str(exc)
        )
        # Transient failure: retry with bounded exponential backoff
        if self.request.retries < self.max_retries:
            job.status = OCRJobStatus.RETRY_PENDING
            job.save(update_fields=['status'])
            raise self.retry(exc=exc, countdown=min(60, 5 * (2 ** self.request.retries)))

        job.status = OCRJobStatus.FAILED
        job.failure_code = "MAX_RETRIES_EXCEEDED"
        job.failure_message = str(exc)
        job.save(update_fields=['status', 'failure_code', 'failure_message'])
        return {
            "job_id": str(job.id),
            "document_id": document_id,
            "status": "FAILED",
            "error": str(exc),
            "correlation_id": corr_id,
        }
