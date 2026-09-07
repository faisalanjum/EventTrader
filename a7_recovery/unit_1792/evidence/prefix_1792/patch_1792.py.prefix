# -*- coding: utf-8 -*-
"""The smallest complete form of remedy A (Codex SEQ 1792 item 2).

ONE owner for the newly declared input rule, consulted by BOTH input owners and
threaded from the real caller. The payload itself lives in the frozen run root,
never here, and is never inferred from the transcript being audited. A record
that carries no message is tolerated only when its canonical attachment object
is byte-exactly one the root declares; anything else - unknown, altered,
duplicated, misplaced, or present with nothing declared - still refuses.
Closed A1 behaviour is untouched: both owners keep their old default.
"""
import hashlib, io, os, sys
U = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = U + "/view/harness_g1v3/audit_worker_access.py"
G = U + "/view/harness_g1v3/a7_g1_build.py"

AUD_HELPER = '''

def _declared_attachment(rec, declared):
    """-> True only when this message-less record is EXACTLY a declared input.

    `declared` is the run root's own list of canonical sha256 strings. It is
    supplied by the caller from frozen evidence; nothing here knows a payload,
    a url, a type name or a keyword, and nothing is read from the record to
    decide what is allowed. A malformed declaration admits nothing.
    """
    if not isinstance(declared, (list, tuple)) or not declared:
        return False
    if not all(isinstance(d, str) and len(d) == 64 for d in declared):
        return False
    if not isinstance(rec, dict) or rec.get("message") is not None:
        return False
    obj = rec.get("attachment")
    if not isinstance(obj, dict):
        return False
    try:
        canon = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return False
    return hashlib.sha256(canon.encode("utf-8")).hexdigest() in declared

'''

EDITS = [
    # ---- the shape owner ---------------------------------------------------
    (A, '''def _g1_shape_problems(recs, agent_id):''',
        '''def _g1_shape_problems(recs, agent_id, declared=()):'''),
    (A, '''        message = rec.get("message")
        if not isinstance(message, dict):
            bad.append("agent %s's record %d carries a %s message, not an "
                       "object" % (agent_id, i, type(message).__name__))''',
        '''        message = rec.get("message")
        if not isinstance(message, dict):
            # THE ONE DECLARED ADMINISTRATIVE INPUT. Tolerated only when the
            # root declared its exact canonical bytes; every other message-less
            # record is still the named problem it always was.
            if not _declared_attachment(rec, declared):
                bad.append("agent %s's record %d carries a %s message, not an "
                           "object" % (agent_id, i, type(message).__name__))'''),
    # ---- the input-topology owner -------------------------------------------
    (A, '''def _input(recs, pin):''', '''def _input(recs, pin, declared=()):'''),
    (A, '''    for i, r in enumerate(recs[1:], 1):
        if r.get("type") != "assistant" or _role(r) != "assistant":
            bad.append(_LaterInput(''',
        '''    seen_declared = 0
    for i, r in enumerate(recs[1:], 1):
        if _declared_attachment(r, declared):
            # at most ONE, and never in place of the prompt at record 0
            seen_declared += 1
            if seen_declared > 1:
                bad.append(_LaterInput(
                    "record %d repeats the declared administrative input; "
                    "exactly one is allowed" % i))
            continue
        if r.get("type") != "assistant" or _role(r) != "assistant":
            bad.append(_LaterInput('''),
    # ---- thread it from the real caller --------------------------------------
    (A, '''    shape = _g1_shape_problems(recs, agent_id)''',
        '''    shape = _g1_shape_problems(recs, agent_id, declared)'''),
    (A, '''    problems = list(_input(recs, prompt_sha) or [])''',
        '''    problems = list(_input(recs, prompt_sha, declared) or [])'''),
    # ---- the root declares it, the audit passes it ------------------------------
    (G, '''def freeze_root(out_dir, run_dir, expect_sha):''',
        '''def freeze_root(out_dir, run_dir, expect_sha, declared_attachments=()):'''),
    (G, '''        ("max_attempts", MAX_ATTEMPTS),''',
        '''        ("max_attempts", MAX_ATTEMPTS),
        # the administrative inputs this run declares, as canonical sha256
        # strings supplied by the caller from reviewed evidence
        ("declared_input_attachments", [str(x) for x in declared_attachments]),'''),
    (G, '''        ("effort", root["lane"]["effort"]),
        ("captures", captures)])''',
        '''        ("effort", root["lane"]["effort"]),
        ("declared_input_attachments",
         root.get("declared_input_attachments") or []),
        ("captures", captures)])'''),
]


def main():
    for path, old, new in EDITS:
        s = io.open(path, encoding="utf-8").read()
        n = s.count(old)
        if n != 1:
            print("REFUSED: a target matches %d times in %s" % (n, os.path.basename(path)))
            return 1
        io.open(path, "w", encoding="utf-8").write(s.replace(old, new, 1))
    s = io.open(A, encoding="utf-8").read()
    anchor = "\n\ndef _pairs(asst):"
    if s.count(anchor) != 1:
        print("REFUSED: cannot place the helper deterministically")
        return 1
    io.open(A, "w", encoding="utf-8").write(
        s.replace(anchor, AUD_HELPER + "\ndef _pairs(asst):", 1))
    for p in (A, G):
        print("  %-24s %s" % (os.path.basename(p),
                              hashlib.sha256(io.open(p, "rb").read()).hexdigest()))
    print("  edits applied: %d plus one helper" % len(EDITS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
