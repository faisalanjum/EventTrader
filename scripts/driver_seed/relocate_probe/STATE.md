# Driver-value relocation probe — state

**What it does:** given a text metric locked from one period (its verbatim quote), blind-refetch its
exact value in a DIFFERENT period's filing — 100% precision is the hard rule; abstain > guess.
This is the "how locked text drivers get future/historical values" mechanism. ISOLATED test harness;
touches nothing in production seeding.

## Method (frozen, working)
1. `build_address` — from the lock filing: label tokens (KEEP metric-kind words), table caption
   (heading, not prose), sibling row-labels, unit, lock_row.
2. `locate` — candidate snippets in the target filing by structural overlap (siblings+caption+label),
   keep ~6 tables + prose windows.
3. `relocate.js` bind — LLM picks TABLE → LINE → COLUMN via the two-signal picker (period TYPE
   annual/quarter + DATE). No magnitude guard, no lock-value anchor (both removed as fragile).
4. verify — independent LLM re-check (right line + right period).
5. `grade.py` — leave-one-out oracle: build address from period A, blind-refetch period B, grade the
   picked number vs fiscal.ai's known B value (rounding-tolerant). Sources: 10-K/10-Q + 8-K EX-99.1.

## Results (blind, unseen companies)
| run | precision | recall | notes |
|---|---|---|---|
| 39-pair (design+holdout) | 100% | 90% | small sample |
| **150-pair validation** (A–D, annual) | **95.8%** | **76%** | the trustworthy corpus-wide read |

Per type (150): geography 100% / segment-rev 100% / operational 97% / non-GAAP 92% / other 78%.

## Key findings
- The 5 precision misses are DEFINITIONAL near-misses: fiscal.ai stores an ADJUSTED number, the filing
  states GAAP (e.g. seg op profit 989.4 adj vs 1,017.0 GAAP); 3/5 fiscal.ai's value not in the filing.
  In production seeding (we HAVE the value + gate `value_ok`) these abstain → precision ~100%. The 95.8%
  is the harder no-value FUTURE-fetch case.
- Two bugs fixed 2026-07-13: (A) label stripped metric-kind words → `kpi_tokens` keeps them;
  (B) caption grabbed MD&A prose → `caption_of` takes the heading.
- Recall ceiling ~90%; misses are safe abstains or value not on the fetched pages.

## Known limits / next
- Annual only (quarterly leave-one-out infeasible: fiscal.ai free + Neo4j lag too thin).
- A–D companies, recent periods (oracle = fiscal.ai free values).
- Deep audit (Fable-5) pending: source-agnostic generalization (news/transcript), simplification,
  XBRL identity-fetch for financial-segment metrics. Apply changes ITERATIVELY, small-sample-checked.
