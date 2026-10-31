# Permanent Prepare regressions

**Current execution (21 October 2026).** The permanent suite includes acquisition,
HTML/XML conversion, picture integration and saved-reading replay. Run both commands
below: retained grader assertions have not all been reconciled for retirement.
The freshly checked `cf01ed22b` baseline passed 651 permanent and 402 retained grader
tests without skips; later fixes require their own exact-candidate gate. Independent
scoring, source coverage and actual-machine execution remain separate.

The extraction command uses `prepare-closeout-20261011`: all 74 checked-in package
pins were verified there on 21 October. The older `prepare-tests` environment lacks
the pinned `tinycss2` and `webencodings`; it remains the retained grader environment.
The reviewed `4e47c9e48` runtime passed 940 extraction and 543 grader tests without
skips using these environments. Do not repeat the missing-dependency failure or install
into an environment another agent is using; use the qualified environment below.

**Historical migration receipt (7 October 2026, branch `ocr-fixture-tests`).** Integrated base
`5d25539d1` has 384 permanent tests; the shared fixture helper adds 12 and the
ported OCR fixture tests add 15: **411 pass, no skips**, on the primary and the
restored fixture roots with the original research folders hidden (Codex gate
`prepare_work/prepare_accuracy_20261007/OCR_FIXTURE_GATE.md`). The 506-input OCR
fixtures and 576 saved-packet data are pinned and restored from a separate machine.
This command is not yet the complete Prepare acceptance gate: the fresh combined
converter/image/context check and actual-machine execution remain separate.

From the repository root, in the approved preparation environment:

```bash
export PREPARE_TEST_DATA=/home/faisal/prepare_test_data
env -u PYTHONPATH /home/faisal/prepare_work/venvs/prepare-closeout-20261011/bin/python -m unittest discover -s tests/driver/prepare -t . -v
```

`env -u PYTHONPATH`: the shell exports the main checkout; the tests must import only the checkout under test.

Keep `unittest`, already used by the downloader and grader. No new test framework,
scoring engine or orchestration service. The full command includes browser tests,
saved-reading replays and failure/restart tests; it makes no SEC or model calls.

## Approved offline test environment (7 October 2026)

Use a dedicated **Linux x86_64 / CPython 3.11.10** environment, currently
`/home/faisal/prepare_work/venvs/prepare-closeout-20261011/`, recreated from
[requirements.txt](requirements.txt). This is separate from the application venv,
Neo4j and GPU production workers. The location is disposable; the checked-in pins
are the record. Initial setup may install packages; test runs make no downloads,
SEC requests or model calls.

Pins include EdgarTools 5.60.0, Playwright 1.59.0, RapidOCR 3.9.2, OnnxTR 0.9.0,
ONNX Runtime 1.30.0, NumPy 2.4.6, Pillow 12.3.0, OpenCV 5.0.0.93 and pylatexenc
2.10. Playwright's Chromium 147.0.7727.15 (revision 1217) and the required system
libraries/fonts must be available; missing dependencies fail, never skip. Install
Chromium during provisioning, not from the test command. Tests of OCR engines
use their real loader/configuration code with model execution/downloads replaced.
No MLX, Chandra weights or GPU are needed for this offline suite.

An earlier qualification used a pinned copy of `d4639b096`: 363 permanent tests and
398 retained grader/converter tests pass with no skips. The suites overlap while
migration is incomplete. Until their retained assertions are fully reconciled,
also run from the relevant checkout:

```bash
env -u PYTHONPATH /home/faisal/prepare_work/venvs/prepare-tests/bin/python -m unittest discover -s benchmarks/prepare/grader/tests -t . -v
```

