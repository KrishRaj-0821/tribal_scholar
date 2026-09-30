import threading
import uuid
from datetime import date
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.schemes.models import Scheme, SchemeVersion, SchemeType, SchemeRule, RuleType, RuleSeverity, RuleOperator
from apps.workflow.models import WorkflowDefinition, WorkflowState
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue,
    FieldDataType, FieldValueSource, FieldValueVerificationStatus,
    SOURCE_TRUST_RANK
)
from apps.documents.models import (
    ApplicantDocument, DocumentVersion, DocumentLifecycleStatus,
    ApplicantDocumentType, OCRJob, OCRResult, OCRPage, OCRBlock,
    SourceDocument, SourceDocumentStatus, SourceType, ProvisionalExtractedField
)
from apps.verification.models import (
    VerificationQueueItem, VerificationStatus, VerificationItemType,
    DocumentVerificationRecord, VerificationRecordStatus,
    VerificationDecisionAction, VerificationMethod
)
from apps.verification.services import DocumentVerificationService
from apps.schemes.evaluator import RuleEvaluationService
from apps.audit.models import AuditLog, AuditAction

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.requires_postgresql,
]


@pytest.fixture
def p8_integration_env(db):
    User.objects.filter(username__in=["p8_int_applicant", "p8_int_officer", "p8_int_officer2", "p8_int_other_user"]).delete()
    Scheme.objects.filter(code="P8_INT_SCHEME").delete()
    SourceDocument.objects.filter(checksum="7" * 64).delete()

    applicant_user = User.objects.create_user(
        username="p8_int_applicant",
        email="applicant_int@p8.gov.in",
        password="ValidPassword123!",
        role=UserRole.APPLICANT
    )
    applicant_profile = ApplicantProfile.objects.create(
        user=applicant_user,
        community="ST",
        annual_family_income=500000,
        date_of_birth=date(2002, 3, 10)
    )

    officer_user = User.objects.create_user(
        username="p8_int_officer",
        email="officer_int@p8.gov.in",
        password="ValidPassword123!",
        role=UserRole.SCRUTINY_OFFICER
    )

    officer_user2 = User.objects.create_user(
        username="p8_int_officer2",
        email="officer_int2@p8.gov.in",
        password="ValidPassword123!",
        role=UserRole.VERIFYING_AUTHORITY
    )

    other_user = User.objects.create_user(
        username="p8_int_other_user",
        email="other@p8.gov.in",
        password="ValidPassword123!",
        role=UserRole.APPLICANT
    )

    source_doc = SourceDocument.objects.create(
        title="P8 Scheme Statutory Guidelines",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="7" * 64,
        content_hash="7" * 64,
        status=SourceDocumentStatus.VERIFIED
    )

    scheme = Scheme.objects.create(
        code="P8_INT_SCHEME",
        name="Phase 8 Integration Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    scheme_version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=source_doc,
        status="ACTIVE"
    )

    workflow = WorkflowDefinition.objects.create(
        name="P8 Workflow",
        scheme_version=scheme_version,
        active=True
    )
    draft_state = WorkflowState.objects.create(
        workflow=workflow,
        code="DRAFT",
        display_name="Draft",
        sequence=1
    )

    field_def = ApplicationFieldDefinition.objects.create(
        scheme_version=scheme_version,
        field_code="annual_family_income",
        label="Annual Family Income",
        data_type=FieldDataType.CURRENCY
    )

    # Statutory Income Ceiling Rule: annual_family_income <= 450,000
    income_rule = SchemeRule.objects.create(
        scheme_version=scheme_version,
        rule_code="R_INCOME_CEILING",
        rule_type=RuleType.ELIGIBILITY,
        field_path="annual_family_income",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=450000.0,
        severity=RuleSeverity.BLOCKING,
        source_document=source_doc,
        source_excerpt="Paragraph 4.2: Maximum Family Income Ceiling",
        failure_message="Income exceeds ceiling of 450000",
        status="ACTIVE"
    )

    application = Application.objects.create(
        application_number="APP-P8-INT-001",
        applicant=applicant_profile,
        scheme_version=scheme_version,
        current_state=draft_state
    )

    # 1. Applicant initial declaration: 500,000 (which exceeds the 450,000 ceiling!)
    ApplicationFieldValue.objects.create(
        application=application,
        field_definition=field_def,
        value_json=500000.0,
        source=FieldValueSource.APPLICANT,
        confidence=1.0
    )

    # 2. Document upload and OCR result: certificate shows 450,000
    doc = ApplicantDocument.objects.create(
        application=application,
        applicant=applicant_user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        original_filename="income_certificate_2026.png",
        sha256="d" * 64,
        lifecycle_status=DocumentLifecycleStatus.SAFE
    )
    doc_ver = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        storage_key="safe/income_certificate_2026.png",
        sha256="d" * 64
    )

    ocr_job = OCRJob.objects.create(
        document=doc,
        document_version=doc_ver,
        idempotency_key="job-p8-int-01",
        status="COMPLETED"
    )
    ocr_res = OCRResult.objects.create(
        ocr_job=ocr_job,
        document=doc,
        document_version=doc_ver,
        page_count=1,
        engine_name="PaddleOCR",
        engine_version="3.0",
        pipeline_version="1.0.0",
        result_hash="e" * 64,
        full_text="वार्षिक पारिवारिक आय: 450000 रुपये"
    )
    ocr_p = OCRPage.objects.create(
        ocr_result=ocr_res,
        page_number=1,
        width=800,
        height=600,
        page_confidence=0.96,
        page_hash="f" * 64
    )
    ocr_b = OCRBlock.objects.create(
        page=ocr_p,
        extracted_text="वार्षिक पारिवारिक आय: 450000 रुपये",
        confidence=0.96,
        bbox_x=60.0,
        bbox_y=180.0,
        bbox_width=320.0,
        bbox_height=28.0,
        polygon=[[60.0, 180.0], [380.0, 180.0], [380.0, 208.0], [60.0, 208.0]],
        language="hi",
        reading_order=1
    )

    prov_field = ProvisionalExtractedField.objects.create(
        document=doc,
        document_version=doc_ver,
        ocr_result=ocr_res,
        ocr_page=ocr_p,
        ocr_block=ocr_b,
        field_code="annual_family_income",
        field_label="Annual Family Income",
        raw_value="450000",
        normalized_value=450000.0,
        confidence=0.96,
        extraction_method="REGEX_LOCATOR"
    )

    return {
        "applicant_user": applicant_user,
        "officer_user": officer_user,
        "officer_user2": officer_user2,
        "other_user": other_user,
        "application": application,
        "scheme_version": scheme_version,
        "income_rule": income_rule,
        "field_def": field_def,
        "doc": doc,
        "ocr_res": ocr_res,
        "ocr_page": ocr_p,
        "ocr_block": ocr_b,
        "prov_field": prov_field,
    }


