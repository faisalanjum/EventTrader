# -*- coding: utf-8 -*-
"""The zero-call G2/G3 candidate: population, batches, prompts, launchers.

WHY THIS FILE IS SHORT. `a7_g1_build` already owns the whole run lifecycle -
root freeze, receipts, reservations, raw-first capture, accounting,
finalization and resume - and none of it is specific to G1's question shape: it
works on batch ROWS and a prompt map. So this module derives the G2 and G3
populations and emits exactly that shape. A second lifecycle would be a second
owner of the same twelve file kinds, and the two would drift.

WHAT IT CANNOT KNOW YET. A G2 pair is matched either by the deterministic
matcher or by an agreed G1 ruling; a G3 obligation is whatever the scorer still
calls unresolved. With G1 unrun there are no rulings, so this plan is the
FLOOR: every batch here is owed regardless of how G1 rules, and G1's rulings can
only ADD pairs. The document says so in `population_is_a_floor`, and
`rebuild_required_after` names the run that must regrow it. Publishing this as
a final count would understate the bill.
"""
import collections
import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import a7_g1_build as G      # noqa: E402  the lifecycle owner
import a7_g23_build as B     # noqa: E402  the packet owner

SCHEMA = "a7_g23_candidate/1"
CANDIDATE_NAME = "a7_g23_candidate.json"
PROMPT_DIRNAME = "prompts"
#: the run whose rulings can only ADD to this floor
REBUILD_AFTER = "G1"


def _sha(text):
    return G._sha(text)


#: where the write-disabled route leaves its audit. Per RUN and per LEG: the
#: route is a real public call whose result depends on the arm's own facts, so
#: one shared directory would let one leg read another's audit.
AUDIT_ROOT = "/tmp/a7_g23_route_audit"


def populations(primary=G.PRIMARY, audit_root=AUDIT_ROOT):
    """-> (g2, g3, arms, gold, meta, problems).

    g2 = {"leg|sid": [(gold_idx, produced_idx)]}, g3 = {"leg|sid": [idx]}.
    Both come from the owners that will score them, never from a rule restated
    here: the pairs from `matched_pairs`, the obligations from the scorer's own
    `extras_verdict_missing` rows.
    """
    legs, _totals, meta, arms, gold, problems = G.inventory(primary)
    del legs
    ev_meta = B.event_meta(gold)
    g2, g3 = collections.OrderedDict(), collections.OrderedDict()
    unroutable = []
    for leg in sorted(arms):
        pairs = B.matched_pairs(gold, arms[leg], {})
        for sid, rows in pairs.items():
            if rows:
                g2["%s|%s" % (leg, sid)] = list(rows)
        # ROUTE PER EVENT, so one refused event is a named row rather than a
        # silent loss of the whole leg. `score_arm` needs a route for EVERY
        # event, so a leg with any refusal cannot be scored at all - and G3's
        # population comes only from what the scorer itself still calls owed.
        audit = os.path.join(audit_root, leg)
        if not os.path.isdir(audit):
            os.makedirs(audit)
        route, refused = {}, []
        for sid in sorted(arms[leg]):
            try:
                route.update(B.route_for({sid: arms[leg][sid]}, audit))
            except Exception as exc:
                refused.append(collections.OrderedDict([
                    ("leg", leg), ("source_id", sid), ("why", str(exc))]))
        if refused:
            unroutable.extend(refused)
            continue
        scored = B.score_leg(gold, arms[leg], ev_meta, route, {})
        for sid, idxs in B.extras_rows(scored).items():
            if idxs:
                g3["%s|%s" % (leg, sid)] = list(idxs)
    return g2, g3, arms, gold, meta, problems, unroutable


