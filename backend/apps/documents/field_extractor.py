import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from django.conf import settings
from .ocr_engines import RawOCRBlock


@dataclass
class ExtractedFieldCandidate:
    field_code: str
    field_label: str
    raw_value: str
    normalized_value: Any
    confidence: float
    page_number: int
    bounding_box: Dict[str, float]
    extraction_method: str = "REGEX_ANCHOR"
    block_index: int = 0
    pipeline_version: str = "1.0.0"


class ProvisionalFieldExtractor:
    """
    Deterministic rule-based provisional field extractor.
    Extracts structured values from OCR text blocks with bounding boxes and evidence links.
    Trust rank: OCR_PROVISIONAL (10).
    """

    VERSION = "1.0.0"

    # Regex patterns for dates
    DATE_PATTERNS = [
        r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b',  # DD/MM/YYYY or DD-MM-YYYY
        r'\b(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b',  # YYYY-MM-DD
    ]

    # Academic year regex: 2024-25, 2025-2026
    ACADEMIC_YEAR_PATTERN = re.compile(r'\b(20\d\d)\s*[-/]\s*(\d{2,4})\b')

    @classmethod
    def _parse_date(cls, text: str) -> Optional[str]:
        for pat in cls.DATE_PATTERNS:
            match = re.search(pat, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups[0]) == 4:  # YYYY-MM-DD
                        d = int(groups[2])
                        m = int(groups[1])
                        y = int(groups[0])
                    else:  # DD-MM-YYYY
                        d = int(groups[0])
                        m = int(groups[1])
                        y = int(groups[2])
                    dt = date(y, m, d)
                    return dt.isoformat()
                except Exception:
                    continue
        return None

    @classmethod
    def _parse_currency(cls, text: str) -> Optional[float]:
        # Handle formats: Rs. 4,50,000 / ₹ 500000 / 4.5 Lakh / 450000/-
        cleaned = text.replace(',', '').replace('/-', '')
        
        # Look for "X Lakh" or "X Lakhs"
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lacs?)\b', cleaned, re.IGNORECASE)
        if lakh_match:
            try:
                val = float(lakh_match.group(1)) * 100_000
                return round(val, 2)
            except Exception:
                pass

        # Look for direct numbers near currency symbols or keywords
        num_match = re.search(r'(?:rs\.?|inr|₹)?\s*(\d{4,9})\b', cleaned, re.IGNORECASE)
        if num_match:
            try:
                return float(num_match.group(1))
            except Exception:
                pass
        return None

    @classmethod
    def extract_fields(
        cls,
        pages_blocks: Dict[int, List[RawOCRBlock]],
        full_text: str
    ) -> List[ExtractedFieldCandidate]:
        """
        Extracts provisional field values across all pages and blocks.
        """
        candidates: List[ExtractedFieldCandidate] = []
        pipeline_ver = getattr(settings, 'OCR_PIPELINE_VERSION', cls.VERSION)

        for page_num, blocks in pages_blocks.items():
            for block_idx, block in enumerate(blocks):
                text = block.text.strip()
                text_lower = text.lower()
                bbox = {
                    "x": block.bbox_x,
                    "y": block.bbox_y,
                    "width": block.bbox_width,
                    "height": block.bbox_height
                }

                # 1. Annual Family Income
                if any(k in text_lower for k in ('income', 'annual', 'rs.', '₹', 'family income')):
                    amount = cls._parse_currency(text)
                    if amount is not None and amount > 0:
                        candidates.append(
                            ExtractedFieldCandidate(
                                field_code="annual_family_income",
                                field_label="Annual Family Income",
                                raw_value=text,
                                normalized_value=amount,
                                confidence=round(block.confidence * 0.95, 2),
                                page_number=page_num,
                                bounding_box=bbox,
                                extraction_method="REGEX_CURRENCY",
                                block_index=block_idx,
                                pipeline_version=pipeline_ver
                            )
                        )

                # 2. Date of Birth
                if any(k in text_lower for k in ('dob', 'date of birth', 'birth date', 'd.o.b')):
                    dob_val = cls._parse_date(text)
                    if dob_val:
                        candidates.append(
                            ExtractedFieldCandidate(
                                field_code="date_of_birth",
                                field_label="Date of Birth",
                                raw_value=text,
                                normalized_value=dob_val,
                                confidence=round(block.confidence * 0.92, 2),
                                page_number=page_num,
                                bounding_box=bbox,
                                extraction_method="REGEX_DATE",
                                block_index=block_idx,
                                pipeline_version=pipeline_ver
                            )
                        )

                # 3. Certificate Number / Reference Number
                cert_match = re.search(
                    r'(?:certificate\s+no\.?|cert\.?\s+no\.?|ref\s+no\.?|sl\.?\s+no\.?|application\s+no\.?)[:\s]+([A-Z0-9\/\-_]{5,30})\b',
                    text,
                    re.IGNORECASE
                )
                if cert_match:
                    cert_no = cert_match.group(1).strip()
                    candidates.append(
                        ExtractedFieldCandidate(
                            field_code="certificate_number",
                            field_label="Certificate / Registration Number",
                            raw_value=text,
                            normalized_value=cert_no,
                            confidence=round(block.confidence * 0.94, 2),
                            page_number=page_num,
                            bounding_box=bbox,
                            extraction_method="REGEX_CERT_NO",
                            block_index=block_idx,
                            pipeline_version=pipeline_ver
                        )
                    )

                # 4. Issue Date
                if any(k in text_lower for k in ('issued on', 'date of issue', 'issue date', 'dated')):
                    issue_val = cls._parse_date(text)
                    if issue_val:
                        candidates.append(
                            ExtractedFieldCandidate(
                                field_code="issue_date",
                                field_label="Issue Date",
                                raw_value=text,
                                normalized_value=issue_val,
                                confidence=round(block.confidence * 0.90, 2),
                                page_number=page_num,
                                bounding_box=bbox,
                                extraction_method="REGEX_DATE",
                                block_index=block_idx,
                                pipeline_version=pipeline_ver
                            )
                        )

                # 5. Validity / Expiry Date
                if any(k in text_lower for k in ('valid up to', 'valid until', 'expiry date', 'valid through')):
                    valid_val = cls._parse_date(text)
                    if valid_val:
                        candidates.append(
                            ExtractedFieldCandidate(
                                field_code="validity_date",
                                field_label="Validity / Expiry Date",
                                raw_value=text,
                                normalized_value=valid_val,
                                confidence=round(block.confidence * 0.90, 2),
                                page_number=page_num,
                                bounding_box=bbox,
                                extraction_method="REGEX_DATE",
                                block_index=block_idx,
                                pipeline_version=pipeline_ver
                            )
                        )

                # 6. Academic Year
                acad_match = cls.ACADEMIC_YEAR_PATTERN.search(text)
                if acad_match:
                    y1 = acad_match.group(1)
                    y2 = acad_match.group(2)
                    norm_acad = f"{y1}-{y2[-2:]}" if len(y2) == 4 else f"{y1}-{y2}"
                    candidates.append(
                        ExtractedFieldCandidate(
                            field_code="academic_year",
                            field_label="Academic Year",
                            raw_value=text,
                            normalized_value=norm_acad,
                            confidence=round(block.confidence * 0.93, 2),
                            page_number=page_num,
                            bounding_box=bbox,
                            extraction_method="REGEX_ACADEMIC_YEAR",
                            block_index=block_idx,
                            pipeline_version=pipeline_ver
                        )
                    )

                # 7. Applicant Name (from anchors like 'This is to certify that Shri/Smt/Kumari <Name>')
                name_match = re.search(
                    r'(?:certify\s+that|name\s*[:\-]|student\s+name\s*[:\-])\s*(?:shri|smt|kumari|mr\.?|ms\.?)?\s*([A-Za-z\s]{3,40})\b',
                    text,
                    re.IGNORECASE
                )
                if name_match:
                    parsed_name = name_match.group(1).strip()
                    if len(parsed_name) >= 3 and not any(k in parsed_name.lower() for k in ('certificate', 'office', 'government')):
                        candidates.append(
                            ExtractedFieldCandidate(
                                field_code="applicant_name",
                                field_label="Applicant Name",
                                raw_value=text,
                                normalized_value=parsed_name.title(),
                                confidence=round(block.confidence * 0.88, 2),
                                page_number=page_num,
                                bounding_box=bbox,
                                extraction_method="REGEX_ANCHOR_NAME",
                                block_index=block_idx,
                                pipeline_version=pipeline_ver
                            )
                        )

                # 8. Roll Number / Registration Number
                roll_match = re.search(
                    r'(?:roll\s+no\.?|registration\s+no\.?|enrollment\s+no\.?)[:\s]+([A-Z0-9\-_]{4,25})\b',
                    text,
                    re.IGNORECASE
                )
                if roll_match:
                    roll_no = roll_match.group(1).strip()
                    candidates.append(
                        ExtractedFieldCandidate(
                            field_code="roll_number",
                            field_label="Roll / Registration Number",
                            raw_value=text,
                            normalized_value=roll_no,
                            confidence=round(block.confidence * 0.91, 2),
                            page_number=page_num,
                            bounding_box=bbox,
                            extraction_method="REGEX_ROLL_NO",
                            block_index=block_idx,
                            pipeline_version=pipeline_ver
                        )
                    )

        # De-duplicate candidates per field_code: keep highest confidence
        unique_map: Dict[str, ExtractedFieldCandidate] = {}
        for cand in candidates:
            code = cand.field_code
            if code not in unique_map or cand.confidence > unique_map[code].confidence:
                unique_map[code] = cand

        return list(unique_map.values())
