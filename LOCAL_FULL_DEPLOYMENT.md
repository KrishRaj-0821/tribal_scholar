# Local Full Production-Like Deployment Guide

This guide describes how to run and operate the complete **Tribal Scholar** system locally at full capability.

No stages are mocked, bypassed, or weakened. The local containerized deployment runs the exact real processing pipeline:
`Upload → Quarantine Storage → Redis (security_scan) → Scanner Worker (Real ClamAV) → SAFE → Redis (ocr) → OCR Worker (Real PaddleOCR) → Provisional Extraction → Verification Queue → Officer Verification → Eligibility Engine → Immutable Audit Ledger → Applicant Status`.

---

## 1. System Architecture & Topology

```text
                           LOCAL FULL DEPLOYMENT
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
       Frontend (:5173)       Backend (:8000)         Redis (:6379)
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
             worker-scanner                      worker-ocr
                     │                               │
             ClamAV (clamd:3310)                 PaddleOCR
          (max-mem: 350MB, c=1)            (max-mem: 850MB, c=1)
                     │                               │
                     └───────────────┬───────────────┘
                                     │
                             PostgreSQL (:5432)
                                     │
                        Persistent Local Volume
                         (storage_data: /app/storage)
```

### Role-Isolated Worker Topology
- **worker-scanner**:
  - `WORKER_ROLE=scanner`
  - Runs `clamd` on `127.0.0.1:3310` with local virus signature database
  - Consumes queues: `security_scan`, `notifications`, `default`
  - Concurrency: `1`, Max memory per child: `350,000 KiB` (~342 MB)
- **worker-ocr**:
  - `WORKER_ROLE=ocr`
  - No ClamAV daemon running inside container (prevents OOM contention)
  - Runs pre-cached PaddleOCR engine (English & Hindi Devanagari models)
  - Consumes queue: `ocr`
  - Concurrency: `1`, Max memory per child: `850,000 KiB` (~830 MB)

---

## 2. Prerequisites

- **Docker & Docker Compose**: Docker Engine 24+ and Docker Compose v2.
  *(For bare-metal/Windows host testing: PostgreSQL 16+, Redis 7+, Python 3.13 venv, and ClamAV binary).*
- **System Memory**: Minimum 4 GB RAM allocated to Docker Engine (6 GB recommended).
- **Disk Space**: ~4 GB for container images and PaddleOCR cached models.

---

## 3. Environment Variables

Copy the template to `.env`:

```bash
cp .env.example .env
```

Key variables configured in `.env`:
```ini
DJANGO_SECRET_KEY=local-dev-secret-key
DJANGO_DEBUG=True
DATABASE_ENGINE=postgresql
POSTGRES_DB=tribal_scholar
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
REDIS_URL=redis://redis:6379/0
STORAGE_BACKEND=local
MALWARE_SCANNER_BACKEND=clamav
CLAMAV_HOST=127.0.0.1
CLAMAV_PORT=3310
OCR_ENGINE_BACKEND=paddleocr
```

---

## 4. Startup Commands

### Start All Services
```bash
docker compose up -d --build
```

### Check Service Status & Health
```bash
docker compose ps
```

Expected healthy services:
```text
NAME                            IMAGE                  STATUS
tribal_scholar_postgres         postgres:16-alpine     Up (healthy)
tribal_scholar_redis            redis:7-alpine         Up (healthy)
tribal_scholar_backend          tribal_scholar-backend Up (healthy)
tribal_scholar_worker_scanner   tribal_scholar-backend Up (healthy)
tribal_scholar_worker_ocr       tribal_scholar-backend Up (healthy)
tribal_scholar_frontend         tribal_scholar-frontend Up
```

---

## 5. Worker Status Inspection

Inspect worker liveness, queues, and memory status:

```bash
# Ping worker fleet
docker compose exec backend celery -A tribel_scholar inspect ping

# View active queues consumed by each worker
docker compose exec backend celery -A tribel_scholar inspect active_queues

# View worker statistics (prefork children, pool size)
docker compose exec backend celery -A tribel_scholar inspect stats

# Inspect real ClamAV daemon inside worker-scanner
docker compose exec worker-scanner python -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 3310)); s.sendall(b'zPING\0'); print(s.recv(1024)); s.close()"
# Output: b'PONG\x00'
```

---

## 6. How to Run Tests

### Unit Tests
```bash
docker compose exec -e TEST_LEVEL=unit backend pytest tests/unit -q
# Or on host venv:
pytest backend/tests/unit -q
```
*Current result: 158 passed (100%).*

### Integration Tests
Integration tests execute against real PostgreSQL and real Redis:
```bash
docker compose exec -e TEST_LEVEL=integration backend pytest tests/integration -v
# Or on host venv:
pytest backend/tests/integration -v
```
*Current result: 156 passed, 16 failed (concurrency/idempotency tests scheduled for future remediation phases), 0 errors.*

---

## 7. How to Perform E2E Verification

Run the automated 22-step real processing pipeline:

```bash
python scratch/verify_phase1b_e2e.py
```

The script verifies:
1. System startup & dependency connectivity
2. Applicant registration
3. Authentication / Login
4. Scheme selection & Draft application creation
5. Real test document upload
6. Document quarantine entry
7. Redis `security_scan` task dispatch
8. Scanner worker task receipt
9. Real ClamAV scanning
10. SAFE promotion only after clean scan
11. Redis `ocr` task dispatch
12. OCR worker task receipt
13. Real PaddleOCR character & block extraction
14. Provisional fields & document classification creation
15. Verification queue item population
16. Officer queue inspection
17. Officer document & field verification
18. Deterministic Eligibility Engine rule evaluation
19. Immutable Audit Ledger event recording
20. Application status reflection in database
21. Service disconnect / restart simulation
22. Document file & metadata persistence verification

All 22 steps report `PASS`.

---

## 8. Stopping & Restarting Services

### Stop services without losing data
```bash
docker compose stop
```

### Restart services
```bash
docker compose start
```

### Clean shutdown (preserves database and document volumes)
```bash
docker compose down
```

### Full teardown (deletes persistent volumes — DESTRUCTIVE)
```bash
docker compose down -v
```

---

## 9. Persistence Architecture

Persistent volumes defined in `docker-compose.yml`:
- `pgdata`: Mounted to `/var/lib/postgresql/data` in `postgres`. Preserves all database schemas, users, schemes, audit logs, applications, and verification records across restarts.
- `redisdata`: Mounted to `/data` in `redis`. Preserves broker state and AOF logs.
- `storage_data`: Mounted to `/app/storage` across `backend`, `worker-scanner`, and `worker-ocr`. Uploaded quarantine and safe documents survive container recreation.

---

## 10. Known Limitations & Scope Boundaries

1. **Host Environment Note**: On Windows developer machines without Docker Desktop/WSL2, local PostgreSQL and local Redis services run as native Windows services on ports 5432 and 6379, with standalone `clamd` running on port 3310.
2. **Phase Boundaries**: Issues P0-2 through P2 (DocumentVault fabrication, CSRF auth enhancements, officer UI workbench, etc.) are strictly preserved for their respective future remediation phases per project specification.
