import hashlib
import json
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from django.conf import settings
from PIL import Image

logger = logging.getLogger('apps.documents.ocr')


@dataclass
class RawOCRBlock:
    text: str
    confidence: float
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    polygon: List[List[float]] = field(default_factory=list)
    block_type: str = 'TEXT'
    language: str = 'eng'
    reading_order: int = 0


class BaseOCREngine(ABC):
    """
    Authoritative abstract adapter interface for OCR engines.
    Isolates the domain layer from specific OCR engine dependencies.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Name of the OCR engine (e.g. 'PaddleOCR')."""
        pass

    @property
    @abstractmethod
    def engine_version(self) -> str:
        """Exact installed version of the OCR engine."""
        pass

    @property
    def pipeline_version(self) -> str:
        """Application OCR pipeline version."""
        return getattr(settings, 'OCR_PIPELINE_VERSION', '1.0.0')

    @abstractmethod
    def get_configuration_hash(self) -> str:
        """Deterministic cryptographic hash representing engine parameters and models."""
        pass

    @abstractmethod
    def process_image(self, image: Image.Image, page_num: int = 1) -> List[RawOCRBlock]:
        """
        Processes a rendered PIL page image and returns granular text blocks
        with coordinates and confidence scores.
        """
        pass


class PaddleOCREngine(BaseOCREngine):
    """
    Primary OCR engine implementation using PaddleOCR.
    Supports multiline detection, angle classification, and bounding box extraction.
    """

    _instance = None
    _paddle_ocr_client = None

    def __init__(self, lang: str = 'en', use_angle_cls: bool = True):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self._cached_version = None

    @property
    def engine_name(self) -> str:
        return 'PaddleOCR'

    @property
    def engine_version(self) -> str:
        if not self._cached_version:
            try:
                import importlib.metadata
                self._cached_version = importlib.metadata.version('paddleocr')
            except Exception:
                self._cached_version = '3.7.0'
        return self._cached_version

    def get_configuration_hash(self) -> str:
        config_dict = {
            "engine": self.engine_name,
            "version": self.engine_version,
            "lang": self.lang,
            "use_angle_cls": self.use_angle_cls,
            "pipeline_version": self.pipeline_version,
        }
        raw = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    _paddle_ocr_clients: Dict[str, Any] = {}
    _client_lock = threading.Lock()

    def _get_client(self):
        if self.lang in PaddleOCREngine._paddle_ocr_clients:
            return PaddleOCREngine._paddle_ocr_clients[self.lang]

        with PaddleOCREngine._client_lock:
            # Double-checked locking across worker threads
            if self.lang in PaddleOCREngine._paddle_ocr_clients:
                return PaddleOCREngine._paddle_ocr_clients[self.lang]

            try:
                from paddleocr import PaddleOCR
                # PaddleOCR 3.x / 2.x compatibility: try standard kwargs first
                try:
                    client = PaddleOCR(lang=self.lang)
                except TypeError:
                    client = PaddleOCR(lang=self.lang, enable_mkldnn=False)

                PaddleOCREngine._paddle_ocr_clients[self.lang] = client
                return client
            except Exception as exc:
                logger.error(f"Failed to initialize PaddleOCR client for lang '{self.lang}': {exc}")
                raise RuntimeError(f"PaddleOCR client initialization failed for lang '{self.lang}': {exc}")

    def process_image(self, image: Image.Image, page_num: int = 1) -> List[RawOCRBlock]:
        import numpy as np

        # Convert PIL Image to RGB numpy array for PaddleOCR
        if image.mode != 'RGB':
            image = image.convert('RGB')
        img_np = np.array(image)

        client = self._get_client()

        try:
            # PaddleOCR 3.x supports predict(), while 2.x uses ocr()
            if hasattr(client, 'predict'):
                results = list(client.predict(img_np))
            else:
                results = client.ocr(img_np, cls=self.use_angle_cls)
        except Exception as exc:
            logger.error(f"PaddleOCR execution failed on page {page_num}: {exc}")
            raise RuntimeError(f"PaddleOCR processing error on page {page_num}: {exc}")

        blocks: List[RawOCRBlock] = []
        if not results:
            return blocks

        # Case 1: PaddleOCR 3.x dict format [{'rec_texts': [...], 'rec_scores': [...], 'rec_polys': [...]}]
        if isinstance(results[0], dict):
            page_dict = results[0]
            rec_texts = page_dict.get('rec_texts', [])
            rec_scores = page_dict.get('rec_scores', [])
            rec_polys = page_dict.get('rec_polys', [])
            rec_boxes = page_dict.get('rec_boxes', [])

            for idx, text in enumerate(rec_texts):
                clean_text = str(text).strip()
                if not clean_text:
                    continue

                conf = float(rec_scores[idx]) if idx < len(rec_scores) else 1.0
                
                # Extract coordinates
                if idx < len(rec_polys) and rec_polys[idx] is not None:
                    poly = rec_polys[idx]
                    poly_list = [[float(p[0]), float(p[1])] for p in poly]
                    xs = [p[0] for p in poly_list]
                    ys = [p[1] for p in poly_list]
                    min_x = float(min(xs))
                    min_y = float(min(ys))
                    width = float(max(xs) - min_x)
                    height = float(max(ys) - min_y)
                elif idx < len(rec_boxes) and rec_boxes[idx] is not None:
                    box = rec_boxes[idx]
                    min_x = float(box[0])
                    min_y = float(box[1])
                    width = float(box[2] - box[0])
                    height = float(box[3] - box[1])
                    poly_list = [[min_x, min_y], [min_x + width, min_y], [min_x + width, min_y + height], [min_x, min_y + height]]
                else:
                    min_x, min_y, width, height = 0.0, 0.0, float(image.width), float(image.height)
                    poly_list = []

                blocks.append(
                    RawOCRBlock(
                        text=clean_text,
                        confidence=round(conf, 4),
                        bbox_x=round(min_x, 2),
                        bbox_y=round(min_y, 2),
                        bbox_width=round(width, 2),
                        bbox_height=round(height, 2),
                        polygon=poly_list,
                        block_type='TEXT',
                        language=self.lang,
                        reading_order=idx + 1
                    )
                )
            return blocks

        # Case 2: PaddleOCR 2.x nested list format [[[polygon, (text, conf)], ...]]
        page_results = results[0]
        if isinstance(page_results, list):
            for idx, line in enumerate(page_results):
                try:
                    if not line or len(line) < 2:
                        continue
                    polygon = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    text_conf = line[1]  # (text, confidence)
                    if isinstance(text_conf, (tuple, list)):
                        text = str(text_conf[0]).strip()
                        conf = float(text_conf[1])
                    else:
                        text = str(text_conf).strip()
                        conf = 1.0

                    if not text:
                        continue

                    # Compute bounding box
                    xs = [p[0] for p in polygon]
                    ys = [p[1] for p in polygon]
                    min_x = float(min(xs))
                    min_y = float(min(ys))
                    width = float(max(xs) - min_x)
                    height = float(max(ys) - min_y)

                    clean_polygon = [[float(p[0]), float(p[1])] for p in polygon]

                    blocks.append(
                        RawOCRBlock(
                            text=text,
                            confidence=round(conf, 4),
                            bbox_x=round(min_x, 2),
                            bbox_y=round(min_y, 2),
                            bbox_width=round(width, 2),
                            bbox_height=round(height, 2),
                            polygon=clean_polygon,
                            block_type='TEXT',
                            language=self.lang,
                            reading_order=idx + 1
                        )
                    )
                except Exception as line_exc:
                    logger.warning(f"Error parsing OCR block {idx} on page {page_num}: {line_exc}")
                    continue

        return blocks


