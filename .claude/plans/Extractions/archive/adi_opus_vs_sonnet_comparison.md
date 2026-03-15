# ADI Opus vs Sonnet Comparison — Full Pipeline (Orchestrator + Primary + Enrichment)

**Date:** 2026-03-15
**Source:** ADI_2026-02-18T10.00 (Q1 FY2026 earnings transcript)
**ADI Fiscal Year End:** October 31

| Config | Sonnet Run | Opus Run |
|--------|-----------|----------|
| Orchestrator | Sonnet 4.6 | Opus 4.6 |
| Primary Agent | Sonnet 4.6 | Opus 4.6 |
| Enrichment Agent | Sonnet 4.6 | Opus 4.6 |
| Extraction time | ~5 min | ~8 min |
| Items written | 16 | 16 |

---

## CRITICAL FINDING: Period Dates OFF BY 1 MONTH (Opus)

ADI's fiscal year ends **October 31**. FY2026 = Nov 1 2025 – Oct 31 2026.

| Period | Sonnet (CORRECT) | Opus (WRONG) | Error |
|--------|-----------------|--------------|-------|
| FY2026 annual | `gp_2025-11-01_2026-10-31` | `gp_2025-12-01_2026-11-30` | +1 month |
| Q2 FY2026 | `gp_2026-02-01_2026-04-30` | `gp_2026-03-01_2026-05-31` | +1 month |
| H2 FY2026 | `gp_2026-05-01_2026-10-31` | (item dropped) | — |
| Data Center long-range | `gp_2025-11-01_2028-10-31` | `gp_MT` (sentinel) | Different approach |

**This is the same bug reported in the prior Opus test.** Opus consistently adds 1 month to ADI fiscal period boundaries. This makes ALL period-based IDs different between Sonnet and Opus, preventing MERGE deduplication.

---

## Item Inventory: 16 vs 16 but Different Composition

### Items in BOTH (14 matched by concept, not by ID due to period bug)

| # | Metric | Segment | Period Scope | Sonnet label_slug | Opus label_slug | Slug Match? |
|---|--------|---------|-------------|-------------------|-----------------|-------------|
| 1 | CapEx | Total | annual | capex | capex | YES |
| 2 | EPS | Total | quarter | eps | eps | YES |
| 3 | Gross Margin | Total | quarter | gross_margin | gross_margin | YES |
| 4 | Operating Margin | Total | quarter | operating_margin | operating_margin | YES |
| 5 | OpEx (FY) | Total | annual | **opex** | **opex_growth** | NO |
| 6 | OpEx (Q2) | Total | quarter | **opex** | **opex_growth** | NO |
| 7 | Revenue | Automotive | annual | revenue | revenue | YES |
| 8 | Revenue | Automotive | quarter | revenue | revenue | YES |
| 9 | Revenue | Communications | quarter | revenue | revenue | YES |
| 10 | Revenue | Consumer | quarter | revenue | revenue | YES |
| 11 | Revenue | Industrial | quarter | revenue | revenue | YES |
| 12 | Revenue | Total | quarter | revenue | revenue | YES |
| 13 | Revenue | Data Center | long_range | revenue | revenue | YES |
| 14 | Tax Rate | Total | quarter | tax_rate | tax_rate | YES |

### Items ONLY in Sonnet (2 dropped by Opus)

| # | gu.id | Metric | Why it matters |
|---|-------|--------|----------------|
| 15 | `gu:...:revenue:gp_2026-02-01_2026-04-30:unknown:ate` | Revenue ATE (Q2) | Subsegment of Industrial — >30% seq growth |
| 16 | `gu:...:revenue:gp_2026-05-01_2026-10-31:unknown:automotive` | Revenue Automotive (H2) | H2 stronger than H1 outlook |

### Items ONLY in Opus (2 new)

