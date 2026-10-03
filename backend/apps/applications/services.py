import json
import hashlib
from datetime import timedelta
from typing import Dict, Any, Tuple, Optional, List
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.conf import settings

from .models import (
    Application, ApplicationFieldValue, ApplicationFieldDefinition,
    FieldConflict, ConflictStatus, FieldValueSource, FieldValueVerificationStatus,
    IdempotencyRecord, ApplicationSubmissionSnapshot, ApplicationUniquenessPolicy,
    DuplicateDetectionMode
)
from .form_services import FieldTrustResolver, ApplicationFormValidator
from apps.documents.models import DocumentRequirement, ApplicantDocument
from apps.workflow.models import WorkflowState, ApplicationStatusHistory
from apps.audit.models import AuditLog, AuditAction


class FieldConflictService:
    """
    Detects and manages contradictions across data sources (e.g. APPLICANT vs OCR vs DOCUMENT).
    Maintains officer scrutiny lifecycle and statutory resolution audit trails.
    """

    @classmethod
    def detect_conflicts(cls, application: Application) -> List[FieldConflict]:
        """
        Inspects all submitted and extracted field values for an application.
        Detects divergence between contending sources and registers FieldConflict records.
        """
        conflicts_found = []
        field_codes = (
            ApplicationFieldValue.objects
            .filter(application=application)
            .values_list('field_definition__field_code', flat=True)
            .distinct()
        )

        for code in field_codes:
            values_qs = (
                ApplicationFieldValue.objects
                .filter(application=application, field_definition__field_code=code)
                .order_by('-created_at')
            )

            # Map values by source
            source_map = {}
            for fv in values_qs:
                if fv.source not in source_map and fv.value_json is not None:
                    source_map[fv.source] = {
                        "value": fv.value_json,
                        "confidence": fv.confidence,
                        "verification_status": fv.verification_status,
                        "created_at": fv.created_at.isoformat(),
                        "id": str(fv.id)
                    }

            # Check divergence: at least 2 distinct non-null values from different sources
            distinct_values = set()
            for s_info in source_map.values():
                val = s_info["value"]
                # Normalize for comparison
                distinct_values.add(json.dumps(val, sort_keys=True) if isinstance(val, (dict, list)) else str(val).strip())

            if len(distinct_values) > 1:
                # Conflict exists!
                existing = FieldConflict.objects.filter(
                    application=application,
                    field_code=code
                ).first()

                contending_list = [s_info["value"] for s_info in source_map.values()]
                if not existing:
                    conflict = FieldConflict.objects.create(
                        application=application,
                        field_code=code,
                        values_json=contending_list,
                        source_values=source_map,
                        severity='BLOCKING',
                        status=ConflictStatus.OPEN
                    )
                    conflicts_found.append(conflict)

                    AuditLog.objects.create(
                        actor=None,
                        actor_role='SYSTEM',
                        entity_type='FieldConflict',
                        entity_id=str(conflict.id),
                        action=AuditAction.CONFLICT_DETECTED,
                        after_json={"field_code": code, "sources": list(source_map.keys())},
                        reason=f"Discrepancy detected between sources on field '{code}'."
                    )
                elif existing.status in (ConflictStatus.OPEN, ConflictStatus.UNDER_REVIEW):
                    existing.values_json = contending_list
                    existing.source_values = source_map
                    existing.save(update_fields=['values_json', 'source_values'])
                    conflicts_found.append(existing)

        return conflicts_found

    @classmethod
    def resolve_conflict(
        cls,
        conflict: FieldConflict,
        officer_user,
        selected_value: Any,
        reason: str
    ) -> FieldConflict:
        """
        Officer resolves an open field conflict.
        Appends an authoritative OFFICER_VERIFIED value and marks conflict RESOLVED.
        """
        if getattr(officer_user, 'is_applicant', False):
            raise PermissionDenied("Applicants cannot resolve field conflicts.")

        with transaction.atomic():
            conf = FieldConflict.objects.select_for_update().get(id=conflict.id)
            conf.status = ConflictStatus.RESOLVED
            conf.resolved_by = officer_user
            conf.resolution = reason
            conf.resolved_at = timezone.now()
            conf.save()

            field_def = ApplicationFieldDefinition.objects.filter(
                scheme_version=conf.application.scheme_version,
                field_code=conf.field_code
            ).first()

            if field_def:
                ApplicationFieldValue.objects.create(
                    application=conf.application,
                    field_definition=field_def,
                    value_json=selected_value,
                    source=FieldValueSource.OFFICER,
                    verification_status=FieldValueVerificationStatus.OFFICER_VERIFIED,
                    confidence=1.0,
                    entered_by=officer_user
                )

            AuditLog.objects.create(
                actor=officer_user,
                actor_role=getattr(officer_user, 'role', 'SCRUTINY_OFFICER'),
                entity_type='FieldConflict',
                entity_id=str(conf.id),
                action=AuditAction.CONFLICT_RESOLVED,
                before_json={"status": ConflictStatus.OPEN},
                after_json={"status": ConflictStatus.RESOLVED, "selected_value": selected_value},
                reason=reason
            )

        return conf


