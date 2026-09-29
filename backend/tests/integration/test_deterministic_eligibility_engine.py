import pytest
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from rest_framework import status

from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile
from apps.applications.models import Application, EligibilityEvaluation
from apps.audit.models import AuditLog, AuditAction
from apps.documents.models import SourceDocument, SourceType
from apps.schemes.models import (
    Scheme, SchemeType, SchemeVersion, SchemeVersionStatus,
    SchemeRule, RuleCategory, RuleOperator, RuleSeverity, RuleStatus, ProvenanceStatus,
    ReferenceSet, ReferenceSetItem, DatasetStatus,
    SchemeQuota, SelectionMethod, InstitutionEligibility, EligibilityStatus
)
from apps.schemes.evaluator import RuleEvaluationService
from apps.workflow.models import WorkflowDefinition, WorkflowState


@pytest.fixture
def base_test_environment(db):
    """
    Sets up a minimal isolated scheme version with verified document provenance.
    """
    scheme = Scheme.objects.create(
        code="TEST_SCHEME",
        name="Deterministic Test Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    doc = SourceDocument.objects.create(
        title="Official Test Guideline 2025-26",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        source_url="https://tribal.nic.in/test-guideline.pdf",
        checksum="1" * 64,
        content_hash="2" * 64
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        status=SchemeVersionStatus.ACTIVE,
        source_document=doc
    )
    wf = WorkflowDefinition.objects.create(scheme_version=version, name="Test WF", active=True)
    state = WorkflowState.objects.create(workflow=wf, code="SUBMITTED", display_name="Submitted", sequence=10)

    user = User.objects.create_user(username="test_student", email="student@tribal.gov.in", password="Password123!", role=UserRole.APPLICANT)
    applicant = ApplicantProfile.objects.create(user=user, community="ST", annual_family_income=Decimal("400000.00"))

    app = Application.objects.create(
        application_number="MOTA/2025-26/TEST/0001",
        applicant=applicant,
        scheme_version=version,
        current_state=state,
        submission_data_json={
            "applicant": {
                "community": "ST",
                "annual_family_income": 400000
            },
            "application": {
                "course_level": "Undergraduate",
                "institute_code": "COL-001"
            },
            "documents": {
                "caste_certificate": True
            }
        }
    )
    return {
        "scheme": scheme,
        "version": version,
        "doc": doc,
        "application": app,
        "applicant": applicant,
        "user": user
    }


# =============================================================================
# SCENARIO A: Complete verified reference set: Known eligible institution -> ELIGIBLE
# =============================================================================
@pytest.mark.django_db
def test_scenario_a_complete_verified_reference_set_eligible(base_test_environment):
    env = base_test_environment
    version = env["version"]
    doc = env["doc"]

    ref_set = ReferenceSet.objects.create(
        code="COMPLETE_VERIFIED_ROSTER",
        name="Official Empanelled Roster",
        dataset_status=DatasetStatus.VERIFIED,
        record_count_expected=2,
        record_count_loaded=2,
        source_document=doc
    )
    ReferenceSetItem.objects.create(reference_set=ref_set, external_code="COL-001", name="Empanelled College A", source_document=doc)
    ReferenceSetItem.objects.create(reference_set=ref_set, external_code="COL-002", name="Empanelled College B", source_document=doc)

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_INSTITUTION_IN_SET",
        category=RuleCategory.ELIGIBILITY,
        field_path="application.institute_code",
        operator=RuleOperator.IN_SET,
        reference_set=ref_set,
        failure_message="Institution is not empanelled.",
        source_document=doc,
        source_excerpt="Official list of verified institutions.",
        status=RuleStatus.ACTIVE,
        provenance_status=ProvenanceStatus.OFFICIAL_VERIFIED
    )

    dossier = {
        "applicant": {"community": "ST"},
        "application": {"institute_code": "COL-001"}
    }
    result = RuleEvaluationService.evaluate("APP-SCENARIO-A", version, dossier)
    assert result["status"] == "ELIGIBLE"
    assert len(result["blocking_failures"]) == 0
    assert any(r["rule_id"] == "RULE_INSTITUTION_IN_SET" and r["result"] == "PASS" for r in result["matched_rules"])


