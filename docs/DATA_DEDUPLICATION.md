# Data Deduplication & Application Uniqueness Policy

## 1. Statutory Context & Principles (Part 10 & 11)
Real-world scholarship guidelines vary in their treatment of multiple applications:
- Certain fellowship schemes permit a candidate to submit separate research proposals or reapply under differing qualification cycles.
- Blindly placing a database constraint `UNIQUE(applicant, scheme_version)` breaks legitimate renewal workflows and nuanced scheme rules.
- Deduplication matches must **NEVER be prematurely labeled as "Fraud"**. Discrepancies often arise from sibling applicants using a common family phone/computer, identical documents uploaded for multiple siblings (e.g. parent income certificates), or benign resubmissions.

## 2. Policy-Driven Uniqueness (`ApplicationUniquenessPolicy`)
Each `SchemeVersion` defines its uniqueness governance:
- `max_active_applications`: Number of concurrent active applications permitted (default: 1).
- `allow_multiple_drafts`: Boolean flag controlling draft multiplicity.
- `allow_resubmission`: Boolean flag controlling resubmission after withdrawal/rejection.
- `duplicate_detection_mode`:
  - `WARN`: Flags warning in response and logs audit entry; allows submission.
  - `REVIEW`: Flags application with `POSSIBLE_DUPLICATE` and routes to officer review. (Prototype Default)
  - `STRICT`: Rejects duplicate submissions with `ValidationError`.

## 3. Deduplication Scanner Service (`DuplicateDetectionService`)
During pre-submission scanning, the service matches against:
1. **Existing Active Applications**: Same applicant profile on the same scheme version.
2. **Document Checksum Collision**: SHA-256 collision of certificates across distinct user accounts in the same academic cycle.
3. **Normalized Profile Attributes**: Matching normalized name, date of birth, and institution.

### Output Contract:
```json
{
  "is_duplicate": true,
  "mode": "REVIEW",
  "flag": "POSSIBLE_DUPLICATE",
  "matches": [
    {
      "type": "DOCUMENT_CHECKSUM_MATCH",
      "detail": "Document hash matches submission from another user (CASTE_CERTIFICATE)."
    }
  ]
}
```
All duplicate detections generate an append-only `AuditLog` event (`AuditAction.DUPLICATE_FLAGGED`) with full match criteria for Scrutiny Officer adjudication.