Converter tests are integrated. The OCR saved-fixture tests have
migrated (`pictures/`: the 506-input replay in both modes, 576 saved packets, worker reuse, table
choice and its 546 frozen damages, saved probes, isolation, and the test-consumer handoff on frozen
routes). They preserve saved behaviour; they are not OCR accuracy, and their frozen routes are never
regenerated. `pictures/test_join.py` checks current conversion, picture preparation,
archiving and reader composition with controlled readers. It does not qualify actual
model execution or independently score the full output.
Environment and validation evidence:
`prepare_work/prepare_regression_20261006/codex_port_review_20261007/` and
`prepare_work/convert_extract_20261007/codex_review/`.

## Location and scope

```text
tests/driver/prepare/
  get/                  existing downloader tests and small fixtures
  convert/              HTML/XML, source links, formatting, tables and images
  pictures/             OCR comparison, packets, readers, workers, saved replays, frozen-route handoff
  pictures/test_imports.py  shared comparison identity and runtime isolation
  pictures/test_join.py  current source -> conversion -> picture/reader composition
  pictures/test_handoff.py  frozen-route serialization and test-consumer checks
  support.py            only reused fixture-loading/isolation helpers
  fixtures/manifest.json  large-fixture hashes, provenance and expected-result pins
```

Subdirectories are importable test packages. Tests import the checkout's
`driver.prepare` modules, never code from a research folder or another worktree.
Small cases stay beside their tests. Names describe behavior, not review rounds.
Keep real failing examples plus valid controls; parameterize distinct spellings,
encodings, placements and failures rather than copying the same test repeatedly.

Preserve these contracts:

- **Get:** exact member bytes, framing/decoding and proof decisions; failed inputs;
  atomic storage, corruption/read errors, retries, pacing and crash/restart reuse.
- **Convert:** text and numeric boundaries, headings, units/periods/notes, redlines,
  row/column associations, XML context/namespaces, source positions, every image
  occurrence and its containing text/table. Missing content stays explicit.
- **Pictures:** marks/fractions/negation and table relationships, raw free evidence,
  uncertainty/status propagation, default Sonnet-off isolation, optional-on replay,
  image/settings identity, model-file validation, independent reader retries and
  durable worker results. Agreement must never become proof of accuracy.
- **Handoff:** original image bytes, complete document context and occurrence links
  survive serialization; reused images keep separate contexts; stale/wrong sources,
  keys, modes and missing/incomplete readings have the required explicit outcome.

### Downstream table-context readiness (27 October 2026)

These are required checks for an AI consumer of the saved extraction, not claims
that a production consumer is wired or qualified. Keep the complete ordered
document and source links; assemble reader input without rewriting extraction.

The owner's extraction scale test is preservation: every original number and
unit/scale statement, its meaningful position and its source connections must
survive. Extraction need not assign an unproved multiplier. Test source content
and associations independently of downstream scale interpretation; an unknown
assigned scale alone is not an extraction defect or a reason to invent a value.

The choice between a small target and larger context is deliberately deferred.
Retain the complete saved source/version and ordered pieces once, with their
actual addresses and known references. Quotes, facts and driver updates made
later must retain the original source addresses as well as their own identities.
Keep the existing saved-output/version pin too: piece numbering may change on
re-extraction. Reuse the source/output hashes already carried by the pipeline;
no new identity system is needed. Unknown positions or relationships remain explicit. No new context flag or
semantic splitting step is required now, and the existing 18 August full-event
reader contract stays in force until the owner changes it.

- Check the actual serialized model input, including any retrieval or splitting:
  table cells, row/column headers, captions, linked notes, relevant surrounding
  prose and applicable section/document declarations must reach the reader.
  Include notes below tables and explicit references outside the local section.
- Apply the same check to tables delivered through the picture path, whether
  the reader receives an image, its extracted text/grid or both. Carry each
  occurrence's surrounding document context through to the actual AI input;
  an image-only packet or OCR result is not sufficient evidence of that handoff.
  Reusing identical image bytes or one OCR result must preserve the distinct
  headings, notes and source locations of every occurrence.
