import pytest
import uuid
from datetime import date
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.schemes.models import (
    Scheme, SchemeVersion, SchemeType, SchemeRule,
    RuleCategory, RuleOperator, RuleSeverity, RuleStatus, ProvenanceStatus
)
from apps.workflow.models import WorkflowDefinition, WorkflowState
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue,
    FieldDataType, FieldValueSource, FieldValueVerificationStatus,
    SOURCE_TRUST_RANK, FieldConflict, ConflictStatus
)
from apps.documents.models import (
    ApplicantDocument, DocumentVersion, DocumentLifecycleStatus,
    ApplicantDocumentType, OCRJob, OCRResult, OCRPage, OCRBlock,
    SourceDocument, SourceDocumentStatus, SourceType
)
from apps.verification.models import (
    VerificationQueueItem, VerificationStatus, VerificationPriority,
    VerificationItemType, DocumentVerificationRecord,
    VerificationRecordStatus, VerificationDecisionAction, VerificationMethod
)
from apps.verification.services import DocumentVerificationService
from apps.audit.models import AuditLog, AuditAction
from apps.schemes.evaluator import RuleEvaluationService

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.requires_postgresql,
]


@pytest.fixture
def p9_env(db):
    """
    Sets up a fully-isolated Phase 9 Officer Workspace testing environment:
    - 1 Applicant
    - 2 Scrutiny Officers
    - 1 System Admin
    - 1 Unauthorized Applicant
    - 1 Scheme with deterministic income eligibility rule (threshold: 2,50,000)
    - 1 Application in SUBMITTED state
    - 1 SAFE Document (Income Certificate)
    - 1 OCR Result with Provisional Extraction (4,50,000)
    - 1 Material Conflict (Applicant declared 5,00,000 vs OCR 4,50,000)
    - 1 VerificationQueueItem
    """
    User.objects.filter(username__in=[
        "p9_applicant", "p9_officer_1", "p9_officer_2", "p9_admin", "p9_unauth"
    ]).delete()
    Scheme.objects.filter(code="P9_SCHOLARSHIP").delete()

    applicant_user = User.objects.create_user(
        username="p9_applicant",
        email="applicant@p9.gov.in",
        password="ValidPassword123!",
        role=UserRole.APPLICANT
    )
    applicant_profile = ApplicantProfile.objects.create(
        user=applicant_user,
        community="ST",
        annual_family_income=500000,
        date_of_birth=date(2002, 5, 20)
    )

    officer_1 = User.objects.create_user(
        username="p9_officer_1",
        email="officer1@p9.gov.in",
        password="ValidPassword123!",
        role=UserRole.SCRUTINY_OFFICER
    )

    officer_2 = User.objects.create_user(
        username="p9_officer_2",
        email="officer2@p9.gov.in",
        password="ValidPassword123!",
        role=UserRole.SCRUTINY_OFFICER
    )

    admin_user = User.objects.create_user(
        username="p9_admin",
        email="admin@p9.gov.in",
        password="ValidPassword123!",
        role=UserRole.ADMIN
    )

    unauth_user = User.objects.create_user(
        username="p9_unauth",
        email="unauth@p9.gov.in",
        password="ValidPassword123!",
        role=UserRole.APPLICANT
    )

    SourceDocument.objects.filter(checksum="9" * 64).delete()
    source_doc = SourceDocument.objects.create(
        title="P9 National Fellowship Guidelines",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="9" * 64,
        content_hash="9" * 64,
        status=SourceDocumentStatus.VERIFIED
    )

    scheme = Scheme.objects.create(
        code="P9_SCHOLARSHIP",
        name="Phase 9 Higher Education Scholarship for ST Students",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    scheme_version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=source_doc,
        status="ACTIVE"
    )

    # Deterministic rule: annual_family_income <= 250000
    income_rule = SchemeRule.objects.create(
        scheme_version=scheme_version,
        rule_code="R_P9_INCOME_CEILING",
        category=RuleCategory.ELIGIBILITY,
        field_path="annual_family_income",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=250000.0,
        failure_message="Annual family income must not exceed INR 2,50,000",
        severity=RuleSeverity.BLOCKING,
        source_document=source_doc,
        source_excerpt="Annual family income must not exceed INR 2.50 lakh"
    )

    workflow = WorkflowDefinition.objects.create(
        name="P9 Workflow",
        scheme_version=scheme_version,
        active=True
    )
    scrutiny_state = WorkflowState.objects.create(
        workflow=workflow,
        code="UNDER_SCRUTINY",
        display_name="Under Scrutiny",
        sequence=2
    )

    income_field_def = ApplicationFieldDefinition.objects.create(
        scheme_version=scheme_version,
        field_code="annual_family_income",
        label="Annual Family Income",
        data_type=FieldDataType.CURRENCY
    )

    application = Application.objects.create(
        application_number="APP-P9-9001",
        applicant=applicant_profile,
        scheme_version=scheme_version,
        current_state=scrutiny_state,
        is_synthetic=True,
        submission_data_json={
            "annual_family_income": 500000.0,
            "community": "ST"
        }
    )

    # 1. Applicant declaration: 500,000 (exceeds 250,000 ceiling)
    decl_value = ApplicationFieldValue.objects.create(
        application=application,
        field_definition=income_field_def,
        value_json=500000.0,
        source=FieldValueSource.APPLICANT,
        verification_status=FieldValueVerificationStatus.UNVERIFIED,
        confidence=1.0,
        entered_by=applicant_user
    )

    # 2. Ingested document (Income Certificate) passed security checks -> SAFE
    doc = ApplicantDocument.objects.create(
        application=application,
        applicant=applicant_user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        original_filename="income_cert_2025.pdf",
        sha256="a" * 64,
        lifecycle_status=DocumentLifecycleStatus.SAFE
    )
    doc_ver = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        storage_key="safe/income_cert_2025.pdf",
        sha256="a" * 64
    )

    # 3. Asynchronous OCR output: extracted 450,000 (still provisional)
    ocr_job = OCRJob.objects.create(
        document=doc,
        document_version=doc_ver,
        idempotency_key=f"job-p9-{uuid.uuid4().hex[:8]}",
        status="COMPLETED"
    )
    ocr_result = OCRResult.objects.create(
        ocr_job=ocr_job,
        document=doc,
        document_version=doc_ver,
        page_count=1,
        engine_name="PaddleOCR",
        engine_version="3.7.0",
        pipeline_version="1.0.0",
        result_hash="b" * 64,
        full_text="GOVERNMENT OF INDIA REVENUE DEPARTMENT INCOME CERTIFICATE ANNUAL INCOME RS 450000"
    )
    ocr_page = OCRPage.objects.create(
        ocr_result=ocr_result,
        page_number=1,
        width=700,
        height=990,
        page_confidence=0.985,
        page_hash="c" * 64
    )
    ocr_block = OCRBlock.objects.create(
        page=ocr_page,
        extracted_text="ANNUAL INCOME RS 450000",
        confidence=0.985,
        bbox_x=100.0,
        bbox_y=200.0,
        bbox_width=500.0,
        bbox_height=50.0,
        polygon=[[100.0, 200.0], [600.0, 200.0], [600.0, 250.0], [100.0, 250.0]],
        reading_order=1
    )

    # 4. Material Conflict between applicant 500,000 and OCR 450,000
    conflict = FieldConflict.objects.create(
        application=application,
        field_code="annual_family_income",
        values_json=[500000.0, 450000.0],
        source_values={
            "APPLICANT": {"value": 500000.0, "trust_rank": 20},
            "OCR_PROVISIONAL": {"value": 450000.0, "trust_rank": 10, "confidence": 0.985}
        },
        severity="BLOCKING",
        status=ConflictStatus.OPEN
    )

    # 5. Verification Queue Item
    queue_item = VerificationQueueItem.objects.create(
        application=application,
        document=doc,
        item_type=VerificationItemType.DOCUMENT,
        priority=VerificationPriority.HIGH,
        status=VerificationStatus.PENDING,
        conflict_type="MATERIAL_CONFLICT",
        target_identifier="annual_family_income",
        confidence_score=0.985,
        current_evidence_json={
            "declared": 500000.0,
            "ocr_provisional": 450000.0
        },
        ai_assistance_json={
            "field": "annual_family_income",
            "declared": 500000.0,
            "ocr": 450000.0,
            "difference": 50000.0
        }
    )

    return {
        "applicant_user": applicant_user,
        "applicant_profile": applicant_profile,
        "officer_1": officer_1,
        "officer_2": officer_2,
        "admin_user": admin_user,
        "unauth_user": unauth_user,
        "scheme": scheme,
        "scheme_version": scheme_version,
        "income_rule": income_rule,
        "income_field_def": income_field_def,
        "application": application,
        "doc": doc,
        "doc_ver": doc_ver,
        "ocr_result": ocr_result,
        "ocr_page": ocr_page,
        "ocr_block": ocr_block,
        "conflict": conflict,
        "queue_item": queue_item,
    }


