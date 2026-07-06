# 95 · Supersession ledger (history — old rule → new rule)

**What this is:** the single record of every decision that was **reversed**. The live plan (`01`–`13`, plus `90`) carries the *current* rule; this file preserves the *old* version + why it changed, so history is never lost. Rule blocks that flipped carry a `Replaces: 95_Supersession #N` pointer where practical.

**How to read:** **Was** = the dead rule (do NOT copy it). **Now** = the locked current rule (in the live plan). Rule #s are stable — never renumbered.

---

## A. Reversals from the origin design → the consolidated design

| # | Topic | Was (dead) | Now (locked) | New source |
|---|---|---|---|---|
| 1 | Brand/segment/geo in the name | `taco_bell_same_store_sales` = its own driver | name = **cause only**; brand/segment/geography/product/customer/channel → the **slice** | Naming_Slices §2 ("reverses") · NAME-10 |
| 2 | The version of a number | in the name → `adjusted_eps` | name = `eps`; adjusted/diluted/constant-cur → the **measurement** slot | Naming_Slices §5 ("intentionally reverses") · NAME-14 / FS-25 |
| 3 | Per-X price units | "$/barrel → unknown" / per-X "stays bare" | denominator **in the name** (`oil_price_per_barrel`), unit = `usd`; no "$/physical → unknown" guard | UnitExtraction Rules 2/3 · NAME-13 |
| 4 | What a driver-update is | "= a change (X→Y)" | = **any real event-level fact** (a CEO exit / FDA approval counts) | DriverGraphSchema §0 · DU-01 |
| 5 | When to create a driver | only if it appears in >2 events | **dropped** — a single event is valid; recurrence is read-time only | DriverGraphSchema §0 · DU-01 |
| 6 | The importance field's name | `magnitude` | `weightage` | DriverGraphSchema · DU-22 |
| 7 | Is importance a share? | a share summing to 100% | an **independent force** — never summed; a move may be partly unexplained | DriverGraphSchema · DU-22 |
| 8 | Where the verdict lives | on the driver-update node | on the **`EXPLAINED_BY` edge** (Event → fact), not the node | DriverGraphSchema §3 · DU-20/21 |
| 9 | Linking related drivers | "related-but-not-same must not be linked" | separate but **linked by `BASE_METRIC`** (revenue_guidance → revenue); never same-as | MetricGuidanceFamily · MF-02/03 |
| 10 | Time periods | period existed for guidance only | one generic **DriverPeriod** for all 4 fact-types; node renamed Period → DriverPeriod | GuidancePeriod · PER-02 |
| 11 | Kinds of "slice" | 4 types; `store_type` its own type | **6 kinds + unknown**; `store_type` folded into **channel** | Consolidation README · FS-06 |
| 12 | What identifies a slice | the official XBRL member-id | the plain **segment text** (member-id was unsafe) *(re-confirm at slices)* | memory · FS-08 / FS-02 |
| 13 | Linking a driver to XBRL | a hand-curated dictionary | LLM **picks from the company's own reported menu** + guards; no dictionary | XBRLConceptLinking §2 · XC-02 |
| 14 | RavenPack's 7,400 categories | import as the name vocabulary | **checklist only** (borrowed just `rumored` + `failed` states) | INDEX §3e · DU-11 |
| 15 | The document-reader model | Fable | **Opus** reads + **Sonnet** classifies (a mixture) — *current leading default; supersedes the Fable/2-pass plan. Full model policy (exact model · # runs · job-by-job) still needs a larger audit → `90_OpenItems`* | INDEX · Consolidation README 5d |

## B. Field-spec amendments (2026-07-02, from `09_DriverUpdate_Fields.md`)

Items #16-25 are applied reversals/amendments carried here for history; nothing in this ledger is a pending owner item.

| # | Topic | Was | Now | Source |
|---|---|---|---|---|
| 16 | Number shape encoding | `level_bound` field (point = low-only) | `level_bound` **cut** → self-describing shapes (point = **both bands**, floor = low-only, ceiling = high-only) + a transient `level_shape_hint`/`comparison_shape_hint` (checked, **never stored**) | 09 §3 · amends DU-13/14/16 |
| 17 | Number-less guidance value | no free-text field (DU-18: "the quote carries it") | the field **returns as `value_text`** (guidance-only, numberless-only, value-aware lint) — the running system renders `value_text`, never the `quote` | 09 §8.1 · amends DU-18 |
| 18 | Fact `evhash16` | stored on the DriverUpdate node | **retired on the fact** (derivable, reader-free; no-op detection = direct field compare). **Kept** on the `EXPLAINED_BY` verdict edge | 09 §5/§8 · amends DU-19 |
| 19 | `company_confirmed` type | enum `{confirmed, unconfirmed}` | **boolean `true`/`false`** | 09 §3 · amends MF-11 |
| 20 | Concept-linker non-GAAP guard (G2) | name-prefix regex (`adjusted_`/`non_gaap_`/…) | key on the **`measurement` set** (primary); name-prefix regex kept as the **legacy-name fallback** (since "adjusted" left the name — see #2) | 09 §8 · amends XC-05 |

*(Also corrected by 09: `DriverGraphSchema:331`'s computed "+0.10" surprise example → `change_value=null` (a beat size derives at read from level − comparison). This is an application of DU-16 rule 6, not a new reversal.)*

## C. Pipeline reversals (2026-07-02, from `10_BuildPipeline.md`)

| # | Topic | Was (dead) | Now (locked) | New source |
|---|---|---|---|---|
| 21 | The live reuse flow (G1) | show the catalog FIRST (`catalog_first.js` catalog-first flow) | **propose-first**: the producer coins its own name + quote blind → only then sees related existing drivers (PIT-filtered `visible_from ≤ event date`, ranked by semantic match on name+quote+scope; usage counts tie-break only, never decide); G2 (+Refute for fusions) stays the admission authority | HCP §13.1.1–4 (owner-approved 2026-06-10) · 10 PIPE-22 |
| 22 | Concept-linker invocation | `claude_agent_sdk` + OAuth (XC-11's mechanism) | **in-session workflow agents under subscription** — batch AND the default live path; the SDK is NOT approved without separate owner sign-off (June-15 metered-pool change) | owner 2026-07-03 · 12 FACT-32/§10.2 · XC-11 amended |
| 23 | Driver-item period fallthrough | PER-11's ladder ends in a quiet `gp_UNDEF` fallthrough | **HARD-FAIL for DriverUpdate items** (fields unresolvable + no explicit `sentinel_class` = producer bug); `action_event` sentinel outcomes hard-fail; the fallthrough survives only in the pure shared builder (Guidance parity) | owner 2026-07-03 · 12 §10.7 · PER-11 note |
| 24 | `previous_guidance` on the metric lane | metric `comparison_baseline` allowed `previous_guidance` (09 §4 / §6.4 matrix); only `consensus` was metric-FORBID | **BOTH expectation baselines FORBID on metric** — metric baseline is temporal-only ({prior_year, sequential_period, null}); an actual-vs-guidance/consensus comparison routes to the `_surprise` fact (which stores the expectation baseline) — no duplicate guide-store, true symmetry (ISS-16/OBJ-2) | owner 2026-07-03 · 12 §10.5 · amends 09 §4 · 07 DU-15 |
| 25 | Whole-company slice serialization | explicit company-wide/total facts stored `slice=total`; silence/no stated part omitted slice | **Whole-company / consolidated / total-company / no stated segment = omitted slice**. For metric/guidance/surprise, omitted means consolidated whole company, not missing/unknown; for action_event, omitted means no slice applies or no narrower business part is stated. Real narrower parts still serialize as slices. | owner 2026-07-04 · 13 §7 · amends FS-10/FS-15 |
| 31 | Surprise beat/miss arithmetic for lower-is-better metrics | ISS-16 derived surprise state by `>high→beat`, `<low→missed`, and hard-failed directional word/number conflicts; DU-16.2 also required positive `change_value` for `beat` and negative for `missed` | **Code computes only polarity-free position** (above/inside/below/at_floor/at_ceiling) and sets `in_line` only when wordless-inside-closed-range/boundary. `beat`/`missed` are producer meaning judgments from the full phrase, negation/polarity/scope-aware; wordless outside-range needs a transient discarded polarity proof, allowed only when the chosen favorable direction has no common mainstream counter-story, else `unknown`. Remove `beat`/`missed` from the sign hard-fail; surprise `change_value` stays stated-only and null when sign is ambiguous. | owner 2026-07-06 · 66 §0.R OD-13 · amends 12 §10.5 · 07 DU-10/DU-16.2 |
| 32 | Negative/loss value convention | Loss values could be stored as positive magnitudes in "loss space" (e.g. "loss of up to $2B" as a ceiling), forking identity from signed storage | **SIGNED value-space on the driver's own numeric axis**: convert the stated phrase to its signed value first, then apply the normal shape grammar. `level_low`/`level_high` are algebraic min/max; "loss of up to $2B" → value ≥ -2000 → floor, while "revenue up to $5B" remains ceiling. A net quantity's loss is negative; a charge/provision amount is positive, but a benefit/release/reversal is negative. No loss-magnitude duplicate drivers (`net_loss`, `loss_margin`, `loss_per_share`); use the standard signed driver (`net_income`, `operating_margin`, `eps`). No new field/list/human. | owner 2026-07-06 · 66 §0.R OD-12 · amends 09 §3 · 07 DU-14 · 02 NAME-08 |
| 33 | Percent-only guidance unit basis | `09 §7` hard-stamped every %-only guide as `percent_yoy`; UNIT-12 leaned against adding `percent_qoq`, leaving sequential guides to be mislabeled or mixed into the wrong series | **Read the growth basis from the source and add `percent_sequential`** to the enum: "% growth vs the immediately prior comparable period," period-agnostic and its own series family. `percent_yoy` remains same-period-prior-year growth. Metric-type gate first; static-% level bare "up X%" → `unknown` unless points/bps/"to X%" is stated; growth basis routes to `percent_sequential`, `percent_yoy`, or `unknown` by comparison-period framing. Measurement adjustments stay in `measurement` and never decide the basis. No `percent_qoq`. No new field/list/human. | owner 2026-07-06 · 66 §0.R OD-11 · amends 09 §7 · 04 UNIT-01/12 · 07 DU-17 · 11 T8/T11 · 12 constants |
| 34 | Chronological guidance movement, amendments, withdrawal fan-out, and Event/DCM late overlap | Guidance movement was stored from the write-time prior view; late old-dated filings could stale later states; Event/DCM single-target was enforced only at creation; amendment handling and blanket-withdrawal fan-out were still open/parked | **Store stated facts, read-derive timeline meanings, and write fan-out only where grading needs real nodes.** Bare guidance stores `driver_state=unknown`; read derives `effective_driver_state` from the prior collapsed value in the canonical guidance series; midpoint validator checks only source-stated movement and skips `unknown`; correction source/event metadata or explicit correction wording excludes correction facts from derive. Withdrawal fan-out stays written but exact-scope-only, open-guide-only, and add-only for late covered guides. Amendments are new facts at amendment public time. Event/DCM is resolved at read/grading: filing wins, DCM ignored not deleted, no stored flag. | owner 2026-07-06 · 66 §0.R OD-14 · amends 09 state/§6.9 · 11 T11.6/T11.7 · 12 FACT-16/§10.9 |
| 35 | Measurement tokenization and producer input | FS-25 allowed stacked labels to be split differently (e.g. `adjusted,diluted` vs `adjusted_diluted`) and 12 FACT-17b let the producer emit final measurement tokens, so two builders could fork identities or drop a qualifier | **Measurement is an open-vocab, source-grounded, never-drop sink.** Producer emits transient `measurement_raw_spans` only; code alone normalizes into `fact_scope.measurement` (lowercase → non-alphanumeric runs become `_` → trim → collapse). Maximal contiguous qualifier spans become one token; separate tokens only for non-contiguous source spans. A qualifier leaves measurement only if another slot captures its exact meaning losslessly; otherwise keep it. No write-time synonym merge, alias, closed list, or human. | owner 2026-07-06 · 66 §0.R OD-9 · amends 03 FS-25 · 09 §3 · 11 T3.5 · 12 FACT-17b |
| 36 | Unit-family map / read-time unit grouping | Read-time unit-family map plus unknown absorption (`level_unit`, else change-unit family; `unknown` absorbed) would force readers to guess without the quote and could fork grouping between builders | Add code-written **`series_unit`** on DriverUpdate facts. The writer stamps the series axis while the quote is available; reads group by plain equality on `series_unit` with no family map and no unknown absorption. Level facts use the level's canonical axis, money canonicalized to the driver's one scale within a currency. Delta-only facts fold only when the fact's own evidence makes one axis uniquely clear; otherwise they fail closed to exact `change_unit` or `unknown`. `series_unit` is a grouping tag only: stated values/units stay source-faithful. | owner 2026-07-06 · 66 §0.R OD-10 · amends 09 §6.1 · 11 T12.1/T12.6 · 12 FACT-33 |

*(Considered and left OUT as a row: "names-only catalog → born-complete class with mandatory fact_type" — an ADDITION, not a reversal of a stated locked rule; already recorded in DU-02/DU-07 and HCP's own header. Logged here so the decision trail isn't lost.)*

---

## Stale-trap docs — still show OLD rules; never copy from them on these topics
- `plans/Drivers/Drivers.md` — pre-reversal naming/DriverUpdate wording
- `plans/Drivers/DriverOntology.md` — R9 (brand/basis in name), the illegal `cut` state example
- `plans/Drivers/INDEX.md` §3b — measurement "kept in the name" (reversal #2)
- `plans/Drivers/WIP/unit_probe/RESULTS.md` — the `$/barrel → unknown` headline (reversal #3)
- `plans/Drivers/WIP/DriverGraphSchema.md:333` (basis "in the name / R9", reversal #2) + `:331` ("+0.10" example)

*(All of `plans/Drivers/archive/` is fully superseded v1 history — kept for the record, never a live source.)*
