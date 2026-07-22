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
    return f"""<html><body>
<div style="display:none">
 <ix:hidden>{hidden_facts}</ix:hidden>
 <ix:resources>
  <xbrli:context id="c-1"><xbrli:entity><xbrli:identifier scheme="s">0001234</xbrli:identifier></xbrli:entity><xbrli:period>
    <xbrli:startDate>2024-04-01</xbrli:startDate>
    <xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>
  {ctx_extra}
  <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
 </ix:resources>
</div>
<p>Distant unrelated paragraph naming Alpha widget special revenue in prose.</p>
<table>
 <tr><td></td><th>Q2 2024</th></tr>
 {body_rows}
</table>
{extra}
</body></html>"""


ROW_390 = ('<tr><td>Widget revenue</td><td><ix:nonFraction id="f-1" '
           'name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" scale="6" '
           'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')


def fact(value='390,000,000', fid='f-1', unit='usd', period=GQ2, seg=None,
         meaning=UNIT):
    fc = {'value': value, 'period': period, 'unitRef': unit, 'fact_id': fid}
    if meaning is not None:
        fc.update(meaning)
    if seg is not None:
        fc['segment'] = seg
    return fc


def src(facts, html, texts=()):
    return {'source_id': 'S1', 'source_type': '10k',
            'xbrls': [json.dumps({'us-gaap:Revenues': facts})],
            'texts': list(texts), 'inline_html': html,
            'company_cik': '1234'}


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
    ctx = ('<xbrli:context id="c-t"><xbrli:period>'
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


def test_reconcile_and_printed_value():
    assert IH.reconcile('390', 'ixt:num-dot-decimal', 6, '', '390,000,000') is True
    assert IH.reconcile('117,679', 'ixt:num-dot-decimal', 3, '', '117679000') is True
    assert IH.reconcile('98', 'ixt:num-dot-decimal', 0, '-', '(98)') is True
    assert IH.reconcile('390', 'ixt:num-dot-decimal', 6, '', '391000000') is False
    assert IH.reconcile('5', 'ixt:unknown', 0, '', '5') is False
    assert IH.printed_value('390', 'ixt:num-dot-decimal', '') == Decimal('390')
    assert IH.printed_value('117,679', 'ixt:num-dot-decimal', '-') \
        == Decimal('-117679')


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


def test_unit_tuple_map_fail_closed():
    r = LOC.locate(ANCHOR, src([fact(meaning=None)], doc(ROW_390)))
    assert r['items'] == [], "missing semantic unit meaning -> abstain"
    div = {'unit_name': 'iso4217:USD', 'is_divide': '1'}
    assert LOC.locate(ANCHOR, src([fact(meaning=div)], doc(ROW_390)))['items'] == []
    odd = {'unit_name': 'unknownunit', 'is_divide': '0'}
    assert LOC.locate(ANCHOR, src([fact(meaning=odd)], doc(ROW_390)))['items'] == []
    junk = {'unit_name': 'iso4217:USD', 'is_divide': 'yes'}
    assert LOC.locate(ANCHOR, src([fact(meaning=junk)], doc(ROW_390)))['items'] == [], \
        "non-'0'/'1' boolean strings abstain (strict normalization)"


def test_padded_or_nonstring_ids_rejected_no_fallback():
    assert LOC.locate(ANCHOR, src([fact(fid=' f-1 ')], doc(ROW_390)))['items'] == []
    assert LOC.locate(ANCHOR, src([fact(fid=7)], doc(ROW_390)))['items'] == []


def test_numeric_headers_and_digit_labels_retained():
    rows = ('<tr><td></td><th>2024</th></tr>'
            '<tr><td>Product 50 widget revenue</td><td><ix:nonFraction id="f-1" '
            'name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" scale="6" '
            'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')
    d = doc('') .replace('<tr><td></td><th>Q2 2024</th></tr>\n ', rows)
    ev, reason = IH.element_evidence(d, 'f-1')
    assert reason == 'ok'
    assert '2024' in ev['columns'], "numeric-only headers are part of the stack"
    assert ev['row_label'] == 'Product 50 widget revenue'


def test_leading_dot_forms():
    assert IH.printed_value('.300', 'ixt:num-dot-decimal', '') == Decimal('0.300')
    assert IH.reconcile('.300', 'ixt:num-dot-decimal', -2, '', '0.003') is True


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
           'unitRef="usd" scale="6" format="ixt:num-dot-decimal">390'
           '</ix:nonFraction></td></tr>')
    r = LOC.locate(ANCHOR, src([fact()], doc(row)))
    assert r['items'] == [], "CSS-hidden text must not prove identity"


