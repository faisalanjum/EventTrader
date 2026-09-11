# -*- coding: utf-8 -*-
"""READ-ONLY diagnosis: why the preserved RETRY closeout does not replay.

Captures what the original owner would write and prints the exact difference
against the stored bytes. Writes nothing, calls nothing.
"""
import difflib
import io
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, os.path.join(A7, "unit_2009/owner"))
import a4_review_composite as R                                    # noqa: E402

CL, K, RT = R.CL, R.K, R.RT
captured = {}


def cap(path, text):
    captured[path] = text


def noraw(*args, **kwargs):
    raise ValueError("no raw write in a diagnosis")


out = {}
with R.old_scope():
    ctx = CL._ctx()
    for name, base in (("primary", R.OLD_RUN),
                       ("retry", os.path.join(R.OLD_RUN, "retry"))):
        captured.clear()
        try:
            with R._using(RT, write_new=cap, save_raw=noraw):
                R.OLD._finalize(ctx, base, R.OLD_PKG)
            err = None
        except Exception as exc:                       # noqa: BLE001
            err = "%s: %s" % (type(exc).__name__, exc)
        rows = []
        for path, text in sorted(captured.items()):
            stored = (io.open(path, encoding="utf-8").read()
                      if os.path.isfile(path) else None)
            rows.append({"path": path, "same": stored == text,
                         "stored_bytes": None if stored is None else len(stored),
                         "replayed_bytes": len(text),
                         "diff": None if stored == text else list(
                             difflib.unified_diff(
                                 (stored or "").splitlines(), text.splitlines(),
                                 "stored", "replayed", n=1))[:60]})
        out[name] = {"error": err, "written": rows}
print(json.dumps(out, indent=1, default=str))
