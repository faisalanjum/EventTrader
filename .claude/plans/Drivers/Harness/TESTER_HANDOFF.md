# Driver Harness — TESTER HANDOFF  *(read this fully; you are the harness tester)*

> **One-line role:** You are the **tester/iterator** for an isolated, test-first harness that proves a
> "driver name-cleaner" works on every requirement + risk **before** any production wiring. A **separate
> builder bot** writes the code from `Harness_BuilderPrompt.md`; **you run it, hammer it with edge cases,
> drive the real-LLM layer IN-SESSION, judge results, and authorize each phase.** This doc + the files it
> points to = everything you need. Read §1 (⚠️ non-negotiables) before doing anything.

---

## 0. The mission (what + why)

The project owner (Faisal) had **paralysis-by-analysis**: a 6,000-line, LLM-built "driver naming" plan he
couldn't verify and feared was bloat. Decision: **stop arguing prose; build the deterministic core as an
isolated harness and PROVE it** on the hardest real-world cases. Green deterministic tests prove the mechanical core; `eval_report.json` is the real accuracy authority.

**What a "driver" is:** a reusable, canonical name for a *cause that moved a stock* (e.g. `iphone_china_sales`).
The system forces many LLMs' messy spellings → **one** canonical driver, so the graph is queryable. The
ontology + a pure Python `canonicalize()` make naming deterministic; the LLM only proposes, Python decides.

**Scope of THIS harness = driver CREATION only** — everything that turns evidence into a clean, validated,
canonical name + companion fields, **up to but NOT including the Neo4j write**. The DB write (ingestion) is
delegated to a clone of the existing **guidance pipeline** and is OUT OF SCOPE here.

**Producers (news-from-start, per the owner):** `earnings-learner` + `news` produce drivers from day one;
`fiscal.ai` later. **(Harness-generality scope, 2026-05-29):** the harness exercises BOTH producers from the start to prove the shared writer/canonicalize is **producer-agnostic** (one canonical driver per concept, whoever emitted). This is a TEST-coverage choice — in **production**, Phase-1's sole driver-registry producer is **`earnings-learner` (learner-only per E30)**; `news` is Phase 2, `fiscal.ai` Phase 3. `earnings-predictor` is a **consumer only** (never writes drivers). All producers consult
ONE global registry and reuse-before-create.

---

## 1. ⚠️ NON-NEGOTIABLES (get these wrong and you cost money or invalidate the tests)

1. **BILLING — the most dangerous one.** Run real-LLM tests **IN-SESSION** (your interactive Claude Code
   session = entrypoint `cli` = **subscription, $0**): spawn in-session **subagents / workflows** as the
   producer-LLM. **NEVER** call `claude_agent_sdk.query()` or `claude -p` — those are entrypoint `sdk-cli` =
   a **METERED pool at full API rates** (~14 runs/mo on Max, then real charges). **NEVER** `import anthropic`,
   set/read `ANTHROPIC_API_KEY`, or fall back to a key to "fix" a failed call. Source of truth:
   `.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md`.
2. **NEVER `sed -i` / automated-edit `~/.bashrc`** (it truncated to 0 bytes once). `.env` is also a billing
   landmine. Don't touch either.
3. **Scope fence:** the harness is creation-only. The spec file `DriverOntology_Implementation.md` also contains
   ingestion machinery — **IGNORE §F.10, §J, §K and anything Neo4j/Cypher/MERGE/EquivalenceToken/VocabToken/
   supersession/`*_visible_at`/audit-tables.** Read only §C, §D, §D.1, §E, §F.1–§F.9 for rules.
4. **Prod-core copies UNCHANGED; tests are a SEPARATE component.** The pure modules (`driver_ids`, `validators`,
   `vocab_seed`, `reuse`, `render_catalog`, `run_one`, the adapter) must import nothing test-only and copy into
   production with zero changes. All replay/eval/fake-registry/LLM-glue is TEST-SCAFFOLD that stays behind.
