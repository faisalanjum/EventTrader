# -*- coding: utf-8 -*-
"""Codex SEQ 2015: prepare the FOUR REAL clarified review requests.

ZERO MODEL CALLS. Nothing historical is written: the original run and package
are served READ-ONLY by this unit's map, and every new byte lands under
A7_PREP_BASE, which the same map binds to this unit alone.

The owners do all the work. This payload only
  * proves which owners and which binding are actually loaded,
  * re-derives the four unsatisfied slots from the real native evidence and
    checks them against the four names Codex named independently,
  * calls R.build and R.prepare_run with EXPLICIT new paths,
  * freezes the transport identity, the capacity/preflight result, every
    prompt / package / receipt / script identity and the call accounting,
  * proves the preserved evidence is byte-unchanged.
"""
import collections
import hashlib
import io
import json
import os
import sys

A7 = "/home/faisal/EventMarketDB-driver-recovery/a7_recovery"
UNIT = os.path.join(A7, "unit_2015_real_reviews")

# --- Codex SEQ 2015's own pins and expectations, checked, never derived here -
COMPOSITE_PIN = "4a93689b5b7d7add223ee4d92c94b7b816871be9e8c10f8bbcf330bb4815aa64"
CLARIFIED_HR_PIN = "ceef0f20e090e0793320fe1def79d958189d715a2dda7ddb48039e9ed6d0cc1b"
EXPECTED_SLOTS = ["sokc-013/b2", "sokc-020/b1", "sokc-026/b1", "sokc-029/b2"]
EXPECTED_A3_ANSWERS = 382
EXPECTED_INITIAL_KEY = 33
EXPECTED_HISTORICAL = 495
EXPECTED_AFTER_PRIMARIES = 499
EXPECTED_WORST_CASE = 503

checks = []


def check(name, got, want):
    assert got == want, "%s: got %r want %r" % (name, got, want)
    checks.append(name)


