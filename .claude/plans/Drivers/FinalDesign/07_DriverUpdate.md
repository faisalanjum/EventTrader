# 07 · DriverUpdate record

**What this is:** the event-level **fact** — how a producer records what happened to a driver in one event, plus the buy/sell **verdict**. This is Track B core.

> **Status split:** the §0 creation contract, `fact_type`, and `driver_state` lanes are **`[LOCKED]`** (2026-06-15). DU-13…DU-18 are now superseded by `09_DriverUpdate_Fields.md`; keep the blocks here as history/cross-reference, but use 09 as the source of truth for stored DriverUpdate fields. The `EXPLAINED_BY` verdict is **`[LOCKED]`** (owner 2026-07-03, via the Track B plan — `12_TrackB_FactPipeline.md` §10.1: explained_target key wording, verdict-edge evhash16 recipe, and DailyCompanyMoveEvent own-label pinned there).
> Historical source = `WIP/DriverGraphSchema.md`. Units/family/fact_scope are cross-referenced, not re-locked here.

---

## A. What a DriverUpdate is

#### DU-01 — A DriverUpdate = a real event-level fact  `[LOCKED]`
- **Plain:** Records one real fact about a driver in one event — not a mere mention.
- **Rule:** A reported state, change, surprise, guidance item, or action. NOT a mention; NO "X→Y change" required (a CEO resignation / FDA approval / store closure is valid). A single event is valid; recurrence is a read-time view, never a write gate.
- **Why:** The fact layer is the tradeable signal; a mention isn't a fact.
- **Source:** DriverGraphSchema.md §0 pt 2/6
- **Replaces:** old "= a change" + "seed only if >2 events" — 95_Supersession #4, #5

#### DU-02 — Producers are the only creators  `[LOCKED]`
- **Plain:** The catalog build makes the driver CLASS; producers make every DriverUpdate.
- **Rule:** Catalog build makes the complete Driver CLASS (name + fact_type + optional family/`SAME_AS` links — class-level links only; XBRL concept/member links live on the FACT, never the class: FS-21 / 09 §3 / 10 PIPE-21), NEVER a DriverUpdate. Producers (earnings-learner / news-driver), LIVE and BACKFILL, are the ONLY creators. No build-time seeder. KPI-only evidence (no event) makes a name only.
- **Data note (2026-07-10):** The current FiscalAI KPI/segment snapshot for source inventory and audits lives at `data/fiscal_ai_segments/runs/2026-05-07/`. This is provenance only; it does not create facts or bypass producer judgment.
- **Why:** Separating class-creation from fact-creation keeps the catalog clean and facts event-sourced.
- **Source:** DriverGraphSchema.md §0

#### DU-03 — The GATE (real fact vs bare mention)  `[LOCKED]`
- **Plain:** A producer writes a DriverUpdate only if the event carries a real fact. A bare mention → nothing.
- **Rule:** A producer-side GATE asks: does this event carry a real fact about the driver (state/change/surprise/guidance/action)? A bare mention → NO DriverUpdate. Generic risk boilerplate ("litigation could harm us", "weather may affect results") → dropped.
- **Why:** The gate removes the no-fact pile so the graph holds only real facts.
- **Source:** DriverGraphSchema.md §0 · fact_type/state section

#### DU-04 — Who fills what  `[LOCKED]`
- **Plain:** The catalog reader saves only name + quote. The producer fills state + numbers, after the gate.
- **Rule:** The reader writes NONE of the fact fields (name + quote only). The PRODUCER fills driver_state + numbers (it has prior-period memory) AFTER the gate. The quote is stored only for a real state/value/change (never a bare mention) — the quote is the final truth.
- **Why:** The reader coins names; only the producer, judging a real event, can assign a state/number.
- **Source:** DriverGraphSchema.md §2 · fact_type/state §4

## B. fact_type

#### DU-05 — The 4 fact_types (definitions)  `[LOCKED]`
- **Plain:** metric · guidance · surprise · action_event (value-free).
- **Rule:** **metric** = any standing variable readable again over time (number/cost/price/rate/count/ratio OR a qualitative condition: weather, sentiment, policy-in-force, labor, brand) — NOT only a number · **guidance** = the company's own forward outlook/target/forecast · **surprise** = an actual result vs an EXPECTATION (consensus or own prior guide), NOT vs a prior-period actual (that's a metric change) · **action_event** = a discrete thing that happened (decision, transaction, incident, approval, one-off charge). Validated on all 1,282 names: 0 fit none.
- **Why:** The flavor routes legal state words + whether guidance period / company_confirmed attaches.
- **Source:** DriverGraphSchema.md fact_type lock (2026-06-15)

