# Minimalism Audit — Driver CREATION Layer

> Adversarial minimalism lens. Verified against current bytes of P1 (CombinedPlan.md), P2
> (DriverOntology_Implementation.md), P4 (DriverImprovements.md), P5 (Prompt), R1/R2/R3 reqs,
> and G1 guidance_ids.py. Every finding cites file:line + on-disk quote. Cross-checked against
> req_canonical.md so no removal drops a requirement.

## Frame

The user's condition 3 = "minimum incremental work — maximum reuse of guidance pipeline; smallest
new code surface." The plan's own honest LOC tally is **~2,500 LOC + ~50 Cypher + ~135 doc**
(P1:595), up from a ~2,080 baseline by the three Levers (~250-350 impl + ~200-300 test, P1:596).

The CREATION layer proper (what req_canonical.md binds: A20 reuse-first, B-R1..R11, B-N1..N6,
B-F1..F10, B-M1 determinism, K1..K60 risk closure) needs: canonicalize() + classify_token() +
order_by_slot() + §F vocab banks + V1..V14 + new-token gate + banned/state/shortcut gates + the
LLM emission contract + the cold-start seed list + the registry/vocab READ path. That is the
genuine new surface and it is NOT over-built — it is the irreducible mechanism for B-M1
determinism. The minimalism problems are concentrated in **Tier-6 (the 3 Levers E26/E27/E28 +
audit tables E29)** and a handful of PIT/backdate refinements folded on top of them.

The headline: roughly **half the net-new code surface (the ~420 LOC + ~200 test LOC of Tier-6,
P1:596) is ingestion machinery or premature accuracy-chasing that the creation layer does not
need to ship, and that traces to NO requirement in R1/R2/R3.** Removing it does not drop a single
A/B/K obligation, and it directly serves condition 3.

---

## FINDINGS

### MIN-1 (major) — Lever #2 (E27) is ~70% ingestion machinery folded INTO the creation plan
The scope_split itself classifies E27's storage/promotion/Cypher/audit as INGESTION (scope_split.md
§2: "the `:EquivalenceToken` Neo4j store, N=2 promotion, two-phase Cypher (v5-4/v6-2), intra-MERGE
to_token guard (v9-2), `equivalence_visible_at` MIN-backdate (v10-2), candidate-hiding, collision
audits" are ingestion). On disk, the E27 entry (P1:368-391, ~24 dense lines) and §F.10 Pattern A2
(P2:455-464) are dominated by: two-phase Cypher (P2:459-463), `equivalence_id` UNIQUE collision
rule (P2:457), v9-2 intra-MERGE race guard (P2:461), v10-2 backdate CASE (DriverImprovements
P4:526-542), two distinct audit labels. **Only the synonym/plural/acronym MAPS that feed
canonicalize step 5 are creation-relevant** (P2:140 `n = vocab.synonym_map.get(n,n)`). Per the
user's scope rule ("for INGESTION items do NOT judge on own merits — check only clean handoff"),
all of this Cypher/promotion/audit belongs to guidance-writer reuse, NOT the creation plan's new
surface. The creation layer needs exactly one thing from Lever #2: a frozen map merged into the
VocabSnapshot. Folding the whole promotion engine into the plan inflates the CREATION review
surface and the LOC tally. **Minimal alternative:** keep the §F.2/F.3/F.4 markdown maps as the
creation seed (already present, P2:322-373); delegate the entire `:EquivalenceToken` store +
N=2 + two-phase Cypher to the ingestion/writer layer the user is reusing, judged only by H1/H6.
Does not drop a requirement: no A/B/K item demands a *runtime* equivalence store — B-N6/K33/K34/K35
require synonym/plural/acronym *folding*, which the static maps already deliver. **Removed from
creation surface:** the write_equivalence_tokens() body + two-phase Cypher (~part of the +80
driver_writer LOC, P1:567) + 2 of 5 audit labels.

