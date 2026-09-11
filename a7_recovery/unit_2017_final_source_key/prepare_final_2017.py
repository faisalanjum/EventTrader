# -*- coding: utf-8 -*-
"""Codex SEQ 2017: prepare the 33 REAL final source-key adjudication requests.

ZERO MODEL CALLS. The completed review run and package are served READ-ONLY by
this unit's map, and every new byte lands under A7_PREP_BASE, which the same
map binds to this unit alone.

The owners do all the work: this payload only enters the published composite's
own final-key scope, calls the unchanged source-key owner's build, preflight
and prepare_run with EXPLICIT fresh paths, and freezes what they produced.
"""
import collections
import glob
import hashlib
import io
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = A7 + "/unit_2017_final_source_key"
REVIEW_UNIT = A7 + "/unit_2015_real_reviews"

# --- Codex SEQ 2017's own pins and derived counts, checked, never derived here
COMPOSITE_PIN = "4a93689b5b7d7add223ee4d92c94b7b816871be9e8c10f8bbcf330bb4815aa64"
REVIEW_RECEIPT_PIN = "63d39415cc74bf53a7a790a7f81170a9c7563ed776ab6f4d5b204d22870eefc6"
REVIEW_FINALIZATION_PIN = "0bf9a9d60731529d3a41845e08466a633118f595b8a85ad57be892ef3946e35b"
REVIEW_MANIFEST_PIN = "4fbee22e8843953cf7d55685c4b34b7d323df0e738aa3d14bccb2b9418cea083"
EXPECTED_SOURCES = 36
EXPECTED_SCHEDULED = 33
EXPECTED_ROWS = 191
EXPECTED_LEADS = 66
EXPECTED_BEFORE = 499
EXPECTED_CALLS_ONLY = 532        # 499 + 33 adjudications, the figure Codex named
EXPECTED_AFTER_PLANNED = 533     # + the ONE separately gated signature
EXPECTED_WORST_CASE = 567        # + one invalid-only child per call and signer
EXPECTED_LOCATOR_GROUPS = 5
EXPECTED_ROLE = collections.OrderedDict([
    ("kind", "LIVE"), ("model_alias", "opus"),
    ("runtime_model_id", "claude-opus-5"),
    ("workflow_row_model", "claude-opus-5[1m]"), ("effort", "high"),
    ("agentType", "lean-probe"), ("disallowedTools", ["Read"]),
    ("max_output_tokens", "128000"),
    ("transport", "Claude Code Workflow agent(), subscription")])

checks = []


def check(name, got, want):
    assert got == want, "%s: got %r want %r" % (name, got, want)
    checks.append(name)


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def tree(root):
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            if os.path.isfile(path) and not os.path.islink(path):
                out[path] = fsha(path)
    return out


# --------------------------------------------------- 1. the loaded owners ---
sys.path.insert(0, A7 + "/unit_2009/owner")
import a4_review_composite as R                                    # noqa: E402
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570"
                   "/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
import boundary                                                    # noqa: E402

CL, HR, K, SK, F, INV, RT = R.CL, R.HR, R.K, R.SK, R.F, R.INV, R.RT
check("1 the published composite is the loaded owner",
      fsha(R.__file__.rstrip("c")), COMPOSITE_PIN)
check("2 the source-key owner is the unchanged unit_1997 one",
      os.path.realpath(SK.__file__.rstrip("c")),
      A7 + "/unit_1997/owner/a4_source_key.py")
check("3 the rejected unit_2008 composite is not loaded",
      [m for m, mod in sorted(sys.modules.items())
       if getattr(mod, "__file__", None)
       and "unit_2008/owner" in str(mod.__file__)], [])

rows = {r["logical"]: r for r in boundary.read_map(os.environ["A7_PREP_MAP"])}
BASE = os.environ["A7_PREP_BASE"]
REVIEW_RUN = os.path.join(os.path.dirname(R.OLD_RUN), "review_2015")
REVIEW_PKG = os.path.join(os.path.dirname(R.OLD_RUN), "closure_2015")
check("4 the completed review run and package are bound READ-ONLY",
      [[rows[p]["source"], rows[p]["mode"], boundary.validate([rows[p]])]
       for p in (REVIEW_RUN, REVIEW_PKG)],
      [[REVIEW_UNIT + "/key_closure/review_2015", "ro", []],
       [REVIEW_UNIT + "/key_closure/closure_2015", "ro", []]])
check("5 the original 2004 run and package stay READ-ONLY too",
      [[rows[p]["mode"], boundary.validate([rows[p]])]
       for p in (R.OLD_RUN, R.OLD_PKG)], [["ro", []], ["ro", []]])
check("6 every new byte lands in this unit alone",
      [rows[os.path.dirname(R.OLD_RUN)]["source"],
       rows[os.path.dirname(R.OLD_RUN)]["mode"]],
      [UNIT + "/key_closure", "rw"])
