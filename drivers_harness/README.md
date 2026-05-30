# drivers_harness — Driver-Naming Pass 1 (deterministic core)

Pure offline, stdlib-only pytest harness for the driver name-cleaner. NO LLM, NO
network, NO Neo4j/Redis. Layer-2 (real-LLM judgment) is **Pass 4** and is NOT run
here. This is the **Pass 1** deterministic core: `canonicalize()` (§C), the §D.1
slot functions, the §E validators V1..V14, the §B reuse ladder, the S1→S6 chain,
and the catalog renderer.

## Run

```bash
source /home/faisal/EventMarketDB/venv/bin/activate
cd /home/faisal/EventMarketDB/drivers_harness
python3 -m pytest -q
```

`pytest.ini` sets `addopts = -m "not llm"`. The `llm` marker is **reserved for
Pass 4** (real-LLM Layer-2); no test carries it in Pass 1, so `-m llm` collects 0.

**Status:** `202 passed in ~0.1s` (0 failed, 0 errors, 0 skipped, 0 xfail) — after
the Pass-1 corrective round (2026-05-29, v11-2 broadened §C step-4.5 freeze + the
emission-level V13 orphan scan + K53 self-consistency check + the K26 motion-noun
seed + regression tests in `tests/test_pass1_corrective.py`). Bucket K
(idempotency) fully green and now parametrized only over string-canonicalizing
inputs (no latent skip). The reserved Pass-2/4 files are absent. Prod-core purity
holds.

## PROD-CORE vs TEST-SCAFFOLD (Harness §9)

PROD-CORE (copies to production unchanged, imports no scaffold):
`driver_ids.py`, `vocab_seed.py`, `validators.py`, `reuse.py`,
`render_catalog.py`, `run_one.py` (hosts `learner_to_writer_input`).
TEST-SCAFFOLD (never imported by prod-core): `registry_fake.py`,
`run_sequence.py`, all of `tests/`. Enforced by
`tests/test_prod_core_purity.py` (AST import scan + grep + reserved-file absence).

---

## (a) COVERAGE LEDGER

Every CREATION-scoped item → the test (file::test) that proves it. `T:` = file in `tests/`.

### canonicalize / §C / shape / folds — K1..K6, K22, K27, K29, K32..K35, R3/R5/R6/R8

| Item | Rule | Test |
|------|------|------|
| K1 CamelCase reject | §C step 1 / §D shape | `T:test_canonicalize::test_A_camelcase_rejected` |
| K2 wrong separator (hyphen) | §C step 1 (direct) | `T:test_canonicalize::test_A_hyphen_rejected_on_direct_call` |
| K3 non-ASCII | §C step 1 | `T:test_canonicalize::test_A_non_ascii_rejected` |
| K4 doubled/edge underscore | §D `_(?!_)` | `T:test_canonicalize::test_A_doubled_underscore_rejected` / `_leading_` / `_trailing_` |
| K5 (shape family) | §C step 1 | covered by K1–K4 group above |
| K6 / R8 length bound | §C step 11 / §G=4 | `T:test_canonicalize::test_E_too_many_slots_five_distinct`; `T:test_edge_cases::test_ADV_five_distinct_slots_too_many_slots` |
| K22 shortcut early-return | §C step 8 / R5 | `T:test_canonicalize::test_E_oil_price_shortcut_early_return` |
| K27 anchor/order inversion + R3 | §C step 10 | `T:test_canonicalize::test_C_word_order_sales_iphone_china` / `test_E_two_geographies_slot_collision` |
| K29 no metric | §C step 11 | `T:test_canonicalize::test_E_no_metric` / `test_D_data_center_..._no_metric` |
| K32 word-order variant | §C step 10 / R3 | `T:test_canonicalize::test_C_word_order_china_iphone_sales` |
| K33 plural variant | §C step 5 (§F.3) | `T:test_canonicalize::test_C_plural_fold_then_reorder` |
| K34 synonym / multi-token sub | §C step 2/5 (§F.2) | `T:test_canonicalize::test_D_synonym_topline_to_revenue` / `_multi_token_sub_gross_profit_` |
| K35 acronym fold | §C step 5 (§F.4) | `T:test_canonicalize::test_D_acronym_gm_to_gross_margin` / `_fcf_compound_metric_accepts` |
| R6 compound = ONE slot | §C step 4.5/8.5 (§F.6) | `T:test_canonicalize::test_D_cloud_gross_margin_one_metric_slot`; `T:test_edge_cases::test_ADV_compound_metric_makes_four_not_five_accepts` |
| doubt#45 shape regex safe | §D regex | bucket A group (`test_A_*`) |
| doubt#13 two geographies → collision | §C step 10 / R3 | `T:test_canonicalize::test_E_two_geographies_slot_collision`; `T:test_edge_cases::test_doubt13_two_geographies_slot_collision` |

