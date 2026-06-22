import base64
import os
import requests
from html2image import Html2Image

OUTPUT_DIR = "/home/mahir/Desktop/News_Agent-main"
OUTPUT_FILE = "fifa_poster.png"

# --- Content ---
BACKGROUND_IMAGE_URL = "https://images.unsplash.com/photo-1540747913346-19e32dc3e97e?w=1080&q=80"
BADGE_TEXT = "LIVE UPDATE"
HEADLINE = "বেলজিয়াম বনাম মিশর"
SUMMARY = "ফিফা বিশ্বকাপ বাছাইপর্বে বেলজিয়াম ২-১ গোলে মিশরকে পরাজিত করেছে। রোমেলু লুকাকু দুটি গোল করেন।"

def fetch_image_as_data_uri(url: str) -> str:
    print(f"Downloading background image...")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    mime = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    b64 = base64.b64encode(resp.content).decode()
    return f"data:{mime};base64,{b64}"

HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }}

  body {{
    width: 1080px;
    height: 1080px;
    overflow: hidden;
    background: #000;
    font-family: sans-serif;
  }}

  .canvas {{
    position: relative;
    width: 1080px;
    height: 1080px;
    overflow: hidden;
  }}

  .bg {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: brightness(45%);
    z-index: 0;
    display: block;
  }}

  /* Gradient overlay for extra text contrast at the bottom */
  .gradient-overlay {{
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 60%;
    background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
    z-index: 1;
  }}

  .content {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: 60px;
    z-index: 2;
  }}

  .badge {{
    display: inline-block;
    background-color: #e50000;
    color: #ffffff;
    font-size: 28px;
    font-weight: 900;
    letter-spacing: 3px;
    text-transform: uppercase;
    padding: 10px 22px;
    border-radius: 6px;
    margin-bottom: 28px;
    width: fit-content;
    text-shadow: none;
  }}

  /* Pulsing dot before badge text */
  .badge::before {{
    content: "⬤ ";
    font-size: 18px;
  }}

  h1 {{
    color: #ffffff;
    font-size: 88px;
    font-weight: 900;
    line-height: 1.1;
    margin-bottom: 28px;
    text-shadow:
      2px 2px 8px rgba(0,0,0,0.9),
      0 0 40px rgba(0,0,0,0.7);
  }}

  p {{
    color: #e0e0e0;
    font-size: 38px;
    font-weight: 400;
    line-height: 1.55;
    max-width: 900px;
    text-shadow:
      1px 1px 6px rgba(0,0,0,0.95),
      0 0 20px rgba(0,0,0,0.8);
  }}

  /* Thin red accent line above content */
  .accent-line {{
    width: 90px;
    height: 6px;
    background: #e50000;
    border-radius: 3px;
    margin-bottom: 28px;
  }}
</style>
</head>
<body>
<div class="canvas">
  <img class="bg" src="{{BG_DATA_URI}}" />
  <div class="gradient-overlay"></div>
  <div class="content">
    <div class="badge">{BADGE_TEXT}</div>
    <div class="accent-line"></div>
    <h1>{HEADLINE}</h1>
    <p>{SUMMARY}</p>
  </div>
</div>
</body>
</html>"""

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    bg_data_uri = fetch_image_as_data_uri(BACKGROUND_IMAGE_URL)
    final_html = HTML.replace("{BG_DATA_URI}", bg_data_uri)

    hti = Html2Image(
        output_path=OUTPUT_DIR,
        browser_executable="/usr/bin/google-chrome",
        custom_flags=[
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-software-rasterizer",
        ],
    )
    # Chrome 112+ dropped the old --headless flag; force the new mode
    hti.browser.use_new_headless = True

    hti.screenshot(
        html_str=final_html,
        save_as=OUTPUT_FILE,
        size=(1080, 1080),
    )

    full_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    if os.path.exists(full_path):
        size_kb = os.path.getsize(full_path) // 1024
        print(f"Poster saved: {full_path}  ({size_kb} KB)")
    else:
        print("ERROR: file was not created. Check Chrome/Chromium is installed.")

if __name__ == "__main__":
    main()
