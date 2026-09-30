import io
import pytest
from PIL import Image
from django.core.exceptions import SuspiciousOperation

from apps.documents.security import FileContentDetector, DocumentSecurityValidator
from apps.documents.malware_scanner import MockMalwareScanner, MalwareScanStatus
from apps.documents.storage import LocalObjectStorage


class TestFileContentDetector:
    """Unit tests for magic byte file type detection."""

    def test_detects_valid_pdf(self):
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<>>\nstartxref\n9\n%%EOF"
        assert FileContentDetector.detect_mime(pdf_bytes) == "application/pdf"

    def test_detects_jpeg(self):
        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
        assert FileContentDetector.detect_mime(jpeg_bytes) == "image/jpeg"

    def test_detects_png(self):
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        assert FileContentDetector.detect_mime(png_bytes) == "image/png"

    def test_detects_pe_executable_danger(self):
        exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff"
        assert FileContentDetector.detect_mime(exe_bytes) == "application/x-dosexec"

    def test_detects_elf_binary_danger(self):
        elf_bytes = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00"
        assert FileContentDetector.detect_mime(elf_bytes) == "application/x-executable"

    def test_detects_zip_danger(self):
        zip_bytes = b"PK\x03\x04\x14\x00\x00\x00"
        assert FileContentDetector.detect_mime(zip_bytes) == "application/zip"

    def test_detects_html_danger(self):
        html_bytes = b"<!DOCTYPE html><html><script>alert(1)</script></html>"
        assert FileContentDetector.detect_mime(html_bytes) == "text/html"

    def test_detects_svg_danger(self):
        svg_bytes = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
        assert FileContentDetector.detect_mime(svg_bytes) == "image/svg+xml"


class TestPdfSecurityValidator:
    """Unit tests for deep PDF structure inspection and exploit vector detection."""

    def test_valid_minimal_pdf(self):
        clean_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\nxref\n0 2\n0000000000 65535 f \ntrailer\n<< /Root 1 0 R >>\nstartxref\n50\n%%EOF"
        res = DocumentSecurityValidator.validate_pdf(clean_pdf)
        assert res.is_valid is True
        assert res.detected_mime == "application/pdf"

    def test_rejects_missing_pdf_header(self):
        bad_pdf = b"NOT_A_PDF_DOCUMENT_GARBAGE\n%%EOF"
        res = DocumentSecurityValidator.validate_pdf(bad_pdf)
        assert res.is_valid is False
        assert res.error_code == "PDF_HEADER_MISSING"

    def test_rejects_truncated_pdf_missing_eof(self):
        truncated_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj"
        res = DocumentSecurityValidator.validate_pdf(truncated_pdf)
        assert res.is_valid is False
        assert res.error_code == "PDF_MALFORMED_STRUCTURE"

    def test_rejects_pdf_with_embedded_javascript(self):
        js_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Action /S /JavaScript /JS (app.alert('pwned');) >>\nendobj\n%%EOF"
        res = DocumentSecurityValidator.validate_pdf(js_pdf)
        assert res.is_valid is False
        assert res.error_code == "PDF_JAVASCRIPT_DETECTED"

    def test_rejects_pdf_with_launch_action(self):
        launch_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Action /S /Launch /F (calc.exe) >>\nendobj\n%%EOF"
        res = DocumentSecurityValidator.validate_pdf(launch_pdf)
        assert res.is_valid is False
        assert res.error_code == "PDF_LAUNCH_ACTION_DETECTED"

    def test_rejects_pdf_with_embedded_files(self):
        embed_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Filespec /EF << /F 2 0 R >> >>\nendobj\n%%EOF"
        res = DocumentSecurityValidator.validate_pdf(embed_pdf)
        assert res.is_valid is False
        assert res.error_code == "PDF_EMBEDDED_FILES_DETECTED"

    def test_rejects_encrypted_pdf(self):
        enc_pdf = b"%PDF-1.4\ntrailer\n<< /Encrypt 1 0 R /Root 2 0 R >>\n%%EOF"
        res = DocumentSecurityValidator.validate_pdf(enc_pdf)
        assert res.is_valid is False
        assert res.error_code == "PDF_ENCRYPTED_NOT_SUPPORTED"


