# -*- coding: utf-8 -*-
"""Restore the exact A6 owner from its two recorded edits (Codex SEQ 1765 item 1).

The base file and the two Edit records are named by Codex. Each record's
old_string/new_string are read literally out of the transcript by tool-use id and
applied forward, each required to match exactly once. Nothing is searched for and
nothing is invented; the published A5 tree's older incidental copy is not touched.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

R = "/home/faisal/EventMarketDB-driver-recovery"
T = R + "/a3_recovery/regen_1541/evidence/transcript/accepted_prefix.jsonl"
BASE = (R + "/a4_recovery/regen_1570/targeted_1589/post_1500_closure_1624"
            "/replay/scratch/a6_launch_freeze.py")
UNIT = os.path.dirname(os.path.abspath(__file__))
OWNERS = UNIT + "/owners"
EV = UNIT + "/evidence"

EDITS = [(88987, "toolu_01J4uYCboGVWXSumzksB27SM"),
         (89026, "toolu_01UPA8cgV9CjExmGpSmvrfSL")]
WANT_BASE = "549be88835adc0744b34f4da1d1c7569c192b489d221912f1511ced6002d7e53"
WANT_OWNER = "2c666040853f611a90f368b9f2dddb1adc8879cb0abfa9fe3923c1eace07118c"
WANT_BASE_BYTES, WANT_OWNER_BYTES = 22146, 24292
CHECKS = []


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


def check(name, got, want):
    ok = got == want
    CHECKS.append((name, ok))
    print("%s %-52s %s%s" % ("ok  " if ok else "BAD ", name, str(got)[:64],
                             "" if ok else "  != %s" % str(want)[:64]), flush=True)


def edit_record(line_no, tool_id):
    """The one Edit tool_use with this id, with its raw line for provenance."""
    raw = subprocess.run(["sed", "-n", "%dp" % line_no, T],
                         capture_output=True, text=True).stdout
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "tool_use" and o.get("id") == tool_id:
                found.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(json.loads(raw))
    if len(found) != 1:
        raise SystemExit("REFUSED: line %d holds %d records with id %s"
                         % (line_no, len(found), tool_id))
    return found[0], raw


os.makedirs(OWNERS, exist_ok=True)
os.makedirs(EV, exist_ok=True)

base = io.open(BASE, "rb").read()
check("the named base file is the pinned one", sha(base), WANT_BASE)
check("the base size", len(base), WANT_BASE_BYTES)

text = base.decode("utf-8")
prov = []
for line_no, tool_id in EDITS:
    rec, raw = edit_record(line_no, tool_id)
    i = rec.get("input", {})
    old, new = i.get("old_string"), i.get("new_string")
    check("record %d names the A6 owner" % line_no,
          os.path.basename(str(i.get("file_path"))), "a6_launch_freeze.py")
    check("record %d old occurs exactly once" % line_no, text.count(old), 1)
    text = text.replace(old, new)
    prov.append({"transcript": T, "line": line_no, "tool_use_id": tool_id,
                 "line_sha256": sha(raw.encode("utf-8")),
                 "file_path": i.get("file_path"),
                 "old_bytes": len(old.encode("utf-8")),
                 "new_bytes": len(new.encode("utf-8")),
                 "text_sha256_after": sha(text)})

out = text.encode("utf-8")
check("recovered A6 owner size", len(out), WANT_OWNER_BYTES)
check("recovered A6 owner sha256", sha(out), WANT_OWNER)

bad = [n for n, ok in CHECKS if not ok]
if bad:
    print("REFUSED: nothing written; failed %s" % bad)
    sys.exit(2)

io.open(OWNERS + "/a6_launch_freeze.py", "wb").write(out)
io.open(EV + "/A6_OWNER_PROVENANCE.json", "w", encoding="utf-8").write(json.dumps(
    {"base": {"path": BASE, "bytes": len(base), "sha256": sha(base)},
     "edits": prov,
     "result": {"bytes": len(out), "sha256": sha(out),
                "written_to": OWNERS + "/a6_launch_freeze.py"},
     "note": ("the published A5 tree carries an OLDER incidental copy of this file; it is "
              "left untouched and is not the A6 owner")},
    indent=1) + "\n")
print("RECOVER_A6_OWNER_OK  checks %d  failed 0" % len(CHECKS))