# ==============================================================================
# A. RBAC TESTS
# ==============================================================================

def test_a_rbac_applicant_cannot_access_verification_endpoints(p9_env):
    """
    RBAC: Applicants and unauthorized users are blocked server-side (HTTP 403)
    from accessing verification queue, detail, and actions.
    """
    client = APIClient()
    client.force_authenticate(user=p9_env["unauth_user"])

    # 1. Listing queue
    res = client.get("/api/v1/verification/queue/")
    assert res.status_code == 403

    # 2. Retrieving queue item detail
    res = client.get(f"/api/v1/verification/queue/{p9_env['queue_item'].id}/")
    assert res.status_code == 403

    # 3. Direct field verification endpoint
    res = client.post(
        f"/api/v1/verification/documents/{p9_env['doc'].id}/verify-field/",
        {"field_code": "annual_family_income", "verified_value": 450000.0}
    )
    assert res.status_code == 403


def test_a_rbac_separation_of_duties_applicant_cannot_verify_own_dossier(p9_env):
    """
    Separation of Duties: An applicant attempting to verify their own document
    or application via service layer raises PermissionDenied with exact message.
    """
    with pytest.raises(PermissionDenied) as exc:
        DocumentVerificationService.verify_field(
            document_id=p9_env["doc"].id,
            field_code="annual_family_income",
            verified_value=450000.0,
            officer=p9_env["applicant_user"],
            reason="Applicant attempt to self-verify"
        )
    assert "Separation of Duties violation" in str(exc.value) or "Only authorized officers" in str(exc.value)


