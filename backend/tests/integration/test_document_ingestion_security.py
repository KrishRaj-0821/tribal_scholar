import io
import hashlib
import concurrent.futures
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.db import transaction, connections
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.schemes.models import Scheme, SchemeType, SchemeVersion
from apps.documents.models import (
    SourceDocument, SourceType, SourceDocumentStatus,
    DocumentRequirement, DocumentValidityPolicy, ApplicantDocumentType,
    ApplicantDocument, DocumentLifecycleStatus, MalwareScanStatus,
    ContentValidationStatus, DocumentVersion, DocumentManifest,
    DocumentProcessingJob, DocumentJobType, DocumentJobStatus
)
from apps.workflow.models import WorkflowDefinition
from apps.applications.models import Application
from apps.audit.models import AuditLog, AuditAction
from apps.documents.services import DocumentIngestionService
from apps.documents.storage import get_object_storage
from apps.documents.malware_scanner import MockMalwareScanner


def make_clean_pdf(title="Official Verification Document"):
    title_comment = f"% {title}\n".encode("utf-8")
    return (
        b"%PDF-1.4\n"
        + title_comment
        + b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 4\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000120 00000 n \n"
        b"trailer\n"
        b"<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n"
        b"200\n"
        b"%%EOF"
    )


def make_clean_image(fmt="JPEG", size=(200, 200), color="blue"):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=fmt)
    return buf.getvalue()


pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.requires_postgresql,
]


@pytest.fixture
def doc_env(db):
    User.objects.filter(username__in=[
        "applicant_alpha", "applicant_beta", "officer_gamma", "admin_delta"
    ]).delete()
    Scheme.objects.filter(code="DOC_SCHEME").delete()
    SourceDocument.objects.filter(checksum="a" * 64).delete()

    user_a = User.objects.create_user(
        username="applicant_alpha",
        email="alpha@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    prof_a = ApplicantProfile.objects.create(
        user=user_a,
        community="ST",
        annual_family_income=300000,
        date_of_birth=date(2001, 5, 20)
    )

    user_b = User.objects.create_user(
        username="applicant_beta",
        email="beta@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    prof_b = ApplicantProfile.objects.create(
        user=user_b,
        community="ST",
        annual_family_income=350000,
        date_of_birth=date(2002, 6, 25)
    )

    officer = User.objects.create_user(
        username="officer_gamma",
        email="officer@tribal.gov.in",
        password="Password123!",
        role=UserRole.SCRUTINY_OFFICER,
        is_staff=True
    )

    admin_user = User.objects.create_user(
        username="admin_delta",
        email="admin@tribal.gov.in",
        password="Password123!",
        role=UserRole.ADMIN,
        is_staff=True
    )

    src_doc = SourceDocument.objects.create(
        title="Document Security & Verification Guidelines",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="a" * 64,
        content_hash="b" * 64,
        status=SourceDocumentStatus.VERIFIED
    )

    scheme = Scheme.objects.create(
        code="DOC_SCHEME",
        name="Document Ingestion Test Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )

    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=src_doc
    )

    wf = WorkflowDefinition.objects.create(scheme_version=version, name="Doc WF")
    state_draft = wf.states.create(code="DRAFT", display_name="Draft", sequence=1)
    state_sub = wf.states.create(code="SUBMITTED", display_name="Submitted", sequence=2)
    wf.transitions.create(from_state=state_draft, to_state=state_sub, required_role="APPLICANT")

    req_income = DocumentRequirement.objects.create(
        scheme_version=version,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        required=True,
        max_size_mb=5,
        source_document=src_doc
    )

    req_caste = DocumentRequirement.objects.create(
        scheme_version=version,
        document_type=ApplicantDocumentType.CASTE_CERTIFICATE,
        required=True,
        max_size_mb=2,
        source_document=src_doc
    )

    app_a = Application.objects.create(
        applicant=prof_a,
        scheme_version=version,
        application_number="MOTA/2025-26/DOC/0001",
        current_state=state_draft
    )

    app_b = Application.objects.create(
        applicant=prof_b,
        scheme_version=version,
        application_number="MOTA/2025-26/DOC/0002",
        current_state=state_draft
    )

    return {
        "user_a": user_a,
        "user_b": user_b,
        "officer": officer,
        "admin": admin_user,
        "version": version,
        "req_income": req_income,
        "req_caste": req_caste,
        "app_a": app_a,
        "app_b": app_b,
        "src_doc": src_doc,
    }


# =============================================================================
# 30 REQUIREMENT TESTS
# =============================================================================

