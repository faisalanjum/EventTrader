# -*- coding: utf-8 -*-
"""The zero-call G2/G3 candidate: population, batches, prompts, launchers.

WHY THIS FILE IS SHORT. `a7_g1_build` already owns the whole run lifecycle -
root freeze, receipts, reservations, raw-first capture, accounting,
finalization and resume - and none of it is specific to G1's question shape: it
works on batch ROWS and a prompt map. So this module derives the G2 and G3
populations and emits exactly that shape. A second lifecycle would be a second
owner of the same twelve file kinds, and the two would drift.

WHAT IT IS BUILT ON. A G2 pair is matched either by the deterministic matcher
or by an agreed G1 ruling; a G3 obligation is whatever the scorer still calls
unresolved. Both depend on G1, so `freeze` REFUSES without the approved G1
lifecycle and every population here is derived under it - the FINAL bill, named
by the `g1_identity` the document and each per-kind candidate carry. This used
to run with G1 unrun and publish a floor and a ceiling; the flags, the notes
and `rebuild_required_after` follow the binding, they are not labels on the
same document (Codex SEQ 1866 item 2).
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
#: NOTHING has to run after this to regrow the population. G1 is applied
#: before the questions are derived, so there is no later run whose rulings
#: could still add a pair or remove an extra.
REBUILD_AFTER = None


def _sha(text):
    return G._sha(text)


#: where the write-disabled route leaves its audit. Per RUN and per LEG: the
#: route is a real public call whose result depends on the arm's own facts, so
#: one shared directory would let one leg read another's audit.
AUDIT_ROOT = "/tmp/a7_g23_route_audit"


def populations(primary=G.PRIMARY, audit_root=AUDIT_ROOT, g1=None):
    """-> (g2, g3, arms, gold, meta, problems, unroutable, derived).

    g2 = {"leg|sid": [(gold_idx, produced_idx)]}, g3 = {"leg|sid": [idx]}.
    Both come from the owners that will score them, never from a rule restated
    here: the pairs from `matched_pairs`, the obligations from the scorer's own
    `extras_verdict_missing` rows.

    `g1` is the APPROVED G1 LIFECYCLE HANDLE, not a resolution map. An earlier
    version of this took the map itself, which let any caller hand in the
    identity answers instead of deriving them from the lifecycle that proved
    them - the caller-invented truth Codex SEQ 1864 item 3 forbids. The map is
    derived here, once, and returned in `derived["resolutions"]` so the
    official consumer reads back exactly the one that was used rather than
    walking the lifecycle a second time.
    """
    legs, _totals, meta, arms, gold, problems = G.inventory(primary)
    del legs
    # THE ONE LIFECYCLE WALK for this whole derivation. The public
    # `official_resolutions` proves the lifecycle for itself, so calling it
    # here and again in the official consumer proved the same run twice; the
    # walk happens once, here, and its PROVED state travels in `derived` for
    # the private owners that need it afterwards. No public entry accepts a
    # state, so this is not a bypass (Codex SEQ 1871 item 1).
    g1_state = B._lifecycle(g1) if g1 else None
    resolutions = B._resolutions_from(g1_state, primary) if g1 else {}
    # THE ORIGINAL PRODUCER INPUTS, from the trace that already records them.
    # Each answered call's `fact_positions` is where ITS facts landed in the
    # event's accumulated list, so the list of those position lists IS the
    # packet boundary set the real route needs. Without it every fact becomes
    # its own raw input and a lawful multi-fact split is flattened - the route
    # then never sees the branch outcomes Step 1 A7.9 requires.
    groups = collections.OrderedDict()
    for row in meta["trace"]:
        if row.get("status") != "answered":
            continue
        groups.setdefault(row["arm"], collections.OrderedDict()).setdefault(
            row["source_id"], []).append(list(row["fact_positions"]))
    ev_meta = B.event_meta(gold)
    g2, g3 = collections.OrderedDict(), collections.OrderedDict()
    unroutable = []
    #: WHAT THIS RUN ALREADY DERIVED, kept rather than thrown away. The route
    #: below is a real public call whose audit depends on the arm's own facts,
    #: so calling it a second time to fill a return value would be a second
    #: routing of the same evidence. `score_leg_official` needs exactly these
    #: two, per leg, and they are the ones that were actually scored here.
    #: THE SHAPE score_leg_official ALREADY READS: derived["routes"][leg] and
    #: derived["event_meta"]. My first attempt invented a per-leg dict and my
    #: proof then checked that invention instead of the caller, which is how a
    #: KeyError survived a green test.
    derived = collections.OrderedDict(
        [("routes", collections.OrderedDict()), ("event_meta", ev_meta),
         ("resolutions", resolutions), ("g1_state", g1_state),
         ("resolution_source",
          "the approved G1 lifecycle" if g1 else
          "NONE - these populations are the pre-G1 floor, not the final bill")])
    for leg in sorted(arms):
        # THE VALIDATED G1 RESOLUTION, derived above from the lifecycle. With
        # none these populations are the pre-G1 floor and ceiling, not the
        # final bill: an accepted G1 identity link adds a pair and removes the
        # extra it was owed for (Codex SEQ 1860 item 3).
        pairs = B.matched_pairs(gold, arms[leg],
                                (resolutions or {}).get(leg) or {})
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
                route.update(B.route_for(
                    {sid: arms[leg][sid]}, audit,
                    {sid: (groups.get(leg) or {}).get(sid)}))
            except Exception as exc:
                refused.append(collections.OrderedDict([
                    ("leg", leg), ("source_id", sid), ("why", str(exc))]))
        if refused:
            unroutable.extend(refused)
            continue
        derived["routes"][leg] = route
        # THE SAME RESOLUTION FOR G3. This passed `{}` while G2 above used the
        # validated map, so a produced fact G1 had already linked to a gold row
        # still counted as an unbucketed extra and was asked a G3 question it
        # no longer owed. Both halves of one population must be derived under
        # one identity answer (Codex SEQ 1864 item 3).
        scored = B.score_leg(gold, arms[leg], ev_meta, route,
                             (resolutions or {}).get(leg) or {})
        for sid, idxs in B.extras_rows(scored).items():
            if idxs:
                g3["%s|%s" % (leg, sid)] = list(idxs)
    return g2, g3, arms, gold, meta, problems, unroutable, derived


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


def _g2_packet_for(gold, arms, batch, run, inputs):
    """ONE G2 call: the packet owner renders the bytes, this only groups.

    `run` and `inputs` are REQUIRED by the packet owner - the reference card
    needs the validated producer and the calendar comes from the verified
    source handle. Supplying neither used to leave both to a default.
    """
    return B.batch_packet("G2", [
        B.meaning_packet(key.split("|", 1)[0], key.split("|", 1)[1], [pair],
                         gold[key.split("|", 1)[1]],
                         arms[key.split("|", 1)[0]][
                             key.split("|", 1)[1]]["facts"],
                         run, inputs=inputs)
        for key, pair in batch])


def _g3_packet_for(gold, arms, batch, run):
    packets = []
    for key, produced_idx in batch:
        leg, sid = key.split("|", 1)
        srcs = [(gi, gold[sid][gi]) for gi in G.accepted_positions(gold[sid])]
        packets.append(B.extras_packet(leg, sid, [produced_idx],
                                       arms[leg][sid]["facts"], srcs, run))
    return B.batch_packet("G3", packets)


def freeze(primary=G.PRIMARY, inputs=None, audit_root=None, g1=None):
    """The whole G2/G3 candidate, derived. -> (doc, prompts, problems).

    `inputs` is the VERIFIED source handle from the loading boundary; it is
    carried through to the packet owner rather than let each packet find its
    own calendar. `primary` is the validated producer identity the packets are
    built for. `g1` is the APPROVED G1 LIFECYCLE HANDLE.

    G1 IS REQUIRED HERE, as a refusal rather than a default. G2 asks about
    matched pairs and G3 about what is left over, so both populations depend on
    which unmatched records G1 ruled identical. Building them without it asked
    the questions over the PRE-G1 FLOOR while the scorer later scores the
    post-G1 bill - the stale floor Codex SEQ 1864 item 3 forbids.
    """
    if not g1:
        return None, {}, [collections.OrderedDict([
            ("reason", "g1_lifecycle_required"),
            ("why", "the G2/G3 populations are defined by the G1 identity "
                    "rulings; without the approved lifecycle these questions "
                    "would be asked over the pre-G1 floor")])]
    # THE VERIFIED SOURCE HANDLE IS REQUIRED TOO, and for the same reason: a
    # G2 packet built with `inputs=None` still renders, but `meaning_packet`
    # silently sets event_context=None, so the grader is asked about a fact
    # with none of the producer's calendar, menu or source context. Succeeding
    # quietly with less evidence than the question needs is the defect
    # (Codex SEQ 1866 item 3).
    if not inputs:
        return None, {}, [collections.OrderedDict([
            ("reason", "verified_inputs_required"),
            ("why", "G2 asks about a produced fact in its event's context; "
                    "without the verified source handle every packet would "
                    "render with event_context=None and still succeed")])]
    # THE AUDIT ROOT IS PASSED, not inherited. `populations` binds its default
    # at definition time, so setting the module attribute afterwards changed
    # nothing and every audit went to the module's own default path.
    (g2, g3, arms, gold, meta, problems, unroutable,
     _derived) = populations(primary,
                             audit_root if audit_root else AUDIT_ROOT, g1=g1)
    g2_batches = B.pack_batches(g2)
    g3_batches = B.pack_batches(g3)
    problems = list(problems)
    # AN UNROUTABLE EVENT MEANS THE BILL IS INCOMPLETE. `populations` skips
    # that leg's G3 obligations and records why, but the reason never reached
    # `problems`, so `write` published a FINAL candidate with problems=[] and a
    # short bill. The later official scorer refuses it, which is exactly why
    # this must refuse first: a final candidate is a publication, and one that
    # cannot derive its own bill must not be rendered at all
    # (Codex SEQ 1869 item 2a).
    if unroutable:
        # RETURN BEFORE ANY PROMPT IS RENDERED. Adding the reason to `problems`
        # but building the document anyway still produced a final candidate and
        # its bytes; a bill that cannot be derived must stop the publication,
        # not annotate it.
        return None, {}, [collections.OrderedDict([
            ("reason", "unroutable_event"), ("leg", u.get("leg")),
            ("source_id", u.get("source_id")), ("why", u.get("why"))])
            for u in unroutable]
    problems += B.batch_problems(g2_batches)
    problems += B.batch_problems(g3_batches)

    g2_rows, g2_prompts, g2_of = _rows_and_prompts(
        "G2", g2_batches,
        lambda bid, b: _g2_packet_for(gold, arms, b, primary, inputs))
    g3_rows, g3_prompts, g3_of = _rows_and_prompts(
        "G3", g3_batches,
        lambda bid, b: _g3_packet_for(gold, arms, b, primary))

    prompts = collections.OrderedDict(list(g2_prompts.items())
                                      + list(g3_prompts.items()))
    rows = g2_rows + g3_rows
    launch = G.launchers(rows)
    _key, identity = G.live_key()
    doc = collections.OrderedDict([
        ("schema", SCHEMA),
        # THE PRODUCER THIS CANDIDATE IS FOR. official_verdict_maps refuses a
        # candidate built for another run, and it can only do that if the
        # identity travels with the candidate.
        ("producer_identity", primary),
        # THE EXACT G1 LIFECYCLE THESE QUESTIONS WERE DERIVED UNDER. Without
        # it a candidate names only its producer, so an older candidate for
        # the same producer - with every hash correct - could stand in as the
        # final one (Codex SEQ 1866 item 2).
        ("g1_identity", B.g1_identity(g1)),
        ("key_identity", identity),
        # THE ACTUAL PAIR AND INDEX POPULATIONS. The g2/g3 blocks below are
        # COUNTS; the verdict map needs the pairs themselves, keyed
        # "leg|source_id", which is what it iterates.
        ("g2_pairs", g2),
        ("g3_idxs", g3),
        ("materialization", meta),
        # THE HONEST SCOPE OF THIS PLAN.
        # These two said FLOOR and CEILING because the populations used to be
        # derived with G1 unrun. `freeze` now REFUSES without the approved
        # lifecycle and the pairs above come from its validated rulings, so
        # both directions are already applied and there is nothing left for a
        # later G1 to add or remove. The flags follow the binding above - they
        # are not a relabelling of the same document (Codex SEQ 1866 item 2).
        ("g2_population_is_a_floor", False),
        ("g3_population_is_a_ceiling", False),
        ("rebuild_required_after", REBUILD_AFTER),
        ("floor_note",
         "A G2 pair is matched by the deterministic matcher or by an agreed "
         "G1 ruling. Both are applied here under the G1 lifecycle named in "
         "g1_identity, so these G2 batches are the FINAL bill, not a floor."),
        ("ceiling_note",
         "A G3 obligation is a produced record the scorer still calls "
         "unresolved. A G1 ruling can MATCH such a record and remove its "
         "obligation; those rulings are applied here, so these G3 batches are "
         "the FINAL bill, not a ceiling."),
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
        # THE REMAINING CALLS, from the launcher rows that ARE the unrun work.
        # `call_plan` used to project a whole future run here - completed
        # producer calls and published G1 lanes counted as future primaries,
        # `G.freeze` re-run merely to count, and a retry cap against a
        # superseded global target - and even the trimmed version reported a
        # partial old subtotal as if it were total spending. The launchers are
        # the single owner of what is left to call, so they are simply counted
        # (Codex SEQ 1871 item 2).
        ("remaining_calls", collections.OrderedDict([
            ("g2", sum(1 for r in launch if r["batch_id"].startswith("G2-"))),
            ("g3", sum(1 for r in launch if r["batch_id"].startswith("G3-"))),
            ("total", len(launch)),
            ("note", "the launcher rows for work that has NOT run. Completed "
                     "producer and G1 spending keeps its own historical "
                     "ledgers and is not restated here.")])),
        ("made_calls", 0)])
    return doc, prompts, problems


# `CEILING` and `call_plan` ARE DELETED (Codex SEQ 1871 item 2).
#
# `call_plan` projected a future producer run that has already happened: it
# added `G.REQUIRED["answers"]` completed producer calls and 206 published G1
# lanes as FUTURE primaries and called `G.freeze` again just to count batches.
# Trimming it to the remaining launchers was still wrong, because
# `G.all_prior_calls` enumerates only two named old grading runs and two probe
# directories - not the complete producer and G1 history - so labelling that
# subtotal `spent_before` and deriving `retry_cap`/`under_ceiling` from a hard
# 6000 target stated a total nobody measured against a target that is
# superseded.
#
# The remaining G2/G3 bill now comes from the launcher rows themselves, which
# already are that bill, and is reported in the candidate as `remaining_calls`.
# The historical ledgers stay exactly as they are and are referenced, not
# restated. The frozen package call limits are unchanged; no new spending
# engine exists.

# ------------------------------------------- the task-kind seam, both ways --
#: each kind's own rules block; the batch owner renders exactly one of them
KIND_RULES = {"G2": B.meaning_rules, "G3": B.extras_rules}


def kind_binding(doc, batch_id):
    """The machine-only binding both G2 and G3 parsers need: the exact
    question ids this batch asked, reconstructed from the frozen candidate and
    never from the reply."""
    rows = [r for r in doc["batch_rows"] if r["batch_id"] == batch_id]
    if len(rows) != 1:
        raise ValueError("%s names %d batch rows" % (batch_id, len(rows)))
    return collections.OrderedDict([("question_ids",
                                     list(rows[0]["question_ids"]))])


G.register_task_kind("G2", kind_binding, B.read_meaning_reply,
                     B.reconcile_meaning)
G.register_task_kind("G3", kind_binding, B.read_extras_reply,
                     B.reconcile_extras)


def kind_candidate(kind, doc, rows, identity):
    """ONE kind's candidate, in the shape the EXISTING lifecycle consumes.

    Same fields `freeze_root`, `prompt_tree_sha` and `load_frozen` already
    read for G1 - `batch_rows`, `launchers.owner_sha256`, `rules_block_sha256`
    - plus `task_kind`, which is the only new field and the only thing the
    seam dispatches on. Nothing here is a second lifecycle.
    """
    rules = KIND_RULES[kind]()
    launch = G.launchers(rows)
    return collections.OrderedDict([
        ("schema", SCHEMA), ("task_kind", kind),
        ("producer_identity", doc.get("producer_identity")),
        # THE SAME G1 IDENTITY the whole document carries, so the PERSISTED
        # per-kind candidate - which is what official_verdict_maps actually
        # loads - names the lifecycle its questions came from.
        ("g1_identity", doc.get("g1_identity")),
        ("key_identity", identity),
        ("rules_block_sha256", G._sha(rules)),
        ("batch_rows", rows),
        ("batching", collections.OrderedDict([
            ("max_items_per_call", B.MAX_ITEMS_PER_CALL),
            ("batches", len(rows))])),
        ("launchers", collections.OrderedDict([
            ("owner_sha256", G.owner_hashes()["grade_batch_owner"]),
            ("count", len(launch)),
            ("lanes_per_batch", len(G.GRADER_LANES)),
            ("rows", launch)])),
        ("questions", sum(len(r["question_ids"]) for r in rows)),
        # THE REAL POPULATION, not the statistical summary. Reading the
        # counts here made the candidate describe its own size instead of
        # naming the pairs the verdict map must resolve.
        ("population", doc["g2_pairs"] if kind == "G2" else doc["g3_idxs"]),
        ("population_counts", doc["g2"] if kind == "G2" else doc["g3"]),
        ("made_calls", 0)])


def write_kind(out_dir, kind, doc, prompts, identity):
    """Write ONE kind's candidate where the lifecycle expects to load it."""
    rows = [r for r in doc["batching"]["rows"]
            if r["batch_id"].startswith(kind + "-")]
    pdir = os.path.join(out_dir, PROMPT_DIRNAME)
    if not os.path.isdir(pdir):
        os.makedirs(pdir)
    for row in rows:
        with io.open(os.path.join(out_dir, row["prompt_path"]), "w",
                     encoding="utf-8") as fh:
            fh.write(prompts[row["batch_id"]])
    path = os.path.join(out_dir, G.CANDIDATE_NAME)
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(G._pretty(kind_candidate(kind, doc, rows, identity)) + "\n")
    return path, G._sha_file(path)


