"""XML declaration and comments as saved extraction metadata (Root FABLE_XML_METADATA_CANDIDATE_20261023T2010). Expected values come from the
source literals (the bytes are searched in the test's own text, never read back from the parser) and from the parser's documented callback values
(standalone: 1 yes, 0 no, -1 not stated). `parser_byte_index` is the parser's event location: a literal comment's
`<!--` byte, an entity-expanded comment's reference byte (never a claimed span); comment text is XML-normalized. The body (field units and element tree) must be the same with and without the metadata."""
import copy
import hashlib
import json
import unittest
import xml.parsers.expat as expat
from pathlib import Path

from driver.prepare import reconstruct
from driver.prepare.convert import xml_fields

FIXTURES = Path(__file__).resolve().parents[1] / 'reconstruct' / 'fixtures'
SHA = lambda raw: hashlib.sha256(raw).hexdigest()


def positions(raw, texts, enc='utf-8'):
    """Byte start of each comment in source order, found in the source literal itself."""
    out, at = [], 0
    for t in texts:
        i = raw.index(('<!--' + t + '-->').encode(enc), at); out.append(i); at = i + 1
    return out


def body(raw, **kw):
    tree = []; units = xml_fields.units_of(raw, elements=tree, **kw); return units, tree


S = ('<?xml version="1.0" encoding="{enc}" standalone="yes"?>\n<!--p1--><!---->\n<r>a<!-- &amp; &#233; é -->b<c><!--  --></c>'
     '<d xmlns="urn:one"><!--n1--><e xmlns="urn:two">t<!--n2-->u</e></d></r><!--e1-->\n')
TEXTS = ['p1', '', ' &amp; &#233; é ', '  ', 'n1', 'n2', 'e1']


