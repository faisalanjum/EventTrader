# G1 attempt-1 206-call run driver (Codex SEQ 1525). Zero logic of its own: it
# only sequences the EXISTING reviewed owners (a7_g1_build, a7_g1_workflow_gate,
# audit_worker_access) against the frozen root. The Workflow TOOL launches are
# driven by the operator (Core); this script does the Python lifecycle only.
#
#   prepare              -> next_admissible + publish_run + preflight for the
#                           NEXT segment; prints segment n, receipt_sha, scriptPath
#                           and the args file to launch. No call.
#   ingest N RSHA RUNID  -> locate the official wf_<runid>.json, record it,
#                           save_results (raw-first), finalize_segment; prints the
#                           per-segment ledger + every non-valid lane. STOP if any.
#   status               -> segments + states + lane_states tally.
import json
import os
import sys

S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import a7_g1_build as G                                          # noqa: E402
import a7_g1_workflow_gate as W                                  # noqa: E402
import audit_worker_access as AUD                                # noqa: E402
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"

CAND = S + "/g1_precall_cand_1525"
RUN = S + "/g1_precall_run_1525"


def root_sha():
    return G._sha_file(G.root_path(RUN))


def _find_wf_state(run_id):
    """The official Workflow state file for this run id, not a transcript dir."""
    hits = []
    for here, _dirs, files in os.walk(AUD.PROJECTS_ROOT):
        if os.path.basename(here) != "workflows":
            continue
        if os.path.basename(os.path.dirname(here)) == "subagents":
            continue
        name = "wf_%s.json" % run_id
        if name in files:
            hits.append(os.path.join(here, name))
    if len(hits) != 1:
        raise SystemExit("REFUSED: found %d official states for wf_%s.json (need "
                         "exactly one): %s" % (len(hits), run_id, hits[:3]))
    return hits[0]


def prepare():
    rsha = root_sha()
    lanes, size, problems = W.next_admissible(CAND, RUN, rsha)
    if problems:
        raise SystemExit("REFUSED next_admissible: %s" % problems[:3])
    pub, problems = G.publish_run(CAND, RUN, rsha, lanes)
    if problems:
        raise SystemExit("REFUSED publish_run: %s" % problems[:3])
    n = pub["segment"]
    receipt_sha = pub["receipt_sha256"]
    packet, problems = G.preflight(CAND, RUN, n, rsha, receipt_sha)
    if problems:
        raise SystemExit("REFUSED preflight: %s" % problems[:3])
    args_file = os.path.join(S, "g1_args_seg%02d.json" % n)
    with open(args_file, "w", encoding="utf-8") as fh:
        json.dump(packet["args"], fh)
    print("SEGMENT     :", n)
    print("LANES       :", len(lanes), "predicted_bytes", size)
    print("ROOT_SHA    :", rsha)
    print("RECEIPT_SHA :", receipt_sha)
    print("SCRIPT_PATH :", packet["scriptPath"])
    print("SCRIPT_BYTES:", os.path.getsize(packet["scriptPath"]))
    print("ARGS_FILE   :", args_file, "rows", len(packet["args"]))
    print("PREPARE_OK")


def retry(expect_lanes):
    """Publish + preflight the ONE lawful attempt-2 retry, through the existing
    owners (Codex SEQ 1527). The retry SET is derived from latest_retry; the
    expected-lane list is a Codex-directed guard, not the decision."""
    rsha = root_sha()
    rset = G.latest_retry(RUN)                 # {lane: seg} from latest attempt-1
    lanes = sorted(rset)
    print("RETRY_SET   :", lanes)
    if lanes != sorted(expect_lanes):
        raise SystemExit("REFUSED: derived retry set %s != expected %s"
                         % (lanes, sorted(expect_lanes)))
    pub, problems = G.publish_run(CAND, RUN, rsha, lanes, attempt=2)
    if problems:
        raise SystemExit("REFUSED publish_run(attempt=2): %s" % problems[:3])
    n = pub["segment"]
    receipt_sha = pub["receipt_sha256"]
    packet, problems = G.preflight(CAND, RUN, n, rsha, receipt_sha)
    if problems:
        raise SystemExit("REFUSED preflight: %s" % problems[:3])
    args_file = os.path.join(S, "g1_args_seg%02d.json" % n)
    with open(args_file, "w", encoding="utf-8") as fh:
        json.dump(packet["args"], fh)
    r = packet["args"][0]
    print("SEGMENT     :", n, "(attempt-2 retry)")
    print("LANES       :", len(lanes))
    print("RECEIPT_SHA :", receipt_sha)
    print("SCRIPT_PATH :", packet["scriptPath"])
    print("ARGS_FILE   :", args_file, "rows", len(packet["args"]))
    print("ROW_CHECK   : batch", r["batch_id"], "lane", r["lane_id"],
          "ordinal", r["ordinal"], "attempt", r["attempt"],
          "prompt_sha", r["prompt_sha256"])
    print("RETRY_OK")


def ingest(n, receipt_sha, run_id):
    rsha = root_sha()
    wf = _find_wf_state(run_id)
    official = json.load(open(wf, encoding="utf-8"))
    results = (official.get("result") or {}).get("results")
    if not isinstance(results, list):
        raise SystemExit("REFUSED: official state carries no result.results list")
    problems = G.record_official_state(RUN, n, wf, rsha, receipt_sha)
    if problems:
        raise SystemExit("REFUSED record_official_state: %s" % problems[:3])
    acc, problems = G.save_results(RUN, n, results, rsha, receipt_sha)
    if problems:
        print("SAVE_PROBLEMS:", problems[:5])
    final, rulings, problems = G.finalize_segment(CAND, RUN, n, rsha, receipt_sha)
    if problems:
        raise SystemExit("REFUSED finalize_segment: %s" % problems[:4])
    led = final["ledger"]
    nonvalid = [[lane, ok] for lane, ok in final["validity"] if not ok]
    print("SEGMENT     :", n, "state_file", os.path.basename(wf))
    print("OFFICIAL_ROWS:", len(results))
    print("LEDGER      :", G._plain(led))
    print("RETRY       :", final["retry"], "UNCALLED", final["uncalled"])
    print("NONVALID    :", nonvalid[:10], "why", G._plain(final["problems"]))
    clean = (led["valid"] == led["scheduled"] and led["invalid"] == 0
             and led["retry"] == 0 and led["uncalled"] == 0 and not nonvalid)
    print("SEGMENT_CLEAN:", clean)
    if not clean:
        print("STOP: segment %d is not clean; do NOT start the next segment" % n)


def status():
    rsha = root_sha()
    segs = G.segments(RUN)
    print("ROOT_SHA    :", rsha)
    print("SEGMENTS    :", segs)
    for n in segs:
        print("  seg", n, G.segment_state(RUN, n))
    st = G.lane_states(RUN)
    called = sum(1 for v in st.values() if v == "called")
    print("LANE_STATES : called", called, "of", len(G._read(G.root_path(RUN))["rows"]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "prepare":
        prepare()
    elif cmd == "retry":
        retry(sys.argv[2:])
    elif cmd == "ingest":
        ingest(int(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif cmd == "status":
        status()
    else:
        raise SystemExit("usage: prepare | retry LANE... | ingest N RECEIPT_SHA "
                         "RUNID | status")
