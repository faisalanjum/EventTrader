# -*- coding: utf-8 -*-
"""Codex SEQ 2016: PRESERVE FIRST, for one clarified blind review reading.

The SEQ 2004 capture owner with only the evidence path and the expected-receipt
path changed: copy the official state, its transcript and the exact returned
text into THIS unit BEFORE any proof, parse or accounting, and report what the
runtime actually recorded in the workflow row AND in the transcript.
Read-only against the official store.
Usage: capture_2015.py <runId>
"""
import collections
import hashlib
import io
import json
import os
import sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A + "/unit_2008/harness_g1v3")
import raw_transport as RT                                         # noqa: E402

UNIT = A + "/unit_2015_real_reviews"
SESSION = "5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
PROJ = "/home/faisal/.claude/projects/-home-faisal-EventMarketDB/" + SESSION
OUTDIR = UNIT + "/evidence/review"
RECEIPT = UNIT + "/key_closure/review_2015/receipt.json"
run_id = sys.argv[1]


def sha(b):
    return hashlib.sha256(b).hexdigest()


res = collections.OrderedDict([("run_id", run_id)])


def preserve(path, raw):
    """Reuse identical UTF-8 workflow evidence; never replace a different copy."""
    if os.path.isfile(path):
        with io.open(path, "rb") as fh:
            if fh.read() != raw:
                raise ValueError("saved evidence differs: " + path)
        return
    RT.write_new(path, raw.decode("utf-8"))


state_path = os.path.join(PROJ, "workflows", run_id + ".json")
res["official_state_path"] = state_path
res["official_state_exists"] = os.path.isfile(state_path)
if not res["official_state_exists"]:
    print(json.dumps(res, indent=1))
    raise SystemExit(3)
raw = io.open(state_path, "rb").read()
res["official_state_sha256"] = sha(raw)
preserve(os.path.join(OUTDIR, run_id + ".state.json"), raw)
doc = json.loads(raw.decode("utf-8"))
rows = [r for r in (doc.get("workflowProgress") or [])
        if r.get("type") == "workflow_agent"]
res["state"] = collections.OrderedDict([
    ("runId", doc.get("runId")), ("status", doc.get("status")),
    ("totalToolCalls", doc.get("totalToolCalls")),
    ("agentCount", doc.get("agentCount")),
    ("durationMs", doc.get("durationMs")),
    ("totalTokens", doc.get("totalTokens")),
    ("defaultModel", doc.get("defaultModel")),
    ("script_sha256", sha((doc.get("script") or "").encode("utf-8"))),
    ("scriptPath", doc.get("scriptPath")),
    ("workflow_agent_rows", len(rows))])
res["row"] = ({k: rows[0].get(k) for k in
               ("label", "state", "agentId", "model", "effort", "agentType",
                "toolCalls", "lastToolName", "status")} if len(rows) == 1
              else rows)
got = doc.get("result") if isinstance(doc.get("result"), dict) else None
res["returned_object_keys"] = sorted(got) if got else None
if got:
    res["returned"] = {k: got.get(k) for k in
                       ("task_id", "kind", "blind", "attempt", "model",
                        "effort", "agentType")}
    text = got.get("text")
    res["returned_text_is_string"] = isinstance(text, str)
    if isinstance(text, str):
        res["returned_text_bytes"] = len(text.encode("utf-8"))
        res["returned_text_sha256"] = sha(text.encode("utf-8"))
        preserve(os.path.join(OUTDIR, run_id + ".returned.txt"),
                 text.encode("utf-8"))

agent_id = rows[0].get("agentId") if len(rows) == 1 else None
tp = os.path.join(PROJ, "subagents", "workflows", run_id,
                  "agent-%s.jsonl" % agent_id) if agent_id else None
res["transcript_path"] = tp
if tp and os.path.isfile(tp):
    tb = io.open(tp, "rb").read()
    res["transcript_sha256"] = sha(tb)
    res["transcript_bytes"] = len(tb)
    preserve(os.path.join(OUTDIR, run_id + ".transcript.jsonl"), tb)
    recs = [json.loads(l) for l in tb.decode("utf-8").splitlines() if l.strip()]
    asst = [r for r in recs if r.get("type") == "assistant"]
    res["transcript"] = collections.OrderedDict([
        ("records", len(recs)),
        ("record_types", [r.get("type") for r in recs][:8]),
        ("assistant_records", len(asst)),
        ("models_named", sorted({(r.get("message") or {}).get("model")
                                 for r in asst}, key=str)),
        ("efforts_named", sorted({r.get("effort") for r in asst}, key=str)),
        ("continuation_groups", len({((r.get("message") or {}).get("id"),
                                      r.get("requestId")) for r in asst})),
        ("tool_blocks", len([b for r in asst
                             for b in ((r.get("message") or {}).get("content") or [])
                             if isinstance(b, dict)
                             and b.get("type") in ("tool_use", "tool_result")])),
        ("first_record_type", recs[0].get("type") if recs else None),
        ("first_prompt_sha256", sha(((recs[0].get("message") or {})
                                     .get("content") or "").encode("utf-8"))
         if recs and isinstance((recs[0].get("message") or {}).get("content"), str)
         else None)])
# THE REVIEWER IS THE TESTED SONNET ROLE, whose identity this run's own receipt
# already records; there is no key-role file on this side.
res["expected_transport"] = json.loads(
    io.open(RECEIPT, encoding="utf-8").read())["transport"]
res["row_model_matches_expected"] = (
    res.get("row", {}).get("model")
    == res["expected_transport"]["runtime_model_id"]
    if isinstance(res.get("row"), dict) else None)
res["preserved_files"] = sorted(os.listdir(OUTDIR))
print(json.dumps(res, indent=1, default=str))
