import pytest
from datetime import date
from apps.schemes.models import (
    Scheme, SchemeType, SchemeVersion, SchemeVersionStatus,
    SchemeRule, RuleType, RuleOperator, RuleSeverity, RuleStatus
)
from apps.documents.models import SourceDocument, SourceType

@pytest.mark.django_db
def test_multiple_academic_year_versions_coexist():
    """
    Test 1: Multiple academic-year scheme versions can coexist without collision.
    """
    scheme = Scheme.objects.create(
        code="TOP_CLASS_TEST",
        name="Top Class Education Scheme (Test)",
        description="Testing multi-version coexistence",
        scheme_type=SchemeType.SCHOLARSHIP
    )

    doc_2024 = SourceDocument.objects.create(
        title="Top Class Guidelines 2024-25",
        source_type=SourceType.GUIDELINE,
        academic_year="2024-25",
        checksum="a" * 64,
        content_hash="b" * 64
    )
    doc_2025 = SourceDocument.objects.create(
        title="Top Class Guidelines 2025-26",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="c" * 64,
        content_hash="d" * 64
    )
    doc_2026 = SourceDocument.objects.create(
        title="Top Class Guidelines 2026-27",
        source_type=SourceType.GUIDELINE,
        academic_year="2026-27",
        checksum="e" * 64,
        content_hash="f" * 64
    )

    # Create versions across three academic years
    v2024 = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2024-25",
        version_number=1,
        status=SchemeVersionStatus.ARCHIVED,
        source_document=doc_2024
    )
    v2025 = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        status=SchemeVersionStatus.ACTIVE,
        source_document=doc_2025
    )
    v2026 = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2026-27",
        version_number=1,
        status=SchemeVersionStatus.DRAFT,
        source_document=doc_2026
    )

    all_versions = scheme.versions.all()
    assert all_versions.count() == 3
    academic_years = [v.academic_year for v in all_versions]
    assert "2024-25" in academic_years
    assert "2025-26" in academic_years
    assert "2026-27" in academic_years


@pytest.mark.django_db
def test_old_scheme_version_remains_unchanged_after_new_version_creation():
    """
    Test 2: Old scheme version and its rules remain completely unchanged
    when a new academic year version is introduced with modified rules.
    """
    scheme = Scheme.objects.create(
        code="NFST_COEXISTENCE",
        name="NFST Coexistence Test",
        description="Testing immutability of historical versions",
        scheme_type=SchemeType.FELLOWSHIP
    )

    doc_old = SourceDocument.objects.create(
        title="NFST Guidelines 2024-25",
        source_type=SourceType.GUIDELINE,
        academic_year="2024-25",
        checksum="1" * 64,
        content_hash="2" * 64
    )

    # Create 2024-25 version with 500 slots
    v_old = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2024-25",
        version_number=1,
        status=SchemeVersionStatus.ACTIVE,
        source_document=doc_old
    )
    rule_old_slots = SchemeRule.objects.create(
        scheme_version=v_old,
        rule_code="NFST_2024_SLOTS",
        rule_type=RuleType.QUOTA,
        field_path="application.slot_quota",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=500,
        failure_message="Maximum 500 fellowship slots for 2024-25.",
        severity=RuleSeverity.BLOCKING,
        source_document=doc_old,
        status=RuleStatus.ACTIVE
    )

    # Now create 2025-26 version with 750 slots
    doc_new = SourceDocument.objects.create(
        title="NFST Advertisement 2025-26",
        source_type=SourceType.ADVERTISEMENT,
        academic_year="2025-26",
        checksum="3" * 64,
        content_hash="4" * 64
    )
    v_new = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        status=SchemeVersionStatus.ACTIVE,
        source_document=doc_new
    )
    rule_new_slots = SchemeRule.objects.create(
        scheme_version=v_new,
        rule_code="NFST_2025_SLOTS",
        rule_type=RuleType.QUOTA,
        field_path="application.slot_quota",
        operator=RuleOperator.LESS_THAN_OR_EQUAL,
        value=750,
        failure_message="Maximum 750 fellowship slots for 2025-26.",
        severity=RuleSeverity.BLOCKING,
        source_document=doc_new,
        status=RuleStatus.ACTIVE
    )

    # Verify that the historical 2024-25 version and rule remain pristine
    v_old.refresh_from_db()
    rule_old_slots.refresh_from_db()

    assert v_old.academic_year == "2024-25"
    assert v_old.source_document.id == doc_old.id
    assert rule_old_slots.value == 500
    assert rule_old_slots.rule_code == "NFST_2024_SLOTS"

    # Verify that the new 2025-26 version has the updated parameter
    assert v_new.academic_year == "2025-26"
    assert rule_new_slots.value == 750
    assert rule_new_slots.source_document.id == doc_new.id
