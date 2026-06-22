/**
 * services/imageService.js
 *
 * Asset layer: takes an image_generation_prompt and produces a background PNG
 * saved to the local /temp directory.
 *
 * Active backend is controlled by IMAGE_BACKEND in .env:
 *   mock        – dark gradient placeholder, no API required (default)
 *   gemini      – Google Imagen 4 via @google/generative-ai
 *   stability   – Stability AI SD3 via REST
 *
 * Structured for easy extension to Higgsfield / Nano Banana / Replicate.
 */

const axios   = require('axios');
const fs      = require('fs');
const path    = require('path');

const TEMP_DIR = path.join(__dirname, '../temp');

const DIMENSIONS = {
  square:    { w: 1080, h: 1080 },
  portrait:  { w: 1080, h: 1350 },
  landscape: { w: 1920, h: 1080 },
};

// ── Main export ────────────────────────────────────────────────────────────────

/**
 * Generate a background image and save it to /temp.
 *
 * @param {string} prompt           - Positive image prompt
 * @param {string} [negativePrompt] - Negative prompt
 * @param {string} [size]           - "square" | "portrait" | "landscape"
 * @returns {Promise<string>}       - Absolute path to saved PNG
 */
async function generateBackground(prompt, negativePrompt = '', size = 'square') {
  const backend = (process.env.IMAGE_BACKEND || 'mock').toLowerCase();

  console.log(`[imageService] backend=${backend}  size=${size}`);

  switch (backend) {
    case 'pollinations':
      return _pollinations(prompt, size);
    case 'gemini':
      return _gemini(prompt, size);
    case 'stability':
      return _stability(prompt, negativePrompt, size);
    case 'higgsfield':
    case 'nanobanana':
      return _genericRestBackend(prompt, negativePrompt, size, backend);
    default:
      return _mock(prompt, size);
  }
}

// ── Pollinations.ai backend (free, no API key) ────────────────────────────────

async function _pollinations(prompt, size) {
  const { w, h } = DIMENSIONS[size] || DIMENSIONS.square;
  const encoded   = encodeURIComponent(prompt.slice(0, 600));
  const seed      = Math.floor(Date.now() / 1000) % (2 ** 31);
  const url       = `https://image.pollinations.ai/prompt/${encoded}?width=${w}&height=${h}&seed=${seed}&nologo=true&enhance=true`;

  console.log(`[imageService] Pollinations request  ${w}x${h}`);
  const resp    = await axios.get(url, { responseType: 'arraybuffer', timeout: 120_000 });
  const outPath = path.join(TEMP_DIR, `pollinations_${Date.now()}.png`);
  fs.writeFileSync(outPath, Buffer.from(resp.data));
  console.log(`[imageService] Pollinations image saved → ${outPath}`);
  return outPath;
}

// ── Mock backend ───────────────────────────────────────────────────────────────

async function _mock(_prompt, size) {
  const { w, h } = DIMENSIONS[size] || DIMENSIONS.square;
  const outPath  = path.join(TEMP_DIR, `mock_${Date.now()}.png`);

  // Minimal valid PNG (1×1 dark pixel) as last-resort fallback
  const PNG_HEADER  = Buffer.from('89504e470d0a1a0a', 'hex');
  const PNG_IHDR    = _buildIHDR(1, 1);
  const PNG_IDAT    = _buildIDAT_1x1([10, 25, 60]);
  const PNG_IEND    = Buffer.from('0000000049454e44ae426082', 'hex');
  const miniPng     = Buffer.concat([PNG_HEADER, PNG_IHDR, PNG_IDAT, PNG_IEND]);

  // Try to paint a proper gradient using the Puppeteer instance we already have
  // available; if this module is called before Puppeteer is ready, fall back to mini PNG.
  try {
    const puppeteer = require('puppeteer');
    const browser   = await puppeteer.launch({
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    });
    const page = await browser.newPage();
    await page.setViewport({ width: w, height: h });
    await page.setContent(`
      <!DOCTYPE html><html><head><style>
        body { margin:0; width:${w}px; height:${h}px;
               background: linear-gradient(160deg,#071428 0%,#0d2460 55%,#1a1a2e 100%); }
      </style></head><body></body></html>
    `);
    await page.screenshot({ path: outPath, type: 'png', clip: { x: 0, y: 0, width: w, height: h } });
    await browser.close();
  } catch (_) {
    fs.writeFileSync(outPath, miniPng);
  }

  console.log(`[imageService] Mock image saved → ${outPath}`);
  return outPath;
}

// ── Gemini / Imagen 4 backend ──────────────────────────────────────────────────

