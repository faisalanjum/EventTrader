"""#827 Stage 3 — the component census reaches reconciliation on the REAL path.

WHY THIS FILE EXISTS. `route_a_component_census.work()` passed `ev['fmt']` — the
filing's own raw QName — into `IH.reconcile`, which now requires the format's
EXPANDED identity. The census is an active seed tool and is imported by the
Phase-4 dry run, so a stale caller here misclassifies silently or crashes.

The reviewer found it by reading the line; I had "proved" the class clean with a
text search that a variable carrying the same raw text walks straight past. So
this test does not inspect code at all — it RUNS `work()` and checks the
outcome, which is the only thing a raw format could not survive.

NO GRAPH IS TOUCHED. `_drv` is a module global, so the fact rows the census
would read from Neo4j are supplied directly; every other step — the real
`prepare`, the real `element_evidence`, the real period law, the real
`reconcile` — is the production code path unchanged.

TWO FACTS, because one would not separate the cases:
  * a NO-FORMAT fact, whose value states itself as an XSD decimal;
  * an OFFICIALLY TRANSFORMED fact (TR4 `num-dot-decimal`), whose printed text
    only becomes a number once the registry is applied.
A raw format breaks the second and leaves the first looking fine.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, '..'))
sys.path.insert(0, os.path.join(_HERE, '..', '..', '..',
                                'driver', 'relocation'))

import route_a_component_census as RC              # noqa: E402

#: TR4, the registry EDGAR release 26.1 admits and the pinned library
#: implements. https://www.sec.gov/files/ixbrl-transform-registries.json
TR4 = 'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12'

_DOC = f"""<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
 xmlns:xbrli="http://www.xbrl.org/2003/instance"
 xmlns:iso4217="http://www.xbrl.org/2003/iso4217"
 xmlns:us-gaap="http://example.org/us-gaap"
 xmlns:ixt="{TR4}"><body>
<div style="display:none"><ix:header><ix:resources>
 <xbrli:context id="c-1"><xbrli:entity><xbrli:identifier
   scheme="http://www.sec.gov/CIK">0000001234</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:startDate>2024-04-01</xbrli:startDate>
   <xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>
 <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
</ix:resources></ix:header></div>
<table>
 <tr><td>Plain revenue</td><td><ix:nonFraction id="f-plain"
   name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" scale="0"
   decimals="0">726</ix:nonFraction></td></tr>
 <tr><td>Grouped revenue</td><td><ix:nonFraction id="f-fmt"
   name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" scale="0"
   decimals="0" format="ixt:num-dot-decimal">1,234</ix:nonFraction></td></tr>
</table></body></html>"""


def _row(fid, value):
    """One graph fact row in the shape `work()`'s own query returns."""
    return {'fid': fid, 'qn': 'us-gaap:Revenues', 'cid': 'c-1', 'v': value,
            'ur': 'usd', 'un': 'iso4217:USD', 'dv': '0',
            'pt': 'duration', 'ps': '2024-04-01', 'pe': '2024-07-01'}


# Frozen graph lexical contract SEQ 265 C / 266 §2; writer formatters own it.
ROWS = [_row('f-plain', '726'), _row('f-fmt', '1,234')]


