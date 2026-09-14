"""A7 transition, run4: the IMMUTABLE G1 completion plus the final G2/G3
review packet. NO model call is made anywhere in this module.

Codex SEQ 1453. Three products, each on top of an owner that already exists:

    1 g1_final       the run4 completion, frozen once, separated by leg, with
                     every accepted pair, every withheld outcome and its
                     existing reason, the confirmed one-gold/many-produced
                     groups and the disputed identity groups
    2 inventory      G2 = every final matched pair exactly once; G3 = every
                     route-ACCEPTED produced row still unmatched after G1,
                     exactly once - both read back from the scorer's own
                     obligations, never re-derived by a second rule
    3 packet         one rendered prompt per (kind, leg, event), two blind
                     lanes per nonempty batch, armed_calls 0

Nothing here decides meaning. The five meaning fields and the three extras
buckets are read from `score_exp5` through the `a6_launch_freeze` accessors, so
this file contains no semantic list of its own.
"""
import collections
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
while _HERE in sys.path:
    sys.path.remove(_HERE)
sys.path.insert(0, _HERE)

import a7_g1_build as G                                          # noqa: E402
import a7_g1_complete_v2 as C                                    # noqa: E402

SCHEMA_G1 = "a7_g1_run4_completion/1"
SCHEMA_PACKET = "a7_g23_event_candidate/1"

#: the two review kinds, and the model-facing id prefix of each
KIND_MEANING = "G2"
KIND_EXTRAS = "G3"
ID_PREFIX = {KIND_MEANING: "M", KIND_EXTRAS: "X"}

REPO = "/home/faisal/EventMarketDB"
#: the frozen fixtures the draft inputs were composed from
FIXTURES = os.path.join(REPO, ".claude", "plans", "Drivers", "experiments",
                        "fixtures", "events")


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git(*args):
    return subprocess.check_output(("git", "-C", REPO) + args).decode().strip()


def meaning_fields():
    """The five verdict names, from the scorer, through the A6 accessor."""
    return list(G._a6()._meaning_fields())


def extras_buckets():
    """The three extras buckets, from the scorer, through the A6 accessor."""
    return list(G._a6()._extras_buckets())


# ------------------------------------------------------------- 0. the pins --
PIN_KEYS = ("run_tree_sha256", "run_file_count", "root_sha256",
            "candidate_sha256", "prompt_tree_sha256", "rules_block_sha256",
            "git_head", "git_tree")


def refuse(cand_dir, run_dir, pins):
    """-> (state, problems). EVERY expectation is supplied from OUTSIDE.

    `state` is None whenever anything at all does not match, so a caller
    cannot accidentally proceed on a partially checked run.
    """
    problems = []
    missing = [k for k in PIN_KEYS if k not in pins]
    if missing:
        return None, ["no external pin for %s" % ", ".join(missing)]
    for name, want in (("git_head", pins["git_head"]),
                       ("git_tree", pins["git_tree"])):
        got = _git("rev-parse", "HEAD" if name == "git_head" else "HEAD^{tree}")
        if got != want:
            problems.append("%s is %s, not the pinned %s" % (name, got, want))
    root, doc, lanes, ev_problems = C.evidence(
        cand_dir, run_dir, pins["root_sha256"],
        pins["run_tree_sha256"], pins["run_file_count"])
    problems.extend(ev_problems)
    if root is None:
        return None, problems
    if root["candidate_sha256"] != pins["candidate_sha256"]:
        problems.append("the root names candidate %s, not the pinned %s"
                        % (root["candidate_sha256"], pins["candidate_sha256"]))
    if root["prompt_tree_sha256"] != pins["prompt_tree_sha256"]:
        problems.append("the root names prompt tree %s, not the pinned %s"
                        % (root["prompt_tree_sha256"],
                           pins["prompt_tree_sha256"]))
    if root["rules_block_sha256"] != pins["rules_block_sha256"]:
        problems.append("the root names rules block %s, not the pinned %s"
                        % (root["rules_block_sha256"],
                           pins["rules_block_sha256"]))
    # EVERY lane state: one selected valid attempt for every root lane, and no
    # lane outside the root.
    expected = [r["lane_id"] for r in root["rows"]]
    if sorted(lanes) != sorted(expected):
        problems.append("the run carries %d lanes, not the root's %d"
                        % (len(lanes), len(expected)))
    for lane in expected:
        rec = lanes.get(lane) or {}
        if rec.get("selected") is None:
            problems.append("%s has no selected valid attempt" % lane)
    return (root, doc, lanes), problems