### MIN-2 (major) — N=2 runtime promotion gate (E27) traces to NO requirement and is premature for a Phase-1, single-producer system
P1:370 "Promotion to `status="promoted"` requires `size(observation_keys) >= EQUIV_PROMOTE_N`
where N=2." The whole point of N=2 is to require *two independent producers/events* to agree
before trusting a synonym. But P1:381 admits it is a no-op in Phase 1: "Predictor+learner emitting
same equivalence on same event = ONE observation. Defensive for Phase 2/3 multi-producer;
**effective no-op in Phase 1 (learner-only per E30)**." And DriverImprovements concedes the
deferred Phase-2 backfill machinery (v9 deferred, P4:43) plus the X3 reversal churn (P4:26-28)
exist only to protect Phase-2/3 scenarios. No R1/R2/R3 requirement asks for runtime synonym
learning at all — B-N6 (R2:22) defines synonym/plural/acronym *maps*, not a promotion protocol;
A20 (R1:76) asks for reuse-before-create against a registry, which the static maps + B3/B4/B6/B7
lookups (P2:41-69) already satisfy. **Minimal alternative:** defer the entire N=2 promotion lifecycle
(candidate/promoted status, observation_keys[], observation_pit_cutoffs[], the collision rechecks,
v9-2/v10-2/v10-3) to Phase 2 when a second producer actually exists. In Phase 1 a new
synonym is just a code-time map entry (the file is explicitly append-only and code-editable per
P2:294 "orchestrator appends entries through valid propose_new_drivers[] emissions" + §I rev-trigger
"Add entry to SYNONYM_MAP … ❌ No [ontology rev]"). Does not drop a requirement (verified against
K32-K35: all are *folding* obligations met by the static maps). **Removed:** the entire promotion
state machine + its tests (~part of P1:592 "+200 test LOC over baseline").

### MIN-3 (major) — Triple PIT-visibility backdate machinery (v9-1/v10-1 VocabToken + v4-7/v10-2 EquivalenceToken) is pure ingestion, folded into creation, and self-described as protecting only out-of-order Phase-2+ backfills
P1:428 "v9-1 + v10-1 VocabToken vocab_visible_at + MIN-on-MATCH backdate"; P1:432 "v10-2
equivalence_visible_at MIN-backdate on each obs"; DriverImprovements P4:13-14 (v10-1/v10-2). The
scope_split tags `:VocabToken.vocab_visible_at` and `:EquivalenceToken.equivalence_visible_at` as
"INGESTION (written), CREATION (read)" (scope_split.md §5). The MIN-on-MATCH backdate CASE
expressions (P2:451 ON MATCH; P4:535-542 the Cypher CASE) are write-time computations — squarely
ingestion. The plan's own honesty: the prior deferral (X3) said these protect "Phase 1 chronological
backfills" and DriverImprovements admits that premise was about out-of-order backfills (P4:28
"E30 doesn't lock backfill order; operators can run reverse-chrono backfills"). For a Phase-1
learner-only producer this is defending against a scenario the user has not asked to support. Per
the scope rule, the *read* (load_vocab_snapshot PIT filter, P2:199-206) is the only creation-side
piece; the *visible_at field computation + MIN-backdate* is ingestion. **Minimal alternative:**
the creation layer reads `vocab_visible_at <= pit_cutoff` (keep, it is a read filter); the writer
owns how the field is set. The MIN-on-MATCH backdate is a writer correctness concern delegated to
guidance-style-writer reuse, not new creation code. Does not drop a requirement — no A/B/K item
mentions PIT backdate (PIT visibility is an ingestion concern per req_canonical.md C.2 + §D handoff).
**Removed from creation surface:** the two MIN-backdate CASE blocks + v10-3 concurrency invariant
+ v9-2 race guard (all ingestion).

