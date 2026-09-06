# -*- coding: utf-8 -*-
"""Recover the exact era SOURCE bytes the final G2/G3 writer runs on
(Codex SEQ 1722 item 2, corrected by SEQ 1724 items 1 and 2).

No new engine and no framework: this is a CALLER of the already-proved saved-edit
recovery owner. For each source file it walks that file's own recorded operations in
transcript order and applies only the part of each program that owns THAT file,
through the recovery owner's existing per-owner extraction hook.

Two shell facts the caller must honour before the recovery owner sees a program:
an UNQUOTED heredoc was expanded by the shell, so its variables are substituted and
a backslash before a backtick is removed; a quoted one was not and is left alone.

Classification is decided by the record, not by its exit status. A record with no
tool call is not an operation and is not listed. A record whose own program writes
this file and then raises is a genuine missing source write and STOPS the recovery.
A record that only reads it stays read-only even though its historical command
succeeded.
"""
import ast
import hashlib
import io
import json
import os
import re
import shlex
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
U = P + "/budget_inputs_1720"
OUT = U + "/sources_g23"
HARNESS = "harness_g1v3/"
LAST = 69852                       # everything strictly before the final writer

sys.path.insert(0, U + "/owner_derive")
import recover_a7g1_1663 as E                                  # noqa: E402

sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
#: the recovery owner's own heredoc form, used here to read a recorded file write
HD = re.compile(r"cat\s+(>>?)\s+(\S+)\s+<<\s*'?([A-Za-z0-9_]+)'?\n(.*?)\n\3\b", re.S)
#: the same heredocs, keeping whether the tag was QUOTED - the shell expands a body
#: only when it was not
#: one well-formed s/// expression, whatever delimiter it chose
SUBST = re.compile(r"\s*s(?P<d>.)(?:(?!(?P=d)).)*(?P=d)(?:(?!(?P=d)).)*(?P=d)[a-zA-Z]*\s*")
HD_Q = re.compile(r"<<(')?([A-Za-z0-9_]+)'?[^\n]*\n(.*?)\n\2\s*$", re.S | re.M)


def folded(node, env):
    """The string this expression evaluates to, or None - constants, names already
    bound to strings, and their concatenation."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        l, r = folded(node.left, env), folded(node.right, env)
        return (l + r) if (l is not None and r is not None) else None
    return None


def names_a_file(s):
    """A path string that ends in a file name rather than a directory."""
    if s is None or "\n" in s or len(s) > 4096:
        return None
    base = s.rsplit("/", 1)[-1]
    return s if re.match(r"^[\w.\-]+\.[A-Za-z0-9]{1,5}$", base) else None


def blocks_for(src, basename):
    """(kept source, whether the kept part WRITES this file).

    A program that edits several files does it one block at a time, and each block
    opens with the assignment that names the file it works on. Statements before any
    such assignment are the shared preamble. A kept block writes the file when it
    opens the owner's own path in a writing mode - that is what makes a raise here a
    missing source write rather than a failed read.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src, False
    lines = src.splitlines(True)
    env, cur, keep = {}, None, []
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 \
                and isinstance(st.targets[0], ast.Name):
            v = folded(st.value, env)
            if v is not None:
                env[st.targets[0].id] = v
            named = names_a_file(v)
            if named is not None:
                cur = named
        if cur is None or cur.endswith(basename):
            keep.append(st)
    writes = False
    for st in keep:
        for c in ast.walk(st):
            if not isinstance(c, ast.Call) or not c.args:
                continue
            fn = c.func.attr if isinstance(c.func, ast.Attribute) else \
                getattr(c.func, "id", "")
            if fn != "open":
                continue
            path = folded(c.args[0], env)
            mode = folded(c.args[1], env) if len(c.args) > 1 else None
            for kw in c.keywords:
                if kw.arg == "mode":
                    mode = folded(kw.value, env)
            if path and path.endswith(basename) and mode and mode[0] in "wa":
                writes = True
    if len(keep) == len(tree.body):
        return src, writes
    out = []
    for st in keep:
        out.extend(lines[st.lineno - 1:getattr(st, "end_lineno", st.lineno)])
    return "".join(out), writes