class MockOCREngine(BaseOCREngine):
    """
    Deterministic mock OCR engine for fast isolated unit testing.
    Can be configured with synthetic blocks or simulated errors.
    """

    def __init__(self, synthetic_blocks: Optional[List[RawOCRBlock]] = None, simulate_error: bool = False):
        self.synthetic_blocks = synthetic_blocks
        self.simulate_error = simulate_error

    @property
    def engine_name(self) -> str:
        return 'MockOCREngine'

    @property
    def engine_version(self) -> str:
        return '1.0.0-mock'

    def get_configuration_hash(self) -> str:
        return hashlib.sha256(b"mock_ocr_config_hash_v1").hexdigest()

    def process_image(self, image: Image.Image, page_num: int = 1) -> List[RawOCRBlock]:
        if self.simulate_error:
            raise RuntimeError("MOCK_OCR_SIMULATED_ENGINE_ERROR")

        if self.synthetic_blocks is not None:
            return self.synthetic_blocks

        # Default fallback synthetic block based on image dimensions
        w, h = image.size
        return [
            RawOCRBlock(
                text=f"Sample Extracted Document Text Page {page_num}",
                confidence=0.95,
                bbox_x=10.0,
                bbox_y=20.0,
                bbox_width=float(w - 20),
                bbox_height=30.0,
                polygon=[[10.0, 20.0], [float(w - 10), 20.0], [float(w - 10), 50.0], [10.0, 50.0]],
                block_type='HEADER',
                language='eng',
                reading_order=1
            )
        ]


def get_ocr_engine(backend: Optional[str] = None, lang: Optional[str] = None) -> BaseOCREngine:
    """
    Factory function returning the configured OCR engine adapter.
    """
    engine_name = backend or getattr(settings, 'OCR_ENGINE_BACKEND', 'paddleocr')
    language = lang or getattr(settings, 'OCR_DEFAULT_LANGUAGE', 'en')
    if engine_name.lower() == 'mock':
        return MockOCREngine()
    elif engine_name.lower() == 'paddleocr':
        return PaddleOCREngine(lang=language)
    else:
        logger.warning(f"Unknown OCR_ENGINE_BACKEND '{engine_name}', falling back to PaddleOCR.")
        return PaddleOCREngine(lang=language)
