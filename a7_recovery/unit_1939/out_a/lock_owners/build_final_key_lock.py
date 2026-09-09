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
OUT = os.environ.get("A7_CANDIDATE_DIR") or S + "/lock/final_key_candidate_1511"
SIG = OUT + "/signer"; MAILBOX = "/home/faisal/.core827-orchestrator"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H); sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_key as K
import raw_transport as RT
import signer_proof as SP
sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()
shaf = lambda p: sha(io.open(p, "rb").read())
J = lambda p: json.load(io.open(p, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
LOCK = OUT + "/a4_final_key_lock.json"; RECEIPT = OUT + "/a4_final_key_lock_receipt.json"
AUTHORITY = os.environ.get("A7_AUTHORITY") or (MAILBOX + "/archive_CODEX_1512.md")


def _session():
    """The session whose workflows dir holds these calls' official states."""
    env = os.environ.get("A7_SIGNER_SESSION")
    if env:
        return env
    for n in [s["attempt"] for s in (J(MANIFEST).get("scripts") or [])] if os.path.isfile(MANIFEST) else []:
        p = SIG + "/final_sign.attempt%d.evidence.json" % n
        if os.path.isfile(p):
            return os.path.dirname(os.path.dirname(J(p)["state_path"]))
    return ""


MANIFEST = SIG + "/signer.manifest.json"
_MAN = J(MANIFEST) if os.path.isfile(MANIFEST) else {}
#: The lawful attempt numbers are the packet's own, not whatever files exist.
RANGE = [s["attempt"] for s in _MAN.get("scripts") or [{"attempt": 1}]]
#: The ONLY outcome that lets a call have a successor, taken from the packet.
RETRYABLE = tuple((_MAN.get("retry_law") or {}).get("retryable") or ())


def _slot(n):
    """What attempt n left behind: its proved evidence, or the invocation the
    harvest owner refused before any credit. Never both."""
    ev = SIG + "/final_sign.attempt%d.evidence.json" % n
    inv = SIG + "/final_sign.attempt%d.invocation.json" % n
    if os.path.isfile(ev):
        return "evidence", ev
    if os.path.isfile(inv):
        return "invocation", inv
    return None, None


def _chain():
    """Every attempt of this packet that actually ran, in order."""
    return [n for n in RANGE if _slot(n)[0]]


def _members(n):
    """The files attempt n is bound by. A refused invocation has only its own
    record; a proved one also has the bytes that record was derived from."""
    kind, rec = _slot(n)
    out = collections.OrderedDict([("record", rec),
                                   ("launcher", SIG + "/final_sign.attempt%d.js" % n)])
    if kind == "evidence":
        d = J(rec)
        out["raw"] = d["raw_path"]
        out["state"] = d["state_path"]
        out["transcript"] = d["transcript_path"]
    return out

def _signer_calls():
    return len(_chain()) or 1


ACCEPTED = max([n for n in RANGE
                if os.path.isfile(SIG + "/final_sign.attempt%d.reply.json" % n)]
               or [max(_chain() or [1])])
SESS = _session()
BOUND = collections.OrderedDict(
    [("key_identity", OUT + "/key_identity.json"), ("sidecar", OUT + "/sidecar.json"), ("validator_receipt", OUT + "/validator_receipt.json"),
     ("provenance", OUT + "/provenance.json"), ("signer_prompt", SIG + "/signer_prompt.txt"), ("signer_launcher", SIG + "/final_sign.attempt%d.js" % ACCEPTED),
     ("signer_manifest", MANIFEST), ("signer_raw", SIG + "/final_sign.attempt%d.raw.json" % ACCEPTED),
     ("signer_evidence", SIG + "/final_sign.attempt%d.evidence.json" % ACCEPTED),
     ("signer_reply", SIG + "/final_sign.attempt%d.reply.json" % ACCEPTED)]
    # every attempt that ran is bound: its own record, and for a proved one the
    # launcher it ran, the raw it returned, its official state and transcript
    + [("attempt%d_%s" % (n, name), path)
       for n in _chain() for name, path in _members(n).items()])



def build():
    # A run with no accepted signature still has to be DESCRIBED, so verify()
    # can say the lock carries none instead of the reader raising.
    _get = lambda k: J(BOUND[k]) if os.path.isfile(BOUND[k]) else {}
    ev, reply = _get("signer_evidence"), _get("signer_reply")
    ident, val, man = J(BOUND["key_identity"]), J(BOUND["validator_receipt"]), J(BOUND["signer_manifest"])
    return collections.OrderedDict([
        ("schema", "a4-final-key-lock/1511"), ("state", "LOCKED"),
        ("authority", collections.OrderedDict([("instruction", os.path.basename(AUTHORITY)), ("instruction_sha256", shaf(AUTHORITY))])),
        # a bound file that is GONE is a problem for verify() to name, not an
        # exception here: the lock must be able to say what is missing.
        ("artifacts", collections.OrderedDict(
            (k, shaf(p) if os.path.isfile(p) else None) for k, p in BOUND.items())),
        ("key", collections.OrderedDict([("identity", "key_identity.json: the ordered exact raw component shards, the four bindings and the pinned loader"),
                                         ("loader", ident["loader"]), ("materializer", ident["materializer"]), ("bindings", collections.OrderedDict((d, v["sha256"]) for d, v in ident["bindings"].items())),
                                         ("events", len(ident["key_shards"])), ("composed_events", sum(1 for s in ident["key_shards"] if s["composed"]))])),
        ("counts", val["full_counts"]), ("validator", collections.OrderedDict([("problems", val["problems"]), ("open_issues", val["counts"]["open_issues"]), ("tags_below_floor", val["counts"]["tags_below_floor"]),
                                                                                ("rows_accounted", val["counts"]["rows_accounted"]), ("class_floor", val["class_floor"])])),
        ("signer", collections.OrderedDict([("signed", reply.get("signed")), ("blocked", reply.get("blocked")), ("run_id", ev.get("run_id")), ("agent_id", ev.get("agent_id")), ("attempt", ev.get("attempt")),
                                            ("state_sha256", ev.get("state_sha256")), ("transcript_sha256", ev.get("transcript_sha256")), ("raw_sha256", ev.get("raw_sha256")),
                                            ("prompt_sha256", ev.get("prompt_sha256")), ("script_sha256", ev.get("script_sha256")), ("parent_session_id", ev.get("parent_session_id")),
                                            ("model", ev.get("model")), ("effort", ev.get("effort")), ("agent_type", ev.get("agent_type")), ("runtime_model_ids", ev.get("runtime_model_ids")),
                                            ("transport", man["transport"]), ("tool_calls", ev.get("tool_calls")), ("parser", ev.get("parser"))])),
        ("call_accounting", collections.OrderedDict([("ledger_before", man["budget"]["before"]), ("signer_calls", _signer_calls()), ("retries", _signer_calls() - 1),
                                                     ("ledger_after", man["budget"]["before"] + _signer_calls()),
                                                     ("ceiling", man["budget"]["ceiling"]), ("retry_law", man["retry_law"]),
                                                     ("lawful_attempts", list(RANGE)),
                                                     ("attempts", [collections.OrderedDict([("attempt", n), ("kind", _slot(n)[0]), ("outcome", J(_slot(n)[1])["outcome"]),
                                                                                            ("record_sha256", shaf(_slot(n)[1]))]) for n in _chain()])]))])


_CANDIDATE_ANSWER = []                  # one derivation per process; see below


def _candidate_problems():
    """Is this still the candidate the signer approved? -> the names that moved.

    ASKED OF THE CANDIDATE'S OWN OWNER. build_final_key_candidate.verify()
    already re-derives every candidate byte from the live owners and names
    whatever differs; writing that question a second time here would be a
    second identity rule for the same fact.

    WHY IT WAS MISSING AND WHY IT COULD NOT BE SEEN. build() reads the
    candidate as it CURRENTLY is and records those CURRENT hashes in the lock;
    verify() then compares the lock to those same current bytes. The two
    therefore always agreed, so at FIRST publication a candidate edited after
    signing produced a perfectly self-consistent lock and published it. An
    ALREADY published lock does catch that drift, because its stored hashes
    predate the change - which is exactly why a check written after
    publication cannot find this hole (Codex SEQ 1927 item 2).

    Cached because main() calls verify() once per bound value to prove every
    mutation refuses, and re-deriving the whole key that many times would turn
    a proof into a timeout. The candidate does not change inside one process.
    """
    if not _CANDIDATE_ANSWER:
        here = os.path.dirname(os.path.abspath(__file__))
        here in sys.path or sys.path.insert(0, here)
        import build_final_key_candidate as C
        try:
            answer = tuple(C.verify(OUT))
        except BaseException as exc:                  # noqa: BLE001 - by design
            # A LOCK REFUSES; IT DOES NOT EXPLODE. The re-derivation needs the
            # same ordinary binding the candidate was built from, and without
            # it the candidate owner reads a different settlement entirely and
            # raises deep inside the hard review. Naming that is not swallowing
            # it: the exception type and message are carried out, publication
            # is refused, and the reader is told which input is missing.
            answer = ("the candidate cannot be re-derived (%s: %s); the "
                      "ordinary binding it was built from must be served as "
                      "A7_ORDINARY_BOUND"
                      % (type(exc).__name__, str(exc)[:120]),)
        _CANDIDATE_ANSWER.append(answer)
    return _CANDIDATE_ANSWER[0]


def verify(lock):
    """Re-derive every bound value from the live bytes, and confirm those bytes
    are still the candidate the signer approved."""
    bad = ["the candidate no longer re-derives: %s" % n
           for n in _candidate_problems()]
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
    man = J(BOUND["signer_manifest"])
    chain = _chain()
    # THE SEQUENCE ITSELF: the calls of this packet run 1, 2, ... with no gap,
    # the accepted one is the last, and a call only has a successor if its own
    # outcome is the one the packet's retry law names.
    if chain != RANGE[:len(chain)]: bad.append("the attempt chain has a gap: %r of %r" % (chain, RANGE))
    if chain and chain[-1] != ACCEPTED: bad.append("the accepted attempt %d is not the last call" % ACCEPTED)
    # ONE shared response-identity dictionary for the whole chain: a response
    # identity reused between two attempts is the transcript owner's refusal,
    # not a rule this file re-states.
    seen = {}
    accepted_outcome, accepted_reply = None, None
    for n in chain:
        kind, rec = _slot(n)
        d = J(rec)
        if kind == "evidence":
            proved, why = SP.prove(SIG, man, n, d.get("run_id"), SESS, seen)
            bad += ["attempt %d does not prove: %s" % (n, w) for w in why]
            bad += ["attempt %d: %s" % (n, w) for w in SP.disagreements(d, proved)]
            outcome = None if why else proved.get("outcome")
            raw = _members(n).get("raw")
            if not (raw and os.path.isfile(raw) and shaf(raw) == proved.get("raw_sha256")):
                bad.append("attempt %d's saved raw is not the proved answer" % n)
            # THE SAVED REPLY IS NOT A SECOND OPINION: it must be the object the
            # parser produced from the proved answer, or it is not this call's.
            saved = SIG + "/final_sign.attempt%d.reply.json" % n
            if os.path.isfile(saved):
                if proved.get("_reply") is None:
                    bad.append("attempt %d saved a parsed reply for an answer that did not prove" % n)
                elif J(saved) != proved["_reply"]:
                    bad.append("attempt %d's saved reply is not the one its answer parses to" % n)
            elif outcome == "signed":
                bad.append("attempt %d proved a signature but saved no reply" % n)
            if n == ACCEPTED:
                accepted_outcome, accepted_reply = outcome, proved.get("_reply")
        else:
            # AN INVOCATION HAS NO PROVED EVIDENCE. Whatever outcome it names,
            # it cannot be the parent that earns another call.
            outcome = None
            if d.get("prompt_sha256") != man["prompt_sha256"]:
                bad.append("attempt %d was not asked the frozen question" % n)
            if n != chain[-1]:
                bad.append("attempt %d earned no evidence, so it cannot have a successor" % n)
        # ITS LEGAL POSITION: only the outcome the packet's retry law names may
        # have a successor, and the accepted call may not be one that owed one.
        if n != chain[-1] and outcome not in RETRYABLE: bad.append("attempt %d returned %r, which earns no further call" % (n, outcome))
        if n == chain[-1] and outcome in RETRYABLE: bad.append("attempt %d earned a retry that was never made" % n)
    # THE ACCEPTED DECISION IS THE PROVED ONE, never the saved file's claim
    if accepted_outcome != "signed" or not isinstance(accepted_reply, dict) \
            or accepted_reply.get("signed") is not True \
            or accepted_reply.get("blocked") != []:
        bad.append("the accepted call does not PROVE a clean signature: %r"
                   % (accepted_outcome,))
    if [a["attempt"] for a in live["call_accounting"]["attempts"]] != chain: bad.append("an attempt was added or removed")
    return bad


def publish(path, text):
    """Write it once, or prove the published bytes ARE these. -> bool"""
    stored = K._stored_matches(path, text)
    if stored is None:
        RT.write_new(path, text)
        return True
    return stored is True


def main():
    lock = build()
    problems = verify(lock)
    if problems:
        print("REFUSED: %s" % problems[:3]); raise SystemExit(1)
    if not publish(LOCK, json.dumps(lock, indent=1)):
        print("REFUSED: %s already holds a different lock" % LOCK)
        raise SystemExit(1)
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
    if not publish(RECEIPT, json.dumps(receipt, indent=1)):
        print("REFUSED: %s already holds a different receipt" % RECEIPT)
        raise SystemExit(1)
    print("a4_final_key_lock_receipt.json %s" % shaf(RECEIPT)); print("RESULT " + ("EVERY BOUND VALUE REFUSES WHEN MUTATED" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
