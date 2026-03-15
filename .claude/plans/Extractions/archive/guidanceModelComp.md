# Guidance Extraction Model Comparison

Date: 2026-03-14
Pipeline: extraction-worker v2.1.76 on K8s (processing namespace)
Orchestrator model: Opus 4.6 (spawns extraction agents)
Extraction agent model: varies per run (Haiku 4.5 → Sonnet 4.6 → Opus 4.6)

## Test Filings

| # | Ticker | Accession | Type | Guidance Content |
|---|---|---|---|---|
| 1 | PG | 0000080424-24-000110 | 7.01 investor presentation | RICH — FY2025: organic sales, net sales, 3x EPS bases, tax rate, FCF productivity, capex, dividends |
| 2 | DECK | 0000910521-25-000013 | 2.02 earnings press release | MODERATE — Q1 FY2026: revenue range, EPS range |
| 3 | NSC | 0001552781-23-000051 | 7.01 conference attendance | NONE — "CEO will attend Barclays conference" + Item 2.03 receivables facility |

---

## PG (0000080424-24-000110) — 7.01 Investor Presentation

### Item Count

| Model | Items Extracted |
|---|---|
| Haiku 4.5 | 9 |
| Sonnet 4.6 | 9 |
| Opus 4.6 | pending |

### Item 1: Capital Expenditure

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:capital_expenditure | guidance:capital_expenditure | pending |
| g.label | Capital Expenditure | Capital Expenditure | pending |
| gu.id | gu:0000080424-24-000110:capital_expenditure:gp_2024-07-01_2025-06-30:unknown:total | gu:0000080424-24-000110:capital_expenditure:gp_2024-07-01_2025-06-30:unknown:total | pending |
| gu.low | 4.0 | 4.0 | pending |
| gu.mid | 4.5 | 4.5 | pending |
| gu.high | 5.0 | 5.0 | pending |
| gu.canonical_unit | percent | percent | pending |
| gu.basis_norm | unknown | unknown | pending |
| gu.basis_raw | null | null | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | As percentage of sales; maintained from prior | % of Net Sales | pending |
| gu.quote | [8-K] Capital Spending, % of Sales (Maintain) 4-5% for fiscal 2025 | [8-K] FY 2025 Capital Spending, % Sales (Maintain) 4-5%. | pending |
| gu.evhash16 | 78cce9e960444b5a | a585ddbac5939080 | pending |
| gu.xbrl_qname | **null** | **us-gaap:PaymentsToAcquirePropertyPlantAndEquipment** | pending |
| gu.concept_family_qname | **null** | **us-gaap:PaymentsToAcquirePropertyPlantAndEquipment** | pending |
| MAPS_TO_CONCEPT | **none** | **none** | pending |
| HAS_MEMBER | **none** | **none** | pending |

**Delta:** Sonnet found XBRL concept (PaymentsToAcquirePropertyPlantAndEquipment). Haiku did not. Conditions and quote wording differ slightly. evhash16 differs (quote text changed).

### Item 2: Dividends

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:dividends | guidance:dividends | pending |
| g.label | Dividends | Dividends | pending |
| gu.id | gu:0000080424-24-000110:dividends:gp_2024-07-01_2025-06-30:unknown:total | gu:0000080424-24-000110:dividends:gp_2024-07-01_2025-06-30:unknown:total | pending |
| gu.low | 10000.0 | 10000.0 | pending |
| gu.mid | 10000.0 | 10000.0 | pending |
| gu.high | 10000.0 | 10000.0 | pending |
| gu.canonical_unit | m_usd | m_usd | pending |
| gu.basis_norm | unknown | unknown | pending |
| gu.basis_raw | null | null | pending |
| gu.derivation | point | point | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | Approximately $10 billion total dividends; maintained | Approximately $10 billion | pending |
| gu.quote | [8-K] Dividends (Maintain) ~$10bn for fiscal 2025 | [8-K] FY 2025 Dividends (Maintain) ~$10bn. | pending |
| gu.evhash16 | 40b2f3f202e62eef | 87f5f674604bea44 | pending |
| gu.xbrl_qname | **null** | **us-gaap:PaymentsOfDividends** | pending |
| gu.concept_family_qname | **null** | **us-gaap:PaymentsOfDividends** | pending |
| MAPS_TO_CONCEPT | **none** | **none** | pending |
| HAS_MEMBER | **none** | **none** | pending |

**Delta:** Sonnet found XBRL concept (PaymentsOfDividends). Haiku did not. Quote and conditions wording differ. evhash16 differs.

