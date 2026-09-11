# -*- coding: utf-8 -*-
"""Codex SEQ 2016 pre-launch recheck. Host side, READ-ONLY, launches nothing.

Everything Codex told me to recheck before a single call is made: this session,
the frozen runtime and settings, the exact script bytes on both the durable and
the callable side, and that no matching result was ever produced.
"""
import collections
import glob
import hashlib
import io
import json
import os
import sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = A + "/unit_2015_real_reviews"
K = UNIT + "/key_closure"
LAUNCH = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
          "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/review_2015")
RECORD = UNIT + "/PREPARED_REVIEW_2015.core_prep2015_real.json"
AGENT = "/home/faisal/EventMarketDB/.claude/agents/lean-probe.md"
FREEZE = A + "/unit_2008/harness_g1v3/a2_runtime_freeze.json"

# Codex SEQ 2016's own frozen pins, checked here, never derived here.
PINS = {
    "record": "82b0138c3710b63a62eb77b76f6e592a58da75bfd739a351717576012ee1d47e",
    "map_launch": "78bcd74a2b2b46beb10e7339ffc732162060231ded144e966dea35822eb63073",
    "manifest": "4fbee22e8843953cf7d55685c4b34b7d323df0e738aa3d14bccb2b9418cea083",
    "receipt": "ed1fc8dc4be40f9f87a5fb6536c7a7e8f7b8fd52914ef26064e42c1174497f23",
    "composite": "4a93689b5b7d7add223ee4d92c94b7b816871be9e8c10f8bbcf330bb4815aa64",
    "clarified_hr": "ceef0f20e090e0793320fe1def79d958189d715a2dda7ddb48039e9ed6d0cc1b",
}
checks = []


def check(name, got, want):
    assert got == want, "%s: got %r want %r" % (name, got, want)
    checks.append(name)


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


record = json.loads(io.open(RECORD, encoding="utf-8").read())
freeze = json.loads(io.open(FREEZE, encoding="utf-8").read())
receipt = json.loads(io.open(K + "/review_2015/receipt.json", encoding="utf-8").read())
res = collections.OrderedDict()

check("1 the frozen inputs re-measure to Codex's pins",
      collections.OrderedDict([
          ("record", fsha(RECORD)),
          ("map_launch", fsha(UNIT + "/map_real_launch_2015.tsv")),
          ("manifest", fsha(K + "/closure_2015/hard_review.manifest.json")),
          ("receipt", fsha(K + "/review_2015/receipt.json")),
          ("composite", fsha(A + "/unit_2009/owner/a4_review_composite.py")),
          ("clarified_hr", fsha(A + "/unit_2008/harness_g1v3/"
                                    "build_kfields_hard_review.py"))]),
      collections.OrderedDict(sorted(PINS.items(), key=lambda kv: [
          "record", "map_launch", "manifest", "receipt", "composite",
          "clarified_hr"].index(kv[0]))))

check("2 this is the session the packet is bound to",
      [os.environ.get("CLAUDE_CODE_SESSION_ID"),
       receipt["transport"]["parent_session_id"]],
      [freeze["parent_session_id"], freeze["parent_session_id"]])
check("3 the required output setting is live in the launching process",
      [os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS"),
       receipt["transport"]["CLAUDE_CODE_MAX_OUTPUT_TOKENS"],
       freeze["max_output_tokens"]], ["128000", "128000", 128000])
check("4 no api key reaches the launching process",
      "ANTHROPIC_API_KEY" in os.environ, False)
check("5 the transport is the frozen Sonnet 5 high-effort lean probe",
      [receipt["transport"][k] for k in
       ("model_alias", "runtime_model_id", "effort", "agentType",
        "disallowedTools")],
      ["sonnet", "claude-sonnet-5", "high", "lean-probe", ["Read"]])
check("6 the served agent definition is the frozen one",
      [fsha(AGENT), freeze["live_proof"]["agent_definition_tools"]],
      [freeze["live_proof"]["agent_definition_sha256"], ["Read"]])

pinned = collections.OrderedDict(
    (os.path.basename(i["scriptPath"]), i) for i in record["invocations"])
for name, inv in pinned.items():
    durable = K + "/review_2015/scripts/" + name
    callable_ = LAUNCH + "/" + name
    check("7 durable and callable bytes are the pinned script: " + inv["label"],
          [fsha(durable), fsha(callable_),
           io.open(durable, "rb").read() == io.open(callable_, "rb").read()],
          [inv["script_sha256"], inv["script_sha256"], True])
check("8 the callable directory holds exactly the four",
      sorted(os.listdir(LAUNCH)), sorted(pinned))

# ---- nothing like this has ever been produced -----------------------------
wanted = {i["script_sha256"] for i in record["invocations"]}
states = sorted(glob.glob("/home/faisal/.claude/projects/*/*/workflows/*.json"))
hits = []
for path in states:
    try:
        doc = json.loads(io.open(path, encoding="utf-8").read())
    except ValueError:
        continue
    script = doc.get("script")
    sha = hashlib.sha256(script.encode("utf-8")).hexdigest() if isinstance(script, str) else None
    if sha in wanted or "review_2015" in (doc.get("scriptPath") or ""):
        hits.append(path)
res["live_workflow_states_scanned"] = len(states)
check("9 no live workflow state carries one of these four scripts", hits, [])

ledgers = sorted(glob.glob(A + "/unit_*/**/launch_ledger*.json", recursive=True))
rows = [r for p in ledgers for r in
        json.loads(io.open(p, encoding="utf-8").read()).get("launches", [])]
res["launch_ledgers"] = [os.path.relpath(p, A) for p in ledgers]
res["launch_ledger_entries"] = len(rows)
check("10 no launch ledger records one of them",
      [r["label"] for r in rows if r.get("script_sha256") in wanted
       or "review_2015" in r.get("scriptPath", "")], [])

check("11 the real run is still unserved",
      [receipt["states"], receipt["allowed"], receipt["attempt"],
       os.path.isfile(K + "/review_2015/finalization.json"),
       os.path.isdir(K + "/review_2015/raw"),
       os.path.isdir(K + "/review_2015/retry")],
      [[], [i["label"] for i in record["invocations"]], 1, False, False, False])

res["to_launch"] = [collections.OrderedDict([
    ("label", i["label"]), ("attempt", i["attempt"]),
    ("launch_path", LAUNCH + "/" + os.path.basename(i["scriptPath"])),
    ("script_sha256", i["script_sha256"])]) for i in record["invocations"]]
res["checks"] = checks
res["passed"] = len(checks)
res["launched"] = 0
print(json.dumps(res, indent=1, default=str))
