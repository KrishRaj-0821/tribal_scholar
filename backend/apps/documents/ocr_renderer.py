import io
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from django.conf import settings
from PIL import Image, ImageOps

logger = logging.getLogger('apps.documents.ocr')


class OCRError(Exception):
    """Base exception for all OCR pipeline errors."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class ResourceExhaustionError(OCRError):
    """Raised when document violates OCR resource limits (pages, dimensions, pixels)."""
    pass


class MalformedDocumentError(OCRError):
    """Raised when document bytes are corrupt or structurally invalid for rendering."""
    pass


class UnsupportedFormatError(OCRError):
    """Raised when document format is not supported for OCR processing."""
    pass


@dataclass
class RenderedPage:
    page_number: int
    image: Image.Image
    width: int
    height: int
    rotation: int = 0


class DocumentOCRRenderer:
    """
    Controlled document-to-image page representation layer.
    Enforces strict resource limits, decompression safety, and bounded dimensions.
    Operates strictly on validated SAFE document binaries.
    """

    @classmethod
    def render_document_pages(
        cls,
        raw_bytes: bytes,
        mime_type: str,
        max_pages: Optional[int] = None,
        max_dimension: Optional[int] = None,
        max_total_pixels: Optional[int] = None
    ) -> List[RenderedPage]:
        """
        Renders safe document bytes into bounded Pillow image pages.
        Validates resource ceilings before and during rendering.
        """
        max_p = max_pages if max_pages is not None else getattr(settings, 'MAX_OCR_PAGES', 10)
        max_dim = max_dimension if max_dimension is not None else getattr(settings, 'MAX_OCR_PAGE_DIMENSION', 4000)
        max_pix = max_total_pixels if max_total_pixels is not None else getattr(settings, 'MAX_OCR_TOTAL_PIXELS', 25_000_000)

        # Decompression bomb safety ceiling
        Image.MAX_IMAGE_PIXELS = max_pix

        if not raw_bytes:
            raise MalformedDocumentError("EMPTY_DOCUMENT", "Document payload is empty (0 bytes).")

        normalized_mime = (mime_type or '').lower().strip()

        if 'pdf' in normalized_mime or raw_bytes.startswith(b"%PDF-"):
            return cls._render_pdf(raw_bytes, max_p, max_dim, max_pix)
        elif any(img_mime in normalized_mime for img_mime in ('image/jpeg', 'image/jpg', 'image/png')):
            return cls._render_image(raw_bytes, max_dim, max_pix)
        else:
            raise UnsupportedFormatError(
                "UNSUPPORTED_DOCUMENT_FORMAT",
                f"MIME type '{normalized_mime}' is not supported for OCR rendering."
            )

    @classmethod
    def _render_pdf(cls, raw_bytes: bytes, max_pages: int, max_dim: int, max_pix: int) -> List[RenderedPage]:
        import pypdfium2

        try:
            pdf = pypdfium2.PdfDocument(io.BytesIO(raw_bytes))
        except Exception as exc:
            logger.warning(f"Failed to parse PDF document for OCR rendering: {exc}")
            raise MalformedDocumentError("CORRUPT_OR_MALFORMED_PDF", f"Failed to parse PDF: {exc}")

        try:
            page_count = len(pdf)
        except Exception as exc:
            raise MalformedDocumentError("CORRUPT_OR_MALFORMED_PDF", f"Failed to read PDF page count: {exc}")

        if page_count == 0:
            raise MalformedDocumentError("EMPTY_PDF", "PDF document contains 0 pages.")

        if page_count > max_pages:
            raise ResourceExhaustionError(
                "MAX_PAGE_COUNT_EXCEEDED",
                f"Document contains {page_count} pages, exceeding the OCR processing limit of {max_pages} pages."
            )

        rendered_pages: List[RenderedPage] = []
        cumulative_pixels = 0

        for page_idx in range(page_count):
            page_num = page_idx + 1
            try:
                page = pdf[page_idx]
                rotation = page.get_rotation()

                # Render at 150 DPI (scale ~ 2.083 on 72 DPI base)
                # Standard resolution for OCR accuracy without pathological memory usage
                bitmap = page.render(scale=2.083)
                pil_image = bitmap.to_pil()

                # Normalize to RGB mode
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')

                w, h = pil_image.size

                # Check page dimension bounds
                if w > max_dim or h > max_dim:
                    # Bounded scale down if exceeding max dimension
                    scale_factor = min(max_dim / w, max_dim / h)
                    new_w = max(1, int(w * scale_factor))
                    new_h = max(1, int(h * scale_factor))
                    pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    w, h = pil_image.size

                page_pixels = w * h
                cumulative_pixels += page_pixels
                if cumulative_pixels > max_pix:
                    raise ResourceExhaustionError(
                        "MAX_TOTAL_PIXELS_EXCEEDED",
                        f"Cumulative rendered pixels ({cumulative_pixels}) exceeds ceiling ({max_pix})."
                    )

                rendered_pages.append(
                    RenderedPage(
                        page_number=page_num,
                        image=pil_image,
                        width=w,
                        height=h,
                        rotation=rotation
                    )
                )
            except ResourceExhaustionError:
                raise
            except Exception as exc:
                logger.warning(f"Error rendering PDF page {page_num}: {exc}")
                raise MalformedDocumentError(
                    "PAGE_RENDERING_ERROR",
                    f"Failed to render page {page_num}: {exc}"
                )

        return rendered_pages

    @classmethod
    def _render_image(cls, raw_bytes: bytes, max_dim: int, max_pix: int) -> List[RenderedPage]:
        try:
            image = Image.open(io.BytesIO(raw_bytes))
            image.verify()
        except Image.DecompressionBombError as dbe:
            raise ResourceExhaustionError(
                "DECOMPRESSION_BOMB_DETECTED",
                f"Image triggers decompression bomb threshold: {dbe}"
            )
        except Exception as exc:
            raise MalformedDocumentError(
                "CORRUPT_OR_MALFORMED_IMAGE",
                f"Corrupted or invalid image bytes: {exc}"
            )

        # Re-open after verify() (Pillow requirement)
        image = Image.open(io.BytesIO(raw_bytes))

        # Handle EXIF orientation
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass

        if image.mode != 'RGB':
            image = image.convert('RGB')

        w, h = image.size
        if (w * h) > max_pix:
            raise ResourceExhaustionError(
                "MAX_TOTAL_PIXELS_EXCEEDED",
                f"Image pixels ({w * h}) exceeds maximum permitted ({max_pix})."
            )

        if w > max_dim or h > max_dim:
            scale_factor = min(max_dim / w, max_dim / h)
            new_w = max(1, int(w * scale_factor))
            new_h = max(1, int(h * scale_factor))
            image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            w, h = image.size

        return [
            RenderedPage(
                page_number=1,
                image=image,
                width=w,
                height=h,
                rotation=0
            )
        ]
