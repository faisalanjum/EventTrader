"""Explicit inline-XBRL relationships are kept as source evidence (Codex ix_footnotes/DESIGN_REVIEW; Fable's shape): every route says whether the strict
XML reading of its document succeeded - `{read: false, error}` is never "no relationships" - and keeps one record per relationship element of the
Inline XBRL 1.1 namespace (whatever its prefix), its attributes as the parser reads them and its reference lists in order, each reference resolved
only to the element its id names: `one` only for exactly one element of the kind the relationship admits; `none`, `several` and `wrong type` keep
the reference and claim no owner. Owners are the source links' own: the units, cells and pictures holding what the element shows - [] when it
shows nothing (empty or hidden alike), null when the scan is uncertain. Continuations are followed in order and stop at the first link that is not
one (missing, duplicated, of another kind, or a cycle). Expected owners are read off the route's own units by their text, never from the candidate."""
import json
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert import edgartools_html as eh

IX = 'http://www.xbrl.org/2013/inlineXBRL'
FF = 'http://www.xbrl.org/2003/arcrole/fact-footnote'


def doc(body, header, prefix='ix', ns=IX, before=''):
    return (f'<?xml version="1.0" encoding="utf-8"?>{before}<html xmlns="http://www.w3.org/1999/xhtml" xmlns:{prefix}="{ns}"><head><title>T</title></head><body>'
            f'<div style="display:none"><{prefix}:header><{prefix}:resources>{header}</{prefix}:resources></{prefix}:header></div>{body}</body></html>').encode()


def fact(i, value, p='ix', kind='nonFraction'): return f'<{p}:{kind} id="{i}" name="us-gaap:Assets" contextRef="c" unitRef="u" decimals="0">{value}</{p}:{kind}>'


TABLE = lambda p='ix': f'<table><tr><td>Total assets (A)</td><td>{fact("f1", "30,929", p)}</td><td>{fact("f2", "27,192", p)}</td></tr></table>'
NOTES = lambda p='ix': f'<p><{p}:footnote id="n1">Includes VIE balances.</{p}:footnote></p><p><{p}:footnote id="n2">Excludes taxes.</{p}:footnote></p>'


def rel(frm, to, p='ix', role=FF): return f'<{p}:relationship fromRefs="{frm}" toRefs="{to}"' + (f' arcrole="{role}"' if role else '') + '/>'


def route(raw): return eh.convert(raw, 'f.htm', anchor.sha256(raw))


def owned(r, endpoint):  # the texts of an endpoint's owners, read off the route's units
    by = {u['id']: u for u in r['units']}
    def text(o):
        u = by[o['unit']]
        return 'picture' if u['kind'] == 'image' else next(c['text'] for c in u['cells'] if c['anchor']['byte_start'] == o['cell']) if 'cell' in o else u['text']
    return None if endpoint['owners'] is None else [text(o) for o in endpoint['owners']]


