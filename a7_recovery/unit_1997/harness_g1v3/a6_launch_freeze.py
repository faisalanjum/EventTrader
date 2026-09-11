"""A6: freeze the exact EXP-5 producer launch. Codex SEQ 1408 + 1409.

ONE owner, ONE artifact. Everything is DERIVED from a prepared A5 run and the
existing owners; nothing here is typed, and nothing here calls a model, arms a
grader, or executes a launcher.

The freeze is self-verifying: `problems(doc)` rederives every recorded value
from the same live files and returns why the document is not the launch it
claims to describe.
"""
import collections
import hashlib
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _g7():
    """`a7_g1_build` - and it MUST be this directory's copy, the mirror of
    a7_g1_build._a6 (Codex SEQ 1489 item E). This owner imports it lazily,
    so whichever copy an earlier sys.path entry preloaded would otherwise be
    used silently: a stale copy has a different history and different
    counts. Refuse rather than repair."""
    import a7_g1_build as mod
    got = os.path.dirname(os.path.abspath(mod.__file__))
    if got != _HERE:
        raise RuntimeError(
            "a7_g1_build resolved to %s, not the harness copy in %s; run from "
            "one clean harness path" % (mod.__file__, _HERE))
    return mod
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import build_a5_exp5_kit as A5                                   # noqa: E402
import build_kfields_final as F                                  # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402
import raw_transport as RT                                       # noqa: E402
import a1_reader                                                 # noqa: E402

K = F.K

#: The scratch pointers that already name every A4 phase run directory. The
#: ledger owners read these same files; the freeze binds them so the total can
#: be recomputed from the exact evidence rather than trusted as a number.
# THE ONE EVIDENCE-ROOT OWNER, not a second copy of it. This restated an
# absolute path carrying one Claude session id, so the freeze could only be
# rebuilt inside that session; `build_kfields_key.EVIDENCE` already names the
# root once and honours KFIELDS_EVIDENCE.
_PTR = K.EVIDENCE
LEDGER_POINTERS = ("a4_dir.txt", "hr_dir.txt", "hrfix_dir.txt", "final_dir.txt",
                   "corr_dir.txt", "decision_dir.txt", "v4_dir.txt",
                   "v5_dir.txt", "v6_dir.txt", "signer_dir.txt",
                   "targeted_dir.txt", "hard_review_targeted_dir.txt",
                   "final_targeted_dir.txt", "final_targeted_corr_dir.txt",
                   "final_targeted_corr2_dir.txt", "final_targeted_corr3_dir.txt")

#: Arms that must be provably ABSENT from an A6 launch. Named once so the
#: freeze records an explicit absence instead of an unstated assumption.
FORBIDDEN_ARMS = ("opus", "haiku", "qwen", "gpt", "deepseek", "fallback",
                  "escalation")

FREEZE_NAME = "a6_exp5_launch_freeze.json"
SCHEMA = "a6-exp5-launch-freeze-v1"

#: A7's grader batch owner. It does not exist yet and A6 does not create it:
#: the freeze names it so A7 cannot silently invent a different one.
GRADER_BATCH_OWNER = "grade_batch.js"

#: the retry child's directory name, from the transport owner
RETRY_DIRNAME = "retry"


def _read_ptr(name):
    with io.open(os.path.join(_PTR, name), encoding="utf-8") as fh:
        return fh.read().strip()


def _sha_file(path):
    with io.open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def bound():
    """The A4 phase runs, from the pointer files the ledger owners already use."""
    pkg = os.path.join(os.path.dirname(_HERE), "kfields_final")
    return F.Bound(pkg, _read_ptr("a4_dir.txt"), _read_ptr("hr_dir.txt"),
                   _read_ptr("hrfix_dir.txt"), _read_ptr("final_dir.txt"),
                   _read_ptr("corr_dir.txt"), _read_ptr("decision_dir.txt"),
                   _read_ptr("v4_dir.txt"), _read_ptr("v5_dir.txt"),
                   _read_ptr("v6_dir.txt"))


