# ─────────────────────────────────────────────────────────────────
# CELL 6 – Full content + image-prompt generation
#
# For each top article, generates:
#   • headline / summary  • Facebook caption
#   • Instagram caption   • Twitter/X caption
#   • Hashtags            • Poster text (image overlay)
#   • SEO metadata        • AI image-generation prompt
# ─────────────────────────────────────────────────────────────────

_CONTENT_SYSTEM = (
    "You are an award-winning FIFA World Cup 2027 social-media editor. "
    "Write punchy, platform-optimised content. Respond only with valid JSON."
)

_STYLE_SUFFIX = (
    "professional sports editorial photography, FIFA World Cup 2027 branding, "
    "dynamic stadium lighting, packed crowd atmosphere, 8K ultra-detailed, "
    "sharp focus, photorealistic, high contrast, vivid colors, cinematic"
)

_NEGATIVE_PROMPT = (
    "text, watermark, logo, blurry, low quality, deformed, ugly, "
    "bad anatomy, duplicate, out of frame"
)


def _content_prompt(article):
    ent  = article.get("entities", {})
    return f"""Write complete social-media content for this football story.

Story:
  Title    : {article['title']}
  Source   : {article['source']}
  Summary  : {article.get('summary','N/A')[:250]}
  Category : {article.get('category','other')}
  Hook     : {article.get('why','N/A')}
  Teams    : {', '.join(ent.get('teams',[])  ) or 'N/A'}
  Players  : {', '.join(ent.get('players',[])) or 'N/A'}

Return ONLY a JSON object with EXACTLY these keys:
  "headline"          : punchy headline, max 12 words
  "summary"           : 2-3 factual engaging sentences
  "facebook_caption"  : professional Facebook post, 2-3 paragraphs
  "instagram_caption" : punchy IG caption with line breaks
  "twitter_caption"   : max 240 chars
  "hashtags"          : array of 8-12 hashtags (no # symbol)
  "poster_text"       : ultra-short headline for image overlay, max 7 words
  "image_prompt"      : 100-150 word visual prompt for Stable Diffusion XL
                        (no text/logos/watermarks in the image)
  "negative_prompt"   : what to avoid in the image
  "seo_keywords"      : array of 5-8 keyword phrases
  "meta_description"  : 150-char SEO meta description

No markdown. Valid JSON only."""


def generate_content(article):
    try:
        raw   = ask_ai(_content_prompt(article), system=_CONTENT_SYSTEM)
        clean = re.sub(r"```(?:json)?|```", "", raw).strip().strip("`")
        data  = json.loads(clean)
        article["headline"]          = data.get("headline",         article["title"])
        article["ai_summary"]        = data.get("summary",          article.get("summary",""))
        article["facebook_caption"]  = data.get("facebook_caption", "")
        article["instagram_caption"] = data.get("instagram_caption","")
        article["twitter_caption"]   = data.get("twitter_caption",  "")
        article["hashtags"]          = data.get("hashtags",         [])
        article["poster_text"]       = data.get("poster_text",      article["title"][:40])
        article["image_prompt"]      = data.get("image_prompt",     "") + ", " + _STYLE_SUFFIX
        article["negative_prompt"]   = data.get("negative_prompt",  _NEGATIVE_PROMPT)
        article["seo_keywords"]      = data.get("seo_keywords",     [])
        article["meta_description"]  = data.get("meta_description", "")
    except Exception as exc:
        print(f"    WARNING: content failed for '{article['title'][:40]}': {exc}")
        article.setdefault("headline",         article["title"])
        article.setdefault("ai_summary",       article.get("summary",""))
        article.setdefault("facebook_caption", "")
        article.setdefault("instagram_caption","")
        article.setdefault("twitter_caption",  "")
        article.setdefault("hashtags",         [])
        article.setdefault("poster_text",      article["title"][:40])
        article.setdefault("image_prompt",     "FIFA 2027 football, " + _STYLE_SUFFIX)
        article.setdefault("negative_prompt",  _NEGATIVE_PROMPT)
        article.setdefault("seo_keywords",     [])
        article.setdefault("meta_description", "")
    return article


# ── Run ────────────────────────────────────────────────────────────────────
print("Generating content and image prompts ...\n")
for idx, art in enumerate(top_articles, start=1):
    print(f"  [{idx}/{len(top_articles)}] {art['title'][:55]}")
    generate_content(art)
    time.sleep(0.5)

print(f"\nContent generation complete for {len(top_articles)} articles.")