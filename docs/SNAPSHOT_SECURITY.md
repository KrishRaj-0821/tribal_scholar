# Submission Snapshot Security & Privacy Guarantees

## 1. PII and Sensitive Data Governance (Part 9)
Application submission snapshots (`ApplicationSubmissionSnapshot`) contain sensitive demographic, financial, and institutional Personally Identifiable Information (PII), including:
- Applicant full legal name, date of birth, gender, and disability status
- Caste/Tribe category and PVTG classification
- Exact annual family income figures
- Document verification manifests, SHA-256 hashes, and filenames

## 2. Access Control Model
- **Authenticated Access Only**: Anonymous requests are denied with `401 Unauthorized`.
- **Applicant Strict Self-Access**: Applicants can only view the submission snapshot of their own application. Cross-applicant requests are rejected with `403 Forbidden` or `404 Not Found`.
- **Authorized Scrutiny Officers & Admins**: Scrutiny Officers and Admins can view snapshots for verification purposes within their designated jurisdiction.
- **Mandatory Audit Logging**: Whenever any sensitive snapshot is inspected via `GET /api/v1/applications/{id}/submission-snapshot/`, an append-only audit event (`AuditAction.SNAPSHOT_VIEWED`) is logged with the user ID, timestamp, and target application ID.

## 3. Log Hygiene & Error Sanitization
- Normal application request/response logs **NEVER** dump raw snapshot JSON or applicant demographic PII.
- Exception handlers suppress raw PII from tracebacks.
- Result hashes are stored as irreversible SHA-256 digests (`snapshot_hash`).

## 4. Security Limitations & Production Readiness
> [!IMPORTANT]
> **Encryption-at-Rest Limitation (Development Prototype)**:
> In this SIH development prototype, JSON payloads are stored unencrypted at the database layer (PostgreSQL / SQLite `JSONField`). Field-level encryption-at-rest (such as pgp_sym_encrypt or KMS envelope encryption) is NOT enabled in the prototype environment. We do NOT claim government-grade encryption exists where it has not been configured. In production, column-level KMS encryption must be applied to `applicant_data_json` and `form_values_json`.
