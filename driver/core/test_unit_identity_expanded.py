"""#827 Stage 3 — the candidate-unit policy must read the DECLARED namespace.

`Unit.name` is Arelle's `stringValue` (`XBRL/xbrl_basic_nodes.py:178,257`), so
it carries THE FILING'S OWN PREFIX. Keying unit policy on that text asks which
alias a filer happened to type, not which currency they declared:

    filing declares                     namespace        candidate units
    iso4217 -> the official ISO-4217    correct          usd, m_usd    lawful
    iso4217 -> some other URI           NOT iso4217      usd, m_usd    WRONG
    cur     -> the official ISO-4217    correct          (none)        WRONG

All three BIND — the storage-integrity comparison is doing its job. The defect
is entirely in the policy, and the replacement was already built and left
unwired: `bind_graph_fact` publishes `unit_measures_expanded`,
`unit_numerator_expanded` and `unit_denominator_expanded`, whose own comment
says they are "what unit policy must consume".

COVERAGE, NAMED EXPLICITLY so the public-callable pin can see it: every test
below drives `driver.core.xbrl_attach.candidate_units_for` through both of its
parameters — `measures_expanded` for a simple unit and `numerator_expanded`
for a divide unit — with a lawful and an unlawful case for each.

Authority for the identity rule: Namespaces in XML 1.0 Third Edition
(W3C Rec 2009-12-08) §3 — a prefix is a scoped alias; identity is
(namespace URI, local name). The currency namespace itself is XBRL 2.1
(Rec 2003-12-31 + errata 2013-02-20) §4.8.2, `http://www.xbrl.org/2003/iso4217`.
"""
import pytest

from driver.core.xbrl_attach import candidate_units_for
from driver.relocation.inline_html import bind_graph_fact

#: The official currency namespace. Written once, here, and every case below
#: is spelled against it — a fixture that types its own URI can claim a
#: currency its document never declared.
ISO4217 = 'http://www.xbrl.org/2003/iso4217'
INSTANCE = 'http://www.xbrl.org/2003/instance'
OTHER = 'http://example.org/not-a-currency-registry'
GAAP = 'http://fasb.org/us-gaap/2023'
CIK = '0000320193'


def _doc(measure, extra_ns=(), denominator=None):
    """One lawful inline filing whose unit declares exactly `measure`."""
    ns = ' '.join(f'xmlns:{p}="{u}"' for p, u in extra_ns)
    body = (f'<xbrli:measure>{measure}</xbrli:measure>' if denominator is None
            else (f'<xbrli:divide><xbrli:unitNumerator>'
                  f'<xbrli:measure>{measure}</xbrli:measure>'
                  f'</xbrli:unitNumerator><xbrli:unitDenominator>'
                  f'<xbrli:measure>{denominator}</xbrli:measure>'
                  f'</xbrli:unitDenominator></xbrli:divide>'))
    return (f'<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
            f'xmlns:xbrli="{INSTANCE}" xmlns:us-gaap="{GAAP}" {ns}><body>'
            f'<ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
            f'<xbrli:identifier scheme="http://www.sec.gov/CIK">{CIK}'
            f'</xbrli:identifier></xbrli:entity><xbrli:period>'
            f'<xbrli:startDate>2024-01-01</xbrli:startDate>'
            f'<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            f'</xbrli:context><xbrli:unit id="u1">{body}</xbrli:unit>'
            f'</ix:resources></ix:header>'
            f'<p><ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
            f'unitRef="u1" scale="6" decimals="-6">390</ix:nonFraction></p>'
            f'</body></html>')


def _bind(measure, stored_name, *, extra_ns=(), denominator=None,
          is_divide='0'):
    """Bind, with `stored_name` being what the WRITER would really have kept.

    Arelle renders the filing's own prefix, so a filing writing `cur:USD` is
    stored as `cur:USD`. Handing the binder a name the writer could not have
    produced tests an impossible world — an earlier probe of mine did exactly
    that and reported a refusal that no filing can cause.
    """
    return bind_graph_fact(
        _doc(measure, extra_ns, denominator), inline_element_id='f1',
        concept='us-gaap:A', context_id='c1', unit_ref='u1',
        unit_name=stored_name, is_divide=is_divide, period_type='duration',
        start_date='2024-01-01', end_date='2024-07-01', dims=(),
        entity_cik=CIK, raw_value='390,000,000', concept_namespace=GAAP,
        graph_concept_qname='us-gaap:A')


def _units(measure, stored_name, **kw):
    bound, why = _bind(measure, stored_name, **kw)
    assert bound is not None, f'the fixture itself does not bind: {why}'
    return sorted(candidate_units_for(bound['unit_measures_expanded'],
                                      bound['unit_numerator_expanded']))


# ---------------------------------------------------------------------------
# THE CURRENCY RULE
# ---------------------------------------------------------------------------

