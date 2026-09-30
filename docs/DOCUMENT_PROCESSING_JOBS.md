# Asynchronous Document Processing Jobs & Celery Boundary

## 1. Job Abstraction Layer

To ensure resilient, observable, and retryable background tasks without blocking HTTP upload requests, processing jobs are tracked via `DocumentProcessingJob`:

```python
class DocumentProcessingJob(models.Model):
    document = models.ForeignKey(ApplicantDocument, on_delete=models.CASCADE, related_name='processing_jobs')
    job_type = models.CharField(max_length=32, choices=DocumentJobType.choices)
    status = models.CharField(max_length=32, choices=DocumentJobStatus.choices, default=DocumentJobStatus.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    error_message = models.TextField(blank=True)
    correlation_id = models.CharField(max_length=128, blank=True, db_index=True)
```

---

## 2. Job Types & Phase Boundaries

| Job Type | Scope for Current Phase | Status |
| :--- | :--- | :--- |
| **`SECURITY_SCAN`** | Magic bytes, antivirus scanning | **IMPLEMENTED** |
| **`CONTENT_VALIDATION`** | PDF syntax, image dimension & raster decode | **IMPLEMENTED** |
| **`OCR`** | Raw optical character recognition | **NOT IMPLEMENTED (Strict Phase Boundary)** |
| **`DOCUMENT_CLASSIFICATION`** | Classification of certificate types | **FUTURE** |
| **`FIELD_EXTRACTION`** | Extraction of income/caste certificate fields | **FUTURE** |
| **`VERIFICATION`** | Trust hierarchy resolution & matching | **FUTURE** |

---

## 3. Celery Asynchronous Boundary & Transactional Safety

### A. The Commit Boundary (`transaction.on_commit`)
Celery background tasks are **never** enqueued directly inside an open database transaction.
```python
# Guaranteed post-commit dispatch
def _dispatch():
    process_document_pipeline_task.delay(str(document.id), correlation_id=correlation_id)

transaction.on_commit(_dispatch)
```
This guarantees that when a Celery worker receives the message, the database row is fully committed and queryable.

### B. Row-Level Locking (`select_for_update()`)
When a Celery worker processes a document, it acquires a PostgreSQL row lock:
```python
with transaction.atomic():
    doc = ApplicantDocument.objects.select_for_update().get(id=document_id)
```
If two workers receive duplicate delivery of the same task, the second worker blocks until the first completes, and then detects that `doc.lifecycle_status == SAFE`, exiting immediately without re-promoting or re-creating manifests.

---

## 4. Idempotency & Failure Handling

### Permanent Failures (No Endless Retries)
- **`INFECTED`**: Job marked `PERMANENT_FAILURE`, quarantine deleted, no retries.
- **`MALFORMED_PDF` / `CONTENT_TYPE_MISMATCH`**: Job marked `PERMANENT_FAILURE`, document rejected.

### Transient Failures (Retry with Exponential Backoff)
- **`SCAN_ERROR` / `STORAGE_ERROR`**: Up to `MAX_PROCESSING_ATTEMPTS` (3 attempts) with exponential backoff delay.
- If attempts exceed limit, job is marked `FAILED` and flagged for administrative reconciliation.

---

## 5. Storage & Database Consistency Strategy

To handle crash failure scenarios:
1. **DB succeeds / storage fails during upload**: Caught synchronously in upload endpoint; transaction rolls back, 0 orphan records.
2. **Quarantine succeeds / DB fails during upload**: Scheduled daily cron scans `quarantine/` for directories without corresponding DB entries older than 2 hours and purges them.
3. **Worker crashes after storage promotion before DB update**:
   - Next retry or reconciliation worker checks if safe storage key exists and SHA-256 matches.
   - If verified, commits `SAFE` status and creates missing manifest.
4. **Duplicate worker execution**:
   - `DocumentManifest` unique constraint on `(document_id, sha256)` prevents duplicate manifests.

---

## 6. Implementation Status Matrix

| Component | Status | Details |
| :--- | :--- | :--- |
| `DocumentProcessingJob` Entity | **IMPLEMENTED** | Tracks job lifecycle, attempts, errors, and correlation IDs |
| Celery Task `process_document_pipeline_task` | **IMPLEMENTED** | Async worker task with retry/backoff for transient failures |
| Idempotency Protection | **IMPLEMENTED** | Row-level locking and status guards prevent duplicate processing |
| Reconciliation-Ready State Flow | **IMPLEMENTED** | Quarantine retention on error allows automated retry/reconciliation |
| OCR Task Pipeline | **FUTURE** | Document OCR processing scheduled for Phase 7 |
| Automated Field Extraction Jobs | **FUTURE** | Extraction pipelines scheduled for Phase 7 |
