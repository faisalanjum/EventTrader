# -*- coding: utf-8 -*-
"""Corrected population proof: strict whole-file reader, BOTH boundaries.

Codex SEQ 1792 item 1. Membership comes from the journal AND the official
served rows; every transcript is read with the owners' own _jsonl, which
returns None if ANY line is malformed - nothing is silently discarded.
"""
import hashlib, io, json, os, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
sys.path.insert(0, R + "/a7_recovery/unit_1792/view/harness_g1v3")
import audit_worker_access as AUD                                # noqa: E402
CAP = R + "/a7_recovery/unit_1786/capture"
RUN, STATE, BEFORE = CAP + "/after/wf_41b934cf-f76", CAP + "/after/wf_41b934cf-f76.json", CAP + "/journal.before.jsonl"
served = {}
for l in io.open(RUN + "/journal.jsonl", encoding="utf-8"):
    if l.strip():
        r = json.loads(l)
        if r.get("type") == "result":
            served[r["agentId"]] = r
st = json.load(io.open(STATE, encoding="utf-8"))
official = {p["agentId"] for p in st.get("workflowProgress", [])
            if p.get("type") == "workflow_agent" and p.get("agentId")}
cached = {json.loads(l)["agentId"] for l in io.open(BEFORE, encoding="utf-8")
          if l.strip() and json.loads(l).get("type") == "result"}
new = sorted(set(served) - cached)
print("  served (journal) %d   official rows %d   agree: %s"
      % (len(served), len(official), set(served) == official))
print("  cached controls %d   new workers %d" % (len(cached), len(new)))
unread = shape = inp = 0
for aid in sorted(served):
    recs = AUD._jsonl(os.path.join(RUN, "agent-%s.jsonl" % aid))
    if recs is None:
        unread += 1
        continue
    c = (recs[0].get("message") or {}).get("content")
    pin = hashlib.sha256((c if isinstance(c, str) else json.dumps(c)).encode()).hexdigest()
    if AUD._g1_shape_problems(recs, aid):
        shape += 1
    if AUD._input(recs, pin):
        inp += 1
print("  unreadable transcripts (strict reader) : %d" % unread)
print("  refused by the SHAPE owner             : %d" % shape)
print("  refused by the INPUT-TOPOLOGY owner    : %d" % inp)
inc = AUD._jsonl(os.path.join(RUN, "agent-a72461c662aeeac39.jsonl"))
print("  the old incomplete worker is preserved and NOT served: %s"
      % ("a72461c662aeeac39" not in served and inc is not None))
