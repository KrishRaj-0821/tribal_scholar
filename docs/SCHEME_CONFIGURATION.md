# Scheme Configuration & Rule Engine Specification
## MoTA SIH Problem Statement 26239

---

### 1. Overview
The **Scheme Configuration Engine** provides a declarative, versioned, and auditable foundation for defining government scholarships without altering code. 

In traditional scholarship platforms, rules such as *"Family income <= ₹6,00,000"* or *"Targeted at Scheduled Tribes (ST)"* are often hardcoded into business logic. This causes immense maintenance drag, failure to track policy amendments across academic years, and zero traceability to official Gazette guidelines.

In **Tribal Scholar**, every scheme policy is transformed into data:
* Schemes are versioned by **Academic Year** (`SchemeVersion`).
* Eligibility, quotas, and preferences are decomposed into discrete, deterministic **Rules** (`SchemeRule`).
* Large eligibility domains (e.g., premier institutes, recognized universities, eligible overseas courses) are encapsulated in **Reference Sets** (`ReferenceSet` / `ReferenceSetItem`).
* Every rule and reference item maintains a required link to a verified **Source Document** (`SourceDocument`).

---

### 2. Data Model Hierarchy

```
[ Scheme ]
    │  (1 to Many)
    ▼
[ SchemeVersion ]  <── Linked to ──  [ SourceDocument (e.g., Guideline/Advertisement) ]
    │  (1 to Many)
    ├──► [ SchemeRule ] (category: ELIGIBILITY, DOCUMENT, SELECTION, PREFERENCE, BENEFIT, WORKFLOW, VALIDATION)
    │         │
    │         └── (Optional FK) ──► [ ReferenceSet ] (dataset_status, record_count_expected/loaded)
    │                                     │ (1 to Many)
    │                                     ├──► [ ReferenceSetItem ] <── Linked to ── [ SourceDocument ]
    │                                     └──► [ InstitutionEligibility ] (course-specific mapping)
    │
    ├──► [ SchemeQuota ] (total_capacity, category, gender, reserved_capacity)
    ├──► [ SelectionMethod ] (code, name, human_decision_required)
    │
    └──► (1 to 1) ──► [ WorkflowDefinition ]
                           │ (1 to Many)
                           ├──► [ WorkflowState ]
                           └──► [ WorkflowTransition ]
```

---

### 3. SchemeRule Mechanics & The Eight Categories

#### A. Core Schema
* `rule_code`: Human-readable identifier (e.g., `TOP_CLASS_2025_INCOME_CEILING`).
* `category`: Explicit classification into exactly one `RuleCategory`:
  * `ELIGIBILITY`: Objective binary requirements evaluated during applicant eligibility screening.
  * `DOCUMENT`: Documentary verification requirements.
  * `SELECTION`: Merit scoring and committee rubrics.
  * `PREFERENCE`: Prioritization metrics (e.g. PVTG, Divyangjan) that **never** cause eligibility disqualification.
  * `QUOTA`: Capacity limits stored in `SchemeQuota` (decoupled from applicant eligibility).
  * `BENEFIT`: Entitlement and scholarship rate configurations.
  * `WORKFLOW`: Procedural transitions and authentication gates.
  * `VALIDATION`: System format constraints and input validations.
* `field_path`: Dot-notation path to the application data structure (e.g., `applicant.community`, `applicant.annual_family_income`, `application.course_level`).
* `operator`:
  * `EQUALS`, `NOT_EQUALS`
  * `LESS_THAN_OR_EQUAL`, `GREATER_THAN_OR_EQUAL`
  * `IN_SET`, `NOT_IN_SET`
  * `EXISTS`
  * `PENDING_OFFICIAL_EXTRACTION` (Indicates criteria pending gazette/notification release)
