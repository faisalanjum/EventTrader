"""#827 Stage 3 — Route A: what a unit IS, and whether the graph means that one.

TWO LAWS, deliberately separate, because collapsing them breaks one or the other.

  MEANING    comes from the FILING's expanded measures — (namespace URI, local
             name) read where the measure is written. A prefix is an alias, so
             `cur:USD` bound to the official ISO-4217 URI is dollars, and
             `iso4217:USD` under a filing that rebound `iso4217` elsewhere is
             not a currency at all.

  INTEGRITY  asks a different question: is the graph row describing this unit?
             The writer stores `unit.stringValue` (XBRL/xbrl_basic_nodes.py),
             and `graph_unit_spelling` derives that SAME serialization from the
             filing by namespace, so the two are compared EXACTLY. No prefix is
             interpreted; the concatenated divide name is never split.

WHY BOTH. I first replaced the old raw-string gate with meaning alone, and a
graph row labelled `unknownunit` bound against a filing declaring dollars.
Spelling alone is no better — it refuses the lawful `cur:USD` alias, which is
the false negative this work started from.

WHAT THE OLD RULE DID, and why it could not be repaired in place: it looked up
`(Unit.name, is_divide)` in a table of graph spellings. That is prefixed text
with no namespace, so it answered "did two documents happen to pick the same
alias?" — which is neither of the questions above.

Spec sources:
  Namespaces in XML 1.0 3e §3 — identity is (namespace URI, local name)
  https://www.w3.org/TR/xml-names/#dt-expname
  XBRL 2.1 (Rec 2003-12-31 + errata 2013-02-20) §4.8.2 — a measure is a QName
"""
import importlib.util
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from driver.relocation import locator as LOC          # noqa: E402

#: The Route-A fixtures already exist and are already certified; building a
#: second set here would be a second definition of "a lawful filing".
_spec = importlib.util.spec_from_file_location(
    'ra_fixtures', os.path.join(_HERE, 'test_route_a.py'))
RA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RA)

ISO = 'http://www.xbrl.org/2003/iso4217'


def _rebind(html, prefix, uri):
    """The SAME lawful filing, with only the unit prefix and the URI it is
    bound to changed. Every other byte is identical, so nothing but the
    namespace question can explain a difference in outcome."""
    return (html.replace('xmlns:iso4217="%s"' % ISO,
                         'xmlns:%s="%s"' % (prefix, uri))
                .replace('<xbrli:measure>iso4217:USD</xbrli:measure>',
                         '<xbrli:measure>%s:USD</xbrli:measure>' % prefix))


def _run(html, facts):
    return LOC.locate(RA.ANCHOR, RA.src(facts, html))


def _graph(unit_name, is_divide='0'):
    return {'unit_name': unit_name, 'is_divide': is_divide}


# ---------------------------------------------------------------------------
# MEANING — the filing's expanded measures decide
# ---------------------------------------------------------------------------

def test_a_LAWFUL_ALIAS_for_the_official_currency_URI_is_the_same_unit():
    """MUST-ALLOW. `cur` is as valid a name for the ISO-4217 namespace as
    `iso4217`; a filer choosing it still states US dollars. The old table knew
    only the spelling `iso4217:USD`, so this correct filing was dropped whole."""
    html = _rebind(RA.doc(body_rows=RA.ROW_390), 'cur', ISO)
    r = _run(html, [RA.fact(meaning=_graph('cur:USD'))])
    assert len(r['items']) == 1, r['status']


def test_a_REBOUND_prefix_is_NOT_the_currency_it_imitates():
    """MUST-REFUSE, and the dangerous direction. The filing declares
    `iso4217 -> urn:evil`, so `iso4217:USD` names something that is not an
    ISO-4217 currency. The graph's spelling MATCHES here — storage integrity is
    satisfied — and only the expanded identity can refuse it."""
    html = _rebind(RA.doc(body_rows=RA.ROW_390), 'iso4217', 'urn:evil')
    r = _run(html, [RA.fact(meaning=_graph('iso4217:USD'))])
    assert r['items'] == []
    assert r['status'] == 'no_proven_match'


def test_a_measure_OUTSIDE_the_route_s_three_readings_still_abstains():
    """MUST-REFUSE, and the control that the fix did not widen the route: the
    scope is exactly the three readings the ratified whitelist admits."""
    html = RA.doc(body_rows=RA.ROW_390).replace(
        '<xbrli:measure>iso4217:USD</xbrli:measure>',
        '<xbrli:measure>iso4217:EUR</xbrli:measure>')
    assert _run(html, [RA.fact(meaning=_graph('iso4217:EUR'))])['items'] == []


# ---------------------------------------------------------------------------
# INTEGRITY — the graph must be describing the same unit
# ---------------------------------------------------------------------------

def test_a_graph_LABEL_that_is_not_the_filings_spelling_abstains():
    """MUST-REFUSE. `unknownunit` is not a serialization of `iso4217:USD`, so
    the row and the filing are not discussing one unit. This is the assertion I
    wrongly weakened: meaning alone let it through."""
    assert _run(RA.doc(body_rows=RA.ROW_390),
                [RA.fact(meaning=_graph('unknownunit'))])['items'] == []


def test_a_graph_row_claiming_a_DIVIDE_unit_abstains_on_a_plain_one():
    """MUST-REFUSE. Structure changes what the number means: a per-share claim
    against a plain-dollars declaration is not a spelling difference."""
    assert _run(RA.doc(body_rows=RA.ROW_390),
                [RA.fact(meaning=_graph('iso4217:USD', '1'))])['items'] == []


