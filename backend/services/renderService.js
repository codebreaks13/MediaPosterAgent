/**
 * services/renderService.js
 *
 * Compositing engine using Puppeteer (headless Chrome).
 *
 * Layer stack (bottom → top):
 *   1. AI-generated background image  (base64 data URI into CSS background)
 *   2. Dark gradient overlay           (CSS gradient, readability)
 *   3. Boishakhi brand template PNG    (transparent overlay, from ./assets/)
 *   4. Bengali typography              (HindSiliguri TTF via @font-face)
 *
 * Text is rendered BY THE BROWSER ENGINE — meaning correct Unicode shaping,
 * ligatures, and script directionality for Bangla are handled automatically.
 * No text is ever passed into the image generation pipeline.
 */

const puppeteer = require('puppeteer');
const fs        = require('path').resolve;
const path      = require('path');
const fss       = require('fs');

const ASSETS_DIR = path.join(__dirname, '../assets');
const TEMP_DIR   = path.join(__dirname, '../temp');

// Poster canvas dimensions per format
const SIZES = {
  square:    { w: 1080, h: 1080 },
  portrait:  { w: 1080, h: 1350 },
  landscape: { w: 1080, h:  566 },
};

// ── Main exports ───────────────────────────────────────────────────────────────

/**
 * Render a single poster.
 *
 * @param {object} posterContent      - { headline_bangla, subtext_bangla }
 * @param {string|null} bgImagePath   - Absolute path to background PNG
 * @param {string} [size]             - "square" | "portrait" | "landscape"
 * @param {string|null} [outputPath]  - Override output file path
 * @returns {Promise<string>}         - Absolute path to rendered poster PNG
 */
async function renderPoster(posterContent, bgImagePath, size = 'square', outputPath = null) {
  const { w, h } = SIZES[size] || SIZES.square;

  const bgDataUri       = _fileToDataUri(bgImagePath);
  const templateDataUri = _fileToDataUri(path.join(ASSETS_DIR, 'boishakhi_template.png'));
  const fontDataUri     = _fileToDataUri(path.join(ASSETS_DIR, 'hind_siliguri.ttf'));

  const html = _buildHtml(posterContent, bgDataUri, templateDataUri, fontDataUri, w, h);

  if (!outputPath) {
    outputPath = path.join(TEMP_DIR, `poster_${Date.now()}_${size}.png`);
  }

  const browser = await puppeteer.launch({
    headless: 'new',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--font-render-hinting=none',
    ],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: w, height: h, deviceScaleFactor: 1 });
    await page.setContent(html, { waitUntil: 'networkidle0' });

    // Block until @font-face is loaded so Bangla glyphs render correctly
    await page.evaluate(() => document.fonts.ready);

    await page.screenshot({ path: outputPath, type: 'png', clip: { x: 0, y: 0, width: w, height: h } });

    console.log(`[renderService] Poster saved → ${outputPath}`);
    return outputPath;
  } finally {
    await browser.close();
  }
}

/**
 * Render all three format variants (square, portrait, landscape).
 *
 * @param {object} posterContent  - { headline_bangla, subtext_bangla }
 * @param {string|null} bgPath    - Background image path
 * @returns {Promise<object>}     - { square, portrait, landscape } → paths or null
 */
async function renderAllFormats(posterContent, bgPath) {
  const results = {};
  for (const size of Object.keys(SIZES)) {
    try {
      results[size] = await renderPoster(posterContent, bgPath, size);
    } catch (err) {
      console.error(`[renderService] Render failed  size=${size}: ${err.message}`);
      results[size] = null;
    }
  }
  return results;
}

// ── HTML template builder ──────────────────────────────────────────────────────

