"""PHASE 1 ROUTE A — corrective tests (RED-first; real graph shapes + attacks).

Real-shape law: graph values carry commas/paren-negatives; periods use the EXCLUSIVE
(+1 day) end convention and are normalized ONCE (exact compare, never both); each fact
carries its semantic Unit meaning (unit_name/is_divide) — fail-closed when absent;
emitted value = the SIGNED, UNSCALED source-printed value contained in its own verbatim
quote; the XBRL block keeps the HTML context's exact dates; identity comes ONLY from
the element's row/header-stack/section/block (no distant text, no hidden content);
typed dimensions abstain; one printed element claimed by different facts = ambiguous.

    venv/bin/python -m pytest driver/relocation/test_route_a.py -q
"""
import json
import os
import pytest
import re
import sys
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import inline_html as IH
import locator as LOC

GQ2 = {'startDate': '2024-04-01', 'endDate': '2024-07-01'}     # graph-exclusive end
UNIT = {'unit_name': 'iso4217:USD', 'is_divide': '0'}   # REAL string boolean

ANCHOR = {
    "source_id": "SYN-PRIOR", "company": "C1", "driver": "revenue", "slice": "",
    "measurement": "", "series_unit": "m_usd", "time_type": "duration",
    "fact_type": "metric", "wording": ("Widget revenue",), "concept_clue": None,
}


def doc(body_rows="", extra="", ctx_extra="", hidden_facts=""):
    return f"""<html xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12" xmlns:utr="http://example.org/utr" xmlns:us-gaap="http://example.org/us-gaap" xmlns:dei="http://example.org/dei" xmlns:srt="http://example.org/srt" xmlns:a="http://example.org/a" xmlns:x="http://example.org/x" xmlns:aapl="http://example.org/aapl" xmlns:slg="http://example.org/slg" xmlns:accd="http://example.org/accd" xmlns:ed="http://example.org/ed" xmlns:dvn="http://example.org/dvn" xmlns:fcx="http://example.org/fcx" xmlns:nog="http://example.org/nog" xmlns:inst="http://example.org/inst" xmlns:dimns="http://example.org/dimns" xmlns:nope="http://example.org/nope" xmlns:geo="http://example.org/geo" xmlns:eqt="http://example.org/eqt" xmlns:geography="http://example.org/geography" xmlns:seg="http://example.org/seg" xmlns:country="http://example.org/country"><body>
<div style="display:none">
 <ix:header>
 <ix:hidden>{hidden_facts}</ix:hidden>
 <ix:resources>
  <xbrli:context id="c-1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000001234</xbrli:identifier></xbrli:entity><xbrli:period>
    <xbrli:startDate>2024-04-01</xbrli:startDate>
    <xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>
  {ctx_extra}
  <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
 </ix:resources></ix:header>
</div>
<p>Distant unrelated paragraph naming Alpha widget special revenue in prose.</p>
<table>
 <tr><td></td><th>Q2 2024</th></tr>
 {body_rows}
</table>
{extra}
</body></html>"""


ROW_390 = ('<tr><td>Widget revenue</td><td><ix:nonFraction id="f-1" '
           'name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" scale="6" decimals="-6" '
           'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')


#: the taxonomy these fixtures' documents declare, and the identity their fact
#: records carry — the locator authorises on (namespace URI, local name), so a
#: record without it has no target and is abstained on.
_NS_GAAP = 'http://example.org/us-gaap'
_IDENTITY = {'concept_namespace': _NS_GAAP,
             'graph_concept_qname': 'us-gaap:Revenues'}


def fact(value='390,000,000', fid='f-1', unit='usd', period=GQ2,
         meaning=UNIT):
    """A graph-shaped fact row. NO `segment` OPTION: the locator's raw-segment
    branch was deleted in #827 because no real producer supplies one, and
    keeping the knob here would preserve a test-only surface for a production
    path that no longer exists — the next reader would write a fixture the
    product can never receive. Dimensions reach the locator the way the real
    producer sends them: through `context_id`."""
    fc = {'value': value, 'period': period, 'unitRef': unit, 'fact_id': fid,
          **_IDENTITY}
    if meaning is not None:
        fc.update(meaning)
    return fc


def src(facts, html, texts=()):
    return {'source_id': 'S1', 'source_type': '10k',
            'xbrls': [json.dumps({'us-gaap:Revenues': facts})],
            'texts': list(texts), 'inline_html': html,
            'company_cik': '0000001234'}


# ---------- evidence layer ----------

def test_evidence_join_and_payload():
    ev, reason = IH.element_evidence(doc(ROW_390), 'f-1')
    assert reason == 'ok' and ev['name'] == 'us-gaap:Revenues'
    assert ev['displayed'] == '390' and ev['scale'] == 6 and ev['sign'] == ''
    assert ev['period'] == ('2024-04-01', '2024-06-30')
    assert ev['row_label'] == 'Widget revenue'
    assert any('Q2 2024' in c for c in ev['columns'])
    assert 'anchor' not in ev, "the distant-text walk is deleted"


def test_evidence_failures_enumerated():
    assert IH.element_evidence(doc(ROW_390), 'f-404')[1] == 'id_not_found'
    assert IH.element_evidence(doc(ROW_390 + ROW_390), 'f-1')[1] == 'duplicate_id'
    bad = ROW_390.replace('"c-1"', '"c-410"').replace('"f-1"', '"f-9"')
    assert IH.element_evidence(doc(ROW_390 + bad), 'f-9')[1] == 'undefined_context'


def test_evidence_typed_dimensions_abstain():
    # THE FIXTURE CARRIES ITS ENTITY (#827 round 5). Without it this context is
    # itself invalid under XBRL 2.1 §4.7, and a structure rule that refuses it
    # was read as over-strict — so production was weakened to keep a malformed
    # fixture green. The assertion below is unchanged by the repair: the real
    # typed-dimension case is proven on a REAL filing in the next test.
    ctx = ('<xbrli:context id="c-t"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
           '</xbrli:identifier></xbrli:entity><xbrli:period>'
           '<xbrli:startDate>2024-04-01</xbrli:startDate>'
           '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
           '<xbrli:scenario><xbrldi:typedMember dimension="x:Ax">'
           '<x:d>1</x:d></xbrldi:typedMember></xbrli:scenario></xbrli:context>')
    row = ROW_390.replace('"c-1"', '"c-t"').replace('"f-1"', '"f-t"')
    ev, reason = IH.element_evidence(doc(ROW_390 + row, ctx_extra=ctx), 'f-t')
    assert ev is None and reason == 'typed_dimensions_unsupported'


def test_evidence_real_typed_case_f427():
    p = os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed', 'relocate_probe',
                     'inline_html_cache', '0000917520-24-000094.htm')
    html = open(os.path.abspath(p), encoding='utf-8', errors='replace').read()
    ev, reason = IH.element_evidence(html, 'f-427')
    assert ev is None and reason == 'typed_dimensions_unsupported'