### MIN-4 (major) — E29 audit telemetry (5 Neo4j labels) is in-scope-creation by file location but the plan itself certifies it removable
E29 lives partly in `DriverOntology_Implementation.md` §K (P2:694-729) — a creation-layer file —
and the §10 LOC tally folds its constraints into the creation build (P1:575-579). But the plan
states outright it is optional: P2:696 "**Self-heal does NOT require any seed edits** … Without
these tables the system still self-heals; we just lose observability," echoed P1:420 "Without these
tables, the system still self-heals correctly; we just lose observability." Five labels
(`:DriverAutoRepair`, `:DriverProposalRejection`, `:EquivalenceConflictAudit`,
`:EquivalenceCollisionAudit`, `:DriverDriftAudit`) with UNIQUE/MERGE keys is non-trivial schema +
writer surface (P2:699-728). None traces to R1/R2/R3 (telemetry is nowhere in the requirement
files). The scope_split correctly buckets E29 as INGESTION (scope_split.md §1 E29 row: "Pure
observability … 'system self-heals without them'"). **Minimal alternative:** drop all 5 audit
labels from Phase-1 scope; the writer can emit a single flat sidecar JSON (already specified at
P2:584 `/tmp/dr_written_{source_id}_{run_id}.json`) for any observability the operator wants on
day 1. Does not drop a requirement. **Removed:** ~part of the "+20 over baseline" Cypher (P1:576-579)
+ write_audit_row() 5-label writer (P2:655-656) + E29 tests (P1:788).

### MIN-5 (major) — Lever #1 auto-repair (E26) is an accuracy-chasing patch that traces to NO requirement and partially defeats determinism
E26 (P1:358-366; P2:591-597) is a writer-side wrapper that *rewrites* an LLM name the canonicalizer
already rejected (e.g. strips `cut` from `opec_supply_cut`, sets driver_state=cut, re-canonicalizes).
No R1/R2/R3 obligation asks for auto-repair: R2's contract is *deterministic rejection* on a bad
name (B-R11f "if R1-R10 produce >1 unresolved candidate … REJECT as ambiguous", R2:86; B-M1 the
three outcomes are reuse / new proposal / **deterministic rejection**, R2:5). The canonical path
for a state-in-name error is K7 (state verb in name) → reject, with the producer re-emitting. E26
adds a second guessing layer that the user's "no fuzzy / no guess" prompt explicitly disfavors (P5:31
"no fuzzy matching … no subjective tie-break"; P5:42 "Do not use … closest-match language"). The
plan tries to keep it safe (exact-match-only commit, P1:361; "never guess when driver_state already
set", DriverImprovements P4:258-260) but it is still net-new branching logic (the magnitude regex,
trend-partner preference v3-3, V8-post-repair v4-5) that exists only to claw back ~3-4pp (P1:366).
Its expected recovery overlaps with Lever #3 retry anyway — the plan admits double-counting:
"a state-smuggle case Lever #1 catches … would otherwise have been caught by Lever #3 retry"
(P4:904). **Minimal alternative:** drop Lever #1 entirely; let canonicalize() return its structured
rejection and let Lever #3's informed-retry (which re-prompts the producer with the exact reason)
recover the same cases — one recovery mechanism, not two. Does not drop a requirement (no A/B/K
item; K7/K10/K11 are *rejection* obligations, which canonicalize already meets at P2:154-158).
**Removed:** repair_and_retry() per E26 (~part of +80 driver_writer LOC, P1:567), the `:DriverAutoRepair`
label, repair_kind/cascade_outcome enums (P2:702-707), and the Lever #1 tests (P1:765-770).

