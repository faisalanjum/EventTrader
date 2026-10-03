# Grader review handover — for Codex's independent review (Fable, 2026-10-03)

**What this is.** The code that scores a conversion route (tool output in the common route format) against the frozen golden set
(package 1134, `../golden/PACKAGE.json`). Pure code, standard library only, no AI, no hard-coded document strings. It answers,
per key target and per field: preserved and correctly associated (pass), not (fail with a reason), or not resolvable (unresolved).
It does **not** rank tools and does **not** grade meaning fields (T4: `measure`, `sign`, `unit_interpretation`, `marker_meaning`
are reported `not_t1`).

**What the owner asked you to confirm.** (1) Correct output passes. (2) Missing text, wrong values, wrong associations fail.
(3) HTML, PDF and XML are handled fairly. Please do not weaken the key to make tools pass; do not read held-out answers.

## Run it (repo root, python 3.10+, no extra packages for the grader itself)
```
python3 -B -m unittest discover -s benchmarks/prepare/grader/tests -t .        # 112 tests, ~1 s
python3 -B -m benchmarks.prepare.grader.checks.real_pairs                       # 42 real-original variants, ~20 s
python3 -B -m benchmarks.prepare.grader.grade --route <run>/route --out <run>/graded   # grade one route (key defaults to golden/PACKAGE.json)
python3 -B -m benchmarks.prepare.grader.checks.why <run>/graded [check:reason]  # explain failures: key value vs what the route carried
python3 -B benchmarks/prepare/golden/check_package.py                           # the key is where PACKAGE.json says, byte for byte
```
Adapters (tool output → common format) run under each tool's own environment; see `README.md`. Graded runs used for the numbers
below are under `/home/faisal/prepare_work/grader_runs/` (development split only; held-out aggregates only).

## Size and shape
`__init__.py` 1, `adapters/__init__.py` 2, `adapters/docling_html.py` 133, `adapters/docling_pdf.py` 129, `adapters/edgartools_html.py` 125, `adapters/prestep_headings.py` 70, `adapters/screen_grid.py` 109, `anchor.py` 172, `grade.py` 760 lines of code; tests 1114 lines;
checks 398 lines. Design and every rule's origin: `DESIGN.md` (§1–§20; §20 = final contract alignment).

## Where the proof comes from
| Proof | What it shows | Where |
|---|---|---|
| 112 unit tests on one fixture (HTML table + text + picture, XML form, native PDF) | every check passes on a correct route; each planted fault (changed digit, dropped cell, value under the next column / next row, lost parentheses, glued footnote digit, dropped note, dropped heading, dropped paragraph, reordered blocks, wrong link, XML value moved to another person, PDF value under another column or on a missing page, dishonest anchor, changed source bytes…) fails with the named reason | `tests/test_grade.py`, `tests/test_anchor.py`, `tests/test_adapters.py` |
| 42 real-original variants | controls built from the originals (never from a tool): the 7 contract pairs and the 8 regression cases of the key package; every valid representation passes, every damaged copy fails for the stated reason | `checks/real_pairs.py`, `checks/RESULTS.json` |
| 7 route variants × 69 development files | generality: no crash, gates computed, every failure explainable with `checks/why.py`; numbers below | `/home/faisal/prepare_work/grader_runs/*/graded/summary.md` |

