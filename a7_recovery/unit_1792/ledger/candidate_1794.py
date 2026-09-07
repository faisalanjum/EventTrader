# -*- coding: utf-8 -*-
"""The complete no-call intake, audit and finalization candidate (SEQ 1794 item 4).

Runs INSIDE the private recovery boundary, in two phases.

  prepare  freeze ONE root that carries each lane's own expected input, replay
           the three already-completed segments against the official states
           they actually returned, then publish segment 4 and stop.
  intake   ingest the batch's own captured official state through the existing
           coordinator - record_official_state, save_results, finalize_segment -
           under the intake map, whose scoped override presents the EXACT
           immutable script the native call executed.

Nothing here re-implements an owner and nothing calls a model: every decision is
made by a7_g1_build, a7_g1_workflow_gate and audit_worker_access, driven by the
same g1_run_1525.py coordinator the real run used. Every historical fact - run
ids, the retry lane, the candidate hash - is read from PUBLISHED evidence, never
written down here.
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
PUB = R + "/unit_1781/out/proposed_run"
PROFILES = R + "/unit_1792/evidence/lane_input_profiles.json"
#: the run the resumed batch actually completed under
BATCH_STATE = R + "/unit_1786/capture/after/wf_41b934cf-f76.json"
#: the identities approved before the call was made
APPROVED = R + "/unit_1786/logs/PRECALL_IDENTITIES.json"

sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_g1_build as G                                          # noqa: E402

RECORDS = []


def run(label, args):
    argv = [sys.executable, "-B", COORD] + list(args)
    r = subprocess.run(argv, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    io.open("%s/g1_%s.log" % (OUT, label), "w", encoding="utf-8").write(
        "COMMAND: %s\n--- STDOUT ---\n%s\n--- STDERR ---\n%s\n--- EXIT ---\n%d\n"
        % (" ".join(argv), r.stdout, r.stderr, r.returncode))
    RECORDS.append(collections.OrderedDict([
        ("label", label), ("command", argv[2:]), ("exit", r.returncode)]))
    return r


def field(text, key):
    for line in text.splitlines():
        if line.startswith(key):
            return line.split(":", 1)[1].strip()
    return None


def published(name):
    return json.load(io.open(os.path.join(PUB, name), encoding="utf-8"))


def segments_from_published():
    """The three completed segments, read out of the published run itself."""
    out = []
    for n in (1, 2, 3):
        states = published("state.seg%02d.json" % n)["states"]
        if len(states) != 1:
            raise SystemExit("REFUSED: published segment %d names %d states"
                             % (n, len(states)))
        run_id = os.path.basename(states[0])[len("wf_"):-len(".json")]
        if n == 3:
            lanes = published("finalization.seg02.json")["retry"]
            out.append((n, ["retry"] + list(lanes), run_id))
        else:
            out.append((n, ["prepare"], run_id))
    return out


def phase_prepare():
    profiles = json.load(io.open(PROFILES, encoding="utf-8"))["profiles"]
    candidate = published("root.json")["candidate_sha256"]
    root, root_sha, problems = G.freeze_root(CAND, RUN, candidate,
                                             lane_inputs=profiles)
    if problems:
        print("REFUSED freeze_root:", problems[:3])
        return 1
    declared = [r for r in root["rows"] if r.get("expected_input") is not None]
    closed = [r for r in root["rows"] if r.get("expected_input") is None]
    print("  root            : %s  rows %d" % (root_sha, len(root["rows"])))
    print("  lanes declaring an input : %d" % len(declared))
    print("  lanes declaring none     : %d" % len(closed))
    if len(declared) != sum(1 for v in profiles.values() if v is not None):
        print("REFUSED: the frozen root does not carry the reviewed declaration")
        return 1

    for n, args, run_id in segments_from_published():
        p = run("seg%d_prepare" % n, args)
        if p.returncode != 0:
            print("SEGMENT %d PREPARE FAILED rc=%d\n%s\n%s"
                  % (n, p.returncode, p.stdout[-400:], p.stderr[-400:]))
            return 1
        receipt = field(p.stdout, "RECEIPT_SHA")
        i = run("seg%d_ingest" % n, ["ingest", str(n), receipt, run_id])
        if i.returncode != 0:
            print("SEGMENT %d INGEST FAILED rc=%d\n%s\n%s"
                  % (n, i.returncode, i.stdout[-600:], i.stderr[-400:]))
            return 1
        # THE BAR IS HISTORY, NOT CLEANLINESS. Segment 2 lawfully carries one
        # schema-invalid lane that segment 3 retries; demanding a clean ledger
        # would reject the run for being what it actually was. The correction
        # must leave every outcome the published finalization recorded exactly
        # as it stands - that is the whole claim being tested.
        mine = G._read(G.finalization_path(RUN, n))
        theirs = published("finalization.seg%02d.json" % n)
        differing = sorted(k for k in ("ledger", "retry", "uncalled",
                                       "validity", "problems")
                           if G._plain(mine.get(k)) != G._plain(theirs.get(k)))
        RECORDS[-1]["ledger"] = G._plain(mine.get("ledger"))
        RECORDS[-1]["reproduces_published_outcome"] = not differing
        RECORDS[-1]["differing"] = differing
        print("  segment %d  lanes %s  receipt %s  ledger %s  reproduces "
              "the published outcome: %s"
              % (n, field(p.stdout, "LANES"), (receipt or "")[:16],
                 G._plain(mine.get("ledger")), not differing))
        if differing:
            print("SEGMENT %d DIFFERS FROM THE PUBLISHED OUTCOME on %s"
                  % (n, differing))
            for k in differing:
                print("   %-9s mine   %s" % (k, G._plain(mine.get(k))))
                print("   %-9s theirs %s" % ("", G._plain(theirs.get(k))))
            return 1

    p = run("seg4_prepare", ["prepare"])
    if p.returncode != 0:
        print("SEGMENT 4 PREPARE FAILED rc=%d\n%s\n%s"
              % (p.returncode, p.stdout[-600:], p.stderr[-400:]))
        return 1
    receipt_sha = field(p.stdout, "RECEIPT_SHA")
    logical = field(p.stdout, "SCRIPT_PATH")
    state = json.load(io.open(BATCH_STATE, encoding="utf-8"))
    # the approved pre-call identities: the segment this candidate publishes
    # must be the SAME 34 lanes and the SAME canonical args that were launched
    approved = json.load(io.open(APPROVED, encoding="utf-8"))
    args = G._read(G.invocation_path(RUN, 4))["args"]
    args_sha = hashlib.sha256(json.dumps(args, sort_keys=True).encode("utf-8")).hexdigest()
    doc = collections.OrderedDict([
        ("phase", "prepare"), ("root_sha256", root_sha),
        ("candidate_sha256", candidate),
        ("segment4", collections.OrderedDict([
            ("receipt_sha256", receipt_sha),
            ("lanes", field(p.stdout, "LANES")),
            ("logical_script_path", logical),
            ("script_sha256", G._sha_file(logical)),
            ("script_bytes", os.path.getsize(logical)),
            ("state_script_path", state.get("scriptPath")),
            ("state_script_is_this_file",
             os.path.isfile(state.get("scriptPath") or "")
             and os.path.samefile(logical, state["scriptPath"]))])),
        ("args_canonical_sha256", args_sha),
        # the SAME invocation, proved against the two artifacts that carry it:
        # the published one this segment was launched from, and the args the
        # runtime itself saved into the official state
        ("args_equal_the_published_invocation",
         G._plain(args) == G._plain(published("invocation.seg04.json")["args"])),
        ("args_equal_the_state_the_runtime_saved",
         G._plain(args) == G._plain(state.get("args"))),
        ("lanes_match_the_approved_list",
         [r["lane_id"] for r in G._read(G.receipt_path(RUN, 4))["rows"]]
         == approved["lanes"]),
        ("steps", RECORDS)])
    io.open(OUT + "/CANDIDATE_PREPARE_1794.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    print("  segment 4 published: receipt %s  script %s"
          % ((receipt_sha or "")[:16], G._sha_file(logical)[:16]))
    print("  the state's script IS this file: %s"
          % doc["segment4"]["state_script_is_this_file"])
    print("  same 34 lanes as approved: %s   args equal published: %s   "
          "args equal the saved state: %s"
          % (doc["lanes_match_the_approved_list"],
             doc["args_equal_the_published_invocation"],
             doc["args_equal_the_state_the_runtime_saved"]))
    return 0


def phase_intake():
    root_sha = G._sha_file(G.root_path(RUN))
    receipt_sha = G._sha_file(G.receipt_path(RUN, 4))
    logical = G.script_path(RUN, 4)
    state = json.load(io.open(BATCH_STATE, encoding="utf-8"))
    same = os.path.isfile(state.get("scriptPath") or "") and \
        os.path.samefile(logical, state["scriptPath"])
    print("  the segment-4 intake resolves to the executed file: %s" % same)
    run_id = os.path.basename(BATCH_STATE)[len("wf_"):-len(".json")]
    i = run("seg4_intake", ["ingest", "4", receipt_sha, run_id])
    doc = collections.OrderedDict([
        ("phase", "intake"), ("root_sha256", root_sha),
        ("receipt_sha256", receipt_sha),
        ("script_is_the_executed_file", same),
        ("exit", i.returncode),
        ("official_rows", field(i.stdout, "OFFICIAL_ROWS")),
        ("ledger", field(i.stdout, "LEDGER")),
        ("retry", field(i.stdout, "RETRY")),
        ("nonvalid", field(i.stdout, "NONVALID")),
        ("clean", field(i.stdout, "SEGMENT_CLEAN")),
        ("steps", RECORDS)])
    io.open(OUT + "/CANDIDATE_INTAKE_1794.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    for key in ("official_rows", "ledger", "retry", "nonvalid", "clean"):
        print("  %-14s %s" % (key, doc[key]))
    if i.returncode != 0:
        print(i.stdout[-1200:]); print(i.stderr[-600:])
    return 0 if doc["clean"] == "True" else 1


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    PHASE = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    sys.exit(phase_prepare() if PHASE == "prepare" else phase_intake())
