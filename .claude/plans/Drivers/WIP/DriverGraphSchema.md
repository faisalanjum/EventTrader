# DriverUpdate — Node Spec

**Status (2026-06-14): core node/edge STRUCTURE locked (Design C). The `Driver` class fields are FINALIZED; the `DriverUpdate` `driver_state` field is FINALIZED (name + vocabulary, 2026-06-16); the number/comparison layer (`level_*`/`change_*`/`comparison_*` — names + shape + store-when-stated) is AGREED (2026-06-16); the `EXPLAINED_BY` verdict layer is also AGREED (2026-06-16). (Field/property layers are settled; the **Deferred** + **SUGGESTION-ONLY** items below — structural/identity questions, optional links, the guidance section — remain open.) Nothing built — 0 `Driver` / `DriverUpdate` nodes in Neo4j.** This file records what is fully decided, plus clearly-labeled **Deferred** and **SUGGESTION-ONLY** sections (the latter explicitly NOT decided). (Owner-approved to write this one file; no other files touched.) **Update 2026-06-15 — the DriverUpdate CREATION CONTRACT is now locked: see §0 (catalog build = the complete Driver class [name + `fact_type` + optional links] in ONE run · producers create every DriverUpdate · no build-time seeder).**

---

## 0. DriverUpdate creation contract — LOCKED 2026-06-15 (read first; do not reopen)

**Owner-approved over a multi-round brainstorm (2026-06-15). This is the AUTHORITY: if any wording below (an older "= a change" phrasing, the §1 table, §7) ever seems to conflict, THIS section wins.**

**In three lines:**
- **Catalog build = builds the complete Driver CLASS** (name from filings/transcripts/8-Ks/KPIs · `fact_type` · optional links — all in ONE run). It never creates a DriverUpdate.
- **Producer = decides real event-level FACTS and creates the DriverUpdates** (earnings-learner / news-driver).
- **Backfill = running that same producer over old events** — the only "seeding" path.