class Relationships(unittest.TestCase):
    def test_a_fact_in_a_cell_and_its_note(self):  # failed before: no such field
        raw = doc(TABLE() + NOTES(), rel('f1', 'n1')); r = route(raw)
        self.assertEqual(r['source_relations']['read'], True)
        [x] = r['source_relations']['relationships']
        self.assertTrue(raw[x['at']:].startswith(b'<ix:relationship '))
        self.assertEqual(x['attributes'], {'fromRefs': 'f1', 'toRefs': 'n1', 'arcrole': FF})
        [f], [t] = x['from'], x['to']
        self.assertEqual((f['ref'], f['status'], f['element'], owned(r, f)), ('f1', 'one', IX + '}nonFraction', ['30,929']))
        self.assertEqual((t['ref'], t['status'], t['element'], owned(r, t)), ('n1', 'one', IX + '}footnote', ['Includes VIE balances.']))
        self.assertTrue(raw[f['extent']['byte_start']:].startswith(b'<ix:nonFraction') and raw[f['extent']['byte_end_exclusive']:].startswith(b'</ix:nonFraction>'))  # start tag to end tag

    def test_the_namespace_decides_not_the_prefix(self):
        r = route(doc(TABLE('q') + NOTES('q'), rel('f1', 'n1', 'q'), prefix='q'))
        self.assertEqual([(e['ref'], e['status']) for x in r['source_relations']['relationships'] for e in x['from'] + x['to']], [('f1', 'one'), ('n1', 'one')])
        r = route(doc(TABLE() + NOTES(), rel('f1', 'n1'), ns='http://example.com/not-inline-xbrl'))
        self.assertEqual(r['source_relations'], {'read': True, 'relationships': []})  # the same prefix bound elsewhere: no relationship
        r = route(doc(TABLE() + NOTES(), rel('f1', 'n1'), ns='http://www.xbrl.org/2013/inline&#x58;BRL'))
        self.assertEqual(len(r['source_relations']['relationships']), 1)  # a namespace written with a reference is that namespace

    def test_reference_lists_keep_their_order_and_absent_stays_absent(self):
        r = route(doc(TABLE() + NOTES(), rel('f2 f1', 'n2 n1', role=None)))
        [x] = r['source_relations']['relationships']
        self.assertEqual((x['attributes'], [e['ref'] for e in x['from']], [e['ref'] for e in x['to']]), ({'fromRefs': 'f2 f1', 'toRefs': 'n2 n1'}, ['f2', 'f1'], ['n2', 'n1']))
        self.assertEqual([owned(r, e) for e in x['to']], [['Excludes taxes.'], ['Includes VIE balances.']])

    def test_kinds_and_bad_references_claim_no_owner(self):
        explanatory = 'http://www.xbrl.org/2009/arcrole/fact-explanatoryFact'
        body = TABLE() + NOTES() + '<p>' + fact('t1', 'An explanation.', kind='nonNumeric') + '</p><p id="n1x">x</p>'
        r = route(doc(body + '<p><ix:footnote id="dup">One.</ix:footnote></p><p><ix:footnote id="dup">Two.</ix:footnote></p>',
                      rel('f1', 't1', role=explanatory) + rel('n1', 'n1') + rel('f1', 'f2', role=None) + rel('f1', 'nope') + rel('f1', 'dup') + rel('f1', 'n1x') + rel('f1', 'n2 f2')))
        got = [(e['ref'], e['status'], e['owners'] is None) for x in r['source_relations']['relationships'] for e in x['to']]
        self.assertEqual(got, [('t1', 'one', False), ('n1', 'one', False), ('f2', 'one', False), ('nope', 'none', True), ('dup', 'several', True), ('n1x', 'wrong type', True),
                               ('n2', 'one', False), ('f2', 'wrong type', True)])  # a fact may point to a fact, with any role or none; a set holding a footnote holds footnotes only (13.1); a plain element is no target
        self.assertEqual([(e['ref'], e['status']) for e in r['source_relations']['relationships'][1]['from']], [('n1', 'wrong type')])  # a relationship starts at a fact

    def test_continuations_in_order_and_where_they_break(self):
        notes = lambda tail: f'<p><ix:footnote id="n1" continuedAt="c1">Part one,</ix:footnote></p><p><ix:continuation id="c1" continuedAt="c2">part two,</ix:continuation></p><p><ix:continuation id="c2"{tail}>part three.</ix:continuation></p>'
        def chain(tail):
            e = route(doc(TABLE() + notes(tail) + '<p><ix:footnote id="n2">Other.</ix:footnote></p>', rel('f1', 'n1')))['source_relations']['relationships'][0]['to'][0]
            return e['chain'], [(c['ref'], c['status']) for c in e['continuations']]
        self.assertEqual(chain(''), ('complete', [('c1', 'one'), ('c2', 'one')]))
        self.assertEqual(chain(' continuedAt="c1"'), ('unresolved', [('c1', 'one'), ('c2', 'one'), ('c1', 'cycle')]))
        self.assertEqual(chain(' continuedAt="cX"'), ('unresolved', [('c1', 'one'), ('c2', 'one'), ('cX', 'none')]))
        self.assertEqual(chain(' continuedAt="n2"'), ('unresolved', [('c1', 'one'), ('c2', 'one'), ('n2', 'wrong type')]))
        self.assertEqual(chain(' continuedAt=" c 9 "'), ('unresolved', [('c1', 'one'), ('c2', 'one'), (' c 9 ', 'none')]))  # a malformed reference kept as written
        r = route(doc(TABLE() + notes(''), rel('f1', 'n1'))); t = r['source_relations']['relationships'][0]['to'][0]
        self.assertEqual([owned(r, c) for c in t['continuations']], [['part two,'], ['part three.']])

    def test_what_an_endpoint_shows_decides_its_owners(self):
        body = TABLE() + '<div style="display:none"><ix:footnote id="h">Hidden.</ix:footnote></div><p><ix:footnote id="e"></ix:footnote></p><p><ix:footnote id="p"><img src="x.png" alt="x"/></ix:footnote></p>'
        r = route(doc(body, rel('f1', 'h e p')))
        self.assertEqual([(e['ref'], e['status'], owned(r, e), e.get('visible')) for e in r['source_relations']['relationships'][0]['to']],
                         [('h', 'one', [], 0), ('e', 'one', [], 0), ('p', 'one', ['picture'], 0)])  # hidden and empty alike show nothing; a picture is held

    def test_a_self_closed_element_ends_where_the_xml_ends_it(self):  # Codex: an HTML reading would run it on past its "/>"
        r = route(doc(TABLE() + '<p><ix:footnote id="n3"/>Unrelated text after it.</p><p><ix:footnote id="n4">Shown.</ix:footnote> Then more.</p>', rel('f1', 'n3 n4')))
        self.assertEqual([(e['ref'], e['status'], owned(r, e), e.get('visible')) for e in r['source_relations']['relationships'][0]['to']],
                         [('n3', 'one', [], 0), ('n4', 'one', ['Shown. Then more.'], 6)])  # empty: owns nothing; the literal counterpart owns its unit, six characters of it

    def test_a_nested_fact_and_an_uncertain_scan(self):
        body = TABLE() + '<p>' + fact('t1', 'Text with ' + fact('f3', '5') + ' inside.', kind='nonNumeric') + '</p>' + NOTES()
        r = route(doc(body, rel('f3 t1', 'n1')))
        self.assertEqual([[' '.join(x.split()) for x in owned(r, e)] for e in r['source_relations']['relationships'][0]['from']], [['Text with 5 inside.'], ['Text with 5 inside.']])  # (the tool's own spaces around an inline fact)
        r = route(doc(TABLE() + NOTES() + '<svg xmlns="http://www.w3.org/2000/svg"><text>x</text></svg>', rel('f1', 'n1')))  # content the scanner does not model
        self.assertEqual([(e['status'], e['owners']) for x in r['source_relations']['relationships'] for e in x['from'] + x['to']], [('one', None), ('one', None)])

    def test_an_unread_document_is_never_no_relationships(self):
        for raw in (doc(TABLE() + NOTES(), rel('f1', 'n1')).replace(b'</table>', b''),  # not well-formed
                    doc(TABLE() + NOTES() + '<p>&ext;</p>', rel('f1', 'n1'), before='<!DOCTYPE html [<!ENTITY ext SYSTEM "http://example.com/x">]>'),  # an external entity: refused
                    b'<html><body><p>Text<br><p>More &nbsp; text</body></html>'):  # ordinary HTML
            r = route(raw)
            self.assertEqual((r['status'], r['source_relations']['read'], 'relationships' in r['source_relations'], bool(r['source_relations'].get('error'))), ('OK', False, False, True))

    def test_elements_an_entity_writes_have_no_source_place(self):  # Codex: the parser's position then points at the reference, not a tag
        ent = f'<!DOCTYPE html [<!ENTITY note "<ix:footnote id=&#39;n9&#39;>Via an entity.</ix:footnote>">]>'
        r = route(doc(TABLE() + NOTES() + '<p>&note;</p>', rel('f1', 'n1 n9'), before=ent))
        to = r['source_relations']['relationships'][0]['to']
        self.assertEqual([(e['ref'], e['status'], e['owners'] is None, 'extent' in e) for e in to], [('n1', 'one', False, True), ('n9', 'entity', True, False)])

    def test_another_encoding_keeps_the_bytes_and_claims_no_owner(self):
        raw = '\ufeff'.encode('utf-16-le') + doc(TABLE() + NOTES(), rel('f1', 'n1')).decode().replace('encoding="utf-8"', 'encoding="utf-16"').encode('utf-16-le')
        r = route(raw); [x] = r['source_relations']['relationships']
        self.assertEqual([(e['status'], e['owners']) for e in x['from'] + x['to']], [('one', None), ('one', None)])  # read, but the scanner cannot certify these bytes
        self.assertEqual(raw[x['at']:x['at'] + 2].decode('utf-16-le'), '<')

    def test_attributes_as_the_parser_reports_them(self):
        r = route(doc(TABLE() + NOTES(), rel('f1', 'n1', role=None), before='<!DOCTYPE html [<!ATTLIST ix:relationship order CDATA "7">]>'))
        self.assertEqual(r['source_relations']['relationships'][0]['attributes'], {'fromRefs': 'f1', 'toRefs': 'n1', 'order': '7'})  # a DTD default is the parser's value; no XBRL default is added

    def test_the_units_and_links_are_not_touched(self):
        raw = doc(TABLE() + NOTES(), rel('f1', 'n1')); r = route(raw)
        before = json.dumps({k: v for k, v in r.items() if k not in ('source_relations', 'seconds')}, sort_keys=True)
        eh.source_relations(raw, r['units'], anchor.Visible(raw))
        self.assertEqual(json.dumps({k: v for k, v in r.items() if k not in ('source_relations', 'seconds')}, sort_keys=True), before)


if __name__ == '__main__':
    unittest.main()
