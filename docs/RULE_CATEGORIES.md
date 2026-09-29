# Scheme Rule Classification & Categorization Taxonomy
## Ministry of Tribal Affairs (MoTA) — SIH Problem Statement 26239

---

### 1. Conceptual Principle
A critical defect in legacy scholarship systems is conflating all business policies into a single monolithic "eligibility" check. In reality, a government scheme encompasses distinct operational concepts that occur at different phases of the lifecycle and possess fundamentally different failure consequences.

Under this corrective architecture, **every SchemeRule explicitly belongs to exactly one `RuleCategory`**. Rule category is never inferred from naming conventions or rule codes.

---

### 2. The Eight Rule Categories

| Category | Definition | Lifecycle Stage | Failure Consequence | Example |
|---|---|---|---|---|
| **`ELIGIBILITY`** | Objective, deterministic binary qualification criteria that every applicant must satisfy to be considered. | Initial Applicant Dossier Evaluation | Blocking failure; application marked `INELIGIBLE`. | ST community membership; family income ceiling <= ₹6,00,000. |
| **`DOCUMENT`** | Documentary evidence requirements necessary to substantiate claims made in application fields. | Document Upload / Pre-Scrutiny Verification | Blocking or defect flag; application sent back for re-upload (`DEFECTIVE`). | Caste certificate uploaded; income certificate valid. |
| **`SELECTION`** | Merit formulation, composite scoring, and committee evaluation rubrics. | Committee Selection / Merit Ranking | Determines ranking in merit list; requires human committee sign-off if flagged. | 50% UGC-NET score + 50% Master's marks; Expert Committee Interview score. |
| **`PREFERENCE`** | Prioritization metrics used for ranking or tie-breaking among already-eligible candidates. | Merit Ordering / Tie-breaking | **NEVER** causes an eligible applicant to become ineligible. Sets priority order. | Preference to PVTG candidates; preference to Divyangjan (PwD). |
| **`QUOTA`** | Total capacity and statutory seat allocations across social, gender, and regional categories. | Final Award Sanctioning | Limits total sanctioned awards to sanctioned capacity; does not alter eligibility. | NFST: 750 annual slots; NOS: 20 awards (17 ST + 3 PVTG, 30% female earmarking). |
| **`BENEFIT`** | Financial entitlements, fee waivers, stipends, and allowances due to selected scholars. | Post-Selection Disbursement / PFMS | Governs calculated DBT disbursement amounts. | JRF rate ₹37,000/month; Computer allowance ₹45,000 one-time. |
| **`WORKFLOW`** | Procedural transitions and routing conditions between administrative tiers. | State Machine Lifecycle Progression | Controls which nodal officer, university, or ministry authority can act. | University Nodal Officer verification before December 31; DigiLocker authentication. |
| **`VALIDATION`** | System integrity checks, format constraints, and date validity. | Form Entry & Ingestion | Prevents invalid data submission (e.g. invalid date ranges or regex mismatches). | Academic year format `YYYY-YY`; valid SHA-256 checksum. |

---

### 3. Rules Engine Invariants
1. **No Quota as Eligibility**: Quota rules (`QUOTA`) reside in the dedicated `SchemeQuota` model and are evaluated during capacity allocation, never as an applicant eligibility gate.
2. **No Preference as Disqualification**: Preference rules (`PREFERENCE`) only award priority in selection queues; an applicant who does not belong to a preference group remains 100% eligible.
3. **No Automated Selection Override**: Selection methods (`SELECTION`) requiring human expert committees cannot be executed autonomously by background tasks without officer sign-off.
4. **Mandatory Provenance**: Any rule lacking a verified link to an official `SourceDocument` returns `NEEDS_REVIEW` and can never silently pass.
