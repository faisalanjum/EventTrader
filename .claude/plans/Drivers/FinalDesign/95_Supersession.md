# 95 · Supersession ledger (history — old rule → new rule)

**What this is:** the single record of every decision that was **reversed**. The live plan (`01`–`09`) carries only the *current* rule; this file preserves the *old* version + why it changed, so history is never lost. Rule blocks that flipped carry a `Replaces: 95_Supersession #N` pointer that resolves here.

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

## B. Field-spec amendments (2026-07-02, from `09_DriverUpdate_Fields.md` — pending owner §8 ack)

| # | Topic | Was | Now | Source |
|---|---|---|---|---|
| 16 | Number shape encoding | `level_bound` field (point = low-only) | `level_bound` **cut** → self-describing shapes (point = **both bands**, floor = low-only, ceiling = high-only) + a transient `level_shape_hint`/`comparison_shape_hint` (checked, **never stored**) | 09 §3 · amends DU-13/14/16 |
| 17 | Number-less guidance value | no free-text field (DU-18: "the quote carries it") | the field **returns as `value_text`** (guidance-only, numberless-only, value-aware lint) — the running system renders `value_text`, never the `quote` | 09 §8.1 · amends DU-18 |
| 18 | Fact `evhash16` | stored on the DriverUpdate node | **retired on the fact** (derivable, reader-free; no-op detection = direct field compare). **Kept** on the `EXPLAINED_BY` verdict edge | 09 §5/§8 · amends DU-19 |
| 19 | `company_confirmed` type | enum `{confirmed, unconfirmed}` | **boolean `true`/`false`** | 09 §3 · amends MF-11 |
| 20 | Concept-linker non-GAAP guard (G2) | name-prefix regex (`adjusted_`/`non_gaap_`/…) | key on the **`measurement` set** (primary); name-prefix regex kept as the **legacy-name fallback** (since "adjusted" left the name — see #2) | 09 §8 · amends XC-05 |

*(Also corrected by 09: `DriverGraphSchema:331`'s computed "+0.10" surprise example → `change_value=null` (a beat size derives at read from level − comparison). This is an application of DU-16 rule 6, not a new reversal.)*

---

## Stale-trap docs — still show OLD rules; never copy from them on these topics
- `plans/Drivers/Drivers.md` — pre-reversal naming/DriverUpdate wording
- `plans/Drivers/DriverOntology.md` — R9 (brand/basis in name), the illegal `cut` state example
- `plans/Drivers/INDEX.md` §3b — measurement "kept in the name" (reversal #2)
- `plans/Drivers/WIP/unit_probe/RESULTS.md` — the `$/barrel → unknown` headline (reversal #3)
- `plans/Drivers/WIP/DriverGraphSchema.md:333` (basis "in the name / R9", reversal #2) + `:331` ("+0.10" example)

*(All of `plans/Drivers/archive/` is fully superseded v1 history — kept for the record, never a live source.)*