def _validated_attempts(run_dir):
    """Every FINALIZED attempt of one run, through the SAME validators the
    prepared-run identity uses (Codex SEQ 1473 item 3).

    Reading any present `finalization.json` and trusting its ledger let a
    corrupted or substituted record move the call ceiling. These are the exact
    receipt and finalization owners `a7_prepared_run.load` calls - not a second
    set of rules.

    They are called HERE rather than through `a7_prepared_run.load` because
    that owner builds the A6 freeze, and the freeze budgets its own run: going
    through it would be `ledger -> load -> freeze -> budget -> ledger`.
    """
    import raw_transport as RT
    out = []
    # THE PLAN, ERA AND RECEIPT FIRST. Returning early on a missing
    # finalization accepted ANY directory - an empty or malformed plan was
    # counted as a lawful zero-call run (Codex SEQ 1474 item 3).
    # NO ERA RULE HERE. The ledger counts VALIDATED calls from every era -
    # that is what a completed-call ledger is - and owning a second current-era
    # rule beside `PR.current` made loading any historical identity refuse,
    # because an identity load budgets its own run (Codex SEQ 1475).
    plan = RT.a1_plan_for_run(run_dir)
    rpath = os.path.join(run_dir, "receipt.json")
    if not os.path.isfile(rpath):
        # NAMED, not a bare FileNotFoundError: a directory with no receipt is
        # not a prepared run, and must not read as a lawful zero-call one.
        raise ValueError("%s has no receipt, so it is not a prepared run and "
                         "cannot be counted" % run_dir)
    receipt = K._load(rpath)
    bad = RT.a1_run_contract_problems(receipt, run_dir, plan)
    if bad:
        raise ValueError("%s: the receipt does not hold: %s"
                         % (run_dir, bad[:2]))
    ppath = os.path.join(run_dir, K.FINALIZATION_NAME)
    if not os.path.isfile(ppath):
        return out                      # a LAWFUL zero-call run, now proved so
    pf = K._load(ppath)
    bad = RT.a1_finalization_problems(pf, plan, run_dir, 1)
    if bad and pf.get("audit_problems"):
        # A REFUSED CLOSEOUT IS STILL A CLOSEOUT. Its completed calls were paid
        # whether or not the run is selectable for scoring, so the audit
        # refusal alone may not hide them from the ledger - but every OTHER
        # binding must still hold, proved by the same validator over the same
        # document with only that one field cleared (Codex SEQ 1482 item 4).
        bad = RT.a1_finalization_problems(dict(pf, audit_problems=[]), plan,
                                          run_dir, 1)
    if bad:
        raise ValueError("%s: the primary finalization does not hold: %s"
                         % (run_dir, bad[:2]))
    out.append((run_dir, "primary", pf, _sha_file(ppath)))

    owed = [tuple(c) for c in pf.get("retry") or []]
    rdir = os.path.join(run_dir, RETRY_DIRNAME)
    rpath = os.path.join(rdir, K.FINALIZATION_NAME)
    if os.path.isfile(rpath):
        bad = RT.a1_run_contract_problems(
            K._load(os.path.join(rdir, "receipt.json")), rdir, plan)
        if bad:
            raise ValueError("%s: the retry receipt does not hold: %s"
                             % (rdir, bad[:2]))
        rf = K._load(rpath)
        bad = RT.a1_finalization_problems(rf, plan, rdir, 2, owed)
        if bad:
            raise ValueError("%s: the retry finalization does not hold: %s"
                             % (rdir, bad[:2]))
        out.append((rdir, "retry", rf, _sha_file(rpath)))
    return out


def precall_view(frozen, run_dir):
    """The accepted PRE-LAUNCH identity of a freeze whose run has since executed.

    A6 is a pre-launch guard, so `freeze()` reflects the live run: once it has
    lawfully spent calls, its zeros, receipt-file hash and completed-ledger
    budget differ from the accepted pre-call freeze, and the identity pin over
    the live bytes would refuse the very run it accepted (Codex SEQ 1521). This
    reconstructs that ONE accepted identity from the run's OWN immutable
    evidence - resetting only the fields execution changes, every launch binding
    untouched: the receipt file's mutable `states` are emptied to the published
    receipt, the spent-state counters return to zero, and the budget is the
    plan's own baseline projection (`budget(schedule, None)`), which counts the
    schedule once and never re-adds the returned calls as a future plan. It is
    a no-op on a run that has not executed, and it invents no second serializer
    or ledger - it renders through A6 and counts through the one ledger.
    """
    import copy
    view = copy.deepcopy(frozen)
    view["zeros"]["states"] = 0
    view["zeros"]["raw_replies"] = 0
    receipt = dict(json.load(io.open(os.path.join(run_dir, "receipt.json"),
                                     encoding="utf-8")))
    receipt["states"] = []
    view["bound_artifacts"]["receipt_sha256"] = hashlib.sha256(
        RT.receipt_bytes(receipt)).hexdigest()
    view["budget"] = budget(view["counts"]["ordered_producer_calls"], None)
    return view