| # | gu.id | Metric | Why it matters |
|---|-------|--------|----------------|
| 15 | `gu:...:dividend_per_share:gp_2026-03-01_2026-05-31:unknown:total` | Dividend Per Share $1.10 | Quarterly dividend (arguably corporate action, not guidance) |
| 16 | `gu:...:free_cash_flow_return:gp_LT:unknown:total` | Free Cash Flow Return 100% | Long-term capital return target (arguably policy, not guidance) |

**Assessment:** Sonnet's 2 dropped items (ATE subsegment, H2 outlook) are both **genuine forward-looking guidance** from Q&A. Opus's 2 new items (dividend declaration, FCF return policy) are **borderline** — dividends were explicitly excluded by design decision D11 ("corporate announcements EXCLUDED... Dividend guidance IS extractable" but this is a declaration, not forward guidance), and the FCF return target is a standing policy, not new guidance.

---

## Property-by-Property Comparison (Matched Items)

### Item 1: CapEx

| Property | Sonnet | Opus | Match? |
|----------|--------|------|--------|
| gu.id | `gu:...:capex:gp_2025-11-01_2026-10-31:unknown:total` | `gu:...:capex:gp_2025-12-01_2026-11-30:unknown:total` | **NO** (period) |
| low/mid/high | 4.0 / 5.0 / 6.0 | 4 / 5.0 / 6 | YES |
| canonical_unit | **unknown** | **percent** | Opus better |
| unit_raw | "% of revenue" | null | Sonnet kept raw |
| basis_norm | unknown | unknown | YES |
| derivation | explicit | explicit | YES |
| fiscal_year | 2026 | 2026 | YES |
| section | CFO Prepared Remarks | CFO Prepared Remarks | YES |
| conditions | null | "within our long-term model" | Opus added |
| qualitative | null | "4% to 6% of revenue" | Opus added |
| quote | identical text | identical text | YES |
| evhash16 | 3e53c1c3c349c3e4 | 9d17aa8c0eca31ca | NO (different properties) |
| MAPS_TO_CONCEPT | PaymentsToAcquire... | PaymentsToAcquire... | YES |
| MAPS_TO_MEMBER | null | null | YES |

### Item 2: EPS

| Property | Sonnet | Opus | Match? |
|----------|--------|------|--------|
| gu.id | `...:eps:gp_2026-02-01_2026-04-30:non_gaap:total` | `...:eps:gp_2026-03-01_2026-05-31:non_gaap:total` | **NO** (period) |
| low/mid/high | 2.73 / 2.88 / 3.03 | 2.73 / 2.88 / 3.03 | YES |
| canonical_unit | usd | usd | YES |
| basis_norm | non_gaap | non_gaap | YES |
| basis_raw | adjusted | adjusted | YES |
| derivation | explicit | explicit | YES |
| conditions | null | null | YES |
| quote | "[PR] Adjusted EPS is expected to be $2.88 plus or minus 15 cents." | "[PR] And based on these inputs, adjusted EPS is expected to be $2.88 plus or minus 15 cents." | Opus slightly longer |
| evhash16 | 3f1730f9c93745ee | 3f1730f9c93745ee | **YES** (same!) |
| MAPS_TO_CONCEPT | EarningsPerShareDiluted | EarningsPerShareDiluted | YES |

### Item 3: Gross Margin

| Property | Sonnet | Opus | Match? |
|----------|--------|------|--------|
| gu.id | `...:gross_margin:...:non_gaap:total` | `...:gross_margin:...:unknown:total` | **NO** (basis_norm + period) |
| basis_norm | **non_gaap** | **unknown** | Sonnet better (Q&A context made it clear) |
| basis_raw | non-GAAP | null | Sonnet captured |
| derivation | **implied** | **comparative** | Different classification |
| source_refs | [qa__1] | [qa__1, qa__2] | Opus merged 2 Q&A refs |
| conditions | Sonnet: "Driven by favorable mix and price uplift; includes 50 bps one-time..." | Opus: "Includes 50 bps from one-time channel inventory repricing...nearing optimal utilization level" | Both rich, different emphasis |
| qualitative | "+100 bps sequential expansion (or +150 bps excluding discrete Q1 items)" | "Q2 expects 100 bps of gross margin expansion on a reported basis, or 150 bps normalized excluding Q1 discrete items..." | Opus more verbose |
| MAPS_TO_CONCEPT | GrossProfit | GrossProfit | YES |

