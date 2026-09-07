# -*- coding: utf-8 -*-
"""Segment-8 intake, the LAST primary batch (Codex SEQ 1814).

There is no next packet: every root lane is accounted for after this, so no
prepare runs and no ninth receipt is created.

Runs INSIDE the boundary. Every decision is the existing coordinator and the
existing owners; this script supplies the externally approved receipt and the
unchanged root, records what the owner returns, and compares it to the
reviewer's expectation without forcing it.
"""
import collections, hashlib, io, json, os, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
COORD, CAND, RUN = S + "/g1_run_1525.py", S + "/g1_precall_cand_1525", S + "/g1_precall_run_1525"
OUT = "/tmp/a7_logs_1781"
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
EXECUTED8 = A + "/unit_1808/out/run_1808/grade_batch.seg08.js"
ROOT = "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0"
RECEIPT8 = "40e95878c57b92db27e45dff372716eeea159721d3277287a100b64e597cf62b"
RID = "b0543d14-6c2"
#: the reviewer's independently derived expectation - compared, never forced
EXPECT = {"valid": 3, "invalid": 0, "retry": 0, "uncalled": 0,
          "selected": 206, "never_started": 0, "required": 206}
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_g1_build as G                                          # noqa: E402
RECORDS = []


def run(label, args):
    argv = [sys.executable, "-B", COORD] + list(args)
    r = subprocess.run(argv, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    io.open("%s/g1814_%s.log" % (OUT, label), "w", encoding="utf-8").write(
        "COMMAND: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
        % (" ".join(argv), r.stdout, r.stderr, r.returncode))
    RECORDS.append(collections.OrderedDict([("label", label), ("command", argv[2:]),
                                            ("exit", r.returncode)]))
    return r


def field(text, key):
    for line in text.splitlines():
        if line.startswith(key):
            return line.split(":", 1)[1].strip()
    return None


def main():
    logical8 = G.script_path(RUN, 8)
    same8 = os.path.samefile(logical8, EXECUTED8)
    root_now = G._sha_file(G.root_path(RUN))
    raw_before = len(os.listdir(os.path.join(RUN, "raw")))
    print("  root unchanged            : %s" % (root_now == ROOT))
    print("  seg8 logical IS the executed file: %s" % same8)
    if not (same8 and root_now == ROOT):
        print("REFUSED: binding or root mismatch"); return 1

    i = run("seg8_intake", ["ingest", "8", RECEIPT8, RID])
    if i.returncode != 0:
        print("SEGMENT 8 INGEST FAILED rc=%d\n%s\n%s"
              % (i.returncode, i.stdout[-900:], i.stderr[-500:]))
        return 1
    fin = G._read(G.finalization_path(RUN, 8))
    led = fin["ledger"]
    states = G.lane_states(RUN)
    called = sorted(l for l, v in states.items() if v == "called")
    rows_all = G._read(G.root_path(RUN))["rows"]
    pending = [r["lane_id"] for r in rows_all if states.get(r["lane_id"]) != "called"]
    got = {"valid": led["valid"], "invalid": led["invalid"], "retry": led["retry"],
           "uncalled": led["uncalled"], "selected": len(called),
           "never_started": len(pending), "required": len(rows_all)}
    differences = {k: {"expected": EXPECT[k], "owner": got[k]}
                   for k in EXPECT if EXPECT[k] != got[k]}
    print("  segment 8 ledger          : %s" % G._plain(led))
    print("  nonvalid                  : %s" % field(i.stdout, "NONVALID"))
    print("  selected %d, never started %d of %d" % (got["selected"], got["never_started"],
                                                     got["required"]))
    print("  matches the reviewer's expectation: %s %s"
          % (not differences, differences or ""))

    doc = collections.OrderedDict([
        ("phase", "segment8_intake"), ("root_sha256", root_now),
        ("receipt_supplied", RECEIPT8), ("run_id", "wf_" + RID),
        ("seg8_logical_is_the_executed_file", same8),
        ("ledger", G._plain(led)), ("retry", fin["retry"]), ("uncalled", fin["uncalled"]),
        ("problems", G._plain(fin["problems"])),
        ("finalization_sha256", G._sha_file(G.finalization_path(RUN, 8))),
        ("accounting_sha256", G._sha_file(G.accounting_path(RUN, 8))),
        ("state_record_sha256", G._sha_file(G.state_path(RUN, 8))),
        ("raw_reply_files_before", raw_before),
        ("raw_reply_files_after", len(os.listdir(os.path.join(RUN, "raw")))),
        ("finalizations_present", len([f for f in os.listdir(RUN)
                                       if f.startswith("finalization.")])),
        ("owner_counts", got), ("reviewer_expectation", EXPECT),
        ("differences_from_the_expectation", differences),
        ("first_four_intakes_rerun", False), ("steps", list(RECORDS))])
    io.open(OUT + "/INTAKE_1814.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    if differences:
        print("STOPPING: the owner differs from the expectation; preserved and reported")
        return 1

    print("  raw reply files           : %d -> %d"
          % (doc["raw_reply_files_before"], doc["raw_reply_files_after"]))
    print("  finalizations present     : %d" % doc["finalizations_present"])
    print("  LAST PRIMARY BATCH: no prepare, no ninth receipt")
    return 0


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sys.exit(main())
