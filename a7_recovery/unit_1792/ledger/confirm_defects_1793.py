# -*- coding: utf-8 -*-
"""Independently confirm the three defects Codex SEQ 1793 reported. Read-only."""
import hashlib, io, json, sys
R = "/home/faisal/EventMarketDB-driver-recovery"
U = R + "/a7_recovery/unit_1792"
sys.path.insert(0, U + "/view/harness_g1v3")
import audit_worker_access as AUD                                # noqa: E402
D = R + "/a7_recovery/unit_1786/capture/after/wf_41b934cf-f76"
decl = [json.load(io.open(U + "/evidence/declared_input_attachments.json")
                  )["attachments"][0]["canonical_sha256"]]
recs = AUD._jsonl(D + "/agent-ac7a389a55bea55ce.jsonl")
pin = hashlib.sha256(((recs[0].get("message") or {}).get("content") or ""
                      ).encode("utf-8")).hexdigest()
what = sys.argv[1]
if what == "positive":
    print("PASSES" if AUD._g1_shape_problems(recs, "x", decl) == [] else "REFUSED")
elif what == "missing":
    r = [recs[0]] + recs[2:]
    print("REFUSED" if AUD._g1_shape_problems(r, "x", decl) else "ACCEPTED")
elif what == "type":
    r = list(recs); r[1] = dict(r[1], type="system")
    print("REFUSED" if AUD._g1_shape_problems(r, "x", decl) else "ACCEPTED")
elif what == "moved":
    r = [recs[0], recs[2], recs[1]] + recs[3:]
    print("REFUSED" if AUD._input(r, pin, decl) else "ACCEPTED")
