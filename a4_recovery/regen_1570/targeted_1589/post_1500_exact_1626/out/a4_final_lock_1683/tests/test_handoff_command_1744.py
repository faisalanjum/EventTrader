# -*- coding: utf-8 -*-
"""The commands RESTART.md hands over must actually work when copied (Codex SEQ 1744).

The check command was emitted with doubled line continuations, so a copy of it lost every
environment setting and silently selected the whole pipeline. This runs the exact lines
from the generated file with the real runner replaced by a stub that reports what it was
given - nothing is built and no boundary is entered - and it also runs the manifest-only
check, which must exit nonzero when a row does not hash.
"""
import io
import os
import re
import subprocess
import sys
import tempfile

UNIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESTART = UNIT + "/FREEZE_1743/RESTART.md"
passed = failed = 0


def check(name, good, why=""):
    global passed, failed
    print("%-4s %-56s %s" % ("ok" if good else "BAD", name, why))
    passed += bool(good)
    failed += (not good)


text = io.open(RESTART, encoding="utf-8").read()
block = re.search(r"\n(    A4_ROUND=3 A4_STEPS=verify_checkpoint.*?run_a4\.sh)\n", text, re.S)
check("the check command is in the handoff", bool(block))
cmd = "\n".join(l[4:] for l in block.group(1).splitlines()) if block else ""
check("it is not doubly escaped", "\\\\" not in cmd, repr(cmd.splitlines()[0][-30:]))

stub = ("bash() { printf 'STEPS=%s ROUND=%s A6=%s\\n' "
        "\"${A4_STEPS-unset}\" \"${A4_ROUND-unset}\" \"${A4_A6-unset}\"; }\n")
r = subprocess.run(["bash", "-c", stub + cmd], capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, cwd=UNIT, timeout=300)
out = (r.stdout or "").strip()
check("a copy of it passes the stage to the runner", "STEPS=verify_checkpoint" in out,
      out.splitlines()[:1])
check("a copy of it passes the round", "ROUND=3" in out, out.splitlines()[:1])
check("a copy of it passes the ledger owner",
      "A6=f0d7b8281ae13bc8184be34253bf0236132c1900f60db574d005ae018880d4de" in out,
      out.splitlines()[:1])
check("no setting reaches the runner unset", "unset" not in out, out.splitlines()[:1])

mblock = re.search(r"\n(    /home/faisal/EventMarketDB/venv/bin/python3 -B - <<'EOF'\n.*?    EOF)\n",
                   text, re.S)
check("the write-nothing manifest check is in the handoff", bool(mblock))
mcmd = "\n".join(l[4:] for l in mblock.group(1).splitlines()) if mblock else ""

# The command's SEMANTICS are what this proves, on a manifest built here: a correct one
# exits zero, a mutated row exits nonzero. It does not depend on the live manifest, which
# this very freeze has not written yet when the tests run.
R = "/home/faisal/EventMarketDB-driver-recovery"
work = tempfile.mkdtemp(prefix="man_", dir=UNIT)
import hashlib
sample = os.path.join(work, "a.txt")
io.open(sample, "w").write("one\n")
good = os.path.join(work, "GOOD.sha256")
h = hashlib.sha256(io.open(sample, "rb").read()).hexdigest()
io.open(good, "w").write("path\tsha256\tbytes\n%s\t%s\t%d\n"
                         % (os.path.relpath(sample, R), h, os.path.getsize(sample)))
bad_man = os.path.join(work, "BAD.sha256")
io.open(bad_man, "w").write("path\tsha256\tbytes\n%s\t%s\t%d\n"
                            % (os.path.relpath(sample, R), "0" * 64, os.path.getsize(sample)))
for label, man, want_rc, want_text in (("valid control: a manifest that verifies", good, 0,
                                        "mismatched 0"),
                                       ("a mutated row makes it exit nonzero", bad_man, 1,
                                        "mismatched 1")):
    cmd = re.sub(r"man = '.*?'", "man = %r" % os.path.relpath(man, R), mcmd)
    r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, cwd=UNIT, timeout=600)
    check(label, (r.returncode != 0) == bool(want_rc) and want_text in (r.stdout or ""),
          (r.stdout or "").strip().splitlines()[-1:] + ["rc=%d" % r.returncode])

import shutil
shutil.rmtree(work, ignore_errors=True)
print("%d passed / %d failed" % (passed, failed))
sys.exit(1 if failed else 0)