### Item 4: Operating Margin

| Property | Sonnet | Opus | Match? |
|----------|--------|------|--------|
| low/mid/high | 46.5 / 47.5 / 48.5 | 46.5 / 47.5 / 48.5 | YES |
| canonical_unit | percent | percent | YES |
| basis_raw | non-GAAP | null | Sonnet captured |
| source_refs | [pr] | **[pr, qa__1]** | Opus enriched |
| section | "CFO Prepared Remarks" | "CFO Prepared Remarks + Q&A #1 (Stacy Raskin)" | Opus richer |
| conditions | **null** | **"200 bps sequential improvement driven by gross margin expansion and OpEx leverage..."** | Opus MUCH richer |
| quote | 1 sentence (PR only) | 2 sentences (PR + Q&A) | Opus richer |
| MAPS_TO_CONCEPT | none | none | YES (both missing) |

### Item 5 & 6: OpEx / OpEx Growth

| Property | Sonnet | Opus | Match? |
|----------|--------|------|--------|
| label_slug | **opex** | **opex_growth** | **NO** (different Guidance node!) |
| label | OpEx | OpEx Growth | NO |
| Guidance node | guidance:opex | guidance:opex_growth | **NO** |
| xbrl_qname | us-gaap:OperatingExpenses | null | Sonnet had XBRL |
| MAPS_TO_CONCEPT | **OperatingExpenses** | **none** | Sonnet better |
| All other fields | Similar qualitative content | Similar qualitative content | ~YES |

### Item 14: Revenue Total (Q2)

| Property | Sonnet | Opus | Match? |
|----------|--------|------|--------|
| low/mid/high | 3400 / 3500 / 3600 | 3400 / 3500 / 3600 | YES |
| canonical_unit | m_usd | m_usd | YES |
| source_refs | [pr, qa__0, qa__11] | [pr, qa__11] | Sonnet captured more |
| section | "CFO Prepared Remarks + Q&A #0 + Q&A #11" | "CFO Prepared Remarks + Q&A #11" | Sonnet broader |
| conditions | Both very rich with pricing decomposition | Opus adds "expects ~50 bps incremental growth in each of Q3 and Q4 from price" | Opus adds forward quarters |
| MAPS_TO_CONCEPT | RevenueFromContract... | RevenueFromContract... | YES |

### Item 16: Tax Rate

| Property | Sonnet | Opus | Match? |
|----------|--------|------|--------|
| low/mid/high | 11 / 12 / 13 | 11 / 12 / 13 | YES |
| canonical_unit | percent | percent | YES |
| basis_raw | non-GAAP | null | Sonnet captured |
| evhash16 | e685cdb85d494810 | e685cdb85d494810 | **YES** (identical!) |
| MAPS_TO_CONCEPT | none | none | YES (both missing) |

---

## XBRL Linking Summary

| Metric | Sonnet MAPS_TO_CONCEPT | Opus MAPS_TO_CONCEPT | Match? |
|--------|----------------------|---------------------|--------|
| CapEx | PaymentsToAcquire... | PaymentsToAcquire... | YES |
| EPS | EarningsPerShareDiluted | EarningsPerShareDiluted | YES |
| Gross Margin | GrossProfit | GrossProfit | YES |
| Operating Margin | none | none | YES |
| OpEx/OpEx Growth (FY) | **OperatingExpenses** | **none** | Sonnet better |
| OpEx/OpEx Growth (Q2) | **OperatingExpenses** | **none** | Sonnet better |
| Revenue (all segments) | RevenueFromContract... | RevenueFromContract... | YES |
| Revenue Data Center | RevenueFromContract... | RevenueFromContract... | YES |
| Revenue ATE | RevenueFromContract... | (item dropped) | — |
| Revenue Auto H2 | RevenueFromContract... | (item dropped) | — |
| Tax Rate | none | none | YES |
| Dividend Per Share | (item absent) | **CommonStockDividendsPerShareDeclared** | Opus NEW |
| Free Cash Flow Return | (item absent) | **none** | — |

