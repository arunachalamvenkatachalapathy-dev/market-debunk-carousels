import base64
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from jinja2 import Template
from PIL import Image

from src.config import settings, TEMPLATES_DIR, STATE_DIR

logger = logging.getLogger(__name__)

ASPECT_1X1 = {"width": 1080, "height": 1080}


class ImageDirector:
    """
    Playwright-powered batch slide renderer and PDF compiler with cache-busting filenames.
    """

    def __init__(self):
        self.temp_dir = STATE_DIR / "carousel_slides"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def render_carousel(self, deck: dict, run_id: Optional[str] = None) -> Dict[str, any]:
        """
        Renders the 6-slide deck to 1080x1080 retina PNGs with unique run_id filenames,
        and compiles them into a single multi-page PDF.
        """
        slides = deck.get("slides", [])
        if not slides:
            raise ValueError("Cannot render empty carousel slides.")

        run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        total_slides = len(slides)
        slide_png_paths = []
        pdf_path = str(STATE_DIR / f"market_debunk_carousel_{run_id}.pdf")
        latest_pdf_path = str(STATE_DIR / "latest_carousel.pdf")

        logger.info("🎨 Rendering %d carousel slides via Playwright (Run ID: %s)...", total_slides, run_id)

        try:
            from playwright.sync_api import sync_playwright

            html_path = TEMPLATES_DIR / "carousel_slide.html"
            css_path = TEMPLATES_DIR / "carousel_slide.css"

            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

            html_with_css = html_content.replace("/* INLINE_STYLES */", css_content)
            template = Template(html_with_css)

            # Load brand logo as base64
            logo_path = next(
                (p for p in (TEMPLATES_DIR / "logo.png", TEMPLATES_DIR / "logo_transparent.png") if p.exists()),
                None
            )
            profile_image_src = ""
            if logo_path:
                with open(logo_path, "rb") as img_f:
                    profile_image_src = "data:image/png;base64," + base64.b64encode(img_f.read()).decode("utf-8")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": ASPECT_1X1["width"], "height": ASPECT_1X1["height"]},
                    device_scale_factor=2
                )

                for idx, slide in enumerate(slides):
                    # Cache-busting unique filename
                    png_name = f"slide_{idx+1}_{run_id}.png"
                    png_path = str(self.temp_dir / png_name)

                    context = {
                        "slide": slide,
                        "slide_index": idx + 1,
                        "total_slides": total_slides,
                        "brand_name": settings.BRAND_NAME,
                        "brand_subtitle": settings.BRAND_SUBTITLE,
                        "brand_handle": settings.BRAND_HANDLE,
                        "profile_image_src": profile_image_src,
                    }
                    rendered = template.render(**context)
                    page.set_content(rendered, wait_until="domcontentloaded")
                    page.screenshot(path=png_path, type="png")
                    slide_png_paths.append(png_path)
                    logger.info("  ✓ Rendered slide %d/%d: %s", idx + 1, total_slides, png_name)

                browser.close()

        except Exception as e:
            logger.error("Playwright rendering failed: %s", e)
            raise e

        # Compile PDF via PIL
        try:
            pil_images = [Image.open(p).convert("RGB") for p in slide_png_paths]
            pil_images[0].save(pdf_path, "PDF", save_all=True, append_images=pil_images[1:])
            # Also save latest_carousel.pdf for easy inspection
            pil_images[0].save(latest_pdf_path, "PDF", save_all=True, append_images=pil_images[1:])
            logger.info("✅ Multi-page Carousel PDF compiled: %s (%d pages, %d KB)", latest_pdf_path, len(pil_images), os.path.getsize(latest_pdf_path) // 1024)
        except Exception as pdf_err:
            logger.error("Failed to compile PDF: %s", pdf_err)

        return {
            "slide_paths": slide_png_paths,
            "pdf_path": latest_pdf_path,
            "run_id": run_id,
            "total_slides": total_slides
        }
