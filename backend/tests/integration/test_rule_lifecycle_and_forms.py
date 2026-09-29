import pytest
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.documents.models import (
    SourceDocument, SourceType, SourceDocumentStatus,
    DocumentRequirement, DocumentValidityPolicy, ApplicantDocumentType
)
from apps.schemes.models import (
    Scheme, SchemeType, SchemeVersion, SchemeVersionStatus,
    SchemeRule, RuleCategory, RuleOperator, RuleSeverity, RuleStatus, ProvenanceStatus,
    ReferenceSet, ReferenceSetItem, DatasetStatus, InstitutionEligibility, EligibilityStatus
)
from apps.workflow.models import WorkflowDefinition, WorkflowState
from apps.applications.models import (
    Application, EligibilityEvaluation, EligibilityInputSnapshot,
    ApplicationFieldDefinition, ApplicationFieldValue, ApplicationDeficiency,
    FieldDataType, FieldValueSource, DeficiencyStatus
)
from apps.schemes.evaluator import RuleEvaluationService
from apps.applications.form_services import (
    FieldTrustResolver, ApplicationFormValidator, DynamicFormGenerator
)


@pytest.fixture
def lifecycle_env(db):
    user = User.objects.create_user(
        username="student_lifecycle",
        email="student_lc@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    applicant = ApplicantProfile.objects.create(
        user=user,
        community="ST",
        annual_family_income=500000,
        date_of_birth=date(2002, 5, 15)
    )
    scheme = Scheme.objects.create(
        code="TEST_LC",
        name="Lifecycle and Forms Test Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    doc = SourceDocument.objects.create(
        title="Official Lifecycle Guideline 2025-26",
        academic_year="2025-26",
        source_type=SourceType.GUIDELINE,
        checksum="a" * 64,
        content_hash="b" * 64,
        status=SourceDocumentStatus.VERIFIED
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=doc,
        status=SchemeVersionStatus.ACTIVE
    )
    workflow = WorkflowDefinition.objects.create(
        scheme_version=version,
        name="Default Flow"
    )
    state = WorkflowState.objects.create(
        workflow=workflow,
        code="DRAFT",
        display_name="Draft",
        sequence=1
    )
    app = Application.objects.create(
        application_number="MOTA/2025-26/TEST_LC/0001",
        applicant=applicant,
        scheme_version=version,
        current_state=state,
        submission_data_json={}
    )
    return {
        "user": user,
        "applicant": applicant,
        "scheme": scheme,
        "doc": doc,
        "version": version,
        "workflow": workflow,
        "state": state,
        "application": app
    }


# =============================================================================
# 1. Superseded rule is not evaluated.
# =============================================================================
@pytest.mark.django_db
def test_1_superseded_rules_are_excluded_from_evaluation(lifecycle_env):
    env = lifecycle_env
    version = env["version"]
    doc = env["doc"]
    app = env["application"]

    active_rule = SchemeRule.objects.create(
        scheme_version=version,
        rule_code="ACTIVE_COMMUNITY_RULE",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.community",
        operator=RuleOperator.EQUALS,
        value="ST",
        failure_message="Must belong to ST community.",
        source_document=doc,
        status=RuleStatus.ACTIVE
    )
    superseded_rule = SchemeRule.objects.create(
        scheme_version=version,
        rule_code="LEGACY_COMMUNITY_RULE",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.community",
        operator=RuleOperator.EQUALS,
        value="NON_ST",  # Would fail if executed
        failure_message="Legacy fail.",
        source_document=doc,
        status=RuleStatus.SUPERSEDED,
        superseded_by_rule=active_rule,
        superseded_at=timezone.now(),
        superseded_reason="Superseded by ACTIVE_COMMUNITY_RULE"
    )

    res = RuleEvaluationService.evaluate(application=app)
    rule_ids = [r["rule_id"] for r in res["rule_results"]]
    assert "ACTIVE_COMMUNITY_RULE" in rule_ids
    assert "LEGACY_COMMUNITY_RULE" not in rule_ids
    assert res["status"] == "ELIGIBLE"


# =============================================================================
# 2. Retired rule is not evaluated.
# =============================================================================
@pytest.mark.django_db
def test_2_retired_rules_are_excluded(lifecycle_env):
    env = lifecycle_env
    version = env["version"]
    doc = env["doc"]
    app = env["application"]

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RETIRED_HISTORICAL_CRITERION",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.annual_family_income",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=100000,  # Would fail for 500000 income
        failure_message="Income too high.",
        source_document=doc,
        status=RuleStatus.RETIRED
    )

    res = RuleEvaluationService.evaluate(application=app)
    rule_ids = [r["rule_id"] for r in res["rule_results"]]
    assert "RETIRED_HISTORICAL_CRITERION" not in rule_ids


