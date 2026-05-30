# Driver Naming — Combined Final Plan

> ⚠️ **NAMING CORE UNDER REDESIGN (2026-05-30):** the closed-vocabulary/`canonicalize` approach in this plan was empirically measured **rejecting 82% of even *correct* driver names** → it is being re-designed from first principles. **Canonical handoff + full empirical record: [`UnifiedRedesignBrief.md`](./UnifiedRedesignBrief.md)** — read it before building on this plan's naming core.

> **Status**: Final consolidated plan, ready for voting review.
> **Sources synthesized**: 5 independent LLM audits (Bot1, Bot2, Bot3, ClaudeBot1, ClaudeBot2) + my own ConceptualRequirements walk + Final.md cross-reference.
> **Goal**: ≥95% driver naming accuracy, 100% ConceptualRequirements accounted for (covered or explicitly deferred with rationale), minimum incremental work on top of the locked ontology + guidance pipeline templates.
>
> **⚖️ LLM-vs-CODE BOUNDARY (owner principle, 2026-05-29 — revisit later):** LLM = semantic judgment (meaning/novelty/ambiguity); code = mechanical consistency (exact-match/format/deterministic fold). 3 watch-spots, each with a revisit-trigger: new-word slot placement · synonym discovery · banned-word completeness. **Full version + triggers:** `DriverOntology_Implementation.md` (top) · `Harness/Harness_BuilderPrompt.md` · `Harness/TESTER_HANDOFF.md` · memory `feedback_llm_vs_code_boundary.md`.
>
> **Governing rule (canonical):** Producer LLM handles semantics first. Isolated judge handles borderline/global/irreversible cases. Code persists, gates, and replays decisions deterministically. Gate strength scales with blast radius × irreversibility.
>
> **OPEN DECISION — driver state handling (2026-05-30):** `driver_state` / `STATES_VOCAB` normalization is NOT fully locked. The current bounded state enum is useful for comparability, but production may need a separate `raw_state` vs canonical `driver_state` policy so novel wording (e.g., elevated / unfavorable / pressured) does not falsely reject a valid driver. Lock this before ingestion/live scoring.

---

## §1. Purpose

This file is the single source of truth for what changes must land in the three driver-spec files (`DriverOntology.md`, `DriverOntology_Implementation.md`, `Neo4jXBRLDesign.md`) before any Python is written. It folds in every actionable suggestion from 5 LLM audits, resolves the conflicts explicitly, lists rejections with reasons, and surfaces the user decisions still needed to lock the spec.

Any reviewer of this file should be able to answer: "Is the resulting design perfect against the three hard conditions, yes or no?"

---

## §2. Locked Architectural Decisions

These are not up for re-debate; they frame everything below.

| # | Decision | Why locked |
|---|---|---|
| L1 | Two-file ontology split: `DriverOntology.md` (rules, stable) + `DriverOntology_Implementation.md` (mechanism, mutable). | Independent evolution; LLM reads rules + runtime envelope, not mechanism. |
| L2 | Three driver execution modes: **Mode 1** learner emits inline in `learning/result.json` (per E30 — predictor is consumer-only, NOT a Mode-1 producer); **Mode 2** news via `/extract` worker pipeline (later); **Mode 3** fiscal.ai direct ingest (later). | ConceptualRequirements §3.3 (CLARIFIED) + §2 + §4 alignment. |
| L3 | Canonicalization runs in Python (`driver_ids.canonicalize()`), NEVER in LLM head. | Determinism. LLM judgment caps at ~85%. |
| L4 | NO human curator anywhere in the loop **at runtime**. (Code-time constants — e.g., `COLD_START_SEED_DRIVERS` in `driver_writer.py` per OQ4 — are normal engineering, not runtime curation.) | User memory + ConceptualRequirements bottom-line. |
| L5 | Driver registry stored in Neo4j as authoritative; JSON snapshots are derived caches. | Source-of-truth clarity. |
| L6 | PIT visibility via `Driver.registry_visible_at = MIN(DC.pit_cutoff)` **(seed drivers exempted — use epoch sentinel; see E9)**; supersession via `superseded_at` / `superseded_pit_cutoff` / `superseded_by_run_id` triplet. **Slot-vocab bootstrap-seed exception (D1 resolution)**: the §F.1 slot-vocab seed uses SANE `vocab_visible_at` dates — TIMELESS anchors (`oil_price`, `fed_rate`, `china`, `revenue`, …) use `EPOCH_SENTINEL`; ERA-BOUND modern tokens (`iphone`, `datacenter`, `hyperscaler`, `ai`, `gpu`, `vision_pro`, …) carry realistic `vocab_visible_at` dates (err LATER = conservative) so the PIT-filtered hint excerpt excludes them on historical runs. (Code-time seed task per L4 = normal engineering; date-assignment + render-filter are integration-phase. Uses the EXISTING `vocab_visible_at` field — NOT a new mechanism.) PIT-safety of the LLM-facing layer rests on EXISTING `visible_at` fields (not a new mechanism): (a) the LLM sees only a short slot/shortcut HINT EXCERPT rendered from the PIT-FILTERED vocab snapshot (`vocab_visible_at <= run.pit_cutoff`), so historical runs are ERA-SAFE — no future-coined tokens are shown; the FULL slot-vocab classification banks stay INTERNAL to `canonicalize()` (harmless + still deterministic given the frozen snapshot, because R11 ensures only evidence-present tokens are ever classified), (b) the Driver-registry PIT gate at `Driver.registry_visible_at <= run.pit_cutoff` blocks visibility at the LLM-facing layer, and (c) R11 evidence-requirement (token must appear in evidence text) prevents proposing a name with a future-coined token under historical PIT. v9-1+v10-1 MIN-backdate still applies to RUNTIME-promoted `:VocabToken` rows (those tokens get `vocab_visible_at = source_driver.registry_visible_at` per E10). | Backfill self-shadowing prevention + re-run safety. |
| L7 | Guidance pipeline reuse pattern: writer/IDs/MERGE/concept-resolver/member-map machinery REUSED; extraction worker + `/extract` orchestrator + agent shells reused ONLY for Mode 2. | Minimalism + leverage of proven code. |

---

## §3. The Three Hard Conditions (enforcement bar)

> **Accuracy-bar clarification (resolves header Goal ≥95% vs §3 hard condition >90%)**: ≥95% = aspirational GOAL; >90% = the HARD enforcement floor (must-clear). Not a contradiction.

1. **>90% driver naming accuracy** — credibly achievable, not aspirational.
2. **100% ConceptualRequirements.md accounted for** — every section either covered OR explicitly deferred with reason (deferrals enumerated in §9 coverage matrix). **DEPENDENCY**: this hard condition assumes `.claude/plans/Drivers/ConceptualRequirements.md` is present in-repo as the source-of-truth. If the file is missing at lock time, §9 coverage matrix becomes unverifiable and §3-#2 is BLOCKED until the file is restored.
3. **Minimum extra work** — maximum reuse of guidance pipeline templates; smallest possible new code surface beyond the locked ontology rule book.

Any change proposed below is checked against these three.

---

## §4. Audit Summary (5 LLM proposals)

| Source | Items raised | Tier-1 catches (Phase-1 blockers) | Verdict |
|---|---|---|---|
| Bot1 | 7 | 0 | PARTIAL — useful polish + state vocab + R5 rename catch |
| Bot2 | 7 | 1 (alias validator bug) | PARTIAL — real correctness bug nobody else found |
| Bot3 | 10 | 0 | STRONGEST OVERALL — concurrency + slot-mapping persistence + Neo4j-authoritative |
| ClaudeBot1 | 8 | 2 (failed-proposal recipe + validation_status) | STRONGEST ON BLOCKERS — closes the two items that drag accuracy under 90% |
| ClaudeBot2 | 7 | 0 | STRONGEST ON INTEGRATION — cold-start seed + Final.md schema reconciliation + sentinel gating |

**Convergence signal**: 4 of 5 bots flagged the human/curator language purge. 3 of 5 flagged "don't overclaim 100% extraction-pipeline reuse". 2 of 5 flagged the PIT filter on bundle render.