def _rows_and_prompts(kind, batches, build_packet):
    """The SHAPE `a7_g1_build.launchers` and the lifecycle already consume."""
    rows, prompts, of_question = [], collections.OrderedDict(), {}
    for n, batch in enumerate(batches):
        batch_id = "%s-%03d" % (kind, n)
        packet = build_packet(batch_id, batch)
        text = packet["prompt"]
        prompts[batch_id] = text
        rows.append(collections.OrderedDict([
            ("batch_id", batch_id), ("items", len(batch)),
            ("source_ids", [B.source_event(k) for k, _i in batch]),
            ("question_ids", list(packet["question_ids"])),
            ("produced_idxs", list(packet.get("produced_idxs") or [])),
            ("prompt_bytes", len(text.encode("utf-8"))),
            ("prompt_sha256", _sha(text)),
            ("prompt_path", "%s/%s.prompt.txt" % (PROMPT_DIRNAME, batch_id))]))
        for qid in packet["question_ids"]:
            of_question[qid] = batch_id
    return rows, prompts, of_question


def _g2_packet_for(gold, arms, batch):
    """ONE G2 call: the packet owner renders the bytes, this only groups."""
    return B.batch_packet("G2", [
        B.meaning_packet(key.split("|", 1)[0], key.split("|", 1)[1], [pair],
                         gold[key.split("|", 1)[1]],
                         arms[key.split("|", 1)[0]][
                             key.split("|", 1)[1]]["facts"])
        for key, pair in batch])


def _g3_packet_for(gold, arms, batch):
    packets = []
    for key, produced_idx in batch:
        leg, sid = key.split("|", 1)
        srcs = [(gi, gold[sid][gi]) for gi in G.accepted_positions(gold[sid])]
        packets.append(B.extras_packet(leg, sid, [produced_idx],
                                       arms[leg][sid]["facts"], srcs))
    return B.batch_packet("G3", packets)


def freeze(primary=G.PRIMARY):
    """The whole G2/G3 candidate, derived. -> (doc, prompts, problems)."""
    g2, g3, arms, gold, meta, problems, unroutable = populations(primary)
    g2_batches = B.pack_batches(g2)
    g3_batches = B.pack_batches(g3)
    problems = list(problems)
    problems += B.batch_problems(g2_batches)
    problems += B.batch_problems(g3_batches)

    g2_rows, g2_prompts, g2_of = _rows_and_prompts(
        "G2", g2_batches, lambda bid, b: _g2_packet_for(gold, arms, b))
    g3_rows, g3_prompts, g3_of = _rows_and_prompts(
        "G3", g3_batches, lambda bid, b: _g3_packet_for(gold, arms, b))

    prompts = collections.OrderedDict(list(g2_prompts.items())
                                      + list(g3_prompts.items()))
    rows = g2_rows + g3_rows
    launch = G.launchers(rows)
    _key, identity = G.live_key()
    doc = collections.OrderedDict([
        ("schema", SCHEMA),
        ("key_identity", identity),
        ("materialization", meta),
        # THE HONEST SCOPE OF THIS PLAN
        # THE TWO POPULATIONS MOVE IN OPPOSITE DIRECTIONS, so one flag for
        # both was simply false.
        ("g2_population_is_a_floor", True),
        ("g3_population_is_a_ceiling", True),
        ("rebuild_required_after", REBUILD_AFTER),
        ("floor_note",
         "A G2 pair is matched by the deterministic matcher or by an agreed "
         "G1 ruling; with G1 unrun only the first exists, so G1 can only ADD "
         "pairs. These G2 batches are a FLOOR."),
        ("ceiling_note",
         "A G3 obligation is a produced record the scorer still calls "
         "unresolved. A G1 ruling can MATCH such a record and remove its "
         "obligation, so G1 can only REMOVE extras. These G3 batches are a "
         "CEILING."),
        ("g2", collections.OrderedDict([
            ("questions", sum(len(v) for v in g2.values())),
            ("batches", len(g2_batches)),
            ("largest_batch", max([len(b) for b in g2_batches] or [0]))])),
        ("g3", collections.OrderedDict([
            ("questions", sum(len(v) for v in g3.values())),
            ("batches", len(g3_batches)),
            ("largest_batch", max([len(b) for b in g3_batches] or [0])),
            # A LEG WITH ANY REFUSED EVENT CANNOT BE SCORED, so it contributes
            # no G3 obligation. Recorded, never rounded away: a zero here means
            # "not derivable yet", not "nothing is owed".
            ("legs_scored", sorted(set(k.split("|", 1)[0] for k in g3))),
            ("unroutable_event_legs", len(unroutable)),
            ("unroutable", unroutable)])),
        ("batching", collections.OrderedDict([
            ("max_items_per_call", B.MAX_ITEMS_PER_CALL),
            ("batches", len(rows)),
            ("rows", rows)])),
        ("launchers", collections.OrderedDict([
            ("count", len(launch)),
            ("lanes_per_batch", len(G.GRADER_LANES)),
            ("rows", launch)])),
        ("question_to_batch", collections.OrderedDict(
            sorted(list(g2_of.items()) + list(g3_of.items())))),
        ("prompt_bytes", collections.OrderedDict([
            ("total", sum(r["prompt_bytes"] for r in rows)),
            ("largest", max([r["prompt_bytes"] for r in rows] or [0]))])),
        ("call_plan", call_plan(len(launch), 0) if False else
         call_plan(sum(1 for r in launch if r["batch_id"].startswith("G2-")),
                   sum(1 for r in launch if r["batch_id"].startswith("G3-")))),
        ("made_calls", 0)])
    return doc, prompts, problems


