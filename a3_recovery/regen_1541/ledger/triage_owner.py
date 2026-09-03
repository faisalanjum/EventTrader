#!/usr/bin/env python3
"""Triage the owner reconstruction record by record (Codex SEQ 1540 item 1).

Replays the modifying records for one file and, for every record that refuses, reports
WHICH anchor text it could not find and WHICH transcript record introduces that text.
That turns "16 refusals" into a list of concrete, checkable next actions instead of a
guess. Nothing is written outside this directory.
"""
import collections
import hashlib
import json
import os
import re
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(R, "ledger"))
import replay_transcript as RT

WRITES = re.compile(
    r"""(io\.open|open)\(\s*p\s*,\s*["']w|["'][^"']*%s["']\s*,\s*["']w|"""
    r""">>\s*"?[^"\s]*%s|write_text\(""")
#: an anchor assignment inside a saved edit program: old = '''...''' or "..."
ANCHOR = re.compile(r"""^\s*(old\w*)\s*=\s*(?:\(\s*)?('''|\"\"\"|'|\")(.*?)\2""",
                    re.S | re.M)


def modifying_records(basename, upto):
    pat = re.compile(WRITES.pattern % (re.escape(basename), re.escape(basename)))
    lines = []
    with open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            if n >= upto:
                break
            if basename.split(".")[0] in line:
                lines.append(n)
    recs = RT.lines(lines)
    mod, base = [], None
    for n in lines:
        for b in ((recs[n].get("message") or {}).get("content") or []):
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            nm = b.get("name")
            inp = b.get("input") or {}
            fp = str(inp.get("file_path") or "")
            p = inp.get("command") or inp.get("content") or ""
            if nm == "Write" and fp.endswith(basename):
                if base is None:
                    base = n
                else:
                    mod.append(n)
            elif nm == "Edit" and fp.endswith(basename):
                mod.append(n)
            elif nm == "Bash" and basename in p and pat.search(p):
                mod.append(n)
    return base, [m for m in mod if base is not None and m > base], recs


def anchors(rec, basename):
    """-> the anchor strings a refused record was looking for."""
    try:
        prog = RT.heredoc(RT.bash_command(rec))
    except RT.TranscriptError:
        e = RT._edit_input(rec, basename)
        return [e[0]] if e else []
    return [m.group(3) for m in ANCHOR.finditer(prog)]


def introducer(text, before):
    """-> transcript lines whose saved payload contains `text`, before `before`."""
    out = []
    needle = text.strip().splitlines()[0].strip() if text.strip() else ""
    if len(needle) < 12:
        return out
    with open(RT.TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            if n >= before or needle not in line:
                continue
            rec = json.loads(line)
            for b in ((rec.get("message") or {}).get("content") or []):
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                p = (inp.get("command") or inp.get("content")
                     or inp.get("new_string") or "")
                if needle in p:
                    out.append(n)
    return sorted(set(out))


def run(basename, upto, target=None):
    base, mod, recs = modifying_records(basename, upto)
    _p, txt = RT.write_input(recs[base])
    rows, applied = [], 0
    for n in mod:
        try:
            t2, _ = RT.apply_saved_edits(txt, {n: recs[n]}, basename)
            changed = t2 != txt
            txt = t2
            applied += 1 if changed else 0
            rows.append(collections.OrderedDict([
                ("line", n), ("result", "applied" if changed else "no-change"),
                ("sha256_after", hashlib.sha256(txt.encode()).hexdigest()),
                ("bytes_after", len(txt))]))
        except Exception as exc:
            missing = [a for a in anchors(recs[n], basename) if a and a not in txt]
            rows.append(collections.OrderedDict([
                ("line", n), ("result", "REFUSED"),
                ("error", "%s: %s" % (type(exc).__name__, str(exc)[:80])),
                ("missing_anchors", len(missing)),
                ("first_missing_head",
                 (missing[0].strip().splitlines() or [""])[0][:90] if missing else None),
                ("introduced_by", introducer(missing[0], n) if missing else []),
                ("sha256_after", hashlib.sha256(txt.encode()).hexdigest())]))
    return collections.OrderedDict([
        ("basename", basename), ("base_line", base),
        ("modifying_records", len(mod)), ("applied", applied),
        ("refused", sum(1 for r in rows if r["result"] == "REFUSED")),
        ("reached_sha256", hashlib.sha256(txt.encode()).hexdigest()),
        ("reached_bytes", len(txt)),
        ("converged", hashlib.sha256(txt.encode()).hexdigest() == target),
        ("steps", rows)])


if __name__ == "__main__":
    rep = run(sys.argv[1], int(sys.argv[2]),
              sys.argv[3] if len(sys.argv) > 3 else None)
    print(json.dumps(rep, indent=1))