def test_a_graph_row_naming_a_DIFFERENT_real_unit_abstains():
    assert _run(RA.doc(body_rows=RA.ROW_390),
                [RA.fact(meaning=_graph('shares'))])['items'] == []


# ---------------------------------------------------------------------------
# ONE UNIT, TWO IDS — an id is the filer's choice, not an identity
# ---------------------------------------------------------------------------

_ROW2 = ('<tr><td>Widget revenue</td><td><ix:nonFraction id="f-2" '
         'name="us-gaap:Revenues" contextRef="c-1" unitRef="usd2" scale="6" '
         'decimals="-6" format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')
_USD2 = ('<xbrli:unit id="usd2"><xbrli:measure>iso4217:USD</xbrli:measure>'
         '</xbrli:unit>')


def test_TWO_unitRef_IDS_for_ONE_unit_are_NOT_ambiguous():
    """MUST-ALLOW. A filing may lawfully declare `usd` and `usd2` for the same
    unit. Keyed on the id, one series looked like two and the whole result was
    thrown away as `ambiguous` — a correct filing answered with nothing."""
    html = RA.doc(body_rows=RA.ROW_390 + _ROW2, ctx_extra=_USD2)
    r = _run(html, [RA.fact(), RA.fact(fid='f-2', unit='usd2')])
    assert r['status'] != 'ambiguous'
    assert len(r['items']) == 1


def test_TWO_unitRef_IDS_for_DIFFERENT_units_STAY_apart():
    """MUST-REFUSE twin. Merging on the expanded structure must not merge units
    that genuinely differ — otherwise the rule above could be satisfied by
    ignoring units altogether."""
    shares = ('<xbrli:unit id="usd2"><xbrli:measure>xbrli:shares'
              '</xbrli:measure></xbrli:unit>')
    html = RA.doc(body_rows=RA.ROW_390 + _ROW2, ctx_extra=shares)
    r = _run(html, [RA.fact(),
                    RA.fact(fid='f-2', unit='usd2',
                            meaning=_graph('shares'))])
    assert r['status'] == 'ambiguous' or len(r['items']) <= 1


# ---------------------------------------------------------------------------
# ISOLATED MUTATIONS — each law must bite ALONE
# ---------------------------------------------------------------------------

MUTANTS = {
    # Remove MEANING -> the rebound `urn:evil` filing attaches as money, while
    # the lawful alias keeps working (so the mutation is not a blanket break).
    'expanded meaning': (
        '            sem_unit = XN.route_a_semantic_unit(declared_unit)\n'
        '            if sem_unit not in accept:',
        '            sem_unit = None\n'
        '            if False:'),
    # Remove INTEGRITY -> `unknownunit` attaches, while the alias still works.
    'stored spelling': (
        '            if spelled != unit_name:\n'
        '                continue',
        '            if False:\n'
        '                continue'),
}


@pytest.fixture(scope='module')
def source():
    return open(LOC.__file__, encoding='utf-8').read()


def _mutant(source, rule, tmp_path):
    old, new = MUTANTS[rule]
    assert source.count(old) == 1, f'{rule}: anchor appears {source.count(old)}x'
    path = tmp_path / 'locator_mutant.py'
    path.write_text(source.replace(old, new), encoding='utf-8')
    spec = importlib.util.spec_from_file_location('loc_mutant', str(path))
    mod = importlib.util.module_from_spec(spec)
    saved = list(sys.path)
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = saved
    return mod


def test_removing_the_EXPANDED_MEANING_lets_a_rebound_prefix_attach(source,
                                                                    tmp_path):
    """Named, both ways: the fabricated currency comes back AND the lawful
    alias still binds, so this cannot be mistaken for a mutation that simply
    broke unit handling."""
    m = _mutant(source, 'expanded meaning', tmp_path)
    evil = _rebind(RA.doc(body_rows=RA.ROW_390), 'iso4217', 'urn:evil')
    assert len(m.locate(RA.ANCHOR,
                        RA.src([RA.fact(meaning=_graph('iso4217:USD'))],
                               evil))['items']) == 1, \
        'the rebound prefix must attach once meaning is gone'
    ok = _rebind(RA.doc(body_rows=RA.ROW_390), 'cur', ISO)
    assert len(m.locate(RA.ANCHOR,
                        RA.src([RA.fact(meaning=_graph('cur:USD'))],
                               ok))['items']) == 1


def test_removing_the_STORED_SPELLING_lets_an_unrelated_row_attach(source,
                                                                   tmp_path):
    m = _mutant(source, 'stored spelling', tmp_path)
    assert len(m.locate(RA.ANCHOR,
                        RA.src([RA.fact(meaning=_graph('unknownunit'))],
                               RA.doc(body_rows=RA.ROW_390)))['items']) == 1, \
        'the mismatched label must attach once integrity is gone'
    # ...and the rebound prefix is STILL refused, proving the two laws are
    # separate and neither is being credited for the other's work.
    evil = _rebind(RA.doc(body_rows=RA.ROW_390), 'iso4217', 'urn:evil')
    assert m.locate(RA.ANCHOR,
                    RA.src([RA.fact(meaning=_graph('iso4217:USD'))],
                           evil))['items'] == []
