# -*- coding: utf-8 -*-
"""Codex SEQ 2011: independent review of the retention / new-slot /
complete-closeout boundary of unit_2009/owner/a4_review_composite.py.

NO MODEL IS CALLED. Every mutation is made on a PRIVATE clone served by this
unit's own map; the frozen source fixtures and the live evidence are never
touched. Each mutation is restored and a positive control is re-run.
"""
import collections, contextlib, hashlib, io, json, os, sys
A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
sys.path.insert(0, A + "/unit_2009/owner")
import a4_review_composite as RC                                  # noqa: E402

CL, HR, K, OLD, RT = RC.CL, RC.HR, RC.K, RC.OLD, RC.RT
TAG = os.environ.get("A7_TAG", "x")
cases, counts = [], collections.Counter()
TOUCHED = set()   # every path THIS battery itself rewrites


def case(name, got, want):
    ok = got == want
    counts["total"] += 1
    counts["passed" if ok else "failed"] += 1
    cases.append(collections.OrderedDict(
        [("case", name), ("ok", ok)] + ([] if ok else
                                        [("got", got), ("want", want)])))
    return ok


def fsha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def tree(root):
    """The BYTES of every file under a run. A restore of my own necessarily
    rewrites an mtime, so content is what 'wrote nothing' can mean here."""
    out = {}
    for d, _s, fs in os.walk(root):
        for n in sorted(fs):
            p = os.path.join(d, n)
            out[p] = fsha(p)
    return out


def mtimes(root):
    out = {}
    for d, _s, fs in os.walk(root):
        for n in sorted(fs):
            p = os.path.join(d, n)
            out[p] = str(os.stat(p).st_mtime_ns)
    return out


def outcome(fn):
    try:
        fn()
        return "ACCEPTED"
    except Exception as exc:                          # noqa: BLE001 - measured
        return "%s: %s" % (type(exc).__name__, str(exc)[:110])


res = collections.OrderedDict()
res["composite_under_review"] = fsha(RC.__file__.rstrip("c"))
res["old_owner"] = fsha(RC.OLD_OWNER_PATH)
res["successor_owner"] = fsha(HR.__file__.rstrip("c"))
res["old_run"], res["old_pkg"] = RC.OLD_RUN, RC.OLD_PKG

# ======================================================================
# 1. THE POPULATION, FROM THE ACTUAL OWNERS
# ======================================================================
base_tree = tree(RC.OLD_RUN)
base_mtimes = mtimes(RC.OLD_RUN)
old, stage = RC.old_readings()
case("1a the old owner itself proves the historical population",
     dict(collections.Counter(v[0] for v in old.values())),
     {"valid": 62, "invalid_response": 4})
case("1b both original attempts are replayed as complete closeouts",
     sorted(os.path.basename(p) for p in stage["evidence"]),
     ["retry", "review_2004"])
# his replay numbers, recomputed per attempt through the same gate
per = collections.OrderedDict()
with RC.old_scope():
    ctx_old = CL._ctx()
    for name, run in (("primary", RC.OLD_RUN),
                      ("child", os.path.join(RC.OLD_RUN, "retry"))):
        doc = RC._completed(OLD, ctx_old, run, RC.OLD_PKG)
        per[name] = (doc["ledger"]["valid"], doc["ledger"]["invalid_response"])
case("1c the two closeouts re-derive his replayed counts",
     dict(per), {"primary": (52, 14), "child": (10, 4)})
res["per_attempt"] = dict(per)

ctx = RC._ctx()
case("1d exactly the unsatisfied slots are carried forward",
     [HR.call_label(t, b) for t, b in ctx["slots"]],
     [l for l, v in old.items() if v[0] != "valid"])
case("1e the record-based input no longer exists at all",
     [hasattr(RC, "OLD_RECORD"), hasattr(RC, "_old_record"),
      "OLD_READINGS" in io.open(RC.__file__.rstrip("c"),
                                encoding="utf-8").read()],
     [False, False, False])
case("1f nothing was written by reading the population",
     tree(RC.OLD_RUN), base_tree)