#: The format's IDENTITY, not its spelling. These called `reconcile` with the
#: raw text `ixt:num-dot-decimal`, which is a prefix the filing chooses — the
#: very thing #827 Stage 3 removed from every semantic decision. There is no
#: raw-string compatibility path, deliberately: keeping one would preserve the
#: defect behind a second door.
_TR4 = 'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12'
_NDD = (_TR4, 'num-dot-decimal')
_RAW = 'ixt:num-dot-decimal'            # a lawful spelling of the above


def test_reconcile_and_printed_value():
    assert IH.reconcile('390', _NDD, 6, '', '390,000,000') is True
    assert IH.reconcile('117,679', _NDD, 3, '', '117,679,000') is True
    # IDENTITY CHANGE (SEQ 265 D): the raw side '(98)' left the graph
    # grammar with the paren branch; the sign law reconciles against the
    # writer's plain negative, and the visible-paren SOURCE story is pinned
    # by test_F_a_visible_accounting_negative_still_reconciles.
    assert IH.reconcile('98', _NDD, 0, '-', '-98') is True
    assert IH.reconcile('390', _NDD, 6, '', '391000000') is False
    # A LOCAL NAME THE APPROVED REGISTRY DOES NOT DEFINE — refused because the
    # registry has no such signature, not because a prefix looked unfamiliar.
    assert IH.reconcile('5', (_TR4, 'unknown'), 0, '', '5') is False
    assert IH.printed_value('390', _NDD, '') == Decimal('390')
    assert IH.printed_value('117,679', _NDD, '-') == Decimal('-117679')


def test_prepare_once_api():
    d = IH.prepare(doc(ROW_390))
    ev, reason = IH.element_evidence(d, 'f-1')
    assert reason == 'ok' and ev['displayed'] == '390'
    assert IH.sha256_text(doc(ROW_390)) == d['sha']


# ---------- locate() Route A ----------

def test_binds_real_shape_comma_value_exclusive_period():
    r = LOC.locate(ANCHOR, src([fact()], doc(ROW_390)))
    assert r['status'] is None and len(r['items']) == 1, r
    it = r['items'][0]
    assert it['value'] == Decimal('390'), "emit the SIGNED UNSCALED printed value"
    assert '390' in it['quote'] and 'Widget revenue' in it['quote']
    assert it['xbrl']['period_start'] == '2024-04-01'
    assert it['xbrl']['period_end'] == '2024-06-30', "HTML context dates in the block"
    ix = it['ix_evidence']
    assert (ix['scale'], ix['sign'], ix['format'], ix['unit_ref']) == \
        (6, '', 'ixt:num-dot-decimal', 'usd')
    prep = IH.prepare(doc(ROW_390))
    assert it['xbrl']['source_evidence']['representation_sha256'] == prep['text_sha']
    a, b = it['xbrl']['source_evidence']['quote_span']
    assert prep['text'][a:b] == it['quote'], \
        "quote = an exact OFFSET slice of the hash-pinned representation"
    la, lb = it['xbrl']['source_evidence']['raw_label_span']
    assert prep['text'][la:lb] == it['raw_label']
    assert 'unit_meaning' not in it and 'source_sha256' not in it


def test_exact_period_law_no_dual_convention():
    inclusive = {'startDate': '2024-04-01', 'endDate': '2024-06-30'}
    r = LOC.locate(ANCHOR, src([fact(period=inclusive)], doc(ROW_390)))
    assert r['items'] == [], "graph end must be doc end +1 EXACTLY (no dual accept)"
    off = {'startDate': '2024-04-01', 'endDate': '2024-07-02'}
    assert LOC.locate(ANCHOR, src([fact(period=off)], doc(ROW_390)))['items'] == []


_DATE_START = '<xbrli:startDate>2024-04-01</xbrli:startDate>'


def test_827_the_LOCATOR_ITSELF_binds_a_lawful_midnight_dateTime_start():
    """THE MISSING PROOF, driven through `locate()` — not through the helper.

    The locator compared the filing's START as a RAW STRING, so a lawful
    `2024-04-01T00:00:00` could never equal the graph's `2024-04-01` and the
    match was silently lost, while the inline-XBRL binder accepted the very
    same value. Two answers to one question.

    The helper was corrected last round and pinned by helper-level tests, but
    NOTHING drove the corrected behaviour through the locator's own path — so
    the repair was unpinned where it actually runs. `xs:date` and the midnight
    `xs:dateTime` are the same instant and must locate identically.
    """
    html = doc(ROW_390).replace(
        _DATE_START, '<xbrli:startDate>2024-04-01T00:00:00</xbrli:startDate>')
    assert html != doc(ROW_390), "the dateTime start was not substituted"
    r = LOC.locate(ANCHOR, src([fact()], html))
    assert len(r['items']) == 1, \
        f"a lawful midnight dateTime start must locate exactly as the date does: {r}"
    assert r['items'][0]['value'] == Decimal('390')


def test_827_a_BACKWARDS_duration_never_binds_through_the_public_door():
    """WHAT THIS PROVES, exactly: no backwards period binds. It does NOT prove
    the locator's own forward-order rule fired, and an earlier version of this
    test claimed it did.

    Measured instead: across the whole Route-A suite the locator calls
    `filing_duration_ordered` 23 times and it rejects NOTHING, and removing the
    call entirely (mutation 19) changes no result. The graph-side period is
    validated first — `period_key` refuses `2024-09-01..2024-07-01` outright —
    so a backwards filing can never reach a matching graph shape. That rule in
    the locator is therefore measured-redundant defence-in-depth; it is left in
    place deliberately (it is the same law the binder applies) and reported as
    a simplification candidate rather than deleted here.
    """
    html = doc(ROW_390).replace(
        _DATE_START, '<xbrli:startDate>2024-09-01</xbrli:startDate>')
    backwards = {'startDate': '2024-09-01', 'endDate': '2024-07-01'}
    r = LOC.locate(ANCHOR, src([fact(period=backwards)], html))
    assert r['items'] == [], \
        f"a period running backwards must never bind: {r}"


def test_unit_tuple_map_fail_closed():
    r = LOC.locate(ANCHOR, src([fact(meaning=None)], doc(ROW_390)))
    assert r['items'] == [], "missing semantic unit meaning -> abstain"
    div = {'unit_name': 'iso4217:USD', 'is_divide': '1'}
    assert LOC.locate(ANCHOR, src([fact(meaning=div)], doc(ROW_390)))['items'] == []
    # RESTORED. In #827 Stage 3 I briefly asserted this SHOULD bind, reasoning
    # that `Unit.name` carries no namespace and so cannot state identity. That
    # much is true, and it is why MEANING now comes from the filing's expanded
    # measures. But identity is not the only job this field has: the graph
    # writer stores `unit.stringValue`, and the filing parser derives the same
    # serialization by namespace, so the two spellings can be compared EXACTLY
    # to ask a different question — is the graph describing this unit at all?
    # `unknownunit` is not a spelling of `iso4217:USD`, so the row and the
    # filing are not talking about the same thing and neither can be trusted.
    odd = {'unit_name': 'unknownunit', 'is_divide': '0'}
    assert LOC.locate(ANCHOR, src([fact(meaning=odd)], doc(ROW_390)))['items'] == [], \
        "graph label that is not the filing's own stored spelling -> abstain"
    junk = {'unit_name': 'iso4217:USD', 'is_divide': 'yes'}
    assert LOC.locate(ANCHOR, src([fact(meaning=junk)], doc(ROW_390)))['items'] == [], \
        "non-'0'/'1' boolean strings abstain (strict normalization)"


