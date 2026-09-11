"""Account for every scheduled answer and every produced fact, without judging.

The saved trace owns replies/attempts, the real route owns outcomes, and the
scorer owns union/dedup identity. A route label 'written' here is a dry run,
never a database write. Missing or unknown outcomes are blocking, not credit.
"""
import collections
import copy
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a7_g1_build as G
import a7_g23_build as B
from driver.core.xbrl_attach import PUBLIC_DECISIONS

SCHEMA = "a7_producer_conservation/2"
TERMINALS = PUBLIC_DECISIONS + ("abstained_only", "invalid_unreadable",
                               "refused_unreadable", "uncalled")
IDENTITY = ("ordinal", "arm", "source_id", "packet_id", "lane_id")


def contributions(run):
    """The original trace, including every attempt and every uncalled slot."""
    arms, meta, problems = G.materialize(run)
    return meta["trace"], arms, problems


def _identity(row):
    return tuple(row.get(k) for k in IDENTITY)


def _branches_of(row, outcomes):
    """One branch per fact occurrence; one terminal when no fact was emitted."""
    facts, positions = row["facts"], row["fact_positions"]
    branches = []
    for local in range(len(facts)) if facts else [None]:
        position = positions[local] if local is not None and local < len(positions) else None
        outcome, terminal = None, None
        if row["status"] == "answered" and row["readable"]:
            if local is not None:
                outcome = outcomes.get(("fact", position))
                decision = (outcome or {}).get("decision")
                if decision in PUBLIC_DECISIONS:
                    terminal = decision
            elif len(row["abstentions"]) == 1:
                terminal = "abstained_only"
        elif not facts:
            terminal = {"invalid": "invalid_unreadable",
                        "refused": "refused_unreadable",
                        "uncalled": "uncalled"}.get(row["status"])
        branch = collections.OrderedDict((k, row.get(k)) for k in IDENTITY)
        branch.update(fact_index=local, fact_position=position,
                      outcome=copy.deepcopy(outcome), terminal=terminal)
        branches.append(branch)
    return branches


def _conservation_problems(rows, scheduled, branches):
    """Exact identities and occurrences, not merely equal aggregate counts."""
    problems = []
    want = collections.Counter(_identity(r) for r in scheduled)
    got = collections.Counter(_identity(r) for r in rows)
    if got != want or any(n != 1 for n in want.values()):
        problems.append("packet identities differ from the frozen schedule: "
                        "missing %s; extra %s" % (list((want - got).items()),
                                                 list((got - want).items())))
    expected = collections.Counter()
    event_positions = collections.defaultdict(list)
    for row in rows:
        positions, facts = row["fact_positions"], row["facts"]
        if len(positions) != len(facts):
            problems.append("fact positions do not cover every fact in %s" % (_identity(row),))
        event_positions[(row["arm"], row["source_id"])].extend(positions)
        for i in range(len(facts)) if facts else [None]:
            pos = positions[i] if i is not None and i < len(positions) else None
            expected[(_identity(row), i, pos)] += 1
    for key, positions in event_positions.items():
        if any(type(p) is not int for p in positions) or positions != list(range(len(positions))):
            problems.append("event fact positions are not exact and ordered for %s" % (key,))
    observed = collections.Counter((_identity(b), b["fact_index"], b["fact_position"])
                                   for b in branches)
    if observed != expected or any(n != 1 for n in observed.values()):
        problems.append("fact/zero-fact branch identities do not reconcile with their packets")
    for branch in branches:
        if branch["terminal"] not in TERMINALS:
            problems.append("no known terminal for %s fact %s" %
                            (_identity(branch), branch["fact_position"]))
    return problems