5. **The accuracy authority is `eval_report.json`'s GO/NO-GO — NOT pytest-green.** Deterministic tests gate at
   100%; the real-LLM layer is **measured** (non-deterministic), never a hard pytest gate.
6. **Never rubber-stamp.** The owner regularly pastes other bots' reviews and asks you to evaluate them.
   **Verify every claim against the live files (cite file:line)** before agreeing — this plan has a long
   history of stale-state false-positives. Flag overstatements (e.g. "100% accuracy", "100% reuse").
7. **Permission before edits.** Show the diff/plan and wait for approval before changing any file. Do exactly
   what's asked; propose extras separately.

---

## ⚖️ LLM-vs-CODE BOUNDARY — architecture principle (owner, 2026-05-29; REVISIT on the triggers below)

Do NOT use deterministic code where an LLM is more accurate. **LLM = semantic judgment** (meaning · novelty ·
ambiguity); **CODE = mechanical consistency** (exact-match · format · slot ORDER · length · validators · the
deterministic fold). As tester, **audit this boundary every phase** and flag where code over-rejects on a semantic call. **Governing rule:** *"Producer LLM handles semantics first. Isolated judge handles borderline/global/irreversible cases. Code persists, gates, and replays decisions deterministically. Gate strength scales with blast radius × irreversibility."*
- **Correctly LLM-led:** reuse-from-catalog · K23/K30/K47/K52 · R9 granularity · Pass-4 accuracy.
- **Correctly code:** canonicalize formatting · exact-match folds · slot order · length · validators V1–V14.
- **🟡 3 watch-spots + REVISIT TRIGGER each:**
  1. **New-word SLOT placement** (`resolve_unknown_slots` rejects ambiguous novel tokens, e.g. `blackwell_revenue`). **REVISIT IF** Pass-4 false-rejects legit new drivers → producer **DECLARES the slot**; code = backstop.
  2. **Synonym DISCOVERY** (`uptake≈demand`) is an LLM call; code = N=2 gate + fold ONLY. **REVISIT IF** a candidate is code-guessed.
  3. **Banned-word completeness** — LLM (taught R7) is the real defense; the list is a backstop. **REVISIT IF** Pass-4 shows leaks.

**Recommended flow** (refined 2026-05-29): LLM emits → code dry-run validates → same-learner **self-correct loop** (≤3 tries, stop-on-no-progress; orchestrator write-gate authoritative) → code re-validates → optional isolated LLM judge (orchestrator/code-triggered) for borderline/global/irreversible cases → code writes/folds deterministically. **6 LLM-judgment uses:** informed-retry · semantic-reuse · synonym-discovery · new-token slot-declaration · evidence-SUPPORT · scope/granularity. (Keep code for identity/gates/graph-safety — the compiler half.)
Canonical: memory `feedback_llm_vs_code_boundary.md` (full refined list). Mirrored in `DriverOntology_Implementation.md` + `Harness_BuilderPrompt.md`.

---

## 2. Your role vs the builder bot

| | **Builder bot** (separate, headless) | **You — the tester** (this interactive session) |
|---|---|---|
| Reads | `Harness_BuilderPrompt.md` | this handoff + everything |
| Does | writes the harness code, one PASS at a time, STOPs after each | runs pytest, **hammers edge cases**, drives the **real-LLM layer in-session**, judges `eval_report.json`, **authorizes** the next pass, **surfaces spec bugs** (does NOT silently fix the spec) |
| Billing | offline in Pass 1/2/3 | **you** are the subscription LLM transport for Pass 4 |

---

## 3. What to read (in order, with purpose)

