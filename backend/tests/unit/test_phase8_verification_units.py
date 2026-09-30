import pytest
import uuid
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.schemes.models import Scheme, SchemeVersion, SchemeType
from apps.workflow.models import WorkflowDefinition, WorkflowState
from apps.applications.models import (
    Application, ApplicationFieldDefinition, ApplicationFieldValue,
    FieldDataType, FieldValueSource, FieldValueVerificationStatus,
    SOURCE_TRUST_RANK
)
from apps.documents.models import (
    ApplicantDocument, DocumentVersion, DocumentLifecycleStatus,
    ApplicantDocumentType, OCRJob, OCRResult, OCRPage, OCRBlock,
    SourceDocument, SourceDocumentStatus, SourceType
)
from apps.verification.models import (
    VerificationQueueItem, VerificationStatus, VerificationItemType,
    DocumentVerificationRecord, VerificationRecordStatus,
    VerificationDecisionAction, VerificationMethod
)
from apps.verification.services import DocumentVerificationService
from apps.audit.models import AuditLog, AuditAction

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.requires_postgresql,
]


@pytest.fixture
def phase8_test_env(db):
    User.objects.filter(username__in=["p8_applicant", "p8_officer", "p8_unauthorized"]).delete()
    Scheme.objects.filter(code="P8_VERIF_SCHEME").delete()

    applicant_user = User.objects.create_user(
        username="p8_applicant",
        email="applicant@p8.gov.in",
        password="ValidPassword123!",
        role=UserRole.APPLICANT
    )
    applicant_profile = ApplicantProfile.objects.create(
        user=applicant_user,
        community="ST",
        annual_family_income=500000,
        date_of_birth=date(2001, 8, 15)
    )

    officer_user = User.objects.create_user(
        username="p8_officer",
        email="officer@p8.gov.in",
        password="ValidPassword123!",
        role=UserRole.SCRUTINY_OFFICER
    )

    unauthorized_user = User.objects.create_user(
        username="p8_unauthorized",
        email="unauth@p8.gov.in",
        password="ValidPassword123!",
        role=UserRole.APPLICANT
    )

    SourceDocument.objects.filter(checksum="8" * 64).delete()
    source_doc = SourceDocument.objects.create(
        title="P8 Source Guideline",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="8" * 64,
        content_hash="8" * 64,
        status=SourceDocumentStatus.VERIFIED
    )

    scheme = Scheme.objects.create(
        code="P8_VERIF_SCHEME",
        name="Phase 8 Verification Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=source_doc,
        status="ACTIVE"
    )
    workflow = WorkflowDefinition.objects.create(
        name="P8 Workflow",
        scheme_version=version,
        active=True
    )
    draft_state = WorkflowState.objects.create(
        workflow=workflow,
        code="DRAFT",
        display_name="Draft",
        sequence=1
    )

    field_def = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Annual Family Income",
        data_type=FieldDataType.CURRENCY
    )

    application = Application.objects.create(
        application_number="APP-P8-001",
        applicant=applicant_profile,
        scheme_version=version,
        current_state=draft_state
    )

    # Initial applicant declaration
    decl = ApplicationFieldValue.objects.create(
        application=application,
        field_definition=field_def,
        value_json=500000.0,
        source=FieldValueSource.APPLICANT,
        confidence=1.0
    )

    doc = ApplicantDocument.objects.create(
        application=application,
        applicant=applicant_user,
        document_type=ApplicantDocumentType.INCOME_CERTIFICATE,
        original_filename="income_cert.png",
        sha256="a" * 64,
        lifecycle_status=DocumentLifecycleStatus.SAFE
    )
    doc_ver = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        storage_key="safe/income_cert.png",
        sha256="a" * 64
    )

    ocr_job = OCRJob.objects.create(
        document=doc,
        document_version=doc_ver,
        idempotency_key="job-p8-01",
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
        result_hash="b" * 64,
        full_text="वार्षिक पारिवारिक आय: 450000 रुपये"
    )
    ocr_p = OCRPage.objects.create(
        ocr_result=ocr_res,
        page_number=1,
        width=800,
        height=600,
        page_confidence=0.95,
        page_hash="c" * 64
    )
    ocr_b = OCRBlock.objects.create(
        page=ocr_p,
        extracted_text="वार्षिक पारिवारिक आय: 450000 रुपये",
        confidence=0.95,
        bbox_x=50.0,
        bbox_y=160.0,
        bbox_width=350.0,
        bbox_height=30.0,
        polygon=[[50.0, 160.0], [400.0, 160.0], [400.0, 190.0], [50.0, 190.0]],
        language="hi",
        reading_order=1
    )

    # Initial provisional OCR field value
    ApplicationFieldValue.objects.create(
        application=application,
        field_definition=field_def,
        value_json=450000.0,
        source=FieldValueSource.OCR,
        verification_status=FieldValueVerificationStatus.PROVISIONALLY_EXTRACTED,
        confidence=0.95
    )

    return {
        "applicant_user": applicant_user,
        "officer_user": officer_user,
        "unauthorized_user": unauthorized_user,
        "application": application,
        "field_def": field_def,
        "doc": doc,
        "doc_ver": doc_ver,
        "ocr_res": ocr_res,
        "ocr_page": ocr_p,
        "ocr_block": ocr_b,
    }


