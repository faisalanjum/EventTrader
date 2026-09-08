# -*- coding: utf-8 -*-
"""Codex SEQ 1881: re-audit EVERY baseline case AFTER all cases and mutations.

The 1880 defect passed every immediate per-case check and still lost seven of
eight histories, because each later case overwrote the shared state file and
the same-id child transcripts. A check that runs while the case is the most
recent one cannot see that. So this runs at the END, over the saved results,
and puts each case's official state and child transcripts back through the REAL
audit owner against that case's OWN root and receipt.

Nothing is rebuilt or re-driven here: it reads what the runs already saved.
"""
import collections, hashlib, io, json, os, sys

RECOVERY = "/home/faisal/EventMarketDB-driver-recovery"
A = RECOVERY + "/a7_recovery"
S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/"
     "5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad")
VIEW = S + "/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3"
OUT = "/tmp/a7_logs_1781"
TAG = os.environ["A7_TAG"]
BASE = os.environ["A7_BASELINE_RESULT"]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RECOVERY)
import driver.core.driver_validators as _DV                      # noqa: E402
sys.path.insert(0, VIEW)
import fresh_target as FT                                        # noqa: E402
import a7_g1_build as G                                          # noqa: E402
import audit_worker_access as AUD                                # noqa: E402

res = collections.OrderedDict(tag=TAG, baseline=BASE)
checks = collections.OrderedDict()


def h(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


base = json.load(io.open(BASE))
rows = collections.OrderedDict()
before = getattr(AUD, "PROJECTS_ROOT", None)
try:
    for name, case in (base.get("cases") or {}).items():
        if not case.get("run_dir"):
            rows[name] = {"skipped": "this case never published"}
            continue
        run_dir, n = case["run_dir"], case["segment"]
        # EACH CASE'S OWN projects root, as its own build reported it.
        AUD.PROJECTS_ROOT = case["projects_root"]
        receipt_sha = G._sha_file(G.receipt_path(run_dir, n))
        problems, whole = G.audit_official_state(
            run_dir, n, case["root_sha256"], receipt_sha)
        again = {l: h(v) for l, v in (whole or {}).items()}
        rows[name] = collections.OrderedDict([
            ("state_path", case["state_path"]),
            ("projects_root", case["projects_root"]),
            ("state_sha256_now",
             G._sha_file(case["state_path"])
             if os.path.isfile(case["state_path"]) else None),
            ("state_sha256_then", case["state_sha256"]),
            ("audit_problems", [str(p)[:160] for p in (problems or [])[:3]]),
            ("whole_sha256_now", again),
            ("whole_sha256_then", case["bound_whole_sha256"]),
            ("whole_matches", again == case["bound_whole_sha256"]),
        ])
finally:
    AUD.PROJECTS_ROOT = before
res["cases"] = rows

audited = [r for r in rows.values() if "skipped" not in r]
paths = [r["state_path"] for r in audited]
roots = [r["projects_root"] for r in audited]
res["cases_audited"] = len(audited)
res["distinct_state_paths"] = len(set(paths))
res["distinct_projects_roots"] = len(set(roots))
checks["1_every_case_kept_its_own_state_path"] = (
    bool(audited) and len(set(paths)) == len(audited)
    and len(set(roots)) == len(audited))
checks["2_every_saved_state_is_still_its_own_bytes"] = all(
    r["state_sha256_now"] == r["state_sha256_then"] for r in audited)
checks["3_the_real_audit_owner_still_accepts_every_case"] = all(
    not r["audit_problems"] for r in audited)
checks["4_the_whole_answers_still_bind_to_the_same_bytes"] = all(
    r["whole_matches"] for r in audited)

res["checks"] = checks
res["n_checks"] = len(checks)
res["n_green"] = sum(1 for v in checks.values() if v)
res["all_green"] = bool(checks) and all(checks.values())
FT.new_file(os.path.join(OUT, "AFTER_AUDIT_1881_%s.json" % TAG),
            json.dumps(res, indent=1, default=str))
print("%s/%s -> %s" % (res["n_green"], res["n_checks"], res["all_green"]))
for k, v in checks.items():
    print("  %s %s" % ("GREEN" if v else "RED  ", k))
print("cases audited: %d  distinct state paths: %d  distinct projects roots: %d"
      % (res["cases_audited"], res["distinct_state_paths"],
         res["distinct_projects_roots"]))
for name, r in rows.items():
    if "skipped" in r:
        continue
    if r["audit_problems"] or not r["whole_matches"]:
        print("  %-34s problems=%s whole_matches=%s"
              % (name, r["audit_problems"][:1], r["whole_matches"]))
sys.exit(0 if res["all_green"] else 1)