**The 8 locked points:**
1. **Catalog build creates the Driver CLASS, never a `DriverUpdate`.** In ONE run it uses non-news sources (filings, transcripts, 8-Ks) + fiscal.ai KPIs to **create/reuse `Driver` names**, then as **final steps** assigns each Driver's **`fact_type`** (mandatory) + **optional XBRL/guidance links** (best-effort). It **never creates a `DriverUpdate`** (that is the producer — points 3–5).
2. **A `DriverUpdate` = a real event-level FACT about a Driver** — a reported **state, change, surprise, guidance item, or action**. It is **NOT a mere mention.** *(Supersedes any narrower "= a change" wording: a CEO resignation, FDA approval, guidance cut, strike start, or store closure is a valid fact with no "X→Y" change.)*
3. **Producers are the ONLY creators of `DriverUpdate`s** — both **live** processing and **historical backfill**.
4. **KPI-only evidence never creates a `DriverUpdate`.** A fiscal.ai KPI can create/reuse a **name** only (no `Event`, no date, no move).
5. **No separate build-time seeder / change-detector.** It would be a **second source of truth** that could disagree with the producer (it lacks the producer's prior-period memory + consensus data) → a silent accuracy risk + a permanent sync burden. Forbidden.
6. **No ">2 events" write rule.** A **single event** can be a valid fact (CEO resignation, FDA approval, guidance cut, strike began, store closure). Recurrence stays a **read-time** view (§6), never a write-time gate.
7. **Want early history? Run the same producer over past events (a backfill).** That gives the "seeding" benefit with **one source of truth and zero duplicate logic** — the correct, accurate version of "seed at build time."
8. **`EXPLAINED_BY` is separate.** The **`DriverUpdate`** says *the fact happened*; the **`EXPLAINED_BY`** edge says *the producer believes that fact caused the stock move*. A fact may exist with no verdict.

**Tensions resolved (logged so this is never reopened by accident):**
- *"The build already sees the quote ('revenue grew 12%') → seed a DriverUpdate for free."* → **No.** The reader extracts **mentions/names**, not fact-judgments; turning a mention into a fact needs producer-grade judgment (state, `fact_scope`, consensus). A separate pass = point 5's second source of truth.
- *"Only seed drivers with >2 events."* → **Dropped** (point 6): single events are valid facts.
- *"DriverUpdate = a change."* → **Widened** to "a real event-level fact" (point 2): actions are not X→Y changes.
- *Mention vs fact:* the build's `evidence_refs` are **mentions** (they justify a name); a **`DriverUpdate`** is the stricter **event-level fact** a producer judges from a real event.

---

## Plain what / why

- A **`Driver`** is a reusable named cause (`same_store_sales`, `oil_price`) — the **class**. Built by the catalog pipeline; optionally linked to XBRL / Guidance nodes.
- A **`DriverUpdate`** is one **fact**: *"on this event, this driver did X"* (a real event-level fact — state/change/surprise/guidance/action — + its size + the quote; never a mere mention, §0). The **instance**.
- The **verdict** — *"this event's stock move is attributed to this driver-fact, this way, this much, this confidently"* — is **not a node**. It is a property-laden **edge** (`EXPLAINED_BY`) that runs **from the `Event` to the `DriverUpdate`**.
- **Company is NOT in the driver layer at all.** The company + its return are reached purely through the existing **`Event → Company`** edge (one company per event, verified). A market-wide driver (`oil_price`) takes the exact same shape — no company, no special case.

**Why the verdict points at the Event, not the Company:** the verdict exists to be **graded against the realized return**, and that return lives on the `Event → Company` edge. A company has hundreds of thousands of return edges, so it can't say *which* move a verdict refers to — the **event** does. So the verdict belongs on the event, one hop from its grade. This also removes a redundancy (the company is already pinned by the event) and needs no macro special-case.

This mirrors the **Guidance** pattern (class node + per-event instances, code-built identity, value-hash, merge-in-place), which runs in production at **548 `Guidance` + 8,432 `GuidanceUpdate`** nodes.

## The shape (high-level)

```
            ( :Driver )
                ▲
                │ OF_DRIVER
          ( :DriverUpdate )
            │          ▲
       FROM_SOURCE     │ EXPLAINED_BY { the verdict }   ← only when attributed
            ▼          │
            ( :Event )─┘
                │
                │ INFLUENCES / PRIMARY_FILER { returns }   ← the real stock move
                ▼
            ( :Company )
```

`FROM_SOURCE` (fact → event) = *"this fact came from this event."*
`EXPLAINED_BY` (event → fact) = *"this event's move is explained by this fact."*
**Two separate edges, opposite directions — never one overloaded edge.**

## 1. The pieces (decided)

| Piece | What it is | Built by |
|---|---|---|
| `Driver` (node, class) | the reusable named cause; name + `fact_type` + reversible `SAME_AS` edges (exact-duplicate names; both nodes survive) + optional XBRL/guidance link **on the class** | catalog pipeline |
| `DriverUpdate` (node, instance) | one per-event **fact** about a driver (state/change/surprise/guidance/action + size + quote — never a mere mention) | **a producer ONLY** — live or backfill; never the catalog build (§0) |
| `EXPLAINED_BY` (edge `Event → DriverUpdate` = the verdict) | the causal verdict, in the edge's properties | a producer, only when a stock move is judged |
| `Event`, `Company` (existing nodes) | the source + the company; the **return** lives on the `Event → Company` edge | the existing pipeline |

## 2. Fields

> ⚠️ **Property-meanings pass IN PROGRESS.** The **`Driver`** fields in the table below are **finalized** (incl. `fact_type`, whose 4-value enum + definitions were LOCKED 2026-06-15 — see the fact_type lock section). The **`DriverUpdate`** `driver_state` field + the number/comparison layer **and** the **`EXPLAINED_BY`** verdict layer are all **agreed** (2026-06-16).

**`Driver`** (the class — FINALIZED)

| field | what it means | keep |
|---|---|---|
| `id` | code-built stable key (e.g. `driver:same_store_sales`) | ✅ |
| `name` | the lower_snake `driver_name` of THIS node — a `SAME_AS` head IS the canonical name; a `SAME_AS` variant node keeps its own name | ✅ |
| `created` | when the driver first appeared | ✅ |
| `definition` | a plain one-line meaning of the driver — **optional / nullable** | ⚪ |
| `fact_type` | the driver's permanent KIND — one of `metric` / `guidance` / `surprise` / `action_event` (routes the DriverUpdate `driver_state`; enum + definitions LOCKED 2026-06-15 — see the fact_type lock section) | ✅ |

**`SAME_AS` lives as an EDGE between `Driver` nodes (NOT a property — see §3):** exact-duplicate driver names stay as SEPARATE `:Driver` nodes (each keeps its OWN evidence via its own `DriverUpdate`s) joined by a reversible `(:Driver)-[:SAME_AS]->(:Driver)`. **No `aliases` property** (a flat array couldn't hold each variant's evidence).
**Excluded:** no `evhash16` on the class (it is never re-extracted → nothing to change-detect; Guidance's anchor has none either).
**Optional links (edges, an OPTIONAL best-effort FINAL step of the catalog-creation run — non-blocking; self-heal on re-run):** `Driver-[:MAPS_TO_CONCEPT]->Concept` · `-[:MAPS_TO_MEMBER]->Member` · `-[:MAPS_TO_GUIDANCE]->Guidance`.

**`DriverUpdate`** (the fact)

| field | what's decided | structural role decided? |
|---|---|---|
| `driver_state` | the driver's event-level **state/outcome** for this fact (not only a direction); lives here, **never in the name** | ✅ name FINAL + vocabulary LOCKED (see the *fact_type + state-words* section, item 2) |
| number + comparison fields — `level_low` · `level_high` · `level_bound` · `level_unit` · `change_value` · `change_unit` · `comparison_low` · `comparison_high` · `comparison_baseline` | the **driver's own** number/size + the stated prior baseline for this fact (NOT the stock effect) — **all nullable** (full spec in the *fact_type + state-words* section, item 3) | ✅ names + shape + store-when-stated AGREED 2026-06-16 |
| `quote` | verbatim source text; stored ONLY when the source gives a real state/value/change (never a bare mention) | ✅ |
| `source_type` · `date` · `created` | provenance · statement-time · write/merge-time | ✅ |
| `fact_scope` | which *version* of this driver-fact inside the event (period / segment / geography / store-type, or a normalized-quote hash) — part of the key; **identity-only, never in `Driver.name`** | ✅ |
| `id` · `evhash16` | code-built key + value-hash (see §4); **no producer in the key** | ✅ |

**`EXPLAINED_BY`** (the verdict — properties on the `Event → DriverUpdate` edge; verdict names + scales **FINAL 2026-06-16**)

| field | what it means | values |
|---|---|---|
| `stock_impact` | the driver's **DIRECTION** of push on this event's move (can oppose the net move) | `long` · `short` |
| `weightage` | the driver's **standalone FORCE / importance** in the move — an *independent* estimate, **NOT a share** (never summed, never forced to its max; a move may be partly unexplained) | `0–1` in **deciles** `{0.1, 0.2, … 1.0}` · **nullable** |
| `confidence` | how **sure** the producer is the attribution is **true** (orthogonal to `weightage`) | `0–100` in **deciles** `{0, 10, … 100}` |
| `produced_mode` | judged in **real time** (PIT-clean) vs a later **re-run** (possible hindsight) | `live` · `backfill` |
| `llm_producer` | who judged | `earnings-learner` · `news-driver` |
| `id` · `created` · `evhash16` | code-built key (**producer IS in the key**, see §4) · write-time · value-hash of (`stock_impact`,`weightage`,`confidence`) — stable under sibling edits | code-built |

**Verdict rules + read-time views (decided 2026-06-16):**
- **Three orthogonal axes** — `stock_impact` = direction · `weightage` = magnitude · `confidence` = certainty; none derivable from another.
- **`weightage` is independent — NO cross-edge sum constraint.** Adding or re-judging one driver **never rewrites a sibling's** `weightage` (clean per-edge MERGE; `evhash16` flips only on a real change to *that* edge).
- **`weightage` nullable (abstain):** sure of *direction* but can't *size* it → `weightage` = `null`. **Never auto-set a sole driver to its max** — a move can be partly unexplained (market / sector / noise).
- **Read-time only (never stored):** `share_i = weightage_i / Σ weightage_j` within one `(event, producer)`; `signed_force = weightage × stock_impact`.
- **PIT:** the *realized* share / actual return is **never stored** on the verdict and **never shown to the predictor** — computed at read time from the `Event → Company` return.
- **Grading is aggregate:** reality gives **one net return** → grade a verdict set on net sign/magnitude + relative ranking, never a per-driver "true share."
- **`produced_mode` — live wins:** a `backfill` verdict NEVER overwrites an existing `live` verdict at the same key (live is PIT-clean; backfill ran after the move was known); a `live` write may replace a `backfill` one. `produced_mode` is provenance → **excluded from `evhash16`** (a live↔backfill swap is not a judgment change).
- **Validator (deterministic · hard-fail):** every edge has `stock_impact` ∈ {long, short}, `confidence` ∈ `{0, 10, … 100}`, and `weightage` ∈ `{0.1, 0.2, … 1.0}` or `null` — **both deciles** (a 10-step ladder: no false-precision floats, keeps `evhash16` stable across re-runs); **no sum constraint.**

## 3. Edges (decided)

| edge | from → to | meaning | when |
|---|---|---|---|
| `OF_DRIVER` | `DriverUpdate` → `Driver` | this fact is an instance of this driver | always (exactly 1) |
| `SAME_AS` | `Driver` (variant) → `Driver` (head) | the two names are the SAME reusable cause; reversible, both nodes survive | when reconcile/repair confirms EXACT-same meaning (0..1 out per node) |
| `FROM_SOURCE` | `DriverUpdate` → `Event` | this fact came from this event (evidence) | always — every `DriverUpdate` is event-sourced |
| `EXPLAINED_BY` {verdict} | `Event` → `DriverUpdate` | this event's move is explained by this fact | 0, or 1 per producer |
| `INFLUENCES` / `PRIMARY_FILER` {returns} | `Event` → `Company` | the realized stock move (existing edge) | existing |

- **`SAME_AS` is reversible and STAR-shaped** — a variant points to its canonical head only (**no chains**, never re-points the head, **never a destructive node merge**); the head is self-canonical (no outgoing `SAME_AS`). Read-through / trading **follows `SAME_AS`** to the head and unions the star's evidence + `DriverUpdate`s. Mirrors the catalog's `canonical_name` pointer + the root's `same_as_variants[]`, so each variant keeps its OWN evidence (never flattened into one node).
- **`FROM_SOURCE` and `EXPLAINED_BY` are SEPARATE edges** (a fact can be *reported* in an event without *explaining* its move) — never collapse the verdict onto the provenance edge.
- **No `BASED_ON`.** Trends are **queried** (each fact's `driver_state` gives the state/outcome and its number fields — level/change/comparison — the value), never stored as links.
- **The same event-level fact reported in different events** = **separate `DriverUpdate`s** (keyed by event); collapsed in **read-time views**, never in storage.
- **Multiple producers** (if the one-producer-per-event invariant ever breaks) → **parallel `EXPLAINED_BY` edges keyed by producer** — supported here (the DB already runs relationship-uniqueness constraints with composite keys).
- **Scoring** a verdict is local to the event: at the `Event`, its `EXPLAINED_BY` verdicts and its `INFLUENCES`/`PRIMARY_FILER` return both hang off the same node — compare directly.

## 4. Identity & change-tracking (decided — the Guidance recipe)

- **Code builds every key; the AI never does.** Each key carries a uniqueness constraint; re-running a producer **MERGEs in place** (overwrite) — never forks.
- **Fact key** = **event + driver + `fact_scope`**. **No producer** → two readers of the same source-fact converge to ONE `DriverUpdate`. *(`fact_scope` prevents silent loss when one event states the same driver more than once — e.g. a May 10-Q reporting Q1 same-store-sales `+3%` AND April month-to-date `−1%`: same event, same driver, same filing date, two facts.)*
- **Verdict key** = **event + driver + `fact_scope` + producer**. **No company** (derivable from the event). `fact_scope` ties the verdict to the *exact* fact; **producer is in the key** so two producers can disagree without colliding.
- **`fact_scope` = "which version of this driver fact inside the event."** Choose in this order: **(1) a structured scope** if the source gives one — period / segment / geography / store-type; **(2) `hash(normalized quote)`** only when no clean scope exists. *(Structured first because it correctly MERGES restatements of the same fact — e.g. press-release + MD&A both saying "Q1 +3%" → one fact; a raw quote-hash would over-split them.)* Like Guidance's `period`/`segment`, the AI supplies the dimension as data and **code composes the key**.
- **`fact_scope` is identity-only — it NEVER enters `Driver.name`** (R7: no periods/segments in names). `same_store_sales` stays ONE driver; the Q1-vs-April distinction lives in the key, not in two driver names.
- **`evhash16`** is a value-hash — a **property, never part of the key**. Fact = hash of the fact payload; verdict = hash of (`stock_impact`, `weightage`, `confidence`). It flags when a value actually changed (vs a no-op re-run).

## 5. What this rests on (verified / invariant)

- **One company per event** — verified live: News **348,669** · Reports **42,243** · Transcripts **9,608**, all **exactly 1 company**. So an event uniquely names its (company, move); the company is a downstream lookup, never stored on the driver layer.
- **One producer per event** — design invariant (earnings events → earnings-learner; news → news-driver). If ever violated, the parallel-edge case in §3 applies.
- **The realized stock move lives on the existing `Event → Company` edge** (`INFLUENCES` / `PRIMARY_FILER` {daily_stock}) — never on a driver node.
- **XBRL / guidance links live on the `Driver` class**, not per instance.

## 6. Persistence (decided)

Every `DriverUpdate` is **persisted, including a driver's first appearance** — the schema allows even a single one. Any "only surface drivers seen N+ times" recurrence threshold is a **read-time / display filter**, never a write-time drop, so nothing is lost and re-runs stay deterministic.

## 7. How the catalog build feeds this

The catalog build **only creates/reuses `Driver` names** (the class) — it **never mints a `DriverUpdate`** (the locked contract, §0). Its `evidence_refs` (driver · company · event · date · quote — KPI-only evidence has no real `Event`/date and never feeds a `DriverUpdate`, §0 point 4) are **mentions** that justify and let producers reuse a name; they are **not** event-level facts and carry no `driver_state` / number fields. The **producers** (earnings-learner / news-driver) are the sole creators of `DriverUpdate`s — judging the real event-level fact + its state/size, and (when attributed) the `EXPLAINED_BY` verdict — in both **live** processing and a **historical backfill** over the same source events. To populate history early, run the producer as a **backfill** (§0 point 7); do **not** add a build-time detector (§0 point 5).

## 8. Full shape (annotated — *all `Driver`, `DriverUpdate`, and `EXPLAINED_BY` field names are final/agreed (2026-06-16)*)

```
                ┌──────────────────────────────────────────────┐
                │ ( :Driver )   — reusable cause (the "class")    │
                │    id  "driver:<slug>" · name "same_store_sales"│
                │    fact_type  permanent KIND (4 values, §2)     │
                │    ─[:SAME_AS]→ head (edge, §3)        │
                │    (+ optional XBRL/guidance link ON THE CLASS) │
                └────────────────────▲──────────────────────────┘
                                     │  :OF_DRIVER  (always · 1)
   ┌─────────────────────────────────┴───────────────────────────────────┐
   │ ( :DriverUpdate )   — the FACT ("what the driver did this event")      │
   │    id  code-built: event + driver + fact_scope   (NO producer)        │
   │    evhash16  value-hash of the fact payload                           │
   │    driver_state     state/outcome     (NEVER in the name)             │
   │    level_* / change_* / comparison_*  driver's OWN numbers (nullable) │
   │    fact_scope  which version of the fact in this event (key part)     │
   │    quote · source_type · date · created                              │
   │    ⚠ ALL field NAMES FINAL — driver_state · number/comparison · verdict (2026-06-16) │
   └────┬─────────────────────────────────────────────────────▲──────────┘
        │ :FROM_SOURCE  (always — "fact came from event")       │
        │                                  :EXPLAINED_BY  ──────┘  (event → fact; 0, or 1 per producer)
        │                                  { the VERDICT, on the edge:
        ▼                                    stock_impact · weightage · confidence
   ┌─────────────────────────┐               llm_producer · id · created · evhash16 }
   │ ( :Event )              │
   │   :News|:Report|        │── INFLUENCES / PRIMARY_FILER {daily_stock} = REAL move ──► ( :Company )
   │   :Transcript           │                                                            id="<cik>"
   │   id = "<event id>"     │                                                            ticker="CAKE"
   └─────────────────────────┘
```

**Notes baked in:** verdict & return both hang off the `Event` (score in one hop) · fact key = event+driver+fact_scope, NO producer (same fact → one node) · verdict key = +producer (two producers won't collide) · no company anywhere in the driver layer (reached via the event) · re-runs MERGE in place (`evhash16` flags a real change).

---

## fact_type + state-words — LOCKED 2026-06-15  ·  number layer (DriverUpdate) — names/shape AGREED 2026-06-16

> Output of the property-meanings pass, grounded in a census of EVERY real Fable driver record (CAKE 594 + 14-ticker 673 + raw menus). **The `fact_type` block AND the per-update `state` lists below are LOCKED (2026-06-15; fact_type validated on 1,282 driver names, states on 3,825 evidence quotes); the number layer (level/change/comparison) is now AGREED 2026-06-16 (item 3).** **Core principle:** the state words are *helper buckets* for grouping/querying; the verbatim **`quote` is the truth** — so the enum can stay small and the quote carries precision.

**Why a routed enum (not one flat list):** the real data breaks a single up/down list — ~1 in 6 facts have no up/down (risk talk, plain snapshots, "stabilized", guidance ranges). So state is **routed by the driver's kind**, and a producer-side **GATE** (per §0: does this event carry a real fact about the driver — state, change, surprise, guidance, or action? a bare mention → write NO DriverUpdate) removes the no-fact pile.

**1. `fact_type` — on the `Driver` — LOCKED 2026-06-15.** The driver's **permanent KIND**, set ONCE at catalog time (never per event). It **routes** the per-update `state` vocabulary (§2 below) and lets the predictor group facts by kind. **Validated on all 1,282 real driver names: 0 fit none; every "merge to 3" and "add a 5th" attempt failed for a concrete reason.** **Exactly 4** (value-free — no state/direction in it):

| `fact_type` | what the Driver is | examples |
|---|---|---|
| `metric` | **any standing variable readable again over time** — a numeric metric, cost, price, rate, count, ratio, **OR a qualitative condition** (weather, sentiment, regulation/policy in force, labor availability, brand reputation). NOT only a number. | `same_store_sales` · `commodity_cost` · `consumer_sentiment` · `tariff_policy` · `adverse_weather` |
| `guidance` | the company's own **forward-looking** outlook / target / forecast for a future value | `eps_guidance` · `revenue_guidance` · `capital_expenditure_guidance` |
| `surprise` | an **actual result vs an EXPECTATION** (consensus OR the company's own prior guide/target) — **not** vs a prior-period actual (that is a `metric` change) | `eps_surprise` · `revenue_surprise` |
| `action_event` | a **discrete thing that happened** — a decision, transaction, incident, approval, or one-off charge | `dividend` · `share_repurchase` · `restaurant_closure` · `ceo_succession` · `asset_impairment` |

**Locked principles:** `metric` = a standing variable/condition readable across time · `guidance` = company forward outlook · `surprise` = actual vs expectation (NOT prior-period) · `action_event` = a discrete thing that happened.

**The `metric` ↔ `action_event` decider — the PERSISTENCE test:** between two events, is there a **standing level/severity you could re-read** ("what is it now vs before?")? **Yes → `metric` · No → `action_event`** ("did it happen / get canceled?"). A `_surprise` or `_guidance` framing overrides to those types.

**Dual framing is allowed** — the same topic may be TWO Drivers of different kind, classified by the NAME's framing (not the topic): `dividend` (action_event) AND `dividend_per_share` (metric); `flower_child_acquisition` (action_event) AND `acquisition_expenses` (metric).

**Bare-root defaults** (the few names that read both ways — default to the standing bucket unless the name is clearly one event): `litigation` · `convertible_notes` · `dividend_policy` · `restructuring_costs` → `metric`; `corporate_restructuring` · `asset_impairment`/writedown → `action_event`.

**WHEN it is set — a FINAL STEP of catalog creation, in the SAME run (NOT a separate later pass):**
A Driver is **born complete** in one catalog-creation run — identical for the **initial batch build, an incremental refresh run, AND a live producer minting a new Driver on the fly** (which is exactly *why* it is one run, not a deferred pass: live producers have no separate downstream pass):
> 1. **Name** — the blind reader extracts candidate names (recall-critical; **names only**).
> 2. **… reconcile / assemble** — the catalog of finalized names is built.
> 3. **`fact_type` — MANDATORY final step** — a per-Driver judgment over each finalized name + evidence, assigned by a **STRONG model (Opus)**, not the blind reader or a weak/cheap model (locked 2026-06-16). Validation: Opus was stable and correct on **28/28 keyed cases plus all reads-both-ways program cases**; the weak model wobbled. Cost stays trivial because this runs **once per `Driver`, not per event**. Keep the 4 definitions as written; **add no extra rules/clauses/examples** — a tested clause overfit by fixing two cases and breaking one. Separate classifier; no source re-read.
> 4. **XBRL/guidance links — OPTIONAL, best-effort final step** — attached only on a confident resolver match; failures **never block** the catalog and **self-heal on re-run**.

So catalog creation outputs the **complete Driver CLASS** (name + `fact_type` + optional links) in ONE run — still **NO `DriverUpdate`s** (those are the producer's job: live + backfill, §0). `fact_type` is set ONCE per `Driver` and is permanent; the *changing* `driver_state` lives on the `DriverUpdate`; never put state/direction in `Driver.name` (R7).

> ✅ The 4 `fact_type`s **AND** the per-update `state`-word lists (§2 below) are now LOCKED (2026-06-15; fact_type validated on 1,282 driver names, states on 3,825 evidence quotes). The **number layer** (level/change/comparison) is now AGREED 2026-06-16 (item 3).

**2. `driver_state` — on `DriverUpdate` — name FINAL + vocabulary LOCKED 2026-06-15** (validated on 3,825 real evidence quotes; set by the PRODUCER when it makes a DriverUpdate, never during catalog creation). Chosen from the driver's `fact_type` lane; `unknown` is the rare last resort; the raw `quote` is always the truth.

| `fact_type` | `state` — pick one |
|---|---|
| `metric` | increased · decreased · unchanged · mixed · reported · persists · unknown |
| `guidance` | introduced · raised · lowered · reaffirmed · withdrawn · unknown |
| `surprise` | beat · in_line · missed · unknown |
| `action_event` | at_risk · announced · occurred · continued · resolved · canceled · suspended · rumored · failed · unknown |

**Plain meanings (the non-obvious ones):**
- **metric — pick the FIRST that matches** (this order removes all ambiguity; *ignore good/bad — that is `stock_impact`*):
    1. **Direction stated** for the named variable (up/down · grew/fell · more/less) → `increased` / `decreased`  *("adverse weather worsened" → `increased` = MORE of it, even though bad).*
    2. **The SAME Driver moved up in some parts AND down in others** → `mixed`. Two *different* Drivers moving opposite ways is **NOT** `mixed` — split them  *("menu_pricing +9%, menu_mix −5%" = two drivers, each its own state).*
    3. **Explicit flat / steady / same-as-before number** → `unchanged`  *("sales remained flat").*
    4. **Ongoing condition still active, no up/down** → `persists`  *("commodity pressure remains elevated").*
    5. **Bare value, no comparison and no direction** → `reported`  *("AUV was $12.2M").* If a comparison exists, use `increased`/`decreased`  *("AUV $12.2M vs $11.8M" → `increased`).*
    6. **A real metric fact but no readable state** → `unknown`.
- **guidance:** `introduced` = first time · `raised`/`lowered` = the prior guide moved up/down · `reaffirmed` = kept the same · `withdrawn` = pulled.
- **surprise:** `beat`/`in_line`/`missed` vs the **expectation = consensus or the company's own prior guide/target** (NOT a prior-period actual — that is a `metric` change).
- **action_event:** `at_risk` (see strict rule) · `announced` = the company *decided/plans* it, not yet done · `occurred` = it happened (incl. a deal **closed/completed**) · `continued` = still ongoing · `resolved` = ended/settled · `canceled` = called off · `suspended` = paused · `rumored` = a third-party-reported possible action/transaction the company has NOT confirmed (a denial keeps it `rumored`) · `failed` = an attempted event ended **involuntarily** (an outside party blocked/rejected it, or an external condition went unmet) — distinct from `canceled` (the company's OWN withdrawal).

**Cross-type routing rule (prevents mis-bucketing):** outlook verbs — "expect / anticipate / target / plan to ___" — route to **`guidance`** (reaffirmed/raised/lowered), **never** a `metric` state. *(The metric direction/level/condition rules now live in the metric ladder above.)*

**`at_risk` — STRICT rule (or it floods):** use ONLY for a **specific, current, source-flagged possible ADVERSE event that has NOT happened and is NOT the company's own plan**. A *planned* action (a closure the company intends, an authorized buyback) is `announced`, not `at_risk`. **Generic risk-factor boilerplate** ("litigation could harm us", "weather may affect results", "cyber incidents could occur") is a mention → the gate drops it, **NO DriverUpdate** (§0). *(`rumored` vs `at_risk`: `rumored` = an unconfirmed possible ACTION the company hasn't confirmed; `at_risk` = a source-flagged adverse THREAT not yet realized.)*

*(`narrowed` is NOT a state — it is derived from the comparison fields below. The metric word is `persists`, NOT `continued` — `continued` collides with "continued to grow/decline" and would steal directional cases from `increased`/`decreased`.)*

**`action_event` — producer decision ladder.** *(Domain-neutral — THIS ladder is the runtime producer-prompt material; copy ONLY this. The LOCKED / validation / Borrow notes elsewhere are documentation and must NEVER be pasted into the prompt — that would re-introduce domain anchoring.)* When a producer assigns an `action_event` state it follows this ordered procedure (reason through it; do NOT keyword-match):
- **Scope:** classify only a discrete corporate ACTION. A guidance/outlook fact or a recurring-metric fact is another lane — route there.
- **Step 0 — precedence:** classify the LATEST stage of one action (an early rejection followed by a continuing pursuit = still OPEN, not `failed`; a vague "explore other options later" does NOT make a just-cancelled plan `continued`); if two actions, take the primary; classify the lifecycle, never good/bad.
- **Step 1 — finality gate:** TERMINAL (executed/completed, or over and unable to proceed without a NEW attempt) vs NOT-TERMINAL (only planned, a third-party rumor, a live/probable threat, a resumable pause, or simply ongoing).
- **Terminal →** `failed` (ended involuntarily — an outside party blocked/rejected it, or a required external condition/test went unmet; incl. declining an external offer never committed to) · `canceled` (the company ended its OWN committed action by free choice, no external cause; decided now even if effective later) · `resolved` (a two-sided dispute settled — counts even if payment steps remain) · `occurred` (completed as intended).
- **Not-terminal →** `rumored` (a third-party-reported possible action/transaction the company has not confirmed; an inbound unsolicited offer stays `rumored`; a denial keeps it `rumored`) · `at_risk` (a specific source-flagged adverse event only threatened/initiated/probable, not yet executed — NOT the company's own plan, NOT generic risk boilerplate) · `suspended` (paused — the SAME attempt can resume) · `announced` (the company stated its OWN action before its completion point; an expansion/extension of its own prior action counts) · `continued` (a prior action still ongoing, no new stage).
- **General word conventions:** shelve/postpone/pause → `suspended`, scrap/abandon/withdraw → `canceled` · a threat ("sues to", "likely to", "pledges to") → `at_risk`, only once executed → `failed` · `announced` requires the SUBJECT company's own action — an outside party's unconfirmed action → `rumored` · `resolved` only for ending a dispute.

**3. Number + comparison fields — AGREED 2026-06-16 (producer-filled; ALL nullable — a fact fills only what applies; all fields null = qualitative-only: the `quote` is the truth, NEVER fabricate a number). Exact meaning of every field:**

| field | what it holds (exact) | values |
|---|---|---|
| `level_low` | the resulting/stated value · the LOW end if a range · the value if a floor (`≥`) | number · `null` |
| `level_high` | the HIGH end if a range · the value if a ceiling (`≤`) | number · `null` |
| `level_bound` | flags an OPEN-ENDED bound (absent ⇒ the level is a point or a closed range) | `floor` · `ceiling` · `null` |
| `level_unit` | the unit of `level_low` / `level_high` | unit enum ↓ |
| `change_value` | the SIGNED size of the move itself (the delta) — NOT the resulting level (`"+60 bps"` → `+60`) | signed number · `null` |
| `change_unit` | the unit of `change_value` — MAY differ from `level_unit` (delta in bps while level is %) | unit enum ↓ |
| `comparison_low` | the prior/baseline value AS STATED in the source · the LOW end if the baseline is a range | number · `null` |
| `comparison_high` | the HIGH end if the stated baseline is a range (`null` ⇒ the baseline is a single point) | number · `null` |
| `comparison_baseline` | WHICH baseline the comparison is against | `consensus` · `prior_year` · `sequential_period` · `previous_guidance` · `null` |

**unit enum** — `level_unit` AND `change_unit` both draw from this ONE list (reused verbatim from the live Guidance `canonical_unit`, so the catalog's Guidance link + dedup line up with no translation table):

| value | means |
|---|---|
| `m_usd` | US dollars in MILLIONS (`6135` = $6,135M) |
| `usd` | US dollars, absolute (`1.20` = $1.20) |
| `percent` | a percentage LEVEL or share (a `17.6`% margin) |
| `percent_yoy` | a year-over-year percent CHANGE (sales `+3`% YoY) |
| `percent_points` | a move in percentage POINTS (margin `+0.6` pts) |
| `basis_points` | a move in basis points (`+60` bps) |
| `count` | a number of things (units, members, stores) |
| `x` | a ratio / multiple (`2.5`x leverage) |
| `unknown` | unit not determinable |

**Level SHAPE — read directly from the slots (no extra field needed):**
- **point** → `level_low` set · `level_high` `null` · `level_bound` `null`   *(the value is `level_low`)*
- **range** → `level_low` < `level_high` · `level_bound` `null`
- **floor (`≥`)** → `level_low` set · `level_high` `null` · `level_bound` = `floor`
- **ceiling (`≤`)** → `level_high` set · `level_low` `null` · `level_bound` = `ceiling`
- **no number** → all four `null`   *(qualitative-only; the `quote` carries the fact)*

**Hard rules (code-enforced at write time — the producer PROPOSES, code DECIDES; reject on violation):**
1. `level_bound` = `floor` ⇒ `level_high` MUST be `null`  ·  `level_bound` = `ceiling` ⇒ `level_low` MUST be `null`.
2. **Sign** — if `change_value` is present AND `driver_state` is DIRECTIONAL (`increased`/`decreased`/`raised`/`lowered`/`beat`/`missed`), its sign MUST match: `+` for increased/raised/beat, `−` for decreased/lowered/missed. Non-directional states impose NO sign rule.
3. **Store-when-stated** — `comparison_low`/`comparison_high` hold the baseline ONLY when the source states it (a frozen fact of THIS event); NEVER a value derived from another node. A stated baseline that fits no enum value ⇒ `comparison_baseline` = `null` WITH the number still stored (the `quote` names it).
4. **Per-unit metrics** (per-share, per-week, per-sq-ft) — the denominator lives in the **driver NAME** (`eps`, `sales_per_square_foot`); the unit stays the base (`usd`/`m_usd`/`count`). There is NO per-X unit.
5. **`comparison_baseline` — ONE primary per fact:** if a fact cites multiple baselines, store only the **primary** (the source's headline; tiebreak `prior_year` > `sequential_period`). The rest stay in the `quote` — **preserved there, but NOT separately queryable** unless per-comparison records are added later. Set `comparison_baseline` = `null` when the comparison is NOT a temporal prior baseline: `vs peers` / `vs 2019` / any anchor-year (a different axis → quote-only), or a streak (`"third consecutive quarter"` → not a baseline). `"exceeded expectations"` is **fact_type-aware**: a `surprise` fact → `consensus` (a surprise is measured vs the market's expectation); a `metric`/`guidance` fact's `"exceeded our guidance/expectations"` → `previous_guidance` (else `null`). Rule of thumb: `consensus` when the baseline is analyst/Street/market; `previous_guidance` only when it clearly refers to company guidance.
6. **`change_value` — store-when-stated:** fill it ONLY when the source states a move (a delta) itself. If a level **and** a comparison baseline are both present in the same unit but no move is stated, leave `change_value` = `null`: for a **point/closed-range** level the delta is derivable (storing it = a drift-prone third copy); for a **floor/ceiling** level, do NOT compute a delta at all (you can't subtract an open bound). A **ranged move** (e.g. a guided "+50–100 bps") has **no second slot** — set `change_value` = `null` and keep the range in the `quote`; never store a single endpoint (there is no `change_high`).
7. **Rate-vs-level routing (don't let a change-verb mis-slot a %):** a change-flavored unit (`percent_yoy` / `percent_points` / `basis_points`) goes in **`change_value`** when the driver has its OWN absolute level (`revenue` → `level_low` = $, the move → `change_value`); it goes in **`level_low`** when the driver **is itself a rate/growth metric** whose value *is* that rate (`same_store_sales` "rose 3%" → `level_low` = `3`, unit `percent_yoy` — NOT `change_value`).

**Worked examples (the disambiguators):**
- *"Margin rose 60 bps to 17.6% from 17.0% a year ago."* → `driver_state`=`increased` · `level_low`=`17.6` · `level_unit`=`percent` · `change_value`=`+60` · `change_unit`=`basis_points` · `comparison_low`=`17.0` · `comparison_baseline`=`prior_year`.
- *"Raised FY guidance to $90–100M from $85–95M."* → `driver_state`=`raised` · `level_low`=`90` · `level_high`=`100` · `level_unit`=`m_usd` · `comparison_low`=`85` · `comparison_high`=`95` · `comparison_baseline`=`previous_guidance`.  *(a prior **band** baseline; "narrowed" stays a read-time derivation, never a state — see the `state` note above.)*
- *"Dividend suspended."* → `driver_state`=`suspended` · all number + comparison fields `null` · the `quote` is the fact.
- *"EPS of $1.30 beat the $1.20 consensus."* → `driver_state`=`beat` · `level_low`=`1.30` · `level_unit`=`usd` · `change_value`=`+0.10` · `change_unit`=`usd` · `comparison_low`=`1.20` · `comparison_baseline`=`consensus`.  *(a surprise's `change_value` = actual − expectation, vs the consensus baseline.)*

**Deliberately NOT fields (do not re-add):** `mid` (derive from low/high) · `usd_per_share` (per-share is in the name) · `unit_raw` (raw wording is in the `quote`) · `accounting_basis`/GAAP-vs-adjusted (lives in the driver name, e.g. `adjusted_eps` ≠ `eps` — kept by ontology R9) · a free-text `qualitative` (the `quote` + `driver_state` carry number-less facts).

**4. Who fills it:** the catalog **reader writes none of this** (it saves `driver_name` + `quote` only). The **producer** fills `driver_state` + the numbers (it has prior-period memory), AFTER the GATE.

**5. Lane check (deterministic · hard-fail · zero LLM):** when a producer writes a `DriverUpdate`, code asserts **(a)** `driver_state` is one of the four `fact_type` lanes defined above, AND **(b)** `level_unit`/`change_unit` ∈ the unit enum and `comparison_baseline` ∈ its enum. Any off-lane / off-menu value — or a Driver with no `fact_type` yet — is **rejected (no write)**, same hard-fail discipline as the structural catalog validators (an off-menu unit would silently break the Guidance-vocab join). The producer *proposes* the state; code *decides* legality. *(Neo4j can't enum-check one property against another, so this is an app-side check at write time — one lane map + one assert, no new DB feature.)*

**LOCKED here (2026-06-15):** the 4 `fact_type`s + all four `state` lists above (fact_type validated on 1,282 names, states on 3,825 quotes). **`rumored` + `failed` were added to the `action_event` lane and validated 2026-06-17** — a weak-model (Haiku) classification-floor test plus an Opus held-out pass on real news; the producer decision ladder above is deliberately principle-based (no domain or example anchors) so it generalizes across industries. **All four `state` lanes (`metric` / `guidance` / `surprise` / `action_event`) were additionally confirmed 2026-06-17 by the same weak-model (Haiku) floor test on real news — objective ~100% in-scope per lane; they passed on the EXISTING vocabulary with no rule changes.** *(Why distinct lane words and not a universal `up/down/flat`: each is a tradeable query signal — "all `withdrawn` guidance" = bearish — so the lanes are deliberately NOT collapsed.)*

**Still OPEN — a few scales/keys only** (the number layer — names + shape + comparison store-vs-derive — is now AGREED 2026-06-16 in item 3 above; minor owner refinements may still follow):
1. *(resolved 2026-06-16: the `EXPLAINED_BY` verdict layer — `weightage` 0–1 deciles (independent, nullable), `confidence` 0–100 deciles, `produced_mode`, derive-share-at-read-time — is now AGREED; see the EXPLAINED_BY rules in §2.)*
2. The type-gating-vs-XBRL rule for the number fields (**store the number for now**; switch to null-and-link only once an XBRL linking pass + a link-checking validator exist, or the value is lost).
3. Exact `id` key strings (principle locked in §4; the literal format is a build detail).

---

## Deferred — NOT decided yet (listed only so they aren't built prematurely or forgotten)

1. **Number layer — names + shape + comparison store-vs-derive AGREED 2026-06-16** (full spec in the fact_type+state section, item 3): `level_low`/`level_high`/`level_bound`/`level_unit` · `change_value`/`change_unit` · `comparison_low`/`comparison_high`/`comparison_baseline` · store-when-stated. Remaining: the type-gating-vs-XBRL rule (**store the number for now**; switch to null-and-link only once an XBRL linking pass + a link-checking validator exist, or the value is lost). The `EXPLAINED_BY` verdict layer (incl. `weightage`/`confidence`/`produced_mode`) is now AGREED 2026-06-16. *(Minor owner tweaks may still follow.)*
2. **Exact `id` key strings** — the principle is locked (§4: fact = event + driver + `fact_scope`; verdict = + producer); the literal format is a build detail.
3. **TODO:** wire **the producer** to extract `driver_state` (vocabulary LOCKED — ready) + the number fields (level/change/comparison; waits on #1) when it makes a `DriverUpdate` (never the catalog build, §0).

*Naming note: the verdict is the `EXPLAINED_BY` edge (`Event → DriverUpdate`) — "attribution," the term chosen over "impact"; in this design there is no separate verdict node.*

---

## STILL OPEN — TO BE DECIDED / FLESHED OUT LATER · SUGGESTION ONLY — Link `fact_type:guidance` Drivers → existing `Guidance` nodes

> **Status: STILL OPEN — TO BE DECIDED / FLESHED OUT LATER. SUGGESTION ONLY — nothing in this ENTIRE section (EVERY subsection below: the contract, resolver, redesign verdict, downside check, owner decisions) is decided, locked, or built.** ONE option for how a `fact_type:guidance` Driver could attach to the existing production Guidance graph (**548 `Guidance` + 8,432 `GuidanceUpdate`** nodes). Read-only investigation 2026-06-15 (mapping subagents + live Neo4j). **Nothing built; the Guidance pipeline is NOT changed by this; the locked fact_types + state lists above are NOT touched.** **Resolver design FINALIZED to a NO-list, fully-automatic form + MEASURED 2026-06-15 (see "Measured validation"); still SUGGESTION-ONLY — nothing built.**

### Why this is even possible
A `Guidance` node IS conceptually a `fact_type:guidance` Driver — a thin, **cross-company, value-free metric tag** (`{id:"guidance:revenue", label, aliases:[40+ phrasings], created_date}`), shared by all companies, identified ONLY by `label_slug = slug(label)`. The per-event values/company/period/concept live on `GuidanceUpdate` (edges: `UPDATES→Guidance`, `FOR_COMPANY`, `FROM_SOURCE`, `HAS_PERIOD`, `MAPS_TO_CONCEPT` 0..1, `MAPS_TO_MEMBER` 0..N). **The guidance pipeline never enforced dedup** (reuse is a prompt-hint, query 7A) → it fragmented into 548 leaky synonyms. **Our Driver catalog is the canonicalization layer it lacks** (Driver↔Guidance-anchor = class↔class; DriverUpdate↔GuidanceUpdate = instance↔instance).

### Empirical finding (live data, verified this session)
```
TRUE synonyms share an EXACT qname → collapse deterministically:
  capex + capital_expenditures → both us-gaap:PaymentsToAcquirePropertyPlantAndEquipment
  revenue + net_sales          → both share us-gaap:Revenues
  d_a + depreciation_and_amort → both share DepreciationDepletionAndAmortization
BUT three deterministic traps (no clean 100% key exists):
  eps + adjusted_eps → SAME exact qname (EarningsPerShareDiluted) → would WRONGLY merge GAAP & non-GAAP
  operating_margin + adjusted_ebitda + operating_income → SAME concept_family (OperatingIncomeLoss) → over-merge
  comparable_sales / comp_store_sales / margins → NULL qname → NO deterministic key at all
```
Live coverage: `xbrl_qname` on 49% of updates, `concept_family` on 61%, the rest slug-only. Match test of our 40 restaurant guidance drivers: **24/40 (60%) link via slug+aliases alone**; concept + base-metric strip reaches ~85%.

### Verified live (2026-06-15, direct Neo4j queries + Python — empirical backbone)
- **Shape solid:** 548 `Guidance` / 8,432 `GuidanceUpdate`; **every** update has exactly one `UPDATES`/`FOR_COMPANY`/`HAS_PERIOD`/`FROM_SOURCE` edge + a `given_date` (100%). Anchor props = `{id,label,aliases,created_date}` only — **no `label_slug`**; `id == "guidance:"+slug(label)` for **all 548** → the slug join is a perfect anchor↔updates key, so the (driver+company)→timeseries query is a clean 2-hop MATCH.
- **Why auto-alias is unsafe:** **227** alias→*different-existing-anchor* collisions; **84** pass a global-uniqueness guard yet still mislink (e.g. `guidance:revenue` lists alias `"custodial revenue"` while `guidance:custodial_revenue` is its own anchor); **161** victim anchors; **216** anchors involved overall.
- **Why auto-qname is unsafe:** one shared qname spans many anchors — `EarningsPerShareDiluted`→**11**, `RevenueFromContract…`→**9** (incl. `subscription_revenue`, `ai_revenue` — *not* synonyms of revenue).
- **Why SET-REPLACE is needed:** the additive-stale-edge pattern already exists in concept links (2 updates with >1 distinct concept qname; 7 edge-without-property; the writer has zero DELETE) — re-resolution must replace, not append.
- **Not built yet:** 0 `Driver` / 0 `DriverUpdate` / 0 `MAPS_TO_GUIDANCE` (the Driver side is unbuilt by design — this contract is the build recipe, not a description of something live).

### The honest answer on "100% reliable + minimal"
**No fully-deterministic 100% shortcut exists** (synonym-collapse is part-judgment), but the no-list design gets close — see **Measured validation** below: **~98–100% precision** (0 wrong links in the objective test) at **~85–96% coverage**. The irreducible gap is metrics with **no Guidance anchor at all** (`four_wall_margin`, `store_week`) → correctly left unlinked.

### The minimal contract — no-list design, MEASURED 2026-06-15 (still SUGGESTION-ONLY)
```
1. LINK = Driver -[:MAPS_TO_GUIDANCE]-> Guidance   (class↔anchor, MATCH-only, ONE-TO-MANY)
     - one-to-many because guidance fragmented: revenue_guidance unions guidance:revenue AND guidance:net_sales
     - a scalar guidance_ref would drop synonym anchors → lose updates → use the EDGE SET
2. RESOLVER (fail-closed; NO hardcoded list — fully automatic, generalizes to any future anchor):
     a. EXACT SLUG (deterministic spine) — link iff Guidance.id == "guidance:" + slug(strip "_guidance" from driver_name).
        Holds for all 548 anchors. Anchor has NO label_slug property → read the slug from g.id; call guidance_ids.slug()
        VERBATIM (never re-implement). Zero wrong links, zero maintenance.
     b. EVIDENCE JUDGE (ONE generic LLM, fail-closed) — retrieve candidate anchors (name-similar + co-filed + same-XBRL),
        the judge PROPOSES which are the SAME metric, then an adversarial Refute drops any that don't clearly survive.
        It reasons ONLY from each anchor's REAL DATA — its unit + a few sample VALUES (co-filing & XBRL as hints only),
        NEVER from the name. GENERIC principles, NO examples, NO list:
          • same THING in the same FORM; a $/count QUANTITY ≠ a %/x RATE or RATIO (an anchor labeled "...sales" that
            HOLDS +2-3% IS a growth % — judge by the values, not the label);
          • GAAP ≠ adjusted/non-GAAP/core; a sub-scope/segment ≠ the whole; net ≠ gross; diluted ≠ basic.
        Default keep-UNLINKED on any doubt. AUTOMATED — humans only in first-industry calibration, hands-off at scale.
     c. else: leave UNLINKED + record conflict.   (MATCH-not-MERGE → a bad ref makes NO edge, never a new node.)
   ⛔ NO curated/synonym list, NO hardcoded examples, NO auto alias-match, NO auto qname-match — each is either a
      maintenance burden or proven UNSAFE on live data (227 alias→other-anchor collisions, 84 defeating a uniqueness
      guard; one qname spans 9–11 anchors incl. GAAP+non-GAAP). The judge reproduces every true synonym
      (revenue↔net_sales, capex↔capital_expenditures) FROM DATA, so a list is redundant — and a curated entry had
      caused a false positive (unit_development→new_store_openings). Fully automatic: the judge reads whatever live
      anchors exist → it generalizes to every present + future metric with nothing to maintain.
3. SET-REPLACE every (continuous) re-run: DELETE MAPS_TO_GUIDANCE edges no longer in the resolver output, then write
   the current set. (Additive MERGE alone leaves stale edges — the same pattern already exists in concept links.)
4. VALIDATORS (guidance-link-specific; zero-judgment HARD-FAIL):
     - target Guidance anchor EXISTS (MATCH-only; never created)
     - live MAPS_TO_GUIDANCE edge-set == current resolver output (the set-replace proof)
     - NO relabeling: the pass never changes any Guidance.label / label_slug
     - REVERSE UNIQUENESS: resolve every incoming source Driver through SAME_AS to its head → each anchor has
       ≤1 distinct canonical head (else HARD-FAIL → leave unlinked, record conflict). No physical reverse edge needed.
     (NOTE: "company actually reports it" + "edge==xbrl_qname" are XBRL CONCEPT-link validators — they belong to the
      SEPARATE MAPS_TO_CONCEPT work, NOT to this guidance link.)
5. INSTANCE link (DriverUpdate ↔ GuidanceUpdate) = producer/backfill work, NOT a Driver-class link.
     (Producer note: guidance `introduced` = first/new for (company, metric, period, basis, segment), NOT "first time
      the Driver ever existed"; raised/lowered/reaffirmed judged from the quote + prior Guidance value-history.)
6. TIMESERIES UNION DEDUP (a Driver unions synonym anchors → one series): REUSE guidance's U54 read-time collapse —
   do NOT hand-roll a key. Partition the unioned rows into series buckets WITHOUT metric_id (so revenue+net_sales
   twins meet), and adapt resolve_unit_groups the same way; then reuse _canonical_numeric_signature /
   _normalize_qualitative + the collapse loop VERBATIM, with key = U54's tuple PLUS
   {company, basis_norm, segment_slug, canonical_unit, time_type}. NEVER fold xbrl_qname or anchor-id into the key
   (that re-splits genuine same-series updates). Keep U54's source priority (8k>transcript>10q>10k>news).
   Query shape: follow `SAME_AS` to the Driver head, union all mapped Guidance anchors, filter updates by company,
   partition by scope/basis/segment/unit/time type, `ORDER BY gu.given_date`, then feed rows through U54.
   U54 de-dupes both cross-anchor twins and same-anchor multi-source duplicates.
7. BORN-LINKED pointer (OPTIONAL): g.canonical_driver on the Guidance ANCHOR (class-level; never the GuidanceUpdate;
   never the label/label_slug). Make it a PURE DERIVATION of the edge (the unique canonical Driver whose
   MAPS_TO_GUIDANCE set contains this anchor), written by the same validator — ONE source of truth, never written
   independently. The relabel ban stays (changing label_slug breaks all guidance machinery — see Downside check).

SAFETY NOTE: a MISSED link is a safe GAP (under-merge) — fixable by a later re-resolution or fresh rebuild; it is NOT
silently-wrong data, and it is NOT "recovered by U54" (U54 only de-dupes anchors ALREADY linked; it cannot see an
anchor that was never linked). An OVER-merge (a WRONG link) is the dangerous, hard-to-undo case — which is exactly why
alias/qname are demoted to evidence and the resolver stays fail-closed.
```

### The link in plain terms — a bridge + a derived pointer
The Driver↔Guidance link has **two halves**:
- **Bridge** = the forward edge above: `Driver -[:MAPS_TO_GUIDANCE]-> Guidance anchor(s)` (one-to-many; built by the evidence-judge, then **maintained on every re-run via set-replace** — contract item 3; a Driver is only re-judged when a *new* anchor could match it, so ongoing cost ≈ 0). → travel *Driver → its full guidance timeseries*.
- **Derived pointer** = one property on each Guidance anchor — `canonical_driver = "driver:<slug>"` — the **same link written backwards** (anchor → its Driver). → travel *Guidance anchor → its Driver* instantly, and let a guidance-ONLY tool find the canonical Driver **without** touching the Driver graph.

```
:Driver "capex"  ═══[:MAPS_TO_GUIDANCE]═══►  :Guidance guidance:capex      ← BRIDGE  (judge-built, forward)
                 ◄── guidance:capex.canonical_driver = "driver:capex" ──    ← POINTER (auto-copied, backward)
```

**"DERIVED" is the whole point:** code COPIES the pointer from the bridge (it is just the reverse of the edge set) and **never decides it separately** → it must **not be allowed to disagree**: the validator **deletes + re-derives it from the edge every run** (the 4 steps below), so it stays a faithful mirror = **one source of truth, no separate judgment.** It NEVER touches `label`/`label_slug`, so it breaks none of guidance's machinery. Build it ONLY after the bridge exists, written by the same validator (contract item 7); do **not** write it as independent guidance-side logic (that would be a second source of truth).

| to answer… | use… |
|---|---|
| Driver → its guidance timeseries (THE GOAL) | the **bridge** edge — *required + sufficient* |
| Guidance anchor → its Driver | the **bridge edge traversed backwards** `(:Guidance)<-[:MAPS_TO_GUIDANCE]-(:Driver)` — free in Neo4j; the pointer only makes it O(1) / usable by a tool that won't traverse |

**Edge required + sufficient; pointer OPTIONAL.** The bridge alone already answers the goal AND the reverse lookup (the edge traverses both ways). So `canonical_driver` is a pure convenience denormalization — add it ONLY if a guidance-side tool needs fast / edge-free reverse lookup. **If added, it MUST be DERIVED with set-replace discipline every run:** (1) build/replace the `MAPS_TO_GUIDANCE` edges → (2) delete stale pointers → (3) rewrite `canonical_driver` from the edges → (4) validate the pointer EXACTLY matches the edge set. Never write it as independent guidance-side logic (second source of truth). **Minimal-safest version = edge only.** Either way, guidance extraction stays untouched.

### Measured validation (2026-06-15 — offline harness, NO production change)
Ran the EXACT resolver above (slug + evidence-judge + Refute, **no list**) as the PREDICTION over **37 guidance-suffixed driver names** (from saved restaurant runs) × the **548 live anchors**, graded against TWO independent golds:

| gold | precision | recall | meaning |
|---|---|---|---|
| **Objective-only** (data rules · ZERO LLM) | **100%** — 0 wrong / 87 hard pairs | n/a | the algorithm **never** linked an objectively-different anchor (wrong unit-class, or GAAP-vs-adjusted) |
| **Independent 3-lens panel** (+ objective overrides) | 91% raw → **~98%** after removing visible panel errors | 77% raw → **~85%** | the panel itself wrongly dropped some drivers' OWN exact-name anchors → *it*, not the algorithm, caused most "misses" |

> **What the two precision numbers mean (do not over-read the 100%):** the **100%** covers only *blatant* wrong links — a $-metric tied to a %-metric, or GAAP tied to adjusted — of which there were **zero**. It does **NOT** prove the *subtle scope* calls (e.g. `cost_inflation` = all costs vs the narrower `input_cost_inflation` = inputs only). Counting those too, **overall precision ≈ 98%** — one known slip (`cost_inflation`→`input_cost_inflation`, a sub-scope over-reach). So: **flawless on obvious errors, ~98% once fine-grained scope is included.**

- **The earlier precision leak is FIXED:** giving the judge each anchor's **unit + sample values** makes it correctly union the whole comparable-/same-store-sales family (it sees they all hold +2–3% → one metric) — the case that capped a prior run at 86%. **Evidence beat labels, with no list.**
- **One-to-many works** (13 drivers union true synonyms, e.g. `capex`→{capex, capital_expenditures}); **many-to-one (8)** is ONLY the un-deduped driver NAMES (4 spellings of capex) → fixed upstream by the catalog's SAME_AS collapse, not by the link.
- **Every recall miss is a SAFE under-link** — a minor true synonym (`eps`↛`reported_eps`) or a fail-closed scope call (`domestic_same_store_sales` left unlinked) → an empty/short series, never wrong data.

**Limitations / NOT tested (read before trusting the numbers):**
- Drivers are **restaurant-derived only** (37 names) vs all-industry anchors — indicative, not universal.
- The panel gold is **partly LLM** and made ~6 visible errors; the **objective-only gold (no LLM) is the trustworthy floor — 0 wrong links in 87 hard cases**. No human-labeled gold exists, so the ~85% recall is measured against an imperfect gold.
- The judge ran on a **retrieved candidate pool** (made generous, but recall is capped by retrieval).
- **Class-level link only.** NOT tested: instance-level `DriverUpdate↔GuidanceUpdate`, the live-producer path, SAME_AS driver-name dedup (assumed upstream), and continuous-resolver behavior as the 548-anchor set grows.
- **Nothing is built** (0 `Driver` / 0 `MAPS_TO_GUIDANCE`) — this is a recipe + offline harness, not a production result.

### What this does NOT change
- The 4 `fact_type`s and all 4 `state` lists stay exactly as locked above.
- The Guidance extraction pipeline stays unchanged in the current resolver: read-only borrow, MATCH-only, never creates Guidance nodes, and never changes `label`, `label_slug`, `GuidanceUpdate`, IDs, XBRL, segments, or grouping. The optional future born-linked integration is the only Guidance-side write: set `g.canonical_driver` on the existing `Guidance` anchor.
- The `_guidance` name suffix stays (it disambiguates the guidance Driver from the `metric` Driver under dual-framing); only the *resolver* strips it.

### Guidance-redesign verdict — NOT worth it (canonicalize on OUR side)
Do **NOT** re-architect the Guidance extraction pipeline. Its fragmentation is **per-company-consistent** (each company's guidance is stable; reuse 7A holds) and only hurts **cross-company aggregation** — which is exactly **our** Driver-catalog's job, not the guidance system's. For its own purposes (per-company tracking, the period-grouped renderer, per-company prediction) it is **good-enough**; a rebuild is high-cost / high-risk for low gain and would **duplicate** the canonicalization our catalog already provides. Division of labor: **Guidance extracts (per-company values/periods/XBRL) · our catalog canonicalizes (cross-company) · the resolver bridges them.** Because the Guidance set is a **live, growing subset**, the link must be a **continuous read-only resolver** (never a one-time dedup). The only worthwhile future integration (small, not a redesign): the guidance writer stamps a **separate `g.canonical_driver` pointer on the `Guidance` ANCHOR** (class-level, computed against our canonical vocab) so new nodes are **born-linked** — **WITHOUT changing the guidance `label`** (contract item 7; zero impact on guidance's labels/slugs/XBRL/segments/IDs/grouping by construction, as long as the resolver stays fail-closed — see below).

### Downside check on the "born-linked" integration (adversarially verified 2026-06-15, executed vs live code)
Checked 6 ways it could harm guidance EXTRACTION (12-agent workflow). **Every downside traces to ONE root: if guidance ADOPTS our driver name INTO its `label`, the `slug` changes — and `label_slug` drives everything** (the XBRL concept resolver `CONCEPT_CANDIDATES.get(label_slug)`; segment placement; the MERGE idempotency key `gu:source:label_slug:period:basis:segment`; renderer/U54 grouping).

| dimension | if RELABELED | severity | unavoidable? |
|---|---|---|---|
| XBRL concept linking | off-registry slug → silently keeps the LLM's guess; loses the deterministic + cross-company concept + `concept_family` | medium | no |
| **Segment dimension** | brand-in-name (R9 `north_italia_…`) → segment lost, `MAPS_TO_MEMBER` never forms | **HIGH** | no |
| **Idempotency** | new slug ≠ historical slug → won't MERGE → **duplicate anchors**, split time-series | **HIGH** | no |
| Recall | breaks ONLY if the reuse becomes a *closed* vocab (the v1 82%-reject death) — safe if kept propose-first | medium | no |
| **Nomenclature** | `_guidance` suffix + R9 brand violate guidance's label contract | **HIGH** | no |
| Downstream | grouping/U54 ripple if the slug changes (evhash16 excludes label → safe) | medium | no |

**Every downside is AVOIDABLE; none is unavoidable** — and **all vanish** in the **separate-pointer** form (contract item 7): a write-time **`g.canonical_driver` on the `Guidance` ANCHOR (class-level — NOT on `GuidanceUpdate`/the instance)** that never changes the `label`/`slug` → all six machinery dimensions = **zero impact by construction**. (The only residual risk is a *wrong* `canonical_driver` match — held to zero by keeping the resolver **FAIL-CLOSED**: unsure → leave unlinked. So "zero impact on guidance's labels/slugs/XBRL/segments/IDs/grouping", not "zero risk of a wrong link".) The pointer form does NOT dedup guidance's *internal* labels (`revenue` vs `net_sales` stay separate anchors), but that fragmentation never hurt guidance's own purposes and both anchors point to our one canonical driver. The **relabel** form is NOT worth it — it needs ≥3 guardrails (strip `_guidance` · split brand/segment back out · keep reuse a PREFERENCE not a filter · company-own-history wins for slug stability) for dedup guidance doesn't need.

### Open owner decisions (before anything is built)
*(The contract above bakes in — and MEASURES (see Measured validation) — a NO-list design: slug + evidence-judge only · set-replace · reverse-uniqueness post-SAME_AS · U54-reuse dedup. Genuinely-open owner calls:)*
1. Confirm the **no-list** design — slug + the evidence-grounded judge replaces the curated map (measured ~98–100% precision, fully automatic, generalizes). The only alternative is **slug-ONLY** (zero-LLM, deterministic, but ~60% coverage — loses every synonym link). Recommended: keep the judge.
2. Confirm the link is a **one-to-many `MAPS_TO_GUIDANCE` edge** (not a scalar `guidance_ref`).
3. Confirm **instance-level** `DriverUpdate ↔ GuidanceUpdate` linking is deferred to the producer/backfill (not a class link).
4. Adopt the optional `canonical_driver` back-pointer on `Guidance` (self-heals + fixes fragmentation), or stay strictly read-only?

*Provenance: investigation 2026-06-15 — `GuidanceExtractionImplemented.md` + `concept_resolver.py`/`guidance_ids.py`/`guidance_writer.py`/`warmup_cache.py` mapped by 3 subagents; the 548-anchor inventory, the exact-qname collapse/over-merge traps, and the 24/40 match all recomputed from live Neo4j. Independently cross-checked a ChatGPT proposal: agreed on the class↔anchor / MATCH-only / fail-closed / `introduced`-scoping points; corrected its scalar `guidance_ref` to one-to-many and its ~80% ceiling (ideally-all needs the judgment). Second cross-check (2026-06-15, resolver order): adopted ChatGPT's correction — **exact SLUG first** (precise: the slug carries the modifier), and **exact-qname demoted to a guarded synonym-EXPANSION step** (leading with qname over-merges GAAP/non-GAAP, e.g. eps↔adjusted_eps share `EarningsPerShareDiluted`). Continuous-resolver + redesign-verdict added (owner note: the 548 anchors are a live, growing subset). Third pass (2026-06-15): ALL data claims re-verified by DIRECT live Neo4j queries + Python (548/8,432; 100% edge + given_date coverage; slug==id for all 548; alias collisions 227/84/161/216; qname 11/9; stale concept edges 2+7; 0 Driver/MAPS_TO_GUIDANCE built). A further ChatGPT cross-check CONVERGED and is adopted — drop auto alias+qname (evidence-only) · set-replace · reverse-uniqueness post-SAME_AS · REUSE U54 for union dedup (partition without metric_id; +basis/segment/unit/time_type; never fold qname/anchor-id). It also corrected TWO of my own earlier overstatements: (i) U54 does NOT "recover" a missed link — a miss is a safe gap, not silently-wrong data; (ii) "company-reports-it" and "edge==xbrl_qname" are XBRL CONCEPT-link validators, not guidance-link validators. Fourth pass (2026-06-15): DROPPED the curated map for a NO-list, evidence-grounded judge (reasons from each anchor's unit + sample values, never names) — fully automatic + generalizes; MEASURED on 37 restaurant guidance drivers × 548 anchors → ~98–100% precision (0 wrong links across 87 objective pairs), ~85% recall (every miss a safe under-link); the prior comp-sales precision leak is fixed by evidence. See "Measured validation".*

---

## APPENDIX — TO BORROW FROM RAVENPACK (read even with zero context — these are PROPOSALS, not locked)

**Zero-context primer (read first):** "RavenPack" (now also branded "Bigdata.com") is a ~20-year commercial product that classifies financial news into an *event taxonomy* — a professionally-curated list of "what kinds of events happen to companies/markets." It is the closest outside analog to THIS `Driver` / `DriverUpdate` catalog. We studied it on 2026-06-16; the full findings, its field model, and a 365-row sample of its **real** categories live in the sibling folder **`/home/faisal/EventMarketDB/.claude/plans/Drivers/RavenPack/`** — files `RavenPack_Taxonomy.md`, `RavenPack_categories_365.csv`, `RavenPack_Taxonomy_vs_Drivers.md`.

**The one thing RavenPack does NOT have that THIS schema does:** *causal attribution.* RavenPack records *what happened* + its sentiment, but never says "this event caused X% of **this** stock's move, this confidently." Our `EXPLAINED_BY` verdict edge (`stock_impact` + `weightage` + `confidence`) is exactly that attribution layer. **So we borrow RavenPack's event-state COVERAGE — never its descriptive model.** Do not dilute the attribution layer.

> **STATUS OF THIS APPENDIX:** Borrow 1 is **ADOPTED** (below). Borrows 2–5 remain **PROPOSALS to evaluate against real data before adopting** — none locked or built; do **not** treat them as decided design.

### Borrow 1 — `rumored` + `failed` `action_event` states — ✅ ADOPTED 2026-06-17
Now in the `action_event` lane (see the lane table + producer decision ladder above). `rumored` = a third-party-reported, company-unconfirmed possible action/transaction; `failed` = an involuntary block/rejection (distinct from `canceled` = the company's OWN withdrawal). Validated on real M&A / biotech / IPO news via a weak-model (Haiku) classification-floor test + an Opus held-out pass; the locked ladder is principle-based (no industry-jargon examples) so it generalizes. RavenPack only motivated the gap — its slugs were NOT imported (per Borrow 2's rule).

### Borrow 2 — use RavenPack's full category list as a coverage / recall CHECKLIST when scaling beyond restaurants — NOT as a vocabulary  *(HIGH value · no lock touched)*
- **What RavenPack has:** a comprehensive, cross-industry, professionally-curated list of ~7,400 corporate event types. Free 365-row sample: `/home/faisal/EventMarketDB/.claude/plans/Drivers/RavenPack/RavenPack_categories_365.csv`. How to obtain the full gated file: `…/RavenPack/RavenPack_Taxonomy.md` §6.
- **What THIS schema does:** `Driver` names are coined **empirically** by an LLM reading the source documents; the catalog has so far been calibrated **only on the restaurant industry**.
- **The exact gap:** restaurant filings never contain whole families of real stock-moving events that exist elsewhere — e.g. spin-off, going-private, reverse-stock-split, rights-issue, shelf-registration, private-placement, shareholder-rights-plan (poison pill), debt-restructuring, clinical-trial outcomes, orphan-drug / fast-track designations, drug-approval / denial, patent-awarded / revoked, cyber-attacks, executive-death / health / scandal, index-listing / delisting, auditor-resignation, exchange-noncompliance. The coiner has only been tested on restaurants → **silent recall blind-spots** when expanding to a new industry.
- **CRITICAL — what NOT to do:** do **NOT** import RavenPack categories as a closed/predefined vocabulary, and do **NOT** use RavenPack slugs as `driver_name`s. (i) A closed vocabulary is exactly what killed catalog **v1** (82% of held-out drivers rejected). (ii) RavenPack slugs bake state + polarity INTO the name (e.g. `earnings-per-share-above-expectations`), which violates this schema's rule that state/direction must never be in `driver_name` (R7). Coining must stay open + empirical.
- **Proposed action:** use the list ONLY as a **post-build QA recall checklist** — after a new industry's catalog is built, cross-check the produced Driver names against RavenPack's category families; for any family genuinely relevant to that industry but ABSENT from our catalog, confirm it is a true absence (the data didn't mention it) and not a coiner blind-spot. It is a completeness-audit tool, never an input to coining.

### Borrow 3 — add a "novelty" (first-seen vs repeat) signal for the predictor — computed at READ TIME, never stored  *(real missed feature · free · no lock touched)*
- **What RavenPack has:** `EVENT_SIMILARITY_DAYS` (days since a similar event was last seen for that entity; 0 = same instant) and an Event Novelty Score — i.e. is this NEW information or a repeat/rehash. Markets react to NEW information; a re-reported old fact barely moves the stock.
- **What THIS schema has:** every `DriverUpdate` is one per-event fact keyed by `event + driver + fact_scope`; the schema already treats recurrence as a READ-TIME view (never a stored field). But NO novelty / first-seen signal is currently exposed to the predictor.
- **The exact gap:** the predictor cannot distinguish *"the FIRST time this company has shown this driver-fact"* (high signal) from *"this driver has appeared every quarter for years"* (low signal). The information is fully present in the `DriverUpdate` time series — it is simply not surfaced.
- **Proposed action:** at READ TIME (do NOT store — consistent with this schema's "store the truth, derive views" rule), compute a novelty feature per (company, driver, fact_scope), e.g. `is_first_occurrence` (boolean) + `days_since_prior_occurrence`, by querying the existing `DriverUpdate` sequence ordered by date, and feed it to the predictor. **No schema or field change** — a query over data we already store.

### Borrow 4 — capture which SIDE the company is on in a two-party event  *(real · lower priority)*
- **What RavenPack does:** for two-party events it tags the company's ROLE — `acquisition-acquiree` (target) vs `acquisition-acquirer` (buyer); `legal-issues-defendant` vs `legal-issues-plaintiff`; `loan-provider` vs `loan-recipient`. The SAME event gives OPPOSITE stock reactions by side (target typically jumps; acquirer often falls).
- **What THIS schema has:** the `EXPLAINED_BY` edge carries `stock_impact` (long/short) = net direction only; nothing records the structural SIDE in a two-party event.
- **The exact gap:** for M&A, litigation, lending, partnerships, the company's side is a strong structural predictor we do not represent; `stock_impact` only gives the noisy net direction.
- **Proposed action (choose one, decide later):** **(a) PREFERRED** — encode the side in `Driver.name` (e.g. `acquisition_target` vs `acquisition_acquirer`), since these are genuinely different causes and this schema already allows two Drivers per topic under different framing ("dual framing"); **OR (b)** add an optional `counterparty_role` property on the `DriverUpdate`. Use (a) unless real data shows it over-splits. Applies only to two-party-event drivers.

### Borrow 5 — a `scheduled` (expected vs surprise) flag  *(cheap · low priority)*
- **What RavenPack has:** a `SCHEDULED` boolean on every event = pre-announced / anticipated (e.g. an earnings release on a known calendar date) vs a surprise (out-of-the-blue news).
- **What THIS schema has:** no equivalent flag.
- **The exact gap:** a scheduled earnings beat and a surprise news shock move the stock differently (a scheduled event already has positioned expectations; a surprise has a larger immediate reaction); the predictor benefits from knowing which.
- **Proposed action:** add a cheap `scheduled` boolean — most likely DERIVED from the event type (regular periodic filings / earnings = scheduled; ad-hoc news = unscheduled), so it may need NO new stored field, just a read-time derivation. Confirm against data before adding any field.

**Priority (honest, most → least):** Borrow **1** (failed/rumored states) and Borrow **2** (recall checklist) are genuine coverage gaps and highest value. Borrow **3** (novelty) is a real missed predictor feature, free to add (read-time). Borrows **4–5** are smaller. NONE changes the core architecture — they add event-state COVERAGE + read-time FEATURES only. The attribution layer (`EXPLAINED_BY`) is the part RavenPack cannot match; keep it intact.

*(Source: RavenPack study 2026-06-16, files in `/home/faisal/EventMarketDB/.claude/plans/Drivers/RavenPack/`. PROPOSALS only — not locked, not built.)*