### validators §E — V1..V14, B-F1..B-F10, K38..K49 / K53..K58

| V / K | Contract row | Test (pass + fail) |
|-------|------|------|
| V1 (K45 alias→parent) | B-F5 | `T:test_validators::test_V1_pass_*` / `test_V1_fail_*` |
| V2 (K46 alias bridge / R10) | B-F5 | `T:test_validators::test_V2_pass_*` / `test_V2_fail_*` |
| V3 (K49 label==name set) | B-F6 | `T:test_validators::test_V3_pass_*` / `test_V3_fail_*` |
| V4 (K39 segment Total vs subdim) | B-F7 | `T:test_validators::test_V4_pass_*` (×2) / `test_V4_fail_*` |
| V5 (K48 base_label / §F.6) | B-F8 | `T:test_validators::test_V5_pass_*` (×2) / `test_V5_fail_*` |
| V6 (K40 narrow/K41 broad/K42 not-verbs/K43 mixed / §G) | B-F10 | `T:test_validators::test_V6_pass_*` + 4 fail cases |
| V7 (K38 empty/>1-sentence/tautology) | B-F9 | `T:test_validators::test_V7_pass_*` + 3 fail cases |
| V8 (K44/K56 state not in allowed) | B-F2 | `T:test_validators::test_V8_pass_*` / `test_V8_fail_*` |
| V9 (K55 direction enum) | B-F3 | `T:test_validators::test_V9_pass_*` / `test_V9_fail_*`; `T:test_edge_cases::test_doubt44_bad_direction_enum_is_rejected` |
| V10 (K57 empty/non-SRC/hallucinated, E18) | B-F4 | `T:test_validators::test_V10_pass_*` + 2 fail cases |
| V11 (K54 unresolved name) | — | `T:test_validators::test_V11_pass_*` (×2) / `test_V11_fail_*` |
| V12 (duplicate proposal NAMES only — does NOT cover K53) | — | `T:test_validators::test_V12_pass_*` / `test_V12_fail_*` |
| V13 (proposal_without_use) | — | `T:test_validators::test_V13_pass_*` / `test_V13_fail_*` |
| V14 (K58/R11 new-token gate / §D) | — | `T:test_validators::test_V14_pass_*` / `test_V14_fail_*`; `T:test_edge_cases::test_G_novel_token_*` |
| B-F1..B-F10 field-contract rows | §E table | mapped per-V above; emission-shape pre-check `validate_emission_shape` exercised via `run_one` in `test_edge_cases` / `test_sequence` |

### Pass-1 corrective round (2026-05-29) — #3/#4/#5 + K12-person/K14/K17/K24/K26/K53

The independent review found 3 code bugs + coverage gaps the green suite missed.
The owner amended the spec to **v11-2** (broadened §C step 4.5 freeze over the FULL
known multi-token atom set: `VocabSnapshot.frozen_atoms`). New regression tests:

| Item | Rule | Test |
|------|------|------|
| #3 / K15 multi-token XBRL ban | §C 4.5 v11-2 freeze + §F.7 xbrl_prefix | `T:test_pass1_corrective::test_xbrl_us_gaap_revenue_banned_K15` |
| K12-person multi-token person ban | §C 4.5 v11-2 + §F.7 identity_person | `T:test_pass1_corrective::test_person_elon_musk_guidance_banned_K12` / `test_person_tim_cook_sales_banned_K12` |
| K14 provider ban | §F.7 provider | `T:test_pass1_corrective::test_provider_benzinga_revenue_banned_K14` |
| K24 effect ban | §F.7 effect | `T:test_pass1_corrective::test_effect_stock_selloff_banned_K24` / `test_effect_selloff_revenue_banned_K24` |
| #4 multi-token OBJECT ACCEPT | §C 4.5 v11-2 freeze keeps object whole | `T:test_pass1_corrective::test_object_vision_pro_sales_accepts` / `test_object_cloud_service_revenue_accepts` |
| #5 V13 orphan-proposal scan (emission-level in `run_one`) | §E V13 proposal_without_use | `T:test_pass1_corrective::test_orphan_proposal_rejected_V13_in_run_one` (+ negative control `test_used_proposal_not_flagged_orphan_V13`) |
| K17 stopword strip (only + interior) | §C step 4 / §F.8 | `T:test_pass1_corrective::test_stopword_only_name_empty_after_strip_K17` / `test_interior_stopword_folds_out_K17` |
| K26 motion/change-noun ban (newly seeded) | §F.7/R7 motion_change | `T:test_pass1_corrective::test_motion_noun_revenue_collapse_banned_K26` / `test_motion_noun_collapse_revenue_banned_K26` / `test_motion_change_category_resolves_via_banned_category` |
| K53 same-canonical collision (emission-level `self_consistency` in `run_one`, NOT V12) | run_one collision pass | `T:test_pass1_corrective::test_same_canonical_collision_flagged_K53` (+ negative control `test_no_false_collision_distinct_canonicals_K53`) |
| bucket K multi-token-object round-trip; `us_gaap` rejects (NOT in idempotency list) | §C 4.5 v11-2 | `T:test_idempotency::test_shortcut_compound_round_trips_to_itself` (now incl. `vision_pro_sales`/`cloud_service_revenue`); `test_us_gaap_not_in_idempotency_list_because_it_rejects` |

> **V12 ≠ K53.** V12 detects duplicate proposal **NAMES** only. K53 (two raw names
> that canonicalize to the SAME driver) is a separate **self-consistency** check,
> enforced at the emission level in `run_one` (the `self_consistency` field), NOT V12.

### reuse ladder §B — B3,B4,B6,B7,B8,K50,K51,B-R1,B-M5,A2

| Item | Rung | Test |
|------|------|------|
| B3 exact name | DriverProcess Try 1 / K50 / B-R1 | `T:test_reuse::test_B3_exact_name_reuse_*` (×3) |
| B4 exact alias | Try 2 / K51 | `T:test_reuse::test_B4_exact_alias_reuse*` (×2) |
| B6 canonical-name fold + auto-alias (§D2) | Try 3 / B-M5 / doubt#16 | `T:test_reuse::test_B6_canonical_*` (×2) |
| B7 alias-of-canonical | Try 4 | `T:test_reuse::test_B7_alias_of_canonical_reuse` |
| B8 sorted-token reuse (all-known gate) | doubt#6 | `T:test_reuse::test_B8_sorted_token_reuse_all_known` |
| K50 reuse-before-propose | B-R1 / A20 | `T:test_reuse::test_reuse_is_tried_before_propose_K50` |
| PROPOSE_NEW after reuse exhausted | B9/B10 | `T:test_reuse::test_genuinely_new_concept_proposes_new` |
| A2 slug-normalize via pipeline | A1↔A2 split | `T:test_reuse::test_A2_rough_phrase_*` (×2) |

### edge cases — banned content + new-token gate + boundaries

| Item | Rule | Test |
|------|------|------|
| K7 state verb in name (B-R7a) | §C step 7 / §F.5 | `T:test_edge_cases::test_B_state_verb_cut_*` / `_lowered_guidance_lowered` |
| K10 period (B-R7e) | §F.7 period | `T:test_edge_cases::test_B_period_q3_revenue` |
| K11 numeric (B-R7f) | §F.7 numeric | `test_B_numeric_..._margin_100bps` / `test_B_leading_magnitude_fails_shape_first` |
| K12 ticker/company (B-R7d) | §F.7 identity | `test_B_ticker_aapl_*` / `test_B_company_apple_*` |
| K13 source_type (B-R7g) | §F.7 source_type | `test_B_source_type_leading_letter_*` |
| K18 durability/one-off (B-R11e) | period lever | `test_G_one_off_single_event_name_rejected_durability` |
| K19 vague descriptor (B-R7l) | §F.7 vague_descriptor | `test_B_vague_descriptor_outlook` / `_momentum` |
| K20 sentiment (B-R7j) | §F.7 sentiment | `test_B_sentiment_bullish_guidance` |
| K25 metaphor (B-R7j) | §F.7 metaphor | `test_B_metaphor_headwind_revenue` |
| K58 evidence-at-registration (B-R11c) | §D(e) / R11 | `test_G_novel_token_in_evidence_proposes_new` / `_not_in_evidence_rejects_hallucination` |
| A2/K22 split-per-variable | R2 | `test_A2_K22_two_causes_yield_two_separate_tags` |
| R8/R9 4-slot boundary accepts | §G | `test_ADV_exactly_four_effective_slots_accepts` |
| stacked-violation first-fired | §C step 7 order | `test_ADV_stacked_violations_*` / `_weak_100bps_*` |
| fold+dedup combos (R2/R3) | §C step 5/6 | `test_ADV_plural_fold_then_dedup_*` / `_dedup_leaves_single_object_no_metric` |
| doubt#11 forward_guidance vs guidance_lowered | R5 / §F.5 | `test_doubt11_forward_guidance_round_trips` / `_guidance_lowered_is_state_in_name` / `_iphone_guidance_not_mechanically_resolvable` |
| doubt#44 inferred direction | §E V9 | `test_doubt44_direction_inferred_not_rejected` |