**Sonnet: 14/16 MAPS_TO_CONCEPT (88%)**
**Opus: 10/16 MAPS_TO_CONCEPT (63%)**

## MAPS_TO_MEMBER Summary

| Segment | Sonnet | Opus | Match? |
|---------|--------|------|--------|
| Automotive (FY) | AutomotiveMember | AutomotiveMember | YES |
| Automotive (Q2) | AutomotiveMember | AutomotiveMember | YES |
| Communications (Q2) | CommunicationsMember | CommunicationsMember | YES |
| Consumer (Q2) | ConsumerMember | ConsumerMember | YES |
| Industrial (Q2) | IndustrialMember | IndustrialMember | YES |
| Automotive (H2) | AutomotiveMember | (item dropped) | — |

**Sonnet: 6/16 MAPS_TO_MEMBER (38%)**
**Opus: 5/16 MAPS_TO_MEMBER (31%)**

---

## Quantitative Summary

| Dimension | Sonnet 4.6 | Opus 4.6 | Winner |
|-----------|-----------|----------|--------|
| Total items | 16 | 16 | Tie |
| **Period accuracy** | **CORRECT** (Nov 1 – Oct 31) | **WRONG** (+1 month) | **Sonnet** |
| Genuine guidance items | **16/16** | **14/16** (2 borderline) | **Sonnet** |
| Subsegment depth | **ATE + H2 auto** | dropped both | **Sonnet** |
| MAPS_TO_CONCEPT | **14/16 (88%)** | 10/16 (63%) | **Sonnet** |
| MAPS_TO_MEMBER | **6/16 (38%)** | 5/16 (31%) | **Sonnet** |
| Numeric accuracy | Correct | Correct | Tie |
| basis_raw captured | **4/16** (non-GAAP on 4 items) | 1/16 (adjusted on EPS only) | **Sonnet** |
| label_slug consistency | `opex` (standard) | `opex_growth` (nonstandard) | **Sonnet** |
| Conditions richness | Mixed | Operating Margin MUCH richer | **Opus** |
| Cross-Q&A enrichment | Good | Operating Margin enriched from Q&A | **Opus** (slight) |
| New metrics discovered | 0 | 2 (dividend, FCF return) | Opus (debatable quality) |
| Extraction time | ~5 min | ~8 min | **Sonnet** |

---

## Verdict

**Sonnet 4.6 remains the clear winner for guidance extraction.**

### Sonnet advantages (deal-breakers):
1. **Correct fiscal periods** — Opus is off by 1 month on EVERY period, making all IDs wrong and preventing cross-source deduplication
2. **Better XBRL linking** — 88% vs 63% concept coverage
3. **Better label consistency** — `opex` is the standard label; `opex_growth` creates a separate Guidance node
4. **More genuine items** — ATE subsegment and H2 automotive outlook are real guidance; Opus's dividend declaration and FCF return policy are borderline

### Opus advantages (nice-to-have):
1. **Richer conditions on operating margin** — pulled Q&A context into prepared remarks items
2. **canonical_unit: percent** on CapEx (Sonnet left as unknown)
3. **Discovered 2 new metrics** (though both are debatable as guidance)

### Recommendation:
Keep Sonnet 4.6 for all three roles (orchestrator + primary + enrichment). The period accuracy bug alone is disqualifying for Opus — it would create duplicate GuidancePeriod nodes and break cross-source matching.
