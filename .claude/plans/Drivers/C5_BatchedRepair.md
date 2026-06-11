# C5 — Batched Repair Pair-Reviews: Deep Study + Dormant Build

**Date:** 2026-06-11 · **Method:** 9-agent adversarial workflow `wf_7c2d3a58-7f7` (4 mappers → 3 designers → 2 skeptics, ~0.89M tokens; the real candidate set was REGENERATED from the actual CAKE catalog with the real `suggest()` code — artifact at `/tmp/m2_cake/repair_candidates.json`, reproducible any time). **Status: BUILT 2026-06-11 (owner-approved ②+③), DORMANT** — `batch_size` defaults to 1 = today's per-pair path byte-identical (prompts moved verbatim into shared templates used by both lanes); the batched PROPOSER + blind per-pair CONFIRM lane ships behind explicit `args.batch_size>1` and stays out of production until the §8 A/B passes (owner decision ④ pending). TDD: suite 218 passed + 1 opt-in skip (17 new tests). LIVE SMOKE PASSED TWICE on a synthetic 6-pair fixture through the SHIPPED workflow (run 2 = round-4 fixes: SLIM suggest relay + batched no-cap default limit=0 + clipped>0 hard-fail; final catalog byte-identical across both runs): 3 hard-disjoint batches → 1 planted true-SAME proposed → blind confirm agreed → applied → genuine validator pass; the 5 distinct pairs correctly DIFFERENT/UNCLEAR; full P2 plan-vs-review enforcement on disk. This file remains the spec of record; skeptic arbitrations and owner decisions are marked.

---

## 1. What C5 is, in plain words

The repair pass (required at every leaf and every fold) has code suggest candidate duplicate pairs, then spawns **one judge agent per pair**. The judge's payload is tiny (~280 tokens = 1.1% of its cost); the other ~51.3k tokens are fixed spin-up. C5: give each judge **k≈10 pairs** in one context, amortizing the spin-up. Payload per pair unchanged; the meaning rule unchanged; the ≥8-company second skeptic stays per-pair.

## 2. Measured facts (regenerated + transcript-mined, not estimates)

| Fact | Measured value |
|---|---|
| TRUE candidates at the real CAKE leaf | **529** (token-overlap only; the old "529" figure now has an artifact) |
| Today's default limit=200 | **329 pairs (62%) silently never judged** — the clip lives in the JS default; build_tree passes no limit |
| Per-pair judge cost | ~52.6k token-events, **~51.3k fixed** (payload ~1.1%) — 3 real transcripts agree |
| k=10 batching | 52.6k → **6.4k per pair (−88%)** |
| Per leaf | today 10.5M (with the 62% hole) → **k=10 at limit 600: 3.4M with FULL 529-pair coverage** = 68% cheaper AND 2.65× coverage |
| 1000-industry projection | ~7.1B tokens saved vs today; ~24.4B vs unclipped per-pair |
| Anchoring raw material | **63.8% of adjacent ranked pairs share a full record name**; streaks up to 10; 25 streaks ≥5 — the similarity-ranked order is maximally anchoring-prone |
| Batch-judging empirical prior | The real CAKE reconcile's whole-batch dedup judge proposed 188 SAME links; the independent refute killed **6 (3.2% — 30× the 0.1% budget)** and 1 of 94 verdict rows was dropped. Batch merge-judging measurably needs an absorber; row loss is real |

## 3. The load-bearing safety fact