| # | File | Why |
|---|---|---|
| 1 | `.claude/plans/Drivers/Harness/Harness_BuilderPrompt.md` (§0–§16) | THE brief — the whole harness spec; single source (sibling of this file) |
| 2 | `.claude/plans/Drivers/_workflow/req_canonical.md` | the **test seed**: 60 deduped risks **K1–K60**, 27 reqs **A1–A27**, the rule contract **B-F/B-N/B-R/B-M** |
| 3 | `.claude/plans/Drivers/DriverOntology.md` | the naming rules **R1–R11** (what a legal name is) |
| 4 | `.claude/plans/Drivers/DriverOntology_Implementation.md` | mechanism: **§C** canonicalize 12 steps · **§D/§D.1** grammar + slot fns · **§E** validators V1–V15 · **§F.1–§F.9** vocab banks. ⛔ IGNORE §F.10/§J/§K. |
| 5 | `.claude/plans/Drivers/DriverProcess.html` | plain-English walkthrough (sanity-check intent) |
| 6 | `.claude/plans/Drivers/_workflow/{BEST_WAY_driver_creation,scope_split}.md` | the verified minimal-creation plan + the creation/ingestion fence |
| 7 | `.claude/plans/Drivers/{ConceptualRequirements,DriverNameRisks,DoubtsInHTML}.md` | the owner's requirements / risks / doubts (sources behind req_canonical + the §14 doubt-ledger) |

Guidance pipeline (the ingestion reuse target, for context): `.claude/skills/earnings-orchestrator/scripts/{guidance_ids,guidance_writer,guidance_write_cli}.py`.
Build folder (currently empty, ready): `drivers_harness/`.

---

## 4. The phases — what each must PROVE

- **Pass 1 — deterministic CORE (offline, GATED 100%).** `canonicalize` + classify/slot fns (§D.1) +
  validators V1–V14 + reuse B1–B10 + vocab banks + render_catalog + run_one. Tests: one per CREATION-scoped
  **K1–K60** + CREATION-binding **A-items** + the field/gate contract + bucket **K** (idempotency incl. the
  shortcut/compound names) + the ADVERSARIAL/BOUNDARY bucket + the production-order `test_sequence`.
- **Pass 2 — synonym-learner (offline, GATED 100%).** In-memory N=2 promotion; synonyms only; promoted synonym
  feeds the next snapshot. (Plurals/acronyms stay static.)
- **Pass 3 — deterministic ACCUMULATION replay (§15A) + false-reject regression (§15C), GATED 100%.** Events in
  SEQUENCE, registry accumulates via `apply_decision`, reuse converges, 0 duplicates, cross-run idempotency —
  all deterministic, so this CAN be 100% green.
- **Pass 4 — real-LLM eval (§13 single-event fixtures + §15B real-corpus accumulation), IN-SESSION, MEASURED.**
  → `eval_report.json` GO/NO-GO (accuracy-vs-gold). This is the true accuracy picture (a measured rate, not 100%).

**4 risks are LLM-judgment, NOT mechanically testable** → Layer-2 only, never a deterministic Pass-1 test:
**K23** (mechanism-collision), **K30** (wrong-discriminator), **K47** (alias-undermatch), **K52** (wrong reuse).

---

## 5. Current state (as of 2026-05-29)

- **The brief (`Harness_BuilderPrompt.md`) is FINAL** (§0–§16) — survived multiple independent review rounds.
- **Pass 1 is BUILT + tester-signed-off through THREE corrective rounds (2026-05-29; 228 tests green, 0 skips).**
  `drivers_harness/` is populated (8 prod-core modules + 10 test files), production guard clean (23 files
  byte-identical). Round 1 = 3 bugs + coverage gaps; round 2 = multi-token freeze-scope (us_gaap/vision_pro) +
  direction/size bans; round 3 = the atom-aware-split TAIL (reuse B9 banned re-check + V4 segment side) so
  `short_interest`/`vision_pro_china_sales` survive the FULL reuse/V4 path. **Pass 2 awaiting owner authorization.**
- **NO production precondition (decided 2026-05-29):** the live `earnings-learner/SKILL.md` is **left UNTOUCHED**.
  Pass 4's producer is a **standalone driver-emit prompt** (= §13 `build_emit_prompt`) emitting the NEW
  `{driver_name, driver_state, direction, evidence}` shape (`primary_driver` + `contributing_factors[]` +
  `propose_new_drivers[]`); `category` is dropped (collides with the no-category rule). The live skill carries the
  OLD `{summary, category}` shape — that's fine; the harness never reads or edits it. **Integration is a later,
  owner-authorised step:** transplant the proven prompt into the live learner, then run a small Pass-4-style smoke
  on the REAL integrated learner (**duplicate-green ≠ integrated-green**). See brief §13 "PIN TO REALITY".
