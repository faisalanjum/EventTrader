# 02 · DriverCatalog

**Track A — the DriverCatalog:** how a driver's NAME is coined, reused, and kept clean.
This file starts with the **naming rules** (NAME-01 … NAME-19). Later slices — the build pipeline, model choice — are added as their own locked pieces.

> Every rule below is **LOCKED** and traceable to its source doc. Where a rule replaced an older one, **Replaces** points into `95_Supersession.md`.

---

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
- **Why:** One consistent order means the same cause is always written the same way, so word-order variants collapse to one canonical name (NAME-02).
- **Source:** DriverOntology.md R3
- **Replaces:** old example `iphone_china_sales` (brand/geo now sliced) — 95_Supersession #1

#### NAME-07 — Familiar names win  `[LOCKED]`
- **Plain:** For well-known market/policy causes, use the familiar name, not an invented one.
- **Rule:** Use the familiar form: `fed_rate`, `yield_curve`, `oil_price`, `tariff_policy`, `fda_approval`.
- **Why:** Everyone already calls it the same thing → maximum reuse.
- **Source:** DriverOntology.md R5
- **Replaces:** —

#### NAME-08 — Keep standard financial phrases whole  `[LOCKED]`
- **Plain:** A standard phrase stays together as one name — don't split or reorder it.
- **Rule:** `gross_margin`, `free_cash_flow`, `net_interest_margin`, `same_store_sales` stay whole.
- **Why:** These are recognized units; splitting them makes non-standard, non-reusable names.
- **Source:** DriverOntology.md R6
- **Replaces:** —

#### NAME-09 — One cause per name (split multiples; short; a noun)  `[LOCKED]`
- **Plain:** One name = one cause. Two causes → two drivers. Keep names short and noun-like.
- **Rule:** A name carries exactly one cause. Two+ independent causes → a separate driver each, never bundled (`asset_impairment_and_lease_termination` → split). Keep names short; if it takes many words to be specific, it's probably two drivers. Reads as a noun.
- **Why:** Bundled names can't be tracked/reused and break one-name-one-meaning.
- **Source:** DriverOntology.md R2 / R8
- **Replaces:** —

### B. Name vs slice

#### NAME-10 — Brand/segment/geography/product/customer/channel → the slice, not the name  `[LOCKED]`
- **Plain:** The "which part of the company" detail goes in the slice tag, not the name.
- **Rule:** Brand, segment, geography, product, customer, channel → the SLICE. `taco_bell_same_store_sales` → `same_store_sales` + `slice=segment:taco_bell`.
- **Why:** The read-time series already partitions by slice + period; a part in the name would fragment the history and duplicate causes.
- **Source:** Naming_Slices_XBRL.md §2
- **Replaces:** old "brand = its own driver" (DriverOntology R9) — 95_Supersession #1

#### NAME-11 — When a brand/product DOES go in the name (the exception ladder)  `[LOCKED]`
- **Plain:** A brand/product enters the name only in rare cases — decided by a short top-down test.
- **Rule:** Ask in order, stop at the first hit:
  - **0.** Strip direction/impact words first (rose, headwind, generic pressure…) — never in the name. Exception: a word like `pressure` may stay only when it is part of a specific reusable market force (`glp1_pressure`), not a generic effect word.
  - **1.** Strip the brand. Normal cause left (revenue, a recall)? → YES → **SLICE** it.
  - **2.** Only a fragment needing an object (demand, ban), OR that exact brand/product itself moves OTHER companies? → YES → **NAME** it (`iphone_demand`, `glp1_pressure`, `tiktok_ban`).
  - Unsure → **SLICE**.
- **Why:** Default to slice (safe over-split); catch the real cross-company brand causes.
- **Source:** Naming_Slices_XBRL.md §2
- **Replaces:** —

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
- **Rule:** The version of a number (adjusted, diluted, basic, constant-currency, core, cash…) goes in the **measurement** slot INSIDE fact_scope — a sibling of the slice, NOT a 7th slice kind. `adjusted eps` → name=`eps`, measurement=`{adjusted}`. Store the specific stated word (case/whitespace/punctuation normalized); default empty (never assume gaap); gaap/non_gaap is a read-time view, never stored.
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
  4. any ticker/legal/person name *[OK: institutions/regulators as a cause: `fed_rate`, `opec_supply`, `fda_approval`]*
  5. period tokens
  6. numbers/sizes/bare units (`bps`, `percent`, `usd`)
  7. source-type labels
  8. provider/vendor labels
  9. XBRL prefixes
  10. metaphors/sentiment/effect-on-stock words *[OK only when the word is part of a specific reusable market force, e.g. `glp1_pressure`; generic "pressure" stays banned]*
  11. a bare category word alone (`macro`, `sector`, `demand`, `sentiment`)
  12. vague descriptors too broad to name a cause
  13. glue words (`the`, `of`, `in`, `and`, `to`, `for`)
- **Why:** Each has its own field; in the name they break reuse and one-name-one-meaning.
- **Source:** DriverOntology.md R7
- **Replaces:** —

### D. Family, gate & meta

#### NAME-17 — Metric-family suffix stays in the name  `[LOCKED]`
- **Plain:** For earnings, the `_guidance` / `_surprise` suffix stays in the name; fact_type is separate.
- **Rule:** Name metric + mechanism: `{metric}_surprise` (actual vs expected), `{metric}_guidance` (forward outlook) — `eps_surprise`, `revenue_guidance`. Suffix stays in the name AND fact_type is a separate permanent field. The base `{metric}` is a separate driver linked by `BASE_METRIC` (never same-as). Beat/miss/raised → driver_state, never the name.
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
- **Replaces:** —

<!-- The later slices now live in 10_BuildPipeline.md (the Track A manual, 2026-07-02): the build pipeline + G1/G2/Refute gates (10 §2–§3), point-in-time safety (10 PIPE-34), and model choice (10 §7). -->
