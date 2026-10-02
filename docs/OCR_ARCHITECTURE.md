# SECURE OCR & DOCUMENT INTELLIGENCE FOUNDATION ARCHITECTURE

> **ARCHITECTURAL MANDATE:**  
> **OCR is assistive evidence extraction and is not an eligibility decision engine.**  
> OCR extracted data represents provisional evidence that must be verified according to the authoritative trust hierarchy. OCR output must NEVER directly decide or bypass scholarship eligibility.

---

## 1. Executive Architectural Overview

The Secure OCR & Document Intelligence Foundation extends the ingestion pipeline by adding automated text extraction, document classification, bounding-box level evidence preservation, and conflict detection.

The foundation enforces a strict non-negotiable security boundary: **only documents in the `SAFE` lifecycle status may enter OCR processing**. Pathological files, malformed PDFs, and oversized images are intercepted by defensive resource limiters before worker exhaustion can occur.

```text
ApplicantDocument
      │
      ▼
Security Validation (ClamAV + Magic MIME + Structure Checks)
      │
      ▼
SAFE DOCUMENT
      │
      ▼  (transaction.on_commit -> Celery task -> Redis)
OCR JOB (Status: PENDING -> RUNNING)
      │
      ▼
DocumentOCRRenderer (PDFium / Pillow with Memory & Pixel Ceilings)
      │
      ▼
BaseOCREngine Adapter (Primary: PaddleOCR / Fallback: MockOCREngine)
      │
      ▼
Immutable OCRResult + OCRPage + OCRBlock (with bounding boxes & polygons)
      │
      ▼
Deterministic Document Classifier (INCOME, CASTE, DOMICILE, MARKSHEET, or UNKNOWN)
      │
      ▼
Provisional Field Extractor (Regex + Anchors + Dictionaries)
      │
      ▼
Evidence Linking (App -> Doc -> DocVersion -> OCRResult -> OCRPage -> OCRBlock -> Field)
      │
      ▼
Conflict Detection & Human Verification Queue (MATERIAL_CONFLICT -> Officer Review)
      │
      ▼
Authoritative Deterministic Eligibility Engine (Untouched & Authoritative)
```

---

## 2. Authoritative Security Boundary & Lifecycle Guards

### 2.1 The Single Authoritative Service Guard
An OCR job is strictly barred from executing against any document not in the `SAFE` state. This invariant is enforced in `OCRService.validate_document_can_enter_ocr(document)`:

Refused States:
* `INITIATED`
* `UPLOADING`
* `UPLOADED`
* `QUARANTINED`
* `SCANNING`
* `PROMOTION_PENDING`
* `REJECTED`
* `SCAN_ERROR`
* `RECONCILIATION_REQUIRED`
* `REVOKED`

Any attempt to initiate OCR on an unapproved document raises an `InvalidDocumentStateForOCRError` and halts execution immediately.

### 2.2 Asynchronous Isolation
OCR is strictly decoupled from the synchronous HTTP upload request:
1. HTTP upload occurs within `transaction.atomic()`.
2. Document is placed into quarantine and scanned for malware and structure violations.
3. Upon promotion to `SAFE`, `transaction.on_commit()` dispatches the Celery task `run_ocr_task` through Redis.
4. If the OCR worker crashes, fails, or exhausts retries, **the document security status remains `SAFE`** and is never corrupted to `REJECTED`.

---

## 3. Data Model Architecture

The data model preserves fine-grained evidence down to the geometric polygon and bounding box of each recognized word or line.

### 3.1 OCRJob
Manages asynchronous task execution, state, and retries.
* `document`: Reference to `ApplicantDocument`
* `document_version`: Reference to specific immutable `DocumentVersion`
* `status`: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `RETRY_PENDING`, `CANCELLED`
* `attempts`: Bounded retry counter (maximum 3 attempts)
* `idempotency_key`: Deterministic hash `sha256(f"{doc_version_id}:{pipeline_version}:{job_type}")`
* `engine_name`: Name of active engine adapter (`PaddleOCR`)
* `pipeline_version`: Version string (`v1.0.0-phase7`)
* `correlation_id`: Distributed tracing identifier

### 3.2 OCRResult (Immutable)
Created once upon successful completion and protected against mutation:
* Overrides `clean()`, `save()`, and `delete()` to raise `RuntimeError` if an update or deletion is attempted on an existing record.
* Contains `result_hash` (SHA-256 of canonical text aggregate, page count, and engine configuration).
* Reruns generate a distinct new `OCRResult` version rather than mutating existing history.

### 3.3 OCRPage
* 1-indexed `page_number`
* Dimensions: `width`, `height`, `rotation` (0, 90, 180, 270)
* Aggregated page text and page-level confidence score
* Unique constraint: `(ocr_result, page_number)`