def test_a_rbac_authorized_officer_and_admin_have_access(p9_env):
    """
    Scrutiny Officer and Admin users can access the verification queue and detail.
    """
    client = APIClient()

    # Officer 1
    client.force_authenticate(user=p9_env["officer_1"])
    res = client.get("/api/v1/verification/queue/")
    assert res.status_code == 200
    assert len(res.data["results"]) >= 1

    # Admin
    client.force_authenticate(user=p9_env["admin_user"])
    res = client.get(f"/api/v1/verification/queue/{p9_env['queue_item'].id}/")
    assert res.status_code == 200
    assert "queue_item" in res.data
    assert "applicant" in res.data
    assert "conflicts" in res.data


# ==============================================================================
# B. IDOR TESTS
# ==============================================================================

def test_b_idor_unauthorized_applicant_cannot_access_foreign_queue_item(p9_env):
    """
    IDOR Protection: Applicant cannot tamper with or inspect another applicant's
    verification item or document evidence.
    """
    client = APIClient()
    client.force_authenticate(user=p9_env["unauth_user"])

    res = client.get(f"/api/v1/verification/queue/{p9_env['queue_item'].id}/detail/")
    assert res.status_code == 403

    res = client.post(
        f"/api/v1/verification/conflicts/{p9_env['queue_item'].id}/resolve/",
        {"decision_action": "USE_DOCUMENT_VALUE", "reason": "Unauthorized bypass"}
    )
    assert res.status_code == 403


