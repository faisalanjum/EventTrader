# -*- coding: utf-8 -*-
"""Segment-5 intake and the next prepared batch (Codex SEQ 1803 items 2-3).

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
EXECUTED5 = A + "/unit_1798/out/run_1798/grade_batch.seg05.js"
ROOT = "6667bb30c18f0ed2a3de6eb8b916c6d270974617f9dfd3d9d73515dbfe656fc0"
RECEIPT5 = "deee46c97dbd4819e5298a3cbb599260260d0656861072da03cfb438d991e467"
RID = "feabb3a2-628"
#: the reviewer's independently derived expectation - compared, never forced
EXPECT = {"valid": 40, "invalid": 0, "retry": 0, "uncalled": 0,
          "selected": 156, "never_started": 50, "required": 206}
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_g1_build as G                                          # noqa: E402
RECORDS = []


def run(label, args):
    argv = [sys.executable, "-B", COORD] + list(args)
    r = subprocess.run(argv, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    io.open("%s/g1803_%s.log" % (OUT, label), "w", encoding="utf-8").write(
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
    logical5 = G.script_path(RUN, 5)
    same5 = os.path.samefile(logical5, EXECUTED5)
    root_now = G._sha_file(G.root_path(RUN))
    print("  root unchanged            : %s" % (root_now == ROOT))
    print("  seg5 logical IS the executed file: %s" % same5)
    if not (same5 and root_now == ROOT):
        print("REFUSED: binding or root mismatch"); return 1

    i = run("seg5_intake", ["ingest", "5", RECEIPT5, RID])
    if i.returncode != 0:
        print("SEGMENT 5 INGEST FAILED rc=%d\n%s\n%s"
              % (i.returncode, i.stdout[-900:], i.stderr[-500:]))
        return 1
    fin = G._read(G.finalization_path(RUN, 5))
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
    print("  segment 5 ledger          : %s" % G._plain(led))
    print("  nonvalid                  : %s" % field(i.stdout, "NONVALID"))
    print("  selected %d, never started %d of %d" % (got["selected"], got["never_started"],
                                                     got["required"]))
    print("  matches the reviewer's expectation: %s %s"
          % (not differences, differences or ""))

    doc = collections.OrderedDict([
        ("phase", "segment5_intake"), ("root_sha256", root_now),
        ("receipt_supplied", RECEIPT5), ("run_id", "wf_" + RID),
        ("seg5_logical_is_the_executed_file", same5),
        ("ledger", G._plain(led)), ("retry", fin["retry"]), ("uncalled", fin["uncalled"]),
        ("problems", G._plain(fin["problems"])),
        ("finalization_sha256", G._sha_file(G.finalization_path(RUN, 5))),
        ("accounting_sha256", G._sha_file(G.accounting_path(RUN, 5))),
        ("state_record_sha256", G._sha_file(G.state_path(RUN, 5))),
        ("owner_counts", got), ("reviewer_expectation", EXPECT),
        ("differences_from_the_expectation", differences),
        ("first_four_intakes_rerun", False), ("steps", list(RECORDS))])
    io.open(OUT + "/INTAKE_1803.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    if differences:
        print("STOPPING: the owner differs from the expectation; preserved and reported")
        return 1

    # ---- item 3: the next primary prefix, ONCE ----------------------------
    p = run("seg6_prepare", ["prepare"])
    if p.returncode != 0:
        print("NEXT BATCH PREPARE FAILED\n%s\n%s" % (p.stdout[-800:], p.stderr[-500:]))
        return 1
    n = int(field(p.stdout, "SEGMENT"))
    receipt = G._read(G.receipt_path(RUN, n))
    invocation = G._read(G.invocation_path(RUN, n))
    reservation = G._read(G.reservation_path(RUN, n))
    script = G.script_path(RUN, n)
    args = invocation["args"]
    lanes = [r["lane_id"] for r in receipt["rows"]]
    root = G._read(G.root_path(RUN))
    nxt = collections.OrderedDict([
        ("phase", "next_batch"), ("segment", n), ("root_sha256", root_now),
        ("lane_count", len(lanes)), ("first_lane", lanes[0]), ("last_lane", lanes[-1]),
        ("lanes", lanes), ("attempt", reservation.get("attempt")),
        ("receipt_sha256", G._sha_file(G.receipt_path(RUN, n))),
        ("reservation_sha256", G._sha_file(G.reservation_path(RUN, n))),
        ("invocation_sha256", G._sha_file(G.invocation_path(RUN, n))),
        ("args_rows", len(args)),
        ("args_compact_sha256", hashlib.sha256(json.dumps(
            args, sort_keys=True, separators=(",", ":")).encode()).hexdigest()),
        ("args_sorted_default_sha256", hashlib.sha256(json.dumps(
            args, sort_keys=True).encode()).hexdigest()),
        ("logical_script_path", script), ("script_sha256", G._sha_file(script)),
        ("script_bytes", os.path.getsize(script)),
        ("predicted_bytes_line", field(p.stdout, "LANES")),
        ("call_settings", collections.OrderedDict(
            (k, args[0].get(k)) for k in ("model", "runtime_model_id", "effort", "agentType",
                                          "disallowedTools", "max_output_tokens"))),
        ("candidate_sha256", root["candidate_sha256"]), ("owners", root["owners"]),
        ("expected_input_of_the_first_lane",
         next(r.get("expected_input") for r in root["rows"] if r["lane_id"] == lanes[0])),
        ("nothing_launched", True), ("later_receipts_created", 0), ("steps", list(RECORDS))])
    io.open(OUT + "/NEXT_BATCH_1803.json", "w", encoding="utf-8").write(
        json.dumps(nxt, indent=1) + "\n")
    print("  NEXT BATCH: segment %d, %d lanes %s .. %s, attempt %s"
          % (n, len(lanes), lanes[0], lanes[-1], nxt["attempt"]))
    print("  receipt %s  args %d rows  script %s (%d bytes)"
          % (nxt["receipt_sha256"][:16], len(args), nxt["script_sha256"][:16],
             nxt["script_bytes"]))
    print("  settings %s" % G._plain(nxt["call_settings"]))
    return 0


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sys.exit(main())
