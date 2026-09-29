# Application Lifecycle & State Machine Architecture

## 1. Statutory Lifecycle Overview
The Tribel_Scholor application lifecycle governs the progression of tribal scholarship applications from initial profile linking and draft form completion through formal submission, scrutiny, and archival.

```
       [ DRAFT ]  <---+ (Deficiency Raised / Unlocked)
           |          |
           | (Submit Application via Atomic Transaction)
           v          |
      [ SUBMITTED ] --+
           |
           v
   [ UNDER_SCRUTINY ]
      |          |
      v          v
  [APPROVED]  [REJECTED]
```

## 2. Canonical Document Requirements (Part 1)
`DocumentRequirement` is the **sole canonical source of truth** for all document mandates across scheme versions.
- Legacy `SchemeRule` entries with `category = RuleCategory.DOCUMENT` that duplicated document presence requirements are marked **`SUPERSEDED`** with a documented `superseded_reason`.
- During rule evaluation, `DocumentRequirement` records are checked to ensure required documents exist.
- Each `DocumentRequirement` controls:
  - `when_required`: e.g., `APPLICATION`, `VERIFICATION`, `DISBURSAL`
  - `validity_policy`: `PERMANENT`, `FINANCIAL_YEAR`, `ACADEMIC_YEAR`, `RENEWABLE`
  - `acceptable_file_types`: Explicit list of MIME types (e.g. `["application/pdf", "image/jpeg"]`)
  - `max_size_mb`: File size limitation in megabytes (default 5 MB)
  - `deficiency_code` & `deficiency_severity`: Standardized defect tracking upon failure

## 3. Optimistic Concurrency Control (Part 4)
To prevent lost updates in multi-tab, multi-device, or concurrent officer review workflows, `Application` models implement optimistic concurrency:
- **`revision_number`**: An incrementing monotonic integer.
- **`last_modified_at`**: UTC timestamp of the latest persistence.
- **`last_modified_by`**: Foreign key to the user who made the last change.

### API Contract:
- `PATCH /api/v1/applications/{id}/form/` requires either:
  1. `expected_revision_number` in the request body, or
  2. `If-Match: "<revision_number>"` in the HTTP request headers.
- If the incoming revision does not match the database value, the server raises **`409 Conflict`**:
  ```json
  {
    "detail": "Application has been modified by another transaction. Reload latest version before editing.",
    "current_revision": 4,
    "expected_revision": 3
  }
  ```

## 4. State Machine Validation (Part 14)
All status transitions are strictly validated against `WorkflowDefinition`, `WorkflowState`, and `WorkflowTransition`:
- Direct illegal leaps (such as `DRAFT` directly to `SELECTED`, or arbitrary reversals) are blocked with `ValidationError`.
- Each transition checks caller permissions (`required_role`).
- Every transition executes within `transaction.atomic()`, acquires `select_for_update()`, appends an immutable `ApplicationStatusHistory` entry, and logs an `AuditLog` entry.
