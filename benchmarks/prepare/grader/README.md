# grader — Step 3 part 5 checker

Scores a conversion route's output against the frozen Step 3 answer key. Design, common output format and checks:
[DESIGN.md](DESIGN.md). Self-contained: standard library only, nothing in `driver/` or `tests/driver/` is used or changed.

Tests (from the repository root):

    python3 -B -S -m unittest discover -s benchmarks/prepare/grader/tests -t . -v

Grade a route (one JSON per source file at `<route dir>/<file_id>.json`, format in DESIGN.md §2):

    python3 -m benchmarks.prepare.grader.grade --route <route dir> --out <out dir>   # --key defaults to the package named in golden/PACKAGE.json; add --heldout-detail only for the independent checker

| File | Role |
|---|---|
| `anchor.py` | visible text of an original with byte spans; linker that places a tool's output back in the original; `norm`/`squash` comparison forms |
| `grade.py` | loads the key package, finds every target in the route output, runs the checks, writes `results.jsonl`, `summary.json`, `summary.md` |
| `adapters/` | one small file per conversion route (tool output → common format + shared linker); `docling_html.py` (`--prestep-headings`), `edgartools_html.py`, `docling_pdf.py`, plus the route-side steps `prestep_headings.py`, `screen_grid.py` (cell geometry from headless Chrome) and `source_formatting.py` (the source's own strike-through — `<s>`/`<del>`/`<strike>`, CSS `line-through` — written onto units and cells as `struck`; `--key <pkg> --route <dir> --out <dir>`, run after the converter and before the screen step, always into its own route folder so the converter's own output stays graded beside it; where the source's decoration cannot be certified the converter's claims are left as they are). Run under the tool's own environment, from the repository root: `<docling python> -m benchmarks.prepare.grader.adapters.docling_html --key <pkg> --split development --out <run dir>` (`--reuse-raw` re-links saved tool output after a linker change) |
| `tests/` | unit tests (`python3 -B -S -m unittest discover -s benchmarks/prepare/grader/tests -t .`): a correct hand-made output passes everything; each planted fault fails only its own check; every reviewer finding has a test |
| `checks/why.py` | explains a run's failures: key value vs what the route carried at the key's anchors (`python3 -m benchmarks.prepare.grader.checks.why <run dir> [check:reason]`) |
| `checks/real_pairs.py` | the 7 contract pairs + 8-case supplement on the frozen originals, plus the six development faults from Codex's review (48 variants): `python3 -m benchmarks.prepare.grader.checks.real_pairs` (needs Poppler's `pdftotext`); results in `checks/RESULTS.json` |