### Item 3: EPS (constant_currency basis)

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:eps | guidance:eps | pending |
| g.label | EPS | EPS | pending |
| gu.id | gu:0000080424-24-000110:eps:gp_2024-07-01_2025-06-30:constant_currency:total | gu:0000080424-24-000110:eps:gp_2024-07-01_2025-06-30:constant_currency:total | pending |
| gu.low | 5.0 | 5.0 | pending |
| gu.mid | 6.0 | 6.0 | pending |
| gu.high | 7.0 | 7.0 | pending |
| gu.canonical_unit | **percent** | **percent_yoy** | pending |
| gu.basis_norm | constant_currency | constant_currency | pending |
| gu.basis_raw | **core** | **Currency Neutral Core** | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | Currency-neutral core EPS growth; expects FX to be neutral | Expect foreign exchange to be neutral | pending |
| gu.quote | [8-K] Currency neutral core EPS growth of +5% to +7% for fiscal 2025 | [8-K] FY 2025 Currency Neutral Core EPS Growth +5% to +7%. Currency neutral core EPS growth of +5% to +7% (expect foreign exchange to be neutral). | pending |
| gu.evhash16 | 1aceb52544492f1c | 24e52e27905fb64f | pending |
| gu.xbrl_qname | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | pending |
| gu.concept_family_qname | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Sonnet used `percent_yoy` (more precise than `percent`). Sonnet's `basis_raw` is "Currency Neutral Core" vs Haiku's "core". Sonnet's quote is longer/more detailed. Conditions differ in wording.

### Item 4: EPS (gaap basis / All-in)

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:eps | guidance:eps | pending |
| g.label | EPS | EPS | pending |
| gu.id | gu:0000080424-24-000110:eps:gp_2024-07-01_2025-06-30:gaap:total | gu:0000080424-24-000110:eps:gp_2024-07-01_2025-06-30:gaap:total | pending |
| gu.low | 10.0 | 10.0 | pending |
| gu.mid | 11.0 | 11.0 | pending |
| gu.high | 12.0 | 12.0 | pending |
| gu.canonical_unit | **percent** | **percent_yoy** | pending |
| gu.basis_norm | gaap | gaap | pending |
| gu.basis_raw | null | **All-in** | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | All-in EPS growth from base of $6.02; includes $0.10-$0.12 headwind from non-recurring items | null | pending |
| gu.quote | [8-K] All-in EPS Growth: 10% to 12% for fiscal 2025 | [8-K] FY 2025 All-In EPS Growth (Maintain) +10% to +12%. FY 2024 Base Period EPS: $6.02. | pending |
| gu.evhash16 | 68a2c0a95982c9a2 | edec4d4e57f6dc34 | pending |
| gu.xbrl_qname | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | pending |
| gu.concept_family_qname | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Sonnet used `percent_yoy`. Sonnet captured `basis_raw: All-in`. Haiku put base period info in conditions; Sonnet put it in quote. Sonnet's conditions is null while Haiku's is richer.

### Item 5: EPS (non_gaap basis / Core)

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:eps | guidance:eps | pending |
| g.label | EPS | EPS | pending |
| gu.id | gu:0000080424-24-000110:eps:gp_2024-07-01_2025-06-30:non_gaap:total | gu:0000080424-24-000110:eps:gp_2024-07-01_2025-06-30:non_gaap:total | pending |
| gu.low | 5.0 | 5.0 | pending |
| gu.mid | 6.0 | 6.0 | pending |
| gu.high | 7.0 | 7.0 | pending |
| gu.canonical_unit | **percent** | **percent_yoy** | pending |
| gu.basis_norm | non_gaap | non_gaap | pending |
| gu.basis_raw | **core** | **Core** | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | Includes $0.2bn commodity headwind | Outlooking $0.2bn after-tax headwind from commodities. Prior fiscal year benefits from minor divestitures and tax that won't repeat represents an additional $0.10 to $0.12 headwind. | pending |
| gu.quote | [8-K] Core EPS Growth: +5% to +7% for fiscal 2025 | [8-K] FY 2025 Core EPS Growth (Maintain) +5% to +7%. Core effective tax rate approximately 20% to 21%. | pending |
| gu.evhash16 | 0acd7cbb5b730562 | a9b89bf818ebdcbe | pending |
| gu.xbrl_qname | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | pending |
| gu.concept_family_qname | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Sonnet used `percent_yoy`. Sonnet's `basis_raw` capitalized ("Core" vs "core"). Sonnet's conditions are MUCH richer (commodity headwind + divestiture/tax headwind + $0.10-$0.12 detail). Sonnet's quote includes tax rate info. evhash16 differs.