def test_padded_or_nonstring_ids_rejected_no_fallback():
    assert LOC.locate(ANCHOR, src([fact(fid=' f-1 ')], doc(ROW_390)))['items'] == []
    assert LOC.locate(ANCHOR, src([fact(fid=7)], doc(ROW_390)))['items'] == []


def test_numeric_headers_and_digit_labels_retained():
    rows = ('<tr><td></td><th>2024</th></tr>'
            '<tr><td>Product 50 widget revenue</td><td><ix:nonFraction id="f-1" '
            'name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" scale="6" decimals="-6" '
            'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')
    d = doc('') .replace('<tr><td></td><th>Q2 2024</th></tr>\n ', rows)
    ev, reason = IH.element_evidence(d, 'f-1')
    assert reason == 'ok'
    assert '2024' in ev['columns'], "numeric-only headers are part of the stack"
    assert ev['row_label'] == 'Product 50 widget revenue'


def test_leading_dot_forms():
    assert IH.printed_value('.300', _NDD, '') == Decimal('0.300')
    assert IH.reconcile('.300', _NDD, -2, '', '0.003') is True


def test_two_anchor_single_parse():
    calls = []
    orig = IH._soup
    IH._soup = lambda t: (calls.append(1), orig(t))[1]
    try:
        IH._PREP_CACHE.clear()
        d = doc(ROW_390)
        LOC.locate(ANCHOR, src([fact()], d))
        LOC.locate(dict(ANCHOR, wording=('Widget revenue',), driver='rev2'),
                   src([fact()], d))
    finally:
        IH._soup = orig
    assert len(calls) == 1, f"two anchors reparsed the filing ({len(calls)} parses)"


def test_identity_never_from_distant_text():
    far = dict(ANCHOR, wording=('Alpha widget special revenue',))
    r = LOC.locate(far, src([fact()], doc(ROW_390)))
    assert r['items'] == [], "a distant paragraph must not prove identity"


def test_identity_never_from_css_hidden_cells():
    row = ('<tr><td style="display:none">Widget revenue</td><td>Other label</td>'
           '<td><ix:nonFraction id="f-1" name="us-gaap:Revenues" contextRef="c-1" '
           'unitRef="usd" scale="6" decimals="-6" format="ixt:num-dot-decimal">390'
           '</ix:nonFraction></td></tr>')
    r = LOC.locate(ANCHOR, src([fact()], doc(row)))
    assert r['items'] == [], "CSS-hidden text must not prove identity"


def test_hidden_fact_element_abstains():
    hid = ('<ix:nonFraction id="f-h" name="us-gaap:Revenues" contextRef="c-1" '
           'unitRef="usd" scale="6" decimals="-6">390</ix:nonFraction>')
    r = LOC.locate(ANCHOR, src([fact(fid='f-h')], doc('', hidden_facts=hid)))
    assert r['items'] == []


def test_formatting_equivalent_duplicates_dedupe_to_one():
    two = [fact(value='390,000,000'), fact(value='390000000')]
    r = LOC.locate(ANCHOR, src(two, doc(ROW_390)))
    assert len(r['items']) == 1 and r['status'] is None, \
        "identical XBRL identities (formatting-equivalent) DEDUPLICATE"


def test_blank_id_unique_identity_fallback():
    r = LOC.locate(ANCHOR, src([fact(fid='')], doc(ROW_390)))
    assert len(r['items']) == 1 and r['items'][0]['value'] == Decimal('390')


def test_one_parse_per_filing():
    calls = []
    orig = IH._soup
    IH._soup = lambda t: (calls.append(1), orig(t))[1]
    try:
        rows = ROW_390 + ROW_390.replace('"f-1"', '"f-2"').replace(
            'Widget revenue', 'Widget other revenue')
        facts = [fact(), fact(fid='f-2', value='390,000,000')]
        LOC.locate(ANCHOR, src(facts, doc(rows)))
    finally:
        IH._soup = orig
    assert len(calls) == 1, f"filing parsed {len(calls)} times; must be once"


def test_no_inline_html_returns_no_proven_match():
    # MIGRATED at Phase 3 (was test_no_inline_html_legacy_path_unchanged, which
    # pinned the deleted flat-text R1 walk): without a display inline document
    # the locator now honestly abstains — prose belongs to the certified reader.
    s = {'source_id': 'S1', 'source_type': '10k',
         'xbrls': [json.dumps({'us-gaap:Revenues': [
             {'value': '4,000,000,000', 'unitRef': 'U_USD', 'period':
              {'startDate': '2024-01-01', 'endDate': '2024-12-31'}}]})],
         'texts': ["Widget revenue was 4,000,000,000 for the year"]}
    out = LOC.locate(ANCHOR, s)
    assert out['items'] == [] and out['status'] == 'no_proven_match', out


def test_real_ce_filing_end_to_end():
    p = os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed', 'relocate_probe',
                     'inline_html_cache', '0001306830-24-000155.htm')
    html = open(os.path.abspath(p), encoding='utf-8', errors='replace').read()
    # THE PRODUCER'S OWN SHAPE. This used to inject a hand-written `segment`
    # list of raw prefixed qnames and omit the context id. The real producer
    # (`driver/channels/fiscal_ai/route_a_source.py`) returns the exact `context_id`
    # and never a segment — a bare `srt:`/`ce:` prefix is this filing's private
    # alias and states no identity, so nothing may authorise a match on it.
    #
    # `c-373` is the graph's own `Fact.context_id` for `f-1357`, read under an
    # unchanged read-only transaction, and it is the SAME string the filing
    # element carries as its contextRef — so the join below is an identity, not
    # a resemblance. Joining on it makes the filing's own dimensions
    # authoritative with no prefix read at all.
    ctx = 'c-373'
    # THE REAL FILING'S OWN graph identity, pinned from a read-only Neo4j read
    # on 2026-08-01 under an unchanged transaction: accession 0001306830-24-000155
    # carries this concept under the FASB 2023 taxonomy. Not the synthetic
    # `_IDENTITY` the fixture documents use, and not derived from this filing.
    fc = {'value': '390,000,000', 'unitRef': 'usd', 'fact_id': 'f-1357',
          'context_id': ctx,
          'unit_name': 'iso4217:USD', 'is_divide': '0',
          'period': {'startDate': '2024-04-01', 'endDate': '2024-07-01'},
          'concept_namespace': 'http://fasb.org/us-gaap/2023',
          'graph_concept_qname':
              'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax'}
    anchor = dict(ANCHOR, wording=('North America',),
                  slice='segment:acetyl_chain')
    s = {'source_id': 'CE-10Q', 'source_type': '10q', 'company_cik': '0001306830',
         'xbrls': [json.dumps(
             {'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax': [fc]})],
         'texts': [], 'inline_html': html}
    r = LOC.locate(anchor, s)
    assert r['status'] is None and len(r['items']) == 1, r['status']
    it = r['items'][0]
    assert it['value'] == Decimal('390') and 'North America' in it['quote']
    assert it['xbrl']['period_end'] == '2024-06-30'
    assert it['ix_evidence']['scale'] == 6
    texts = [piece['text'] for piece in it['xbrl']['source_evidence']['pieces']]
    assert any('Acetyl Chain' in t for t in texts), \
        "the EXPECTED section piece must be present"
    assert any('In $ millions' in t for t in texts), \
        "the EXPECTED header piece must be present"
    for piece in it['xbrl']['source_evidence']['pieces']:
        a, b = piece['span']
        assert IH.prepare(html)['text'][a:b] == piece['text']