#### DU-06 — The persistence-test decider  `[LOCKED]`
- **Plain:** metric vs action_event? "Is there a standing level I could re-read next quarter?" Yes → metric, no → action.
- **Rule:** Persistence test: between two events, is there a standing level/severity you could re-read? Yes → metric · No → action_event. A `_surprise`/`_guidance` framing OVERRIDES. Outlook verbs (expect/anticipate/target/plan to) → guidance, never a metric state. Dual framing allowed (`dividend` = action_event vs `dividend_per_share` = metric). Bare-root defaults: litigation/convertible_notes/dividend_policy/restructuring_costs → metric; corporate_restructuring/asset_impairment → action_event.
- **Why:** One clean test resolves the only genuinely ambiguous boundary.
- **Source:** DriverGraphSchema.md fact_type lock

#### DU-07 — fact_type set once, as the final build step  `[LOCKED]`
- **Plain:** A strong model sets fact_type once per driver at the end of catalog creation. No fact_type → no fact.
- **Rule:** fact_type is the driver's permanent KIND, set ONCE per Driver (never per event) as the MANDATORY final catalog-creation step, by a STRONG model (Opus) — not the blind reader/weak model. A Driver with no fact_type → any write REJECTED. Keep the 4 definitions exactly; add NO extra clauses/examples (a tested clause overfit: fixed 2, broke 1). Runs once per Driver → cost trivial.
- **Why:** A permanent per-driver kind routes everything downstream; overfit definitions break generalization.
- **Source:** DriverGraphSchema.md fact_type lock

## C. driver_state

#### DU-08 — driver_state lives on the fact, from the fact_type lane  `[LOCKED]`
- **Plain:** The state word (what happened) is on the DriverUpdate, never the name, from the driver's lane.
- **Rule:** driver_state is on the DriverUpdate (never the name), set by the PRODUCER (never at catalog time), chosen from the driver's fact_type lane. `unknown` = rare last resort; the quote is always the truth. State words are helper buckets for grouping; the quote carries precision.
- **Why:** The state changes per event → lives on the fact; out of the name → preserves reuse.
- **Source:** DriverGraphSchema.md driver_state lock (2026-06-15, 3,825 quotes)

#### DU-09 — metric lane + pick-first-match ladder  `[LOCKED]`
- **Plain:** metric states: increased/decreased/unchanged/mixed/reported/persists/unknown — pick the first that matches.
- **Rule:** Pick the FIRST match (ignore good/bad = stock_impact): (1) direction stated → increased/decreased ("weather worsened" → increased = MORE of it) · (2) same driver up in some parts + down in others → mixed (two DIFFERENT drivers opposite = split, not mixed) · (3) explicit flat → unchanged · (4) ongoing, no direction → persists · (5) bare value, no comparison → reported (prior value present → increased/decreased) · (6) real fact, no readable state → unknown. `narrowed` isn't a state (derived); `persists` not `continued`.
- **Why:** The ordered ladder removes ambiguity deterministically.
- **Source:** DriverGraphSchema.md driver_state

#### DU-10 — guidance + surprise lanes  `[LOCKED]`
- **Plain:** guidance: introduced/raised/lowered/reaffirmed/withdrawn. surprise: beat/in_line/missed (vs the expectation).
- **Rule:** **guidance** = introduced (first time) · raised/lowered (prior guide moved) · reaffirmed (kept) · withdrawn (pulled) · unknown. **surprise** = beat · in_line · missed · unknown, vs the EXPECTATION (consensus or the company's own prior guide/target) — NOT vs a prior-period actual (that's a metric change).
- **Surprise-state derivation (ISS-16 as amended by OD-13, owner 2026-07-06 via `66` §0.R):** the trigger is still a stated actual-vs-EXPECTATION comparison (consensus or own prior guidance), and the stated actual always also writes the metric fact. Code computes only polarity-free `position` (above / inside / below / at_floor / at_ceiling) and sets `in_line` when there is no favorability wording and the actual is inside a closed range or exactly at a boundary. Code NEVER maps above→beat or below→missed, never keyword-matches, and never assumes higher=better. `beat`/`missed` are producer meaning judgments from the full phrase, negation/polarity/scope-aware; wordless outside-range cases need a transient discarded polarity proof, else `unknown`. A TEMPORAL comparison (prior_year/sequential) is a metric change, never a surprise.
- **Why:** Forecast-moves and beat/miss are their own signals, distinct from a metric's direction.
- **Source:** DriverGraphSchema.md driver_state · ISS-16 lock (`12` §10.5) · OD-13 amendment (`66` §0.R)

