# Decider guidance study — November 15, 2026

**Start with the [function-by-function results](readme.md).** This folder preserves the stopped experiment, its earlier attempts, supporting data and external reviews. Historical code and results are unchanged; documentation does not approve a new extraction strategy.

## Where to find things

| Location | Contents and status |
| --- | --- |
| [experiment/OWNER_REVIEW.md](experiment/OWNER_REVIEW.md) | Original one-page stopping memo: demonstrated parts, owner choices, remaining failures and the procedure actually run. |
| [experiment/frozen_six/](experiment/frozen_six/) | **Final unchanged six-call run.** Configuration, code/source fingerprints, exact requests, raw answers, proposals, holds and reviews. |
| [experiment/sentence_screen/](experiment/sentence_screen/) | Earlier standalone Paychex March sentence test, its 22 positive/eight negative controls, and review of all 104 selections. |
| [experiment/passage_cohort/](experiment/passage_cohort/) | Earlier six-call prepared-block/Q&A screening test. |
| [experiment/turn_screen/](experiment/turn_screen/) | Speaker-turn comparison: six requests prepared, **only Paychex March executed**. |
| [experiment/main_path/](experiment/main_path/) | Earlier combined stages and focused tests: roles, endpoints, measures, units, support, words and field copying. Different configurations; do not merge their scores into a single pipeline result. |
| [experiment/quote_fields/](experiment/quote_fields/) | Field choices on reviewed evidence versus the whole call, with matched requests and scores. |
| [experiment/prepared_record/](experiment/prepared_record/) | Prepared-section record probes and narrower evidence-copy experiments. |
| [experiment/assembled_proposals/](experiment/assembled_proposals/) | Reconciliation of earlier saved stages from mixed configurations; **not the final frozen run**. |
| [experiment/metadata_filter/](experiment/metadata_filter/) | Source-header filtering, full-cohort read-only audit and preservation checks. |
| [experiment/calendar_support/](experiment/calendar_support/) | Native calendar-helper checks and read-only review of stored fiscal metadata. |
| [experiment/reference_key/](experiment/reference_key/) | Human source readings, exact reference evidence and comparisons: 186 passages, 102 entries, of which 79 enter the final confirmed-claim count. Development reference, not an independent final key. |
| [experiment/sources.json](experiment/sources.json) | Six model-input source reconstructions; corresponding `.txt` files sit beside it. |
| [experiment/records54.md](experiment/records54.md) | The 54 legacy Guidance/GuidanceUpdate records used for comparison. Their old schema/defaults are not the current correctness standard. |
| [source_snapshots/](source_snapshots/readme.md) | Original six graph snapshots and extraction queries, preserved separately from reconstructed inputs. |
| [project_snapshots/](project_snapshots/) | Supporting project code and the rulebook, with original paths preserved. Two code files match frozen run hashes; others are explicitly archive-time snapshots. See the catalogue below. |
| [experiment/docs/](experiment/docs/) | Saved upstream documentation/code and revision information, including TypeSafe references. These are inspection snapshots, not the installed runtime. |
| [experiment/vendor/](experiment/vendor/) | Supplied `pysbd 0.3.4` sentence splitter, metadata, license, examples and benchmarks. |
| [external_review/](external_review/readme.md) | Claude-supplied reviews, draft inventory, short-text Locate results and usage notes. Proposals remain proposals unless supported by a recorded test/decision. |
| [archive_manifest.json](archive_manifest.json) | Original-to-archive path map, hashes, byte counts, cache exclusions and missing external fixtures. |
| [functional_checks.json](functional_checks.json) | Archive-time review of saved sentence answers: 79/79 claim retention, 408 exact selections, and final-run 20/22 sentence-control retention. No new inference. |
| [archive_verification.json](archive_verification.json) | Copy integrity, documentation links, code coverage and syntax/JSON checks performed while archiving. These are not model-accuracy tests. |

