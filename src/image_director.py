import base64
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from jinja2 import Template
from PIL import Image

from src.config import settings, TEMPLATES_DIR, STATE_DIR, FONTS_DIR, ROOT_DIR

logger = logging.getLogger(__name__)


def _generate_font_faces_css() -> str:
    """Encodes bundled local TTF fonts as base64 data URIs for 100% deterministic offline rendering."""
    font_faces = []
    if FONTS_DIR.exists():
        for ttf_path in sorted(FONTS_DIR.glob("*.ttf")):
            name = ttf_path.stem
            # Parse weight and style (e.g. PlusJakartaSans-700-italic)
            weight = "400"
            style = "normal"
            if "700" in name:
                weight = "700"
            elif "800" in name:
                weight = "800"
            elif "600" in name:
                weight = "600"
            elif "900" in name:
                weight = "900"

            if "italic" in name.lower():
                style = "italic"

            b64_data = base64.b64encode(ttf_path.read_bytes()).decode("utf-8")
            font_faces.append(f"""
            @font-face {{
              font-family: 'Plus Jakarta Sans';
              font-weight: {weight};
              font-style: {style};
              font-display: block;
              src: url(data:font/truetype;charset=utf-8;base64,{b64_data}) format('truetype');
            }}""")
    return "\n".join(font_faces)


class ImageDirector:
    """
    Playwright-powered batch slide renderer and PDF compiler with cache-busting filenames.
    Renders into native Instagram 4:5 portrait resolution (1080x1350 px).
    """

    def __init__(self):
        self.temp_dir = STATE_DIR / "carousel_slides"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.cached_font_faces = _generate_font_faces_css()
        logo_path = ROOT_DIR / "assets" / "market_debunk_logo.png"
        if not logo_path.exists():
            logo_path = ROOT_DIR / "assets" / "market_debunk_logo.jpg"
        if logo_path.exists():
            b64_logo = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
            mime = "image/png" if logo_path.suffix.lower() == ".png" else "image/jpeg"
            self.logo_src = f"data:{mime};base64,{b64_logo}"
        else:
            self.logo_src = ""

    def render_carousel(self, deck: dict, run_id: Optional[str] = None) -> Dict[str, any]:
        """
        Renders the authoritative 8-slide deck to 1080x1350 retina PNGs with unique run_id filenames,
        and compiles them into a single multi-page PDF.
        """
        slides = deck.get("slides", [])
        if not slides:
            raise ValueError("Cannot render empty carousel slides.")

        expected_count = settings.EXPECTED_SLIDE_COUNT
        if len(slides) != expected_count:
            logger.warning("Deck slide count (%d) does not match expected (%d); normalizing...", len(slides), expected_count)
            slides = slides[:expected_count]

        run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        total_slides = len(slides)
        slide_png_paths = []
        pdf_path = str(STATE_DIR / f"market_debunk_carousel_{run_id}.pdf")
        latest_pdf_path = str(STATE_DIR / "latest_carousel.pdf")

        logger.info("🎨 Rendering %d carousel slides via Playwright (4:5 Portrait 1080x1350, Run ID: %s)...", total_slides, run_id)

        try:
            from playwright.sync_api import sync_playwright

            html_path = TEMPLATES_DIR / "carousel_slide.html"
            css_path = TEMPLATES_DIR / "carousel_slide.css"

            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()

            html_with_assets = html_content.replace("/* FONT_FACES */", self.cached_font_faces)
            html_with_assets = html_with_assets.replace("/* INLINE_STYLES */", css_content)
            template = Template(html_with_assets)

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
                page = browser.new_page(
                    viewport={"width": settings.SLIDE_WIDTH, "height": settings.SLIDE_HEIGHT},
                    device_scale_factor=1
                )

                for idx, slide in enumerate(slides):
                    png_name = f"slide_{idx+1}_{run_id}.png"
                    png_path = str(self.temp_dir / png_name)

                    context = {
                        "slide": slide,
                        "slide_index": idx + 1,
                        "total_slides": total_slides,
                        "brand_name": settings.BRAND_NAME,
                        "brand_subtitle": settings.BRAND_SUBTITLE,
                        "brand_handle": settings.BRAND_HANDLE,
                        "brand_url": settings.BRAND_URL,
                        "logo_src": self.logo_src,
                    }
                    rendered = template.render(**context)
                    page.set_content(rendered, wait_until="domcontentloaded")
                    page.evaluate("document.fonts.ready")

                    # Strict clipping to ensure exact 1080x1350 canvas without overflow expansion
                    page.screenshot(
                        path=png_path,
                        type="png",
                        clip={"x": 0, "y": 0, "width": settings.SLIDE_WIDTH, "height": settings.SLIDE_HEIGHT}
                    )
                    slide_png_paths.append(png_path)
                    logger.info("  ✓ Rendered slide %d/%d: %s", idx + 1, total_slides, png_name)

                browser.close()

        except Exception as e:
            logger.error("Playwright rendering failed: %s", e)
            raise e

        # Compile 300 DPI PDF via PIL
        try:
            pil_images = [Image.open(p).convert("RGB") for p in slide_png_paths]
            pil_images[0].save(
                pdf_path,
                "PDF",
                save_all=True,
                append_images=pil_images[1:],
                resolution=float(settings.PDF_DPI)
            )
            pil_images[0].save(
                latest_pdf_path,
                "PDF",
                save_all=True,
                append_images=pil_images[1:],
                resolution=float(settings.PDF_DPI)
            )
            logger.info("✅ Multi-page Carousel PDF compiled: %s (%d pages, %d KB)", latest_pdf_path, len(pil_images), os.path.getsize(latest_pdf_path) // 1024)
        except Exception as pdf_err:
            logger.error("Failed to compile PDF: %s", pdf_err)
            raise pdf_err

        return {
            "slide_paths": slide_png_paths,
            "pdf_path": latest_pdf_path,
            "run_id": run_id,
            "total_slides": total_slides
        }
