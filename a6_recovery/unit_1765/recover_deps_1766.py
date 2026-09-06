# -*- coding: utf-8 -*-
"""Restore the recorded direct dependencies for A6's tests (Codex SEQ 1766).

Only the literal replacements each recorded program lists FOR ONE NAMED FILE are
taken; no historical command is executed, and the other files those programs also
touched are ignored. Two shapes appear and both are read structurally:

  * `p = "<file>"` followed by `s = s.replace(old, new)` calls
  * `patch("<file>", [(old, new), ...])`
"""
import ast
import hashlib
import io
import json
import re
import subprocess

R = "/home/faisal/EventMarketDB-driver-recovery"
T = R + "/a3_recovery/regen_1541/evidence/transcript/accepted_prefix.jsonl"


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


def command(line_no, tool_id):
    raw = subprocess.run(["sed", "-n", "%dp" % line_no, T], capture_output=True, text=True).stdout
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
    walk(json.loads(raw))
    if len(found) != 1:
        raise SystemExit("REFUSED: line %d holds %d records with id %s"
                         % (line_no, len(found), tool_id))
    return found[0]["input"]["command"], raw


def py_blocks(cmd):
    """Every python heredoc body in the recorded command, in order."""
    out, lines = [], cmd.splitlines()
    i = 0
    while i < len(lines):
        m = re.search(r"<<'([A-Z]+)'\s*$", lines[i])
        if m:
            tag, j = m.group(1), i + 1
            body = []
            while j < len(lines) and lines[j].strip() != tag:
                body.append(lines[j])
                j += 1
            out.append("\n".join(body))
            i = j
        i += 1
    return out


def _const(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def pairs_for(body, target):
    """The (old, new) literals this program applies to `target`, in order."""
    tree = ast.parse(body)
    found, current = [], None
    for node in ast.walk(tree):
        # patch("<file>", [(old, new), ...])
        if (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "patch"
                and node.args and (_const(node.args[0]) or "").rsplit("/", 1)[-1] == target):
            for e in node.args[1].elts:
                a, b = _const(e.elts[0]), _const(e.elts[1])
                if a is not None and b is not None:
                    found.append((a, b))
    if found:
        return found
    # p = "<file>" ... s = s.replace(old, new), read in SOURCE ORDER: these
    # programs apply their replacements sequentially and later ones depend on
    # earlier output, so ast.walk's breadth-first order would be wrong.
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            v = _const(node.value)
            if v is None and isinstance(node.value, ast.BinOp):
                # the recorded programs also write `p = base + "<file>.py"`
                v = _const(node.value.right)
            if v and v.endswith(".py"):
                current = v.rsplit("/", 1)[-1]
            elif (isinstance(node.value, ast.Call)
                  and isinstance(node.value.func, ast.Attribute)
                  and node.value.func.attr == "replace" and current == target):
                a = _const(node.value.args[0]) if node.value.args else None
                b = _const(node.value.args[1]) if len(node.value.args) > 1 else None
                if a is not None and b is not None:
                    found.append((a, b))
    return found


def apply_forward(text, edits, label):
    for i, (old, new) in enumerate(edits, 1):
        n = text.count(old)
        if n != 1:
            raise SystemExit("REFUSED: %s edit %d applies %d times, not once" % (label, i, n))
        text = text.replace(old, new)
    return text


def splice_ops(body, target):
    """A recorded `start/end/new` function splice for one file, read structurally.

    Shape: start = s.index(<lit>); end = s.index(<lit>, start + 1); new = <lit>;
    s = s[:start] + new + s[end:]. Returned as (start_literal, end_literal, new).
    """
    tree = ast.parse(body)
    seen, lits = None, {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            v = _const(node.value)
            if v is None and isinstance(node.value, ast.BinOp):
                v = _const(node.value.right)
            if name == "p" and v and v.endswith(".py"):
                seen = v.rsplit("/", 1)[-1]
            elif seen == target and name in ("start", "end") and isinstance(node.value, ast.Call) \
                    and getattr(node.value.func, "attr", None) == "index" and node.value.args:
                lits[name] = _const(node.value.args[0])
            elif seen == target and name == "new":
                lits["new"] = _const(node.value)
    if {"start", "end", "new"} <= set(lits):
        # the tail offset is part of the record: `s = s[:start] + new + s[end + N:]`
        offset = 0
        for node in ast.walk(tree):
            if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Slice)
                    and node.slice.lower is not None and node.slice.upper is None
                    and isinstance(node.slice.lower, ast.BinOp)
                    and isinstance(node.slice.lower.left, ast.Name)
                    and node.slice.lower.left.id == "end"
                    and isinstance(node.slice.lower.right, ast.Constant)):
                offset = node.slice.lower.right.value
        return lits["start"], lits["end"], lits["new"], offset
    return None


def apply_splice(text, ops, label):
    start_lit, end_lit, new, offset = ops
    if text.count(start_lit) < 1:
        raise SystemExit("REFUSED: %s splice start not found" % label)
    a = text.index(start_lit)
    b = text.index(end_lit, a + 1)
    return text[:a] + new + text[b + offset:]
