# K-pairs protocol — v1 (EXP-0 grader qualification key)

**Status:** DRAFT for Fable finalization. This protocol is written and **sha256-pinned BEFORE any pair is drafted** (Fable v1.8 route). The pairs in `K-pairs.v1.jsonl` are drafted against *this* text; the pin is recorded in `K-pairs.v1.lock.json.protocol_sha256`. A locked key + protocol pair is immutable (WorkOrder §1.4); corrections require a new version.

## 0. Purpose
K-pairs is the calibration key for **EXP-0 — grader qualification**. Before the LLM grader tier is trusted to score every downstream experiment, it must prove on this key that it separates *genuinely different* business drivers from *genuinely same* ones. v1 = the **planted** subset only (v2 adds ~90 mined pairs, locks before EXP-4A).

## 1. Common WP-KEYS protocol (restated)
1. **Draft** — the strong tier proposes records following this protocol (here: hand-drafted 0-LLM via `harness/build_kpairs_v1.py`, a deterministic emitter; no grader/LLM calls).
2. **Lint** — `harness/key_lint.py lint` validates schema + strata quotas + **anti-tell** (below). A key that does not lint clean cannot be locked.
3. **Adjudicate** — **Fable adjudicates EVERY record** (main session). Hard calls are double-adjudicated; unresolved splits become `exhibits/ra_*.json`. Adjudication is recorded in the **sidecar**, never in the grader-visible key.
4. **Lock** — `harness/sha_lock.py lock` writes `K-pairs.v1.lock.json` (`locked_by: fable`) = sha256(key bytes) + sha256(protocol) + strata. The runner verifies the sha before the first grader call; the scorer re-verifies; mismatch = abort.

## 2. Record schema (`kp_` records, grader-visible key)
```jsonc
{"pair_id":"kp_0001","provenance":"planted",
 "family":"<one of the 13 families §4>",
 "side_a":{"name":"...","quotes":["<>=1 realistic filing-language quote>"],"slice_tokens":[],"per_x":null,"industry":"...","fact_type":null},
 "side_b":{ ... },
 "rival":null,
 "gold":"SAME|DIFFERENT","gold_rationale":"<1-2 sentences>","hard":false}
```
- **Grader-visible fields are ONLY** `side_*.{name,quotes,slice_tokens,per_x,industry}`. Everything else (`gold`, `gold_rationale`, `family`, `provenance`, `rival`, `hard`) is stripped by `key_lint.py blind` — the single blindness choke point (kernel §9 smoke-alarm doctrine). The grader NEVER sees the answer, the family, or any provenance.
- **Source references live ONLY in the sidecar** (`K-pairs.v1.sidecar.jsonl`), never in the key — a source id is itself a tell.

## 3. Adjudication sidecar (`K-pairs.v1.sidecar.jsonl`, NOT grader-visible)
```jsonc
{"pair_id":"kp_0001","source_ref":"<corpus ticker/doc or 'synthetic-realistic'>","grounding":"real|synthetic",
 "drafter_gold":"SAME|DIFFERENT","drafter_rationale":"...","hard":false,"tell_control":"<why this pair does not leak>",
 "fable":{"status":"open","verdict":null,"note":null}}   // Fable fills verdict∈{confirmed,flipped,reworded,dropped}, status→closed
```

## 4. Families (13) and strata (EXACT)
- **110 planted-DIFFERENT** across the **12 different-capable families**, **≥8 per family**:
  `bookings_billings · adjusted_vs_gaap · gross_net · segment_consolidated · deferred_recognized · genus_species · benchmark_siblings · cause_consequence · channel_homonym · ownership_axis · per_x · cross_flavor`.
- **50 planted-SAME** in family `synonym` (the 13th family), **which MUST include hard SAME** — same underlying driver expressed in *different vocabulary* (low lexical overlap), not only easy near-string synonyms.
- (`mined` is v2-only; forbidden in v1.)

## 5. Quote sourcing
Prefer **real corpus language** from the 12 Phase-1 companies (AAL·AZO·BBY·CAKE·CMG·DAL·DRI·LUV·MCD·ORLY·ULTA·YUM — restaurants/airlines/retail/auto-parts). Planted quotes MAY be **synthetic-but-realistic** filing language (calibration plants, kernel §9.6). Grounding (`real|synthetic`) is recorded in the sidecar. Named real clusters to prefer: AZO↔ORLY comparable-store-sales; multi-brand system-sales; the homonyms *traffic* (guest count / store foot-traffic / RPMs), *capacity* (seats / ASMs / DC throughput), *yield*, *unit* (store / per-ASM), *comps*.

## 6. The grader instrument (prompt contract — byte-identical across arms)
Input = the two sides RAW only (§2). Framing (kernel §10.3 recovery-grader + PIPE-13 Refute): **default-DIFFERENT** — treat as different unless the evidence compels sameness; over-merge is permanent, over-split is cheap. Decide via the **3-check**, each backed by a **verbatim quote from EACH side**:
1. same **OBJECT** — the same underlying thing/metric.
2. same **SCOPE** — same business population AND ownership class (company-owned vs franchised, segment vs consolidated, gross vs net).
3. same **MECHANISM** — the same causal driver, not a correlated or downstream effect.
Any one false/unclear → DIFFERENT. **Unclear means CONFLICT, not silence (O10 pin, 2026-07-09):** a check is unclear when the two sides conflict or one side carries a qualifier the other lacks (a segment, an ownership class, a sub-channel, a different denominator). When BOTH sides are symmetrically silent on a dimension, that silence is NOT evidence against sameness. Likewise, a sub-reason or color explaining WHY the same quantity moved (a price move, a demand source, an offsetting mix effect) is not a different MECHANISM; mechanism differs only when the sides measure different quantities or different causal positions. Default-DIFFERENT still governs whenever the sides genuinely conflict or the OBJECT itself is not the same thing. Output: `{pair_id, verdict:SAME|DIFFERENT, cited_a, cited_b, reason(≤60w)}`.

