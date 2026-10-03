# How the Step 3 answer key is made (Claude) — read me first
**Latest edit: Codex, 2026-10-03.** The 457 answers are unchanged. Source mappings and scoring guidance were corrected;
see [CODEX_ROUND2_UPDATE_20261003.md](CODEX_ROUND2_UPDATE_20261003.md), the prior [source update](CODEX_UPDATE_20261003.md), and [CONVERTER_COMPARISON.md](CONVERTER_COMPARISON.md).

**Raw answers are never edited.** Each model's answers stay exactly as written in `outputs/` (first batch) and
`bundled/outputs/` (bundles). The answer key is rebuilt from them plus Claude's recorded decisions, by one command:

    cd prepare_work/step3_sample_20261002/bulk_20261002 && python3 claude_build_key.py

| File | What it is |
|---|---|
| `claude_build_key.py` | Builds the key. Per field: Claude's recorded decision wins → else the two models' answers if they agree (whitespace only; case, unit case and reference destinations count) → else the target is pending (never guessed). A target without its mandatory content (cell `printed_value`, structure `printed_text`) is pending. Only jobs both models finished are used. (Since 2026-10-03 there is no automatic acceptance of two different answers.) |
| `claude_decide.py` | The only way target-field decisions are written: updates `CLAUDE_DECISIONS.json` and appends to `CLAUDE_DECISIONS_LOG.md` together. |
| `CLAUDE_DECISIONS.json` | Every decision, keyed `packet/target`: field → final answer (or `openai`/`sonnet` = that model's answer), reason, evidence, time. |
| `CLAUDE_DECISIONS_LOG.md` | The same, in plain English, append-only, in the order made (changed decisions are logged as changes). |
| `CONTRACT_DECISIONS_R2.json` | Round 2 package-wide contract decisions and exact wording; also appended to the decision log. These do not create artificial target-field decisions. |
| `decision_batches_*.json` | The exact inputs given to `claude_decide.py` (replayable). |
| `CLAUDE_ANSWER_KEY.json` | The built key: final fields, accepted alternatives, which fields Claude decided and why. |
| `CLAUDE_KEY_PENDING.json` | Targets still needing a decision (should be empty at the end). |
| `CLAUDE_WORKLIST.json` | Inventory of differences between the two models (input for checking). |
| `CLAUDE_GUIDE_ISSUES.md` | Guide gaps found while checking; for guide v3.1 after the run. |
| `CLAUDE_KEY_FLAGS.json` | Record notes a field value cannot express: `uncertain` (genuine source uncertainty, with its scoring), `source_conflicts` (kept as printed). |
| `KEY_SUPPORT_MAP.json` (`claude_support_map.py`) | Where each key field's text sits in the original: the model's own anchors, inline anchors, or Claude's exact search (all occurrences). |
| `KEY_SUPPORT_OVERRIDES.json` | Reviewed field-specific locations, including stacked cells and image regions. Replaying them checks the field value, source fingerprint and bounds; old raw answers stay untouched. |
| `final_pass/` | The final-check pass: `batch_final.py` (every decision, with source assertions), `case_actions.json`, `check_acceptance.py`, `loss_scan.py` + `loss_review.json`, `diff_vs_2236.py`, Codex's review copy. |
| `CLAUDE_FIRST_BATCH_CHECK.md`, `CLAUDE_MECHANICAL_FIRST_BATCH.md` | The first-batch gate check and its mechanical results. |
| `../claude_v3_check.py`, `../claude_render_check.py` | Mechanical checker (template, enums, anchors, model differences) and on-screen header checker (renders the whole original in headless Chrome). |

## Scoring contract (frozen with this key, 2026-10-03; agreed with Codex's final check)
This is a **reference key**, not the JSON shape that each converter must produce. T1/Step 4 checks preservation and
correct association of source evidence, without an AI reader; T4/Step 8 checks interpretation by a fixed reader.
Use [CONVERTER_COMPARISON.md](CONVERTER_COMPARISON.md) for equivalent representations, score boundaries and regression cases.

**One canonical reading per record.** Where a field lists several accepted values, every combination of them is a complete,
correct answer: `final_pass/loss_scan.py` enumerates every combination, and every word any accepted answer can lose was
reviewed (`final_pass/loss_review.json`: only document titles, one-company company lines, time-only headings, spacing,
duplicates of a fixed field, or flagged uncertainty). The first alternative is the canonical reading. There are no
company-specific cross-field rules (`p1_constraints` is empty; the two old pairs became canonical readings).

Equivalences and preservation rules a grader may apply — nothing else is folded:
- **E1** a heading kept as `table_title` may also end `section_path` (or not), while the same heading stays in the answer.
- **E2** Ignore a heading's continuation marker on either side of comparison, only for the same heading and scope. It never removes body text or resets scope.
- **E3** the document's own title (its cover/headline, own file) may be absent, only while identity stays recoverable from
  the frozen metadata or other fields. The own title of an instrument embedded in a file (a form, a schedule) is NOT
  waived when nothing else names it (Trademark Security Agreement form, Nexstar facilities schedule).
- **E4** a heading that is only time and comparison words may move or go, only while its time meaning stays in `periods`.
- **E5** withdrawn: middle headings can carry company, segment or note identity.
- **E6** References require the same referent, relation, status and destination; wording and output shape may differ. An explicit wrong link fails even if the correct text also appears elsewhere. An explicit edge field is unnecessary when another representation retains the correct association.
- **E7** an optional `other` date group may be duplicated or absent only where the key lists that reading; never a
  value/comparison date or a unique describing date.
- **E8** Typography only: retain the existing allowance for same-function dash glyphs; fold curly/straight glyphs within the same quote class. Keep single versus double marks, apostrophes, measurement marks and meaningful punctuation distinct. Never fold negation, numeric signs, ranges or unit case.
- **E9** "ARTICLE N" joined with its own title line = the two lines split; never collapse two different levels.
- **E10** Long transcriptions are strict; word error rate is a diagnostic, never a pass rule. A furniture exclusion requires a reviewed source anchor declared in this key version, must apply equally and must be reported. There is no automatic waiver for page numbers, headers or logos. Without a declared exclusion, retain the text.
- **E11** A footnote may occupy text blocks, table rows, a one-cell table, or separate marker/body blocks. Require the complete note and correct marker-to-note association. A matching note elsewhere, a wrong note link or a marker glued into a number must not pass.
- **E12** Compare ordered, source-mapped pieces of the same passage together, using the order and boundaries retained by the output (including its geometry or mapping). Verify them against the rendered source; never use the key to invent a joiner or restore missing text. Segmentation alone is not a fault, including fragments within a word when adjacency is retained without an inserted separator. Whitespace reflow is allowed only when word/number boundaries and table associations survive. A lost word boundary or an inserted space inside a word must fail; unresolved joins stay explicit.
- **E13** A cell may hold the title plus the record's own basis/unit text. It passes when each required piece stays identifiable, complete and attached to the same table; grade each piece in its own check. Do not drop other parenthetical text, qualifiers or extra units.
- **E14** Header scope comes from the rendered source. Accept any representation that preserves the correct association (grid, geometry or explicit association); otherwise count a miss. Source-aware repair is a declared candidate route, scored separately; the grader never repairs from the key.
- **E15** Each period part must govern the target: column headings by column, time printed on the target's row by row, and preceding time headings by their containing row group until that scope ends. A lower-level subheading or an unrelated label does not by itself end the containing time scope. A new competing group must not inherit the old group's date. Left-column placement alone establishes none of these associations.
- **E16** Grade visible-text targets against rendered content. Exclude only proved non-rendered content from that channel and report its size; retain/account for structured metadata separately. Font size alone does not prove a subtree invisible: a zero-size wrapper can contain visible children, and 1-point text is not automatically invisible. A visibility:hidden ancestor can have visibility:visible descendants; do not discard them. OCR must correspond to visible image content; generated titles are not original evidence. Uncertain visibility remains explicit.
- **E17** Declare each route's supported formats. Keep all 30 XML targets and count unsupported XML explicitly. HTML-only results compare HTML performance only and cannot select the complete pipeline. Test an approved tool-based XML route before pipeline selection; no custom XML converter.

Conventions applied consistently across the key at the final check (CLAUDE_GUIDE_ISSUES.md V14 revised, V18–V22):
- Headings by function: a standalone styled caption that introduces the following text is a heading even as a full
  sentence (Digital Realty, Yelp, e.l.f.); a numbered inline legal section ("Section 1.01 Defined Terms.", "6.10
  Transactions with Affiliates.") is a containing heading of what it holds (added to 12 contract records).
- Page banners and "(continued)" repeats never reset scope; signatures close the last section; a whole-page picture
  takes `kind` image and only the headings that contain the whole page.
- `header_path` keeps literal on-screen spans; a change column's underlying measure goes to `measure` (Euronet, Aflac).
- `periods` uses value/comparison only where the source states the direction; announcement, grant, valuation and
  event dates stay `other` with their describing words; a forecast horizon is the value period (fairness opinion).
- `segment_or_basis` keeps every condition, definition or holding basis the source applies to the value (rate
  applicability rules with their discretion, ratio definitions, non-GAAP adjustments, nominee / client-asset holding).
- Struck text is kept as struck evidence (`~~…~~`) and never applied as active terms (Nexstar).
- A generic document class or framework ("any Finance Document", "U.S. GAAP") is not a reference; a block's pointer to
  itself is not a reference; a specific unsigned-URL agreement is (unresolved).
- Literal money with no printed multiplier: scale `1` (G1). Counts under a money-only multiplier: scale null + flag (G20).
- Currency keeps the literal sign; an explicitly stated code (USD) stays in its own field (unit line, footnote).

**Uncertainty:** `CLAUDE_KEY_FLAGS.json` → `uncertain` lists 16 field entries. 5 fields on 5 targets are excluded from
scoring (`scoring: excluded`, that field only); the others accept both readings. Report the exclusion count with every
score. All 457 targets stay in the inventory.

**What this key cannot prove (Codex S01):** these targets do not test full causal chains, continuation recovery,
transitive definitions or document-wide rounding; their source links are kept, but such capabilities need separate tests.
No claim of full-document recall follows from a score on this key; "457 verified" is coverage, not an accuracy estimate.
The bulk key has 300 HTML cells, 30 XML values, 116 HTML structure targets and 11 PDF structure targets. It has no
PDF table-cell targets and no non-null ranges. The separate development supplement adds known trial cases; remaining
coverage requirements and its exact status are recorded in `converter_checks/README.md`. Never count those reused
trial cases as fresh held-out validation or quietly combine their scores with the bulk sample.

## Scoring the two labelling models (historical, not the converter contract)
Each job is scored against the guide it received (TASK.md `1c0a88a9…` for the first three packets, `f78e535e…` for the
34 bundles). **An old key's acceptance does not make an answer correct.** Apply compatibility exceptions only to
documented changes in the issued rule, with the affected field and rule recorded. Confirmed examples: scale `null`
for literal money with no printed multiplier (Codex R16), and omission of a run-in section label or sentence caption
(guide 2.1 as issued). Omitting a governing footnote or qualifier remains an error where §§3.6/3.8 already required
it; American Airlines T03's old empty footnote list is not grandfathered. Any unresolved rule-version question must
be reported separately before publishing model rankings. Converter scoring uses only the current key and its flags.

## Verification (owner order 2026-10-02): `CLAUDE_VERIFIED.json`, written only by `claude_verify.py mark`
Each finished record is checked by Claude field by field against the original; corrections go through
`claude_decide.py` first. `python3 claude_verify.py status` shows verified / STALE (changed after the check) / unverified.
- **Extra check 1 — full text** (`claude_textcheck.py` → `textcheck_report.txt`): every quoted string in every key field
  and alternative is searched in its source (spacing ignored; `~~` and ` | ` display marks allowed), and every
  `{text, anchor}` pair is compared with the source bytes. All 65 remaining flags were checked by hand (page pictures
  read, stacked headers rendered, page breaks, footnote marks): every flagged string is right, but reviewing them exposed
  one real error elsewhere in a record (Dycom slide 5: a missed footnote reference) and the auto-accept weakness behind
  the evening sweep.
- **Extra check 2 — screen headers** (`claude_screen_all.py` → `screen_all.json`): every HTML cell target is rendered in
  headless Chrome and the cells above the value that cover it on screen are compared with the key's header_path.
- **Full-key re-run (2026-10-02 ≈20:35–20:54, 445 records; bundles 023–034 added):** text check `textcheck_report_445.txt`:
  42 new lines, all explained (28 = an XML name's anchor is its opening tag; struck-text marks; stacked headers; footnote
  marks kept out of titles; the Ford slide is a picture; Matador's second alternative anchors contain, not equal, the phrase
  — as bundle-011/015 before; the CleanSpark apostrophe, see E8). On-screen header check over all 300 HTML cell targets in
  both directions (covering headers missing from the key; key headers not above the value): 1 error, fixed (Cigna T01 lacked
  the spanning 'Three Months Ended March 31,'). Nearest-heading sweep over all HTML targets: 1 error, fixed (Robinhood T02/T03
  lacked 'Net Interest Revenues'). Both errors were agreed by the two models. Result: 445/445 verified.
- **Reconciliation with Codex's independent review (2026-10-03, after Claude's freeze FROZEN_CLAUDE_REVIEW_20261002_2210):**
  48 records changed (`decision_batches_reconcile_codex.json`, `decision_batches_reconcile_v3.json`): Codex's 17 exact
  corrections all verified against the originals and applied; its groups 91, 124, 125, 158, 173, 190, 213, 331, 360–365
  applied as recorded; V13 revised and V3 tightened (see CLAUDE_GUIDE_ISSUES.md); two automatic alternatives found by the
  builder audit decided. Record-level constraints and source contradictions: `CLAUDE_KEY_FLAGS.json`. Full list:
  `FINAL_CHANGE_LOG.md`.
- **Evening sweep:** every field where the key had auto-accepted both models' answers (79 empty-vs-filled + 165 others)
  was decided by hand (`decision_batches_verify_sweep1-5.json`); reasons cite rulings V1–V12 in CLAUDE_GUIDE_ISSUES.md.
- **Codex final check pass (2026-10-03):** all 79 record-specific cases of Codex's final review (55 F, 7 U, 16 R, 1 S) were
  answered one by one (`FINAL_CHANGE_LOG.md` → per-case table): applied, already satisfied, or disputed with the original.
  211 fields on 149 records changed against the 22:36 key (`final_pass/batch_final.py`, a one-time script that asserts every
  new phrase and anchor against the source and now refuses to run again). Builder hardened (no automatic alternatives, strict
  compare, every accepted transcription must hold content); the rebuild reproduces the key byte for byte.
- **Codex's review of that batch (same day):** Primerica T07 now requires the dated heading (a structure record has no
  periods to keep the date); the builder rejects an empty or null accepted transcription even beside a good one (fixtures
  in `final_pass/check_acceptance.py`); the whole-record scan keeps negation and quantifiers and a second check flags meaning
  differences a word list cannot see (negation, sign, case, period roles, strike-through, reference destination) — both
  are candidate finders, every hit reviewed (`final_pass/loss_review.json`, `final_pass/semantic_review.json`). All 138
  text-check lines carry a written disposition (`final_pass/textcheck_dispositions.json`). Every changed record was read
  against the original text at each field's governing location (`final_pass/REVERIFY_SHEET.md`, from
  `KEY_SUPPORT_MAP.json`) and only then re-stamped: 457/457 verified.

## Running this frozen package
The key, tests and helper code live here. `FINAL_MANIFEST.json` declares `evidence_root` relative to this folder;
originals and raw answers remain in that shared bulk root. Resolution starts from each script's `__file__`, never
the working directory. Run `python3 -B /absolute/package/path/VERIFY_PACKAGE.py` first; it verifies all declared
packet/source/raw hashes. The support test also verifies packet manifests and source hashes, and uses no model
output directory. Run it with the project's Python environment (Pillow, lxml and Poppler required).

`CODEX_VALIDATION_0729_20261003.json` records a fresh check of the actual 0729 package. The earlier validation
file is historical and still names the 0005 run it actually performed. This package's post-freeze result is kept
outside the immutable folder, linked in `CODEX_ROUND2_UPDATE_20261003.md`.
