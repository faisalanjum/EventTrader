# Driver updates from new filings

**10-K choice for a staged rollout.** Flash screens groups of passages for each known driver. Hosted full Decider chooses individual passages from those groups. At the same time, cached Sol Medium reads the entire filing. Merge both readers’ original passages into one packet per driver. [Driver workflow v2](DriverWorkflow_v2.md) · [Driver workflow](DriverWorkflow.md#company-workflow)

## Step 1 cost for 700 companies and 50 drivers each

**Estimated historical backfill in USD.** **$1,443** with hosted Flash screening 10-Ks, **about $1,428** with Mac Flash and hosted full Decider, or **$1,772** with full Decider scanning every 10-K directly. Moving only Flash to the Mac saves about **$15** across 2,625 annual filings before electricity.

| Source | Historical items | Full hosted scan per item | Full hosted total | Hosted Flash on 10-Ks | Mac Flash on 10-Ks |
|---|---:|---:|---:|---:|---:|
| 10-K | 2,625 | 17.9¢ | $469 | $141 (5.4¢/filing) | ~$126 (4.8¢/filing) |
| 10-Q | 6,420 | 11.1¢ | $710 | $710 | $710 |
| Earnings 8-K | 9,668 | 1.97¢ | $191 | $191 | $191 |
| Other 8-K (all assumed processed) | 16,415 | 2.30¢ | $377 | $377 | $377 |
| Earnings-call transcript | 8,449 | 0.29¢ | $24 | $24 | $24 |
| Short news | 306,618 | 0¢ | $0 | $0 | $0 |
| **Total, rounded** | | | **$1,772** | **$1,443** | **~$1,428** |

Historical source counts from 796 companies were scaled to 700. Four 10-Ks at **50 names each** used **2.57¢ Flash + 21.89¢ full Decider**, versus **81.49¢** for the full scans. The budget applies this 70% saving to the $469 annual-filing baseline. The Mac estimate assumes the same forwarded workload; only Timken was measured locally. The earlier ten-name projection was $1,410 all hosted. Prices per million input tokens were $0.01 for Flash and $0.02 for full Decider. Totals exclude subscription quota, electricity, filing preparation and downstream work. [Pricing](https://docs.perplexity.ai/docs/getting-started/pricing.md) · [Cost evidence](Experiments/2026-11-27_sol_base_copies/RunpodCostTrial.json)

**10-Q budget stays at $710.** Flash screening saved 82% in the quarterly test but dropped useful evidence. For other 8-Ks, screen the event type and exhibit list before parsing. Budget $377 until the share that can be skipped is measured.

## Fifty drivers each on three previously untested 10-Ks

Both routes used the same independent cached Sol Medium read. Fees are actual hosted API costs in US cents for all 50 names per filing. Sol used subscription quota.

| Company | Preselected facts found by both | Median text per driver, full / Flash + full | API cost, full / Flash + full | Sol time for 50 |
|---|---:|---:|---:|---:|
| Marriott | 52/52 | 3.23% / 3.60% | 10.57¢ / 2.29¢ | 6m 05s |
| Disney | 45/45 | 2.69% / 3.01% | 21.49¢ / 6.71¢ | 8m 53s |
| Equitable Holdings | 29/29 | 5.67% / 5.86% | 36.27¢ / 13.27¢ | 22m 05s¹ |
| **All 150 packets** | **126/126** | **3.82% / 4.41%** | **68.33¢ / 22.27¢** | |

**Decision.** Adding hosted Flash saved **67%**. Testing both routes cost **90.60¢** in total. Both also passed **32/32** separately checked figures and **18/18** additional context checks. Both Decider routes alone missed Equitable’s $857m/$752m intersegment fee disclosure. Sol recovered it, Disney’s Hotstar bundle exclusion and Equitable’s note that prior periods were revised.

**Limits.** The 126 preselected checks covered 98 of 150 drivers. The additional checks reached four more. Only **2/150** final packets contained identical text. In 36 sampled passages from the Flash route, **8** were clearly useful, **9** clearly irrelevant and **19** uncertain. Combining all 50 drivers and counting shared text once returned **30%** of Marriott, **39%** of Disney and **58%** of Equitable. Filing share measures text volume.

¹ Equitable includes two timed-out reads that succeeded on retry. Times start from prepared text and cover Sol alone. [Frozen checks, packets, cost records and offline verification](ContextSearchEvidence/Flash50Fresh_20261127.zip)

## Who reads each source

| Source | Evidence sent downstream | Reason |
|---|---|---|
| 10-K | Flash + full Decider and independent cached Sol. Send one combined packet per driver. | 212/213 reviewed facts across 20 filings. Flash forwards groups at 1% relevance. Full Decider keeps passages at ⅓ combined probability of direct or supporting evidence. |
| 10-Q | Full Decider reads the filing and exhibits. | The cheaper route twice missed Tyler’s fee-growth explanation and Ovintiv’s Canadian revenue table. [Quarterly test](#quarterly-flash-test) |
| 8-K | On earnings filings and other events selected for processing, full Decider reads the filing **and exhibits**. | All 13 checked earnings facts came from the release. Other 8-Ks still need separate accuracy checks. |
| Earnings-call transcript | Full Decider selects management guidance from prepared remarks and Q&A. | 79/79 checked forecasts across six calls. Creating complete updates from those passages remains untested. [Transcript evidence](Experiments/2026-11-15_decider_guidance/readme.md) |
| Short news | Send the full dated story directly to the downstream reader. | The whole story kept 8/8 checks. Filtering lost two fiscal-year labels. |

**Handoff.** Retrieval was tested with driver names alone. Give the downstream reader the existing definition, previous update when available, and original evidence with source locations. It checks the measure, value, unit, period and qualifications, then creates the update and links. Permit a focused search of the saved filing when a heading, definition or footnote could change the record. Leave unresolved fields open. A separate Decider-only transcript test produced zero complete accepted updates. [Driver rules](../DRIVER_RULES.md) · [Decider extraction](DeciderExtraction.md)

## Quarterly Flash test

Autodesk, Tyler Technologies, Nasdaq and Atlassian. Each method received the same 50 driver names per company and the same quarterly filing and exhibits. Expected details were recorded before the scans. No Sol read the filings.

| Method | Figures or calculation inputs | Supporting details | Details for 4 drivers reviewed more deeply | Median filing text per driver | Actual hosted cost |
|---|---:|---:|---:|---:|---:|
| **Full Decider** | 139/141 | 136/138 | 22/28 | 2.24% | 41.57¢ |
| Flash → full Decider | 139/141 | 135/138 | 23/28 | 2.60% | 7.52¢ |
| Flash alone, keeping whole groups | 141/141 | 138/138 | 27/28 | 12.73% | 1.23¢ |

**What changed.** Both narrow methods missed the inputs for Tyler’s SaaS recurring revenue and its growth. Adding Flash recovered Autodesk’s $3.515bn in unbilled obligations that full Decider missed.

**Fresh repeat on Tyler and Ovintiv.** With the same 50 names per filing, both misses repeated. Flash passed Tyler’s fee-growth paragraph. Full Decider then scored it 27.8% on the filtered read and 41.3% on the full scan, against a 33⅓% cutoff. Both kept the fee figures. At Ovintiv, Flash scored the Canadian revenue table ($693m versus $782m) at 0.87%, below its 1% cutoff. Full Decider kept it. Repeating both methods on both filings cost **16.84¢**. [Repeat scores, source text and costs](ContextSearchEvidence/FlashQuarterlyRepeat_20261127.json)

**Coverage and cost.** Of 200 drivers, 141 had a verified figure or inputs, 19 had only supporting details and 40 had no verified answer. The four deeper reviews searched the entire filing for one driver each. Check sets overlap. In 48 sampled passages per method, 10 were clearly irrelevant with full Decider, 9 with Flash → full and 27 with whole groups. Total paid was **49.08¢** across all methods, counting the shared Flash scan once. [Source passages, per-driver scores, API responses and offline replay](ContextSearchEvidence/FlashQuarterly50_20261127.zip)

Earlier Palo Alto 10-Q, eight drivers. Full Decider and Flash → full both found 27/28 facts, missing that customers pay up front. They kept 1.65% and 2.52% of the filing per driver at the median and cost 1.31¢ and 0.46¢. Whole groups found 28/28, kept 19.51% and cost 0.11¢.

## Twenty 10-Ks, ten drivers per filing

| Evidence readers | Facts before Sol | Facts with Sol | Tagged figures with Sol | Median text per driver | Hosted Decider fees for 20 |
|---|---:|---:|---:|---:|---:|
| Full Decider + Sol | 211/213 | 212/213 | 107/110 | 2.91% | 74.28¢ |
| **Flash → full Decider + Sol** | **211/213** | **212/213** | **107/110** | **3.19%** | **17.06¢** |
| Flash → Flash + Sol | 200/213 | 210/213 | 110/110 | 2.56% | 11.29¢ |
| Flash → keep whole groups + Sol | 212/213 | 213/213 | 110/110 | 10.27% | 5.53¢ |

Ten packets combined covered a median **16.56%** of the filing after counting shared text once. The checks count driver-specific details and may overlap with the tagged figures. The 17.06¢ was 5.53¢ for Flash and 11.53¢ for full Decider. Actual new spend across all four comparisons was **33.24¢** after reusing earlier paid results and the same subscription Sol reads. [Per-driver results and offline replay](ContextSearchEvidence/FlashAnnual20_20261127.zip)

**Deeper accuracy check.** On eight Palo Alto drivers, the three readers found **164/192** (42/42 original checks and 122/150 added checks) versus **158/192** without Flash at the same cutoff. The 28 misses included headcount-based cost allocation and tariff-driven price increases. Median packet size fell from 3.84% to 3.64%. Separately, on ten filings with one driver each, the Flash route found **158/159** versus **159/159** without Flash. Both kept all 25 critical checks. [Palo Alto audit](Experiments/2026-11-27_sol_base_copies/FilingAudit.md) · [Ten-filing evidence](ContextSearchEvidence/FlashAnnualTen_20261127.json.gz)

## Mac or hosted Flash

**Hosted Flash is the faster backfill choice on the first complete 50-driver test.** Timken FY2023 used 1,401 passages and the same 50 names on both routes. Full Decider ran at Perplexity in both.

| Flash location | Flash time | Flash + full Decider time | Flash fee | Full Decider fee | Total cash |
|---|---:|---:|---:|---:|---:|
| Perplexity | 13s | **36s** | 0.45¢ | 1.73¢ | **2.18¢** |
| Mac BF16 | 12m 12s | **12m 34s** | 0¢ | 1.74¢ | **1.74¢** |

Both passed **9/9 reviewed details and 14/14 tagged figures** on five drivers, plus **42/42 source checks** on 38 drivers. The checks overlap. Twelve names lacked a separately verified amount. Only 19/50 packets matched exactly. Reviewing all 119 differing passage–driver pairs found useful context on both sides. Only hosted supplied the segment restatement for bearings capital spending. Only local supplied acquired Lagersmit’s ~$40m annual sales for Total Revenue. Both kept about 1.39% of the filing per driver at the median before Sol. Actual combined API spend was **3.92¢**. No new Sol calls were made. These are one-filing measurements. A seven-day backfill of 2,625 annual filings would require 3m 50s of Mac time per filing, running continuously. [Timken results and per-driver differences](ContextSearchEvidence/MacFlash50_Timken_20261127.json.gz)

Use one local request at a time with `pplx-decider-flash-v1.3:bf16` at `/api/decide`. Start Sol alongside Flash. For a prepared filing, packet time is the **longer of Sol’s time or Flash + full Decider’s time**, plus the merge. Sol took about seven minutes on eight Palo Alto drivers and a median 3m 20s at ten names in the 20-filing trial, with some reads reused. Each driver’s copy starts from the same unchanged section including its table headings. Verify cache use and flag interrupted or empty reads. [Cache design](BaseAndCopies.md) · [Mac concurrency](Experiments/2026-11-27_sol_base_copies/LocalDeciderConcurrency.json)

The local BF16 endpoint accepts up to 32,768 tokens. Both Flash precisions agreed on 472/472 filing choices. Using Flash to select final passages lost two useful disclosures in eight test batches. [Local model checks and examples](Experiments/2026-11-27_sol_base_copies/HistoricalComparisons.md#mac-verification)

**Still untested.** Final driver records, links, cases where no update is warranted and the cost of downstream lookups. [Reference protocol](Experiments/SELECTED/2026-11-23_decider_production_trial/PROTOCOL.md) · [Earlier methods and costs](Experiments/2026-11-27_sol_base_copies/HistoricalComparisons.md)
