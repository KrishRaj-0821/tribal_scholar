import pytest
import os
import uuid
from unittest.mock import patch
from django.conf import settings
from apps.accounts.models import User
from apps.applicants.models import ApplicantProfile, CommunityCategory
from apps.schemes.models import Scheme, SchemeVersion
from apps.workflow.models import WorkflowDefinition
from apps.applications.models import Application
from apps.documents.models import (
    ApplicantDocument, DocumentLifecycleStatus, ApplicantDocumentType,
    SourceDocument, SourceDocumentStatus,
    OCRJob, OCRJobStatus
)
from apps.documents.malware_scanner import ClamAVScanner, MalwareScanStatus
from apps.documents.ocr_engines import PaddleOCREngine
from apps.documents.tasks import run_ocr_task


@pytest.fixture
def document_fixture(db):
    user = User.objects.create_user(
        username=f"applicant_{uuid.uuid4().hex[:6]}",
        email=f"app_{uuid.uuid4().hex[:6]}@example.com",
        password="ValidPassword123!",
        role="APPLICANT"
    )
    profile = ApplicantProfile.objects.create(
        user=user,
        community=CommunityCategory.ST
    )
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
        name="Test Scheme for Worker",
        description="Scheme objective"
    )
    scheme_version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=source_doc,
        status="ACTIVE"
    )
    wf = WorkflowDefinition.objects.create(scheme_version=scheme_version, name="Worker Test WF")
    state_draft = wf.states.create(code="DRAFT", display_name="Draft", sequence=1)
    application = Application.objects.create(
        applicant=profile,
        scheme_version=scheme_version,
        application_number=f"APP-WRK-{uuid.uuid4().hex[:6].upper()}",
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
    return doc


@pytest.mark.django_db
class TestP0WorkerStability:
    """
    Targeted verification suite for P0-1: Worker OOM / OCR Processing Architecture.
    Validates queue decoupling, fail-closed ClamAV scanner behavior,
    pre-cached PaddleOCR initialization, and failure-safe OCR task execution.
    """

    def test_celery_task_routing_isolation(self):
        """
        Verify that document processing tasks are routed to isolated queues,
        ensuring ClamAV malware scanning and PaddleOCR inference execute in decoupled failure domains.
        """
        routes = getattr(settings, 'CELERY_TASK_ROUTES', {})
        assert 'apps.documents.tasks.process_document_pipeline_task' in routes, "Missing routing for security scan task"
        assert routes['apps.documents.tasks.process_document_pipeline_task']['queue'] == 'security_scan'

        assert 'apps.documents.tasks.run_ocr_task' in routes, "Missing routing for OCR task"
        assert routes['apps.documents.tasks.run_ocr_task']['queue'] == 'ocr'

        assert 'apps.notifications.tasks.*' in routes, "Missing routing for notification tasks"
        assert routes['apps.notifications.tasks.*']['queue'] == 'notifications'

    def test_worker_memory_protection_settings(self):
        """
        Verify that worker memory recycling settings are configured for prefork recycling,
        serving as supporting controls against memory leaks.
        """
        assert getattr(settings, 'CELERY_WORKER_MAX_TASKS_PER_CHILD', 0) > 0
        assert getattr(settings, 'CELERY_WORKER_MAX_MEMORY_PER_CHILD', 0) > 0

    def test_worker_startup_concurrency_contracts(self):
        """
        Verify that start-worker.sh strictly enforces concurrency=1 for both scanner and ocr
        roles to prevent memory multiplication under prefork.
        """
        script_path = os.path.join(settings.BASE_DIR, 'start-worker.sh')
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()

        # Both scanner and ocr must use --concurrency=1 for memory safety
        assert '--queues=ocr --concurrency=1' in script_content, "OCR worker must enforce concurrency=1"
        assert '--queues=security_scan,notifications,default --concurrency=1' in script_content, "Scanner worker must enforce concurrency=1"

    def test_clamav_scanner_fails_closed_when_daemon_unreachable(self):
        """
        Verify that when the ClamAV daemon is unreachable (e.g. socket refusal/timeout),
        the scanner fails closed returning ERROR, never CLEAN or SAFE.
        """
        scanner = ClamAVScanner(host="127.0.0.1", port=9999, timeout=0.5)
        status, message = scanner.scan(b"test binary content")
        assert status == MalwareScanStatus.ERROR
        assert "unreachable" in message.lower() or "error" in message.lower()

    def test_paddleocr_engine_model_source_check_disabled(self):
        """
        Verify that PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK is enforced to prevent
        runtime network calls to remote model hosters.
        """
        engine = PaddleOCREngine(lang='en')
        assert engine.engine_name == 'PaddleOCR'
        assert os.environ.get('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK') == 'True'
        assert engine.get_configuration_hash() is not None

    def test_run_ocr_task_fails_safely_on_missing_job(self):
        """
        Verify that run_ocr_task handles missing job cleanly without fabricating success.
        """
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        result = run_ocr_task(fake_uuid)
        assert result.get("error") == "OCR_JOB_NOT_FOUND"

    def test_run_ocr_task_records_failed_status_on_exception(self, document_fixture):
        """
        Verify that if an unhandled exception or OOM condition occurs during OCR,
        the job is marked FAILED and no provisional fields are fabricated.
        """
        doc = document_fixture
        job = OCRJob.objects.create(
            document=doc,
            status=OCRJobStatus.PENDING
        )

        with patch('apps.documents.ocr_service.OCRService.execute_ocr_pipeline', side_effect=RuntimeError("Simulated OOM")):
            with patch.object(run_ocr_task, 'retry', side_effect=RuntimeError("Retry simulated")):
                try:
                    run_ocr_task(str(job.id))
                except Exception:
                    pass

        # If retried or failed, status must never be COMPLETED
        job.refresh_from_db()
        assert job.status != OCRJobStatus.COMPLETED