def _cached(name):
    p = os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed', 'relocate_probe',
                     'inline_html_cache', name)
    return open(os.path.abspath(p), encoding='utf-8', errors='replace').read()


def test_real_shares_and_per_share_pins():
    html = _cached('0000027904-23-000006.htm')
    ev, reason = IH.element_evidence(html, 'f-246')     # DAL shares outstanding
    assert reason == 'ok' and ev['unit_ref']
    assert IH.reconcile(ev['value_input'], ev['fmt_expanded'], ev['scale'],
                        ev['sign'], '654,000,000') is True, \
        "real shares fact reconciles"
    ev2, reason2 = IH.element_evidence(html, 'f-685')   # DAL loss per share
    assert reason2 == 'ok'
    assert IH.reconcile(ev2['value_input'], ev2['fmt_expanded'], ev2['scale'],
                        ev2['sign'], '-0.57') is True, \
        "real USD-per-share reconciles"


def test_bools_reject_python_types():
    for bad in (False, True, 0, 1):
        m = {'unit_name': 'iso4217:USD', 'is_divide': bad}
        assert LOC.locate(ANCHOR, src([fact(meaning=m)], doc(ROW_390)))['items'] \
            == [], f"is_divide={bad!r} must abstain (only '0'/'1' strings bind)"


def test_idless_element_fallback_binds():
    row = ('<tr><td>Widget revenue</td><td><ix:nonFraction '
           'name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" scale="6" decimals="-6" '
           'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')
    fc = fact(fid='')
    fc['context_id'] = 'c-1'
    fc.pop('segment', None)
    r = LOC.locate(ANCHOR, src([fc], doc(row)))
    assert len(r['items']) == 1 and r['items'][0]['value'] == Decimal('390'), \
        "a null-graph-id fact must bind via its id-LESS element (unique identity)"


#: THE GRAPH'S OWN IDENTITY for the concept in accession 0001193125-23-136738,
#: read read-only from Neo4j on 2026-08-01 under an unchanged transaction and
#: PINNED here as a literal. It is deliberately NOT derived from the filing this
#: test checks — that would let the candidate vouch for its own expected value.
#: The taxonomy year matters: this one qname exists under SIX different FASB
#: namespaces in the live graph (2021-01-31, 2022, 2023, 2024, 2025, 2026), so
#: the expanded name is what separates a 2022 concept from a 2026 one.
_REAL_FILING_CONCEPT_NS = 'http://fasb.org/us-gaap/2022'
_REAL_FILING_CONCEPT = ('us-gaap:CashCashEquivalentsRestrictedCashAndRestricted'
                        'CashEquivalentsPeriodIncreaseDecreaseIncludingExchange'
                        'RateEffect')


def test_real_idless_fallback_evidence():
    html = _cached('0001193125-23-136738.htm')
    target = IH.graph_concept_target(_REAL_FILING_CONCEPT,
                                     _REAL_FILING_CONCEPT_NS,
                                     _REAL_FILING_CONCEPT)
    assert target is not None, "the pinned graph identity must be usable"
    el, why = IH.identity_fallback(html, target,
                                   'P01_01_2023To04_01_2023', 'Unit_USD')
    # `el` is now the fact seen through BOTH views. The id is an XML
    # attribute, so it is read off the SEMANTIC half.
    assert why == 'ok' and el is not None and not el.sem.get('id')
    ev, w2 = IH.evidence_for_element(html, el)
    assert w2 == 'ok'
    assert IH.reconcile(ev['value_input'], ev['fmt_expanded'], ev['scale'],
                        ev['sign'], '1,406,000') is True, \
        "real id-less fact reconciles"


def test_separate_period_columns_stay_separate():
    ctx2 = ('<xbrli:context id="c-2"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000001234</xbrli:identifier></xbrli:entity><xbrli:period>'
            '<xbrli:startDate>2024-01-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>')
    rows = ('<tr><td>Widget revenue</td>'
            '<td><ix:nonFraction id="f-1" name="us-gaap:Revenues" contextRef="c-1" '
            'unitRef="usd" scale="6" decimals="-6" format="ixt:num-dot-decimal">390'
            '</ix:nonFraction></td>'
            '<td><ix:nonFraction id="f-2" name="us-gaap:Revenues" contextRef="c-2" '
            'unitRef="usd" scale="6" decimals="-6" format="ixt:num-dot-decimal">778'
            '</ix:nonFraction></td></tr>')
    facts = [fact('390,000,000'),
             fact('778,000,000', fid='f-2',
                  period={'startDate': '2024-01-01', 'endDate': '2024-07-01'})]
    r = LOC.locate(ANCHOR, src(facts, doc(rows, ctx_extra=ctx2)))
    assert len(r['items']) == 2, "genuinely separate period columns both bind"
    assert {str(i['value']) for i in r['items']} == {'390', '778'}


def test_different_context_pointers_cannot_share_one_element():
    ctx2 = ('<xbrli:context id="c-2"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000001234</xbrli:identifier></xbrli:entity><xbrli:period>'
            '<xbrli:startDate>2024-04-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>')
    a = fact('390,000,000'); a['context_id'] = 'c-1'; a.pop('segment', None)
    b = fact('390,000,000'); b['context_id'] = 'c-2'; b.pop('segment', None)
    r = LOC.locate(ANCHOR, src([a, b], doc(ROW_390, ctx_extra=ctx2)))
    assert len(r['items']) == 1, \
        "the element's own contextRef admits exactly ONE claiming context"


