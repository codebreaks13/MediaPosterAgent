# ─────────────────────────────────────────────────────────────────
# CELL 5 – Multi-dimension AI scoring
#
# Scores every article on 4 axes:
#   relevance_score  (0-100) – FIFA 2027 relevance
#   viral_score      (0-100) – social virality
#   breaking_score   (0-100) – time-sensitivity
#   engagement_score (0-100) – comment/share/reaction potential
#
# Also extracts: category, entities (teams, players, countries)
# ─────────────────────────────────────────────────────────────────

BATCH_SIZE = 15
_SCORE_SYSTEM = (
    "You are a FIFA World Cup 2027 social-media strategist. "
    "Respond only with valid JSON."
)
_W = dict(viral=0.35, relevance=0.30, breaking=0.20, engagement=0.15)


def _build_scoring_prompt(batch):
    lines = []
    for i, art in enumerate(batch, start=1):
        line = f"{i}. [{art['source']}] {art['title']}"
        if art.get("summary"):
            line += f"\n   {art['summary'][:150]}"
        lines.append(line)

    return f"""Score these football articles for a FIFA 2027 social-media pipeline.
Articles sourced from "FIFA Inside" (inside.fifa.com) are official FIFA content
covering rankings, analytics, transfers and governance – treat them as authoritative
and score their relevance_score at least 10 points higher than equivalent non-official
coverage of the same topic.

For EACH article return a JSON object with EXACTLY these fields:
  "index"           : article number (integer, 1-based)
  "relevance_score" : 0-100 (FIFA 2027 / World Cup relevance; +10 for FIFA Inside source)
  "viral_score"     : 0-100 (social viral potential)
  "breaking_score"  : 0-100 (how breaking / time-sensitive)
  "engagement_score": 0-100 (comment/share/reaction potential)
  "why"             : one sentence on top viral hook
  "category"        : transfer | injury | result | announcement | ranking |
                      squad | controversy | logistics | stadium | analytics | other
  "entities"        : object with keys teams[], players[], countries[], stage

Return ONLY a valid JSON array. No markdown. No extra text.

Articles:
{chr(10).join(lines)}"""


def _parse_batch(response_text, batch):
    clean = re.sub(r"```(?:json)?|```", "", response_text).strip().strip("`")
    try:
        scored_list = json.loads(clean)
    except json.JSONDecodeError as exc:
        print(f"  WARNING: JSON parse error ({exc}). Assigning default scores.")
        for art in batch:
            for k, v in [("relevance_score",0),("viral_score",0),("breaking_score",0),
                         ("engagement_score",0),("why",""),("category","other"),("entities",{})]:
                art.setdefault(k, v)
            art["rank_score"] = 0
        return batch

    lookup = {item["index"]: item for item in scored_list if "index" in item}
    for i, art in enumerate(batch, start=1):
        ai = lookup.get(i, {})
        art["relevance_score"]  = int(ai.get("relevance_score",  0))
        art["viral_score"]      = int(ai.get("viral_score",       0))
        art["breaking_score"]   = int(ai.get("breaking_score",    0))
        art["engagement_score"] = int(ai.get("engagement_score",  0))
        art["why"]              = ai.get("why",      "")
        art["category"]         = ai.get("category", "other").lower()
        art["entities"]         = ai.get("entities", {})
        base = (
            art["viral_score"]       * _W["viral"]
            + art["relevance_score"] * _W["relevance"]
            + art["breaking_score"]  * _W["breaking"]
            + art["engagement_score"]* _W["engagement"]
        )
        # FIFA Inside is the official source: +10 point priority boost
        if art.get("priority"):
            base += 10
        art["rank_score"] = int(min(base, 100))
    return batch


def score_articles(articles):
    """Score all articles in batches; return sorted by rank_score desc."""
    all_scored    = []
    n_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE

    for b in range(n_batches):
        batch = articles[b * BATCH_SIZE : (b+1) * BATCH_SIZE]
        print(f"  Scoring batch {b+1}/{n_batches} ({len(batch)} articles) ...")
        response  = ask_ai(_build_scoring_prompt(batch), system=_SCORE_SYSTEM)
        all_scored.extend(_parse_batch(response, batch))
        if b < n_batches - 1:
            time.sleep(1)

    all_scored.sort(key=lambda a: a.get("rank_score", 0), reverse=True)
    top = all_scored[0]
    print(f"\nTop story (rank={top['rank_score']}): {top['title'][:60]}")
    return all_scored


# ── Run ────────────────────────────────────────────────────────────────────
print("Scoring articles ...\n")
scored_articles = score_articles(unique_articles)
top_articles = [
    a for a in scored_articles
    if a.get("viral_score", 0) >= MIN_VIRAL_SCORE
][:MAX_ARTICLES]
print(f"\n{len(top_articles)} articles passed the viral score threshold.")