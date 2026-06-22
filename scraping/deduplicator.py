"""
scraping/deduplicator.py
------------------------
Near-duplicate removal using Jaccard similarity on headline tokens.
Evolved from the original Cell 3 — now also URL-deduplicates and
supports a seen-URL cache for incremental runs.
"""

import re
from config.logging_setup import get_logger

log = get_logger(__name__)

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "in", "on", "at", "of", "to",
    "and", "or", "but", "is", "are", "was", "were",
    "for", "with", "from", "by", "as", "it", "its",
    "this", "that", "he", "she", "they", "his", "her",
    "has", "have", "had", "be", "been", "will", "not",
})


def _tokens(title: str) -> frozenset[str]:
    words = re.sub(r"[^\w\s]", "", title.lower()).split()
    return frozenset(w for w in words if w not in _STOP_WORDS)


def deduplicate_articles(
    articles: list[dict],
    threshold: float = 0.60,
    seen_urls: set[str] | None = None,
) -> list[dict]:
    """
    Remove near-duplicate articles.

    Two articles are considered duplicates when their Jaccard title
    similarity >= `threshold` (default 60%).

    Parameters
    ----------
    articles    : list of article dicts
    threshold   : similarity threshold (0–1)
    seen_urls   : optional set of previously processed URLs to skip

    Returns
    -------
    list – deduplicated articles, original order preserved
    """
    seen_urls = seen_urls or set()
    unique: list[dict] = []
    seen_token_sets: list[frozenset] = []

    for article in articles:
        # ── URL-level dedup ──────────────────────────────────────────────────
        link = article.get("link", "")
        if link and link in seen_urls:
            continue
        if link:
            seen_urls.add(link)

        # ── Title-similarity dedup ───────────────────────────────────────────
        tok = _tokens(article["title"])
        is_dup = False
        for seen in seen_token_sets:
            if not tok or not seen:
                continue
            jaccard = len(tok & seen) / len(tok | seen)
            if jaccard >= threshold:
                is_dup = True
                break

        if not is_dup:
            unique.append(article)
            seen_token_sets.append(tok)

    removed = len(articles) - len(unique)
    log.info(
        "Dedup: %d → %d articles (%d duplicates removed)",
        len(articles), len(unique), removed,
    )
    return unique