- **A spec edit already landed today:** `DriverOntology_Implementation.md` **§D.1** now defines the real slot
  functions (`freeze_known_atoms`, `classify_token`, `resolve_unknown_slots`, `order_by_slot`,
  `effective_slot_count`, `rejoin_compound_metrics`) + canonicalize steps **4.5 / 8.5 / 9.5 / 10-collision**.
  The builder implements these verbatim.
- **✅ RESOLVED (2026-05-29) — the §C shortcut/compound idempotency bug:** the prior "step-5 normalize mangles a
  shortcut/compound fragment" issue (`fda_approval`→`fda_approvals`, `gross_margin` via `margin→gross_margin`) is
  FIXED in the spec by **`§C step 4.5 freeze_known_atoms`** (freeze known atoms before step-5; step 5 skips them).
  Bucket K idempotency on `fda_approval`/`gross_margin`/`cloud_gross_margin` MUST now be GREEN. If it reds, it's a
  builder mis-implementation of step 4.5 — fix the code to match §C; do NOT edit §C or a seed fold.
- **Known issue the harness must still SURFACE, not fix:** CON-2 new-token-gate range must include §F.6.
  The prior §F.5-vs-§F.9 `restricted`/`accumulated` contradiction is resolved in the spec (2026-05-29):
  both stay §F.5 STATES and were removed from §F.9 ALLOWED_VERBAL_FORMS.

**Next action:** hand the builder `Harness_BuilderPrompt.md`; when Pass 1 returns, you run pytest + the coverage
ledger, then hammer (order below).

---

## 6. Your plan of action when Pass 1 lands

1. `source venv/bin/activate`; `pytest -q` from `drivers_harness/` → must be green.
2. Check the README **coverage ledger**: every CREATION-scoped K/A/B/doubt → a test. Flag any silently dropped.
3. **Hammer hardest first:** the new-token slot gate (§D.1 multi-anchor) · bucket-K idempotency on shortcuts +
   compounds (must be GREEN via §C step 4.5 freeze_known_atoms — verify the builder implemented it) · the
   CON-2 TODO · the false-reject regression set (no valid
   name wrongly rejected) · the ADVERSARIAL stacked/boundary cases.
4. Only when Pass 1 is rock-solid → authorize **Pass 2** → **Pass 3** (deterministic accumulation) → **Pass 4**.
5. In Pass 4 **you** are the LLM: spawn in-session subagents as the producer over the real corpus; collect
   `eval_report.json`; read the **GO/NO-GO** vs §H.9 targets. Report it to the owner honestly (measured rate,
   not 100%).

---

## 7. §16 blind spots — GREEN ≠ SAFE (tell the owner these are NOT covered here)

Concurrency races · PIT-correct historical-backfill accuracy (harness has no `registry_visible_at`, so only
LIVE/forward accuracy is honest) · evidence-semantically-supports-the-claim · real-Neo4j ≡ the fake registry
(needs the §15D contract suite against Neo4j). These belong to the **ingestion harness** / live monitoring.
The §14 doubt-ledger in the brief tags the ingestion-deferred doubts — that's the to-do list for that later harness.

---

## 7B. RE-ADD TRIGGERS — a cut goes back in ONLY on this evidence (never silently dropped)

The minimal scope **cut or deferred** several items (tracked in `_workflow/scope_split.md` + `BEST_WAY` +
the brief §8 + §14 ledger). **None is permanent.** Each has an explicit RESTORE TRIGGER measured by the
harness. If a trigger fires, **surface it to the owner and propose restoring that item** — do NOT leave a
proven-needed cut out, and do NOT widen scope on your own.

