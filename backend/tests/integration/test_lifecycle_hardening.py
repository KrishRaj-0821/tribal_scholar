import json
import hashlib
import pytest
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.documents.models import (
    SourceDocument, SourceType, SourceDocumentStatus,
    DocumentRequirement, DocumentValidityPolicy, ApplicantDocumentType,
    ApplicantDocument
)
from apps.schemes.models import (
    Scheme, SchemeType, SchemeVersion, SchemeVersionStatus,
    SchemeRule, RuleCategory, RuleOperator, RuleSeverity, RuleStatus, ProvenanceStatus,
    ReferenceSet, ReferenceSetItem, DatasetStatus
)
from apps.workflow.models import WorkflowDefinition, WorkflowState, WorkflowTransition, ApplicationStatusHistory
from apps.applications.models import (
    Application, EligibilityEvaluation, EligibilityInputSnapshot,
    ApplicationFieldDefinition, ApplicationFieldValue, ApplicationDeficiency,
    FieldDataType, FieldValueSource, FieldValueVerificationStatus,
    FieldConflict, ConflictStatus, IdempotencyRecord,
    ApplicationSubmissionSnapshot, ApplicationUniquenessPolicy, DuplicateDetectionMode
)
from apps.schemes.evaluator import RuleEvaluationService
from apps.applications.form_services import FieldTrustResolver, ApplicationFormValidator
from apps.applications.services import (
    FieldConflictService, DuplicateDetectionService, SubmissionService
)
from apps.audit.models import AuditLog, AuditAction


@pytest.fixture
def env(db):
    user_a = User.objects.create_user(
        username="applicant_a",
        email="applicant_a@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    prof_a = ApplicantProfile.objects.create(
        user=user_a,
        community="ST",
        annual_family_income=400000,
        date_of_birth=date(2001, 1, 10)
    )

    user_b = User.objects.create_user(
        username="applicant_b",
        email="applicant_b@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    prof_b = ApplicantProfile.objects.create(
        user=user_b,
        community="ST",
        annual_family_income=500000,
        date_of_birth=date(2002, 2, 20)
    )

    officer = User.objects.create_user(
        username="scrutiny_officer",
        email="officer@tribal.gov.in",
        password="Password123!",
        role=UserRole.SCRUTINY_OFFICER
    )

    scheme = Scheme.objects.create(
        code="TEST_SCHEME",
        name="Lifecycle Hardening Test Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    doc = SourceDocument.objects.create(
        title="Statutory Guidelines 2025-26",
        academic_year="2025-26",
        source_type=SourceType.GUIDELINE,
        checksum="1" * 64,
        content_hash="2" * 64,
        status=SourceDocumentStatus.VERIFIED
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        status=SchemeVersionStatus.ACTIVE,
        source_document=doc
    )

    wf = WorkflowDefinition.objects.create(
        scheme_version=version,
        name="Standard Workflow"
    )
    state_draft = WorkflowState.objects.create(
        workflow=wf,
        code="DRAFT",
        display_name="Draft",
        sequence=1,
        applicant_visible=True
    )
    state_submitted = WorkflowState.objects.create(
        workflow=wf,
        code="SUBMITTED",
        display_name="Submitted",
        sequence=2,
        applicant_visible=True
    )
    t_submit = WorkflowTransition.objects.create(
        workflow=wf,
        from_state=state_draft,
        to_state=state_submitted,
        required_role="APPLICANT"
    )

    # Required field definition
    fdef_income = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Annual Family Income (INR)",
        data_type=FieldDataType.CURRENCY,
        required=True,
        source_document=doc,
        source_excerpt="Income must be declared.",
        status="ACTIVE",
        validation_schema={"min": 0, "max": 600000}
    )

    # Document Requirement (Canonical)
    doc_req = DocumentRequirement.objects.create(
        scheme_version=version,
        document_type=ApplicantDocumentType.CASTE_CERTIFICATE,
        required=True,
        when_required="APPLICATION",
        validity_policy=DocumentValidityPolicy.PERMANENT,
        verification_required=False,
        acceptable_file_types=["application/pdf", "image/jpeg"],
        max_size_mb=5,
        source_document=doc,
        source_excerpt="ST Certificate required."
    )

    # Create applications
    app_a = Application.objects.create(
        application_number="MOTA/2025-26/TEST/0001",
        applicant=prof_a,
        scheme_version=version,
        current_state=state_draft,
        revision_number=1
    )
    app_b = Application.objects.create(
        application_number="MOTA/2025-26/TEST/0002",
        applicant=prof_b,
        scheme_version=version,
        current_state=state_draft,
        revision_number=1
    )

    # Upload required document for app_a
    ApplicantDocument.objects.create(
        applicant=user_a,
        document_type=ApplicantDocumentType.CASTE_CERTIFICATE,
        file_name="caste_certificate.pdf",
        checksum="c" * 64
    )

    # Populate valid field value for app_a
    ApplicationFieldValue.objects.create(
        application=app_a,
        field_definition=fdef_income,
        value_json=400000,
        source=FieldValueSource.APPLICANT,
        verification_status=FieldValueVerificationStatus.UNVERIFIED
    )

    return {
        "user_a": user_a,
        "prof_a": prof_a,
        "app_a": app_a,
        "user_b": user_b,
        "prof_b": prof_b,
        "app_b": app_b,
        "officer": officer,
        "scheme": scheme,
        "version": version,
        "doc": doc,
        "fdef_income": fdef_income,
        "doc_req": doc_req,
        "state_draft": state_draft,
        "state_submitted": state_submitted,
    }


