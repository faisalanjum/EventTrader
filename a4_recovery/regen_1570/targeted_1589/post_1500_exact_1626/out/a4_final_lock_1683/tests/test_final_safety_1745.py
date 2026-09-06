# -*- coding: utf-8 -*-
"""The two safety defects of Codex SEQ 1745, proved and then closed.

A - the short-test cache could not see a change in what a test covered. The failing
control is the PRESERVED freeze source that carried it: its key hashed the test file and
nothing else, because the path expressions those tests use cannot be folded. The live
owner no longer has that cache at all.

B - the restoration step only PRINTED two hashes, so a wrong one still published. The
generated command is now exercised end to end in a disposable directory, with its three
subject lines pointed at throwaway files: the real original and the real compressed
evidence are never read, written or moved by this test.
"""
import ast
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD = UNIT + "/superseded/cache_defect_1745/freeze_1743.with_cache.py"
NEW = UNIT + "/tests/freeze_1743.py"
RESTART = UNIT + "/FREEZE_1743/RESTART.md"
passed = failed = 0


def check(name, good, why=""):
    global passed, failed
    print("%-4s %-58s %s" % ("ok" if good else "BAD", name, why))
    passed += bool(good)
    failed += (not good)


def load(path):
    mod = types.ModuleType(os.path.basename(path))
    mod.__file__ = path
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    defs = [n for n in tree.body
            if isinstance(n, (ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef))]
    m = ast.Module(body=defs, type_ignores=[])
    ast.fix_missing_locations(m)
    exec(compile(m, path, "exec"), mod.__dict__)
    return mod


# --- A: the cache defect, on the source that carried it -------------------------
old = load(OLD)
for t in ("test_boundary_checks_1743.py", "test_handoff_command_1744.py"):
    p = UNIT + "/tests/" + t
    check("the old cache saw no dependency of %s" % t, old.deps_of(p)[0] == [],
          "named files: %r" % (old.deps_of(p)[0],))
    check("so its key was the test file alone (%s)" % t,
          old.bound_identity(p) == hashlib.sha256(old.sha(p).encode()).hexdigest())
src = io.open(NEW, encoding="utf-8").read()
check("the live freeze has no such cache",
      "bound_identity" not in src and "reused, source unchanged" not in src)
check("and it runs the short checks once, unconditionally",
      "There is no cache" in src and "prev" not in src.split("def run_short_tests")[1][:800])

# --- B: the restoration command, in a disposable directory ----------------------
text = io.open(RESTART, encoding="utf-8").read()
block = re.search(r"\n(    T=/home/faisal.*?\n    fi)\n", text, re.S)
check("the restoration command is in the handoff", bool(block))
cmd = "\n".join(l[4:] for l in block.group(1).splitlines()) if block else ""
check("it compares the decompressed bytes, not just prints them",
      '= "$WANT" ]' in cmd and cmd.count('sha256sum') >= 3, "%d sha256sum uses" % cmd.count("sha256sum"))
check("it does not use a fixed temporary name", ".restored" not in cmd and "mktemp" in cmd)


def run(work, content=b"the original bytes\n", gz_ok=True, gz_content=None, pre=None,
        stub=""):
    """The generated command with its three subject lines pointed at throwaway files."""
    d = os.path.join(work, "sub", "dir")
    t = os.path.join(d, "original.jsonl")
    gz = os.path.join(work, "copy.gz")
    want = hashlib.sha256(content).hexdigest()
    import gzip
    with gzip.open(gz, "wb") as fh:
        fh.write(gz_content if gz_content is not None else content)
    if not gz_ok:
        io.open(gz, "wb").write(b"not a gzip at all")
    if pre is not None:
        os.makedirs(d, exist_ok=True)
        io.open(t, "wb").write(pre)
    body = re.sub(r"^T=.*$", "T=" + t, cmd, count=1, flags=re.M)
    body = re.sub(r"^GZ=.*$", "GZ=" + gz, body, count=1, flags=re.M)
    body = re.sub(r"^WANT=.*$", "WANT=" + want, body, count=1, flags=re.M)
    r = subprocess.run(["bash", "-c", stub + body], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300)
    got = io.open(t, "rb").read() if os.path.isfile(t) else None
    return r, t, got, content


work = tempfile.mkdtemp(prefix="restore_")
r, t, got, want = run(work)
check("valid control: an absent original is restored, parent made",
      r.returncode == 0 and got == want and "restored" in r.stdout,
      r.stdout.strip().splitlines()[-1:])
shutil.rmtree(work, ignore_errors=True)

work = tempfile.mkdtemp(prefix="restore_")
r, t, got, want = run(work, pre=b"the original bytes\n")
check("an existing correct original is verified and left alone",
      r.returncode == 0 and got == want and "left unchanged" in r.stdout,
      r.stdout.strip().splitlines()[-1:])
shutil.rmtree(work, ignore_errors=True)

work = tempfile.mkdtemp(prefix="restore_")
r, t, got, want = run(work, pre=b"something else\n")
check("a differing existing original is REFUSED and left unchanged",
      r.returncode != 0 and got == b"something else\n",
      (r.stderr or "").strip().splitlines()[-1:])
shutil.rmtree(work, ignore_errors=True)

work = tempfile.mkdtemp(prefix="restore_")
r, t, got, want = run(work, gz_ok=False)
check("a bad compressed input never creates the target",
      r.returncode != 0 and got is None, (r.stderr or "").strip().splitlines()[-1:])
check("and it leaves no temporary behind",
      not [f for f in os.listdir(os.path.dirname(t)) if f.startswith(".accepted_prefix")]
      if os.path.isdir(os.path.dirname(t)) else True)
shutil.rmtree(work, ignore_errors=True)

work = tempfile.mkdtemp(prefix="restore_")
r, t, got, want = run(work, gz_content=b"different bytes entirely\n")
check("a wrong decompressed hash never creates the target",
      r.returncode != 0 and got is None, (r.stderr or "").strip().splitlines()[-1:])
shutil.rmtree(work, ignore_errors=True)

work = tempfile.mkdtemp(prefix="restore_")
r, t, got, want = run(work, stub="mv() { :; }\n")
check("a publication that does not take place is REFUSED, not reported as success",
      r.returncode != 0 and got is None, (r.stderr or "").strip().splitlines()[-1:])
shutil.rmtree(work, ignore_errors=True)

print("%d passed / %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
