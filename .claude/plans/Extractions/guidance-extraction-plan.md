# Guidance Extraction Plan — Prioritized Execution

**Created**: 2026-03-15
**Status**: Active
**Parent**: `extraction-pipeline-reference.md` (pipeline architecture), `earnings-orchestrator.md` (prediction pipeline)

---

## Context

The guidance extraction pipeline v3.5 is built, deployed on K8s, and validated (CRM E2E: 28 items, 100% recall/precision across all 5 assets). This plan covers scaling extraction to all companies and all source types.

**What this unlocks:**
- Trade 1: Earnings prediction (guidance vs consensus at earnings time)
- Trade 2: Standalone guidance trading (mid-quarter revisions)
- Prediction context: inter-quarter 8-K filings with `extracted_sections` (predictor.md §4b Input 3)

---

## Extraction Sources — Final Decisions (2026-03-15)

| Source | Extract? | Gate | Reasoning |
|---|---|---|---|
| **Transcripts** | Yes | None — all processed | Richest source. Q&A captures nuanced guidance press releases omit. |
| **8-K Item 2.02** | Yes | None — item code IS the gate | Always contains earnings press release (EX-99.1). 100% recall for earnings-bundled guidance. |
| **8-K Items 7.01/8.01** | Yes | Haiku `FINANCIAL_GUIDANCE` tag OR keyword rescue | Catches standalone mid-quarter guidance. Requires Haiku router (Phase 1b). |
| **8-K Investor Presentations** | Yes | Haiku `INVESTOR_PRESENTATION` tag | ~$140 recall insurance. Extraction returns empty if no guidance — zero cost for false positives. |
| **8-K Item 5.02 + EX-99.1** | Yes | Keyword rescue ("guidance", "outlook") | CEO departure press releases with embedded outlook revision. Edge case. |
| **10-Q** | Yes | None — MD&A section always targeted | 98.9% have MD&A. Fallback chain for the 1.1% without. |
| **10-K** | Yes | None — MD&A section always targeted | 99.6% have MD&A. Fallback chain for the 0.4% without. |
| **News** | **SKIP** | — | Reports ON guidance, doesn't create it. Same data in 8-K/transcript. Headlines provide consensus via "Vs $X Est" pattern for free in predictor context (Input 5). |

### 10-Q/10-K Fallback Chain (confirmed — no changes needed)

1. Fetch MD&A section ← normal path (99%+)
2. If MD&A missing → scan other narrative sections
3. If still nothing → financial statement JSON payloads (embedded notes)
4. If still nothing → exhibits
5. Last resort → raw filing text (bounded/sliced)

In practice, steps 2-5 almost never fire.

---

## Execution Plan

### Architecture Decision (2026-03-15 — final, validated)

**No classification gate. No Haiku router. No keywords. Item code filter + extraction LLM only.**

Validated through 75-sample testing across 3 test runs:
- Haiku 24-way classification: 33% accuracy (catastrophic — hallucinated guidance in non-guidance filings)
- Haiku binary classification: 59% precision (7/15 hard negatives incorrectly flagged as guidance)
- Keywords: 31% precision for guidance, 0-75% for other tags
- Root cause: Haiku hallucinates on raw database content (legal boilerplate, safe-harbor disclaimers)

**The extraction LLM (Sonnet 4.6) IS the precision gate.** It reads full content and returns empty if no guidance. False positives produce no bad data — they just waste extraction tokens. At one company at a time, cost is manageable (~20 filings per company).

### The One Rule

```
EXTRACT GUIDANCE FROM 8-K IF:
  Item 2.02 OR Item 7.01 OR Item 8.01 is present.
  Skip everything else.

  Covered:  16,561 filings (69.5%)
  Skipped:   7,275 filings (30.5%) — 5.02, 5.07, 1.01, 5.03, etc.
  Recall:   ~99.9% (verified: only ~75 skipped filings contain
            guidance keywords + financial metrics in exhibits,
            most are boilerplate noise)

  Why this works: SEC Regulation FD requires material forward-looking
  disclosures under Item 7.01. Guidance IS a Reg FD event. Filings
  with guidance but without 7.01/8.01 are either sloppy filers or
  incidental boilerplate mentions (~0.1% gap).
```

