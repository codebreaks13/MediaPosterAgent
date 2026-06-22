# ─────────────────────────────────────────────────────────────────
# CELL 2 – RSS feed fetcher + FIFA Inside scraper (priority source)
#
# Fetches from:
#   1. inside.fifa.com (rankings, homepage, women's, etc.) – PRIORITY
#   2. Standard RSS feeds (BBC, Sky, ESPN, Goal, Reuters)
#
# Normalises every article into the same dict schema.
# ─────────────────────────────────────────────────────────────────

RSS_SOURCES = {
    "FIFA News":     "https://www.fifa.com/rss-feeds/news/en.xml",
    "BBC Sport":     "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "Sky Sports":    "https://www.skysports.com/rss/11095",
    "ESPN Soccer":   "https://www.espn.com/espn/rss/soccer/news",
    "Goal.com":      "https://www.goal.com/feeds/en/news",
    "Reuters Sport": "https://feeds.reuters.com/reuters/sportsNews",
}

# Priority: scraped directly from inside.fifa.com using Next.js page data.
# Covers rankings, women's football, transfers, and general FIFA news.
FIFA_INSIDE_SOURCES = {
    "FIFA Rankings":           "https://inside.fifa.com/en/fifa-rankings",
    "FIFA Inside Home":        "https://inside.fifa.com/en/",
    "FIFA Women's Football":   "https://inside.fifa.com/womens-football",
    "FIFA Advancing Football": "https://inside.fifa.com/advancing-football",
    "FIFA Transfer System":    "https://inside.fifa.com/transfer-system",
    "FIFA Talent Development": "https://inside.fifa.com/talent-development",
}

_HEADERS = {"User-Agent": "FIFA2027Bot/1.0"}
_INSIDE_BASE = "https://www.inside.fifa.com"


def _clean_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _extract_richtext(node):
    """Recursively extract plain text from a Contentful Rich Text JSON document."""
    if not isinstance(node, dict):
        return ""
    if node.get("nodeType") == "text":
        return node.get("value", "")
    parts = []
    for child in node.get("content", []):
        parts.append(_extract_richtext(child))
    sep = "\n" if node.get("nodeType") in ("paragraph", "list-item") else ""
    return sep.join(p for p in parts if p)


def _fetch_article_text(article_url):
    """Fetch a single FIFA Inside article page and return its body text."""
    try:
        resp = requests.get(article_url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        m = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            resp.text, re.S
        )
        if not m:
            return ""
        data = json.loads(m.group(1))
        pp = data["props"]["pageProps"]
        rt = pp.get("richTextProps", {}).get("document", {})
        return _extract_richtext(rt).strip()
    except Exception:
        return ""


def _find_article_cards(obj):
    """Recursively find all FFArticleCardProps entries in a nested dict/list."""
    found = []
    if isinstance(obj, dict):
        if obj.get("typeRender") == "FFArticleCardProps" and obj.get("articleTitle"):
            found.append(obj)
        for v in obj.values():
            found.extend(_find_article_cards(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_article_cards(item))
    return found


def scrape_fifa_inside(sources, fetch_full_text=False):
    """
    Scrape FIFA Inside listing pages via their embedded Next.js JSON data.
    Returns a flat list of normalised article dicts with source marked as
    'FIFA Inside' for priority boosting in scoring.
    Setting fetch_full_text=True makes an extra HTTP request per article to
    get the full body text (slower but richer).
    """
    all_articles = []
    seen_links = set()

    for source_name, url in sources.items():
        print(f"Scraping {source_name} ...", end=" ")
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=20)
            resp.raise_for_status()
            m = re.search(
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                resp.text, re.S
            )
            if not m:
                print("SKIP (no page data)")
                continue

            data = json.loads(m.group(1))
            page_data = data["props"]["pageProps"].get("pageData", {})
            cards = _find_article_cards(page_data)

            count = 0
            for card in cards:
                link = card.get("articleLink", "")
                # Resolve relative links
                if link.startswith("/"):
                    link = _INSIDE_BASE + link
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                summary = (card.get("description") or "").strip()
                full_text = summary

                if fetch_full_text:
                    fetched = _fetch_article_text(link)
                    if fetched:
                        full_text = fetched
                    time.sleep(0.25)

                all_articles.append({
                    "title":     (card.get("articleTitle") or "No title").strip(),
                    "summary":   summary,
                    "full_text": full_text,
                    "link":      link,
                    "source":    f"FIFA Inside – {source_name.replace('FIFA ', '')}",
                    "published": card.get("articleDate", ""),
                    "tag":       card.get("articleTag", ""),
                    "priority":  True,   # flag for score boosting in cell 5
                })
                count += 1

            print(f"OK ({count} articles)")
        except Exception as exc:
            print(f"FAILED – {exc}")
        time.sleep(0.3)

    return all_articles


def fetch_rss_articles(sources):
    """Fetch all RSS feeds; return flat list of normalised article dicts."""
    all_articles = []

    for source_name, feed_url in sources.items():
        print(f"Fetching {source_name} ...", end=" ")
        try:
            feed = feedparser.parse(feed_url, request_headers=_HEADERS)
            if feed.bozo:
                print("(parse warning)", end=" ")
            count = 0
            for entry in feed.entries:
                summary  = _clean_html(getattr(entry, "summary", "") or "")
                content  = ""
                if hasattr(entry, "content") and entry.content:
                    content = _clean_html(entry.content[0].get("value", ""))
                all_articles.append({
                    "title":     (entry.get("title") or "No title").strip(),
                    "summary":   summary,
                    "full_text": content or summary,
                    "link":      entry.get("link", ""),
                    "source":    source_name,
                    "published": getattr(entry, "published", ""),
                    "tag":       "",
                    "priority":  False,
                })
                count += 1
            print(f"OK ({count} articles)")
        except Exception as exc:
            print(f"FAILED – {exc}")
        time.sleep(0.3)

    return all_articles


# ── Run ────────────────────────────────────────────────────────────────────
print("=== FIFA Inside (priority source) ===")
fifa_articles = scrape_fifa_inside(FIFA_INSIDE_SOURCES)

print("\n=== RSS Feeds ===")
rss_articles = fetch_rss_articles(RSS_SOURCES)

# FIFA Inside articles placed first so dedup keeps them over RSS duplicates
raw_articles = fifa_articles + rss_articles
print(f"\nTotal fetched: {len(raw_articles)} articles "
      f"({len(fifa_articles)} FIFA Inside + {len(rss_articles)} RSS)")
