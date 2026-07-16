# Fable Admission Kernel Design v3.4 — LOCK CANDIDATE

> **STATUS (2026-07-07): FABLE PROPOSAL v3.4 — LOCK CANDIDATE. v3.4 = v3.3 + the applied citation-diff doc-fixes (stale-label + citation corrections; NO design content changed) + the LOCKED model-tiering rule (§11.0). Supersedes v3.3 in full; v3.3 was the LOCK CANDIDATE after the final three-auditor lock-read (run wf_42ef5242-9d9), superseding v3.2.** The lock-read verdict: the architecture stands — all six suspected contradiction pairs resolved as designed tensions, the recovery matrix complete — with TWO bounded blockers fixed in this version: **(L1)** the suffix-blind fact_type/BASE_METRIC re-derivation (the `regulatory_guidance` class) now runs as a LIVE sampled falsifier lane, not only in the seed gauntlet (§9.1-vii) — without it, a live-minted card with a deceptive suffix would stamp a wrong family and look clean forever; **(L2)** every code auto-refusal is now classified for REPAIRABILITY (§6.1) — permanent-by-locked-rule vs state-based-auto-reenqueue vs judge-territory — because "over-split is cheap ONLY IF repairable" and an auto-refusal that no judge can ever revisit must be justified by a locked rule, not by machinery. Named-series sibling pairs (Brent vs WTI) move OUT of code into the judge's fixture families (code cannot know two benchmarks differ without a curated list — the v1 pattern); only the form-decidable token-subset (species) case stays code-refused, justified by NAME-04. Plus lock-read errata: QUARANTINED nodes block exact-ATTACH (park, safe direction — the one undefined matrix cell); §8.4 features gate on BROAD ∧ the §6.5 flag guards; "write-time-final" scoped to event-level with async series-completion named; the §13.5 "wash" framing corrected (CLAIM-off is a real precision gain, not a wash); same-industry homonym heterogeneity added to the ATTACH-audit; the qualitative-homonym blindness stated as an explicit residual. **Pre-lock step for the doc-editing pass: a citation-diff of every locked-rule paraphrase against the binding topic docs — APPLIED in v3.4.** v3.2 = v3.1 + the owner's five rulings (all five independently verified and AGREED, two with strengthening amendments) + a second adversarial pass (3 agents: owner-devil's-advocate, mechanism-attacker, completeness critic — 24 findings, 4 FATAL, all dispositioned inline). **The five rulings as integrated:** (1) the model-free falsifier is a SMOKE ALARM — code surfaces form-level contradictions and may take only the REVERSIBLE protective step (signal-quarantine); the quarantine VERDICT always belongs to graders, who receive the RAW facts (quotes, ids, concepts) and never the falsifier's conclusion — independence enters through data, not framing; (2) the synchronous CLAIM trigger ships **OFF**, running in shadow-log mode from Phase 2 (would-be edges computed, nothing written) and turns ON only after S3 passes with zero wrong links, graded against pre-locked keys with per-arm forked state; (3) no `head_id` denormalization initially — reads use the locked one-hop union; if ever added: same-tx invalidation + version-stamped derivations + a head-degree SLO watched from day 1; (4) the falsifier is necessary-not-sufficient and is BLIND on no-XBRL heads — v3.2 adds two more model-free channels (periodicity coherence; company-set × event-time co-occurrence) and demotes 8-K item-codes to abstain-only evidence; (5) frozen anchors protect precision at a measurable recall cost — v3.2 adds the **split-reconciliation lane** (§6.6), the recall-symmetric twin of quarantine, so over-splits stay repairable by construction. Lineage: v1 (inline skeptic) → v2 (merge-free live-first) → v3 (anchor-first, live-always; CLAIM restored) → **v3.1 = v3 hardened by a 7-agent adversarial pass** (historian · CLAIM-attacker · recovery-critic · ESTABLISHED-critic · seed-poisoner · fallback-analyst · silent-corruption attacker; ~40 findings, 9 FATAL-class, all dispositioned below). The two historical deaths were re-verified first-hand and now anchor the design: **v1 died** of a closed word-list/`canonicalize()` rejecting 82% of even-correct names (code must never decide meaning; vocabulary stays open) `[DriverContext:39 · NAME-03]`; **v2 died** of eager merging collapsing three demand stories into one generic `revenue_demand`, failing its held-out exam **while its reuse metrics looked clean** (~99% string-match vs ~29% judged) `[10 PIPE-32 · NAME-04 · historical: DriverContext:40/INDEX:54/Drivers.md:98 — INDEX/Drivers are stale-trap docs per 95]`.
>
> **The four architectural changes the pass forced (v3 → v3.1):**
> 1. **Variant-anchored storage.** Facts ALWAYS write to the Driver node matching their own (post-ADOPT) wording — never physically onto a foreign head. The "head series" is a read-union over COMMITTED SAME_AS edges (PIPE-35's own locked consumption contract); the *non-quarantined* filter and a denormalized `head_id` column (O(1) reads) are **v3.x additions [§10], not part of PIPE-35**. v3's attach-to-head is DELETED: it made wrong merges physically irreversible and bought nothing (union-over-committed-edges is write-time-final, unlike v2's union over links that did not yet exist).
> 2. **One LINK mechanism, two triggers.** CLAIM and the sweep are now literally the same operation — a code-assembled pair judged by one hardened skeptic, applied as a reversible edge — differing only in WHEN it fires (synchronously at admission on the producer's routing, vs asynchronously from the code suggester). The fallback ("CLAIM off") becomes a config flag, not a different architecture.
> 3. **An immune system with a model-independent oracle.** v3's metrics watched only the SAME_AS channel, with LLMs of the same generation grading themselves — v2's exact death posture. v3.1 adds a deterministic merge FALSIFIER over stored facts (XBRL concepts, numeric directions, return signatures), an audit on the previously-uninstrumented exact-ATTACH channel, transitive-drift probes, risk-stratified audits with published upper bounds, and a planted calibration stream that MEASURES grader blindness instead of assuming it away.
> 4. **Edge-state recovery, fully automatic.** Wrong links are detected, signal-quarantined, 2-grader confirmed, and edge-quarantined (never deleted; reversible; audit-trailed) with NO physical fact replay — closing the no-human gap without violating id immutability. D4's never-auto-reopen is scoped: it stays absolute for approvals (links are never LOOSENED automatically); quarantine — the tightening direction — is automated for ALL link origins including the seed, with a higher confirmation bar for seed links. **[owner decision]**
>
> **Tags:** `[LOCKED · cite]` reused rule · `[PIN]` operational pin · `[NEW — owner sign-off]` addition · `[v3.1]` changed by the adversarial pass. *('owner ruling N' below = a ruling on THIS proposal during design — distinct from a locked FinalDesign OD-#.)* Authority: `01–09` + `10` + `12` + `95` + owner-approved `66 §0.R` blocks (OD-1/2/3/6/8/9–15) win on any conflict; **OD-7 is a pending recommendation (not yet owner-approved)** this design builds on. Code map: `WorkflowContextPack.md`.

---

## §1 Production strategy (carried from v3, unchanged in substance)

**Anchor-first, live-always.** D1: a head-focused, machine-built, gate-proven seed (stratified leaves, default 3 companies/industry, X-S1-tuned; full defense stack; the never-run fitness gate must go GREEN before launch). D2: live kernel from day 1 — exact ATTACH · code-verified ADOPT · the LINK mechanism (§6) for cross-wording sameness · born-complete CREATE · fail-closed PARK. D3: the async LINK trigger (event-driven + nightly) as backstop. D4: write-time-final signal eligibility. The old leaf→industry→sector/global workflow remains the seed-builder, the contingency deep-clean, and the component donor — never a scheduled production backbone. Rationale, dial decomposition, and the attacks on batch-first/live-first/owner assumptions: v3 §1 (preserved in git history; conclusions unchanged by the pass).

**The eight strategy answers (v3 §1.6) stand**, with three amendments from the pass: seed cards are NOT automatically ESTABLISHED (§8.3); ESTABLISHED is skeptic-minted, not count-minted (§6.5); signal eligibility keys cross-company features off `BROAD`, not `ESTABLISHED` (§8.4).

---

## §2 The kernel — decision flow

```
INPUT (per candidate, from the BLIND extraction pass — outside the kernel):
  {proposed_name, quote, evidence_atom, slice_tokens[], measurement_spans[], per_x, event_time}
  [PIPE-22 propose-first; OD-3 slicing; NAME-13/14; NAME-06/07/08 canonical coining]

STAGE 0 — deterministic intake (code, zero LLM)
  norm() [v3.1: absorbs ALL typography — case/separators/whitespace/unicode; NEVER
    plural/stem/acronym — that is meaning, the v1 line; plural/acronym convergence is achieved by canonical coining (NAME-06/07/08) + the sweep SAME_AS (NAME-02: a true duplicate is joined by a reversible same-as, both nodes survive), NOT by code normalization] → NAME-05 format check →
  banned-token lint (exact full-token, tiny frozen list) → terminal-suffix scan →
  collision probe (records ∪ variant nodes ∪ latent anchors) →
  PIT retrieval (embed name+quote+scope; visible_from ≤ event date; cluster-deduped
    top-K; exact-norm match slot 1 flagged EXACT; badges: ESTABLISHED / YOUNG /
    CLAIM_FROZEN / QUARANTINED) → build the reuse view (§3)

STAGE 1 — the G2 router (ONE batched call per event ≤400/≤300k; ATTACH/CLAIM
  discrimination is identity work on the strong-judge tier per §11.0 [OD-18] —
  CREATE/SKIP dispositions may run cheap where experiments prove no loss)
  ATTACH(card)   — EXACT card only; same cause + same causal scope + SAME MECHANISM
                   confirmed from the card's evidence [v3.1: mechanism added — the
                   tariff_impact homonym crossed K with no mechanism question]
  ADOPT(card)    — sorted-token-multiset reorder, code-verified → ATTACH
  CLAIM(card)    — different wording, same cause as a claim-eligible card → routes
                   the pair to the LINK judge (§6); the router only proposes; the
                   judge's input is CODE-assembled — producer rationale never
                   reaches the judge [v3.1: kills advocacy anchoring]
  CREATE         — no surviving match; NAME-18 (a)–(g) → born-complete (§5)
  SKIP           — vague / not reusable / single-event-bound
  UNSURE         — one strong-tier re-judge of this candidate
  Hard rules: never claim across flavors; never claim a QUARANTINED card; a
  homonym-quarantined exact name forces a more-specific re-coin (§10.4); when
  unsure, keep separate.

STAGE 2 — arm execution
  ATTACH : write the fact to the exact-matched node (its own wording — always)
  CLAIM  : [SHIPS OFF — shadow-log only until S3 passes, §6.2; the narration
           below describes flag-ON behavior] LINK judge fires synchronously
           (§6). APPROVED → in ONE atomic tx:
           variant node created (fact_type copied from head — PIPE-24/25; F1 validates presence) +
           SAME_AS→head edge + judge memo on the edge + the fact written TO THE
           VARIANT. The union makes it part of the head series at write time.
           REFUSED/timeout → fall through to CREATE (pair → deferred ledger).
  CREATE : collision routing → stamping (OD-1 ×2 | DU-06 roots | C1→C2; live
           thin-evidence UNCLEAR → PARK-RETRY, never a default [OD-2 pin 3]) →
           BASE_METRIC (PIPE-25) → atomic tx → index immediately →
           first fact flagged new_driver=true → pair enqueued to the suggester
  SKIP/PARK: unchanged park ledger (RETRY drains on arrival · TERMINAL counted)

STAGE 3 — fact guards (Track B writer, unchanged): FACT-16 · first-fact
  lane-exercise guard · write | park. Every fact stores attach_mode ∈
  {exact, adopt, claim, create} + attached_via (birth-id) [v3.1 provenance — also
  recorded for seed/fold-built facts at sync time].

ASYNC — the LINK mechanism's second trigger (§6.2) + the immune system (§9)
  + edge-state recovery (§10).
```

**Real-time guarantee (axiom C, scoped precisely [v3.3]):** at write, the fact sits on its own wording-node — final forever (ids immutable) — and is **event-level signal-eligible immediately**; that is what "write-time-final" guarantees. Cross-wording SERIES membership completes synchronously only when CLAIM is ON; with CLAIM OFF it completes asynchronously (minutes-to-nightly, §6.2) by ADDING committed edges — the additive, safe-direction latency axiom C explicitly permits (nothing wrong is ever asserted meanwhile; splits under-attribute). A later quarantine only REMOVES a link confirmed wrong (an audited correction — a tightening-reversal on new evidence, never a re-litigation of an approved link [D4]). No written fact ever moves, re-keys, or waits on a cleanup job.

---

## §3 Reuse-display (G1) — carried from v3 with v3.1 badges

Selection, PIT discipline, card fields, and the never-shown list carried verbatim (v3 §3): propose-first; Tier-0 exact probe + Tier-1 semantic top-K=10 cluster-deduped; cards show name · fact_type · companies-count (tie-break only) · **ESTABLISHED/YOUNG/QUARANTINED badge** · BASE_METRIC line · SAME_AS variants · ≤2 evidence quotes PIT-cut to `date ≤ event date`. Never shown: full catalog, facts/values, XBRL, latents/parked/quarantined-as-targets, scores, future text, hierarchy lanes. Instruction [v3.1]: “ATTACH only on an EXACT card whose evidence shows the same cause, scope, AND mechanism. ADOPT trivial reorders. CLAIM a differently-worded claim-eligible card only when the evidence supports same cause — a skeptic decides, and your reasoning is not forwarded to it. Never claim YOUNG (except your own company's per-X causes, §6.5), never claim QUARANTINED. When unsure, keep separate.”

---

## §4 Admission arms and parks — carried, with v3.1 deltas

- **ATTACH** = exact-name only + 3-part confirmation (cause/scope/**mechanism**); homonym verdict → more-specific re-coin (one cycle) else PARK-TERMINAL. Facts write to the matched node itself.
- **ADOPT** = code-verified reorder only (typography now absorbed by norm(); plural = experiment-gated default OFF; stem/acronym NEVER — v1's line).
- **CLAIM** = a synchronous LINK trigger (§6); at most one claim per candidate per event; refused claims CREATE and defer the pair.
- **CREATE / SELF-REWRITE / SKIP / PARK** — unchanged from v3 §4 (park classes: RETRY {gate_unavailable, stamp_thin_evidence, base_unresolved, stamp_conflict, lane_unexercised} drains on arrival; TERMINAL {vague_skip, rule_reject, gate_rejected} counted+aged; parks drain only through the full kernel; park rates never model targets).

---

## §5 Family policy — carried from v3 unchanged

One `stamp_fact_type()` (suffix → OD-1 gate ×2 → DU-06 roots → C1 → C2; live UNCLEAR parks, never defaults) and one `resolve_base_metric()` (PIPE-25 order; OD-1 latent rules; proven-metric F2 gate), shared by seed finalize and live admission. CLAIM-approved variants copy the head's fact_type (PIPE-24/25; F1 = the presence check) — stamped only AFTER judge approval (no wasted stamping; a refused claim goes through full CREATE stamping). Latent graduation exact-norm only; stamp conflicts park; `visible_from = min(existing, new evidence date)`; batch imports live nodes PROTECTED. *(OD-1 is source-backed via 66 §0.R and back-ported to the topic docs — no 95 row (an admission-gate addition, not a reversal); OD-2 is recorded in 95 #29; OD-8 is recorded in 95 #30. Completed 2026-07-07.)*

---

## §6 The LINK mechanism — one judge, two triggers **[v3.1 — the core rewrite]**

### 6.1 The operation (identical wherever it fires)

```
PAIR ASSEMBLY (code — no producer advocacy): side A = the proposal/new node's
  name + quote(s) + slice tokens + per_x + industry tag; side B = the target
  head's FROZEN definitional anchor (§6.3) + industry tag.
AUTO-REFUSALS (code, pre-judge) — each classified for REPAIRABILITY [v3.3 L2]:
  PERMANENT-BY-LOCKED-RULE (no judge may ever revisit; the justification is the
  locked rule itself, and re-opening one is an owner RULE question, never
  machinery): cross-flavor [MF-02 / NAME-17 / 95 #9: never SAME_AS across flavors] · terminal-
  suffix mismatch [MF-06/NAME-17] · per-X mismatch [NAME-13: different per-X is
  never SAME_AS]. [OD-19, owner 2026-07-11 — GATED: the former TOKEN-SUBSET species auto-refusal
  (brent_oil_price vs oil_price, resin_cost vs input_cost) moves to JUDGE-TERRITORY
  below once K-pairs.v2's portion family passes with wrong-same = 0 (95 #41); until
  then it stays auto-refused here. Portion-qualifier supersets (OD-17: current_rpo
  vs rpo) are ALWAYS DIFFERENT — a locked judge instruction, never reconcilable.]
  STATE-BASED (auto-re-enqueued when the state clears — never permanent):
  target not claim-eligible (§6.5) · either side QUARANTINED/flagged.
  JUDGE-TERRITORY (moved OUT of code [v3.3 L2]): SIBLING named-series pairs
  (Brent vs WTI, SOFR vs fed_funds — non-subset) · [post-OD-19-gate] TOKEN-SUBSET
  pairs (judged by meaning when proposed — never auto-refused, never deferred;
  the per-X/cross-flavor/terminal-suffix/portion refusals above unchanged) — code cannot know two
  benchmarks are distinct instruments without a curated list (the v1 pattern);
  these go to the judge's check-1 with a dedicated fixture family, and judge
  refusals enter the refuted-cache → §6.6-repairable like any other refusal.
THE JUDGE (strong, default survives=false, code-assembled input only):
  5 checks, ALL must hold, each quoting both sides — checks (1)–(3) = the locked
  object/scope/mechanism 3-check [10 PIPE-13/PIPE-19]; (4)–(5) are v3.x
  safe-direction additions:
  (1) same OBJECT — CO-EXTENSIVE, never hyponym: if either side's object is a
      narrower species of the other's (iphone⊂smartphone, resin_cost⊂input_cost,
      brent⊂oil), REFUSE — breadth may only emerge from the SAME name recurring,
      never from absorption [v3.1 — kills the genus-species v2-death channel];
  (2) same SCOPE — business population AND referent ownership class
      {own-entity-internal | external-market | counterparty}: a firm-realized
      quantity is never the external market variable that drives it
      (fx_headwind≠dollar_strength; wage_bill≠wage_inflation) [v3.1];
  (3) same MECHANISM — same measured quantity at the same causal position:
      upstream/downstream/correlated on one chain is grounds to REFUSE
      (energy_costs≠oil_price; freight_cost_pressure≠freight_costs), and the
      financial transmission channel to equity must match (revenue vs margin vs
      funding cost vs multiple) — same-flavor cross-industry homonyms refuse
      here (telecom churn ≠ deposit churn) [v3.1];
  (4) NO RIVAL — when retrieval surfaced ≥2 claim-eligible cards above threshold,
      the judge sees the top rival and must REFUSE unless the quote uniquely
      discriminates ONE target; ambiguity → keep separate [v3.1];
  (5) the head's own anchor is MONO-mechanism — a head whose frozen anchor spans
      mechanisms is un-claimable, not easily-claimable → REFUSE + flag (§9) [v3.1].
HIGH-BLAST second skeptic [v3.1 — locked-rule alignment]: a link onto a head
  spanning ≥ HIGH_BLAST (8) companies gets a SECOND, independent, lens-split
  (object/scope/mechanism), AND-voted skeptic on a disjoint evidence view —
  the batch high-blast rule applied to live fusions [10 PIPE-13].
APPLY (code): SAME_AS variant→head + memo {trigger, judge model id, date,
  anchor hash, verdict quotes}; head election [v3.x design choice — owner sign-off;
  the locked catalog canonical is NAME-06 'shortest standard form' + the assemble
  star-flatten's shortest-then-lex, which this reorders]: ESTABLISHED beats YOUNG, then
  earlier visible_from, then lexicographic; star-flatten; D1-traceable.
CACHE: refuted pairs cached; re-judged only when either side gains ≥1 distinct
  company. Approved links are never LOOSENED automatically; tightening
  (quarantine) is §10's automated path.
```

### 6.2 The two triggers

- **Synchronous (CLAIM):** the producer's routing at admission — buys write-time union membership. **Ships OFF [owner ruling 2].** From Phase 2 it runs in **shadow-log mode**: the judge fires and the would-be edge + verdict are logged in strict admission order against PIT catalog state, but nothing is written — burning in the path and feeding S3 representative data. It turns ON only after S3 passes with ZERO wrong links; if it ever fires a confirmed wrong link in production, the flag flips OFF again with zero architectural change.
- **Asynchronous (the sweep):** on-create enqueue of every new node to the suggester (embeddings top_k=5 min_score=0.60 ∪ token-overlap ∪ rare-token — suggest, never decide), judged immediately ONLY for corroborated/non-thin pairs; fresh single-quote thin pairs go to the **deferred-pair ledger**, auto-re-judged on evidence growth. Batch passes run **event-driven keyed to the earnings calendar / CREATE-burst detector** (gap → minutes exactly when clustering matters), nightly as the idle backstop.
- **Deferred-pair ledger hygiene [v3.2]:** a claim attempted against a falsifier-flagged head is parked to the ledger as `deferred(head_flagged)` — **no node is minted** (a false flag must not cause a duplicate storm); recovery resolution RE-ENQUEUES every pair deferred against that head immediately (never waits for company growth). Deferred pairs age: after N periods without maturation they move to a TERMINAL-defer class — counted, reported, re-openable on any evidence growth.

### 6.3 The frozen definitional anchor **[the anti-ratchet — v3.2 final form]**

Every card carries `definitional_evidence` with an **immutable `birth_quotes` sub-field**: for a seed card, its build-stack evidence draw + slice tokens; for a live card, the RAW quotes from its first qualifying events — **never an LLM distillation** (re-summarizing re-broadens and violates NAME-03). The fast-path judge and every audit judge against THIS anchor only; the drift probe (§9.3) pins to `birth_quotes` forever. Claim-attached quotes and variant wordings are display-only — never the judge's reference, never retrieval-score justification for further claims. The anchor also accumulates a **frozen refuted-negative set** [v3.2 — contrastive boundary]: pairs the judge refused sharpen what the card is NOT. Anchor ENRICHMENT (adding minting-vetted exact-attach quotes) is **experiment-gated, default OFF** [mechanism-attacker M2: a pre-mint homonym would bake into an eternal anchor; the recall pressure enrichment addressed is handled by §6.6 instead]. **Anchor RE-FREEZE** [v3.2 — completeness #1]: when recovery graders confirm an anchor quote itself was mis-attributed by extraction, the anchor is re-drawn from the next clean qualifying events in one RecoveryEvent-audited step — re-drawn, never distilled.

### 6.4 Union-preview: suggested-but-unjudged pairs may be consumed **abstain-only** — they may suppress/downgrade a "this signal is narrow" conclusion, never assert a merged signal.

### 6.5 Claim-eligibility and establishment **[v3.1 — replaces v3 §2.4's count-minted rule]**

- `BROAD(card)` ⇔ evidence from ≥K distinct companies (K=2 default, X-S4) — a pure code count, used ONLY for §8.4 cross-company signal features.
- `ESTABLISHED(card)` (= claim-eligible) ⇔ **skeptic-minted**: the card crossed an eligibility floor (BROAD; or seed-built + gauntlet-passed §8.3) AND passed a ONE-TIME mono-mechanism coherence check by the LINK judge over its accumulated evidence ("does this one name's evidence describe ONE object + ONE scope + ONE mechanism?", default-suspect). Code counts eligibility; the skeptic mints standing. Fails → stays YOUNG + flagged (homonym suspect → §9/§10.4). Fires once per card — negligible cost. [Kills the tariff_impact weaponized-homonym channel: opposite-mechanism evidence cannot mint a claim target.]
- **Single-company causes:** v3's persistence lane (M/T/D) is DROPPED (it matured on echoes). Replacement: a claim may target a YOUNG card iff `same company AND same per_x AND entity-bound family` (a company converging its OWN wordings for its own cause — `taco_bell_value_menu`, `blackwell_supply_constraint`), still through the full judge. Macro/standard-KPI families require BROAD — a macro cause "maturing" at one company is a homonym red flag, not maturity. "Distinct event" everywhere = distinct primary filing/earnings event (accession-level), never news re-quotes. [v3.1]
- Rejected as gate inputs: source-quality ranks (orthogonal to meaning stability) and LLM-graded "quote clarity" (code/LLM deciding meaning at a threshold — the v1 death vector).
- **Eligibility is read LIVE, in-tx [v3.2]:** `claim_eligible = ESTABLISHED ∧ ¬falsifier_flagged ∧ ¬quarantined ∧ ¬CLAIM_FROZEN`, re-checked inside the commit transaction with an edge-set version bump (a stale retrieval badge can never authorize a claim — completeness #8; flag-set serializes against in-flight commits on that head). **CLAIM_FROZEN** [v3.2 — completeness #5] is the de-mint state: a formerly-established card whose evidence turns incoherent (drift probe / dispersion tripwire) loses claim-eligibility while its existing edges route to per-edge §10 adjudication — badges are ESTABLISHED / YOUNG / CLAIM_FROZEN / QUARANTINED.

### 6.6 The split-reconciliation lane **[v3.2 — NEW — the recall-recovery twin of quarantine; owner ruling 5 resolved structurally]**

The frozen anchor protects the FAST path's precision, but frozen anchors + cached refusals could make two valid synonyms refuse each other forever — an over-split ratchet that would break the law's own premise (splits are cheap BECAUSE repairable). So recall gets its own governed exit, mirroring §10: periodically (and on TERMINAL-defer aging), mutual-refusal and long-deferred pairs where both sides are now evidence-rich are re-judged by the **batch-grade process** — FULL evidence on both sides, lens-split skeptic, high-blast rules, the same machinery batch dedup/D5 uses — NOT the frozen-anchor fast judge. Two regimes, each matched to its information: frozen anchors govern thin-evidence live claims (anti-ratchet); full-evidence batch-grade judgment governs mature-pair reconciliation (anti-permanent-split). Reconciliation approvals are ordinary reversible SAME_AS links with memos; its false-refusal rate and time-to-reconcile are first-class §9.7 metrics [owner ruling 5's measurement demand].

---

## §7 Validators — carried, with v3.1 deltas

V1 format/lint · V2 link legality [v3.1]: claims only on claim-eligible targets; auto-refusal classes enforced pre-judge; ADOPT reorder-only · V3 OD-1 memo completeness · V4 exactly-one BASE_METRIC, proven-metric target · V5 suffix⇔fact_type · V6 latent sanity · V7 create-collision invariants · V8 admission atomicity + ON-CREATE-only fact_type · V9 fact-side (FACT-16 + lane-exercise) + **attach_mode/attached_via provenance present on every fact** [v3.1] · V10 park-ledger integrity · V11 link-side (memo'd, D1-traceable, deterministic head election/star-flatten, refuted-cache respected) · V12 variant rules (copied fact_type + memo + edge in one tx; variants never claim targets) · **V13 [v3.1] anchor integrity: `definitional_evidence` frozen at establishment, hash-pinned, never rewritten; judge inputs assembled from it verbatim** · **V14 [v3.1, extended 2026-07-11] recovery integrity: quarantine is edge-state only, plus two reversible recovery-lane booleans (fact `disputed`, `ContinuationClaim.quarantined`) set only by §10 machinery; no mutation of fact identity/content fields, no deletion; every recovery emits a RecoveryEvent**. All code, zero LLM, hard-fail.

---

## §8 Strategy phases, the seed gauntlet, eligibility

### 8.1 Sequence (v3 §8.1 carried) — Phase 0 stale-trap fixes + FINALIZE build → Phase 1 SEED (stratified leaves → folds → finalize → validate --final → **GAUNTLET [v3.1]** → fitness gate GREEN → graph sync) → Phase 2 shadow burn-in → Phase 3 production with priority backfill → forever: async LINK trigger + immune system + quarterly fresh-key gate re-runs.

### 8.2 The seed (v3 §8.2 carried): the head of every industry's vocabulary through the full defense stack; sizing by X-S1 (default 3 companies/industry); by-products = keys, fixtures, the gate's frozen catalog; degradation dial intact.

### 8.3 The seed GAUNTLET **[v3.1 — NEW, pre-sync, zero-tolerance]** — because the seed is built by the documented stale-trap code and v3 granted it unaudited full gravity.

- **Layer A — static audit (code + ONE strong-model pass, no humans):** S-A1 single-token scan (forced through S-A4 + homonym adjudication before any standing) · S-A2 bare NAME-16 category scan (hard-fail) · S-A3 brand/measurement/ticker/period/direction token scan vs a gazetteer (hard-fail — catches the `taco_bell_same_store_sales` / `adjusted_eps` prompt-drift classes deterministically, independent of Phase-0 trust) · S-A4 **mechanism-spread audit**: embed each card's own evidence, flag internal dispersion ≥2 clusters (broad-or-homonym suspects; embeddings flag, a strong model adjudicates — suggest-never-decide) · S-A5 gravity-well scan (cards that are retrieval-neighbors of many distinct causes) · S-A6 **suffix-blind fact_type/BASE_METRIC re-derivation** (a strong model re-derives from evidence ignoring the suffix; disagreement on any `_guidance`/`_surprise` card = hard fail — the `regulatory_guidance` ISS-19 (→ OD-1) class).
- **Layer B — dynamic probes (crafted candidates replayed through the live kernel against the frozen seed; meaning-graded, 2-grader, zero merge tolerance):** P1 three-demand-stories (the literal v2 exam: three different demand mechanisms must yield three creates) · P2 metric/guidance/surprise routing + family edges · P3 own-segment vs external cause · P4 measurement words route to the slot, never to an `adjusted_*` card · P5 per-X trio · P6 brand/geo slice traps · P7 same-words-different-mechanism homonym pairs (spread/coverage/retention families) — any double-accept quarantines the card · P8 genus-species traps (species candidates at any genus card must CREATE) · P9 benchmark identity (Brent/WTI/generic).
- **Pass bar:** zero S-A2/A3/A6 hits; every S-A1/A4/A5 flag adjudicated clean or the card quarantined from the seed; zero wrong convergences across P1–P9. **Seed-built cards earn ESTABLISHED only by passing; unprovable cards ship YOUNG** — usable anchors that must earn claim-standing from live evidence like anything else [kills born-fat gravity]. Failure → bootstrap-time D4 out-of-band fix (split/re-stamp/drop/demote) → full gauntlet re-run. No partial sync.

### 8.4 Signal eligibility (v3 §8.4 carried, one fix): write-time-final, deterministic; every written fact immediately event-signal-eligible; `new_driver` flags empty-history-by-construction; **cross-company/history-weighted features key off `BROAD`** (not ESTABLISHED — a single-company-matured card must never feed a cross-company feature computed over a population of one) [v3.1]; parked invisible; quarantined never; **signal-quarantine** (§10.2) pauses history-weighted features on detector-fired links pending confirmation — event-level reads unaffected.

### 8.5 Contingency ladder (v3 carried): judge/cadence/suggester escalations → claim-flag OFF (= trigger-2-only, zero redesign) → partial batch rebuilds (live nodes PROTECTED) → full Track A build.

---

## §9 The immune system **[v3.1 — replaces v3 §6.4; the anti-"looks clean while corrupting" layer]**

Principle: v2 was caught by a held-out exam, not by its own metrics. Every detector below either uses NO model, a DIFFERENT information channel than the one that made the decision, or measures the graders themselves.

**The smoke-alarm doctrine [v3.2 — owner ruling 1, integrated]:** code surfaces form-level contradictions and may take exactly one automatic action — the REVERSIBLE signal-quarantine (pausing history-weighted features through the suspect link/head, §10.2). Code never concludes "different causes"; the quarantine VERDICT belongs to the §10 graders. Graders receive the **raw facts only** (the quotes, ids, periods, concept identifiers) — never the falsifier's conclusion or framing [mechanism-attacker M1-FATAL: a shared code-derived prior would collapse two graders into one]; the falsifier's own verdict is logged for audit only. The principled line: code decides FORM (identity, counts, topology, taxonomy codes); only LLMs decide MEANING; the falsifier's outputs are form-level facts whose interpretation is always a meaning claim.

1. **The model-free merge FALSIFIER (deterministic graph queries; ~free; the held-out-exam analog) — v3.2 corrected signals:** (i) one head whose facts at the SAME COMPANY map to ≥2 distinct XBRL concepts, or carry inconsistent dimensional members (the mis-slice signature) — cross-company multi-concept is NORMAL (concept links are per-company by locked design, PIPE-29) and is flagged only as an **industry-partitioned concept split** (concepts partitioning cleanly by industry = the cross-industry-homonym signature); (ii) co-occurring same-company same-**fiscal-normalized**-period same-scope members with OPPOSITE numeric directions — suspicion only (amendments and intra-period guidance revisions legitimately produce opposite signs); (iii) two differently-named heads repeatedly sharing company+period+XBRL-concept — the duplicate oracle, independent of the embedding suggester (also disambiguates a low link rate between "converged" and "blind suggester"); (iv) **periodicity coherence** [v3.2]: a `metric`-stamped head whose per-company facts never recur across reporting periods behaves like a mistyped one-off — pure arithmetic; (v) **company-set × event-time co-occurrence** [the XBRL-free DUPLICATE channel for qualitative/news/action space — note: a duplicate detector, not a homonym detector]: candidate duplicate pairs with high company-Jaccard and tight temporal co-occurrence, plus 8-K item-code family sets as abstain-only evidence (per-head, item→family map, fail-OPEN when codes are absent); (vi) bimodal post-event return signatures — abstain-only audit-priority (a real cause CAN be legitimately bimodal across companies: oil up = airlines down, producers up); (vii) **[v3.3 L1] live suffix-blind re-derivation** — the gauntlet's S-A6 as a SAMPLED ops lane: for live-created suffixed drivers, a strong model periodically re-derives fact_type/base from evidence IGNORING the suffix; disagreement = raw-evidence exhibit → §10 (the `regulatory_guidance` class was otherwise guarded only at seed time while the live path runs forever). Runs offline over stored facts (FS-14 third context). Every flag → §10, as raw evidence — and §8.4 features gate on `BROAD ∧ ¬falsifier_flagged ∧ ¬homonym_suspect ∧ ¬CLAIM_FROZEN` [v3.3 — a flagged card must not feed cross-company features while adjudication runs].
2. **ATTACH-channel audit.** The highest-volume, cheapest-model path was uninstrumented. Deterministic risk pre-filter: cross-industry exact-name attaches, per-head industry-cluster count ≥2, scope-qualifier heterogeneity — **including SAME-industry heterogeneity** [v3.3: two telecoms can homonym "churn" as subscriber vs employee; falsifier 1(i)'s per-company scoping is blind to it] → strong-model blind re-judge of flagged samples only. **QUARANTINED nodes (any cause, not only homonym) block exact-ATTACH: incoming facts PARK-RETRY** [v3.3 — the one undefined recovery-matrix cell; parking is the safe under-attribution direction; a true type-CORRECTION lane is a deferred recall optimization, not required for safety]. **SYNCHRONOUS (OD-18, owner 2026-07-11):** the deterministic pre-filter runs AT WRITE TIME; a flagged ATTACH is confirmed BEFORE the write by a blind strong-judge 3-check (same cause + same causal scope + same mechanism vs the head's frozen anchor; code-assembled, batchable per head). CONFIRM → write. REFUSE → never overturned toward the write. UNSURE → one blind escalation-tier re-judge; only its CONFIRM writes; anything else → the more-specific re-coin path (the fact CREATEs now under NAME-18; no coinable distinguisher → the existing vague-evidence TERMINAL skip, counted; judge timeout → PARK-RETRY). Flag scoping: heads with gauntlet/skeptic-earned ESTABLISHED standing fire only qualifier-heterogeneity; the ≥8-company HIGH_BLAST flag extends to ATTACH on non-ESTABLISHED heads. The post-write sampled audit continues unchanged. Counters (P7): flag rate · refuse rate · escalation-disagreement rate · re-coin-failure rate. Until OD-19's gate passes, a wrong refusal's token-superset re-coin is not judge-recoverable (§6.1) — an accepted, counted under-attribution residual (§9 item 7 metrics). A confirmed mis-attach found later routes to the fact-level `disputed` lane (§10 item 8), not only whole-node quarantine.
3. **Transitive-drift probe.** Per established head per period: present its EARLIEST anchor quote vs its LATEST attached quote to the judge as a hypothetical fresh pair; a refusal = the head drifted → freeze claims onto it + §10. Plus a deterministic centroid-drift alarm on the frozen-anchor embedding vs newest members.
4. **Evidence-dispersion re-cluster** (S-A4 run continuously on live heads): bifurcation into ≥2 stable mechanism clusters = homonym tripwire → §10.4.
5. **Risk-stratified audits + honest bounds.** The x% link/attach audit budget concentrates on structurally risky cases (cross-industry, homonym-shaped names, just-crossed-K thin sides, high-connectivity heads — blast-radius-weighted toward 100%). Dashboards publish the statistical UPPER BOUND (0 wrong in n audited ⇒ ≤3/n at 95%) × live population, alarmed against a permanent-error budget — "zero confirmed wrong" is never reported without its denominator. **Stratum honesty (owner 2026-07-11):** a published "0 wrong in n audited" bounds the flagged/audited strata only; the unflagged stratum is bounded pre-launch (gauntlet + EXP-3 fixture families incl. same-industry mechanism-drift homonyms + one pre-registered unflagged sample) and monitored by the §9 detectors.
6. **Planted calibration stream + grader-independence measurement.** A permanent stream of known-answer, surface-similar-but-different pairs (bookings/billings · adjusted-vs-GAAP EBITDA · gross/net · segment/consolidated · deferred/recognized revenue) runs through the live judge AND both graders — **in a tagged shadow namespace, never admissible to the live graph** [v3.2 — mechanism-attacker fix 10]. The shared-miss rate quantifies generation-level blindness (measured and reported for interpretation and escalation; NOT automatically applied as a discount in any gate — deliberate owner decision 2026-07-11, T1-08 rejected); a suspiciously LOW grader-disagreement rate is itself an alarm. The stream ALSO injects known-SYNONYM pairs at the suggester to verify retrieval recall does not decay as the catalog grows; suggester tuning faces a JOINT promotion bar (planted-synonym recall AND false-merge rate held simultaneously, via the locked A/B gate). Honest limitation: all in-session judges are one vendor's models — the falsifier is therefore the only fully independent channel, which is why it is a launch blocker.
7. **Flow metrics** (kept from v3, re-shaped): per-head fan-in rate (wordings/companies absorbed per unit time) + evidence-spread trend (a gravity well over-converges at admission and SUPPRESSES sweep activity — so fan-in, not sweep_link_ratio, is the well detector); duplicate_half_life SLO; claim_refusal_rate; park drain age. `sweep_link_ratio` is kept only WITH detector-1(iii) disambiguation.

**Launch blockers:** detectors 1 and 2 must exist before Phase 3 — without them v3.1 has less independent signal than v2 had.

---

## §10 Edge-state recovery — automatic, no-human, reversible **[v3.1 — NEW — owner sign-off]**

1. **Provenance (write time, immutable):** every fact carries `attach_mode` + `attached_via` (birth-id); seed/fold facts get lineage recorded at sync. Every link carries its judge memo + anchor hash. Every card carries its frozen anchor.
2. **Detect → signal-quarantine:** any §9 detector firing on a link/head immediately pauses history-weighted/cross-company features THROUGH that link (event-level reads untouched) — the burden falls in the safe direction while adjudication runs [asymmetry: admission is default-refuse; recovery must not be default-keep].
3. **Confirm:** two independent strong graders (blind, independence-measured by §9.6) must confirm "different cause" citing evidence. Confirmed → proceed; unresolved → one blind re-grade round; still split → INCONCLUSIVE: the signal-quarantine stays, the case becomes a calibration-stream fixture, and the class goes to the owner as a RULE question (OD-6's own remediation) — not a silent keep.
4. **Quarantine (the only write):** `quarantined=true` on the SAME_AS edge — never deleted, fully reversible, one edge-flip tx. Read-union excludes quarantined edges; the variant reverts to a standalone driver (revert is a STATE: in-flight facts PARK-RETRY(`variant_reverting`) and re-enter; recoveries serialize per SAME_AS component). Facts never move — they were always on their own node. A **confirmed homonym NODE**: `homonym_quarantined` badge → never claim-eligible, excluded from cross-company features; future exact proposals are router-forced to more-specific re-coins (the D5-DIFFERENT analogue); existing facts stay as flagged historical evidence — no re-key, no delete [OD-7's semantics, automated]. **v3.2 propagation rules [completeness #2/#3/#4]:** homonym-quarantining a head that already HAS variants signal-quarantines ALL its variant edges and routes each to per-edge two-grader adjudication (never a bare badge — the variants straddle both meanings); quarantining a BASE (or family head) signal-quarantines its `BASE_METRIC`-derived members pending re-resolution to a clean base, else they revert to standalone; the quarantine tx re-keys or drops any latent anchors keyed to the quarantined exact-norm name in the same transaction (no permanently ungraduatable latents).
5. **Audit + regate:** every recovery emits an immutable `RecoveryEvent` (detector, both grader memos, frozen evidence snapshot, edge/node ids). The case joins the regression fixtures; the responsible prompt/model combo is flagged; remediation may DISABLE a claim-class immediately (reversible) but a model/prompt change only takes effect through the locked A/B gate — auto-escalation PROPOSES, never swaps.
6. **Wrong quarantine** (link was right) = an over-split: reversible — the pair re-enters the suggester once either side grows, re-judged with the quarantine memo in view; un-quarantine is the same one-flip tx. No double-counting is possible because nothing was ever replayed.
7. **D4 scoping [owner decision]:** D4 remains absolute against automatic LOOSENING (approved links never auto-reopened to re-litigate; unlink-to-relink churn impossible). Automatic TIGHTENING (quarantine on 2-grader-confirmed wrongness) is enabled for ALL link origins; seed-built links require a third grader. Rationale: a permanently locked wrong merge with no exit contradicts no-human; quarantine is conservative-direction and reversible. **Binding-doc note [v3.4]:** `10 PIPE-11 D4` formerly said SAME_AS links are "never reopened or broken automatically" (only exit = the out-of-band path); this scoping MODIFIES that locked rule — **RATIFIED in principle 2026-07-07 · `95 #39`** (10 PIPE-11 D4 updated to match); implementation details remain experiment-gated.
8. **Fact-level dispute [owner 2026-07-11 · OD-18]:** a single fact confirmed mis-attached (any §9 detector → this section's two-grader blind confirm) is marked `disputed=true` — a reversible, non-identity metadata boolean set/unset ONLY by this recovery lane (never by producers/enrichment): that ONE fact is excluded from cross-company/history-weighted features; the head, its other facts, and event-level reads are untouched; the fact never moves (id immutable). Every flip emits a `RecoveryEvent`; V14 validates. Field note: 09 §3 recovery-metadata note.

---

## §11 Models (v3 §9 carried; v3.1 deltas)

### §11.0 Model-tiering policy [LOCKED — owner 2026-07-07]

**The locked rule (membership-agnostic).** Any second-check or confirmation step that can change **Driver identity, Driver family/type (`fact_type`), `SAME_AS` state, `BASE_METRIC`, claim-eligibility, quarantine state, seed standing, or fact placement (an exact-name ATTACH onto an existing head — OD-18, additive 2026-07-11)** MUST be performed by the **strong-judge tier**. Cheap models may propose, extract, route, or draft low-risk candidates, but a cheap-tier model may **NEVER be the final confirmer** for a permanent or semi-permanent identity decision.

**Three tiers (defined by ROLE, never a hard-coded model name):**
- **Cheap producer tier** — bulk extraction / routing / low-risk drafting; allowed ONLY where experiments prove no loss.
- **Strong judge tier** — REQUIRED for every identity-changing confirmation named above.
- **Exceptional / fallback tier** — used only when the strong-judge tier fails its experiments.

**LOCKED vs experiment-gated.** The *rule* — "an identity-changing confirmation cannot be done by the cheap producer tier" — is **LOCKED**. The *model membership* of each tier is **experiment-gated** and may change over time (decided by the locked A/B gate + pinned exact model IDs, P6); do NOT hard-code a model name as an eternal rule.

**Current owner default for experiments [owner 2026-07-08].** Start with the cheapest plausible split: **Haiku, or an equally low-intelligence cheap model, as the default blind leaf producer** for leaf/chunk Driver-name proposals; **Sonnet 5 as the default strong-judge candidate** for judgment-heavy identity work: G2 decisions, Refute, LINK/SAME_AS judging, BASE_METRIC/fact_type confirmations, quarantine confirmation, establishment/standing, and similar second checks. Opus 4.8 / GPT-5.5 / Fable are escalation or fallback candidates, not the starting runtime default. Exact model IDs are still pinned in the run manifest, and this default survives only if experiments show no loss against the locked quality bars.

This makes the design's cost/safety law explicit — **cheapest model where safe, strongest model where identity damage is possible** — and binds, as strong-judge-tier work, the LINK judge, the OD-1 suffix checks, C2 metric-proof, establishment-minting, quarantine confirmation, gauntlet adjudication, and every §10 grader; it subsumes P4 (strong-by-default on permanent classes).

Principles P1–P7 unchanged (structure over model strength · diversity over repetition · cheap-first with zero-loss promotion · strong-by-default on permanent classes · structural escalation only · pinned IDs + canary · park/skip rates never targets). Deltas: the LINK judge row absorbs the reuse-skeptic/sweep-judge rows (ONE judge — **Sonnet 5 default baseline under the owner default above; escalate to Opus 4.8 / GPT-5.5 / Fable only if measured misses require it**; lens-split high-blast variant); the router's promotion bar adds claim-precision/recall AND zero wrong-ATTACH on the cross-industry fixture family; establishment-minting checks and gauntlet adjudications use the judge tier; graders' independence is measured, not assumed; the falsifier and all §9 pre-filters are code (no model). Billing: subscription workflow agents, step-0 guards, SDK banned [10 §11 · 95 #22]; embeddings remain the one metered, suggest-only lane.

---

## §12 Experiments (designed, not run) — v3 §10 carried with v3.1 additions

Standing rules unchanged (pre-registered · sha-locked adjudicated keys · graded once · judged-not-string · zero merge-direction tolerance · `ab_*` kit · pinned IDs). Strategy deciders S1 (seed-size knee) · S2 (three-world shootout) · **S3 [re-scoped]: synchronous vs asynchronous LINK trigger** — same hardened judge, same corpus; measure wrong links (zero tolerance), write-time series-correctness, duplicate half-life, cost; S3 must specifically instrument the RATCHET (head-meaning drift across sequential approvals vs the frozen anchor — endpoint counts alone would have passed v2) · S4 (K + eligibility floors). Kernel ladders X0–X9 carried (X0 fixtures now include: genus-species family, benchmark siblings, cause-vs-consequence, transmission-channel homonyms, ownership-axis pairs, no-rival ambiguity, calibration-stream pairs). **New: X-G the gauntlet itself** (Layer A+B against the frozen seed — a launch gate, §8.3) and **X-IM immune-system proofs** (each §9 detector must catch its seeded corruption class; each validator has a failing mutation test; OD-18 addition: a seeded mis-attach must end flagged `disputed=true` and excluded from cross-company features — never silently kept). **X-C chunking granularity [owner 2026-07-08 suggestion]:** test whether blind leaf producers should see source text as smaller paragraph-at-a-time units instead of huge wall-of-text chunks; adopt only if the automatic chunker preserves enough surrounding context and improves or maintains recall/precision while lowering cost/noise. This is an experiment, not a locked prompt shape.

---

## §13 Considered and rejected (v3 §11 carried; v3.1 additions)

1. **Attach-to-head (v3's own §2.1)** — REJECTED by the recovery critic's analysis: physicalization made wrong merges irreversible (replay, orphaned verdict/XBRL/period edges, id collisions, immutability violations) and bought nothing — union-over-committed-edges is write-time-final and is PIPE-35's own locked read contract.
2. **Physical fact replay as the recovery mechanism** — rejected with it (racy, non-reversible on false positives, audit-incomplete). Edge-state quarantine dominates.
3. **Count-minted establishment + the M/T/D persistence lane** — rejected (weaponized homonyms; echo-maturity). Skeptic-minted standing + the intra-company exception dominate with less machinery.
4. **"Seed-built ⇒ ESTABLISHED"** — rejected (born-fat gravity wells built by stale-trap code, exempt from the design's own best gate). Gauntlet-earned standing only.
5. **CLAIM-off as a PERMANENT posture** — rejected, but the v3.1 "wash" framing is CORRECTED [v3.3, minimality-audit]: CLAIM-off is NOT a wash — the synchronous judge decides at admission with thinner catalog state and fewer visible rivals than the async judge sees later, so it is strictly riskier per decision. CLAIM-off trades write-time union membership (recall/latency) for more-evidence precision. That is exactly why it ships OFF and must EARN ON through S3 [owner ruling 2]; it remains rejected only as a permanent posture, because the latency cost during earnings clustering is real and the hardened judge is designed to close the risk gap.
6. **LLM-distilled card "definitions"** — rejected (re-broadening; NAME-03). Anchors are raw frozen quotes.
7. **Union-preview as signal input** — rejected except abstain-only.
8. Carried v3/v2 rejections: full-796-first · zero-seed live-first · unguarded semantic reuse · hand-seeded vocabulary · sweep/refresh-gated eligibility · thin-thin merging · alias caches · morphology in code (plural experiment-gated OFF; stem/acronym never) · self-declared-confidence routing · auto in-context teaching · same-prompt stability voting · serialization locks · stamp-later queues · LLM validators · threshold-decided admissions · full-catalog display.

---

## §14 What would make me reject v3.4 after testing

1. S3 shows ANY confirmed wrong synchronous link the async path avoided → claim flag OFF (architecture unchanged).
2. The calibration stream shows a shared-miss rate the falsifier cannot compensate (generation-level blindness on finance identity) → judge-tier escalation via the A/B gate; if Fable-tier still misses, the claim class disables and the owner is told the honest limit.
3. The gauntlet cannot reach zero on P1/P7/P8 after two remediation rounds → the seed ships YOUNG-only (anchors without claim-standing) and live earns all standing.
4. Falsifier fire-rate on live heads exceeds the permanent-error budget in shadow → Phase 3 blocked; contingency ladder.
5. X-S1 shows no coverage knee → re-open D1 with the owner.
6. Batch/live equivalence divergence (X8) → fork bug; build stops.

## §15 Owner decisions required — MUST-LOCK-NOW vs EXPERIMENT-GATED [v3.3 final split]

**§15.0 The MVP (smallest safe first build — lock-read minimality audit):**
- **Day-1 core:** kernel Stages 0–3 (ATTACH+confirm · ADOPT · CREATE born-complete · SKIP/PARK) · async LINK trigger + deferred-pair ledger (with no-mint-on-flagged-head) · frozen birth anchors · evidence-mass gate + **skeptic-minted ESTABLISHED** (cannot be deferred: the day-1 sweep's eligibility rule depends on it) + BROAD split · validators V1–V14 · falsifier signals (i)(ii)(iii)+(vii) + ATTACH-audit · calibration stream (minimal) · recovery core (quarantine + variant/family propagation + RecoveryEvent) · seed + gauntlet static scans (S-A2/A3/A6) · park/outage discipline. **Coverage rule: if MVP admits no-XBRL (news/qualitative/action) drivers, falsifier (v) ships day-1; otherwise admission is fenced to XBRL-backed sources until (v) ships** — the qualitative space is never live-and-uninstrumented.
- **Deferred (flag/experiment-gated, inert until enabled):** CLAIM-ON (S3) · anchor enrichment M2 · item-codes M3 · UNSURE valve · union-preview · falsifier (iv)(vi) · full dynamic gauntlet P1–P9 IF the owner instead ships the seed YOUNG-only (the gauntlet-lite dial) · transitive-drift cadence beyond quarterly · exotic-latent propagation · head-degree sharding · time-keyed anchor revalidation · sampled-audit rate tuning · type-CORRECTION lane (recall optimization; parking covers safety).


1. **Ratify the v3.2 architecture** (variant-anchored storage · one LINK mechanism, two triggers · frozen birth-anchors + the split-reconciliation lane · skeptic-minted establishment with CLAIM_FROZEN de-mint).
2. **Ratify edge-state recovery + the D4 scoping** (§10.7): automatic quarantine (tightening only) for all links, 2-grader confirmed (raw evidence, no falsifier framing), 3-grader for seed links; the v3.2 propagation rules (§10.4); INCONCLUSIVE escalates the RULE, not the case.
3. **Ratify the seed gauntlet as a launch gate** (§8.3) incl. seed cards earning ESTABLISHED (unprovable → YOUNG).
4. **Ratify launch blockers**: the corrected model-free falsifier + ATTACH audit before production writes (§9); audit intensity on flagged heads is bounded (100% for first N/T, then risk-stratified) with a hard SLA that never hangs on the owner queue.
5. **CLAIM ships OFF** [owner ruling 2, adopted]: shadow-log from Phase 2; ON only after S3 (pre-locked keys, per-arm forked state, ratchet instrumentation, false-refusal/recall metrics) passes with zero wrong links.
6. Carried: gate protocol amendment (meaning-judged synonym-creates; links graded in-window) · experiment program + promotion rules (anchor-enrichment M2 and item-code evidence M3 are experiment-gated, default OFF) · G1 display spec · OD-7 born-complete · the [PIN] set · reject auto in-context teaching · thresholds post-calibration · time/standard-keyed anchor revalidation escalates as an owner RULE question (completeness #6) · outage discipline (RETRY-age alarms, drain rate-limiter, catalog-frozen signal flag) · ADOPT takes the same 3-part confirmation as ATTACH (completeness #12).

## §16 Honest residuals

- The irreducible floor is now precisely: a single-shot hardened judge wrong on a genuinely co-extensive-looking pair at FIRST encounter, before any falsifier signal exists — identical for both triggers, measured by OD-6, reversible by §10 once evidence accumulates. Zero-by-construction remains impossible; zero-by-measurement with honest upper bounds is the enforceable promise.
- Homonym facts written before detection stay on the quarantined node as flagged history — contained, never erased (ids immutable), excluded from features.
- All in-session judges/graders share one model vendor; the falsifier is the only fully independent oracle. Stated, not hidden.
- **Qualitative homonyms have no model-independent tripwire [v3.3 — stated, not masked]:** for no-XBRL, non-numeric heads (news/action_event), falsifier channels (i)–(iv) are silent and (v) detects duplicates, not one-name-two-meanings; the only watchers are the same-vendor drift/dispersion probes and audits. The deepest-worry residual lives exactly here; the quarterly held-out gate re-runs are its backstop, and the MVP rule (§15.0) forbids leaving this space uninstrumented.
- **History completeness is the ambition's success metric [v3.3]:** the composite "fraction of a cause's true facts its canonical series contains at query time" (duplicate half-life + reconciliation efficacy + park drain + false-refusal rate) is a first-class dashboard number — the memory must be USEFUL, not merely uncorrupted.
- Conservative splits and deferred thin pairs under-attribute history during their window — the safe direction, visible in §9.7 metrics.

*v3.4 (LOCK CANDIDATE) = v3.3 + the citation-diff doc-fixes + the §11.0 model-tiering lock (owner 2026-07-07); no other design content changed. v3.3 assembled 2026-07-07: v3.2 + the three-auditor lock-read (wf_42ef5242-9d9 — verdicts: deaths-auditor NOT-LOCKABLE→two blockers fixed here as L1/L2; minimality-auditor: no overengineering blocker, MVP defined §15.0; contradiction-auditor: LOCKABLE-WITH-ERRATA, all folded). Remaining pre-lock step: the citation-diff of locked-rule paraphrases against binding topic docs (a doc-editing pass, no design content). v3.2 was assembled from: the v3/v3.1 full texts; first-hand re-verification of the v1/v2 deaths (DriverContext.md:39-40 · evolution.md:7,17,56 · DriverExperiment.md:29-36 · INDEX.md:54,172,207 · 01/02); WorkflowContextPack.md; the seven-agent adversarial pass (run wf_2b8e6c4f-aef); the owner's five rulings; and the final three-agent perfection pass (owner-devil's-advocate, mechanism-attacker, completeness critic — run wf_78f550ec-12a). Every FATAL/MAJOR finding from both passes is dispositioned inline. On any conflict, the cited topic doc wins.*
