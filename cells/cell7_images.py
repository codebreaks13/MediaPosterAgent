# ─────────────────────────────────────────────────────────────────
# CELL 7 – Background image generation
#
# Generates one background image per top article.
# Backend is controlled by IMAGE_BACKEND in .env:
#   mock       – solid dark-blue placeholder (no API needed)
#   stability  – Stability AI (STABILITY_API_KEY required)
#   replicate  – Flux via Replicate (REPLICATE_API_KEY required)
#
# Each image is saved to the posters/ directory.
# ─────────────────────────────────────────────────────────────────

import os
from pathlib import Path

POSTERS_DIR = Path("posters")
POSTERS_DIR.mkdir(exist_ok=True)

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY", "")


def _mock_image(w, h, label="FIFA 2027"):
    """Create a dark-blue placeholder PNG."""
    img  = Image.new("RGB", (w, h), (8, 20, 50))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        shade = int(30 + 20 * y / h)
        draw.line([(0, y), (w, y)], fill=(shade, shade * 2, shade * 5))
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32
        )
    except Exception:
        font = ImageFont.load_default()
    draw.text((w // 2, h // 2), f"FIFA 2027 | {label}", fill=(212,175,55),
              anchor="mm", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _stability_image(prompt, negative_prompt, w, h):
    import requests as req
    resp = req.post(
        "https://api.stability.ai/v2beta/stable-image/generate/sd3",
        headers={"authorization": f"Bearer {STABILITY_API_KEY}", "accept": "image/*"},
        files={"none": ""},
        data={"prompt": prompt, "negative_prompt": negative_prompt,
              "width": str(w), "height": str(h), "output_format": "png"},
        timeout=120,
    )
    resp.raise_for_status()
    return io.BytesIO(resp.content)


def _replicate_image(prompt, negative_prompt, w, h):
    import replicate, requests as req
    output = replicate.run(
        "black-forest-labs/flux-1.1-pro",
        input={"prompt": prompt, "negative_prompt": negative_prompt,
               "width": w, "height": h, "output_format": "png"},
    )
    url  = str(output)
    resp = req.get(url, timeout=120)
    resp.raise_for_status()
    return io.BytesIO(resp.content)


def generate_bg_image(article, size=(1080, 1080)):
    w, h = size
    prompt    = article.get("image_prompt", "FIFA 2027 football match")
    neg       = article.get("negative_prompt", "text, watermark, blurry")
    slug      = "".join(c if c.isalnum() else "_" for c in article["title"][:30])
    out_path  = POSTERS_DIR / f"bg_{slug}.png"

    try:
        if IMAGE_BACKEND == "stability" and STABILITY_API_KEY:
            buf = _stability_image(prompt, neg, w, h)
        elif IMAGE_BACKEND == "replicate" and REPLICATE_API_KEY:
            buf = _replicate_image(prompt, neg, w, h)
        else:
            buf = _mock_image(w, h)

        img = Image.open(buf).convert("RGB").resize((w, h))
        img.save(out_path, "PNG")
        return out_path

    except Exception as exc:
        print(f"    Image gen failed ({exc}); using mock.")
        buf = _mock_image(w, h)
        img = Image.open(buf)
        img.save(out_path, "PNG")
        return out_path


# ── Run ────────────────────────────────────────────────────────────────────
print(f"Generating background images  backend={IMAGE_BACKEND} ...\n")
for idx, art in enumerate(top_articles, start=1):
    print(f"  [{idx}/{len(top_articles)}] {art['title'][:50]}")
    art["bg_image_path"] = str(generate_bg_image(art))

print(f"\nImages saved to {POSTERS_DIR}/")