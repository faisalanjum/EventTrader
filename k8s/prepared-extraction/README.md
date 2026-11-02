# Prepared SEC extraction

This build keeps the existing HTML/XML extraction and adds optional, self-hosted
Chandra reading of embedded images and every PDF page. Other companion files are
kept intact. Committing, building or pushing it does not activate production; the
final switch and shared Redis persistence change remain an owner decision.

OCR output is **unverified model output**. A completed request is not a claim of
correct numbers or complete meaning. Known errors include ratios read as percent
signs and invented chart values. Preserve the source and reading together; downstream
consumers must check `fidelity`, not use `status: complete` as an accuracy guarantee.

## Qualified release (not activated)

The 2 November build combines receipt and wrapped-error fixes with prompt browser
crash recovery, one whole-filing deadline and faster package reading. It preserves
the existing extraction format and OCR integration. Readability changes stay in
place; there is no new service, model, document format or storage migration.

- Published image: `faisalanjum/report-enricher@sha256:e0fdcab4ebba79308ced6c80b9ba94cc4067a3f90ed1a55147df73425fa09017`.
- Verified image ID: `sha256:8e17ad0e4a9ffc7cf60e78587c781c7bf87ea1b25834d2118a63b10020edb8fe`.
- Runtime manifest: `8561062f3d2e5fe7d6ca2118799d212f80917a8d41de477893ddfdaf6ff02454`.
- Evidence: `/home/faisal/prepare_cleanup_review_20261031/extraction_deferred_20261102T152805Z/proof/`.
- Registry pull verified this exact image. The review patches pin its matching
  manifest and command; activation remains a separate owner decision.

Final coverage: 2,305 distinct required methods have passing results across the
host and native-image checks. The full 1,676-method Prepare run took 3 h 05 m 03 s;
nine methods failed because three old test browser substitutes lacked `Page.on`.
Only three missing methods on test substitutes were added; every original assertion stayed unchanged.
Both complete affected files then passed all 39 tests in 3.659 seconds. The raw
failed run remains in the evidence; this is a full run plus an affected-file rerun,
not a claim of one uninterrupted green run. Runtime bytes did not change.

Native adapter, worker and crash-retry checks ran on predecessor image
`sha256:ecab567d970190df6edd772a8e7c0d52960349b4521777b989d3cb362c4d621a`.
Its filesystem layers are identical to the final image. The final image restores
the inherited default worker command; separate checks passed for default startup,
explicit Kubernetes arguments and exact runtime, adapter and Tini hashes.
Those command checks use a marker worker; the actual worker passed the tests on
the identical application files above. Original receipts retain their image identities.

Measured HTML/XML extraction on Mini 2: ordinary 8-K 11.861 seconds, large 8-K
16.432 seconds, large 10-Q 408.241 seconds, largest 10-K 587.667 seconds.
All required documents verified. The first three timings use the earlier selective-reader
candidate; the largest 10-K was rerun on the final runtime. Recorded SEC inputs were used
with OCR disabled;
they do not measure live download or full OCR latency. The largest 10-K leaves
only 12.333 seconds under the 600-second budget. First-time script qualification
and large OCR filings have no demonstrated whole-filing timing bound for success.

## Retained previous releases

- Storage image: `faisalanjum/report-enricher@sha256:3e0ac53919cb24a0034c18244398e6666374ba83431259557c7236f3b599a242`.
- Previous table-lookup image: `faisalanjum/report-enricher@sha256:cb980c0daba30dbe61e3d62009daed994a403c50973866af5ccd2af9182d5e6d`.
- Previous OCR image (1 November documentation rebuild): `faisalanjum/report-enricher@sha256:7d057ab66ac7e6ab3b97a31cd2c828b4123df2704a5d395a0e6c17164a089010`.
- Previous OCR image (31 October qualification): `faisalanjum/report-enricher@sha256:7d1be4640e4806a526c62b5d5a92808940a7e49fb5367d049502c91ee40ddd70`.
- Earlier HTML/XML-only image: `faisalanjum/report-enricher@sha256:f72f3a014007e8dca8e4909a5747814c5304315fa1c27b715a0ca925e1455b7b`.
- Storage-release runtime manifest: `f0ac7059e617646cd4a51fe87a8915f4e5c6026a9d5800d7af433401c727074e`.
- Environment base: `faisalanjum/report-enricher@sha256:23ca15adc2b1f265ec862a1af2bfa471cc525a6b18b25524049b044803c6236b`.

