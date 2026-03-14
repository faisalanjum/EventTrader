# 8-K Strategy — Consolidated Analysis

Date: 2026-03-14
Sources: Claude Session 1, Claude Session 2, Codex Sessions 2-4

This is the single canonical strategy document for 8-K extraction routing. It consolidates three independent analyses without losing any content.

**Companion file:** `8k_reference.md` — pure reference data (taxonomy, database numbers, query patterns)

---

## 1. How to use Haiku, super simply

Think of Haiku as a **traffic cop**, not an extractor.

- Rules handle easy filings.
- Haiku only looks at the messy ones.
- Haiku returns a tag, not a full analysis.

Simple example:

A new 8-K arrives with:

- items: `["7.01", "9.01"]`
- exhibit: EX-99.1
- excerpt: "Company reports second quarter 2025 financial results..."

You send Haiku only this small packet:

```json
{
  "items": ["7.01", "9.01"],
  "section_names": ["Regulation FD Disclosure", "Financial Statements and Exhibits"],
  "exhibits": ["EX-99.1"],
  "text_excerpt": "Company reports second quarter 2025 financial results..."
}
```

Prompt:

```text
Classify this 8-K into one primary event type using the canonical event taxonomy in Section 1A below.
Return JSON only.
```

Haiku returns:

```json
{
  "primary_event": "EARNINGS",
  "secondary_events": [],
  "confidence": 0.96
}
```

That is the whole idea.

**Use Haiku only for:**

- `7.01`
- `8.01`
- `9.01`-only
- mixed `5.02`
- messy multi-item filings

**Do not use Haiku for obvious buckets like:**

- `2.02` → earnings
- `2.01` → M&A
- `1.01 + 2.03` → debt
- `5.07` → governance

## 1A. Freeze The Haiku Tag List Before Production

Important distinction:

- SEC item codes already exist in the filing metadata
- Haiku tags should be the semantic event labels on top of those item codes

So do **not** ask Haiku to rediscover `2.02`, `5.02`, `8.01`, etc.
Ask it: **what economic event is this filing actually about?**

### Canonical event taxonomy (v4 — Claude + GPT + Codex combined, final)

Single source of truth for event tags. Used across storage, routing, and evaluation.

Built iteratively: Claude's database validation → GPT's naming improvements → Codex's safety findings → GPT's overlay refinement → final synthesis.

**Deterministic tags — item code alone, never sent to Haiku (10 tags)**

| Tag | Item Code | Filings | Why Deterministic |
|---|---|---|---|
| `EARNINGS` | 2.02 | 8,847 | IS earnings by SEC definition. 100% precision. |
| `M_AND_A` | 2.01 | 189 | IS acquisition/disposition completion. Signing (1.01) ≠ closing (2.01). |
| `DEBT_FINANCING` | 1.01+2.03 | 1,494 | IS debt creation. Private credit facilities, refinancings, covenant amendments. RESTORED per GPT — too structurally distinct to merge into MATERIAL_AGREEMENT. |
| `SHAREHOLDER_VOTE` | 5.07 | 2,279 | IS shareholder vote results. Split from GOVERNANCE (GPT). |
| `GOVERNANCE` | 5.03, remainder | 836+ | Bylaws, charter amendments, board committee changes |
| `IMPAIRMENT` | 2.06 | 54 | IS material impairment by SEC definition |
| `CYBERSECURITY` | 1.05 | 12 | IS cyber incident by SEC definition (Dec 2023 rule) |
| `RESTATEMENT` | 4.02 | 15 | IS non-reliance on prior financials. High-signal red flag. |
| `ACCOUNTANT_CHANGE` | 4.01 | 42 | IS auditor change by SEC definition |
| `DELISTING` | 3.01 | 55 | IS delisting notice by SEC definition |

**Semantic primary tags — Haiku assigns as primary_event (13 tags)**

| Tag | What It Covers |
|---|---|
| `BUYBACK` | Share/stock repurchase program announcements, authorizations, expansions |
| `DIVIDEND` | Cash dividend declarations, increases, special dividends |
| `RESTRUCTURING` | Layoffs, workforce reductions, facility closures, restructuring plans. NOT "restructuring charges" as accounting line items. |
| `EXECUTIVE_CHANGE` | C-suite and named executive officers ONLY (CEO, CFO, COO, President). Appointment, departure, compensation. Board directors = GOVERNANCE. |
| `MATERIAL_AGREEMENT` | Business partnerships, technology licenses, JVs, and contracts. NOT M&A closings (→ M_AND_A), NOT public offerings (→ SECURITIES_OFFERING), NOT private credit facilities (→ DEBT_FINANCING). |
| `SECURITIES_OFFERING` | Public bond/equity offerings, convertible notes, ATM programs, shelf registrations |
| `LITIGATION` | Lawsuits, settlements, legal proceedings, consent decrees |
| `PRODUCT_PIPELINE` | Clinical trial data, FDA/EMA approvals, regulatory submissions, drug/device clearances, product launches |
| `CREDIT_RATING` | Rating agency actions: downgrades, upgrades, outlook changes, credit watch |
| `SPINOFF_SPLIT` | Spin-offs, stock splits, reverse splits, corporate separations |
| `INVESTIGATION` | SEC/DOJ/government investigations, subpoenas, consent decrees |
| `OTHER_MATERIAL_EVENT` | Real business events that don't fit above categories |
| `ADMINISTRATIVE_ONLY` | Paperwork-only filings: 10b5-1 plans, exhibit corrections, plumbing filings with no business event. Skip in event timeline. |

**Overlay / secondary-only tags — almost never primary (3 tags)**

| Tag | When Primary | When Secondary | Why Overlay |
|---|---|---|---|
| `FINANCIAL_GUIDANCE` | Only if filing is SOLELY a guidance revision (rare mid-quarter update) | Usually secondary to EARNINGS or PRODUCT_PIPELINE | A filing is rarely "primarily about guidance" — it's primarily earnings that contains guidance, or a pipeline update with revenue targets |
| `INVESTOR_PRESENTATION` | Only if filing is literally just a deck with no stronger event | Secondary/context tag for filings that include a presentation alongside a real event | It's a document type, not an economic event |
| `REGULATORY` | Only if filing is a non-pipeline regulatory event (EPA subpoena, trade compliance) | Secondary when a PRODUCT_PIPELINE event also has regulatory dimensions | PRODUCT_PIPELINE covers most cases; this is the escape hatch for non-pipeline regulatory events |

**Total: 26 tags** (10 deterministic + 13 semantic primary + 3 overlay)

### Design rules

- Keep raw SEC item codes exactly as filed in `Report.items`
- Haiku assigns one `haiku_primary` from the 13 semantic primary tags (or 3 overlays when no stronger primary exists)
- Haiku assigns zero or more `haiku_secondary` from ALL 16 semantic + overlay tags
- Deterministic tags are assigned directly from item codes (no Haiku needed)
- A filing can have BOTH deterministic AND Haiku tags (e.g., deterministic `EARNINGS` + haiku_secondary `FINANCIAL_GUIDANCE`)
- Use `OTHER_MATERIAL_EVENT` for real business events that don't fit the taxonomy
- Use `ADMINISTRATIVE_ONLY` for paperwork — skip in event timeline entirely
- Do NOT keep a generic `OTHER` — always classify as `OTHER_MATERIAL_EVENT` or `ADMINISTRATIVE_ONLY`
- Overlay tags (FINANCIAL_GUIDANCE, INVESTOR_PRESENTATION, REGULATORY) should be secondary unless the filing has no stronger primary event

### What changed across versions

| Version | Change | Reason |
|---|---|---|
| v2 | GUIDANCE → FINANCIAL_GUIDANCE | Avoid clinical trial "guidance" false positives (NTLA test case) |
| v2 | CONTRACT_WIN → MATERIAL_AGREEMENT | Maps to SEC terminology (Item 1.01), broader coverage |
| v2 | CAPITAL_RAISE → SECURITIES_OFFERING | Covers both equity and debt public offerings |
| v2 | REGULATORY_UPDATE → PRODUCT_PIPELINE | Broader: captures clinical data + product launches |
| v2 | Added SHAREHOLDER_VOTE | Split from GOVERNANCE — 2,279 filings (GPT) |
| v2 | Added ADMINISTRATIVE_ONLY | Separates paperwork from material events (GPT) |
| v2 | OTHER → OTHER_MATERIAL_EVENT | More descriptive (GPT) |
| v3 | Kept SPINOFF_SPLIT, CREDIT_RATING, INVESTIGATION | GPT dropped — database shows 1,789 + 341 + 27 filings |
| v3 | Kept EARNINGS, M_AND_A as deterministic | GPT omitted — most important tags |
| v4 | **RESTORED DEBT_FINANCING** | GPT feedback: 1.01+2.03 is too structurally distinct for MATERIAL_AGREEMENT. Revolvers, term loans, refinancings deserve own tag. |
| v4 | **FINANCIAL_GUIDANCE → overlay** | GPT feedback: almost always secondary to EARNINGS or PRODUCT_PIPELINE, rarely a primary event on its own |
| v4 | **INVESTOR_PRESENTATION → overlay** | GPT feedback: document/context tag, not an economic event. Primary only when filing is just a deck. |
| v4 | **Added REGULATORY overlay** | GPT feedback: escape hatch for non-pipeline regulatory events |

### Recommended Haiku prompt (v4)

```text
Classify this 8-K filing into one primary event type and zero or more secondary types.

PRIMARY choices (pick exactly one):
BUYBACK, DIVIDEND, RESTRUCTURING, EXECUTIVE_CHANGE,
MATERIAL_AGREEMENT, SECURITIES_OFFERING, LITIGATION,
PRODUCT_PIPELINE, CREDIT_RATING, SPINOFF_SPLIT,
INVESTIGATION, OTHER_MATERIAL_EVENT, ADMINISTRATIVE_ONLY

SECONDARY / OVERLAY choices (pick zero or more):
FINANCIAL_GUIDANCE, INVESTOR_PRESENTATION, REGULATORY
(these can also be primary if no stronger event exists)

Definitions:
- FINANCIAL_GUIDANCE: Forward-looking FINANCIAL projections only
  (revenue, EPS, margins, CapEx). NOT clinical timelines. Usually secondary.
- EXECUTIVE_CHANGE: C-suite/named officers only. Board changes are not this.
- PRODUCT_PIPELINE: Clinical trial data, FDA actions, product launches.
- MATERIAL_AGREEMENT: Partnerships, licenses, JVs, contracts.
  NOT M&A closings, NOT public offerings, NOT credit facilities.
- SECURITIES_OFFERING: Public bond/equity offerings, convertibles, ATM programs.
- ADMINISTRATIVE_ONLY: Paperwork with no business event (10b5-1 plans, exhibit updates).
- REGULATORY: Non-pipeline regulatory events (EPA, trade compliance, sanctions).

Return JSON only:
{"primary_event": "...", "secondary_events": [...], "confidence": 0.0-1.0}
```

Note: EARNINGS, M_AND_A, DEBT_FINANCING, SHAREHOLDER_VOTE, GOVERNANCE, IMPAIRMENT, CYBERSECURITY, RESTATEMENT, ACCOUNTANT_CHANGE, DELISTING are NOT in the Haiku prompt — assigned deterministically from item codes.

### Haiku output example

```json
{
  "primary_event": "RESTRUCTURING",
  "secondary_events": ["FINANCIAL_GUIDANCE"],
  "confidence": 0.92
}
```

### Storage (on Report node)

```
haiku_primary:    String    'RESTRUCTURING'
haiku_secondary:  String    '["FINANCIAL_GUIDANCE"]'
haiku_confidence: Double    0.92
```

Deterministic tags stored separately or derived at query time from `Report.items`.

---

## Guidance Extraction Routing — Complete Spec

Guidance has NO item code. It hides inside other filings. Two paths combine for ~99%+ recall.

### Path A: Earnings-Bundled Guidance (100% recall, already built)

```
IF 'Item 2.02' in filing.items:
    → ALWAYS run guidance extraction on EX-99.1
    → No pre-screening needed
    → Recall: 100% for earnings-bundled guidance (~70-80% of all guidance)
    → Precision: 100% — extraction prompt returns nothing if no guidance
    → Pool: 8,847 filings
```

### Path B: Standalone Guidance (the hard part — mid-quarter revisions)

```
IF 'Item 7.01' OR 'Item 8.01' in filing.items (WITHOUT 2.02):
    → Gate: Haiku says FINANCIAL_GUIDANCE  OR  keywords match
    → Keywords: "guidance" OR "outlook" OR "preliminary results" OR
      "revised" OR "updated outlook" OR "pre-announce" OR
      "expects revenue" OR "expects earnings"
    → Union routing: Haiku catches euphemisms, keywords catch what Haiku undercalls
    → Recall: ~97-99% for standalone guidance
    → Pool: ~500-1,000 filings after gating (from ~10,500 candidates)
```

### Path C: Rescue (optional, catches ~1% edge cases)

```
IF 'Item 5.02' with EX-99.1 exhibit (WITHOUT 2.02):
    → Gate: keywords only ("guidance", "outlook")
    → Catches: CEO departure press release that includes outlook revision
    → Pool: ~50-100 additional filings
```

### Combined

| Metric | Value |
|---|---|
| Recall | **~99%+** |
| Precision | **100%** (extraction prompt handles — returns nothing if absent) |
| Total extractions | ~9,500-10,000 |
| Haiku pre-screen cost | ~$10-15 |
| Remaining gap (~1%) | Implicit guidance ("comfortable with Street consensus"), misclassified 9.01-only filings, euphemistic language |
| To get true 100% | Process all 23,836 filings through extraction prompt (expensive, diminishing returns) |

---

## Super Simple: Real-Time Earnings Detection

Honest answer:

you cannot get literal `100.00%` precision and `100.00%` recall from 8-K metadata alone.

Best practical rule:

1. Treat these as earnings candidates:
   - any filing with `2.02`
   - any filing with `7.01` or `8.01` plus `EX-99.1` / `EX-99.2`
2. Confirm with text or Haiku that the filing contains actual results, not just an announcement of a future call.

Positive evidence:

- `reported financial results`
- `quarter ended`
- `results for the quarter`
- `earnings presentation`
- `financial results for`

Negative evidence:

- `will release earnings`
- `announcing date of earnings release`
- `conference call scheduled`

Best measured deterministic coverage from the database:

- `2.02` alone: `95.11%` recall on the earnings keyword universe
- `2.02 + 7.01 + 8.01`: `99.42%` recall on the earnings keyword universe

So the practical answer is:

- deterministic rules catch the candidates
- Haiku or text confirmation separates real earnings from earnings-related noise
- always inspect `EX-99.1` / `EX-99.2` when present

## Super Simple: Guidance-Related 8-K Fetching

Honest answer:

there is no fully automated literal `100.00%` recall and `100.00%` precision rule for guidance-related 8-Ks.

If you want true 100/100, a human has to review the candidate set.

Best practical production rule:

1. Fetch this candidate set:
   - all `2.02`
   - all `7.01`
   - all `8.01`
   - all `9.01`-only filings that have `EX-99.x`
2. Read only:
   - the trigger sections
   - `EX-99.x`
   - skip `EX-10.x`
3. Call it `GUIDANCE` only if the content has explicit forward-looking guidance:
   - numeric future range or target for revenue, EPS, margin, EBITDA, capex, volumes, etc.
   - or explicit update language tied to future metrics:
     - `raises`
     - `lowers`
     - `reaffirms`
     - `updates`
     - `expects`
     - `outlook`
     - `preliminary results` with forward targets
4. Reject as non-guidance if it is only:
   - historical results
   - generic optimism / boilerplate outlook
   - investor presentation with no new targets
   - covenant or contract language
5. Use Haiku only on ambiguous cases, mainly:
   - `7.01`
   - `8.01`
   - `9.01`-only

So the closest safe production rule is:

`fetch = 2.02 OR 7.01 OR 8.01 OR (9.01-only with EX-99.x)`

then confirm with explicit forward-looking quantitative guidance in the section or `EX-99.x`, with Haiku helping only on the messy middle.

Why this is the right rule:

- `2.02` catches guidance bundled with earnings
- `7.01` and `8.01` catch standalone guidance revisions
- `9.01`-only rescues rare leaks
- keywords alone are too noisy
- Haiku alone is not reliable enough as the only gate

## Super Simple: Expected Hybrid Performance

Important caveat:

these are best operating estimates from the live validation and disagreement audits.
They are **not** exact gold-set precision / recall metrics.

If hybrid means:

- deterministic anchors for obvious buckets
- Haiku only for ambiguous buckets
- narrow rescue heuristics where needed

then the best overall estimate for the 4 validated event jobs is:

- expected recall: about `99%+`
- expected precision: about `high-80s / low-90s overall`

Best estimated performance by event type:

| Event type | Expected recall | Expected precision |
| --- | ---: | ---: |
| Earnings | `99.9%` | `95% to 99%` |
| Buyback | `99.4% to 99.7%` | `80% to 90%` |
| Dividend | `99.5% to 100%` | `75% to 90%` |
| Restructuring | `98.8% to 99.5%` | `85% to 95%` |

For the other event families, I am only comfortable saying the direction:

- debt: anchored bucket is very strong, likely high-90s precision
- M&A: anchored bucket is very strong, likely mid/high-90s precision
- governance: anchored bucket is very strong, likely mid/high-90s precision
- executive change: good but noisier, likely high-80s / low-90s precision

Weakest category:

- dividends

Strongest categories:

- earnings
- debt
- M&A
- governance

One more caveat:

these estimates assume the **good hybrid design**:

- rules for obvious filings
- Haiku only on ambiguous filings

If you use a naive union everywhere, recall may go up slightly but precision will get worse.

Small exact manual check:

- random non-earnings sample from the hybrid Haiku bucket: `10` filings
- primary-label accuracy: `10/10 = 100.00%`
- filing-level exact set match: `9/10 = 90.00%`
- multi-label precision: `91.67%`
- multi-label recall: `100.00%`

Artifact:

- `haiku_10sample_manual_validation.md`

## Super Simple: Best Practical Guidance Fetch Rule

There is no literal automated `100%` recall and `100%` precision rule for guidance. The only true `100/100` method is human review.

Best practical approach is to separate:

- guidance candidate fetch
- true guidance confirmation

### Candidate fetch

Fetch an 8-K for guidance processing if:

- it has `2.02`
- or it has `7.01`
- or it has `8.01`
- or it is `9.01`-only **and** has an `EX-99.x` press-release-style exhibit

Read only:

- the `2.02` / `7.01` / `8.01` / `9.01` sections
- `EX-99.1`, `EX-99.2`, other `EX-99.x`
- skip `EX-10.x`

Why this is the right fetch superset:

- `2.02` catches earnings releases, which often contain guidance
- standalone guidance revisions live mainly in `7.01` / `8.01`
- there are rare real `9.01`-only guidance leaks

### True guidance confirmation

Within that candidate set, call it guidance only if there is actual forward company expectation, for example:

- raise / lower / maintain / reaffirm / update / withdraw guidance
- outlook / forecast / preliminary results / pre-announcement
- expects revenue / EPS / EBITDA / margin / capex / sales / free cash flow
- a clear future period like `Q2`, `FY2026`, `next quarter`, `full year`

Reject it if it is only:

- conference call scheduling
- investor presentation with no new outlook
- prepared remarks with no new forecast
- safe-harbor boilerplate
- historical results only

### Best production rule

`guidance_candidate = 2.02 OR 7.01 OR 8.01 OR (9.01_only AND EX_99x)`

`guidance_true = guidance_candidate AND (Haiku says FINANCIAL_GUIDANCE OR explicit forward-metric signal)`

Most important nuance:

- do **not** label every `2.02` as true guidance
- but do fetch every `2.02` for the guidance extractor, because many earnings releases contain guidance and missing them is worse than over-fetching

### INVESTOR_PRESENTATION → also feed to guidance extraction

Haiku-classified INVESTOR_PRESENTATION filings (~280) should also go to the guidance extraction pipeline as recall insurance.

**Why:** Haiku has a ~5% miss rate. Some presentations that contain new financial targets get tagged INVESTOR_PRESENTATION instead of GUIDANCE. Feeding all ~280 to extraction catches these misses.

**Cost:** ~$140 total (280 × ~$0.50). Negligible.

**Risk:** Zero. The extraction LLM returns empty if no guidance is found. No false data produced.

**The fuzzy boundary problem:** 100% accurate separation of INVESTOR_PRESENTATION from GUIDANCE is impossible because the boundary is semantic:

```
CLEARLY PRESENTATION (no guidance):
  "Updated corporate overview deck for healthcare conferences"

CLEARLY GUIDANCE:
  "Company raises full-year revenue outlook to $50-52B"

FUZZY MIDDLE (can't tell without reading every slide):
  "Long-term financial framework: 5-7% revenue growth, 20%+ margins"
  → New targets? Or the same slide from last year's deck?

  "Investor Day: 2027 targets of $10B revenue, $3.00 EPS"
  → Were these targets just set? Or recycled?
```

Rather than engineering complex rules to separate these, just send both to the extraction pipeline. The extraction LLM is the precision gate.

### Updated guidance fetch formula

```
ALWAYS PROCESS (send to guidance extraction pipeline):
  ✓ All Item 2.02 filings (earnings press releases)
  ✓ All Haiku-classified GUIDANCE from 7.01/8.01
  ✓ All Haiku-classified INVESTOR_PRESENTATION         ← $140 recall insurance
  ✓ Keyword rescue on remaining 7.01/8.01:
    'guidance', 'outlook', 'preliminary results', 'pre-announce',
    'revised outlook', 'updated outlook', 'expects revenue',
    'expects earnings', 'full-year outlook', 'raises guidance',
    'lowers guidance', 'reaffirms guidance'

SKIP:
  ✗ Everything else (5.02, 5.07, 1.01, 2.03, etc.)

Expected: ~100% recall, extraction LLM handles precision
```

### Honest estimates: INVESTOR_PRESENTATION → real GUIDANCE detection

Conservative, realistic estimates for this specific sub-task: "does this investor presentation filing contain real guidance worth sending to guidance extraction?"

**Haiku alone (strong prompt):**

| Metric | Range |
|---|---|
| Recall | ~80-90% |
| Precision | ~75-85% |

**Haiku + explicit forward-target check (strong prompt + evidence span + numeric/forward-target confirmation):**

| Metric | Range |
|---|---|
| Recall | ~88-95% |
| Precision | ~85-93% |

**Why not higher?** Investor presentations are messy:

- Some repeat old guidance (recycled slides from prior quarter)
- Some contain only broad strategy with no numbers
- Some imply outlook without explicit targets ("we see continued momentum")
- Some mix presentation content with other filing content
- Some "guidance-like" language is just boilerplate safe-harbor text

Even with a strong prompt, Haiku will still make mistakes on these edge cases.

**Honest bottom line for investor presentations specifically:**

- Haiku alone: useful but not reliable enough to trust blindly
- Haiku + explicit target check: good enough as a cheap prefilter, still not 100/100
- **Plan around: ~90% recall and ~90% precision** using strong Haiku prompt + numeric forward-guidance confirmation

This is exactly why we send ALL INVESTOR_PRESENTATION to the guidance extraction pipeline ($140 insurance) rather than trying to pre-filter within this category. The extraction LLM is the final precision gate — it reads the full content and returns empty if no real guidance exists.

---

## Storage: Haiku Tags on Report Nodes

Tags are 1:1 with the filing — every filing gets exactly one classification. No separate nodes needed. Store as properties on the Report node (same pattern as `market_session`, `formType`).

```
Report node — add 3 properties:
  haiku_primary:    String    'EARNINGS'
  haiku_secondary:  String    '["GUIDANCE","BUYBACK"]'  (JSON array, same as items)
  haiku_confidence: Double    0.96
```

Query examples:

```cypher
// All guidance filings
MATCH (r:Report {formType: '8-K'})
WHERE r.haiku_primary = 'FINANCIAL_GUIDANCE'
   OR r.haiku_secondary CONTAINS 'FINANCIAL_GUIDANCE'
RETURN r.accessionNo, r.created

// Earnings with secondary buyback
MATCH (r:Report {haiku_primary: 'EARNINGS'})
WHERE r.haiku_secondary CONTAINS 'BUYBACK'
RETURN r.accessionNo
```

---

## 2. Historical Coverage-Gap Search That Motivated The Frozen Taxonomy

This section explains why the frozen taxonomy in Section 1A exists.

Earlier drafts used a much smaller tag set and produced too much `OTHER`. The gap search across the 8-K corpus showed that several real event families needed to be promoted into the production taxonomy, especially `SHAREHOLDER_VOTE`, `SECURITIES_OFFERING`, `PRODUCT_PIPELINE`, and `ADMINISTRATIVE_ONLY`.

### Coverage gaps found

The gap search showed that the earlier compact taxonomy was missing several real event families, especially:

- shareholder-vote filings that deserved their own tag rather than broad governance
- securities-offering / ATM type filings that were neither clean debt nor generic agreements
- product / pipeline milestone filings, especially in healthcare
- purely administrative exhibit / disclosure updates that should not be forced into a business-event bucket

That evidence is why the frozen taxonomy in Section 1A now includes `SHAREHOLDER_VOTE`, `SECURITIES_OFFERING`, `PRODUCT_PIPELINE`, and `ADMINISTRATIVE_ONLY`.

### Updated Haiku prompt

```text
Classify this 8-K into one primary and zero or more secondary event types.

Use the canonical event taxonomy from Section 1A.

Return JSON only:
{"primary_event": "...", "secondary_events": [...], "confidence": 0.0-1.0}
```

### Which tags need Haiku vs deterministic rules

```
Use the split already frozen in Section 1A:

- deterministic supplemental tags are assigned directly from item codes
- Haiku is used only for the prompt-routed semantic tags on ambiguous filings
```

---

## 3. Guidance-Specific 8-K Fetch Strategy

Guidance can appear in exactly three places in 8-K filings:

```
1. Item 2.02 (Earnings press release)
   → "We expect Q3 revenue of $94-98B"
   → EX-99.1 contains the outlook section
   → 8,847 filings. Not all have guidance (some companies don't guide)

2. Item 7.01 (Reg FD) WITHOUT 2.02
   → Mid-quarter guidance revision, pre-announcement
   → ~3,782 filings total, only ~149 contain actual guidance

3. Item 8.01 (Other Events) WITHOUT 2.02
   → Rare guidance updates
   → ~15 filings with guidance
```

Guidance does NOT appear in other item codes (5.02, 5.07, 1.01, 2.03, etc.).

### Why 100%/100% is not achievable with metadata alone

"Guidance" is a semantic concept — you have to read the text to know if it's there. A filing can have Item 7.01 and be an investor presentation with zero forward-looking numbers. Another 7.01 can be a full guidance revision. The item code can't tell you which.

### The 3-stage approach (practical ~99.5% recall, ~100% precision)

```
Stage 1: ITEM CODE FILTER (100% recall, ~5% precision)
  Process ALL of these:
    ✓ Every Item 2.02 filing                       → 8,847 filings
    ✓ Every Item 7.01 filing (without 2.02)         → 3,782 filings
    ✓ Every Item 8.01 filing (without 2.02)         → 3,949 filings
                                                     ─────────────
    Total superset:                                  ~16,578 filings
  No guidance filing can escape this net.

Stage 2: HAIKU + KEYWORD RESCUE (~99.5% recall, ~95% precision)
  For 2.02: always process (guidance lives in EX-99.1)
  For 7.01/8.01: Haiku classifies → GUIDANCE tag
  Keyword rescue for Haiku misses (~5%):
    'guidance', 'outlook', 'preliminary results', 'pre-announce',
    'revised outlook', 'updated outlook', 'expects revenue',
    'expects earnings', 'full-year outlook', 'raises guidance',
    'lowers guidance', 'reaffirms guidance'
  Route formula: Haiku_yes OR keyword_rescue_yes

Stage 3: EXTRACTION LLM (~99.5% recall, ~100% precision)
  Reads full EX-99.1 / section content
  Extracts structured guidance (ranges, metrics, periods)
  Returns empty if no guidance found → false positives produce no data
```

### Implementation

```python
def should_extract_guidance(filing):
    items = filing.items

    # Always process earnings — guidance lives in the press release
    if 'Item 2.02' in items:
        return True

    # Haiku-gate Reg FD and Other Events
    if 'Item 7.01' in items or 'Item 8.01' in items:
        haiku_result = classify_with_haiku(filing)
        if 'FINANCIAL_GUIDANCE' in haiku_result.categories:
            return True
        # Rescue: keyword fallback for Haiku misses (~5%)
        if has_guidance_keywords(filing.content):
            return True

    return False

def has_guidance_keywords(text):
    keywords = [
        'guidance', 'outlook', 'preliminary results',
        'pre-announce', 'revised outlook', 'updated outlook',
        'expects revenue', 'expects earnings', 'full-year outlook',
        'raises guidance', 'lowers guidance', 'reaffirms guidance'
    ]
    return any(kw in text.lower() for kw in keywords)
```

