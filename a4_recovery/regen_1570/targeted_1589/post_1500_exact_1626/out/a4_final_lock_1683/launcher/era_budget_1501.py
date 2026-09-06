# -*- coding: utf-8 -*-
"""Produce the round-1 budget receipt under its OWN era closure
(Codex SEQ 1696 epoch rule).

`budget_receipt_1501.py` belongs to the correction era. Run under the FINAL
closure it reaches the later A5 kit, which pins the FINAL A4 lock 63018354 -
the very artifact this whole task exists to reconstruct - so the final closure
cannot produce it without assuming its own result.

The era closure is supplied by the BOUNDARY as read-only per-file binds
(a6_launch_freeze 57604202 and build_a5_exp5_kit f35aa6ad, both named era
generators under inputs/drivers). Nothing is edited and no module is swapped in
process. The receipt is copied into the durable unit so the later chain can bind
it at its historical /tmp name, and it is accepted ONLY if it equals its pin.
"""
import hashlib
import os
import shutil
import subprocess
import sys

RECON = os.environ["RECON_DIR"]
KEEP = os.environ["KEEP_DIR"]                     # durable unit/tmpfiles
PIN = os.environ["BUDGET_PIN"]                    # expected sha256 of the receipt
OUT = "/tmp/a7_budget_receipt_1501.json"

r = subprocess.run([sys.executable, "-B", os.path.join(RECON, "budget_receipt_1501.py")],
                   capture_output=True, text=True,
                   env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
print("budget_receipt_1501.py rc=%s" % r.returncode)
print((r.stdout or "")[-1200:])
if r.returncode:
    print((r.stderr or "")[-1500:])
    sys.exit(1)

if not os.path.isfile(OUT):
    print("generator produced no %s" % OUT)
    sys.exit(2)
got = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
print("receipt sha : %s" % got[:16])
print("required pin: %s" % PIN[:16])
if got != PIN:
    print("REFUSED: receipt does not equal its pin; nothing preserved")
    sys.exit(3)

os.makedirs(KEEP, exist_ok=True)
dst = os.path.join(KEEP, os.path.basename(OUT))
shutil.copyfile(OUT, dst)
if hashlib.sha256(open(dst, "rb").read()).hexdigest() != got:
    print("REFUSED: preserved copy mismatch")
    sys.exit(4)
print("PRESERVED %s" % dst)
