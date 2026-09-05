"""Mechanical derivation of the hard-review-era files that survive only as recorded command payloads in the durable Core
transcript (Codex SEQ 1608): whole-file Write payloads, patch(name, pairs) calls, per-file rep()/replace blocks and one
shell append, replayed in recorded order with the harness path rebound to a scratch directory. Nothing is retyped."""
import ast, hashlib, io, json, os, re, sys

TRANSCRIPT = os.environ.get("CORE_TRANSCRIPT", "/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl")
HIST_S = "/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad"
HIST_H = HIST_S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sha = lambda b: hashlib.sha256(b).hexdigest()
_lines = None


def record(ln):
    global _lines
    if _lines is None:
        with io.open(TRANSCRIPT, encoding="utf-8", errors="replace") as fh:
            _lines = fh.readlines()
    d = json.loads(_lines[ln - 1])
    calls = [c for c in (d.get("message") or {}).get("content") or [] if c.get("type") == "tool_use"]
    if len(calls) != 1:
        raise ValueError("line %d holds %d tool calls" % (ln, len(calls)))
    return calls[0]["name"], calls[0]["input"], d.get("timestamp")


def heredocs(command, tag="PYEOF"):
    """Every python heredoc body in a recorded Bash command (tags PYEOF, PY or EOF), in order."""
    out = []
    for m in re.finditer(r"<<'(PYEOF|PY|EOF)'\n(.*?)\n\1(?:\n|$)", command, re.S):
        body = m.group(2)
        try: ast.parse(body); out.append(body)
        except SyntaxError: pass
    return out


def step_write(name, inp):
    if os.path.basename(inp["file_path"]) != name:
        raise ValueError("the Write names %s, not %s" % (inp["file_path"], name))
    return inp["content"]


def step_patch(name, text, command):
    pairs = []
    for body in heredocs(command, "PYEOF"):
        for node in ast.walk(ast.parse(body)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "patch" and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == name:
                pairs.extend(ast.literal_eval(node.args[1]))
    if not pairs:
        raise ValueError("no patch() pairs for %s" % name)
    for old, new in pairs:
        if text.count(old) != 1:
            raise ValueError("%s: a pair's old text occurs %d times" % (name, text.count(old)))
        text = text.replace(old, new)
    return text, len(pairs)


def _preamble(body, stmts):
    return [s for s in stmts if isinstance(s, (ast.Import, ast.ImportFrom, ast.FunctionDef)) or (isinstance(s, ast.Assign) and any(isinstance(x, ast.Name) and x.id in ("S", "H") for x in s.targets))]


def _remap(path, scratch):
    if isinstance(path, str):
        for pre in (HIST_H, HIST_S):
            if path.startswith(pre + "/"): return os.path.join(scratch, os.path.basename(path))
    return path


def _exec_block(body, stmts, keep, scratch):
    src = "\n".join(ast.get_source_segment(body, s) for s in _preamble(body, stmts) + keep)
    import builtins, io as _io
    real_open, real_io_open = builtins.open, _io.open
    builtins.open = lambda f, *a, **k: real_open(_remap(f, scratch), *a, **k)
    _io.open = lambda f, *a, **k: real_io_open(_remap(f, scratch), *a, **k)
    try:
        ns = {"__name__": "replay"}; exec(compile(src, "<recorded>", "exec"), ns)
    finally:
        builtins.open, _io.open = real_open, real_io_open


def step_block(name, text, command, scratch):
    """The recorded per-file statement block: the statements from the assignment `p = H + "/<name>"` up to the next
    such assignment, executed after the preamble (imports, defs, S and H) with the paths rebound to the scratch dir."""
    body = heredocs(command)[0].replace(HIST_H, scratch).replace(HIST_S, scratch)
    stmts = ast.parse(body).body
    def names_p(s):
        return isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Name) and any(isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.rsplit("/", 1)[-1].endswith(".py") for n in ast.walk(s.value))
    keep, on = [], None
    for s in stmts:
        if names_p(s):
            seg = ast.get_source_segment(body, s.value) or ""; lits = re.findall(r'"([^"]+)"', seg); on = bool(lits and os.path.basename(lits[-1]) == name)
            if on: keep.append(s)
            continue
        if on and isinstance(s, ast.Expr) and isinstance(s.value, ast.Call) and isinstance(s.value.func, ast.Name) and s.value.func.id == "patch":
            break                                       # the recorded script moved on to another file's patch() call
        if on:
            keep.append(s)
    if not keep:
        raise ValueError("no statement block for %s" % name)
    path = os.path.join(scratch, name)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    cwd = os.getcwd(); os.chdir(scratch)
    try:
        _exec_block(body, stmts, keep, scratch)
    finally:
        os.chdir(cwd)
    return io.open(path, encoding="utf-8", newline="").read(), len(keep)


