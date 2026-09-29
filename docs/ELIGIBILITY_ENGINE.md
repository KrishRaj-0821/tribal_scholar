# Deterministic Eligibility Engine (RuleEvaluationService v2.0.0)

## 1. Overview & Non-Negotiable Safety Rule

The **Deterministic Eligibility Engine** (`RuleEvaluationService`) is the statutory core of the Ministry of Tribal Affairs (MoTA) Scholarship and Fellowship Management System. It evaluates whether an applicant's dossier satisfies statutory guidelines for central tribal scholarship schemes (such as Top Class Education, National Fellowship for Higher Education of ST Students [NFST], and National Overseas Scholarship [NOS]).

### The Non-Negotiable Safety Rule
> **The system must NEVER mark an applicant `INELIGIBLE` merely because an official master or reference dataset is incomplete.**

When an applicant selects an institution or course that is not found within a local database dataset whose `dataset_status` is `SAMPLE`, `PARTIAL`, or `COMPLETE` (unverified), the engine cannot distinguish between:
1. *"The institution is officially ineligible under MoTA guidelines"*, and
2. *"The institution is officially eligible, but our local database roster has not yet ingested the complete gazette dataset."*

Because central scholarships are life-altering constitutional entitlements for Scheduled Tribe candidates, the engine guarantees that **absence from an incomplete roster results in `UNRESOLVED` (aggregated to `NEEDS_REVIEW`), accompanied by an explicit data quality notice.** Rejection (`FAIL` / `INELIGIBLE`) is strictly permitted **only** when evaluated against a `COMPLETE` and cryptographically `VERIFIED` authoritative master dataset.

---

## 2. Eligibility Engine Contract

### Input Dossier
The engine receives a structured application dossier along with an explicit `SchemeVersion` record:
- **`application_id`**: Target application UUID / tracking code.
- **`scheme_version`**: The exact statutory version tied to the application's academic year (e.g., `2025-26`).
- **`dossier`**: Structured dictionary containing:
  - `applicant`: Community, income, gender, DOB, etc.
  - `application`: Course level, admission date, institution identifiers, overseas ranking, etc.
  - `documents`: Dictionary of uploaded statutory certificates with verification status (`VERIFIED`, `UNVERIFIED`, `EXPIRED`, `INVALID`, `MISSING`).
  - Structured application fields.

### Output JSON Contract
```json
{
  "status": "ELIGIBLE | INELIGIBLE | NEEDS_REVIEW",
  "blocking_failures": [
    {
      "rule_id": "TOP_CLASS_2025_INCOME_CEILING",
      "result": "FAIL",
      "observed_value": 850000,
      "operator": "<=",
      "required_value": 600000,
      "explanation": "Declared annual family income is ₹8.50 lakh, which exceeds the configured scheme ceiling of ₹6.00 lakh.",
      "source_document_id": "41cf4aa3-1627-4bf0-ba8f-7c15e8c3b001",
      "source_url": "https://tribal.nic.in/schemes/top-class-guidelines-2025.pdf",
      "source_excerpt": "Section 4(ii): Total family income from all sources shall not exceed ₹6.00 lakh per annum.",
      "provenance_status": "OFFICIAL_VERIFIED"
    }
  ],
  "warnings": [],
  "matched_rules": [...],
  "unresolved_rules": [
    {
      "rule_id": "TOP_CLASS_2025_PREMIER_INSTITUTE",
      "result": "UNRESOLVED",
      "observed_value": "IIT_GOA_001",
      "operator": "IN_SET",
      "required_value": "TOP_CLASS_PREMIER_INSTITUTES_SAMPLE",
      "explanation": "Reference data is incomplete. Eligibility cannot be conclusively determined from the currently loaded official dataset.",
      "source_document_id": "41cf4aa3-1627-4bf0-ba8f-7c15e8c3b002",
      "provenance_status": "OFFICIAL_VERIFIED"
    }
  ],
  "data_quality_issues": [
    {
      "type": "INCOMPLETE_REFERENCE_DATASET",
      "rule_code": "TOP_CLASS_2025_PREMIER_INSTITUTE",
      "reference_set": "TOP_CLASS_PREMIER_INSTITUTES_SAMPLE",
      "expected_records": 265,
      "loaded_records": 7,
      "description": "Reference data is incomplete. Eligibility cannot be conclusively determined from the currently loaded official dataset."
    }
  ],
  "source_references": [
    {
      "rule_code": "TOP_CLASS_2025_PREMIER_INSTITUTE",
      "document_title": "Top Class Education Guidelines 2025-26",
      "source_url": "https://tribal.nic.in/schemes/top-class-guidelines-2025.pdf",
      "provenance_status": "OFFICIAL_VERIFIED"
    }
  ],
  "evaluated_at": "2026-09-28T09:30:00Z",
  "rule_version": "2025-26 v1",
  "result_hash": "a1b2c3d4e5f6..."
}
```

