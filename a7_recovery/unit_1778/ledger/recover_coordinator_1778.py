# -*- coding: utf-8 -*-
"""Recover the ORIGINAL G1 coordinator exactly from its own recorded records.

Codex SEQ 1778 item 1. The script is never retyped or rewritten: its Write and
its two Edits are read out of the published transcript by tool_use id, each old
string must match EXACTLY ONCE (a second match would mean the replacement was
ambiguous, so it refuses rather than guessing), and the linked results are
checked to confirm each operation actually succeeded at the time.
"""
import hashlib
import io
import json
import os
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
T = R + "/a3_recovery/regen_1541/evidence/transcript/accepted_prefix.jsonl"
UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = UNIT + "/view/scratchpad/g1_run_1525.py"

WRITE = (92637, "toolu_019gjcztEDhRW4RydxWrLyT6", 92643)
EDITS = [(93141, "toolu_01DKuiG9gKf8WHCmDmVyZLur", 93143),
         (93152, "toolu_018gYvLfR55JwAqL9nTc6oQU", 93154)]
WANT_SHA = "e2aba199fbe7328ee4f14f6061cfc7599123360833142414bf1e8a79c2f2715d"
WANT_BYTES = 7158


def blocks(rec):
    c = ((rec.get("message") or {}).get("content"))
    return c if isinstance(c, list) else []


def main():
    lines = io.open(T, encoding="utf-8").read().splitlines(True)

    def at(n):
        return json.loads(lines[n - 1])

    def use(n, tid):
        for b in blocks(at(n)):
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") == tid:
                return b
        raise SystemExit("line %d carries no tool_use %s" % (n, tid))

    def result_ok(n):
        for b in blocks(at(n)):
            if isinstance(b, dict) and b.get("type") == "tool_result":
                out = b.get("content")
                if isinstance(out, list):
                    out = "".join(x.get("text", "") for x in out if isinstance(x, dict))
                return not b.get("is_error"), str(out)[:80]
        return False, "no tool_result"

    ln, tid, rln = WRITE
    w = use(ln, tid)
    ok, said = result_ok(rln)
    if not ok:
        raise SystemExit("the Write did not succeed: %s" % said)
    s = w["input"]["content"]
    path = w["input"]["file_path"]
    print("Write  line %d  %d bytes -> %s" % (ln, len(s), os.path.basename(path)))
    print("   result %d: %s" % (rln, said))

    for ln, tid, rln in EDITS:
        e = use(ln, tid)
        if e["input"].get("file_path") != path:
            raise SystemExit("edit at %d targets another file" % ln)
        old, new = e["input"]["old_string"], e["input"]["new_string"]
        n = s.count(old)
        if n != 1:
            raise SystemExit("edit at %d: its old string matches %d times, not once"
                             % (ln, n))
        ok, said = result_ok(rln)
        if not ok:
            raise SystemExit("the edit at %d did not succeed: %s" % (ln, said))
        s = s.replace(old, new)
        print("Edit   line %d  -%d +%d  -> %d bytes" % (ln, len(old), len(new), len(s)))
        print("   result %d: %s" % (rln, said))

    body = s.encode("utf-8")
    got = hashlib.sha256(body).hexdigest()
    print("\nrecovered: %d bytes  %s" % (len(body), got))
    print("required : %d bytes  %s" % (WANT_BYTES, WANT_SHA))
    match = (got == WANT_SHA and len(body) == WANT_BYTES)
    print("MATCH:", match)
    if not match:
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "wb").write(body)
    print("written ->", os.path.relpath(OUT, UNIT))
    print("original logical path:", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