class DuplicateDetectionService:
    """
    Evaluates application uniqueness against ApplicationUniquenessPolicy.
    Identifies potential duplicate applications across applicant identity,
    demographics, and document hashes without automatically accusing applicants of fraud.
    """

    @classmethod
    def check_duplicates(cls, application: Application) -> Dict[str, Any]:
        policy = ApplicationUniquenessPolicy.objects.filter(
            scheme_version=application.scheme_version
        ).first()

        mode = policy.duplicate_detection_mode if policy else DuplicateDetectionMode.WARN
        max_active = policy.max_active_applications if policy else 1

        matches = []

        # 1. Existing active applications for same applicant on same scheme version
        active_apps = Application.objects.filter(
            applicant=application.applicant,
            scheme_version=application.scheme_version
        ).exclude(id=application.id).exclude(current_state__code__in=['REJECTED', 'WITHDRAWN'])

        if active_apps.count() >= max_active:
            matches.append({
                "type": "SAME_APPLICANT_ACTIVE_APPLICATION",
                "detail": f"Applicant already has {active_apps.count()} active application(s) for this scheme version."
            })

        # 2. Document checksum collision across other applications in same academic year
        applicant_user = application.applicant.user
        doc_checksums = list(applicant_user.uploaded_documents.values_list('checksum', flat=True))
        if doc_checksums:
            colliding_docs = (
                ApplicantDocument.objects
                .filter(checksum__in=doc_checksums)
                .exclude(applicant=applicant_user)
            )
            for cdoc in colliding_docs:
                matches.append({
                    "type": "DOCUMENT_CHECKSUM_MATCH",
                    "detail": f"Document hash matches submission from another user ({cdoc.document_type})."
                })

        if matches:
            AuditLog.objects.create(
                actor=None,
                actor_role='SYSTEM',
                entity_type='Application',
                entity_id=str(application.id),
                action=AuditAction.DUPLICATE_FLAGGED,
                after_json={"matches": matches, "mode": mode},
                reason="Potential duplicate application detected by deduplication scanner."
            )

            if mode == DuplicateDetectionMode.STRICT:
                raise ValidationError("Duplicate application detected under STRICT uniqueness policy.")

            return {
                "is_duplicate": True,
                "mode": mode,
                "flag": "POSSIBLE_DUPLICATE",
                "matches": matches
            }

        return {
            "is_duplicate": False,
            "mode": mode,
            "flag": "CLEAR",
            "matches": []
        }


