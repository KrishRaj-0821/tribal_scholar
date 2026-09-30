import hashlib
import uuid
from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.conf import settings

from apps.audit.models import AuditLog, AuditAction
from .models import (
    ApplicantDocument,
    ApplicantDocumentType,
    DocumentLifecycleStatus,
    MalwareScanStatus,
    ContentValidationStatus,
    DocumentJobType,
    DocumentJobStatus,
    DocumentRequirement,
    DocumentVersion,
    DocumentManifest,
    DocumentProcessingJob,
    DocumentJobExecution,
    JobExecutionStatus,
    SecurityQuarantineRecord,
    QuarantineDeletionStatus,
)
from .storage import get_object_storage
from .malware_scanner import get_malware_scanner
from .security import DocumentSecurityValidator, FileContentDetector


class DocumentIngestionService:
    """
    Authoritative service orchestrating the complete secure document ingestion pipeline:
    Upload -> Quarantine -> Security Scan -> Deep Content Validation -> Promotion -> Manifesting
    """

    @classmethod
    def upload_document(
        cls,
        application,
        actor_user,
        document_type: str,
        file_obj,
        client_checksum: Optional[str] = None,
        sync_process: bool = False
    ) -> ApplicantDocument:
        """
        Receives raw upload, validates scheme binding, puts file into quarantine storage,
        records initial database entities, and enqueues asynchronous processing.
        """
        # 1. Authorization Gate
        if not actor_user or not actor_user.is_authenticated:
            raise PermissionDenied("Authentication required to upload application documents.")

        is_owner = (application.applicant.user_id == actor_user.id)
        is_staff_or_admin = (
            getattr(actor_user, 'is_staff', False) or
            getattr(actor_user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER')
        )
        if not (is_owner or is_staff_or_admin):
            raise PermissionDenied("You are not authorized to upload documents for this application.")

        # 2. Scheme Document Requirement Binding Check
        if not application.scheme_version:
            raise ValidationError("Target application has no active SchemeVersion associated.")

        requirement = DocumentRequirement.objects.filter(
            scheme_version=application.scheme_version,
            document_type=document_type
        ).first()

        if not requirement:
            raise ValidationError(
                f"Document type '{document_type}' is not a statutory requirement "
                f"for scheme version '{application.scheme_version}'."
            )

        # 3. Read content & compute authoritative SHA-256
        if hasattr(file_obj, 'read'):
            raw_content = file_obj.read()
        elif isinstance(file_obj, bytes):
            raw_content = file_obj
        else:
            raise ValidationError("Invalid file object provided.")

        actual_size = len(raw_content)
        if actual_size == 0:
            raise ValidationError("Uploaded file is empty (0 bytes).")

        # 4. Strict File Size Enforcement
        global_max_bytes = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 10) * 1024 * 1024
        req_max_bytes = requirement.max_size_mb * 1024 * 1024
        effective_max_bytes = min(global_max_bytes, req_max_bytes)

        if actual_size > effective_max_bytes:
            raise ValidationError(
                f"File size ({actual_size} bytes) exceeds maximum permitted limit of {effective_max_bytes} bytes."
            )

        # Authoritative SHA-256 (client_checksum is completely ignored)
        authoritative_sha256 = hashlib.sha256(raw_content).hexdigest()

        # Extract declared attributes
        original_name = getattr(file_obj, 'name', 'document.bin')
        declared_mime = getattr(file_obj, 'content_type', '') or 'application/octet-stream'

        # 5. Preliminary Magic Byte Security Filter
        # Fast reject known dangerous executables before writing to storage
        detected_prelim_mime = FileContentDetector.detect_mime(raw_content)
        if detected_prelim_mime in (
            "application/x-dosexec",
            "application/x-executable",
            "application/x-mach-binary",
            "application/zip",
            "text/html",
            "application/javascript"
        ):
            raise ValidationError(
                f"Executable, script, or archive binary detected ({detected_prelim_mime}). "
                "Upload rejected by security boundary."
            )

        # 6. Quarantine Storage
        doc_id = uuid.uuid4()
        storage = get_object_storage()
        quarantine_key = storage.put_quarantine(str(doc_id), raw_content, original_name)

        # 7. Duplicate Content Candidate Check
        is_duplicate_candidate = ApplicantDocument.objects.filter(
            sha256=authoritative_sha256
        ).exclude(applicant=application.applicant.user).exists()

        metadata = {
            "declared_mime": declared_mime,
            "original_filename": original_name,
            "quarantine_key": quarantine_key,
        }
        if is_duplicate_candidate:
            metadata["duplicate_document_candidate"] = True

        # 8. Database Entity Persistence in Transaction
        with transaction.atomic():
            # Check if this document type already exists on the application to determine version
            existing_doc = ApplicantDocument.objects.filter(
                application=application,
                document_type=document_type
            ).first()

            if existing_doc:
                document = existing_doc
                document.original_filename = original_name
                document.file_name = original_name
                document.storage_key = quarantine_key
                document.declared_mime_type = declared_mime
                document.detected_mime_type = detected_prelim_mime
                document.file_size_bytes = actual_size
                document.sha256 = authoritative_sha256
                document.checksum = authoritative_sha256
                document.lifecycle_status = DocumentLifecycleStatus.QUARANTINED
                document.malware_scan_status = MalwareScanStatus.NOT_SCANNED
                document.content_validation_status = ContentValidationStatus.PENDING
                document.uploaded_by = actor_user
                document.uploaded_at = timezone.now()
                document.metadata_json = metadata
                document.save()

                latest_ver = document.versions.order_by('-version_number').first()
                new_ver_num = (latest_ver.version_number + 1) if latest_ver else 2
                supersedes_ver = latest_ver
            else:
                document = ApplicantDocument.objects.create(
                    id=doc_id,
                    application=application,
                    applicant=application.applicant.user,
                    document_type=document_type,
                    original_filename=original_name,
                    file_name=original_name,
                    storage_key=quarantine_key,
                    declared_mime_type=declared_mime,
                    detected_mime_type=detected_prelim_mime,
                    file_size_bytes=actual_size,
                    sha256=authoritative_sha256,
                    checksum=authoritative_sha256,
                    lifecycle_status=DocumentLifecycleStatus.QUARANTINED,
                    malware_scan_status=MalwareScanStatus.NOT_SCANNED,
                    content_validation_status=ContentValidationStatus.PENDING,
                    uploaded_by=actor_user,
                    uploaded_at=timezone.now(),
                    metadata_json=metadata
                )
                new_ver_num = 1
                supersedes_ver = None

            # Create DocumentVersion record
            DocumentVersion.objects.create(
                document=document,
                version_number=new_ver_num,
                storage_key=quarantine_key,
                sha256=authoritative_sha256,
                file_size_bytes=actual_size,
                uploaded_at=timezone.now(),
                uploaded_by=actor_user,
                lifecycle_status=DocumentLifecycleStatus.QUARANTINED,
                supersedes_version=supersedes_ver,
                reason="Initial upload" if new_ver_num == 1 else "Replacement document version"
            )

            # Create processing job record
            correlation_id = f"DOC-JOB-{document.id}-{uuid.uuid4().hex[:8]}"
            job = DocumentProcessingJob.objects.create(
                document=document,
                job_type=DocumentJobType.SECURITY_SCAN,
                status=DocumentJobStatus.PENDING,
                correlation_id=correlation_id
            )

            # Audit Log: Document Uploaded
            AuditLog.objects.create(
                actor=actor_user,
                actor_role=getattr(actor_user, 'role', 'APPLICANT'),
                entity_type='ApplicantDocument',
                entity_id=str(document.id),
                action=AuditAction.DOCUMENT_UPLOADED,
                after_json={
                    "document_type": document_type,
                    "sha256": authoritative_sha256,
                    "size_bytes": actual_size,
                    "version": new_ver_num,
                    "storage_key": quarantine_key,
                    "is_duplicate_candidate": is_duplicate_candidate
                },
                reason="Document uploaded to quarantine."
            )

            if is_duplicate_candidate:
                AuditLog.objects.create(
                    actor=None,
                    actor_role='SYSTEM',
                    entity_type='ApplicantDocument',
                    entity_id=str(document.id),
                    action=AuditAction.DUPLICATE_FLAGGED,
                    after_json={"sha256": authoritative_sha256},
                    reason="Document checksum matches submission from another user. Marked as DUPLICATE_DOCUMENT_CANDIDATE."
                )

        # 9. Asynchronous Processing Boundary
        def _dispatch():
            try:
                from .tasks import process_document_pipeline_task
                process_document_pipeline_task.delay(str(document.id), correlation_id=correlation_id)
            except Exception as e:
                logger.error(f"Failed to dispatch async document processing task: {e}")

        if sync_process:
            # Synchronous processing (for tests and direct validation)
            document = cls.process_document(document.id, correlation_id=correlation_id)
        else:
            transaction.on_commit(_dispatch)

        return document

    @classmethod
    def process_document(
        cls,
        document_id,
        correlation_id: Optional[str] = None,
        task_id: Optional[str] = None,
        worker_id: Optional[str] = None
    ) -> ApplicantDocument:
        """
        Core worker processing method.
        Uses SELECT FOR UPDATE row-level locking to guarantee idempotent, race-free promotion.
        Tracks execution via DocumentJobExecution and preserves security quarantine evidence.
        """
        storage = get_object_storage()
        scanner = get_malware_scanner()

        with transaction.atomic():
            doc = ApplicantDocument.objects.select_for_update().get(id=document_id)

            # Idempotency Guard: Never re-process already resolved safe/rejected documents
            if doc.lifecycle_status in (
                DocumentLifecycleStatus.SAFE,
                DocumentLifecycleStatus.REJECTED,
                DocumentLifecycleStatus.VERIFIED,
                DocumentLifecycleStatus.REVOKED
            ):
                return doc

            job = DocumentProcessingJob.objects.filter(
                document=doc,
                status__in=[DocumentJobStatus.PENDING, DocumentJobStatus.FAILED, DocumentJobStatus.PROCESSING]
            ).order_by('-created_at').first()

            if not job:
                job = DocumentProcessingJob.objects.create(
                    document=doc,
                    job_type=DocumentJobType.SECURITY_SCAN,
                    status=DocumentJobStatus.PROCESSING,
                    correlation_id=correlation_id or f"DOC-JOB-{doc.id}",
                    started_at=timezone.now(),
                    attempts=1
                )
            else:
                job.status = DocumentJobStatus.PROCESSING
                job.started_at = timezone.now()
                job.attempts += 1
                if correlation_id and not job.correlation_id:
                    job.correlation_id = correlation_id
                job.save()

            effective_task_id = task_id or str(uuid.uuid4())
            effective_corr_id = correlation_id or job.correlation_id or f"CORR-{doc.id}"
            effective_worker_id = worker_id or "worker-local"

            # Create DocumentJobExecution record for deterministic idempotency audit
            execution = DocumentJobExecution.objects.create(
                job=job,
                task_id=effective_task_id,
                document=doc,
                stage='INITIALIZED',
                execution_status=JobExecutionStatus.RUNNING,
                worker_id=effective_worker_id,
                correlation_id=effective_corr_id,
                retry_count=job.attempts
            )

            doc.lifecycle_status = DocumentLifecycleStatus.SCANNING
            doc.save()

            # Retrieve quarantine payload
            try:
                with storage.get_stream(doc.storage_key) as f:
                    content = f.read()
            except Exception as e:
                # Storage retrieval error
                if job:
                    job.status = DocumentJobStatus.FAILED
                    job.error_code = "STORAGE_ERROR"
                    job.error_message = f"Failed to retrieve quarantine file: {e}"
                    job.save()
                execution.execution_status = JobExecutionStatus.FAILED
                execution.finished_at = timezone.now()
                execution.details = {"error": str(e)}
                execution.save()
                return doc

            # Step A: Deep Content & Format Validation
            execution.stage = 'CONTENT_VALIDATION'
            execution.save()

            val_res = DocumentSecurityValidator.validate_file(
                content=content,
                declared_filename=doc.original_filename or doc.file_name,
                declared_mime=doc.declared_mime_type,
                max_size_bytes=getattr(settings, 'MAX_UPLOAD_SIZE_MB', 10) * 1024 * 1024
            )

            if not val_res.is_valid:
                doc.lifecycle_status = DocumentLifecycleStatus.REJECTED
                doc.detected_mime_type = val_res.detected_mime
                doc.content_validation_status = ContentValidationStatus.INVALID
                doc.rejection_reason = f"{val_res.error_code}: {val_res.error_message}"
                doc.save()

                if job:
                    job.status = DocumentJobStatus.PERMANENT_FAILURE
                    job.error_code = val_res.error_code or "VALIDATION_FAILED"
                    job.error_message = val_res.error_message or "Content validation failed."
                    job.completed_at = timezone.now()
                    job.save()

                execution.execution_status = JobExecutionStatus.FAILED
                execution.finished_at = timezone.now()
                execution.details = {"error_code": val_res.error_code, "error_message": val_res.error_message}
                execution.save()

                AuditLog.objects.create(
                    actor=None,
                    actor_role='SYSTEM',
                    entity_type='ApplicantDocument',
                    entity_id=str(doc.id),
                    action=AuditAction.DOCUMENT_REJECTED,
                    after_json={
                        "error_code": val_res.error_code,
                        "rejection_reason": doc.rejection_reason,
                        "correlation_id": effective_corr_id,
                    },
                    reason=f"Document rejected: {val_res.error_message}"
                )
                return doc

            doc.detected_mime_type = val_res.detected_mime
            doc.content_validation_status = ContentValidationStatus.VALID

            # Step B: Antivirus / Malware Scan
            execution.stage = 'SECURITY_SCAN'
            execution.save()

            doc.malware_scan_status = MalwareScanStatus.SCANNING
            doc.save()

            scan_status, scan_detail = scanner.scan(content)
            doc.malware_scan_status = scan_status
            doc.malware_scan_timestamp = timezone.now()

            if scan_status == MalwareScanStatus.INFECTED:
                doc.lifecycle_status = DocumentLifecycleStatus.REJECTED
                doc.rejection_reason = f"MALWARE_DETECTED: {scan_detail}"
                doc.save()

                if job:
                    job.status = DocumentJobStatus.PERMANENT_FAILURE
                    job.error_code = "INFECTED"
                    job.error_message = scan_detail
                    job.completed_at = timezone.now()
                    job.save()

                execution.execution_status = JobExecutionStatus.FAILED
                execution.finished_at = timezone.now()
                execution.details = {"malware_scan": scan_detail}
                execution.save()

                # Requirement 12: Security Quarantine Retention Record
                # Preserves forensic evidence in isolated quarantine storage for configured retention period
                retention_days = getattr(settings, 'QUARANTINE_RETENTION_DAYS', 30)
                SecurityQuarantineRecord.objects.create(
                    document=doc,
                    detection_result=scan_detail,
                    scanner=scanner.__class__.__name__,
                    detected_at=timezone.now(),
                    retention_until=timezone.now() + timezone.timedelta(days=retention_days),
                    deletion_status=QuarantineDeletionStatus.RETAINED,
                    quarantine_storage_key=doc.storage_key
                )

                AuditLog.objects.create(
                    actor=None,
                    actor_role='SYSTEM',
                    entity_type='ApplicantDocument',
                    entity_id=str(doc.id),
                    action=AuditAction.DOCUMENT_REJECTED,
                    after_json={
                        "malware_scan_status": scan_status,
                        "detail": scan_detail,
                        "correlation_id": effective_corr_id,
                    },
                    reason="Malware detected during antivirus scan. Retained in security quarantine."
                )
                return doc

            elif scan_status == MalwareScanStatus.ERROR:
                doc.lifecycle_status = DocumentLifecycleStatus.QUARANTINED
                doc.rejection_reason = f"SCAN_ERROR: {scan_detail}"
                doc.save()

                if job:
                    job.status = DocumentJobStatus.FAILED
                    job.error_code = "SCAN_ERROR"
                    job.error_message = scan_detail
                    job.save()

                execution.execution_status = JobExecutionStatus.RETRY
                execution.finished_at = timezone.now()
                execution.details = {"scan_error": scan_detail}
                execution.save()
                return doc

            # Step C: Intermediate Promotion State & Promotion to Safe Storage
            doc.lifecycle_status = DocumentLifecycleStatus.PROMOTION_PENDING
            doc.save()

            execution.stage = 'STORAGE_PROMOTION'
            execution.save()

            try:
                safe_key = storage.promote_to_safe(
                    document_id=str(doc.id),
                    application_id=str(doc.application_id or 'unbound'),
                    filename=doc.original_filename or doc.file_name
                )
            except Exception as exc:
                doc.lifecycle_status = DocumentLifecycleStatus.SCANNING
                doc.save()
                if job:
                    job.status = DocumentJobStatus.FAILED
                    job.error_code = "PROMOTION_ERROR"
                    job.error_message = f"Storage promotion failed: {exc}"
                    job.save()
                execution.execution_status = JobExecutionStatus.FAILED
                execution.finished_at = timezone.now()
                execution.details = {"promotion_error": str(exc)}
                execution.save()
                return doc

            # Step D: Immutable Document Manifest
            execution.stage = 'DOCUMENT_MANIFEST'
            execution.save()

            DocumentManifest.objects.create(
                document=doc,
                sha256=doc.sha256,
                size_bytes=doc.file_size_bytes,
                detected_mime_type=doc.detected_mime_type,
                storage_key=safe_key,
                scan_status=scan_status,
                validation_status=doc.content_validation_status
            )

            # Update Document state to SAFE
            doc.storage_key = safe_key
            doc.lifecycle_status = DocumentLifecycleStatus.SAFE
            doc.processed_at = timezone.now()
            doc.save()

            if job:
                job.status = DocumentJobStatus.COMPLETED
                job.completed_at = timezone.now()
                job.save()

            execution.execution_status = JobExecutionStatus.COMPLETED
            execution.stage = 'COMPLETED'
            execution.finished_at = timezone.now()
            execution.save()

            AuditLog.objects.create(
                actor=None,
                actor_role='SYSTEM',
                entity_type='ApplicantDocument',
                entity_id=str(doc.id),
                action=AuditAction.DOCUMENT_PROMOTED,
                after_json={
                    "safe_storage_key": safe_key,
                    "sha256": doc.sha256,
                    "detected_mime": doc.detected_mime_type,
                    "correlation_id": effective_corr_id,
                },
                reason="Document passed security scan and content validation. Promoted to safe storage."
            )

            # Asynchronous OCR Dispatch: Only SAFE documents enter OCR (Requirement 2)
            if getattr(settings, 'ENABLE_AUTO_OCR', True):
                doc_id_val = doc.id
                def _dispatch_ocr():
                    try:
                        from .ocr_service import OCRService
                        OCRService.enqueue_ocr_job(doc_id_val, correlation_id=effective_corr_id)
                    except Exception as ocr_disp_err:
                        logger.warning(f"Could not auto-enqueue OCR job for doc {doc_id_val}: {ocr_disp_err}")

                transaction.on_commit(_dispatch_ocr)

            return doc

    @classmethod
    def revoke_document(cls, document_id, actor_user, reason: str) -> ApplicantDocument:
        """
        Revokes an existing document without destructive file deletion, preserving full audit history.
        """
        with transaction.atomic():
            doc = ApplicantDocument.objects.select_for_update().get(id=document_id)
            doc.lifecycle_status = DocumentLifecycleStatus.REVOKED
            doc.revoked_by = actor_user
            doc.revoked_at = timezone.now()
            doc.revocation_reason = reason
            doc.save()

            AuditLog.objects.create(
                actor=actor_user,
                actor_role=getattr(actor_user, 'role', 'STAFF'),
                entity_type='ApplicantDocument',
                entity_id=str(doc.id),
                action=AuditAction.DOCUMENT_REVOKED,
                after_json={"reason": reason, "revoked_at": str(doc.revoked_at)},
                reason=f"Document revoked: {reason}"
            )
            return doc
