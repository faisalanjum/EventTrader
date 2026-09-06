# -*- coding: utf-8 -*-
"""Render the launch-directory launchers through their OWNERS (Codex SEQ 1695
item 2: "exact receipt/finalization/raw/script trees for each bound run").

The receipts name launchers in a separate launch directory
(`/tmp/<run>_launch/NN_<packet>.attemptN.js`). Those bytes are not stored
anywhere durable - they are owner-rendered, and `LAUNCHERS.tsv` pins the exact
sha of each. This renders every pinned launcher through the owners and writes it
ONLY when the rendered bytes equal the pin, so a rendered byte can never differ
from the historical one. Which owner renders a given run is decided by the pin
itself, never assumed.

Runs inside the private namespace; writes into the durable unit.
"""
import hashlib
import io
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
OUT_ROOT = os.environ["LAUNCH_OUT"]          # durable unit/launch
SPEC = os.environ["LAUNCH_SPEC"]             # run_name<TAB>LAUNCHERS.tsv path, one per line
RUNS_ROOT = os.environ["RUNS_ROOT"]           # durable unit/runs (reconstructed run dirs)

sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")

sha = lambda t: hashlib.sha256(t.encode("utf-8") if isinstance(t, str) else t).hexdigest()

import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402
import build_kfields_final_targeted as FT                        # noqa: E402
import build_kfields_hard_review_targeted as HRT                 # noqa: E402


def task_sources():
    """Every task list an owner can supply, tried in turn; the pin decides."""
    out = []
    for label, fn in (("T.targeted_items", getattr(T, "targeted_items", None)),
                      ("HRT.tasks", getattr(HRT, "tasks", None)),
                      ("FT.event_tasks", getattr(FT, "event_tasks", None))):
        if callable(fn):
            try:
                out.append((label, list(fn())))
            except Exception:                                    # noqa: BLE001
                pass
    return out


import build_kfields_hard_review as HR                          # noqa: E402
BLINDS = list(getattr(HR, "BLINDS", []) or [])

RENDERERS = [("K.render_launcher", getattr(K, "render_launcher", None)),
             ("FT.render_launcher", getattr(FT, "render_launcher", None)),
             ("HRT.render_launcher", getattr(HRT, "render_launcher", None))]


def ident(t):
    for k in ("packet_id", "task_id", "source_id", "lead_id", "id"):
        if isinstance(t, dict) and t.get(k):
            return t[k]
    return None


SOURCES = task_sources()
total = matched = written = 0
unmatched = []

for line in io.open(SPEC, encoding="utf-8").read().splitlines():
    if not line.strip():
        continue
    run, tsv = line.split("\t")
    rows = io.open(tsv, encoding="utf-8").read().splitlines()
    # The exports use two shapes: a separate `<run>_launch/` directory keyed by
    # `packet_id`, or launchers inside the run's own `scripts/` keyed by `label`.
    # Resolve the columns and the destination from the row itself.
    hdr = rows[0].split("\t")
    iid = hdr.index("packet_id") if "packet_id" in hdr else hdr.index("label")
    ish, isp = hdr.index("sha256"), hdr.index("scriptPath")
    ia = hdr.index("attempt") if "attempt" in hdr else None
    for r in rows[1:]:
        if not r.strip():
            continue
        c = r.split("\t")
        packet, pin, spath = c[iid], c[ish], c[isp]
        if ia is not None:
            attempt = int(c[ia])
        else:                                    # ...attemptN.js
            stem = os.path.basename(spath).split(".attempt")
            attempt = int(stem[1].split(".")[0]) if len(stem) > 1 else 1
        rel = spath[len("/tmp/"):] if spath.startswith("/tmp/") else os.path.basename(spath)
        top = rel.split("/")[0]
        # a launcher inside a reconstructed run dir stays there; a separate
        # launch directory is mirrored under the unit's launch/ root.
        if os.path.isdir(os.path.join(RUNS_ROOT, top)):
            dst = os.path.join(RUNS_ROOT, rel)
        else:
            dst = os.path.join(OUT_ROOT, rel)
        total += 1
        if os.path.isfile(dst) and sha(io.open(dst, encoding="utf-8").read()) == pin:
            matched += 1
            continue
        hit = None
        # A hard-review label is "<task id>/<blind tag>"; the task is keyed by
        # the id part alone, and the blind is decided below by the pin.
        key = packet.split("/")[0]
        for _sl, tasks in SOURCES:
            task = next((t for t in tasks if ident(t) in (packet, key)), None)
            if task is None:
                continue
            for _rl, fn in RENDERERS:
                if not callable(fn):
                    continue
                # Two owner shapes: (task, attempt) and the hard-review
                # (task, blind, attempt). Try each blind and let the PIN decide,
                # so the blind is never assumed from the label text.
                for args in [(task, attempt)] + [(task, b, attempt) for b in BLINDS]:
                    try:
                        text = fn(*args)
                    except Exception:                            # noqa: BLE001
                        continue
                    if sha(text) == pin:                         # the pin decides
                        hit = text
                        break
                if hit is not None:
                    break
            if hit is not None:
                break
        if hit is None:
            unmatched.append((run, packet, pin[:16]))
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with io.open(dst, "w", encoding="utf-8") as fh:
            fh.write(hit)
        matched += 1
        written += 1

print("pinned launchers   : %d" % total)
print("reproduced (== pin): %d   newly written: %d" % (matched, written))
if unmatched:
    print("NOT REPRODUCIBLE (%d):" % len(unmatched))
    for run, packet, pin in unmatched[:15]:
        print("   ! %-28s %-32s pin %s" % (run, packet, pin))
    sys.exit(1)
print("LAUNCHERS OK")
