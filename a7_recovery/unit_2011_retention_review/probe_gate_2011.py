# -*- coding: utf-8 -*-
"""Core 2011: isolate the closeout comparison gate, with the FULL reason.
Private clone only; every mutation restored.
"""
import collections, hashlib, io, json, os, sys, traceback
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A + "/unit_2009/owner")
import a4_review_composite as RC                                  # noqa: E402
CL, HR, K, OLD, RT = RC.CL, RC.HR, RC.K, RC.OLD, RC.RT
fsha = lambda p: hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def snapshot(root):
    return {os.path.join(d, n): fsha(os.path.join(d, n))
            for d, _s, fs in os.walk(root) for n in sorted(fs)}


res = collections.OrderedDict()
old, _st = RC.old_readings()
label = [l for l, v in old.items() if v[0] == "valid"][0]
p0 = os.path.join(RC.OLD_RUN, "raw",
                  "%s.attempt1.proved.json" % label.replace("/", "_"))
res["label"] = label
res["artifact"] = p0
base = snapshot(RC.OLD_RUN)


def run(tag, gated):
    keep = io.open(p0, "rb").read()
    os.remove(p0)                       # the artifact the finalizer would write
    real = RC._completed
    if not gated:
        RC._completed = lambda owner, ctx, r, pkg: owner._finalize(ctx, r, pkg)
    try:
        RC.old_readings()
        out = "ACCEPTED"
    except Exception as exc:                          # noqa: BLE001 - measured
        out = "%s: %s" % (type(exc).__name__, str(exc))
        res[tag + "_traceback_tail"] = traceback.format_exc().strip(
            ).splitlines()[-4:]
    finally:
        RC._completed = real
        created = os.path.isfile(p0)
        res[tag + "_artifact_recreated_by_the_owner"] = created
        if created:
            res[tag + "_recreated_bytes_equal_original"] = \
                io.open(p0, "rb").read() == keep
        io.open(p0, "wb").write(keep)
    now = snapshot(RC.OLD_RUN)
    res[tag + "_outcome"] = out
    res[tag + "_files_differing_after_restore"] = [
        os.path.relpath(p, RC.OLD_RUN) for p in set(now) | set(base)
        if now.get(p) != base.get(p)]


run("gated", True)
run("ungated", False)
control, _s = RC.old_readings()
res["positive_control_after"] = dict(
    collections.Counter(v[0] for v in control.values()))
res["run_unchanged_at_end"] = snapshot(RC.OLD_RUN) == base
print(json.dumps(res, indent=1, default=str))
