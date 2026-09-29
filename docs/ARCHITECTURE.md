# System Architecture: Tribal Scholar Management System
## MoTA SIH Problem Statement 26239 — Architectural Blueprint

---

### 1. Executive Summary & Purpose
The **Tribal Scholar Management System** is an AI-assisted, rule-governed Scholarship and Fellowship Management platform engineered for the **Ministry of Tribal Affairs (MoTA)**. The system administers high-impact schemes including:
* **NFST** (National Fellowship for Higher Education of ST Students)
* **NOS** (National Overseas Scholarship for ST Candidates)
* **TOP_CLASS** (National Scholarship for Higher Education of ST Students - Top Class Education Scheme)

This implementation serves as the foundational architectural core for the Smart India Hackathon (SIH) prototype.

---

### 2. Core Architectural Philosophy: The Modular Monolith

To avoid the operational pitfalls, distributed transaction complexities, and excessive infrastructure overhead of premature microservices, the system is strictly architected as a **Modular Monolith**.

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
|   PostgreSQL   |       | Redis/Celery  |             |  MinIO Storage |
|  (Relational)  |       | (Async Tasks) |             |  (S3 Compliant)|
+----------------+       +---------------+             +----------------+
```

#### Why Modular Monolith?
1. **Domain Isolation with Zero Network Overhead**: Each module owns its models and services with clear interfaces, yet runs in a single cohesive runtime.
2. **ACID Transactions**: Workflow state transitions and immutable audit logs can be committed atomically within PostgreSQL transactions.
3. **Simplicity in Deployment**: A single containerized backend service running Django 5 + DRF, with Celery worker containers sharing the exact same codebase.

---

### 3. Core Architectural Decisions (Frozen)

| Layer | Technology | Decision & Rationale |
|---|---|---|
| **Frontend** | React, TypeScript, Vite, PWA | Responsive desktop and mobile UI, offline-first capability via Service Workers, type-safety for scheme contracts. |
| **Backend** | Python 3.13, Django 5.x, DRF | High developer velocity, battle-tested ORM, native admin controls, robust serializer validation. |
| **Database** | PostgreSQL | Relational integrity, foreign key cascading constraints, JSONB support for configuration and metadata. |
| **Async Tasks** | Celery + Redis | Decouples long-running OCR, checksum calculations, and notification dispatches from the HTTP request-response cycle. |
| **Object Store** | MinIO / S3-compatible | Storage abstraction for uploaded applicant documents and official scheme guidelines with content hashing. |
| **OCR Pipeline** | PaddleOCR + Tesseract fallback | Dual-engine OCR with confidence scoring. AI OCR is strictly assistive. |
| **PDF Viewer** | PDF.js | Client-side deterministic PDF rendering without proprietary plugins. |
| **Deployment** | Docker Compose | Reproducible local development and staging environments. |

---

### 4. Ten Commandments of Scheme Governance & AI Safety

1. **Zero Hardcoded Eligibility**: Scheme rules are NEVER hardcoded in Python conditionals or application code. All rules reside in the database, linked to specific `SchemeVersion` instances.
2. **Academic Year Versioning**: Eligibility criteria vary across academic years. Each academic cycle has an isolated `SchemeVersion` record.
3. **Strict Source-Document Provenance**: Every rule and reference item MUST link to an authentic official document (Gazette notification, advertisement, or guideline).
4. **Assistive AI Boundary**: AI models (OCR, NER, image classification, anomaly scoring) assist human operators and prepare structured data. **AI NEVER has final decision authority over eligibility, rejection, or selection.**
5. **Deterministic Rule Engine**: Objective criteria (age limit, caste category, annual family income, course level) are evaluated by a transparent deterministic rule engine.
6. **Mandatory Human-in-the-Loop**: Low-confidence extractions, borderline criteria, or document anomalies route directly to an officer verification queue.
7. **Append-Only Auditing**: Any modification to scheme rules, workflow states, or applicant records creates an immutable, cryptographically verifiable `AuditLog` entry.
8. **Synthetic Data Policy**: Development, automated testing, and demonstration use synthetic applicant profiles only.
9. **PII Minimization**: Sensitive identity data (e.g., Aadhaar, account numbers) are never logged in plaintext or exposed unnecessarily.
10. **Adapter Pattern for External Systems**: No fictitious government APIs or private endpoints are scraped. Integrations with Aadhaar, DigiLocker, PFMS, NSP, and BHASHINI are cleanly encapsulated behind interface adapters with deterministic mocks for SIH demonstration.

---

### 5. Architectural Boundaries & Modules

```
backend/apps/
├── accounts/      # Custom User model, Roles (APPLICANT, VERIFIER, APPROVER, ADMIN), Permissions
├── applicants/    # Synthetic profile management, demographic records, disability info
├── schemes/       # Scheme, SchemeVersion, SchemeRule (8 categories), SchemeQuota, SelectionMethod,
│                  # ReferenceSet (with completeness metadata), InstitutionEligibility (course-specific)
├── documents/     # SourceDocument registry (provenance, tier-1/tier-2 URLs, SHA-256 checksums)
├── workflow/      # WorkflowDefinition, WorkflowState, WorkflowTransition, ApplicationStatusHistory
├── applications/  # Application aggregate root, linking applicant to scheme version and state
├── verification/  # Verification queue, confidence thresholds, human scrutiny workflows
├── notifications/ # Event-driven async notification service (Email, SMS, Portal notice)
├── audit/         # Tamper-resistant, append-only AuditLog
└── integrations/  # Interface abstractions & high-fidelity mocks for external gov systems
```

---

### 6. AI Governance & Decision Authority Boundary (Part 14)

Under statutory administrative law and SIH architectural safety requirements:
1. **Assistive Extraction Only**: AI (PaddleOCR, Tesseract, extraction heuristics) is strictly confined to extracting candidate data, reading document text, and computing confidence metrics.
2. **Absolute Decision Prohibition**: AI may **NEVER**:
   * Create policy rules.
   * Modify official rules.
   * Override deterministic rules.
   * Make final eligibility decisions (marking an applicant ELIGIBLE or INELIGIBLE).
   * Change quotas or capacity allocations.
   * Change selection criteria or scoring rubrics.
3. **Rule Proposal Governance Lifecycle**: If an AI assistant proposes any rule revision, it cannot be enacted automatically. It must traverse the strict four-tier governance state machine:
   $$\text{DRAFT} \longrightarrow \text{HUMAN REVIEW} \longrightarrow \text{APPROVED} \longrightarrow \text{PUBLISHED}$$
4. **Deterministic Evaluation Guarantee**: All initial applicant eligibility checks are performed exclusively by the deterministic `RuleEvaluationService` (`backend/apps/schemes/evaluator.py`).

---

### 7. Corrective Architecture: The Eight Rule Categories

A scheme rule must explicitly belong to exactly one functional category (`RuleCategory`). Categories are never inferred from rule codes:
1. `ELIGIBILITY`: Objective binary requirements (e.g. ST community, income ceiling).
2. `DOCUMENT`: Documentary verification requirements (e.g. caste certificate).
3. `SELECTION`: Merit scoring and committee rubrics (e.g. UGC-NET composite score).
4. `PREFERENCE`: Prioritization metrics (e.g. PVTG, Divyangjan) that **never** cause eligibility disqualification.
5. `QUOTA`: Capacity limits (e.g. 750 NFST slots, 20 NOS awards) stored in `SchemeQuota`.
6. `BENEFIT`: Fellowship/scholarship rates, stipends, and allowances.
7. `WORKFLOW`: Procedural transitions, nodal verification windows, DigiLocker gates.
8. `VALIDATION`: System-level format constraints and data integrity checks.

---

### 8. Prohibited Technologies & Anti-Patterns
To ensure academic rigor, architectural sanity, and compliance with the specification:
* **NO Microservices**: The system is intentionally a modular monolith.
* **NO MongoDB**: Polyglot persistence is unnecessary; PostgreSQL handles relational and JSONB data.
* **NO GraphQL**: RESTful APIs with hypermedia and standard pagination provide predictable caching and RBAC.
* **NO Kafka**: Redis + Celery provides lightweight, performant task queuing.
* **NO Kubernetes**: Docker Compose is standard for the SIH prototype.
* **NO Blockchain**: PostgreSQL append-only tables with tamper-evident audit logs meet all SIH auditability requirements without distributed ledger overhead.
* **NO LLM-based Rejections**: Rejections require traceable legal and policy citations from official guidelines.
* **NO Quotas as Applicant Eligibility**: Annual quotas are capacity allocations, not applicant fields (e.g., no `slot_quota <= 750`).

