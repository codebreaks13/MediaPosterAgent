"""
generate_notebook.py
--------------------
Reads the 9 cell source files from cells/ and assembles them into
news_agent.ipynb — the FIFA 2027 AI News Poster Generator notebook.

Run once:
    python generate_notebook.py

You can delete this file after the notebook has been created.
"""

import json
import pathlib

NOTEBOOK_TEMPLATE = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0",
        },
    },
    "cells": [],
}

INTRO_MD = """\
# ⚽ FIFA 2027 AI News Poster Generator

An end-to-end pipeline that scrapes football news, scores articles for viral
potential, generates social-media content, and composites poster images.

## Quick start

1. Ensure `.env` exists next to this notebook:
```
AI_PROVIDER=groq
AI_API_KEY=your-groq-key
AI_MODEL=llama-3.3-70b-versatile
IMAGE_BACKEND=mock
MIN_VIRAL_SCORE=5
MAX_ARTICLES_PER_RUN=20
```
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. **Run all cells top-to-bottom** (Kernel → Restart & Run All).

## Image generation
Set `IMAGE_BACKEND` in `.env`:
| Value | Backend | Key needed |
|-------|---------|------------|
| `mock` | Solid-colour placeholder (default) | — |
| `stability` | Stable Diffusion XL via Stability AI | `STABILITY_API_KEY` |
| `replicate` | Flux via Replicate | `REPLICATE_API_KEY` |

## Cells overview
| # | Name | What it does |
|---|------|--------------|
| 1 | Imports | Load env, imports |
| 2 | RSS Fetch | Scrape all news sources |
| 3 | Dedup | Remove duplicate articles |
| 4 | AI Client | Multi-provider LLM wrapper |
| 5 | Scoring | 4-dimension viral scoring |
| 6 | Content | Social captions + image prompts |
| 7 | Images | Generate background images |
| 8 | Posters | Composite final posters (3 formats) |
| 9 | Export | JSON / CSV / HTML + console report |

> **Production mode**: use `python main.py` for scheduled automated runs.
"""

CELL_FILES = [
    "cells/cell1_imports.py",
    "cells/cell2_rss.py",
    "cells/cell3_dedup.py",
    "cells/cell4_ai.py",
    "cells/cell5_scoring.py",
    "cells/cell6_content.py",
    "cells/cell7_images.py",
    "cells/cell8_posters.py",
    "cells/cell9_export.py",
]


def make_markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.splitlines(keepends=True),
    }


def make_code_cell(source: str, cell_id: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": cell_id,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def build_notebook() -> dict:
    nb = dict(NOTEBOOK_TEMPLATE)
    nb["cells"] = [make_markdown_cell(INTRO_MD)]

    base = pathlib.Path(__file__).parent
    for i, rel_path in enumerate(CELL_FILES, start=1):
        full_path = base / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Missing cell file: {full_path}")
        source = full_path.read_text(encoding="utf-8")
        nb["cells"].append(make_code_cell(source, f"cell_{i:02d}"))

    return nb


if __name__ == "__main__":
    notebook = build_notebook()
    output   = pathlib.Path(__file__).parent / "news_agent.ipynb"

    with open(output, "w", encoding="utf-8") as fh:
        json.dump(notebook, fh, indent=1, ensure_ascii=False)

    print(f"✅  Notebook written → {output}")
    print(f"    Cells: 1 markdown + {len(CELL_FILES)} code = {1+len(CELL_FILES)} total")