# =============================================================================
# 3. NFST unknown institution returns NEEDS_REVIEW.
# =============================================================================
@pytest.mark.django_db
def test_3_nfst_unknown_institution_returns_needs_review(lifecycle_env):
    env = lifecycle_env
    version = env["version"]
    doc = env["doc"]
    app = env["application"]

    sample_ref = ReferenceSet.objects.create(
        code="NFST_RECOGNIZED_INSTITUTIONS_SAMPLE",
        name="NFST Sample Roster",
        dataset_status=DatasetStatus.SAMPLE,
        record_count_expected=150,
        record_count_loaded=1,
        source_document=doc
    )
    ReferenceSetItem.objects.create(
        reference_set=sample_ref,
        external_code="JNU_001",
        name="Jawaharlal Nehru University",
        source_document=doc
    )
    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="NFST_2025_INSTITUTION_ELIGIBILITY",
        category=RuleCategory.ELIGIBILITY,
        field_path="application.institute_code",
        operator=RuleOperator.IN_SET,
        reference_set=sample_ref,
        failure_message="Institution is not empanelled.",
        source_document=doc,
        status=RuleStatus.ACTIVE
    )

    # Applicant applies with an unknown university
    app.submission_data_json = {"application": {"institute_code": "UNKNOWN_TRIBAL_RESEARCH_INST"}}
    app.save()

    res = RuleEvaluationService.evaluate(application=app)
    assert res["status"] == "NEEDS_REVIEW"
    assert any(dq["type"] == "INCOMPLETE_REFERENCE_DATASET" for dq in res["data_quality_issues"])


# =============================================================================
# 4. Document validity without official policy returns NEEDS_REVIEW.
# =============================================================================
@pytest.mark.django_db
def test_4_document_validity_without_official_policy_returns_needs_review(lifecycle_env):
    env = lifecycle_env
    version = env["version"]
    doc = env["doc"]
    app = env["application"]

    # Rule checks caste certificate, but DocumentRequirement is NOT created
    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_CHECK_CASTE_DOC",
        category=RuleCategory.DOCUMENT,
        field_path="documents.CASTE_CERTIFICATE",
        operator=RuleOperator.EXISTS,
        failure_message="Caste certificate required.",
        source_document=doc,
        status=RuleStatus.ACTIVE
    )

    # Applicant provided document
    dossier = {
        "applicant": {"community": "ST"},
        "documents": {
            "CASTE_CERTIFICATE": {"status": "VERIFIED", "is_verified": True}
        }
    }
    res = RuleEvaluationService.evaluate(application=app, structured_fields=dossier)
    # Because validity policy is undocumented, engine refuses to make a decision
    assert res["status"] == "NEEDS_REVIEW"
    unresolved_ids = [r["rule_id"] for r in res["unresolved_rules"]]
    assert "RULE_CHECK_CASTE_DOC" in unresolved_ids


# =============================================================================
# 5. Dynamic form is generated from database definitions.
# =============================================================================
@pytest.mark.django_db
def test_5_dynamic_form_is_generated_from_database_definitions(lifecycle_env):
    env = lifecycle_env
    version = env["version"]
    doc = env["doc"]

    ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Annual Family Income",
        data_type=FieldDataType.CURRENCY,
        required=True,
        section="FINANCIAL",
        display_order=1,
        source_document=doc
    )
    ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="hostel_resident",
        label="Hostel Resident",
        data_type=FieldDataType.BOOLEAN,
        required=False,
        section="ACADEMIC",
        display_order=2,
        source_document=doc
    )

    form = DynamicFormGenerator.generate_form(version)
    assert form["scheme"] == "TEST_LC"
    assert form["academic_year"] == "2025-26"
    assert len(form["sections"]) == 2
    section_codes = [s["code"] for s in form["sections"]]
    assert "FINANCIAL" in section_codes
    assert "ACADEMIC" in section_codes


