import pytest
from apps.applications.models import (
    FieldValueSource,
    FieldValueVerificationStatus,
    SOURCE_TRUST_RANK,
    ApplicationFieldValue,
    ApplicationFieldDefinition,
    Application,
    FieldDataType
)
from apps.schemes.models import Scheme, SchemeVersion
from apps.users.models import User, UserRole, ApplicantProfile
from apps.applications.form_services import DynamicFormService


@pytest.fixture
def scheme_setup(db):
    user = User.objects.create_user(
        username="trust_applicant",
        email="trust@tribal.gov.in",
        password="Password123!",
        role=UserRole.APPLICANT
    )
    profile = ApplicantProfile.objects.create(
        user=user,
        community="ST",
        annual_family_income=250000
    )
    scheme = Scheme.objects.create(code="TRUST_SCHEME", name="Trust Test Scheme")
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2026-27",
        version_number="1.0"
    )
    fdef = ApplicationFieldDefinition.objects.create(
        scheme_version=version,
        field_code="annual_family_income",
        label="Annual Family Income",
        data_type=FieldDataType.CURRENCY
    )
    app = Application.objects.create(
        applicant=profile,
        scheme_version=version,
        application_number="MOTA/TRUST/001"
    )
    return app, fdef


@pytest.mark.django_db
def test_canonical_trust_hierarchy_ordering():
    """
    Validates canonical trust order:
    OFFICER_VERIFIED (60) > OFFICIAL_INTEGRATION (50) > VERIFIED_DOCUMENT (40) >
    SYSTEM (30) > APPLICANT_DECLARED (20) > OCR_PROVISIONAL (10)
    """
    assert SOURCE_TRUST_RANK[FieldValueSource.OFFICER_VERIFIED] == 60
    assert SOURCE_TRUST_RANK[FieldValueSource.OFFICIAL_INTEGRATION] == 50
    assert SOURCE_TRUST_RANK[FieldValueSource.VERIFIED_DOCUMENT] == 40
    assert SOURCE_TRUST_RANK[FieldValueSource.SYSTEM] == 30
    assert SOURCE_TRUST_RANK[FieldValueSource.APPLICANT_DECLARED] == 20
    assert SOURCE_TRUST_RANK[FieldValueSource.OCR_PROVISIONAL] == 10

    # Strict transitivity checks
    assert SOURCE_TRUST_RANK[FieldValueSource.OFFICER_VERIFIED] > SOURCE_TRUST_RANK[FieldValueSource.OFFICIAL_INTEGRATION]
    assert SOURCE_TRUST_RANK[FieldValueSource.OFFICIAL_INTEGRATION] > SOURCE_TRUST_RANK[FieldValueSource.VERIFIED_DOCUMENT]
    assert SOURCE_TRUST_RANK[FieldValueSource.VERIFIED_DOCUMENT] > SOURCE_TRUST_RANK[FieldValueSource.SYSTEM]
    assert SOURCE_TRUST_RANK[FieldValueSource.SYSTEM] > SOURCE_TRUST_RANK[FieldValueSource.APPLICANT_DECLARED]
    assert SOURCE_TRUST_RANK[FieldValueSource.APPLICANT_DECLARED] > SOURCE_TRUST_RANK[FieldValueSource.OCR_PROVISIONAL]


@pytest.mark.django_db
def test_ocr_provisional_cannot_outrank_applicant_declaration(scheme_setup):
    """
    OCR_PROVISIONAL (rank 10) must NEVER outrank APPLICANT_DECLARED (rank 20),
    even if OCR confidence is 0.9999.
    """
    app, fdef = scheme_setup

    # 1. Applicant declares income = 300,000
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=300000,
        source=FieldValueSource.APPLICANT_DECLARED,
        confidence=1.0
    )

    # 2. OCR extracts 150,000 with very high confidence
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=150000,
        source=FieldValueSource.OCR_PROVISIONAL,
        confidence=0.9999
    )

    effective = DynamicFormService.get_effective_field_values(app)
    inc_entry = effective["annual_family_income"]

    assert inc_entry["source"] == FieldValueSource.APPLICANT_DECLARED
    assert inc_entry["value"] == 300000
    assert inc_entry["trust_rank"] == 20
    assert inc_entry["source"] != FieldValueSource.OCR_PROVISIONAL