# ------------------------------------------------- 1. the G1 completion -----
def _withheld(categories, legs):
    """Every gold row that did NOT earn a link, with its existing reason."""
    out = []
    for (leg, sid, gold_idx), why in categories.items():
        if why == "accepted":
            continue
        out.append(collections.OrderedDict([
            ("leg", leg), ("source_id", sid), ("gold_idx", gold_idx),
            ("reason", why)]))
    return out


def g1_final(doc, legs, lanes, pins):
    """-> (result, problems). The immutable run4 completion, split by leg."""
    per_lane = C.relations_from_run(lanes)
    relations, rel_problems = C.lane_relations(doc, per_lane)
    base, problems = C.complete(doc, legs, per_lane,
                                (pins["run_tree_sha256"],
                                 pins["run_file_count"]))
    problems = list(rel_problems) + list(problems)
    categories = G.terminal_categories(relations, legs)
    pairs, _mp, _inc, report = G.validate_merged(relations, legs)

    by_leg = collections.OrderedDict()
    for leg in sorted(legs):
        accepted = [collections.OrderedDict([
            ("source_id", sid), ("gold_idx", g), ("produced_idx", p)])
            for sid in sorted((pairs.get(leg) or {}))
            for g, p in sorted((pairs[leg] or {})[sid])]
        withheld = [w for w in _withheld(categories, legs) if w["leg"] == leg]
        terminal = collections.OrderedDict(
            (k, sum(1 for (l, _s, _g), v in categories.items()
                    if l == leg and v == k)) for k in G.TERMINAL)
        confirmed = [dict(c, leg=leg, source_id=k[1])
                     for k, v in report.items() if k[0] == leg
                     for c in G.confirmed_duplicate_groups(v)]
        disputed = [dict(c, leg=leg, source_id=k[1])
                    for k, v in report.items() if k[0] == leg
                    for c in v["components"] if c["contested"]]
        gold_rows = sum(len(legs[leg][sid]["unmatched_gold"])
                        for _l, sid in G.expected_groups(legs) if _l == leg)
        if len(accepted) + len(withheld) != gold_rows:
            problems.append(
                "leg %s: %d accepted + %d withheld is not its %d gold rows"
                % (leg, len(accepted), len(withheld), gold_rows))
        if sum(terminal.values()) != gold_rows:
            problems.append("leg %s: terminal categories cover %d, not %d"
                            % (leg, sum(terminal.values()), gold_rows))
        if terminal["accepted"] != len(accepted):
            problems.append("leg %s: %d accepted categories, %d accepted pairs"
                            % (leg, terminal["accepted"], len(accepted)))
        for c in confirmed:
            if c.get("contested"):
                problems.append("leg %s: a contested component reached the "
                                "confirmed duplicate list" % leg)
        by_leg[leg] = collections.OrderedDict([
            ("gold_rows", gold_rows),
            ("terminal_counts", terminal),
            ("accepted_pairs", accepted),
            ("withheld", withheld),
            ("confirmed_duplicate_groups", confirmed),
            ("disputed_identity_groups", disputed)])

    # cross-leg conservation against the ONE shared owner's own totals
    if sum(v["gold_rows"] for v in by_leg.values()) != base["gold_rows"]:
        problems.append("the per-leg gold rows do not sum to %d"
                        % base["gold_rows"])
    for k in G.TERMINAL:
        got = sum(v["terminal_counts"][k] for v in by_leg.values())
        if got != base["terminal_counts"][k]:
            problems.append("terminal %s sums to %d, not the owner's %d"
                            % (k, got, base["terminal_counts"][k]))
    if sum(len(v["accepted_pairs"]) for v in by_leg.values()) != len(
            base["accepted_pairs"]):
        problems.append("the per-leg accepted pairs do not sum to %d"
                        % len(base["accepted_pairs"]))
    for name in ("duplicate_emission_groups", "disputed_identity_groups"):
        mine = "confirmed_duplicate_groups" if name.startswith("dup") else name
        got = sum(len(v[mine]) for v in by_leg.values())
        if got != len(base[name]):
            problems.append("%s sums to %d, not the owner's %d"
                            % (name, got, len(base[name])))

    result = collections.OrderedDict([
        ("schema", SCHEMA_G1),
        ("pins", collections.OrderedDict((k, pins[k]) for k in PIN_KEYS)),
        ("events", base["events"]),
        ("gold_rows", base["gold_rows"]),
        ("terminal_counts", base["terminal_counts"]),
        ("terminal_total", base["terminal_total"]),
        ("incomplete", base["incomplete"]),
        ("scorer_problems", base["scorer_problems"]),
        ("legs", by_leg)])
    return result, problems


