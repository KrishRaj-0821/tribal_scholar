import pytest
from django.core.exceptions import ValidationError
from apps.schemes.models import (
    Scheme, SchemeType, SchemeVersion, SchemeVersionStatus,
    SchemeRule, RuleCategory, RuleOperator, RuleSeverity, RuleStatus,
    ReferenceSet, ReferenceSetItem, DatasetStatus,
    SchemeQuota, SelectionMethod, InstitutionEligibility, EligibilityStatus
)
from apps.documents.models import SourceDocument, SourceType
from apps.schemes.evaluator import RuleEvaluationService


@pytest.mark.django_db
def test_1_2025_26_and_2026_27_rules_coexist(seeded_db):
    """
    Test 1: Proves that 2025-26 and 2026-27 rules coexist simultaneously in the database
    under the same scheme without collision.
    """
    nos_scheme = Scheme.objects.get(code="NOS")

    v2025 = SchemeVersion.objects.filter(scheme=nos_scheme, academic_year="2025-26").first()
    v2026 = SchemeVersion.objects.filter(scheme=nos_scheme, academic_year="2026-27").first()

    assert v2025 is not None, "NOS 2025-26 must exist"
    assert v2026 is not None, "NOS 2026-27 must exist"
    assert v2025.id != v2026.id

    rules_2025 = list(v2025.rules.values_list('rule_code', flat=True))
    rules_2026 = list(v2026.rules.values_list('rule_code', flat=True))

    # 2025-26 has its specific rules
    assert "NOS_2025_COMMUNITY" in rules_2025
    assert "NOS_2025_STUDY_ABROAD" in rules_2025
    assert "NOS_2025_AGE_LIMIT" in rules_2025

    # 2026-27 has its amended rules
    assert "NOS_2026_QS_TOP_1000" in rules_2026
    assert "NOS_2026_RESTRICTED_INDIAN_SUBJECTS" in rules_2026
    assert "NOS_2026_EXCLUDE_BACHELORS" in rules_2026

    # Verify querying rules by version returns distinct rules without collision
    assert len(rules_2025) > 0
    assert len(rules_2026) > 0


@pytest.mark.django_db
def test_2_publishing_2026_27_does_not_mutate_2025_26(seeded_db):
    """
    Test 2: Proves that publishing or modifying 2026-27 does not mutate or alter
    historical 2025-26 rules or configurations.
    """
    nos_scheme = Scheme.objects.get(code="NOS")

    v2025 = SchemeVersion.objects.get(scheme=nos_scheme, academic_year="2025-26")
    v2026 = SchemeVersion.objects.get(scheme=nos_scheme, academic_year="2026-27")

    initial_2025_rules = list(v2025.rules.values('rule_code', 'value', 'operator', 'category'))
    initial_2025_rule_count = v2025.rules.count()

    # Simulate an update / publication to 2026-27 version
    v2026.status = SchemeVersionStatus.ACTIVE
    v2026.save()

    # Add a mock amended rule to 2026-27 to simulate ongoing policy changes
    doc_2026 = v2026.source_document
    SchemeRule.objects.create(
        scheme_version=v2026,
        rule_code="NOS_2026_NEW_TEST_AMENDMENT",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.custom_check",
        operator=RuleOperator.EQUALS,
        value="PASSED",
        failure_message="Test amendment failed",
        source_document=doc_2026,
        source_excerpt="Official Gazette test amendment",
        status=RuleStatus.ACTIVE
    )

    # Refresh 2025-26 from DB
    v2025.refresh_from_db()
    current_2025_rules = list(v2025.rules.values('rule_code', 'value', 'operator', 'category'))

    # Verify 2025-26 was completely unmutated
    assert v2025.rules.count() == initial_2025_rule_count
    assert current_2025_rules == initial_2025_rules
    assert not v2025.rules.filter(rule_code="NOS_2026_NEW_TEST_AMENDMENT").exists()


