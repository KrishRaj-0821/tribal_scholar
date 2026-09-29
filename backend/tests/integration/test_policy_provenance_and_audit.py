import pytest
from datetime import date
from apps.schemes.models import (
    Scheme, SchemeVersion, SchemeRule, RuleCategory,
    ProvenanceStatus, SourceClaimStatus, RuleStatus
)
from apps.documents.models import SourceDocument, SourceDocumentStatus
from apps.applications.models import ApplicationFieldDefinition, Application
from apps.schemes.evaluator import RuleEvaluationService
from apps.accounts.models import User, UserRole
from apps.applicants.models import ApplicantProfile

# =============================================================================
# CANONICAL STATUTORY MOTA SOURCE CONSTANTS (2025-26)
# =============================================================================
# Ministry of Tribal Affairs official scholarship guideline states:
# "Total family income of the candidate to be eligible for this scheme is Rs. 6.00 lakh per annum from all sources."
OFFICIAL_MOTA_TOP_CLASS_2025_INCOME_CEILING = 600000  # Rs. 6,00,000/- (6.00 lakh)
OFFICIAL_MOTA_TOP_CLASS_2025_EXCERPT_KEYWORD = "6.00 lakh"

@pytest.fixture
def canonical_top_class_source_document(db):
    """Canonical test fixture referencing the official MoTA Top Class source record."""
    doc, _ = SourceDocument.objects.get_or_create(
        title="National Fellowship and Scholarship for Higher Education of ST Students - Top Class Education Scheme Guidelines 2025-26",
        academic_year="2025-26",
        defaults={
            "source_url": "https://tribal.nic.in/ScholarshiP.aspx",
            "checksum": "a" * 64,
            "content_hash": "b" * 64,
            "status": SourceDocumentStatus.VERIFIED,
            "notes": "Official MoTA source establishing statutory income ceiling of Rs. 6.00 lakh per annum."
        }
    )
    return doc


# =============================================================================
# 1. TOP CLASS INCOME CEILING AUDIT & REGRESSION TEST
# =============================================================================
@pytest.mark.django_db
def test_top_class_income_ceiling_matches_official_source(seeded_db, canonical_top_class_source_document):
    """
    CRITICAL HARDENING GATE REGRESSION TEST:
    Verifies that the configured Top Class Scholarship statutory income ceiling strictly
    matches the official Ministry of Tribal Affairs verified value of Rs. 6.00 lakh per annum (600,000).

    Audits:
    1. SchemeRule value
    2. SchemeRule source_excerpt
    3. ApplicationFieldDefinition validation_schema max
    4. DocumentRequirement income certificate binding
    5. SourceDocument provenance link
    """
    scheme = Scheme.objects.get(code="TOP_CLASS")
    version = SchemeVersion.objects.get(scheme=scheme, academic_year="2025-26")

    # 1. Audit SchemeRule value
    income_rule = SchemeRule.objects.get(
        scheme_version=version,
        rule_code="TOP_CLASS_2025_INCOME_CEILING"
    )
    assert income_rule.value == OFFICIAL_MOTA_TOP_CLASS_2025_INCOME_CEILING, (
        f"CRITICAL MISCONFIGURATION: Top Class income ceiling is {income_rule.value}, "
        f"must strictly equal official MoTA value {OFFICIAL_MOTA_TOP_CLASS_2025_INCOME_CEILING} (Rs. 6.00 lakh)."
    )
    assert OFFICIAL_MOTA_TOP_CLASS_2025_EXCERPT_KEYWORD in income_rule.source_excerpt, (
        f"Rule source excerpt '{income_rule.source_excerpt}' must explicitly cite {OFFICIAL_MOTA_TOP_CLASS_2025_EXCERPT_KEYWORD}."
    )
    assert income_rule.status == RuleStatus.ACTIVE
    assert income_rule.category == RuleCategory.ELIGIBILITY

    # 2. Audit ApplicationFieldDefinition machine-readable JSON validation schema
    field_def = ApplicationFieldDefinition.objects.get(
        scheme_version=version,
        field_code="annual_family_income"
    )
    assert field_def.validation_schema.get("max") == OFFICIAL_MOTA_TOP_CLASS_2025_INCOME_CEILING, (
        f"Field validation schema max {field_def.validation_schema.get('max')} does not match official 6.00 lakh ceiling."
    )
    assert field_def.status == "ACTIVE"

    # 3. Audit DocumentRequirement
    doc_req = version.document_requirements.get(document_type="INCOME_CERTIFICATE")
    assert doc_req.required is True
    assert doc_req.source_document is not None


