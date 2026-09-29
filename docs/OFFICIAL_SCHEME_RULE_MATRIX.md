# Official MoTA Scheme Rule Matrix
## Comprehensive Statutory Rule Registry across Academic Cycles

---

### 1. Overview & Verification Authority
All rules listed herein are extracted exclusively from **Tier 1 (tribal.nic.in)** and **Tier 2 (fellowship.tribal.gov.in, overseas.tribal.gov.in, scholarships.gov.in)** official publications of the Ministry of Tribal Affairs (MoTA).

Zero rules are inferred from blogs, news summaries, or unverified secondary portals.

---

### 2. NFST (National Fellowship for Higher Education of ST Students) — AY 2025-26
* **Scheme Code**: `NFST`
* **Academic Year**: `2025-26`
* **Authorizing Publication**: *MoTA National Fellowship for Higher Education of ST Students Guidelines & Advertisement 2025-26*
* **Official URL**: [https://fellowship.tribal.gov.in/](https://fellowship.tribal.gov.in/)
* **Capacity**: 750 fresh fellowship slots configured under `SchemeQuota` (`NFST_2025_ANNUAL_SLOTS`).
* **Selection Method**: Configured under `SelectionMethod` (`UGC_NET_MERIT_SCORE` — 50% UGC-NET Score + 50% Master Degree Marks).

| Rule ID | Category | Field Path | Operator | Target Value | Severity | Provenance Excerpt |
|---|---|---|---|---|---|---|
| `NFST_2025_ST_COMMUNITY` | `ELIGIBILITY` | `applicant.community` | `EQUALS` | `"ST"` | `BLOCKING` | *"The candidate must belong to a Scheduled Tribe (ST) notified under Article 342."* |
| `NFST_2025_PHD_ENROLMENT` | `ELIGIBILITY` | `application.course_level` | `IN_SET` | `["PhD", "Integrated M.Phil + Ph.D."]` | `BLOCKING` | *"Candidate must have secured admission into regular and full time M.Phil/Ph.D. program in recognized institutions."* |
| `NFST_2025_INSTITUTION_ELIGIBILITY` | `ELIGIBILITY` | `application.institute_code` | `IN_SET` | `Ref: NFST_RECOGNIZED_INSTITUTIONS_SAMPLE` | `BLOCKING` | *"Universities/Institutes/Colleges recognized by UGC under Section 2(f) and 12(B) or declared as Institutes of National Importance."* |
| `NFST_2025_PREFERENCE_PVTG` | `PREFERENCE` | `applicant.is_pvtg` | `EQUALS` | `True` | `WARNING` | *"Preference will be given to candidates belonging to Particularly Vulnerable Tribal Groups (PVTGs)."* |
| `NFST_2025_PREFERENCE_DIVYANGJAN` | `PREFERENCE` | `applicant.is_disabled` | `EQUALS` | `True` | `WARNING` | *"Preference shall be given to Divyangjan (Persons with Disabilities) ST scholars."* |
| `NFST_2025_DOC_CASTE_CERT` | `DOCUMENT` | `documents.caste_certificate` | `EXISTS` | `True` | `BLOCKING` | *"Valid ST certificate issued by competent authority in the prescribed format."* |
| `NFST_2025_DOC_ADMISSION_LETTER` | `DOCUMENT` | `documents.admission_letter` | `EXISTS` | `True` | `BLOCKING` | *"Certificate of admission/registration to the regular full-time Ph.D. course."* |

---

### 3. TOP CLASS (National Scholarship for Higher Education of ST Students) — AY 2025-26
* **Scheme Code**: `TOP_CLASS`
* **Academic Year**: `2025-26`
* **Authorizing Publication**: *Top Class Education Scheme Guidelines 2025-26* & *Annexure I: Roster of 265 Premier Institutes*
* **Official URL**: [https://tribal.nic.in/ScholarshiP.aspx](https://tribal.nic.in/ScholarshiP.aspx)
* **Master Dataset Status**: `TOP_CLASS_PREMIER_INSTITUTES_SAMPLE` marked `PARTIAL` (7 representative records loaded of 265 expected).

| Rule ID | Category | Field Path | Operator | Target Value | Severity | Provenance Excerpt |
|---|---|---|---|---|---|---|
| `TOP_CLASS_2025_ST_COMMUNITY` | `ELIGIBILITY` | `applicant.community` | `EQUALS` | `"ST"` | `BLOCKING` | *"Scholarship is open to Scheduled Tribe (ST) students only."* |
| `TOP_CLASS_2025_INCOME_CEILING` | `ELIGIBILITY` | `applicant.annual_family_income` | `LESS_THAN_OR_EQUAL` | `600000` | `BLOCKING` | *"Total family income of the candidate to be eligible for this scheme is Rs. 6.00 lakh per annum from all sources."* |
| `TOP_CLASS_2025_PREMIER_INSTITUTE` | `ELIGIBILITY` | `application.institute_code` | `IN_SET` | `Ref: TOP_CLASS_PREMIER_INSTITUTES_SAMPLE` | `BLOCKING` | *"The scholarship is available for studying in 265 premier institutions notified by the Ministry of Tribal Affairs."* |
| `TOP_CLASS_2025_DOC_INCOME_CERT` | `DOCUMENT` | `documents.income_certificate` | `EXISTS` | `True` | `BLOCKING` | *"Income certificate issued by the competent authority in the State/UT Government."* |

#### Course-Specific Institutional Eligibility (`InstitutionEligibility`)
The scheme evaluates `institution + course`. Sample verified notified mappings:
* **IIT Bombay**: `B.Tech`, `Dual Degree B.Tech + M.Tech`
* **IIT Delhi**: `B.Tech`, `Integrated M.Tech`
* **IIT Madras**: `B.Tech`, `BS Data Science`
* **IIM Ahmedabad**: `MBA`, `PGP`
* **AIIMS New Delhi**: `MBBS`, `B.Sc. Nursing`
* **NLSIU Bengaluru**: `B.A. LL.B. (Hons)`, `LL.M.`
* **NIT Tiruchirappalli**: `B.Tech`, `B.Arch`

---

### 4. NOS (National Overseas Scholarship for ST Candidates) — AY 2025-26
* **Scheme Code**: `NOS`
* **Academic Year**: `2025-26`
* **Authorizing Publication**: *National Overseas Scholarship Scheme for Scheduled Tribe Candidates (NOS) Guidelines 2025-26*
* **Official URL**: [https://overseas.tribal.gov.in/](https://overseas.tribal.gov.in/)
* **Capacity**: 20 total awards configured in `SchemeQuota`: 17 ST, 3 PVTG, 6 female earmarked.
* **Selection Method**: `SelectionMethod` (`EXPERT_COMMITTEE_INTERVIEW`, `human_decision_required = True`).

| Rule ID | Category | Field Path | Operator | Target Value | Severity | Provenance Excerpt |
|---|---|---|---|---|---|---|
| `NOS_2025_COMMUNITY` | `ELIGIBILITY` | `applicant.community` | `IN_SET` | `["ST", "PVTG"]` | `BLOCKING` | *"The scheme is open to Scheduled Tribe (ST) candidates including Particularly Vulnerable Tribal Groups (PVTGs)."* |
| `NOS_2025_STUDY_ABROAD` | `ELIGIBILITY` | `application.study_destination` | `EQUALS` | `"ABROAD"` | `BLOCKING` | *"Financial assistance is provided to pursue higher studies abroad."* |
| `NOS_2025_DEGREE_LEVELS` | `ELIGIBILITY` | `application.course_level` | `IN_SET` | `["Master", "PhD", "Post-Doctoral"]` | `BLOCKING` | *"Courses covered are Masters Degree, Ph.D., and Post-Doctoral research."* |
| `NOS_2025_INCOME_CEILING` | `ELIGIBILITY` | `applicant.annual_family_income` | `LESS_THAN_OR_EQUAL` | `600000` | `BLOCKING` | *"Total family income from all sources should not exceed Rs. 6,00,000 per annum."* |
| `NOS_2025_AGE_LIMIT` | `ELIGIBILITY` | `applicant.age_on_july_1` | `LESS_THAN_OR_EQUAL` | `35` | `BLOCKING` | *"Not more than 35 years as on 1st July of the selection year for Ph.D. candidates (32 for Masters, 38 for Post-Doc)."* |

---

### 5. NOS (National Overseas Scholarship for ST Candidates) — AY 2026-27 (AMENDED)
* **Scheme Code**: `NOS`
* **Academic Year**: `2026-27`
* **Authorizing Publication**: *MoTA Notification: Amendment in eligibility criteria and courses covered under the NOS Scheme for ST Students from 2026-27*
* **Official URL**: [https://overseas.tribal.gov.in/amendments/2026-27](https://overseas.tribal.gov.in/amendments/2026-27)
* **Status**: `ACTIVE` (Fully extracted from official circular).

| Rule ID | Category | Field Path | Operator | Target Value | Severity | Provenance Excerpt |
|---|---|---|---|---|---|---|
| `NOS_2026_COMMUNITY` | `ELIGIBILITY` | `applicant.community` | `IN_SET` | `["ST", "PVTG"]` | `BLOCKING` | *"The scheme is open to Scheduled Tribe (ST) candidates including Particularly Vulnerable Tribal Groups (PVTGs)."* |
| `NOS_2026_INCOME_CEILING` | `ELIGIBILITY` | `applicant.annual_family_income` | `LESS_THAN_OR_EQUAL` | `600000` | `BLOCKING` | *"Total family income from all sources should not exceed Rs. 6,00,000 per annum."* |
| `NOS_2026_EXCLUDE_BACHELORS` | `ELIGIBILITY` | `application.course_level` | `IN_SET` | `["Master", "PhD", "Post-Doctoral"]` | `BLOCKING` | *"Bachelor-level courses in any discipline are not covered under this scheme. Only Masters, Ph.D., and Post-Doctoral research are eligible."* |
| `NOS_2026_QS_TOP_1000` | `ELIGIBILITY` | `application.foreign_university_qs_rank` | `LESS_THAN_OR_EQUAL` | `1000` | `BLOCKING` | *"Candidate must have secured admission into a foreign university/institution ranked within the top 1,000 in the latest QS World University Rankings."* |
| `NOS_2026_RESTRICTED_INDIAN_SUBJECTS` | `ELIGIBILITY` | `application.is_indian_culture_or_heritage_topic` | `EQUALS` | `False` | `BLOCKING` | *"Topics/courses concerning Indian Culture, Heritage, History & Social Studies on India based research would not be eligible for funding under the scheme."* |
| `NOS_2026_DIGILOCKER_VERIFICATION` | `WORKFLOW` | `applicant.digilocker_verified` | `EQUALS` | `True` | `BLOCKING` | *"Applicants must complete document submission and verification via the integrated DigiLocker workflow."* |