**Post-vote audit additions (applied incrementally as each bot's review is processed):**

| Round | Source | Items merged into existing E* (modified) | New OQ added | Other doc sections touched |
|---|---|---|---|---|
| 1 | ClaudeBot2 review of CombinedPlan.md v1 | E10 (zero-anchor clause), E14 (corrected exposure_role), E16 (per-item ticker schema) | OQ4 (cold-start seed source) | §12 (volume-dependent reuse thresholds + 5 explicit per-edit tests), §13 (2 new risk rows) |
| 2 | ChatGPTBot1 review of CombinedPlan.md (post-Round-1) | E1 (STRICT failure policy pinned), E9 (seed PIT policy added), E13 (rejected-label handling), E16 (pit_cutoff/result_path/run_id added), **E22 REVERTED (singular kept; ClaudeBot1's plural was a misread)**, E23 (extended from title-only to full rename incl. `MACROS_VOCAB` → `SHORTCUTS_VOCAB`) | (none) | §9 (coverage count fixed: 9 ✅ + 3 ⏸ DEFERRED; §3.3 row reframed as DEFERRED) |
| 3 | Bot 5 review of CombinedPlan.md (post-Round-2 consistency audit) | (none — no E* item content changes) | (none) | L6 (seed exception parenthetical), §8 (manifest synced to E22 revert + E23 full-rename scope), §10 (seed → Python constant), §11 Day 2 ("macro" → "standalone" shortcut), §12 lock conditions (OQ1-OQ4; 9 ✅ + 3 ⏸), §13 risk row (Python constant phrasing), Appendix A (coverage count 9 + 3) |
| 4 | ChatGPT Bot 2 + Bot 3 reviews (deferred at evaluation time, applied post-Bot-5) | **E1 (STRICT → PARTIAL — explicit REVERSAL of Round 2 pin)**, E8 (canonical pairs enumerated; `declined` kept distinct from `deteriorated`), **E14 (CRITICAL source_id formula correction — restored stable per-{ticker}:{quarter})**, E16 (`source_catalog` field added for V10), E20 (FISCAL.AI removed from /extract; Mode 3 direct ingest per L2), E23 (tests-import note added) | (none) | Goal wording softened ("100% covered" → "100% accounted for"); §11 Day 1 (seed Python constant per OQ4) |
| 5 | Bot A + Bot B + Bot C reviews. **Bot A duplicate-noise**: 7 of 8 items already applied in Rounds 3–4 (reviewing stale state); only §12 test list fix was novel. **Bot B + Bot C #5 convergent** on E9 PIT seed leak. **Bot C** surfaced 5 distinct net items. | **E1 (exit-code semantics for PARTIAL added)**, **E8 (full STATES_VOCAB enumerated across all 7 classes; banned-alias map)**, **E9 (PIT-safe two-tier seed policy — timeless-only epoch; modern excluded or per-driver date)**, **E10 (Neo4j-backed vocab store specified per L5)**, **E16 (sidecar `{run_id}` suffix + reconciled exit codes)** | (none) | §3 Hard Condition #2 wording ("100% accounted for"); §14 Vote Request wording ("100% accounted-for"); §12 test list ("macro shortcut" → "standalone shortcut") |
| 6 | New review (17 claims). **9 false-positives** (stale snapshot — bot reviewing pre-Round-3 state for D1/D2/D4/D5/D6/N1 + math-error N6 + duplicate-of-Round-5 I2 + wrong-direction N5). **8 genuine items** accepted. | E8 (close Open Items #2 pointer) | (none) | **L4** (clarify "at runtime" vs code-time constants), **OQ3** (description updated to full-rename scope), **§8 Neo4jXBRLDesign** (Final.md §24 stale pointer fix added), **§10** (SKILL.md LOC bumped ~50 → ~150 for honesty), **§12** (cold-start test strengthened to ≥30 entries + V1-V15 + idempotent canonicalize), **§13** (slot-vocab-pollution risk row added), **E16** (per-mode source_catalog sourcing explicit) |
| 7 | Two reviews combined (5 + 4 claims). **Critical honest correction**: prior rounds (R3 B3-1, R5 Bot C #1) flagged `ConceptualRequirements.md` as missing; this plan WRONGLY rejected those as "false claim". Round 7 ls verification confirmed the file IS missing. All 3 prior rejections were errors caused by trusting system-reminder cached context instead of filesystem. | E17 (`null for non-financial drivers` wording), E9 (expanded TIER 1 to ~32 anchors covering macro/metric/geography/institution slots; explicit slot-coverage note for object/customer/theme gap) | (none) | **§3 #2** (file-dependency note: §3 BLOCKED until ConceptReq restored), **§9** (file-dependency warning added at footer), **§13** (manual-pruning wording → code-time pruning to align with L4), **§11 Day 3** (MIN seed exception + `null for non-financial` wording), **Appendix A** (per-file LOC counts updated to match §8 manifest: 5/60/20 instead of stale 1/40/15) |
| 8 | Two reviews combined (5 + 2 claims). **2 substantive accepts** (N1 §8 per-file arithmetic stale; M1 Day 5 overload after Round 6 ~150 LOC SKILL.md bump). **4 stale-snapshot rejects** (N2 ~15-20 already addressed Round 7; M2 MIN seed exception already added Round 7; M3 Round 6 row exists at line 64; Bot R/S ConceptReq + seed count already acknowledged/addressed Round 7). | (none) | (none) | §8 per-file synced to 5/60/20 (matches Appendix A Round 7 update); all "~75 lines" refs (4 places) → "~85 lines" for consistency; §10 timeline bumped 5-7 → 6-8 days reflecting Round 6 SKILL.md LOC correction; §11 Day 5 load warning added with split fallback |
| (rejected) | (Round 8 rejections) N2, M2, M3 — all stale-snapshot artifacts (bot reviewing pre-Round-7). Bot R + Bot S concerns — already acknowledged/addressed in Round 7. Bot S seed-count "contradiction" — false; E9 now ~32 anchors, §12 ≥30 entries, mathematically consistent. | — | — | — |
| (rejected) | (Round 7 rejections) Latest bot's Claim 3 framing "lower the cold-start accuracy claim" — partially rejected (we addressed via TIER 1 expansion + slot-coverage note instead of lowering accuracy claim). All other Round 7 claims accepted. | — | — | — |
| (rejected) | (Round 6 rejections) **N5** OQ5 STRICT/PARTIAL — bot has it backward; Round 4 already reversed to PARTIAL; trade-off documented in E1. **N6** L6↔E9 contradiction — false on TWO grounds: L6 has exception carve-out per Round 3, AND MIN(epoch_sentinel, future_date) = epoch_sentinel mathematically. **I2/D1/D2/D4/D5/D6/N1** — bot reviewed pre-Round-3/4 state; all already fixed. | — | — | — |
| (rejected) | ChatGPT Bot 2 #2 (E22 plural) — already reverted Round 2. ChatGPT Bot 3 #1 (ConceptReq file not found) — factually wrong; file exists. **Round 5: Bot A #1–4, #6–8** — duplicate of Rounds 3–4 applies (Bot A reviewed stale state). **Round 5: Bot C #1** — duplicate false claim of B3 #1. **Round 5: Bot C #5** — convergent with Bot B #1 (counted once under E9 fix). | — | — | — |

---

## §5. Final Consolidated Edit List (24 items + 1 my-own = 25 total)

Each item below has been independently verified against the three hard conditions.

### 5.1 Tier 1 — Phase-1 Blockers (4 items, must close before any code)

**[E1] Failed-proposal recipe (PARTIAL policy with audit — REVERSED from Round 2 STRICT; explicit exit-code semantics)**
- Location: `DriverOntology_Implementation.md` §A.1 Mode 1, append bullet
- Text: "On §B10 fail (single proposal cannot canonicalize): orchestrator REJECTS that proposal, logs to `driver_proposal_rejection` audit row, and PROCEEDS with remaining valid proposals. `complete.json` sentinel fires IFF (a) ≥1 driver successfully wrote AND (b) no system/writer infrastructure failure occurred. BLOCK sentinel only when: (i) ALL proposals fail (no useful drivers landed), OR (ii) writer/system fails (Neo4j down, file I/O error). `result.json` preserved verbatim in all cases. Failed runs may be re-run.

  **EXIT-CODE SEMANTICS** (writer ↔ orchestrator contract; reconciles partial policy with E16 exit codes):
  - `exit 0` (sentinel fires): ≥1 driver wrote successfully; system OK. Sidecar JSON reports `accepted_count`, `rejected_count`, per-driver rejection reasons.
  - `exit 1` (sentinel blocks): ALL proposals failed (zero drivers wrote). Sidecar JSON reports all rejection reasons.
  - `exit 2` (sentinel blocks): writer/system infrastructure failure (Neo4j down, file I/O error, schema constraint violation). Sidecar JSON may be incomplete.
  - Orchestrator reads exit code: 0 → write `complete.json`; 1 or 2 → mark run failed in `run_ledger`, no sentinel."
- Source: ClaudeBot1 #1 (original recipe) + ChatGPTBot1 #4 (asked for clarification) + ChatGPTBot2 #4 + ChatGPTBot3 #4 (PARTIAL reversal) + **Round 5 Bot C #6** (exit-code semantics pinned)
- Why: Round 2 STRICT pin was operationally too brittle — one malformed driver tag (e.g., LLM emits motion noun "collapse") would throw away the entire prediction. PARTIAL with explicit audit aligns with guidance-pipeline precedent. Without explicit exit-code semantics, the original E16 `1=validation_fail` collided with the PARTIAL policy (some validations may fail while sentinel still fires). New semantics: exit code reflects SENTINEL OUTCOME (fire / block), not granular per-driver verdicts (those go in sidecar).

**[E2] Resolve `validation_status` (drop or mechanical-only)**
- Location: `Neo4jXBRLDesign.md` Open Items #3 + 5 doc references
- Text: "RESOLVED: drop `validation_status` field from `Driver` schema. All registered drivers are reusable. Remove all references in TL;DR steps, Phase 1 step 3, line 159, Open Items #3, and §"Locked"."
- Source: ClaudeBot1 #4 + Bot3 #2
- Why: Phase 1 is NOW; orchestrator code at TL;DR step 3 has no spec for what `provisional` means at promotion time. Silence blocks the build. User memory says "no curator ever" → drop is simpler than mechanical promotion.

**[E3] Purge all human/curator/manual-review language from `Neo4jXBRLDesign.md`**
- Location: `Neo4jXBRLDesign.md` throughout
- Action: grep for `curator`, `human`, `manual review`, `validation_status: provisional`, `curator-seeded`, `curator confirms`, `human-curated`. Replace with system/bootstrap-seed semantics OR remove.
- Source: Bot1 #2 + Bot2 #5 + Bot3 #1 + ClaudeBot1 (inferred)
- Why: 4 of 5 audits independently flagged this. Directly conflicts with L4.

**[E4] Fix `DriverOntology_Implementation.md` §A vs §A.1 wording contradiction**
- Location: `DriverOntology_Implementation.md` §A bullet 1
- Text: Change "At each emission, the orchestrator injects into the LLM prompt..." → "Once per predictor/learner session (bundle context) OR once per /extract worker invocation."
- Source: ClaudeBot1 #2
- Why: Reading §A then §A.1 produces a contradiction. Mode 1 is per-session, not per-emission.

### 5.2 Tier 2 — Accuracy-Critical Fixes (7 items)

**[E5] PIT filter on bundle registry catalog**
- Location: `DriverOntology_Implementation.md` §A.1 Mode 1
- Text: "Registry catalog rendered into predictor/learner bundle is filtered by `Driver.registry_visible_at <= run.pit_cutoff` for historical runs; unfiltered for live runs."
- Source: ClaudeBot1 #3 + ClaudeBot2 #7
- Why: Without it, historical backfills see future-coined drivers → vocabulary leak → biased reasoning.

**[E6] Fix alias validator V1 (correctness bug)**
- Location: `DriverOntology_Implementation.md` §E V1
- Text: Change `canonicalize(entry) == entry` → `canonicalize(entry) == parent_driver.name`.
- Source: Bot2 #3a
- Why: Current rule REJECTS valid order/spelling variants. e.g., `china_iphone_sales` as alias of `iphone_china_sales` would fail because `canonicalize(china_iphone_sales) = iphone_china_sales != china_iphone_sales`.

**[E7] Shape regex must reject consecutive underscores**
- Location: `DriverOntology_Implementation.md` §D shape regex
- Text: Tighten current `^[a-z][a-z0-9_]*[a-z0-9]$` to `^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$` OR add validator `V_no_consecutive_underscores`.
- Source: Bot2 #3b
- Why: Ontology bans `__` but current regex allows it. Mismatch weakens determinism.

**[E8] Standardize state vocab (full canonical STATES_VOCAB enumerated; preserve distinct class concepts; closes Open Items #2)**
- Location: `DriverOntology_Implementation.md` §F.5 STATES_VOCAB
- Action: Pin one canonical past-tense form per concept across ALL 7 classes (full enumeration, not "per implementation pass"):

  ```
  financial_outcome:  beat, missed, inline, raised, lowered, reaffirmed, withdrawn
  quantity_move:      cut, expanded, contracted, exhausted, built, cleared, accumulated
  policy_action:      imposed, eased, lifted, restricted, approved, denied, lapsed
  rate_curve:         steepened, flattened, inverted, normalized
  event_lifecycle:    announced, initiated, completed, cancelled, delayed
  trend_motion:       accelerated, decelerated, stable, declined, compressed
  sentiment_motion:   improved, deteriorated

  Banned aliases (LLMs may emit these — orchestrator normalizes):
    miss → missed,  raise → raised,  lower → lowered,
    reaffirm → reaffirmed,  withdraw → withdrawn,
    cut(verb) → cut (kept),  expand → expanded,  contract → contracted,
    impose → imposed,  approve → approved,  deny → denied,
    steepen → steepened,  flatten → flattened,  invert → inverted,
    announce → announced,  complete → completed,  cancel → cancelled,
    accelerate → accelerated,  decelerate → decelerated,  decline → declined,
    compress → compressed,  improve → improved,  deteriorate → deteriorated
  ```

  **KEEP DISTINCT — DO NOT COLLAPSE**: `declined` (trend_motion: revenue/margin going down) ≠ `deteriorated` (sentiment_motion: credit quality / tone going negative). Different state classes, different phenomena.

  **ALSO**: This enumeration RESOLVES `Neo4jXBRLDesign.md` Open Items #2 (state vocabulary closed list); mark Open Items #2 as CLOSED with pointer to `DriverOntology_Implementation.md` §F.5 STATES_VOCAB.
- Source: Bot1 #5 + ChatGPTBot2 #5 + ChatGPTBot3 #5 + Round 5 Bot C #4 + **Round 6 P2** (close Open Items #2)
- Why: Inconsistency → LLMs pick different verbs for same motion → driver_state drift. Round 3 only pinned financial_outcome explicitly; remaining 6 classes had "per implementation pass" handwave. Full enumeration removes interpretation surface for the engineer building canonicalize().

**[E9] Cold-start seed (with PIT policy — timeless-only epoch + per-driver date for modern)**
- Location: `DriverOntology_Implementation.md` §A.1 OR §J
- Text: "Before first predictor/learner production run, Driver registry MUST be pre-seeded with ~30 anchor drivers spanning all slot types. Without this, less-capable LLMs lack slot-classification anchors and accuracy drops to ~80%.

  **SEED PIT POLICY — TWO TIERS** (revised per Bot B + Bot C convergence to prevent PIT leakage):
  - **TIER 1 (timeless tokens — always valid as driver-name building blocks)**: covers MULTIPLE slot types so anchor coverage spans the grammar:
    - macros: `yield_curve`, `fed_rate`, `ecb_rate`, `boj_rate`, `oil_price`, `oil_supply`, `vix`, `credit_spread`, `treasury_yield`, `usd_index`, `inflation_rate` (~11)
    - universal compound metrics: `gross_margin`, `operating_margin`, `net_margin`, `free_cash_flow`, `operating_cash_flow`, `capital_expenditure` (~6)
    - timeless geographies: `china`, `us`, `japan`, `eu`, `india` (~5)
    - timeless institutions: `fed`, `opec`, `ecb`, `fda`, `sec` (~5)
    - timeless generic metrics: `revenue`, `sales`, `capex`, `opex`, `eps` (~5)
    - Total: ~32 anchors covering metric/geography/institution/macro slot types.
    All get `registry_visible_at = epoch_sentinel` (`1970-01-01T00:00:00Z`) — these tokens are not bound to any modern event/product/era.
  - **TIER 2 (modern / product / company-specific)**: e.g. `iphone`, `hyperscaler`, `datacenter`, `ai`, `ev`, `ai_capex`, `fda_approval` for a specific year. These either (a) are EXCLUDED from cold-start seed (organic growth via `propose_new_drivers`), OR (b) get an explicit per-driver `registry_visible_at` = earliest plausible date.

  **Default seed scope**: TIER 1 ONLY (~32 anchors per breakdown above). TIER 2 grows organically. Adding TIER 2 to cold-start requires per-driver date evidence to prevent PIT leak.

  **Slot-coverage note**: TIER 1 does NOT cover OBJECTS (iphone/mac/datacenter) or CUSTOMERS (hyperscaler/enterprise) or THEMES (ai/ev) slot types — those are all era-bound. Early-run accuracy for object/customer/theme classification depends on first ~3–5 propose_new_drivers landing successfully; until then, slot inference for these tokens may drift more than for the slots TIER 1 covers.

  L6's `MIN(DC.pit_cutoff)` rule does NOT apply to seed drivers at bootstrap (they have zero DCs); once real DCs land, the seed's `registry_visible_at` stays at the assigned bootstrap value unless explicitly recomputed."
- Source: ClaudeBot2 #1 + ChatGPTBot1 #3 + **Round 5 Bot B + Bot C #5** (convergent — timeless-only epoch; per-driver date for modern; defaults to TIER-1-only to avoid PIT leak)
- Why: Original epoch-for-all policy would PIT-leak: a 1990 backfill would see `iphone_china_sales` in the registry catalog, contaminating LLM vocabulary with future-coined names. Two-tier policy preserves anchor benefit for timeless drivers while preventing vocabulary leak for modern ones.

**[E10] Persist accepted new-token slot mappings (Neo4j-backed vocab store) — AMENDED per v9-1 + v10-1**
- Location: `DriverOntology_Implementation.md` §B10 outcome + §F.1 vocab-growth note
- Text: "When `propose_new_drivers[]` introduces a token not in §F.1 slot vocabs and orchestrator accepts the proposal, the token is appended to the **live Neo4j-backed vocab store** (e.g., `(:VocabToken {slot, token, added_at, source_driver_id, vocab_visible_at})` nodes) keyed by slot type, so future canonicalization is deterministic. **STORAGE**: per L5 (Neo4j authoritative), the live vocab is in Neo4j; the markdown §F.1 list is BOOTSTRAP SEED ONLY — never mutated at runtime. The bundle renderer + canonicalize() read from the Neo4j vocab store, not from markdown. Slot is inferred from position in the proposed name relative to known tokens; tied to the Driver MERGE transaction for atomicity. **When the slot for a new token is AMBIGUOUS, the producer DECLARES the slot and a tiny isolated Pattern B judge (verdict cached/persisted, replay-by-code) resolves only the ambiguous case; on acceptance the :Driver and its tokens' :VocabToken slots are written ATOMICALLY in one transaction and canonicalize(name) is verified to round-trip under the new vocab BEFORE commit (no "written Driver with un-persisted token slot" state).** Position-based inference and the atomic write STAY code. **EDGE CASE**: if a proposal contains ZERO known tokens (no anchor for position-based inference), reject as `slot_anchor_unavailable`.

  **PIT visibility (v9-1 + v10-1)** — `vocab_visible_at` is the source-pit-anchored visibility field that closes the L6 leak via the slot-vocab path:
  - ON CREATE: `vocab_visible_at = source_driver.registry_visible_at` at write time (= MIN of that Driver's DC pit_cutoffs at write time)
  - ON MATCH: BACKDATE via `vocab_visible_at = CASE WHEN $source_pit < vocab_visible_at THEN $source_pit ELSE vocab_visible_at END` — mirrors `Driver.registry_visible_at` MIN(DC.pit_cutoff) L6 pattern. Closes the out-of-order under-visibility scenario v9-1's set-once semantics left open (closed by v10-1 per Bot A finding 1.1; reverses prior X3 deferral)
  - Read path: bootstrap loader PIT-filters via `WHERE ($run_pit_cutoff IS NULL OR vt.vocab_visible_at <= datetime($run_pit_cutoff))` — parallel to `EquivalenceToken.equivalence_visible_at` filter per v4-7
  Without this anchor + filter, historical backfills would load future-coined slot tokens unfiltered, contaminating canonicalize step 9 classification (e.g., a 2020-PIT backfill loading a `hyperscaler` token created at 2024-Q3 via runtime promotion). Same architectural class as v4-7's EquivalenceToken fix.

  **Bootstrap-seed scope** (D1 resolution, per `DriverOntology_Implementation.md` §J.2): the PIT-filter + MIN-backdate above apply to RUNTIME-PROMOTED `:VocabToken` rows (tokens appended via `propose_new_drivers[]` get `vocab_visible_at = source_driver.registry_visible_at`). For the BOOTSTRAP-loaded §F.1 slot-vocab seed (THEMES/OBJECTS/CUSTOMERS/etc.), the seed uses SANE `vocab_visible_at` dates — TIMELESS anchors (`oil_price`, `fed_rate`, `china`, `revenue`, …) use `EPOCH_SENTINEL`; ERA-BOUND modern tokens (`iphone`, `datacenter`, `hyperscaler`, `ai`, `gpu`, `vision_pro`, …) carry realistic `vocab_visible_at` dates (err LATER = conservative) so the PIT-filtered hint excerpt excludes them on historical runs. (Code-time seed task per L4 = normal engineering; date-assignment + render-filter are integration-phase. Uses the EXISTING `vocab_visible_at` field — NOT a new mechanism.) PIT-safety of the LLM-facing layer rests on EXISTING `visible_at` fields (not a new mechanism): (a) the LLM sees only a short slot/shortcut HINT EXCERPT rendered from the PIT-FILTERED vocab snapshot (`vocab_visible_at <= run.pit_cutoff`), so historical runs are ERA-SAFE — no future-coined tokens are shown; the FULL slot-vocab classification banks stay INTERNAL to `canonicalize()` (harmless + still deterministic given the frozen snapshot, because R11 ensures only evidence-present tokens are ever classified), (b) the Driver-registry PIT gate (`Driver.registry_visible_at <= run.pit_cutoff`) blocks visibility at the LLM-facing layer, and (c) R11 evidence-requirement (token must appear in evidence text) prevents proposing a name with a future-coined token under historical PIT. See L6 row in §1 + `DriverImprovements.md` v9-1+v10-1 amendments for the runtime-promotion scope this rule covers."
- Source: Bot3 #7 + ClaudeBot2 M1 + **Round 5 Bot C #3** (storage location explicit; Neo4j-backed) + **v9-1** (Bot B finding 1 — PIT-filter parallel to v4-7) + **v10-1** (Bot A finding 1.1 — MIN-on-MATCH backdate parallel to Driver.registry_visible_at)
- Why: Without persistence, slot classification for the same token may differ across runs → drift. Without explicit Neo4j storage location, an engineer might mutate markdown (which violates L5 Neo4j-authoritative) OR keep tokens in process memory (lost on restart). Without vocab_visible_at PIT-filter + MIN-backdate, historical backfills produce non-deterministic canonicalization based on wall-clock VocabToken drift (L6 leak + out-of-order under-visibility — both closed by v9-1 + v10-1).

**[E11] Concurrency safety**
- Location: `DriverOntology_Implementation.md` §B + Neo4j schema in `Neo4jXBRLDesign.md`
- Text: "`Driver.id` carries a UNIQUE constraint. Canonical lookup-then-MERGE is transactional. On concurrent-proposal collision: retry lookup and reuse existing Driver."
- Source: Bot3 #6
- Why: Predictor + learner can write simultaneously for the same event → race condition without explicit handling.

### 5.3 Tier 3 — ConceptualRequirements Compliance (3 items)

**[E12] Predictor source-visibility (ConceptReq §3.3 gap) — RESOLVED MOOT by E30**
- Status: SUPERSEDED. E30 establishes predictor is consumer-only, NOT a Mode-1 producer. Predictor doesn't emit drivers, so the "what sources should predictor see for driver emission" question is moot.
- Predictor still receives the bundle for its own analysis (prediction reasoning), but bundle widening to include transcript/10-K/Q is a separate Final.md scope question disconnected from the driver-emission concern.
- Original text (for forensics): "ConceptReq §3.3 says predictor produces drivers from 8-K + transcript (+ optional 10-K/10-Q). Current predictor bundle has only 8-K + summarized prior financials."
- Source: ClaudeBot2 #5 → resolved by E30
- Why now moot: Per E30, predictor is consumer-only. No driver-emission scope from predictor exists.

**[E30] Phase-1 producer set: learner-only (predictor is consumer)**
- Location: `CombinedPlan.md` §2 Locked Decisions (L2 amended), and propagates to E12 (moot), E14 (text), E16 (source_type enum), E20 (Phase 1 producers list), E21 (predictor §7 scope dropped), OQ2 (dropped)
- Text: "Phase-1 Driver registry producer = `learner_result` ONLY. Predictor is a CONSUMER: it reads driver_tags from prior learner reports via `prior_reports_context` (Final.md §6) for relevance ranking, and reads the Driver Registry Catalog via the bundle (per Lever #2 read path) for awareness of stock-movers — but it does NOT emit drivers to the registry. Phase-2 adds `news` producer (Mode 2); Phase-3 adds `fiscal_kpi` producer (Mode 3). Predictor's `prediction/result.json` §7 `key_drivers[]` field stays as FREE-FORM analysis prose ('short causal phrases; no controlled vocabulary/tags' per Final.md §7) — these are predictor's own thinking, never written to the Driver registry, no canonical-name discipline applied. E16's `source_type` enum drops `prediction_result` from the Phase-1 set; remains a future option if predictor ever becomes a producer (it is not in current scope)."
- Source: USER clarification (post-v4 review) resolving the ConceptReq §3.2 vs §3.3 contradiction in favor of §3.2 (learner produces, predictor consumes)
- Why: ConceptReq §3.2 + §5.4 always intended learner-only producer; §3.3's "predictor must produce drivers" wording was a contradictory artifact. ConceptReq §3.3 has been rewritten to align with §3.2. This unblocks v4-2 simplification (event-level dedup becomes effectively a no-op in Phase 1 — only one producer per event), reduces SKILL.md effort to one file (earnings-learner only), and drops OQ2 entirely.
- Downstream propagation needed (when CombinedPlan edits land in DriverOntology_Implementation.md + Neo4jXBRLDesign.md):
  - `Neo4jXBRLDesign.md` TL;DR — strip the "BOTH predictor result.json AND learner result.json" wording; keep only learner path
  - `Neo4jXBRLDesign.md` source_id formula table — `prediction_result → "predictor:{ticker}:{quarter}"` row stays in spec (audit reference) but flagged "not used in Phase 1"
  - `DriverProcess.html` — regenerate sections that show predictor as producer (C1.5 predictor result.json example, etc.) to reflect consumer-only role
  - `earnings-prediction/SKILL.md` — NO anti-pattern checklist needed; predictor doesn't emit drivers. Only `earnings-learner/SKILL.md` gets the emission contract changes.

**[E13] Fiscal.ai consults registry (ConceptReq §6 compliance) + rejected-label handling**
- Location: `Neo4jXBRLDesign.md` Phase 3
- Text: "Phase 3 fiscal.ai Option A (direct ingest, no LLM) MUST consult registry under canonical form before MERGE; raw KPI labels canonicalize through the same `driver_write_cli` pipeline as LLM proposals, just without the LLM step. Honors §6 'must be consulted by all producers.' **REJECTED-LABEL HANDLING**: If canonicalize rejects a raw fiscal label (banned content, shape violation, slot ambiguity), NO Driver is MERGEd; rejection is logged to `driver_proposal_rejection`. Whether to preserve rejected raw labels in a separate non-canonical store is a Phase-3-only decision, out of scope for Phase 1 spec lock."
- Source: ClaudeBot1 #8 + **ChatGPTBot1 #7** (rejected-label-handling clause)
- Why: ConceptReq §6 says all producers consult registry. Without rejected-label handling, fiscal.ai could either pollute canonical registry with sub-canonical labels OR silently lose data.

**[E14] Direction + exposure_role + evidence_refs vs source_id clarification (CRITICAL source_id formula correction)**
- Location: `Neo4jXBRLDesign.md` DriverChange schema notes
- Text:
  - "LLM emits `direction`; persisted on `FOR_COMPANY` edge per company; not part of driver identity. `exposure_role` (producer/consumer/supplier/competitor/neutral) also lives on this edge but is populated ONLY by the news pipeline when one DriverChange affects multiple companies with non-uniform signs (e.g., OPEC supply cut → producers long + consumers short). Phase 1 producer (learner only, per E30) emits a single ticker and does NOT emit `exposure_role`."
  - "`source_id` = STABLE per-emission identifier following the locked formula from `Neo4jXBRLDesign.md` §source_id FORMULA: `learner:{ticker}:{quarter_label}` / `news:{news.id}` / `fiscal:{ticker}:{quarter_label}:{kpi_slug}`. The `predictor:{ticker}:{quarter_label}` formula is preserved in the spec table for forensic/audit completeness but is NOT used in Phase 1 (per E30: predictor is consumer-only, not a producer). **CRITICAL: source_id MUST be stable across re-runs of the same emission** — re-running the same learner on the same ticker+quarter must produce the same source_id, which is what enables supersession (L6) to detect dropped drivers across re-runs. `run_id` is a SEPARATE field (per E16) tracking individual run identity; it goes into the `superseded_by_run_id` triplet, NOT into source_id. `evidence_refs[]` carry the underlying event/report/transcript/news IDs the LLM cited as evidence. `CITES_EVIDENCE` edges are derived best-effort from parseable `evidence_refs`."
- Source: Bot1 #4 + Bot1 #7 + ClaudeBot2 Gap 3 + **ChatGPTBot3 #3** (CRITICAL: source_id formula correction — restored locked stable-per-{ticker}:{quarter} form; previous "prediction_run_id" wording was wrong)
- Why: Previous E14 text said `source_id = prediction_run_id` which BREAKS L6 supersession (run-scoped IDs change every run → orchestrator cannot detect dropped drivers across re-runs). The locked design has always been per-{ticker}:{quarter} for stability. This is a real correctness bug in v1, not a wording polish.

### 5.4 Tier 4 — Architectural Clarity (7 items)

**[E15] Mirror Map fixes**
- Location: `DriverOntology_Implementation.md` §J
- Changes:
  - Replace `"registry+vocab loader ← warmup_cache.py concept-cache loader"` with `"registry+vocab loader ← bundle renderer's guidance query 7A pattern"`. (`warmup_cache.py` is XBRL-concept-specific; misleading.)
  - Add row: `"driver_concept_resolver.py ← concept_resolver.py (financial-sliver only; null xbrl_qname for macro/news/positioning drivers)"`.
  - Add row: `"Neo4j constraints in driver_writer.create_driver_constraints() ← guidance_writer.create_guidance_constraints()"`.
  - Add to NEW logic: `"Supersession handlers (R15 #1) — no guidance equivalent; new in driver_writer.py"`.
- Source: ClaudeBot1 #6
- Why: Engineer copying the mirror map verbatim would hit wrong file + miss real work.

**[E16] Shared writer contract (source-agnostic input JSON, multi-ticker safe, PIT-complete, evidence-verifiable)**
- Location: `DriverOntology_Implementation.md` §J sub-section
- Text:
  ```
  input JSON: { source_id,
                source_type ∈ {learner_result, news, fiscal_kpi},
                              // v7-3: prediction_result REMOVED per E30 +
                              // ConceptReq §5.4 — predictor is consumer-only
                              // (permanent stance, not "for now"); the
                              // writer never receives prediction_result.
                              // Historical Round-2/3 forensic rows in this
                              // file may still reference predictor formula
                              // as audit trail; current writer contract is
                              // learner + news (Phase 2) + fiscal_kpi
                              // (Phase 3) only.
                pit_cutoff,
                result_path,
                run_id,
                source_catalog,
                items: [{ticker, driver_name, driver_state, direction,
                         exposure_role?, evidence}],
                propose_new_drivers: [...] }
  sidecar:    /tmp/dr_written_{source_id}_{run_id}.json
              (run_id suffix prevents concurrent-rerun collision; same
               source_id is stable across reruns per E14, but each run
               has a unique run_id)
  exit codes: 0=sentinel_fires (≥1 driver wrote, system OK),
              1=all_proposals_failed (no driver wrote; sentinel blocks),
              2=system_or_writer_failure (sentinel blocks)
              (See E1 exit-code semantics for full contract)
  guarantee:  atomic per item write; sidecar reports
              accepted_count, rejected_count, per-driver outcomes
  ```
  Required fields rationale:
  - `pit_cutoff` → required for L6 PIT contract; written to `DriverChange.pit_cutoff`
  - `result_path` → required because `DriverChange.result_path` is a property per `Neo4jXBRLDesign.md`
  - `run_id` → required for supersession tracking (`superseded_by_run_id` triplet per L6)
  - `source_catalog` → list/manifest of valid `SRC:*` IDs available to this emission; required so V10 can verify `evidence_refs` resolve against real sources (not hallucinated) — per E18 stricter V10. **PER-MODE SOURCING** (revised per E30 — learner is sole Phase-1 producer): learner → orchestrator extracts SRC IDs from bundle context's source references (8-K accessions, transcript IDs, news IDs cited in bundle); news (Phase 2) → `[news.id]`; fiscal.ai (Phase 3) → `[fiscal_kpi_row_id]`
  - Per-item `ticker` supports single-ticker producer (learner: all items same ticker per E30) and multi-ticker emissions (news: per-item ticker varies, aligned with `FOR_COMPANY` edge being per-company)
  - `exposure_role` per-item populated only for multi-ticker non-uniform-direction cases (news pipeline)
- Source: Bot2 #4 + ClaudeBot2 #3 + ClaudeBot2 Gap 2 + ChatGPTBot1 #5 + **ChatGPTBot2 #3** (source_catalog for V10 evidence validation)
- Why: Engineer copying `guidance_write_cli.py` would inherit guidance-specific assumptions (`fye_month`, `period_u_id`) that don't apply. Without `pit_cutoff` writer cannot implement L6; without `result_path` DC property is missing; without `run_id` supersession breaks; without `source_catalog` V10 cannot verify evidence_refs and falls back to syntactic-only check. Top-level ticker would force N writer calls per news event (ConceptReq §2.4); per-item ticker handles all modes uniformly.

**[E17] XBRL/member linking non-blocking**
- Location: `DriverOntology_Implementation.md` writer behavior
- Text: "Failed concept/member match does NOT reject a valid driver. `xbrl_qname` stays null for non-financial drivers (macro variables, news drivers, positioning drivers, themes, sentiment, etc.). `base_label` validation against `CANONICAL_BASE_LABELS` still applies for the financial-driver sliver."
- Source: Bot2 #8 + Bot3 #9
- Why: Most drivers have NO XBRL home. Blocking on resolver failure would reject most macro/news drivers.

**[E18] Evidence validation against source catalog**
- Location: `DriverOntology_Implementation.md` §E V10
- Text: V10 stricter — "`evidence[]` entries follow `SRC:*` format AND resolve against the current emission's source catalog (not just syntactic match)."
- Source: Bot3 #10
- Why: Syntactic-only check accepts hallucinated SRC IDs.

**[E19] Neo4j authoritative registry**
- Location: `DriverOntology_Implementation.md` §J or §A
- Text: "Neo4j is the authoritative registry. Any JSON snapshot in `/tmp` or config is derived cache only, never authoritative."
- Source: Bot3 #8
- Why: Locks the source-of-truth question.

**[E20] Lock "Phase 1 = zero extraction-LLM" commitment + per-mode routing clarified**
- Location: `Neo4jXBRLDesign.md` Locked section
- Text: "Phase 1 producer (learner only, per E30) emits drivers inside its own LLM session. NO second FULL extraction LLM pass and NO LLM canonicalizer. Canonicalization runs in Python, not in the LLM. (This ban is narrow: tiny, persisted, gated semantic judge calls at propose/unknown/borderline points — the isolated Pattern B judge — are ALLOWED and do NOT count as a second extraction pass.) **NEWS** (Phase 2) goes through the `/extract` worker pipeline. **FISCAL.AI** (Phase 3) is direct ingest via the same `driver_write_cli` pipeline as learner — NOT routed through `/extract` (per L2 Mode 3 + E13). Predictor is consumer-only (E30) — its `prediction/result.json` §7 `key_drivers[]` stays free-form analysis prose, never written to Driver registry."
- Source: ClaudeBot1 #5 + **ChatGPTBot2 #1** (fix L2 vs E20 contradiction — fiscal.ai is Mode 3 direct ingest, not /extract)
- Why: Without explicit lock, future rev could quietly flip to LLM-canonicalize → 5-7% accuracy loss. Original E20 wording wrongly grouped FISCAL.AI with /extract — that contradicts L2 Mode 3 (direct ingest) and E13 (fiscal.ai uses driver_write_cli). Corrected text resolves the internal contradiction.

**[E21] Final.md schema reconciliation**
- Location: `Neo4jXBRLDesign.md` "Final.md Changes Required" section
- Text (AMENDED by E30): "Confirm Final.md §8 `learner_result.v1 primary_driver / contributing_factors[i]` migrate from the current LIVE `{summary, category, evidence_refs}` shape (per `validate_learning.py` v3 — the live `category` free-form snake_case label, e.g. `guidance_change`, is the field that becomes the canonical `driver_name`; this is the real baseline, NOT the older `{driver/factor, evidence}`) to `{driver_name, driver_state, direction, evidence_refs}` PLUS an OPTIONAL per-tag `context_note` (<=2 sentences, free-form, event-specific 'why this driver applies HERE', e.g. "capex rising to support AI capacity, may pressure near-term FCF"). INVARIANT: `context_note` is stored on `:DriverChange` (per-mention) — NEVER on the global `:Driver`, NEVER an input to `canonicalize()` / identity / the global `definition`; explanatory metadata only (evidence/source_catalog stay authoritative). It is UNSCORED in the Pass-4 eval and may later feed audit / embeddings / reconciliation / human reports; the dedup-surface embedding stays on STABLE identity fields (name+definition+aliases), not per-event notes. **§7 `prediction_result.v1 key_drivers[i]` STAYS as `{driver, direction, evidence}` free-form (no canonical-form migration)** per E30 — predictor is consumer-only, does NOT emit canonical drivers. Spell out learner field-by-field migration so no version drift."
- Source: ClaudeBot2 #2
- Why: Schema host divergence guaranteed bugs without explicit migration spec.

### 5.5 Tier 5 — Polish (3 items)

**[E22] Phase 2 directory: KEEP SINGULAR** (REVERTED from earlier draft)
- Location: `Neo4jXBRLDesign.md` Phase 2 line 616
- Change: **NONE — keep `.claude/skills/extract/types/driver/` (singular)**. Earlier draft proposed plural `types/drivers/` claiming "match guidance convention", but guidance actually uses SINGULAR everywhere (`types/guidance/`, `TYPE=guidance`, `guidance_status`). Pluralizing would CREATE drift, not match it.
- Source: ClaudeBot1 #7 → **REVERTED per ChatGPTBot1 #1** (factual correction)
- Why: Drivers must follow guidance pattern verbatim: `types/driver/`, `TYPE=driver`, `driver_status` — all singular. Original E22 was a propagated misread; this entry now stands as a permanent record of the correction.

**[E23] R5 FULL rename: "Macro shortcut" → "Standalone shortcut" + `MACROS_VOCAB` → `SHORTCUTS_VOCAB`** (FULL CONCEPT RENAME, incl. tests)
- Location: `DriverOntology.md` R5 (title + body) + `DriverOntology_Implementation.md` §F.1 (bank name + all references) + test fixtures (Day 6-7)
- Change:
  - R5 title: "Macro shortcut" → "Standalone shortcut"
  - R5 body: replace "macros vocab" / "MACROS_VOCAB" references with "shortcuts vocab" / "SHORTCUTS_VOCAB"
  - Implementation §F.1: rename bank `MACROS_VOCAB` → `SHORTCUTS_VOCAB`; update all references throughout implementation file (§C canonicalize step 8, §D grammar, §F.1 contents, §H Conformance Index)
  - Tests (Day 6-7): test files import `SHORTCUTS_VOCAB` (not `MACROS_VOCAB`); any test fixture data referencing standalone-shortcut entries uses the new name
- Source: Bot1 #1 + ChatGPTBot1 #2 + **ChatGPTBot3 #7** (extend rename scope to test imports/fixtures)
- Why: R5 covers macro AND regulatory AND corporate-action AND event shortcuts (`fda_approval`, `share_buyback`, `opec_supply`). "Macro" is misleading. Half-rename (title only, body/bank still "MACROS_VOCAB") creates worse internal inconsistency than no rename. Full rename incl. tests keeps naming coherent end-to-end from spec through implementation through tests.

**[E24] Inline writer doesn't invent missing propose_new_drivers**
- Location: `DriverOntology_Implementation.md` §A.1 Mode 1
- Text: "The writer runs validation/resolution on emitted tags; it does NOT invent missing `propose_new_drivers` entries. If a tag references a `driver_name` not in registry AND not in `propose_new_drivers`, the tag is rejected (V11)."
- Source: Bot3 #3
- Why: Prevents writer from silently filling LLM gaps; preserves emission integrity.

### 5.6 My own addition (gap no audit caught)

**[E25] allowed_states mismatch on existing-driver reuse**
- Location: `DriverOntology_Implementation.md` §B6/B7 + §E (note)
- Text: "When a proposal's `driver_name` resolves to an existing Driver via canonicalize, the emission's `allowed_states` is IGNORED (registry wins). If the LLM intended a different state class for an existing driver, that is evidence the driver is mis-classified — log to drift audit; do not modify registry."
- Source: Self (no bot flagged it)
- Why: Spec currently silent → engineer would either modify registry on every emission (corruption) or hard-fail (false rejection).

### 5.7 Tier 6 — Self-Heal Levers folded from DriverImprovements v10 (4 items)

These 4 items absorb the locked content of `DriverImprovements.md` (v2 through v10) into CombinedPlan as the single source of truth. `DriverImprovements.md` remains as forensic audit-trail header but is no longer the operational spec. Each Tier-6 item below carries the full set of v* refinements (v2 through v10) that apply to it; downstream files (`DriverOntology_Implementation.md`, `Neo4jXBRLDesign.md`, `DriverProcess.html`) propagate from these Tier-6 entries.

**[E26] Writer-side auto-repair wrapper (Lever #1)**
- Location: `DriverOntology_Implementation.md` §A.1 / new §A.2 (writer behavior); audit row in §K
- Text: "A repair wrapper in `driver_writer.py` (NOT inside `driver_ids.canonicalize()` — L3 stays pure) is called when `canonicalize()` returns a structured rejection. Tries deterministic single-rule repairs (only if PROVABLY SAFE):
  - **`REJECTION_STATE_IN_NAME(t)`** — if `driver_state` is empty OR case-insensitively equals `t` (v6 Fix #9), strip `t` from name, set `driver_state = t`, re-run canonicalize. ON PASS: if repaired name EXACT-MATCHES an existing Driver (v2 Fix #4) AND repaired driver_state ∈ Driver.allowed_states (v4-5 V8 post-repair, per E25), write + log `:DriverAutoRepair{repair_kind:state_to_driver_state}`. If V8 fails → DEFER to Lever #3 retry. If no exact match → DEFER to Lever #3 retry. If conflict (driver_state already set differently) → final reject. Trend-partner preference (v3-3 + v4-16): when stripping a `trend_motion` verb (declined/accelerated/etc.), check registry for `{metric}_trend` partner first; prefer the trend Driver (state_to_trend_partner). Only `_trend` suffix recognized per current ontology.
  - **`REJECTION_BANNED_TOKEN(t)`** where t is period (q3/fy26/2025/h1): strip → re-canonicalize → exact-match-or-retry. Where t is magnitude (v3-2 NARROWED): match `/^\\d+(pct|bps|x|percent|basis_points)$/` ONLY — do NOT strip bare `/^\\d/` (would incorrectly remove 5g, 10yr, 3nm tokens). Where t is identity (ticker/company/person): final reject.
  - **`REJECTION_NO_METRIC_TOKEN` / `REJECTION_TOO_MANY_SLOTS`**: no safe repair → reject.
  Audit row `:DriverAutoRepair{source_id, run_id, item_index, original_name, repaired_name, stripped_token, repair_kind, cascade_outcome, evidence_refs, repaired_at}` with UNIQUE on `(source_id, item_index)` per v4-14 + v5-2 (v9-4: item_index is a declared property, not just key)."
- Source: `DriverImprovements.md` v2 through v10 — full Lever #1 fold
- Why: State-smuggle / magnitude-smuggle / period-token-smuggle is the #1 LLM mistake class (~5pp loss). Deterministic repair recovers them without weakening L3 (canonicalize stays pure). Exact-match-only commit + V8 post-repair check prevents writer from inventing under-spec'd drivers. Expected recovery: ~3-4pp (part of cumulative ~10pp total across 3 levers). **DEMOTED/DEFERRED (do NOT delete):** the PRIMARY recovery path is now Pattern A = the producer (learner) self-corrects WITHIN ITS OWN session: after drafting driver tags it calls a deterministic validate tool (`driver_write_cli.py --dry-run` = canonicalize + validators), reads the exact per-tag rejection reasons, fixes ONLY the flagged tags, and re-validates — looping AT MOST 2-3 times, stopping if a rejection repeats (no progress), never contorting a name just to pass (drop+note instead). The orchestrator's write-path validation is the NON-NEGOTIABLE external authority/gate: it re-validates before MERGE, handles partial-failure audit/drop, and the learner cannot bypass it; the internal loop is a convenience, not the authority. Cost $0 (extra in-session turns on interactive OAuth; SDK / `claude -p` stay forbidden/metered). An optional single orchestrator-level fallback retry is DEFERRED (build only if post-launch audit shows many gate-failures worth recovering — same metrics-gated posture as this demoted deterministic auto-repair). Revive this deterministic auto-repair only if post-launch metrics show many mechanically-recoverable rejects, and then only for unambiguous strips.

**[E27] Unified `:EquivalenceToken` store with N=2 promotion gate (Lever #2)**
- Location: `Neo4jXBRLDesign.md` new schema section; `DriverOntology_Implementation.md` §F.10 NEW + §C bootstrap loader
- Text: "Single `:EquivalenceToken{equivalence_id UNIQUE, kind ∈ {synonym, plural, acronym}, from_token, to_token, observation_keys[], observation_pit_cutoffs[], provenance_source_driver_ids[], first_seen_at, last_seen_at, evidence_refs, status, promoted_at, equivalence_visible_at}` Neo4j label (per v5-5: kind:shortcut dropped — shortcuts go to direct `:Driver` registration per Pattern B). Promotion to `status="promoted"` requires `size(observation_keys) >= EQUIV_PROMOTE_N` where N=2 is a HARDCODED Python constant per v3-14 + L4 — KEEP the N=2 gate as the irreversibility/stability guard. **A context-free token-synonym equivalence promotion (word=word, e.g. uptake→demand) is a Pattern B judge call (verdict cached/persisted, replay-by-code) gated ON TOP OF N=2; it is DISTINCT from driver-level reuse — a context-specific reuse (e.g. `iphone_demand` reusing `iphone_china_sales`) is a driver-level ATTACH and MUST NOT promote a global token synonym (`demand→sales` would wrongly merge `labor_demand`/`labor_sales`). Multiple CANDIDATE to_tokens may EXIST (evidence-gated); only ONE may PROMOTE per (kind, from_token); a conflict FREEZES promotion until one isolated judge call resolves it → persist exactly one of {to_A, to_B, no-global-rule (→ driver-level reuse only)}; N=2 gate first, judge confirms meaning once, code persists + replays. (builder: this changes synonym_fold.py conflict handling from block → judge-escalate; aligned at integration.)** Code retains all mechanical promotion + collision + PIT-backdate steps.

  **Acceptance rule (v4-3 + v4-4 + v6-5 + v9-3 cleanup)**:
  - (a) one-token same-slot substitution
  - (b) from-form appears in evidence text (anti-hallucination)
  - (c) no collision with existing Driver name/alias at acceptance time
  - (d) proposing Driver passes R11 + V1-V15 (V1 STAYS STRICT per E6 + v4-4). Per v6-5 STRICT-vs-NON-STRICT alias routing: STRICT aliases (where `canonicalize(alias, current_vocab) == parent.name` — word-order variants or already-promoted equivalence folds) land in `Driver.aliases[]`. NON-STRICT aliases (V1 would fail) route to `:EquivalenceToken` as candidates; per v5-6 NO post-promotion alias-sync (promoted equivalences fold via canonicalize step 5 → B6 hits registry directly)
  - (e) `kind=shortcut` path (v5-5 + v7-2): `is_shortcut=true` proposals bypass slot grammar; MUST have zero slot-classifying tokens; MUST have ≥2 underscore-separated tokens (v7-2 mechanical gate, rejects single-word LLM hallucinations like `winter`/`crash`); R11 evidence required. **Because a new shortcut bypasses slot grammar, registering a NON-seeded shortcut requires a MANDATORY isolated Pattern B judge verdict (cheap model, temp 0, structured output, verdict cached/persisted — decide-once, replay-by-code) before it lands; seeded shortcuts stay code.** The mechanical gates above (≥2 tokens, zero slot tokens, R11) STAY code and run first. Lands as `:Driver{name, is_shortcut:true}` directly (v8-1 schema field). NO parallel :EquivalenceToken record (v5-5).

  **`equivalence_id` PROMOTION invariant + conflict rule (v5-1)**: multiple CANDIDATE `to_token`s MAY coexist per `(kind, from_token)` (each evidence-gated, arrival-order independent — NOT first-wins). Only ONE may be PROMOTED per `(kind, from_token)` — that invariant is PRESERVED. A conflicting proposal (different to_token, same key) does NOT auto-reject; instead it FREEZES promotion for that `(kind, from_token)` and escalates: once ≥2 evidence-backed candidates have each cleared the N=2 gate, make ONE isolated Pattern B judge call (cheap model, temp 0, structured output, verdict cached/persisted — decide-once, replay-by-code) that persists exactly one of `{to_token_A, to_token_B, NO-GLOBAL-RULE, DEFER}`. Each `(kind, from_token, to_token)` candidate carries its OWN `observation_keys`/count (N=2 applies PER candidate, so a later "loser" can still reach N=2; the `(kind, from_token)` uniqueness is the PROMOTED invariant). N=2 is the ELIGIBILITY gate — the judge may only approve a candidate that has cleared N=2 (never a one-off merely because it "sounds better"); DEFER = stay frozen, re-judge when more evidence. NO-GLOBAL-RULE = the token is context-dependent (e.g. `demand`) → no global synonym lands; the reuse is handled via driver-level reuse only (driver-level ATTACH). Code persists the single verdict and replays it deterministically forever. `:EquivalenceConflictAudit{equivalence_id, existing_to, proposed_to, source_id, item_index, froze_at, judge_verdict?}` now records the FREEZE + judge-escalation (NOT a silent reject). POST-PROMOTION: a later stray conflicting observation does NOT auto-demote an already-promoted rule — it is audit-only; re-judge only if that stray candidate independently clears its own N=2 gate. Python pre-MERGE check + intra-MERGE WHERE guard (v9-2) preserve the two-phase race mechanics (sequential + concurrent) — they now route a conflict to FREEZE+judge-escalate instead of REJECT. (builder: this changes synonym_fold.py conflict handling from block → judge-escalate; aligned at integration.)

  **Judge-unavailable degradation (fail-safe)**: if the isolated Pattern B judge is DISABLED or UNREACHABLE, the system FAILS SAFE and NEVER hard-blocks the run or the driver writes — local `canonicalize()` + per-tag validation are independent of the judge and proceed under the PARTIAL policy. Only the gated global/irreversible decisions wait: a pending non-seeded-shortcut registration (rule (e) above) is REJECTED (reject-don't-guess; audited; re-tryable on a later run once the judge is back), and a frozen `(kind, from_token)` synonym conflict STAYS DEFERRED (audited debt via `:EquivalenceConflictAudit`, re-judged when the judge returns). Never guess a global rule; never block production on a judge outage.

  **Observation counting (v4-2 event-level dedup)**: `observation_keys[]` is APPEND-ONLY-IF-NOT-PRESENT keyed by event-level identifier (strip producer prefix: `learner:AAPL:Q2_FY2026` → `AAPL:Q2_FY2026`). Predictor+learner emitting same equivalence on same event = ONE observation. Defensive for Phase 2/3 multi-producer; effective no-op in Phase 1 (learner-only per E30).

  **PIT visibility (v4-7 + v10-2)**: `equivalence_visible_at = sort(observation_pit_cutoffs)[N-1]` set at promotion. ON each subsequent observation, BACKDATE via Phase 1 SET clause: `CASE WHEN et.status='promoted' AND sort(new_pit_cutoffs)[N-1] < et.equivalence_visible_at THEN sort(new_pit_cutoffs)[N-1] ELSE et.equivalence_visible_at END` — mirrors `Driver.registry_visible_at` MIN-backdate L6 pattern. `promoted_at` is wall-clock audit only, NEVER used for PIT (per v5-12).

  **Promotion Cypher (v5-4 compute-before-SET + v6-2 two-phase)**: split into TWO Cypher queries with Python in between — Cypher cannot be interrupted midstream by Python. Phase 1: MERGE + WITH (compute new arrays) + intra-MERGE `WITH et WHERE et.to_token = $to` guard (v9-2 concurrent-writer race protection) + SET observation arrays + visible_at backdate CASE (v10-2) + RETURN `would_promote`. Phase 2 (Python): if Phase 1 returned zero rows → conflict path = FREEZE promotion for that `(kind, from_token)` and write `:EquivalenceConflictAudit` recording the FREEZE + judge-escalation (NOT a silent reject); once ≥2 candidates have each cleared the N=2 gate, ONE isolated Pattern B judge call resolves the FREEZE by persisting exactly one of `{to_token_A, to_token_B, NO-GLOBAL-RULE (→ driver-level reuse only)}`, after which code replays the verdict deterministically. If `would_promote=true`: collision recheck against current Driver registry (v4-6) — registry may have changed between candidate creation and promotion. Phase 3 (conditional Cypher): SET status='promoted' + promoted_at + equivalence_visible_at via `WHERE et.status = 'candidate'` guard (concurrent-writers race-safe: exactly ONE Phase 3 status transition succeeds even if multiple Phase 1's returned would_promote=true per v10-3 wording precision).

  **Hide candidates from LLM (v2 Fix #2)**: bundle renderer + read-path query filter `WHERE et.status = 'promoted'` only. Candidates live in audit layer until promoted; never enter LLM-visible vocab block.

  **Backward-compat (v3-7 + v5-7)**: pre-promotion legacy split Drivers (cloud_topline + cloud_revenue both existing before topline→revenue promoted) stay AS-IS. `Driver.name` is IMMUTABLE. A reconciliation job is MANDATORY for production-trust (may be STAGED after the harness): when a late-learned equivalence or judge ruling finds two ALREADY-REGISTERED Drivers are the same, it merges Drivers + relinks DriverChanges + records supersession; judge-confirmed only; audited with provenance; reversible (un-merge); PIT-honest (carries an effective date so historical/PIT queries still see what was true then). Until it ships, late duplicates are AUDITED debt (`:DriverDriftAudit`), never silent. `Driver.name` stays IMMUTABLE; pre-promotion legacy split Drivers stay AS-IS until the reconciliation job processes them."
- Source: `DriverImprovements.md` Lever #2 (v2 through v10) — full fold including v9-1+v10-1 (VocabToken PIT-filter + MIN-backdate per E10 amendment above), v9-2 (intra-MERGE to_token guard), v10-2 (equivalence_visible_at MIN-backdate)
- Why: Synonym/plural/acronym splits are ~5pp loss; markdown-only growth has no runtime path. N=2 promotion gate + collision rechecks + PIT MIN-backdate close the splits without weakening L4 (no runtime curator). The unified store with kind discriminator avoids 3-label code duplication. Expected recovery: ~5-7pp combined. Post-E27, the only code-time-editable banks in the entire design are STATES_VOCAB (7 stable classes) and BANNED_CONTENT (bounded English vocab); true "no human in loop" reaches its design limit.

**[INGESTION-DESIGN] Layered admission + correction loop (open-world, ~100/100 target)** — INTEGRATION/INGESTION-PHASE (NOT a Phase-1-harness build item; surfaced by Pass-3's V4-segment + unregistered-shortcut findings; locked 2026-05-30). NOT a new spec-lock E* — consolidates E27 + the reconciliation job + the `new_name_judge` admission seam for the ingestion build.
- GOAL: ~max recall AND ~max precision on THOUSANDS of unknown future drivers. No single front gate reaches it — the last mile is audit + reversibility. Four layers, matched to tool strength:
  1. **Code rules (precision, free):** shape / banned-token / evidence-grounded (R11) gates; PIT-frozen parse (`parsed_slots_at_create`, `segment_at_create`, vocab version). Vocab learning is **PIT-MONOTONIC** — it may only ADD resolution paths (aliases), NEVER rename / reject / re-interpret an accepted Driver. On a token/atom learn, re-canonicalize existing names and ADD any divergent form as an alias (deterministic — closes the V4/segment-drift fragmentation Pass-3 surfaced).
  2. **Dedup surface (precision):** deterministic canonical-key / sorted-token / alias match FIRST; an embedding near-dup index **SURFACES** semantic duplicates code cannot (`chip_shortage` ≈ `component_supply_constraint`, zero lexical overlap) — **surface-only, NEVER auto-merge.** (Embedding infra ALREADY EXISTS — reuse, don't reinvent; need only a `Driver` vector index. PIT-filter the search. See `INGESTION_embedding_dedup.md`.)
  3. **Cached judge (recall on the residual):** mechanical gates → **recurrence gate (>=2 DISTINCT events)** → `new_name_judge` (admit) / merge-judge (dedup confirm). Positive admits are EXPENSIVE + DOUBLE-CONFIRMED (the promote-confirmation pattern, E27); verdict persisted + audited (decide-once, replay-by-code); judge down → DEFER (never guess). A lone-atom shortcut (Pass-3 finding #2) is admitted ONLY through this seam, never via slot-grammar.
  4. **Correction loop (the last mile):** a wrong merge is **UN-mergeable**; `defer` AND `reject` are BOTH **REVISITABLE** on new evidence (never a permanent rejection — same lesson as the E27 incumbent re-open); the mandatory **reconciliation job** periodically revisits accumulated evidence to catch + fix residual cached-judge errors.
- INVARIANT: prefer **DEFER over REJECT**, **ALIAS over RENAME**, **decide-once-replay-by-code**, **fail-safe-defer**. ~100/100 is an ASYMPTOTE reached by audit + reversibility, NOT a perfect front gate.
- WHY (rejected alternatives): allowlist-only shortcuts CAP recall on unknowns AND re-introduce the banned human curator; slot-grammar / deterministic keys alone CANNOT catch no-lexical-overlap semantic dups. So: code for mechanical precision + dedup, recurrence for cheap recall, a THIN cached LLM for the open-world semantic residual, and a reversible correction loop for the errors any LLM-in-loop will make.

**[E28] Driver-only informed retry (Lever #3)**

> **MECHANISM UPDATED 2026-05-29 — Pattern A is now LEARNER-SELF-CORRECT (producer calls the validate tool and fixes flagged tags, <=3 tries, orchestrator write-gate authoritative), NOT orchestrator-driven re-injection. The re-injection / prior-rejection-block / 3-stage-merge details below are SUPERSEDED; retained for reference pending the integration rewrite (SKILL.md + driver_write_cli.py).**

- Location: `DriverOntology_Implementation.md` new §J writer contract + retry
- Text: "Mirror H2 informed-retry pattern at `orch.py:1347-1387` for `driver_write` failures. Within-session re-emission of the SAME learner LLM (per E20 + E30: not a second extraction pass — same producer, same bundle, same source_id, same TMUX transport per Final.md §5 Fix #5). Function name `run_driver_write()` is transport-neutral (drops `_via_sdk` suffix per Fix #5; SDK paths are forbidden per Final.md §5).

  **Flow**: predictor/learner writes result.json → orchestrator validates + `driver_write_cli --dry-run` → if FAIL with per-driver rejection_reasons: build prior-rejection block (per orch.py:3118-3165 verbatim format) → ONE retry via TMUX → `--dry-run` AGAIN → PASS = write all + outcome `SUCCEEDED_AFTER_RETRY` for fixed tags; STILL FAIL = per-driver final reject → `:DriverProposalRejection` audit + run continues per E1 PARTIAL policy.

  **Outcome enum** mirrors `LearnerOutcome` (orch.py:1066-1106): `SUCCEEDED`, `SUCCEEDED_AFTER_RETRY`, `FAILED_VALIDATION_RETRY`, `FAILED_DRIFT_GUARD` (v3-9 + v4-8), `FAILED_SCOPE_CREEP` (v3-8), `FAILED_RETRY_SHAPE_VIOLATION` (v4-9), `FAILED_SYSTEM`.

  **Merge logic 3-stage (v3-8 + v3-9 + v4-8 + v4-9 + v4-15 + v5-9 + v5-11 + v6-1)**:
  - **STAGE 1 — DRIFT GUARD (v4-8 inversion-whitelist)**: `DRIVER_FIELDS` is producer-specific per v7-1 dispatch (learner Phase 1 = `{primary_driver, contributing_factors, propose_new_drivers}`; Phase 2 news = `{items, propose_new_drivers}`; v10-6: `key_drivers` REMOVED from DRIVER_FIELDS — that's predictor's free-form field per E30). `ORCHESTRATOR_STAMPED` = explicit Python-owned echo fields (schema_version, ticker, predicted_at, attributed_at, model_version, sdk_session_id, pit_*, confidence_bucket, magnitude_bucket — derived from LLM-authored confidence_score/expected_move_range_pct per Final.md §7, etc.). Diff R1 vs R2 across `(all_fields − DRIVER_FIELDS − ORCHESTRATOR_STAMPED)` only — any drift = FAILED_DRIFT_GUARD; R1 rejected drivers stay rejected; field-diff logged to `:DriverDriftAudit`. Future-proof: new LLM-authored fields default-include in guard.
  - **STAGE 2 — SURGICAL REPLACE (v3-8 + v4-9 + v5-9 tuple equality + v10-6 contributing_factors-aware)**: array length + order preserved (`R2.contributing_factors.length == R1.contributing_factors.length`). PASSED-in-R1 indices: R2 tuple `(driver_name, driver_state, direction, evidence)` MUST be IDENTICAL to R1 (else FAILED_RETRY_SHAPE_VIOLATION). FAILED-in-R1 indices: REPLACE with R2 at same index. v4-15: drop ORPHANED R1 proposals (R1 entries no longer referenced by any merged tag).
  - **STAGE 3 — PROPOSE_NEW_DRIVERS gate (v5-11 same-name replacement)**: CASE A — R2 entry has same `name` as a R1 entry that FAILED V1-V15: ACCEPT as corrected version (re-run R11 + V1-V15). CASE B — NEW name referenced by STAGE-2-replaced tag whose R1 rejection was `unresolved_driver_name`: ACCEPT (V11 carve-out). CASE C — NEW name with no carve-out: REJECT as FAILED_SCOPE_CREEP.
  - **FINAL merge formula (v6-1 corrected)**: `final.propose_new_drivers = (R1 − replaced − orphaned) + STAGE-3-CASE-A-replacements + STAGE-3-CASE-B-additions`.

  **One retry only**: learner pattern production-validated. More = drift + diminishing returns."
- Source: `DriverImprovements.md` Lever #3 (v2 through v10)
- Why: V8/V10/V11/R11 tail failures need a recovery path that doesn't bypass canonicalize discipline. Mirroring the proven learner H2 pattern at orch.py:1347 keeps implementation surface minimal. 3-stage merge with explicit producer-field dispatch + drift guard + scope-creep block enforces "change ONLY driver fields" structurally — belt + suspenders + structural lockout. Expected recovery: ~3-4pp.

**[E29] Audit telemetry tables**
- Location: `Neo4jXBRLDesign.md` new schema sections; `DriverOntology_Implementation.md` new §K + constraints
- Text: "Five audit/telemetry labels for observability:
  - `:DriverAutoRepair{source_id, run_id, item_index, original_name, repaired_name, stripped_token, repair_kind, cascade_outcome, evidence_refs, repaired_at}` — every deterministic repair (Lever #1). UNIQUE on `(source_id, item_index)` per v4-14 + v5-2 + v9-4 (item_index is declared schema property).
  - `:DriverProposalRejection{source_id, run_id, proposed_name, rejection_reason, evidence_refs, rejected_at}` — every final rejection (Lever #3 + E1 PARTIAL policy). MERGE on `(source_id, run_id, proposed_name)`.
  - `:EquivalenceConflictAudit{equivalence_id, existing_to, proposed_to, source_id, item_index, froze_at, judge_verdict?}` — records a to_token conflict that FREEZES promotion + escalates to one isolated judge call (v5-1 conflict rule; Python pre-MERGE OR v9-2 intra-MERGE race-guard detects it). NOT a silent reject; the FREEZE/judge-escalation is the recorded event.
  - `:EquivalenceCollisionAudit{equivalence_id, conflict_driver_id, rejected_at}` — promotion-time Driver-registry collision (v4-6 recheck — registry may have changed between candidate creation and promotion).
  - `:DriverDriftAudit{dc_id, ticker, old_direction, new_direction, revision_ts, reason?}` — direction flips on FOR_COMPANY edges across re-runs (preserved audit trail without per-revision immutable DC nodes).

  **Scope (v2 Fix #6 clarification)**: PURE TELEMETRY for observability. Self-heal does NOT require any seed edits — Neo4j EquivalenceToken + VocabToken stores cover runtime growth. Engineers MAY OPTIONALLY use audit data for code-time cleanup (deprecating bad VocabToken entries via Cypher migration, reviewing aberrant promotion counts). Without these tables, the system still self-heals correctly; we just lose observability into HOW it's healing."
- Source: `DriverImprovements.md` §4.2 + v9-4 schema declaration + Lever #2 + Lever #3 audit paths
- Why: Without telemetry, the operator has no signal on auto-repair hit rate, rejection patterns, promotion velocity, registry split detection, or direction-drift incidence. Required for Q1+ "measure then iterate" learning loop. Audit tables are NOT a feedback input to markdown seed; the runtime loop is closed without code-time intervention.

### 5.7.1 v9 + v10 fold-specific consistency reminders (per v10-5 process note)

When implementing E26-E29, the engineer MUST verify the following v9 + v10 fixes appear in the implementation (because they were applied as patches to DriverImprovements after the original Lever drafts):

- **v9-1 + v10-1 VocabToken vocab_visible_at + MIN-on-MATCH backdate** → see amended E10 above + E27 read path
- **v9-2 intra-MERGE WITH et WHERE et.to_token = $to guard** → E27 Phase 1 Cypher
- **v9-3 acceptance rule (a) drops "or whole-name shortcut"** → E27 acceptance rules wording
- **v9-4 :DriverAutoRepair item_index declared property** → E29 schema
- **v10-2 equivalence_visible_at MIN-backdate on each obs** → E27 Phase 1 SET CASE expression
- **v10-3 concurrency invariant**: "exactly ONE Phase 3 status transition succeeds" (NOT "exactly ONE Phase 1 returns true")
- **v10-4 ≥2-token gate negative test** → E27 acceptance rule (e).3 + Day 6-7 adversarial tests
- **v10-6 `key_drivers` → `contributing_factors`** for all learner-retry examples (E28 STAGE 2 + STAGE 3)

The historical X3 deferral premise ("Phase 1 chronological backfills") was WRONG (E30 doesn't lock backfill order); v10-1 + v10-2 close the L6 inconsistency by mirroring `Driver.registry_visible_at` MIN-backdate pattern across all three stores symmetrically. Implementer must NOT re-introduce a "no-backdate" simplification.

---

## §6. Open User Decisions (4 questions; must answer to lock spec)

| # | Question | Recommendation | Rationale |
|---|---|---|---|
| **OQ1** | `validation_status`: drop entirely OR keep with mechanical-only promotion (`validated` after ≥3 DCs across ≥2 source_types)? | **DROP** | L4 ("no human curator ever"); simplest path; removes 5 references; promotion threshold can be added later if empirical signal warrants. |
| **OQ2** | ~~Predictor source-visibility~~ — **RESOLVED MOOT by E30** (predictor is consumer-only, doesn't emit drivers, so no driver-emission source-visibility gap exists). Question dropped from open-decisions list. | n/a | n/a |
| **OQ3** | R5 "Macro shortcut" → "Standalone shortcut" — accept full rename (DriverOntology.md R5 title+body + Implementation §F.1 `MACROS_VOCAB` → `SHORTCUTS_VOCAB` + cross-references in §C/§D/§H + tests-import update)? | **ACCEPT** | Current name is genuinely misleading. Round 2 extended scope from title-only to full rename for consistency. Half-rename (title only) creates worse internal inconsistency than no rename. |
| **OQ4** | Cold-start seed source: (a) hardcoded constant `COLD_START_SEED_DRIVERS = [...]` in `driver_writer.py`; (b) LLM bootstrap call on first run; (c) migrated from existing guidance metric labels; (d) manually curated (violates L4)? | **(a) HARDCODED CONSTANT** (optionally informed by (c) for financial drivers) | L4 forbids RUNTIME human curator; code-time constant is normal engineering, deterministic, inspectable, no runtime LLM dependency. Existing guidance metric labels can seed the financial sliver. |

---

## §7. Rejected Suggestions (with reasons)

| Source | Suggestion | Reason for rejection |
|---|---|---|
| ClaudeBot2 #4 | Bidirectional Conformance Index | Reverse direction (enforcement → rule) creates many-to-one explosion + false drift signals. One-way index (rule → enforcement) already in `DriverOntology_Implementation.md`. |
| Various | "Just trust the smart LLM" for canonicalize | Violates L3. LLM judgment caps at ~85%. |
| Bot3 #4 (partial) | Fiscal.ai keep "direct + optional later" | Accepted in spirit (E13 + L2); reject the "optional" framing — direct ingest MUST consult registry per ConceptReq §6, optional is not an option. |
| (Implied by anti-bloat preference) | Add slot vocabs inline in ontology | Would bloat ontology + slot vocabs grow over time. Implementation file owns vocab seeds; bundle renderer injects current state. |

---

## §8. Per-File Change Manifest

```
DriverOntology.md
  Total change:  ~5 lines (R5 title + body rename; 'macros vocab'
                  references replaced; unified SHORTCUTS_VOCAB naming
                  across ontology and implementation)
  Items:         E23 (extended in Round 2 from title-only to full rename)

DriverOntology_Implementation.md
  Total change:  ~60 lines (new §A.1 additions, §J, fixes to §A/§D/§E/§F.5,
                  plus Round 5–7 extensions: E1 exit codes, E8 full
                  STATES_VOCAB enum, E9 two-tier seed, E10 Neo4j vocab
                  store, E16 source_catalog + sidecar per-mode detail)
  Items:         E1, E4, E5, E6, E7, E8, E9, E10, E11, E15, E16, E17, E18,
                 E19, E24, E25
  Major sections:
    • §A bullet 1 reworded (E4)
    • §A.1 NEW additions (E1, E5, E24, plus Mode 2 wording)
    • §D shape regex tightened (E7)
    • §E V1 fixed + V10 hardened (E6, E18)
    • §F.5 standardized (E8)
    • §J NEW Mirror Map fixes + Shared Writer Contract + Cold-start
      seed clause (E9, E15, E16)
    • Writer behavior notes: XBRL non-blocking (E17), Neo4j
      authoritative (E19), slot-mapping persistence (E10),
      concurrency (E11), allowed_states-mismatch note (E25)

Neo4jXBRLDesign.md
  Total change:  ~20 lines added/changed (incl. Round 6 P1 stale §24
                  pointer fix)
  Items:         E2, E3, E11, E13, E14, E20, E21, E22, E27, E29
                 (E12 RESOLVED MOOT per E30 — no Neo4jXBRL edit; forensic
                  entry kept at §5 Tier 3 above. E27 + E29 added per
                  Tier 6 fold of DriverImprovements Lever #2 + audit tables.)
  Major sections:
    • Purge human/curator language throughout (E3)
    • Open Items #3 RESOLVED (E2)
    • Schema: UNIQUE constraint on Driver.id (E11)
    • (Phase 1 predictor source-visibility note REMOVED — E12 RESOLVED MOOT per E30: predictor is consumer-only, no driver-emission source-visibility gap exists)
    • NEW :EquivalenceToken + :VocabToken (vocab_visible_at) + audit
      labels per E27 + E29 Tier-6 fold (Neo4j schemas + constraints +
      Driver.is_shortcut field per v8-1)
    • Phase 2: directory KEPT singular `types/driver/` (E22 REVERTED in
      Round 2; matches guidance convention `types/guidance/`)
    • Phase 3: fiscal.ai consults registry (E13)
    • DriverChange schema notes: direction + evidence_refs/source_id (E14)
    • "Final.md Changes Required" section: schema reconciliation (E21)
    • Locked section: Phase-1-zero-extraction-LLM (E20)
    • Stale §24 Final.md pointer at line 809-811: replace
      "DriversListNeo4jXBRL_design.md" with "Neo4jXBRLDesign.md"
      (this file) — leftover from an earlier filename draft (P1)

Final.md
  Total change:  noted in Neo4jXBRLDesign.md E21; actual edits when code lands
```

**Grand total** (pre-Tier-6 fold, 3 spec files): ~85 lines of doc additions. Post-Tier-6 fold (with E26-E29 self-heal levers, E30 producer-scope clarifier, and v9/v10 PIT patches added to `DriverImprovements.md` + propagated): ~135 lines TOTAL across the 4 spec files — see the §10 detail block below for the per-file breakdown.

> **Note**: per-file LOC are ROUGH estimates that drifted post-Tier-6 fold; the ~135-line TOTAL is the current indicative figure; treat per-file splits as indicative, not reconciled.

---

## §9. ConceptualRequirements.md Coverage Matrix (post-edits)

| ConceptReq § | Requirement | Covered by | Status |
|---|---|---|---|
| §1 | Same driver tagged to many events | DriverChange node design + slot ID | ✅ |
| §1 | One event with many drivers | Multiple DriverChange entries per source | ✅ |
| §1.5 | Driver = anything that moved price; not promoted without evidence | R11 evidence requirement + E18 source-catalog validation | ✅ |
| §2.x | News drivers exclude same-day company filings | Phase 2 deferred (acceptable per L2) | ⏸ DEFERRED |
| §2.2 | News tradeable/triggerable | Phase 2 deferred (acceptable) | ⏸ DEFERRED |
| §3.3 | ~~Predictor must produce drivers from 8-K + transcript (+ optional 10-K/Q)~~ — **CLARIFIED by E30**: predictor is consumer-only, NOT a producer. ConceptReq §3.3 has been rewritten to align with §3.2 (learner produces, predictor consumes). The original "predictor must produce" wording was a §3.2 vs §3.3 contradiction resolved during plan v4 review | E30 + ConceptReq §3.3 rewrite | ✅ RESOLVED (not deferred — re-scoped to consumer) |
| §3.4 | Learner produces from 8-K + transcript | Learner has DataSubAgent access; covered by L2 Mode 1 | ✅ |
| §4 | Fiscal.ai different conventions OK | §1 ontology exemption + Phase 3 + E13 (consults registry) | ✅ |
| §5.5 | Macro/sector/company category — deferred | No category field in schema (correct rejection) | ✅ |
| §6 | Global standardized list consulted by all producers | E13 + L2 + L5 | ✅ |
| §7 | Focus on learner + predictor first | Phase 1 = Mode 1 | ✅ |
| §8 | Specific vs generic tension | R3 grammar + R9 granularity | ✅ |

**Conceptual coverage (updated post-E30 / v6-6)**: **10/12 fully covered + 2/12 deferred** with explicit rationale (acceptable per Condition 2). Math: 10 ✅ + 2 ⏸ DEFERRED = 12. (§3.3 flipped from DEFERRED to RESOLVED per E30 — predictor is consumer-only, no driver-emission obligation exists; the "predictor must produce drivers from 8-K+transcript" wording was a §3.2 vs §3.3 contradiction resolved during plan v4 review.)

> ✅ **FILE-DEPENDENCY NOTE (resolved post-v5)**: `.claude/plans/Drivers/ConceptualRequirements.md` is **PRESENT and ALIGNED** with this matrix. §3.3 was updated (per E30 + the "predictor is consumer-only" clarification) to resolve the §3.2 vs §3.3 contradiction in favor of §3.2. The Round-7 "missing file" warning was stale by the time the v5 audit was run (file was restored / authored before E30 work). Matrix above is verified against the current ConceptReq source.

---

## §10. Honest Engineering Effort

> **SUPERSEDED 2026-05-29** — Pattern A is now LEARNER-SELF-CORRECT (learner calls `driver_write_cli.py --dry-run`, fixes flagged tags <=3, orchestrator write-gate authoritative). The `run_driver_write()`/`_merge_retry_response()`/3-stage-merge/one-retry-cap items below are SUPERSEDED; the self-correct build+test items will be re-specified at integration (SKILL.md + driver_write_cli.py). Do NOT build the orchestrator-reinjection retry.

```
Documentation additions (this plan, post Tier-6 fold of DriverImprovements v10):
                                                ~85 doc lines (original)
                                                + ~30 lines E26-E29 entries (§5.7)
                                                + amendment to E10 (~15 lines)
                                                + §13 risk register additions (~5 lines)
                                                ~135 lines TOTAL
Implementation work (after spec locks):
  driver_ids.py (mirror guidance_ids.py +
                 + canonicalize(candidate, vocab) signature per v3-1
                 + classify_token() pure function)              ~500 LOC
  driver_writer.py (mirror guidance_writer.py +
                    + Lever #1 repair_and_retry() per E26
                    + Lever #2 write_equivalence_tokens() per E27
                      [INTEGRATION-phase (DEFERRED — the harness uses an
                       in-memory model per §8 OUT-OF-SCOPE; NOT a
                       Phase-1-harness build item)]
                    + write_vocab_token() w/ vocab_visible_at MIN
                      on MATCH per E10 amended + v9-1 + v10-1
                      [INTEGRATION-phase (DEFERRED — the harness uses an
                       in-memory model per §8 OUT-OF-SCOPE; NOT a
                       Phase-1-harness build item)]
                    + two-phase promotion Cypher per v5-4 + v6-2
                    + supersession handlers)                     ~430 LOC
                                                                 (+~80 over baseline
                                                                  for Lever #1+#2
                                                                  per DriverImprovements
                                                                  §10)
  driver_write_cli.py                            ~400 LOC
  driver_concept_resolver.py (financial sliver)  ~150 LOC
  driver_write.sh                                 ~20 LOC
  registry+vocab bundle renderer                  ~80 LOC
  Neo4j schema + constraints                      ~50 lines Cypher
                                                  (+~20 over baseline for
                                                   EquivalenceToken + audit labels
                                                   + Driver.is_shortcut + vocab_visible_at
                                                   + UNIQUE constraints per E29)
                                                  [the EquivalenceToken store + E29
                                                   audit constraints are INTEGRATION-phase
                                                   (DEFERRED — the harness uses an in-memory
                                                   model per §8 OUT-OF-SCOPE; NOT a
                                                   Phase-1-harness build item)]
  Learner SKILL.md emission updates                ~75 LOC
    (earnings-learner/SKILL.md only per E30 / v6-6: emission contract
     + bundle-reading instructions + propose_new_drivers entry format
     including is_shortcut + worked examples. earnings-prediction/
     SKILL.md needs NO edits — predictor is consumer-only.)
  Cold-start seed Python constant                 ~30 entries
    (COLD_START_SEED_DRIVERS in driver_writer.py per OQ4)
  orchestrator.run_driver_write() w/ informed retry  ~65 LOC
    (Lever #3 / E28 — mirror H2 informed-retry at orch.py:1347-1387;
     producer-specific DRIVER_FIELDS dispatch per v7-1;
     three-stage merge per v3-8 + v3-9 + v4-8 + v4-9 + v5-11 + v6-1)
  Tests (unit + supersession + canonicalize +
         Lever #1/#2/#3 + audit + v9/v10 fix tests)  ~700 LOC
                                                     (+~200 over baseline)
  ──────────────────────────────────────────────
  Total: ~2,500 LOC + ~50 lines Cypher + ~135 lines doc
  (Up from prior v8 baseline of ~2,080 LOC by ~250-350 impl + ~200-300 test
   LOC per DriverImprovements §10 Tier-6 fold; net ~15-20% on top of baseline)

Realistic timeline (after spec locks): 7–9 working days
Aggressive timeline: 6 days
(Updated from prior 6–8 to 7-9 per v3-11 honest scheduling +
 Lever #3 + audit tables on Day 5b. Day 5 pre-split into 5a/5b
 per CombinedPlan §11.)
```

**Honesty note**: The "30 lines" figure from earlier audits referred to doc-only. Total engineering = ~2000 LOC. Anyone reading the plan should know this upfront.

---

## §11. Implementation Order (after spec lock)

```
Day 0   — PRECONDITION (BLOCKER for everything below — per DriverImprovements §3 + §9):
            • Final.md §8 `learner_result.v1 primary_driver / contributing_factors[i]`
              schema migration from the live `{summary, category, evidence_refs}`
              (validate_learning.py v3) → `{driver_name, driver_state, direction,
              evidence_refs}` (E21 amended by E30 —
              v6-3 correction: §8 only, §7 stays free-form). Until this lands, the
              learner SKILL.md updates (Day 5a) fight Final.md and Lever #1-#3 sit
              on contradictory foundations for the only Phase-1 producer.
            • §9 pit_cutoff bullet + §11 driver_tags[] bullet + §24 pointer to
              Neo4jXBRLDesign.md (per Neo4j impl-order step 11).
            • NOT optional. (DriverImprovements v4-10 explicitly removed E21 from
              Day 5b; this entry restores the Day-0 PRECONDITION canonical position.)

Day 1   — Spec lock + Neo4j schema:
            • Apply the spec edit list (E1-E30 minus E12 MOOT = 29 active items + Tier-6 fold E26-E29) across 4 spec files (`DriverOntology.md`, `DriverOntology_Implementation.md`, `Neo4jXBRLDesign.md`, plus the `DriverImprovements.md` forensic header reflecting fold status)
            • Driver + DriverChange + DriverDriftAudit constraints/indexes
            • Cold-start seed `COLD_START_SEED_DRIVERS` Python constant
              drafted in `driver_writer.py` (per OQ4)

Day 2   — driver_ids.py:
            • slug() (verbatim from guidance)
            • canonicalize() (NEW — slot grammar + standalone shortcut +
              banned content + new-token gate)
            • classify_token() (NEW)
            • Slot ID computation
            • Unit tests

Day 3   — driver_writer.py + driver_concept_resolver.py:
            • MERGE Cypher (mirror guidance pattern)
            • 15 validators (V1–V15) + new V_no_consecutive_underscores
              (V15 = registry-global dedup = INGESTION-layer, covered in the
               harness by B8 sorted-token reuse; the deterministic harness
               builds V1-V14)
            • Supersession handlers (NEW)
            • registry_visible_at = MIN(DC.pit_cutoff) logic
              (EXCEPT seed-bootstrap drivers — they carry epoch_sentinel
               or per-driver date per E9 TIER 1/TIER 2)
            • Lever #1 repair_and_retry() per E26 — state-strip + V8 check
              + magnitude-narrow regex + trend-partner preference +
              exact-match-only commit
              [DEMOTED/DEFERRED per E26 (do NOT delete) — Pattern A
               (learner self-correct) is the PRIMARY recovery path; build
               this deterministic auto-repair ONLY if post-launch metrics
               show many mechanically-recoverable rejects. NOT a Phase-1
               build item.]
            • Lever #2 write_equivalence_tokens() per E27 — N=2 promotion
              + two-phase Cypher (v5-4 + v6-2) + intra-MERGE to_token guard
              (v9-2) + equivalence_visible_at MIN-backdate (v10-2)
              [the :EquivalenceToken store + two-phase Cypher are
               INTEGRATION-phase (DEFERRED — the harness uses an in-memory
               model per §8 OUT-OF-SCOPE; NOT a Phase-1-harness build item)]
            • write_vocab_token() per E10 amended + v9-1 + v10-1 —
              vocab_visible_at ON CREATE + MIN-on-MATCH backdate
              [the VocabToken store + PIT MIN-on-MATCH backdate are
               INTEGRATION-phase (DEFERRED — the harness uses an in-memory
               model per §8 OUT-OF-SCOPE; NOT a Phase-1-harness build item)]
            • concept_resolver (financial-sliver only; null for
              non-financial drivers per L7 + E17)
            • Unit tests for Levers #1/#2 + v9/v10 fix scenarios

Day 4   — driver_write_cli.py + driver_write.sh + bundle renderer:
            • Source-agnostic input JSON (E16; with is_shortcut + item_index)
            • Cold-start seed loader
            • Bootstrap PIT-filtered loader for promoted_equivalences
              + promoted_vocab_tokens per E10 + E27 read path
            • Bundle registry catalog render (PIT-filtered, candidates HIDDEN
              from LLM per v2 Fix #2)
            • Vocab excerpt render
            • Integration tests

Day 5a  — SKILL.md updates ONLY (per v3-11 + E30 split):
            • Learner SKILL.md emit canonical drivers (~75 LOC;
              earnings-learner only per E30 / v6-6 — earnings-prediction
              stays consumer-only, no SKILL.md edits needed)
            • is_shortcut emission contract teaching (v3-5 + v8-1)
            • Anti-pattern checklist (5-check Before You Emit block)

Day 5b  — Orchestrator retry + audit constraints (Final.md §8 migration is Day 0 PRECONDITION — NOT here):
            • SUPERSEDED 2026-05-29 — Pattern A is now LEARNER-SELF-CORRECT
              (learner calls driver_write_cli.py --dry-run, fixes flagged tags
              <=3, orchestrator write-gate authoritative). The
              run_driver_write()/_merge_retry_response()/3-stage-merge/
              one-retry-cap items below are SUPERSEDED; the self-correct
              build+test items will be re-specified at integration (SKILL.md
              + driver_write_cli.py). Do NOT build the orchestrator-reinjection
              retry. (Old items retained below for reference.)
            • orchestrator.run_driver_write() with informed retry per E28
              Lever #3 (mirror H2 informed-retry logic at orch.py:1347-1387;
              transport-neutral name per Fix #5)
            • _merge_retry_response() 3-stage merge per v3-8/v3-9/v4-8/v4-9
              /v4-15/v5-9/v5-11/v6-1 — drift guard inversion + surgical
              replace + scope creep block + final formula
            • DriverWriteOutcome enum with FAILED_DRIFT_GUARD,
              FAILED_SCOPE_CREEP, FAILED_RETRY_SHAPE_VIOLATION outcomes
            • Neo4j audit constraints per E29 — :DriverAutoRepair
              with item_index (v9-4), :DriverProposalRejection,
              :EquivalenceConflictAudit (v5-1 + v9-2),
              :EquivalenceCollisionAudit (v4-6), :DriverDriftAudit
              [these E29 Neo4j audit tables are INTEGRATION-phase
               (DEFERRED — the harness uses an in-memory model per §8
               OUT-OF-SCOPE; NOT a Phase-1-harness build item)]

Day 6–7 — Production smoke + adversarial tests:
            • AAPL or similar fresh ticker
            • Adversarial canonicalize edge cases
            • Lever #1 repair scenarios (state-smuggle / period-strip /
              magnitude-narrow / trend-partner / V8 check / Fix #4
              exact-match)
            • Lever #2 promotion + collision + backdate tests
              (v9-1/v10-1 VocabToken backdate; v10-2 equivalence backdate;
              v9-2 concurrent-writer race; v5-1 to_token conflict
              acceptance-time; v10-4 ≥2-token shortcut negative)
            • Lever #3 informed retry tests (drift guard / surgical
              replace / scope creep / orphan drop / same-name replacement)
            • Concurrency stress test (learner re-runs concurrent on same
              source_id; future Phase-2 news producer concurrent with
              learner once it ships). Predictor concurrency is N/A per E30
              — predictor doesn't write to registry.
            • PIT backfill replay test — verify VocabToken +
              EquivalenceToken backdates produce L6-correct visibility
              under reverse-chrono + out-of-order PIT arrival
            • Supersession on re-run test
```

---

## §12. Acceptance Criteria (how to know it's done)

```
LOCK CONDITIONS — spec is locked when all true:
  ✅ All 29 ACTIVE E* items (E1-E30 minus E12 RESOLVED MOOT) reflected in target file
     — 24 original (E1-E25 minus E12 MOOT) + 4 Tier-6 fold (E26 Lever #1, E27 Lever #2,
     E28 Lever #3, E29 audit tables) + E30 producer-scope = 29
     (NOTE: the E27 :EquivalenceToken/VocabToken store + two-phase Cypher and the E29
      Neo4j audit tables are INTEGRATION-phase (DEFERRED — the harness uses an in-memory
      model per §8 OUT-OF-SCOPE; NOT a Phase-1-harness build item); they remain part of
      the full design and the spec-lock count, just not the Phase-1 harness build set)
  ✅ OQ1, OQ3, OQ4 answered (OQ2 RESOLVED MOOT per E30 — dropped from
     pending-decisions list; predictor consumer-only, no source-visibility
     gap exists)
  ✅ No human/curator/manual-review string remains in any spec file
  ✅ ConceptReq coverage matrix shows 10/12 ✅ + 2/12 ⏸ DEFERRED (post-E30 / v6-6 update)
  ✅ Implementation file's Conformance Index (§H) maps every rule to ≥1 clause
  ✅ E27 entry explicitly carries v9-1 + v10-1 (vocab_visible_at + MIN-backdate),
     v9-2 (intra-MERGE to_token guard), v10-2 (equivalence_visible_at MIN-backdate)
     — per v10-5 Phase-B fold reminder; without explicit inclusion these fixes
     can be lost in the fold

BUILD CONDITIONS — code is done when all true:
  ✅ canonicalize() unit tests cover: slot reorder, standalone shortcut,
     compound metric collapse, stopword strip, banned-content rejection,
     new-token gate, ALL 25 E* items where mechanical
  ✅ MERGE writer concurrency test passes (2 concurrent writers, same source)
  ✅ PIT backfill replay shows no future-vocab leak
  ✅ Supersession on re-run: dropped drivers carry superseded_pit_cutoff
  ✅ Cold-start seed: registry has ≥30 entries after load; each entry
     passes V1–V15; canonicalize() is idempotent on every seed name;
     TIER 1 seeds have registry_visible_at = epoch_sentinel per E9
  ✅ Production smoke reuse rate (volume-dependent thresholds;
     numbers are initial estimates pending real-data calibration —
     revise after first cohort):
       ≥70% within-ticker after 5+ emissions on same ticker
       ≥50% cross-ticker after 20+ emissions across tickers
       ≥85% once registry exceeds ~150 drivers
  ✅ Driver-write failure → no complete.json sentinel
  ✅ Adversarial input (banned tokens, consecutive underscores, etc.)
     all rejected with named V*-rule reasons

EXPLICIT PER-EDIT TESTS (close ambiguity from "adversarial input" bullet):
  ✅ E5 PIT filter test: historical-run replay renders bundle catalog
     filtered by registry_visible_at <= run.pit_cutoff
  ✅ E7 consecutive-underscore test: `iphone__sales` rejected with
     shape violation
  ✅ E10 token-persistence test: accepted new token appears in slot
     vocab on next run; canonicalize deterministic across runs;
     zero-anchor proposal rejected as slot_anchor_unavailable
  ✅ E13 fiscal.ai-consults-registry test: direct ingest of a raw
     KPI label that canonicalizes to an existing driver REUSES,
     does not create new
  ✅ E25 allowed_states-mismatch test: reuse of existing driver
     where emission carries different allowed_states does NOT mutate
     registry; logs to drift audit
  ✅ E26 Lever #1 auto-repair tests: state-smuggle / period-strip /
     magnitude-strip narrowed regex (v3-2) / trend-partner preference
     (v3-3) / V8 post-repair check (v4-5) / exact-match-only commit (Fix #4)
     / case-insensitive driver_state (v6 Fix #9) / cascade_outcome
     populated (v4-17). :DriverAutoRepair UNIQUE on (source_id,
     item_index) per v4-14 + v5-2 + v9-4
  ✅ E27 Lever #2 EquivalenceToken tests: candidate creation /
     observation_keys event-level dedup (v4-2) / N=2 promotion gate
     (v3-14) / equivalence_id collision rule (v5-1) / two-phase Cypher
     under MERGE locking (v5-4 + v6-2 + v10-3 concurrency invariant) /
     equivalence_visible_at PIT anchor (v4-7) + MIN-backdate on each
     observation (v10-2) / intra-MERGE to_token conflict guard race
     protection (v9-2) / VocabToken vocab_visible_at PIT filter (v9-1) +
     MIN-on-MATCH backdate (v10-1) / shortcut direct Driver registration
     with is_shortcut=true (v5-5 + v8-1) + ≥2-token gate (v7-2) +
     negative test (v10-4) / hide candidates from LLM bundle (v2 Fix #2)
  ✅ E28 Lever #3 informed retry tests:
     SUPERSEDED 2026-05-29 — Pattern A is now LEARNER-SELF-CORRECT
     (learner calls driver_write_cli.py --dry-run, fixes flagged tags
     <=3, orchestrator write-gate authoritative). The
     run_driver_write()/_merge_retry_response()/3-stage-merge/
     one-retry-cap items below are SUPERSEDED; the self-correct
     build+test items will be re-specified at integration (SKILL.md +
     driver_write_cli.py). Do NOT build the orchestrator-reinjection
     retry. (Old test items retained below for reference.)
     H2 pattern mirror /
     producer-specific DRIVER_FIELDS dispatch (v7-1 + v10-6
     contributing_factors, no key_drivers) / drift guard inversion
     (v4-8) / surgical replace + tuple equality (v4-9 + v5-9) / orphan
     proposal drop (v4-15) / STAGE 3 same-name replacement (v5-11) +
     scope creep block / final merge formula subtracts replaced + orphaned
     (v6-1) / one-retry cap
  ✅ E29 audit table tests: :DriverAutoRepair item_index property
     populated (v9-4) / :EquivalenceConflictAudit distinct from
     :EquivalenceCollisionAudit (v5-1 + v9-2 vs v4-6) /
     :DriverDriftAudit on direction flip

PASS-4 PROOF GATE (the CRUX proof — GO/NO-GO):
  ✅ Pass 4 = the CRUX proof (GO/NO-GO): it must target the HARD /
     registry-fragmenting cases (the F9-F12 semantic near-dup families,
     not just the easy anchored ones) AND MEASURE the cross-LLM equality
     rate -> emit eval_report.json as the GO/NO-GO gate. This converts the
     ~95-98% from PROJECTION to MEASURED; harness-green on the deterministic
     core is necessary but NOT sufficient to prove the "same concept ->
     same name" claim.
```

---

## §13. Risk Register

> **Scope note (semantic-discrimination risks are judge-domain, not a code gap)**: Semantic-discrimination risks (mechanism-collision oil_price/oil_supply, wrong-discriminator, alias-undermatch) are NOT deterministic-code-covered (V1-V14) BY DESIGN — they are Pattern B isolated-judge domain (scope/reuse) + the embedding near-dup trigger + the reconciliation job. Declared judge-domain, not a code gap.

| Risk | Mitigation |
|---|---|
| Canonicalize edge cases discovered late | Adversarial test suite Day 6–7; spec lists known edge classes |
| Slot classification ambiguity for novel tokens (e.g. `hyperscaler_datacenter_capex`) | Position-based slot inference + E10 persists accepted mappings |
| Concurrency on Driver writes (learner re-runs same source_id concurrently; future Phase-2 news producer concurrent with learner) | E11 transactional MERGE + UNIQUE constraint + retry. Predictor concurrency N/A per E30 — predictor doesn't write |
| Cold-start period weak accuracy | E9 ~30-driver seed; aliases compound over time |
| Vocab grows faster than expected | E10 auto-grow path; `COLD_START_SEED_DRIVERS` Python constant editable in `driver_writer.py` source (revise after first cohort if observed reuse below threshold) |
| Final.md drift after schema change | E21 explicit field-by-field migration spec |
| News/fiscal.ai future work re-opens decisions | L2 + L7 lock the routing; Mode 2/3 framework already in spec |
| Validators V1-V15 miss a real-world bad-name pattern | Iterate as bugs surface; framework supports additive validators |
| Cold-start seed quality (OQ4 source choice) | E9 + OQ4 hardcoded-constant default; if seed is poorly chosen, slot anchors weak for early production; revise seed contents after first cohort if observed reuse < first threshold band |
| ~~ConceptReq §3.3 deferral (predictor restricted to current bundle per OQ2-a)~~ — **RESOLVED per E30 (v8-2 cleanup)**: predictor is consumer-only, NOT a producer. The transcript/10-K/Q grounding gap was about predictor's emission scope, which is now moot. ConceptReq §3.3 has been rewritten to align with §3.2 (learner produces, predictor consumes). OQ2 is also MOOT. No deferral risk remains | Row resolved by E30; kept for forensic audit trail |
| Slot vocab pollution by low-quality accepted proposal | Mitigation: vocab append only after ALL V1–V15 validators pass; E10 zero-anchor rejection blocks worst case (proposals with no known tokens); periodic vocab audit via Day 6–7 adversarial test suite; **code-time pruning** (engineer edits `COLD_START_SEED_DRIVERS` constant and/or runs a Cypher migration to deprecate bad VocabToken nodes if observed pollution; consistent with L4 — no runtime human curation, only code-time engineering) |
| **Lever #1 over-repair (E26)** — auto-repair commits wrong fix | Mitigation: Fix #4 exact-match-only commit (no new Driver invented), v4-5 V8 post-repair check (state must be in registry's allowed_states), v3-3 trend-partner preference, conflict-rejection rule (never guess when driver_state already set to different value). All repairs logged to `:DriverAutoRepair` with `repair_kind` + `cascade_outcome` for telemetry. Audit-data review at Q1 if pattern emerges of mis-repairs |
| **Lever #2 false equivalence promotion (E27)** — N=2 promotes a wrong synonym | Mitigation: v5-1 conflict rule (only ONE to_token may PROMOTE per kind+from_token; a conflict FREEZES promotion + escalates to one isolated judge call → persist exactly one of {to_A, to_B, NO-GLOBAL-RULE → driver-level reuse only}, N=2 gate first), v4-6 collision recheck at promotion (registry may have changed between candidate + promotion), v4-2 event-level observation dedup (predictor+learner on same event = ONE observation, not TWO), v9-2 intra-MERGE to_token race guard, candidates HIDDEN from LLM bundle (v2 Fix #2 — prevents fast-pass via LLM self-reinforcement), promoted equivalences traceable via `:EquivalenceConflictAudit` + `:EquivalenceCollisionAudit` |
| **Lever #3 LLM-retry token cost (E28)** | **SUPERSEDED 2026-05-29 — Pattern A is now LEARNER-SELF-CORRECT (learner calls `driver_write_cli.py --dry-run`, fixes flagged tags <=3, orchestrator write-gate authoritative). The `run_driver_write()`/`_merge_retry_response()`/3-stage-merge/one-retry-cap mitigation below is SUPERSEDED; the self-correct build+test items will be re-specified at integration (SKILL.md + driver_write_cli.py). Do NOT build the orchestrator-reinjection retry.** (Old mitigation retained for reference:) 1-retry cap (production-validated learner H2 pattern); retry only fires on validation failure (~5-10% of emissions); affordable burn (~5K-15K tokens per retry × ~15-30 retries per quarter = bounded). 3-stage merge (drift guard + surgical replace + scope creep block) prevents wasted retries from LLM-misbehavior; FAILED_DRIFT_GUARD outcome short-circuits if R2 mutates non-driver fields |
| **VocabToken legacy NULL `vocab_visible_at` (E10 + v9-1 + v10-1)** — pre-v9-1 VocabToken rows lack the new field | Phase-1 deployment requires one-time NULL-fill migration OR treat NULL as epoch_sentinel (1970-01-01) in the read-path WHERE clause. Latter is simpler + safer (no batch update needed; NULL → always-visible like timeless TIER-1 seed drivers). Decide at Day 1 schema lock; either path is one-line implementation |

---

## §14. Vote Request

Reviewer of this plan: answer ONE question.

> **"Does this plan, when applied, produce a spec that satisfies all three hard conditions (≥90% accuracy, 100% ConceptReq accounted-for (covered or explicitly deferred), minimum incremental work) with no unsurfaced gaps?"**

Acceptable answers:
- **YES** — spec is ready to apply + Python build can start
- **NO** — list every specific gap you can name, with location

If NO is returned by ≥2 reviewers on the same gap, that gap becomes a new E* item and re-vote.

---

## Appendix A — Paste-ready text for Claude3 (if Claude3 owns the spec edits)

```
Your 30-line plan is directionally correct but understates 29 active
E* items (E1-E30 minus E12 RESOLVED MOOT) identified across 5
independent audits + 6 fold rounds of DriverImprovements v2-v10.
Apply all 29 from §5 of CombinedPlan.md before declaring done.
Per-file breakdown (post Tier-6 fold):

  DriverOntology.md:                ~5 lines   (E23 R5 full rename:
                                                title + body + impl
                                                SHORTCUTS_VOCAB references)
  DriverOntology_Implementation.md: ~140-160   (E1, E4-E11, E15-E19, E24,
                                       lines   E25 + Tier-6 fold:
                                                §A.1/§A.2 Lever #1 (E26),
                                                §F.10 NEW Live Token Stores
                                                  (E27 — Pattern A1 VocabToken
                                                   + vocab_visible_at MIN-on-MATCH
                                                   per v9-1 + v10-1,
                                                   Pattern A2 EquivalenceToken
                                                   + two-phase Cypher per
                                                   v5-4 + v6-2, intra-MERGE
                                                   to_token guard v9-2,
                                                   equivalence_visible_at
                                                   MIN-backdate per v10-2,
                                                   Pattern B shortcut Drivers
                                                   per v5-5 + v8-1 + v7-2),
                                                §J NEW writer contract +
                                                  retry (E28 Lever #3 with
                                                  v7-1 producer dispatch +
                                                  v10-6 contributing_factors),
                                                §K NEW audit schemas (E29 +
                                                  v9-4 item_index))
  Neo4jXBRLDesign.md:               ~50-60     (E2, E3, E11, E13, E14, E20,
                                       lines    E21, E22 + Final.md §24
                                                pointer fix + v8-1
                                                Driver.is_shortcut + NEW
                                                schemas for :EquivalenceToken
                                                (E27), :VocabToken with
                                                vocab_visible_at (E10 amended
                                                + v9-1 + v10-1), 5 audit
                                                labels (E29 + v9-4),
                                                + UNIQUE constraints.
                                                E12 dropped per E30.)

Decide OQ1 (validation_status drop),
~~OQ2 (predictor source restrict)~~ — DROPPED per E30 / v8-3 (predictor consumer-only, MOOT),
OQ3 (R5 rename accept), OQ4 (cold-start seed source = hardcoded
constant) before applying. Recommended: OQ1 + OQ3 + OQ4 accepted as
defaulted in §6.

Accuracy after applied: ~96-98% projection pending Q1 measurement
(up from ~87% v8 baseline; per DriverImprovements §10 + v3-12 honest framing).
(PROJECTION, not a verified/measured figure — methodology TBD: which deduped set + how a correct naming is counted; do not cite as achieved. Raw LLM consistency caps ~85%; the lift is from the deterministic compiler + levers.)
ConceptReq coverage: 100% accounted for (10 ✅ + 2 ⏸ DEFERRED with rationale per E30 / v6-6).
Total documentation additions: ~135 lines (post Tier-6 fold).
Engineering work AFTER spec lock: ~2,500 LOC + ~50 Cypher + 7-9 days
  (~250-350 impl + ~200-300 test LOC on top of prior v8 ~2,080 LOC baseline).
```

---

**End of CombinedPlan.md** — ready for review vote.
