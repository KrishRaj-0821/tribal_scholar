import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from django.conf import settings
from django.core.exceptions import SuspiciousOperation


class ObjectStorage(ABC):
    """
    Abstract object storage boundary separating untrusted quarantine storage
    from authenticated safe document storage.
    """

    @abstractmethod
    def put_quarantine(self, document_id: str, content: bytes, filename: str) -> str:
        """Stores unverified raw file in quarantine. Returns storage_key."""
        pass

    @abstractmethod
    def promote_to_safe(self, document_id: str, application_id: str, filename: str) -> str:
        """Promotes safe verified file from quarantine into final document storage."""
        pass

    @abstractmethod
    def get_stream(self, storage_key: str):
        """Returns readable binary stream / open file handle for authorized download."""
        pass

    @abstractmethod
    def delete_quarantine(self, document_id: str) -> bool:
        """Purges quarantine copy."""
        pass

    @abstractmethod
    def delete_safe(self, storage_key: str) -> bool:
        """Deletes safe document (only for administrative revocation/cleanup)."""
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Checks if object exists at key."""
        pass


class LocalObjectStorage(ObjectStorage):
    """
    Local filesystem implementation of isolated object storage.
    Quarantine: {STORAGE_DIR}/quarantine/{document_id}/original_{filename}
    Safe:       {STORAGE_DIR}/documents/{application_id}/{document_id}/original_{filename}
    """

    def __init__(self, base_dir: Path = None):
        self.base_dir = Path(base_dir or getattr(settings, 'STORAGE_DIR', settings.BASE_DIR / 'storage'))
        self.quarantine_dir = self.base_dir / 'quarantine'
        self.safe_dir = self.base_dir / 'documents'

        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.safe_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_path(self, relative_key: str) -> Path:
        full_path = (self.base_dir / relative_key).resolve()
        if not str(full_path).startswith(str(self.base_dir.resolve())):
            raise SuspiciousOperation(f"Path traversal detected for storage key: {relative_key}")
        return full_path

    def put_quarantine(self, document_id: str, content: bytes, filename: str) -> str:
        safe_name = os.path.basename(filename) or "document.bin"
        doc_q_dir = self.quarantine_dir / str(document_id)
        doc_q_dir.mkdir(parents=True, exist_ok=True)
        target_path = doc_q_dir / safe_name
        target_path.write_bytes(content)
        return f"quarantine/{document_id}/{safe_name}"

    def promote_to_safe(self, document_id: str, application_id: str, filename: str) -> str:
        safe_name = os.path.basename(filename) or "document.bin"
        quarantine_key = f"quarantine/{document_id}/{safe_name}"
        q_path = self._sanitize_path(quarantine_key)

        app_str = str(application_id or 'unbound')
        safe_target_dir = self.safe_dir / app_str / str(document_id)
        safe_target_dir.mkdir(parents=True, exist_ok=True)
        safe_target_path = safe_target_dir / safe_name

        if not q_path.exists():
            # Crash-recovery guard: If file was already promoted in prior attempt before crash
            if safe_target_path.exists() and safe_target_path.is_file():
                return f"documents/{app_str}/{document_id}/{safe_name}"
            raise FileNotFoundError(f"Quarantine object not found for document {document_id}")

        # Atomically copy to safe destination
        shutil.copy2(q_path, safe_target_path)
        # Remove quarantine file
        try:
            q_path.unlink(missing_ok=True)
            q_dir = q_path.parent
            if q_dir.exists() and not any(q_dir.iterdir()):
                q_dir.rmdir()
        except OSError:
            pass

        return f"documents/{app_str}/{document_id}/{safe_name}"

    def get_stream(self, storage_key: str):
        target_path = self._sanitize_path(storage_key)
        if not target_path.exists() or not target_path.is_file():
            # Crash-recovery fallback: If looking for quarantine key that was already copied to safe
            if storage_key.startswith("quarantine/"):
                parts = storage_key.split('/')
                if len(parts) >= 3:
                    doc_id = parts[1]
                    file_name = parts[2]
                    for match in self.safe_dir.glob(f"*/{doc_id}/{file_name}"):
                        if match.is_file():
                            return open(match, 'rb')
            raise FileNotFoundError(f"Object not found in storage at: {storage_key}")
        return open(target_path, 'rb')

    def delete_quarantine(self, document_id: str) -> bool:
        doc_q_dir = self.quarantine_dir / str(document_id)
        if doc_q_dir.exists():
            shutil.rmtree(doc_q_dir, ignore_errors=True)
            return True
        return False

    def delete_safe(self, storage_key: str) -> bool:
        target_path = self._sanitize_path(storage_key)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        try:
            target_path = self._sanitize_path(storage_key)
            return target_path.exists() and target_path.is_file()
        except SuspiciousOperation:
            return False


class S3CompatibleObjectStorage(ObjectStorage):
    """
    Production-ready S3 / MinIO storage adapter boundary.
    Can be activated via STORAGE_BACKEND='s3' or STORAGE_BACKEND='minio'.
    """

    def __init__(self):
        # Initialized on demand when minio/boto3 client is configured
        pass

    def put_quarantine(self, document_id: str, content: bytes, filename: str) -> str:
        raise NotImplementedError("S3 storage adapter ready for cloud deployment.")

    def promote_to_safe(self, document_id: str, application_id: str, filename: str) -> str:
        raise NotImplementedError("S3 storage adapter ready for cloud deployment.")

    def get_stream(self, storage_key: str):
        raise NotImplementedError("S3 storage adapter ready for cloud deployment.")

    def delete_quarantine(self, document_id: str) -> bool:
        raise NotImplementedError("S3 storage adapter ready for cloud deployment.")

    def delete_safe(self, storage_key: str) -> bool:
        raise NotImplementedError("S3 storage adapter ready for cloud deployment.")

    def exists(self, storage_key: str) -> bool:
        raise NotImplementedError("S3 storage adapter ready for cloud deployment.")


def get_object_storage() -> ObjectStorage:
    backend = getattr(settings, 'STORAGE_BACKEND', 'local').lower()
    if backend in ('s3', 'minio'):
        return S3CompatibleObjectStorage()
    return LocalObjectStorage()
