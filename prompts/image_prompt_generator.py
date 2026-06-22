"""
prompts/image_prompt_generator.py
----------------------------------
Automatically generates high-quality image-generation prompts
for each article — tailored for Stable Diffusion XL, Flux, or Gemini.

Prompts follow professional sports editorial photography conventions:
dynamic stadium lighting, action atmosphere, national flags, team colors.
"""

import re
import json
from config.logging_setup import get_logger
from ai.client import ask_ai

log = get_logger(__name__)

_SYSTEM = (
    "You are a world-class sports visual director creating prompts for "
    "AI image generation (Stable Diffusion XL / Flux). "
    "Respond only with valid JSON."
)

# Base style suffix appended to every prompt
_STYLE_SUFFIX = (
    "professional sports editorial photography, FIFA World Cup 2027 branding, "
    "dynamic stadium lighting, packed crowd atmosphere, 8K ultra-detailed, "
    "sharp focus, photorealistic, high contrast, vibrant colors, "
    "cinematic composition, golden hour lighting"
)

_NEGATIVE_PROMPT = (
    "text, watermark, logo, caption, blurry, low quality, deformed, "
    "ugly, duplicate, morbid, mutilated, out of frame, extra fingers, "
    "poorly drawn hands, poorly drawn face, mutation, bad anatomy, "
    "bad proportions, cloned face, disfigured, cross-eyed, collage"
)


def _build_prompt_request(article: dict) -> str:
    entities = article.get("entities", {})
    teams    = ", ".join(entities.get("teams",    [])) or "N/A"
    players  = ", ".join(entities.get("players",  [])) or "N/A"
    countries= ", ".join(entities.get("countries",[])) or "N/A"

    return f"""Create an image generation prompt for a FIFA 2027 news poster.

Story:
  Headline  : {article.get('headline', article['title'])}
  Category  : {article.get('category', 'other')}
  Teams     : {teams}
  Players   : {players}
  Countries : {countries}
  Why viral : {article.get('why', 'N/A')}

Return ONLY a JSON object with EXACTLY these keys:
  "main_prompt"     : detailed positive image prompt (100-150 words)
                      Include: scene, atmosphere, composition, lighting,
                      national flags when relevant, team colors, action
  "negative_prompt" : what to avoid (copy standard negatives + anything
                      story-specific that would look wrong)
  "style_notes"     : 1-2 sentences on the specific visual style

Rules:
- NO text or typography in the main_prompt (image gen renders text badly)
- NO watermarks or logos
- Favor action shots over static poses
- FIFA 2027 branding color: deep blue + gold
- Make it look BREAKING NEWS and HIGH ENERGY

No markdown. Valid JSON only."""


def generate_image_prompt(article: dict) -> dict:
    """
    Generate an image prompt for one article.

    Adds keys to the article dict:
        image_prompt    – positive prompt string
        negative_prompt – negative prompt string
        style_notes     – style guidance
    """
    try:
        response = ask_ai(_build_prompt_request(article), system=_SYSTEM, model="llama-3.1-8b-instant")
        clean    = re.sub(r"```(?:json)?|```", "", response).strip().strip("`")
        data     = json.loads(clean)

        article["image_prompt"]    = (
            data.get("main_prompt", "") + ", " + _STYLE_SUFFIX
        )
        article["negative_prompt"] = data.get("negative_prompt", _NEGATIVE_PROMPT)
        article["style_notes"]     = data.get("style_notes",     "")

    except Exception as exc:
        log.warning("Image prompt generation failed for '%s': %s",
                    article["title"][:50], exc)
        # Sensible fallback prompt
        article["image_prompt"]    = (
            f"FIFA World Cup 2027 football match scene, "
            f"{article.get('category','sport')} moment, "
            + _STYLE_SUFFIX
        )
        article["negative_prompt"] = _NEGATIVE_PROMPT
        article["style_notes"]     = ""

    return article


def generate_image_prompts_batch(articles: list[dict]) -> list[dict]:
    """Generate image prompts for all articles."""
    for i, art in enumerate(articles, start=1):
        log.info("Image prompt %d/%d: %s", i, len(articles), art["title"][:55])
        generate_image_prompt(art)
    return articles