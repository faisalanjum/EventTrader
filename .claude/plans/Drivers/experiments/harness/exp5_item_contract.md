# EXP-5 ITEM CONTRACT — assembled VERBATIM (v5, 2026-07-24)

v2 adds the DEFINING blocks v1 only referenced (hint enums · the
09 §3 field table · the 09 §4 lane matrix · FACT-23 · §10.7) so a
drafter/producer never needs any file beyond this one. Every doc
block is byte-true from its pinned source (manifest: line ranges
+ per-block sha256). Served to gold drafters and later,
byte-identical, to every EXP-5 producer arm (model slot only).

## 02 NAME rules — the naming law (NAME-01..NAME-19; drafters coin driver_name under it)
### [VERBATIM from 02_DriverCatalog.md lines 10-183]

## Naming rules

### A. Core naming rules

#### NAME-01 — A driver name is the cause only  `[LOCKED]`
- **Plain:** The name holds only the cause — a specific, reusable noun. Nothing else.
- **Rule:** The driver name is the reusable causal noun the evidence is about. What happened (the state), the direction, the size, the date, the company, the period, the units, and the raw quote all live in OTHER fields — never the name.
- **Why:** A clean cause-only label is what lets the same cause recur and be tracked over time; anything extra breaks reuse and "one name = one meaning."
- **Source:** Naming_Slices_XBRL.md §2 · DriverOntology.md R2 / §3
- **Replaces:** —

#### NAME-02 — One name per driver; no aliases list  `[LOCKED]`
- **Plain:** Each driver has exactly ONE name. Different spellings of the same thing all fold into that one name.
- **Rule:** A driver stores exactly one name. Spelling, plural, acronym, and word-order variants of the same cause are the SAME canonical form — reuse it, never coin a duplicate. There is no "aliases" list on the driver. A true duplicate found later is joined to its canonical by a reversible "same-as" link, and each node keeps its own evidence.
- **Why:** One name per cause is the whole point (same cause → same name everywhere); an aliases array can't hold each variant's own evidence, and duplicate names split the history.
- **Source:** DriverOntology.md §2 + R1 · DriverGraphSchema.md (SAME_AS edge, "No aliases property")
- **Replaces:** —

#### NAME-03 — Open vocabulary  `[LOCKED]`
- **Plain:** There's no fixed list of allowed words. A name's words come from the source text (or an existing driver).
- **Rule:** Names use an open vocabulary. Every important noun in a name must come from the source material or an existing catalog driver — never a fixed, closed word-list.
- **Why:** A closed word-list is what killed version 1 — it rejected 82% of even-correct names. Open vocabulary keeps real causes from being thrown away.
- **Source:** DriverOntology.md R4 / R10 · DriverExperiment.md (the two deaths)
- **Replaces:** —

#### NAME-04 — As specific as the evidence allows  `[LOCKED]`
- **Plain:** Name a driver as specifically as the source lets you. Never coin a broad name — breadth appears on its own, from reuse.
- **Rule:** Name the cause as specific as the evidence allows. Never coin a broad or category name — breadth is not chosen; it emerges only when the same exact name is reused across events or companies.
- **Why:** Coining a generic name is exactly what killed version 2 (three demand stories collapsed into one). Specific by default; broad only by emergence.
- **Source:** DriverOntology.md core rule · Naming_Slices_XBRL.md §0
- **Replaces:** —

#### NAME-05 — Name format  `[LOCKED]`
- **Plain:** Names are lowercase, words joined by underscores only — no spaces, hyphens, dots, or colons.
- **Rule:** A driver name has only lowercase ASCII letters, digits, and underscores; starts with a letter; never ends with an underscore; has no double underscores; and is at least 2 characters.
- **Why:** One fixed, machine-safe form so the same cause always makes the exact same string, and code can group and compare names deterministically.
- **Source:** DriverOntology.md §2 (driver_name definition)
- **Replaces:** —

#### NAME-06 — Word order  `[LOCKED]`
- **Plain:** When a name has several parts, order them: thing/actor → detail → metric.
- **Rule:** When coining a multi-part name, order the parts: concrete thing or actor → needed detail → metric or mechanism. ("Thing or actor" = a commodity, customer group, or policy body like the Fed / OPEC.) Brand/segment/place parts are sliced off first (NAME-10), so they don't appear here. Examples: `hyperscaler_capex`, `restaurant_traffic`, `oil_price`, `fed_rate`.
- **Note (singular-by-default — owner 2026-07-11):** SINGULAR BY DEFAULT — coin the singular form of a count noun (`store_closure` not `store_closures`, `tariff` not `tariffs`): the name is the cause CLASS; how many, how big, and how often live in the fact's fields, never the name. Keep the plural ONLY when (a) the plural is the standard financial/business term for that concept — the form it is normally reported under (`earnings`, `bookings`, `sales`, `savings`, `futures`, `receivables`) — or (b) the singular would name a DIFFERENT concept (`product_returns` — a "return" is an investment concept). The exception list is illustrative, never exhaustive — the two-part test decides (NAME-19). Locked whole phrases (NAME-08) are never singularized (`same_store_sales`).
- **Why:** One consistent order means the same cause is always written the same way, so word-order variants collapse to one canonical name (NAME-02).
- **Source:** DriverOntology.md R3
- **Replaces:** old example `iphone_china_sales` (brand/geo now sliced) — 95_Supersession #1

#### NAME-07 — Familiar names win  `[LOCKED]`
- **Plain:** For well-known market/policy causes, use the familiar name, not an invented one.
- **Rule:** Use the familiar form: `fed_rate`, `yield_curve`, `oil_price`, `tariff_policy`, `fda_approval`. **Precedence (owner 2026-07-11):** the familiar short form applies only when the source does not itself distinguish a specific named sibling instrument or benchmark within that family; when the source names the sibling (SOFR vs the fed-funds family → coin `sofr_rate`), NAME-04 specificity wins. Familiarity is a fallback for undifferentiated mentions, never a license to flatten stated specificity. (Commodity benchmarks: already NAME-12(c).)
- **Why:** Everyone already calls it the same thing → maximum reuse.
- **Source:** DriverOntology.md R5
- **Replaces:** —

#### NAME-08 — Keep standard financial phrases whole  `[LOCKED]`
- **Plain:** A standard phrase stays together as one name — don't split or reorder it.
- **Rule:** `gross_margin`, `free_cash_flow`, `net_interest_margin`, `same_store_sales` stay whole.
- **Why:** These are recognized units; splitting them makes non-standard, non-reusable names.
- **Source:** DriverOntology.md R6
- **Replaces:** —
- **Note (signed-driver pin — OD-12, owner 2026-07-06 · 66 §0.R OD-12):** a loss/deficit is the NEGATIVE region of the standard signed metric, not a separate cause — coin `net_income` / `operating_margin` / `eps`, never a loss-magnitude driver (`net_loss` / `loss_margin` / `loss_per_share`). The loss is stored as a negative value (09 §3), so two producers can't fork on `loss_margin=+5` vs `operating_margin=−5`. Consistent with NAME-15 (what-happened / size are not in the name).

