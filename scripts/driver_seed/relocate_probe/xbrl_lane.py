#!/usr/bin/env python3
"""XBRL-FIRST deterministic lane (GPT final design, head-to-head verified 2026-07-13; #767 step 1).

WP2: THIS FILE IS A THIN ADAPTER over `driver/relocation/locator.py`
(`match_facts` + `discover_pairings`), and the law it delegates to CHANGED in #827 Stage 3.

    WAS: exact concept identifier AS STORED (full qname when present; otherwise bare
         local name) + COMPLETE (axis, member) PAIRS + period + unit -> exact value
    NOW: the request shape is validated and the route ABSTAINS.

The old law authorised on a PREFIX — text with no namespace — so it could not tell
`us-gaap:Revenues` from the same local name under a rebound prefix, and its unit rule
searched opaque `unitRef` ids for `usd`/`dollar`/`share`. This request shape carries no
namespace, so nothing here can be repaired into identity; the honest answer is abstention
until a caller supplies expanded names. Route A (`locator.locate`) is the route that can
answer, because it holds the filing document.
Callers that know the full dimension address pass `pairs` (THE identity). A DIMENSIONED
member-only request is INCOMPLETE identity → abstain, always — an axis is NEVER inferred,
not even from uniqueness. Dimensionless requests ([] members, no pairs) stay legal. Supplying
BOTH inputs (pairs plus any non-None member_qnames, including []) is rejected.

Certification: NONE, and that is the honest state. The durable 150-case live gate
(`test_xbrl_gate.py`) was RETIRED in #827 Stage 3 together with the law it certified —
its per-case verdicts described prefix-based authorization, which has been withdrawn.
Retirement is accounted for in
`.claude/plans/Drivers/experiments/harness/receipts_827/26_withdrawn_certification_ledger.md`.
This adapter cannot be certified again until a caller supplies expanded identities.

SEPARATE from tier1 on purpose: the value-known certified lane stays untouched (the naive
seg_members list-fix broke 50/1761 certified records — STATE.md).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'driver', 'relocation'))
import locator as LOC

HERE = os.path.dirname(__file__)


def resolve(xbrls, concept_qname, member_qnames, period_start, period_end, unit_ref=None,
            expected_unit=None, pairs=None):
    """THIN ADAPTER — see module docstring. `pairs` (the full (axis,member) address) is THE
    identity. A DIMENSIONED member-only request is INCOMPLETE identity → abstain, always —
    an axis is NEVER inferred, not even from uniqueness (the wrong-axis class). Dimensionless
    requests ([] members) are fully specified and stay legal."""
    if pairs is not None:
        if member_qnames is not None:              # [] is STILL a supplied input — truthiness
            raise ValueError("pass pairs OR member_qnames, never both")   # hid it (reproduced)
        return LOC.match_facts(xbrls, concept_qname, pairs, period_start, period_end,
                               unit_ref=unit_ref, expected_unit=expected_unit)
    if member_qnames:
        return None                 # dimensioned member-only: incomplete identity, abstain
    return LOC.match_facts(xbrls, concept_qname, [], period_start, period_end,
                           unit_ref=unit_ref, expected_unit=expected_unit)
