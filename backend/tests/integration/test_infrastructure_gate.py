import io
import json
import time
import uuid
import socket
import subprocess
import sys
import threading
import concurrent.futures
from datetime import date
from unittest.mock import patch

import pytest
import redis
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction, connection
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.schemes.models import Scheme, SchemeType, SchemeVersion
from apps.workflow.models import WorkflowDefinition
from apps.applications.models import Application
from apps.audit.models import AuditLog, AuditAction
from apps.documents.models import (
    SourceDocument, SourceType, SourceDocumentStatus,
    DocumentRequirement, ApplicantDocumentType,
    ApplicantDocument, DocumentLifecycleStatus, MalwareScanStatus,
    ContentValidationStatus, DocumentVersion, DocumentManifest,
    DocumentProcessingJob, DocumentJobType, DocumentJobStatus,
    DocumentJobExecution, JobExecutionStatus, SecurityQuarantineRecord,
    QuarantineDeletionStatus
)
from apps.documents.services import DocumentIngestionService
from apps.documents.tasks import process_document_pipeline_task
from apps.documents.storage import get_object_storage
from apps.documents.malware_scanner import ClamAVScanner, MockMalwareScanner


# Standard EICAR signature hex matching test.ndb
EICAR_HEX = "58354f2150254041505b345c505a58353428505e2937434329377d2445494341522d5354414e444152442d414e544956495255532d544553542d46494c452124482b482a"
EICAR_BYTES = bytes.fromhex(EICAR_HEX)


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


pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.requires_postgresql,
]


@pytest.fixture
def redis_client():
    r = redis.Redis(
        host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
        port=int(getattr(settings, 'REDIS_PORT', 6379)),
        db=int(getattr(settings, 'REDIS_DB', 0))
    )
    return r


@pytest.fixture
def infra_env(db):
    User.objects.filter(username__in=[
        "infra_applicant", "infra_officer", "infra_admin"
    ]).delete()
    Scheme.objects.filter(code="INFRA_GATE_SCHEME").delete()
    SourceDocument.objects.filter(checksum="f" * 64).delete()

    user = User.objects.create_user(
        username="infra_applicant",
        email="infra_applicant@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    prof = ApplicantProfile.objects.create(
        user=user,
        community="ST",
        annual_family_income=250000,
        date_of_birth=date(2000, 1, 15)
    )

    src_doc = SourceDocument.objects.create(
        title="Infrastructure Verification Guidelines",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="f" * 64,
        content_hash="e" * 64,
        status=SourceDocumentStatus.VERIFIED
    )

    scheme = Scheme.objects.create(
        code="INFRA_GATE_SCHEME",
        name="Infrastructure Gate Test Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )

    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=src_doc
    )

    wf = WorkflowDefinition.objects.create(scheme_version=version, name="Infra WF")
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
        application_number="MOTA/2025-26/INFRA/0001",
        current_state=state_draft
    )

    return {
        "user": user,
        "profile": prof,
        "scheme": scheme,
        "version": version,
        "app": app,
        "req_income": req_income,
    }


# ==============================================================================
# 1. REAL REDIS TASK DISPATCH
# ==============================================================================
def test_1_real_redis_task_dispatch(infra_env, redis_client):
    """Prove real Redis receives and queues dispatched Celery tasks."""
    redis_client.delete("celery")
    doc_id = str(uuid.uuid4())
    corr_id = f"CORR-DISPATCH-{doc_id[:8]}"

    res = process_document_pipeline_task.delay(doc_id, correlation_id=corr_id)
    assert res.id is not None

    queue_len = redis_client.llen("celery")
    assert queue_len > 0, "Task was not pushed to real Redis 'celery' queue."

    # Inspect payload in Redis to confirm serialization
    raw_item = redis_client.lindex("celery", 0)
    data = json.loads(raw_item.decode("utf-8"))
    assert data["headers"]["task"] == "apps.documents.tasks.process_document_pipeline_task"
    assert doc_id in str(data)
    redis_client.delete("celery")


# ==============================================================================
# 2. transaction.on_commit() DISPATCHES AFTER COMMIT
# ==============================================================================
def test_2_transaction_on_commit_dispatches_after_commit(infra_env, redis_client):
    """Prove no task is visible in Redis before DB commit, and is visible after commit."""
    redis_client.delete("celery")
    app = infra_env["app"]
    user = infra_env["user"]
    pdf_bytes = make_clean_pdf("Income Proof Commit Test")

    with transaction.atomic():
        doc = DocumentIngestionService.upload_document(
            application=app,
            actor_user=user,
            document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
            file_obj=SimpleUploadedFile("cert_commit.pdf", pdf_bytes, content_type="application/pdf"),
            sync_process=False
        )
        # Inside transaction: must NOT be dispatched to Redis yet
        assert redis_client.llen("celery") == 0, "Task was prematurely dispatched before DB commit!"

    # Outside transaction: transaction.on_commit() has fired
    assert redis_client.llen("celery") >= 1, "Task was not dispatched after DB commit."
    redis_client.delete("celery")