Other root notes—`progress.md`, `strategy_*.md`, `review*.md`, `pending_claude_review.md`, `final_review_assessment.md`, `all_66_dispositions.json`, `continuation*.md`—preserve the reasoning/history. Root `.log` and `*_request`, `*_result`, `*_scored` JSON files belong to the matching script/test name. They do not replace the current project rulebook or the final run.

## Reading the final run

1. [configuration.json](experiment/frozen_six/configuration.json), [manifest.json](experiment/frozen_six/manifest.json): fixed settings and saved fingerprints. Returned model name does **not** verify weight/conversion/runtime identity; that remains explicitly unverified.
2. Per-call folders: `prepared.json` and `ledger.json` retain text and locations; numbered request/result files preserve what the model saw and answered; `targets.json`, `bound_holds.json`, `copies.json` and `proposals.json` preserve intermediate decisions.
3. [run_summary.json](experiment/frozen_six/run_summary.json): timing, usage and totals. [proposal_reviews.json](experiment/frozen_six/proposal_reviews.json): manual source review of the 45 proposals, including the incorrect proposal that cleared automatic holds.
4. [review_counts.json](experiment/frozen_six/review_counts.json): outcomes for all 79 confirmed claims. [other_reference_entries.json](experiment/frozen_six/other_reference_entries.json): the other 23 entries, without hiding them in the denominator.
5. [integrity.json](experiment/frozen_six/integrity.json): 322 mechanical checks passed, including 122 exact source spans. This does not certify meanings or record completeness.

## Preservation and reuse limits

- **644 files / 33,735,376 bytes** copied byte-for-byte: 634 original experiment/review/source files plus 10 supporting project snapshots. Original directories remain in `/tmp`. The manifest maps every original path. Only generated Python/pytest caches were excluded (66 files). New README/check files are additional archive documentation.
- Original absolute `/tmp` paths remain inside scripts and historical metadata to preserve tested code and hashes. Links within the preserved experiment layout remain usable; historical links outside it may not resolve. Use the manifest to resolve old paths; old prose can describe intermediate results or superseded attempts.
- **Do not run or import scripts merely to inspect them.** Many execute inference at top level; others write derived files or query Neo4j. The code catalogue marks the kind of work. Even existing test files may import helpers with project dependencies.
- For any later authorized rerun, make a separate working copy, deliberately update paths/output locations, and record the new configuration. Do not overwrite this evidence or present edited code as the frozen tested version. No compatibility wrapper was added.
- Supporting project source is preserved under `project_snapshots/`; the final run's two fingerprinted project files still matched when copied. Other dependencies were not fingerprinted at run time and are labelled archive-time copies. The Python environment, model weights and running model service are **not** bundled (`Babel 2.17` was used; `pysbd 0.3.4` is included). No `.env` or credentials are included.
- External Locate fixtures `4c_ref_answers.json`, `eval_set.json` and `inputs_acme_report.json` were **not supplied**; see [external review limits](external_review/readme.md). This archive is not a fully self-contained reproduction environment.
- Final fiscal-period options were a May-31 fixture for Cintas/Paychex, not a generic company-calendar implementation. Five original snapshots lack speaker metadata; preservation does not silently repair them.
- Reference annotations and expected answers are **grading material only**, never discovery inputs. Names such as `unseen_*` describe an earlier test stage; all saved examples are now exposed development material.
- Upstream `docs/manifest.json` records two initial failed fetches whose files were later saved. Keep it as history, not proof that every installed-runtime file matches upstream. The local punctuation fix/runtime fingerprint remains a separate reproducibility limit.

## Code catalogue

Every saved Python file is listed below. **Model** means it can make inference calls; **offline** reads/writes saved data; **database** means read-only graph access; **helper/test** is support code; **reference** is manual grading or inspection material. These descriptions are not instructions to execute the archived scripts.

### Final run, helpers and focused tests