The table-lookup change reuses a local source-anchor index and preserves
the existing exactly-one-match rule. The failing R70.htm step now reconstructs in
4.006 seconds and verifies in 3.906 seconds; it previously hit the 240-second limit
on all three attempts. All 1,780 saved outputs from 19 other filings remain byte
identical. A larger 32,768-cell, 256-holder case passed its independent checks.
All 102 affected reconstruction tests, 543 grader tests and three native adapter
cases passed; the exact image's 48 runtime files match the reviewed source.
The earlier full Prepare run passed 1,603 of 1,604 tests. One unchanged browser test,
`ControlIdentity.test_a_swapped_inner_pointer_never_credits_another_label_change`,
exceeded that run's 20-minute test budget. The unchanged `2f0c6a4d` host baseline
subsequently passed all 1,628 methods in 11,656.657 seconds on 2 November,
including all four ControlIdentity methods. Their individual duration was not
recorded; that pass does not establish acceptable production latency.
Evidence and the complete test ledger are retained in
`/home/faisal/prepare_cleanup_review_20261031/storage_review_20261101/`.
In that release the timeout, extraction content and OCR behavior were unchanged; the bounded model
findings in [OCR_QUALIFICATION.txt](OCR_QUALIFICATION.txt) still apply.

Storage verification compared all 1,780 saved outputs through both legacy and
compressed reads: 3,560 exact-byte and native-verification matches. The final image
passed three whole-filing adapter cases and 23 disk-reserve, recovery and OCR
controls, without network or model calls. The storage test ledger separates fresh affected checks
from retained checks of unchanged behavior; it does not claim a fresh full-suite pass.

The later 1 November `set_filing` fix affects the `event-trader` intake service.
Rebuild that service's image before restarting intake. This enricher image contains
the corrected Redis wrapper, but its worker does not call `set_filing`.

Keep these immutable images available. The base retains the tested native packages,
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
configuration. The deployment patch and adapter configuration must name the same
qualified release. Rebuilt images need their own verification; a successful build
does not authorize activation.
Before activation, create the configured `script_qualifications` directory for
this manifest. Keep older directories: their records and claims belong to the
runtime that created them and must not block qualification of this new runtime.
`requirements-ocr.txt` pins the native CPU client dependencies; `cpu-models.sha256`
pins four existing CPU reader weights, loaded into native caches during the build.
The worker image contains no GPU framework or model weights for Chandra.

## Self-hosted OCR server

Use the tested RTX 4090 configuration and immutable server image:
`vllm/vllm-openai@sha256:14ea8b431aaaf75eb873c46c8ebfbad2b4b0790d30c66126d789d8cb9bd0aab9`.
Set a fresh private `VLLM_API_KEY` on the server. Use container disk only for a
short test, expose HTTP port 8000, and run the native command:

```sh
vllm serve --model datalab-to/chandra-ocr-2 \
  --revision af93b47dba1b47b6640c86ccf487ed2260ab9a09 \
  --served-model-name chandra --dtype bfloat16 --no-enforce-eager \
  --max-num-seqs 16 --max-model-len 18000 --max_num_batched_tokens 2048 \
  --gpu-memory-utilization .85 --enable-prefix-caching \
  --mm-processor-kwargs '{"min_pixels":3136,"max_pixels":6291456}'
```

Before activation, confirm the launched image, revision, GPU and settings against
`adapter-config.yaml`; `/v1/models` alone cannot establish the model revision.
Wait for the server to be ready and keep it running while the OCR option is enabled.
Check that a request without the key is refused and an authenticated `/v1/models`
request lists `chandra`. A cold or restarting server can exhaust three quick
attempts; exhausted filings remain in the existing dead-letter list for replay.
Replace `REPLACE_WITH_POD_ID` in that file with the running server's Pod ID. Provide
the same API key through the `prepared-ocr` Kubernetes Secret's `api-key` value;
`worker.patch.yaml` passes it as `VLLM_API_KEY`. Never put a key in the adapter JSON,
URL, identity or repository. This release uses no hosted OCR API. Mac automation
and automatic GPU allocation are outside this release.

The native Chandra 0.2 client supplies its prompt, image sizing and generation
request. A small integration uses the native SDK's streaming response to avoid
proxy idle timeouts and retain the finish reason and token usage. It does not
retry or reinterpret model content. A cutoff or repetition remains incomplete;
a dropped stream remains a technical failure. The adapter allows three total
OCR attempts, retaining good saved readings. Each child's time budget is the
base `seconds` plus `timeout` for each distinct image input and each PDF page.
The technical retry does not repeat successful HTML/XML extraction. All these
attempts share the caller's whole-filing deadline described below.

