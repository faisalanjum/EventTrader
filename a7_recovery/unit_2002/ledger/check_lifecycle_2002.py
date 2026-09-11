"""Actual invalid-only children and failure accounting. TEST evidence, no AI.

Fresh unique run IDs preserve every earlier TEST result. No saved successful
model call is executed, and no real native workflow store is writable.
"""
import json
import os
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2002/owner")
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a7_recovery/unit_2001/tests")
import a4_source_closure as CL
import synthetic_reading as SYN

K, F, SK = CL.K, CL.F, CL.SK
tag = os.environ["A7_TAG"]
base = os.path.dirname(CL.PKG_DIR)
review_pkg = os.path.join(base, "retry_pkg_" + tag)
review = os.path.join(base, "retry_review_" + tag)
final_pkg = os.path.join(base, "retry_final_pkg_" + tag)
final = os.path.join(base, "retry_final_" + tag)
projects = "/home/faisal/.claude/projects"
pristine = os.path.join(projects, "_pristine")
cases = []


def check(name, ok, detail=None):
    cases.append({"case": name, "ok": bool(ok), "detail": detail})


def refuses_final_scope():
    try:
        with CL.final_scope(review, review_pkg):
            return False
    except ValueError:
        return True


CL.build(review_pkg)
prep = CL.prepare_run(review, review_pkg)
assert prep["ok"], prep
labels = CL.canonical_calls()
bad_label = labels[0]
check("unstarted reviews cannot publish final work", refuses_final_scope())
for n, label in enumerate(labels):
    path = SYN.write_state(
        CL, review, review_pkg, label, "wf_%s_r_%03d" % (tag, n),
        pristine, projects, text="{}" if label == bad_label else None)
    CL.record_state(review, path)
before, problems = CL.readings(review, review_pkg)
check("a parseable but schema-invalid review remains invalid",
      not problems and before[bad_label][0] == "invalid_response")
rfin = CL.finalize(review, review_pkg)
check("review finalization credits successes and retries only the invalid one",
      not rfin["problems"] and rfin["retry"] == [bad_label]
      and rfin["ledger"]["valid"] == len(labels) - 1)
child = os.path.join(review, "retry")
check("an unstarted review child does not clear the obligation",
      refuses_final_scope())
path = SYN.write_state(CL, child, review_pkg, bad_label,
                       "wf_%s_rc" % tag, pristine, projects, attempt=2)
CL.record_state(child, path)
check("a valid but unfinalized review child still blocks final publication",
      refuses_final_scope())
rcfin = CL.finalize(child, review_pkg)
after, problems = CL.readings(review, review_pkg)
check("the review child is credited once, with every primary success unchanged",
      not problems and not rcfin["retry"] and not rcfin["problems"]
      and rcfin["ledger"]["valid"] == 1
      and all(v[0] == "valid" for v in after.values())
      and all(after[l] == before[l] for l in labels if l != bad_label))

with CL.final_scope(review, review_pkg) as context:
    expected_before = (CL.ledger_before() + rfin["ledger"]["scheduled"]
                       + rcfin["ledger"]["scheduled"])
    check("the final budget counts the actual invalid review attempt and child",
          context["before"] == expected_before)
    by_source = context["by_source"]
    SK.build(final_pkg)
    final_prep = SK.prepare_run(final, package=final_pkg)
    assert final_prep["ok"], final_prep
    task_labels = [t["source_id"] for t in SK.tasks()]
    invalid = task_labels[0]
    scripts = {i["label"]: i["scriptPath"]
               for i in final_prep["invocations"]}
    for n, label in enumerate(task_labels):
        path = SYN.write_final_state(
            CL, final, final_pkg, label, "wf_%s_f_%03d" % (tag, n),
            projects, by_source, script_path=scripts[label],
            resolve_open_issues=True, text="{}" if label == invalid else None)
        SK.record_state(final, path)
    fin = SK.finalize(final, package=final_pkg)
    before_resume = SK.resume_plan(final, package=final_pkg)
    primaries, primary_raws, primary_bad = SK.accepted_shards(
        final, package=final_pkg)
    check("final closeout preserves every valid primary and owes one invalid child",
          fin["ledger"]["valid"] == len(task_labels) - 1
          and fin["ledger"]["invalid_response"] == 1
          and fin["retry"] == [invalid] and not fin["problems"]
          and before_resume["owed"] == [invalid]
          and len(before_resume["never_repeat"]) == len(task_labels) - 1
          and not before_resume["problems"], fin["ledger"])
    child = os.path.join(final, "retry")
    child_invocations = fin["child"]["invocations"]
    check("the actual child contains no successful primary",
          [i["label"] for i in child_invocations] == [invalid])
    path = SYN.write_final_state(
        CL, child, final_pkg, invalid, "wf_%s_fc" % tag,
        projects, by_source, script_path=child_invocations[0]["scriptPath"],
        resolve_open_issues=True, attempt=2)
    SK.record_state(child, path)
    child_fin = SK.finalize(child, package=final_pkg)
    resumed = SK.resume_plan(final, package=final_pkg)
    shards, raws, bad = SK.accepted_shards(final, package=final_pkg)
    check("final child completes exactly the one remaining result",
          child_fin["ledger"]["valid"] == 1 and not child_fin["retry"]
          and not child_fin["problems"] and not child_fin.get("child")
          and not os.path.exists(os.path.join(child, "retry")))
    check("resume credits all results once and preserves every successful primary",
          resumed["served"] == task_labels
          and resumed["never_repeat"] == task_labels and not resumed["owed"]
          and not resumed["retryable"] and not resumed["problems"]
          and not bad and list(shards) == task_labels
          and all(raws[s] == primary_raws[s] for s in primary_raws),
          {k: resumed[k] for k in ("owed", "retryable", "problems")})
    with SK._scope(bind_role=True):
        actual_before_signer = F.ledger_before_next_call(SK.bound(final, final_pkg))
    check("signer accounting includes final primary and invalid-only child",
          actual_before_signer == expected_before + len(task_labels) + 1,
          actual_before_signer)