## 7. Anti-tell (no surface-stat leaks) — enforced by `key_lint.py`
The visible fields MUST NOT let a shallow model separate SAME from DIFFERENT without reasoning. `key_lint.py` fails the key if any single surface feature separates the classes beyond tolerance:
- **Lexical overlap** (Jaccard of name+quote tokens between sides): must NOT predict gold — DIFFERENT includes high-overlap traps (e.g. *bookings* vs *billings*) AND SAME includes **low-overlap hard cases**; class AUC must be near 0.5.
- **Quote length** (total chars, and |len_a−len_b|): near-balanced across classes.
- **Digit/percent presence**, **per_x present**, **slice present**, **industry**, **exact name equality**: no value may be class-pure above a support floor. Note *channel_homonym* deliberately makes identical/near names → DIFFERENT, defeating "same name ⇒ SAME."
- Separation metric = `2·|AUC−0.5|` (numeric) / class-rate deviation (categorical); thresholds in `key_lint.py` (defaults: numeric ≤0.40, categorical ≤0.30 above support 10, hard-SAME ≥12 with overlap ≤0.34).

## 8. Gate (EXP-0, for reference — scored by `score_exp0.py`)
A tier T qualifies iff for every instance `g∈T`: `wrong_same(g)==0/110` AND `false_refusal(g)≤10%/50` AND `invalid_rate(g)≤0.02`. Sonnet tier = both instances (`g_sonnet_a`,`g_sonnet_b`); Opus = its one. Any `shared_miss` on a family (both sonnet instances wrong-SAME) ⇒ generation-blindness flag + discount + kernel §14.2 escalation. **O10:** Fable ratifies the qualified tier + records per-family blindness discounts.

## 9. Fable sign-off (filled at lock)
```
locked_by: fable   locked_at: <iso>   protocol_sha256: <this file>   key_sha256: <K-pairs.v1.jsonl>
records_adjudicated: <n>/160   flipped: <n>   reworded: <n>   dropped: <n>   ra_exhibits: [ ... ]
```

## 10. v1.1 addendum (owner-directed second adjudication pass, 2026-07-09 - pre-first-use supersession)
v1 was locked, then the owner directed a doubled-attention realism pass BEFORE any grader call ran. Per WorkOrder 1.4 immutability, **v1 stays byte-frozen**; **K-pairs.v1.1.jsonl supersedes it pre-first-use** under a fresh Fable lock. EXP-0 consumes v1.1. Changes (all golds unchanged; every record re-derived adversarially; key_lint re-run clean):
1. **Canonical names** - all sides + rivals converted to lowercase_underscore canon (297 sides renamed), matching what readers and catalog cards actually emit (NAME-01..19). Grader qualification now transfers to real snake_case inputs instead of prose names.
2. **Realism surface** - 24 records (15 DIFFERENT / 9 SAME, class-proportional) gained a second corroborating quote per side; 12 carry realistic numerics (digit AUC 0.5009 post-change - perfectly class-balanced); quote-length totals class-balanced (135.5 vs 135.7 mean chars).
3. **Two decisiveness sharpenings** from the adversarial pass: kp_0137 (return_on_sales quote now pins the OPERATING numerator - the ROS-vs-net-income ambiguity invited a fair refusal against a SAME gold) and kp_0152 (unit_revenue quote now pins passenger fares - PRASM/TRASM ambiguity removed).
4. kp_0118 (cross-company convergence SAME, identical names) is retained deliberately as a doctrine probe: if both Sonnet instances refuse it, that is a real generation-blindness signal on PIPE-20 convergence, not key noise - budget one potential refusal for it.

## 11. v1.2 addendum (O10 instrument corrections after the first EXP-0 run, 2026-07-09)
EXP-0 run 2026-07-09T20-31-24Z FAILED on false_refusal only (wrong_same 0/110 and invalid 0 on every arm). Fable's O10 re-adjudication found the failures instrument-sided, in two classes. (1) **Eight all-three-refused pairs**: 4 had quote-authorship defects on true-synonym name pairs (kp_0141/0143/0155/0157 - quotes SHARPENED, golds unchanged) and 4 were arguable-both-ways (kp_0132/0151/0154/0160 - REPLACED with fresh decisive hard-SAMEs never seen by any arm). (2) **The section-6 contract left 'unclear' undefined**, and the literal reading (symmetric silence on scope = unclear = DIFFERENT) is unsatisfiable in principle on snippet records - it rejected even net_sales vs total_net_sales. The 'unclear means conflict' pin above fixes the semantics without touching default-DIFFERENT. **No gold was flipped; no bar changed; the package recommendation to re-label pairs so a tier passes was REJECTED as retune-to-pass.** Tiers must re-earn the bar on v1.2 in a fresh run with reasoning effort explicitly pinned in the manifest (the first run left it unset - recorded execution gap). ra_0007 documents the contract defect; the same silence-vs-conflict semantics must be reviewed against the EXP-4 judge contract (kernel 6.1) before K-pairs.v2 locks.
