#!/usr/bin/env python3
"""Importing ANY active harness module must do nothing at all.

WHY, AND WHY IT IS THE WHOLE INVENTORY. `make_g_ledger` once ended in a bare
`main()`, so merely importing it REWROTE the live ledger and printed. That was
fixed — and the class was not swept: `rev4_build_patch` still ran `git rev-parse`
AND `os.chdir` at module level, and `rev4_coverage_check` ran a subprocess and
then called `main(sys.argv[1])`, crashing on import. Naming two generators by
hand is what let two siblings keep the same defect, so the inventory is DERIVED.

WHAT COUNTS AS A SIDE EFFECT (not just printing):
  * creating a process   — subprocess.Popen / os.exec* / os.posix_spawn / system / fork
  * changing directory   — os.chdir moves the CALLER'S cwd, silently
  * writing ANY file     — not merely the module's own named artifact; the old
                           check compared one output file's bytes, so a generator
                           writing somewhere else passed
  * TOUCHING THE FILESYSTEM ANY OTHER WAY — mkdir, rename, remove, rmdir, link,
                           symlink, truncate, and the shutil copy/move/rmtree
                           family. Watching `open` alone left a hole the size of
                           the whole mutation vocabulary: a module could create a
                           directory, rename an artifact out of the way, or delete
                           one, and the probe reported it inert.
  * writing to stdout or stderr, or failing to import at all

Bytecode caching (`__pycache__`) is the INTERPRETER writing, not the module, so
probes run with `-B` and ignore those paths — otherwise every module looks dirty
and the check gets switched off as noisy.

Run: venv/bin/python harness/import_inertness.py
"""
import ast
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCORERS = os.path.join(_HERE, "scorers")

# Generators/checkers that are ACTIVE by contract even when no test imports them
# (they are invoked as subprocesses). Declared, because "invoked by a subprocess"
# is not visible to an import walk — and then UNIONED with the derived closure,
# never used as the whole list.
DECLARED = ("make_g_ledger", "make_pin_inventory", "isolated_manifest_check",
            "rev4_build_patch", "rev4_coverage_check")

# LOADED BY FILENAME, AND ONLY PARTIALLY. `rev4_build_patch` reads
# `rev3_build.py` and execs the slice BEFORE its build tail — so `import
# rev3_build` would run code no caller ever runs, and fail on paths meant to be
# resolved from the repository root. The honest probe is the load that really
# happens, and its owner's loader is the single authority on how much of the file
# executes. The SET of such modules is derived (a string naming a sibling `.py`);
# only the load STATEMENT is declared, because no walk can infer it. The test
# suite asserts the two agree, so a new one cannot be quietly forgotten.
DYNAMIC = {
    "rev3_build": "import rev4_build_patch; rev4_build_patch.load_tables()",
}

_PROBE = r'''
import sys, json, os
sys.dont_write_bytecode = True
# THE FILESYSTEM-MUTATION VOCABULARY, named once. Anything that creates, moves,
# links, truncates or destroys a path belongs here — `open` in write mode was
# only the most obvious member.
MUTATE = ("os.mkdir", "os.rename", "os.remove", "os.rmdir", "os.link",
          "os.symlink", "os.truncate", "os.replace", "shutil.copyfile",
          "shutil.copymode", "shutil.copystat", "shutil.copytree",
          "shutil.move", "shutil.rmtree", "shutil.unpack_archive",
          "tempfile.mkstemp", "tempfile.mkdtemp")
seen = {"spawn": [], "chdir": [], "write": [], "fs": []}
def hook(event, args):
    if event in ("subprocess.Popen", "os.exec", "os.posix_spawn", "os.system",
                 "os.fork"):
        seen["spawn"].append(event)
    elif event == "os.chdir":
        seen["chdir"].append(str(args[0])[:60])
    elif event in MUTATE:
        # `-B` already stops bytecode writing; the filter stays because an
        # interpreter that ignores it must not turn every module DIRTY.
        target = " ".join(str(a)[-60:] for a in args if a is not None)
        if "__pycache__" not in target:
            seen["fs"].append(f"{event}({target[:70]})")
    elif event == "open":
        path, mode, flags = (list(args) + [None, None])[:3]
        if not isinstance(path, str) or "__pycache__" in path:
            return
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                  (isinstance(flags, int)
                   and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)))
        if writing:
            seen["write"].append(path[-70:])
sys.addaudithook(hook)
try:
    LOADSTATEMENT
    err = None
except BaseException as exc:
    err = f"{type(exc).__name__}: {exc}"[:100]
sys.stderr.write("RESULT:" + json.dumps({"seen": seen, "err": err}))
'''


