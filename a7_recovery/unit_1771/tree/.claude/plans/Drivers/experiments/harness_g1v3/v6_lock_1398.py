"""The V6 lock-only owner. Codex SEQ 1398.

It owns EXACTLY ONE thing: the V6 lock document and its re-derivation check.
Everything else - the gate, the official signer-evidence reader, the signature
parser, the package data and the V6 shard composition - is imported from the
frozen build_kfields_final.py, whose bytes interpreted the paid replies and
must not change. There is no new parser, auditor, transport, semantic rule,
compatibility layer or framework here.
"""
import collections
import os

import build_kfields_final as F

K, INV = F.K, F.INV
_HERE = os.path.dirname(os.path.abspath(__file__))
_OWNER = os.path.join(F._HERE, "build_kfields_final.py")
_SELF = os.path.join(_HERE, "v6_lock_1398.py")

SCHEMA = "a4-detailed-key-lock-v6"


def _v6_history_pins(bound):
    """The V1-V5 pins the ACCEPTED V6 receipt itself recorded.

    Deliberately not F._recorded_history_pins: that reads
    `decision_correction or decision` and would silently bind the V4 run's
    pins to a V6 lock.
    """
    path = os.path.join(bound.decision_correction_v6, K.RECEIPT_NAME)
    if not os.path.isfile(path):
        raise ValueError("the v6 receipt is missing")
    pins = K._load(path).get("v1_evidence")
    if not isinstance(pins, dict) or not pins:
        raise ValueError("the v6 receipt records no earlier evidence")
    return pins


def v6_lock(signer_dir, bound):
    """The V6 key's lock, re-derived from live bytes every time.

    Never falls through to the V5 or V4 shape: a bound without a v6 run is
    refused outright rather than sealed by an older branch.
    """
    if bound.decision_correction_v6 is None:
        raise ValueError("this owner locks a v6 composition only; no v6 run "
                         "is bound")
    drift = F.package_problems(bound.package, bound.evidence, bound.hr,
                               bound.fix)
    if drift:
        raise ValueError("the interpreting owners drifted: %s" % drift[:2])
    gate = F.signing_gate(bound.events, bound)
    if not gate["ok"]:
        raise ValueError("the signing gate is not clean: %s" % gate["stops"][:2])
    stale = F._receipt_still_the_proved_one(signer_dir, bound)
    if stale:
        raise ValueError("the signer receipt is not the proved one: %s"
                         % stale[:2])
    receipt = K._load(os.path.join(signer_dir, K.RECEIPT_NAME))
    proved, probs = F.run_evidence(signer_dir, bound, receipt)
    if probs:
        raise ValueError("the signature is not proved: %s" % probs[:2])
    text = None
    for _label, (state, _why, t) in proved.items():
        if state == "proved":
            text = t
    sig, bad = F.read_signature(text or "")
    if bad or not sig["signed"]:
        raise ValueError("there is no lawful signature")

    # the composition must be the v6 one, not an older branch that happens to
    # be derivable from the same bound
    shards, raws, origins, sprob = F.v6_shards(bound)
    if sprob:
        raise ValueError("the v6 composition does not derive: %s" % sprob[:2])
    if list(raws) != list(gate["raws"]):
        raise ValueError("the gate and the v6 composition disagree on order")

    v6 = bound.decision_correction_v6
    doc = F._package(bound)
    return collections.OrderedDict([
        ("schema", SCHEMA), ("state", "LOCKED"),
        ("base_commit", INV.BASE_COMMIT),
        ("package_manifest_sha256", INV.sha_file(
            os.path.join(bound.package, F.MANIFEST_NAME))),
        ("bound_owners", doc["bound"]),
        ("lock_owner", collections.OrderedDict([
            ("module", "v6_lock_1398"),
            ("sha256", INV.sha_file(_SELF))])),
        ("loader", collections.OrderedDict([
            ("module", "build_kfields_final"), ("entry", "v6_shards"),
            ("sha256", INV.sha_file(_OWNER))])),
        ("key_shards", [collections.OrderedDict(
            [("source_id", sid), ("origin", origins[sid]),
             ("sha256", K._sha(raw))])
            for sid, raw in raws.items()]),
        ("v6_events", list(F.v6_labels(bound))),
        ("history_evidence", _v6_history_pins(bound)),
        ("v6_receipt_sha256", INV.sha_file(os.path.join(v6, K.RECEIPT_NAME))),
        ("v6_finalization_sha256", INV.sha_file(
            os.path.join(v6, K.FINALIZATION_NAME))),
        # The V1-V5 pins above each carry their run's whole raw tree. Binding
        # the receipt and finalization alone would leave THIS run's preserved
        # replies - and the signer's - the only evidence a lock never notices.
        ("v6_raw_tree", F.raw_tree(v6)),
        ("signer_raw_sha256", K._sha(text)),
        ("signer_finalization_sha256", INV.sha_file(
            os.path.join(signer_dir, K.FINALIZATION_NAME))),
        ("signer_raw_tree", F.raw_tree(signer_dir)),
        ("counts", gate["counts"]),
        ("signature", collections.OrderedDict([
            ("signed", sig["signed"]), ("why", sig["why"])])),
    ])


def v6_lock_problems(candidate, signer_dir, bound):
    """Re-derive every bound value; mutating any one of them must refuse."""
    try:
        live = v6_lock(signer_dir, bound)
    except ValueError as exc:                         # noqa: BLE001 - by design
        return ["the v6 lock no longer derives: %s" % exc]
    bad = []
    for field in live:
        if candidate.get(field) != live[field]:
            bad.append("the locked %s is not the live one" % field)
    for field in candidate:
        if field not in live:
            bad.append("the locked %s is not a v6 lock field" % field)
    return bad
