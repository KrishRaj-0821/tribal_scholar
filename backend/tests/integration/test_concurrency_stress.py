import pytest
import concurrent.futures
from datetime import date, timedelta
from unittest.mock import patch
from django.utils import timezone
from django.db import transaction, connections
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.requires_postgresql,
]

@pytest.fixture(autouse=True)
def ensure_postgresql_backend(db):
    """
    STRICT INTEGRITY GATE:
    Concurrency tests must NEVER skip. If the active database backend is not PostgreSQL,
    fail immediately with a clear assertion.
    """
    from django.db import connection
    assert connection.vendor == "postgresql", "Concurrency tests require PostgreSQL."

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.schemes.models import (
    Scheme, SchemeType, SchemeVersion, SchemeRule,
    RuleCategory, RuleOperator, RuleSeverity, RuleStatus
)
from apps.documents.models import (
    SourceDocument, SourceType, SourceDocumentStatus,
    DocumentRequirement, DocumentValidityPolicy, ApplicantDocumentType, ApplicantDocument,
    DocumentLifecycleStatus
)
from apps.workflow.models import WorkflowDefinition, WorkflowState, ApplicationStatusHistory
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue,
    ApplicationSubmissionSnapshot, EligibilityInputSnapshot, EligibilityEvaluation,
    IdempotencyRecord, FieldDataType, FieldValueSource
)
from apps.applications.services import ApplicationSubmissionService
from apps.audit.models import AuditLog, AuditAction


@pytest.fixture
def stress_env(db):
    """
    Creates a robust, isolated environment for PostgreSQL concurrency stress testing.
    """
    user = User.objects.create_user(
        username="concurrency_applicant",
        email="concurrency@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    applicant = ApplicantProfile.objects.create(
        user=user,
        community="ST",
        annual_family_income=450000,
        date_of_birth=date(2001, 8, 12)
    )
    doc = SourceDocument.objects.create(
        title="Concurrency Hardening Official Guidelines 2025-26",
        academic_year="2025-26",
        source_type=SourceType.GUIDELINE,
        checksum="1" * 64,
        content_hash="2" * 64,
        status=SourceDocumentStatus.VERIFIED
    )
    scheme = Scheme.objects.create(
        code="CONC_TEST",
        name="Concurrency Authority Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=doc
    )

    # Workflow
    wf = WorkflowDefinition.objects.create(scheme_version=version, name="Concurrency Workflow")
    draft_state = wf.states.create(code="DRAFT", display_name="Draft", sequence=1)
    submitted_state = wf.states.create(code="SUBMITTED", display_name="Submitted", sequence=2)
    wf.transitions.create(from_state=draft_state, to_state=submitted_state, required_role="APPLICANT")

    # Income rule
    income_rule = SchemeRule.objects.create(
        scheme_version=version,
        rule_code="CONC_INCOME_CEILING",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.annual_family_income",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=600000,
        failure_message="Income exceeds 600000",
        source_document=doc,
        status=RuleStatus.ACTIVE
    )

    # Form field definition with strict validation schema
    fdef = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Annual Income",
        data_type=FieldDataType.CURRENCY,
        required=True,
        validation_schema={"max": 600000, "min": 0},
        source_document=doc,
        status="ACTIVE"
    )

    # Document requirement
    doc_req = DocumentRequirement.objects.create(
        scheme_version=version,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        required=True,
        when_required="APPLICATION",
        validity_policy=DocumentValidityPolicy.FINANCIAL_YEAR_BOUND,
        source_document=doc
    )

    # Upload document to satisfy manifest requirement
    doc_upload = ApplicantDocument.objects.create(
        applicant=user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        file_name="income_cert.pdf",
        checksum="3" * 64,
        lifecycle_status=DocumentLifecycleStatus.SAFE,
        is_verified_by_officer=False
    )

    app = Application.objects.create(
        applicant=applicant,
        scheme_version=version,
        application_number="MOTA/2025-26/CONC/0001",
        current_state=draft_state,
        revision_number=1
    )

    # Populate form answer
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=450000,
        source=FieldValueSource.APPLICANT
    )

    return {
        "user": user,
        "applicant": applicant,
        "scheme": scheme,
        "version": version,
        "application": app,
        "draft_state": draft_state,
        "submitted_state": submitted_state,
        "fdef": fdef,
        "doc": doc
    }


