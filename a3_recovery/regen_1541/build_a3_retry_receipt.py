#!/usr/bin/env python3
"""Rebuild the A3 RETRY receipt from surviving evidence (Codex SEQ 1541 item 2).

NO CALL IS MADE. The retry is `_a1_publish(child, derived, attempt=2, parent=...)`,
which is `a1_expected_receipt` plus the one state the runner recorded, so it is derived
exactly as the primary was:

  * the plan and the two reproduced programs, as before;
  * the ONE retry key, printed by the run itself ("retry: [[...]]", transcript 35037);
  * the parent binding - the primary's run_id and receipt digest, both of which this
    recovery has reproduced byte-exactly, and the primary finalization's digest, which
    is history's own recorded value and is the single figure here that is quoted;
  * the ONE workflow state the retry recorded, named in the record that recorded it
    (transcript 35083) and still present on disk.

`a1_prepare_retry` is not called, because it re-reads the primary finalization from
disk and that artefact is not reproduced yet; the payload it would publish is built
directly instead. The target digest is compared only AFTER the build.
"""
import collections
import hashlib
import io
import json
import os
import sys

R = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(R, "a3_work")
SESS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
        "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
PRIMARY = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
           "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/"
           "Drivers/experiments/runs/kf-a3-one-item-196x2-serial-20260821T055948Z")
#: the run's own printed retry set (transcript 35037)
RETRY_KEYS = [("0000092380-26-000044#042", "0000092380-26-000044#042/L1")]
#: the one state the retry recorded (transcript 35083)
RETRY_STATE = "wf_7b06aa46-c6f"
PARENT_RECEIPT = "19abb07cf23178434ff230443bb1d146f390226fcba3fa20c4a8d2c35e6e1536"
#: history's own figure, the single quoted input here
PARENT_FINALIZATION = ("92e1872ce4e171e7829f13274216cff9b32aa237d137d6401cfd34e9c137"
                       "a8d7")
PIN = "4a2ecf870f390fc67f69d9937a48766a0e990bfff0046c6c486b660453b42465"


def main():
    sys.path.insert(0, WORK)
    import raw_transport as RT                                    # noqa: E402
    import audit_worker_access as AUD                             # noqa: E402

    plan = RT.a1_plan()
    child = os.path.join(PRIMARY, "retry")
    payload = RT.a1_expected_receipt(
        child, RETRY_KEYS, 2,
        {"run_id": os.path.basename(PRIMARY),
         "receipt_sha256": PARENT_RECEIPT,
         "finalization_sha256": PARENT_FINALIZATION}, plan)
    rpath = os.path.join(WORK, "retry_receipt.json")
    RT._atomic_json(rpath, payload)
    AUD.record_state(rpath, payload["run_id"],
                     os.path.join(SESS, "workflows", RETRY_STATE + ".json"))
    got = io.open(rpath, "rb").read()
    sha = hashlib.sha256(got).hexdigest()
    doc = json.loads(got.decode("utf-8"))
    out = collections.OrderedDict([
        ("run_id", doc["run_id"]), ("attempt", doc.get("attempt")),
        ("states_recorded", len(doc["states"])),
        ("allowed_calls", len(doc["allowed"])),
        ("invocations", len(doc["invocations"])),
        ("parent", doc.get("parent")),
        ("bytes", len(got)), ("sha256", sha), ("pin", PIN), ("pin_met", sha == PIN)])
    io.open(os.path.join(R, "reports", "a3_retry_receipt_rebuild.json"), "w",
            encoding="utf-8").write(json.dumps(out, indent=2) + "\n")
    for k, v in out.items():
        print("%-16s %s" % (k, json.dumps(v) if isinstance(v, dict) else v))


if __name__ == "__main__":
    main()
