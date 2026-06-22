"""
ranking/scorer.py
-----------------
Scores every article on four dimensions:

  • relevance_score  (0-100) – how relevant to FIFA 2027
  • viral_score      (0-100) – social engagement potential
  • breaking_score   (0-100) – freshness / breaking-news indicator
  • engagement_score (0-100) – combined social metric

Articles are also tagged with category and extracted entities.
Processing is batched (BATCH_SIZE articles per AI call) to stay within
token limits and minimise API costs.
"""

import re
import json
import time
from config.logging_setup import get_logger
from ai.client import ask_ai

log = get_logger(__name__)

BATCH_SIZE = 8    # keeps each request well under Groq's 6000 TPM limit

# Priority weights for the overall rank score
_W = dict(viral=0.35, relevance=0.30, breaking=0.20, engagement=0.15)

_SYSTEM = (
    "You are a world-class sports social-media strategist. "
    "You respond only with valid JSON."
)

# Use a high-quota model for scoring (500k tokens/day free tier)
# Content generation still uses the bigger model from .env
_SCORING_MODEL = "llama-3.1-8b-instant"

# Max articles fed into the scorer — prevents burning daily quota on huge feeds
_MAX_SCORE = 80


def _build_scoring_prompt(batch: list[dict]) -> str:
    lines = []
    for i, art in enumerate(batch, start=1):
        line = f"{i}. [{art['source']}] {art['title']}"
        if art.get("summary"):
            line += f"\n   {art['summary'][:150]}"
        lines.append(line)

    return f"""You are scoring football news articles for a FIFA 2027 social-media pipeline.

Articles from "FIFA Inside" sources (source label starts with "FIFA Inside") are
official FIFA content covering rankings, analytics, women's football, transfers and
governance. Treat them as authoritative and score their relevance_score at least
10 points higher than non-official coverage of the same topic.

For EACH article return a JSON object with EXACTLY these fields:
  "index"          : article number (integer, 1-based)
  "relevance_score": 0-100  (how relevant to FIFA 2027 / World Cup; +10 for FIFA Inside)
  "viral_score"    : 0-100  (social-media viral potential)
  "breaking_score" : 0-100  (how breaking / time-sensitive)
  "engagement_score": 0-100 (comment / share / reaction potential)
  "why"            : one sentence explaining the top viral hook
  "category"       : one of: transfer | injury | result | announcement | ranking |
                              squad | controversy | logistics | stadium | analytics | other
  "entities"       : object with keys teams[], players[], countries[], stage

Scoring guide (viral_score):
  80-100 : blockbuster transfer, shocking result, major controversy, ranking shake-up
  50-79  : notable match, star player injury, squad announcement, ranking update
  20-49  : routine report, minor update, press-conference filler
  0-19   : off-topic or not football-related

Return ONLY a valid JSON array. No markdown. No extra text.

Articles:
{chr(10).join(lines)}"""


def _parse_batch(response_text: str, batch: list[dict]) -> list[dict]:
    """Attach scores from AI response to article dicts; fallback on parse error."""
    clean = re.sub(r"```(?:json)?|```", "", response_text).strip().strip("`")

    try:
        scored_list = json.loads(clean)
    except json.JSONDecodeError as exc:
        log.warning("Score JSON parse error: %s – assigning default scores", exc)
        for art in batch:
            art.setdefault("relevance_score",  0)
            art.setdefault("viral_score",       0)
            art.setdefault("breaking_score",    0)
            art.setdefault("engagement_score",  0)
            art.setdefault("why",               "")
            art.setdefault("category",          "other")
            art.setdefault("entities",          {})
        return batch

    lookup = {item["index"]: item for item in scored_list if "index" in item}

    for i, art in enumerate(batch, start=1):
        ai = lookup.get(i, {})
        art["relevance_score"]  = int(ai.get("relevance_score",  0))
        art["viral_score"]      = int(ai.get("viral_score",       0))
        art["breaking_score"]   = int(ai.get("breaking_score",    0))
        art["engagement_score"] = int(ai.get("engagement_score",  0))
        art["why"]              = ai.get("why",      "")
        art["category"]         = ai.get("category", "other").lower()
        art["entities"]         = ai.get("entities", {})
        base = (
            art["viral_score"]       * _W["viral"]
            + art["relevance_score"] * _W["relevance"]
            + art["breaking_score"]  * _W["breaking"]
            + art["engagement_score"] * _W["engagement"]
        )
        # Official FIFA Inside source: +10 priority boost, capped at 100
        if art.get("priority"):
            base += 10
        art["rank_score"] = int(min(base, 100))

    return batch


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Score all articles in batches and return them sorted by rank_score desc.

    Parameters
    ----------
    articles : list of article dicts from the scraping layer

    Returns
    -------
    list – same articles enriched with score fields, sorted best-first
    """
    # Priority (FIFA Inside) articles are always scored; non-priority capped newest-first
    priority   = [a for a in articles if a.get("priority")]
    non_priority = sorted(
        [a for a in articles if not a.get("priority")],
        key=lambda a: a.get("published_ts", 0), reverse=True,
    )
    slots = max(0, _MAX_SCORE - len(priority))
    articles = priority + non_priority[:slots]

    if len(priority) or slots < len(non_priority):
        log.info(
            "Scoring cap: %d priority + %d non-priority = %d total",
            len(priority), len(articles) - len(priority), len(articles),
        )

    all_scored: list[dict] = []
    n_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE

    for b in range(n_batches):
        start = b * BATCH_SIZE
        batch = articles[start : start + BATCH_SIZE]
        log.info("Scoring batch %d/%d (%d articles)", b + 1, n_batches, len(batch))

        prompt   = _build_scoring_prompt(batch)
        response = ask_ai(prompt, system=_SYSTEM, model=_SCORING_MODEL)
        scored   = _parse_batch(response, batch)
        all_scored.extend(scored)

        if b < n_batches - 1:
            time.sleep(12)  # stay under 6000 TPM — ~500 tokens/batch needs 12s gap

    all_scored.sort(key=lambda a: a.get("rank_score", 0), reverse=True)

    if all_scored:
        top = all_scored[0]
        log.info(
            "Top story (rank=%d): %s | viral=%d relevance=%d",
            top["rank_score"], top["title"][:60],
            top["viral_score"], top["relevance_score"],
        )

    return all_scored