# =============================================================================
# SCENARIO B: Complete verified reference set: Known non-eligible institution -> INELIGIBLE
# =============================================================================
@pytest.mark.django_db
def test_scenario_b_complete_verified_reference_set_non_eligible(base_test_environment):
    env = base_test_environment
    version = env["version"]
    doc = env["doc"]

    ref_set = ReferenceSet.objects.create(
        code="COMPLETE_VERIFIED_ROSTER_B",
        name="Authoritative Master Roster",
        dataset_status=DatasetStatus.VERIFIED,
        record_count_expected=2,
        record_count_loaded=2,
        source_document=doc
    )
    ReferenceSetItem.objects.create(reference_set=ref_set, external_code="COL-001", name="Empanelled College A", source_document=doc)
    ReferenceSetItem.objects.create(reference_set=ref_set, external_code="COL-002", name="Empanelled College B", source_document=doc)

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_INSTITUTION_IN_SET_B",
        category=RuleCategory.ELIGIBILITY,
        field_path="application.institute_code",
        operator=RuleOperator.IN_SET,
        reference_set=ref_set,
        failure_message="Institution is not empanelled in verified master list.",
        source_document=doc,
        source_excerpt="Authoritative roster of empanelled institutes.",
        status=RuleStatus.ACTIVE,
        provenance_status=ProvenanceStatus.OFFICIAL_VERIFIED,
        severity=RuleSeverity.BLOCKING
    )

    dossier = {
        "applicant": {"community": "ST"},
        "application": {"institute_code": "COL-999-UNLISTED"}
    }
    result = RuleEvaluationService.evaluate("APP-SCENARIO-B", version, dossier)
    assert result["status"] == "INELIGIBLE"
    assert len(result["blocking_failures"]) == 1
    assert "COL-999-UNLISTED" in result["blocking_failures"][0]["detail"]


# =============================================================================
# SCENARIO C: Partial reference set: Unknown institution -> NEEDS_REVIEW
# =============================================================================
@pytest.mark.django_db
def test_scenario_c_partial_reference_set_unknown_institution(base_test_environment):
    env = base_test_environment
    version = env["version"]
    doc = env["doc"]

    ref_set = ReferenceSet.objects.create(
        code="PARTIAL_ROSTER_C",
        name="Partial Roster",
        dataset_status=DatasetStatus.PARTIAL,
        record_count_expected=265,
        record_count_loaded=7,
        source_document=doc
    )
    ReferenceSetItem.objects.create(reference_set=ref_set, external_code="IIT-BOM", name="IIT Bombay", source_document=doc)

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_TOP_CLASS_INST",
        category=RuleCategory.ELIGIBILITY,
        field_path="application.institute_code",
        operator=RuleOperator.IN_SET,
        reference_set=ref_set,
        failure_message="Institute not empanelled.",
        source_document=doc,
        source_excerpt="265 premier institutes.",
        status=RuleStatus.ACTIVE,
        provenance_status=ProvenanceStatus.OFFICIAL_VERIFIED,
        severity=RuleSeverity.BLOCKING
    )

    # Candidate selects an institution not in the 7 loaded records
    dossier = {
        "applicant": {"community": "ST"},
        "application": {"institute_code": "IIT-ROORKEE"}
    }
    result = RuleEvaluationService.evaluate("APP-SCENARIO-C", version, dossier)

    # CRITICAL: Must be NEEDS_REVIEW, NOT INELIGIBLE!
    assert result["status"] == "NEEDS_REVIEW"
    assert len(result["blocking_failures"]) == 0
    assert len(result["unresolved_rules"]) == 1
    assert any(dq["type"] == "INCOMPLETE_REFERENCE_DATASET" for dq in result["data_quality_issues"])
    assert "Reference data is incomplete" in result["unresolved_rules"][0]["explanation"]


