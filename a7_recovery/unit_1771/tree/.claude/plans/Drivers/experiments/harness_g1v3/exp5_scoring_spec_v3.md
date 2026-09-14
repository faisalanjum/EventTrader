# EXP-5 scoring specification v3 (COMPLETE — FOR REVIEW; spec only, no impl)

> Supersedes the v2 spec + the DESIGN_v3 diff for this file. Carries forward the
> rounds 13-16 mechanics (union semantics · home-fact law · ambiguity grader
> channel · per-rule error table · dedup) UNCHANGED except where named. Adds the
> reviewer's v3 refinements: order-free matching · the real run_event dry-run
> path (no exam-only shim) · exact would_park math · qualified graders ·
> raw-decimal preservation · "eligible for admission" wording.

## 1. Order-independent one-to-one matching (replaces greedy file-order)

Candidate criterion unchanged (quote ≥20-char overlap OR canonical value
equality). Resolution is a fixpoint, order-free by construction:
1. Build the full bipartite candidate graph gold ↔ produced per event.
2. Repeat until no change, each round computed SIMULTANEOUSLY from the current
   graph: (a) golds with exactly ONE live candidate; (b) a produced fact claimed
   by exactly ONE such gold → COMMIT the pair, remove both; (c) a produced fact
   claimed by >1 such golds → that connected group is AMBIGUOUS, removed.
3. Anything still multi-candidate at fixpoint → AMBIGUOUS (grader channel;
   unresolved ties still block PASS).
4. A committed pair consumes its produced fact GLOBALLY (one-to-one everywhere,
   presence_disagreement included).
Tests: permutation-invariance PROPERTY (score identical under random shuffles of
gold AND produced order — the reproduced defect becomes the RED regression) +
the forced-choice propagation case (2 pairs, 0 ambiguous, both orders) + the
>1-claimants case → grader queue in both orders.

## 2. Abstention semantics + exact would_park math (owner Q1 ruling, 2026-07-24)

Three model behaviours, kept distinct:
- **Known non-fact** → the model OMITS it (no record, no abstention). Correct
  silence, no penalty.
- **Unresolvable real candidate** → an `abstentions[]` row (verbatim quote +
  reason).
- **Silent miss** → detected only by the gold key; affects RECALL only.

An abstention is **gold-linked** when it is a one-to-one tie to an OTHERWISE-
UNMATCHED gold fact (its quote covers a du_worthy gold fact that no produced
fact matched). The abstention's quote is located by its `occurrence` field — a GLOBAL 1-based count — scan the event's `text_parts` in canonical order and count each verbatim match left-to-right within a part, continuing the SAME count across parts (never reset at a part boundary); a match never spans two parts — required only when the quote repeats (audit-only, outside the 37 PreparedFact fields). Only gold-linked abstentions are parks:

```
recall     = unambiguously-matched du_worthy gold / total du_worthy gold
             (a gold-linked abstention or a silent miss is a NON-match → both
              lower recall identically; an abstention never rescues recall)

would_park = (parked/rejected emitted facts + gold-linked abstentions)
             ---------------------------------------------------------
             (all emitted facts            + gold-linked abstentions)
```
Non-fact abstentions are DIAGNOSTIC only (never in would_park, never a recall
penalty). Each emitted fact parks at most once. **Emitted facts are DEDUPLICATED
(full canonical fact key, the same key dedup_items uses) BEFORE the park rate is
computed**, so a repeated fact never inflates the denominator or double-parks.

## 3. The real production validation path — no exam-only shim (reviewer point 5)

Accepted/parked classification runs the ONE production entry point the S4
rehearsal already certified: **`run_event(run_input, store, audit_dir,
enable_writes=False)`** (driver_write_cli.py:275). In dry-run it performs the
SAME reads and runs `validate_fact` (driver_write_cli.py:456) + the period/unit
resolvers, and returns the write-ahead audit with park codes WITHOUT opening
`store.transaction()` (that opens only under enable_writes + ENABLE_DRIVER_WRITES,
:607). The scorer builds a `RunInputV1` from the produced facts via
`PreparedFactV1.from_dict` and calls run_event dry-run; the produced-fact
classification IS the real audit. **`fact16_checks.py` (the second rule engine,
own `_NUMY` regex + duplicated enums) is TO BE RETIRED (planned, not yet done —
the scorer still imports `check_item`, score_exp5.py:50).** No exam-only
validation logic is kept; if any per-event check genuinely lives outside
run_event it is extracted as ONE shared helper used by both paths.

**Store validation path (reviewer point 4 — CORRECTED; my prior admissions-
create proposal was WRONG).** An EMPTY store parks every fact `DRIVER_NOT_READY`
when the typed driver is absent (driver_write_cli.py:369). My round-22 fix —
run_event in ADMISSIONS mode — FAILS the four-lane probe: admissions is
METRIC-ONLY (driver_write_cli.py:144 raises on any non-metric fact_type, the
v2.5 rehearsal fence), so guidance/surprise/action_event all reject. Retracted.

