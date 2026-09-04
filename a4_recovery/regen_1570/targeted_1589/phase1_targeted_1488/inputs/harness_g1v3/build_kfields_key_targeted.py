"""A TARGETED A4 phase-one packet, through the ONE lifecycle (Codex SEQ 1487
item 3, corrected per SEQ 1488 item 1).

build_kfields_key owns the phase-one lifecycle - preflight, receipt, official-
state proof, raw-first finalizer, parser, invalid-only child, no third attempt
- over a small package context. This module supplies that context for exactly
the items whose source binding changed, and nothing else:

  * the target set, derived mechanically from the frozen-to-corrected
    inventory diff - a record may differ only in `quote` and
    `raw_label_or_claim`, anything else refuses;
  * the corrected item in place of the frozen one, with the SAME proved A3
    drafts as untrusted leads;
  * a manifest of the phase-one shape plus a `correction` block and a
    hash-bound current stage budget;
  * ONE gated door, prepare_run, and the shared finalize/record_state.

There is no ungated publication and no second finalizer. The module never
imports the key, its ledger, or any grader.
"""
import collections
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import build_kfields_key as K                                    # noqa: E402
import raw_transport as RT                                       # noqa: E402

INV = K.INV
#: the only fields a source correction may change (Codex SEQ 1487 item 1)
CHANGEABLE = ("quote", "raw_label_or_claim")
PKG_NAME = "phase1.manifest.json"
#: THE corrected inventory this package is bound to, beside the frozen one
CORRECTED_INVENTORY = os.path.join(K._X, "one_item_benchmark_inventory.v2_1487.json")
#: THE targeted package this module serves; the 1487 package stays as history
PKG_DIR = os.path.join(K._X, "kfields_key_a4", "phase1_targeted_1488")
#: the current call-budget receipt this stage's budget is bound to, by hash
BUDGET_RECEIPT = "/tmp/a7_budget_receipt_1488.json"
#: the correction receipt that derived the corrected inventory from the
#: reviewed source receipt; it carries that receipt's file hash and digest
CORRECTION_RECEIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(K._X))))), "lock", "candidate_v2_1488",
    "correction_receipt.json")


