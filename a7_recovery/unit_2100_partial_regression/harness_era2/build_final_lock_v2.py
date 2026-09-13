"""The reviewed materializer seam, versioned ONCE more (Codex SEQ 1487 item 1).

build_final_lock.py (untouched, imported here) derives the frozen inventory from
the immutable accepted raws plus the ONE reviewed reconciliation. This version
adds exactly one reconciliation change kind, `rebind`: an existing source item's
binding fields - `quote`, and where changed `raw_label_or_claim` - are replaced.
Every rebind is bound to the COMPLETE old record and its hash and carries the
exact before/after values; the changes are DATA read from the independently
verified 1486 receipt. A stale target, an extra field, missing source bytes, an
invalid location, a claim outside the new quote, or any difference nobody
declared refuses before an inventory exists.

Nothing else moves: the v1 derivation must first reproduce the frozen records
exactly, the serializer is the frozen one, the validator is the existing one.
"""
import collections
import copy
import hashlib
import io
import json
import os
import sys

LOCK_DIR = os.path.dirname(os.path.abspath(__file__))
if LOCK_DIR not in sys.path:
    sys.path.insert(0, LOCK_DIR)
import build_final_lock as L                                   # noqa: E402
from driver.core.prepared_fact_v2 import verify_occurrence     # noqa: E402

INV, RT = L.INV, L.RT
REBIND = "rebind"
#: the only fields a source correction may change (Codex SEQ 1487 item 1)
REBINDABLE = ("quote", "raw_label_or_claim")
RECEIPT_PATH = "/tmp/a7_source_locator_audit_1486.json"
DEFAULT_OUT = os.path.join(LOCK_DIR, "candidate_v2_1487")
#: the new version lives BESIDE the frozen inventory, never over it
VERSIONED_INVENTORY = os.path.join(
    os.path.dirname(os.path.abspath(INV.INV)),
    "one_item_benchmark_inventory.v2_1487.json")
SCHEMA = "a4-source-correction-freeze-v1"


def _order():
    return [e["source_id"] for e in json.load(io.open(
        L.X + "/inventory_review/package.manifest.json", encoding="utf-8"))["events"]]


def record_sha(rec):
    """The complete old record identity, hashed canonically."""
    return L.sha(json.dumps(collections.OrderedDict(
        (f, rec[f]) for f in INV.RECORD_FIELDS), sort_keys=True,
        ensure_ascii=False, separators=(",", ":")))


def records_of(rows):
    return [collections.OrderedDict((f, r[f]) for f in INV.RECORD_FIELDS)
            for sid in rows for r in rows[sid]]


def base_rows():
    """The v1 derivation, which must reproduce the frozen records exactly:
    nothing may be rebound on a base that has moved."""
    recon = json.load(io.open(L.RECON, encoding="utf-8"))
    rows, sidecar, raws, locator, problems = L.derive(recon, L.accepted(),
                                                      _order())
    if not problems:
        frozen = json.load(io.open(INV.INV, encoding="utf-8"))["records"]
        if [dict(r) for r in records_of(rows)] != frozen:
            problems.append("the v1 derivation does not reproduce the frozen "
                            "inventory; nothing may be rebound on a moved base")
    return rows, sidecar, raws, locator, problems


def rebind_changes(receipt, frozen):
    """The receipt's EXTENDABLE rows as rebind changes, each bound to the
    complete frozen record it names. A receipt row that does not name the
    frozen record exactly is refused here, before anything is applied."""
    owner = "Codex SEQ 1486 receipt %s" % receipt["receipt_sha256"]
    records = frozen["records"]
    out = []
    for r in receipt["rows"]:
        if r.get("outcome") != "EXTENDABLE":
            continue
        n = int(r["packet_id"].rsplit("#", 1)[1])
        rec = records[n]
        span = r["proposed_span"]
        if rec["source_id"] != r["source_id"] or \
                rec["quote"] != r["old_locator"]["quote"] or \
                rec["raw_label_or_claim"] != span["raw_label_or_claim"]:
            raise ValueError("%s: the receipt does not name the frozen record"
                             % r["packet_id"])
        after = collections.OrderedDict([("quote", span["span"])])
        if span["corrected_raw_label_or_claim"] != rec["raw_label_or_claim"]:
            after["raw_label_or_claim"] = span["corrected_raw_label_or_claim"]
        out.append(collections.OrderedDict([
            ("op", REBIND), ("owner", owner), ("source_id", rec["source_id"]),
            ("record_index", n), ("packet_id", r["packet_id"]),
            ("before", collections.OrderedDict(
                (f, rec[f]) for f in INV.RECORD_FIELDS)),
            ("before_sha256", record_sha(rec)),
            ("after", after)]))
    return out


