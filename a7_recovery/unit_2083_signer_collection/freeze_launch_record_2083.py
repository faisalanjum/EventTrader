# -*- coding: utf-8 -*-
"""Codex SEQ 2083: FREEZE the ONE authorized signer call. Launches nothing.

The SEQ 2070/2074/2080 freezer, adapted to the SIGNER's own shape: one label,
one attempt, one call. It re-hashes the candidate, ordinary binding, manifest,
prompt and script against the packet's own values, and records this authority,
the declared input source and the transport before anything may be launched.
Written once; a second run refuses.
Usage: freeze_launch_record_2083.py <out.json>
"""
import collections, hashlib, io, json, os, subprocess, sys
CAND = ("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/"
        "unit_2081_final_key_candidate/codex_cand2082_a")
SIG = CAND + "/candidate/signer"
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()
man = json.loads(io.open(SIG + "/signer.manifest.json", encoding="utf-8").read())
script = SIG + "/final_sign.attempt1.js"
prompt = SIG + "/signer_prompt.txt"
assert man["label"] == "a4-final-signer", man["label"]
assert man["state"] == "frozen, unrun", man["state"]
assert man["prompt_sha256"] == fsha(prompt), "prompt is not the manifest's"
assert man["script_sha256"] == fsha(script), "script is not the manifest's"
assert os.path.getsize(script) == man["script_bytes"] < man["transport_limit_bytes"]
assert not os.path.exists(SIG + "/final_sign.attempt1.evidence.json"), "already harvested"
assert not os.path.exists(SIG + "/final_sign.attempt1.raw.json"), "already answered"
src = man["expected_input_source"]
assert fsha(src["path"]) == src["sha256"], "the declared input source moved"
rec = collections.OrderedDict([
    ("authority", "Codex SEQ 2083"),
    ("authority_sha256", fsha("/home/faisal/.core827-orchestrator/CODEX_TO_CORE.md")),
    ("phase", "a7 REAL final-key signature, attempt 1"),
    ("label", man["label"]), ("role", "signer"),
    ("candidate", CAND + "/candidate"),
    ("candidate_result_sha256", fsha(CAND + "/RESULT.json")),
    ("ordinary_binding", CAND + "/ordinary_bound.json"),
    ("ordinary_sha256", fsha(CAND + "/ordinary_bound.json")),
    ("key_identity_sha256", fsha(CAND + "/candidate/key_identity.json")),
    ("manifest_sha256", fsha(SIG + "/signer.manifest.json")),
    ("prompt_sha256", man["prompt_sha256"]), ("script_path", script),
    ("script_sha256", man["script_sha256"]), ("script_bytes", man["script_bytes"]),
    ("transport_limit_bytes", man["transport_limit_bytes"]),
    ("expected_input", man["expected_input"]),
    ("expected_input_source", src),
    ("transport", man["transport"]),
    ("runtime_observed_before_launch", subprocess.run(
        ["/home/faisal/.local/bin/claude", "--version"],
        capture_output=True, text=True).stdout.strip()),
    ("parent_session_observed", os.path.basename(sorted(
        __import__("glob").glob("/home/faisal/.claude/projects/"
                                "-home-faisal-EventMarketDB/*.jsonl"),
        key=os.path.getmtime)[-1])[:-6]),
    ("attempt", 1), ("authorized_calls", 1),
    ("ledger_before", man["budget"]["before"]),
    ("ledger_at_most", man["budget"]["before"] + 1),
    ("retry_not_authorized", True), ("attempt2_is_accounting_only", True),
    ("invocations", [collections.OrderedDict([
        ("label", man["label"]), ("attempt", 1), ("scriptPath", script),
        ("script_sha256", man["script_sha256"]),
        ("script_bytes", man["script_bytes"]),
        ("prompt_sha256", man["prompt_sha256"])])]),
    ("launched", 0)])
with io.open(sys.argv[1], "x", encoding="utf-8") as fh:
    fh.write(json.dumps(rec, indent=1))
print(json.dumps({k: rec[k] for k in
                  ("label", "manifest_sha256", "prompt_sha256", "script_sha256",
                   "script_bytes", "ledger_before", "ledger_at_most",
                   "runtime_observed_before_launch")}
                 | {"record_sha256": fsha(sys.argv[1])}, indent=1))