# =============================================================================
# SCENARIO D: Sample reference set: Unknown institution -> NEEDS_REVIEW
# =============================================================================
@pytest.mark.django_db
def test_scenario_d_sample_reference_set_unknown_institution(base_test_environment):
    env = base_test_environment
    version = env["version"]
    doc = env["doc"]

    ref_set = ReferenceSet.objects.create(
        code="SAMPLE_UNIVERSITIES_D",
        name="Sample Universities",
        dataset_status=DatasetStatus.SAMPLE,
        record_count_expected=150,
        record_count_loaded=4,
        source_document=doc
    )
    ReferenceSetItem.objects.create(reference_set=ref_set, external_code="DU-DEL", name="Delhi University", source_document=doc)

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_NFST_INST",
        category=RuleCategory.ELIGIBILITY,
        field_path="application.institute_code",
        operator=RuleOperator.IN_SET,
        reference_set=ref_set,
        failure_message="Institution must be UGC recognized.",
        source_document=doc,
        source_excerpt="UGC 2f/12B universities.",
        status=RuleStatus.ACTIVE,
        provenance_status=ProvenanceStatus.OFFICIAL_VERIFIED,
        severity=RuleSeverity.BLOCKING
    )

    dossier = {
        "applicant": {"community": "ST"},
        "application": {"institute_code": "CALCUTTA-UNIV"}
    }
    result = RuleEvaluationService.evaluate("APP-SCENARIO-D", version, dossier)
    assert result["status"] == "NEEDS_REVIEW"
    assert len(result["blocking_failures"]) == 0
    assert any(dq["type"] == "INCOMPLETE_REFERENCE_DATASET" for dq in result["data_quality_issues"])


# =============================================================================
# SCENARIO E: Missing required field: NEEDS_REVIEW
# =============================================================================
@pytest.mark.django_db
def test_scenario_e_missing_required_field_returns_needs_review(base_test_environment):
    env = base_test_environment
    version = env["version"]
    doc = env["doc"]

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_MANDATORY_INCOME",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.annual_family_income",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=600000,
        failure_message="Income ceiling exceeded.",
        source_document=doc,
        source_excerpt="Income must not exceed 6 lakh.",
        status=RuleStatus.ACTIVE,
        provenance_status=ProvenanceStatus.OFFICIAL_VERIFIED,
        severity=RuleSeverity.BLOCKING
    )

    # Dossier completely lacks annual_family_income
    dossier = {
        "applicant": {"community": "ST"},
        "application": {"course_level": "Undergraduate"}
    }
    result = RuleEvaluationService.evaluate("APP-SCENARIO-E", version, dossier)
    assert result["status"] == "NEEDS_REVIEW"
    assert len(result["blocking_failures"]) == 0
    assert any(unres["rule_id"] == "RULE_MANDATORY_INCOME" for unres in result["unresolved_rules"])


# =============================================================================
# SCENARIO F: Blocking eligibility failure: INELIGIBLE
# =============================================================================
@pytest.mark.django_db
def test_scenario_f_blocking_eligibility_failure_returns_ineligible(base_test_environment):
    env = base_test_environment
    version = env["version"]
    doc = env["doc"]

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_INCOME_CEILING_BLOCKING",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.annual_family_income",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=600000,
        failure_message="Income exceeds ₹6,00,000 ceiling.",
        source_document=doc,
        source_excerpt="Income ceiling clause.",
        status=RuleStatus.ACTIVE,
        provenance_status=ProvenanceStatus.OFFICIAL_VERIFIED,
        severity=RuleSeverity.BLOCKING
    )

    dossier = {
        "applicant": {"annual_family_income": 850000}
    }
    result = RuleEvaluationService.evaluate("APP-SCENARIO-F", version, dossier)
    assert result["status"] == "INELIGIBLE"
    assert len(result["blocking_failures"]) == 1
    assert "exceeds statutory ceiling" in result["blocking_failures"][0]["explanation"]


# =============================================================================
# SCENARIO G: Warning only: ELIGIBLE
# =============================================================================
@pytest.mark.django_db
def test_scenario_g_warning_only_does_not_block_eligibility(base_test_environment):
    env = base_test_environment
    version = env["version"]
    doc = env["doc"]

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_WARNING_OPTIONAL",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.residence_state",
        operator=RuleOperator.EQUALS,
        value="Odisha",
        failure_message="Applicant is outside target state for this regional grant notice.",
        source_document=doc,
        source_excerpt="Special focus on Odisha.",
        status=RuleStatus.ACTIVE,
        provenance_status=ProvenanceStatus.OFFICIAL_VERIFIED,
        severity=RuleSeverity.WARNING
    )

    dossier = {
        "applicant": {"residence_state": "Jharkhand"}
    }
    result = RuleEvaluationService.evaluate("APP-SCENARIO-G", version, dossier)
    assert result["status"] == "ELIGIBLE"
    assert len(result["blocking_failures"]) == 0
    assert len(result["warnings"]) == 1


