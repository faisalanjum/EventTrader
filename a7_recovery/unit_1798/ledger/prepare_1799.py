# -*- coding: utf-8 -*-
"""Freeze the next root, replay the four accepted segments, prepare the next
batch (Codex SEQ 1798 items 2-4, resumed under 1799). No model call.

Runs INSIDE the boundary in two phases, exactly the proved shape:
  prepare      freeze ONE root carrying every lane's input, replay segments
               1-3 against their saved official states, publish segment 4.
  intake_next  ingest segment 4's captured official state under the scoped
               read-only script override, then run the existing
               next_admissible -> publish_run -> preflight chain ONCE for the
               next primary batch and stop.
"""
import collections
import hashlib
import io
import json
import os
import subprocess
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
COORD = S + "/g1_run_1525.py"
CAND = S + "/g1_precall_cand_1525"
RUN = S + "/g1_precall_run_1525"
OUT = "/tmp/a7_logs_1781"
R = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
PUB = R + "/unit_1792/out/candidate_run_1794"
PROFILES = R + "/unit_1798/evidence/lane_input_profiles_1799.json"
BATCH_STATE = R + "/unit_1786/capture/after/wf_41b934cf-f76.json"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_g1_build as G                                          # noqa: E402
RECORDS = []


def run(label, args):
    argv = [sys.executable, "-B", COORD] + list(args)
    r = subprocess.run(argv, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    io.open("%s/g1799_%s.log" % (OUT, label), "w", encoding="utf-8").write(
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


def published(name):
    return json.load(io.open(os.path.join(PUB, name), encoding="utf-8"))


def segments_from_published():
    out = []
    for n in (1, 2, 3):
        states = published("state.seg%02d.json" % n)["states"]
        rid = os.path.basename(states[0])[len("wf_"):-len(".json")]
        if n == 3:
            out.append((n, ["retry"] + list(published("finalization.seg02.json")["retry"]), rid))
        else:
            out.append((n, ["prepare"], rid))
    return out


def phase_prepare():
    decl = json.load(io.open(PROFILES, encoding="utf-8"))
    profiles = decl["profiles"]
    root, root_sha, problems = G.freeze_root(
        CAND, RUN, published("root.json")["candidate_sha256"], lane_inputs=profiles)
    if problems:
        print("REFUSED freeze_root:", problems[:3])
        return 1
    declared = sum(1 for r in root["rows"] if r.get("expected_input") is not None)
    closed = len(root["rows"]) - declared
    print("  root %s  rows %d  declaring an input %d  declaring none %d"
          % (root_sha, len(root["rows"]), declared, closed))
    if (declared, closed) != (decl["counts"]["declare_the_child_input"],
                              decl["counts"]["declare_no_added_input"]):
        print("REFUSED: the frozen root does not carry the reviewed declaration")
        return 1
    for n, args, rid in segments_from_published():
        p = run("seg%d_prepare" % n, args)
        if p.returncode != 0:
            print("SEGMENT %d PREPARE FAILED\n%s\n%s" % (n, p.stdout[-400:], p.stderr[-400:]))
            return 1
        receipt = field(p.stdout, "RECEIPT_SHA")
        i = run("seg%d_ingest" % n, ["ingest", str(n), receipt, rid])
        if i.returncode != 0:
            print("SEGMENT %d INGEST FAILED\n%s\n%s" % (n, i.stdout[-500:], i.stderr[-400:]))
            return 1
        mine, theirs = G._read(G.finalization_path(RUN, n)), published("finalization.seg%02d.json" % n)
        differing = sorted(k for k in ("ledger", "retry", "uncalled", "validity", "problems")
                           if G._plain(mine.get(k)) != G._plain(theirs.get(k)))
        RECORDS[-1]["ledger"] = G._plain(mine.get("ledger"))
        RECORDS[-1]["reproduces_published_outcome"] = not differing
        print("  segment %d  receipt %s  ledger %s  reproduces published: %s"
              % (n, (receipt or "")[:16], G._plain(mine.get("ledger")), not differing))
        if differing:
            print("SEGMENT %d DIFFERS on %s" % (n, differing))
            return 1
    p = run("seg4_prepare", ["prepare"])
    if p.returncode != 0:
        print("SEGMENT 4 PREPARE FAILED\n%s\n%s" % (p.stdout[-500:], p.stderr[-400:]))
        return 1
    logical = field(p.stdout, "SCRIPT_PATH")
    io.open(OUT + "/PREPARE_1799.json", "w", encoding="utf-8").write(json.dumps(
        collections.OrderedDict([
            ("phase", "prepare"), ("root_sha256", root_sha),
            ("rows", len(root["rows"])), ("declaring_an_input", declared),
            ("declaring_none", closed),
            ("segment4_receipt_sha256", field(p.stdout, "RECEIPT_SHA")),
            ("segment4_script", logical),
            ("segment4_script_sha256", G._sha_file(logical)),
            ("steps", RECORDS)]), indent=1) + "\n")
    print("  segment 4 published: receipt %s script %s"
          % ((field(p.stdout, "RECEIPT_SHA") or "")[:16], G._sha_file(logical)[:16]))
    return 0


def phase_intake_next():
    root_sha = G._sha_file(G.root_path(RUN))
    receipt4 = G._sha_file(G.receipt_path(RUN, 4))
    logical = G.script_path(RUN, 4)
    state = json.load(io.open(BATCH_STATE, encoding="utf-8"))
    same = os.path.isfile(state.get("scriptPath") or "") and \
        os.path.samefile(logical, state["scriptPath"])
    print("  segment 4 intake resolves to the executed file: %s" % same)
    i = run("seg4_intake", ["ingest", "4", receipt4,
                            os.path.basename(BATCH_STATE)[len("wf_"):-len(".json")]])
    clean = field(i.stdout, "SEGMENT_CLEAN")
    print("  segment 4: rows %s ledger %s nonvalid %s clean %s"
          % (field(i.stdout, "OFFICIAL_ROWS"), field(i.stdout, "LEDGER"),
             field(i.stdout, "NONVALID"), clean))
    if i.returncode != 0 or clean != "True":
        print(i.stdout[-900:]); print(i.stderr[-400:])
        return 1
    # ---- the next primary batch, ONCE ------------------------------------
    p = run("seg5_prepare", ["prepare"])
    if p.returncode != 0:
        print("NEXT BATCH PREPARE FAILED\n%s\n%s" % (p.stdout[-700:], p.stderr[-400:]))
        return 1
    n = int(field(p.stdout, "SEGMENT"))
    receipt = G._read(G.receipt_path(RUN, n))
    invocation = G._read(G.invocation_path(RUN, n))
    reservation = G._read(G.reservation_path(RUN, n))
    script = G.script_path(RUN, n)
    args = invocation["args"]
    lanes = [r["lane_id"] for r in receipt["rows"]]
    doc = collections.OrderedDict([
        ("phase", "next_batch"), ("segment", n),
        ("root_sha256", root_sha),
        ("receipt_sha256", G._sha_file(G.receipt_path(RUN, n))),
        ("reservation_sha256", G._sha_file(G.reservation_path(RUN, n))),
        ("invocation_sha256", G._sha_file(G.invocation_path(RUN, n))),
        ("args_rows", len(args)),
        ("args_canonical_sha256", hashlib.sha256(
            json.dumps(args, sort_keys=True).encode()).hexdigest()),
        ("lanes", lanes), ("lane_count", len(lanes)),
        ("first_lane", lanes[0]), ("last_lane", lanes[-1]),
        ("attempt", reservation.get("attempt")),
        ("predicted_bytes", field(p.stdout, "LANES")),
        ("logical_script_path", script),
        ("script_sha256", G._sha_file(script)),
        ("script_bytes", os.path.getsize(script)),
        ("call_settings", collections.OrderedDict([
            ("model", args[0].get("model")), ("effort", args[0].get("effort")),
            ("agentType", args[0].get("agentType")),
            ("disallowedTools", args[0].get("disallowedTools")),
            ("max_output_tokens", args[0].get("max_output_tokens"))])),
        ("expected_input_of_the_first_lane",
         {r["lane_id"]: r.get("expected_input") for r in G._read(G.root_path(RUN))["rows"]
          if r["lane_id"] == lanes[0]}),
        ("owners", G._read(G.root_path(RUN))["owners"]),
        ("nothing_launched", True), ("steps", RECORDS)])
    io.open(OUT + "/NEXT_BATCH_1799.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    print("  NEXT BATCH: segment %d, %d lanes %s .. %s, attempt %s"
          % (n, len(lanes), lanes[0], lanes[-1], doc["attempt"]))
    print("  receipt %s  args rows %d  script %s (%d bytes)"
          % (doc["receipt_sha256"][:16], len(args), doc["script_sha256"][:16],
             doc["script_bytes"]))
    print("  settings %s" % G._plain(doc["call_settings"]))
    return 0


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    PHASE = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    sys.exit(phase_prepare() if PHASE == "prepare" else phase_intake_next())