# ==============================================================================
# 3. ROLLBACK PREVENTS DISPATCH
# ==============================================================================
def test_3_transaction_rollback_prevents_dispatch(infra_env, redis_client):
    """Prove rollback prevents task from ever reaching Redis."""
    redis_client.delete("celery")
    app = infra_env["app"]
    user = infra_env["user"]
    pdf_bytes = make_clean_pdf("Income Proof Rollback Test")

    try:
        with transaction.atomic():
            DocumentIngestionService.upload_document(
                application=app,
                actor_user=user,
                document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
                file_obj=SimpleUploadedFile("cert_rollback.pdf", pdf_bytes, content_type="application/pdf"),
                sync_process=False
            )
            # Force transaction failure
            raise RuntimeError("SIMULATED_TRANSACTION_ROLLBACK")
    except RuntimeError:
        pass

    assert redis_client.llen("celery") == 0, "Task was dispatched despite transaction rollback!"


# ==============================================================================
# 4. REAL CELERY WORKER CONSUMES TASK
# ==============================================================================
def test_4_real_celery_worker_consumes_task(infra_env, redis_client):
    """Run an actual Celery worker process against Redis and PostgreSQL."""
    import os
    redis_client.delete("celery")
    app = infra_env["app"]
    user = infra_env["user"]
    pdf_bytes = make_clean_pdf("Real Worker Document")

    # Upload document to quarantine
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("real_worker.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=False
    )
    doc_id = str(doc.id)

    # Launch Celery worker process against real Redis with exact active test database
    worker_env = os.environ.copy()
    worker_env["POSTGRES_DB"] = connection.settings_dict["NAME"]
    worker_env["TEST_LEVEL"] = "integration"

    worker_p = subprocess.Popen([
        sys.executable, "-m", "celery", "-A", "tribel_scholar",
        "worker", "--pool=solo", "-l", "WARNING", "-n", f"worker_{uuid.uuid4().hex[:6]}@localhost"
    ], env=worker_env)

    try:
        # Wait up to 50 seconds for worker to pick up task and transition document to SAFE
        max_wait = 50
        start = time.time()
        completed = False

        while time.time() - start < max_wait:
            doc.refresh_from_db()
            if doc.lifecycle_status == DocumentLifecycleStatus.SAFE:
                completed = True
                break
            time.sleep(0.5)

        assert completed is True, f"Worker did not process document {doc_id} to SAFE (status: {doc.lifecycle_status})."

        job = DocumentProcessingJob.objects.filter(document_id=doc_id).first()
        assert job.status == DocumentJobStatus.COMPLETED
        assert DocumentManifest.objects.filter(document_id=doc_id).exists() is True

    finally:
        worker_p.terminate()
        try:
            worker_p.wait(timeout=5)
        except Exception:
            worker_p.kill()
        redis_client.delete("celery")


