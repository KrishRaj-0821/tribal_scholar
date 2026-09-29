from typing import List
from django.core.exceptions import ValidationError

class SchemeConfigurationValidationError(ValidationError):
    """Raised when a SchemeVersion or its associated rules violate statutory integrity constraints."""
    pass


def validate_scheme_version_integrity(scheme_version) -> List[str]:
    """
    Automated statutory validation checking:
    1. A SchemeRule has no source_document
    2. A SchemeVersion has no academic_year
    3. An active SchemeVersion has no workflow
    4. An active SchemeVersion has unpublished/unknown rules
    5. A ReferenceSet item used by an active rule has no provenance
    """
    from apps.schemes.models import SchemeVersionStatus, RuleStatus, RuleOperator

    errors = []

    # Check 1: SchemeVersion academic_year
    if not scheme_version.academic_year:
        errors.append(f"SchemeVersion {scheme_version.id} has no academic_year.")

    # Check 2: SchemeVersion source_document provenance
    if not scheme_version.source_document_id:
        errors.append(f"SchemeVersion {scheme_version.id} ({scheme_version.scheme.code}) has no authorizing source_document.")

    # Rules evaluation
    rules = list(scheme_version.rules.all())

    # Check 3: Any rule has no source document
    for rule in rules:
        if not rule.source_document_id:
            errors.append(
                f"SchemeRule '{rule.rule_code}' (ID {rule.id}) in SchemeVersion {scheme_version.id} has no source_document provenance."
            )

    # If the SchemeVersion is ACTIVE, apply strict operational checks
    if scheme_version.status == SchemeVersionStatus.ACTIVE:
        # Check 4: Active SchemeVersion has an active workflow definition
        try:
            workflow = getattr(scheme_version, 'workflow', None)
            if not workflow or not workflow.active:
                errors.append(
                    f"Active SchemeVersion {scheme_version.id} ({scheme_version.scheme.code} {scheme_version.academic_year}) has no active WorkflowDefinition."
                )
        except Exception:
            errors.append(f"Active SchemeVersion {scheme_version.id} has no associated WorkflowDefinition.")

        # Check 5: Active SchemeVersion has unpublished/unknown rules (e.g. PENDING_OFFICIAL_SOURCE_EXTRACTION or DRAFT)
        if not rules:
            errors.append(f"Active SchemeVersion {scheme_version.id} has no configured rules.")

        for rule in rules:
            if rule.status in (RuleStatus.PENDING_OFFICIAL_SOURCE_EXTRACTION, RuleStatus.DRAFT) or rule.operator == RuleOperator.PENDING_OFFICIAL_EXTRACTION:
                errors.append(
                    f"Active SchemeVersion {scheme_version.id} contains unpublished/unknown rule '{rule.rule_code}' with status '{rule.status}' / operator '{rule.operator}'. Active versions cannot contain pending rules."
                )

            # Check 6: ReferenceSet items used by an active rule must maintain provenance
            if rule.reference_set:
                items = rule.reference_set.items.all()
                for item in items:
                    if not item.source_document_id:
                        errors.append(
                            f"ReferenceSetItem '{item.name}' ({item.external_code}) in ReferenceSet '{rule.reference_set.code}' used by active rule '{rule.rule_code}' has no source_document provenance."
                        )

            # Check 7: Active rules must not be marked UNSUPPORTED
            from apps.schemes.models import ProvenanceStatus
            prov_status = getattr(rule, 'provenance_status', None)
            if prov_status in ('UNSUPPORTED', ProvenanceStatus.UNSUPPORTED):
                errors.append(
                    f"Active SchemeVersion {scheme_version.id} contains rule '{rule.rule_code}' marked UNSUPPORTED. "
                    "Unsupported policy claims cannot be configured as active policy rules."
                )

    return errors


def validate_all_schemes():
    """
    Validates all SchemeVersions in the system, raising SchemeConfigurationValidationError
    if any critical violation is encountered.
    """
    from apps.schemes.models import SchemeVersion

    all_errors = []
    for version in SchemeVersion.objects.all():
        errs = validate_scheme_version_integrity(version)
        if errs:
            all_errors.extend(errs)

    if all_errors:
        raise SchemeConfigurationValidationError(all_errors)
    return True
