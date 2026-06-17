# RavenPack Event Taxonomy — full findings + comparison to our Drivers catalog

**What this is (plain):** RavenPack is a financial-news analytics vendor (now also "Bigdata.com"). Their **Event Taxonomy** is a mature, professional classification of "what kinds of events happen to companies/markets" — the closest external analog to our Driver/DriverUpdate ontology. This file (a) dumps everything we found about it, then (b) compares it to our catalog — same vs different — and (c) recommends what to borrow and why.

**Provenance:** multi-agent web hunt 2026-06-16 (5 source channels + targeted gap-fill). The 6-level hierarchy, the 13 entity types, the fact-level enum, and the 10-column taxonomy-file schema were **verified verbatim** against a local extract of the *RavenPack Analytics User Guide* PDF. The exhaustive ~7,400-leaf list itself is **gated** (not on the open web) — we captured the full *frame* (~85–90%) but only ~1–5% of the actual leaf names.

> ⚠️ **Coverage caveat:** structure + scale = HIGH confidence (verbatim). The closed top-level TOPIC list and the full leaf CATEGORY list live only in a login-gated CSV / API (see §1.7). Treat the leaf examples here as illustrative, not exhaustive.
>
> 📂 **Companion files (this folder):** `RavenPack_Taxonomy.md` (full taxonomy dump) · `RavenPack_categories_365.csv` (365 real leaf categories now pulled in — a concrete sample of the gated ~7,400).

---

## PART 1 — What RavenPack's taxonomy actually is

### 1.1 The hierarchy — 6 named levels (verbatim from the User Guide)

| # | Level | Definition (verbatim) |
|---|---|---|
| L1 | **TOPIC** | "A subject or theme of events. The highest level of the RavenPack Taxonomy." |
| L2 | **GROUP** | "A collection of related events." (~56 groups total) |
| L3 | **TYPE** | "A class of events, the constituents of which share similar characteristics." |
| L4 | **SUB_TYPE** | "A subdivision of a particular class of events." |
| L5 | **PROPERTY** | "A named attribute of an event such as a role." → renamed **ROLES** in the newer "Edge" product. |
| L6 | **CATEGORY** *(leaf)* | "A tag to label a particular type and property of an event." The unique canonical event name (e.g. `earnings-above-expectations`, `product-recall`). Indicator words (positive/negative, bullish/bearish) are appended so each CATEGORY is unique. **~7,000–7,400 of these.** |

Worked chain (the one fully-public mid-to-leaf example — TOPIC and PROPERTY not shown):
```
analyst-ratings (GROUP) > ratings-change (TYPE) > change-positive / change-negative (SUB_TYPE)
   > analyst-ratings-change-positive / analyst-ratings-change-negative (CATEGORY leaf)
```

### 1.2 Cross-cutting fields (on every event record — NOT hierarchy levels)

These are the most relevant part for us:

- **`FACT_LEVEL` = `fact` · `forecast` · `opinion`** (exactly 3, verbatim) — separates a reported result from guidance from commentary.
- **`SCHEDULED` = TRUE/FALSE** — anticipated (e.g. earnings date) vs surprise.
- **`EVALUATION_METHOD` = YOY | QOQ | MOM | LFL** — the comparison basis.
- **`EARNINGS_TYPE`** = reported · non-gaap · ex-exceptionals · adjusted · non-diluted · diluted-adjusted · diluted-reported · headline-basic · headline-diluted · consolidated · standalone.
- `MATURITY` (2-DAY … 40-YR), `REPORTING_PERIOD` (YYYY-Q1, FY-YYYY-Q1, …).
- Plus a numeric **Event Sentiment Score (ESS)** and relevance/novelty scores (their analytics layer).

### 1.3 The downloadable file (the full leaf list lives here)

"Event Taxonomy File" — a **10-column CSV**:
`TOPIC, GROUP, TYPE, SUB_TYPE, PROPERTY, FACT_LEVEL, CATEGORY, DESCRIPTION, SCHEDULED, VALID_ENTITY_TYPES`  (~7,000–7,400 rows).

### 1.4 Entity types — 13 (the full Guide table)

`COMP` Company · `ORGA` Organization · `ORGT` Org-Type · `PEOP` People · `POSI` Position (CEO/CTO/…) · `PLCE` Place · `PROD` Product · `PRDT` Product-Type · `CMDT` Commodity · `CURR` Currency · `NATL` Nationality · `TEAM` Sports-Team · `SRCE` Source.

### 1.5 The content (what's public)

**Top-level TOPICS** (themes; the closed list is gated): business/corporate · macro-economy · geopolitics · society · environment/ESG · war-conflict-security.