- Nearby or earlier scale statements with unproved scope remain attributed
  candidate context. Preserve their exact text, exceptions, location and order;
  proximity, agreement among phrases and an assumed table continuation do not
  prove that a statement governs a value. Different units may correctly govern
  different tables, columns or kinds of value.
- If a table's required context cannot be bounded reliably, widen to the
  containing section or document with its referenced context. Do not silently
  truncate required evidence to fit a model budget. An unresolved association
  or unread required context must remain explicit, including when the full
  document does not fit. Whole-document delivery is not proof of interpretation.
- Verify each resolved value's unit/scale and exceptions against independent
  source evidence. Preserve raw values and native normalized values separately;
  unknown scale is not zero, one or the document's most frequent scale, and an
  already scaled native value must not be scaled again.
- Use independent real examples and positive/negative controls for above/below
  notes, genuine and false continuations, distant declarations, mixed units,
  per-share exceptions, conflicting/missing scope and model-budget boundaries.
  Report content preservation, correct context association and downstream meaning
  accuracy separately, with abstentions, actual prompt tokens and runtime costs.
  Phrase-search coverage alone qualifies none of these measures.

No new parser, semantic rule engine, model call or release credit is authorized
by this checklist. Reuse native structures and existing reconstruction; first
prove any proposed integration on the actual consumer's inputs. Existing reader
contracts that require a complete event still apply.

Retain regression cases for supported PDF behavior already in the runtime; this
does not restart PDF development. Tests of retired routes and grader-only scoring,
rankings, key management or experiment measurements remain with their archived
tools. A production preservation assertion may be extracted from those tests,
but do not import or rebuild the grader to run it.

## Fixtures: small in git, large outside it

Keep the current small downloader fixtures in git (20 files, about 0.56 MB total)
and the small browser cases. Reduce new examples where that preserves the failure;
retain the original when layout, byte offsets or image geometry require it.

Use **`PREPARE_TEST_DATA`**, provisioned once, for large immutable fixture bytes.
The local location is `/home/faisal/prepare_test_data/`, outside git and
`prepare_work`. The main manifest has 2,330 asset references; the observed-controls
manifest has another 100. Together they require 2,340 unique blobs (173,586,617
original bytes). Both checked-in manifests pin the provisioned bytes; draft-status
text records the inventory's creation, not current provisioning. Reuse get's content-addressed
gzip format and `archive.load_blob`: `blobs/<original-sha256>.gz`. No Git LFS,
new cache service or dependency on the live corpus.

The checked-in manifest names each fixture and records its original byte length
and full SHA-256, role (input or expected output), source/member/page or region,
reader settings when relevant, and how the expectation was checked. Input groups
list every member explicitly, including intentionally absent readings; no globs
or mutable `latest` paths determine coverage. Include the existing 506-input OCR
inventory and 576 saved-packet checks, with their actual inputs and approved
expectations, until an explicit coverage review justifies reducing them.

`support.FixtureStore` resolves manifest entries, checks bytes/hashes and materializes
needed files in a temporary directory. Blob-format tests use independent stdlib
hash/decompression checks so the store is not its own only oracle. The fixture
root is read-only during tests; test outputs never overwrite inputs or baselines.
Missing, corrupted or inaccessible required data **fails**, never skips or fetches
from SEC. Tests print the missing asset ID and expected hash.

Before retiring old evidence, copy the pinned fixture store to backed-up persistent
storage and prove restoration into an empty directory. The current snapshot was
backed up on **minisforum2** on 31 October 2026, under
`/home/faisal/prepare_test_data_backup/ad2a1b04300792a1e6fc20f1704e8f9c849fa0786d4ad66ea0db1489af527b24/`.
All 2,340 blobs were restored from that machine into an empty directory and checked
against both manifests using stdlib gzip/hashlib and the native loader. The primary
store was not used during restoration. The earlier October 7 backup remains intact.
Evidence: `prepare_work/extraction_closeout_20261010/production_qualification_20261022/CLAUDE_SEC_GIT_PUBLICATION_20261031/FIXTURE_BACKUP_20261031/`
(`BACKUP.json`, `RESTORE.json`). The backup is on a different machine from the primary
store on minisforum; its host directory persists after the helper pod is removed.
A directory name or symlink alone is not a backup. Retain old evidence until all
required ports and clean-checkout checks pass. Unreleased held-out answers do not
enter this store.