### Item 6: Free Cash Flow Productivity

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:free_cash_flow_productivity | guidance:free_cash_flow_productivity | pending |
| g.label | Free Cash Flow Productivity | Free Cash Flow Productivity | pending |
| gu.id | gu:0000080424-24-000110:free_cash_flow_productivity:gp_2024-07-01_2025-06-30:unknown:total | gu:0000080424-24-000110:free_cash_flow_productivity:gp_2024-07-01_2025-06-30:unknown:total | pending |
| gu.low | 90.0 | 90.0 | pending |
| gu.mid | 90.0 | 90.0 | pending |
| gu.high | 90.0 | 90.0 | pending |
| gu.canonical_unit | percent | percent | pending |
| gu.basis_norm | unknown | unknown | pending |
| gu.basis_raw | null | **Adjusted** | pending |
| gu.derivation | point | point | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | Adjusted free cash flow productivity; maintained from prior guidance | null | pending |
| gu.quote | [8-K] Adjusted Free Cash Flow Productivity (Maintain) 90% for fiscal 2025 | [8-K] FY 2025 Adjusted Free Cash Flow Productivity (Maintain) 90%. | pending |
| gu.evhash16 | f6d718363ab95775 | 995d22131c096dea | pending |
| gu.xbrl_qname | null | null | pending |
| gu.concept_family_qname | null | null | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Sonnet captured `basis_raw: Adjusted`. Haiku left it null. Haiku put "Adjusted" context in conditions; Sonnet's conditions is null. Quote wording differs slightly.

### Item 7: Organic Revenue Growth

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:organic_revenue_growth | guidance:organic_revenue_growth | pending |
| g.label | Organic Revenue Growth | Organic Revenue Growth | pending |
| gu.id | gu:0000080424-24-000110:organic_revenue_growth:gp_2024-07-01_2025-06-30:unknown:total | gu:0000080424-24-000110:organic_revenue_growth:gp_2024-07-01_2025-06-30:unknown:total | pending |
| gu.low | 3.0 | 3.0 | pending |
| gu.mid | 4.0 | 4.0 | pending |
| gu.high | 5.0 | 5.0 | pending |
| gu.canonical_unit | percent | percent | pending |
| gu.basis_norm | unknown | unknown | pending |
| gu.basis_raw | null | null | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | Organic growth; excludes FX, acquisitions, divestitures | null | pending |
| gu.quote | [8-K] Organic Sales Growth: +3% to +5% for fiscal 2025 | [8-K] FY 2025 Organic Sales Growth (Maintain) +3% to +5% | pending |
| gu.evhash16 | 5451472cb385d263 | 3581c8f01465877b | pending |
| gu.xbrl_qname | null | null | pending |
| gu.concept_family_qname | null | null | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Haiku provided conditions explaining what "organic" excludes. Sonnet's conditions is null. Quote wording differs (Sonnet includes "Maintain"). evhash16 differs.

### Item 8: Revenue (Net Sales Growth)

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:revenue | guidance:revenue | pending |
| g.label | Revenue | Revenue | pending |
| gu.id | gu:0000080424-24-000110:revenue:gp_2024-07-01_2025-06-30:unknown:total | gu:0000080424-24-000110:revenue:gp_2024-07-01_2025-06-30:unknown:total | pending |
| gu.low | 2.0 | 2.0 | pending |
| gu.mid | 3.0 | 3.0 | pending |
| gu.high | 4.0 | 4.0 | pending |
| gu.canonical_unit | **percent** | **percent_yoy** | pending |
| gu.basis_norm | unknown | unknown | pending |
| gu.basis_raw | null | null | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | Net sales growth including 1% negative FX impact and acquisition/divestiture impacts | Includes a 1% negative impact from foreign exchange and acquisitions and divestitures | pending |
| gu.quote | [8-K] Net Sales Growth: +2% to +4% for fiscal 2025, includes 1% negative FX impact | [8-K] FY 2025 Net Sales Growth (Maintain) +2% to +4%. Includes a 1% negative impact from foreign exchange and acquisitions and divestitures. | pending |
| gu.evhash16 | b6a9ca89007d5e5c | b4db82034ab88983 | pending |
| gu.xbrl_qname | us-gaap:Revenues | us-gaap:Revenues | pending |
| gu.concept_family_qname | us-gaap:Revenues | us-gaap:Revenues | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Sonnet used `percent_yoy`. Conditions convey same info with slightly different wording. Quote more structured in Sonnet (includes "Maintain" tag).

