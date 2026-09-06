V3=/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/bench_1306/.claude/plans/Drivers/experiments/harness_g1v3
cat > "$V3/a7_g23_run.py" <<'EOF'
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


def populations(primary=G.PRIMARY):
    """-> (g2, g3, arms, gold, meta, problems).

    g2 = {"leg|sid": [(gold_idx, produced_idx)]}, g3 = {"leg|sid": [idx]}.
    Both come from the owners that will score them, never from a rule restated
    here: the pairs from `matched_pairs`, the obligations from the scorer's own
    `extras_verdict_missing` rows.
    """
    legs, _totals, meta, arms, gold, problems = G.inventory(primary)
    del legs
    route = B.route_for(arms[sorted(arms)[0]], B.AUDIT_DIR) \
        if hasattr(B, "AUDIT_DIR") else None
    ev_meta = B.event_meta(gold)
    g2, g3 = collections.OrderedDict(), collections.OrderedDict()
    for leg in sorted(arms):
        pairs = B.matched_pairs(gold, arms[leg], {})
        for sid, rows in pairs.items():
            if rows:
                g2["%s|%s" % (leg, sid)] = list(rows)
        try:
            scored = B.score_leg(gold, arms[leg], ev_meta, route, {})
        except Exception as exc:                 # the scorer refused: report it
            problems.append("leg %s does not score: %s" % (leg, exc))
            continue
        for sid, idxs in B.extras_rows(scored).items():
            if idxs:
                g3["%s|%s" % (leg, sid)] = list(idxs)
    return g2, g3, arms, gold, meta, problems


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


def _g2_packet_for(gold, arms, batch_id, batch):
    """ONE G2 call. A batch holds at most one item per SOURCE EVENT, so each
    entry is packed as its own event packet and the parts are concatenated by
    the packet owner - never re-rendered here."""
    parts, qids = [], []
    for key, pair in batch:
        leg, sid = key.split("|", 1)
        packet = B.meaning_packet(leg, sid, [pair], gold[sid],
                                  arms[leg][sid]["facts"])
        parts.append(packet["prompt"])
        qids.extend(q["question_id"] for q in packet["questions"])
    return {"prompt": "\n".join(parts), "question_ids": qids}


def _g3_packet_for(gold, arms, batch_id, batch):
    parts, qids = [], []
    for key, produced_idx in batch:
        leg, sid = key.split("|", 1)
        srcs = [(gi, gold[sid][gi])
                for gi in G.accepted_positions(gold[sid])]
        packet = B.extras_packet(leg, sid, [produced_idx],
                                 arms[leg][sid]["facts"], srcs)
        parts.append(packet["prompt"])
        qids.extend(q["question_id"] for q in packet["questions"])
    return {"prompt": "\n".join(parts), "question_ids": qids}


def freeze(primary=G.PRIMARY):
    """The whole G2/G3 candidate, derived. -> (doc, prompts, problems)."""
    g2, g3, arms, gold, meta, problems = populations(primary)
    g2_batches = B.pack_batches(g2)
    g3_batches = B.pack_batches(g3)
    problems = list(problems)
    problems += B.batch_problems(g2_batches)
    problems += B.batch_problems(g3_batches)

    g2_rows, g2_prompts, g2_of = _rows_and_prompts(
        "G2", g2_batches, lambda bid, b: _g2_packet_for(gold, arms, bid, b))
    g3_rows, g3_prompts, g3_of = _rows_and_prompts(
        "G3", g3_batches, lambda bid, b: _g3_packet_for(gold, arms, bid, b))

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
        ("population_is_a_floor", True),
        ("rebuild_required_after", REBUILD_AFTER),
        ("floor_note",
         "A G2 pair is matched by the deterministic matcher or by an agreed "
         "G1 ruling; with G1 unrun only the first exists. These batches are "
         "owed however G1 rules, and G1 can only add more."),
        ("g2", collections.OrderedDict([
            ("questions", sum(len(v) for v in g2.values())),
            ("batches", len(g2_batches)),
            ("largest_batch", max([len(b) for b in g2_batches] or [0]))])),
        ("g3", collections.OrderedDict([
            ("questions", sum(len(v) for v in g3.values())),
            ("batches", len(g3_batches)),
            ("largest_batch", max([len(b) for b in g3_batches] or [0]))])),
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
        ("made_calls", 0)])
    return doc, prompts, problems


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
EOF
echo written; wc -l "$V3/a7_g23_run.py"