# ==============================================================================
# 5. DUPLICATE TASK DELIVERY
# ==============================================================================
def test_5_duplicate_task_delivery_is_idempotent(infra_env):
    """Submit the same logical processing job twice. Exactly one transition occurs."""
    app = infra_env["app"]
    user = infra_env["user"]
    pdf_bytes = make_clean_pdf("Duplicate Task Proof")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("dup.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE

    manifests_initial = DocumentManifest.objects.filter(document=doc).count()
    assert manifests_initial == 1

    # Replay task delivery
    replayed_doc = DocumentIngestionService.process_document(doc.id)
    assert replayed_doc.lifecycle_status == DocumentLifecycleStatus.SAFE

    # No duplicate manifest or promotions
    assert DocumentManifest.objects.filter(document=doc).count() == 1
    promoted_audits = AuditLog.objects.filter(
        entity_id=str(doc.id),
        action=AuditAction.DOCUMENT_PROMOTED
    ).count()
    assert promoted_audits == 1


# ==============================================================================
# 6. TWO WORKERS SAME DOCUMENT RACE CONDITION
# ==============================================================================
def test_6_two_workers_same_document_version_race_condition(infra_env):
    """Two workers schedule/process the same document concurrently. Exactly one promotes."""
    app = infra_env["app"]
    user = infra_env["user"]
    pdf_bytes = make_clean_pdf("Two Worker Concurrency Proof")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("concur.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=False
    )

    def worker_run(worker_name):
        return DocumentIngestionService.process_document(
            document_id=doc.id,
            worker_id=worker_name
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker_run, "celery@worker-1")
        f2 = executor.submit(worker_run, "celery@worker-2")
        r1 = f1.result()
        r2 = f2.result()

    assert r1.lifecycle_status == DocumentLifecycleStatus.SAFE
    assert r2.lifecycle_status == DocumentLifecycleStatus.SAFE

    # Exactly 1 manifest created despite two concurrent workers
    assert DocumentManifest.objects.filter(document=doc).count() == 1
    # Exactly 1 promotion event
    promoted_events = AuditLog.objects.filter(
        entity_id=str(doc.id),
        action=AuditAction.DOCUMENT_PROMOTED
    ).count()
    assert promoted_events == 1


# ==============================================================================
# 7. WORKER CRASH SIMULATION & RECOVERY
# ==============================================================================
def test_7_worker_crash_simulation_and_recovery(infra_env):
    """Worker crashes before promotion commit. Document enters recoverable state and retries."""
    app = infra_env["app"]
    user = infra_env["user"]
    pdf_bytes = make_clean_pdf("Crash Recovery Proof")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("crash.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=False
    )

    # Simulate crash before promotion commit
    with patch("apps.documents.models.DocumentManifest.objects.create", side_effect=RuntimeError("WORKER_PROCESS_KILLED")):
        with pytest.raises(RuntimeError):
            DocumentIngestionService.process_document(doc.id)

    doc.refresh_from_db()
    # Must NOT become SAFE
    assert doc.lifecycle_status != DocumentLifecycleStatus.SAFE
    assert doc.lifecycle_status in (
        DocumentLifecycleStatus.SCANNING,
        DocumentLifecycleStatus.PROMOTION_PENDING,
        DocumentLifecycleStatus.QUARANTINED
    )

    # Recover via retry
    recovered_doc = DocumentIngestionService.process_document(doc.id)
    assert recovered_doc.lifecycle_status == DocumentLifecycleStatus.SAFE
    assert DocumentManifest.objects.filter(document=doc).count() == 1


# ==============================================================================
# 8. REDIS RESTART & RECOVERY
# ==============================================================================
def test_8_redis_restart_and_recovery(infra_env):
    """Test broker stop and restart resilience using an ephemeral Redis instance."""
    redis_exe = "C:\\Users\\kishu\\tools\\redis\\redis-server.exe"
    test_port = 6385
    processes = []

    def wait_for_redis_conn(r_instance, timeout=6.0):
        start_t = time.time()
        while time.time() - start_t < timeout:
            try:
                if r_instance.ping():
                    return True
            except Exception:
                time.sleep(0.2)
        return False

    # 1. Start temporary Redis instance
    p1 = subprocess.Popen([redis_exe, "--port", str(test_port)])
    processes.append(p1)
    r = redis.Redis(host="127.0.0.1", port=test_port, socket_timeout=1, socket_connect_timeout=1)
    assert wait_for_redis_conn(r, timeout=6.0) is True, "Ephemeral Redis instance failed to start."

    try:
        # 2. Stop Redis
        p1.terminate()
        p1.wait(timeout=5)
        r.connection_pool.disconnect()

        # 3. Verify failure behavior
        with pytest.raises((redis.exceptions.ConnectionError, redis.exceptions.TimeoutError)):
            r.ping()

        # 4. Restart Redis
        p2 = subprocess.Popen([redis_exe, "--port", str(test_port)])
        processes.append(p2)
        r2 = redis.Redis(host="127.0.0.1", port=test_port, socket_timeout=2, socket_connect_timeout=2)
        assert wait_for_redis_conn(r2, timeout=6.0) is True, "Ephemeral Redis failed to restart."

        # 5. Verify successful reconnection and task enqueue
        r2.rpush("celery_recovery_test", "recovered_job_data")
        assert r2.llen("celery_recovery_test") == 1

    finally:
        for proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


# ==============================================================================
# 9. REAL CLAMAV CLEAN SCAN
# ==============================================================================
def test_9_real_clamav_clean_scan(require_clamav):
    """Scan clean document against live ClamAV daemon over TCP socket."""
    scanner = ClamAVScanner(
        host=getattr(settings, 'CLAMAV_HOST', '127.0.0.1'),
        port=int(getattr(settings, 'CLAMAV_PORT', 3310))
    )
    clean_bytes = make_clean_pdf("ClamAV Clean Scan Test")
    status, detail = scanner.scan(clean_bytes)
    assert status == MalwareScanStatus.CLEAN
    assert "Clean" in detail


# ==============================================================================
# 10. REAL CLAMAV EICAR DETECTION
# ==============================================================================
def test_10_real_clamav_eicar_detection(require_clamav, infra_env):
    """Stream EICAR test signature to live ClamAV daemon. Must reject document."""
    scanner = ClamAVScanner(
        host=getattr(settings, 'CLAMAV_HOST', '127.0.0.1'),
        port=int(getattr(settings, 'CLAMAV_PORT', 3310))
    )
    status, detail = scanner.scan(EICAR_BYTES)
    assert status == MalwareScanStatus.INFECTED
    assert "FOUND" in detail or "Threat detected" in detail

    # End-to-end rejection through ingestion pipeline
    app = infra_env["app"]
    user = infra_env["user"]
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("eicar.pdf", make_clean_pdf() + EICAR_BYTES, content_type="application/pdf"),
        sync_process=False
    )

    with patch("apps.documents.services.get_malware_scanner", return_value=scanner):
        res = DocumentIngestionService.process_document(doc.id)
        assert res.lifecycle_status == DocumentLifecycleStatus.REJECTED
        assert res.lifecycle_status != DocumentLifecycleStatus.SAFE
        assert "MALWARE_DETECTED" in res.rejection_reason