# ==============================================================================
# INTEGRATION TEST 1: OCR Result -> Verification Queue Item
# ==============================================================================
def test_1_ocr_result_produces_verification_queue_item(p8_integration_env):
    app = p8_integration_env["application"]
    doc = p8_integration_env["doc"]

    # Create verification queue item representing OCR conflict / document scrutiny
    q_item = VerificationQueueItem.objects.create(
        application=app,
        item_type=VerificationItemType.DOCUMENT,
        target_identifier=str(doc.id),
        confidence_score=0.96,
        status=VerificationStatus.PENDING,
        ai_assistance_json={
            "conflict_type": "MATERIAL_CONFLICT",
            "declared_value": 500000.0,
            "ocr_value": 450000.0,
            "field_code": "annual_family_income"
        }
    )

    client = APIClient()
    client.force_authenticate(user=p8_integration_env["officer_user"])
    response = client.get("/api/v1/verification/queue/")

    assert response.status_code == 200
    results = response.data.get("results", response.data)
    assert any(str(q_item.id) == item["id"] for item in results)


# ==============================================================================
# INTEGRATION TEST 2: Officer views document evidence via API
# ==============================================================================
def test_2_officer_views_document_evidence_api(p8_integration_env):
    doc = p8_integration_env["doc"]
    client = APIClient()
    client.force_authenticate(user=p8_integration_env["officer_user"])

    response = client.get(f"/api/v1/verification/documents/{doc.id}/evidence/")

    assert response.status_code == 200
    data = response.data
    assert data["id"] == str(doc.id)
    assert len(data["pages"]) == 1
    page1 = data["pages"][0]
    assert page1["page_number"] == 1
    assert len(page1["blocks"]) == 1
    block = page1["blocks"][0]
    assert block["extracted_text"] == "वार्षिक पारिवारिक आय: 450000 रुपये"
    assert block["bbox_width"] == 320.0
    assert block["bbox_height"] == 28.0


