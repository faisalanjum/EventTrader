"""Harvest and prove the ONE authorized final-key signer call.

Everything about whether a call IS what it claims now belongs to
signer_proof.prove, which the compact owner asks as well. What is left here is
what only a harvest can do: wait for the runtime to finish, decide from the
packet's own law whether this attempt was earned, and write - once - the raw,
the evidence, or the record of an invocation that earned no credit.

A child is authorized by its parent's PROVED outcome, never by the string its
parent's record happens to carry, and the parent is proved with the SAME shared
response-identity dictionary, so a child that reuses its parent's response is
refused here rather than being written down.

Usage: harvest_final_sign.py <run_id> <attempt>
"""
import io, json, os, sys, time

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
SESSION = "5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
SESS = (os.environ.get("A7_SIGNER_SESSION")
        or "/home/faisal/.claude/projects/-home-faisal-EventMarketDB/" + SESSION)
SIG = (os.environ.get("A7_CANDIDATE_DIR")
       or S + "/lock/final_key_candidate_1511") + "/signer"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_final as F                                  # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import raw_transport as RT                                       # noqa: E402
import signer_proof as SP                                        # noqa: E402

run_id, attempt = sys.argv[1], int(sys.argv[2])
MAN = json.load(io.open(SIG + "/signer.manifest.json", encoding="utf-8"))
LAWFUL = [s["attempt"] for s in MAN.get("scripts") or [{"attempt": 1}]]
EARNS_A_CHILD = tuple((MAN.get("retry_law") or {}).get("retryable") or ())
#: ONE dictionary for this harvest: the parent and the child are proved against
#: each other, which is what makes a reused response identity visible.
SEEN = {}

# A call the packet never rendered has no slot to record: there is nothing of
# this attempt to preserve, and inventing one would create the call.
if attempt not in LAWFUL:
    print("STOP: attempt %d is outside the packet's lawful range %r"
          % (attempt, LAWFUL))
    raise SystemExit(2)
PROMPT, SCRIPT, PACKET_BAD = SP.packet(SIG, MAN, attempt)
if PACKET_BAD:
    print("STOP: %s" % PACKET_BAD)
    raise SystemExit(2)


def record(outcome, problems, run=None):
    """The invocation happened. Write it once, then stop with no credit."""
    RT.write_new(SIG + "/final_sign.attempt%d.invocation.json" % attempt,
                 json.dumps({"attempt": attempt, "run_id": run_id,
                             "outcome": outcome, "problems": list(problems),
                             "state_path": run,
                             "prompt_sha256": SP.sha(PROMPT),
                             "script_sha256": SP.sha(SCRIPT)}, indent=1))
    print("STOP: %s" % problems)
    raise SystemExit(2)


def write_once(path, text, run=None):
    """Write it, or prove what is already there IS it. The same law the paid
    answer follows, so an interrupted run finishes instead of refusing."""
    stored = K._stored_matches(path, text)
    if stored is None:
        RT.write_new(path, text)
    elif stored is False:
        record("unproved", ["%s already holds different bytes"
                            % os.path.basename(path)], run)


def slot(n):
    for kind in ("evidence", "invocation"):
        p = SIG + "/final_sign.attempt%d.%s.json" % (n, kind)
        if os.path.isfile(p):
            return kind, p, json.load(io.open(p, encoding="utf-8"))
    return None, None, None


# ---- was this call earned? the PARENT'S OWN PROOF answers, not its record
if attempt > 1:
    kind, path, parent = slot(attempt - 1)
    if parent is None:
        record("unauthorized", ["attempt %d has no parent call" % attempt])
    if kind != "evidence":
        # a call that never earned evidence cannot be anyone's parent, whatever
        # outcome its own record names
        record("unauthorized", ["attempt %d's parent earned no proved evidence"
                                % attempt])
    proved, why = SP.prove(SIG, MAN, attempt - 1, parent["run_id"], SESS, SEEN)
    if why:
        record("unauthorized", ["attempt %d's parent no longer proves: %s"
                                % (attempt, why[0])])
    wrong = SP.disagreements(parent, proved)
    if wrong:
        record("unauthorized", ["attempt %d's parent record disagrees with "
                                "its own proof: %s" % (attempt, wrong[0])])
    outcome = proved["outcome"]
    if outcome not in EARNS_A_CHILD:
        record("unauthorized", ["attempt %d's parent returned %r, which earns "
                                "no further call" % (attempt, outcome)])

# ---- the ONLY waiting in this owner, and it is outside the proof
state = SP.state_of(SESS, run_id)
TERMINAL = SP.TERMINAL   # ONE owner for this rule; see signer_proof
for _ in range(360):
    if os.path.isfile(state):
        try:
            d = json.load(io.open(state, encoding="utf-8"))
        except Exception:                             # noqa: BLE001 - by design
            break        # bytes that cannot be read will not become terminal
        # a state that is not an object has no status to reach, and asking it
        # for one is how a named refusal became a traceback
        if not isinstance(d, dict) or d.get("status") in TERMINAL:
            break
    time.sleep(10)
else:
    record("waiting", ["%s never reached a terminal state" % run_id])

proof, problems = SP.prove(SIG, MAN, attempt, run_id, SESS, SEEN)
if problems:
    record("unproved", problems, state)

complete = proof.pop("_text")
obj = proof.pop("_reply")
# THE PAID BYTES, ONCE. A run interrupted after capturing them resumes on the
# same bytes and pays nothing; different bytes are an integrity conflict, not a
# licence to overwrite.
raw_path = os.path.join(SIG, RT._raw_filename("final_sign.attempt%d" % attempt))
stored = K._stored_matches(raw_path, complete)
if stored is None:
    RT.save_raw(complete, SIG, "final_sign.attempt%d" % attempt)
elif stored is False:
    record("unproved", ["the stored raw answer is not the official returned "
                        "text"], state)
assert io.open(raw_path, encoding="utf-8").read() == complete
print("  raw %s sha %s (%d chars)"
      % (os.path.basename(raw_path), proof["raw_sha256"], proof["raw_chars"]))
print("  run %s | agent %s | model %s | effort %s | %s | tools %s | runtime %s"
      % (run_id, proof["agent_id"], proof["model"], proof["effort"],
         proof["agent_type"], proof["tool_calls"], proof["runtime_model_ids"]))

proof["raw_path"] = raw_path
proof["retry_law"] = {"owner": "build_kfields_final.RETRYABLE",
                      "retryable": list(F.RETRYABLE)}
write_once(SIG + "/final_sign.attempt%d.evidence.json" % attempt,
           json.dumps(proof, indent=1), state)
if proof["outcome"] == "invalid_response":
    print("  OUTCOME: invalid_response (%s) -> the one identical-bytes retry is "
          "permitted" % proof["parser_problems"][0])
    raise SystemExit(3)
write_once(SIG + "/final_sign.attempt%d.reply.json" % attempt,
           json.dumps(obj, indent=1), state)
print("  OUTCOME: signed=%r blocked=%r" % (obj["signed"], obj["blocked"]))
print("  why: %s" % obj["why"][:300])
raise SystemExit(0 if (obj["signed"] is True and obj["blocked"] == []) else 4)