#### NAME-09 — One cause per name (split multiples; short; a noun)  `[LOCKED]`
- **Plain:** One name = one cause. Two causes → two drivers. Keep names short and noun-like.
- **Rule:** A name carries exactly one cause. Two+ independent causes → a separate driver each, never bundled (`asset_impairment_and_lease_termination` → split). Keep names short; if it takes many words to be specific, it's probably two drivers. Reads as a noun.
- **Why:** Bundled names can't be tracked/reused and break one-name-one-meaning.
- **Source:** DriverOntology.md R2 / R8
- **Replaces:** —

### B. Name vs slice

#### NAME-10 — Own measured company parts → the slice, not the name  `[LOCKED]`
- **Plain:** If the quote is measuring one part of the reporting company's own business, put that part in the slice tag, not the Driver name.
- **Rule:** Segment, geography, product, customer, channel, and entity_ownership are slices ONLY when the quote clearly frames them as the reporting company's own measured part. Stored slice kinds are FS-06's six kinds; "brand" is a source word, not a stored kind. Capture every such qualifier with FS-02 multi-slice. Examples: Apple reports iPhone sales → `sales` + `slice=product:iphone`; Nike revenue in China → `revenue` + `slice=geography:china`; supplier orders from Walmart → `orders` + `slice=customer:walmart`.
- **Why:** The read-time series already partitions by slice + period; an own-part in the name would fragment the history and duplicate causes.
- **Source:** Naming_Slices_XBRL.md §2
- **Replaces:** old "brand = its own driver" (DriverOntology R9) — 95_Supersession #1

#### NAME-11 — External or unclear objects stay in the name  `[LOCKED]`
- **Plain:** Decide from this quote and this company only. Own measured part → slice. Outside thing causing the outcome, or unclear role → name.
- **Rule:** Ask in order, stop at the first hit:
  - **0.** Strip freestanding direction/impact words first (rose, headwind, generic pressure…) — never in the name. Exception: a word like `pressure` may stay only when it is part of a specific reusable market force (`glp1_pressure`), not a generic effect word.
  - **1.** Is the qualifier clearly the reporting company's own measured part (segment/geography/product/customer/channel/entity_ownership)? → **SLICE** it under NAME-10.
  - **2.** Is the qualifier an external object, actor, platform, policy, event, or product causing the outcome? → keep it in the **NAME** (`iphone_demand`, `aws_outage`, `china_lockdown`, `freight_cost_pressure`, `tiktok_ban`).
  - **3.** Is the role unclear, or would stripping the qualifier leave only a vague fragment (`demand`, `ban`, `pressure`, `outage`)? → keep it in the **NAME**.
- **Customer pin:** `customer:walmart` is a slice only when the metric measures the reporting company's own business with Walmart (orders/revenue from Walmart). If Walmart's independent action is the cause, keep Walmart in the name (`walmart_price_cuts`).
- **Vendor pin:** Do not add a vendor slice kind here. A vendor/platform as an external cause stays in the name (`aws_outage`, `aws_spending`) unless a later owner rule creates a vendor slice.
- **Portion pin (OD-17):** a qualifier naming a PORTION of the measured quantity is never a slice — it stays in the name (see OD-17 below).
- **Why:** Slicing an unclear external cause can merge two different causes. Naming it may over-split, which is repairable.
- **Source:** Naming_Slices_XBRL.md §2
- **Replaces:** —