@pytest.mark.live
def test_real_e2e_shares_count_anchor():
    from driver.channels.fiscal_ai import route_a_source as SRC
    s = SRC.build_source('0000027904-23-000006')
    assert s is not None
    anchor = dict(ANCHOR, series_unit='count', time_type='instant',
                  wording=('Balance',), slice='equity:common_stock',
                  concept_clue='CommonStockSharesOutstanding')
    r = LOC.locate(anchor, s)
    assert r['status'] is None and r['items'], r['status']
    hit = [i for i in r['items']
           if i['value'] == Decimal('654') and i['ix_evidence']['scale'] == 6
           and i['ix_evidence']['unit_ref'] == 'shares'
           and i['xbrl']['ix']['unit_ref'] == 'shares'
           and i['xbrl']['period_start'] is None
           and i['xbrl']['period_end'] == '2023-03-31']
    assert hit, [(str(i['value']), i['ix_evidence']) for i in r['items']][:3]


@pytest.mark.live
def test_real_e2e_per_share_usd_anchor():
    from driver.channels.fiscal_ai import route_a_source as SRC
    s = SRC.build_source('0000027904-23-000006')
    anchor = dict(ANCHOR, series_unit='usd',
                  wording=('per share',),
                  concept_clue='EarningsPerShareBasic')
    r = LOC.locate(anchor, s)
    assert r['status'] is None and r['items'], r['status']
    hit = [i for i in r['items']
           if i['value'] == Decimal('-0.57') and i['ix_evidence']['scale'] == 0
           and i['ix_evidence']['unit_ref'] == 'usdPerShare'
           and 'format' in i['xbrl']['ix']]
    assert hit, [(str(i['value']), i['ix_evidence']) for i in r['items']][:3]


def test_entity_mismatch_abstains():
    # The document states CIK 1234 in the ten-digit form XBRL requires; only
    # the EXPECTED registrant changes below. The rewrite here used to inject a
    # seven-digit identifier, which is now malformed markup — that would have
    # tested the structure rule, not the entity law it is named for.
    d = doc(ROW_390)
    s = src([fact()], d)
    s['company_cik'] = '0000009999'
    assert LOC.locate(ANCHOR, s)['items'] == [], "wrong registrant must abstain"
    s['company_cik'] = '0000001234'
    assert len(LOC.locate(ANCHOR, s)['items']) == 1, "right registrant binds"


def test_packet_boundary_channelcontract_only():
    from driver.channels.fiscal_ai import build_packets as BP
    r = LOC.locate(ANCHOR, src([fact()], doc(ROW_390)))
    it = dict(r['items'][0])
    it.update({'source_id': 'S1', 'source_type': '10q', 'ticker': 'WID',
               'fmt': 'number', 'is_currency': True})
    packets, skip, park = BP.build([it], [], {'WID': 12})
    assert len(packets) == 1 and packets[0]['items']
    leaked = {'ix_evidence', 'unit_meaning', 'source_sha256',
              '_element_id'} & set(packets[0]['items'][0])
    assert not leaked, f"internal fields must never reach the packet: {leaked}"


# ---- corrective-5 item 1: durable pins (GREEN-ON-ARRIVAL — the laws were already
# implemented; these tests were falsely claimed earlier and are added honestly now) --

_ENT = ('<xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000001234'
        '</xbrli:identifier></xbrli:entity>')


def test_two_series_identities_ambiguous():
    ctxs = (f'<xbrli:context id="c-3">{_ENT}<xbrli:period>'
            '<xbrli:startDate>2024-04-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            '<xbrli:scenario><xbrldi:explicitMember dimension="srt:Geo">'
            'x:NorthAmericaMember</xbrldi:explicitMember></xbrli:scenario>'
            f'</xbrli:context><xbrli:context id="c-2">{_ENT}<xbrli:period>'
            '<xbrli:startDate>2024-04-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            '<xbrli:scenario><xbrldi:explicitMember dimension="srt:Geo">'
            'x:SouthAmericaMember</xbrldi:explicitMember></xbrli:scenario>'
            '</xbrli:context>')
    rows = ('<tr><td>America widget revenue north</td><td><ix:nonFraction '
            'id="f-1" name="us-gaap:Revenues" contextRef="c-3" unitRef="usd" '
            'scale="6" decimals="-6" format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>'
            '<tr><td>America widget revenue south</td><td><ix:nonFraction '
            'id="f-2" name="us-gaap:Revenues" contextRef="c-2" unitRef="usd" '
            'scale="6" decimals="-6" format="ixt:num-dot-decimal">120</ix:nonFraction></td></tr>')
    a = fact('390,000,000'); a['context_id'] = 'c-3'
    b = fact('120,000,000', fid='f-2'); b['context_id'] = 'c-2'
    anchor = dict(ANCHOR, wording=('widget revenue',), slice='lock:america')
    r = LOC.locate(anchor, src([a, b], doc(rows, ctx_extra=ctxs)))
    assert r['items'] == [] and r['status'] == 'ambiguous', r