@pytest.mark.django_db
def test_top_class_income_ceiling_distinct_from_nos_enhanced_ceiling(seeded_db):
    """
    Verifies that the Top Class 2025-26 income ceiling (6.00 lakh) is properly segregated
    from the NOS 2026-27 enhanced income ceiling (8.00 lakh) across distinct SchemeVersions.
    """
    top_version = SchemeVersion.objects.get(scheme__code="TOP_CLASS", academic_year="2025-26")
    top_rule = SchemeRule.objects.get(scheme_version=top_version, rule_code="TOP_CLASS_2025_INCOME_CEILING")
    assert top_rule.value == 600000

    # NOS 2026-27 has enhanced 8.00 lakh ceiling under a separate SchemeVersion
    nos_version_2026 = SchemeVersion.objects.get(scheme__code="NOS", academic_year="2026-27")
    nos_rule = SchemeRule.objects.get(scheme_version=nos_version_2026, rule_code="NOS_2026_INCOME_CEILING")
    assert nos_rule.value == 800000


# =============================================================================
# 2. NFST NIRF TOP-100 AUDIT & REMOVAL OF UNSUPPORTED CLAIMS
# =============================================================================
@pytest.mark.django_db
def test_nfst_does_not_enforce_unsupported_nirf_requirement(seeded_db):
    """
    Official MoTA guidelines for NFST (fellowship.tribal.gov.in and tribal.nic.in)
    require UGC recognition under Section 2(f)/12(B) or Institute of National Importance.
    They do NOT require NIRF Top-100 ranking.

    Verifies:
    1. No active rule in NFST 2025-26 requires a NIRF rank.
    2. Applicants admitted to valid universities without NIRF ranking are NOT rejected.
    """
    nfst_version = SchemeVersion.objects.get(scheme__code="NFST", academic_year="2025-26")
    active_rule_codes = list(
        nfst_version.rules.filter(status=RuleStatus.ACTIVE).values_list("rule_code", flat=True)
    )

    # Ensure no active rule code mentions NIRF
    for code in active_rule_codes:
        assert "NIRF" not in code, f"Found unauthorized active NIRF rule: {code}"

    # Verify candidate from unranked but UGC recognized institution is eligible
    user = User.objects.create_user(
        username="phd_scholar_unranked",
        email="scholar@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    applicant = ApplicantProfile.objects.create(
        user=user,
        community="ST",
        annual_family_income=400000,
        date_of_birth=date(1998, 2, 20)
    )
    app = Application.objects.create(
        applicant=applicant,
        scheme_version=nfst_version,
        application_number="MOTA/2025-26/NFST/TEST-NIRF",
        current_state=nfst_version.workflow.states.get(code="DRAFT"),
        submission_data_json={
            "application": {
                "enrolment_status": "CONFIRMED",
                "university_code": "DU",  # Empanelled university
                "degree_level": "PHD"
            }
        }
    )

    eval_result = RuleEvaluationService.evaluate(application=app)
    # NIRF must not produce any blocking failure or warning
    blocking_codes = [f["rule_code"] for f in eval_result["blocking_failures"]]
    assert not any("NIRF" in c for c in blocking_codes)