| File | Kind | Purpose |
| --- | --- | --- |
| [frozen_six_run.py](experiment/frozen_six_run.py) | Model | Runs the final fixed procedure on all six calls; saves requests, probabilities, proposals and named holds. |
| [frozen_six_score.py](experiment/frozen_six_score.py) | Offline | Grades saved final outputs and writes derived counts; does not independently judge source meaning. |
| [frozen_six_review_carriers.py](experiment/frozen_six_review_carriers.py) | Reference | Records the manually reviewed sentence/number locations for 79 claims; never model input. |
| [metadata_candidates.py](experiment/metadata_candidates.py) | Helper | Reuses the repository's speaker-header matcher to skip verified metadata digits while retaining exact speech positions; unknown headers stay unchanged. |
| [proposal_numbers.py](experiment/proposal_numbers.py) | Helper | Uses Babel and existing exact-number helpers to parse/scale printed amounts; does not infer what they mean. |
| [test_frozen_six_mechanics.py](experiment/test_frozen_six_mechanics.py) | Test | Checks final-run boundaries, source copying and configuration mechanics; not model accuracy. |
| [test_metadata_candidates.py](experiment/test_metadata_candidates.py) | Test | Checks verified, missing and mismatched headers, with positive controls for spoken digits. |
| [test_proposal_numbers.py](experiment/test_proposal_numbers.py) | Test | Checks supported number spelling, scaling and boundary cases. |

### Source preparation and manual reference

| File | Kind | Purpose |
| --- | --- | --- |
| [prepare_review.py](experiment/prepare_review.py) | Offline | Assembles saved graph snapshots into source text, sources.json and the legacy-record comparison. |
| [reference_key/source_annotations.py](experiment/reference_key/source_annotations.py) | Reference | Shared helper for source-based manual annotations and evidence checks. |
| [reference_key/annotate_ctas_sep.py](experiment/reference_key/annotate_ctas_sep.py) | Reference | Builds the manually read Cintas September 2025 reference; not an extraction rule. |
| [reference_key/annotate_ctas_dec.py](experiment/reference_key/annotate_ctas_dec.py) | Reference | Builds the manually read Cintas December 2025 reference; not an extraction rule. |
| [reference_key/annotate_ctas_mar.py](experiment/reference_key/annotate_ctas_mar.py) | Reference | Builds the manually read Cintas March 2026 reference; not an extraction rule. |
| [reference_key/annotate_payx_sep.py](experiment/reference_key/annotate_payx_sep.py) | Reference | Builds the manually read Paychex September 2025 reference; not an extraction rule. |
| [reference_key/annotate_payx_dec.py](experiment/reference_key/annotate_payx_dec.py) | Reference | Builds the manually read Paychex December 2025 reference; not an extraction rule. |
| [reference_key/annotate_payx_mar.py](experiment/reference_key/annotate_payx_mar.py) | Reference | Builds the manually read Paychex March 2026 reference; not an extraction rule. |

### Screening and source checks

| File | Kind | Purpose |
| --- | --- | --- |
| [passage_cohort_check.py](experiment/passage_cohort_check.py) | Model | Tests one screening question per prepared block/Q&A exchange with the whole call visible. |
| [turn_screen_check.py](experiment/turn_screen_check.py) | Model | Compares existing speaker-turn targeting with passage targeting. |
| [sentence_screen_check.py](experiment/sentence_screen_check.py) | Model | Tests sentence questions with the full call visible. |
| [score_passage_cohort.py](experiment/score_passage_cohort.py) | Offline | Scores saved passage-screen answers against the frozen development labels. |
| [score_turn_screen.py](experiment/score_turn_screen.py) | Offline | Scores saved speaker-turn answers and retained parent passages. |
| [score_sentence_screen.py](experiment/score_sentence_screen.py) | Offline | Scores saved sentence controls and retained parent passages. |
| [audit_metadata_candidates.py](experiment/audit_metadata_candidates.py) | Database | Audits header exclusion, exact positions and speech-digit preservation over the live standard cohort; read-only. |
| [run_checks.py](experiment/run_checks.py) | Mixed | Combines boundary checks, read-only graph checks and model probes; not an offline-only verifier. |

### Earlier combined stages and evidence-copy tests

