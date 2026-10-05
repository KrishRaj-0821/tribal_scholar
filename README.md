# 🏛️ Tribal Scholar: AI-Enabled National Scholarship & Fellowship Management System
### Ministry of Tribal Affairs (MoTA), Government of India — Smart India Hackathon (SIH Problem Statement 26239)

[![Deployment Status](https://img.shields.io/badge/Deployment-Live%20on%20Railway-success?style=for-the-badge&logo=railway)](https://tribalscholar.up.railway.app)
[![API Health](https://img.shields.io/badge/Backend%20API-Online%20(HTTP%20200)-blue?style=for-the-badge&logo=django)](https://backend-production-ba69a.up.railway.app/health/live/)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript%20%2B%20PWA-61DAFB?style=for-the-badge&logo=react)](https://tribalscholar.up.railway.app)
[![Backend](https://img.shields.io/badge/Backend-Django%205.1%20%2B%20DRF-092E20?style=for-the-badge&logo=django)](https://backend-production-ba69a.up.railway.app)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Async](https://img.shields.io/badge/Async%20Worker-Celery%20%2B%20Redis-37814A?style=for-the-badge&logo=celery)](https://docs.celeryq.dev/)
[![Compliance](https://img.shields.io/badge/Accessibility-GIGW%203.0%20%2F%20WCAG%202.1%20AA-orange?style=for-the-badge)](https://guidelines.india.gov.in/)

---

## 🌐 Live Production Deployment Links

| Resource | Target URL | Description & Health Status |
| :--- | :--- | :--- |
| **🚀 Public Portal (PWA)** | [https://tribalscholar.up.railway.app](https://tribalscholar.up.railway.app) | Production Progressive Web App for Scheduled Tribe applicants & scrutiny officers |
| **⚡ Authoritative Backend API** | [https://backend-production-ba69a.up.railway.app/api/v1/](https://backend-production-ba69a.up.railway.app/api/v1/) | Central REST API root with JSON schema contracts |
| **💚 Liveness Health Probe** | [https://backend-production-ba69a.up.railway.app/health/live/](https://backend-production-ba69a.up.railway.app/health/live/) | Monitored uptime probe (`HTTP 200 OK`) |
| **🩺 Readiness Health Probe** | [https://backend-production-ba69a.up.railway.app/health/ready/](https://backend-production-ba69a.up.railway.app/health/ready/) | Database, cache & worker connectivity readiness check |
| **📜 Schemes Directory API** | [https://backend-production-ba69a.up.railway.app/api/v1/schemes/](https://backend-production-ba69a.up.railway.app/api/v1/schemes/) | Real-time statutory rules and quota listings |
| **📋 End-to-End QA Report** | [docs/LIVE_APPLICATION_QA_REPORT.md](docs/LIVE_APPLICATION_QA_REPORT.md) | Verified audit with real telecom SMS dispatch & OCR telemetry |

---

## 👥 Instant Evaluation & Demo Personas

For evaluators, jury members, and reviewers, the live deployment contains pre-seeded synthetic personas to test both student application and officer scrutiny workflows immediately:

| Role | Username | Password | Key Workflows & Permissions |
| :--- | :--- | :--- | :--- |
| **🎓 ST Student Applicant** | `demo_applicant` | `Tribal@2026` | Sovereign OTR profile, Scheme Discovery, Multi-Step Application Wizard, Document Vault with ClamAV status, Live SMS Audit Ledger |
| **🛡️ District Scrutiny Officer** | `demo_officer` | `Officer@2026` | Scrutiny Desk (`/officer`), Priority Triage Queue (SLA countdowns, conflict alerts), Side-by-Side Verification Workbench with original certificate canvas & bounding box overlays |

> **Direct Mobile OTP Testing**: The portal supports live telecom SMS authentication powered by the Fast2SMS gateway. Register with any valid 10-digit Indian mobile number to receive live real-time OTPs and statutory SMS dispatch receipts.

---

## 📖 Executive Summary & Problem Context

The **Ministry of Tribal Affairs (MoTA)** oversees the socio-economic empowerment of India's Scheduled Tribes (ST). While flagship scholarship schemes provide critical financial lifelines, traditional delivery pipelines face substantial administrative hurdles:
- **Disparate verification bottlenecks** across district and state welfare desks.
- **Complex statutory criteria** (income ceilings, course eligibility, institution empanelment, academic year rule mutations).
- **High vulnerability to document fraud** and certificate spoofing.
- **Lack of affirmative action transparency** and real-time beneficiary tracking.

**Tribal Scholar** addresses **SIH Problem Statement 26239** by delivering an enterprise-grade, rule-governed, AI-assisted sovereign portal. It unifies the entire scholarship lifecycle—from one-time registration and scheme-matching to OCR document intelligence, antivirus quarantine, deterministic statutory rule evaluation, officer scrutiny, and direct telecom SMS notifications.

---

## 🏛️ Flagship Statutory Schemes Administered

The platform natively supports the official guidelines and gazette notifications for MoTA's primary schemes:

1. **NFST (National Fellowship for Higher Education of ST Students)**
   - Full financial assistance to ST candidates pursuing regular M.Phil. and Ph.D. degrees in Sciences, Humanities, Engineering, and Technology.
2. **TOP_CLASS (Top Class Education Scheme for ST Students)**
   - Full tuition fee coverage and living allowances across premier institutes (IITs, IIMs, NITs, AIIMS, NLUs).
3. **NOS (National Overseas Scholarship for ST Candidates)**
   - Financial support for meritorious ST scholars admitted to top QS/Times Higher Education ranked international universities for Master's and Ph.D. programs.
4. **Pre-Matric & Post-Matric ST Scholarships**
   - Inter-state welfare schemes supporting secondary and higher secondary tribal education with Direct Benefit Transfer (DBT) readiness.

---

## ⚡ Core Innovations & Capabilities

### 1. 🤖 Assistive AI & Dual-Engine Document Intelligence
- **PaddleOCR + Tesseract Fallback**: Robust dual-engine optical character recognition tuned for bilingual Indian certificates (Devanagari script + English).
- **Assistive AI Boundary**: AI models extract data (income, caste certificate number, issuing authority, dates) with confidence scoring. **Crucially, AI never has final rejection or selection authority**; ambiguous or low-confidence readings automatically trigger human-in-the-loop review.
- **Field Conflict Resolution**: Visual bounding boxes map extracted values against user-declared values on an interactive side-by-side canvas for scrutiny officers.

### 2. 🛡️ Enterprise Security & ClamAV Antivirus Quarantine
- **Zero-Trust Document Pipeline**: All uploaded certificates enter an isolated `QUARANTINED` state.
- **Live Antivirus Scanning**: Integrates ClamAV daemon to inspect uploaded files for malware, macros, and malicious payloads before safe-storage promotion.
- **Tamper-Resistant SHA-256 Hashing**: Every document and statutory gazette is fingerprinted with cryptographic checksums for immutable provenance tracking.
- **PII Masking & IDOR Protection**: Sensitive personal identity markers (Aadhaar, phone numbers) are masked (`******1902`) across UI and API layers. Strict tenancy isolation prevents unauthorized dossier access.

### 3. ⚖️ Declarative Zero-Hardcoding Rule Engine
- **No Hardcoded Conditionals**: Eligibility criteria reside dynamically in database tables (`SchemeRule`), never inside brittle Python `if/else` conditionals.
- **Academic Year Versioning**: Multi-year schemes coexist without retroactive invalidation. Rules are versioned per academic year (`2024-25`, `2025-26`, `2026-27`).
- **Cryptographic Source Provenance**: Every rule links directly to an authentic official publication (`SourceDocument`) with page-level statutory citations.

### 4. 📲 Real-Time Indian Telecom SMS Notifications (Fast2SMS Gateway)
- **Direct Citizen Alerts**: Application submission, status transitions, query requests, and OTP authentications dispatch real transactional SMS messages via Indian telecom routes (headers e.g., `57575711`).
- **Truthful Delivery Status Tracking**: Decouples provider acceptance (`SENT_TO_PROVIDER`) from true carrier delivery (`DELIVERED`) to guarantee complete telemetry honesty.
- **Asynchronous Task Queue**: Dispatches are executed off the HTTP critical path via Celery workers with automated retry policies.

### 5. 🔍 District Scrutiny Desk & Officer Verification Workbench
- **Priority Triage Queue**: Intelligent workload sorting based on statutory SLAs, pending deadlines, and flagged discrepancies.
- **Interactive Verification Workbench**: Officers view high-resolution certificate scans side-by-side with OCR bounding boxes, allowing one-click decisions: *Accept Document Value*, *Keep Declared*, *Request Evidence*, or *Escalate*.
- **Append-Only Immutable Audit Log**: Every administrative action, view, and status update writes to a cryptographically indexed, append-only ledger (`AuditLog`).

### 6. ♿ GIGW 3.0 Compliance & Offline-First PWA
- **Accessibility by Design**: Fully compliant with the Guidelines for Indian Government Websites (GIGW 3.0) and WCAG 2.1 AA standards. Includes high-contrast modes, text resizer, keyboard navigation, and screen reader ARIA landmarks.
- **Bilingual Experience**: Instant switching between Hindi (हिंदी) and English.
- **Offline Resilience**: Built with Vite + Workbox Progressive Web App service workers for reliable offline caching and low-bandwidth rural connectivity.

---

## 📐 Architecture & Technology Stack

The system is engineered as a **Modular Monolith** to guarantee ACID transactional consistency, eliminate distributed microservice overhead, and maintain sovereign data integrity.

```
+---------------------------------------------------------------------------------------+
|                                    TRIBAL SCHOLAR                                    |
|                              (Modular Monolith Backend)                               |
+---------------------------------------------------------------------------------------+
|  +----------------+  +----------------+  +----------------+  +---------------------+  |
|  |    accounts    |  |   applicants   |  |     schemes    |  |     documents       |  |
|  | (RBAC & Auth)  |  | (Profiles/PII) |  | (Rules/RefSets)|  | (Provenance/Source) |  |
|  +----------------+  +----------------+  +----------------+  +---------------------+  |
|  +----------------+  +----------------+  +----------------+  +---------------------+  |
|  |  applications  |  |    workflow    |  |  verification  |  |    notifications    |  |
|  | (Lifecycle/App)|  | (State Engine) |  | (Human Review) |  | (Async Dispatch)    |  |
|  +----------------+  +----------------+  +----------------+  +---------------------+  |
|  +----------------+  +-------------------------------------------------------------+  |
|  |     audit      |  |                        integrations                         |  |
|  | (Append-Only)  |  | (Mock/Adapter Boundary: DigiLocker, PFMS, NSP, MoTA, Aadhaar)|  |
|  +----------------+  +-------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
        |                        |                             |
+----------------+       +---------------+             +----------------+
|   PostgreSQL   |       | Redis/Celery  |             |  Storage Layer |
| (PostgreSQL 16)|       | (Worker 5.4)  |             | (MinIO / S3)   |
+----------------+       +---------------+             +----------------+
```

### Technology Matrix

| Layer | Technology | Function & Purpose |
| :--- | :--- | :--- |
| **Frontend PWA** | React 18, TypeScript, Vite, Tailwind CSS | High-performance responsive single page application, PWA Service Worker caching |
| **Icons & UI** | Lucide React, Custom Tribal Motifs | GIGW compliant design system with sovereign Indian national aesthetics |
| **Backend API** | Python 3.13, Django 5.1, Django REST Framework | Robust business logic, declarative serializers, and ORM transaction safety |
| **Database** | PostgreSQL 16 | Relational data integrity, foreign key cascades, and JSONB rule configurations |
| **Async Tasks & Broker** | Celery 5.4 + Redis 7.2 | Decoupled OCR processing, antivirus inspection, and SMS dispatching |
| **Document Intelligence** | PaddleOCR 3.7 + Tesseract fallback | Dual-engine OCR with Devanagari script extraction and bounding box geometry |
| **Malware Defense** | ClamAV Daemon | Real-time antivirus quarantine and file sanitization |
| **SMS Gateway** | Fast2SMS Quick SMS API | Real Indian telecom SMS dispatching with carrier header routing |
| **Web Server & WSGI** | Gunicorn 23.0 + WhiteNoise 6.8 | Production WSGI application server with optimized static caching |
| **Cloud Infrastructure** | Railway PaaS | Continuous automated deployment with dedicated worker egress |

---

## 📁 Repository Structure

```
Tribel_Scholor/
├── .railway/                     # Railway Infrastructure-as-Code definitions
├── backend/                      # Django Modular Monolith Backend
│   ├── apps/
│   │   ├── accounts/             # RBAC, Authentication, Custom User model
│   │   ├── applicants/           # Profile management, PII masking, caste validation
│   │   ├── applications/         # Application lifecycle aggregate root
│   │   ├── audit/                # Append-only tamper-resistant audit ledger
│   │   ├── core/                 # Shared base models, validators, and exceptions
│   │   ├── documents/            # Document vault, provenance tracking, SHA-256 checks
│   │   ├── integrations/         # Government sandbox adapters (DigiLocker, PFMS, NSP)
│   │   ├── notifications/        # Celery-driven notification engine & Fast2SMS provider
│   │   ├── schemes/              # SchemeRule, SchemeVersion, Quota, ReferenceSets
│   │   ├── verification/         # Officer scrutiny triage queue & demo services
│   │   └── workflow/             # State machine engine & status transition history
│   ├── tribel_scholar/           # Django settings, WSGI, ASGI, and root routing
│   ├── tests/                    # 300+ integration, concurrency, and unit test suites
│   ├── Dockerfile                # Production backend container definition
│   ├── requirements.txt          # Python dependencies
│   ├── start.sh                  # Railway container boot script (migrate + seed + run)
│   └── manage.py                 # Django management interface
├── frontend/                     # React + TypeScript + Vite PWA
│   ├── public/                   # Static assets, web manifest, and national emblems
│   ├── src/
│   │   ├── components/           # UI components, GIGW accessibility toolbar, views
│   │   │   ├── views/            # Portal Home, Dashboard, Officer Desk, Application Wizard
│   │   │   └── common/           # Tribal motifs, headers, footers, badges
│   │   ├── context/              # AuthContext, LanguageContext (English/Hindi)
│   │   ├── services/             # Authoritative API client (`api.ts`)
│   │   └── types/                # TypeScript interfaces and scheme schemas
│   ├── Dockerfile                # Production multi-stage Nginx container
│   ├── nginx.conf.template       # Production Nginx reverse proxy configuration
│   └── vite.config.ts            # Vite build setup with Workbox PWA plugin
├── docs/                         # 30+ Architectural blueprints and audit specifications
│   ├── ARCHITECTURE.md           # Master architectural blueprint
│   ├── LIVE_APPLICATION_QA_REPORT.md # Live production test verification audit
│   ├── SCHEME_CONFIGURATION.md   # Declarative rule engine specification
│   ├── RAILWAY_DEPLOYMENT.md     # Cloud provisioning and environment variables
│   └── WORKFLOW_ENGINE.md        # State transition formal definition
├── docker-compose.yml            # Local multi-service orchestration
└── README.md                     # Project documentation & entry point
```

---

## 🚀 Quickstart & Local Development

### Prerequisites
- **Python**: 3.11+ (Python 3.12 or 3.13 recommended)
- **Node.js**: 18.x or 20.x
- **PostgreSQL**: 15+ (or Docker)
- **Redis**: 7.x (or Docker)

### 1. Backend Setup

```bash
# 1. Clone the repository
git clone https://github.com/KrishRaj-0821/tribal_scholar.git
cd tribal_scholar

# 2. Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# 3. Install backend dependencies
pip install -r backend/requirements.txt

# 4. Configure local environment variables
cp .env.example backend/.env
# Edit backend/.env to set your local DB connection string (or use default SQLite for quick preview)

# 5. Execute migrations
python backend/manage.py migrate

# 6. Seed statutory schemes and synthetic demo scenarios
python backend/manage.py seed_schemes
python backend/manage.py validate_schemes
python backend/manage.py seed_demo_scenario

# 7. Start the backend development server
python backend/manage.py runserver 8000
```

### 2. Frontend Setup

```bash
# In a new terminal window:
cd frontend

# 1. Install dependencies
npm install

# 2. Start Vite development server
npm run dev
```

The frontend will be accessible at `http://localhost:5173` and will automatically proxy API requests to `http://localhost:8000`.

### 3. Optional: Background Celery Worker

For async OCR and SMS task testing:

```bash
# In an activated virtual environment:
celery -A tribel_scholar worker --loglevel=info
```

### 4. Docker Compose (Full Stack with one command)

```bash
docker-compose up --build
```

---

## ☁️ Production Railway Deployment

The repository includes ready-to-deploy configurations for **Railway**:

1. **Backend Service**: Uses `Dockerfile.backend` (or `backend/Dockerfile`), starts via `/app/start.sh` which executes zero-downtime database migrations, statutory scheme validation, static asset collection, and Gunicorn initialization.
2. **Frontend Service**: Uses `frontend/Dockerfile` with multi-stage Node build and Nginx runtime serving the optimized PWA bundle.
3. **Managed Plugins**: Provision PostgreSQL and Redis directly from the Railway dashboard.
4. **Environment Variables**: See [docs/RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md) for full variable mappings.

---

## 🧪 Testing & Quality Assurance

The codebase contains a comprehensive test suite covering unit, integration, and security specifications:

```bash
# Run backend test suite
pytest backend

# Run with coverage report
pytest backend --cov=apps
```

### Test Coverage Highlights:
- **Statutory Rule Integrity**: Asserts that NFST, TOP_CLASS, and NOS rules match official gazette parameters without drift.
- **Concurrency & Stress**: Verifies atomic lock protections during simultaneous application submissions.
- **IDOR & Tenancy Isolation**: Verifies that students cannot access foreign dossiers or administrative verification workbenches.
- **Malware Interception**: Confirms malicious file payloads are quarantined by the ClamAV gate.
- **Live QA Audit**: See [docs/LIVE_APPLICATION_QA_REPORT.md](docs/LIVE_APPLICATION_QA_REPORT.md) for real browser automation and telecom test evidence.

---

## 📜 Ten Principles of Sovereign Scheme Governance

1. **Zero Hardcoded Eligibility**: Scheme rules reside entirely in database models (`SchemeRule`) and are never buried in procedural code.
2. **Academic Year Versioning**: Schemes are versioned per academic year (`SchemeVersion`), preventing retroactive rule invalidation.
3. **Strict Source Provenance**: Every rule points to an authentic gazette publication (`SourceDocument`) verified with SHA-256 checksums.
4. **Assistive AI Boundary**: AI models assist with OCR and anomaly detection. **AI is never the final decision authority for eligibility, rejection, or selection.**
5. **Deterministic Rule Engine**: Binary eligibility conditions are evaluated deterministically with complete audit logs.
6. **Mandatory Human-in-the-Loop**: Discrepancies or low-confidence extractions automatically route to officer scrutiny queues.
7. **Append-Only Auditing**: `ApplicationStatusHistory` and `AuditLog` records are strictly immutable.
8. **Synthetic Applicant Data**: Development, testing, and pitch demonstrations use synthetic profiles only.
9. **Zero Scraping & Sandboxed Adapters**: External government integrations (DigiLocker, Aadhaar, PFMS, NSP, BHASHINI) are cleanly abstracted through standardized interface adapters.
10. **Zero Guessing Policy**: When statutory criteria from future amendments are pending gazette release, rules are explicitly marked `PENDING_OFFICIAL_SOURCE_EXTRACTION`.

---

## 👥 Authors & Acknowledgments

- **Team**: Smart India Hackathon (SIH) Finalists
- **Agency**: Ministry of Tribal Affairs (MoTA), Government of India
- **Problem Statement**: SIH PS 26239 — AI-Enabled Scholarship & Fellowship Management System
- **Repository**: [https://github.com/KrishRaj-0821/tribal_scholar](https://github.com/KrishRaj-0821/tribal_scholar)
- **Live Application**: [https://tribalscholar.up.railway.app](https://tribalscholar.up.railway.app)

---

## 📄 License

This project is developed for the Smart India Hackathon in partnership with the Ministry of Tribal Affairs (MoTA). Released under the [MIT License](LICENSE).