def step_sblock(name, src_name, command, scratch):
    """A recorded script block that derives <name> FROM <src_name>: the statements from the first one naming the source
    file up to and including the one writing the derived file, executed with S rebound to the scratch dir (the source
    file must already be there from its own chain)."""
    body = heredocs(command)[0].replace(HIST_H, scratch).replace(HIST_S, scratch)
    stmts = ast.parse(body).body; keep = []; on = False
    for s in stmts:
        seg = ast.get_source_segment(body, s) or ""
        if not on and ('"/%s"' % src_name) in seg: on = True
        if on: keep.append(s)
        if on and ('"/%s"' % name) in seg and ("w" in seg.split('"/%s"' % name)[1][:12]): break
    if not keep:
        raise ValueError("no derivation block for %s from %s" % (name, src_name))
    _exec_block(body, stmts, keep, scratch)
    return io.open(os.path.join(scratch, name), encoding="utf-8", newline="").read(), len(keep)


def step_cat(name, command):
    m = re.search(r'cat > "?[^\s"<]*/%s"? <<\'(PYEOF|PY|EOF)\'\n(.*?)\n\1\n' % re.escape(name), command, re.S)
    if not m:
        raise ValueError("no heredoc creating %s" % name)
    return m.group(2) + "\n"


def step_sed(name, text, command, scratch):
    """The recorded `sed -i ... <file>` line(s) naming this file, run by sed itself on the scratch copy."""
    import subprocess
    path = os.path.join(scratch, name); io.open(path, "w", encoding="utf-8", newline="").write(text); n = 0
    for line in command.splitlines():
        if "sed -i" in line and name in line:
            cmd = re.sub(r"[^\s'\"]*/%s" % re.escape(name), path, line.replace("$H/" + name, path).replace("$S/" + name, path))
            subprocess.run(["bash", "-c", cmd], check=True, cwd=scratch); n += 1
    if not n:
        raise ValueError("no sed line for %s" % name)
    return io.open(path, encoding="utf-8", newline="").read(), n


def step_edit(name, text, inp):
    if os.path.basename(inp["file_path"]) != name:
        raise ValueError("the Edit names %s, not %s" % (inp["file_path"], name))
    old, new = inp["old_string"], inp["new_string"]
    if inp.get("replace_all"):
        if text.count(old) < 1: raise ValueError("%s: edit text absent" % name)
        return text.replace(old, new), text.count(old)
    if text.count(old) != 1:
        raise ValueError("%s: the Edit's old text occurs %d times" % (name, text.count(old)))
    return text.replace(old, new), 1


def step_append(name, text, command):
    m = re.search(r"cat >> \"?\$[SH]/%s\"? <<'(EOF|PYEOF)'\n(.*?)\n\1\n" % re.escape(name), command, re.S)
    if not m:
        raise ValueError("no append for %s" % name)
    return text + m.group(2) + "\n"


def derive(name, steps, scratch, base=None):
    text = io.open(base, encoding="utf-8", newline="").read() if base else None
    log = [("base", "-", "-", "-", sha(text.encode("utf-8")) if text else "-", len(text.encode("utf-8")) if text else 0)]
    for ln, kind in steps:
        tool, inp, ts = record(ln); n = 1
        if os.environ.get("DERIVE_TRACE"): print("trace\t%s\tat\t%s\t%s" % (name, ln, kind))
        if kind == "write":
            text = step_write(name, inp)
        elif kind == "patch":
            text, n = step_patch(name, text, inp["command"])
        elif kind == "block":
            text, n = step_block(name, text, inp["command"], scratch)
        elif kind == "append":
            text = step_append(name, text, inp["command"])
        elif kind == "cat":
            text = step_cat(name, inp["command"])
        elif kind == "py":
            try:
                text, n = step_patch(name, text, inp["command"])
            except ValueError as exc:
                if "no patch() pairs" not in str(exc): raise
                text, n = step_block(name, text, inp["command"], scratch)
        elif kind == "sed":
            text, n = step_sed(name, text, inp["command"], scratch)
        elif kind == "edit":
            text, n = step_edit(name, text, inp)
        elif kind.startswith("sblock:"):
            text, n = step_sblock(name, kind.split(":", 1)[1], inp["command"], scratch)
        log.append((kind, ln, ts, n, sha(text.encode("utf-8")), len(text.encode("utf-8"))))
        if os.environ.get("DERIVE_TRACE"): print("trace\t%s\t%s\t%s\t%s\t%s" % (name, kind, ln, log[-1][4][:16], log[-1][5]))
    return text, log


