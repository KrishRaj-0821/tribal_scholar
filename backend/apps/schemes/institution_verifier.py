import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from django.db import models
from apps.schemes.models import (
    Scheme, SchemeVersion, InstitutionEligibility, EligibilityStatus,
    ReferenceSet, ReferenceSetItem, DatasetStatus
)

logger = logging.getLogger(__name__)

class InstitutionVerificationStatus(str, Enum):
    VERIFIED_ELIGIBLE = "VERIFIED_ELIGIBLE"
    VERIFIED_INELIGIBLE = "VERIFIED_INELIGIBLE"
    UNKNOWN = "UNKNOWN"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class InstitutionEligibilityVerifier:
    """
    Abstract contract for institutional qualification and course-specific verification.
    """
    def verify(
        self,
        institution: str,
        scheme: Scheme,
        scheme_version: SchemeVersion,
        course: Optional[str] = None,
        academic_year: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError("InstitutionEligibilityVerifier subclasses must implement verify().")


class MockInstitutionEligibilityVerifier(InstitutionEligibilityVerifier):
    """
    SIH Reference implementation for institution qualification.
    Ensures safe evaluation against authoritative reference sets and Course-Specific Institution Eligibility.
    
    Safety Invariants:
    1. Never invent eligibility.
    2. If a reference source is incomplete (SAMPLE, PARTIAL, or unverified COMPLETE):
       Returns UNKNOWN or PENDING_VERIFICATION (which resolves to NEEDS_REVIEW, never INELIGIBLE).
    3. Returns VERIFIED_INELIGIBLE only when an authoritative, verified source explicitly disallows the institution/course.
    """
    def verify(
        self,
        institution: str,
        scheme: Scheme,
        scheme_version: SchemeVersion,
        course: Optional[str] = None,
        academic_year: Optional[str] = None,
    ) -> Dict[str, Any]:
        academic_year = academic_year or scheme_version.academic_year
        institution_str = str(institution or "").strip()
        course_str = str(course or "").strip()

        if not institution_str:
            return {
                "institution": institution_str,
                "course": course_str,
                "status": InstitutionVerificationStatus.UNKNOWN.value,
                "source_references": [],
                "reason": "Missing institution identifier."
            }

        # 1. Course-Specific Institution Eligibility check
        inst_elig_qs = InstitutionEligibility.objects.filter(
            scheme_version=scheme_version,
            academic_year=academic_year
        ).filter(
            models.Q(institute_code__iexact=institution_str) | models.Q(institute_name__iexact=institution_str)
        )

        mapping = inst_elig_qs.first()
        if mapping:
            # Check course if specified
            if course_str and mapping.course_code and mapping.course_code != '*':
                course_match = mapping.course_code.upper() == course_str.upper()
                if not course_match:
                    # Specific course not verified under this mapping
                    return {
                        "institution": institution_str,
                        "course": course_str,
                        "status": InstitutionVerificationStatus.PENDING_VERIFICATION.value,
                        "source_references": [str(mapping.source_document.id)] if mapping.source_document else [],
                        "reason": f"Institution '{institution_str}' has approved course '{mapping.course_code}', but applicant course '{course_str}' is not yet verified."
                    }

            if mapping.eligibility_status == EligibilityStatus.INELIGIBLE:
                return {
                    "institution": institution_str,
                    "course": course_str,
                    "status": InstitutionVerificationStatus.VERIFIED_INELIGIBLE.value,
                    "source_references": [str(mapping.source_document.id)] if mapping.source_document else [],
                    "reason": f"Institution '{institution_str}' is officially notified as INELIGIBLE for course '{course_str}'."
                }
            elif mapping.eligibility_status == EligibilityStatus.ELIGIBLE:
                return {
                    "institution": institution_str,
                    "course": course_str,
                    "status": InstitutionVerificationStatus.VERIFIED_ELIGIBLE.value,
                    "source_references": [str(mapping.source_document.id)] if mapping.source_document else [],
                    "reason": f"Institution '{institution_str}' and course '{course_str or 'ANY'}' are officially verified under {scheme_version.scheme.code}."
                }
            else:
                return {
                    "institution": institution_str,
                    "course": course_str,
                    "status": InstitutionVerificationStatus.PENDING_VERIFICATION.value,
                    "source_references": [str(mapping.source_document.id)] if mapping.source_document else [],
                    "reason": f"Institution '{institution_str}' is conditional / subject to special verification."
                }

        # 2. Check ReferenceSets attached to rules in this scheme_version
        inst_rules = scheme_version.rules.filter(
            reference_set__isnull=False
        ).select_related('reference_set', 'source_document')

        for r in inst_rules:
            ref_set = r.reference_set
            item_match = ref_set.items.filter(
                models.Q(external_code__iexact=institution_str) | models.Q(name__iexact=institution_str)
            ).first()

            if item_match:
                return {
                    "institution": institution_str,
                    "course": course_str,
                    "status": InstitutionVerificationStatus.VERIFIED_ELIGIBLE.value,
                    "source_references": [str(item_match.source_document_id or ref_set.source_document_id or "")],
                    "reason": f"Institution '{institution_str}' matched empanelled roster '{ref_set.name}'."
                }
            else:
                # Not matched in this reference set
                if ref_set.dataset_status == DatasetStatus.VERIFIED or (
                    ref_set.dataset_status == DatasetStatus.COMPLETE
                    and ref_set.record_count_loaded == ref_set.record_count_expected
                    and ref_set.record_count_expected > 0
                ):
                    return {
                        "institution": institution_str,
                        "course": course_str,
                        "status": InstitutionVerificationStatus.VERIFIED_INELIGIBLE.value,
                        "source_references": [str(ref_set.source_document_id or "")],
                        "reason": f"Institution '{institution_str}' is absent from authoritative verified master roster '{ref_set.name}'."
                    }
                else:
                    return {
                        "institution": institution_str,
                        "course": course_str,
                        "status": InstitutionVerificationStatus.PENDING_VERIFICATION.value,
                        "source_references": [str(ref_set.source_document_id or "")],
                        "reason": f"Reference dataset '{ref_set.name}' is incomplete ({ref_set.record_count_loaded}/{ref_set.record_count_expected} records loaded). Eligibility cannot be conclusively determined."
                    }

        # Default fallback: unknown institution
        return {
            "institution": institution_str,
            "course": course_str,
            "status": InstitutionVerificationStatus.UNKNOWN.value,
            "source_references": [],
            "reason": f"Institution '{institution_str}' has no matching official empanelment record."
        }
