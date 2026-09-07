# -*- coding: utf-8 -*-
"""Run ONE test file against an EXPLICITLY selected reference owner.

argv: <selected owner path> <test file> <label>

a7_g1_build moves its own directory to sys.path[0] on import, so a bare
PYTHONPATH cannot decide which reference owner a later import resolves to.
This loads the SELECTED file by location and installs it in sys.modules FIRST,
then asserts what is actually loaded - before and after the test - by file,
digest and the builder's own code object.
"""
import hashlib, importlib.util, io, json, os, sys

selected, testfile, label = sys.argv[1], sys.argv[2], sys.argv[3]
#: optional 4th argument: the inventory DOCUMENT this owner must be served.
#: owner and document are one pair - a corrected owner given a stale document is
#: correctly refused by the validation owner, which is a mismatch, not a defect.
inventory = sys.argv[4] if len(sys.argv) > 4 else None
spec = importlib.util.spec_from_file_location("a7_reference_inventory", selected)
mod = importlib.util.module_from_spec(spec)
sys.modules["a7_reference_inventory"] = mod
spec.loader.exec_module(mod)
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def observe(when):
    m = sys.modules.get("a7_reference_inventory")
    return {"when": when, "module_file": getattr(m, "__file__", None),
            "inventory_path": getattr(m, "INVENTORY_PATH", None),
            "module_sha256": fsha(m.__file__) if getattr(m, "__file__", None) else None,
            "build_code_filename": m.build.__code__.co_filename,
            "overrides": len(m.SPAN_OVERRIDES)}


if inventory:
    mod.INVENTORY_PATH = inventory
before = observe("before")
assert before["module_file"] == selected, before
import pytest                                                    # noqa: E402
rc = pytest.main(["-q", testfile])
after = observe("after")
io.open(os.environ["REPORT"], "w", encoding="utf-8").write(json.dumps(
    {"label": label, "selected_owner": selected, "selected_sha256": fsha(selected),
     "test_file": testfile, "exit": int(rc),
     "loaded_before": before, "loaded_after": after,
     "owner_held_through_the_test": before == {**after, "when": "before"}},
    indent=1) + "\n")
sys.exit(0)