#: the ceiling the Work Order fixes. Not ours to move.
CEILING = 6000


def call_plan(g2_launchers, g3_launchers):
    """-> the WHOLE remaining bill, and a retry cap that fits under the ceiling.

    Every primary is counted, including the fresh exact-v3 producer run that
    the current G1 population does NOT yet reflect: G1 today grades v1 producer
    output, so its numbers are a diagnostic, not a frozen population.

    THE RETRY CAP IS HEADROOM, NOT A PER-ROW RESERVATION. Reserving one retry
    for every row would book more than twice the primaries for a failure mode
    measured at roughly one call in six hundred. The cap is simply what is left
    under the ceiling, declared as a hard stop, and reported beside the
    observed-rate expectation so nobody reads it as an expectation.
    """
    spent, _prov = G.all_prior_calls()
    producer = G.REQUIRED["answers"]
    g1 = len(G.GRADER_LANES) * G.freeze()[0]["batching"]["batches"]
    primaries = producer + g1 + g2_launchers + g3_launchers
    after = spent + primaries
    return collections.OrderedDict([
        ("spent_before", spent),
        ("producer_v3", producer),
        ("g1", g1), ("g2", g2_launchers), ("g3", g3_launchers),
        ("primaries", primaries),
        ("after_primaries", after),
        ("ceiling", CEILING),
        ("retry_cap", max(0, CEILING - after)),
        ("under_ceiling", after < CEILING),
        ("note", "G1/G2/G3 counts are shapes from v1 producer output and must "
                 "be re-derived after the fresh v3 producer run"),
    ])


def write(out_dir, primary=G.PRIMARY):
    """Write the frozen G2/G3 candidate. Refuses anything with a problem."""
    doc, prompts, problems = freeze(primary)
    if problems:
        return None, problems
    pdir = os.path.join(out_dir, PROMPT_DIRNAME)
    if not os.path.isdir(pdir):
        os.makedirs(pdir)
    for batch_id, text in prompts.items():
        with io.open(os.path.join(pdir, "%s.prompt.txt" % batch_id), "w",
                     encoding="utf-8") as fh:
            fh.write(text)
    path = os.path.join(out_dir, CANDIDATE_NAME)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(G._pretty(doc) + "\n")
    return path, []


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/a7_g23_candidate"
    path, problems = write(out)
    if problems:
        print("REFUSED:", len(problems))
        for p in problems[:8]:
            print("   *", str(p)[:200])
        raise SystemExit(1)
    with io.open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    print("candidate  :", path)
    print("sha256     :", G._sha_file(path))
    print("key digest :", doc["key_identity"]["key_digest"])
    print("G2         :", doc["g2"])
    print("G3         :", doc["g3"])
    print("launchers  :", doc["launchers"]["count"])
    print("made_calls :", doc["made_calls"])
