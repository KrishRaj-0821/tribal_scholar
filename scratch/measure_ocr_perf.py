import os
import sys
import time
import django

# Setup Django environment
sys.path.insert(0, os.path.abspath("backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tribel_scholar.settings")
django.setup()

from PIL import Image, ImageDraw, ImageFont
import io
from apps.documents.ocr_engines import get_ocr_engine

def make_sample_image(text_lines):
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font_path = "C:/Windows/Fonts/Nirmala.ttc"
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, 24)
    else:
        font = ImageFont.load_default()
    
    y = 50
    for line in text_lines:
        draw.text((50, y), line, fill=(0, 0, 0), font=font)
        y += 40
    return img

print("=== STARTING OCR BENCHMARK ===")
engine = get_ocr_engine(backend='paddleocr', lang='en')

# 1. First Inference (Cold Start: includes model weights loading & warm-up)
img_p1 = make_sample_image([
    "Government of India",
    "Income Certificate",
    "Annual Family Income: 450000",
    "Certificate No: INC-2026-9901"
])

t0 = time.perf_counter()
blocks_cold = engine.process_image(img_p1, page_num=1)
t_cold = time.perf_counter() - t0
print(f"1. First Inference (Cold Start): {t_cold:.3f} s (blocks: {len(blocks_cold)})")

# 2. Subsequent Inference (Warm / In-Memory Inference)
img_p2 = make_sample_image([
    "State Government Department of Social Welfare",
    "Scheduled Tribe Caste Certificate",
    "Applicant: Arjun Munda",
    "Verification Code: VERIF-ST-8821"
])
t0 = time.perf_counter()
blocks_warm = engine.process_image(img_p2, page_num=1)
t_warm = time.perf_counter() - t0
print(f"2. Subsequent Inference (Warm Single-Page): {t_warm:.3f} s (blocks: {len(blocks_warm)})")

# 3. Three-Page Document OCR Measurement
img_p3 = make_sample_image([
    "Academic Marksheet 2025-2026",
    "Board of Intermediate Education",
    "Total Marks: 472 / 500",
    "Result: Pass with Distinction"
])

t0 = time.perf_counter()
b1 = engine.process_image(img_p1, page_num=1)
b2 = engine.process_image(img_p2, page_num=2)
b3 = engine.process_image(img_p3, page_num=3)
t_3page = time.perf_counter() - t0
print(f"3. Three-Page OCR (Cumulative Warm): {t_3page:.3f} s ({t_3page/3:.3f} s/page avg)")

# 4. Devanagari OCR Measurement (Warm)
hi_engine = get_ocr_engine(backend='paddleocr', lang='hi')
img_hi = make_sample_image([
    "भारत सरकार",
    "आय प्रमाण पत्र",
    "वार्षिक पारिवारिक आय: 450000 रुपये",
    "प्रमाण पत्र संख्या: INC-2026-00124"
])
t0 = time.perf_counter()
blocks_hi = hi_engine.process_image(img_hi, page_num=1)
t_hi = time.perf_counter() - t0
print(f"4. Devanagari Single-Page (Warm): {t_hi:.3f} s (blocks: {len(blocks_hi)})")

print("=== BENCHMARK COMPLETED ===")
