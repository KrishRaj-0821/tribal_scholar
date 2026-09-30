# OCR SUPPORTED LANGUAGES SPECIFICATION

This document outlines the official language support matrix for the Tribal Scholar OCR & Document Intelligence Foundation.

> **CRITICAL ARCHITECTURAL PRINCIPLES:**
> 1. `OCR confidence != verification`
> 2. `OCR output != eligibility decision`
> 3. Support claims must be backed by deterministic synthetic or scanned integration tests running through the complete pipeline.

---

## 1. Language Support Tiers

| Tier | Definition | Production Policy |
|---|---|---|
| **VERIFIED SUPPORT** | Script and model pipeline thoroughly verified by automated deterministic integration tests through the complete OCR pipeline (`Input -> Render -> Model -> OCRResult -> OCRPage -> OCRBlock`). Provenance and bounded bounding boxes verified. | Approved for automated OCR processing into `OCR_PROVISIONAL` fields. |
| **EXPERIMENTAL** | Language models available in underlying OCR libraries but lack full automated regression test suites, custom token dictionaries, or statutory certificate regex extraction rules. | Require manual officer verification flag. Unverified extraction rules. |
| **UNSUPPORTED** | No trained recognition models configured, or scripts requiring specialized unintegrated fonts/tokenizers. | Blocked from automated field extraction; flagged immediately for human review. |

---

## 2. Language Matrix

| Language | Script | Model Configuration | Support Tier | Test Evidence | Mean Confidence Observed |
|---|---|---|---|---|---|
| **English** | Latin | `PP-OCRv6_medium_rec` (`lang='en'`) | **VERIFIED SUPPORT** | `test_ocr_integration_gate.py` (Tests A-H, J, K), `test_ocr_pipeline_units.py` | 0.95 - 0.99 |
| **Hindi** | Devanagari | `devanagari_PP-OCRv5_mobile_rec` (`lang='hi'`) | **VERIFIED SUPPORT** | `test_ocr_integration_gate.py` (Test I - pure Devanagari raster, Test K - mixed English + Devanagari) | 0.93 - 0.98 |
| **Mixed English + Devanagari** | Dual (Latin + Devanagari) | `devanagari_PP-OCRv5_mobile_rec` (`lang='hi'`) | **VERIFIED SUPPORT** | `test_ocr_integration_gate.py` (Test K - dual script preservation) | 0.96 - 0.99 |
| **Bengali** | Bengali / Assamese | Model `ch` / `bn` available in PaddleX | **EXPERIMENTAL** | Not integrated in automated test gate. | N/A |
| **Odia** | Odia | Model available in PaddleX | **EXPERIMENTAL** | Not integrated in automated test gate. | N/A |
| **Santhali (Ol Chiki)** | Ol Chiki | No pre-trained PaddleOCR mobile model | **UNSUPPORTED** | Requires custom OCR model training or fallback human transcription. | N/A |
| **Gondi** | Gondi / Devanagari | Devanagari variant experimental; native scripts unsupported | **UNSUPPORTED** | Flagged for manual scrutiny officer workflow. | N/A |
| **All Other Regional Scripts** | Various | Not loaded | **UNSUPPORTED** | Routed directly to `VerificationQueueItem` for manual verification. | N/A |

---

## 3. Test Evidence Summary

### 3.1 Pure Devanagari Script (`test_i`)
* **Fixture**: High-resolution raster image containing:
  ```text
  भारत सरकार
  आय प्रमाण पत्र
  वार्षिक पारिवारिक आय: 450000 रुपये
  प्रमाण पत्र संख्या: INC-2026-00124
  ```
* **Pipeline Executed**:
  `make_devanagari_raster_png -> DocumentIngestionService.upload_document -> OCRService.create_or_get_ocr_job -> OCRService.execute_ocr_pipeline(lang='hi') -> OCRResult -> OCRPage -> OCRBlock`
* **Verified Attributes**:
  - Full Unicode Devanagari characters (`\u0900` - `\u097F`) recognized.
  - Page level confidence > 0.90.
  - Distinct `OCRBlock` entities created with 4-point bounding boxes, width, height, and reading order.
  - Language metadata accurately preserved as `hi`.

### 3.2 Mixed English + Devanagari (`test_k`)
* **Fixture**: Bilingual certificate image containing:
  ```text
  Government of India
  आय प्रमाण पत्र
  Annual Family Income
  वार्षिक पारिवारिक आय
  ```
* **Verified Attributes**:
  - Both Latin (`A-Z`, `a-z`) and Devanagari (`\u0900` - `\u097F`) scripts recognized simultaneously.
  - Both scripts survive into persistent `OCRBlock` records.
  - Document remains in `SAFE` lifecycle status (proves OCR confidence != verification).
  - Application draft state unaffected (proves OCR output != eligibility decision).

---

## 4. Frozen Acceptance Contract Notice

The language support contract for the OCR Foundation is frozen as of:
**2026-09-30 02:00:00 UTC**  
Associated Test Files:
- `backend/tests/integration/test_ocr_integration_gate.py`
- `backend/tests/unit/test_ocr_pipeline_units.py`
