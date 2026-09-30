import uuid
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import UserRole
from apps.documents.models import (
    ApplicantDocument, ProvisionalExtractedField, OCRBlock, OCRPage
)
from apps.applications.models import Application, ApplicationFieldValue, ApplicationFieldDefinition
from .models import (
    VerificationQueueItem, DocumentVerificationRecord,
    VerificationStatus, VerificationRecordStatus, VerificationDecisionAction
)
from .services import DocumentVerificationService
from .serializers import (
    VerificationQueueItemSerializer, DocumentEvidenceSerializer,
    OCRFieldEvidenceSerializer, DocumentVerificationRecordSerializer,
    VerifyFieldRequestSerializer, ResolveConflictRequestSerializer,
    ReopenVerificationRequestSerializer
)


class IsReviewerOrOfficer(permissions.BasePermission):
    """
    Strict server-side permission enforcing reviewer/officer authorization.
    Rejects anonymous users and applicants.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.role == UserRole.APPLICANT:
            return False
        return getattr(user, 'is_officer', False) or user.is_superuser


class VerificationQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Reviewer viewset for inspecting items in the human verification queue.
    """
    serializer_class = VerificationQueueItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsReviewerOrOfficer]

    def get_queryset(self):
        qs = VerificationQueueItem.objects.select_related(
            'application', 'application__applicant', 'application__applicant__user',
            'application__scheme_version', 'application__scheme_version__scheme',
            'reviewed_by'
        ).all()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.order_by('-created_at')