#: the five V1-V5 phases the lock pins, to the five existing `Bound` fields.
#: Measured against the lock's own receipt hashes, not assumed.
_HISTORY_FIELDS = (("v1", "events"), ("v2", "corrections"),
                   ("v3", "decision"), ("v4", "decision_correction"),
                   ("v5", "decision_correction_v5"))


def _locked_rows():
    """ONE structural row: the closed A4 answer key, from the SIGNED FINAL A4
    lock (Codex SEQ 1515). The retired V6 per-phase walk is gone - the final
    lock seals every A4-era call and A5.a4_lock() already refuses any mutation
    of the lock or its receipt (LOCKED, signed, blocked [], receipt binds
    these exact bytes, every bound value refuses). A4 is never re-walked; its
    call_accounting.ledger_after is the closed baseline. Row shape unchanged:
    (stage, run, calls, receipt_sha, finalization_sha).
    """
    import build_a5_exp5_kit as A5
    lock = A5.a4_lock()
    acc = lock["call_accounting"]
    return [("a4_final_key", lock["signer"]["run_id"], acc["ledger_after"],
             A5.A4_LOCK_SHA, A5.A4_LOCK_RECEIPT_SHA)]


def ledger(run_dir=None):
    """THE completed call total. The signed final A4 lock's own accounting is
    the closed A4 baseline (Codex SEQ 1515); A4 history is NOT re-walked here,
    and there is NO producer history in the baseline - PRODUCER_HISTORY, the
    all_prior_calls walk and the V6 walk are gone (Codex SEQ 1516).

    Post-lock spend is added ONLY when a `run_dir` is supplied: each validated,
    actually-returned primary/retry attempt of that ONE run is counted exactly
    once as `current_producer_*`. Ignoring `run_dir` (the SEQ 1515 regression)
    let the real producer calls read as the bare baseline. Before any producer
    call the total is the lock's own ledger_after, the lock its single row.
    """
    rows, total = [], 0
    for stage, run, calls, receipt_sha, fin_sha in _locked_rows():
        total += calls
        rows.append(collections.OrderedDict([
            ("stage", stage), ("run_dir", run),
            ("receipt_sha256", receipt_sha),
            ("finalization_sha256", fin_sha), ("calls", calls)]))
    if run_dir is None:
        return total, rows

    # THE SUPPLIED RUN, THROUGH THE SAME VALIDATORS the prepared-run identity
    # uses (`_validated_attempts`): a missing/malformed receipt or finalization
    # refuses by name before a single call is counted.
    run_dir = os.path.abspath(run_dir)
    for base, kind, fin, fin_sha in _validated_attempts(run_dir):
        # `_validated_attempts` returns each attempt of the one run exactly
        # once (primary, then a finalized retry if owed), so the supplied run's
        # spend is counted once with no dedup set - the cross-history double
        # reach that needed one is gone with PRODUCER_HISTORY (Codex SEQ 1516).
        # THE ROWS THE OFFICIAL STATE RETURNED, bound to the raw tree the
        # closeout preserved from them - never the schedule: a refused partial
        # run scheduled its whole plan and spent only what came back (Codex SEQ
        # 1482 item 4). Equal counts proved nothing (Codex SEQ 1483), so the
        # transport's one binding owner verifies every filename and every byte
        # before a single call is added.
        returned = RT.a1_readable_rows(
            K._load(os.path.join(base, "receipt.json")).get("states"))
        bad = RT.a1_raw_binding_problems(base, returned, fin["attempt"])
        if bad:
            raise ValueError("%s: the preserved raw tree is not the official "
                             "returned rows, so this run's spend cannot be "
                             "counted: %s" % (base, bad[:2]))
        raw = F.raw_tree(base)
        calls = len(returned)
        total += calls
        rows.append(collections.OrderedDict([
            ("stage", "current_producer_%s" % kind), ("run_dir", base),
            ("finalization_sha256", fin_sha),
            ("raw_tree", raw["sha256"]), ("calls", calls)]))
    return total, rows

