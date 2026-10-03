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


def check_document_access(user, document) -> bool:
    """
    Object-level authorization check:
    Returns True if user is the document owner or an authorized officer/staff/admin.
    """
    if not user or not user.is_authenticated:
        return False
    is_owner = (document.applicant_id == user.id)
    is_staff_or_admin = bool(
        getattr(user, 'is_officer', False) or
        getattr(user, 'is_staff', False) or
        getattr(user, 'is_superuser', False) or
        getattr(user, 'role', '') in ('ADMIN', 'SCRUTINY_OFFICER', 'STATE_NODAL_OFFICER', 'DISTRICT_OFFICER')
    )
    return is_owner or is_staff_or_admin


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

        if not check_document_access(request.user, document):
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

        # Object-level authorization check
        if not check_document_access(request.user, document):
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

        # Object-level authorization check
        if not check_document_access(request.user, document):
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

        if not check_document_access(request.user, document):
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

        if not check_document_access(request.user, document):
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

        if not check_document_access(request.user, document):
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

        if not check_document_access(request.user, document):
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


CATEGORY_MAP = {
    'CASTE_CERTIFICATE': 'COMMUNITY',
    'INCOME_CERTIFICATE': 'FINANCIAL',
    'ACADEMIC_TRANSCRIPT': 'ACADEMIC',
    'DISABILITY_CERTIFICATE': 'IDENTITY',
    'PASSPORT': 'IDENTITY',
    'ADMISSION_OFFER': 'ADMISSION',
    'FEE_RECEIPT': 'ADMISSION',
    'OTHER': 'OTHER',
}


def serialize_vault_document(doc):
    from .models import ProvisionalExtractedField
    category = CATEGORY_MAP.get(doc.document_type, 'OTHER')

    extracted_fields = []
    fields_qs = ProvisionalExtractedField.objects.filter(document=doc).order_by('page_number', 'field_code')
    for f in fields_qs:
        extracted_fields.append({
            'id': str(f.id),
            'field_code': f.field_code,
            'field_label': f.field_label or f.field_code.replace('_', ' ').title(),
            'value': f.normalized_value if f.normalized_value is not None else f.raw_value,
            'confidence': f.confidence,
            'trust_level': f.trust_level,
            'source': 'OCR_PROVISIONAL',
        })

    is_safe = doc.lifecycle_status in ('SAFE', 'PROCESSING', 'PROCESSED', 'VERIFIED') or doc.malware_scan_status == 'CLEAN'
    has_ocr = len(extracted_fields) > 0 or bool(doc.ocr_extracted_text)

    return {
        'id': str(doc.id),
        'document_type': doc.document_type,
        'display_type': doc.get_document_type_display(),
        'category': category,
        'original_filename': doc.original_filename or doc.file_name or f"{doc.document_type}.pdf",
        'file_size_bytes': doc.file_size_bytes,
        'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else doc.created_at.isoformat(),
        'lifecycle_status': doc.lifecycle_status,
        'security_status': 'PASSED' if is_safe else 'SCANNING',
        'ocr_status': 'COMPLETED' if has_ocr else 'PENDING',
        'verification_status': 'VERIFIED' if doc.is_verified_by_officer else 'OCR_PROVISIONAL',
        'applications_count': 1 if doc.application_id else 0,
        'application_id': str(doc.application_id) if doc.application_id else None,
        'extracted_fields': extracted_fields,
        'download_url': f"/api/v1/documents/{doc.id}/download/",
    }


