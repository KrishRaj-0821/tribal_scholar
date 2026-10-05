# 🏛️ Tribal Scholar: AI-Enabled National Scholarship & Fellowship Management System
### Ministry of Tribal Affairs (MoTA), Government of India — Smart India Hackathon (SIH Problem Statement 26239)

[![Deployment Status](https://img.shields.io/badge/Deployment-Live%20Application-success?style=for-the-badge&logo=railway)](https://tribalscholar.up.railway.app)
[![API Health](https://img.shields.io/badge/Backend%20API-Online%20(HTTP%20200)-blue?style=for-the-badge&logo=django)](https://backend-production-ba69a.up.railway.app/health/live/)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%2B%20TypeScript%20%2B%20PWA-61DAFB?style=for-the-badge&logo=react)](https://tribalscholar.up.railway.app)
[![Backend](https://img.shields.io/badge/Backend-Django%205.1%20%2B%20DRF-092E20?style=for-the-badge&logo=django)](https://backend-production-ba69a.up.railway.app)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?style=for-the-badge&logo=postgresql)](https://www.postgresql.org/)
[![Compliance](https://img.shields.io/badge/Accessibility-GIGW%203.0%20%2F%20WCAG%202.1%20AA-orange?style=for-the-badge)](https://guidelines.india.gov.in/)

---

## 🌐 Live Application Links

| Portal / Service | Direct URL | Description |
| :--- | :--- | :--- |
| **🚀 Live Tribal Scholar Portal (PWA)** | **[https://tribalscholar.up.railway.app](https://tribalscholar.up.railway.app)** | Production web application for ST applicants & scrutiny officers |

| **📋 Comprehensive QA Audit Report** | **[docs/LIVE_APPLICATION_QA_REPORT.md](docs/LIVE_APPLICATION_QA_REPORT.md)** | End-to-end audit with live telecom SMS dispatch & OCR telemetry |

---

## 👥 Instant Evaluation & Demo Personas

The live deployment comes pre-configured with synthetic personas for instant evaluation without manual registration:

| Persona | Username | Password | Purpose & Accessible Workflows |
| :--- | :--- | :--- | :--- |
| **🎓 ST Student Applicant** | `demo_applicant` | `Tribal@2026` | Sovereign OTR Profile, Scheme Matching, 5-Step Application Wizard, Document Vault with ClamAV status & OCR extraction, Live SMS Audit Ledger |
| **🛡️ District Scrutiny Officer** | `demo_officer` | `Officer@2026` | District Scrutiny Desk (`/officer`), Priority Triage Queue, SLA Countdown, Interactive Side-by-Side Verification Workbench with bounding box overlays |

> **📲 Live Telecom SMS OTP Testing**: You can also register or log in with any valid 10-digit Indian mobile number. Real transactional OTPs and application dispatch receipts are sent directly to physical mobile phones via the **Fast2SMS** telecom gateway.

---

## 📌 What is Tribal Scholar?

**Tribal Scholar** is a sovereign, rule-governed, and AI-assisted scholarship administration ecosystem custom-built for the **Ministry of Tribal Affairs (MoTA), Government of India**.

Developed to solve **Smart India Hackathon (SIH) Problem Statement 26239**, Tribal Scholar modernizes the distribution and governance of central scholarships and fellowships for India's **10.4+ crore Scheduled Tribe (ST) citizens**.

The platform replaces fractured, paper-heavy, and opaque legacy scholarship workflows with an end-to-end digital pipeline that combines:
1. **Sovereign Student Lifecycle Management** with One-Time Registration (OTR), multilingual access, and offline-ready PWA functionality.
2. **Assistive Document Intelligence (AI OCR)** tuned for regional bilingual certificates (Hindi/Devanagari + English).
3. **Deterministic Statutory Rule Engine** that evaluates complex government gazette policies without hardcoded software logic.
4. **Human-in-the-Loop Scrutiny Workbench** empowering district welfare officers with side-by-side evidence inspection and fraud mitigation tools.
5. **Real-Time Telecom SMS Telemetry** ensuring remote tribal students with basic mobile handsets receive immediate submission and verification updates.

---

## 🎯 The Problem It Solves

Despite substantial financial commitments by the Government of India, tribal scholarship delivery historically suffers from severe structural bottlenecks:

```
Traditional Scholarship Friction Points:
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│ High Dropout & Low  │    │  Bilingual Document │    │  Lengthy Scrutiny   │
│  Digital Literacy   │───>│  Extraction Errors  │───>│    Bottlenecks      │
│ (Remote V/VI Areas) │    │(Devanagari/English) │    │  (12-18 Mo Delays)  │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
                                                                 │
┌─────────────────────┐    ┌─────────────────────┐               │
│ Delayed Fund Flow   │<───│  Opaque Rejections  │<──────────────┘
│& Academic Hardship  │    │  & Zero Auditability│
└─────────────────────┘    └─────────────────────┘
```

1. **Geographical & Connectivity Barriers**: Tribal students residing in remote Scheduled Areas (under Article 244 of the Constitution) frequently encounter intermittent 2G/3G connectivity, causing application submission failures and lost data.
2. **Linguistic & Certificate Challenges**: Caste, income, and domicile certificates in tribal districts (e.g., Jharkhand, Odisha, Madhya Pradesh, Chhattisgarh) are predominantly issued in regional Devanagari script or mixed bilingual formats that generic document scanners fail to parse.
3. **Severe Verification Delays (12–18 Months)**: Welfare departments face mountains of unindexed PDF and paper submissions, resulting in massive verification backlogs, missed academic fee deadlines, and student dropouts.
4. **Certificate Tampering & Fraud**: Lack of automated antivirus and malware quarantine permits malicious files, while lack of forensic cross-referencing allows forged income declarations or altered marksheets.
5. **Arbitrary Rejections**: In legacy portals, students receive abrupt rejection notices without specific statutory citations or opportunities to submit clarifying evidence.

---

## 🌟 What Tribal Scholar Does: Key Capabilities

### 1. 🎓 For Tribal Students
- **One-Time Registration (OTR)**: Students create a persistent sovereign profile once. Demographic, income, and community details are saved securely and reused across multiple schemes.
- **Dynamic Scheme Discovery**: Based on the student's degree level (Undergraduate, Postgraduate, M.Phil., Ph.D., Overseas), annual family income, and chosen institution, the system instantly matches eligible schemes.
- **Smart 5-Step Application Wizard**: Guided, step-by-step form completion with auto-saving, optimistic concurrency checks, and pre-submission validation.
- **Zero-Trust Document Vault**: Upload certificates once. The vault displays real-time ClamAV antivirus clearance and AI OCR provisional extraction tags.
- **Direct Telecom SMS Updates**: Every critical lifecycle event (submission, officer query, approval, fund transfer) triggers a direct SMS to the applicant's mobile phone.
- **Bilingual & GIGW 3.0 Accessible**: Seamless one-click switching between **English** and **Hindi (हिंदी)**, with full screen reader support, keyboard navigation, and high-contrast color modes.
- **Progressive Web App (PWA)**: Works smoothly on low-end smartphones and remains accessible during intermittent rural connectivity.

### 2. 🛡️ For Scrutiny Officers & MoTA Administrators
- **District Scrutiny Desk**: A unified administrative console that triages incoming applications by urgency, statutory SLA deadlines, and flagged discrepancies.
- **Side-by-Side Verification Workbench**: Eliminates tab-switching. Officers review the uploaded physical certificate on an interactive canvas alongside the AI-extracted fields and student-declared data.
- **Visual Bounding Box Overlays**: OCR-detected text regions are highlighted directly on the certificate image with confidence ratings.
- **Material Conflict Alerting**: If an applicant declares an annual income of ₹2,50,000 but the tehsildar-issued certificate states ₹4,50,000, the system automatically flags a `MATERIAL_CONFLICT` for mandatory officer resolution.
- **One-Click Determinations**: Officers can `Accept Extracted Value`, `Keep Declared Value`, `Request Clarifying Evidence`, or `Escalate`.
- **Append-Only Tamper-Resistant Audit Trail**: Every viewing, decision, and status modification is permanently recorded with user identity, timestamp, and immutable state hashes.

### 3. ⚖️ For Statutory Policy Governance
- **Zero-Hardcoding Rule Engine**: Eligibility rules are stored as structured database entities linked to specific academic year versions (`SchemeVersion`), completely eliminating fragile hardcoded Python conditionals.
- **Source-Document Provenance**: Every rule and institutional empanelment links directly to the authoritative Government of India Gazette notification with page citations and SHA-256 checksums.

---

## 🏛️ Flagship MoTA Schemes Administered

Tribal Scholar natively administers the statutory guidelines of the Ministry of Tribal Affairs' flagship programs:

```
                        ┌────────────────────────────────────────────────────────┐
                        │      MINISTRY OF TRIBAL AFFAIRS SCHEME PORTFOLIO       │
                        └────────────────────────────────────────────────────────┘
                                    │                           │
          ┌─────────────────────────┴──────────┐   ┌────────────┴────────────────────────┐
          ▼                                    ▼   ▼                                     ▼
   ┌───────────────┐                    ┌───────────────┐ ┌───────────────┐       ┌───────────────┐
   │     NFST      │                    │   TOP_CLASS   │ │      NOS      │       │  PRE / POST   │
   │  Fellowship   │                    │  Scholarship  │ │  Overseas ST  │       │  MATRIC ST    │
   └───────────────┘                    └───────────────┘ └───────────────┘       └───────────────┘
   • Regular M.Phil / Ph.D              • 260+ Premier    • World Top 500         • Secondary &
   • JRF: ₹31,000/mo                    • IIT, IIM, AIIMS   Universities          • Higher Sec.
   • SRF: ₹35,000/mo                    • Full Tuition    • Tuition + Allowance   • State DBT
   • 750 Slots / Year                   • Living Expense  • 20 Slots / Year       • Inter-State
```

| Scheme Code | Scheme Name | Target Beneficiaries & Scope | Key Statutory Criteria |
| :--- | :--- | :--- | :--- |
| **NFST** | **National Fellowship for Higher Education of ST Students** | 750 annual fellowships for ST scholars pursuing full-time regular M.Phil. and Ph.D. degrees in Indian universities. | ST community certificate; admission in UGC-recognized university; JRF/SRF tenure guidelines. |
| **TOP_CLASS** | **Top Class Education Scheme for ST Students** | Financial assistance covering full tuition fees and living stipends for meritorious ST students admitted to 260+ notified premier institutions (IITs, IIMs, NITs, AIIMS, NLUs, etc.). | ST certificate; annual family income $\le$ ₹6.0 Lakhs; admission in notified institution list. |
| **NOS** | **National Overseas Scholarship for ST Candidates** | Prestigious overseas fellowship for ST scholars admitted to top QS/Times Higher Education ranked international universities for Master's and Ph.D. degrees. | ST certificate; annual family income $\le$ ₹6.0 Lakhs; minimum 55% marks in qualifying degree; QS ranking criteria. |
| **PMS-ST** | **Post-Matric Scholarship for ST Students** | Centrally sponsored inter-state scheme covering post-matriculation studies with Direct Benefit Transfer (DBT) maintenance allowances. | ST community; annual family income $\le$ ₹2.50 Lakhs; recognized higher secondary/degree program. |

---

## 🤖 Responsible AI & Assistive Intelligence

Tribal Scholar implements strict **AI Safety and Ethical Governance** principles:

```
               Applicant Uploads Certificate
                            │
                            ▼
              ┌───────────────────────────┐
              │  ClamAV Antivirus Gateway │
              └───────────────────────────┘
                            │ (Safe)
                            ▼
              ┌───────────────────────────┐
              │  Dual-Engine OCR Pipeline │
              │ (PaddleOCR + Tesseract)   │
              └───────────────────────────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
   Devanagari Text Parsing       Visual Bounding Boxes
   (Income, Reg No, Authority)   (Mapped on Canvas)
               │                         │
               └────────────┬────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │    AI Confidence Score    │
              │  (Trust: OCR_PROVISIONAL) │
              └───────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │       HUMAN SCRUTINY WORKBENCH        │
        │                                       │
        │  [Accept]  [Keep Declared]  [Query]   │
        │                                       │
        │  * Officer Retains Sole Statutory *   │
        │  *    Authority to Approve/Reject *   │
        └───────────────────────────────────────┘
```

1. **AI is Strictly Assistive, Never Authoritative**: AI models perform optical character recognition, bounding box localization, and discrepancy scoring. **AI is never permitted to reject an applicant, disqualify a candidate, or approve disbursement.**
2. **Dual-Engine Bilingual Support**: Integrates **PaddleOCR** paired with **Tesseract** fallbacks, trained specifically for Devanagari script certificates alongside standard English stamps and typography.
3. **Confidence Scoring & Anomaly Detection**: Every extracted field carries a confidence percentage. Extractions with confidence below statutory thresholds automatically route into the officer review queue marked `NEEDS_HUMAN_SCRUTINY`.
4. **Zero Pre-population Overwrite**: Extracted OCR data is flagged as `OCR_PROVISIONAL` and never blindly overwrites an applicant's sworn declaration without an officer's conscious validation.

---

## 🛡️ Enterprise Security & Data Integrity

- **ClamAV Antivirus Quarantine**: Every uploaded document undergoes real-time antivirus scanning. Infected or corrupted files are immediately neutralized and rejected before entering storage.
- **Cryptographic SHA-256 Checksums**: Every uploaded certificate and official scheme rulebook is hashed using SHA-256 to ensure complete non-repudiation and tamper prevention.
- **Strict PII Masking**: In accordance with the Digital Personal Data Protection Act (DPDPA), Aadhaar numbers and mobile numbers are permanently masked (`******1902`) across all views, logs, and public API responses.
- **In-Depth IDOR & Tenancy Protection**: Fine-grained authorization prevents horizontal privilege escalation. Students can only access their personal applications; officers can only review dossiers assigned to their jurisdiction.
- **Telecom Key Isolation**: Third-party SMS API credentials and database connection secrets are encrypted in isolated server environments with zero client exposure.

---

## 📱 Real-Time Indian Telecom SMS Pipeline

To bridge the connectivity divide for tribal households that rely on basic feature phones, Tribal Scholar integrates directly with the **Fast2SMS Sovereign Telecom Gateway**:

```
[Application Lifecycle Event]
         │
         ▼
[Celery Background Task] ──> [Fast2SMS Gateway] ──> [Indian Telecom Route (57575711)]
         │                                                            │
         ▼                                                            ▼
[Database Audit Ledger]                                 [Applicant's Physical Phone]
 (Status: SENT_TO_PROVIDER)                               "Your Tribal Scholar app
                                                           MOTA/2025-26/NFST/9FA274
                                                           submitted successfully."
```

- **Truthful Telemetry**: The system strictly records provider dispatch (`SENT_TO_PROVIDER`) and does not falsify carrier handset delivery until genuine delivery receipts (DLR) are received.
- **Non-Blocking Execution**: SMS dispatches are processed asynchronously by Celery workers, ensuring the student's browser experience remains instant and responsive.

---

## 🏛️ GIGW 3.0 Compliance & Accessibility

Tribal Scholar adheres strictly to the **Guidelines for Indian Government Websites (GIGW 3.0)**:
- **National Emblem & Typography**: Official Government of India national motifs, bilingual header branding, and accessible color contrast.
- **Accessibility Toolbar**: Dedicated controls to increase/decrease text size, toggle high-contrast display modes, and activate text-to-speech screen reader support.
- **Screen Reader Compatibility**: Semantic HTML5 landmarks, comprehensive ARIA attributes, and keyboard-only navigation paths.
- **Sovereign Bilingualism**: Complete Hindi and English parity across all application workflows, alerts, and instructions.

---

## 🏗️ System Architecture at a Glance

Tribal Scholar is constructed as a **Modular Monolith** to maximize reliability, maintain strict ACID transactional guarantees, and avoid the operational overhead of microservices:

| Subsystem | Core Responsibilities |
| :--- | :--- |
| **`accounts`** | Role-Based Access Control (RBAC), secure authentication, session management. |
| **`applicants`** | Sovereign profile management, community categorization, demographic records, PII masking. |
| **`schemes`** | Declarative scheme catalog, academic year versions, eligibility rule engine, empanelled institution lists. |
| **`documents`** | Document vault, ClamAV antivirus quarantine, SHA-256 content hashing, provenance registry. |
| **`workflow`** | Deterministic state machine managing the application lifecycle (`DRAFT` $\rightarrow$ `SUBMITTED` $\rightarrow$ `UNDER_SCRUTINY` $\rightarrow$ `SANCTIONED`). |
| **`verification`** | Priority triage queues, officer verification workbench, side-by-side evidence comparison. |
| **`notifications`** | Event-driven async SMS engine powered by Celery, Redis, and Fast2SMS. |
| **`audit`** | Append-only, tamper-resistant transaction ledger recording all administrative decisions. |
| **`frontend (PWA)`** | React 18, TypeScript, Tailwind CSS, Workbox PWA service worker with offline caching. |

---

## 🧪 Live Evaluation Walkthrough

Want to test the platform right now? Follow this 3-minute evaluation flow:

1. **Open the Live Portal**: Navigate to [https://tribalscholar.up.railway.app](https://tribalscholar.up.railway.app).
2. **Log In as Student**: Click **"Sign In"**, enter `demo_applicant` and `Tribal@2026` (or use the one-click persona button).
   - Explore the **Sovereign Dashboard**, review the **Document Vault**, or initiate an application for **NFST** or **TOP_CLASS**.
   - Notice the instant bilingual toggle (English $\leftrightarrow$ Hindi) and GIGW accessibility toolbar at the top.
3. **Log In as Officer**: Sign out, then sign in with `demo_officer` and `Officer@2026`.
   - Access the **District Scrutiny Desk** (`/officer`).
   - Open a pending application to view the **Side-by-Side Verification Workbench**.
   - Observe the uploaded certificate canvas with PaddleOCR bounding box highlights and material conflict warnings.

---

## 📜 Ten Principles of Sovereign Scheme Governance

1. **Zero Hardcoded Eligibility**: All scheme rules live in database tables (`SchemeRule`), never inside application code.
2. **Academic Year Versioning**: Schemes are versioned per academic year (`SchemeVersion`), preventing retroactive rule invalidation.
3. **Strict Source Provenance**: Every rule points to an authentic gazette publication (`SourceDocument`) with verified SHA-256 checksums.
4. **Assistive AI Boundary**: AI assists with OCR and anomaly detection. **AI is never the final decision authority for eligibility, rejection, or selection.**
5. **Deterministic Rule Engine**: Binary eligibility conditions are evaluated deterministically with complete audit logs.
6. **Mandatory Human-in-the-Loop**: Discrepancies or low-confidence extractions automatically route to officer scrutiny queues.
7. **Append-Only Auditing**: `ApplicationStatusHistory` and `AuditLog` records are strictly immutable.
8. **Synthetic Applicant Data**: Development, testing, and pitch demonstrations use synthetic profiles only.
9. **Zero Scraping & Sandboxed Adapters**: External government integrations (DigiLocker, Aadhaar, PFMS, NSP, BHASHINI) are cleanly abstracted through standardized interface adapters.
10. **Zero Guessing Policy**: When statutory criteria from future amendments are pending gazette release, rules are explicitly marked `PENDING_OFFICIAL_SOURCE_EXTRACTION`.

---

## 👥 Authors & Acknowledgments

- **Platform**: Tribal Scholar Management System
- **Partner Agency**: Ministry of Tribal Affairs (MoTA), Government of India
- **Problem Statement**: SIH Problem Statement 26239 — AI-Enabled Scholarship & Fellowship Management System
- **Live Portal**: [https://tribalscholar.up.railway.app](https://tribalscholar.up.railway.app)
- **Repository**: [https://github.com/KrishRaj-0821/tribal_scholar](https://github.com/KrishRaj-0821/tribal_scholar)

---

## 📄 License

This project is developed for the Smart India Hackathon in partnership with the Ministry of Tribal Affairs (MoTA), Government of India. Released under the [MIT License](LICENSE).
