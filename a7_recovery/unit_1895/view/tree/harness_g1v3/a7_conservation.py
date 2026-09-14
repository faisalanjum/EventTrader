# -*- coding: utf-8 -*-
"""Producer-output conservation: every packet, in every arm, terminates once.

WHAT THIS IS NOT. Counting the 196 answer-key packets and their 209 key facts
is a proof about the ANSWER KEY. It says nothing about what the producer
actually returned. This traces the other side:

    raw reply -> its exact input packet -> the four-field answer
      -> enriched provenance -> facts / abstentions / continuity
      -> split, fusion, dedup -> the route's own index_map outcome,
         or an explicit zero-fact terminal

NO SECOND SEMANTIC ENGINE. Every judgement here is read from an owner that
already made it: the reader for what a reply contained, the matcher for what
duplicated, the route for what was written, parked or rejected. This module
only accounts.
"""
import collections
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a7_g1_build as G       # noqa: E402
import a7_g23_build as B      # noqa: E402

SCHEMA = "a7_producer_conservation/1"

#: every terminal a packet's contribution can reach. A packet reaches EXACTLY
#: one of these in one arm; the list is closed so a new outcome cannot hide in
#: an "other" bucket.
TERMINALS = ("written", "parked", "rejected", "abstained_only",
             "zero_fact_terminal", "refused_unreadable", "uncalled")


def contributions(primary=G.PRIMARY):
    """-> (rows, arms, problems). ONE row per (arm, packet), before routing.

    Re-walks the SAME slots `materialize` walks, but keeps what it drops: which
    packet produced which facts, and the continuity hints.
    """
    import a1_reader
    import build_a5_exp5_kit as A5
    import build_launch_manifest as blm
    import kf_lint
    slots, plan, problems = G.effective_slots(primary)
    items = {pk["packet_id"]: pk["item"] for pk in plan["packets"]}
    sources = {pk["packet_id"]: pk["source_id"] for pk in plan["packets"]}
    menus = {e["source_id"]: e.get("menu_display_to_original", {})
             for e in plan.get("events", [])}
    parts, arms, rows = {}, {}, []
    for n, key, path, attempt in slots:
        packet_id, lane_id = key
        sid = sources[packet_id]
        if sid not in parts:
            parts[sid] = kf_lint.part_lookup(sid, blm.INPUTS)
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        completed, why = a1_reader.read_one(text, items[packet_id], sid,
                                            menus.get(sid, {}), parts[sid])
        leg = A5.arm_for_call(lane_id)["arm"]
        by_sid = arms.setdefault(leg, {})
        row = by_sid.setdefault(sid, {"facts": [], "abstentions": []})
        base = len(row["facts"])
        n_facts = 0 if why else len(completed["facts"])
        if not why:
            row["facts"].extend(completed["facts"])
            row["abstentions"].extend(completed["abstentions"])
        rows.append(collections.OrderedDict([
            ("arm", leg), ("packet_id", packet_id), ("source_id", sid),
            ("lane_id", lane_id), ("attempt", attempt),
            ("raw_path", path), ("raw_sha256", G._sha_file(path)),
            # THE FOUR-FIELD ANSWER this packet was asked about
            ("item_quote_sha256", G._sha((items[packet_id] or {}).get("quote")
                                         or "")),
            ("readable", not why),
            ("why_unreadable", (why or [])[:2]),
            ("n_facts", n_facts),
            ("n_abstentions", 0 if why else len(completed["abstentions"])),
            ("n_continuity", 0 if why else len(completed["continuity_hints"])),
            # WHERE this packet's facts landed in its event's accumulated list,
            # which is the only way to join a packet to a route outcome
            ("fact_positions", list(range(base, base + n_facts))),
        ]))
    return rows, arms, problems