| File | Kind | Purpose |
| --- | --- | --- |
| [main_path_trial.py](experiment/main_path_trial.py) | Model/helper | Earlier passage/candidate workflow; also supplies shared request helpers used by later probes. |
| [main_path_fields.py](experiment/main_path_fields.py) | Model | Earlier field choices and evidence-copy stage; its former routing gaps are preserved as history. |
| [main_path_assemble.py](experiment/main_path_assemble.py) | Offline | Assembles earlier saved stages into provisional records. |
| [assemble_saved_proposals.py](experiment/assemble_saved_proposals.py) | Offline | Reconciles earlier outputs from different configurations; not a single unchanged run. |
| [finish_proposal_reconciliation.py](experiment/finish_proposal_reconciliation.py) | Offline | Applies existing number normalization to saved proposals and retains unresolved gaps. |
| [prepared_record_probe.py](experiment/prepared_record_probe.py) | Model | Tests fields/evidence for six expressions using the whole prepared section. |
| [prepared_copy_label_check.py](experiment/prepared_copy_label_check.py) | Model | Tests a controlled change to Locate copying instructions. |
| [selected_copy_check.py](experiment/selected_copy_check.py) | Model | Tests copying from previously selected evidence. |
| [review_prepared_record.py](experiment/review_prepared_record.py) | Offline | Reconstructs quotes and checks saved prepared-section proposals; mechanical checks do not prove meanings. |
| [final_review_item8_audit.py](experiment/final_review_item8_audit.py) | Offline | Accounts for outcomes of 333 earlier targets to expose silent routing drops. |

### Numeric occurrence identity, roles and endpoints

| File | Kind | Purpose |
| --- | --- | --- |
| [tagged_tests.py](experiment/tagged_tests.py) | Model | Tests visible occurrence tags for repeated-number roles and Cintas field questions. |
| [target_binding_probe.py](experiment/target_binding_probe.py) | Model | Compares tag-only questions with literal-number-plus-tag questions. |
| [numeric_bounds_probe.py](experiment/numeric_bounds_probe.py) | Model | Tests choosing range endpoints instead of asking Locate to copy them. |
| [numeric_bounds_compact.py](experiment/numeric_bounds_compact.py) | Model | Tests shorter endpoint-choice questions. |
| [numeric_bounds_shared.py](experiment/numeric_bounds_shared.py) | Model | Tests endpoint questions with definitions shared once in the input. |
| [literal_numeric_fields.py](experiment/literal_numeric_fields.py) | Model | Asks field questions about numbers classified as current forecasts. |
| [expression_fields_probe.py](experiment/expression_fields_probe.py) | Model | Groups chosen endpoints before asking expression-level fields. |
| [shared_role_population.py](experiment/shared_role_population.py) | Model | Classifies the roles of all numeric candidates in retained passages. |
| [literal_copy_probe.py](experiment/literal_copy_probe.py) | Model | Applies literal-number-plus-tag addressing to copy requests. |

### Measure naming and copying probes

| File | Kind | Purpose |
| --- | --- | --- |
| [locate_followup.py](experiment/locate_followup.py) | Model | Earlier targeted Locate wording/context comparisons. |
| [passage_fields.py](experiment/passage_fields.py) | Model | Tests copying fields at passage level. |
| [source_names_and_choices.py](experiment/source_names_and_choices.py) | Model | Tests source wording plus measure, period, unit and scale choices; uses the two-company May-31 fixture, not an existing Driver-name catalogue. |
| [measure_kind.py](experiment/measure_kind.py) | Model | Checks whether copied wording actually names a business measure. |
| [measure_occurrences.py](experiment/measure_occurrences.py) | Model | Tests linking source measure-wording occurrences to forecast amounts. |
| [measure_pointer_probe.py](experiment/measure_pointer_probe.py) | Model | Chooses an evidence sentence before copying the measure, without supplying existing Driver names. |
| [measure_local_probe.py](experiment/measure_local_probe.py) | Model | Tests short Locate inputs containing the selected measure sentence and forecast sentence. |

### Units and evidence-based field choices