### MIN-6 (major) — Two recovery mechanisms (Lever #1 + Lever #3) for the same failure class; at most one is needed for Phase 1
Even if some recovery is wanted, the plan ships BOTH a deterministic repair (E26) AND an LLM
informed-retry (E28) that target overlapping failures, and admits the overlap nets the summed
~12-17pp down to ~10pp (P4:904 "OVERLAPPING RECOVERIES — many failures are catchable by more than
one lever … counting both … double-counts"). For minimum incremental work, ship ONE. Lever #3
(E28) has a verified production analog (orch.py:1347-1387, P1:395) and mirrors at ~65 LOC (P1:587)
— it is the cheaper, requirement-neutral choice and it covers Lever #1's cases by re-prompting.
Lever #1 is the redundant one (see MIN-5). **Minimal alternative:** keep Lever #3 only, drop Lever
#1. Net: ~one recovery path instead of two; removes the entire E26 surface without losing the
recovery (Lever #3 catches the same state/period smuggles via the rejection-reason re-prompt).
Cross-check: no requirement mandates *either* lever; both are accuracy projections above the
enforced >=90% bar.

### MIN-7 (minor→major) — The accuracy story rests on the Levers, so cutting them does NOT breach condition 1 (and the ~96-98% projection is unsupported anyway)
P1:883 "Accuracy after applied: ~96-98% projection pending Q1 measurement (up from ~87% v8
baseline)"; the enforced bar is only ">=95%" in the Goal (P1:5) / ">=90%" per the hard-conditions
table referenced in scope_split.md §8.1. Both prior phase-1 maps flag this as an OVERSTATEMENT
(scope_split.md §8.1; reuse_map.md Claim G: "OVERSTATED / UNSUPPORTED … no measurement behind it").
Because the ~96-98% is an unmeasured forecast built on summed lever recoveries that the plan itself
discounts for overlap (P4:904), removing Levers #1/#2's runtime machinery does not provably lower
achieved accuracy — it lowers an unproven projection. The mechanical determinism that actually
serves condition 1 is canonicalize() + V1-V14 + the deterministic-rejection gates (B-M1, B-R3,
B-R8, B-R11f), all of which are RETAINED in every minimal alternative above. **Recommendation:**
restate the Phase-1 accuracy claim as "deterministic canonicalize + static maps + V1-V14; bar
>=90/95% enforced; runtime self-heal deferred to Phase 2 with the second producer," and remove the
~96-98% headline until measured.

### MIN-8 (minor) — Mirror-map / LOC framing over-credits guidance reuse, working against the "max reuse" honesty
reuse_map.md establishes (verified against G1) that the only verbatim reuse is `slug()` (6 LOC,
G1:21-26) + structural skeletons; `canonicalize()` and everything downstream is net-new
(grep-empty for classify_token/order_by_slot/VocabSnapshot/SHAPE_REGEX in guidance). Yet the §J.1
Mirror Map (P2:623-626) still claims `driver_ids.driver_change_id() <- guidance_ids.guidance_change_id()`
— a function reuse_map.md proves does not exist (zero grep hits; real builder is
build_guidance_ids producing guidance_id/guidance_update_id, G1:814/962-966). And the §10 tally
labels driver_ids.py "(mirror guidance_ids.py)" (P1:557) when ~95% is net-new. This is not extra
*code*, but it misrepresents the reuse fraction the user is optimizing for, and the bad mirror row
is exactly the "engineer copies map → wrong name" hazard E15 warns about. **Recommendation:** fix
the §J.1 row to cite `build_guidance_ids` slot-ID assembly (G1:962-966), drop the fictional
`guidance_change_id`, and relabel driver_ids.py as "net-new grammar engine reusing slug() only" so
the reuse claim matches reality. No requirement impact; condition-3 honesty fix.

### MIN-9 (minor) — `provenance_source_driver_ids[]` on EquivalenceToken is audit-only by the plan's own words; redundant with the audit labels
P2 (DriverImprovements P4:403-408) `provenance_source_driver_ids` is "Audit-only; NOT used for
promotion counting." It duplicates what `:EquivalenceConflictAudit`/provenance telemetry already
capture, and (per MIN-2) the whole EquivalenceToken store should be deferred. Even if the store
stays, this array is dead weight in the creation/handoff JSON. **Minimal alternative:** drop it;
observation_keys[] already gives event-level dedup. No requirement references provenance arrays.

---

## What is GENUINELY MINIMAL and must NOT be cut (anti-false-positive)

- **canonicalize() 12 steps + classify_token + order_by_slot** (P2:118-182): the irreducible B-M1
  determinism mechanism. Net-new, no guidance equivalent (reuse_map.md §1 confirmed). Keep.
- **§F.1-§F.9 vocab banks as static markdown seed** (P2:296-441): these ARE the synonym/plural/
  acronym/banned/state/shortcut data K1-K60 need. Keep — they make the runtime stores (MIN-1/MIN-2)
  unnecessary for Phase 1.
- **V1-V14 validators** (P2:272-288): each maps to a K-risk / B-rule (req_canonical.md C.1). Keep.
  (V15 is registry-global = ingestion-leaning per scope_split.md §3; fine to delegate.)
- **New-token gate, banned-content gate, state-in-name gate, shape regex** (P2:120-158, 258-264):
  core B-R4/B-R7/B-R11c. Keep.
- **load_vocab_snapshot() READ + PIT registry render** (P2:184-226; E5): the A20 reuse-before-create
  read path. Keep (it is a read; only the *field computation* it reads is ingestion).
- **E16 input-JSON contract** (P2:545-582): the clean cut. Keep — verified self-contained handoff.
- **Cold-start seed list** (P2:663-690): day-1 anchors (data, not machinery). Keep.
- **Lever #3 informed retry IF any recovery is wanted** (P1:393-409): cheap (~65 LOC), production-proven,
  requirement-neutral; the single recovery path to keep over Lever #1.

These are not over-build; they are the smallest surface that delivers B-M1 + A20 + K1-K60.

---

## Net minimalism delta (quantified)

| Cut | Removes from creation surface | Requirement dropped? |
|---|---|---|
| MIN-1 EquivalenceToken store → static maps only | write_equivalence_tokens() + two-phase Cypher | none (K33-K35 met by static maps) |
| MIN-2 N=2 promotion gate (Phase-1 no-op) | candidate/promoted state machine + obs arrays + tests | none (A20 met by registry+map lookups) |
| MIN-3 PIT MIN-backdate (v9-1/v10-1/v10-2) | 2 backdate CASE blocks + v9-2 + v10-3 | none (PIT visibility = ingestion per C.2) |
| MIN-4 E29 5 audit labels | ~20 Cypher + write_audit_row() + tests | none (telemetry, not in R1/R2/R3) |
| MIN-5/6 Lever #1 auto-repair | repair_and_retry() + :DriverAutoRepair + tests | none (K7/K10/K11 = rejection, already met) |

Combined, these are essentially the entire Tier-6 net-new delta the plan books at ~250-350 impl +
~200-300 test LOC over baseline (P1:596) — i.e. removing them returns the creation build to roughly
the ~2,080 baseline while preserving every A/B/K requirement and the enforced determinism bar.
The retained surface (canonicalize + banks + V1-V14 + gates + read path + E16 + seed + Lever #3) is
the true minimum for conditions 1 & 2.
