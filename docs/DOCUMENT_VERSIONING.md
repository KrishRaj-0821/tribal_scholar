# Document Versioning & Immutable Evidence Manifest

## 1. Non-Destructive Evidence Retention

In statutory scholarship administration, applicants may submit revised, clearer, or updated documents in response to deficiencies. Overwriting historical uploads destroys the administrative audit trail required to resolve disputes and verify decisions.

Tribel_Scholor enforces two complementary evidence primitives:
1. **`DocumentVersion`**: Tracks the sequential history of file replacements.
2. **`DocumentManifest`**: Provides a cryptographically sealed, immutable record of every document promoted to safe status.

---

## 2. DocumentVersion Entity

When an applicant uploads a replacement document for an existing `document_type` on the same application:
- The previous physical file is retained in storage.
- A new `DocumentVersion` instance is appended.
- `version_number` increments monotonically ($1, 2, 3, \dots$).
- `supersedes_version` maintains a foreign key to the superseded version.

```python
class DocumentVersion(models.Model):
    document = models.ForeignKey(ApplicantDocument, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=512)
    sha256 = models.CharField(max_length=64, validators=[validate_sha256_checksum])
    file_size_bytes = models.BigIntegerField()
    uploaded_at = models.DateTimeField(default=timezone.now)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    lifecycle_status = models.CharField(max_length=32)
    supersedes_version = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.TextField(blank=True)
```

---

## 3. Immutable DocumentManifest Entity

The `DocumentManifest` represents the official canonical evidence used downstream by OCR, field extraction, and scrutiny officers.

### Enforcement of Strict Immutability
- **Protection on `save()`**: Calling `manifest.save()` on an existing manifest raises `ValidationError("DocumentManifest records are strictly immutable and cannot be updated.")`.
- **Protection on `delete()`**: Calling `manifest.delete()` raises `ValidationError("DocumentManifest records cannot be deleted. Historical evidence is strictly preserved.")`.
- **Protection on QuerySet `update()`**: Disabled via custom manager.

```python
class DocumentManifest(models.Model):
    document = models.ForeignKey(ApplicantDocument, on_delete=models.PROTECT, related_name='manifests')
    sha256 = models.CharField(max_length=64, validators=[validate_sha256_checksum])
    size_bytes = models.BigIntegerField()
    detected_mime_type = models.CharField(max_length=128)
    storage_key = models.CharField(max_length=512)
    scan_status = models.CharField(max_length=32)
    validation_status = models.CharField(max_length=32)
    created_at = models.DateTimeField(default=timezone.now)
```

---

## 4. Document Revocation

If an official notice or fraudulent act renders a document invalid:
- `DocumentIngestionService.revoke_document()` transitions the document to `REVOKED`.
- Records `revoked_by`, `revoked_at`, and a mandatory administrative `reason`.
- Emits an append-only `DOCUMENT_REVOKED` audit log.
- Historical evidence files and versions remain intact in safe storage for legal and compliance audit.

---

## 5. Implementation Status Matrix

| Feature | Status | Details |
| :--- | :--- | :--- |
| Sequential Version History | **IMPLEMENTED** | `DocumentVersion` linked list preserving historical file copies |
| Strict Manifest Immutability | **IMPLEMENTED** | Blocked updates and deletions on `DocumentManifest` |
| Non-Destructive Revocation | **IMPLEMENTED** | Status update with mandatory officer attribution and audit trail |
| Retention & Expiry Policy Automation | **FUTURE** | Automated 7-year statutory archive purging policies (Phase 9) |