| File | Kind | Purpose |
| --- | --- | --- |
| [unit_rule_probe.py](experiment/unit_rule_probe.py) | Model | Tests explicit questions for the rulebook's growth-comparison-basis requirement. |
| [unit_evidence_probe.py](experiment/unit_evidence_probe.py) | Model | Asks whether comparison-basis evidence is present. |
| [unit_basis_choice_probe.py](experiment/unit_basis_choice_probe.py) | Model | Combines presence and comparison basis in one choice; its input includes scoped evidence, so this is not a bare whole-call test. |
| [unit_basis_boundary_probe.py](experiment/unit_basis_boundary_probe.py) | Model | Tests real positive controls and controlled changes at the evidence boundary. |
| [unit_quote_probe.py](experiment/unit_quote_probe.py) | Model | Chooses unit/scale from exact reviewed quotes. |
| [unit_assembled_quote_probe.py](experiment/unit_assembled_quote_probe.py) | Model | Chooses units from automatically assembled continuous quotes. |
| [unit_selected_evidence_probe.py](experiment/unit_selected_evidence_probe.py) | Model | Chooses units from selected sentences without intervening text. |
| [quote_fields_probe.py](experiment/quote_fields_probe.py) | Model | Tests seven field choices on reviewed evidence. |
| [quote_fields_time_check.py](experiment/quote_fields_time_check.py) | Model | Tests the duration-versus-instant clarification with controls and with real evidence only. |
| [quote_fields_whole_call_check.py](experiment/quote_fields_whole_call_check.py) | Model | Matched field comparison using the whole call instead of reviewed excerpts. |
| [quote_fields_basis_check.py](experiment/quote_fields_basis_check.py) | Model | Adds an explicit comparison-basis choice and applies rule 3.33; saves raw and rule-applied outcomes separately. |

### Worded guidance and support experiments

| File | Kind | Purpose |
| --- | --- | --- |
| [unseen_word_probe.py](experiment/unseen_word_probe.py) | Model | Earlier worded-guidance probes on Micron, FedEx and Ollie's; now exposed development examples. |
| [unseen_passage_probe.py](experiment/unseen_passage_probe.py) | Model | Earlier prepared-section/Q&A passage probes on those additional examples. |
| [unseen_sentence_probe.py](experiment/unseen_sentence_probe.py) | Model | Earlier sentence probes and controls on those additional examples. |
| [targeted_word_fields.py](experiment/targeted_word_fields.py) | Model | Tests field copying for selected worded forecasts. |
| [word_choice_probe.py](experiment/word_choice_probe.py) | Model | Tests word-position choices for measure/value boundaries; exploratory, not an adopted working path. |
| [word_start_probe.py](experiment/word_start_probe.py) | Model | Tests yes/no questions at word positions for forecast starts. |
| [count_probe.py](experiment/count_probe.py) | Model | Tests counting forecasts within a sentence. |
| [ordinal_word_probe.py](experiment/ordinal_word_probe.py) | Model | Tests field boundaries for the first/second/etc. forecast after model counting. |
| [shared_all_guidance_screen.py](experiment/shared_all_guidance_screen.py) | Model | Tests a shared sentence question covering numeric and worded guidance. |
| [support_sentence_probe.py](experiment/support_sentence_probe.py) | Model | Tests whether a sentence supplies an assumption/exclusion/dependency for a particular forecast. |

### Upstream code kept for inspection

| File | Kind | Purpose |
| --- | --- | --- |
| [docs/model.py](experiment/docs/model.py) | Reference | Saved upstream model implementation; not the installed local runtime. |
| [docs/locate.py](experiment/docs/locate.py) | Reference | Saved upstream Locate implementation used to inspect boundaries and limits; not the locally patched runtime. |
| [docs/protocol.py](experiment/docs/protocol.py) | Reference | Saved upstream request/response definitions. |

### External Locate test

| File | Kind | Purpose |
| --- | --- | --- |
| [external_review/locate_boundaries.py](external_review/locate_boundaries.py) | Model / offline comparison | Supplied short-text before/after punctuation test; `--compare` reads saved results. Three referenced fixtures were not supplied. |