# =============================================================================
# PART 19 — API SECURITY TESTS
# =============================================================================

@pytest.mark.django_db
def test_1_applicant_cannot_submit_another_users_application(env):
    client = APIClient()
    client.force_authenticate(user=env["user_b"])
    res = client.post(
        f"/api/v1/applications/{env['app_a'].id}/submit/",
        {"idempotency_key": "KEY-SUBMIT-ATTEMPT-01"},
        format="json",
        HTTP_IDEMPOTENCY_KEY="KEY-SUBMIT-ATTEMPT-01"
    )
    assert res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
def test_2_applicant_cannot_modify_submitted_application_unless_workflow_permits(env):
    app = env["app_a"]
    app.current_state = env["state_submitted"]
    app.save()

    client = APIClient()
    client.force_authenticate(user=env["user_a"])
    res = client.patch(
        f"/api/v1/applications/{app.id}/form/",
        {"answers": {"annual_family_income": 350000}},
        format="json"
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST
    assert res.data.get("error") == "LOCKED"


@pytest.mark.django_db
def test_3_applicant_cannot_read_another_applicants_snapshot(env):
    # Create submission snapshot for app_a
    snapshot = ApplicationSubmissionSnapshot.objects.create(
        application=env["app_a"],
        revision_number=1,
        applicant_data_json={"name": "Applicant A"},
        form_values_json={},
        document_manifest_json=[],
        scheme_version=env["version"],
        snapshot_hash="s" * 64
    )

    client = APIClient()
    client.force_authenticate(user=env["user_b"])
    res = client.get(f"/api/v1/applications/{env['app_a'].id}/submission-snapshot/")
    assert res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
def test_4_officer_cannot_modify_scheme_rules(env):
    rule = SchemeRule.objects.create(
        scheme_version=env["version"],
        rule_code="TEST_RULE_IMMUTABLE",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.community",
        operator=RuleOperator.EQUALS,
        value="ST",
        source_document=env["doc"],
        status=RuleStatus.ACTIVE
    )
    client = APIClient()
    client.force_authenticate(user=env["officer"])
    res = client.patch(f"/api/v1/schemes/rules/{rule.id}/", {"value": "SC"}, format="json")
    assert res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_405_METHOD_NOT_ALLOWED)


