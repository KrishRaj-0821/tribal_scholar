import io
import uuid
import pytest
from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.schemes.models import Scheme, SchemeVersion
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue,
    FieldDataType, FieldValueSource, FieldValueVerificationStatus,
    SOURCE_TRUST_RANK
)
from apps.applications.form_services import FieldTrustResolver
from apps.documents.models import (
    ApplicantDocument, DocumentVersion, DocumentLifecycleStatus,
    ApplicantDocumentType, OCRJob, OCRJobStatus, OCRResult,
    OCRPage, OCRBlock, DocumentClassificationResult,
    DocumentClassificationType, ProvisionalExtractedField
)
from apps.documents.ocr_renderer import (
    DocumentOCRRenderer, OCRError, ResourceExhaustionError,
    MalformedDocumentError, UnsupportedFormatError
)
from apps.documents.classifier import DocumentClassifier
from apps.documents.field_extractor import ProvisionalFieldExtractor, ExtractedFieldCandidate
from apps.documents.ocr_service import OCRService, InvalidDocumentStateForOCRError
from apps.audit.models import AuditLog, AuditAction
from apps.verification.models import VerificationQueueItem, VerificationItemType
from django.db import transaction


@pytest.fixture
def ocr_env(db):
    user = User.objects.create_user(
        username=f"applicant_{uuid.uuid4().hex[:6]}",
        email=f"app_{uuid.uuid4().hex[:6]}@example.com",
        password="ValidPassword123!",
        role="APPLICANT"
    )
    from apps.applicants.models import ApplicantProfile, CommunityCategory
    profile = ApplicantProfile.objects.create(
        user=user,
        community=CommunityCategory.ST
    )
    from apps.documents.models import SourceDocument, SourceDocumentStatus
    source_doc = SourceDocument.objects.create(
        title="Test Guideline",
        source_type="GUIDELINE",
        academic_year="2025-26",
        checksum="0" * 64,
        content_hash="1" * 64,
        status=SourceDocumentStatus.VERIFIED
    )
    scheme = Scheme.objects.create(
        code=f"SCHEME_{uuid.uuid4().hex[:6].upper()}",
        name="Test Scheme for OCR",
        description="Scheme objective"
    )
    scheme_version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=source_doc,
        status="ACTIVE"
    )
    from apps.workflow.models import WorkflowDefinition
    wf = WorkflowDefinition.objects.create(scheme_version=scheme_version, name="OCR Test WF")
    state_draft = wf.states.create(code="DRAFT", display_name="Draft", sequence=1)
    application = Application.objects.create(
        applicant=profile,
        scheme_version=scheme_version,
        application_number=f"APP-OCR-{uuid.uuid4().hex[:6].upper()}",
        current_state=state_draft
    )

    doc = ApplicantDocument.objects.create(
        application=application,
        applicant=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_name="income_cert.pdf",
        original_filename="income_cert.pdf",
        sha256="a" * 64,
        checksum="a" * 64,
        storage_key="safe/income_cert.pdf",
        lifecycle_status=DocumentLifecycleStatus.SAFE,
        detected_mime_type="application/pdf"
    )

    doc_version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        storage_key=doc.storage_key,
        sha256=doc.sha256,
        lifecycle_status=DocumentLifecycleStatus.SAFE
    )

    return {
        "user": user,
        "scheme": scheme,
        "scheme_version": scheme_version,
        "application": application,
        "document": doc,
        "document_version": doc_version,
    }


