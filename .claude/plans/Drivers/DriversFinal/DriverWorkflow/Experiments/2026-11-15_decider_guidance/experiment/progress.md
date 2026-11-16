Test: Full-call passage selection on CTAS_2026-03-25T10.00; 32 questions, local Decider, fixed source-only definition and provisional 0.25 cutoff.
Result: 10/32 passages retained; 138.06 seconds, 12,793 input tokens, one sequence. This is selection, not complete-record accuracy; exact outputs are in main_path/A_result.json.
Next: Finish candidate classification, copy required evidence, assemble/check proposals, and count failures. No word-count/ordinal repair layer.

Test: B, full-call numeric-role choices plus worded-guidance sentence checks inside the 10 retained CTAS passages.
Result: 333 questions, 744.52 seconds, 59,388 input tokens, 2 sequences; 18 numeric targets selected before probability screening and 55 worded sentence flags at 0.25. Some dates were called current values and real forecast amounts were rejected; this gate has not passed.
Next: Finish the unchanged field/assembly path on its actual selections to expose end-to-end failures; do not add a new repair layer.

Test: Independently checked all 120 numeric target offsets, 213 sentence offsets and model-visible numeric tag bindings against the original source.
Result: Zero mapping errors; each tag directly precedes the intended source token. This rules out a misplaced-tag code error, not a model interpretation error.
Next: Complete the fixed field pass, then compare tag-only wording with literal-plus-tag wording in separate matched requests.

Test: C_choices, CTAS_2026-03-25T10.00, 477 questions, frozen local isolated request.
Result: 1379.51 seconds; {'input_tokens': 113520, 'output_tokens': 0, 'sequences': 4}; error=None. Semantic accuracy still requires record review.
Next: Copy required fields for eligible targets, then copy only positive optional fields.

Test: Offline audit of numeric eligibility probabilities, combining the two eligible role classes without another model call.
Result: At 0.5, the combined probability retains 10/13 clear numeric forecast controls, including the previously dropped $101 and $11.24; three endpoints still fail. These are candidate controls, not complete records, and the running baseline was not changed.
Next: Finish the baseline, then test clearer target wording; remove the unnecessary single-class confidence gate in the next configuration if validated end to end.

