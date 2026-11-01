# Prepared SEC extraction

This build keeps the existing HTML/XML extraction and adds optional, self-hosted
Chandra reading of embedded images and every PDF page. Other companion files are
kept intact. Committing, building or pushing it does not activate production; the
final switch and shared Redis persistence change remain an owner decision.

OCR output is **unverified model output**. A completed request is not a claim of
correct numbers or complete meaning. Known errors include ratios read as percent
signs and invented chart values. Preserve the source and reading together; downstream
consumers must check `fidelity`, not use `status: complete` as an accuracy guarantee.

## Exact release

- OCR integration image: `faisalanjum/report-enricher@sha256:93707585439aa85f6350e5d430b35a5c65f33aaef48e30c8fea67de7de478260`.
- Previous OCR image (31 October qualification): `faisalanjum/report-enricher@sha256:7d1be4640e4806a526c62b5d5a92808940a7e49fb5367d049502c91ee40ddd70`.
- Earlier HTML/XML-only image: `faisalanjum/report-enricher@sha256:f72f3a014007e8dca8e4909a5747814c5304315fa1c27b715a0ca925e1455b7b`.
- Runtime manifest SHA-256: `105890dce16aa9737ada2c71674f4bdaa6510e409f2b45f20213c56049ef5bb2`.
- Environment base: `faisalanjum/report-enricher@sha256:23ca15adc2b1f265ec862a1af2bfa471cc525a6b18b25524049b044803c6236b`.

The 1 November image updates only `driver/prepare/README.md` and its manifest.
All executable runtime, adapter and worker bytes are unchanged. Its exact 48-file
inventory and 37 adapter tests, including the three recorded native cases with
networking disabled, passed. It inherits the bounded OCR findings in
[OCR_QUALIFICATION.txt](OCR_QUALIFICATION.txt); no new model accuracy claim or
production activation follows from this documentation rebuild.

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
configuration. The checked-in deployment patches pair the new image with its exact manifest.
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
The technical retry does not repeat successful HTML/XML extraction.

After an isolated RunPod test, **delete** the Pod and any test-created volume;
stopping a Pod may retain paid storage. Verify the account has no remaining test
resources. Production needs a running OCR server while the OCR option is enabled.
Omitting `ocr` retains the existing HTML/XML-only behavior; also omit the unused
`VLLM_API_KEY` Secret reference in that case.

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
and reason in `reports:queues:enrich:dead`. The original HTML/XML receipt is under
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

The immutable detailed evidence is retained outside Git under
`/home/faisal/prepare_work/extraction_closeout_20261010/production_qualification_20261022/`:
`ROOT_PRELIVE_HEADER_20261031T121050Z/`, `ROOT_PRELIVE_20261031T043600Z/` and
`AUTOMATIC_BROWSER_RECOVERY_20261031T114638Z/`. Keep required fixtures in the existing
`PREPARE_TEST_DATA` store; see `tests/driver/prepare/README.md`. Model weights, raw
filing collections and trial outputs do not belong in this source commit.

The OCR integration adds a 48th runtime file. Its exact image qualification and
source-comparison results are recorded in `OCR_QUALIFICATION.txt`; known model
errors remain explicit. Live activation and a real-arrival canary are still pending.
