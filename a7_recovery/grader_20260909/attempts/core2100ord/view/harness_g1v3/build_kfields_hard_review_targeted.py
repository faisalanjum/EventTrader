"""THE FROZEN A4 DOUBLE-BLIND REVIEW OF THE CORRECTED ITEMS (Codex SEQ 1492 B/C).

build_kfields_hard_review owns the ONE hard-review lifecycle - prompt, manifest,
package identity, receipt, official-state proof, raw-first write-once
finalizer, parser, invalid-only child, no third attempt - over a small private
context. This module supplies that context, fixed, and nothing else:

  * the population is the COMPLETE corrected-inventory diff, one located item
    per task, in the diff's order - never caller-supplied ids;
  * each task is read by exactly the owner's two independent blind calls;
  * the calls see the CURRENT v3 rules/output owners, the readable menu, the
    complete event and the corrected located item last; no A3 draft, no
    targeted reply, no ruling, no key, no sibling;
  * the budget is bound by hash to the current derived budget receipt, so
    completed-before, after-primary, worst case and ceiling are read from
    owners, never typed here;
  * ONE public prepare door and the shared finalize/record_state.

No model is called by this module; nothing here reads the key.
"""
import collections
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import build_kfields_hard_review as HR                           # noqa: E402
import build_kfields_key as K                                    # noqa: E402
import build_kfields_key_targeted as T                           # noqa: E402
import build_launch_manifest as BLM                              # noqa: E402
import raw_transport as RT                                       # noqa: E402

INV = K.INV
C = K.C
ORIGIN = "source_correction"
#: THE contract version the blind calls read: the current producer era
SUFFIX = BLM.PRODUCER_CONTRACT_SUFFIX
PKG_DIR = os.path.join(K._X, "kfields_key_a4", "hard_review_targeted_1493")
#: the current derived budget receipt this stage's numbers are bound to
BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1493.json"


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def items():
    """The corrected located items, by key (the targeted owner's binding)."""
    return {i["packet_id"]: i for i in T.targeted_items()}


def tasks():
    """One item task per corrected record, in the diff's order."""
    out = []
    for n, pid in enumerate(T.targets()):
        out.append(collections.OrderedDict([
            ("task_id", "hrt-%03d" % n), ("kind", "item"),
            ("origin", ORIGIN), ("members", [pid])]))
    return out


def population_problems(built):
    """The population is exactly the complete diff, once each, in order."""
    want = [[pid] for pid in T.targets()]
    bad = []
    if [t["members"] for t in built] != want:
        bad.append("the tasks are not the complete corrected diff in order")
    if [t["task_id"] for t in built] != ["hrt-%03d" % n for n in range(len(want))]:
        bad.append("the task ids are not the derived ones")
    if any(t["kind"] != "item" or t["origin"] != ORIGIN for t in built):
        bad.append("a task is not a one-item source-correction task")
    return bad


def _targeted_run():
    """The targeted key-review run this review is independent of, as
    provenance: THE one immutable binding, by path and hash (Codex SEQ 1493);
    its identities are never copied here, and never shown to a call."""
    return collections.OrderedDict([
        ("binding_path", T.BINDING),
        ("binding_sha256", INV.sha_file(T.BINDING)),
        ("run_dir", _load(T.BINDING)["run_dir"])])


def _derived_from():
    return collections.OrderedDict([
        ("key_owner_sha256", INV.sha_file(os.path.join(_HERE, "build_kfields_key.py"))),
        ("targeted_owner_sha256", INV.sha_file(
            os.path.join(_HERE, "build_kfields_key_targeted.py"))),
        ("hard_review_owner_sha256", INV.sha_file(
            os.path.join(_HERE, "build_kfields_hard_review.py"))),
        ("frozen_inventory_sha256", INV.sha_file(INV.INV)),
        ("corrected_inventory_sha256", INV.sha_file(T.CORRECTED_INVENTORY)),
        ("correction_receipt_sha256", INV.sha_file(T.CORRECTION_RECEIPT)),
        ("targets", T.targets()),
        ("contract_package_sha256", INV.sha_file(C.package_path(SUFFIX))),
        ("targeted_binding", _targeted_run())])


