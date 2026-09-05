"""Edit-site index over the durable Core transcript: for each named file, every recorded tool call that writes it
(Write tool, Edit tool, shell heredoc create/append, sed -i, and python heredocs that open it for writing or patch() it),
in transcript order. Recognizes, never decides: the replayer then applies each site mechanically."""
import ast, io, json, re, sys

TRANSCRIPT = "/home/faisal/.claude/projects/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200.jsonl"


def py_write_targets(body):
    """Basenames a recorded python heredoc writes: patch("<name>", ...) calls, and any io.open(<expr>, "w") / open(..., "w")
    whose path expression ends in a literal naming the file (p = ... assignments are resolved by their last literal)."""
    out = set()
    try: tree = ast.parse(body)
    except SyntaxError: return out
    last_p = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            lits = [n.value for n in ast.walk(node.value) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            if lits: last_p.setdefault(node.targets[0].id, []).append(lits[-1].rsplit("/", 1)[-1])
        if isinstance(node, ast.Call):
            fn = node.func; name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
            if name == "patch" and node.args and isinstance(node.args[0], ast.Constant): out.add(node.args[0].value)
            if name == "open" and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and "w" in str(node.args[1].value) or name == "write_new":
                a = node.args[0]
                lits = [n.value for n in ast.walk(a) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
                if lits: out.add(lits[-1].rsplit("/", 1)[-1])
                elif isinstance(a, ast.Name) and a.id in last_p: out.update(last_p[a.id])
    return out


def sites(names, lo, hi):
    with io.open(TRANSCRIPT, encoding="utf-8", errors="replace") as fh: lines = fh.readlines()
    hits = {n: [] for n in names}
    for ln in range(lo, hi):
        l = lines[ln-1]
        if not any(n in l for n in names): continue
        try: d = json.loads(l)
        except Exception: continue
        if d.get("type") != "assistant": continue
        for c in (d.get("message") or {}).get("content") or []:
            if c.get("type") != "tool_use": continue
            inp = c["input"]
            if c["name"] in ("Write", "Edit"):
                fp = inp.get("file_path", "")
                for n in names:
                    if fp.endswith("/" + n): hits[n].append((ln, c["name"].lower()))
                continue
            if c["name"] != "Bash": continue
            t = inp.get("command", ""); found = set()
            for m in re.finditer(r"cat >(>?) \"?\$?[A-Za-z_]*/?([^\s\"<]+)\"? <<'", t):
                found.add((m.group(2).rsplit("/", 1)[-1], "append" if m.group(1) else "cat"))
            for m in re.finditer(r"sed -i [^\n|;]*?([A-Za-z0-9_]+\.py)", t):
                found.add((m.group(1), "sed"))
            for body in re.findall(r"<<'(?:PYEOF|PY|EOF)'\n(.*?)\n(?:PYEOF|PY|EOF)(?:\n|$)", t, re.S):
                for n in py_write_targets(body): found.add((n, "py"))
            for n, kind in found:
                if n in hits: hits[n].append((ln, kind))
    return hits


if __name__ == "__main__":
    names = sys.argv[3:]; lo, hi = int(sys.argv[1]), int(sys.argv[2])
    for n, h in sites(names, lo, hi).items():
        print("%-40s %3d sites: %s" % (n, len(h), " ".join("%d%s" % (ln, k[0]) for ln, k in h)))