#### DU-11 — action_event lane + decision ladder  `[LOCKED]`
- **Plain:** 10 action states via a step-by-step ladder: is the action terminal or not, then pick the word.
- **Rule:** Lane = at_risk · announced · occurred · continued · resolved · canceled · suspended · rumored · failed · unknown. Domain-neutral ladder (copy ONLY the ladder into prompts, never the validation notes): **Step 0** classify the LATEST stage of one action; **Step 1** finality gate — **TERMINAL** {`failed` = ended involuntarily (outside party blocked / external condition unmet; incl. declining an offer never committed to) · `canceled` = the company's OWN free-choice withdrawal · `resolved` = a two-sided dispute settled · `occurred` = completed} vs **NOT-TERMINAL** {`rumored` = third-party-reported, company-unconfirmed (a denial keeps it rumored) · `at_risk` = a specific source-flagged adverse threat, not the company's plan · `suspended` = paused/resumable · `announced` = the company stated its OWN action before completion · `continued` = a prior action still ongoing}. Conventions: shelve/postpone → suspended; scrap/abandon/withdraw → canceled; threat → at_risk until executed → failed. **at_risk STRICT:** only a specific current source-flagged adverse not-yet-happened non-plan event; generic boilerplate is gate-dropped (rumored = unconfirmed ACTION; at_risk = adverse THREAT).
- **Why:** Actions have a lifecycle; the ladder + strict at_risk keep the 10 words unambiguous and prevent flooding.
- **Source:** DriverGraphSchema.md driver_state + action ladder (rumored/failed added & validated 2026-06-17)

#### DU-12 — Lane check (hard-fail)  `[LOCKED]`
- **Plain:** Code checks the state is a legal word for that fact_type; a driver with no fact_type can't accept a fact.
- **Rule:** At write time, code asserts driver_state ∈ the driver's fact_type lane (deterministic, hard-fail, zero LLM). A Driver with no fact_type → REJECTED. Producer proposes; code decides. (App-side — Neo4j can't check one field against another.)
- **Why:** Keeps every fact's state legal for its kind.
- **Source:** DriverGraphSchema.md · DriverCatalogProcess.html

## D. Number + comparison layer  `[SUPERSEDED by 09_DriverUpdate_Fields.md]`

> **`09_DriverUpdate_Fields.md` is the FINAL field spec (2026-07-02, owner-adjudicated). Where the blocks below differ, 09 wins.** Amendments 09 makes: `level_bound` **cut** → self-describing shapes (point = BOTH bands · low-only = floor · high-only = ceiling) + a transient `level_shape_hint`/`comparison_shape_hint` (producer emits, code cross-checks vs the slots, hard-fails on mismatch, **never stored**) · `value_text` + `conditions` **added** (guidance-only, hard-guarded) · the fact `evhash16` **retired** (kept on the verdict edge) · sharpenings: metric lane **forbids `consensus`** (→ route to `_surprise`), `level_unit` **required when any level_*/comparison_* is non-null**. DU-15/17 confirmed; DU-13/14/16/18 amended.

#### DU-13 — The number + comparison fields  `[AGREED · fields being finalized]`
- **Plain:** A set of nullable number fields; fill only what the source states; all-null = a qualitative fact (never invent a number).
- **Rule:** All nullable; fill only what applies; all fields null = qualitative-only (the quote is the truth, NEVER fabricate a number).
  - `level_low` = the stated value · low end of a range · the value if a floor (≥)
  - `level_high` = high end of a range · the value if a ceiling (≤)
  - ~~`level_bound`~~ — **CUT by 09:** shape is self-describing from the slots (point = both bands · floor = low-only · ceiling = high-only), verified by a transient (never-stored) `level_shape_hint`
  - `level_unit` = unit of level_* (the 9-enum)
  - `change_value` = the SIGNED delta itself (NOT the level) — "+60 bps" → +60
  - `change_unit` = unit of change_value (may differ from level_unit)
  - `comparison_low` / `comparison_high` = the stated prior/baseline shape using the same grammar as level values: a single baseline fills BOTH fields; a range fills low/high; low-only/high-only mean stated floor/ceiling
  - `comparison_baseline` = which baseline (DU-15)
