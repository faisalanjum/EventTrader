#!/usr/bin/env python3
"""XBRL-FIRST deterministic lane (GPT final design, head-to-head verified 2026-07-13; #767 step 1).

WP2: THIS FILE IS NOW A THIN ADAPTER over the neutral matcher (driver/relocation/locator.py —
`match_facts` + `discover_pairings`). The one strict identity law lives THERE:
    exact concept identifier AS STORED (full qname when present; otherwise bare local name,
    never promoted — verified live 109/109) + COMPLETE (axis, member) PAIRS + exactly one
    valid period shape + unit  ->  unique exact-Decimal fact value | None (abstain)
Callers that know the full dimension address pass `pairs`; LEGACY member-only callers cannot
name an axis, so the adapter first discovers the source's DISTINCT pairings for that member
set — more than one → axis-ambiguous → abstain; exactly one → matched on its FULL pairs (the
wrong-axis class can never bind).

Certification: the durable 150-case live gate = test_xbrl_gate.py (selection sha-pinned,
exact Decimal, reconciles all 150; the old uncollected __main__ check is retired).

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
    """THIN ADAPTER — see module docstring. `pairs` (full (axis,member) address) is the
    preferred identity; `member_qnames` is the legacy member-only form."""
    if pairs is not None:
        return LOC.match_facts(xbrls, concept_qname, pairs, period_start, period_end,
                               unit_ref=unit_ref, expected_unit=expected_unit)
    found = LOC.discover_pairings(xbrls, concept_qname, member_qnames,
                                  period_start, period_end)
    if len(found) != 1:
        return None                 # zero = absent; >1 = axis-ambiguous for a member-only ask
    return LOC.match_facts(xbrls, concept_qname, next(iter(found)), period_start, period_end,
                           unit_ref=unit_ref, expected_unit=expected_unit)
