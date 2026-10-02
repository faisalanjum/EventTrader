# Prepare Get

Save one SEC submission as a compressed original, manifest and receipt. Decode
its files once when needed. Standard library only; Python 3.10/3.11 tested.

From the repository root, this offline example uses the included AMG fixture:

```bash
python3 -m driver.prepare.acquire \
  --accession 0001004434-23-000015 --cik 0001004434 --form 8-K \
  --package tests/driver/prepare/fixtures/0001004434-23-000015.txt.gz \
  --sha256 7f6812c06b8455d9c33611c9acca9320f1982fd7e3fc49572e3771a80cf935bb \
  --output /path/to/output
```

`--package` accepts raw or gzip input; SHA-256 always identifies the uncompressed
original. Supplied gzip is immutable and hard-linked into the version, so the
download cache and version share one physical copy. Keep both on the same filesystem;
cross-filesystem sharing fails explicitly. Raw input and live downloads are compressed once.
Verified reuse makes zero requests. Replace both source arguments with
`--live` for a fresh SEC download; live mode never guesses which saved version to use.
Success prints the version directory; failure exits nonzero, with HTTP details
on stderr when available.

```text
output/<accession>/<original-sha256>/
  submission.txt.gz
  manifest.json
  receipt.json
```

```python
from driver.prepare.acquire import read_package
manifest, files = read_package(version_directory)  # verify and decode once
# files maps each original relative filename to its exact decoded bytes.
```

The version-2 manifest keeps accession, all validated company IDs, form, printed
acceptance time and timezone, original size/hash, and exact header/member byte
ranges. Each member retains name, sequence/type/description, size/hash and format
hint. Ranges refer to uncompressed original bytes; hints do not prove readability.
SEC's stated and actual document counts are recorded separately: equality is not
required. Repeated identical filenames keep separate manifest rows and share bytes.

`acquire.py` handles parsing, verification and atomic saving; `transport.py` handles
HTTP. Corrupt caches, unsafe paths and malformed packages stop explicitly. No
silent repairs or legacy-cache migration; use a new output root for older layouts.
The receipt retains actual retrieval details; offline input has unknown retrieval time.

HTTP: `EventMarketDB faianjum@gmail.com`, at most 3 attempts, 10/60-second connect/read
timeouts, 120 seconds per attempt and 900 seconds total. Transient errors retry;
403 and redirects stop. The caller coordinates the shared SEC request limit.

Limits: one writer per output directory; live HTTP requires Linux/main thread;
one package and its decoded files fit in memory. Framing/hash checks cannot detect
an entire omitted member without an independent inventory. Readability, external
references and broader coverage remain later checks. See [tests](../../tests/driver/README.md)
and the [work order](../../.claude/plans/Drivers/DriversFinal/StepsPlans/Prepare-A_Get.md).

## Batch acquisition and raw payloads

`inventory.py` compares the package with a preserved SEC index. Every listed file
is required, including XML and images; package-only files are reported separately.

`Campaign` adds one download owner, a shared **5 requests/second** gate (including
retries), and a persistent campaign-wide stop after any 403. Receipt times are
recorded after pacing. All campaign calls go through this owner; separate folders
are not separate request allowances. SEC's overall cap remains 10/second.

`responses.sqlite3` saves each receipt in one durable transaction, using Python's
built-in SQLite. Fetching reads one receipt; history is loaded only for an explicit
`campaign.records` audit. Existing `responses.json` imports once without alteration.
Default replay is offline; `live=True`
fetches only unselected URLs. Corrupt selections stop without repair. Refreshes
use a separate campaign directory, preserving previous versions.

New downloads/saves require a configurable free-space reserve (default **5 GiB**).
Storage failures stop the batch; callers must stop on `StorageError` or
`campaign.stopped`. Cached bytes remain readable when space is low. Every filing
in the planned full run requires its SEC inventory comparison, not a sample.

```python
from driver.prepare.campaign import Campaign
with Campaign(cache_directory) as campaign:  # offline by default
    original_bytes, receipt = campaign.fetch(exact_sec_archive_url)

from driver.prepare.archive import store_blob, load_blob
source_hash = store_blob(raw_directory, payload_bytes)
assert load_blob(raw_directory, source_hash) == payload_bytes
```

The raw archive stores lossless compressed bytes without interpreting them.
Call it before JSON/schema parsing or transcript SDK transformations; keep source,
event, publication/version and actual retrieval metadata in caller-owned receipts.
Existing news/transcript ingestion has not been connected to it yet.

The bounded comparison job lives in `scripts/driver/prepare/acquisition_check.py`;
tests live in `tests/driver/prepare/`. It consumes a frozen filing list and local
originals, writes the final outcome report once, and separates this-run requests
from cached history. It is a comparison job, not the overnight runner. Its HTML
links are observations, not a claim of complete reference
resolution. Conversion, reference interpretation and ingestion activation are
separate steps.
