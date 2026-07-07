# 14 · Build readiness

**Purpose:** one clean list of what must still be designed or closed before the Driver system can be handed to coding agents.

**Short answer:** the core Track A / Track B / Track C design is strong, but the full system is not yet code-ready. The biggest missing piece is the running layer: how new facts are produced, backfilled, retried, checked, and refreshed over time. A second smaller set of exact-rule fixes is also required because those rules affect permanent graph identity.

This file supersedes `StillTodo.md`.

**Authority note:** this file is a readiness checklist, not the final rule source. When an item is closed, the actual rule must be written into its owning design doc (`03`, `09`, `10`, `12`, `90`, etc.) and then this file may be marked closed.

**Priority terms:** `P0` means blocks a safe coding handoff. `P1` means the owner/home must be clear before handoff, but the actual build may happen later if explicitly deferred.

---

## 1. What is already solid

Do not reopen these as blank-slate design work.

| Area | Status |
|---|---|
| Track A catalog shape | Strong enough as the catalog design base. |
| Track A build pipeline | Strong enough as the batch catalog-build plan, with listed open decisions still to close. |
| Track B DriverUpdate shape | Strong enough as the fact model: fields, periods, slices, units, XBRL hooks, and validators are mostly defined. |
| Track C old guidance | Decided: archive/retire old guidance; never replay old `GuidanceUpdate` rows into production truth. |
| Old guidance role | QA evidence only. Fresh guidance must be produced from source documents by the new system. |

Important caveat: "solid" does not mean "coding agents can start with zero ambiguity." The items below must still be closed.

---

## 2. P0 missing design: the running layer

This is the largest remaining design section. It should become the actual "part 2" production/update plan.

| # | Needed design | What must be defined |
|---|---|---|
| 1 | Source schedule | Which reports, transcripts, filings, and news run; source priority; live cadence; backfill order. |
| 2 | Run ledger | Per `source_id × fact_type`: `pending`, `running`, `done`, `parked`, `failed`; ruleset version; model version; hashes; retry count; timestamps. |
| 3 | Producer packets | Exact input/output contract for every fact type, especially fresh `fact_type=guidance`; no human in the loop. |
| 4 | Verdict / attribution producer | Exact contract for `EXPLAINED_BY` stock-move judgments: decile fields, PIT/no-look-ahead inputs, Event vs DCM target, two-producer split, and whether it may create a missing `DriverUpdate`. |
| 5 | Report processing scope | Decide whether 10-K/10-Q facts are re-extracted like other sources or created through the dormant XBRL-link rider; this bounds historical backfill cost. |
| 6 | Historical backfill | Freshly process 2023-2026 sources, including the 894 old-guidance sources, without replaying old guidance rows. |
| 7 | QA gates | Recall against the Track C archive, field checks, dual-producer agreement, thresholds, and rollout blockers. |
| 8 | Prediction / learner cutover | Read new Driver facts, stop reading `guidance_history.v1`, and tolerate empty guidance until fresh backfill exists. |
| 9 | Incremental refresh | Append new facts, handle amendments, freeze old decisions unless an explicit repair path is invoked. |
| 10 | Model policy and execution path | Exact model per job, number of runs, grader model, fallback rules, and allowed execution path. Current "Opus reads / Sonnet classifies" is a lean, not a final full policy; any metered SDK path needs explicit owner approval. |
| 11 | Source edge cases | Filing amendments, corrected filings, reissued guidance after withdrawal, duplicate source IDs, pure macro/news days. |
| 12 | Retirement gates | Old guidance deletion may happen before fresh backfill only if the archive is complete, old consumers are safe, and the owner accepts the temporary guidance gap; otherwise deletion waits. |

---

## 3. P0 exact-rule fixes before coding

These are not large sections, but they are dangerous because two coding agents could otherwise create different permanent graph data.

