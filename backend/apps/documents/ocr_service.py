import hashlib
import json
import uuid
import logging
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.audit.models import AuditLog, AuditAction
from .models import (
    ApplicantDocument,
    DocumentVersion,
    DocumentLifecycleStatus,
    OCRJob,
    OCRJobStatus,
    OCRResult,
    OCRPage,
    OCRBlock,
    DocumentClassificationResult,
    ProvisionalExtractedField,
)
from .storage import get_object_storage
from .ocr_renderer import DocumentOCRRenderer, OCRError, ResourceExhaustionError, MalformedDocumentError
from .ocr_engines import get_ocr_engine, RawOCRBlock
from .classifier import DocumentClassifier
from .field_extractor import ProvisionalFieldExtractor, ExtractedFieldCandidate

logger = logging.getLogger('apps.documents.ocr')


class InvalidDocumentStateForOCRError(OCRError):
    """Raised when an OCR job is requested for a non-SAFE document."""
    pass


class OCRService:
    """
    Authoritative service orchestrating the Secure OCR & Document Intelligence Pipeline.
    Enforces the single service-level security guard, idempotency, provenance linking,
    and field conflict detection.
    """

    @classmethod
    def validate_document_can_enter_ocr(cls, document: ApplicantDocument) -> None:
        """
        Authoritative single service-level guard: OCR may ONLY process SAFE documents.
        Refuses: INITIATED, UPLOADING, UPLOADED, QUARANTINED, SCANNING,
        PROMOTION_PENDING, REJECTED, SCAN_ERROR, RECONCILIATION_REQUIRED, REVOKED.
        """
        if document.lifecycle_status != DocumentLifecycleStatus.SAFE:
            raise InvalidDocumentStateForOCRError(
                "DOCUMENT_NOT_SAFE_FOR_OCR",
                f"Document '{document.id}' is in lifecycle state '{document.lifecycle_status}'. "
                "OCR processing strictly requires 'SAFE' state."
            )

    @classmethod
    def create_or_get_ocr_job(
        cls,
        document_id,
        document_version_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> OCRJob:
        """
        Idempotently creates or discovers an OCRJob for a SAFE document.
        """
        doc = ApplicantDocument.objects.get(id=document_id)
        cls.validate_document_can_enter_ocr(doc)

        doc_version = None
        if document_version_id:
            doc_version = DocumentVersion.objects.filter(id=document_version_id).first()
        else:
            doc_version = doc.versions.order_by('-version_number').first()

        pipeline_version = getattr(settings, 'OCR_PIPELINE_VERSION', '1.0.0')
        idempotency_key = f"{doc_version.id if doc_version else doc.id}:{pipeline_version}:OCR_EXTRACTION"
        corr_id = correlation_id or f"OCR-JOB-{doc.id}-{uuid.uuid4().hex[:8]}"

        with transaction.atomic():
            job, created = OCRJob.objects.select_for_update().get_or_create(
                idempotency_key=idempotency_key,
                defaults={
                    "document": doc,
                    "document_version": doc_version,
                    "job_type": "OCR_EXTRACTION",
                    "status": OCRJobStatus.PENDING,
                    "correlation_id": corr_id,
                    "pipeline_version": pipeline_version,
                    "engine_name": getattr(settings, 'OCR_ENGINE_BACKEND', 'paddleocr')
                }
            )

            if created:
                AuditLog.objects.create(
                    actor=None,
                    actor_role='SYSTEM',
                    entity_type='ApplicantDocument',
                    entity_id=str(doc.id),
                    action=AuditAction.OCR_JOB_CREATED,
                    after_json={
                        "job_id": str(job.id),
                        "idempotency_key": idempotency_key,
                        "correlation_id": corr_id,
                    },
                    reason="Asynchronous OCR job created for safe document."
                )

        return job

    @classmethod
    def enqueue_ocr_job(
        cls,
        document_id,
        correlation_id: Optional[str] = None,
        sync_process: bool = False
    ) -> OCRJob:
        """
        Schedules an OCR job asynchronously through transaction.on_commit and Redis.
        Supports sync execution for unit testing.
        """
        job = cls.create_or_get_ocr_job(document_id, correlation_id=correlation_id)

        if sync_process:
            cls.execute_ocr_pipeline(job.id, correlation_id=correlation_id)
            job.refresh_from_db()
        else:
            def _dispatch():
                try:
                    from .tasks import run_ocr_task
                    run_ocr_task.delay(str(job.id), correlation_id=correlation_id)
                except Exception as exc:
                    logger.error(f"Failed to dispatch Celery OCR task for job {job.id}: {exc}")

            transaction.on_commit(_dispatch)

        return job

    @classmethod
    def execute_ocr_pipeline(
        cls,
        ocr_job_id,
        task_id: Optional[str] = None,
        worker_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        lang: Optional[str] = None
    ) -> OCRResult:
        """
        Executes the complete OCR + Classification + Field Extraction pipeline.
        Pessimistic row locking ensures single-worker execution and idempotency.
        """
        storage = get_object_storage()
        engine = get_ocr_engine(lang=lang)

        with transaction.atomic():
            job = OCRJob.objects.select_for_update().get(id=ocr_job_id)
            doc = job.document

            # Idempotency guard: If already COMPLETED, safely return existing result
            if job.status == OCRJobStatus.COMPLETED and hasattr(job, 'result'):
                logger.info(f"OCRJob {job.id} already COMPLETED. Returning existing OCRResult (Idempotent skip).")
                return job.result

            # Authoritative State Check
            cls.validate_document_can_enter_ocr(doc)

            # Update job to RUNNING
            job.status = OCRJobStatus.RUNNING
            job.started_at = timezone.now()
            job.attempts += 1
            if task_id:
                job.task_id = task_id
            if worker_id:
                job.worker_id = worker_id
            if correlation_id:
                job.correlation_id = correlation_id
            job.engine_name = engine.engine_name
            job.engine_version = engine.engine_version
            job.configuration_hash = engine.get_configuration_hash()
            job.save()

            AuditLog.objects.create(
                actor=None,
                actor_role='SYSTEM',
                entity_type='ApplicantDocument',
                entity_id=str(doc.id),
                action=AuditAction.OCR_STARTED,
                after_json={
                    "job_id": str(job.id),
                    "attempt": job.attempts,
                    "engine": engine.engine_name,
                    "correlation_id": job.correlation_id,
                },
                reason="OCR processing started on worker."
            )

        # Retrieval of safe document content outside row lock to reduce lock hold time
        try:
            stream = storage.get_stream(doc.storage_key)
            raw_bytes = stream.read()
            stream.close()
        except Exception as exc:
            logger.error(f"Failed to read safe document {doc.id} from storage: {exc}")
            cls._mark_job_failed(job, "STORAGE_READ_ERROR", str(exc))
            raise

        # Page Rendering & Resource Safety Checks
        try:
            rendered_pages = DocumentOCRRenderer.render_document_pages(
                raw_bytes=raw_bytes,
                mime_type=doc.detected_mime_type or doc.declared_mime_type
            )
        except OCRError as ocr_err:
            logger.warning(f"Document {doc.id} failed OCR rendering checks: {ocr_err.code} - {ocr_err.message}")
            cls._mark_job_failed(job, ocr_err.code, ocr_err.message)
            raise
        except Exception as exc:
            logger.error(f"Unexpected error rendering document {doc.id}: {exc}")
            cls._mark_job_failed(job, "UNEXPECTED_RENDERING_ERROR", str(exc))
            raise

        # Engine OCR processing on each page
        pages_blocks: Dict[int, List[RawOCRBlock]] = {}
        all_blocks_text: List[str] = []

        try:
            for page in rendered_pages:
                blocks = engine.process_image(page.image, page_num=page.page_number)
                pages_blocks[page.page_number] = blocks
                for b in blocks:
                    all_blocks_text.append(b.text)
        except Exception as exc:
            logger.error(f"OCR engine execution error on document {doc.id}: {exc}")
            cls._mark_job_failed(job, "OCR_ENGINE_EXECUTION_ERROR", str(exc))
            raise

        full_text = "\n".join(all_blocks_text)

        # Result hash computation (SHA-256 of canonical text and page hashes)
        canonical_digest_input = f"{full_text}:{len(rendered_pages)}:{engine.get_configuration_hash()}"
        result_hash = hashlib.sha256(canonical_digest_input.encode('utf-8')).hexdigest()

        # Database Entity Persistence in Transaction
        with transaction.atomic():
            # Refresh job and lock again
            job = OCRJob.objects.select_for_update().get(id=ocr_job_id)

            # Idempotency double-check inside transaction
            if job.status == OCRJobStatus.COMPLETED and hasattr(job, 'result'):
                return job.result

            ocr_result = OCRResult.objects.create(
                ocr_job=job,
                document=doc,
                document_version=job.document_version,
                page_count=len(rendered_pages),
                engine_name=engine.engine_name,
                engine_version=engine.engine_version,
                pipeline_version=job.pipeline_version,
                language_metadata={"primary_language": getattr(engine, 'lang', 'en')},
                result_hash=result_hash,
                full_text=full_text
            )

            # Persist Pages and Blocks
            for page in rendered_pages:
                blocks = pages_blocks.get(page.page_number, [])
                page_text = "\n".join([b.text for b in blocks])
                avg_conf = (sum(b.confidence for b in blocks) / len(blocks)) if blocks else 0.0
                page_hash = hashlib.sha256(page_text.encode('utf-8')).hexdigest()

                ocr_page = OCRPage.objects.create(
                    ocr_result=ocr_result,
                    page_number=page.page_number,
                    width=page.width,
                    height=page.height,
                    rotation=page.rotation,
                    processing_status='SUCCESS',
                    text_aggregate=page_text,
                    page_confidence=round(avg_conf, 2),
                    page_hash=page_hash
                )

                created_blocks = []
                for b in blocks:
                    block_obj = OCRBlock.objects.create(
                        page=ocr_page,
                        extracted_text=b.text,
                        confidence=b.confidence,
                        bbox_x=b.bbox_x,
                        bbox_y=b.bbox_y,
                        bbox_width=b.bbox_width,
                        bbox_height=b.bbox_height,
                        polygon=b.polygon,
                        block_type=b.block_type,
                        language=b.language,
                        reading_order=b.reading_order
                    )
                    created_blocks.append(block_obj)

            # Document Classification Layer
            classification = DocumentClassifier.classify(full_text)
            DocumentClassificationResult.objects.create(
                document=doc,
                document_version=job.document_version,
                ocr_result=ocr_result,
                predicted_type=classification.predicted_type,
                confidence=classification.confidence,
                classifier_version=classification.classifier_version,
                classification_method=classification.classification_method,
                evidence_summary=classification.evidence_summary
            )

            # Provisional Field Extraction Layer
            extracted_candidates = ProvisionalFieldExtractor.extract_fields(pages_blocks, full_text)
            for cand in extracted_candidates:
                # Find matching page and block for evidence linking
                matching_page = ocr_result.pages.filter(page_number=cand.page_number).first()
                matching_block = None
                if matching_page:
                    matching_block = matching_page.blocks.filter(reading_order=cand.block_index + 1).first()

                ProvisionalExtractedField.objects.create(
                    document=doc,
                    document_version=job.document_version,
                    ocr_result=ocr_result,
                    ocr_page=matching_page,
                    ocr_block=matching_block,
                    field_code=cand.field_code,
                    field_label=cand.field_label,
                    raw_value=cand.raw_value,
                    normalized_value=cand.normalized_value,
                    confidence=cand.confidence,
                    trust_level='OCR_PROVISIONAL',
                    extraction_method=cand.extraction_method,
                    pipeline_version=cand.pipeline_version,
                    page_number=cand.page_number,
                    bounding_box=cand.bounding_box
                )

            # Conflict Detection & Field Value Integration
            cls._integrate_application_fields_and_detect_conflicts(doc, extracted_candidates, ocr_result)

            # Authoritative Handoff to Verification Queue
            try:
                from apps.verification.services import DocumentVerificationService
                DocumentVerificationService.enqueue_document_for_verification(doc, correlation_id=job.correlation_id)
            except Exception as v_err:
                logger.error(f"Failed to auto-enqueue document {doc.id} for verification: {v_err}")
                try:
                    AuditLog.objects.create(
                        actor=None,
                        actor_role='SYSTEM',
                        entity_type='ApplicantDocument',
                        entity_id=str(doc.id),
                        action=AuditAction.VALIDATE,
                        after_json={'error': str(v_err), 'correlation_id': job.correlation_id, 'queue_handoff_failed': True},
                        reason=f"OCR succeeded, but auto-enqueuing to verification queue failed: {v_err}. Retry scheduled on submission."
                    )
                except Exception as audit_err:
                    logger.error(f"Failed to write audit log for queue handoff failure: {audit_err}")

            # Mark OCRJob COMPLETED
            job.status = OCRJobStatus.COMPLETED
            job.completed_at = timezone.now()
            job.save()

            # Update backward-compatibility fields on ApplicantDocument
            doc.ocr_extracted_text = full_text[:5000]
            total_blocks = sum(len(b) for b in pages_blocks.values())
            overall_conf = (sum(sum(b.confidence for b in bl) for bl in pages_blocks.values()) / total_blocks) if total_blocks else 0.0
            doc.ocr_confidence_score = round(overall_conf, 2)
            doc.save()

            # Audit Logs
            AuditLog.objects.create(
                actor=None,
                actor_role='SYSTEM',
                entity_type='ApplicantDocument',
                entity_id=str(doc.id),
                action=AuditAction.OCR_COMPLETED,
                after_json={
                    "job_id": str(job.id),
                    "page_count": len(rendered_pages),
                    "result_hash": result_hash,
                    "correlation_id": job.correlation_id,
                },
                reason="OCR pipeline completed successfully. Evidence and blocks persisted."
            )

            AuditLog.objects.create(
                actor=None,
                actor_role='SYSTEM',
                entity_type='ApplicantDocument',
                entity_id=str(doc.id),
                action=AuditAction.DOCUMENT_CLASSIFIED,
                after_json={
                    "predicted_type": classification.predicted_type,
                    "confidence": classification.confidence,
                    "correlation_id": job.correlation_id,
                },
                reason=f"Document classified as {classification.predicted_type}."
            )

            if extracted_candidates:
                AuditLog.objects.create(
                    actor=None,
                    actor_role='SYSTEM',
                    entity_type='ApplicantDocument',
                    entity_id=str(doc.id),
                    action=AuditAction.FIELD_EXTRACTED,
                    after_json={
                        "field_codes": [c.field_code for c in extracted_candidates],
                        "count": len(extracted_candidates),
                        "correlation_id": job.correlation_id,
                    },
                    reason=f"Extracted {len(extracted_candidates)} provisional fields from OCR evidence."
                )

        return ocr_result

    @classmethod
    def _integrate_application_fields_and_detect_conflicts(
        cls,
        doc: ApplicantDocument,
        candidates: List[ExtractedFieldCandidate],
        ocr_result: OCRResult
    ) -> None:
        """
        Integrates extracted fields into ApplicationFieldValue with trust rank OCR_PROVISIONAL (10).
        Detects MATERIAL_CONFLICT against APPLICANT_DECLARED values without overwriting them.
        """
        if not doc.application:
            return

        from apps.applications.models import (
            ApplicationFieldValue, ApplicationFieldDefinition,
            FieldValueSource, FieldValueVerificationStatus,
            ApplicationDeficiency, DeficiencySeverity, DeficiencyStatus
        )
        from apps.verification.models import VerificationQueueItem, VerificationItemType, VerificationStatus

        application = doc.application
        if not application.scheme_version:
            return

        for cand in candidates:
            # Check if field definition exists for the application's scheme
            field_def = ApplicationFieldDefinition.objects.filter(
                scheme_version=application.scheme_version,
                field_code=cand.field_code
            ).first()

            # Record provisional value in ApplicationFieldValue (source=OCR, rank=10)
            if field_def:
                ApplicationFieldValue.objects.create(
                    application=application,
                    field_definition=field_def,
                    value_json=cand.normalized_value,
                    source=FieldValueSource.OCR,
                    confidence=cand.confidence,
                    verification_status=FieldValueVerificationStatus.PROVISIONALLY_EXTRACTED
                )

            # Conflict Detection: Compare against highest-trust applicant declaration
            existing_declared = ApplicationFieldValue.objects.filter(
                application=application,
                field_definition__field_code=cand.field_code,
                source=FieldValueSource.APPLICANT
            ).order_by('-created_at').first()

            if existing_declared and existing_declared.value_json is not None:
                dec_val = existing_declared.value_json
                ocr_val = cand.normalized_value

                # Material disagreement check
                has_conflict = False
                if isinstance(dec_val, (int, float)) and isinstance(ocr_val, (int, float)):
                    # Income/currency difference exceeding 5% threshold
                    diff = abs(float(dec_val) - float(ocr_val))
                    if diff > 1000 and (diff / max(float(dec_val), 1.0)) > 0.05:
                        has_conflict = True
                elif str(dec_val).strip().lower() != str(ocr_val).strip().lower():
                    has_conflict = True

                if has_conflict:
                    # Emit conflict audit event
                    AuditLog.objects.create(
                        actor=None,
                        actor_role='SYSTEM',
                        entity_type='Application',
                        entity_id=str(application.id),
                        action=AuditAction.FIELD_CONFLICT_DETECTED,
                        after_json={
                            "field_code": cand.field_code,
                            "declared_value": dec_val,
                            "ocr_extracted_value": ocr_val,
                            "document_id": str(doc.id),
                        },
                        reason=(
                            f"Material disagreement detected for field '{cand.field_code}': "
                            f"Applicant declared '{dec_val}', OCR extracted '{ocr_val}'."
                        )
                    )

                    # Create Human Verification Queue Item (Officer Review)
                    VerificationQueueItem.objects.create(
                        application=application,
                        document=doc,
                        item_type=VerificationItemType.DOCUMENT,
                        target_identifier=f"CONFLICT_{cand.field_code}_{doc.id}",
                        confidence_score=cand.confidence,
                        status=VerificationStatus.PENDING,
                        ai_assistance_json={
                            "conflict_type": "MATERIAL_CONFLICT",
                            "field_code": cand.field_code,
                            "applicant_declared": dec_val,
                            "ocr_extracted": ocr_val,
                            "page_number": cand.page_number,
                            "bounding_box": cand.bounding_box,
                            "raw_text": cand.raw_value,
                        },
                        officer_remarks=(
                            f"Provisional OCR value ('{ocr_val}') materially conflicts with "
                            f"applicant declared value ('{dec_val}'). Human officer scrutiny required."
                        )
                    )

    @classmethod
    def _mark_job_failed(cls, job: OCRJob, failure_code: str, failure_message: str) -> None:
        """
        Marks an OCRJob as FAILED while strictly preserving the document's SAFE security state.
        """
        try:
            with transaction.atomic():
                job.status = OCRJobStatus.FAILED
                job.failure_code = failure_code[:100]
                job.failure_message = failure_message
                job.completed_at = timezone.now()
                job.save()

                AuditLog.objects.create(
                    actor=None,
                    actor_role='SYSTEM',
                    entity_type='ApplicantDocument',
                    entity_id=str(job.document_id),
                    action=AuditAction.OCR_FAILED,
                    after_json={
                        "job_id": str(job.id),
                        "failure_code": failure_code,
                        "failure_message": failure_message[:200],
                        "correlation_id": job.correlation_id,
                    },
                    reason=f"OCR processing failed: {failure_code}."
                )
        except Exception as exc:
            logger.error(f"Error marking OCR job {job.id} as failed: {exc}")