@pytest.mark.django_db
def test_ocr_provisional_cannot_become_verified_merely_due_to_high_confidence(scheme_setup):
    """
    OCR extraction remains PROVISIONALLY_EXTRACTED regardless of confidence score.
    High confidence never automatically mutates state to DOCUMENT_VERIFIED or OFFICER_VERIFIED.
    """
    app, fdef = scheme_setup

    ocr_val = ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=200000,
        source=FieldValueSource.OCR_PROVISIONAL,
        confidence=0.9999
    )
    assert ocr_val.verification_status == FieldValueVerificationStatus.PROVISIONALLY_EXTRACTED
    assert ocr_val.verification_status != FieldValueVerificationStatus.DOCUMENT_VERIFIED
    assert ocr_val.verification_status != FieldValueVerificationStatus.OFFICER_VERIFIED


@pytest.mark.django_db
def test_verified_document_can_outrank_applicant_only_through_explicit_verification(scheme_setup):
    """
    VERIFIED_DOCUMENT (rank 40) outranks APPLICANT_DECLARED (rank 20) only when
    explicitly stamped with VERIFIED_DOCUMENT and DOCUMENT_VERIFIED status.
    """
    app, fdef = scheme_setup

    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=400000,
        source=FieldValueSource.APPLICANT_DECLARED
    )

    effective_before = DynamicFormService.get_effective_field_values(app)
    assert effective_before["annual_family_income"]["source"] == FieldValueSource.APPLICANT_DECLARED

    # Explicit document verification
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=350000,
        source=FieldValueSource.VERIFIED_DOCUMENT
    )

    effective_after = DynamicFormService.get_effective_field_values(app)
    assert effective_after["annual_family_income"]["source"] == FieldValueSource.VERIFIED_DOCUMENT
    assert effective_after["annual_family_income"]["value"] == 350000
    assert effective_after["annual_family_income"]["trust_rank"] == 40


@pytest.mark.django_db
def test_officer_verified_is_highest_human_trust_state(scheme_setup):
    """
    OFFICER_VERIFIED (rank 60) outranks all other sources, including official integrations.
    """
    app, fdef = scheme_setup

    for src, val in [
        (FieldValueSource.OCR_PROVISIONAL, 100000),
        (FieldValueSource.APPLICANT_DECLARED, 200000),
        (FieldValueSource.SYSTEM, 250000),
        (FieldValueSource.VERIFIED_DOCUMENT, 300000),
        (FieldValueSource.OFFICIAL_INTEGRATION, 350000),
        (FieldValueSource.OFFICER_VERIFIED, 380000),
    ]:
        ApplicationFieldValue.objects.create(
            application=app,
            field_definition=fdef,
            value_json=val,
            source=src
        )

    effective = DynamicFormService.get_effective_field_values(app)
    assert effective["annual_family_income"]["source"] == FieldValueSource.OFFICER_VERIFIED
    assert effective["annual_family_income"]["value"] == 380000
    assert effective["annual_family_income"]["trust_rank"] == 60


@pytest.mark.django_db
def test_official_integration_evidence_distinguishable_from_applicant_declared(scheme_setup):
    """
    OFFICIAL_INTEGRATION (e.g. DigiLocker) must be cleanly distinguishable from
    applicant declaration both in source enum and in trust rank (50 vs 20).
    """
    app, fdef = scheme_setup

    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=500000,
        source=FieldValueSource.APPLICANT_DECLARED
    )
    ApplicationFieldValue.objects.create(
        application=app,
        field_definition=fdef,
        value_json=480000,
        source=FieldValueSource.OFFICIAL_INTEGRATION
    )

    effective = DynamicFormService.get_effective_field_values(app)
    assert effective["annual_family_income"]["source"] == FieldValueSource.OFFICIAL_INTEGRATION
    assert effective["annual_family_income"]["trust_rank"] == 50
    assert effective["annual_family_income"]["value"] == 480000
