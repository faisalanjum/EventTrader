# C1 — Fold Re-review Inheritance: Deep Study (PRE-BUILD — nothing coded)

**Date:** 2026-06-11 · **Method:** 10-agent adversarial workflow `wf_c67c4aa9-c4d` (5 code mappers → 3 designers → 2 skeptics; ~1.33M tokens; every load-bearing claim re-verified line-by-line against the workflows code + real run artifacts) · **Status: STUDY ONLY.** This file is the MERGED spec — where the designers disagreed, the skeptics arbitrated and this document records the winning rule.

---

## 1. What C1 is, in plain words

Today, when industry catalogs get folded into a sector catalog (and sectors into the global one), **every record is re-judged from scratch at every level** — the full dedup + gate + refute pipeline re-runs identically (verified: `build_tree.js` calls `reconcile.js` with only `{run_id}`; reconcile has zero fold-awareness). A record like `oil_price` that one industry coined, that collides with nothing, and that arrives at the sector byte-for-byte unchanged, still gets a fresh gate judgment at sector AND again at global.

C1's idea: **if pure code can PROVE a record is exactly what a validated child already judged, skip only the gate re-judgment** (admit verdict carries up with provenance). **Dedup is NEVER skipped** — finding cross-industry duplicates is the whole purpose of fold-level dedup. Refute, refute2, D5, repair: all untouched.

```
Today:    leaf gate ✓ → sector: dedup + GATE + refute (all fresh) → global: dedup + GATE + refute (all fresh)
With C1:  leaf gate ✓ → sector: dedup + refute fresh, GATE inherited-if-proven → global: re-gate (depth cap)
```

## 2. The honest numbers (the ledger's 50–70% claim is WRONG — restated)

Measured anatomy of one parent reconcile pass (real CAKE shape, 594 records, 3 batches ≈ 1.28M tokens):

| Lane | Tokens | C1 effect |
|---|---|---|
| Dedup (full batch reads + verdicts) | ~278k | untouched (byte-identical by construction) |
| **Gate (full batch reads + verdicts)** | **~297k** | **the only lane C1 cuts** |
| Refute (full batch reads) | ~281k | untouched (kept full-file deliberately) |
| D5 lane + assemble + clerks | ~425k | assemble shrinks ~77%-of-decisions share |

- Defensible saving = **N × ~21–33% of each parent reconcile pass** (N = fraction of records provably unchanged — **UNMEASURED at any real fold**; synth folds gave 50%/87% on 6–7 records).
- As a share of TOTAL fold-level spend: **~5–22%** (5% if the repair pass dominates — 529 pre-limit candidates were measured at ONE single-company leaf vs the JS clip of 200).
- **Zero wall-clock saving** (dedup reads the same batches in parallel anyway) — this buys 5-hour-window headroom, not latency.
- The 50–70% figure reproduces ONLY against the narrow "dedup+gate batch-read pair" base, not fold spend. CostCutting.md row C1 is restated accordingly.
- **Mandatory first step (free): `--measure-inherit`** — a pure-observation flag that measures N + repair-candidate load on the first real sector fold with zero pipeline change. The GO/NO-GO ROI decision is made on that number, pre-registered threshold: projected horizon saving (incl. refresh cycles + all gate/oracle overheads) > 3× total gate cost.

## 3. How the fold actually works (verified facts the rule rests on)

