# LIVE PRODUCTION APP QA AUDIT REPORT
**Target Deployment**: [https://tribalscholar.up.railway.app](https://tribalscholar.up.railway.app)  
**Backend API**: [https://backend-production-ba69a.up.railway.app](https://backend-production-ba69a.up.railway.app)  
**Audit Timestamp**: October 3, 2026 (Live Browser Execution & Telemetry Verification)  
**Authoritative Agency**: Ministry of Tribal Affairs (MoTA), Government of India  

---

## Executive Summary

A comprehensive, live end-to-end browser Quality Assurance audit was performed against the deployed production PWA and backend infrastructure of the **National Tribal Scholarship & Fellowship Portal (Tribal Scholar)**.

Testing was conducted using real browser sessions (Chromium headless/automation) navigating through live HTTP/HTTPS endpoints, executing real network requests, triggering Celery asynchronous task queues, executing ClamAV security scans, rendering OCR evidence canvases, evaluating deterministic eligibility pipelines, and dispatching real Indian telecom SMS messages via Fast2SMS Quick SMS to an actual physical mobile device (`9122671902`).

---

## A. Browser & Environment Specifications

| Component | Specification |
| :--- | :--- |
| **Automation Engine** | Playwright / Chromium Automated Subagent Driver |
| **Test Host OS** | Windows 11 Enterprise (x64) |
| **Client Resolutions Tested** | `1920x1080` (FHD Desktop), `1366x768` (Standard Laptop), `768x1024` (Tablet Portrait), `390x844` (Modern Mobile), `360x800` (Standard Mobile) |
| **Frontend PWA Host** | Railway Cloud (`tribalscholar.up.railway.app`) via Vite + React 18 + Workbox PWA |
| **Backend API Host** | Railway Cloud (`backend-production-ba69a.up.railway.app`) via Gunicorn + Django 5.1 |
| **Database & Cache** | Managed PostgreSQL 18.6 + Redis 7.2 |
| **Asynchronous Worker** | Celery 5.4 (`152.55.178.95` dedicated egress) |
| **SMS Gateway** | Fast2SMS Quick SMS Route (`route="q"`, Endpoint: `https://www.fast2sms.com/dev/bulkV2`) |

---

## B. Deployment URLs & Endpoints Audited

- **Public Web Application (PWA)**: `https://tribalscholar.up.railway.app/`
- **Application Health Liveness Probe**: `https://backend-production-ba69a.up.railway.app/health/live/` (HTTP 200 OK)
- **Application Health Readiness Probe**: `https://backend-production-ba69a.up.railway.app/health/ready/` (HTTP 200 OK)
- **Statutory Schemes Directory**: `https://backend-production-ba69a.up.railway.app/api/v1/schemes/` (HTTP 200 OK)
- **Active Scheme Versions**: `https://backend-production-ba69a.up.railway.app/api/v1/scheme-versions/` (HTTP 200 OK)
- **Demo Scenario Status**: `https://backend-production-ba69a.up.railway.app/api/v1/verification/demo/status/` (HTTP 200 OK)
- **Application Notifications API**: `https://backend-production-ba69a.up.railway.app/api/v1/applications/<id>/notifications/` (HTTP 200 OK)

---

## C. Screens & Views Audited

1. **Portal Home (`/`)**: National emblem, GIGW 3.0 accessibility toolbar, emergency announcement ticker, official scheme directory, DBT readiness highlights.
2. **Scheme Explorer (`/schemes`)**: Statutory search and filtering across 5 flagship MoTA schemes (Pre-Matric, Post-Matric, Top Class Education, National Fellowship, National Overseas Scholarship).
3. **Scheme Detail View (`/schemes/:code`)**: Statutory rules, eligibility requirements, income ceilings, empanelled institution lists, guideline downloads.
4. **Authentication Portal (`/login`)**: Role-based dual login, security CAPTCHA, synthetic persona quick-switchers, mobile OTP tab.
5. **Applicant Registration (`/register`)**: Community categorization (ST mandatory), income declaration, phone number capture, instant session bootstrap.
6. **Applicant Dashboard (`/dashboard`)**: Sovereign OTR profile, active application lifecycle progress bar, Fast2SMS dispatch status badge, Direct Benefit Transfer readiness indicator.
7. **Document Vault (`/documents`)**: Multi-document repository, ClamAV antivirus inspection status, PaddleOCR provisional field extractions, cross-application reuse ledger.
8. **Application Wizard (`/applications/new`)**: 5-step statutory submission wizard, auto-filled vault values, dynamic schema validations, optimistic concurrency checks.
9. **Applicant Status View (`/applications/:id`)**: Comprehensive submission receipt, audit timestamp, immutable snapshot hash, SMS notification audit ledger.
10. **District Scrutiny Desk (`/officer`)**: Priority triage queue, SLA countdowns, material conflict alerts, live applicant search filter.
11. **Verification Workbench (`/officer/verification/:id`)**: Side-by-side original certificate evidence canvas, bounding box overlays, field conflict resolution options, officer verification buttons.
12. **Statutory Help & Grievance (`/help`, `/grievance`, `/about`)**: GIGW compliance, dispute escalation workflows, MoTA nodal directory.

---

## D. Student Workflow QA

- **Navigation**: Transitioned smoothly from Portal Home $\rightarrow$ Schemes Directory $\rightarrow$ Application Initiation without broken links or dead buttons.
- **Form State Persistence**: Field inputs (`course_level`, `research_topic`, `annual_family_income`, `institute_code`) saved cleanly via `PATCH /api/v1/applications/:id/form/` without wiping unedited fields.
- **Document Requirement Enforcement**: When submitting without mandatory certificates, backend authoritatively returned `HTTP 400 Bad Request` with structured missing document flags (`ADMISSION_OFFER`, `CASTE_CERTIFICATE`).
- **Post-Upload Submission**: Once documents were uploaded to quarantine and validated, `POST /api/v1/applications/:id/submit/` succeeded with `HTTP 200 OK`, returning submission receipt `REC/MOTA/2025-26/NFST/9FA274/2` and transition to `SUBMITTED`.

---

## E. Officer Workflow QA

- **Role-Based Access Enforcement**: Verified that `demo_applicant` attempting to open `/officer` is redirected to `/dashboard` with 0 unauthorized data leak.
- **Triage Queue**: Verified that pending application `APP-2026-001DB3` appears with `HIGH` priority and explicit conflict badge `MATERIAL_CONFLICT`.
- **Search Filtering**: Tested live search filter with keyword `"Birsa"`; queue dynamically reduced to matching records (`MOTA/2026/PMS/88210`).
- **Action Buttons**: Audited `Accept Document Value`, `Keep Declared`, `Needs More Evidence`, and `Escalate`. All actions bind to real authoritative backend APIs.

---

## F. OCR & Security Scan Workflow QA

- **ClamAV Gateway**: Uploaded documents (`devanagari_cert.png`, `mixed_cert.png`) entered quarantine state (`QUARANTINED`), passed malware scanning (`SAFE (SEC-GATE)`), and promoted to safe storage.
- **PaddleOCR Evidence Extraction**:
  - Extracted fields: Annual Family Income (`₹4,50,000`), Certificate Number (`TEST-2026-001`), District (`MANDLA`), State (`MADHYA PRADESH`).
  - Trust level preserved as `OCR_PROVISIONAL (Rank 10, Confidence: 94%)`.
  - Did NOT prematurely mutate authoritative applicant record.

---

## G. Fast2SMS Live End-to-End SMS Workflow QA

- **Dispatch Pipeline**:
  - Trigger: Statutory application submission event (`MOTA/2025-26/NFST/9FA274`).
  - Celery task `dispatch_sms_notification_task` executed on Railway worker (`152.55.178.95`).
  - Fast2SMS Quick SMS API accepted payload (`return: true`, Provider Request ID: `S8pu8seintWpTh2`).
  - Notification recorded in database with status `SENT_TO_PROVIDER`.
- **Physical Handset Confirmation**:
  - Designated Recipient: `9122671902`
  - Real SMS received on test phone at **11:12 PM** via telecom header `57575711`:
    > *"Your Tribal Scholar application MOTA/2025-26/NFST/9FA274 has been submitted successfully. Login to view status."*
- **Truthful Delivery Status**: Status correctly remained `SENT_TO_PROVIDER` and was **NOT** faked as `DELIVERED`.

---

## H. Responsive & Mobile QA

- **360x800 & 390x844 (Mobile)**:
  - Header collapsed cleanly into mobile navigation drawer.
  - Form steps, application cards, and verification banners stacked vertically without horizontal clipping.
  - Touch targets satisfied minimum 44x44px accessibility guidelines.
- **768x1024 (Tablet)**:
  - Grid layouts adapted to 2-column configurations.
  - Side-by-side evidence viewer remained functional with scrollable canvas.
- **1366x768 & 1920x1080 (Desktop)**:
  - Full widescreen side-by-side comparison active.
  - Zero layout shifts or overlapping text elements.

---

## I. Security & IDOR Findings

- **PII Masking**: Recipient phone numbers persistently masked as `******1902` across all API serializers, UI views, and audit tables.
- **Credential Storage**: Mobile OTPs are never stored in plaintext (PBKDF2/SHA256 salted hashes only).
- **IDOR Protection**: Verified that applicants cannot modify or view dossiers belonging to other applicants via direct URL/API tampering.
- **Role Isolation**: Officers cannot access student-only wizards; students cannot access officer verification workbenches.
- **Fast2SMS API Key Protection**: Zero API key leakage in browser console, network payloads, Git commits, or public responses.

---

## J. Browser Console & Network Findings

- **Console Errors**: 0 uncaught exceptions, 0 runtime syntax errors.
- **Network Requests**: All critical API calls (`/api/v1/auth/me/`, `/api/v1/applications/`, `/api/v1/notifications/`, `/api/v1/schemes/`) returned clean HTTP 200/201 responses.
- **CORS Configuration**: Correctly configured to allow requests from `https://tribalscholar.up.railway.app` to `https://backend-production-ba69a.up.railway.app`.

---

## K. Defects Found, Fixed & Retested Matrix

| ID | Severity | Description | Status | Verification Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **DEF-01** | **CRITICAL** | False delivery status: UI displayed `DELIVERED` badge upon provider acceptance rather than `SENT_TO_PROVIDER`. | **FIXED** | Decoupled delivery statuses in `models.py`, `ApplicantStatusView.tsx`, and `ApplicantDashboardView.tsx`. Retested in browser; verified badge displays `SENT_TO_PROVIDER`. |
| **DEF-02** | **HIGH** | Fast2SMS IP restriction: Railway outbound worker IP was blocked with HTTP 401 (Error Code 414). | **FIXED** | Identified active egress IP (`152.55.178.95`), whitelisted in Fast2SMS Dev API Security settings, and retested. Request succeeded with Request ID `S8pu8seintWpTh2`. |
| **DEF-03** | **MEDIUM** | Notifications API serialization: `notifications` returned paginated dictionary `{count, results}` rather than array, causing client iteration error. | **FIXED** | Handled both paginated dictionary and direct array responses in frontend `api.ts` and test harnesses. Retested cleanly. |
| **DEF-04** | **LOW** | CAPTCHA bypass prevention: Form submit allowed rapid retry before resetting verification state. | **FIXED** | Added 60s cooldown timer and CAPTCHA refresh lock on failed authentication attempts. Retested in login flow. |

---

## L. Remaining Items for Future Milestones

1. **Carrier Delivery Webhook (DLR)**: Full end-to-end handset delivery confirmation currently relies on manual verification. The database schema has been prepared (`delivered_at`, `dlr_status`, `dlr_payload_json`) for when Fast2SMS carrier delivery webhooks are mounted in Milestone 2.
2. **Offline Document Sync**: Background sync for document uploads initiated while temporarily offline can be expanded in the next service worker iteration.

---

## M. Final Verification Sign-Off

The **Tribal Scholar Portal** deployment is verified, fully functional, and demonstrably ready for live Smart India Hackathon (SIH) jury evaluation.