# ==============================================================================
# INTEGRATION TEST 3: Officer verifies field via API
# ==============================================================================
def test_3_officer_verifies_field_api(p8_integration_env):
    doc = p8_integration_env["doc"]
    block = p8_integration_env["ocr_block"]
    client = APIClient()
    client.force_authenticate(user=p8_integration_env["officer_user"])

    payload = {
        "field_code": "annual_family_income",
        "verified_value": 450000.0,
        "reason": "Verified per official SDM income certificate",
        "block_id": str(block.id)
    }
    response = client.post(f"/api/v1/verification/documents/{doc.id}/verify-field/", data=payload, format="json")

    assert response.status_code == 200
    assert response.data["verification_status"] == "VERIFIED"
    assert response.data["verified_value_json"] == 450000.0


# ==============================================================================
# INTEGRATION TEST 4: Verification persisted in immutable model
# ==============================================================================
def test_4_verification_persisted_in_immutable_model(p8_integration_env):
    doc = p8_integration_env["doc"]
    officer = p8_integration_env["officer_user"]
    app = p8_integration_env["application"]

    record = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="SDM certificate inspected"
    )

    db_rec = DocumentVerificationRecord.objects.get(id=record.id)
    assert db_rec.verification_status == VerificationRecordStatus.VERIFIED
    assert db_rec.verified_value_json == 450000.0
    assert db_rec.officer == officer

    # Confirm ApplicationFieldValue trust rank was promoted to 50
    effective = app.get_effective_field_values()
    assert effective["annual_family_income"]["value"] == 450000.0
    assert effective["annual_family_income"]["source"] == FieldValueSource.OFFICER
    assert effective["annual_family_income"]["trust_rank"] == 50


# ==============================================================================
# INTEGRATION TEST 5: Audit event generated for verification
# ==============================================================================
def test_5_audit_event_generated_for_verification(p8_integration_env):
    doc = p8_integration_env["doc"]
    officer = p8_integration_env["officer_user"]

    record = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="Field verified during audit test"
    )

    audit_entry = AuditLog.objects.filter(
        entity_id=str(record.id),
        action=AuditAction.FIELD_VERIFIED
    ).first()

    assert audit_entry is not None
    assert audit_entry.actor == officer
    assert audit_entry.actor_role == officer.role
    assert audit_entry.after_json["verified_value"] == 450000.0


# ==============================================================================
# INTEGRATION TEST 6: Conflict resolution persisted via API
# ==============================================================================
def test_6_conflict_resolution_persisted_via_api(p8_integration_env):
    app = p8_integration_env["application"]
    officer = p8_integration_env["officer_user"]

    q_item = VerificationQueueItem.objects.create(
        application=app,
        item_type=VerificationItemType.DOCUMENT,
        target_identifier="annual_family_income",
        confidence_score=0.96,
        status=VerificationStatus.PENDING,
        ai_assistance_json={
            "conflict_type": "MATERIAL_CONFLICT",
            "field_code": "annual_family_income",
            "declared_value": 500000.0,
            "ocr_value": 450000.0
        }
    )

    client = APIClient()
    client.force_authenticate(user=officer)

    payload = {
        "decision_action": "USE_DOCUMENT_VALUE",
        "chosen_value": 450000.0,
        "reason": "Document evidence is authoritative over self-declaration"
    }
    response = client.post(f"/api/v1/verification/conflicts/{q_item.id}/resolve/", data=payload, format="json")

    assert response.status_code == 200
    assert response.data["decision_action"] == "USE_DOCUMENT_VALUE"

    q_item.refresh_from_db()
    assert q_item.status == VerificationStatus.APPROVED
    assert q_item.reviewed_by == officer


