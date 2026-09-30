# Tribel_Scholor Document Failure Matrix

This document defines the authoritative failure mode taxonomy, state transitions, retry semantics, manual review flags, cleanup behaviors, and audit trails across the document ingestion and processing lifecycle.

---

## 1. Overview & Architectural Boundaries

```
[ Upload HTTP Request ]
          │
          ▼ (Magic Byte & Size Gate)
[ Quarantine Storage ] ──> [ Database Transaction ] ──> [ Celery on_commit() ]
                                                                 │
                                                                 ▼
                                                        [ Real Redis Broker ]
                                                                 │
                                                                 ▼
                                                        [ Celery Worker ]
                                                                 │
                                     ┌───────────────────────────┴───────────────────────────┐
                                     ▼                                                       ▼
                            [ ClamAV Scan ]                                      [ Format/Security Validation ]
                                     │                                                       │
                                     └───────────────────────────┬───────────────────────────┘
                                                                 ▼
                                                     [ Storage Promotion ]
                                                                 │
                                                                 ▼
                                                   [ Immutable Manifest & SAFE ]
```

All document transitions strictly adhere to the `ApplicantDocument.VALID_LIFECYCLE_TRANSITIONS` state machine.
`SAFE` and `REJECTED` are distinct terminal/post-security outcomes, and transitions directly from `SAFE` to `REJECTED` are prohibited without explicit administrative revocation (`DOCUMENT_REVOKED`).

---

## 2. Comprehensive Failure Matrix

| Failure Mode | State Before | State After | Retry Policy | Manual Review? | Cleanup Action | Audit Event Produced |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Invalid MIME** | `INITIATED` / `UPLOADING` | `REJECTED` | No (permanent client error) | No | Quarantine payload deleted immediately if created. | `DOCUMENT_REJECTED` (reason: `MIME_MISMATCH` or `DISALLOWED_MIME`) |
| **2. Malformed PDF** | `SCANNING` | `REJECTED` | No (permanent malformed file) | No | Quarantine payload purged; job marked `PERMANENT_FAILURE`. | `DOCUMENT_REJECTED` (reason: `PDF_HEADER_MISSING` / `PDF_CORRUPT`) |
| **3. Scanner Unavailable** | `SCANNING` | `QUARANTINED` | Yes (automatic Celery backoff retry, up to 3 attempts, exponential backoff) | Yes, if retries exhausted | Quarantine payload retained in quarantine storage; never marked `SAFE`. | `celery_task_execution` log with status `TRANSIENT_FAILURE_RETRYING`; alert raised on 3rd failure |
| **4. Malware Detected** | `SCANNING` | `REJECTED` | No (permanent security rejection) | Yes (Security Officer notification) | File isolated in security quarantine storage with `SecurityQuarantineRecord` (`retention_until` = 30 days statutory policy). Never deleted silently. | `DOCUMENT_REJECTED` (threat name, scanner signature, and correlation ID logged) |
| **5. Redis Unavailable** | `UPLOADING` / `QUARANTINED` | `QUARANTINED` | Yes (connection retry on broker reconnect; persistent in PostgreSQL) | No (self-healing on Redis recovery) | None. Database transaction holds `DocumentProcessingJob` in `PENDING` state; worker reconciles on reconnect. | System error log with structured JSON; no orphaned tasks |
| **6. Worker Crash** | `SCANNING` / `PROMOTION_PENDING` | `PROMOTION_PENDING` or `SCANNING` | Yes (Celery `acks_late=True` or periodic reconciliation task) | No | Storage promotion checks if safe destination already exists before re-copying. Safe state NOT set until DB commit succeeds. | Structured task crash log; execution marked `CRASHED`/`RETRY` in `DocumentJobExecution` |
| **7. Storage Unavailable** | `PROMOTION_PENDING` / `SCANNING` | `SCANNING` / `RECONCILIATION_REQUIRED` | Yes (transient retry, up to 3 attempts) | Yes, if storage persists down | None. Document prevented from false `SAFE` state; stays in quarantine storage. | `celery_task_execution` log with `PROMOTION_ERROR`; job marked `FAILED` |
| **8. Database Rollback** | `UPLOADING` | Unchanged (No DB record created) | No (HTTP request fails with transaction error) | No | Quarantine payload orphaned in quarantine directory is garbage-collected by periodic quarantine purge script. | None (transaction rolled back atomically) |
| **9. Duplicate Task Delivery** | `SAFE` | `SAFE` (No change) | No (idempotent short-circuit) | No | Second execution detects `lifecycle_status == SAFE` and immediately returns without duplicate promotion or manifest. | `celery_task_execution` logged with idempotent skip; no duplicate `DOCUMENT_PROMOTED` event |
| **10. Concurrent Worker Processing** | `QUARANTINED` / `SCANNING` | `SAFE` (Exactly one worker promotes) | No (serialized via row lock) | No | PostgreSQL `SELECT FOR UPDATE` serializes the workers. Worker 1 promotes; Worker 2 observes `SAFE` and safely returns. | Exactly 1 `DOCUMENT_PROMOTED` event; exactly 1 `DocumentManifest` record |
| **11. Manifest Creation Failure** | `PROMOTION_PENDING` | `SCANNING` / `RECONCILIATION_REQUIRED` | Yes (retry transaction) | Yes, if DB constraints violated | Database transaction rolls back; document does NOT become `SAFE`. | Transaction exception logged; execution marked `FAILED` in `DocumentJobExecution` |

---

## 3. Detailed Failure Mode Specifications