def apply_rebinds(rows, changes):
    """Apply rebinds to the derived rows in place. -> problems (empty = all
    applied). Every refusal is by name; a refused change applies nothing."""
    problems = []
    for c in changes:
        if c.get("op") != REBIND:
            problems.append("%r is not a change this seam owns" % c.get("op"))
            continue
        after = c.get("after") or {}
        extra = sorted(set(after) - set(REBINDABLE))
        if extra or not after:
            problems.append("%s: a rebind may change only %s; it names field(s) "
                            "%s" % (c.get("packet_id"), list(REBINDABLE),
                                    extra or "none"))
            continue
        sid = c["source_id"]
        hits = [r for r in rows.get(sid, [])
                if all(r.get(f) == c["before"].get(f) for f in INV.RECORD_FIELDS)]
        if len(hits) != 1 or record_sha(c["before"]) != c["before_sha256"]:
            problems.append("%s: stale target: %d derived row(s) equal the "
                            "declared old record and its hash %s"
                            % (c.get("packet_id"), len(hits),
                               "matches" if record_sha(c["before"]) ==
                               c["before_sha256"] else "does not match"))
            continue
        r = hits[0]
        txt = L.parts_of(sid).get(r["part_ref"])
        new_quote = after.get("quote", r["quote"])
        why = verify_occurrence(txt or "", new_quote, None)
        if why:
            problems.append("%s: the new quote must occur exactly once in %s: "
                            "%s" % (c.get("packet_id"), r["part_ref"], why))
            continue
        claim = after.get("raw_label_or_claim", r["raw_label_or_claim"])
        if not isinstance(claim, str) or claim not in new_quote:
            problems.append("%s: the claim is not inside the new quote"
                            % c.get("packet_id"))
            continue
        for f, v in after.items():
            r[f] = v
        r["occurrence_in_part"] = None          # unique, proved above
    return problems


def unowned_difference_problems(records, frozen, changes):
    """Every difference from the frozen inventory must be a declared rebind,
    and every declared rebind must have changed something."""
    declared = {(c["record_index"], f) for c in changes for f in c["after"]}
    problems = []
    base = frozen["records"]
    if len(records) != len(base):
        return ["%d records, the frozen inventory has %d"
                % (len(records), len(base))]
    for n, (a, b) in enumerate(zip(base, records)):
        for f in INV.RECORD_FIELDS:
            if a.get(f) != b.get(f) and (n, f) not in declared:
                problems.append("record %d: unowned difference in %s" % (n, f))
    for n, f in sorted(declared):
        if base[n][f] == records[n][f]:
            problems.append("record %d: the declared change to %s changed "
                            "nothing" % (n, f))
    return problems


def census(frozen, inv):
    out = collections.Counter()
    out["records"] = len(inv["records"])
    for a, b in zip(frozen["records"], inv["records"]):
        diff = [f for f in INV.RECORD_FIELDS if a.get(f) != b.get(f)]
        if diff:
            out["changed_records"] += 1
        for f in diff:
            out[f if f in REBINDABLE else "other_fields"] += 1
    for k in ("changed_records", "quote", "raw_label_or_claim", "other_fields"):
        out.setdefault(k, 0)
    return dict(out)