@pytest.mark.django_db
def test_5_duplicate_submission_with_same_idempotency_key_produces_one_result(env):
    client = APIClient()
    client.force_authenticate(user=env["user_a"])
    headers = {"HTTP_IDEMPOTENCY_KEY": "IDEMP-KEY-TEST-001"}

    # First Submission
    res1 = client.post(
        f"/api/v1/applications/{env['app_a'].id}/submit/",
        {},
        format="json",
        **headers
    )
    assert res1.status_code == status.HTTP_200_OK
    assert res1.data["status"] == "SUBMITTED"

    # Second Submission with exact same idempotency key
    res2 = client.post(
        f"/api/v1/applications/{env['app_a'].id}/submit/",
        {},
        format="json",
        **headers
    )
    assert res2.status_code == status.HTTP_200_OK
    assert res2.data["receipt_number"] == res1.data["receipt_number"]

    # Verify that only ONE ApplicationSubmissionSnapshot and ONE status transition occurred
    assert ApplicationSubmissionSnapshot.objects.filter(application=env["app_a"]).count() == 1
    assert ApplicationStatusHistory.objects.filter(application=env["app_a"]).count() == 1
    assert AuditLog.objects.filter(entity_id=str(env["app_a"].id), action=AuditAction.APPLICATION_SUBMITTED).count() == 1


@pytest.mark.django_db
def test_6_different_idempotency_key_fails_when_workflow_forbids_resubmission(env):
    client = APIClient()
    client.force_authenticate(user=env["user_a"])

    # First submission
    res1 = client.post(
        f"/api/v1/applications/{env['app_a'].id}/submit/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="KEY-AAA"
    )
    assert res1.status_code == status.HTTP_200_OK

    # Second submission with a different key on the already SUBMITTED application
    res2 = client.post(
        f"/api/v1/applications/{env['app_a'].id}/submit/",
        {},
        format="json",
        HTTP_IDEMPOTENCY_KEY="KEY-BBB"
    )
    assert res2.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_7_concurrent_edits_produce_409_conflict(env):
    app = env["app_a"]
    client = APIClient()
    client.force_authenticate(user=env["user_a"])

    # Successful patch with current revision (1)
    res1 = client.patch(
        f"/api/v1/applications/{app.id}/form/",
        {"answers": {"annual_family_income": 420000}, "expected_revision_number": 1},
        format="json"
    )
    assert res1.status_code == status.HTTP_200_OK
    assert res1.data["revision_number"] == 2

    # Concurrent patch from stale client presenting old revision (1)
    res2 = client.patch(
        f"/api/v1/applications/{app.id}/form/",
        {"answers": {"annual_family_income": 450000}, "expected_revision_number": 1},
        format="json"
    )
    assert res2.status_code == status.HTTP_409_CONFLICT
    assert res2.data["error"] == "CONFLICT"
    assert res2.data["current_revision"] == 2


@pytest.mark.django_db
def test_8_concurrent_submission_cannot_create_duplicate_status_events(env):
    # Verify that calling SubmissionService on an already submitted application raises ValidationError
    SubmissionService.submit(
        application=env["app_a"],
        actor_user=env["user_a"],
        idempotency_key="SUB-KEY-100"
    )
    env["app_a"].refresh_from_db()
    assert env["app_a"].current_state.code == "SUBMITTED"

    with pytest.raises(ValidationError):
        SubmissionService.submit(
            application=env["app_a"],
            actor_user=env["user_a"],
            idempotency_key="SUB-KEY-200"
        )


@pytest.mark.django_db
def test_9_historical_snapshots_cannot_be_updated(env):
    snapshot = ApplicationSubmissionSnapshot.objects.create(
        application=env["app_a"],
        revision_number=1,
        applicant_data_json={"name": "A"},
        form_values_json={},
        document_manifest_json=[],
        scheme_version=env["version"],
        snapshot_hash="x" * 64
    )
    with pytest.raises(ValidationError):
        snapshot.snapshot_hash = "y" * 64
        snapshot.save()

    with pytest.raises(ValidationError):
        snapshot.delete()


@pytest.mark.django_db
def test_10_sensitive_snapshot_access_generates_audit_event(env):
    snapshot = ApplicationSubmissionSnapshot.objects.create(
        application=env["app_a"],
        revision_number=1,
        applicant_data_json={"name": "A"},
        form_values_json={},
        document_manifest_json=[],
        scheme_version=env["version"],
        snapshot_hash="s" * 64
    )
    client = APIClient()
    client.force_authenticate(user=env["user_a"])
    res = client.get(f"/api/v1/applications/{env['app_a'].id}/submission-snapshot/")
    assert res.status_code == status.HTTP_200_OK

    audit = AuditLog.objects.filter(
        entity_id=str(snapshot.id),
        action=AuditAction.SNAPSHOT_VIEWED
    ).first()
    assert audit is not None
    assert audit.actor == env["user_a"]


