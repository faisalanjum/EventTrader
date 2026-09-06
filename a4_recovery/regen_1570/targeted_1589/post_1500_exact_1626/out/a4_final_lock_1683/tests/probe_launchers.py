# -*- coding: utf-8 -*-
"""Decide whether the pinned launcher bytes are OWNER-REPRODUCIBLE.

The targeted run's receipt names launchers in a separate launch directory
(`/tmp/<run>_launch/NN_<packet>.attemptN.js`) and the audit requires each to be
readable at the sha `LAUNCHERS.tsv` pins. No durable copy of those bytes was
found, so either an owner re-renders them exactly (they are reproducible, and
only the FILE NAME was historical), or they are a genuine missing byte.

This probe renders the first pinned task through each candidate owner renderer
and compares the rendered sha with the pin. It writes nothing.
"""
import hashlib
import io
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
LAUNCHERS = os.environ["LAUNCHERS_TSV"]

sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()

rows = [l.split("\t") for l in io.open(LAUNCHERS, encoding="utf-8").read().splitlines()[1:] if l.strip()]
hdr = io.open(LAUNCHERS, encoding="utf-8").read().splitlines()[0].split("\t")
i_packet, i_sha, i_attempt = hdr.index("packet_id"), hdr.index("sha256"), hdr.index("attempt")
want = {r[i_packet]: (r[i_sha], int(r[i_attempt])) for r in rows}
first_packet = rows[0][i_packet]
first_sha, first_attempt = want[first_packet]
print("pinned packet   : %s (attempt %d)" % (first_packet, first_attempt))
print("pinned sha      : %s" % first_sha[:16])

import build_kfields_key_targeted as T                          # noqa: E402
import build_kfields_final_targeted as FT                       # noqa: E402
import build_kfields_key as K                                   # noqa: E402

# find the task object for that packet through the targeted owner's own task list
tasks = None
for name in ("targeted_items", "targets", "event_tasks", "tasks", "items"):
    fn = getattr(T, name, None)
    if callable(fn):
        try:
            tasks = fn()
            print("task source     : T.%s -> %d" % (name, len(tasks)))
            break
        except Exception as exc:                                 # noqa: BLE001
            print("task source     : T.%s raised %s" % (name, type(exc).__name__))
if tasks is None:
    print("RESULT: no task list obtainable from the targeted owner")
    sys.exit(2)


def _id(t):
    for k in ("packet_id", "source_id", "lead_id", "id"):
        if isinstance(t, dict) and t.get(k):
            return t[k]
    return None


task = next((t for t in tasks if _id(t) == first_packet), None)
if task is None:
    print("RESULT: pinned packet %r not present in the owner's task list" % first_packet)
    sys.exit(3)

for label, fn in (("K.render_launcher", getattr(K, "render_launcher", None)),
                  ("FT.render_launcher", getattr(FT, "render_launcher", None)),
                  ("T.render_launcher", getattr(T, "render_launcher", None))):
    if not callable(fn):
        continue
    try:
        text = fn(task, first_attempt)
        got = sha(text)
        print("%-20s -> %s  %s" % (label, got[:16],
                                   "MATCHES PIN" if got == first_sha else "differs"))
    except Exception as exc:                                     # noqa: BLE001
        print("%-20s -> raised %s: %s" % (label, type(exc).__name__, str(exc)[:120]))
print("RESULT: see above")