def create_minimal_test_pdf_bytes():
    """Returns valid minimal single-page PDF bytes."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 55 >> stream\n"
        b"BT /F1 12 Tf 50 250 Td (Annual Family Income Rs. 450000) Tj ET\n"
        b"endstream endobj\n"
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000204 00000 n \n"
        b"trailer << /Size 5 /Root 1 0 R >>\n"
        b"startxref\n"
        b"310\n"
        b"%%EOF\n"
    )


class TestOCRFoundationUnits:

    def test_1_ocr_cannot_process_non_safe_documents(self, ocr_env):
        """Mandatory Unit Test 1: OCR cannot process non-SAFE documents."""
        doc = ocr_env["document"]
        invalid_states = [
            DocumentLifecycleStatus.INITIATED,
            DocumentLifecycleStatus.UPLOADING,
            DocumentLifecycleStatus.UPLOADED,
            DocumentLifecycleStatus.QUARANTINED,
            DocumentLifecycleStatus.SCANNING,
            DocumentLifecycleStatus.PROMOTION_PENDING,
            DocumentLifecycleStatus.RECONCILIATION_REQUIRED,
            DocumentLifecycleStatus.REJECTED,
            DocumentLifecycleStatus.REVOKED,
        ]

        for state in invalid_states:
            doc_sample = ApplicantDocument(id=uuid.uuid4(), lifecycle_status=state)
            with pytest.raises(InvalidDocumentStateForOCRError) as excinfo:
                OCRService.validate_document_can_enter_ocr(doc_sample)
            assert "DOCUMENT_NOT_SAFE_FOR_OCR" in str(excinfo.value.code)

    def test_2_safe_document_can_create_ocr_job(self, ocr_env):
        """Mandatory Unit Test 2: SAFE document can create OCR job."""
        doc = ocr_env["document"]
        doc.lifecycle_status = DocumentLifecycleStatus.SAFE
        doc.save()

        job = OCRService.create_or_get_ocr_job(doc.id)
        assert job.status == OCRJobStatus.PENDING
        assert job.document_id == doc.id
        assert job.attempts == 0
        assert job.idempotency_key.startswith(str(ocr_env["document_version"].id))

        # Check audit event
        audit = AuditLog.objects.filter(
            entity_id=str(doc.id),
            action=AuditAction.OCR_JOB_CREATED
        ).first()
        assert audit is not None

    def test_3_ocr_job_idempotency(self, ocr_env):
        """Mandatory Unit Test 3: OCR job idempotency."""
        doc = ocr_env["document"]
        job1 = OCRService.create_or_get_ocr_job(doc.id)
        job2 = OCRService.create_or_get_ocr_job(doc.id)

        assert job1.id == job2.id
        assert OCRJob.objects.filter(document=doc).count() == 1

    def test_4_ocr_result_immutability(self, ocr_env):
        """Mandatory Unit Test 4: OCR result immutability."""
        doc = ocr_env["document"]
        job = OCRService.create_or_get_ocr_job(doc.id)

        result = OCRResult.objects.create(
            ocr_job=job,
            document=doc,
            document_version=ocr_env["document_version"],
            page_count=1,
            engine_name="MockOCREngine",
            engine_version="1.0.0",
            pipeline_version="1.0.0",
            result_hash="b" * 64,
            full_text="Sample immutable text"
        )

        # Direct mutation must raise ValidationError
        result.full_text = "Mutated text"
        with pytest.raises(ValidationError):
            result.save()

        # Delete must raise ValidationError
        with pytest.raises(ValidationError):
            result.delete()

    def test_5_ocr_confidence_does_not_imply_verification(self, ocr_env):
        """Mandatory Unit Test 5: OCR confidence does not imply verification."""
        # Even with high confidence (0.98), trust level remains OCR_PROVISIONAL
        cand = ExtractedFieldCandidate(
            field_code="annual_family_income",
            field_label="Annual Family Income",
            raw_value="Rs. 450000",
            normalized_value=450000.0,
            confidence=0.98,
            page_number=1,
            bounding_box={"x": 10.0, "y": 20.0, "width": 100.0, "height": 30.0},
            pipeline_version="1.0.0"
        )

        field_obj = ProvisionalExtractedField.objects.create(
            document=ocr_env["document"],
            field_code=cand.field_code,
            raw_value=cand.raw_value,
            normalized_value=cand.normalized_value,
            confidence=cand.confidence,
            trust_level="OCR_PROVISIONAL",
            page_number=1,
            bounding_box=cand.bounding_box
        )

        assert field_obj.trust_level == "OCR_PROVISIONAL"
        assert field_obj.confidence == 0.98
        # Ensure it is provisional, NOT verified
        assert field_obj.trust_level != "OFFICER_VERIFIED"
        assert field_obj.trust_level != "VERIFIED"

    def test_6_ocr_provisional_does_not_outrank_applicant_declared(self, ocr_env):
        """Mandatory Unit Test 6: OCR_PROVISIONAL does not outrank APPLICANT_DECLARED."""
        app = ocr_env["application"]
        scheme_version = ocr_env["scheme_version"]

        field_def = ApplicationFieldDefinition.objects.create(
            scheme_version=scheme_version,
            field_code="annual_family_income",
            label="Annual Family Income",
            data_type=FieldDataType.CURRENCY
        )

        # 1. Applicant declares 500,000 (rank 20)
        ApplicationFieldValue.objects.create(
            application=app,
            field_definition=field_def,
            value_json=500000.0,
            source=FieldValueSource.APPLICANT,
            confidence=1.0
        )

        # 2. OCR extracts 450,000 (rank 10) with high confidence
        ApplicationFieldValue.objects.create(
            application=app,
            field_definition=field_def,
            value_json=450000.0,
            source=FieldValueSource.OCR,
            confidence=0.99
        )

        # FieldTrustResolver must select APPLICANT (500000.0), NOT OCR (450000.0)
        effective = FieldTrustResolver.get_effective_values(app)
        assert effective["annual_family_income"]["value"] == 500000.0
        assert effective["annual_family_income"]["source"] == FieldValueSource.APPLICANT
        assert effective["annual_family_income"]["trust_rank"] == SOURCE_TRUST_RANK[FieldValueSource.APPLICANT]

    def test_7_bounding_boxes_persist_correctly(self, ocr_env):
        """Mandatory Unit Test 7: Bounding boxes persist correctly."""
        doc = ocr_env["document"]
        job = OCRService.create_or_get_ocr_job(doc.id)
        result = OCRResult.objects.create(
            ocr_job=job,
            document=doc,
            page_count=1,
            engine_name="PaddleOCR",
            engine_version="3.7.0",
            pipeline_version="1.0.0",
            result_hash="c" * 64
        )
        page = OCRPage.objects.create(
            ocr_result=result,
            page_number=1,
            width=1000,
            height=1400
        )
        block = OCRBlock.objects.create(
            page=page,
            extracted_text="Certificate Number 987654",
            confidence=0.96,
            bbox_x=120.5,
            bbox_y=340.2,
            bbox_width=250.0,
            bbox_height=45.0,
            polygon=[[120.5, 340.2], [370.5, 340.2], [370.5, 385.2], [120.5, 385.2]],
            reading_order=1
        )

        retrieved = OCRBlock.objects.get(id=block.id)
        assert retrieved.bbox_x == 120.5
        assert retrieved.bbox_y == 340.2
        assert retrieved.bbox_width == 250.0
        assert retrieved.bbox_height == 45.0
        assert len(retrieved.polygon) == 4

    def test_8_page_numbering_remains_deterministic(self, ocr_env):
        """Mandatory Unit Test 8: Page numbering remains deterministic."""
        doc = ocr_env["document"]
        job = OCRService.create_or_get_ocr_job(doc.id)
        result = OCRResult.objects.create(
            ocr_job=job,
            document=doc,
            page_count=2,
            engine_name="PaddleOCR",
            engine_version="3.7.0",
            pipeline_version="1.0.0",
            result_hash="d" * 64
        )

        p1 = OCRPage.objects.create(ocr_result=result, page_number=1, width=800, height=1000)
        p2 = OCRPage.objects.create(ocr_result=result, page_number=2, width=800, height=1000)

        # Duplicate page number for same OCRResult must fail unique constraint
        with transaction.atomic():
            with pytest.raises(Exception):
                OCRPage.objects.create(ocr_result=result, page_number=1, width=800, height=1000)

        pages = list(result.pages.order_by('page_number').values_list('page_number', flat=True))
        assert pages == [1, 2]

    def test_9_document_classification_may_return_unknown(self):
        """Mandatory Unit Test 9: Document classification may return UNKNOWN."""
        # Ambiguous / generic text without scheme certificate keywords
        text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio."
        outcome = DocumentClassifier.classify(text)

        assert outcome.predicted_type == DocumentClassificationType.UNKNOWN
        assert outcome.confidence < 0.40

    def test_10_malformed_ocr_output_is_rejected(self):
        """Mandatory Unit Test 10: Malformed document bytes rejected in renderer."""
        corrupted_bytes = b"NOT_A_VALID_PDF_OR_IMAGE_DATA_12345"

        with pytest.raises(MalformedDocumentError) as excinfo:
            DocumentOCRRenderer.render_document_pages(corrupted_bytes, "application/pdf")
        assert "CORRUPT_OR_MALFORMED_PDF" in str(excinfo.value.code)

    def test_11_unsupported_document_type_handled_safely(self):
        """Mandatory Unit Test 11: Unsupported document type handled safely."""
        fake_zip = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"

        with pytest.raises(UnsupportedFormatError) as excinfo:
            DocumentOCRRenderer.render_document_pages(fake_zip, "application/zip")
        assert "UNSUPPORTED_DOCUMENT_FORMAT" in str(excinfo.value.code)

    def test_12_resource_limit_validation(self):
        """Mandatory Unit Test 12: Resource-limit validation works."""
        pdf_bytes = create_minimal_test_pdf_bytes()

        # Enforce max_pages = 0 to trigger ceiling error
        with pytest.raises(ResourceExhaustionError) as excinfo:
            DocumentOCRRenderer.render_document_pages(pdf_bytes, "application/pdf", max_pages=0)
        assert "MAX_PAGE_COUNT_EXCEEDED" in str(excinfo.value.code)

        # Enforce max_total_pixels = 100 to trigger ceiling error
        with pytest.raises(ResourceExhaustionError) as excinfo2:
            DocumentOCRRenderer.render_document_pages(pdf_bytes, "application/pdf", max_total_pixels=100)
        assert "MAX_TOTAL_PIXELS_EXCEEDED" in str(excinfo2.value.code)

    def test_13_extracted_field_provenance_preserved(self, ocr_env):
        """Mandatory Unit Test 13: Extracted-field provenance is preserved."""
        doc = ocr_env["document"]
        job = OCRService.create_or_get_ocr_job(doc.id)
        result = OCRResult.objects.create(
            ocr_job=job,
            document=doc,
            document_version=ocr_env["document_version"],
            page_count=1,
            engine_name="PaddleOCR",
            engine_version="3.7.0",
            pipeline_version="1.0.0",
            result_hash="e" * 64
        )
        page = OCRPage.objects.create(ocr_result=result, page_number=1, width=1000, height=1200)
        block = OCRBlock.objects.create(page=page, extracted_text="Income Rs. 450000", confidence=0.95, reading_order=1)

        extracted = ProvisionalExtractedField.objects.create(
            document=doc,
            document_version=ocr_env["document_version"],
            ocr_result=result,
            ocr_page=page,
            ocr_block=block,
            field_code="annual_family_income",
            field_label="Annual Family Income",
            raw_value="Income Rs. 450000",
            normalized_value=450000.0,
            confidence=0.95,
            bounding_box={"x": 10.0, "y": 20.0, "width": 80.0, "height": 30.0}
        )

        # Full provenance chain verification
        assert extracted.ocr_block.id == block.id
        assert extracted.ocr_page.id == page.id
        assert extracted.ocr_result.id == result.id
        assert extracted.document_version.id == ocr_env["document_version"].id
        assert extracted.document.id == doc.id
        assert extracted.document.application.id == ocr_env["application"].id

    def test_14_conflict_creation_works(self, ocr_env):
        """Mandatory Unit Test 14: Conflict creation works."""
        app = ocr_env["application"]
        doc = ocr_env["document"]
        scheme_version = ocr_env["scheme_version"]

        field_def = ApplicationFieldDefinition.objects.create(
            scheme_version=scheme_version,
            field_code="annual_family_income",
            label="Annual Family Income",
            data_type=FieldDataType.CURRENCY
        )

        # Applicant declared 500,000
        ApplicationFieldValue.objects.create(
            application=app,
            field_definition=field_def,
            value_json=500000.0,
            source=FieldValueSource.APPLICANT
        )

        # OCR Candidate: 450,000 (material disagreement > 5%)
        candidate = ExtractedFieldCandidate(
            field_code="annual_family_income",
            field_label="Annual Family Income",
            raw_value="Rs. 450000",
            normalized_value=450000.0,
            confidence=0.94,
            page_number=1,
            bounding_box={"x": 10.0, "y": 20.0, "width": 100.0, "height": 30.0}
        )

        job = OCRService.create_or_get_ocr_job(doc.id)
        result = OCRResult.objects.create(
            ocr_job=job,
            document=doc,
            page_count=1,
            engine_name="MockOCREngine",
            engine_version="1.0.0",
            pipeline_version="1.0.0",
            result_hash="f" * 64
        )

        OCRService._integrate_application_fields_and_detect_conflicts(
            doc=doc,
            candidates=[candidate],
            ocr_result=result
        )

        # Audit event created
        audit = AuditLog.objects.filter(
            entity_id=str(app.id),
            action=AuditAction.FIELD_CONFLICT_DETECTED
        ).first()
        assert audit is not None
        assert audit.after_json["declared_value"] == 500000.0
        assert audit.after_json["ocr_extracted_value"] == 450000.0

        # Human verification queue item created
        v_item = VerificationQueueItem.objects.filter(
            application=app,
            item_type=VerificationItemType.DOCUMENT
        ).first()
        assert v_item is not None
        assert v_item.ai_assistance_json["conflict_type"] == "MATERIAL_CONFLICT"

    def test_15_ocr_failure_does_not_change_document_security_state_to_rejected(self, ocr_env):
        """Mandatory Unit Test 15: OCR failure does not change document security state to REJECTED."""
        doc = ocr_env["document"]
        assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE

        job = OCRService.create_or_get_ocr_job(doc.id)

        # Simulate an OCR failure (e.g. rendering or memory error)
        OCRService._mark_job_failed(job, "SIMULATED_FAILURE", "OCR engine exhausted worker memory.")

        job.refresh_from_db()
        doc.refresh_from_db()

        assert job.status == OCRJobStatus.FAILED
        assert job.failure_code == "SIMULATED_FAILURE"
        # Crucial security guarantee: Document remains SAFE!
        assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE
        assert doc.lifecycle_status != DocumentLifecycleStatus.REJECTED
