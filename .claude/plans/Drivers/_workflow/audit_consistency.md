# CONSISTENCY Audit — Driver CREATION Layer (P1/P2/P5 + DriverOntology)

Adversarial internal-consistency lens. Every claim verified against CURRENT bytes on disk (read in full:
P2 DriverOntology_Implementation.md, P5 DriverOntology Prompt.md, DriverOntology.md, reuse_map.md;
targeted reads of P1 CombinedPlan.md; grep against live guidance code G1/G2/G3). No claim taken on the
plan's own word — the plan documents >=9 prior stale-state false-positives.

Scope = the CREATION layer (evidence → clean canonical validated name + companion fields, BEFORE the Neo4j
write). Ingestion judged only on clean hand-off. Three hard conditions: ~100% naming accuracy (bar >=90%),
100% requirement-file coverage, minimum incremental work / max reuse.

---

## CON-1 (major) — §F.5 STATES_VOCAB vs §F.9 ALLOWED_VERBAL_FORMS: `restricted` + `accumulated` in BOTH; canonicalize step 7 makes §F.9 a dead letter for them

- §F.5 STATES_VOCAB (P2:378-384): `accumulated` ∈ quantity_move; `restricted` ∈ policy_action.
- §F.9 ALLOWED_VERBAL_FORMS (P2:439-440): `{consolidated, diluted, weighted, restricted, deferred, accrued,
  retained, accumulated, underwriting, lending}` — explicitly "may appear in `name`".
- canonicalize() step 7 (P2:154-158):
  ```
  for t in normalized:
      if t in vocab.banned:  return REJECTION_BANNED_TOKEN(t)
      if t in vocab.states:  return REJECTION_STATE_IN_NAME(t)   # §F.5 — NO §F.9 carve-out here
  ```
- The §F.7 `verb_form` ban (P2:423-425) DOES carve out §F.9 (`... ∪ ALLOWED_VERBAL_FORMS (§F.9)`). But the
  SEPARATE `vocab.states` branch in step 7 has NO §F.9 exception. So `accumulated`/`restricted` are caught by
  the states branch and rejected from any name (e.g. `accumulated_deficit`, `restricted_cash`,
  `accumulated_depreciation`), directly contradicting §F.9's promise that they may appear in name.
- DriverOntology R7 (DriverOntology.md:54) names only 3 example exceptions (`consolidated, diluted, weighted`)
  and does not flag the states-collision either.
- Determinism is preserved (it always rejects), so this is not an accuracy blocker — but it is a genuine
  internal contradiction between two reference banks and the function that reads them, and it silently makes
  two legitimate accounting qualifiers un-nameable.
- FIX: either (a) remove `accumulated`/`restricted` from §F.9 (accept they are states-only), or (b) add a
  `and t not in vocab.allowed_verbal_forms` guard to the states branch of step 7, or (c) document that §F.9
  applies ONLY to the verb_form regex ban, not the states-set ban (and drop the two collision tokens from F.9).

## CON-2 (major) — "known token" definition is inconsistent across B8 / new-token gate / V14 / grammar; §F.6 COMPOUND_METRICS omitted from the gates

- B8 sorted-token reuse (P2:67): known = registry name/aliases + **§F.2–F.4 maps** only.
- §D new-token gate (P2:258, 263): known = registry name/aliases + **§F.1–F.5** entry.
- V14 (P2:287): "for every token in `name` not present in **registry/banks**" — unspecified range.
- Grammar BNF (P2:253): `<metric> ∈ METRICS ∪ COMPOUND_METRICS` — §F.6 IS a legitimate metric vocabulary.
- Conflict: a canonical compound-metric token from §F.6 (e.g. `gross_margin`, `operating_margin`,
  `free_cash_flow`) is a KNOWN metric for the grammar/classifier (step 9-10 uses `vocab.compound_metrics`,
  P2:114-116) but is treated as UNKNOWN by both B8 (F.2-F.4 only) and the new-token gate (F.1-F.5, no F.6).
  A first-ever proposal using `gross_margin` would be routed through the new-token gate as if `gross_margin`
  were a brand-new token, and gate clause (d) (P2:263) only checks against §F.1–F.5, never §F.6.