def terminals(primary=G.PRIMARY, audit_root="/tmp/a7_conservation_audit"):
    """-> (doc, problems). Each (arm, packet) joined to its route outcome."""
    from scorers.score_exp5 import _rows_for_event
    rows, arms, problems = contributions(primary)
    outcomes = {}
    for leg in sorted(arms):
        audit = os.path.join(audit_root, leg)
        if not os.path.isdir(audit):
            os.makedirs(audit)
        for sid in sorted(arms[leg]):
            arm = arms[leg][sid]
            routed = B.route_for({sid: arm}, audit)[sid]
            # THE ROUTE'S OWN per-record outcome, through the scorer's own
            # validator. Nothing is decided here.
            outcomes[(leg, sid)] = _rows_for_event(
                {sid: routed}, sid, len(arm["facts"]),
                len(arm["abstentions"]))

    counts = collections.Counter()
    for row in rows:
        row["terminal"] = _terminal_of(row, outcomes)
        counts[row["terminal"]] += 1
    doc = collections.OrderedDict([
        ("schema", SCHEMA),
        ("arms", sorted(arms)),
        ("packets_per_arm", G.REQUIRED["packets"]),
        ("rows", rows),
        ("terminal_counts", collections.OrderedDict(sorted(counts.items()))),
        ("dimensions", dimensions(rows, arms)),
    ])
    problems += _conservation_problems(rows, sorted(arms))
    return doc, problems


def dimensions(rows, arms):
    """The accounting dimensions that are NOT a packet's terminal.

    A packet terminates once; these describe HOW its content behaved on the
    way there, and every one is read from an owner that already decided it.
    """
    from driver.core.fact_match import match_facts
    from scorers import score_exp5 as SCO
    gold, _identity = G.live_key()
    out = collections.OrderedDict()
    out["continuity_hints"] = sum(r["n_continuity"] for r in rows)
    out["abstentions"] = sum(r["n_abstentions"] for r in rows)
    # SPLIT: one input packet that yielded more than one fact
    out["split_packets"] = sum(1 for r in rows if r["n_facts"] > 1)
    out["skipped_packets"] = sum(1 for r in rows if r["n_facts"] == 0
                                 and not r["n_abstentions"])
    out["refused_unreadable"] = sum(1 for r in rows if not r["readable"])
    dup, missed = 0, 0
    for leg in sorted(arms):
        for sid in sorted(arms[leg]):
            du = [g for g in gold.get(sid, [])
                  if g.get("du_worthy") is True]
            produced = arms[leg][sid]["facts"]
            gold_v2, _gp = SCO._to_v2_with_positions(du)
            prod_v2, _pp = SCO._to_v2_with_positions(produced)
            mr = match_facts(gold_v2, prod_v2)
            # DUPLICATE: the matcher's own inconclusive groups, never a rule
            # restated here
            dup += sum(len(g) for g in mr.gold_inconclusive)
            missed += len(mr.to_grading_gold)
    out["duplicate_gold_in_inconclusive_groups"] = dup
    out["gold_still_needing_a_ruling"] = missed
    out["precall_unresolved"] = len(B.precall_unresolved(gold))
    return out


def _terminal_of(row, outcomes):
    """The ONE terminal this packet's contribution reached, read from owners."""
    if not row["readable"]:
        return "refused_unreadable"
    if not row["fact_positions"]:
        return "abstained_only" if row["n_abstentions"] else "zero_fact_terminal"
    per_fact = outcomes.get((row["arm"], row["source_id"])) or {}
    decisions = [(per_fact.get(("fact", i)) or {}).get("decision")
                 for i in row["fact_positions"]]
    # a packet whose facts were not all decided the same way still terminates
    # once: the STRONGEST outcome it reached, in the order the route ranks them
    for name in ("written", "parked", "rejected"):
        if name in decisions:
            return name
    return "zero_fact_terminal"


def _conservation_problems(rows, arms):
    """Every packet, in every arm, terminates EXACTLY once."""
    problems = []
    seen = collections.Counter((r["arm"], r["packet_id"]) for r in rows)
    twice = [k for k, v in seen.items() if v != 1]
    if twice:
        problems.append("these (arm, packet) pairs do not terminate exactly "
                        "once: %s" % twice[:3])
    for arm in arms:
        n = sum(1 for r in rows if r["arm"] == arm)
        if n != G.REQUIRED["packets"]:
            problems.append("arm %s accounts %d packets, not %d"
                            % (arm, n, G.REQUIRED["packets"]))
    bad = [r["terminal"] for r in rows if r["terminal"] not in TERMINALS]
    if bad:
        problems.append("unknown terminal(s): %s" % sorted(set(bad))[:3])
    return problems


if __name__ == "__main__":
    import json
    doc, problems = terminals()
    print("arms          :", doc["arms"])
    print("rows          :", len(doc["rows"]))
    print("terminals     :", json.dumps(doc["terminal_counts"]))
    print("dimensions    :", json.dumps(doc["dimensions"]))
    print("problems      :", problems[:3] or "NONE")
