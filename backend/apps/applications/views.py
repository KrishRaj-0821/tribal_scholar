import uuid
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied as DjangoPermissionDenied

from .models import (
    Application, EligibilityEvaluation, ApplicationDeficiency,
    ApplicationFieldValue, ApplicationFieldDefinition,
    FieldValueSource, DeficiencyStatus, FieldConflict,
    ApplicationSubmissionSnapshot
)
from .serializers import (
    ApplicationSerializer, EligibilityEvaluationSerializer,
    ApplicationDeficiencySerializer, ApplicationFieldValueSerializer,
    FieldConflictSerializer, ApplicationSubmissionSnapshotSerializer
)
from .form_services import (
    FieldTrustResolver, ApplicationFormValidator, DynamicFormGenerator
)
from .services import FieldConflictService, DuplicateDetectionService, SubmissionService
from apps.schemes.models import SchemeVersion
from apps.schemes.evaluator import RuleEvaluationService
from apps.workflow.models import WorkflowState
from apps.applicants.models import ApplicantProfile
from apps.audit.models import AuditLog, AuditAction


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    Application aggregate root ViewSet.
    Provides protected endpoints for application lifecycle, dynamic forms,
    deficiencies, field trust resolution, and deterministic eligibility evaluation.
    """
    queryset = Application.objects.select_related('applicant__user', 'scheme_version__scheme', 'current_state').all()
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Application.objects.none()
        if user.is_officer or user.is_superuser:
            return Application.objects.all()
        # Applicants only see their own applications
        return Application.objects.filter(applicant__user=user)

    def create(self, request, *args, **kwargs):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if 'scheme_version' not in data or not data['scheme_version']:
            scheme_code = data.get('scheme_code') or data.get('scheme')
            if scheme_code:
                sv = SchemeVersion.objects.filter(scheme__code__iexact=str(scheme_code).replace('-', '_')).order_by('-version_number').first()
                if not sv:
                    sv = SchemeVersion.objects.filter(scheme__code__icontains=str(scheme_code)).first()
                if sv:
                    data['scheme_version'] = str(sv.id)
            if 'scheme_version' not in data or not data['scheme_version']:
                sv = SchemeVersion.objects.first()
                if sv:
                    data['scheme_version'] = str(sv.id)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        user = self.request.user
        scheme_version = serializer.validated_data.get('scheme_version')

        # Associate or find applicant profile
        applicant_profile = getattr(user, 'applicant_profile', None)
        if not applicant_profile:
            applicant_profile, _ = ApplicantProfile.objects.get_or_create(
                user=user,
                defaults={
                    "community": "ST",
                    "annual_family_income": 0
                }
            )

        # Default tracking number if not passed
        app_number = serializer.validated_data.get('application_number')
        if not app_number:
            code = scheme_version.scheme.code if scheme_version else "SCH"
            ay = scheme_version.academic_year if scheme_version else "2025-26"
            rand_suffix = str(uuid.uuid4().hex[:6]).upper()
            app_number = f"MOTA/{ay}/{code}/{rand_suffix}"

        # Resolve initial workflow state
        current_state = serializer.validated_data.get('current_state')
        if not current_state:
            workflow = getattr(scheme_version, 'workflow', None) if scheme_version else None
            if workflow:
                initial_state = workflow.states.filter(code='DRAFT').first() or workflow.states.order_by('sequence').first()
            else:
                initial_state = WorkflowState.objects.filter(code='DRAFT').first() or WorkflowState.objects.order_by('sequence').first()
            current_state = initial_state

        instance = serializer.save(
            applicant=applicant_profile,
            application_number=app_number,
            current_state=current_state
        )

        # Statutory audit trail
        AuditLog.objects.create(
            actor=user,
            actor_role=getattr(user, 'role', 'APPLICANT'),
            entity_type='Application',
            entity_id=str(instance.id),
            action=AuditAction.APPLICATION_CREATED,
            after_json={"application_number": instance.application_number},
            reason="Applicant initialized new application dossier"
        )

    # -------------------------------------------------------------------------
    # DYNAMIC FORM ENDPOINTS
    # -------------------------------------------------------------------------
    @action(detail=True, methods=['get', 'patch'], url_path='form')
    def form_endpoint(self, request, pk=None):
        """
        GET /api/v1/applications/{id}/form/
        Returns dynamic schema and current effective field values.

        PATCH /api/v1/applications/{id}/form/
        Submits applicant or officer field answers with optimistic concurrency control.
        Validates server-side against ApplicationFieldDefinition schema and conditional logic.
        """
        if request.method.lower() == 'get':
            application = self.get_object()
            form_schema = DynamicFormGenerator.generate_form(application.scheme_version)
            effective_values = FieldTrustResolver.get_effective_values(application)

            return Response({
                "application_id": str(application.id),
                "application_number": application.application_number,
                "scheme_version": str(application.scheme_version.id),
                "current_state": application.current_state.code,
                "form": form_schema,
                "effective_values": effective_values
            }, status=status.HTTP_200_OK)

        # PATCH Handling
        application = self.get_object()
        user = request.user

        # Authorization: Applicant can only update their own application in editable states
        if user.is_applicant and application.applicant.user != user:
            raise PermissionDenied("You can only modify your own application.")

        # Workflow State Check (Part 14)
        if user.is_applicant and application.current_state.code not in ('DRAFT',):
            return Response({
                "error": "LOCKED",
                "message": f"Application in state '{application.current_state.code}' cannot be edited."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Optimistic Concurrency Control (Part 4)
        expected_rev = request.data.get('expected_revision_number')
        if_match = request.headers.get('If-Match') or request.META.get('HTTP_IF_MATCH')
        if expected_rev is not None and int(expected_rev) != application.revision_number:
            return Response({
                "error": "CONFLICT",
                "message": "Your application was changed in another tab/device. Reload latest version before continuing.",
                "current_revision": application.revision_number
            }, status=status.HTTP_409_CONFLICT)
        if if_match:
            clean_match = if_match.strip('"')
            if clean_match != str(application.revision_number):
                return Response({
                    "error": "CONFLICT",
                    "message": "Your application was changed in another tab/device. Reload latest version before continuing.",
                    "current_revision": application.revision_number
                }, status=status.HTTP_409_CONFLICT)

        answers = request.data.get('answers', request.data)
        if not isinstance(answers, dict):
            return Response(
                {"error": "Expected JSON dictionary of field answers under 'answers' or body."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Merge with existing effective values for complete conditional evaluation
        existing_effective = FieldTrustResolver.get_effective_values(application)
        merged_for_validation = {k: v['value'] for k, v in existing_effective.items()}
        merged_for_validation.update(answers)

        # Authoritative Server-Side Form Validation (Part 13)
        is_valid, validation_errors = ApplicationFormValidator.validate_submission(
            scheme_version=application.scheme_version,
            submitted_data=merged_for_validation
        )

        if not is_valid:
            field_errors = {}
            for err in validation_errors:
                field_errors.setdefault(err["field"], []).append(err["message"])
            return Response({
                "status": "VALIDATION_FAILED",
                "field_errors": field_errors,
                "errors": validation_errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Determine source
        value_source = FieldValueSource.OFFICER if user.is_officer else FieldValueSource.APPLICANT

        # Record answers under transactional lock honoring Field Trust Hierarchy
        with transaction.atomic():
            app_locked = Application.objects.select_for_update().get(id=application.id)
            if expected_rev is not None and int(expected_rev) != app_locked.revision_number:
                return Response({
                    "error": "CONFLICT",
                    "message": "Your application was changed in another tab/device. Reload latest version before continuing.",
                    "current_revision": app_locked.revision_number
                }, status=status.HTTP_409_CONFLICT)
            if if_match is not None:
                clean_match = if_match.strip('"')
                if clean_match != str(app_locked.revision_number):
                    return Response({
                        "error": "CONFLICT",
                        "message": "Your application was changed in another tab/device. Reload latest version before continuing.",
                        "current_revision": app_locked.revision_number
                    }, status=status.HTTP_409_CONFLICT)

            saved_records = []
            for field_code, value in answers.items():
                field_def = ApplicationFieldDefinition.objects.filter(
                    scheme_version=app_locked.scheme_version,
                    field_code=field_code
                ).first()

                if field_def:
                    new_val = ApplicationFieldValue.objects.create(
                        application=app_locked,
                        field_definition=field_def,
                        value_json=value,
                        source=value_source,
                        confidence=1.0,
                        entered_by=user
                    )
                    saved_records.append(field_code)

            app_locked.revision_number += 1
            app_locked.last_modified_by = user
            app_locked.save(update_fields=['revision_number', 'last_modified_by', 'updated_at'])

            # Audit event
            AuditLog.objects.create(
                actor=user,
                actor_role=getattr(user, 'role', 'APPLICANT'),
                entity_type='Application',
                entity_id=str(app_locked.id),
                action=AuditAction.FIELD_VALUE_CHANGED,
                after_json={"updated_fields": saved_records, "source": value_source, "revision": app_locked.revision_number},
                reason="Form fields updated"
            )

            # Conflict Detection Trigger (Part 3)
            FieldConflictService.detect_conflicts(app_locked)

        # Return refreshed effective values and ETag
        updated_effective = FieldTrustResolver.get_effective_values(app_locked)
        resp = Response({
            "status": "SUCCESS",
            "revision_number": app_locked.revision_number,
            "updated_fields": saved_records,
            "effective_values": updated_effective
        }, status=status.HTTP_200_OK)
        resp['ETag'] = f'"{app_locked.revision_number}"'
        return resp

    # -------------------------------------------------------------------------
    # TRANSACTIONAL & IDEMPOTENT SUBMISSION (Part 6 & 7)
    # -------------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='submit')
    def submit_application(self, request, pk=None):
        """
        POST /api/v1/applications/{id}/submit/
        Requires Idempotency-Key header. Executes full transactional submission pipeline.
        """
        application = self.get_object()
        idempotency_key = (
            request.headers.get('Idempotency-Key') or
            request.META.get('HTTP_IDEMPOTENCY_KEY') or
            request.data.get('idempotency_key')
        )
        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header is required for submission."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            receipt, status_code = SubmissionService.submit(
                application=application,
                actor_user=request.user,
                idempotency_key=idempotency_key,
                request_path=request.path
            )
            return Response(receipt, status=status_code)
        except (ValidationError, DjangoValidationError) as e:
            msg = e.message_dict if hasattr(e, 'message_dict') else (e.messages if hasattr(e, 'messages') else str(e))
            return Response(
                {"error": msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except (PermissionDenied, DjangoPermissionDenied) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_403_FORBIDDEN
            )

    # -------------------------------------------------------------------------
    # SUBMISSION SNAPSHOT VIEWING (Part 8 & 9)
    # -------------------------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='submission-snapshot')
    def submission_snapshot(self, request, pk=None):
        """
        GET /api/v1/applications/{id}/submission-snapshot/
        Secure access to immutable submission snapshot. Logs audit event.
        """
        application = self.get_object()
        user = request.user
        if getattr(user, 'is_applicant', False) and application.applicant.user != user:
            raise PermissionDenied("You can only access your own submission snapshot.")

        snapshot = application.submission_snapshots.order_by('-submitted_at').first()
        if not snapshot:
            return Response(
                {"error": "No submission snapshot found for this application."},
                status=status.HTTP_404_NOT_FOUND
            )

        AuditLog.objects.create(
            actor=user,
            actor_role=getattr(user, 'role', 'APPLICANT'),
            entity_type='ApplicationSubmissionSnapshot',
            entity_id=str(snapshot.id),
            action=AuditAction.SNAPSHOT_VIEWED,
            after_json={"snapshot_hash": snapshot.snapshot_hash, "revision": snapshot.revision_number},
            reason="User viewed sensitive submission snapshot."
        )

        serializer = ApplicationSubmissionSnapshotSerializer(snapshot)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # CONFLICT MANAGEMENT ENDPOINTS (Part 3)
    # -------------------------------------------------------------------------
    @action(detail=True, methods=['get'], url_path='conflicts')
    def list_conflicts(self, request, pk=None):
        """
        GET /api/v1/applications/{id}/conflicts/
        """
        application = self.get_object()
        user = request.user
        if getattr(user, 'is_applicant', False) and application.applicant.user != user:
            raise PermissionDenied("You can only view your own application conflicts.")

        conflicts = application.conflicts.all()
        serializer = FieldConflictSerializer(conflicts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='conflicts/(?P<conflict_id>[^/.]+)/resolve')
    def resolve_conflict(self, request, pk=None, conflict_id=None):
        """
        POST /api/v1/applications/{id}/conflicts/{conflict_id}/resolve/
        Officer endpoint to resolve an open field contradiction.
        """
        application = self.get_object()
        user = request.user
        if getattr(user, 'is_applicant', False):
            raise PermissionDenied("Applicants cannot resolve field conflicts.")

        conflict = application.conflicts.filter(id=conflict_id).first()
        if not conflict:
            return Response({"error": "Conflict not found."}, status=status.HTTP_404_NOT_FOUND)

        selected_value = request.data.get('selected_value')
        reason = request.data.get('reason', 'Resolved following document scrutiny.')
        if selected_value is None:
            return Response({"error": "selected_value is required."}, status=status.HTTP_400_BAD_REQUEST)

        resolved_conf = FieldConflictService.resolve_conflict(
            conflict=conflict,
            officer_user=user,
            selected_value=selected_value,
            reason=reason
        )
        return Response(FieldConflictSerializer(resolved_conf).data, status=status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # DEFICIENCY WORKFLOW ENDPOINTS
    # -------------------------------------------------------------------------
    @action(detail=True, methods=['get', 'post'], url_path='deficiencies')
    def deficiencies(self, request, pk=None):
        """
        GET /api/v1/applications/{id}/deficiencies/
        POST /api/v1/applications/{id}/deficiencies/ (Officer raises deficiency)
        """
        application = self.get_object()

        if request.method == 'GET':
            defs_qs = application.deficiencies.all().order_by('-raised_at')
            serializer = ApplicationDeficiencySerializer(defs_qs, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == 'POST':
            # Only officers or admins can raise deficiencies
            if request.user.is_applicant:
                raise PermissionDenied("Applicants cannot raise deficiencies.")

            data = request.data
            def_obj = ApplicationDeficiency.objects.create(
                application=application,
                deficiency_code=data.get('deficiency_code', 'DEF_MANUAL'),
                field_code=data.get('field_code', ''),
                document_type=data.get('document_type', ''),
                description=data.get('description', 'Deficiency noted during scrutiny.'),
                severity=data.get('severity', 'BLOCKING'),
                raised_by=request.user,
                due_at=data.get('due_at')
            )

            AuditLog.objects.create(
                actor=request.user,
                actor_role=getattr(request.user, 'role', 'SCRUTINY_OFFICER'),
                entity_type='ApplicationDeficiency',
                entity_id=str(def_obj.id),
                action=AuditAction.DEFICIENCY_RAISED,
                after_json={"deficiency_code": def_obj.deficiency_code, "severity": def_obj.severity},
                reason="Administrative deficiency raised during officer review."
            )

            return Response(ApplicationDeficiencySerializer(def_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='deficiencies/(?P<deficiency_id>[^/.]+)/respond')
    def respond_deficiency(self, request, pk=None, deficiency_id=None):
        """
        POST /api/v1/applications/{id}/deficiencies/{deficiency_id}/respond/
        Applicant submits response or clarification to an open deficiency.
        """
        application = self.get_object()
        def_obj = application.deficiencies.filter(id=deficiency_id).first()
        if not def_obj:
            return Response({"error": "Deficiency not found."}, status=status.HTTP_404_NOT_FOUND)

        resolution_text = request.data.get('resolution_text', '').strip()
        if not resolution_text:
            return Response({"error": "A non-empty resolution_text is required."}, status=status.HTTP_400_BAD_REQUEST)

        def_obj.resolution_text = resolution_text
        def_obj.status = DeficiencyStatus.RESPONDED
        def_obj.save()

        AuditLog.objects.create(
            actor=request.user,
            actor_role=getattr(request.user, 'role', 'APPLICANT'),
            entity_type='ApplicationDeficiency',
            entity_id=str(def_obj.id),
            action=AuditAction.DEFICIENCY_RESPONDED,
            after_json={"status": def_obj.status, "resolution_text": resolution_text},
            reason="Applicant submitted formal response to deficiency."
        )

        return Response(ApplicationDeficiencySerializer(def_obj).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='deficiencies/(?P<deficiency_id>[^/.]+)/resolve')
    def resolve_deficiency(self, request, pk=None, deficiency_id=None):
        """
        POST /api/v1/applications/{id}/deficiencies/{deficiency_id}/resolve/
        Only authorized officers can mark a deficiency RESOLVED or WAIVED.
        """
        if request.user.is_applicant:
            raise PermissionDenied("Applicants are strictly prohibited from resolving deficiencies.")

        application = self.get_object()
        def_obj = application.deficiencies.filter(id=deficiency_id).first()
        if not def_obj:
            return Response({"error": "Deficiency not found."}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status', DeficiencyStatus.RESOLVED)
        if new_status not in (DeficiencyStatus.RESOLVED, DeficiencyStatus.WAIVED):
            return Response(
                {"error": "Status must be either 'RESOLVED' or 'WAIVED'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        def_obj.status = new_status
        def_obj.resolved_by = request.user
        def_obj.resolved_at = timezone.now()
        resolution_notes = request.data.get('resolution_text')
        if resolution_notes:
            def_obj.resolution_text = resolution_notes
        def_obj.save()

        AuditLog.objects.create(
            actor=request.user,
            actor_role=getattr(request.user, 'role', 'SCRUTINY_OFFICER'),
            entity_type='ApplicationDeficiency',
            entity_id=str(def_obj.id),
            action=AuditAction.DEFICIENCY_RESOLVED,
            after_json={"status": def_obj.status},
            reason="Officer concluded review of deficiency."
        )

        return Response(ApplicationDeficiencySerializer(def_obj).data, status=status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # OFFICER FIELD VERIFICATION
    # -------------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='verify-field')
    def verify_field(self, request, pk=None):
        """
        POST /api/v1/applications/{id}/verify-field/
        Officer assigns an OFFICER_VERIFIED value to a field, outranking applicant and OCR values.
        """
        if request.user.is_applicant:
            raise PermissionDenied("Applicants cannot verify field values.")

        application = self.get_object()
        field_code = request.data.get('field_code')
        value = request.data.get('value')

        if not field_code:
            return Response({"error": "field_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        field_def = ApplicationFieldDefinition.objects.filter(
            scheme_version=application.scheme_version,
            field_code=field_code
        ).first()

        if not field_def:
            return Response(
                {"error": f"Field '{field_code}' is not defined for scheme version."},
                status=status.HTTP_404_NOT_FOUND
            )

        val_obj = ApplicationFieldValue.objects.create(
            application=application,
            field_definition=field_def,
            value_json=value,
            source=FieldValueSource.OFFICER,
            confidence=1.0,
            entered_by=request.user
        )

        AuditLog.objects.create(
            actor=request.user,
            actor_role=getattr(request.user, 'role', 'SCRUTINY_OFFICER'),
            entity_type='ApplicationFieldValue',
            entity_id=str(val_obj.id),
            action=AuditAction.FIELD_VALUE_CHANGED,
            after_json={"field_code": field_code, "value": value, "source": "OFFICER"},
            reason="Officer verified field value."
        )

        updated_effective = FieldTrustResolver.get_effective_values(application)
        return Response({
            "status": "FIELD_VERIFIED",
            "effective_values": updated_effective
        }, status=status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # DETERMINISTIC ELIGIBILITY EVALUATION
    # -------------------------------------------------------------------------
    @action(detail=True, methods=['post'], url_path='evaluate-eligibility')
    def evaluate_eligibility(self, request, pk=None):
        """
        POST /api/v1/applications/{id}/evaluate-eligibility/
        Executes the deterministic RuleEvaluationService against this application.
        """
        application = self.get_object()

        # Authorization guardrail
        if request.user.is_applicant and application.applicant.user != request.user:
            raise PermissionDenied("You are only permitted to evaluate your own application.")

        # Execute deterministic evaluation
        eval_result = RuleEvaluationService.evaluate(
            application=application,
            actor=request.user
        )

        response_payload = {
            "status": eval_result["status"],
            "rule_results": eval_result["rule_results"],
            "blocking_failures": eval_result["blocking_failures"],
            "warnings": eval_result["warnings"],
            "unresolved_rules": eval_result["unresolved_rules"],
            "data_quality_issues": eval_result["data_quality_issues"],
            "source_references": eval_result["source_references"],
            "rule_version": eval_result["rule_version"],
            "result_hash": eval_result["result_hash"],
            "evaluated_at": eval_result["evaluated_at"]
        }

        return Response(response_payload, status=status.HTTP_200_OK)


class EligibilityEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for immutable historical eligibility evaluations.
    """
    queryset = EligibilityEvaluation.objects.select_related('application', 'scheme_version').all()
    serializer_class = EligibilityEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return EligibilityEvaluation.objects.none()
        if user.is_officer or user.is_superuser:
            return EligibilityEvaluation.objects.all()
        return EligibilityEvaluation.objects.filter(application__applicant__user=user)


class SchemeApplicationFormView(APIView):
    """
    GET /api/v1/schemes/{scheme_version_id}/application-form/
    Public/authenticated dynamic form structure retrieval.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, scheme_version_id):
        # Allow lookup by UUID or SchemeVersion pk
        try:
            version = SchemeVersion.objects.get(id=scheme_version_id)
        except (SchemeVersion.DoesNotExist, ValueError):
            return Response({"error": "SchemeVersion not found."}, status=status.HTTP_404_NOT_FOUND)

        form_data = DynamicFormGenerator.generate_form(version)
        return Response(form_data, status=status.HTTP_200_OK)
