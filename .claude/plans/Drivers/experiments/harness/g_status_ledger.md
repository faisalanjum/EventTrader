# G1-G35 status ledger — DERIVED from `test_g_suite.py::G_COVERAGE`

Do not edit by hand: run `make_g_ledger.py` and commit the result.

| status | count | meaning |
|---|---|---|
| code | 18 | a runnable test proves it today |
| partial | 13 | one leg proven, one leg unbuilt or switch-dependent |
| grading | 2 | only hidden grading can catch it (a MEANING error) — never counted as a code proof |
| gated-switch | 2 | NOT provable until the owner-approved atomic switch |
| **total** | **35** | |

| G | status | proving pytest node id | remaining leg |
|---|---|---|---|
| G1 | code | `driver/core/test_prepared_fact_v2.py::test_G1_converter_api_fence_by_reflection` | — |
| G2 | code | `driver/core/test_prepared_fact_v2.py::test_G2_quote_and_concept_name_cannot_alter_a_value` | — |
| G3 | code | `driver/core/test_prepared_fact_v2.py::test_G3_percent_family_units_are_distinct` | — |
| G4 | code | `driver/core/test_prepared_fact_v2.py::test_G4_scale_via_model_stated_multiplier` | — |
| G5 | code | `driver/core/test_prepared_fact_v2.py::test_G5_slot_structure_failures` | — |
| G6 | code | `driver/core/test_prepared_fact_v2.py::test_G6_wrong_scale_word_elsewhere_in_the_SAME_part_still_fails` | — |
| G7 | code | `driver/core/test_prepared_fact_v2.py::test_G7_unknown_units_still_multiply` | — |
| G8 | partial | `driver/core/test_prepared_fact_v2.py::test_G8_per_x_rides_once_at_fact_level` | per_x rides once at fact level and is proven; the NAME-13 denominator check is deleted from Core with check_per_x_against_name and moves to the POST per-X naming feature; wiring into the admission kernel remains unprovable because the kernel is not built |
| G9 | gated-switch | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G9_one_shared_validation_entry_point_exists` | one shared validation entry point exists and is proven; the scorer and run_event both moving onto it IS the atomic switch |
| G10 | code | `driver/core/test_prepared_fact_v2.py::test_G10_order_free_under_full_permutation` | — |
| G11 | partial | `driver/relocation/test_packet_items_through_the_door.py::test_every_saved_packet_item_attaches_on_its_LITERAL_evidence` | re-pointed at the strongest proof: 11 saved packet items, loaded from the TRACKED wp3 packets, attach on their literal source evidence against real cached filings and live Neo4j. The remaining leg is genuinely unprovable, not merely unbuilt: the event view those quotes are checked against is scaffolding derived from each item's own quote, because the historical text the reader was actually shown was never archived. No test can recover a record that does not exist |
| G12 | code | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G12_the_live_launcher_serves_the_v2_drafter_prompt` | — |
| G13 | grading | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G13_attack_fixtures_are_registered_and_classified` | a MEANING error: only hidden grading can catch it, never a code proof |
| G14 | partial | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G14_guidance_legacy_path_is_untouched` | the legacy guidance suite is untouched; hint fields are no longer refused by a hint-specific branch — they refuse as unexpected keys at the exact-key owner; 'never a WRITER input' still needs the switched writer |
| G15 | partial | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G15_xbrl_declared_metadata_path_is_untouched` | S14: the dead declared-scale helper call removed; proves the legacy v1 XBRL suite only |
| G16 | gated-switch | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G16_old_path_removal_is_gated_on_the_switch` | old-path removal is not provable until the owner-approved atomic switch |
| G17 | code | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G17_transport_is_exact_and_refuses_ambiguity` | — |
| G18 | partial | `driver/core/test_prepared_fact_v2.py::test_G18_the_new_modules_reach_no_graph_write` | REASON RE-ADJUDICATED FROM CURRENT BYTES (Codex SEQ 1138.2). The old reason said the exam had not reached run_event; that is now FALSE — B-14 proves the replay reaches the public run_event, and the scoring seam pins enable_writes=False with a store whose transaction() REFUSES, so a write attempt during scoring raises rather than succeeding quietly. STILL partial, and this is the precise unproven leg: that covers the SCORING replay path only. 'Zero writes reachable from the EXAM' also spans the launcher and plan-bound entry points, and no single public-path test yet drives the COMPLETE exam route and shows it write-free. Not promoted on a green count or a module name |
| G19 | partial | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G19_two_rebuilds_are_byte_identical` | docs-patch determinism is proven; contract/launcher/manifest regeneration happens at the switch |
| G20 | code | `driver/core/test_prepared_fact_v2.py::test_G20_table_wide_scale_applied_once` | — |
| G21 | partial | `driver/core/test_v2_attacks.py::test_ATTACK_a_wrong_declared_scale_fails_the_certified_reconcile` | the never-double-scaled rule is proven on synthetic input; the same rule against a real Fiscal packet row is not exercised by this selector |
| G22 | partial | `driver/core/test_prepared_fact_v2.py::test_G22_the_xbrl_lane_does_not_require_quote_local_evidence` | the XBRL lane is proven; the TEXT lane's matching requirement — the other half of the rule — is not touched by this selector |
| G23 | partial | `driver/core/test_round10_event_boundary.py::test_MIXED_TYPE_keys_are_refused_cleanly_at_every_door` | an old payload now fails as an ordinary unexpected-key refusal at every door; the retired-name-specific branch and its message are deleted. Fiscal actually ceasing to emit the fields is O-f, after the boundary proof |
| G24 | grading | `driver/core/test_prepared_fact_v2.py::test_G24_membership_alone_cannot_catch_a_wrong_slot_assignment` | a MEANING error: only hidden grading can catch a wrong slot assignment (fixture A6_swapped_scale_inside_one_quote) |
| G25 | partial | `driver/core/test_prepared_fact_v2.py::test_G25_emit_once_violation_blocks_a_silent_pass` | emit-once detection is proven; the reliability gate that consumes it lives in the scorer, which moves at the switch |
| G26 | partial | `driver/core/test_prepared_fact_v2.py::test_G26_duration_and_instant_are_meaning_not_date_count` | the illegal combination is code-caught; 'a balance with a window still grades instant' is a MEANING judgment no code can prove |
| G27 | code | `driver/core/test_prepared_fact_v2.py::test_G27_a_point_is_not_a_floor` | — |
| G28 | code | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G28_source_id_echo_mismatch_is_refused` | — |
| G29 | code | `driver/core/test_prepared_fact_v2.py::test_G29_two_shape_fields_together_park` | — |
| G30 | partial | `driver/relocation/test_real_726_end_to_end.py::test_the_REAL_726_fact_binds_to_its_live_row_and_its_filing` | the consistency equation is proven on a synthetic row; despite the test's name no live Fiscal packet is loaded, so the real-packet leg and the violation case are both unproven here |
| G31 | code | `driver/core/test_prepared_fact_v2.py::test_G31_compensated_misread_can_never_grade_correct` | — |
| G32 | code | `.claude/plans/Drivers/experiments/harness/test_g_suite.py::test_G32_every_assembled_event_view_is_exactly_the_authorized_fields` | — |
| G33 | code | `driver/core/test_v2_attacks.py::test_ATTACK_an_invalid_slice_kind_is_rejected` | — |
| G34 | code | `driver/core/test_prepared_fact_v2.py::test_G34_company_confirmed_never_stores_a_guessed_false` | — |
| G35 | partial | `driver/core/test_prepared_fact_v2.py::test_G35_per_share_cell_lawfully_keeps_multiplier_one` | the per-share cell is proven; the aggregate misreading is a MEANING error only grading can catch (fixture A6-class) |