A repair SAME on a pair spanning <8 companies is **terminal** — no skeptic follows it (unlike reconcile's dedup, whose proposals all pass an independent refute). The honest system invariant is: **every n<8 merge decision today involves two independent agents** (proposer + skeptic) *or* total per-pair isolation. Naive batching would uniquely break that. Links are permanent (`already_linked` excludes them from all future suggests; §13.4 refresh compounds quarterly).

## 4. LIVE TODAY-BUGS found by the study (independent of C5 — fix regardless)

1. **The suggest relay returns the ENTIRE candidates JSON via structured output.** At a real leaf (200 candidates ≈ 417k chars ≈ ~104k tokens) this either crashes (repair cannot run at real scale at all — it has only ever run with 3 smoke candidates) or, worse, an abridging relay returns valid-but-shortened JSON: `SUGGEST_SCHEMA` never asserts `candidates.length === count`, and the review fan-out consumes the relay copy, never the disk file → pairs silently never judged, all existing checks pass. Minimum fix (Stage-0 class): one-line JS length-vs-count assert + a python disk-side exact-set check (review rows == on-disk candidates, multiset) + the C6 suggest-slim (relay returns counts only; judges load pairs from disk) before any real-scale repair.
2. The 200 clip itself: 62% of real candidates never judged today, silently-loudly. The batched limit-raise (k=10 @ 600) fixes coverage AND cost together.

## 5. What could go wrong with batching — the kill list (all guards mandatory)

| # | Attack (proven mechanism) | Guard |
|---|---|---|
| K1 | **The A/B's zero-tolerance rule exempts contested pairs** — anchoring doesn't flip clear pairs, it shifts marginal ones, which are exactly the pairs the two baselines disagree on; the gate as templated records zero novelty and false-GOs | Pre-registered DIRECTIONAL criterion on the contested stratum (variant SAME-rate on baseline-disagreed pairs ≤ pooled baseline rate, one-sided binomial) + a degenerate-floor rule |
| K2 | **Gate population ≠ production population**: production repair runs ONLY at folds (cross-industry, multi-company, embeddings-on); the leaf census licenses nothing about folds; a 10% canary has ~0.3 expected catches | A second census gate on a fold-profile fixture before any fold enable; canary demoted to monitoring |
| K3 | **Best-effort record-disjointness re-opens transitive chaining**: a record with degree > batch count forces same-record co-batching → halo SAME chains → `_star()` flattens them into one multi-record over-merge invisible to every code check | Record-disjointness HARD: overflow pairs go to the per-pair lane, never log-and-proceed; degree-vs-batch assert at composition |
| K4 | **The statistics can't reach the budget**: a clean 1,058-judgment census bounds the flip rate at ~0.28–0.57% = 3–6× the 0.1% budget. No A/B size we can afford certifies the terminal merge direction | **P4 — the architecture decision (see §6)** |
| K5 | Quote-echo verifies quote provenance, not reasoning provenance — an anchored judge quotes correctly from its assigned pair while judging it wrong; no code check can ever bound this class | P4 again (structural, not statistical) |
| Others | One death = k verdicts (fail-close re-fan per batch); structured-output truncation at k verdicts (cap k, length checks); retry re-anchoring; canary must compare BEFORE apply (links are permanent); deterministic composition without Math.random (content-hash seeded); P2 = per-batch exact-set echo + python disk backstop | All specified in the merged design |

## 6. The architecture that survives: batched PROPOSER + per-pair CONFIRM (P4)

The failure catalog's own math says the A/B alone cannot certify the merge direction; the measured dedup precedent (188 proposed → 6 killed by the second agent) says batch merge-judging needs an absorber. So C5 ships in the same shape the system already trusts:

- **Batched judge (k=10, hard-disjoint, deterministically interleaved) = PROPOSER.** Its DIFFERENT/UNCLEAR verdicts are terminal (under-merge direction — recoverable by later repair passes; bounded by the A/B against the noise floor).
- **Every batched SAME on an n<8 pair gets ONE isolated per-pair confirmation with today's EXACT prompt before apply.** The terminal merge decision is therefore made by byte-identically the same isolated judgment as today — the catastrophic direction is protected **by construction**, not by statistics. ≥8 pairs keep the second skeptic on top (three agents).
- Economics with P4 at SAME-rate s (measured FREE from the A/B baseline arms; smoke prior 33%, expected lower at scale): s=10% → ~6.2M/leaf (−78% vs unclipped per-pair, −41% vs today-with-hole, full coverage); s=33% → ~12.6M ≈ today's cost but with full 529 coverage AND the two-agent invariant everywhere. **Never worse than today; strictly better coverage; merge direction never weaker.**

## 7. Minimal build (BUILT dormant; production enable still waits for §8 A/B)

`repair_duplicates.js`: dormant batched lane behind `args.batch_size>1`; default `batch_size=1` keeps today's per-pair path. Batched mode uses slim suggest relay (counts/hashes only), code-written batch files, hard name-disjoint batches, blind per-pair confirm for every batched SAME, and fail-close P2 checks before apply. `repair_duplicates.py`: `suggest(limit=0)` means no cap; `plan` pages all candidates from one pinned file; `show` loads confirm candidates by index; `apply` verifies stale-plan, missing-row, duplicate-row, transposed-name, and unconfirmed-SAME failures. Tests cover the dangerous cases; production enable still waits for the §8 A/B gate.

## 8. The A/B gate (after build; pre-registered)

Fixture = the regenerated REAL 529-pair set (pure code, reproducible) + ~150 placement-engineered baits (marginal pairs deliberately placed after true-SAME streaks — the hardest composition) + ≥10 planted high-blast pairs (gate-template rule 6). Protocol: per-pair baseline ×2 (noise floor + free SAME-rate measurement) vs batched ×2; cost ≈ 2×27.8M + 2×3.4M… sampled instead: stratified ~150 pairs ≈ ~16M total. Differ: K1's directional contested-stratum criterion · position-in-batch flip analysis (the anchoring smoking gun) · transposition audit · under-merge ≤ floor · P4-confirm agreement rate. Fold enable ONLY after a fold-profile census gate. The gate must run through the SHIPPED workflow path on a frozen candidates file (a `--candidates-file` pin), not a replica harness.

## 8b. Round-3 review pins (2026-06-11, owner-relayed; validated independently)

- **Relay binding is exact-set, not count-only** (was never count-only): `pairs_h32` binds the ordered pair list, `cands_h32` binds full content, and the python disk-side coverage+membership checks are the deterministic enforcement — a self-consistent forged relay still fails at apply against the code-written disk file. Residual (documented, bounded to the recoverable under-merge direction): a relay that both drops a flag AND forges the params echo; closed as far as relay-side checks can be by the params assert below.
- **Mode/limit echo (BUILT same day):** suggest() echoes `limit_used` + `use_embeddings` into the hash-protected blob; the workflow asserts they equal what it commanded — a relay-dropped flag is now loud. Embeddings-lane failures were already hard-fail (missing key = SystemExit; API error = crash), never silent.
- **Rerun pinning:** full-workflow reruns REGENERATE candidates by design (the whole chain re-runs consistently — embeddings drift is safe there); MIXED generations (old review vs new candidates) are fail-close via the coverage + membership + already_linked trio. No further pinning needed.
- **Confirm blindness (P4) — pinned:** the per-pair confirm prompt must be byte-identical to today's per-pair review prompt, which carries NO proposer verdict ("YOU decide exact meaning from evidence") — the confirm judge never learns the batch proposer said SAME.
- **Lost-merge direction — pinned:** batch-DIFFERENT-where-isolated-would-SAME = under-merge, recoverable, measured by the A/B differ (under-merge novelty ≤ baseline noise floor); already in §8.
- **Hard record-disjointness — pinned:** already K3; overflow pairs go per-pair, never co-batched.
- **OWNER DECISION ③ RESOLVED — paging, not a terminal limit:** k=10 batches; **600 = default PAGE size, page until ALL pairs are reviewed** (no terminal clip anywhere). All pages slice ONE pinned suggest output (single candidates file; pages are deterministic index ranges) — never regenerate between pages. The slim relay is built in batched mode: pages/judges load candidates from disk by index, while the relay carries counts+hashes only.

## 9. Owner decisions needed

(O1) **P4 yes/no** — recommended YES (the merge direction stays two-agent everywhere; the saving stays large). Without P4: a ~0.57%-bounded, statistically-uncertifiable residual on permanent links must be explicitly accepted in the ledger. (O2) Approve the today-bug fixes as an immediate Stage-0-class commit (independent of C5). (O3) RESOLVED — k=10, page size 600, page-until-done from one pinned candidates file (no terminal clip). (O4) The A/B budget (~16M) and the fold-profile second gate before fold enable.

## Provenance
Study `wf_7c2d3a58-7f7` (9 agents, 2026-06-11). Skeptic #2 re-verified all 5 load-bearing code claims line-by-line; 2 map errors found+corrected (repair_smoke has zero high-blast pairs; "every terminal merge judgment is per-item" is false — refute1 is multi-item, the honest invariant is two-agents-per-merge). Raw output `/tmp/.../w0oiyc8qw.output` (ephemeral — THIS FILE is the durable record).
