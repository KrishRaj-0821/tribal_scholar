# Idempotency Architecture & Replay Protection

## 1. Statutory Rationale (Part 6)
In real-world government scholarship portals, applicants often experience network latency, server timeouts, or accidental double-clicking on submission buttons. Without rigorous idempotency guarantees, repeated submission attempts can lead to:
- Duplicate application records
- Redundant and confusing status history events
- Multiple duplicate audit logs
- Inconsistent merit ranking entries

## 2. Idempotency Implementation
Tribel_Scholor enforces strict idempotency on `POST /api/v1/applications/{id}/submit/` using the `Idempotency-Key` HTTP header.

### Model: `IdempotencyRecord`
- `key`: The caller-supplied idempotency key string.
- `actor`: Foreign key to authenticated user.
- `endpoint`: The normalized URI path (e.g. `/api/v1/applications/{uuid}/submit/`).
- `request_hash`: SHA-256 hash of canonical request payload.
- `response_status`: HTTP status code returned upon first successful processing (e.g. `200`).
- `response_body`: JSON payload returned to the caller.
- `created_at`: UTC timestamp of original execution.
- `expires_at`: Expiration threshold (default 24 hours).

### Database Constraints
```python
unique_together = ('key', 'actor', 'endpoint')
```
Keys are strictly scoped to the authenticated caller and specific endpoint to prevent cross-applicant or cross-endpoint collision.

## 3. Replay Semantics
1. **First Request**:
   - The transaction executes normally.
   - The final receipt dictionary and status code are committed.
   - An `IdempotencyRecord` is created containing the cached response.
2. **Subsequent Identical Requests**:
   - The endpoint checks `IdempotencyRecord.objects.filter(key=idempotency_key, actor=user, endpoint=path).first()`.
   - If found, it immediately returns the original cached response body and status code.
   - **Zero additional database changes, status events, audit logs, or evaluations are generated.**
3. **Resubmission with New Key**:
   - If a new key is sent against an already submitted application, the pipeline detects that `current_state.code != 'DRAFT'` and rejects the request with HTTP 400 Bad Request, protecting against unauthorized state mutations.
