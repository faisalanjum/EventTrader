# -*- coding: utf-8 -*-
"""The current callable-file closure and what changed since checkpoint_1890.

Two questions, answered from the files themselves:

  WHAT THE CURRENT ENTRYPOINTS NEED - every module reachable by import from
  the source/key/signer/producer/grader entrypoints, plus the runtime files
  those modules OPEN by name, which imports alone never mention.

  WHAT ACTUALLY CHANGED - that closure compared byte-for-byte against the
  same-named file already published by checkpoint_1890. Anything identical is
  already served by the existing resolver and is NOT recopied.
"""
import ast, collections, hashlib, io, json, os, re, sys

R = "/home/faisal/EventMarketDB-driver-recovery"
A = R + "/a7_recovery"
CUR = A + "/unit_1939/view/tree/harness_g1v3"      # the verified current view
PUB = A + "/unit_1881/view/tree/harness_g1v3"      # what 1890 published from
ENTRIES = ("build_a5_exp5_kit", "build_kfields_key", "build_kfields_final",
           "a6_launch_freeze", "a7_prepared_run", "a7_g1_build",
           "a7_g23_build", "a7_g23_run", "a7_g1_complete_v2",
           "a7_reference_inventory", "a7_key_correction",
           "build_launch_manifest", "raw_transport", "audit_worker_access")


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


mods = {n[:-3]: os.path.join(CUR, n) for n in os.listdir(CUR)
        if n.endswith(".py")}
imports, opened = {}, collections.defaultdict(set)
for name, path in mods.items():
    src = io.open(path, encoding="utf-8").read()
    tree = ast.parse(src, name)
    got = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            got |= {a.name for a in node.names if a.name in mods}
        elif isinstance(node, ast.ImportFrom) and node.module in mods:
            got.add(node.module)
    imports[name] = got
    # the NON-.py files this module names as a literal - the assets an import
    # graph cannot see. Only names that actually exist beside it are kept.
    for lit in re.findall(r"[\"']([A-Za-z0-9_./-]+\.(?:json|js|md|txt|mjs))[\"']",
                          src):
        cand = os.path.join(CUR, lit)
        if os.path.isfile(cand):
            opened[name].add(lit)

seen = set()
stack = [e for e in ENTRIES if e in mods]
missing_entries = [e for e in ENTRIES if e not in mods]
while stack:
    n = stack.pop()
    if n in seen:
        continue
    seen.add(n)
    stack.extend(imports.get(n, ()))

assets = sorted({a for n in seen for a in opened.get(n, ())})
closure = sorted(n + ".py" for n in seen)
res = collections.OrderedDict()
res["entrypoints"] = list(ENTRIES)
res["entrypoints_absent"] = missing_entries
res["closure_modules"] = len(closure)
res["closure_assets"] = len(assets)

rows = collections.OrderedDict()
for rel in closure + assets:
    cur = os.path.join(CUR, rel)
    pub = os.path.join(PUB, rel)
    cs = sha(cur)
    ps = sha(pub) if os.path.isfile(pub) else None
    rows[rel] = {"current": cs, "published": ps,
                 "state": ("new" if ps is None
                           else ("changed" if ps != cs else "unchanged")),
                 "bytes": os.path.getsize(cur)}
res["files"] = rows
for state in ("new", "changed", "unchanged"):
    res[state] = sorted(k for k, v in rows.items() if v["state"] == state)
    res[state + "_count"] = len(res[state])
res["bytes_to_stage"] = sum(v["bytes"] for v in rows.values()
                            if v["state"] != "unchanged")
out = os.path.join(A, "unit_1943", "CLOSURE_1943.json")
io.open(out, "w", encoding="utf-8").write(
    json.dumps(res, indent=2, default=str) + "\n")
print("  entrypoints %d (absent %s)" % (len(ENTRIES), missing_entries))
print("  closure: %d modules + %d assets" % (len(closure), len(assets)))
print("  new %d   changed %d   unchanged %d   bytes to stage %d"
      % (res["new_count"], res["changed_count"], res["unchanged_count"],
         res["bytes_to_stage"]))
print("  NEW:     %s" % res["new"][:6])
print("  CHANGED: %s" % res["changed"][:8])