After an isolated RunPod test, **delete** the Pod and any test-created volume;
stopping a Pod may retain paid storage. Verify the account has no remaining test
resources. Production needs a running OCR server while the OCR option is enabled.
Omitting `ocr` retains the existing HTML/XML-only behavior; also omit the unused
`VLLM_API_KEY` Secret reference in that case.

## Operating boundary

New `ROUTE.json` and `R.json` records use the existing gzip compression. Their
decoded bytes and hashes stay unchanged; older plain files remain readable.
Each receipt still requires its own pinned runtime. The caller removes temporary
before/after-input snapshots only after all required readings verify. Failed,
incomplete and fallback evidence stays. Required outputs and new directory entries
are flushed before completion; a failed flush cannot count as a finished job.

New extraction and OCR attempts check the native 16% free-disk reserve, including
cached filings and retries. Existing saved-result verification remains available.
Measured historical HTML/XML storage scenarios are 305–332 GB allocated, excluding
additional OCR, graph growth and failed attempts; these are estimates, not upper bounds.

Historical replay should reuse the existing Mini 2 archive through read-only
version/blob mounts and a private copy of its HTTP metadata, with live fetching off.
That layout passed a native cached-filing control without requests or new blobs.
Check one cached filing on the exact Mini 2 mounts before starting backfill.
The normal new-arrival configuration below retains writable acquisition.

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

The worker retains a claimed input until publication and acknowledgement. Adapter
jobs, OCR requests and crash deliveries each have separate bounded attempts. A
failed receipt pointer itself schedules no retry: legacy enrichment still publishes,
and the full original input/reason remains in `reports:queues:enrich:dead` for
explicit replay. `filing_seconds` is the total caller budget, starting before
configuration is read and including acquisition, qualification, all retries, OCR
and final receipt validation. It defaults to 600 seconds. A positive number or
form map such as `{"8-K": 120, "default": 600}` is accepted; amendments use the
base form. The review configuration keeps 600 for all forms, including OCR:
the retained warm AMG OCR run took about 274 seconds, so a 120-second total would
reject it. These are safety limits, not guaranteed completion times. Large OCR
workloads can exceed them and must remain failed; do not count a cutoff as fast
successful extraction. Actual HTML/XML and complete OCR timings are separate.

At the total deadline the worker stops its owned process tree; the image's native
Tini process reaps exited descendants. Keep the matching command in the Kubernetes
patch, since Kubernetes overrides the image entry point. A native renderer crash
invalidates the attempt promptly and the existing job retries it. Script-check
ownership uses a local filesystem lock released on exit; only completed verdicts
remain. Use a new qualification directory for each runtime, as above.

The original HTML/XML receipt is under
`runs/<accession>/*/*/RECEIPT.json`; with OCR enabled, the published pointer names
the combined receipt under that run's `ocr/receipts/`. Preserve both receipts,
original files, OCR records and source/version identities together.

The image uses the active application under `/app`; both older checkouts under
`/app/src/eventtrader` and `/app/venv/src/eventtrader` are removed from its filesystem.
Package metadata points to `/app`, with the same package version and requirements.
The active `/app/redisDB/ReportProcessor.py` still supplies fields used by the
existing consumer. There is one current `driver.prepare` tree, under
`/opt/prepared/runtime`, and no older Prepare/test/grader tree in the image.

## Qualification record

The preceding HTML/XML-only cleanup image passed all 23 worker checks with an isolated Redis and imported
its real worker without test substitutes. Its 47 runtime files and the adapter,
worker, Redis wrapper, active legacy processor, native library and browser retain
their qualified hashes. Package resolution and effective dependencies were checked
independently. Earlier extraction qualification therefore remains applicable.

The preceding extraction snapshot passed 1,116 affected tests without skips. A complete
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

The detailed evidence is retained outside Git in
`/home/faisal/prepare_cleanup_review_20261031/preserved/SEC_RELEASE_PROOF_20261101.tar.gz`.
All 81,141 archived files passed a full restore and hash check. Its `_restore/`
directory records original paths, runtime sources and separately retained native
inputs. Extract into an empty review directory; historical replay needs those
external inputs too. Keep required fixtures in `PREPARE_TEST_DATA`; see
`tests/driver/prepare/README.md`. Model weights, raw filing collections and trial
outputs do not belong in this source commit.

The OCR integration adds a 48th runtime file. Its exact image qualification and
source-comparison results are recorded in `OCR_QUALIFICATION.txt`; known model
errors remain explicit. Live activation and a real-arrival canary are still pending.