### idempotency / determinism — bucket K (Harness §6)

| Item | Test |
|------|------|
| Shortcut/compound self round-trip (§C 4.5 freeze) | `T:test_idempotency::test_shortcut_compound_round_trips_to_itself` |
| COLD_START_SEED_DRIVERS each → itself (§J.2) | `T:test_idempotency::test_cold_start_seed_round_trips_to_itself` |
| `canonicalize(canonicalize(x))==canonicalize(x)` (B-M1, doubt#45) | `T:test_idempotency::test_canonicalize_is_idempotent_when_string` |
| §F.2/§F.3/§F.4 normalize-map keysets pairwise disjoint | `T:test_idempotency::test_normalize_map_keysets_pairwise_disjoint` |

### sequence S1→S6 — A14,A15,A22,B-M4,B-M5,doubt#43

| Item | Test |
|------|------|
| S1→S6 decision buckets (B-M4/B-M5) | `T:test_sequence::test_sequence_hand_emission_decision_buckets` |
| per-item records (§5) | `T:test_sequence::test_sequence_per_item_records` |
| A22 run_sequence == run_one | `T:test_sequence::test_sequence_equals_direct_run_one` |
| S1 catalog hand-off | `T:test_sequence::test_sequence_render_catalog_contains_seeded_names` |
| S1→S6 CALL ORDER (emit_fn seam) | `T:test_sequence::test_sequence_call_order_S1_through_S6` |
| fail-closed (no emission/emit_fn; emit_fn w/o context) | `test_sequence_requires_emission_or_emit_fn` / `_emit_fn_without_context_raises` |
| learner→writer adapter (doubt#43/A14/A15) | `T:test_sequence::test_adapter_*` (×3) |

### render_catalog — §A item 2/3, C1.1, doubt#18

| Item | Test |
|------|------|
| every name/alias/state/segment/definition present | `T:test_render_catalog::test_every_*` |
| definition field label per driver | `test_definition_label_rendered_per_driver` |
| VOCAB EXCERPT headers + SHORTCUTS (B-R5) | `test_vocab_excerpt_headers_present` / `test_shortcuts_header_and_list_present` |
| section markers + ordering | `test_catalog_and_vocab_section_markers_present` |
| doubt#18 base_label NOT leaked | `test_base_label_value_not_leaked_as_catalog_field` |
| deterministic / returns str | `test_render_is_deterministic` / `test_returns_string` |

### prod-core purity — Harness §9 / §3 / §11

| Item | Test |
|------|------|
| no prod-core module imports scaffold (AST) | `T:test_prod_core_purity::test_prod_core_module_imports_no_scaffold` |
| grep CI check (line 459) | `test_prod_core_no_substring_scaffold_import_lines` |
| all 6 prod-core modules present | `test_prod_core_modules_all_present` |
| reserved Pass-2/4 files absent | `test_reserved_pass24_file_absent` |

### COVERAGE GAPS

CREATION-scoped DETERMINISTIC items through **K60** each have a deterministic test
(the Pass-1 corrective round added the multi-token bans #3/K15 + K12-person, K14,
K17, K24, the #4 multi-token-object ACCEPT, #5 V13 orphan scan, K26 motion-noun
ban, and K53 self-consistency). We do NOT claim "everything mechanically decidable
is tested" — that overstatement masked the very gaps the independent review found
(the multi-token-ban bypass and the multi-token-object false-reject were both
mechanically decidable yet untested before v11-2). The items WITHOUT a Pass-1 test
remain the intentionally LLM-judgment ones (K23/K30/K47/K52, plus the R9 half of
K19) — deferred to Layer-2; see (b). V15 (registry-global sorted-token dedup) is
INGESTION, explicitly out of Pass-1 scope (prevented by B8 sorted-token reuse).

---

## (b) DEFERRAL — Layer-2 (Pass 4), tested with real LLM, NOT faked here

- **K23** — granularity / "is this driver at the right altitude?" is a semantic
  judgment the deterministic core cannot decide; tested in Layer-2.
- **K30** — whether two phrasings denote the *same concept* (semantic synonymy
  beyond the static §F.2 map) is LLM judgment; Layer-2.
- **K47** — definition *quality* (is the one sentence actually descriptive, not
  just well-formed) is judgment; V7 enforces only the mechanical shape; Layer-2.
- **K52** — concept-level duplicate detection across differently-spelled drivers
  (beyond exact/alias/sorted-token reuse) is judgment; Layer-2.
- **K19 split** — a *bare valid metric* (`revenue`) ACCEPTS deterministically
  (`test_canonicalize::test_E_bare_revenue_accepts`); whether a bare metric is
  *over-generic for this context* is the R9 judgment half → Layer-2.

These are NOT skipped/xfail'd in Pass 1; they simply have no deterministic test
because there is no deterministic rule to assert. `pytest -m llm` is reserved for
them in Pass 4.

---

## (c) OPEN QUESTIONS / surfaced ambiguities

1. **§F.5-vs-§F.9 `restricted` / `accumulated`.** These two tokens historically
   sat in BOTH §F.5 STATES (policy_action / quantity_move) AND §F.9
   ALLOWED_VERBAL_FORMS — a contradiction (a name token cannot be both a banned
   state and an allowed verbal form). The 2026-05-29 spec fix REMOVED them from
   §F.9 (they are states → belong in `driver_state`, banned from a NAME by
   canonicalize step 7). `vocab_seed.py` reflects the fix: `ALLOWED_VERBAL_FORMS`
   has neither token; `STATE_CLASSES` keeps both. Verified: `restricted_revenue`
   and `accumulated_inventory` both reject `state_in_name`. Surfaced in
   `validators.py` docstring + `test_validators.py` module docstring. If a tester
   re-introduces them to §F.9, V6's one-class check and the step-7 state ban will
   disagree — revisit then.

2. **CON-2 new-token-gate known set.** The §D new-token "known" set must include
   §F.6 **COMPOUND_METRICS** (lowercase name tokens like `gross_margin`), NOT
   §F.6 **CANONICAL_BASE_LABELS** (capitalized V5 values like `GrossMargin`).
   `vocab_seed.is_known_token` unions the slot vocabs (metric slot already carries
   `METRICS ∪ COMPOUND_METRICS`) + compounds explicitly; it does NOT consult
   CANONICAL_BASE_LABELS. Surfaced.

3. **verb_form ban excludes STATES (decision).** `banned_category` deliberately
   adds `STATES` to the §F.7 verb_form allowlist so a state verb
   (`lowered`/`accelerated`/`cut`) is NOT mislabeled `banned_token`/`verb_form`
   and instead falls through to the SEPARATE step-7 state check →
   `REJECTION_STATE_IN_NAME`. This keeps the rejection *reason* correct
   (`state_in_name`, not `banned_token`). Surfaced as a `# TODO(harden-in-test)`.

4. **Brief-prose vs §D.1 — bare novel token before `<metric>`.** The brief's
   bucket-G prose names bare `blackwell_revenue` as an ACCEPT, but §D.1
   `resolve_unknown_slots` fails closed: a lone UNKNOWN token before `<metric>`
   has FIVE candidate free slots → `len(free)!=1` → `slot_ambiguous` (never
   guess). The impl faithfully follows §D.1; the ACCEPT path needs a
   positionally-unique placement (`gpu_blackwell_us_revenue`). Diagnosis =
   spec(§D.1)-vs-brief-prose tension, NOT an impl bug. Documented in
   `test_edge_cases.py` module docstring +
   `test_G_bare_novel_token_before_metric_is_slot_ambiguous`. No impl edit.

5. **`iphone_guidance` is R9 granularity, not a deterministic ACCEPT.**
   `guidance` is not seeded as a metric-slot token (only the SHORTCUT
   `forward_guidance` exists), so `iphone_guidance` → `slot_ambiguous`. Whether
   product-specific guidance is acceptable is an R9 judgment → Layer-2.
   `test_doubt11_iphone_guidance_not_mechanically_resolvable`.

6. **Authorised seed additions (not verbatim §F).** FOUR additions are required by
   the brief / corrective round and surfaced in `vocab_seed.py`: (i) `eps` added to
   the metric SLOT vocab only — §F.1 METRICS verbatim lacks it though it is an §F.4
   acronym key and §F.6 base label, and the brief requires `eps` to round-trip to
   itself; (ii) `forward_guidance` appended to SHORTCUTS_VOCAB (doubt#11/F13
   seed-completeness); (iii) `BANNED_TICKERS` static seed — §F.7 tickers are
   DB-sourced, so the offline harness needs a static representative set for
   `aapl_iphone_sales → REJECT ticker`; (iv) **`motion_change` banned category
   (K26 seed, corrective round 2026-05-29)** — §F.7/R7 names "motion or change
   nouns" as a banned category but the §F.7 token block left it UNSEEDED (an empty
   category is a conformance error per the spec's line-21 rule). Seeded with
   `{collapse, surge, rebound, plunge, recovery, slump, spike, drop, jump, decline}`
   — movement nouns that describe a price/quantity MOVE, not a reusable cause; so
   `revenue_collapse` → `banned_token / motion_change`. (`rally` is omitted because
   it is already banned under `effect`; it stays banned.) Verified none collide with
   a real THEMES/OBJECTS/CUSTOMERS/GEOGRAPHIES/INSTITUTIONS/METRICS/COMPOUND_METRICS/
   STATES/SHORTCUTS/ALLOWED_VERBAL_FORMS entry. None weaken a seed fold.

---

## (d) `# TODO(harden-in-test)` aggregate

All code TODOs (Layer-2 / future hardening hooks; none mask a Pass-1 failure):

1. `validators.py:44` — F.5-vs-F.9 (`restricted`/`accumulated`): V6 currently
   treats both purely as states (post-2026-05-29 fix). Revisit if §F.9 is
   re-amended to re-add them.
2. `validators.py:216` — V7 "exactly one sentence-final punctuation" counts every
   `.!?`, so an abbreviation like "U.S." trips the count. Best first-cut: keep
   strict count, author abbreviation-free fixture definitions. Revisit if the
   spec wants abbreviation-aware segmentation.
3. `validators.py:354` (V14) — "joined evidence text": Layer-1 evidence is SRC:*
   IDs only; the §D(e) substring check uses any `evidence_text` the item carries
   (Pass-4 packets) plus the SRC IDs. Hardens when real evidence text arrives.
4. `vocab_seed.py:382` (`banned_category`) — the verb_form allowlist deliberately
   includes STATES so a state verb falls through to the separate state check.
   Revisit if a real state token is ever wrongly let through.
5. `vocab_seed.py:465` (`is_known_token`) — answers membership only for the
   V14/B-R11 known-token range; the full §D(c) positional slot inference lives in
   `canonicalize.resolve_unknown_slots`.
6. `tests/test_reuse.py:318` — the B8 all-known-tokens gate is exercised only on
   its POSITIVE side; a clean NEGATIVE demonstration (canonical succeeds + sorted
   match exists + one token NOT `_known_token`) is unreachable offline because any
   slot-unknown token makes canonicalize reject earlier. Revisit if a future seed
   admits a positionally-resolvable novel token that also sorted-matches.

---

## (e) Pass-4 note

`pytest -m llm` is **reserved for Pass 4** (real-LLM Layer-2 judgment for
K19-R9/K23/K30/K47/K52). It is excluded by default (`addopts = -m "not llm"`) and
collects 0 tests in Pass 1. The reserved Pass-2/4 files (`synonym_fold.py`,
`llm_emit.py`, `tests/test_synonym_fold.py`, `tests/test_llm_layer2.py`,
`tests/fixtures/evidence_samples.json`) are intentionally ABSENT in Pass 1.
