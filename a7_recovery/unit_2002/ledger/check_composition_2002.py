"""Reuse the independent composition probes against the actual new owner."""
import runpy
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2002/owner")
import a4_source_closure as CL

root = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/codex_review_1989"
scope = runpy.run_path(root + "/probe_closure_interactions_2001.py")
assert scope["CL"] is CL
assert all(row["keys"] == list(CL.PAYLOAD_KEYS)
           and row["exact_own_leads"] and row["canonical_scope"]
           and not row["prompt_problems"]
           and row["launcher_contains_own_lead"]
           for row in scope["results"])
gate = runpy.run_path(root + "/probe_closure_run_error_2000.py")
assert gate["CL"] is CL
assert [r["ok"] for r in gate["results"]] == [True, False, True]
