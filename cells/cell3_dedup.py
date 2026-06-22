# ─────────────────────────────────────────────────────────────────
# CELL 3 – Deduplication (Jaccard + URL-level)
# ─────────────────────────────────────────────────────────────────
import re  ##comment: 're' was missing; required for tokenization and regex operations


_STOP_WORDS = frozenset({
    "a","an","the","in","on","at","of","to","and","or","but",
    "is","are","was","were","for","with","from","by","as","it",
    "its","this","that","he","she","they","his","her","has",
    "have","had","be","been","will","not",
})


def _tokens(title):
    words = re.sub(r"[^\w\s]", "", title.lower()).split()
    return frozenset(w for w in words if w not in _STOP_WORDS)


def deduplicate_articles(articles, threshold=0.60):
    """
    Remove near-duplicate articles using Jaccard title similarity.
    Also deduplicates by exact URL match.
    """
    unique, seen_token_sets, seen_urls = [], [], set()

    for article in articles:
        link = article.get("link", "")
        if link and link in seen_urls:
            continue
        if link:
            seen_urls.add(link)

        tok = _tokens(article["title"])
        is_dup = any(
            (len(tok & seen) / len(tok | seen)) >= threshold
            for seen in seen_token_sets
            if tok and seen
        )
        if not is_dup:
            unique.append(article)
            seen_token_sets.append(tok)

    removed = len(articles) - len(unique)
    print(f"Dedup: {len(articles)} → {len(unique)} articles ({removed} removed)")
    return unique


# ── Run ────────────────────────────────────────────────────────────────────
unique_articles = deduplicate_articles(raw_articles)  ##comment: 'raw_articles' is undefined here; this script expects notebook globals or should accept an 'articles' input parameter