---

## 3. Pre-Evaluation Data Quality Layer (`DataQualityValidator`)

Before executing statutory business rules, the dossier is inspected by `DataQualityValidator`. It identifies:
- Missing required fields (e.g. absent community or income declaration).
- Negative or non-numeric income amounts.
- Future birth dates or impossible historical birth dates (>120 years ago).
- Inconsistent academic years (e.g., application applying for `2025-26` but submitted under `2026-27` version).
- Course-level inconsistencies (e.g., applying for PhD without a postgraduate qualification).
- Duplicate applicant registrations.

**Data quality issues never cause synthetic `INELIGIBLE` failures.** Instead, they flag the evaluation as `NEEDS_REVIEW` with an explicit diagnostic trail for the scrutiny officer.

---

## 4. Rule Category Isolation

To prevent misapplying administrative procedures as legal disqualifiers, rules are strictly categorized:
- **Executed by Eligibility Engine**:
  - `ELIGIBILITY` (income, community, age, min percentage)
  - `DOCUMENT` (mandatory certificate existence and verification)
  - `VALIDATION` (field constraints and data formats)
- **Prohibited from Execution by Eligibility Engine**:
  - `SELECTION` (merit ranking algorithms, committee evaluation)
  - `PREFERENCE` (vulnerable tribal group preference, gender priority)
  - `QUOTA` (sanctioned slot limits, state caps)
  - `BENEFIT` (stipend amount calculation, fee reimbursement)
  - `WORKFLOW` (approval stages, SLA routing)

Any non-eligibility rule included in a scheme version is safely skipped by the engine.

---

## 5. Course-Specific Institutional Qualification

The engine supports granular institution evaluation through `InstitutionEligibility`. Instead of approving an institution globally, the engine verifies:
$$\text{Institution} + \text{Course Level} + \text{Academic Year} + \text{Scheme Version}$$

- If an institution exists in an authoritative roster but the specific course is listed as `INELIGIBLE`, the rule fails with `FAIL` (`INELIGIBLE`).
- If an institution exists but course coverage has not been fully verified, the rule produces `UNRESOLVED` (`NEEDS_REVIEW`).

---

## 6. Zero Hidden AI / LLM Invariant

The engine contains **no LLM calls, embeddings, or heuristic AI models**.
- Evaluation is 100% deterministic, verifiable, and rule-driven.
- OCR or AI models in earlier pipeline stages may extract dossier fields, but the engine only accepts structured fields and executes verified mathematical/relational rules.

---

## 7. Idempotency, Immutability & Statutory Audit

### Result Hash
Each evaluation computes a canonical SHA-256 digest (`result_hash`) across normalized evaluation components:
```python
hash_payload = {
    "status": result["status"],
    "scheme_version": str(scheme_version.id),
    "blocking_failures": sorted_failures,
    "matched_rules": sorted_matched,
    "unresolved_rules": sorted_unresolved,
    "data_quality_issues": sorted_issues,
}
```
Two evaluations of the same dossier against the same scheme version yield identical hashes.

### Immutable Records (`EligibilityEvaluation`)
Evaluations are persisted to the `EligibilityEvaluation` model. Historical records are immutable: any update or delete operation raises a `ValidationError`.

### Append-Only Audit Trail
Every evaluation automatically emits an immutable audit event:
- **`action`**: `ELIGIBILITY_EVALUATED`
- **`entity_type`**: `Application`
- **`entity_id`**: `<application_uuid>`
- **`metadata`**: Scheme version, engine version, evaluated rule count, status, actor, and result hash.

---

## 8. REST API Endpoint

### Endpoint
`POST /api/v1/applications/{id}/evaluate-eligibility/`

### Permissions & RBAC
- **Unauthenticated**: `401 Unauthorized` / `403 Forbidden`
- **Applicant**: Can evaluate only their own application. Attempting to evaluate another student's application returns `404 Not Found` or `403 Forbidden`.
- **Scrutiny Officer / Admin**: Can evaluate any application in the system.
