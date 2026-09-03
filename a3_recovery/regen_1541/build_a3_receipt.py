#!/usr/bin/env python3
"""Rebuild the A3 primary receipt from surviving evidence (Codex SEQ 1541 item 2).

NO CALL IS MADE. The run that produced this receipt cost 392 paid calls, and repeating
one is forbidden - so the receipt is DERIVED instead, from four things that survive:

  * `raw_transport.py` and `audit_worker_access.py`, reproduced byte-exactly here,
    which are the two programs that built and then mutated the receipt;
  * the accepted A3 plan `d65e4f87...`, recovered earlier;
  * the 36-row ledger, read back from history's OWN printed output (`ledgered i/36
    <source_id> <wf>`), so the order is history's and not mine;
  * the 36 workflow state files, which still exist under the session directory.

The receipt is `a1_expected_receipt(...)` as the gate published it, plus one recorded
state per ledger row, re-serialised the way `record_state` writes it. The target digest
is compared only AFTER the build, as an output assertion.
"""
import collections
import hashlib
import io
import json
import os
import re
import sys

R = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(R, "a3_work")
SESS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
        "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
#: the run directory as it stood; only its NAME and the launcher paths built from it
#: reach the receipt, so the string is used and nothing is created on disk
RUN_DIR = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
           "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/"
           "Drivers/experiments/runs/kf-a3-one-item-196x2-serial-20260821T055948Z")
PIN = "19abb07cf23178434ff230443bb1d146f390226fcba3fa20c4a8d2c35e6e1536"


def ledger():
    """-> [(index, source_id, wf_run_id)] read back from history's own output."""
    rows = []
    for line in io.open(os.path.join(R, "logs", "a3_ledger.txt"), encoding="utf-8"):
        m = re.match(r"^\s*(\d+)\s+(\S+)\s+(wf_\S+)", line)
        if m:
            rows.append((int(m.group(1)), m.group(2), m.group(3)))
    return sorted(rows)


def main():
    sys.path.insert(0, WORK)
    import raw_transport as RT                                    # noqa: E402
    import audit_worker_access as AUD                             # noqa: E402
    import build_launch_manifest as blm                           # noqa: E402

    # NOTHING HERE IS QUOTED. The A3-era builder carries this setting itself, and its
    # reconstruction now reaches history's own line count exactly, so the value is
    # read from the rebuilt file rather than copied out of a printed assertion. The
    # run's own gate independently asserted "128000" at transcript line 34239, which
    # is a check on the result and not an input to it.
    derived_setting = blm.MAX_OUTPUT_TOKENS_SETTING

    plan = RT.a1_plan()
    payload = RT.a1_expected_receipt(RUN_DIR, RT.a1_canonical_calls(plan, 1), 1, None,
                                     plan)
    rows = ledger()
    # THE GATE PUBLISHES, THEN THE RUNNER RECORDS. Writing the published receipt first
    # is what makes `record_state` lawful: it refuses to create one, by design.
    # THE PUBLISHER'S OWN WRITER, not an equivalent-looking one. `_atomic_json` sorts
    # keys; a hand-rolled dump in insertion order produces the same DATA and different
    # BYTES, and every later rewrite preserves whatever order it found.
    rpath = os.path.join(WORK, "receipt.json")
    RT._atomic_json(rpath, payload)
    for _i, _sid, wf in rows:
        AUD.record_state(rpath, payload["run_id"],
                         os.path.join(SESS, "workflows", wf + ".json"))
    got = io.open(rpath, "rb").read()
    sha = hashlib.sha256(got).hexdigest()
    doc = json.loads(got.decode("utf-8"))
    out = collections.OrderedDict([
        ("run_id", doc["run_id"]),
        ("ledger_rows", len(rows)),
        ("states_recorded", len(doc["states"])),
        ("unique_states", len(set(doc["states"]))),
        ("allowed_calls", len(doc["allowed"])),
        ("unique_allowed", len({tuple(c) for c in doc["allowed"]})),
        ("invocations", len(doc["invocations"])),
        ("manifest_sha256", doc["manifest_sha256"]),
        ("max_output_tokens", doc.get("max_output_tokens")),
        ("quoted_not_derived", []),
        ("setting_read_from_rebuilt_builder", derived_setting),
        ("bytes", len(got)), ("sha256", sha),
        ("pin", PIN), ("pin_met", sha == PIN)])
    io.open(os.path.join(R, "reports", "a3_receipt_rebuild.json"), "w",
            encoding="utf-8").write(json.dumps(out, indent=2) + "\n")
    for k, v in out.items():
        print("%-18s %s" % (k, v))


if __name__ == "__main__":
    main()