# ==============================================================================
# 11. CLAMAV UNAVAILABLE POLICY
# ==============================================================================
def test_11_clamav_unavailable_fails_safe_to_quarantine_error(infra_env):
    """If ClamAV is unreachable, system enters QUARANTINED/SCAN_ERROR, never SAFE."""
    scanner = ClamAVScanner(host="127.0.0.1", port=33999, timeout=0.5)
    status, detail = scanner.scan(b"Some document bytes")
    assert status == MalwareScanStatus.ERROR
    assert "unreachable" in detail

    app = infra_env["app"]
    user = infra_env["user"]
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("av_down.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=False
    )

    with patch("apps.documents.services.get_malware_scanner", return_value=scanner):
        res = DocumentIngestionService.process_document(doc.id)
        assert res.lifecycle_status == DocumentLifecycleStatus.QUARANTINED
        assert res.lifecycle_status != DocumentLifecycleStatus.SAFE
        assert "SCAN_ERROR" in res.rejection_reason


# ==============================================================================
# 12. SAFE STORAGE PROMOTION AND CHECKSUM INTEGRITY
# ==============================================================================
def test_12_safe_storage_promotion_and_checksum_integrity(infra_env):
    """Put quarantine -> promote safe -> read stream -> sha256 checksum matches."""
    app = infra_env["app"]
    user = infra_env["user"]
    pdf_bytes = make_clean_pdf("Checksum Validation Proof")

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("cert_check.pdf", pdf_bytes, content_type="application/pdf"),
        sync_process=True
    )
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE

    storage = get_object_storage()
    with storage.get_stream(doc.storage_key) as f:
        read_bytes = f.read()

    import hashlib
    assert hashlib.sha256(read_bytes).hexdigest() == doc.sha256
    assert read_bytes == pdf_bytes


# ==============================================================================
# 13. PROMOTION FAILURE PREVENTS SAFE STATE
# ==============================================================================
def test_13_storage_promotion_failure_prevents_safe_state(infra_env):
    """Storage failure during promotion results in recoverable SCANNING state, never SAFE."""
    app = infra_env["app"]
    user = infra_env["user"]
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("prom_fail.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=False
    )

    with patch("apps.documents.storage.LocalObjectStorage.promote_to_safe", side_effect=OSError("Disk write error")):
        res = DocumentIngestionService.process_document(doc.id)
        assert res.lifecycle_status != DocumentLifecycleStatus.SAFE
        assert res.lifecycle_status == DocumentLifecycleStatus.SCANNING
        job = DocumentProcessingJob.objects.filter(document=doc).first()
        assert job.status == DocumentJobStatus.FAILED
        assert job.error_code == "PROMOTION_ERROR"


# ==============================================================================
# 14. SECURITY QUARANTINE RETENTION RECORD
# ==============================================================================
def test_14_security_quarantine_retention_record_created(infra_env):
    """Infected document produces SecurityQuarantineRecord and preserves evidence."""
    app = infra_env["app"]
    user = infra_env["user"]
    infected_payload = make_clean_pdf() + b"\n% __MOCK_INFECTED__\n"

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("infected_retention.pdf", infected_payload, content_type="application/pdf"),
        sync_process=True
    )

    assert doc.lifecycle_status == DocumentLifecycleStatus.REJECTED

    record = SecurityQuarantineRecord.objects.filter(document=doc).first()
    assert record is not None
    assert record.deletion_status == QuarantineDeletionStatus.RETAINED
    assert record.retention_until > timezone.now()
    assert "MockMalwareScanner" in record.scanner
    assert record.deleted_at is None

    # Quarantine file remains intact for forensic retention
    storage = get_object_storage()
    assert storage.exists(record.quarantine_storage_key) is True