def _remaining_primary(schedule, rows):
    """The primary calls STILL OWED: the primary schedule minus the run's OWN
    validated `current_producer_primary` calls, measured from ledger rows.

    Only primary is subtracted. A completed retry lives in `completed_actual`
    and must never reduce primary work a second time - the class bug was
    subtracting every post-lock call (primary + retry), giving P-(P+R) = -R and
    hiding the retry spend (Codex SEQ 1522 item 1). An impossible count - more
    validated primary than the schedule - refuses rather than returning a
    negative plan.
    """
    done = sum(r["calls"] for r in rows
               if r.get("stage") == "current_producer_primary")
    if done > schedule:
        raise ValueError(
            "recorded %d validated primary calls, above the %d-call primary "
            "schedule" % (done, schedule))
    return schedule - done


def budget(planned, run_dir=None, measured=None):
    """Derived budget. `planned` is the FUTURE primary call count, itself
    derived. `measured`, when given, is an already-computed `(completed, rows)`
    from the ONE ledger, so a caller that has measured to derive `planned` need
    not measure the same run twice (Codex SEQ 1522 item 1)."""
    completed, rows = ledger(run_dir) if measured is None else measured
    return collections.OrderedDict([
        ("completed_actual", completed),
        ("provenance", rows),
        ("a3_measured_baseline", K.ledger_before()),
        ("planned_producer_primary", planned),
        ("producer_primary_after", completed + planned),
        ("global_abort_ceiling", F.GLOBAL_CEILING),
        ("under_ceiling", completed + planned <= F.GLOBAL_CEILING),
        ("rule", "every future actual call, including each retry and each "
                 "grader sublaunch, is checked against the global ceiling "
                 "before it is armed"),
        ("retry_rule", "only a model-invalid/invalid-JSON reply earns the one "
                       "canonical attempt-2 subset; a valid sibling, a refusal "
                       "and an integrity failure never do, and attempt 2 can "
                       "never create attempt 3")])


def grader_staging():
    """The grader ANSWER inventory, in the dependency order Codex SEQ 1409
    ruling 1 fixed. A6 arms ZERO grader calls: none of these counts exists
    before the producer replies do.
    """
    src = os.path.join(_HERE, "scorers", "score_exp5.py")
    return collections.OrderedDict([
        ("armed_grader_calls", 0),
        ("count_is_derivable_now", False),
        ("why", "every class below is a function of producer output, and no "
                "producer call has been made"),
        ("stages", [
            collections.OrderedDict([
                ("stage", "G1_identity"),
                ("owner", "score_exp5.grade_unmatched"),
                ("question", "every unmatched gold row produced by the "
                             "deterministic matcher, ruled against that "
                             "event/arm's unmatched produced rows"),
                ("key", "(source_id, gold_idx)"),
                ("none_means", "a decided miss, which still counts against "
                               "recall")]),
            collections.OrderedDict([
                ("stage", "reconcile"),
                ("owner", "score_exp5.reconcile_rulings"),
                ("question", "two blind independent grader answers; ONLY "
                             "agreement becomes a ruling")]),
            collections.OrderedDict([
                ("stage", "G2_meaning"),
                ("owner", "score_exp5.score_arm"),
                ("question", "every FINAL matched pair - direct deterministic "
                             "links plus agreed G1 links - receives every "
                             "required MEANING_FIELDS verdict"),
                ("key", "(source_id, gold_idx)"),
                ("meaning_fields", list(_meaning_fields()))]),
            collections.OrderedDict([
                ("stage", "G3_extras"),
                ("owner", "score_exp5.classify_extras"),
                ("question", "every route-accepted produced row still "
                             "unmatched after G1"),
                ("key", "(source_id, produced_idx)"),
                ("buckets", list(_extras_buckets()))])]),
        ("inventory", "the exact union of G1 + G2 + G3, derived by those "
                      "existing scorer owners; it is NOT reducible to the "
                      "unresolved rows"),
        ("batching", "the live scorer owns QUESTIONS, not batching; "
                     "'2*N answers' does not imply '2*N calls'"),
        ("scorer_owner_sha256", _sha_file(src)),
        ("a7_boundary", collections.OrderedDict([
            ("batch_owner", GRADER_BATCH_OWNER),
            ("batch_owner_present_now", os.path.isfile(
                os.path.join(_HERE, GRADER_BATCH_OWNER))),
            ("order", "G1 must COMPLETE before the final G2/G3 inventory is "
                      "frozen"),
            ("then", "A7 builds the smallest exact grader batch packet from "
                     "that owner, hash-freezes its batch count, and only then "
                     "runs exactly two blind independent Sonnet-5/high calls "
                     "per nonempty batch"),
            ("ceiling", F.GLOBAL_CEILING)]))])


def _matcher_path():
    """The matcher lives in the driver package, not the harness."""
    from driver.core import fact_match
    return os.path.abspath(fact_match.__file__)