- **Why:** One nullable number layer holds any fact's numbers without fabricating.
- **Source:** DriverGraphSchema.md number layer (AGREED 2026-06-16)

#### DU-14 — Level shape read from the slots  `[AGREED]`
- **Plain:** Whether it's a point, range, floor, ceiling, or no-number is read from which slots are filled — no separate "shape" field.
- **Rule:** *(amended by 09 — self-describing shapes, no `level_bound` field):* **point** → `level_low == level_high` (fill BOTH bands) · **range** → level_low < level_high · **floor** (≥) → level_low only · **ceiling** (≤) → level_high only · **no number** → all null. A shape is *closed* when both bands are present (point / closed range). The producer emits a transient `level_shape_hint` (and `comparison_shape_hint` when comparison numbers exist); the writer cross-checks it against the slots, hard-fails on mismatch, then **discards** it (never stored) — this catches the forgotten-high (point→floor) slip AND the forgotten-low slip the old `level_bound` field couldn't. Same grammar for `comparison_low/high` (a single-value baseline sets BOTH). *[Signed value-space — OD-12, owner 2026-07-06 (66 §0.R OD-12 · 09 §3): values are SIGNED on the driver's numeric axis (a net quantity's loss is negative; a charge AMOUNT positive, a benefit/reversal negative); value-first, so "a loss of up to $X" → value ≥ −X → floor, and `level_low`/`level_high` are the algebraic min/max.]*
- **Why:** The slots already encode the shape; a separate field would be a redundant, drift-prone copy.
- **Source:** DriverGraphSchema.md number layer

#### DU-15 — comparison_baseline (one primary)  `[AGREED]`
- **Plain:** What the number is compared against — store ONE primary baseline; null when it's not a temporal prior.
- **Rule:** `comparison_baseline` ∈ {consensus, prior_year, sequential_period, previous_guidance, null}. Store the PRIMARY only (the source's headline; tiebreak prior_year > sequential_period); the rest stay in the quote. `null` when NOT a temporal prior baseline (vs peers / vs 2019 / any anchor-year / a streak). "Exceeded expectations" is fact_type-aware: a surprise fact → consensus; a guidance fact's "exceeded our guidance" → previous_guidance (else null). Rule of thumb: consensus = analyst/Street/market; previous_guidance = clearly company guidance. **ISS-16/OBJ-2 amendment (owner 2026-07-03):** on the METRIC lane BOTH expectation baselines are FORBIDDEN — a metric fact's `comparison_baseline` is temporal-only ({prior_year, sequential_period, null}); an "exceeded our guidance"/consensus comparison on a reported actual does NOT sit on the metric fact, it routes to the `_surprise` fact (which stores the expectation baseline). Expectation baselines thus live only on surprise (and guidance-revision) facts.
- **Why:** One queryable baseline per fact; the rest preserved in the quote.
- **Source:** DriverGraphSchema.md hard rule 5

#### DU-16 — The 7 hard rules (code-enforced)  `[AGREED]`
- **Plain:** Seven write-time checks; the producer proposes, code decides, reject on violation.
- **Rule:** (1) *[amended by 09 — no `level_bound`]* shape is self-describing (floor = level_low only · ceiling = level_high only · point = both bands equal); the transient `level_shape_hint` is cross-checked and hard-fails on mismatch. (2) SIGN — a present change_value with a directional state (increased/decreased/raised/lowered) must match sign (+ increased/raised, − decreased/lowered); non-directional impose no sign rule. *[OD-13 amendment, owner 2026-07-06 — 66 §0.R OD-13: `beat`/`missed` REMOVED from this sign rule. Surprise favorability is not a numeric sign — a lower-better beat has a NEGATIVE arithmetic delta, and a surprise fact stores no favorability-signed change_value (magnitude is read-derived; a rare source-stated surprise delta is arithmetic-signed).]* (3) STORE-WHEN-STATED baseline — comparison_* hold a baseline ONLY when the source states it, NEVER derived from another node; a stated baseline fitting no enum ⇒ comparison_baseline=null with the number still stored. (4) per-X in the NAME, unit stays base (cross-ref UNIT-08). (5) ONE primary baseline (DU-15). (6) change_value store-when-stated only — leave null if derivable from level+comparison (point/closed-range delta is derivable → no third copy; floor/ceiling has no derivable delta); a ranged move stays in the quote (no change_high, never a single endpoint). (7) rate-vs-level routing — a change-flavored unit (percent_yoy/percent_sequential/percent_points/basis_points) goes in change_value when the driver has its OWN absolute level ($ revenue, move → change), but in level_low when the driver IS a rate/growth metric whose value is that rate (same_store_sales "rose 3%" → level_low=3, percent_yoy). Guidance facts use the OD-11 §09 rule: a %-only guide stores the growth basis in `level_unit`, while `change_value` is reserved for the guide's own revision size.
- **Why:** These are the exact number-mis-slotting failure modes; code-enforcing them keeps values correct.
- **Source:** DriverGraphSchema.md hard rules 1-7

#### DU-17 — Units (cross-ref)  `[AGREED]`
- **Plain:** level_unit and change_unit both come from the 10-unit enum; they may differ; there's no comparison_unit.
- **Rule:** `level_unit` and `change_unit` both draw from the 10-unit enum (see the Units section, UNIT-01; `percent_sequential` added by OD-11). They MAY differ (a bps change on a % level). There is NO `comparison_unit` — comparison values share `level_unit`; a different-unit baseline stays in the quote.
- **Why:** Reuses the one shared unit vocabulary; a separate comparison unit would be dead weight.
- **Source:** DriverGraphSchema.md unit enum · UnitExtraction.md · cross-ref Units

#### DU-18 — Deliberately-NOT fields  `[AGREED]`
- **Plain:** Fields we intentionally do NOT add (they're derivable or live elsewhere).
- **Rule:** Do not re-add: `mid` (derive from low/high) · `usd_per_share` (per-share is in the name) · `unit_raw` (raw wording is in the quote) · `change_high` · `comparison_unit`. — **AMENDED by 09:** the old free-text `qualitative` field DOES return as **`value_text`** (guidance-only, numberless-only, value-aware lint) — verified because the running system renders `value_text` to the predictor but never renders the `quote`, so DU-18's "the quote carries it" premise was false. — NOTE: the accounting basis (adjusted/diluted) gets no field either, but it lives in the **measurement** slot of fact_scope, **NOT the name** (reversal #2).
- **Why:** Each is derivable or has a proper home; adding them invites drift.
- **Source:** DriverGraphSchema.md line 333 (basis line corrected)
- **Replaces:** schema:333 "accounting_basis in the name" — 95_Supersession #2

## E. Edges + identity

#### DU-19 — Fact key (recap)  `[LOCKED]`
- **Plain:** A fact's identity = event + driver + fact_scope; code builds it; re-runs update in place.
- **Rule:** Fact key = event + driver + fact_scope (NO producer → two readers of one fact converge to one node). Code builds every key; re-running a producer MERGEs in place, never forks. *(Amended by 09: the fact-node `evhash16` is **retired** — derivable + reader-free; no-op re-runs are detected by direct field comparison. The verdict-edge `EXPLAINED_BY.evhash16` is unaffected — see DU-22.)* Full identity spec = the fact_scope section (FS-01…04).
- **Why:** A deterministic, producer-free key keeps identity stable across re-runs.
- **Source:** DriverGraphSchema.md §4 · cross-ref fact_scope section

#### DU-20 — A DriverUpdate's edges (FROM_SOURCE ≠ EXPLAINED_BY)  `[LOCKED]`
- **Plain:** Every fact links to its driver + its source event + (if period-bearing) a period. The verdict is a SEPARATE edge.
- **Rule:** `OF_DRIVER` → Driver (always, exactly 1) · `FROM_SOURCE` → Event (always — provenance, "this fact came from this event") · `HAS_PERIOD` → DriverPeriod (period-bearing facts). The verdict `EXPLAINED_BY` (Event → DriverUpdate) is a **SEPARATE** edge — 0 or 1 per producer, added only when a producer attributes the move. **NEVER collapse the verdict onto `FROM_SOURCE`** (a fact can be reported without explaining the move). Company is never in the driver layer — reached via Event → Company. **Macro/news moves without a filing event** attach the verdict to a thin **`DailyCompanyMoveEvent`** (`id = dcm:<company_cik>:<trade_date>` · `{trade_date, created}` · `-[:FOR_COMPANY]->Company` · `-[:ON_DATE]->Date`); the realized return is **read from the existing `Date-[:HAS_PRICE]->Company`**, never duplicated on the node; the News article stays the `FROM_SOURCE`. *(Core shape LOCKED 2026-07-02; open details — significance threshold, pure-macro source — in `90_OpenItems`.)* **Cross-ref (FS-26, owner 2026-07-11):** `CONTINUES_AS` (03 §J) is a class-level Driver–Driver continuity link minted live by producers — never part of this fact-edge inventory.
- **Why:** Provenance (always) and attribution (only when blamed) are different facts; merging them would fabricate attributions.
- **Source:** DriverGraphSchema.md §3 (edges) lines 132/134/138

## F. EXPLAINED_BY verdict  `[LOCKED — owner 2026-07-03 via 12 §10.1]`

#### DU-21 — The verdict is the EXPLAINED_BY edge  `[LOCKED]`
- **Plain:** The buy/sell verdict is not a node — it's the properties on the Event→DriverUpdate edge, added only when a producer blames the move on the fact.
- **Rule:** The verdict is NOT a node — it's the property-laden `EXPLAINED_BY` edge (Event → DriverUpdate), added only when a producer believes that fact caused the stock move. A fact may exist with no verdict. It points at the Event (not the Company) because it's graded against the realized return on Event→Company. Term chosen = "attribution" (over "impact").
- **Why:** Attaching the verdict to the event lets it be scored against that event's realized move in one hop.
- **Source:** DriverGraphSchema.md §2/§3 (AGREED 2026-06-16)

#### DU-22 — The 3 orthogonal verdict axes  `[LOCKED]`
- **Plain:** A verdict has direction, force, and certainty — three independent numbers — plus who judged and when.
- **Rule:** `stock_impact` ∈ {long, short} (the driver's DIRECTION of push, can oppose the net move) · `weightage` ∈ {0.1…1.0 deciles} or null (the driver's standalone FORCE — an INDEPENDENT estimate, NOT a share; never summed, never forced to max; a move may be partly unexplained; null = sure of direction, can't size) · `confidence` ∈ {0…100 deciles} (how sure the attribution is TRUE, orthogonal to weightage). Plus `produced_mode` ∈ {live, backfill} (live wins, never overwritten by backfill; excluded from evhash16) · `llm_producer`. Verdict key = **explained_target** + driver + fact_scope + **producer**, where explained_target ∈ {Event, DailyCompanyMoveEvent} (wording locked 2026-07-03 via 12 §10.1; two producers can disagree without colliding).
- **Why:** Direction, force, and certainty are genuinely independent; a share/sum would force a false 100%.
- **Source:** DriverGraphSchema.md EXPLAINED_BY (FINAL 2026-06-16)

#### DU-23 — Read-time only + PIT  `[LOCKED]`
- **Plain:** The "share of the move" is computed at read time, never stored; the real return is never shown to the predictor.
- **Rule:** Read-time only (never stored): `share_i = weightage_i / Σweightage` within one (event, producer); `signed_force = weightage × stock_impact`. PIT: the realized share / actual return is NEVER stored on the verdict and NEVER shown to the predictor. Grading is aggregate — reality gives one net return, so grade a verdict SET on net sign/magnitude + relative ranking, never a per-driver "true share."
- **Why:** Storing/showing the realized share would leak the answer (look-ahead); shares are derived, not truth.
- **Source:** DriverGraphSchema.md verdict rules

#### DU-24 — Verdict validator  `[LOCKED]`
- **Plain:** Code checks every verdict edge has a valid direction, decile confidence, and decile-or-null weightage — no sum rule.
- **Rule:** Deterministic hard-fail: every `EXPLAINED_BY` edge has `stock_impact` ∈ {long, short}, `confidence` ∈ {0,10,…100}, `weightage` ∈ {0.1,…1.0} or null — both on a 10-step decile ladder (no false-precision floats; keeps evhash16 stable across re-runs). NO cross-edge sum constraint.
- **Why:** Deciles keep the value-hash stable; no-sum protects the independent-force design.
- **Source:** DriverGraphSchema.md verdict validator