def _ctx():
    """THE complete package context this module serves."""
    receipt = _load(BUDGET_RECEIPT)
    return {"items": items(), "tasks": tasks(), "suffix": SUFFIX,
            "derived_from": _derived_from(),
            "before": receipt["completed_before"],
            "ceiling": receipt["ceiling"],
            "budget_receipt": INV.sha_file(BUDGET_RECEIPT),
            "authority": "Codex SEQ 1492",
            "step": "live Step 1 A4 - the double-blind review of the "
                    "eleven corrected items"}


def prompt_prefix(kind):
    return HR._prompt_prefix(SUFFIX, kind)


def blind_prompt(task):
    return HR._blind_prompt(_ctx(), task)


def render_launcher(task, blind, attempt=1):
    return HR._render_launcher(_ctx(), task, blind, attempt)


def canonical_calls():
    return HR._canonical_of(_ctx())


def manifest():
    """The complete manifest; the population is proved first. Writes nothing."""
    ctx = _ctx()
    bad = population_problems(ctx["tasks"])
    if bad:
        raise ValueError("population refused: %s" % bad[:3])
    return HR._manifest(ctx)


def build(out_dir):
    """Write the frozen package ONCE. Launches nothing, calls nothing."""
    doc = manifest()
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    text = json.dumps(doc, indent=1)
    RT.write_new(os.path.join(out_dir, HR.MANIFEST_NAME), text)
    RT.write_new(os.path.join(out_dir, "prompt_prefix_item.txt"),
                 prompt_prefix("item"))
    doc["manifest_sha256"] = K._sha(text)
    return doc


def package_problems(pkg_dir):
    """The whole rebuilt manifest and the shipped prefix against the package."""
    ctx = _ctx()
    bad = population_problems(ctx["tasks"])
    if bad:
        return bad
    return HR._package_problems(ctx, pkg_dir)


def prompt_order_problems():
    return HR._prompt_order_problems(_ctx())


def preflight():
    return HR._preflight(_ctx(), PKG_DIR)


def prepare_run(out_dir):
    """THE ONE public door: the whole package must rebuild identically and
    pass the shared gate, then the shared receipt owner publishes exactly the
    frozen calls, in order."""
    bad = package_problems(PKG_DIR)
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    return HR._prepare_run(_ctx(), out_dir, PKG_DIR)


def finalize(out_dir):
    """The shared raw-first, write-once finalizer over this context."""
    return HR._finalize(_ctx(), out_dir, PKG_DIR)


record_state = HR.record_state


# ------------------------------------ the completed run, bound and counted --
# Codex SEQ 1496 item 1: the targeted-run binding/pointer pattern, reused over
# THIS lifecycle. The immutable binding decides which attempts exist and what
# their receipt, finalization, every raw/proved file and canonical raw tree
# ARE; then everything is re-proved through the shared owners before ONE spend
# row per attempt is returned. a6_launch_freeze.ledger() only records that row.
import build_kfields_final as F                                  # noqa: E402

#: THE IMMUTABLE HARD-REVIEW EVIDENCE BINDING, beside the run pointer
BINDING = os.path.join(K.EVIDENCE, "hard_review_targeted_binding.json")
BINDING_SCHEMA = "a4-hard-review-targeted-evidence-binding/1"
#: the outcomes a finalized, complete attempt may carry (the shared law)
_FINAL_OUTCOMES = ("valid", "invalid_response", "transport_no_answer")


def _measured_attempt(base, attempt):
    """The exact identity of one finalized attempt directory, measured: the
    targeted owner's receipt/finalization/every-raw-file identity PLUS the
    canonical raw-tree digest of the one owner that defines it."""
    row = T._measured_attempt(base, attempt)
    row["raw_tree"] = F.raw_tree(base)
    return row