**Business / company-news GROUPS — all 20, verbatim:**
`acquisitions-mergers · analyst-ratings · assets · credit · credit-ratings · dividends · earnings · equity-actions · insider-trading · labor-issues · legal · marketing · partnerships · price-targets · products-services · regulatory · revenues · sanctions · stock-picks · stock-prices`

**Group event-share** (≈ % of all events; CloudQuant/Mariner dictionary): stock-prices ~17% · equity-actions ~14% · earnings ~13% · analyst-ratings ~11% · acquisitions-mergers ~10% · products-services ~9% · revenues ~5% · labor-issues/price-targets/partnerships ~4% each · legal ~2%.

**Macro branch** (academic appendices, NOT exhaustive): sovereign-debt · public-finance · retail-sales · consumer-confidence · housing · interest-rates · treasury-yield · durable-goods · consumer-spending · recession · GDP · CPI · PPI · trade-balance · exports · FX · employment · private-credit.

**Geopolitical branch:** terrorism · war-conflict · civil-unrest · natural-disasters · government · geopolitical-tension · trade-tensions · embargo/sanctions.

**ESG sub-taxonomy** (large): 3 pillars (Environmental / Social / Governance), **171 controversy categories, 625+ event types, 70+ sustainability concepts.** E.g. Environmental: airborne-emissions, biodiversity, pollution; Social: human-rights, child/forced-labor, layoffs, privacy, product-compliance; Governance: corruption, fraud, taxes, board, shareholder-rights, lobbying, anti-competitive.

**Earnings sub-taxonomy** (Edge "Earnings Intelligence" = earnings + revenues + dividends, 400+ categories): Earnings Up/Down/Positive/Negative/Unchanged, Estimate, Expectation, Guidance, Revision, Delayed, Misstatement, Probe, EBIT/EBITA (estimate/expectation/guidance), Operating-Earnings, Pre-Tax, Interest-Income.

**PROPERTY-level modifiers** (combine into the leaf string): roles (raters, plaintiffs, defendants, suppliers) · positions (CEO/CTO/Director) · indicators (bearish/bullish/overbought/oversold) · benchmarks (YOY/QOQ/MOM/LFL) · earnings-type · relationship (PRODUCT/OWNER) · fact-level.

### 1.6 Scale & editions

- 6 levels · **~56 GROUPS** (~36 named publicly; 20 business groups verbatim-complete) · **~7,000–7,400 leaf CATEGORIES** · 13 entity types · 12M+ named entities · history from ~2000.
- Equity sub-taxonomy grew ~1,000 → ~3,317 categories. Editions: Dow Jones · Web (19,000+ sources) · PR · Full. Product lines: RPA 1.0 / RPNA 4.0 (legacy) → **RavenPack Edge** (current; PROPERTY→ROLES) → **Bigdata.com** (LLM/MCP layer over the same taxonomy).

### 1.7 How to get the complete ~7,400-leaf CSV (all gated — none on open web)

1. **WRDS** (best for academic/institutional): wrds-www.wharton.upenn.edu → RavenPack → dataset **"RPA 1.0 – Mapping Files"** → *event taxonomy dataset* (institutional login or sample request).
2. **RavenPack/Bigdata Product-Area portal** → download the taxonomy `.csv` (subscriber/trial login).
3. **Taxonomy API** with an rpa/edge key — `RavenPack/python-api` or `r-api` `RP_APITaxonomy()` returns every row as JSON.

**Best public partial leaf source:** Brandt & Gao (2019, *J. Empirical Finance*) appendix, reproduced openly in arXiv 2105.08214 Table 5 and Monash WP21-2024. **Field-name source of truth:** `github.com/RavenPack/python-api` (`models/fields.py`). **Structure source of truth:** the RavenPack Analytics User Guide PDF.

---

## PART 2 — RavenPack vs our Drivers catalog

**Plain framing of the core difference:** RavenPack catalogs **what happened** (events + sentiment). Our Drivers catalog explains **why the stock moved** (causal attribution graded against the realized return). They overlap on the *vocabulary scaffold*; they diverge on *purpose*.

### 2.1 Concept-by-concept map