def _meaning_fields():
    from scorers import score_exp5
    return tuple(score_exp5.MEANING_FIELDS)


def _extras_buckets():
    from scorers import score_exp5
    return tuple(score_exp5.EXTRAS_BUCKETS)


def _launchers(run_dir, plan):
    """Every ORDERED launcher identity, armed and unarmed, from this run."""
    rows = []
    for inv in json.load(io.open(os.path.join(run_dir, "receipt.json"),
                                 encoding="utf-8"))["invocations"]:
        armed = inv["scriptPath"]
        name = os.path.basename(armed)
        # THE UNARMED TEMPLATE is persisted by its source id, not the armed
        # call name: persist_launchers writes "<PREFIX><sid>.workflow.js" while
        # the armed launcher is "<PREFIX><sid>.attempt1.js", so looking it up by
        # the armed basename bound None for every launcher (Codex SEQ 1515).
        unarmed = os.path.join(run_dir, RT.PLAN_DIRNAME, A5.LAUNCHER_DIRNAME,
                               "%s%s.workflow.js" % (A5.LAUNCHER_PREFIX,
                                                     inv["source_id"]))
        if not os.path.isfile(unarmed):
            raise ValueError("%s: the unarmed launcher template is missing at %s"
                             % (inv["source_id"], unarmed))
        rows.append(collections.OrderedDict([
            ("source_id", inv["source_id"]), ("launcher", name),
            ("armed_sha256", _sha_file(armed)),
            ("unarmed_sha256", _sha_file(unarmed))]))
    return rows


def freeze(run_dir):
    """THE A6 freeze document, derived entirely from a prepared A5 run."""
    run_dir = os.path.abspath(run_dir)
    plan = RT.a1_plan_for_run(run_dir)
    manifest_path, prefix = RT.a1_plan_identity(plan)
    receipt = json.load(io.open(os.path.join(run_dir, "receipt.json"),
                                encoding="utf-8"))
    calls = [tuple(c) for c in receipt["allowed"]]
    a2 = plan["a2_runtime_freeze"]
    lock = A5.a4_lock()
    arms = [a["arm"] for a in plan["arms"]]
    backmap = os.path.join(run_dir, "a5_menu_backmap.json")
    # THE ONE LEDGER MEASUREMENT for this run, reused for both the remaining
    # primary plan and the budget it feeds (Codex SEQ 1522 item 1).
    measured = ledger(run_dir)
    remaining_primary = _remaining_primary(len(calls), measured[1])

    return collections.OrderedDict([
        ("schema", SCHEMA),
        ("phase", "A6 - freeze the exact EXP-5 producer launch"),
        ("prepared_run", run_dir),
        ("a4_lock", collections.OrderedDict([
            ("path", A5.A4_LOCK_PATH), ("sha256", A5.A4_LOCK_SHA),
            ("receipt_path", A5.a4_lock_receipt_path()),
            ("receipt_sha256", A5.A4_LOCK_RECEIPT_SHA),
            ("schema", lock["schema"]), ("state", lock["state"]),
            ("signed", lock["signer"]["signed"]),
            ("events", lock["key"]["events"]),
            ("ledger_after", lock["call_accounting"]["ledger_after"])])),
        ("bound_artifacts", collections.OrderedDict([
            ("manifest_path", manifest_path),
            ("manifest_sha256", _sha_file(manifest_path)),
            ("bundle_path", plan["bundle_path"]),
            ("bundle_sha256", plan["bundle_sha256"]),
            ("receipt_sha256", _sha_file(os.path.join(run_dir,
                                                      "receipt.json"))),
            ("menu_backmap_sha256", _sha_file(backmap)),
            ("prompt_sha256", plan["prompt_sha256"]),
            ("input_sha256", plan["bound_inputs"]["event_source_sha256"]),
            ("inventory_sha256", plan["bound_inputs"]["inventory_sha256"]),
            ("owners", plan["owners"]),
            ("scorer_sha256", _sha_file(os.path.join(_HERE, "scorers",
                                                     "score_exp5.py"))),
            ("matcher_sha256", _sha_file(_matcher_path())),
            ("reader_sha256", a1_reader.owner_sha256()),
            ("launcher_prefix", prefix),
            ("launchers", _launchers(run_dir, plan))])),
        ("counts", collections.OrderedDict([
            ("events", len(plan["events"])),
            ("packets", len(plan["packets"])),
            ("arms", arms),
            ("lanes_per_packet", sorted({len(p["lanes"])
                                         for p in plan["packets"]})),
            ("ordered_producer_calls", len(calls)),
            ("unique_ordered_calls", len(set(calls))),
            ("invocations", len(receipt["invocations"])),
            ("capacity", plan["capacity"])])),
        ("transport", collections.OrderedDict([
            ("runtime_model_id", a2["runtime_model_id"]),
            ("effort", a2["effort"]), ("agentType", a2["agentType"]),
            ("disallowedTools", a2["disallowedTools"]),
            (BLM.OUTPUT_TOKENS_VAR, a2[BLM.OUTPUT_TOKENS_VAR]),
            ("transport", a2["transport"]), ("door", plan["door"]),
            ("a2_freeze_sha256", A5.A2_FREEZE_SHA)])),
        ("absent_arms", collections.OrderedDict(
            (name, False) for name in FORBIDDEN_ARMS)),
        ("zeros", collections.OrderedDict([
            ("states", len(receipt.get("states") or [])),
            ("raw_replies", len(os.listdir(os.path.join(run_dir, "raw")))
             if os.path.isdir(os.path.join(run_dir, "raw")) else 0),
            ("made_calls", plan["made_calls"]),
            ("database_writes", 0), ("activated", False)])),
        # THE RUN THIS FREEZE IS ABOUT, through the same budget owner. The
        # `planned` is the primary schedule NOT YET SPENT: only this run's
        # validated PRIMARY calls are subtracted, so a completed retry stays in
        # `completed_actual` and is never subtracted from primary work twice
        # (Codex SEQ 1522 item 1). Pre-launch this is the whole schedule;
        # post-run it is zero. One ledger measurement, one budget owner.
        ("budget", budget(remaining_primary, measured=measured)),
        ("grader", grader_staging()),
    ])


