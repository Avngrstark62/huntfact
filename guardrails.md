EDGE CASE HANDLING:

- Reaction videos:
  Carefully distinguish creator vs quoted speech

- Mixed languages:
  Translate everything to English before further steps

- No clear speaker separation:
  Use "unknown" but continue

- No valid claims:
  Return empty claims_by_creator array (NOT error)

- Noisy / broken transcript:
  Still attempt best-effort output, mark LOW_CONFIDENCE

QUALITY BAR:

- Do NOT over-extract claims
- Prefer fewer high-quality claims over many weak ones
