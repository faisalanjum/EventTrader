# -*- coding: utf-8 -*-
"""Codex SEQ 2018: PRESERVE-FIRST harvester for the 33 final adjudications.

Host side only. For every launch still in flight whose official state has
landed, it preserves the run through the capture owner BEFORE anything judges
it and marks it in the durable ledger. It launches nothing, judges nothing and
finalizes nothing. Run it again as more results land.
"""
import collections
import datetime
import io
import json
import os
import subprocess
import sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A + "/unit_2008/harness_g1v3")
import raw_transport as RT                                         # noqa: E402

UNIT = A + "/unit_2017_final_source_key"
LEDGER = UNIT + "/evidence/final_key/launch_ledger_2017.json"
CAPTURE = UNIT + "/capture_2017.py"
WORKFLOWS = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
             "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/workflows")


def ready(run_id):
    path = os.path.join(WORKFLOWS, run_id + ".json")
    if not os.path.isfile(path):
        return False
    try:
        doc = json.loads(io.open(path, encoding="utf-8").read())
    except ValueError:
        return False
    return doc.get("status") is not None and doc.get("result") is not None


led = json.loads(io.open(LEDGER, encoding="utf-8").read())
harvested = []
for row in led["launches"]:
    if row["state"] != "in_flight" or not ready(row["runId"]):
        continue
    got = subprocess.run([sys.executable, "-B", CAPTURE, row["runId"]],
                         capture_output=True, text=True)
    RT._atomic_json(os.path.join(UNIT, "evidence/final_key",
                                 "capture_%s.json" % row["runId"]),
                    {"stdout": got.stdout, "stderr": got.stderr,
                     "exit": got.returncode})
    if got.returncode != 0:
        row["state"] = "capture_failed"
        row["capture_stderr"] = (got.stderr or "")[:400]
        harvested.append({"label": row["label"], "result": "CAPTURE FAILED"})
        continue
    cap = json.loads(got.stdout)
    agent_row = cap.get("row") or {}
    row["state"] = "preserved"
    row["preserved_utc"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    row["official_state_sha256"] = cap["official_state_sha256"]
    row["transcript_sha256"] = cap.get("transcript_sha256")
    row["row_label"] = agent_row.get("label")
    row["row_model"] = agent_row.get("model")
    row["row_effort"] = agent_row.get("effort")
    row["row_agent_type"] = agent_row.get("agentType")
    row["row_tool_calls"] = agent_row.get("toolCalls")
    row["transcript_models"] = (cap.get("transcript") or {}).get("models_named")
    row["returned_text_sha256"] = cap.get("returned_text_sha256")
    row["returned_text_bytes"] = cap.get("returned_text_bytes")
    row["state_script_sha256"] = cap["state"]["script_sha256"]
    row["state_status"] = cap["state"]["status"]
    row["durationMs"] = cap["state"]["durationMs"]
    row["totalTokens"] = cap["state"]["totalTokens"]
    harvested.append({"label": row["label"], "runId": row["runId"],
                      "row_model": agent_row.get("model"),
                      "bytes": cap.get("returned_text_bytes"),
                      "ms": cap["state"]["durationMs"],
                      "script_matches_launch":
                          cap["state"]["script_sha256"] == row["script_sha256"]})
RT._atomic_json(LEDGER, led)

led = json.loads(io.open(LEDGER, encoding="utf-8").read())
print(json.dumps(collections.OrderedDict([
    ("harvested_now", harvested),
    ("states", dict(collections.Counter(r["state"] for r in led["launches"]))),
    ("in_flight", [r["label"] for r in led["launches"]
                   if r["state"] == "in_flight"]),
    ("launched_total", len(led["launches"]))]), indent=1, default=str))