### Supporting project source snapshots

These nine Python files are **reference copies**, not new implementations or installed modules. The first two match hashes recorded before the final run; the remaining seven preserve current supporting source without claiming a missing historical fingerprint. Originals in the project were not edited. Their repository-relative paths are preserved below `project_snapshots/`.

| File | Purpose |
| --- | --- |
| [config/local_llm.py](project_snapshots/config/local_llm.py) | Local model client, including `decide()`; matches the final-run fingerprint. |
| [driver_period_resolver.py](project_snapshots/driver_reference/core/driver_period_resolver.py) | Existing fiscal-period resolver used by the run; matches the final-run fingerprint. |
| [driver_ids.py](project_snapshots/driver_reference/core/driver_ids.py) | Existing period/identity validation used by the resolver. |
| [outcome_codes.py](project_snapshots/driver_reference/core/outcome_codes.py) | Existing outcome-code definitions used by the resolver. |
| [xml_names.py](project_snapshots/driver_reference/xml_names.py) | Existing qualified-name helper imported by the identity module. |
| [exact_numbers.py](project_snapshots/driver_reference/relocation/exact_numbers.py) | Existing precise number parsing/scaling helpers used by the experiment wrapper. |
| [m1_transcript_census.py](project_snapshots/scripts/driver_seed/relocate_probe/phase2/m1_transcript_census.py) | Existing speaker-header matcher; its original census entry point can query Neo4j. |
| [fiscal_math.py](project_snapshots/.claude/skills/earnings-orchestrator/scripts/fiscal_math.py) | Existing fiscal-date arithmetic required by the period resolver. |
| [guidance_ids.py](project_snapshots/.claude/skills/earnings-orchestrator/scripts/guidance_ids.py) | Existing guidance-period ID builder required by the period resolver. |

The [rulebook snapshot](project_snapshots/.claude/plans/Drivers/DriversFinal/DRIVER_RULES_Categorized.md) preserves the rules available at archive time. It is a historical reference copy, **not another maintained rulebook**; the live project's rules still govern later work. Its hash and snapshot limitation are recorded in the archive manifest.

### Vendored sentence-splitting library

All **51 Python files** below belong to the supplied `pysbd 0.3.4` package, not newly written extraction code. Package metadata and its license remain under [experiment/vendor/](experiment/vendor/). Listings are complete, including examples and benchmarks preserved with the package.

**Sentence splitter core (12 files).** Unchanged package entry points, sentence-boundary processing, punctuation/abbreviation handling and utility functions.

- [pysbd/__init__.py](experiment/vendor/pysbd/__init__.py)
- [pysbd/abbreviation_replacer.py](experiment/vendor/pysbd/abbreviation_replacer.py)
- [pysbd/about.py](experiment/vendor/pysbd/about.py)
- [pysbd/between_punctuation.py](experiment/vendor/pysbd/between_punctuation.py)
- [pysbd/cleaner.py](experiment/vendor/pysbd/cleaner.py)
- [pysbd/exclamation_words.py](experiment/vendor/pysbd/exclamation_words.py)
- [pysbd/languages.py](experiment/vendor/pysbd/languages.py)
- [pysbd/lists_item_replacer.py](experiment/vendor/pysbd/lists_item_replacer.py)
- [pysbd/processor.py](experiment/vendor/pysbd/processor.py)
- [pysbd/punctuation_replacer.py](experiment/vendor/pysbd/punctuation_replacer.py)
- [pysbd/segmenter.py](experiment/vendor/pysbd/segmenter.py)
- [pysbd/utils.py](experiment/vendor/pysbd/utils.py)

**Cleaning helpers (2 files).** Unchanged optional package cleaning rules and initialization.

- [pysbd/clean/__init__.py](experiment/vendor/pysbd/clean/__init__.py)
- [pysbd/clean/rules.py](experiment/vendor/pysbd/clean/rules.py)

**Language support (24 files).** Unchanged language modules and registration. These are library sentence-boundary rules, not company-specific guidance rules.