# =============================================================================
# SCENARIO H: Unverified official rule: NEEDS_REVIEW
# =============================================================================
@pytest.mark.django_db
def test_scenario_h_unverified_rule_returns_needs_review(base_test_environment):
    env = base_test_environment
    version = env["version"]
    doc = env["doc"]

    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="RULE_PENDING_PROVENANCE",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.community",
        operator=RuleOperator.EQUALS,
        value="ST",
        failure_message="Candidate must be ST.",
        source_document=doc,
        source_excerpt="",
        status=RuleStatus.ACTIVE,
        provenance_status=ProvenanceStatus.OFFICIAL_PENDING_VERIFICATION,
        severity=RuleSeverity.BLOCKING
    )

    dossier = {"applicant": {"community": "ST"}}
    result = RuleEvaluationService.evaluate("APP-SCENARIO-H", version, dossier)
    assert result["status"] == "NEEDS_REVIEW"
    assert len(result["unresolved_rules"]) == 1
    assert "OFFICIAL_PENDING_VERIFICATION" in result["unresolved_rules"][0]["explanation"]


# =============================================================================
# SCENARIOS I & J: 2025-26 uses 2025-26 rules; 2026-27 uses 2026-27 rules
# =============================================================================
@pytest.mark.django_db
def test_scenario_i_and_j_academic_year_isolation(seeded_db):
    nos_scheme = Scheme.objects.get(code="NOS")
    v2025 = SchemeVersion.objects.get(scheme=nos_scheme, academic_year="2025-26")
    v2026 = SchemeVersion.objects.get(scheme=nos_scheme, academic_year="2026-27")

    # A candidate researching Indian Culture (prohibited under 2026-27 amendment, but not in 2025-26)
    dossier_culture = {
        "applicant": {
            "community": "ST",
            "annual_family_income": 400000,
            "age_on_july_1": 28
        },
        "application": {
            "study_destination": "ABROAD",
            "course_level": "PhD",
            "foreign_university_qs_rank": 800,
            "is_indian_culture_or_heritage_topic": True,
            "academic_year": "2025-26"
        },
        "documents": {
            "digilocker_verified": True
        }
    }

    # Under 2025-26: Indian culture restriction rule does not exist
    result_2025 = RuleEvaluationService.evaluate("APP-NOS-2025", v2025, dossier_culture)
    assert result_2025["status"] == "ELIGIBLE"
    assert not any(r["rule_id"] == "NOS_2026_RESTRICTED_INDIAN_SUBJECTS" for r in result_2025["rule_results"])

    # Under 2026-27: Candidate is blocked by the amendment rule
    dossier_culture_2026 = dict(dossier_culture)
    dossier_culture_2026["application"] = dict(dossier_culture["application"])
    dossier_culture_2026["application"]["academic_year"] = "2026-27"

    result_2026 = RuleEvaluationService.evaluate("APP-NOS-2026", v2026, dossier_culture_2026)
    assert result_2026["status"] == "INELIGIBLE"
    assert any(fail["rule_id"] == "NOS_2026_RESTRICTED_INDIAN_SUBJECTS" for fail in result_2026["blocking_failures"])


# =============================================================================
# SCENARIO K: Creating 2026-27 version does not modify 2025-26 result
# =============================================================================
@pytest.mark.django_db
def test_scenario_k_new_version_does_not_alter_historical_result(seeded_db):
    nos_scheme = Scheme.objects.get(code="NOS")
    v2025 = SchemeVersion.objects.get(scheme=nos_scheme, academic_year="2025-26")

    dossier = {
        "applicant": {
            "community": "ST",
            "annual_family_income": 400000,
            "age_on_july_1": 30
        },
        "application": {
            "study_destination": "ABROAD",
            "course_level": "PhD",
            "academic_year": "2025-26"
        }
    }
    res_before = RuleEvaluationService.evaluate("APP-IMMUTABLE-TEST", v2025, dossier)

    # Now create or modify a rule in 2026-27
    v2026 = SchemeVersion.objects.get(scheme=nos_scheme, academic_year="2026-27")
    SchemeRule.objects.create(
        scheme_version=v2026,
        rule_code="NOS_2026_TEMP_CHANGE",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.custom_flag",
        operator=RuleOperator.EQUALS,
        value="REQUIRED",
        failure_message="Flag required",
        source_document=v2026.source_document,
        source_excerpt="Excerpt",
        status=RuleStatus.ACTIVE
    )

    res_after = RuleEvaluationService.evaluate("APP-IMMUTABLE-TEST", v2025, dossier)
    assert res_before["status"] == res_after["status"]
    assert res_before["result_hash"] == res_after["result_hash"]