- Partial mitigation: §F.2 multi-token subs (`gross_profit → gross_margin`) and step-2 substitution exist,
  and `gross_margin` may already be a seeded Driver (J.2 TIER-1, P2:674), in which case B3 exact-match short-
  circuits before the gate. But the bank-range definitions themselves are genuinely divergent (F.2-F.4 vs
  F.1-F.5 vs "registry/banks" vs grammar's F.6 inclusion). This is the exact "engineer reads the gate, omits
  F.6" hazard the plan elsewhere warns about.
- FIX: pick ONE canonical "known-token bank set" (almost certainly F.1–F.6) and use it verbatim in B8, the
  new-token gate (clauses present + d), and V14. Spell out whether §F.6 counts as known.

## CON-3 (major) — fictional `guidance_change_id()` in P2 §J.1 Mirror Map (verified WRONG vs live code)

- P2 §J.1 (P2:624-626): `driver_ids.driver_change_id() ← guidance_ids.guidance_change_id() (same 3-component
  slot ID pattern; driver-specific tokens)`.
- Verified against G1 guidance_ids.py: `grep change_id` across G1/G2/G3 = ZERO hits. `guidance_change_id()`
  does not exist. The real ID builder is `build_guidance_ids()` (G1:814) producing `guidance_id =
  f"guidance:{label_slug}"` (G1:962) and `guidance_update_id = f"gu:{safe_source_id}:{label_slug}:
  {period_u_id}:{basis_norm}:{segment_slug}"` (G1:963-966).
- The "3-component" count is also wrong: `guidance_update_id` is 5-component after the `gu:` prefix.
- This is the precise hazard E15 itself was created to fix ("engineer copying the mirror map verbatim would
  hit wrong file + name", P1:247), yet the §J.1 map STILL contains the bad row. E15 in P1 (P1:239-247) lists
  4 mirror-map fixes but never touches the `guidance_change_id` row, so it slipped through.
- Matches reuse_map.md Claim C (verified). FIX: replace the row with `guidance_update_id` slot-concatenation
  assembly (G1:963-966), drop the invented `guidance_change_id` name, correct "3-component" → "5-component".

## CON-4 (major) — SKILL.md LOC: changelog claims a bump to ~150 that the actual numbers (~75) never reflect

- Round 6 changelog (P1:64): "**§10** (SKILL.md LOC bumped ~50 → ~150 for honesty)".
- Round 8 changelog (P1:66): "M1 Day 5 overload after Round 6 ~150 LOC SKILL.md bump" + "§10 timeline bumped
  5-7 → 6-8 days reflecting Round 6 SKILL.md LOC correction".
- But the actual figures on disk: §10 (P1:580) "Learner SKILL.md emission updates  **~75 LOC**" and §11
  Day 5a (P1:669) "Learner SKILL.md emit canonical drivers (**~75 LOC**...)". `grep ~150` returns only
  `driver_concept_resolver.py ~150 LOC` (P1:572) and "registry exceeds ~150 drivers" (P1:746) — neither is
  SKILL.md.
- So the changelog records a ~50→~150 bump "for honesty" that was either never applied or silently reverted,
  while the changelog still asserts it happened. This is exactly the stale-state class of defect the audit
  warns about, living inside the plan's own log. FIX: reconcile — either set the SKILL.md figure to ~150
  (matching the Round-6/8 narrative) or correct the changelog to state the figure stands at ~75.

## CON-5 (major) — §8 per-file manifest (~60 / ~20) contradicts Appendix A (~140-160 / ~50-60) for the SAME files; Round-7/8 "synced" claims are false

- §8 manifest: DriverOntology_Implementation.md "Total change: **~60 lines**" (P1:473); Neo4jXBRLDesign.md
  "**~20 lines**" (P1:492). Both items lists INCLUDE Tier-6 items (E27, E29 in the Neo4jXBRL list P1:494-497;
  §J/§F.10 Tier-6 work in the Impl list).
- Appendix A: DriverOntology_Implementation.md "**~140-160 lines**" (P1:844); Neo4jXBRLDesign.md "**~50-60**"
  (P1:865) — the post-Tier-6 figures.
- Round 7 (P1:65): "Appendix A (per-file LOC counts updated to match §8 manifest: 5/60/20 ...)".
- Round 8 (P1:66): "§8 per-file synced to 5/60/20 (matches Appendix A Round 7 update)".
- Both reconciliation claims are FALSE against current bytes: Appendix A shows 5 / **140-160** / **50-60**,
  NOT 5/60/20. The Implementation file differs by ~2.3x (60 vs 140-160) and Neo4jXBRL by ~2.5-3x (20 vs
  50-60) between the two sections that both purport to be the per-file breakdown. The §8 ~60/~20 are the
  PRE-Tier-6 numbers but §8 lists the Tier-6 items, so its line counts undercount its own item list.
- This is a real cross-section numeric contradiction (not polish): the grand-total ~135 line claim
  (P1:520, 555, 595, 886) is built on the §8 numbers (5+60+20=85 pre-Tier-6 + ~50 Tier-6 = ~135) while
  Appendix A's per-file numbers (5+150+55 ≈ 210) cannot reconcile to ~135. FIX: make §8 and Appendix A use
  one consistent post-Tier-6 per-file set, and re-derive the grand total from it.

## CON-6 (minor) — Goal-line accuracy bar disagrees with the Hard-Conditions bar (>=95% vs >90%)

- P1:5 Goal: "**≥95%** driver naming accuracy".
- P1:35 Hard Condition #1: "**>90%** driver naming accuracy — credibly achievable, not aspirational."
- P1:822 Vote Request: "**≥90%** accuracy".
- The enforced bar appears three different ways (≥95 in the goal header, >90 in the hard condition, ≥90 in
  the vote). Minor (the binding bar is clearly >=90 per §3), but the goal header overstates it to 95.

## CON-7 (minor, OVERSTATEMENT) — "~96-98% accuracy projection" is unsupported and conflated with clean-landing rate

- P1:883 "Accuracy after applied: ~96-98% projection pending Q1 measurement". DriverImprovements.md:898,
  1232, 1309 frame ~96-98% as the **clean-landing rate** (% of emissions that wrote without rejection AND
  without registry split) AFTER 8 quarters, explicitly "PROJECTIONS derived from estimated LLM failure rates"
  (DriverImprovements.md:1309). The enforced bar is >=90% (P1:35).
- So ~96-98% is (a) a projection with no measurement, and (b) a clean-LANDING metric being presented in P1's
  bottom-line as "Accuracy". Per the anti-overstatement rule this must not be read as achieved naming
  accuracy. Matches reuse_map.md Claim G and scope_split. The user's ~100% target is NOT mechanically
  demonstrated; TIER-1 cold-start seed explicitly does NOT cover object/customer/theme slot anchors
  (P1:177), so early novel-token slot classification can drift.

## CON-8 (minor, OVERSTATEMENT) — "maximum reuse" / L7 reuse list over-credit the creation layer

- P1:37 "maximum reuse of guidance pipeline templates"; P1:5 "minimum incremental work on top of the locked
  ontology + guidance pipeline templates"; L7 (P1:29) lists "writer/IDs/MERGE/concept-resolver/**member-map**
  machinery REUSED".
- Verified against live code (reuse_map.md, confirmed by my grep): for the CREATION layer the only verbatim
  reuse is `slug()` (G1:21-26, exact match to P2 §B2). The entire canonicalize() grammar, classify_token,
  order_by_slot, VocabSnapshot, SHAPE_REGEX, gates, V1-V15, cold-start seed are NET-NEW (grep-empty in
  guidance). member-map (`_apply_member_map` G3, guidance-segment→XBRL-Member) has NO driver equivalent and
  must be STRIPPED, not "reused" — so L7 lumping it into the reuse list is wrong for the creation layer.
- P1's body is honest elsewhere (§10 "~2,500 LOC" total engineering, mostly net-new), but the headline
  "maximum reuse" + L7 over-state borrowable surface. Minor: does not block; misleads an engineer copying
  the framing.

---

## Sub-areas verified CLEAN (no finding emitted)

- **R5 "macro → standalone shortcut" rename fully propagated.** DriverOntology.md R5 (DriverOntology.md:49-50)
  uses "Standalone shortcut" + SHORTCUTS_VOCAB; P2 uses SHORTCUTS_VOCAB throughout (§C step 8 P2:160-163,
  §F.1 P2:306, §H P2:502); P5 uses "standalone shortcut" consistently (P5:9, 61, 76, 84, 126, 130). No
  residual `MACROS_VOCAB` / "macro shortcut" in the creation-scope files. E23 full-rename is complete.
- **`share_buyback` placement consistent.** §F.1 SHORTCUTS_VOCAB (P2:310) holds it; §F.6 COMPOUND_METRICS
  explicitly REMOVED it with rationale (P2:395-397); P5 preamble item 4 (P5:12) agrees. Coherent.
- **STATES_VOCAB ↔ banned-state-verb rule (the main one) is consistent.** canonicalize step 7 rejects any
  §F.5 state from a name (REJECTION_STATE_IN_NAME, P2:157) and V8 requires driver_state ∈ allowed_states
  (P2:281). States are banned from name, allowed in driver_state — internally coherent (the ONLY breakage is
  the F.9 overlap, CON-1).
- **P5 author prompt ↔ P2 mechanism field contract.** P5:38 propose_new_drivers fields
  `{name, label, base_label, segment, definition, allowed_states, aliases, is_shortcut}` exactly match P2 E16
  (P2:569-579). P5's "no new fields / no token-only proposals / Python-canonicalize-not-LLM" constraints
  align with L3 and the §C pure-function design. No P5↔P2 contradiction found.
- **Hand-off contract clean.** canonicalize() is a pure function taking a frozen VocabSnapshot param, zero
  Neo4j reads (P2:85-88, 118); load_vocab_snapshot() builds the snapshot before any call (P2:187-226); E16
  input JSON is self-contained (P2:545-582). Creation does not depend on writer/MERGE/promotion/audit
  internals. (The source_type enum {learner_result,news,fiscal_kpi} is disjoint from guidance's {8k,10q,...}
  and the guidance REQUIRED_ITEM_FIELDS must be replaced not inherited — already flagged in reuse_map.md
  NIT-1/NIT-2; not re-raised here as those are reuse-map's lane.)
- **slug() reuse claim VERIFIED.** P2 §B2 description matches G1:21-26 verbatim. The one true verbatim reuse.
- **Guidance LOC claims VERIFIED.** G1=1000, G2=524, G3=656 (wc -l). P1/reuse_map figures correct.
- **§9 ConceptReq coverage math internally consistent** (10 ✅ + 2 ⏸ = 12, P1:541) — though it depends on
  ConceptualRequirements.md content, which is a separate dimension's question, not this consistency lens.
