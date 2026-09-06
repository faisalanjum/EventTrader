# -*- coding: utf-8 -*-
"""Replay the round-2 saved patch for THIS owner only (Codex SEQ 1737).

The saved patch edits the correction owner and, after it, an unrelated test file that the
reviewer's boundaries exclude. The owner is seeded alone, so the patch performs exactly
its owner replacements and then stops at the file that is deliberately absent; the owner's
own COMPLETE hash is what decides, and nothing is kept unless it matches.
"""
import hashlib, io, os, shutil, subprocess, sys

A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = A + "/patch_1505"
WORK = HERE + "/work_1505b"
NAME = "build_kfields_final_targeted.py"
PRE = ("25fb1f0c688f61e12daab20aa202cc711fac08dc2fb2b29ddaa25c01809605c6",
       A + "/proved/ft_bind_25fb1f0c.py")
POST = "8f1cba41a27727a211d088a499c9f4c3394dd67e551208d4cb9c670ef90316d9"
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK)
if fsha(PRE[1]) != PRE[0]:
    sys.exit("REFUSE: the preimage is %s" % fsha(PRE[1])[:16])
shutil.copyfile(PRE[1], os.path.join(WORK, NAME))
print("seeded %s %s %d bytes" % (NAME, PRE[0][:16], os.path.getsize(PRE[1])))

r = subprocess.run([sys.executable, "-B", HERE + "/patch_1505b.py", WORK],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
print("patch rc=%s  %s" % (r.returncode, (r.stdout or "").strip()[-200:]))
if r.returncode:
    print("stopped at:", (r.stderr or "").strip().splitlines()[-1][:160])

got = fsha(os.path.join(WORK, NAME))
print("%s -> %s  %s" % (NAME, got, "ok" if got == POST else "WANT " + POST))
if got != POST:
    sys.exit("REFUSE: the owner did not reach its recorded result")
shutil.copyfile(os.path.join(WORK, NAME), A + "/proved/ft_round2_8f1cba41.py")
print("ROUND2_OWNER_OK")