| # | Issue to close | Why it matters | Required design close |
|---|---|---|---|
| 1 | `quote_hash` recipe | Fact IDs can fork if hash inputs differ. | Pin algorithm, exact normalization, exact value-signature recipe, and examples. |
| 2 | `quote_hash` rerun idempotency | A rerun that sees only one old collider could write the bare ID and create a duplicate. | Collision handling must be stable across partial reruns, not only inside one batch. |
| 3 | Measurement tokenization | "adjusted diluted EPS" could become one token or two; a dropped token could merge different number versions. | **✅ RESOLVED — owner-approved 2026-07-06 (66 §0.R OD-9):** open-vocab, source-grounded, NEVER-DROP sink. Producer copies exact source spans → transient `measurement_raw_spans`; code alone normalizes (lowercase → each non-alphanumeric run → `_` → trim → collapse); MAXIMAL contiguous spans → one token ("adjusted diluted" → `adjusted_diluted`); measurement = fail-closed bucket for any modifier not losslessly captured elsewhere — unsure → keep, never drop; no write-time synonym merge/alias/list/human. Amends 03 FS-25; back-ported to 66/03/09/11/12/90/95. |
| 4 | Unit-family grouping | Read-time series grouping can differ by implementer. | **✅ RESOLVED — owner-approved 2026-07-06 (66 §0.R OD-10):** replace the read-time unit-family map with a code-written **`series_unit`** stamped at WRITE; read groups by plain equality on `series_unit` (no family map, no unknown-absorption). Delta-only facts fold onto the driver's evidence-unique axis (never name-match; unstated growth-frame / cc-GAAP / cold-start → fail closed to exact `change_unit`/`unknown`); money canonicalized to the driver's one scale within a currency; `series_unit` is a grouping tag — values stay source-faithful. Amends 09 §6.1 / 11 T12.6 / 12 FACT-33; back-ported to 66/09/11/12/90/95. |
| 5 | Sequential percent guides | `09 §7` formerly hard-stamped percent-only guidance as `percent_yoy`, which was wrong for sequential-guiding companies. | **✅ RESOLVED — owner-approved 2026-07-06 (66 §0.R OD-11):** read the growth basis from the source; **add `percent_sequential`** (period-agnostic, own family; UNIT-01 now 10 units, UNIT-12 resolved); metric-type gate first (static-% level bare "up X%" → `unknown`); bare dated growth → `percent_yoy`, sentinel → `unknown`; measurement adjustments (cc/organic) go in the measurement slot and never decide the basis. Amends 09 §7 · UNIT-01/12; back-ported to 66/09/04/11/12/14/90/95. |
| 6 | Negative / loss values | "Loss of up to $2B" can be represented as a ceiling in loss-space or a floor in signed-space. | **✅ RESOLVED — owner-approved 2026-07-06 (66 §0.R OD-12):** SIGNED value-space on the driver's numeric axis (not good/bad); value-first ("loss up to $X" → floor, the mirror of "revenue up to $X" → ceiling); no loss-magnitude drivers (02 naming pin); amends 09 §3 / 07 DU-14 shape grammar; back-ported to 66/09/07/02/90/95. |
| 7 | Lower-is-better metrics | Cost, capex, tax rate, churn, and similar metrics can invert beat/miss logic. | **✅ RESOLVED — owner-approved 2026-07-06 (66 §0.R OD-13):** favorability = producer MEANING judgment, code stays polarity-free (computes position + `in_line` only); wordless-outside-range → transient polarity proof else `unknown`. Amends ISS-16 (12 §10.5) + DU-16.2; back-ported to 12/07/90/95. |
| 8 | Chronological writes | Late old-dated filings can corrupt guidance state, withdrawal logic, and the Event-vs-DCM single-target rule. | **✅ RESOLVED — owner-approved 2026-07-06 (66 §0.R OD-14):** order by public source time; guidance movement READ-DERIVED (bare→`unknown`, read layer derives `effective_driver_state`; validator skips `unknown`) so no stored-state staleness; withdrawal fan-out stays WRITTEN but strictly bounded (clear-withdrawal + exact resolved-scope, open guides only, add-only, no delete); amendments = new facts at amendment time (correction events/wording excluded from the derive); Event/DCM resolved at READ on trade date. No repair queue, no mutation, no human. Back-ported to 66/11/12/09/90/95. |
| 9 | Concurrent producers | Two producers can coin near-synonym Drivers at the same time. | **✅ RESOLVED — owner-approved 2026-07-06 (66 §0.R OD-15):** exact duplicate Driver names already converge through `Driver.name` uniqueness + `MERGE`; near-synonym names are accepted over-splits handled by normal SAME_AS repair/fold. No new lock, queue, serialization layer, or special repair path. |
| 10 | Live missing-Driver creation | Track A stamps `fact_type` at catalog finalization, but live creation also needs a safe path. | Define how a live proposed Driver gets `fact_type`, validation, graph write, or parking. |
| 11 | Catalog to graph materialization | Track B assumes Driver nodes exist; Track A says Neo4j writes are not its goal. | Assign one owner step that writes finalized Drivers to the graph. |
| 12 | Fitness / honesty gate | The gate is required, but the exact quality budget is still unclear. | Pin scoring, threshold, sample, answer key protocol, and failure action. |
| 13 | Change-flag scanner | Several rules cite a scanner/change detector that is not yet specified. | Write the scanner contract or explicitly remove the dependency. |