def test_hidden_fact_element_abstains():
    hid = ('<ix:nonFraction id="f-h" name="us-gaap:Revenues" contextRef="c-1" '
           'unitRef="usd" scale="6">390</ix:nonFraction>')
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
             {'value': '4000000000', 'unitRef': 'U_USD', 'period':
              {'startDate': '2024-01-01', 'endDate': '2024-12-31'}}]})],
         'texts': ["Widget revenue was 4,000,000,000 for the year"]}
    out = LOC.locate(ANCHOR, s)
    assert out['items'] == [] and out['status'] == 'no_proven_match', out


def test_real_ce_filing_end_to_end():
    p = os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed', 'relocate_probe',
                     'inline_html_cache', '0001306830-24-000155.htm')
    html = open(os.path.abspath(p), encoding='utf-8', errors='replace').read()
    seg = [{'dimension': 'srt:StatementGeographicalAxis',
            'value': 'srt:NorthAmericaMember'},
           {'dimension': 'us-gaap:StatementBusinessSegmentsAxis',
            'value': 'ce:AcetylChainMember'}]
    fc = {'value': '390,000,000', 'unitRef': 'usd', 'fact_id': 'f-1357',
          'unit_name': 'iso4217:USD', 'is_divide': '0', 'segment': seg,
          'period': {'startDate': '2024-04-01', 'endDate': '2024-07-01'}}
    anchor = dict(ANCHOR, wording=('North America',),
                  slice='segment:acetyl_chain')
    s = {'source_id': 'CE-10Q', 'source_type': '10q', 'company_cik': '1306830',
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
    assert IH.reconcile(ev['displayed'], ev['fmt'], ev['scale'], ev['sign'],
                        '654,000,000') is True, "real shares fact reconciles"
    ev2, reason2 = IH.element_evidence(html, 'f-685')   # DAL loss per share
    assert reason2 == 'ok'
    assert IH.reconcile(ev2['displayed'], ev2['fmt'], ev2['scale'], ev2['sign'],
                        '-0.57') is True, "real USD-per-share fact reconciles"


def test_bools_reject_python_types():
    for bad in (False, True, 0, 1):
        m = {'unit_name': 'iso4217:USD', 'is_divide': bad}
        assert LOC.locate(ANCHOR, src([fact(meaning=m)], doc(ROW_390)))['items'] \
            == [], f"is_divide={bad!r} must abstain (only '0'/'1' strings bind)"


def test_idless_element_fallback_binds():
    row = ('<tr><td>Widget revenue</td><td><ix:nonFraction '
           'name="us-gaap:Revenues" contextRef="c-1" unitRef="usd" scale="6" '
           'format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>')
    fc = fact(fid='')
    fc['context_id'] = 'c-1'
    fc.pop('segment', None)
    r = LOC.locate(ANCHOR, src([fc], doc(row)))
    assert len(r['items']) == 1 and r['items'][0]['value'] == Decimal('390'), \
        "a null-graph-id fact must bind via its id-LESS element (unique identity)"


def test_real_idless_fallback_evidence():
    html = _cached('0001193125-23-136738.htm')
    el, why = IH.identity_fallback(html,
        'us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCash'
        'EquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect',
        'P01_01_2023To04_01_2023', 'Unit_USD')
    assert why == 'ok' and el is not None and not el.get('id')
    ev, w2 = IH.evidence_for_element(html, el)
    assert w2 == 'ok'
    assert IH.reconcile(ev['displayed'], ev['fmt'], ev['scale'], ev['sign'],
                        '1,406,000') is True, "real id-less fact reconciles"


def test_separate_period_columns_stay_separate():
    ctx2 = ('<xbrli:context id="c-2"><xbrli:entity><xbrli:identifier scheme="s">0001234</xbrli:identifier></xbrli:entity><xbrli:period>'
            '<xbrli:startDate>2024-01-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>')
    rows = ('<tr><td>Widget revenue</td>'
            '<td><ix:nonFraction id="f-1" name="us-gaap:Revenues" contextRef="c-1" '
            'unitRef="usd" scale="6" format="ixt:num-dot-decimal">390'
            '</ix:nonFraction></td>'
            '<td><ix:nonFraction id="f-2" name="us-gaap:Revenues" contextRef="c-2" '
            'unitRef="usd" scale="6" format="ixt:num-dot-decimal">778'
            '</ix:nonFraction></td></tr>')
    facts = [fact('390,000,000'),
             fact('778,000,000', fid='f-2',
                  period={'startDate': '2024-01-01', 'endDate': '2024-07-01'})]
    r = LOC.locate(ANCHOR, src(facts, doc(rows, ctx_extra=ctx2)))
    assert len(r['items']) == 2, "genuinely separate period columns both bind"
    assert {str(i['value']) for i in r['items']} == {'390', '778'}


def test_different_context_pointers_cannot_share_one_element():
    ctx2 = ('<xbrli:context id="c-2"><xbrli:entity><xbrli:identifier scheme="s">0001234</xbrli:identifier></xbrli:entity><xbrli:period>'
            '<xbrli:startDate>2024-04-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>')
    a = fact('390,000,000'); a['context_id'] = 'c-1'; a.pop('segment', None)
    b = fact('390,000,000'); b['context_id'] = 'c-2'; b.pop('segment', None)
    r = LOC.locate(ANCHOR, src([a, b], doc(ROW_390, ctx_extra=ctx2)))
    assert len(r['items']) == 1, \
        "the element's own contextRef admits exactly ONE claiming context"


def test_real_e2e_shares_count_anchor():
    sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed'))
    import route_a_source as SRC
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
           and i['xbrl']['period_end'] == '2023-03-31']
    assert hit, [(str(i['value']), i['ix_evidence']) for i in r['items']][:3]