def test_same_series_multiple_periods_all_bind():
    ctx2 = (f'<xbrli:context id="c-2">{_ENT}<xbrli:period>'
            '<xbrli:startDate>2024-01-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            '</xbrli:context>')
    rows = (ROW_390
            + ROW_390.replace('"f-1"', '"f-2"').replace('"c-1"', '"c-2"')
            .replace('>390<', '>778<'))
    facts = [fact('390,000,000'),
             fact('778,000,000', fid='f-2',
                  period={'startDate': '2024-01-01', 'endDate': '2024-07-01'})]
    r = LOC.locate(ANCHOR, src(facts, doc(rows, ctx_extra=ctx2)))
    assert {str(i['value']) for i in r['items']} == {'390', '778'}, r['status']


def test_twin_rows_distinct_exact_spans():
    ctx2 = (f'<xbrli:context id="c-2">{_ENT}<xbrli:period>'
            '<xbrli:startDate>2024-01-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            '</xbrli:context>')
    rows = ROW_390 + ROW_390.replace('"f-1"', '"f-2"').replace('"c-1"', '"c-2"')
    facts = [fact('390,000,000'),
             fact('390,000,000', fid='f-2',
                  period={'startDate': '2024-01-01', 'endDate': '2024-07-01'})]
    r = LOC.locate(ANCHOR, src(facts, doc(rows, ctx_extra=ctx2)))
    assert len(r['items']) == 2
    s1, s2 = (tuple(i['xbrl']['source_evidence']['quote_span'])
              for i in r['items'])
    assert s1 != s2 and r['items'][0]['quote'] == r['items'][1]['quote']
    prep = IH.prepare(doc(rows, ctx_extra=ctx2))
    for i in r['items']:
        a, b = i['xbrl']['source_evidence']['quote_span']
        assert prep['text'][a:b] == i['quote']


def test_a_NON_STRING_expected_CIK_abstains_through_the_public_door():
    """827 Packet 17. The only difference between these two calls is the PYTHON
    TYPE of the expected CIK — same filing, same ten digits, same everything.

    `locate` used to hand the owner `str(source.get('company_cik') or '')`, so
    the integer became the string "1234567890" and BOUND, while the owner it
    was handed to says a non-string refuses. The coercion minted a spelling the
    source never stated and made the gate a formality.

    1234567890 is deliberately a LAWFUL ten-digit CIK: nothing here is
    malformed, so only the repair is on trial."""
    d = doc(ROW_390).replace('0000001234', '1234567890')
    s = src([fact()], d)

    s['company_cik'] = '1234567890'
    assert len(LOC.locate(ANCHOR, s)['items']) == 1, \
        "the lawful STRING twin must still bind"

    s['company_cik'] = 1234567890
    assert LOC.locate(ANCHOR, s)['items'] == [], \
        "the INTEGER must abstain — the door may not repair it into a string"


def test_company_identity_missing_or_mismatched_abstains():
    s = src([fact()], doc(ROW_390))
    del s['company_cik']
    assert LOC.locate(ANCHOR, s)['items'] == [], "missing expected CIK"
    s = src([fact()], doc(ROW_390)); s['company_cik'] = '0000009999'
    assert LOC.locate(ANCHOR, s)['items'] == [], "mismatched CIK"
    noent = doc(ROW_390).replace(_ENT.replace('0001234', '0001234'), '') \
        .replace('<xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">0000001234'
                 '</xbrli:identifier></xbrli:entity>', '')
    assert LOC.locate(ANCHOR, src([fact()], noent))['items'] == [], \
        "missing element entity"


@pytest.mark.live
def test_ce_scale_survives_real_packet_layer():
    from driver.channels.fiscal_ai import build_packets as BP
    from driver.channels.fiscal_ai import route_a_source as SRC
    s = SRC.build_source('0001306830-24-000155')
    anchor = dict(ANCHOR, wording=('North America',), slice='segment:acetyl_chain',
                  concept_clue='RevenueFromContractWithCustomerExcludingAssessedTax')
    r = LOC.locate(anchor, s)
    it = [i for i in r['items'] if str(i['value']) == '390'][0]
    rec = dict(it)
    rec.update({'source_id': s['source_id'], 'source_type': s['source_type'],
                'ticker': 'CE', 'fmt': 'number', 'is_currency': True})
    packets, _, _ = BP.build([rec], [], {'CE': 12})
    pk = packets[0]['items'][0]
    assert pk['value'] == Decimal('390')
    assert pk['xbrl']['ix'] == {'scale': 6, 'sign': '', 'format': '',
                                'unit_ref': 'usd'}, \
        "flags survive the REAL packet layer (real CE element has no format attr)"


def test_period_evidence_boundary_string_and_internal_pieces():
    r = LOC.locate(ANCHOR, src([fact()], doc(ROW_390)))
    it = r['items'][0]
    prep = IH.prepare(doc(ROW_390))
    assert isinstance(it['period_evidence'], str), \
        "frozen boundary: period_evidence stays a STRING (downstream substring code)"
    assert it['period_evidence'] == it['quote'] \
        and it['quote'] in prep['text'], "and it is an EXACT source slice"
    se = it['xbrl']['source_evidence']
    qa, qb = se['quote_span']
    assert prep['text'][qa:qb] == it['quote']
    pieces = se['pieces']
    assert all(p2['kind'] in ('header', 'section') for p2 in pieces)
    assert all(prep['text'][p2['span'][0]:p2['span'][1]] == p2['text']
               for p2 in pieces)
    assert not any(p2['text'] == it['quote'] for p2 in pieces), \
        'the quote is never duplicated into the pieces'
    assert any('Q2 2024' in p2['text'] for p2 in pieces)


# ---------------------------------------------------------------------------
# #827 round 8c — CONCEPT IDENTITY THROUGH THE PUBLIC `locate()` DOOR.
#
# The binder's own tests cannot stand in for these: the locator is a SECOND
# consumer of the same join, and it was still authorising on the graph's stored
# prefix long after the binder stopped. Every case below goes through
# `LOC.locate` and each bad one has a lawful twin.
# ---------------------------------------------------------------------------

_ALIAS_ROW = ('<tr><td>Widget revenue</td><td><ix:nonFraction id="f-1" '
              'name="gaap:Revenues" contextRef="c-1" unitRef="usd" scale="6" decimals="-6" '
              'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')


def _alias_doc(row=_ALIAS_ROW):
    """The same fixture document, plus a SECOND lawful prefix bound to the very
    same taxonomy URI — which is what a raw-name comparison cannot see."""
    return doc(row).replace('xmlns:us-gaap="%s"' % _NS_GAAP,
                            'xmlns:us-gaap="%s" xmlns:gaap="%s"'
                            % (_NS_GAAP, _NS_GAAP), 1)


def _located(fc, html):
    return LOC.locate(ANCHOR, src([fc], html))['items']


def test_827R8c_locate_MUST_ALLOW_a_document_alias_for_the_same_namespace():
    """(1) The filing writes `gaap:Revenues`; the graph stores
    `us-gaap:Revenues`. One taxonomy, two lawful prefixes — the same concept."""
    fc = fact(fid='')
    fc['context_id'] = 'c-1'
    fc.pop('segment', None)
    assert len(_located(fc, _alias_doc())) == 1, \
        "a lawful document alias for the same namespace must bind"


def test_827R8c_locate_the_SAME_local_name_under_a_DIFFERENT_URI_refuses():
    """(2) Alias tolerance must not become name tolerance."""
    fc = fact(fid='')
    fc['context_id'] = 'c-1'
    fc.pop('segment', None)
    other = doc(_ALIAS_ROW).replace('xmlns:us-gaap="%s"' % _NS_GAAP,
                                    'xmlns:us-gaap="%s" '
                                    'xmlns:gaap="http://example.org/OTHER"'
                                    % _NS_GAAP, 1)
    assert _located(fc, other) == [], \
        "a different taxonomy bound as if it were the same concept"


@pytest.mark.parametrize("missing", ["concept_namespace", "graph_concept_qname"])
def test_827R8c_locate_a_MISSING_graph_concept_identity_refuses(missing):
    """(3) No identity, no target, no match — never a guess."""
    fc = fact()
    fc.pop('segment', None)
    fc[missing] = None
    assert _located(fc, doc(ROW_390)) == [], \
        f"a fact with no {missing} was matched anyway"


def test_827R8c_locate_MUST_ALLOW_the_same_fact_once_its_identity_is_present():
    """The twin for every refusal above."""
    fc = fact()
    fc.pop('segment', None)
    assert len(_located(fc, doc(ROW_390))) == 1


def test_827R8c_locate_two_document_aliases_for_ONE_identity_are_ambiguous():
    """(4) Two elements under different prefixes expanding to the SAME identity
    are two candidates for one fact; the fallback cannot say which."""
    twin = _ALIAS_ROW.replace('id="f-1" ', '').replace('gaap:Revenues',
                                                       'us-gaap:Revenues')
    fc = fact(fid='')
    fc['context_id'] = 'c-1'
    fc.pop('segment', None)
    both = _alias_doc(_ALIAS_ROW.replace('id="f-1" ', '') + twin)
    assert _located(fc, both) == [], "two candidates for one fact were bound"


@pytest.mark.parametrize("order", ["good_then_bad", "bad_then_good"])
def test_827R8c_locate_CONFLICTING_graph_identities_refuse_in_BOTH_orders(order):
    """(5) THE ROW-ORDER CASE. Two records under one stored concept key naming
    DIFFERENT namespaces cannot say which concept the key means, so the key
    abstains — whichever order they arrive in. Deriving the target per row let
    the good one bind while the conflicting one was silently skipped."""
    good = fact()
    good.pop('segment', None)
    bad = dict(good, concept_namespace='http://example.org/OTHER-taxonomy')
    facts = [good, bad] if order == "good_then_bad" else [bad, good]
    r = LOC.locate(ANCHOR, src(facts, doc(ROW_390)))
    assert r['items'] == [], \
        f"a conflicting graph Concept identity was resolved by row order ({order})"


def test_827R8c_locate_the_lawful_EXACT_ID_path_is_unchanged():
    """(6) The exact-id path keeps working exactly as before."""
    fc = fact(fid='f-1')
    fc.pop('segment', None)
    assert len(_located(fc, doc(ROW_390))) == 1


# ---------------------------------------------------------------------------
# #827 round 9 — DIMENSION prefixes through the public `locate()` door.
#
# The round-8c block above covers the CONCEPT's identity. A dimension travels a
# different path and needed its own controls.
#
# WHAT THIS LANE CAN AND CANNOT DECIDE, measured rather than assumed. With the
# raw-`segment` branch deleted, the producer sends the exact `context_id` and
# NO dimension identity at all, so the joined context is the sole authority and
# its dimensions are correct by construction. Driving one fixture four ways:
#
#     declared prefix -> its own URI          binds
#     ALIAS prefix    -> the SAME URI         binds      <- test 1 below
#     same spelling   -> a DIFFERENT URI      binds
#     UNDECLARED prefix                       REFUSES    <- test 2 below
#
# So a wrong-namespace REFUSAL is not a rule this lane holds, and asserting one
# here would pin a law that does not exist. It is not missing: a dimension URI
# can only disagree where the graph states one, which is the Core binder lane —
# proven there by `test_bind_graph_fact` and by the namespace park in
# `test_round10_event_boundary`. Recorded for the reviewer rather than papered
# over with a test that passes for the wrong reason.
# ---------------------------------------------------------------------------

_DIM_ROW = ('<tr><td>Widget revenue North America</td><td>'
            '<ix:nonFraction id="f-2" name="us-gaap:Revenues" contextRef="c-2" '
            'unitRef="usd" scale="6" decimals="-6" format="ixt:num-dot-decimal">390'
            '</ix:nonFraction></td></tr>')

_DIM_ANCHOR = dict(ANCHOR, slice="geography:north_america",
                   wording=("Widget revenue North America",))

#: READ OUT OF THE FIXTURE ITSELF, never transcribed — the alias below must
#: name the very URI this document already binds, or the test would prove
#: nothing about aliasing.
_FIXTURE_NS_GEO = re.search(r'xmlns:geo="([^"]+)"', doc()).group(1)


def _dim_doc(prefix, declare=None):
    """The proven fixture plus a DIMENSIONED context `c-2`, written with
    whatever prefix the caller names. `declare` binds one extra prefix."""
    ctx = ('<xbrli:context id="c-2"><xbrli:entity><xbrli:identifier '
           'scheme="http://www.sec.gov/CIK">0000001234</xbrli:identifier>'
           f'<xbrli:segment><xbrldi:explicitMember dimension="{prefix}:RegionAxis">'
           f'{prefix}:NorthAmericaMember</xbrldi:explicitMember></xbrli:segment>'
           '</xbrli:entity><xbrli:period>'
           '<xbrli:startDate>2024-04-01</xbrli:startDate>'
           '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
           '</xbrli:context>')
    html = doc(body_rows=_DIM_ROW, ctx_extra=ctx)
    if declare is not None:
        html = html.replace('xmlns:xbrli=',
                            f'xmlns:{prefix}="{declare}" xmlns:xbrli=', 1)
    return html


def _dim_located(html):
    fc = fact(fid='f-2')
    fc['context_id'] = 'c-2'
    return LOC.locate(_DIM_ANCHOR, src([fc], html))['items']


def test_827R9_locate_MUST_ALLOW_a_dimension_under_ANOTHER_lawful_prefix():
    """A second prefix bound to the same namespace names the same dimension.

    THE POSITIVE HALF, and it is what makes the refusal below meaningful: the
    fixture is identical except for the prefix, so a refusal there cannot be
    blamed on the concept, context, unit, period or fixture shape — all of
    which this case proves are fine.
    """
    same_uri = _FIXTURE_NS_GEO
    assert len(_dim_located(_dim_doc('geo2', declare=same_uri))) == 1, \
        "a lawful alias for the dimension's namespace must still bind"
    # And the product output keeps the filing's OWN spelling, not an expansion.
    assert _dim_located(_dim_doc('geo2', declare=same_uri))[0]['xbrl'][
        'axis_members'] == [('geo2:RegionAxis', 'geo2:NorthAmericaMember')]


def test_827R9_locate_REFUSES_a_dimension_whose_prefix_is_UNDECLARED():
    """An undeclared prefix is not a QName, so the context states no dimension
    this filing can be held to — and the fact must not be located through it.

    Reaches the DIMENSION rule and no earlier gate. The twin above binds the
    very same document with the very same concept, context id, unit and period,
    differing ONLY in whether the prefix is declared; and the reason is read
    back below rather than inferred from the empty result, because an empty
    list is what every unrelated failure also looks like.
    """
    html = _dim_doc('zzz')
    assert _dim_located(html) == [], \
        "a member whose prefix nobody declared was read as a real dimension"
    ev, why = IH.element_evidence(html, 'f-2')
    assert (ev, why) == (None, 'malformed_context_structure'), why
    # ...and the twin's element is readable, so the refusal is the dimension's.
    assert IH.element_evidence(
        _dim_doc('geo2', declare=_FIXTURE_NS_GEO), 'f-2')[1] == 'ok'


# ---------------------------------------------------------------------------
# #827 round 9 — SEMANTIC IDENTITY inside `locate`, not just at the join.
#
# Removing the raw graph comparison did not remove the locator's LATER uses of
# raw spellings: the dedup `fact_key`, the `series_ids` ambiguity count, and
# the final quote grouping all keyed on the filing's own prefixed text. So two
# lawful aliases for ONE namespace counted as TWO series (a real filing then
# lost every item to the ambiguity guard), and two DIFFERENT taxonomies sharing
# a local name counted as ONE. These drive that through the public door.
# ---------------------------------------------------------------------------

_TWO_ROWS = (
    '<tr><td>Widget revenue North America</td><td><ix:nonFraction id="f-2" '
    'name="us-gaap:Revenues" contextRef="c-2" unitRef="usd" scale="6" decimals="-6" '
    'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>'
    '<tr><td>Widget revenue North America</td><td><ix:nonFraction id="f-3" '
    'name="us-gaap:Revenues" contextRef="c-3" unitRef="usd" scale="6" decimals="-6" '
    'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')


def _two_ctx_doc(uri_b):
    """Two contexts naming the SAME axis and member local names, under two
    different PREFIXES — `geo` (the fixture's own) and `gx` (bound here to
    whatever the caller says). Only the URI behind `gx` differs between the
    two cases below, so nothing else can explain a change in outcome."""
    def ctx(cid, prefix):
        return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier '
                'scheme="http://www.sec.gov/CIK">0000001234</xbrli:identifier>'
                f'<xbrli:segment><xbrldi:explicitMember dimension="{prefix}:RegionAxis">'
                f'{prefix}:NorthAmericaMember</xbrldi:explicitMember></xbrli:segment>'
                '</xbrli:entity><xbrli:period>'
                '<xbrli:startDate>2024-04-01</xbrli:startDate>'
                '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
                '</xbrli:context>')
    html = doc(body_rows=_TWO_ROWS, ctx_extra=ctx('c-2', 'geo') + ctx('c-3', 'gx'))
    return html.replace('xmlns:xbrli=', f'xmlns:gx="{uri_b}" xmlns:xbrli=', 1)


def _gfact(fid, cid):
    fc = fact(fid=fid)
    fc['context_id'] = cid
    return fc


_PAIR = (('f-2', 'c-2'), ('f-3', 'c-3'))


def _two_located(uri_b, order=_PAIR):
    facts = [_gfact(fid, cid) for fid, cid in order]
    return LOC.locate(_DIM_ANCHOR, src(facts, _two_ctx_doc(uri_b)))


def _each_binds_alone(uri_b):
    """PRECONDITION FOR BOTH CONTROLS BELOW. Each row must locate on its own,
    or a two-row refusal proves only that something earlier — concept, context,
    unit, period, wording — rejected one of them, and the series rule would
    never have been reached at all."""
    for fid, cid in _PAIR:
        out = LOC.locate(_DIM_ANCHOR, src([_gfact(fid, cid)],
                                          _two_ctx_doc(uri_b)))
        assert len(out['items']) == 1, \
            f"{fid} does not bind alone ({out['status']}) — the two-row " \
            f"result below would prove the wrong gate"


def test_827R9_two_ALIASES_for_one_namespace_are_ONE_semantic_series():
    """Same URI, same local names, two prefixes — one series, so the ambiguity
    guard must not fire. Keyed on spellings this looked like two series and the
    guard emptied the result, losing a fact the filing states plainly."""
    _each_binds_alone(_FIXTURE_NS_GEO)
    for order in (_PAIR, _PAIR[::-1]):
        out = _two_located(_FIXTURE_NS_GEO, order)
        assert out['status'] is None and out['items'], \
            f"lawful aliases were treated as competing series: {out['status']}"
        # THE PUBLISHED SPELLINGS ARE STILL THE FILING'S OWN — identity decides
        # sameness, it never rewrites what the product reports...
        assert {tuple(it['xbrl']['axis_members'][0]) for it in out['items']} <= {
            ('geo:RegionAxis', 'geo:NorthAmericaMember'),
            ('gx:RegionAxis', 'gx:NorthAmericaMember')}
        # ...and the internal key never crosses the boundary. The frozen
        # contract's field allowlist would refuse it, so a leak here is a
        # product break and not merely untidy.
        assert all('_identity' not in it for it in out['items'])


def test_827R9_aliased_readings_of_ONE_fact_FOLD_to_a_single_item():
    """THE FINAL QUOTE GROUPING — a separate site, so a separate detector.

    Both rows render the same quote for the same period in the same series:
    one reading told twice, which the last grouping must fold. Keyed on the
    written spellings it saw two different dimensions and published the fact
    TWICE. Kept apart from the series test above because each of the three
    identity sites must be observable on its own — otherwise one mutant flips
    two detectors and neither is pinned to the code it guards.
    """
    _each_binds_alone(_FIXTURE_NS_GEO)
    for order in (_PAIR, _PAIR[::-1]):
        out = _two_located(_FIXTURE_NS_GEO, order)
        # THE PRECONDITION, SAID SEPARATELY. The grouping runs last, so if the
        # ambiguity guard before it has already emptied the list there is
        # nothing here to fold — a real failure, but of that guard, and the
        # message must not blame this one.
        assert out['items'], \
            f"nothing reached the grouping ({out['status']}) — the ambiguity " \
            f"guard upstream failed, not the fold"
        assert len(out['items']) == 1, \
            f"aliases of one dimension survived as {len(out['items'])} " \
            f"facts ({order})"


def test_827R9_one_element_claimed_under_TWO_CONCEPT_ALIASES_is_not_a_conflict():
    """THE PER-ELEMENT DEDUP, which the other two controls never reach.

    The graph offers the same fact under two concept keys — `us-gaap:Revenues`
    and `gaap:Revenues` — that this filing binds to ONE taxonomy URI. That is
    one claim written twice, not two competing claims. Keyed on the spellings
    the two became rival claims on a single element, the clash guard fired, and
    the fact was dropped as ambiguous: a filing lost a number it states plainly
    because it spelled one namespace two lawful ways.
    """
    fc = fact(fid='f-1')
    fc['context_id'] = 'c-1'
    blob = json.dumps({
        'us-gaap:Revenues': [dict(fc)],
        'gaap:Revenues': [dict(fc, graph_concept_qname='gaap:Revenues')]})
    out = LOC.locate(ANCHOR, {
        'source_id': 'S1', 'source_type': '10k', 'xbrls': [blob], 'texts': [],
        'inline_html': _alias_doc(), 'company_cik': '0000001234'})
    assert (len(out['items']), out['status']) == (1, None), \
        f"two aliases of one concept became a conflict: {out['status']}"


def test_827R9_the_same_LOCAL_NAMES_under_DIFFERENT_URIs_stay_DIFFERENT():
    """MUST-REFUSE twin, identical but for the URI behind one prefix: two
    taxonomies that share a local name are two series, so the filing is
    genuinely ambiguous for this anchor and nothing may be picked by order."""
    other = 'http://example.org/OTHER-taxonomy'
    _each_binds_alone(other)
    # BOTH INPUT ORDERS. A one-order assertion passes on the very defect it is
    # named for, because collapsing keeps whichever row arrived first.
    for order in (_PAIR, _PAIR[::-1]):
        assert _two_located(other, order)['items'] == [], \
            f"two different taxonomies were collapsed into one series ({order})"
