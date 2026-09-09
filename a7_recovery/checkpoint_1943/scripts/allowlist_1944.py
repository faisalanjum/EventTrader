# -*- coding: utf-8 -*-
"""The COMPLETE allowlist for checkpoint_1943 (Codex SEQ 1944 item 1).

Three kinds of dependency, all derived from the files themselves:

  IMPORTED MODULE FILES - importlib reads the .py itself, which the previous
  check's builtins/io.open gate never saw, so an "import ok" row proved
  nothing about Git. Every module in the entrypoint closure is required.

  SIBLING FILES AN OWNER OPENS BESIDE ITSELF - `os.path.join(_HERE, X)` where
  X is a literal or a module-level constant. These are invisible to an import
  graph and a same-named file in another directory is not a substitute.

  THE LOCK / CANDIDATE / SIGNER OWNERS - a harness-only import scan cannot
  reach them, so they are taken from the unit's own lock_owners directory.

Plus the changed focused tests, which are not the published unchanged ones.
"""
import ast, collections, io, json, os, sys

R = "/home/faisal/EventMarketDB-driver-recovery"
A = R + "/a7_recovery"
CUR = A + "/unit_1939/view/tree/harness_g1v3"
LOCKS = A + "/unit_1939/out_a/lock_owners"
ENTRIES = ("build_a5_exp5_kit", "build_kfields_key", "build_kfields_final",
           "a6_launch_freeze", "a7_prepared_run", "a7_g1_build",
           "a7_g23_build", "a7_g23_run", "a7_g1_complete_v2",
           "a7_reference_inventory", "a7_key_correction",
           "build_launch_manifest", "raw_transport", "audit_worker_access",
           "a1_reader", "kf_lint", "build_exp5_contract",
           "build_inventory_review", "build_kfields_hard_review",
           "validate_benchmark_inventory", "g1_fake_state")
TESTS = ("test_a5_route_1406.py", "test_harness_guards.py",
         "test_a7_closeout_integrity_1482.py")

mods = {n[:-3]: os.path.join(CUR, n) for n in os.listdir(CUR)
        if n.endswith(".py")}
trees = {n: ast.parse(io.open(p, encoding="utf-8").read(), n)
         for n, p in mods.items()}

imports = {}
for name, tree in trees.items():
    got = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            got |= {a.name for a in node.names if a.name in mods}
        elif isinstance(node, ast.ImportFrom) and node.module in mods:
            got.add(node.module)
    imports[name] = got

# THE LOCK/CANDIDATE/SIGNER OWNERS IMPORT HARNESS MODULES TOO, and the
# harness entrypoint list does not reach all of them - build_final_key_candidate
# imports build_kfields_final_targeted, which no harness entrypoint touches.
# Their imports are therefore roots as well (Codex SEQ 1944).
lock_roots = set()
for fn in sorted(os.listdir(LOCKS)):
    if not fn.endswith(".py"):
        continue
    t = ast.parse(io.open(os.path.join(LOCKS, fn), encoding="utf-8").read(), fn)
    for node in ast.walk(t):
        if isinstance(node, ast.Import):
            lock_roots |= {a.name for a in node.names if a.name in mods}
        elif isinstance(node, ast.ImportFrom) and node.module in mods:
            lock_roots.add(node.module)

seen, stack = set(), [e for e in ENTRIES if e in mods] + sorted(lock_roots)
absent = [e for e in ENTRIES if e not in mods]
while stack:
    n = stack.pop()
    if n in seen:
        continue
    seen.add(n)
    stack.extend(imports.get(n, ()))


def const_strings(tree):
    """Module-level NAME = "literal" assignments, for constant sibling names."""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = node.value.value
    return out


siblings = collections.defaultdict(set)
for name in sorted(seen):
    tree = trees[name]
    consts = const_strings(tree)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "join"):
            continue
        args = node.args
        if not args:
            continue
        first = args[0]
        # the anchor must be this module's own directory
        anchor = getattr(first, "id", None) or getattr(first, "attr", None)
        if anchor not in ("_HERE", "HERE", "_DIR", "THIS_DIR"):
            continue
        parts = []
        for a in args[1:]:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                parts.append(a.value)
            elif isinstance(a, ast.Name) and a.id in consts:
                parts.append(consts[a.id])
            else:
                parts = None
                break
        if parts:
            rel = "/".join(parts)
            if os.path.isfile(os.path.join(CUR, rel)):
                siblings[name].add(rel)

res = collections.OrderedDict()
res["entrypoints_absent"] = absent
res["lock_owner_import_roots"] = sorted(lock_roots)
res["closure_modules"] = sorted(n + ".py" for n in seen)
res["sibling_reads"] = {k: sorted(v) for k, v in sorted(siblings.items())}
harness = set(res["closure_modules"])
harness |= {r for v in siblings.values() for r in v}
harness |= set(TESTS)
res["harness_files"] = sorted(harness)
res["lock_owner_files"] = sorted(f for f in os.listdir(LOCKS)
                                 if os.path.isfile(os.path.join(LOCKS, f)))
base = "a7_recovery/unit_1939/view/tree/harness_g1v3/"
lbase = "a7_recovery/unit_1939/out_a/lock_owners/"
res["allowlist"] = ([base + f for f in res["harness_files"]]
                    + [lbase + f for f in res["lock_owner_files"]])
res["allowlist_count"] = len(res["allowlist"])
io.open(os.path.join(A, "unit_1943", "ALLOWLIST_1944.json"), "w",
        encoding="utf-8").write(json.dumps(res, indent=2, default=str) + "\n")
print("  entrypoints absent: %s" % (absent or "none"))
print("  closure modules %d   modules with sibling reads %d"
      % (len(res["closure_modules"]), len(siblings)))
print("  harness files %d   lock owners %d   TOTAL %d"
      % (len(res["harness_files"]), len(res["lock_owner_files"]),
         res["allowlist_count"]))
for k, v in sorted(siblings.items()):
    print("    %-26s -> %s" % (k, sorted(v)))
