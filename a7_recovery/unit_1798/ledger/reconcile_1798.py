# -*- coding: utf-8 -*-
"""Recompute the lane population and reconcile the physical ledger (item 1).

Runs inside the boundary against the PUBLISHED candidate run, read-only. Every
selection decision is made by the existing owners - lane_states, segments,
segment_state, latest_retry - never by counting here. Completion is taken from
the finalized receipts and the saved official states, never from the fact that
a reply happens to parse.
"""
import collections
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
RUN = S + "/g1_precall_run_1525"
OUT = "/tmp/a7_logs_1781"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
os.environ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = "128000"
import a7_g1_build as G                                          # noqa: E402
import audit_worker_access as AUD                                # noqa: E402


def main():
    root = G._read(G.root_path(RUN))
    rows = root["rows"]
    segs = G.segments(RUN)
    states = G.lane_states(RUN)
    called = sorted(l for l, v in states.items() if v == "called")
    pending = [r["lane_id"] for r in rows if states.get(r["lane_id"]) != "called"]

    per_seg, ledger_calls, official = [], 0, []
    for n in segs:
        receipt = G._read(G.receipt_path(RUN, n))
        fin = G._read(G.finalization_path(RUN, n)) if os.path.isfile(
            G.finalization_path(RUN, n)) else None
        state_doc = G._read(G.state_path(RUN, n))
        for p in state_doc["states"]:
            st = json.load(io.open(p, encoding="utf-8"))
            agents = [x for x in st.get("workflowProgress", [])
                      if x.get("type") == "workflow_agent" and x.get("agentId")]
            cached = [x for x in agents if x.get("cached")]
            official.append(collections.OrderedDict([
                ("segment", n), ("state", os.path.basename(p)),
                ("agent_rows", len(agents)),
                ("re_returned_from_cache", len(cached)),
                ("newly_started", len(agents) - len(cached))]))
            ledger_calls += len(agents) - len(cached)
        per_seg.append(collections.OrderedDict([
            ("segment", n), ("attempt", receipt.get("attempt")),
            ("rows", len(receipt["rows"])),
            ("state", G.segment_state(RUN, n)),
            ("ledger", G._plain(fin["ledger"]) if fin else None),
            ("retry", fin["retry"] if fin else None),
            ("uncalled", fin["uncalled"] if fin else None),
            ("problems", G._plain(fin["problems"]) if fin else None)]))

    retry_owed = G.latest_retry(RUN)
    doc = collections.OrderedDict([
        ("root_sha256", G._sha_file(G.root_path(RUN))),
        ("candidate_sha256", root["candidate_sha256"]),
        ("required_lanes", len(rows)),
        ("selected_called_lanes", len(called)),
        ("never_started_primary_lanes", len(pending)),
        ("lane_state_values", dict(collections.Counter(states.values()))),
        ("segments", per_seg),
        ("official_states", official),
        ("retry_still_owed_by_the_owner", retry_owed),
        ("physical_calls_from_saved_official_states", ledger_calls),
        ("note", "a re-returned cached row is NOT a call; only newly started agent "
                 "rows are counted, and completion comes from the finalized receipts "
                 "and saved official states, never from a reply that happens to parse"),
        ("pending_lane_ids", pending)])
    io.open(OUT + "/RECONCILE_1798.json", "w", encoding="utf-8").write(
        json.dumps(doc, indent=1) + "\n")
    print("  root                : %s" % doc["root_sha256"])
    print("  required lanes      : %d" % doc["required_lanes"])
    print("  selected (called)   : %d" % doc["selected_called_lanes"])
    print("  never started       : %d" % doc["never_started_primary_lanes"])
    print("  lane states         : %s" % doc["lane_state_values"])
    for s in per_seg:
        print("    seg %s attempt %s rows %-2d %s ledger %s retry %s"
              % (s["segment"], s["attempt"], s["rows"], s["state"], s["ledger"], s["retry"]))
    for o in official:
        print("    state %s: %d rows = %d newly started + %d re-returned from cache"
              % (o["state"], o["agent_rows"], o["newly_started"], o["re_returned_from_cache"]))
    print("  physical new calls in these segments : %d" % ledger_calls)
    print("  retry still owed by the owner        : %s" % retry_owed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
