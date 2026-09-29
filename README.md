# Tribal Scholar: AI-Enabled Scholarship & Fellowship Management System
### Ministry of Tribal Affairs (MoTA) — SIH Problem Statement 26239

---

## 🏛️ System Overview
The **Tribal Scholar Management System** is a rule-governed, AI-assisted platform engineered for the Ministry of Tribal Affairs (MoTA) to administer central scholarships and fellowships, including:
1. **NFST**: National Fellowship for Higher Education of ST Students
2. **TOP_CLASS**: National Scholarship for Higher Education of ST Students - Top Class Education Scheme
3. **NOS**: National Overseas Scholarship for ST Candidates

---

## 📐 Frozen Architectural Decisions
* **Architecture**: **MODULAR MONOLITH** (No microservices, no Kafka, no Kubernetes, no GraphQL, no MongoDB, no Blockchain).
* **Backend**: Django 5.1, Django REST Framework.
* **Database**: PostgreSQL (Relational schema with JSONB metadata).
* **Async Processing**: Celery + Redis.
* **Object Storage**: MinIO (S3-compatible).
* **Frontend**: React 18, TypeScript, Vite, PWA, Responsive Desktop + Mobile UI.
* **OCR**: PaddleOCR with Tesseract fallback (Assistive only; human review retains statutory authority).
* **Deployment**: Docker Compose.

---

## 🛡️ Core Governance Principles
1. **Zero Hardcoded Eligibility**: Scheme rules reside entirely in database tables (`SchemeRule`) and are never hardcoded inside Python conditionals.
2. **Academic Year Versioning**: Schemes are versioned by academic year (`SchemeVersion`), enabling multi-year coexistence without retroactive invalidation.
3. **Strict Source Provenance**: Every `SchemeRule` and `ReferenceSetItem` must point to an authentic publication (`SourceDocument`) with verified SHA-256 checksums.
4. **Assistive AI Only**: AI assists with OCR, extraction, classification, and anomaly detection. **AI is never the final authority for eligibility, rejection, or selection.**
5. **Deterministic Rule Engine**: Binary eligibility conditions are evaluated deterministically.
6. **Mandatory Human-in-the-Loop**: Ambiguous or low-confidence extractions automatically route to an officer verification queue (`VerificationQueueItem`).
7. **Append-Only Auditing**: `ApplicationStatusHistory` and `AuditLog` records are strictly immutable and append-only.
8. **Synthetic Applicant Data**: Development and testing use synthetic applicant profiles only.
9. **Zero Live Scraping / No Fictitious APIs**: External government integrations (DigiLocker, Aadhaar e-KYC, PFMS, NSP, BHASHINI) are represented strictly through sandboxed interface adapters with deterministic mocks.
10. **Zero Guessing Policy**: When exact criteria have not yet been extracted from an official gazette amendment (such as NOS 2026-27), the rule is marked `PENDING_OFFICIAL_SOURCE_EXTRACTION`.

---

## 🚀 Quickstart & Local Development

### 1. Backend Setup (Virtual Environment)
```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations
python backend/manage.py migrate

# Seed official MoTA schemes (NFST, TOP_CLASS, NOS)
python backend/manage.py seed_schemes

# Validate statutory integrity & provenance
python backend/manage.py validate_schemes

# Run Django development server
python backend/manage.py runserver
```

### 2. Running Test Suite
```bash
pytest backend
```

### 3. Docker Compose Deployment
```bash
docker-compose up --build
```

---

## 📚 Architectural Documentation
* [System Architecture Blueprint](docs/ARCHITECTURE.md)
* [Scheme Configuration & Declarative Rules](docs/SCHEME_CONFIGURATION.md)
* [Source Document Provenance Registry](docs/SOURCE_PROVENANCE.md)
* [Workflow Engine & State Machine](docs/WORKFLOW_ENGINE.md)
