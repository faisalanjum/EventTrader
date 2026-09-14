# -*- coding: utf-8 -*-
"""The restatement-AUTHORITY version of the served source-only task (SEQ 2143).

It builds ONE thing: the prefix this round serves. That prefix is the prefix
`a7_source_context_2127` already builds, with exactly ONE anchored span
replaced. Nothing else moves, no frozen owner is edited in place, and no
historical prompt, script or result is relabelled.

WHY THE SPAN MOVES, from measured evidence. The completed eight-source round
left exactly one open issue, recorded by the reader itself: it asked whether a
prior-period comparative column restated inside a current filing is in scope as
a fact of THIS event, and gave as its reason that "no rule states a scope
filter for restated comparatives". A rule does state it, and has since
2026-07-14; the served task simply never carried it. The served Rule 1 item 5 -
emit each distinct fact exactly once - is the clause the reader reached
instead, so the missing authority is served immediately after it, where the
question actually arises.

NOTHING HERE IS RETYPED. The clause is READ from its live owner and pinned
TWICE: the owning file by its bytes, and the clause itself by its own bytes.
A moved, reworded, renumbered or mis-selected authority therefore refuses
instead of silently serving text this version was not written against. The
pins are what make "verbatim" checkable rather than asserted.

NO SEMANTIC WORK HAPPENS HERE. This module reads no fact, answer, finding or
grade, and names no company, period, field, state, direction or count. Its
output is a pure function of the prefix it is given and the pinned clause.
"""
import collections
import io
import os
import sys
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
for _rel in ("unit_2009/owner", "unit_2063_source_closeout",
             "unit_2127_source_context"):
    sys.path.insert(0, str(A7 / _rel))
import a4_review_composite as R                                    # noqa: E402
import a4_source_taskv2 as V2                                      # noqa: E402
import a7_source_context_2127 as V3                                # noqa: E402
F, K, INV = R.F, R.K, R.INV

VERSION = "a7-source-authority/2143"

#: V3's OWN builder, captured before any successor swaps that name - the same
#: recursion discipline V2 and V3 each record for their own base.
_V3_SERVED_PREFIX = V3.served_prefix

#: The live owner of the clause, addressed the way every other authority in
#: this harness is addressed: relative to the bench repo root the existing
#: review owner already resolves. Nothing here computes a root of its own.
CLAUSE_OWNER_REL = ".claude/plans/Drivers/FinalDesign/15_CandidateFactPacket.md"
CLAUSE_OWNER_SHA256 = ("aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4b"
                       "c5c66b7e98c")
#: the clause's OWN bytes. Selection is by identity, never by line number,
#: heading, keyword or proximity: the clause is the one line of its owner that
#: hashes to this, and anything but exactly one match refuses.
CLAUSE_SHA256 = ("b9013beddb49d0150f1bc11accd362687d498e1eab01d3bd1f43ddc8c5e"
                 "b5c6d")

#: the served Rule 1 item the authority answers, quoted from the served prefix
#: so a reworded rule makes this anchor miss and this module refuse.
TARGET_ITEM = ("5. Emit each distinct fact exactly ONCE — never restate "
               "one fact as two\n   records.\n")
#: the one line of our own wording. It says WHERE the text comes from and that
#: it binds; it adds no direction, no count and no example.
LABEL = ("**Restatement across events (governing contract, quoted verbatim; "
         "binding).**")


def owner_path():
    """The clause owner's live path, from the review owner's own bench root."""
    return os.path.join(F.BIR._REPO, CLAUSE_OWNER_REL)


def clause():
    """The governing clause, read from its live owner and pinned twice."""
    path = owner_path()
    if not os.path.isfile(path):
        raise ValueError("the authority owner does not exist: %s" % path)
    got = INV.sha_file(path)
    if got != CLAUSE_OWNER_SHA256:
        raise ValueError("the authority owner is %s, not the pinned %s: %s"
                         % (got, CLAUSE_OWNER_SHA256, path))
    found = [line for line in io.open(path, encoding="utf-8").read().split("\n")
             if K._sha(line) == CLAUSE_SHA256]
    if len(found) != 1:
        raise ValueError("the pinned clause appears %d times in %s, not once"
                         % (len(found), path))
    return found[0]


def span_new():
    """The anchored item, unchanged, followed by the served authority."""
    return "%s\n%s\n%s\n" % (TARGET_ITEM, LABEL, clause())


def served_prefix(bound):
    """The served source-only prefix with exactly the one authority added."""
    return V2._replace_once(_V3_SERVED_PREFIX(bound), TARGET_ITEM, span_new(),
                            "restatement authority")


def provenance(bound):
    """What this version changed, measured - never asserted."""
    base = _V3_SERVED_PREFIX(bound)
    new = served_prefix(bound)
    text = clause()
    return collections.OrderedDict([
        ("version", VERSION), ("builds_on", V3.VERSION),
        ("base_prefix_sha256", K._sha(base)),
        ("new_prefix_sha256", K._sha(new)),
        ("bytes_before", len(base)), ("bytes_after", len(new)),
        ("bytes_added", len(new) - len(base)),
        ("spans_replaced", 1),
        ("span_owner", "the served Rule 1 item quoted in TARGET_ITEM"),
        ("clause_owner_path", owner_path()),
        ("clause_owner_sha256", INV.sha_file(owner_path())),
        ("clause_sha256", K._sha(text)),
        ("clause_bytes", len(text.encode("utf-8"))),
        ("clause_served_verbatim_once", new.count(text) == 1),
        ("label_sha256", K._sha(LABEL)),
        ("owner_sha256", INV.sha_file(os.path.abspath(__file__))),
        ("frozen_owners_edited", 0), ("model_calls", 0)])
