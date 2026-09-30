# PHASE 8: HUMAN-IN-THE-LOOP DOCUMENT VERIFICATION ARCHITECTURE

## 1. Executive Summary & Core Principle

In the **Tribel_Scholor** statutory scholarship administration system, the Human-in-the-Loop Document Verification subsystem bridges automated processing and statutory eligibility determination.

### Core Principle
> **The Officer Verifies Evidence. The Officer Does NOT Rewrite History.**  
> **The Officer Does NOT Directly Edit the Underlying Original Document.**  
> **The Officer Does NOT Bypass the Deterministic Scheme Rule Engine.**  
> **Every Officer Action Creates an Auditable, Append-Only Verification Event.**

The fundamental boundaries are strictly enforced:
```text
OCR Output != Eligibility Decision
Officer Verification != Eligibility Decision
Eligibility Decision == Pure Deterministic Rule Evaluation over Verified Evidence
```

---

## 2. Verification Lifecycle State Machine

The document verification state machine governs the promotion of OCR provisional data to verified evidence without mutating original documents:

```text
       Applicant Document Upload
                  │
                  ▼
          QUARANTINE / SCAN
                  │
                  ▼
                 SAFE
                  │
                  ▼
            OCR_PROVISIONAL (Trust Rank: 10)
                  │
                  ▼
         VERIFICATION_PENDING
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
    VERIFIED             CONFLICT
 (Trust Rank: 40)           │
        │                   ▼
        │              HUMAN REVIEW
        │             (Officer Workbench)
        │                   │
        └─────────┬─────────┘
                  ▼
          VERIFIED_DOCUMENT
                  │
                  ▼
         DETERMINISTIC ENGINE
    (Pure Rule Evaluation)
```

---

## 3. Data Models & Immutability Invariant

### 3.1. `DocumentVerificationRecord` (Append-Only)
Defined in `apps.verification.models`:

- **`id`**: Unique UUID primary key.
- **`document`**: Foreign key to `ApplicantDocument`.
- **`document_version`**: Foreign key to `DocumentVersion`.
- **`ocr_result`**: Foreign key to `OCRResult`.
- **`ocr_page`**: Foreign key to `OCRPage`.
- **`ocr_block`**: Foreign key to `OCRBlock` (source bounding box, text, confidence).
- **`field_code`**: Field identifier (e.g., `annual_family_income`, `community`).
- **`previous_value_json`**: Snapshot of prior value (declared or previous verification).
- **`verified_value_json`**: Explicit value confirmed by officer.
- **`verification_status`**: `PENDING`, `VERIFIED`, `REJECTED`, `CONFLICT`, `NEEDS_REVIEW`.
- **`decision_action`**: `USE_APPLICANT_DECLARATION`, `USE_DOCUMENT_VALUE`, `REQUEST_CORRECTION`, `NEEDS_REVIEW`.
- **`officer`**: Foreign key to `User` (the authorized reviewer).
- **`verified_at`**: Timestamp.
- **`reason`**: Mandatory human justification string.
- **`verification_method`**: `MANUAL_OFFICER_REVIEW`, `PHYSICAL_INSPECTION`, `DIGILOCKER_OFFICIAL_API`, `OFFICIAL_AUTHORITY_LETTER`.
- **`superseded_record`**: Self-referencing FK linking to historical verification record when re-verifying or reopening.

### Immutability Invariant:
Once written, rows in `DocumentVerificationRecord` **CANNOT** be updated or deleted.  
Attempts to call `record.delete()` or `DocumentVerificationRecord.objects.filter(...).update(...)` raise an immutable `ValidationError`.  
If a field is re-opened or re-verified by a senior authority, a **new** record is created with `superseded_record` pointing to the previous event, maintaining an uninterrupted cryptographic audit lineage.

---

## 4. Evidence-First Verification Linkage

When an officer inspects a field in the Officer Workbench, the system provides full evidence provenance:
```text
Original Document (SAFE Storage)
      ↓
DocumentVersion (SHA-256 Checksum)
      ↓
OCRPage (Dimensions, Hash)
      ↓
OCRBlock (Bounding Box [x, y, w, h], Polygon, Confidence, Script)
      ↓
Extracted Field (Normalized Value)
      ↓
Officer Verification Event (Identity, Timestamp, Justification)
      ↓
Verified Value (Promoted to ApplicationFieldValue with Trust Rank 40)
```

---

## 5. Conflict Resolution Workflow

When a discrepancy is detected between applicant declaration and document evidence:
```text
Applicant Declaration: ₹5,00,000
Document OCR Text:     ₹4,50,000
Conflict Status:       MATERIAL_DISCREPANCY (Open)
```

The system **does not** automatically pick a winner. The officer must explicitly evaluate the evidence and choose an action:
1. `USE_DOCUMENT_VALUE`: Overrides declaration with the verified certificate value (promoted with Trust Rank 40 `OFFICER_VERIFIED`).
2. `USE_APPLICANT_DECLARATION`: Confirms applicant declaration is valid despite differing document phrasing.
3. `REQUEST_CORRECTION`: Issues deficiency back to applicant for clarification without rejecting the application.
4. `NEEDS_REVIEW`: Escalates to supervisory authority for further inquiry.

---

## 6. Role-Based Access Control (RBAC) & Separation of Duties

All verification APIs enforce server-side role validation:
- **`APPLICANT`**: Strictly forbidden from verifying documents or calling verification APIs (`403 Forbidden`). An applicant cannot verify their own application or another applicant's documents.
- **`SCRUTINY_OFFICER`** / **`VERIFYING_AUTHORITY`**: Authorized to view document evidence, submit field verifications, and resolve conflicts.
- **`SYSTEM / OCR SERVICE`**: Cannot impersonate an officer or perform officer verifications.

---

## 7. Audit Events Specification

Every lifecycle transition emits a dedicated audit event to the append-only `AuditLog`:
- `DOCUMENT_VERIFICATION_STARTED`
- `FIELD_VERIFIED`
- `FIELD_REJECTED`
- `FIELD_CONFLICT_RESOLVED`
- `DOCUMENT_VERIFICATION_COMPLETED`
- `DOCUMENT_VERIFICATION_REOPENED`

Audit records contain `actor`, `timestamp`, `entity_type`, `entity_id`, `action`, `before_json`, `after_json`, `reason`, and `correlation_id`. Zero raw document binary bytes or sensitive plaintext passwords/PII are ever written to audit logs.

---

## 8. Frontend Officer Verification Workbench

Built in React (`VerificationWorkbench.tsx`) as a responsive dual-pane desktop / stacked mobile workstation:
- **Left Pane**: High-resolution document viewer with SVG evidence bounding-box overlays (`highlightBbox`) indicating the exact physical coordinates on the page where text was extracted.
- **Right Pane**: Evidence comparison panel displaying declared applicant value, extracted OCR value, confidence metrics, conflict resolution action controls, and full immutable audit history.