## Contract → code → proof
| Rule | Implemented in | Proved by |
|---|---|---|
| Value (printed/display, symbol cells apart or merged, parentheses, minus) | `Grader.value`, `same()` | tests `changed_digit`, `lost_parentheses`, `symbol_cell_moved`, `symbol_cells_merged`; pairs "$ ( ) kept as separate cells" / "joined into one cell" / "parentheses removed" / "minus sign lost" |
| Row association (row label, row context, header path by column coverage, continued tables, merged stacked headers) | `row_label`, `row_context`, `header_path`, `col_hit` | tests `value_in_the_next_row`, `value_under_the_next_column`, `header_over_the_wrong_columns`, `merged_stacked_header_cell`, `table_continued_as_two_units`; pairs "five header fragments" / "fragments joined" / "Excluding fragment lost" / "header assigned to the adjacent column" |
| E2 "(continued)" both sides | `heading_eq`, `_CONTINUED` | test `continued_in_the_key_heading_is_folded_too` |
| E6 references: destination, wrong explicit link fails, missing edge is only a structure miss | `references` (`wrong_link`), `reference_linked` | tests `reference_destination_changed_fails`, `explicit_link_to_the_wrong_block_fails`; pair "link points to another block" |
| E8 typography: quotes within class, dashes to hyphen, format characters as whitespace, brackets by Unicode category | `anchor.norm/_FOLD/_WS` | tests `norm_*`, `whitespace_quotes_dashes_and_brackets_come_from_unicode_categories`, `straight_quote_in_tool_text_matches_curly_quote` |
| E10 strict transcriptions, WER diagnostic only | `grade_structure` (`wer` in detail only) | test `picture_block_dropped_fails_text_with_word_error_rate`; pairs "one block omitted" / "one \"not\" omitted" / "blocks out of order" |
| E11 footnotes: any layout, complete note, right mark→note link, glued digit fails | `footnotes`, `note_linked` | tests `footnote_digit_glued_to_the_value_fails`, `dropped_note_fails`, `note_printed_as_the_tables_last_row`, `note_laid_out_as_a_one_cell_table`, `note_split_into_mark_and_body_units`, `notes_block_holding_several_numbered_notes`; pair "footnote digit joined to the value" |
| E12 pieces of one passage: spell the key text, no lost space, no inserted space in a word; fragments pass only with proven adjacency (`fragmented` counted) | `pieces_match`, `adjacent` | tests `block_split_by_the_tool_is_joined…`, `fragments_of_one_word_pass_flagged…`, `a_word_split_whose_pieces_are_not_adjacent…fails`, `a_space_lost_between_two_words…fails`, `a_word_broken_by_a_space_fails` |
| E13 title cell with the record's own basis/unit text | `same()` joined_with_own_pieces, `table_title` | tests `title_cell_that_also_holds_the_records_unit_line`, `title_cell_holding_title_basis_words_and_a_unit_line` |
| E14 header scope from the rendered source; any representation; screen step = separate declared route | `header_path` (grid), `adapters/screen_grid.py` (route-side) | tests `value_cell_spanning_columns_is_covered…`, adapter tests `screen_columns_come_from_pixel_edges…`, `route_cells_take_the_screen_grid…` |
| E15 period parts: column by coverage, same-row by row, label-column time heading above the value until a competing known time heading | `periods` (`column`, `order`, `scope`) | tests `time_only_section_row…needs_no_column_coverage`, `time_row…below_the_value_does_not_govern_it`, `value_moved_under_a_competing_time_group_fails`, `an_unrelated_label_row…does_not_end_its_scope` |
| E16 visible text: display/opacity/ix:hidden hide subtrees, visibility overridable, font size never, hidden counted | `anchor.Visible` (`hidden_chars`), gate `nothing_lost` | tests `hidden_subtrees_head_comments_and_styles_are_not_visible`, `text_made_invisible_by_style…is_counted`, `a_visible_descendant_inside_a_hidden_parent…`, `tiny_or_white_text_is_still_visible_text…` |
| E17 formats declared; unsupported counted, never hidden | `run` (`NOT_CONVERTED` / route `UNSUPPORTED`), summary by split × format | tests `failed_file_marks_its_targets_not_converted`, `summary_counts_targets_by_split_and_format` |
| XML forms (field units, groups, expanded names) | `grade_xml`, `local()` | tests `xml_value_moved_to_another_reporting_person_fails`, `xml_element_name_changed_fails…`; pairs "expanded names", "value moved to another reporting person", "namespace changed", "element renamed" |
| PDF (page + region anchors, top-left, row/column by geometry) | `RouteFile.cells_at` (regions), `source_before` | tests `pdf_value_under_another_column…`, `pdf_value_on_a_missing_page…`, `source_order_of_pdf_boxes…`; pairs "value linked to its row, column and page" (×5 files) and their damaged copies |
| Gates P14: honest anchors, ids + run facts, reading order, markers apart, nothing lost | `gates_for_file`, `Visible.uncovered` | tests `dishonest_anchor_fails_the_anchor_gate`, `reordered_units_fail_the_order_gate`, `dropped_paragraph_is_unresolved_and_counted_as_lost`, `every_target_passes_and_every_gate_holds` |
| Key integrity: source bytes must match the key's sha256; excluded fields (5) honoured; held-out hidden by default | `run` (`INPUT_MISMATCH`), `load_key`, `--heldout-detail` | tests `changed_source_bytes_stop_that_file…`, `heldout_detail_is_hidden_by_default` |

