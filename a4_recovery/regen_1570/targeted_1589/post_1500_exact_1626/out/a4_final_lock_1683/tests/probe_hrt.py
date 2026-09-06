# -*- coding: utf-8 -*-
"""Why the hard-review launchers do not re-render: does the owner's task list
load at all, and what identifies each task?

`render_launchers.py` swallows loader errors so one broken source cannot stop
the rest; that hid whether `HRT.tasks()` failed or simply keys its tasks
differently. This reports both, without writing anything.
"""
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

import build_kfields_hard_review_targeted as HRT                 # noqa: E402
import build_kfields_hard_review as HR                           # noqa: E402

print("HR.BLINDS            : %r" % (getattr(HR, "BLINDS", None),))
print("HRT public callables : %s"
      % ", ".join(sorted(n for n in dir(HRT)
                         if not n.startswith("_") and callable(getattr(HRT, n)))))

for name in ("tasks", "targeted_items", "event_tasks", "leads"):
    fn = getattr(HRT, name, None)
    if not callable(fn):
        continue
    try:
        got = list(fn())
    except BaseException as exc:                                 # noqa: BLE001
        print("HRT.%-14s -> raised %s: %s" % (name, type(exc).__name__, str(exc)[:200]))
        continue
    print("HRT.%-14s -> %d items" % (name, len(got)))
    if got:
        first = got[0]
        if isinstance(first, dict):
            print("   keys  : %s" % sorted(first.keys())[:12])
            for k in ("label", "packet_id", "source_id", "lead_id", "id", "task_id"):
                if k in first:
                    print("   %-9s: %r" % (k, first[k]))
        else:
            print("   type  : %s  value: %r" % (type(first).__name__, str(first)[:120]))

rl = getattr(HRT, "render_launcher", None)
if rl is not None:
    import inspect
    try:
        print("HRT.render_launcher signature: %s" % (inspect.signature(rl),))
    except Exception:                                            # noqa: BLE001
        pass
