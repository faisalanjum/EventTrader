"""Harvest and prove the ONE authorized final-key signer call (Codex SEQ 1512 items 2-3).

The raw is preserved before parsing. The official Workflow state, run id, agent id,
transcript, first-user prompt bytes, launcher bytes, parent session, model, effort,
agent type, runtime model id and zero tool use are bound through the shared owners
(build_kfields_key._official_proof / direct_result, audit_worker_access._jsonl).
Parsing is build_kfields_final.read_signature only. Any proof fault stops with no
credit and no lock. Usage: harvest_final_sign.py <run_id> <attempt>
"""
import hashlib, io, json, os, sys, time
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
SESSION = "5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
SESS = "/home/faisal/.claude/projects/-home-faisal-EventMarketDB/" + SESSION
SIG = S + "/lock/final_key_candidate_1511/signer"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_key as K, build_kfields_final as F, raw_transport as RT, audit_worker_access as AUD
sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()
run_id, attempt = sys.argv[1], int(sys.argv[2])
MAN = json.load(io.open(SIG + "/signer.manifest.json", encoding="utf-8"))
PROMPT = io.open(SIG + "/signer_prompt.txt", encoding="utf-8").read(); SCRIPT = io.open(SIG + "/final_sign.attempt%d.js" % attempt, encoding="utf-8").read()
assert sha(PROMPT) == MAN["prompt_sha256"] and sha(SCRIPT) == MAN["script_sha256"], "the frozen packet moved"
state = os.path.join(SESS, "workflows", run_id + ".json")
for _ in range(360):
    if os.path.isfile(state):
        d = json.load(io.open(state, encoding="utf-8"))
        if d.get("status") in ("completed", "failed", "error"): break
    time.sleep(10)
else:
    print("STOP: %s never reached a terminal state" % run_id); raise SystemExit(2)
d = json.load(io.open(state, encoding="utf-8"))
rows = [r for r in d.get("workflowProgress") or [] if r.get("type") == "workflow_agent"]
bad = []
if d.get("status") != "completed": bad.append("status %s" % d.get("status"))
if len(rows) != 1: bad.append("%d agent rows" % len(rows))
if d.get("runId") != run_id: bad.append("runId %r" % d.get("runId"))
if d.get("script") != SCRIPT: bad.append("the state did not run the frozen launcher bytes")
sp = d.get("scriptPath")
if sp and sha(io.open(sp, "rb").read()) != MAN["script_sha256"]: bad.append("scriptPath bytes are not the frozen launcher")
sdir, sid = AUD._official_location(state)
if sdir is None or sid != SESSION: bad.append("the state is not an official state of the parent session")
if bad: print("STOP: %s" % bad); raise SystemExit(2)
row = rows[0]; agent = row.get("agentId")
got = K.direct_result(d) or {}
for field, want in (("role", "signer"), ("attempt", attempt), ("model", K.MODEL), ("effort", K.EFFORT), ("agentType", K.AGENT_TYPE)):
    if got.get(field) != want: bad.append("result %s is %r, not %r" % (field, got.get(field), want))
if row.get("label") != "a4-final-signer": bad.append("label %r" % row.get("label"))
if row.get("state") != "done": bad.append("agent row state %r" % row.get("state"))
if d.get("totalToolCalls") != 0 or (row.get("toolCalls") not in (0, None)): bad.append("tool calls recorded: %r / %r" % (d.get("totalToolCalls"), row.get("toolCalls")))
tp = os.path.join(sdir or "", "subagents", "workflows", run_id, "agent-%s.jsonl" % agent)
recs = AUD._jsonl(tp) if os.path.isfile(tp) else None
if recs is None: bad.append("the transcript cannot be read whole")
else:
    asst = [r for r in recs if r.get("type") == "assistant"]; users = [r for r in recs if r.get("type") == "user"]
    tools = [b for r in asst for b in ((r.get("message") or {}).get("content") or []) if isinstance(b, dict) and b.get("type") in ("tool_use", "tool_result")]
    if tools: bad.append("%d tool blocks in the transcript" % len(tools))
    if {r.get("sessionId") for r in recs} != {SESSION}: bad.append("a transcript record carries a foreign sessionId")
    if {r.get("agentId") for r in recs} != {agent}: bad.append("a transcript record carries a foreign agentId")
    models = {(r.get("message") or {}).get("model") for r in asst} - {None}
    if models != {K.RUNTIME_MODEL_ID} if hasattr(K, "RUNTIME_MODEL_ID") else not models: bad.append("transcript runtime model ids %r" % sorted(models))
    if len(users) < 1 or users[0]["message"]["content"] != PROMPT: bad.append("the first user turn is not the frozen prompt bytes")
final, complete, why = K._official_proof(state, PROMPT)
bad += why
if got.get("text") != final: bad.append("the returned text is not the proved final segment")
if bad: print("STOP: %s" % bad); raise SystemExit(2)
raw_path = RT.save_raw(complete, SIG, "final_sign.attempt%d" % attempt)
raw_path = raw_path if isinstance(raw_path, str) else os.path.join(SIG, RT._raw_filename("final_sign.attempt%d" % attempt))
assert io.open(raw_path, encoding="utf-8").read() == complete
print("  raw %s sha %s (%d chars)" % (os.path.basename(raw_path), sha(complete), len(complete)))
print("  run %s | agent %s | model %s | effort %s | %s | tools %s | runtime %s" % (run_id, agent, got.get("model"), got.get("effort"), got.get("agentType"), d.get("totalToolCalls"), sorted(models)))
obj, problems = F.read_signature(complete)
outcome = "invalid_response" if problems else ("signed" if obj["signed"] is True else "refused")
RT.write_new(SIG + "/final_sign.attempt%d.evidence.json" % attempt, json.dumps({
    "run_id": run_id, "agent_id": agent, "attempt": attempt, "state_path": state, "transcript_path": tp,
    "state_sha256": sha(io.open(state, "rb").read()), "transcript_sha256": sha(io.open(tp, "rb").read()),
    "raw_path": raw_path, "raw_sha256": sha(complete), "raw_chars": len(complete),
    "prompt_sha256": sha(PROMPT), "script_sha256": sha(SCRIPT), "parent_session_id": SESSION,
    "model": got.get("model"), "effort": got.get("effort"), "agent_type": got.get("agentType"), "runtime_model_ids": sorted(models),
    "tool_calls": d.get("totalToolCalls"), "total_tokens": d.get("totalTokens"), "duration_ms": d.get("durationMs"),
    "parser": "build_kfields_final.read_signature", "parser_problems": problems, "outcome": outcome,
    "retry_law": {"owner": "build_kfields_final.RETRYABLE", "retryable": list(F.RETRYABLE)}}, indent=1))
if problems:
    print("  OUTCOME: invalid_response (%s) -> the one identical-bytes retry is permitted" % problems[0]); raise SystemExit(3)
RT.write_new(SIG + "/final_sign.attempt%d.reply.json" % attempt, json.dumps(obj, indent=1))
print("  OUTCOME: signed=%r blocked=%r" % (obj["signed"], obj["blocked"])); print("  why: %s" % obj["why"][:300])
raise SystemExit(0 if (obj["signed"] is True and obj["blocked"] == []) else 4)