class _Session:
    """The two rows the census would have read from Neo4j."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, *_a, **_k):
        return list(ROWS)


class _Driver:
    def session(self):
        return _Session()


@pytest.fixture
def census(tmp_path, monkeypatch):
    """`work()` on a real file, with the graph read supplied. Returns its
    counter."""
    monkeypatch.setattr(RC, '_drv', _Driver())
    path = tmp_path / '0000001234-24-000001.htm'
    path.write_text(_DOC, encoding='utf-8')
    _acc, tally, _err = RC.work(str(path))
    return tally


def test_BOTH_facts_reach_reconciliation_and_RECONCILE(census):
    """THE POSITIVE CONTROL, and the one a raw format cannot pass.

    `1,234` is only a number once TR4's `num-dot-decimal` is applied; handed a
    prefix instead of the registry identity, the transformed fact cannot
    reconcile. Both facts must arrive at reconciliation AND succeed."""
    assert census.get('facts') == 2, dict(census)
    assert census.get('period_ok') == 2, dict(census)
    assert census.get('reconcile_ok') == 2, dict(census)
    assert census.get('reconcile_fail', 0) == 0, dict(census)


def test_a_RAW_format_would_BREAK_this_census(tmp_path, monkeypatch):
    """THE MUTATION, in a fresh temp copy: change ONLY `fmt_expanded` back to
    `fmt` — the exact defect the reviewer found — and require this census to
    stop reconciling the transformed fact.

    Nothing else is altered, so a failure here can only be that one argument.
    """
    import importlib.util

    source = open(RC.__file__, encoding='utf-8').read()
    old = "IH.reconcile(ev['value_input'], ev['fmt_expanded'], ev['scale'],"
    new = "IH.reconcile(ev['value_input'], ev['fmt'], ev['scale'],"
    assert source.count(old) == 1, 'the call site moved; re-anchor this mutation'

    path = tmp_path / 'mutant_census.py'
    path.write_text(source.replace(old, new), encoding='utf-8')
    spec = importlib.util.spec_from_file_location('rc_mutant', str(path))
    mutant = importlib.util.module_from_spec(spec)
    saved = list(sys.path)
    try:
        spec.loader.exec_module(mutant)
    finally:
        sys.path[:] = saved

    monkeypatch.setattr(mutant, '_drv', _Driver())
    doc = tmp_path / '0000001234-24-000002.htm'
    doc.write_text(_DOC, encoding='utf-8')

    # THE RAW FORMAT DOES NOT MERELY MISCOUNT — it raises, because a prefixed
    # string cannot be unpacked into (namespace URI, local name). That is the
    # loud half of the defect; the quiet half is that until this round the
    # signature ACCEPTED it and the census reported numbers built on a
    # comparison that never resolved a registry.
    with pytest.raises(ValueError, match='unpack'):
        mutant.work(str(doc))


#: A number that appears NOWHERE else in the fixture, padded. `_text` collapses
#: whitespace and strips the ends, so the rendered form (`9,876`) and the value
#: as filed (`  9,876  `) are different strings AND neither collides with any
#: other fact — which is what lets a negative assertion mean something.
_PADDED = ('<ix:nonFraction id="f-pad" name="us-gaap:Revenues"'
           ' contextRef="c-1" unitRef="usd" scale="0" decimals="0"'
           ' format="ixt:num-dot-decimal">  9,876  </ix:nonFraction>')
_PADDED_AS_FILED, _PADDED_RENDERED = '  9,876  ', '9,876'


def _census_over_padded_doc(tmp_path, monkeypatch, module, name):
    """Run `module.work()` over a document containing the padded fact and
    return every first argument `reconcile` received."""
    import inline_html as IH
    seen, real = [], IH.reconcile
    monkeypatch.setattr(
        IH, 'reconcile', lambda *a, **k: (seen.append(a[0]), real(*a, **k))[1])
    doc = _DOC.replace('<table>',
                       f'<table><tr><td>Padded</td><td>{_PADDED}</td></tr>', 1)
    path = tmp_path / name
    path.write_text(doc, encoding='utf-8')
    monkeypatch.setattr(module, '_drv', _Driver())
    monkeypatch.setitem(globals(), 'ROWS', ROWS + [_row('f-pad', '9,876')])
    module.work(str(path))
    return seen


def test_a_MALFORMED_DOCUMENT_is_refused_truthfully___not_a_KeyError(
        tmp_path, monkeypatch):
    """RED through `work()` itself.

    `prepare()` does not RAISE on a bad document — it returns a refusal value —
    so the `except IH.SemanticParseError` written here first was dead code and
    the census crashed further down with a bare `KeyError('ids')`. The refusal
    is now read through `IH.refused()`, the accessor every public door uses.
    """
    import inline_html as IH
    path = tmp_path / '0000001234-24-000007.htm'
    path.write_text('<html><body><unclosed></body></html>', encoding='utf-8')
    monkeypatch.setattr(RC, '_drv', _Driver())
    _acc, tally, err = RC.work(str(path))
    assert dict(tally) == {'file_error': 1}, dict(tally)
    # The SHARED owner, not a copy of the sentence: a reworded refusal must
    # move this test with it rather than leave a stale string passing.
    assert err == IH.NOT_WELL_FORMED, err


def test_a_WELL_FORMED_document_is_still_read___the_must_allow_twin(
        tmp_path, monkeypatch):
    path = tmp_path / '0000001234-24-000008.htm'
    path.write_text(_DOC, encoding='utf-8')
    monkeypatch.setattr(RC, '_drv', _Driver())
    _acc, tally, err = RC.work(str(path))
    # EXACTLY '' — the public contract for "nothing went wrong". `not err`
    # would also swallow `None`, and any future non-empty reason would have to
    # be looked at rather than passed over.
    assert err == '', err
    assert tally.get('facts') == 2, dict(tally)


def test_a_PROGRAMMING_ERROR_propagates___it_is_not_a_filing_error(
        tmp_path, monkeypatch):
    """The half the old `except Exception` destroyed. A bug of ours inside
    `prepare()` must reach the operator, not be filed as a defect in someone's
    10-K."""
    import inline_html as IH

    def boom(_text):
        raise TypeError('a bug of ours, not the filing')

    monkeypatch.setattr(IH, 'prepare', boom)
    path = tmp_path / '0000001234-24-000009.htm'
    path.write_text(_DOC, encoding='utf-8')
    monkeypatch.setattr(RC, '_drv', _Driver())
    with pytest.raises(TypeError, match='a bug of ours'):
        RC.work(str(path))


def test_UNDECODABLE_BYTES_are_refused___not_silently_rewritten(
        tmp_path, monkeypatch):
    """`errors='replace'` turned bytes this census could not read into U+FFFD
    and carried on, so a file it never really read was counted as one it had.
    The decode is strict now and the failure is named."""
    path = tmp_path / '0000001234-24-000005.htm'
    path.write_bytes(_DOC.encode('utf-8').replace(b'Plain revenue',
                                                  b'Plain \xff\xfe revenue'))
    monkeypatch.setattr(RC, '_drv', _Driver())
    _acc, tally, err = RC.work(str(path))
    assert dict(tally) == {'file_unreadable': 1}, dict(tally)
    assert 'UnicodeDecodeError' in err, err


def test_a_DECODABLE_file_is_still_read___the_must_allow_twin(
        tmp_path, monkeypatch):
    """Strictness that refused everything would satisfy the case above and
    destroy the census. Non-ASCII that IS valid UTF-8 must sail through."""
    path = tmp_path / '0000001234-24-000006.htm'
    path.write_text(_DOC.replace('Plain revenue', 'Plain revenue — café'),
                    encoding='utf-8')
    monkeypatch.setattr(RC, '_drv', _Driver())
    _acc, tally, err = RC.work(str(path))
    # EXACTLY '', for the same reason. The previous form —
    # `err is None or 'Unicode' not in err` — would have passed on an
    # unrelated KeyError, which is not what this twin claims to prove.
    assert err == '', err
    assert tally.get('facts') == 2, dict(tally)


def test_the_FIXTURE_itself_distinguishes_the_two_fields(tmp_path):
    """ASSERTED FROM THE RETURNED EVIDENCE, because the previous fixture could
    not tell the arguments apart at all.

    That version used a nested `ix:nonFraction` chain on the belief that the
    rendered text and the fact value diverge there. Measured, they are
    IDENTICAL for a clean chain — `'1,234'` both ways — so its assertion was
    satisfied by the defective caller too. A fixture's discriminating power is
    now a checked precondition rather than an assumption.
    """
    import inline_html as IH
    doc = _DOC.replace('<table>',
                       f'<table><tr><td>Padded</td><td>{_PADDED}</td></tr>', 1)
    ev, why = IH.element_evidence(IH.prepare(doc), 'f-pad')
    assert ev is not None, why
    assert ev['value_input'] == _PADDED_AS_FILED
    assert ev['displayed'] == _PADDED_RENDERED
    assert ev['value_input'] != ev['displayed']


def test_RESTORING_the_displayed_caller_turns_this_RED(tmp_path, monkeypatch):
    """THE RED HALF, run first. A temp copy with the one argument put back to
    `ev['displayed']` must send the RENDERED text and never the filed value —
    otherwise the green below is measuring nothing."""
    import importlib.util

    source = open(RC.__file__, encoding='utf-8').read()
    intended = "IH.reconcile(ev['value_input'], ev['fmt_expanded'], ev['scale'],"
    defect = "IH.reconcile(ev['displayed'], ev['fmt_expanded'], ev['scale'],"
    assert source.count(intended) == 1, 'the call site moved; re-anchor this'

    path = tmp_path / 'displayed_caller.py'
    path.write_text(source.replace(intended, defect), encoding='utf-8')
    spec = importlib.util.spec_from_file_location('rc_displayed', str(path))
    mutant = importlib.util.module_from_spec(spec)
    saved = list(sys.path)
    try:
        spec.loader.exec_module(mutant)
    finally:
        sys.path[:] = saved

    seen = _census_over_padded_doc(tmp_path, monkeypatch, mutant,
                                   '0000001234-24-000004.htm')
    assert _PADDED_RENDERED in seen, seen
    assert _PADDED_AS_FILED not in seen, seen


def test_the_argument_reaching_RECONCILE_is_the_FACT_VALUE_not_the_page(
        tmp_path, monkeypatch):
    """THE ARGUMENT ITSELF, observed — not read out of the source.

    `displayed` is the element's RENDERED text: `_text` collapses runs of
    whitespace, strips the ends and deletes zero-width spaces. The fact's value
    under Inline XBRL 1.1 §10.1.1 is the element's content AS WRITTEN. This
    census was the last caller handing over the page instead of the fact; both
    live sites (`locator.py:1146`, `inline_html.py:2388`) pass `value_input`.

    THE FIXTURE IS PADDED ON PURPOSE. My first attempt used a nested
    `nonFraction` chain and measured nothing: for a clean chain the two strings
    are IDENTICAL (`'1,234'` both ways), so the assertion would have passed
    whichever argument the census sent. Padding is the smallest shape where
    they genuinely differ — `'1,234'` rendered versus `'  1,234  '` as filed —
    so what reaches `reconcile` becomes observable.
    """
    seen = _census_over_padded_doc(tmp_path, monkeypatch, RC,
                                   '0000001234-24-000003.htm')
    assert seen, 'reconcile was never reached'
    # BOTH DIRECTIONS, and the negative is only meaningful because `9,876`
    # appears nowhere else in the fixture. An earlier draft padded `1,234` —
    # the other fact's value — so its negative assertion failed on CORRECT
    # behaviour. A negative has to name a value only the defect could produce.
    assert _PADDED_AS_FILED in seen, (
        'the RENDERED text reached reconcile instead of the fact value; '
        f'observed {seen}')
    assert _PADDED_RENDERED not in seen, (
        f'the rendered text also reached reconcile: {seen}')
