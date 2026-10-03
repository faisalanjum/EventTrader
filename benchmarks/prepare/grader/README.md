# grader — Step 3 part 5 checker

Scores a conversion route's output against the frozen Step 3 answer key. Design, common output format and checks:
[DESIGN.md](DESIGN.md). Self-contained: standard library only, nothing in `driver/` or `tests/driver/` is used or changed.

Tests (from the repository root):

    python3 -B -S -m unittest discover -s grader/tests -t . -v

Grade a route (one JSON per source file at `<route dir>/<file_id>.json`, format in DESIGN.md §2):

    python3 -m benchmarks.prepare.grader.grade \
      --key /home/faisal/prepare_work/step3_sample_20261002/bulk_20261002/FINAL_KEY_FOR_CODEX_20261003_1134 \
      --route <route dir> --out <out dir>            # add --heldout-detail only for the independent checker

| File | Role |
|---|---|
| `anchor.py` | visible text of an original with byte spans; linker that places a tool's output back in the original; `norm`/`squash` comparison forms |
| `grade.py` | loads the key package, finds every target in the route output, runs the checks, writes `results.jsonl`, `summary.json`, `summary.md` |
| `adapters/` | one small file per conversion route (tool output → common format + shared linker); `docling_html.py` (`--prestep-headings`), `edgartools_html.py`, `docling_pdf.py`, plus the route-side steps `prestep_headings.py` and `screen_grid.py`. Run under the tool's own environment: `<docling python> -m grader.adapters.docling_html --key <pkg> --split development --out <run dir>` |
| `tests/` | 100 tests: a correct hand-made output passes everything; each planted fault fails only its own check |
| `checks/why.py` | explains a run's failures: key value vs what the route carried at the key's anchors (`python3 -m benchmarks.prepare.grader.checks.why <run dir> [check:reason]`) |
| `checks/real_pairs.py` | the 7 contract pairs + 8-case supplement on the frozen originals, plus the six development faults from Codex's review (48 variants): `python3 -m benchmarks.prepare.grader.checks.real_pairs` (needs Poppler's `pdftotext`); results in `checks/RESULTS.json` |