Test: C_copy_prepared, CTAS_2026-03-25T10.00, 60 questions, frozen local isolated request.
Result: 68.42 seconds; {'input_tokens': 6322, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA006, CTAS_2026-03-25T10.00, 15 questions, frozen local isolated request.
Result: 16.64 seconds; {'input_tokens': 1576, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA016, CTAS_2026-03-25T10.00, 21 questions, frozen local isolated request.
Result: 21.03 seconds; {'input_tokens': 1992, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA000, CTAS_2026-03-25T10.00, 3 questions, frozen local isolated request.
Result: 8.12 seconds; {'input_tokens': 793, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA001, CTAS_2026-03-25T10.00, 9 questions, frozen local isolated request.
Result: 10.88 seconds; {'input_tokens': 1033, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA003, CTAS_2026-03-25T10.00, 6 questions, frozen local isolated request.
Result: 10.50 seconds; {'input_tokens': 1015, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA020, CTAS_2026-03-25T10.00, 9 questions, frozen local isolated request.
Result: 9.64 seconds; {'input_tokens': 917, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA022, CTAS_2026-03-25T10.00, 12 questions, frozen local isolated request.
Result: 11.72 seconds; {'input_tokens': 1120, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: D_optional, CTAS_2026-03-25T10.00, 24 questions, frozen local isolated request.
Result: 155.65 seconds; {'input_tokens': 14095, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: E, deterministic assembly of actual C/D outputs with exact mapping back to the original CTAS transcript.
Result: {"targets": 53, "statuses": {"unresolved": 49, "rejected": 4}, "reasons": {"missing_value": 37, "missing_context": 32, "positive_presence_missing_conditions": 16, "missing_measure": 19, "requires_supported_association_or_encoding_qualification": 17, "form_none": 4, "period_unclear": 4, "requires_supported_association_or_encoding_revision": 1, "form_several": 4, "period_several": 2, "time_type_unclear": 2, "positive_presence_missing_comparison_revision": 2, "requires_supported_association_or_encoding_reaffirmation": 2, "subject_scope_unclear": 1, "sign_unclear": 1}}. Field presence is not semantic correctness; independent record review is still required.
Next: Audit all proposed/rejected/held targets against source requirements, report the end-to-end outcome and select only a justified generic next fix.

Test: binding_tag_only, CTAS_2026-03-25T10.00, 25 questions, frozen local isolated request.
Result: 188.88 seconds; {'input_tokens': 17114, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: binding_literal_tag, CTAS_2026-03-25T10.00, 25 questions, frozen local isolated request.
Result: 190.26 seconds; {'input_tokens': 17283, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: C_copy_QA000_literal, CTAS_2026-03-25T10.00, 3 questions, frozen local isolated request.
Result: 9.41 seconds; {'input_tokens': 880, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA001_literal, CTAS_2026-03-25T10.00, 9 questions, frozen local isolated request.
Result: 12.78 seconds; {'input_tokens': 1222, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: Matched tag-only versus literal-plus-tag questions on the same 25 CTAS numeric controls, using separate requests.
Result: Exact role labels improved 16/25 to 25/25; literal-plus-tag retained all 10 forecast controls and rejected all 15 non-forecast controls at combined eligibility probability 0.5. Time 188.88 to 190.26 seconds; 169 extra input tokens. No complete-record claim.
Next: Apply only this binding change to the existing field-copy requests, then judge the full evidence rather than merely counting nonempty spans.

Test: C_copy_QA003_literal, CTAS_2026-03-25T10.00, 6 questions, frozen local isolated request.
Result: 12.05 seconds; {'input_tokens': 1165, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA006_literal, CTAS_2026-03-25T10.00, 15 questions, frozen local isolated request.
Result: 21.34 seconds; {'input_tokens': 1900, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA016_literal, CTAS_2026-03-25T10.00, 21 questions, frozen local isolated request.
Result: 28.23 seconds; {'input_tokens': 2427, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA020_literal, CTAS_2026-03-25T10.00, 9 questions, frozen local isolated request.
Result: 12.82 seconds; {'input_tokens': 1100, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_QA022_literal, CTAS_2026-03-25T10.00, 12 questions, frozen local isolated request.
Result: 17.93 seconds; {'input_tokens': 1549, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: C_copy_prepared_literal, CTAS_2026-03-25T10.00, 60 questions, frozen local isolated request.
Result: 89.94 seconds; {'input_tokens': 7462, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Continue the frozen copying batches; then assemble and audit complete proposals.

Test: Matched literal-plus-ID Locate copying against the prior ID-only baseline across all eight retained CTAS contexts (135 questions).
Result: 204.50 seconds; clearer target references did not repair complete copying: no revenue/EPS value in prepared remarks and zero ERP spans; some measure names and a transaction-cost range were recovered. Nonempty spans are not correct complete records.
Next: Stop further Locate prompt repairs for the repeatedly failing classes; finish the exact-number selection probe, then revise the design around prerequisites and measured results.

Test: numeric_bounds, CTAS_2026-03-25T10.00, 50 questions, frozen local isolated request.
Result: 673.80 seconds; {'input_tokens': 57046, 'output_tokens': 0, 'sequences': 2}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Independent scoring of native lower/upper choices on all 25 CTAS numeric controls, including 15 non-forecast controls.
Result: 22/25 exact endpoint pairs; six distinct positive numeric forecasts tested; 673.80 seconds, {'input_tokens': 57046, 'output_tokens': 0, 'sequences': 2}. This does not test measures, conditions or full records.
Next: Inspect every mismatch and test the same choices with shorter option rendering; retain source identity and no-match options.

Test: numeric_bounds_compact, CTAS_2026-03-25T10.00, 50 questions, frozen local isolated request.
Result: 351.47 seconds; {'input_tokens': 28752, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Same 25 bound controls with numeric option descriptions removed; literal targets and source tags retained.
Result: 22/25 exact pairs; 351.47 seconds, {'input_tokens': 28752, 'output_tokens': 0, 'sequences': 1}. Original 673.80 seconds/57,046 tokens; complete records remain untested.
Next: Move the remaining repeated task/alternative definitions into shared state once, retaining the same rules and options; measure accuracy and cost again.

Test: numeric_bounds_shared, CTAS_2026-03-25T10.00, 50 questions, frozen local isolated request.
Result: 255.82 seconds; {'input_tokens': 22248, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Same 25 bound controls with task/alternative definitions once in shared state and short literal-plus-ID questions.
Result: 25/25 exact pairs; 255.82 seconds, {'input_tokens': 22248, 'output_tokens': 0, 'sequences': 1}. Complete-record extraction remains untested for this configuration.
Next: Test the remaining typed fields on actual role-positive occurrences, preserving definitions while removing repeated wording; no new Locate repair.

Test: literal_numeric_fields, CTAS_2026-03-25T10.00, 90 questions, frozen local isolated request.
Result: 273.75 seconds; {'input_tokens': 23277, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Shared-definition field questions on all ten current numeric occurrences selected by the role model (six forecasts).
Result: 60/60 clear categorical choices correct; one selected form below 0.5. 273.75 seconds, {'input_tokens': 23277, 'output_tokens': 0, 'sequences': 1}. Conditions still missed for growth forecasts and differ between endpoints; units/basis require source evidence review. No complete-record pass.
Next: Treat each model-established value expression as a candidate before field work, retaining all source associations; test that change as a bounded comparison, not another per-endpoint repair layer.

Test: shared_role_population, CTAS_2026-03-25T10.00, 120 questions, frozen local isolated request.
Result: 255.11 seconds; {'input_tokens': 21415, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Short shared-definition role choice on all 120 numeric seeds in all ten retained passages of the fixed CTAS call.
Result: {'not_current__other': 100, 'not_current__not_retained': 99, 'current_required__current': 12, 'current_required__retained': 15, 'current_required__other': 4, 'not_current__retained': 1, 'support_role_requires_review__other': 4, 'support_role_requires_review__not_retained': 4, 'current_required__not_retained': 1}; 255.11 seconds, {'input_tokens': 21415, 'output_tokens': 0, 'sequences': 1}. Four supporting/reference amounts are separately reported; this is not full-record or all-source recall.
Next: Finish the whole-expression field comparison; reconcile measured findings and remaining failures into the strategy, without adding another repair chain.

Test: Offline uncertainty handling on the frozen 120-role outputs; do not discard a candidate without a confident negative class.
Result: {'not_current__context_only': 94, 'not_current__advance': 6, 'current_required__advance': 16, 'support_role_requires_review__context_only': 3, 'support_role_requires_review__advance': 1}. The same provisional 0.5 threshold now advances all 16 required current occurrences; no new model call, no accepted records, and four support/reference cases remain separately accounted for.
Next: Keep this as a candidate-work rule, require field evidence before any acceptance, and test its cost/recall on independent complete calls.

Test: expression_fields, CTAS_2026-03-25T10.00, 54 questions, frozen local isolated request.
Result: 231.02 seconds; {'input_tokens': 20162, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Corrected the offline routing rule to sum compatible work outcomes (current, qualification, unclear), rather than compare one negative class.
Result: {'not_current__context_only': 98, 'current_required__advance': 16, 'not_current__advance': 2, 'support_role_requires_review__context_only': 4}; all 16 required current occurrences advance, alongside two other amounts; all four separately reviewed support/reference amounts remain source context. The discarded maximum-negative rule would advance five additional candidates; four are clear extra non-current amounts and one is a supporting reference. The newly recovered 7.9 case is only just over 0.5, so this is not a validated stable threshold. No model calls or accepted records.
Next: Use this explicit work branch in the candidate procedure; retain flags and require complete field evidence before accepting anything.

Test: Same field definitions on complete source expressions from model-selected bounds; grouped only identical occurrence spans, keeping every original target alias.
Result: 90→54 questions, 273.75→231.02 seconds; 36/36 clear categorical choices correct and all above 0.5. Both growth-unit choices and two shared-condition judgments still fail. No complete records passed.
Next: Keep expression-level work as a candidate simplification, log condition/basis failures, and independently assess the new preliminary review before adding any new mechanism.

Test: shared_all_guidance_screen, CTAS_2026-03-25T10.00, 333 questions, frozen local isolated request.
Result: 343.43 seconds; {'input_tokens': 28172, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Shared definitions with one broad guidance question per retained sentence and unchanged numeric role questions in the same request (333 questions).
Result: {'not_current__context_only': 98, 'current_required__advance': 16, 'not_current__advance': 2, 'support_role_requires_review__context_only': 4}; 27/213 sentence flags at 0.5; 343.43 seconds and {'input_tokens': 28172, 'output_tokens': 0, 'sequences': 1}. Complete sentence/record gold remains unfinished; passage selection is not revalidated by this test.
Next: Score explicit positive/negative sentence controls, retain the coverage check without inventing number/sentence contradictions, then reconcile the strategy and pending review notes.

Test: Recomputed every category in the supplied draft inventory and checked unique fact IDs/source membership.
Result: 69 core and 6 borderline rows; counts saved in draft_inventory_audit.json. This is category arithmetic, not an adjudicated quote-level key.
Next: Attach exact source passages and reconcile interpretation differences before using it to score records or prioritize complete-fact fixes.

Test: unit_rule, CTAS_2026-03-25T10.00, 12 questions, frozen local isolated request.
Result: 196.47 seconds; {'input_tokens': 16998, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Explicit rule 3.33 unit choice on six forecast expressions and six actual-result positive controls, including stated yearly growth, levels and basis points.
Result: 11/12 expected units; 196.47 seconds, {'input_tokens': 16998, 'output_tokens': 0, 'sequences': 1}. Exact mismatches in unit_rule_scored.json; no full-record pass.
Next: Preserve source-evidence requirements and test any changed representation on an independently adjudicated set; do not add a keyword parser or unproved blanket unknown rule.

Test: unit_evidence, CTAS_2026-03-25T10.00, 4 questions, frozen local isolated request.
Result: 183.00 seconds; {'input_tokens': 15677, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Growth-basis evidence presence on two unstated-basis forecasts and two explicit prior-year-growth controls, using exact source quotes with the full call visible.
Result: 4/4 at 0.5; 183.0 seconds; exact probabilities and quotes in unit_evidence_scored.json. Boolean evidence presence only, not basis identification or complete extraction.
Next: Inspect any false presence or missed evidence; compare a complete evidence-based choice without adding a keyword parser or a mandatory new model round.

Test: unit_basis_choice, CTAS_2026-03-25T10.00, 4 questions, frozen local isolated request.
Result: 192.58 seconds; {'input_tokens': 16189, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: One evidence-based choice instead of yes/no, using the same four quotes, whole-call state and explicit targets.
Result: 4/4 correct top choices; 192.58 seconds; {'input_tokens': 16189, 'output_tokens': 0, 'sequences': 1}. Identifies basis or absence in one question; only yearly/absent cases checked so far.
Next: Check forecast positives and other basis classes on real-source quotes plus generic boundary mutations; do not add a separate mandatory presence round.

Test: One evidence-basis choice on eight exact real-source quotes and ten controlled boundary mutations, including actual/forecast controls, two bases, other comparisons, decoys and wider evidence.
Result: 18/18 top choices; 46.52 seconds; {'input_tokens': 4242, 'output_tokens': 0, 'sequences': 1}. Exact results and independent expected labels saved; no complete-record claim.
Next: Reconcile the smallest supported unit procedure; hold unclear/missing stated evidence, apply current rules only, and retain real/constructed test counts separately.

Test: measure_pointer, CTAS_2026-03-25T10.00, 15 questions, frozen local isolated request.
Result: 220.20 seconds; {'input_tokens': 19398, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Full-call choice of a source naming sentence for all retained numeric work targets (six identical-bound expressions grouped) plus one already-selected worded qualifier. No known names in input.
Result: 11/15 choices match independently identified naming sentences; 220.20 seconds. Any alternate evidence needs review; no field-copying or complete-record result yet.
Next: Run one fixed short Locate on the selected naming sentence plus target sentence; preserve exact maps and inspect wrong or missing names without another repair chain.

Test: measure_local_F0, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.61 seconds; {'input_tokens': 192, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_F1, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.20 seconds; {'input_tokens': 189, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_F2, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.18 seconds; {'input_tokens': 187, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_F3, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.19 seconds; {'input_tokens': 189, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_F4, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.67 seconds; {'input_tokens': 218, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_F5, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.59 seconds; {'input_tokens': 218, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_V53, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.26 seconds; {'input_tokens': 170, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_V65, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.20 seconds; {'input_tokens': 180, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_V66, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.19 seconds; {'input_tokens': 180, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_V90, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.16 seconds; {'input_tokens': 163, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_V91, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.17 seconds; {'input_tokens': 163, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_V103, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 1.82 seconds; {'input_tokens': 160, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_V108, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.17 seconds; {'input_tokens': 167, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_V109, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.18 seconds; {'input_tokens': 167, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: measure_local_S212, CTAS_2026-03-25T10.00, 1 questions, frozen local isolated request.
Result: 2.90 seconds; {'input_tokens': 242, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Existing full unit-choice options on the same 12 source controls, with explicit quoted evidence instead of undifferentiated whole-call state; no added basis/presence question.
Result: 32.81 seconds; {'input_tokens': 2867, 'output_tokens': 0, 'sequences': 1}; raw choices saved in unit_quote_result.json, semantic scoring follows.
Next: Compare against the independently saved unit key, then keep only the smallest evidenced change; quote completeness remains a separate prerequisite.

Test: One fixed sentence-pointer→short-Locate procedure, including all advanced numeric work targets and one already-selected worded qualifier; exact source mapping checked.
Result: naming pointers 11/15; short Locate 34.51s and 12/15 nonempty, but two >0.99 spans were not measure names and several other fields lacked meaning-changing wording or included periods. No complete records. Details in measure_local_reviewed.json.
Next: Keep this proposal unresolved; retain the useful short-context copying observation, but do not stack another measure-repair layer. Finish the bounded unit integration check and reconcile the draft.

Test: Score the quote-grounded existing unit choice against the prior independent 12-control unit key.
Result: 12/12 correct top choices, 32.81s and 2867 tokens; earlier whole-call configuration was 11/12, 196.47s and 16,998 tokens. This changes evidence framing and context, not merely runtime speed.
Next: Keep one evidence-grounded unit choice as the smallest candidate; no separate mandatory presence/basis question. Complete quote construction and full-record testing remain required.

Test: Final evidence-file and scope audit for growth-unit and sentence-pointer experiments.
Result: Saved JSON parses; 12/12 unit and 18/18 basis top-choice totals verified; all returned measure spans map exactly, despite semantic failures; all 66 review IDs retained; main strategy SHA-256 unchanged. No production, runtime, rulebook or database writes.
Next: Reconcile the complete review and unresolved measure/condition/worded paths before applying the strategy; no claim that complete extraction has passed.

Test: support_sentence, CTAS_2026-03-25T10.00, 108 questions, frozen local isolated request.
Result: 214.53 seconds; {'input_tokens': 18066, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic accuracy still requires record review.
Next: Assemble source-backed proposals and audit missing/incorrect fields; no repair loop.

Test: Association between four annual forecast expressions and all 27 retained guidance sentences; supports assumptions/exclusions, not final field assignment.
Result: 86/88 definite relation labels correct; 12/12 definite positives found; 2 false positives; 20 pairs remain unadjudicated; 214.53s. No full-record result.
Next: Inspect missed links and ambiguous source scope; separate measurement qualifiers from assumptions, and keep only demonstrated gains without a repair chain.

Test: Existing unit choice on four continuous quotes assembled from actual support-sentence selections plus target sentences.
Result: 74.56s; {'input_tokens': 7083, 'output_tokens': 0, 'sequences': 1}; raw answers saved. These quotes are not yet certified complete for every field.
Next: Compare with the independent same-unit reference and inspect any borrowed comparison basis before promoting the unit result beyond short-quote controls.

Test: Score units on the actual expanded support quotes against the unchanged independent unit key.
Result: 3/4 correct; 74.56s; detailed mismatch/probabilities in unit_assembled_quote_scored.json. A short-quote component pass does not establish the automatic evidence pipeline.
Next: Preserve the integration failure and its exact inputs; do not promote quote-grounded units as solved or add an unmeasured field-repair loop.

Test: Identical unit questions on identical selected evidence sentences, omitting only intervening source gaps from inference while preserving the full original quote separately.
Result: 19.48s; {'input_tokens': 1762, 'output_tokens': 0, 'sequences': 1}; raw answers saved in unit_selected_evidence_result.json.
Next: Score unchanged unit controls and source mappings; no extra model gate or automatic completeness claim.

Test: Score selected-evidence unit inference and verify every source slice plus the unchanged continuous saved quote.
Result: 4/4 correct; 19.48s / 1762 tokens, versus 3/4 / 74.56s / 7,083 tokens with gaps included. All original quote/slice checks passed. No complete-record pass.
Next: Review the newly supplied nine-point final review one item at a time; establish source-backed expected records before another narrowly selected model probe.

Test: Source-only annotation pass on all 36 prepared/Q&A passages of CTAS 2025-09-24; exact evidence intervals checked mechanically.
Result: 15 claim/interpretation entries with passage coverage and source-backed fields; this includes ambiguities, not 15 certified records. No model calls, blind-pass claim or complete gold-key claim.
Next: Compare the independent source reading with the supplied draft/legacy records, expose disagreements, then continue the remaining five source reads before new model tuning.

Test: Source-first reference reading of every passage in CTAS_2025-12-18T10.00, under the current Driver rulebook.
Result: 28 passages accounted for; 17 claim/interpretation entries with exact source locations; no complete-gold or independent-blind claim.
Next: Compare legacy/draft inventories only after this source pass, adjudicate differences and finish the remaining calls before further narrow model tuning.

Test: Source-first reference reading of every passage in PAYX_2025-09-30T09.30, under the current Driver rulebook.
Result: 23 passages accounted for; 18 claim/interpretation entries with exact source locations; no complete-gold or independent-blind claim.
Next: Compare legacy/draft inventories only after this source pass, adjudicate differences and finish the remaining calls before further narrow model tuning.

Test: Source-first reference reading of every passage in PAYX_2025-12-19T09.30, under the current Driver rulebook.
Result: 29 passages accounted for; 15 claim/interpretation entries with exact source locations; no complete-gold or independent-blind claim.
Next: Compare legacy/draft inventories only after this source pass, adjudicate differences and finish the remaining calls before further narrow model tuning.

Test: Source-first reference reading of every passage in PAYX_2026-03-25T09.30, under the current Driver rulebook.
Result: 38 passages accounted for; 19 claim/interpretation entries with exact source locations; no complete-gold or independent-blind claim.
Next: Compare legacy/draft inventories only after this source pass, adjudicate differences and finish the remaining calls before further narrow model tuning.

Test: Source-first reference reading of every passage in CTAS_2026-03-25T10.00, under the current Driver rulebook.
Result: 32 passages accounted for; 18 claim/interpretation entries with exact source locations; no complete-gold or independent-blind claim.
Next: Compare legacy/draft inventories only after this source pass, adjudicate differences and finish the remaining calls before further narrow model tuning.

Test: Validate six source-first inventories against frozen transcript hashes and every exact evidence location.
Result: Six calls, 186 passages and 102 claim/interpretation entries checked; all evidence slices exact, all entries explicitly non-gold. No completeness or extraction score inferred from this count.
Next: Reconcile meaningful reference differences and assess final-review suggestions against current rules and measured outputs; old schema is not the answer key.

Test: Independently audit final-review item 8 against frozen B/C/E code and all 333 source targets.
Result: {"targets": 333, "outcomes": {"not_selected_by_B": 260, "unresolved": 49, "not_advanced_to_C": 20, "rejected": 4}, "not_advanced_reasons": {"selected_numeric_role_probability_below_0.5": 2, "sentence_probability_0.25_to_below_0.5": 18}, "no_copy_but_recorded": [{"tag": "V58", "form": "none", "outcome": "rejected"}, {"tag": "S14", "form": "several", "outcome": "unresolved"}, {"tag": "S15", "form": "several", "outcome": "unresolved"}, {"tag": "S68", "form": "none", "outcome": "rejected"}, {"tag": "S71", "form": "several", "outcome": "unresolved"}, {"tag": "S76", "form": "none", "outcome": "rejected"}, {"tag": "S183", "form": "several", "outcome": "unresolved"}, {"tag": "S191", "form": "none", "outcome": "rejected"}]}. No new model calls or baseline changes; this is accounting, not extraction recall.
Next: Accept explicit outcomes for earlier filtering, but correct the claim that several/form rejects vanish: E already records all C targets.

Test: Final reference-location recheck plus exact request inspection for the quote-grounded unit claims.
Result: 186 passages/102 entries/196 evidence references exact; reviewer identity corrected to root agent, not human. Unit requests share evidence blocks in one state, so per-record hard isolation and its timing remain untested. Main strategy and rulebook hashes unchanged.
Next: Use final_review_assessment.md and the current-rule source reference to test one coherent procedure; do not replace missing extraction with legacy-schema agreement.

Test: Seven existing choice fields on six model-selected expressions with reviewed source evidence; shared quote-block state, not automatic evidence discovery.
Result: 40/42 field choices; 140.02s; {'input_tokens': 9422, 'output_tokens': 0, 'sequences': 1}; status=scored_fields_only. Complete records not tested.
Next: Inspect wrong choices and evidence contamination; reuse only demonstrated simplifications, with incomplete extraction still counted.

Test: Clarify duration versus instant by quantity meaning; retain all 42 prior field questions and add six paired/negative semantic controls.
Result: 48/48 field choices; 119.81s; {'input_tokens': 10084, 'output_tokens': 0, 'sequences': 1}; error=None. This is not complete extraction.
Next: Keep only a measured generic wording improvement; check other fields and do not infer full-record readiness.

Test: Clarify duration versus instant by quantity meaning; retain all 42 prior field questions with 0 additional paired/negative semantic controls.
Result: 42/42 field choices; 112.08s; {'input_tokens': 9516, 'output_tokens': 0, 'sequences': 1}; error=None. This is not complete extraction.
Next: Keep only a measured generic wording improvement; check other fields and do not infer full-record readiness.

Test: Challenge evidence-first complexity with the same seven fields/six source expressions, whole-call context and clarified time/unit definitions; no manually selected evidence supplied.
Result: 40/42 field choices; 221.03s; {'input_tokens': 19803, 'output_tokens': 0, 'sequences': 1}; error=None. Full records and proof selection not tested.
Next: Compare correctness and total stage cost before choosing evidence-first or whole-call field input; keep failed classes explicit.

Test: Integrate an explicit growth-basis choice into the same full-call choice batch: six field targets plus two real positive controls, no reviewed excerpts supplied.
Result: 48/50 raw choices; 42/42 original fields after the narrow 3.33 absence rule; 232.90s; {'input_tokens': 20621, 'output_tokens': 0, 'sequences': 1}; error=None. Not full records.
Next: Inspect failures and total stage cost before retaining an extra judgment; do not turn prototype conflict handling into a production normalizer.

Test: Assemble six prior field targets from actual saved numeric bounds, measure pointers/copies, support associations and whole-call choices; verify all source locations.
Result: Six partial proposals with exact quotes and input hashes; zero complete accepts claimed. Mixed configurations are explicit; no reference labels or legacy rows supplied as fields.
Next: Audit actual assembled records under the current rulebook, distinguishing missing meaning from deferred canonical naming and redundant copying.

Test: Complete prepared-section evidence, six saved numeric targets; existing fields plus amount meaning, baseline, modifiers and assumptions. No new discovery or measure repair.
Result: 237.47s; {'input_tokens': 18226, 'output_tokens': 0, 'sequences': 2}; error=None. Semantic review pending; not a complete extraction pass.
Next: Map returned copies to source and review complete target meanings; keep failures explicit instead of adding repair layers.

Test: Reconstruct complete-prepared-block field outputs and compare choices with the frozen six-target reference.
Result: 56/60 raw choices; 58 after the existing absence rule; 0 copied spans, 0 outside source. Full-record semantic review pending.
Next: Review all copied conditions/qualifiers and whole proposals; field counts are not a readiness score.

Test: Matched prepared-block request; replace only 12 indirect Locate task-name references with explicit generic extraction labels.
Result: 209.41s; {'input_tokens': 18412, 'output_tokens': 0, 'sequences': 2}; error=None. Source, choice questions and grouping unchanged; copying requires review.
Next: Compare exact returned spans and complete meanings; keep only demonstrated improvements and stop bounded field-copy repairs.

Test: Reconstruct label_check_complete-prepared-block field outputs and compare choices with the frozen six-target reference.
Result: 56/60 raw choices; 58 after the existing absence rule; 4 copied spans, 0 outside source. Full-record semantic review pending.
Next: Review all copied conditions/qualifiers and whole proposals; field counts are not a readiness score.

Test: Third bounded copy configuration: same explicit labels on the union of actual prior model-selected evidence sentences; no manual excerpts or new selection calls.
Result: 13.58s; {'input_tokens': 1124, 'output_tokens': 0, 'sequences': 1}; error=None; 5 copied spans. Source/semantic review still required.
Next: Review required meanings; record remaining copying failures and stop this repair chain. No complete-extraction claim.

Test: Normalize all six actual numeric proposals with native strict Babel parsing and the existing exact-scaling helper; check source copies and all observed six-source digit tokens.
Result: Six exact numeric proposals; 1050 observed tokens accounted for: {'unsupported_literal': 497, 'lexically_parseable': 553}. Wrapper tests passed after the initial missing-helper failure. Semantic acceptance remains unset.
Next: Complete the source-based proposal review and record copying gaps; no parser expansion or further copy repair loop.

Test: Review all six normalized proposals under the current rulebook after three bounded field-copy configurations.
Result: Four proposals remain incomplete; two contain the required source-claim content but await independent review/calibration. Zero runtime accepts; no full-transcript recall or coherent-pipeline score. Missing assumptions are present in the copy input, so this is not merely absent context.
Next: Stop O4 copying repairs and reconcile the complete procedure/open cases; preserve current-rule grading and do not tune these six examples further.

Test: Read-only live audit of metadata-only candidate exclusion across the entire standard transcript cohort, using existing native header recognition and each source's speaker metadata.
Result: {'prepared': 9167, 'qa': 9167}; {'prepared': {'blocks': 9167, 'utterances': 57261, 'verified_header': 57257, 'numeric_questions_before': 1042246, 'numeric_questions_after': 984964, 'question_reduction': 57282, 'body_digits_preserved': 2459555, 'header_name_not_in_metadata': 4}, 'qa': {'blocks': 160778, 'utterances': 384582, 'verified_header': 384507, 'numeric_questions_before': 936722, 'numeric_questions_after': 552158, 'question_reduction': 384564, 'body_digits_preserved': 1220653, 'header_name_not_in_metadata': 75}}; all retained source offsets/body digits exact, every unverified header keeps original candidates. No model calls.
Next: Retain only the measured structural simplification; changed model grouping still needs validation in the final procedure, and semantic extraction gaps remain open.

Test: Reconcile full-cohort metadata-filter counts, preserve all exception identifiers, and pin the native formatter/matcher plus adapter hashes.
Result: 441,843 utterances across 9,167 transcripts; 441,764 verified headers, 79 unchanged unmatched headers; 1,978,968 to 1,537,122 numeric questions (22.33% fewer). Complete stored-speech digit coverage and offsets passed; no model calls or latency/accuracy claim.
Next: Use this as a preparation component in the coherent procedure; changed question grouping still needs model validation, and O1–O4 extraction failures remain open.

Test: Freeze uniform whole-call passage requests and source-derived labels for all six development calls.
Result: 186 passages; {'positive': 57, 'negative': 118, 'unadjudicated': 11}; exact source hashes and complete passage membership verified. No answers used to build this request or labels.
Next: Run the frozen local requests once, then score raw probabilities and report uncertainty without retuning the wording.

Test: Frozen six-call passage detector: CTAS_2025-09-24T10.00, 36 questions, unchanged complete source.
Result: 178.67s; usage={'input_tokens': 13394, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic scoring still pending.
Next: Finish the frozen requests, then reconcile every passage; no copy/measure repair loop.

Test: Frozen six-call passage detector: CTAS_2025-12-18T10.00, 28 questions, unchanged complete source.
Result: 133.49s; usage={'input_tokens': 12575, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic scoring still pending.
Next: Finish the frozen requests, then reconcile every passage; no copy/measure repair loop.

Test: Inspect and exercise the existing period resolver through its public API, without ticker lookups; exact dates, month-calendar controls, leap day, instant and missing-data refusals.
Result: Seven controls passed; exact week-based dates preserved and missing required information refused. Native month math is explicitly not a verified calendar source. No new resolver or production changes.
Next: Reuse native exact-date handling where independently verified source dates exist; keep calendar acquisition and lookup-order compatibility explicit in the procedure review.

Test: Frozen six-call passage detector: PAYX_2025-09-30T09.30, 23 questions, unchanged complete source.
Result: 129.56s; usage={'input_tokens': 12249, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic scoring still pending.
Next: Finish the frozen requests, then reconcile every passage; no copy/measure repair loop.

Test: Frozen six-call passage detector: PAYX_2025-12-19T09.30, 29 questions, unchanged complete source.
Result: 158.64s; usage={'input_tokens': 14699, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic scoring still pending.
Next: Finish the frozen requests, then reconcile every passage; no copy/measure repair loop.

Test: Frozen six-call passage detector: PAYX_2026-03-25T09.30, 38 questions, unchanged complete source.
Result: 200.33s; usage={'input_tokens': 17800, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic scoring still pending.
Next: Finish the frozen requests, then reconcile every passage; no copy/measure repair loop.

Test: Frozen six-call passage detector: CTAS_2026-03-25T10.00, 32 questions, unchanged complete source.
Result: 136.21s; usage={'input_tokens': 12807, 'output_tokens': 0, 'sequences': 1}; error=None. Semantic scoring still pending.
Next: Finish the frozen requests, then reconcile every passage; no copy/measure repair loop.

Test: Prepare a generic utterance-targeted comparison using stored prepared blocks and Q&A entries, without text heuristics.
Result: All six frozen sources reconstruct exactly; 363 targets replace 186 passage targets. No model calls during preparation.
Next: Test one complete call with observed passage-screen misses, using identical wording and no answer-key input; compare both coverage and cost.

Test: Score the frozen six-call passage detector against the source-derived development labels and inspect its low-scoring positive passages.
Result: All 186 passages accounted for; at .5, 48/57 positives retained; at .25, 52/57. 11 reference cases remain unadjudicated. Total 936.90s, 83,524 tokens, six sequences. Presence counts are not fact recall; negative-label disagreements still need review.
Next: Test existing-utterance targeting with identical wording and full context on a complete call; preserve filtered context in later evidence choices and do not tune a cutoff to these examples.

Test: Whole-call guidance screen, one unchanged question per stored utterance: PAYX_2026-03-25T09.30, 73 questions.
Result: 230.31s; usage={'input_tokens': 20268, 'output_tokens': 0, 'sequences': 1}; error=None. Source-based scoring follows.
Next: Compare retained known claims and extra passages with the frozen passage run. Do not adopt from a single call or change the prompt to fit its misses.

Test: Compare passage vs existing-utterance guidance targeting on PAYX_2026-03-25T09.30, using the frozen source-derived labels.
Result: {'0.5': {'passages': {'tp': 9, 'fn': 3, 'fp': 0, 'tn': 23, 'unadjudicated_retained': 1, 'unadjudicated_filtered': 2}, 'turns': {'tp': 8, 'fn': 4, 'fp': 0, 'tn': 23, 'unadjudicated_retained': 2, 'unadjudicated_filtered': 1}}, '0.25': {'passages': {'tp': 9, 'fn': 3, 'fp': 2, 'tn': 21, 'unadjudicated_retained': 2, 'unadjudicated_filtered': 1}, 'turns': {'tp': 9, 'fn': 3, 'fp': 1, 'tn': 22, 'unadjudicated_retained': 2, 'unadjudicated_filtered': 1}}}; timings={'passages_seconds': 200.33114540902898, 'turns_seconds': 230.31093742488883}; usage={'passages': {'input_tokens': 17800, 'output_tokens': 0, 'sequences': 1}, 'turns': {'input_tokens': 20268, 'output_tokens': 0, 'sequences': 1}}. Parent retention only; complete records and semantic error review remain separate.
Next: Inspect changed classifications against source before retaining or rejecting this structural alternative; no prompt repair or cutoff tuning.

Test: Inspect the utterance-screen changes against the complete PAYX March source and the frozen passage comparison.
Result: No coverage gain at .25 (9/12 positive-labelled passages for both); worse at .5 (8/12 versus 9/12), 230.31s versus 200.33s. Same three low-score contexts remained. Reference ambiguities stay explicit.
Next: Reject the utterance replacement; compare direct sentence targeting with unchanged whole-call context and the native segmenter. No further copying/measure repair, company wording or cutoff fitting.

Test: Prepare whole-call sentence targeting for PAYX_2026-03-25T09.30 using native pysbd exact spans.
Result: 673 sentence targets, all 38 passages and every non-whitespace source character accounted for. Shared task instructions avoid repeated long questions. No model calls.
Next: Freeze quote-level source controls separately, then run once and compare actual relevant statements as well as parent-passage retention.

Test: Freeze exact source-level sentence controls for the complete PAYX March sentence screen before inference.
Result: 30 controls: 22 forecast/confirmation/qualifier carriers and eight actual/boilerplate/schedule negatives; every quote and native sentence mapping checked. This is a development reference, not complete gold.
Next: Run the whole 673-sentence source and score these controls plus all selected sentences; no expected text or values enter requests.

Test: Whole-call direct sentence screening: PAYX_2026-03-25T09.30, 673 questions, no coarse filter.
Result: 729.94s; usage={'input_tokens': 60073, 'output_tokens': 0, 'sequences': 2}; error=None. Complete semantic scoring still pending.
Next: Check frozen source controls and every selected sentence; compare cost/coverage without tuning the threshold or adding a repair layer.

Test: Score all 673 sentence responses for PAYX_2026-03-25T09.30, verifying frozen hashes, exact text and complete answer coverage.
Result: {'0.5': {'controls': {'tp': 19, 'fn': 3, 'fp': 0, 'tn': 8, 'unadjudicated_retained': 0, 'unadjudicated_filtered': 0}, 'sentences_selected': 43, 'parents_from_sentences': {'tp': 9, 'fn': 3, 'fp': 4, 'tn': 19, 'unadjudicated_retained': 2, 'unadjudicated_filtered': 1}, 'parent_baseline': {'tp': 9, 'fn': 3, 'fp': 0, 'tn': 23, 'unadjudicated_retained': 1, 'unadjudicated_filtered': 2}}, '0.25': {'controls': {'tp': 21, 'fn': 1, 'fp': 0, 'tn': 8, 'unadjudicated_retained': 0, 'unadjudicated_filtered': 0}, 'sentences_selected': 104, 'parents_from_sentences': {'tp': 12, 'fn': 0, 'fp': 7, 'tn': 16, 'unadjudicated_retained': 2, 'unadjudicated_filtered': 1}, 'parent_baseline': {'tp': 9, 'fn': 3, 'fp': 2, 'tn': 21, 'unadjudicated_retained': 2, 'unadjudicated_filtered': 1}}}; 729.94s, usage={'input_tokens': 60073, 'output_tokens': 0, 'sequences': 2}. Controls are development labels, not distinct-fact recall.
Next: Review each selected sentence and all control misses; record limitations without a fourth screening repair or fitted cutoff.

Test: Review every one of the 104 selected sentence targets against source, keeping ambiguous statements and supporting context separate from current forecasts.
Result: At .25, 21/22 positive controls and 8/8 negative controls were correct, yet other actual results were selected. All 12 positive-labelled parents were retained while the S483 margin exclusion was missed. Post-result review: 36 guidance-related, 49 context/past, 19 ambiguous; not a gold precision or fact count. Cost 729.94s, 60,073 tokens, two sequences.
Next: Preserve this bounded comparison and its open screening limitation; no further prompt/cutoff repair on these examples. Reconcile complete-record requirements and the four open extraction classes before updating the main strategy.

Test: Read-only calendar ownership and annual-filing metadata checks before replacing the two-company period menu; inspected native resolver and cache APIs.
Result: All 9,167 selected transcripts have one INFLUENCES company, across 789 companies. Stored company FYE can disagree with annual filing endpoints (COST month 11 versus Aug/Sep endings; WMT month 4 versus Jan endings). The first Redis PING timed out; no cache result is claimed and no service was changed.
Next: Check the project Redis endpoint, audit the finite cohort against available calendar evidence, and exercise the native exact-date path instead of adding calendar math.

Test: Finish the read-only calendar check over every selected-cohort company and exercise native conflicting-lookup/exact-date controls.
Result: {"companies": 789, "transcripts": 9167, "counts": {"month_matches_all_observed_end_months": 663, "month_matches_no_observed_end_months": 80, "month_matches_some_observed_end_months": 45, "no_readable_annual_metadata": 1}, "companies_with_non_month_end_annuals": 124}; source-exact native path wins, default lookup takes existing before SEC. Both Redis PING checks timed out; no cache accuracy/availability claim.
Next: Freeze the bounded six-call procedure and explicit calendar hold; run once, report complete/held/missed against the development reference, then wait for owner.

Test: Freeze the combined six-call procedure and inspect four mechanical source-mapping controls before the single run.
Result: Four preparation/copy/configuration controls passed; code and inputs frozen at 19:51:51 EST. These are mechanical checks, not extraction accuracy.
Next: Complete this run, review actual claim outcomes, write the owner memo and stop.

Test: Inspect the first frozen input against the metadata-exclusion helper while inference is running.
Result: sources.json lacks meta.speakers; the helper conservatively keeps timestamp numbers. No speech digits are lost, but exclusion proven on raw structured data is not active on these saved inputs.
Next: Keep the frozen run unchanged; disclose extra numeric work and do not claim the combined preparation is fully integrated.

Test: Frozen six-call run CTAS_2025-09-24T10.00/01_scan, 704 questions.
Result: 934.22s; usage={'input_tokens': 74925, 'output_tokens': 0, 'sequences': 3}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-09-24T10.00/02_bounds, 18 questions.
Result: 210.44s; usage={'input_tokens': 18990, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-09-24T10.00/03_fields, 60 questions.
Result: 268.53s; usage={'input_tokens': 23380, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-09-24T10.00/04_copy_prepared_0, 12 questions.
Result: 49.56s; usage={'input_tokens': 3887, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-09-24T10.00/04_copy_QA026_0, 3 questions.
Result: 10.43s; usage={'input_tokens': 826, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-09-24T10.00/05_optional_0, 4 questions.
Result: 170.58s; usage={'input_tokens': 15503, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call assembly CTAS_2025-09-24T10.00.
Result: 5 numeric proposals; {'held': 4, 'needs_source_review': 1}; all sentence/number routing outcomes retained. No correctness claim before source review.
Next: Continue the same procedure on remaining calls, then report complete/held/missed and stop.

Test: Review all five numeric proposals from the first frozen call against source and map all 12 confirmed reference claims to their actual carrier statements.
Result: CTAS September: 0 complete, 12 held, 0 missed; four numeric proposals have automatic holds and semantic errors, while one cleared automatic holds but has unsupported FY2026 and a quote omitting horizon/reaffirmation. No output was repaired or accepted.
Next: Keep the remaining five calls unchanged, grade their saved outputs, finish the one-page memo and wait.

Test: Frozen six-call run CTAS_2025-12-18T10.00/01_scan, 716 questions.
Result: 876.52s; usage={'input_tokens': 74907, 'output_tokens': 0, 'sequences': 3}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-12-18T10.00/02_bounds, 32 questions.
Result: 234.07s; usage={'input_tokens': 20775, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-12-18T10.00/03_fields, 96 questions.
Result: 310.36s; usage={'input_tokens': 26320, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-12-18T10.00/04_copy_prepared_0, 12 questions.
Result: 52.71s; usage={'input_tokens': 4103, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-12-18T10.00/04_copy_QA003_0, 6 questions.
Result: 23.95s; usage={'input_tokens': 1891, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-12-18T10.00/04_copy_QA010_0, 3 questions.
Result: 10.33s; usage={'input_tokens': 804, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-12-18T10.00/04_copy_QA012_0, 3 questions.
Result: 13.11s; usage={'input_tokens': 1046, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2025-12-18T10.00/05_optional_0, 8 questions.
Result: 170.87s; usage={'input_tokens': 15485, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call assembly CTAS_2025-12-18T10.00.
Result: 8 numeric proposals; {'held': 8}; all sentence/number routing outcomes retained. No correctness claim before source review.
Next: Continue the same procedure on remaining calls, then report complete/held/missed and stop.

Test: Review all eight numeric proposals from frozen CTAS December and every one of its 14 confirmed reference claims.
Result: 0 complete, 14 held, 0 missed; all eight proposals already have automatic holds. One proposal repeats the revenue-growth claim. Exact values often survive, but missing measure/period/qualifier evidence and range-form errors prevent complete records.
Next: Continue the same run on the four remaining calls; no repair or rerun, then finalize memo and stop.

Test: Frozen six-call run PAYX_2025-09-30T09.30/01_scan, 634 questions.
Result: 663.58s; usage={'input_tokens': 55349, 'output_tokens': 0, 'sequences': 2}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-09-30T09.30/02_bounds, 38 questions.
Result: 346.63s; usage={'input_tokens': 29134, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-09-30T09.30/03_fields, 144 questions.
Result: 360.55s; usage={'input_tokens': 29901, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-09-30T09.30/04_copy_prepared_0, 33 questions.
Result: 71.70s; usage={'input_tokens': 5512, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-09-30T09.30/04_copy_QA005_0, 3 questions.
Result: 14.04s; usage={'input_tokens': 1114, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-09-30T09.30/05_optional_0, 10 questions.
Result: 166.16s; usage={'input_tokens': 15082, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call assembly PAYX_2025-09-30T09.30.
Result: 12 numeric proposals; {'held': 12}; all sentence/number routing outcomes retained. No correctness claim before source review.
Next: Continue the same procedure on remaining calls, then report complete/held/missed and stop.

Test: Review all 12 numeric proposals from frozen Paychex September and all 14 confirmed reference claims.
Result: Frozen procedure: 0 complete releases, 14 held, 0 missed. P1-07/V056 has complete source-backed fields and quote but is unnecessarily held solely for an empty redundant context copy. Other proposals have concrete missing measure, target period, scale or comparison evidence; no output was repaired.
Next: Keep the correct-content false hold separate from real extraction failures; finish the remaining three calls, finalize memo and stop.

Test: Frozen six-call run PAYX_2025-12-19T09.30/01_scan, 738 questions.
Result: 971.86s; usage={'input_tokens': 81770, 'output_tokens': 0, 'sequences': 3}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-12-19T09.30/02_bounds, 20 questions.
Result: 256.89s; usage={'input_tokens': 22495, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-12-19T09.30/03_fields, 96 questions.
Result: 339.70s; usage={'input_tokens': 28444, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-12-19T09.30/04_copy_prepared_0, 15 questions.
Result: 57.94s; usage={'input_tokens': 4514, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-12-19T09.30/04_copy_QA000_0, 3 questions.
Result: 19.48s; usage={'input_tokens': 1552, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-12-19T09.30/04_copy_QA018_0, 3 questions.
Result: 11.11s; usage={'input_tokens': 866, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-12-19T09.30/04_copy_QA020_0, 3 questions.
Result: 8.39s; usage={'input_tokens': 662, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2025-12-19T09.30/05_optional_0, 2 questions.
Result: 192.76s; usage={'input_tokens': 17350, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call assembly PAYX_2025-12-19T09.30.
Result: 8 numeric proposals; {'held': 8}; all sentence/number routing outcomes retained. No correctness claim before source review.
Next: Continue the same procedure on remaining calls, then report complete/held/missed and stop.

Test: 2026-11-15 21:55:21 EST — source review of fourth frozen call, Paychex 2025-12-19; no further inference.
Result: all 12 confirmed claim carriers retained; all eight numeric proposals held, including one with complete source content blocked only by the confidence gate; two repeats excluded from distinct-claim counts.
Next: finish the existing fifth and sixth calls, review their saved outputs, then finalize memo and stop.

Test: Frozen six-call run PAYX_2026-03-25T09.30/01_scan, 896 questions.
Result: 1669.69s; usage={'input_tokens': 141128, 'output_tokens': 0, 'sequences': 5}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: 2026-11-15 22:14:11 EST — check actual claim sentences/numeric occurrences in the fifth frozen call’s completed screen.
Result: all 13 confirmed Paychex March claims have retained carriers; 86 sentences and five numeric occurrences are held, eight numbers advance. Source-selected wording is not yet a complete record.
Next: await unchanged numeric stages and review final outputs; sixth call follows automatically.

Test: Frozen six-call run PAYX_2026-03-25T09.30/02_bounds, 16 questions.
Result: 295.55s; usage={'input_tokens': 25461, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2026-03-25T09.30/03_fields, 48 questions.
Result: 326.84s; usage={'input_tokens': 27730, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2026-03-25T09.30/04_copy_prepared_0, 9 questions.
Result: 58.92s; usage={'input_tokens': 4622, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run PAYX_2026-03-25T09.30/04_copy_QA000_0, 3 questions.
Result: 13.54s; usage={'input_tokens': 1058, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call assembly PAYX_2026-03-25T09.30.
Result: 4 numeric proposals; {'held': 4}; all sentence/number routing outcomes retained. No correctness claim before source review.
Next: Continue the same procedure on remaining calls, then report complete/held/missed and stop.

Test: 2026-11-15 22:27:19 EST — source review of all four final numeric proposals from frozen Paychex March.
Result: 0 complete under frozen checks, 13 held, 0 missed across confirmed claims. Three proposals have concrete field/evidence omissions; the H2 organic-growth quote is adequate for core fields but its headline-comparison interpretation remains unsettled. No output was repaired.
Next: finish the already-running final Cintas call, review it, finalize one-page memo and stop.

Test: Frozen six-call run CTAS_2026-03-25T10.00/01_scan, 641 questions.
Result: 645.84s; usage={'input_tokens': 54158, 'output_tokens': 0, 'sequences': 2}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: 2026-11-15 22:37:23 EST — inspect exact claim carriers in the final Cintas March screen.
Result: all 14 confirmed claims retained; the 7.6/7.9 sentence scores .7248, and the lesser ERP-impact sentence scores .4873 (retained at the frozen .25 cutoff). Numeric assumptions and worded amounts remain held. These are detection results, not complete records.
Next: finish the existing numeric stages, review all resulting proposals and final integrity, write final memo, then stop.

Test: Frozen six-call run CTAS_2026-03-25T10.00/02_bounds, 26 questions.
Result: 223.89s; usage={'input_tokens': 20022, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2026-03-25T10.00/03_fields, 96 questions.
Result: 304.56s; usage={'input_tokens': 25891, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2026-03-25T10.00/04_copy_prepared_0, 18 questions.
Result: 61.94s; usage={'input_tokens': 4822, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2026-03-25T10.00/04_copy_QA004_0, 3 questions.
Result: 15.09s; usage={'input_tokens': 1209, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2026-03-25T10.00/04_copy_QA016_0, 3 questions.
Result: 15.09s; usage={'input_tokens': 1195, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call run CTAS_2026-03-25T10.00/05_optional_0, 5 questions.
Result: 163.77s; usage={'input_tokens': 14857, 'output_tokens': 0, 'sequences': 1}; error=None.
Next: Continue this fixed procedure without repairs; score all six and wait for owner.

Test: Frozen six-call assembly CTAS_2026-03-25T10.00.
Result: 8 numeric proposals; {'held': 8}; all sentence/number routing outcomes retained. No correctness claim before source review.
Next: Continue the same procedure on remaining calls, then report complete/held/missed and stop.

Test: 2026-11-15 22:50:27 EST — source review of all eight numeric proposals from the final frozen Cintas March call.
Result: 0 complete, 14 held, 0 missed among confirmed claims; one repeated leverage target. Evidence/field omissions persist; signed negative bounds are reversed by the number assembly and correctly held, a code integration defect distinct from model errors.
Next: verify the frozen files and final counts, write the one-page owner memo, then stop; no further inference.

Test: 2026-11-15 22:54:39 EST — final frozen-run integrity and owner memo reconciliation.
Result: six calls finished once, 0 complete / 79 held / 0 missed in the confirmed development reference; 45 numeric proposals, four repeats, two correct-content holds, one incorrect unflagged proposal caught in review. All 322 file/answer/accounting checks passed, including 122 exact source spans; these checks do not establish semantic accuracy. Main strategy/rulebook/client unchanged.
Next: STOPPED. Await owner; no further model calls, repairs, strategy edits or production work under this bounded task. Latest summary: OWNER_REVIEW.md.
