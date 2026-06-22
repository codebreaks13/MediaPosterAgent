# ─────────────────────────────────────────────────────────────────
# CELL 1 – Imports and environment loading
# ─────────────────────────────────────────────────────────────────

import os, re, json, time, textwrap, io
from pathlib import Path
from datetime import datetime

import feedparser
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()
AI_API_KEY  = os.getenv("AI_API_KEY",  "")
AI_MODEL    = os.getenv("AI_MODEL",    "llama-3.3-70b-versatile")
IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "mock")
MIN_VIRAL_SCORE = int(os.getenv("MIN_VIRAL_SCORE", "5"))
MAX_ARTICLES    = int(os.getenv("MAX_ARTICLES_PER_RUN", "20"))

if not AI_API_KEY:
    raise EnvironmentError(
        "AI_API_KEY is not set. "
        "Create a .env file with AI_API_KEY=<your key> and re-run this cell."
    )

print(f"✅  Provider : {AI_PROVIDER}")
print(f"✅  Model    : {AI_MODEL}")
print(f"✅  Image    : {IMAGE_BACKEND}")
print("✅  API key  : ***hidden***")