# =============================================================================
# 6. Application does not hard-code scheme fields.
# =============================================================================
@pytest.mark.django_db
def test_6_application_does_not_hard_code_scheme_fields(lifecycle_env):
    env = lifecycle_env
    doc = env["doc"]

    scheme_b = Scheme.objects.create(code="SCH_B", name="Scheme B", scheme_type=SchemeType.FELLOWSHIP)
    ver_b = SchemeVersion.objects.create(scheme=scheme_b, academic_year="2025-26", version_number=1, source_document=doc)

    ApplicationFieldDefinition.objects.create(
        scheme_version=ver_b,
        field_code="passport_number",
        label="Passport Number",
        data_type=FieldDataType.TEXT,
        section="OVERSEAS",
        source_document=doc
    )

    form_a = DynamicFormGenerator.generate_form(env["version"])
    form_b = DynamicFormGenerator.generate_form(ver_b)

    assert any(s["code"] == "OVERSEAS" for s in form_b["sections"])
    assert not any(s["code"] == "OVERSEAS" for s in form_a["sections"])


# =============================================================================
# 7. Conditional fields behave correctly.
# =============================================================================
@pytest.mark.django_db
def test_7_conditional_fields_behave_correctly(lifecycle_env):
    env = lifecycle_env
    version = env["version"]
    doc = env["doc"]

    ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="course_level",
        label="Course Level",
        data_type=FieldDataType.SELECT,
        required=True,
        validation_schema={"options": ["UG", "PG", "PHD"]},
        section="ACADEMIC",
        source_document=doc
    )
    ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="research_topic",
        label="Doctoral Research Topic",
        data_type=FieldDataType.TEXT,
        required=True,
        validation_schema={"visibility_condition": {"depends_on": "course_level", "operator": "==", "value": "PHD"}},
        section="ACADEMIC",
        source_document=doc
    )

    # Submission 1: UG level -> research_topic is hidden, so omitting it is valid
    is_valid, errors = ApplicationFormValidator.validate_submission(version, {"course_level": "UG"})
    assert is_valid is True

    # Submission 2: PHD level -> research_topic is visible and required, so omitting it fails
    is_valid_phd, errors_phd = ApplicationFormValidator.validate_submission(version, {"course_level": "PHD"})
    assert is_valid_phd is False
    assert any(e["field"] == "research_topic" for e in errors_phd)


# =============================================================================
# 8. Applicant cannot alter protected scheme data.
# =============================================================================
@pytest.mark.django_db
def test_8_applicant_cannot_alter_protected_scheme_data(lifecycle_env):
    env = lifecycle_env
    client = APIClient()
    client.force_authenticate(user=env["user"])

    res = client.post("/api/v1/schemes/", {"code": "HACKED_SCHEME", "name": "Illegal Mutation"})
    assert res.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# 9. Applicant cannot modify officer verification.
# =============================================================================
@pytest.mark.django_db
def test_9_applicant_cannot_modify_officer_verification(lifecycle_env):
    env = lifecycle_env
    app = env["application"]
    client = APIClient()
    client.force_authenticate(user=env["user"])

    url = f"/api/v1/applications/{app.id}/verify-field/"
    res = client.post(url, {"field_code": "annual_family_income", "value": 100000})
    assert res.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# 10. Applicant cannot resolve own deficiency.
# =============================================================================
@pytest.mark.django_db
def test_10_applicant_cannot_resolve_own_deficiency(lifecycle_env):
    env = lifecycle_env
    app = env["application"]
    student_user = env["user"]

    officer_user = User.objects.create_user(
        username="scrutiny_officer",
        email="officer_def@tribal.gov.in",
        password="Password123!",
        role=UserRole.SCRUTINY_OFFICER,
        is_staff=True
    )
    def_obj = ApplicationDeficiency.objects.create(
        application=app,
        deficiency_code="DEF_INCOME_CERT_UNCLEAR",
        description="Uploaded income certificate is blurry.",
        raised_by=officer_user
    )

    client = APIClient()
    client.force_authenticate(user=student_user)

    # Applicant attempts to resolve deficiency directly -> 403 Forbidden
    url = f"/api/v1/applications/{app.id}/deficiencies/{def_obj.id}/resolve/"
    res = client.post(url, {"status": DeficiencyStatus.RESOLVED})
    assert res.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# 11. Officer can verify an application field.
