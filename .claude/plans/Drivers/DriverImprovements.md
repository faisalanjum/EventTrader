> ⚠️ **SUPERSEDED IN PART — 2026-05-29.** Historical improvements log. Where any item below conflicts with the 2026-05-29 change-set (isolated Pattern B judge + learner-self-correct feedback retry + mandatory reconciliation job), the change-set WINS — see CombinedPlan.md (E20/E26/E27 region) + DriverOntology_Implementation.md §J. Specifically: "NO retroactive merge" is SUPERSEDED by the mandatory **reconciliation job**; the levers are no longer co-equal (**Pattern A learner-self-correct is PRIMARY**, **Lever #1 auto-repair DEMOTED/DEFERRED**); "no second LLM" is NARROWED to allow tiny, persisted, gated isolated judge calls.

# Driver Naming — Final Self-Heal Plan

> **Status**: v10 — applied ninth-round critiques. 6 NEW fixes (v10-1 VocabToken backdate via MIN(existing, source_pit) ON MATCH — REVERSES v9-1 "no-backdate" Phase-1 limitation; v10-2 EquivalenceToken visible_at backdate on each observation when sort()[N-1] decreases — REVERSES prior X3 deferral; v10-3 concurrency test wording fix at v8-6; v10-4 shortcut ≥2-token negative test; v10-5 Phase-B fold reminder for E27; v10-6 `key_drivers` → `contributing_factors` cleanup in 4 stale spec+test references per E30 + v7-1). 1 deferred (Bot A #1.2 — token/slot conflict guard; cross-slot token reuse rare in financial vocab + deterministic dict iteration provides Phase-1 tiebreaker; Phase 2 prep). HONEST REVERSAL: prior X3 deferral premise ("chronological backfills in Phase 1") was unstated and unenforced — E30 doesn't lock backfill order. v10-1 + v10-2 close the L6 inconsistency by mirroring Driver.registry_visible_at MIN-backdate pattern across all three stores. No code, no spec edits yet. Awaiting USER approval.
> **Source spec**: `.claude/plans/Drivers/CombinedPlan.md` v8 (25 E* edits + 4 OQs)
> **Goal**: push the steady-state clean-landing rate from ~87% baseline → ~96-98% after 8 quarters of data, without weakening L3 (deterministic canonicalize), L4 (no runtime human), or L5 (Neo4j-authoritative).

---

## §0. v10 changelog (5 NEW fixes on top of v9 + 1 deferred + 1 honest reversal)

| # | Fix | Section touched | Source | Verdict |
|---|---|---|---|---|
| v10-1 | **VocabToken backdate (MIN-on-MATCH) — closes L6 inconsistency** — ON MATCH semantics for `:VocabToken{slot, token}` now mirror `Driver.registry_visible_at`: `vocab_visible_at = CASE WHEN $source_pit < vocab_visible_at THEN $source_pit ELSE vocab_visible_at END`. v9-1 set vocab_visible_at ONCE at write and never backdated, creating an L6 inconsistency: Driver backdates (MIN of DC pit_cutoffs) but VocabToken did not. Under-visibility scenario: token first introduced by Driver D1 at 2024-Q3 → later D2 at 2024-Q1 uses same token; VocabToken stays at 2024-Q3 even though D2 makes the token "knowable" at Q1. v10-1 fixes via MIN-on-MATCH backdate. REVERSES v9-1's "Phase-1 precision limitation: no backdate" wording. | §2 Lever #2 read-path comment + §6.1 Neo4jXBRL edit list + §6.2 write_vocab_token + §7.z test | Bot A finding 1.1 | REAL L6 inconsistency closed |
| v10-2 | **EquivalenceToken visible_at backdate on each observation — REVERSES X3 deferral** — Phase 1 SET clause gains a backdate CASE: when `et.status = "promoted"` AND `sort(new_pit_cutoffs)[N-1] < et.equivalence_visible_at`, backdate visible_at to the lower value. Prior deferral premise ("Phase 1 chronological backfills make this rare") was unstated and unenforced — E30 doesn't lock backfill order. Bot A finding 2 correctly caught this. Same L6 MIN-backdate pattern as Driver.registry_visible_at + v10-1 VocabToken. Out-of-order observations now produce L6-correct visible_at; under-visibility eliminated. | §2 Lever #2 Phase 1 SET Cypher + §7.y v4-7 test | Bot A finding 2 (reverses X3 deferral) | REAL L6 inconsistency closed |
| v10-3 | **Concurrency test wording precision** — v8-6 test at line 1085 says "exactly ONE of the two writers' PHASE 1 returns `would_promote=true`, the other returns `would_promote=false`" but this is too strong: when count is at N-1, BOTH concurrent writers can return `would_promote=true` (Phase 1 + WITH compute happens before Phase 3's status flip). What's guaranteed is that only ONE Phase 3 status transition succeeds (the second's `WHERE et.status = "candidate"` filters out — no-op). Update test wording to reflect this. | §7.x v8-6 test | Bot A finding 3 | Test precision fix |
| v10-4 | **Shortcut ≥2-token gate negative test** — v7-2 rule at acceptance rule (e).3 says shortcut name MUST have ≥2 underscore-separated tokens (rejects single-word LLM hallucinations like `winter`, `crash`). But v4-3 / v5-10 test blocks have NO negative test that triggers this rule specifically. Add: `is_shortcut=true, name="winter", evidence ok, zero slot-classifying tokens` → expect rejection on `shortcut_min_tokens` (NOT on R11 evidence). | §7.y v4-3 test block | Bot B finding 4 | Test coverage gap |
| v10-5 | **Phase-B fold reminder: E27 must carry both v9-1 AND v9-2 (+ now v10-1 + v10-2)** — when DriverImprovements is folded into CombinedPlan §5 E26-E29 entries, the E27 (unified equivalence store + promotion) entry MUST explicitly include: (a) vocab_visible_at PIT-filter + MIN-backdate per v9-1 + v10-1, (b) intra-MERGE to_token conflict guard per v9-2, (c) equivalence_visible_at MIN-backdate per v10-2. Without explicit inclusion, these v9/v10 fixes can be lost in the fold. Add as a §6.1 process note. | §6.1 spec edits table | Bot B finding 5 | Phase-B fold process reminder |
| v10-6 | **Stale `key_drivers` → `contributing_factors` cleanup in retry spec + tests** — 4 references still used predictor's `key_drivers[]` (E30 + v7-1 say predictor is consumer-only, learner uses `primary_driver` + `contributing_factors[]`): (a) STAGE 2 ORPHANED R1 PROPOSALS DROP example at line ~818, (b) v3-8 surgical-replace integration test at line ~1110, (c) v4-9 array-order preservation unit test at line ~1179, (d) v4-15 orphaned-proposal-drop unit test at line ~1188. Each now reads `contributing_factors[i]` for learner Phase 1. Implementer copying these examples no longer gets the wrong field name. Closes the m6 + Bot-A finding 4 + Bot-B finding 3 cleanup that was tracked but not applied through v10. | §2 Lever #3 STAGE 2 + §7.x v3-8 + §7.y v4-9 + §7.y v4-15 | m6 / Bot A finding 4 / Bot B finding 3 (all convergent) | Stale-text cleanup |

### v10 deferred (1 — NOT applied)

| Bot suggestion | My counter |
|---|---|
| Bot A finding 1.2 — add token/slot conflict guard (one slot per token) | DEFERRED. Cross-slot token reuse (e.g., `cloud` classified as customer in D1, theme in D2) is rare in financial vocab. With deterministic Python 3.7+ dict iteration order on slot_vocabs (§F.1 fixed precedence: theme → object → customer → geography → institution → metric), a token in multiple slots gets a deterministic first-match tiebreaker — no L3 violation. Real correctness gap but LOW Phase-1 frequency. Phase 2 enablement work when cross-producer token-slot conflicts become more likely. Documenting as known limitation in §F.10 / classify_token() contract suffices for now. |

### v10 honest reversal note

Prior X3 deferral (in v9 push-back block) was based on the premise that "Phase 1 = learner-only chronological backfills per E30." This premise was WRONG on two counts: (a) E30 only locks predictor-consumer-scope, NOT backfill order — operators can run reverse-chrono backfills or arbitrary-order re-runs; (b) the "no over-engineering" filter incorrectly classified a 2-3 line CASE expression as new mechanism, when it's actually a parallel of the existing Driver.registry_visible_at MIN-backdate pattern. Bot A finding 2 caught both errors. v10-2 reverses the deferral; v10-1 applies the same fix to VocabToken (which had the same L6 inconsistency I missed in v9-1).

## §0.v9. v9 changelog (4 NEW fixes on top of v8 + 1 deferred + 1 cross-file tracked)

| # | Fix | Section touched | Source | Verdict |
|---|---|---|---|---|
| v9-1 | **VocabToken PIT-filter — closes L6 leak parallel to v4-7 (RUNTIME-PROMOTED scope; bootstrap-seed exception per D1)** — VocabToken schema gains `vocab_visible_at = source_driver.registry_visible_at` at write time; bootstrap read-path adds `WHERE vt.vocab_visible_at <= run.pit_cutoff` parallel to EquivalenceToken's filter. Without it, historical backfills loaded future-coined slot tokens UNFILTERED at the RUNTIME-promotion path, contaminating canonicalize step 9 classification with anachronistic vocabulary. Same architectural class as v4-7's EquivalenceToken fix; missed in v4-7 because slot-vocabs and equivalences were treated as separate growth paths (Pattern A1 vs A2 per v6-4). **Bootstrap-seed scope clarification (D1 resolution)**: this PIT-filter + MIN-backdate apply to RUNTIME-PROMOTED `:VocabToken` rows. The BOOTSTRAP-loaded §F.1 markdown seed uses SANE `vocab_visible_at` dates — TIMELESS anchors (`oil_price`, `fed_rate`, `china`, `revenue`, ...) use `EPOCH_SENTINEL`; ERA-BOUND modern tokens (`iphone`, `datacenter`, `hyperscaler`, `ai`, `gpu`, `vision_pro`, ...) carry realistic `vocab_visible_at` dates (err LATER = conservative) so the PIT-filtered hint excerpt excludes them on historical runs. (Code-time seed task per L4 = normal engineering; date-assignment + render-filter are integration-phase. Uses the EXISTING `vocab_visible_at` field — NOT a new mechanism.) PIT-safety of the LLM-facing layer rests on EXISTING `visible_at` fields (not a new mechanism) because (a) the LLM sees only a short slot/shortcut HINT EXCERPT rendered from the PIT-FILTERED vocab snapshot (`vocab_visible_at <= run.pit_cutoff`), so historical runs are ERA-SAFE — no future-coined tokens are shown; the FULL slot-vocab classification banks stay INTERNAL to `canonicalize()` (harmless + still deterministic given the frozen snapshot, because R11 ensures only evidence-present tokens are ever classified), (b) the Driver-registry PIT gate (`Driver.registry_visible_at <= run.pit_cutoff`) blocks visibility at the LLM-facing layer, and (c) R11 evidence-requirement (token must appear in evidence text) prevents proposing a name with a future-coined token under historical PIT. Mirrored in CombinedPlan L6 + E10. CombinedPlan E10 schema + Neo4jXBRLDesign VocabToken section + driver_writer.write_vocab_token() must also be updated. | §2 Lever #2 read path + tests | Bot B finding 1 + D1 user resolution | REAL — L6 leak parallel to v4-7 (runtime-promotion scope) |
| v9-2 | **Intra-MERGE-transaction to_token conflict guard** — Phase 0 (Python pre-check) has TOCTOU window: two writers can both pass Phase 0 (no existing) then race into Phase 1, with the loser silently appending observations to the winner's `to_token` row. Fix: add `WITH et WHERE et.to_token = $to` between MERGE and the array-update SET in Phase 1 Cypher. If filtered out, SET skipped, RETURN empty; Python detects empty-RETURN and writes `:EquivalenceConflictAudit` (same audit node as Phase 0 conflict detection). Closes concurrent-writer correctness race within the atomic Cypher transaction. | §2 Lever #2 Phase 1 Cypher + tests | Bot B finding 2 | REAL — concurrent-writer race |
| v9-3 | **Drop stale "or whole-name shortcut" from acceptance rule (a)** — line 380 said "(a) it is a one-token same-slot substitution (or whole-name shortcut)" but v5-5 removed `kind:shortcut` from the EquivalenceToken enum entirely; shortcuts route to direct `:Driver` registration via acceptance rule (e). The "(or whole-name shortcut)" parenthetical was leftover residue from v4 that contradicts both rule (e) and v5-5. Implementer reading rule (a) might attempt to create `EquivalenceToken{kind:shortcut}` records that the (now-restricted) kind enum would reject at runtime. Spec self-contradiction cleanup. | §2 Lever #2 acceptance rule (a) | Bot A finding 1 | REAL — spec self-contradiction |
| v9-4 | **Add item_index property to :DriverAutoRepair schema block** — idempotency UNIQUE constraint is `(source_id, item_index)` per v4-14 + v5-2, but the schema block at lines 277-294 omitted `item_index` from the property list. Implementer writing the schema would declare the UNIQUE constraint but never set the property on the node — MERGE would either fail at runtime or silently treat `item_index` as null and collapse all per-source repairs into one row. Add `item_index` to the property list with descriptive comment cross-referencing v4-14 + v5-2. | §2 Lever #1 audit schema | Bot A finding 2 | REAL — schema/key mismatch |

### v9 deferred (1 — NOT applied, with explicit rationale)

| Bot suggestion | My counter |
|---|---|
| Bot B finding 3 — recompute `equivalence_visible_at` on every observation when count ≥ N | DEFERRED to Phase 2 enablement. The pathological scenarios (concurrent same-equivalence emissions across producers + out-of-order PIT backfills with earlier-than-current-min PITs) are Phase 2+ phenomena. In Phase 1 (learner-only, chronological backfills per E30), out-of-order observations are rare; the under-visibility direction is conservative (no PIT leak — historical queries may under-see, not over-see, the equivalence) and at worst causes occasional registry-split during unusual backfill paths. Adding the Cypher CASE expression NOW for Phase-2 protection violates "only what's 100% required for Phase 1 ship." Phase 2 implementation will revisit the equivalence promotion path for multi-producer dispatch — natural home for this refinement. Documented as known Phase-1 PIT-precision limitation. |

### v9 cross-file edit (1 — separate Edit call to CombinedPlan.md, NOT applied here)

| Item | Where | Status |
|---|---|---|
| X6 — drop E12 from CombinedPlan §8 manifest (lines 401 + 406) | `.claude/plans/Drivers/CombinedPlan.md` | Tracked for separate application; not a DriverImprovements.md edit |

## §0.v8. v8 changelog (7 NEW fixes on top of v7 + 4 already-fixed in v6/v7 + 1 push-back)

| # | Fix | Section touched | Source | Verdict |
|---|---|---|---|---|
| v8-1 | **`is_shortcut: bool` declared as OPTIONAL Driver schema property** — v5-5 / v7-2 tests assert `:Driver{name:"chip_shortage", is_shortcut:true}` lands, but Neo4jXBRLDesign.md §C3.1 Driver OPTIONAL block never declared `is_shortcut`. Without it: (a) engineer reading schema doc misses the field; (b) canonicalize step 8 has no clean discriminator to identify which Drivers are shortcuts. Fix: add `is_shortcut: bool DEFAULT false` to Driver OPTIONAL fields; v5-5 acceptance rule (e) example updated; §6.1 Neo4jXBRLDesign edit list extended | §2 Lever #2 acceptance rule (e) + §6.1 spec edits | N1 | REAL — undeclared schema field used in tests |
| v8-2 | **CombinedPlan §13 Risk Register §3.3 deferral row marked RESOLVED** — line 601 still says "ConceptReq §3.3 deferral (predictor restricted to current bundle per OQ2-a)" but §3.3 is RESOLVED + OQ2 is MOOT per E30. Mark row RESOLVED with E30 reference | CombinedPlan.md §13 Risk Register | N4 | REAL stale fallout |
| v8-3 | **CombinedPlan Appendix A drops OQ2 from pending-decisions list** — line 637 still says "Decide OQ1 ..., OQ2 (predictor source restrict), OQ3 ..., OQ4 ..." but OQ2 is MOOT per E30 (line 345 marks it RESOLVED MOOT). Drop OQ2 from the list | CombinedPlan.md Appendix A | N5 | REAL stale fallout |
| v8-4 | **CombinedPlan Appendix A Neo4jXBRLDesign edit list drops E12** — line 634 says "Neo4jXBRLDesign.md: ~20 lines (E2, E3, E12-E14, E20-E22 ...)" but E12 is RESOLVED MOOT per line 197 + E30 (predictor doesn't emit, no source-visibility gap). Update list to "E2, E3, E13, E14, E20-E22" — drop E12. Add the v8-1 Driver.is_shortcut field declaration to the Neo4jXBRL edit list at the same time | CombinedPlan.md Appendix A | N7 | REAL stale fallout |
| v8-5 | **v5-1 to_token conflict test added** — bot correctly noted v5-1 (acceptance-time conflict at `equivalence_id` MERGE) is a distinct mechanism from v4-6 (collision recheck at promotion against Driver registry), with distinct audit nodes (`:EquivalenceConflictAudit` vs `:EquivalenceCollisionAudit`). Add explicit test for v5-1: candidate `topline → revenue` exists, new proposal claims `topline → income` → REJECT + `:EquivalenceConflictAudit` row + existing candidate observation_keys UNCHANGED | §7 v5 tests block | N9 | REAL coverage gap |
| v8-6 | **v5-4 Cypher concurrency test added** — bot correctly noted the two-phase pattern (v6-2) needs a concurrency test verifying observation_keys count is correct under MERGE locking when two writers MERGE same equivalence_id near-simultaneously. Leverages Neo4j's per-node MERGE locking. Add explicit test | §7 v5/v6 tests block | N10 | REAL coverage gap |
| v8-7 | **§10 cumulative gain projection citation cleanup** — line 670-672 said "+ Lever #2 ... v3-1/4/5" but v3-4 was REVERSED by v4-4 (V1-forgiving relaxation was UNDONE). Update Lever #2 citation to the actual contributing v* IDs: v3-1 + v4-4 (supersedes v3-4) + v3-5 + v4-6 + v4-7 + v5-1 + v5-5 + v5-6 | §10 cumulative gain projection | N11 | Attribution accuracy |

### v8 push-backs (NOT applied)

| Bot suggestion | My counter |
|---|---|
| N12 — confidence_bucket/magnitude_bucket should move from ORCHESTRATOR_STAMPED to LLM_AUTHORED_NON_DRIVER | REJECTED with explicit doc. Per Final.md §7, these are Python-derived from LLM-authored `confidence_score` and `expected_move_range_pct` (orchestrator computes the bin from the raw LLM values). They are correctly classified as orchestrator-stamped. The actual LLM-authored confidence assessment is `confidence_score` (raw), which IS in LLM_AUTHORED_NON_DRIVER by default → drift guard catches it. Bucket can echo through retries because it's deterministically derivable. Note: this concern applies to PREDICTOR schema fields only — per E30 + v7-1, Phase 1 retry is learner-only and learner's §8 schema has no confidence_bucket/magnitude_bucket fields anyway. Either way, no drift-guard hole exists |
| N2, N3, N6, N8 — claimed stale wording | NOT APPLIED — verified clean post-v6/v7 (bot scanned older snapshot). N2 coverage math fixed v6-6; N3 SKILL.md LOC fixed v6-6; N6 Appendix A coverage fixed v6-6; N8 §6.1 §7+§8 fixed v6-3 |

## §0.v7. v7 changelog (3 fixes on top of v6 — kept for forensics)

| # | Fix | Section touched | Source | Verdict |
|---|---|---|---|---|
| v7-1 | **Learner-only retry context per E30** — three spots in §2 Lever #3 referenced `key_drivers[]` (predictor's analysis-prose field per Final.md §7), but Phase 1 retry runs ONLY against learner emissions (learner's schema = `primary_driver` + `contributing_factors[]` + `propose_new_drivers[]`). Fixes: (a) retry prompt instruction drops `key_drivers[]` (b) DRIVER_FIELDS whitelist becomes producer-specific dispatch — for learner = `{primary_driver, contributing_factors, propose_new_drivers}`; for future Mode 2 news = `{items, propose_new_drivers}` (c) STAGE 2 array-order precondition drops `key_drivers[]` length/order line (learner has no key_drivers field) | §2 Lever #3 retry prompt + STAGE 1 DRIVER_FIELDS + STAGE 2 array order | Finding #1 | REAL — predictor schema leaked into learner retry |
| v7-2 | **Shortcut acceptance ≥2-token gate + explicit trade-off doc** — bot raised the integrity concern that one-off LLM mistake-shortcuts can land permanently. PUSH BACK on N=2 (would deadlock first emission of any real new shortcut). INSTEAD: add a mechanical `≥2-token-required` rule for shortcut names (rejects single-word LLM hallucinations like `winter`, `crash`, `disaster` while preserving multi-token canonical shortcuts like `chip_shortage`, `fda_approval`, `yield_curve`). Plus: more explicit recall-vs-integrity trade-off acknowledgment in acceptance rule (e) point 7 | §2 Lever #2 acceptance rule (e) | Finding #5 (partial — reject N=2, apply tightening) | PARTIAL — strengthen gate, push back on deadlock-inducing N=2 |
| v7-3 | **CombinedPlan E16 source_type enum cleanup** — line 246 still listed `prediction_result` in the `source_type ∈ {prediction_result, learner_result, news, fiscal_kpi}` enum. Per E30's PERMANENT stance ("predictor is consumer-only" — per the ConceptReq §5.4 update — not "for now"), prediction_result will never be a writer input source_type. Remove it. The historical formula in Round-2/3 forensics rows stays as-is (audit trail) | CombinedPlan.md E16 source_type enum | Finding #7 (partial — only line 246 left; 452/506 fixed in v6-6) | REAL — final E30 propagation step |

### v7 push-backs (NOT applied)

| Bot suggestion | My counter |
|---|---|
| Finding #5 — "Require N=2 for new shortcuts" | REJECTED. Deadlock: first emission of a real shortcut has no Driver yet (not promoted), so the LLM at quarter 2 sees no anchor in the catalog → emits the shortcut form again, still no Driver → never lands. Recall collapses for genuine new shortcuts. Tighter trade-off: keep immediate landing + add mechanical ≥2-token gate (v7-2 above) to reject single-word LLM hallucinations |
| Findings #2, #3, #4, #6 — claimed stale wording | NOT APPLIED — verified clean post-v6 (bot scanned older snapshot). §7/§8 wording fixed in v6-3; VocabToken N=2 fixed in v6-4 (Pattern A1 says IMMEDIATE); Cypher Python-between fixed in v6-2 (two-phase pattern); merge formula fixed in v6-1 |

## §0.v6. v6 changelog (7 fixes on top of v5 — kept for forensics)

| # | Fix | Section touched | Source | Verdict |
|---|---|---|---|---|
| v6-1 | **Retry merge formula — subtract REPLACED R1 proposals** — v5-11 added STAGE 3 same-name replacement, but the FINAL MERGED RESULT_JSON formula at §2 Lever #3 still said `propose_new_drivers = R1's entries + STAGE-3-accepted new entries` — which would KEEP the broken R1 proposal alongside the corrected R2 replacement, double-listing the name. Fix: `final propose_new_drivers = (R1 - {entries replaced same-name by R2} - {orphaned per v4-15}) + {STAGE-3 CASE A replacements} + {STAGE-3 CASE B unresolved-carve-out additions}` | §2 Lever #3 STAGE 2 + STAGE 3 + FINAL MERGED | Finding #1 | REAL merge bug — same-name dedup gap |
| v6-2 | **Promotion Cypher two-phase pattern — Python collision check between two queries, NOT within one** — v5-4 said "Python runs collision check between WITH and SET" in a SINGLE Cypher query. That is IMPOSSIBLE — Cypher executes as one atomic statement; Python cannot interrupt midstream. Fix: split into two Cypher queries. Phase 1 query: MERGE + update observation_keys/pit_cutoffs/provenance + RETURN `would_promote`, observation_count, current Driver-registry-state-at-promotion-time. Phase 2 (Python): if would_promote, run collision-recheck against registry. Phase 3 query: SET status="promoted" + promoted_at + equivalence_visible_at IFF Python allows | §2 Lever #2 promotion Cypher | Finding #2 | REAL implementation trap — Cypher atomicity |
| v6-3 | **E21 wording corrected — §8 ONLY, not §7/§8** — multiple locations (§3 precondition, §6.1 spec edits table, §9 Day 0 timeline, §10 bottom-line, §9 Day 5b note) still said "§7 + §8 schema migration" or quoted §7 as "contradicting the ontology." Per E30, §7 (predictor) stays free-form by design — NOT contradicting. E21 precondition migrates §8 (learner) only | §3, §6.1, §9 Day 0 + Day 5b note, §10 bottom-line | Finding #3 | REAL stale wording in 6 locations |
| v6-4 | **Pattern A split: VocabToken (immediate, per E10) vs EquivalenceToken (N=2 promotion)** — §5 + §10 simplification grouped both stores under "N=2 promotion gate." But per E10, accepted new slot-vocab tokens append to `:VocabToken` IMMEDIATELY after R11 acceptance; no N=2 gate. Only `:EquivalenceToken{synonym/plural/acronym}` uses N=2. Fix: split Pattern A into A1 (`:VocabToken` immediate-append) + A2 (`:EquivalenceToken` N=2 promotion). Pattern B (shortcut → Driver row) unchanged | §5 architecture table + §10 simplification | Finding #4 | REAL — different promotion lifecycle wrongly conflated |
| v6-5 | **Strict-vs-candidate alias routing refined** — v5-6 over-broadly said "ALL proposed aliases route to :EquivalenceToken, NEVER added to Driver.aliases[]." But strict aliases (where `canonicalize(alias, current_vocab) == parent.name` already — e.g., word-order variants resolved via slot-reorder, OR aliases using already-promoted equivalences) PASS V1 strictly and SHOULD land in `Driver.aliases[]` for B4 fast-path lookup. Only NON-STRICT aliases (V1 would fail because alias requires a NEW transform not yet in vocab) get routed to `:EquivalenceToken` as candidates. Both paths keep V1 strict; routing decision per-alias at registration time | §2 Lever #2 acceptance rule (d) + tests | Finding #5 | REAL — v5-6 was over-correction; strict aliases lose B4 fast-path |
| v6-6 | **CombinedPlan stale E30 fallout** — `CombinedPlan.md` still has: (a) coverage math "9 ✅ + 3 ⏸ DEFERRED" at lines 434, 534, 630 — should be "10 ✅ + 2 ⏸" since E30 flipped §3.3 from DEFERRED to RESOLVED. (b) §6.3 / §11 phrasing of "predictor + learner SKILL edits" stale per E30 (learner only). (c) Manifest references to §7/§8 migration stale per v6-3 (§8 only) | CombinedPlan.md L434/L534/L630 + spec edit / impl order references | Finding #6 | REAL — fallout from E30 not fully propagated |
| v6-7 | **ConceptReq §2.2.1.4 "curate manually" wording clarified** — line 44 says "we will curate a list of most effective drivers manually before setting up this trigger" — this is future Phase 4 (trade-triggering) scope, NOT Phase 1 driver naming. But the literal wording "curate manually" conflicts with the no-runtime-human posture if read out of context. Fix: explicit "Phase 4 future scope" marker + reframe to "ranking based on objective signals (impact breadth, historical move size)" rather than "manual curation" | ConceptualRequirements.md §2.2.1.4 | Finding #7 | REAL minor — context-disambiguation |

### v6 push-backs (NOT applied)

None. All 7 findings are real correctness/clarity issues; no over-claims from this audit round.

## §0.v5. v5 changelog (13 fixes on top of v4 — kept for forensics)

| # | Fix | Section touched | Source | Verdict |
|---|---|---|---|---|
| v5-1 | **`equivalence_id` semantics + "one to_token per (kind, from_token)" rule** — keep ID formula `slug("eq:" + kind + ":" + from_token)` (no widening with to_token; the `phrase` clause from v4 is removed since v5-5 drops kind:shortcut). ADD explicit rule: for each `(kind, from_token)` pair, at most one canonical `to_token` may exist. Conflicting proposal (e.g., `topline → revenue` candidate exists; new proposal claims `topline → income`) → REJECT new proposal + log `:EquivalenceConflictAudit`. Do NOT count toward promotion of the first | §2 Lever #2 schema + acceptance rule | A1 / Bot2 #1 / Bot3 #3 | REAL — silent collision risk in v4 |
| v5-2 | **§4.2 audit idempotency keys updated** — line 648 still said `(source_id, original_name)` for `:DriverAutoRepair`; contradicts v4-14. Fix to `(source_id, item_index)`. PUSH BACK on Bot3 #5 adding `run_id` — defeats v4-14's intentional overwrite-on-retry | §4.2 idempotency text | A2 / Bot2 #7 / Bot3 #5 | REAL stale text |
| v5-3 | **§7 v3-stale tests purged** — multiple v3 tests still asserted `source_driver_ids` and `promoted_at` for PIT filter (lines 748, 751-753, 757); v3-4 test still said "V1 forgiving" (line 787). These would mislead implementation. Mark SUPERSEDED or replace with v4-aligned versions | §7.1 / §7.x | A3 / A4 / Bot2 #6 / Bot3 #6 | REAL — implementation hazard |
| v5-4 | **Promotion Cypher refactored — compute BEFORE SET** — v4 ON MATCH SET appends to `observation_keys` then in the same block uses `size(et.observation_keys)` for status. Cypher SET evaluation may read old array. Refactor: pre-compute `new_obs_keys`, `new_count`, `would_promote` in a WITH clause; run collision recheck BEFORE flipping status; then commit. Removes one-late-promotion + collision-race risks | §2 Lever #2 promotion Cypher | Bot2 #2 / Bot3 #2 | REAL Cypher-semantics ambiguity |
| v5-5 | **DROP `:EquivalenceToken{kind:shortcut}` entirely** — v4 had it as "telemetry-only" for shortcuts that already land as `:Driver` rows. Bot 3 #4 correctly notes this is parallel-store bloat. Registry IS the shortcut store: a shortcut Driver registers as `:Driver{name:"chip_shortage"}` directly; future B3 lookups hit it. No `:EquivalenceToken` needed for kind:shortcut. EquivalenceToken `kind` enum reduces to `{synonym, plural, acronym}` only. Simpler, no recall loss | §2 Lever #2 schema (kind enum) + §2 Lever #2 acceptance rule (e) + §5 simplification table + tests | Bot2 #3 + Bot3 #4 + USER confirmed | SIMPLIFICATION — reduces schema |
| v5-6 | **DROP alias-sync to `Driver.aliases[]`** — v4 had an "explicit orchestrator step syncs from_token-form into parent Driver's aliases[] after promotion." Bot 3 #1-partial + Bot 2 #5 second option correctly note: once equivalence is promoted, `canonicalize()` step 5 folds the synonym automatically at next emission → B6 hits registry → reuse works. `Driver.aliases[]` becomes redundant for promoted equivalences (still works for aliases explicitly authored at Driver creation). Removes ~30 LOC of sync logic + simplifies post-promotion behavior | §2 Lever #2 acceptance rule (d) + backward-compat block + tests | B1 / Bot2 #5 / Bot3 #1-partial + USER confirmed | SIMPLIFICATION — drops sync mechanism |
| v5-7 | **Drop v4-12 Cypher migration suggestion** — Bot 1 B2 correctly notes: the `SET legacy.deprecated_at = $now, legacy.replaced_by = "driver:cloud_revenue"` migration leaves reader-behavior undefined (which readers respect deprecated_at? B3? bundle renderer?). Cleanest: drop migration suggestion entirely. Pre-promotion splits stay as audit-only known limitation. No retroactive merge mechanism specified | §2 Lever #2 backward-compat block | B2 | Clarity — drops underspec'd mechanism |
| v5-8 | **§3 precondition cross-link to v4-13 E20 reconciliation** — readers scanning §3 in isolation would miss the "informed retry is same-session re-emission, not a second extraction pass" clarification. Add one-line cross-ref | §3 precondition | B3 | Minor clarity |
| v5-9 | **v4-9 order-preserved check — spell out tuple equality** — v4 said "preserve length + order" but didn't specify equality criterion. Add: "PASSED indices must have IDENTICAL `(driver_name, driver_state, direction, evidence)` tuple in R2; FAILED indices may differ" | §2 Lever #3 STAGE 2 ARRAY-ORDER PRECONDITION | C1 | Minor clarity |
| v5-10 | **v4-3 adversarial unit test** — add test: "LLM emits `is_shortcut=true, name='made_up_phrase'` with no real evidence ground in registry/source → expect rejection on R11 evidence requirement (not on shape/banned)" | §7 verification v4-3 block | C2 | Coverage gap |
| v5-11 | **STAGE 3 same-name proposal replacement** — v4 STAGE 3 only allowed NEW propose_new_drivers entries when referenced by `unresolved_driver_name` rejection. But R1 may have an existing failed proposal `{name:"foo"}` whose V1/V6/V8/V10 failed; R2 needs to send a CORRECTED `{name:"foo"}` proposal to fix it. Refine STAGE 3: R2 MAY replace same-name R1 proposals with corrected versions (run R11+V1-V15 on the replacement); truly NEW-name proposals still require the unresolved_driver_name carve-out | §2 Lever #3 STAGE 3 | Bot3 #1 | REAL retry-coverage gap |
| v5-12 | **§10 bottom-line L6 wording updated** — line 954 still said "promoted_at" for L6 PIT visibility. v4-7 changed PIT anchor to `equivalence_visible_at`. Update §10 to match | §10 bottom line L6 row | Bot2 #8 | Stale wording |
| v5-13 | **CombinedPlan stale missing-file warning removed** — CombinedPlan line 436 still has Round-7 warning that `ConceptualRequirements.md` was "found MISSING". File exists (was edited in Option 1 step). Remove or replace with "verified present, file aligned with §3.3 clarification per E30" | CombinedPlan.md line 436 | Bot3 #7 | Stale post-Option-1 |

### v5 push-backs (NOT applied)

| Bot suggestion | My counter |
|---|---|
| Bot 3 #5: audit key `(source_id, run_id, item_index)` | Rejected. v4-14's intentional design is overwrite-on-retry (same emission slot = same row, last-write-wins). Adding `run_id` would bloat audit table linearly with retries; sidecar JSON + run_ledger preserve full retry history separately |
| Bot 2 #9: collapse doc into E26-E29 + short appendix | DEFERRED, not rejected. Will happen during the "fold-into-CombinedPlan" step in the user's stated order (DriverImprovements → CombinedPlan E26+ entries). Premature to collapse before fold |

## §0.v4. v4 changelog (19 fixes — kept for forensics)

| # | Fix | Section touched | Source | Verdict |
|---|---|---|---|---|
| v4-1 | **Rename `source_driver_ids` → `observation_keys[]`** — field name was misleading; Cypher uses emission identifiers, not Driver IDs | §2 Lever #2 schema + Cypher + tests | Set1#1 / Set2#1 / Set3 N6 | REAL bug; my v3 was inconsistent |
| v4-2 | **Promotion observation key = event-level dedup** — strip producer prefix from source_id so `predictor:AAPL:Q2_FY2026` and `learner:AAPL:Q2_FY2026` share `AAPL:Q2_FY2026` as their observation_key. Predictor+learner emitting same equivalence on same event count as ONE independent observation, not two | §2 Lever #2 promotion rule | Set1#2 | REAL — same evidence base, weak independence; conservative interpretation |
| v4-3 | **Shortcut bootstrap — explicit canonicalize bypass path** — `is_shortcut=true` proposals follow a SPECIAL path in writer: shape regex + banned-content + zero-slot-token check + R11 evidence, then Driver lands immediately (NOT deferred). `:EquivalenceToken{kind:shortcut}` is recorded as telemetry/discoverability artifact, NOT a promotion gate for shortcuts. Rationale: R11+shape+banned+zero-slot already gives shortcut-quality protection equivalent to N=2 promotion for other equivalence kinds; deferring would sacrifice first-emission recall | §2 Lever #2 acceptance rule (e) | Set1#3 / Set2#2 | REAL — circularity broken |
| v4-4 | **REVERSE v3-4: V1 stays strict (E6 unchanged)** — proposed `aliases[]` are NOT added to `Driver.aliases[]` at registration; they live only in `:EquivalenceToken` as candidates. After promotion, an explicit orchestrator step syncs `from_token`-form into the parent Driver's `aliases[]`. V1 remains the locked E6 rule (`canonicalize(alias) == parent.name`) and never weakens | §2 Lever #2 acceptance rule (d) | Set1#4 / supersedes v3-4 | REAL — cleaner arch; v3-4 was wrong direction |
| v4-5 | **Auto-repair must pass V8 before write commits** — after PASS canonicalize + EXACT-MATCH existing Driver, also require repaired `driver_state ∈ Driver.allowed_states`. V8 failure → defer to Lever #3 retry. Honors E25 (registry wins; never silently mutate allowed_states) | §2 Lever #1 auto-repair table | Set1#5 / Set3 N9 | REAL clarification — was implicit, now explicit |
| v4-6 | **`:EquivalenceToken.equivalence_id` UNIQUE + collision recheck at promotion** — add `equivalence_id` derived from `(kind, from_token, to_token, phrase)` with UNIQUE Neo4j constraint. At promotion time (when N reached), re-run acceptance checks (collision with new Drivers, ambiguity vs newer candidates) against CURRENT registry state — registry may have changed between candidate creation and promotion | §2 Lever #2 schema + promotion path | Set1#6 | REAL safety — multi-quarter gap between candidate + promotion is the risk window |
| v4-7 | **PIT visibility via `equivalence_visible_at`, NOT wall-clock `promoted_at`** — `equivalence_visible_at = sorted(observation_pit_cutoffs)[N-1]` (the pit_cutoff at which the Nth distinct observation occurred). PIT filter uses this. `promoted_at` kept as wall-clock audit only. Aligns with L6's `Driver.registry_visible_at = MIN(DC.pit_cutoff)` semantics — PIT visibility is anchored in source pit_cutoffs, never wall-clock | §2 Lever #2 schema + read path | Set1#7 / Set2#3 | REAL — L6 alignment bug in v3 |
| v4-8 | **Drift guard INVERSION (whitelist + invert)** — replace enumerated non-driver field list with: `DRIVER_FIELDS = {key_drivers, primary_driver, contributing_factors, propose_new_drivers}`. `ORCHESTRATOR_STAMPED = {schema_version, ticker, quarter_label, predicted_at, attributed_at, model_version, sdk_session_id, pit_mode, pit_cutoff, pit_boundary_source, pit_boundary_event, prediction_delay_sec, confidence_bucket, magnitude_bucket, actual_return_pct, context_bundle_ref, prediction_result_ref}`. Diff R1 vs R2 across `(all_fields - DRIVER_FIELDS - ORCHESTRATOR_STAMPED)` only. Future-proof against schema additions | §2 Lever #3 merge logic STAGE 1 | Set1#8 / Set2#5 / Set3 N7 | REAL — orchestrator-stamped false-positives + future schema safety |
| v4-9 | **Retry must preserve array length + order** — `key_drivers[]` / `contributing_factors[]` in R2 retry MUST have same length and ordering as R1. Orchestrator validates on receipt; mismatch → `FAILED_RETRY_SHAPE_VIOLATION`, R1 rejected drivers stay rejected. Prevents merge-by-index from silently swapping tags when LLM reorders | §2 Lever #3 merge logic STAGE 2 | Set1#9 | REAL — index-based merge was fragile |
| v4-10 | **§9 Day 5b dedup — remove E21 from Day 5b** | §9 implementation order | Set1#10 / Set3 N1 | REAL contradiction in v3; verified line 676 |
| v4-11 | **§9 stale "Day 5 SKILL.md" line removed** | §9 implementation order | Set3 N2 | REAL — verified line 679; leftover from v2 |
| v4-12 | **v3-7 backward-compat migration replaced** — was `SET d.aliases = d.aliases + ["cloud_topline"]` which DOESN'T merge legacy split (B3 still hits legacy Driver). Correct pattern: `SET legacy.deprecated_at = $now, legacy.replaced_by = "driver:cloud_revenue"` (uses existing Driver schema OPTIONAL fields per Neo4jXBRLDesign §C3.1). B3 still hits legacy; subsequent code should respect deprecated_at + follow replaced_by. Or: don't migrate at all — leave splits as audit-only known limitation | §2 Lever #2 backward-compat block (v3-7) | Set3 N3 | REAL — my v3 Cypher suggestion was broken |
| v4-13 | **Lever #3 vs E20 clarification** — E20 prohibits a SECOND extraction LLM PASS (a separate /extract pipeline call). Lever #3 is H2 informed-retry within the SAME predictor/learner session — same producer LLM, same bundle, same source_id. NOT an extraction pass. Add one line to §2 Lever #3 head + §3 precondition note | §2 Lever #3 head + §3 | Set3 N5 | REAL interpretation gap |
| v4-14 | **Auto-repair audit idempotency key includes `item_index`** — change MERGE key from `(source_id, original_name)` to `(source_id, item_index)`. Handles multi-ticker news where same source_id + same original_name produces distinct repairs per item position. `item_index` is the position in the `items[]` array (stable across retries since LLM emits items in deterministic bundle-driven order) | §2 Lever #1 audit schema | Set2#4 | REAL for Mode-2 news; future-proofs Mode-1 too |
| v4-15 | **Merge logic drops orphaned R1 propose_new_drivers** — after STAGE 2 surgical-replace, if a R1 proposal entry is no longer referenced by ANY tag in the merged result, drop it (otherwise V13 `proposal_without_use` rejects the merged emission) | §2 Lever #3 merge logic STAGE 2 trailing step | Set3 N8 | REAL — V13 trigger in v3 |
| v4-16 | **Document `_trend` as the only canonical trend-suffix** — current ontology recognizes only `_trend` as the trend-class suffix per DriverProcess.html §B2. If future ontology adds `_growth`/`_momentum`/`_motion` as additional trend suffixes, v3-3 logic must widen — but that's an ontology rev, not silent code drift. Document as inline note | §2 Lever #1 trend-partner preference | Set3 N10 | Doc clarification |
| v4-17 | **Add cascade_outcome unit test** — verify the field is populated correctly across each outcome (PASS / REJECTION_NO_METRIC / REJECTION_BANNED / DEFERRED_TO_RETRY / FINAL_REJECT_OTHER) | §7 verification | Set3 N11 | Coverage gap |
| v4-18 | **Fix v3-3 attribution** — was "Bot A #5 / Bot B #5" but Bot A #5 was about equivalence promotion (mapped to v3-4), not trend-partner. Correct: "Bot B #5" only | §0 v3 changelog row v3-3 | Set3 N12 | Attribution accuracy |
| v4-19 | **Inline note about cumulative gain math** — standalone gains sum to ~12-17pp but cumulative shows ~10pp due to overlapping recoveries (e.g., a state-smuggle case Lever #1 catches deterministically would otherwise have been caught by Lever #3 retry). Add inline transparency note | §2 cumulative gain projection | Set3 N13 | Transparency |

### What I PUSHED BACK on (didn't apply verbatim)

| Bot suggestion | My counter |
|---|---|
| "Bot N12: v3 changelog cites Bot A #5 twice (v3-3 and v3-4); verify or correct" | v4-18 fixes attribution. NOT renumbering items since downstream references depend on v3-* IDs |
| "Set1 #6: add separate equivalence_id AND collision recheck" | Applied both as v4-6 (single fix) |
| Implicit suggestion that v4 should renumber/restructure changelogs | Keep v2/v3/v4 changelog sections for forensics. Rolling up loses audit trail of what was decided when |
| Set2 #2 ambiguity "candidate-only/deferred driver" for shortcuts | Applied v4-3 with EXPLICIT "Driver lands immediately + EquivalenceToken is telemetry-only" — chose recall preservation over deferred promotion. Trade-off documented |

## §0.v3. v3 changelog (14 fixes — kept for forensics)

| # | Fix | Section touched | Source | Verdict |
|---|---|---|---|---|
| v3-1 | **canonicalize() takes vocab snapshot as PARAMETER** — no DB reads inside; writer loads markdown seed + Neo4j promoted entries at bootstrap, passes immutable snapshot dict. Restores L3 purity (same snapshot + same input → same output, always) | §2 Lever #2 read path | Bot A #3 / Bot B #1 | REAL L3 fix — my v2 was sloppy |
| v3-2 | **Magnitude strip narrowed to unit-suffix patterns only** — must match `{pct, bps, x, percent, basis_points}` suffix OR `/^\d/` immediately followed by such a unit. Bare `/^\d/` strip would incorrectly remove legit tokens like `5g`, `10yr`, `3nm`, `3d`, `4k` — these are domain technology designations, not magnitudes | §2 Lever #1 auto-repair table | Bot A #4 / Bot B #5 | REAL semantic bug |
| v3-3 | **Trend-partner check before bare-metric collapse** — when stripping a `trend_motion` state verb (e.g., `revenue_decline → revenue` + state=declined), first check registry for a `{metric}_trend` partner. If exists, prefer the trend Driver. If not and result is bare metric, defer to Lever #3 retry | §2 Lever #1 auto-repair table | Bot B #5 (v4-18: attribution corrected — Bot A #5 was about equivalence promotion, not trend-partner) | REAL semantic fix |
| v3-4 | **Equivalence circularity broken** — proposed `aliases[]` are recorded as CANDIDATE equivalences, NOT written to `Driver.aliases[]` until promoted. V1 (`canonicalize(alias) == parent_name`) is forgiving toward candidate-equivalence forms — does not reject the proposing Driver if the alias only canonicalizes correctly AFTER the candidate equivalence promotes | §2 Lever #2 acceptance + promotion | Bot A #5 / Bot B refined | REAL architecture fix — circular dep my v2 introduced |
| v3-5 | **`is_shortcut: bool` added to E16 input JSON contract + SKILL.md emission teaching** | §2 Lever #2 + §6.2 + §6.3 | Bot B #4 | REAL spec gap |
| v3-6 | **`cascade_outcome` field on `:DriverAutoRepair`** — captures what happened after re-canonicalize (PASS / REJECTION_NO_METRIC / REJECTION_BANNED / DEFERRED_TO_RETRY). Telemetry richness | §2 Lever #1 audit schema | Bot B #6 | Incremental but useful |
| v3-7 | **Backward-compat: pre-promotion splits stay as-is** — Driver.name is immutable per §C3.1. Equivalence promotion does NOT retroactively merge legacy split Drivers. Documented as known limitation | §2 Lever #2 acceptance rule | Bot B #7 | REAL clarification |
| v3-8 | **Lever #3 surgical-replace by tag index + reject scope-creep proposals** — PASSED drivers stay verbatim from R1; FAILED tags replaced by R2 versions. NEW `propose_new_drivers[]` entries in R2 are rejected EXCEPT when an entry is referenced by a previously-rejected tag whose rejection_reason was `unresolved_driver_name` (the one legitimate recovery path) | §2 Lever #3 merge logic | Bot B #8 (with my carve-out) | REAL safety improvement |
| v3-9 | **Lever #3 hard-reject on non-driver field drift** — orchestrator diffs R1 vs R2 across non-driver fields (analysis, thesis, falsifier, evidence_ledger, etc.); ANY change → mark retry as `FAILED_DRIFT_GUARD`, all R1 rejected drivers stay rejected. Audit-logged with field-diff for observability | §2 Lever #3 merge logic | Bot B #9 | Stricter discipline; defensible |
| v3-10 | **LOC honesty corrected** — ~250-350 impl LOC + ~200-300 test LOC on top of CombinedPlan baseline (was understated as ~150 total in v2; excluded tests + 9-fix refinements) | §10 bottom line | Bot B #10 | Honest correction |
| v3-11 | **Timeline 6-8 → 7-9 days; Day 5 PRE-SPLIT into 5a + 5b** at plan time (not as runtime risk) | §9 implementation order | Bot B #11 | Honest scheduling |
| v3-12 | **Pp gains re-labeled as "projections pending Q1 measurement"** — not claimed as fact | §2 cumulative gain + §10 | Bot B #12 | Honest framing |
| v3-13 | **§8 rejections list expanded** — explicit reject for (a) aggressive pre-launch seed expansion (50-100 entries), (b) adversarial-fuzz test suite expansion pre-launch | §8 | Bot B #13 | Document what we implicitly rejected |
| v3-14 | **N=2 is a hard code-time constant** — clarified; NOT runtime-env-tunable. Aligns with L4 (no runtime curator). Engineer may edit in source; never via env var or config file at runtime | §2 Lever #2 promotion rule | Bot B #14 | Language clarification |

## §0.v2. v2 changelog (9 fixes — kept for forensics)

| # | Fix | Section touched | Source |
|---|---|---|---|
| 1 | PIT filter `promoted_at <= run.pit_cutoff` on EquivalenceToken read paths — prevents future-synonym leak in historical backfills | §2 Lever #2 read path | ChatGPT critique |
| 2 | Hide `candidate` equivalences from the LLM-visible bundle entirely — only `promoted` entries enter the prompt; prevents fast-pass of the promotion gate via LLM self-reinforcement | §2 Lever #2 read path | ChatGPT critique |
| 3 | Promotion counts **distinct** `source_id` only — derive `observation_count` from `size(source_driver_ids)`, append-only-if-not-present. Same retry / same predictor+learner pair counts as ONE | §2 Lever #2 schema + promotion rule | ChatGPT critique |
| 4 | Auto-repair ONLY commits write if repaired name EXACT-MATCHES an existing Driver. Brand-new bare-metric names route through Lever #3 retry instead | §2 Lever #1 auto-repair table | ChatGPT critique (principle) + self-audit (mechanism) |
| 5 | Rename `run_driver_write_via_sdk()` → `run_driver_write()` (transport-neutral per Final.md §5; SDK is forbidden, TMUX is the transport) | §2 Lever #3 + §6.2 + §9 | ChatGPT critique |
| 6 | Reframe audit narrative — telemetry-only / optional code-time cleanup. **Self-heal does NOT require seed edits** — Neo4j Token store covers it fully | §4.2 | ChatGPT critique |
| 7 | Specify idempotency key for `:DriverAutoRepair` upsert: UNIQUE on `(source_id, original_name)` | §2 Lever #1 schema | Self-audit |
| 8 | Spec the merge logic in Lever #3: retry returns full `result.json`; orchestrator merges driver-fields-only, keeps first-emission analysis/thesis/falsifier verbatim | §2 Lever #3 | Self-audit |
| 9 | Case-insensitive comparison in auto-repair conflict check (`driver_state.lower() == t.lower()`) | §2 Lever #1 auto-repair table | Self-audit |

---

## §1.0. Producer Scope (clarified post-v4; precondition for everything below)

**Phase-1 Driver registry producer = `learner` ONLY.** Predictor is a CONSUMER of driver_tags from prior learner reports (via `prior_reports_context` per Final.md §6) and reads the Driver Registry Catalog via the bundle for awareness — but does NOT emit drivers to the registry. Predictor's `prediction/result.json` §7 `key_drivers[]` stays as free-form analysis prose (no canonical-form discipline). Tracked in CombinedPlan E30 (added during v4 cleanup); resolves the ConceptReq §3.2 vs §3.3 contradiction in favor of §3.2.

**Implications for this plan**:
- **v4-2** (event-level dedup) is effectively a NO-OP in Phase 1 — only one producer per event means no producer-prefix-collapse needed. Kept as a defensive measure for Phase 2 news (multi-source-per-event possible) and to keep the writer mode-agnostic.
- **§6.3 SKILL.md anti-pattern checklist + is_shortcut emission contract** apply to `earnings-learner/SKILL.md` ONLY. `earnings-prediction/SKILL.md` does NOT need these edits because predictor does not emit canonical drivers.
- **E16 input JSON `source_type` enum** drops `prediction_result` from the Phase-1 producer set. `learner_result` is the sole Phase-1 value; `news` and `fiscal_kpi` come in Phases 2 and 3.
- **Levers #1/#2/#3 all still apply** unchanged — they're producer-agnostic writer logic. Only the *set* of producers shrinks, not the writer/canonicalize/retry machinery.
- **Future-Final.md propagation**: only §8 learner schema migrates (E21 amended); §7 predictor key_drivers[] stays free-form.

---

## §1. Context — why this plan exists

The CombinedPlan locks 25 spec edits + 4 OQ decisions that bring the driver naming system to a **realistic ~87% clean-landing rate** (defined: tag is registered, not split, not malformed, correctly slot-classified) after a few quarters of production. The user explicitly asked: how do we push that closer to 99% — with the smallest changes that preserve system integrity, no runtime human in the loop, no bloat?

A ChatGPT critique (revised after one round of my pushback) proposed 3 specific levers. I independently evaluated them against the spec files + the guidance pipeline production track record (`.claude/plans/Extractions/GuidanceExtractionImplemented.md`, 8,432 live rows). Verdict: **ChatGPT's revised 3 are the right top 3 — better than my earlier synthesis** because (a) they keep `canonicalize()` pure, (b) they add a noise-hardening "promote after repeated evidence" rule I missed, and (c) the retry lever has a verified production analog at `scripts/earnings/earnings_orchestrator.py:1347-1387` (learner H2 informed-retry) that mirrors at ~45-65 LOC.

The plan below is **the three levers plus one critical precondition (E21) plus two small supporting edits**. It also flags one architectural simplification to apply alongside.

---

## §2. The three load-bearing levers

### Lever #1 — Writer-side auto-repair wrapper (NOT inside canonicalize)

**Problem.** LLM emits `opec_supply_cut`. canonicalize() step 7 rejects (state-in-name). Tag is lost. Per audit history, state-smuggle / direction-smuggle / period-token-smuggle is the #1 LLM mistake (~5pp of total loss).

**Design.** A repair wrapper in `driver_writer.py` (NOT inside `driver_ids.canonicalize()` — that stays pure per L3). Called when canonicalize() returns a structured rejection. Tries deterministic single-rule repairs:

```
Rejection                         Auto-repair (only if PROVABLY SAFE)
─────────────────────────────────────────────────────────────────────────
REJECTION_STATE_IN_NAME(t)        IF driver_state is empty
                                  OR driver_state.lower() == t.lower():    ← Fix #9 case-insensitive
                                    strip t from name
                                    set driver_state = t (case-normalized to registry form)
                                    re-run canonicalize on stripped name
                                    │
                                    ├─ if PASS AND repaired name             ← Fix #4 exact-match-only
                                    │    EXACT-MATCHES existing Driver:
                                    │    AND repaired driver_state ∈           ← v4-5 ADDED
                                    │       matched Driver.allowed_states:
                                    │      → write, log :DriverAutoRepair
                                    │        (repair_kind=state_to_driver_state)
                                    │    If V8 fails (state not in allowed):
                                    │      → DEFER to Lever #3 retry
                                    │        (E25 — registry wins; never silently
                                    │         mutate allowed_states)
                                    │
                                    ├─ if PASS but repaired name is NEW       ← Fix #4 route to retry
                                    │    (no registry match — would create
                                    │     a brand-new generic Driver):
                                    │      → DO NOT WRITE.
                                    │        Route tag to Lever #3 retry
                                    │        with rejection_reason=
                                    │        "auto_repair_simplified_but_no_match"
                                    │        so LLM confirms the simplified
                                    │        concept (or proposes a more
                                    │        specific name) before any new
                                    │        Driver lands.
                                    │
                                    └─ if canonicalize FAIL → final reject
                                  ELSE (conflict — driver_state already set
                                        to something different, case-insensitive)
                                    → final reject (never guess)

REJECTION_BANNED_TOKEN(t)         Same exact-match-only rule applies in every branch:
   where t is period/magnitude    IF t is period (q3/fy26/2025/h1):
                                    strip t → re-canonicalize → MUST exact-match
                                    existing Driver to auto-commit; else route to retry.

                                  IF t is magnitude (v3-2 NARROWED):
                                    Match SPECIFIC unit pattern only:
                                      /^\d+(pct|bps|x|percent|basis_points)$/
                                    DO NOT strip bare /^\d/ — that would incorrectly
                                    remove legitimate domain-technology tokens like
                                    5g, 10yr, 3nm, 3d, 4k, 2nm, 18650 (battery cell)
                                    which are objects/themes, not magnitudes.
                                    If matched magnitude → strip → re-canonicalize →
                                    same exact-match-or-retry rule.
                                    If /^\d/ but NOT matched pattern → NO strip;
                                    let new-token gate / classifier handle it.

                                  IF t is identity (ticker/company/person):
                                    final reject (no safe repair path).
                                  ELSE → final reject.

TREND-PARTNER PREFERENCE (v3-3 + v4-16 scope note):
                                  Current ontology recognizes ONLY `_trend` as the
                                  canonical trend-suffix per DriverProcess.html §B2.
                                  If future ontology adds `_growth` / `_momentum` /
                                  `_motion` as additional trend suffixes, this logic
                                  must widen — but that's an ontology rev, not silent
                                  code drift.
                                  When repair would strip a `trend_motion` class
   applies AFTER state-strip       state verb (declined / accelerated / decelerated /
                                   stable / compressed) AND the resulting bare metric
                                   has a `{metric}_trend` partner in registry:
                                     → REWRITE the repair: driver_name = "{metric}_trend",
                                       driver_state = the stripped verb.
                                       Preserves the trend-vs-level semantic distinction
                                       per ontology rules.
                                       e.g., `revenue_decline` →
                                         IF Driver `revenue_trend` exists:
                                           repaired_name = "revenue_trend", state = declined
                                         ELIF Driver `revenue` exists:
                                           repaired_name = "revenue", state = declined
                                         ELSE:
                                           DEFER to Lever #3 retry
                                           (no safe bare-metric collapse)

REJECTION_NO_METRIC_TOKEN         No safe repair (name is missing essential info) → reject

REJECTION_TOO_MANY_SLOTS          No safe repair (usually smuggled state already caught above) → reject
```

**Why outside canonicalize**: canonicalize() must remain a pure function (L3). Repair is a *writer-side decision* about whether a recoverable mistake should land. Mixing them blurs the determinism guarantee.

**Why exact-match-only commit (Fix #4)**: stripping a token like `q3_iphone_sales` → `iphone_sales` is safe ONLY when `iphone_sales` already exists in registry — then the auto-repair is a deterministic reuse, no new concept introduced. If the repaired name is brand-new, we cannot prove the LLM intended a generic-level concept (vs the qualified-period version). Routing such cases to Lever #3 retry asks the LLM to confirm or refine, instead of silently landing a too-broad Driver.

**Audit row** (mirror existing learner audit pattern at `orchestrator.py:2450-2488` with upsert idempotency):

```cypher
(:DriverAutoRepair {
   source_id, run_id,
   item_index,                              ← v9-4 NEW: position of the failing tag
                                              in the input items[] array. Part of
                                              the idempotency UNIQUE key
                                              `(source_id, item_index)` declared
                                              below (per v4-14 + v5-2). Was MISSING
                                              from the property list in v8 even
                                              though the constraint required it —
                                              implementer would have set the
                                              constraint but never populated the
                                              property, causing MERGE to either
                                              fail or silently collapse per-source
                                              repairs into one row. v9-4 cleanup.
   original_name, repaired_name,
   stripped_token,
   repair_kind: "state_to_driver_state"
              | "state_to_trend_partner"   ← v3-3 new: trend_motion verb rewritten
                                            to {metric}_trend Driver
              | "magnitude_strip"          ← only fires on narrowed unit-pattern match
              | "period_strip"
              | "deferred_to_retry",       ← Fix #4: repaired name had no exact match
   cascade_outcome: "PASS"                  ← v3-6 NEW: what happened after the repair's
                  | "REJECTION_NO_METRIC_TOKEN"   re-canonicalize step?
                  | "REJECTION_BANNED_TOKEN"      Lets telemetry distinguish "repair
                  | "REJECTION_TOO_MANY_SLOTS"    succeeded → committed" from
                  | "DEFERRED_TO_RETRY"           "repair attempted → cascaded to a
                  | "FINAL_REJECT_OTHER",         different rejection"
   evidence_refs, repaired_at: $now
})
// Idempotency (Fix #7 + v4-14 + v5-2 confirmed): UNIQUE constraint on
//   (source_id, item_index)
// where item_index is the position of the failing tag in the input items[] array.
// Why item_index over original_name: handles Mode-2 news where one source_id has
// MULTIPLE items with same original_name but different tickers — each item gets
// its own repair audit row. item_index is stable across retries since LLM emits
// items in deterministic bundle-driven order.
// MERGE on (source_id, item_index) — re-runs of same source_id+item_index
// overwrite the prior audit row (last-write-wins on writeback timestamp),
// preventing duplicate audit entries across retries.
```

**Expected recovery**: ~3-4 pp (slightly lower than v1's ~4-5pp estimate because Fix #4 routes some recoverable-but-novel cases through Lever #3 retry instead of auto-committing — recall is unchanged; just split across Lever #1 vs Lever #3).

---

### Lever #2 — Neo4j unified Token-Equivalence Store with promotion gate

**Problem.** SYNONYM_MAP / PLURAL_MAP / ACRONYM_MAP / SHORTCUTS_VOCAB are markdown-seed only. Missing entries cause silent registry splits (`cloud_topline` lands alongside `cloud_revenue`). No runtime growth path. SYNONYM splits are ~5pp of total loss. SHORTCUTS rejections are ~1-2pp more.

**Design.** Extend E10's `:VocabToken` (slot-classification growth) with **one unified equivalence-token store**, gated by a "promotion after repeated evidence" rule to prevent one-off LLM noise from teaching the system false synonyms.

```cypher
// Unified equivalence store (replaces 4 separate maps growing independently)
// v4-1 + v4-6 + v4-7 refined schema:
(:EquivalenceToken {
   equivalence_id,                        ← v4-6 NEW + v5-1 collision-rule:
                                            UNIQUE Neo4j constraint.
                                            Derived: slug("eq:" + kind + ":" +
                                                          from_token)
                                            (deterministic key per (kind, from_token)).
                                            v5-1 RULE: at most one canonical to_token
                                            per (kind, from_token) pair. Conflicting
                                            proposal (different to_token for same key)
                                            → REJECT + :EquivalenceConflictAudit;
                                            does NOT count toward existing promotion.
   kind:       "synonym" | "plural" | "acronym",   ← v5-5: dropped "shortcut".
                                                     Shortcuts land as :Driver rows
                                                     directly (no parallel store).
   from_token, to_token,                 // for synonym/plural/acronym only

   observation_keys: [...],              ← v4-1 RENAMED from source_driver_ids.
                                            APPEND-ONLY-IF-NOT-PRESENT.
                                            observation_count = size(observation_keys).
                                            Each entry is an EVENT-LEVEL key (v4-2):
                                              predictor:AAPL:Q2_FY2026 → "AAPL:Q2_FY2026"
                                              learner:AAPL:Q2_FY2026   → "AAPL:Q2_FY2026"
                                              news:bz-12345            → "news:bz-12345"
                                              fiscal:AAPL:Q2:iphone    → "AAPL:Q2:iphone"
                                            Predictor + learner on same event share the
                                            same observation_key → counted as ONE.
   observation_pit_cutoffs: [...],       ← v4-7 NEW: parallel array; one entry per
                                            observation_key, captures the pit_cutoff
                                            at which that observation occurred.
   provenance_source_driver_ids: [...],  ← v4-1 separate provenance field — actual
                                            Driver.id values that exhibited this
                                            equivalence. Audit-only; NOT used for
                                            promotion counting (avoids the v3 conflation
                                            bug where same-event Driver IDs would
                                            double-count).
   first_seen_at, last_seen_at,
   evidence_refs: [...],
   status: "candidate" | "promoted",
   promoted_at: null | ISO ts,            // AUDIT ONLY (wall-clock). Used for ops/
                                          // telemetry; NEVER for PIT filter.
   equivalence_visible_at: null | ISO ts  ← v4-7 NEW: PIT VISIBILITY ANCHOR.
                                            ON-SET at promotion to
                                            sorted(observation_pit_cutoffs)[N-1]
                                            (i.e., the pit_cutoff of the Nth distinct
                                            observation — the earliest moment promotion
                                            became JUSTIFIED). Historical-run PIT
                                            filter uses THIS, not promoted_at.
                                            Aligns with L6 source-pit-anchored
                                            visibility (mirrors
                                            Driver.registry_visible_at = MIN(DC pit_cutoff)).
})
```

**UNIQUE constraint (v4-6)**:
```cypher
CREATE CONSTRAINT equivalence_id_unique FOR (et:EquivalenceToken)
  REQUIRE et.equivalence_id IS UNIQUE;
```

**Acceptance rule (v4-4 supersedes v3-4 — V1 stays STRICT; v4-3 explicit shortcut path)** — equivalence is only WRITTEN AS CANDIDATE if ALL hold:
- (a) it is a one-token same-slot substitution
   (v9-3 cleanup: dropped trailing "(or whole-name shortcut)" — shortcuts are NOT
    EquivalenceToken candidates per v5-5. They follow acceptance rule (e) below and
    land directly as `:Driver` rows. The registry IS the shortcut store; no parallel
    EquivalenceToken record. The pre-v9-3 wording was leftover residue from v4 that
    contradicted both v5-5 and acceptance rule (e); implementer reading the old (a)
    might attempt to create `:EquivalenceToken{kind:shortcut}` records that the
    v5-5-narrowed `kind` enum `{synonym, plural, acronym}` would reject at runtime.)
- (b) the from-form appears in the supporting evidence text (anti-hallucination, mirrors E10's rule)
- (c) it does not collide with another existing Driver's name/alias **at acceptance time**
- (d) **The proposing Driver passes R11 + V1–V15 using the CURRENT vocab snapshot** — V1 (E6 locked rule: `canonicalize(alias) == parent.name`) **STAYS STRICT and is NEVER relaxed**. **v6-5 refined alias-routing decision**: for EACH proposed alias in `propose_new_drivers[i].aliases[]`, the writer computes `canonicalize(alias, current_vocab_snapshot)`:
    - **STRICT-alias path**: IF `result == parent.name` (V1 passes — alias resolves to parent purely via slot-reorder OR via already-promoted equivalences in the current snapshot, e.g., word-order variant `china_iphone_sales` → `iphone_china_sales` via step-10 reorder; or `cloud_topline` → `cloud_revenue` when `topline → revenue` is already PROMOTED in the snapshot): **APPEND to `Driver.aliases[]` at registration**. V1 is satisfied by construction. Future emissions hit B4 (exact alias match) fast-path with O(1) lookup.
    - **NON-STRICT candidate-equivalence path**: IF `result != parent.name` (V1 would fail — alias requires a NEW transform not yet in vocab, e.g., `cloud_topline` when `topline → revenue` is NOT yet anywhere): **route to `:EquivalenceToken` as candidate**, with `kind` inferred from the required transform (synonym / plural / acronym — the writer detects which map fold would be needed). NOT added to `Driver.aliases[]`. The proposing Driver still passes V1 strictly (Driver.aliases[] contains only the STRICT-path aliases). If/when the candidate equivalence promotes, future emissions fold via canonicalize step 5 → B6 hits registry → reuse correctly (no Driver.aliases[] mutation needed post-promotion).
    - **v5-6 still holds**: NO post-promotion alias-sync orchestrator step. The two paths above split routing AT REGISTRATION based on V1-pass-now-or-not; nothing rewrites `Driver.aliases[]` later.
    - **Why this matters (vs v5's all-aliases-go-to-EquivalenceToken)**: routing strict aliases to `Driver.aliases[]` preserves B4 fast-path lookup (small performance win) AND keeps the documented Driver.aliases[] semantics intact (a Driver authored with `aliases: ["china_iphone_sales"]` actually has that alias on Day 0, not pending some unrelated promotion). v5-6 over-corrected by routing ALL aliases to EquivalenceToken; v6-5 restores correct routing per alias's V1-pass status.
- (e) `is_shortcut=true` proposals (v5-5 + v7-2 tightened gate):
    1. `propose_new_drivers[i].is_shortcut = true` MUST be set
    2. Proposal MUST have zero slot-classifying tokens (genuinely standalone phrase)
    3. **NEW (v7-2): Proposal name MUST have ≥2 underscore-separated tokens** — e.g., `chip_shortage` (2 tokens) and `fda_approval` (2 tokens) and `yield_curve` (2 tokens) all pass; single-word LLM hallucinations like `winter`, `crash`, `disaster`, `armageddon` are REJECTED at this gate. Mechanical, deterministic, no curated list. Rationale: every canonical financial-domain shortcut we've identified (yield_curve, fda_approval, opec_supply, chip_shortage, share_buyback, etc.) is multi-token; single-word "shortcuts" are almost always LLM-hallucinated metaphors that pollute registry without retrieval value
    4. Writer follows a SPECIAL CANONICALIZE PATH for shortcut proposals: shape regex + banned-content check + zero-slot-confirmation + ≥2-token confirmation (v7-2) + R11 evidence requirement; slot grammar (steps 9-11) is bypassed
    5. **Driver lands immediately** on R11 pass as a normal `:Driver` row with the new OPTIONAL `is_shortcut: bool` property set (e.g., `:Driver{name:"chip_shortage", is_shortcut:true}`). The `is_shortcut: bool DEFAULT false` field must be declared in Neo4jXBRLDesign.md §C3.1 Driver OPTIONAL block (v8-1; added to §6.1 edit list). Rationale: declarative discriminator so canonicalize step 8 (standalone-shortcut early-return) can identify shortcut Drivers via a clean query instead of reverse-validating against §F.1 slot vocabs. NO parallel `:EquivalenceToken` record is created for shortcuts (v5-5 drops `kind:shortcut`). The registry itself IS the shortcut store.
    6. Future emissions of the shortcut form hit `Driver.name` via B3 (exact-match name lookup) directly — no canonicalize needed, no EquivalenceToken lookup needed
    7. The `is_shortcut: bool` flag MUST be added to E16's input JSON contract and taught in `earnings-learner/SKILL.md` (per v3-5 + E30: learner is sole producer)
    8. **Integrity trade-off acknowledged (v7-2 explicit)**: this design CHOOSES RECALL over N=2 promotion for shortcuts. We rejected the bot suggestion of "require N=2 for shortcuts" because it would deadlock: a real new shortcut's first emission would have no Driver yet (not promoted, candidate-only), so the LLM at the next event would see no anchor in the catalog and emit the same shortcut form again — still no Driver, still no promotion, infinite loop. The current gate (R11 + shape + banned + zero-slot + ≥2-token + evidence) is the production trade-off. One-off LLM mistake-shortcuts that pass these gates land permanently and clutter the registry; cleanup is code-time (deprecate via `deprecated_at + replaced_by` per Neo4jXBRLDesign §C3.1). This is a DOCUMENTED, ACCEPTED known limitation — not "perfect integrity" but the best recall/integrity balance available given the deadlock constraint. If post-launch audit data shows shortcut pollution growing faster than ~5 entries/quarter, an engineer can tighten the gate further code-time (e.g., add a banned-shortcut-token allowlist, or shortcut name pattern allowlist) without re-architecting

**Backward-compat (v3-7)** — when a candidate promotes to `status="promoted"`, the change applies to FUTURE canonicalize() calls only. Pre-existing Driver rows registered under split spellings (e.g., legacy `cloud_topline` and `cloud_revenue` both existing in registry before `topline → revenue` was promoted) stay AS-IS. `Driver.name` is IMMUTABLE per `DriverProcess.html` §C3.1 — promotion does NOT retroactively merge legacy splits. Post-promotion behavior:
- new B3/B4 lookups for `cloud_topline` will fold via promoted equivalence and hit `cloud_revenue` → reuse correctly going forward
- legacy `cloud_topline` Driver row remains queryable for historical DriverChanges that reference it
- **v5-7 (drops the migration suggestion entirely)**: pre-promotion legacy splits stay as an **audit-only known limitation**. The plan does NOT specify a retroactive merge / deprecation mechanism for legacy split Drivers. Reasoning: any deprecation pattern (e.g., `deprecated_at + replaced_by` from Neo4jXBRLDesign §C3.1 OPTIONAL block) would leave reader behavior undefined (which lookups respect `deprecated_at`? B3? bundle renderer? canonicalize?) — and prescribing those rules expands spec surface without runtime gain. If post-launch the audit `:DriverDriftAudit` shows accumulated splits become a problem, an engineer can write a one-time targeted Cypher migration tailored to the specific deprecation semantics needed at that moment. For now: ship, observe, iterate

**Promotion rule (v4-2 + v4-6 + v4-7 + v5-1 + v5-4 — refactored to compute-before-SET)** — equivalence is promoted to `status="promoted"` once `size(observation_keys) >= EQUIV_PROMOTE_N` where **N=2 is a hardcoded Python constant** in `driver_writer.py` (NOT runtime-env-tunable per L4 + v3-14). `observation_keys` is **append-only-if-not-present**, derived from EVENT-level keys (v4-2 strips producer prefix; with E30 in effect, only one Phase-1 producer exists so this is defensive for Phase 2/3).

**v5-1 collision rule for `(kind, from_token)`**: BEFORE executing the MERGE/SET below, Python must verify: if an EquivalenceToken already exists with the same `equivalence_id` (i.e., same `(kind, from_token)` pair) AND its `to_token` differs from the proposed `to_token` → REJECT the new proposal, write `:EquivalenceConflictAudit{equivalence_id, existing_to, proposed_to, source_id, item_index, rejected_at}`, do NOT increment observation_keys for the existing entry. This guarantees one canonical mapping per source token.

**v5-4 + v6-2 two-phase pattern**: pre-compute `new_obs_keys`, `new_pit_cutoffs`, `new_count`, `would_promote` in a WITH clause BEFORE any SET; run the v4-6 collision recheck (against the registry, not the equivalence itself) in PYTHON between two Cypher queries; flip status in a SECOND Cypher query if Python allows. Why: a single Cypher statement is atomic on Neo4j — Python CANNOT interrupt it midstream to make a decision. The original v5-4 spec wrongly implied "Python checks between WITH and SET in the same query"; v6-2 corrects this to a genuine two-phase flow:

```cypher
// v4-2: observation_key derivation BEFORE the MERGE (in writer Python):
//   prediction_result:  "predictor:AAPL:Q2_FY2026" → "AAPL:Q2_FY2026"
//   learner_result:     "learner:AAPL:Q2_FY2026"   → "AAPL:Q2_FY2026"
//   news:               "news:bz-12345"            → "news:bz-12345"  (no strip)
//   fiscal_kpi:         "fiscal:AAPL:Q2:kpi"        → "AAPL:Q2:kpi"
//
// $obs_key, $obs_pit_cutoff, $driver_id passed in.

// v6-2 PHASE 0 (Python pre-check): query existing EquivalenceToken (if any) by
// equivalence_id. IF exists AND existing.to_token != $to:
//   → REJECT proposal (v5-1 collision), write :EquivalenceConflictAudit, RETURN
//   (do not even reach the MERGE below)

// v6-2 PHASE 1 (Cypher query #1): MERGE + update observation arrays + RETURN
// would_promote. NO status change yet.
MERGE (et:EquivalenceToken {equivalence_id: $equivalence_id})
  ON CREATE SET
    et.kind = $kind, et.from_token = $from, et.to_token = $to,
    et.observation_keys = [$obs_key],
    et.observation_pit_cutoffs = [$obs_pit_cutoff],
    et.provenance_source_driver_ids = [$driver_id],
    et.first_seen_at = $now, et.last_seen_at = $now,
    et.evidence_refs = $evidence_refs,
    et.status = "candidate", et.promoted_at = null,
    et.equivalence_visible_at = null

// v9-2 INTRA-MERGE CONFLICT GUARD: race protection for concurrent writers.
// Phase 0 (Python pre-check) catches sequential conflicts BEFORE Cypher runs.
// But two concurrent writers can both pass Phase 0 (each saw no existing node)
// and only ON CREATE-vs-ON MATCH ordering inside this MERGE decides which
// to_token wins. The loser's MERGE matches the winner's freshly-created node
// (ON MATCH path runs) — and without this guard, the loser's SET below would
// silently append its observation_key to the winner's to_token row.
// Guard: filter out the row if et.to_token != $to. SET below skipped, RETURN
// returns zero rows. Python detects empty RETURN and writes
// :EquivalenceConflictAudit (same audit node as Phase 0 conflict detection).
// All of this is atomic within the MERGE transaction — no race window remains.
WITH et
WHERE et.to_token = $to

WITH et,
     // Compute new arrays from CURRENT (pre-update) state plus this observation:
     CASE WHEN $obs_key IN et.observation_keys
          THEN et.observation_keys
          ELSE et.observation_keys + $obs_key END             AS new_obs_keys,
     CASE WHEN $obs_key IN et.observation_keys
          THEN et.observation_pit_cutoffs
          ELSE et.observation_pit_cutoffs + $obs_pit_cutoff END AS new_pit_cutoffs,
     CASE WHEN $driver_id IN et.provenance_source_driver_ids
          THEN et.provenance_source_driver_ids
          ELSE et.provenance_source_driver_ids + $driver_id END  AS new_provenance
SET et.observation_keys = new_obs_keys,
    et.observation_pit_cutoffs = new_pit_cutoffs,
    et.provenance_source_driver_ids = new_provenance,
    et.last_seen_at = $now,
    // v10-2 BACKDATE: when already-promoted and a new observation lowers
    // the sort(observation_pit_cutoffs)[N-1] anchor (out-of-order or
    // backfill PIT arrival), backdate equivalence_visible_at. Mirrors the
    // Driver.registry_visible_at MIN-backdate L6 pattern. For NOT-yet-promoted
    // candidates (status="candidate" still), Phase 3 sets visible_at on first
    // promotion — this CASE is a no-op (visible_at stays NULL until Phase 3).
    // Closes the under-visibility scenario where E30 chronological-order
    // assumption was unstated/unenforced (Bot A finding 2; reverses prior
    // X3 deferral).
    et.equivalence_visible_at = CASE
      WHEN et.status = "promoted"
           AND et.equivalence_visible_at IS NOT NULL
           AND apoc.coll.sort(new_pit_cutoffs)[$EQUIV_PROMOTE_N - 1]
               < et.equivalence_visible_at
      THEN apoc.coll.sort(new_pit_cutoffs)[$EQUIV_PROMOTE_N - 1]
      ELSE et.equivalence_visible_at
    END
RETURN et.equivalence_id  AS eq_id,
       et.kind             AS kind,
       et.from_token       AS from_token,
       et.to_token         AS to_token,
       (size(new_obs_keys) >= $EQUIV_PROMOTE_N
        AND et.status = "candidate")  AS would_promote,
       new_pit_cutoffs                AS pit_cutoffs

// v6-2 PHASE 2 (PYTHON, between Cypher queries):
//   IF Phase 1 RETURNED ZERO ROWS (v9-2 conflict path — guard filtered):
//     This is the concurrent-conflict case caught by v9-2's WHERE clause.
//     Re-query the existing to_token via a separate single-property read.
//     Write :EquivalenceConflictAudit{equivalence_id, existing_to=<queried>,
//       proposed_to=$to, source_id, item_index, rejected_at}.
//     Same audit node as the Phase 0 (Python pre-check) conflict path.
//     Done. No promotion path; observation NOT counted.
//   IF would_promote == false:
//     done. status stays "candidate", observation_keys accumulated, no promotion.
//   ELSE (would_promote == true):
//     Run COLLISION RECHECK against current Driver registry state:
//       allow_promote = NOT registry_collision_exists(kind, from_token, to_token)
//     (e.g., check if any :Driver exists whose name would now be folded by this
//      equivalence into a DIFFERENT existing Driver — that would be a collision)
//     IF allow_promote == true: proceed to PHASE 3.
//     ELSE: write :EquivalenceCollisionAudit{eq_id, conflict_driver_id, $now};
//           status STAYS "candidate"; PHASE 3 skipped this round.

// v6-2 PHASE 3 (Cypher query #2, conditional on Python allow_promote=true):
MATCH (et:EquivalenceToken {equivalence_id: $eq_id})
WHERE et.status = "candidate"
SET et.status = "promoted",
    et.promoted_at = $now,
    et.equivalence_visible_at = apoc.coll.sort($pit_cutoffs)[$EQUIV_PROMOTE_N - 1]
RETURN et.equivalence_id, et.status, et.equivalence_visible_at
```

**Collision recheck at promotion (v4-6)**: When `status` transitions candidate → promoted (i.e., the Nth observation arrives), the writer MUST re-run the acceptance-rule (c) collision check against CURRENT registry state — registry may have changed between candidate creation (e.g., Q1) and promotion (e.g., Q3): a new Driver may have landed that conflicts. If collision detected at promotion: equivalence STAYS candidate (do not promote), audit-log the collision to `:EquivalenceCollisionAudit`. Engineer reviews code-time.

This guarantees N=2 means **two distinct EVENT-level observations agreed**, not "same event counted twice from different producers" and not "same source retry counted twice." Without v4-2 dedup the promotion gate would be artificially fast-passed by predictor+learner same-event emissions.

**Read path (v3-1 purity + Fix #1 PIT + Fix #2 hide candidates)** — canonicalize() does NOT read Neo4j directly. Instead:

```
WRITER bootstrap (once per run, BEFORE any canonicalize() call):
  1. seed_maps = load_markdown_seed()       # static, from §F.1-F.8 banks
  2. promoted_equivalences = neo4j.query("""
        MATCH (et:EquivalenceToken)
        WHERE et.status = "promoted"
          AND ($run_pit_cutoff IS NULL
               OR et.equivalence_visible_at <= datetime($run_pit_cutoff))
                  // ↑ v4-7: PIT filter uses observation_pit anchor,
                  //   NOT wall-clock promoted_at. Aligns with L6.
        RETURN et.kind, et.from_token, et.to_token
                  // ↑ v5-5: no et.phrase field — kind:shortcut dropped;
                  //   shortcuts live as :Driver rows, not in this query.
     """)
  3. promoted_vocab_tokens = neo4j.query("""                  // ← v9-1 NEW (X1)
        MATCH (vt:VocabToken)
        WHERE ($run_pit_cutoff IS NULL
               OR vt.vocab_visible_at <= datetime($run_pit_cutoff))
                  // ↑ v9-1: PIT filter parallel to v4-7 for EquivalenceToken.
                  //   Closes L6 leak that was silently present in v8 — the
                  //   slot-vocab merge below used to load VocabToken rows
                  //   UNFILTERED, so historical backfills could see
                  //   future-coined tokens (e.g., a 2020-PIT backfill
                  //   loading a `hyperscaler` token created at 2024-Q3).
                  //   vocab_visible_at is set at VocabToken write time to
                  //   the source_driver.registry_visible_at (= MIN of that
                  //   Driver's DC pit_cutoffs at write time). v10-1: ON
                  //   MATCH (token already exists from earlier write) the
                  //   field BACKDATES via MIN(existing, new $source_pit) —
                  //   same pattern as Driver.registry_visible_at L6 rule.
                  //   So if a later backfill creates a Driver with earlier
                  //   PIT that uses an already-known token, the VocabToken
                  //   row's vocab_visible_at correctly backdates to the
                  //   earliest source PIT. Closes the L6 inconsistency v9-1
                  //   left open (Bot A finding 1.1 + finding 2 reversal of
                  //   X3 deferral). NO out-of-order under-visibility remains.
        RETURN vt.slot, vt.token
     """)
  4. vocab_snapshot = VocabSnapshot(           # immutable, frozen dict
        synonym_map  = merge(seed_maps.synonym, promoted_equivalences.synonyms),
        plural_map   = merge(seed_maps.plural,  promoted_equivalences.plurals),
        acronym_map  = merge(seed_maps.acronym, promoted_equivalences.acronyms),
        // v5-5: no `shortcuts` entry in EquivalenceToken anymore.
        // Shortcut canonical phrases are :Driver.name rows themselves;
        // canonicalize step 8 (standalone-shortcut early-return) reads
        // them from the seed-maps + the live Driver registry via a separate
        // lookup, NOT from EquivalenceToken.
        slot_vocabs  = merge(seed_maps.slots,   promoted_vocab_tokens),  # E10 + v9-1 PIT-filtered
        ... etc
     )

CANONICALIZE (pure function, NO DB reads):
  def canonicalize(candidate: str, vocab: VocabSnapshot) -> str | REJECTION:
      # all the 12 steps use vocab.* dicts, never touch Neo4j
      n = vocab.acronym_map.get(t, t)
      n = vocab.plural_map.get(n, n)
      n = vocab.synonym_map.get(n, n)
      ...
```

This restores L3 purity in full: **same `(candidate, vocab)` → same output, always, on any machine.** No "time-of-day" non-determinism from Neo4j drift. Writer is responsible for snapshot loading + PIT filtering; canonicalize is responsible for folding.

Bundle renderer renders ONLY these PIT-filtered promoted entries into the LLM-visible vocab block.

**Candidate entries are NEVER shown to the LLM** (neither in the catalog block nor in any "pending equivalences" appendix). They live exclusively in the audit / telemetry layer until promoted. Rationale: showing candidates to the LLM creates a feedback loop where the LLM that proposed candidate X at Q1 reinforces it at Q2 (same prompt-pattern, same training distribution) — fast-passing the promotion gate without genuine independent evidence. The gate's whole purpose is "trust only after N independent observations"; surfacing candidates to the LLM defeats that purpose.

**Why one unified store, not three separate labels**: simpler graph schema (one label, kind discriminator) + one bundle render path + one growth/audit pipeline. The three "kinds" (synonym / plural / acronym — kind:shortcut dropped per v5-5) share 100% of the acceptance/promotion mechanics; splitting into 3 separate labels would be pure code duplication. Shortcut growth lives separately as direct `:Driver` row creation (v5-5).

**Expected recovery**: ~5-7 pp combined — split as (a) synonym/plural/acronym splits prevented via `:EquivalenceToken` promotion (this lever), and (b) shortcut self-bootstrap via direct `:Driver` registration (the `is_shortcut=true` path in acceptance rule (e) — landing immediately on R11 evidence pass, no EquivalenceToken involved per v5-5). This is the **architectural completeness lever** — post this change, the only code-time-editable banks in the entire design are STATES_VOCAB §F.5 (7 stable classes) and BANNED_CONTENT hand-lists (bounded English vocab). True "no human in loop ever" reaches its design limit.

---

### Lever #3 — Driver-only informed retry (mirror existing learner pattern verbatim)

**Problem.** Even after Levers #1 and #2, ~3-4pp of failures remain: V10 evidence-catalog miss, V8 allowed_states mismatch, V11 unresolved driver_name (LLM referenced a name not in registry AND not in propose_new_drivers), R11 gate failures with fixable companion fields, slot_anchor_unavailable where one rephrasing would fix it.

**Design.** Mirror the H2 informed-retry pattern already in production at `scripts/earnings/earnings_orchestrator.py:1347-1387`. Verified by Explore agent — pattern is 45-65 LOC to mirror, including outcome enum.

**Relationship to E20 (v4-13)** — E20 (as amended by E30) locks "Phase 1 producer (learner only) emits drivers inside its own LLM session. NO second extraction LLM pass." Lever #3's informed retry is a RE-EMISSION OF THE SAME LEARNER SESSION (same producer LLM, same bundle, same source_id, same TMUX transport per Final.md §5). It is NOT a second extraction LLM pass on top of the producer — that is what E20 prohibits (a separate `/extract` pipeline call). Within-session H2 informed retry is the production-validated pattern at `orch.py:1347-1387` for learner; Lever #3 mirrors that exact pattern for driver writes. No E20 conflict.

```
learner writes result.json  (per E30: learner is sole Phase-1 producer)
       │
       ▼
orchestrator validates result.json + runs driver_write_cli --dry-run
       │
   ┌───┴────┐
 PASS     FAIL with per-driver rejection_reasons
   │        │
   │        ▼
   │   Build "--- YOUR PRIOR DRIVER OUTPUT WAS REJECTED ---" block
   │   (verbatim format from orch.py:3118-3165) — numbered reasons,
   │   instruction (Phase 1 learner-only per E30 + v7-1):
   │     "Fix these EXACT errors and re-emit ONLY the
   │      primary_driver / contributing_factors[] /
   │      propose_new_drivers[] fields. Do not change other fields."
   │   (Phase 2+ news producer would substitute `items[]` for
   │    primary_driver/contributing_factors per the producer-specific
   │    schema; orchestrator dispatches the right template at retry
   │    time. Phase 3 fiscal.ai has no LLM, so no retry path.)
   │        │
   │        ▼
   │   ONE retry via existing TMUX transport (per Final.md §5)        ← Fix #5
   │   (NOT SDK — `claude -p` / `claude_agent_sdk.query` are
   │    forbidden target paths per Final.md §5; transport is
   │    interactive TMUX with OAuth credentials)
   │        │
   │        ▼
   │   driver_write_cli --dry-run AGAIN
   │        │
   │     ┌──┴─────┐
   │   PASS     STILL FAIL
   │     │        │
   │     │        ▼
   │     │   Per-driver FINAL reject → :DriverProposalRejection
   │     ▼        audit row + run continues per PARTIAL policy (E1)
   │   WRITE
   ▼
WRITE
```

**Outcome enum** mirrors `LearnerOutcome` (orch.py:1066-1106):
- `SUCCEEDED` (first attempt OR retry)
- `SUCCEEDED_AFTER_RETRY` (telemetry-useful distinction)
- `FAILED_VALIDATION_RETRY` (both attempts failed legitimate driver validation)
- `FAILED_DRIFT_GUARD` (v3-9 + v4-8: retry mutated LLM-authored non-driver fields; whole retry discarded)
- `FAILED_SCOPE_CREEP` (v3-8 NEW: retry added propose_new_drivers entries outside the
   legitimate recovery carve-out; whole retry discarded)
- `FAILED_RETRY_SHAPE_VIOLATION` (v4-9 NEW: retry violated array length/order preservation)
- `FAILED_SYSTEM` (writer/Neo4j infrastructure)

**What's reused verbatim from the learner pattern**:
- Rejection block markdown shape
- One-attempt cap (no recursive retries)
- `prior_validation_errors` → renamed `prior_driver_rejection_reasons`
- Outcome enum structure
- Audit upsert pattern (orch.py:2473-2488)

**What's NEW (driver-specific)**:
- Per-driver granularity (PARTIAL policy: 4 rejected of 5 drivers → retry only those 4)
- Driver-field constraint in prompt ("change ONLY driver fields, not analysis/thesis/falsifier")

**Merge logic on retry response (Fix #8 + v3-8 surgical-replace + v3-9 drift guard)** — the retry returns a FULL `result.json` from the LLM (it cannot return partial fields — the TMUX harness emits the whole file). Orchestrator applies a strict 3-stage merge:

```
STAGE 1 — DRIFT GUARD (v3-9 hard-reject + v4-8 INVERSION-based whitelist):

  DRIVER_FIELDS (per v7-1 — producer-specific dispatch):
    Phase 1 (learner only per E30):
      DRIVER_FIELDS = {
        "primary_driver",                  (learner)
        "contributing_factors",            (learner)
        "propose_new_drivers"
      }
    Phase 2 (news producer, when activated):
      DRIVER_FIELDS = {
        "items",                           (news per-row tags)
        "propose_new_drivers"
      }
    Phase 3 (fiscal.ai direct ingest): no LLM, no retry, no drift guard.

  (v7-1 removed "key_drivers" from DRIVER_FIELDS. Per E30, key_drivers[] is
   predictor's free-form analysis prose per Final.md §7 — predictor is
   consumer-only and never emits canonical drivers, so key_drivers never
   appears in a writer-retry context.)

  ORCHESTRATOR_STAMPED = {               ← v4-8: Python-owned, NOT LLM-authored;
    "schema_version", "ticker",             excluded from drift diff so R2
    "quarter_label", "predicted_at",         echoes don't trigger false reject
    "attributed_at", "model_version",
    "sdk_session_id", "pit_mode",
    "pit_cutoff", "pit_boundary_source",
    "pit_boundary_event",
    "prediction_delay_sec",
    "confidence_bucket", "magnitude_bucket",
    "actual_return_pct",
    "context_bundle_ref",
    "prediction_result_ref"
  }

  LLM_AUTHORED_NON_DRIVER =
    set(r1.keys() ∪ r2.keys()) - DRIVER_FIELDS - ORCHESTRATOR_STAMPED

  Diff R1 vs R2 across LLM_AUTHORED_NON_DRIVER only:
    e.g., analysis, thesis, falsifier, evidence_ledger[],
          data_gaps[], opened_prior_reports[], feedback{},
          key_takeaway, future_checklist[], missing_inputs[],
          data_sources_used[], + ANY future LLM-authored field
          (the whitelist is future-proof: new fields default-INCLUDE
           in the drift check until explicitly added to one of the
           two whitelisted sets above)

  IF ANY LLM_AUTHORED_NON_DRIVER field differs (whitespace-normalized):
    → MARK RETRY = FAILED_DRIFT_GUARD
    → ALL R1 rejected drivers stay rejected → :DriverProposalRejection
    → Log field-diff to :DriverDriftAudit for observability
    → DO NOT apply ANY of R2's changes; R1's non-driver fields stand
  Rationale: LLM that can't follow "only change driver fields" instruction
  is exhibiting misbehavior signal; we fail closed rather than silently
  cherry-pick. Inversion-based formulation protects against future
  result.json schema additions silently default-passing the guard.

STAGE 2 — SURGICAL REPLACE BY TAG (v3-8 + v4-9 array-order constraint):

  ARRAY-ORDER PRECONDITION (v4-9 + v5-9 tuple-equality + v7-1 learner-scope):
    Phase 1 (learner only per E30):
      R2.contributing_factors.length == R1.contributing_factors.length AND order preserved
      (primary_driver is single, no array concern)
    (v7-1: dropped `R2.key_drivers.length` check — key_drivers is the
     predictor field per Final.md §7; predictor doesn't emit drivers per E30,
     so this learner-retry path never sees key_drivers.)
    Phase 2 (news, when activated):
      R2.items.length == R1.items.length AND order preserved.

    For PASSED-in-R1 indices (per STAGE 2 below):
      R2[i] tuple MUST be IDENTICAL to R1[i] tuple:
        (driver_name, driver_state, direction, evidence) field-by-field equal.
      For FAILED-in-R1 indices: R2[i] tuple MAY differ — that's the whole point of retry.

    If violated → MARK RETRY = FAILED_RETRY_SHAPE_VIOLATION;
                  ALL R1 rejected drivers stay rejected; halt merge.

  PASSED-in-R1 tags     → KEEP R1's version VERBATIM
                          (retry must NOT mutate already-good drivers;
                           any R2 change to these is discarded)
  FAILED-in-R1 tags     → REPLACE with R2's version at the SAME index
                          (per-driver granular; not all-or-nothing)
                          Subject to STAGE 3 propose_new_drivers gate.

  ORPHANED R1 PROPOSALS DROP (v4-15):
    After surgical-replace, scan R1.propose_new_drivers[]:
    For each R1 entry NOT referenced by any tag in merged result:
      → DROP it from merged.propose_new_drivers[]
    (Without this, V13 proposal_without_use would reject the merge.
     Example (Phase 1 learner per E30 + v7-1 + v10-6):
       R1 had contributing_factors[1]={name:"foo"} + propose_new_drivers
       entry "foo". R2 replaces [1] with name="bar"; "foo" proposal is
       now orphaned. Drop to keep V13 happy.
     Future Mode-2 news producer would use items[1] in place of
     contributing_factors[1] — same algorithm, different field name.)

STAGE 3 — PROPOSE_NEW_DRIVERS GATE (v3-8 + v5-11 same-name replacement):
  Categorize R2.propose_new_drivers entries vs R1.propose_new_drivers:

  CASE A — SAME-NAME REPLACEMENT (v5-11 NEW):
    R2 entry has same `name` as a R1 entry that FAILED any of V1-V15 in R1.
    → ACCEPT the replacement; treat as a fresh proposal of that same name
      with corrected companion fields. Re-run R11 + V1-V15 on the replacement.
    Rationale: this is the legitimate recovery path for proposal-level failures
    (e.g., R1 proposal failed V6 invalid_allowed_states; R2 sends corrected
    allowed_states for the same name). Without this, retry can't fix bad
    R1 proposals — Bot 3 #1 gap.

  CASE B — NEW NAME via UNRESOLVED carve-out:
    R2 entry has a name NOT in R1.propose_new_drivers, AND that name is
    referenced by a STAGE-2-replaced tag whose R1 rejection_reason was
    "unresolved_driver_name".
    → ACCEPT (one legitimate recovery path for V11 rejection).
    → Run R11 + V1-V15 as fresh proposal.

  CASE C — NEW NAME with NO unresolved carve-out:
    R2 entry has a name NOT in R1.propose_new_drivers, AND no STAGE-2-replaced
    tag references it.
    → REJECT this propose_new_drivers entry as SCOPE_CREEP.
    → If any STAGE-2-replaced tag depends on this rejected entry, that tag
      stays rejected.

  Rationale: retry exists to FIX rejected tags + their broken proposals,
  not EXPAND the emission scope. CASE A (same-name fix) and CASE B
  (unresolved-name carve-out) cover the legitimate recovery patterns.
  CASE C is scope creep — blocked.

FINAL MERGED RESULT_JSON =
   - R1's non-driver fields verbatim (STAGE 1 guarantee)
   - Per-tag: R1 if PASSED, R2 if REPLACED (STAGE 2)
   - propose_new_drivers (v6-1 corrected merge formula — subtracts replaced + orphaned):
       Start with R1.propose_new_drivers
       MINUS  {R1 entries whose `name` was REPLACED by an accepted STAGE-3 CASE A entry}
       MINUS  {R1 entries that became orphaned (no tag references them) per v4-15}
       PLUS   {STAGE-3 CASE A accepted same-name replacements (the corrected versions)}
       PLUS   {STAGE-3 CASE B accepted new entries (unresolved-name carve-out)}
       (CASE C entries were rejected upstream as SCOPE_CREEP; never enter merge)
       Net result: no double-listing of names; broken R1 proposals are removed when replaced; V13 (proposal_without_use) won't fire on orphans.
```

This 3-stage merge enforces the "change only driver fields" constraint **structurally** AND **strictly**. Belt + suspenders + structural lockout.

**Why one retry, not N**: learner pattern caps at 1 retry. Production-validated. More retries = more LLM tokens + more drift risk + diminishing returns. Single retry is the production-proven sweet spot.

**Expected recovery**: ~3-4 pp (tail cases not covered by deterministic auto-repair or token store) + ~1-2pp absorbed from Lever #1's deferred cases (Fix #4 routes brand-new repaired names here instead of auto-committing).

---

### Cumulative gain PROJECTION (v3-12 — pending Q1 measurement)

> ⚠ **These are projections, not measurements.** They are derived from (a) the guidance pipeline's production track record (~80% useful resolution on 8,432 rows), (b) estimated LLM failure rates per audit history (state-smuggle ~5pp, synonym splits ~5pp, slot ambiguity ~2-3pp, evidence misses ~2-3pp), and (c) the qualitative effect of each lever on those failure modes. **They will be validated against actual cohort data after Q1 ships and revised based on telemetry from `:DriverAutoRepair` + `:DriverProposalRejection` + `:EquivalenceToken` audit tables.** The numbers below should be treated as planning estimates, not commitments.

```
PROJECTION (pending Q1 measurement):

Baseline (CombinedPlan v8, all 25 E* applied)                      ~87%
+ Lever #1 (writer-side auto-repair, v3-2 + v3-3 + v4-5 + v5-9)   ~90-91%
+ Lever #2 (unified Neo4j Token store + promotion gate;
   v3-1 + v4-4 [supersedes v3-4] + v3-5 + v4-6 + v4-7
   + v5-1 + v5-4 + v5-5 + v5-6 + v6-2 + v6-4 + v6-5 + v8-1
   + v9-1 [VocabToken PIT-filter, closes L6 leak parallel to v4-7]
   + v9-2 [intra-MERGE to_token conflict guard, concurrent-writer race]
   + v10-1 [VocabToken MIN-backdate on MATCH, L6 alignment with Driver]
   + v10-2 [EquivalenceToken visible_at MIN-backdate on each obs,
            reverses prior X3 deferral, closes L6 inconsistency])  ~95-96%
+ Lever #3 (driver-only informed retry; v3-8 + v3-9
   + v4-8 + v4-9 + v5-11 + v6-1 + v7-1)                            ~97-98%
─────────────────────────────────────────────────────────────────
Honest projection after 8Q                                         ~96-98%
                                                                   (±2-3pp error bar)
```

I will not project 99%. Last 1-2pp lives in genuine tail cases (rare slot ambiguity with no positional anchor, hallucinated evidence with no salvage path, novel concepts whose tokens never recur and never get promoted) that don't have clean repair patterns even with LLM help.

**v4-19 — Cumulative gain math note (transparency)**: standalone gains sum to ~12-17pp (~4pp Lever #1 + ~5-7pp Lever #2 + ~3-4pp Lever #3) but the cumulative table shows only ~10pp net (~87% → ~97%). The difference is OVERLAPPING RECOVERIES — many failures are catchable by more than one lever (e.g., a state-smuggle case that Lever #1's deterministic auto-repair commits would otherwise have been caught by Lever #3's LLM retry; counting both as +X pp double-counts the recovery). The cumulative number is the net delta with overlaps removed.

**First real cohort data (Q1 production) will tell us how close these numbers actually are.** Audit tables capture per-lever hit rates, so we can recompute the breakdown empirically by Q2.

---

## §3. Required precondition (NOT a lever — a blocker)

> **v5-8 cross-ref**: For the relationship between Lever #3's informed retry and E20's "no second extraction LLM pass" rule, see §2 Lever #3 head paragraph (v4-13 reconciliation). TL;DR: H2 informed retry within the same producer session ≠ a separate /extract pass, so no E20 conflict.

**E21 (CombinedPlan, as amended by E30) must land FIRST — §8 ONLY (v6-3).**

Per E30, predictor is consumer-only — `Final.md` §7 `key_drivers[]` stays free-form by design and does NOT contradict the driver ontology (it lives in a separate semantic universe: predictor's analysis prose, not canonical drivers).

The actual blocker is `Final.md` §8 — `learner_result.v1` `primary_driver / contributing_factors[i]`. The current §8 schema must migrate from `{driver / factor, evidence}` to `{driver_name, driver_state, direction, evidence}` so the learner SKILL.md emits ontology-compliant tags that the writer can validate. Until E21 lands this §8 migration, the learner SKILL.md updates (§4.1 anti-pattern checklist + is_shortcut emission contract) fight Final.md and Lever #1-#3 sit on contradictory foundations for the only producer (learner).

This is **not optional**. It is the precondition all three levers depend on. §7 is NOT in scope of this precondition.

---

## §4. Supporting edits (small, high-value, NOT in top 3)

### §4.1 SKILL.md anti-pattern checklist (~30 lines, learner skill only — per E30)

Zero code. Pure SKILL.md edit to **`earnings-learner/SKILL.md` only** (per E30 / §1.0 Producer Scope — predictor doesn't emit drivers so it doesn't need the checklist). Adds a "Before You Emit — 5-Check" block with **rule-pattern examples (not hardcoded driver names** — respects user's no-hardcoding preference):

```
Before emitting each driver_name, verify:
  □ No verb in name        Wrong: "opec_supply_cut"  Right: name=opec_supply, state=cut
  □ No direction word      Wrong: "bullish_eps"      Right: name=eps, direction=long
  □ No magnitude / number  Wrong: "100bps_margin"    Right: name=gross_margin, evidence="100bps"
  □ No ticker / company    Wrong: "aapl_iphone_..."  Right: name=iphone_sales
  □ No quarter / FY token  Wrong: "q3_revenue"       Right: name=revenue
```

Compounds with Lever #1 (prevention → less repair) and Lever #3 (better-formed first emissions → fewer retries → less token spend). Net gain on its own: ~2pp.

### §4.2 Repair / rejection audit tables — load-bearing for telemetry

Two new Neo4j labels, both mirror the existing learner audit upsert pattern at `orch.py:2450-2488`:

- `:DriverAutoRepair` (Lever #1) — every deterministic repair, with `{source_id, run_id, item_index, original_name, repaired_name, stripped_token, repair_kind, cascade_outcome, evidence_refs, repaired_at}` (full schema per §2 Lever #1 audit block; idempotency UNIQUE on `(source_id, item_index)` per v4-14 + v5-2)
- `:DriverProposalRejection` (already in CombinedPlan E1 + Lever #3) — every final rejection, with `{source_id, run_id, proposed_name, rejection_reason, evidence_refs, rejected_at}`; idempotency MERGE on `(source_id, run_id, proposed_name)`

**Why these tables exist (Fix #6 — clarified scope)**: PURE TELEMETRY for observability. They let an operator measure auto-repair hit rate, rejection patterns, promotion velocity, and registry split detection.

**Critical clarification: self-heal does NOT require any seed edits.** The system grows itself at runtime via the Neo4j `:EquivalenceToken` + `:VocabToken` stores (Lever #2 + E10). Audit data is NOT a feedback input to the markdown seed; the design does NOT assume an engineer will read these audits and add entries to `DriverOntology_Implementation.md`. The runtime loop is closed without any code-time intervention required.

Engineers MAY OPTIONALLY use audit data for code-time cleanup (deprecating bad VocabToken entries via Cypher migration, reviewing aberrant promotion counts, etc.) — but this is optional one-time engineering work, not a runtime dependency. If the audit tables existed but nobody ever looked at them, the system would still self-heal correctly; we would just lose observability into HOW it's healing.

~10 lines of Cypher constraints + audit upsert lives inside the writer. **Idempotency keys (v5-2 corrected)**: `:DriverAutoRepair` MERGE on `(source_id, item_index)` — aligns with v4-14, supersedes the earlier `(source_id, original_name)` wording that this section briefly contained; `:DriverProposalRejection` MERGE on `(source_id, run_id, proposed_name)`.

---

## §5. Recommended simplification — the live-growth architecture map

The CombinedPlan currently treats E10 (VocabToken) as one mechanism, SHORTCUTS_VOCAB as a separate markdown bank, and SYNONYM/PLURAL/ACRONYM as separate markdown banks. After Lever #2 + v5-5, **the architectural truth is**:

| Bank | Markdown seed | Runtime growth (Phase 1+) |
|---|---|---|
| Slot vocabs (THEMES/OBJECTS/CUSTOMERS/GEOGRAPHIES/INSTITUTIONS/METRICS) | seed only | `:VocabToken` nodes (E10) — **IMMEDIATE append** on accepted new-token proposal (NO N=2 gate per v6-4; token already validated in-context by R11+V14+new-token-gate at Driver write-time) |
| SYNONYM_MAP | seed only | `:EquivalenceToken{kind:synonym}` — **N=2 distinct-event promotion** (transforms need broader-blast-radius protection) |
| PLURAL_MAP | seed only | `:EquivalenceToken{kind:plural}` — same N=2 promotion mechanic |
| ACRONYM_MAP | seed only | `:EquivalenceToken{kind:acronym}` — same N=2 promotion mechanic |
| SHORTCUTS_VOCAB | seed only | **Direct `:Driver` row creation (v5-5)** — `is_shortcut=true` proposals land immediately on R11 evidence pass; NO EquivalenceToken record. Registry IS the shortcut store |

**Three growth patterns total (v6-4 — split Pattern A into A1 + A2)**:
- **Pattern A1 — `:VocabToken` immediate append (per E10)**: when an accepted `propose_new_drivers` introduces a token not in §F.1 slot vocabs, the token is appended to `:VocabToken` **IMMEDIATELY** at Driver-write time. NO N=2 gate. Rationale: slot vocab growth is a side-effect of accepted Driver creation — the Driver itself already passed R11+V1-V15 (which validates the token in context). Re-gating the token via N=2 would needlessly delay future slot classification.
- **Pattern A2 — `:EquivalenceToken{kind: synonym|plural|acronym}` with N=2 promotion**: equivalence proposals require N=2 distinct-event observations before promotion. Rationale: equivalences are TRANSFORMS that change canonicalize behavior across MANY future emissions; a wrong equivalence has broader blast radius than a wrong slot-vocab entry. The N=2 gate protects against one-LLM-mistake teaching the system a false synonym.
- **Pattern B — direct `:Driver` registration** (shortcuts): `is_shortcut=true` proposals bypass slot grammar (canonicalize steps 9-11) and register as `:Driver` rows on R11 evidence pass. No separate store; registry IS the shortcut store.

**Why the asymmetry**: synonyms/plurals/acronyms are TRANSFORM mappings (fold `topline → revenue` during canonicalize step 5). Shortcuts are CANONICAL FULL-NAMES that should be matched verbatim by B3 — no transform needed. A separate EquivalenceToken record for shortcuts would be parallel-store bloat (v5-5 / Bot 3 #4 critique).

**Simplification recommendation**: spec these as TWO patterns (not five separate banks). Pattern A covers 4 banks (slot vocabs + 3 EquivalenceToken kinds). Pattern B covers shortcuts only. Each pattern has a distinct rationale; conflating them was the v4 error v5-5 corrected.

**Not a code simplification** (Lever #2 + v5-5 are already in design surface) — a **doc / mental-model simplification** that helps future maintainers see the two-pattern split clearly instead of asking "why does VocabToken grow but SHORTCUTS_VOCAB doesn't follow the same path?"

### Other simplification candidates considered and rejected

- **B8 sorted-token reuse**: I considered marking it for deprecation once token stores mature. Rejected — it's ~20 LOC, cheap, catches edge cases canonicalize() doesn't, and removing it later is easier than adding it back. Keep.
- **STATES_VOCAB markdown enumeration**: bounded to 7 stable financial concepts. Already minimal. Keep.
- **MAPS_TO_CONCEPT / MAPS_TO_MEMBER for non-financial drivers**: already non-blocking per E17. Already minimal. Keep.
- **The 12-step canonicalize() pipeline**: each step has clear distinct purpose per `DriverProcess.html` §C2.2 "Why this specific order — 5 key dependencies." Keep.
- **R16 cleanup already removed**: `level`, `triggerable`, `effective_from`, `evhash16`, `magnitude`. The design is already lean post-R16. There is no further structural fat to trim.

**Honest answer to "is current design perfect as-is?"**: No, but very close. The R16 cleanup did the major simplification work. The only remaining opportunity is the unified-token-store framing in §5 above. Beyond that, current design is at the lean limit for its functional requirements.

---

## §6. Critical files to modify (when implementation begins — NOT NOW)

### §6.1 Spec files (Day 1 of implementation — text-only edits)

| File | Edit |
|---|---|
| `.claude/plans/PredictorLearner/Final.md` | §8 schema migration per E21 (PRECONDITION). §7 stays free-form per E30 — NOT in scope (v6-3 correction) |
| `.claude/plans/Drivers/DriverOntology_Implementation.md` | New §A.1 sub-bullet for repair wrapper (Lever #1); new §F.10 "Live Token Stores" (Lever #2); new §J entry for retry adapter (Lever #3); SKILL.md anti-pattern reference (§4.1) |
| `.claude/plans/Drivers/Neo4jXBRLDesign.md` | New schema sections for `:DriverAutoRepair` (with `item_index` property per v9-4), `:DriverProposalRejection`, `:EquivalenceToken`, `:EquivalenceConflictAudit`, `:EquivalenceCollisionAudit`; constraint definitions; **v8-1 — add `is_shortcut: bool DEFAULT false` to Driver OPTIONAL block in §C3.1** (discriminator for canonicalize step 8 standalone-shortcut path per v5-5 / v7-2); **v9-1 + v10-1 — add `vocab_visible_at: ISO ts` to `:VocabToken` schema with MIN-on-MATCH backdate** (PIT visibility anchor = `source_driver.registry_visible_at` at VocabToken write time; ON MATCH the field BACKDATES via `MIN(existing, $source_pit)` mirroring Driver.registry_visible_at MIN(DC.pit_cutoff) L6 pattern; parallel to `EquivalenceToken.equivalence_visible_at` per v4-7 + v10-2 backdate; closes L6 leak via slot-vocab path AND closes the out-of-order under-visibility scenario that v9-1's "set-once" semantics left open) |
| `.claude/plans/Drivers/CombinedPlan.md` | Add E26 (writer-side repair), E27 (unified equivalence store + promotion), E28 (driver-only informed retry), E29 (audit telemetry tables) to the §5 edit list with cross-refs to this plan. **v10-5 Phase-B fold reminder (per Bot B finding 5)**: when drafting E27 specifically, MUST explicitly include (a) v9-1 + v10-1 `vocab_visible_at` field on `:VocabToken` with MIN-on-MATCH backdate semantic, (b) v9-2 intra-MERGE `WITH et WHERE et.to_token = $to` conflict guard in Phase 1 Cypher, (c) v10-2 `equivalence_visible_at` MIN-backdate CASE expression in Phase 1 SET clause, (d) the X1+v10-1+v10-2 L6-alignment story (parallel to Driver.registry_visible_at across all 3 stores). Without explicit inclusion in E27, these v9 + v10 fixes can be lost in the fold from DriverImprovements forensic-only into the locked CombinedPlan source-of-truth. |

### §6.2 Implementation files (Day 2+ — Python + Cypher)

Pattern: mirror existing learner/guidance machinery wherever possible. Reusable code locations identified during exploration:

| New file | Mirrors / reuses |
|---|---|
| `scripts/earnings/builders/driver_ids.py::canonicalize()` | pure function, no repair logic (L3) |
| `scripts/earnings/builders/driver_writer.py::repair_and_retry()` | new — implements Lever #1 deterministic wrapper |
| `scripts/earnings/builders/driver_writer.py::write_equivalence_tokens()` | new — implements Lever #2 acceptance + promotion. v9-2: Phase 1 Cypher now includes intra-MERGE `WITH et WHERE et.to_token = $to` guard; Python detects empty-RETURN and writes `:EquivalenceConflictAudit` (same audit node as Phase 0 conflict-detection path) |
| `scripts/earnings/builders/driver_writer.py::write_vocab_token()` | new (v9-1 + v10-1) — implements E10 VocabToken append with PIT anchor + MIN-backdate. Contract: ON CREATE set `vocab_visible_at = source_driver.registry_visible_at` at write time within the same MERGE transaction as the Driver creation. ON MATCH (token+slot already exists) BACKDATE: `vocab_visible_at = CASE WHEN $source_pit < vocab_visible_at THEN $source_pit ELSE vocab_visible_at END` — mirrors Driver.registry_visible_at MIN(DC.pit_cutoff) L6 pattern. Without the ON CREATE anchor, historical backfills load future-coined slot tokens (L6 leak — closed by v9-1). Without the ON MATCH backdate, out-of-order/reverse-chrono backfills produce under-visibility — token "should be" visible at PIT T but isn't (closed by v10-1, reverses prior X3 deferral premise). Same architectural pattern as `EquivalenceToken.equivalence_visible_at` (v4-7 + v10-2 backdate). |
| `scripts/earnings/earnings_orchestrator.py::run_driver_write()` (transport-neutral name per Final.md §5 — Fix #5) | mirror H2 informed-retry logic from `run_learner_via_sdk()` at lines 1301-1387 verbatim; new function deliberately drops the legacy `_via_sdk` suffix since SDK/`claude -p` is a forbidden target path per Final.md §5 ("anchors to replace, not target names"). Transport is interactive TMUX |
| `scripts/earnings/earnings_orchestrator.py::DriverWriteOutcome` enum | mirror `LearnerOutcome` enum at lines 1066-1106 |
| `scripts/earnings/earnings_orchestrator.py::_upsert_driver_audit_in_history()` | mirror `_upsert_audit_in_history()` at lines 2473-2488 |
| `scripts/earnings/earnings_orchestrator.py::_merge_retry_response()` (NEW per Fix #8 + v3-8/v3-9 + v4-8/v4-9/v4-15 + v5-9/v5-11) | 3-stage merge logic (see §2 Lever #3 merge spec): STAGE 1 inversion-whitelist drift guard (v4-8 — diff LLM-authored non-driver fields only; ORCHESTRATOR_STAMPED excluded); STAGE 2 surgical-replace with array-order preservation + tuple-equality for PASSED indices (v4-9 + v5-9) + orphan R1 proposal drop (v4-15); STAGE 3 propose_new_drivers gate with same-name replacement (v5-11) + unresolved-carve-out + scope-creep block. Fail-closed semantics: any guard violation → R1 rejected drivers stay rejected (no silent cherry-picking) |

### §6.3 SKILL.md edits (Day 5a per CombinedPlan §11 + E30)

- `.claude/skills/earnings-learner/SKILL.md` — add anti-pattern checklist (§4.1) + emission contract for `propose_new_drivers[i].is_shortcut: bool` flag (Lever #2 / v3-5 / v5-5 direct-Driver path)
- `.claude/skills/earnings-prediction/SKILL.md` — **NO EDITS NEEDED** per E30. Predictor is consumer-only (does not emit canonical drivers); §7 `key_drivers[]` stays free-form analysis prose. Anti-pattern checklist + is_shortcut emission contract apply ONLY to the learner skill

### §6.4 E16 input JSON contract update (v3-5)

CombinedPlan E16 `propose_new_drivers[]` schema MUST add the optional field:

```
propose_new_drivers: [
  {
    name, label, base_label, segment, definition,
    allowed_states, aliases,
    is_shortcut: bool  // v3-5 NEW. Default false.
                       // If true: this proposal is a standalone shortcut
                       // (yield_curve / fda_approval / chip_shortage class).
                       // MUST have zero slot-classifying tokens; Lever #2
                       // (v5-5: lands DIRECTLY as :Driver row; no parallel
                       //  :EquivalenceToken record. Registry IS the shortcut store.)
                       // SKILL.md teaches LLM when to set this flag:
                       //   "Set is_shortcut=true ONLY when the entire driver name
                       //    is a canonical macro/regulatory/corporate-action phrase
                       //    that does not decompose into theme/object/customer/
                       //    geography/institution/metric slots."
  }
]
```

Without this field, Lever #2's shortcut bootstrap path never fires; SHORTCUTS_VOCAB stays a manual code-time-edit list.

---

## §7. Verification — how to know each lever works

### §7.1 Per-lever tests

**Lever #1 (auto-repair)**:
- Unit: feed `{driver_name: "opec_supply_cut", driver_state: null}` AND `opec_supply` EXISTS in registry → expect `{driver_name: "opec_supply", driver_state: "cut"}` + `:DriverAutoRepair{repair_kind:state_to_driver_state}` row + write committed
- **Unit (Fix #4)**: feed `{driver_name: "opec_supply_cut", driver_state: null}` AND `opec_supply` does NOT exist in registry → expect `:DriverAutoRepair{repair_kind:deferred_to_retry}` row + tag routed to Lever #3 retry (NO new Driver auto-registered)
- **Unit (Fix #9 case-insensitive)**: feed `{driver_name: "opec_supply_cut", driver_state: "Cut"}` → expect repair commits (case-insensitive match treats "Cut" == "cut" as agreement, not conflict)
- Unit: feed `{driver_name: "opec_supply_cut", driver_state: "expanded"}` (genuine conflict) → expect rejection (no silent overwrite)
- Unit: feed `{driver_name: "q3_revenue"}` AND `revenue` exists in registry → expect repair commits to `revenue`; if `revenue` does NOT exist → deferred to retry
- Unit: feed `{driver_name: "100bps_margin_pressure"}` → expect strip `100bps` → re-canonicalize → likely still reject due to "pressure" verb; verify rejection logged
- **Unit (Fix #7 idempotency — v5-2 corrected key)**: feed same `(source_id, item_index)` twice → expect exactly ONE `:DriverAutoRepair` row (MERGE upsert, not duplicate). [SUPERSEDES the v3-era `(source_id, original_name)` key per v4-14 + v5-2]

**Lever #2 (equivalence store)**:
- [SUPERSEDED v3 — see v4-1 / v4-7 tests below]: ~~Unit: propose driver with `aliases: ["cloud_topline"]` ... → expect `source_driver_ids:["driver:cloud_revenue"]`~~ (use v4-1 / v5-1 wording: `observation_keys`, no `source_driver_ids` for promotion; provenance is separate)
- [SUPERSEDED v3 — distinct source counting moved to v4-2 / v5-4 tests below]: ~~re-propose with SAME `source_id` → `source_driver_ids` UNCHANGED~~
- [SUPERSEDED v3 — promotion + PIT now via `equivalence_visible_at` per v4-7 / v5-12, not wall-clock `promoted_at`]: ~~re-propose with DIFFERENT `source_id` → ... `promoted_at` set~~
- Unit: canonicalize `cloud_topline` after promotion → expect fold to `cloud_revenue`, B6 hits registry
- [SUPERSEDED by v5-5]: ~~shortcut bootstrap creates `:EquivalenceToken{kind:shortcut, phrase:"chip_shortage"}`~~ — v5-5 drops kind:shortcut entirely. New behavior: shortcut Driver lands as `:Driver{name:"chip_shortage"}` directly; future B3 lookups hit Driver.name. See v4-3 + v5-5 tests below for the current expected behavior.
- Unit: malicious case — LLM proposes alias that collides with another existing Driver's name → expect rejection, no token write
- [SUPERSEDED v3 — PIT now via `equivalence_visible_at` per v4-7 + v5-12]: ~~PIT test using `promoted_at` for future-vocab leak check~~. See §7.y v4-7 test below (uses `equivalence_visible_at` correctly).
- **Unit (Fix #2 hide candidates)**: render bundle vocab block with one `candidate` and one `promoted` equivalence → expect ONLY the `promoted` entry in the LLM-visible output; `candidate` invisible

**Lever #3 (informed retry)**:
- Integration: learner emits 1 primary + 4 contributing drivers (5 total), 2 fail V8/V10 → driver_write returns rejection reasons → retry prompt built → LLM emits fixed drivers in full result.json → second dry-run passes → all 5 land with `outcome=SUCCEEDED_AFTER_RETRY` on 2 of them
- Integration: retry still fails → those 2 → `:DriverProposalRejection` rows + run continues with 3 successful drivers (PARTIAL policy)
- **Integration (Fix #8 merge logic)**: LLM's retry response also alters `analysis` and `falsifier` text → orchestrator's `_merge_retry_response()` discards those changes, keeps first-emission values verbatim; only driver-field changes propagate
- Integration: verify Lever #1 deferred-to-retry cases (Fix #4) successfully land via this retry path

### §7.x v3 additional tests

**v3-1 — canonicalize purity (parameter-injection)**:
- Unit: call `canonicalize("cloud_topline", vocab=VocabSnapshot(synonym_map={"topline":"revenue"}))` → expect "cloud_revenue"
- Unit: same call with `synonym_map={}` → expect "cloud_topline" (no fold)
- Unit: same call across 1000 invocations with identical (input, vocab) → expect identical output every time (determinism)
- Unit: verify `canonicalize` function has ZERO Neo4j driver imports / DB-call statements via static analysis

**v3-2 — magnitude narrowing**:
- Unit: feed `{driver_name: "5g_capex"}` → expect NO strip; 5g classified via new-token gate as theme/object
- Unit: feed `{driver_name: "10yr_yield"}` → expect NO strip; 10yr classified as theme/macro
- Unit: feed `{driver_name: "3nm_chip_supply"}` → expect NO strip; 3nm as theme/object
- Unit: feed `{driver_name: "100bps_margin"}` → expect strip 100bps (matches unit-suffix pattern)
- Unit: feed `{driver_name: "2pct_eps_beat"}` → expect strip 2pct, then catch `beat` as state, repair to `eps + state=beat` (if eps in registry)

**v3-3 — trend-partner preference**:
- Unit: registry has `revenue_trend` (allowed_states: trend_motion). Feed `{driver_name: "revenue_decline", driver_state: null}` → expect repair to `{driver_name: "revenue_trend", driver_state: "declined"}` + `:DriverAutoRepair{repair_kind: state_to_trend_partner}`
- Unit: registry has `revenue` only (no _trend partner). Feed same input → expect repair to `revenue + declined` if revenue allows trend states
- Unit: registry has NEITHER `revenue_trend` nor `revenue`. Feed same → expect DEFERRED_TO_RETRY (no safe bare-metric collapse)

**v3-4 — equivalence circularity broken**:
- Unit (v4-4 + v5-6 — REPHRASED): propose new Driver `cloud_revenue` with `aliases: ["cloud_topline"]` where `topline → revenue` synonym does NOT yet exist → expect Driver PASSES V1-V15 strictly (V1 has nothing to validate because Driver.aliases[] stays EMPTY at registration per v4-4). `cloud_topline` is recorded as `:EquivalenceToken{kind:synonym, from:topline, to:revenue, status:candidate}`, NOT written to `Driver.aliases[]`. V1 strictness preserved throughout (NO "V1 forgiving" relaxation — v5-6 removes the wording)
- [SUPERSEDED by v5-6 + v5-7]: ~~verify Driver.aliases[] can include cloud_topline via Cypher migration / lazy alias-link~~ — v5-7 drops the migration suggestion; v5-6 drops alias-sync. New behavior: post-promotion, canonicalize() step 5 handles the fold automatically; no Driver.aliases[] mutation occurs.

**v3-5 — is_shortcut flag wiring**:
- Unit: parse E16 input JSON with `propose_new_drivers[i].is_shortcut: true, name: "chip_shortage", aliases: [], allowed_states: [...]` → orchestrator validates, writer creates `:Driver{name:"chip_shortage", is_shortcut:true}` directly (v5-5: NO parallel `:EquivalenceToken`; registry IS the shortcut store)
- Unit: same with `is_shortcut: true` but name has slot-classifying tokens (e.g., `iphone_china_sales`) → REJECT (R11 violation; shortcuts must have zero slot tokens)
- Unit: verify SKILL.md emission contract includes is_shortcut teaching by grep

**v3-7 — backward-compat (no retrofit)**:
- Unit: registry already has `cloud_topline` and `cloud_revenue` as separate Drivers (legacy split). After `topline → revenue` equivalence promotes, query both Drivers → expect both STILL EXIST with original names (Driver.name immutable). Promotion only affects future B3/B4 lookups, not retroactive merge.

**v3-8 — surgical-replace + scope-creep block**:
- Integration: R1 (learner per E30 + v7-1) emits 1 primary_driver + 4 contributing_factors[0..3] (5 driver-tags total). Of the 5: primary_driver PASSES; contributing_factors indices 1 PASSES; 0, 2, 3 FAIL. R2 (retry) emits a full result.json with all 5 driver-tags changed → expect final merged result has R1's primary_driver verbatim + R1's contributing_factors[1] verbatim + R2's contributing_factors[0, 2, 3] (per v3-8 + v10-6 stale `key_drivers` → `contributing_factors` cleanup)
- Integration: R2 retry adds a new `propose_new_drivers` entry NOT referenced by any failed tag → expect entry REJECTED, marked FAILED_SCOPE_CREEP
- Integration: R1 has tag referencing name "foo" with no propose entry → V11 unresolved_driver_name. R2 fixes by adding `propose_new_drivers[{name:"foo"}]` → expect new entry ACCEPTED (legitimate recovery carve-out)

**v3-9 — drift guard**:
- Integration: R1 has `analysis: "X"`, R2 retry returns `analysis: "Y"` (changed) plus fixed drivers → expect FAILED_DRIFT_GUARD, all R1 rejected drivers stay rejected, R2 driver changes discarded, field-diff logged to :DriverDriftAudit
- Integration: R1 and R2 have identical non-driver fields → expect drift guard PASSES, surgical-replace proceeds to STAGE 2

**v3-14 — N=2 is hard constant**:
- Unit: grep `driver_writer.py` for `EQUIV_PROMOTE_N` → expect single hardcoded `= 2` constant, no env var read, no config file lookup
- Unit: confirm no other code path can mutate EQUIV_PROMOTE_N at runtime (static analysis)

**v8-5 — v5-1 to_token conflict at ACCEPTANCE time (NEW per v8-5)** — distinct from v4-6 collision-recheck-at-PROMOTION:
- Unit: First proposal creates `:EquivalenceToken{kind:synonym, from:topline, to:revenue, status:candidate}`. Second proposal claims `topline → income` (different to_token, same kind+from) → expect REJECT + `:EquivalenceConflictAudit{equivalence_id, existing_to:"revenue", proposed_to:"income", source_id, item_index, rejected_at}` row written. The existing candidate's `observation_keys`, `observation_pit_cutoffs`, status, etc. ALL UNCHANGED (the conflicting proposal does NOT count as an observation). This is acceptance-time conflict detection (per v5-1 Python pre-MERGE check); distinct mechanism from v4-6 collision-recheck-at-promotion (which guards against Driver registry collisions emerging between candidate creation and Nth observation).
- Differentiation unit: verify `:EquivalenceConflictAudit` (v5-1 to_token conflict at acceptance) is a distinct Neo4j label from `:EquivalenceCollisionAudit` (v4-6 Driver collision at promotion). Both audit nodes exist; both have distinct schemas; tests should not conflate them.

**v8-6 — v5-4 / v6-2 Cypher concurrency under MERGE locking (NEW per v8-6)** — verifies two-phase pattern correctness under concurrent writers:
- Concurrency: two writers issue the v5-4 PHASE 1 query (MERGE + observation_keys append + RETURN would_promote) against the SAME `equivalence_id` near-simultaneously. Expect: Neo4j's per-node MERGE locking serializes the two writes; observation_keys count is exactly 2 (no double-increment, no missed-increment); both writers' RETURN values are consistent with their serialized order.
- Concurrency promotion (v10-3 PRECISION-CORRECTED): when count is at N-1 and two writers arrive concurrently, BOTH writers' PHASE 1 may return `would_promote=true` (the Phase 1 SET + WITH compute completes BEFORE either writer's PHASE 3 status flip runs — they're separate Cypher queries with Python in between). What's actually guaranteed: exactly ONE of the two writers' PHASE 3 SET status transition SUCCEEDS — the second writer's PHASE 3 `WHERE et.status = "candidate"` clause filters out (because the first writer's PHASE 3 already flipped status to "promoted"), making it a no-op. The Python collision-recheck + PHASE 3 promote thus FIRES once even if Phase 1 returns true twice. v10-3 wording fix per Bot A finding 3 — the prior "exactly ONE PHASE 1 returns true" assertion was too strong; the actual invariant is "exactly ONE PHASE 3 status transition succeeds."
- Determinism: same `(equivalence_id, observation sequence)` across 100 runs → identical final state (same observation_keys, same status, same equivalence_visible_at). Neo4j MERGE locking + v5-4 compute-before-SET + v6-2 two-phase = deterministic outcome.

### §7.y v4 additional tests

**v4-1 — observation_keys naming + Cypher consistency**:
- Unit: grep schema and Cypher — confirm field is `observation_keys` everywhere, NOT `source_driver_ids`
- Unit: provenance lives in separate `provenance_source_driver_ids` field; promotion counts `size(observation_keys)`, NOT provenance

**v4-2 — event-level observation dedup**:
- Unit (Phase-1 primary case per E30): emit synonym from `learner:AAPL:Q2_FY2026` → observation_keys = [`AAPL:Q2_FY2026`], count=1, status=candidate
- Unit (Phase-1 retry-dedup): re-run same learner with SAME source_id `learner:AAPL:Q2_FY2026` → observation_keys UNCHANGED (still 1 entry), still candidate (confirms same-source retries don't promote)
- Unit (Phase-1 promotion): emit SAME synonym from `learner:AAPL:Q3_FY2026` (DIFFERENT event for same ticker) → observation_keys grows to 2, status promoted, equivalence_visible_at set to pit_cutoff(Q3)
- Unit (algorithm correctness — defensive for Phase 2+, NOT Phase 1 deployment per E30): emit synonym from `predictor:AAPL:Q2_FY2026` then SAME from `learner:AAPL:Q2_FY2026` → observation_keys UNCHANGED at 1 entry (predictor+learner same-event collapse to ONE observation per v4-2). NOTE: predictor is consumer-only in Phase 1; this test exists to verify the algorithm correctly handles producer-prefix stripping if predictor or other multi-producer scenarios are activated in later phases.

**v4-3 — shortcut bootstrap explicit flow**:
- Unit: propose Driver with `is_shortcut=true, name="chip_shortage"`, zero slot-classifying tokens, R11 evidence ok → expect `:Driver{name:"chip_shortage"}` lands IMMEDIATELY (v5-5: NO `:EquivalenceToken{kind:shortcut}` written)
- **Unit (v5-10 adversarial — NEW)**: propose Driver with `is_shortcut=true, name="made_up_phrase"`, zero slot-classifying tokens, BUT no real evidence ground in registry/source (V10 evidence_refs[] empty or hallucinated SRC) → expect rejection on R11 evidence requirement (NOT on shape or banned-content). Confirms R11 evidence gate is the critical quality control once slot grammar is bypassed
- Unit: propose `is_shortcut=true` with slot-classifying token in name (e.g., `iphone_chip_shortage`) → REJECT (R11 violation: shortcuts must have zero slot tokens)
- **Unit (v10-4 ≥2-token negative — NEW per Bot B finding 4)**: propose `is_shortcut=true, name="winter"` with valid R11 evidence + zero slot-classifying tokens + non-banned single-token name → expect REJECTION on `shortcut_min_tokens` (the v7-2 ≥2-token mechanical gate at acceptance rule (e).3), NOT on R11 evidence (evidence is valid) NOR on slot-classifying-token check (winter has none) NOR on banned-content (winter is not banned). Confirms the v7-2 mechanical gate fires independently of the other shortcut-acceptance gates and correctly rejects single-word LLM hallucinations like `winter`, `crash`, `disaster`, `armageddon`.
- Unit: future B3 lookup for `chip_shortage` hits the registered Driver directly (no canonicalize, no shortcut bank consultation needed)

**v4-4 — V1 stays strict; candidate aliases segregated**:
- Unit (v6-5 NON-STRICT alias path): propose Driver `cloud_revenue` with `aliases: ["cloud_topline"]` BEFORE `topline → revenue` is promoted → canonicalize(`cloud_topline`, current_vocab) = `cloud_topline` (no fold available) ≠ `cloud_revenue` → V1 would fail → route alias to `:EquivalenceToken{kind:synonym, from:topline, to:revenue, status:candidate}`. `Driver.aliases[]` is EMPTY at registration. V1 strictly passes for the Driver (no aliases to validate).
- Unit (v6-5 STRICT alias path — NEW per v6-5): propose Driver `iphone_china_sales` with `aliases: ["china_iphone_sales"]` (word-order variant). canonicalize(`china_iphone_sales`, current_vocab) = `iphone_china_sales` via slot-reorder → matches parent.name → V1 passes → **APPEND to `Driver.aliases[]`**. No EquivalenceToken record needed (no transform required). Future emissions hit B4 fast-path.
- Unit (v6-5 STRICT alias via PROMOTED equivalence — NEW per v6-5): registry already has promoted `topline → revenue`. Now propose Driver `cloud_revenue` with `aliases: ["cloud_topline"]` → canonicalize fold via the promoted equivalence at step 5 → `cloud_revenue` → matches parent.name → V1 passes → APPEND to `Driver.aliases[]`. (Same alias gets routed DIFFERENTLY depending on whether the underlying equivalence is already promoted — snapshot-driven routing per v6-5.)
- Unit (v5-6 REPLACES the v4-era "alias-sync after promotion" test): after `topline → revenue` promotes IN A LATER RUN, the orchestrator does NOT retroactively sync `cloud_topline` into the legacy `cloud_revenue` Driver's aliases[]. The promoted equivalence enters canonicalize()'s synonym_map at step 5 for FUTURE emissions. A future emission of `cloud_topline` folds via canonicalize → resolves to `cloud_revenue` → B6 (canonical name match) hits the registry → reuse correctly. The legacy `cloud_revenue` Driver's aliases[] remains UNCHANGED (no retrofit).

**v4-5 — V8 enforced post-repair**:
- Unit: repair to `opec_supply + state=paused` where `opec_supply.allowed_states = [cut, expanded, exhausted, stable]` → V8 fails → DEFER_TO_RETRY (NOT silent commit)
- Unit: repair to `opec_supply + state=cut` (in allowed_states) → write commits

**v4-6 — equivalence_id unique + collision recheck at promotion**:
- Unit: try to MERGE two EquivalenceToken nodes with same equivalence_id → constraint violation, second MERGE is no-op on existing
- Integration: candidate `topline → revenue` created at Q1. At Q2, a new Driver `cloud_topline` lands (separate producer). At Q3, 2nd distinct observation of `topline → revenue` arrives. Promotion attempt re-runs collision check → detects `cloud_topline` Driver collision → promotion DENIED, equivalence stays candidate, `:EquivalenceCollisionAudit` row written

**v4-7 — equivalence_visible_at PIT anchor**:
- Unit: candidate observed at pit_cutoff Q1+Q3 with N=2 → expect `equivalence_visible_at = pit_cutoff(Q3)` (the Nth = later)
- Unit: historical run at pit_cutoff Q2 (between Q1 and Q3) → promoted equivalence NOT visible (visible_at = Q3 > Q2)
- Unit: historical run at pit_cutoff Q4 → equivalence visible
- Unit: promoted_at (wall-clock) is also Q3-ish but DIFFERENT from equivalence_visible_at; PIT filter uses visible_at, not promoted_at
- **Unit (v10-2 backdate on out-of-order observation — NEW per Bot A finding 2 / X3 reversal)**: equivalence already promoted at visible_at=Q3 (Nth observation arrived from a Q3-PIT learner emission). Later, a backfill emission arrives with pit_cutoff=Q1 (earlier than Q3). Phase 1 SET re-evaluates: sort([Q3, ..., Q1])[N-1] = Q1 < current visible_at=Q3 → backdate fires; `equivalence_visible_at` UPDATES to Q1. Historical query at pit_cutoff=Q2 (previously NOT visible since Q3 > Q2) NOW sees the equivalence (Q1 ≤ Q2). This closes the under-visibility scenario where out-of-order/reverse-chrono backfills produced spurious slot_anchor_unavailable rejections.
- **Unit (v10-2 backdate is monotonically non-increasing)**: after backdate to Q1, a LATER observation with pit_cutoff=Q4 arrives. Phase 1 SET re-evaluates: sort([Q1, Q3, Q4, ...])[N-1] = Q3 > Q1 → backdate CASE does NOT fire (the inner WHEN `< et.equivalence_visible_at` is false); visible_at STAYS at Q1. MIN-backdate semantics: visible_at can only go DOWN as new earlier-PIT observations arrive; never UP.
- **Unit (v10-2 no-op for not-yet-promoted)**: candidate with count<N receives a new observation. Phase 1 SET runs but status="candidate" so the v10-2 backdate CASE's `WHEN et.status = "promoted"` guard is false → no-op. Phase 3 (when promotion eventually fires) sets visible_at correctly. Confirms v10-2 doesn't break first-promotion semantics.

**v4-8 — drift guard inversion**:
- Unit: R2 changes ONLY `analysis` field (in LLM_AUTHORED_NON_DRIVER) → FAILED_DRIFT_GUARD
- Unit: R2 changes ONLY `attributed_at` (in ORCHESTRATOR_STAMPED — harmless echo; learner-stamped field per Final.md §8 / E30) → drift PASSES, retry proceeds to STAGE 2
- Unit: result.json schema adds a new LLM-authored field "foo" not in either whitelist → R2 changes foo → drift FAILS (future-proof: unknown fields default-include in guard)

**v4-9 — array order preservation**:
- Unit (Phase-1 learner per E30 + v7-1 + v10-6): R1.contributing_factors = [a, b, c, d], indices 1+3 failed. R2.contributing_factors = [a, b', c, d'] (same length, same order) → STAGE 2 surgical-replace proceeds
- Unit: R1.contributing_factors length=4, R2.contributing_factors length=3 → FAILED_RETRY_SHAPE_VIOLATION
- Unit: R1.contributing_factors = [a, b, c], R2.contributing_factors = [a, c, b'] (reordered) → FAILED_RETRY_SHAPE_VIOLATION

**v4-14 — audit key with item_index**:
- Unit: Mode-2 news emission with 3 items, all same original_name "foo" but different tickers → expect 3 separate `:DriverAutoRepair` rows (keyed by (source_id, item_index 0/1/2)), NOT 1 collapsed row
- Unit: same source_id, same item_index, re-run → expect 1 row (upsert), not 2

**v4-15 — orphaned proposal drop**:
- Unit (Phase-1 learner per E30 + v7-1 + v10-6): R1 has contributing_factors[1]={name:"foo"} + propose_new_drivers includes {name:"foo"}. R2 replaces contributing_factors[1] with {name:"bar"}. R2 propose includes {name:"bar"}. Merged result → R1's "foo" proposal DROPPED (V13 happy), R2's "bar" proposal KEPT.

**v3-6 cascade_outcome (v4-17 — was missing in v3 tests)**:
- Unit: feed inputs producing each cascade_outcome value (PASS, REJECTION_NO_METRIC_TOKEN, REJECTION_BANNED_TOKEN, REJECTION_TOO_MANY_SLOTS, DEFERRED_TO_RETRY, FINAL_REJECT_OTHER) → expect `:DriverAutoRepair.cascade_outcome` populated correctly for each

### §7.z v9 additional tests

**v9-1 — VocabToken PIT filter (closes L6 leak parallel to v4-7)**:
- Unit (PIT under-cutoff = hidden): Driver D1 has `registry_visible_at = 2024-Q3` and introduces a new slot token `hyperscaler` → writer creates `:VocabToken{slot:"customer", token:"hyperscaler", vocab_visible_at: 2024-Q3, source_driver_id: D1.id, added_at: $now}`. Run bootstrap query at `$run_pit_cutoff = 2020-Q1` → returns ZERO VocabToken rows; `hyperscaler` NOT in `vocab_snapshot.slot_vocabs.customer`; canonicalize at this PIT cannot classify the token (falls to new-token gate).
- Unit (PIT post-cutoff = visible): Same setup; run bootstrap query at `$run_pit_cutoff = 2024-Q4` → `hyperscaler` IS in slot_vocabs; canonicalize classifies the token to customer slot correctly.
- Unit (write-time anchor): verify that on VocabToken write, `vocab_visible_at` equals the source_driver's `registry_visible_at` at the moment of write (NOT the wall-clock `$now`). Pure unit test of `driver_writer.write_vocab_token()` contract.
- **Unit (v10-1 backdate via MIN-on-MATCH — REPLACES the v9-era no-backdate test)**: Driver D1 created at wall-clock 2024-12 with registry_visible_at = 2024-Q3 introduces token `hyperscaler` → VocabToken{vocab_visible_at: 2024-Q3} initially. Later (wall-clock 2025-01), backfill creates Driver D2 with registry_visible_at = 2024-Q1 whose canonical name also contains `hyperscaler`. D2's write triggers VocabToken ON MATCH on the same {slot, token} key. Expect: `vocab_visible_at` BACKDATES to 2024-Q1 (the MIN of existing=2024-Q3 and new $source_pit=2024-Q1). Subsequent historical query at pit_cutoff=2024-Q2 NOW sees the token (vocab_visible_at=2024-Q1 ≤ 2024-Q2). This eliminates the out-of-order under-visibility scenario without introducing future-vocab leak (the new pit_cutoff is by definition older than or equal to its source Driver's registry_visible_at).
- Unit (backdate idempotent — MIN only goes down): repeat the ON MATCH path with a LATER-PIT Driver (e.g., D3 at registry_visible_at=2025-Q1 using same `hyperscaler` token). Expect: `vocab_visible_at` STAYS at 2024-Q1 (current MIN), does NOT update to 2025-Q1. MIN-on-MATCH is monotonically non-increasing; later writes with higher PITs are no-ops on the visible_at field.
- Determinism check: same bundle input + same `$run_pit_cutoff` → identical `vocab_snapshot.slot_vocabs` regardless of wall-clock. Verifies L3 purity is not violated by wall-clock VocabToken drift.

**v9-2 — Intra-MERGE-transaction to_token conflict guard (concurrent-writer race protection)**:
- Concurrency unit (the race v9-2 closes): two writers near-simultaneously emit conflicting equivalences for the SAME `(kind, from_token)` pair:
   - Writer A: `topline → revenue` with `source_id = "learner:AAPL:Q2_FY2026"`, observation_key = `AAPL:Q2_FY2026`.
   - Writer B: `topline → income` with `source_id = "learner:MSFT:Q2_FY2026"`, observation_key = `MSFT:Q2_FY2026`.
   - Both pass Phase 0 (no existing EquivalenceToken with this equivalence_id).
   - Both reach Phase 1 MERGE. Neo4j serializes per-node MERGE locking; say Writer A wins ON CREATE (`to_token = revenue`); Writer B's MERGE matches A's node (ON MATCH path).
   - v9-2 `WITH et WHERE et.to_token = $to` clause: Writer A's row passes (A's `$to = revenue` matches `et.to_token = revenue`). Writer B's row is FILTERED OUT (B's `$to = income` ≠ `et.to_token = revenue` set by A).
   - Expect: Writer A's SET runs; A's observation_keys = [`AAPL:Q2_FY2026`]; Writer A's RETURN returns one row.
   - Expect: Writer B's SET does NOT run; B's RETURN returns zero rows.
   - Expect: Python detects B's empty RETURN; writes `:EquivalenceConflictAudit{equivalence_id, existing_to:"revenue", proposed_to:"income", source_id:"learner:MSFT:Q2_FY2026", item_index, rejected_at}`.
   - Expect: B's observation_key `MSFT:Q2_FY2026` is NOT in observation_keys of the EquivalenceToken. The conflicting observation does NOT count toward promotion.
- Sequential test (sanity — Phase 0 catches first): same setup but with A and B sequenced. A's run completes fully (CREATE + SET observation). B's Phase 0 (Python pre-check) reads existing `et.to_token = revenue`, sees B's `$to = income` differs → REJECTS at Phase 0 with `:EquivalenceConflictAudit` BEFORE reaching Phase 1. Confirms Phase 0 + Phase 1 (v9-2) are belt-and-suspenders: Phase 0 catches sequential, Phase 1 catches concurrent.
- Idempotency: re-running the SAME emission (same source_id, same to_token = revenue) hits ON MATCH; `WITH et WHERE et.to_token = $to` passes (revenue == revenue); SET runs with append-only-if-not-present semantics → observation_keys UNCHANGED if obs_key already present. Confirms v9-2 doesn't accidentally break legitimate retry-idempotency.

### §7.2 End-to-end smoke

After 1 ticker × 4 quarters of historical replay:
- Query `:DriverAutoRepair` count → expect 5-10 rows per quarter (state-smuggle is the dominant repair)
- Query `:EquivalenceToken{status:promoted}` count → expect grows to ~5-10 by Q4
- Query `:DriverProposalRejection` count → expect declining trend Q1 → Q4 (system self-heals)
- Query Driver registry split detection (sorted-token V15) → expect zero or near-zero

### §7.3 8-quarter realistic target

After 8Q × 50-200 active tickers:
- Clean-landing rate (cohort metric: % of emissions that wrote without rejection AND without registry split): **target ~96-98%**
- Equivalence token promotion count: ~30-80 promoted entries (synonyms / plurals / acronyms only — shortcuts grow as `:Driver` rows directly per v5-5, not in the EquivalenceToken store)
- Shortcut Driver count: ~5-15 new `:Driver` rows authored with `is_shortcut=true` over the 8Q period (yield_curve, fda_approval, chip_shortage class)
- Auto-repair hit rate: stabilizes at ~3-5% of emissions (the deterministic-recoverable mistakes)
- Retry hit rate: stabilizes at ~2-4% of emissions (the LLM-fixable tail)
- Final rejection rate: ~2-4% of emissions (genuine tail — hallucinated evidence, novel concepts with no anchor)

---

## §8. What is NOT in this plan (explicit rejections)

| Idea | Why rejected |
|---|---|
| V10 substring fallback for SRC:* | Evidence IDs must stay exact; substring matching opens hallucination surface. Rejected (ChatGPT correct). |
| Auto-promote `allowed_states` on existing Drivers | E25 says registry wins on conflict, drift is audited. Auto-promotion silently mutates registry — wrong. Rejected. |
| NLP library (spaCy/WordNet/NLTK) for normalization | Violates L3 determinism + has finance-jargon gaps. Rejected. |
| Multiple LLM repair attempts (N > 1) | Learner pattern caps at 1 retry — production-validated. More attempts = more drift + diminishing returns. Rejected. |
| Bigger cold-start seed (32 → 100) | Only helps Q1; averaged over 8Q gain is ~1pp. Lower leverage than the 3 levers. Defer to post-Lever-2 measurement. |
| Pre-emit LLM "double-check" turn (separate call before final emission) | Doubles LLM token cost; SKILL.md anti-pattern checklist (§4.1) achieves similar at zero cost. Rejected. |
| Promotion threshold tunable per-environment | v3-14: HARD code-time constant N=2 in `driver_writer.py`. NOT env-tunable, NOT config-driven. Engineer may edit at source; never via env/config at runtime. Aligns with L4 |
| Equivalence store across separate Neo4j labels (`:SynonymToken`, `:PluralToken`, etc.) | Single `:EquivalenceToken{kind}` is simpler, one render path, one audit pipeline. Unified store wins. |
| **Aggressive pre-launch markdown seed expansion (50-100 entries) (v3-13)** | Only helps Q1; averaged over 8Q gain is ~1-2pp; lower leverage than Levers #1/#2/#3. Defer to post-launch measurement — if audit data after Q1 shows specific recurring repair patterns, add those entries to seed code-time then. Speculative pre-launch expansion = guessing without data |
| **Adversarial-fuzz test suite expansion pre-launch (v3-13)** | The §7 per-lever tests cover all 9 fix-specific behaviors + per-lever edge cases. A 1000-case adversarial fuzz suite is high-cost / low-marginal-value when production data will reveal real failure patterns within Q1. Defer; iterate based on actual production audit signals |

---

## §9. Implementation order (when work begins)

```
Day 0   PRECONDITION   E21 Final.md §8 schema migration (BLOCKER for everything
                        else). §7 stays free-form per E30 — NOT migrated (v6-3).
Day 1   Spec           Apply E26-E29 (this plan) + all 25 E* from CombinedPlan to 3 spec files
Day 1   Schema         Neo4j constraints for Driver, DriverChange, DriverAutoRepair,
                        DriverProposalRejection, EquivalenceToken, VocabToken
Day 2   Code           driver_ids.py (pure canonicalize, no repair)
Day 3   Code           driver_writer.py (MERGE, validators V1-V15, repair wrapper Lever #1,
                        equivalence token writer Lever #2, promotion gate)
Day 4   Code           driver_write_cli.py + driver_write.sh + bundle renderer (PIT-filtered
                        catalog + promoted equivalences block)
Day 5a  SKILL.md only   earnings-learner SKILL.md anti-pattern checklist
                        (§4.1) + is_shortcut emission contract (v3-5).
                        Per E30: NO edits to earnings-prediction/SKILL.md
                        (predictor is consumer-only).                    ← v3-11 split + E30
Day 5b  Orchestrator    run_driver_write() with informed retry (Lever #3
                        — mirror H2 informed-retry logic from
                        run_learner_via_sdk() at orch.py:1301-1387 verbatim;
                        new function name transport-neutral per Final.md §5 — Fix #5).
                        Includes _merge_retry_response() with v3-9 + v4-8
                        STAGE 1 drift guard (inversion-whitelist), v3-8 + v4-9
                        STAGE 2 surgical-replace (array-order preserved) + v4-15
                        orphan proposal drop, STAGE 3 scope-creep block.
                        ALSO: audit upsert constraints (DriverAutoRepair,
                        DriverProposalRejection, EquivalenceToken, VocabToken).
                        (E21 Final.md §8 migration is Day 0 precondition,
                        NOT Day 5b — v4-10 dedup correction. v6-3: §7 stays
                        free-form per E30, NOT in E21 scope.)
Day 6-7 Smoke + tests  Per-lever tests (§7.1) + end-to-end smoke (§7.2)
```

Total estimated effort post-spec-lock: **7-9 working days** (v3-11 honest correction; was 6-8 in v2 but Day 5 was overloaded with SKILL.md + orchestrator + Final.md + audit-table work; split into 5a + 5b). Lever #1+#2+#3 add **~250-350 impl LOC + ~200-300 test LOC** on top of the ~1,980 LOC baseline (v3-10 corrected from v2's ~150 LOC which excluded tests and underestimated the 9-fix refinements + v3 architecture cleanup).

---

## §10. Bottom line for the user

**Top 3 levers (independently verified, beyond reasonable doubt for the 96-98% target):**

1. Writer-side auto-repair wrapper (canonicalize stays pure)
2. Unified Neo4j EquivalenceToken store with promotion-after-N-evidence gate
3. Driver-only informed retry mirroring existing learner H2 pattern

**Plus mandatory precondition (v6-3 corrected)**: E21 Final.md §8 schema migration only — §7 stays free-form per E30 (predictor is consumer-only; its key_drivers[] is analysis prose, not canonical drivers). Only §8 (learner) currently fights the ontology.

**Plus two small supporting edits**: SKILL.md anti-pattern checklist (zero code) + audit telemetry tables (`:DriverAutoRepair`, `:DriverProposalRejection`) for continuous improvement signal.

**Simplification (refined post-v5-5 + v6-4)**: three growth patterns, not five (see §5). Pattern A1 (`:VocabToken` per E10) appends slot-vocab tokens IMMEDIATELY after accepted Driver creation — no promotion gate. Pattern A2 (`:EquivalenceToken{kind: synonym|plural|acronym}`) uses N=2 distinct-event promotion gate (one-LLM-mistake protection on transforms). Pattern B (shortcuts) uses direct `:Driver` row registration via `is_shortcut=true`. The asymmetry is intentional: slot tokens are validated in-context at Driver-write time (no extra gate needed); transform-mappings change canonicalize behavior broadly (gate needed); canonical-full-name shortcuts don't need a parallel store (registry IS the store).

**Honest projection (pending Q1 measurement, v3-12)**: ~96-98% clean-landing after 8 quarters. Not 99% — the last 1-2pp lives in genuine tail cases that don't have clean repair patterns. These numbers are PROJECTIONS derived from estimated LLM failure rates + guidance pipeline analog; they will be validated and revised against actual Q1 cohort data captured in audit tables.

**System integrity preserved** (and strengthened in v3):
- L3 (pure canonicalize) — v3-1 restored fully: canonicalize takes vocab snapshot as parameter; no DB reads inside the pure function. Determinism guaranteed.
- L4 (no runtime human) — intact. Promotion threshold N=2 is hardcoded code-time constant (v3-14), not env-tunable. Self-heal does not require seed edits (v3 §4.2 clarified).
- L5 (Neo4j authoritative) — intact + extended. EquivalenceToken store grows authoritatively; markdown is bootstrap-only.
- L6 (PIT visibility) — **FULLY ALIGNED across all 3 stores after v10**: v3-1 + v4-7 + v9-1 + v10-1 + v10-2 extended. `promoted_at` is kept as wall-clock audit only and NEVER used for PIT (v5-12 corrects an earlier stale wording). The L6 source-pit-anchored visibility rule (analog of `Driver.registry_visible_at = MIN(DC.pit_cutoff)`) now applies symmetrically across all three live token stores:
   - **Driver** (E5): `registry_visible_at = MIN(DC.pit_cutoff)`, MIN-backdate on every new DC
   - **VocabToken** (v9-1 + v10-1): `vocab_visible_at = source_driver.registry_visible_at` on CREATE; ON MATCH MIN-backdate via `MIN(existing, $source_pit)`. Closes L6 leak via slot-vocab path AND the out-of-order under-visibility scenario v9-1 alone left open.
   - **EquivalenceToken** (v4-7 + v10-2): `equivalence_visible_at = sort(observation_pit_cutoffs)[N-1]` set at promotion; ON every subsequent observation re-evaluated — if `sort(new_pit_cutoffs)[N-1] < et.equivalence_visible_at`, BACKDATES. Closes the under-visibility scenario v4-7 alone left open when out-of-order observations arrive post-promotion.
   v10 reverses the prior X3 deferral and v9-1's "set-once" Phase-1 limitation by recognizing that E30 does NOT lock chronological backfill order; the backdate fix is a single CASE expression per store, mirroring Driver.registry_visible_at exactly. No new mechanism — pure L6 strict alignment.

**Bloat (v3-10 + E30 honest)**: net +**~250-350 impl LOC + ~30 lines Cypher + ~30 SKILL.md lines (earnings-learner only, per E30 — was ~60 across both skills in pre-E30 estimate) + ~200-300 test LOC** on top of the CombinedPlan baseline. Larger than v2's stated ~150 LOC because v2 excluded tests and underestimated the architecture cleanup; E30 then halved the SKILL.md portion. Still minimal vs the ~1,980 LOC baseline — additions are ~15-20% on top.

**Timeline (v3-11 + v4-10 + v6-3 honest)**: 7-9 working days post-spec-lock. Day 0 = E21 Final.md **§8-only** migration (PRECONDITION blocker; §7 stays free-form per E30). Day 5 pre-split into 5a (earnings-learner SKILL.md edits per E30) + 5b (orchestrator retry + audit upsert constraints). Final.md edits live at Day 0, NOT Day 5b (v4-10 dedup correction).