class TestImageSecurityValidator:
    """Unit tests for raster image decoding and decompression bomb prevention."""

    def test_valid_jpeg(self):
        buf = io.BytesIO()
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(buf, format="JPEG")
        content = buf.getvalue()

        res = DocumentSecurityValidator.validate_image(content)
        assert res.is_valid is True
        assert res.detected_mime == "image/jpeg"
        assert res.metadata["width"] == 100
        assert res.metadata["height"] == 100

    def test_valid_png(self):
        buf = io.BytesIO()
        img = Image.new("RGBA", (150, 150), color="green")
        img.save(buf, format="PNG")
        content = buf.getvalue()

        res = DocumentSecurityValidator.validate_image(content)
        assert res.is_valid is True
        assert res.detected_mime == "image/png"

    def test_rejects_decompression_bomb(self, settings):
        settings.MAX_IMAGE_PIXELS = 10_000
        buf = io.BytesIO()
        img = Image.new("RGB", (200, 200), color="red")  # 40,000 pixels > 10,000
        img.save(buf, format="JPEG")
        content = buf.getvalue()

        res = DocumentSecurityValidator.validate_image(content)
        assert res.is_valid is False
        assert res.error_code == "IMAGE_DECOMPRESSION_BOMB"

    def test_rejects_corrupted_image_bytes(self):
        corrupted = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        res = DocumentSecurityValidator.validate_image(corrupted)
        assert res.is_valid is False
        assert res.error_code == "IMAGE_DECODE_ERROR"


class TestMockMalwareScanner:
    """Unit tests for malware scanner mock behaviors."""

    def test_clean_file(self):
        scanner = MockMalwareScanner()
        status, msg = scanner.scan(b"Safe binary text payload")
        assert status == MalwareScanStatus.CLEAN

    def test_eicar_pattern_detected_as_infected(self):
        scanner = MockMalwareScanner()
        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        status, msg = scanner.scan(eicar)
        assert status == MalwareScanStatus.INFECTED

    def test_mock_error_trigger(self):
        scanner = MockMalwareScanner()
        status, msg = scanner.scan(b"some content with __MOCK_SCANNER_ERROR__ embedded")
        assert status == MalwareScanStatus.ERROR


class TestLocalObjectStorage:
    """Unit tests for local filesystem quarantine and promotion storage."""

    def test_put_quarantine_and_promote_to_safe(self, tmp_path):
        storage = LocalObjectStorage(base_dir=tmp_path)
        content = b"Binary certificate data"
        doc_id = "test-doc-1234"
        app_id = "test-app-5678"

        q_key = storage.put_quarantine(doc_id, content, "income_cert.pdf")
        assert storage.exists(q_key) is True

        safe_key = storage.promote_to_safe(doc_id, app_id, "income_cert.pdf")
        assert storage.exists(safe_key) is True
        assert storage.exists(q_key) is False  # Purged from quarantine

        with storage.get_stream(safe_key) as f:
            assert f.read() == content

    def test_path_traversal_blocked(self, tmp_path):
        storage = LocalObjectStorage(base_dir=tmp_path)
        with pytest.raises(SuspiciousOperation, match="Path traversal detected"):
            storage._sanitize_path("../../../etc/passwd")


