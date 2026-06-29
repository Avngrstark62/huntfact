# Production Concern: Source Attribution (Tier 1)

Focus: whether backend outputs let users reliably trace each claim verdict to the exact supporting evidence.

## Major Source Attribution Issues

1. **Attribution is URL-only, without evidence span/chunk references** (`backend/services/claim_verifier/claim_verifier.py`)  
   Final rows keep `sources` as URL lists only, so users cannot see which exact quoted passage or chunk supported/contradicted a claim.

2. **No backend check that explanation text is grounded in listed sources** (`backend/services/claim_verifier/claim_verifier.py`)  
   The model is instructed to cite evidence, but there is no post-validation linking explanation statements to the returned source URLs, allowing plausible but weakly grounded attribution.

3. **Source identity can collapse when multiple pages share the same URL** (`backend/services/claim_verifier/claim_verifier.py`)  
   Deduplication key `(url, content)` plus URL-only output means distinct evidence contexts on one domain/page variant are not transparently represented to users.

4. **Missing/empty source metadata is tolerated and stripped** (`backend/services/rag_storage/rag_storage.py`, `backend/services/claim_verifier/claim_verifier.py`)  
   When title/query metadata is absent, flow still proceeds with bare URLs, reducing attribution quality and making evidence provenance harder to audit.

## Important Source Attribution Gaps

5. **Persisted hunt result has no explicit citation schema version** (`backend/services/save_result_to_db/save_result_to_db.py`, `backend/schemas.py`)  
   `result` is stored as raw JSON string, so attribution structure can drift over time without a versioned contract for clients.

6. **No source-level credibility metadata is surfaced with claim rows** (`backend/services/web_scraper/web_scraper.py`, `backend/services/rag_storage/rag_storage.py`, `backend/services/claim_verifier/claim_verifier.py`)  
   Backend tracks title/query/url but does not expose provenance signals (publisher/domain type/retrieval distance) in final output, limiting user ability to judge citation strength.

7. **No minimum citation coverage rule per claim before non-unverified verdicts** (`backend/services/claim_verifier/claim_verifier.py`)  
   Claims can receive strong verdict labels with sparse citations because there is no hard attribution sufficiency gate (for example, minimum number/diversity of sources).