def load_statement(module):
    """How this module's code actually comes to run."""
    return DYNAMIC.get(module, f"import {module}")


def _local_imports(path, files=()):
    """Modules this file pulls in — by `import`, AND by naming a sibling `.py`
    file in a string.

    THE HOLE THIS CLOSES: `rev4_build_patch.load_tables` reads `rev3_build.py`
    and `exec`s it. There is no import statement to find, so the walk could not
    see it, and `rev3_build` — a module whose code really does run inside a
    generator — was absent from the inventory and never probed for inertness.
    Loading by filename is still loading. The trigger is a string ending in
    `.py` whose stem is a real harness module, so nothing is hand-listed and any
    future exec/importlib/runpy sibling is caught the same way.
    """
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except (SyntaxError, OSError):
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module.split(".")[0])
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) \
                and n.value.endswith(".py"):
            stem = os.path.basename(n.value)[:-3]
            if stem in files:
                out.add(stem)
    return out


def _module_files():
    """name -> file, for every harness module (top level and scorers/)."""
    found = {}
    for root in (_HERE, _SCORERS):
        if not os.path.isdir(root):
            continue
        for f in sorted(os.listdir(root)):
            if f.endswith(".py") and f != "__init__.py":
                found.setdefault(f[:-3], os.path.join(root, f))
    assert found, "no harness modules found — the scan has no premise"
    return found


def active_inventory():
    """DECLARED, unioned with the import closure of the harness's own tests.

    The first version returned only the closure, so the DECLARED seeds themselves
    were never checked — which is precisely how `rev4_coverage_check` stayed
    unexamined while being named as a target.
    """
    files = _module_files()
    active = {m for m in DECLARED if m in files}
    stack = [files[m] for m in active]
    stack += [os.path.join(_HERE, f) for f in sorted(os.listdir(_HERE))
              if f.startswith("test_") and f.endswith(".py")]
    while stack:
        for name in _local_imports(stack.pop(), files):
            if name in files and name not in active and not name.startswith("test_"):
                active.add(name)
                stack.append(files[name])
    out = sorted(active)
    assert out, "the active inventory is empty — the derivation is broken"
    return out


def probe(module):
    """[] when LOADING `module` is inert, else the side effects observed."""
    files = _module_files()
    cwd = os.path.dirname(files[module])
    r = subprocess.run([sys.executable, "-B", "-c",
                        _PROBE.replace("LOADSTATEMENT", load_statement(module))],
                       capture_output=True, text=True, cwd=cwd)
    pre, _, payload = r.stderr.partition("RESULT:")
    if not payload:
        return [f"the probe did not report (module crashed the interpreter): "
                f"{r.stderr.strip()[-120:]}"]
    d = json.loads(payload)
    seen, issues = d["seen"], []
    if seen["spawn"]:
        issues.append(f"created a process: {sorted(set(seen['spawn']))}")
    if seen["chdir"]:
        issues.append(f"changed directory: {seen['chdir']}")
    if seen["write"]:
        issues.append(f"wrote file(s): {seen['write'][:3]}")
    if seen["fs"]:
        issues.append(f"changed the filesystem: {seen['fs'][:3]}")
    if r.stdout.strip():
        issues.append(f"printed to stdout: {r.stdout.strip()[:60]!r}")
    if pre.strip():
        issues.append(f"printed to stderr: {pre.strip()[:60]!r}")
    if d["err"]:
        issues.append(f"failed to import: {d['err']}")
    return issues


def main():
    inv = active_inventory()
    dirty = {}
    for m in inv:
        issues = probe(m)
        print(f"  {'DIRTY  ' if issues else 'inert  '}{m}"
              + ("" if not issues else "  " + "; ".join(issues)[:110]))
        if issues:
            dirty[m] = issues
    print(f"\n  active modules: {len(inv)}   not inert: {len(dirty)}")
    return 1 if dirty else 0


if __name__ == "__main__":
    raise SystemExit(main())