### Item 9: Tax Rate

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:tax_rate | guidance:tax_rate | pending |
| g.label | Tax Rate | Tax Rate | pending |
| gu.id | gu:0000080424-24-000110:tax_rate:gp_2024-07-01_2025-06-30:unknown:total | gu:0000080424-24-000110:tax_rate:gp_2024-07-01_2025-06-30:unknown:total | pending |
| gu.low | 20.0 | 20.0 | pending |
| gu.mid | 20.5 | 20.5 | pending |
| gu.high | 21.0 | 21.0 | pending |
| gu.canonical_unit | percent | percent | pending |
| gu.basis_norm | unknown | unknown | pending |
| gu.basis_raw | null | **Core effective** | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | annual | annual | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2025 | 2025 | pending |
| gu.fiscal_quarter | null | null | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2024-10-18T14:08:15Z | 2024-10-18T14:08:15Z | pending |
| gu.source_key | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 CHARTER | EX-99.1 CHARTER | pending |
| gu.conditions | Core effective tax rate | null | pending |
| gu.quote | [8-K] Core effective tax rate approximately 20% to 21% for fiscal 2025 | [8-K] FY 2025 Core Effective Tax Rate approximately 20% to 21%. | pending |
| gu.evhash16 | e495dc0d05a3655d | 26823646e7dcee77 | pending |
| gu.xbrl_qname | us-gaap:EffectiveIncomeTaxRateContinuingOperations | us-gaap:EffectiveIncomeTaxRateContinuingOperations | pending |
| gu.concept_family_qname | us-gaap:EffectiveIncomeTaxRateContinuingOperations | us-gaap:EffectiveIncomeTaxRateContinuingOperations | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Sonnet captured `basis_raw: Core effective`. Haiku put "Core effective" in conditions instead. Quote wording differs slightly.

### PG: Share Repurchase (potential missing item)

PG's FY2025 guidance included share repurchase of $6-7B. Neither Haiku nor Sonnet extracted this.

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| Share repurchase $6-7B | **NOT EXTRACTED** | **NOT EXTRACTED** | pending |

---

## DECK (0000910521-25-000013) — 2.02 Earnings Press Release

### Item Count

| Model | Items Extracted |
|---|---|
| Haiku 4.5 | 2 |
| Sonnet 4.6 | 3 (includes 1 duplicate) |
| Opus 4.6 | pending |

### Item 1: EPS (gaap basis)

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:eps | guidance:eps | pending |
| g.label | EPS | EPS | pending |
| gu.id | gu:0000910521-25-000013:eps:gp_2025-04-01_2025-06-30:gaap:total | gu:0000910521-25-000013:eps:gp_2025-04-01_2025-06-30:gaap:total | pending |
| gu.low | 0.62 | 0.62 | pending |
| gu.mid | 0.645 | 0.645 | pending |
| gu.high | 0.67 | 0.67 | pending |
| gu.canonical_unit | usd | usd | pending |
| gu.basis_norm | gaap | gaap | pending |
| gu.basis_raw | null | null | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | quarter | quarter | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2026 | 2026 | pending |
| gu.fiscal_quarter | 1 | 1 | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2025-05-22T20:07:32Z | 2025-05-22T20:07:32Z | pending |
| gu.source_key | EX-99.1 | EX-99.1 | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 | EX-99.1 | pending |
| gu.conditions | excludes any impact from additional share repurchases | excludes any impact from additional share repurchases | pending |
| gu.quote | [8-K] Diluted earnings per share is expected to be in the range of $0.62 to $0.67. Diluted earnings per share guidance excludes any impact from additional share repurchases. | [8-K] Diluted earnings per share is expected to be in the range of $0.62 to $0.67. Diluted earnings per share guidance excludes any impact from additional share repurchases. | pending |
| gu.evhash16 | df4fc1b19a08e97e | df4fc1b19a08e97e | pending |
| gu.xbrl_qname | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | pending |
| gu.concept_family_qname | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | pending |
| gu.created | 2026-03-14T11:24:23.214105+00:00 | 2026-03-14T11:24:23.214105+00:00 | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Identical across Haiku and Sonnet. Same evhash16. Sonnet MERGEd onto the existing Haiku node without changing values.

