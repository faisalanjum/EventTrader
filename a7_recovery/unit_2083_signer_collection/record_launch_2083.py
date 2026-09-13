# -*- coding: utf-8 -*-
"""Codex SEQ 2083: append ONE launch to this unit's durable ledger.

The SEQ 2016/2018 recorder with only this phase's paths changed. A label that
already appears - in ANY state - is refused, so no successful call can be
launched twice, and the script on disk is re-hashed against the frozen packet
before anything is written.
Usage: record_launch_2070.py <label> <runId> <scriptPath> [attempt]
"""
import collections
import datetime
import hashlib
import io
import json
import os
import sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A + "/unit_2008/harness_g1v3")
import raw_transport as RT                                         # noqa: E402

UNIT = A + "/unit_2083_signer_collection"
LEDGER = UNIT + "/evidence/signer/launch_ledger_2083.json"
RECORD = UNIT + "/LAUNCH_RECORD_2083.json"
label, run_id, script_path = sys.argv[1:4]
attempt = int(sys.argv[4]) if len(sys.argv) > 4 else 1

pinned = {i["label"]: i for i in
          json.loads(io.open(RECORD, encoding="utf-8").read())["invocations"]}
if attempt != 1:
    # THIS TASK AUTHORIZES 1 SIGNER CALL AND NOTHING ELSE (Codex SEQ 2083).
    # There is no frozen child to read, so a second attempt is refused here
    # rather than silently launching an unauthorized call.
    print(json.dumps({"refused": "only attempt 1 is authorized by this "
                                 "collection-only task", "label": label,
                      "attempt": attempt}, indent=1))
    raise SystemExit(3)
if label not in pinned:
    print(json.dumps({"refused": "label is not in the frozen packet",
                      "label": label, "attempt": attempt}, indent=1))
    raise SystemExit(3)
want = pinned[label]["script_sha256"]

led = (json.loads(io.open(LEDGER, encoding="utf-8").read())
       if os.path.isfile(LEDGER)
       else {"phase": "a7 REAL final-key signature, attempt 1",
             "authority": "Codex SEQ 2083", "launches": []})
for row in led["launches"]:
    if row["label"] == label and row["attempt"] == attempt:
        print(json.dumps({"refused": "label already launched at this attempt",
                          "label": label, "existing": row}, indent=1))
        raise SystemExit(3)
    if row["runId"] == run_id:
        print(json.dumps({"refused": "runId already recorded", "runId": run_id,
                          "existing": row}, indent=1))
        raise SystemExit(3)
on_disk = hashlib.sha256(io.open(script_path, "rb").read()).hexdigest()
if on_disk != want:
    print(json.dumps({"refused": "the script on disk is not the pinned one",
                      "path": script_path, "on_disk": on_disk,
                      "pinned": want}, indent=1))
    raise SystemExit(3)
led["launches"].append(collections.OrderedDict([
    ("label", label), ("runId", run_id), ("scriptPath", script_path),
    ("script_sha256", want), ("attempt", attempt), ("state", "in_flight"),
    ("launched_utc", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))]))
RT._atomic_json(LEDGER, led)
print(json.dumps({"recorded": label, "runId": run_id, "attempt": attempt,
                  "launches": len(led["launches"])}, indent=1))
