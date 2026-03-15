# ADI Transcript Guidance Ground Truth Backup

Captured: 2026-03-14 before Haiku-only re-extraction test.
Source: ADI_2026-02-18T10.00 (Q1 FY2026 earnings call)
Original extraction model: Opus 4.6 (extracted 2026-03-13)
Total items: 14 GuidanceUpdate nodes

---

## Item 1: CapEx as Percent of Revenue (FY2026, Total)

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:capex_as_percent_of_revenue:gp_2025-12-01_2026-11-30:unknown:total |
| gu.label | CapEx as Percent of Revenue |
| gu.label_slug | capex_as_percent_of_revenue |
| gu.low | 4.0 |
| gu.mid | 5.0 |
| gu.high | 6.0 |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | explicit |
| gu.period_scope | annual |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | null |
| gu.segment | Total |
| gu.segment_slug | total |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | CFO Prepared Remarks |
| gu.conditions | null |
| gu.quote | [PR] We continue to expect fiscal 2026 CapEx to be within our long-term model of 4% to 6% of revenue. |
| gu.evhash16 | a240a1aa0b78f0a5 |
| gu.created | 2026-03-13T12:01:52.076666+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_pr"] |
| gu.xbrl_qname | null |
| gu.concept_family_qname | null |
| g.id | guidance:capex_as_percent_of_revenue |
| g.label | CapEx as Percent of Revenue |
| g.aliases | [] |
| g.created_date | 2026-03-13 |
| MAPS_TO_CONCEPT | NONE |
| MAPS_TO_MEMBER | NONE |
| HAS_PERIOD | gp_2025-12-01_2026-11-30 |

