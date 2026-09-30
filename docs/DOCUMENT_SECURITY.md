# Document Security & Content Validation

## 1. Zero-Trust Content Security

The Tribel_Scholor document ingestion boundary does not trust client-declared filenames or HTTP `Content-Type` headers. Every uploaded artifact is subjected to multi-tiered byte-level inspection.

```text
Incoming Stream
  ├── [1] Byte Count Check (max size ceiling)
  ├── [2] Magic-Byte Sniffing (true MIME identification)
  ├── [3] Header vs Body Consistency Check (MIME mismatch detection)
  ├── [4] Deep Format Parse (PDF structural parser / PIL Image rasterizer)
  └── [5] Antivirus / Malware Scanner Interface
```

---

## 2. File Type Allowlist & Dangerous Type Rejection

### Allowed Formats
- `application/pdf` (`.pdf`)
- `image/jpeg` (`.jpg`, `.jpeg`)
- `image/png` (`.png`)

### Blocked Dangerous Binaries & Scripts
The preliminary magic byte detector instantly halts and rejects:
- Windows Executables / Dynamic Link Libraries (`PE32`, `MZ` headers)
- Linux Executables (`\x7fELF`)
- macOS Binaries (`Mach-O` headers)
- Zip & Compressed Archives (`PK\x03\x04`, `7z`, `Rar!`)
- Scripting & Markup Formats (`<html`, `<?xml`, `<svg`, `javascript:`, `eval(`)

---

## 3. MIME Mismatch & Extension Spoofing Detection

If a user declares a `.pdf` file with `Content-Type: application/pdf` but provides an executable binary or an image disguised as a PDF:
- Server sniffs actual content bytes via `FileContentDetector.detect_mime()`.
- If declared MIME and detected MIME do not match:
  - Immediate `ValidationError` (`CONTENT_TYPE_MISMATCH`).
  - Document status transitions to `REJECTED`.
  - Quarantined file is deleted.
  - Reason recorded: `"CONTENT_TYPE_MISMATCH: Declared as application/pdf but detected as application/x-dosexec"`.

---

## 4. Deep PDF Structural Validation

Before promoting any PDF to `SAFE`, `DocumentSecurityValidator.validate_pdf()` verifies:
1. **Magic Header**: Must start with `%PDF-` within the first 1024 bytes.
2. **EOF Marker**: Must contain `%%EOF` within the final 2048 bytes (detects malformed/truncated payloads).
3. **Executable / Script Attachment Blocking**: Scans dictionary tokens for:
   - `/JavaScript` and `/JS` (PDF embedded scripts)
   - `/Launch` (OS command execution triggers)
   - `/EmbeddedFiles` (hidden binaries inside PDF containers)
4. **Encryption Rejection**: Detects `/Encrypt` dictionary tags. Encrypted or password-protected PDFs are rejected because automated verification pipelines cannot safely evaluate them.

---

## 5. Image Security & EXIF Sanitization

JPEG and PNG files undergo deep raster decoding via Pillow (`PIL.Image`):
1. **Raster Verification**: Verifies valid raster headers and stream readability via `Image.open(io.BytesIO(content)).verify()`.
2. **Decompression Bomb Protection**:
   - Rejects images where width or height exceeds `10,000` pixels.
   - Rejects total pixel volume exceeding `25,000,000` pixels (25 Megapixels).
   - Rejects zero or negative dimensions.
3. **Metadata / GPS Sanitization**:
   - When images are saved or normalized, EXIF metadata containing GPS geolocation coordinates and camera serial numbers is stripped to protect applicant privacy.

---

## 6. Implementation Status Matrix

| Security Feature | Status | Details |
| :--- | :--- | :--- |
| Magic-Byte Content Sniffing | **IMPLEMENTED** | `FileContentDetector` analyzes byte signatures independent of extensions |
| PDF Structure & EOF Validation | **IMPLEMENTED** | Enforces `%PDF-` header, `%%EOF` trailer, blocks truncated streams |
| PDF JavaScript & Launch Action Blocking | **IMPLEMENTED** | Scans and rejects `/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFiles` |
| PDF Password/Encryption Blocking | **IMPLEMENTED** | Rejects `/Encrypt` protected PDFs |
| Image Raster & Bomb Rejection | **IMPLEMENTED** | Pillow validation rejecting corrupted images, $>10k$ px, $>25$ MP bombs |
| EXIF GPS Stripping | **IMPLEMENTED** | Normalizes images without retaining GPS coordinates |
| Sandboxed PDF Visual Rendering | **FUTURE** | Rendering PDF pages to canvas in isolated worker containers (Phase 7) |