# =============================================================================
# 5 & 7. ACTUAL CONCURRENCY STRESS TEST (20 CONCURRENT SUBMISSIONS - DIFFERENT KEYS)
# =============================================================================
@pytest.mark.django_db(transaction=True)
def test_concurrency_stress_20_different_keys_single_winner(stress_env):
    """
    STRESS TEST GATE:
    Launches 20 concurrent submission attempts with different Idempotency-Key values
    against the same DRAFT application.

    PostgreSQL Transactional Authority Requirements:
    1. Exactly one request succeeds in transitioning DRAFT -> SUBMITTED.
    2. All other 19 requests fail safely (ValidationError / already submitted).
    3. Exactly 1 ApplicationSubmissionSnapshot created.
    4. Exactly 1 ApplicationStatusHistory transition created.
    5. Exactly 1 APPLICATION_SUBMITTED AuditLog entry created.
    6. Revision number increments by exactly 1.
    7. Zero database corruption or duplicate transitions.
    """
    app = stress_env["application"]
    user = stress_env["user"]
    num_requests = 20

    def submit_attempt(key_index):
        # Open separate connection for thread
        connections.close_all()
        idempotency_key = f"CONC-DIFF-KEY-{key_index:03d}"
        try:
            receipt, status_code = ApplicationSubmissionService.submit(
                application=app,
                actor_user=user,
                idempotency_key=idempotency_key
            )
            return {"success": True, "status": status_code, "receipt": receipt, "key": idempotency_key}
        except Exception as e:
            return {"success": False, "error": str(e), "key": idempotency_key}
        finally:
            connections.close_all()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(submit_attempt, i) for i in range(num_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    # Invariant 1: Exactly one submission winner
    assert len(successes) == 1, (
        f"Concurrency failure: expected exactly 1 winner, got {len(successes)}. "
        f"Successes: {successes}"
    )
    # Invariant 2: Exactly 19 requests fail safely
    assert len(failures) == num_requests - 1, (
        f"Expected {num_requests - 1} safe failures, got {len(failures)}"
    )

    # Invariant 3: Safe failure reason matches documented state machine error
    for f in failures:
        assert "cannot be submitted from current state" in f["error"] or "SUBMITTED" in f["error"]

    # Verify Database State under PostgreSQL
    connections.close_all()
    app.refresh_from_db()
    assert app.current_state.code == "SUBMITTED"
    assert app.revision_number == 2  # Incremented from 1 to 2 exactly once

    # Invariant 4: No duplicate submission snapshot
    snapshot_count = ApplicationSubmissionSnapshot.objects.filter(application=app).count()
    assert snapshot_count == 1, f"Expected 1 submission snapshot, found {snapshot_count}"

    # Invariant 5: No duplicate state transition history
    history_count = ApplicationStatusHistory.objects.filter(application=app).count()
    assert history_count == 1, f"Expected 1 status history event, found {history_count}"

    # Invariant 6: No duplicate audit events
    audit_count = AuditLog.objects.filter(
        entity_id=str(app.id),
        action=AuditAction.APPLICATION_SUBMITTED
    ).count()
    assert audit_count == 1, f"Expected 1 APPLICATION_SUBMITTED audit log, found {audit_count}"


# =============================================================================
# 6. SAME IDEMPOTENCY KEY RACE (20 CONCURRENT SUBMISSIONS - IDENTICAL KEY)
# =============================================================================
@pytest.mark.django_db(transaction=True)
def test_same_idempotency_key_race_20_threads_zero_duplicates(stress_env):
    """
    STRESS TEST GATE:
    Launches 20 concurrent submission attempts with the EXACT SAME Idempotency-Key
    against the same DRAFT application.

    Expected:
    1. Exactly one logical submission occurs.
    2. All 20 threads return the exact same stored response body and HTTP 200.
    3. No thread receives HTTP 500 or unhandled unique-constraint crash.
    4. Exactly 1 ApplicationSubmissionSnapshot, 1 status history, and 1 audit event.
    """
    app = stress_env["application"]
    user = stress_env["user"]
    shared_key = "SHARED-IDEMPOTENCY-KEY-999"
    num_requests = 20

    def submit_same_key():
        connections.close_all()
        try:
            receipt, status_code = ApplicationSubmissionService.submit(
                application=app,
                actor_user=user,
                idempotency_key=shared_key
            )
            return {"success": True, "status": status_code, "receipt": receipt}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            connections.close_all()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(submit_same_key) for _ in range(num_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Every single thread must receive the exact same successful receipt
    failures = [r for r in results if not r["success"]]
    assert len(failures) == 0, f"Expected 0 failures during replay race, got errors: {failures}"

    receipt_hashes = {r["receipt"]["snapshot_hash"] for r in results}
    assert len(receipt_hashes) == 1, f"Receipt mismatch across threads: {receipt_hashes}"

    receipt_numbers = {r["receipt"]["receipt_number"] for r in results}
    assert len(receipt_numbers) == 1, f"Receipt number mismatch across threads: {receipt_numbers}"

    # Verify Database Integrity
    connections.close_all()
    app.refresh_from_db()
    assert app.current_state.code == "SUBMITTED"
    assert app.revision_number == 2

    assert ApplicationSubmissionSnapshot.objects.filter(application=app).count() == 1
    assert ApplicationStatusHistory.objects.filter(application=app).count() == 1
    assert AuditLog.objects.filter(entity_id=str(app.id), action=AuditAction.APPLICATION_SUBMITTED).count() == 1
    assert IdempotencyRecord.objects.filter(key=shared_key).count() == 1


# =============================================================================
# 8. CONCURRENT FIELD PATCH (10 CONCURRENT PATCH REQUESTS WITH STALE REVISION)
# =============================================================================
@pytest.mark.django_db(transaction=True)
def test_concurrent_field_patch_10_requests_stale_revisions_produce_409(stress_env):
    """
    STRESS TEST GATE:
    Launches 10 concurrent PATCH requests to edit application form fields,
    all starting from the same initial revision number (revision 1).

    Expected:
    1. Exactly one matching revision succeeds (revision increments from 1 -> 2).
    2. The other 9 requests receive HTTP 409 CONFLICT.
    3. No lost updates, no corrupted revision numbers.
    """
    app = stress_env["application"]
    user = stress_env["user"]
    initial_revision = app.revision_number
    num_requests = 10

    def patch_attempt(thread_idx):
        connections.close_all()
        client = APIClient()
        client.force_authenticate(user=user)
        try:
            response = client.patch(
                f"/api/v1/applications/{app.id}/form/",
                data={
                    "expected_revision_number": initial_revision,
                    "answers": {"annual_family_income": 400000 + (thread_idx * 1000)}
                },
                format="json"
            )
            return {"status": response.status_code, "data": response.data}
        finally:
            connections.close_all()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(patch_attempt, i) for i in range(num_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    success_responses = [r for r in results if r["status"] == status.HTTP_200_OK]
    conflict_responses = [r for r in results if r["status"] == status.HTTP_409_CONFLICT]

    assert len(success_responses) == 1, (
        f"Expected exactly 1 PATCH success, got {len(success_responses)}. Results: {results}"
    )
    assert len(conflict_responses) == num_requests - 1, (
        f"Expected {num_requests - 1} 409 CONFLICT responses, got {len(conflict_responses)}"
    )

    connections.close_all()
    app.refresh_from_db()
    # Revision number must be exactly 2 (incremented once by the sole winner)
    assert app.revision_number == initial_revision + 1


# =============================================================================
# 9. SNAPSHOT IMMUTABILITY (ALL ACCESS PATHS BLOCKED ON POSTGRESQL)
# =============================================================================
@pytest.mark.django_db
def test_submission_and_eligibility_snapshot_immutability(stress_env):
    """
    STRESS TEST GATE:
    Verifies that under PostgreSQL, snapshots are strictly immutable across all intended access paths:
    1. instance.save() -> raises ValidationError
    2. instance.delete() -> raises ValidationError
    3. QuerySet.update() -> raises ValidationError
    4. QuerySet.delete() -> raises ValidationError
    """
    app = stress_env["application"]
    version = stress_env["version"]

    # 1. Test ApplicationSubmissionSnapshot Immutability
    sub_snap = ApplicationSubmissionSnapshot.objects.create(
        application=app,
        revision_number=1,
        applicant_data_json={"test": "data"},
        form_values_json={"annual_family_income": 450000},
        scheme_version=version,
        snapshot_hash="s" * 64
    )

    # Path A: instance.save() update attempt
    sub_snap.applicant_data_json = {"tampered": True}
    with pytest.raises(ValidationError, match="ApplicationSubmissionSnapshot is strictly immutable"):
        sub_snap.save()

    # Path B: instance.delete() attempt
    with pytest.raises(ValidationError, match="ApplicationSubmissionSnapshot cannot be deleted"):
        sub_snap.delete()

    # Path C: QuerySet.update() attempt
    with pytest.raises(ValidationError, match="Immutable snapshot records cannot be modified via bulk update"):
        ApplicationSubmissionSnapshot.objects.filter(id=sub_snap.id).update(snapshot_hash="tampered" + "0" * 56)

    # Path D: QuerySet.delete() attempt
    with pytest.raises(ValidationError, match="Immutable snapshot records cannot be deleted"):
        ApplicationSubmissionSnapshot.objects.filter(id=sub_snap.id).delete()

    # 2. Test EligibilityInputSnapshot & EligibilityEvaluation Immutability
    eval_rec = EligibilityEvaluation.objects.create(
        application=app,
        scheme_version=version,
        engine_version="2.0.0",
        result={"status": "ELIGIBLE"},
        result_hash="e" * 64
    )
    input_snap = EligibilityInputSnapshot.objects.create(
        evaluation=eval_rec,
        payload_json={"applicant": {"income": 450000}},
        payload_hash="p" * 64
    )

    # Path A: instance.save() update
    input_snap.payload_json = {"tampered": True}
    with pytest.raises(ValidationError, match="EligibilityInputSnapshot is strictly immutable"):
        input_snap.save()

    eval_rec.result = {"tampered": True}
    with pytest.raises(ValidationError, match="EligibilityEvaluation records are strictly immutable"):
        eval_rec.save()

    # Path B: instance.delete()
    with pytest.raises(ValidationError, match="EligibilityInputSnapshot cannot be deleted"):
        input_snap.delete()

    with pytest.raises(ValidationError, match="EligibilityEvaluation records cannot be deleted"):
        eval_rec.delete()

    # Path C: QuerySet.update()
    with pytest.raises(ValidationError, match="Immutable snapshot records cannot be modified via bulk update"):
        EligibilityInputSnapshot.objects.filter(id=input_snap.id).update(payload_hash="tampered" + "0" * 56)

    with pytest.raises(ValidationError, match="EligibilityEvaluation records cannot be modified via bulk update"):
        EligibilityEvaluation.objects.filter(id=eval_rec.id).update(result_hash="tampered" + "0" * 56)

    # Path D: QuerySet.delete()
    with pytest.raises(ValidationError, match="Immutable snapshot records cannot be deleted"):
        EligibilityInputSnapshot.objects.filter(id=input_snap.id).delete()

    with pytest.raises(ValidationError, match="EligibilityEvaluation records cannot be deleted"):
        EligibilityEvaluation.objects.filter(id=eval_rec.id).delete()


# =============================================================================
# 10. AUDIT EVENT ATOMICITY (FULL ROLLBACK ON TRANSACTION FAILURE)
# =============================================================================
@pytest.mark.django_db
def test_submission_transaction_failure_causes_full_rollback(stress_env):
    """
    STRESS TEST GATE:
    Injects a deliberate failure after submission snapshot creation but before final commit.

    Expected:
    FULL ROLLBACK.
    No submitted state, no status history, no snapshot, and no submission audit event
    may remain committed.
    """
    app = stress_env["application"]
    user = stress_env["user"]

    # Verify initial clean DRAFT state
    assert app.current_state.code == "DRAFT"
    initial_revision = app.revision_number

    # Inject failure during AuditLog creation (inside the transaction)
    with patch("apps.audit.models.AuditLog.objects.create", side_effect=RuntimeError("SIMULATED_DB_FAILURE_DURING_AUDIT")):
        with pytest.raises(RuntimeError, match="SIMULATED_DB_FAILURE_DURING_AUDIT"):
            ApplicationSubmissionService.submit(
                application=app,
                actor_user=user,
                idempotency_key="ROLLBACK-TEST-KEY"
            )

    # Assert complete and total rollback in the database
    app.refresh_from_db()
    assert app.current_state.code == "DRAFT", "Application state was not rolled back to DRAFT!"
    assert app.revision_number == initial_revision, "Revision number was incremented despite transaction failure!"
    assert ApplicationSubmissionSnapshot.objects.filter(application=app).count() == 0, "Snapshot committed despite rollback!"
    assert ApplicationStatusHistory.objects.filter(application=app).count() == 0, "Status history committed despite rollback!"
    assert AuditLog.objects.filter(entity_id=str(app.id), action=AuditAction.APPLICATION_SUBMITTED).count() == 0, "Audit log committed despite rollback!"
    assert IdempotencyRecord.objects.filter(key="ROLLBACK-TEST-KEY").count() == 0, "Idempotency record committed despite rollback!"


# =============================================================================
# 11. IDEMPOTENCY RECORD EXPIRATION CONTRACT
# =============================================================================
@pytest.mark.django_db
def test_idempotency_record_expiration_and_renewal(stress_env):
    """
    STRESS TEST GATE:
    Verifies behavior after IdempotencyRecord expires:
    1. Retention period: 24 hours.
    2. Replay behavior: while active, returns cached response.
    3. When expired: record is pruned upon lookup, and key reuse is permitted.
    """
    app = stress_env["application"]
    user = stress_env["user"]
    key = "EXPIRABLE-KEY-100"

    # Pre-seed an expired idempotency record (created 48 hours ago, expired 24 hours ago)
    past_time = timezone.now() - timedelta(hours=48)
    expired_time = timezone.now() - timedelta(hours=24)
    record = IdempotencyRecord.objects.create(
        key=key,
        actor=user,
        endpoint=f"/api/v1/applications/{app.id}/submit/",
        request_hash="old_hash",
        response_status=400,
        response_body={"error": "Stale attempt"},
        expires_at=expired_time
    )

    # When request arrives with this expired key, system purges the expired entry
    # and processes the fresh valid submission cleanly
    receipt, code = ApplicationSubmissionService.submit(
        application=app,
        actor_user=user,
        idempotency_key=key
    )

    assert code == 200
    assert receipt["status"] == "SUBMITTED"

    # Check updated record has renewed 24-hour expiration
    new_record = IdempotencyRecord.objects.get(key=key, actor=user)
    assert new_record.response_status == 200
    assert new_record.expires_at > timezone.now()
    assert new_record.expires_at <= timezone.now() + timedelta(hours=25)


# =============================================================================
# 12. APPLICATION REVISION NUMBER MONOTONICITY & FREEZE
# =============================================================================
@pytest.mark.django_db
def test_application_revision_monotonicity_and_freeze(stress_env):
    """
    STRESS TEST GATE:
    1. Every successful mutation increments revision exactly once.
    2. Failed mutations do not increment revision.
    3. Submission freezes the submitted revision.
    """
    app = stress_env["application"]
    user = stress_env["user"]
    client = APIClient()
    client.force_authenticate(user=user)

    assert app.revision_number == 1

    # 1. Failed mutation: invalid field value (income above scheme maximum)
    fail_resp = client.patch(
        f"/api/v1/applications/{app.id}/form/",
        data={
            "expected_revision_number": 1,
            "answers": {"annual_family_income": 99999999}
        },
        format="json"
    )
    assert fail_resp.status_code == status.HTTP_400_BAD_REQUEST
    app.refresh_from_db()
    assert app.revision_number == 1, "Failed mutation must not increment revision number!"

    # 2. Successful mutation: increments revision exactly once (1 -> 2)
    succ_resp = client.patch(
        f"/api/v1/applications/{app.id}/form/",
        data={
            "expected_revision_number": 1,
            "answers": {"annual_family_income": 400000}
        },
        format="json"
    )
    assert succ_resp.status_code == status.HTTP_200_OK
    app.refresh_from_db()
    assert app.revision_number == 2, "Successful mutation must increment revision by 1."

    # 3. Submission freezes revision and records frozen revision in submission snapshot
    receipt, code = ApplicationSubmissionService.submit(
        application=app,
        actor_user=user,
        idempotency_key="SUBMISSION-FREEZE-KEY"
    )
    assert code == 200
    app.refresh_from_db()
    submitted_rev = app.revision_number
    assert submitted_rev == 3  # Incremented to 3 upon submission

    snap = ApplicationSubmissionSnapshot.objects.get(application=app)
    assert snap.revision_number == 2  # Captured form revision before state change

    # 4. Subsequent patch attempts in SUBMITTED state are rejected and revision remains frozen
    post_sub_resp = client.patch(
        f"/api/v1/applications/{app.id}/form/",
        data={
            "expected_revision_number": submitted_rev,
            "answers": {"annual_family_income": 350000}
        },
        format="json"
    )
    assert post_sub_resp.status_code == status.HTTP_400_BAD_REQUEST
    app.refresh_from_db()
    assert app.revision_number == submitted_rev, "Revision number must remain frozen after submission!"
