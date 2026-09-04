"""Codex SEQ 1370 — read-only regrade of the IMMUTABLE A4 phase-1 evidence.

Re-reads the primary and child official states with the corrected owners and
writes ONE new artifact. It never overwrites a receipt or a historical
finalization, never calls a model, and never selects an invalid envelope.

Grading here is not a second implementation: it is the owner's own
`run_evidence` (proof) followed by the owner's own `read_reply` (parse), which
is exactly what `finalize` composes - minus the writing.
"""
import collections
import hashlib
import io
import json
import os
import sys

S = ("/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200"
     "/scratchpad")
H = S + "/bench_1306/.claude/plans/Drivers/experiments/harness"
sys.path.insert(0, H)
sys.path.insert(0, "/home/faisal/EventMarketDB")
import build_kfields_key as K                                    # noqa: E402

RUN = io.open(S + "/a4_dir.txt", encoding="utf-8").read().strip()
CHILD = os.path.join(RUN, "retry")
OUT = os.path.join(RUN, "regrade_1370.json")
OLD_OWNER = "13d00b1f2a057701972b97d27f3dbb815e36ed72d9b284f76ff25f03e644c071"


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def grade(run_dir):
    """One run's corrected outcome per scheduled key. Reads only."""
    receipt = K._load(os.path.join(run_dir, K.RECEIPT_NAME))
    allowed = list(receipt.get("allowed") or [])
    items = {i["packet_id"]: i for i in K.phase1_items()}
    bad_receipt = K.receipt_problems(run_dir, receipt)
    outcomes = collections.OrderedDict()
    envelopes = {}
    if bad_receipt:
        for key in allowed:
            outcomes[key] = ("unproved", "the receipt is not the owner's")
        return receipt, allowed, outcomes, envelopes, bad_receipt
    proved, problems = K.run_evidence(run_dir, receipt)
    for label, (state, why, text) in proved.items():
        if state != "proved":
            outcomes[label] = (state, why)
            continue
        obj, bad = K.read_reply(text, items[label])
        if bad:
            outcomes[label] = ("invalid_response", bad[0])
        else:
            outcomes[label] = ("valid", "")
            envelopes[label] = obj
    for key in allowed:
        outcomes.setdefault(key, ("missing", "no official state"))
    return receipt, allowed, outcomes, envelopes, problems


def main():
    prim_receipt, prim_allowed, prim_out, prim_env, prim_probs = grade(RUN)
    kid_receipt, kid_allowed, kid_out, kid_env, kid_probs = grade(CHILD)

    old_prim = {k: o for k, o, _w in
                json.load(open(os.path.join(RUN, K.FINALIZATION_NAME)))["outcomes"]}
    old_kid = {k: o for k, o, _w in
               json.load(open(os.path.join(CHILD, K.FINALIZATION_NAME)))["outcomes"]}

    rows, unresolved, selected = [], [], {}
    for key in prim_allowed:
        pnew = prim_out[key][0]
        knew = kid_out.get(key, ("absent", ""))[0]
        if pnew == "valid":
            pick, env = 1, prim_env[key]
        elif knew == "valid":
            pick, env = 2, kid_env[key]
        else:
            pick, env = None, None
            unresolved.append(key)
        if pick is not None:
            assert key not in selected, "an item may be selected once"
            selected[key] = env
        rows.append(collections.OrderedDict([
            ("packet_id", key),
            ("primary_before", old_prim.get(key)),
            ("primary_after", pnew),
            ("child_before", old_kid.get(key)),
            ("child_after", knew if key in kid_out else None),
            ("selected_attempt", pick),
            ("selected_from", None if pick is None
             else ("primary" if pick == 1 else "child")),
        ]))

    counts = collections.Counter(r["primary_after"] for r in rows)
    kcounts = collections.Counter(kid_out[k][0] for k in kid_allowed)
    recovered = [r["packet_id"] for r in rows
                 if r["primary_after"] != "valid" and r["selected_attempt"] == 2]
    surplus = [k for k in kid_allowed
               if kid_out[k][0] == "valid" and prim_out[k][0] == "valid"]

    doc = collections.OrderedDict([
        ("door", K.A4_DOOR),
        ("kind", "correction_regrade"),
        ("authority", "Codex SEQ 1370"),
        ("owner_before", OLD_OWNER),
        ("owner_after", sha_file(os.path.join(H, "build_kfields_key.py"))),
        ("primary", collections.OrderedDict([
            ("run_id", prim_receipt.get("run_id")),
            ("receipt_sha256", sha_file(os.path.join(RUN, K.RECEIPT_NAME))),
            ("finalization_sha256",
             sha_file(os.path.join(RUN, K.FINALIZATION_NAME))),
            ("problems", prim_probs),
            ("ledger_after", collections.OrderedDict(
                [("scheduled", len(prim_allowed))]
                + [(n, counts.get(n, 0)) for n in
                   ("valid", "invalid_response", "transport_no_answer",
                    "unproved", "missing")])),
        ])),
        ("child", collections.OrderedDict([
            ("run_id", kid_receipt.get("run_id")),
            ("receipt_sha256", sha_file(os.path.join(CHILD, K.RECEIPT_NAME))),
            ("finalization_sha256",
             sha_file(os.path.join(CHILD, K.FINALIZATION_NAME))),
            ("problems", kid_probs),
            ("ledger_after", collections.OrderedDict(
                [("scheduled", len(kid_allowed))]
                + [(n, kcounts.get(n, 0)) for n in
                   ("valid", "invalid_response", "transport_no_answer",
                    "unproved", "missing")])),
        ])),
        ("selection", collections.OrderedDict([
            ("usable", len(selected)),
            ("from_primary", sum(1 for r in rows if r["selected_attempt"] == 1)),
            ("from_child", len(recovered)),
            ("child_surplus", len(surplus)),
            ("unresolved", unresolved),
        ])),
        ("items", rows),
    ])
    tmp = OUT + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(json.dumps(doc, indent=1))
    os.replace(tmp, OUT)

    print("owner_before      :", OLD_OWNER)
    print("owner_after       :", doc["owner_after"])
    print("primary problems  :", len(prim_probs))
    print("child   problems  :", len(kid_probs))
    print("primary ledger    :", json.dumps(doc["primary"]["ledger_after"]))
    print("child   ledger    :", json.dumps(doc["child"]["ledger_after"]))
    print("usable envelopes  :", len(selected),
          "(primary %d + child %d)" % (doc["selection"]["from_primary"],
                                       len(recovered)))
    print("child surplus     :", len(surplus))
    print("unresolved        :", len(unresolved))
    for k in unresolved:
        print("   *", k)
    print("artifact          :", OUT)
    print("artifact sha256   :", sha_file(OUT))


main()