def _load(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def diff(corrected_path=CORRECTED_INVENTORY):
    """-> [(index, packet_id, changed_fields)] against the frozen inventory.
    Refuses any identity, order or field the correction may not touch."""
    frozen = _load(INV.INV)["records"]
    corrected = _load(corrected_path)["records"]
    if len(frozen) != len(corrected):
        raise ValueError("the corrected inventory carries %d records, the "
                         "frozen one %d" % (len(corrected), len(frozen)))
    out = []
    for n, (a, b) in enumerate(zip(frozen, corrected)):
        if a["source_id"] != b["source_id"]:
            raise ValueError("record %d names %s, the frozen record names %s"
                             % (n, b["source_id"], a["source_id"]))
        changed = tuple(f for f in INV.RECORD_FIELDS if a.get(f) != b.get(f))
        if not changed:
            continue
        if set(changed) - set(CHANGEABLE):
            raise ValueError("record %d: only %s may differ in a source "
                             "correction; %s differs"
                             % (n, list(CHANGEABLE), sorted(changed)))
        out.append((n, "%s#%03d" % (a["source_id"], n), changed))
    return out


def targets(corrected_path=CORRECTED_INVENTORY):
    return [pid for _n, pid, _c in diff(corrected_path)]


def targeted_items(corrected_path=CORRECTED_INVENTORY):
    """The frozen items, in frozen order, restricted to the targets and
    carrying the corrected binding. Drafts, part and identity are untouched."""
    corrected = _load(corrected_path)["records"]
    want = {pid: n for n, pid, _c in diff(corrected_path)}
    items = []
    for it in K.phase1_items():
        if it["packet_id"] not in want:
            continue
        rec = corrected[want[it["packet_id"]]]
        row = collections.OrderedDict(it)
        row["quote"] = rec["quote"]
        row["raw_label_or_claim"] = rec["raw_label_or_claim"]
        row["occurrence_in_part"] = rec["occurrence_in_part"]
        items.append(row)
    return items


def _stage_budget(calls):
    """This stage's budget, bound by hash to the current budget receipt: the
    completed-before figure and the ceiling are that receipt's, never typed
    here (Codex SEQ 1488 item 3)."""
    receipt = _load(BUDGET_RECEIPT)
    before = receipt["completed_before"]
    return collections.OrderedDict([
        ("budget_receipt_path", BUDGET_RECEIPT),
        ("budget_receipt_sha256", INV.sha_file(BUDGET_RECEIPT)),
        ("before", before), ("primaries", calls),
        ("retry_cap", 1),
        ("retry_cap_meaning", "PER ITEM, never a run total"),
        ("max_attempts_per_item", K.MAX_ATTEMPTS),
        ("after", before + calls),
        ("worst_case_after", before + calls * K.MAX_ATTEMPTS),
        ("ceiling", receipt["ceiling"])])


def _correction_block(corrected_path):
    """The correction, bound end to end: frozen inventory -> reviewed source
    receipt (file hash + digest, from the correction receipt that applied
    it) -> corrected inventory -> targets. A correction receipt that did not
    derive THIS corrected inventory refuses (Codex SEQ 1488 item 4)."""
    cr = _load(CORRECTION_RECEIPT)
    if cr.get("versioned_inventory_path") != os.path.abspath(corrected_path) \
            or INV.sha_file(cr["versioned_inventory_path"]) != \
            INV.sha_file(corrected_path):
        raise ValueError("the correction receipt %s did not derive %s"
                         % (CORRECTION_RECEIPT, corrected_path))
    # CORRECTION OUTPUT IDENTITY (Codex SEQ 1489 item B): the receipt's whole
    # declared output mapping must be the owner's actual outputs beside it -
    # a missing, extra, changed or swapped row refuses before anything binds.
    here = os.path.dirname(CORRECTION_RECEIPT)
    actual = {n: INV.sha_file(os.path.join(here, n)) for n in os.listdir(here)
              if n != os.path.basename(CORRECTION_RECEIPT)}
    if cr.get("outputs") != actual:
        raise ValueError("the correction receipt's declared outputs %s are not "
                         "the owner's actual outputs %s"
                         % (sorted(cr.get("outputs") or {}), sorted(actual)))
    return collections.OrderedDict([
        ("frozen_inventory_sha256", INV.sha_file(INV.INV)),
        ("correction_receipt_path", CORRECTION_RECEIPT),
        ("correction_receipt_sha256", INV.sha_file(CORRECTION_RECEIPT)),
        ("source_receipt", collections.OrderedDict(
            (k, cr["source_receipt"][k])
            for k in ("path", "file_sha256", "receipt_sha256"))),
        ("corrected_inventory_path", os.path.abspath(corrected_path)),
        ("corrected_inventory_sha256", INV.sha_file(corrected_path)),
        ("targets", [collections.OrderedDict([
            ("packet_id", pid), ("record_index", n),
            ("changed_fields", list(c))]) for n, pid, c in diff(corrected_path)])])


def manifest_document(corrected_path=CORRECTED_INVENTORY):
    """The complete targeted manifest, derived; the same function builds it
    and rebuilds it for the whole-document comparison."""
    items = targeted_items(corrected_path)
    ev = K.a3_evidence()
    rows, sizes, scripts = [], [], []
    for item in items:
        text = K.phase1_prompt(item)
        script = K.render_launcher(item)
        sizes.append(len(text.encode("utf-8")))
        scripts.append(len(script.encode("utf-8")))
        rows.append(collections.OrderedDict([
            ("packet_id", item["packet_id"]),
            ("source_id", item["source_id"]),
            ("prompt_sha256", K._sha(text)),
            ("prompt_bytes", sizes[-1]),
            ("script_sha256", K._sha(script)),
            ("script_bytes", scripts[-1]),
            ("drafts", [collections.OrderedDict([("lane_id", d["lane_id"]),
                                                 ("sha256", d["sha256"])])
                        for d in item["a3_drafts"]])]))
    return collections.OrderedDict([
        ("schema", "kfields-a4-phase1-v1"),
        ("base_commit", INV.BASE_COMMIT),
        ("door", K.A4_DOOR),
        ("calls", len(rows)),
        ("inventory_sha256", INV.sha_file(corrected_path)),
        ("rules_sha256", K._sha(K.RULES_BLOCK)),
        ("transport", K._transport_block()),
        ("a3_binding", ev["binding"]),
        ("budget", _stage_budget(len(rows))),
        ("capacity", collections.OrderedDict([
            ("unit", "UTF-8 bytes of the serialized launcher script the "
                     "runtime actually runs; never summed"),
            ("transport_limit_bytes", K.TRANSPORT_LIMIT),
            ("largest_script_bytes", max(scripts)),
            ("smallest_script_bytes", min(scripts)),
            ("largest_prompt_bytes", max(sizes)),
            ("at_or_over_transport_limit",
             sorted(r["packet_id"] for r, n in zip(rows, scripts)
                    if n >= K.TRANSPORT_LIMIT))])),
        ("history", collections.OrderedDict([
            ("frozen_package_proposals",
             K.historical_package()["manifest"]["inventory"]["proposals"]),
            ("final_inventory_records", len(_load(INV.INV)["records"])),
            ("source_gap", K.historical_source_gap())])),
        ("reply_keys", list(K.REPLY_KEYS)),
        ("launch", collections.OrderedDict([
            ("renderer", "build_kfields_key.render_launcher"),
            ("gate", "build_kfields_key.preflight(pkg) inside "
                     "build_kfields_key_targeted.prepare_run"),
            ("prepare", "build_kfields_key_targeted.prepare_run"),
            ("finalize", "build_kfields_key_targeted.finalize -> "
                         "build_kfields_key.finalize(run_dir, pkg)"),
            ("order", "the items list below, once each, in this order"),
            ("one_agent_in_flight", True),
            ("retry", "at most one identical-prompt retry, transport/JSON/"
                      "schema only; never a semantic retry"),
            ("raw_first", "preserve every raw answer before any parse")])),
        ("correction", _correction_block(corrected_path)),
        ("items", rows)])


def build_targeted(out_dir, corrected_path=CORRECTED_INVENTORY):
    """Write the targeted phase-one candidate ONCE. Launches nothing."""
    doc = manifest_document(corrected_path)
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    text = json.dumps(doc, indent=1)
    RT.write_new(os.path.join(out_dir, PKG_NAME), text)
    RT.write_new(os.path.join(out_dir, "rules.txt"), K.RULES_BLOCK)
    doc["manifest_sha256"] = K._sha(text)
    return doc


def package_problems(pkg_dir):
    """Why this built package is not the exact, complete, unaltered targeted
    candidate: the WHOLE manifest is rebuilt from the owners and compared."""
    path = os.path.join(pkg_dir, PKG_NAME)
    if not os.path.isfile(path):
        return ["no manifest at %s" % path]
    doc = _load(path)
    corrected = (doc.get("correction") or {}).get("corrected_inventory_path")
    if not corrected or not os.path.isfile(corrected):
        return ["the manifest names no readable corrected inventory"]
    try:
        want = json.loads(json.dumps(manifest_document(corrected)))
    except ValueError as exc:
        return ["the manifest cannot be rebuilt: %s" % exc]
    if doc == want:
        bad = []
    else:
        bad = ["manifest.%s is not the rebuilt value" % k
               for k in want if doc.get(k) != want[k]]
        bad += ["manifest carries %r, which the rebuild does not" % k
                for k in doc if k not in want]
    rules = os.path.join(pkg_dir, "rules.txt")
    if not os.path.isfile(rules) or \
            io.open(rules, encoding="utf-8").read() != K.RULES_BLOCK:
        bad.append("the shipped rules block is not the live one")
    return bad


def _ctx():
    """THE package context this module serves."""
    return {"dir": PKG_DIR, "items": targeted_items(CORRECTED_INVENTORY)}


def prepare_run(run_dir):
    """THE ONE gated door: the whole package must rebuild identically, then
    the shared phase-one gate and receipt owner run over this context."""
    bad = package_problems(PKG_DIR)
    if bad:
        return {"ok": False, "problems": bad, "invocations": []}
    return K._prepare_run(run_dir, _ctx())


def finalize(run_dir):
    """The shared raw-first, write-once finalizer over this context."""
    return K._finalize(run_dir, _ctx())


record_state = K.record_state          # the one appendable field, unchanged
