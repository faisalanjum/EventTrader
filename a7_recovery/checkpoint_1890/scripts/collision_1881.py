# -*- coding: utf-8 -*-
"""Codex SEQ 1881 step 1: EXPOSE the shared-directory collision, before fixing it.

`g1_fake_state.build(tmp_root, ...)` owns its own path - it writes
`tmp_root/projects/proj/sess/workflows/wf_g1seg<NN>.json` and sets
AUD.PROJECTS_ROOT itself, so assigning that root beforehand isolates nothing.
Both 1880 payloads passed `os.path.dirname(run_dir)`, which is the ONE shared
WORK directory, and every case published segment 01. So all eight cases wrote
the SAME wf_g1seg01.json and the same child transcript ids: the last case won
and the other seven histories were overwritten.

This reads unit_1880's SAVED artifacts only. It changes nothing there and
reconstructs nothing: the overwritten histories are gone and stay gone.
"""
import collections, hashlib, io, json, os, sys

A = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
PRIOR = A + "/unit_1880/out"
OUT = "/tmp/a7_logs_1781"
TAG = os.environ["A7_TAG"]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fresh_target as FT                                        # noqa: E402

res = collections.OrderedDict(tag=TAG, reads_only=PRIOR)
checks = collections.OrderedDict()


def sha(p):
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


#: PER ATTEMPT. Each cont_<tag> directory is one attempt's own work root, so
#: they are measured separately - merging them counts a second attempt's state
#: file as if it were isolation, which is the opposite of the finding.
work = [d for d in sorted(os.listdir(PRIOR)) if d.startswith("cont_")]
res["prior_work_dirs"] = work
per_attempt = collections.OrderedDict()
for w in work:
    root = os.path.join(PRIOR, w)
    states = collections.OrderedDict()
    for base, _dirs, files in os.walk(root):
        for f in sorted(files):
            if f.startswith("wf_g1seg") and f.endswith(".json"):
                states[os.path.relpath(os.path.join(base, f), root)] = \
                    os.path.join(base, f)
    cases = sorted(d for d in os.listdir(root) if d.endswith("_run"))
    surviving = collections.OrderedDict()
    for rel, path in states.items():
        doc = json.load(io.open(path))
        # `scriptPath` is a TOP-LEVEL field of the state document, not a
        # workflowProgress row field - read from the document that owns it.
        script = doc.get("scriptPath")
        surviving[rel] = collections.OrderedDict([
            ("sha256", sha(path)), ("runId", doc.get("runId")),
            ("final_scriptPath", script)])
    # WHICH case run directory that surviving state actually describes, matched
    # on the script path's own leading directory rather than a guessed prefix.
    # THE SCRIPT PATH IS ABSOLUTE, so a leading-segment guess reads "" and
    # matches nothing. Match a case name as a real path COMPONENT instead.
    parts = set()
    for v in surviving.values():
        parts |= set((v["final_scriptPath"] or "").split("/"))
    described = sorted(parts & set(cases))
    per_attempt[w] = collections.OrderedDict([
        ("case_run_dirs", len(cases)), ("cases", cases),
        ("distinct_state_files", len(states)),
        ("surviving_state", surviving),
        ("cases_the_state_describes", described),
        ("overwritten_case_histories", len(cases) - len(described)),
    ])
res["per_attempt"] = per_attempt

#: EVERY ATTEMPT THAT DROVE MORE THAN ONE CASE. The defect is not a particular
#: count: it is that many cases shared a state path, so fewer histories survive
#: than cases ran. Stating it as "exactly one file" would be a fact about this
#: sample rather than the collision itself.
multi = [w for w, v in per_attempt.items() if v["case_run_dirs"] > 1]
res["multi_case_attempts"] = multi
checks["1_state_files_are_shared_across_cases"] = bool(multi) and all(
    per_attempt[w]["distinct_state_files"] < per_attempt[w]["case_run_dirs"]
    for w in multi)
checks["2_fewer_histories_survive_than_cases_ran"] = bool(multi) and all(
    len(per_attempt[w]["cases_the_state_describes"])
    < per_attempt[w]["case_run_dirs"] for w in multi)
res["overwritten_case_histories"] = {w: per_attempt[w][
    "overwritten_case_histories"] for w in multi}

res["checks"] = checks
res["n_checks"] = len(checks)
res["n_green"] = sum(1 for v in checks.values() if v)
res["all_green"] = all(checks.values())
FT.new_file(os.path.join(OUT, "COLLISION_1881_%s.json" % TAG),
            json.dumps(res, indent=1, default=str))
print("%s/%s -> %s" % (res["n_green"], res["n_checks"], res["all_green"]))
for k, v in checks.items():
    print("  %s %s" % ("GREEN" if v else "RED  ", k))
for w, v in per_attempt.items():
    print("  %-12s cases=%-3d distinct_state_files=%-2d describes=%s"
          % (w, v["case_run_dirs"], v["distinct_state_files"],
             v["cases_the_state_describes"]))
print("overwritten case histories:", res["overwritten_case_histories"])
sys.exit(0 if res["all_green"] else 1)