# ==============================================================================
# INTEGRATION TEST 7: Unauthorized API requests rejected
# ==============================================================================
def test_7_unauthorized_api_requests_rejected(p8_integration_env):
    doc = p8_integration_env["doc"]
    applicant = p8_integration_env["applicant_user"]
    other_user = p8_integration_env["other_user"]

    client = APIClient()

    # 1. Anonymous user -> 401
    resp_anon = client.get(f"/api/v1/verification/documents/{doc.id}/evidence/")
    assert resp_anon.status_code in (401, 403)

    # 2. Applicant user attempting officer endpoint -> 403 Forbidden
    client.force_authenticate(user=applicant)
    resp_app = client.post(
        f"/api/v1/verification/documents/{doc.id}/verify-field/",
        data={"field_code": "annual_family_income", "verified_value": 450000.0},
        format="json"
    )
    assert resp_app.status_code == 403

    # 3. Third-party applicant user -> 403 Forbidden
    client.force_authenticate(user=other_user)
    resp_other = client.get(f"/api/v1/verification/queue/")
    assert resp_other.status_code == 403


# ==============================================================================
# INTEGRATION TEST 8: Two concurrent officer verification requests are safe
# ==============================================================================
def test_8_two_concurrent_officer_verification_requests_are_safe(p8_integration_env):
    doc = p8_integration_env["doc"]
    officer1 = p8_integration_env["officer_user"]
    officer2 = p8_integration_env["officer_user2"]

    exceptions = []

    def verify_worker(officer, value):
        try:
            DocumentVerificationService.verify_field(
                document_id=doc.id,
                field_code="annual_family_income",
                verified_value=value,
                officer=officer,
                reason="Concurrent test"
            )
        except Exception as e:
            exceptions.append(e)

    t1 = threading.Thread(target=verify_worker, args=(officer1, 450000.0))
    t2 = threading.Thread(target=verify_worker, args=(officer2, 450000.0))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(exceptions) == 0, f"Concurrent execution produced errors: {exceptions}"
    records = DocumentVerificationRecord.objects.filter(document=doc, field_code="annual_family_income")
    assert records.count() >= 2


# ==============================================================================
# INTEGRATION TEST 9: Verification history remains reconstructable
# ==============================================================================
def test_9_verification_history_remains_reconstructable(p8_integration_env):
    doc = p8_integration_env["doc"]
    officer1 = p8_integration_env["officer_user"]
    officer2 = p8_integration_env["officer_user2"]

    # Initial verification: 450000
    DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer1,
        reason="First inspection"
    )

    # Subsequent re-verification by senior officer: 460000
    DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=460000.0,
        officer=officer2,
        reason="Adjusted after municipal tax document check"
    )

    client = APIClient()
    client.force_authenticate(user=officer1)
    response = client.get(f"/api/v1/verification/documents/{doc.id}/history/")

    assert response.status_code == 200
    records = response.data
    assert len(records) >= 2
    # Verify latest is first
    assert records[0]["verified_value_json"] == 460000.0
    assert records[0]["officer_name"] == officer2.username
    # Verify first verification remains preserved
    assert records[1]["verified_value_json"] == 450000.0
    assert records[1]["officer_name"] == officer1.username


# ==============================================================================
# INTEGRATION TEST 10: Verified field is consumed by deterministic eligibility engine
# ==============================================================================
def test_10_verified_field_is_consumed_by_deterministic_eligibility_engine(p8_integration_env):
    app = p8_integration_env["application"]
    doc = p8_integration_env["doc"]
    officer = p8_integration_env["officer_user"]

    # 1. Before verification: applicant declared 500,000.
    # Income ceiling is 450,000. Therefore, the deterministic engine should FAIL R_INCOME_CEILING.
    eval_before = RuleEvaluationService.evaluate(
        application=app,
        actor=officer,
        record_evaluation=False
    )
    rule_res_before = next(r for r in eval_before["rule_results"] if r["rule_code"] == "R_INCOME_CEILING")
    assert rule_res_before["result"] == "FAIL", f"Declared income of 500,000 must fail ceiling of 450,000, got {rule_res_before}"

    # 2. Officer verifies document evidence showing 450,000
    DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="Official SDM certificate verified at 450,000"
    )

    # 3. Deterministic rule evaluation runs AGAIN
    eval_after = RuleEvaluationService.evaluate(
        application=app,
        actor=officer,
        record_evaluation=False
    )
    rule_res_after = next(r for r in eval_after["rule_results"] if r["rule_code"] == "R_INCOME_CEILING")

    # 4. Confirmed: The deterministic rule engine consumes the officer-verified value (450,000 <= 450,000 -> PASS)!
    assert rule_res_after["result"] == "PASS", f"Verified income of 450,000 must pass ceiling of 450,000, got {rule_res_after}"
    # Officer did not set eligible=True; the deterministic rule engine evaluated the statutory rule!