function _buildHtml(posterContent, bgDataUri, templateDataUri, fontDataUri, w, h) {
  const { headline_bangla, subtext_bangla } = posterContent;

  // Responsive font sizes relative to canvas width
  const headlinePx   = Math.max(48, Math.floor(w / 13));
  const subtextPx    = Math.max(24, Math.floor(w / 32));
  const badgePx      = Math.max(18, Math.floor(w / 44));
  const brandPx      = Math.max(16, Math.floor(w / 46));
  const padding      = Math.max(48, Math.floor(w / 16));
  const badgeMargin  = Math.max(18, Math.floor(h / 55));
  const accentMargin = Math.max(16, Math.floor(h / 55));
  const headlineGap  = Math.max(16, Math.floor(h / 60));
  const footerGap    = Math.max(12, Math.floor(h / 80));

  const bgCss = bgDataUri
    ? `url("${bgDataUri}") center/cover no-repeat`
    : 'linear-gradient(160deg,#071428 0%,#0d2460 55%,#1a1a2e 100%)';

  const fontFaceRule = fontDataUri
    ? `@font-face {
        font-family: 'HindSiliguri';
        src: url('${fontDataUri}') format('truetype');
        font-weight: 400 900;
        font-display: block;
      }`
    : '';

  // Escape HTML entities to prevent XSS through AI-generated text
  const safeHeadline = _escapeHtml(headline_bangla || '');
  const safeSubtext  = _escapeHtml(subtext_bangla  || '');

  return `<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<style>
  ${fontFaceRule}

  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    width: ${w}px;
    height: ${h}px;
    overflow: hidden;
    background: #000;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Layer 1: AI-generated background ───────────────────────── */
  .l-bg {
    position: absolute;
    inset: 0;
    background: ${bgCss};
    filter: brightness(48%);
    z-index: 1;
  }

  /* ── Layer 2: Bottom-heavy gradient for text legibility ──────── */
  .l-gradient {
    position: absolute;
    inset: 0;
    background: linear-gradient(
      to top,
      rgba(0, 0, 0, 0.93)  0%,
      rgba(0, 0, 0, 0.60)  35%,
      rgba(0, 0, 0, 0.15)  70%,
      rgba(0, 0, 0, 0)    100%
    );
    z-index: 2;
  }

  /* ── Layer 3: Brand template (transparent PNG) ───────────────── */
  .l-template {
    position: absolute;
    inset: 0;
    background: ${templateDataUri ? `url("${templateDataUri}") center/cover no-repeat` : 'none'};
    z-index: 3;
    pointer-events: none;
  }

  /* ── Layer 4: Typography ─────────────────────────────────────── */
  .l-content {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: ${padding}px;
    z-index: 4;
    font-family: 'HindSiliguri', 'Noto Sans Bengali', 'SolaimanLipi', sans-serif;
  }

  /* Breaking news badge */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    background: #e50000;
    color: #fff;
    font-size: ${badgePx}px;
    font-weight: 900;
    letter-spacing: 1px;
    padding: 8px 20px 8px 16px;
    border-radius: 4px;
    margin-bottom: ${badgeMargin}px;
    width: fit-content;
    text-transform: uppercase;
  }
  .badge-dot {
    width: ${Math.max(8, Math.floor(badgePx * 0.55))}px;
    height: ${Math.max(8, Math.floor(badgePx * 0.55))}px;
    background: #fff;
    border-radius: 50%;
    flex-shrink: 0;
  }

  /* Red accent rule */
  .accent {
    width: ${Math.max(70, Math.floor(w / 12))}px;
    height: 5px;
    background: #e50000;
    border-radius: 3px;
    margin-bottom: ${accentMargin}px;
  }

  /* Main Bengali headline */
  .headline {
    color: #ffffff;
    font-size: ${headlinePx}px;
    font-weight: 900;
    line-height: 1.22;
    margin-bottom: ${headlineGap}px;
    max-width: ${Math.floor(w * 0.90)}px;
    text-shadow:
      2px 2px 14px rgba(0, 0, 0, 0.98),
      0   0   40px rgba(0, 0, 0, 0.75);
    word-break: break-word;
  }

  /* Bengali sub-headline / context */
  .subtext {
    color: #e8e8e8;
    font-size: ${subtextPx}px;
    font-weight: 400;
    line-height: 1.65;
    max-width: ${Math.floor(w * 0.88)}px;
    text-shadow: 1px 1px 8px rgba(0, 0, 0, 0.98);
    margin-bottom: ${Math.max(22, Math.floor(h / 48))}px;
    word-break: break-word;
  }

  /* Footer bar */
  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid rgba(255, 255, 255, 0.15);
    padding-top: ${footerGap}px;
  }
  .brand {
    color: #f5c842;
    font-size: ${brandPx}px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
  }
  .tagline {
    color: rgba(255, 255, 255, 0.50);
    font-size: ${Math.max(13, Math.floor(w / 58))}px;
    font-weight: 300;
  }
</style>
</head>
<body>
  <div class="l-bg"></div>
  <div class="l-gradient"></div>
  <div class="l-template"></div>
  <div class="l-content">
    <div class="badge"><span class="badge-dot"></span>ব্রেকিং নিউজ</div>
    <div class="accent"></div>
    <div class="headline">${safeHeadline}</div>
    ${safeSubtext ? `<div class="subtext">${safeSubtext}</div>` : ''}
    <div class="footer">
      <span class="brand">বৈশাখী টিভি</span>
      <span class="tagline">boishakhitv.com</span>
    </div>
  </div>
</body>
</html>`;
}

// ── Utilities ──────────────────────────────────────────────────────────────────

function _fileToDataUri(filePath) {
  if (!filePath) return '';
  try {
    if (!fss.existsSync(filePath)) return '';
    const data = fss.readFileSync(filePath);
    const ext  = path.extname(filePath).toLowerCase();
    const mime = ext === '.png' ? 'image/png' : (ext === '.ttf' ? 'font/truetype' : 'image/jpeg');
    return `data:${mime};base64,${data.toString('base64')}`;
  } catch (_) {
    return '';
  }
}

function _escapeHtml(str) {
  return str
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}

module.exports = { renderPoster, renderAllFormats };
