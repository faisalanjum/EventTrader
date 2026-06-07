# Embedding reuse for the dedup-surface layer · INGESTION-PHASE reference

Supports **`CombinedPlan.md` §5.7 `[INGESTION-DESIGN]` layer 2 (dedup surface)** +
the **`merge_judge`** seam. The embedding/vector infrastructure for semantic
near-duplicate detection **already exists — do NOT reinvent it**; add only a
driver-side vector surface. (Reference; NOT a Phase-1-harness build item.)

## VERIFIED 2026-05-30 (Neo4j `SHOW VECTOR INDEXES` + file checks)

Existing online vector indexes — all **`text-embedding-3-large`, 3072 dims, COSINE**, HNSW (m=16, ef_construction=100), quantized:

| index | label.property |
|---|---|
| `news_vector_index` | `News.embedding` |
| `qaexchange_vector_idx` | `QAExchange.embedding` |
| `risk_classification_vector` | `RiskClassification.embedding` |

Coverage (**as reported by investigation — re-count before relying**): News ~348,563/348,670 · Q&A ~170,328/170,654 · RiskClassification 39,821/39,821.

Reusable code (verified present):
- `neograph/mixins/embedding.py` — embedding write/read mixin (3072 dims confirmed)
- `openai_local/openai_parallel_embeddings.py` — parallel embedding generation
- `.claude/skills/earnings-orchestrator/scripts/generate_embedding.py` — single-embed helper
- `.claude/skills/earnings-orchestrator/scripts/find_similar_news.py` / `find_similar_qa.py` — **the vector-search query pattern to copy for the driver search**

## CAVEAT (verified): NO `Driver`/`DriverConcept` vector index exists yet
`SHOW VECTOR INDEXES` returns ONLY the 3 above. Reuse the stack, but **add a driver-side surface.**

## The driver dedup-surface (layer 2) — minimal add
1. **New index:** a `Driver`/`DriverConcept` vector index on a `.embedding` property — same config (`text-embedding-3-large`, 3072, COSINE).
2. **Embed the MEANING, not just the name:** `definition + aliases + a few sample_evidence snippets` (weight definition/evidence — a name alone won't catch `chip_shortage` ≈ `component_supply_constraint`). Embed once at create; **cache** (re-embed only when definition/aliases change).
3. **Flow** (matches `[INGESTION-DESIGN]` layer 2):
   ```
   new candidate driver → embed its text → vector-search the Driver index (top-K, cosine >= threshold)
   → SURFACE near-dups as merge CANDIDATES → cached merge_judge decides → NEVER auto-merge on score
   ```
4. **PIT (critical):** the vector search MUST be PIT-filtered — `WHERE d.registry_visible_at <= run.pit_cutoff` — so a historical/backfill run never "discovers" a driver coined in its future (same rule as the registry-catalog filter). An unfiltered search leaks future drivers and fake-inflates dedup.
5. **Billing:** embeddings are OpenAI `text-embedding-3-large` = **metered** (same bucket as `judge_llm`, NOT the Anthropic subscription). Tiny per call; cache to avoid re-embeds.

## Rule (from `[INGESTION-DESIGN]`)
Embedding **surfaces** candidates; the **cached `merge_judge`** (positive merges double-confirmed) **decides**; a wrong merge is **un-mergeable**. Embedding score alone NEVER merges.
