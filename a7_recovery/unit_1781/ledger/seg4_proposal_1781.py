# -*- coding: utf-8 -*-
"""Prepare segment 4 under the proposed snapshot and STOP (Codex SEQ 1781).

Produces the canonical TYPED args array the future native invocation must use,
the logical and durable script paths with an actual same-file proof, exact
hashes, and the cache expectation. Nothing is launched, ingested or finalized.
"""
import hashlib, io, json, os, subprocess, sys
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
COORD = S + "/g1_run_1525.py"
RUN = S + "/g1_precall_run_1525"
DURABLE = ("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1781/"
           "out/proposed_run")
OUT = "/tmp/a7_logs_1781"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")


def main():
    os.makedirs(OUT, exist_ok=True)
    argv = [sys.executable, "-B", COORD, "prepare"]
    r = subprocess.run(argv, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    io.open(OUT + "/g1_seg4_prepare_proposed.log", "w", encoding="utf-8").write(
        "COMMAND: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
        % (" ".join(argv), r.stdout, r.stderr, r.returncode))
    if r.returncode != 0:
        print("PREPARE FAILED", r.returncode); print(r.stdout[-500:], r.stderr[-500:])
        return 1
    for line in r.stdout.splitlines():
        if line.split(":")[0].strip() in ("SEGMENT", "LANES", "ROOT_SHA",
                                          "RECEIPT_SHA", "SCRIPT_BYTES"):
            print("  " + line)

    import a7_g1_build as G
    rsha = G._sha_file(G.root_path(RUN))
    receipt_sha = G._sha_file(os.path.join(RUN, "receipt.seg04.json"))
    packet, problems = G.preflight(S + "/g1_precall_cand_1525", RUN, 4, rsha, receipt_sha)
    if problems:
        print("REFUSED preflight:", problems[:3]); return 1
    args = packet["args"]
    logical = packet["scriptPath"]
    durable = os.path.join(DURABLE, os.path.basename(logical))
    same = os.path.exists(durable) and os.path.samefile(logical, durable)
    doc = {
        "typed_args_array": {"rows": len(args), "type": type(args).__name__,
                             "sha256": hashlib.sha256(json.dumps(
                                 args, sort_keys=True).encode()).hexdigest(),
                             "lanes": sorted({a["lane_id"] for a in args})},
        "script": {"logical_path": logical, "durable_path": durable,
                   "same_file_proved": same,
                   "sha256": G._sha_file(logical),
                   "bytes": os.path.getsize(logical)},
        "root_sha256": rsha, "receipt_seg04_sha256": receipt_sha,
        "cache_expectation": {"cache_hits": 4, "new_calls": 30,
                              "note": ("Codex SEQ 1781 recomputed all 34 v2 keys: four "
                                       "completed journal keys hit, the fifth is "
                                       "started-without-result, 29 never started. This "
                                       "is a statement of expectation only; NO call is "
                                       "authorized or made here.")},
        "stopped_before": ["launch", "ingest", "finalization"],
    }
    io.open(OUT + "/SEG4_PROPOSAL.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    print("  typed args   : %s of %d rows, sha %s"
          % (doc["typed_args_array"]["type"], len(args),
             doc["typed_args_array"]["sha256"][:16]))
    print("  logical path : %s" % logical)
    print("  durable path : %s" % durable)
    print("  SAME FILE    : %s" % same)
    print("  script sha   : %s (%d bytes)" % (doc["script"]["sha256"][:16],
                                              doc["script"]["bytes"]))
    print("  stopped before launch, ingest and finalization")
    return 0


if __name__ == "__main__":
    sys.exit(main())
