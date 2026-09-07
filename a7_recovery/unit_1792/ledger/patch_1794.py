# -*- coding: utf-8 -*-
"""ONE exact expected input per lane (Codex SEQ 1794 item 2).

Rebuilds both owners from the PUBLISHED unit_1781 baseline and applies the
correction, so the derivation is one deterministic step from reviewed bytes and
the defective SEQ 1792 attempt contributes nothing.

WHAT REPLACES WHAT
    out: a run-wide list of allowed payload hashes, tolerated wherever it
         appeared - which accepted a DELETED, a WRONG-TYPED and a MOVED
         attachment (Codex SEQ 1793).
    in : each lane's own expectation, frozen into the root row: either nothing
         at all, or exactly ONE input at a declared record index, of a declared
         outer record type, whose payload field canonicalises to a declared
         sha256. Presence and position are required, every other extra record
         still refuses, the record chain is untouched, and no payload, url,
         type name or keyword appears in any owner.
"""
import hashlib
import io
import os
import shutil
import sys

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = ("/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_1781/"
        "view/harness_g1v3")
VIEW = U + "/view/harness_g1v3"
A, G = VIEW + "/audit_worker_access.py", VIEW + "/a7_g1_build.py"

MATCHER = '''

def _expected_input(rec, i, spec):
    """-> True only when record `i` is EXACTLY the ONE input this lane declares.

    `spec` is that lane's own expectation, frozen in the approved root and
    handed down by the caller: the record index the input must sit at, the
    outer record type it must carry, the field its payload sits in, and that
    payload's canonical sha256. THE ONE MATCH RULE, shared by both input
    owners.

    Nothing is read from the transcript to decide what is allowed; no payload,
    url, type name or keyword is written here; and an absent or malformed
    expectation admits nothing at all.
    """
    if not isinstance(spec, dict):
        return False
    index, kind = spec.get("record_index"), spec.get("record_type")
    field, want = spec.get("payload_field"), spec.get("payload_sha256")
    if isinstance(index, bool) or not isinstance(index, int) or index < 1:
        return False                       # record 0 is the supplied prompt
    if not isinstance(kind, str) or not kind:
        return False
    if not isinstance(field, str) or not field:
        return False
    if not isinstance(want, str) or len(want) != 64:
        return False
    if i != index or not isinstance(rec, dict):
        return False
    if rec.get("type") != kind or rec.get("message") is not None:
        return False
    try:
        canon = json.dumps(rec.get(field), sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return False
    return hashlib.sha256(canon.encode("utf-8")).hexdigest() == want

'''

