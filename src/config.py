import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT_DIR / "src" / "templates"
DATA_DIR = ROOT_DIR / "data"
STATE_DIR = ROOT_DIR / "state"
ASSETS_DIR = ROOT_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)
FONTS_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    # ── Authoritative Carousel Contract ─────────────────────────────────────
    EXPECTED_SLIDE_COUNT: int = 8
    SLIDE_WIDTH: int = 1080
    SLIDE_HEIGHT: int = 1350
    PDF_DPI: int = 300

    # ── Design Tokens ───────────────────────────────────────────────────────
    BG_COLOR: str = "#f8f8f9"
    BRAND_NAVY: str = "#111111"
    BRAND_GREEN: str = "#16a34a"
    CARD_GREEN: str = "#15803d"
    TEXT_WHITE: str = "#ffffff"
    TEXT_MUTED: str = "#333333"

    # ── AI Keys ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GEMMA_FALLBACK_MODEL: str = os.getenv("GEMMA_FALLBACK_MODEL", "gemma-4-31b-it")

    # ── News / Market Sourcing ──────────────────────────────────────────────
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    MARKETAUX_API_TOKEN: str = os.getenv("MARKETAUX_API_TOKEN", "bZ1PVR803PweIGinKuMa1r6Zk4kPn4v8xikQvUkC")
    INDIAN_API_KEY: str = os.getenv("INDIAN_API_KEY", "sk-live-Ca1EJj4XFo61nRpchb93tlGrs0IyVEC5cl4A6iF5")

    # ── Meta (Instagram & Facebook) ─────────────────────────────────────────
    INSTAGRAM_USER_ID: str = os.getenv("INSTAGRAM_USER_ID", "17841476402324907")
    INSTAGRAM_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_GRAPH_VERSION: str = os.getenv("INSTAGRAM_GRAPH_VERSION", "v21.0")

    FACEBOOK_PAGE_ID: str = os.getenv("FACEBOOK_PAGE_ID", "106828592534579")
    FACEBOOK_ACCESS_TOKEN: str = os.getenv("FACEBOOK_ACCESS_TOKEN", "")

    # ── Telegram ────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── LinkedIn (English Channel Only) ─────────────────────────────────────
    LINKEDIN_ACCESS_TOKEN: str = os.getenv(
        "LINKEDIN_ACCESS_TOKEN",
        "AQXymIB5XIOlwPKRw8jCvXQIK4pstiF6EN_9pA8zhB8hjYLVAztqAuxYj7my_oXMuhRorCgi_vftJpcqiTtVVjWLP_lolqCPaY5ry1G78IZ3zu2x7sgU7eYuTxTbcCvsX99hYX9V0UnkfYHgLY_r_DJt1SbqlZoc4R7mP5JMM5CSxZHK5zB2ltX1EpiYRgOi3JsjhvDMHiNgtKVqTiXyJf9KZkah1Rm-zwX_k37mcGISv5ZO44Hn1rSnpkLfGIPjboulukqyN2w64-aq-kIhA2Po4kK9UpgSrfILUhAbIsuoYaqAz0wkfJb6aDonZ6NINANTawAJob19n42swMZFd1Rj8yrizw"
    )
    LINKEDIN_AUTHOR_URN: str = os.getenv(
        "LINKEDIN_AUTHOR_URN",
        os.getenv("LINKEDIN_ORGANIZATION_URN", "urn:li:organization:143659978")
    )
    LINKEDIN_ORGANIZATION_URN: str = LINKEDIN_AUTHOR_URN

    # ── Feature Flags ───────────────────────────────────────────────────────
    ENABLE_INSTAGRAM: bool = os.getenv("ENABLE_INSTAGRAM", "true").lower() == "true"
    ENABLE_FACEBOOK: bool = os.getenv("ENABLE_FACEBOOK", "true").lower() == "true"
    ENABLE_TELEGRAM: bool = os.getenv("ENABLE_TELEGRAM", "true").lower() == "true"
    ENABLE_LINKEDIN: bool = os.getenv("ENABLE_LINKEDIN", "true").lower() == "true"

    # ── Branding ────────────────────────────────────────────────────────────
    BRAND_NAME: str = "Market Debunk"
    BRAND_SUBTITLE: str = "Exposing Retail Traps & Institutional Math"
    BRAND_HANDLE: str = "@Market_Debunk"
    BRAND_URL: str = "www.marketdebunk.com"

settings = Settings()
