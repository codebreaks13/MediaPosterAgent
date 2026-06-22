"""
scraping/sources.py
-------------------
Master list of all news sources used by the FIFA 2027 pipeline.
Add / remove entries here; everything else adapts automatically.
"""

# ── RSS sources ───────────────────────────────────────────────────────────────
# Key   = human-readable label used throughout the pipeline.
# Value = RSS feed URL.

RSS_SOURCES: dict[str, str] = {
    # Football / Soccer
    "BBC Sport Football": "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports Football":"https://www.skysports.com/rss/11095",
    "ESPN Soccer":        "https://www.espn.com/espn/rss/soccer/news",

    # Multi-sport
    "BBC Sport":          "https://feeds.bbci.co.uk/sport/rss.xml",
    "ESPN Top":           "https://www.espn.com/espn/rss/news",

    # Cricket, F1, Tennis via BBC
    "BBC Sport Cricket":  "https://feeds.bbci.co.uk/sport/cricket/rss.xml",
    "BBC Sport F1":       "https://feeds.bbci.co.uk/sport/formula1/rss.xml",
    "BBC Sport Tennis":   "https://feeds.bbci.co.uk/sport/tennis/rss.xml",
}

# ── HTML-scrape sources (fallback when RSS is unavailable) ────────────────────
HTML_SOURCES: dict[str, str] = {
    "BBC Sport":          "https://www.bbc.com/sport",
}