def resolutions(doc, legs, lanes):
    """-> {leg: {(sid, gold_idx): produced_idx|None}} - the COMPLETE scalar the
    scorer already consumes, taken from the one relation-to-credit owner."""
    per_lane = C.relations_from_run(lanes)
    relations, _p = C.lane_relations(doc, per_lane)
    out = {}
    for leg, sid in G.expected_groups(legs):
        row = legs[leg][sid]
        lane_pair = (relations.get(leg) or {}).get(sid)
        if not lane_pair or lane_pair[0] is None or lane_pair[1] is None:
            continue
        accepted, _rep = G.event_credit(lane_pair[0], lane_pair[1])
        for g in row["unmatched_gold"]:
            out.setdefault(leg, {})[(sid, g)] = accepted.get(g)
    return out


# ------------------------------------------------- 2. the real public route --
def _event_doc(sid):
    """ONE event exactly as the write-disabled Stage-A route requires it.

    The field set is the route owner's own `V2_EVENT_FIELDS`, so a new required
    field shows up as a KeyError here rather than as a silently dropped input.
    `event_time` is the full ISO source timestamp the route demands; the frozen
    draft input carries the date only, and the anchor used to build those very
    inputs is `date + "T00:00:00"` (build_kfields_inputs.py, `compose`). This
    re-applies that ONE existing convention and refuses any date that already
    carries a time, rather than inventing a second timestamp rule.
    """
    import build_launch_manifest as blm
    from driver.core.driver_write_cli import V2_EVENT_FIELDS
    with io.open(os.path.join(blm.INPUTS, "%s.json" % sid),
                 encoding="utf-8") as fh:
        raw = json.load(fh)
    date = raw["event_date"]
    if len(date) != 10:
        raise ValueError("%s: event_date %r already carries a time; the "
                         "anchoring convention does not apply" % (sid, date))
    raw = dict(raw, event_time=date + "T00:00:00")
    return {k: raw[k] for k in V2_EVENT_FIELDS if k != "items"}


def route_for(arm_by_event, audit_dir):
    """The REAL public write-disabled route, one call per event."""
    from scorers.score_exp5 import route_reply
    out = {}
    for sid in sorted(arm_by_event):
        arm = arm_by_event[sid]
        reply = {"source_id": sid, "facts": arm.get("facts") or [],
                 "abstentions": arm.get("abstentions") or []}
        out[sid] = route_reply(reply, _event_doc(sid), audit_dir)
    return out