@pytest.mark.django_db
def test_11_duplicate_detection_produces_review_state_not_automatic_rejection(env):
    # Set policy to WARN
    ApplicationUniquenessPolicy.objects.update_or_create(
        scheme_version=env["version"],
        defaults={"duplicate_detection_mode": DuplicateDetectionMode.WARN, "max_active_applications": 1}
    )
    # Create another application for user_a
    dup_app = Application.objects.create(
        application_number="MOTA/2025-26/TEST/DUP",
        applicant=env["prof_a"],
        scheme_version=env["version"],
        current_state=env["state_draft"]
    )
    res = DuplicateDetectionService.check_duplicates(dup_app)
    assert res["is_duplicate"] is True
    assert res["flag"] == "POSSIBLE_DUPLICATE"


@pytest.mark.django_db
def test_12_ocr_provisional_cannot_outrank_applicant_declared(env):
    app = env["app_a"]
    fdef = env["fdef_income"]

    # Applicant declared 300,000 (rank 20)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=300000,
        source=FieldValueSource.APPLICANT,
        verification_status=FieldValueVerificationStatus.UNVERIFIED
    )
    # OCR provisional 500,000 (rank 10)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=500000,
        source=FieldValueSource.OCR,
        verification_status=FieldValueVerificationStatus.PROVISIONALLY_EXTRACTED
    )

    effective = FieldTrustResolver.get_effective_values(app)
    assert effective["annual_family_income"]["value"] == 300000
    assert effective["annual_family_income"]["source"] == FieldValueSource.APPLICANT


@pytest.mark.django_db
def test_13_document_verified_can_outrank_applicant_declaration(env):
    app = env["app_a"]
    fdef = env["fdef_income"]

    # Applicant declared 300,000 (rank 20)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=300000,
        source=FieldValueSource.APPLICANT
    )
    # Verified document extraction 350,000 (rank 30)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=350000,
        source=FieldValueSource.VERIFIED_DOCUMENT,
        verification_status=FieldValueVerificationStatus.DOCUMENT_VERIFIED
    )

    effective = FieldTrustResolver.get_effective_values(app)
    assert effective["annual_family_income"]["value"] == 350000
    assert effective["annual_family_income"]["source"] == FieldValueSource.VERIFIED_DOCUMENT


@pytest.mark.django_db
def test_14_officer_verified_outranks_all_lower_trust_values(env):
    app = env["app_a"]
    fdef = env["fdef_income"]

    # Add APPLICANT, OCR, VERIFIED_DOCUMENT, OFFICIAL_INTEGRATION
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=100000, source=FieldValueSource.OCR)
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=200000, source=FieldValueSource.APPLICANT)
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=300000, source=FieldValueSource.VERIFIED_DOCUMENT)
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=400000, source=FieldValueSource.OFFICIAL_INTEGRATION)

    # Officer Verified (rank 50)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=450000,
        source=FieldValueSource.OFFICER,
        verification_status=FieldValueVerificationStatus.OFFICER_VERIFIED
    )

    effective = FieldTrustResolver.get_effective_values(app)
    assert effective["annual_family_income"]["value"] == 450000
    assert effective["annual_family_income"]["source"] == FieldValueSource.OFFICER


@pytest.mark.django_db
def test_15_material_unresolved_field_conflict_produces_needs_review(env):
    app = env["app_a"]
    fdef = env["fdef_income"]

    # Applicant declares 400,000
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=400000, source=FieldValueSource.APPLICANT)
    # OCR extracts 540,000
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=540000, source=FieldValueSource.OCR)

    # Detect conflict
    conflicts = FieldConflictService.detect_conflicts(app)
    assert len(conflicts) >= 1
    assert conflicts[0].status == ConflictStatus.OPEN

    # Add eligibility rule on income
    SchemeRule.objects.create(
        scheme_version=env["version"],
        rule_code="TEST_INCOME_LIMIT",
        category=RuleCategory.ELIGIBILITY,
        field_path="annual_family_income",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=600000,
        source_document=env["doc"],
        status=RuleStatus.ACTIVE
    )

    # Evaluation on this application must yield NEEDS_REVIEW due to open conflict
    res = RuleEvaluationService.evaluate(application=app)
    assert res["status"] == "NEEDS_REVIEW"
    assert any("Material unresolved field conflict" in r.get("explanation", "") for r in res["unresolved_rules"])