* `value`: Target comparison value (JSON formatted: string, integer, float, list, or null).
* `reference_set`: Optional foreign key to a `ReferenceSet` for complex membership checks.
* `failure_message`: Human-readable feedback citing policy reasoning.
* `severity`: `BLOCKING`, `WARNING`, `MANUAL_REVIEW`.
* `source_document`: Mandatory foreign key to `SourceDocument`.
* `source_excerpt`: Short exact textual excerpt from the official publication.
* `confidence`: `OFFICIAL`.

#### B. Deterministic Rule Evaluator Contract
The evaluation service (`RuleEvaluationService`) evaluates candidate dossiers against active `ELIGIBILITY` rules and outputs:
```json
{
  "application_id": "...",
  "scheme_version": "...",
  "eligibility_status": "ELIGIBLE | INELIGIBLE | NEEDS_REVIEW",
  "blocking_failures": [],
  "warnings": [],
  "matched_rules": [],
  "unresolved_rules": [],
  "source_references": []
}
```
* **Guardrail**: If any rule lacks verified official provenance, is marked `PENDING_OFFICIAL_SOURCE_EXTRACTION`, or has operator `PENDING_OFFICIAL_EXTRACTION`, the evaluator returns `NEEDS_REVIEW` and populates `unresolved_rules`. It **NEVER** silently passes.
* **Quota Decoupling**: Quota rules (`SchemeQuota`) are evaluated during capacity allocation, never as an eligibility barrier.
* **Preference Isolation**: Preference rules (`PREFERENCE`) record priority in `matched_rules` but never trigger `INELIGIBLE`.

#### C. The `PENDING_OFFICIAL_SOURCE_EXTRACTION` Protocol
Government schemes frequently introduce revisions, such as the **NOS 2026-27 Course Amendment**. Under our architectural safety guidelines:
1. **Never guess** or fabricate eligibility parameters.
2. If an official gazette or notification states that a rule is modified, but the full clause has not been parsed or verified, the rule is created with status / operator `PENDING_OFFICIAL_SOURCE_EXTRACTION`.
3. An active `SchemeVersion` cannot be approved or activated if any of its mandatory rules remain `PENDING_OFFICIAL_SOURCE_EXTRACTION`.
4. Automated system checks raise validation exceptions if an activated version contains unextracted rules.

---

### 4. Reference Sets (Configurable Master Data)
Instead of hardcoding institute lists or course categories into code or database enums:
* `ReferenceSet`: Groups items under a unique code (e.g., `TOP_CLASS_PREMIER_INSTITUTES`, `NFST_RECOGNIZED_UNIVERSITIES`).
* `ReferenceSetItem`: Represents a specific approved entity (e.g., IIT Bombay, AIIMS New Delhi) with AISHE code, valid date ranges, and metadata.
* **Strict Integrity Requirement**: Every `ReferenceSetItem` must point to a verified `SourceDocument` (such as the official MoTA Annexure of Empanelled Institutes).

---

### 5. Multi-Year Version Coexistence
* Multiple academic years (e.g., `2024-25`, `2025-26`, `2026-27`) coexist simultaneously in the database.
* Applications submitted under `2024-25` remain strictly bound to `SchemeVersion` for `2024-25`.
* Introducing a new `SchemeVersion` for `2025-26` or `2026-27` never mutates or invalidates historical versions or historical eligibility evaluations.

---

### 6. Automated Startup & Integrity Validation
The system implements automated integrity checks running on Django startup, CI tests, and scheme approval workflows:
1. **Rule Provenance Check**: Fails if any `SchemeRule` lacks a `source_document`.
2. **Academic Year Check**: Fails if any `SchemeVersion` lacks an `academic_year`.
3. **Active Workflow Check**: Fails if an active `SchemeVersion` lacks an associated `WorkflowDefinition`.
4. **Unpublished/Unknown Rules Check**: Fails if an active `SchemeVersion` has rules marked `PENDING_OFFICIAL_SOURCE_EXTRACTION` or draft.
5. **Reference Set Item Provenance Check**: Fails if a `ReferenceSetItem` referenced by an active rule has no `source_document`.