### Item 2: EPS (unknown basis — Sonnet duplicate)

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| gu.id | **not created** | gu:0000910521-25-000013:eps:gp_2025-04-01_2025-06-30:unknown:total | pending |
| gu.low | — | 0.62 | pending |
| gu.mid | — | 0.645 | pending |
| gu.high | — | 0.67 | pending |
| gu.canonical_unit | — | usd | pending |
| gu.basis_norm | — | **unknown** | pending |
| gu.basis_raw | — | null | pending |
| gu.conditions | — | excludes any impact from additional share repurchases | pending |
| gu.quote | — | [8-K] Diluted earnings per share is expected to be in the range of $0.62 to $0.67. Diluted earnings per share guidance excludes any impact from additional share repurchases. | pending |
| gu.evhash16 | — | df4fc1b19a08e97e | pending |
| gu.created | — | 2026-03-14T11:35:21.103099+00:00 | pending |

**Delta:** Sonnet created a DUPLICATE EPS item with `basis_norm: unknown` instead of `gaap`. Same values, same quote, same evhash16, but different gu.id (basis_norm in the ID changed from gaap to unknown). This is a Sonnet error — it failed to recognize the EPS guidance was GAAP and defaulted to unknown.

### Item 3: Revenue

| Property | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| g.id | guidance:revenue | guidance:revenue | pending |
| g.label | Revenue | Revenue | pending |
| gu.id | gu:0000910521-25-000013:revenue:gp_2025-04-01_2025-06-30:unknown:total | gu:0000910521-25-000013:revenue:gp_2025-04-01_2025-06-30:unknown:total | pending |
| gu.low | 890.0 | 890.0 | pending |
| gu.mid | 900.0 | 900.0 | pending |
| gu.high | 910.0 | 910.0 | pending |
| gu.canonical_unit | m_usd | m_usd | pending |
| gu.basis_norm | unknown | unknown | pending |
| gu.basis_raw | null | null | pending |
| gu.derivation | explicit | explicit | pending |
| gu.period_scope | quarter | quarter | pending |
| gu.time_type | duration | duration | pending |
| gu.fiscal_year | 2026 | 2026 | pending |
| gu.fiscal_quarter | 1 | 1 | pending |
| gu.segment | Total | Total | pending |
| gu.segment_slug | total | total | pending |
| gu.given_date | 2025-05-22T20:07:32Z | 2025-05-22T20:07:32Z | pending |
| gu.source_key | EX-99.1 | EX-99.1 | pending |
| gu.source_type | 8k | 8k | pending |
| gu.section | EX-99.1 | EX-99.1 | pending |
| gu.conditions | (absent in Haiku) | assumes no meaningful changes to business prospects or risks; subject to changes in macroeconomic conditions, global trade policy including tariffs, geopolitical tensions, and supply chain disruption | pending |
| gu.quote | [8-K] Net sales are expected to be in the range of $890 million to $910 million. | [8-K] Net sales are expected to be in the range of $890 million to $910 million. | pending |
| gu.evhash16 | 378f421c97f8004c | **d368cb573b8a8c1b** | pending |
| gu.xbrl_qname | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | pending |
| gu.concept_family_qname | us-gaap:Revenues | us-gaap:Revenues | pending |
| gu.created | 2026-03-14T11:24:22.017887+00:00 | 2026-03-14T11:24:22.017887+00:00 | pending |
| MAPS_TO_CONCEPT | none | none | pending |
| HAS_MEMBER | none | none | pending |