# =============================================================================
# PART 20 — PROPERTY / INVARIANT TESTS
# =============================================================================

@pytest.mark.django_db
def test_16_application_cannot_move_backward_unless_explicitly_configured(env):
    app = env["app_a"]
    app.current_state = env["state_submitted"]
    app.save()

    # Attempting to submit again from SUBMITTED state must fail
    with pytest.raises(ValidationError):
        SubmissionService.submit(application=app, actor_user=env["user_a"], idempotency_key="TEST-BACKWARD-01")


@pytest.mark.django_db
def test_17_immutable_snapshots_cannot_be_changed(env):
    snapshot = ApplicationSubmissionSnapshot.objects.create(
        application=env["app_a"],
        revision_number=1,
        applicant_data_json={"name": "A"},
        form_values_json={},
        document_manifest_json=[],
        scheme_version=env["version"],
        snapshot_hash="hash_orig"
    )
    with pytest.raises(ValidationError):
        snapshot.revision_number = 2
        snapshot.save()


@pytest.mark.django_db
def test_18_submitted_revision_cannot_silently_change(env):
    app = env["app_a"]
    initial_rev = app.revision_number
    receipt, _ = SubmissionService.submit(
        application=app,
        actor_user=env["user_a"],
        idempotency_key="REV-TEST-KEY"
    )
    app.refresh_from_db()
    assert app.revision_number == initial_rev + 1
    assert receipt["revision_number"] == initial_rev + 1


@pytest.mark.django_db
def test_19_result_hashes_remain_stable(env):
    dossier = {
        "applicant": {"community": "ST"},
        "annual_family_income": 400000,
        "documents": {"caste_certificate": True}
    }
    res1 = RuleEvaluationService.evaluate("APP-STABLE", env["version"], dossier)
    res2 = RuleEvaluationService.evaluate("APP-STABLE", env["version"], dossier)
    assert res1["result_hash"] == res2["result_hash"]


@pytest.mark.django_db
def test_20_audit_history_remains_append_only(env):
    log = AuditLog.objects.create(
        actor=env["user_a"],
        actor_role="APPLICANT",
        entity_type="Application",
        entity_id=str(env["app_a"].id),
        action=AuditAction.APPLICATION_CREATED,
        reason="Initial test creation"
    )
    with pytest.raises(ValidationError):
        log.reason = "Tampered reason"
        log.save()

    with pytest.raises(ValidationError):
        log.delete()


@pytest.mark.django_db
def test_21_one_idempotency_key_maps_to_one_response(env):
    record = IdempotencyRecord.objects.create(
        key="UNIQUE-KEY-001",
        actor=env["user_a"],
        endpoint="/api/v1/applications/submit/",
        request_hash="h1",
        response_status=200,
        response_body={"status": "SUBMITTED"}
    )
    # Unique constraint must prevent duplicate creation with same actor/key/endpoint
    with pytest.raises(Exception):
        IdempotencyRecord.objects.create(
            key="UNIQUE-KEY-001",
            actor=env["user_a"],
            endpoint="/api/v1/applications/submit/",
            request_hash="h2",
            response_status=400,
            response_body={"status": "FAILED"}
        )


@pytest.mark.django_db
def test_22_one_document_checksum_identifies_the_same_binary_file(env):
    doc_hash = hashlib.sha256(b"SAMPLE_OFFICIAL_PDF_BYTES").hexdigest()
    doc1 = ApplicantDocument.objects.create(
        applicant=env["user_a"],
        document_type=ApplicantDocumentType.CASTE_CERTIFICATE,
        file_name="cert1.pdf",
        checksum=doc_hash
    )
    doc2 = ApplicantDocument.objects.create(
        applicant=env["user_b"],
        document_type=ApplicantDocumentType.CASTE_CERTIFICATE,
        file_name="cert2.pdf",
        checksum=doc_hash
    )
    assert doc1.checksum == doc2.checksum


