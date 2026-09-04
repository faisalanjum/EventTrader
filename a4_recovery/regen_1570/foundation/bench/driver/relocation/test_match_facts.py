"""The value-unknown route FAILS CLOSED — it no longer matches anything.

WHAT THIS FILE USED TO BE. A pin battery for `match_facts` / `match_facts_explain`,
"the neutral matcher": a concept authorized by comparing one prefixed string to
another, and — when the caller gave no `unitRef` — a unit authorized by looking
for `usd`, `dollar` or `share` INSIDE an opaque unit id.

WHY IT IS NOT THAT ANY MORE (#827 Stage 3). Neither test states identity:

  * a prefix is a scoped alias (Namespaces in XML 1.0 3e §3). Two documents
    agreeing on the short name `us-gaap:` proves they chose the same alias, not
    that they mean the same taxonomy — and a filing may bind that alias to any
    URI it likes;
  * a `unitRef` is an XML IDREF the FILER picks. `fraud_usd_marker`,
    `dollarNotCurrency` and `shareholder_notes` each satisfied the substring
    rule and returned a value. All three were reproduced through this door.

THE REQUEST SHAPE CANNOT CARRY THE ANSWER. It has a prefixed qname and an opaque
id and no namespace anywhere, so there is nothing to expand and nothing to
compare. A partially working raw-string matcher is worse than none, because it
answers. Route A (`locator.locate`) holds the filing document and therefore the
in-scope declarations, and that is where identity is proven — see
`test_route_a_unit_identity.py`.

THE 150-CASE GATE THAT CERTIFIED THE OLD LAW WAS RETIRED WITH IT, accounted for
in `receipts_827/26_withdrawn_certification_ledger.md`. It is not re-pinned as
150 abstentions: a certification of a withdrawn law is not evidence, at any size.

WHAT SURVIVES HERE. The public contract: the route refuses, it refuses for a
named reason, request-shape errors stay distinguishable from it, and deceptive
spellings get no purchase.

    venv/bin/python -m pytest driver/relocation/test_match_facts.py -q
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed',
                                'relocate_probe'))
sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed'))
import locator as LOC                                        # noqa: E402
import xbrl_lane                                             # noqa: E402

CONCEPT = 'us-gaap:Revenues'
PERIOD = ('2024-01-01', '2024-03-31')


def _blob(unit='usd', concept=CONCEPT, value='100'):
    return [json.dumps({concept: [
        {'value': value, 'fact_id': 'f-1', 'unitRef': unit,
         'period': {'startDate': '2024-01-01', 'endDate': '2024-04-01'}}]})]


# ---------------------------------------------------------------------------
# THE CONTRACT — one named refusal, whatever it is asked
# ---------------------------------------------------------------------------

def test_a_WELL_FORMED_request_is_refused_with_ONE_truthful_reason():
    """Not `concept_missing`, not `no_candidate` — those said something about
    the DATA. The truth is about the REQUEST: it cannot state identity."""
    value, reason = LOC.match_facts_explain(_blob(), CONCEPT, [], *PERIOD)
    assert value is None
    assert reason == 'insufficient_semantic_identity'


def test_the_value_only_form_agrees():
    assert LOC.match_facts(_blob(), CONCEPT, [], *PERIOD) is None


def test_the_seed_ADAPTER_inherits_the_refusal():
    """`xbrl_lane.resolve` is a thin delegate; it must not develop its own
    opinion now that the thing it delegates to abstains."""
    assert xbrl_lane.resolve(_blob(), CONCEPT, [], *PERIOD) is None


# ---------------------------------------------------------------------------
# MUST-REFUSE — the deceptive spellings that used to authorize
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('unit,expected', [
    ('fraud_usd_marker', 'money'),
    ('dollarNotCurrency', 'money'),
    ('USD_this_is_not_a_currency', 'money'),
    ('shareholder_notes', 'nonmoney'),
    ('shares_outstanding_notes', 'nonmoney'),
])
def test_a_DECEPTIVE_unit_id_gets_no_authority(unit, expected):
    """Each contains `usd`, `dollar` or `share` and means nothing of the kind.
    The substring rule returned a value for these; it is deleted, not narrowed,
    and no larger word list replaces it."""
    value, reason = LOC.match_facts_explain(_blob(unit), CONCEPT, [], *PERIOD,
                                            expected_unit=expected)
    assert value is None
    assert reason == 'insufficient_semantic_identity'


@pytest.mark.parametrize('stored,asked', [
    ('evil:Revenues', 'us-gaap:Revenues'),
    ('us-gaap:Revenues', 'evil:Revenues'),
    ('Revenues', 'us-gaap:Revenues'),
    ('us-gaap:Revenues', 'us-gaap:Revenues'),
])
def test_NO_concept_spelling_authorizes_ANYTHING(stored, asked):
    """Including the case that "should" work — the last row. That is the point:
    this route cannot tell a genuine match from a coincidence of aliases, so it
    must claim neither. Under the old law that row bound, and it could not
    justify doing so."""
    value, reason = LOC.match_facts_explain(_blob(concept=stored), asked, [],
                                            *PERIOD)
    assert value is None
    assert reason == 'insufficient_semantic_identity'


# ---------------------------------------------------------------------------
# REQUEST-SHAPE ERRORS STAY DISTINGUISHABLE — each isolated
# ---------------------------------------------------------------------------
# A caller sending a broken ASK still learns that, rather than getting the
# generic refusal. Each case is malformed in exactly ONE way, so no other
# validator can be what produced the reason.

@pytest.mark.parametrize('bad', [
    'x:A=x:M', 3, None,
    [('x:A',)], [('x:A', 'x:M', 'extra')], [('x:A', 3)], [(' x:A', 'x:M')],
    [('x:A', 'x:M'), ('x:A', 'x:N')],          # repeated axis: never collapse
    [('x:A', 'x:M'), ('x:A', 'x:M')],          # ...even when identical
    ['x:A=x:M'], [{'x:A': 'x:M'}],
])
def test_a_malformed_PAIRS_request_says_so(bad):
    """THE FULL MATRIX, restored. Each row was reproduced before it was fixed:
    unhashable items crashed with TypeError, and a repeated axis silently
    COLLAPSED through `frozenset` — two different addresses becoming one. That
    is request validation, not matching, so withdrawing the matcher does not
    withdraw it."""
    got, reason = LOC.match_facts_explain(_blob(), CONCEPT, bad, *PERIOD)
    assert got is None and reason == 'bad_request_pairs', f'{bad!r} -> {reason}'


@pytest.mark.parametrize('lawful', [
    [('x:A', 'x:M')],
    [['x:A', 'x:M']],                          # JSON turns tuples into LISTS
])
def test_a_LAWFUL_pairs_request_reaches_the_IDENTITY_refusal(lawful):
    """MUST-ALLOW twin, and the reason the matrix above cannot be satisfied by
    calling everything malformed. A well-formed address — including one that has
    been through `json.dumps`/`loads`, which is how it arrives in practice — must
    pass validation and be refused for the REAL reason. Under the old law these
    returned a value; they must not return one now, and they must not be
    mislabelled as malformed either."""
    assert json.loads(json.dumps([('x:A', 'x:M')])) == [['x:A', 'x:M']]
    got, reason = LOC.match_facts_explain(_blob(), CONCEPT, lawful, *PERIOD)
    assert got is None
    assert reason == 'insufficient_semantic_identity'


@pytest.mark.parametrize('bad', ['   ', '', [], ['usd'], 3, {'u': 1}, ' usd '])
def test_a_malformed_UNIT_request_says_so(bad):
    """Malformed unit SHAPES, pinned separately from the pairs matrix so neither
    can cover for the other. ` usd ` is in this list deliberately: a padded id is
    a DIFFERENT id, and repairing it by stripping would be the request-side twin
    of the spelling repairs this round removed."""
    assert LOC.match_facts_explain(_blob(), CONCEPT, [], *PERIOD,
                                   unit_ref=bad)[1] == 'bad_request_unit'


def test_an_EXACT_unit_ref_passes_validation_and_reaches_the_refusal():
    """MUST-ALLOW twin: a lawful unpadded id is not a malformed request."""
    assert LOC.match_facts_explain(_blob(), CONCEPT, [], *PERIOD,
                                   unit_ref='usd')[1] == \
        'insufficient_semantic_identity'


def test_a_malformed_PERIOD_request_says_so():
    assert LOC.match_facts_explain(_blob(), CONCEPT, [], 'not-a-date',
                                   '2024-03-31')[1] == 'bad_request_period'


# ---------------------------------------------------------------------------
# ADAPTER BEHAVIOUR — the seed lane's own rules, not the matcher's output
# ---------------------------------------------------------------------------
# `xbrl_lane.resolve` decides what a REQUEST may look like before it delegates.
# That decision survives the matcher's withdrawal untouched, so these are kept
# with their value assertions replaced by the refusal — the SHAPE rules are what
# they were always testing.

def test_the_adapter_REFUSES_a_member_only_request_outright():
    """An axis is NEVER inferred, not even when the pairing is unique. This
    raises no delegation at all: the adapter answers `None` from its own rule,
    which is why it still discriminates now that the matcher abstains."""
    b = _blob()
    assert xbrl_lane.resolve(b, CONCEPT, ['x:USMember'], *PERIOD) is None


def test_the_adapter_REJECTS_pairs_and_members_together():
    """Mutual exclusion, and `[]` still counts as a supplied input — the subtle
    half. This is an adapter contract violation and raises, so it is
    distinguishable from every abstention below it."""
    with pytest.raises(ValueError, match='never both'):
        xbrl_lane.resolve(_blob(), CONCEPT, ['x:USMember'], *PERIOD,
                          pairs=[('x:OnlyAxis', 'x:USMember')])
    with pytest.raises(ValueError, match='never both'):
        xbrl_lane.resolve(_blob(), CONCEPT, [], *PERIOD,
                          pairs=[('x:OnlyAxis', 'x:USMember')])


def test_a_fully_specified_adapter_request_reaches_the_refusal():
    """MUST-ALLOW twin for both rules above: a dimensionless `[]` ask and a
    `pairs=` ask are each fully specified, so they pass the adapter's own gate
    and are refused by the route — not by the adapter."""
    assert xbrl_lane.resolve(_blob(), CONCEPT, [], *PERIOD) is None
    assert xbrl_lane.resolve(_blob(), CONCEPT, None, *PERIOD,
                             pairs=[('x:OnlyAxis', 'x:USMember')]) is None


def test_the_shape_errors_are_CHECKED_BEFORE_the_identity_refusal():
    """Order matters and is asserted: a request that is BOTH malformed and
    identity-less reports the malformity. Otherwise the generic refusal would
    swallow every diagnosis a caller could act on."""
    assert LOC.match_facts_explain(_blob('fraud_usd_marker'), CONCEPT,
                                   [('axis',)], *PERIOD,
                                   expected_unit='money')[1] == \
        'bad_request_pairs'
