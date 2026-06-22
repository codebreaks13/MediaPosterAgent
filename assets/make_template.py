"""
assets/make_template.py
-----------------------
Run once to generate the Boishakhi TV poster overlay template PNGs.

    python assets/make_template.py

Outputs:
    assets/boishakhi_template.png          (1080×1080 — square)
    assets/boishakhi_template_portrait.png (1080×1350 — portrait)
    assets/boishakhi_template_landscape.png(1080×566  — landscape)

Design spec:
  - Solid green top header bar  (#006a4e) carrying the channel logo text
  - 3px red accent line below header (#f42a41)
  - Thin green border frame (4px)
  - Top-right red corner triangle (decorative stamp)
  - Solid green footer bar (#006a4e)
  - Left red vertical stripe in footer
  - All non-brand areas: fully transparent (background image + text renders through)
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ASSETS = Path(__file__).parent

# ── Brand palette ─────────────────────────────────────────────────────────────
GREEN      = (0, 106, 78, 255)     # #006a4e
GREEN_DARK = (0, 78, 57, 255)      # darker shade for depth
RED        = (244, 42, 65, 255)    # #f42a41
WHITE      = (255, 255, 255, 255)
WHITE_DIM  = (255, 255, 255, 170)  # 67% opacity white for secondary text
CLEAR      = (0, 0, 0, 0)          # fully transparent

# ── Font paths (Noto Sans Bengali — confirmed on system) ──────────────────────
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"
FONT_LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

SIZES = {
    "square":    (1080, 1080),
    "portrait":  (1080, 1350),
    "landscape": (1080,  566),
}


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def make_template(w: int, h: int) -> Image.Image:
    img  = Image.new("RGBA", (w, h), CLEAR)
    draw = ImageDraw.Draw(img)

    header_h = max(72, h // 14)   # e.g. 77px for 1080
    footer_h = max(60, h // 17)   # e.g. 63px for 1080
    border   = 4

    # ── 1. Outer green border frame ───────────────────────────────────────────
    draw.rectangle([0, 0, w - 1, h - 1], outline=GREEN, width=border)

    # ── 2. Top header bar ─────────────────────────────────────────────────────
    draw.rectangle([0, 0, w, header_h], fill=GREEN)

    # Subtle inner shadow at bottom of header
    for i in range(6):
        alpha = int(80 * (i / 6))
        draw.line([(0, header_h - 6 + i), (w, header_h - 6 + i)],
                  fill=(0, 0, 0, alpha))

    # Red dot (live indicator)
    pad    = max(28, w // 32)
    dot_r  = max(7, header_h // 9)
    dot_cx = pad + dot_r
    dot_cy = header_h // 2
    draw.ellipse(
        [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
        fill=RED
    )
    # Pulse ring around dot
    draw.ellipse(
        [dot_cx - dot_r - 4, dot_cy - dot_r - 4,
         dot_cx + dot_r + 4, dot_cy + dot_r + 4],
        outline=(244, 42, 65, 120), width=2
    )

    # Channel name "বৈশাখী টিভি" in Bengali
    logo_size  = max(22, header_h // 3)
    logo_font  = _font(FONT_BOLD, logo_size)
    logo_x     = dot_cx + dot_r + 12
    logo_y     = header_h // 2
    draw.text((logo_x, logo_y), "বৈশাখী টিভি", font=logo_font,
              fill=WHITE, anchor="lm")

    # "BOISHAKHI TV" secondary label on right
    sub_size = max(11, header_h // 6)
    sub_font = _font(FONT_LATIN, sub_size)
    sub_text = "BOISHAKHI TV"
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_font)
    sub_w    = sub_bbox[2] - sub_bbox[0]
    draw.text((w - sub_w - pad, header_h // 2), sub_text,
              font=sub_font, fill=WHITE_DIM, anchor="lm")

    # ── 3. Red accent stripe below header ─────────────────────────────────────
    draw.rectangle([0, header_h, w, header_h + 3], fill=RED)

    # ── 4. Top-right corner decorative triangle ───────────────────────────────
    tri = max(44, w // 18)
    draw.polygon(
        [(w - tri, border), (w - border, border), (w - border, border + tri)],
        fill=RED
    )
    # Small white notch inside triangle
    notch = tri // 3
    draw.polygon(
        [(w - notch, border + 2), (w - border - 2, border + 2),
         (w - border - 2, border + notch)],
        fill=(255, 255, 255, 60)
    )

    # ── 5. Footer bar ─────────────────────────────────────────────────────────
    draw.rectangle([0, h - footer_h, w, h], fill=GREEN)

    # Left red accent stripe in footer
    draw.rectangle([0, h - footer_h, 6, h], fill=RED)

    # Thin white separator line at top of footer
    draw.line([(0, h - footer_h), (w, h - footer_h)],
              fill=(255, 255, 255, 40), width=1)

    # "boishakhitv.com" on the right
    url_size = max(12, footer_h // 4)
    url_font = _font(FONT_LATIN, url_size)
    url_text = "boishakhitv.com"
    url_bbox = draw.textbbox((0, 0), url_text, font=url_font)
    url_w    = url_bbox[2] - url_bbox[0]
    draw.text(
        (w - url_w - pad, h - footer_h // 2),
        url_text, font=url_font, fill=WHITE_DIM, anchor="lm"
    )

    # Small red diamond in footer (left decorative element)
    dm_cx = pad + 12
    dm_cy = h - footer_h // 2
    dm_r  = max(5, footer_h // 8)
    draw.polygon(
        [(dm_cx, dm_cy - dm_r), (dm_cx + dm_r, dm_cy),
         (dm_cx, dm_cy + dm_r), (dm_cx - dm_r, dm_cy)],
        fill=RED
    )

    return img


if __name__ == "__main__":
    for name, (w, h) in SIZES.items():
        suffix = "" if name == "square" else f"_{name}"
        out    = ASSETS / f"boishakhi_template{suffix}.png"
        img    = make_template(w, h)
        img.save(out, format="PNG")
        size_kb = out.stat().st_size // 1024
        print(f"  {out.name}  {w}×{h}  {size_kb} KB")

    print("\nAll templates generated.")