async function _gemini(prompt, size) {
  if (!process.env.GEMINI_API_KEY) throw new Error('GEMINI_API_KEY not set');

  const { w, h } = DIMENSIONS[size] || DIMENSIONS.square;
  const ratio    = w === h ? '1:1' : (h > w ? '9:16' : '16:9');

  // Imagen 4 REST endpoint (v1beta)
  const url = `https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict?key=${process.env.GEMINI_API_KEY}`;

  const body = {
    instances:  [{ prompt }],
    parameters: { sampleCount: 1, aspectRatio: ratio, outputMimeType: 'image/png' },
  };

  const resp = await axios.post(url, body, {
    headers: { 'Content-Type': 'application/json' },
    timeout: 120_000,
  });

  const b64 = resp.data?.predictions?.[0]?.bytesBase64Encoded;
  if (!b64) throw new Error('Gemini returned no image bytes');

  const outPath = path.join(TEMP_DIR, `gemini_${Date.now()}.png`);
  fs.writeFileSync(outPath, Buffer.from(b64, 'base64'));
  console.log(`[imageService] Gemini image saved → ${outPath}`);
  return outPath;
}

// ── Stability AI SD3 backend ───────────────────────────────────────────────────

async function _stability(prompt, negativePrompt, size) {
  if (!process.env.STABILITY_API_KEY) throw new Error('STABILITY_API_KEY not set');

  const { w, h } = DIMENSIONS[size] || DIMENSIONS.square;

  const FormData = require('form-data');
  const form     = new FormData();
  form.append('prompt',          prompt);
  form.append('negative_prompt', negativePrompt);
  form.append('width',           String(w));
  form.append('height',          String(h));
  form.append('output_format',   'png');

  const resp = await axios.post(
    'https://api.stability.ai/v2beta/stable-image/generate/sd3',
    form,
    {
      headers: {
        ...form.getHeaders(),
        authorization: `Bearer ${process.env.STABILITY_API_KEY}`,
        accept:        'image/*',
      },
      responseType: 'arraybuffer',
      timeout:      120_000,
    }
  );

  const outPath = path.join(TEMP_DIR, `stability_${Date.now()}.png`);
  fs.writeFileSync(outPath, Buffer.from(resp.data));
  console.log(`[imageService] Stability image saved → ${outPath}`);
  return outPath;
}

// ── Generic REST stub (Higgsfield / Nano Banana / future backends) ────────────
// Replace endpoint + auth headers + body shape when onboarding a new provider.

async function _genericRestBackend(prompt, negativePrompt, size, backendName) {
  const endpointMap = {
    higgsfield: process.env.HIGGSFIELD_API_URL  || 'https://api.higgsfield.ai/v1/generate',
    nanobanana: process.env.NANOBANANA_API_URL  || 'https://api.nanobanana.ai/v1/generate',
  };
  const keyMap = {
    higgsfield: process.env.HIGGSFIELD_API_KEY,
    nanobanana: process.env.NANOBANANA_API_KEY,
  };

  const endpoint = endpointMap[backendName];
  const apiKey   = keyMap[backendName];
  if (!apiKey) throw new Error(`${backendName.toUpperCase()}_API_KEY not set`);

  const { w, h } = DIMENSIONS[size] || DIMENSIONS.square;

  const resp = await axios.post(
    endpoint,
    { prompt, negative_prompt: negativePrompt, width: w, height: h, output_format: 'png' },
    {
      headers:      { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      responseType: 'arraybuffer',
      timeout:      120_000,
    }
  );

  const outPath = path.join(TEMP_DIR, `${backendName}_${Date.now()}.png`);
  fs.writeFileSync(outPath, Buffer.from(resp.data));
  return outPath;
}

// ── Minimal PNG helpers (for ultra-fallback mock only) ────────────────────────

function _buildIHDR(w, h) {
  const data = Buffer.alloc(25);
  data.writeUInt32BE(13, 0);
  data.write('IHDR', 4);
  data.writeUInt32BE(w, 8);
  data.writeUInt32BE(h, 12);
  data[16] = 8; data[17] = 2; // 8-bit RGB
  const crc = require('zlib').crc32(data.slice(4, 21));
  data.writeInt32BE(crc, 21);
  return data;
}

function _buildIDAT_1x1(rgb) {
  const raw  = Buffer.from([0, ...rgb]);
  const comp = require('zlib').deflateSync(raw);
  const out  = Buffer.alloc(comp.length + 12);
  out.writeUInt32BE(comp.length, 0);
  out.write('IDAT', 4);
  comp.copy(out, 8);
  const crc = require('zlib').crc32(out.slice(4, 8 + comp.length));
  out.writeInt32BE(crc, 8 + comp.length);
  return out;
}

module.exports = { generateBackground };