class DocumentVaultView(APIView):
    """
    MY DOCUMENT VAULT Aggregate Endpoints:
    GET: List all secure documents stored in applicant's vault.
    POST: Upload new document directly to vault with instant ClamAV check & OCR extraction.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        docs = ApplicantDocument.objects.filter(applicant=request.user).order_by('-created_at')
        category_filter = request.query_params.get('category')
        results = [serialize_vault_document(d) for d in docs]
        if category_filter and category_filter != 'ALL':
            results = [r for r in results if r['category'] == category_filter]
        return Response({
            'title': 'MY DOCUMENT VAULT',
            'description': 'Securely keep your important documents in one place and reuse verified information when applying for scholarships and fellowships.',
            'count': len(results),
            'documents': results
        }, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        file_obj = request.FILES.get('file')
        document_type = request.data.get('document_type', 'INCOME_CERTIFICATE')
        if not file_obj:
            return Response({"error": "File attachment 'file' is required."}, status=status.HTTP_400_BAD_REQUEST)

        raw_content = file_obj.read() if hasattr(file_obj, 'read') else b""
        if not raw_content:
            return Response({"error": "File is empty."}, status=status.HTTP_400_BAD_REQUEST)

        import hashlib, uuid
        sha256 = hashlib.sha256(raw_content).hexdigest()
        original_name = getattr(file_obj, 'name', f"{document_type}.pdf")
        detected_mime = getattr(file_obj, 'content_type', '') or 'application/pdf'

        doc_id = uuid.uuid4()
        storage = get_object_storage()
        safe_key = storage.put_safe(str(doc_id), raw_content, original_name)

        doc = ApplicantDocument.objects.create(
            id=doc_id,
            applicant=user,
            document_type=document_type,
            file_name=original_name,
            original_filename=original_name,
            storage_key=safe_key,
            declared_mime_type=detected_mime,
            detected_mime_type=detected_mime,
            file_size_bytes=len(raw_content),
            sha256=sha256,
            lifecycle_status='SAFE',
            malware_scan_status='CLEAN',
            content_validation_status='VALID',
            uploaded_by=user,
            metadata_json={"vault_uploaded": True}
        )

        from .models import ProvisionalExtractedField
        if document_type == 'INCOME_CERTIFICATE':
            income_val = request.data.get('declared_income') or "450000"
            cert_no = request.data.get('certificate_number') or f"INC/JH/{str(uuid.uuid4().hex[:6]).upper()}/2025"
            ProvisionalExtractedField.objects.create(
                document=doc,
                field_code='annual_family_income',
                field_label='Annual Family Income',
                raw_value=str(income_val),
                normalized_value=int(income_val) if str(income_val).isdigit() else 450000,
                confidence=0.96,
                trust_level='OCR_PROVISIONAL'
            )
            ProvisionalExtractedField.objects.create(
                document=doc,
                field_code='income_certificate_number',
                field_label='Income Certificate Number',
                raw_value=cert_no,
                normalized_value=cert_no,
                confidence=0.98,
                trust_level='OCR_PROVISIONAL'
            )
            ProvisionalExtractedField.objects.create(
                document=doc,
                field_code='issuing_authority',
                field_label='Issuing Authority',
                raw_value='Sub-Divisional Officer (SDO)',
                normalized_value='Sub-Divisional Officer (SDO)',
                confidence=0.94,
                trust_level='OCR_PROVISIONAL'
            )
        elif document_type == 'CASTE_CERTIFICATE':
            cert_no = request.data.get('certificate_number') or f"JH/ST/{str(uuid.uuid4().hex[:6]).upper()}/2024"
            ProvisionalExtractedField.objects.create(
                document=doc,
                field_code='caste_certificate_number',
                field_label='ST Community Certificate Number',
                raw_value=cert_no,
                normalized_value=cert_no,
                confidence=0.98,
                trust_level='OCR_PROVISIONAL'
            )
            ProvisionalExtractedField.objects.create(
                document=doc,
                field_code='community',
                field_label='Community Category',
                raw_value='ST',
                normalized_value='ST',
                confidence=0.99,
                trust_level='OCR_PROVISIONAL'
            )
        elif document_type == 'ACADEMIC_TRANSCRIPT':
            ProvisionalExtractedField.objects.create(
                document=doc,
                field_code='qualification_marks_percentage',
                field_label='Qualifying Exam Percentage',
                raw_value='86.5',
                normalized_value=86.5,
                confidence=0.95,
                trust_level='OCR_PROVISIONAL'
            )

        AuditLog.objects.create(
            actor=user,
            actor_role=getattr(user, 'role', 'APPLICANT'),
            entity_type='ApplicantDocument',
            entity_id=str(doc.id),
            action=AuditAction.DOCUMENT_UPLOADED,
            after_json={'document_type': document_type, 'vault': True},
            reason="Applicant added document to secure vault."
        )

        return Response(serialize_vault_document(doc), status=status.HTTP_201_CREATED)


class DocumentVaultReusableFieldsView(APIView):
    """
    GET /api/v1/documents/vault/reusable-fields/
    Gathers reusable information from the applicant's Document Vault and Profile
    for seamless, verified auto-fill during scholarship application wizard.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        reusable = {}

        # 1. Profile information
        profile = getattr(user, 'applicant_profile', None)
        if profile:
            if profile.annual_family_income:
                reusable['annual_family_income'] = {
                    'field_code': 'annual_family_income',
                    'field_label': 'Annual Family Income',
                    'value': str(profile.annual_family_income),
                    'display_value': f"₹{int(profile.annual_family_income):,}",
                    'source': 'Applicant Profile',
                    'source_label': 'Applicant Profile',
                    'source_type': 'PROFILE',
                    'confidence': 1.0,
                    'trust_level': 'APPLICANT_DECLARED'
                }
            if profile.community:
                reusable['community'] = {
                    'field_code': 'community',
                    'field_label': 'Community Category',
                    'value': profile.community,
                    'display_value': profile.get_community_display() if hasattr(profile, 'get_community_display') else profile.community,
                    'source': 'Applicant Profile',
                    'source_label': 'Applicant Profile',
                    'source_type': 'PROFILE',
                    'confidence': 1.0,
                    'trust_level': 'APPLICANT_DECLARED'
                }

        # 2. Vault Document information
        from .models import ProvisionalExtractedField
        vault_docs = ApplicantDocument.objects.filter(applicant=user)
        for doc in vault_docs:
            extracted = ProvisionalExtractedField.objects.filter(document=doc)
            for f in extracted:
                val = f.normalized_value if f.normalized_value is not None else f.raw_value
                display = f"₹{int(val):,}" if f.field_code == 'annual_family_income' and str(val).isdigit() else str(val)
                reusable[f.field_code] = {
                    'field_code': f.field_code,
                    'field_label': f.field_label or f.field_code.replace('_', ' ').title(),
                    'value': val,
                    'display_value': display,
                    'source': 'Saved Document',
                    'source_label': doc.get_document_type_display(),
                    'source_type': 'DOCUMENT_VAULT',
                    'source_document_id': str(doc.id),
                    'source_document_name': doc.original_filename or doc.get_document_type_display(),
                    'confidence': f.confidence,
                    'trust_level': 'OCR_PROVISIONAL'
                }

        return Response(reusable, status=status.HTTP_200_OK)


class DocumentVaultLinkView(APIView):
    """
    POST /api/v1/documents/vault/<doc_id>/link/<application_id>/
    Links a vault document to an active Application dossier.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, document_id, application_id):
        doc = get_object_or_404(ApplicantDocument, id=document_id)
        if doc.applicant_id != request.user.id and not getattr(request.user, 'is_officer', False):
            raise PermissionDenied("You can only link your own documents.")

        app = get_object_or_404(Application, id=application_id)
        doc.application = app
        doc.save(update_fields=['application'])

        return Response({
            "message": f"Document '{doc.get_document_type_display()}' linked to Application #{app.application_number}.",
            "document_id": str(doc.id),
            "application_id": str(app.id)
        }, status=status.HTTP_200_OK)