## Stable execution and expectations

- Run against the checkout under test and approved dependency/browser versions;
  record those versions. Required libraries, Chromium and fixtures must be present.
  Remove dependency-based skips and conditional omission of tests. No `skip` or
  `expectedFailure` may hide a required regression. A narrower developer run is
  useful while editing but does not count as the full gate.
- Use injected transports/readers, saved responses and controlled clocks. Browser
  cases use local fixtures, fixed viewport/fonts and blocked external requests;
  process-kill and lock tests run in temporary folders. No paid calls or downloads.
- Preserve the source facts and relationships in expected results. Compare opaque
  bytes exactly; compare structured fields and ordered content explicitly. Known
  timing fields and the temporary-root prefix may be isolated by named helpers;
  never broadly strip numbers, whitespace, paths, errors or status fields to pass.
- Expectations are frozen data, not values calculated by the implementation under
  test or by old experiment code. Read-only replay cannot regenerate them. An
  intentional change includes an original-backed explanation, old/new diff and
  replacement hash in the same reviewed change. Policy changes need owner approval;
  ordinary fixes follow the agreed contract. No blanket baseline refresh.
- Keep known OCR mistakes in saved readings as evidence, with tests of faithful
  output and honest status. A passing replay proves software preservation, not
  that a model read the picture correctly. Unfixed production bugs stay explicit
  blockers, not newly blessed expected answers.
- Test fixed operation/call counts and bounded work where possible; do not make
  shared-machine timing a brittle pass/fail threshold. Hardware latency, model
  accuracy and corpus coverage measurements remain outside this regression suite.

Actual Chandra/OnnxTR execution on new hardware still needs a target-environment
qualification before deployment or a model/provider change. Saved-reading tests
do not replace it. Do not add routine GPU/model calls to the offline command or
describe an offline pass as that qualification.

## Every new finding follows the same short path

1. Freeze the failing input and independently establish the intended outcome from
   the original. Identify the owning production function and the whole failure class.
2. Add a named regression there **before the fix**, with a correct control and the
   relevant neighboring cases. The test's short comment records the cause and source;
   real filing names in fixtures are evidence, never runtime exceptions.
3. Show failure before the fix and success after it. For a changed interface, retain
   the same failure scenario rather than a permanently failing old API call.
4. Make the smallest generic fix, run its focused tests and the full command. Include
   any new blobs and manifest pins with the change; verify they are restorable.
5. Review expected-output changes separately from implementation changes. Keep each
   distinct regression even when several issues share one parameterized test.

## Migration gate

Fable owns converter tests; OCR owns picture/worker tests; Codex coordinates the
shared helper, fixture manifest and overlap review. Do not interrupt current fixes.
Migrate alongside the approved runtime extraction, then finish before cleanup and
release. Keep old checks until their replacements pass on the final combined code.

Use a one-time ledger outside this test tree: each old assertion/review finding
maps to a new test, an exact duplicate of a named test, a retired non-runtime
behavior, or an explicit open issue. No production regression disappears because
its script is called an audit. For each distinct fix, show the migrated test still
catches the pre-fix behavior or a targeted reversal. Consolidate repeated full OCR
replays into one parametrized replay, preserving each assertion and input.

Completion requires: no unmapped findings; all required regressions passing on the
combined checkout; no research/benchmark runtime imports; no skipped required
tests; restored fixtures verified from their backup; and the full command passing
from a clean checkout without the old worktrees or `prepare_work`. The migration
inventory and experiments remain outside this permanent suite.