class TestDocumentLifecycleTransitions:
    """Unit tests for document lifecycle state machine and valid/invalid transitions."""

    @pytest.mark.django_db
    def test_valid_lifecycle_transitions(self, db):
        from unittest.mock import MagicMock
        from django.core.exceptions import ValidationError
        from apps.documents.models import ApplicantDocument, DocumentLifecycleStatus

        # Test valid transitions defined in VALID_LIFECYCLE_TRANSITIONS
        transitions = [
            (DocumentLifecycleStatus.INITIATED, DocumentLifecycleStatus.UPLOADING),
            (DocumentLifecycleStatus.UPLOADING, DocumentLifecycleStatus.UPLOADED),
            (DocumentLifecycleStatus.UPLOADED, DocumentLifecycleStatus.QUARANTINED),
            (DocumentLifecycleStatus.QUARANTINED, DocumentLifecycleStatus.SCANNING),
            (DocumentLifecycleStatus.SCANNING, DocumentLifecycleStatus.PROMOTION_PENDING),
            (DocumentLifecycleStatus.PROMOTION_PENDING, DocumentLifecycleStatus.SAFE),
            (DocumentLifecycleStatus.SCANNING, DocumentLifecycleStatus.REJECTED),
            (DocumentLifecycleStatus.SCANNING, DocumentLifecycleStatus.QUARANTINED),
            (DocumentLifecycleStatus.SAFE, DocumentLifecycleStatus.PROCESSING),
            (DocumentLifecycleStatus.PROCESSING, DocumentLifecycleStatus.PROCESSED),
            (DocumentLifecycleStatus.PROCESSED, DocumentLifecycleStatus.VERIFICATION_PENDING),
            (DocumentLifecycleStatus.VERIFICATION_PENDING, DocumentLifecycleStatus.VERIFIED),
            (DocumentLifecycleStatus.VERIFIED, DocumentLifecycleStatus.REVOKED),
        ]

        for from_state, to_state in transitions:
            assert to_state in ApplicantDocument.VALID_LIFECYCLE_TRANSITIONS.get(from_state, set()), (
                f"Transition from {from_state} to {to_state} should be valid in transition table"
            )

    @pytest.mark.django_db
    def test_safe_cannot_transition_to_rejected(self, db):
        """Requirement 11: SAFE -> REJECTED must be forbidden without explicit revocation."""
        from django.core.exceptions import ValidationError
        from apps.documents.models import ApplicantDocument, DocumentLifecycleStatus
        from apps.accounts.models import User, UserRole

        user = User.objects.create_user(username="test_trans_user", role=UserRole.APPLICANT)
        doc = ApplicantDocument.objects.create(
            applicant=user,
            document_type="CASTE_CERTIFICATE",
            lifecycle_status=DocumentLifecycleStatus.SAFE
        )

        doc.lifecycle_status = DocumentLifecycleStatus.REJECTED
        with pytest.raises(ValidationError, match="cannot transition directly from 'SAFE' to 'REJECTED'"):
            doc.clean()

    @pytest.mark.django_db
    def test_uploaded_cannot_jump_directly_to_verified(self, db):
        """Requirement 11: Direct jump from unverified states to VERIFIED is forbidden."""
        from django.core.exceptions import ValidationError
        from apps.documents.models import ApplicantDocument, DocumentLifecycleStatus
        from apps.accounts.models import User, UserRole

        user = User.objects.create_user(username="test_trans_user2", role=UserRole.APPLICANT)
        for unverified in [
            DocumentLifecycleStatus.INITIATED,
            DocumentLifecycleStatus.UPLOADING,
            DocumentLifecycleStatus.UPLOADED,
            DocumentLifecycleStatus.QUARANTINED,
            DocumentLifecycleStatus.SCANNING
        ]:
            doc = ApplicantDocument.objects.create(
                applicant=user,
                document_type="CASTE_CERTIFICATE",
                lifecycle_status=unverified
            )
            doc.lifecycle_status = DocumentLifecycleStatus.VERIFIED
            with pytest.raises(ValidationError, match="directly from .* to 'VERIFIED'"):
                doc.clean()


class TestSecurityQuarantineRecordUnit:
    """Unit tests for SecurityQuarantineRecord model and retention policy."""

    @pytest.mark.django_db
    def test_quarantine_record_creation(self, db):
        from django.utils import timezone
        from apps.documents.models import (
            ApplicantDocument, SecurityQuarantineRecord, QuarantineDeletionStatus
        )
        from apps.accounts.models import User, UserRole

        user = User.objects.create_user(username="test_q_user", role=UserRole.APPLICANT)
        doc = ApplicantDocument.objects.create(
            applicant=user,
            document_type="CASTE_CERTIFICATE",
        )
        record = SecurityQuarantineRecord.objects.create(
            document=doc,
            detection_result="EICAR test virus signature detected",
            scanner="ClamAVScanner",
            retention_until=timezone.now() + timezone.timedelta(days=30),
            deletion_status=QuarantineDeletionStatus.RETAINED,
            quarantine_storage_key="quarantine/test/malware.bin"
        )
        assert record.deletion_status == QuarantineDeletionStatus.RETAINED
        assert record.deleted_at is None
        assert "EICAR" in record.detection_result


class TestDocumentJobExecutionUnit:
    """Unit tests for DocumentJobExecution model and task tracking."""

    @pytest.mark.django_db
    def test_job_execution_lifecycle(self, db):
        from django.utils import timezone
        from apps.documents.models import (
            ApplicantDocument, DocumentProcessingJob, DocumentJobExecution,
            JobExecutionStatus, DocumentJobType
        )
        from apps.accounts.models import User, UserRole

        user = User.objects.create_user(username="test_exec_user", role=UserRole.APPLICANT)
        doc = ApplicantDocument.objects.create(
            applicant=user,
            document_type="CASTE_CERTIFICATE",
        )
        job = DocumentProcessingJob.objects.create(
            document=doc,
            job_type=DocumentJobType.SECURITY_SCAN,
        )
        exec_record = DocumentJobExecution.objects.create(
            job=job,
            task_id="celery-task-uuid-12345",
            document=doc,
            stage="SECURITY_SCAN",
            execution_status=JobExecutionStatus.RUNNING,
            worker_id="celery@worker-node-1",
            correlation_id="CORR-12345",
        )
        assert exec_record.execution_status == JobExecutionStatus.RUNNING
        exec_record.execution_status = JobExecutionStatus.COMPLETED
        exec_record.finished_at = timezone.now()
        exec_record.save()
        assert exec_record.finished_at is not None

