# Comparing conversion tools

**Goal:** preserve the original evidence and its relationships, in a small, useful reader input. Keep the existing
reference key; do not require Docling, EdgarTools or another tool to emit its annotation JSON.

## What is scored

| Stage | Check |
|---|---|
| T1 / Step 4, code only | Correct text/value, row and column association, order, headings, printed unit/period/qualifier evidence, footnotes, references and source locations survive conversion. |
| T4 / Step 8, fixed AI reader | The reader interprets that evidence into the correct facts and stated causes. Semantic fields in the key are the expected meaning, not mandatory native converter fields. |

1. Freeze source bytes, tool/settings, input route and key version. Retain raw converter output separately from any adapter.
2. Map output evidence to the key's source occurrences. Matching words anywhere in a document is insufficient.
3. Grade equivalent representations equally. Several output blocks may represent one target, or one cell may join
   several original symbol/value cells. Require the same content and associations, not identical block IDs or JSON.
4. The grading adapter must not fill missing evidence from the original/key. If source-based preservation or repair
   is part of the candidate preparation route, declare and score the whole route; show raw-converter results separately.
5. Keep content and interpretation scores separate. Report per format/capability, excluded fields, unsupported files,
   unresolved mappings, reader tokens and total time. Preserve all five bulk-key field exclusions. A successful
   conversion return code, a word overlap score or valid JSON is not a correctness score.

## Equivalence limits

- Use the key README's E1–E17. Preserve negation, numeric signs, units, conditions and relationships.
- Evidence may use original byte spans, page regions, cells or mapped item IDs. Record the mapping; exact coordinate
  equality is unnecessary when both locations identify the same occurrence and scope.
- A scanned page may become multiple paragraphs/tables rather than one `image` item. Test recovered content and
  order; source-block classification and output segmentation are different things.
- XML prefixes may differ; expanded names retain the same namespace URI and local name. A renamed output property
  needs an explicit mapping. Keep the correct reporting-person occurrence, not just a matching number.
- Never infer a missing year, multiplier or label from the answer key. Preserve literal evidence and grade later
  interpretation separately. Excluding an ambiguous interpretation does not waive preservation of its printed text.

## Round 2 contract clarifications

**E8 (B1).** Typography only: retain the existing allowance for same-function dash glyphs; fold curly/straight glyphs within the same quote class. Keep single versus double marks, apostrophes, measurement marks and meaningful punctuation distinct. Never fold negation, numeric signs, ranges or unit case.

**E2 (B2).** Ignore a heading's continuation marker on either side of comparison, only for the same heading and scope. It never removes body text or resets scope.

**E11 (B3).** A footnote may occupy text blocks, table rows, a one-cell table, or separate marker/body blocks. Require the complete note and correct marker-to-note association. A matching note elsewhere, a wrong note link or a marker glued into a number must not pass.

**E12 (B4).** Compare ordered, source-mapped pieces of the same passage together, using the order and boundaries retained by the output (including its geometry or mapping). Verify them against the rendered source; never use the key to invent a joiner or restore missing text. Segmentation alone is not a fault, including fragments within a word when adjacency is retained without an inserted separator. Whitespace reflow is allowed only when word/number boundaries and table associations survive. A lost word boundary or an inserted space inside a word must fail; unresolved joins stay explicit.

**E13 (B5).** A cell may hold the title plus the record's own basis/unit text. It passes when each required piece stays identifiable, complete and attached to the same table; grade each piece in its own check. Do not drop other parenthetical text, qualifiers or extra units.

**E14 (B6).** Header scope comes from the rendered source. Accept any representation that preserves the correct association (grid, geometry or explicit association); otherwise count a miss. Source-aware repair is a declared candidate route, scored separately; the grader never repairs from the key.

**E15 (B7).** Each period part must govern the target: column headings by column, time printed on the target's row by row, and preceding time headings by their containing row group until that scope ends. A lower-level subheading or an unrelated label does not by itself end the containing time scope. A new competing group must not inherit the old group's date. Left-column placement alone establishes none of these associations.

**E10 (B8).** Long transcriptions are strict; word error rate is a diagnostic, never a pass rule. A furniture exclusion requires a reviewed source anchor declared in this key version, must apply equally and must be reported. There is no automatic waiver for page numbers, headers or logos. Without a declared exclusion, retain the text.

**E16 (B9).** Grade visible-text targets against rendered content. Exclude only proved non-rendered content from that channel and report its size; retain/account for structured metadata separately. Font size alone does not prove a subtree invisible: a zero-size wrapper can contain visible children, and 1-point text is not automatically invisible. A visibility:hidden ancestor can have visibility:visible descendants; do not discard them. OCR must correspond to visible image content; generated titles are not original evidence. Uncertain visibility remains explicit.

**E17 (B10).** Declare each route's supported formats. Keep all 30 XML targets and count unsupported XML explicitly. HTML-only results compare HTML performance only and cannot select the complete pipeline. Test an approved tool-based XML route before pipeline selection; no custom XML converter.

## Required checks before using the grader to rank tools

Pair each valid case with a damaged copy that must fail for the stated reason. Run these against the actual grader
and adapters when built in Step 4; the list is a specification, not a claim that this grader already exists.

| Valid representation must pass | Damaged representation must fail |
|---|---|
| Berry T05: symbol cells joined into `$(506)` with the same row/period | Parentheses/sign removed, or attached to a different row/year |
| Aflac T03: five stacked header fragments joined or kept separately | `Excluding` lost, or the header assigned to the adjacent column |
| UDR PDF target linked to its table row, column and page | Correct number under a different row/column; missing page/table |
| Darden low/high scenario and range endpoints kept with their roles | Endpoints flipped, minus sign lost, or a footnote digit joined to EPS |
| Full scanned-page text split into ordered output blocks | A block, negation or referenced destination omitted |
| XML namespace prefix changed with identical expanded names | Value moved to another reporting person, namespace or field |
| Same source reference expressed with a faithful shorter phrase | Different target, relation or resolved/unresolved status |

**Coverage:** the 457 bulk targets are not a full-document or everyday-accuracy test. Use the development supplement
in [converter_checks](converter_checks/README.md), then the planned T7 and held-out tests. Unsupported formats remain
explicit gaps. Do not expose held-out answers to converter builders or choose test targets from converter output.