1. `runFold` per level: `fold_catalogs.js` (part-a → D5 same-name review → part-b) → `reconcile.js` (FULL) → `repair_duplicates.js` → `validate --fold` (D8). Identical at sector and global.
2. part-a: every cross-child name with **exactly 1 owner = passthrough** (record carried as `dict(r)` of the child's collapsed rep); **≥2 owners = queue** → D5 review (SAME union / DIFFERENT split / UNCLEAR park).
3. `collapse_child` resolves each child's SAME_AS clusters into self-canonical reps (absorbing variant evidence) BEFORE classification — so "unchanged" must be defined against the checker's own recomputed rep, not raw child bytes (46% of real records differ from raw bytes on ref order alone; 185/573 are cluster reps).
4. Dedup, gate, refute, blast-count, refute2 ALL read the SAME batch file (`${bf}`) — so C1 requires a second, gate-only file set; the dedup set must stay byte-identical.
5. Child catalogs contain ONLY kept (admitted) records — skips/parks/rewrites never travel. So the only inheritable verdict is **admit**, structurally.
6. `validate_catalog.py` never reads decisions.json; the sidecar binds only catalog+approved shas → child decisions.json is currently UNBOUND (matters for provenance — see §4 P5').
7. No resume exists at fold levels: any abort re-pays the whole fold (a C1 false-stop is expensive — every new hard-fail must be pre-tested).

## 4. The inheritance rule (merged predicate — pure code, zero AI judgment)

A parent-seed record R may inherit `admit` iff ALL of:

| # | Condition | Why |
|---|---|---|
| E0 | Every child passes `require_validated` (sidecar exit==0, shas match, fold-mode for fold parents) — failure ABORTS the fold, never demotes to re-gate | demotion would launder tamper |
| E1 | R's name occurs as a rep name in EXACTLY ONE child (no cross-child collision, even byte-identical ones) | collisions are the D5 lane's property |
| E2 | Singleton cluster: no other child record resolves into R's rep (cluster size 1) | a rep with absorbed variants carries union evidence the child gate never judged under that name (the 185/573 class = OUT in v1; opt-in "N2" only behind its own A/B) |
| E3 | R dict-equals the checker's OWN `collapse_child` output (full structural equality, all 6 fields) | recompute-the-transform-then-compare-exactly; never trust fold_passthrough/fold_queue files as proof |
| E4 | Permutation proof vs the RAW child record: same ref count (no silent key5-dup drops), string-identical companies/variants/links, order-only deltas | catches silent shrink/mutation that set-equality tolerates |
| **E5** | **norm(name) ∈ the child's own seed.json names** (sha-bound) | **kills skeptic-KILL A1: D5-split coined targets are non-seed names judged only by a names-only mini-gate (zero evidence read) — 6 such records exist in the real CAKE catalog TODAY; they must never inherit** |
| E6 | Depth ≤ 1 (depth field carried per row): leaf-fresh admits may skip the sector gate; everything inherited at sector is RE-GATED at global | the flip risk is maximal at global; raising to 2 requires a passed depth-2 oracle arm |
| E7 | Drift stamp match: child's `validation_exit.json` carries ontology-sha + workflows-commit + judge-model id equal to the parent run's current stamp | gate semantics live in prompts/ontology and WILL evolve; mismatch → automatic re-gate (semantic cache-bust), never silent grandfathering |
| E8 | Name untouched by parent non-SAME D5 review; claimed set disjoint from fresh gate verdicts; claimed ⊆ parent seed names; 1:1 bijection | a fresh verdict naming an inherited record = hallucination/corruption → hard fail |

Edge rulings (all OUT, fail-close): D5 unions/splits/parks, child skips/parked rewrites (structurally absent), duplicate gate rows, rewrite-target-skipped records (child verdict was REWRITE, not admit — excluded once decisions.json is sha-bound), stale sidecars (ABORT), ""→None or case mutations (E4). IN: KPI-only evidence (content-identity rule; excluding by source_type would be code making a semantic call — A/B stratifies instead); evidence re-SORTING alone (shared with today's baseline, A/B-neutral).

## 5. What could go wrong — the ranked catalog (21 failure modes + 11 skeptic attacks; full detail in the study transcript)

**CATASTROPHIC (all killed by construction in the merged spec):**
- F1/F4 dedup view shrinkage / silently dropped dedup batch → dedup batch files stay byte-identical (gate gets ADDITIONAL subset files, 1:1 aligned, never re-packed); slice writes a batch MANIFEST (file list + shas) — all partition checks verify against it, never glob.
- F2 refute repointed to the reduced file → refute/blast/refute2 pinned to the FULL file (forgoes their saving deliberately).
- F3 gate-coverage weakening → the Stage-0 #3 check stays presence-based; the PROOF moves into code (assemble recomputes eligibility itself; names failing both fresh-verdict and proven-inheritance still hard-fail).
- F5 relay-fabricated inheritance → relays carry only run_ids; assemble + validator independently recompute the whole derivation from sha-bound bytes (ONE predicate implementation, three enforcement points: slice partition / assemble coverage+disjointness+gate-batch cross-check / validator final recompute).

**INTEGRITY (bounded by the A/B + guards):**
- F6 the named risk — parent context legitimately flips a leaf admit. Concrete flip classes: industry-vague single-child names (`traffic`, `volume`, `mix`, `capacity`… — the LONG TAIL that dominates passthroughs at 1000-industry scale), borderline instance-names, lost cross-child naming convergence. Direction note: flips ship UNDER-specified names, not over-merges (dedup+refute still guard fusion) — integrity, not catastrophic.
- F7 D5-trigger halving (gate's mixed_flags channel disappears for inherited records; only dedup can flag them) → A/B must diff D5 FLAG SETS, not just verdicts.
- F8 rewrite-target universe shrinkage (a fresh record's correct rewrite_to is an inherited name it can no longer see) → measured in the A/B; candidate mitigation (names-only appendix in gate batches) is itself a judge-input change.
- F9 batch composition/anchoring shifts for the REMAINING fresh records → aligned-subset batches eliminate boundary shift by construction; residual composition effect lives inside the A/B with a baseline-vs-baseline noise floor.
- F10 cluster-rep class (185/573) → OUT in v1 (semantic call), separate gate if ever wanted.
- F11/F12 drift + multi-hop staleness → E6 depth cap + E7 stamp.
- F13 stale artifacts on manual run-dir reuse → recompute everything from current bytes per run; mode transitions delete stale files; repair re-injection keyed on the pre-repair approved.json state (NOT artifact presence — kills skeptic A5's false-provenance scenario).
- **F14 scale extrapolation — calibration CANNOT prove production safety**: a 0-flip pass at n≈600 bounds the flip rate only at ≤0.5%; a production global inherits ~10⁵ records → hundreds of wrong records at a true 0.3% rate. Guards: sector-only rollout first (global re-gates), permanent 1–2% sampled oracle re-gate per production fold with alert-on-flip, retrieval-exposure audit at the honesty gate (a vague inherited name is a reuse ATTRACTOR in §13.1 live flow — flip cost compounds multiplicatively).
- **§13.4 batch-refresh regime (skeptic-KILL: nobody had analyzed it)**: quarterly refresh = fold(existing, delta) where N≈1.0 forever and eligibility decays with every repair link. **C1's GO is scoped to the one-time build-out walk ONLY; refresh folds are EXCLUDED pending their own gate**; an explicit fold-kind flag prevents the rollout switch from silently covering refresh merges.

**COST-ONLY:** empty-gate-batch crash (explicit no-spawn branch + N=1.0 multi-batch synth test), savings overstatement (§2), repair dilution (separate fix: raise/fail-on-clip the 200-pair limit at fold levels — kept OUT of C1's diff), zero wall-clock.

## 6. The minimal reliable build (merged spec — ~350 LOC + ~45 tests across 6 files; NOT built)

- `slice_seed.py --inherit` (~120 LOC): computes the predicate (imports `require_validated` + `collapse_child`), writes `inherit_manifest.json` + aligned `gate_batch_NNN.json` subsets + batch manifest; `--measure-inherit` = counts only, zero judge impact. OFF mode = byte-identical outputs (golden-file regression).
- `assemble_catalog.py --inherit` (~90 LOC): `compute_inherited()` re-derives everything from disk (manifest is coordination, never proof); gate-batch cross-check; disjointness hard-fail (with a JS pre-filter dropping hallucinated gate rows naming never-shown records, so noise can't abort a multi-M-token fold); coverage = fresh ⊎ inherited ⊎ reshaped-review, pairwise disjoint; writes `approved.json["inherited_admits"]` (sha-bound, repair-preserved) with per-row provenance {name, child_run_id, child shas, depth, origin run, reason copy, predicate_version}.
- `validate_catalog.py` inherit lane (~80 LOC): full independent recompute; **I4 = claimed name accounted in the parent catalog as self-canonical OR D1-reachable via approved links** (the skeptics' #1 kill: the self-canonical-only version aborts every fold where dedup correctly fuses an inherited record — the most expected fold event); sidecar extended with decisions/review/inherited shas + the E7 drift stamp.
- `repair_duplicates.py` (~10 LOC): re-inject inherited_admits on apply, keyed on pre-repair approved.json state.
- `reconcile.js` (~25 LOC): threads `--inherit`, gate prompt interpolates the subset file (OFF: `gf===bf`, prompt character-identical — the A/B baseline arm is byte-stable), explicit null-gate-batch no-spawn branch.
- `build_tree.js` (~6 LOC): threads `fold.inherit/walk.inherit` + the fold-kind flag.
- Kill-switch: code default OFF permanently; ON only via explicit per-run args. Narrowing ladder: OFF → singleton-admits-only sector-folds (default) → +global (only after depth-2 oracle) → cluster-reps (separate A/B, likely never).
- Fail-close inventory: every relay degradation (dropped flag, invented flag, drift, tamper, partition mismatch) lands on SystemExit or silent-full-re-gate — never a silent skip.

## 7. The A/B gate (build comes AFTER owner reads this; A/B after build)

**The skeptics' second kill: the obvious fixture (split CAKE into two pseudo-children) is a false-GO machine** — same-industry children mean the parent context equals the leaf context, so the named risk (scope flips) can't occur BY CONSTRUCTION; a clean PASS would license nothing. The decisive gate therefore runs on **the first REAL 2-industry fold** (already scheduled on the §13.6 roadmap before production GO) — hardest available data, near-zero extra cost.

Protocol (pre-registered): baseline ×2 + variant ×2 on the frozen real fold (~6M tokens, fresh 5-hour window, repair suggest-only) + an **oracle side-lane** (re-gate ALL inherited records in measurement-only batches; output discarded) + ~12 planted baits (cross-industry vague names like `traffic` vs `web_traffic` with foreign-domain quotes, mixed-meaning singletons, rewrite-target baits, collision controls) + a depth-2/global arm before any cap raise. Deterministic differ, zero LLM: R1 merge-direction novelty = zero tolerance · R2 inherited-override flips (non-admit in both baselines) = FAIL → narrow or reject · R3 D5-flag-set loss = FAIL/narrow · R4 under-merge novelty ≤ baseline self-disagreement floor · R5 construction proofs (dedup inputs byte-identical across all 4 runs) · R6 full catalog diff + per-bait scorecard. A bait flipping in both baselines is the gate WORKING — the answer is narrow/reject, never prompt-tuning retries.

## 8. Sequencing + owner decisions

```
0. --measure-inherit on the first real sector fold  (FREE — settles N + repair load; ROI go/no-go)
1. Build plumbing, default-OFF (TDD, golden-file OFF-identity)        ← no judge spend
2. Synth-fold plumbing smoke (inherit:true on synth children)          ← small spend
3. Decisive A/B on the first real 2-industry fold + oracle lane        ← ~6M tokens
4. Owner GO → sector-only production, global re-gates, 1–2% sampled audit forever
```
Owner decisions needed before build: (O1) approve the predicate as specified (esp. E5 seed-membership, E6 depth-1, E7 stamp = validator-semantics changes); (O2) approve sector-only scope + refresh exclusion; (O3) approve the A/B protocol (repair suggest-only deviation); (O4) the CostCutting C1 row restatement (done); (O5) the separate repair-clip fix.

## 9. Side-discoveries (independent of C1)

1. **6 records in the real CAKE catalog were NEVER evidence-gated** (D5-split coined targets judged only by the names-only mini-G2: `food_beverage_cogs`, `new_restaurant_food_cost_efficiency`, `cash_capital_expenditure_guidance`, `restaurant_capital_expenditures`, `board_share_repurchase_authorization`, `shares_repurchased`) — a baseline finding for the Focus-1 list, and the reason E5 exists.
2. Fold-level repair runs at the JS default limit 200 vs 529 pre-limit candidates measured at ONE single-company leaf — the clip is silent-loud at exactly the level where cross-industry duplicates concentrate. Recommend a small separate fix.
3. The 005333 calibration run predates the current reconcile shape (decisions.json lacks the high_blast_refute2 key) — its artifacts cannot serve as an A/B baseline arm; baselines must be regenerated.
4. The "529 repair candidates" §0 ledger figure is transcript-derived; no on-disk artifact exists (repair never ran on the real leaf dir) — treat repair load as UNMEASURED.

## Provenance
Study run `wf_c67c4aa9-c4d` (10 agents, ~1.33M tokens, 2026-06-11); raw output `/tmp/.../wefmaahn0.output` (ephemeral — THIS FILE is the durable record). Every load-bearing code claim verified against `workflows/{build_tree,reconcile,fold_catalogs,menu_build,repair_duplicates}.js`, `{slice_seed,fold_catalogs,assemble_catalog,validate_catalog,repair_duplicates}.py` + real artifacts under `runs/` at the post-final-gate state. Skeptic #2 re-verified the 5 most load-bearing map claims line-by-line: all confirmed.