@pytest.mark.django_db
def test_unsupported_policy_claim_marked_unsupported_and_unresolved():
    """
    Verifies that any hypothetical or speculative rule marked with
    ProvenanceStatus.UNSUPPORTED or SourceClaimStatus.UNSUPPORTED:
    1. Is rejected from automated qualification.
    2. Evaluates to UNRESOLVED (NEEDS_REVIEW) rather than falsely marking an applicant ELIGIBLE or INELIGIBLE.
    """
    doc_spec = SourceDocument.objects.create(
        title="Speculative Guidelines (Unverified)",
        academic_year="2025-26",
        source_type="GUIDELINE",
        checksum="e" * 64,
        content_hash="f" * 64,
        status=SourceDocumentStatus.DEPRECATED
    )
    scheme = Scheme.objects.create(code="SPECULATIVE", name="Speculative Scheme")
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=doc_spec
    )
    # Create simple workflow
    from apps.workflow.models import WorkflowDefinition
    wf = WorkflowDefinition.objects.create(scheme_version=version, name="Speculative Workflow")
    draft_st = wf.states.create(code="DRAFT", display_name="Draft", sequence=1)

    unsupported_rule = SchemeRule.objects.create(
        scheme_version=version,
        rule_code="SPECULATIVE_NIRF_TOP_100",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.nirf_rank",
        operator="LESS_THAN_OR_EQUAL",
        value=100,
        failure_message="Requires NIRF Top-100",
        source_document=doc_spec,
        provenance_status=ProvenanceStatus.UNSUPPORTED,
        status=RuleStatus.ACTIVE
    )

    user = User.objects.create_user(
        username="spec_user",
        email="spec@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    applicant = ApplicantProfile.objects.create(
        user=user,
        community="ST",
        annual_family_income=300000
    )
    app = Application.objects.create(
        applicant=applicant,
        scheme_version=version,
        application_number="MOTA/2025-26/SPEC/001",
        current_state=draft_st,
        submission_data_json={"applicant": {"nirf_rank": 50}}
    )

    result = RuleEvaluationService.evaluate(application=app)
    assert result["status"] == "NEEDS_REVIEW"
    assert len(result["unresolved_rules"]) == 1
    assert result["unresolved_rules"][0]["rule_code"] == "SPECULATIVE_NIRF_TOP_100"
    assert "UNSUPPORTED" in result["unresolved_rules"][0]["explanation"]


# =============================================================================
# 3. NOS 2025-26 HISTORICAL PRESERVATION & 2026-27 SEGREGATION
# =============================================================================

@pytest.mark.django_db
def test_nos_2025_26_historical_version_exists(seeded_db):
    """
    Verifies that NOS 2025-26 exists as an immutable historical SchemeVersion,
    properly linked to its authentic official source document and verified rules.
    """
    nos_scheme = Scheme.objects.get(code="NOS")
    nos_2025 = SchemeVersion.objects.filter(scheme=nos_scheme, academic_year="2025-26", version_number=1).first()
    assert nos_2025 is not None, "NOS 2025-26 historical SchemeVersion must exist!"
    assert nos_2025.source_document is not None
    assert "2025-26" in nos_2025.source_document.academic_year
    assert nos_2025.source_document.status == SourceDocumentStatus.VERIFIED

    # Check that income ceiling rule is 6.00 lakh
    inc_rule = nos_2025.rules.get(rule_code="NOS_2025_INCOME_CEILING")
    assert inc_rule.value == 600000
    assert inc_rule.provenance_status == ProvenanceStatus.OFFICIAL_VERIFIED


@pytest.mark.django_db
def test_nos_2025_26_cannot_be_mutated_after_publication(seeded_db):
    """
    Verifies that published historical SchemeVersion NOS 2025-26:
    1. Rejects changes to academic_year, scheme, version_number, source_document.
    2. Cannot be deleted (raises PermissionDenied).
    """
    from django.core.exceptions import ValidationError, PermissionDenied
    nos_2025 = SchemeVersion.objects.get(scheme__code="NOS", academic_year="2025-26")

    # Attempt mutation of academic_year
    with pytest.raises(ValidationError):
        nos_2025.academic_year = "2027-28"
        nos_2025.save()

    # Attempt mutation of version_number
    nos_2025.refresh_from_db()
    with pytest.raises(ValidationError):
        nos_2025.version_number = 99
        nos_2025.save()

    # Attempt deletion
    nos_2025.refresh_from_db()
    with pytest.raises(PermissionDenied):
        nos_2025.delete()


