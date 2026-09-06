"""
Market Debunk - Comprehensive Carousel and PDF Quality Gate Validator
Enforces strict 1080x1350 resolution, aspect ratio, page count, and edge integrity.
"""
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from PIL import Image

from src.config import settings

logger = logging.getLogger("CarouselValidator")


class CarouselValidator:
    @staticmethod
    def validate_content(deck: dict, expected_count: Optional[int] = None) -> Tuple[bool, str]:
        expected = expected_count or settings.EXPECTED_SLIDE_COUNT
        slides = deck.get("slides", [])
        if len(slides) != expected:
            return False, f"Content error: Expected {expected} slides, got {len(slides)}."

        # Check Slide 1 (Hook)
        s1 = slides[0]
        if s1.get("role") != "hook" or not s1.get("title_lines"):
            return False, "Slide 1 content error: Must be hook with non-empty title_lines."

        # Check Value Slides (2 to expected-1)
        for i in range(1, expected - 1):
            s = slides[i]
            if not s.get("title_lines"):
                return False, f"Slide {i+1} content error: Missing title_lines."
            if not s.get("card_text"):
                return False, f"Slide {i+1} content error: Missing green card_text."

        # Check Final Slide (CTA)
        last_s = slides[-1]
        if not last_s.get("title_lines"):
            return False, f"Slide {expected} content error: Missing CTA title_lines."

        return True, f"CONTENT VALIDATION PASSED: All {expected} slides conform to strict schema."

    @staticmethod
    def validate_slide_png(
        png_path: str,
        expected_width: Optional[int] = None,
        expected_height: Optional[int] = None
    ) -> Tuple[bool, str]:
        p = Path(png_path)
        if not p.exists():
            return False, f"Render error: File does not exist: {png_path}"

        size_bytes = p.stat().st_size
        if size_bytes < 5000:
            return False, f"Render error: File {p.name} is too small ({size_bytes} bytes), possible blank frame."

        w = expected_width or settings.SLIDE_WIDTH
        h = expected_height or settings.SLIDE_HEIGHT

        try:
            with Image.open(p) as img:
                if img.size != (w, h):
                    return False, f"Dimensional error: {p.name} is {img.size[0]}x{img.size[1]}, expected {w}x{h}."

                # Inspect edge pixels to guarantee full-bleed canvas (no letterbox/margins)
                rgb_img = img.convert("RGB")
                corners = [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]
                for cx, cy in corners:
                    r, g, b = rgb_img.getpixel((cx, cy))
                    # Background is #f8f8f9 (r~248, g~248, b~249)
                    if r < 140 and g < 140 and b < 140:
                        return False, f"Edge border artifact detected at corner ({cx}, {cy}) in {p.name}: RGB({r},{g},{b})"

        except Exception as e:
            return False, f"Failed to inspect image {p.name}: {e}"

        return True, f"{p.name} passed exact {w}x{h} dimension and edge-pixel validation."

    @staticmethod
    def validate_pdf(pdf_path: str, expected_page_count: Optional[int] = None) -> Tuple[bool, str]:
        p = Path(pdf_path)
        if not p.exists():
            return False, f"PDF error: File does not exist: {pdf_path}"

        if p.stat().st_size < 20000:
            return False, f"PDF error: File {p.name} is unusually small ({p.stat().st_size} bytes)."

        expected = expected_page_count or settings.EXPECTED_SLIDE_COUNT

        try:
            with open(p, "rb") as f:
                raw_bytes = f.read()

            count_match = re.search(rb'/Count\s+(\d+)', raw_bytes)
            if count_match:
                pages = int(count_match.group(1))
            else:
                pages = len(re.findall(rb'/Type\s*/Page\b', raw_bytes))

            if pages != expected:
                return False, f"PDF page count mismatch: Expected {expected} pages, found {pages}."

        except Exception as e:
            return False, f"PDF inspection failed: {e}"

        return True, f"PDF VALIDATION PASSED: {p.name} contains exactly {expected} valid pages."