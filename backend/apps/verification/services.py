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
    FieldValueSource, FieldValueVerificationStatus, FieldDataType
)
from apps.documents.models import (
    ApplicantDocument, DocumentVersion, OCRResult, OCRPage, OCRBlock,
    ProvisionalExtractedField, DocumentLifecycleStatus
)
from .models import (
    VerificationQueueItem, VerificationStatus, VerificationItemType,
    DocumentVerificationRecord, VerificationRecordStatus,
    VerificationDecisionAction, VerificationMethod
)


class DocumentVerificationService:
    """
    Core Phase 8 Service for Human-in-the-Loop Document Verification.
    
    Principles:
    1. The officer verifies evidence; the officer does NOT rewrite history.
    2. The officer does NOT directly edit original documents.
    3. The officer does NOT bypass the scheme rule engine.
    4. Separation of duties: Applicants cannot verify their own documents.
    5. Immutable verification events are created for every action.
    6. Verified evidence increases field trust to OFFICER_VERIFIED (rank 50).
    7. Eligibility evaluation remains strictly deterministic through RuleEvaluationService.
    """

    @classmethod
    def validate_officer_authorization(cls, user: User, application: Application):
        """
        Enforces strict RBAC and Separation of Duties:
        - Authenticated
        - Reviewer / Officer role
        - Applicant cannot verify their own application/document
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to perform document verification.")

        if getattr(user, 'role', '') == UserRole.APPLICANT or not getattr(user, 'is_officer', False):
            raise PermissionDenied("Only authorized officers/reviewers may perform document verification.")

        if application and application.applicant and application.applicant.user_id == user.id:
            raise PermissionDenied("Separation of Duties violation: An applicant cannot verify their own application.")

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
        Converts OCR_PROVISIONAL into OFFICER_VERIFIED (Trust rank 50).
        Creates an immutable verification record and preserves evidence linkage.
        """
        doc = ApplicantDocument.objects.select_related('application', 'application__applicant', 'application__scheme_version').get(id=document_id)
        cls.validate_officer_authorization(officer, doc.application)

        app = doc.application
        if not app:
            raise ValidationError("Document is not linked to an application.")

        corr_id = correlation_id or f"VERIF-FIELD-{doc.id}-{uuid.uuid4().hex[:6]}"

        # Resolve field definition
        field_def = ApplicationFieldDefinition.objects.filter(
            scheme_version=app.scheme_version,
            field_code=field_code
        ).first()

        # Resolve document version and active OCR entities
        doc_version = doc.versions.order_by('-version_number').first()
        ocr_result = doc.ocr_results.order_by('-created_at').first()

        ocr_block = None
        ocr_page = None
        if block_id:
            ocr_block = OCRBlock.objects.filter(id=block_id).first()
            if ocr_block:
                ocr_page = ocr_block.page
        elif ocr_result:
            # Fallback to matching provisional field block
            prov = ProvisionalExtractedField.objects.filter(
                document=doc,
                field_code=field_code
            ).order_by('-confidence').first()
            if prov and prov.ocr_block:
                ocr_block = prov.ocr_block
                ocr_page = prov.ocr_page

        if page_id and not ocr_page:
            ocr_page = OCRPage.objects.filter(id=page_id).first()

        # Find previous effective value for historical audit comparison
        prev_val = ApplicationFieldValue.objects.filter(
            application=app,
            field_definition__field_code=field_code
        ).order_by('-created_at').first()
        prev_value_json = prev_val.value_json if prev_val else None

        with transaction.atomic():
            # Discover and link previous verification record for this field
            prev_record = DocumentVerificationRecord.objects.filter(
                document=doc,
                field_code=field_code
            ).order_by('-verified_at').first()

            # 1. Create Immutable Verification Record
            record = DocumentVerificationRecord.objects.create(
                document=doc,
                document_version=doc_version,
                ocr_result=ocr_result,
                ocr_page=ocr_page,
                ocr_block=ocr_block,
                field_definition=field_def,
                field_code=field_code,
                previous_value_json=prev_value_json,
                verified_value_json=verified_value,
                verification_status=VerificationRecordStatus.VERIFIED,
                decision_action=VerificationDecisionAction.USE_DOCUMENT_VALUE,
                officer=officer,
                officer_role=officer.role,
                reason=reason or "Officer verified field based on document evidence.",
                verification_method=VerificationMethod.DOCUMENT_EVIDENCE,
                is_current=True,
                superseded_record=prev_record,
                correlation_id=corr_id
            )

            # 2. Promote trust level in ApplicationFieldValue to OFFICER (rank 50)
            if field_def:
                ApplicationFieldValue.objects.create(
                    application=app,
                    field_definition=field_def,
                    value_json=verified_value,
                    source=FieldValueSource.OFFICER,
                    verification_status=FieldValueVerificationStatus.OFFICER_VERIFIED,
                    confidence=1.0,
                    entered_by=officer
                )

            # 3. Emit Statutory Audit Log
            AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='DocumentVerificationRecord',
                entity_id=str(record.id),
                action=AuditAction.FIELD_VERIFIED,
                before_json={
                    "field_code": field_code,
                    "previous_value": prev_value_json
                },
                after_json={
                    "field_code": field_code,
                    "verified_value": verified_value,
                    "document_id": str(doc.id),
                    "block_id": str(ocr_block.id) if ocr_block else None,
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason or "Field verified by officer."
            )

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
        doc = ApplicantDocument.objects.select_related('application', 'application__applicant').get(id=document_id)
        cls.validate_officer_authorization(officer, doc.application)

        if not reason:
            raise ValidationError("A specific justification is required when rejecting a field.")

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

        with transaction.atomic():
            prev_record = DocumentVerificationRecord.objects.filter(
                document=doc,
                field_code=field_code
            ).order_by('-verified_at').first()

            record = DocumentVerificationRecord.objects.create(
                document=doc,
                document_version=doc_version,
                ocr_result=ocr_result,
                field_definition=field_def,
                field_code=field_code,
                previous_value_json=prev_val.value_json if prev_val else None,
                verified_value_json=None,
                verification_status=VerificationRecordStatus.REJECTED,
                decision_action=VerificationDecisionAction.REQUEST_CORRECTION,
                officer=officer,
                officer_role=officer.role,
                reason=reason,
                verification_method=VerificationMethod.MANUAL_REVIEW,
                is_current=True,
                superseded_record=prev_record,
                correlation_id=corr_id
            )

            AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='DocumentVerificationRecord',
                entity_id=str(record.id),
                action=AuditAction.FIELD_REJECTED,
                before_json={
                    "field_code": field_code,
                    "previous_value": prev_val.value_json if prev_val else None
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

        return record

    @classmethod
    def resolve_field_conflict(
        cls,
        queue_item_id,
        decision_action: str,
        chosen_value: Any,
        officer: User,
        reason: str,
        correlation_id: Optional[str] = None
    ) -> DocumentVerificationRecord:
        """
        Resolves a material field conflict where applicant declaration differs from OCR evidence.
        Officer explicitly chooses the resolution supported by evidence:
        - USE_APPLICANT_DECLARATION
        - USE_DOCUMENT_VALUE
        - REQUEST_CORRECTION
        - NEEDS_REVIEW
        """
        queue_item = VerificationQueueItem.objects.select_related('application', 'application__applicant', 'application__scheme_version').get(id=queue_item_id)
        app = queue_item.application
        cls.validate_officer_authorization(officer, app)

        if decision_action not in VerificationDecisionAction.values:
            raise ValidationError(f"Invalid decision_action '{decision_action}'.")

        corr_id = correlation_id or f"RESOLVE-CONFLICT-{queue_item.id}-{uuid.uuid4().hex[:6]}"

        # Target field code from queue item assistance json or target identifier
        field_code = queue_item.ai_assistance_json.get("field_code") or queue_item.target_identifier
        field_def = ApplicationFieldDefinition.objects.filter(
            scheme_version=app.scheme_version,
            field_code=field_code
        ).first()

        doc = ApplicantDocument.objects.filter(application=app).order_by('-uploaded_at').first()
        doc_version = doc.versions.order_by('-version_number').first() if doc else None
        ocr_result = doc.ocr_results.order_by('-created_at').first() if doc else None

        prev_val = ApplicationFieldValue.objects.filter(
            application=app,
            field_definition__field_code=field_code
        ).order_by('-created_at').first()

        with transaction.atomic():
            status = VerificationRecordStatus.VERIFIED
            if decision_action in (VerificationDecisionAction.REQUEST_CORRECTION, VerificationDecisionAction.NEEDS_REVIEW):
                status = VerificationRecordStatus.NEEDS_REVIEW

            record = DocumentVerificationRecord.objects.create(
                document=doc,
                document_version=doc_version,
                ocr_result=ocr_result,
                field_definition=field_def,
                field_code=field_code,
                previous_value_json=prev_val.value_json if prev_val else None,
                verified_value_json=chosen_value,
                verification_status=status,
                decision_action=decision_action,
                officer=officer,
                officer_role=officer.role,
                reason=reason,
                verification_method=VerificationMethod.CONFLICT_RESOLUTION,
                is_current=True,
                correlation_id=corr_id
            )

            # If resolved with a definitive value, promote to OFFICER rank (50)
            if decision_action in (VerificationDecisionAction.USE_APPLICANT_DECLARATION, VerificationDecisionAction.USE_DOCUMENT_VALUE) and field_def:
                ApplicationFieldValue.objects.create(
                    application=app,
                    field_definition=field_def,
                    value_json=chosen_value,
                    source=FieldValueSource.OFFICER,
                    verification_status=FieldValueVerificationStatus.OFFICER_VERIFIED,
                    confidence=1.0,
                    entered_by=officer
                )
                queue_item.status = VerificationStatus.APPROVED
            elif decision_action == VerificationDecisionAction.REQUEST_CORRECTION:
                queue_item.status = VerificationStatus.DEFECT_FLAGGED
            else:
                queue_item.status = VerificationStatus.PENDING

            queue_item.reviewed_by = officer
            queue_item.reviewed_at = timezone.now()
            queue_item.officer_remarks = reason
            queue_item.save()

            AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='VerificationQueueItem',
                entity_id=str(queue_item.id),
                action=AuditAction.FIELD_CONFLICT_RESOLVED,
                before_json={
                    "status": "PENDING",
                    "conflict_details": queue_item.ai_assistance_json
                },
                after_json={
                    "field_code": field_code,
                    "decision_action": decision_action,
                    "resolved_value": chosen_value,
                    "queue_item_status": queue_item.status,
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason
            )

        return record

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

            new_record = DocumentVerificationRecord.objects.create(
                document=doc,
                document_version=latest_record.document_version if latest_record else None,
                ocr_result=latest_record.ocr_result if latest_record else None,
                field_definition=latest_record.field_definition if latest_record else None,
                field_code=latest_record.field_code if latest_record else "document_level",
                previous_value_json=latest_record.verified_value_json if latest_record else None,
                verified_value_json=None,
                verification_status=VerificationRecordStatus.NEEDS_REVIEW,
                decision_action=VerificationDecisionAction.NEEDS_REVIEW,
                officer=officer,
                officer_role=officer.role,
                reason=reason,
                verification_method=VerificationMethod.REOPENED,
                is_current=True,
                superseded_record=latest_record,
                correlation_id=corr_id
            )

            AuditLog.objects.create(
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
                    "new_record_id": str(new_record.id),
                    "status": "NEEDS_REVIEW",
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason
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
        Promotes document status to VERIFIED without deciding scholarship eligibility.
        """
        doc = ApplicantDocument.objects.select_related('application', 'application__applicant').get(id=document_id)
        cls.validate_officer_authorization(officer, doc.application)

        corr_id = correlation_id or f"COMPLETE-VERIF-{doc.id}-{uuid.uuid4().hex[:6]}"

        with transaction.atomic():
            # Update any open verification queue item for this document
            v_items = VerificationQueueItem.objects.filter(
                application=doc.application,
                target_identifier__icontains=str(doc.id)
            )
            for vi in v_items:
                vi.status = VerificationStatus.APPROVED
                vi.reviewed_by = officer
                vi.reviewed_at = timezone.now()
                vi.officer_remarks = reason or "Document verification completed."
                vi.save()

            AuditLog.objects.create(
                actor=officer,
                actor_role=officer.role,
                entity_type='ApplicantDocument',
                entity_id=str(doc.id),
                action=AuditAction.DOCUMENT_VERIFICATION_COMPLETED,
                after_json={
                    "document_id": str(doc.id),
                    "application_id": str(doc.application_id) if doc.application_id else None,
                    "officer": officer.username,
                    "correlation_id": corr_id,
                },
                reason=reason or "Document verification completed by officer."
            )

        return {
            "document_id": str(doc.id),
            "status": "COMPLETED",
            "correlation_id": corr_id
        }
