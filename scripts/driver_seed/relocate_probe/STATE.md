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

## Deferred (seed-side, NOT relocation) — do with a certified-pipeline regression check
- **XBRL member-parser bug** (`link_lib.seg_members`): `explicitMember` can be a LIST of `{dimension,$t}`
  (multi-axis, e.g. OperatingSegments × GroceryAndSnacks) — current code only reads a single dict, so
  multi-axis segment facts parse to `[]`. **The naive ~4-line "loop over the list" fix is NOT safe:
  tested 2026-07-13, it BROKE 50 / 1761 certified T1 records (~3%).** Reason: parsing the extra members
  makes previously-invisible multi-axis facts (that used to return `[]`) collide at the same value with
  the single-axis fact, so `tier1` sees an ambiguous member tie and ABSTAINS → loses the clean match.
  So the real fix needs a COMPANION ambiguity resolver (prefer the member set that best/most-specifically
  matches the KPI slice, or dedupe same-value facts across axis-decompositions) — not a one-liner. Only
  worth it for the SEED side (free Lane-0 count = 5% on the text-relocation residual). Regression harness:
  `scratchpad/t1_regression.py` (re-runs tier1 on all certified T1 records; must show 0 BROKE before merge).

## Alignment with the LOCKED FinalDesign (audited 2026-07-13, 3 Opus readers)
Verdict: probe `kind/slice/units` are **COMPATIBLE-BUT-CRUDER retrieval aids**, LOW risk — they enforce the
distinctions that matter (won't bind wrong-kind/measurement/slice) and NEVER write typed identity.
- **Units:** probe's currency/count/percent = a coarse hint like the design's `unit_kind_hint`; NOT the final
  10-value enum (`usd/m_usd/percent…`). Per-X → base unit matches UNIT-08. `locate()` doesn't even use it. Guard: never let this become the stored unit.
- **Slices:** design = typed `kind:value`, 6 kinds (segment/product/geography/customer/channel/entity_ownership + unknown);
  period is NOT a slice; total = OMITTED slice (not `slice=total`); LLM never merges (over-split-safe). Probe = untyped
  word-bag naming 4 of 6 kinds — benign because scope is same-company + same-KPI + cross-period only (the design's
  cross-company/cross-axis hazard FS-08/FS-23 is out of scope). Probe emits no typed slice → can't corrupt identity.
- **Kind:** there is NO `metric_family` field/taxonomy. Identity = separate fields: `name` (revenue vs profit) ·
  `unit` · `measurement` (adjusted/organic/GAAP — NOT the name; GAAP = empty, read-time view) · `slice` · `fact_type`.
  Adjusted vs GAAP = SAME driver, DIFFERENT facts (measurement token). Probe's "don't swap" = correct for retrieval.
- **REQUIRED HANDOFF (pipeline's job, not the probe's):** a decomposition step must split the raw fiscal.ai name into
  `name / measurement / slice`, stamp `fact_type` (else DU-12 reject), and resolve the enum unit BEFORE any write.
  NEVER store the raw fiscal.ai name as `Driver.name` (violates NAME-10/14; re-creates the retired `adjusted_eps` defect, 95 #2).

## Known limits / next
- Annual only (quarterly leave-one-out infeasible: fiscal.ai free + Neo4j lag too thin).
- A–D companies, recent periods (oracle = fiscal.ai free values).
- Deep audit (Fable-5) pending: source-agnostic generalization (news/transcript), simplification,
  XBRL identity-fetch for financial-segment metrics. Apply changes ITERATIVELY, small-sample-checked.