### 3.4 OCRBlock
* `extracted_text`: Raw recognized text
* `confidence`: Float `0.0` to `1.0`
* Bounding Box: `bbox_x`, `bbox_y`, `bbox_width`, `bbox_height`
* Polygon: 4-corner coordinate array `[[x1, y1], [x2, y2], [x3, y3], [x4, y4]]`
* `reading_order`: 1-indexed sequence number
* `block_type`: `TEXT`, `TITLE`, `TABLE_CELL`

### 3.5 DocumentClassificationResult
* `predicted_type`: E.g., `INCOME_CERTIFICATE`, `CASTE_CERTIFICATE`, `DOMICILE_CERTIFICATE`, or `UNKNOWN`
* `confidence`: Float `0.0` to `1.0`
* `classification_method`: `DETERMINISTIC_RULES_V1`
* `evidence_summary`: Matched keywords and triggers

### 3.6 ProvisionalExtractedField
* `field_code`: E.g., `annual_family_income`, `certificate_number`, `date_of_birth`
* `raw_value`: Raw text snippet as recognized by OCR
* `normalized_value`: Strongly typed value (float, date, string)
* `trust_level`: Strictly `OCR_PROVISIONAL` (rank 10)
* Full foreign key back-pointers to `ocr_page` and `ocr_block` for officer UI highlighting.

---

## 4. OCR Engine Adapter Architecture

To prevent hard vendor lock-in, all OCR execution routes through `BaseOCREngine`:

```python
class BaseOCREngine(ABC):
    @property
    @abstractmethod
    def engine_name(self) -> str: pass

    @property
    @abstractmethod
    def engine_version(self) -> str: pass

    @abstractmethod
    def get_configuration_hash(self) -> str: pass

    @abstractmethod
    def process_image(self, image: Image.Image, page_num: int = 1) -> List[RawOCRBlock]: pass
```

### PaddleOCR Engine Adapter (`PaddleOCREngine`)
* Primary production engine (`paddleocr==3.7.0`, `paddlepaddle==3.2.2` CPU, `pypdfium2==5.13.0`, `python==3.13.x`).
* Direct PaddleOCR 3.x `predict()` pipeline path (legacy `ocr()` fallback removed).
* Bounded CPU execution (`MAX_DET_SIDE = 700`, `text_det_limit_side_len = 700`, `text_det_limit_type = 'max'`).
* Disabled heavy pre-processing: `use_doc_unwarping=False`, `use_doc_orientation_classify=False`, `use_textline_orientation=False`, `enable_mkldnn=False`.
* Returns normalized `RawOCRBlock` representations containing text, confidence, and 4-point bounding polygons.

### Mock OCR Engine (`MockOCREngine`)
* Zero-dependency deterministic adapter used for high-speed isolated unit testing and simulating engine errors.

---

## 5. Confidence vs. Truth vs. Eligibility

| Layer | Value | Semantic Meaning | Can Mutate Database? | Can Alter Eligibility? |
|---|---|---|---|---|
| **OCR Recognition** | `confidence = 0.98` | The optical model is 98% sure the glyphs match this text. | No | **NEVER** |
| **Field Extraction** | `trust = OCR_PROVISIONAL (10)` | Extracted provisionally from a document. Subservient to applicant declaration (20). | Stored as provisional | **NEVER** |
| **Officer Verification** | `trust = OFFICER_VERIFIED (50)` | Human verification officer verified document evidence against scheme requirements. | Yes | Verified for evaluation |
| **Deterministic Rules** | `ELIGIBLE / INELIGIBLE` | Evaluated solely on authoritative verified fields. | Yes | Yes |

### Unbroken Field Trust Hierarchy
1. `OFFICER_VERIFIED` (Rank 50)
2. `OFFICIAL_INTEGRATION` (Rank 40)
3. `VERIFIED_DOCUMENT` (Rank 30)
4. `SYSTEM` (Rank 25)
5. `APPLICANT_DECLARED` (Rank 20)
6. `OCR_PROVISIONAL` (Rank 10)

`OCR_PROVISIONAL` **never** outranks or overwrites `APPLICANT_DECLARED`.

---

## 6. Conflict Detection & Human Review

When an applicant declares an income of ₹500,000 and OCR extracts ₹450,000 from an uploaded certificate:
1. Both values are preserved in `ApplicationFieldValue` with their respective trust ranks.
2. The discrepancy exceeds the 5% / ₹1,000 tolerance threshold.
3. An audit event `FIELD_CONFLICT_DETECTED` is emitted.
4. A `VerificationQueueItem` is generated with conflict type `MATERIAL_CONFLICT`.
5. The application remains in its workflow state for human officer review; **neither the document nor the application is automatically rejected**.