# =============================================================================
@pytest.mark.django_db
def test_11_officer_can_verify_an_application_field(lifecycle_env):
    env = lifecycle_env
    app = env["application"]
    version = env["version"]
    doc = env["doc"]

    ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Income",
        data_type=FieldDataType.CURRENCY,
        source_document=doc
    )

    officer = User.objects.create_user(
        username="officer_field_vf",
        email="officer_vf@tribal.gov.in",
        password="Password123!",
        role=UserRole.SCRUTINY_OFFICER,
        is_staff=True
    )
    client = APIClient()
    client.force_authenticate(user=officer)

    url = f"/api/v1/applications/{app.id}/verify-field/"
    res = client.post(url, {"field_code": "annual_family_income", "value": 540000}, format="json")
    assert res.status_code == status.HTTP_200_OK

    val_rec = ApplicationFieldValue.objects.filter(application=app, source=FieldValueSource.OFFICER).first()
    assert val_rec is not None
    assert int(val_rec.value_json) == 540000


# =============================================================================
# 12. Officer verification outranks OCR.
# =============================================================================
@pytest.mark.django_db
def test_12_officer_verification_outranks_ocr(lifecycle_env):
    env = lifecycle_env
    app = env["application"]
    version = env["version"]
    doc = env["doc"]

    fdef = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Income",
        data_type=FieldDataType.CURRENCY,
        source_document=doc
    )
    # OCR Extraction (rank 20)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=480000,
        source=FieldValueSource.OCR,
        confidence=0.88
    )
    # Officer Verification (rank 50)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=520000,
        source=FieldValueSource.OFFICER,
        confidence=1.0
    )

    effective = FieldTrustResolver.get_effective_values(app)
    assert effective["annual_family_income"]["value"] == 520000
    assert effective["annual_family_income"]["source"] == FieldValueSource.OFFICER


# =============================================================================
# 13. OCR outranks applicant declaration.
# =============================================================================
@pytest.mark.django_db
def test_ocr_provisional_does_not_outrank_applicant_declaration(lifecycle_env):
    """
    Phase 5 Trust Hierarchy Invariant:
    APPLICANT_DECLARED (rank 20) outranks OCR_PROVISIONAL (rank 10).
    VERIFIED_DOCUMENT (rank 30) outranks APPLICANT_DECLARED.
    """
    env = lifecycle_env
    app = env["application"]
    version = env["version"]
    doc = env["doc"]

    fdef = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Income",
        data_type=FieldDataType.CURRENCY,
        source_document=doc
    )
    # OCR Extraction (rank 10)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=360000,
        source=FieldValueSource.OCR,
        confidence=0.92
    )
    # Applicant Declared (rank 20)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=300000,
        source=FieldValueSource.APPLICANT
    )

    # 1. OCR cannot outrank Applicant Declared
    effective = FieldTrustResolver.get_effective_values(app)
    assert effective["annual_family_income"]["value"] == 300000
    assert effective["annual_family_income"]["source"] == FieldValueSource.APPLICANT

    # 2. Verified Document outranks Applicant Declared (rank 30 > 20)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=320000,
        source=FieldValueSource.VERIFIED_DOCUMENT,
        confidence=0.98
    )
    effective2 = FieldTrustResolver.get_effective_values(app)
    assert effective2["annual_family_income"]["value"] == 320000
    assert effective2["annual_family_income"]["source"] == FieldValueSource.VERIFIED_DOCUMENT


@pytest.mark.django_db
def test_ocr_provisional_cannot_replace_applicant_declared_value(lifecycle_env):
    """
    Explicit Trust Hierarchy Test:
    OCR_PROVISIONAL (rank 10) cannot replace an APPLICANT_DECLARED (rank 20) value.
    """
    env = lifecycle_env
    app = env["application"]
    version = env["version"]
    doc = env["doc"]

    fdef = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="candidate_category",
        label="Category",
        data_type=FieldDataType.TEXT,
        source_document=doc
    )

    # Applicant declares ST first
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json="ST",
        source=FieldValueSource.APPLICANT
    )
    effective_before = FieldTrustResolver.get_effective_values(app)
    assert effective_before["candidate_category"]["value"] == "ST"
    assert effective_before["candidate_category"]["source"] == FieldValueSource.APPLICANT

    # Provisional OCR arrives later claiming SC with high OCR confidence
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json="SC",
        source=FieldValueSource.OCR,
        confidence=0.99
    )

    # Effective value must strictly remain the applicant declared value
    effective_after = FieldTrustResolver.get_effective_values(app)
    assert effective_after["candidate_category"]["value"] == "ST"
    assert effective_after["candidate_category"]["source"] == FieldValueSource.APPLICANT