def event_meta(gold_by_ev):
    """`score_arm`'s mandatory per-event meta, from the same frozen inputs."""
    out = {}
    for sid in gold_by_ev:
        ev = _event_doc(sid)
        out[sid] = {"event_date": ev["event_time"],
                    "fye_month": ev["fye_month"]}
    return out


# ------------------------------------------- 3. the final review inventory ---
def matched_pairs(gold_by_ev, arm_by_event, resolution):
    """-> {sid: [(gold_idx, produced_idx)]}, EXACTLY what `score_arm` scores.

    Both halves come from the owners `score_arm` itself calls: the
    deterministic links from `match_facts`, and the G1-ruled pairs from
    `score_exp5.grade_unmatched` over the same complete scalar. Nothing is
    matched here.
    """
    from driver.core.fact_match import match_facts
    from scorers import score_exp5 as SCO
    out = collections.OrderedDict()
    for sid in sorted(gold_by_ev):
        du = [g for g in gold_by_ev[sid] if g.get("du_worthy") is True]
        produced = (arm_by_event.get(sid) or {}).get("facts", [])
        gold_v2, gold_pos = SCO._to_v2_with_positions(du)
        prod_v2, prod_pos = SCO._to_v2_with_positions(produced)
        mr = match_facts(gold_v2, prod_v2)
        inconclusive = {gold_pos[id(g)]
                        for grp in mr.gold_inconclusive for g in grp}
        pairs = [(gold_pos[id(g)], prod_pos[id(p)]) for g, p in mr.links]
        ug = [gold_pos[id(g)] for g in mr.to_grading_gold
              if gold_pos[id(g)] not in inconclusive]
        up = [prod_pos[id(p)] for p in mr.to_grading_produced]
        mine = {k: v for k, v in (resolution or {}).items() if k[0] == sid}
        ruled, bad = SCO.grade_unmatched(mine or None, sid, ug, up)
        if bad:
            ruled = []
        out[sid] = sorted(set(pairs) | set(ruled))
    return out


def extras_rows(scored):
    """-> {sid: [produced_idx]} the scorer ITSELF says still owe a bucket.

    Read back from `score_arm` run with no extras verdict at all: every
    `extras_verdict_missing` row is one obligation. Deriving the eligible set
    here instead would be a second copy of the scorer's own rule.
    """
    out = collections.OrderedDict()
    for row in scored.get("ambiguous_rows") or []:
        if row.get("reason") == "extras_verdict_missing":
            out.setdefault(row["sid"], []).append(row["produced_idx"])
    return collections.OrderedDict(
        (sid, sorted(set(v))) for sid, v in sorted(out.items()))


def score_leg(gold_by_ev, arm_by_event, meta, route, resolution,
              grader_verdicts=None, extras_verdicts=None):
    """One unchanged `score_arm` call. Nothing is scored in this module."""
    from scorers import score_exp5 as SCO
    return SCO.score_arm(gold_by_ev, arm_by_event, meta,
                         grader_verdicts, dict(resolution or {}),
                         route=route, extras_verdicts=extras_verdicts)


def meaning_questions(gold_by_ev, arms, resolution_by_leg):
    """-> {leg: {sid: [(gold_idx, produced_idx)]}} - every FINAL matched pair
    exactly once. Needs no route: a pair is matched by the deterministic
    matcher or by an agreed G1 ruling, and by nothing else."""
    out = collections.OrderedDict()
    for leg in sorted(arms):
        out[leg] = matched_pairs(gold_by_ev, arms[leg],
                                 resolution_by_leg.get(leg) or {})
    return out


def write_atomic(path, doc):
    """One fresh immutable artifact. Refuses to overwrite an existing one."""
    if os.path.exists(path):
        raise ValueError("%s already exists; an immutable artifact is written "
                         "once and never edited" % path)
    directory = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(directory):
        os.makedirs(directory)
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with io.open(fd, "w", encoding="utf-8") as fh:
            fh.write(G._pretty(doc) + "\n")
        os.rename(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return G._sha_file(path)
