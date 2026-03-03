# 8-K Guidance Extraction — Design & Findings

**Date**: 2026-02-26
**Status**: Dry-run validated, pre-write
**Parent**: `guidanceInventory.md` (§3 source #2, §10 execution order step 3)

---

## Issues Found

### Issue A — CLOSED: Double-Scaling Bug (3 Revenue Items)

**Fixed as Issue #20 in `guidance-extraction-issues.md`.** Prompt fix (copy as printed) + code guard (`multiplier > 1 and value > 999`) in `canonicalize_value()`.

**Original finding (pre-fix):** Same as Issue #20 from AAPL transcript runs. Agent pre-converts "$10.3B" → 10300 (millions), then sets `unit_raw: "billion"`. The canonicalizer in `guidance_ids.py:canonicalize_value()` sees `10300` + `"billion"` and multiplies by 1000 → **10,300,000 m_usd ($10.3 TRILLION)**.

**Verified by direct test:**
```python
canonicalize_value(10300.0, 'billion', 'm_usd', 'revenue')  # → 10300000.0 (WRONG)
canonicalize_value(10.3, 'billion', 'm_usd', 'revenue')     # → 10300.0    (CORRECT)
```

**Affected items:**
| Item | Agent value | Would write as | Correct value |
|---|---|---|---|
| Revenue Total low | 10300.0 | 10,300,000.0 m_usd | 10,300.0 m_usd |
| Revenue QCT low | 9000.0 | 9,000,000.0 m_usd | 9,000.0 m_usd |
| Revenue QTL low | 1250.0 | 1,250,000.0 m_usd | 1,250.0 m_usd |

**EPS items unaffected** — per-share override in `canonicalize_value()` skips scaling for `label_slug in PER_SHARE_LABELS`.

**Root cause:** The agent does mental math (10.3B → 10,300M) before writing JSON, then also declares `unit_raw: "billion"`. The system expects one of:
- Raw values as spoken: `low=10.3, unit_raw="billion"` → canonicalizer scales to m_usd
- Pre-converted values: `low=10300, unit_raw="million"` → canonicalizer recognizes already in millions

**Fix options:**

**Fix A1: Code guard in `guidance_ids.py` (0% regression)**

Add a sanity check in `canonicalize_value()`: if the value is already large (>1000) AND unit_raw suggests billions, skip scaling:

```python
# In canonicalize_value(), after multiplier resolution:
if canonical_unit == 'm_usd' and multiplier is not None and multiplier >= 1000:
    if value >= 1000:  # Already looks like millions
        return value   # Skip scaling — likely pre-converted
```

Trade-off: Could misfire on genuinely large billion-scale numbers ($5000B = $5T), but no company guides $5T revenue. Threshold of 1000 is safe.

**Fix A2: Code guard in `guidance_write_cli.py` (validation layer)**

Add a reasonableness check after ID computation:
```python
if item.get('canonical_unit') == 'm_usd' and canonical_low and canonical_low > 1_000_000:
    errors.append(f"SUSPICIOUS: {item['label']} low={canonical_low} m_usd — possible double-scaling")
```

Trade-off: Doesn't prevent the bug, just flags it. Useful as diagnostic even if A1 is implemented.

**Fix A3: Prompt fix in `guidance-extract.md` (unreliable)**

Add instruction: "Always pass raw values exactly as stated in the source text. Do NOT pre-convert units. If source says '$10.3 billion', pass low=10.3, unit_raw='billion'."

Trade-off: LLMs may still pre-convert on some runs. Prompt-only fix is unreliable.

**Recommended: A1 + A2 + A3** (defense in depth — code guard prevents, CLI flags, prompt nudges).

---

### Issue B — LOW: Stale Member Taxonomy Version

Agent used `804328:http://www.qualcomm.com/20221225:qcom:QctMember` (Dec 2022). Latest available: `20250629` (Jun 2025). The 2022 node exists in the graph so the link will succeed, but per spec §7 it should use the current taxonomy window.

**Root cause:** Agent found members through direct Member node search rather than the spec's member cache (QUERIES.md 2B), which returned empty for QCOM (see Issue C). The direct search returned the oldest matching node first.

**Fix:** Not blocking. The write will succeed. Address later when improving member resolution ordering.

---

### Issue C — LOW: Member Cache Gap for QCOM

The standard member cache query (QUERIES.md 2B) filters `dim_u_id CONTAINS 'Segment' OR 'Product' OR 'Geography' OR 'Region'`. QCOM's Context nodes don't associate QCT/QTL members via dimensions matching this filter. The agent found members through a fallback path (direct Member node search).

**Evidence:** Direct `MATCH (m:Member) WHERE m.qname CONTAINS 'Qct'` found 11 taxonomy versions. But the Context-based member cache returned empty `[]`.

**Fix:** QCOM may use a custom axis name (e.g., `StatementBusinessSegmentsAxis`). Could widen the 2B filter, but low priority.

---

### Issue D — LOW: Conditions Missing from Segment Items

Footnote (1) applies to the entire Business Outlook table, but only Revenue(Total), EPS(GAAP), and EPS(non-GAAP) carry the conditions text. Revenue(QCT) and Revenue(QTL) have `conditions: null`.

**Fix:** Prompt clarification — "When a disclaimer footnote applies to the entire guidance table, propagate conditions to ALL items, including supplemental/segment items." Low priority.

---

## Architecture Finding

**`guidance-extract` handles ALL source types** — not just transcripts. It routes by `SOURCE_TYPE` parameter:

| Source Type | Profile Loaded | Queries Used |
|---|---|---|
| `8k` | `PROFILE_8K.md` | 4G (content inventory) → 4C (exhibit) → 4E (section) → 4F (filing text) |
| `transcript` | `PROFILE_TRANSCRIPT.md` | 3B/3C/3D (prepared remarks, Q&A) |
| `news` | `PROFILE_NEWS.md` | 6A/6B |
| `10q` / `10k` | `PROFILE_10Q.md` / `PROFILE_10K.md` | 5B/5C |

**`guidance-qa-enrich` is transcript-only** (Phase 2 — enriches Phase 1 items with Q&A content). Its agent file explicitly states: "This agent ONLY processes transcripts."

This means 8-K extraction uses the same `guidance-extract` agent that already works for transcripts. No new agent needed.

---

## Context

The guidance extraction system has been running on **transcripts only** (AAPL, 5 runs, 30 GuidanceUpdate nodes). Per the spec's execution order, 8-K is the next source type to validate. Two dry-runs were completed:

1. **AAPL 8-K** (`0000320193-25-000071`, Q4 FY2025) — Minimal-guidance path validated. Apple doesn't provide operating guidance in press releases. 1 DPS item extracted (dividend declaration).
2. **QCOM 8-K** (`0000804328-25-000044`, Q3 FY2025 earnings / Q4 FY2025 outlook) — 5 items extracted from Business Outlook section. Full audit completed.

---

## AAPL 8-K Dry-Run Results

**Filing**: `0000320193-25-000071` (Q3 FY2025 earnings, filed 2025-07-31)
**Outcome**: 1 item extracted (DPS only). Apple does not provide forward revenue/EPS guidance in press releases — validates the minimal-guidance / near-empty path.

### Extracted Item

| # | Label | Segment | Basis | Low | Mid | High | Unit | Derivation | XBRL Concept |
|---|-------|---------|-------|-----|-----|------|------|------------|--------------|
| 1 | DPS | Total | unknown | 0.26 | 0.26 | 0.26 | dollars | point | us-gaap:CommonStockDividendsPerShareDeclared |

- **Quote**: "Apple's board of directors has declared a cash dividend of $0.26 per share of the Company's common stock. The dividend is payable on August 14, 2025 to shareholders of record as of the close of business on August 11, 2025."
- **Conditions**: "payable on August 14, 2025 to shareholders of record as of the close of business on August 11, 2025"
- **Aliases**: `["Dividend Per Share", "Dividends Per Share"]`
- **Section**: Press Release, **Source key**: EX-99.1

### AAPL JSON Payload

```json
{
    "source_id": "0000320193-25-000071",
    "source_type": "8k",
    "ticker": "AAPL",
    "fye_month": 9,
    "items": [
        {
            "label": "DPS",
            "given_date": "2025-07-31",
            "fiscal_year": 2025,
            "fiscal_quarter": 4,
            "basis_norm": "unknown",
            "segment": "Total",
            "low": 0.26,
            "mid": 0.26,
            "high": 0.26,
            "unit_raw": "dollars",
            "qualitative": null,
            "conditions": "payable on August 14, 2025 to shareholders of record as of the close of business on August 11, 2025",
            "quote": "Apple's board of directors has declared a cash dividend of $0.26 per share of the Company's common stock. The dividend is payable on August 14, 2025 to shareholders of record as of the close of business on August 11, 2025.",
            "section": "Press Release",
            "source_key": "EX-99.1",
            "derivation": "point",
            "basis_raw": null,
            "aliases": ["Dividend Per Share", "Dividends Per Share"],
            "xbrl_qname": "us-gaap:CommonStockDividendsPerShareDeclared",
            "member_u_ids": []
        }
    ]
}
```

---

## QCOM 8-K Dry-Run Results

**Filing**: `0000804328-25-000044` (Q3 FY2025 earnings / Q4 FY2025 outlook, filed 2025-07-30)
**Outcome**: 5/5 items extracted — 100% recall, 0 false positives.

### Extracted Items

| # | Label | Segment | Basis | Low | Mid | High | Unit | Derivation | Quote |
|---|-------|---------|-------|-----|-----|------|------|------------|-------|
| 1 | Revenue | Total | unknown | 10300.0 | 10700.0 | 11100.0 | billion | explicit | "Current Guidance Q4 FY25 Estimates Revenues $10.3B - $11.1B" |
| 2 | Revenue | QCT | unknown | 9000.0 | 9300.0 | 9600.0 | billion | explicit | "Supplemental Revenue Information QCT revenues $9.0B - $9.6B" |
| 3 | Revenue | QTL | unknown | 1250.0 | 1350.0 | 1450.0 | billion | explicit | "Supplemental Revenue Information QTL revenues $1.25B - $1.45B" |
| 4 | EPS | Total | gaap | 2.23 | 2.33 | 2.43 | dollars | explicit | "Current Guidance Q4 FY25 Estimates GAAP diluted EPS $2.23 - $2.43" |
| 5 | EPS | Total | non_gaap | 2.75 | 2.85 | 2.95 | dollars | explicit | "Current Guidance Q4 FY25 Estimates Non-GAAP diluted EPS $2.75 - $2.95" |

**Note on Revenue items**: Agent pre-converted values to millions (10.3B → 10300) but kept `unit_raw: "billion"` — triggers Issue A double-scaling bug. Correct source values are $10.3B, $9.0B, $1.25B.

### Per-Item Detail

**Items 1-3 (Revenue)**: `basis_raw: null` (no explicit GAAP/non-GAAP qualifier on revenue line), `xbrl_qname: "us-gaap:Revenues"`, `section: "Business Outlook"`, `source_key: "EX-99.1"`, `qualitative: null`, `aliases: []`.

**Items 1, 4, 5 (Total segment)**: `member_u_ids: []` (no member linking needed for consolidated totals).

**Items 2-3 (Segment)**: Member u_ids linked:
- QCT: `["804328:http://www.qualcomm.com/20221225:qcom:QctMember"]` (stale taxonomy — Issue B)
- QTL: `["804328:http://www.qualcomm.com/20221225:qcom:QtlMember"]` (stale taxonomy — Issue B)

**Items 1, 4, 5 (Conditions)**: All carry the same disclaimer — "Our outlook does not include provisions for proposed tax law changes or for the recently enacted tax reform legislation included in the One Big Beautiful Bill Act, future asset impairments or for pending legal matters, other than future legal amounts that are probable and estimable."

**Items 2-3 (Conditions)**: `null` — footnote not propagated to segment items (Issue D).

**Items 4-5 (EPS)**: `basis_raw: "GAAP"` / `"Non-GAAP"` respectively.

### Correctly Excluded

- GAAP→non-GAAP bridge items (QSI $0, SBC -$0.53, other items $0.01)
- CEO qualitative: "confidence in achieving our long-term revenue targets" (no quantitative anchor)
- Buyback: "On track to meet our accelerated buyback commitment" (qualitative, no amount)
- All Q3 FY2025 actuals (past period)
- Dividend $0.89/share paid in Q3 (past, no Q4 declaration in this filing)
- Item 2.02 section text (just references EX-99.1, no standalone guidance)

### QCOM JSON Payload

```json
{
    "source_id": "0000804328-25-000044",
    "source_type": "8k",
    "ticker": "QCOM",
    "fye_month": 9,
    "items": [
        {
            "label": "Revenue",
            "given_date": "2025-07-30",
            "fiscal_year": 2025,
            "fiscal_quarter": 4,
            "basis_norm": "unknown",
            "segment": "Total",
            "low": 10300.0,
            "mid": 10700.0,
            "high": 11100.0,
            "unit_raw": "billion",
            "qualitative": null,
            "conditions": "Our outlook does not include provisions for proposed tax law changes or for the recently enacted tax reform legislation included in the One Big Beautiful Bill Act, future asset impairments or for pending legal matters, other than future legal amounts that are probable and estimable.",
            "quote": "Current Guidance Q4 FY25 Estimates Revenues $10.3B - $11.1B",
            "section": "Business Outlook",
            "source_key": "EX-99.1",
            "derivation": "explicit",
            "basis_raw": null,
            "aliases": [],
            "xbrl_qname": "us-gaap:Revenues",
            "member_u_ids": []
        },
        {
            "label": "Revenue",
            "given_date": "2025-07-30",
            "fiscal_year": 2025,
            "fiscal_quarter": 4,
            "basis_norm": "unknown",
            "segment": "QCT",
            "low": 9000.0,
            "mid": 9300.0,
            "high": 9600.0,
            "unit_raw": "billion",
            "qualitative": null,
            "conditions": null,
            "quote": "Supplemental Revenue Information QCT revenues $9.0B - $9.6B",
            "section": "Business Outlook",
            "source_key": "EX-99.1",
            "derivation": "explicit",
            "basis_raw": null,
            "aliases": [],
            "xbrl_qname": "us-gaap:Revenues",
            "member_u_ids": ["804328:http://www.qualcomm.com/20221225:qcom:QctMember"]
        },
        {
            "label": "Revenue",
            "given_date": "2025-07-30",
            "fiscal_year": 2025,
            "fiscal_quarter": 4,
            "basis_norm": "unknown",
            "segment": "QTL",
            "low": 1250.0,
            "mid": 1350.0,
            "high": 1450.0,
            "unit_raw": "billion",
            "qualitative": null,
            "conditions": null,
            "quote": "Supplemental Revenue Information QTL revenues $1.25B - $1.45B",
            "section": "Business Outlook",
            "source_key": "EX-99.1",
            "derivation": "explicit",
            "basis_raw": null,
            "aliases": [],
            "xbrl_qname": "us-gaap:Revenues",
            "member_u_ids": ["804328:http://www.qualcomm.com/20221225:qcom:QtlMember"]
        },
        {
            "label": "EPS",
            "given_date": "2025-07-30",
            "fiscal_year": 2025,
            "fiscal_quarter": 4,
            "basis_norm": "gaap",
            "segment": "Total",
            "low": 2.23,
            "mid": 2.33,
            "high": 2.43,
            "unit_raw": "dollars",
            "qualitative": null,
            "conditions": "Our outlook does not include provisions for proposed tax law changes or for the recently enacted tax reform legislation included in the One Big Beautiful Bill Act, future asset impairments or for pending legal matters, other than future legal amounts that are probable and estimable.",
            "quote": "Current Guidance Q4 FY25 Estimates GAAP diluted EPS $2.23 - $2.43",
            "section": "Business Outlook",
            "source_key": "EX-99.1",
            "derivation": "explicit",
            "basis_raw": "GAAP",
            "aliases": [],
            "xbrl_qname": "us-gaap:EarningsPerShareDiluted",
            "member_u_ids": []
        },
        {
            "label": "EPS",
            "given_date": "2025-07-30",
            "fiscal_year": 2025,
            "fiscal_quarter": 4,
            "basis_norm": "non_gaap",
            "segment": "Total",
            "low": 2.75,
            "mid": 2.85,
            "high": 2.95,
            "unit_raw": "dollars",
            "qualitative": null,
            "conditions": "Our outlook does not include provisions for proposed tax law changes or for the recently enacted tax reform legislation included in the One Big Beautiful Bill Act, future asset impairments or for pending legal matters, other than future legal amounts that are probable and estimable.",
            "quote": "Current Guidance Q4 FY25 Estimates Non-GAAP diluted EPS $2.75 - $2.95",
            "section": "Business Outlook",
            "source_key": "EX-99.1",
            "derivation": "explicit",
            "basis_raw": "Non-GAAP",
            "aliases": [],
            "xbrl_qname": "us-gaap:EarningsPerShareDiluted",
            "member_u_ids": []
        }
    ]
}
```

### CLI Dry-Run Output

```json
{"mode": "dry_run", "total": 5, "valid": 5, "id_errors": [], "results": [
  {"id": "gu:0000804328-25-000044:revenue:gp_2025-07-01_2025-09-30:unknown:total"},
  {"id": "gu:0000804328-25-000044:revenue:gp_2025-07-01_2025-09-30:unknown:qct"},
  {"id": "gu:0000804328-25-000044:revenue:gp_2025-07-01_2025-09-30:unknown:qtl"},
  {"id": "gu:0000804328-25-000044:eps:gp_2025-07-01_2025-09-30:gaap:total"},
  {"id": "gu:0000804328-25-000044:eps:gp_2025-07-01_2025-09-30:non_gaap:total"}
]}
```

---

## What Worked Well

- **8-K routing**: Agent correctly loaded PROFILE_8K.md, ran 4G (content inventory) → 4C (exhibit fetch)
- **Business Outlook section identification**: Agent found the guidance table cleanly
- **GAAP/non-GAAP dual extraction**: Both EPS bases extracted separately with correct `basis_norm`/`basis_raw` — exactly what PROFILE_8K's "table columns trap" was designed for
- **Segment member linking**: QCT and QTL correctly identified with XBRL Member u_ids
- **Period resolution**: Q4 FY2025 → `gp_2025-07-01_2025-09-30` (Sep FYE, Jul-Sep quarter) correct
- **XBRL concepts**: `us-gaap:Revenues` and `us-gaap:EarningsPerShareDiluted` both confirmed in concept cache (usage=13)
- **Basis rules**: Revenue correctly `unknown` (no explicit qualifier), EPS correctly split
- **Exclusion logic**: Bridge items, qualitative quotes, actuals all correctly filtered
- **Empty path (AAPL)**: `NO_GUIDANCE` handled cleanly, no crash, no false positives

---

## Implementation Plan

### Step 1: Fix double-scaling bug (Issue A)

**Files to modify:**
- `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py` — Add heuristic guard in `canonicalize_value()`
- `.claude/skills/earnings-orchestrator/scripts/test_guidance_ids.py` — Add test cases for double-scaling detection
- `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py` — Add reasonableness warning
- `.claude/agents/guidance-extract.md` — Add prompt instruction about raw values

### Step 2: Re-run QCOM dry-run to verify fix

After code fix, re-run:
```
QCOM 8k 0000804328-25-000044 MODE=dry_run
```
Verify all 3 Revenue items produce correct canonical values (10300, 9000, 1250 m_usd).

### Step 3: Run QCOM 8-K in write mode

```bash
ENABLE_GUIDANCE_WRITES=true bash .claude/skills/earnings-orchestrator/scripts/guidance_write.sh /tmp/gu_QCOM_0000804328-25-000044.json --write
```

Verify in Neo4j:
```cypher
MATCH (gu:GuidanceUpdate)-[:FOR_COMPANY]->(c:Company {ticker: 'QCOM'})
RETURN gu.id, gu.low, gu.mid, gu.high, gu.canonical_unit
```

### Step 4: Run 2-3 more companies on 8-K

Candidates (companies known to provide 8-K guidance):
- QCOM — done
- Need 2 more with rich Business Outlook sections
- Find via: `MATCH (r:Report {formType:'8-K'})-[:HAS_EXHIBIT]->(e:ExhibitContent) WHERE e.content CONTAINS 'Business Outlook' ...`

### Step 5: Run QCOM transcript for cross-source validation

Process QCOM transcript for the same earnings event. Verify:
- Cross-source dedup works (same metrics from different sources get different slot IDs via different `source_id`)
- Transcript has additional guidance not in 8-K (common)
- The graph accumulates correctly across source types

### Step 6: Progress toward must-pass gates

After Steps 1-5, status would be:
- [x] 1 company on transcripts (AAPL — 5 runs, 30 items)
- [ ] 3+ companies on transcripts (need QCOM + 1 more)
- [ ] 3+ companies on 8-K (AAPL validated NO_GUIDANCE path, QCOM done, need 1 more)
- [ ] 3+ source types (transcript + 8-K = 2, need news or 10-Q)
- [ ] Idempotency check (same source twice → 0 new nodes)

---

## Reference: Source Data Verified

| Check | Result |
|---|---|
| EX-99.1 exhibit size | 25,309 chars |
| Other exhibits | None (EX-99.1 only) |
| Item 2.02 section | "issued a press release... furnished as Exhibit 99.1" (pointer only) |
| Filing date | 2025-07-30T16:01:22-04:00 |
| Market session | post_market |
| CIK | 0000804328 |
| FYE month | 9 (September) |
| Concept cache | `us-gaap:Revenues` (usage=13), `us-gaap:EarningsPerShareDiluted` (usage=13) confirmed |
| Member nodes | QctMember (11 versions), QtlMember (11 versions) exist |
| Member cache (2B) | Empty for QCOM — dimension filter gap |
