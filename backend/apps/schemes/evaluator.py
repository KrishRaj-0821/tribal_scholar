import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple, Union

from django.core.exceptions import ValidationError

from apps.audit.models import AuditLog, AuditAction
from apps.schemes.models import (
    SchemeRule, SchemeVersion, RuleCategory, RuleOperator,
    RuleSeverity, RuleStatus, ProvenanceStatus,
    ReferenceSet, DatasetStatus, InstitutionEligibility, EligibilityStatus
)
from apps.schemes.data_quality import DataQualityValidator


def get_nested_field(data: Dict[str, Any], path: str) -> Any:
    """Extract nested value from a dictionary using dot notation (e.g. applicant.community)."""
    if not isinstance(data, dict):
        return None
    parts = path.split('.')
    curr = data
    for part in parts:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        else:
            return None
    return curr


def compute_result_hash(result_dict: Dict[str, Any]) -> str:
    """
    Computes a deterministic SHA-256 hash of the canonical evaluation result.
    Excludes non-deterministic timestamps to guarantee idempotency.
    """
    hashable = {
        "status": result_dict.get("status"),
        "scheme_version": result_dict.get("scheme_version"),
        "rule_results": [
            {
                "rule_id": r.get("rule_id"),
                "result": r.get("result"),
                "observed_value": str(r.get("observed_value")),
                "operator": r.get("operator")
            }
            for r in result_dict.get("rule_results", [])
        ],
        "blocking_failures": result_dict.get("blocking_failures", []),
        "warnings": result_dict.get("warnings", []),
        "unresolved_rules": result_dict.get("unresolved_rules", []),
        "data_quality_issues": result_dict.get("data_quality_issues", [])
    }
    canonical_json = json.dumps(hashable, sort_keys=True, default=str)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


