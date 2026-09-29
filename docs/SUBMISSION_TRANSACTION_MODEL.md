# Submission Transaction Model & Concurrency Control

## 1. Transaction Boundaries (Part 5 & 7)
All critical state transitions in Tribel_Scholor execute inside database-level transactions using Django's `transaction.atomic()`, paired with row-level locks via `select_for_update()`.

### The 9-Stage Submission Pipeline
Submission is an authoritative, atomic operation that cannot be completed partially. If any step fails, the entire transaction rolls back cleanly:

```
[1. Check Idempotency Key] 
         │ (Already processed -> Return cached receipt immediately)
         ▼
[2. Database Lock: select_for_update()]
         ▼
[3. Validate Workflow State: DRAFT -> SUBMITTED only]
         ▼
[4. Server-Side Dynamic Form Validation (ApplicationFormValidator)]
         ▼
[5. Canonical Document Requirement Verification (DocumentRequirement)]
         ▼
[6. Duplicate Scanning & Multi-Source Conflict Detection]
         ▼
[7. Generate Immutable Document Manifest (SHA-256 + Metadata)]
         ▼
[8. Create Immutable ApplicationSubmissionSnapshot]
         ▼
[9. Transition State to SUBMITTED + Append StatusHistory & AuditLog]
```

## 2. Invariants Guaranteed by Database Transactions
1. **No Partial Submissions**: An application will never be left in an intermediate state where files were recorded but status history was not written.
2. **Authoritative Backend Validation**: Client-side JavaScript validation is treated strictly as an ergonomic UX layer. The backend dynamically evaluates types, formats, ranges, enums, conditional logic, and document presence.
3. **No Phantom Submissions**: Concurrency races (such as double-clicking submit or simultaneous automated requests) are blocked at the database lock level.