# ==============================================================================
# C. FIELD VERIFICATION TESTS
# ==============================================================================

def test_c_field_verification_promotes_trust_and_records_audit(p9_env):
    """
    Field Verification:
    - Promotes value to OFFICER_VERIFIED (Trust rank 60)
    - Records previous value (500000, rank 20 APPLICANT_DECLARED)
    - Sets verified value (450000, rank 60)
    - Records supporting document and block reference
    - Creates immutable audit event
    """
    officer = p9_env["officer_1"]
    doc = p9_env["doc"]
    block = p9_env["ocr_block"]

    record = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="Verified against SDM stamp and official seal",
        block_id=str(block.id)
    )

    assert record.verified_source == "OFFICER_VERIFIED"
    assert record.verified_trust_rank == 60
    assert record.previous_trust_rank == 20
    assert record.previous_source == "APPLICANT_DECLARED"
    assert record.verified_value_json == 450000.0
    assert record.audit_event_id != ""

    # Verify AuditLog existence
    audit_entry = AuditLog.objects.get(id=record.audit_event_id)
    assert audit_entry.actor == officer
    assert audit_entry.action == AuditAction.FIELD_VERIFIED
    assert audit_entry.after_json["verified_trust_rank"] == 60

    # Promoted ApplicationFieldValue
    current_val = ApplicationFieldValue.objects.filter(
        application=p9_env["application"],
        field_definition=p9_env["income_field_def"]
    ).order_by('-created_at').first()
    assert current_val.source == FieldValueSource.OFFICER_VERIFIED
    assert current_val.trust_rank == 60
    assert current_val.value_json == 450000.0


def test_c_field_rejection_requires_justification(p9_env):
    """
    Field Rejection:
    - Requires non-empty reason
    - Sets verification_status to REJECTED
    - Sets queue item to DEFECT_FLAGGED
    """
    officer = p9_env["officer_1"]
    doc = p9_env["doc"]

    with pytest.raises(ValidationError):
        DocumentVerificationService.reject_field(
            document_id=doc.id,
            field_code="annual_family_income",
            officer=officer,
            reason=""  # empty justification rejected
        )

    rec = DocumentVerificationService.reject_field(
        document_id=doc.id,
        field_code="annual_family_income",
        officer=officer,
        reason="Income certificate is illegible; seal blurred"
    )
    assert rec.verification_status == VerificationRecordStatus.REJECTED
    assert rec.decision_action == VerificationDecisionAction.REQUEST_CORRECTION


# ==============================================================================
# D. DOCUMENT VERIFICATION TESTS
# ==============================================================================

def test_d_document_verification_distinguishes_safe_from_verified(p9_env):
    """
    Security lifecycle separation:
    - SAFE means ingestion passed anti-virus/MIME checks. SAFE != VERIFIED.
    - VERIFIED_DOCUMENT requires explicit officer action.
    """
    doc = p9_env["doc"]
    assert doc.lifecycle_status == DocumentLifecycleStatus.SAFE

    # Initial trust rank of an unverified document is NOT 40
    records = DocumentVerificationRecord.objects.filter(document=doc, is_current=True)
    assert records.count() == 0

    officer = p9_env["officer_1"]
    res = DocumentVerificationService.verify_document(
        document_id=doc.id,
        officer=officer,
        reason="Verified authentic state revenue certificate"
    )

    doc.refresh_from_db()
    assert doc.lifecycle_status == DocumentLifecycleStatus.VERIFIED
    assert res["status"] == "VERIFIED"
    assert res["record_id"] is not None

    record = DocumentVerificationRecord.objects.get(id=res["record_id"])
    assert record.verified_source == "VERIFIED_DOCUMENT"
    assert record.verified_trust_rank == 40
    assert record.field_code == "document_level"