class RuleEvaluationService:
    """
    Deterministic Rule Evaluation Engine.
    
    Principles:
    1. Zero hidden AI: Evaluation is 100% deterministic and rule-driven.
    2. Three-state logic: Every rule yields PASS, FAIL, or UNRESOLVED.
    3. Category isolation: Executes strictly ELIGIBILITY, DOCUMENT, and VALIDATION rules.
    4. Reference safety: Incomplete reference datasets (SAMPLE/PARTIAL) NEVER cause INELIGIBLE.
    5. Course-awareness: Institution eligibility evaluates (institution + course + academic_year).
    6. Strict Provenance: Unverified rules yield UNRESOLVED / NEEDS_REVIEW.
    7. Idempotency & Audit: Canonical result hashing and append-only audit trail.
    """

    ENGINE_VERSION = "2.0.0"

    @classmethod
    def evaluate(
        cls,
        *args,
        application=None,
        applicant=None,
        scheme_version: Optional[SchemeVersion] = None,
        documents=None,
        structured_fields: Optional[Dict[str, Any]] = None,
        application_id: Optional[str] = None,
        applicant_data: Optional[Dict[str, Any]] = None,
        actor=None,
        record_evaluation: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Flexible entry point supporting positional and keyword invocation:
        - evaluate(application_id, scheme_version, applicant_data)
        - evaluate(application=app, actor=user)
        - evaluate(application=app, scheme_version=sv, applicant_data=data)
        """
        # Handle legacy positional arguments: (application_id, scheme_version, applicant_data)
        if len(args) >= 1:
            first_arg = args[0]
            if hasattr(first_arg, 'submission_data_json'):
                application = first_arg
            else:
                application_id = str(first_arg)
        if len(args) >= 2:
            scheme_version = args[1]
        if len(args) >= 3:
            applicant_data = args[2]

        # Resolve application instance if passed or lookup
        resolved_app = None
        if application is not None and hasattr(application, 'submission_data_json'):
            resolved_app = application
            if application_id is None:
                application_id = str(resolved_app.id)
            if scheme_version is None:
                scheme_version = resolved_app.scheme_version
        elif application_id:
            try:
                from apps.applications.models import Application
                resolved_app = Application.objects.filter(id=application_id).first()
                if resolved_app and scheme_version is None:
                    scheme_version = resolved_app.scheme_version
            except Exception:
                resolved_app = None

        if scheme_version is None:
            raise ValueError("A valid SchemeVersion must be provided for eligibility evaluation.")

        # Build composite dossier
        dossier: Dict[str, Any] = {}
        if resolved_app and resolved_app.submission_data_json:
            dossier.update(resolved_app.submission_data_json)

        # Merge effective field values using the deterministic field trust hierarchy
        if resolved_app and hasattr(resolved_app, 'get_effective_field_values'):
            effective_map = resolved_app.get_effective_field_values()
            dossier.setdefault('application', {})
            for code, field_meta in effective_map.items():
                val = field_meta.get('value')
                dossier['application'][code] = val
                dossier[code] = val

        # Merge demographic applicant profile if available
        if resolved_app and hasattr(resolved_app, 'applicant') and resolved_app.applicant:
            app_prof = resolved_app.applicant
            dossier.setdefault('applicant', {})
            dossier['applicant'].setdefault('community', app_prof.community)
            dossier['applicant'].setdefault('annual_family_income', float(app_prof.annual_family_income))
            dossier['applicant'].setdefault('is_pvtg', app_prof.community == 'PVTG')
            dossier['applicant'].setdefault('is_disabled', app_prof.is_disabled)
            if app_prof.date_of_birth:
                dossier['applicant'].setdefault('date_of_birth', str(app_prof.date_of_birth))

        # Merge explicit applicant_data or structured_fields passed
        if applicant_data:
            for k, v in applicant_data.items():
                if isinstance(v, dict) and isinstance(dossier.get(k), dict):
                    dossier[k].update(v)
                else:
                    dossier[k] = v

        if structured_fields:
            for k, v in structured_fields.items():
                if isinstance(v, dict) and isinstance(dossier.get(k), dict):
                    dossier[k].update(v)
                else:
                    dossier[k] = v

        if documents and isinstance(documents, dict):
            dossier.setdefault('documents', {})
            dossier['documents'].update(documents)

        # ---------------------------------------------------------------------
        # 1. FIELD VALIDATION & DATA QUALITY LAYER
        # ---------------------------------------------------------------------
        data_quality_issues = DataQualityValidator.validate(dossier, scheme_version=scheme_version)

        # ---------------------------------------------------------------------
        # 2. RETRIEVE ISOLATED RULES (ELIGIBILITY, DOCUMENT, VALIDATION ONLY)
        # Exclude SUPERSEDED, RETIRED, DRAFT, and SUSPENDED rules
        # ---------------------------------------------------------------------
        all_rules = list(
            scheme_version.rules
            .select_related('source_document', 'reference_set')
            .order_by('category', 'rule_code')
        )

        # Part 1 Canonical DocumentRequirement Enforcement:
        # If DocumentRequirement records exist for this scheme version, duplicate DOCUMENT SchemeRules
        # must be marked SUPERSEDED, preserving audit history and preventing execution.
        if scheme_version.document_requirements.exists():
            for r in all_rules:
                if r.category == RuleCategory.DOCUMENT and r.status != RuleStatus.SUPERSEDED:
                    r.status = RuleStatus.SUPERSEDED
                    r.superseded_reason = "DocumentRequirement is the canonical source for document requirements."
                    r.save(update_fields=['status', 'superseded_reason'])

        allowed_categories = (
            RuleCategory.ELIGIBILITY,
            RuleCategory.DOCUMENT,
            RuleCategory.VALIDATION
        )
        executable_rules = [
            r for r in all_rules 
            if r.category in allowed_categories and r.status not in (RuleStatus.SUPERSEDED, RuleStatus.RETIRED)
        ]

        now_iso = datetime.now(timezone.utc).isoformat()
        result: Dict[str, Any] = {
            "status": "ELIGIBLE",
            "eligibility_status": "ELIGIBLE",
            "application_id": str(application_id or ""),
            "scheme_version": str(scheme_version.id),
            "scheme_code": scheme_version.scheme.code,
            "academic_year": scheme_version.academic_year,
            "rule_version": f"{scheme_version.academic_year}-v{scheme_version.version_number}",
            "evaluated_at": now_iso,
            "engine_version": cls.ENGINE_VERSION,
            "rule_results": [],
            "blocking_failures": [],
            "warnings": [],
            "matched_rules": [],
            "unresolved_rules": [],
            "data_quality_issues": data_quality_issues,
            "source_references": []
        }

        # If blocking data quality issues prevent safe evaluation, note them
        has_blocking_data_quality = any(issue.get('blocking', False) for issue in data_quality_issues)

        # Check for unresolved field conflicts affecting this application (Part 3)
        conflict_map = {}
        if resolved_app:
            try:
                from apps.applications.models import ConflictStatus
                for conf in resolved_app.conflicts.filter(status__in=[ConflictStatus.OPEN, ConflictStatus.UNDER_REVIEW]):
                    conflict_map[conf.field_code] = conf
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 3. THREE-STATE RULE EVALUATION (PASS / FAIL / UNRESOLVED)
        # ---------------------------------------------------------------------
        for rule in executable_rules:
            # Build Source Reference entry
            src_ref = {
                "rule_id": rule.rule_code,
                "category": rule.category,
                "source_document_id": str(rule.source_document.id) if rule.source_document else None,
                "source_document": rule.source_document.title if rule.source_document else None,
                "source_url": rule.source_document.source_url if rule.source_document else "",
                "source_excerpt": rule.source_excerpt,
                "provenance_status": getattr(rule, 'provenance_status', ProvenanceStatus.OFFICIAL_VERIFIED),
                "academic_year": scheme_version.academic_year
            }
            if rule.source_document:
                result["source_references"].append(src_ref)

            # Check Provenance Status: Unverified rules MUST return UNRESOLVED
            prov_status = getattr(rule, 'provenance_status', ProvenanceStatus.OFFICIAL_VERIFIED)
            if (
                not rule.source_document or
                prov_status in (
                    ProvenanceStatus.OFFICIAL_PENDING_VERIFICATION,
                    ProvenanceStatus.UNVERIFIED,
                    ProvenanceStatus.UNSUPPORTED,
                    'UNSUPPORTED',
                    'PENDING_VERIFICATION'
                ) or
                rule.status == RuleStatus.PENDING_OFFICIAL_SOURCE_EXTRACTION or
                rule.operator == RuleOperator.PENDING_OFFICIAL_EXTRACTION
            ):
                rule_explanation = {
                    "rule_id": rule.rule_code,
                    "rule_code": rule.rule_code,
                    "result": "UNRESOLVED",
                    "field_path": rule.field_path,
                    "observed_value": None,
                    "operator": rule.operator,
                    "required_value": rule.value,
                    "explanation": (
                        f"Rule '{rule.rule_code}' is marked {prov_status} and lacks verified gazette citation. "
                        "Official provenance must be verified before automated qualification."
                    ),
                    "source": rule.source_document.title if rule.source_document else None,
                    "source_document_id": str(rule.source_document.id) if rule.source_document else None,
                    "source_url": rule.source_document.source_url if rule.source_document else "",
                    "source_excerpt": rule.source_excerpt,
                    "provenance_status": prov_status,
                    "severity": rule.severity,
                    "category": rule.category
                }
                result["rule_results"].append(rule_explanation)
                result["unresolved_rules"].append(rule_explanation)
                continue

            # Check if an unresolved conflict affects this rule (Part 3)
            matching_conflict = None
            for f_code, conf_obj in conflict_map.items():
                if f_code in rule.field_path or rule.field_path.endswith(f".{f_code}") or rule.field_path == f_code:
                    matching_conflict = conf_obj
                    break

            if matching_conflict:
                actual_val = get_nested_field(dossier, rule.field_path)
                rule_explanation = {
                    "rule_id": rule.rule_code,
                    "rule_code": rule.rule_code,
                    "result": "UNRESOLVED",
                    "field_path": rule.field_path,
                    "observed_value": actual_val,
                    "actual": actual_val,
                    "operator": rule.operator,
                    "required_value": rule.value,
                    "explanation": f"Material unresolved field conflict on '{matching_conflict.field_code}' between sources ({list(matching_conflict.source_values.keys())}). Requires officer review.",
                    "source": rule.source_document.title if rule.source_document else None,
                    "source_document_id": str(rule.source_document.id) if rule.source_document else None,
                    "source_url": rule.source_document.source_url if rule.source_document else "",
                    "source_excerpt": rule.source_excerpt,
                    "provenance_status": prov_status,
                    "severity": rule.severity,
                    "category": rule.category
                }
                result["rule_results"].append(rule_explanation)
                result["unresolved_rules"].append(rule_explanation)
                continue

            # Extract actual observed value from submitted dossier
            actual_value = get_nested_field(dossier, rule.field_path)

            # Handle missing field
            if actual_value is None and rule.operator != RuleOperator.EXISTS:
                rule_explanation = {
                    "rule_id": rule.rule_code,
                    "rule_code": rule.rule_code,
                    "result": "UNRESOLVED",
                    "field_path": rule.field_path,
                    "observed_value": None,
                    "operator": rule.operator,
                    "required_value": rule.value if rule.value is not None else (rule.reference_set.code if rule.reference_set else None),
                    "explanation": f"Required dossier field '{rule.field_path}' is missing or empty. Eligibility cannot be determined without this information.",
                    "source": rule.source_document.title if rule.source_document else None,
                    "source_document_id": str(rule.source_document.id) if rule.source_document else None,
                    "source_url": rule.source_document.source_url if rule.source_document else "",
                    "source_excerpt": rule.source_excerpt,
                    "provenance_status": prov_status,
                    "severity": rule.severity,
                    "category": rule.category
                }
                result["rule_results"].append(rule_explanation)
                result["unresolved_rules"].append(rule_explanation)
                continue

            # Evaluate the rule
            rule_state, explanation_str, extra_dq_issue = cls._evaluate_single_rule(
                rule, actual_value, dossier, scheme_version
            )

            if extra_dq_issue:
                result["data_quality_issues"].append(extra_dq_issue)

            rule_explanation = {
                "rule_id": rule.rule_code,
                "rule_code": rule.rule_code,
                "result": rule_state,  # "PASS", "FAIL", "UNRESOLVED"
                "field_path": rule.field_path,
                "observed_value": actual_value,
                "actual": actual_value,
                "operator": rule.operator,
                "required_value": rule.value if rule.value is not None else (rule.reference_set.code if rule.reference_set else None),
                "expected": rule.value if rule.value is not None else (rule.reference_set.code if rule.reference_set else None),
                "explanation": explanation_str,
                "source": rule.source_document.title if rule.source_document else None,
                "source_document": rule.source_document.title if rule.source_document else None,
                "source_document_id": str(rule.source_document.id) if rule.source_document else None,
                "source_url": rule.source_document.source_url if rule.source_document else "",
                "source_excerpt": rule.source_excerpt,
                "provenance_status": prov_status,
                "severity": rule.severity,
                "category": rule.category
            }
            result["rule_results"].append(rule_explanation)

            if rule_state == "PASS":
                result["matched_rules"].append(rule_explanation)
            elif rule_state == "FAIL":
                failure_entry = dict(rule_explanation)
                failure_entry["failure_message"] = rule.failure_message
                failure_entry["detail"] = explanation_str
                if rule.severity == RuleSeverity.BLOCKING:
                    result["blocking_failures"].append(failure_entry)
                else:
                    result["warnings"].append(failure_entry)
            elif rule_state == "UNRESOLVED":
                result["unresolved_rules"].append(rule_explanation)

        # ---------------------------------------------------------------------
        # 4. PREFERENCE RULES (INFORMATIONAL ONLY — NEVER FAIL OR DISQUALIFY)
        # ---------------------------------------------------------------------
        preference_rules = [r for r in all_rules if r.category == RuleCategory.PREFERENCE]
        for pref in preference_rules:
            pref_val = get_nested_field(dossier, pref.field_path)
            state, expl, _ = cls._evaluate_single_rule(pref, pref_val, dossier, scheme_version)
            if state == "PASS":
                result["matched_rules"].append({
                    "rule_id": pref.rule_code,
                    "rule_code": pref.rule_code,
                    "category": RuleCategory.PREFERENCE,
                    "priority_applied": True,
                    "explanation": f"Statutory preference awarded: {expl}",
                    "source": pref.source_document.title if pref.source_document else None
                })

        # ---------------------------------------------------------------------
        # 5. AGGREGATE THREE-STATE LOGIC
        # ---------------------------------------------------------------------
        if len(result["blocking_failures"]) > 0:
            final_status = "INELIGIBLE"
        elif len(result["unresolved_rules"]) > 0 or has_blocking_data_quality:
            final_status = "NEEDS_REVIEW"
        else:
            final_status = "ELIGIBLE"

        result["status"] = final_status
        result["eligibility_status"] = final_status

        # ---------------------------------------------------------------------
        # 6. IDEMPOTENCY RESULT HASH & PERSISTENCE
        # ---------------------------------------------------------------------
        res_hash = compute_result_hash(result)
        result["result_hash"] = res_hash

        if record_evaluation and resolved_app:
            try:
                from apps.applications.models import EligibilityEvaluation, EligibilityInputSnapshot
                eval_record = EligibilityEvaluation.objects.create(
                    application=resolved_app,
                    scheme_version=scheme_version,
                    engine_version=cls.ENGINE_VERSION,
                    result=result,
                    result_hash=res_hash
                )

                # Part K: Snapshot effective input values to ensure historical reproducibility
                snapshot_payload = {
                    "application_id": str(resolved_app.id),
                    "dossier": dossier,
                    "evaluated_at": now_iso,
                    "scheme_version_id": str(scheme_version.id),
                    "active_rules_evaluated": [r.rule_code for r in executable_rules],
                }
                snapshot_hash = hashlib.sha256(
                    json.dumps(snapshot_payload, sort_keys=True, default=str).encode('utf-8')
                ).hexdigest()
                EligibilityInputSnapshot.objects.create(
                    evaluation=eval_record,
                    payload_json=snapshot_payload,
                    payload_hash=snapshot_hash
                )
            except Exception:
                pass

            # Create statutory audit log
            try:
                AuditLog.objects.create(
                    actor=actor if actor and hasattr(actor, 'is_authenticated') and actor.is_authenticated else None,
                    actor_role=getattr(actor, 'role', 'SYSTEM') if actor else 'SYSTEM',
                    entity_type='Application',
                    entity_id=str(resolved_app.id),
                    action=AuditAction.ELIGIBILITY_EVALUATED,
                    after_json={
                        "status": final_status,
                        "engine_version": cls.ENGINE_VERSION,
                        "result_hash": res_hash,
                        "rules_evaluated": [r.get("rule_id") for r in result["rule_results"]],
                        "blocking_failures_count": len(result["blocking_failures"]),
                        "unresolved_rules_count": len(result["unresolved_rules"])
                    },
                    reason=f"Automated deterministic eligibility evaluation ({final_status})"
                )
            except Exception:
                pass

        return result

    @classmethod
    def _evaluate_single_rule(
        cls,
        rule: SchemeRule,
        actual: Any,
        full_dossier: Dict[str, Any],
        scheme_version: SchemeVersion
    ) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        """
        Evaluates one rule returning (status, explanation, optional_data_quality_issue).
        Status is strictly: PASS | FAIL | UNRESOLVED.
        """
        op = rule.operator
        expected = rule.value

        # -----------------------------------------------------------------
        # Document Category Rules
        # -----------------------------------------------------------------
        if rule.category == RuleCategory.DOCUMENT or (op == RuleOperator.EXISTS and "document" in rule.field_path.lower()):
            from apps.documents.models import DocumentRequirement, DocumentValidityPolicy, ApplicantDocumentType

            # Normalize doc type from field_path or rule_code
            doc_key = rule.field_path.split('.')[-1].upper()
            matched_type = None
            if "ADMISSION" in doc_key or "ENROLMENT" in doc_key:
                matched_type = ApplicantDocumentType.ADMISSION_OFFER
            elif "CASTE" in doc_key or "TRIBE" in doc_key:
                matched_type = ApplicantDocumentType.CASTE_CERTIFICATE
            elif "INCOME" in doc_key:
                matched_type = ApplicantDocumentType.INCOME_CERTIFICATE
            elif "DISABILITY" in doc_key or "UDID" in doc_key:
                matched_type = ApplicantDocumentType.DISABILITY_CERTIFICATE
            elif "PASSPORT" in doc_key:
                matched_type = ApplicantDocumentType.PASSPORT
            elif "TRANSCRIPT" in doc_key or "MARKSHEET" in doc_key:
                matched_type = ApplicantDocumentType.ACADEMIC_TRANSCRIPT
            else:
                for choice_key, _ in ApplicantDocumentType.choices:
                    if choice_key in doc_key or doc_key in choice_key or choice_key.replace('_', '') in rule.rule_code.replace('_', ''):
                        matched_type = choice_key
                        break
            if not matched_type:
                matched_type = doc_key

            doc_req = DocumentRequirement.objects.filter(
                scheme_version=scheme_version,
                document_type=matched_type
            ).first()

            # Part D Invariant: An undocumented validity policy must NOT automatically reject a document.
            # It should become: NEEDS_REVIEW (UNRESOLVED)
            if not doc_req or doc_req.validity_policy == DocumentValidityPolicy.NO_EXPIRY_RULE_CONFIGURED:
                if actual is None:
                    return "UNRESOLVED", f"Required document '{rule.field_path}' is missing.", None
                return (
                    "UNRESOLVED",
                    f"Document '{rule.field_path}' has no official validity policy configured ({getattr(doc_req, 'validity_policy', 'NONE')}). Requires officer review.",
                    None
                )

            if actual is None:
                return "UNRESOLVED", f"Required document '{rule.field_path}' is missing.", None

            # Actual can be a boolean or a dict containing metadata
            if isinstance(actual, dict):
                doc_status = actual.get('status', '').upper()
                is_verified = actual.get('is_verified', False) or actual.get('is_verified_by_officer', False)
                is_expired = doc_status == 'EXPIRED' or actual.get('is_expired', False)

                # Check validity policy
                if doc_req.validity_policy == DocumentValidityPolicy.PERMANENT:
                    # Permanent certificate (e.g. ST Caste Certificate) - ignore expiry flag
                    pass
                elif doc_req.validity_policy in (
                    DocumentValidityPolicy.EXPIRY_DATE_REQUIRED,
                    DocumentValidityPolicy.FINANCIAL_YEAR_BOUND,
                    DocumentValidityPolicy.ACADEMIC_YEAR_BOUND
                ):
                    if is_expired:
                        return "FAIL", f"Submitted certificate '{rule.field_path}' is expired under validity policy '{doc_req.validity_policy}'.", None
                elif doc_req.validity_policy == DocumentValidityPolicy.ISSUE_DATE_REQUIRED:
                    if not actual.get('issue_date'):
                        return "UNRESOLVED", f"Submitted certificate '{rule.field_path}' lacks mandatory issue date.", None

                if doc_status == 'INVALID':
                    return "UNRESOLVED", f"Submitted document '{rule.field_path}' is unreadable or flagged invalid.", None

                if doc_status == 'MISSING' or not actual:
                    return "UNRESOLVED", f"Required document '{rule.field_path}' is missing.", None

                if doc_req.verification_required:
                    if is_verified or doc_status == 'VERIFIED':
                        return "PASS", f"Document '{rule.field_path}' is present and verified under policy '{doc_req.validity_policy}'.", None
                    return "UNRESOLVED", f"Document '{rule.field_path}' is uploaded but pending officer verification.", None
                else:
                    return "PASS", f"Document '{rule.field_path}' is present.", None

            if isinstance(actual, bool):
                if actual:
                    return "PASS", f"Document requirement '{rule.field_path}' is satisfied.", None
                else:
                    return "UNRESOLVED", f"Required document '{rule.field_path}' is not yet uploaded.", None

            if actual:
                return "PASS", f"Document requirement '{rule.field_path}' is satisfied.", None
            return "UNRESOLVED", f"Required document '{rule.field_path}' is missing or empty.", None

        # -----------------------------------------------------------------
        # IN_SET Operator (Reference Set / Master Data Check)
        # -----------------------------------------------------------------
        if op == RuleOperator.IN_SET:
            if rule.reference_set:
                ref_set: ReferenceSet = rule.reference_set
                actual_code = str(actual).strip()
                matching_item = ref_set.items.filter(external_code__iexact=actual_code).first()

                if matching_item:
                    # Institution is empanelled. Now perform course-specific evaluation
                    course_name = get_nested_field(full_dossier, "application.course_name")
                    if course_name:
                        course_eligibility = InstitutionEligibility.objects.filter(
                            scheme_version=scheme_version,
                            institution=matching_item,
                            course_name__iexact=str(course_name).strip()
                        ).first()

                        if course_eligibility:
                            if course_eligibility.eligibility_status == EligibilityStatus.INELIGIBLE:
                                return (
                                    "FAIL",
                                    f"Course '{course_name}' is not an eligible program at {matching_item.name} under {scheme_version.scheme.code}.",
                                    None
                                )
                            elif course_eligibility.eligibility_status == EligibilityStatus.ELIGIBLE:
                                return (
                                    "PASS",
                                    f"Institution '{matching_item.name}' and course '{course_name}' are verified eligible under {scheme_version.scheme.code}.",
                                    None
                                )
                            else:
                                return (
                                    "UNRESOLVED",
                                    f"Course '{course_name}' at {matching_item.name} has conditional status ({course_eligibility.eligibility_status}).",
                                    None
                                )
                        else:
                            # Institution recognized, but specific course coverage not fully loaded
                            return (
                                "UNRESOLVED",
                                f"Institution '{matching_item.name}' is recognized, but course coverage for '{course_name}' is not yet fully loaded or verified.",
                                None
                            )

                    return "PASS", f"Institution '{matching_item.name}' ({actual_code}) is empanelled in reference set '{ref_set.name}'.", None

                # Institution is NOT found in the ReferenceSet items
                # CRITICAL SAFETY RULE (Part 0, 4, 5, 6, 20):
                # If dataset is SAMPLE or PARTIAL or unverified COMPLETE, we CANNOT conclusively mark INELIGIBLE!
                is_authoritative_complete = (
                    ref_set.dataset_status == DatasetStatus.VERIFIED or
                    (
                        ref_set.dataset_status == DatasetStatus.COMPLETE and
                        ref_set.record_count_expected > 0 and
                        ref_set.record_count_loaded == ref_set.record_count_expected
                    )
                )

                if is_authoritative_complete:
                    return (
                        "FAIL",
                        f"Institution/Code '{actual_code}' is not empanelled in the complete verified roster '{ref_set.name}'.",
                        None
                    )
                else:
                    # Incomplete master dataset: must return UNRESOLVED
                    dq_issue = {
                        "type": "INCOMPLETE_REFERENCE_DATASET",
                        "reference_set": ref_set.code,
                        "expected_records": ref_set.record_count_expected,
                        "loaded_records": ref_set.record_count_loaded,
                        "message": (
                            f"Reference dataset '{ref_set.code}' is marked {ref_set.dataset_status} "
                            f"({ref_set.record_count_loaded}/{ref_set.record_count_expected} records loaded). "
                            f"Institution '{actual_code}' cannot be conclusively rejected."
                        )
                    }
                    return (
                        "UNRESOLVED",
                        "Reference data is incomplete. Eligibility cannot be conclusively determined from the currently loaded official dataset.",
                        dq_issue
                    )

            elif isinstance(expected, list):
                if actual in expected or str(actual) in [str(x) for x in expected]:
                    return "PASS", f"Observed value '{actual}' is in approved list {expected}.", None
                return "FAIL", f"Observed value '{actual}' is not in approved list {expected}.", None

            return "UNRESOLVED", "Malformed IN_SET definition.", None

        # -----------------------------------------------------------------
        # NOT_IN_SET Operator
        # -----------------------------------------------------------------
        if op == RuleOperator.NOT_IN_SET:
            if isinstance(expected, list):
                if actual in expected or str(actual) in [str(x) for x in expected]:
                    return "FAIL", f"Observed value '{actual}' is in restricted list {expected}.", None
                return "PASS", f"Observed value '{actual}' is excluded from restricted list {expected}.", None
            return "UNRESOLVED", "Malformed NOT_IN_SET definition.", None

        # -----------------------------------------------------------------
        # EQUALS Operator
        # -----------------------------------------------------------------
        if op == RuleOperator.EQUALS:
            matches = (actual == expected) or (str(actual).strip() == str(expected).strip())
            if matches:
                return "PASS", f"Observed value '{actual}' exactly matches statutory requirement '{expected}'.", None
            return "FAIL", f"Observed value '{actual}' does not match statutory requirement '{expected}'.", None

        # -----------------------------------------------------------------
        # NOT_EQUALS Operator
        # -----------------------------------------------------------------
        if op == RuleOperator.NOT_EQUALS:
            matches = (actual == expected) or (str(actual).strip() == str(expected).strip())
            if not matches:
                return "PASS", f"Observed value '{actual}' satisfies negative condition (!= '{expected}').", None
            return "FAIL", f"Observed value '{actual}' unexpectedly matched restricted value '{expected}'.", None

        # -----------------------------------------------------------------
        # LESS_THAN_OR_EQUAL Operator (Income, Age, QS Rank)
        # -----------------------------------------------------------------
        if op == RuleOperator.LESS_THAN_OR_EQUAL:
            try:
                act_dec = Decimal(str(actual))
                exp_dec = Decimal(str(expected))
                if act_dec <= exp_dec:
                    if 'income' in rule.field_path.lower():
                        expl = f"Declared annual family income is ₹{act_dec:,.2f}, which is within the configured scheme ceiling of ₹{exp_dec:,.2f}."
                    elif 'age' in rule.field_path.lower():
                        expl = f"Applicant age of {act_dec} years is within the maximum limit of {exp_dec} years."
                    elif 'qs' in rule.field_path.lower() or 'rank' in rule.field_path.lower():
                        expl = f"Foreign institution QS rank of {act_dec} satisfies the Top {exp_dec} threshold."
                    else:
                        expl = f"Observed value {act_dec} satisfies upper ceiling requirement (<= {exp_dec})."
                    return "PASS", expl, None
                else:
                    if 'income' in rule.field_path.lower():
                        expl = f"Declared annual family income of ₹{act_dec:,.2f} exceeds statutory ceiling of ₹{exp_dec:,.2f}."
                    elif 'age' in rule.field_path.lower():
                        expl = f"Applicant age of {act_dec} years exceeds statutory limit of {exp_dec} years."
                    elif 'qs' in rule.field_path.lower() or 'rank' in rule.field_path.lower():
                        expl = f"Foreign institution QS rank of {act_dec} exceeds the Top {exp_dec} threshold."
                    else:
                        expl = f"Observed value {act_dec} exceeds statutory upper limit of {exp_dec}."
                    return "FAIL", expl, None
            except Exception as exc:
                return "UNRESOLVED", f"Cannot numerically compare '{actual}' with limit '{expected}': {str(exc)}", None

        # -----------------------------------------------------------------
        # GREATER_THAN_OR_EQUAL Operator
        # -----------------------------------------------------------------
        if op == RuleOperator.GREATER_THAN_OR_EQUAL:
            try:
                act_dec = Decimal(str(actual))
                exp_dec = Decimal(str(expected))
                if act_dec >= exp_dec:
                    return "PASS", f"Observed value {act_dec} satisfies minimum threshold (>= {exp_dec}).", None
                return "FAIL", f"Observed value {act_dec} is below statutory minimum threshold of {exp_dec}.", None
            except Exception as exc:
                return "UNRESOLVED", f"Cannot numerically compare '{actual}' with limit '{expected}': {str(exc)}", None

        return "UNRESOLVED", f"Unsupported rule operator '{op}'.", None