## Known limits (stated, not hidden)
- E15: a competing time group whose heading no key record anchors and whose text equals no known period part is invisible to the scope rule.
- E12: adjacency can be proved only from byte anchors; PDF region anchors cannot prove it, so a within-word split on the PDF route fails.
- Heading recognition, note links and reference links are **structure counts**, not pass rules (the contract grades preservation; recognition is reported separately).
- The linker (`anchor.link`) serves routes without source positions: long texts are placed in order, short texts between anchored neighbours; a fallback placement is flagged `out_of_order`, never silent. Dishonest anchors are a gate failure.
- No XML route exists yet (both tools: unsupported, counted); the PDF route covers 14 development files.
- The screen-span step is a separate declared route (E14), scored beside the plain one, never merged into it.

## Results on the development split (final code, key 1134; run of 2026-10-03 12:36)
Development split only: 171 HTML cells, 60 HTML blocks, 9 XML cells, 9 PDF blocks (plus 5 supplement PDF cells on the PDF route).
"Not converted 18" = the 9 XML + 9 PDF development targets no HTML route claims (counted, never hidden — E17). Headings / notes / refs
are structure counts, not pass rules. The screen-span step and the heading pre-step are separate declared routes (E14).

| route | HTML cells | HTML blocks | PDF targets | headings recognised | notes linked | refs linked | gates failing | not converted / unresolved |
|---|---|---|---|---|---|---|---|---|
| Docling HTML | 123/171 | 24/60 | - | 0/152 | 8/34 | 0/13 | nothing_lost | not converted 18 |
| Docling HTML + screen | 127/171 | 24/60 | - | 0/152 | 8/34 | 0/13 | nothing_lost | not converted 18 |
| Docling HTML + headings | 125/170 | 20/60 | - | 104/145 | 8/34 | 0/13 | nothing_lost | not converted 18, unresolved 1 |
| Docling HTML + headings + screen | 129/170 | 20/60 | - | 104/145 | 8/34 | 0/13 | nothing_lost | not converted 18, unresolved 1 |
| edgartools HTML | 141/171 | 22/54 | - | 0/166 | 8/35 | 0/12 | nothing_lost, reading_order | unresolved 6, not converted 18 |
| edgartools HTML + screen | 145/171 | 22/54 | - | 0/166 | 8/35 | 0/12 | nothing_lost, reading_order | unresolved 6, not converted 18 |
| Docling PDF route (14 files) | 11/36 | 1/5 | 3/9 | 6/17 | 0/4 | 0/4 | nothing_lost | not converted 194, unresolved 5 |

What the numbers are for here: the grader ran on every development file of both tools without a crash; every gate is computed; every
failure is explainable with `checks/why.py`. They are **not** a tool ranking (that waits for this review, then the controls and the
held-out split). Three grader defects were found and fixed by these runs themselves, all in the linker/gate for footnote marks: a mark
printed before its text, a two-column layout where the first column's text took the second column's leading mark, and one mark on
each side of the same text (DESIGN.md §20). After the fixes the honest-anchor gate passes for every route.

Proof state at hand-over: 116 unit tests, 42/42 real-original variants, package check `golden/check_package.py` passes.
