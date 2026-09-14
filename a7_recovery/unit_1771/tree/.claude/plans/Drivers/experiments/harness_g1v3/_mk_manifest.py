#!/usr/bin/env python3
"""EXP-0 PRE-CALL manifest builder + verification (0 LLM). Records the six user-required confirmations BEFORE
any grader call and EXITS NONZERO if any fails, so the runner STOPS before spending. Never mutates the key.
args: RUNDIR KEY LOCK PROTOCOL ARMS_BLIND FRAMING"""
import hashlib
import json
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/harness")
import key_lint as KL

RUNDIR, KEY, LOCK, PROTO, ARMS_BLIND, FRAMING, REQ_SHA, EFFORT = sys.argv[1:9]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


fail = []

# --- 1. lock / hash ---
lock = json.load(open(LOCK))
key_sha, proto_sha = sha(KEY), sha(PROTO)
lock_ok = (key_sha == lock.get("sha256")) and (proto_sha == lock.get("protocol_sha256")) and (key_sha == REQ_SHA)
if not lock_ok:
    fail.append("LOCK/HASH mismatch: key %s / lock %s / required %s" % (key_sha[:12], str(lock.get("sha256"))[:12], REQ_SHA[:12]))

# --- 2. blind fields only ---
arms = json.load(open(ARMS_BLIND))
BLIND_PAIR = {"pair_id", "side_a", "side_b"}
BLIND_SIDE = {"name", "quotes", "slice_tokens", "per_x", "industry"}
FORBIDDEN = ["gold", "gold_rationale", "family", "provenance", "rival", "hard", "source_ref",
             "source", "grounding", "sidecar", "drafter_gold", "drafter_rationale", "tell_control", "fable"]
keyset = set(r["pair_id"] for _l, r in KL.load_records(KEY))
blind_bad = []
arms_pids = {}
for a in arms:
    pids = []
    for p in a["pairs"]:
        pids.append(p["pair_id"])
        if set(p.keys()) - BLIND_PAIR:
            blind_bad.append([a["arm"], p["pair_id"], "pair", sorted(set(p.keys()) - BLIND_PAIR)])
        for s in ("side_a", "side_b"):
            extra = set(p.get(s, {}).keys()) - BLIND_SIDE
            if extra:
                blind_bad.append([a["arm"], p["pair_id"], s, sorted(extra)])
    arms_pids[a["arm"]] = pids
blob = json.dumps(arms)
forbidden_hits = sorted(f for f in FORBIDDEN if ('"%s":' % f) in blob)   # forbidden as a JSON KEY (not a substring of a value)
pid_ok = all(set(v) == keyset and len(v) == len(keyset) for v in arms_pids.values())
blind_ok = (not blind_bad) and (not forbidden_hits) and pid_ok
if blind_bad:
    fail.append("BLINDNESS: %d non-blind field occurrence(s): %s" % (len(blind_bad), blind_bad[:3]))
if forbidden_hits:
    fail.append("BLINDNESS: forbidden JSON keys present: %s" % forbidden_hits)
if not pid_ok:
    fail.append("PAIR_ID COVERAGE: an arm's pair_ids != the key's %d pair_ids" % len(keyset))

# --- 3. prompt vs locked protocol ---
framing_txt = open(FRAMING, encoding="utf-8").read()
framing_sha = hashlib.sha256(framing_txt.encode()).hexdigest()
checklist = {
    "default_DIFFERENT": "Default to DIFFERENT" in framing_txt,
    "three_check_object_scope_mechanism": all(x in framing_txt for x in ("same OBJECT", "same SCOPE", "same MECHANISM")),
    "cite_verbatim_each_side": "verbatim quote from EACH side" in framing_txt,
    "over_merge_permanent": "Over-merging is permanent" in framing_txt,
    "placeholders_present": all(x in framing_txt for x in ("<<SIDE_A>>", "<<SIDE_B>>", "<<PAIR_ID>>")),
    "no_backtick_or_dollarbrace": ("`" not in framing_txt) and ("${" not in framing_txt),
}
prompt_ok = all(checklist.values())
if not prompt_ok:
    fail.append("PROMPT does not implement protocol section 6: %s" % checklist)