def terminals(run, audit_root="/tmp/a7_conservation_audit"):
    """Full producer accounting. The union keeps origins, not extra calls."""
    import build_a5_exp5_kit as A5
    import raw_transport as RT
    from scorers import score_exp5 as SCO

    rows, arms, problems = contributions(run)
    # This reads the frozen plan, not the saved answers/attempt selection again.
    plan = RT.a1_plan_for_run(run["run_dir"])
    scheduled = [dict((k, r[k]) for k in ("source_id", "packet_id", "lane_id"))
                 for r in RT.a1_schedule(plan)]
    for n, row in enumerate(scheduled):
        row.update(ordinal=n, arm=A5.arm_for_call(row["lane_id"])["arm"])
    required_arms = sorted({r["arm"] for r in scheduled})
    for leg in required_arms:
        arms.setdefault(leg, {})
    groups = B.packet_groups(rows)
    outcomes = {}
    for leg in sorted(arms):
        audit = os.path.join(audit_root, leg)
        os.makedirs(audit, exist_ok=True)
        for sid, answer in sorted(arms[leg].items()):
            try:
                route = B.route_for({sid: answer}, audit,
                                    {sid: groups.get(leg, {}).get(sid)})
                outcomes[(leg, sid)] = SCO._rows_for_event(
                    route, sid, answer["facts"], len(answer["abstentions"]))
            except Exception as exc:
                problems.append({"arm": leg, "source_id": sid,
                                 "reason": "route_unaccounted", "why": str(exc)})
    branches = [branch for row in rows for branch in _branches_of(
        row, outcomes.get((row["arm"], row["source_id"]), {}))]
    problems += _conservation_problems(rows, scheduled, branches)

    gold, _key_identity = G.live_key()
    origins = []
    if len(required_arms) == 2:
        a, b = required_arms
        union = SCO.union_answer(gold, arms[a], arms[b], (a, b))
        parents = {(r["arm"], r["source_id"], pos): r
                   for r in rows for pos in r["fact_positions"]}
        for sid, answer in sorted(union.items()):
            for position, group in enumerate(answer["origins"]):
                linked = []
                for origin in group:
                    parent = parents.get((origin["arm"], sid, origin["position"]))
                    if parent is None:
                        problems.append({"reason": "union_origin_unaccounted",
                                         "source_id": sid, "origin": origin})
                    linked.append(dict(origin, **{k: (parent or {}).get(k)
                                                  for k in ("packet_id", "lane_id", "ordinal")}))
                origins.append(dict(source_id=sid, fact_position=position, origins=linked))
    counts = collections.Counter(b["terminal"] or "unresolved" for b in branches)
    attempts = [a for r in rows for a in r["attempts"]]
    return collections.OrderedDict([
        ("schema", SCHEMA), ("arms", required_arms),
        ("scheduled_calls", len(scheduled)),
        ("packets_per_arm", dict(collections.Counter(r["arm"] for r in scheduled))),
        ("packets", rows), ("branches", branches), ("branch_total", len(branches)),
        ("terminal_counts", dict(sorted(counts.items()))),
        ("attempt_total", len(attempts)),
        ("attempt_counts", dict(sorted(collections.Counter(
            "readable" if a["readable"] else a["stage"] for a in attempts).items()))),
        ("union_origins", origins), ("dimensions", dimensions(rows, arms, gold)),
    ]), problems


def dimensions(rows, arms, gold):
    """Descriptive counts; semantic and duplicate rules stay with their owners."""
    from driver.core.fact_match import match_facts
    from scorers import score_exp5 as SCO
    out = collections.OrderedDict()
    out["continuity_hints"] = sum(len(r["continuity_hints"]) for r in rows)
    out["abstentions"] = sum(len(r["abstentions"]) for r in rows)
    out["split_packets"] = sum(len(r["facts"]) > 1 for r in rows)
    out["packet_statuses"] = dict(sorted(collections.Counter(r["status"] for r in rows).items()))
    dup, missed = 0, 0
    for leg in sorted(arms):
        for sid in sorted(gold):
            du = [g for g in gold.get(sid, []) if g.get("du_worthy") is True]
            gold_v2, _gp = SCO._to_v2_with_positions(du)
            prod_v2, _pp = SCO.eligible_produced(arms[leg].get(sid, {}).get("facts", []))
            matched = match_facts(gold_v2, prod_v2)
            dup += sum(len(g) for g in matched.gold_inconclusive)
            missed += len(matched.to_grading_gold)
    out["duplicate_gold_in_inconclusive_groups"] = dup
    out["gold_still_needing_a_ruling"] = missed
    return out


if __name__ == "__main__":
    import a7_prepared_run as PR
    doc, problems = terminals(PR.cli_run(sys.argv))
    print(G._pretty({"accounting": doc, "problems": problems}))
    raise SystemExit(1 if problems else 0)
