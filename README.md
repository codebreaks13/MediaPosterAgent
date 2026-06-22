# ⚽ FIFA 2027 AI News Poster Generator

A fully automated, production-ready pipeline that scrapes real-time football
news, scores articles for viral potential using AI, generates professional
social-media content and image prompts, composites poster images in three
formats, and exports everything for publishing.

---

## Architecture

```
main.py  (orchestrator)
│
├── scraping/
│   ├── sources.py          RSS + HTML source registry
│   ├── rss_fetcher.py      Fetches all RSS feeds (with retry)
│   ├── html_scraper.py     HTML scraping fallback
│   └── deduplicator.py     Jaccard + URL dedup
│
├── ai/
│   ├── client.py           Provider-agnostic ask_ai() (Groq | Claude | Gemini)
│   └── content_generator.py  Social captions, SEO, poster text
│
├── ranking/
│   └── scorer.py           4-dimension AI scoring + ranking
│
├── prompts/
│   └── image_prompt_generator.py  AI image prompt generation
│
├── image_generation/
│   └── generator.py        Stability AI | Replicate/Flux | Gemini | mock
│
├── poster_builder/
│   └── builder.py          PIL compositor: 3 formats per article
│
├── storage/
│   └── cache.py            JSON article cache (incremental runs)
│
├── exports/
│   └── exporter.py         JSON / CSV / HTML report / manifest
│
├── scheduler/
│   └── runner.py           schedule-based recurring execution
│
├── config/
│   ├── settings.py         .env loader + typed constants
│   └── logging_setup.py    Rotating file + console logging
│
├── cells/                  Jupyter notebook cell sources (cell1–cell9)
├── news/                   Article cache + run metadata
├── posters/                Generated poster images
├── exports/                JSON / CSV / HTML exports
└── logs/                   Rotating log files
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure `.env`

Your `.env` is already set up with your Groq key.
To add image generation, add one of:

```env
# Stability AI (Stable Diffusion XL)
STABILITY_API_KEY=your_key_here
IMAGE_BACKEND=stability

# OR Replicate (Flux)
REPLICATE_API_KEY=your_key_here
IMAGE_BACKEND=replicate
```

Leave `IMAGE_BACKEND=mock` to test without image API credits.

### 3. Run the pipeline

```bash
# Run once
python main.py

# Run and skip image generation (text-only, fastest)
python main.py --skip-images

# Run on a schedule (every N minutes from .env)
python main.py --schedule
```

### 4. Jupyter notebook

```bash
# Generate the notebook from cell source files
python generate_notebook.py

# Open it
jupyter notebook news_agent.ipynb
```

---

## Pipeline Steps

| Step | Module | What happens |
|------|--------|--------------|
| 1 | `scraping/rss_fetcher.py` | Fetch all RSS feeds with retry |
| 1b | `scraping/html_scraper.py` | HTML scraping fallback |
| 2 | `scraping/deduplicator.py` | Jaccard + URL deduplication |
| 3 | `ranking/scorer.py` | AI scores: relevance, viral, breaking, engagement |
| 4 | Filter | Keep articles above `MIN_VIRAL_SCORE` |
| 5 | `ai/content_generator.py` | Headlines, captions, hashtags, SEO |
| 6 | `prompts/image_prompt_generator.py` | AI image generation prompts |
| 7 | `image_generation/generator.py` | Generate background images |
| 8 | `poster_builder/builder.py` | Composite 3-format posters |
| 9 | `storage/cache.py` | Cache processed URLs |
| 10 | `exports/exporter.py` | JSON / CSV / HTML / manifest |

---

## Output Formats

### Poster sizes
| Format | Dimensions | Use case |
|--------|-----------|----------|
| Portrait | 1080 × 1350 | Instagram feed post |
| Square | 1080 × 1080 | Facebook / general |
| Landscape | 1920 × 1080 | Twitter banner / YouTube |

### Export files (in `exports/`)
- `articles_YYYYMMDD_HHMMSS.json` — full article data
- `articles_YYYYMMDD_HHMMSS.csv`  — spreadsheet
- `report_YYYYMMDD_HHMMSS.html`   — human-readable ranked report
- `manifest_YYYYMMDD_HHMMSS.json` — poster asset manifest

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `groq` | `groq` \| `claude` \| `gemini` |
| `AI_API_KEY` | — | API key for your AI provider |
| `AI_MODEL` | `llama-3.3-70b-versatile` | Model name |
| `IMAGE_BACKEND` | `mock` | `mock` \| `stability` \| `replicate` \| `gemini` |
| `MIN_VIRAL_SCORE` | `5` | Minimum viral score (0–100) to process |
| `MAX_ARTICLES_PER_RUN` | `20` | Max articles per pipeline run |
| `SCHEDULE_INTERVAL_MINUTES` | `60` | Interval for `--schedule` mode |
| `MAX_RETRIES` | `3` | API retry attempts |
| `RETRY_DELAY_SECONDS` | `5` | Seconds between retries |

---

## Switching AI Providers

Update `.env` and re-run:

```env
# Groq (current)
AI_PROVIDER=groq
AI_MODEL=llama-3.3-70b-versatile

# Anthropic Claude
AI_PROVIDER=claude
AI_MODEL=claude-sonnet-4-6

# Google Gemini
AI_PROVIDER=gemini
AI_MODEL=gemini-2.0-flash
```

---

## Adding News Sources

Edit `scraping/sources.py`:

```python
RSS_SOURCES = {
    "My Source": "https://example.com/rss.xml",
    # ...existing sources...
}
```

---

## Production Checklist

- [ ] Set real API keys in `.env`
- [ ] Set `IMAGE_BACKEND=stability` or `replicate`
- [ ] Adjust `MIN_VIRAL_SCORE` to taste (40+ for strict filtering)
- [ ] Run `python main.py --schedule` in a screen / tmux / systemd service
- [ ] Check `logs/pipeline.log` for errors
- [ ] Review `exports/report_*.html` after each run# MediaPosterAgent