### 3.1 Invalid MIME & Extension Spoofing
- **Trigger**: Applicant uploads a file named `marksheet.pdf` whose magic bytes indicate an executable (`MZ`), ZIP archive (`PK`), script (`<script>`), or unsupported binary.
- **Handling**: `FileContentDetector.detect_mime()` rejects hazardous binaries in the preliminary boundary check. If passed to worker, `DocumentSecurityValidator.validate_file()` verifies magic bytes match declared extension.
- **Outcome**: `ApplicantDocument.lifecycle_status` becomes `REJECTED`, `content_validation_status` becomes `INVALID`.

### 3.2 Malformed or Exploit PDF
- **Trigger**: Truncated PDF missing `%%EOF`, missing PDF header, encrypted PDF without key, or PDF containing exploit streams (`/JavaScript`, `/Launch`, `/EmbeddedFiles`).
- **Handling**: `PdfSecurityValidator.validate_pdf()` scans the document token stream.
- **Outcome**: `REJECTED` with specific error code (e.g. `PDF_JS_DETECTED`, `PDF_LAUNCH_ACTION_DETECTED`).

### 3.3 Malware Scanner Unavailable (Daemon Down / Socket Timeout)
- **Trigger**: The ClamAV TCP daemon (`clamd`) on `127.0.0.1:3310` is unresponsive or network socket times out.
- **Handling**: `ClamAVScanner.scan()` catches `socket.error` and returns `(MalwareScanStatus.ERROR, "ClamAV daemon unreachable")`.
- **Safety Invariant**: Under NO circumstances does scanner failure result in `SAFE`. Document enters `QUARANTINED` with `rejection_reason = "SCAN_ERROR: ..."`. Celery schedules exponential retry.

### 3.4 Malware Detection & Quarantine Retention
- **Trigger**: Binary contains known virus signatures (tested via EICAR test signature).
- **Handling**: `scan()` returns `MalwareScanStatus.INFECTED`. Document is set to `REJECTED`.
- **Retention Policy**: In compliance with security and forensics standards, the infected payload is NOT immediately deleted. A `SecurityQuarantineRecord` is created linking `document`, `detection_result`, `scanner`, `detected_at`, `retention_until` (now + 30 days default), and `deletion_status='RETAINED'`.

### 3.5 Redis Broker Interruption
- **Trigger**: Redis broker crashes or network connection is severed.
- **Handling**: Celery tasks are dispatched via `transaction.on_commit()`. If Redis is down, task submission raises `ConnectionError`. The database state retains `DocumentProcessingJob(status=PENDING)`. When Redis recovers, a reconciliation command or client reconnect resumes queueing.

### 3.6 Worker Crash During Execution
- **Trigger**: Worker process terminated (SIGKILL / OOM / crash) between storage copy and DB manifest insertion.
- **Handling**: The document remains in `PROMOTION_PENDING` or `SCANNING`. On retry, `LocalObjectStorage.promote_to_safe()` checks if the target safe file was already copied in the prior attempt and reuses it without failing. The database transaction then cleanly creates `DocumentManifest` and updates `ApplicantDocument` to `SAFE`.

### 3.7 Storage Promotion Failure
- **Trigger**: Local disk full, permission denied, or target directory unwritable.
- **Handling**: `promote_to_safe()` raises `OSError`. `process_document()` catches exception, marks `DocumentProcessingJob.status = FAILED`, error code `PROMOTION_ERROR`, and leaves document in `SCANNING` or `RECONCILIATION_REQUIRED`. Document NEVER falsely becomes `SAFE`.

### 3.8 Database Transaction Rollback
- **Trigger**: Unhandled exception during upload transaction before commit.
- **Handling**: Because tasks are bound to `transaction.on_commit()`, no Celery task is ever placed on the Redis broker if the database transaction rolls back.

### 3.9 Duplicate Task Delivery
- **Trigger**: Redis broker redelivers message due to visibility timeout or network retry.
- **Handling**: `process_document()` acquires row lock `select_for_update()`. If `doc.lifecycle_status` is already `SAFE`, `REJECTED`, `VERIFIED`, or `REVOKED`, it exits immediately. No duplicate manifests or promotion events are produced.

### 3.10 Concurrent Worker Race
- **Trigger**: Two workers receive tasks for the same document version simultaneously.
- **Handling**: The first worker acquires row lock on `ApplicantDocument`. The second worker blocks. When worker 1 commits `SAFE`, worker 2 resumes, detects `doc.lifecycle_status == SAFE`, and short-circuits.

### 3.11 Manifest Creation Failure
- **Trigger**: Unique constraint or integrity failure during `DocumentManifest.objects.create()`.
- **Handling**: Manifest table is append-only and strictly immutable. Any database constraint failure rolls back the entire transaction, preventing the document from being marked `SAFE`.

---

## 4. Observability & Audit Log Schema

Every transition and failure emits a structured JSON log and an immutable `AuditLog` entry.

### 4.1 Structured Worker Log Format
```json
{
  "event_type": "celery_task_execution",
  "correlation_id": "CORR-01923485-abc123",
  "document_id": "7132f291-1bf0-4e38-946d-06b1a76d2b5f",
  "job_id": "84812301-44ab-45bc-9182-123456789abc",
  "task_id": "2a41efb0-4d0c-4b49-ad4c-75b9fa09082f",
  "job_type": "SECURITY_SCAN",
  "attempt": 1,
  "duration_ms": 142.50,
  "result_status": "SUCCESS"
}
```

### 4.2 Prohibited Log Attributes
In strict accordance with government security and data privacy mandates (DPDP Act / IT Act), the following attributes are NEVER written to logs or correlation tokens:
- Raw document binary bytes
- OCR extracted text / transcriptions
- Passwords or authentication credentials
- API tokens / session cookies
- Aadhaar numbers (masked or unmasked)
- Bank account / IFSC details
- Passport or Certificate identification numbers