# =============================================================================
# SCENARIOS L, M, N: Quota, Preference, Selection Isolation
# =============================================================================
@pytest.mark.django_db
def test_scenario_l_m_n_category_isolation(seeded_db):
    nfst_scheme = Scheme.objects.get(code="NFST")
    v2025 = SchemeVersion.objects.get(scheme=nfst_scheme, academic_year="2025-26")

    dossier = {
        "applicant": {
            "community": "ST",
            "is_pvtg": False,
            "is_disabled": False
        },
        "application": {
            "course_level": "PhD",
            "institute_code": "JNU-ND"
        },
        "documents": {
            "caste_certificate": True,
            "admission_letter": True
        }
    }
    result = RuleEvaluationService.evaluate("APP-CATEGORY-ISOLATION", v2025, dossier)
    assert result["status"] == "ELIGIBLE"

    # L: Quota rule never runs in eligibility
    assert not any("quota" in r["rule_id"].lower() for r in result["rule_results"])
    # M: Non-preference candidate is not disqualified
    assert len(result["blocking_failures"]) == 0
    # N: Selection method does not block eligibility
    assert not any("selection" in r["rule_id"].lower() for r in result["rule_results"])


# =============================================================================
# SCENARIO O: Course-specific institution eligibility works
# =============================================================================
@pytest.mark.django_db
def test_scenario_o_course_specific_institution_eligibility(seeded_db):
    tc_scheme = Scheme.objects.get(code="TOP_CLASS")
    v2025 = SchemeVersion.objects.get(scheme=tc_scheme, academic_year="2025-26")
    ref_set = ReferenceSet.objects.get(code="TOP_CLASS_PREMIER_INSTITUTES_SAMPLE")
    iit_bombay = ref_set.items.get(external_code="IIT-BOM")

    # Mark an unapproved course as INELIGIBLE
    InstitutionEligibility.objects.create(
        scheme_version=v2025,
        institution=iit_bombay,
        course_name="Aviation Hospitality",
        eligibility_status=EligibilityStatus.INELIGIBLE,
        source_document=v2025.source_document
    )

    base = {
        "applicant": {"community": "ST", "annual_family_income": 400000},
        "application": {"institute_code": "IIT-BOM"},
        "documents": {"income_certificate": True}
    }

    # O.1: Approved course -> PASS / ELIGIBLE
    dossier_approved = dict(base)
    dossier_approved["application"] = dict(base["application"])
    dossier_approved["application"]["course_name"] = "B.Tech"
    res_app = RuleEvaluationService.evaluate("APP-APPROVED", v2025, dossier_approved)
    assert res_app["status"] == "ELIGIBLE"

    # O.2: Ineligible course -> FAIL / INELIGIBLE
    dossier_ineligible = dict(base)
    dossier_ineligible["application"] = dict(base["application"])
    dossier_ineligible["application"]["course_name"] = "Aviation Hospitality"
    res_ineligible = RuleEvaluationService.evaluate("APP-INELIGIBLE", v2025, dossier_ineligible)
    assert res_ineligible["status"] == "INELIGIBLE"

    # O.3: Unloaded course coverage on empanelled institute -> UNRESOLVED / NEEDS_REVIEW
    dossier_unloaded = dict(base)
    dossier_unloaded["application"] = dict(base["application"])
    dossier_unloaded["application"]["course_name"] = "Cybersecurity Diploma"
    res_unloaded = RuleEvaluationService.evaluate("APP-UNLOADED", v2025, dossier_unloaded)
    assert res_unloaded["status"] == "NEEDS_REVIEW"
    assert "not yet fully loaded or verified" in res_unloaded["unresolved_rules"][0]["explanation"]