@pytest.mark.django_db
def test_verified_document_can_replace_applicant_declared_value(lifecycle_env):
    """
    Explicit Trust Hierarchy Test:
    VERIFIED_DOCUMENT (rank 30) can replace an APPLICANT_DECLARED (rank 20) value.
    """
    env = lifecycle_env
    app = env["application"]
    version = env["version"]
    doc = env["doc"]

    fdef = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Annual Income",
        data_type=FieldDataType.CURRENCY,
        source_document=doc
    )

    # Applicant declared income
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=250000,
        source=FieldValueSource.APPLICANT
    )
    assert FieldTrustResolver.get_effective_values(app)["annual_family_income"]["value"] == 250000

    # Income certificate verified extraction (rank 30)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=280000,
        source=FieldValueSource.VERIFIED_DOCUMENT,
        confidence=1.0
    )
    effective = FieldTrustResolver.get_effective_values(app)
    assert effective["annual_family_income"]["value"] == 280000
    assert effective["annual_family_income"]["source"] == FieldValueSource.VERIFIED_DOCUMENT


@pytest.mark.django_db
def test_officer_verified_can_replace_all_lower_trust_values(lifecycle_env):
    """
    Explicit Trust Hierarchy Test:
    OFFICER_VERIFIED (rank 50) replaces all lower trust tiers:
    OFFICIAL_INTEGRATION (40), VERIFIED_DOCUMENT (30), SYSTEM (25), APPLICANT (20), OCR (10).
    """
    env = lifecycle_env
    app = env["application"]
    version = env["version"]
    doc = env["doc"]

    fdef = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="verified_income",
        label="Verified Income",
        data_type=FieldDataType.CURRENCY,
        source_document=doc
    )

    # Populate lower tiers
    tiers = [
        (FieldValueSource.OCR, 100000),
        (FieldValueSource.APPLICANT, 200000),
        (FieldValueSource.SYSTEM, 220000),
        (FieldValueSource.VERIFIED_DOCUMENT, 240000),
        (FieldValueSource.OFFICIAL_INTEGRATION, 250000),
    ]
    for src, val in tiers:
        ApplicationFieldValue.objects.create(
            application=app,
            field_definition=fdef,
            value_json=val,
            source=src
        )

    # Official integration currently wins (rank 40)
    assert FieldTrustResolver.get_effective_values(app)["verified_income"]["value"] == 250000

    # Officer scrutinizes and overrides (rank 50)
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=245000,
        source=FieldValueSource.OFFICER
    )

    effective = FieldTrustResolver.get_effective_values(app)
    assert effective["verified_income"]["value"] == 245000
    assert effective["verified_income"]["source"] == FieldValueSource.OFFICER


# =============================================================================
# 14. Historical field values remain queryable.
# =============================================================================
@pytest.mark.django_db
def test_14_historical_field_values_remain_queryable(lifecycle_env):
    env = lifecycle_env
    app = env["application"]
    version = env["version"]
    doc = env["doc"]

    fdef = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Income",
        data_type=FieldDataType.CURRENCY,
        source_document=doc
    )
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=300000, source=FieldValueSource.APPLICANT)
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=360000, source=FieldValueSource.OCR)
    ApplicationFieldValue.objects.create(application=app, field_definition=fdef, value_json=400000, source=FieldValueSource.OFFICER)

    history = ApplicationFieldValue.objects.filter(application=app, field_definition=fdef)
    assert history.count() == 3
    sources = set(history.values_list('source', flat=True))
    assert sources == {FieldValueSource.APPLICANT, FieldValueSource.OCR, FieldValueSource.OFFICER}


# =============================================================================
# 15. Eligibility evaluation stores an immutable input snapshot.
# =============================================================================
@pytest.mark.django_db
def test_15_eligibility_evaluation_stores_an_immutable_input_snapshot(lifecycle_env):
    env = lifecycle_env
    app = env["application"]

    RuleEvaluationService.evaluate(application=app)
    eval_rec = EligibilityEvaluation.objects.filter(application=app).first()
    assert eval_rec is not None

    snapshot = EligibilityInputSnapshot.objects.filter(evaluation=eval_rec).first()
    assert snapshot is not None
    assert "dossier" in snapshot.payload_json
    assert len(snapshot.payload_hash) == 64

    # Immutability check
    snapshot.payload_hash = "tampered"
    with pytest.raises(ValidationError):
        snapshot.save()


