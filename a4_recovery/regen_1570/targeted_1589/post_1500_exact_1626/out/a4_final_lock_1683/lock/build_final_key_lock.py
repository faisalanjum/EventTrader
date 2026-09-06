"""Write the ONE compact signed A4 final-key lock, then prove it (Codex SEQ 1512 item 4).

The pre-A2 lock owner's shape (build_lock.py), applied to the final-key candidate:
the lock binds only identities that already exist - the seven frozen candidate
artifacts, the signer's raw, evidence and reply, the official call identities and
configuration, the counts the validator measured and the call accounting. It adds
no semantic decision and no framework: `verify()` re-derives every bound value from
the live bytes, so mutating any one of them refuses. Written once.
"""
import collections, hashlib, io, json, os, sys
S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
OUT = S + "/lock/final_key_candidate_1511"; SIG = OUT + "/signer"; MAILBOX = "/home/faisal/.core827-orchestrator"
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import raw_transport as RT
sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()
shaf = lambda p: sha(io.open(p, "rb").read())
J = lambda p: json.load(io.open(p, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
LOCK = OUT + "/a4_final_key_lock.json"; RECEIPT = OUT + "/a4_final_key_lock_receipt.json"
BOUND = collections.OrderedDict([
    ("key_identity", OUT + "/key_identity.json"), ("sidecar", OUT + "/sidecar.json"), ("validator_receipt", OUT + "/validator_receipt.json"),
    ("provenance", OUT + "/provenance.json"), ("signer_prompt", SIG + "/signer_prompt.txt"), ("signer_launcher", SIG + "/final_sign.attempt1.js"),
    ("signer_manifest", SIG + "/signer.manifest.json"), ("signer_raw", SIG + "/final_sign.attempt1.raw.json"),
    ("signer_evidence", SIG + "/final_sign.attempt1.evidence.json"), ("signer_reply", SIG + "/final_sign.attempt1.reply.json")])


def build():
    ev, reply, ident, val, man = J(BOUND["signer_evidence"]), J(BOUND["signer_reply"]), J(BOUND["key_identity"]), J(BOUND["validator_receipt"]), J(BOUND["signer_manifest"])
    return collections.OrderedDict([
        ("schema", "a4-final-key-lock/1511"), ("state", "LOCKED"),
        ("authority", collections.OrderedDict([("instruction", "Codex SEQ 1512"), ("instruction_sha256", shaf(MAILBOX + "/archive_CODEX_1512.md"))])),
        ("artifacts", collections.OrderedDict((k, shaf(p)) for k, p in BOUND.items())),
        ("key", collections.OrderedDict([("identity", "key_identity.json: the ordered exact raw component shards, the four bindings and the pinned loader"),
                                         ("loader", ident["loader"]), ("materializer", ident["materializer"]), ("bindings", collections.OrderedDict((d, v["sha256"]) for d, v in ident["bindings"].items())),
                                         ("events", len(ident["key_shards"])), ("composed_events", sum(1 for s in ident["key_shards"] if s["composed"]))])),
        ("counts", val["full_counts"]), ("validator", collections.OrderedDict([("problems", val["problems"]), ("open_issues", val["counts"]["open_issues"]), ("tags_below_floor", val["counts"]["tags_below_floor"]),
                                                                                ("rows_accounted", val["counts"]["rows_accounted"]), ("class_floor", val["class_floor"])])),
        ("signer", collections.OrderedDict([("signed", reply["signed"]), ("blocked", reply["blocked"]), ("run_id", ev["run_id"]), ("agent_id", ev["agent_id"]), ("attempt", ev["attempt"]),
                                            ("state_sha256", ev["state_sha256"]), ("transcript_sha256", ev["transcript_sha256"]), ("raw_sha256", ev["raw_sha256"]),
                                            ("prompt_sha256", ev["prompt_sha256"]), ("script_sha256", ev["script_sha256"]), ("parent_session_id", ev["parent_session_id"]),
                                            ("model", ev["model"]), ("effort", ev["effort"]), ("agent_type", ev["agent_type"]), ("runtime_model_ids", ev["runtime_model_ids"]),
                                            ("transport", "subscription"), ("max_output_tokens", "128000"), ("tool_calls", ev["tool_calls"]), ("parser", ev["parser"])])),
        ("call_accounting", collections.OrderedDict([("ledger_before", man["budget"]["before"]), ("signer_calls", 1), ("retries", 0), ("ledger_after", man["budget"]["before"] + 1),
                                                     ("ceiling", man["budget"]["ceiling"]), ("retry_law", man["retry_law"])]))])


def verify(lock):
    """Re-derive every bound value from the live bytes."""
    bad = []
    live = build()
    for k, p in BOUND.items():
        if not os.path.isfile(p): bad.append("bound artifact missing: %s" % k)
        elif lock["artifacts"].get(k) != shaf(p): bad.append("bound artifact changed: %s" % k)
    for k in ("key", "counts", "validator", "call_accounting", "authority", "schema"):
        if lock.get(k) != live[k]: bad.append("%s does not re-derive" % k)
    for k, v in live["signer"].items():
        if lock["signer"].get(k) != v: bad.append("signer %s does not re-derive" % k)
    if lock["signer"]["signed"] is not True or lock["signer"]["blocked"] != []: bad.append("the lock does not carry a clean signature")
    if lock["validator"]["problems"] or lock["validator"]["open_issues"] or lock["validator"]["tags_below_floor"]: bad.append("the validator is not clean")
    ev = J(BOUND["signer_evidence"]); man = J(BOUND["signer_manifest"])
    if ev["prompt_sha256"] != man["prompt_sha256"] or ev["script_sha256"] != man["script_sha256"]: bad.append("the signer did not run the frozen packet")
    if ev["raw_sha256"] != shaf(BOUND["signer_raw"]): bad.append("the signer raw is not the evidence's")
    return bad


def main():
    lock = build()
    problems = verify(lock)
    if problems:
        print("REFUSED: %s" % problems[:3]); raise SystemExit(1)
    RT.write_new(LOCK, json.dumps(lock, indent=1))
    again = build()
    if json.dumps(again, indent=1) != json.dumps(lock, indent=1):
        print("REFUSED: the lock does not re-derive identically"); raise SystemExit(1)
    print("a4_final_key_lock.json %s" % shaf(LOCK))
    print("  signed=%r blocked=%r  ledger %d -> %d of %d" % (lock["signer"]["signed"], lock["signer"]["blocked"], lock["call_accounting"]["ledger_before"], lock["call_accounting"]["ledger_after"], lock["call_accounting"]["ceiling"]))
    results, ok = collections.OrderedDict(), True
    for k in list(lock["artifacts"]):
        m = json.loads(json.dumps(lock)); m["artifacts"][k] = "0" * 64; caught = bool(verify(m)); ok = ok and caught; results["artifact:" + k] = "refused" if caught else "NOT REFUSED"
    for k in ("run_id", "agent_id", "raw_sha256", "transcript_sha256", "state_sha256", "parent_session_id", "model", "effort", "agent_type", "prompt_sha256", "script_sha256", "signed", "blocked"):
        m = json.loads(json.dumps(lock)); m["signer"][k] = False if k == "signed" else (["tampered"] if k == "blocked" else "0" * 8); caught = bool(verify(m)); ok = ok and caught; results["signer:" + k] = "refused" if caught else "NOT REFUSED"
    for k in ("counts", "validator", "call_accounting", "key", "authority"):
        m = json.loads(json.dumps(lock)); first = list(m[k])[0]; m[k][first] = -1; caught = bool(verify(m)); ok = ok and caught; results["block:" + k] = "refused" if caught else "NOT REFUSED"
    for name, r in results.items(): print("  %-34s %s" % (name, r))
    receipt = collections.OrderedDict([("schema", "a4-final-key-lock-receipt/1511"), ("lock_path", LOCK), ("lock_sha256", shaf(LOCK)), ("re_derives_identically", True),
                                       ("mutations", results), ("every_bound_value_refuses_when_mutated", ok), ("verify_problems_on_the_live_bytes", verify(J(LOCK)))])
    RT.write_new(RECEIPT, json.dumps(receipt, indent=1))
    print("a4_final_key_lock_receipt.json %s" % shaf(RECEIPT)); print("RESULT " + ("EVERY BOUND VALUE REFUSES WHEN MUTATED" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
