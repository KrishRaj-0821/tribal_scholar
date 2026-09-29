# Workflow Engine & State Machine Specification
## MoTA SIH Problem Statement 26239

---

### 1. Overview
Scholarship applications follow rigorous multi-tier statutory workflows spanning applicant submission, scrutiny by university/nodal officers, state-level verification, ministry sanction, merit ranking, and PFMS disbursement.

To guarantee that workflow logic is neither hardcoded nor uniform across different schemes (e.g., NFST fellowships have university nodal review, whereas NOS has interview committee scrutiny), the workflow engine is **entirely declarative and data-driven**.

---

### 2. Workflow Entities

```
[ SchemeVersion ]
       │ (1 to 1)
       ▼
[ WorkflowDefinition ]
       │ (1 to Many)
       ├──► [ WorkflowState ] (e.g., DRAFT, SUBMITTED, UNDER_SCRUTINY, DEFECTIVE, VERIFIED, APPROVED)
       │
       └──► [ WorkflowTransition ]
                ├── from_state ──► [ WorkflowState ]
                ├── to_state   ──► [ WorkflowState ]
                ├── required_role (APPLICANT, SCRUTINY_OFFICER, VERIFYING_AUTHORITY, SANCTIONING_OFFICER)
                ├── requires_reason (Boolean)
                └── rule_condition_json (JSON condition)
```

#### Application Status History (Append-Only)
Whenever an application undergoes a transition:
```python
class ApplicationStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey('applications.Application', on_delete=models.CASCADE, related_name='status_history')
    from_state = models.ForeignKey(WorkflowState, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    to_state = models.ForeignKey(WorkflowState, on_delete=models.PROTECT, related_name='+')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```
* **Append-Only Invariant**: The model overrides `save()` to forbid modifications on existing instances and overrides `delete()` to prevent deletions. Once written, a state change record cannot be altered or removed.

---

### 3. Workflow State Lifecycle

```
[ DRAFT ] ──(Submit: Applicant)──► [ SUBMITTED ]
                                         │
                         (Scrutiny: Officer)
                                         ▼
                               [ UNDER_SCRUTINY ]
                                  │          │
                 (Defect Flagged) │          │ (Verified)
                                  ▼          ▼
                             [ DEFECTIVE ] [ VERIFIED ]
                                  │          │
                     (Resubmit)   │          │ (Merit/Sanction Committee)
                                  └──► [ SUBMITTED ]
                                             │
                                             ▼
                                      [ APPROVED ] ──► [ DISBURSED ] (Terminal)
                                             │
                                             └──► [ REJECTED ] (Terminal)
```

---

### 4. Visibility & Governance Matrix
Each `WorkflowState` defines:
* `applicant_visible`: Boolean controlling if an applicant can view this detailed state or if it is abstracted into a friendly summary.
* `officer_visible`: Boolean controlling officer portal visibility.
* `terminal`: Identifies definitive end-states (e.g., `DISBURSED`, `REJECTED`, `WITHDRAWN`).

---

### 5. Human-in-the-Loop Verification Queue
* AI algorithms (OCR, entity extraction, cross-field anomaly checks) output a normalized confidence score (0.0 to 1.0).
* When any document or rule validation yields confidence below the configured threshold, or produces conflicting evidence, the transition to automated verification is blocked.
* The application transitions to `DEFECTIVE` or routes to an officer verification queue with highlighted anomalies and source document citations.

---

### 6. Decoupled Selection & Capacity Allocation Stages
Under this corrective architecture, application progression is divided into distinct lifecycle phases:

1. **Phase 1: Deterministic Eligibility Evaluation**
   * Triggered upon submission.
   * `RuleEvaluationService` evaluates purely objective `ELIGIBILITY` rules.
   * Returns `ELIGIBLE`, `INELIGIBLE`, or `NEEDS_REVIEW`.
   * Quotas and selection methods are **not** evaluated here.

2. **Phase 2: Scrutiny & Document Verification**
   * Verifying authorities scrutinize documents satisfying `DOCUMENT` rules.
   * Defective applications are sent back to the applicant for resubmission.

3. **Phase 3: Merit Selection (`SelectionMethod`)**
   * Governed by the scheme version's `SelectionMethod` (e.g. `UGC_NET_MERIT_SCORE` or `EXPERT_COMMITTEE_INTERVIEW`).
   * Where `human_decision_required = True`, selection requires human committee sign-off.
   * Preference rules (`PREFERENCE`) apply priority ordering or tie-breaking here without causing prior disqualification.

4. **Phase 4: Capacity & Quota Allocation (`SchemeQuota`)**
   * Applications are awarded up to the statutory limit defined in `SchemeQuota` (e.g. 750 NFST slots; 20 NOS awards with 17 ST, 3 PVTG, 6 female earmarked).
   * Unawarded eligible candidates may be waitlisted; they are never falsely marked as ineligible.