CHAINS = {
    "build_kfields_hard_review_targeted.py": [(82323, "write"), (82394, "patch"), (82632, "patch")],
    "test_a4_targeted_accounting_1492.py": [(82226, "write"), (82343, "block"), (82625, "append"), (82654, "block"), (82744, "block")],
    "test_a4_hard_review_targeted_1492.py": [(82258, "write"), (82369, "block"), (82378, "block"), (82394, "patch"), (82645, "block"), (82654, "block")],
    "a6_launch_freeze.py": [(55324, "cat"), (55327, "append"), (55336, "append"), (55339, "append"), (55345, "block")] + [(ln, "block") for ln in (72690, 73797, 74049, 74070, 74370, 74380, 74645, 74848, 74873, 74935, 74940, 75104, 75112, 75130)] + [(77826, "edit"), (77829, "edit"), (78350, "edit"), (80546, "block"), (82289, "patch")],
    # the budget sources: each file's chain is the recorded index (Codex SEQ 1610 item 1); a file derived FROM its
    # predecessor in one recorded script block is replayed as that block (sblock), and the index must not hold a site
    # the chain omits
    "budget_receipt_1487.py": "INDEX",
    "budget_receipt_1488.py": [(79355, "sblock:budget_receipt_1487.py")],
    "budget_receipt_1492.py": [(82303, "sblock:budget_receipt_1488.py")],
    "budget_receipt_1493.py": [(82632, "sblock:budget_receipt_1492.py")],
}
BASES = {}
KIND = {"write": "write", "cat": "cat", "append": "append", "edit": "edit", "py": "py", "sed": "sed"}


def chain_from_index(name, lo=55000, hi=83247):
    """The recorded write sites of one file from its last whole-file creation before the era end, in order."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import index_edits_1495 as IDX
    s = IDX.sites([name], lo, hi)[name]
    starts = [i for i, (ln, k) in enumerate(s) if k in ("write", "cat")]
    if not starts:
        raise ValueError("%s: no whole-file creation recorded in %d-%d" % (name, lo, hi))
    return [(ln, KIND[k]) for ln, k in s[starts[-1]:]]


EXTRA = os.environ.get("DERIVE_EXTRA", "").split()


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True); scratch = os.path.join(out_dir, "scratch"); os.makedirs(scratch, exist_ok=True)
    rows = []
    for name in EXTRA:
        lo = 1 if name in ("test_kfields_key.py", "build_exp5_contract.py") else 55000
        try:
            CHAINS[name] = chain_from_index(name, lo)
        except Exception as exc:
            print("%s\tNOCHAIN\t%s" % (name, exc))
    for name, steps in list(CHAINS.items()):
        if steps == "INDEX":
            CHAINS[name] = steps = chain_from_index(name, 79000)
        elif name.startswith("budget_receipt_"):
            import index_edits_1495 as IDX
            sites = {ln for ln, k in IDX.sites([name], 79000, 83247)[name]}
            if not sites <= {ln for ln, k in steps}:
                print("%s\tFAILED\tthe index holds sites the chain omits: %s" % (name, sorted(sites))); continue
        try:
            text, log = derive(name, steps, scratch, BASES.get(name))
        except Exception as exc:
            print("%s\tFAILED\t%s" % (name, str(exc)[:200])); continue
        tmp = os.path.join(out_dir, name + ".tmp")
        io.open(tmp, "w", encoding="utf-8", newline="").write(text); os.replace(tmp, os.path.join(out_dir, name))
        io.open(os.path.join(scratch, name), "w", encoding="utf-8", newline="").write(text)
        for r in log:
            rows.append((name,) + r); print("%s\t%s\t%s\t%s\t%s\t%s\t%s" % ((name,) + r))
    with io.open(os.path.join(out_dir, "DERIVATION.tsv"), "w", encoding="utf-8") as fh:
        fh.write("file\tstep\ttranscript_line\ttimestamp\tcount\tsha256\tbytes\n")
        for r in rows: fh.write("\t".join(str(c) for c in r) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