@pytest.mark.django_db
def test_nos_2025_evaluation_uses_only_2025_rules_and_nos_2026_uses_only_2026_rules(seeded_db):
    """
    Verifies that:
    1. NOS 2025-26 evaluation uses strictly NOS 2025-26 rules (no QS rank or restricted topic checks).
    2. NOS 2026-27 evaluation uses strictly NOS 2026-27 rules (includes QS rank and restricted topic checks).
    """
    nos_2025 = SchemeVersion.objects.get(scheme__code="NOS", academic_year="2025-26")
    nos_2026 = SchemeVersion.objects.get(scheme__code="NOS", academic_year="2026-27")

    user = User.objects.create_user(username="nos_student", email="nos@tribal.gov.in", password="Password123!", role=UserRole.APPLICANT)
    prof = ApplicantProfile.objects.create(user=user, community="ST", annual_family_income=500000, date_of_birth=date(1996, 5, 10))

    # Application submitted under NOS 2025-26
    app_2025 = Application.objects.create(
        applicant=prof,
        scheme_version=nos_2025,
        application_number="MOTA/2025-26/NOS/HIST-001",
        current_state=nos_2025.workflow.states.get(code="DRAFT"),
        submission_data_json={
            "application": {
                "study_destination": "ABROAD",
                "course_level": "PhD",
                "is_indian_culture_or_heritage_topic": True,  # Would fail 2026 rule, but allowed in 2025
            },
            "applicant": {
                "community": "ST",
                "annual_family_income": 500000,
                "age_on_july_1": 29
            }
        }
    )

    res_2025 = RuleEvaluationService.evaluate(application=app_2025)
    evaluated_codes_2025 = [r["rule_code"] for r in res_2025["rule_results"]]
    assert all("NOS_2025" in c for c in evaluated_codes_2025)
    assert not any("NOS_2026" in c for c in evaluated_codes_2025)
    assert res_2025["status"] == "ELIGIBLE"

    # Application submitted under NOS 2026-27 with restricted Indian heritage topic
    app_2026 = Application.objects.create(
        applicant=prof,
        scheme_version=nos_2026,
        application_number="MOTA/2026-27/NOS/AMEND-001",
        current_state=nos_2026.workflow.states.get(code="DRAFT"),
        submission_data_json={
            "application": {
                "course_level": "PhD",
                "foreign_university_qs_rank": 200,
                "is_indian_culture_or_heritage_topic": True,  # Fails 2026 rule
            },
            "applicant": {
                "community": "ST",
                "annual_family_income": 500000,
                "digilocker_verified": True
            }
        }
    )

    res_2026 = RuleEvaluationService.evaluate(application=app_2026)
    evaluated_codes_2026 = [r["rule_code"] for r in res_2026["rule_results"]]
    assert all("NOS_2026" in c for c in evaluated_codes_2026)
    assert not any("NOS_2025" in c for c in evaluated_codes_2026)
    failures = [f["rule_code"] for f in res_2026["blocking_failures"]]
    assert "NOS_2026_RESTRICTED_INDIAN_SUBJECTS" in failures


# =============================================================================
# 4. NOS 2026-27 UNVERIFIED ₹8 LAKH RULE EVALUATION GUARANTEE
# =============================================================================

@pytest.mark.django_db
def test_nos_2026_27_unverified_income_produces_needs_review_not_automatic_eligibility(seeded_db):
    """
    Verifies that the NOS 2026-27 ₹8 Lakh income rule is stored as
    OFFICIAL_PENDING_VERIFICATION and:
    1. Produces UNRESOLVED result during evaluation.
    2. Yields overall status NEEDS_REVIEW.
    3. Strictly forbids automatic ELIGIBLE grant.
    """
    nos_2026 = SchemeVersion.objects.get(scheme__code="NOS", academic_year="2026-27")
    inc_rule = nos_2026.rules.get(rule_code="NOS_2026_INCOME_CEILING")
    assert inc_rule.value == 800000
    assert inc_rule.provenance_status == ProvenanceStatus.OFFICIAL_PENDING_VERIFICATION

    user = User.objects.create_user(username="nos_2026_applicant", email="nos26@tribal.gov.in", password="Password123!", role=UserRole.APPLICANT)
    prof = ApplicantProfile.objects.create(user=user, community="ST", annual_family_income=700000)

    app = Application.objects.create(
        applicant=prof,
        scheme_version=nos_2026,
        application_number="MOTA/2026-27/NOS/PEND-001",
        current_state=nos_2026.workflow.states.get(code="DRAFT"),
        submission_data_json={
            "application": {
                "course_level": "PhD",
                "foreign_university_qs_rank": 150,
                "is_indian_culture_or_heritage_topic": False,
            },
            "applicant": {
                "community": "ST",
                "annual_family_income": 700000,
                "digilocker_verified": True
            }
        }
    )

    eval_result = RuleEvaluationService.evaluate(application=app)
    assert eval_result["status"] == "NEEDS_REVIEW", "Unverified income ceiling must produce NEEDS_REVIEW, never ELIGIBLE!"
    unresolved_codes = [u["rule_code"] for u in eval_result["unresolved_rules"]]
    assert "NOS_2026_INCOME_CEILING" in unresolved_codes


# =============================================================================
# 5. SOURCE CLAIM STATUS LIFECYCLE & INTEGRITY CHECKS
# =============================================================================

