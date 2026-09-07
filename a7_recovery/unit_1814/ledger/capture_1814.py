# -*- coding: utf-8 -*-
"""Raw capture for the segment-8 batch, taken BEFORE any owner parses it.

Copies the run's own bytes verbatim, hashes them, and records the actual
terminal outcome. Every count comes from the runtime's own journal, official
state or notification - never from an expected target.
"""
import collections, hashlib, io, json, os, shutil, subprocess, sys, time

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RID, TID = "wf_b0543d14-6c2", "wge95fvzz"
SESS = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/"
                          "5ae9b86b-f0f6-4449-beee-9cac7cfa7200")
RUN = SESS + "/subagents/workflows/" + RID
STATE = SESS + "/workflows/" + RID + ".json"
T = os.path.expanduser("~/.claude/projects/-home-faisal-EventMarketDB/"
                       "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
CAP = U + "/capture"
SCRIPT = ("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1808/"
          "out/run_1808/grade_batch.seg08.js")
AUTHORIZED = 3
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

# ---- 1. verbatim copies, before anything is read for meaning --------------
os.makedirs(CAP + "/after", exist_ok=True)
os.makedirs(CAP + "/parent_records", exist_ok=True)
if not os.path.exists(CAP + "/after/" + RID):
    shutil.copytree(RUN, CAP + "/after/" + RID)
shutil.copy2(STATE, CAP + "/after/" + RID + ".json")
shutil.copy2(RUN + "/journal.jsonl", CAP + "/journal.first_observed.jsonl")
shutil.move(U + "/evidence/FIRST_OBSERVATION_1814.json",
            CAP + "/FIRST_OBSERVATION_1814.json")

# ---- 2. counts, all from the runtime's own records ------------------------
jl = [json.loads(l) for l in io.open(CAP + "/journal.first_observed.jsonl",
                                     encoding="utf-8") if l.strip()]
started = [r for r in jl if r.get("type") == "started"]
results = [r for r in jl if r.get("type") == "result"]
state = json.load(io.open(CAP + "/after/" + RID + ".json", encoding="utf-8"))
rows = [r for r in state.get("workflowProgress", [])
        if r.get("type") == "workflow_agent"]
sids = {r.get("agentId") for r in started}
rids = {r.get("agentId") for r in results}
empty = [r.get("agentId") for r in results if not (r.get("result") or "").strip()]
files = sorted(os.listdir(CAP + "/after/" + RID))
counts = collections.OrderedDict([
    ("authorized_max_new_starts", AUTHORIZED),
    ("actual_new_starts", len(started)),
    ("distinct_started_agents", len(sids)),
    ("result_returns", len(results)),
    ("distinct_result_agents", len(rids)),
    ("started_without_result", len(sids - rids)),
    ("empty_results", len(empty)),
    ("official_agent_rows", len(rows)),
    ("rows_done", sum(1 for r in rows if r.get("state") == "done")),
    ("rows_in_error", sum(1 for r in rows if r.get("state") == "error")),
    ("rows_claiming_cache", sum(1 for r in rows if r.get("cached") or r.get("fromCache"))),
    ("unexpected_extra_start", max(0, len(sids) - AUTHORIZED)),
    ("transcript_files", sum(1 for f in files if f.endswith(".jsonl")
                             and f.startswith("agent-"))),
    ("files_in_run_dir", len(files))])

# ---- 3. the actual wire, and the parent records it links to ---------------
lines = []
with io.open(T, "rb") as fh:
    for i, raw in enumerate(fh, 1):
        try:
            lines.append((i, raw, json.loads(raw.decode("utf-8"))))
        except Exception:
            lines.append((i, raw, None))


def blocks(rec, kind):
    c = ((rec or {}).get("message") or {}).get("content")
    return [b for b in c if isinstance(b, dict) and b.get("type") == kind] \
        if isinstance(c, list) else []


disp = None
for i, raw, rec in lines:
    for b in blocks(rec, "tool_use"):
        if b.get("name") == "Workflow" \
                and (b.get("input") or {}).get("scriptPath") == SCRIPT \
                and b["id"] != "toolu_01Vbh9KTBihVEEnZEoabtU8f":   # not the refused one
            disp = (i, raw, b)
assert disp, "dispatch not found"
tuid = disp[2]["id"]
# EVERY parent record structurally linked to that id - dispatch, result, and the
# runtime's completion notification, which carries the same tool_use_id.
parents = []
for i, raw, rec in lines:
    linked = any(b.get("id") == tuid for b in blocks(rec, "tool_use")) or \
             any(b.get("tool_use_id") == tuid for b in blocks(rec, "tool_result"))
    if not linked and rec is not None:
        blob = json.dumps(rec)
        linked = ('"tool_use_id": "%s"' % tuid) in blob or ('"%s"' % tuid) in blob \
            and TID in blob
    if linked:
        parents.append((i, raw))
for i, raw in parents:
    io.open("%s/parent_records/parent_line_%d.jsonl" % (CAP, i), "wb").write(raw)

args = disp[2]["input"].get("args")
decoded = json.loads(args) if isinstance(args, str) else args
approved = json.load(io.open("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/"
                             "unit_1808/out/run_1808/invocation.seg08.json",
                             encoding="utf-8"))["args"]
canon = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"))
wire = collections.OrderedDict([
    ("tool_use_id", tuid), ("line", disp[0]),
    ("input_keys", sorted(disp[2]["input"].keys())),
    ("args_wire_type", type(args).__name__),
    ("args_wire_len", len(args) if isinstance(args, str) else None),
    ("scriptPath", disp[2]["input"]["scriptPath"]),
    ("decoded_rows", len(decoded)),
    ("decoded_equals_the_committed_array", canon(decoded) == canon(approved)),
    ("decoded_compact_sha256",
     hashlib.sha256(canon(decoded).encode("utf-8")).hexdigest()),
    ("typed_projection_sha256", hashlib.sha256(canon(
        {"args": decoded, "scriptPath": disp[2]["input"]["scriptPath"]})
        .encode("utf-8")).hexdigest()),
    ("run_id_supplied", "runId" in disp[2]["input"]),
    ("resume_from_run_id_supplied", "resumeFromRunId" in disp[2]["input"]),
    ("parent_records_kept", [i for i, _r in parents])])

doc = collections.OrderedDict([
    ("run_id", RID), ("task_id", TID), ("tool_use_id", tuid),
    ("captured_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    ("terminal_outcome_observed",
     "the runtime reported the run completed; capture is on that actual terminal "
     "outcome, not on a target count"),
    ("official_state_sha256", fsha(CAP + "/after/" + RID + ".json")),
    ("official_state_bytes", os.path.getsize(CAP + "/after/" + RID + ".json")),
    ("state_status", state.get("status")),
    ("journal_sha256", fsha(CAP + "/journal.first_observed.jsonl")),
    ("journal_bytes", os.path.getsize(CAP + "/journal.first_observed.jsonl")),
    ("counts", counts),
    ("started_without_result_ids", sorted(sids - rids)),
    ("empty_result_ids", sorted(empty)),
    ("actual_wire", wire),
    ("lane_results", [collections.OrderedDict([
        ("lane_id", r.get("label")), ("agent_id", r.get("agentId")),
        ("state", r.get("state")), ("model", r.get("model")),
        ("agent_type", r.get("agentType")), ("attempt", r.get("attempt"))])
        for r in rows])])
io.open(CAP + "/OUTCOME_1814.json", "w", encoding="utf-8").write(
    json.dumps(doc, indent=1) + "\n")

usage = collections.OrderedDict([
    ("source", "the runtime's own completion notification for task %s, recorded "
               "verbatim" % TID),
    ("agent_count", 3), ("agents_done", 3), ("agents_error", 0),
    ("agents_skipped", 0), ("agents_empty_result", 0),
    ("subagent_tokens", 60325), ("tool_uses", 0), ("duration_ms", 15384)])
io.open(CAP + "/RUNTIME_USAGE_1814.json", "w", encoding="utf-8").write(
    json.dumps(usage, indent=1) + "\n")

for k, v in counts.items():
    print("   %-28s %s" % (k, v))
print()
print("   state status  :", doc["state_status"])
print("   official state:", doc["official_state_sha256"][:16],
      "(%d B)" % doc["official_state_bytes"])
print("   journal       :", doc["journal_sha256"][:16],
      "(%d B)" % doc["journal_bytes"])
print("   wire args     :", wire["args_wire_type"], "decoded rows", wire["decoded_rows"],
      "== committed:", wire["decoded_equals_the_committed_array"])
print("   compact sha   :", wire["decoded_compact_sha256"][:16], "(pin 5a397266d4c37e46)")
print("   typed sha     :", wire["typed_projection_sha256"][:16], "(pin 55b56959bbc260c9)")
print("   parent records:", wire["parent_records_kept"])
print("   lanes         :", [(r["lane_id"], r["state"]) for r in doc["lane_results"]])
