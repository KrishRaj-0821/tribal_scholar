# SECURE OCR FAILURE MATRIX & RESILIENCY SPECIFICATION

This matrix defines the complete failure handling semantics, error codes, retry behavior, and audit trails for the Secure OCR Foundation.

---

## 1. Core Resiliency Principle

> **INVARIANT:**  
> An OCR failure or rendering issue is a processing exception, NOT a malware event or an eligibility rejection.  
> If an OCR worker fails, crashes, or encounters an unreadable file, the `ApplicantDocument.lifecycle_status` **MUST REMAIN `SAFE`**.  
> The system must NEVER convert an OCR failure into an automatic applicant rejection.

---

## 2. Comprehensive OCR Failure Matrix

| Failure Mode | Failure Code | Root Cause / Trigger | OCRJob State | Retried? | Document Status | Application State | Audit Event Emitted | Action Required |
|---|---|---|---|---|---|---|---|---|
| **Non-SAFE Document Entry** | `INVALID_DOCUMENT_LIFECYCLE_STATE` | Attempt to run OCR on document in QUARANTINED, SCANNING, or REJECTED status | Rejected before Job creation | No | Unchanged | Unchanged | None | Enforce service guard |
| **Malformed / Corrupted PDF** | `CORRUPT_OR_MALFORMED_PDF` | PDF stream has truncated xref, invalid header, or damaged stream | `FAILED` | No (permanent file error) | **SAFE** (Preserved) | Unchanged | `OCR_FAILED` | Flag for manual officer review |
| **Empty Document** | `EMPTY_DOCUMENT` / `EMPTY_PDF` | 0-byte file payload or 0-page PDF document | `FAILED` | No | **SAFE** | Unchanged | `OCR_FAILED` | Officer requests document re-upload |
| **Unsupported MIME Format** | `UNSUPPORTED_DOCUMENT_FORMAT` | File is a text or binary format not supported by image renderer | `FAILED` | No | **SAFE** | Unchanged | `OCR_FAILED` | System alert |
| **Max Page Ceiling Exceeded** | `MAX_PAGE_COUNT_EXCEEDED` | PDF page count > `MAX_OCR_PAGES` (default: 10 pages) | `FAILED` | No | **SAFE** | Unchanged | `OCR_FAILED` | Route to human verification |
| **Cumulative Pixels Exceeded** | `MAX_TOTAL_PIXELS_EXCEEDED` | Total rendered pixels across all pages > 25,000,000 px | `FAILED` | No | **SAFE** | Unchanged | `OCR_FAILED` | Prevent decompression-bomb worker hang |
| **Worker Subprocess Crash** | `WORKER_KILLED` / `LOST_WORKER` | Celery worker killed by OS / OOM killer during OCR | `FAILED` (upon recovery) | Yes (up to 3x with backoff) | **SAFE** | Unchanged | `OCR_RETRIED` / `OCR_FAILED` | Celery bounded retry / restart |
| **Redis Connectivity Interruption** | `REDIS_CONNECTION_ERROR` | Temporary network partition between worker and Redis broker | `RETRY_PENDING` | Yes (exponential backoff) | **SAFE** | Unchanged | `OCR_RETRIED` | Automatic Redis reconnect |
| **PostgreSQL Lock Contention** | `LOCK_TIMEOUT` | Concurrent transactions attempting `SELECT FOR UPDATE` on OCRJob | `RETRY_PENDING` | Yes (jittered retry) | **SAFE** | Unchanged | `OCR_RETRIED` | Row lock released upon transaction commit |
| **Duplicate Delivery Race** | `IDEMPOTENT_ALREADY_COMPLETED` | Two workers receive identical job ID from Redis queue | `COMPLETED` | No (early return) | **SAFE** | Unchanged | `OCR_COMPLETED` (single) | Second worker safely observes completed result |
| **Unclassifiable Document** | `DOCUMENT_TYPE_UNKNOWN` | Document text does not match any certificate keyword patterns | `COMPLETED` | No | **SAFE** | Unchanged | `DOCUMENT_CLASSIFIED` | Classified as `UNKNOWN` for manual classification |
| **Material Field Conflict** | `MATERIAL_CONFLICT` | Extracted value differs from applicant declared value by > 5% | `COMPLETED` | No | **SAFE** | `SUBMITTED` / Review | `FIELD_CONFLICT_DETECTED` | Create `VerificationQueueItem` for officer review |
| **Low OCR Confidence** | `LOW_CONFIDENCE_WARNING` | Mean OCR recognition confidence < 0.60 | `COMPLETED` | No | **SAFE** | Unchanged | `OCR_COMPLETED` | Marked provisional; officer review flag set |

---

## 3. State Machine Transitions

```text
[Document Promoted to SAFE]
             │
             ▼
        [ PENDING ] ──(Worker picks up task)──► [ RUNNING ]
                                                     │
               ┌─────────────────────────────────────┼──────────────────────────────────┐
               │                                     │                                  │
      (Success & Persist)                 (Transient Error < 3)               (Permanent Error or
               │                                     │                         Attempts >= 3)
               ▼                                     ▼                                  │
        [ COMPLETED ]                        [ RETRY_PENDING ]                          │
        (Immutable Result)                           │                                  │
                                                     ▼ (Celery Backoff: 2s, 4s, 8s)     │
                                                [ RUNNING ]                             ▼
                                                                                   [ FAILED ]
                                                                             (Document remains SAFE)
```

---

## 4. Resource Ceilings & Protection Protocol

1. **Memory Allocation**: Bitmap buffers from `pypdfium2` are held strictly in local memory and freed after RGB numpy conversion.
2. **Dynamic Downsampling**: Pages exceeding 4,000 pixels in any dimension are automatically downsampled using Lanczos filtering to prevent memory explosion.
3. **Decompression Bomb Shield**: `Image.MAX_IMAGE_PIXELS = 25_000_000` is enforced globally before opening any image payload.
4. **Temporary Files**: Zero sensitive document files are stored on unencrypted temporary disks. All operations occur in in-memory byte streams.

---

## 5. Audit Event Log Specifications

All audit entries use the standard `AuditLog` table:

```json
{
  "actor": null,
  "actor_role": "SYSTEM",
  "entity_type": "ApplicantDocument",
  "entity_id": "<document_uuid>",
  "action": "OCR_FAILED",
  "after_json": {
    "job_id": "<job_uuid>",
    "failure_code": "CORRUPT_OR_MALFORMED_PDF",
    "attempts": 1,
    "correlation_id": "CORR-DOC-001"
  },
  "reason": "Failed to parse PDF: corrupt xref table."
}
```

No PII, passwords, full document content, or raw binaries are recorded in audit logs.