def sed_ops(cmd, basename):
    """(substitutions this record makes to THIS file, command without them).

    Per-owner extraction is not only a program-level idea: one recorded shell
    statement renamed two fields across three files at once, and two of those are
    another owner and a test. The substitutions are taken exactly as recorded, in
    recorded order, and only when the statement names this owner; the statement is
    then removed so the rest of the record replays unchanged. A script whose parts
    are not all well-formed substitutions is left alone.
    """
    ops, out = [], []
    for line in cmd.replace("\\\n", " ").splitlines(True):
        head = line.strip()
        if not head.startswith("sed ") or " -i" not in head.split("'")[0]:
            out.append(line)
            continue
        try:
            argv = shlex.split(head)
        except ValueError:
            out.append(line)
            continue
        files = [a for a in argv[1:] if not a.startswith("-")][1:]
        if not files or not [f for f in files if os.path.basename(f) == basename]:
            out.append(line)
            continue
        script = [a for a in argv if a not in files][-1]
        parts = [x.strip() for x in script.split(";") if x.strip()]
        if not all(SUBST.fullmatch(x) for x in parts):
            out.append(line)
            continue
        got = []
        for x in parts:
            d = x[1]
            f = x[2:].split(d)
            if len(f) < 3:
                got = None
                break
            got.append((f[0], f[1], f[2]))
        if got is None:
            out.append(line)
        else:
            ops.extend(got)
    # A RECORD THIS OWNER'S SUBSTITUTIONS DO NOT TOUCH IS HANDED BACK BYTE-FOR-BYTE.
    # Rebuilding it would join its line continuations and change the very command the
    # recovery owner reads, so a record with nothing to strip is never rewritten.
    return (ops, "".join(out)) if ops else ([], cmd)


def durable(pin):
    """The one durable copy whose bytes hash to this recorded pin."""
    for root in (P + "/inputs",
                 P.replace("/post_1500_exact_1626", "") + "/phase1_targeted_1488",
                 R, "/home/faisal/.core827_backups"):
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                c = os.path.join(dp, f)
                try:
                    if os.path.getsize(c) and hashlib.sha256(
                            io.open(c, "rb").read()).hexdigest() == pin:
                        return c
                except OSError:
                    continue
    return None


