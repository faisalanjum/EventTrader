# -*- coding: utf-8 -*-
"""Replay the SAME three completed segments under the PROPOSED owner snapshot.

Codex SEQ 1778 item 2. No call is made: every segment is prepared by the real
g1_run_1525.py and then ingests the SAVED official state that segment actually
returned. Codex SEQ 1781. The root now pins the CORRECTED audit owner, so the receipt and
finalization hashes NECESSARILY differ from the published ones - they are
recorded as new values and never claimed to be the old ones. What must be
identical is everything the correction does not touch: the per-lane validity,
the retry outcomes and the selected answers.

Segment 3 is the one lawful attempt-2 retry; its finalization hash is read from
what the owner writes, because no historical hash for it survives and inventing
one is forbidden.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
COORD = S + "/g1_run_1525.py"
RUN = S + "/g1_precall_run_1525"
OUT = "/tmp/a7_logs_1781"

SEGMENTS = [
    {"n": 1, "prepare": ["prepare"], "run_id": "85692dcf-0e8", "lanes": 30,
     "receipt": "dd59d2d3d37f45c43f80ebf34a50fe0b6e06584996259fbeadf141c79fb0e9b4",
     "finalization": "540000fbc2f5bebbf84a5da685bf073a6fe619a8ce252f7e1e63adb18ce471c6",
     "expect": "30 valid, no retry or uncalled"},
    {"n": 2, "prepare": ["prepare"], "run_id": "f309e723-949", "lanes": 52,
     "receipt": "8853a3fd3fb68f9795e51c0f69710ef0a1692098fe14b9c17cf09e6201480094",
     "finalization": "5ae820e804ec18812780c5269cd0a17ea42b87df571ec39182d96e3f4e4912e1",
     "expect": "51 valid and one schema-invalid G1-018/G1a"},
    {"n": 3, "prepare": ["retry", "G1-018/G1a"], "run_id": "87012c93-dba", "lanes": 1,
     "receipt": "6ae2d791c542cdbede088c22247e1943c2098eb2b63dc4eaf2abb563bccc08f3",
     "finalization": None,
     "expect": "one valid, no retry or uncalled"},
]
RECORDS = []


def run(label, args):
    argv = [sys.executable, "-B", COORD] + args
    r = subprocess.run(argv, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    io.open("%s/g1_%s.log" % (OUT, label), "w", encoding="utf-8").write(
        "COMMAND: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
        % (" ".join(argv), r.stdout, r.stderr, r.returncode))
    RECORDS.append({"label": label, "command": argv, "exit": r.returncode})
    return r


def field(out, key):
    for line in out.splitlines():
        if line.startswith(key):
            return line.split(":", 1)[1].strip()
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    for spec in SEGMENTS:
        n = spec["n"]
        p = run("seg%d_prepare" % n, spec["prepare"])
        if p.returncode != 0:
            print("SEGMENT %d PREPARE FAILED rc=%d" % (n, p.returncode))
            print(p.stdout[-600:]); print(p.stderr[-600:])
            return 1
        got_seg = field(p.stdout, "SEGMENT")
        got_receipt = field(p.stdout, "RECEIPT_SHA")
        lanes = field(p.stdout, "LANES")
        print("seg %s prepared: lanes %s receipt %s" % (got_seg, lanes, (got_receipt or "")[:16]))
        if got_receipt == spec["receipt"]:
            print("  receipt unchanged from the published run")
        else:
            print("  receipt CHANGED by the owner snapshot (expected): %s"
                  % got_receipt)

        g = run("seg%d_ingest" % n, ["ingest", str(n), got_receipt, spec["run_id"]])
        if g.returncode != 0:
            print("SEGMENT %d INGEST FAILED rc=%d" % (n, g.returncode))
            print(g.stdout[-800:]); print(g.stderr[-800:])
            return 1
        for k in ("OFFICIAL_ROWS", "LEDGER", "RETRY", "NONVALID", "SEGMENT_CLEAN"):
            v = field(g.stdout, k)
            if v is not None:
                print("  %-14s %s" % (k, v[:110]))
        # the owner names it finalization.seg<NN>.json at the run root
        fpath = os.path.join(RUN, "finalization.seg%02d.json" % n)
        fsha = (hashlib.sha256(io.open(fpath, "rb").read()).hexdigest()
                if fpath and os.path.isfile(fpath) else None)
        print("  finalization  %s" % fsha)
        if spec["finalization"]:
            print("  finalization %s (published run had %s)"
                  % ("unchanged" if fsha == spec["finalization"] else "CHANGED by the "
                     "owner snapshot, as expected", spec["finalization"][:16]))
        else:
            print("  no historical finalization hash exists for this retry; "
                  "recorded from the owner, not invented")
        RECORDS[-1]["finalization_sha256"] = fsha
        RECORDS[-1]["expected_outcome"] = spec["expect"]

    st = run("status_after_3", ["status"])
    print("\n--- status after three segments (exit %d) ---" % st.returncode)
    print(st.stdout.strip()[-500:])
    io.open(OUT + "/SEGMENT_RECORDS.json", "w", encoding="utf-8").write(
        json.dumps(RECORDS, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