EDITS = [
    # ---- the shape owner ----------------------------------------------------
    (A, '''def _g1_shape_problems(recs, agent_id):''',
        '''def _g1_shape_problems(recs, agent_id, expected_input=None):'''),
    (A, '''        message = rec.get("message")
        if not isinstance(message, dict):
            bad.append("agent %s's record %d carries a %s message, not an "
                       "object" % (agent_id, i, type(message).__name__))''',
        '''        message = rec.get("message")
        if not isinstance(message, dict):
            # THE ONE INPUT THIS LANE DECLARES, at the declared index and only
            # there. Every other message-less record is the problem it was.
            if not _expected_input(rec, i, expected_input):
                bad.append("agent %s's record %d carries a %s message, not an "
                           "object" % (agent_id, i, type(message).__name__))'''),
    # ---- the input-topology owner -------------------------------------------
    (A, '''def _input(recs, pin):''', '''def _input(recs, pin, expected_input=None):'''),
    (A, '''    for i, r in enumerate(recs[1:], 1):
        if r.get("type") != "assistant" or _role(r) != "assistant":
            bad.append(_LaterInput(''',
        '''    seen = False
    for i, r in enumerate(recs[1:], 1):
        if _expected_input(r, i, expected_input):
            seen = True
            continue
        if r.get("type") != "assistant" or _role(r) != "assistant":
            bad.append(_LaterInput('''),
    (A, '''    content = (first.get("message") or {}).get("content")
    if not isinstance(content, str):''',
        '''    if expected_input is not None and not seen:
        # PRESENCE AND POSITION ARE REQUIRED, not merely permitted. A plain
        # problem, never a _LaterInput: a missing declared input is not the
        # runtime adding something, so it may not be held as uncreditable.
        bad.append("the one input this lane declares is not at record %r"
                   % (expected_input.get("record_index")
                      if isinstance(expected_input, dict) else expected_input,))
    content = (first.get("message") or {}).get("content")
    if not isinstance(content, str):'''),
    # ---- the transcript owner threads ONE lane's expectation ----------------
    (A, '''def _g1_transcript(session_dir, session_id, rid, agent_id, prompt_sha, model,
                   effort, response_ids):''',
        '''def _g1_transcript(session_dir, session_id, rid, agent_id, prompt_sha, model,
                   effort, response_ids, expected_input=None):'''),
    (A, '''    shape = _g1_shape_problems(recs, agent_id)''',
        '''    shape = _g1_shape_problems(recs, agent_id, expected_input)'''),
    (A, '''    problems = list(_input(recs, prompt_sha) or [])''',
        '''    problems = list(_input(recs, prompt_sha, expected_input) or [])'''),
    (A, '''        why, final, _complete = _g1_transcript(
            session_dir, session_id, rid, agent_id, row["prompt_sha256"],
            expect["runtime_model_id"], expect["effort"], response_ids)''',
        '''        why, final, _complete = _g1_transcript(
            session_dir, session_id, rid, agent_id, row["prompt_sha256"],
            expect["runtime_model_id"], expect["effort"], response_ids,
            row.get("expected_input"))'''),
    # ---- the root declares it per row, the caller carries it down -----------
    (G, '''def freeze_root(out_dir, run_dir, expect_sha):''',
        '''def freeze_root(out_dir, run_dir, expect_sha, lane_inputs=None):'''),
    (G, '''        ("rows", [collections.OrderedDict([
            ("ordinal", n), ("batch_id", r["batch_id"]),
            ("lane_id", r["lane_id"]),
            ("prompt_sha256", r["prompt_sha256"])])
            for n, r in enumerate(doc["launchers"]["rows"])])])''',
        '''        # EACH LANE'S OWN EXPECTED RUNTIME INPUT, supplied by the caller
        # from reviewed evidence: None means this lane may carry no added
        # input at all, which is also what a lane the caller does not name
        # gets - the closed default every earlier segment was proved under.
        ("rows", [collections.OrderedDict([
            ("ordinal", n), ("batch_id", r["batch_id"]),
            ("lane_id", r["lane_id"]),
            ("prompt_sha256", r["prompt_sha256"]),
            ("expected_input", (lane_inputs or {}).get(r["lane_id"]))])
            for n, r in enumerate(doc["launchers"]["rows"])])])'''),
    (G, '''        ("rows", [collections.OrderedDict([
            ("lane_id", r["lane_id"]), ("ordinal", r["ordinal"]),
            ("prompt", prompts[r["lane_id"]]),
            ("prompt_sha256", r["prompt_sha256"])]) for r in receipt["rows"]]),''',
        '''        # THE EXPECTATION COMES FROM THE APPROVED ROOT, never from the
        # state or transcript being judged.
        ("rows", [collections.OrderedDict([
            ("lane_id", r["lane_id"]), ("ordinal", r["ordinal"]),
            ("prompt", prompts[r["lane_id"]]),
            ("prompt_sha256", r["prompt_sha256"]),
            ("expected_input",
             declared_inputs.get(r["lane_id"]))]) for r in receipt["rows"]]),'''),
    (G, '''    prompts = {r["lane_id"]: r["prompt"] for r in derived}''',
        '''    prompts = {r["lane_id"]: r["prompt"] for r in derived}
    declared_inputs = {r["lane_id"]: r.get("expected_input")
                       for r in root["rows"]}'''),
]


def sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def main():
    for path in (A, G):
        shutil.copyfile(os.path.join(BASE, os.path.basename(path)), path)
    for path, old, new in EDITS:
        text = io.open(path, encoding="utf-8").read()
        if text.count(old) != 1:
            print("REFUSED: a target matches %d times in %s"
                  % (text.count(old), os.path.basename(path)))
            return 1
        io.open(path, "w", encoding="utf-8").write(text.replace(old, new, 1))
    text = io.open(A, encoding="utf-8").read()
    anchor = "\n\ndef _pairs(asst):"
    if text.count(anchor) != 1:
        print("REFUSED: cannot place the match rule deterministically")
        return 1
    io.open(A, "w", encoding="utf-8").write(
        text.replace(anchor, MATCHER + "\ndef _pairs(asst):", 1))
    for path in (A, G):
        print("  %-24s %s  %d bytes"
              % (os.path.basename(path), sha(path), os.path.getsize(path)))
    print("  %d edits plus one shared match rule, from the unit_1781 baseline"
          % len(EDITS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
