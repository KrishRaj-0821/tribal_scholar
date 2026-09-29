import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from apps.schemes.models import (
    Scheme, SchemeType, SchemeVersion, SchemeRule,
    RuleType, RuleOperator, RuleSeverity, RuleStatus,
    ReferenceSet, ReferenceSetItem
)
from apps.documents.models import SourceDocument, SourceType

@pytest.mark.django_db
def test_rules_always_reference_a_source_document():
    """
    Test 3: Rules must always reference a valid SourceDocument.
    Attempts to create a SchemeRule without source_document must fail.
    """
    scheme = Scheme.objects.create(
        code="PROVENANCE_TEST",
        name="Provenance Test Scheme",
        description="Testing strict source provenance",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    doc = SourceDocument.objects.create(
        title="Official Source Test",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="1" * 64,
        content_hash="2" * 64
    )
    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=doc
    )

    # Creating a rule with a valid source_document succeeds
    valid_rule = SchemeRule.objects.create(
        scheme_version=version,
        rule_code="TEST_VALID_RULE",
        rule_type=RuleType.ELIGIBILITY,
        field_path="applicant.community",
        operator=RuleOperator.EQUALS,
        value="ST",
        failure_message="Must be ST",
        severity=RuleSeverity.BLOCKING,
        source_document=doc,
        status=RuleStatus.ACTIVE
    )
    assert valid_rule.source_document == doc

    # Creating a rule without a source_document violates clean() validation
    invalid_rule = SchemeRule(
        scheme_version=version,
        rule_code="TEST_INVALID_ORPHAN_RULE",
        rule_type=RuleType.ELIGIBILITY,
        field_path="applicant.community",
        operator=RuleOperator.EQUALS,
        value="ST",
        failure_message="Missing provenance",
        severity=RuleSeverity.BLOCKING,
        source_document=None
    )
    with pytest.raises(ValidationError, match="Every SchemeRule must be linked to a verified source_document"):
        invalid_rule.clean()


@pytest.mark.django_db
def test_rule_references_versioned_reference_set_with_provenance():
    """
    Test 6: A rule can reference a versioned reference set, and reference set items
    must maintain their own verified source document provenance.
    """
    scheme = Scheme.objects.create(
        code="REFSET_TEST",
        name="Reference Set Test Scheme",
        description="Testing reference sets with provenance",
        scheme_type=SchemeType.SCHOLARSHIP
    )
    doc_scheme = SourceDocument.objects.create(
        title="Scheme Guideline 2025-26",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="a" * 64,
        content_hash="b" * 64
    )
    doc_annexure = SourceDocument.objects.create(
        title="Annexure of Premier Institutions 2025-26",
        source_type=SourceType.INSTITUTE_LIST,
        academic_year="2025-26",
        checksum="c" * 64,
        content_hash="d" * 64
    )

    version = SchemeVersion.objects.create(
        scheme=scheme,
        academic_year="2025-26",
        version_number=1,
        source_document=doc_scheme
    )

    ref_set = ReferenceSet.objects.create(
        code="PREMIER_INSTITUTES_2025",
        name="Premier Institutions 2025",
        description="Empanelled premier colleges"
    )

    item1 = ReferenceSetItem.objects.create(
        reference_set=ref_set,
        external_code="IIT-B",
        name="IIT Bombay",
        metadata_json={"state": "Maharashtra"},
        source_document=doc_annexure
    )

    # Reference set item without source document violates clean() validation
    orphan_item = ReferenceSetItem(
        reference_set=ref_set,
        external_code="ORPHAN_INST",
        name="Unverified College",
        source_document=None
    )
    with pytest.raises(ValidationError, match="ReferenceSetItem must maintain source document provenance"):
        orphan_item.clean()

    # Rule linking to the reference set
    rule = SchemeRule.objects.create(
        scheme_version=version,
        rule_code="TEST_IN_SET_RULE",
        rule_type=RuleType.ELIGIBILITY,
        field_path="application.institute_code",
        operator=RuleOperator.IN_SET,
        reference_set=ref_set,
        failure_message="Institute not in approved premier list.",
        severity=RuleSeverity.BLOCKING,
        source_document=doc_scheme
    )

    assert rule.reference_set.items.count() == 1
    assert rule.reference_set.items.first().source_document.id == doc_annexure.id