## Item 2: DPS (Q2 FY2026, Total)

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:dps:gp_2026-03-01_2026-05-31:unknown:total |
| gu.label | DPS |
| gu.label_slug | dps |
| gu.low | 1.1 |
| gu.mid | 1.1 |
| gu.high | 1.1 |
| gu.canonical_unit | usd |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | point |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Total |
| gu.segment_slug | total |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | CFO Prepared Remarks |
| gu.conditions | null |
| gu.quote | [PR] And as Vince mentioned, yesterday we announced our 22nd consecutive annual dividend increase, raising the quarterly amount by 11% to $1.10. |
| gu.evhash16 | aa6d3607fd53d73c |
| gu.created | 2026-03-13T12:01:52.607084+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_pr"] |
| gu.xbrl_qname | us-gaap:CommonStockDividendsPerShareDeclared |
| gu.concept_family_qname | us-gaap:CommonStockDividendsPerShareDeclared |
| g.id | guidance:dps |
| g.label | DPS |
| g.aliases | [] |
| g.created_date | 2026-03-13 |
| MAPS_TO_CONCEPT | us-gaap:CommonStockDividendsPerShareDeclared (label: "Common Stock, Dividends, Per Share, Declared", id: http://fasb.org/us-gaap/2022:us-gaap:CommonStockDividendsPerShareDeclared) |
| MAPS_TO_MEMBER | NONE |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 3: EPS (Q2 FY2026, Non-GAAP, Total)

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:eps:gp_2026-03-01_2026-05-31:non_gaap:total |
| gu.label | EPS |
| gu.label_slug | eps |
| gu.low | 2.73 |
| gu.mid | 2.88 |
| gu.high | 3.03 |
| gu.canonical_unit | usd |
| gu.basis_norm | non_gaap |
| gu.basis_raw | adjusted |
| gu.derivation | explicit |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Total |
| gu.segment_slug | total |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | CFO Prepared Remarks |
| gu.conditions | null |
| gu.quote | [PR] And based on these inputs, adjusted EPS is expected to be $2.88 plus or minus 15 cents. |
| gu.evhash16 | 3f1730f9c93745ee |
| gu.created | 2026-03-13T12:01:50.968840+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_pr"] |
| gu.xbrl_qname | us-gaap:EarningsPerShareDiluted |
| gu.concept_family_qname | us-gaap:EarningsPerShareDiluted |
| g.id | guidance:eps |
| g.label | EPS |
| g.aliases | ["Diluted EPS", "diluted EPS", "earnings per share", "diluted earnings per share", "core eps growth", "all-in eps growth", "currency neutral core eps growth"] |
| g.created_date | 2026-03-09 |
| MAPS_TO_CONCEPT | us-gaap:EarningsPerShareDiluted (label: "Earnings Per Share, Diluted", id: http://fasb.org/us-gaap/2022:us-gaap:EarningsPerShareDiluted) |
| MAPS_TO_MEMBER | NONE |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 4: Gross Margin (Q2 FY2026, Total) — COMPARATIVE

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:gross_margin:gp_2026-03-01_2026-05-31:unknown:total |
| gu.label | Gross Margin |
| gu.label_slug | gross_margin |
| gu.low | null |
| gu.mid | null |
| gu.high | null |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | comparative |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Total |
| gu.segment_slug | total |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | Q&A #1 (Stacy Raskin) |
| gu.conditions | Includes 50 bps from one-time channel inventory repricing that will not repeat in Q3; nearing optimal utilization level with only modest upside expected from utilization |
| gu.quote | [Q&A] In our Q2 outlook, we're assuming 100 bps of gross margin expansion, or up essentially 150 bps versus Q1, because that excludes the discrete items that I mentioned in my prepared remarks. And again, the expected increase here is driven by favorable mix and uplift from price, which includes 50 bps that will not repeat in Q3 since it relates to the one-time effect of repricing our inventory in the channel. |
| gu.evhash16 | 7d286773c989d915 |
| gu.created | 2026-03-13T12:05:15.839328+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_qa__1", "ADI_2026-02-18T10.00_qa__2"] |
| gu.xbrl_qname | us-gaap:GrossProfit |
| gu.concept_family_qname | us-gaap:GrossProfit |
| g.id | guidance:gross_margin |
| g.label | Gross Margin |
| g.aliases | [] |
| g.created_date | 2026-03-08 |
| MAPS_TO_CONCEPT | us-gaap:GrossProfit (label: "Gross Profit", id: http://fasb.org/us-gaap/2022:us-gaap:GrossProfit) |
| MAPS_TO_MEMBER | NONE |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 5: Operating Margin (Q2 FY2026, Total)

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:operating_margin:gp_2026-03-01_2026-05-31:unknown:total |
| gu.label | Operating Margin |
| gu.label_slug | operating_margin |
| gu.low | 46.5 |
| gu.mid | 47.5 |
| gu.high | 48.5 |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | explicit |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Total |
| gu.segment_slug | total |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | CFO Prepared Remarks + Q&A #1 (Stacy Raskin) |
| gu.conditions | 200 bps sequential improvement driven by gross margin expansion and OpEx leverage; OpEx growing mid-single digits due to no shutdown in Q2, continued hiring, higher bonus factor, GTC conference |
| gu.quote | [PR] Operating margin at the midpoint is expected to be 47.5% plus or minus 100 basis points. [Q&A] In Q2, I see OpEx growing in the mid single digit range. But we will see OpEx as a percent of revenue fall. And with the expected growth in gross margin, we see about 200 basis points of sequential improvement in Q2. So 47.5 at the midpoint. |
| gu.evhash16 | 71a58256280d3c15 |
| gu.created | 2026-03-13T12:01:49.950768+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_pr", "ADI_2026-02-18T10.00_qa__1"] |
| gu.xbrl_qname | null |
| gu.concept_family_qname | us-gaap:OperatingIncomeLoss |
| g.id | guidance:operating_margin |
| g.label | Operating Margin |
| g.aliases | [] |
| g.created_date | 2026-03-09 |
| MAPS_TO_CONCEPT | NONE |
| MAPS_TO_MEMBER | NONE |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 6: OpEx Growth (FY2026, Total) — IMPLIED

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:opex_growth:gp_2025-12-01_2026-11-30:unknown:total |
| gu.label | OpEx Growth |
| gu.label_slug | opex_growth |
| gu.low | null |
| gu.mid | null |
| gu.high | null |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | implied |
| gu.period_scope | annual |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | null |
| gu.segment | Total |
| gu.segment_slug | total |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | Q&A #1 (Stacy Raskin) |
| gu.conditions | null |
| gu.quote | [Q&A] And, you know, for the full year, we continue to expect OpEx growth to trail revenue growth by roughly half. |
| gu.evhash16 | 6bf476ea2f7e9e7f |
| gu.created | 2026-03-13T12:05:23.512410+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_qa__1"] |
| gu.xbrl_qname | null |
| gu.concept_family_qname | us-gaap:OperatingExpenses |
| g.id | guidance:opex_growth |
| g.label | OpEx Growth |
| g.aliases | [] |
| g.created_date | 2026-03-13 |
| MAPS_TO_CONCEPT | NONE |
| MAPS_TO_MEMBER | NONE |
| HAS_PERIOD | gp_2025-12-01_2026-11-30 |

## Item 7: Revenue — Automotive Q2 (Q2 FY2026) — IMPLIED

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:revenue:gp_2026-03-01_2026-05-31:unknown:automotive |
| gu.label | Revenue |
| gu.label_slug | revenue |
| gu.low | null |
| gu.mid | null |
| gu.high | null |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | implied |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Automotive |
| gu.segment_slug | automotive |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | Q&A #0 (Jim Schneider) + Q&A #9 (Joe Moore) |
| gu.conditions | Below seasonal due to tariff and macro pull-in unwind; greater China exposure light in Q2 due to Chinese New Year; book-to-bill ended under one in Q1; second half expected stronger |
| gu.quote | [Q&A] From an auto perspective, we do expect that to be flat to down sequentially, a bit below seasonal. And this is, as we've talked about, largely due to the tariff and macro pull-in unwind that we've been talking about since the second and third quarters of last year. |
| gu.evhash16 | c7d33b73d209f1b8 |
| gu.created | 2026-03-13T12:05:19.102413+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_qa__0", "ADI_2026-02-18T10.00_qa__9"] |
| gu.xbrl_qname | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| gu.concept_family_qname | us-gaap:Revenues |
| g.id | guidance:revenue |
| MAPS_TO_CONCEPT | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| MAPS_TO_MEMBER | adi:AutomotiveMember (id: 6281:http://www.analog.com/20230128:adi:AutomotiveMember) |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 8: Revenue — Automotive FY2026 — IMPLIED

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:revenue:gp_2025-12-01_2026-11-30:unknown:automotive |
| gu.label | Revenue |
| gu.label_slug | revenue |
| gu.low | null |
| gu.mid | null |
| gu.high | null |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | implied |
| gu.period_scope | annual |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | null |
| gu.segment | Automotive |
| gu.segment_slug | automotive |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | Q&A #9 (Joe Moore) |
| gu.conditions | Share position and underlying content growth unchanged; headwinds concentrated in first half from tariff pull-in unwind and China CNY |
| gu.quote | [Q&A] And I actually believe that auto will grow in fiscal 26 versus what was a record fiscal 25. |
| gu.evhash16 | c27b150904b8e780 |
| gu.created | 2026-03-13T12:05:21.308118+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_qa__9"] |
| gu.xbrl_qname | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| gu.concept_family_qname | us-gaap:Revenues |
| g.id | guidance:revenue |
| MAPS_TO_CONCEPT | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| MAPS_TO_MEMBER | adi:AutomotiveMember (id: 6281:http://www.analog.com/20230128:adi:AutomotiveMember) |
| HAS_PERIOD | gp_2025-12-01_2026-11-30 |

## Item 9: Revenue — Communications Q2 — IMPLIED

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:revenue:gp_2026-03-01_2026-05-31:unknown:communications |
| gu.label | Revenue |
| gu.label_slug | revenue |
| gu.low | null |
| gu.mid | null |
| gu.high | null |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | implied |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Communications |
| gu.segment_slug | communications |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | Q&A #0 (Jim Schneider) |
| gu.conditions | Driven by AI surge for data center and wireless cyclical recovery |
| gu.quote | [Q&A] We expect comms to be up high single digit sequentially, above seasonal and about 60% year over year. Again, as we've talked about now, the AI surge for data center and the wireless cyclical recovery of both driving. |
| gu.evhash16 | 9f9f1298e1e1046b |
| gu.created | 2026-03-13T12:05:17.995771+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_qa__0"] |
| gu.xbrl_qname | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| gu.concept_family_qname | us-gaap:Revenues |
| g.id | guidance:revenue |
| MAPS_TO_CONCEPT | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| MAPS_TO_MEMBER | adi:CommunicationsMember (id: 6281:http://www.analog.com/20230128:adi:CommunicationsMember) |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 10: Revenue — Consumer Q2 — IMPLIED

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:revenue:gp_2026-03-01_2026-05-31:unknown:consumer |
| gu.label | Revenue |
| gu.label_slug | revenue |
| gu.low | null |
| gu.mid | null |
| gu.high | null |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | implied |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Consumer |
| gu.segment_slug | consumer |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | Q&A #0 (Jim Schneider) |
| gu.conditions | null |
| gu.quote | [Q&A] And then consumer in Q2, we expect to be down mid-single digits in line with seasonality. |
| gu.evhash16 | c8ff3fda3f19afd6 |
| gu.created | 2026-03-13T12:05:20.203935+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_qa__0"] |
| gu.xbrl_qname | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| gu.concept_family_qname | us-gaap:Revenues |
| g.id | guidance:revenue |
| MAPS_TO_CONCEPT | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| MAPS_TO_MEMBER | adi:ConsumerMember (id: 6281:http://www.analog.com/20230128:adi:ConsumerMember) |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 11: Revenue — Data Center Medium-Term — IMPLIED

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:revenue:gp_MT:unknown:data_center |
| gu.label | Revenue |
| gu.label_slug | revenue |
| gu.low | null |
| gu.mid | null |
| gu.high | null |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | implied |
| gu.period_scope | medium_term |
| gu.time_type | duration |
| gu.fiscal_year | null |
| gu.fiscal_quarter | null |
| gu.segment | Data Center |
| gu.segment_slug | data_center |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | Q&A #6 (Vivek Arya) |
| gu.conditions | Refers to ATE, optical, and power segments within data center; current run rate over $2 billion (roughly 20% of total ADI) |
| gu.quote | [Q&A] Well, I think it's safe to say that these areas will all grow at double digits over the next several years. |
| gu.evhash16 | ced0be07420f90bc |
| gu.created | 2026-03-13T12:05:22.413008+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_qa__6"] |
| gu.xbrl_qname | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| gu.concept_family_qname | us-gaap:Revenues |
| g.id | guidance:revenue |
| MAPS_TO_CONCEPT | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| MAPS_TO_MEMBER | NONE (Data Center is not a standard XBRL segment for ADI) |
| HAS_PERIOD | gp_MT |

## Item 12: Revenue — Industrial Q2 — IMPLIED

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:revenue:gp_2026-03-01_2026-05-31:unknown:industrial |
| gu.label | Revenue |
| gu.label_slug | revenue |
| gu.low | null |
| gu.mid | null |
| gu.high | null |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | implied |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Industrial |
| gu.segment_slug | industrial |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | Q&A #0 (Jim Schneider) |
| gu.conditions | Driven by cyclical recovery and strength in ATE and aerospace/defense; book-to-bill well above one excluding pricing impact; still 20% below previous peaks |
| gu.quote | [Q&A] By end market, as we look out for Q2, what we expect to see is industrial continuing strong up 20% sequentially and well above seasonal at 50% year over year, clearly being aided by the cyclical recovery and our strength in ATE and ADEF. |
| gu.evhash16 | 31feda0ccb58f7ce |
| gu.created | 2026-03-13T12:05:16.894464+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_qa__0", "ADI_2026-02-18T10.00_qa__8"] |
| gu.xbrl_qname | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| gu.concept_family_qname | us-gaap:Revenues |
| g.id | guidance:revenue |
| MAPS_TO_CONCEPT | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| MAPS_TO_MEMBER | adi:IndustrialMember (id: 6281:http://www.analog.com/20230128:adi:IndustrialMember) |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 13: Revenue — Total Q2 — EXPLICIT

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:revenue:gp_2026-03-01_2026-05-31:unknown:total |
| gu.label | Revenue |
| gu.label_slug | revenue |
| gu.low | 3400.0 |
| gu.mid | 3500.0 |
| gu.high | 3600.0 |
| gu.canonical_unit | m_usd |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | explicit |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Total |
| gu.segment_slug | total |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | CFO Prepared Remarks + Q&A #11 (Chris Kesa) |
| gu.conditions | About 1/3 of Q/Q revenue increase from pricing actions; excluding pricing, sequential growth ~7% vs 11% total; roughly half of price lift relates to repricing channel inventory which will not repeat in Q3; expects ~50 bps incremental growth in Q3 and Q4 from price |
| gu.quote | [PR] Revenue is expected to be 3.5 billion plus or minus 100 million. [Q&A] The overall impact of the pricing actions on our Q2 outlook is about a third of the quarter-over-quarter revenue increase at the midpoint is related to price. Excluding the pricing uplift, our sequential growth outlook is more like 7% versus the 11% I mentioned before. |
| gu.evhash16 | 4c86f003510b3df9 |
| gu.created | 2026-03-13T12:01:48.813240+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_pr", "ADI_2026-02-18T10.00_qa__11"] |
| gu.xbrl_qname | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| gu.concept_family_qname | us-gaap:Revenues |
| g.id | guidance:revenue |
| MAPS_TO_CONCEPT | us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax |
| MAPS_TO_MEMBER | NONE |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

## Item 14: Tax Rate (Q2 FY2026, Total)

| Property | Value |
|---|---|
| gu.id | gu:ADI_2026-02-18T10.00:tax_rate:gp_2026-03-01_2026-05-31:unknown:total |
| gu.label | Tax Rate |
| gu.label_slug | tax_rate |
| gu.low | 11.0 |
| gu.mid | 12.0 |
| gu.high | 13.0 |
| gu.canonical_unit | percent |
| gu.basis_norm | unknown |
| gu.basis_raw | null |
| gu.derivation | explicit |
| gu.period_scope | quarter |
| gu.time_type | duration |
| gu.fiscal_year | 2026 |
| gu.fiscal_quarter | 2 |
| gu.segment | Total |
| gu.segment_slug | total |
| gu.given_date | 2026-02-18T15:00:00Z |
| gu.source_key | full |
| gu.source_type | transcript |
| gu.section | CFO Prepared Remarks |
| gu.conditions | null |
| gu.quote | [PR] Our tax rate is expected to be between 11 and 13%. |
| gu.evhash16 | e685cdb85d494810 |
| gu.created | 2026-03-13T12:01:50.461992+00:00 |
| gu.source_refs | ["ADI_2026-02-18T10.00_pr"] |
| gu.xbrl_qname | null |
| gu.concept_family_qname | us-gaap:EffectiveIncomeTaxRateContinuingOperations |
| g.id | guidance:tax_rate |
| g.label | Tax Rate |
| g.aliases | ["effective tax rate", "core effective tax rate"] |
| g.created_date | 2026-03-08 |
| MAPS_TO_CONCEPT | NONE |
| MAPS_TO_MEMBER | NONE |
| HAS_PERIOD | gp_2026-03-01_2026-05-31 |

---

## Relationship Summary

| Relationship | Count | Details |
|---|---|---|
| MAPS_TO_CONCEPT | 9/14 | DPS, EPS, Gross Margin, Revenue×7 (all segments) |
| MAPS_TO_MEMBER | 5/14 | Automotive×2, Communications, Consumer, Industrial |
| HAS_PERIOD | 14/14 | All items linked to GuidancePeriod nodes |
| FROM_SOURCE | 14/14 | All → Transcript ADI_2026-02-18T10.00 |
| FOR_COMPANY | 14/14 | All → Company ADI |
| UPDATES | 14/14 | All → Guidance parent nodes |

## Concept Nodes Referenced

| XBRL Concept | Concept Node ID | Items Using |
|---|---|---|
| us-gaap:CommonStockDividendsPerShareDeclared | http://fasb.org/us-gaap/2022:us-gaap:CommonStockDividendsPerShareDeclared | DPS |
| us-gaap:EarningsPerShareDiluted | http://fasb.org/us-gaap/2022:us-gaap:EarningsPerShareDiluted | EPS |
| us-gaap:GrossProfit | http://fasb.org/us-gaap/2022:us-gaap:GrossProfit | Gross Margin |
| us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | http://fasb.org/us-gaap/2022:us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax | Revenue (all 7 segment items) |

## Member Nodes Referenced

| Member | Member Node ID | Items Using |
|---|---|---|
| adi:AutomotiveMember | 6281:http://www.analog.com/20230128:adi:AutomotiveMember | Revenue Automotive Q2, Revenue Automotive FY |
| adi:CommunicationsMember | 6281:http://www.analog.com/20230128:adi:CommunicationsMember | Revenue Communications Q2 |
| adi:ConsumerMember | 6281:http://www.analog.com/20230128:adi:ConsumerMember | Revenue Consumer Q2 |
| adi:IndustrialMember | 6281:http://www.analog.com/20230128:adi:IndustrialMember | Revenue Industrial Q2 |

## concept_family_qname Summary

| concept_family_qname | Items Using |
|---|---|
| null | CapEx as Percent of Revenue (1 item) |
| us-gaap:CommonStockDividendsPerShareDeclared | DPS (1 item) |
| us-gaap:EarningsPerShareDiluted | EPS (1 item) |
| us-gaap:EffectiveIncomeTaxRateContinuingOperations | Tax Rate (1 item) |
| us-gaap:GrossProfit | Gross Margin (1 item) |
| us-gaap:OperatingExpenses | OpEx Growth (1 item) |
| us-gaap:OperatingIncomeLoss | Operating Margin (1 item) |
| us-gaap:Revenues | Revenue — all 7 segment items |

## Transcript Node Properties

| Property | Value |
|---|---|
| id | ADI_2026-02-18T10.00 |
| guidance_status | completed |
| symbol | ADI |
| formType | TRANSCRIPT_Q1 |
| fiscal_year | 2026 |
| fiscal_quarter | 1 |
| calendar_year | 2026 |
| calendar_quarter | 1 |
| quarter_key | ADI_2026_1 |
| conference_datetime | 2026-02-18T10:00:00-05:00 |
| company_name | Analog Devices, Inc. |
| speakers | {"Operator", "Jeff Ambrose", "Vincent Roche", "Richard Puccio", "Jim Schneider", ...} |
