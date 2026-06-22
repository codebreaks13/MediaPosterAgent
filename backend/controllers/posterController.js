/**
 * controllers/posterController.js
 *
 * POST /api/generate-poster
 *
 * Body (JSON):
 *   news_text     {string}   Raw sports news text (required, min 10 chars)
 *   size          {string}   "square" | "portrait" | "landscape"  (default: "square")
 *   all_formats   {boolean}  If true, renders all three size variants (default: false)
 *
 * Response (JSON):
 *   copyright_audit  {object}
 *   poster_content   {object}  { headline_bangla, subtext_bangla }
 *   poster_path      {string}  Path to generated PNG  (single-format mode)
 *   posters          {object}  { square, portrait, landscape }  (all_formats mode)
 */

const express = require('express');
const router  = express.Router();

const { orchestrate }        = require('../services/aiService');
const { generateBackground } = require('../services/imageService');
const { renderPoster, renderAllFormats } = require('../services/renderService');

const VALID_SIZES = new Set(['square', 'portrait', 'landscape']);

// ── Image API rate limiter ─────────────────────────────────────────────────────
// Only the paid image-generation call is gated. LLM + Puppeteer render run freely.
// When the cooldown is active bgImagePath stays null and renderService falls back
// to the CSS dark-gradient — the poster still generates, just without a paid bg.
// IMAGE_RATE_LIMIT_MINUTES in .env overrides the default of 60.
const RATE_LIMIT_MS = (parseInt(process.env.IMAGE_RATE_LIMIT_MINUTES, 10) || 60) * 60 * 1000;
let _lastImageGenAt = 0;

function _imageAllowed()     { return (Date.now() - _lastImageGenAt) >= RATE_LIMIT_MS; }
function _minutesUntilNext() { return Math.ceil((RATE_LIMIT_MS - (Date.now() - _lastImageGenAt)) / 60_000); }

router.post('/generate-poster', async (req, res) => {
  const { news_text, size = 'square', all_formats = false } = req.body;

  // ── Input validation ──────────────────────────────────────────────────────
  if (!news_text || typeof news_text !== 'string' || news_text.trim().length < 10) {
    return res.status(400).json({
      error: 'INVALID_INPUT',
      detail: '"news_text" is required and must be at least 10 characters.',
    });
  }
  if (!VALID_SIZES.has(size)) {
    return res.status(400).json({
      error: 'INVALID_SIZE',
      detail: `"size" must be one of: ${[...VALID_SIZES].join(', ')}`,
    });
  }

  const start = Date.now();
  console.log(`\n[posterController] ── New request ──`);
  console.log(`  size=${size}  all_formats=${all_formats}`);
  console.log(`  news_text: "${news_text.trim().slice(0, 80)}..."`);

  // ── Step 1: AI orchestration ──────────────────────────────────────────────
  let aiPayload;
  try {
    aiPayload = await orchestrate(news_text.trim());
    console.log(`[posterController] ✓ AI orchestration  (${Date.now() - start}ms)`);
  } catch (err) {
    console.error(`[posterController] ✗ AI service failed: ${err.message}`);
    return res.status(502).json({
      error:  'AI_SERVICE_FAILURE',
      detail: err.message,
    });
  }

  const { poster_content, image_generation_prompt, negative_prompt, copyright_audit } = aiPayload;

  // ── Step 2: Background image generation (rate-limited) ──────────────────
  let bgImagePath = null;
  if (!_imageAllowed()) {
    console.warn(`[posterController] ⏱ Image rate limit active — ${_minutesUntilNext()} min(s) remaining. Using gradient fallback.`);
  } else {
    try {
      bgImagePath = await generateBackground(
        image_generation_prompt,
        negative_prompt || '',
        size,
      );
      _lastImageGenAt = Date.now();
      console.log(`[posterController] ✓ Background image  (${Date.now() - start}ms)  → ${bgImagePath}`);
    } catch (err) {
      console.warn(`[posterController] ⚠ Image generation failed: ${err.message} — using gradient fallback`);
    }
  }

  // ── Step 3: Poster rendering ──────────────────────────────────────────────
  try {
    if (all_formats) {
      const posters = await renderAllFormats(poster_content, bgImagePath);
      console.log(`[posterController] ✓ All formats rendered  (${Date.now() - start}ms)`);
      return res.json({ copyright_audit, poster_content, posters });
    } else {
      const posterPath = await renderPoster(poster_content, bgImagePath, size);
      console.log(`[posterController] ✓ Poster rendered  (${Date.now() - start}ms)  → ${posterPath}`);
      return res.json({ copyright_audit, poster_content, poster_path: posterPath });
    }
  } catch (err) {
    console.error(`[posterController] ✗ Render failed: ${err.message}`);
    return res.status(500).json({
      error:  'RENDER_FAILURE',
      detail: err.message,
    });
  }
});

module.exports = router;
