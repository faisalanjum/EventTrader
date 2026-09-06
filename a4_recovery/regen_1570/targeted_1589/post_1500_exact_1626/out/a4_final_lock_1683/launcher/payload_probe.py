# -*- coding: utf-8 -*-
"""Boundary positive-control payload: runs INSIDE the private namespace."""
import hashlib, os, sys
IN = "/tmp/a4_targeted_run_1491/targeted_binding.json"   # a bound read-only input
OUT = "/tmp/a4_boundary_out/probe.txt"                    # a bound read-write output
assert os.path.isfile(IN), "bound input not visible inside ns: " + IN
sha = hashlib.sha256(open(IN, "rb").read()).hexdigest()
# prove ro: writing into the ro bind must fail
ro_enforced = False
try:
    open("/tmp/a4_targeted_run_1491/__x", "w").close()
except OSError:
    ro_enforced = True
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("ok")
print("PAYLOAD_OK input_sha=%s ro_enforced=%s" % (sha[:16], ro_enforced))
sys.exit(0)