# ==============================================================================
# 15. CORRELATION ID PROPAGATION ACROSS LAYERS
# ==============================================================================
def test_15_correlation_id_propagation_across_layers(infra_env):
    """Correlation ID propagates through HTTP, DB, Celery execution, and AuditLog."""
    app = infra_env["app"]
    user = infra_env["user"]
    corr_id = f"MOTA-CORR-TRACE-{uuid.uuid4().hex[:8]}"

    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("corr_test.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=False
    )

    processed_doc = DocumentIngestionService.process_document(
        document_id=doc.id,
        correlation_id=corr_id,
        task_id="task-uuid-corr-test",
        worker_id="worker-node-alpha"
    )

    # 1. Database Job entity
    job = DocumentProcessingJob.objects.filter(document=doc).first()
    assert job.correlation_id is not None

    # 2. Execution Record entity
    execution = DocumentJobExecution.objects.filter(document=doc).first()
    assert execution.correlation_id == corr_id
    assert execution.worker_id == "worker-node-alpha"

    # 3. AuditLog entity
    promoted_audit = AuditLog.objects.filter(
        entity_id=str(doc.id),
        action=AuditAction.DOCUMENT_PROMOTED
    ).first()
    assert promoted_audit is not None
    assert promoted_audit.after_json.get("correlation_id") == corr_id


# ==============================================================================
# 16. STRUCTURED SECURITY LOGGING (NO PII)
# ==============================================================================
def test_16_structured_security_logging_no_pii(infra_env, caplog):
    """Task log contains structured JSON with zero document bytes, passwords, or PII."""
    import logging
    app = infra_env["app"]
    user = infra_env["user"]
    doc = DocumentIngestionService.upload_document(
        application=app,
        actor_user=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_obj=SimpleUploadedFile("obs_test.pdf", make_clean_pdf(), content_type="application/pdf"),
        sync_process=False
    )

    corr_id = f"CORR-LOG-{uuid.uuid4().hex[:8]}"
    with caplog.at_level(logging.INFO, logger="apps.documents"):
        process_document_pipeline_task.apply(args=[str(doc.id)], kwargs={"correlation_id": corr_id})

    found_structured_log = False
    for record in caplog.records:
        try:
            parsed = json.loads(record.message)
            if parsed.get("event_type") == "celery_task_execution":
                found_structured_log = True
                assert parsed["correlation_id"] == corr_id
                assert parsed["document_id"] == str(doc.id)
                assert "duration_ms" in parsed
                assert parsed["result_status"] == "SUCCESS"
                assert "job_type" in parsed
                # Prohibit sensitive data
                assert "password" not in parsed
                assert "token" not in parsed
                assert "%PDF" not in record.message
        except (ValueError, TypeError):
            continue

    assert found_structured_log is True, "Structured task execution JSON log not found."


# ==============================================================================
# 17. CONCURRENT UPLOAD RATE LIMITING
# ==============================================================================
def test_17_concurrent_upload_rate_limiting(infra_env, settings):
    """Concurrent upload burst enforces limit and prevents uncontrolled Celery jobs."""
    settings.MAX_UPLOADS_PER_MINUTE = 5
    cache.clear()
    client = APIClient()
    client.force_authenticate(user=infra_env["user"])

    pdf_bytes = make_clean_pdf("Rate Limit Test")
    responses = []

    # Issue 20 upload requests
    for i in range(20):
        file_obj = SimpleUploadedFile(f"burst_{i}.pdf", pdf_bytes, content_type="application/pdf")
        resp = client.post(
            f"/api/v1/applications/{infra_env['app'].id}/documents/",
            data={"document_type": ApplicantDocumentType.INCOME_CERTIFICATE, "file": file_obj},
            format="multipart"
        )
        responses.append(resp.status_code)

    accepted = [code for code in responses if code == status.HTTP_201_CREATED]
    throttled = [code for code in responses if code == status.HTTP_429_TOO_MANY_REQUESTS]

    assert len(accepted) == 5, f"Expected 5 accepted uploads, got {len(accepted)}"
    assert len(throttled) == 15, f"Expected 15 throttled uploads, got {len(throttled)}"
