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
import copy
import hashlib
import io
import json
import os
import re
import shlex
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
P = R + "/a4_recovery/regen_1570/targeted_1589/post_1500_exact_1626"
U = P + "/a4_owner_1726"
PRIOR = P + "/budget_inputs_1720"    # accepted, read only
#: which era this run recovers: the output directory, the harness the paths sit in,
#: and the record strictly before which the walk stops
OUT = U + "/" + os.environ.get("SOURCES_DIR", "sources_g23")
HARNESS = "harness_g1v3/"
LAST = int(os.environ.get("LAST_RECORD", "69852"))

sys.path.insert(0, PRIOR + "/owner_derive")
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


def call_file(st, env):
    """The file this top-level CALL names as its first argument, or None."""
    if not isinstance(st, ast.Expr) or not isinstance(st.value, ast.Call):
        return None
    call = st.value
    if not call.args:
        return None
    return names_a_file(folded(call.args[0], env))


def narrow_loop(st, basename):
    """A literal loop over file names, narrowed to this owner: the loop node with only
    this owner's names left, False when it names none of them, None when the statement
    is not that form."""
    if not isinstance(st, ast.For) or not isinstance(st.iter, (ast.Tuple, ast.List)):
        return None
    vals = [e.value for e in st.iter.elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    if len(vals) != len(st.iter.elts) or not vals:
        return None
    if not any(names_a_file(v) for v in vals):
        return None
    mine = [v for v in vals if v.endswith(basename)]
    if not mine:
        return False
    node = copy.deepcopy(st)
    node.iter = ast.Tuple(elts=[ast.Constant(value=v) for v in mine], ctx=ast.Load())
    return ast.fix_missing_locations(node)


def expand_heads(cmd, RT):
    """The command with shell variables resolved everywhere the SHELL resolved them.

    A saved program is recognised by the interpreter named just before it, and some
    records name that interpreter - and the script it runs - through a shell variable,
    so the program is invisible and every edit it makes is skipped in silence. The
    shell had already substituted those, so they are substituted here too. Heredoc
    BODIES are left exactly as recorded: a quoted body was never expanded, and an
    unquoted one is handled where its own program is read.
    """
    env = dict(RT.shell_vars(cmd))
    if not env:
        return cmd
    bodies = [(m.start(3), m.end(3)) for m in HD_Q.finditer(cmd)]
    out, done = [], 0
    for a, b in bodies:
        if a < done:
            continue
        out.append(RT.expand(cmd[done:a], env))
        out.append(cmd[a:b])
        done = b
    out.append(RT.expand(cmd[done:], env))
    return "".join(out)


def prog_before_write(cmd, basename):
    """True when this command's python program sits BEFORE its own write to this file."""
    write_at = [m.start() for m in HD.finditer(cmd)
                if m.group(2).strip("\"'").endswith(basename)]
    prog_at = [m.start() for m in HD_Q.finditer(cmd)
               if "python" in cmd[:m.start()].split("\n")[-1]]
    return bool(write_at and prog_at and min(prog_at) < min(write_at))


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
    env, cur, keep, loops = {}, None, [], []
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 \
                and isinstance(st.targets[0], ast.Name):
            v = folded(st.value, env)
            if v is not None:
                env[st.targets[0].id] = v
            named = names_a_file(v)
            if named is not None:
                cur = named
        # A STATEMENT MAY NAME ITS FILE IN THE CALL ITSELF. One record defines an
        # edit(path, old, new, why) helper and calls it for two owners in turn; the
        # file is the argument, not a block heading, so such a statement is judged on
        # its own and does not change which block the ones after it belong to.
        called = call_file(st, env)
        if called is not None:
            if called.endswith(basename):
                keep.append(st)
            continue
        # A STATEMENT MAY LOOP OVER THE FILES IT EDITS. One record rewires the same
        # call in two owners with `for f in ("a", "b")`. The loop is kept with its
        # iterable narrowed to this owner's own names, so the other owner is excluded
        # without touching what the loop does.
        narrowed = narrow_loop(st, basename)
        if narrowed is not None:
            if narrowed is not False:
                keep.append(narrowed)
                loops.append(narrowed)
            continue
        if cur is None or cur.endswith(basename):
            keep.append(st)
    # A HELPER THIS PROGRAM DEFINES CAN BE THE WRITER. `edit(path, old, new, why)`
    # opens its own first parameter for writing, so a kept call into it is a write to
    # the file that call names - reading only the top-level `open` would score three
    # completed edits as a read.
    writers = set()
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef) or not fn.args.args:
            continue
        first = fn.args.args[0].arg
        for c in ast.walk(fn):
            if isinstance(c, ast.Call) and c.args \
                    and (c.func.attr if isinstance(c.func, ast.Attribute)
                         else getattr(c.func, "id", "")) == "open" \
                    and isinstance(c.args[0], ast.Name) and c.args[0].id == first:
                mode = folded(c.args[1], env) if len(c.args) > 1 else None
                for kw in c.keywords:
                    if kw.arg == "mode":
                        mode = folded(kw.value, env)
                if mode and mode[0] in "wa":
                    writers.add(fn.name)
    writes = False
    for st in loops:
        for c in ast.walk(st):
            if isinstance(c, ast.Call) and len(c.args) > 1 \
                    and (c.func.attr if isinstance(c.func, ast.Attribute)
                         else getattr(c.func, "id", "")) == "open":
                mode = folded(c.args[1], env)
                if mode and mode[0] in "wa":
                    writes = True
    for st in keep:
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            name = (st.value.func.attr if isinstance(st.value.func, ast.Attribute)
                    else getattr(st.value.func, "id", ""))
            if name in writers:
                f = call_file(st, env)
                if f and f.endswith(basename):
                    writes = True
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
    if len(keep) == len(tree.body) and not loops:
        return src, writes
    # EACH SELECTED STATEMENT ONCE, AND ONLY ITSELF. Taking whole physical lines
    # repeated a line that carried several statements once per statement and joined
    # the pieces with nothing, so two calls ran together and the fragment did not
    # parse; it also dragged in a neighbour that belongs to another owner. The
    # statement's own source segment is exact, so a shared line contributes only the
    # part that was selected, and the pieces are separated by a newline whether or
    # not the program ended with one.
    out = []
    for st in keep:
        # A NARROWED LOOP STILL CARRIES THE ORIGINAL SPAN, so asking the source for
        # its text would hand back the very names that were just excluded; it is
        # written from its own tree instead.
        seg = None if any(st is nl for nl in loops) else ast.get_source_segment(src, st)
        if seg is None:
            # a narrowed loop is a NEW node with no span in the original text; it is
            # written back out from its own syntax tree, which keeps every value it
            # carries and only drops the names that belong to another owner
            try:
                seg = ast.unparse(st)
            except Exception:
                return src, writes
        out.append(seg)
    return "\n".join(out) + "\n", writes


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
    targets = json.loads(io.open(U + "/" + os.environ.get("SOURCES_LIST",
                                                      "G23_SOURCES.json"),
                             encoding="utf-8").read())
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

    def apply_program(n, cmd, base, text, side):
        """This record's saved edit program, applied to THIS owner only."""
        subs, stripped = sed_ops(cmd, base)
        for old, new, flags in subs:
            if old not in text:
                sys.exit("REFUSE: record %d substitution %r has no match" % (n, old))
            text = text.replace(old, new) if "g" in flags else text.replace(old, new, 1)
        out, _s = RT.apply_saved_edits(
            text, {n: projected(n, stripped)}, HARNESS + base,
            prepare=lambda _l, x: blocks_for(shell_semantics(cmd, x), base)[0], side=side)
        return out

    def shell_semantics(cmd, src):
        """An unquoted heredoc was expanded by the shell before python read it."""
        for m in HD_Q.finditer(cmd):
            if m.group(3) != src:
                continue
            if m.group(1):                      # <<'TAG' - literal
                return src
            return RT.expand(src, dict(RT.shell_vars(cmd))).replace("\\`", "`")
        return src

    helpers = {}
    RT.SIBLING_RESOLVER = lambda path, _line: helpers.get(path)

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
            # ONE RESOLVED VIEW OF THE COMMAND, used for everything below. The shell
            # substituted its variables before anything ran, so the paths a heredoc
            # writes and the script an interpreter runs are the SAME concrete paths -
            # keeping two spellings is how a written helper and its own run stopped
            # finding each other.
            cmd = expand_heads(cmd_of(n) or "", RT)
            hd = [(op, p.strip("\"'"), body) for op, p, _t, body in HD.findall(cmd)]
            own = [(op, body) for op, p, body in hd if p.endswith(base)]
            # A RECORDED FILE WRITE IS NOT ALWAYS A SHELL HEREDOC. The write tool states
            # the whole file directly, and an owner that begins that way would otherwise
            # never start.
            for c in uses:
                inp = c.get("input") or {}
                if c.get("name") == "Write" and str(inp.get("file_path", "")).endswith(base):
                    own.append((">", inp.get("content", "")))
            for op, p, body in hd:
                if not p.endswith(base):
                    side[p] = (side.get(p, "") + body) if op == ">>" else body
                    # A COMMAND MAY WRITE A HELPER AND THEN RUN IT. The recovery owner
                    # only resolves an executed script through a sibling replay, which
                    # is switched off here - but this script's text is in this very
                    # command, so it is offered directly. Nothing else is resolved, so
                    # no recursive replay is reintroduced.
                    helpers[p] = side[p]
            before, cat, err = text, None, None
            # ONE COMMAND CAN DO BOTH, AND THE ORDER IS THE COMMAND'S. A record that
            # edits this file with a program and then appends to it with the shell used
            # to be treated as a file write ALONE, so the edits before the append were
            # dropped in silence. Both halves run, in the order they sit in the command.
            # A COMMAND IS MIXED WHEN ITS OWN PROGRAM ALSO WRITES THIS FILE - decided
            # by the already-proved per-owner extraction, not by where the halves sit:
            # the recovery owner replays the whole command for this file in the order
            # the command itself has, so it needs no ordering hint from here. A record
            # whose program touches only another owner keeps the plain write path.
            mixed = bool(own) and started and any(
                blocks_for(shell_semantics(cmd, m.group(3)), base)[1]
                for m in HD_Q.finditer(cmd)
                if "python" in cmd[:m.start()].split("\n")[-1])
            if mixed:
                # the recovery owner replays the WHOLE command for this file, so it
                # performs the append itself; applying the heredoc again here would
                # add the same text twice
                text = apply_program(n, cmd, base, text, side)
                cat = "applied" if text != before else "read-only"
            elif own:
                for op, body in own:
                    text = (text or "") + body + "\n" if op == ">>" else body + "\n"
                cat, started = "recorded-file-write", True
            elif started and not mixed:
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