### Why the extraction LLM handles precision

The pipeline already has an LLM that reads content and extracts structured guidance. If no guidance is present, it returns empty. So false positives don't produce wrong data — they just waste tokens. The ONLY thing that matters for the fetch stage is RECALL. Precision is the extraction LLM's job.

---

## How to Read This Document

| Part | What | Source | Start With |
|---|---|---|---|
| **I** | Intuitive 8-K walkthrough (Layers 1-4B) | Claude 1 | If learning 8-K structure |
| **II** | Extraction architecture & per-type specs | Claude 2 | If building pipelines |
| **III** | Stock impact & predictive analysis (Layers 5-8) | Claude 1 | If evaluating what matters |
| **IV** | Independent database validation & Haiku safety | Codex 2 | If validating methodology |
| **V** | Combined conclusions | All | If you want the bottom line |

---

## Final Bottom Line (from all three analyses)

- **Guidance extraction pipeline** — already built, keep it. Single most valuable input.
- **Build a $15 Haiku event timeline** — classify all non-earnings 8-Ks. Tags, not full extraction.
- **Restructuring + litigation** — the two highest-value new extraction types (if building more).
- **Haiku is useful but not safe alone** — misses ~30-35% of buybacks/dividends (Codex finding). Hybrid wins.
- **The amplifier effect** — restructuring/exec changes AT earnings amplify reactions 28-39%. Prior restructuring is the ONLY event proven to predict worse subsequent earnings (+20%).
- **Transparency effect** — more inter-quarter filings = less earnings surprise (monotonic -23%).
- **Don't build separate pipelines** for buybacks, dividends, M&A, debt — the earnings press release already contains them.

---
---

# Part I: Intuitive 8-K Walkthrough (Claude Session 1)

> Bite-sized explanations for grokking the entire 8-K structure. Each layer builds on the previous.

## Layer 1: The Newspaper Analogy — What Is an 8-K?

Think of a company as a person, and the SEC as the government.

The government says: **"Any time something important happens to you, you must file a report within 4 business days."**

That report is an **8-K**. It's a **breaking news alert** filed with the government.

```
10-K  = Annual physical        (once a year, comprehensive health check)
10-Q  = Quarterly checkup      (every 3 months, lighter version)
8-K   = Emergency room visit   (something just happened, report NOW)
```

**In our database:**
- 23,836 emergency room visits (8-K filings)
- 514 corrected reports (8-K/A amendments — "we made an error in our earlier report")

