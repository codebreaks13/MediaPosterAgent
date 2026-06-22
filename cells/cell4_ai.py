# ─────────────────────────────────────────────────────────────────
# CELL 4 – Provider-agnostic AI client
#
# Public API:  ask_ai(prompt, system=None) -> str
# Supports:    groq | claude | gemini
# Switch by changing AI_PROVIDER in .env, then re-running Cell 1.
# ─────────────────────────────────────────────────────────────────


def ask_ai(prompt, system=None, max_tokens=2048):
    """Route to the correct AI backend based on AI_PROVIDER."""
    if AI_PROVIDER == "groq":
        return _ask_groq(prompt, system, max_tokens)
    elif AI_PROVIDER == "claude":
        return _ask_claude(prompt, system, max_tokens)
    elif AI_PROVIDER == "gemini":
        return _ask_gemini(prompt, system, max_tokens)
    else:
        raise ValueError(f"Unknown AI_PROVIDER='{AI_PROVIDER}'")


def _ask_groq(prompt, system, max_tokens):
    from groq import Groq
    client   = Groq(api_key=AI_API_KEY)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=AI_MODEL, messages=messages,
        max_tokens=max_tokens, temperature=0.7,
    )
    return resp.choices[0].message.content


def _ask_claude(prompt, system, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=AI_API_KEY)
    kwargs = dict(model=AI_MODEL, max_tokens=max_tokens,
                  messages=[{"role": "user", "content": prompt}])
    if system:
        kwargs["system"] = system
    msg = client.messages.create(**kwargs)
    return msg.content[0].text


def _ask_gemini(prompt, system, max_tokens):
    import google.generativeai as genai
    genai.configure(api_key=AI_API_KEY)
    full = f"{system}\n\n{prompt}" if system else prompt
    model = genai.GenerativeModel(AI_MODEL)
    resp  = model.generate_content(
        full, generation_config={"max_output_tokens": max_tokens}
    )
    return resp.text


# ── Quick sanity check ─────────────────────────────────────────────────────
print("Testing AI connection ...")
test = ask_ai("Reply with exactly: AI client is working!")
print(f"Response: {test.strip()}")