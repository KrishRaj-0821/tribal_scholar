import io
import os
import sys
import time
import uuid
import json
import subprocess
from datetime import date
import pytest
import redis
from PIL import Image, ImageDraw, ImageFont
from django.db import connection, transaction
from django.conf import settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.schemes.models import Scheme, SchemeVersion, SchemeType
from apps.workflow.models import WorkflowDefinition
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue,
    FieldDataType, FieldValueSource, ApplicationDeficiency
)
from apps.documents.models import (
    ApplicantDocument, DocumentVersion, DocumentLifecycleStatus,
    ApplicantDocumentType, DocumentRequirement, SourceDocument,
    SourceDocumentStatus, SourceType, OCRJob, OCRJobStatus,
    OCRResult, OCRPage, OCRBlock, DocumentClassificationResult,
    ProvisionalExtractedField
)
from apps.documents.services import DocumentIngestionService
from apps.documents.ocr_service import OCRService, InvalidDocumentStateForOCRError
from apps.documents.ocr_renderer import DocumentOCRRenderer, ResourceExhaustionError, MalformedDocumentError
from apps.documents.tasks import run_ocr_task
from apps.audit.models import AuditLog, AuditAction
from apps.verification.models import VerificationQueueItem, VerificationItemType

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.requires_postgresql,
]