---

## 4. P1 unowned or under-homed build pieces

These do not necessarily change the model, but a coding agent still needs a clear owner and implementation target.

| Piece | Needed close |
|---|---|
| Unit resolver wiring | `UNIT-14`: shared resolver is proven, but not wired into the producer. |
| Period resolver build | `PER-20`: extract/build `driver_period_resolver.py`, pass the 21 tests, prove YTD/TTM handling. |
| Concept linker | Decide whether `XC-16` calc-hierarchy veto is required before any rollout or only before full-universe rollout. |
| Concept backstop C / veto D | Backstop C and the 4-entry component veto D are locked in spec, but still need fresh implementation and tests. |
| Concept-link full run | Full-universe run is pending; prior validation covered only part of the universe. |
| Slice/member lists | Materialize the HARD-EXCLUDE and PROVISIONAL member lists as real data artifacts, with one owner vetting pass. |
| PIT concept-menu query | Build and test the point-in-time concept/member menu query used by fact producers. |
| News Driver admission path | Track A leaf build excludes news; part 2 must say how news-coined Drivers enter through live governed G1/G2 or park. |
| Prompt rewrites and mirror tests | Apply the Track A prompt/rule overrides and add tests so inlined naming/fact rules do not drift from the source docs. |
| `min_score` mismatch | Docs lock `0.60`; code still has `0.72`. Decide exact fix and owner. |
| `--measure-inherit` counter | Build or explicitly defer the counter mentioned by the concept-link plan. |

---

## 5. Open owner decisions to close or explicitly defer

These should not stay vague before a coding handoff.

| Decision | Current status |
|---|---|
| `FS-23` cross-company value comparison | Deferred; keep conservative unless explicitly built. |
| 8-K taxonomy | Open: whether the 24-tag taxonomy is reused. |
| Amendments | **Resolved by OD-14:** amended/corrected filings create new facts at amendment public time; current reads prefer the latest collapsed value; correction events/wording are excluded from read-derived guidance movement; exact retractions write numberless facts, otherwise do not guess. |
| Final model policy | Open: exact model, number of runs, and job-by-job policy. |
| G1 reuse-display rules | Open; blocks live catalog-first display details. |
| K2 fold-repair profile gate | **Resolved:** folds stay slow per-pair for safety; batched fold repair is deferred as a future optimization experiment/gate, not required for build readiness. |
| Target universe count | Open: 796 vs 786 tickers. |
| Lifecycle / dormancy / IPO absorption | Open; default lean is live G1/G2 absorbs, but not final. |
| Macro/news details | Open: significance threshold and pure-macro source representation. |
| Dormant XBRL-link write path | Deferred; activate only if the owner approves the XBRL-link rider. |
| Blanket withdrawal fan-out | **Resolved by OD-14:** kept written only because each withdrawn guide needs a gradable node; exact-scope-only, open guides only, resolved-period containment, add-only for late covered guides, never delete. |

---

## 6. Cross-doc cleanup before coding

These are mostly wording and authority-map fixes, but they matter because coding agents read files independently.

| Cleanup | Why |
|---|---|
| Back-port rejected alias-layer wording | Current docs still contain older alias-language in places; final design is member-anchored read-time grouping, not ID-changing alias merges. |
| Back-port `previous_guidance` metric ban | Some prose still suggests `previous_guidance` can live on metric facts; final rule sends expectation comparisons to surprise. |
| Align unit hint wording | `04_UNIT-04` still has older one-hint-pair wording; Track B uses per-slot hints. |
| Apply ISS-19 / ISS-20 fixes to Track A | They are proposed elsewhere but not fully reflected in `10_BuildPipeline.md`. |
| Finish overview | Add the 3-track map, authority/reading map, and status dashboard. |
| Add glossary | Define repeated terms with multiple meanings: `G1/G2`, `menu`, `slice`, `created`, `parked`, `fail-closed`, `source`, `archive`. |