gate = CL.signing_checks(review, review_pkg, key_run=final, key_package=final_pkg)
check("the complete primary-plus-child key passes the existing signing gate",
      gate["ok"], gate["stops"])

# The exact same gate must reject a complete, schema-valid key that leaves
# meaning unresolved. This is not an invitation to rerun a valid answer.
with CL.final_scope(review, review_pkg):
    unresolved_run = os.path.join(base, "unresolved_final_" + tag)
    prep = SK.prepare_run(unresolved_run, package=final_pkg)
    assert prep["ok"], prep
    for n, inv in enumerate(prep["invocations"]):
        path = SYN.write_final_state(
            CL, unresolved_run, final_pkg, inv["label"],
            "wf_%s_u_%03d" % (tag, n), projects, by_source,
            script_path=inv["scriptPath"], resolve_open_issues=False)
        SK.record_state(unresolved_run, path)
    ufin = SK.finalize(unresolved_run, package=final_pkg)
    plan = SK.resume_plan(unresolved_run, package=final_pkg)
check("semantic uncertainty is completed without a repeat call",
      ufin["ledger"]["valid"] == len(task_labels) and not ufin["retry"]
      and not ufin["problems"] and not plan["owed"]
      and not plan["retryable"] and not plan["problems"])
gate = CL.signing_checks(review, review_pkg, key_run=unresolved_run,
                         key_package=final_pkg)
check("schema-valid unresolved meaning still blocks signature",
      not gate["ok"] and bool(gate["stops"]), gate["stops"][:3])

# Unknown identity is not a retryable invalid answer. The remaining requests
# are deliberately unstarted, so the complete missing denominator is visible.
with CL.final_scope(review, review_pkg):
    broken = os.path.join(base, "unproved_final_" + tag)
    prep = SK.prepare_run(broken, package=final_pkg)
    assert prep["ok"], prep
    inv = prep["invocations"][0]
    path = SYN.write_final_state(
        CL, broken, final_pkg, inv["label"], "wf_%s_wrongid" % tag,
        projects, by_source, script_path=inv["scriptPath"],
        resolve_open_issues=True, row={"model": "TEST-wrong-identity"})
    SK.record_state(broken, path)
    bfin = SK.finalize(broken, package=final_pkg)
    plan = SK.resume_plan(broken, package=final_pkg)
check("wrong identity plus missing calls fail closed with complete accounting",
      bfin["ledger"]["unproved"] == 1
      and bfin["ledger"]["missing"] == len(task_labels) - 1
      and bfin["ledger"]["valid"] == 0
      and not bfin["phase_complete"] and not bfin["retry"]
      and not plan["served"] and plan["owed"] == task_labels,
      bfin["ledger"])
gate = CL.signing_checks(review, review_pkg, key_run=broken, key_package=final_pkg)
check("the wrong-identity run cannot sign", not gate["ok"])
gate = CL.signing_checks(review, review_pkg, key_run=final, key_package=final_pkg)
check("the intact completed child remains a positive control", gate["ok"])
print(json.dumps({"test_only": True, "model_calls": 0, "cases": cases,
                  "passed": sum(c["ok"] for c in cases), "total": len(cases)},
                 indent=1))
raise SystemExit(0 if all(c["ok"] for c in cases) else 3)