def write_binding(run_dir):
    """Freeze the accepted run ONCE: its primary and, when present, its one
    child. Write-once through the transport's owner; never rewritten."""
    run_dir = os.path.abspath(run_dir)
    attempts = [_measured_attempt(run_dir, 1)]
    child = os.path.join(run_dir, "retry")
    if os.path.isdir(child):
        attempts.append(_measured_attempt(child, HR.MAX_ATTEMPTS))
    doc = collections.OrderedDict([("schema", BINDING_SCHEMA),
                                   ("run_dir", run_dir),
                                   ("attempts", attempts)])
    RT.write_new(BINDING, json.dumps(doc, indent=1))
    return doc


def _derived_outcome(ctx, label, state, text):
    """What THIS lifecycle says one proved call is - re-derived, never read."""
    if state == "transport_no_answer":
        return "transport_no_answer"
    _obj, bad = HR._read_reply(ctx, text, HR._by_label_of(ctx)[label][0])
    return "valid" if not bad else "invalid_response"


def proved_spend(run_dir):
    """READ-ONLY. The calls the FINALIZED double-blind run actually spent,
    re-proved through this lifecycle's own context and the shared owners:
    binding identity (receipt, finalization, every raw/proved byte, canonical
    raw tree), the receipt through HR._receipt_problems, the finalization
    binding that receipt and closed clean and complete, every official state
    through HR._run_evidence, every stored raw and proved byte equal to the
    official text, every outcome RE-DERIVED and equal to the stored one, the
    allowed identities served exactly once, the raw tree holding exactly the
    preserved files, and the child owed by the outcomes owned by the binding.
    Any missing, foreign, unexpected or tampered byte refuses the WHOLE spend.
    -> [{run_dir, attempt, receipt_sha256, finalization_sha256, raw_tree,
         raw_files, calls}]"""
    ctx = _ctx()
    binding = _load(BINDING)
    if binding.get("schema") != BINDING_SCHEMA or \
            binding.get("run_dir") != os.path.abspath(run_dir):
        raise ValueError("%s is not the bound hard-review run %s"
                         % (run_dir, binding.get("run_dir")))
    bound = {a["attempt"]: a for a in binding["attempts"]}
    present = [1] + ([HR.MAX_ATTEMPTS] if os.path.isdir(
        os.path.join(run_dir, "retry")) else [])
    if sorted(bound) != present:
        raise ValueError("%s carries attempts %s; the binding owns %s"
                         % (run_dir, present, sorted(bound)))
    rows = []
    for attempt in sorted(bound):
        base = bound[attempt]["dir"]
        rec_path = os.path.join(base, HR.RECEIPT_NAME)
        fin_path = os.path.join(base, HR.FINALIZATION_NAME)
        for p in (rec_path, fin_path):
            if not os.path.isfile(p):
                raise ValueError("%s: missing %s" % (base, os.path.basename(p)))
        if _measured_attempt(base, attempt) != bound[attempt]:
            raise ValueError("%s: the receipt, finalization, raw tree or a raw "
                             "byte is not the bound identity" % base)
        rec, fin = _load(rec_path), _load(fin_path)
        bad = list(HR._receipt_problems(ctx, base, PKG_DIR, rec))
        allowed = list(rec.get("allowed") or [])
        if rec.get("attempt") != attempt:
            bad.append("receipt attempt %r is not %d" % (rec.get("attempt"), attempt))
        for field, was, want in (
                ("attempt", fin.get("attempt"), attempt),
                ("door", fin.get("door"), HR.DOOR),
                ("run_id", fin.get("run_id"), rec.get("run_id")),
                ("receipt_sha256", fin.get("receipt_sha256"), INV.sha_file(rec_path)),
                ("manifest_sha256", fin.get("manifest_sha256"), rec.get("manifest_sha256")),
                ("derived_from", fin.get("derived_from"), rec.get("derived_from")),
                ("problems", list(fin.get("problems") or []), []),
                ("primary_complete", fin.get("primary_complete"), True)):
            if was != want:
                bad.append("the finalization's %s is not the derived value" % field)
        outcomes = [tuple(o) for o in (fin.get("outcomes") or [])]
        if [o[0] for o in outcomes] != allowed:
            bad.append("the finalization's outcomes are not the allowed calls in order")
        if any(o[1] not in _FINAL_OUTCOMES for o in outcomes):
            bad.append("a finalized outcome is not a complete one")
        led = fin.get("ledger") or {}
        if led.get("scheduled") != len(allowed) or \
                sum(v for k, v in led.items() if k != "scheduled") != len(allowed) \
                or led.get("unproved") or led.get("missing"):
            bad.append("the finalization's ledger is not the derived count")
        states = list(rec.get("states") or [])
        if len(set(states)) != len(states):
            bad.append("a state is recorded twice")
        if len(states) != len(allowed):
            bad.append("%d states for %d allowed calls" % (len(states), len(allowed)))
        proved, problems = HR._run_evidence(ctx, base, PKG_DIR, rec)
        bad += problems
        derived, expected_files = collections.OrderedDict(), []
        for state in states:
            run_id = os.path.splitext(os.path.basename(state))[0]
            try:
                label = K._state_label(json.loads(K._read(state)))
            except Exception as exc:                  # noqa: BLE001 - by design
                bad.append("%s: state unreadable (%s)" % (run_id, str(exc)[:60]))
                continue
            got = proved.get(label)
            if not got or got[0] not in ("proved", "transport_no_answer"):
                bad.append("%s: %s is not proved" % (run_id, label))
                continue
            if got[0] == "proved":
                text = got[2]
                raw = os.path.join(base, "raw", RT._raw_filename("%s.000" % run_id))
                proved_file = os.path.join(base, "raw", "%s.attempt%s.proved.json"
                                           % (label.replace("/", "_"), attempt))
                for path in (raw, proved_file):
                    if K._stored_matches(path, text) is not True:
                        bad.append("%s is not the official text" % os.path.basename(path))
                expected_files += [os.path.basename(raw), os.path.basename(proved_file)]
            derived[label] = _derived_outcome(ctx, label, got[0], got[2])
        if set(proved) != set(allowed):
            bad.append("the proved labels are not the allowed ones")
        if [(o[0], o[1]) for o in outcomes] != list(derived.items()):
            bad.append("a stored outcome is not the re-derived one")
        counted = collections.Counter(derived.values())
        if any(led.get(name) != counted.get(name, 0) for name in _FINAL_OUTCOMES):
            bad.append("the finalization's ledger is not the re-derived count")
        raw_dir = os.path.join(base, "raw")
        listing = sorted(os.listdir(raw_dir)) if os.path.isdir(raw_dir) else []
        if listing != sorted(expected_files):
            bad.append("the raw tree does not hold exactly the preserved files")
        if list(fin.get("harvested_raw") or []) != \
                [f for f in expected_files if f.endswith(RT._raw_filename(""))]:
            bad.append("the finalization's harvested list is not the preserved raw files")
        owed = [lab for lab, kind in derived.items() if kind in HR.RETRYABLE] \
            if attempt == 1 else []
        if list(fin.get("retry") or []) != owed:
            bad.append("the finalization's retry is not the derived one")
        if owed and HR.MAX_ATTEMPTS not in bound:
            bad.append("the primary owes a child the binding does not own")
        if attempt == HR.MAX_ATTEMPTS and not fin.get("retry") == []:
            bad.append("a child names a successor; there is no third attempt")
        if bad:
            raise ValueError("%s: this run's spend cannot be counted: %s"
                             % (base, bad[:3]))
        rows.append(collections.OrderedDict([
            ("run_dir", base), ("attempt", attempt),
            ("receipt_sha256", INV.sha_file(rec_path)),
            ("finalization_sha256", INV.sha_file(fin_path)),
            ("raw_tree", bound[attempt]["raw_tree"]["sha256"]),
            ("raw_files", bound[attempt]["raw_tree"]["files"]),
            ("calls", len(states))]))
    return rows
