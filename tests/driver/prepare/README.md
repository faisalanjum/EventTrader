# Permanent Prepare regressions

**Migration in progress (7 October 2026).** Integrated base `5d25539d1`
has 384 permanent tests. The shared fixture helper adds 12 (396 pass, no skips).
The 506-input OCR fixtures and 576 saved-packet data are pinned and restored from
a separate machine. Their permanent test ports are still pending; this command
is not yet the complete Prepare acceptance gate.

From the repository root, in the approved preparation environment:

```bash
export PREPARE_TEST_DATA=/home/faisal/prepare_test_data
/home/faisal/prepare_work/venvs/prepare-tests/bin/python -m unittest discover -s tests/driver/prepare -t . -v
```

Keep `unittest`, already used by the downloader and grader. No new test framework,
scoring engine or orchestration service. The full command includes browser tests,
saved-reading replays and failure/restart tests; it makes no SEC or model calls.

## Approved offline test environment (7 October 2026)

Use a dedicated **Linux x86_64 / CPython 3.11.10** environment, currently
`/home/faisal/prepare_work/venvs/prepare-tests/`, recreated from
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

Latest qualification used a pinned copy of `d4639b096`: 363 permanent tests and
398 retained grader/converter tests pass with no skips. The suites overlap while
migration is incomplete. Until their retained assertions are fully reconciled,
also run from the relevant checkout:

```bash
/home/faisal/prepare_work/venvs/prepare-tests/bin/python -m unittest discover -s benchmarks/prepare/grader/tests -t . -v
```

Converter coverage begins with the reviewed candidate's integration; do not report
saved-fixture coverage until those tests have actually migrated. Saved-picture replay, current producer
handoff, fixture restoration and target-machine execution remain separate gates.
Environment and validation evidence:
`prepare_work/prepare_regression_20261006/codex_port_review_20261007/` and
`prepare_work/convert_extract_20261007/codex_review/`.

## Location and scope

```text
tests/driver/prepare/
  get/                  existing downloader tests and small fixtures
  convert/              HTML/XML, source links, formatting, tables and images
  pictures/             OCR comparison, packets, readers, workers and saved replays
  test_compare.py       shared comparison rules, tested once
  test_handoff.py       downloaded source -> conversion -> OCR -> consumer receipt
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
`prepare_work`; 2,319 asset references / 2,253 unique blobs (168,878,153 original
bytes) are provisioned. The checked-in manifest pins this exact snapshot; its
draft-status text records the inventory's creation, not current provisioning. Reuse get's content-addressed
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
storage and prove restoration into an empty directory. Record the actual backup
location here during migration. This snapshot was backed up on **minisforum2**, under
`/home/faisal/prepare_test_data_backup/7b8cdc07f7237b68b73b1466d4348fd17c8b71cd060580fa479145134f621e3a/`,
and restored into an empty directory with every asset's original SHA-256 and
length checked using both stdlib gzip/hashlib and the loader. The backup uses a
different machine from the primary store on minisforum. Its helper pod is
transient; the host directory is durable. Evidence: `prepare_work/prepare_accuracy_20261007/fixture_support/`
(`PROVISION.json`, `BACKUP.json`, `RESTORE.json`). A directory name or symlink alone
is not a backup. Retain old evidence until all required ports and clean-checkout
checks pass. Unreleased held-out answers do not enter this store.

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
