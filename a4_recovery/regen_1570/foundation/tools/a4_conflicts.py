"""Codex SEQ 1370 — the finite read-only conflict inventory.

Three mechanical classes over the corrected usable evidence. Nothing here
detects a named class: there is no keyword list, no packet id and no threshold.
Whatever the three rules reach is what the inventory contains.

  A  every model-reported ambiguity
  B  every item both drafts were derived to reject
  C  every same-source exact quote/locator group whose settled answers conflict
     (this reaches two shapes for free: two packets sharing one locator, and
      one packet answered twice across attempts)

No semantic correction, no model call, no write outside the one artifact.
"""
import collections
import decimal
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
OUT = os.path.join(RUN, "conflicts_1370.json")


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def valid_envelopes(run_dir, attempt):
    """(item, envelope) for every key this run graded valid. Reads only."""
    receipt = K._load(os.path.join(run_dir, K.RECEIPT_NAME))
    items = {i["packet_id"]: i for i in K.phase1_items()}
    proved, _problems = K.run_evidence(run_dir, receipt)
    out = []
    for label, (state, _why, text) in proved.items():
        if state != "proved":
            continue
        obj, bad = K.read_reply(text, items[label])
        if not bad:
            out.append((items[label], obj, attempt))
    return out


def main():
    entries = valid_envelopes(RUN, 1) + valid_envelopes(CHILD, 2)
    regrade = json.load(open(os.path.join(RUN, "regrade_1370.json")))
    picked = {r["packet_id"]: r["selected_attempt"] for r in regrade["items"]}

    ambiguities, both_rejected = [], []
    for item, env, attempt in entries:
        if picked.get(item["packet_id"]) != attempt:
            continue                      # only the SELECTED usable envelope
        loc = collections.OrderedDict([
            ("source_id", item["source_id"]), ("part_ref", item["part_ref"]),
            ("occurrence_in_part", item["occurrence_in_part"]),
            ("quote", item["quote"])])
        for amb in env["ambiguities"]:
            ambiguities.append(collections.OrderedDict([
                ("packet_id", item["packet_id"]), ("attempt", attempt),
                ("locator", loc), ("what", amb["what"]), ("why", amb["why"])]))
        rows = env["reconciliation"]
        if rows and all(r["exact_match"] is False for r in rows):
            both_rejected.append(collections.OrderedDict([
                ("packet_id", item["packet_id"]), ("attempt", attempt),
                ("locator", loc),
                ("lane_reasons", [collections.OrderedDict(
                    [("lane_id", r["lane_id"]), ("why", r["why"])])
                    for r in rows]),
                ("settled", env["settled"])]))

    # ---- C: group EVERY valid envelope (both attempts) by its exact locator
    groups = collections.OrderedDict()
    for item, env, attempt in entries:
        key = (item["source_id"], item["part_ref"],
               item["occurrence_in_part"], item["quote"])
        groups.setdefault(key, []).append((item, env, attempt))
    conflicts = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # `read_reply` already returns the COMPLETED settled object, so the
        # projection applies directly - re-completing it would refuse.
        shapes = [json.dumps(K._answer_identity(env["settled"]),
                             sort_keys=True, default=str)
                  for _it, env, _att in members]
        if len(set(shapes)) < 2:
            continue
        conflicts.append(collections.OrderedDict([
            ("locator", collections.OrderedDict(
                [("source_id", key[0]), ("part_ref", key[1]),
                 ("occurrence_in_part", key[2]), ("quote", key[3])])),
            ("members", [collections.OrderedDict([
                ("packet_id", it["packet_id"]), ("attempt", att),
                ("settled", env["settled"])])
                for it, env, att in members]),
            ("distinct_answers", len(set(shapes)))]))

    doc = collections.OrderedDict([
        ("door", K.A4_DOOR), ("kind", "conflict_inventory"),
        ("authority", "Codex SEQ 1370"),
        ("governing_rules_sha256", K._sha(K.RULES_BLOCK)),
        ("regrade_sha256", sha_file(os.path.join(RUN, "regrade_1370.json"))),
        ("valid_envelopes_read", len(entries)),
        ("selected_usable", sum(1 for v in picked.values() if v)),
        ("counts", collections.OrderedDict([
            ("model_reported_ambiguities", len(ambiguities)),
            ("items_both_drafts_rejected", len(both_rejected)),
            ("conflicting_locator_groups", len(conflicts))])),
        ("model_reported_ambiguities", ambiguities),
        ("items_both_drafts_rejected", both_rejected),
        ("conflicting_locator_groups", conflicts),
    ])
    # the reader parses numbers as exact Decimals; this artifact is evidence
    # for a human, so each one is rendered as its exact decimal LITERAL rather
    # than converted to a float, which would silently change the value
    def literal(obj):
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        raise TypeError(repr(obj))

    doc["number_rendering"] = "exact decimal literals as JSON strings"
    tmp = OUT + ".tmp"
    io.open(tmp, "w", encoding="utf-8").write(
        json.dumps(doc, indent=1, default=literal))
    os.replace(tmp, OUT)
    print("governing rules sha256 :", doc["governing_rules_sha256"])
    print("valid envelopes read   :", len(entries))
    print("A ambiguities          :", len(ambiguities))
    print("B both-drafts-rejected :", len(both_rejected))
    print("C conflicting groups   :", len(conflicts))
    for c in conflicts:
        print("   group %s x%d ->" % (c["locator"]["source_id"],
                                      len(c["members"])),
              ", ".join("%s(a%d)" % (m["packet_id"][-5:], m["attempt"])
                        for m in c["members"]))
    print("artifact               :", OUT)
    print("artifact sha256        :", sha_file(OUT))


main()