#### OD-17 — Portion qualifiers & non-population aggregates  `[LOCKED — owner 2026-07-11 · 66 §0.R OD-17]`
- **Plain:** A word naming which portion of a quantity is counted stays in the name. Aggregates map to the omitted slice only when they equal the whole consolidated company. Residual buckets are legal slice values. Accounting constructs are neither names nor slices.
- **Rule (core):** A qualifier naming which PORTION of the company's own measured quantity is counted — and that is not one of the six slice kinds, not a period window, and not a measurement version — stays in the NAME (`current_rpo`, `fee_earning_aum`, `funded_backlog`). Different portion = different driver, never SAME_AS the bare form. If unclear whether a word is a window or a portion, keep it in the name; never drop it.
- **(a) All-parts aggregates (population test):** a stated aggregate maps to FS-10's omitted slice ONLY when its population is the consolidated reporting entity ("total company", "consolidated", "group"). An aggregate crossing the ownership boundary or curating a subset is NEVER the omitted slice: network/system aggregates (`systemwide_sales`, `gmv`, `total_payment_volume`) are their own whole-phrase Drivers (NAME-08 posture); curated subsets ("core operations", ex-items, pro-forma combined) keep their qualifier — never mapped to the consolidated series.
- **(b) Residual buckets:** a company-stated residual ("Other", "Rest of World", "Corporate unallocated") is a LEGAL slice value of its stated kind (`segment:other`) — never a name token, never dropped. Residuals are company-specific and their composition may drift across periods: guards in 03 FS-07 note.
- **(c) Accounting constructs:** pure consolidation artifacts (eliminations, fair-value levels, reconciling items) are excluded as slice values AND as Driver names — never coin an eliminations Driver; drop-and-log (FS-20's log). An eliminations-driven mover is recorded as a fact on the AFFECTED reported metric (e.g. `operating_income`, lane state, quote carrying the eliminations mechanism) — evidence is never dropped.
- **Why:** Portion words otherwise fork producers or silently merge a portion into its total (the forbidden over-merge); "system-wide" maps ~5× different populations onto one series if read as consolidated; residuals and eliminations otherwise fork three ways.
- **Source:** 66 §0.R OD-17 (owner 2026-07-11) · FS-06a review (tracker T1-01/a/b/c as amended)
- **Replaces:** — (addition)

### C. What's in / out of a name

#### NAME-12 — What's allowed IN the name  `[LOCKED]`
- **Plain:** The cause, plus only the few locked extras that change identity: per-X denominator, benchmark name, or the terminal guidance/surprise suffix.
- **Rule:** In the name: (a) the cause; (b) per-X denominators (`oil_price_per_barrel`, `dividend_per_share`); (c) benchmark identity when a commodity has named, differently-priced benchmarks (`brent_oil_price` vs `wti_oil_price`); (d) terminal `_guidance` / `_surprise` suffixes under NAME-17. Nothing else.
- **Why:** Per-X and benchmark change the actual number → must be separate drivers; the read key has no other slot for them.
- **Source:** Naming_Slices_XBRL.md §3
- **Replaces:** —

#### NAME-13 — Per-X goes in the name (business AND physical)  `[LOCKED]`
- **Plain:** Source states a "per-X" → put it in the name. Not stated → leave the name bare.
- **Rule:** Transcribe whatever per-X the source states — business (`per_share`, `per_square_foot`) AND physical (`per_barrel`, `per_tonne`, `per_hour`), no judgment. Stated → oil at $80/barrel → `oil_price_per_barrel`; not stated → oil rose 8% → `oil_price`. Different per-X = a different driver (`oil_price_per_barrel` ≠ `oil_price_per_tonne`), never same-as. No per-X unit — the unit stays the base (usually `usd`/`count`).
- **Note:** Standard financial acronyms that already include the denominator keep their familiar name: `eps` is valid and does not need to become `earnings_per_share`.
- **Why:** The read-time key uses name + unit and ignores the quote, so a per-X left out of the name would merge two different numbers.
- **Source:** Consolidation/UnitExtraction.md Rules 2/3 · Naming_Slices_XBRL.md §3
- **Replaces:** old "$/physical → unknown / per-X stays bare" — 95_Supersession #3

#### NAME-14 — The version of a number is NOT in the name  `[LOCKED]`
- **Plain:** adjusted / diluted / constant-currency go in a separate "measurement" tag, not the name.
- **Rule:** The version of a number (adjusted, diluted, basic, constant-currency, core, cash…) goes in the **measurement** slot INSIDE fact_scope — a sibling of the slice, NOT a 7th slice kind. `adjusted eps` → name=`eps`, measurement=`{adjusted}`. Store the specific stated word (case/whitespace/punctuation normalized); default empty (never assume gaap); gaap/non_gaap is a read-time view, never stored. A measurement word re-expresses the SAME quantity through a different lens; a word that changes WHICH portion is counted is never a measurement token — it belongs in the name (OD-17).
- **Why:** Keeps the base metric (`eps`) able to carry both its gaap and adjusted readings as separate, comparable facts.
- **Source:** Naming_Slices_XBRL.md §1 / §5
- **Replaces:** old "adjusted_eps in the name" (DriverOntology R9) — 95_Supersession #2

#### NAME-15 — What's kept OUT of the name  `[LOCKED]`
- **Plain:** Direction, what-happened, date, company, period, units, size never go in the name.
- **Rule:** Out of the name → into other fields: direction/impact (→ verdict), what-happened (→ driver_state), date/period (→ DriverPeriod), company (→ linked company), units & size (→ number fields), raw quote (→ quote). The name is only the cause.
- **Why:** Any of these in the name breaks reuse and one-name-one-meaning.
- **Source:** DriverOntology.md R7 · Naming_Slices_XBRL.md §3
- **Replaces:** —

#### NAME-16 — The full "banned inside a name" list  `[LOCKED]`
- **Plain:** 13 things that must never appear inside a name (with a few carve-outs).
- **Rule:** None appear in a name (rejected even if the source uses them):
  1. state words → driver_state *[OK: stable nouns/metric phrases ending -ing/-ed: `pricing`, `bookings`, `operating_margin`]*
  2. direction/polarity → verdict
  3. motion/change nouns → driver_state
  4. the reporting company's own name/brand (redundant — the fact already links to the company), and any incidental co-mentioned entity adding no causal specificity (an analyst, executive, law firm, or counterparty named in passing) *[OK: an external company, platform, institution, or person whose own independent action or state IS the stated cause (NAME-11 test 2): `fed_rate`, `opec_supply`, `fda_approval`, `walmart_price_cuts`, `aws_outage`, `tiktok_ban`]*
  5. period tokens
  6. numbers/sizes/bare units (`bps`, `percent`, `usd`)
  7. source-type labels
  8. provider/vendor labels as metadata *[OK when the vendor/platform is the external cause under NAME-11: `aws_outage`, `aws_spending`]*
  9. XBRL prefixes
  10. metaphors/sentiment/effect-on-stock words *[OK only when the word is part of a specific reusable market force, e.g. `glp1_pressure`; generic "pressure" stays banned]*
  11. a bare category word alone (`macro`, `sector`, `demand`, `sentiment`)
  12. vague descriptors too broad to name a cause
  13. glue words (`the`, `of`, `in`, `and`, `to`, `for`)
- **Why:** Each has its own field; in the name they break reuse and one-name-one-meaning.
- **Source:** DriverOntology.md R7
- **Replaces:** #4 ticker/legal/person ban → external-actor principle — 95_Supersession #40 (owner 2026-07-11)

### D. Family, gate & meta

#### NAME-17 — Metric-family suffix stays in the name  `[LOCKED]`
- **Plain:** For earnings, the `_guidance` / `_surprise` suffix stays in the name; fact_type is separate.
- **Rule:** Name metric + mechanism: `{metric}_surprise` (a delivered-or-promised value vs a cross-party expectation; the 3 types live in the `surprise=` fact_scope slot, NOT the name — one `{metric}_surprise` Driver, OD-21), `{metric}_guidance` (forward outlook) — `eps_surprise`, `revenue_guidance`. Suffix stays in the name AND fact_type is a separate permanent field. The base `{metric}` is a separate driver linked by `BASE_METRIC` (never same-as). Beat/miss/raised → driver_state, never the name.
- **Why:** The guidance/surprise version is a genuinely different fact → its own driver, connected (not merged) to the base.
- **Source:** DriverOntology.md (earnings convention) · Consolidation/MetricGuidanceFamily.md
- **Replaces:** old "related-but-not-same must not be linked" — 95_Supersession #9

#### NAME-18 — The new-driver gate  `[LOCKED]`
- **Plain:** A new driver is allowed only if it's a genuinely reusable cause, grounded in the source, and unambiguous. Vague text → skip.
- **Rule:** Propose a new driver only when ALL hold: (a) no existing name means the same cause; (b) it satisfies every naming rule; (c) each important noun comes from the source or an existing driver; (d) it's attached to ≥1 causal claim with real evidence; (e) it's a reusable CLASS, not bound to a single instance (`government_shutdown` OK even once; `q1_2026_shutdown_effect` rejected); (f) if the rules leave >1 candidate name → reject as ambiguous; (g) if the evidence is vague or names no reusable cause → skip, never invent.
- **Why:** The fail-closed gate that keeps junk, one-off, and hallucinated names out of the catalog.
- **Source:** DriverOntology.md R10 · Drivers.md (skip-if-vague)
- **Replaces:** —

#### NAME-19 — Rule changes use one general principle, never sector examples  `[LOCKED]`
- **Plain:** When we change a naming rule, we state one general principle — never sector-specific examples.
- **Rule:** Any change to the naming rules must be a single general principle, not sector-specific examples. Examples overfit — named domains pass while unnamed ones break on held-out data.
- **Why:** Baking in specific examples is exactly how version 1 died; principles generalize.
- **Source:** Drivers.md · DriverExperiment.md

## 07 driver_state lane vocabularies — DU-09 metric ladder · DU-10 guidance/surprise · DU-11 action ladder
### [VERBATIM from 07_DriverUpdate.md lines 66-81]

#### DU-09 — metric lane + pick-first-match ladder  `[LOCKED]`
- **Plain:** metric states: increased/decreased/unchanged/mixed/reported/persists/unknown — pick the first that matches.
- **Rule:** Pick the FIRST match (ignore good/bad = stock_impact): (1) direction stated → increased/decreased ("weather worsened" → increased = MORE of it) · (2) same driver up in some parts + down in others → mixed (two DIFFERENT drivers opposite = split, not mixed) · (3) explicit flat → unchanged · (4) ongoing, no direction → persists · (5) bare value, no comparison → reported (prior value present → increased/decreased) · (6) real fact, no readable state → unknown. `narrowed` isn't a state (derived); `persists` not `continued`.
- **Why:** The ordered ladder removes ambiguity deterministically.
- **Source:** DriverGraphSchema.md driver_state

#### DU-10 — guidance + surprise lanes  `[LOCKED]`
- **Plain:** guidance: introduced/raised/lowered/reaffirmed/withdrawn. surprise: beat/in_line/missed (vs the expectation).
- **Rule:** **guidance** = introduced (first time) · raised/lowered (prior guide moved) · reaffirmed (kept) · withdrawn (pulled) · unknown. **surprise** = beat · in_line · missed · unknown, vs the EXPECTATION (consensus or the company's own prior guide/target) — NOT vs a prior-period actual (that's a metric change).
- **Surprise-state derivation (ISS-16 as amended by OD-13, owner 2026-07-06 via `66` §0.R):** the trigger is a stated comparison of a company value — a reported actual OR a company forward guide — vs a cross-party EXPECTATION (consensus, or for an actual its own prior guidance); an actual also writes the metric fact and a guide also writes the guidance fact (OD-21). Code computes only polarity-free `position` (above / inside / below / at_floor / at_ceiling) and sets `in_line` when there is no favorability wording and the compared value (actual OR guide) is inside a closed range or exactly at a boundary — INCLUDING a guide RANGE that CONTAINS the consensus point (e.g. guide $2.66–2.72B vs Street $2.67B → `in_line`, absent contrary wording; a band wholly above/below the point → beat/missed by producer meaning; OD-21). Code NEVER maps above→beat or below→missed, never keyword-matches, and never assumes higher=better. `beat`/`missed` are producer meaning judgments from the full phrase, negation/polarity/scope-aware; wordless outside-range cases need a transient discarded polarity proof, else `unknown`. A TEMPORAL comparison (prior_year/sequential) is a metric change, never a surprise.
- **Why:** Forecast-moves and beat/miss are their own signals, distinct from a metric's direction.
- **Source:** DriverGraphSchema.md driver_state · ISS-16 lock (`12` §10.5) · OD-13 amendment (`66` §0.R)

#### DU-11 — action_event lane + decision ladder  `[LOCKED]`
- **Plain:** 10 action states via a step-by-step ladder: is the action terminal or not, then pick the word.
- **Rule:** Lane = at_risk · announced · occurred · continued · resolved · canceled · suspended · rumored · failed · unknown. Domain-neutral ladder (copy ONLY the ladder into prompts, never the validation notes): **Step 0** classify the LATEST stage of one action; **Step 1** finality gate — **TERMINAL** {`failed` = ended involuntarily (outside party blocked / external condition unmet; incl. declining an offer never committed to) · `canceled` = the company's OWN free-choice withdrawal · `resolved` = a two-sided dispute settled · `occurred` = completed} vs **NOT-TERMINAL** {`rumored` = third-party-reported, company-unconfirmed (a denial keeps it rumored) · `at_risk` = a specific source-flagged adverse threat, not the company's plan · `suspended` = paused/resumable · `announced` = the company stated its OWN action before completion · `continued` = a prior action still ongoing}. Conventions: shelve/postpone → suspended; scrap/abandon/withdraw → canceled; threat → at_risk until executed → failed. **at_risk STRICT:** only a specific current source-flagged adverse not-yet-happened non-plan event; generic boilerplate is gate-dropped (rumored = unconfirmed ACTION; at_risk = adverse THREAT).

## 05 — HAS_PERIOD per lane + the OD-21 surprise target-period rule
### [VERBATIM from 05_Periods.md lines 40-40]

- **Rule:** guidance → REQUIRED. metric/surprise → used when the fact has a stated, source-implied, or code-derivable period. action_event → rare/optional, only when the action has a real stated window. Never force a period; no real window → no HAS_PERIOD. (For guidance, both `company_confirmed` true/false still require a period.) **OD-21:** a `guidance_vs_consensus` surprise REQUIRES a period = its matching guidance fact's TARGET period — may be future, or already ended for a restated guide (never the reported quarter, never absent); an `actual_vs_*` surprise takes its reported period. Actual-vs-guide is decided by the producer's basis hint, NEVER by whether the period has ended.

## 05 — producer period routing (first-match-wins) + the driver hard-fail amendment
### [VERBATIM from 05_Periods.md lines 80-81]

- **Rule:** Code computes `period_u_id`; the LLM emits only period fields and never writes `period_u_id`. Producer routing is first-match-wins: exact dates → sentinel_class → long_range_end_year → month → half → fiscal_quarter → fiscal_year → gp_UNDEF fallthrough. Don't emit conflicting fields. Never silently default a missing FYE to December (`ensure_driver_period` returns None only when there's truly no period).
- **Driver-wrapper amendment (owner 2026-07-03 — 95 #23 · `12_TrackB_FactPipeline.md` §10.7):** for DriverUpdate items, fields-present-but-unresolvable with NO explicit `sentinel_class` HARD-FAILS as a producer bug (never a quiet gp_UNDEF); `action_event` sentinel outcomes hard-fail (only a real stated window — which resolves to dated periods — qualifies); guidance still requires a real resolved period OR an explicit sentinel. The gp_UNDEF fallthrough survives only inside the pure shared builder (Guidance parity).

## FACT-17b — the ITEM CONTRACT (field meanings + top-level shape)
### [VERBATIM from 12_TrackB_FactPipeline.md lines 74-74]

- **FACT-17b — The ITEM CONTRACT (the producer-facing JSON every §4 component is built against; stored-field-aligned names).** Top-level: `source_id · source_type · ticker · fye_month` (+ optional `calendar_override`). Per item: `driver_name` · `driver_state` · `quote` · value slots EXACTLY as stored — `level_low / level_high / change_value / comparison_low / comparison_high / comparison_baseline / value_text / conditions / company_confirmed` (NOT the substrate's low/mid/high; no `mid` exists) · transients: `level_unit_raw / change_unit_raw`, the four per-slot hints (FACT-23), `level_shape_hint / comparison_shape_hint`, `measurement_raw_spans` (OD-9: producer copies exact source qualifier spans; code normalizes into `fact_scope.measurement`; raw spans are discarded and never stored), `surprise_basis_hint ∈ {actual, guidance}` (OD-21: REQUIRED on a SURPRISE item, FORBIDDEN elsewhere — the producer's forward-guide-vs-reported-actual call (DU-05/DU-06 outlook-verb + ISS-16); code composes the stored `surprise=` from it × `comparison_baseline`; transient, never stored, producer never emits `surprise=`) · period fields verbatim from the resolver contract: `period_start_date / period_end_date / fiscal_year / fiscal_quarter / half / month / long_range_start_year / long_range_end_year / sentinel_class / time_type` (+ `period_scope ∈ {ytd, ttm}` on cumulative facts) · `slice` = list of `kind:value` tokens or menu-pick refs. One CLI invocation = ONE source event (the fusion/collision locality guarantee). The CLI is the sole id/unit/period/measurement-token authority — any producer-precomputed derived field or final measurement token is ignored and recomputed (the substrate's always-recompute rule, cli:341-390).

## Per-slot hint VALUE ENUMS — code authority (driver.core.unit_resolver)

The four per-slot hints take EXACTLY these values (authority = the
production resolver constants, driver.core.unit_resolver — the module
the work-order import table names for canonicalization):

- `level_unit_kind_hint` / `change_unit_kind_hint` ∈ ['count', 'money', 'multiplier', 'ratio', 'unknown']
- `level_money_mode_hint` / `change_money_mode_hint` ∈ ['aggregate', 'price_like', 'unknown']

`money_mode` applies ONLY when the kind is money (aggregate = a total
amount; price_like = a per-unit/per-share style money figure; unknown =
cannot tell). A hint slot for an absent value slot stays null.

## EXAM RULING — producer-side period_scope + time_type (ISS-23)

- period_scope on an ITEM is producer-side: {ytd, ttm} or null ONLY
  (FACT-17b: 'period_scope in {ytd, ttm} on cumulative facts'); the
  wider stored enum (quarter/annual/...) is CODE-derived at write time
  and never emitted by a drafter/producer.
- time_type is {duration, instant} or null; a start==end window is
  ILLEGAL as a duration — mark it instant (ISS-23, 12 §10.7).

## 09 §3 — value shapes (self-describing) + OD-12 signed value-space (NOTE: this archived block's 'none' hint literal is HISTORICAL and NON-OPERATIVE — the binding rule follows immediately below)
### [VERBATIM from 09_DriverUpdate_Fields.md lines 38-40]

### Value shapes — self-describing, no shape field

> **point** = `level_low == level_high` (BOTH set — a point fills both bands) · **range** = `level_low < level_high` · **floor** ("at least X") = `level_low` only · **ceiling** ("up to X") = `level_high` only · **numberless** = all null. A shape is **closed** when both bands are present (point / closed range); deltas and widths derive ONLY from closed shapes. `comparison_low/high` use the SAME grammar — a single-value baseline sets BOTH (the $1.20 consensus = 1.20/1.20), and floor/ceiling baselines ("previously guided at least $85M") become expressible. **Hard writer rule: never write a point as low-only; low-only always means floor, and high-only always means ceiling.** **Structural safety net — transient hints:** the producer emits `level_shape_hint ∈ {point, range, floor, ceiling, none}` for level numbers and `comparison_shape_hint ∈ {point, range, floor, ceiling, none}` when comparison numbers are present; the writer derives each shape from the slots, hard-fails on mismatch, and discards the hints (never stored) — the same propose-then-verify pattern as `unit_kind_hint`/`money_mode_hint`. This catches the forgotten-high slip (a point degrading to a floor) AND the mirror slip the old `bound` field never caught (a floor degrading to a point when `bound` was forgotten); the only uncatchable error is a genuine semantic misread, which no field design catches. This is the old pipeline's production-proven encoding (points stored low=high for 3 years; the live renderer already decodes low-only→≥, high-only→≤, low==high→point; malformed partial fills were 6 rows in 8,432 under a three-slot regime — and detectable only via the redundant `derivation` field, whose role the transient hints now play without storage). Amends DU-13/14/16 + Codex §3.14 + schema:287-331 (§8). **Signed value-space (OD-12, owner 2026-07-06 — 66 §0.R OD-12):** the shape grammar applies to SIGNED values on the driver's own numeric axis — losses/declines are NEGATIVE for a net quantity; a charge/provision AMOUNT is positive, but a benefit/credit/release/reversal is negative (the sign is the driver's axis, NOT good/bad). `level_low`/`level_high` are the algebraic min/max. **Value-first:** convert each stated phrase to the value it denotes, THEN apply the grammar — so "a loss of up to $2B" → value ≥ −2B → **floor** (`level_low=−2000`), the exact mirror of "revenue up to $5B" → **ceiling** (same "up to", opposite shape via the sign); a zero-crossing range stores both signed endpoints ("EPS −$0.10 to +$0.05" → `−0.10, 0.05` — magnitude+polarity cannot). Comparatives ("no worse/better than") are polarity-read (OD-13); numberless loss language stores no bounds; conditional downsides stay narrative; two co-stated one-sided bounds fuse (T11.3) into a range. Naming pin: no loss-magnitude drivers (02).

## EXAM RULING — the BINDING shape-hint rule (live law; supersedes the archived block above)

**BINDING SHAPE-HINT RULE (supersedes the archived text ABOVE):** the
archived 09 §3 block directly above lists 'none' as a hint literal —
that wording is HISTORICAL and NON-OPERATIVE. The LIVE LAW
(FINAL_DESIGN.md:238) governs: shape hints are
required-when-numbers-present, cross-checked, hard-fail on mismatch,
then discarded. Legal emitted values are EXACTLY {point, range, floor,
ceiling}; a slot with NO numbers carries NULL (no hint). Never emit
'none'. (Corroboration only: production
driver_validators._VALID_SHAPES carries the same four values and
rejects any hint without numbers.)

## 09 §3 — the producer/enrichment-written field table (18 fields: state vocab rule, level/change/comparison rules, baseline enum, value_text/conditions/company_confirmed, period_scope enum)
### [VERBATIM from 09_DriverUpdate_Fields.md lines 42-57]

### Producer/enrichment-written (18) — every one validator-gated

| Group | Fields | Key rules |
|---|---|---|
| State | `driver_state` | locked lane vocab. **OD-14 (owner 2026-07-06): guidance MOVEMENT is read-derived** — a bare guidance update stores `driver_state=unknown` and the read layer derives introduced/raised/lowered/reaffirmed from the prior COLLAPSED value (exposed as `effective_driver_state`, never written back); only source-STATED movements are stored; correction source/event metadata or explicit correction wording excludes an amendment from the derive (66 §0.R OD-14). Narrowed range → **midpoint rule** (mid up = raised · down = lowered · equal = reaffirmed); the validator enforces it ONLY on STATED movements (both shapes closed) and **SKIPS `unknown`**, so bare guidance never hard-fails. `narrowed` itself = read-time derived flag (§6.8), never stored |
| Evidence | `quote` | required, all lanes, unconditional |
| Level | `level_low` / `level_high` / `level_unit` | shapes per the grammar above (**a point fills BOTH bands** — producer-prompt rule + the ≥ render makes a forgotten high visible; low-only is a floor, high-only is a ceiling); old mid-only "approximately $X" → point; values stored **post-canonicalize scaling** (cents-on-aggregate / glued-$B mis-scale = write-time hard-fails — old Guard F's formal home); `level_unit` **required when ANY of level_*/comparison_* is non-null** and governs comparison values (no `comparison_unit`) |
| Change | `change_value` / `change_unit` | **strictly stated-only, all lanes** (DriverGraphSchema:331's computed "+0.10" example must be amended — beat size derives at read as `level_low − comparison_low`, defined only for closed point comparisons); delta-only facts keep their only number here; units may differ from level |
| Comparison | `comparison_low` / `comparison_high` / `comparison_baseline` | stated-only, never derived from another node; same shape grammar as level (single value = BOTH set); baseline enum `{consensus, prior_year, sequential_period, previous_guidance, null}` (DU-15 — no `internal_target`: own-target phrasing → `previous_guidance` else null); baseline MAY be set with null numbers ("ahead of expectations"); **metric lane FORBIDs BOTH `consensus` AND `previous_guidance`, and the guidance lane FORBIDs `consensus`** (OBJ-2 · OD-21) — an expectation comparison IS a surprise → route to the `_surprise` driver |
| Text | `value_text` | **GUIDANCE-ONLY**; the stated value in words ("low-to-mid single digits"); ≤200 chars, normalized; **value-aware lint** (rejects numeric values — "$5M", "12%", "160 bps" — allows anchors like "Q2", "2019 levels"); legal ONLY when every number field is null. Revisit trigger: first census of real metric facts |
| Caveat | `conditions` | **GUIDANCE-ONLY** (52.3% real fill; rendered to predictor); producer must also keep the clause inside the `quote`. Extension to action_event = a revisit trigger (see §4 note), not an owner decision |
| Flag | `company_confirmed` | **guidance-only boolean `true/false`** (matches Consolidation README, GuidancePeriod, and 99_Codex_Decision_Audit.md §3.18; enum wording is unnecessary); non-identity; all current-pipeline output = `true`; future allowed third-party/rumored guidance-like claims = `false` |
| XBRL | `xbrl_qname` | **metric-only, ON THE FACT** + `MAPS_TO_CONCEPT` edge on the fact; written by the concept-link enrichment step, not source-stated by the normal producer. A Driver class is global, while concepts are company-specific and can drift, so a class link would over-merge; guidance/surprise inherit via `BASE_METRIC` at read, and if the base metric is latent with no linked metric fact yet, inheritance returns no concept for now; **any non-GAAP measurement label ⇒ no inheritance** (the concept-linker G2 guard EXTENDED: measurement set = primary key, name-prefix regex kept only as the legacy-name fallback — old catalog names like `adjusted_eps` still exist until regeneration) |
| Framing | `fiscal_year` / `fiscal_quarter` / `period_scope` / `time_type` | kept on the node (locked §3.8/PER-13 — the same calendar window reads differently per company); `period_scope` final enum = `{quarter, annual, half, monthly, ytd, ttm, exact_range, short_term, medium_term, long_term, undefined}` — **`long_range` retired at store time → `exact_range`** (dated multi-year windows keep their real `gp_<start>_<end>`; the `*_term`/`undefined` values pair with the 4 dateless sentinels — a validator-checkable invariant) |

> **Recovery-lane metadata (owner 2026-07-11, not producer-written):** `disputed` (boolean, default false) — set/unset ONLY by the kernel §10 recovery machinery, never by producers or enrichment; excludes that one fact from cross-company/history-weighted features; outside the producer contract and the field count above (kernel §10 item 8).

## 09 §4 — the per-lane validator matrix (REQ / WS / FORBID per lane)
### [VERBATIM from 09_DriverUpdate_Fields.md lines 64-84]

## §4 Per-lane validator matrix

`REQ` = must be present · `WS` = only when the source states it · `FORBID` = hard-fail.

| Field / edge | metric | guidance | surprise | action_event |
|---|---|---|---|---|
| `id` `fact_scope` `created` `date` `source_type` `driver_state` `quote` `OF_DRIVER` `FROM_SOURCE` | REQ | REQ | REQ | REQ |
| `HAS_PERIOD` | when real | **REQ** | when real (**REQ** for `guidance_vs_consensus` = the guidance fact's target period, OD-21) | when real (rare) |
| `level_*` | WS | WS | WS (the compared value — actual OR guide, OD-21) | WS (deal/buyback size) |
| `change_value/unit` | WS stated-only | WS stated-only (= the guide's own revision size) | WS stated-only | WS stated-only |
| `comparison_low/high` | WS | WS (prior band) | WS (the expectation) | WS |
| `comparison_baseline` | WS ∈ {prior_year, sequential_period} — **`consensus` AND `previous_guidance` FORBID** (both expectation baselines → `_surprise`; ISS-16/OBJ-2, owner 2026-07-03) | WS — **`consensus` FORBID → route to `_surprise`** (`surprise=guidance_vs_consensus`; guide-vs-own-prior stays a guidance movement; OD-21) | **REQ** ∈ {`consensus`, `previous_guidance`} (required — missing = hard-fail, NEVER silently defaulted; "expectations"/"Street" reads as `consensus`, "our guidance" as `previous_guidance`; `previous_guidance` = `actual_vs_guidance`; `surprise=` can't be composed without it; OD-21) | WS |
| `surprise=` (fact_scope slot, code-composed, OD-21) | FORBID | FORBID | **REQ** | FORBID |
| `value_text` | FORBID | WS (numberless-only) | FORBID | FORBID |
| `conditions` | FORBID | WS | FORBID | FORBID |
| `company_confirmed` | FORBID | WS | FORBID | FORBID |
| `xbrl_qname` + `MAPS_TO_CONCEPT` | WS | FORBID (inherit) | FORBID (inherit) | FORBID |
| any computed/fabricated number | **FORBID — all lanes** | | | |

*(Revisit triggers, not owner decisions: `value_text` → metric ONLY if the first census of real metric facts shows (a) material numberless-reading rates AND (b) actual persists→persists reading reversals the state stream missed — the one case §6.4's quote-render fallback cannot surface to the scanner; any such flip must be **extractive-only** (copy the stated reading verbatim — "soft", "elevated" — never paraphrase) or it destabilizes §6.9's collapse comparator: paraphrased direction words ("weakened" vs "softened") make cross-source restatements of one fact look like different facts. Considered + rejected 2026-07-02: metric direction words duplicate `driver_state` ("demand improved" adds nothing to `increased`), and the real gap — numberless metric facts rendering as a bare state word — is closed by §6.4's quote fallback at zero field cost. ALSO rejected 2026-07-02: a read-time "persists quote-change flag" (compare consecutive quotes, flag possible reading changes) — its comparator is either string inequality (fires on nearly every cross-event rewording of an unchanged reading → alarm-fatigue noise in the signal path) or semantic judgment at read time (LLM/NLP inside the deterministic scanner — architecture violation); the predictor already sees reading flips because the series render shows consecutive rendered values incl. §6.4 quote fallbacks, and the scanner's only sound comparator is the extractive `value_text` this trigger governs. `conditions` → action_event on the first census of real action facts showing material stated-caveat rates. Each flip = one dict entry.)*


## 12 FACT-23 — the four per-slot hints (names + arity; owner-approved)
### [VERBATIM from 12_TrackB_FactPipeline.md lines 93-93]

- **FACT-23 — Per-slot hints (ADD, small).** `resolve_driverupdate_units` forwards ONE hint pair to both slots (verified :234-252) — but a money level + ratio change ("$5B, up 12%") needs two. Extend the item contract + helper: `level_unit_kind_hint`/`level_money_mode_hint` and `change_unit_kind_hint`/`change_money_mode_hint` (the bare pair stays accepted as applying to the level slot for backward compatibility of the tests). This sharpens census T11.5; hint arity per slot is now pinned — **✅ APPROVED (owner 2026-07-03, §10.3)**.

## 09 §7 — the PRODUCER CONTRACT (OD-11 basis · OD-9 spans · hints · units · OD-21 basis hint)
### [VERBATIM from 09_DriverUpdate_Fields.md lines 129-129]

**Producer contract:** chronological per-company processing (states depend on history reads); same-day tie rank = source rank; **a point fills BOTH bands** (`level_low = level_high`); **low-only means floor, high-only means ceiling**; **`level_shape_hint` accompanies level numbers and `comparison_shape_hint` accompanies comparison numbers** (writer cross-checks vs slots, hard-fails mismatch, discards — see §3 Value shapes); %-only guides stay on `<metric>_guidance`; the `level_unit` is the guide's growth BASIS **read from the source** (OD-11, owner 2026-07-06 — 66 §0.R OD-11), NOT the old blanket `percent_yoy` hard-stamp — **metric-type first:** a static-% LEVEL metric's bare "up X%" → `unknown` (unless "points/bps" → `percent_points`/`basis_points`, or "to X%" → `percent`); else a GROWTH → sequential/prior-period → `percent_sequential` (added to UNIT-01), YoY/comparable/annual or a bare dated-period default → `percent_yoy`, sentinel-horizon → `unknown`; annual sequential==yoy → `percent_yoy`; measurement adjustments (constant_currency/organic/adjusted/pro_forma) go in the measurement slot (FS-25) and NEVER decide the basis (explicit DU-16-rule-7 extension: on guidance facts `change_value` is reserved for the guide's own revision size); blanket withdrawals fan out per open guide in the stated scope (history-derived — the one place the model writes beyond the literal quote; owner sign-off noted); money facts must carry `money_mode_hint`; numeric facts must carry non-empty `unit_raw` to the resolver; a SURPRISE item must carry `surprise_basis_hint ∈ {actual, guidance}` (FORBIDDEN on other lanes), from which code composes `surprise=` × `comparison_baseline` BEFORE fusion (OD-21).

## 12 §10.5 — ISS-16 routing (LOCKED) + OD-13 favorability + OD-21 symmetry
### [VERBATIM from 12_TrackB_FactPipeline.md lines 124-134]

5. **ISS-16 routing — ✅ LOCKED (owner 2026-07-03), corpus-grounded; surprise-state derivation AMENDED by OD-13 (owner 2026-07-06).** The routing answer is still **"both, and the comparison baseline decides"** — a THREE-way split (the corpus revealed a tense trap the two-way framing missed). OD-13 replaces only the old higher-is-better surprise-state arithmetic: code computes polarity-free `position` (above/inside/below/at_floor/at_ceiling) + `in_line` when wordless-inside-closed-range; `beat`/`missed` are producer meaning judgments from the full phrase, with wordless-outside-range requiring a transient discarded polarity proof. `metric_meaning` proof is allowed only when the chosen favorable direction has no common mainstream counter-story; if not clean, state=`unknown`. DU-16.2 drops `beat`/`missed` from the sign rule. The routing below (0/1/2), `in_line` materialization, and OBJ-2 are unchanged.
   - **(0) Forward-looking guide-vs-guide → GUIDANCE lane, NOT surprise.** "we now expect $X (was $Y)" / "raised / reaffirmed / expects to be at the high end" (FIVE, KR, APA, ROKU-forward). The report scout confirmed MOST 8-K "prior guidance" text is this — a new-guide-vs-old-guide revision (state raised/lowered/reaffirmed/introduced), already DU-06's outlook-verb rule. The `vs prior guidance` phrasing must never be mistaken for a surprise.
   - **(1) Actual compared to an EXPECTATION → BOTH facts. The surprise trigger is the presence of an expectation COMPARISON, not a "beat" word (REVISED per owner 2026-07-03, grounded in DU-09 symmetry).** When a number is stated it ALWAYS lands on its home fact — the **metric** fact for a reported actual, the **guidance** fact for a forward guide (OD-21) — (level); AND a **`<metric>_surprise`** fact is written whenever the **PRODUCER DETECTS a stated actual-vs-expectation comparison** in the source (own prior guidance OR consensus) — a producer/extraction-time trigger, NOT a read-back of the metric fact's stored baseline (DU-15 keeps only ONE primary baseline, so a fact whose headline is `prior_year` + a secondary guide comparison would never fire an enum-keyed trigger — OBJ-1). The expectation comparison lands on the **surprise fact**. **State after OD-13:** code computes only position, never favorability; wordless actual inside a closed range or exactly at a boundary → `in_line`; wordless outside range → producer may set `beat`/`missed` only with a clean transient polarity proof, else `unknown`; stated favorability words set state only by full-phrase meaning, negation/polarity/scope-aware. Position words and loose verbs ("above", "below", "exceeded", "ahead of", "beat the budget/target/number") are not automatic favorability. A favorability judgment that disagrees with position is logged, not hard-failed; ungroundable derivation becomes `unknown`. Separate drivers, BASE_METRIC-linked (MF-02). There is still NO "bare-number → metric-only" case when an expectation comparison is present.
   - **(2) The ONLY metric-only cases:** (a) no expectation referenced at all (just the actual: "revenue was $5B"); (b) a comparison to a TEMPORAL baseline only — `prior_year` / `sequential_period` ("$5B vs $4.5B a year ago") → that is a metric CHANGE (increased/decreased), **not** a surprise (DU-05: actual-vs-prior-period-actual is a metric change, never a surprise). The distinction is EXPECTATION vs TEMPORAL comparison, detected by the producer at extraction (not read from a stored primary): a stated actual-vs-guidance/consensus → surprise; a stated actual-vs-prior-year/sequential → metric change. A fact may state BOTH (prior-year headline + a secondary guide) — the temporal one is the metric's change baseline, the expectation one fires the surprise fact.
   - **True symmetry (OBJ-2, ✅ APPROVED owner 2026-07-03):** BOTH expectation baselines are now metric-FORBID — `consensus` (already) AND `previous_guidance` (new). Expectation comparisons live ONLY on the surprise fact; the metric fact's `comparison_baseline` is **temporal-only** (`prior_year` / `sequential_period` / null). No duplicate guide-store. Amends the §6.4 matrix + 09 §4 + DU-15; logged as 95 #24. **OD-21 (owner 2026-07-14) extends the symmetry to the GUIDANCE lane** — a guidance fact ALSO FORBIDs `consensus`: a stated forward guide-vs-consensus/Street writes the guidance fact (the guide value + read-derived raised/lowered movement) AND a `<metric>_surprise` fact tagged `surprise=guidance_vs_consensus`; a guide-vs-own-prior-guide stays a guidance movement (case 0, unchanged). The three surprise types (`actual_vs_consensus`/`actual_vs_guidance`/`guidance_vs_consensus`) are carried by the `surprise=` fact_scope slot, which enters the id + series key (03 FS-27 · 09 §6.9 · 11 T12.1) so an outlook surprise and a later earnings surprise on the same driver+period never collapse together; OD-13's favorability machinery (position + producer meaning) applies unchanged to `guidance_vs_consensus` — in particular a guide RANGE that CONTAINS the consensus point is `in_line` absent contrary wording (guide $2.66–2.72B vs Street $2.67B → in_line; a band wholly above/below → beat/missed). Logged 95 #42.
   - **Not a store-when-stated violation:** both operands are STATED; code may materialize `in_line` for wordless inside-range facts, and the producer may materialize `beat`/`missed` only as a grounded favorability classification. No number is fabricated. The beat/miss MAGNITUDE stays derived-at-read (DU-16.6 — no stored computed `change_value`); a source-stated surprise delta is stored only when stated and arithmetic sign is determinable.
   - **Safety (satisfies the one law):** the level is never lost (always on its home fact — metric for a reported actual, guidance for a forward guide, OD-21); ambiguous favorability becomes `unknown` instead of a wrong label; an over-eager surprise is cheap over-split. All structural validators still hard-fail. OD-13 removes only the old polarity-based directional hard-fail, which rejected correct lower-better facts. **No new machinery** — MF-02 separate-but-linked drivers + §10.6 governed-create for a missing `_surprise`.
   - **Voice/relay (news):** a relayed beat/miss (third-party outlet/analyst, not the company — most news "vs own guidance" phrasings are third-party) carries no `company_confirmed` (guidance-only); provenance = `source_type=news` + quote; the common consensus/own-guidance BLUR ("beating consensus and its own guidance" — LULU, LNTH) must be split by the producer into two comparisons. ISS-53 residual, unchanged.
   - **in_line materialization — ✅ APPROVED FULL (owner 2026-07-03):** `within-range → in_line` is materialized as a surprise fact just like beat/missed (a complete surprise series; "met guidance" is itself a signal). The C-lite variant (suppress in_line) was NOT taken.
   - **Adversarial pass (folded 2026-07-03, then OD-13 reframe-confirmed 2026-07-06):** the original pass confirmed that writing the surprise fact does not collide with the metric fact (different drivers → different ids, DU-19; it IS MF-02/03) and surfaced OBJ-1/OBJ-2/OBJ-3. OD-13 then stress-tested and replaced OBJ-3's higher-is-better arithmetic with the producer-favorability model (66 §0.R OD-13; 95 #31). Watch-item for part 2 (not a structural flaw): a producer must not attach full-weight verdicts to BOTH the metric and its own same-event surprise (near-duplicate causes) — grading is aggregate/no-sum (DU-23/24) so it's safe, but flag it in the producer contract.
   - **Scope note:** the range-comparator details + the favorability proof are PRODUCER-CONTRACT (part 2); Track B pins the structural principle — a producer-detected EXPECTATION comparison writes a surprise, the level lands on its home fact (metric for a reported actual, guidance for a forward guide — OD-21), TEMPORAL comparisons are metric changes, forward-guide-vs-own-prior routes to guidance while forward-guide-vs-consensus writes guidance + `guidance_vs_consensus` surprise (OD-21), expectation baselines live on the surprise fact, and OD-13 governs the surprise state. `[DU-05/06/08/09/10/16.2 · MF-02/03 · DU-15 · 66 ISS-16/OD-13 · 90 §A]`

## 12 §10.7 — period strictness + ISS-23 (start==end illegal -> instant; sentinel rules)
### [VERBATIM from 12_TrackB_FactPipeline.md lines 136-136]

7. **Period strictness + ISS-23 — ✅ APPROVED WITH PINS (owner 2026-07-03):** (a) a DriverUpdate item that sends period fields code cannot resolve, with NO explicit `sentinel_class`, **HARD-FAILS as a producer bug** — no quiet gp_UNDEF fallthrough (a scoped owner amendment to PER-11's ladder for driver items; the pure shared builder keeps its fallthrough for Guidance — 95 #23, PER-11 annotated); (b) `action_event`: sentinel periods **HARD-FAIL** unless a real stated action window/duration exists (which resolves to a dated period, not a sentinel); (c) ISS-23 normalization CONFIRMED — start==end duration is illegal input, the producer marks it instant. **Owner's distinction, pinned:** non-guidance facts with truly NO period stay `HAS_PERIOD`-less; GUIDANCE still requires either a real resolved period or an explicit sentinel.

## 12 FACT-26f — the FS-15 slice-kind ladder (serve verbatim)
### [VERBATIM from 12_TrackB_FactPipeline.md lines 100-100]

- **FACT-26f — FS-15 kind ladder (owner 2026-07-11; serve verbatim in EXP-5 packets):** per stated company part: (1) menu match (same meaning; the producer judges; code never near-snaps) → take the menu value + its kind (came from the frozen axis table; never reconsidered). (2) The same normalized label under two or more kinds in the menu with no selecting framing → `unknown:<value>`. (3) Prose-only, kind clear ("our X segment", "revenue in China", a named product) → coin `kind:value`. (4) Prose-only, two or more kinds reasonable → `unknown:<value>` — never guess; a guessed kind is a fake axis-grade confirmation. `unknown:` values enter the company menu, so later producers reuse them — one series per company, no fragmentation from honesty.

## 03 FS-15 — the producer's 4 outcomes per fact [LOCKED] + kind ladder
### [VERBATIM from 03_Slices_FactScope.md lines 120-123]

#### FS-15 — The producer's 4 outcomes per fact  `[LOCKED]`
- **Plain:** For each fact the producer picks a menu value, coins one, marks a real slice unknown, or omits the slice for whole-company. A quote-hash is only a last tie-breaker.
- **Rule:** (1) on menu → pick (code supplies kind + a free XBRL link); (2) real, off-menu → coin in-style (no link); (3) real slice but no kind fits → `unknown:value`; unknown XBRL axis (code-emitted sentinel path only) → `unknown:xbrlaxis_<hex_encoded_exact_axis_qname>__<normalized_member_value>` so two "Other" axes never merge; (4) whole-company / consolidated / total-company / no stated segment → omit slice. If two different facts in the same event still collide after all structured parts are set, add `quote_hash`.
- **Kind ladder (FS-15 clarification — owner 2026-07-11; mirrored in 12 FACT-26f, served verbatim in EXP-5 packets):** per stated company part: (1) menu match (same meaning; the producer judges; code never near-snaps) → take the menu value + its kind (came from the frozen axis table; never reconsidered). (2) The same normalized label under two or more kinds in the menu with no selecting framing → `unknown:<value>`. (3) Prose-only, kind clear ("our X segment", "revenue in China", a named product) → coin `kind:value`. (4) Prose-only, two or more kinds reasonable → `unknown:<value>` — never guess; a guessed kind is a fake axis-grade confirmation. `unknown:` values enter the company menu, so later producers reuse them — one series per company, no fragmentation from honesty.

## WorkOrder v1.9 §4 EXP-5 — the EXACT 34-field output list
### [VERBATIM from FableExperimentWorkOrder.md lines 635-641]

driver_name · driver_state · quote · level_low · level_high · change_value · comparison_low ·
comparison_high · comparison_baseline · value_text · conditions · company_confirmed ·
level_unit_raw · change_unit_raw · level_unit_kind_hint · level_money_mode_hint ·
change_unit_kind_hint · change_money_mode_hint · level_shape_hint · comparison_shape_hint · surprise_basis_hint ·
measurement_raw_spans[] · period_start_date · period_end_date · fiscal_year · fiscal_quarter ·
half · month · long_range_start_year · long_range_end_year · sentinel_class · time_type ·
period_scope · slice[]