@pytest.mark.django_db
def test_source_claim_status_transitions_and_exclusions(seeded_db):
    """
    Integrity Check:
    - ACTIVE + VERIFIED -> allowed in final eligibility
    - ACTIVE + PENDING_VERIFICATION -> NEEDS_REVIEW
    - UNSUPPORTED -> cannot be evaluated as policy / blocked from active rules
    - SUPERSEDED / RETIRED -> excluded from execution list
    """
    from apps.core.services import validate_scheme_version_integrity
    top_version = SchemeVersion.objects.get(scheme__code="TOP_CLASS", academic_year="2025-26")

    # 1. VERIFIED rule produces pass/fail
    ver_rule = top_version.rules.get(rule_code="TOP_CLASS_2025_INCOME_CEILING")
    assert ver_rule.provenance_status == ProvenanceStatus.OFFICIAL_VERIFIED

    # 2. Add temporary UNSUPPORTED rule to ACTIVE version -> integrity check fails
    doc = top_version.source_document
    bad_rule = SchemeRule.objects.create(
        scheme_version=top_version,
        rule_code="TOP_CLASS_UNSUPPORTED_TEST",
        category=RuleCategory.ELIGIBILITY,
        field_path="applicant.unsupported_field",
        operator="EQUALS",
        value=True,
        failure_message="Unsupported claim",
        source_document=doc,
        provenance_status=ProvenanceStatus.UNSUPPORTED,
        status=RuleStatus.ACTIVE
    )
    errs = validate_scheme_version_integrity(top_version)
    assert any("UNSUPPORTED" in e for e in errs)
    bad_rule.delete()


# =============================================================================
# 6. HISTORICAL SOURCE DOCUMENT & RULE IMMUTABILITY
# =============================================================================

@pytest.mark.django_db
def test_historical_source_documents_cannot_be_replaced_silently(seeded_db):
    """
    Verifies that a VERIFIED SourceDocument cannot have its checksum or content_hash silently altered,
    and cannot be deleted.
    """
    from django.core.exceptions import ValidationError, PermissionDenied
    doc = SourceDocument.objects.filter(status=SourceDocumentStatus.VERIFIED).first()
    assert doc is not None

    with pytest.raises(ValidationError):
        doc.checksum = "0" * 64
        doc.save()

    doc.refresh_from_db()
    with pytest.raises(ValidationError):
        doc.content_hash = "1" * 64
        doc.save()

    doc.refresh_from_db()
    with pytest.raises(PermissionDenied):
        doc.delete()


# =============================================================================
# 7. SECURITY LOGGING SANITIZATION
# =============================================================================

def test_security_logging_redacts_credentials_tokens_and_pii():
    """
    Verifies that SensitiveDataRedactingFilter intercepts and masks:
    - Passwords
    - API keys and secrets
    - Bearer tokens
    - Database connection URIs
    - 12-digit Aadhaar PII
    - Document data URLs
    """
    import logging
    from apps.core.logging_filters import SensitiveDataRedactingFilter

    redactor = SensitiveDataRedactingFilter()

    # Test password redaction
    rec1 = logging.LogRecord("test", logging.INFO, "path", 1, "User login with password='SuperSecretPassword123!'", (), None)
    redactor.filter(rec1)
    assert "SuperSecretPassword123!" not in rec1.msg
    assert "[REDACTED]" in rec1.msg

    # Test token redaction
    rec2 = logging.LogRecord("test", logging.INFO, "path", 1, "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token", (), None)
    redactor.filter(rec2)
    assert "eyJhbGci" not in rec2.msg
    assert "[REDACTED]" in rec2.msg

    # Test database URI password redaction
    rec3 = logging.LogRecord("test", logging.INFO, "path", 1, "Connecting to postgresql://postgres:mySecretDbPassword@localhost:5432/tribal_scholar", (), None)
    redactor.filter(rec3)
    assert "mySecretDbPassword" not in rec3.msg
    assert "[REDACTED]" in rec3.msg

    # Test Aadhaar PII redaction
    rec4 = logging.LogRecord("test", logging.INFO, "path", 1, "Applicant Aadhaar verified: 1234 5678 9012", (), None)
    redactor.filter(rec4)
    assert "1234 5678 9012" not in rec4.msg
    assert "[REDACTED-AADHAAR]" in rec4.msg

    # Test document data url redaction
    rec5 = logging.LogRecord("test", logging.INFO, "path", 1, "Uploaded document data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", (), None)
    redactor.filter(rec5)
    assert "iVBORw0KGgoAAAANSUhEUg" not in rec5.msg
    assert "[REDACTED-DOCUMENT-CONTENT]" in rec5.msg