---

## 7. Aspirational brief for Driver ingestion

This is not a locked design yet. It is the design challenge Fable must solve with full attention.

**North-star aspiration:** both `Driver` and `DriverUpdate` should be continuously and super quickly updated for all live ingestion. As soon as a new asset is ingested -- report, transcript, filing, news, or any future source -- the system should automatically start converting it into the right Drivers and DriverUpdates.

There should be **no human in the loop by construction**. No steady-state review process. The system should be robust enough to handle parked and fail-closed facts automatically and efficiently, with parked/failed cases minimized as much as possible, ideally near none.

The target is **100% recall, 100% precision, and the lowest practical cost**. Fable must treat misses and false writes as unacceptable design failures, then define how recall and precision are measured, how uncertain cases retry or escalate, what parks/fails closed, and how every unresolved gap becomes visible instead of silent.

Cost and model use must be designed deliberately. Fable should first understand every task that truly requires an LLM, then design the best combination of deterministic code, cheap models, strong models, multiple runs/iterations where needed, and an advisor strategy where a lower-intelligence model uses a higher-intelligence model only when needed. Fable should propose the small experiments needed to find the best combination.

Reuse existing machinery wherever possible. The old guidance extraction pipeline is only one example of the generic extraction process; Fable must inspect whether the existing daemon, worker, queues, sidecars, run ledger, source ingestion, and extraction framework can be reused safely for Drivers and DriverUpdates.

Historical backfill is required, but it may be staged intelligently if full backfill is too much at once. For example, the first pass may prioritize companies with upcoming earnings in the next day or two, then expand to higher-value companies and finally the full historical universe.

The execution path should use the Claude Code subscription / workflow path, not the API or metered SDK path, unless the owner explicitly approves a different path.

The design should use minimalistic machinery and aim for 100% reliability. Do not add complex machinery unless it clearly improves recall, precision, cost, speed, or reliability.

Most importantly, Fable must think hard about the best possible design for an actual living, intelligent Driver system. Even before prediction or learner loops, the Driver and DriverUpdate graph should become powerful by virtue of being so well designed, so well connected, fully automated, perfectly actionable, and useful for automatic trading. The graph should become intelligent through its structure: Drivers, DriverUpdates, sources, companies, events, periods, concepts, members, verdicts, and time should connect in the right way so the system keeps becoming more useful as new assets arrive.

Fable's output should not be a vague architecture. It should compare design choices, reject weaker options, and produce the simplest design that can satisfy the requirements above.

### Tentative living-ingestion component breakdown

This breakdown is tentative. Fable should use it as a starting map, not as a locked architecture. The final design may merge, split, rename, or reject components if that produces a simpler and more reliable system.

```text
new asset arrives
-> decide what work to run
-> extract Drivers + DriverUpdates
-> validate/write graph
-> enrich/link/verdict
-> measure quality/cost
-> retry, escalate, park, or fail closed without human review
```

