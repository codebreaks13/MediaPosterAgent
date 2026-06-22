"""
main.py
-------
FIFA 2027 AI News Poster Generator — Full Pipeline Orchestrator

End-to-end flow:
  1. Scrape   – RSS feeds + HTML fallback
  2. Dedup    – remove near-duplicate articles
  3. Score    – AI multi-dimension ranking
  4. Filter   – keep top articles above MIN_VIRAL_SCORE
  5. Content  – AI social-media captions, SEO, poster text
  6. Prompts  – AI image-generation prompts
  7. Images   – generate background images
  8. Posters  – composite final poster (3 formats each)
  9. Cache    – persist processed URLs
  10. Export  – JSON / CSV / manifest / HTML report

Usage:
    python main.py              # run once
    python main.py --schedule   # run on schedule (interval from .env)
    python main.py --skip-images # skip image generation (text pipeline only)
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# ── Config & logging ──────────────────────────────────────────────────────────
from config.settings import MAX_ARTICLES_PER_RUN, MIN_VIRAL_SCORE
from config.logging_setup import get_logger

log = get_logger("pipeline")

# ── Pipeline modules ──────────────────────────────────────────────────────────
from ai.client import test_connection
from scraping import (
    fetch_rss_articles,
    scrape_html_articles,
    deduplicate_articles,
    RSS_SOURCES,
    HTML_SOURCES,
    get_trending_sports_sources,
    scrape_fifa_inside,
    FIFA_INSIDE_SOURCES,
)
from ranking import score_articles
from ai.content_generator import generate_content_batch
from prompts import generate_image_prompts_batch
from ai.poster_pipeline import run_stage1_batch, run_stage2_batch
from image_generation import generate_image
from poster_builder import build_all_formats
from storage import get_seen_urls, save_articles, save_run_metadata
from exports import export_all


def run_pipeline(skip_images: bool = False) -> dict:
    """
    Execute the full pipeline end-to-end.

    Parameters
    ----------
    skip_images : if True, skip image generation and poster building

    Returns
    -------
    dict with summary statistics about the run
    """
    start_time = time.time()
    run_id     = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    log.info("=" * 65)
    log.info("FIFA 2027 Pipeline  RUN ID: %s", run_id)
    log.info("=" * 65)

    # ── Step 1a: FIFA Inside (priority source) ────────────────────────────────
    log.info("STEP 1a/10 – Scraping inside.fifa.com (priority source, %d sections)",
             len(FIFA_INSIDE_SOURCES))
    fifa_articles = scrape_fifa_inside(FIFA_INSIDE_SOURCES)
    log.info("  FIFA Inside: %d articles", len(fifa_articles))

    # ── Step 1b: RSS feeds + Google Trends ───────────────────────────────────
    log.info("STEP 1b/10 – Scraping RSS feeds + Google Trends")
    log.info("  Fetching trending sports topics from Google …")
    trending_sources = get_trending_sports_sources()
    all_rss_sources  = {**RSS_SOURCES, **trending_sources}
    log.info("  Total RSS sources: %d (%d static + %d Google)",
             len(all_rss_sources), len(RSS_SOURCES), len(trending_sources))
    rss_articles = fetch_rss_articles(all_rss_sources)

    log.info("STEP 1c/10 – HTML scraping fallback")
    html_articles = scrape_html_articles(HTML_SOURCES)

    # FIFA Inside first so dedup keeps official articles over RSS mirrors
    raw_articles = fifa_articles + rss_articles + html_articles
    log.info("Total raw articles: %d  (%d FIFA Inside + %d RSS + %d HTML)",
             len(raw_articles), len(fifa_articles),
             len(rss_articles), len(html_articles))

    # ── Step 2: Deduplicate ───────────────────────────────────────────────────
    log.info("STEP 2/10 – Deduplication")
    seen_urls  = get_seen_urls()
    articles   = deduplicate_articles(raw_articles, seen_urls=seen_urls)

    if not articles:
        log.warning("No new articles found. Pipeline complete (nothing to process).")
        return {"run_id": run_id, "articles_processed": 0}

    # ── Step 3: Score ─────────────────────────────────────────────────────────
    log.info("STEP 3/10 – AI scoring  (%d articles)", len(articles))
    scored = score_articles(articles)

    # ── Step 4: Filter ────────────────────────────────────────────────────────
    log.info("STEP 4/10 – Filtering  (MIN_VIRAL_SCORE=%d)", MIN_VIRAL_SCORE)
    top = [a for a in scored if a.get("viral_score", 0) >= MIN_VIRAL_SCORE]
    top = top[:MAX_ARTICLES_PER_RUN]
    log.info("Articles after filter: %d", len(top))

    if not top:
        log.warning("No articles passed the viral score threshold.")
        return {"run_id": run_id, "articles_processed": 0}

    # ── Step 5: Stage 1 — Content + Image Brief (Groq 70b) ───────────────────
    # Single call per article: Bangla content, badge type, emphasis fragment,
    # social captions, image generation prompt. Prompt loaded from
    # prompts/stage1_content.md. Output stored in article dict as shared context.
    log.info("STEP 5/10 – Stage 1: Content & Image Orchestration  (%d articles)", len(top))
    top = run_stage1_batch(top, delay=0.5)

    # ── Step 6: (placeholder — image prompt is now part of Stage 1) ──────────
    log.info("STEP 6/10 – Image prompts embedded in Stage 1 output (skipping legacy step)")

    # ── Steps 7–8: Images & Posters ───────────────────────────────────────────
    if skip_images:
        log.info("STEP 7–8 – SKIPPED (--skip-images flag)")
    else:
        log.info("STEP 7/10 – Image generation")
        for i, art in enumerate(top, start=1):
            log.info("  Image %d/%d: %s", i, len(top), art["title"][:50])
            bg_path = generate_image(
                prompt          = art.get("image_prompt", ""),
                negative_prompt = art.get("negative_prompt", ""),
                size            = "square",   # generate square; poster builder handles variants
            )
            art["bg_image_path"] = str(bg_path) if bg_path else ""

        # ── Step 7.5: Stage 2 — Typography Spec (Groq 8b) ────────────────────
        # Receives full Stage 1 context from each article dict.
        # Outputs AI-driven CSS typography parameters (font sizes, weights,
        # emphasis colour, badge colour). Prompt from prompts/stage2_typography.md.
        log.info("STEP 7.5/10 – Stage 2: Typography Orchestration  (%d articles)", len(top))
        top = run_stage2_batch(top, size="square", delay=0.2)

        log.info("STEP 8/10 – Poster composition")
        for i, art in enumerate(top, start=1):
            log.info("  Poster %d/%d: %s", i, len(top), art["title"][:50])
            # Prefer AI-generated image, fall back to RSS thumbnail, then gradient
            ai_bg = Path(art["bg_image_path"]) if art.get("bg_image_path") else None
            bg = (
                ai_bg if ai_bg and ai_bg.exists()
                else art.get("image_url") or None
            )
            formats = build_all_formats(art, bg)
            art["poster_portrait"]  = str(formats.get("portrait",  "") or "")
            art["poster_square"]    = str(formats.get("square",    "") or "")
            art["poster_landscape"] = str(formats.get("landscape", "") or "")

    # ── Step 9: Cache ─────────────────────────────────────────────────────────
    log.info("STEP 9/10 – Caching processed URLs")
    save_articles(top)

    # ── Step 10: Export ───────────────────────────────────────────────────────
    log.info("STEP 10/10 – Exporting outputs")
    export_paths = export_all(top)

    elapsed = time.time() - start_time
    summary = {
        "run_id":             run_id,
        "articles_processed": len(top),
        "elapsed_seconds":    round(elapsed, 1),
        "exports":            {k: str(v) for k, v in export_paths.items()},
        "top_story":          top[0]["title"] if top else "",
        "top_viral_score":    top[0].get("viral_score", 0) if top else 0,
    }

    save_run_metadata(summary)

    log.info("=" * 65)
    log.info("Pipeline COMPLETE  articles=%d  elapsed=%.1fs",
             len(top), elapsed)
    log.info("Top story: %s (viral=%d)",
             summary["top_story"][:60], summary["top_viral_score"])
    log.info("Exports:")
    for fmt, path in export_paths.items():
        log.info("  %-10s  %s", fmt, path)
    log.info("=" * 65)

    return summary


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FIFA 2027 AI News Poster Generator"
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="Run continuously on a schedule (interval from .env)"
    )
    parser.add_argument(
        "--skip-images", action="store_true",
        help="Skip image generation and poster building (text pipeline only)"
    )
    args = parser.parse_args()

    # ── Pre-flight checks ─────────────────────────────────────────────────────
    log.info("Checking AI connection …")
    if not test_connection():
        log.error("AI connection failed. Check AI_API_KEY in .env and try again.")
        sys.exit(1)

    pipeline_fn = lambda: run_pipeline(skip_images=args.skip_images)  # noqa: E731

    if args.schedule:
        from scheduler import run_with_schedule
        run_with_schedule(pipeline_fn)
    else:
        run_pipeline(skip_images=args.skip_images)


if __name__ == "__main__":
    main()