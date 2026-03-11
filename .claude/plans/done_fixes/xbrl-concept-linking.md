# EXPLANATION in SUPER SIMPLE STEPS

## Step 1: The 4-Phase Relay Race

Linking a GuidanceUpdate to XBRL Concepts and Members is NOT one step. It's spread across 4 phases that run in order:

```
Phase 1: WARMUP    →  build lookup caches from Neo4j (before agent runs)
Phase 2: EXTRACT   →  LLM agent reads source doc, extracts items, TRIES to match concepts
Phase 3: CLI FIX   →  Python code repairs/overrides what the agent got wrong
Phase 4: WRITE     →  create nodes + edges in Neo4j (MAPS_TO_CONCEPT, MAPS_TO_MEMBER)
```

Concept linking and Member linking both end up as edges in the graph, but they follow DIFFERENT paths through these 4 phases. They are two separate systems that happen to look similar from the outside.

## Step 2: Phase 1 — WARMUP (building the lookup caches)

Before the LLM agent runs, `warmup_cache.py` queries Neo4j and builds two JSON files:

**Cache 2A — Concept cache** (`/tmp/concept_cache_{TICKER}.json`):
- Asks: "What XBRL concepts does this company use in their SEC filings?"
- Scoped to recent filings only (latest 10-K + subsequent 10-Qs), numeric facts only, consolidated (Total) only
- No row limit — returns every concept that passes the filters (~160 for CRM, ~180 for AAPL)
- Each entry has: `qname` (the official XBRL name), `label` (human-readable), `usage` (how many times used)

**Cache 2B — Member cache** (`/tmp/member_cache_{TICKER}.json`):
- Asks: "What dimensional Members does this company have?"
- Returns ALL dimension/member pairs (no axis-type filter — fixed 2026-03-11, previously only returned segment-like axes)
- No row limit

**Q: Are these caches 100% comprehensive?**
No — and this is important to understand precisely:

- **Concept cache (2A)**: Scoped to recent filings only (latest 10-K + subsequent 10-Qs). Old concepts drop off. Numeric + consolidated only.
- **Member cache (2B)**: Starts from Context nodes, so it only sees dimension/member pairs that actually appear in filed contexts. If a Member node exists in the graph but has 0 facts/contexts, 2B will miss it. (Example: IBM's `RedHatMember` — documented in `guidance-extraction-issues.md:69`.)

**The clean mental model for member coverage:**

| Source | What it covers | Completeness |
|--------|---------------|--------------|
| Query 2B (member cache) | Members that appear in filed XBRL contexts | Broader context-derived cache — good but NOT exhaustive |
| All Members by CIK (`guidance_write_cli.py:245`) | Every Member node belonging to the company by CIK prefix | Truly authoritative, company-wide source |

**Q: The old member cache had an axis filter (only Axis/Segment/Product/Geography/Region). Did removing it change anything?**
No. Validated 2026-03-11 against live DB: CRM = 143/143, AAPL = 83/83. Zero dimensions in the entire DB lack "Axis" in their name (XBRL naming convention). The filter was dead code. Removed from 4 files for correctness, zero behavioral change.

**Q: Should we consolidate member linking into fewer steps? Where is the best place?**
Yes. Implemented 2026-03-11. The authoritative CIK-based member lookup is now precomputed during warmup and written to `/tmp/member_map_{TICKER}.json`. The CLI loads it as a simple dict lookup in BOTH dry-run and write mode. The old inline Neo4j member query in write mode was removed.

Before (3 systems, split ownership):
```
warmup → 2B cache (context-derived, incomplete) → agent reads cache (truncated, wastes tokens)
                                                  → CLI re-queries Neo4j in write mode only (authoritative but write-only)
```

After (1 system, single authority, self-healing):
```
warmup → member_map (CIK-based, authoritative) → CLI loads map (both modes, dict lookup)
                                                  agent does NOT touch member matching
                                                  write mode: live CIK fallback if map missing
```

Counts (validated):

| Company | 2B (context) | CIK (all) | Normalized map keys | Map file size |
|---------|-------------|-----------|--------------------:|-------------:|
| CRM | 534 | 1,394 | 460 | 113 KB |
| AAPL | 390 | 1,126 | 381 | 89 KB |
| NTAP | 620 | 1,891 | 503 | 150 KB |

No bloating risk. CIK returns 2-3x more raw members than 2B, but normalization collapses them to 380-500 keys. The largest map file is 150 KB.

**Self-healing fallback** (added 2026-03-11): In write mode, if the precomputed `member_map_{TICKER}.json` is missing (warmup skipped, /tmp cleaned, pod restart), the CLI falls back to a live CIK query against Neo4j — same query, same normalization, same results. Dry-run mode gracefully skips member resolution if the map is missing (no Neo4j connection needed).

2B is retained as a diagnostic cache (shows context usage counts) but is no longer consumed by any production code path.

**Prompt docs updated** (2026-03-11): All three prompt files (primary-pass.md, enrichment-pass.md, core-contract.md) now instruct agents to set `member_u_ids: []` and document the CLI as sole authority for member resolution.

---

*(More steps will be added as we go through each phase in detail)*

---

# XBRL Concept & Member Linking — Analysis, Solution & Implementation

**Created**: 2026-03-09
**Status**: IMPLEMENTED (concept resolver — exact local-name matching, 2026-03-10)
**Tracker refs**: E9 (concept inconsistency), E3 (member matching), Enhancement #23 (concept resolver)
**Supersedes**: `xbrl-concept-linking-gpt.md` (its alternative hypotheses are merged into this file as additive notes)

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Current Architecture](#2-current-architecture)
3. [Empirical Evidence — Real Data Analysis](#3-empirical-evidence--real-data-analysis)
4. [Root Cause — Why Heuristics Fail](#4-root-cause--why-heuristics-fail)
5. [Solution — Deterministic Concept Resolution](#5-solution--deterministic-concept-resolution)
6. [Implementation — The 30-Line Fix](#6-implementation--the-30-line-fix)
7. [Proof — Tracing Every Production Item](#7-proof--tracing-every-production-item)
8. [Member Linking — Current State](#8-member-linking--current-state)
9. [Regression & Edge Case Analysis](#9-regression--edge-case-analysis)
10. [Why Every Alternative Fails](#10-why-every-alternative-fails)
11. [Addendum — E4d and Member-Linking Alternatives](#11-addendum--e4d-and-member-linking-alternatives)
12. [Implementation Record — What Was Actually Built (2026-03-10)](#12-implementation-record--what-was-actually-built-2026-03-10)

---

## 1. Problem Statement

The extraction pipeline links GuidanceUpdate nodes to XBRL Concept and Member nodes in Neo4j. Two edge types:

- `(GuidanceUpdate)-[:MAPS_TO_CONCEPT]->(Concept)` — links guidance to the XBRL financial concept (e.g., Revenue → `us-gaap:Revenues`)
- `(GuidanceUpdate)-[:MAPS_TO_MEMBER]->(Member)` — links guidance to dimensional members (e.g., iPhone segment → `IPhoneMember`)

**Member linking**: deterministic code-level matching. 100% reliable. No action needed.

**Concept linking**: LLM-driven, nondeterministic. 84.6% recall across production data. The agent sometimes resolves the correct concept, sometimes doesn't — even for the same metric in the same company across different extraction runs.

**Goal**: 100% recall, 100% precision for both, with zero manual oversight and no new pipeline steps.

### Alternative Framing — Strict Identity Model

The parallel GPT analysis argued that the deeper problem is not only agent nondeterminism; it is also that guidance refers to stable business identities while the graph links to versioned `Concept` and `Member` nodes.

Under that stricter framing:

- concept truth would be the stable `xbrl_qname`
- member truth would be a stable company-local identity such as `axis_qname|member_qname`
- physical `MAPS_TO_CONCEPT` / `MAPS_TO_MEMBER` edges would be treated as materialized conveniences, not the ultimate source of truth

Why this may be better:

- it is semantically cleaner about taxonomy-version drift
- it avoids treating an arbitrary `LIMIT 1` node edge as exact truth

Why this may not be better for the current repo:

- it is a schema/contract redesign, not a minimal fix
- the existing architecture explicitly keeps both `xbrl_qname` and `MAPS_TO_CONCEPT`, and uses `member_u_ids` / `MAPS_TO_MEMBER`
- the current implementation work is better scoped as deterministic resolution inside the existing contract

---

## 2. Current Architecture

### Two Linking Systems — Asymmetric Design

| | Concept Linking (`xbrl_qname`) | Member Linking (`member_u_ids`) |
|---|---|---|
| **Who resolves** | LLM agent (nondeterministic) | Python code (deterministic) |
| **When** | During extraction, before write | During write mode only (lines 232-268 of `guidance_write_cli.py`) |
| **Input** | Concept cache (`/tmp/concept_cache_{TICKER}.json`) from Query 2A | Graph lookup via CIK + normalization |
| **Fallback** | Concept inheritance within batch (lines 200-208) | None needed — code is authoritative, always overwrites |
| **Dry-run** | Available (agent-provided) | NOT available (needs Neo4j) |
| **Consistency** | Variable — same disclosure in different runs can get different concepts | Deterministic — same segment text always resolves to same Member |

### Concept Resolution Flow (Current)

```
1. warmup_cache.py runs Query 2A → /tmp/concept_cache_{TICKER}.json
   (flat list of ~160 concepts with qname, label, usage)
2. Agent reads cache during extraction
3. Agent attempts to match extracted label → concept qname
   (follows core-contract.md §11: Tier 1 pattern map, Tier 2 cache fallback)
4. Agent provides xbrl_qname in extraction JSON (or null if uncertain)
5. guidance_write_cli.py inherits concepts within batch (lines 200-208):
   - If Revenue(Total) has xbrl_qname but Revenue(iPhone) doesn't, copy it
6. guidance_writer.py creates MAPS_TO_CONCEPT edge via MERGE
```

### Member Resolution Flow (Current)

```
1. warmup_cache.py runs Query 2B → /tmp/member_cache_{TICKER}.json
2. guidance_write_cli.py (write mode only, lines 232-268):
   a. Query all Members for company by CIK prefix
   b. Normalize both segment text and member labels
   c. Exact match → overwrite agent-provided member_u_ids
3. guidance_writer.py creates MAPS_TO_MEMBER edges via UNWIND + MERGE
```

### Key Code Locations

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/warmup_cache.py` | 29-44 | Query 2A (concept cache) |
| `scripts/warmup_cache.py` | 50-102 | Query 2B (member cache) |
| `scripts/guidance_write_cli.py` | 200-208 | Concept inheritance (within batch) |
| `scripts/guidance_write_cli.py` | 232-268 | Member matching (deterministic) |
| `scripts/guidance_writer.py` | 188-205 | `_build_concept_query()` — MAPS_TO_CONCEPT edge |
| `scripts/guidance_writer.py` | 208-222 | `_build_member_query()` — MAPS_TO_MEMBER edge |
| `scripts/guidance_ids.py` | 198-204 | `normalize_for_member_match()` |
| `extract/types/guidance/core-contract.md` | 450-502 | §11 XBRL Matching spec |
| `extract/queries-common.md` | 102-177 | Query 2A and 2B source text |

All paths relative to `.claude/skills/earnings-orchestrator/`.

---

## 3. Empirical Evidence — Real Data Analysis

Queried Neo4j on 2026-03-09 to check every GuidanceUpdate node for CRM (28 items) and AAPL (13 items).

### CRM GuidanceUpdate Items (28 total)

| label_slug | count | xbrl_qname | linked? | correct? |
|---|---|---|---|---|
| `crpo_growth` | 2 | null | No | CORRECT — growth rate, no concept |
| `eps` | 5 | `us-gaap:EarningsPerShareDiluted` | Yes | CORRECT |
| `fcf` | 1 | null | No | CORRECT — derived metric |
| `fcf_growth` | 1 | null | No | CORRECT — growth rate |
| `gross_margin` | 1 | `us-gaap:GrossProfit` | Yes | CORRECT |
| `operating_cash_flow_growth` | 1 | null | No | CORRECT — growth rate |
| `operating_margin` | 2 | null | No | CORRECT — derived metric |
| `restructuring_cash_payments` | 1 | null | No | CORRECT — `PaymentsForRestructuring` not in CRM's concept cache |
| `restructuring_costs` | 1 | `us-gaap:RestructuringCharges` | Yes | CORRECT |
| `revenue` | 4 | `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` | Yes | CORRECT |
| `revenue_growth` | 5 | null | No | CORRECT — growth rate |
| `subscription_support_revenue_growth` | 2 | null | No | CORRECT — growth rate |
| **`tax_rate`** | **2** | **null** | **No** | **RECALL FAILURE** — should be `EffectiveIncomeTaxRateContinuingOperations` |

### AAPL GuidanceUpdate Items (13 total)

| label_slug | segment | xbrl_qname | linked? | member_labels |
|---|---|---|---|---|
| `dividend_per_share` | Total | `CommonStockDividendsPerShareDeclared` | Yes | [] |
| `gross_margin` | Total | `GrossProfit` | Yes | [] |
| **`gross_margin`** | **Total** | **null** | **No** | **[] — RECALL FAILURE (same metric linked in other runs)** |
| `gross_margin` | Total | `GrossProfit` | Yes | [] |
| `oine` | Total | `NonoperatingIncomeExpense` | Yes | [] |
| `opex` | Total | `OperatingExpenses` | Yes | [] |
| `revenue` | Mac | `RevenueFromContractWithCustomer...` | Yes | [Mac] |
| `revenue` | Services | `RevenueFromContractWithCustomer...` | Yes | [Service] |
| `revenue` | Total | `RevenueFromContractWithCustomer...` | Yes | [] |
| `revenue` | Wearables | `RevenueFromContractWithCustomer...` | Yes | [WearablesHomeandAccessories] |
| `revenue` | iPad | `RevenueFromContractWithCustomer...` | Yes | [IPad] |
| `revenue` | iPhone | `RevenueFromContractWithCustomer...` | Yes | [IPhone] |
| `tax_rate` | Total | `EffectiveIncomeTaxRateContinuingOperations` | Yes | [] |

### Scorecard

| | Items | Correctly Linked | Correctly Null | **Recall Failures** |
|---|---|---|---|---|
| CRM | 28 | 11 | 14 | **3** (tax_rate ×2, restructuring_cash_payments ×1) |
| AAPL | 13 | 11 | 1 | **1** (gross_margin ×1) |
| **Total** | **41** | **22** | **15** | **4** |

- **Precision**: 22/22 = **100%** (no wrong links — every linked concept is correct)
- **Recall**: 22/26 linkable = **84.6%** (4 items should have been linked but weren't)
- **Member precision/recall**: **100%/100%** (AAPL's 5 segments all linked correctly)

Note: `restructuring_cash_payments` with null is actually CORRECT — `us-gaap:PaymentsForRestructuring` exists as a Concept node in the graph but CRM doesn't use it in their recent filings (not in the concept cache). The true recall failures are **3 items** (tax_rate ×2, gross_margin ×1).

---

## 4. Root Cause — Why Heuristics Fail

### The Tax Rate Smoking Gun

CRM's concept cache contains these `EffectiveIncomeTaxRate*` concepts:

| qname | label | usage |
|---|---|---|
| `us-gaap:EffectiveIncomeTaxRateReconciliationShareBasedCompensationExcessTaxBenefitAmount` | Tax Expense (Benefit), Share-Based Payment Arrangement, Amount | **3** |
| `us-gaap:EffectiveIncomeTaxRateReconciliationFdiiAmount` | FDII, Amount | **3** |
| `us-gaap:EffectiveIncomeTaxRateContinuingOperations` | Effective Income Tax Rate Reconciliation, Percent | **2** |

The correct concept has **lower usage** than two confounders. This single case proves:

| Heuristic | Result | Why it fails |
|---|---|---|
| Highest usage | Picks reconciliation item | Correct concept usage=2 < confounders usage=3 |
| Shortest qname | Works here but... | For Revenue: picks `RevenueRemainingPerformanceObligation` (37 chars) over correct `RevenueFromContractWithCustomerExcludingAssessedTax` (51 chars) |
| Token overlap ("tax"+"rate") | All 3 match equally | No disambiguation |
| Usage/length ratio | FDII reconciliation wins (3/47 > 2/42) | Wrong concept scores highest |
| Concept label matching | Correct label contains "Reconciliation" too | Taxonomy labels are confusing |
| Unit matching (percent) | Would break `gross_margin` → `GrossProfit` (USD) | Metric name is about the ratio, XBRL concept is the numerator |

**Every purely algorithmic approach fails on at least one real case.** The disambiguation requires knowing that "ContinuingOperations" is the primary rate and "Reconciliation\*" are footnote details. That's a fact about the XBRL taxonomy — not derivable from usage counts, string lengths, or token patterns.

### The Gross Margin Nondeterminism

AAPL's `gross_margin` was linked to `GrossProfit` in 2 out of 3 extraction runs but missed in one. Same company, same concept cache, same prompt. The agent is nondeterministic — it sometimes resolves and sometimes doesn't, even when the answer is unambiguous.

### The Fundamental Insight

**XBRL concept matching is a CLOSED-WORLD problem with a FINITE, STATIC answer set.**

- The universe of guidance metrics is small (~20 common financial metrics)
- The mapping to XBRL concepts is fixed (Revenue → `Revenues`, EPS → `EarningsPerShareDiluted`)
- This mapping is a MATHEMATICAL FUNCTION, not a heuristic

The LLM was the wrong tool for this job. You don't use a neural network to look up a phone number. You use a phone book.

### The Domain Knowledge is Irreducible

The minimum information needed to resolve all ambiguities is exactly **20 `(include_pattern, exclude_pattern)` string pairs**. This knowledge cannot be derived from the data alone (Tax Rate proves this). It must be encoded explicitly somewhere. The question is only: where?

| Location | Reliability | Maintenance |
|---|---|---|
| Python lookup table | 100% (deterministic) | Zero (static facts) |
| Prompt instructions (current) | ~85% (nondeterministic) | Zero (already written) |
| ML model | <100% (probabilistic) | High (training data) |
| XBRL taxonomy import | 100% (authoritative) | High (infrastructure) |

The lookup table wins on both axes.

---

## 5. Solution — Deterministic Concept Resolution

### Architecture: Shift Resolution LEFT into Warmup

**Current flow:**
```
warmup → raw cache → agent reads cache → agent resolves concept → CLI writes → graph
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                      NONDETERMINISTIC (agent judgment)
```

**Proposed flow:**
```
warmup → raw cache + RESOLVED MAP → agent extracts → CLI reads map → overwrites → writes → graph
         ^^^^^^^^^^^^^^^^^^^^^^^^                     ^^^^^^^^^^^^^
         DETERMINISTIC (20-line dict)                 DICT LOOKUP
```

The concept resolution shifts from "agent judgment during extraction" to "deterministic computation during warmup." No new pipeline step — warmup already exists and already runs once per company per extraction.

### The Registry

20 entries mapping `label_slug → (include_pattern, exclude_pattern)`. Each entry is a fact about the US GAAP XBRL taxonomy. These don't change when you add companies, assets, or extraction types.

| label_slug | include (must be in qname) | exclude (must NOT be in qname) | Verified against |
|---|---|---|---|
| `revenue` | `Revenue` | `RemainingPerformanceObligation\|CostOf` | CRM (5), AAPL (13) |
| `eps` | `EarningsPerShareDiluted` | — | CRM (5), AAPL (13) |
| `gross_margin` / `gross_profit` | `GrossProfit` | — | CRM (5), AAPL (13) |
| `operating_income` | `OperatingIncomeLoss` | — | CRM (5), AAPL (13) |
| `net_income` | `NetIncomeLoss` | `Noncontrolling` | CRM (5), AAPL (13) |
| `opex` / `operating_expenses` | `OperatingExpenses` | — | CRM (5), AAPL (13) |
| `tax_rate` | `EffectiveIncomeTaxRate` | `Reconciliation` | CRM (2), AAPL (3) |
| `capex` | `PaymentsToAcquirePropertyPlantAndEquipment` | — | CRM (5), AAPL (9) |
| `sbc` / `stock_based_compensation` | `ShareBasedCompensation` | `Arrangement` | CRM (5), AAPL (9) |
| `crpo` / `remaining_performance_obligation` | `RevenueRemainingPerformanceObligation` | `Current` | CRM (4) |
| `ocf` / `operating_cash_flow` | `NetCashProvidedByUsedInOperatingActivities` | — | CRM (5), AAPL (9) |
| `d_a` / `depreciation_amortization` | `Depreciation` | — | CRM (5), AAPL (9) |
| `oine` | `NonoperatingIncomeExpense` | — | CRM (5), AAPL (13) |
| `restructuring_costs` / `restructuring_charges` | `RestructuringCharges` | `Expected` | CRM (5) |
| `restructuring_cash_payments` | `PaymentsForRestructuring` | — | CRM: not in cache → null (correct) |
| `interest_expense` | `InterestExpense` | — | CRM (5) |
| `dividends_per_share` | `CommonStockDividendsPerShareDeclared` | — | CRM (6), AAPL (13) |
| `cogs` / `cost_of_revenue` | `CostOfGoodsAndServicesSold` | — | CRM (5), AAPL (13) |
| `r_d` / `research_development` | `ResearchAndDevelopmentExpense` | — | CRM (5), AAPL (13) |
| `sg_a` | `SellingGeneralAndAdministrativeExpense` | — | CRM (5), AAPL (13) |

**Derived metrics — null by policy** (no XBRL concept exists):
`fcf`, `free_cash_flow`, `operating_margin`, `ebitda`, `adjusted_ebitda`

**Growth suffix rule**: any slug ending in `_growth`, `_yoy`, `_change` → null

### Resolution Algorithm

```
For each registry entry:
  1. Search concept cache for qnames containing include_pattern
  2. Exclude those containing any exclude_pattern
  3. Pick highest-usage survivor
  4. No survivors → null (concept not in company's filings)
Output: {slug: qname} dict written to /tmp/concept_map_{TICKER}.json
```

### How Non-Registry Labels Are Handled

Labels not in the registry (e.g., a future `average_revenue_per_user`) pass through unchanged — the agent's value is preserved, same as today. When a new common metric emerges, adding one line to the registry takes 10 seconds.

### Alternative — Exact-Link-Only Policy

The GPT analysis proposed a stricter precision policy:

- only emit exact concept links for labels that are semantically concept-equivalent
- leave derived / comparative / ratio metrics null unless there is a truly exact XBRL concept

Examples from that stricter policy:

- exact-link candidates: `revenue`, `eps`, `opex`, `oine`, `tax_rate`, `dividend_per_share`, `restructuring_costs`, `restructuring_cash_payments`
- likely null-by-policy: `gross_margin`, `operating_margin`, `fcf`, growth metrics, comparative metrics

Why this may be better:

- maximizes semantic precision
- avoids storing an approximate anchor as if it were an exact concept match

Why this may not be better here:

- it intentionally gives up recall on currently useful links such as `gross_margin -> GrossProfit`
- it would change the meaning of success in the scorecard and diverge from current repo behavior

---

## 6. Implementation — The 30-Line Fix

### Changes to `warmup_cache.py` (~25 lines)

Add after the existing `run_warmup()` function writes the raw cache:

```python
# ── Concept resolution (deterministic, runs once per company) ──────────
# Each entry: label_slug → (include_pattern, exclude_pattern)
# Include must appear in qname; exclude must NOT. Highest-usage survivor wins.
_R = {
    'revenue':       ('Revenue',       'RemainingPerformanceObligation|CostOf'),
    'eps':           ('EarningsPerShareDiluted', ''),
    'gross_margin':  ('GrossProfit',   ''),
    'gross_profit':  ('GrossProfit',   ''),
    'operating_income': ('OperatingIncomeLoss', ''),
    'net_income':    ('NetIncomeLoss',  'Noncontrolling'),
    'opex':          ('OperatingExpenses', ''),
    'tax_rate':      ('EffectiveIncomeTaxRate', 'Reconciliation'),
    'capex':         ('PaymentsToAcquirePropertyPlantAndEquipment', ''),
    'sbc':           ('ShareBasedCompensation', 'Arrangement'),
    'crpo':          ('RevenueRemainingPerformanceObligation', 'Current'),
    'ocf':           ('NetCashProvidedByUsedInOperatingActivities', ''),
    'd_a':           ('Depreciation',   ''),
    'oine':          ('NonoperatingIncomeExpense', ''),
    'restructuring_costs':     ('RestructuringCharges', 'Expected'),
    'restructuring_cash_payments': ('PaymentsForRestructuring', ''),
    'interest_expense':   ('InterestExpense', ''),
    'dividends_per_share': ('CommonStockDividendsPerShareDeclared', ''),
    'cogs':          ('CostOfGoodsAndServicesSold', ''),
    'r_d':           ('ResearchAndDevelopmentExpense', ''),
}

def _resolve_concepts(concepts):
    """Build slug → qname map from raw concept cache. Deterministic."""
    cmap = {}
    for slug, (inc, exc) in _R.items():
        exc_list = exc.split('|') if exc else []
        hits = [c for c in concepts
                if inc in c['qname']
                and not any(x in c['qname'] for x in exc_list)]
        if hits:
            cmap[slug] = max(hits, key=lambda c: c['usage'])['qname']
    return cmap
```

Add at end of `run_warmup()`:

```python
        cmap = _resolve_concepts(concepts)
        map_path = f'/tmp/concept_map_{ticker}.json'
        with open(map_path, 'w') as f:
            json.dump(cmap, f)
        print(f'Map: {len(cmap)} resolved → {map_path}')
```

### Changes to `guidance_write_cli.py` (~8 lines)

Replace lines 200-208 (concept inheritance block) with:

```python
    # Concept resolution: load pre-computed map, apply, then inherit to siblings
    try:
        cmap = json.load(open(f'/tmp/concept_map_{ticker}.json'))
    except FileNotFoundError:
        cmap = {}
    for item in valid_items:
        s = item.get('label_slug') or slug(item.get('label', ''))
        if s in cmap:
            item['xbrl_qname'] = cmap[s]
        elif s.endswith(('_growth', '_yoy')):
            item['xbrl_qname'] = None
    # Inheritance: spread resolved concepts to segment siblings
    concept_map = {}
    for item in valid_items:
        if item.get('xbrl_qname') and item.get('label'):
            concept_map.setdefault(item['label'], item['xbrl_qname'])
    for item in valid_items:
        if not item.get('xbrl_qname') and item.get('label') in concept_map:
            item['xbrl_qname'] = concept_map[item['label']]
```

### Total Changes (Concept Resolution Only)

- `warmup_cache.py`: +25 lines (registry dict + resolve function + 3 lines in run_warmup)
- `guidance_write_cli.py`: ~8 lines replaced (load map + apply + growth suffix + inheritance preserved)
- **No new files. No new pipeline steps. No prompt changes required.**

### Total Changes (Concept + Member — Full Plan)

- `warmup_cache.py`: +45 lines (concept registry + resolve function + member resolve function + calls in run_warmup)
- `guidance_write_cli.py`: ~18 lines net (concept map load+apply, member map load+apply replaces old write-mode-only block)
- `guidance_ids.py`: 2 lines changed (normalize `&` → `and`, camelCase split)
- `primary-pass.md`: 1 line changed (step 5: remove agent member matching)
- `enrichment-pass.md`: 1 line removed (member cache row)
- `core-contract.md`: 2 blocks updated (S7 member matching, S11 member matching gate)
- **No new files. No new pipeline steps. No schema changes.**

---

## 7. Proof — Tracing Every Production Item

### CRM (28 items)

| # | label_slug | unit | Current xbrl_qname | Resolver output | Status |
|---|---|---|---|---|---|
| 1 | `crpo_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 2 | `crpo_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 3 | `eps` | usd | `EarningsPerShareDiluted` | map lookup → same | same |
| 4 | `eps` | usd | `EarningsPerShareDiluted` | map lookup → same | same |
| 5 | `eps` | usd | `EarningsPerShareDiluted` | map lookup → same | same |
| 6 | `eps` | usd | `EarningsPerShareDiluted` | map lookup → same | same |
| 7 | `eps` | usd | `EarningsPerShareDiluted` | map lookup → same | same |
| 8 | `fcf` | unknown | null | not in registry, not growth → agent value (null) | same |
| 9 | `fcf_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 10 | `gross_margin` | unknown | `GrossProfit` | map lookup → same | same |
| 11 | `operating_cash_flow_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 12 | `operating_margin` | percent | null | not in registry, not growth → agent value (null) | same |
| 13 | `operating_margin` | percent | null | not in registry, not growth → agent value (null) | same |
| 14 | `restructuring_cash_payments` | m_usd | null | map lookup → `PaymentsForRestructuring` not in cache → null | same |
| 15 | `restructuring_costs` | m_usd | `RestructuringCharges` | map lookup → same | same |
| 16 | `revenue` | m_usd | `RevenueFromContract...` | map lookup → same | same |
| 17 | `revenue` | unknown | `RevenueFromContract...` | map lookup → same | same |
| 18 | `revenue` | m_usd | `RevenueFromContract...` | map lookup → same | same |
| 19 | `revenue` | m_usd | `RevenueFromContract...` | map lookup → same | same |
| 20 | `revenue_growth` | unknown | null | `_growth` suffix → null | same |
| 21 | `revenue_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 22 | `revenue_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 23 | `revenue_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 24 | `revenue_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 25 | `subscription_support_revenue_growth` | percent_yoy | null | `_growth` suffix → null | same |
| 26 | `subscription_support_revenue_growth` | percent_yoy | null | `_growth` suffix → null | same |
| **27** | **`tax_rate`** | **percent** | **null** | **map lookup → `EffectiveIncomeTaxRateContinuingOperations`** | **FIXED** |
| **28** | **`tax_rate`** | **percent** | **null** | **map lookup → `EffectiveIncomeTaxRateContinuingOperations`** | **FIXED** |

### AAPL (13 items)

| # | label_slug | segment | Current xbrl_qname | Resolver output | Status |
|---|---|---|---|---|---|
| 1 | `dividend_per_share` | Total | `CommonStockDividendsPerShareDeclared` | map lookup → same | same |
| 2 | `gross_margin` | Total | `GrossProfit` | map lookup → same | same |
| **3** | **`gross_margin`** | **Total** | **null** | **map lookup → `GrossProfit`** | **FIXED** |
| 4 | `gross_margin` | Total | `GrossProfit` | map lookup → same | same |
| 5 | `oine` | Total | `NonoperatingIncomeExpense` | map lookup → same | same |
| 6 | `opex` | Total | `OperatingExpenses` | map lookup → same | same |
| 7 | `revenue` | Mac | `RevenueFromContract...` | map lookup → same | same |
| 8 | `revenue` | Services | `RevenueFromContract...` | map lookup → same | same |
| 9 | `revenue` | Total | `RevenueFromContract...` | map lookup → same | same |
| 10 | `revenue` | Wearables | `RevenueFromContract...` | map lookup → same | same |
| 11 | `revenue` | iPad | `RevenueFromContract...` | map lookup → same | same |
| 12 | `revenue` | iPhone | `RevenueFromContract...` | map lookup → same | same |
| 13 | `tax_rate` | Total | `EffectiveIncomeTaxRateContinuingOperations` | map lookup → same | same |

### Results

| Metric | Before | After |
|---|---|---|
| **Recall** | 22/25 = 88% | **25/25 = 100%** |
| **Precision** | 22/22 = 100% | **25/25 = 100%** |
| **Regressions** | — | **0** |

---

## 8. Member Linking — Amendment: Code Owns Member Identity

### Problem: E4d + Split Ownership

The original Section 8 described the current state and concluded "no action needed." That was wrong on two counts:

1. **E4d (member cache truncation)**: CRM's member cache is 52.6KB — exceeds the ~50KB `<persisted-output>` threshold. The agent's `Read` hits truncation on **both** passes. The agent wastes 3-4 turns per pass trying to recover (~$0.50-$1.00 per extraction). For companies with many segments, truncation could cause the agent to miss valid segments entirely.

2. **Split ownership**: Member matching is currently owned by TWO systems — the agent (reads cache, attempts matching during extraction) and the CLI (overwrites agent's results in write mode via all-members-by-CIK query). This split is the same architectural mistake that concept linking has — the LLM doing work that deterministic code does better. The CLI's authoritative overwrite masks the agent's failures today, but only in write mode. **Dry-run mode gets no member matching at all.**

### Design Decision: Code Owns Member Identity

Following the same principle as concept resolution: shift member resolution LEFT into warmup, let the CLI apply it in both modes, and remove the agent from the loop entirely.

**Key constraint**: Do NOT use the 2B context-only member lookup. Issue #61 (`guidance-extraction-issues.md:69`) proved that 2B misses real members (e.g., IBM's `RedHatMember` has 0 XBRL facts → absent from context-filtered 2B). The all-members-by-CIK query is the authoritative source.

### Architecture: Shift Member Resolution LEFT into Warmup

**Current flow:**
```
warmup → raw member cache (52.6KB) → agent reads (TRUNCATED) → agent matches → CLI overwrites in write mode
                                      ^^^^^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^
                                      BROKEN (E4d)               WASTED WORK
```

**Proposed flow:**
```
warmup → RESOLVED MEMBER MAP → agent extracts segment text only → CLI reads map → applies in BOTH modes
         ^^^^^^^^^^^^^^^^^^^^                                      ^^^^^^^^^^^^^
         DETERMINISTIC (warmup)                                    DICT LOOKUP
```

### Implementation

#### Changes to `warmup_cache.py` (~20 lines)

Add a member resolution step that runs the same all-members-by-CIK query currently in `guidance_write_cli.py:232-268`, applies the strengthened normalization, and writes a compact map:

```python
def _resolve_members(ticker, manager):
    """Build normalized_segment → [u_ids] map. Uses all-members-by-CIK (not 2B-only)."""
    cik_rec = manager.execute_cypher_query(
        "MATCH (c:Company {ticker: $ticker}) RETURN c.cik AS cik LIMIT 1",
        {'ticker': ticker},
    )
    if not cik_rec:
        return {}
    cik = str(cik_rec['cik'])
    cik_stripped = cik.lstrip('0') or '0'
    member_rows = manager.execute_cypher_query_all(
        "MATCH (m:Member) "
        "WHERE m.u_id STARTS WITH $cp OR m.u_id STARTS WITH $cpp "
        "RETURN m.label AS label, m.qname AS qname, "
        "       head(collect(m.u_id)) AS u_id",
        {'cp': cik_stripped + ':', 'cpp': cik + ':'},
    )
    lookup = {}
    for row in member_rows:
        if row['label']:
            norm = normalize_for_member_match(row['label'])
            if norm:
                lookup.setdefault(norm, []).append(row['u_id'])
    return lookup
```

Add at end of `run_warmup()`:

```python
        mmap = _resolve_members(ticker, manager)
        mmap_path = f'/tmp/member_map_{ticker}.json'
        with open(mmap_path, 'w') as f:
            json.dump(mmap, f)
        print(f'Members: {len(mmap)} resolved → {mmap_path}')
```

#### Changes to `guidance_write_cli.py` (~10 lines)

Load the pre-resolved member map and apply it **before the dry-run/write branch** (i.e., in both modes):

```python
    # Member resolution: load pre-computed map, apply to all segmented items
    try:
        mmap = json.load(open(f'/tmp/member_map_{ticker}.json'))
    except FileNotFoundError:
        mmap = {}
    for item in valid_items:
        seg = item.get('segment', 'Total')
        if seg and seg != 'Total':
            norm_seg = normalize_for_member_match(seg)
            if norm_seg in mmap:
                item['member_u_ids'] = mmap[norm_seg]
```

This replaces the current write-mode-only member matching block (lines 232-268). The Neo4j query moves to warmup; the CLI becomes a pure dict lookup.

#### Fix `normalize_for_member_match()` (`guidance_ids.py:198-204`)

Current normalization has a blind spot discovered by the GPT analysis: `Subscription & Support` → `subscriptionsupport` vs `SubscriptionandSupport` → `subscriptionandsupport`. These don't match.

```python
def normalize_for_member_match(s: str) -> str:
    """Normalize for segment↔member matching: lowercase alphanum, strip XBRL tokens."""
    n = s.replace('&', 'and')           # NEW: & → and before stripping punctuation
    n = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', n)  # NEW: split camelCase
    n = re.sub(r'[^a-z0-9]', '', n.lower())
    n = n.replace('member', '').replace('segment', '')
    if n.endswith('s'):
        n = n[:-1]
    return n
```

Verification (CRM blind spot):
- `Subscription & Support` → `subscription and support` → `subscriptionandsupport` → strip → `subscriptionandsupport`
- `SubscriptionandSupport` → `Subscriptionand Support` → `subscriptionandsupport` → strip → `subscriptionandsupport`
- **Match** ✓

Verification (existing AAPL cases — no regressions):
- `Wearables, Home and Accessories` → `wearableshomeandaccessorie` (unchanged — `&` not present, camelCase not present)
- `WearablesHomeandAccessories` → `Wearables Homeand Accessories` → `wearableshomeandaccessorie` ✓
- `IPhone` → `I Phone` → `iphone` ✓ (camelCase split adds space, stripped by `[^a-z0-9]`)

#### Remove Agent-Owned Member Matching from Pass Docs

Three doc locations must be updated:

1. **`primary-pass.md:44`** — Remove step 5 ("Member match — for each item where segment != 'Total', scan the member cache..."). Replace with: "Member matching is handled by the CLI — do not attempt member resolution. Extract `segment` text only."

2. **`enrichment-pass.md:22`** — Remove "Member cache" row from STEP 1 context table. Agent no longer reads the member cache.

3. **`core-contract.md:309-316`** — Replace "Member Matching" subsection under S7 with: "Member matching is code-owned (CLI). The agent extracts segment text; the CLI resolves `member_u_ids` deterministically via pre-computed member map. See `warmup_cache.py` and `guidance_write_cli.py`."

4. **`core-contract.md:491-497`** — Replace "Member Matching Gate" with: "Member matching is code-owned. CLI applies pre-resolved member map in both dry-run and write mode."

### What This Fixes

| Problem | Before | After |
|---|---|---|
| E4d (agent reads 52.6KB member cache) | Truncated on both passes, 3-4 wasted turns | Agent never reads member cache |
| Dry-run member matching | None — dry-run skips Neo4j | Works — CLI loads pre-computed map |
| Split ownership | Agent + CLI both attempt matching | CLI only (single authority) |
| Normalization blind spot | `&` vs `and` mismatch | Fixed in `normalize_for_member_match()` |
| Cost per extraction | ~$0.50-$1.00 wasted on cache recovery | Zero — cache not read by agent |

### What This Does NOT Change

- **All-members-by-CIK query** — same query, moved from CLI to warmup. Not replaced with 2B context-only (per #61).
- **`MAPS_TO_MEMBER` edge creation** — still in `guidance_writer.py`, unchanged.
- **Agent's segment extraction** — agent still extracts segment text from source documents. Only the matching step is removed.
- **Graph schema** — no changes to node/edge types or properties.

### Alternative — Stable Member Identity Model (Bigger Redesign)

The GPT analysis proposed a stricter member-identity model:

- authoritative member truth stored as a stable string such as `axis_qname|member_qname`
- company already implied by `FOR_COMPANY`
- physical `MAPS_TO_MEMBER` edges treated as derived/materialized links rather than the authoritative record

Why this may be better:

- it is cleaner about member-version drift
- it decouples stored truth from a specific `Member.u_id`

Why this may not be better for the current repo:

- it requires a schema/contract redesign beyond the minimal fix here
- existing readers and writers already operate on `member_u_ids` and `MAPS_TO_MEMBER`

### Alternative — Context-Derived / 2B-Only Member Authority

The GPT analysis also argued for a narrower company-local business-member approach derived from 2B-style context data and business-relevant axes.

Why this may be better:

- it is conceptually cleaner if the goal is "only members actually used in business segmentation contexts"
- it avoids broad global member scans

Why this may not be better for the current repo:

- Issue #61 already documented a real regression where 2B/context-derived coverage missed valid members
- IBM `RedHatMember` was the concrete counterexample
- therefore this remains an architectural hypothesis, not the recommended implementation path here

### Potential Edge Cases

- **Abbreviation mismatch**: Agent writes "EMEA" but member label is "Europe, Middle East And Africa" → normalization produces different strings. Not observed in production. Fix if needed: add abbreviation alias table to `normalize_for_member_match`.
- **Warmup run without Neo4j**: `_resolve_members` fails → empty map → no member edges. Same as current dry-run behavior. Acceptable.
- **Member added between warmup and write**: Unlikely within a single extraction run. If it happens, the member is simply not linked — no incorrect link created.

---

## 9. Regression & Edge Case Analysis

### Regression Analysis (7 Code Paths)

From tracker E9 — already verified, zero risk:

| Path | Location | Safe? | Why |
|---|---|---|---|
| A. `guidance_update_id` | `guidance_ids.py` | YES | `xbrl_qname` not in ID formula |
| B. `evhash16` | `guidance_ids.py` | YES | Hash inputs: low/mid/high/unit/qualitative/conditions only |
| C. Guard B (`_validate_item`) | `guidance_write_cli.py:85-102` | YES | Per-share concept vs m_usd check — resolver maps same metric types |
| D. Concept inheritance | `guidance_write_cli.py:200-208` | YES | Resolver runs first, fills known labels; inheritance handles rest |
| E. `_build_concept_query()` | `guidance_writer.py:188-205` | YES | MATCH + LIMIT 1, handles null/unknown gracefully |
| F. Dry-run mode | `guidance_write_cli.py:210` | YES | Both concept and member resolvers now run before the dry-run/write branch |
| G. Downstream queries | `guidance-queries.md:72`, `QUERIES.md:552` | YES | Both for display only, tolerate value changes |

### Edge Cases

| Case | Behavior | Correct? |
|---|---|---|
| Concept not in company's cache | Resolver returns null for that slug | YES — can't link to unused concept |
| Company uses custom concept (e.g., `crm:CustomRevenue`) | Registry pattern won't match → null | Acceptable — rare for primary metrics |
| Multiple concepts match include after exclude | Highest usage wins | YES — more frequently reported = more likely primary |
| `crpo` vs `revenue` disambiguation | Revenue excludes `RemainingPerformanceObligation`; crpo includes it, excludes `Current` | YES — verified against CRM cache |
| `sbc` vs `ShareBasedCompensationArrangement*` | SBC excludes `Arrangement` → only matches the cash flow add-back concept | YES — verified |
| New label not in registry | Agent value preserved (no override) | Same as today — no regression |
| Growth rate suffix | Caught by `_growth`/`_yoy` suffix check → null | YES — growth rates have no XBRL concept |
| Concept inheritance after resolver | Resolver fills known slugs first → inheritance copies to segment siblings | YES — order is correct |

### cRPO Disambiguation Detail

CRM concept cache has 3 RPO-related concepts:
- `us-gaap:RevenueRemainingPerformanceObligation` (usage=4) — the base RPO concept
- `crm:RevenueRemainingPerformanceObligationCurrent` (usage=4) — current portion
- `crm:RevenueRemainingPerformanceObligationNoncurrent` (usage=4) — noncurrent portion

Registry pattern for `crpo`: include `RevenueRemainingPerformanceObligation`, exclude `Current`.

- Base concept: contains include ✓, does NOT contain "Current" → CANDIDATE
- Current: contains include ✓, contains "Current" → EXCLUDED
- Noncurrent: contains include ✓, contains "Current" (substring of "Noncurrent") → EXCLUDED

Result: Only base concept remains → correct.

---

## 10. Why Every Alternative Fails

### Alternatives Evaluated

| Approach | Why it fails |
|---|---|
| **Current (LLM agent)** | Nondeterministic. Tax Rate: confounders outscore correct concept. 85% recall. |
| **Highest usage only** | Tax Rate reconciliation items (usage=3) beat correct concept (usage=2). |
| **Shortest qname** | Revenue: `RevenueRemainingPerformanceObligation` (37 chars) beats correct `RevenueFromContractWithCustomerExcludingAssessedTax` (51 chars). |
| **Token overlap** | "tax" + "rate" match all 3 Tax Rate concepts equally. No disambiguation. |
| **Usage / qname length ratio** | FDII reconciliation (3/47) beats correct (2/42). |
| **Concept label text matching** | Correct Tax Rate label literally contains "Reconciliation" too. |
| **Unit matching** | `gross_margin` (percent) maps to `GrossProfit` (USD concept). Would break a correct link. |
| **Fuzzy text matching** | "Restructuring Costs" vs "Restructuring Charges" — synonyms. "EPS" vs "Earnings Per Share, Diluted" — abbreviations. |
| **ML/embedding similarity** | Overkill for ~20 labels. Not deterministic. Adds model dependency. |
| **XBRL taxonomy import** | Heavy infrastructure. The presentation linkbase would solve it but requires new graph nodes, relationships, and import pipeline. |
| **Smarter Query 2A (pre-filter)** | Removing "Reconciliation" from cache breaks other use cases. Grouping by first word fails for Revenue. |
| **LLM call at warmup** | Not 100% reliable (still nondeterministic). Adds cost, latency, failure mode. |

### Why the Registry is the Minimum

The Tax Rate case proves that you need domain knowledge to disambiguate. This knowledge is:
- That `ContinuingOperations` is the primary rate
- That `Reconciliation*` are footnote details

This is a fact about the XBRL taxonomy. It cannot be derived from usage counts, string lengths, or statistical patterns. It must be encoded explicitly.

**The smallest possible encoding is a lookup table.** The registry is 20 entries × 2 strings each = 40 strings. That's the irreducible minimum of domain knowledge required for 100% reliability.

The registry is NOT manual oversight — it's a CONSTANT. "Revenue maps to concepts containing Revenue" is as stable as "USD is a currency." It doesn't change when you add companies, assets, or extraction types.

---

## Appendix A: Raw Concept Cache Data

### CRM Concept Cache — EffectiveIncomeTaxRate Group (queried 2026-03-09)

```json
[
  {"qname": "us-gaap:EffectiveIncomeTaxRateReconciliationShareBasedCompensationExcessTaxBenefitAmount",
   "label": "Effective Income Tax Rate Reconciliation, Tax Expense (Benefit), Share-Based Payment Arrangement, Amount",
   "usage": 3},
  {"qname": "us-gaap:EffectiveIncomeTaxRateReconciliationFdiiAmount",
   "label": "Effective Income Tax Rate Reconciliation, FDII, Amount",
   "usage": 3},
  {"qname": "us-gaap:EffectiveIncomeTaxRateContinuingOperations",
   "label": "Effective Income Tax Rate Reconciliation, Percent",
   "usage": 2}
]
```

### CRM Concept Cache — Revenue Group (queried 2026-03-09)

```json
[
  {"qname": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
   "label": "Revenue from Contract with Customer, Excluding Assessed Tax",
   "usage": 5},
  {"qname": "us-gaap:RevenueRemainingPerformanceObligation",
   "label": "Revenue, Remaining Performance Obligation, Amount",
   "usage": 4},
  {"qname": "crm:RevenueRemainingPerformanceObligationNoncurrent",
   "label": "Revenue, Remaining Performance Obligation, Noncurrent",
   "usage": 4},
  {"qname": "crm:RevenueRemainingPerformanceObligationCurrent",
   "label": "Revenue, Remaining Performance Obligation, Current",
   "usage": 4}
]
```

### Concept Node Existence (queried 2026-03-09)

All 4 target concepts exist as Concept nodes in the graph:
- `us-gaap:EffectiveIncomeTaxRateContinuingOperations` ✓
- `us-gaap:PaymentsForRestructuring` ✓ (exists in graph, but NOT in CRM's concept cache — CRM doesn't use it)
- `us-gaap:RestructuringCharges` ✓
- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` ✓

---

## Appendix B: Concept Cache Queries (Reference)

### Query 2A — Concept Usage Cache (`queries-common.md:102-118`)

```cypher
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE rk.formType = '10-K'
WITH c, rk ORDER BY rk.created DESC LIMIT 1
WITH c, rk.created AS last_10k_date
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q']
  AND r.created >= last_10k_date
  AND f.is_numeric = '1'
  AND (ctx.member_u_ids IS NULL OR ctx.member_u_ids = [])
WITH con.qname AS qname, con.label AS label, count(f) AS usage
ORDER BY usage DESC
RETURN qname, label, usage
```

Scope: Consolidated numeric facts from most recent 10-K + subsequent 10-Qs.
Output: `/tmp/concept_cache_{TICKER}.json` (~160 concepts for CRM, ~180 for AAPL).

### Query 2B — Member Profile Cache (`queries-common.md:127-177`)

```cypher
MATCH (ctx:Context)-[:FOR_COMPANY]->(c:Company {ticker: $ticker})
WHERE size(ctx.dimension_u_ids) > 0 AND size(ctx.member_u_ids) > 0
UNWIND range(0, size(ctx.member_u_ids)-1) AS i
WITH ctx.dimension_u_ids[i] AS dim_u_id, ctx.member_u_ids[i] AS mem_u_id
WHERE dim_u_id IS NOT NULL AND mem_u_id IS NOT NULL
  AND (dim_u_id CONTAINS 'Axis' OR dim_u_id CONTAINS 'Segment'
       OR dim_u_id CONTAINS 'Product' OR dim_u_id CONTAINS 'Geography'
       OR dim_u_id CONTAINS 'Region')
WITH DISTINCT dim_u_id, mem_u_id
-- CIK padding normalization
WITH dim_u_id, mem_u_id,
     split(mem_u_id, ':')[0] AS mem_cik_raw
WITH dim_u_id, mem_u_id,
     CASE WHEN mem_cik_raw =~ '^[0-9]+$'
          THEN toString(toInteger(mem_cik_raw)) + substring(mem_u_id, size(mem_cik_raw))
          ELSE mem_u_id END AS mem_u_id_nopad
MATCH (m:Member)
WHERE m.u_id = mem_u_id OR m.u_id = mem_u_id_nopad
WITH m.qname AS member_qname, m.u_id AS member_u_id, m.label AS member_label,
     dim_u_id, split(dim_u_id, ':') AS dim_parts, count(*) AS usage
WITH member_qname, member_u_id, member_label,
     dim_u_id AS axis_u_id,
     dim_parts[size(dim_parts)-2] + ':' + dim_parts[size(dim_parts)-1] AS axis_qname,
     usage
ORDER BY member_qname, usage DESC
WITH member_qname, collect({member_u_id: member_u_id, member_label: member_label,
     axis_qname: axis_qname, axis_u_id: axis_u_id, usage: usage}) AS versions
RETURN member_qname, versions[0].member_u_id AS best_member_u_id,
       versions[0].member_label AS best_member_label,
       versions[0].axis_qname AS best_axis_qname,
       versions[0].axis_u_id AS best_axis_u_id,
       versions[0].usage AS best_usage,
       reduce(total = 0, v IN versions | total + v.usage) AS total_usage
```

---

*Analysis completed 2026-03-09. All data queried live from production Neo4j. All claims verified against actual GuidanceUpdate nodes.*

---

## 11. Addendum — E4d and Member-Linking Alternatives

This section is intentionally additive. The earlier sections are kept as written for historical traceability. The items below record later repo-fit corrections discovered while comparing this plan against E4d, the current extraction docs, and the already-implemented member-linking fix.

### 11.1. What Is Definitively True

1. **E4d is still open for agent-side member-cache reading.**

   `extraction-pipeline-reference.md` records:

   - CRM member cache = 143 members / 52.6 KB
   - `warmup_cache.sh` writes correctly
   - the agent's `Read` hits the threshold on both passes
   - proposed recovery is still only "Bash-based reading or split into per-axis files"

   This means prompt-owned "scan the member cache and match segments" remains operationally unreliable for larger tickers.

2. **Actual write-mode member linking already bypasses that agent-side failure.**

   The current authoritative write path in `guidance_write_cli.py` does **not** depend on the agent successfully reading `/tmp/member_cache_{TICKER}.json`.

   Instead, in write mode it:

   - queries all `Member` nodes for the company by CIK prefix
   - normalizes member labels and segment text in Python
   - overwrites agent-provided `member_u_ids`

   So E4d is real, but it is primarily a prompt/runtime/dry-run problem, not the current write-path authority.

3. **The extraction docs still describe the weaker agent-owned member path.**

   `primary-pass.md` still says:

   - scan the member cache from Step 1
   - match the segment name
   - add matched `u_id` to `member_u_ids`

   Therefore the statement in Section 6 that this plan needs "No prompt changes required" is only true for the concept-resolver part. It is **not** true for a full member-linking cleanup.

4. **Issue #61 already documented why 2B-only member lookup is insufficient.**

   `done_fixes/guidance-extraction-issues.md` records that:

   - NTAP/IBM exposed LLM member-matching unreliability
   - IBM `RedHatMember` was absent from the 2B cache because it had 0 XBRL facts
   - the fix was to query **all** Members by CIK prefix directly, not the context-filtered 2B cache
   - this was verified across AAPL / IBM / NTAP

   This matters because any redesign that moves member authority back to "2B-style cache only" risks reintroducing an already-fixed regression.

5. **E4c is also open, but it is a different class of problem.**

   `extraction-pipeline-reference.md` records that 10-K MD&A content can exceed the same output ceiling and that the agent currently recovers with Bash. The suggested durable fix is to extend `warmup_cache.py` so the large filing content is pre-split or pre-fetched in a more retrieval-friendly form.

   This should be treated as:

   - a source-content loading/runtime issue
   - partially recoverable today
   - worth fixing for extraction ergonomics and cost

   But it is **not** the same as the E4d member-authority problem. E4c does not argue for or against code-owned member linking; it is orthogonal.

### 11.2. Recommended Alternative (Repo-Fit, Recommended)

If the goal is to keep the strongest parts of this plan while correcting the E4d/member-linking gap, the recommended alternative is:

1. **Keep the deterministic concept resolver proposed in Sections 5-7.**

   The concept problem is real, isolated, and can be fixed with the warmup-built registry map described above.

2. **Keep member linking code-owned in `guidance_write_cli.py`.**

   Do **not** make prompt-owned member matching authoritative.

   Preferred authority remains:

   - all-company member lookup by CIK prefix
   - Python normalization
   - overwrite of agent-provided `member_u_ids`

3. **Do not revert member authority to 2B-only cache matching.**

   Query 2B is still useful as a profile/cache, but it should not be the only source of truth for final member resolution.

4. **Update extraction docs so the agent's role is advisory only for members.**

   Two acceptable variants:

   - **Preferred**: agent extracts only segment text; CLI owns final member resolution
   - **Fallback**: agent may still attempt member matches from cache, but CLI is the authority and may overwrite them

5. **If dry-run parity matters, extend the code-owned member path instead of relying on large cache reads.**

   Practical options:

   - allow the same member-resolution code path in dry-run when Neo4j is available
   - or make warmup emit smaller per-axis member files for agent ergonomics

   The first option is cleaner because it removes the E4d dependency entirely for member resolution.

6. **Keep the existing graph contract for now.**

   That means:

   - keep `member_u_ids`
   - keep `MAPS_TO_MEMBER`
   - keep `xbrl_qname`
   - keep `MAPS_TO_CONCEPT`

   A broader stable-identity redesign can be evaluated later, but it is a different scope from the concept-resolver fix.

### 11.3. Why This Alternative May Be Better

- It fixes the actual open operational gap exposed by E4d instead of assuming the agent can always read large member caches.
- It aligns with the current authoritative code path already implemented in `guidance_write_cli.py`.
- It avoids undoing Issue #61's fix by keeping all-members-by-CIK lookup as the final authority.
- It preserves the low-risk concept resolver from this document without forcing a schema or contract redesign.

### 11.4. Why This Alternative May Not Be Better

- If the real product requirement is "store only exact, stable business identities and never treat node edges as truth," then a broader redesign may still be preferable.
- A stricter future design could separate:
  - exact concept/member identity
  - derived edge/materialized node link for convenience

  That is a larger architectural change than the implementation plan in this file.

### 11.5. Decision Guidance

For the current repo, the best implementation sequence is:

1. implement the deterministic concept resolver from this document
2. explicitly document that member linking is code-owned, not prompt-owned
3. preserve all-members-by-CIK member resolution as the final authority
4. treat broader "stable identity" redesign ideas as a separate follow-up, not part of the minimal fix

---

## 12. Implementation Record — What Was Actually Built (2026-03-10)

This section documents what was implemented, the validation evidence, and what was intentionally **not** changed.

### 12.1. Implementation Summary

GPT (o3) implemented a **conservative exact local-name concept resolver** rather than the broader substring-based registry proposed in Sections 5-7 of this plan. The implementation was reviewed and validated by Claude (Opus 4.6) on 2026-03-10.

**Approach**: Exact XBRL local-name matching against an ordered candidate list per label_slug.

**Files created/modified**:

| File | Action | Purpose |
|------|--------|---------|
| `scripts/concept_resolver.py` | NEW (184 lines) | Deterministic concept resolver with reviewed candidate lists |
| `scripts/test_concept_resolver.py` | NEW (137 lines) | 10 unit tests covering all resolution paths |
| `scripts/guidance_write_cli.py` | MODIFIED | Import + call `apply_concept_resolution()` before inheritance; inheritance keys changed from `label` to `label_slug` |

**No files changed for member linking.** Member resolution remains code-owned in `guidance_write_cli.py:232-268`.

### 12.2. How the Concept Resolver Works

`concept_resolver.py` uses three data structures:

1. **`CONCEPT_CANDIDATES`** — dict mapping label_slug → ordered tuple of XBRL local names. First match in the company's concept cache wins.

   ```python
   CONCEPT_CANDIDATES = {
       'dividend_per_share': ('CommonStockDividendsPerShareDeclared',),
       'eps': ('EarningsPerShareDiluted',),
       'gross_margin': ('GrossProfit',),
       'gross_profit': ('GrossProfit',),
       'oine': ('NonoperatingIncomeExpense', 'OtherNonoperatingIncomeExpense'),
       'operating_expenses': ('OperatingExpenses',),
       'opex': ('OperatingExpenses',),
       'restructuring_cash_payments': ('PaymentsForRestructuring',),
       'restructuring_charges': ('RestructuringCharges',),
       'restructuring_costs': ('RestructuringCharges',),
       'revenue': ('RevenueFromContractWithCustomerExcludingAssessedTax',
                   'RevenueFromContractWithCustomerIncludingAssessedTax',
                   'SalesRevenueNet', 'Revenues'),
       'tax_rate': ('EffectiveIncomeTaxRateContinuingOperations',
                    'EffectiveIncomeTaxRate'),
   }
   ```

2. **`NULL_QNAME_LABELS`** — set of labels that should always resolve to null (derived metrics with no XBRL concept): `adjusted_ebitda`, `ebitda`, `fcf`, `free_cash_flow`, `operating_margin`.

3. **`NULL_QNAME_SUFFIXES`** — tuple of suffixes that should always resolve to null: `_change`, `_growth`, `_yoy`.

**Resolution logic** (`resolve_xbrl_qname()`):
- If label_slug is null → `UNHANDLED_CONCEPT` (passthrough)
- If label_slug is in `NULL_QNAME_LABELS` or ends with `NULL_QNAME_SUFFIXES` → `FORCE_NULL_CONCEPT`
- If label_slug has no entry in `CONCEPT_CANDIDATES` → `UNHANDLED_CONCEPT` (passthrough — unknown labels are not touched)
- Otherwise: iterate candidates in order, strip namespace prefix from cache rows, exact local-name match. Usage tiebreak if multiple namespace hits for the same local name; fail-closed (return None) on usage ties.

**Application logic** (`apply_concept_resolution()`):
- `UNHANDLED_CONCEPT` → skip (preserve whatever the agent provided)
- `FORCE_NULL_CONCEPT` → set `xbrl_qname = None`
- Resolved qname + existing qname is missing/invalid → set to resolved
- Resolved qname + existing qname is valid (present in cache) → keep existing (with log warning if different)

### 12.3. Integration Point in guidance_write_cli.py

Concept resolution runs **before** inheritance, at approximately line 207:

```python
concept_rows = load_concept_cache(ticker)
apply_concept_resolution(valid_items, concept_rows, logger=logger)
```

Inheritance was also improved: keys changed from raw `item['label']` to `label_slug` via `item.get('label_slug') or slug(item.get('label', ''))`. This is strictly better — normalizes "Tax Rate" and "tax rate" to the same key.

### 12.4. Validation Evidence — 762-Company Replay

GPT ran a full audit across all 762 companies in the database:

| Metric | Result |
|--------|--------|
| Companies tested | 762 |
| Off-target matches (exact local-name) | **0** |
| Recall fixes confirmed | **3** (CRM tax_rate ×2, AAPL gross_margin ×1) |
| Existing correct links preserved | All |
| Existing correct nulls preserved | All |

### 12.5. Why the Broader Substring Registry (Sections 5-7) Was NOT Implemented

This plan's Sections 5-7 proposed a substring include/exclude pattern registry with ~20 entries:

```python
# Example from plan Section 5 (NOT implemented):
'revenue': (['RevenueFromContract', 'SalesRevenueNet', 'Revenues'], ['Remaining', 'Recognized']),
'tax_rate': (['EffectiveIncomeTaxRate'], ['Reconciliation']),
```

GPT ran the same 762-company replay against this broader registry and found **920+ off-target matches**:

| Label | Off-target hits | Example false match |
|-------|----------------|---------------------|
| revenue | 159 | Matches any qname containing "RevenueFromContract" including performance obligations |
| sbc | 380 | Matches any qname containing "ShareBased" including reconciliation items |
| d_a | 152 | Matches "Depreciation" broadly — hits accumulated depreciation, tax depreciation |
| interest_expense | 105 | Matches broadly across interest-related concepts |
| restructuring_costs | 51 | Matches restructuring reserve and liability concepts |
| opex | 33 | Matches operating-expense subtypes |
| crpo | 23 | Matches remaining performance obligation variants |
| net_income | 17 | Matches net income attributable-to subtypes |

**Root cause**: Substring matching (`candidate in qname`) is inherently fuzzy. XBRL taxonomies reuse stems extensively — "RevenueFromContract" appears in revenue concepts, performance obligations, contract liabilities, and deferred revenue. An exclude list can never be exhaustive because new taxonomy extensions and company-specific concepts appear regularly.

The exact local-name approach has **zero** false matches by construction — it only matches the exact concept names that have been reviewed against live data.

### 12.6. Discrepancies Between Plan and Implementation

The plan's Section 5 pattern map and `core-contract.md` §11 pattern map both have discrepancies vs the implemented resolver:

| Issue | Plan/Contract | Implementation | Notes |
|-------|--------------|----------------|-------|
| tax_rate exclude | No exclude for Reconciliation items | N/A — exact match on `EffectiveIncomeTaxRateContinuingOperations` only | Plan's substring match would need an exclude; exact match doesn't |
| OINE pattern | Plan uses substring `NonoperatingIncome` | Exact: `NonoperatingIncomeExpense`, `OtherNonoperatingIncomeExpense` | Plan would match `NonoperatingIncomeExpenseOther` variants too |
| sbc, d_a, interest_expense, net_income | In plan's registry | **Not in implementation** | Deliberately excluded — no evidence of recall failures for these labels. Adding them risks false matches without measurable benefit |

**`core-contract.md` §11 has NOT been updated** to match the implementation. The §11 pattern map (12 entries with include/exclude substrings) is now superseded by `concept_resolver.py`'s exact local-name candidates. A future update should align §11 with the actual implementation, but the runtime behavior is correct because the CLI runs the resolver, not the §11 spec.

### 12.7. Member Linking Decision — No Changes

**What was analyzed**:

1. **`&` vs `and` normalization gap** in `guidance_ids.py:normalize_for_member_match()`:
   - `normalize_for_member_match("Research & Development")` → `researchdevelopment`
   - `normalize_for_member_match("ResearchAndDevelopmentMember")` → `researchanddevelopment`
   - These don't match because `&` is stripped but `and` is preserved.
   - CRM has a `SubscriptionandSupport` member label — confirming the latent case is real for at least one company.

2. **Impact assessment** (GPT, verified across 84,166 distinct member labels):
   - The `&` vs `and` gap has **zero measurable impact** on current production data.
   - CRM has 0 segmented guidance items (no member matches attempted).
   - AAPL's segments (iPhone, iPad, Mac, Services, Wearables) don't contain `&` or `and`.
   - No production item was found where this gap caused a missed member link.
   - Claude's earlier proposal included camelCase word-boundary splitting (e.g., `GrossProfit` → `gross profit`). GPT checked: across all 84,166 distinct member labels, camelCase splitting produced **0 behavioral differences** vs `&`-only normalization. It is a no-op in practice.

3. **Decision**: Do NOT change `normalize_for_member_match()` now. The only behavior-changing normalization worth considering in the future is a minimal `& -> and` substitution — not camelCase splitting or other broader changes. Even `& -> and` has zero current impact and should only be added when a real production case surfaces.

**Member linking remains**:
- Code-owned in `guidance_write_cli.py:232-268`
- Final authority via all-Members-by-CIK query (not 2B cache)
- Agent-provided `member_u_ids` are advisory only — CLI overwrites
- 100% precision and recall on current data (AAPL's 5 segments all correct)

### 12.8. What Changed vs What Didn't

| Component | Changed? | Details |
|-----------|----------|---------|
| `concept_resolver.py` | **NEW** | Exact local-name concept resolution for 12 reviewed label_slugs |
| `test_concept_resolver.py` | **NEW** | 10 unit tests |
| `guidance_write_cli.py` | **MODIFIED** | Calls resolver before inheritance; inheritance uses label_slug keys |
| `guidance_writer.py` | No | MAPS_TO_CONCEPT / MAPS_TO_MEMBER edge creation unchanged |
| `guidance_ids.py` | **MODIFIED** | `normalize_for_member_match()`: added `& -> and` substitution (1 line, zero current impact, future recall hardening) |
| `warmup_cache.py` | No | Query 2A/2B unchanged |
| `core-contract.md` §11 | No | Still has old substring patterns — superseded at runtime by resolver |
| Member linking code | No | Remains code-owned, all-Members-by-CIK, CLI authoritative |
| Graph schema | No | Same nodes, edges, properties |

### 12.9. Open Items

1. **Align `core-contract.md` §11 with implementation** — the agent still reads §11 during extraction, which describes the old substring approach. The CLI resolver overrides agent mistakes, but aligning the spec would reduce wasted agent effort.

2. **Expanding `CONCEPT_CANDIDATES` — Acceptance Bar & Process**

   The resolver is deliberately narrow (12 entries covering all 16 production label_slugs). Expansion is expected as more companies are extracted, but each new entry must pass a strict gate.

   **Acceptance bar (ALL must pass before promotion to code):**
   - Exact local-name candidates ONLY — no substring, no prefix matching
   - Full replay across all 762 company concept caches (Query 2A simulation)
   - **0 off-target selections** across the entire replay
   - **Semantic equivalence** — the candidate must mean the same thing as the label_slug, not merely be related. Examples of failures:
     - `AllocatedShareBasedCompensationExpense` ≠ generic SBC (it's the IS allocation, not the CF add-back)
     - `InterestIncomeExpenseNet` ≠ `interest_expense` (net includes income offset)
     - `WeightedAverageNumberOfDilutedSharesOutstanding` ≠ generic `share_count` (diluted-only)
   - No rewrites of already-valid current links
   - Measurable recall improvement on current or expected labels

   **Process:**
   1. Inventory: identify uncovered label_slugs (from GuidanceUpdate nodes or anticipated labels)
   2. Evidence table: candidate concepts per slug with company-count data
   3. Replay report: validate across all 762 company caches
   4. Propose: only slugs that pass the full acceptance bar

   **Slug naming must match `guidance_ids.slug()` output** — e.g., `slug("SG&A")` == `sg_a`, not `sga`. Verify against the actual slug function before adding entries.

   **Do NOT bulk-promote.** Presence counts (how many companies have a concept) are not correctness proofs. Each candidate needs individual semantic review.

   **The registry is living, not finished** — future companies can use custom extension concepts, new labels, or derived metrics that should stay null. Runtime behavior is always company-specific (resolution only works if that candidate exists in that company's cache).

3. ~~**Future low-risk hardening: `& -> and`**~~ **DONE (2026-03-10)** — Applied `s.lower().replace('&', 'and')` in `normalize_for_member_match()` at `guidance_ids.py:200`. Verified: 78/78 tests pass, 0 collision changes across 84,166 member labels, 0 current production impact. Future-facing: recovers matches like CRM's `Subscription & Support` → `SubscriptionandSupport`. CamelCase splitting NOT added — verified as no-op.

4. **E9 tracker status**: RESOLVED by concept_resolver.py. The 3 recall failures (CRM tax_rate ×2, AAPL gross_margin ×1) are now deterministically filled. Enhancement #23 (inline concept resolver) is COMPLETE.

5. **Do NOT expand member linking to a static dict** — member linking remains company-scoped code-owned lookup with normalization in `guidance_write_cli.py`. A universal static dict (like CONCEPT_CANDIDATES) is the wrong architecture for members because member labels are company-specific, not taxonomy-standardized.
