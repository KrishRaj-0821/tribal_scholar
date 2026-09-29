# Field Trust Hierarchy & Multi-Source Conflict System

## 1. Statutory Field Trust Order (Part 2)
In the Tribel_Scholor architecture, field values originate from multiple distinct evidence sources (applicant declarations, direct API integrations, certified documents, scrutiny officers, and provisional OCR extraction).

The authoritative trust hierarchy is strictly defined as:

```
OFFICER_VERIFIED (Trust Rank: 50)
        ▲
        │
OFFICIAL_INTEGRATION (Trust Rank: 40)
        ▲
        │
VERIFIED_DOCUMENT (Trust Rank: 30)
        ▲
        │
     SYSTEM (Trust Rank: 25)
        ▲
        │
APPLICANT_DECLARED (Trust Rank: 20)
        ▲
        │
OCR_PROVISIONAL (Trust Rank: 10)
```

### Rationale
- **OCR is provisional evidence, not truth**: Raw OCR extraction can produce misreads, OCR hallucinations, or incorrect character recognition (e.g. `400000` misread as `540000`).
- Raw OCR must **never silently overwrite** an applicant's declared value.
- A value extracted by OCR starts as `FieldValueVerificationStatus.PROVISIONALLY_EXTRACTED` and is assigned rank 10.
- Only when an officer or an automated certified pipeline confirms the document does it graduate to `DOCUMENT_VERIFIED` (rank 30) or `OFFICER_VERIFIED` (rank 50).

## 2. FieldValueVerificationStatus Enum
Every value recorded in `ApplicationFieldValue` has a lifecycle status:
- `UNVERIFIED`: Declared by applicant, awaiting document or officer scrutiny.
- `PROVISIONALLY_EXTRACTED`: Parsed by automated OCR/extraction; not yet confirmed.
- `DOCUMENT_VERIFIED`: Confirmed by verified documentary evidence.
- `OFFICIAL_VERIFIED`: Directly fetched from authoritative institutional/government registries.
- `OFFICER_VERIFIED`: Inspected and approved by a human Scrutiny Officer.

## 3. Conflict Detection Engine (Part 3)
When multiple sources report different values for the same field code on an application, `FieldConflictService` detects and logs a `FieldConflict`:

### Model Structure (`FieldConflict`):
- `application`: Foreign key to the target application.
- `field_code`: E.g. `annual_family_income`, `community`, `course_level`.
- `values_json`: List of all competing values.
- `source_values`: Dictionary of source-tagged values (e.g., `{"APPLICANT": 400000, "OCR": 540000}`).
- `severity`: `MATERIAL` or `INFORMATIONAL`.
- `status`: `OPEN`, `UNDER_REVIEW`, `RESOLVED`, `WAIVED`.
- `resolved_by`, `resolution`, `resolved_at`: Officer adjudication trail.

### Non-Negotiable Eligibility Rule
When a material unresolved conflict (`status in ['OPEN', 'UNDER_REVIEW']`) affects a field evaluated by an active eligibility rule:
- The rule evaluation engine **MUST NOT silently pick one value**.
- The rule is flagged as `UNRESOLVED`.
- The aggregate eligibility status returns **`NEEDS_REVIEW`** with a clear explanation:
  ```json
  "explanation": "Material unresolved field conflict exists for 'annual_family_income' across sources: {'APPLICANT': 400000, 'OCR': 540000}."
  ```