| RavenPack | Our Drivers | Same / Different |
|---|---|---|
| **TOPIC / GROUP** (subject themes: earnings, M&A, legal…) | **`fact_type`** (4 kinds: metric/guidance/surprise/action_event) + canonical name + `SAME_AS` rollup (the separate **fold pipeline** aggregates leaf→sector→global) | **Different axis.** RP groups by *subject*; we group by *kind of fact*. Both are top-down buckets, but ours is value-free KIND, theirs is content domain. |
| **TYPE / SUB_TYPE** | (no explicit level — the **Driver name** is the granular unit) | **Different.** RP has 2 middle layers; we collapse to one canonical Driver name + a `SAME_AS` rollup. |
| **CATEGORY** (leaf, ~7,400; name **+ baked-in indicator**, e.g. `earnings-above-expectations`) | **Driver name** (canonical, `same_store_sales`) — **state kept OUT of the name** | **Same spirit, opposite execution.** RP bakes direction into the leaf string → ~7,400 leaves. We deliberately keep direction in a separate field (our "no state in the name" rule) → fewer, more-reusable names + a `driver_state`. **Ours is leaner.** (Over-merge — the v2 failure — is held off *separately* by non-transitive `SAME_AS` dedup + the Refute merge-skeptic, **not** by state-in-field.) |
| **PROPERTY / ROLES** (indicators + benchmarks + roles, bundled) | split into **`driver_state`** (direction) + **`comparison_baseline`** (benchmark); **roles not modeled** | **Partial.** We split what RP bundles (good). We don't model roles (raters/plaintiffs) — out of scope for causes. |
| **`FACT_LEVEL` = fact / forecast / opinion** | encoded as **`fact_type=guidance`** (forecast) vs metric/surprise (fact); "opinion" gated out | **Different placement — RP's is cleaner here.** RP keeps the metric as ONE node and flags forecast-ness as an *orthogonal field*; we mint guidance as a *separate fact_type*. (See recommendation R1.) |
| **`EVALUATION_METHOD` = YoY/QoQ/MoM/LFL** (a pure *time-period* basis) | **`comparison_baseline`** = prior_year / sequential_period / consensus / previous_guidance | **Related, not a superset.** RP's axis is *which time period* (YoY≈prior_year, QoQ≈sequential_period); ours covers those two **and** adds two benchmark *targets* on a different axis (consensus, previous_guidance). RP's **MoM** and **LFL** have no analog in our locked enum (LFL≈same-store, which we coin as a driver *name*). |
| **`EARNINGS_TYPE`** (reported/adjusted/non-gaap…) as a field | GAAP-vs-adjusted lives in the **Driver name** (`adjusted_eps` ≠ `eps`) | **Different placement.** RP = field; we = name (dual-framing). Both valid. |
| **`SCHEDULED`** (anticipated vs surprise) | **no analog** | **RP has it; we don't.** Cheap candidate to borrow (R3). |
| **ENTITY taxonomy** (13 types, their own) | reuse the **existing graph** (Company / News / Report / Transcript nodes) | **Different scope.** They own entities; we lean on the existing graph. |
| **Event Sentiment Score (ESS)** + indicators | **`stock_impact`** (long/short) + the **realized return** (read-time, on Event→Company) | **Different.** RP scores sentiment of the *text*; we record the driver's directional push + grade against the *actual* move. |
| **(none)** — RP has **no causal attribution** | **`EXPLAINED_BY` edge:** `stock_impact` + `weightage` (standalone force) + `confidence` + `produced_mode`, graded vs the realized return | **The big difference — OUR differentiator.** RP tells you an event happened and its sentiment; it never says "this event caused X% of *this* stock's move, with this weight, this confidently." Our attribution layer has no RavenPack analog. |
| Curated, **closed**, human-maintained vocabulary | **empirical, LLM-coined, bottom-up, dedup'd** via `SAME_AS` | **Philosophical opposite.** A closed curated vocab is exactly what killed our v1 (82% reject on held-out). We coin from data and canonicalize. |

### 2.2 Where we are genuinely the SAME (and RP validates us)

- **Direction/state is a separate field, not part of the event name.** RP appends indicators precisely so the base event stays clean — independent confirmation of our `driver_state`-not-in-name rule (our locked "no state/period in the Driver name" rule).
- **Comparison basis is its own field** (`EVALUATION_METHOD` ↔ `comparison_baseline`).
- **A rollup with both a top-down aggregation view and bottom-up leaves** (their TOPIC>…>CATEGORY ↔ our fact_type + canonical name + `SAME_AS`, with the **fold pipeline** aggregating leaf→sector→global). RP proves this scales to ~7,400 leaves hands-off — encouraging for our ~1,000-driver target.
- **Identity = code-composed, modifiers separated from the base.** RP's leaf is `base + property`; ours is `name + state + numbers` keyed by code. Same instinct: don't fuse everything into one string.

### 2.3 Where we are genuinely DIFFERENT (by design, correctly)