def test_real_e2e_per_share_usd_anchor():
    sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed'))
    import route_a_source as SRC
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
    d = doc(ROW_390).replace(
        '<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier scheme="s">0001234</xbrli:identifier></xbrli:entity><xbrli:period>',
        '<xbrli:context id="c-1"><xbrli:entity><xbrli:identifier>0001234'
        '</xbrli:identifier></xbrli:entity><xbrli:period>')
    s = src([fact()], d)
    s['company_cik'] = '9999'
    assert LOC.locate(ANCHOR, s)['items'] == [], "wrong registrant must abstain"
    s['company_cik'] = '1234'
    assert len(LOC.locate(ANCHOR, s)['items']) == 1, "right registrant binds"


def test_packet_boundary_channelcontract_only():
    sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed'))
    import build_packets as BP
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

_ENT = ('<xbrli:entity><xbrli:identifier scheme="s">0001234'
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
            'scale="6" format="ixt:num-dot-decimal">390</ix:nonFraction></td></tr>'
            '<tr><td>America widget revenue south</td><td><ix:nonFraction '
            'id="f-2" name="us-gaap:Revenues" contextRef="c-2" unitRef="usd" '
            'scale="6" format="ixt:num-dot-decimal">120</ix:nonFraction></td></tr>')
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


def test_company_identity_missing_or_mismatched_abstains():
    s = src([fact()], doc(ROW_390))
    del s['company_cik']
    assert LOC.locate(ANCHOR, s)['items'] == [], "missing expected CIK"
    s = src([fact()], doc(ROW_390)); s['company_cik'] = '9999'
    assert LOC.locate(ANCHOR, s)['items'] == [], "mismatched CIK"
    noent = doc(ROW_390).replace(_ENT.replace('0001234', '0001234'), '') \
        .replace('<xbrli:entity><xbrli:identifier scheme="s">0001234'
                 '</xbrli:identifier></xbrli:entity>', '')
    assert LOC.locate(ANCHOR, src([fact()], noent))['items'] == [], \
        "missing element entity"


def test_ce_scale_survives_real_packet_layer():
    sys.path.insert(0, os.path.join(_HERE, '..', '..', 'scripts', 'driver_seed'))
    import build_packets as BP
    import route_a_source as SRC
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