def fsha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def tree(root):
    """{host path: sha} for every regular file under root."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            if os.path.isfile(path) and not os.path.islink(path):
                out[path] = fsha(path)
    return out


# --------------------------------------------------- 1. the loaded owners ---
sys.path.insert(0, os.path.join(A7, "unit_2009/owner"))
import a4_review_composite as R                                    # noqa: E402

CL, HR, K, SK, F, INV, RT = R.CL, R.HR, R.K, R.SK, R.F, R.INV, R.RT
check("1 the published composite is the loaded owner",
      fsha(R.__file__.rstrip("c")), COMPOSITE_PIN)
check("2 the clarified hard-review owner is the loaded one",
      fsha(HR.__file__.rstrip("c")), CLARIFIED_HR_PIN)
check("3 the rejected unit_2008 composite is not loaded",
      [m for m, mod in sorted(sys.modules.items())
       if getattr(mod, "__file__", None)
       and "unit_2008/owner" in str(mod.__file__)], [])
# a bind mount keeps the mountpoint's name, so the owner's own path proves
# nothing about which tree serves it; the BINDING is what has to be read, and
# the boundary's own validator is what re-measures it.
sys.path.insert(0, "/home/faisal/EventMarketDB-driver-recovery/a4_recovery/regen_1570"
                   "/targeted_1589/post_1500_exact_1626/out/a4_final_lock_1683/launcher")
import boundary                                                    # noqa: E402
rows = {r["logical"]: r for r in boundary.read_map(os.environ["A7_PREP_MAP"])}
served = os.path.dirname(HR.__file__.rstrip("c"))
check("4 the clarified harness is bound read-only from the published tree",
      [rows[served]["source"], rows[served]["mode"],
       boundary.validate([rows[served]])],
      [os.path.join(A7, "unit_2008/harness_g1v3"), "ro", []])
check("5 the preserved owner is the original unit_1997 one",
      os.path.realpath(str(R.OLD_OWNER_PATH)),
      os.path.join(A7, "unit_1997/harness_g1v3/build_kfields_hard_review.py"))
check("5b the original run and package are bound READ-ONLY",
      [[rows[p]["source"], rows[p]["mode"], boundary.validate([rows[p]])]
       for p in (R.OLD_RUN, R.OLD_PKG)],
      [[os.path.join(A7, "unit_2004/key_closure/review_2004"), "ro", []],
       [os.path.join(A7, "unit_2004/key_closure/closure_2004"), "ro", []]])
check("5c every new byte lands in this unit alone",
      [rows[os.path.dirname(R.OLD_RUN)]["source"],
       rows[os.path.dirname(R.OLD_RUN)]["mode"]],
      [os.path.join(UNIT, "key_closure"), "rw"])

# --------------------------------------- 2. the real, not TEST, native store -
a3_run = os.path.abspath(K.a3_run_dirs()[0])
check("6 the saved answers are bound read-only from their durable evidence",
      [rows[a3_run]["mode"], boundary.validate([rows[a3_run]])], ["ro", []])
check("6b nothing in this binding is a TEST or fabricated store",
      [[l for l in rows if l.startswith(boundary.PROJECTS_MOUNT)],
       sorted({r["source"] for r in rows.values() if "TEST" in r["source"]})],
      [[], []])

# ------------------------------------------- 3. the frozen transport identity -
transport = K._transport_block()
runtime = K.RUNTIME_FREEZE
check("7 the frozen transport is Sonnet 5 at high effort",
      [transport["model_alias"], transport["runtime_model_id"],
       transport["effort"]], ["sonnet", "claude-sonnet-5", "high"])
check("8 the required output-token setting is live",
      [runtime["max_output_tokens"], runtime["capacity"]["output_setting_tokens"],
       os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")],
      [128000, 128000, "128000"])
check("9 no api key reaches this process",
      "ANTHROPIC_API_KEY" in os.environ, False)

# --------------------------- 4. the preserved evidence, and what it still owes -
before_tree = tree(os.path.join(A7, "unit_2004/key_closure"))
old, stage = R.old_readings()
check("10 the real native evidence still proves 62 valid and 4 invalid",
      dict(collections.Counter(v[0] for v in old.values())),
      {"valid": 62, "invalid_response": 4})

spent, best = 0, collections.OrderedDict()
for base in (R.OLD_RUN, os.path.join(R.OLD_RUN, "retry")):
    doc = K._load(os.path.join(base, K.FINALIZATION_NAME))
    spent += len(K._load(os.path.join(base, K.RECEIPT_NAME))["allowed"])
    for label, state, why in doc["outcomes"]:
        if best.get(label) != "valid":
            best[label] = state
derived = [label for label, state in best.items() if state != "valid"]
check("11 the old attempts paid for 80 review calls", spent, 80)
check("12 the four unsatisfied slots derive from the old closeouts",
      derived, EXPECTED_SLOTS)

ctx = R._context(old, stage)
check("13 the owner schedules exactly those four", HR._canonical_of(ctx),
      EXPECTED_SLOTS)
check("14 495 historical calls, each stage counted once",
      [ctx["before"], EXPECTED_A3_ANSWERS + EXPECTED_INITIAL_KEY + spent],
      [EXPECTED_HISTORICAL, EXPECTED_HISTORICAL])

# ---------------------------------- 5. same sources, only the wrapper changed -
old_manifest = K._load(os.path.join(R.OLD_PKG, CL.MANIFEST_NAME))
manifest = HR._manifest(ctx)
by_old = {row["task_id"]: row for row in old_manifest["tasks"]}
for row in manifest["tasks"]:
    prior = by_old[row["task_id"]]
    check("15 same source, members and payload: " + row["task_id"],
          [row[k] == prior[k] for k in ("source_id", "members", "payload_sha256")],
          [True, True, True])
    check("16 a new instruction only for the unsatisfied slot: " + row["task_id"],
          row["prompt_sha256"] == prior["prompt_sha256"], False)
check("17 the item instructions are untouched",
      manifest["prefix_item_sha256"], old_manifest["prefix_item_sha256"])
check("18 four primaries, 499 after them, 503 worst case",
      [manifest["budget"][k] for k in
       ("primaries", "after_primaries", "worst_case_after")],
      [4, EXPECTED_AFTER_PRIMARIES, EXPECTED_WORST_CASE])
check("19 the worst case stays inside the global ceiling",
      manifest["budget"]["worst_case_after"] <= ctx["ceiling"], True)

by_label = HR._by_label_of(ctx)
answers = [v[2] for v in old.values() if v[0] == "valid"]
for label in EXPECTED_SLOTS:
    prompt = HR._blind_prompt(ctx, by_label[label][0])
    check("20 no earlier answer is fed back into the request: " + label,
          [a for a in answers if a in prompt], [])

# ------------------------------------------- 6. the fresh package and run ----
BASE = os.environ["A7_PREP_BASE"]
PKG, RUN = os.path.join(BASE, "closure_2015"), os.path.join(BASE, "review_2015")
check("21 the new paths are not a historical directory",
      [os.path.exists(PKG), os.path.exists(RUN),
       PKG == R.NEW_PKG, RUN == R.NEW_RUN], [False, False, False, False])
R.build(PKG)
prepared = R.prepare_run(RUN, PKG)
check("22 preparation passes its own gate",
      [prepared["ok"], prepared["problems"]], [True, []])
preflight = HR._preflight(ctx, PKG)
check("23 preflight is clean", [preflight["ok"], preflight["problems"]],
      [True, []])
receipt = K._load(os.path.join(RUN, K.RECEIPT_NAME))
check("24 the receipt schedules exactly the four slots, attempt one",
      [receipt["allowed"], receipt["attempt"], receipt["parent"],
       receipt["states"]], [EXPECTED_SLOTS, 1, None, []])
check("25 the receipt binds the package that was just built",
      receipt["manifest_sha256"],
      INV.sha_file(os.path.join(PKG, CL.MANIFEST_NAME)))
check("26 the receipt binds the frozen transport", receipt["transport"],
      transport)
check("27 four callable scripts, one per slot",
      [len(prepared["invocations"]),
       [i["label"] for i in prepared["invocations"]],
       sorted({i["attempt"] for i in prepared["invocations"]})],
      [4, EXPECTED_SLOTS, [1]])
for inv in prepared["invocations"]:
    check("28 the emitted script is the pinned one: " + inv["label"],
          fsha(inv["scriptPath"]), inv["script_sha256"])
    check("29 the script carries this slot's exact prompt: " + inv["label"],
          K._sha(HR._blind_prompt(ctx, by_label[inv["label"]][0])),
          receipt["prompts"][inv["label"]])

# ------------------------------------- 7. nothing may close before the calls -
try:
    with R.final_scope(RUN, PKG):
        raise AssertionError("an unfinalized run entered the final-key gate")
except ValueError as exc:
    check("30 an unfinalized run cannot reach the final key",
          "not finalized" in str(exc), True)
check("31 the run is not finalized and holds no result",
      [os.path.isfile(os.path.join(RUN, K.FINALIZATION_NAME)),
       os.path.isdir(os.path.join(RUN, "raw"))], [False, False])

# ------------------------------------------------- 8. the preserved bytes ---
after_tree = tree(os.path.join(A7, "unit_2004/key_closure"))
check("32 every preserved review byte is unchanged",
      [len(after_tree), after_tree == before_tree], [len(before_tree), True])
import a7_prepared_run as PR                                       # noqa: E402
a3 = PR._executed(a3_run)
check("33 the original answer run is untouched", a3["run_files"], 799)

# ------------------------------------------------------ 9. the frozen record -
record = collections.OrderedDict([
    ("authority", "Codex SEQ 2015 - preparation only, no call is authorized"),
    ("model_calls", 0),
    ("package", PKG), ("run", RUN),
    ("map", os.environ["A7_PREP_MAP"]),
    ("map_sha256", fsha(os.environ["A7_PREP_MAP"])),
    ("environment", collections.OrderedDict(
        (name, os.environ.get(name)) for name in (
            "A7_TAG", "A7_PREP_BASE", "A7_LANE_INPUT_PROFILES",
            "A7_SOURCE_CONTEXT", "A7_SOURCE_PROJECTS", "A7_REVIEW_OUT",
            "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "PYTHONDONTWRITEBYTECODE"))),
    ("owners", collections.OrderedDict([
        ("review_composite", fsha(R.__file__.rstrip("c"))),
        ("clarified_hard_review", fsha(HR.__file__.rstrip("c"))),
        ("preserved_hard_review", fsha(str(R.OLD_OWNER_PATH))),
        ("source_closure", fsha(CL.__file__.rstrip("c"))),
        ("source_key", fsha(SK.__file__.rstrip("c"))),
        ("final_key", fsha(F.__file__.rstrip("c"))),
    ])),
    ("preserved", collections.OrderedDict([
        ("run", R.OLD_RUN), ("package", R.OLD_PKG),
        ("receipt_sha256", INV.sha_file(os.path.join(R.OLD_RUN, K.RECEIPT_NAME))),
        ("finalization_sha256",
         INV.sha_file(os.path.join(R.OLD_RUN, K.FINALIZATION_NAME))),
        ("retry_receipt_sha256", INV.sha_file(
            os.path.join(R.OLD_RUN, "retry", K.RECEIPT_NAME))),
        ("retry_finalization_sha256", INV.sha_file(
            os.path.join(R.OLD_RUN, "retry", K.FINALIZATION_NAME))),
        ("manifest_sha256", INV.sha_file(os.path.join(R.OLD_PKG, CL.MANIFEST_NAME))),
        ("files", len(before_tree)),
        ("valid", 62), ("unresolved", derived),
    ])),
    ("package_identity", collections.OrderedDict(
        (name, INV.sha_file(os.path.join(PKG, name))) for name in
        sorted(os.listdir(PKG)))),
    ("receipt_sha256", INV.sha_file(os.path.join(RUN, K.RECEIPT_NAME))),
    ("prompts", collections.OrderedDict(
        (label, receipt["prompts"][label]) for label in EXPECTED_SLOTS)),
    ("counts", manifest["counts"]),
    ("sources", manifest["sources"]),
    ("tasks", [collections.OrderedDict(
        list(row.items())
        + [("prompt_sha256_before", by_old[row["task_id"]]["prompt_sha256"]),
           ("payload_sha256_before", by_old[row["task_id"]]["payload_sha256"])])
        for row in manifest["tasks"]]),
    ("transport", transport),
    ("runtime", collections.OrderedDict([
        ("model_alias", K.MODEL), ("effort", K.EFFORT),
        ("agent_type", K.AGENT_TYPE),
        ("disallowed_tools", list(K.DISALLOWED)),
        ("max_output_tokens", runtime["max_output_tokens"]),
        ("process_max_output_tokens",
         os.environ.get("CLAUDE_CODE_MAX_OUTPUT_TOKENS")),
        ("transport", runtime["transport"]),
        ("entrypoint", runtime["live_proof"]["entrypoint"]),
        ("subscription", runtime["live_proof"]["oauth_subscription_type"]),
        ("runtime_freeze_sha256",
         INV.sha_file(os.path.join(os.path.dirname(HR.__file__.rstrip("c")),
                                   "a2_runtime_freeze.json"))),
    ])),
    ("capacity", manifest["capacity"]),
    ("preflight_ok", preflight["ok"]),
    ("budget", manifest["budget"]),
    ("accounting", collections.OrderedDict([
        ("a3_saved_answers", EXPECTED_A3_ANSWERS),
        ("initial_source_key", EXPECTED_INITIAL_KEY),
        ("review_calls_already_paid", spent),
        ("historical_total", ctx["before"]),
        ("new_primaries", manifest["budget"]["primaries"]),
        ("after_primaries", manifest["budget"]["after_primaries"]),
        ("worst_case_after", manifest["budget"]["worst_case_after"]),
        ("global_ceiling", ctx["ceiling"]),
    ])),
    ("invocations", prepared["invocations"]),
    ("a3_answer_run", collections.OrderedDict([
        ("run", a3_run), ("files", a3["run_files"])])),
    ("launched", 0),
    ("finalized", False),
])
record["checks"] = checks
RT.write_new(os.path.join(UNIT, "PREPARED_REVIEW_2015.%s.json" % os.environ["A7_TAG"]),
             json.dumps(record, indent=1, default=str))
print(json.dumps(record, indent=1, default=str))