# ======================================================================
# 2. THE 58 PAIRED-VALID SWAPS, AT THE ARTIFACT BOUNDARY IT CONSUMES
# ======================================================================
paired = [t["task_id"] for t in ctx["tasks"]
          if all(old[HR.call_label(t["task_id"], b)][0] == "valid"
                 for b in HR.BLINDS)]
res["paired_valid_tasks"] = len(paired)


def proved_path(label):
    for base, att in ((RC.OLD_RUN, 1),
                      (os.path.join(RC.OLD_RUN, "retry"), K.MAX_ATTEMPTS)):
        p = os.path.join(base, "raw", "%s.attempt%d.proved.json"
                         % (label.replace("/", "_"), att))
        if os.path.isfile(p):
            return p
    return None


swaps = accepted = 0
first_reason = None
accepted_rows, identical_pairs = [], []
for task_id in paired:
    for a, b in ((1, 2), (2, 1)):
        la, lb = HR.call_label(task_id, a), HR.call_label(task_id, b)
        pa, pb = proved_path(la), proved_path(lb)
        if not (pa and pb):
            continue
        same_already = old[la][2] == old[lb][2]
        if same_already:
            identical_pairs.append((la, lb))
        keep = io.open(pb, "rb").read()
        TOUCHED.add(pb)
        io.open(pb, "wb").write(io.open(pa, "rb").read())   # ONE blind's answer
        try:                                                # in the OTHER's file
            got, _st = RC.old_readings()
            credited = (got[lb][0] == "valid" and got[lb][2] == old[la][2])
            reason = "ACCEPTED"
        except Exception as exc:                            # noqa: BLE001
            credited, reason = False, "%s: %s" % (type(exc).__name__,
                                                  str(exc)[:90])
        finally:
            io.open(pb, "wb").write(keep)
        swaps += 1
        if credited:
            accepted += 1
            accepted_rows.append(collections.OrderedDict(
                [("from", la), ("into", lb),
                 ("the two answers were already byte-identical", same_already),
                 ("so no foreign answer was substituted", same_already)]))
        first_reason = first_reason or reason
res["identity_swaps_tested"] = swaps
res["identity_swaps_accepted"] = accepted
res["first_swap_reason"] = first_reason
res["accepted_swaps"] = accepted_rows
res["pairs_already_identical"] = [list(p) for p in identical_pairs]
res["substitutions_of_a_DIFFERENT_answer"] = [
    r for r in accepted_rows
    if not r["the two answers were already byte-identical"]]
case("2a no DIFFERENT reviewer's answer is ever substituted",
     [swaps, len(res["substitutions_of_a_DIFFERENT_answer"])], [58, 0])
after_swaps, _s = RC.old_readings()
case("2b the positive control is restored after every swap",
     dict(collections.Counter(v[0] for v in after_swaps.values())),
     {"valid": 62, "invalid_response": 4})
case("2c the swaps left every byte as it was", tree(RC.OLD_RUN), base_tree)

# ---- directly relevant missing / drifted negatives --------------------
def with_file(path, new_bytes, fn):
    TOUCHED.add(path)
    keep = io.open(path, "rb").read() if os.path.isfile(path) else None
    try:
        if new_bytes is None:
            os.remove(path)
        else:
            io.open(path, "wb").write(new_bytes)
        return fn()
    finally:
        if keep is None:
            os.path.isfile(path) and os.remove(path)
        else:
            io.open(path, "wb").write(keep)


label0 = [l for l, v in old.items() if v[0] == "valid"][0]
p0 = proved_path(label0)
neg = collections.OrderedDict()
neg["missing proved artifact"] = with_file(
    p0, None, lambda: outcome(RC.old_readings))
neg["drifted proved artifact"] = with_file(
    p0, b'{"drifted": true}', lambda: outcome(RC.old_readings))
fin = os.path.join(RC.OLD_RUN, K.FINALIZATION_NAME)
doc = json.loads(io.open(fin, encoding="utf-8").read())
neg["drifted closeout"] = with_file(
    fin, json.dumps(dict(doc, ledger=dict(doc["ledger"], valid=99)),
                    indent=1).encode("utf-8"),
    lambda: outcome(RC.old_readings))
childr = os.path.join(RC.OLD_RUN, "retry", K.RECEIPT_NAME)
neg["missing child receipt"] = with_file(
    childr, None, lambda: outcome(RC.old_readings))
