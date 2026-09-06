# -*- coding: utf-8 -*-
"""Freeze the A7 reconstruction: manifest, accounting, proposed whitelist.

The manifest covers every byte this unit produced or depends on. The two large
composed views are evidence COPIES bound read-only, so they are pinned by one
directory digest each rather than listed file by file - that is what makes the
manifest the smallest complete one.
"""
import hashlib, io, os, json

U = os.path.dirname(os.path.abspath(__file__))
VIEWS = {"view/workflows", "view/subagent_runs"}


def fsha(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dir_digest(d):
    lines = []
    for base, _x, fs in os.walk(d):
        for n in fs:
            p = os.path.join(base, n)
            lines.append("%s  ./%s\n" % (fsha(p), os.path.relpath(p, d)))
    return (hashlib.sha256("".join(sorted(lines)).encode()).hexdigest(), len(lines))


rows, skipped = [], []
for base, dirs, files in os.walk(U):
    rel = os.path.relpath(base, U)
    if any(rel == v or rel.startswith(v + os.sep) for v in VIEWS):
        dirs[:] = []
        continue
    for n in sorted(files):
        p = os.path.join(base, n)
        rows.append("%s  %s\n" % (fsha(p), os.path.relpath(p, U)))
for v in sorted(VIEWS):
    dg, n = dir_digest(os.path.join(U, v))
    skipped.append("%s  %s/  (%d files, one directory digest)\n" % (dg, v, n))

io.open(U + "/MANIFEST.sha256", "w").write("".join(sorted(rows)) + "".join(skipped))
print("manifest rows: %d files + %d pinned view digests" % (len(rows), len(skipped)))

# --- the accounting, historical and live kept apart -------------------------
acct = {
    "producer": {"workflow_records_bound_by_the_receipt": 36,
                 "answers": 392, "packets": 196, "events": 36,
                 "extra_session_limit_starts_counted_separately": 3},
    "candidate": {"lanes": 206, "batches": 103, "questions": 444,
                  "prompt_pins": 103, "finalized_lanes_bound": 82,
                  "answered_questions": 199, "remaining_questions": 245},
    "budget": {"frozen_historical_spent_before": 5612,
               "live_conservative": 5739,
               "note": "kept apart; no retrospective change to closed A4/A6 accounting"},
}
io.open(U + "/ACCOUNTING.json", "w").write(json.dumps(acct, indent=1) + "\n")

# --- proposed publication whitelist ----------------------------------------
wl = []
for base, dirs, files in os.walk(U):
    rel = os.path.relpath(base, U)
    if any(rel == v or rel.startswith(v + os.sep) for v in VIEWS):
        dirs[:] = []
        continue
    for n in sorted(files):
        wl.append(os.path.relpath(os.path.join(base, n), U))
io.open(U + "/WHITELIST.tsv", "w").write("".join(p + "\n" for p in sorted(wl)))
print("proposed whitelist rows: %d  (the two bound evidence views excluded)" % len(wl))
print("manifest sha:", fsha(U + "/MANIFEST.sha256"))
print("whitelist sha:", fsha(U + "/WHITELIST.tsv"))
