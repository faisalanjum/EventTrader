# DriverUpdate — Node Spec

**Status (2026-06-14): core node/edge STRUCTURE locked (Design C). The `Driver` class fields are FINALIZED; the `DriverUpdate` + `EXPLAINED_BY` property names/meanings are still open (*working placeholders* — see §2 + Deferred). Nothing built — 0 `Driver` / `DriverUpdate` nodes in Neo4j.** This file records ONLY what is fully decided. (Owner-approved to write this one file; no other files touched.) **Update 2026-06-15 — the DriverUpdate CREATION CONTRACT is now locked: see §0 (catalog build = the complete Driver class [name + `fact_type` + optional links] in ONE run · producers create every DriverUpdate · no build-time seeder).**

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
| `Driver` (node, class) | the reusable named cause; name + `fact_type` + `aliases` + optional XBRL/guidance link **on the class** | catalog pipeline |
| `DriverUpdate` (node, instance) | one per-event **fact** about a driver (state/change/surprise/guidance/action + size + quote — never a mere mention) | **a producer ONLY** — live or backfill; never the catalog build (§0) |
| `EXPLAINED_BY` (edge `Event → DriverUpdate` = the verdict) | the causal verdict, in the edge's properties | a producer, only when a stock move is judged |
| `Event`, `Company` (existing nodes) | the source + the company; the **return** lives on the `Event → Company` edge | the existing pipeline |

## 2. Fields

> ⚠️ **Property-meanings pass IN PROGRESS.** The **`Driver`** fields in the table below are **finalized** (incl. `fact_type`, whose 4-value enum + definitions were LOCKED 2026-06-15 — see the fact_type lock section). **`DriverUpdate`** and **`EXPLAINED_BY`** field names are still **working placeholders** until approved.

**`Driver`** (the class — FINALIZED)

| field | what it means | keep |
|---|---|---|
| `id` | code-built stable key (e.g. `driver:same_store_sales`) | ✅ |
| `name` | the canonical lower_snake driver name | ✅ |
| `aliases` | the **SAME_AS** variant names — reversible, both survive; one-hop read-through. **NOTE: our formal SAME_AS set, NOT Guidance's loose "aliases."** | ✅ |
| `created` | when the driver first appeared | ✅ |
| `definition` | a plain one-line meaning of the driver — **optional / nullable** | ⚪ |
| `fact_type` | the driver's permanent KIND — one of `metric` / `guidance` / `surprise` / `action_event` (routes the DriverUpdate `state`; enum + definitions LOCKED 2026-06-15 — see the fact_type lock section) | ✅ |