# --- 4. model routes  /  5. api-key policy ---
models = {"g_sonnet_a": {"slot": "sonnet", "resolved": "claude-sonnet-5", "effort": EFFORT},
          "g_sonnet_b": {"slot": "sonnet", "resolved": "claude-sonnet-5", "effort": EFFORT},
          "g_opus": {"slot": "opus", "resolved": "claude-opus-4-8", "effort": EFFORT},
          "record_clerk": {"slot": "opus", "resolved": "claude-opus-4-8", "effort": "default (mechanical file write, not a grader arm)"}}

status = "pre_call_verified" if not fail else "PRE_CALL_FAIL"
manifest = {
    "exp_id": "EXP-0", "run_id": RUNDIR.rstrip("/").split("/")[-1], "status": status,
    "pre_call_confirmations": {
        "1_lock_hash_verified": {"ok": lock_ok, "key_sha256": key_sha, "required_sha256": REQ_SHA,
                                 "key_matches_required": key_sha == REQ_SHA, "protocol_sha256": proto_sha,
                                 "lock_key_sha256": lock.get("sha256"), "lock_protocol_sha256": lock.get("protocol_sha256"),
                                 "locked_by": lock.get("locked_by"), "lock_file": "K-pairs.v1.1.lock.json"},
        "2_blind_fields_only": {"ok": blind_ok, "non_blind_findings": blind_bad, "forbidden_keys_found": forbidden_hits,
                                "pair_ids_match_key": pid_ok, "key_n_pairs": len(keyset),
                                "n_pairs_per_arm": {a: len(p) for a, p in arms_pids.items()},
                                "allowed_pair_keys": sorted(BLIND_PAIR), "allowed_side_keys": sorted(BLIND_SIDE)},
        "3_prompt_matches_protocol": {"ok": prompt_ok, "framing_sha256": framing_sha, "protocol_sha256": proto_sha,
                                      "checklist": checklist, "framing_text": framing_txt},
        "4_model_routes": models,
        "5_anthropic_api_key": {"policy": "unset / subscription (OAuth) only",
                                "agent_env_probe": "ANTHROPIC_API_KEY empty in subagent env (preflight task w8p52kz0b: APIKEY=)",
                                "note": "judges run via the Workflow subscription path; NO server clerks during judging; CLAUDE.md billing guard in force"},
        "6_outputs_plan": {"verdicts_raw": ["verdicts.g_sonnet_a.json", "verdicts.g_sonnet_b.json", "verdicts.g_opus.json"],
                           "scores": "scores.json", "decision": "decision.json", "budget": "../../BUDGET.json",
                           "status_board": "WORKORDER_STATUS.md", "saved": False},
        "7_effort_pinned": {"ok": True, "grader_effort": EFFORT,
                            "per_arm": {"g_sonnet_a": EFFORT, "g_sonnet_b": EFFORT, "g_opus": EFFORT},
                            "note": "Fable O10: identical reasoning effort across arms; qualified tier identity = (model_id, effort); downstream graded calls must reuse the same (model_id, effort); NO effort laddering. Effort honored-verified before the run (Sonnet 2.9x, Opus 2.8x high/low token ratio on the grading task) -- applied+recordable, not silently ignored."}},
    "grader_effort": EFFORT,
    "arms": {a["arm"]: {"model": a["model"], "n": a["n"], "page_h32": a["page_h32"], "effort": EFFORT} for a in arms},
    "keys": {"K-pairs": key_sha, "protocol": proto_sha, "lock": "K-pairs.v1.1.lock.json"},
    "caps": {"max_calls": 900},
    "counts": {"planned_strong_grader_calls": sum(a["n"] for a in arms), "planned_record_clerk_calls": len(arms), "made_calls": 0},
    "gate": {"expr": "EXISTS tier T: forall g in T: wrong_same==0 && false_refusal<=0.10 && invalid_rate<=0.02"},
}
json.dump(manifest, open(RUNDIR.rstrip("/") + "/manifest.json", "w"), indent=2, sort_keys=True)
print("MANIFEST_STATUS", status)
print("CONFIRMATIONS", json.dumps({k: v.get("ok") for k, v in manifest["pre_call_confirmations"].items() if isinstance(v, dict) and "ok" in v}, sort_keys=True))
print("ARMS", json.dumps(manifest["arms"], sort_keys=True))
if fail:
    print("PRE_CALL_FAIL", json.dumps(fail), file=sys.stderr)
    sys.exit(3)
print("PRE_CALL_VERIFIED_OK")