def materialize(receipt):
    """Derive every output text. Writes nothing."""
    frozen = json.load(io.open(INV.INV, encoding="utf-8"))
    order = _order()
    rows, sidecar, raws, locator, problems = base_rows()
    if problems:
        return {"problems": problems}
    changes = rebind_changes(receipt, frozen)
    problems += apply_rebinds(rows, changes)
    records = records_of(rows)
    problems += unowned_difference_problems(records, frozen, changes)
    counted = collections.Counter(r["proposed_record_kind"] for r in records)
    inventory = collections.OrderedDict([
        ("base_commit", INV.BASE_COMMIT),
        ("counts", collections.OrderedDict([
            ("events_covered", len({r["source_id"] for r in records})),
            ("proposed_lawful_abstention_controls",
             counted["lawful_abstention_control"]),
            ("proposed_negative_controls", counted["negative_control"]),
            ("proposed_real_items", counted["real_item"]),
            ("records", len(records)), ("source_events", len(order))])),
        ("note", frozen["note"]), ("records", records),
        ("schema", INV.SCHEMA), ("source_manifest", frozen["source_manifest"])])
    inv_text = json.dumps(inventory, indent=1, sort_keys=True)   # the frozen serializer
    problems += INV.check(json.loads(inv_text))
    tags = collections.defaultdict(set)
    for r in records:
        for t in r["proposed_hard_classes"]:
            tags[t].add((r["source_id"], r["quote"], r["raw_label_or_claim"]))
    for t in INV.HARD_CLASSES:
        if len(tags[t]) < INV.TAG_FLOOR:
            problems.append("hard class %s has %d distinct rows, below the "
                            "floor %d" % (t, len(tags[t]), INV.TAG_FLOOR))
    for c in changes:
        sidecar.append(collections.OrderedDict([
            ("source_id", c["source_id"]),
            ("origin", "reviewed_source_correction"),
            ("proposal_id", None), ("decision", REBIND),
            ("why", c["owner"]), ("row", None)]))
    recon_text = io.open(L.RECON, encoding="utf-8").read()
    side_text = json.dumps(collections.OrderedDict([
        ("schema", "pre-a2-inventory-adjudication-v1"),
        ("rows", sidecar),
        ("reviewed_reconciliation", collections.OrderedDict([
            ("path", os.path.relpath(L.RECON, L.S)), ("sha256", L.sha(recon_text)),
            ("resolutions", len(json.loads(recon_text)["resolutions"])),
            ("changes", len(json.loads(recon_text)["changes"])),
            ("locator_translations", locator)])),
        ("source_correction", collections.OrderedDict([
            ("receipt_sha256", receipt["receipt_sha256"]),
            ("changes", changes)])),
        ("raw_replies", collections.OrderedDict((s, L.sha(raws[s])) for s in order)),
    ]), indent=1)
    val_text = json.dumps(collections.OrderedDict([
        ("validator", os.path.relpath(INV.__file__, "/home/faisal/EventMarketDB")),
        ("problems", []), ("records_checked", len(records)),
        ("hard_class_counts", {t: len(tags[t]) for t in INV.HARD_CLASSES}),
        ("tag_floor", INV.TAG_FLOOR)]), indent=1)
    hashes = collections.OrderedDict([
        ("final_inventory.json", L.sha(inv_text)),
        ("adjudication_sidecar.json", L.sha(side_text)),
        ("validator_receipt.json", L.sha(val_text))])
    correction = collections.OrderedDict([
        ("schema", SCHEMA),
        ("frozen_inventory", collections.OrderedDict([
            ("path", os.path.abspath(INV.INV)),
            ("sha256", L.sha(io.open(INV.INV, encoding="utf-8").read()))])),
        ("reviewed_reconciliation_sha256", L.sha(recon_text)),
        ("source_receipt", collections.OrderedDict([
            ("path", RECEIPT_PATH), ("receipt_sha256", receipt["receipt_sha256"])])),
        ("source_manifest", frozen["source_manifest"]),
        ("census", census(frozen, json.loads(inv_text))),
        ("changes", changes),
        ("versioned_inventory_path", VERSIONED_INVENTORY),
        ("outputs", hashes)])
    corr_text = json.dumps(correction, indent=1, ensure_ascii=False)
    hashes["correction_receipt.json"] = L.sha(corr_text)
    return {"inventory_text": inv_text, "sidecar_text": side_text,
            "receipt_text": val_text, "correction_text": corr_text,
            "records": records, "changes": changes, "problems": problems,
            "hashes": hashes}


def _write_new(path, text):
    """Write-once: an existing identical file is fine; a different one refuses."""
    if os.path.exists(path):
        if io.open(path, encoding="utf-8").read() == text:
            return
        raise ValueError("%s exists with different bytes; never overwritten"
                         % path)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def build(out_dir, receipt, versioned_path=None):
    """Materialize into `out_dir` and publish the versioned inventory beside
    the frozen one. Refuses with a written reason before any inventory exists."""
    out = materialize(receipt)
    os.path.isdir(out_dir) or os.makedirs(out_dir)
    if out["problems"]:
        io.open(os.path.join(out_dir, "refusal.json"), "w",
                encoding="utf-8").write(json.dumps(
                    {"problems": out["problems"]}, indent=1))
        raise ValueError("refused: %s" % out["problems"][:3])
    for name, key in (("final_inventory.json", "inventory_text"),
                      ("adjudication_sidecar.json", "sidecar_text"),
                      ("validator_receipt.json", "receipt_text"),
                      ("correction_receipt.json", "correction_text")):
        _write_new(os.path.join(out_dir, name), out[key])
    if versioned_path is not False:
        _write_new(versioned_path or VERSIONED_INVENTORY, out["inventory_text"])
    return {"hashes": out["hashes"], "out_dir": out_dir,
            "versioned_inventory": versioned_path or VERSIONED_INVENTORY}


if __name__ == "__main__":
    receipt = json.load(io.open(RECEIPT_PATH, encoding="utf-8"))
    got = build(DEFAULT_OUT, receipt)
    print(json.dumps(got, indent=1))
