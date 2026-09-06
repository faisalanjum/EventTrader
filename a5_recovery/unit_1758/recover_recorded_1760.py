# -*- coding: utf-8 -*-
"""Recover recorded program material from the transcript (Codex SEQ 1760).

Only LITERAL material is read: a heredoc body, or the old/new string constants a
recorded patch program assigns. No historical shell command is executed. Pairs are
grouped by their variable suffix (old/new, old2/new2 ...) so a record that carries
several patches can have exactly the wanted ones selected.
"""
import ast
import hashlib
import io
import json
import re
import subprocess

R = "/home/faisal/EventMarketDB-driver-recovery"
T = R + "/a3_recovery/regen_1541/evidence/transcript/accepted_prefix.jsonl"
_PAIR = re.compile(r"^(old|new)(\d*)$")


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


def tool_use(line_no, tool_id):
    """The one recorded tool_use with this id on this transcript line."""
    line = subprocess.run(["sed", "-n", "%dp" % line_no, T], capture_output=True, text=True).stdout
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "tool_use" and o.get("id") == tool_id:
                found.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(json.loads(line))
    if len(found) != 1:
        raise SystemExit("REFUSED: line %d holds %d records with id %s" % (line_no, len(found), tool_id))
    return found[0]["input"]["command"]


def heredoc(cmd, tag):
    """The literal body the recorded command fed to a <<'TAG' heredoc."""
    lines = cmd.splitlines()
    start = next(i for i, l in enumerate(lines) if l.rstrip().endswith("<<'%s'" % tag))
    end = next(i for i, l in enumerate(lines) if i > start and l.strip() == tag)
    return "\n".join(lines[start + 1:end]) + "\n"


def pairs(cmd, tag="PY", want=None):
    """(old, new) constants the recorded patch program assigns, by suffix."""
    body = heredoc(cmd, tag)
    got = {}
    for node in ast.walk(ast.parse(body)):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        t = node.targets[0]
        if not isinstance(t, ast.Name):
            continue
        m = _PAIR.match(t.id)
        if not m:
            continue
        val = _literal_or_regex(node.value)
        if val is None:
            continue
        got.setdefault(m.group(2), {})[m.group(1)] = val
    out = []
    for suffix in sorted(got, key=lambda x: (x != "", x)):
        if want is not None and suffix not in want:
            continue
        d = got[suffix]
        if "old" in d and "new" in d:
            out.append((d["old"], d["new"]))
    if want is not None and len(out) != len(want):
        raise SystemExit("REFUSED: wanted suffixes %s, recovered %d pairs" % (want, len(out)))
    return out


class RecordedSearch(object):
    """An `old` the recorded program computed with re.search(<literal>, s, flags).

    The pattern is recorded material; resolving it against the text being patched
    is exactly what the original program did, so nothing is invented here.
    """

    def __init__(self, pattern, flags):
        self.pattern = pattern
        self.flags = flags

    def resolve(self, text):
        m = re.search(self.pattern, text, self.flags)
        if m is None:
            raise SystemExit("REFUSED: the recorded pattern matches nothing")
        return m.group(0)


def _literal_or_regex(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    # re.search(<pattern>, s, re.S).group(0)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "group" and isinstance(node.func.value, ast.Call)):
        inner = node.func.value
        if (isinstance(inner.func, ast.Attribute) and inner.func.attr == "search"
                and inner.args and isinstance(inner.args[0], ast.Constant)):
            flags = 0
            for a in inner.args[2:]:
                if isinstance(a, ast.Attribute) and a.attr in ("S", "DOTALL"):
                    flags |= re.S
            return RecordedSearch(inner.args[0].value, flags)
    return None


def apply_forward(text, edits, label):
    for i, (old, new) in enumerate(edits, 1):
        if isinstance(old, RecordedSearch):
            old = old.resolve(text)
        n = text.count(old)
        if n != 1:
            raise SystemExit("REFUSED: %s edit %d applies %d times, not once" % (label, i, n))
        text = text.replace(old, new)
    return text
