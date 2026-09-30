import io
import re
from typing import Tuple, Dict, Any, Optional
from django.conf import settings
from PIL import Image, ImageOps

# Maximum pixel threshold to prevent decompression bombs (default 25 megapixels)
DEFAULT_MAX_IMAGE_PIXELS = 25_000_000


class FileValidationResult:
    def __init__(
        self,
        is_valid: bool,
        detected_mime: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sanitized_bytes: Optional[bytes] = None,
    ):
        self.is_valid = is_valid
        self.detected_mime = detected_mime
        self.error_code = error_code
        self.error_message = error_message
        self.metadata = metadata or {}
        self.sanitized_bytes = sanitized_bytes


class FileContentDetector:
    """
    Detects authentic MIME types from byte signatures (magic numbers).
    Never trusts filename extensions or client-supplied headers.
    """

    MAGIC_SIGNATURES = [
        # PDF
        (b"%PDF-", "application/pdf"),
        # JPEG
        (b"\xff\xd8\xff", "image/jpeg"),
        # PNG
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        # Dangerous Executables (DOS/Windows PE, DLL)
        (b"MZ", "application/x-dosexec"),
        # Linux ELF
        (b"\x7fELF", "application/x-executable"),
        # Mach-O
        (b"\xfe\xed\xfa\xce", "application/x-mach-binary"),
        (b"\xfe\xed\xfa\xcf", "application/x-mach-binary"),
        (b"\xce\xfa\xed\xfe", "application/x-mach-binary"),
        (b"\xcf\xfa\xed\xfe", "application/x-mach-binary"),
        # Archives
        (b"PK\x03\x04", "application/zip"),
        (b"PK\x05\x06", "application/zip"),
        (b"PK\x07\x08", "application/zip"),
        (b"Rar!\x1a\x07", "application/x-rar"),
        (b"7z\xbc\xaf\x27\x1c", "application/x-7z-compressed"),
        (b"\x1f\x8b\x08", "application/gzip"),
        (b"BZh", "application/x-bzip2"),
    ]

    @classmethod
    def detect_mime(cls, content: bytes) -> str:
        if not content:
            return "application/x-empty"

        # Check binary headers
        for prefix, mime in cls.MAGIC_SIGNATURES:
            if content.startswith(prefix):
                return mime

        # PDF tolerance: some scanners check first 1024 bytes
        if b"%PDF-" in content[:1024]:
            return "application/pdf"

        # Text-based dangerous payloads: HTML, XML, SVG, Scripts
        header_sample = content[:512].lower()
        if b"<svg" in header_sample or (b"<?xml" in header_sample and b"<svg" in content[:2048].lower()):
            return "image/svg+xml"
        if b"<html" in header_sample or b"<!doctype html" in header_sample:
            return "text/html"
        if b"<?xml" in header_sample:
            return "application/xml"
        if b"<script" in header_sample or b"javascript:" in header_sample:
            return "application/javascript"

        return "application/octet-stream"


