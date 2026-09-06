# -*- coding: utf-8 -*-
"""Check every owner the saved A4 path consumes, together (Codex SEQ 1729).

One old module discovered per expensive rerun is the failure mode this avoids. Each
saved operation is read for the module attributes it actually uses, and each bench
module is read for what it actually defines - both from the syntax tree, so nothing is
imported and nothing runs. What comes back is the complete list of attributes the path
needs and the bench cannot supply.
"""
import ast, io, os, sys

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = (UNIT + "/bench/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3")
REC = UNIT + "/reconstruct"
EXTRA = [UNIT + "/launcher/recon_round1.py"]


def defined(path):
    """Every top-level name a module binds."""
    out = set()
    try:
        tree = ast.parse(io.open(path, encoding="utf-8").read())
    except Exception:
        return out
    for st in tree.body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(st.name)
        elif isinstance(st, ast.Assign):
            for t in st.targets:
                if isinstance(t, ast.Name):
                    out.add(t.id)
        elif isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
            out.add(st.target.id)
        elif isinstance(st, (ast.Import, ast.ImportFrom)):
            for a in st.names:
                out.add(a.asname or a.name.split(".")[0])
    return out


def used(path):
    """{module: {attribute}} for every module this script imports by alias."""
    src = io.open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    alias = {}
    for st in ast.walk(tree):
        if isinstance(st, ast.Import):
            for a in st.names:
                if os.path.isfile(H + "/" + a.name + ".py"):
                    alias[a.asname or a.name] = a.name
    need = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and n.value.id in alias:
            need.setdefault(alias[n.value.id], set()).add(n.attr)
    return need


scripts = EXTRA + sorted(os.path.join(REC, f) for f in os.listdir(REC) if f.endswith(".py"))
have, missing = {}, []
for s in scripts:
    for mod, attrs in used(s).items():
        have.setdefault(mod, defined(H + "/" + mod + ".py"))
        for a in sorted(attrs):
            # a module dunder is supplied by the interpreter, not by the source
            if a.startswith("__") or a in have[mod]:
                continue
            if True:
                missing.append((os.path.basename(s), mod, a))

print("saved operations checked: %d" % len(scripts))
print("owner attributes the bench cannot supply: %d" % len(missing))
seen = set()
for s, mod, a in missing:
    if (mod, a) in seen:
        continue
    seen.add((mod, a))
    print("   %-28s %-34s %s" % (s, mod, a))
sys.exit(1 if missing else 0)