### Execution (single phase — no dependencies)

| Task | Source | Filter | Count | Model |
|---|---|---|---|---|
| Transcripts | Earnings call transcripts | None — all processed | All companies | Sonnet 4.6 |
| 8-K | All 8-K filings | `Item 2.02 OR Item 7.01 OR Item 8.01` | 16,561 filings | Sonnet 4.6 |
| 10-Q | Quarterly filings | MD&A section + fallback chain | All 10-Qs | Sonnet 4.6 |
| 10-K | Annual filings | MD&A section + fallback chain | All 10-Ks | Sonnet 4.6 |

**Command:** `trigger-extract.py --all --type guidance --asset 8k` with item-code filter added to process only filings containing Item 2.02, 7.01, or 8.01.

**What was eliminated:**
- ~~Phase 1b: Haiku router batch~~ — Haiku unreliable on raw content (33-59% accuracy)
- ~~Phase 2: Haiku-gated extraction~~ — no gate needed, extraction LLM handles precision
- ~~Keyword rescue~~ — 31% precision, keywords match strings not meaning
- ~~24-tag taxonomy classification~~ — deferred to shelf (designed, ready if needed later)

### 24-Tag Taxonomy Status

The taxonomy (8k_strategy.md §1A) is **designed and shelved**, not abandoned:
- 8 deterministic tags work perfectly (item code = tag, SEC law)
- 16 semantic tags require reliable classification which Haiku can't provide on raw content
- If a larger model (Sonnet/Opus) proves reliable, or if the prediction attributor reveals specific tags are needed, deploy from shelf
- No infrastructure lost — the prompt, definitions, and broad improvements (2026-03-15) are all documented

---

## What This Does NOT Include

| Item | Status | Why deferred |
|---|---|---|
| News guidance extraction | **SKIP** (decided 2026-03-15) | Reports ON guidance, doesn't create it. 8-K + transcript + 10-Q/10-K cover 99%+. |
| News consensus extraction | **SKIP** (decided 2026-03-15) | AlphaVantage covers EPS + Revenue. Headlines carry embedded "Vs $X Est" naturally. |
| Haiku/keyword classification | **ELIMINATED** (validated 2026-03-15) | Haiku hallucinates on raw content (33-59%). Keywords: 31% precision. Extraction LLM handles precision instead. |
| Non-guidance 8-K event tags | **SHELVED** (taxonomy ready in 8k_strategy.md) | Feed predictor raw `extracted_sections` text. Tags not needed for prediction — LLM reads raw context. Deploy from shelf if attributor proves specific tags are needed. |
| Operating metric consensus (CF, EBITDA, margins) | **Known gap** | No source outside Bloomberg/FactSet. Revisit if attributor flags prediction failures. |

---

## After Extraction Completes → Prediction Pipeline

The prediction pipeline has all 6 inputs:

1. **Guidance history** ← from this extraction plan (transcripts + 8-K + 10-Q/10-K)
2. **AlphaVantage consensus** ← EARNINGS + EARNINGS_ESTIMATES endpoints (EPS + Revenue)
3. **Non-earnings 8-K context** ← raw `extracted_sections` text from inter-quarter filings (no tags needed)
4. **Significant-move days with headlines** ← Cypher query (newsImpact.md architecture)
5. **Channel-filtered news headlines** ← Cypher query (12 channels, titles only)
6. **Attribution feedback** ← empty for first run, populated by attributor/learner

See `predictor.md §4b` and `earnings-orchestrator.md §2a` for the full context bundle specification.

---

## References

- `extraction-pipeline-reference.md` — pipeline v3.5 architecture, 8-slot agent design, model config
- `8k_strategy.md` — Haiku router design, 24-tag taxonomy, guidance routing paths
- `8k_reference.md` — 8-K database numbers, item code taxonomy, content layers
- `10q_reference.md` / `10k_reference.md` — periodic filing structure
- `news_reference.md` — guidance news filter (18,161 articles), channel inventory
- `predictor.md §4b` — prediction context bundle (6 inputs)
- `earnings-orchestrator.md §2a` — context bundle JSON schema
