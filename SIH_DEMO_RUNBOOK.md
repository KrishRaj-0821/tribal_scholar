# Smart India Hackathon (SIH) — Live Demonstration Runbook

## Overview & Architecture Separation

> **IMPORTANT ARCHITECTURAL CLARIFICATION**
> - **LOCAL FULL PRODUCTION-LIKE DEPLOYMENT (DEMO SOURCE OF TRUTH):**
>   The complete production-grade pipeline is validated locally under a decoupled, role-isolated architecture:
>   `Frontend (:5173)` + `Backend (:8000)` + `PostgreSQL (:5432)` + `Redis (:6379)` + `worker-scanner (ClamAV :3310)` + `worker-ocr (PaddleOCR)`.
>   All components are real: live ClamAV stream scanning, real PaddleOCR neural inference, immutable audit logging, and transactional officer verification.
> - **RAILWAY CURRENT DEPLOYMENT:**
>   The current remote Railway deployment does **NOT** host the decoupled multi-worker topology due to resource/topology constraints on the current cloud plan. To prevent OOM crashes and protect system stability, the cloud deployment is intentionally **not** collapsed into an unsafe single worker. The local full environment is the authoritative demonstration target.

---

## 1. System Services & Port Mapping

| Service | Port / Socket | Component / Technology | Operational Role |
| :--- | :--- | :--- | :--- |
| **Frontend** | `http://localhost:5173` | React 18 / Vite / TypeScript | Applicant portal & Officer Verification Workbench |
| **Backend API** | `http://127.0.0.1:8000` | Django 5.1 / DRF / Gunicorn | Core API, scheme engine, auth, audit ledger |
| **Database** | `127.0.0.1:5432` | PostgreSQL 16+ | Persistent ACID relational storage |
| **Message Broker** | `127.0.0.1:6379/0` | Redis 7+ | Asynchronous task queue & cache |
| **Scanner Worker** | Internal Celery | Celery (`worker-scanner`) | Consumes `security_scan,notifications,default` (350MB max mem) |
| **ClamAV Daemon** | `127.0.0.1:3310` | ClamAV (`clamd`) | Real stream anti-malware verification |
| **OCR Worker** | Internal Celery | Celery (`worker-ocr`) | Consumes `ocr` queue (850MB max mem, PaddleOCR models) |

---

## 2. Startup Commands

### Option A: Local Process Startup (Bare-Metal / Development Host)

1. **Start Infrastructure Services:**
   - PostgreSQL running on port `5432` with database `tribal_scholar`.
   - Redis running on port `6379`.
   - ClamAV daemon:
     ```bash
     clamd -c /path/to/clamd.conf
     # Verify daemon responds:
     python -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 3310)); s.sendall(b'zPING\0'); print(s.recv(1024))"
     # Output must be: b'PONG\0'
     ```

2. **Start Backend API:**
   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver 127.0.0.1:8000 --noreload
   ```

3. **Start Role-Isolated Celery Workers (in separate terminals):**
   - **Terminal 1 — Scanner Worker:**
     ```bash
     cd backend
     python -m celery -A tribel_scholar worker --pool=solo -l INFO -Q security_scan,notifications,default -n scanner@localhost
     ```
   - **Terminal 2 — OCR Worker:**
     ```bash
     cd backend
     python -m celery -A tribel_scholar worker --pool=solo -l INFO -Q ocr -n ocr@localhost
     ```

4. **Start Frontend Portal:**
   ```bash
   cd frontend
   npm run dev -- --host 127.0.0.1 --port 5173
   ```

---

### Option B: Docker Compose Full Stack Startup

```bash
docker compose up -d --build
```
Verify health status of all containers:
```bash
docker compose ps
```

---

## 3. End-to-End Demonstration Sequence

The demonstration follows the natural, un-mocked lifecycle:

```text
[Applicant Registration]
        │
        ▼
[Create Application (e.g. TOP_CLASS)]
        │
        ▼
[Upload Revenue/Income Certificate]
        │
        ▼
[Quarantine Storage (quarantine/<uuid>/)] ──► Job: SECURITY_SCAN (Redis: security_scan)
                                                  │
                                                  ▼
                                       [Scanner Worker + ClamAV]
                                                  │
                                         ┌────────┴────────┐
                                      (CLEAN)          (INFECTED)
                                         │                 │
                                         ▼                 ▼
                          [Promote to SAFE Storage]  [Quarantine Retained]
                                         │           [Audit: MALWARE_DETECTED]
                                         ▼
                            Job: OCR (Redis: ocr)
                                         │
                                         ▼
                               [OCR Worker + PaddleOCR]
                                         │
                                         ▼
                         [ProvisionalExtractedField records]
                                         │
                                         ▼
                      [Natural Handoff: VerificationQueueItem]
                                         │
                                         ▼
                      [Officer Scrutiny & Field Reconciliation]
                                         │
                                         ▼
                      [Promoted to OFFICER_VERIFIED (Rank 60)]
                                         │
                                         ▼
                      [Deterministic Eligibility Evaluation]
                                         │
                                         ▼
                      [Application Status: VERIFIED / PASS]
