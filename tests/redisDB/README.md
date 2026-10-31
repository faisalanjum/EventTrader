# Prepared-extraction adapter and worker tests

Tests for `redisDB/prepared_filing.py` (the adapter), `redisDB/report_enricher.py` (the worker) and `redisDB/redisClasses.py`.
They need two environments:

| Tests | Environment | Needs |
|---|---|---|
| `test_prepared_filing.py` | the Prepare test environment (EdgarTools 5.60.0) | `PREPARE_TEST_DATA` with fixture group `adapter.r1_verified` |
| `test_worker_order.py`, `test_worker_recovery.py`, `test_redis_init.py` | the worker image (redis-py) | a **disposable** Redis for the last two |

Tests that cannot run in the current environment are skipped with the reason printed. A skipped test has not passed.

## 1. Adapter tests (host)

From the repository root:

```bash
export PREPARE_TEST_DATA=/home/faisal/prepare_test_data
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 \
  /home/faisal/prepare_work/venvs/prepare-closeout-20261011/bin/python -B -m unittest discover -s tests/redisDB -t . -v
```

Expected: 21 adapter tests pass. The 3 native end-to-end tests and the 23 worker tests are skipped.

## 2. Worker tests (worker image + disposable Redis)

Every Redis test runs `FLUSHALL`. Never point `REDIS_TEST_HOST`/`REDIS_TEST_PORT` at a shared or production Redis.
The commands below put the test Redis on an internal Docker network with no outside access, and remove it afterwards.

```bash
NET=redisdb-test-net; RED=redisdb-test-redis
OLD=$(mktemp -d)/report_enricher.py
# previous worker (for the RED proof and the rollback test): taken from image5, never copied into Git
docker run --rm --network none --entrypoint cat \
  faisalanjum/report-enricher@sha256:23ca15adc2b1f265ec862a1af2bfa471cc525a6b18b25524049b044803c6236b \
  /app/redisDB/report_enricher.py > "$OLD"
sha256sum "$OLD"   # must be b36aa7d2a70ddd29aefc24658baf915e28f40537663b06cf5142eae51f75f4b4

docker network create --internal $NET
docker run -d --rm --name $RED --network $NET --memory 512m \
  redis@sha256:7b5ee51c14cf5febd4adde3a4b6cced72efdf154df7e9a0383163b13e16e9091
docker run --rm --network $NET --memory 8g \
  -e REDIS_TEST_HOST=$RED -e REDIS_TEST_PORT=6379 -e ENRICHER_OLD=/old/report_enricher.py -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD":/t:ro -v "$OLD":/old/report_enricher.py:ro -w /t --entrypoint python \
  faisalanjum/report-enricher@sha256:f72f3a014007e8dca8e4909a5747814c5304315fa1c27b715a0ca925e1455b7b \
  -B -m unittest discover -s tests/redisDB -t . -p 'test_[wr]*.py' -v
docker stop $RED; docker network rm $NET
```

Expected: 23 tests pass (2 initializer + 5 worker order + 16 recovery).
Without `ENRICHER_OLD`, the RED proof and the rollback test are skipped.

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
