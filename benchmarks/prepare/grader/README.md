# grader — Step 3 part 5 checker

Scores a conversion route's output against the frozen Step 3 answer key. Design, common output format and checks:
[DESIGN.md](DESIGN.md). Self-contained: standard library only, nothing in `driver/` or `tests/driver/` is used or changed.

Tests (from the repository root):

    python3 -B -S -m unittest discover -s benchmarks/prepare/grader/tests -t . -v

Grade a route (one JSON per source file at `<route dir>/<file_id>.json`, format in DESIGN.md §2):

    python3 -m benchmarks.prepare.grader.grade --route <route dir> --out <out dir>   # --key defaults to the package named in golden/PACKAGE.json; add --heldout-detail only for the independent checker

| File | Role |
|---|---|
| `anchor.py` | visible text of an original with byte spans (HTML: the stated inline-CSS subset and the text-decoration grammar — an invalid declaration is dropped as the browser drops it, an unevaluated one makes the file uncertain; XML: the strict standard parser's character data — CDATA literal, references decoded, attributes not text); linker that places a tool's output back in the original; `norm`/`squash` comparison forms |
| `grade.py` | loads the key package, finds every target in the route output, runs the checks, writes `results.jsonl`, `summary.json`, `summary.md` |
| `adapters/` | one small file per conversion route (tool output → common format + shared linker); `docling_html.py` (`--prestep-headings`), `edgartools_html.py`, `docling_pdf.py` (native PDFs and HTML printed by headless Chrome; a native page whose text layer Docling's own confidence grades POOR on parsing is converted again alone with full-page OCR and its units take the page's place — the route's own gate, never a file name), `xml_fields.py` (XML forms: one `field` unit per element that carries text, from the standard strict parser — expanded name, ancestors, the containing instance ("n of m" and the byte of its start tag, which tells two first children of two parents apart), the element's own place among its siblings, text, byte span; an element whose own text holds inline elements is one field read whole; attribute values are not read and their count is stated as `not_read`; a malformed document is FAILED, never repaired), plus the route-side steps `prestep_headings.py`, `screen_grid.py` (cell geometry from headless Chrome) and `source_formatting.py` (the source's own strike-through — `<s>`/`<del>`/`<strike>`, CSS `line-through` — written onto units and cells as `struck`; `--key <pkg> --route <dir> --out <dir>`, run after the converter and before the screen step, always into its own route folder so the converter's own output stays graded beside it; it writes a strike only where the source's decoration is fully resolved and no stylesheet rule touches decorations, drops a converter's claim only where nothing is struck and no sheet rule could add one, and otherwise leaves the converter's claim as it is). Run under the tool's own environment, from the repository root: `<docling python> -m benchmarks.prepare.grader.adapters.docling_html --key <pkg> --split development --out <run dir>` (`--reuse-raw` re-links saved tool output after a linker change) |
| `tests/` | unit tests (`python3 -B -S -m unittest discover -s benchmarks/prepare/grader/tests -t .`): a correct hand-made output passes everything; each planted fault fails only its own check; every reviewer finding has a test |
| `checks/why.py` | explains a run's failures: key value vs what the route carried at the key's anchors (`python3 -m benchmarks.prepare.grader.checks.why <run dir> [check:reason]`) |
| `checks/real_pairs.py` | the 7 contract pairs + 8-case supplement on the frozen originals, plus the six development faults from Codex's review (48 variants): `python3 -m benchmarks.prepare.grader.checks.real_pairs` (needs Poppler's `pdftotext`); results in `checks/RESULTS.json` |