The correct path (ChatGPT's, verified): build a **temporary read-only store
AFTER the model output**, populated from the produced facts' OWN
`(driver_name, fact_type)` pairs — never from gold. `store.get_driver(name)`
returns the typed driver `{name, fact_type}` the MODEL produced; run_event runs
in **None-mode** (admissions=None), so at :367-371 the driver exists+typed →
validation proceeds for ALL FOUR lanes (`_tail` → fusion → `validate_fact`).
`validate_fact` reads only `driver["fact_type"]` and `driver["name"]`
(driver_validators.py:156-163), so `{name, fact_type}` suffices. This leaks
nothing (the names come from the model, not the key) and generalizes to any
unseen name. **Guard: if the model emits the SAME driver_name with CONFLICTING
fact_types across facts, reject that name** (one name cannot be two types). The
store is also seeded with the per-event SOURCE + its single COMPANY (needed for
the :340 company check + period resolution; both knowable per event, no leak).
Store-backed create-vs-attach ADMISSION/REUSE stays out of scope (§8).
Integration checkpoint at implementation: run_event completes cleanly for one
fact of each lane against this temp store.

## 4. The gates (owner O-4 + reviewer point 7)

- **Safety gate (absolute, per run): zero confirmed-wrong ACCEPTED facts.**
  Accepted = a produced fact that survives run_event dry-run (would be ELIGIBLE
  for the later admission decision — NOT "written"; EXP-5 does not test
  create-vs-attach). Confirmed-wrong = adjudication CONFIRMS any production field
  wrong (values · period · slice · state · units · basis · polarity ·
  name-meaning), OR an unsupported extra (§5). One → EXAM FAIL.
- **Capability bars (all still GATES, AND-ed with the safety gate) — the LOCKED
  set + LOCKED formulas (workorder:643):** recall ≥95 single / ≥98 union ·
  wrong-lane 0 · **`value_shape_acc` ≥98 computed EXACTLY as the current
  certified scorer does — the POOLED ratio `code_ok / code_all` over the
  code-comparable fields (score_exp5.py:423), NOT a per-field MIN** · state ≥95 ·
  would_park ≤10 (per §2). I do not alter the locked formula.
- **PROPOSED refinement (owner-only, NOT applied):** the pooled formula lets a
  low-rate wrong-hint dilute (the round-17/18 dilution class). A fix — recompute
  `value_shape_acc` as the MIN over the value/shape/unit-hint field group so a
  single weak field can't hide — is a REAL improvement but changes a LOCKED
  formula → owner ratification required. Until then it is REPORT-ONLY alongside
  the locked pooled number; the gate uses the locked formula.
- **Union never hides an unsafe run:** a union-recall rescue applies ONLY to the
  recall leg; it NEVER bypasses the per-run safety gate or the other capability
  bars (the union must be clean on its own axes). A single unsafe run fails
  regardless of union recall.
- Mismatch ≠ confirmed-wrong until adjudicated: mismatches route to the
  qualified graders (§7); verdicts {model_wrong → safety gate · key_erratum → §5
  · tie_unscorable → ambiguity channel}.

## 5. Extras classification + INCONCLUSIVE law

Every unmatched ACCEPTED produced fact → exactly one bucket: (1) **duplicate**
of a matched fact → dedup, no penalty; (2) **genuine key miss** (a real fact the
key lacks) → the run is INCONCLUSIVE for the affected bar(s); the key is
VERSIONED (erratum recorded, scores never retro-edited) and the retest uses
FRESH unseen cases; (3) **unsupported** → confirmed-wrong accepted fact → safety
gate FAIL.

## 6. Decimal-safe transport — TO BE PROVEN (open implementation item)

Honest status: this is NOT proven today. The current launcher returns
SCHEMA-PARSED objects — the workflow `agent(..., schema=…)` path parses the
model's JSON (default float parsing) before I ever see raw text, so a
high-precision decimal is ALREADY lossy at that boundary. Saving "raw bytes"
after a parse proves nothing.

The required change (implementation, after approval): capture the model's reply
as RAW TEXT at the agent boundary (the string, never a pre-parsed object), write
that exact text to disk, and ONLY THEN parse with `parse_float=Decimal`.
Named RED regression to WRITE at that point: a reply containing
`1.000000000000000000001` and a `2^60`-vs-`2^60+1` pair round-trips through the
real transport → the on-disk raw string is byte-identical to the model's emit
AND the parsed value is the EXACT Decimal (not a float). Until that test is
green, Decimal-safety is a REQUIREMENT, not a fact. All downstream comparisons
already run dec_canon exact decimals with no float `repr` bridge; the open gap
is purely the transport capture.

## 7. Graders (reviewer point 9)

Ambiguity resolutions, extras verdicts, and the meaning-field verdicts
(driver_state · lane_routing · favorability_od13 · basis_od11 · slice_vs_menu)
require the EXP-0-QUALIFIED grader tier ONLY — two independent instances
(claude-sonnet-5 @ effort=high; FableExperimentWorkOrder.md:164). Grader input =
RAW evidence only (quotes/names/values), never detector conclusions or the other
grader's output. PASS stays None (INCOMPLETE) until every required verdict is in.

## 8. Scope boundary — EXP-5 is strictly text-lane (reviewer point 4)

The exam measures the TEXT decomposer: the model owns `fact_type` + the 37
text-lane fields. **Structured XBRL BYPASSES this model exam entirely** — for an
XBRL-backed fact, CODE owns the context (`xbrl_concept_raw`), the periods (the
all-or-nothing bundle dates, prepared_fact.py:143-157) and the slices/dimensions
(`member_refs`). None of those are scored here or shown through the menu; they
enter downstream via the source-linked path, not the reader.

## 9. Reporting

Per-field accuracies (populated pairs) · state accuracy · parks by actual code ·
the per-rule error table (actual-code buckets, case-correct) · extras buckets ·
abstention ledger (gold-linked vs diagnostic) · ambiguity queue + resolutions ·
safety-gate verdict with adjudication citations. PASS is three-valued (None
until grading + adjudication complete; definite failures short-circuit to False).
