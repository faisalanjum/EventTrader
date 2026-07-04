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
| 3 | Measurement tokenization | "cash EPS" could become `cash_eps`, `casheps`, or another token. | Pin multi-word token normalization with examples. |
| 4 | Unit-family grouping | Read-time series grouping can differ by implementer. | Pin the full unit-family map for the 9-unit enum, including the `percent_qoq` decision. |
| 5 | Sequential percent guides | `09 §7` currently hard-stamps percent-only guidance as `percent_yoy`, which can be wrong for QoQ-guiding companies. | Pin whether sequential percent guides use a new unit, existing `percent`, `unknown`, or another fail-closed rule. |
| 6 | Negative / loss values | "Loss of up to $2B" can be represented as a ceiling in loss-space or a floor in signed-space. | Pin sign convention, storage convention, rendering convention, and examples. |
| 7 | Lower-is-better metrics | Cost, capex, tax rate, churn, and similar metrics can invert beat/miss logic. | Define direction-aware surprise arithmetic and conflict rules. |
| 8 | Chronological writes | Late old-dated filings can corrupt guidance state, withdrawal logic, and the Event-vs-DCM single-target rule. | Define event-time order, write-time order, repair trigger, and validation rule. |
| 9 | Concurrent producers | Two producers can coin near-synonym Drivers at the same time. | Define locking/serialization point for Driver creation and fact writes. |
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
| `UNIT-12` / `percent_qoq` | Lean no, but must be closed or explicitly deferred. |
| 8-K taxonomy | Open: whether the 24-tag taxonomy is reused. |
| Amendments | Open: how amended filings affect old facts and states. |
| Final model policy | Open: exact model, number of runs, and job-by-job policy. |
| G1 reuse-display rules | Open; blocks live catalog-first display details. |
| K2 fold-repair profile gate | Open. |
| Target universe count | Open: 796 vs 786 tickers. |
| Lifecycle / dormancy / IPO absorption | Open; default lean is live G1/G2 absorbs, but not final. |
| Macro/news details | Open: significance threshold and pure-macro source representation. |
| Dormant XBRL-link write path | Deferred; activate only if the owner approves the XBRL-link rider. |
| Blanket withdrawal fan-out | Parked; needs explicit final rule if included in production. |

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

## 7. What Fable or another design agent should do

Do not redo Track A, Track B, or Track C from scratch.

The right task is narrower:

1. Write the missing running-layer design in §2.
2. Pin the exact identity and write-order rules in §3.
3. Assign owners for the unowned build pieces in §4.
4. Force the owner decisions in §5 to either "decided" or "explicitly deferred."
5. Patch the cross-doc wording and glossary in §6.

The most important instruction: every identity-bearing field must have one exact recipe and worked examples. No "builder decides" rule can remain for IDs, graph keys, or write-order behavior.

---

## 8. Coding handoff checklist

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