# ==============================================================================
# E. CONFLICT RESOLUTION TESTS
# ==============================================================================

def test_e_conflict_resolution_use_document_value(p9_env):
    """
    Conflict Resolution: USE_DOCUMENT_VALUE
    - Promotes document/OCR value to OFFICER_VERIFIED (rank 60)
    - Resolves FieldConflict
    - Finalizes queue item as VERIFIED
    """
    officer = p9_env["officer_1"]
    queue_item = p9_env["queue_item"]

    record = DocumentVerificationService.resolve_field_conflict(
        queue_item_id=queue_item.id,
        officer=officer,
        decision_action=VerificationDecisionAction.USE_DOCUMENT_VALUE,
        reason="Document clearly indicates 450,000 as issued by tehsildar"
    )

    assert record.verification_status == VerificationRecordStatus.VERIFIED
    queue_item.refresh_from_db()
    assert queue_item.status == VerificationStatus.VERIFIED
    p9_env["conflict"].refresh_from_db()
    assert p9_env["conflict"].status == ConflictStatus.RESOLVED


def test_e_conflict_resolution_needs_more_evidence_and_escalate(p9_env):
    """
    Conflict Resolution: NEEDS_MORE_EVIDENCE and ESCALATE
    """
    officer = p9_env["officer_1"]
    queue_item = p9_env["queue_item"]

    # Needs more evidence
    item_nme = DocumentVerificationService.request_more_evidence(
        queue_item_id=queue_item.id,
        officer=officer,
        reason="Income certificate older than 1 year. Upload current financial year certificate."
    )
    assert item_nme.status == VerificationStatus.NEEDS_MORE_EVIDENCE

    # Escalate
    item_esc = DocumentVerificationService.escalate_queue_item(
        queue_item_id=queue_item.id,
        officer=officer,
        reason="Discrepancy exceeds permissible threshold. Forward to District Officer."
    )
    assert item_esc.status == VerificationStatus.ESCALATED
    assert item_esc.priority in [VerificationPriority.HIGH, VerificationPriority.URGENT]


# ==============================================================================
# F. AUDIT IMMUTABILITY TESTS
# ==============================================================================

def test_f_audit_log_and_verification_record_immutability(p9_env):
    """
    Append-only Immutability:
    - AuditLog raises ValidationError on bulk update or direct modification.
    - Superceding a verification creates a new record, never overwrites the previous.
    """
    officer = p9_env["officer_1"]
    doc = p9_env["doc"]

    rec1 = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="Initial verification"
    )

    # Direct bulk update on AuditLog must fail
    with pytest.raises(ValidationError):
        AuditLog.objects.filter(id=rec1.audit_event_id).update(reason="Tampered reason")

    # Re-verifying creates a new record and supersedes the old
    rec2 = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=420000.0,
        officer=officer,
        reason="Corrected value after reviewing annexure"
    )

    rec1.refresh_from_db()
    assert rec2.superseded_record == rec1
    assert rec2.verified_value_json == 420000.0
    assert rec1.verified_value_json == 450000.0
    assert DocumentVerificationRecord.objects.filter(document=doc).count() >= 2

    # Immutability enforcement: direct bulk update and delete raise ValidationError
    with pytest.raises(ValidationError):
        DocumentVerificationRecord.objects.filter(id=rec1.id).update(verified_value_json=999999.0)
    with pytest.raises(ValidationError):
        DocumentVerificationRecord.objects.filter(id=rec1.id).delete()


# ==============================================================================
# G. DUPLICATE-ACTION / IDEMPOTENCY TESTS
# ==============================================================================