# =============================================================================
# 16. Editing applicant profile after evaluation does not mutate historical evaluation.
# =============================================================================
@pytest.mark.django_db
def test_16_editing_applicant_profile_does_not_mutate_historical_evaluation(lifecycle_env):
    env = lifecycle_env
    app = env["application"]
    applicant = env["applicant"]
    version = env["version"]
    doc = env["doc"]

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_INCOME_CEILING_PASS",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.annual_family_income",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=600000,
        failure_message="Exceeds 6L.",
        source_document=doc,
        status=RuleStatus.ACTIVE
    )

    res1 = RuleEvaluationService.evaluate(application=app)
    eval_id = res1["result_hash"]

    # Applicant later edits profile to 15 Lakh
    applicant.annual_family_income = 1500000
    applicant.save()

    # Query historical record
    eval_saved = EligibilityEvaluation.objects.filter(application=app).first()
    assert eval_saved.result["status"] == "ELIGIBLE"
    assert eval_saved.result_hash == eval_id
    assert eval_saved.input_snapshot.payload_json["dossier"]["applicant"]["annual_family_income"] == 500000.0


# =============================================================================
# 17. 2025-26 application loads only 2025-26 form fields.
# =============================================================================
@pytest.mark.django_db
def test_17_2025_26_application_loads_only_2025_26_form_fields(lifecycle_env):
    env = lifecycle_env
    version_2025 = env["version"]
    doc = env["doc"]

    ApplicationFieldDefinition.objects.create(
        scheme_version=version_2025,
        field_code="ay_2025_field",
        label="2025 Unique Field",
        source_document=doc
    )

    form = DynamicFormGenerator.generate_form(version_2025)
    all_fields = [f["field_code"] for sec in form["sections"] for f in sec["fields"]]
    assert "ay_2025_field" in all_fields


# =============================================================================
# 18. 2026-27 application loads only 2026-27 form fields.
# =============================================================================
@pytest.mark.django_db
def test_18_2026_27_application_loads_only_2026_27_form_fields(lifecycle_env):
    env = lifecycle_env
    scheme = env["scheme"]
    doc = env["doc"]

    version_2026 = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2026-27",
        version_number=1,
        source_document=doc
    )
    ApplicationFieldDefinition.objects.create(
        scheme_version=version_2026,
        field_code="ay_2026_field",
        label="2026 Unique Field",
        source_document=doc
    )

    form_2026 = DynamicFormGenerator.generate_form(version_2026)
    all_fields = [f["field_code"] for sec in form_2026["sections"] for f in sec["fields"]]
    assert "ay_2026_field" in all_fields
    assert "ay_2025_field" not in all_fields


# =============================================================================
# 19. Source provenance is mandatory for official field definitions.
# =============================================================================
@pytest.mark.django_db
def test_19_source_provenance_is_mandatory_for_official_field_definitions(lifecycle_env):
    env = lifecycle_env
    version = env["version"]

    orphan_field = ApplicationFieldDefinition(
        scheme_version=version,
        field_code="orphan_field",
        label="Unverified Field",
        status="ACTIVE",
        source_document=None
    )
    with pytest.raises(ValidationError, match="Active ApplicationFieldDefinition must maintain source document provenance"):
        orphan_field.clean()


# =============================================================================
# 20. Incomplete institutional data never produces false rejection.
# =============================================================================
@pytest.mark.django_db
def test_20_incomplete_institutional_data_never_produces_false_rejection(lifecycle_env):
    env = lifecycle_env
    version = env["version"]
    doc = env["doc"]
    app = env["application"]

    partial_ref = ReferenceSet.objects.create(
        code="TOP_CLASS_PREMIER_INSTITUTES_SAMPLE",
        name="Top Class Sample Institutions",
        dataset_status=DatasetStatus.PARTIAL,
        record_count_expected=265,
        record_count_loaded=7,
        source_document=doc
    )
    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="TOP_CLASS_2025_PREMIER_INSTITUTE",
        category=RuleCategory.ELIGIBILITY,
        field_path="application.institute_code",
        operator=RuleOperator.IN_SET,
        reference_set=partial_ref,
        failure_message="Institute not in premier list.",
        source_document=doc,
        status=RuleStatus.ACTIVE
    )

    # Student chooses institution #8 (not in 7 loaded)
    app.submission_data_json = {"application": {"institute_code": "IIT_GOA_008"}}
    app.save()

    res = RuleEvaluationService.evaluate(application=app)
    assert res["status"] == "NEEDS_REVIEW"
    assert res["status"] != "INELIGIBLE"
    assert any(dq["type"] == "INCOMPLETE_REFERENCE_DATASET" for dq in res["data_quality_issues"])