---

## 7. Resource Ceilings & Defensive Preprocessing

| Metric | Config Setting | Ceiling | Defensive Action on Violation |
|---|---|---|---|
| Maximum Pages | `MAX_OCR_PAGES` | 10 pages | Rejects with `MAX_PAGE_COUNT_EXCEEDED`. Job marked FAILED; doc remains SAFE. |
| Page Dimension | `MAX_OCR_PAGE_DIMENSION` | 4,000 px | Dynamically scaled down with high-quality Lanczos resampling. |
| Total Pixels | `MAX_OCR_TOTAL_PIXELS` | 25,000,000 px | Rejects with `MAX_TOTAL_PIXELS_EXCEEDED` before decompression bomb can exhaust RAM. |
| Render DPI | Internal PDFium scale | 150 DPI | Balanced optical resolution avoiding gigabyte memory allocation. |
| Malformed PDF | Structure parser | Corrupt stream | Rejects with `CORRUPT_OR_MALFORMED_PDF`. Worker cleans up gracefully. |

---

## 8. Audit Trail & Provenance

The foundation emits structured audit logs without leaking PII:
* `OCR_JOB_CREATED`: Documents job dispatch with idempotency key.
* `OCR_STARTED`: Captures worker host, process ID, and start timestamp.
* `OCR_COMPLETED`: Captures duration, page count, and deterministic `result_hash`.
* `OCR_FAILED`: Captures sanitized error code and error message.
* `DOCUMENT_CLASSIFIED`: Records classified category and confidence.
* `FIELD_EXTRACTED`: Records list of extracted field codes.
* `FIELD_CONFLICT_DETECTED`: Records field code, declared value, and extracted value.

---

## 9. Explicit Non-Goals

1. **No LLM Integration**: No OpenAI, Anthropic Claude, Google Gemini, or local HuggingFace/Ollama models are used. All extraction is deterministic.
2. **No Automatic Ineligibility**: OCR errors, low confidences, or unreadable certificates never automatically reject an applicant.
3. **No Direct Database Overwrite**: OCR extraction never overwrites existing applicant form data.
4. **No Public Storage Access**: Rendered pages and intermediate images are processed in volatile memory and cleaned up immediately.

---

## 10. Empirical OCR Performance Measurements

Actual observed measurements recorded on host CPU execution environment (Windows 11 x86_64, CPU inference, no GPU/MKLDNN acceleration):

| Benchmark Scenario | Workload | Actual Measured Duration | Mean Rate | Details / Notes |
|---|---|---|---|---|
| **First Inference (Cold Start)** | 1 Page (English) | **19.465 s** | 19.47 s/page | Includes model initialization & graph loading (`PP-OCRv6_medium_rec`) |
| **Subsequent Inference (Warm)** | 1 Page (English) | **15.510 s** | 15.51 s/page | In-memory model instance, 4 blocks recognized |
| **Three-Page Document (Warm)** | 3 Pages (English) | **42.805 s** | **14.268 s/page** | Continuous multi-page pipeline execution |
| **Devanagari Document (Warm)** | 1 Page (Hindi) | **28.437 s** | 28.44 s/page | `devanagari_PP-OCRv5_mobile_rec`, 4 Devanagari blocks |

> **Engineering Note on Scalability:**  
> CPU OCR processing on Windows takes approximately 14–15 seconds per page for English text and ~28 seconds per page for complex Devanagari scripts. This confirms the baseline observation and underlines why OCR is decoupled into asynchronous background Celery worker tasks rather than blocking synchronous HTTP request/response loops.

---

## 11. Frozen Acceptance Test Contract

The acceptance test contract for the OCR Foundation is formally frozen.  
**Contract Frozen Timestamp:** `2026-09-30 02:00:00 UTC`

### Frozen Acceptance Contract Rule:
```text
APPLICATION CODE MAY CHANGE
ACCEPTANCE TEST CONTRACT MAY NOT CHANGE
```

No modifications to expected assertions, pass/fail conditions, required states, required counts, required provenance, or concurrency behavior are permitted without an approved, documented specification error.

### Frozen Test Files:
1. `backend/tests/integration/test_ocr_integration_gate.py` (Tests A through K)
2. `backend/tests/unit/test_ocr_pipeline_units.py` (Units 1 through 10)
3. `backend/tests/integration/test_infrastructure_gate.py` (Infrastructure Gate)
4. `backend/tests/unit/test_document_ingestion_units.py` (Document Security Ingestion Units)
5. `backend/tests/integration/test_document_ingestion_integration.py` (Document Ingestion Integration)

