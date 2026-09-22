import os
import sys
from pathlib import Path
from PIL import Image

# Add project root to path
repo_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_path))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.validator import CarouselValidator
from src.image_director import ImageDirector

def test_offline_render():
    deck = {
        "caption": "Test caption with save and share cta",
        "slides": [
            {
                "role": "hook",
                "slide_index": 1,
                "tag": "#MARKETDEBUNK",
                "title_lines": ["Why Mutual", "Funds Hide", "<span class='highlight-box'>₹34 Lakhs</span>", "From You"]
            },
            {
                "role": "value_1",
                "slide_index": 2,
                "tag": "#MARKETDEBUNK",
                "title_lines": ["The Retail Myth", "<span class='highlight-box'>vs Actual Market</span>", "Reality"],
                "comparison_data": {
                    "myth": "Regular mutual funds offer superior alpha because distributor brokers monitor portfolio rebalancing.",
                    "reality": "Regular plans lag Direct plans by <strong>1.0% to 1.5% annually</strong> due to compounding trail commissions."
                }
            },
            {
                "role": "value_2",
                "slide_index": 3,
                "tag": "#MARKETDEBUNK",
                "title_lines": ["The True Cost", "<span class='highlight-box'>Of The Hidden 1%</span>", "Fee"],
                "stat_data": {
                    "badge": "VERIFIED COMPOUNDING LEAK",
                    "metric": "₹34 Lakhs",
                    "label": "capital lost over 20 years",
                    "context": "On a ₹25,000 monthly SIP compounding at 12% over 20 years, an extra 1% expense ratio silently transfers <strong>₹34.8 Lakhs</strong> into distributor commissions."
                }
            },
            {
                "role": "value_3",
                "slide_index": 4,
                "tag": "#MARKETDEBUNK",
                "title_lines": ["How Syndicates", "<span class='highlight-box'>Dump Liquidity</span>", "On Retail"],
                "flowchart_data": [
                    {"step": 1, "title": "Headline Spark", "text": "News releases trigger retail market orders."},
                    {"step": 2, "title": "Exit Fill", "text": "Smart capital dumps inventory into retail bids."},
                    {"step": 3, "title": "Drawdown Trap", "text": "Spread widens and retail is left holding losses."}
                ]
            },
            {
                "role": "value_4",
                "slide_index": 5,
                "tag": "#MARKETDEBUNK",
                "title_lines": ["Compounding Drag", "<span class='highlight-box'>Erodes Principal</span>", "Quietly"],
                "card_text": "Drawdowns hit compounding capital exponentially. Recovering from a 50% loss requires a <strong>100% gain</strong> just to break even."
            },
            {
                "role": "value_5",
                "slide_index": 6,
                "tag": "#MARKETDEBUNK",
                "title_lines": ["The Golden Rule:", "<span class='highlight-box'>Audit Before</span>", "Entering"],
                "card_text": "Never allocate more than <strong>2% total equity risk</strong> to any unconfirmed headline catalyst."
            },
            {
                "role": "value_6",
                "slide_index": 7,
                "tag": "#MARKETDEBUNK",
                "title_lines": ["The 3-Point", "<span class='highlight-box'>Pre-Trade Risk</span>", "Audit"],
                "checklist_data": [
                    {"status": "fail", "text": "Entering blindly on breaking news headlines without delivery volume."},
                    {"status": "pass", "text": "Verifying institutional open interest and dark pool block trades."},
                    {"status": "pass", "text": "Hard-coding exit stop-loss in terminal prior to order dispatch."}
                ]
            },
            {
                "role": "bookmark_save",
                "slide_index": 8,
                "tag": "#MARKETDEBUNK",
                "title_lines": ["Don’t", "forget to", "<span class='highlight-box'>save & share</span>", "this for", "later"],
                "cta_detail": "Bookmark this checklist to audit your next trade. Share it with an investor friend before they risk capital."
            }
        ]
    }

    # 1. Validation test
    print("[TEST 1] Validating polymorphic deck with CarouselValidator...")
    validator = CarouselValidator()
    is_valid, report = validator.validate_content(deck)
    print(f"Validation result: valid={is_valid}, report={report}")
    assert is_valid, f"Validation failed with report: {report}"
    print("✓ CarouselValidator PASSED!")

    # 2. Offline Render test
    print("\n[TEST 2] Rendering polymorphic deck via ImageDirector (Playwright)...")
    director = ImageDirector()
    result = director.render_carousel(deck, run_id="test_archetypes")

    png_paths = result.get("slide_png_paths", [])
    pdf_path = result.get("pdf_path")

    print(f"Rendered {len(png_paths)} slides. PDF path: {pdf_path}")
    assert len(png_paths) == 8, f"Expected 8 slide PNGs, got {len(png_paths)}"

    for idx, p in enumerate(png_paths):
        assert os.path.exists(p), f"Slide {idx+1} PNG does not exist at {p}"
        with Image.open(p) as img:
            assert img.size == (1080, 1350), f"Slide {idx+1} dimensions {img.size} != (1080, 1350)"
        print(f"  ✓ Slide {idx+1} confirmed: 1080x1350 px ({os.path.basename(p)})")

    assert pdf_path and os.path.exists(pdf_path), f"PDF does not exist at {pdf_path}"
    pdf_size = os.path.getsize(pdf_path)
    assert pdf_size > 10000, f"PDF file size too small: {pdf_size} bytes"
    print(f"  ✓ Multi-page PDF confirmed: {pdf_size} bytes ({os.path.basename(pdf_path)})")

    print("\n✅ ALL OFFLINE RENDERING UNIT TESTS PASSED!")

if __name__ == "__main__":
    test_offline_render()