# ==============================================================================
# UNIT TEST 1: Unauthorized user cannot verify
# ==============================================================================
def test_1_unauthorized_user_cannot_verify(phase8_test_env):
    doc = phase8_test_env["doc"]
    unauth = phase8_test_env["unauthorized_user"]

    with pytest.raises(PermissionDenied) as exc:
        DocumentVerificationService.verify_field(
            document_id=doc.id,
            field_code="annual_family_income",
            verified_value=450000.0,
            officer=unauth,
            reason="Unauthorized attempt"
        )
    assert "Only authorized officers/reviewers" in str(exc.value)


# ==============================================================================
# UNIT TEST 2: Applicant cannot verify own document (Separation of Duties)
# ==============================================================================
def test_2_applicant_cannot_verify_own_document(phase8_test_env):
    doc = phase8_test_env["doc"]
    applicant = phase8_test_env["applicant_user"]

    with pytest.raises(PermissionDenied) as exc:
        DocumentVerificationService.verify_field(
            document_id=doc.id,
            field_code="annual_family_income",
            verified_value=450000.0,
            officer=applicant,
            reason="Applicant self-verifying"
        )
    assert "Separation of Duties violation" in str(exc.value) or "Only authorized officers" in str(exc.value)


# ==============================================================================
# UNIT TEST 3: Explicit verification increases trust to OFFICER (rank 50)
# ==============================================================================
def test_3_explicit_verification_increases_trust(phase8_test_env):
    doc = phase8_test_env["doc"]
    officer = phase8_test_env["officer_user"]
    app = phase8_test_env["application"]
    block = phase8_test_env["ocr_block"]

    record = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="SDM Income certificate verified",
        block_id=str(block.id)
    )

    assert record.verification_status == VerificationRecordStatus.VERIFIED
    assert record.decision_action == VerificationDecisionAction.USE_DOCUMENT_VALUE
    assert record.verified_value_json == 450000.0

    # Verify ApplicationFieldValue trust rank
    effective = app.get_effective_field_values()
    assert "annual_family_income" in effective
    assert effective["annual_family_income"]["value"] == 450000.0
    assert effective["annual_family_income"]["source"] == FieldValueSource.OFFICER
    assert effective["annual_family_income"]["trust_rank"] == SOURCE_TRUST_RANK[FieldValueSource.OFFICER]


# ==============================================================================
# UNIT TEST 4: OCR confidence alone cannot increase trust
# ==============================================================================
def test_4_ocr_confidence_alone_cannot_increase_trust(phase8_test_env):
    app = phase8_test_env["application"]
    field_def = phase8_test_env["field_def"]

    # Even with 100% confidence, OCR source stays at trust rank 10
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=field_def,
        value_json=400000.0,
        source=FieldValueSource.OCR,
        confidence=1.0
    )

    effective = app.get_effective_field_values()
    # Applicant declaration (500000, rank 20) must still outrank OCR (400000, rank 10)
    assert effective["annual_family_income"]["value"] == 500000.0
    assert effective["annual_family_income"]["source"] == FieldValueSource.APPLICANT


# ==============================================================================
# UNIT TEST 5: Verification history is immutable
# ==============================================================================
def test_5_verification_history_is_immutable(phase8_test_env):
    doc = phase8_test_env["doc"]
    officer = phase8_test_env["officer_user"]

    record = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="Initial verification"
    )

    # Calling .update() raises ValidationError
    with pytest.raises(ValidationError):
        DocumentVerificationRecord.objects.filter(id=record.id).update(verified_value_json=500000.0)

    # Calling .delete() raises ValidationError
    with pytest.raises(ValidationError):
        DocumentVerificationRecord.objects.filter(id=record.id).delete()