def write(out_dir, primary=G.PRIMARY, g1=None, inputs=None,
          audit_root=None):
    """Write the frozen G2/G3 candidate. Refuses anything with a problem.

    `inputs` is the handle `a7_g23_build.load_verified_inputs` RETURNS. It had
    no parameter here at all, so every write called freeze with inputs=None.

    `audit_root` is where the write-disabled route leaves its per-leg audit.
    `freeze` has always taken one; `write` did not pass it, so every audit went
    to the module default under /tmp - which, inside the recovery boundary, is
    an ephemeral tmpfs that dies with the run. The route audit is the evidence
    that the route happened, so it has to land somewhere durable
    (Codex SEQ 1869 item 2b).
    """
    doc, prompts, problems = freeze(primary, inputs=inputs, g1=g1,
                                    audit_root=audit_root)
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


# THE MODULE CLI IS DELETED (Codex SEQ 1867 item 2).
#
# It called `load_verified_inputs(manifest, G.PRIMARY, bench)`, but
# `G.PRIMARY` is the PATH string "/tmp/a6_prepared_run" while the loader
# needs the validated producer IDENTITY dict - so the branch raised
# AttributeError and `write` was never reached. It also bound neither the
# current grading scorer nor the reference inventory, so even fixed it
# would have been a second bootstrap beside the supported one.
#
# `write(out_dir, primary, g1=, inputs=)` IS the supported entry: the
# caller supplies the validated producer, the approved G1 lifecycle handle
# and the handle `load_verified_inputs` returns, through the existing
# initialization owners. Nothing here is replaced by a new bootstrap.