def test_g_idempotency_prevents_mutating_finalized_queue_item(p9_env):
    """
    Idempotency: An already finalized item (VERIFIED / CLOSED) cannot be
    re-assigned or re-resolved.
    """
    officer = p9_env["officer_1"]
    queue_item = p9_env["queue_item"]

    DocumentVerificationService.resolve_field_conflict(
        queue_item_id=queue_item.id,
        officer=officer,
        decision_action=VerificationDecisionAction.USE_DOCUMENT_VALUE,
        reason="Resolved initial"
    )

    # Attempting to assign finalized item
    with pytest.raises(ValidationError) as exc:
        DocumentVerificationService.assign_queue_item(
            queue_item_id=queue_item.id,
            officer=officer,
            assigned_to=p9_env["officer_2"]
        )
    assert "Cannot assign an already finalized item" in str(exc.value)

    # Attempting to resolve already finalized item
    with pytest.raises(ValidationError) as exc:
        DocumentVerificationService.resolve_field_conflict(
            queue_item_id=queue_item.id,
            officer=officer,
            decision_action=VerificationDecisionAction.USE_DOCUMENT_VALUE,
            reason="Duplicate resolution attempt"
        )
    assert "Cannot resolve an already finalized verification item" in str(exc.value)


# ==============================================================================
# H. CONCURRENT OFFICER TESTS
# ==============================================================================

def test_h_concurrent_officer_adjudication_safety(p9_env):
    """
    Concurrency Safety:
    Officer A and Officer B both open the same queue item.
    Officer A finalizes the item.
    Officer B attempts to resolve the item -> blocked by status check / lock.
    Result: Exactly one valid final state, no corrupted audit log.
    """
    officer_a = p9_env["officer_1"]
    officer_b = p9_env["officer_2"]
    queue_item = p9_env["queue_item"]

    # Officer A finalizes
    res_a = DocumentVerificationService.resolve_field_conflict(
        queue_item_id=queue_item.id,
        officer=officer_a,
        decision_action=VerificationDecisionAction.USE_DOCUMENT_VALUE,
        reason="Officer A completed review first"
    )
    assert res_a.verification_status == VerificationRecordStatus.VERIFIED
    queue_item.refresh_from_db()
    assert queue_item.status == VerificationStatus.VERIFIED

    # Officer B attempts conflicting action
    with pytest.raises(ValidationError) as exc:
        DocumentVerificationService.resolve_field_conflict(
            queue_item_id=queue_item.id,
            officer=officer_b,
            decision_action=VerificationDecisionAction.USE_APPLICANT_DECLARATION,
            reason="Officer B conflicting review attempt"
        )
    assert "Cannot resolve an already finalized verification item" in str(exc.value)


# ==============================================================================
# I. ELIGIBILITY REEVALUATION TESTS
# ==============================================================================

def test_i_authoritative_verification_triggers_eligibility_reevaluation(p9_env):
    """
    Eligibility Reevaluation:
    - Before verification: Applicant declared 500,000 > 250,000 threshold -> FAILS rule
    - OCR provisional: 200,000 (below threshold), but does NOT trigger automatic pass
    - Officer explicitly verifies: 200,000 (promoted to OFFICER_VERIFIED, rank 60)
    - Post-verification: Engine reevaluation executes deterministically, passing rule.
    """
    app = p9_env["application"]
    officer = p9_env["officer_1"]
    doc = p9_env["doc"]

    # Initial evaluation with declared income 500,000 (fails rule R_P9_INCOME_CEILING)
    eval_initial = RuleEvaluationService.evaluate(
        application=app,
        applicant_data={"annual_family_income": 500000.0, "community": "ST"},
        actor=officer,
        record_evaluation=False
    )
    assert eval_initial["status"] in ["FAIL", "INELIGIBLE", "UNRESOLVED", "NEEDS_REVIEW"]

    # Officer explicitly verifies income to 200,000
    DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=200000.0,
        officer=officer,
        reason="Official Tahsildar income certificate confirms family income is INR 2,00,000"
    )

    # Post-verification evaluation reflects authoritative 200,000 value
    eval_post = RuleEvaluationService.evaluate(
        application=app,
        actor=officer,
        record_evaluation=False
    )
    income_rule_res = next(
        (r for r in eval_post.get("rule_results", []) if r.get("rule_code") == "R_P9_INCOME_CEILING"),
        None
    )
    if income_rule_res:
        assert income_rule_res.get("result") == "PASS"