check("7 nothing in this binding is a TEST or fabricated store",
      [[l for l in rows if l.startswith(boundary.PROJECTS_MOUNT)],
       sorted({r["source"] for r in rows.values() if "TEST" in r["source"]}),
       sorted({r["source"] for r in rows.values() if "rehearsal" in r["source"]})],
      [[], [], []])
check("8 the completed review stage is the one Codex verified",
      [INV.sha_file(os.path.join(REVIEW_RUN, K.RECEIPT_NAME)),
       INV.sha_file(os.path.join(REVIEW_RUN, K.FINALIZATION_NAME)),
       INV.sha_file(os.path.join(REVIEW_PKG, CL.MANIFEST_NAME))],
      [REVIEW_RECEIPT_PIN, REVIEW_FINALIZATION_PIN, REVIEW_MANIFEST_PIN])

# ------------------------------------- 2. the complete review, read back -----
before_tree = tree(REVIEW_UNIT + "/key_closure")
merged, stages = R.merged_readings(REVIEW_RUN, REVIEW_PKG)
check("9 both review stages replay and all 66 slots are valid",
      [len(merged), dict(collections.Counter(v[0] for v in merged.values()))],
      [EXPECTED_LEADS, {"valid": EXPECTED_LEADS}])

# ------------------------------------------ 3. the real final-key gate -------
PKG = os.path.join(BASE, "key_package_2017")
RUN = os.path.join(BASE, "key_run_2017")
check("10 the new paths are not an existing directory",
      [os.path.exists(PKG), os.path.exists(RUN)], [False, False])

with R.final_scope(REVIEW_RUN, REVIEW_PKG) as proof:
    doc = SK.build(PKG)
    check("11 the package re-derives from the live owners",
          SK.package_problems(PKG), [])
    pre = SK.preflight(PKG)
    check("12 preflight is clean", [pre["ok"], pre["problems"]], [True, []])
    prepared = SK.prepare_run(RUN, package=PKG)
    check("13 preparation passes and schedules exactly 33 adjudications",
          [prepared["ok"], prepared["problems"], len(prepared["invocations"])],
          [True, [], EXPECTED_SCHEDULED])
    check("14 both real review stages are bound into the key package",
          doc["hard_review"]["stages"], stages)
    budget = doc["budget"]
    check("15 the ledger starts at 499 and 33 adjudications make 532",
          [budget["before"], budget["planned_key_calls"],
           budget["before"] + budget["planned_key_calls"]],
          [EXPECTED_BEFORE, EXPECTED_SCHEDULED, EXPECTED_CALLS_ONLY])
    check("16 the one signature is planned but separately gated, giving 533",
          [budget["planned_signer"], budget["planned_total"],
           budget["after_planned"]],
          [1, EXPECTED_SCHEDULED + 1, EXPECTED_AFTER_PLANNED])
    check("17 the worst case is 567 and stays inside both ceilings",
          [budget["worst_case_after"],
           budget["worst_case_after"] <= budget["package_ceiling"],
           budget["worst_case_after"] <= budget["global_ceiling"],
           budget["calls_made_by_this_package"]],
          [EXPECTED_WORST_CASE, True, True, 0])
    check("18 the package counts are the derived ones",
          [doc["counts"][k] for k in
           ("source_events", "events_scheduled", "frozen_rows",
            "rows_scheduled", "locator_groups", "leads_shown")]
          + [len(doc["counts"]["events_with_no_located_row"])],
          [EXPECTED_SOURCES, EXPECTED_SCHEDULED, EXPECTED_ROWS, EXPECTED_ROWS,
           EXPECTED_LOCATOR_GROUPS, EXPECTED_LEADS,
           EXPECTED_SOURCES - EXPECTED_SCHEDULED])
    coverage = SK.coverage()
    check("19 all 36 source events are accounted, 33 scheduled",
          [len(coverage), sum(1 for c in coverage if c["scheduled"]),
           sum(1 for c in coverage if not c["scheduled"]),
           sum(c["located_rows"] for c in coverage)],
          [EXPECTED_SOURCES, EXPECTED_SCHEDULED,
           EXPECTED_SOURCES - EXPECTED_SCHEDULED, EXPECTED_ROWS])
    check("20 two independent review leads per source, none foreign or omitted",
          [len(proof["by_source"]),
           sorted({len(v) for v in proof["by_source"].values()}),
           [t["source_id"] for t in SK.tasks()
            if SK.payload(t)["leads"] != proof["by_source"][t["source_id"]]]],
          [EXPECTED_SCHEDULED, [2], []])
    role = SK.key_role()
    check("21 the isolated key role is the frozen non-Sonnet one",
          collections.OrderedDict((k, role[k]) for k in EXPECTED_ROLE),
          EXPECTED_ROLE)
    prompts = [SK.prompt(t) for t in SK.tasks()]
    capacity = SK.capacity(prompts)
    check("22 no request is at or over the transport limit",
          capacity["at_or_over_transport_limit"], [])

    # ---- the isolation rule: no evaluated answer may reach the key owner ----
    a3_run = os.path.abspath(K.a3_run_dirs()[0])
    answers = [io.open(p, encoding="utf-8").read()
               for base in (a3_run, os.path.join(a3_run, "retry"))
               for p in sorted(glob.glob(os.path.join(base, "raw", "*")))
               if os.path.isfile(p)]
    joined = "\n".join(prompts)
    check("23 not one saved A3 answer appears in any of the 33 requests",
          [len(answers), [n for n, a in enumerate(answers) if a and a in joined]],
          [len(answers), []])

    receipt = K._load(os.path.join(RUN, K.RECEIPT_NAME))
    check("24 the receipt schedules exactly the frozen call order, unserved",
          [receipt["allowed"], receipt["attempt"], receipt["states"]],
          [doc["call_order"], 1, []])
    for inv in prepared["invocations"]:
        check("25 the emitted script is the pinned one: " + inv["label"],
              fsha(inv["scriptPath"]), inv["script_sha256"])
    check("26 no result exists yet and the run cannot close",
          [os.path.isdir(os.path.join(RUN, "raw")),
           os.path.isfile(os.path.join(RUN, K.FINALIZATION_NAME)),
           os.path.isdir(os.path.join(RUN, "retry"))], [False, False, False])
    resume = SK.resume_plan(RUN, package=PKG)
    check("27 the real resume path names this run and owes every call",
          [resume["problems"], len(resume["owed"]), len(resume["served"])],
          [[], EXPECTED_SCHEDULED, 0])

