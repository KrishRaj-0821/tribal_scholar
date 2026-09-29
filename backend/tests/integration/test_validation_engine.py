import pytest
from apps.schemes.models import (
    Scheme, SchemeType, SchemeVersion, SchemeVersionStatus,
    SchemeRule, RuleType, RuleOperator, RuleSeverity, RuleStatus,
    ReferenceSet, ReferenceSetItem
)
from apps.documents.models import SourceDocument, SourceType
from apps.workflow.models import WorkflowDefinition
from apps.core.services import validate_scheme_version_integrity

@pytest.fixture
def base_doc(db):
    return SourceDocument.objects.create(
        title="Official Verification Guideline",
        source_type=SourceType.GUIDELINE,
        academic_year="2025-26",
        checksum="1" * 64,
        content_hash="2" * 64
    )

@pytest.fixture
def base_scheme(db):
    return Scheme.objects.create(
        code="VAL_SCHEME",
        name="Validation Integrity Scheme",
        scheme_type=SchemeType.SCHOLARSHIP
    )

@pytest.mark.django_db
def test_validation_fails_if_active_version_has_no_workflow(base_scheme, base_doc):
    """
    Check 3: Automated validation fails if an active SchemeVersion has no workflow.
    """
    version = SchemeVersion.objects.create(
        scheme=base_scheme,
        academic_year="2025-26",
        version_number=1,
        status=SchemeVersionStatus.ACTIVE,
        source_document=base_doc
    )
    # Add a valid active rule
    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="TEST_ACTIVE_RULE",
        field_path="applicant.community",
        operator=RuleOperator.EQUALS,
        value="ST",
        failure_message="Must be ST",
        source_document=base_doc,
        status=RuleStatus.ACTIVE
    )

    errors = validate_scheme_version_integrity(version)
    assert any("has no active WorkflowDefinition" in err for err in errors)

    # Adding an active workflow resolves this error
    wf = WorkflowDefinition.objects.create(scheme_version=version, name="Active Workflow", active=True)
    errors_after = validate_scheme_version_integrity(version)
    assert not any("has no active WorkflowDefinition" in err for err in errors_after)


@pytest.mark.django_db
def test_validation_fails_if_active_version_has_unpublished_rules(base_scheme, base_doc):
    """
    Check 4: Automated validation fails if an active SchemeVersion contains unpublished/unknown rules
    (such as PENDING_OFFICIAL_SOURCE_EXTRACTION or DRAFT).
    """
    version = SchemeVersion.objects.create(
        scheme=base_scheme,
        academic_year="2025-26",
        version_number=1,
        status=SchemeVersionStatus.ACTIVE,
        source_document=base_doc
    )
    WorkflowDefinition.objects.create(scheme_version=version, name="Active Workflow", active=True)

    # Create a rule pending official source extraction inside an ACTIVE version
    SchemeRule.objects.create(
        scheme_version=version,
        rule_code="TEST_PENDING_RULE",
        field_path="application.course_subject",
        operator=RuleOperator.PENDING_OFFICIAL_EXTRACTION,
        value=None,
        failure_message="Criteria not yet extracted from Gazette.",
        source_document=base_doc,
        status=RuleStatus.PENDING_OFFICIAL_SOURCE_EXTRACTION
    )

    errors = validate_scheme_version_integrity(version)
    assert any("contains unpublished/unknown rule" in err for err in errors)


@pytest.mark.django_db
def test_validation_fails_if_reference_set_item_lacks_provenance(base_scheme, base_doc):
    """
    Check 5: Automated validation fails if a ReferenceSet item used by an active rule has no provenance.
    """
    version = SchemeVersion.objects.create(
        scheme=base_scheme,
        academic_year="2025-26",
        version_number=1,
        status=SchemeVersionStatus.ACTIVE,
        source_document=base_doc
    )
    WorkflowDefinition.objects.create(scheme_version=version, name="Active Workflow", active=True)

    ref_set = ReferenceSet.objects.create(
        code="UNVERIFIED_SET",
        name="Unverified Reference Set"
    )
    # Create item with empty/null source_document bypass
    # Since DB model has null=False, let's test if an item is corrupted or points to unlinked source
    doc_orphan = SourceDocument.objects.create(
        title="Temp Doc",
        source_type=SourceType.DATASET,
        academic_year="2025-26",
        checksum="9" * 64,
        content_hash="9" * 64
    )
    item = ReferenceSetItem.objects.create(
        reference_set=ref_set,
        external_code="COL-01",
        name="Test College",
        source_document=doc_orphan
    )

    rule = SchemeRule.objects.create(
        scheme_version=version,
        rule_code="TEST_REF_SET_RULE",
        field_path="application.college_code",
        operator=RuleOperator.IN_SET,
        reference_set=ref_set,
        failure_message="College not recognized",
        source_document=base_doc,
        status=RuleStatus.ACTIVE
    )

    # Valid when doc is present
    assert len(validate_scheme_version_integrity(version)) == 0

    # Set source_document_id to None via raw update to simulate corruption
    ReferenceSetItem.objects.filter(id=item.id).update(source_document_id=None)
    errors = validate_scheme_version_integrity(version)
    assert any("has no source_document provenance" in err for err in errors)