def test_1_unauthenticated_upload_rejected(doc_env):
    """1. Unauthenticated upload rejected."""
    client = APIClient()
    pdf_bytes = make_clean_pdf()
    file_obj = SimpleUploadedFile("income.pdf", pdf_bytes, content_type="application/pdf")
    resp = client.post(
        f"/api/v1/applications/{doc_env['app_a'].id}/documents/",
        data={"document_type": ApplicantDocumentType.INCOME_CERTIFICATE, "file": file_obj},
        format="multipart"
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_2_applicant_cannot_upload_into_another_application(doc_env):
    """2. Applicant cannot upload into another application."""
    client = APIClient()
    client.force_authenticate(user=doc_env["user_a"])
    pdf_bytes = make_clean_pdf()
    file_obj = SimpleUploadedFile("income.pdf", pdf_bytes, content_type="application/pdf")
    resp = client.post(
        f"/api/v1/applications/{doc_env['app_b'].id}/documents/",
        data={"document_type": ApplicantDocumentType.INCOME_CERTIFICATE, "file": file_obj},
        format="multipart"
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_3_unsupported_document_type_rejected(doc_env):
    """3. Unsupported document type rejected."""
    client = APIClient()
    client.force_authenticate(user=doc_env["user_a"])
    pdf_bytes = make_clean_pdf()
    file_obj = SimpleUploadedFile("passport.pdf", pdf_bytes, content_type="application/pdf")
    resp = client.post(
        f"/api/v1/applications/{doc_env['app_a'].id}/documents/",
        data={"document_type": ApplicantDocumentType.PASSPORT, "file": file_obj},
        format="multipart"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "not a statutory requirement" in str(resp.data)


def test_4_extension_spoofing_rejected(doc_env):
    """4. Extension spoofing rejected (PE binary disguised as .pdf)."""
    client = APIClient()
    client.force_authenticate(user=doc_env["user_a"])
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100  # DOS/PE Header
    file_obj = SimpleUploadedFile("spoofed.pdf", fake_pdf, content_type="application/pdf")
    resp = client.post(
        f"/api/v1/applications/{doc_env['app_a'].id}/documents/",
        data={"document_type": ApplicantDocumentType.INCOME_CERTIFICATE, "file": file_obj},
        format="multipart"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Executable, script, or archive binary detected" in str(resp.data)


def test_5_mime_mismatch_rejected(doc_env):
    """5. MIME mismatch rejected (Declared PDF, actually JPEG bytes)."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    jpeg_bytes = make_clean_image("JPEG")
    file_obj = SimpleUploadedFile("cert.pdf", jpeg_bytes, content_type="application/pdf")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.REJECTED
    assert "CONTENT_TYPE_MISMATCH" in doc.rejection_reason


def test_6_oversized_file_rejected(doc_env):
    """6. Oversized file rejected."""
    client = APIClient()
    client.force_authenticate(user=doc_env["user_a"])
    # req_caste has max_size_mb = 2
    oversized = b"%PDF-" + b"0" * (3 * 1024 * 1024)
    file_obj = SimpleUploadedFile("huge.pdf", oversized, content_type="application/pdf")
    resp = client.post(
        f"/api/v1/applications/{doc_env['app_a'].id}/documents/",
        data={"document_type": ApplicantDocumentType.CASTE_CERTIFICATE, "file": file_obj},
        format="multipart"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeds maximum permitted limit" in str(resp.data)


def test_7_empty_file_rejected(doc_env):
    """7. Empty file rejected."""
    client = APIClient()
    client.force_authenticate(user=doc_env["user_a"])
    file_obj = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")
    resp = client.post(
        f"/api/v1/applications/{doc_env['app_a'].id}/documents/",
        data={"document_type": ApplicantDocumentType.INCOME_CERTIFICATE, "file": file_obj},
        format="multipart"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "empty" in str(resp.data)


def test_8_malformed_pdf_rejected(doc_env):
    """8. Malformed PDF rejected (missing %%EOF)."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    malformed_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"
    file_obj = SimpleUploadedFile("malformed.pdf", malformed_pdf, content_type="application/pdf")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.REJECTED
    assert "PDF_MALFORMED_STRUCTURE" in doc.rejection_reason


def test_9_invalid_image_rejected(doc_env):
    """9. Invalid image rejected (corrupted raster)."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    corrupted_img = b"\xff\xd8\xff\xe0" + b"\x00" * 30
    file_obj = SimpleUploadedFile("corrupted.jpg", corrupted_img, content_type="image/jpeg")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.REJECTED
    assert "IMAGE_DECODE_ERROR" in doc.rejection_reason


def test_10_sha256_correctly_computed_serverside(doc_env):
    """10. SHA-256 correctly computed server-side."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    pdf_bytes = make_clean_pdf()
    expected_hash = hashlib.sha256(pdf_bytes).hexdigest()

    file_obj = SimpleUploadedFile("income.pdf", pdf_bytes, content_type="application/pdf")
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        client_checksum="bogus_client_checksum_12345",
        sync_process=False
    )
    assert doc.sha256 == expected_hash
    assert doc.checksum == expected_hash


def test_11_duplicate_binary_produces_same_checksum(doc_env):
    """11. Duplicate binary produces same checksum."""
    pdf_bytes = make_clean_pdf("Duplicate Test Content")
    doc1 = DocumentIngestionService.upload_document(
        application=doc_env["app_a"],
        actor_user=doc_env["user_a"],
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("doc1.pdf", pdf_bytes, content_type="application/pdf")
    )
    doc2 = DocumentIngestionService.upload_document(
        application=doc_env["app_b"],
        actor_user=doc_env["user_b"],
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("doc2.pdf", pdf_bytes, content_type="application/pdf")
    )
    assert doc1.sha256 == doc2.sha256


def test_12_duplicate_document_is_flagged_not_called_fraud(doc_env):
    """12. Duplicate document is flagged, not called fraud."""
    pdf_bytes = make_clean_pdf("Duplicate Candidate Content")
    # First upload by User A
    DocumentIngestionService.upload_document(
        application=doc_env["app_a"],
        actor_user=doc_env["user_a"],
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("docA.pdf", pdf_bytes, content_type="application/pdf")
    )
    # Second upload of same file by User B
    doc_b = DocumentIngestionService.upload_document(
        application=doc_env["app_b"],
        actor_user=doc_env["user_b"],
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("docB.pdf", pdf_bytes, content_type="application/pdf")
    )
    assert doc_b.metadata_json.get("duplicate_document_candidate") is True

    audit = AuditLog.objects.filter(
        entity_id=str(doc_b.id),
        action=AuditAction.DUPLICATE_FLAGGED
    ).first()
    assert audit is not None
    assert "DUPLICATE_DOCUMENT_CANDIDATE" in audit.reason


def test_13_infected_mock_scan_rejects_document(doc_env):
    """13. Infected mock scan rejects document."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    # EICAR signature in PDF body
    infected_payload = make_clean_pdf() + b"\n% EICAR-STANDARD-ANTIVIRUS-TEST-FILE\n%%EOF"
    file_obj = SimpleUploadedFile("infected.pdf", infected_payload, content_type="application/pdf")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.REJECTED
    assert doc.malware_scan_status == MalwareScanStatus.INFECTED
    assert "MALWARE_DETECTED" in doc.rejection_reason


def test_14_scanner_error_does_not_mark_safe(doc_env):
    """14. Scanner error does not mark SAFE (becomes QUARANTINED)."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    error_payload = make_clean_pdf() + b"\n% __MOCK_SCANNER_ERROR__\n%%EOF"
    file_obj = SimpleUploadedFile("scan_err.pdf", error_payload, content_type="application/pdf")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.QUARANTINED
    assert doc.malware_scan_status == MalwareScanStatus.ERROR
    assert "SCAN_ERROR" in doc.rejection_reason


def test_15_safe_document_promoted_from_quarantine(doc_env):
    """15. Safe document promoted from quarantine."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    pdf_bytes = make_clean_pdf()
    file_obj = SimpleUploadedFile("safe.pdf", pdf_bytes, content_type="application/pdf")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE
    assert doc.malware_scan_status == MalwareScanStatus.CLEAN
    assert doc.storage_key.startswith("documents/")
    assert get_object_storage().exists(doc.storage_key) is True


def test_16_unsafe_document_never_enters_ocr_queue(doc_env):
    """16. Unsafe document never enters OCR queue."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    infected_payload = make_clean_pdf() + b"\n% EICAR-STANDARD-ANTIVIRUS-TEST-FILE\n%%EOF"
    file_obj = SimpleUploadedFile("infected.pdf", infected_payload, content_type="application/pdf")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        sync_process=True
    )
    ocr_jobs = DocumentProcessingJob.objects.filter(
        document=doc,
        job_type=DocumentJobType.OCR
    )
    assert ocr_jobs.count() == 0

    scan_job = DocumentProcessingJob.objects.filter(
        document=doc,
        job_type=DocumentJobType.SECURITY_SCAN
    ).first()
    assert scan_job.status == DocumentJobStatus.PERMANENT_FAILURE


def test_17_document_versioning_preserves_old_evidence(doc_env):
    """17. Document versioning preserves old evidence."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    pdf1 = make_clean_pdf("Version 1 Payload")
    pdf2 = make_clean_pdf("Version 2 Payload Replacement")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("income_v1.pdf", pdf1, content_type="application/pdf"),
        sync_process=True
    )
    v1 = doc.versions.get(version_number=1)

    doc_updated = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("income_v2.pdf", pdf2, content_type="application/pdf"),
        sync_process=True
    )
    assert doc_updated.id == doc.id
    assert doc_updated.versions.count() == 2

    v2 = doc_updated.versions.get(version_number=2)
    assert v2.supersedes_version == v1
    assert v1.sha256 != v2.sha256


def test_18_manifest_immutable(doc_env):
    """18. Manifest immutable."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("manifest_test.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=True
    )
    manifest = DocumentManifest.objects.get(document=doc)

    manifest.sha256 = "0" * 64
    with pytest.raises(ValidationError, match="DocumentManifest records are strictly immutable"):
        manifest.save()

    with pytest.raises(ValidationError, match="DocumentManifest records cannot be deleted"):
        manifest.delete()


def test_19_revocation_is_auditable(doc_env):
    """19. Revocation is auditable."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    officer = doc_env["officer"]

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("cert.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=True
    )
    revoked_doc = DocumentIngestionService.revoke_document(
        document_id=doc.id,
        actor_user=officer,
        reason="Official notice of invalidity received from revenue tehsildar."
    )
    assert revoked_doc.lifecycle_status == DocumentLifecycleStatus.REVOKED
    assert revoked_doc.revoked_by == officer

    audit = AuditLog.objects.filter(
        entity_id=str(doc.id),
        action=AuditAction.DOCUMENT_REVOKED
    ).first()
    assert audit is not None
    assert "Official notice" in audit.reason


def test_20_applicant_cannot_download_another_applicants_document(doc_env):
    """20. Applicant cannot download another applicant's document."""
    doc = DocumentIngestionService.upload_document(
        application=doc_env["app_a"],
        actor_user=doc_env["user_a"],
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("cert_a.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=True
    )
    client = APIClient()
    client.force_authenticate(user=doc_env["user_b"])
    resp = client.get(f"/api/v1/documents/{doc.id}/download/")
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_21_officer_access_follows_authorization(doc_env):
    """21. Officer access follows authorization."""
    doc = DocumentIngestionService.upload_document(
        application=doc_env["app_a"],
        actor_user=doc_env["user_a"],
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("cert_a.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=True
    )
    client = APIClient()
    client.force_authenticate(user=doc_env["officer"])
    resp = client.get(f"/api/v1/documents/{doc.id}/download/")
    assert resp.status_code == status.HTTP_200_OK


def test_22_document_view_produces_audit_event(doc_env):
    """22. Document view produces audit event."""
    doc = DocumentIngestionService.upload_document(
        application=doc_env["app_a"],
        actor_user=doc_env["user_a"],
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("cert_a.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=True
    )
    client = APIClient()
    client.force_authenticate(user=doc_env["user_a"])
    resp = client.get(f"/api/v1/documents/{doc.id}/download/")
    assert resp.status_code == status.HTTP_200_OK

    audit = AuditLog.objects.filter(
        entity_id=str(doc.id),
        action=AuditAction.DOCUMENT_VIEWED
    ).first()
    assert audit is not None
    assert audit.actor == doc_env["user_a"]


def test_23_upload_processing_triggered_only_after_db_commit(doc_env):
    """23. Upload processing is triggered only after DB commit."""
    mock_on_commit = MagicMock()
    with patch("django.db.transaction.on_commit", side_effect=mock_on_commit):
        DocumentIngestionService.upload_document(
            application=doc_env["app_a"],
            actor_user=doc_env["user_a"],
            document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
            file_obj=SimpleUploadedFile("income.pdf", make_clean_pdf(), content_type="application/pdf"),
            sync_process=False
        )
        assert mock_on_commit.called is True


def test_24_duplicate_worker_delivery_is_idempotent(doc_env):
    """24. Duplicate worker delivery is idempotent."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("income.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=False
    )
    # First execution
    res1 = DocumentIngestionService.process_document(doc.id)
    assert res1.lifecycle_status == DocumentLifecycleStatus.SAFE
    # Duplicate delivery
    res2 = DocumentIngestionService.process_document(doc.id)
    assert res2.lifecycle_status == DocumentLifecycleStatus.SAFE

    # Exactly 1 manifest created
    assert DocumentManifest.objects.filter(document=doc).count() == 1


@pytest.mark.django_db(transaction=True)
def test_25_two_workers_cannot_promote_same_document_version_twice(doc_env):
    """25. Two workers cannot promote same document version twice (concurrency race)."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    with patch("apps.documents.tasks.process_document_pipeline_task.delay"):
        doc = DocumentIngestionService.upload_document(
            application=app,
            actor_user=user,
            document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
            file_obj=SimpleUploadedFile("race.pdf", make_clean_pdf(), content_type="application/pdf"),
            sync_process=False
        )

    connections.close_all()

    def worker_run():
        connections.close_all()
        try:
            res = DocumentIngestionService.process_document(doc.id)
            return {"status": res.lifecycle_status}
        finally:
            connections.close_all()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker_run)
        f2 = executor.submit(worker_run)
        r1 = f1.result()
        r2 = f2.result()

    connections.close_all()
    doc.refresh_from_db()
    assert r1["status"] == DocumentLifecycleStatus.SAFE
    assert r2["status"] == DocumentLifecycleStatus.SAFE
    assert DocumentManifest.objects.filter(document=doc).count() == 1


def test_26_storage_failure_results_in_reconciliation_state(doc_env):
    """26. Storage failure results in reconciliation state (FAILED job, remains QUARANTINED)."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("storage_fail.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=False
    )
    with patch("apps.documents.storage.LocalObjectStorage.promote_to_safe", side_effect=OSError("Disk write error")):
        res = DocumentIngestionService.process_document(doc.id)
        assert res.lifecycle_status == DocumentLifecycleStatus.SCANNING
        job = DocumentProcessingJob.objects.filter(document=doc).first()
        assert job.status == DocumentJobStatus.FAILED
        assert job.error_code == "PROMOTION_ERROR"


def test_27_database_failure_does_not_create_false_safe_state(doc_env):
    """27. Database failure does not create false SAFE state."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("db_fail.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=False
    )
    with patch("apps.documents.models.DocumentManifest.objects.create", side_effect=RuntimeError("DB_CRASH")):
        with pytest.raises(RuntimeError):
            DocumentIngestionService.process_document(doc.id)

    doc.refresh_from_db()
    assert doc.lifecycle_status != DocumentLifecycleStatus.SAFE


def test_28_rate_limiting_works(doc_env, settings):
    """28. Rate limiting works."""
    settings.MAX_UPLOADS_PER_MINUTE = 3
    cache.clear()
    client = APIClient()
    client.force_authenticate(user=doc_env["user_a"])

    pdf_bytes = make_clean_pdf()
    for i in range(3):
        file_obj = SimpleUploadedFile(f"file_{i}.pdf", pdf_bytes, content_type="application/pdf")
        resp = client.post(
            f"/api/v1/applications/{doc_env['app_a'].id}/documents/",
            data={"document_type": ApplicantDocumentType.INCOME_CERTIFICATE, "file": file_obj},
            format="multipart"
        )
        assert resp.status_code == status.HTTP_201_CREATED

    # 4th upload must be throttled
    file_obj_throttled = SimpleUploadedFile("throttled.pdf", pdf_bytes, content_type="application/pdf")
    resp_throttled = client.post(
        f"/api/v1/applications/{doc_env['app_a'].id}/documents/",
        data={"document_type": ApplicantDocumentType.INCOME_CERTIFICATE, "file": file_obj_throttled},
        format="multipart"
    )
    assert resp_throttled.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_29_processing_retry_backoff_works(doc_env):
    """29. Processing retry/backoff works."""
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    error_payload = make_clean_pdf() + b"\n% __MOCK_SCANNER_ERROR__\n%%EOF"
    file_obj = SimpleUploadedFile("retry.pdf", error_payload, content_type="application/pdf")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=file_obj,
        sync_process=True
    )
    job = DocumentProcessingJob.objects.filter(document=doc).first()
    assert job.attempts == 1
    assert job.status == DocumentJobStatus.FAILED


def test_30_no_raw_document_bytes_appear_in_application_logs(doc_env, caplog):
    """30. No raw document bytes appear in application logs."""
    import logging
    app = doc_env["app_a"]
    user = doc_env["user_a"]
    pdf_bytes = make_clean_pdf("Sensitive Applicant Secret 987654321")
    file_obj = SimpleUploadedFile("cert.pdf", pdf_bytes, content_type="application/pdf")

    with caplog.at_level(logging.DEBUG):
        doc = DocumentIngestionService.upload_document(
            application=app,
            actor_user=user,
            document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
            file_obj=file_obj,
            sync_process=True
        )

    for record in caplog.records:
        assert "Sensitive Applicant Secret" not in record.message
        assert b"%PDF-1.4" not in record.message.encode()
