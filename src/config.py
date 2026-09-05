import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT_DIR / "src" / "templates"
DATA_DIR = ROOT_DIR / "data"
STATE_DIR = ROOT_DIR / "state"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

class Settings:
    # ── AI Keys ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    # ── News / Market Sourcing ──────────────────────────────────────────────
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "b8906f93f638b596fb6ef15e4086e0eebcfc3372a0d293b2977224b92a7d4ecf")

    # ── Meta (Instagram & Facebook) ─────────────────────────────────────────
    INSTAGRAM_USER_ID: str = os.getenv("INSTAGRAM_USER_ID", "17841476402324907")
    INSTAGRAM_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_GRAPH_VERSION: str = os.getenv("INSTAGRAM_GRAPH_VERSION", "v21.0")

    FACEBOOK_PAGE_ID: str = os.getenv("FACEBOOK_PAGE_ID", "106828592534579")
    FACEBOOK_ACCESS_TOKEN: str = os.getenv("FACEBOOK_ACCESS_TOKEN", "")

    # ── Telegram ────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── LinkedIn ────────────────────────────────────────────────────────────
    LINKEDIN_ACCESS_TOKEN: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    LINKEDIN_ORGANIZATION_URN: str = os.getenv("LINKEDIN_ORGANIZATION_URN", "")

    # ── Feature Flags ───────────────────────────────────────────────────────
    ENABLE_INSTAGRAM: bool = os.getenv("ENABLE_INSTAGRAM", "true").lower() == "true"
    ENABLE_FACEBOOK: bool = os.getenv("ENABLE_FACEBOOK", "true").lower() == "true"
    ENABLE_TELEGRAM: bool = os.getenv("ENABLE_TELEGRAM", "true").lower() == "true"
    ENABLE_LINKEDIN: bool = os.getenv("ENABLE_LINKEDIN", "false").lower() == "true"

    # ── Branding ────────────────────────────────────────────────────────────
    BRAND_NAME: str = "Market Debunk"
    BRAND_SUBTITLE: str = "Exposing Retail Traps & Institutional Math"
    BRAND_HANDLE: str = "@marketdebunk"

settings = Settings()
