# -*- coding: utf-8 -*-
"""Replay the saved patch_1505.py on its own two preimages (Codex SEQ 1737).

The smallest lawful path: the saved patch imports only io and sys and edits exactly two
files, so it is run as itself in a directory seeded with the two proved preimages. No
parser, no engine, no surrounding shell. Both results are asserted at their COMPLETE
hashes before anything is kept, and the seeded directory is separate from every bench.
"""
import hashlib, io, os, shutil, subprocess, sys

A = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = A + "/patch_1505"
WORK = HERE + "/work"
PRE = {"build_kfields_final_targeted.py":
       ("eef9afa4d025966177e909278dd47ca47003e8d6e07e461b19bd8af1060cadaa",
        A + "/proved/ft_round1_eef9afa4.py",
        "1c34db7e1f117f25d312481a97405e6bb10d28184776660b7824be18717a81c1"),
       "a6_launch_freeze.py":
       ("57604202dff9c015973b42bf292dec2786d6763c48947cc075c9876ec4379db8",
        A + "/sources_a6/a6_launch_freeze.py",
        "7081e9a51a94ca43ea8fee281711337fd8674fe19e1501bd2fca7246a5bddd74")}
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()

shutil.rmtree(WORK, ignore_errors=True)
os.makedirs(WORK)
for name, (pre, src, _post) in sorted(PRE.items()):
    if fsha(src) != pre:
        sys.exit("REFUSE: %s preimage is %s, not %s" % (name, fsha(src)[:16], pre[:16]))
    shutil.copyfile(src, os.path.join(WORK, name))
    print("seeded %-34s %s  %d bytes" % (name, pre[:16], os.path.getsize(src)))

r = subprocess.run([sys.executable, "-B", HERE + "/patch_1505.py", WORK],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120)
print("patch rc=%s" % r.returncode)
print((r.stdout or "").strip()[-400:])
if r.returncode:
    print((r.stderr or "")[-600:])
    sys.exit("REFUSE: the saved patch did not run")

bad = []
for name, (_pre, _src, post) in sorted(PRE.items()):
    got = fsha(os.path.join(WORK, name))
    print("%-34s -> %s  %s" % (name, got, "ok" if got == post else "WANT " + post))
    if got != post:
        bad.append(name)
if bad:
    sys.exit("REFUSE: %s did not reach the recorded result" % bad)
shutil.copyfile(WORK + "/a6_launch_freeze.py", A + "/proved/a6_round1_7081e9a5.py")
shutil.copyfile(WORK + "/build_kfields_final_targeted.py", A + "/proved/ft_after_1505_1c34db7e.py")
print("PATCH_1505_OK")