# ==============================================================================
# UNIT TEST 6: Conflict creates review state
# ==============================================================================
def test_6_conflict_creates_review_state(phase8_test_env):
    app = phase8_test_env["application"]
    officer = phase8_test_env["officer_user"]

    q_item = VerificationQueueItem.objects.create(
        application=app,
        item_type=VerificationItemType.DOCUMENT,
        target_identifier="annual_family_income",
        ai_assistance_json={
            "conflict_type": "MATERIAL_CONFLICT",
            "declared_value": 500000.0,
            "ocr_value": 450000.0,
            "field_code": "annual_family_income"
        }
    )

    record = DocumentVerificationService.resolve_field_conflict(
        queue_item_id=q_item.id,
        decision_action=VerificationDecisionAction.REQUEST_CORRECTION,
        chosen_value=None,
        officer=officer,
        reason="Discrepancy exceeds tolerance; applicant re-upload required."
    )

    q_item.refresh_from_db()
    assert record.verification_status == VerificationRecordStatus.NEEDS_REVIEW
    assert q_item.status == VerificationStatus.DEFECT_FLAGGED


# ==============================================================================
# UNIT TEST 7: Conflict resolution records actor and justification
# ==============================================================================
def test_7_conflict_resolution_records_actor(phase8_test_env):
    app = phase8_test_env["application"]
    officer = phase8_test_env["officer_user"]

    q_item = VerificationQueueItem.objects.create(
        application=app,
        item_type=VerificationItemType.DOCUMENT,
        target_identifier="annual_family_income",
        ai_assistance_json={
            "conflict_type": "MATERIAL_CONFLICT",
            "field_code": "annual_family_income"
        }
    )

    record = DocumentVerificationService.resolve_field_conflict(
        queue_item_id=q_item.id,
        decision_action=VerificationDecisionAction.USE_DOCUMENT_VALUE,
        chosen_value=450000.0,
        officer=officer,
        reason="Document evidence accepted after gazette review."
    )

    assert record.officer == officer
    assert record.officer_role == officer.role
    assert "gazette review" in record.reason

    audit = AuditLog.objects.filter(
        entity_id=str(q_item.id),
        action=AuditAction.FIELD_CONFLICT_RESOLVED
    ).first()
    assert audit is not None
    assert audit.actor == officer
    assert audit.after_json["decision_action"] == "USE_DOCUMENT_VALUE"


# ==============================================================================
# UNIT TEST 8: Document evidence reference preserved
# ==============================================================================
def test_8_document_evidence_reference_preserved(phase8_test_env):
    doc = phase8_test_env["doc"]
    officer = phase8_test_env["officer_user"]
    block = phase8_test_env["ocr_block"]
    page = phase8_test_env["ocr_page"]

    record = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        block_id=str(block.id),
        page_id=str(page.id)
    )

    assert record.document == doc
    assert record.ocr_block == block
    assert record.ocr_page == page
    assert record.ocr_block.extracted_text == "वार्षिक पारिवारिक आय: 450000 रुपये"
    assert record.ocr_block.bbox_width == 350.0


# ==============================================================================
# UNIT TEST 9: Reopening creates new history without deleting past record
# ==============================================================================
def test_9_reopening_creates_new_history(phase8_test_env):
    doc = phase8_test_env["doc"]
    officer = phase8_test_env["officer_user"]

    rec1 = DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="First verification"
    )

    rec2 = DocumentVerificationService.reopen_verification(
        document_id=doc.id,
        officer=officer,
        reason="Re-investigating income per grievance cell query"
    )

    rec1.refresh_from_db()
    assert rec2.superseded_record == rec1
    assert rec2.verification_status == VerificationRecordStatus.NEEDS_REVIEW
    assert DocumentVerificationRecord.objects.filter(document=doc).count() >= 2
    # Verify historical immutability: rec1 remains exactly preserved
    assert rec1.verification_status == VerificationRecordStatus.VERIFIED
    assert rec1.verified_value_json == 450000.0


# ==============================================================================
# UNIT TEST 10: Verification does not directly decide eligibility
# ==============================================================================
def test_10_verification_does_not_directly_decide_eligibility(phase8_test_env):
    doc = phase8_test_env["doc"]
    officer = phase8_test_env["officer_user"]
    app = phase8_test_env["application"]

    # Before verification: application is DRAFT
    assert app.current_state.code == "DRAFT"

    # Officer verifies field and completes document verification
    DocumentVerificationService.verify_field(
        document_id=doc.id,
        field_code="annual_family_income",
        verified_value=450000.0,
        officer=officer,
        reason="Field verified"
    )
    DocumentVerificationService.complete_document_verification(
        document_id=doc.id,
        officer=officer,
        reason="Document completed"
    )

    app.refresh_from_db()
    # Application state remains strictly DRAFT; no hidden eligible=True or APPROVED
    assert app.current_state.code == "DRAFT"
