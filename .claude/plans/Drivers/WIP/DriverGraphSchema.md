# DriverUpdate — Node Spec

**Status (2026-06-14): core node/edge STRUCTURE locked (Design C). Every property's *name AND meaning* is still open — the field names below are *working placeholders* (see "Deferred"). Nothing built — 0 `Driver` / `DriverUpdate` nodes in Neo4j.** This file records ONLY what is fully decided. (Owner-approved to write this one file; no other files touched.)

---

## Plain what / why

- A **`Driver`** is a reusable named cause (`same_store_sales`, `oil_price`) — the **class**. Built by the catalog pipeline; optionally linked to XBRL / Guidance nodes.
- A **`DriverUpdate`** is one **fact**: *"on this event, this driver did X"* (the change + its size + the quote). The **instance**.
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
| `Driver` (node, class) | the reusable named cause; name + `aliases` + optional XBRL/guidance link **on the class** | catalog pipeline |
| `DriverUpdate` (node, instance) | one per-event **fact** about a driver (change + size + quote) | a producer / catalog evidence |
| `EXPLAINED_BY` (edge `Event → DriverUpdate` = the verdict) | the causal verdict, in the edge's properties | a producer, only when a stock move is judged |
| `Event`, `Company` (existing nodes) | the source + the company; the **return** lives on the `Event → Company` edge | the existing pipeline |

## 2. Fields

> ⚠️ **Property-meanings pass IN PROGRESS.** The **`Driver`** field names below are **finalized**; **`DriverUpdate`** and **`EXPLAINED_BY`** field names are still **working placeholders** until approved.

**`Driver`** (the class — FINALIZED)

| field | what it means | keep |
|---|---|---|
| `id` | code-built stable key (e.g. `driver:same_store_sales`) | ✅ |
| `name` | the canonical lower_snake driver name | ✅ |
| `aliases` | the **SAME_AS** variant names — reversible, both survive; one-hop read-through. **NOTE: our formal SAME_AS set, NOT Guidance's loose "aliases."** | ✅ |
| `created` | when the driver first appeared | ✅ |
| `definition` | a plain one-line meaning of the driver — **optional / nullable** | ⚪ |

