# Prepared-extraction adapter and worker tests

Tests for `redisDB/prepared_filing.py` (the adapter), `redisDB/report_enricher.py` (the worker) and `redisDB/redisClasses.py`.
Use three separate lanes; verify source/image pins and collected test IDs:

| Tests | Environment | Needs |
|---|---|---|
| Offline `test_prepared_filing.py` | qualified OCR overlay, CPython 3.11.10 | `PREPARE_TEST_DATA`, including `adapter.r1_verified` |
| Native `AmgEvent` plus recovery/OCR controls | exact candidate image, CPython 3.11.13 | pinned browser and recorded AMG inputs |
| Worker, recovery, initializer and `test_set_filing_dedup.py` | candidate worker image (redis-py) | **disposable** Redis and retained old worker |

Tests that cannot run in the current environment are skipped with the reason printed. A skipped test has not passed.

## 1. Adapter tests (host)

From the repository root:

```bash
export PREPARE_TEST_DATA=/home/faisal/prepare_test_data
env -u PYTHONPATH -u ADAPTER_E2E PYTHONDONTWRITEBYTECODE=1 \
  /home/faisal/prepare_cleanup_review_20261031/ocr_env/bin/python -B -m unittest tests.redisDB.test_prepared_filing -v
```

Current inventory: 50 offline adapter methods and 3 named `AmgEvent` skips.
These are expected counts, not a passing-run claim; close the skips in lane 3.
Do not install into the shared overlay or its retained base. Current results and
historical proof are linked by the [operating guide](../../k8s/prepared-extraction/README.md).

Also run the six deadline controls with the private qualified environment described
in the [Prepare test instructions](../driver/prepare/README.md):

```bash
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 \
  /home/faisal/prepare_cleanup_review_20261031/extraction_deferred_20261102T152805Z/test_env/bin/python -B -m unittest tests.redisDB.test_prepared_deadline -v
```

These check the whole-filing budget and honest late/error outcomes. Native process
cleanup additionally requires the candidate image's Tini entry point: plain Docker
or a Kubernetes command overriding it does not prove orphan reaping. Never count a
timeout as successful extraction, even when all processes stop correctly.

`fixtures/real_receipt.json` is the retained AMG receipt (SHA-256
`cf1b59858bbb012438e3b05f49327f34bb0d0b255a9d6f0eebfd53d42ea64715`). Its old runtime
pin is historical. Pointer tests relocate private copies and cover invalid
bytes/identity/pins, legitimate repeat reclassification and actual OCR aggregates.

## 2. Worker tests (worker image + disposable Redis)

Every Redis test runs `FLUSHALL`. Never point `REDIS_TEST_HOST`/`REDIS_TEST_PORT` at a shared or production Redis.
The commands below put the test Redis on an internal Docker network with no outside access, and remove it afterwards.

```bash
TEST_NET=redisdb-test-net; TEST_REDIS=redisdb-test-redis; TEST_WORKER=redisdb-test-worker
OLD=$(mktemp -d)/report_enricher.py
# Set CANDIDATE_IMAGE to the reviewed candidate image ID from the operating guide.
# previous worker (for the RED proof and the rollback test): taken from image5, never copied into Git
docker run --rm --network none --entrypoint cat \
  faisalanjum/report-enricher@sha256:23ca15adc2b1f265ec862a1af2bfa471cc525a6b18b25524049b044803c6236b \
  /app/redisDB/report_enricher.py > "$OLD"
sha256sum "$OLD"   # must be b36aa7d2a70ddd29aefc24658baf915e28f40537663b06cf5142eae51f75f4b4

docker network create --internal "$TEST_NET"
trap 'docker rm -f "$TEST_WORKER" "$TEST_REDIS"; docker network rm "$TEST_NET"' EXIT
docker run -d --rm --name "$TEST_REDIS" --network "$TEST_NET" --memory 512m \
  redis@sha256:7b5ee51c14cf5febd4adde3a4b6cced72efdf154df7e9a0383163b13e16e9091
timeout 15s sh -c 'until docker exec "$1" redis-cli ping; do sleep 0.2; done' sh "$TEST_REDIS"
timeout --kill-after=10s 600s docker run --rm --name "$TEST_WORKER" --network "$TEST_NET" --memory 4g --read-only --tmpfs /tmp:rw,size=1g \
  -e REDIS_TEST_HOST="$TEST_REDIS" -e REDIS_TEST_PORT=6379 -e ENRICHER_OLD=/old/report_enricher.py -e PYTHONDONTWRITEBYTECODE=1 \
  -e ENRICHER_UNDER_TEST=/app/redisDB/report_enricher.py \
  -e ADAPTER_UNDER_TEST=/opt/prepared/adapter/prepared_filing.py \
  -e REDIS_CONSTANTS=/app/redisDB/redis_constants.py \
  -v "$PWD/tests":/t/tests:ro -v "$OLD":/old/report_enricher.py:ro -w /t \
  "$CANDIDATE_IMAGE" python -B -m unittest tests.redisDB.test_redis_init tests.redisDB.test_worker_order \
  tests.redisDB.test_worker_recovery tests.redisDB.test_set_filing_dedup -v
```