def render(doc):
    """The ONE serialization, so two builds cannot differ by formatting."""
    return json.dumps(doc, indent=1, sort_keys=True)


def problems(doc):
    """Why this document is not the launch it says it is. Empty = it rederives.

    Every check REDERIVES from the live files; nothing is compared against
    another field of the same document, because a document that only agrees
    with itself proves nothing.
    """
    bad = []
    if not isinstance(doc, dict):
        return ["the freeze is %s, not an object" % type(doc).__name__]
    run = doc.get("prepared_run")
    if not (isinstance(run, str) and os.path.isdir(run)):
        return ["the freeze names no prepared run directory on disk"]
    try:
        live = freeze(run)
    except Exception as exc:                          # noqa: BLE001 - by design
        return ["the freeze cannot be rederived from %s: %s" % (run, exc)]

    # the budget provenance is time-invariant only if the SAME files are read,
    # so it is compared whole, exactly like every other block
    for key in sorted(set(live) | set(doc)):
        if key not in doc:
            bad.append("the freeze is missing the %r block" % key)
        elif key not in live:
            bad.append("the freeze carries %r, which nothing rederives" % key)
        elif doc[key] != live[key]:
            bad.append("%s does not rederive from the live launch" % key)

    if not bad:
        b = doc["budget"]
        if b["completed_actual"] + b["planned_producer_primary"] \
                != b["producer_primary_after"]:
            bad.append("the budget arithmetic does not close")
        if b["producer_primary_after"] > b["global_abort_ceiling"]:
            bad.append("the planned launch exceeds the global ceiling")
        c = doc["counts"]
        if c["ordered_producer_calls"] != c["unique_ordered_calls"]:
            bad.append("the ordered call list contains a duplicate")
        if c["ordered_producer_calls"] != c["packets"] * len(c["arms"]):
            bad.append("the call count is not packets x arms")
        if any(doc["absent_arms"].values()):
            bad.append("an arm recorded as absent is present")
        if any(doc["zeros"][k] for k in ("states", "raw_replies", "made_calls",
                                         "database_writes")):
            bad.append("this launch has already spent something")
        if doc["zeros"]["activated"]:
            bad.append("the launch is recorded as activated")
        if doc["grader"]["armed_grader_calls"] != 0:
            bad.append("A6 armed a grader call")
    return bad


def write(run_dir, dest_dir):
    """Persist the freeze. Returns (path, sha256)."""
    doc = freeze(run_dir)
    text = render(doc)
    path = os.path.join(dest_dir, FREEZE_NAME)
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    with io.open(path + ".tmp", "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(path + ".tmp", path)
    return path, hashlib.sha256(text.encode("utf-8")).hexdigest()