- [pysbd/lang/__init__.py](experiment/vendor/pysbd/lang/__init__.py)
- [pysbd/lang/amharic.py](experiment/vendor/pysbd/lang/amharic.py)
- [pysbd/lang/arabic.py](experiment/vendor/pysbd/lang/arabic.py)
- [pysbd/lang/armenian.py](experiment/vendor/pysbd/lang/armenian.py)
- [pysbd/lang/bulgarian.py](experiment/vendor/pysbd/lang/bulgarian.py)
- [pysbd/lang/burmese.py](experiment/vendor/pysbd/lang/burmese.py)
- [pysbd/lang/chinese.py](experiment/vendor/pysbd/lang/chinese.py)
- [pysbd/lang/danish.py](experiment/vendor/pysbd/lang/danish.py)
- [pysbd/lang/deutsch.py](experiment/vendor/pysbd/lang/deutsch.py)
- [pysbd/lang/dutch.py](experiment/vendor/pysbd/lang/dutch.py)
- [pysbd/lang/english.py](experiment/vendor/pysbd/lang/english.py)
- [pysbd/lang/french.py](experiment/vendor/pysbd/lang/french.py)
- [pysbd/lang/greek.py](experiment/vendor/pysbd/lang/greek.py)
- [pysbd/lang/hindi.py](experiment/vendor/pysbd/lang/hindi.py)
- [pysbd/lang/italian.py](experiment/vendor/pysbd/lang/italian.py)
- [pysbd/lang/japanese.py](experiment/vendor/pysbd/lang/japanese.py)
- [pysbd/lang/kazakh.py](experiment/vendor/pysbd/lang/kazakh.py)
- [pysbd/lang/marathi.py](experiment/vendor/pysbd/lang/marathi.py)
- [pysbd/lang/persian.py](experiment/vendor/pysbd/lang/persian.py)
- [pysbd/lang/polish.py](experiment/vendor/pysbd/lang/polish.py)
- [pysbd/lang/russian.py](experiment/vendor/pysbd/lang/russian.py)
- [pysbd/lang/slovak.py](experiment/vendor/pysbd/lang/slovak.py)
- [pysbd/lang/spanish.py](experiment/vendor/pysbd/lang/spanish.py)
- [pysbd/lang/urdu.py](experiment/vendor/pysbd/lang/urdu.py)

**Shared language rules (3 files).** Unchanged common sentence-boundary definitions shared by the language modules.

- [pysbd/lang/common/__init__.py](experiment/vendor/pysbd/lang/common/__init__.py)
- [pysbd/lang/common/common.py](experiment/vendor/pysbd/lang/common/common.py)
- [pysbd/lang/common/standard.py](experiment/vendor/pysbd/lang/common/standard.py)

**Upstream benchmarks (7 files).** Supplied package benchmarking code and reference cases; not Decider accuracy tests and not run during archiving.

- [benchmarks/__init__.py](experiment/vendor/benchmarks/__init__.py)
- [benchmarks/benchmark_sbd_tools.py](experiment/vendor/benchmarks/benchmark_sbd_tools.py)
- [benchmarks/bigtext_speed_benchmark.py](experiment/vendor/benchmarks/bigtext_speed_benchmark.py)
- [benchmarks/english_golden_rules.py](experiment/vendor/benchmarks/english_golden_rules.py)
- [benchmarks/genia.py](experiment/vendor/benchmarks/genia.py)
- [benchmarks/genia_benchmark.py](experiment/vendor/benchmarks/genia_benchmark.py)
- [benchmarks/universal_dependency_sbd.py](experiment/vendor/benchmarks/universal_dependency_sbd.py)

**Upstream examples (3 files).** Supplied package integration/timing examples; not part of the final extraction procedure.

- [examples/__init__.py](experiment/vendor/examples/__init__.py)
- [examples/pysbd_as_spacy_component.py](experiment/vendor/examples/pysbd_as_spacy_component.py)
- [examples/test_timing_script.py](experiment/vendor/examples/test_timing_script.py)