| # | Component | What it owns |
|---|---|---|
| 1 | Asset trigger | Detects a new report, transcript, filing, news item, or future source immediately after ingestion and starts Driver work automatically. |
| 2 | Source normalizer | Converts every asset into one standard packet: company, source id, timestamp, source type, text, sections, metadata, and hashes. |
| 3 | Run ledger | One truth table for status: `pending`, `running`, `done`, `parked`, `failed`, per source + fact type + model + ruleset + hash. |
| 4 | Work router | Decides which tasks to run for that source: Driver discovery, DriverUpdate extraction, guidance, surprise, verdict, enrichment. |
| 5 | Driver resolver | Reuses an existing Driver when safe; creates/proposes a new Driver only through governed rules; parks if unsafe. |
| 6 | DriverUpdate producer | Reads the source and emits fact candidates: state, value, period, unit hints, slice, quote, conditions, comparison, and related fields. |
| 7 | Code validator/writer | Deterministic layer: builds ids, resolves units/periods, validates fields, writes good facts, parks/fails unsafe facts. |
| 8 | Verdict producer | Writes `EXPLAINED_BY`: whether this fact explained the stock move, plus direction, force, and confidence. |
| 9 | Enrichment layer | Adds XBRL concept links, member links, `BASE_METRIC` inheritance, source links, and read grouping. |
| 10 | Park/fail handler | Automatically retries, escalates, parks, or fail-closes unresolved cases. No human review queue. |
| 11 | Model/cost router | Chooses cheap model, strong model, multi-run, or advisor strategy based on task difficulty, risk, and cost. |
| 12 | QA and recall monitor | Measures misses, false writes, field accuracy, source coverage, parked rate, latency, and token/model cost. |
| 13 | Backfill scheduler | Runs historical work in stages: upcoming earnings first, then high-value companies, then full history. |
| 14 | Graph readiness layer | Ensures outputs are useful for trading: company, source, event, time, concept, member, period, Driver, DriverUpdate, and verdict links are connected correctly. |

Three large layers:

| Layer | Plain meaning |
|---|---|
| Orchestration | What runs, when it runs, in what order, and with what priority. |
| Production | How Drivers and DriverUpdates are extracted, validated, written, enriched, and linked. |
| Reliability | How the system reaches the 100% recall / 100% precision target, keeps cost low, avoids humans, and makes every failure measurable. |

Most important point: Fable should design the full living ingestion conveyor belt, not just prompts. Prompts are only one piece. The real system is the full loop:

```text
Asset -> Work Router -> Driver Resolver -> DriverUpdate Producer
-> Validator/Writer -> Enrichment -> Verdict -> QA/Cost Monitor
-> Retry/Escalate/Park/Fail Closed
```

**Recommended order before coding:**

1. Write the full living-ingestion design first: live trigger -> daemon/worker reuse -> run ledger -> Driver reuse/create -> DriverUpdate write -> verdict write -> retries/parks -> Claude subscription execution path.
2. Close all P0 identity/write rules immediately after: `quote_hash`, measurement tokens, unit-family map, sequential percent guidance, loss signs, lower-is-better metrics, chronological writes, concurrency, and catalog-to-graph materialization.
3. Define producer packets/prompts exactly: what every report/transcript/filing/news job receives, emits, validates, retries, parks, and writes. No human review path.
4. Design the model/cost experiment: break down every LLM task, test cheap model vs strong model vs advisor/escalation, aiming for 100% recall, 100% precision, and lowest practical cost.
5. Design live + historical backfill together: live is immediate; historical can be staged by upcoming earnings first, then high-value companies, then the full history.
6. Define QA gates and rollout blockers: how recall/precision are measured, how silent misses are found, what blocks production, and how parked/failed cases are minimized.
7. Patch owning docs and update presentation last: after the design is accepted, write rules into the owning docs (`10`, `12`, `14`, `90`, etc.); update `DriverPlan.html` only after the real design is settled.

---

## 8. What Fable or another design agent should do

Do not redo Track A, Track B, or Track C from scratch.

The right task is narrower:

1. Use the aspiration in §7 as the north star for the ingestion design.
2. Write the missing running-layer design in §2.
3. Pin the exact identity and write-order rules in §3.
4. Assign owners for the unowned build pieces in §4.
5. Force the owner decisions in §5 to either "decided" or "explicitly deferred."
6. Patch the cross-doc wording and glossary in §6.

The most important instruction: every identity-bearing field must have one exact recipe and worked examples. No "builder decides" rule can remain for IDs, graph keys, or write-order behavior.

---

## 9. Coding handoff checklist

Coding should start only when all of these are true:

- Every permanent ID component has an exact recipe and examples.
- Every producer packet has exact input, output, validator, and park/fail behavior.
- The run ledger schema is complete and is the only source of run status.
- The allowed model execution path and billing guard are specified.
- Fresh guidance production is specified from source documents, not old guidance rows.
- Historical backfill and live refresh use the same rules unless a difference is explicitly named.
- Graph materialization has a single owner path.
- Prediction and learner either have new guidance available or are proven to degrade safely when guidance is empty.
- QA gates say exactly what blocks rollout.
- Cross-doc contradictions are patched or listed as superseded.
