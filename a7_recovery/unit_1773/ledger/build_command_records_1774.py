# -*- coding: utf-8 -*-
"""Preserve the ORIGINAL command/result records for this unit's runs.

Codex SEQ 1774 item 4, reusing the accepted A6 command-record pattern. The
earlier reconstruction and candidate logs hold their output but not their full
invocation or exit status, because the shell wrote only the payload's stdout.
Those invocations ARE durably recorded in the Core transcript, so they are
resolved there BY CONTENT - the tool_use that launched each payload and the
tool_result that returned - and written out with the transcript path, physical
line numbers and the sha256 of each raw line.

Nothing is re-run and no output is reconstructed: successful work is not
repeated to manufacture provenance.
"""
import hashlib
import io
import json
import os

T = ("/home/faisal/.claude/projects/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = UNIT + "/evidence/COMMAND_RECORDS_1774.json"

#: the payload each recorded run launched, and the log it wrote
WANT = [("ledger/reconstruct_producer_1773.py", "logs/reconstruct_1773f.log",
         "the accepted producer reconstruction"),
        ("ledger/build_candidate_1773.py", "logs/candidate_1773b.log",
         "the accepted two-build candidate proof"),
        ("ledger/run_tests_1774.py", "logs/tests_1774.log",
         "the focused and affected test suites"),
        ("ledger/run_mutations_1774.py", "logs/mutations_1774.log",
         "the controlled mutation cases"),
        ("compose_views_1773.sh", "logs/compose_views_1773.log",
         "the view compose command")]


def blocks(rec):
    c = ((rec.get("message") or {}).get("content"))
    return c if isinstance(c, list) else []


def main():
    lines = io.open(T, encoding="utf-8").read().splitlines(True)
    uses = {}          # tool_use_id -> (lineno, command)
    results = {}       # tool_use_id -> (lineno, exit/output head)
    for i, raw in enumerate(lines, 1):
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        for b in blocks(rec):
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and isinstance(b.get("input"), dict):
                cmd = b["input"].get("command")
                if isinstance(cmd, str):
                    uses[b.get("id")] = (i, cmd)
            elif b.get("type") == "tool_result":
                out = b.get("content")
                if isinstance(out, list):
                    out = " ".join(x.get("text", "") for x in out
                                   if isinstance(x, dict))
                results[b.get("tool_use_id")] = (i, out if isinstance(out, str) else "")

    def line_sha(n):
        return hashlib.sha256(lines[n - 1].encode("utf-8")).hexdigest()

    out = []
    for payload, log, what in WANT:
        hits = [(tid, ln, cmd) for tid, (ln, cmd) in uses.items() if payload in cmd]
        if not hits:
            out.append({"payload": payload, "log": log, "what": what,
                        "found": False,
                        "note": "no invocation of this payload is recorded"})
            continue
        tid, ln, cmd = sorted(hits, key=lambda h: h[1])[-1]     # the run that stands
        rln, rtext = results.get(tid, (None, ""))
        rec = {"payload": payload, "log": log, "what": what, "found": True,
               "transcript": T, "tool_use_id": tid,
               "invocation_line": ln, "invocation_line_sha256": line_sha(ln),
               "command": cmd,
               "result_line": rln,
               "result_line_sha256": line_sha(rln) if rln else None,
               "result_head": rtext[:400]}
        p = os.path.join(UNIT, log)
        if os.path.isfile(p):
            rec["log_sha256"] = hashlib.sha256(io.open(p, "rb").read()).hexdigest()
            rec["log_bytes"] = os.path.getsize(p)
        out.append(rec)

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, indent=1) + "\n")
    for r in out:
        print("  %-42s %s" % (r["payload"],
                              ("line %s, result line %s" % (r.get("invocation_line"),
                                                            r.get("result_line")))
                              if r["found"] else "NOT RECORDED"))
    print("->", OUT)


if __name__ == "__main__":
    main()