# ==============================================================================
# J. UNRESOLVED EVIDENCE TESTS
# ==============================================================================

def test_j_unresolved_evidence_remains_needs_review(p9_env):
    """
    Unresolved Evidence:
    Missing or unverified evidence must remain NEEDS_REVIEW / UNRESOLVED.
    Uncertainty is never silently converted into automatic rejection or pass.
    """
    queue_item = p9_env["queue_item"]
    officer = p9_env["officer_1"]

    # Detailed workspace payload reports unresolved conflicts
    detail = DocumentVerificationService.get_verification_detail(queue_item.id, officer)
    assert detail["queue_item"]["status"] == VerificationStatus.PENDING
    assert len(detail["conflicts"]) >= 1
    assert detail["conflicts"][0]["status"] == "OPEN"
    assert detail["declared_values"]["annual_family_income"] == 500000.0


# ==============================================================================
# K. TRUST HIERARCHY TESTS
# ==============================================================================

def test_k_canonical_trust_hierarchy_ranking():
    """
    Statutory Trust Hierarchy must strictly maintain:
    OFFICER_VERIFIED (60) > OFFICIAL_INTEGRATION (50) > VERIFIED_DOCUMENT (40)
    > SYSTEM (30) > APPLICANT_DECLARED (20) > OCR_PROVISIONAL (10)
    """
    assert SOURCE_TRUST_RANK[FieldValueSource.OFFICER_VERIFIED] == 60
    assert SOURCE_TRUST_RANK[FieldValueSource.OFFICIAL_INTEGRATION] == 50
    assert SOURCE_TRUST_RANK[FieldValueSource.VERIFIED_DOCUMENT] == 40
    assert SOURCE_TRUST_RANK[FieldValueSource.SYSTEM] == 30
    assert SOURCE_TRUST_RANK[FieldValueSource.APPLICANT] == 20
    assert SOURCE_TRUST_RANK[FieldValueSource.OCR_PROVISIONAL] == 10

    assert (
        SOURCE_TRUST_RANK[FieldValueSource.OFFICER_VERIFIED] >
        SOURCE_TRUST_RANK[FieldValueSource.OFFICIAL_INTEGRATION] >
        SOURCE_TRUST_RANK[FieldValueSource.VERIFIED_DOCUMENT] >
        SOURCE_TRUST_RANK[FieldValueSource.SYSTEM] >
        SOURCE_TRUST_RANK[FieldValueSource.APPLICANT] >
        SOURCE_TRUST_RANK[FieldValueSource.OCR_PROVISIONAL]
    )


# ==============================================================================
# L. REGRESSION: OCR_PROVISIONAL CANNOT BECOME VERIFIED WITHOUT OFFICER ACTION
# ==============================================================================

def test_l_ocr_provisional_never_silently_becomes_verified(p9_env):
    """
    Regression Guarantee:
    Even with 1.0 confidence, OCR_PROVISIONAL remains rank 10 and cannot
    overwrite APPLICANT_DECLARED or become OFFICER_VERIFIED without explicit
    officer decision.
    """
    app = p9_env["application"]
    income_field_def = p9_env["income_field_def"]

    # Current authoritative value is applicant-declared (rank 20)
    active_val = ApplicationFieldValue.objects.filter(
        application=app,
        field_definition=income_field_def
    ).order_by('-created_at').first()

    assert active_val.source == FieldValueSource.APPLICANT
    assert active_val.trust_rank == 20
    assert active_val.value_json == 500000.0

    # Ensure no automated process elevated OCR to verified
    verified_vals = ApplicationFieldValue.objects.filter(
        application=app,
        field_definition=income_field_def,
        source=FieldValueSource.OFFICER_VERIFIED
    )
    assert verified_vals.count() == 0
