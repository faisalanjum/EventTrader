"""THE A3 protected re-audit, version 2 (Codex SEQ 1488 item 2).

a3_reaudit.py (2026-08-21, untouched beside this file) measured the A3
dependency set over the pre-v3 `harness/` tree. The A4 lifecycle now imports
`harness_g1v3/`, so a baseline over `harness/` could neither pass nor guard.
This version keeps v1's derivation - nothing hand-listed: the modules the
verification actually imported (sys.modules filtered to the experiments
tree), the plan's declared protected pins, the plan's declared per-event
inputs - and measures it over the ONE tree the lifecycle imports, importing
the same raw transport, launch manifest, reader, auditor and validator owners
that build_kfields_key imports.

    a3_reaudit_v2.py            -> print the JSON measurement
    a3_reaudit_v2.py <out.json> -> also write the versioned baseline ONCE,
                                   through raw_transport.write_new, with the
                                   enumerated differences from the v1 baseline

build_kfields_key._a3_probe runs THIS file in a clean interpreter; it holds no
copy of the derivation.
"""
import collections
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
     "/scratchpad")
X = S + "/bench_1306/.claude/plans/Drivers/experiments"
TREE = X + "/harness_g1v3"
REPO = os.path.abspath(os.path.join(X, "..", "..", "..", ".."))
V1 = S + "/a4/a3_baseline.json"
sys.path.insert(0, TREE)
sys.path.insert(0, REPO)
T = io.open(S + "/a3_serial_dir.txt", encoding="utf-8").read().strip()

sha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def measure():
    import raw_transport as RT
    import build_launch_manifest as blm
    import a1_reader
    import audit_worker_access
    import validate_benchmark_inventory

    fin = json.load(io.open(T + "/finalization.json", encoding="utf-8"))
    plan = RT.a1_plan()
    problems = RT.a1_primary_evidence_problems(fin, plan, T)

    dep = {}
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if f and os.path.abspath(f).startswith(os.path.abspath(X)):
            dep[os.path.relpath(f, X)] = sha(f)
    dep[os.path.relpath(RT.a1_plan_path(), X)] = sha(RT.a1_plan_path())
    for name, path in blm._protected_pins().items():
        dep[os.path.relpath(path, X)] = sha(path)
    for e in plan.get("events", []):
        p = os.path.join(blm._REPO, e["input_path"])
        dep[os.path.relpath(p, X)] = sha(p)
    imports = collections.OrderedDict()
    for name, mod in (("raw_transport", RT), ("build_launch_manifest", blm),
                      ("a1_reader", a1_reader),
                      ("audit_worker_access", audit_worker_access),
                      ("validate_benchmark_inventory",
                       validate_benchmark_inventory)):
        imports[name] = os.path.relpath(os.path.abspath(mod.__file__), X)
    return collections.OrderedDict([
        ("tree", TREE),
        ("digest", hashlib.sha256(json.dumps(dep, sort_keys=True)
                                  .encode("utf-8")).hexdigest()),
        ("files", dep), ("imports", imports), ("primary_problems", problems)])


def changes_from(prev_files, files):
    """Every difference between the v1 dependency set and this one, by name:
    a v1 `harness/...` file whose twin exists under the current tree is
    compared by bytes; everything else is added or removed."""
    tree = os.path.basename(TREE)
    out, twins = [], set()
    for name, old in prev_files.items():
        parts = name.split("/")
        twin = name
        if parts[0] != tree and os.path.isfile(os.path.join(X, tree, *parts[1:])):
            twin = "/".join([tree] + parts[1:])
        twins.add(twin)
        if twin in files:
            if twin != name or files[twin] != old:
                out.append(collections.OrderedDict([
                    ("v1", name), ("v2", twin),
                    ("status", "renamed_same_bytes" if files[twin] == old
                     else "changed"),
                    ("v1_sha256", old), ("v2_sha256", files[twin])]))
        else:
            out.append(collections.OrderedDict([
                ("v1", name), ("v2", None), ("status", "removed"),
                ("v1_sha256", old), ("v2_sha256", None)]))
    for name, new in files.items():
        if name not in twins and name not in prev_files:
            out.append(collections.OrderedDict([
                ("v1", None), ("v2", name), ("status", "added"),
                ("v1_sha256", None), ("v2_sha256", new)]))
    return out


def main():
    doc = measure()
    if len(sys.argv) > 1:
        import raw_transport as RT
        prev = json.load(io.open(V1, encoding="utf-8"))
        doc = collections.OrderedDict(
            [("schema", "a4-a3-dependency-baseline-v2"),
             ("measured_from", TREE), ("owner", os.path.abspath(__file__))]
            + list(doc.items())
            + [("previous", collections.OrderedDict([
                ("path", V1), ("sha256", sha(V1)), ("digest", prev["digest"]),
                ("changes", changes_from(prev["files"], doc["files"]))]))])
        RT.write_new(sys.argv[1], json.dumps(doc, indent=1, sort_keys=True))
    sys.stdout.write(json.dumps(doc))


if __name__ == "__main__":
    main()