class XmlMetadata(unittest.TestCase):
    def check(self, raw, enc, decl_at):
        meta = {}; units, tree = body(raw, metadata=meta)
        self.assertEqual(meta['declaration'], {'version': '1.0', 'encoding': enc.upper(), 'standalone': 1, 'parser_byte_index': decl_at})
        e = {b'\xff\xfe': 'utf-16-le', b'\xfe\xff': 'utf-16-be'}.get(raw[:2], 'utf-8')  # the test's own encoding of its literal
        starts = {n: raw.index(('<' + n).encode(e)) for n in 'rcde'}; parents = [None, None, starts['r'], starts['c'], starts['d'], starts['e'], None]
        want = [{'text': t, 'parser_byte_index': b, 'parent': p} for t, b, p in zip(TEXTS, positions(raw, TEXTS, e), parents)]
        self.assertEqual(meta['comments'], want)  # every comment, source order, text verbatim (empty, white space, entity-looking strings kept)
        self.assertEqual((units, tree), body(raw))  # the body is unchanged by reading the metadata

    def test_utf8_prolog_mixed_nested_epilog_and_namespace_rebinding(self):
        self.check(S.format(enc='UTF-8').encode('utf-8'), 'UTF-8', 0)

    def test_utf16_little_and_big_endian_byte_positions(self):
        self.check(S.format(enc='UTF-16').encode('utf-16-le').join([b'\xff\xfe', b'']), 'UTF-16', 2)
        self.check(b'\xfe\xff' + S.format(enc='UTF-16').encode('utf-16-be'), 'UTF-16', 2)

    def test_declaration_absent_comments_absent_and_standalone_values(self):
        cases = {b'<r>x</r>': (None, []), b'<!--c--><r/>': (None, [{'text': 'c', 'parser_byte_index': 0, 'parent': None}]),
                 b'<?xml version="1.0"?><r/>': ({'version': '1.0', 'encoding': None, 'standalone': -1, 'parser_byte_index': 0}, []),
                 b'<?xml version="1.0" standalone="no"?><r/>': ({'version': '1.0', 'encoding': None, 'standalone': 0, 'parser_byte_index': 0}, []),
                 b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-8"?><r/>': ({'version': '1.0', 'encoding': 'UTF-8', 'standalone': -1, 'parser_byte_index': 3}, [])}
        for raw, (decl, comments) in cases.items():
            with self.subTest(raw=raw):
                meta = {}; got = body(raw, metadata=meta)
                self.assertEqual(meta, {'declaration': decl, 'comments': comments}); self.assertEqual(got, body(raw))

    def test_boundary_placement_and_doctype_subset(self):
        raw = b'<?xml version="1.0"?><!DOCTYPE r [<!--in subset--><!ELEMENT r ANY>]><!--before--><r><!--first--><x/><!--last--></r><!--after-->'
        texts = ['in subset', 'before', 'first', 'last', 'after']; r = raw.index(b'<r>')
        meta = {}; body(raw, metadata=meta)
        self.assertEqual(meta['comments'], [{'text': t, 'parser_byte_index': b, 'parent': p} for t, b, p in zip(texts, positions(raw, texts), [None, None, r, r, None])])

    def test_entity_comments_report_the_reference_byte_in_callback_order(self):
        raw = b'<!DOCTYPE r [<!ENTITY e "<!--a--><!--b-->">]><r>&e;<!--c-->&e;</r>'
        meta = {}; got = body(raw, metadata=meta); r = raw.index(b'<r>'); ref1 = raw.index(b'&e;'); ref2 = raw.index(b'&e;', ref1 + 1)
        self.assertEqual(meta['comments'], [{'text': t, 'parser_byte_index': b, 'parent': r} for t, b in (('a', ref1), ('b', ref1), ('c', raw.index(b'<!--c')), ('a', ref2), ('b', ref2))])
        self.assertEqual(got, body(raw))
        pe = b'<!DOCTYPE r [<!ENTITY % p "<!--pe-->"> %p; <!--lit-->]><r/>'; meta = {}; body(pe, metadata=meta)
        self.assertEqual(meta['comments'], [{'text': 'pe', 'parser_byte_index': pe.index(b'%p;'), 'parent': None}, {'text': 'lit', 'parser_byte_index': pe.index(b'<!--lit'), 'parent': None}])

    def test_comment_text_is_xml_normalized_not_source_bytes(self):
        for raw, want in ((b'<r><!--a\r\nb\rc\nd--></r>', 'a\nb\nc\nd'), ('<r><!--x\r\ny--></r>'.encode('utf-16'), 'x\ny')):
            with self.subTest(raw=raw):
                meta = {}; body(raw, metadata=meta); e = 'utf-16-le' if raw[:2] == b'\xff\xfe' else 'utf-8'
                self.assertEqual(meta['comments'], [{'text': want, 'parser_byte_index': raw.index('<!--'.encode(e)), 'parent': raw.index('<r>'.encode(e))}])

    def test_existing_entity_and_external_refusals_unchanged(self):
        for raw in (b'<!DOCTYPE r [<!ENTITY e SYSTEM "x.xml">]><r>&e;</r>', b'<!DOCTYPE r [<!ENTITY e "<x>t</x>">]><r>&e;</r>', b'<r><!--open</r>'):
            with self.subTest(raw=raw):
                with self.assertRaises(expat.ExpatError): body(raw, metadata={})
                with self.assertRaises(expat.ExpatError): body(raw)

    def test_convert_saves_metadata_beside_the_body_and_failed_has_none(self):
        raw = S.format(enc='UTF-8').encode('utf-8'); doc = xml_fields.convert(raw, 'f', SHA(raw)); units, tree = body(raw)
        self.assertEqual((doc['status'], doc['units'], doc['xml_elements']), ('OK', units, tree))
        meta = {}; body(raw, metadata=meta); self.assertEqual(doc['xml_metadata'], meta)
        bad = b'<r><!--x--><r>'; doc = xml_fields.convert(bad, 'f', SHA(bad))
        self.assertEqual((doc['status'], 'xml_metadata' in doc, 'xml_elements' in doc), ('FAILED', False, False))


class ReadbackKeepsMetadata(unittest.TestCase):
    def test_new_route_carries_metadata_and_states_only_uncaptured_categories(self):
        raw = S.format(enc='UTF-8').encode('utf-8'); route = xml_fields.convert(raw, 'f', SHA(raw)); R = reconstruct.readback(route)
        self.assertEqual(R['not_composed']['xml_metadata'], route['xml_metadata'])
        self.assertEqual(R['xml']['not_represented'], ['processing_instructions', 'doctype', 'source_spelling'])
        self.assertEqual(reconstruct.preserved(route, R), [])
        self.assertEqual(reconstruct.annotations(route, R), [])
        changed = copy.deepcopy(R); changed['not_composed']['xml_metadata']['comments'][0]['text'] = 'other'
        self.assertNotEqual(reconstruct.preserved(route, changed), [])  # a changed comment is caught by the readback equality

    def test_legacy_and_malformed_metadata_keep_the_full_warning(self):
        legacy = json.loads((FIXTURES / 'x1_structure.json').read_text())['route']
        self.assertNotIn('xml_metadata', legacy)
        self.assertEqual(reconstruct.readback(legacy)['xml']['not_represented'], list(reconstruct.NOT_REPRESENTED_XML))
        for bad in ([], {'comments': []}, {'declaration': None, 'comments': {}}, None):
            with self.subTest(bad=bad):
                route = dict(legacy, xml_metadata=bad); R = reconstruct.readback(route)
                self.assertEqual(R['xml']['not_represented'], list(reconstruct.NOT_REPRESENTED_XML)); self.assertEqual(reconstruct.preserved(route, R), [])


if __name__ == '__main__':
    unittest.main()
