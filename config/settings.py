"""
config/settings.py
------------------
Single source of truth for all configuration.
Reads from .env (or real environment) and exposes typed constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def _get(key: str, default=None, cast=str):
    val = os.environ.get(key, default)
    if val is None:
        return val
    try:
        return cast(val)
    except (ValueError, TypeError):
        return default


# ── AI provider ───────────────────────────────────────────────────────────────
AI_PROVIDER: str = _get("AI_PROVIDER", "groq").lower()
AI_API_KEY:  str = _get("AI_API_KEY",  "")
AI_MODEL:    str = _get("AI_MODEL",    "llama-3.3-70b-versatile")

# ── Image generation ──────────────────────────────────────────────────────────
IMAGE_BACKEND:      str = _get("IMAGE_BACKEND",      "mock")   # stability|replicate|gemini|mock
STABILITY_API_KEY:  str = _get("STABILITY_API_KEY",  "")
REPLICATE_API_KEY:  str = _get("REPLICATE_API_KEY",  "")
GEMINI_API_KEY:     str = _get("GEMINI_API_KEY",     "")

# ── Pipeline tuning ───────────────────────────────────────────────────────────
MAX_ARTICLES_PER_RUN:      int = _get("MAX_ARTICLES_PER_RUN",      20,  int)
MIN_VIRAL_SCORE:           int = _get("MIN_VIRAL_SCORE",           5,   int)
SCHEDULE_INTERVAL_MINUTES: int = _get("SCHEDULE_INTERVAL_MINUTES", 60,  int)
REQUEST_TIMEOUT:           int = _get("REQUEST_TIMEOUT_SECONDS",   15,  int)
MAX_RETRIES:               int = _get("MAX_RETRIES",               3,   int)
RETRY_DELAY:               int = _get("RETRY_DELAY_SECONDS",       5,   int)

# ── Storage paths (auto-created) ──────────────────────────────────────────────
NEWS_DIR    = _ROOT / "news"
POSTERS_DIR = _ROOT / "posters"
EXPORTS_DIR = _ROOT / "exports"
LOGS_DIR    = _ROOT / "logs"

for _d in (NEWS_DIR, POSTERS_DIR, EXPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)