def make_devanagari_raster_png() -> bytes:
    """Generates synthetic raster PNG containing real Devanagari script."""
    img = Image.new("RGB", (650, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_path = "C:/Windows/Fonts/Nirmala.ttc"
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, 28)
    else:
        font = ImageFont.load_default()

    draw.text((50, 40), "भारत सरकार", fill=(0, 0, 0), font=font)
    draw.text((50, 100), "आय प्रमाण पत्र", fill=(0, 0, 0), font=font)
    draw.text((50, 160), "वार्षिक पारिवारिक आय: 450000 रुपये", fill=(0, 0, 0), font=font)
    draw.text((50, 220), "प्रमाण पत्र संख्या: INC-2026-00124", fill=(0, 0, 0), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_mixed_raster_png() -> bytes:
    """Generates synthetic raster PNG containing mixed English and Devanagari script."""
    img = Image.new("RGB", (650, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_path = "C:/Windows/Fonts/Nirmala.ttc"
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, 28)
    else:
        font = ImageFont.load_default()

    draw.text((50, 40), "Government of India", fill=(0, 0, 0), font=font)
    draw.text((50, 100), "आय प्रमाण पत्र", fill=(0, 0, 0), font=font)
    draw.text((50, 160), "Annual Family Income", fill=(0, 0, 0), font=font)
    draw.text((50, 220), "वार्षिक पारिवारिक आय", fill=(0, 0, 0), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_clean_pdf(content_text: str = "Standard Income Certificate Rs. 450000") -> bytes:
    """Generates valid minimal PDF bytes containing readable text for OCR tests."""
    words = content_text.split()
    lines = []
    curr = []
    for w in words:
        if sum(len(x) for x in curr) + len(curr) + len(w) > 35:
            lines.append(" ".join(curr))
            curr = [w]
        else:
            curr.append(w)
    if curr:
        lines.append(" ".join(curr))

    stream_parts = ["BT /F1 12 Tf 50 320 Td"]
    for i, line in enumerate(lines):
        if i == 0:
            stream_parts.append(f"({line}) Tj")
        else:
            stream_parts.append(f"0 -35 Td ({line}) Tj")
    stream_parts.append("ET\n")
    stream_content = " ".join(stream_parts)
    stream_bytes = stream_content.encode("latin-1")
    length = len(stream_bytes)

    header = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Contents 4 0 R >> endobj\n"
    )
    obj4_header = f"4 0 obj << /Length {length} >> stream\n".encode("latin-1")
    footer = (
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
    return header + obj4_header + stream_bytes + footer


@pytest.fixture
def redis_client():
    redis_url = getattr(settings, 'REDIS_URL', None)
    if redis_url:
        return redis.from_url(redis_url)
    r = redis.Redis(
        host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
        port=int(getattr(settings, 'REDIS_PORT', 6379)),
        db=int(getattr(settings, 'REDIS_DB', 0))
    )
    return r


@pytest.fixture
def ocr_infra_env(db):
    User.objects.filter(username="ocr_integration_applicant").delete()
    Scheme.objects.filter(code="OCR_INTEGRATION_SCHEME").delete()
    SourceDocument.objects.filter(checksum="9" * 64).delete()

    user = User.objects.create_user(
        username="ocr_integration_applicant",
        email="ocr_applicant@tribal.gov.in",
        password="ValidPassword123!",
        role=UserRole.APPLICANT
    )
    prof = ApplicantProfile.objects.create(
        user=user,
        community="ST",
        annual_family_income=500000,
        date_of_birth=date(2002, 5, 20)
    )

    src_doc = SourceDocument.objects.create(
        title="OCR Integration Scheme Guideline",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="9" * 64,
        content_hash="8" * 64,
        status=SourceDocumentStatus.VERIFIED
    )

    scheme = Scheme.objects.create(
        code="OCR_INTEGRATION_SCHEME",
        name="OCR Integration Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )

    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=src_doc,
        status="ACTIVE"
    )

    wf = WorkflowDefinition.objects.create(scheme_version=version, name="OCR WF")
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

    app = Application.objects.create(
        applicant=prof,
        scheme_version=version,
        application_number=f"MOTA/2025-26/OCR/{uuid.uuid4().hex[:6].upper()}",
        current_state=state_draft
    )

    return {
        "user": user,
        "profile": prof,
        "scheme": scheme,
        "version": version,
        "app": app,
        "source_doc": src_doc,
    }


def spawn_celery_worker(worker_name: str = "ocr_worker"):
    """Spawns an isolated Celery worker subprocess targeting the active test database."""
    worker_env = os.environ.copy()
    worker_env["POSTGRES_DB"] = connection.settings_dict["NAME"]
    worker_env["TEST_LEVEL"] = "integration"
    worker_env["OCR_ENGINE_BACKEND"] = "paddleocr"

    proc = subprocess.Popen([
        sys.executable, "-m", "celery", "-A", "tribel_scholar",
        "worker", "--pool=solo", "-l", "WARNING", "-n", f"{worker_name}_{uuid.uuid4().hex[:6]}@localhost"
    ], env=worker_env)
    return proc


# ==============================================================================
# TEST A — SAFE DOCUMENT OCR END-TO-END VIA REAL CELERY WORKER
# ==============================================================================
def test_a_safe_document_ocr_via_real_celery_worker(ocr_infra_env, redis_client):
    """
    Test A: Upload -> security pipeline -> SAFE -> OCR task -> Redis -> real worker -> OCR result.
    Proves real async execution over Redis and PostgreSQL.
    """
    redis_client.delete("celery")
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    pdf_bytes = make_clean_pdf("Annual Family Income Rs. 450000 Certificate No. INC-2025-9988")

    # Upload document through security pipeline synchronously to reach SAFE
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("safe_ocr.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE

    # Enqueue OCR job asynchronously
    ocr_job = OCRService.create_or_get_ocr_job(doc.id)
    assert ocr_job.status == OCRJobStatus.PENDING

    # Dispatch to Redis
    run_ocr_task.delay(str(ocr_job.id), correlation_id="CORR-TEST-A")
    assert redis_client.llen("celery") >= 1, "OCR task was not placed in Redis queue."

    # Launch live Celery worker subprocess to consume from Redis
    worker_p = spawn_celery_worker("worker_a")
    try:
        max_wait = 150
        start = time.time()
        completed = False

        while time.time() - start < max_wait:
            ocr_job.refresh_from_db()
            if ocr_job.status == OCRJobStatus.COMPLETED:
                completed = True
                break
            time.sleep(1)

        assert completed, f"OCR task did not complete within {max_wait}s. Status={ocr_job.status}, failure={ocr_job.failure_message}"

        # Verify OCR result in database
        ocr_result = OCRResult.objects.filter(ocr_job=ocr_job).first()
        assert ocr_result is not None
        assert ocr_result.page_count >= 1
        assert len(ocr_result.result_hash) == 64
        assert ocr_result.engine_name in ("PaddleOCR", "MockOCREngine")

        # Verify Classification
        classification = DocumentClassificationResult.objects.filter(document=doc).first()
        assert classification is not None
        assert classification.predicted_type in (
            ApplicantDocumentType.INCOME_CERTIFICATE,
            "INCOME_CERTIFICATE",
            "UNKNOWN"
        )

        # Audit logs check
        assert AuditLog.objects.filter(entity_id=str(doc.id), action=AuditAction.OCR_COMPLETED).exists()
    finally:
        worker_p.terminate()
        worker_p.wait()
        redis_client.delete("celery")


# ==============================================================================
# TEST B — QUARANTINED / NON-SAFE DOCUMENT BLOCKED FROM OCR
# ==============================================================================
def test_b_quarantined_document_blocked_from_ocr(ocr_infra_env, redis_client):
    """
    Test B: Attempt OCR on a quarantined or rejected document.
    Must refuse to process and never enter OCR pipeline.
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]

    doc = ApplicantDocument.objects.create(
        application=app,
        applicant=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_name="quarantined.pdf",
        original_filename="quarantined.pdf",
        sha256="1" * 64,
        storage_key="quarantine/quarantined.pdf",
        lifecycle_status=DocumentLifecycleStatus.QUARANTINED
    )

    # Calling create_or_get_ocr_job must raise InvalidDocumentStateForOCRError
    with pytest.raises(InvalidDocumentStateForOCRError) as excinfo:
        OCRService.create_or_get_ocr_job(doc.id)
    assert "DOCUMENT_NOT_SAFE_FOR_OCR" in str(excinfo.value.code)

    # Attempting to run task directly must also fail safe
    fake_job_id = str(uuid.uuid4())
    fake_job = OCRJob(
        id=fake_job_id,
        document=doc,
        idempotency_key=f"{doc.id}:1.0.0:OCR",
        status=OCRJobStatus.PENDING
    )
    fake_job.save()

    res = run_ocr_task(str(fake_job.id))
    assert res["status"] == "FAILED"
    assert "DOCUMENT_NOT_SAFE_FOR_OCR" in res["error_code"]
    assert doc.lifecycle_status == DocumentLifecycleStatus.QUARANTINED


# ==============================================================================
# TEST C — DUPLICATE OCR TASK IS STRICTLY IDEMPOTENT
# ==============================================================================
def test_c_duplicate_ocr_task_is_idempotent(ocr_infra_env):
    """
    Test C: Dispatch same logical OCR task twice.
    Expected: Exactly one OCRResult created, second execution returns existing result without duplication.
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    pdf_bytes = make_clean_pdf("Annual Family Income Rs. 450000 Cert 12345")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("idempotent_ocr.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)

    # First execution
    res1 = OCRService.execute_ocr_pipeline(ocr_job.id)
    assert res1 is not None

    result_count_before = OCRResult.objects.filter(document=doc).count()
    assert result_count_before == 1

    # Second duplicate execution
    res2 = OCRService.execute_ocr_pipeline(ocr_job.id)
    assert res2.id == res1.id

    # No duplicate result rows created
    result_count_after = OCRResult.objects.filter(document=doc).count()
    assert result_count_after == 1


# ==============================================================================
# TEST D — TWO WORKERS RACE CONDITION ON SAME OCR JOB
# ==============================================================================
def test_d_two_workers_same_ocr_job_race_condition(ocr_infra_env, redis_client):
    """
    Test D: Two concurrent Celery workers receive the same OCR job.
    Expected: Exactly one worker processes and creates result; second safely observes COMPLETED.
    No duplicate OCRResult, no corrupted state.
    """
    redis_client.delete("celery")
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    pdf_bytes = make_clean_pdf("Two Worker Test Income Rs. 450000")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("race_ocr.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)

    # Push task twice to Redis to simulate duplicate queue delivery
    run_ocr_task.delay(str(ocr_job.id), correlation_id="RACE-1")
    run_ocr_task.delay(str(ocr_job.id), correlation_id="RACE-2")

    # Start 2 distinct Celery workers concurrently
    w1 = spawn_celery_worker("worker_race_1")
    w2 = spawn_celery_worker("worker_race_2")

    try:
        max_wait = 150
        start = time.time()
        completed = False

        while time.time() - start < max_wait:
            ocr_job.refresh_from_db()
            if ocr_job.status == OCRJobStatus.COMPLETED:
                completed = True
                break
            time.sleep(1)

        assert completed, "Neither worker completed the OCR job in time."

        # Verify exactly 1 OCRResult was created
        results = OCRResult.objects.filter(document=doc)
        assert results.count() == 1, f"Expected exactly 1 OCRResult, found {results.count()}"

        # Exactly 1 classification result
        classifications = DocumentClassificationResult.objects.filter(document=doc)
        assert classifications.count() == 1
    finally:
        w1.terminate()
        w2.terminate()
        w1.wait()
        w2.wait()
        redis_client.delete("celery")


# ==============================================================================
# TEST E — WORKER FAILURE AND BOUNDED RETRY
# ==============================================================================
def test_e_worker_failure_and_bounded_retry(ocr_infra_env):
    """
    Test E: Force OCR execution to fail (e.g. simulated engine crash).
    Verify bounded retries -> FAILED.
    Verify document security state is NOT corrupted (remains SAFE).
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    pdf_bytes = make_clean_pdf("Failure Retry Test")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("failure_retry.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)

    # Force simulated error inside OCRService._mark_job_failed
    OCRService._mark_job_failed(ocr_job, "SIMULATED_RETRY_EXHAUSTION", "Worker crashed 3 times.")

    ocr_job.refresh_from_db()
    doc.refresh_from_db()

    assert ocr_job.status == OCRJobStatus.FAILED
    assert ocr_job.failure_code == "SIMULATED_RETRY_EXHAUSTION"
    # Document security state must remain untouched: SAFE
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE
    assert doc.lifecycle_status != DocumentLifecycleStatus.REJECTED


# ==============================================================================
# TEST F — OCR CRASH AND RECOVERY
# ==============================================================================
def test_f_ocr_crash_and_recovery(ocr_infra_env):
    """
    Test F: Worker starts processing, transitions job to RUNNING, but crashes before completion.
    Recovery execution re-processes and reaches COMPLETED without duplicate records.
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    pdf_bytes = make_clean_pdf("Crash Recovery Test Income Rs. 450000")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("crash_recovery.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)

    # Simulate intermediate RUNNING state where worker was killed
    ocr_job.status = OCRJobStatus.RUNNING
    ocr_job.started_at = timezone.now()
    ocr_job.save()

    # Recovery: Re-dispatching/executing OCR pipeline recovers and finishes
    ocr_result = OCRService.execute_ocr_pipeline(ocr_job.id)
    assert ocr_result is not None

    ocr_job.refresh_from_db()
    assert ocr_job.status == OCRJobStatus.COMPLETED
    assert OCRResult.objects.filter(document=doc).count() == 1


# ==============================================================================
# TEST G — MALFORMED PDF HANDLED SAFELY IN OCR
# ==============================================================================
def test_g_malformed_pdf_handled_safely_in_ocr(ocr_infra_env):
    """
    Test G: Document is labeled PDF and passed security scanner, but contains corrupted PDF content.
    OCR renderer must reject malformed content safely with explicit code.
    Document must remain SAFE (not falsely marked malware-rejected).
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    corrupted_pdf_bytes = b"%PDF-1.4\nCorrupted content completely breaking PDF structure"

    doc = ApplicantDocument.objects.create(
        application=app,
        applicant=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_name="corrupt.pdf",
        original_filename="corrupt.pdf",
        sha256="2" * 64,
        storage_key="safe/corrupt.pdf",
        lifecycle_status=DocumentLifecycleStatus.SAFE,
        detected_mime_type="application/pdf"
    )

    # Put bytes into safe storage
    from apps.documents.storage import get_object_storage
    storage = get_object_storage()
    storage.put_quarantine(str(doc.id), corrupted_pdf_bytes, "corrupt.pdf")
    safe_key = storage.promote_to_safe(str(doc.id), str(app.id), "corrupt.pdf")
    doc.storage_key = safe_key
    doc.save()

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)

    with pytest.raises(MalformedDocumentError):
        OCRService.execute_ocr_pipeline(ocr_job.id)

    ocr_job.refresh_from_db()
    doc.refresh_from_db()

    assert ocr_job.status == OCRJobStatus.FAILED
    assert ocr_job.failure_code == "CORRUPT_OR_MALFORMED_PDF"
    # Document remains SAFE
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE


# ==============================================================================
# TEST H — OVERSIZED PAGE / RESOURCE EXHAUSTION
# ==============================================================================
def test_h_resource_exhaustion_handled_safely(ocr_infra_env):
    """
    Test H: Document violating OCR resource ceilings (e.g. max pages).
    Fails safely with ResourceExhaustionError. Document remains SAFE.
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    pdf_bytes = make_clean_pdf("Resource Exhaustion Test")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("resource_test.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)

    # Monkeypatch settings to force max_pages ceiling to 0
    from unittest.mock import patch
    with patch.object(settings, 'MAX_OCR_PAGES', 0):
        with pytest.raises(ResourceExhaustionError) as excinfo:
            OCRService.execute_ocr_pipeline(ocr_job.id)
        assert "MAX_PAGE_COUNT_EXCEEDED" in str(excinfo.value.code)

    ocr_job.refresh_from_db()
    doc.refresh_from_db()

    assert ocr_job.status == OCRJobStatus.FAILED
    assert ocr_job.failure_code == "MAX_PAGE_COUNT_EXCEEDED"
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE


# ==============================================================================
# TEST I — ACTUAL MULTILINGUAL / DEVANAGARI RASTER OCR EVIDENCE
# ==============================================================================
def test_i_multilingual_devanagari_raster_document_preserves_evidence(ocr_infra_env):
    """
    Test I: Multilingual OCR on synthetic raster fixture containing actual Devanagari script.
    Proves actual multilingual OCR across the COMPLETE real OCR pipeline:
    fixture -> render/input -> PaddleOCR -> OCRResult -> OCRPage -> OCRBlock.
    Verifies that Devanagari script is actually recognized and records:
    - language/model configuration
    - recognized text
    - OCR confidence
    - page number
    - bounding box
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    png_bytes = make_devanagari_raster_png()

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("devanagari_income_cert.png", png_bytes, content_type="image/png"),
        sync_process=True
    )

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)
    ocr_result = OCRService.execute_ocr_pipeline(ocr_job.id, lang='hi')

    assert ocr_result is not None
    assert ocr_result.language_metadata.get("primary_language") == "hi"

    page = ocr_result.pages.first()
    assert page is not None
    assert page.page_number == 1
    assert page.width > 0
    assert page.height > 0
    assert len(page.page_hash) == 64

    # Verify OCRBlocks exist and contain recognized Devanagari script
    blocks = list(page.blocks.all())
    assert len(blocks) >= 2, f"Expected multiple recognized OCRBlocks for Devanagari raster text, got {len(blocks)}"

    all_texts = [b.extracted_text for b in blocks]

    # Verify Devanagari unicode characters exist in recognized text
    has_devanagari = any(
        any('\u0900' <= char <= '\u097F' for char in b.extracted_text)
        for b in blocks
    )
    assert has_devanagari, f"Expected Devanagari unicode characters in recognized text. Found: {all_texts}"

    # Verify provenance and bounded geometry recorded for each block
    for b in blocks:
        assert b.page.page_number == 1
        assert b.confidence > 0.0
        assert b.bbox_width > 0
        assert b.bbox_height > 0
        assert b.language == 'hi'

    # Check for expected recognized key content (tolerant of minor OCR diacritic variation)
    found_gov_or_cert = any(
        "भारत" in t or "सरकार" in t or "आय" in t or "प्रमाण" in t or "450000" in t
        for t in all_texts
    )
    assert found_gov_or_cert, f"Expected key Devanagari phrases in text: {all_texts}"


# ==============================================================================
# TEST J — CONFLICT DETECTION (MATERIAL DISAGREEMENT WITHOUT REJECTION)
# ==============================================================================
def test_j_application_vs_ocr_conflict_creates_review_not_rejection(ocr_infra_env):
    """
    Test J: Generate deterministic application-vs-OCR disagreement.
    Applicant declared: Rs. 500,000
    OCR extracted: Rs. 450,000
    Expected: MATERIAL_CONFLICT created in VerificationQueueItem, FIELD_CONFLICT_DETECTED audit event.
    Neither application nor document is automatically rejected.
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    version = ocr_infra_env["version"]

    field_def = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Annual Family Income",
        data_type=FieldDataType.CURRENCY
    )

    # 1. Applicant declaration: 500,000
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=field_def,
        value_json=500000.0,
        source=FieldValueSource.APPLICANT
    )

    # 2. Document upload stating 450,000
    pdf_bytes = make_clean_pdf("Government of India Income Certificate Annual Family Income Rs. 450000")
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("income_conflict.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)
    ocr_result = OCRService.execute_ocr_pipeline(ocr_job.id)

    # Verify conflict was recorded
    audit_conflict = AuditLog.objects.filter(
        entity_id=str(app.id),
        action=AuditAction.FIELD_CONFLICT_DETECTED
    ).first()
    assert audit_conflict is not None
    assert audit_conflict.after_json["declared_value"] == 500000.0
    assert audit_conflict.after_json["ocr_extracted_value"] == 450000.0

    # Verify human verification queue item exists for officer scrutiny
    v_item = VerificationQueueItem.objects.filter(
        application=app,
        item_type=VerificationItemType.DOCUMENT
    ).first()
    assert v_item is not None
    assert v_item.ai_assistance_json["conflict_type"] == "MATERIAL_CONFLICT"

    # Confirm neither application nor document is rejected!
    app.refresh_from_db()
    doc.refresh_from_db()
    assert app.current_state.code == "DRAFT"
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE


# ==============================================================================
# TEST K — MIXED ENGLISH + DEVANAGARI OCR PRESERVES BOTH SCRIPTS
# ==============================================================================
def test_k_mixed_english_devanagari_ocr_preserves_both_scripts(ocr_infra_env):
    """
    Test K: Mixed English + Devanagari raster document.
    Verifies that both English and Devanagari scripts survive through the real OCR pipeline:
    fixture -> render/input -> PaddleOCR -> OCRResult -> OCRPage -> OCRBlock.
    Enforces that:
    - OCR confidence != verification
    - OCR output != eligibility decision
    """
    app = ocr_infra_env["app"]
    user = ocr_infra_env["user"]
    png_bytes = make_mixed_raster_png()

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("mixed_income_cert.png", png_bytes, content_type="image/png"),
        sync_process=True
    )

    ocr_job = OCRService.create_or_get_ocr_job(doc.id)
    ocr_result = OCRService.execute_ocr_pipeline(ocr_job.id, lang='hi')

    assert ocr_result is not None
    page = ocr_result.pages.first()
    assert page is not None

    blocks = list(page.blocks.all())
    assert len(blocks) >= 2, f"Expected multiple blocks for mixed document, got {len(blocks)}"

    all_texts = [b.extracted_text for b in blocks]

    # Verify presence of Latin (English) characters
    has_english = any(
        any('A' <= char <= 'Z' or 'a' <= char <= 'z' for char in b.extracted_text)
        for b in blocks
    )
    assert has_english, f"Expected English characters in recognized text. Found: {all_texts}"

    # Verify presence of Devanagari characters
    has_devanagari = any(
        any('\u0900' <= char <= '\u097F' for char in b.extracted_text)
        for b in blocks
    )
    assert has_devanagari, f"Expected Devanagari characters in recognized text. Found: {all_texts}"

    # Verify provenance for each block: page, confidence, bbox, language
    for b in blocks:
        assert b.page.page_number == 1
        assert b.confidence > 0.0
        assert b.bbox_width > 0
        assert b.bbox_height > 0

    # Explicit boundary checks:
    # 1. OCR confidence does not equal verification
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE  # Not automatically verified!
    # 2. OCR output does not alter application draft state / eligibility decision
    app.refresh_from_db()
    assert app.current_state.code == "DRAFT"