@pytest.mark.django_db
def test_3_quota_cannot_be_evaluated_as_applicant_eligibility(seeded_db):
    """
    Test 3: Proves that a quota (slot capacity) cannot be evaluated as an applicant
    eligibility rule. Quota operates during selection/allocation, NOT initial eligibility.
    """
    nfst_scheme = Scheme.objects.get(code="NFST")
    v2025 = SchemeVersion.objects.get(scheme=nfst_scheme, academic_year="2025-26")

    # 1. Verify there is NO eligibility rule checking slot_quota <= 750
    eligibility_rules = v2025.rules.filter(category=RuleCategory.ELIGIBILITY)
    slot_rules = eligibility_rules.filter(field_path__contains="slot_quota")
    assert not slot_rules.exists(), "Quota must not exist in applicant eligibility rules!"

    # 2. Verify that total_capacity is stored in SchemeQuota
    quota = SchemeQuota.objects.filter(scheme_version=v2025, quota_code="NFST_2025_ANNUAL_SLOTS").first()
    assert quota is not None
    assert quota.total_capacity == 750
    assert quota.source_document is not None

    # 3. Verify an applicant without slot_quota evaluates cleanly through RuleEvaluationService
    applicant_dossier = {
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
    result = RuleEvaluationService.evaluate(
        application_id="TEST-APP-001",
        scheme_version=v2025,
        applicant_data=applicant_dossier
    )
    # The evaluation passes without needing slot_quota
    assert result["eligibility_status"] == "ELIGIBLE"
    assert len(result["blocking_failures"]) == 0


@pytest.mark.django_db
def test_4_preference_rule_cannot_cause_direct_eligibility_failure(seeded_db):
    """
    Test 4: Proves that a preference rule (e.g. PVTG, Divyangjan) cannot cause
    an otherwise eligible applicant to become ineligible.
    """
    nfst_scheme = Scheme.objects.get(code="NFST")
    v2025 = SchemeVersion.objects.get(scheme=nfst_scheme, academic_year="2025-26")

    # Verify preference rules exist with category PREFERENCE
    pref_rules = v2025.rules.filter(category=RuleCategory.PREFERENCE)
    assert pref_rules.count() >= 2

    # Applicant who is ST and qualifies, but is NEITHER PVTG NOR Divyangjan
    non_pvtg_applicant = {
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
    result = RuleEvaluationService.evaluate("APP-NON-PVTG", v2025, non_pvtg_applicant)
    assert result["eligibility_status"] == "ELIGIBLE"
    assert len(result["blocking_failures"]) == 0

    # Applicant who IS PVTG qualifies for the statutory priority in matched_rules
    pvtg_applicant = dict(non_pvtg_applicant)
    pvtg_applicant["applicant"] = dict(non_pvtg_applicant["applicant"])
    pvtg_applicant["applicant"]["is_pvtg"] = True

    pvtg_result = RuleEvaluationService.evaluate("APP-PVTG", v2025, pvtg_applicant)
    assert pvtg_result["eligibility_status"] == "ELIGIBLE"
    pvtg_matched = [r for r in pvtg_result["matched_rules"] if r.get("rule_code") == "NFST_2025_PREFERENCE_PVTG"]
    assert len(pvtg_matched) == 1
    assert pvtg_matched[0]["priority_applied"] is True


@pytest.mark.django_db
def test_5_selection_method_cannot_create_eligibility_result(seeded_db):
    """
    Test 5: Proves that SelectionMethod (e.g., Interview Committee) is separated
    from deterministic eligibility evaluation.
    """
    nos_scheme = Scheme.objects.get(code="NOS")
    v2025 = SchemeVersion.objects.get(scheme=nos_scheme, academic_year="2025-26")

    # Verify SelectionMethod exists with human_decision_required = True
    selection_method = SelectionMethod.objects.filter(scheme_version=v2025, code="EXPERT_COMMITTEE_INTERVIEW").first()
    assert selection_method is not None
    assert selection_method.human_decision_required is True

    # Verify that NOS_2025_EXPERT_COMMITTEE_MERIT is NOT an eligibility rule in SchemeRule
    assert not v2025.rules.filter(rule_code="NOS_2025_EXPERT_COMMITTEE_MERIT").exists()
    assert not v2025.rules.filter(category=RuleCategory.ELIGIBILITY, field_path__contains="interview").exists()

    # The deterministic eligibility evaluator runs without requiring interview marks
    applicant_data = {
        "applicant": {
            "community": "ST",
            "annual_family_income": 500000,
            "age_on_july_1": 28
        },
        "application": {
            "study_destination": "ABROAD",
            "course_level": "PhD"
        }
    }
    eval_result = RuleEvaluationService.evaluate("APP-NOS-PRE-INTERVIEW", v2025, applicant_data)
    assert eval_result["eligibility_status"] == "ELIGIBLE"
    assert len(eval_result["blocking_failures"]) == 0


@pytest.mark.django_db
def test_6_incomplete_reference_sets_cannot_be_marked_complete():
    """
    Test 6: Proves that the system refuses to mark a reference set as COMPLETE
    if record_count_loaded != record_count_expected.
    """
    doc = SourceDocument.objects.create(
        title="Test Source",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="a" * 64,
        content_hash="b" * 64
    )

    ref_set = ReferenceSet.objects.create(
        code="TEST_INCOMPLETE_SET",
        name="Test Incomplete Reference Set",
        dataset_status=DatasetStatus.PARTIAL,
        record_count_expected=265,
        record_count_loaded=7,
        source_document=doc
    )

    # Adding only 1 item so actual count = 1 != 265
    ReferenceSetItem.objects.create(
        reference_set=ref_set,
        external_code="INST-01",
        name="Test College",
        source_document=doc
    )

    # Attempting to mark as COMPLETE when actual_count (1) != record_count_expected (265)
    ref_set.dataset_status = DatasetStatus.COMPLETE

    with pytest.raises(ValidationError, match=r"Cannot mark ReferenceSet 'TEST_INCOMPLETE_SET' as COMPLETE: loaded count"):
        ref_set.clean()


@pytest.mark.django_db
def test_7_institution_eligibility_can_be_course_specific(seeded_db):
    """
    Test 7: Proves that Top Class institution eligibility is course-aware,
    evaluating (institution + course), not institution alone.
    """
    tc_scheme = Scheme.objects.get(code="TOP_CLASS")
    v2025 = SchemeVersion.objects.get(scheme=tc_scheme, academic_year="2025-26")
    ref_set = ReferenceSet.objects.get(code="TOP_CLASS_PREMIER_INSTITUTES_SAMPLE")
    iit_bombay = ref_set.items.get(external_code="IIT-BOM")

    # In our seed data, IIT-BOM has B.Tech as ELIGIBLE
    eligible_mapping = InstitutionEligibility.objects.get(
        scheme_version=v2025,
        institution=iit_bombay,
        course_name="B.Tech"
    )
    assert eligible_mapping.eligibility_status == EligibilityStatus.ELIGIBLE

    # Create an INELIGIBLE course for IIT-BOM (e.g. Non-approved diploma)
    InstitutionEligibility.objects.create(
        scheme_version=v2025,
        institution=iit_bombay,
        course_name="Unapproved Diploma",
        eligibility_status=EligibilityStatus.INELIGIBLE,
        source_document=eligible_mapping.source_document
    )

    base_dossier = {
        "applicant": {
            "community": "ST",
            "annual_family_income": 450000
        },
        "application": {
            "institute_code": "IIT-BOM"
        },
        "documents": {
            "income_certificate": True
        }
    }

    # Scenario A: Applying for approved B.Tech program
    dossier_approved = dict(base_dossier)
    dossier_approved["application"] = dict(base_dossier["application"])
    dossier_approved["application"]["course_name"] = "B.Tech"

    res_approved = RuleEvaluationService.evaluate("APP-IITB-BTECH", v2025, dossier_approved)
    assert res_approved["eligibility_status"] == "ELIGIBLE"
    assert len(res_approved["blocking_failures"]) == 0

    # Scenario B: Applying for unapproved program at the exact same institution
    dossier_unapproved = dict(base_dossier)
    dossier_unapproved["application"] = dict(base_dossier["application"])
    dossier_unapproved["application"]["course_name"] = "Unapproved Diploma"

    res_unapproved = RuleEvaluationService.evaluate("APP-IITB-DIPLOMA", v2025, dossier_unapproved)
    assert res_unapproved["eligibility_status"] == "INELIGIBLE"
    assert any("not an eligible program at Indian Institute of Technology Bombay" in fail["detail"] for fail in res_unapproved["blocking_failures"])


@pytest.mark.django_db
def test_8_unproven_rule_returns_needs_review(seeded_db):
    """
    Test 8: Proves that an unproven rule (lacking provenance or pending extraction)
    returns NEEDS_REVIEW and NEVER silently passes.
    """
    nfst_scheme = Scheme.objects.get(code="NFST")
    v2025 = SchemeVersion.objects.get(scheme=nfst_scheme, academic_year="2025-26")
    doc = v2025.source_document

    # Create a rule pending official extraction
    pending_rule = SchemeRule.objects.create(
        scheme_version=v2025,
        rule_code="TEST_UNPROVEN_CRITERIA",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.unproven_metric",
        operator=RuleOperator.PENDING_OFFICIAL_EXTRACTION,
        value=None,
        failure_message="Official criteria not yet gazetted.",
        severity=RuleSeverity.BLOCKING,
        source_document=doc,
        status=RuleStatus.PENDING_OFFICIAL_SOURCE_EXTRACTION
    )

    applicant_data = {
        "applicant": {
            "community": "ST",
            "is_pvtg": False,
            "is_disabled": False,
            "unproven_metric": "SOMETHING"
        },
        "application": {
            "course_level": "PhD",
            "institute_code": "JNU-ND"
        }
    }

    result = RuleEvaluationService.evaluate("APP-UNPROVEN", v2025, applicant_data)

    # Must return NEEDS_REVIEW, never ELIGIBLE!
    assert result["eligibility_status"] == "NEEDS_REVIEW"
    assert len(result["unresolved_rules"]) > 0
    assert any(unres["rule_code"] == "TEST_UNPROVEN_CRITERIA" for unres in result["unresolved_rules"])

    # Clean up test rule
    pending_rule.delete()


@pytest.mark.django_db
def test_9_every_active_rule_has_official_provenance(seeded_db):
    """
    Test 9: Proves that every active SchemeRule across all seeded schemes
    has verified source document provenance, an authentic excerpt, and OFFICIAL confidence.
    """
    active_rules = SchemeRule.objects.filter(status=RuleStatus.ACTIVE)
    assert active_rules.count() >= 15, "Expected active rules to be seeded"

    for rule in active_rules:
        assert rule.source_document is not None, f"Rule {rule.rule_code} missing source_document"
        assert len(rule.source_excerpt.strip()) > 0, f"Rule {rule.rule_code} missing source_excerpt"
        assert rule.confidence == "OFFICIAL", f"Rule {rule.rule_code} must have OFFICIAL confidence"
        assert rule.category in [c[0] for c in RuleCategory.choices]


@pytest.mark.django_db
def test_10_nos_2026_27_changed_rules_point_to_amendment_source(seeded_db):
    """
    Test 10: Proves that NOS 2026-27 changed rules point directly to the official
    MoTA amendment and instruction manual source document.
    """
    nos_scheme = Scheme.objects.get(code="NOS")
    v2026 = SchemeVersion.objects.get(scheme=nos_scheme, academic_year="2026-27")

    culture_rule = v2026.rules.get(rule_code="NOS_2026_RESTRICTED_INDIAN_SUBJECTS")
    qs_rule = v2026.rules.get(rule_code="NOS_2026_QS_TOP_1000")
    bachelor_rule = v2026.rules.get(rule_code="NOS_2026_EXCLUDE_BACHELORS")
    digilocker_rule = v2026.rules.get(rule_code="NOS_2026_DIGILOCKER_VERIFICATION")

    # Check amendment source document
    assert "Amendment in eligibility criteria and courses covered under the NOS Scheme for ST Students from 2026-27" in culture_rule.source_document.title
    assert "Indian Culture" in culture_rule.source_excerpt
    assert "1,000" in qs_rule.source_excerpt or "1000" in qs_rule.source_excerpt
    assert "Bachelor" in bachelor_rule.failure_message or "Bachelor" in bachelor_rule.source_excerpt
    assert digilocker_rule.category == RuleCategory.WORKFLOW


@pytest.mark.django_db
def test_11_sample_data_cannot_be_mistaken_for_complete_official_master_data(seeded_db):
    """
    Test 11: Proves that sample reference sets (e.g. TOP_CLASS_PREMIER_INSTITUTES_SAMPLE)
    are marked with status SAMPLE or PARTIAL and explicitly report record counts and coverage.
    """
    ref_set = ReferenceSet.objects.get(code="TOP_CLASS_PREMIER_INSTITUTES_SAMPLE")

    assert ref_set.dataset_status in (DatasetStatus.SAMPLE, DatasetStatus.PARTIAL)
    assert ref_set.record_count_expected == 265
    assert ref_set.record_count_loaded < 265
    assert ref_set.coverage_percentage < 100.0

    # Verify that trying to force COMPLETE fails validation
    ref_set.dataset_status = DatasetStatus.COMPLETE
    with pytest.raises(ValidationError):
        ref_set.clean()