class DocumentVerificationViewSet(viewsets.ViewSet):
    """
    Authoritative controller for human-in-the-loop document evidence verification.
    """
    permission_classes = [permissions.IsAuthenticated, IsReviewerOrOfficer]

    @action(detail=True, methods=['get'], url_path='evidence')
    def get_document_evidence(self, request, pk=None):
        """
        GET /api/v1/verification/documents/{id}/evidence/
        Returns complete evidence chain: document, pages, OCR blocks with bounding boxes.
        """
        doc = get_object_or_404(
            ApplicantDocument.objects.select_related('application', 'applicant'),
            id=pk
        )
        serializer = DocumentEvidenceSerializer(doc)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='ocr-fields')
    def get_ocr_field_evidence(self, request, pk=None):
        """
        GET /api/v1/verification/documents/{id}/ocr-fields/
        Returns extracted provisional fields paired with declared values, confidence, and bounding boxes.
        """
        doc = get_object_or_404(
            ApplicantDocument.objects.select_related('application', 'application__scheme_version'),
            id=pk
        )
        app = doc.application

        prov_fields = ProvisionalExtractedField.objects.filter(
            document=doc
        ).select_related('ocr_block', 'ocr_page', 'field_definition')

        # Map declared values
        declared_map = {}
        verified_map = {}
        if app:
            for val in ApplicationFieldValue.objects.filter(application=app).select_related('field_definition'):
                code = val.field_definition.field_code
                if val.source == 'OFFICER':
                    verified_map[code] = val.value_json
                elif val.source == 'APPLICANT':
                    declared_map[code] = val.value_json

        evidence_items = []
        for pf in prov_fields:
            code = pf.field_code
            decl_val = declared_map.get(code)
            verif_val = verified_map.get(code)
            
            # Check for conflict
            has_conflict = False
            if decl_val is not None and pf.extracted_value_json is not None:
                try:
                    v1 = float(decl_val)
                    v2 = float(pf.extracted_value_json)
                    diff = abs(v1 - v2)
                    has_conflict = (diff > max(1000.0, 0.05 * v1))
                except (ValueError, TypeError):
                    has_conflict = (str(decl_val).strip() != str(pf.extracted_value_json).strip())

            # Bounding box coordinates from block
            bbox = None
            poly = None
            block_id = None
            page_num = pf.ocr_page.page_number if pf.ocr_page else None
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

            evidence_items.append({
                "field_code": code,
                "field_label": pf.field_definition.label if pf.field_definition else code.replace('_', ' ').title(),
                "declared_value": decl_val,
                "ocr_value": pf.extracted_value_json,
                "verified_value": verif_val,
                "verification_status": "VERIFIED" if verif_val is not None else ("CONFLICT" if has_conflict else "PENDING"),
                "confidence": pf.confidence,
                "page_number": page_num,
                "bbox": bbox,
                "polygon": poly,
                "ocr_block_id": block_id,
                "has_conflict": has_conflict
            })

        serializer = OCRFieldEvidenceSerializer(evidence_items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='verify-field')
    def verify_field(self, request, pk=None):
        """
        POST /api/v1/verification/documents/{id}/verify-field/
        Explicit officer verification of a field. Increases trust rank to OFFICER (50).
        """
        doc = get_object_or_404(ApplicantDocument, id=pk)
        serializer = VerifyFieldRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        record = DocumentVerificationService.verify_field(
            document_id=doc.id,
            field_code=data["field_code"],
            verified_value=data["verified_value"],
            officer=request.user,
            reason=data.get("reason", ""),
            block_id=str(data["block_id"]) if data.get("block_id") else None
        )

        resp_serializer = DocumentVerificationRecordSerializer(record)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reject-field')
    def reject_field(self, request, pk=None):
        """
        POST /api/v1/verification/documents/{id}/reject-field/
        Explicit officer rejection of an unreadable or defective field.
        """
        doc = get_object_or_404(ApplicantDocument, id=pk)
        field_code = request.data.get("field_code")
        reason = request.data.get("reason", "")
        if not field_code or not reason:
            return Response(
                {"error": "Both 'field_code' and 'reason' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        record = DocumentVerificationService.reject_field(
            document_id=doc.id,
            field_code=field_code,
            officer=request.user,
            reason=reason
        )

        resp_serializer = DocumentVerificationRecordSerializer(record)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='history')
    def get_verification_history(self, request, pk=None):
        """
        GET /api/v1/verification/documents/{id}/history/
        Returns complete immutable historical audit trail of verification actions on this document.
        """
        doc = get_object_or_404(ApplicantDocument, id=pk)
        records = DocumentVerificationRecord.objects.filter(
            document=doc
        ).select_related('officer').order_by('-verified_at')
        serializer = DocumentVerificationRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='reopen')
    def reopen_verification(self, request, pk=None):
        """
        POST /api/v1/verification/documents/{id}/reopen/
        Reopens verification session for re-investigation.
        """
        doc = get_object_or_404(ApplicantDocument, id=pk)
        serializer = ReopenVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = DocumentVerificationService.reopen_verification(
            document_id=doc.id,
            officer=request.user,
            reason=serializer.validated_data["reason"]
        )
        resp_serializer = DocumentVerificationRecordSerializer(record)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete_verification(self, request, pk=None):
        """
        POST /api/v1/verification/documents/{id}/complete/
        Formally completes document verification without deciding scholarship eligibility.
        """
        doc = get_object_or_404(ApplicantDocument, id=pk)
        reason = request.data.get("reason", "Verification completed.")
        result = DocumentVerificationService.complete_document_verification(
            document_id=doc.id,
            officer=request.user,
            reason=reason
        )
        return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsReviewerOrOfficer])
def resolve_conflict_api_view(request, queue_item_id):
    """
    POST /api/v1/verification/conflicts/{queue_item_id}/resolve/
    Resolves a material discrepancy between applicant declaration and document OCR evidence.
    """
    serializer = ResolveConflictRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    record = DocumentVerificationService.resolve_field_conflict(
        queue_item_id=queue_item_id,
        decision_action=data["decision_action"],
        chosen_value=data["chosen_value"],
        officer=request.user,
        reason=data["reason"]
    )

    resp_serializer = DocumentVerificationRecordSerializer(record)
    return Response(resp_serializer.data, status=status.HTTP_200_OK)
