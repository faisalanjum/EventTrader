# -*- coding: utf-8 -*-
"""Focused test (Codex SEQ 1692): the boundary allows EXACTLY the historical
session-store projects mountpoint (+ children), never its parent, a look-alike
prefix, or other /home paths; /tmp stays allowed. Tests validate()'s escape rule."""
import os, sys, tempfile, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import boundary
PROJ = boundary.PROJECTS_MOUNT
src = tempfile.mkdtemp(prefix="bp_", dir=HERE); open(os.path.join(src, "x"), "w").write("x")
good_sha = boundary.source_sha(src)
def escapes(logical):
    bad = boundary.validate([{"logical": logical, "source": src, "sha": good_sha, "mode": "ro"}])
    return any("escape" in b for b in bad)
cases = [
    ("positive_exact_projects", PROJ, False),
    ("positive_projects_child", PROJ + "/-home-x/sess/workflows", False),
    ("positive_tmp_still_ok", "/tmp/a4_targeted_run_1491", False),
    ("neg_parent_claude", "/home/faisal/.claude", True),
    ("neg_lookalike_prefix", PROJ + "_evil", True),
    ("neg_other_home", "/home/faisal/somethingelse", True),
    ("neg_outside", "/etc/passwd_dir", True),
    ("neg_dotdot_escape", PROJ + "/../../secret", True),
]
OUT, allok = [], True
for name, logical, want_escape in cases:
    got = escapes(logical)
    ok = (got == want_escape)
    allok = allok and ok
    OUT.append("[%s] %-26s logical=%-40s escape=%s (want %s)" % ("ok" if ok else "BAD", name, logical, got, want_escape))
import shutil; shutil.rmtree(src, ignore_errors=True)
print("\n".join(OUT)); print("SUMMARY:", "PROJECTS BOUNDARY OK" if allok else "FAILED")
sys.exit(0 if allok else 1)
