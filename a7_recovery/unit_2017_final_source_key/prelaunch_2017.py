# -*- coding: utf-8 -*-
"""Codex SEQ 2018 pre-launch recheck. Host side, READ-ONLY, launches nothing.

Everything that must hold before a single adjudication call is made: this
session, the frozen isolated key role and settings, the exact script bytes on
both the durable and the callable side, and that no matching result was ever
produced.
"""
import collections
import glob
import hashlib
import io
import json
import os
import sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = A + "/unit_2017_final_source_key"
KC = UNIT + "/key_closure"
LAUNCH = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
          "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/final_key_2017")
RECORD = UNIT + "/PREPARED_FINAL_KEY_2017.core_final2017_real.json"
AGENT = "/home/faisal/EventMarketDB/.claude/agents/lean-probe.md"
ROLE_FILE = A + "/unit_1997/owner/key_owner_role.json"
SESSION = "5ae9b86b-f0f6-4449-beee-9cac7cfa7200"

# Codex SEQ 2018's own accepted pins, checked here, never derived here.
PINS = collections.OrderedDict([
    ("record", "7aee43a7e296e68f4dffec91ce3c3229e685cace93b91933a5eb84412a62de89"),
    ("manifest", "ec8b702a0028030e5de4078fef9212fd02420db00e217cf067780e21fe3624b0"),
    ("receipt", "59939771b0f69c7a9cbcfa0633190de9f1380e5f548d5b3e7154eff820b85786"),
    ("map_launch", "a8654af2102a6f8c38b284c3f64cd0ffcf905ed48f94a537b4e0c6b868646274"),
])
EXPECTED_ROLE = collections.OrderedDict([
    ("kind", "LIVE"), ("model_alias", "opus"),
    ("runtime_model_id", "claude-opus-5"),
    ("workflow_row_model", "claude-opus-5[1m]"), ("effort", "high"),
    ("agentType", "lean-probe"), ("disallowedTools", ["Read"]),
    ("max_output_tokens", "128000")])
checks = []


def check(name, got, want):
    assert got == want, "%s: got %r want %r" % (name, got, want)
    checks.append(name)


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


record = json.loads(io.open(RECORD, encoding="utf-8").read())
role = json.loads(io.open(ROLE_FILE, encoding="utf-8").read())
receipt = json.loads(io.open(KC + "/key_run_2017/receipt.json",
                             encoding="utf-8").read())
res = collections.OrderedDict()

check("1 the accepted packet re-measures to Codex's pins",
      collections.OrderedDict([
          ("record", fsha(RECORD)),
          ("manifest", fsha(KC + "/key_package_2017/source_only_key.manifest.json")),
          ("receipt", fsha(KC + "/key_run_2017/receipt.json")),
          ("map_launch", fsha(UNIT + "/map_final_launch_2017.tsv"))]), PINS)
check("2 this is the session the packet is bound to",
      os.environ.get("CLAUDE_CODE_SESSION_ID"), SESSION)
check("3 the required output setting is live in the launching process",
      [os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS"),
       role["max_output_tokens"]], ["128000", "128000"])
check("4 no api key reaches the launching process",
      "ANTHROPIC_API_KEY" in os.environ, False)
check("5 the isolated key role is the frozen non-Sonnet one",
      collections.OrderedDict((k, role[k]) for k in EXPECTED_ROLE), EXPECTED_ROLE)
check("6 the served agent definition grants exactly Read",
      [fsha(AGENT), role["agentType"]],
      ["28736c63efd7d2ffb9066a02b47dc69751f8c0c867fa42d6546db812c7c8e515",
       "lean-probe"])

pinned = collections.OrderedDict(
    (os.path.basename(i["scriptPath"]), i) for i in record["invocations"])
bad_scripts = []
for name, inv in pinned.items():
    durable = KC + "/key_run_2017/scripts/" + name
    callable_ = LAUNCH + "/" + name
    if [fsha(durable), fsha(callable_),
            io.open(durable, "rb").read() == io.open(callable_, "rb").read()] \
            != [inv["script_sha256"], inv["script_sha256"], True]:
        bad_scripts.append(inv["label"])
check("7 durable and callable bytes are the pinned script, all 33",
      [len(pinned), bad_scripts], [33, []])
check("8 the callable directory holds exactly those 33",
      sorted(os.listdir(LAUNCH)), sorted(pinned))

wanted = {i["script_sha256"] for i in record["invocations"]}
states = sorted(glob.glob("/home/faisal/.claude/projects/*/*/workflows/*.json"))
hits = []
for path in states:
    try:
        doc = json.loads(io.open(path, encoding="utf-8").read())
    except ValueError:
        continue
    script = doc.get("script")
    sha = (hashlib.sha256(script.encode("utf-8")).hexdigest()
           if isinstance(script, str) else None)
    if sha in wanted or "key_run_2017" in (doc.get("scriptPath") or ""):
        hits.append(path)
res["live_workflow_states_scanned"] = len(states)
check("9 no live workflow state carries one of these 33 scripts", hits, [])

ledgers = sorted(glob.glob(A + "/unit_*/**/launch_ledger*.json", recursive=True))
rows = [r for p in ledgers for r in
        json.loads(io.open(p, encoding="utf-8").read()).get("launches", [])]
res["launch_ledgers"] = [os.path.relpath(p, A) for p in ledgers]
res["launch_ledger_entries"] = len(rows)
check("10 no launch ledger records one of them",
      [r["label"] for r in rows if r.get("script_sha256") in wanted
       or "key_run_2017" in r.get("scriptPath", "")], [])

check("11 the real run is still unserved",
      [receipt["states"], len(receipt["allowed"]), receipt["attempt"],
       os.path.isfile(KC + "/key_run_2017/finalization.json"),
       os.path.isdir(KC + "/key_run_2017/raw"),
       os.path.isdir(KC + "/key_run_2017/retry")],
      [[], 33, 1, False, False, False])

res["to_launch"] = [collections.OrderedDict([
    ("label", i["label"]), ("attempt", i["attempt"]),
    ("launch_path", LAUNCH + "/" + os.path.basename(i["scriptPath"])),
    ("script_sha256", i["script_sha256"])]) for i in record["invocations"]]
res["checks"] = checks
res["passed"] = len(checks)
res["launched"] = 0
print(json.dumps(res, indent=1, default=str))
