# Secure Document Ingestion Architecture

## 1. Overview & Objective

The Tribel_Scholor document ingestion foundation implements a zero-trust, defense-in-depth ingestion pipeline designed to ingest, isolate, validate, scan, and manifest applicant documents before any automated extraction (OCR) or verification can occur.

The foundational ingestion flow follows the strict lifecycle:
```text
SECURE FILE → QUARANTINE → VALIDATE → HASH → SCAN → STORE → MANIFEST → ASYNC PROCESSING READY
```

> **Strict Non-Verification Boundary**:
> Automated document verification, text/field extraction (OCR), and eligibility inference are explicitly out of scope for this phase. Ingestion establishes the authentic, tamper-evident evidence chain; human or OCR-based verification operates strictly downstream.

---

## 2. Explicit Document Lifecycle State Machine

Documents progress through a deterministic, strictly enforced 12-state lifecycle:

1. **`INITIATED`**: Document upload session or requirement declared.
2. **`UPLOADING`**: File bytes stream from client to server.
3. **`UPLOADED`**: Server received payload into initial quarantine boundary.
4. **`QUARANTINED`**: Payload isolated in sandbox quarantine storage key (`quarantine/{document_id}/{filename}`).
5. **`SCANNING`**: Antivirus and deep content validation engines currently evaluating payload.
6. **`SAFE`**: File passed magic-byte detection, structural sanity, decompression safety, and malware scanning. File promoted to safe document bucket.
7. **`REJECTED`**: Validation failure (MIME mismatch, malformed PDF, decompression bomb) or malware detected (`INFECTED`). Quarantined payload deleted.
8. **`PROCESSING`**: Asynchronous worker processing background extraction tasks.
9. **`PROCESSED`**: Background jobs completed; document ready for human scrutiny or review.
10. **`VERIFICATION_PENDING`**: Queued for scrutiny officer evaluation.
11. **`VERIFIED`**: Certified authentic and eligible by an authorized scrutiny officer.
12. **`REVOKED`**: Nullified or invalidated by an authorized official (non-destructive audit retention).

### Lifecycle Transition Guard
- **Forbidden Jump**: Direct transition from `UPLOADED` $\rightarrow$ `VERIFIED` is strictly rejected at model and service boundaries with a `ValidationError`. Verification belongs exclusively to human scrutiny or approved verification workflows.

---

## 3. Document Requirement Binding

Uploaded documents are bound to canonical `DocumentRequirement` rules:
- Requirement lookup joins `scheme_version`, `academic_year`, and `document_type`.
- If an applicant uploads an arbitrary or unsupported document type not declared in the application's active `SchemeVersion`, the request is rejected immediately with a structured HTTP 400 `UNSUPPORTED_DOCUMENT_TYPE` error.
- Enforces statutory document validity policies (e.g., `FINANCIAL_YEAR_BOUND`, `ONE_TIME_ISSUANCE`).

---

## 4. Implementation Status Matrix

| Component | Status | Details |
| :--- | :--- | :--- |
| Multipart Upload & Quarantine Storage | **IMPLEMENTED** | Server-side size validation, quarantine directory isolation, path traversal sanitization |
| Authoritative SHA-256 Computation | **IMPLEMENTED** | Computed purely server-side from raw bytes; client-provided checksums ignored |
| Magic-Byte & File Structure Validation | **IMPLEMENTED** | Deep PDF structural parse, Pillow image raster decoding, pixel bomb rejection |
| Malware Scanning Boundary | **IMPLEMENTED** | `MalwareScanner` ABC with `MockMalwareScanner` and `ClamAVScanner` socket adapter |
| Quarantine Promotion & Safe Storage | **IMPLEMENTED** | Atomic copy and quarantine unlink upon clean scan result |
| Immutable Manifest & Versioning | **IMPLEMENTED** | Append-only `DocumentManifest` and `DocumentVersion` audit preservation |
| Celery Async Dispatch | **IMPLEMENTED** | Dispatched via `transaction.on_commit()` with exponential retry/backoff |
| Row-Level Concurrency Locks | **IMPLEMENTED** | `select_for_update()` prevents race conditions across competing workers |
| OCR / Text Extraction | **FUTURE** | Intentionally not implemented in this phase; scheduled for Phase 7 |
| Automatic Eligibility Inference | **FUTURE** | Documents serve as raw evidence only; no automated income/caste approval |
