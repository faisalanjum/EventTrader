# Prepared SEC extraction

This directory preserves the qualified HTML/XML worker's build inputs and manual
operating instructions. Committing or building it does not activate production.
The final live switch, including the shared Redis persistence change, remains an
owner decision. OCR/PDF reading remains disabled; other companion files are kept
intact.

## Exact release

- Qualified image: `faisalanjum/report-enricher@sha256:e8ca7a5887dcce986f18b377917fa1e4a07c0684c2e6edfc15e2010978a27adc`.
- Runtime manifest SHA-256: `d4aaffdee5d99748cb370d172c024f966aae5fb32c773f12f1b36671ee09804a`.
- Environment base: `faisalanjum/report-enricher@sha256:23ca15adc2b1f265ec862a1af2bfa471cc525a6b18b25524049b044803c6236b`.

Keep both immutable images available. The base retains the tested native packages,
Chromium and fonts; the Dockerfile copies the reviewed repository source into their
existing locations. The Docker-specific allowlist excludes unrelated application
files, credentials, tests, archives and caches from the build context. The legacy
`Dockerfile.enricher` is a separate build and does not reproduce this release.

Build from the repository root:

```sh
docker build -f k8s/prepared-extraction/Dockerfile -t sec-prepared-enricher:local .
```

A rebuild has its own image identity and is not automatically the qualified image.
Verify its runtime against `RUNTIME_MANIFEST.json`, plus the worker, Redis wrapper,
adapter and browser, before changing deployment pins. A source change requires a
new reviewed manifest/image pair; never combine this image with an older manifest
configuration. The checked-in deployment patches still name the qualified image.

## Operating boundary

Run the operating instructions from `k8s/prepared-extraction/`:

- `ROLLOUT.txt`: prerequisites, one-worker ownership and result observation.
- `REDIS_AOF.txt`: the approved sequence for online persistence conversion before
  the shared Redis restart and worker switch.
- `ROLLBACK.txt`: stop the worker, return retained claims, then restore its captured
  previous deployment revision. Redis stays on durable persistence.

These are manual guides, not scripts to execute during a build or test. Preserve
their stop-on-error checks and bounded waits. Recheck the actual deployment,
queues, idle worker, storage and scaler settings at activation; historical values
in evidence are not live-state guarantees. `BEFORE_WORKER_REVISION.txt` is created
at that time and is deliberately not committed.

Qualified operation has **one extraction worker**, a writable home directory and
the image's existing root user. Runtime code is under `/opt/prepared`; persistent
output is `/data/sec_prepared` in the container, mounted from
`/home/faisal/data/sec_prepared` on `minisforum2`. The host directory must exist with
the required access and free-disk reserve. Changing user, ownership, storage paths
or worker count needs a focused validation; it is not part of source consolidation.

The worker retains a claimed input until publication and acknowledgement. Technical
failures permit three total attempts; exhausted work keeps the full original input
and reason in `reports:queues:enrich:dead`. Saved successes can be found under
`runs/<accession>/*/*/RECEIPT.json` beneath the configured output directory. Preserve
the saved original files, source/version identities and receipts together.

The inherited base still has older copies of the wider application under
`/app/src/eventtrader` and `/app/venv/src/eventtrader`. Their cleanup is open and
separate from this source import. Two old `redisDB/ReportProcessor.py` copies are
shadowed by the active `/app/redisDB/ReportProcessor.py`; the active processor still
supplies fields used by the existing consumer. Do not delete entire old checkouts
without checking their unique files. There is one current `driver.prepare` tree,
under `/opt/prepared/runtime`, and no older Prepare/test/grader tree in the image.

## Qualification record

The final extraction snapshot passed 1,116 affected tests without skips. A complete
saved-output comparison covered 954 HTML documents, 1,813 native views and 602,977
table cells. The table-header clarification preserved native guesses and all other
payload. The proposed spacing change was rejected after it split a real list item
into a marker and guessed heading; native spacing and heading code are unchanged.

The earlier fixed 1,000-file run retains its actual result: 999 verified and one
browser-start failure, followed by a successful separate recheck. Fresh 200 passed;
32 source comparisons found no demonstrated material loss. Controlled actual-worker
tests separately proved automatic recovery after a temporary browser crash and
retention after persistent failure. These proofs do not establish perfect accuracy
for every future filing or current live-traffic performance.

The immutable detailed evidence is retained outside Git under
`/home/faisal/prepare_work/extraction_closeout_20261010/production_qualification_20261022/`:
`ROOT_PRELIVE_HEADER_20261031T121050Z/`, `ROOT_PRELIVE_20261031T043600Z/` and
`AUTOMATIC_BROWSER_RECOVERY_20261031T114638Z/`. Keep required fixtures in the existing
`PREPARE_TEST_DATA` store; see `tests/driver/prepare/README.md`. Model weights, raw
filing collections and trial outputs do not belong in this source commit.