**Delta:** Sonnet added rich conditions (tariffs, geopolitical tensions, supply chain). Haiku had no conditions. evhash16 differs (Sonnet's conditions changed the hash). XBRL concepts identical.

### DECK: Potential Missing Items

The DECK press release mentioned: gross margin 57.9%, HOKA revenue $2.233B, UGG revenue $2.531B, share repurchase authorization $2.5B. These are FY2025 ACTUALS not FY2026 guidance, so correctly excluded by both models. Only Q1 FY2026 forward guidance (revenue $890-910M, EPS $0.62-0.67) was extracted.

---

## NSC (0001552781-23-000051) — 7.01 Conference Attendance + 2.03 Receivables Facility

### Item Count

| Model | Items Extracted |
|---|---|
| Haiku 4.5 | 0 |
| Sonnet 4.6 | 0 |
| Opus 4.6 | pending |

Both models correctly identified this filing as containing NO forward guidance. The filing contains:
- Item 7.01: "CEO and EVP will attend Barclays conference" (no financial content)
- Item 2.03: $400M receivables facility amendment (financial obligation, not guidance)

**guidance_status: completed** for both models (correct — "completed" with zero items means "processed successfully, found no guidance").

---

## Cross-Model Comparison Summary (Haiku vs Sonnet)

### Structural Differences

| Dimension | Haiku 4.5 | Sonnet 4.6 | Winner |
|---|---|---|---|
| PG items extracted | 9 | 9 | Tie |
| DECK items extracted | 2 | 3 (1 duplicate) | **Haiku** (no duplicate) |
| NSC items extracted | 0 | 0 | Tie |
| XBRL concepts found | 5/9 PG items | **7/9** PG items | **Sonnet** (+CapEx, +Dividends) |
| XBRL members linked | 0 | 0 | Tie |
| canonical_unit precision | `percent` for growth metrics | **`percent_yoy`** for growth metrics | **Sonnet** (more semantically precise) |
| basis_raw captured | 1/9 PG items (core on one EPS) | **5/9** PG items (Core, Currency Neutral Core, All-in, Adjusted, Core effective) | **Sonnet** |
| conditions richness | Richer on some items (organic revenue, all-in EPS) | Richer on others (non_gaap EPS, DECK revenue) | Mixed |
| quote detail | Shorter, more concise | Longer, includes "(Maintain)" tags and base periods | **Sonnet** |
| Duplicate items | 0 | 1 (DECK EPS unknown) | **Haiku** |

### Numeric Accuracy

| Metric | Haiku | Sonnet | Match? |
|---|---|---|---|
| All PG low/mid/high values | Correct | Correct | YES |
| All DECK low/mid/high values | Correct | Correct | YES |
| Period identification | Correct (FY2025 annual, Q1 FY2026 quarter) | Correct | YES |
| Fiscal year/quarter | Correct | Correct | YES |

### XBRL Linking Detail

| PG Item | Haiku xbrl_qname | Sonnet xbrl_qname |
|---|---|---|
| Capital Expenditure | null | **us-gaap:PaymentsToAcquirePropertyPlantAndEquipment** |
| Dividends | null | **us-gaap:PaymentsOfDividends** |
| EPS (all 3 bases) | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted |
| FCF Productivity | null | null |
| Organic Revenue Growth | null | null |
| Revenue | us-gaap:Revenues | us-gaap:Revenues |
| Tax Rate | us-gaap:EffectiveIncomeTaxRateContinuingOperations | us-gaap:EffectiveIncomeTaxRateContinuingOperations |

| DECK Item | Haiku xbrl_qname | Sonnet xbrl_qname |
|---|---|---|
| EPS | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted |
| Revenue | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |

Neither model created MAPS_TO_CONCEPT or HAS_MEMBER relationships for any item. XBRL linking is property-level only (qname strings on GuidanceUpdate), not graph-level (relationship to XBRLConcept/XBRLMember nodes).

### Timing

| Model | PG Time | DECK Time | NSC Time | Notes |
|---|---|---|---|---|
| Haiku 4.5 | ~2 min | ~2 min | ~2 min | Fastest |
| Sonnet 4.6 | ~5 min | ~5 min | ~3 min | pending exact |
| Opus 4.6 | pending | pending | pending | Expected slowest |

---

## Opus 4.6 Results

### Item Counts

| Filing | Opus Items |
|---|---|
| PG | 9 |
| DECK | 3 (includes same Sonnet duplicate — basis_norm unknown) |
| NSC | 0 |

### PG — Opus Deltas vs Haiku/Sonnet

| Item | Property | Haiku | Sonnet | Opus | Notes |
|---|---|---|---|---|---|
| CapEx | xbrl_qname | null | us-gaap:PaymentsToAcquirePropertyPlantAndEquipment | **null** | Opus LOST the Sonnet XBRL link (MERGE overwrote with null) |
| CapEx | concept_family_qname | null | us-gaap:PaymentsToAcquirePropertyPlantAndEquipment | **null** | Same — Opus overwrote |
| CapEx | conditions | "As percentage of sales; maintained from prior" | "% of Net Sales" | **"as a percentage of net sales"** | All 3 differ |
| CapEx | quote | "Capital Spending, % of Sales (Maintain) 4-5% for fiscal 2025" | "FY 2025 Capital Spending, % Sales (Maintain) 4-5%." | **"Capital Spending, % Sales: 4-5%"** | Opus shortest |
| CapEx | evhash16 | 78cce9e960444b5a | a585ddbac5939080 | **83e3053ff2bfaf9b** | All 3 differ (quotes differ) |
| CapEx | g.aliases | [] | [] | **["capital spending % sales"]** | Opus added alias |
| Dividends | xbrl_qname | null | us-gaap:PaymentsOfDividends | **us-gaap:PaymentsOfDividends** | Opus kept Sonnet's XBRL |
| Dividends | conditions | "Approximately $10 billion total dividends; maintained" | "Approximately $10 billion" | **null** | Opus removed conditions |
| Dividends | quote | "Dividends (Maintain) ~$10bn for fiscal 2025" | "FY 2025 Dividends (Maintain) ~$10bn." | **"Dividends: ~$10bn"** | Opus shortest |
| Dividends | evhash16 | 40b2f3f202e62eef | 87f5f674604bea44 | **289ffb901e5e5cdf** | All 3 differ |
| EPS cc | canonical_unit | percent | percent_yoy | **percent_yoy** | Opus matches Sonnet |
| EPS cc | basis_raw | core | Currency Neutral Core | **currency neutral core** | Opus lowercase |
| EPS cc | conditions | "Currency-neutral core EPS growth; expects FX to be neutral" | "Expect foreign exchange to be neutral" | **"expect foreign exchange to be neutral"** | Opus matches Sonnet (lowercase) |
| EPS cc | evhash16 | 1aceb52544492f1c | 24e52e27905fb64f | **24e52e27905fb64f** | Opus matches Sonnet evhash! |
| EPS gaap | canonical_unit | percent | percent_yoy | **percent_yoy** | Opus matches Sonnet |
| EPS gaap | basis_raw | null | All-in | **all-in** | Opus lowercase |
| EPS gaap | conditions | "All-in EPS growth from base of $6.02; includes $0.10-$0.12 headwind" | null | **null** | Opus matches Sonnet (null) |
| EPS gaap | evhash16 | 68a2c0a95982c9a2 | edec4d4e57f6dc34 | **edec4d4e57f6dc34** | Opus matches Sonnet evhash! |
| EPS non_gaap | canonical_unit | percent | percent_yoy | **percent_yoy** | Opus matches Sonnet |
| EPS non_gaap | conditions | "Includes $0.2bn commodity headwind" | "Outlooking $0.2bn after-tax headwind from commodities. Prior fiscal year..." | **"Outlooking $0.2bn after-tax headwind from commodities. Prior fiscal year benefits from minor divestitures and tax that won't repeat represents an additional $0.10 to $0.12 headwind to EPS"** | Opus = Sonnet (richest) |
| EPS non_gaap | evhash16 | 0acd7cbb5b730562 | a9b89bf818ebdcbe | **50566a2d798349c3** | All 3 differ |
| FCF | basis_raw | null | Adjusted | **null** | Opus lost Sonnet's basis_raw |
| FCF | g.aliases | [] | [] | **["adjusted free cash flow productivity"]** | Opus added alias |
| Organic Rev | g.aliases | [] | [] | **["organic sales growth"]** | Opus added alias |
| Revenue | canonical_unit | percent | percent_yoy | **percent_yoy** | Opus matches Sonnet |
| Revenue | g.aliases | ["net sales"] | ["net sales"] | **["net sales", "net revenue", "total revenue", "net sales growth"]** | Opus expanded aliases |
| Tax Rate | basis_raw | null | Core effective | **null** | Opus lost Sonnet's basis_raw |
| Tax Rate | g.aliases | ["effective tax rate"] | ["effective tax rate"] | **["effective tax rate", "core effective tax rate"]** | Opus expanded aliases |
| Share repurchase $6-7B | NOT EXTRACTED | NOT EXTRACTED | **NOT EXTRACTED** | All 3 missed this |

### DECK — Opus Deltas

| Item | Property | Haiku | Sonnet | Opus |
|---|---|---|---|---|
| EPS gaap | — | identical | identical | **identical** (no changes) |
| EPS unknown (dup) | — | not created | created by Sonnet | **kept** (Opus didn't remove it) |
| Revenue | conditions | null | "assumes no meaningful changes...tariffs, geopolitical..." | **null** | Opus removed Sonnet's conditions |
| Revenue | evhash16 | 378f421c97f8004c | d368cb573b8a8c1b | **378f421c97f8004c** | Opus reverted to Haiku's evhash |

---

## Final 3-Model Comparison

### Quantitative Summary

| Metric | Haiku 4.5 | Sonnet 4.6 | Opus 4.6 |
|---|---|---|---|
| PG items | 9 | 9 | 9 |
| DECK items | 2 | 3 (1 dup) | 3 (1 dup kept) |
| NSC items | 0 | 0 | 0 |
| PG XBRL concepts found | 5/9 | **7/9** | 6/9 |
| PG aliases added | 0 | 0 | **7** (across multiple items) |
| PG canonical_unit precision | percent (4 items wrong) | **percent_yoy** (4 items correct) | **percent_yoy** (4 items correct) |
| PG basis_raw captured | 1/9 | **5/9** | **3/9** |
| DECK duplicate created | NO | YES | YES (kept) |
| Share repurchase $6-7B captured | NO | NO | NO |
| PG conditions richness | Medium | High | Medium (some nulled out) |
| PG quote conciseness | Verbose | Structured w/ (Maintain) | **Most concise** |
| Approximate time per filing | ~2 min | ~5 min | ~4 min (239s PG) |

### XBRL Linking Comparison (PG items)

| PG Metric | Haiku xbrl_qname | Sonnet xbrl_qname | Opus xbrl_qname |
|---|---|---|---|
| Capital Expenditure | null | **us-gaap:PaymentsToAcquirePropertyPlantAndEquipment** | null (lost!) |
| Dividends | null | **us-gaap:PaymentsOfDividends** | **us-gaap:PaymentsOfDividends** |
| EPS (all 3 bases) | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted | us-gaap:EarningsPerShareDiluted |
| FCF Productivity | null | null | null |
| Organic Revenue Growth | null | null | null |
| Revenue | us-gaap:Revenues | us-gaap:Revenues | us-gaap:Revenues |
| Tax Rate | us-gaap:EffectiveIncomeTaxRateContinuingOperations | us-gaap:EffectiveIncomeTaxRateContinuingOperations | us-gaap:EffectiveIncomeTaxRateContinuingOperations |

No model created MAPS_TO_CONCEPT or HAS_MEMBER relationships. All XBRL linking is property-level only (qname strings on GuidanceUpdate nodes).

### Winner by Dimension

| Dimension | Winner | Why |
|---|---|---|
| **Numeric accuracy** | TIE | All 3 identical on low/mid/high/unit values |
| **Item count (recall)** | TIE | All found 9 PG items, 2 DECK items |
| **No duplicates (precision)** | **Haiku** | Only model that didn't create the DECK EPS unknown duplicate |
| **XBRL concept linking** | **Sonnet** | Found 7/9 vs Opus 6/9 vs Haiku 5/9 |
| **Unit precision** | **Sonnet = Opus** | Both use percent_yoy; Haiku uses imprecise percent |
| **basis_raw capture** | **Sonnet** | 5/9 vs Opus 3/9 vs Haiku 1/9 |
| **Aliases** | **Opus** | Added 7 aliases across items; Sonnet/Haiku added 0 |
| **Conditions richness** | **Sonnet** | Most detailed conditions on EPS items; Opus nulled some out |
| **Quote conciseness** | **Opus** | Shortest quotes, most structured |
| **Speed** | **Haiku** | ~2 min vs ~5 min Sonnet vs ~4 min Opus |
| **Cost** | **Haiku** | ~$0.05 vs ~$0.25 Sonnet vs ~$1.50 Opus (estimated) |

### Overall Verdict

**Sonnet 4.6 is the best overall performer for guidance extraction.**

- Ties on numeric accuracy (the most important dimension)
- Best XBRL linking (found 2 more concepts than Haiku)
- Best basis_raw capture (critical for distinguishing GAAP vs non-GAAP vs constant currency)
- Richest conditions
- Only weakness: created 1 duplicate DECK EPS item

**Haiku 4.5 is the best cost/accuracy ratio.** Gets all numbers right, fastest, cheapest. Only misses XBRL enrichment and some metadata nuance. The DECK duplicate issue is absent.

**Opus 4.6 adds aliases but loses some Sonnet gains.** The MERGE pattern means later runs can overwrite earlier property values. Opus nulled out some conditions and lost the CapEx XBRL concept that Sonnet found. The alias expansion (7 new aliases) is unique to Opus and useful for future matching.

### Critical Finding: MERGE Overwrites

Because the pipeline uses Neo4j MERGE (not CREATE), each model run OVERWRITES properties set by the previous model. This means:
- Sonnet's CapEx xbrl_qname was OVERWRITTEN to null by Opus
- Sonnet's rich DECK revenue conditions were OVERWRITTEN to null by Opus
- Only the LAST model's property values persist

**Implication for production:** Run ONE model, not multiple. The comparison here required reading results between runs. In production, pick one model and stick with it.