# ------------------------------------------------- 4. the preserved bytes ---
check("28 every completed review byte is unchanged",
      tree(REVIEW_UNIT + "/key_closure") == before_tree, True)
import a7_prepared_run as PR                                       # noqa: E402
a3 = PR._executed(os.path.abspath(K.a3_run_dirs()[0]))
check("29 the original answer run is untouched", a3["run_files"], 799)

# ------------------------------------------------------ 5. the frozen record -
record = collections.OrderedDict([
    ("authority", "Codex SEQ 2017 - preparation only, no call is authorized"),
    ("model_calls", 0), ("launched", 0), ("finalized", False),
    ("package", PKG), ("run", RUN),
    ("review_run", REVIEW_RUN), ("review_package", REVIEW_PKG),
    ("map", os.environ["A7_PREP_MAP"]),
    ("map_sha256", fsha(os.environ["A7_PREP_MAP"])),
    ("environment", collections.OrderedDict(
        (name, os.environ.get(name)) for name in (
            "A7_TAG", "A7_PREP_BASE", "A7_LANE_INPUT_PROFILES",
            "A7_SOURCE_CONTEXT", "A7_SOURCE_PROJECTS", "A7_REVIEW_OUT",
            "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "PYTHONDONTWRITEBYTECODE"))),
    ("owners", collections.OrderedDict([
        ("review_composite", fsha(R.__file__.rstrip("c"))),
        ("source_key", fsha(SK.__file__.rstrip("c"))),
        ("final_key", fsha(F.__file__.rstrip("c"))),
        ("clarified_hard_review", fsha(HR.__file__.rstrip("c"))),
        ("source_closure", fsha(CL.__file__.rstrip("c"))),
        ("key_owner_role", fsha(SK.KEY_ROLE_FILE))])),
    ("review_stage", collections.OrderedDict([
        ("run", REVIEW_RUN), ("package", REVIEW_PKG),
        ("receipt_sha256", REVIEW_RECEIPT_PIN),
        ("finalization_sha256", REVIEW_FINALIZATION_PIN),
        ("manifest_sha256", REVIEW_MANIFEST_PIN),
        ("slots", len(merged)),
        ("outcomes", dict(collections.Counter(v[0] for v in merged.values())))])),
    ("package_identity", collections.OrderedDict(
        (name, INV.sha_file(os.path.join(PKG, name)))
        for name in sorted(os.listdir(PKG)))),
    ("receipt_sha256", INV.sha_file(os.path.join(RUN, K.RECEIPT_NAME))),
    ("role", role),
    ("transport", doc.get("requested_key_role")),
    ("counts", doc["counts"]),
    ("coverage", coverage),
    ("budget", budget),
    ("capacity", capacity),
    ("preflight_ok", pre["ok"]),
    ("call_order", doc["call_order"]),
    ("leads_per_source", collections.OrderedDict(
        (sid, len(v)) for sid, v in sorted(proof["by_source"].items()))),
    ("invocations", prepared["invocations"]),
    ("resume", collections.OrderedDict([
        ("owed", len(resume["owed"])), ("served", len(resume["served"])),
        ("problems", resume["problems"])])),
    ("a3_answer_run", collections.OrderedDict([
        ("run", a3_run), ("files", a3["run_files"]),
        ("saved_answers_checked", len(answers))])),
])
record["checks"] = checks
RT.write_new(os.path.join(UNIT, "PREPARED_FINAL_KEY_2017.%s.json"
                          % os.environ["A7_TAG"]),
             json.dumps(record, indent=1, default=str))
print(json.dumps(record, indent=1, default=str))