# =============================================================================
# SCENARIO P: Incomplete reference dataset cannot produce false INELIGIBLE result
# =============================================================================
@pytest.mark.django_db
def test_scenario_p_incomplete_dataset_cannot_falsely_reject(seeded_db):
    tc_scheme = Scheme.objects.get(code="TOP_CLASS")
    v2025 = SchemeVersion.objects.get(scheme=tc_scheme, academic_year="2025-26")

    dossier = {
        "applicant": {"community": "ST", "annual_family_income": 400000},
        "application": {
            "institute_code": "COLLEGE_NOT_IN_7_LOADED_RECORDS"
        },
        "documents": {"income_certificate": True}
    }
    result = RuleEvaluationService.evaluate("APP-INCOMPLETE-SAFETY", v2025, dossier)
    assert result["status"] == "NEEDS_REVIEW"
    assert result["status"] != "INELIGIBLE"
    assert len(result["blocking_failures"]) == 0


# =============================================================================
# SCENARIO Q: Two identical evaluations produce same result_hash
# =============================================================================
@pytest.mark.django_db
def test_scenario_q_idempotent_result_hash(seeded_db):
    tc_scheme = Scheme.objects.get(code="TOP_CLASS")
    v2025 = SchemeVersion.objects.get(scheme=tc_scheme, academic_year="2025-26")

    dossier = {
        "applicant": {"community": "ST", "annual_family_income": 350000},
        "application": {"institute_code": "IIT-BOM", "course_name": "B.Tech"},
        "documents": {"income_certificate": True}
    }

    res1 = RuleEvaluationService.evaluate("APP-HASH-1", v2025, dossier)
    res2 = RuleEvaluationService.evaluate("APP-HASH-2", v2025, dossier)

    assert res1["result_hash"] is not None
    assert res1["result_hash"] == res2["result_hash"]


# =============================================================================
# SCENARIO R: Historical evaluations remain immutable
# =============================================================================
@pytest.mark.django_db
def test_scenario_r_historical_evaluations_immutable(base_test_environment):
    env = base_test_environment
    app = env["application"]
    version = env["version"]

    eval_record = EligibilityEvaluation.objects.create(
        application=app,
        scheme_version=version,
        engine_version="2.0.0",
        result={"status": "ELIGIBLE"},
        result_hash="abc" * 20
    )

    # Attempting to modify existing evaluation must raise ValidationError
    eval_record.result = {"status": "TAMPERED"}
    with pytest.raises(ValidationError, match="EligibilityEvaluation records are strictly immutable"):
        eval_record.save()

    # Attempting to delete must raise ValidationError
    with pytest.raises(ValidationError, match="EligibilityEvaluation records cannot be deleted"):
        eval_record.delete()


# =============================================================================
# SCENARIO S: API Endpoint & RBAC Authorization Checks
# =============================================================================
@pytest.mark.django_db
def test_scenario_s_api_evaluate_eligibility_rbac(api_client, base_test_environment):
    env = base_test_environment
    app = env["application"]
    student_user = env["user"]

    # 1. Unauthenticated request -> 401 / 403
    url = f"/api/v1/applications/{app.id}/evaluate-eligibility/"
    res_anon = api_client.post(url)
    assert res_anon.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    # 2. Another applicant trying to evaluate this student's application -> 403 Forbidden
    other_user = User.objects.create_user(username="other_student", email="other@tribal.gov.in", password="Password123!", role=UserRole.APPLICANT)
    api_client.force_authenticate(user=other_user)
    # Filtered queryset returns 404 or 403
    res_other = api_client.post(url)
    assert res_other.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    # 3. Application owner evaluating their own application -> 200 OK
    api_client.force_authenticate(user=student_user)
    res_owner = api_client.post(url)
    assert res_owner.status_code == status.HTTP_200_OK
    assert "status" in res_owner.data
    assert "rule_results" in res_owner.data
    assert "result_hash" in res_owner.data

    # 4. Scrutiny Officer evaluating application -> 200 OK
    officer_user = User.objects.create_user(username="officer_01", email="officer@tribal.gov.in", password="Password123!", role=UserRole.SCRUTINY_OFFICER, is_staff=True)
    api_client.force_authenticate(user=officer_user)
    res_officer = api_client.post(url)
    assert res_officer.status_code == status.HTTP_200_OK

    # 5. Audit Log generated
    assert AuditLog.objects.filter(entity_id=str(app.id), action=AuditAction.ELIGIBILITY_EVALUATED).exists()