class SubmissionService:
    """
    Authoritative transactional submission pipeline.
    Enforces DRAFT -> SUBMITTED state machine, validates form schema,
    verifies required document manifests, creates immutable snapshots,
    locks application records, and enforces idempotent replay protection.
    """

    @classmethod
    def build_document_manifest(cls, application: Application) -> List[Dict[str, Any]]:
        manifest = []
        user = application.applicant.user
        for doc in user.uploaded_documents.all():
            manifest.append({
                "document_id": str(doc.id),
                "document_type": doc.document_type,
                "original_filename": doc.file_name,
                "checksum": doc.checksum,
                "uploaded_at": doc.created_at.isoformat() if hasattr(doc, 'created_at') and doc.created_at else timezone.now().isoformat(),
                "file_size": doc.file.size if doc.file else 0,
                "mime_type": "application/pdf" if doc.file_name.lower().endswith(".pdf") else "image/jpeg",
                "verification_status": "OFFICER_VERIFIED" if doc.is_verified_by_officer else "UNVERIFIED",
                "source": "APPLICANT_UPLOAD",
                "applicant_id": str(application.applicant.id),
                "application_id": str(application.id)
            })
        return manifest

    @classmethod
    def submit(
        cls,
        application: Application,
        actor_user,
        idempotency_key: Optional[str] = None,
        request_path: Optional[str] = None
    ) -> Tuple[Dict[str, Any], int]:
        """
        Executes the transactional submission pipeline.
        Returns (receipt_dict, status_code).
        """
        endpoint = request_path or f"/api/v1/applications/{application.id}/submit/"

        # 1. Idempotency Replay Protection (with expiration check)
        if idempotency_key:
            existing = IdempotencyRecord.objects.filter(
                key=idempotency_key,
                actor=actor_user,
                endpoint=endpoint
            ).first()
            if existing:
                if existing.expires_at and existing.expires_at < timezone.now():
                    existing.delete()
                else:
                    return existing.response_body, existing.response_status

        # 2. Database Transaction & Exclusive Locking
        with transaction.atomic():
            app = Application.objects.select_for_update().get(id=application.id)

            # In-lock idempotency re-check for concurrent identical-key requests
            if idempotency_key:
                existing = IdempotencyRecord.objects.filter(
                    key=idempotency_key,
                    actor=actor_user,
                    endpoint=endpoint
                ).first()
                if existing:
                    if existing.expires_at and existing.expires_at < timezone.now():
                        existing.delete()
                    else:
                        return existing.response_body, existing.response_status

            # Authorization Check
            if getattr(actor_user, 'is_applicant', False) and app.applicant.user != actor_user:
                raise PermissionDenied("You can only submit your own application.")

            # Workflow State Machine Invariant: DRAFT -> SUBMITTED only
            if app.current_state.code != 'DRAFT':
                raise ValidationError(
                    f"Application cannot be submitted from current state '{app.current_state.code}'. Only DRAFT applications may be submitted."
                )

            # 3. Server-Side Form Validation
            effective_map = FieldTrustResolver.get_effective_values(app)
            data_for_validation = {k: v['value'] for k, v in effective_map.items()}
            if app.applicant:
                data_for_validation.setdefault('annual_family_income', float(app.applicant.annual_family_income or 0))
                data_for_validation.setdefault('community', app.applicant.community)

            is_valid, validation_errors = ApplicationFormValidator.validate_submission(
                scheme_version=app.scheme_version,
                submitted_data=data_for_validation
            )
            if not is_valid:
                field_errors = {}
                for err in validation_errors:
                    field_errors.setdefault(err["field"], []).append(err["message"])
                raise ValidationError({
                    "status": "VALIDATION_FAILED",
                    "field_errors": field_errors,
                    "errors": validation_errors
                })

            # 4. Mandatory Document Requirements Validation
            doc_reqs = DocumentRequirement.objects.filter(
                scheme_version=app.scheme_version,
                required=True,
                when_required='APPLICATION'
            )
            uploaded_types = set(app.applicant.user.uploaded_documents.values_list('document_type', flat=True))
            missing_docs = [
                d_req.document_type for d_req in doc_reqs
                if d_req.document_type not in uploaded_types
            ]
            if missing_docs:
                raise ValidationError({
                    "status": "MISSING_DOCUMENTS",
                    "missing_documents": missing_docs,
                    "message": f"Mandatory documents missing: {', '.join(missing_docs)}"
                })

            # 5. Duplicate & Conflict Detection
            dup_info = DuplicateDetectionService.check_duplicates(app)
            FieldConflictService.detect_conflicts(app)

            # 6. Document Manifest Generation
            manifest = cls.build_document_manifest(app)

            # 7. Immutable ApplicationSubmissionSnapshot
            applicant_summary = {
                "applicant_id": str(app.applicant.id),
                "user_id": str(app.applicant.user_id),
                "community": app.applicant.community,
                "annual_family_income": float(app.applicant.annual_family_income or 0),
                "is_disabled": app.applicant.is_disabled,
                "date_of_birth": str(app.applicant.date_of_birth) if app.applicant.date_of_birth else None,
            }
            snapshot_payload = {
                "application_id": str(app.id),
                "application_number": app.application_number,
                "scheme_version_id": str(app.scheme_version_id),
                "academic_year": app.scheme_version.academic_year,
                "revision_number": app.revision_number,
                "applicant_data": applicant_summary,
                "form_values": effective_map,
                "document_manifest": manifest,
            }
            canonical_str = json.dumps(snapshot_payload, sort_keys=True, default=str)
            snap_hash = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

            snapshot = ApplicationSubmissionSnapshot.objects.create(
                application=app,
                revision_number=app.revision_number,
                applicant_data_json=applicant_summary,
                form_values_json=effective_map,
                document_manifest_json=manifest,
                scheme_version=app.scheme_version,
                snapshot_hash=snap_hash
            )

            # 8. Workflow State Transition: DRAFT -> SUBMITTED
            submitted_state = WorkflowState.objects.filter(code='SUBMITTED').first()
            if not submitted_state:
                submitted_state = WorkflowState.objects.create(
                    workflow=app.current_state.workflow,
                    code='SUBMITTED',
                    name='Submitted',
                    is_initial=False,
                    is_terminal=False
                )

            prev_state = app.current_state
            app.current_state = submitted_state
            app.revision_number += 1
            app.last_modified_by = actor_user
            app.save()

            # 9. Workflow History & Statutory Audit Log
            ApplicationStatusHistory.objects.create(
                application=app,
                from_state=prev_state,
                to_state=submitted_state,
                changed_by=actor_user,
                reason="Applicant completed statutory form validation and submitted application."
            )

            AuditLog.objects.create(
                actor=actor_user,
                actor_role=getattr(actor_user, 'role', 'APPLICANT'),
                entity_type='Application',
                entity_id=str(app.id),
                action=AuditAction.APPLICATION_SUBMITTED,
                before_json={"state": prev_state.code, "revision": app.revision_number - 1},
                reason="Application submitted with verified document manifest and input snapshot."
            )

            # 9.5. Queue Asynchronous SMS Notification via Fast2SMS
            try:
                from apps.notifications.services import NotificationService
                NotificationService.send_application_submitted(app)
            except Exception as notif_err:
                logger.warning("Failed to queue submission SMS for application %s: %s", app.id, notif_err)

            # 10. Generate Submission Receipt
            receipt = {
                "status": "SUBMITTED",
                "application_id": str(app.id),
                "application_number": app.application_number,
                "revision_number": app.revision_number,
                "submitted_at": snapshot.submitted_at.isoformat(),
                "snapshot_hash": snap_hash,
                "receipt_number": f"REC/{app.application_number}/{snapshot.revision_number}",
                "duplicate_detection": dup_info.get("flag", "CLEAR")
            }

            if idempotency_key:
                try:
                    with transaction.atomic():
                        IdempotencyRecord.objects.create(
                            key=idempotency_key,
                            actor=actor_user,
                            endpoint=endpoint,
                            request_hash=hashlib.sha256(canonical_str.encode('utf-8')).hexdigest(),
                            response_status=200,
                            response_body=receipt,
                            expires_at=timezone.now() + timedelta(hours=24)
                        )
                except IntegrityError:
                    existing = IdempotencyRecord.objects.filter(
                        key=idempotency_key,
                        actor=actor_user,
                        endpoint=endpoint
                    ).first()
                    if existing:
                        return existing.response_body, existing.response_status

            return receipt, 200


ApplicationSubmissionService = SubmissionService