The critical thing: A 10-K or 10-Q is predictable (you know when it's coming). An 8-K is unpredictable — it fires when an EVENT happens. That's why 8-Ks are the most market-moving filing type.

---

## Layer 2: The Event Label System — Item Codes

When you go to the emergency room, the doctor writes a **diagnosis code** on your chart. "Broken arm" = one code. "Allergic reaction" = another.

The SEC works the same way. When a company files an 8-K, it must label it with one or more **Item codes** that say what happened. Think of them as **event tags**.

### Counting It Right — Sections vs Item Codes

Don't confuse these three things:

```
9 SECTIONS    = broad categories the SEC groups events into
                (Section 1, 2, 3, 4, 5, 6, 7, 8, 9)
                All 9 exist in the SEC spec. Section 6 (ABS) has 0 filings in our data.

31 ITEM CODES = the specific event types WITHIN those sections
                (1.01, 1.02, 1.03, ... 9.01)
                The SEC defines 31 total across all 9 sections.

26 ACTIVE     = the ones that actually appear in our 23,836 filings
                (5.06 and 6.01–6.05 have zero filings because our
                 796 companies include no shell companies or ABS issuers)
```

The relationship is simple: **Sections are folders. Item codes are files inside the folders.**
Section 2 (Financial Information) contains 6 item codes: 2.01, 2.02, 2.03, 2.04, 2.05, 2.06.

The SEC organized all possible corporate events into **9 sections** (Section 6 is for asset-backed securities and has 0 filings in our universe):

```
Section 1: Registrant's Business and Operations
Section 2: Financial Information
Section 3: Securities and Trading Markets
Section 4: Matters Related to Accountants and Financial Statements
Section 5: Corporate Governance and Management
Section 7: Regulation FD
Section 8: Other Events
Section 9: Financial Statements and Exhibits
```

Within each section, specific event types are numbered (the ".XX" part). Here is the complete list with exact SEC names and intuitive analogies:

### Section 1 — Registrant's Business and Operations

```
1.01  Entry into a Material Definitive Agreement
      → "Signed a big contract" (credit facility, M&A deal, license)

1.02  Termination of a Material Definitive Agreement
      → "Ended a big contract" (often paired with 1.01 for replacements)

1.03  Bankruptcy or Receivership
      → "Flatlined" (Chapter 7/11 filing — only 1 in our database)

1.04  Mine Safety – Reporting of Shutdowns and Patterns of Violations
      → "Workplace injury report" (Dodd-Frank mandate for mining companies)

1.05  Material Cybersecurity Incidents
      → "Got hacked" (new SEC rule, effective Dec 2023 — only 12 filings)
```

### Section 2 — Financial Information

```
2.01  Completion of Acquisition or Disposition of Assets
      → "Bought or sold a business" (M&A deal closing)

2.02  Results of Operations and Financial Condition                    ⭐
      → "Quarterly blood test results" — THIS IS EARNINGS
      → The single most important 8-K type. 8,847 filings (37%)

2.03  Creation of a Direct Financial Obligation or an Obligation
      under an Off-Balance Sheet Arrangement of a Registrant
      → "Got a mortgage" (new debt — bonds, credit lines)

2.04  Triggering Events That Accelerate or Increase a Direct
      Financial Obligation or an Obligation under an Off-Balance
      Sheet Arrangement
      → "Missed a mortgage payment" (debt covenant triggers)

2.05  Costs Associated with Exit or Disposal Activities
      → "Paying for the divorce" (restructuring charges, layoffs, closures)

2.06  Material Impairments
      → "House lost value" (goodwill write-downs, asset impairments)
```

### Section 3 — Securities and Trading Markets

```
3.01  Notice of Delisting or Failure to Satisfy a Continued Listing
      Rule or Standard; Transfer of Listing
      → "Evicted from the neighborhood" (exchange delisting or transfer)

3.02  Unregistered Sales of Equity Securities
      → "Sold shares to a friend" (private placements, not public offerings)

3.03  Material Modification to Rights of Security Holders
      → "Rewrote the HOA rules" (charter changes affecting stock rights)
```

### Section 4 — Matters Related to Accountants and Financial Statements

```
4.01  Changes in Registrant's Certifying Accountant
      → "Switched doctors" (auditor change — e.g., Deloitte to PwC)

4.02  Non-Reliance on Previously Issued Financial Statements or a
      Related Audit Report or Completed Interim Review
      → "Old blood tests were wrong" (restatement red flag)
```

### Section 5 — Corporate Governance and Management

```
5.01  Changes in Control of Registrant
      → "New owner" (mergers, buyouts, activist takeovers)

5.02  Departure of Directors or Certain Officers; Election of
      Directors; Appointment of Certain Officers; Compensatory
      Arrangements of Certain Officers
      → "New or departing doctor" (executive/board changes, comp amendments)

5.03  Amendments to Articles of Incorporation or Bylaws;
      Change in Fiscal Year
      → "Rewrote the house rules" (governance structure changes)

5.04  Temporary Suspension of Trading Under Registrant's Employee
      Benefit Plans
      → "401(k) blackout" (employees temporarily can't trade company stock)

5.05  Amendments to the Registrant's Code of Ethics, or Waiver of
      a Provision of the Code of Ethics
      → "Updated the code of conduct" (ethics policy changes/waivers)

5.06  Change in Shell Company Status
      → Not in our universe (0 filings — no shell companies tracked)

5.07  Submission of Matters to a Vote of Security Holders
      → "Election day results" (shareholder vote tallies from annual meetings)

5.08  Shareholder Director Nominations
      → "Candidates announced" (board nominations under universal proxy rules)
```

### Section 7 — Regulation FD

```
7.01  Regulation FD Disclosure
      → "Press conference" (publicly sharing material info — investor
         presentations, guidance updates, pre-announcements)
```

### Section 8 — Other Events

```
8.01  Other Events
      → "Anything else important" (catch-all: restructurings, buybacks,
         strategic updates, litigation — whatever doesn't fit elsewhere)
```

### Section 9 — Financial Statements and Exhibits

```
9.01  Financial Statements and Exhibits
      → "See attached paperwork" (companion tag — just says documents
         are attached. NOT meaningful on its own. Appears in 79% of 8-Ks)
```

### The Distribution — Not All Events Are Equal

In our 23,836 filings, the distribution is wildly skewed:

```
THE BIG FOUR (appear in 20%+ of all 8-Ks):
  ██████████████████████████████████████████  9.01  79%  (just says "docs attached")
  ███████████████                            2.02  37%  (EARNINGS)
  ██████████                                 7.01  24%  (public disclosure)
  ████████                                   5.02  21%  (exec changes)

THE MIDDLE TIER (5–20%):
  ████████                                   8.01  20%  (other events)
  ████                                       1.01  11%  (new contracts)
  ████                                       5.07  10%  (voting)
  ██                                         2.03   6%  (new debt)

EVERYTHING ELSE: under 4% each
  5.03  3.5%  (bylaws)
  3.02  1.3%  (private stock sales)
  1.02  1.2%  (contract terminations)
  ...
  1.03  0.004%  (bankruptcy — literally 1 filing)
```

**Takeaway:** If you only understood Items 2.02, 7.01, 5.02, 8.01, 1.01, and 9.01, you'd cover 90%+ of all 8-K filings in the database.

### Key Clarification: Item 9.01 Is Not an Event

Item 9.01 is never the event itself — it's a mandatory checkbox the company ticks to say "we attached files (exhibits) to this filing." That's why it appears in 79% of all 8-Ks as a silent companion to the real event items. When you see a filing with Items `2.02 + 9.01`, the event is 2.02 (earnings); the 9.01 just means "the press release is attached as an exhibit."

### Key Clarification: EX-99.1 Is Not an Item Code — It's an Exhibit

Item codes (1.01, 2.02, etc.) tell you **what happened**. Exhibits (EX-99.1, EX-10.1, etc.) are the **actual documents attached** to the filing. EX-99.1 is the most common exhibit — it's almost always the **press release** that contains the real narrative content (earnings results, guidance numbers, financial tables). When Item 9.01 says "documents attached," EX-99.1 is what it's pointing to. This distinction (item codes = event labels, exhibits = attached documents) is covered in Layer 3.

---

## Layer 3: What's Physically Inside an 8-K Filing?

An 8-K is like a **physical manila folder** dropped off at the SEC's front desk. Open it and you find three things:

```
┌─────────────────────────────────────────────────┐
│                 THE 8-K FOLDER                   │
│                                                  │
│  1. COVER PAGE (the item checkboxes)             │
│     ☑ Item 2.02 — Results of Operations          │
│     ☑ Item 9.01 — Financial Statements/Exhibits  │
│                                                  │
│  2. BODY TEXT (one short paragraph per item)      │
│     "On Jan 30, Apple issued a press release     │
│      regarding Q1 results. A copy is furnished   │
│      as Exhibit 99.1 to this report."            │
│                                                  │
│  3. STAPLED ATTACHMENTS (the actual documents)   │
│     📎 EX-99.1: [24-page press release with      │
│                   revenue, EPS, tables, guidance] │
│     📎 EX-99.2: [Supplemental data tables]       │
└─────────────────────────────────────────────────┘
```

### How these map to our database

```
Cover page       →  Report.items field        (the item codes — Layer 2)
Body text        →  ExtractedSectionContent   (we call these "Sections")
Attachments      →  ExhibitContent            (we call these "Exhibits")
```

### Dual storage: Properties vs Linked Nodes

The same content is stored TWICE in Neo4j:

```
REPORT NODE (compact copies)
├── .exhibit_contents     = JSON string blob   ← denormalized snapshot
├── .extracted_sections   = JSON string blob   ← denormalized snapshot
│
├──[:HAS_EXHIBIT]──→ ExhibitContent node       ← exploded, queryable
└──[:HAS_SECTION]──→ ExtractedSectionContent   ← exploded, queryable
```

The properties on the Report node are compact JSON snapshots (for quick glance). The linked nodes are the exploded, individually queryable version (with fulltext indexes for search). **We always use the linked nodes, never the properties.**

### The pointer pattern: Sections are not always the content

Whether the section (body text) IS the real content or just a pointer depends on the item type:

```
SECTION IS A POINTER (exhibit has the full version):

  Item 2.02 (Earnings) section:    avg 1 KB
    "Apple issued a press release. See Exhibit 99.1."
    → Real content: EX-99.1 press release (avg 24 KB)

  Item 7.01 (Reg FD) section:     avg 1.5 KB
    "The Company is furnishing the investor presentation
     as Exhibit 99.1."
    → Real content: EX-99.1 presentation (avg 24 KB)

SECTION IS A SUMMARY (exhibit has full legal text):

  Item 1.01 (Agreement) section:   avg 4.4 KB
    "The Company entered into a Credit Agreement dated
     Feb 28 providing for a $2B revolving facility..."
    → Full contract: EX-10.1 (avg 205 KB)

SECTION IS THE CONTENT (no exhibit needed):

  Item 5.07 (Voting) section:      avg 2.6 KB
    "At the annual meeting held March 1, directors were
     elected with the following vote tallies: ..."
    → 79% have NO exhibit at all

  Item 5.02 (Exec changes) section: avg 2.4 KB
    "On March 1, John Smith resigned as CFO. Jane Doe
     was appointed. Annual salary $850K, signing bonus $1.2M..."
    → 43% have NO exhibit
```

### The two exhibit families

Exhibits use a numbering system. The number tells you what kind of document it is:

```
"99" SERIES = NARRATIVE DOCUMENTS
  EX-99.1  = Press release                    (14,199 in DB, avg 24 KB)
  EX-99.2  = Investor presentation / suppl.   (2,676 in DB, avg 33 KB)
  EX-99.3+ = Additional press materials       (361+ in DB)

"10" SERIES = LEGAL DOCUMENTS
  EX-10.1  = Primary contract / agreement     (2,341 in DB, avg 205 KB)
  EX-10.2  = Secondary contract               (591 in DB, avg 114 KB)
  EX-10.3+ = Additional contracts             (231+ in DB)
```

These are **generic** — any item code can have any exhibit stapled to it. But in practice:
- Earnings filings (2.02) almost always get EX-99.1 (press release)
- Contract filings (1.01) almost always get EX-10.1 (the agreement)

101 distinct exhibit numbers exist in the database, but the top 6 cover 95%+ of all exhibits. The long tail includes dirty variants like `EX-99.-1`, `EX-99.01`, `EX-10.EXECSEVPLAN` from sloppy filers.

### The content fetch strategy (corrected — not as simple as "exhibit wins")

The oversimplified rule "exhibit wins, section is fallback" breaks down on multi-item filings and edge cases. The real picture has four cases:

```
Case 1: Section is a pointer (Item 2.02 earnings — 99.7% of 8,126 filings)
  Section (avg 322 B–899 B): "See Exhibit 99.1"
  Exhibit (avg 31 KB):        [full press release]
  → Exhibit is sufficient for THIS item
  → But check for OTHER sections on the same filing (see Case 3)

Case 2: Section adds context not in exhibit (documented in extraction rules)
  Section: "Revenue guidance of $94-98B, subject to tariff resolution"
  Exhibit: "Revenue guidance of $94-98B"
  → Section adds a condition not found in the exhibit
  → Extraction pipeline captures this via the `conditions` field
  Source: 8k-primary.md: "Section may add context — annotate in conditions field"

Case 3: Section and exhibit cover DIFFERENT events (910+ multi-item filings)
  Filing has Items 2.02 + 8.01 + 9.01
  Exhibit EX-99.1 (31 KB): [earnings press release — covers Item 2.02]
  Section "OtherEvents" (avg 1.2 KB): [share buyback — covers Item 8.01]
  → They cover COMPLETELY DIFFERENT events
  → Ignoring the section = losing the buyback info entirely
  → Each section maps to ONE item code; exhibits may map to a DIFFERENT item

Case 4: Section IS the main document (786 filings, mostly Item 1.01)
  Filing has Item 1.01
  Section (avg 4.4 KB, up to 40 KB): [full merger agreement text]
  Exhibit EX-99.1 (avg 23 KB):       [press release announcing the deal]
  → Section has the legal contract, exhibit has the announcement
  → Neither is a subset of the other — they're complementary
```

**The corrected rule:**

1. Always fetch BOTH sections and exhibits
2. Exhibits are primary for the item they cover (e.g., EX-99.1 for earnings)
3. Sections for OTHER items on the same filing are independent content — never skip them
4. Even same-topic sections may add conditions/context not in the exhibit
5. Only skip a section if it's literally a one-line pointer ("see Exhibit 99.1")

### There's also a rare fallback layer

Beyond sections and exhibits, 494 filings (2%) have a third layer:

```
FilingTextContent  = Raw full filing HTML (avg 690 KB)
                     Used ONLY when section/exhibit parsing failed.
                     It's the entire filing as one giant text blob.
```

And one layer that NEVER appears on 8-Ks:

```
FinancialStatementContent = Structured JSON financial statements
                            ONLY exists on 10-K and 10-Q filings.
                            Zero instances on any 8-K in the database.
```

### Content layer distribution across all 23,836 8-Ks

```
Exhibit + Section:                 15,643   65.6%   (exhibit has the goods)
Section only:                       7,648   32.1%   (section IS the goods)
Exhibit + Section + Filing Text:      329    1.4%   (parsing partly failed)
Section + Filing Text:                165    0.7%   (parsing partly failed)
Exhibit only (no section):             28    0.1%   (rare anomaly)
Neither:                               23    0.1%   (empty filing)
```

### Deep dive: Where exhibit numbers actually come from

The exhibit numbering system is NOT specific to 8-K filings. It comes from a universal SEC classification system defined in **Regulation S-K, Item 601** — a master table of ~40 formal exhibit types used across ALL filing types (8-K, 10-K, 10-Q, S-1, etc.).

#### The SEC's Master Exhibit Table (Item 601)

```
EX-1    Underwriting agreement
EX-2    Plan of acquisition/reorganization/liquidation
EX-3    (i) Articles of incorporation  (ii) Bylaws
EX-4    Instruments defining rights of security holders
EX-5    Opinion re legality
EX-7    Correspondence from independent accountant
EX-8    Opinion re tax matters
EX-9    Voting trust agreement
EX-10   MATERIAL CONTRACTS                              ← "EX-10.x" comes from here
EX-13   Annual/quarterly report to security holders
EX-14   Code of ethics
EX-15   Letter re unaudited interim financial info
EX-16   Letter re change in certifying accountant
EX-17   Correspondence on departure of director
EX-18   Letter re change in accounting principles
EX-19   Insider trading policies
EX-20   Other documents to security holders
EX-21   Subsidiaries of registrant
EX-22   Subsidiary guarantors
EX-23   Consents of experts and counsel
EX-24   Power of attorney
EX-25   Statement of eligibility of trustee
EX-31   CEO/CFO certifications (SOX Section 302)
EX-32   CEO/CFO certifications (SOX Section 906)
EX-33   Report on servicing criteria
EX-34   Attestation report on servicing
EX-95   Mine safety disclosure
EX-96   Technical report summary
EX-97   Clawback policy
EX-98   Reports in de-SPAC transactions
EX-99   ADDITIONAL EXHIBITS                              ← "EX-99.x" comes from here
EX-101  Interactive data (XBRL)
EX-104  Cover page interactive data
EX-107  Filing fee table
```

**Critical insight:** EX-99 is formally called "Additional Exhibits" — a catch-all bucket for anything that doesn't fit the other categories. It is NOT formally defined as "press releases." Companies put press releases there by convention, which is why 14,199 of our EX-99.1s are press releases. But there's no SEC rule mandating this.

#### The sub-numbering convention (.1, .2, .3)

The `.1`, `.2`, `.3` suffix is NOT a formal SEC designation. It's a filing convention meaning "first attachment of this type, second, third..."

```
EX-99.1 = "first additional exhibit"    (by convention: the press release)
EX-99.2 = "second additional exhibit"   (by convention: investor presentation)
EX-99.3 = "third additional exhibit"    (whatever else)

EX-10.1 = "first material contract"     (the primary agreement)
EX-10.2 = "second material contract"    (amendment or secondary deal)
```

This also explains the dirty variants (`EX-99.01`, `EX-99.-1`, `EX-10.EXECSEVPLAN`) — filers can number however they want within the type. There is no enforcement.

#### Which exhibit types actually appear on 8-K filings?

Of the ~40 exhibit types, Item 601's table marks only a handful as applicable to 8-K:

```
RELEVANT TO 8-K:
  EX-2     Plan of acquisition         → pairs with Item 2.01
  EX-4     Instruments defining rights  → pairs with Item 3.03
  EX-10    Material contracts           → pairs with Item 1.01
  EX-17    Director departure letter    → pairs with Item 5.02
  EX-99    Additional exhibits (catch-all) → pairs with ANYTHING
  EX-104   Cover page interactive data  → mechanical/XBRL

NOT RELEVANT TO 8-K (these live on 10-K/10-Q/S-1):
  EX-21    Subsidiaries
  EX-23    Consents
  EX-31/32 SOX certifications
  EX-101   XBRL interactive data
  etc.
```

Our database confirms: 95%+ of 8-K exhibits are EX-99.x or EX-10.x.

### Filed vs Furnished — The legal status layer

A hidden dimension most people miss. Not all 8-K content has the same legal weight:

```
FURNISHED (lower liability — NOT subject to Section 18 of the Exchange Act):
  Item 2.02  Results of Operations     → exhibits are FURNISHED
  Item 7.01  Regulation FD             → exhibits are FURNISHED

FILED (full liability — subject to Section 18):
  ALL OTHER ITEMS (1.01, 5.02, 8.01, etc.) → exhibits are FILED
```

Exhibits inherit the filed/furnished status of their parent item code. The **same** EX-99.1 press release has different legal status depending on which item it's attached to:
- EX-99.1 on a 2.02 filing → FURNISHED (company has less legal exposure)
- EX-99.1 on an 8.01 filing → FILED (company has full Section 18 liability)

This is why companies route earnings through Item 2.02 specifically — it gives them the "furnished" shield.

**Note for extraction pipeline:** Filed/furnished status doesn't currently affect what gets extracted (guidance is extracted regardless), but it's correct metadata that could matter for other use cases.

### The natural pairings (Item Code → Exhibit Type → Legal Status)

```
Item 2.02 (Earnings)        → EX-99.1 (press release)     FURNISHED
Item 7.01 (Reg FD)          → EX-99.1 (presentation)      FURNISHED
Item 1.01 (Agreement)       → EX-10.1 (contract)          FILED
Item 5.02 (Officer change)  → EX-10.x (employment agmt)   FILED
Item 8.01 (Other)           → EX-99.1 (varies)            FILED
Item 2.01 (Acquisition)     → EX-2   (acquisition plan)   FILED
```

### The complete mental model (three coordinates)

An 8-K filing needs THREE coordinates to fully understand any piece of content:

1. **Item Code** — what event happened (the trigger, from 31 SEC event types)
2. **Exhibit Type** — where the extractable content lives (from Item 601 table)
3. **Filed/Furnished status** — legal weight of the content (inherited from item code)

```
8-K FILING
│
├── ITEM CODE(s)  ← WHAT happened (event classification)
│   │                31 types across 9 sections
│   │                Determines: filed vs furnished status
│   │
│   ├── SECTION(s) ← Brief body text per item (ExtractedSectionContent)
│   │                 Often just a pointer: "see Exhibit 99.1"
│   │                 Sometimes IS the content (Item 5.07, 5.02)
│   │
│   └── EXHIBIT(s) ← Attached documents (ExhibitContent)
│                     TYPE = what kind of document (from Item 601 table)
│                     SEQUENCE = .1, .2, .3 (first, second, third of that type)
│
│       Only 2 families matter for 8-K:
│       ├── EX-99.x = "Additional exhibits" (narrative: press releases, decks)
│       └── EX-10.x = "Material contracts" (legal: agreements, plans)
│
│       Rare:
│       ├── EX-2    = Acquisition plans
│       ├── EX-4    = Instruments defining rights
│       └── EX-17   = Director departure correspondence
│
└── Item 9.01 ← NOT an event. Just a checkbox: "exhibits are attached"
                 Appears in 79% of 8-Ks as a companion tag
```

---

## Layer 4: How Items Combine in Real Filings

A single corporate event often triggers multiple item codes because one action has multiple consequences — like a hospital visit where you broke your arm AND discovered high blood pressure. The doctor codes both.

### The 9.01 tax

Before reading any combination, mentally subtract Item 9.01. It appears in 79% of filings and just means "we attached documents." Zero information about what happened.

```
Filing says: [Item 2.02, Item 9.01]
You read:    Item 2.02 (earnings)

Filing says: [Item 1.01, Item 2.03, Item 9.01]
You read:    Item 1.01 + Item 2.03 (contract + debt)
```

### The distribution — most filings have multiple items

```
1 item:   ████                 18.6%   (relatively rare)
2 items:  ██████████████████   52.9%   (most common — typically event + 9.01)
3 items:  █████████            22.4%
4+ items: ███                   6.1%
```

81% of 8-Ks have 2+ items. The most common pattern is 2 items (the event + 9.01 companion tag).

### The five patterns that cover 90% of all filings

**Pattern 1: Solo earnings (6,157 filings — 26% of all 8-Ks)**
```
Items: [2.02 + 9.01]

What happened: Company reported quarterly results. Clean, simple.
Content:       EX-99.1 has the press release.
```

**Pattern 2: Earnings + investor deck (1,468 filings — 6%)**
```
Items: [2.02 + 7.01 + 9.01]

What happened: Company reported earnings AND shared an investor
               presentation or supplemental data under Reg FD.
Content:       EX-99.1 = press release (earnings)
               EX-99.2 = investor presentation or data tables

This is the RICHEST earnings filing — two documents instead of one.
```

**Pattern 3: Governance events (5,103+ filings across various combos)**
```
Items: [5.02]                  ← 1,583 filings (standalone, no exhibit)
Items: [5.02 + 9.01]          ← 1,350 filings (with employment agreement)
Items: [5.07]                  ← 1,186 filings (standalone voting results)
Items: [5.02 + 5.07 + 9.01]   ← 301 filings (officer changes + voting)

What happened: Executive hired/fired, shareholders voted, or both.
Content:       Sections have details directly.
               Exhibits (when present) are employment contracts.

Note: 5.02 and 5.07 often appear WITHOUT 9.01 — they frequently
don't need attached documents. Data lives in the section body.
```

**Pattern 4: Deals and debt (705+ filings)**
```
Items: [1.01 + 2.03 + 9.01]         ← 705 filings
Items: [1.01 + 1.02 + 2.03 + 9.01]  ← 96 filings
Items: [1.01 + 9.01]                 ← 378 filings

What happened:
  1.01       = "We signed a new credit agreement"
  2.03       = "That agreement created a debt obligation"
  1.02       = "We terminated the old agreement" (refinancing)

The 1.01+2.03 pair = classic "took on new debt" signal.
Add 1.02 and it's a REFINANCING (killed old deal, signed new one).

Content:       EX-10.1 = the actual contract (205 KB avg)
               EX-99.1 = press release announcing it (if present)
```

**Pattern 5: Other material events (1,996+ filings)**
```
Items: [8.01 + 9.01]   ← 1,996 filings
Items: [7.01 + 9.01]   ← 1,587 filings
Items: [8.01]           ← 712 filings (no exhibit)

What happened: Something material that doesn't fit other categories.
               Could be: restructuring, buyback, litigation update,
               strategic initiative, pre-announcement, guidance revision.
Content:       Highly variable — could be section-only or exhibit-heavy.
```

### How to decode any combination

```
Step 1: Cross out 9.01 (it's just "docs attached")
Step 2: Each remaining item = one event or consequence
Step 3: Look for natural pairs:

  1.01 + 2.03          = "signed contract that created debt"
  1.01 + 1.02          = "replaced one contract with another"
  1.01 + 2.01          = "signed deal, acquisition completed"
  2.02 + 7.01          = "earnings + investor presentation"
  2.02 + 8.01          = "earnings + some other material event"
  5.02 + 5.07          = "officer changes + shareholder vote"
  5.03 + 5.07          = "bylaw change approved by vote"
  1.01 + 1.02 + 2.03   = "refinanced debt"
```

### The extreme cases — transformative events

Some filings have 6+ items. These are major corporate events:

```
[1.01, 1.02, 2.01, 2.03, 3.01, 3.03, 5.01, 5.02, 5.03, 8.01, 9.01]
= 11 items = a MERGER or ACQUISITION closing

Reading: signed new agreements (1.01), terminated old ones (1.02),
completed acquisition (2.01), took on debt (2.03), listing changed
(3.01), shareholder rights modified (3.03), control changed hands
(5.01), officers replaced (5.02), bylaws amended (5.03), other
stuff (8.01), documents attached (9.01).

One single event (a merger) triggering 10 different consequences.
```

**Key takeaway:** Items don't randomly combine — they reflect the natural consequences of a single corporate event. The combination IS the story.

---

## Layer 4B: Identifying Earnings Releases — Precision and Recall

### The standard test

```cypher
r.items CONTAINS 'Item 2.02'
```

This is the gold standard filter. But is it 100%/100%?

### Precision: "If it says 2.02, is it ALWAYS an earnings release?"

**~99%+ yes.** The SEC *requires* companies to use Item 2.02 when disclosing "Results of Operations and Financial Condition." If it's tagged 2.02, it IS a results disclosure by law.

The tiny precision gap — some Item 2.02 filings are:
- Preliminary/partial results (not a full quarterly report)
- Revenue pre-announcements
- Restatement-driven results updates

These are all technically "Results of Operations" per SEC rules, but you might not call them a "standard quarterly earnings release."

### Recall: "Are ALL earnings releases tagged 2.02?"

**~98%+ yes.** Edge cases:

```
Possible leaks:
  - Company reports results under Item 7.01 (Reg FD) instead of 2.02
    → Rare, technically non-compliant with SEC rules

  - Company buries results in Item 8.01 (Other Events)
    → Even rarer, would invite SEC scrutiny

  - Foreign private issuers file on Form 6-K, not 8-K
    → Their earnings never appear as Item 2.02 at all
    → But 6-K filings aren't in our 8-K universe
```

### What would 100%/100% require?

```
HIGH CONFIDENCE (what we do now):
  r.items CONTAINS 'Item 2.02'
  → ~99% precision, ~98% recall

HIGHER CONFIDENCE (add content verification):
  r.items CONTAINS 'Item 2.02'
  AND has EX-99.1 exhibit
  AND exhibit contains financial keywords (revenue, EPS, net income)
  → ~99.5% precision, ~97% recall (loses the 6.4% section-only filings)

MAXIMUM RECALL (catch leaks from 7.01/8.01):
  r.items CONTAINS 'Item 2.02'
  OR (r.items CONTAINS 'Item 7.01' AND exhibit mentions quarterly results)
  OR (r.items CONTAINS 'Item 8.01' AND exhibit mentions earnings)
  → Higher recall, but now you need NLP to verify content
```

### The practical answer

**`Item 2.02` alone is the right filter.** The edge cases (~1-2%) are so rare that NLP verification would cost more than it gains. Every major financial data provider (Bloomberg, S&P, Refinitiv) uses Item 2.02 as their primary earnings filing identifier.

The one thing to be aware of: not every Item 2.02 is a *standard quarterly* earnings release. Some are preliminary results, pre-announcements, or restatements. If you need to distinguish those, look at EX-99.1 content. But for the guidance extraction pipeline (which extracts guidance from any results disclosure), this distinction doesn't matter.

---


---
---

# Part II: Extraction Architecture & Per-Type Specs (Claude Session 2)

> Architecture, routing rules, and empirically validated specs for all extraction job types.
> Contains Haiku-classified sub-event analysis within 8.01, litigation discovery, and conditioning signals.

# Extraction Triggers

> Architecture, routing rules, and empirically validated specs for all extraction job types.
> Validated against live Neo4j database (23,836 8-K filings, 796 companies) on 2026-03-14.

---

## Ongoing Extraction Pipelines (for Earnings Prediction Agent)

The prediction agent receives a new earnings press release and predicts the stock reaction.
It needs prior context. Three extraction types run on an **ongoing basis** to feed it:

### 1. Guidance (LIVE — already built)

| Field | Value |
|---|---|
| Why | Directly changes market expectations. If management guided down 2 weeks ago, a "miss" is less surprising. |
| Signal | 3.42% standalone impact, -0.34pp earnings conditioning, 36% more impactful than non-guidance 7.01 |
| What agent gets | Prior guidance values (revenue, EPS, margins) to compare against tonight's actuals |

### 2. Restructuring (NEW — build next)

| Field | Value |
|---|---|
| Why | **Strongest conditioning signal in database (+2.97pp volatility).** Market expects restructuring charges in upcoming earnings. Agent needs timeline: was this pre-announced or a surprise in earnings? |
| Signal | 4.14% standalone, +2.97pp earnings volatility increase (9.42% vs 6.45%, N=953) |
| What agent gets | Restructuring details (headcount, charges, timeline) so it can distinguish expected charges from surprises |
| Spec | See Restructuring — TIER 1 below |

### 3. Litigation (NEW — build next)

| Field | Value |
|---|---|
| Why | Highest standalone impact within 8.01 (4.65%). Pending lawsuits or settlements change how the agent interprets legal expense line items in earnings. |
| Signal | 4.65% standalone (N=152), +0.74% positive bias (resolution = relief rally) |
| What agent gets | Litigation status (filed/settled/dismissed, amount, parties) to contextualize legal costs in earnings |
| Spec | See Litigation — TIER 1 below |

### Why NOT separate pipelines for buyback/dividend/M&A/debt?

The earnings press release **itself** mentions these — 37% mention buybacks, 15% mention dividends, 25% mention restructuring charges as line items. The prediction LLM already SEES them in the text it's reading. Their conditioning signals (-0.72pp buyback, -0.51pp dividend) are too weak to justify dedicated extraction pipelines. The LLM can pick these up from the earnings text directly.

Restructuring and litigation are different: their prior occurrence CHANGES how the agent should interpret earnings, and that context is NOT in the earnings press release itself.

---

## Pipeline Architecture

### 3-Stage Routing Pipeline

```
Stage 1: ITEM CODE FILTER          free, instant, deterministic
  → Narrow 23,836 filings to candidate superset by item codes

Stage 2: LLM ROUTER (Haiku)        ~$0.0006/filing, ~$13.50 total
  → Reads section text (1-4KB avg)
  → Classifies into event type(s)
  → 0% false positive rate (validated on 130 filings)
  → Replaces keyword matching entirely

Stage 3: EXTRACTION PROMPT          per-type LLM, reads full content
  → Routes to specific extraction job
  → Reads section + exhibit content
  → Produces structured output
```

### LLM Router Prompt (Stage 2)

```
Classify this 8-K filing section into ALL applicable categories using the
canonical event taxonomy in Section 1A.

Section text: {section_text}

Return: comma-separated list of categories.
```

One call per section. All categories in one pass. No keyword curation needed.

Recommended production output fields:

- `primary_event`
- `secondary_events`
- `event_date`
- `confidence`

Optional extended tags for the long-term event timeline, if needed later:

- `CYBER_INCIDENT`
- `RESTATEMENT`
- `ACCOUNTANT_CHANGE`
- `DELISTING_RIGHTS_CHANGE`
- `IMPAIRMENT`
- `SECURITIES_OFFERING`

### Why LLM Router > Keywords (empirically validated)

| Metric                    | Compound Keywords | LLM Router |
|---------------------------|-------------------|------------|
| Recall (buyback)          | ~99%              | ~100%      |
| Recall (dividend)         | ~99%              | ~100%      |
| Recall (restructuring)    | ~90%              | ~100%      |
| Recall (M&A, debt, etc.)  | 0%                | ~100%      |
| False positive rejection  | 85-90%            | ~100%      |
| Cost per filing           | $0                | $0.0006    |
| Adding new types          | new keyword list   | add to prompt |

### Content Source Rules

```
SECTIONS  = per-ITEM (1:1 with item codes, always fetchable)
EXHIBITS  = per-FILING (no formal item linkage, filing-level attachments)
```

Content fetch strategy:
1. Always fetch BOTH sections and exhibits
2. If section is a pointer ("see Exhibit 99.1") → exhibit is primary
3. Sections for OTHER items on same filing are independent content
4. Only skip a section if it's literally a pointer

### Exhibit Families (SEC Item 601)

| Family   | Formal Name          | Content Type   | Avg Size  | 8-K Relevance        |
|----------|----------------------|----------------|-----------|----------------------|
| EX-99.x  | Additional Exhibits  | Narrative       | 24-33 KB  | Press releases, decks |
| EX-10.x  | Material Contracts   | Legal           | 80-205 KB | Contracts, agreements |
| EX-2     | Plan of Acquisition  | Legal           | varies    | Rare (Item 2.01)      |
| EX-4     | Instruments          | Legal           | varies    | Rare (Item 3.03)      |
| EX-17    | Director Departure   | Correspondence  | varies    | Rare (Item 5.02)      |

Sub-numbering (.1, .2, .3) = filing convention ("first of this type, second, third..."), NOT formal SEC designation.

### Filed vs Furnished

| Status    | Items           | Liability         |
|-----------|-----------------|-------------------|
| FURNISHED | 2.02, 7.01      | NOT Section 18    |
| FILED     | All others      | Full Section 18   |

Exhibits inherit status from their parent item code. Same EX-99.1 has different legal weight depending on which item it's stapled to.

---

## 8k_events

> 9 SEC sections, 31 item codes. Item 9.01 is NOT an event — just a checkbox ("exhibits attached").
> Distribution: 6 item codes cover 90%+ of all filings (2.02, 7.01, 5.02, 8.01, 1.01, 9.01).

### 1_materialAgreements
#### 1.01_materialAgreementEntry
#### 1.02_materialAgreementTermination
#### 1.03_bankruptcy
#### 1.04_mineSafety
#### 1.05_cyberIncident

### 2_financialResults
#### 2.01_acquisitionOrDisposition
#### 2.02_resultsOfOperations
#### 2.03_directFinancialObligation
#### 2.04_obligationTriggerEvent
#### 2.05_exitOrDisposalCosts
#### 2.06_materialImpairment

### 3_securitiesAndTrading
#### 3.01_delistingNotice
#### 3.02_unregisteredEquitySales
#### 3.03_securityHolderRightsChange

### 4_accountantChanges
#### 4.01_certifyingAccountantChange
#### 4.02_priorStatementNonReliance

### 5_corporateGovernance
#### 5.01_controlChange
#### 5.02_officerDirectorChange
#### 5.03_bylawAmendment
#### 5.04_benefitPlanSuspension
#### 5.05_ethicsCodeChange
#### 5.06_shellStatusChange
#### 5.07_shareholderVote
#### 5.08_shareholderNomination

### 6_assetBackedSecurities
#### 6.01_absInfoMaterial
#### 6.02_servicerTrusteeChange
#### 6.03_creditEnhancementChange
#### 6.04_missedDistribution
#### 6.05_securitiesActUpdate

### 7_regFD
#### 7.01_regFDDisclosure

### 8_otherEvents
#### 8.01_otherEvents

### 9_financialStatements
#### 9.01_financialStatementsAndExhibits

---

## Consensus/Analyst Expectations

### News

### external_data/api

---

## Guidance Extraction

### Transcripts

### News

### 10-Q

### 10-K

### 8-K

**Validated spec:**

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| Trigger items     | 2.02, 7.01, 8.01                              |
| LLM router label  | GUIDANCE                                       |
| Content sources   | Sections for trigger items + EX-99.x exhibits  |
| Skip              | EX-10.x (contracts — no guidance content)      |
| Pool size         | ~8,847 (2.02) + keyword-gated 7.01/8.01       |
| Recall            | ~100%                                          |
| 2.02 handling     | Always include; content in EX-99.1             |

---

## CompanyDrivers

### Transcripts

### News

### 10-Q

### 10-K

### 8-K

> CompanyDrivers encompasses multiple event types that can move stock prices.
> Each sub-type has its own routing spec below.

#### Earnings — TIER 1

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| Trigger           | Item 2.02 only — no keywords or LLM needed    |
| Content           | EX-99.1 (press release)                        |
| Pool              | **8,847**                                      |
| Recall            | **~100%**                                      |
| Precision         | **100%** (10/10 sample)                        |
| Status            | FURNISHED                                      |
| Standalone impact | **6.78%** avg abs adj return (N=6,132 single-item) |
| Notes             | Item 2.02 IS earnings by SEC definition. 2.5x all other event types. |

#### Restructuring — TIER 1

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | RESTRUCTURING                                  |
| Trigger items     | 2.05 (always), 8.01, 7.01, 5.02, 2.06 (gated) |
| EXCLUDE           | **2.02** — 100% false positive rate            |
| Content           | Sections + EX-99.x exhibits                   |
| Pool              | **388** (215 via 2.05 + 173 LLM-gated)        |
| Recall            | **~100%** (0 true restructurings escape)       |
| 2.05 precision    | **100%** (15/15 sample)                        |
| Gated precision   | 45% keywords → ~100% LLM                      |
| Standalone impact | **4.14%** in 8.01 (N=22), **2.44%** via 2.05 (N=60), -1.06% negative bias |
| Earnings conditioning | **+2.97pp** volatility increase (9.42% vs 6.45%, N=953) — STRONGEST signal in database |
| 2.05 handling     | Always include — this IS the restructuring code|

Fallback compound keywords:
`'restructuring', 'workforce reduction', 'layoff', 'headcount reduction', 'facility closure', 'reduction in force'`

#### Guidance Revision — TIER 1

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | GUIDANCE                                       |
| Trigger items     | 7.01, 8.01                                    |
| Content           | Sections + EX-99.x exhibits                   |
| Pool              | ~149 (7.01) + ~15 (8.01) standalone           |
| Standalone impact | **3.42%** in 7.01 (N=149), **2.66%** in 8.01 (N=15), negative bias (-0.55%) |
| vs non-guidance   | **36% more impactful** than 7.01 without guidance (3.42% vs 2.51%) |
| Earnings conditioning | **-0.34pp** directional (more negative earnings reactions) |
| Notes             | Most valuable Reg FD content type. Directly changes market expectations. |

Fallback compound keywords:
`'guidance', 'outlook', 'preliminary results', 'pre-announce', 'revised', 'updated outlook', 'expects revenue', 'expects earnings'`

#### Litigation — TIER 1

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | LITIGATION                                     |
| Trigger items     | 8.01, 7.01                                    |
| Content           | Sections + EX-99.x                             |
| Pool              | ~152 standalone in 8.01                        |
| Standalone impact | **4.65%** avg abs adj return (N=152) — **highest non-earnings 8.01 content type** |
| Direction         | +0.74% positive bias (settlements often resolve uncertainty) |
| Earnings conditioning | Not yet tested                              |
| Notes             | High variance (std 10.15%) — outcomes range from catastrophic to relief rallies |

#### Buybacks — TIER 2

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | BUYBACK                                        |
| Trigger items     | 2.02, 8.01, 7.01, 1.01                        |
| Content           | Sections + EX-99.x exhibits                   |
| Pool              | **~3,651** (3,030 via 2.02 + 621 non-2.02)    |
| Recall            | **~99%+**                                      |
| Known gap         | 3 TE Connectivity share cancellations via 5.03 |
| Standalone impact | **2.42%** in 8.01 (N=86), **+1.12% consistently positive** bias |
| Earnings conditioning | **-0.72pp** directional — counter-intuitive: buyback before earnings predicts WORSE reaction (defensive signal) |
| 2.02 handling     | Always include; scan EX-99.1                   |
| 8.01/7.01/1.01    | LLM-gated                                     |
| Validation        | 130-filing sample, 0% LLM FP rate             |

Fallback compound keywords:
`'share repurchase', 'stock repurchase', 'buyback', 'buy back', 'repurchase program', 'repurchase of its', 'repurchase of up to'`

#### Impairment — TIER 2

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| Trigger           | Item 2.06 — no LLM needed                     |
| Content           | Sections + EX-99.x                             |
| Pool              | **54** (small)                                 |
| Standalone impact | 2.52% (N=11 single-item, too small for confidence) |
| Earnings conditioning | **-1.15pp** directional bias (-1.32% vs -0.17%, N=214) — foreshadows worse earnings |
| Notes             | Logically strong signal. Small N limits statistical confidence. |

#### M&A — TIER 2

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | M_AND_A                                        |
| Trigger items     | 1.01, 2.01, 8.01, 7.01, 5.01                  |
| Content           | Sections + EX-99.x + EX-10.x + EX-2           |
| Pool              | ~182 (8.01) + ~4 (7.01) + Item 2.01 (189)     |
| Standalone impact | **2.63%** in 8.01 (N=182), **2.75%** via 2.01 (N=29) |
| Earnings conditioning | +0.33pp directional — mild positive (acquisition = growth signal) |
| Notes             | 14% of Item 8.01, 10% of Item 7.01. Vocabulary too diverse — LLM router required. |

#### Executive Departure — TIER 2

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | EXECUTIVE_CHANGE                               |
| Trigger items     | 5.02                                           |
| Content           | Sections (57% section-only) + EX-10.x (employment agreements) |
| Pool              | ~5,103 total, needs LLM to separate departures from routine board refresh |
| Standalone impact | **1.84%** at item-code level (N=2,853), -0.24% negative bias |
| Notes             | Content matters: CFO departure ≠ routine board committee rotation. Item-code level is too noisy. LLM must classify departure vs appointment vs routine, with `GOVERNANCE` available only as a secondary tag when the filing is mainly board-structure rather than officer-change content. |

#### Dividends — TIER 3

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | DIVIDEND                                       |
| Trigger items     | 2.02, 8.01, 7.01                              |
| Content           | Sections + EX-99.x exhibits                   |
| Pool              | **~1,738** (1,230 via 2.02 + 508 non-2.02)    |
| Recall            | **~99.4%**                                     |
| Non-2.02 precision| **100%** (20/20 sample)                        |
| Standalone impact | **1.74%** in 8.01 (N=51) — **quietest event type**, -0.27% neutral |
| Earnings conditioning | **-0.51pp** directional, **-14% lower volatility** (5.88% vs 6.82%) — compressed, mildly negative regime |
| Known gap         | 3 filings with missing 2.02 tag (data quality) |
| Notes             | Regular quarterly dividends are non-events. Value is in CHANGES (cuts, special dividends, increases). LLM must distinguish announcement vs routine. |

Fallback compound keywords:
`'declared a dividend', 'declared a quarterly', 'quarterly cash dividend', 'quarterly dividend of', 'dividend per share', 'cash dividend of', 'regular quarterly dividend', 'declared a special dividend', 'annual dividend of', 'increased the dividend'`

#### Debt — TIER 3

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | DEBT_FINANCING                                 |
| Trigger items     | 1.01, 2.03, 8.01, 7.01                        |
| Content           | Sections + EX-10.x exhibits                   |
| Pool              | ~72 (8.01) + Item 2.03 (1,494)                |
| Standalone impact | **2.44%** in 8.01 (N=72), +0.54% mildly positive |
| Earnings conditioning | Neutral                                     |
| Notes             | **30% of Item 8.01** — largest category. Usually routine (credit facility renewals). Value is in WHY they raised capital (expansion vs liquidity distress). |

#### Cybersecurity — TIER 3

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| Trigger           | Item 1.05 — no LLM needed                     |
| Content           | Sections                                       |
| Pool              | **12** (very rare, new SEC rule Dec 2023)      |
| Standalone impact | 2.60% (N=10), **-2.46% strongly negative**    |
| Notes             | Logically devastating. Insufficient data for statistical confidence. As more filings accumulate under the new rule, this will become more testable. |

#### Restatement — TIER 3

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| Trigger           | Item 4.02 — no LLM needed                     |
| Content           | Sections                                       |
| Pool              | **15** (very rare)                             |
| Standalone impact | 5.01% (N=6 single-item, unreliable — driven by outliers, median only 0.76%) |
| Notes             | Logically devastating (prior financials unreliable). Too rare for empirical validation but always worth extracting when it occurs. |

---

## ManagementAnnouncements

### Transcripts

### News

### 10-Q

### 10-K

### 8-K

> ManagementAnnouncements is the parent category. Sub-types that are also CompanyDrivers
> (buybacks, dividends, restructuring) share the same routing specs defined above.
> Additional sub-types below.

#### Governance — DON'T EXTRACT (for earnings prediction)

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | GOVERNANCE                                     |
| Trigger items     | 5.02, 5.03, 5.07, 5.01, 3.03                  |
| Standalone impact | 5.02: 1.84% (N=2,853), 5.07: 1.64% (N=1,389), 5.03: 1.58% (N=318) |
| Earnings conditioning | No meaningful signal                       |
| Notes             | Routine governance. Exception: executive DEPARTURES (see Tier 2 above). |

#### InvestorPresentation — DON'T EXTRACT (for earnings prediction)

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| LLM router label  | INVESTOR_PRESENTATION                          |
| Trigger items     | 7.01                                           |
| Standalone impact | **2.33%** (N=275) — below 7.01 baseline of 2.84% |
| Earnings conditioning | No signal (-0.08pp, noise)                 |
| Notes             | Routine decks with no new information. 22.5% of 7.01 filings. Exception: if presentation contains NEW GUIDANCE, it's classified as GUIDANCE instead. |

#### ShareholderVote — DON'T EXTRACT

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| Standalone impact | **1.64%** (N=1,389) — second-lowest            |
| Notes             | Routine annual meeting results. No earnings conditioning signal. |

#### BylawAmendment — DON'T EXTRACT

| Field             | Value                                          |
|-------------------|------------------------------------------------|
| Standalone impact | **1.58%** (N=318) — lowest reliable item       |
| Notes             | Governance structure changes. Irrelevant to earnings prediction. |

---

## Empirical Validation Summary

### Database coverage

| Metric                         | Value                |
|--------------------------------|----------------------|
| Total 8-K filings              | 23,836               |
| Companies tracked               | 796                  |
| Filings with exhibits           | 16,000 (67%)         |
| Filings with sections           | 23,785 (99.8%)       |
| Distinct exhibit numbers        | 101 (top 6 = 95%+)   |
| Distinct section types          | 26                   |

### LLM router vs keywords (130-filing validation)

| Category      | LLM Recall | Keyword Recall | LLM FP Rate | Keyword FP Rate |
|---------------|------------|----------------|-------------|-----------------|
| Buyback       | 100%       | 100%           | 0%          | 0%              |
| Dividend      | 100%       | 100%           | 0%          | 0%              |
| Restructuring | 100%       | 0% (1 miss)    | 0%          | n/a             |
| M&A           | 100%       | 0%             | 0%          | n/a             |
| Debt          | 100%       | 0%             | 0%          | n/a             |
| Guidance      | 100%       | 75%            | 0%          | n/a             |

### Known false positive patterns (keywords)

| Pattern                                  | Rate | Root Cause                       |
|------------------------------------------|------|----------------------------------|
| "repurchase" in Item 1.01                | 85%  | Bond/note repurchase provisions  |
| "restructuring" in Item 2.02 sections   | 100% | Non-GAAP line items in earnings  |
| "dividend" in Item 1.01                  | 90%  | Credit agreement covenant language|
| "restructuring" in Item 5.02            | 80%  | Severance/departure boilerplate  |

### Section-only search recall gap (exhibit-only content)

| Category      | Filings with keyword in exhibit ONLY | % of total |
|---------------|--------------------------------------|------------|
| Buyback       | 1,985                                | 73%        |
| Dividend      | 1,076                                | 58%        |
| Restructuring | 1,286                                | 67%        |

Root cause: Item 2.02 sections are pointers ("see Exhibit 99.1"). Must scan exhibits too.

### 2.02 EX-99.1 signal rates (how often earnings press releases mention each topic)

| Topic         | Raw Hit Rate | Estimated Substantive Rate |
|---------------|-------------|---------------------------|
| Buyback       | 36.9%       | ~11-15%                   |
| Dividend      | 15.0%       | ~6-9%                     |
| Restructuring | 24.8%       | ~5-7%                     |

---

## Market Impact Analysis (Empirical, 3-Phase)

### Phase 1: Standalone Impact — Single-Item Filings (N=15,966)

Baseline (all 8-K): 4.02% avg absolute adjusted return. Non-earnings baseline: ~2.0-2.8%.

| Item Code | N (single) | Avg \|Adj\| | Signed | Tier |
|---|---|---|---|---|
| **2.02 Earnings** | 6,132 | **6.78%** | -0.09% | 1 |
| 4.01 Accountant Change | 39 | 3.15% | +0.16% | — |
| **7.01 Reg FD** | 1,969 | **2.84%** | +0.11% | mixed |
| **1.01 Material Agreement** | 422 | **2.73%** | -0.32% | 2 |
| **8.01 Other Events** | 2,584 | **2.65%** | +0.001% | mixed |
| 2.05 Restructuring | 60 | 2.44% | -0.60% | 1 |
| **5.02 Officer Change** | 2,853 | **1.84%** | -0.24% | skip |
| **5.07 Shareholder Vote** | 1,389 | **1.64%** | -0.12% | skip |
| 5.03 Bylaws | 318 | 1.58% | +0.27% | skip |
| 2.03 Financial Obligation | 37 | 1.59% | +0.02% | 3 |

### Phase 2: Content-Level Impact — Within 8.01 (N=2,584 single-item)

| Content Type | N | Avg \|Adj\| | Signed | vs 8.01 baseline (2.65%) |
|---|---|---|---|---|
| **LITIGATION** | 152 | **4.65%** | +0.74% | **+75%** |
| **RESTRUCTURING** | 22 | **4.14%** | -1.06% | +56% |
| UNCLASSIFIED | 306 | 2.77% | -0.46% | baseline |
| GUIDANCE | 15 | 2.66% | -1.84% | baseline (small N) |
| M&A | 182 | 2.63% | -0.35% | baseline |
| DEBT_FINANCING | 72 | 2.44% | +0.54% | -8% |
| **BUYBACK** | 86 | 2.42% | **+1.12%** | -9% (but consistently positive) |
| DIVIDEND | 51 | 1.74% | -0.27% | **-34%** |

### Phase 2: Content-Level Impact — Within 7.01 (N=1,969 single-item)

| Content Type | N | Avg \|Adj\| | Signed | vs 7.01 baseline (2.84%) |
|---|---|---|---|---|
| **GUIDANCE** | 149 | **3.42%** | -0.55% | **+36%** |
| INVESTOR_PRES | 275 | 2.33% | -0.10% | -18% |

### Phase 3: Earnings Conditioning — Does Prior Event Change Earnings Reaction?

Baseline earnings: 6.78% avg abs adj, -0.20% directional.

| Prior Event (30d) | N (with) | \|Adj\| delta | Direction delta | Signal |
|---|---|---|---|---|
| **Restructuring (2.05)** | 953 | **+2.97pp** | +0.20pp | **STRONGEST** |
| **Buyback (content)** | 786 | -0.15pp | **-0.72pp** | Counter-intuitive negative |
| **Dividend (content)** | 358 | **-0.94pp** | **-0.51pp** | Compressed, negative |
| **Guidance (content)** | 1,511 | +0.22pp | **-0.34pp** | Moderate negative |
| Non-guidance 7.01 | 5,042 | +0.23pp | -0.08pp | **Noise** |
| Impairment (2.06) | 214 | +0.61pp | **-1.15pp** | Directional (small N) |

### Extraction Priority Matrix

| Tier | Extraction Type | Standalone | Conditioning | Action |
|---|---|---|---|---|
| **1** | Earnings | 6.78% | — | Always extract |
| **1** | Restructuring | 4.14% | +2.97pp vol | Always extract |
| **1** | Guidance Revision | 3.42% | -0.34pp dir | Always extract |
| **1** | Litigation | 4.65% | untested | Always extract |
| **2** | Buyback | 2.42% (+1.12% pos) | -0.72pp dir | Extract for context |
| **2** | Impairment | 2.52% | -1.15pp dir | Extract for context |
| **2** | M&A | 2.63% | +0.33pp dir | Extract for context |
| **2** | Executive Departure | 1.84% (noisy) | needs test | Extract for context |
| **3** | Dividend | 1.74% | -0.51pp, -14% vol | Context only |
| **3** | Debt | 2.44% | neutral | Context only |
| **3** | Cybersecurity | 2.60% (N=10) | insufficient | Extract when available |
| **3** | Restatement | 5.01% (N=6) | insufficient | Extract when available |
| **skip** | Shareholder Vote | 1.64% | no signal | Don't extract |
| **skip** | Bylaws | 1.58% | no signal | Don't extract |
| **skip** | Investor Presentation | 2.33% | no signal | Don't extract |

---
---

# Part III: Stock Impact & Predictive Analysis (Claude Session 1)

> Empirical stock return analysis, amplifier discovery, and Phase 4 contextual value testing.

## Layer 5: The Extraction Routing Pipeline — Validated Strategy

### The Core Problem

An 8-K filing arrives. You need to answer:
1. Which extraction job(s) should fire? (routing)
2. What text should each job read? (content selection)

Both answers must be deterministic, near-100% recall, and maximum precision.

### Why Pure Heuristics Fall Short

Three approaches were tested empirically against the full database (23,836 filings):

**Approach 1: Item codes only** — Fast and free but insufficient for non-earnings types. Item 8.01 ("Other Events") could be a buyback, dividend, restructuring, or anything else. Item codes can't tell you WHAT the filing says, only what SEC category it was filed under.

**Approach 2: Item codes + compound keywords** — Better precision but:
- "restructuring" in earnings press releases = 82.8% false positives (line-item mentions, not announcements)
- "dividend" in loan covenants = ~50% false positives
- Forward guidance keywords ("outlook", "we expect") = 68% false positive rate
- Requires per-type keyword engineering and maintenance

**Approach 3: Item codes + Haiku LLM classifier** — Best of all worlds.

### The Haiku Router Test (280 filings, $0.28)

Tested 40 filings per item-code group (7 groups × 40 = 280), comparing Haiku classification vs keyword heuristics:

```
PRECISION COMPARISON (Haiku rejected heuristic false positives):

  Forward guidance: Heuristic tagged 75, Haiku only 24
    → Heuristic has 68% FALSE POSITIVE RATE
    → "outlook" and "we expect" match boilerplate, not real guidance

  Executive change: Heuristic tagged 73, Haiku only 46
    → Heuristic over-tags by 37%

  Buybacks: Heuristic tagged 14, Haiku only 8
    → Heuristic over-tags by 43%

RECALL COMPARISON (Haiku caught things heuristic missed):

  Governance: Haiku +19 items from 8.01 filings with 5.03/3.03
  Restructuring: Haiku +5 from 2.05 filings without keyword hits
  Earnings: Haiku +4 from 7.01 filings that were actually earnings
  Buybacks: Haiku +2 from content without compound keyword matches

RESTRUCTURING DEEP-DIVE:
  Item 2.02 filings classified as restructuring:
    Haiku: 0 of 40   (correctly rejects line-item mentions)
    Heuristic: 0 of 40 in this sample, but 82.8% false positive at scale

MULTI-CATEGORY:
  Haiku: 20% of filings tagged multi-category (selective)
  Heuristic: 33% of filings tagged multi-category (over-tags)

COST:
  280 filings: $0.28
  Full database (23,836 filings): ~$24
  Per filing: $0.001
```

### Cross-Validation with Codex Analysis

A separate independent analysis (Codex, stored in `8k_codex_analysis.md`) arrived at converging conclusions using keyword-only approach:

| Category | Our Keyword Recall | Codex Keyword Recall | Agreement |
|---|---|---|---|
| Earnings | ~100% (2.02 alone) | ~100% (2.02 alone) | Full agreement |
| Buybacks | 99.1% [2.02,8.01,7.01,1.01] | 99.5% [1.01,2.02,2.03,7.01,8.01] | Codex added 2.03 → +0.4% |
| Dividends | 98.8% [2.02,8.01,7.01] | 97.4% [2.02,7.01,8.01] | Same filter, different keyword specificity |
| Restructuring | 37.7% w/o 2.02 | 95.7% [2.02,2.05,5.02,7.01,8.01] | Codex used tighter keywords, avoided 2.02 FP flood |

**Key Codex-unique findings incorporated:**
- Item 2.03 should be in buyback filter (catches ASR contracts) → recall 99.1% → 99.5%
- "restructuring plan" instead of bare "restructuring" avoids the 2.02 false positive flood (768 vs 4,180 matches)
- Dividends leak into 9.01-only and 5.02 filings → Haiku handles this naturally
- Codex confirmed: keyword-first search across ALL content (not just sections) is mandatory

### The Optimal 3-Stage Pipeline

```
STAGE 1: ITEM CODE PRE-FILTER (free, instant, deterministic)
┌───────────────────────────────────────────────────────┐
│ IDENTITY ITEMS → route directly to extraction:        │
│   2.02 → earnings + guidance + fan-out to all types   │
│   2.05 → restructuring extraction                     │
│   2.06 → impairment extraction                        │
│   2.01 → M&A extraction                               │
│                                                       │
│ CONTAINER ITEMS → send to Stage 2:                    │
│   8.01, 7.01, 1.01, 5.02, 2.03                       │
│                                                       │
│ GOVERNANCE-ONLY → governance extraction only:         │
│   5.07 alone, 5.03 alone                              │
│                                                       │
│ SKIP: 9.01-only filings (exhibit index, no event)     │
└───────────────────────────────────────────────────────┘

STAGE 2: HAIKU CLASSIFIER ($0.001/filing, ~1 second)
┌───────────────────────────────────────────────────────┐
│ Input: item codes + first 3KB of section + exhibit    │
│                                                       │
│ Output: multi-label classification with confidence    │
│   {"categories": ["share_buyback", "debt_financing"], │
│    "primary": "share_buyback"}                        │
│                                                       │
│ Supported categories:                                 │
│   earnings_release, forward_guidance, share_buyback,  │
│   dividend_declaration, restructuring, m_and_a,       │
│   debt_financing, executive_change, governance, other │
│                                                       │
│ Key advantage: understands context                    │
│   "restructuring charges" as line item → NOT restruct │
│   "declared a quarterly dividend" → YES dividend      │
│   "repurchase agreement" (repo) → NOT buyback         │
│                                                       │
│ Adding new extraction types = add to prompt. Done.    │
└───────────────────────────────────────────────────────┘

STAGE 3: FULL EXTRACTION (Opus/Sonnet, expensive)
┌───────────────────────────────────────────────────────┐
│ Only runs on filings routed by Stage 1 or Stage 2.   │
│ Reads full content (sections + exhibits).             │
│ Extracts structured data per extraction type.         │
│                                                       │
│ Content selection per type:                           │
│   Earnings/Guidance → EX-99.1 (press release)        │
│   Buybacks → EX-99.1 + Item 8.01 section             │
│   Dividends → EX-99.1 + Item 8.01 section            │
│   Restructuring → Item 2.05 section + EX-99.1        │
│   M&A → EX-10.1 (contract) + Item 2.01 section       │
│   Debt → EX-10.1 (agreement) + Item 1.01 section     │
│   Exec change → Item 5.02 section + EX-10.x          │
└───────────────────────────────────────────────────────┘
```

### Why Haiku Routing Is Definitively Better Than Keywords

| Dimension | Keywords | Haiku |
|---|---|---|
| Precision | ~50-85% (type-dependent) | ~90-100% |
| Recall | ~95-99% | ~95-100% |
| Maintenance | Per-type keyword lists | One prompt |
| New types | Engineer new keyword list | Add category name |
| Context understanding | None ("restructuring" = match) | Full ("restructuring charges as line item" ≠ "announced restructuring") |
| Cost | Free (but downstream waste) | $0.001/filing ($24 total) |
| Multi-category | Over-tags by 33% | Selective 20% |

### Fallback: Compound Keywords (when Haiku unavailable)

If Haiku routing is not available, these validated compound keyword specs provide the best heuristic fallback:

```
BUYBACKS:
  Items: [1.01, 2.02, 2.03, 7.01, 8.01]
  Keywords: "share repurchase" OR "stock repurchase" OR "buyback" OR
            "buy back" OR "repurchase program" OR "repurchase authorization"
  Search: sections + EX-99.x exhibits
  Recall: 99.5% | Precision: ~55% (LLM handles rest)

DIVIDENDS:
  Items: [2.02, 7.01, 8.01]
  Keywords: "declared a dividend" OR "declared a quarterly" OR
            "quarterly cash dividend" OR "cash dividend of" OR
            "special dividend" OR "increased the dividend" OR
            "dividend of $" OR "annual dividend of"
  Search: sections + EX-99.x exhibits
  Recall: 97-99% | Precision: ~95%

RESTRUCTURING:
  Items: [2.05, 5.02, 7.01, 8.01, 2.06]
  Keywords: "restructuring plan" OR "workforce reduction" OR
            "layoff" OR "layoffs" OR "reduction in force" OR
            "headcount reduction" OR "facility closure"
  NOTE: Do NOT include bare "restructuring" (hits 4,180 false positives
        from earnings line items). Do NOT use Item 2.02 in the filter.
  Search: sections + EX-99.x exhibits
  Recall: ~96% | Precision: ~70-80%

EARNINGS:
  Items: [2.02]
  Keywords: not needed
  Recall: ~100% | Precision: ~100%
```

### Test artifacts

- Haiku test script: `scripts/test_haiku_router.py`
- Haiku test results: `.claude/plans/Extractions/haiku_router_test_results.json` (280 filings)
- Codex independent analysis: `.claude/plans/Extractions/8k_codex_analysis.md`
- Codex raw data: `.claude/plans/Extractions/8k_codex_analysis_data.json`

---

## Layer 6: Stock Price Impact by Event Type — Empirical Results

Validated against live Neo4j database: 22,972 filings with return data. All returns are market-adjusted (daily_stock - daily_macro) in percentage points.

### The Measurement Methodology

Returns are per-FILING, not per-EVENT. A filing with Items `[2.02, 8.01, 9.01]` reflects mostly earnings, not the 8.01 event. To isolate event impact:

- **Phase 1 (Clean isolation):** Filings where the event is the ONLY substantive item (Item 2.02 excluded to avoid earnings contamination)
- **Phase 2 (Incremental signal):** Compare pure-earnings filings vs earnings+event filings — the difference is the event's incremental contribution
- **Phase 3 (Sector decomposition):** Same as Phase 1 but by sector

### Phase 1: Standalone Event Impact

Baseline: non-earnings 8-K filings = **2.37% avg |adjusted return|**

```
RANKED BY STANDALONE IMPACT (avg |adjusted return|):

  Earnings (2.02)           6.78%  2.86x baseline  n=8,601  ██████████████████████████████
  Agreement non-debt (1.01) 3.32%  1.40x baseline  n=1,009  ██████████████
  Restructuring (2.05)      3.28%  1.38x baseline  n=130    █████████████
  Reg FD (7.01)             3.10%  1.31x baseline  n=3,782  █████████████
  M&A completion (2.01)     2.93%  1.24x baseline  n=160    ████████████
  Other Events (8.01)       2.88%  1.22x baseline  n=3,949  ████████████
  Impairment (2.06)         2.67%  1.13x baseline  n=45     ███████████
  Cybersecurity (1.05)      2.66%  1.12x baseline  n=12     ███████████
  ── BASELINE ──            2.37%  1.00x            n=14,371 ██████████
  Debt (1.01+2.03)          1.84%  0.78x baseline  n=1,290  ████████
  Exec change (5.02)        1.84%  0.78x baseline  n=3,428  ████████
  Governance (5.07)         1.64%  0.69x baseline  n=2,077  ███████
```

**Key finding:** Only earnings (2.02) exceeds 2x baseline standalone. All other event types produce moderate or below-baseline standalone impact. But Phase 2 reveals a different story.

### Phase 2: Incremental Signal When Bundled With Earnings

Does adding a non-earnings event to an earnings filing amplify the stock reaction?

```
EARNINGS COMBINATIONS (vs pure earnings baseline of 6.79%):

  2.02 only (pure)          6.79%   baseline        n=6,160   direction: -0.10%
  2.02 + 7.01 (Reg FD)      6.18%  -0.61 (LOWER)   n=1,728   direction: -0.38%
  2.02 + 8.01 (Other)       7.14%  +0.35            n=611     direction: -0.49%
  2.02 + 1.01 (Agreement)   8.70%  +1.91 (+28%)     n=85      direction: -1.12%
  2.02 + 5.02 (Exec change) 8.92%  +2.13 (+31%)     n=331     direction: -1.50%
  2.02 + 2.05 (Restructure) 9.47%  +2.68 (+39%)     n=78      direction: -3.41%
```

**The amplifier discovery:**

- **Earnings + restructuring = 9.47%** — 39% more volatile than pure earnings, AND strongly negative (-3.41%). The "bad news compounding" pattern: company is cutting costs AND reporting weak results.
- **Earnings + exec change = 8.92%** — 31% more volatile, negative (-1.50%). CEO/CFO departures at earnings = trouble signal.
- **Earnings + material agreement = 8.70%** — 28% more volatile. Major deals announced alongside earnings amplify the reaction.
- **Earnings + Reg FD = 6.18%** — actually LOWER than pure earnings. These are larger, institutional companies that provide supplemental materials. More transparency = less surprise = lower volatility.

**Critical implication:** Items 2.05, 5.02, and 1.01 have low standalone impact (below baseline) but MASSIVE incremental signal when co-occurring with earnings. They are not price-movers on their own — they are **amplifiers** of the earnings reaction.

### Phase 3: Sector Decomposition

#### Clean 8.01 (Other Events) by sector

| Sector | n | Avg |Adj| | Sector Baseline | Ratio |
|---|---|---|---|---|
| Healthcare | 772 | 5.79% | 5.15% | 1.12x |
| CommunicationSvcs | 146 | 3.76% | 5.76% | 0.65x |
| Technology | 648 | 2.50% | 5.04% | 0.50x |
| FinancialServices | 331 | 1.74% | 2.74% | 0.64x |
| Utilities | 209 | 1.44% | 2.13% | 0.68x |

After sector-adjusting, most 8.01 events are BELOW their sector's baseline volatility. Only Healthcare 8.01 slightly exceeds its sector baseline (1.12x). The apparent sector spread (5.79% Healthcare vs 1.44% Utilities) is mostly inherent sector volatility, not event-driven.

#### Clean 1.01+2.03 (Debt) by sector

| Sector | n | Avg |Adj| | Direction |
|---|---|---|---|
| BasicMaterials | 74 | 3.45% | -1.09% |
| CommunicationSvcs | 49 | 2.85% | -1.58% |
| FinancialServices | 87 | 1.47% | -0.05% |

Debt issuance is a non-event across ALL sectors. For FinancialServices especially routine (1.47% vs 2.74% baseline = 0.54x).

#### Clean 2.05 (Restructuring) by sector

| Sector | n | Avg |Adj| | Direction |
|---|---|---|---|
| Healthcare | 17 | 5.61% | -2.29% |
| Technology | 37 | 3.75% | -0.03% |
| ConsumerCyclical | 28 | 2.72% | +0.84% |

Small samples, but Healthcare restructuring stands out (5.61%, strongly negative). In Tech, restructurings barely register against the sector's high inherent volatility (3.75% vs 5.04% baseline = 0.74x).

### Evidence-Based Tier Assignment

```
TIER 1 — ALWAYS EXTRACT (clear standalone or incremental signal)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Earnings (2.02)
    Standalone: 6.78% = 2.86x baseline
    n = 8,601 — rock solid
    Signal: dominant, directionally neutral

  Forward Guidance (within 2.02 + 7.01)
    Standalone (7.01): 3.10% = 1.31x baseline, n = 3,782
    Signal: guidance revisions are the most market-moving
            non-earnings content

  Restructuring (2.05)
    Standalone: 3.28% = 1.38x baseline (moderate)
    INCREMENTAL: 9.47% when bundled with 2.02 (+39% amplification)
    Direction: strongly negative (-3.41% when bundled)
    Signal: "company is cutting costs AND reporting bad earnings"
    n = 130 standalone, 78 bundled


TIER 2 — CONDITIONALLY EXTRACT (incremental signal, context-dependent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Executive Change (5.02)
    Standalone: 1.84% = 0.78x baseline (below — routine alone)
    INCREMENTAL: 8.92% when bundled with 2.02 (+31%)
    Direction: negative (-1.50% when bundled)
    Signal: "CEO/CFO departure at earnings = trouble"
    → Extract when co-occurring with 2.02 or within 30 days of earnings

  Material Agreement non-debt (1.01 w/o 2.03)
    Standalone: 3.32% = 1.40x baseline
    INCREMENTAL: 8.70% when bundled with 2.02 (+28%)
    Signal: major deals (M&A, licensing) announced at earnings
    → Always extract agreements; debt (1.01+2.03) is Tier 3

  Other Events (8.01) — buybacks, strategic updates, etc.
    Standalone: 2.88% = 1.22x baseline (mixed bag)
    Signal: highly heterogeneous — needs Haiku classification
    → Extract after Haiku classifies as buyback/dividend/restructuring

  M&A Completion (2.01)
    Standalone: 2.93% = 1.24x, negative bias (-0.52%)
    n = 160
    → Extract for M&A-specific analysis

  Impairment (2.06)
    Standalone: 2.67% = 1.13x, n = 45
    → Extract when co-occurring with 2.05 (restructuring + impairment)


TIER 3 — EXTRACT FOR CONTEXT ONLY (low standalone, contextual value)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Debt/Financing (1.01+2.03)
    Standalone: 1.84% = 0.78x baseline — BELOW baseline
    Signal: routine financing, does not move stocks
    → Extract cheaply, feed as context to prediction LLM

  Governance/Voting (5.07)
    Standalone: 1.64% = 0.69x baseline — lowest of all
    Signal: true non-event for price action
    → Context only (rare activist votes might matter)

  Cybersecurity (1.05)
    Standalone: 2.66%, n = 12 — too small for statistical confidence
    Direction: strongly negative (-1.63%)
    → Extract always (qualitative importance), cannot prove impact yet

  Dividend Declarations
    Not directly measurable from item codes alone (dividends are
    announced within 8.01/2.02/7.01 content — need Haiku to isolate)
    → Tier 2 when Haiku-classified as dividend in 8.01/7.01 filings
    → Already captured by earnings extraction when in 2.02
```

### The "Amplifier" Insight — Key Takeaway for the Prediction LLM

The biggest finding is NOT about standalone event impact — it's about **event combinations as amplifiers**:

```
Pure earnings:               6.79% avg |adj return|
Earnings + restructuring:    9.47% (+39%)  ← "bad news compounding"
Earnings + exec departure:   8.92% (+31%)  ← "management fleeing"
Earnings + major agreement:  8.70% (+28%)  ← "big deal at earnings"
Earnings + Reg FD:           6.18% (-9%)   ← "institutional stability"
```

The prediction LLM should weight co-occurring events heavily:
- An earnings filing that ALSO has Item 2.05 → expect larger, more negative reaction
- An earnings filing that ALSO has Item 5.02 → expect amplified negative reaction
- An earnings filing with Item 7.01 → expect slightly MORE STABLE reaction (institutional transparency)
- An earnings filing with only 9.01 → pure earnings, use standard model

---

## Layer 7: What to Actually Build — The Final Decision

### The Question

We already extract structured guidance from 8-K filings (the guidance extraction pipeline). Should we build SEPARATE full extraction pipelines for buybacks, dividends, restructuring, exec changes, M&A, etc.?

### The Answer: No — Event Tags, Not Full Extraction

The amplifier data (Layer 6) tells us these events matter as **signals** (something happened), not as **structured data** (exactly what happened). The prediction LLM doesn't need "Company repurchased 5.2M shares at $142.50 avg price under the $10B authorization." It needs: *"there was a restructuring announcement 12 days before this earnings filing."*

### Why Guidance Is Different

Guidance is the one extraction type where structured data IS essential:

```
The LLM needs to know:
  "Company guided Q3 revenue $94-98B, non-GAAP EPS $3.20-3.40"

So when earnings arrive:
  "Q3 revenue was $96.5B (within guidance range)"
  → LLM assesses: in-line, no surprise → moderate reaction

Without structured guidance, the LLM has to guess what was expected.
A tag saying "guidance was issued" is NOT enough.
```

For every OTHER event type, a tag IS enough:

```
"CEO departed on March 1"       → LLM knows trouble signal
"Restructuring announced Feb 15" → LLM knows cost-cutting mode
"$2B credit facility signed"     → LLM knows liquidity secured

The LLM doesn't need the exact severance terms, the credit
agreement covenants, or the buyback price per share.
```

### What to Build

```
┌─────────────────────────────────────────────────────────────────┐
│ FULL EXTRACTION PIPELINE (structured data, expensive)           │
│                                                                 │
│   Guidance only. ← Already built and running.                   │
│                                                                 │
│   Why structured: LLM needs exact numbers (revenue range,       │
│   EPS target, margin outlook) to assess beat/miss.              │
│   A tag isn't enough.                                           │
│                                                                 │
│   Cost: ~$0.50-1.00/filing × relevant filings                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ LIGHTWEIGHT EVENT TIMELINE (tags + dates, cheap)                │
│                                                                 │
│   Everything else. ← NEW, simple to build.                      │
│                                                                 │
│   How: Haiku classifies every non-earnings 8-K into event       │
│   types. Store as simple records:                               │
│   {event_type, date, ticker, accession_no, item_codes}          │
│                                                                 │
│   Event types detected:                                         │
│   - restructuring (2.05 or Haiku-classified)                    │
│   - exec_departure / exec_appointment (5.02)                    │
│   - buyback_authorization (Haiku-classified from 8.01/7.01)     │
│   - dividend_change (Haiku-classified from 8.01/7.01)           │
│   - m_and_a (2.01 or Haiku-classified)                          │
│   - debt_financing (1.01+2.03)                                  │
│   - impairment (2.06)                                           │
│   - cybersecurity (1.05)                                        │
│   - governance (5.07)                                           │
│                                                                 │
│   Fed to prediction LLM as context:                             │
│   "Events since last earnings:                                  │
│     - 2025-03-01: CEO departed (Item 5.02)                      │
│     - 2025-03-15: Restructuring announced (Item 2.05)           │
│     - 2025-03-20: $2B credit facility (Item 1.01+2.03)"        │
│                                                                 │
│   Cost: $0.001/filing × ~15,000 non-earnings filings = $15     │
└─────────────────────────────────────────────────────────────────┘
```

### Cost Comparison

```
Option A: Build full extraction pipelines for 8 event types
  8 types × ~2,000 filings each × $0.75/filing = ~$12,000
  + weeks of prompt engineering per type
  + ongoing maintenance of 8 pipeline specs

Option B: Haiku event timeline + guidance extraction (already built)
  Haiku classification: $15 total for entire database
  Guidance extraction: already running
  New engineering: one Haiku prompt (already tested and validated)
  Maintenance: one prompt to update

  Marginal value of full extraction over event tags: UNPROVEN
```

### The Exception: When to Revisit

Build a full extraction pipeline for a second event type IF AND WHEN:

1. **Phase 4 analysis** (contextual value — not yet run) proves that the MAGNITUDE of a specific event type (e.g., "10% layoff" vs "2% layoff") significantly improves prediction accuracy beyond the binary tag
2. **A specific trading strategy** requires structured event data (e.g., systematic buyback tracking needs exact authorization amounts and remaining capacity)
3. **Regulatory/compliance needs** require structured records of specific event types

Until one of these triggers fires, the event timeline approach is the right call: maximum information value per dollar spent.

### Summary: The Complete 8-K Extraction Architecture

```
8-K FILING ARRIVES
│
├── Has Item 2.02? ──────────────────────────────────────────────┐
│   YES                                                          │
│   ├── Run GUIDANCE EXTRACTION on EX-99.1 (full pipeline)       │
│   ├── Store structured guidance (ranges, metrics, periods)     │
│   ├── Feed to prediction LLM at next earnings                 │
│   └── Note co-occurring items (2.05, 5.02) as amplifier flags │
│                                                                │
├── Has identity item (2.05, 2.06, 2.01)? ──────────────────────┐
│   YES                                                          │
│   └── Store EVENT TAG: {type, date, ticker, accession}         │
│       No full extraction needed.                               │
│                                                                │
├── Has container item (8.01, 7.01, 1.01, 5.02)? ──────────────┐
│   YES                                                          │
│   ├── Run HAIKU CLASSIFIER on 3KB excerpt ($0.001)             │
│   └── Store EVENT TAG with Haiku-determined type               │
│                                                                │
├── Has governance only (5.07, 5.03)? ──────────────────────────┐
│   YES                                                          │
│   └── Store EVENT TAG: governance. Lowest priority.            │
│                                                                │
└── AT PREDICTION TIME (earnings filing arrives): ───────────────┐
    │                                                             │
    │ Assemble context for prediction LLM:                        │
    │  1. Full earnings press release (EX-99.1)                   │
    │  2. Prior structured guidance (from extraction pipeline)    │
    │  3. Event timeline since last earnings (from event tags)    │
    │  4. Amplifier flags (co-occurring items on this filing)     │
    │                                                             │
    │ The LLM sees everything it needs:                           │
    │  - What was expected (guidance)                              │
    │  - What happened between quarters (event timeline)          │
    │  - What's in this filing (press release + amplifier flags)  │
    └─────────────────────────────────────────────────────────────┘
```

---

## Layer 8: Phase 4 — Do Prior Events Predict Earnings Reactions?

Tested whether non-earnings 8-K events filed 2-60 days BEFORE an earnings release predict a different stock reaction at earnings. This is about TEMPORAL context — separate filings, not co-occurring items.

### The Dominant Finding: Transparency Effect

**Our initial assumption was wrong.** We expected prior "bad" events (exec departures, restructuring) to predict worse earnings reactions. Instead, the dominant effect is simpler:

```
MORE inter-quarter 8-K activity = LESS earnings surprise

Prior 8-Ks    n       Avg |Adj Return|   vs Baseline
─────────────────────────────────────────────────────
0 (none)      3,738   7.05%              ── baseline ──
1             2,880   6.75%              -4%
2             1,209   6.52%              -8%
3-4             656   6.05%              -14%
5+              118   5.43%              -23%
```

**Why:** Companies filing many inter-quarter 8-Ks are larger, more institutional, more analyst-covered. More disclosure between quarters = market already knows part of the story = less surprise at earnings.

### Per-Event-Type Results

Baseline: earnings with zero prior events = **7.05%** avg |adj return|, direction **+0.11%**

```
ABOVE BASELINE (predicts BIGGER earnings reaction):

  Prior restructuring (2.05):  8.49%  +20%   dir: -1.54%  n=94
    → THE ONLY prior event that reliably predicts worse earnings
    → Restructuring between quarters = company in trouble
    → Subsequent earnings: bigger move, strongly negative

  Prior governance (5.07):     7.53%  +7%    dir: -0.57%  n=834
    → Slightly elevated — possibly activist-related voting

  Prior impairment (2.06):     7.43%  +5%    dir: -0.98%  n=29
    → Slightly elevated, negative bias (tiny sample)

AT OR BELOW BASELINE (predicts SMALLER or EQUAL reaction):

  Prior exec change (5.02):    6.80%  -4%    dir: -0.39%  n=2,373
    → BELOW baseline — market already priced in the departure

  Prior agreement (1.01):      6.34%  -10%   dir: -0.60%  n=1,173
    → Below baseline — transparency/size effect

  Prior Reg FD (7.01):         6.16%  -13%   dir: -0.25%  n=1,842
    → Significantly below — mid-quarter disclosure de-risks earnings

  Prior debt (1.01+2.03):      5.95%  -16%   dir: -0.63%  n=709
    → Well below — companies with active debt markets are larger/stabler

  Prior Other Events (8.01):   5.76%  -18%   dir: -0.29%  n=1,574
    → Lowest — more disclosure = less surprise
```

### The Key Distinction: Same-Day vs Prior

```
EXECUTIVE DEPARTURE:
  Co-occurring with earnings (same filing):  8.92%  +31% amplifier  ← HUGE
  Filed separately 2-60 days before:         6.80%  -4% vs baseline ← NOTHING

RESTRUCTURING:
  Co-occurring with earnings (same filing):  9.47%  +39% amplifier  ← HUGE
  Filed separately 2-60 days before:         8.49%  +20% vs baseline ← STILL STRONG

The difference: when an exec departure is filed weeks before earnings,
the market prices it in immediately. By earnings day, it's old news.

But restructuring filed before earnings STILL predicts worse earnings —
because the restructuring signals ongoing operational problems that
will show up in the numbers.
```

### Exec Change Window Sensitivity

```
Window          n       Avg |Adj|   Direction
2-14 days       541     7.04%       -0.69%
2-60 days       2,373   6.80%       -0.39%
2-90 days       3,415   6.86%       -0.46%
```

Even within 14 days of earnings, prior exec changes are AT baseline — not above it. The amplifier effect is ONLY real when announced on the same day.

### Hypothesis Scorecard

```
H1: Prior exec departure → worse earnings         ❌ REJECTED (-4%)
H2: Prior restructuring → worse earnings           ✅ CONFIRMED (+20%, -1.54%)
H3: Prior Reg FD → smaller surprise                ✅ CONFIRMED (-13%)
H4: Prior agreement → unclear                      RESOLVED: -10% (lower)
H5: Prior debt → negative signal                   RESOLVED: -16% (lower)
H6: More prior activity → bigger reaction          ❌ OPPOSITE (-23% monotonic)
```

### What the Prediction LLM Should Actually Receive

Based on Phase 4 results, the event timeline should weight signals differently:

```
AT PREDICTION TIME — context to feed the LLM:

  1. STRUCTURED GUIDANCE (from extraction pipeline)
     → "Company guided Q3 revenue $94-98B"
     → THE most valuable input. Already built.

  2. AMPLIFIER FLAGS (from co-occurring items on THIS filing)
     → "This earnings filing also has Item 2.05 (restructuring)"
     → Expect +39% higher volatility, negative direction
     → Zero-cost signal: just read the items field

  3. PRIOR RESTRUCTURING (from event timeline)
     → "Company filed a standalone restructuring (2.05) 18 days ago"
     → Expect +20% higher volatility, negative direction
     → The ONLY prior event empirically proven to predict worse earnings

  4. PRIOR REG FD (from event timeline)
     → "Company filed a Reg FD disclosure (7.01) 25 days ago"
     → Expect -13% LOWER surprise (market partially de-risked)
     → Useful for calibrating confidence

  5. FILING VOLUME (simple count)
     → "Company filed 4 non-earnings 8-Ks since last earnings"
     → Expect -14% lower surprise (transparency effect)
     → Simplest possible signal, strong monotonic effect

  6. OTHER EVENTS (low-weight context)
     → Exec changes, agreements, debt — include as narrative context
     → No proven predictive value as prior events
     → Minimal cost to include, LLM may find qualitative use
```

### Updated Tier Assignment (Post-Phase 4)

```
TIER 1 — PROVEN PREDICTIVE VALUE
  Guidance extraction (structured data) — already built
  Amplifier flags (co-occurring items) — free, read items field
  Prior restructuring (2.05 event tag) — +20% predictive signal

TIER 2 — PROVEN DE-RISKING SIGNAL
  Prior Reg FD (7.01 event tag) — -13% surprise reduction
  Filing volume count — -23% monotonic transparency effect

TIER 3 — CONTEXTUAL ONLY (no proven predictive value as prior events)
  Prior exec change (5.02) — priced in by earnings day
  Prior agreement (1.01) — transparency effect only
  Prior debt (1.01+2.03) — transparency effect only
  Prior 8.01 — transparency effect only
  Prior governance (5.07) — no proven signal
```

---
---

# Part IV: Independent Validation (Codex Session 2)

> Full database analysis, 840-sample Haiku evaluation, manual spot-checks, Haiku error rates.
> CRITICAL FINDING: Haiku misses ~30-35% of real buyback/dividend events.

# 8-K Complete Consolidated Analysis

Date: 2026-03-14

This is the canonical merged file for the 8-K routing work. It preserves the full text of the merged analysis documents and adds the later clarifications from the follow-up discussion. After consolidation, the intermediate source analysis artifacts were deleted on request, so this file is the canonical record.

## Included Source Documents

| Source | File | Lines |
| --- | --- | ---: |
| Base deterministic 8-K analysis | `8k_codex_analysis.md` | 1079 |
| 840-sample Haiku vs baseline comparison | `8k_haiku_router_strategy.md` | 176 |
| 1,281-sample Haiku bucket evaluation | `haiku_router_strategy_evaluation.md` | 130 |
| Best-strategy synthesis | `8k_router_best_strategy.md` | 252 |

## Post-Merge Clarification: What Is Exact vs Estimated

The project has two different kinds of numbers, and they should not be mixed:

- Exact deterministic recall numbers measured on keyword-hit universes from the live database.
- Exact Haiku-vs-baseline overlap numbers on stratified samples.
- Estimated Haiku error-rate judgments from manual spot-checking, not from a fully human-labeled gold set.

Exact deterministic recall numbers from the live database:

| Job | Strategy | Exact recall measured |
| --- | --- | ---: |
| Earnings | `2.02` only | 95.11% on 6,538 keyword matches |
| Earnings | `2.02 + 7.01 + 8.01` | 99.42% |
| Buyback | `1.01 + 2.02 + 2.03 + 7.01 + 8.01` | 99.50% on 2,613 keyword matches |
| Dividend | `2.02 + 7.01 + 8.01` | 97.42% on 854 keyword matches |
| Restructuring | `2.02 + 2.05 + 5.02 + 7.01 + 8.01` | 95.70% on 768 keyword matches |
| Restructuring | `1.01 + 2.02 + 2.03 + 2.05 + 5.02 + 7.01 + 8.01` | 99.09% but noisier |

Exact Haiku-vs-baseline overlap numbers from the 840-filing sample:

| Job | Haiku yes | Baseline yes | Both | Haiku only | Baseline only | Baseline retained by Haiku | Haiku overlap with baseline |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Earnings | 254 | 267 | 249 | 5 | 18 | 93.26% | 98.03% |
| Buyback | 52 | 137 | 46 | 6 | 91 | 33.58% | 88.46% |
| Dividend | 71 | 94 | 46 | 25 | 48 | 48.94% | 64.79% |
| Restructuring | 80 | 120 | 51 | 29 | 69 | 42.50% | 63.75% |

These Haiku numbers are not exact ground-truth precision and recall. They are overlap metrics against the deterministic baseline.

## Post-Merge Clarification: Best Single-Number Estimate For Haiku-Only Error Rate

If forced to compress the current evidence into one number, the best estimate from the sampled disagreements is that Haiku-only is wrong about 20% of the time overall on the current four-job routing problem. This is an estimate, not a gold-set metric.

Best estimated Haiku-only error-rate by job family:

| Job | Best estimate of Haiku-only wrong rate | Confidence |
| --- | ---: | --- |
| Earnings | about 5% | highest confidence |
| Restructuring | about 10-15% | medium confidence |
| Buybacks | about 30% | medium confidence |
| Dividends | about 35% | medium confidence |

Interpretation: Haiku is strongest on messy earnings and restructuring routing, and weakest on buyback and dividend recall.

## Post-Merge Clarification: Sample Spot-Check Of Important Haiku Disagreements

I manually checked a targeted sample of the most decision-relevant disagreement filings against the actual filing text.

Haiku clearly missed real events in these sample cases:

- `0000875320-23-000004` (`VRTX`): real new `$3.0 billion` share repurchase authorization.
- `0001193125-23-088906` (`OVV`): real dividend increase announcement.
- `0001096752-23-000014` (`EPC`): real cash dividend declaration.
- `0001880661-23-000040` (`TPG`): real dividend declaration.
- `0001468174-23-000077` (`H`): real cash dividend declaration.

Haiku also appeared wrong in this direction:

- `0000005272-25-000036` (`AIG`): if Haiku routed this as buyback, that looked like a false positive. The clear new event was the dividend increase, while the buyback language looked historical/current-quarter capital return context.

Haiku was clearly right in these sample cases:

- `0001193125-25-044753` (`BL`): real workforce reduction under `8.01`.
- `0001810806-23-000044` (`U`): real reduction of about 600 employee roles under `2.05`.
- `0001628280-23-002424` (`TTWO`): real earnings filing under `9.01`-only.
- `0000051143-25-000007` (`IBM`): real earnings presentation under `7.01`.

Practical takeaway from the sample check:

- Haiku makes real mistakes on buybacks and dividends.
- Haiku is useful on messy `7.01`, `8.01`, and `9.01` earnings / restructuring routing.
- This is why Haiku is useful as a hybrid semantic router but not as the sole router.

## Post-Merge Clarification: Final Winner In Simple Terms

- Deterministic plus keyword rescues wins on recall safety for the current four jobs.
- Haiku wins as a semantic classifier inside ambiguous filing buckets.
- Hybrid wins overall because it combines deterministic recall guards with Haiku semantic fan-out.

---

## Verbatim Source 1: Base deterministic 8-K analysis

Original file: `8k_codex_analysis.md`


# 8-K Filing Analysis And Extraction Filter Validation

Validated against the live Neo4j graph at `bolt://localhost:30687` on the current workspace snapshot. Unless noted otherwise, the working corpus is the full 8-K family: `24,350` filings (`8-K` + `8-K/A`).

## Method

- Every numeric claim below comes from a Cypher query shown inline.
- I used `Report.formType IN ['8-K','8-K/A']` for the main corpus and cross-checked the total against `formType STARTS WITH '8-K'`.
- For keyword validation, I searched both `ExtractedSectionContent` and `ExhibitContent` via the live fulltext indexes and then inspected misses with raw section/exhibit previews.

## Part 0: Schema Verification

### Labels

```cypher
CALL db.labels() YIELD label
RETURN label
ORDER BY label
```

Relevant labels present in the graph:

`Company`, `ExhibitContent`, `ExtractedSectionContent`, `FilingTextContent`, `FinancialStatementContent`, `Report`

### Relationship Types

```cypher
CALL db.relationshipTypes() YIELD relationshipType
RETURN relationshipType
ORDER BY relationshipType
```

Relevant relationship types present in the graph:

`HAS_EXHIBIT`, `HAS_FILING_TEXT`, `HAS_FINANCIAL_STATEMENT`, `HAS_SECTION`, `PRIMARY_FILER`

### `Report` Properties

```cypher
CALL apoc.meta.nodeTypeProperties({includeLabels: ['Report']})
YIELD propertyName, propertyTypes
RETURN propertyName, propertyTypes
ORDER BY propertyName
```

| Property | Types |
| --- | --- |
| accessionNo | String |
| cik | String |
| created | String |
| description | String |
| entities | String |
| exhibit_contents | String |
| exhibits | String |
| extracted_sections | String |
| financial_statements | String |
| formType | String |
| guidance_status | String |
| id | String |
| isAmendment | Boolean |
| is_xml | Boolean |
| items | String |
| linkToFilingDetails | String |
| linkToHtml | String |
| linkToTxt | String |
| market_session | String |
| periodOfReport | String |
| primaryDocumentUrl | String |
| returns_schedule | String |
| symbols | String |
| xbrl_error | String |
| xbrl_status | String |

### Relevant Relationship Property Schemas

```cypher
CALL apoc.meta.relTypeProperties({
  includeRels: ['PRIMARY_FILER','HAS_SECTION','HAS_EXHIBIT','HAS_FILING_TEXT','HAS_FINANCIAL_STATEMENT']
})
YIELD relType, propertyName, propertyTypes
RETURN relType, propertyName, propertyTypes
ORDER BY relType, propertyName
```

| Relationship | Property | Types |
| --- | --- | --- |
| :`HAS_EXHIBIT` | None | None |
| :`HAS_FILING_TEXT` | None | None |
| :`HAS_FINANCIAL_STATEMENT` | None | None |
| :`HAS_SECTION` | None | None |
| :`PRIMARY_FILER` | created_at | String |
| :`PRIMARY_FILER` | daily_industry | Double |
| :`PRIMARY_FILER` | daily_macro | Double |
| :`PRIMARY_FILER` | daily_sector | Double |
| :`PRIMARY_FILER` | daily_stock | Double |
| :`PRIMARY_FILER` | hourly_industry | Double |
| :`PRIMARY_FILER` | hourly_macro | Double |
| :`PRIMARY_FILER` | hourly_sector | Double |
| :`PRIMARY_FILER` | hourly_stock | Double |
| :`PRIMARY_FILER` | session_industry | Double |
| :`PRIMARY_FILER` | session_macro | Double |
| :`PRIMARY_FILER` | session_sector | Double |
| :`PRIMARY_FILER` | session_stock | Double |
| :`PRIMARY_FILER` | symbol | String |

Key verification result: `PRIMARY_FILER` is the relationship that carries filing-level returns, while sections, exhibits, filing text, and financial statements sit on separate content relationships off `Report`.

## Part 1: Complete 8-K Taxonomy

### 1.1 Form Counts

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
RETURN r.formType AS form_type, count(*) AS filings
ORDER BY form_type
```

| Form | Filings | % of 8-K Family |
| --- | --- | --- |
| 8-K | 23,836 | 97.9% |
| 8-K/A | 514 | 2.1% |

Cross-check query:

```cypher
MATCH (r:Report)
WHERE r.formType STARTS WITH '8-K'
RETURN count(*) AS total_8k_family
```

Result: `24,350` total filings with `formType STARTS WITH '8-K'`, exactly matching the sum of the table above.

Data-quality check:

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
RETURN
  sum(CASE WHEN r.items IS NULL OR trim(r.items) = '' THEN 1 ELSE 0 END) AS null_or_empty_items,
  sum(CASE WHEN r.created IS NULL THEN 1 ELSE 0 END) AS null_created,
  sum(CASE WHEN r.market_session IS NULL OR trim(r.market_session) = '' THEN 1 ELSE 0 END) AS null_market_session
```

| Null / Empty `items` | Null `created` | Null `market_session` |
| --- | --- | --- |
| 2 | 0 | 0 |

### 1.2 Distinct Item Codes

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A'] AND r.items IS NOT NULL
UNWIND apoc.convert.fromJsonList(r.items) AS item
WITH replace(trim(split(item, ':')[0]), 'Item ', '') AS item_code, count(DISTINCT r) AS filings
RETURN item_code, filings
ORDER BY filings DESC, item_code
```

| Item | SEC Title | Filings | % of 8-K Family | Top Co-occurrences |
| --- | --- | --- | --- | --- |
| 9.01 | Financial Statements and Exhibits | 19,140 | 78.6% | 2.02 (8,727), 7.01 (5,147), 8.01 (3,854) |
| 2.02 | Results of Operations and Financial Condition | 8,905 | 36.6% | 9.01 (8,727), 7.01 (1,830), 8.01 (632) |
| 7.01 | Regulation FD Disclosure | 5,844 | 24.0% | 9.01 (5,147), 2.02 (1,830), 5.02 (1,098) |
| 5.02 | Departure or Appointment of Officers and Directors | 5,335 | 21.9% | 9.01 (3,373), 7.01 (1,098), 5.07 (528) |
| 8.01 | Other Events | 4,793 | 19.7% | 9.01 (3,854), 2.02 (632), 7.01 (592) |
| 1.01 | Entry into a Material Definitive Agreement | 2,550 | 10.5% | 9.01 (2,345), 2.03 (1,403), 8.01 (586) |
| 5.07 | Submission of Matters to a Vote of Security Holders | 2,368 | 9.7% | 9.01 (952), 5.02 (528), 5.03 (275) |
| 2.03 | Creation of a Direct Financial Obligation | 1,496 | 6.1% | 1.01 (1,403), 9.01 (1,370), 8.01 (341) |
| 5.03 | Amendments to Articles or Bylaws; Change in Fiscal Year | 843 | 3.5% | 9.01 (787), 5.07 (275), 5.02 (203) |
| 3.02 | Unregistered Sales of Equity Securities | 310 | 1.3% | 9.01 (270), 1.01 (214), 8.01 (154) |
| 1.02 | Termination of a Material Definitive Agreement | 283 | 1.2% | 9.01 (220), 1.01 (195), 2.03 (153) |
| 2.05 | Costs Associated with Exit or Disposal Activities | 234 | 1.0% | 9.01 (137), 2.02 (79), 7.01 (73) |
| 2.01 | Completion of Acquisition or Disposition of Assets | 198 | 0.8% | 9.01 (191), 7.01 (104), 1.01 (77) |
| 3.03 | Material Modification to Rights of Security Holders | 127 | 0.5% | 9.01 (124), 5.03 (108), 8.01 (47) |
| 2.06 | Material Impairments | 57 | 0.2% | 2.05 (27), 9.01 (27), 7.01 (21) |
| 3.01 | Notice of Delisting or Transfer of Listing | 55 | 0.2% | 9.01 (45), 5.02 (21), 5.03 (20) |
| 4.01 | Changes in Registrant's Certifying Accountant | 44 | 0.2% | 9.01 (39), 7.01 (2), 8.01 (2) |
| 5.01 | Changes in Control of Registrant | 24 | 0.1% | 9.01 (21), 2.01 (17), 3.01 (17) |
| 1.05 | Material Cybersecurity Incidents | 18 | 0.1% | 9.01 (4), 7.01 (2) |
| 1.04 | Mine Safety Reporting | 15 | 0.1% | 9.01 (1) |
| 2.04 | Triggering Events That Accelerate Financial Obligations | 15 | 0.1% | 9.01 (8), 1.01 (6), 2.03 (5) |
| 4.02 | Non-Reliance on Previously Issued Financial Statements | 15 | 0.1% | 9.01 (9), 2.02 (8), 7.01 (4) |
| 5.04 | Temporary Suspension of Trading Under Benefit Plans | 10 | 0.0% | 9.01 (8) |
| 5.08 | Shareholder Director Nominations | 10 | 0.0% | 8.01 (7), 9.01 (4), 3.01 (1) |
| 5.05 | Amendments to Code of Ethics or Waiver | 7 | 0.0% | 9.01 (7), 5.03 (2), 5.02 (1) |
| 1.03 | Bankruptcy or Receivership | 1 | 0.0% | 2.04 (1), 7.01 (1), 9.01 (1) |

Observed but absent standard items:

`5.06`

Interpretation:

- `9.01` is the dominant administrative companion item. It signals attachments and should not be treated as the primary business event.
- `2.02`, `7.01`, and `9.01` form the earnings / investor-materials cluster.
- `1.01` and `2.03` form the contracts / financing cluster.
- `5.02` and `5.07` are the major governance-heavy items; `5.07` is notably stand-alone more often than most other items.

### 1.3 Items Per Filing

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A'] AND r.items IS NOT NULL
WITH size(apoc.convert.fromJsonList(r.items)) AS item_count
RETURN item_count, count(*) AS filings
ORDER BY item_count
```

| Items per Filing | Filings | % of 8-K Family |
| --- | --- | --- |
| 1 | 4,747 | 19.5% |
| 2 | 12,782 | 52.5% |
| 3 | 5,368 | 22.0% |
| 4 | 1,128 | 4.6% |
| 5 | 236 | 1.0% |
| 6 | 53 | 0.2% |
| 7 | 13 | 0.1% |
| 8 | 13 | 0.1% |
| 9 | 5 | 0.0% |
| 10 | 1 | 0.0% |
| 11 | 2 | 0.0% |

Takeaway: two-item filings dominate the corpus, which is why companion-item analysis matters. Single-item filings are the minority.

### 1.4 Most Common Full Item Combinations

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A'] AND r.items IS NOT NULL
WITH r,
     [item IN apoc.convert.fromJsonList(r.items) | replace(trim(split(item, ':')[0]), 'Item ', '')] AS item_codes
RETURN
  apoc.text.join(item_codes, ' + ') AS item_code_combo,
  r.items AS raw_items,
  count(*) AS filings
ORDER BY filings DESC, item_code_combo
LIMIT 30
```

| Item-Code Combo | Filings | % of 8-K Family | Raw `items` String |
| --- | --- | --- | --- |
| 2.02 + 9.01 | 6,202 | 25.5% | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] |
| 8.01 + 9.01 | 2,006 | 8.2% | ["Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] |
| 5.02 | 1,740 | 7.1% | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers"] |
| 7.01 + 9.01 | 1,597 | 6.6% | ["Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] |
| 2.02 + 7.01 + 9.01 | 1,473 | 6.0% | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] |
| 5.02 + 9.01 | 1,412 | 5.8% | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 9.01: Financial Statements and Exhibits"] |
| 5.07 | 1,254 | 5.1% | ["Item 5.07: Submission of Matters to a Vote of Security Holders"] |
| 5.02 + 7.01 + 9.01 | 828 | 3.4% | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] |
| 8.01 | 717 | 2.9% | ["Item 8.01: Other Events"] |
| 1.01 + 2.03 + 9.01 | 707 | 2.9% | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 2.03: Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant", "Item 9.01: Financial Statements and Exhibits"] |
| 7.01 | 519 | 2.1% | ["Item 7.01: Regulation FD Disclosure"] |
| 2.02 + 8.01 + 9.01 | 393 | 1.6% | ["Item 2.02: Results of Operations and Financial Condition", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] |
| 1.01 + 9.01 | 383 | 1.6% | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 9.01: Financial Statements and Exhibits"] |
| 5.02 + 5.07 + 9.01 | 301 | 1.2% | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 5.07: Submission of Matters to a Vote of Security Holders", "Item 9.01: Financial Statements and Exhibits"] |
| 5.03 + 9.01 | 301 | 1.2% | ["Item 5.03: Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year", "Item 9.01: Financial Statements and Exhibits"] |
| 7.01 + 8.01 + 9.01 | 267 | 1.1% | ["Item 7.01: Regulation FD Disclosure", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] |
| 5.07 + 9.01 | 241 | 1.0% | ["Item 5.07: Submission of Matters to a Vote of Security Holders", "Item 9.01: Financial Statements and Exhibits"] |
| 1.01 + 8.01 + 9.01 | 181 | 0.7% | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] |
| 1.01 + 7.01 + 9.01 | 180 | 0.7% | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] |
| 2.02 + 5.02 + 9.01 | 180 | 0.7% | ["Item 2.02: Results of Operations and Financial Condition", "Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 9.01: Financial Statements and Exhibits"] |
| 1.01 + 2.03 + 8.01 + 9.01 | 167 | 0.7% | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 2.03: Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] |
| 5.02 + 8.01 + 9.01 | 152 | 0.6% | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] |
| 2.02 + 7.01 + 8.01 + 9.01 | 145 | 0.6% | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] |
| 5.03 + 5.07 + 9.01 | 144 | 0.6% | ["Item 5.03: Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year", "Item 5.07: Submission of Matters to a Vote of Security Holders", "Item 9.01: Financial Statements and Exhibits"] |
| 9.01 | 114 | 0.5% | ["Item 9.01: Financial Statements and Exhibits"] |
| 2.02 | 108 | 0.4% | ["Item 2.02: Results of Operations and Financial Condition"] |
| 1.01 + 1.02 + 2.03 + 9.01 | 96 | 0.4% | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 1.02: Termination of a Material Definitive Agreement", "Item 2.03: Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant", "Item 9.01: Financial Statements and Exhibits"] |
| 5.02 + 5.07 | 90 | 0.4% | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 5.07: Submission of Matters to a Vote of Security Holders"] |
| 1.01 + 2.03 + 7.01 + 9.01 | 85 | 0.3% | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 2.03: Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] |
| 2.02 + 5.02 + 7.01 + 9.01 | 85 | 0.3% | ["Item 2.02: Results of Operations and Financial Condition", "Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] |

Natural clusters:

- `2.02 + 9.01` is the canonical earnings-release package.
- `2.02 + 7.01 + 9.01` is the richer earnings package: press release plus presentation / prepared remarks.
- `1.01 + 2.03 + 9.01` is the canonical financing package: debt or credit agreement plus attached contracts.
- `5.02` often appears alone or with `9.01`, reflecting the fact that executive changes are usually self-contained in the section body.

### 1.5 Market Session Distribution

Stored session query:

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
RETURN coalesce(r.market_session, '<null>') AS market_session, count(*) AS filings
ORDER BY filings DESC, market_session
```

| Stored `market_session` | Filings | % of 8-K Family |
| --- | --- | --- |
| post_market | 14,762 | 60.6% |
| pre_market | 8,206 | 33.7% |
| in_market | 1,027 | 4.2% |
| market_closed | 355 | 1.5% |

Derived local-time bucket query:

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A'] AND r.created IS NOT NULL
WITH localtime(datetime(r.created)) AS filed_time
RETURN CASE
  WHEN filed_time < localtime('09:30:00') THEN 'pre_market'
  WHEN filed_time < localtime('16:00:00') THEN 'in_market'
  WHEN filed_time < localtime('20:00:00') THEN 'post_market'
  ELSE 'market_closed'
END AS derived_bucket,
count(*) AS filings
ORDER BY filings DESC, derived_bucket
```

| Derived Bucket | Filings | % of 8-K Family |
| --- | --- | --- |
| post_market | 14,824 | 60.9% |
| pre_market | 8,209 | 33.7% |
| in_market | 1,035 | 4.3% |
| market_closed | 282 | 1.2% |

Mismatch audit:

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A'] AND r.created IS NOT NULL
WITH r, localtime(datetime(r.created)) AS filed_time
WITH r, CASE
  WHEN filed_time < localtime('09:30:00') THEN 'pre_market'
  WHEN filed_time < localtime('16:00:00') THEN 'in_market'
  WHEN filed_time < localtime('20:00:00') THEN 'post_market'
  ELSE 'market_closed'
END AS derived_bucket
RETURN r.market_session AS stored_bucket, derived_bucket, count(*) AS filings
ORDER BY filings DESC, stored_bucket, derived_bucket
```

| Stored | Derived | Filings |
| --- | --- | --- |
| post_market | post_market | 14,762 |
| pre_market | pre_market | 8,206 |
| in_market | in_market | 1,026 |
| market_closed | market_closed | 282 |
| market_closed | post_market | 61 |
| market_closed | in_market | 9 |
| market_closed | pre_market | 3 |
| in_market | post_market | 1 |

Interpretation: the stored `market_session` field is usable. The small mismatch bucket is mostly `market_closed` filings submitted on weekends / holidays where local clock time alone is not enough.

## Part 2: Content Layer Analysis

### 2.1 Content-Layer Presence

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
WITH r,
  EXISTS { MATCH (r)-[:HAS_SECTION]->(:ExtractedSectionContent) } AS has_section,
  EXISTS { MATCH (r)-[:HAS_EXHIBIT]->(:ExhibitContent) } AS has_exhibit,
  EXISTS { MATCH (r)-[:HAS_FILING_TEXT]->(:FilingTextContent) } AS has_filing_text,
  EXISTS { MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(:FinancialStatementContent) } AS has_financial_statement
RETURN
  count(*) AS total_filings,
  sum(CASE WHEN has_section THEN 1 ELSE 0 END) AS with_sections,
  sum(CASE WHEN has_exhibit THEN 1 ELSE 0 END) AS with_exhibits,
  sum(CASE WHEN has_filing_text THEN 1 ELSE 0 END) AS with_filing_text,
  sum(CASE WHEN has_financial_statement THEN 1 ELSE 0 END) AS with_financial_statements
```

| Layer | Filings With Layer | % of 8-K Family |
| --- | --- | --- |
| Sections | 24,295 | 99.8% |
| Exhibits | 16,188 | 66.5% |
| Filing text | 501 | 2.1% |
| Financial statements | 0 | 0.0% |

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
WITH r,
  EXISTS { MATCH (r)-[:HAS_SECTION]->(:ExtractedSectionContent) } AS has_section,
  EXISTS { MATCH (r)-[:HAS_EXHIBIT]->(:ExhibitContent) } AS has_exhibit,
  EXISTS { MATCH (r)-[:HAS_FILING_TEXT]->(:FilingTextContent) } AS has_filing_text,
  EXISTS { MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(:FinancialStatementContent) } AS has_financial_statement
RETURN has_section, has_exhibit, has_filing_text, has_financial_statement, count(*) AS filings
ORDER BY filings DESC
```

| Has Section | Has Exhibit | Has Filing Text | Has Financial Statement | Filings | % of 8-K Family |
| --- | --- | --- | --- | --- | --- |
| True | True | False | False | 15,827 | 65.0% |
| True | False | False | False | 7,967 | 32.7% |
| True | True | True | False | 333 | 1.4% |
| True | False | True | False | 168 | 0.7% |
| False | True | False | False | 28 | 0.1% |
| False | False | False | False | 27 | 0.1% |

Cross-check: the combination counts above sum exactly to the corpus total and reproduce the same layer totals as the first query.

Contentless sample filings:

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
  AND NOT EXISTS { MATCH (r)-[:HAS_SECTION]->(:ExtractedSectionContent) }
  AND NOT EXISTS { MATCH (r)-[:HAS_EXHIBIT]->(:ExhibitContent) }
MATCH (r)-[:PRIMARY_FILER]->(c:Company)
RETURN r.accessionNo AS accession, c.ticker AS ticker, r.formType AS form_type, r.items AS raw_items
ORDER BY r.created DESC
LIMIT 10
```

| Accession | Ticker | Form | Raw `items` |
| --- | --- | --- | --- |
| 0001688568-25-000064 | DXC | 8-K | ["Item 5.07: Submission of Matters to a Vote of Security Holders"] |
| 0001104659-25-037502 | EQT | 8-K | ["Item 3.02: Unregistered Sales of Equity Securities"] |
| 0000950170-25-042330 | CBRE | 8-K | ["Item 7.01: Regulation FD Disclosure"] |
| 0001086222-25-000054 | AKAM | 8-K | ["Item 9.01: Financial Statements and Exhibits"] |
| 0000851310-24-000101 | HLIT | 8-K | ["Item 5.01: Changes in Control of Registrant"] |
| 0000950170-24-123117 | PRI | 8-K/A | ["Item 2.05: Cost Associated with Exit or Disposal Activities", "Item 2.06: Material Impairments"] |
| 0000007084-24-000034 | ADM | 8-K | ["Item 4.02: Non-Reliance on Previously Issued Financial Statements or a Related Audit Report or Completed Interim Review"] |
| 0001835632-24-000151 | MRVL | 8-K | ["Item 5.01: Changes in Control of Registrant"] |
| 0001193125-24-088517 | MKTX | 8-K | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers"] |
| 0001562088-24-000058 | DUOL | 8-K | None |

### 2.2 Distinct Section Names

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
RETURN
  s.section_name AS section_name,
  count(*) AS section_nodes,
  count(DISTINCT r) AS filings,
  round(avg(size(coalesce(s.content, ''))), 1) AS avg_chars
ORDER BY filings DESC, section_name
```

| Section Name | Section Nodes | Filings | Avg Chars |
| --- | --- | --- | --- |
| FinancialStatementsandExhibits | 19,061 | 19,061 | 534.3 |
| ResultsofOperationsandFinancialCondition | 8,824 | 8,824 | 1,053.8 |
| RegulationFDDisclosure | 5,732 | 5,732 | 1,453.9 |
| DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers | 5,298 | 5,298 | 2,385.2 |
| OtherEvents | 4,758 | 4,758 | 2,280.6 |
| EntryintoaMaterialDefinitiveAgreement | 2,540 | 2,540 | 4,433.1 |
| SubmissionofMatterstoaVoteofSecurityHolders | 2,364 | 2,364 | 2,513.3 |
| CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant | 1,490 | 1,490 | 783.5 |
| AmendmentstoArticlesofIncorporationorBylaws;ChangeinFiscalYear | 838 | 838 | 1,679.9 |
| UnregisteredSalesofEquitySecurities | 305 | 305 | 1,248.4 |
| TerminationofaMaterialDefinitiveAgreement | 281 | 281 | 904.7 |
| CostsAssociatedwithExitorDisposalActivities | 232 | 232 | 2,768.5 |
| CompletionofAcquisitionorDispositionofAssets | 184 | 184 | 2,342.4 |
| MaterialModificationstoRightsofSecurityHolders | 127 | 127 | 1,770.3 |
| MaterialImpairments | 55 | 55 | 1,714.3 |
| NoticeofDelistingorFailuretoSatisfyaContinuedListingRuleorStandard;TransferofListing | 55 | 55 | 1,539 |
| ChangesinRegistrantsCertifyingAccountant | 43 | 43 | 3,375.8 |
| ChangesinControlofRegistrant | 21 | 21 | 1,097.1 |
| MaterialCybersecurityIncidents | 18 | 18 | 3,317.4 |
| MineSafetyReportingofShutdownsandPatternsofViolations | 15 | 15 | 707.9 |
| TriggeringEventsThatAccelerateorIncreaseaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangement | 15 | 15 | 1,431.6 |
| NonRelianceonPreviouslyIssuedFinancialStatementsoraRelatedAuditReportorCompletedInterimReview | 14 | 14 | 5,280.1 |
| ShareholderNominationsPursuanttoExchangeActRule14a-11 | 10 | 10 | 952.2 |
| TemporarySuspensionofTradingUnderRegistrantsEmployeeBenefitPlans | 10 | 10 | 2,744.5 |
| AmendmentstotheRegistrantsCodeofEthics,orWaiverofaProvisionoftheCodeofEthics | 7 | 7 | 963.1 |
| BankruptcyorReceivership | 1 | 1 | 2,163 |

### 2.3 Distinct Exhibit Numbers

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
RETURN
  e.exhibit_number AS exhibit_number,
  count(*) AS exhibit_nodes,
  count(DISTINCT r) AS filings,
  round(avg(size(coalesce(e.content, ''))), 1) AS avg_chars
ORDER BY filings DESC, exhibit_number
```

| Exhibit Number | Exhibit Nodes | Filings | Avg Chars |
| --- | --- | --- | --- |
| EX-99.1 | 14,319 | 14,319 | 23,886.3 |
| EX-99.2 | 2,726 | 2,726 | 32,973 |
| EX-10.1 | 2,390 | 2,390 | 202,294 |
| EX-10.2 | 605 | 605 | 113,079.3 |
| EX-99.3 | 386 | 386 | 29,646 |
| EX-10.3 | 234 | 234 | 86,027.4 |
| EX-10.4 | 113 | 113 | 78,792.9 |
| EX-99.01 | 96 | 96 | 27,516.1 |
| EX-99.4 | 73 | 73 | 29,864.7 |
| EX-10.5 | 47 | 47 | 73,411.6 |
| EX-10.6 | 25 | 25 | 88,542.9 |
| EX-99.1 CHARTER | 25 | 25 | 10,256.7 |
| EX-99.5 | 22 | 22 | 26,017.4 |
| EX-10.7 | 13 | 13 | 115,388.8 |
| EX-99.1(A) | 8 | 8 | 35,648 |
| EX-10.8 | 7 | 7 | 84,855.1 |
| EX-10.9 | 7 | 7 | 96,285 |
| EX-99.6 | 7 | 7 | 21,498.4 |
| EX-10.01 | 6 | 6 | 190,012 |
| EX-99.02 | 6 | 6 | 23,763.3 |
| EX-99.7 | 5 | 5 | 15,002.2 |
| EX-99.1A | 4 | 4 | 27,114.8 |
| EX-10.12 | 3 | 3 | 81,516 |
| EX-10.1A | 3 | 3 | 33,482.7 |
| EX-10.1B | 3 | 3 | 26,010 |
| EX-10.1C | 3 | 3 | 24,190.7 |
| EX-10.1D | 3 | 3 | 25,168.7 |
| EX-99.1B | 3 | 3 | 20,077 |
| EX-99.1PRE | 3 | 3 | 8,912 |
| EX-99.8 | 3 | 3 | 15,829 |
| EX-99.9 | 3 | 3 | 35,600.3 |
| EX-10.10 | 2 | 2 | 100,023.5 |
| EX-10.11 | 2 | 2 | 96,975 |
| EX-10.13 | 2 | 2 | 96,923 |
| EX-10.15 | 2 | 2 | 52,108.5 |
| EX-10.1E | 2 | 2 | 154,043.5 |
| EX-10.1F | 2 | 2 | 254,174 |
| EX-10.1G | 2 | 2 | 4,366.5 |
| EX-10.1H | 2 | 2 | 21,881 |
| EX-10.1I | 2 | 2 | 11,718 |
| EX-10.1J | 2 | 2 | 7,091.5 |
| EX-10.1K | 2 | 2 | 6,517.5 |
| EX-10.1L | 2 | 2 | 1,065 |
| EX-10.A | 2 | 2 | 32,414.5 |
| EX-99.10 | 2 | 2 | 26,543 |
| EX-99.11 | 2 | 2 | 34,793 |
| EX-99.12 | 2 | 2 | 12,248.5 |
| EX-10.1 2 | 1 | 1 | 397,540 |
| EX-10.10(M) | 1 | 1 | 855,326 |
| EX-10.10(N) | 1 | 1 | 818,617 |
| EX-10.10(O) | 1 | 1 | 841,043 |
| EX-10.10(P) | 1 | 1 | 832,129 |
| EX-10.12K | 1 | 1 | 36,807 |
| EX-10.16 | 1 | 1 | 670,222 |
| EX-10.18 | 1 | 1 | 69,330 |
| EX-10.1M | 1 | 1 | 8,601 |
| EX-10.1N | 1 | 1 | 39,937 |
| EX-10.1O | 1 | 1 | 1,053 |
| EX-10.1P | 1 | 1 | 4,322 |
| EX-10.1Q | 1 | 1 | 48,068 |
| EX-10.1R | 1 | 1 | 5,722 |
| EX-10.25 | 1 | 1 | 14,597 |
| EX-10.26 | 1 | 1 | 14,563 |
| EX-10.27 | 1 | 1 | 14,472 |
| EX-10.32 | 1 | 1 | 54,708 |
| EX-10.36 | 1 | 1 | 21,207 |
| EX-10.37 | 1 | 1 | 15,660 |
| EX-10.40 | 1 | 1 | 12,813 |
| EX-10.5 10 | 1 | 1 | 26,682 |
| EX-10.5 11 | 1 | 1 | 27,153 |
| EX-10.5 8 | 1 | 1 | 25,811 |
| EX-10.5 9 | 1 | 1 | 25,129 |
| EX-10.56 | 1 | 1 | 32,378 |
| EX-10.62 | 1 | 1 | 406,078 |
| EX-10.6A | 1 | 1 | 161,391 |
| EX-10.6B | 1 | 1 | 86,690 |
| EX-10.74 | 1 | 1 | 378,455 |
| EX-10.75 | 1 | 1 | 300,406 |
| EX-10.7D | 1 | 1 | 484,363 |
| EX-10.7E | 1 | 1 | 29,085 |
| EX-10.8A | 1 | 1 | 118,054 |
| EX-10.EXECSEVPLAN | 1 | 1 | 29,990 |
| EX-10.III | 1 | 1 | 13,068 |
| EX-99.(10)(1) | 1 | 1 | 5,757 |
| EX-99.-1 | 1 | 1 | 26,737 |
| EX-99.03 | 1 | 1 | 112,347 |
| EX-99.04 | 1 | 1 | 123,645 |
| EX-99.05 | 1 | 1 | 109,299 |
| EX-99.1 PR Q3 F23 EA | 1 | 1 | 36,606 |
| EX-99.13 | 1 | 1 | 59,898 |
| EX-99.14 | 1 | 1 | 36,950 |
| EX-99.15 | 1 | 1 | 19,855 |
| EX-99.16 | 1 | 1 | 4,867 |
| EX-99.17 | 1 | 1 | 40,691 |
| EX-99.18 | 1 | 1 | 11,800 |
| EX-99.19 | 1 | 1 | 6,715 |
| EX-99.2 Q3 F23 SUPPL | 1 | 1 | 15,839 |
| EX-99.20 | 1 | 1 | 6,989 |
| EX-99.21 | 1 | 1 | 9,995 |
| EX-99.22 | 1 | 1 | 2,220 |
| EX-99.3 PR APPOINTME | 1 | 1 | 2,745 |
| EX-99.A | 1 | 1 | 61 |
| EX-99.EX-99 | 1 | 1 | 8,901 |
| EX-99.EX-99_1 | 1 | 1 | 25,720 |
| EX-99.EX-99_2 | 1 | 1 | 2,853 |

### 2.4 Financial Statements On 8-Ks

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
OPTIONAL MATCH (r)-[:HAS_FINANCIAL_STATEMENT]->(fs:FinancialStatementContent)
RETURN
  count(DISTINCT fs) AS financial_statement_nodes,
  count(DISTINCT CASE WHEN fs IS NOT NULL THEN r END) AS filings_with_financial_statements,
  collect(DISTINCT fs.statement_type) AS statement_types
```

| FS Nodes | Filings With FS | Statement Types |
| --- | --- | --- |
| 0 | 0 |  |

Result: financial statements do not appear as `FinancialStatementContent` on the 8-K family in this graph.

### 2.5 Per-Item Content Profiles

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A'] AND r.items IS NOT NULL
WITH r, [item IN apoc.convert.fromJsonList(r.items) | replace(trim(split(item, ':')[0]), 'Item ', '')] AS item_codes
WHERE $item_code IN item_codes
WITH r,
  EXISTS { MATCH (r)-[:HAS_SECTION]->(:ExtractedSectionContent) } AS has_section,
  EXISTS { MATCH (r)-[:HAS_EXHIBIT]->(:ExhibitContent) } AS has_exhibit
RETURN
  count(*) AS filings,
  sum(CASE WHEN has_section THEN 1 ELSE 0 END) AS with_sections,
  sum(CASE WHEN has_exhibit THEN 1 ELSE 0 END) AS with_exhibits,
  sum(CASE WHEN has_section AND has_exhibit THEN 1 ELSE 0 END) AS with_both,
  sum(CASE WHEN has_section AND NOT has_exhibit THEN 1 ELSE 0 END) AS section_only,
  sum(CASE WHEN has_exhibit AND NOT has_section THEN 1 ELSE 0 END) AS exhibit_only,
  sum(CASE WHEN NOT has_section AND NOT has_exhibit THEN 1 ELSE 0 END) AS neither
```

| Item | Filings | With Exhibits | Section Only | Both | Pointer-Like Sections | Avg Section Chars | Top Exhibit Numbers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2.02 | 8,905 | 8,331 (93.6%) | 570 (6.4%) | 8,314 (93.4%) | 7,848/8,824 | 1,053.8 | EX-99.1 (8,247), EX-99.2 (2,047), EX-99.3 (290), EX-10.1 (108), EX-99.01 (68) |
| 7.01 | 5,844 | 4,974 (85.1%) | 867 (14.8%) | 4,955 (84.8%) | 3,808/5,732 | 1,453.9 | EX-99.1 (4,897), EX-99.2 (1,401), EX-10.1 (445), EX-99.3 (253), EX-10.2 (131) |
| 1.01 | 2,550 | 1,755 (68.8%) | 794 (31.1%) | 1,754 (68.8%) | 1,606/2,540 | 4,433.1 | EX-10.1 (1,272), EX-99.1 (845), EX-10.2 (310), EX-99.2 (213), EX-10.3 (110) |
| 5.02 | 5,335 | 2,970 (55.7%) | 2,356 (44.2%) | 2,965 (55.6%) | 1,682/5,298 | 2,385.2 | EX-99.1 (2,173), EX-10.1 (1,150), EX-10.2 (308), EX-99.2 (160), EX-10.3 (131) |
| 8.01 | 4,793 | 3,057 (63.8%) | 1,734 (36.2%) | 3,053 (63.7%) | 2,433/4,758 | 2,280.6 | EX-99.1 (2,928), EX-99.2 (588), EX-10.1 (298), EX-99.3 (101), EX-10.2 (90) |
| 5.07 | 2,368 | 471 (19.9%) | 1,895 (80.0%) | 471 (19.9%) | 33/2,364 | 2,513.3 | EX-10.1 (300), EX-99.1 (180), EX-10.2 (66), EX-10.3 (23), EX-99.2 (18) |
| 2.03 | 1,496 | 989 (66.1%) | 507 (33.9%) | 989 (66.1%) | 561/1,490 | 783.5 | EX-10.1 (801), EX-99.1 (361), EX-10.2 (194), EX-99.2 (82), EX-10.3 (60) |

Interpretation by item:

- `2.02` and `7.01` are exhibit-heavy and often use a short routing section that points to `EX-99.x` content.
- `1.01` and `2.03` are mixed: the section summarizes, while the legally operative language sits in `EX-10.x`.
- `5.02`, `8.01`, and `5.07` rely much more on the section body. `5.07` is the cleanest section-first item in the corpus.

### 2.6 Multi-Item Evidence

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A'] AND r.items IS NOT NULL
WITH r, [item IN apoc.convert.fromJsonList(r.items) | replace(trim(split(item, ':')[0]), 'Item ', '')] AS item_codes
WHERE item_codes = $item_codes
MATCH (r)-[:PRIMARY_FILER]->(c:Company)
OPTIONAL MATCH (r)-[:HAS_SECTION]->(s:ExtractedSectionContent)
OPTIONAL MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
RETURN
  r.accessionNo AS accession,
  c.ticker AS ticker,
  r.created AS created,
  collect(DISTINCT {section_name: s.section_name, preview: substring(coalesce(s.content, ''), 0, 220)}) AS sections,
  collect(DISTINCT {exhibit_number: e.exhibit_number, preview: substring(coalesce(e.content, ''), 0, 220)}) AS exhibits
ORDER BY r.created DESC
LIMIT 2
```

#### Example: `2.02+8.01+9.01`

| Accession | Ticker | Created | Sections | Exhibits |
| --- | --- | --- | --- | --- |
| 0001089063-25-000105 | DKS | 2025-08-28T07:02:12-04:00 | ResultsofOperationsandFinancialCondition: ITEM 2.02. RESULTS OF OPERATIONS AND FINANCIAL CONDITION On August 28, 2025, the Company i \| OtherEvents: ITEM 8.01. OTHER EVENTS On August 27, 2025, the Board of Directors of Dick's Sporting Good \| FinancialStatementsandExhibits: ITEM 9.01. FINANCIAL STATEMENTS AND EXHIBITS (d) Exhibits. The following exhibits are bein | EX-99.1: Exhibit 99.1 FOR IMMEDIATE RELEASE DICK'S Sporting Goods Reports Second Quarter Results; R |
| 0000896878-25-000031 | INTU | 2025-08-21T16:02:20-04:00 | ResultsofOperationsandFinancialCondition: ITEM 2.02 RESULTS OF OPERATIONS AND FINANCIAL CONDITION. On August 21, 2025, Intuit Inc. a \| OtherEvents: ITEM 8.01 OTHER EVENTS. On August 21, 2025, Intuit also announced that its Board of Direct \| FinancialStatementsandExhibits: ITEM 9.01 FINANCIAL STATEMENTS AND EXHIBITS. (d) Exhibits 99.01 Press release issued on Au | EX-99.01: Exhibit 99.01 Contacts: Investors Media Kim Watkins Kali Fry Intuit Inc. Intuit Inc. 650-9 |

#### Example: `1.01+2.03+9.01`

| Accession | Ticker | Created | Sections | Exhibits |
| --- | --- | --- | --- | --- |
| 0000012927-25-000064 | BA | 2025-08-28T17:00:55-04:00 | EntryintoaMaterialDefinitiveAgreement: Item 1.01. Entry into a Material Definitive Agreement. On August 25, 2025, The Boeing Comp \| CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant: Item 2.03. Creation of a Direct Financial Obligation or an Obligation Under an Off-Balance \| FinancialStatementsandExhibits: Item 9.01. Financial Statements and Exhibits. (d) Exhibits. Exhibit Number Description 10. | EX-10.1: Exhibit 10.1 THE BOEING COMPANY 364-DAY CREDIT AGREEMENT among THE BOEING COMPANY for itse |
| 0001193125-25-189845 | CAH | 2025-08-27T17:02:44-04:00 | EntryintoaMaterialDefinitiveAgreement: Item 1.01. Entry Into a Material Definitive Agreement. On August 27, 2025, Cardinal Health \| CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant: Item 2.03. Creation of a Direct Financial Obligation or an Obligation under an Off-Balance \| FinancialStatementsandExhibits: Item 9.01. Financial Statements and Exhibits. (d) Exhibits Exhibit No. Description 4.1 Ind |  |

#### Example: `5.07`

| Accession | Ticker | Created | Sections | Exhibits |
| --- | --- | --- | --- | --- |
| 0001558370-25-011801 | BOOT | 2025-08-28T16:05:20-04:00 | SubmissionofMatterstoaVoteofSecurityHolders: Item 5.07 Submission of Matters to a Vote of Security Holders ​ The 2025 Annual Meeting of |  |
| 0001999001-25-000159 | FUN | 2025-08-22T16:34:49-04:00 | SubmissionofMatterstoaVoteofSecurityHolders: Item 5.07. Submission of Matters to a Vote of Security Holders. As previously reported in |  |

This confirms the routing risk the task called out: exhibits attach to the filing, not to a specific item. In multi-item filings, the exhibit often belongs to one event while another item's section remains self-contained.

## Part 3: Extraction Filter Design

For each extraction family below, I searched both section and exhibit fulltext indexes, computed item-code coverage on the live matches, and then reviewed specific misses.

### Generic Candidate Query

```cypher
CALL () {
  CALL db.index.fulltext.queryNodes('extracted_section_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_SECTION]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
  UNION
  CALL db.index.fulltext.queryNodes('exhibit_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_EXHIBIT]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
}
WITH DISTINCT r, [item IN apoc.convert.fromJsonList(r.items) | replace(trim(split(item, ':')[0]), 'Item ', '')] AS item_codes
MATCH (r)-[:PRIMARY_FILER]->(c:Company)
RETURN
  r.accessionNo AS accession,
  c.ticker AS ticker,
  r.formType AS form_type,
  r.created AS created,
  r.items AS raw_items,
  item_codes
ORDER BY r.created DESC
```

### Earnings Release Detection

Candidate query:

```cypher
CALL () {
  CALL db.index.fulltext.queryNodes('extracted_section_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_SECTION]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
  UNION
  CALL db.index.fulltext.queryNodes('exhibit_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_EXHIBIT]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
}
WITH DISTINCT r, [item IN apoc.convert.fromJsonList(r.items) | replace(trim(split(item, ':')[0]), 'Item ', '')] AS item_codes
MATCH (r)-[:PRIMARY_FILER]->(c:Company)
RETURN
  r.accessionNo AS accession,
  c.ticker AS ticker,
  r.formType AS form_type,
  r.created AS created,
  r.items AS raw_items,
  item_codes
ORDER BY r.created DESC
```

Parameter:

```text
$search_query = "earnings release" OR "announced financial results" OR "reported financial results" OR "quarterly results" OR "reports first quarter" OR "reports second quarter" OR "reports third quarter" OR "reports fourth quarter"
```

Keyword filter: `earnings release`, `announced financial results`, `reported financial results`, `quarterly results`, `reports first/second/third/fourth quarter`

Total filings matching keywords: `6,538`

Coverage by item-code gate:

| Item Filter | Caught | Missed | Recall on Keyword Matches |
| --- | --- | --- | --- |
| 2.02 | 6,218 | 320 | 95.11% |
| 2.02, 7.01, 8.01 | 6,500 | 38 | 99.42% |

Top item codes among matched filings:

| Item | Filings | % of Matched Filings |
| --- | --- | --- |
| 9.01 | 6,518 | 99.7% |
| 2.02 | 6,335 | 96.9% |
| 7.01 | 1,615 | 24.7% |
| 8.01 | 514 | 7.9% |
| 5.02 | 267 | 4.1% |
| 1.01 | 84 | 1.3% |
| 2.05 | 51 | 0.8% |
| 2.03 | 36 | 0.6% |
| 5.03 | 24 | 0.4% |
| 2.01 | 16 | 0.2% |
| 5.07 | 14 | 0.2% |
| 3.02 | 10 | 0.2% |

Recommended item-code filter: `2.02`

Caught by recommended filter: `6,218` (`95.11%` recall on keyword matches)

Missed by recommended filter: `320`

Miss inspection samples:

| Accession | Ticker | Form | Created | Preview | Assessment |
| --- | --- | --- | --- | --- | --- |
| 0001193125-25-190894 | URBN | 8-K | 2025-08-28T12:14:27-04:00 | section OtherEvents: Item 8.01. Other Events On August 27, 2025, Urban Outfitters, Inc. (the “Company”) issued an earnings release, which is attached hereto as Exhibit 99.1 and incorporated herein by r // section FinancialStatementsandExhibits: Item 9.01. Financial Statements and Exhibits Exhibit No. Description 99.1 Earnings Release dated August 27, 2025 – Operating results for the three and six months ended July 31, 202 | Real earnings release under Item 8.01; 2.02 alone misses it. |
| 0000080424-25-000069 | PG | 8-K | 2025-07-29T10:51:39-04:00 | section RegulationFDDisclosure: Item 7.01 - Regulation FD Disclosure On July 29, 2025, The Procter & Gamble Company (the "Company") issued a press release announcing its fourth quarter and fiscal year 2025 result // section FinancialStatementsandExhibits: Item 9.01 - Financial Statements and Exhibits (d): The following exhibits are being filed herewith: Exhibit No. Description 99.1 Informational Slides Provided by The Procter & Gamb | Real earnings release under Item 7.01; 2.02 alone misses it. |
| 0000898173-25-000040 | ORLY | 8-K | 2025-07-01T16:40:14-04:00 | section RegulationFDDisclosure: Item 7.01 – Regulation FD Disclosure ​ On July 1, 2025, O’Reilly Automotive, Inc. issued a press release announcing the dates of its 2025 second quarter earnings release and confer // section FinancialStatementsandExhibits: Item 9.01 – Financial Statements and Exhibits ​ Exhibit Number Description 99.1 ​ Press release dated July 1, 2025 ​ Cover Page Interactive Data File – the cover page XBRL tags are | False positive: schedule for a future earnings release, not the results themselves. |

Conclusion: `2.02` is the core earnings item, but it is not a perfect hard gate for near-100% recall. Real earnings releases do appear under `7.01` and `8.01` (for example URBN and PG), while some `7.01` misses are only schedules or pre-announcements. The safest production rule is `2.02` plus keyword rescue over the rest of the 8-K family.

Recommended content sources: EX-99.1/EX-99.2 first; then Item 2.02 / 7.01 / 8.01 sections for routing and context.

### Share Buyback / Repurchase Detection

Candidate query:

```cypher
CALL () {
  CALL db.index.fulltext.queryNodes('extracted_section_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_SECTION]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
  UNION
  CALL db.index.fulltext.queryNodes('exhibit_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_EXHIBIT]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
}
WITH DISTINCT r, [item IN apoc.convert.fromJsonList(r.items) | replace(trim(split(item, ':')[0]), 'Item ', '')] AS item_codes
MATCH (r)-[:PRIMARY_FILER]->(c:Company)
RETURN
  r.accessionNo AS accession,
  c.ticker AS ticker,
  r.formType AS form_type,
  r.created AS created,
  r.items AS raw_items,
  item_codes
ORDER BY r.created DESC
```

Parameter:

```text
$search_query = "share repurchase authorization" OR "share repurchase program" OR "stock repurchase plan" OR "stock repurchase program" OR "accelerated share repurchase" OR "buyback program" OR "buyback authorization" OR "repurchase authorization"
```

Keyword filter: `share repurchase authorization`, `share repurchase program`, `stock repurchase plan`, `stock repurchase program`, `accelerated share repurchase`, `buyback program`, `buyback authorization`, `repurchase authorization`

Total filings matching keywords: `2,613`

Coverage by item-code gate:

| Item Filter | Caught | Missed | Recall on Keyword Matches |
| --- | --- | --- | --- |
| 8.01 | 580 | 2,033 | 22.20% |
| 7.01, 8.01 | 1,164 | 1,449 | 44.55% |
| 1.01, 2.02, 2.03, 7.01, 8.01 | 2,600 | 13 | 99.50% |

Top item codes among matched filings:

| Item | Filings | % of Matched Filings |
| --- | --- | --- |
| 9.01 | 2,520 | 96.4% |
| 2.02 | 2,119 | 81.1% |
| 7.01 | 728 | 27.9% |
| 8.01 | 587 | 22.5% |
| 5.02 | 137 | 5.2% |
| 1.01 | 123 | 4.7% |
| 2.03 | 61 | 2.3% |
| 5.07 | 30 | 1.1% |
| 5.03 | 23 | 0.9% |
| 3.02 | 21 | 0.8% |
| 2.05 | 19 | 0.7% |
| 1.02 | 15 | 0.6% |

Recommended item-code filter: `1.01`, `2.02`, `2.03`, `7.01`, `8.01`

Caught by recommended filter: `2,600` (`99.50%` recall on keyword matches)

Missed by recommended filter: `13`

Miss inspection samples:

| Accession | Ticker | Form | Created | Preview | Assessment |
| --- | --- | --- | --- | --- | --- |
| 0000950170-25-060551 | GRMN | 8-K | 2025-04-30T07:00:09-04:00 | section FinancialStatementsandExhibits: Item 9.01. Financial Statements and Exhibits (d) Exhibits. The following exhibits are furnished herewith. Exhibit No. Description 99.1 Press Release dated April 30, 2025 The cover  // exhibit EX-99.1: EXHIBIT 99.1 Garmin announces first quarter 2025 results Company reports record first quarter operating results and maintains full year EPS guidance Schaffhausen, Switzerland / Apr | Garmin Q1 results; buyback phrase is incidental inside an earnings release. |
| 0001996862-24-000299 | BG | 8-K | 2024-12-09T16:27:14-05:00 | section AmendmentstoArticlesofIncorporationorBylaws;ChangeinFiscalYear: Item 5.03 Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year. Effective December 6, 2024, Bunge Global SA (the “Company”) amended Article 4 of the Company’s A // section FinancialStatementsandExhibits: Item 9.01 Financial Statements and Exhibits (d): Exhibits. Exhibit No. Description 3.1 Articles of Association of Bunge Global SA, as amended, effective December 6, 2024 104 Cover | Bunge bylaw/share-capital update tied to prior repurchases, not a new authorization. |
| 0001104659-25-001305 | ULTA | 8-K | 2025-01-06T16:05:24-05:00 | section DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers: Item 5.02 Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; Compensatory Arrangements of Certain Officers. On January 6, 2025, Ult // section FinancialStatementsandExhibits: Item 9.01. Financial Statements and Exhibits. (d) Exhibits . The exhibits listed in the Exhibit Index below are being filed herewith. EXHIBIT INDEX 99.1 Press release issued by Ult | Ulta CEO transition press release; no buyback event. |

Conclusion: item-code gating helps here. The recommended gate catches 99.5% of keyword matches, and the sampled misses are mostly incidental buyback mentions, governance clean-up, or unrelated personnel / pro-forma filings. This is the cleanest place to use an item-code prefilter before reading content.

Recommended content sources: Check Item 8.01 / 7.01 sections plus EX-99.x press releases; if 1.01/2.03 are present, also read EX-10.x ASR or financing contracts.

### Dividend Declaration Detection

Candidate query:

```cypher
CALL () {
  CALL db.index.fulltext.queryNodes('extracted_section_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_SECTION]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
  UNION
  CALL db.index.fulltext.queryNodes('exhibit_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_EXHIBIT]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
}
WITH DISTINCT r, [item IN apoc.convert.fromJsonList(r.items) | replace(trim(split(item, ':')[0]), 'Item ', '')] AS item_codes
MATCH (r)-[:PRIMARY_FILER]->(c:Company)
RETURN
  r.accessionNo AS accession,
  c.ticker AS ticker,
  r.formType AS form_type,
  r.created AS created,
  r.items AS raw_items,
  item_codes
ORDER BY r.created DESC
```

Parameter:

```text
$search_query = "declares quarterly dividend" OR "declared a quarterly dividend" OR "declared a cash dividend" OR "announces quarterly dividend" OR "special dividend" OR "board declared a regular quarterly cash dividend" OR "board declared a cash dividend"
```

Keyword filter: `declares quarterly dividend`, `declared a quarterly dividend`, `declared a cash dividend`, `announces quarterly dividend`, `special dividend`, `board declared a regular quarterly cash dividend`, `board declared a cash dividend`

Total filings matching keywords: `854`

Coverage by item-code gate:

| Item Filter | Caught | Missed | Recall on Keyword Matches |
| --- | --- | --- | --- |
| 8.01 | 373 | 481 | 43.68% |
| 7.01, 8.01 | 536 | 318 | 62.76% |
| 2.02, 7.01, 8.01 | 832 | 22 | 97.42% |

Top item codes among matched filings:

| Item | Filings | % of Matched Filings |
| --- | --- | --- |
| 9.01 | 850 | 99.5% |
| 2.02 | 552 | 64.6% |
| 8.01 | 377 | 44.1% |
| 7.01 | 254 | 29.7% |
| 5.07 | 41 | 4.8% |
| 5.02 | 28 | 3.3% |
| 1.01 | 16 | 1.9% |
| 5.03 | 13 | 1.5% |
| 2.03 | 8 | 0.9% |
| 2.05 | 4 | 0.5% |
| 2.01 | 3 | 0.4% |
| 3.02 | 2 | 0.2% |

Recommended item-code filter: `2.02`, `7.01`, `8.01`

Caught by recommended filter: `832` (`97.42%` recall on keyword matches)

Missed by recommended filter: `22`

Miss inspection samples:

| Accession | Ticker | Form | Created | Preview | Assessment |
| --- | --- | --- | --- | --- | --- |
| 0000950170-24-119238 | KIM | 8-K | 2024-10-31T06:54:30-04:00 | section FinancialStatementsandExhibits: Item 9.01. Financial Statements and Exhibits. (d) Exhibits 99.1 Press Release, dated October 31, 2024 issued by Kimco Realty Corporation 104 Cover Page Interactive Data File (forma // exhibit EX-99.1: Exhibit 99.1 Kimco Realty® Announces Third Quarter 2024 Results – Portfolio Occupancy Matches All-Time High – – Board Increases Quarterly Cash Dividend on Common Shares by 4.2% – – | Kimco earnings release with a real dividend increase, tagged only as Item 9.01. |
| 0000950170-24-133345 | OGE | 8-K | 2024-12-04T17:13:45-05:00 | section DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers: Item 5.02. Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; Compensatory Arrangements of Certain Officers OGE Energy Corp. (”OGE  // section FinancialStatementsandExhibits: Item 9.01. Financial Statements and Exhibits (d) Exhibits Exhibit Number Description 99.01 Press release dated December 4, 2024, announcing OGE Energy Corp. appoints Walworth as ch | OGE CFO transition press release also declares a quarterly dividend under 5.02/9.01. |
| 0001104659-25-030297 | IAC | 8-K | 2025-04-01T08:45:25-04:00 | section CompletionofAcquisitionorDispositionofAssets: Item 2.01. Completion of Acquisition or Disposition of Assets. On March 31, 2025, IAC Inc. (“IAC” or the “Company”) completed the previously announced spin-off of Angi Inc. (“Angi” // section DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers: Item 5.02. Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; Compensatory Arrangements of Certain Officers. On March 31, 2025, eff | IAC spin-off special dividend; real distribution event outside 2.02/7.01/8.01. |

Conclusion: hard item-code exclusion is risky. The sampled misses include real declarations in `9.01`-only earnings releases and in `5.02` press releases. For dividend extraction, keyword-first search across all 8-K sections / exhibits is safer than a narrow item gate.

Recommended content sources: Keyword-first on sections and EX-99.x. Read the matched press release or shareholder letter directly; item codes are not safe as a hard exclusion.

### Restructuring / Layoff Detection

Candidate query:

```cypher
CALL () {
  CALL db.index.fulltext.queryNodes('extracted_section_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_SECTION]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
  UNION
  CALL db.index.fulltext.queryNodes('exhibit_content_ft', $search_query) YIELD node
  MATCH (r:Report)-[:HAS_EXHIBIT]->(node)
  WHERE r.formType IN ['8-K','8-K/A']
  RETURN DISTINCT r
}
WITH DISTINCT r, [item IN apoc.convert.fromJsonList(r.items) | replace(trim(split(item, ':')[0]), 'Item ', '')] AS item_codes
MATCH (r)-[:PRIMARY_FILER]->(c:Company)
RETURN
  r.accessionNo AS accession,
  c.ticker AS ticker,
  r.formType AS form_type,
  r.created AS created,
  r.items AS raw_items,
  item_codes
ORDER BY r.created DESC
```

Parameter:

```text
$search_query = "reduction in force" OR "workforce reduction" OR layoff OR layoffs OR "restructuring plan" OR "headcount reduction" OR "job cuts" OR "employee reduction"
```

Keyword filter: `reduction in force`, `workforce reduction`, `layoff`, `layoffs`, `restructuring plan`, `headcount reduction`, `job cuts`, `employee reduction`

Total filings matching keywords: `768`

Coverage by item-code gate:

| Item Filter | Caught | Missed | Recall on Keyword Matches |
| --- | --- | --- | --- |
| 2.05 | 138 | 630 | 17.97% |
| 2.05, 8.01 | 216 | 552 | 28.12% |
| 2.02, 2.05, 5.02, 7.01, 8.01 | 735 | 33 | 95.70% |
| 1.01, 2.02, 2.03, 2.05, 5.02, 7.01, 8.01 | 761 | 7 | 99.09% |

Top item codes among matched filings:

| Item | Filings | % of Matched Filings |
| --- | --- | --- |
| 9.01 | 720 | 93.8% |
| 2.02 | 516 | 67.2% |
| 7.01 | 217 | 28.3% |
| 2.05 | 141 | 18.4% |
| 5.02 | 119 | 15.5% |
| 8.01 | 105 | 13.7% |
| 1.01 | 77 | 10.0% |
| 2.03 | 38 | 4.9% |
| 2.06 | 16 | 2.1% |
| 5.07 | 11 | 1.4% |
| 2.01 | 9 | 1.2% |
| 1.02 | 8 | 1.0% |

Recommended item-code filter: `2.02`, `2.05`, `5.02`, `7.01`, `8.01`

Caught by recommended filter: `735` (`95.70%` recall on keyword matches)

Missed by recommended filter: `33`

Miss inspection samples:

| Accession | Ticker | Form | Created | Preview | Assessment |
| --- | --- | --- | --- | --- | --- |
| 0001193125-25-182214 | ARMK | 8-K | 2025-08-18T07:47:58-04:00 | section EntryintoaMaterialDefinitiveAgreement: Item 1.01. Entry into a Material Definitive Agreement. Amendment No. 18 to the Credit Agreement On August 15, 2025 (the “Closing Date”), Aramark Services, Inc. (the “Company”), an  // section FinancialStatementsandExhibits: Item 9.01. Financial Statements and Exhibits (d) Exhibits Exhibit No. Description 10.1 Amendment No. 18 (the “Amendment”), dated as of August 15, 2025, among Aramark Services, Inc. | Credit-agreement amendment false positive; no layoff event. |
| 0001477449-25-000091 | TDOC | 8-K | 2025-07-23T16:05:35-04:00 | section EntryintoaMaterialDefinitiveAgreement: Item 1.01 Entry into a Material Definitive Agreement . On July 17, 2025 (the “Effective Date”), Teladoc Health, Inc. (the “Company”) entered into a credit agreement (the “Credit Ag // section CreationofaDirectFinancialObligationoranObligationunderanOff-BalanceSheetArrangementofaRegistrant: Item 2.03 Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant. The information contained in Item 1.01 of this Current | Credit facility filing false positive; restructuring terms appear only in debt language. |
| 0001193125-25-056735 | ON | 8-K | 2025-03-18T17:10:21-04:00 | section MaterialImpairments: Item 2.06. Material Impairments On March 17, 2025, as part of the restructuring plan and cost reduction initiatives previously announced on February 24, 2025, management of ON Semi | Item 2.06 impairment follow-on to a previously announced restructuring plan, not a fresh layoff filing. |

Conclusion: `2.05` alone is far too narrow. A broader gate across `2.02`, `2.05`, `5.02`, `7.01`, and `8.01` catches most precise phrase matches, and the sampled misses are largely financing noise or follow-on impairment reports rather than fresh layoff announcements. If maximum recall is worth extra review, add `1.01` and `2.03`.

Recommended content sources: Read Item 2.05 / 8.01 / 5.02 sections first. Only open EX-10.x if the matched text suggests a severance framework or plant-closure agreement.

## Part 4: Content Routing

| Extraction Type | Read First | Routing Risk |
| --- | --- | --- |
| Earnings release | Read `EX-99.1` and `EX-99.2` first; then the matching Item `2.02` / `7.01` / `8.01` section for framing. | A filing can mix an earnings exhibit with a separate `8.01` or governance section. |
| Buyback / repurchase | Read the matched `8.01` / `7.01` section plus any matched `EX-99.x`; add `EX-10.x` when `1.01` / `2.03` suggests an ASR or financing agreement. | Earnings releases mention prior repurchases frequently; section/exhibit keyword confirmation is mandatory. |
| Dividend declaration | Read the exact matched `EX-99.x` or shareholder letter first. Use the section only to see whether the dividend was bundled with earnings, governance, or a spin-off. | Real declarations leak into `9.01`-only and `5.02` filings, so item-code-only routing misses them. |
| Restructuring / layoff | Read Item `2.05`, `8.01`, `5.02`, or `7.01` sections first. Open exhibits only if the matched language points to a specific workforce plan, severance framework, or closure announcement. | Debt contracts and merger agreements contain restructuring language that is not itself a layoff event. |

General routing rule: treat `9.01` as a discovery aid, not a semantic event label. The actual business event usually lives in the other item sections and in the attached `EX-99.x` / `EX-10.x` content.

## Part 5: Synthesis

### What Surprised Me

- The 8-K family is even more multi-item than intuition suggests: two-item filings are the norm, not the exception.
- `9.01` is so ubiquitous that it has almost no standalone semantic value, but it still matters operationally because many real events only expose their usable text through attached exhibits.
- Dividend declarations are the hardest of the four target filters to item-code gate safely. Real declarations leak into governance and `9.01`-only filings.
- `2.05` is the dedicated restructuring item, but it does not come close to covering the full layoff / workforce-reduction universe in practice.

### Recommended Additional Extraction Types

| Candidate Extraction | Why It Is Worth Building |
| --- | --- |
| M&A closing / disposition | Items `2.01`, `1.01`, and `9.01` create a clean event family with clear market relevance. |
| Debt financing / refinancing | Items `1.01` + `2.03` are frequent, structurally consistent, and rich in `EX-10.x` contracts. |
| Auditor change / restatement risk | Items `4.01` and `4.02` are rare but high-signal and operationally important. |
| Cybersecurity incident | Item `1.05` is sparse but extremely high-value and easy to route. |
| Executive changes | Item `5.02` is common, section-first, and materially relevant for management-turnover monitoring. |

### Bottom Line

- Earnings can use `2.02` as the primary gate, but not the only gate if recall matters.
- Buybacks support the strongest item-code prefilter of the four.
- Dividends are the clearest case where keyword-first search beats narrow item gating.
- Restructuring / layoff detection needs both the dedicated item (`2.05`) and a broader rescue path, because companies disclose workforce actions under multiple items.

---

## Verbatim Source 2: 840-sample Haiku vs baseline comparison

Original file: `8k_haiku_router_strategy.md`


# Haiku Router Strategy Evaluation

Model used: `claude-haiku-4-5-20251001`

Sample: `840` live 8-K / 8-K/A filings, stratified across `12` groups with target `70` filings per group.

## Method

- Candidate jobs tested: `earnings_release`, `share_buyback`, `dividend_declaration`, `restructuring`.
- Haiku saw item codes, section names, exhibit numbers, and bounded excerpts from up to 3 sections and 2 exhibits.
- Baseline comparator is the current deterministic strategy from the validated 8-K analysis, not the older weak heuristic script.
- This report compares route decisions on a broad stratified sample; it does not claim human-labeled ground truth for every filing.

## Sampling

| Group | Available | Sampled |
| --- | --- | --- |
| buyback_keyword | 2,613 | 70 |
| dividend_keyword | 854 | 70 |
| restructuring_keyword | 768 | 70 |
| earnings_core | 8,762 | 70 |
| regfd_only | 3,468 | 70 |
| other_events_only | 3,628 | 70 |
| debt_core | 1,319 | 70 |
| restructuring_item | 231 | 70 |
| executive_core | 3,702 | 70 |
| governance_core | 2,138 | 70 |
| only_901 | 110 | 70 |
| background_misc | 7,489 | 70 |

## Runtime

| Classified Filings | Input Tokens | Output Tokens | Estimated Cost | Errors |
| --- | --- | --- | --- | --- |
| 840 | 787,125 | 127,772 | $1.1408 | 47 |

## Per-Job Comparison

| Job | Haiku Yes | Baseline Yes | Both | Haiku Only | Baseline Only | Baseline Retained by Haiku | Haiku Overlap With Baseline |
| --- | --- | --- | --- | --- | --- | --- | --- |
| earnings_release | 254 | 267 | 249 | 5 | 18 | 93.26% | 98.03% |
| share_buyback | 52 | 137 | 46 | 6 | 91 | 33.58% | 88.46% |
| dividend_declaration | 71 | 94 | 46 | 25 | 48 | 48.94% | 64.79% |
| restructuring | 80 | 120 | 51 | 29 | 69 | 42.50% | 63.75% |

## Control-Group Load

These groups are important because they show whether Haiku reduces noisy routing on clearly non-target event families.

| Control Group | Sampled | Haiku Routed to Any Current Job | Baseline Routed to Any Current Job |
| --- | --- | --- | --- |
| governance_core | 70 | 0 (0.00%) | 0 (0.00%) |
| only_901 | 70 | 11 (15.71%) | 14 (20.00%) |
| debt_core | 70 | 1 (1.43%) | 7 (10.00%) |
| executive_core | 70 | 0 (0.00%) | 0 (0.00%) |
| background_misc | 70 | 0 (0.00%) | 2 (2.86%) |

## Disagreement Samples

### earnings_release

#### Haiku Only

| Accession | Ticker | Group | Haiku Secondary Tags | Items | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0001628280-23-002424 | TTWO | only_901 | forward_guidance | ["Item 9.01: Financial Statements and Exhibits"] | [Section: FinancialStatementsandExhibits] Item 9.01 Financial Statements and Exhibits (d) Exhibits: 99.1 Press Release dated February 6, 2023 relating to Take-Two Interactive Software, Inc.’s financial results for its th |
| 0000047111-23-000043 | HSY | other_events_only |  | ["Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: OtherEvents] Item 8.01. Other Events. On April 27, 2023, The Hershey Company furnished a Current Report on Form 8-K (the "Original 8-K") that included, as Exhibit 99.1, a press release dated April 27, 2023, ann |
| 0000016875-23-000019 | CP | regfd_only | m_and_a | ["Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: RegulationFDDisclosure] ITEM 7.01 Regulation FD Disclosure. Canadian Pacific Kansas City Southern Limited (“CPKC”) is furnishing the unaudited financial report of Kansas City Southern for the quarter ended Marc |
| 0000051143-25-000007 | IBM | regfd_only | forward_guidance | ["Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: RegulationFDDisclosure] Item 7.01. Regulation FD Disclosure. Exhibit 99.1 of this Form 8-K contains the prepared remarks for IBM's Chairman, President and Chief Executive Officer Arvind Krishna and Chief Financ |
| 0000051143-25-000051 | IBM | regfd_only | forward_guidance | ["Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: RegulationFDDisclosure] Item 7.01. Regulation FD Disclosure. Exhibit 99.1 of this Form 8-K contains the prepared remarks for IBM's Chairman, President and Chief Executive Officer Arvind Krishna and Chief Financ |

#### Baseline Only

| Accession | Ticker | Group | Haiku Secondary Tags | Items | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0001193125-25-005690 | PINC | buyback_keyword | forward_guidance | ["Item 7.01: Regulation FD Disclosure", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: RegulationFDDisclosure] Item 7.01. Regulation FD Disclosure Premier, Inc. (the “ Company ”) is scheduled to present at the J.P. Morgan Healthcare Conference in San Francisco, California on Tuesday, January 14,  |
| 0001104659-24-101211 | MTDR | debt_core | m_and_a, debt_financing | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 2.01: Completion of Acquisition or Disposition of Assets", "Item 2.03: Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: RegulationFDDisclosure] Item 7.01 Regulation FD Disclosure. On September 19, 2024, Matador issued a press release (the “Press Release”) announcing the Amendment and the closing of the Acquisition. A copy of the |
| 0001193125-23-088906 | OVV | dividend_keyword | m_and_a | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] ITEM 2.02 Results of Operations and Financial Condition. On April 3, 2023, Ovintiv Inc. (“Ovintiv”) issued a press release regarding (i) the acquisition by its wholly-o |
| 0001692063-23-000147 | SNDR | only_901 |  | ["Item 9.01: Financial Statements and Exhibits"] | [Section: FinancialStatementsandExhibits] ITEM 9.01 Financial Statements and Exhibits. (d) Exhibits. Exhibit No. Description of Exhibit 99.1 Press release dated August 3, 2023 104 The cover page from this Current Report  |
| 0001193125-23-202870 | XYL | only_901 |  | ["Item 9.01: Financial Statements and Exhibits"] | [Section: FinancialStatementsandExhibits] Item 9.01 Financial Statements and Exhibits (a) Financial Statements of Business Acquired The audited consolidated financial statements of Evoqua as of and for the year ended Sep |
| 0001157523-23-000544 | VCTR | other_events_only |  | ["Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: OtherEvents] Item 8.01. Other Events. On April 12, 2023, Victory Capital Holdings, Inc., (the “Company”) issued a press release reporting certain information about the Company’s assets under management (“AUM”)  |
| 0001562401-24-000026 | AMH | regfd_only | forward_guidance | ["Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: RegulationFDDisclosure] Item 7.01 Regulation FD Disclosure On February 28, 2024 , American Homes 4 Rent (“AMH” or the “Company”) posted a presentation concerning the Company titled “Investor Highlights–March 20 |
| 0000074303-23-000130 | OLN | restructuring_item | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 2.05: Cost Associated with Exit or Disposal Activities", "Item 2.06: Material Impairments", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Conditions On June 20, 2023, Olin Corporation (“Olin”) issued a press release announcing an updated outlook for the secon |

### share_buyback

#### Haiku Only

| Accession | Ticker | Group | Haiku Secondary Tags | Items | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0000005272-25-000036 | AIG | dividend_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Condition. On May 1, 2025, American International Group, Inc. (the “Company”) issued a press release (the “Press Release” |
| 0000818479-24-000070 | XRAY | restructuring_item | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 2.05: Cost Associated with Exit or Disposal Activities", "Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition On July 31, 2024, DENTSPLY SIRONA Inc. (the “Company”) issued a press release regarding the Company’s financial  |
| 0000818479-23-000081 | XRAY | restructuring_keyword | forward_guidance, governance | ["Item 2.02: Results of Operations and Financial Condition", "Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. The following information is furnished pursuant to Item 2.02, "Results of Operations and Financial Condition."  |
| 0001193125-24-033715 | REVG | restructuring_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. The information set forth under Item 7.01 below is incorporated by reference into this Item 2.02.  [Section: Re |
| 0001637207-24-000041 | PLNT | restructuring_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On May 9, 2024, Planet Fitness, Inc. (the “Company”) issued a press release announcing its financial results fo |
| 0000950103-24-015970 | EMR | restructuring_keyword |  | ["Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: OtherEvents] Item 8.01 Other Events. On Tuesday, November 5, 2024, the Company issued a press release announcing that (i) the Company had submitted a proposal (the “Proposal”) to the board of directors of Aspen |

#### Baseline Only

| Accession | Ticker | Group | Haiku Secondary Tags | Items | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0000875320-23-000004 | VRTX | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Condition. On February 7, 2023, we issued a press release in which we reported our consolidated financial results for the |
| 0000046080-23-000011 | HAS | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On February 16, 2023, Hasbro, Inc. ("Hasbro" or "we") announced its financial results for the fiscal quarter an |
| 0000073124-23-000099 | NTRS | buyback_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Condition The information contained in the registrant’s April 25, 2023 press release, reporting on the registrant’s earni |
| 0001097149-23-000039 | ALGN | buyback_keyword | m_and_a | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On April 26, 2023, Align issued a press release and will hold a conference call regarding its financial results |
| 0000916365-23-000052 | TSCO | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On April 27, 2023 , Tractor Supply Company (the "Company") issued a press release reporting its results of oper |
| 0001193125-23-122177 | ALSN | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On April 27, 2023, Allison Transmission Holdings, Inc. (“Allison”) published an earnings release reporting its  |
| 0001157523-23-000746 | VCTR | buyback_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Condition On May 4, 2023, Victory Capital Holdings, Inc., (the “Company”) issued a press release (the “Earnings Press Rel |
| 0001604028-23-000012 | WMS | buyback_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition On May 18, 2023, Advanced Drainage Systems, Inc. (the "Company") issued a press release setting forth the Compan |

### dividend_declaration

#### Haiku Only

| Accession | Ticker | Group | Haiku Secondary Tags | Items | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0001157523-23-000746 | VCTR | buyback_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Condition On May 4, 2023, Victory Capital Holdings, Inc., (the “Company”) issued a press release (the “Earnings Press Rel |
| 0000940944-23-000031 | DRI | buyback_keyword | forward_guidance, governance | ["Item 2.02: Results of Operations and Financial Condition", "Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On June 22, 2023, Darden Restaurants, Inc. (the Company) issued a news release entitled “Darden Restaurants Rep |
| 0000105770-23-000064 | WST | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On October 26, 2023, West Pharmaceutical Services, Inc. (the “Company”) issued a press release announcing its t |
| 0001193125-24-046183 | SBAC | buyback_keyword | forward_guidance, debt_financing | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On February 26, 2024, SBA Communications Corporation issued a press release announcing its financial and operat |
| 0001730168-24-000012 | AVGO | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On March 7, 2024, Broadcom Inc. (the “Company”) issued a press release announcing its unaudited financial resul |
| 0001628280-24-021203 | LPX | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On May 8, 2024, Louisiana-Pacific Corporation (the "Company") issued a press release announcing financial resul |
| 0001022079-25-000008 | DGX | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Condition On January 30, 2025, Quest Diagnostics Incorporated (the "Company") issued a press release announcing, among ot |
| 0000052988-25-000014 | J | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition On February 4, 2025, Jacobs Solutions Inc. (the “Company”) issued a press release announcing its financial resul |

#### Baseline Only

| Accession | Ticker | Group | Haiku Secondary Tags | Items | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0001628280-25-019784 | LAZ | buyback_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On April 25, 2025, Lazard, Inc. (the “Company”) issued a press release announcing financial results for its fir |
| 0001193125-24-075251 | TDG | debt_core | debt_financing | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 2.03: Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant", "Item 9.01: Financial Statements and Exhibits"] | [Section: EntryintoaMaterialDefinitiveAgreement] Item 1.01. Entry into a Material Definitive Agreement. Completed Refinancing Summary On March 22, 2024, TransDigm Inc. (“TransDigm”), a wholly-owned subsidiary of TransDig |
| 0001193125-23-050970 | OVV | dividend_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] ITEM 2.02 Results of Operations and Financial Condition. On February 27, 2023 Ovintiv Inc. (the “Company”) issued a news release announcing its financial and operating  |
| 0001193125-23-088906 | OVV | dividend_keyword | m_and_a | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] ITEM 2.02 Results of Operations and Financial Condition. On April 3, 2023, Ovintiv Inc. (“Ovintiv”) issued a press release regarding (i) the acquisition by its wholly-o |
| 0001694028-23-000014 | LBRT | dividend_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 5.07: Submission of Matters to a Vote of Security Holders", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Condition On April 19, 2023, Liberty Energy Inc., a Delaware corporation (the “Company”), issued a press release announci |
| 0001096752-23-000014 | EPC | dividend_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition On May 9, 2023, the Edgewell Personal Care Company ("the Company") issued a press release announcing financial a |
| 0001880661-23-000040 | TPG | dividend_keyword | m_and_a | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On May 15, 2023 , TPG Inc. issued a summary press release and a detailed earnings presentation announcing finan |
| 0001468174-23-000077 | H | dividend_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Condition. On August 3, 2023, Hyatt Hotels Corporation (the "Company") issued a press release announcing its results for  |

### restructuring

#### Haiku Only

| Accession | Ticker | Group | Haiku Secondary Tags | Items | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0001193125-25-044753 | BL | other_events_only |  | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: OtherEvents] Item 8.01 Other Events On March 4, 2025, the Company announced that it is planning to reduce its global workforce by approximately 7%, or approximately 130 total positions (the “Planned Reductions” |
| 0001104659-23-032991 | TEL | restructuring_item | executive_change | ["Item 2.05: Cost Associated with Exit or Disposal Activities", "Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 5.07: Submission of Matters to a Vote of Security Holders"] | [Section: CostsAssociatedwithExitorDisposalActivities] Item 2.05. Costs Associated with Exit or Disposal Activities On March 16, 2023, the Board of Directors of TE Connectivity Ltd. (the “Company”) approved incremental r |
| 0001193125-23-083797 | WMG | restructuring_item |  | ["Item 2.05: Cost Associated with Exit or Disposal Activities", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: RegulationFDDisclosure] ITEM 7.01 REGULATION FD DISCLOSURE. In connection with this announcement, the employee communication furnished herewith as Exhibit 99.1 was sent by Robert Kyncl, the Company’s Chief Exec |
| 0001810806-23-000044 | U | restructuring_item |  | ["Item 2.05: Cost Associated with Exit or Disposal Activities"] | [Section: CostsAssociatedwithExitorDisposalActivities] Item 2.05 Costs Associated with Exit or Disposal Activities. On May 2, 2023, Unity Software Inc. (“ Unity ” or the “ Company ”) announced the reduction of approximat |
| 0001193125-23-155426 | NWL | restructuring_item |  | ["Item 2.05: Cost Associated with Exit or Disposal Activities", "Item 9.01: Financial Statements and Exhibits"] | [Section: CostsAssociatedwithExitorDisposalActivities] Item 2.05. Costs Associated with Exit or Disposal Activities On May 24, 2023, Newell Brands Inc. (the “Company”) committed to a restructuring and savings initiative  |
| 0001477294-23-000097 | ST | restructuring_item |  | ["Item 2.05: Cost Associated with Exit or Disposal Activities"] | [Section: CostsAssociatedwithExitorDisposalActivities] Item 2.05 Costs Associated with Exit or Disposal Activities. On June 6, 2023, Sensata Technologies Holding plc (the “Company”) made the decision to exit Spear Power  |
| 0000074303-23-000130 | OLN | restructuring_item | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 2.05: Cost Associated with Exit or Disposal Activities", "Item 2.06: Material Impairments", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02. Results of Operations and Financial Conditions On June 20, 2023, Olin Corporation (“Olin”) issued a press release announcing an updated outlook for the secon |
| 0000078239-23-000104 | PVH | restructuring_item |  | ["Item 2.05: Cost Associated with Exit or Disposal Activities"] | [Section: CostsAssociatedwithExitorDisposalActivities] ITEM 2.05 COSTS ASSOCIATED WITH EXIT OR DISPOSAL ACTIVITIES PVH Corp. (the “Company”) announced in its press release dated August 30, 2022 that the Company would be  |

#### Baseline Only

| Accession | Ticker | Group | Haiku Secondary Tags | Items | Excerpt |
| --- | --- | --- | --- | --- | --- |
| 0001288469-24-000116 | MXL | background_misc |  | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers"] | [Section: DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers] Item 5.02 Departure of Directors or Certain Officers; Election of Directors; App |
| 0001842718-25-000013 | IAS | background_misc | executive_change | ["Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers"] | [Section: DepartureofDirectorsorCertainOfficers;ElectionofDirectors;AppointmentofCertainOfficers:CompensatoryArrangementsofCertainOfficers] Item 5.02. Departure of Directors or Certain Officers; Election of Directors; Ap |
| 0001522540-23-000023 | MQ | buyback_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 8.01: Other Events", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On May 9, 2023 , Marqeta, Inc. issued a press release announcing its financial results for the quarter ended Ma |
| 0000105770-23-000064 | WST | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On October 26, 2023, West Pharmaceutical Services, Inc. (the “Company”) issued a press release announcing its t |
| 0001104659-24-014723 | BERY | buyback_keyword | m_and_a | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 5.02: Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers: Compensatory Arrangements of Certain Officers", "Item 9.01: Financial Statements and Exhibits"] | [Section: EntryintoaMaterialDefinitiveAgreement] Item 1.01 Entry into a Material Definitive Agreement. As previously disclosed in a Current Report on Form 8-K filed by Berry Global Group, Inc. (the “Company”) with the Se |
| 0000950170-25-022236 | BMBL | buyback_keyword |  | ["Item 2.02: Results of Operations and Financial Condition", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On February 18, 2025, Bumble Inc. (the “Company”) issued a press release announcing earnings for the fourth qua |
| 0000105770-25-000029 | WST | buyback_keyword | forward_guidance | ["Item 2.02: Results of Operations and Financial Condition", "Item 7.01: Regulation FD Disclosure", "Item 9.01: Financial Statements and Exhibits"] | [Section: ResultsofOperationsandFinancialCondition] Item 2.02 Results of Operations and Financial Condition. On April 24, 2025, West Pharmaceutical Services, Inc. (the “Company”) issued a press release announcing its fir |
| 0001396814-23-000017 | PCRX | debt_core | debt_financing | ["Item 1.01: Entry into a Material Definitive Agreement", "Item 1.02: Termination of a Material Definitive Agreement", "Item 2.03: Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant", "Item 8.01: Other Events"] | [Section: OtherEvents] Item 8.01. Other Events. On April 3, 2023, the Company issued a press release relating to, among other things, the entry into the Credit Agreement. A copy of the press release is attached as Exhibi |

## Verdict

Haiku is not strong enough to replace deterministic routing as the sole router.

Operational interpretation:

- If Haiku drops baseline-retention below a recall threshold you care about, it should not be the sole router.
- If Haiku materially reduces routing inside control groups, it is useful as a second-pass precision filter on a deterministic superset.
- As the number of extraction jobs grows, the LLM router becomes more valuable for fan-out and multi-label assignment, but only if deterministic recall guards remain in place.

---

## Verbatim Source 3: 1,281-sample Haiku bucket evaluation

Original file: `haiku_router_strategy_evaluation.md`


# Haiku Router Strategy Evaluation

Date: 2026-03-14

## Goal

Evaluate whether a small-LLM router (Haiku) should replace deterministic routing, augment it, or be reserved for ambiguous 8-K subsets.

## Run Summary

- Model: `claude-haiku-4-5-20251001`
- Classified filings: **1281**
- Total input tokens: **1,871,001**
- Total output tokens: **60,751**
- Average input tokens / filing: **1460.6**
- Average output tokens / filing: **47.4**
- Estimated sample cost: **$1.7398**
- Estimated full-8-K-universe cost at same prompt size: **$33.07**

## Group Findings

| Group | N | Dominant Haiku primary | Dominant rate | Multi-label rate | Recommendation |
|---|---:|---|---:|---:|---|
| 1.01_2.03_debt | 119 | DEBT_FINANCING | 98.32% | 11.76% | deterministic_ok |
| 2.01_ma | 119 | M_AND_A | 95.80% | 45.38% | deterministic_ok |
| 2.02_core | 120 | EARNINGS | 99.17% | 65.00% | deterministic_ok |
| 2.05_restructuring | 120 | RESTRUCTURING | 71.67% | 47.50% | hybrid_preferred |
| 5.02_exec | 118 | EXECUTIVE_CHANGE | 88.98% | 5.93% | hybrid_preferred |
| 5.07_governance | 120 | GOVERNANCE | 95.83% | 20.00% | deterministic_ok |
| 7.01_ambiguous | 120 | INVESTOR_PRESENTATION | 25.83% | 21.67% | llm_needed |
| 8.01_ambiguous | 120 | DEBT_FINANCING | 31.67% | 10.83% | llm_needed |
| 9.01_only | 89 | M_AND_A | 46.07% | 13.48% | llm_needed |
| random_all | 149 | EARNINGS | 40.94% | 30.87% | llm_needed |
| rare_other | 87 | GOVERNANCE | 64.37% | 11.49% | llm_needed |

Recommendation key:

- `deterministic_ok`: Haiku adds little routing value for the primary label.
- `hybrid_preferred`: deterministic prefilter plus Haiku adds value.
- `llm_needed`: bucket is too semantically diverse for deterministic-only routing.

## Category Comparison: Haiku vs Stronger Heuristic Baseline

Note: this benchmark originally used the older label names `DEBT` and `OTHER`. In the frozen taxonomy from Section 1A, read those as `DEBT_FINANCING` and a pre-split residual bucket that is now divided into `OTHER_MATERIAL_EVENT` and `ADMINISTRATIVE_ONLY`.

| Category | Haiku yes | Heuristic yes | Both yes | Haiku only | Heuristic only |
|---|---:|---:|---:|---:|---:|
| EARNINGS | 248 | 236 | 231 | 17 | 5 |
| GUIDANCE | 123 | 258 | 108 | 15 | 150 |
| BUYBACK | 46 | 18 | 17 | 29 | 1 |
| DIVIDEND | 52 | 30 | 28 | 24 | 2 |
| RESTRUCTURING | 127 | 59 | 58 | 69 | 1 |
| M_AND_A | 231 | 433 | 215 | 16 | 218 |
| DEBT_FINANCING | 258 | 278 | 247 | 11 | 31 |
| EXECUTIVE_CHANGE | 236 | 261 | 229 | 7 | 32 |
| GOVERNANCE | 267 | 248 | 226 | 41 | 22 |
| INVESTOR_PRESENTATION | 93 | 51 | 43 | 50 | 8 |
| OTHER_MATERIAL_EVENT / ADMINISTRATIVE_ONLY | 75 | 137 | 49 | 26 | 88 |

## Practical Conclusion

This run supports a **hybrid** strategy, not a full replacement in either direction.

- Keep deterministic direct routes for canonical buckets where the primary event is structurally obvious: `2.02` earnings, `2.01` M&A completion, `1.01+2.03` debt financing, `5.02` executive change, `5.07` governance.
- Use Haiku on ambiguous / multi-purpose buckets where item codes are poor proxies for downstream jobs: `7.01`, `8.01`, `9.01`-only, and mixed multi-item filings.
- If the objective expands to many more extraction types, Haiku becomes more attractive because prompt labels scale better than maintaining many keyword systems.
- If the objective is maximum recall for a few well-understood event types, deterministic backstops should remain in place even when Haiku is used.

## Disagreement Audit Highlights

- Haiku is clearly useful on ambiguous buckets. `7.01`, `8.01`, and `9.01`-only filings were too semantically diverse for deterministic routing: the top primary label was only `25.83%`, `31.67%`, and `46.07%` respectively.
- Haiku also surfaced real secondary labels that deterministic rules under-call. Example: `5.02` board-appointment filings were sometimes better understood as governance events, not just executive change.
- Haiku is **not** reliable enough by itself for expensive secondary-job routing on earnings and financing filings. In the sampled disagreements:
  - some debt/convertible-note filings were labeled `BUYBACK` for unusual capital-markets transactions that did include share repurchases, but were not standard board-authorized buyback-program announcements;
  - some earnings filings were labeled `DIVIDEND` or `BUYBACK` because the press release discussed historical capital returns, not a new declaration/authorization.
- Concrete likely Haiku mistakes I checked:
  - `0000051434-23-000003` (International Paper earnings): Haiku added `BUYBACK` and `DIVIDEND`, but the excerpt only discussed past-year shareholder returns and dividends, not a new authorization or declaration.
  - `0000060667-25-000018` (Lowe's earnings): same pattern; past repurchases and dividends were mentioned, but no clear new trigger phrase was present in the excerpt.
  - `0000006951-24-000017` (Applied Materials filing with only `9.01` section content plus an earnings exhibit): Haiku added `BUYBACK` and `DIVIDEND`, but the exhibit language was backward-looking shareholder return commentary, not a fresh capital-returns action.
- Manual spot checks also showed that some apparent Haiku "overcalls" were actually real events that the heuristic missed:
  - `0001140361-25-006524` (BridgeBio debt filing): this did include real share repurchases funded alongside the note offering, so it should not be treated as an obvious Haiku mistake.
  - `0001104659-25-030297` (IAC / Angi spin-off): Haiku's `DIVIDEND` call was justified because the filing explicitly says the board "declared a special dividend" consisting of distributed Angi shares.
- Small manual sample result: in 8 filings I re-read directly from Neo4j, Haiku looked clearly wrong on 4 backward-looking capital-returns mentions (`IP`, `LOW`, `AMAT`, `TXT`) and directionally right on 4 real but sometimes non-standard events (`BBIO` buyback, `IAC` special dividend, `KMT` restructuring, `PFE` restructuring).
- Simple proxy check on Haiku-only disagreements showed only a minority of the extra `BUYBACK` / `DIVIDEND` calls contained strong action phrases:
  - `BUYBACK`: 29 Haiku-only calls, only 5 with strong authorization/program language
  - `DIVIDEND`: 24 Haiku-only calls, only 2 with strong declaration/increase language
- By contrast, Haiku looked directionally stronger than heuristics at rejecting broad false positives:
  - heuristic `GUIDANCE` was over-fired on debt and M&A documents
  - heuristic `M_AND_A` was over-fired inside debt documents because of transaction / purchase-agreement wording
- Concrete cases where Haiku looked better than the heuristic:
  - `0000062709-23-000021` (`5.02` filing): Haiku treated it as `GOVERNANCE` because it was really about new independent board members and audit-committee appointments, not a standard officer-change filing.
  - many `2.05` filings were treated by Haiku as `RESTRUCTURING` even when the wording was cost-realignment / streamlining language instead of literal workforce-reduction phrases; that is directionally consistent with the SEC item itself.

## Best Strategy So Far

Best current strategy is:

1. Deterministic direct routing for structurally obvious primary jobs.
2. Haiku routing for ambiguous buckets and for future category expansion.
3. Deterministic confirmation for high-cost secondary jobs (`BUYBACK`, `DIVIDEND`, `GUIDANCE`, sometimes `RESTRUCTURING`) before launching the expensive extractor.

In practice:

- `2.02` should still directly trigger the earnings path.
- `2.05` should directly trigger restructuring as a backstop when present, because the sample strongly suggests it is a genuine restructuring signal even when workforce keywords are absent.
- `7.01`, `8.01`, `9.01`-only, and mixed `5.02` cases are the strongest candidates for Haiku-first routing.
- Haiku should not be the only guardrail for buyback/dividend extraction from earnings and debt filings.

If forced to choose only one system:

- `Haiku-on-all-8-Ks` is more future-proof than keyword-only routing.
- `Deterministic-only` is safer for a few canonical event families.
- `Hybrid` is better than either single-system extreme.

## Production Cost View

Using the observed average prompt size from this run:

- Full-corpus Haiku on all 24,350 8-K filings would cost about **$33.07**
- A more targeted hybrid pass is cheaper:
  - filings in a canonical direct-route bucket: about **12,915**
  - filings in an ambiguous bucket: about **14,728**
  - ambiguous-only filings: about **10,756**

That means the production question is no longer cost alone; it is mostly about whether you trust Haiku enough to route secondary extraction jobs without deterministic confirmation. Based on this run, the honest answer is **no**.

## Audit Sample

Stored **80** disagreement rows in the JSON results file for manual review.

Full JSON results: `/home/faisal/EventMarketDB/.claude/plans/Extractions/haiku_router_strategy_eval_results.json`

---

## Verbatim Source 4: Best-strategy synthesis

Original file: `8k_router_best_strategy.md`


# 8-K Router Best Strategy

Date: 2026-03-14

## Question

Should we pass a broad 8-K superset to a small LLM such as Haiku and let it route filings to extraction jobs, instead of relying mainly on deterministic heuristics?

## Short Answer

Yes for a hybrid router.

No for a Haiku-only router.

The best strategy so far is:

1. Keep deterministic recall guards for structurally obvious filing families.
2. Run Haiku on the ambiguous superset, or on all 8-Ks if you want a simpler system.
3. Use a union rule for routing: deterministic yes OR Haiku yes OR targeted rescue heuristic yes.

That is better than deterministic-only for platform growth, and better than Haiku-only for recall safety.

## Evidence Base

This recommendation is based on two live experiments plus full-corpus bucket counts from Neo4j.

### Experiment A: targeted current-job comparison

Source: [8k_haiku_router_strategy.md](/home/faisal/EventMarketDB/.claude/plans/Extractions/8k_haiku_router_strategy.md)

Sample:

- 840 live 8-K / 8-K/A filings
- 12 stratified groups
- compared Haiku against the validated current deterministic strategy for:
  - `earnings_release`
  - `share_buyback`
  - `dividend_declaration`
  - `restructuring`

Results:

| Job | Haiku yes | Baseline yes | Both | Haiku only | Baseline only | Baseline retained by Haiku |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| earnings_release | 254 | 267 | 249 | 5 | 18 | 93.26% |
| share_buyback | 52 | 137 | 46 | 6 | 91 | 33.58% |
| dividend_declaration | 71 | 94 | 46 | 25 | 48 | 48.94% |
| restructuring | 80 | 120 | 51 | 29 | 69 | 42.50% |

Interpretation:

- Haiku improves semantic precision in noisy buckets.
- Haiku is not safe as the sole router for buybacks, dividends, or restructuring.
- Haiku is closer to usable as a sole router for earnings, but still not perfect.

Manual audits confirmed real misses by Haiku:

- Buyback miss: `0000875320-23-000004` (`VRTX`) contained a real new `$3.0 billion` repurchase authorization.
- Dividend misses: `OVV`, `EPC`, `TPG`, and `H` sample filings contained real dividend declarations or increases that Haiku failed to route.
- Restructuring was mixed: Haiku missed some baseline hits, but it also caught real restructuring events the baseline missed.

Manual audits also confirmed real Haiku wins:

- Earnings: `TTWO` `9.01`-only results filing, plus IBM `7.01` earnings prepared remarks.
- Restructuring: `BL`, `U`, `NWL`, and `ST` real workforce reduction / restructuring filings.
- Dividend: several `8.01` and mixed earnings filings with real board dividend declarations.

### Experiment B: larger hybrid bucket evaluation

Source: [haiku_router_strategy_evaluation.md](/home/faisal/EventMarketDB/.claude/plans/Extractions/haiku_router_strategy_evaluation.md)

Sample:

- 1,281 live 8-K / 8-K/A filings
- bucketed by filing structure, not just the current four jobs
- goal: determine where Haiku adds value and where deterministic routing is already good enough

Top findings:

| Group | N | Dominant Haiku primary | Dominant rate | Recommendation |
| --- | ---: | --- | ---: | --- |
| `2.02_core` | 120 | `EARNINGS` | 99.17% | deterministic_ok |
| `1.01_2.03_debt` | 119 | `DEBT_FINANCING` | 98.32% | deterministic_ok |
| `2.01_ma` | 119 | `M_AND_A` | 95.80% | deterministic_ok |
| `5.07_governance` | 120 | `GOVERNANCE` | 95.83% | deterministic_ok |
| `2.05_restructuring` | 120 | `RESTRUCTURING` | 71.67% | hybrid_preferred |
| `5.02_exec` | 118 | `EXECUTIVE_CHANGE` | 88.98% | hybrid_preferred |
| `7.01_ambiguous` | 120 | `INVESTOR_PRESENTATION` | 25.83% | llm_needed |
| `8.01_ambiguous` | 120 | `DEBT_FINANCING` | 31.67% | llm_needed |
| `9.01_only` | 89 | `M_AND_A` | 46.07% | llm_needed |
| `rare_other` | 87 | `GOVERNANCE` | 64.37% | llm_needed |

Interpretation:

- Some buckets are structurally obvious enough that deterministic routing should stay primary.
- `7.01`, `8.01`, and `9.01`-only are too semantically diverse for deterministic-only routing.
- Haiku becomes more valuable as the label set grows because multi-label semantic routing scales better than many separate keyword systems.

## Full-Corpus Feasibility

I queried the full 8-K corpus to see how large the ambiguous superset actually is.

Exact query shape used:

```cypher
MATCH (r:Report)
WHERE r.formType IN ['8-K','8-K/A']
WITH r,
CASE
  WHEN r.items CONTAINS 'Item 2.02' AND NOT r.items CONTAINS 'Item 2.01' AND NOT r.items CONTAINS 'Item 2.05' THEN 'deterministic_2.02_core'
  WHEN r.items CONTAINS 'Item 2.01' AND NOT r.items CONTAINS 'Item 2.02' THEN 'deterministic_2.01_ma'
  WHEN r.items CONTAINS 'Item 1.01' AND r.items CONTAINS 'Item 2.03' AND NOT r.items CONTAINS 'Item 2.02' AND NOT r.items CONTAINS 'Item 2.01' THEN 'deterministic_1.01_2.03_debt'
  WHEN r.items CONTAINS 'Item 5.07' AND NOT r.items CONTAINS 'Item 2.02' AND NOT r.items CONTAINS 'Item 7.01' AND NOT r.items CONTAINS 'Item 8.01' THEN 'deterministic_5.07_governance'
  WHEN r.items CONTAINS 'Item 2.05' THEN 'llm_2.05_restructuring'
  WHEN r.items CONTAINS 'Item 5.02' AND NOT r.items CONTAINS 'Item 2.02' AND NOT r.items CONTAINS 'Item 7.01' AND NOT r.items CONTAINS 'Item 8.01' AND NOT r.items CONTAINS 'Item 5.07' THEN 'llm_5.02_exec'
  WHEN r.items CONTAINS 'Item 7.01' AND NOT r.items CONTAINS 'Item 2.02' AND NOT r.items CONTAINS 'Item 8.01' AND NOT r.items CONTAINS 'Item 5.07' THEN 'llm_7.01_ambiguous'
  WHEN r.items CONTAINS 'Item 8.01' AND NOT r.items CONTAINS 'Item 2.02' AND NOT r.items CONTAINS 'Item 7.01' AND NOT r.items CONTAINS 'Item 2.01' THEN 'llm_8.01_ambiguous'
  WHEN r.items = '["Item 9.01: Financial Statements and Exhibits"]' THEN 'llm_9.01_only'
  WHEN (r.items CONTAINS 'Item 3.01' OR r.items CONTAINS 'Item 3.03' OR r.items CONTAINS 'Item 4.01' OR r.items CONTAINS 'Item 4.02' OR r.items CONTAINS 'Item 1.05')
       AND NOT r.items CONTAINS 'Item 2.02'
       AND NOT r.items CONTAINS 'Item 7.01'
       AND NOT r.items CONTAINS 'Item 8.01'
       AND NOT r.items CONTAINS 'Item 5.02' THEN 'llm_rare_other'
  ELSE 'unassigned'
END AS bucket
RETURN bucket, count(*) AS filings
ORDER BY filings DESC
```

Live result:

| Bucket | Filings |
| --- | ---: |
| `deterministic_2.02_core` | 8,821 |
| `llm_8.01_ambiguous` | 3,420 |
| `llm_7.01_ambiguous` | 3,303 |
| `llm_5.02_exec` | 3,252 |
| `deterministic_5.07_governance` | 2,142 |
| `unassigned` | 1,440 |
| `deterministic_1.01_2.03_debt` | 1,330 |
| `llm_2.05_restructuring` | 230 |
| `deterministic_2.01_ma` | 192 |
| `llm_9.01_only` | 114 |
| `llm_rare_other` | 106 |

Total 8-K family filings: `24,350`

Partition summary:

- Deterministic anchor buckets: `12,485` filings (`51.3%`)
- Haiku-valuable buckets: `10,425` filings (`42.8%`)
- Unassigned residue: `1,440` filings (`5.9%`)

## Cost Reality

From the 1,281-filing Haiku run:

- estimated full-corpus cost at observed prompt size: `$33.07`
- average cost per filing: about `$0.00136`

That implies:

- Haiku on all `24,350` historical 8-Ks is cheap.
- Haiku only on the `10,425` ambiguous/hybrid buckets is even cheaper, about `$14.16` at the same average prompt size.

So cost is not the blocker.

Quality is the blocker.

## Best Strategy

### 1. Deterministic anchors stay in place

Use direct routing for buckets where structure is already a very strong proxy for the event family:

- `2.02` core -> earnings
- `2.01` without `2.02` -> M&A / asset transaction
- `1.01 + 2.03` without `2.01` / `2.02` -> debt financing
- `5.07` without `2.02` / `7.01` / `8.01` -> governance / shareholder vote

These are your recall guards.

### 2. Haiku routes the ambiguous superset

Run Haiku on:

- `2.05`
- `5.02`
- `7.01`
- `8.01`
- `9.01`-only
- rare-other administrative buckets such as `3.01`, `3.03`, `4.01`, `4.02`, `1.05`

If implementation simplicity matters more than shaving router cost, run Haiku on all 8-Ks instead. The cost is still trivial compared with extraction.

### 3. Keep deterministic rescue rules for fragile event types

For the current high-stakes jobs, retain rescue logic because Haiku-only misses real events:

- buybacks
- dividends
- restructuring

In practice this means:

- deterministic anchor routes for known high-recall structures
- Haiku semantic routing on the broad superset
- targeted keyword rescues for event families with proven LLM misses

### 4. Final job routing should be union-based

For each extraction job:

`route = deterministic_anchor OR haiku_semantic_yes OR rescue_rule_yes`

That is the key design choice.

Do not let Haiku veto a deterministic recall guard unless you have labeled evidence that the guard is wrong.

## Honest Verdict

If the question is:

- "Is Haiku the best sole router right now?" -> `No`
- "Is hybrid deterministic + Haiku the best overall strategy right now?" -> `Yes`
- "Does Haiku become more attractive as we add more extraction types?" -> `Yes`

Why:

- Deterministic-only does not scale well as the job catalog grows.
- Haiku-only is still too risky for near-zero-miss routing on current fragile jobs.
- Hybrid gives you semantic fan-out, better handling of ambiguous filings, low operating cost, and hard recall backstops.

## Recommended Production Design

1. Deterministic bucket assignment first.
2. Immediate route for anchor buckets.
3. Haiku multi-label classification for ambiguous buckets.
4. Apply targeted rescue heuristics for buyback / dividend / restructuring.
5. Route any job selected by any of the above.
6. Log all disagreements between deterministic and Haiku for ongoing calibration.

## Final Recommendation

For the current system, the best strategy is not "replace heuristics with Haiku."

The best strategy is:

`cheap deterministic recall guards + cheap Haiku semantic fan-out + narrow rescue heuristics`

That is the strongest option found so far.

---
---

# Part V: Combined Conclusions

## Where All Three Analyses Agree

1. **Hybrid routing wins.** Deterministic item codes for recall safety + Haiku for semantic classification on ambiguous buckets. Neither alone is sufficient.
2. **Item 2.02 = earnings with ~100% precision/recall.** No keywords or LLM needed.
3. **Item 9.01 is administrative, not semantic.** Ignore it as an event signal.
4. **Sections are often pointers; exhibits have the real content.** Must search both.
5. **Multi-item filings are the norm.** 81% have 2+ items.
6. **Earnings is the dominant price-moving event.** 6.78% = 2.86x all others.

## Where Analyses Diverged (and resolution)

| Topic | Claude 1 (280 sample) | Claude 2 (130 sample) | Codex 2 (840 sample) | Resolution |
|---|---|---|---|---|
| Haiku buyback recall | High (rejected 8 FPs) | 100% (0 FP) | **~70% (misses real events)** | Codex's larger sample wins — Haiku is NOT safe alone for buybacks |
| Haiku dividend recall | High (9/10 agreement) | 100% (20/20) | **~65% (misses real events)** | Codex's larger sample wins — Haiku is NOT safe alone for dividends |
| Restructuring in 2.02 | "Don't include 2.02" | "Exclude 2.02 — 100% FP" | "Include 2.02 with tighter keywords" | Claude sessions correct for keyword approach; Codex correct that tighter keywords allow 2.02 inclusion |
| Litigation | Not tested | **Tier 1 — 4.65% standalone** | Not specifically tested | Claude 2's unique finding — confirmed by sub-event analysis |
| Prior event prediction | **Tested (Phase 4)** | Conditioning signals | Not tested | Claude 1's Phase 4 is the definitive temporal analysis |

## The Three Unique Contributions

**Claude 1 only:** The amplifier discovery (co-occurring events at earnings: +28-39%) and Phase 4 transparency effect (more filings = less surprise). These are novel empirical findings.

**Claude 2 only:** Litigation identified as Tier 1 extraction type (4.65% standalone — highest non-earnings 8.01 content type). Haiku-classified sub-event analysis within 8.01 revealing content-level impact differences. Conditioning signals with specific numbers (+2.97pp restructuring, -0.72pp buyback).

**Codex 2 only:** Haiku safety analysis at scale (840 filings). Manual spot-checks proving specific tickers where Haiku missed real events (VRTX $3B buyback, OVV dividend increase). The critical finding that Haiku's ~30-35% buyback/dividend miss rate makes it unsafe as sole router.

## The Definitive Architecture

```
WHAT TO BUILD (in priority order):

  1. GUIDANCE EXTRACTION — already built, keep it
     (structured data essential — LLM needs exact numbers)

  2. EVENT TIMELINE via HYBRID ROUTER — build next
     Stage 1: Item codes (deterministic recall guards)
     Stage 2: Haiku classifier (semantic fan-out)
     Stage 3: Keyword rescue (for buyback/dividend where Haiku is weak)
     Route formula: deterministic OR haiku_yes OR rescue_keyword
     NEVER let Haiku veto a deterministic guard

  3. RESTRUCTURING EXTRACTION — build if prediction value confirmed
     Strongest conditioning signal: +2.97pp earnings volatility
     Only prior event proven to predict worse subsequent earnings

  4. LITIGATION EXTRACTION — build if prediction value confirmed
     Highest standalone non-earnings impact: 4.65%
     Earnings conditioning not yet tested

  5. EVERYTHING ELSE — event tags only, no full extraction
     Buybacks, dividends, M&A, debt, exec changes, governance
     Binary signal + date is sufficient
     Earnings press release already contains these topics
```

## Test Artifacts

| File | Source | Content |
|---|---|---|
| `scripts/test_haiku_router.py` | Claude 1 | 280-filing Haiku test script |
| `haiku_router_test_results.json` | Claude 1 | 280-filing classification results |
| `8k_codex_analysis_data.json` | Codex 2 | Raw Codex analysis data |
| `8k_reference.md` | Claude 1 | Pure reference (taxonomy, numbers, queries) |
| `8k_print.md` | Claude 1 | SEC item codes from EDGAR |