rawf = os.path.join(RC.OLD_RUN, "raw", sorted(
    n for n in os.listdir(os.path.join(RC.OLD_RUN, "raw"))
    if n.endswith(".raw.json"))[0])
neg["drifted kept raw"] = with_file(
    rawf, b"drifted raw bytes", lambda: outcome(RC.old_readings))
res["negatives"] = neg
case("2d every missing or drifted evidence negative refuses",
     [k for k, v in neg.items() if v == "ACCEPTED"], [])
case("2e the run is byte-identical after the negatives",
     tree(RC.OLD_RUN), base_tree)

# ---- REMOVE THE NEW CLOSEOUT COMPARISON GATE -------------------------
real_completed = RC._completed


def ungated(owner, ctx_, run, package):
    """The same replay WITHOUT the write-refusing comparison guard."""
    return owner._finalize(ctx_, run, package)


def gate_removed():
    RC._completed = ungated
    try:
        return with_file(p0, None, lambda: outcome(RC.old_readings))
    finally:
        RC._completed = real_completed


def missing_artifact_recreated(gated):
    """Remove one completed proved artifact and report whether the owner
    silently re-manufactures it. The artifact is always restored."""
    keep = io.open(p0, "rb").read()
    real = RC._completed
    os.remove(p0)
    TOUCHED.add(p0)
    if not gated:
        RC._completed = ungated
    try:
        try:
            RC.old_readings()
            why = "ACCEPTED"
        except Exception as exc:                      # noqa: BLE001 - measured
            why = "%s: %s" % (type(exc).__name__, str(exc)[:90])
        return os.path.isfile(p0), why
    finally:
        RC._completed = real
        io.open(p0, "wb").write(keep)


gated_recreated, gated_why = missing_artifact_recreated(True)
ungated_recreated, ungated_why = missing_artifact_recreated(False)
res["gate_kept"] = {"recreated_the_missing_evidence": gated_recreated,
                    "reason": gated_why}
res["gate_removed"] = {"recreated_the_missing_evidence": ungated_recreated,
                       "reason": ungated_why}
case("2f the gate is load-bearing: without it the finalizer re-manufactures "
     "the missing completed evidence, with it the run refuses",
     [gated_recreated, ungated_recreated], [False, True])
control, _s = RC.old_readings()
case("2g the positive control returns after the gate is restored",
     [dict(collections.Counter(v[0] for v in control.values())),
      tree(RC.OLD_RUN) == base_tree],
     [{"valid": 62, "invalid_response": 4}, True])
# THE UNTOUCHED FILES must keep their exact nanosecond mtime: only the files
# this battery itself rewrote may differ, and they are named.
drifted = [p for p, m in mtimes(RC.OLD_RUN).items()
           if m != base_mtimes.get(p)]
res["files_this_battery_rewrote"] = len(TOUCHED)
res["mtime_drift_after_everything"] = len(drifted)
res["drift_outside_what_i_rewrote"] = [os.path.relpath(p, RC.OLD_RUN)
                                       for p in drifted if p not in TOUCHED]
case("2h only files this battery rewrote have a new mtime",
     res["drift_outside_what_i_rewrote"], [])

# ======================================================================
# 3. WRITES AND CONTEXT LEAKS
# ======================================================================
case("3a a refusal restores the transport writers",
     [RT.write_new is not RC._existing, RT.save_raw is not RC._no_raw_write],
     [True, True])
leak = None
try:
    with RC.old_scope():
        raise RuntimeError("forced")
except RuntimeError:
    leak = (CL.HR is HR, CL.SK.HR is HR, CL.F.HR is HR,
            CL.F._HERE != str(RC.OLD_OWNER_PATH.parent))
case("3b old_scope restores every patched owner after a failure",
     list(leak), [True, True, True, True])
case("3c the composite never changed a byte in the run",
     tree(RC.OLD_RUN), base_tree)

res["counts"] = dict(counts)
res["failed"] = [c for c in cases if not c["ok"]]
res["cases"] = [c["case"] for c in cases]
res["ok"] = not res["failed"]
print(json.dumps(res, indent=1, default=str))
raise SystemExit(0 if res["ok"] else 3)
