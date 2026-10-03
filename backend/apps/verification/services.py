import uuid
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.conf import settings

from apps.accounts.models import User, UserRole
from apps.audit.models import AuditLog, AuditAction
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue,
    FieldValueSource, FieldValueVerificationStatus, FieldDataType,
    FieldConflict, ConflictStatus
)
from apps.documents.models import (
    ApplicantDocument, DocumentVersion, OCRResult, OCRPage, OCRBlock,
    ProvisionalExtractedField, DocumentLifecycleStatus
)
from apps.schemes.evaluator import RuleEvaluationService
from .models import (
    VerificationQueueItem, VerificationStatus, VerificationPriority, VerificationItemType,
    DocumentVerificationRecord, VerificationRecordStatus,
    VerificationDecisionAction, VerificationMethod
)


class DocumentVerificationService:
    """
    Authoritative Phase 9 Service for Human-in-the-Loop Document Verification,
    Queue Adjudication, and Evidentiary Audit Trail.

    Statutory Principles:
    1. The Officer verifies evidence; the officer does NOT rewrite history.
    2. The Officer does NOT directly edit the underlying original document.
    3. The Officer does NOT bypass the deterministic scheme rule engine.
    4. Statutory Trust Hierarchy is strictly preserved:
       OFFICER_VERIFIED (60) > OFFICIAL_INTEGRATION (50) > VERIFIED_DOCUMENT (40) >
       SYSTEM (30) > APPLICANT_DECLARED (20) > OCR_PROVISIONAL (10)
    5. Separation of Duties: Applicants cannot inspect or verify their own applications.
    6. Concurrency Safe: select_for_update() prevents double-finalization.
    7. Pure Immutability: Every verification event creates an append-only audit trail.
    """

    @classmethod
    def validate_officer_authorization(cls, user: User, application: Optional[Application] = None):
        """
        Enforces strict server-side RBAC and Separation of Duties:
        - Authenticated user
        - Not an applicant role
        - Officer flag or scrutiny officer role
        - Applicant cannot verify their own application/document
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to access officer verification workspace.")

        if application and application.applicant and application.applicant.user_id == user.id:
            raise PermissionDenied("Separation of Duties violation: An applicant cannot verify their own application.")

        is_officer = (
            getattr(user, 'is_officer', False) or
            getattr(user, 'role', '') in (
                UserRole.SCRUTINY_OFFICER,
                UserRole.VERIFYING_AUTHORITY,
                UserRole.SANCTIONING_OFFICER,
                UserRole.ADMIN
            ) or
            user.is_superuser or user.is_staff
        )
        if not is_officer:
            raise PermissionDenied("Only authorized officers/reviewers may perform verification actions.")

    @classmethod
    def assign_queue_item(
        cls,
        queue_item_id,
        officer: User,
        assigned_to: Optional[User] = None,
        correlation_id: Optional[str] = None
    ) -> VerificationQueueItem:
        """
        Assigns a verification queue item to an authorized scrutiny officer.
        """
        cls.validate_officer_authorization(officer)
        if assigned_to:
            cls.validate_officer_authorization(assigned_to)

        target_officer = assigned_to or officer

        with transaction.atomic():
            item = VerificationQueueItem.objects.select_for_update().get(id=queue_item_id)
            cls.validate_officer_authorization(officer, item.application)

            if item.status in (VerificationStatus.VERIFIED, VerificationStatus.APPROVED, VerificationStatus.CLOSED, VerificationStatus.REJECTED):
                raise ValidationError(f"Cannot assign an already finalized item (status: '{item.status}').")

            corr_id = correlation_id or f"ASSIGN-{item.id}-{uuid.uuid4().hex[:6]}"
            old_assigned = item.assigned_to.username if item.assigned_to else None

            item.assigned_to = target_officer
            item.assigned_at = timezone.now()
            if item.status == VerificationStatus.PENDING:
                item.status = VerificationStatus.IN_REVIEW
            item.save()

            AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='VerificationQueueItem',
                entity_id=str(item.id),
                action=AuditAction.VERIFICATION_ASSIGNED,
                before_json={"assigned_to": old_assigned, "status": item.status},
                after_json={
                    "assigned_to": target_officer.username,
                    "status": item.status,
                    "correlation_id": corr_id
                },
                reason=f"Queue item assigned to {target_officer.username} by {officer.username}."
            )

        return item

    @classmethod
    def start_document_verification(
        cls,
        document_id,
        officer: User,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Marks document verification as initiated by an authorized officer.
        """
        doc = ApplicantDocument.objects.select_related('application', 'application__applicant').get(id=document_id)
        cls.validate_officer_authorization(officer, doc.application)

        corr_id = correlation_id or f"VERIF-START-{doc.id}-{uuid.uuid4().hex[:6]}"

        AuditLog.objects.create(
            actor=officer,
            actor_role=officer.role,
            entity_type='ApplicantDocument',
            entity_id=str(doc.id),
            action=AuditAction.DOCUMENT_VERIFICATION_STARTED,
            after_json={
                "document_id": str(doc.id),
                "application_id": str(doc.application_id) if doc.application_id else None,
                "officer": officer.username,
                "correlation_id": corr_id,
            },
            reason=f"Verification session initiated by officer {officer.username}."
        )

        return {
            "document_id": str(doc.id),
            "status": "VERIFICATION_STARTED",
            "correlation_id": corr_id
        }

    @classmethod
    def verify_field(
        cls,
        document_id,
        field_code: str,
        verified_value: Any,
        officer: User,
        reason: str = "",
        block_id: Optional[str] = None,
        page_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> DocumentVerificationRecord:
        """
        Explicit officer verification of an extracted or declared field.
        Converts OCR_PROVISIONAL into OFFICER_VERIFIED (Trust rank 60).
        Creates an immutable verification record and preserves evidence linkage.
        """
        cls.validate_officer_authorization(officer)

        with transaction.atomic():
            doc = ApplicantDocument.objects.select_for_update().get(id=document_id)
            cls.validate_officer_authorization(officer, doc.application)

            app = doc.application
            if not app:
                raise ValidationError("Document is not linked to an application.")

            corr_id = correlation_id or f"VERIF-FIELD-{doc.id}-{uuid.uuid4().hex[:6]}"

            field_def = ApplicationFieldDefinition.objects.filter(
                scheme_version=app.scheme_version,
                field_code=field_code
            ).first()

            doc_version = doc.versions.order_by('-version_number').first()
            ocr_result = doc.ocr_results.order_by('-created_at').first()

            ocr_block = None
            ocr_page = None
            if block_id:
                ocr_block = OCRBlock.objects.filter(id=block_id).first()
                if ocr_block:
                    ocr_page = ocr_block.page
            elif ocr_result:
                prov = ProvisionalExtractedField.objects.filter(
                    document=doc,
                    field_code=field_code
                ).order_by('-confidence').first()
                if prov and prov.ocr_block:
                    ocr_block = prov.ocr_block
                    ocr_page = prov.ocr_page

            if page_id and not ocr_page:
                ocr_page = OCRPage.objects.filter(id=page_id).first()

            # Find previous value and trust rank for historical audit comparison
            prev_val = ApplicationFieldValue.objects.filter(
                application=app,
                field_definition__field_code=field_code
            ).order_by('-created_at').first()
            prev_value_json = prev_val.value_json if prev_val else None
            prev_source = prev_val.source if prev_val else "APPLICANT_DECLARED"
            prev_trust_rank = prev_val.trust_rank if prev_val else 20

            prev_record = DocumentVerificationRecord.objects.filter(
                document=doc,
                field_code=field_code
            ).order_by('-verified_at').first()

            record_id = uuid.uuid4()
            audit_log_id = uuid.uuid4()

            # 1. Create AuditLog first to supply audit_event_id
            audit_log = AuditLog.objects.create(
                id=audit_log_id,
                actor=officer,
                actor_role=officer.role,
                entity_type='DocumentVerificationRecord',
                entity_id=str(record_id),
                action=AuditAction.FIELD_VERIFIED,
                before_json={
                    "field_code": field_code,
                    "previous_value": prev_value_json,
                    "previous_source": prev_source,
                    "previous_trust_rank": prev_trust_rank
                },
                after_json={
                    "field_code": field_code,
                    "verified_value": verified_value,
                    "verified_source": "OFFICER_VERIFIED",
                    "verified_trust_rank": 60,
                    "document_id": str(doc.id),
                    "block_id": str(ocr_block.id) if ocr_block else None,
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason or "Field verified by officer."
            )

            # 2. Create Immutable Verification Record
            record = DocumentVerificationRecord.objects.create(
                id=record_id,
                document=doc,
                document_version=doc_version,
                ocr_result=ocr_result,
                ocr_page=ocr_page,
                ocr_block=ocr_block,
                field_definition=field_def,
                field_code=field_code,
                previous_value_json=prev_value_json,
                verified_value_json=verified_value,
                previous_source=prev_source,
                previous_trust_rank=prev_trust_rank,
                verified_source='OFFICER_VERIFIED',
                verified_trust_rank=60,
                verification_status=VerificationRecordStatus.VERIFIED,
                decision_action=VerificationDecisionAction.USE_DOCUMENT_VALUE,
                officer=officer,
                officer_role=officer.role,
                reason=reason or "Officer verified field based on document evidence.",
                verification_method=VerificationMethod.DOCUMENT_EVIDENCE,
                is_current=True,
                superseded_record=prev_record,
                correlation_id=corr_id,
                audit_event_id=str(audit_log.id)
            )

            # 3. Promote trust level in ApplicationFieldValue to OFFICER (rank 60)
            if field_def:
                ApplicationFieldValue.objects.create(
                    application=app,
                    field_definition=field_def,
                    value_json=verified_value,
                    source=FieldValueSource.OFFICER_VERIFIED,
                    verification_status=FieldValueVerificationStatus.OFFICER_VERIFIED,
                    confidence=1.0,
                    entered_by=officer
                )

            # 4. Resolve any open FieldConflict on this field
            FieldConflict.objects.filter(
                application=app,
                field_code=field_code,
                status__in=[ConflictStatus.OPEN, ConflictStatus.UNDER_REVIEW]
            ).update(
                status=ConflictStatus.RESOLVED,
                resolved_by=officer,
                resolved_at=timezone.now(),
                resolution=reason or f"Resolved by officer field verification as {verified_value}"
            )

            # 5. Update open queue items targeting this field
            VerificationQueueItem.objects.filter(
                application=app,
                target_identifier__icontains=field_code,
                status__in=[VerificationStatus.PENDING, VerificationStatus.IN_REVIEW]
            ).update(
                status=VerificationStatus.VERIFIED,
                reviewed_by=officer,
                reviewed_at=timezone.now(),
                officer_remarks=reason or "Field verified by officer."
            )

        # 6. Trigger deterministic eligibility reevaluation
        try:
            RuleEvaluationService.evaluate(application=app, actor=officer, record_evaluation=True)
        except Exception:
            pass

        return record

    @classmethod
    def reject_field(
        cls,
        document_id,
        field_code: str,
        officer: User,
        reason: str,
        correlation_id: Optional[str] = None
    ) -> DocumentVerificationRecord:
        """
        Explicit officer rejection of an extracted field due to unreadability,
        fraud suspicion, or document discrepancy.
        """
        if not reason:
            raise ValidationError("A specific justification is required when rejecting a field.")

        cls.validate_officer_authorization(officer)

        with transaction.atomic():
            doc = ApplicantDocument.objects.select_for_update().get(id=document_id)
            cls.validate_officer_authorization(officer, doc.application)

            app = doc.application
            corr_id = correlation_id or f"REJECT-FIELD-{doc.id}-{uuid.uuid4().hex[:6]}"

            field_def = ApplicationFieldDefinition.objects.filter(
                scheme_version=app.scheme_version,
                field_code=field_code
            ).first()

            doc_version = doc.versions.order_by('-version_number').first()
            ocr_result = doc.ocr_results.order_by('-created_at').first()

            prev_val = ApplicationFieldValue.objects.filter(
                application=app,
                field_definition__field_code=field_code
            ).order_by('-created_at').first()

            prev_record = DocumentVerificationRecord.objects.filter(
                document=doc,
                field_code=field_code
            ).order_by('-verified_at').first()

            record_id = uuid.uuid4()
            audit_log_id = uuid.uuid4()

            audit_log = AuditLog.objects.create(
                id=audit_log_id,
                actor=officer,
                actor_role=officer.role,
                entity_type='DocumentVerificationRecord',
                entity_id=str(record_id),
                action=AuditAction.FIELD_REJECTED,
                before_json={
                    "field_code": field_code,
                    "previous_value": prev_val.value_json if prev_val else None,
                    "previous_source": prev_val.source if prev_val else "APPLICANT_DECLARED",
                    "previous_trust_rank": prev_val.trust_rank if prev_val else 20
                },
                after_json={
                    "field_code": field_code,
                    "verification_status": "REJECTED",
                    "reason": reason,
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason
            )

            record = DocumentVerificationRecord.objects.create(
                id=record_id,
                document=doc,
                document_version=doc_version,
                ocr_result=ocr_result,
                field_definition=field_def,
                field_code=field_code,
                previous_value_json=prev_val.value_json if prev_val else None,
                verified_value_json=None,
                previous_source=prev_val.source if prev_val else "APPLICANT_DECLARED",
                previous_trust_rank=prev_val.trust_rank if prev_val else 20,
                verified_source="OFFICER_VERIFIED",
                verified_trust_rank=60,
                verification_status=VerificationRecordStatus.REJECTED,
                decision_action=VerificationDecisionAction.REQUEST_CORRECTION,
                officer=officer,
                officer_role=officer.role,
                reason=reason,
                verification_method=VerificationMethod.MANUAL_REVIEW,
                is_current=True,
                superseded_record=prev_record,
                correlation_id=corr_id,
                audit_event_id=str(audit_log.id)
            )

            VerificationQueueItem.objects.filter(
                application=app,
                target_identifier__icontains=field_code,
                status__in=[VerificationStatus.PENDING, VerificationStatus.IN_REVIEW]
            ).update(
                status=VerificationStatus.DEFECT_FLAGGED,
                reviewed_by=officer,
                reviewed_at=timezone.now(),
                officer_remarks=reason
            )

        # Trigger eligibility reevaluation
        try:
            RuleEvaluationService.evaluate(application=app, actor=officer, record_evaluation=True)
        except Exception:
            pass

        return record

    @classmethod
    def verify_document(
        cls,
        document_id,
        officer: User,
        reason: str = "Document documentary evidence inspected and accepted by officer.",
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Officer explicitly marks document as VERIFIED_DOCUMENT evidence.
        Document security lifecycle (SAFE) remains strictly independent from verification.
        SAFE = Passed file security / content ingestion controls.
        VERIFIED_DOCUMENT = Authorized officer accepted document as authentic evidence.
        """
        cls.validate_officer_authorization(officer)

        with transaction.atomic():
            doc = ApplicantDocument.objects.select_for_update().get(id=document_id)
            cls.validate_officer_authorization(officer, doc.application)

            app = doc.application
            corr_id = correlation_id or f"VERIF-DOC-{doc.id}-{uuid.uuid4().hex[:6]}"

            # Independent security lifecycle verification:
            # SAFE does not mean VERIFIED, but document must be in safe/processable lifecycle state
            if doc.lifecycle_status in (DocumentLifecycleStatus.REJECTED, DocumentLifecycleStatus.QUARANTINED):
                raise ValidationError(f"Cannot verify document in security state '{doc.lifecycle_status}'.")

            doc.is_verified_by_officer = True

            # If document lifecycle status is SAFE, VERIFICATION_PENDING, or PROCESSED, promote to VERIFIED
            if doc.lifecycle_status in (
                DocumentLifecycleStatus.SAFE,
                DocumentLifecycleStatus.VERIFICATION_PENDING,
                DocumentLifecycleStatus.PROCESSED
            ):
                doc.lifecycle_status = DocumentLifecycleStatus.VERIFIED
            doc.save()

            doc_version = doc.versions.order_by('-version_number').first()
            ocr_result = doc.ocr_results.order_by('-created_at').first()

            audit_log = AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='ApplicantDocument',
                entity_id=str(doc.id),
                action=AuditAction.DOCUMENT_EVIDENCE_VERIFIED,
                after_json={
                    "document_id": str(doc.id),
                    "application_id": str(app.id) if app else None,
                    "document_type": doc.document_type,
                    "status": "VERIFIED_DOCUMENT",
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason
            )

            # Create document-level verification record
            record = DocumentVerificationRecord.objects.create(
                document=doc,
                document_version=doc_version,
                ocr_result=ocr_result,
                field_code="document_level",
                previous_value_json={"lifecycle_status": doc.lifecycle_status},
                verified_value_json={"is_verified_by_officer": True, "lifecycle_status": doc.lifecycle_status},
                previous_source="VERIFIED_DOCUMENT",
                previous_trust_rank=30,
                verified_source="VERIFIED_DOCUMENT",
                verified_trust_rank=40,
                verification_status=VerificationRecordStatus.VERIFIED,
                decision_action=VerificationDecisionAction.VERIFIED_DOCUMENT,
                officer=officer,
                officer_role=officer.role,
                reason=reason,
                verification_method=VerificationMethod.DOCUMENT_EVIDENCE,
                is_current=True,
                correlation_id=corr_id,
                audit_event_id=str(audit_log.id)
            )

            # Update open verification queue items targeting this document
            if app:
                v_items = VerificationQueueItem.objects.filter(
                    application=app,
                    status__in=[VerificationStatus.PENDING, VerificationStatus.IN_REVIEW]
                )
                for vi in v_items:
                    if vi.document_id == doc.id or str(doc.id) in vi.target_identifier:
                        vi.status = VerificationStatus.VERIFIED
                        vi.reviewed_by = officer
                        vi.reviewed_at = timezone.now()
                        vi.officer_remarks = reason
                        vi.save()

        # Trigger deterministic eligibility reevaluation
        if app:
            try:
                RuleEvaluationService.evaluate(application=app, actor=officer, record_evaluation=True)
            except Exception:
                pass

        return {
            "document_id": str(doc.id),
            "status": "VERIFIED",
            "verification_status": "VERIFIED_DOCUMENT",
            "is_verified_by_officer": True,
            "record_id": str(record.id),
            "audit_event_id": str(audit_log.id)
        }

    @classmethod
    def resolve_field_conflict(
        cls,
        queue_item_id,
        decision_action: str,
        *args,
        officer: Optional[User] = None,
        reason: str = "",
        chosen_value: Optional[Any] = None,
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> DocumentVerificationRecord:
        """
        Resolves a material discrepancy between applicant declaration and document OCR evidence.
        Uses database row locking (select_for_update) to prevent conflicting concurrent adjudications.
        Officer explicitly chooses the resolution supported by evidence:
        - USE_APPLICANT_DECLARATION
        - USE_DOCUMENT_VALUE
        - REQUEST_CORRECTION
        - NEEDS_MORE_EVIDENCE
        - ESCALATE
        """
        if len(args) >= 3:
            chosen_value = args[0]
            officer = args[1]
            reason = args[2]
        elif len(args) == 2:
            if isinstance(args[0], User):
                officer = args[0]
                reason = args[1]
            else:
                chosen_value = args[0]
                officer = args[1]
        elif len(args) == 1:
            if isinstance(args[0], User):
                officer = args[0]
            else:
                chosen_value = args[0]

        if not officer:
            raise ValidationError("Officer identity required to resolve conflict.")

        cls.validate_officer_authorization(officer)

        if decision_action not in VerificationDecisionAction.values:
            raise ValidationError(f"Invalid decision_action '{decision_action}'.")

        corr_id = correlation_id or f"RESOLVE-CONFLICT-{queue_item_id}-{uuid.uuid4().hex[:6]}"

        with transaction.atomic():
            # Concurrency Protection: Lock the row
            queue_item = VerificationQueueItem.objects.select_for_update().get(id=queue_item_id)
            cls.validate_officer_authorization(officer, queue_item.application)

            # Prevent double-finalization
            if queue_item.status in (VerificationStatus.VERIFIED, VerificationStatus.APPROVED, VerificationStatus.CLOSED, VerificationStatus.REJECTED):
                raise ValidationError(f"Cannot resolve an already finalized verification item (status: '{queue_item.status}').")

            if chosen_value is None and queue_item.current_evidence_json:
                if decision_action == VerificationDecisionAction.USE_DOCUMENT_VALUE:
                    chosen_value = (
                        queue_item.current_evidence_json.get('ocr_provisional') or
                        queue_item.current_evidence_json.get('document') or
                        queue_item.current_evidence_json.get('ocr')
                    )
                elif decision_action == VerificationDecisionAction.USE_APPLICANT_DECLARATION:
                    chosen_value = (
                        queue_item.current_evidence_json.get('declared') or
                        queue_item.current_evidence_json.get('applicant')
                    )

            app = queue_item.application
            field_code = queue_item.ai_assistance_json.get("field_code") or queue_item.target_identifier
            if field_code.startswith("CONFLICT_"):
                # Clean prefix if format is CONFLICT_<field>_<uuid>
                parts = field_code.split("_")
                if len(parts) >= 2:
                    field_code = parts[1]

            field_def = ApplicationFieldDefinition.objects.filter(
                scheme_version=app.scheme_version,
                field_code=field_code
            ).first()

            doc = queue_item.document or ApplicantDocument.objects.filter(application=app).order_by('-uploaded_at').first()
            doc_version = doc.versions.order_by('-version_number').first() if doc else None
            ocr_result = doc.ocr_results.order_by('-created_at').first() if doc else None

            prev_val = ApplicationFieldValue.objects.filter(
                application=app,
                field_definition__field_code=field_code
            ).order_by('-created_at').first()

            prev_value_json = prev_val.value_json if prev_val else None
            prev_source = prev_val.source if prev_val else "APPLICANT_DECLARED"
            prev_trust_rank = prev_val.trust_rank if prev_val else 20

            status = VerificationRecordStatus.VERIFIED
            if decision_action in (VerificationDecisionAction.REQUEST_CORRECTION, VerificationDecisionAction.NEEDS_MORE_EVIDENCE, VerificationDecisionAction.NEEDS_REVIEW):
                status = VerificationRecordStatus.NEEDS_REVIEW
            elif decision_action == VerificationDecisionAction.ESCALATE:
                status = VerificationRecordStatus.NEEDS_REVIEW

            audit_log = AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='VerificationQueueItem',
                entity_id=str(queue_item.id),
                action=AuditAction.FIELD_CONFLICT_RESOLVED,
                before_json={
                    "status": queue_item.status,
                    "field_code": field_code,
                    "conflict_details": queue_item.ai_assistance_json,
                    "previous_value": prev_value_json,
                    "previous_source": prev_source,
                    "previous_trust_rank": prev_trust_rank
                },
                after_json={
                    "field_code": field_code,
                    "decision_action": decision_action,
                    "resolved_value": chosen_value,
                    "new_source": "OFFICER_VERIFIED" if decision_action in (VerificationDecisionAction.USE_APPLICANT_DECLARATION, VerificationDecisionAction.USE_DOCUMENT_VALUE) else prev_source,
                    "new_trust_rank": 60 if decision_action in (VerificationDecisionAction.USE_APPLICANT_DECLARATION, VerificationDecisionAction.USE_DOCUMENT_VALUE) else prev_trust_rank,
                    "queue_item_status": queue_item.status,
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason
            )

            record = DocumentVerificationRecord.objects.create(
                document=doc,
                document_version=doc_version,
                ocr_result=ocr_result,
                field_definition=field_def,
                field_code=field_code,
                previous_value_json=prev_value_json,
                verified_value_json=chosen_value,
                previous_source=prev_source,
                previous_trust_rank=prev_trust_rank,
                verified_source='OFFICER_VERIFIED' if decision_action in (VerificationDecisionAction.USE_APPLICANT_DECLARATION, VerificationDecisionAction.USE_DOCUMENT_VALUE) else prev_source,
                verified_trust_rank=60 if decision_action in (VerificationDecisionAction.USE_APPLICANT_DECLARATION, VerificationDecisionAction.USE_DOCUMENT_VALUE) else prev_trust_rank,
                verification_status=status,
                decision_action=decision_action,
                officer=officer,
                officer_role=officer.role,
                reason=reason,
                verification_method=VerificationMethod.CONFLICT_RESOLUTION,
                is_current=True,
                correlation_id=corr_id,
                audit_event_id=str(audit_log.id)
            )

            # If resolved with a definitive value, promote to OFFICER rank (60)
            if decision_action in (VerificationDecisionAction.USE_APPLICANT_DECLARATION, VerificationDecisionAction.USE_DOCUMENT_VALUE) and field_def:
                ApplicationFieldValue.objects.create(
                    application=app,
                    field_definition=field_def,
                    value_json=chosen_value,
                    source=FieldValueSource.OFFICER_VERIFIED,
                    verification_status=FieldValueVerificationStatus.OFFICER_VERIFIED,
                    confidence=1.0,
                    entered_by=officer
                )
                queue_item.status = VerificationStatus.VERIFIED
            elif decision_action == VerificationDecisionAction.REQUEST_CORRECTION:
                queue_item.status = VerificationStatus.DEFECT_FLAGGED
            elif decision_action == VerificationDecisionAction.NEEDS_MORE_EVIDENCE:
                queue_item.status = VerificationStatus.NEEDS_MORE_EVIDENCE
            elif decision_action == VerificationDecisionAction.ESCALATE:
                queue_item.status = VerificationStatus.ESCALATED
            else:
                queue_item.status = VerificationStatus.PENDING

            queue_item.reviewed_by = officer
            queue_item.reviewed_at = timezone.now()
            queue_item.officer_remarks = reason
            queue_item.save()

            # Resolve linked FieldConflict if present
            FieldConflict.objects.filter(
                application=app,
                field_code=field_code,
                status__in=[ConflictStatus.OPEN, ConflictStatus.UNDER_REVIEW]
            ).update(
                status=ConflictStatus.RESOLVED if queue_item.status == VerificationStatus.VERIFIED else ConflictStatus.UNDER_REVIEW,
                resolved_by=officer if queue_item.status == VerificationStatus.VERIFIED else None,
                resolved_at=timezone.now() if queue_item.status == VerificationStatus.VERIFIED else None,
                resolution=reason
            )

        # Trigger deterministic eligibility reevaluation
        try:
            RuleEvaluationService.evaluate(application=app, actor=officer, record_evaluation=True)
        except Exception:
            pass

        return record

    @classmethod
    def request_more_evidence(
        cls,
        queue_item_id,
        officer: User,
        reason: str,
        correlation_id: Optional[str] = None
    ) -> VerificationQueueItem:
        """
        Marks verification queue item as NEEDS_MORE_EVIDENCE with required remarks.
        """
        cls.validate_officer_authorization(officer)
        if not reason:
            raise ValidationError("A specific reason is required to request additional evidence.")

        with transaction.atomic():
            item = VerificationQueueItem.objects.select_for_update().get(id=queue_item_id)
            cls.validate_officer_authorization(officer, item.application)

            if item.status in (VerificationStatus.VERIFIED, VerificationStatus.APPROVED, VerificationStatus.CLOSED, VerificationStatus.REJECTED):
                raise ValidationError(f"Cannot request more evidence on an already finalized item (status: '{item.status}').")

            corr_id = correlation_id or f"NEEDS-EVID-{item.id}-{uuid.uuid4().hex[:6]}"
            old_status = item.status

            item.status = VerificationStatus.NEEDS_MORE_EVIDENCE
            item.officer_remarks = reason
            item.reviewed_by = officer
            item.reviewed_at = timezone.now()
            item.save()

            AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='VerificationQueueItem',
                entity_id=str(item.id),
                action=AuditAction.TRANSITION,
                before_json={"status": old_status},
                after_json={"status": VerificationStatus.NEEDS_MORE_EVIDENCE, "correlation_id": corr_id},
                reason=reason
            )

        return item

    @classmethod
    def escalate_queue_item(
        cls,
        queue_item_id,
        officer: User,
        reason: str,
        correlation_id: Optional[str] = None
    ) -> VerificationQueueItem:
        """
        Escalates a verification queue item to supervisory scrutiny authority.
        """
        cls.validate_officer_authorization(officer)
        if not reason:
            raise ValidationError("A specific reason is required to escalate an item.")

        with transaction.atomic():
            item = VerificationQueueItem.objects.select_for_update().get(id=queue_item_id)
            cls.validate_officer_authorization(officer, item.application)

            if item.status in (VerificationStatus.VERIFIED, VerificationStatus.APPROVED, VerificationStatus.CLOSED, VerificationStatus.REJECTED):
                raise ValidationError(f"Cannot escalate an already finalized item (status: '{item.status}').")

            corr_id = correlation_id or f"ESCALATE-{item.id}-{uuid.uuid4().hex[:6]}"
            old_status = item.status

            item.status = VerificationStatus.ESCALATED
            item.priority = VerificationPriority.HIGH
            item.officer_remarks = reason
            item.reviewed_by = officer
            item.reviewed_at = timezone.now()
            item.save()

            AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='VerificationQueueItem',
                entity_id=str(item.id),
                action=AuditAction.VERIFICATION_ESCALATED,
                before_json={"status": old_status},
                after_json={
                    "status": VerificationStatus.ESCALATED,
                    "priority": VerificationPriority.HIGH,
                    "correlation_id": corr_id
                },
                reason=reason
            )

        return item

    @classmethod
    def reopen_verification(
        cls,
        document_id,
        officer: User,
        reason: str,
        correlation_id: Optional[str] = None
    ) -> DocumentVerificationRecord:
        """
        Reopens a previously completed or verified document for re-investigation.
        Creates a new immutable verification record without overwriting past history.
        """
        doc = ApplicantDocument.objects.select_related('application', 'application__applicant').get(id=document_id)
        cls.validate_officer_authorization(officer, doc.application)

        if not reason:
            raise ValidationError("A justification reason is required to reopen document verification.")

        corr_id = correlation_id or f"REOPEN-VERIF-{doc.id}-{uuid.uuid4().hex[:6]}"

        latest_record = DocumentVerificationRecord.objects.filter(
            document=doc,
            is_current=True
        ).first()

        with transaction.atomic():
            audit_log = AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='ApplicantDocument',
                entity_id=str(doc.id),
                action=AuditAction.DOCUMENT_VERIFICATION_REOPENED,
                before_json={
                    "previous_record_id": str(latest_record.id) if latest_record else None,
                    "previous_status": latest_record.verification_status if latest_record else None
                },
                after_json={
                    "status": "NEEDS_REVIEW",
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason
            )

            new_record = DocumentVerificationRecord.objects.create(
                document=doc,
                document_version=latest_record.document_version if latest_record else None,
                ocr_result=latest_record.ocr_result if latest_record else None,
                field_definition=latest_record.field_definition if latest_record else None,
                field_code=latest_record.field_code if latest_record else "document_level",
                previous_value_json=latest_record.verified_value_json if latest_record else None,
                verified_value_json=None,
                previous_source=latest_record.verified_source if latest_record else "VERIFIED_DOCUMENT",
                previous_trust_rank=latest_record.verified_trust_rank if latest_record else 40,
                verified_source="OFFICER_VERIFIED",
                verified_trust_rank=60,
                verification_status=VerificationRecordStatus.NEEDS_REVIEW,
                decision_action=VerificationDecisionAction.NEEDS_REVIEW,
                officer=officer,
                officer_role=officer.role,
                reason=reason,
                verification_method=VerificationMethod.REOPENED,
                is_current=True,
                superseded_record=latest_record,
                correlation_id=corr_id,
                audit_event_id=str(audit_log.id)
            )

            # Reopen any closed verification queue item for this document
            if doc.application:
                VerificationQueueItem.objects.filter(
                    application=doc.application,
                    target_identifier__icontains=str(doc.id)
                ).update(
                    status=VerificationStatus.IN_REVIEW,
                    officer_remarks=f"Reopened by {officer.username}: {reason}"
                )

        return new_record

    @classmethod
    def complete_document_verification(
        cls,
        document_id,
        officer: User,
        reason: str = "",
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Marks document verification as formally completed by an authorized officer.
        """
        return cls.verify_document(
            document_id=document_id,
            officer=officer,
            reason=reason or "Document verification completed by officer.",
            correlation_id=correlation_id
        )

    @classmethod
    def get_verification_detail(cls, queue_item_id: str, officer: User) -> Dict[str, Any]:
        """
        Comprehensive verification detail workspace payload returning:
        A. Applicant information
        B. Application information
        C. Document preview & documents list
        D. OCR extracted text
        E. Extracted fields (with bounding boxes and conflict flags)
        F. Applicant-declared values
        G. Official/system values where available
        H. Conflicts
        I. Verification history
        J. Current eligibility impact
        """
        item = VerificationQueueItem.objects.select_related(
            'application', 'application__applicant', 'application__applicant__user',
            'application__scheme_version', 'application__scheme_version__scheme',
            'document', 'assigned_to', 'reviewed_by'
        ).get(id=queue_item_id)

        cls.validate_officer_authorization(officer, item.application)

        app = item.application
        applicant_profile = app.applicant
        user = applicant_profile.user if applicant_profile else None
        scheme_version = app.scheme_version
        scheme = scheme_version.scheme if scheme_version else None

        # A. Applicant Information
        applicant_info = {
            "id": str(applicant_profile.id) if applicant_profile else None,
            "username": user.username if user else "",
            "full_name": user.get_full_name() if user else "",
            "email": user.email if user else "",
            "community": getattr(applicant_profile, 'community', 'ST'),
            "category": getattr(applicant_profile, 'category', 'ST'),
            "date_of_birth": str(getattr(applicant_profile, 'date_of_birth', '')) if getattr(applicant_profile, 'date_of_birth', None) else None,
            "gender": getattr(applicant_profile, 'gender', ''),
            "state_of_residence": getattr(applicant_profile, 'state_of_residence', '')
        }

        # B. Application Information
        application_info = {
            "id": str(app.id),
            "application_number": app.application_number,
            "scheme_code": scheme.code if scheme else "",
            "scheme_name": scheme.name if scheme else "",
            "academic_year": scheme_version.academic_year if scheme_version else "",
            "status": app.current_state.code if app.current_state else "UNKNOWN",
            "submission_date": app.created_at.isoformat() if app.created_at else None,
            "is_synthetic": app.is_synthetic
        }

        # C. Documents List & Previews
        docs_qs = ApplicantDocument.objects.filter(application=app).order_by('-uploaded_at')
        target_doc = item.document or docs_qs.first()

        documents_list = []
        for d in docs_qs:
            documents_list.append({
                "id": str(d.id),
                "document_type": d.document_type,
                "file_name": d.file_name or d.original_filename,
                "lifecycle_status": d.lifecycle_status,
                "is_verified_by_officer": d.is_verified_by_officer,
                "file_size_bytes": d.file_size_bytes,
                "detected_mime_type": d.detected_mime_type,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
                "is_target": bool(target_doc and d.id == target_doc.id)
            })

        # D. OCR Extracted Text
        latest_ocr = target_doc.ocr_results.order_by('-created_at').first() if target_doc else None
        ocr_full_text = latest_ocr.full_text if latest_ocr else ""

        # E & F & G. Extracted Fields vs Declared Values vs Official Values
        declared_map = {}
        verified_map = {}
        official_map = {}

        for val in ApplicationFieldValue.objects.filter(application=app).select_related('field_definition').order_by('created_at'):
            code = val.field_definition.field_code
            if val.source in (FieldValueSource.OFFICER_VERIFIED, 'OFFICER'):
                verified_map[code] = val.value_json
            elif val.source in (FieldValueSource.OFFICIAL_INTEGRATION, 'DIGILOCKER'):
                official_map[code] = val.value_json
            elif val.source in (FieldValueSource.APPLICANT_DECLARED, 'APPLICANT'):
                declared_map[code] = val.value_json

        # Fetch provisional fields from document
        extracted_fields = []
        if target_doc:
            prov_fields = ProvisionalExtractedField.objects.filter(
                document=target_doc
            ).select_related('ocr_block', 'ocr_page')

            for pf in prov_fields:
                code = pf.field_code
                decl_val = declared_map.get(code)
                verif_val = verified_map.get(code)
                off_val = official_map.get(code)
                extracted_val = pf.normalized_value if pf.normalized_value is not None else pf.raw_value

                has_conflict = False
                if decl_val is not None and extracted_val is not None:
                    try:
                        v1 = float(decl_val)
                        v2 = float(extracted_val)
                        diff = abs(v1 - v2)
                        has_conflict = (diff > max(1000.0, 0.05 * v1))
                    except (ValueError, TypeError):
                        has_conflict = (str(decl_val).strip() != str(extracted_val).strip())

                bbox = None
                poly = None
                block_id = None
                page_num = pf.ocr_page.page_number if pf.ocr_page else pf.page_number
                if pf.ocr_block:
                    b = pf.ocr_block
                    block_id = str(b.id)
                    bbox = {
                        "x": b.bbox_x,
                        "y": b.bbox_y,
                        "width": b.bbox_width,
                        "height": b.bbox_height
                    }
                    poly = b.polygon

                extracted_fields.append({
                    "field_code": code,
                    "field_label": pf.field_label or code.replace('_', ' ').title(),
                    "declared_value": decl_val,
                    "ocr_value": pf.normalized_value if pf.normalized_value is not None else pf.raw_value,
                    "verified_value": verif_val,
                    "official_value": off_val,
                    "verification_status": "VERIFIED" if verif_val is not None else ("CONFLICT" if has_conflict else "PENDING"),
                    "confidence": pf.confidence,
                    "page_number": page_num,
                    "bbox": bbox,
                    "polygon": poly,
                    "ocr_block_id": block_id,
                    "has_conflict": has_conflict,
                    "trust_level": pf.trust_level
                })

        # H. Conflicts
        conflicts_qs = FieldConflict.objects.filter(application=app).order_by('-created_at')
        conflicts_data = []
        for c in conflicts_qs:
            conflicts_data.append({
                "id": str(c.id),
                "field_code": c.field_code,
                "values": c.values_json,
                "source_values": c.source_values,
                "severity": c.severity,
                "status": c.status,
                "resolution": c.resolution,
                "created_at": c.created_at.isoformat() if c.created_at else None
            })

        # I. Verification History
        history_qs = DocumentVerificationRecord.objects.filter(
            document__application=app
        ).select_related('officer', 'document').order_by('-verified_at')
        history_data = []
        for h in history_qs:
            history_data.append({
                "id": str(h.id),
                "document_id": str(h.document_id),
                "field_code": h.field_code,
                "previous_value": h.previous_value_json,
                "verified_value": h.verified_value_json,
                "previous_source": h.previous_source,
                "previous_trust_rank": h.previous_trust_rank,
                "verified_source": h.verified_source,
                "verified_trust_rank": h.verified_trust_rank,
                "verification_status": h.verification_status,
                "decision_action": h.decision_action,
                "officer_name": h.officer.username if h.officer else "System",
                "officer_role": h.officer_role,
                "verified_at": h.verified_at.isoformat() if h.verified_at else None,
                "reason": h.reason,
                "audit_event_id": h.audit_event_id
            })

        # J. Current Eligibility Impact
        latest_eval = app.eligibility_evaluations.order_by('-evaluated_at').first()
        eligibility_impact = None
        if latest_eval:
            eligibility_impact = {
                "evaluation_id": str(latest_eval.id),
                "evaluated_at": latest_eval.evaluated_at.isoformat() if latest_eval.evaluated_at else None,
                "engine_version": latest_eval.engine_version,
                "result_status": latest_eval.result.get("status") if isinstance(latest_eval.result, dict) else None,
                "is_eligible": latest_eval.result.get("is_eligible") if isinstance(latest_eval.result, dict) else None,
                "summary": latest_eval.result.get("summary") if isinstance(latest_eval.result, dict) else None,
                "rule_evaluations": latest_eval.result.get("evaluations", []) if isinstance(latest_eval.result, dict) else []
            }
        else:
            # Generate a live deterministic evaluation preview
            try:
                eval_res = RuleEvaluationService.evaluate(application=app, actor=officer, record_evaluation=False)
                eligibility_impact = {
                    "evaluation_id": "PREVIEW",
                    "evaluated_at": timezone.now().isoformat(),
                    "engine_version": RuleEvaluationService.ENGINE_VERSION,
                    "result_status": eval_res.get("status"),
                    "is_eligible": eval_res.get("is_eligible"),
                    "summary": eval_res.get("summary"),
                    "rule_evaluations": eval_res.get("evaluations", [])
                }
            except Exception:
                eligibility_impact = {"status": "UNEVALUATED"}

        return {
            "queue_item": {
                "id": str(item.id),
                "item_type": item.item_type,
                "priority": item.priority,
                "status": item.status,
                "confidence_score": item.confidence_score,
                "conflict_type": item.conflict_type,
                "officer_remarks": item.officer_remarks,
                "assigned_to": item.assigned_to.username if item.assigned_to else None,
                "assigned_at": item.assigned_at.isoformat() if item.assigned_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "ai_assistance": item.ai_assistance_json
            },
            "applicant": applicant_info,
            "application": application_info,
            "documents": documents_list,
            "target_document_id": str(target_doc.id) if target_doc else None,
            "ocr_extracted_text": ocr_full_text,
            "extracted_fields": extracted_fields,
            "declared_values": declared_map,
            "verified_values": verified_map,
            "official_values": official_map,
            "conflicts": conflicts_data,
            "verification_history": history_data,
            "eligibility_impact": eligibility_impact
        }
