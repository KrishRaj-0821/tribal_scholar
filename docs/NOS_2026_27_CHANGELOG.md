# NOS (National Overseas Scholarship) AY 2026-27 Amendment Changelog
## Ministry of Tribal Affairs (MoTA) — Statutory Policy Lineage

---

### 1. Authorizing Amendment Metadata
* **Document Title**: *MoTA Notification: Amendment in eligibility criteria and courses covered under the NOS Scheme for ST Students from 2026-27*
* **Source Type**: `AMENDMENT`
* **Issuing Authority**: Ministry of Tribal Affairs (Education Section), Government of India
* **Official URL**: [https://overseas.tribal.gov.in/amendments/2026-27](https://overseas.tribal.gov.in/amendments/2026-27)
* **Amendment Date**: January 15, 2026
* **Effective Academic Year**: `2026-27`
* **Superseded Publication**: *National Overseas Scholarship Scheme Guidelines 2025-26*

---

### 2. Statutory Change Matrix

| Change ID | Old Rule (2025-26) | New Rule (2026-27) | Change Type | Official Provenance Excerpt |
|---|---|---|---|---|
| **NOS-CHG-01** | `None` (All academic topics eligible subject to committee review) | `NOS_2026_RESTRICTED_INDIAN_SUBJECTS` (`application.is_indian_culture_or_heritage_topic == False`) | **`ADDED`** | *"Topics/courses concerning Indian Culture, Heritage, History & Social Studies on India based research would not be eligible for funding under the scheme."* |
| **NOS-CHG-02** | `NOS_2025_STUDY_ABROAD` (General requirement of accredited institution abroad) | `NOS_2026_QS_TOP_1000` (`application.foreign_university_qs_rank <= 1000`) | **`CHANGED`** | *"Candidate must have secured admission into a foreign university/institution ranked within the top 1,000 in the latest QS World University Rankings."* |
| **NOS-CHG-03** | `NOS_2025_DEGREE_LEVELS` (`IN_SET ['Master', 'PhD', 'Post-Doctoral']`) | `NOS_2026_EXCLUDE_BACHELORS` (Explicit exclusion of Undergraduate/Bachelor programs) | **`REPLACED`** | *"Bachelor-level courses in any discipline are not covered under this scheme. Only Masters, Ph.D., and Post-Doctoral research are eligible."* |
| **NOS-CHG-04** | `NOS_2025_ANNUAL_AWARDS_QUOTA` (Treated as pseudo-rule on applicant) | `NOS_2026_TOTAL_SLOTS` under `SchemeQuota` (`total_capacity = 20`, `ST = 17`, `PVTG = 3`, `Female = 6`) | **`RELOCATED`** | *"The total number of fresh awards per year is 20, comprising 17 for ST candidates and 3 for Particularly Vulnerable Tribal Groups (PVTGs). 30% earmarked for females."* Moved from eligibility to statutory quota configuration. |
| **NOS-CHG-05** | `None` (Physical / scan-based document upload) | `NOS_2026_DIGILOCKER_VERIFICATION` (`applicant.digilocker_verified == True`) | **`ADDED`** | *"Applicants must complete document submission and verification via the integrated DigiLocker workflow."* |
| **NOS-CHG-06** | `NOS_2026_AMENDED_COURSE_ELIGIBILITY` (`PENDING_OFFICIAL_SOURCE_EXTRACTION` placeholder) | Replaced with verified `NOS_2026_RESTRICTED_INDIAN_SUBJECTS` and `NOS_2026_QS_TOP_1000` | **`REMOVED`** | Obsolete unextracted draft placeholder removed following complete retrieval of official circular. |

---

### 3. Implementation Verification
1. **Multi-Year Coexistence**: Historical applications submitted under `2025-26` continue to evaluate against the `2025-26` snapshot. They are **not** retroactively evaluated against the 2026-27 Indian heritage restriction or QS Top 1000 threshold.
2. **Zero Hallucination Protocol**: All rule definitions cite exact textual fragments from the official gazette amendment.
3. **Capacity Separation**: 20-award limit operates in the selection and sanction allocation pipeline, rather than functioning as an applicant disqualifier.