Expected inventory: 27 methods (2 initializer + 5 worker order + 17 recovery + 3 intake).
The tests-only mount keeps application imports in the actual image. Set all three
source paths above; otherwise the recovery harness looks for constants beside the
mounted tests. Keep the image's Tini entry point for native process cleanup.
Without `ENRICHER_OLD`, the RED proof and the rollback test are skipped.
A Docker-client timeout does not stop its container; execute the cleanup trap
and check that the exact owned resources are gone. The real-pointer control
checks committed publication, retained full input and explicit replay. Successful
substituted pointers in both harnesses have temporary readable receipts.

## 3. Native end-to-end adapter tests (opt-in, not part of the routine run)

The 3 `AmgEvent` tests run the pinned `job.py` with a real browser on the public AMG filing. They need all of:

- `ADAPTER_E2E=1`;
- `ADAPTER_OUT`: a new folder on a filesystem with at least 16% free space;
- `ADAPTER_RECORDED`: the recorded SEC responses (`responses.sqlite3` + `blobs/`, 17 responses).
  A hashed copy is kept outside Git in
  `/home/faisal/prepare_work/extraction_closeout_20261010/production_qualification_20261022/CLAUDE_SEC_GIT_PUBLICATION_20261031/AMG_RECORDED_RESPONSES`;
- `ADAPTER_BROWSER_EXECUTABLE`: the pinned headless shell (sha256 `22d72b58…`).
  The default is the image path `/opt/prepared/browser/chrome-headless-shell-linux64/chrome-headless-shell`;
- a CPU allocation for 3 browser rows.

Optional: `ADAPTER_RUNTIME_MANIFEST` (the default is `k8s/prepared-extraction/RUNTIME_MANIFEST.json`).

Reuse the existing `run_native_adapter_final_2_image.py` under
`/home/faisal/prepare_cleanup_review_20261031/storage_review_20261101/storage_release/`.
It selects 26 methods (3 native + Recovery/CachedReserve/OcrExtension) with zero
skips. Mount the harness at `/runner.py`, only tests at `/workspace/tests`, fixture
store at `/fixtures`, recorded AMG at `/recorded` (read-only), and new output at
`/proof`. Mounting the whole checkout at `/workspace` can shadow the image runtime.
Set `ADAPTER_RUNTIME_MANIFEST=/opt/prepared/runtime/RUNTIME_MANIFEST_ROLE.json`,
`PREPARE_TEST_DATA=/fixtures`, `ADAPTER_E2E=1`, `ADAPTER_RECORDED=/recorded`,
`ADAPTER_OUT=/proof/adapter`, `PYTHONDONTWRITEBYTECODE=1`. Run the image's
`/opt/prepared/venv/bin/python -B /runner.py` with networking disabled, read-only
root and private temporary storage. Verify imports under `/opt/prepared/runtime`
and `/opt/prepared/adapter` after loading tests.

Revision 3 limits: offline adapter 300 seconds; native adapter 300 seconds;
worker lane 600 seconds. Record setup/build separately, exact IDs and elapsed
time, with correctness and timing as separate outcomes. No lane qualifies model
accuracy, a whole-filing latency target or live activation.