**Excluded:** no `evhash16` on the class (it is never re-extracted → nothing to change-detect; Guidance's anchor has none either).
**Optional links (edges, built later by the linking pass):** `Driver-[:MAPS_TO_CONCEPT]->Concept` · `-[:MAPS_TO_MEMBER]->Member` · `-[:MAPS_TO_GUIDANCE]->Guidance`.

**`DriverUpdate`** (the fact)

| field (placeholder name) | what's decided | structural role decided? |
|---|---|---|
| `driver_state` | the driver's change **direction**; lives here, **never in the name** | ⏳ exact vocabulary deferred |
| `magnitude_value` + `magnitude_unit` | the **driver's own** change size (NOT the stock effect); **nullable** | ⏳ precise definition deferred |
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
| `FROM_SOURCE` | `DriverUpdate` → `Event` | this fact came from this event (evidence) | always, for event-sourced facts |
| `EXPLAINED_BY` {verdict} | `Event` → `DriverUpdate` | this event's move is explained by this fact | 0, or 1 per producer |
| `INFLUENCES` / `PRIMARY_FILER` {returns} | `Event` → `Company` | the realized stock move (existing edge) | existing |

- **`FROM_SOURCE` and `EXPLAINED_BY` are SEPARATE edges** (a fact can be *mentioned* in an event without *explaining* its move) — never collapse the verdict onto the provenance edge.
- **No `BASED_ON`.** Trends are **queried** (each fact's `driver_state` gives the direction and `magnitude` the value), never stored as links.
- **Duplicate mentions** of the same fact across different events = **separate `DriverUpdate`s** (keyed by event); collapsed in **read-time views**, never in storage.
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

The catalog build already yields each fact's **identity + links + quote** (driver · company · event · date · quote) — enough to mint a `DriverUpdate` and wire `OF_DRIVER` + `FROM_SOURCE`. (The company comes via the event, not a direct link.) It does **not** yet produce `driver_state` / `magnitude` (a cheap parse of the quote it already holds) or the attribution (a separate producer step).

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
   │    driver_state     change direction  (NEVER in the name)             │
   │    magnitude_value  driver's OWN change size        (nullable)        │
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

## State + Magnitude (DriverUpdate) — PROPOSED, still OPEN (pending final approval)

> Output of the property-meanings pass, grounded in a census of EVERY real Fable driver record (CAKE 594 + 14-ticker 673 + raw menus). **NOT yet locked** — replaces the placeholder `driver_state` / `magnitude_value` / `magnitude_unit` rows in §2 once approved. **Core principle:** the state words are *helper buckets* for grouping/querying; the verbatim **`quote` is the truth** — so the enum can stay small and the quote carries precision.

**Why a routed enum (not one flat list):** the real data breaks a single up/down list — ~1 in 6 facts have no up/down (risk talk, plain snapshots, "stabilized", guidance ranges). So state is **routed by the driver's kind**, and a producer-side **GATE** ("did the driver actually change at this event? if no → write NO DriverUpdate") removes the no-change pile.

**1. `fact_type` — on the `Driver`** (the driver's **permanent kind**, set ONCE at catalog time by the catalog creator — never per event). **One of 4:**

| `fact_type` | use when the Driver is about… | examples |
|---|---|---|
| `metric` | a value, KPI, **condition**, cost, rate, price, trend, or qualitative business condition | `same_store_sales` · `traffic` · `commodity_cost` · `consumer_sentiment` · `market_share` |
| `guidance` | a company outlook, target, forecast, plan, or expected future value | `eps_guidance` · `revenue_guidance` · `capital_expenditure_guidance` |
| `surprise` | an actual result compared to an expectation | `eps_surprise` · `revenue_surprise` · `same_store_sales_surprise` |
| `action_event` | a discrete action, decision, incident, or one-off event | `dividend` · `share_repurchase` · `restaurant_closure` · `ceo_succession` · `asset_impairment` |

**Simple rule to pick it:** can go up/down over time → `metric` · future outlook → `guidance` · actual vs expectation → `surprise` · happened as an action/event → `action_event`.

*(`condition` is folded into `metric` — a qualitative condition is just a metric with no number; its `magnitude` stays null. Keeps direction neutral + removes the messiest lane.)*

**Catalog-creator instructions:** add `fact_type` (one of the 4 above) on **every** `Driver`. It is the driver's **permanent kind** — the *changing* state goes later on the `DriverUpdate`, never here. **Never put state / direction in `Driver.name`** (R7).

**2. `state` — on `DriverUpdate`**, chosen from the driver's `fact_type` lane; `unknown` always allowed; raw `quote` always kept:

| `fact_type` | `state` — pick one |
|---|---|
| `metric` *(incl. qualitative; magnitude stays null)* | increased · decreased · unchanged · mixed · unknown |
| `guidance` | introduced · raised · lowered · reaffirmed · withdrawn · unknown |
| `surprise` | beat · in_line · missed · unknown |
| `action_event` | occurred · resolved · continued · canceled · suspended · unknown |

*(`narrowed` is NOT a state — it is derived from the comparison fields below.)*

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

**Sub-decisions — current LEANINGS (still OPEN suggestions, NOT approved / NOT finalized):**
1. Fold `condition` into `metric` → **4** types. *(leaning; vs keep `condition` = 5 types)*
2. COMPARISON fields: **store** the prior baseline on each update — verifiable + self-contained. *(leaning; vs derive from the prior update = leaner)*
3. Field **names** kept as written (`level_value` / `change_value` / …). *(leaning; vs shorter)*
4. Keep **both** `mixed` and `unknown`. *(leaning; vs merge)*

⛔ **NOTHING here is finalized** — these 4 are working suggestions, and the ENTIRE `state` + `magnitude` design (and the rest of the `DriverUpdate` property *meanings*) remains an open **PROPOSAL** pending final owner sign-off **and** the empirical producer test. Nothing is locked into the decided §1–§8.

**Where to STOP (don't over-trim):** keep the **natural lane words** (`raised`, `beat`, `withdrawn`, `occurred`) — do NOT collapse to a universal `up/down/flat`. Those are **tradeable signals you'll query** ("all `withdrawn` guidance" = bearish); collapsing them forces "say `occurred`, re-read every quote," which kills the query. This is the minimal floor that keeps clarity + trading-use.

---

## Deferred — NOT decided yet (listed only so they aren't built prematurely or forgotten)

1. **Property NAMES *and* meanings (the next pass):** every field name above is a working placeholder — to finalize the name AND the meaning of each: exact `driver_state` vocabulary · `magnitude` precise definition **and** the type-gating-vs-XBRL rule (**store the number for now**; switch to null-and-link only once an XBRL linking pass + a link-checking validator exist, or the value is lost) · `weightage` scale/normalization · `confidence` scale + how it differs from `weightage`.
2. **Exact `id` key strings** — the principle is locked (§4: fact = event + driver + `fact_scope`; verdict = + producer); the literal format is a build detail.
3. **KPI-sourced facts** (`source_id = "fiscal_ai:…"`) have no real `Event` node → how `FROM_SOURCE` (and therefore the company lookup) is handled.
4. **TODO:** add `driver_state` + `magnitude` extraction to the catalog reader (or producer) — after the meanings in #1 are decided.

*Naming note: the verdict is the `EXPLAINED_BY` edge (`Event → DriverUpdate`) — "attribution," the term chosen over "impact"; in this design there is no separate verdict node.*