| eval/test symptom (the evidence) | what to restore | source |
|---|---|---|
| high **reject-rate** on state/period/magnitude smuggles (LLM keeps emitting `opec_supply_cut`-style names) | **Lever #1 writer auto-repair** (deterministic state-strip) | brief §8 / CombinedPlan E26 |
| **reuse-rate < §H.9** target, OR **duplication-rate** climbing across the §15 accumulation replay | first: grow the static seed/synonym maps; if still short: **instant synonym promotion** (the heavier `:EquivalenceToken` store) | brief §8 / E27 |
| same-concept duplicate drivers persist that a fold would catch | same as above (seed growth → synonym store) | E27 |
| `eval_report.json` = **NO-GO** and no single cut explains it | **STOP → report to owner**; re-open the scope decision (do not patch unilaterally) | — |
| **false-reject** count > 0 (a VALID name rejected) | NOT a cut — a `canonicalize`/vocab **bug**; fix at source + add a §15C regression test | §15C |
| concurrency / PIT-backfill / "real-Neo4j ≡ fake" questions | NOT restorable here — by design (§16); validated in the **ingestion harness**, not this one | brief §16 |

**Rule:** cut → **measure** → **restore on its trigger, with evidence in hand** — never preemptively, never
silently dropped. This loop is what makes "minimal now" safe.

- Deferred-but-MANDATORY ingestion item — the **reconciliation job**: merge two ALREADY-REGISTERED drivers when a late-learned equivalence or judge ruling proves them the same (relink DriverChanges + supersession; judge-confirmed; reversible/un-merge; PIT-honest effective date). Audited-not-silent until it ships.

---

## 8. How the owner works with you (style — this matters)

- **ADHD:** crux-first, plain simple words, **one small concept at a time**, short replies, small visuals
  (tables/ASCII/arrows). No jargon dumps. Don't move to the next point until this one lands.
- **Explain before writeup:** lead with a plain-language "what / why" before any schema/code block.
- **Independent eval (above):** verify other bots vs the live files; never rubber-stamp; flag overstatements.
- **Strict enforcer:** never let a half-baked artifact pass; fix at the source; surface, don't paper over.
- **No `Co-Authored-By` trailer** in any git commit.

---

## 9. Glossary (so the files read cleanly)

- **K1–K60** — the deduped canonical risk list (from `DriverNameRisks.md`) in `req_canonical.md` = the test seed.
- **A1–A27** — the owner's ConceptualRequirements obligations. **B-F/B-N/B-R/B-M** — the DriverOntology contract rows.
- **R1–R11** — the naming rules. **V1–V15** — validators (harness builds V1–V14; V15 is registry-global = ingestion).
- **B1–B10** — the reuse/propose ladder. **S1–S6** — the production sequence the harness mirrors (S7 = the
  Neo4j write = out of scope). **Layer 1** = deterministic phases (gated); **Layer 2** = the real-LLM phase (measured).
- **canonicalize()** — the pure 12-step name-cleaner (the heart). **registry_fake** — the only stub; prod swaps it for Neo4j.

---

## 10. You are "super successful" when

✅ Pass 1 green + coverage ledger shows every CREATION-scoped K/A/B/doubt tested (none silently dropped) ·
✅ bucket-K idempotency (incl. shortcuts/compounds) is GREEN via §C step 4.5 freeze_known_atoms ·
✅ no false rejects of valid names ·
✅ Pass 2 synonym-learner green ·
✅ §15 accumulation replay green (0 duplicates, cross-run reuse converges) ·
✅ `eval_report.json` = **GO** vs §H.9 targets, reported honestly as a measured rate ·
✅ the §16 blind spots are stated to the owner, not assumed covered ·
✅ the prod-core modules copy into production with **zero changes**.

---

## 11. Pointers

- Auto-loaded memory: `~/.claude/projects/-home-faisal-EventMarketDB/memory/project_drivers_harness.md` (direction breadcrumb).
- Workflow audits: `.claude/plans/Drivers/_workflow/` (BEST_WAY, scope_split, req_canonical, audit_*).
- Doubt coverage: `Harness_BuilderPrompt.md` §14 (all of `DoubtsInHTML.md` #1–#51, tagged tested/by-design/deferred).
- Canonical billing rules: `.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md`.