class DocumentSecurityValidator:
    """
    Comprehensive content and structure validator.
    Inspects PDF streams, AST/action dictionaries, image raster dimensions,
    and MIME consistency.
    """

    SUSPICIOUS_PDF_PATTERNS = [
        (re.compile(rb"/JavaScript\b|/JS\b", re.IGNORECASE), "PDF_JAVASCRIPT_DETECTED", "PDF contains embedded JavaScript actions."),
        (re.compile(rb"/Launch\b", re.IGNORECASE), "PDF_LAUNCH_ACTION_DETECTED", "PDF contains executable launch directives."),
        (re.compile(rb"/EmbeddedFiles\b|/EF\b", re.IGNORECASE), "PDF_EMBEDDED_FILES_DETECTED", "PDF contains embedded binary attachments."),
        (re.compile(rb"/Encrypt\b", re.IGNORECASE), "PDF_ENCRYPTED_NOT_SUPPORTED", "Password-protected or encrypted PDFs are not supported for automated processing."),
    ]

    @classmethod
    def validate_pdf(cls, content: bytes) -> FileValidationResult:
        """
        Validates PDF structure and security invariants:
        - Must start with %PDF-
        - Must terminate with %%EOF
        - Prohibits JavaScript, Launch actions, EmbeddedFiles, and Encryption.
        """
        if len(content) < 32:
            return FileValidationResult(
                is_valid=False,
                detected_mime="application/pdf",
                error_code="PDF_MALFORMED_STRUCTURE",
                error_message="PDF payload is truncated or too small to be a valid document."
            )

        if not content.startswith(b"%PDF-") and b"%PDF-" not in content[:1024]:
            return FileValidationResult(
                is_valid=False,
                detected_mime="application/pdf",
                error_code="PDF_HEADER_MISSING",
                error_message="Valid %PDF- header not found in file."
            )

        # Look for %%EOF in trailing 4096 bytes
        trailing_window = content[-4096:] if len(content) > 4096 else content
        if b"%%EOF" not in trailing_window:
            return FileValidationResult(
                is_valid=False,
                detected_mime="application/pdf",
                error_code="PDF_MALFORMED_STRUCTURE",
                error_message="PDF missing closing %%EOF marker (truncated document)."
            )

        # Inspect for dangerous PDF objects
        for pattern, err_code, err_msg in cls.SUSPICIOUS_PDF_PATTERNS:
            if pattern.search(content):
                return FileValidationResult(
                    is_valid=False,
                    detected_mime="application/pdf",
                    error_code=err_code,
                    error_message=err_msg
                )

        return FileValidationResult(
            is_valid=True,
            detected_mime="application/pdf",
            metadata={"format": "PDF", "bytes": len(content)}
        )

    @classmethod
    def validate_image(cls, content: bytes) -> FileValidationResult:
        """
        Decodes image server-side, verifies raster integrity,
        blocks decompression bombs, and strips unnecessary metadata.
        """
        max_pixels = getattr(settings, 'MAX_IMAGE_PIXELS', DEFAULT_MAX_IMAGE_PIXELS)

        try:
            with Image.open(io.BytesIO(content)) as img:
                img_format = img.format
                if img_format not in ("JPEG", "PNG"):
                    return FileValidationResult(
                        is_valid=False,
                        detected_mime="image/unknown",
                        error_code="IMAGE_UNSUPPORTED_FORMAT",
                        error_message=f"Image format '{img_format}' is not in the safe allowlist (JPEG, PNG)."
                    )

                width, height = img.size
                if width <= 0 or height <= 0:
                    return FileValidationResult(
                        is_valid=False,
                        detected_mime=f"image/{img_format.lower()}",
                        error_code="IMAGE_INVALID_DIMENSIONS",
                        error_message=f"Invalid image dimensions: {width}x{height}."
                    )

                total_pixels = width * height
                if total_pixels > max_pixels or width > 10000 or height > 10000:
                    return FileValidationResult(
                        is_valid=False,
                        detected_mime=f"image/{img_format.lower()}",
                        error_code="IMAGE_DECOMPRESSION_BOMB",
                        error_message=f"Image resolution {width}x{height} ({total_pixels} pixels) exceeds maximum security threshold."
                    )

                # Verify integrity
                img.verify()

                # Reopen to sanitize EXIF / GPS metadata
                with Image.open(io.BytesIO(content)) as img_clean:
                    # Strip EXIF GPS tags while preserving visual raster
                    out_buffer = io.BytesIO()
                    save_format = img_format
                    # Convert RGBA to RGB for JPEG if necessary
                    if save_format == "JPEG" and img_clean.mode in ("RGBA", "P"):
                        img_clean = img_clean.convert("RGB")
                    img_clean.save(out_buffer, format=save_format)
                    sanitized_bytes = out_buffer.getvalue()

                detected_mime = "image/jpeg" if img_format == "JPEG" else "image/png"
                return FileValidationResult(
                    is_valid=True,
                    detected_mime=detected_mime,
                    metadata={"width": width, "height": height, "format": img_format},
                    sanitized_bytes=sanitized_bytes or content
                )

        except Exception as exc:
            return FileValidationResult(
                is_valid=False,
                detected_mime="image/corrupted",
                error_code="IMAGE_DECODE_ERROR",
                error_message=f"Failed to decode raster image: {exc}"
            )

    @classmethod
    def validate_file(
        cls,
        content: bytes,
        declared_filename: str,
        declared_mime: str,
        max_size_bytes: int = 10 * 1024 * 1024
    ) -> FileValidationResult:
        """
        Master gate for incoming files:
        1. Non-empty check
        2. Maximum size check
        3. Real MIME detection via magic bytes
        4. Consistency between declared and detected MIME
        5. Deep content security verification (PDF / Image)
        """
        if not content:
            return FileValidationResult(
                is_valid=False,
                detected_mime="application/x-empty",
                error_code="EMPTY_FILE",
                error_message="Uploaded file payload is empty (0 bytes)."
            )

        if len(content) > max_size_bytes:
            return FileValidationResult(
                is_valid=False,
                detected_mime="application/octet-stream",
                error_code="FILE_SIZE_EXCEEDED",
                error_message=f"File size {len(content)} bytes exceeds maximum permitted size of {max_size_bytes} bytes."
            )

        detected_mime = FileContentDetector.detect_mime(content)
        allowed_mimes = getattr(settings, 'ALLOWED_MIME_TYPES', ['application/pdf', 'image/jpeg', 'image/png'])

        # Security check: dangerous binaries / scripts
        if detected_mime not in allowed_mimes:
            return FileValidationResult(
                is_valid=False,
                detected_mime=detected_mime,
                error_code="UNSAFE_FILE_TYPE",
                error_message=f"Detected MIME type '{detected_mime}' is not permitted. Allowed types: {', '.join(allowed_mimes)}."
            )

        # Consistency check: declared vs detected
        # Allow image/jpg vs image/jpeg alias
        norm_declared = declared_mime.lower().replace("jpg", "jpeg").strip()
        norm_detected = detected_mime.lower().replace("jpg", "jpeg").strip()
        if norm_declared and norm_declared != norm_detected:
            return FileValidationResult(
                is_valid=False,
                detected_mime=detected_mime,
                error_code="CONTENT_TYPE_MISMATCH",
                error_message=f"Declared Content-Type '{declared_mime}' does not match detected binary signature '{detected_mime}'."
            )

        # Deep validation
        if detected_mime == "application/pdf":
            return cls.validate_pdf(content)
        elif detected_mime in ("image/jpeg", "image/png"):
            return cls.validate_image(content)

        return FileValidationResult(
            is_valid=False,
            detected_mime=detected_mime,
            error_code="UNSUPPORTED_TYPE",
            error_message=f"No deep validator configured for MIME type '{detected_mime}'."
        )
