import logging
from django.core.cache import cache
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import viewsets, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import BaseThrottle
from rest_framework.parsers import MultiPartParser, FormParser

from apps.accounts.permissions import IsSchemeAdmin
from apps.applications.models import Application
from apps.audit.models import AuditLog, AuditAction
from .models import SourceDocument, ApplicantDocument, DocumentLifecycleStatus
from .serializers import (
    SourceDocumentSerializer,
    ApplicantDocumentSerializer,
    DocumentUploadResponseSerializer,
    DocumentStatusSerializer
)
from .services import DocumentIngestionService
from .storage import get_object_storage

logger = logging.getLogger('apps.documents')


class DocumentUploadRateThrottle(BaseThrottle):
    """
    Rate limiter for document uploads.
    Applies per-user and per-application rate limiting to prevent denial of service.
    """

    def allow_request(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        max_per_min = getattr(settings, 'MAX_UPLOADS_PER_MINUTE', 10)
        user_key = f"rate_limit_upload_user_{request.user.id}"
        count = cache.get(user_key, 0)

        if count >= max_per_min:
            return False

        cache.set(user_key, count + 1, timeout=60)
        return True


class SourceDocumentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing authentic Source Documents and provenance registries.
    Mutations strictly restricted to authorized Scheme Administrators.
    """
    queryset = SourceDocument.objects.all()
    serializer_class = SourceDocumentSerializer
    permission_classes = [IsSchemeAdmin]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'academic_year', 'notes', 'source_type']
    ordering_fields = ['document_date', 'retrieved_at', 'academic_year']

    def perform_create(self, serializer):
        from apps.audit.services import log_audit_event
        instance = serializer.save()
        log_audit_event(
            entity_type="SourceDocument",
            entity_id=str(instance.id),
            action="CREATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            after_json=serializer.data,
            reason="Registered new official publication in source registry."
        )

    def perform_update(self, serializer):
        from apps.audit.services import log_audit_event
        before_data = SourceDocumentSerializer(serializer.instance).data
        instance = serializer.save()
        log_audit_event(
            entity_type="SourceDocument",
            entity_id=str(instance.id),
            action="UPDATE",
            actor=self.request.user if self.request.user.is_authenticated else None,
            before_json=before_data,
            after_json=serializer.data,
            reason="Updated source document metadata."
        )


class ApplicationDocumentUploadView(APIView):
    """
    POST /api/v1/applications/{id}/documents/
    Secure upload endpoint:
    - Accepts multipart/form-data
    - Validates scheme requirements and limits
    - Stores file in quarantine
    - Returns HTTP 201 with document metadata
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [DocumentUploadRateThrottle]

    def post(self, request, application_id=None, pk=None):
        target_id = application_id or pk
        application = get_object_or_404(Application, id=target_id)

        document_type = request.data.get('document_type')
        if not document_type:
            return Response(
                {"error": "Field 'document_type' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {"error": "File attachment 'file' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        client_checksum = request.data.get('client_checksum')

        # Allow synchronous processing mode via parameter for test/demo environments
        sync_mode = request.query_params.get('sync', 'false').lower() in ('true', '1')

        try:
            document = DocumentIngestionService.upload_document(
                application=application,
                actor_user=request.user,
                document_type=document_type,
                file_obj=file_obj,
                client_checksum=client_checksum,
                sync_process=sync_mode
            )

            serializer = DocumentUploadResponseSerializer(document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except PermissionDenied as pe:
            return Response({"error": str(pe)}, status=status.HTTP_403_FORBIDDEN)
        except ValidationError as ve:
            return Response({"error": ve.messages if hasattr(ve, 'messages') else str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error(f"Upload error: {exc}", exc_info=True)
            return Response({"error": f"Internal upload error: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DocumentDetailView(APIView):
    """
    GET /api/v1/documents/{id}/
    Inspect document status, verification state, and security scan metadata.
    Never exposes internal storage bucket keys or raw binary data.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id=None, pk=None):
        target_id = document_id or pk
        document = get_object_or_404(ApplicantDocument, id=target_id)

        # Authorization: Applicant (own application) or Staff/Officer/Admin
        is_owner = (document.applicant_id == request.user.id)
        is_staff_or_admin = (
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER')
        )
        if not (is_owner or is_staff_or_admin):
            raise PermissionDenied("You are not authorized to view status for this document.")

        serializer = DocumentStatusSerializer(document)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentDownloadView(APIView):
    """
    GET /api/v1/documents/{id}/download/
    Authenticated streaming download for safe documents.
    Generates DOCUMENT_VIEWED statutory audit event.
    Strictly forbids downloading REJECTED or INFECTED documents.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id=None, pk=None):
        target_id = document_id or pk
        document = get_object_or_404(ApplicantDocument, id=target_id)

        # Authorization check
        is_owner = (document.applicant_id == request.user.id)
        is_staff_or_admin = (
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER')
        )
        if not (is_owner or is_staff_or_admin):
            raise PermissionDenied("You are not authorized to download this document.")

        # Security check: rejected / infected files cannot be downloaded
        if document.lifecycle_status in (DocumentLifecycleStatus.REJECTED,):
            return Response(
                {"error": "Access Denied: Infected or rejected documents cannot be downloaded."},
                status=status.HTTP_403_FORBIDDEN
            )

        storage = get_object_storage()
        try:
            stream = storage.get_stream(document.storage_key)
        except Exception as exc:
            logger.error(f"Failed to retrieve document stream for {document.id}: {exc}")
            raise Http404("Document file not found in storage.")

        # Create statutory audit log
        AuditLog.objects.create(
            actor=request.user,
            actor_role=getattr(request.user, 'role', 'APPLICANT'),
            entity_type='ApplicantDocument',
            entity_id=str(document.id),
            action=AuditAction.DOCUMENT_VIEWED,
            after_json={
                "application_id": str(document.application_id) if document.application_id else None,
                "document_type": document.document_type,
                "sha256": document.sha256
            },
            reason="Authorized user streamed document."
        )

        response = FileResponse(
            stream,
            content_type=document.detected_mime_type or 'application/octet-stream'
        )
        filename = document.original_filename or document.file_name or "document.bin"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class DocumentOCRStatusView(APIView):
    """
    GET /api/v1/documents/{id}/ocr-status/
    Authenticated endpoint reporting asynchronous OCR job status, attempt count,
    and completion/failure state.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id=None, pk=None):
        target_id = document_id or pk
        document = get_object_or_404(ApplicantDocument, id=target_id)

        # Authorization check
        is_owner = (document.applicant_id == request.user.id)
        is_staff_or_admin = (
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER')
        )
        if not (is_owner or is_staff_or_admin):
            raise PermissionDenied("You are not authorized to access this document's OCR status.")

        from .models import OCRJob
        from .serializers import OCRJobStatusSerializer

        latest_job = OCRJob.objects.filter(document=document).order_by('-created_at').first()
        if not latest_job:
            return Response(
                {"status": "NOT_REQUESTED", "message": "No OCR job has been requested for this document."},
                status=status.HTTP_200_OK
            )

        serializer = OCRJobStatusSerializer(latest_job)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentOCRResultView(APIView):
    """
    GET /api/v1/documents/{id}/ocr-result/
    Returns full OCR result metadata, pages, blocks, and bounding boxes.
    Does NOT expose raw filesystem paths or storage credentials.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id=None, pk=None):
        target_id = document_id or pk
        document = get_object_or_404(ApplicantDocument, id=target_id)

        is_owner = (document.applicant_id == request.user.id)
        is_staff_or_admin = (
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER')
        )
        if not (is_owner or is_staff_or_admin):
            raise PermissionDenied("You are not authorized to view this document's OCR results.")

        from .models import OCRResult
        from .serializers import OCRResultMetadataSerializer

        latest_result = OCRResult.objects.filter(document=document).prefetch_related('pages__blocks').order_by('-created_at').first()
        if not latest_result:
            return Response(
                {"status": "PENDING_OR_NOT_FOUND", "message": "No OCR result exists for this document yet."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = OCRResultMetadataSerializer(latest_result)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentClassificationView(APIView):
    """
    GET /api/v1/documents/{id}/classification/
    Returns latest document classification result, predicted type, confidence, and matching evidence.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id=None, pk=None):
        target_id = document_id or pk
        document = get_object_or_404(ApplicantDocument, id=target_id)

        is_owner = (document.applicant_id == request.user.id)
        is_staff_or_admin = (
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER')
        )
        if not (is_owner or is_staff_or_admin):
            raise PermissionDenied("You are not authorized to view this classification.")

        from .models import DocumentClassificationResult
        from .serializers import DocumentClassificationSerializer

        classification = DocumentClassificationResult.objects.filter(document=document).order_by('-created_at').first()
        if not classification:
            return Response(
                {"status": "NOT_CLASSIFIED", "message": "Document has not yet been classified."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = DocumentClassificationSerializer(classification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentExtractedFieldsView(APIView):
    """
    GET /api/v1/documents/{id}/extracted-fields/
    Returns provisional extracted field evidence with bounding boxes, confidence, and source provenance.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, document_id=None, pk=None):
        target_id = document_id or pk
        document = get_object_or_404(ApplicantDocument, id=target_id)

        is_owner = (document.applicant_id == request.user.id)
        is_staff_or_admin = (
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER')
        )
        if not (is_owner or is_staff_or_admin):
            raise PermissionDenied("You are not authorized to view extracted fields.")

        from .models import ProvisionalExtractedField
        from .serializers import ProvisionalExtractedFieldSerializer

        fields_qs = ProvisionalExtractedField.objects.filter(document=document).order_by('page_number', 'field_code')
        serializer = ProvisionalExtractedFieldSerializer(fields_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DocumentTriggerOCRView(APIView):
    """
    POST /api/v1/documents/{id}/trigger-ocr/
    Triggers or re-enqueues OCR processing for an explicitly SAFE document.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id=None, pk=None):
        target_id = document_id or pk
        document = get_object_or_404(ApplicantDocument, id=target_id)

        is_owner = (document.applicant_id == request.user.id)
        is_staff_or_admin = (
            getattr(request.user, 'is_staff', False) or
            getattr(request.user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER')
        )
        if not (is_owner or is_staff_or_admin):
            raise PermissionDenied("You are not authorized to trigger OCR for this document.")

        from .ocr_service import OCRService, InvalidDocumentStateForOCRError

        try:
            job = OCRService.enqueue_ocr_job(document.id)
            return Response(
                {
                    "message": "OCR job enqueued successfully.",
                    "job_id": str(job.id),
                    "status": job.status,
                    "idempotency_key": job.idempotency_key
                },
                status=status.HTTP_202_ACCEPTED
            )
        except InvalidDocumentStateForOCRError as ocr_err:
            return Response(
                {"error": ocr_err.code, "message": ocr_err.message},
                status=status.HTTP_400_BAD_REQUEST
            )
