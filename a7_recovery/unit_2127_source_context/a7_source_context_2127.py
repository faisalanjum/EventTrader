# -*- coding: utf-8 -*-
"""The source-CONTEXT version of the served source-only task (Codex SEQ 2127).

It builds ONE thing: the prefix the next source-only phase serves. That prefix
is the prefix `a4_source_taskv2` already builds, with exactly ONE anchored span
replaced. Nothing else moves, no frozen owner is edited in place, and no
historical prompt, script or result is relabelled.

WHY THE SPAN MOVES, from measured evidence. The served role paragraph tells the
reviewer that the located target names the one meaning to interpret and that
the complete event is CONTEXT so that target can be interpreted correctly. It
never says the context is evidence for the reviewer's own FIELDS. Ten of the
thirty-five reported metric facts in the live key were settled as a bare value
while the same source part stated the prior value or the direction for that
exact driver, measurement, population and period
(`unit_2123_post_signature_key/SOURCE_STATE_DISPOSITIONS_2126.json`). That is
an input defect: FINAL_DESIGN 4.3 already scopes the metric state to the source
and is already ordered.

The replacement adds one approved sentence pair immediately after the existing
"Interpret those targets only.", and changes nothing else. It names no field,
no state, no direction and no example; it is equally true for a target whose
part states no prior at all.

NO SEMANTIC WORK HAPPENS HERE. This module reads no fact, no answer, no
finding and no grade; its output is a pure function of the prefix it is given.
"""
import collections
import os
import sys
import textwrap
from pathlib import Path

A7 = Path(__file__).resolve().parents[1]
for _rel in ("unit_2009/owner", "unit_2023_source_correction",
             "unit_2063_source_closeout"):
    sys.path.insert(0, str(A7 / _rel))
import a4_review_composite as R                                    # noqa: E402
import a4_source_taskv2 as V2                                      # noqa: E402
K, INV = R.K, R.INV

VERSION = "a7-source-context/2127"

#: V2's OWN builder, captured before any successor swaps that name. A phase
#: that serves THIS prefix binds it at `C2023._served_prefix`, so reading the
#: live attribute here would call this function again and recurse forever (the
#: discipline V2 records for `_C2023_SERVED_PREFIX`).
_V2_SERVED_PREFIX = V2.served_prefix

#: the sentence the approved wording is inserted after, quoted from the served
#: role so a reworded owner makes the anchor miss and this module refuse.
TARGET_SENTENCE = "Interpret those targets only."
#: the first line of the split cap that follows it, quoted FROM V2's own
#: constant rather than retyped, for the same reason.
_SPLIT_CAP_LINE = V2.SPAN_A_NEW.split("\n")[0]

#: Codex SEQ 2127's approved wording, stored as the one sentence pair it is.
CLARIFICATION = (
    "The target fixes which fact you review. For each permitted field, use "
    "the complete supplied source unless that field's rule restricts it to "
    "the quote, then apply the governing rules in their stated order.")
#: the served paragraph wraps at 84-87 characters (measured on the live
#: prefix), so the block joins it at the same width. Wrapping changes no word,
#: which `test_source_context_2127` asserts rather than assumes.
WRAP = 86
CLARIFICATION_BLOCK = textwrap.fill(CLARIFICATION, width=WRAP)

SPAN_OLD = "%s %s\n" % (TARGET_SENTENCE, _SPLIT_CAP_LINE)
SPAN_NEW = "%s\n%s\n%s\n" % (TARGET_SENTENCE, CLARIFICATION_BLOCK,
                             _SPLIT_CAP_LINE)


def served_prefix(bound):
    """The served source-only prefix with exactly the one context span added."""
    return V2._replace_once(_V2_SERVED_PREFIX(bound), SPAN_OLD, SPAN_NEW,
                            "located-target context")


def provenance(bound):
    """What this version changed, measured - never asserted."""
    base = _V2_SERVED_PREFIX(bound)
    new = served_prefix(bound)
    return collections.OrderedDict([
        ("version", VERSION), ("builds_on", V2.VERSION),
        ("base_prefix_sha256", K._sha(base)),
        ("new_prefix_sha256", K._sha(new)),
        ("bytes_before", len(base)), ("bytes_after", len(new)),
        ("bytes_added", len(new) - len(base)),
        ("spans_replaced", 1),
        ("span_owner", "the served role paragraph, after %r" % TARGET_SENTENCE),
        ("split_cap_owner", "a4_source_taskv2.SPAN_A_NEW"),
        ("clarification_sha256", K._sha(CLARIFICATION)),
        ("owner_sha256", INV.sha_file(os.path.abspath(__file__))),
        ("frozen_owners_edited", 0), ("model_calls", 0)])