- **Purpose:** RP = descriptive event catalog; Drivers = causal attribution engine. Everything downstream follows from this.
- **Closed vs open vocabulary:** RP curates; we coin empirically + dedup. Ours must stay open (closed = v1 death).
- **Leaf count:** RP ~7,400 baked-in leaves; we keep names lean and push polarity/magnitude into fields. Ours is deliberately smaller and less redundant.
- **The outcome is in the graph:** we hold the realized return (Event→Company) and grade verdicts against it, PIT/leakage-safe. RP has sentiment scores, not a per-event causal grade.

---

## PART 3 — Recommendations: what to borrow, what to skip, and why

### ✅ Borrow / seriously consider

**R1 — Reframe guidance with a `fact_level`-style flag (the strongest idea).**
RP keeps a metric as ONE node and flags `fact / forecast / opinion` orthogonally. Today we mint a *separate* `fact_type=guidance` with its own state lane. RP's pattern is a ready-made answer to our long-running guidance-vs-driver linking problem: a guidance mention and an actual-result mention could **share one driver identity** and differ by a `fact_level`-style field — instead of being two fact_types we then have to link. (Caveat: **not a one-field add** — guidance and metric use *different state lanes*, so merging would force a state-lane resolution.)
*Why it matters:* it could simplify the `MAPS_TO_GUIDANCE` work (no cross-fact_type linking if they're the same node at different fact_levels). *Honest trade-off:* this revisits a locked decision (guidance as its own fact_type + lane); evaluate whether `fact_level` **replaces** or **complements** fact_type before changing anything. Do NOT just bolt it on.

**R2 — Validate (don't change) `comparison_baseline` against `EVALUATION_METHOD`.**
RP's time-period basis maps onto two of our values (YoY≈prior_year, QoQ≈sequential_period); we add two benchmark *targets* on a separate axis (consensus, previous_guidance). RP's **MoM** and **LFL** have no analog in our locked enum — add **MoM** only if real data shows it; **LFL** is already handled as the `same_store_sales` driver name. (Don't claim our enum is a strict superset — it's a different axis.)

**R3 — Consider a `scheduled` (anticipated vs surprise) flag.**
Cheap, and the predictor genuinely cares: a scheduled earnings beat moves differently than an out-of-the-blue news shock. Could live on the Event or the DriverUpdate. Low-cost, real signal. Evaluate against real driver data before adding (our minimalism rule).

**R4 — Keep the field-separation discipline; RP is external proof you're right.**
Identity vs direction vs benchmark vs fact-level as *separate fields* is exactly RP's design and exactly our `name / driver_state / comparison_baseline` split. This is the single biggest "you already nailed it" — keep enforcing it (it keeps names lean + reusable; over-merge itself is prevented *separately*, by non-transitive `SAME_AS` + the Refute merge-skeptic).

### ⚠️ Borrow the SHAPE, not the content

**R5 — The 6-level rollup is a useful sanity check, not a thing to copy.**
Their ~56 mid-tier GROUPS and aggregation-view confirm a ~1,000-leaf catalog can stay navigable with top-down buckets. Use it to gut-check "how many top-level driver buckets should we expect," not as a structure to import.

### ❌ Do NOT borrow

- **The closed, curated ~7,400-leaf vocabulary or the leaf strings themselves.** We coin empirically and canonicalize; a closed vocab killed v1. RP is news-event-centric (what happened); we're causal (why it moved). Importing their leaves would drag us back toward event-cataloging.
- **Roles (raters/plaintiffs/positions), sentiment scores, the entity taxonomy.** Out of scope for "causes of a stock move."
- **Baking direction into the name.** RP does it (`earnings-above-expectations`); we deliberately don't. Keep state in the field.

### 🛡️ The thing to protect (our moat)

RavenPack has **no causal-attribution layer.** Our `EXPLAINED_BY` verdict (which driver, which direction, how much force, how confident, graded against the *realized* return, leakage-safe) is exactly what RP lacks and what makes the catalog *predictive* rather than merely *descriptive*. Borrow RP's vocabulary discipline; **do not** dilute the attribution layer by drifting toward their event-catalog model.

---

## One-line takeaways

- **Same instinct, leaner execution:** we separate direction/benchmark/identity into fields just like RP — and avoid their ~7,400 baked-in leaves.
- **Best single borrow:** RP's `fact_level` (fact/forecast/opinion) is a candidate simplification for guidance linking (evaluate vs our `fact_type=guidance`).
- **Our moat:** causal attribution (`EXPLAINED_BY` weightage/confidence graded vs realized return) — RP has nothing like it; protect it.
- **Full leaf list:** gated; pull via WRDS / Product-Area portal / Taxonomy API (need credentials).

*(Provenance: web hunt 2026-06-16; structure verified verbatim vs the RavenPack Analytics User Guide. Coverage ~85–90% of frame, ~1–5% of leaves. Comparison written against the in-session Drivers design, 2026-06-16.)*