```

### Demonstration Steps

1. **Applicant Registration & Application Initiation:**
   - Navigate to `http://localhost:5173/`.
   - Register a new applicant account and log in.
   - Initiate a new application under a statutory scheme (e.g., *Top Class Education for ST Students*).
   - Enter candidate declarations (e.g., declared income).

2. **Secure Document Ingestion (Quarantine Gate):**
   - Upload a revenue certificate (PDF or PNG).
   - File is immediately placed into isolated quarantine storage.
   - Lifecycle status is `QUARANTINED`, malware status is `NOT_SCANNED`.

3. **Anti-Malware Verification:**
   - `worker-scanner` picks up the task from `security_scan` queue.
   - Streams raw file bytes to local `clamd` on `127.0.0.1:3310`.
   - Clean file is promoted to `SAFE` storage; malware scan status becomes `CLEAN`.
   - Celery automatically enqueues the OCR job to the `ocr` queue.

4. **Multi-Lingual OCR Extraction:**
   - `worker-ocr` picks up the task from `ocr` queue.
   - Executes real PaddleOCR neural model across the document.
   - Provisional extracted fields (income amount, certificate number, authority) are persisted to the database.

5. **Natural Handoff to Verification Queue:**
   - Upon OCR completion, `DocumentVerificationService.enqueue_document_for_verification` executes automatically.
   - Compares declared values against OCR provisional extractions.
   - Creates an active `VerificationQueueItem` with priority and evidence snapshot.
   - Generates immutable `AuditLog` entry.

6. **Officer Scrutiny & Conflict Resolution:**
   - Log in as Scrutiny Officer and navigate to the Officer Workbench.
   - Open the pending case: view side-by-side comparison of declared value vs. OCR provisional value with bounding boxes.
   - Officer accepts, overrides, or resolves discrepancy.
   - Field value is promoted to authoritative trust rank `OFFICER_VERIFIED` (Rank 60).
   - Immutable audit record is stamped.

7. **Eligibility Evaluation & Timeline Verification:**
   - The scheme rule engine evaluates verified evidence deterministically.
   - Applicant views `ApplicantStatusView`: timeline dynamically renders real audit events from `/api/v1/applications/{id}/status-timeline/`.

---

## 4. How to Verify Worker Isolation

### Verify Scanner Worker
- Inspect Celery task registration:
  ```bash
  python -m celery -A tribel_scholar inspect active -d scanner@localhost
  ```
- Confirm it only listens to queues: `security_scan`, `notifications`, `default`.
- Confirm ClamAV is running and reachable on `127.0.0.1:3310`.

### Verify OCR Worker
- Inspect Celery task registration:
  ```bash
  python -m celery -A tribel_scholar inspect active -d ocr@localhost
  ```
- Confirm it only listens to queue: `ocr`.
- Confirm PaddleOCR models are loaded without `clamd` memory contention.

---

## 5. Recovery After Service Restart

If any or all processes (Django, Celery, Vite) are restarted:
1. Verify PostgreSQL and Redis are running.
2. Restart workers and web server using the startup commands in Section 2.
3. Open the browser and refresh the page.
4. **State Persistence:** All applications, uploaded documents, OCR provisional fields, verification queue items, and audit logs are fully persisted in PostgreSQL and immediately restored.

---

## 6. Common Symptoms & Troubleshooting

| Symptom | Root Cause | Resolution |
| :--- | :--- | :--- |
| Document stays `QUARANTINED` / `NOT_SCANNED` | `worker-scanner` is not running or Redis is unreachable. | Check Redis connection and start `worker-scanner`. |
| Scanner reports `MalwareScanStatus.ERROR` | `clamd` daemon is not running on port `3310`. | Start `clamd.exe -c clamd.conf` and verify `PONG` response. The system fails closed safely. |
| OCR extraction does not trigger | Document has not passed malware scan, or `worker-ocr` is not running. | Verify document is `SAFE` and start `worker-ocr` listening to queue `ocr`. |
| Worker crashes with OOM | Both workers running inside a single memory-constrained process. | Run separate worker processes with role-specific memory caps (`--max-memory-per-child`). |
| "Invalid scheme code" HTTP 400 | Application created without valid scheme version or code. | Provide valid scheme code (e.g., `TOP_CLASS` or `NOS`). Arbitrary fallback is disabled. |
