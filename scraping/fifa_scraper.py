"""
scraping/fifa_scraper.py
------------------------
Priority scraper for inside.fifa.com — the official FIFA news portal.

Extracts articles from six sections of inside.fifa.com by parsing the
embedded Next.js __NEXT_DATA__ JSON blob (no RSS feed required).
Articles are tagged with priority=True so the scorer gives them a
+10 rank-score boost over equivalent non-official sources.

Sections scraped:
  • FIFA Rankings           – en/fifa-rankings
  • FIFA Inside Home        – en/
  • FIFA Women's Football   – womens-football
  • FIFA Advancing Football – advancing-football
  • FIFA Transfer System    – transfer-system
  • FIFA Talent Development – talent-development
"""

import re
import json
import time

import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from config.settings import MAX_RETRIES, RETRY_DELAY
from config.logging_setup import get_logger

log = get_logger(__name__)

_HEADERS = {"User-Agent": "FIFA2027Bot/1.0"}
_INSIDE_BASE = "https://www.inside.fifa.com"
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.S,
)

FIFA_INSIDE_SOURCES: dict[str, str] = {
    "FIFA Rankings":           "https://inside.fifa.com/en/fifa-rankings",
    "FIFA Inside Home":        "https://inside.fifa.com/en/",
    "FIFA Women's Football":   "https://inside.fifa.com/womens-football",
    "FIFA Advancing Football": "https://inside.fifa.com/advancing-football",
    "FIFA Transfer System":    "https://inside.fifa.com/transfer-system",
    "FIFA Talent Development": "https://inside.fifa.com/talent-development",
}


@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_fixed(RETRY_DELAY))
def _get(url: str) -> requests.Response:
    resp = requests.get(url, headers=_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp


def _extract_richtext(node: dict | list | None) -> str:
    """Recursively extract plain text from a Contentful Rich Text JSON document."""
    if not isinstance(node, dict):
        return ""
    if node.get("nodeType") == "text":
        return node.get("value", "")
    parts = [_extract_richtext(child) for child in node.get("content", [])]
    sep = "\n" if node.get("nodeType") in ("paragraph", "list-item") else ""
    return sep.join(p for p in parts if p)


def _find_article_cards(obj: dict | list) -> list[dict]:
    """Recursively find all FFArticleCardProps entries in a nested structure."""
    found: list[dict] = []
    if isinstance(obj, dict):
        if obj.get("typeRender") == "FFArticleCardProps" and obj.get("articleTitle"):
            found.append(obj)
        for v in obj.values():
            found.extend(_find_article_cards(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_article_cards(item))
    return found


def _fetch_article_fulltext(article_url: str) -> str:
    """
    Fetch a single FIFA Inside article page and return its richtext body as
    plain text.  Silently returns "" on any error so the listing summary
    is used as fallback.
    """
    try:
        resp = _get(article_url)
        m = _NEXT_DATA_RE.search(resp.text)
        if not m:
            return ""
        pp = json.loads(m.group(1))["props"]["pageProps"]
        rt = pp.get("richTextProps", {}).get("document", {})
        return _extract_richtext(rt).strip()
    except Exception as exc:
        log.debug("Full-text fetch failed for %s: %s", article_url, exc)
        return ""


def scrape_fifa_inside(
    sources: dict[str, str] | None = None,
    fetch_full_text: bool = False,
) -> list[dict]:
    """
    Scrape FIFA Inside listing pages and return normalised article dicts.

    Parameters
    ----------
    sources        : dict {label: url}; defaults to FIFA_INSIDE_SOURCES
    fetch_full_text: if True, fetch each article page for body text (slower)

    Returns
    -------
    list of article dicts matching the rss_fetcher schema, plus:
        priority (bool) = True   — used by scorer for +10 rank-score boost
        tag      (str)           — article tag from FIFA Inside
    """
    sources = sources or FIFA_INSIDE_SOURCES
    all_articles: list[dict] = []
    seen_links: set[str] = set()

    for source_name, url in sources.items():
        log.info("FIFA Inside  %-26s  %s", source_name, url)
        try:
            resp = _get(url)
            m = _NEXT_DATA_RE.search(resp.text)
            if not m:
                log.warning("%s: no __NEXT_DATA__ found — skipping", source_name)
                continue

            page_data = json.loads(m.group(1))["props"]["pageProps"].get("pageData", {})
            cards = _find_article_cards(page_data)

            count = 0
            for card in cards:
                link = card.get("articleLink", "")
                if link.startswith("/"):
                    link = _INSIDE_BASE + link
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                summary = (card.get("description") or "").strip()
                full_text = summary

                if fetch_full_text:
                    fetched = _fetch_article_fulltext(link)
                    if fetched:
                        full_text = fetched
                    time.sleep(0.25)

                all_articles.append({
                    "title":        (card.get("articleTitle") or "No title").strip(),
                    "summary":      summary,
                    "full_text":    full_text,
                    "link":         link,
                    "source":       f"FIFA Inside – {source_name.replace('FIFA ', '')}",
                    "published":    card.get("articleDate", ""),
                    "published_ts": 0.0,   # date strings only; scorer sorts by rank
                    "image_url":    (card.get("image") or {}).get("src", ""),
                    "tag":          card.get("articleTag", ""),
                    "priority":     True,
                })
                count += 1

            log.info("  → %d articles", count)

        except Exception as exc:
            log.error("FIFA Inside %s FAILED: %s", source_name, exc)

        time.sleep(0.3)

    log.info(
        "FIFA Inside total: %d unique articles from %d sources",
        len(all_articles), len(sources),
    )
    return all_articles
