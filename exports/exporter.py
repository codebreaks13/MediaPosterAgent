"""
exports/exporter.py
-------------------
Exports all pipeline outputs:
  • JSON   – full article data with all AI-generated fields
  • CSV    – flat spreadsheet of articles
  • HTML   – human-readable run report
  • Manifest – maps article → poster file paths
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from config.settings import EXPORTS_DIR
from config.logging_setup import get_logger

log = get_logger(__name__)


def _run_slug() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def export_json(articles: list[dict], run_id: str | None = None) -> Path:
    """Export full article data as JSON."""
    run_id = run_id or _run_slug()
    path   = EXPORTS_DIR / f"articles_{run_id}.json"
    path.write_text(
        json.dumps(articles, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    log.info("JSON export → %s (%d articles)", path, len(articles))
    return path


def export_csv(articles: list[dict], run_id: str | None = None) -> Path:
    """Export a flat CSV of all articles."""
    run_id = run_id or _run_slug()
    path   = EXPORTS_DIR / f"articles_{run_id}.csv"

    fields = [
        "title", "source", "published", "link",
        "rank_score", "viral_score", "relevance_score",
        "breaking_score", "engagement_score",
        "category", "why",
        "headline", "ai_summary",
        "poster_text", "hashtags",
        "image_prompt",
        "poster_portrait", "poster_square", "poster_landscape",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for art in articles:
            row = dict(art)
            # Flatten lists to strings for CSV
            row["hashtags"] = " ".join(art.get("hashtags", []))
            writer.writerow(row)

    log.info("CSV export → %s", path)
    return path


def export_manifest(articles: list[dict], run_id: str | None = None) -> Path:
    """Export a poster-asset manifest (JSON)."""
    run_id   = run_id or _run_slug()
    path     = EXPORTS_DIR / f"manifest_{run_id}.json"
    manifest = []

    for art in articles:
        manifest.append({
            "headline":          art.get("headline", art["title"]),
            "source":            art.get("source", ""),
            "date":              art.get("published", ""),
            "summary":           art.get("ai_summary", art.get("summary", "")),
            "viral_score":       art.get("viral_score",  0),
            "rank_score":        art.get("rank_score",   0),
            "caption":           art.get("instagram_caption", ""),
            "hashtags":          art.get("hashtags", []),
            "poster_prompt":     art.get("image_prompt", ""),
            "poster_portrait":   art.get("poster_portrait", ""),
            "poster_square":     art.get("poster_square",   ""),
            "poster_landscape":  art.get("poster_landscape",""),
            "link":              art.get("link", ""),
        })

    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log.info("Manifest export → %s", path)
    return path


def export_html_report(articles: list[dict], run_id: str | None = None) -> Path:
    """Generate a human-readable HTML run report."""
    run_id = run_id or _run_slug()
    path   = EXPORTS_DIR / f"report_{run_id}.html"
    now    = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    rows = ""
    for rank, art in enumerate(articles, start=1):
        ht  = art.get("hashtags", [])
        tag = " ".join(f"<span class='tag'>#{t}</span>" for t in ht[:5])
        rows += f"""
        <tr>
          <td>{rank}</td>
          <td><a href="{art.get('link','#')}" target="_blank">{art.get('headline', art['title'])}</a></td>
          <td>{art.get('source','')}</td>
          <td>{art.get('rank_score', 0)}</td>
          <td>{art.get('viral_score', 0)}</td>
          <td>{art.get('category','')}</td>
          <td>{tag}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FIFA 2027 Pipeline Report – {now}</title>
<style>
  body  {{ font-family: Arial, sans-serif; background:#0a1432; color:#eee; margin:2rem; }}
  h1    {{ color:#d4af37; }}
  table {{ border-collapse:collapse; width:100%; font-size:0.9em; }}
  th    {{ background:#1a2a5e; color:#d4af37; padding:8px 12px; text-align:left; }}
  td    {{ border-bottom:1px solid #1a2a5e; padding:7px 12px; }}
  tr:hover td {{ background:#111d44; }}
  a     {{ color:#7ab3ff; }}
  .tag  {{ background:#1a2a5e; border-radius:4px; padding:2px 6px;
           margin-right:4px; font-size:0.8em; color:#d4af37; }}
</style>
</head>
<body>
<h1>⚽ FIFA 2027 Pipeline Report</h1>
<p>Generated: {now} &nbsp;|&nbsp; Articles: {len(articles)}</p>
<table>
  <tr>
    <th>#</th><th>Headline</th><th>Source</th>
    <th>Rank</th><th>Viral</th><th>Category</th><th>Hashtags</th>
  </tr>
  {rows}
</table>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    log.info("HTML report → %s", path)
    return path


def export_all(articles: list[dict]) -> dict[str, Path]:
    """Run all exporters and return a dict of {format: path}."""
    run_id = _run_slug()
    return {
        "json":     export_json(articles,       run_id),
        "csv":      export_csv(articles,        run_id),
        "manifest": export_manifest(articles,   run_id),
        "report":   export_html_report(articles, run_id),
    }