def test_USD_under_a_LAWFUL_ALIAS_still_yields_the_dollar_units():
    """MUST-ALLOW. `cur:USD` with `cur` bound to the official ISO-4217
    namespace is US dollars — a filer's choice of prefix is not a fact about
    money. Keyed on the stored spelling this returned NOTHING and the fact
    silently lost every candidate unit."""
    assert _units('cur:USD', 'cur:USD',
                  extra_ns=(('cur', ISO4217),)) == ['m_usd', 'usd']


def test_the_SAME_TEXT_under_a_DIFFERENT_URI_is_not_dollars():
    """MUST-REFUSE twin, identical but for the URI behind the prefix. A filing
    may lawfully bind `iso4217` to something else; that is not a currency
    declaration, and reading the spelling granted it dollars anyway."""
    assert _units('iso4217:USD', 'iso4217:USD',
                  extra_ns=(('iso4217', OTHER),)) == []


def test_the_ORDINARY_declaration_is_unchanged():
    """The control that keeps the two above honest: the overwhelmingly common
    filing must behave exactly as before."""
    assert _units('iso4217:USD', 'iso4217:USD',
                  extra_ns=(('iso4217', ISO4217),)) == ['m_usd', 'usd']


def test_a_NON_USD_official_currency_keeps_the_frozen_unknown_answer():
    """Behaviour preserved deliberately: another official currency is money we
    do not canonicalise, and `unknown` is the honest carrier. The change is
    about WHICH NAMESPACE was declared, never about widening the currency
    policy."""
    assert _units('iso4217:EUR', 'iso4217:EUR',
                  extra_ns=(('iso4217', ISO4217),)) == ['unknown']


# ---------------------------------------------------------------------------
# THE INSTANCE-NAMESPACE UNITS — same law, different namespace
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('prefix', ['xbrli', 'i'])
def test_SHARES_is_read_whatever_prefix_the_filing_binds(prefix):
    """`shares` is an XBRL 2.1 instance-namespace measure. A filing may bind
    any prefix to that namespace — `i:shares` is as lawful as `xbrli:shares`."""
    extra = () if prefix == 'xbrli' else ((prefix, INSTANCE),)
    assert _units(f'{prefix}:shares', 'shares', extra_ns=extra) == ['count']


def test_PURE_keeps_its_frozen_answer():
    assert 'count' in _units('xbrli:pure', 'pure')


def test_an_instance_LOCAL_NAME_under_a_FOREIGN_URI_is_not_shares():
    """MUST-REFUSE twin for the instance units: the word `shares` under a
    namespace that is not the XBRL instance namespace is a different measure."""
    assert _units('x:shares', 'x:shares', extra_ns=(('x', OTHER),)) == []


# ---------------------------------------------------------------------------
# DIVIDE UNITS — the numerator carries the same law
# ---------------------------------------------------------------------------

def test_a_DIVIDE_numerator_under_a_lawful_alias_is_still_dollars():
    """MUST-ALLOW. Per-share money written with an aliased currency prefix."""
    assert _units('cur:USD', 'cur:USDshares', is_divide='1',
                  denominator='xbrli:shares',
                  extra_ns=(('cur', ISO4217),)) == ['usd']


def test_a_DIVIDE_numerator_under_a_FOREIGN_URI_is_not_dollars():
    """MUST-REFUSE twin. The name is never split to find this out — the
    numerator's own declared identity answers it."""
    assert _units('iso4217:USD', 'iso4217:USDshares',
                  is_divide='1', denominator='xbrli:shares',
                  extra_ns=(('iso4217', OTHER),)) == []


def test_a_NON_USD_divide_numerator_keeps_the_frozen_unknown():
    assert _units('iso4217:CAD', 'iso4217:CADshares',
                  is_divide='1', denominator='xbrli:shares',
                  extra_ns=(('iso4217', ISO4217),)) == ['unknown']


# ---------------------------------------------------------------------------
# THE FIELDS COME FROM THE BOUND ELEMENT, on both resolution paths
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('element_id', ['f1', ''])
def test_the_expanded_measures_come_from_the_BOUND_unitRef(element_id):
    """Whether the element is found by its exact id or by the
    (name, contextRef, unitRef) fallback, the expanded measures must be the
    ones on THAT element's unit — never re-parsed and never guessed."""
    bound, why = bind_graph_fact(
        _doc('cur:USD', (('cur', ISO4217),)), inline_element_id=element_id,
        concept='us-gaap:A', context_id='c1', unit_ref='u1',
        unit_name='cur:USD', is_divide='0', period_type='duration',
        start_date='2024-01-01', end_date='2024-07-01', dims=(),
        entity_cik=CIK, raw_value='390,000,000', concept_namespace=GAAP,
        graph_concept_qname='us-gaap:A')
    assert bound is not None, why
    assert bound['unit_measures_expanded'] == ((ISO4217, 'USD'),)