def main():
    CR, RT, rec, tool_uses, cmd_of, bind_block, results, _text, _MAN = E.build()
    lines = io.open(RT.TRANSCRIPT, encoding="utf-8", errors="replace").readlines()
    targets = json.loads(io.open(U + "/G23_SOURCES.json", encoding="utf-8").read())
    os.makedirs(OUT, exist_ok=True)
    rows = [("file", "line", "tool_use_id", "result_line", "recorded_outcome",
             "category", "before_sha256", "after_sha256", "bytes")]
    seen_ids, counts = {}, {}

    def bind(n):
        """(tool_use_id, result_line, recorded outcome) - exactly one later result."""
        tid = ""
        for c in (json.loads(lines[n - 1]).get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use":
                tid = c.get("id") or ""
        if not tid:
            return "", "", ""
        hits = []
        for m in range(n, len(lines)):
            if tid not in lines[m]:
                continue
            for c in (json.loads(lines[m]).get("message") or {}).get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_result" \
                        and c.get("tool_use_id") == tid:
                    hits.append((m + 1, "error" if c.get("is_error") else "ok"))
        if len(hits) != 1:
            sys.exit("REFUSE: record %d id %s has %d later results" % (n, tid, len(hits)))
        return (tid,) + hits[0]

    def projected(n, command):
        r = json.loads(lines[n - 1])
        for c in (r.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use" \
                    and isinstance(c.get("input"), dict) \
                    and "command" in c["input"]:
                    c["input"]["command"] = command
        return r

    def shell_semantics(cmd, src):
        """An unquoted heredoc was expanded by the shell before python read it."""
        for m in HD_Q.finditer(cmd):
            if m.group(3) != src:
                continue
            if m.group(1):                      # <<'TAG' - literal
                return src
            return RT.expand(src, dict(RT.shell_vars(cmd))).replace("\\`", "`")
        return src

    for target in targets:
        # a file the record CREATES is named alone; a file that already existed and is
        # only edited is named with the pin the record states for it and the line that
        # states it, so the walk starts from a byte the record itself fixes
        name, pin, first = (target, None, 1) if isinstance(target, str) else target
        base = os.path.basename(name)
        text, side, started = None, {}, False
        if pin:
            src = durable(pin)
            if src is None:
                sys.exit("REFUSE: no durable byte hashes %s for %s" % (pin[:16], name))
            text = io.open(src, encoding="utf-8").read()
            started = True
            rows.append((name, first, "", "", "pinned", "recorded-base-pin",
                         "", sha(text), len(text.encode())))

        for n in range(first, LAST + 1):
            if base not in lines[n - 1]:
                continue
            uses = tool_uses(n)
            if not uses:                        # not an operation at all
                continue
            cmd = cmd_of(n) or ""
            hd = [(op, p.strip("\"'"), body) for op, p, _t, body in HD.findall(cmd)]
            own = [(op, body) for op, p, body in hd if p.endswith(base)]
            for op, p, body in hd:
                if not p.endswith(base):
                    side[p] = (side.get(p, "") + body) if op == ">>" else body
            before, cat, err = text, None, None
            if own:
                for op, body in own:
                    text = (text or "") + body + "\n" if op == ">>" else body + "\n"
                cat, started = "recorded-file-write", True
            elif started:
                subs, stripped = sed_ops(cmd, base)
                for old, new, flags in subs:
                    if old not in text:
                        sys.exit("REFUSE: record %d substitution %r has no match in %s"
                                 % (n, old, name))
                    text = text.replace(old, new) if "g" in flags \
                        else text.replace(old, new, 1)
                # the recorded substitutions are themselves source effects: if the
                # program that followed them cannot be replayed here, they still
                # happened, so the revert below goes back to THIS state, not before
                after_subs = text

                def prepare(_line, s, _b=base):
                    kept, w = blocks_for(shell_semantics(cmd, s), _b)
                    if w:
                        writes_flag.append(True)
                    return kept
                writes_flag = []
                try:
                    text, _s = RT.apply_saved_edits(
                        text, {n: projected(n, stripped)}, HARNESS + name,
                        prepare=prepare, side=side)
                    cat = "applied" if text != before else "read-only"
                except Exception as exc:
                    text, err = after_subs, "%s: %s" % (type(exc).__name__, str(exc)[:120])
                    if writes_flag:
                        tid, rl, out = bind(n)
                        sys.exit("REFUSE: record %d (%s, result %s, recorded %s) writes "
                                 "%s and could not be applied: %s"
                                 % (n, tid, rl, out, name, err))
                    cat = ("applied(substitutions only)" if text != before
                           else "read-only(raised)")
            else:
                continue
            if cat == "read-only" and before is not None:
                counts["read-only"] = counts.get("read-only", 0) + 1
                continue
            tid, rl, out = bind(n)
            if tid:
                seen_ids[tid] = seen_ids.get(tid, 0) + 1
            counts[cat] = counts.get(cat, 0) + 1
            rows.append((name, n, tid, rl, out, cat,
                         sha(before) if before is not None else "",
                         sha(text), len(text.encode())))
            print("%-26s %6d %-20s %-8s %s" % (name, n, cat, out, sha(text)[:16]),
                  flush=True)
        if text is None:
            sys.exit("REFUSE: no recorded file write for %s" % name)
        dst = os.path.join(OUT, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        io.open(dst, "w", encoding="utf-8", newline="").write(text)

    with io.open(OUT + "/SOURCE_OPS.tsv", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    print("recovered %d source files; %s; %d unique tool ids"
          % (len(targets), ", ".join("%s=%d" % kv for kv in sorted(counts.items())),
             len(seen_ids)))


if __name__ == "__main__":
    main()
