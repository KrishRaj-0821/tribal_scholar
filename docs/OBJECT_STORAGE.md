# Object Storage & Quarantine Architecture

## 1. Storage Abstraction Layer

To ensure cloud portability and security boundary isolation, Tribel_Scholor abstracts physical file operations behind the `ObjectStorage` interface:

```python
class ObjectStorage(ABC):
    @abstractmethod
    def put_quarantine(self, document_id: str, content: bytes, filename: str) -> str: ...

    @abstractmethod
    def promote_to_safe(self, document_id: str, application_id: str, filename: str) -> str: ...

    @abstractmethod
    def get_stream(self, storage_key: str): ...

    @abstractmethod
    def delete_quarantine(self, document_id: str) -> bool: ...

    @abstractmethod
    def delete_safe(self, storage_key: str) -> bool: ...

    @abstractmethod
    def exists(self, storage_key: str) -> bool: ...
```

---

## 2. Directory Layout & Isolation

Untrusted uploads **never** enter the safe document namespace directly. All uploads enter a strictly separated quarantine hierarchy:

```text
storage/
  ├── quarantine/
  │     └── {document_id}/
  │           └── {sanitized_filename}        <-- Initial upload lands here
  └── documents/
        └── {application_id}/
              └── {document_id}/
                    └── {sanitized_filename}  <-- Promoted ONLY after passing security scan
```

### Path Traversal Defense
Both `LocalObjectStorage` and any future storage provider sanitize paths by resolving keys against `base_dir` and verifying `str(full_path).startswith(str(base_dir.resolve()))`. Attempted directory escapes (e.g. `../../etc/passwd`) raise `django.core.exceptions.SuspiciousOperation`.

---

## 3. Storage Adapters

### A. LocalObjectStorage (`apps.documents.storage.LocalObjectStorage`)
- **Status**: **IMPLEMENTED**
- Used for local development and integration testing.
- Uses Python `pathlib.Path`, `shutil.copy2`, and `os.unlink` for atomic file promotion.

### B. S3CompatibleObjectStorage (`apps.documents.storage.S3CompatibleObjectStorage`)
- **Status**: **IMPLEMENTED** (Interface Boundary Prepared)
- Configurable via `STORAGE_BACKEND='minio'` or `STORAGE_BACKEND='s3'`.
- Leverages `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, and `MINIO_SECRET_KEY` settings.
- Direct bucket access is private; files are retrieved via backend proxies or short-lived presigned URLs.

---

## 4. No Public Bucket URLs & Authenticated Streaming

Documents are never exposed via unauthenticated public S3 bucket URLs or public static routes.

1. **Access Control**:
   - Applicant: Permitted to stream only documents belonging to their own application.
   - Scrutiny Officer: Permitted to stream documents within their jurisdiction or assigned schemes.
   - Administrator: Audited access.
2. **Audit Logging**: Every successful streaming request records a `DOCUMENT_VIEWED` audit entry with actor ID and timestamp.
3. **Infected Artifacts Blocked**: Any attempt to stream a document in `REJECTED` or `INFECTED` status is blocked with HTTP 403 / 410.

---

## 5. Implementation Status Matrix

| Component | Status | Details |
| :--- | :--- | :--- |
| `ObjectStorage` ABC | **IMPLEMENTED** | Base interface with 6 canonical storage methods |
| `LocalObjectStorage` Provider | **IMPLEMENTED** | Local filesystem quarantine and safe storage hierarchy |
| Path Traversal Sanitization | **IMPLEMENTED** | Rejects directory traversal tokens |
| Authenticated Streaming Download | **IMPLEMENTED** | DRF endpoint `/api/v1/documents/{id}/download/` with RBAC |
| S3 / MinIO Production Adapter | **FUTURE** | MinIO boto3 client integration for cloud Kubernetes deployments |
| Short-Lived Pre-Signed URLs | **FUTURE** | 5-minute expiring presigned GET tokens for direct S3 client streaming |
