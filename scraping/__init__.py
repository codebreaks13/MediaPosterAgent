from .rss_fetcher import fetch_rss_articles
from .html_scraper import scrape_html_articles
from .deduplicator import deduplicate_articles
from .sources import RSS_SOURCES, HTML_SOURCES
from .trends_fetcher import get_trending_sports_sources
from .fifa_scraper import scrape_fifa_inside, FIFA_INSIDE_SOURCES

__all__ = [
    "fetch_rss_articles",
    "scrape_html_articles",
    "deduplicate_articles",
    "RSS_SOURCES",
    "HTML_SOURCES",
    "get_trending_sports_sources",
    "scrape_fifa_inside",
    "FIFA_INSIDE_SOURCES",
]