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
    def put_safe(self, document_id: str, content: bytes, filename: str, application_id: str = 'vault') -> str:
        """Stores verified or vault-uploaded safe file directly in safe storage. Returns storage_key."""
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

    def put_safe(self, document_id: str, content: bytes, filename: str, application_id: str = 'vault') -> str:
        safe_name = os.path.basename(filename) or "document.bin"
        app_str = str(application_id or 'vault')
        safe_target_dir = self.safe_dir / app_str / str(document_id)
        safe_target_dir.mkdir(parents=True, exist_ok=True)
        safe_target_path = safe_target_dir / safe_name
        safe_target_path.write_bytes(content)
        return f"documents/{app_str}/{document_id}/{safe_name}"

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
    Production-ready S3 / MinIO / Cloudflare R2 storage adapter boundary.
    Activated via STORAGE_BACKEND='s3' or STORAGE_BACKEND='minio'.
    Credentials provided exclusively through environment variables.
    Separate quarantine/ and safe/ namespaces.
    No public URLs - strictly authenticated streaming via get_stream.
    """

    def __init__(self):
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise RuntimeError(
                "boto3 is required for S3CompatibleObjectStorage. "
                "Install boto3 or configure STORAGE_BACKEND='local'."
            )

        self.bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', os.getenv('AWS_STORAGE_BUCKET_NAME', 'tribal-scholar-documents'))
        self.region = getattr(settings, 'AWS_S3_REGION_NAME', os.getenv('AWS_S3_REGION_NAME', 'ap-south-1'))
        endpoint_url = getattr(settings, 'AWS_S3_ENDPOINT_URL', os.getenv('AWS_S3_ENDPOINT_URL', None))
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', os.getenv('AWS_ACCESS_KEY_ID', None))
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', os.getenv('AWS_SECRET_ACCESS_KEY', None))

        config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3, 'mode': 'standard'}
        )

        client_kwargs = {
            'service_name': 's3',
            'region_name': self.region,
            'config': config,
        }
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url
        if access_key and secret_key:
            client_kwargs['aws_access_key_id'] = access_key
            client_kwargs['aws_secret_access_key'] = secret_key

        self.client = boto3.client(**client_kwargs)

    def put_quarantine(self, document_id: str, content: bytes, filename: str) -> str:
        safe_name = os.path.basename(filename) or "document.bin"
        storage_key = f"quarantine/{document_id}/{safe_name}"
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=storage_key,
            Body=content,
            ServerSideEncryption='AES256',
            Metadata={'document_id': str(document_id)}
        )
        return storage_key

    def put_safe(self, document_id: str, content: bytes, filename: str, application_id: str = 'vault') -> str:
        safe_name = os.path.basename(filename) or "document.bin"
        app_str = str(application_id or 'vault')
        safe_key = f"documents/{app_str}/{document_id}/{safe_name}"
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=safe_key,
            Body=content,
            ServerSideEncryption='AES256',
            Metadata={'document_id': str(document_id), 'application_id': app_str}
        )
        return safe_key

    def promote_to_safe(self, document_id: str, application_id: str, filename: str) -> str:
        safe_name = os.path.basename(filename) or "document.bin"
        quarantine_key = f"quarantine/{document_id}/{safe_name}"
        app_str = str(application_id or 'unbound')
        safe_key = f"documents/{app_str}/{document_id}/{safe_name}"

        # Copy object within S3 bucket
        copy_source = {'Bucket': self.bucket_name, 'Key': quarantine_key}
        self.client.copy_object(
            CopySource=copy_source,
            Bucket=self.bucket_name,
            Key=safe_key,
            ServerSideEncryption='AES256'
        )
        # Delete from quarantine
        self.client.delete_object(Bucket=self.bucket_name, Key=quarantine_key)
        return safe_key

    def get_stream(self, storage_key: str):
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=storage_key)
            return response['Body']
        except Exception as exc:
            raise FileNotFoundError(f"Object not found in S3 at: {storage_key} ({exc})")

    def delete_quarantine(self, document_id: str) -> bool:
        prefix = f"quarantine/{document_id}/"
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                objects = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
                if objects:
                    self.client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': objects})
            return True
        except Exception:
            return False

    def delete_safe(self, storage_key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except Exception:
            return False

    def exists(self, storage_key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except Exception:
            return False


def get_object_storage() -> ObjectStorage:
    backend = getattr(settings, 'STORAGE_BACKEND', os.getenv('STORAGE_BACKEND', 'local')).lower()
    if backend in ('s3', 'minio', 'r2'):
        return S3CompatibleObjectStorage()
    return LocalObjectStorage()

