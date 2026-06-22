/**
 * services/aiService.js
 *
 * Core intelligence layer: takes raw English sports news, sends it to Groq
 * (llama-3.3-70b-versatile) via the Groq SDK, and returns a structured JSON
 * payload enforcing Bangladeshi demographic localisation + copyright safety.
 *
 * The system prompt is the single source of truth for LLM behaviour.
 * Nothing else in the codebase should encode these rules.
 */

const Groq = require('groq-sdk');

// ── System prompt ──────────────────────────────────────────────────────────────

const SYSTEM_PROMPT = `You are the Core Orchestrator AI for Boishakhi TV (বৈশাখী টিভি), a major Bangladeshi sports and news television channel.

## YOUR ROLE
Adapt raw sports news into highly engaging, localised Bangla content for social media posters.

## LOCALISATION RULES
- Write ALL text in proper Unicode Bangla (not transliteration).
- Use punchy, regional Bangladeshi sports journalism style — short, high-energy, emotionally resonant.
- Prioritise angles that matter to Bangladeshi viewers: FIFA World Cup, cricket, major transfers, Bangladesh national team news, popular European clubs.
- Headline: max 10 Bangla words. Make it a hook, not a summary.
- Subtext: 1-2 sentences max. Give quick context a reader needs to care.

## COPYRIGHT COMPLIANCE (MANDATORY)
- The image_generation_prompt MUST describe ABSTRACT or HIGHLY STYLISED artwork only.
- NEVER name, describe, or reference the likeness of any real athlete, club logo, or identifiable uniform.
- NEVER instruct the image AI to recreate real photographs or match scenes.
- SAFE examples: "cinematic neon-lit football stadium with motion-blurred ball trajectory", "abstract watercolour explosion of green and red sports energy".
- UNSAFE examples: "Messi kicking a ball", "a player in a red jersey", "Champions League final photo".

## OUTPUT CONTRACT
Return ONLY a single valid JSON object. No markdown fences. No prose. No comments.

{
  "copyright_audit": {
    "status": "APPROVED_SAFE_GEN",
    "risk_factor_notes": "<one sentence assessing the source content's copyright risk>"
  },
  "poster_content": {
    "headline_bangla": "<punchy Bangla headline, max 10 words>",
    "subtext_bangla": "<1-2 Bangla sentences giving quick context>"
  },
  "image_generation_prompt": "<detailed, abstract, copyright-safe art description — min 40 words, include dominant colours, mood, and style>",
  "negative_prompt": "real people, athlete faces, club logos, jersey numbers, text, watermark, blurry, low resolution, ugly"
}`;

// ── Main export ────────────────────────────────────────────────────────────────

/**
 * Orchestrate AI processing of raw sports news.
 *
 * @param {string} rawNewsText  - Raw English (or Bangla) sports news text
 * @returns {Promise<object>}   - Parsed JSON payload from LLM
 * @throws {Error}              - On API failure or unparseable response
 */
async function orchestrate(rawNewsText) {
  if (!process.env.AI_API_KEY) {
    throw new Error('AI_API_KEY not set in .env');
  }

  const groq = new Groq({ apiKey: process.env.AI_API_KEY });

  const completion = await groq.chat.completions.create({
    model:       process.env.AI_MODEL || 'llama-3.3-70b-versatile',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user',   content: `Process the following sports news:\n\n${rawNewsText.trim()}` },
    ],
    max_tokens:  1024,
    temperature: 0.65,
  });

  const raw   = completion.choices[0].message.content.trim();
  const clean = _stripCodeFences(raw);

  let payload;
  try {
    payload = JSON.parse(clean);
  } catch (_) {
    throw new Error(`LLM returned non-JSON. Preview: ${raw.slice(0, 300)}`);
  }

  _validatePayload(payload);
  return payload;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function _stripCodeFences(text) {
  return text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();
}

function _validatePayload(payload) {
  const required = [
    ['copyright_audit',              'object'],
    ['poster_content',               'object'],
    ['image_generation_prompt',      'string'],
    ['negative_prompt',              'string'],
  ];
  for (const [key, type] of required) {
    if (!payload[key] || typeof payload[key] !== type) {
      throw new Error(`AI payload missing or wrong type for key: "${key}"`);
    }
  }
  const textRequired = ['headline_bangla', 'subtext_bangla'];
  for (const key of textRequired) {
    if (!payload.poster_content[key]) {
      throw new Error(`poster_content.${key} is missing from AI response`);
    }
  }
}

module.exports = { orchestrate };