@pytest.mark.django_db
def test_23_scheme_version_is_immutable_once_published(env):
    published_ver = env["version"]
    published_ver.status = SchemeVersionStatus.ACTIVE
    published_ver.save()

    # Changing academic year of published version must be prohibited
    with pytest.raises(ValidationError):
        published_ver.academic_year = "2029-30"
        published_ver.save()


@pytest.mark.django_db
def test_24_document_requirements_canonical_and_duplicates_superseded(env):
    # A DOCUMENT SchemeRule that duplicates DocumentRequirement is marked SUPERSEDED
    dup_rule = SchemeRule.objects.create(
        scheme_version=env["version"],
        rule_code="DUP_DOC_CASTE_RULE",
        category=RuleCategory.DOCUMENT,
        field_path="documents.caste_certificate",
        operator=RuleOperator.EXISTS,
        value=True,
        source_document=env["doc"],
        status=RuleStatus.ACTIVE
    )
    res = RuleEvaluationService.evaluate(
        application=env["app_a"],
        scheme_version=env["version"],
        applicant_data={"documents": {"caste_certificate": True}}
    )
    dup_rule.refresh_from_db()
    assert dup_rule.status == RuleStatus.SUPERSEDED
    assert "DocumentRequirement" in dup_rule.superseded_reason


@pytest.mark.django_db
def test_25_seed_determinism_repeated_execution(db):
    """
    Seed Determinism Gate:
    Running seed_schemes multiple times must produce identical object counts,
    identical rule hashes, reference-set hashes, document requirement hashes,
    form definition hashes, and keep the Top Class income rule unchanged at 600,000.
    """
    import hashlib, json

    def compute_seed_state():
        def hash_qs(items):
            serialized = json.dumps(list(items), sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

        rules = SchemeRule.objects.order_by('rule_code').values('rule_code', 'category', 'field_path', 'operator', 'value', 'source_excerpt', 'status')
        ref_sets = ReferenceSetItem.objects.order_by('reference_set__code', 'external_code').values('reference_set__code', 'external_code', 'name')
        doc_reqs = DocumentRequirement.objects.order_by('scheme_version__scheme__code', 'scheme_version__academic_year', 'document_type').values('scheme_version__scheme__code', 'scheme_version__academic_year', 'document_type', 'required', 'validity_policy')
        form_defs = ApplicationFieldDefinition.objects.order_by('scheme_version__scheme__code', 'scheme_version__academic_year', 'field_code').values('scheme_version__scheme__code', 'scheme_version__academic_year', 'field_code', 'data_type', 'required', 'validation_schema')
        top_rule = SchemeRule.objects.filter(rule_code='TOP_CLASS_2025_INCOME_CEILING').first()

        return {
            "counts": (
                SchemeVersion.objects.count(),
                SchemeRule.objects.count(),
                ReferenceSet.objects.count(),
                ReferenceSetItem.objects.count(),
                DocumentRequirement.objects.count(),
                ApplicationFieldDefinition.objects.count(),
            ),
            "rule_hash": hash_qs(rules),
            "ref_set_hash": hash_qs(ref_sets),
            "doc_req_hash": hash_qs(doc_reqs),
            "form_def_hash": hash_qs(form_defs),
            "top_income_val": top_rule.value if top_rule else None,
            "top_income_excerpt": top_rule.source_excerpt if top_rule else None,
        }

    call_command("seed_schemes")
    state1 = compute_seed_state()

    call_command("seed_schemes")
    state2 = compute_seed_state()

    assert state1["counts"] == state2["counts"], "Object counts changed across seed_schemes executions!"
    assert state1["rule_hash"] == state2["rule_hash"], "Rule hashes changed across seed_schemes executions!"
    assert state1["ref_set_hash"] == state2["ref_set_hash"], "Reference-set hashes changed across seed_schemes executions!"
    assert state1["doc_req_hash"] == state2["doc_req_hash"], "Document requirement hashes changed across seed_schemes executions!"
    assert state1["form_def_hash"] == state2["form_def_hash"], "Form definition hashes changed across seed_schemes executions!"
    assert state1["top_income_val"] == 600000, "Top Class income ceiling must be 600000 (6.00 lakh)."
    assert state2["top_income_val"] == 600000, "Top Class income ceiling altered after second seed run!"
    assert "6.00 lakh" in state1["top_income_excerpt"]
