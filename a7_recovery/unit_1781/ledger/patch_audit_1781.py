# -*- coding: utf-8 -*-
"""The SMALLEST correction that lets the existing G1 audit accept a native
cached resumption, and the same frozen script at its durable location.

Codex SEQ 1781. Two edits, both inside g1_state_audit, both in this unit's
PRIVATE view. Nothing else changes: the cached-shape helper, the transcript
engine, the A1 audit and every other check are untouched.

  1 a row that CLAIMS to be cached is decided by the ONE existing owner,
    _resumed_cached_row, against its real agent metadata. The planned alias and
    agent type are read from the already-bound expectations (the published args
    carry the alias; the root lane carries the agent type) - no alias table and
    no literal. Only the three progress fields that helper's exact key set
    permits are then skipped. A row that claims cached and FAILS the helper is
    refused outright; it never falls through to the fresh-row path.

  2 scriptPath keeps exact-path acceptance. A DIFFERENT path is accepted only
    when the operating system proves it is the same regular file as the
    published script. Missing, malformed, inaccessible, different-file and
    same-bytes-but-different-file all fail closed.
"""
import hashlib
import io
import os
import sys

U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = U + "/view/harness_g1v3/audit_worker_access.py"

HELPER = '''

def _same_published_script(claim, published):
    """True only when the OS proves these name the same regular file.

    Not a path-prefix exception and not a hash allowance: two different files
    with identical bytes are still two files, and are refused. Anything
    missing, malformed or unreadable is refused as well (Codex SEQ 1781).
    """
    if not isinstance(claim, str) or not isinstance(published, str):
        return False
    if not claim or not published:
        return False
    try:
        if not (os.path.isfile(claim) and os.path.isfile(published)):
            return False
        return os.path.samefile(claim, published)
    except OSError:
        return False

'''

EDITS = [
    # ---- 1 the cached row, decided by the one existing owner ---------------
    ('''        agent_id = pr.get("agentId")
        if not agent_id:
            problems.append("%s records no agentId" % label)
            continue
        if pr.get("model") != expect["runtime_model_id"]:
            problems.append("%s ran model %r, not %r"
                            % (label, pr.get("model"),
                               expect["runtime_model_id"]))
        if pr.get("agentType") != expect["agentType"]:
            problems.append("%s ran agent type %r, not %r"
                            % (label, pr.get("agentType"), expect["agentType"]))
        # ZERO TOOL USE MUST BE PROVED, not assumed from a missing field.
        if pr.get("toolCalls") != 0:
            problems.append("%s records toolCalls %r; this lane must prove "
                            "exactly 0" % (label, pr.get("toolCalls")))''',
     '''        agent_id = pr.get("agentId")
        if not agent_id:
            problems.append("%s records no agentId" % label)
            continue
        # A NATIVE CACHED RETURN, decided by the ONE cached-shape owner against
        # this row's real agent metadata. The plan it is judged against comes
        # from the already-bound expectations, never from a literal: the
        # published args carry the model ALIAS the runtime reports on a cached
        # row, and the root lane carries the agent type (Codex SEQ 1781).
        planned = expect["args"][position] if position < len(expect["args"]) else {}
        lane_plan = {"model": planned.get("model"),
                     "agentType": expect["agentType"]}
        rid_dir = os.path.join(session_dir, "subagents", "workflows", rid)
        cached = _resumed_cached_row(pr, rid_dir, lane_plan)
        if "cached" in pr and not cached:
            # It claims the cached shape but its own metadata does not back it.
            # It must NOT reach the fresh-row path and pass by another route.
            problems.append("%s claims a cached row that its exact shape and "
                            "agent metadata do not support" % label)
            continue
        if not cached and pr.get("model") != expect["runtime_model_id"]:
            problems.append("%s ran model %r, not %r"
                            % (label, pr.get("model"),
                               expect["runtime_model_id"]))
        if not cached and pr.get("agentType") != expect["agentType"]:
            problems.append("%s ran agent type %r, not %r"
                            % (label, pr.get("agentType"), expect["agentType"]))
        # ZERO TOOL USE MUST BE PROVED, not assumed from a missing field - and a
        # cached row is the ONE shape whose key set proves it never spawned.
        if not cached and pr.get("toolCalls") != 0:
            problems.append("%s records toolCalls %r; this lane must prove "
                            "exactly 0" % (label, pr.get("toolCalls")))'''),
    # ---- 2 the same frozen script at its durable location -------------------
    ('''    if st.get("scriptPath") != expect["script_path"]:
        problems.append("the state ran %r, this segment published %r"
                        % (st.get("scriptPath"), expect["script_path"]))''',
     '''    if st.get("scriptPath") != expect["script_path"] and not _same_published_script(
            st.get("scriptPath"), expect["script_path"]):
        problems.append("the state ran %r, this segment published %r"
                        % (st.get("scriptPath"), expect["script_path"]))'''),
]


def main():
    s = io.open(P, encoding="utf-8").read()
    before = hashlib.sha256(s.encode("utf-8")).hexdigest()
    print("owner before: %s  %d bytes" % (before, len(s.encode("utf-8"))))
    for old, new in EDITS:
        n = s.count(old)
        if n != 1:
            print("REFUSED: an edit target matches %d times, not once" % n)
            return 1
        s = s.replace(old, new)
    anchor = "\n\ndef record_state(receipt_path, run_id, state_path):"
    if s.count(anchor) != 1:
        print("REFUSED: cannot place the helper deterministically")
        return 1
    s = s.replace(anchor, HELPER + "\ndef record_state(receipt_path, run_id, "
                                   "state_path):", 1)
    io.open(P, "w", encoding="utf-8").write(s)
    after = hashlib.sha256(s.encode("utf-8")).hexdigest()
    print("owner after : %s  %d bytes" % (after, len(s.encode("utf-8"))))
    print("edits applied: %d, plus one new helper" % len(EDITS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
