# Driver tests

Run from the repository root:

```bash
python3 -B -S -m unittest discover -s tests/driver -t . -v
```

Standard library only; no credentials, network or external fixture directory.
Missing or damaged fixtures fail. Temporary outputs are removed automatically.

```text
Production                         Tests
driver/prepare/acquire.py           tests/driver/prepare/test_acquire.py
driver/prepare/transport.py         tests/driver/prepare/test_transport.py
driver/prepare/archive.py           tests/driver/prepare/test_archive.py
driver/prepare/campaign.py          tests/driver/prepare/test_campaign.py
                                   tests/driver/prepare/test_scale.py
                                   tests/driver/prepare/test_crash.py
driver/prepare/inventory.py         tests/driver/prepare/test_inventory.py
scripts/driver/prepare/             tests/driver/prepare/test_acquisition_check.py
                                   tests/driver/prepare/fixtures/
```

Acquisition tests cover identities, framing, decoding, source locations, compressed
storage, corruption, cache reuse and CLI behavior. Transport tests simulate HTTP,
retries and timeouts. The three real packages cover:

| Accession | Regression |
|---|---|
| 0001004434-23-000015 | AMG: 17 files, including both EX-99.1 originals |
| 0000906107-25-000005 | EQR: stated count 12, actual count 11 |
| 0000950170-25-021181 | 13D: two company IDs; requested company is not first |

Each losslessly compressed fixture has independent expected metadata, original
SHA-256, decoded-file hashes and source ranges. Never regenerate expected answers
from the parser under test. Broader sample evidence is linked in the
[work order](../../.claude/plans/Drivers/DriversFinal/StepsPlans/Prepare-A_Get.md).

Future stages use matching test folders. Keep small synthetic inputs with tests;
share helpers only when reused. Large samples and historical runs stay outside
the source tree. Use production module CLIs; add scripts only for separate jobs.

Step 2 tests add independent SEC-index checks, missing whole files, exact raw-byte
archiving, malformed caches, shared pacing, terminal 403s, explicit failure ledgers
and zero-request replay. The real AMG index is an additional source fixture;
it does not replace the independently checked package expectations.

Scale regressions cover joint-company index paths (real Entergy fixture), one
physical compressed copy, incremental receipts, old receipt import, actual send
times, disk/quota failures and whole-batch stops. Subprocess tests use SIGKILL
during receipt writes, after commit and before package publication. Completed
responses replay without requests; interrupted, uncommitted work may be retried.
