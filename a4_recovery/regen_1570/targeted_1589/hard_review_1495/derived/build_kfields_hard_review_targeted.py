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
