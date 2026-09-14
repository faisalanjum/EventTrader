# -*- coding: utf-8 -*-
"""Producer-output conservation, proved rather than asserted.

Counting the answer key's 196 packets and 209 facts is a proof about the KEY.
These prove the other side: what the producer actually returned, and that every
packet in every arm reaches exactly one terminal.
"""
import collections
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import a7_conservation as C   # noqa: E402
import a7_g1_build as G       # noqa: E402

_C = {}


def doc():
    if "doc" not in _C:
        _C["doc"] = C.terminals()
    return _C["doc"]


def test_every_packet_in_every_arm_terminates_exactly_once():
    d, problems = doc()
    assert problems == [], problems[:3]
    seen = collections.Counter((r["arm"], r["packet_id"]) for r in d["packets"])
    assert seen and set(seen.values()) == {1}
    for arm in d["arms"]:
        n = sum(1 for r in d["packets"] if r["arm"] == arm)
        assert n == G.REQUIRED["packets"] == 196, (arm, n)
    assert len(d["packets"]) == len(d["arms"]) * G.REQUIRED["packets"]


def test_the_terminal_vocabulary_is_closed():
    d, _p = doc()
    assert set(d["terminal_counts"]) <= set(C.TERMINALS)
    # terminals count BRANCHES, not calls
    assert sum(d["terminal_counts"].values()) == d["branch_total"]


def test_one_input_can_produce_many_facts_and_every_branch_is_kept():
    """Collapsing a packet to one "strongest" terminal hid every extra branch.

    With this population there are more branches than calls, and the gap is
    exactly the multi-fact packets."""
    d, _p = doc()
    shape = {int(k): v for k, v in d["facts_per_packet"].items()}
    assert sum(shape.values()) == d["scheduled_calls"] == len(d["packets"])
    want = sum(max(1, n) * c for n, c in shape.items())
    assert d["branch_total"] == want
    assert d["branch_total"] > d["scheduled_calls"], (
        "no packet produced more than one fact, so this proves nothing")
    # every branch names its packet and its exact fact position
    seen = collections.Counter(
        (b["arm"], b["packet_id"], b["fact_position"]) for b in d["branches"])
    assert set(seen.values()) == {1}
    for b in d["branches"]:
        assert b["terminal"] in C.TERMINALS
        assert b["arm"] and b["packet_id"] and b["source_id"] and b["lane_id"]


def test_a_multi_fact_packet_keeps_each_fact_separately():
    d, _p = doc()
    multi = [p for p in d["packets"] if len(p["facts"]) > 1]
    assert multi, "no multi-fact packet exists"
    for packet in multi:              # every multi-fact packet, not ten
        kids = [b for b in d["branches"]
                if b["arm"] == packet["arm"]
                and b["packet_id"] == packet["packet_id"]]
        assert len(kids) == len(packet["facts"]), (packet["packet_id"], len(kids))
        assert sorted(b["fact_position"] for b in kids) == \
            sorted(packet["fact_positions"])


def test_every_row_traces_back_to_its_own_raw_reply_and_input_packet():
    """A trace that cannot name its own evidence is not a trace."""
    d, _p = doc()
    for row in d["packets"]:          # THE FULL POPULATION, never a prefix
        assert row["packet_id"] and row["lane_id"]
        if not row["readable"]:
            # an uncalled or refused slot stays EXPLICIT, with its reason
            assert row["why"], row["packet_id"]
            continue
        assert row["raw_path"] and os.path.isfile(row["raw_path"])
        assert G._sha_file(row["raw_path"]) == row["raw_sha256"]
        assert row["source_id"] and row["attempt"] >= 1
        assert len(row["input_sha256"]) == 64
        assert len(row["fact_positions"]) == len(row["facts"])


def test_the_sidecar_reads_the_ONE_trace_and_never_reparses():
    """Conservation used to re-walk the schedule and call the reader a SECOND
    time, so it could drift from the parser that produced the arms."""
    import ast
    import inspect
    # STRUCTURAL, not textual: the previous shape of this check matched its own
    # docstring, which is how a "no second parser" guard can pass while a
    # second parser sits three lines below it.
    tree = ast.parse(inspect.getsource(C))
    called = {n.func.attr for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    called |= {n.func.id for n in ast.walk(tree)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    for banned in ("read_one", "effective_slots"):
        assert banned not in called, banned
    d, _p = doc()
    assert d["scheduled_calls"] == len(d["packets"])
    d, _p = doc()
    assert "continuity_hints" in d["dimensions"]
    assert any(r["fact_positions"] for r in d["packets"]), "no packet origin kept"
    # the positions really partition each event's accumulated facts
    by_event = collections.defaultdict(list)
    for r in d["packets"]:
        by_event[(r["arm"], r["source_id"])].extend(r["fact_positions"])
    for key, positions in by_event.items():
        assert sorted(positions) == list(range(len(positions))), key


def test_the_rejected_terminal_is_the_conflicting_name_law_being_applied():
    d, _p = doc()
    assert d["terminal_counts"].get("rejected", 0) > 0, (
        "no packet was rejected, so the fact-scoped law is not reaching here")
    assert d["terminal_counts"].get("written", 0) > 0, "nothing was written"


def test_the_dimensions_are_reported_and_internally_consistent():
    d, _p = doc()
    dims = d["dimensions"]
    for name in ("continuity_hints", "abstentions", "split_packets",
                 "skipped_packets", "refused_unreadable",
                 "duplicate_produced",
                 "gold_awaiting_a_g1_ruling", "precall_unresolved"):
        assert name in dims, name
        assert isinstance(dims[name], int)
    assert dims["abstentions"] == sum(len(r["abstentions"]) for r in d["packets"])
    assert dims["split_packets"] == sum(1 for r in d["packets"]
                                        if len(r["facts"]) > 1)
    assert dims["refused_unreadable"] == sum(1 for r in d["packets"]
                                             if not r["readable"])


def test_answer_key_conservation_is_kept_as_a_SEPARATE_proof():
    """The two must never be presented as one: 196 key packets and 209 key
    facts describe the answer key, not the producer's output."""
    d, _p = doc()
    produced_facts = sum(len(r["facts"]) for r in d["packets"])
    assert produced_facts != G.REQUIRED["accepted_gold"], (
        "producer output and answer key coincide; that would make the two "
        "proofs indistinguishable and this test meaningless")
