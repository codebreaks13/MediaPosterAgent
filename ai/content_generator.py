"""
ai/content_generator.py
------------------------
For each top article, generates the full social-media content block:
  • headline / summary
  • Facebook caption
  • Instagram caption
  • Twitter/X caption
  • Hashtags
  • Poster text (short, image-ready)
  • SEO metadata (keywords, meta description, tags)

Evolved from Cell 6; now outputs a richer, structured content object.
"""

import re
import json
import time
from config.logging_setup import get_logger
from ai.client import ask_ai

log = get_logger(__name__)

_SYSTEM = (
    "You are an award-winning news social-media editor. "
    "You write punchy, platform-optimised content that drives engagement. "
    "You respond only with valid JSON."
)

_BANGLA_SYSTEM = (
    "You are a Bangla translator. Translate the given text accurately into Bangla. "
    "Return only the translated text, nothing else."
)


def _translate_to_bangla(text: str) -> str:
    """Translate a short English text to Bangla using the AI."""
    if not text:
        return text
    try:
        return ask_ai(
            f"Translate this to Bangla:\n{text}",
            system=_BANGLA_SYSTEM,
            model="llama-3.1-8b-instant",
        ).strip()
    except Exception as exc:
        log.warning("Bangla translation failed: %s", exc)
        return text


def _build_content_prompt(article: dict) -> str:
    entities = article.get("entities", {})
    teams    = ", ".join(entities.get("teams",    [])) or "N/A"
    players  = ", ".join(entities.get("players",  [])) or "N/A"
    countries= ", ".join(entities.get("countries",[])) or "N/A"

    return f"""Write a complete social-media content block for this news story.

Story details:
  Title     : {article['title']}
  Source    : {article['source']}
  Summary   : {article.get('summary', 'N/A')[:250]}
  Category  : {article.get('category', 'other')}
  Viral hook: {article.get('why', 'N/A')}
  Entities  : {teams or players or countries or 'N/A'}

Return ONLY a JSON object with EXACTLY these keys:
  "headline"          : punchy headline, max 12 words
  "summary"           : 2-3 sentences, factual and engaging
  "facebook_caption"  : professional Facebook post, 2-3 paragraphs
  "instagram_caption" : punchy IG caption with line breaks, emoji-friendly
  "twitter_caption"   : max 240 chars, hook + call to action
  "hashtags"          : array of 8-12 relevant hashtags (no # symbol)
  "poster_text"       : ultra-short headline for image overlay, max 7 words
  "seo_keywords"      : array of 5-8 SEO keyword phrases
  "meta_description"  : 150-char SEO meta description
  "tags"              : array of 4-6 content tags

No markdown. No extra text. Valid JSON only."""


def generate_content(article: dict) -> dict:
    """
    Generate social-media content for a single article.

    Returns the article dict enriched with content fields,
    or falls back to the original title/summary on failure.
    """
    try:
        prompt   = _build_content_prompt(article)
        response = ask_ai(prompt, system=_SYSTEM, model="llama-3.1-8b-instant")
        clean    = re.sub(r"```(?:json)?|```", "", response).strip().strip("`")
        data     = json.loads(clean)

        article["headline"]          = data.get("headline",         article["title"])
        article["ai_summary"]        = data.get("summary",          article.get("summary", ""))
        article["facebook_caption"]  = data.get("facebook_caption", "")
        article["instagram_caption"] = data.get("instagram_caption","")
        article["twitter_caption"]   = data.get("twitter_caption",  "")
        article["hashtags"]          = data.get("hashtags",         [])
        article["poster_text"]       = data.get("poster_text",      article["title"][:40])
        article["seo_keywords"]      = data.get("seo_keywords",     [])
        article["meta_description"]  = data.get("meta_description", "")
        article["tags"]              = data.get("tags",             [])

        # Translate poster fields to Bangla
        article["poster_text"] = _translate_to_bangla(article["poster_text"])
        article["ai_summary"]  = _translate_to_bangla(article["ai_summary"])

    except Exception as exc:
        log.warning("Content generation failed for '%s': %s", article.get("title", "<unknown>")[:50], exc)  ##comment: using article["title"] here could raise KeyError if 'title' missing; use .get() to be safe
        # Graceful fallback
        article.setdefault("headline",          article["title"])
        article.setdefault("ai_summary",        article.get("summary", ""))
        article.setdefault("facebook_caption",  "")
        article.setdefault("instagram_caption", "")
        article.setdefault("twitter_caption",   "")
        article.setdefault("hashtags",          [])
        article.setdefault("poster_text",       article["title"][:40])
        article.setdefault("seo_keywords",      [])
        article.setdefault("meta_description",  "")
        article.setdefault("tags",              [])

    return article


def generate_content_batch(articles: list[dict], delay: float = 0.5) -> list[dict]:
    """Generate content for a list of articles, one at a time."""
    enriched = []
    for i, art in enumerate(articles, start=1):
        log.info("Content %d/%d: %s", i, len(articles), art["title"][:55])
        enriched.append(generate_content(art))
        if i < len(articles):
            time.sleep(delay)
    log.info("Content generation complete for %d articles", len(enriched))
    return enriched