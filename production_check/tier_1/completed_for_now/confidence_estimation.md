# Production Concern: Confidence Estimation (Tier 1)

Focus: whether confidence values accurately represent evidence strength and uncertainty in backend outputs.

## Major Confidence Estimation Issues

1. **Confidence is derived from a fixed heuristic formula without calibration evidence** (`backend/services/claim_verifier/claim_verifier.py`)  
   `p_true` is computed from LLM-produced latent scores via a hand-tuned formula, but there is no demonstrated calibration loop against known outcomes, so numeric confidence can be systematically misleading.

2. **Model-generated scoring dimensions are trusted without consistency checks** (`backend/services/claim_verifier/claim_verifier.py`)  
   `support_strength`, `contradiction_strength`, `completeness`, and `source_quality` are accepted after type/range normalization only; contradictory or unstable scoring patterns can still become authoritative confidence outputs.

3. **Low-evidence fallback paths default to mid confidence (50)** (`backend/services/claim_verifier/claim_verifier.py`)  
   Missing RAG collection, empty retrieval, or unmatched rows return `unverified` with confidence `50`, which can overstate certainty for “insufficient evidence” states.

4. **No minimum evidence threshold gates high confidence verdicts** (`backend/services/claim_verifier/claim_verifier.py`)  
   Confidence can be high even with sparse sources because there is no hard backend rule tying maximum confidence to evidence depth/diversity.

## Important Confidence Estimation Gaps

5. **Cluster-level trust score is a plain mean of per-claim confidences** (`backend/services/save_result_to_db/save_result_to_db.py`)  
   Averaging treats all claims equally regardless of claim importance or evidence quality variance, so overall trust can look strong while critical claims are weakly supported.

6. **Trust score is persisted as final output without uncertainty metadata** (`backend/services/save_result_to_db/save_result_to_db.py`, `backend/db/models/hunt.py`)  
   Backend stores a single `trust_score` integer but not calibration quality, confidence band, or caveat signals, reducing interpretability of uncertainty for clients.

7. **Confidence normalization clamps invalid values instead of surfacing quality faults** (`backend/services/claim_verifier/claim_verifier.py`, `backend/services/save_result_to_db/save_result_to_db.py`)  
   Out-of-range or malformed confidence inputs are coerced into valid ranges, which hides upstream quality problems rather than flagging confidence estimation degradation.