**Excluded:** no `evhash16` on the class (it is never re-extracted → nothing to change-detect; Guidance's anchor has none either).
**Optional links (edges, an OPTIONAL best-effort FINAL step of the catalog-creation run — non-blocking; self-heal on re-run):** `Driver-[:MAPS_TO_CONCEPT]->Concept` · `-[:MAPS_TO_MEMBER]->Member` · `-[:MAPS_TO_GUIDANCE]->Guidance`.

**`DriverUpdate`** (the fact)

| field (placeholder name) | what's decided | structural role decided? |
|---|---|---|
| `driver_state` | the driver's event-level **state/outcome** for this fact (not only a direction); lives here, **never in the name** | ✅ vocabulary LOCKED (see §2-state); field NAME still a placeholder |
| `magnitude_value` + `magnitude_unit` | the **driver's own** number/size for this fact (NOT the stock effect); **nullable** | ⏳ precise definition deferred |
| `quote` | verbatim source text; stored ONLY when the source gives a real state/value/change (never a bare mention) | ✅ |
| `source_type` · `date` · `created` | provenance · statement-time · write/merge-time | ✅ |
| `fact_scope` | which *version* of this driver-fact inside the event (period / segment / geography / store-type, or a normalized-quote hash) — part of the key; **identity-only, never in `Driver.name`** | ✅ |
| `id` · `evhash16` | code-built key + value-hash (see §4); **no producer in the key** | ✅ |

**`EXPLAINED_BY`** (the verdict — properties on the `Event → DriverUpdate` edge)

| field (placeholder name) | what's decided | structural role decided? |
|---|---|---|
| `stock_impact` | `long` / `short` — this driver's **own** push on the event's move (can oppose the net move) | ✅ |
| `weightage` | the **model's estimate** of this driver's share of *this event's* move — **never** the realized share | ⏳ scale/normalization deferred |
| `confidence` | how sure the producer is the claim is true | ⏳ exact scale deferred |
| `llm_producer` | who judged (earnings-learner / news-driver) | ✅ |
| `id` · `created` · `evhash16` | code-built key + write-time + value-hash (see §4); **producer IS in the key** | ✅ |

**PIT rule (decided):** the *realized* share / actual return is **never stored** on the verdict and **never shown to the predictor** — it is computed at read time from the `Event → Company` return.

## 3. Edges (decided)

| edge | from → to | meaning | when |
|---|---|---|---|
| `OF_DRIVER` | `DriverUpdate` → `Driver` | this fact is an instance of this driver | always (exactly 1) |
| `FROM_SOURCE` | `DriverUpdate` → `Event` | this fact came from this event (evidence) | always — every `DriverUpdate` is event-sourced |
| `EXPLAINED_BY` {verdict} | `Event` → `DriverUpdate` | this event's move is explained by this fact | 0, or 1 per producer |
| `INFLUENCES` / `PRIMARY_FILER` {returns} | `Event` → `Company` | the realized stock move (existing edge) | existing |

- **`FROM_SOURCE` and `EXPLAINED_BY` are SEPARATE edges** (a fact can be *reported* in an event without *explaining* its move) — never collapse the verdict onto the provenance edge.
- **No `BASED_ON`.** Trends are **queried** (each fact's `driver_state` gives the state/outcome and `magnitude`/numbers the value), never stored as links.
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

The catalog build **only creates/reuses `Driver` names** (the class) — it **never mints a `DriverUpdate`** (the locked contract, §0). Its `evidence_refs` (driver · company · event · date · quote — KPI-only evidence has no real `Event`/date and never feeds a `DriverUpdate`, §0 point 4) are **mentions** that justify and let producers reuse a name; they are **not** event-level facts and carry no `driver_state` / `magnitude`. The **producers** (earnings-learner / news-driver) are the sole creators of `DriverUpdate`s — judging the real event-level fact + its state/size, and (when attributed) the `EXPLAINED_BY` verdict — in both **live** processing and a **historical backfill** over the same source events. To populate history early, run the producer as a **backfill** (§0 point 7); do **not** add a build-time detector (§0 point 5).

## 8. Full shape (annotated — *all field names are placeholders*)

```
                ┌──────────────────────────────────────────────┐
                │ ( :Driver )   — reusable cause (the "class")    │
                │    id  "driver:<slug>" · name "same_store_sales"│
                │    aliases [ … ]                       │
                │    (+ optional XBRL/guidance link ON THE CLASS) │
                └────────────────────▲──────────────────────────┘
                                     │  :OF_DRIVER  (always · 1)
   ┌─────────────────────────────────┴───────────────────────────────────┐
   │ ( :DriverUpdate )   — the FACT ("what the driver did this event")      │
   │    id  code-built: event + driver + fact_scope   (NO producer)        │
   │    evhash16  value-hash of the fact payload                           │
   │    driver_state     state/outcome     (NEVER in the name)             │
   │    magnitude_value  driver's OWN number/size        (nullable)        │
   │    magnitude_unit                                   (nullable)        │
   │    quote · source_type · date · created                              │
   │    ⚠ ALL field names = working placeholders (name + meaning TBD)      │
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

## fact_type + state-words — LOCKED 2026-06-15  ·  number fields (DriverUpdate) — still OPEN

> Output of the property-meanings pass, grounded in a census of EVERY real Fable driver record (CAKE 594 + 14-ticker 673 + raw menus). **The `fact_type` block AND the per-update `state` lists below are LOCKED (2026-06-15; fact_type validated on 1,282 driver names, states on 3,825 evidence quotes); only the number fields (level/change/comparison) remain open.** **Core principle:** the state words are *helper buckets* for grouping/querying; the verbatim **`quote` is the truth** — so the enum can stay small and the quote carries precision.

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
> 3. **`fact_type` — MANDATORY final step** — a cheap per-Driver judgment over each finalized name + its evidence assigns one of the 4 kinds. **NOT the blind reader** (a separate classifier at the end; no source re-read).
> 4. **XBRL/guidance links — OPTIONAL, best-effort final step** — attached only on a confident resolver match; failures **never block** the catalog and **self-heal on re-run**.

So catalog creation outputs the **complete Driver CLASS** (name + `fact_type` + optional links) in ONE run — still **NO `DriverUpdate`s** (those are the producer's job: live + backfill, §0). `fact_type` is set ONCE per `Driver` and is permanent; the *changing* `state` lives on the `DriverUpdate`; never put state/direction in `Driver.name` (R7).

> ✅ The 4 `fact_type`s **AND** the per-update `state`-word lists (§2 below) are now LOCKED (2026-06-15; fact_type validated on 1,282 driver names, states on 3,825 evidence quotes). Only the **number fields** (level/change/comparison) remain open.

**2. `state` — on `DriverUpdate` — LOCKED 2026-06-15** (validated on 3,825 real evidence quotes; set by the PRODUCER when it makes a DriverUpdate, never during catalog creation). Chosen from the driver's `fact_type` lane; `unknown` is the rare last resort; the raw `quote` is always the truth.

| `fact_type` | `state` — pick one |
|---|---|
| `metric` | increased · decreased · unchanged · mixed · reported · persists · unknown |
| `guidance` | introduced · raised · lowered · reaffirmed · withdrawn · unknown |
| `surprise` | beat · in_line · missed · unknown |
| `action_event` | at_risk · announced · occurred · continued · resolved · canceled · suspended · unknown |

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
- **action_event:** `at_risk` (see strict rule) · `announced` = the company *decided/plans* it, not yet done · `occurred` = it happened (incl. a deal **closed/completed**) · `continued` = still ongoing · `resolved` = ended/settled · `canceled` = called off · `suspended` = paused.

**Cross-type routing rule (prevents mis-bucketing):** outlook verbs — "expect / anticipate / target / plan to ___" — route to **`guidance`** (reaffirmed/raised/lowered), **never** a `metric` state. *(The metric direction/level/condition rules now live in the metric ladder above.)*

**`at_risk` — STRICT rule (or it floods):** use ONLY for a **specific, current, source-flagged possible ADVERSE event that has NOT happened and is NOT the company's own plan** — e.g. `debt_covenant_default`, `delisting`, `loss_of_license`. A *planned* action (a closure the company intends, an authorized buyback) is `announced`, not `at_risk`. **Generic risk-factor boilerplate** ("litigation could harm us", "weather may affect results", "cyber incidents could occur") is a mention → the gate drops it, **NO DriverUpdate** (§0).

*(`narrowed` is NOT a state — it is derived from the comparison fields below. The metric word is `persists`, NOT `continued` — `continued` collides with "continued to grow/decline" and would steal directional cases from `increased`/`decreased`.)*

**3. Numbers — explicit fields (NOT a vague magnitude); ALL nullable, a fact fills only what applies:**
- **LEVEL** (the resulting/stated value): `level_value` · `level_value_high` (range high) · `level_unit`
- **CHANGE** (the move/delta): `change_value` (signed) · `change_unit`
- **COMPARISON** (the prior baseline it is measured against): `comparison_value` · `comparison_value_high` · `comparison_basis` *(e.g. `previous_guidance` · `prior_period` · `consensus` · `prior_year`)*
- `*_unit` ∈ `pct · bps · usd · usd_per_share · count · ratio`
- **all-null = qualitative-only** (the `quote` is the truth; never fabricate a number).

**Exact field meanings (unambiguous):**

| field | what it means | example |
|---|---|---|
| `level_value` | the driver's **resulting / stated value** after the change — a point-in-time level (the LOW end if it is a range) | margin → `17.6` |
| `level_value_high` | the HIGH end when the level is a **range** (e.g. a guidance band); `null` otherwise | guidance band → `100` |
| `level_unit` | the unit of `level_value` / `level_value_high` | `pct` |
| `change_value` | the **size of the move itself** (the delta), **signed** (`+` up / `−` down) — NOT the resulting level | "+60 bps" → `+60` |
| `change_unit` | the unit of `change_value` — **may differ from `level_unit`** (the change is in bps while the level is in %) | `bps` |
| `comparison_value` | the **prior / baseline value** the change is measured against (LOW end if a range) | prior guidance → `70` |
| `comparison_value_high` | the HIGH end of the comparison baseline when it is a **range**; `null` otherwise | prior band → `110` |
| `comparison_basis` | **what** the baseline is: `previous_guidance` / `prior_period` / `consensus` / `prior_year` | `previous_guidance` |

> **The three in one line:** `change` = *how much it moved* · `level` = *where it ended up* · `comparison` = *what it moved from*. A fact carries any combination — a delta with no level, a level with no delta, or both (the margin example carries both).

> Example — guidance `$85–100M` vs prior `$70–110M`: `state=reaffirmed`; `level_value=85, level_value_high=100, level_unit=usd`; `comparison_value=70, comparison_value_high=110, comparison_basis=previous_guidance`. → "narrowed" (new band 15 < prior 40) is **computable**, not stored.

**4. Who fills it:** the catalog **reader writes none of this** (it saves `driver_name` + `quote` only). The **producer** fills `state` + the numbers (it has prior-period memory), AFTER the GATE.

**LOCKED here (2026-06-15):** the 4 `fact_type`s + all four `state` lists above (fact_type validated on 1,282 names, states on 3,825 quotes). *(Why distinct lane words and not a universal `up/down/flat`: each is a tradeable query signal — "all `withdrawn` guidance" = bearish — so the lanes are deliberately NOT collapsed.)*

**Still OPEN — only the number layer + a few field details** (also in Deferred):
1. **COMPARISON fields** — *store* the prior baseline on each update (leaning; verifiable + self-contained) vs *derive* it from the prior update (leaner).
2. **Number field names** — `level_value` / `change_value` / … kept as written (leaning) vs shorter.
3. Exact **DriverUpdate field NAMES** (`driver_state` / `magnitude_*` are still placeholders), `weightage` scale, `confidence` scale, and `id` key formats.

---

## Deferred — NOT decided yet (listed only so they aren't built prematurely or forgotten)

1. **Number layer + exact field NAMES (the next pass):** the `state` *vocabulary* is LOCKED, but the DriverUpdate *field names* (`driver_state` / `magnitude_*`) are still placeholders, and these remain to finalize: `magnitude` precise definition **and** the type-gating-vs-XBRL rule (**store the number for now**; switch to null-and-link only once an XBRL linking pass + a link-checking validator exist, or the value is lost) · `weightage` scale/normalization · `confidence` scale + how it differs from `weightage`.
2. **Exact `id` key strings** — the principle is locked (§4: fact = event + driver + `fact_scope`; verdict = + producer); the literal format is a build detail.
3. **TODO:** wire **the producer** to extract `state` (vocabulary LOCKED — ready) + `magnitude` (waits on #1) when it makes a `DriverUpdate` (never the catalog build, §0).

*Naming note: the verdict is the `EXPLAINED_BY` edge (`Event → DriverUpdate`) — "attribution," the term chosen over "impact"; in this design there is no separate verdict node.*

---

## STILL OPEN — TO BE DECIDED / FLESHED OUT LATER · SUGGESTION ONLY — Link `fact_type:guidance` Drivers → existing `Guidance` nodes

> **Status: STILL OPEN — TO BE DECIDED / FLESHED OUT LATER. SUGGESTION ONLY — nothing in this ENTIRE section (EVERY subsection below: the contract, resolver, redesign verdict, downside check, owner decisions) is decided, locked, or built.** ONE option for how a `fact_type:guidance` Driver could attach to the existing production Guidance graph (**548 `Guidance` + 8,432 `GuidanceUpdate`** nodes). Read-only investigation 2026-06-15 (mapping subagents + live Neo4j). **Nothing built; the Guidance pipeline is NOT changed by this; the locked fact_types + state lists above are NOT touched.**

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

### The honest answer on "100% reliable + minimal"
**No fully-deterministic 100% shortcut exists** — synonym-collapse is irreducibly part-deterministic, part-judgment (same reason the guidance pipeline's own deterministic reuse leaked).

| meaning of "reliable" | achievable? | cost |
|---|---|---|
| **No wrong links** (fail-closed) | **Yes, deterministically — ~75–80%** coverage (all high-value metrics: revenue·eps·capex·tax·op-income) | **zero** guidance change, zero judgment |
| **Ideally-ALL coverage** | needs a G2/Refute dedup judgment for the fuzzy residual (comp-sales, GAAP/non-GAAP) → ~**95%** | a **CONTINUOUS resolver** (re-runs as the guidance set grows — NOT a one-time pass; the 548 are a live, expanding subset), reusing our existing G2/Refute |
| true 100% | **impossible** — ~5% (`four_wall_margin`, `store_week`) have **no Guidance node**; correctly left unlinked | — |

### The proposed minimal contract (the suggestion)
```
1. Link = Driver -[:MAPS_TO_GUIDANCE]-> Guidance   (class↔anchor, MATCH-only, ONE-TO-MANY)
     - one-to-many because of fragmentation: capex_guidance → guidance:capex AND guidance:capital_expenditures
     - a scalar guidance_ref would drop the synonym anchors → lose updates → use the EDGE SET
2. Resolver order (fail-closed — PRECISE key first; the fuzzy key only EXPANDS, never decides):
     a. exact slug match (strip _guidance; guidance's EXACT slug(): sga→sg_a, d&a→d_a) → the PRIMARY anchor.
        Precise by construction: the slug carries the modifier, so adjusted_eps→guidance:adjusted_eps, NEVER guidance:eps.
     b. approved override map (curated, for known wording gaps: unit_development→guidance:new_store_openings)
     c. exact-qname EXPANSION (NOT a primary decision): only AFTER a modifier guard, ADD synonym anchors that
        share the exact qname AND the same adjusted/non_gaap/diluted modifier (capex → also guidance:capital_expenditures).
        Used only to EXPAND the link set — never to decide a link from scratch (qname over-merges GAAP/non-GAAP).
     d. unique alias (exactly one target)
     e. [ideally-all only] G2/Refute judgment (the existing dedup) for the fuzzy residual
     f. else: leave unlinked, record conflict   (NEVER create a Guidance node — MATCH only)
3. Instance link (DriverUpdate ↔ GuidanceUpdate) = producer/backfill work, NOT a Driver-class link
     (only the producer knows event/source/period/basis/segment)
4. State clarification: guidance `introduced` = first/new for (company, metric, period, basis, segment),
     NOT "first time the Driver ever existed". raised/lowered/reaffirmed are judged by the producer from
     the quote + the prior Guidance value-history (the Guidance graph stores values, not the raised/lowered enum).
5. Guidance pipeline: UNCHANGED.  OPTIONAL future ("born-linked" — zero IMPACT on guidance's machinery, see "Downside check"):
     the guidance writer stamps a SEPARATE pointer `g.canonical_driver = "driver:…"` **on the `Guidance` ANCHOR (the
     class — NOT on `GuidanceUpdate`/the per-event instance)**, computed by the same resolver against our vocab. The
     mapping is identical for every one of an anchor's updates, so it is a CLASS↔CLASS fact (matching the
     `Driver -[:MAPS_TO_GUIDANCE]-> Guidance` edge in §1; only the *concept* qname is per-`gu`, the *canonical driver* is not).
     It does NOT touch the guidance `label`/`label_slug`, so XBRL resolution, segments, idempotency (the slug-keyed MERGE),
     and grouping are ALL untouched.
     ⛔ Do NOT instead make guidance ADOPT our names INTO the `label` (a "relabel") — that changes the slug and
     breaks the slug-keyed machinery (see Downside check). The separate pointer gives "born-linked" with **no impact on
     guidance's machinery; the only residual risk is a WRONG match, held to zero by keeping the resolver FAIL-CLOSED**.
```

### What this does NOT change
- The 4 `fact_type`s and all 4 `state` lists stay exactly as locked above.
- The Guidance extraction pipeline stays unchanged in the current resolver: read-only borrow, MATCH-only, never creates Guidance nodes, and never changes `label`, `label_slug`, `GuidanceUpdate`, IDs, XBRL, segments, or grouping. The optional future born-linked integration is the only Guidance-side write: set `g.canonical_driver` on the existing `Guidance` anchor.
- The `_guidance` name suffix stays (it disambiguates the guidance Driver from the `metric` Driver under dual-framing); only the *resolver* strips it.

### Guidance-redesign verdict — NOT worth it (canonicalize on OUR side)
Do **NOT** re-architect the Guidance extraction pipeline. Its fragmentation is **per-company-consistent** (each company's guidance is stable; reuse 7A holds) and only hurts **cross-company aggregation** — which is exactly **our** Driver-catalog's job, not the guidance system's. For its own purposes (per-company tracking, the period-grouped renderer, per-company prediction) it is **good-enough**; a rebuild is high-cost / high-risk for low gain and would **duplicate** the canonicalization our catalog already provides. Division of labor: **Guidance extracts (per-company values/periods/XBRL) · our catalog canonicalizes (cross-company) · the resolver bridges them.** Because the Guidance set is a **live, growing subset**, the link must be a **continuous read-only resolver** (never a one-time dedup). The only worthwhile future integration (small, not a redesign): the guidance writer stamps a **separate `g.canonical_driver` pointer on the `Guidance` ANCHOR** (class-level, computed against our canonical vocab) so new nodes are **born-linked** — **WITHOUT changing the guidance `label`** (contract §5; zero impact on guidance's labels/slugs/XBRL/segments/IDs/grouping by construction, as long as the resolver stays fail-closed — see below).

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

**Every downside is AVOIDABLE; none is unavoidable** — and **all vanish** in the **separate-pointer** form (contract §5): a write-time **`g.canonical_driver` on the `Guidance` ANCHOR (class-level — NOT on `GuidanceUpdate`/the instance)** that never changes the `label`/`slug` → all six machinery dimensions = **zero impact by construction**. (The only residual risk is a *wrong* `canonical_driver` match — held to zero by keeping the resolver **FAIL-CLOSED**: unsure → leave unlinked. So "zero impact on guidance's labels/slugs/XBRL/segments/IDs/grouping", not "zero risk of a wrong link".) The pointer form does NOT dedup guidance's *internal* labels (`revenue` vs `net_sales` stay separate anchors), but that fragmentation never hurt guidance's own purposes and both anchors point to our one canonical driver. The **relabel** form is NOT worth it — it needs ≥3 guardrails (strip `_guidance` · split brand/segment back out · keep reuse a PREFERENCE not a filter · company-own-history wins for slug stability) for dedup guidance doesn't need.

### Open owner decisions (before anything is built)
1. Take the **read-only ~80% deterministic** resolver (truly minimal, captures all high-value metrics), or add the **continuous G2/Refute dedup step** to reach ~95% (ideally-all)?
2. Confirm the link is a **one-to-many `MAPS_TO_GUIDANCE` edge** (not a scalar `guidance_ref`).
3. Confirm **instance-level** `DriverUpdate ↔ GuidanceUpdate` linking is deferred to the producer/backfill (not a class link).
4. Adopt the optional `canonical_driver` back-pointer on `Guidance` (self-heals + fixes fragmentation), or stay strictly read-only?

*Provenance: investigation 2026-06-15 — `GuidanceExtractionImplemented.md` + `concept_resolver.py`/`guidance_ids.py`/`guidance_writer.py`/`warmup_cache.py` mapped by 3 subagents; the 548-anchor inventory, the exact-qname collapse/over-merge traps, and the 24/40 match all recomputed from live Neo4j. Independently cross-checked a ChatGPT proposal: agreed on the class↔anchor / MATCH-only / fail-closed / `introduced`-scoping points; corrected its scalar `guidance_ref` to one-to-many and its ~80% ceiling (ideally-all needs the judgment). Second cross-check (2026-06-15, resolver order): adopted ChatGPT's correction — **exact SLUG first** (precise: the slug carries the modifier), and **exact-qname demoted to a guarded synonym-EXPANSION step** (leading with qname over-merges GAAP/non-GAAP, e.g. eps↔adjusted_eps share `EarningsPerShareDiluted`). Continuous-resolver + redesign-verdict added (owner note: the 548 anchors are a live, growing subset).*
