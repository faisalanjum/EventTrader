"""The XML route reads one document with the grader's parser: what stands outside it is refused, markup an entity generates gets no position
(Codex's worktree cases, `test_xml_evidence.py`, on this adapter); internal entities and CDATA read as written; a UTF-16 source is read by the adapter
but the scanner certifies none of its positions, while a UTF-8 source places each character at its bytes; the batch case (an unsupported encoding fails its own file and
the batch goes on, Codex G6-1) stays with the grader's command line. The element tree (`xml_elements`) is the standard library's own tree
of the same bytes, every element at its own start tag, and the units do not change with it (the parked worktree test, ported; root's three
ambiguity pairs, post_font_scope_20261008/ROOT_XML_AMBIGUITY.json)."""
import io
import unittest
import xml.etree.ElementTree as ET
import xml.parsers.expat as expat

from driver.prepare.convert.xml_fields import convert, units_of
from driver.prepare.convert.anchor import Visible, sha256

STRUCTURE = ('<?xml version="1.0" encoding="ENC"?><r xmlns="urn:a" xmlns:u="urn:unit" x="A &amp; B" e="">'
             '<holding u:amount="10" unit="shares"/><scope xmlns="urn:b"><n>5</n><n>6</n><none xmlns=""/></scope>'
             '<note>not <b>zero</b>, <!--c-->a&amp;b<![CDATA[ <c> ]]><?pi x?>.\n</note><t xmlns:u="urn:other" u:k=" a\tb " w="&#10;"/></r>')
SOURCES = [STRUCTURE.replace('ENC', 'UTF-8').encode(), b'<p>Revenue was <v>10</v> in 2024 and <v>10</v> in 2025.</p>',
           b'<!DOCTYPE r [<!ENTITY unit "shares"><!ATTLIST r d CDATA "declared">]><r><n unit="&unit;">5 &unit;</n><e></e><e/></r>']


def oracle(raw):
    """ElementTree's reading: per element in document order, its name, attributes, the bindings declared on it and its direct content."""
    nodes, pending = [], {}
    for event, x in ET.iterparse(io.BytesIO(raw), events=('start-ns', 'start')):
        if event == 'start-ns': pending[x[0]] = x[1]
        else: nodes.append((x, dict(pending))); pending.clear()
    at = {id(e): i for i, (e, _) in enumerate(nodes)}
    return [(e.tag, e.attrib, ns, ([e.text] if e.text else []) + [y for c in e for y in [('child', at[id(c)])] + ([c.tail] if c.tail else [])]) for e, ns in nodes]


def tree(raw):
    elements = []; units_of(raw, {}, elements=elements); at = {e['anchor']['byte_start']: i for i, e in enumerate(elements)}
    return elements, [(e['name'], e.get('attributes', {}), e.get('namespaces', {}), [('child', at[x['child']]) if isinstance(x, dict) else x for x in e.get('content', [])]) for e in elements]


class XmlRouteReading(unittest.TestCase):
    def test_external_content_is_refused_not_read_as_an_empty_success(self):
        for raw in (b'<!DOCTYPE r [<!ENTITY x SYSTEM "file:///does-not-exist">]><r>&x;</r>',
                    b'<!DOCTYPE r SYSTEM "https://invalid.example/external.dtd"><r>5</r>',
                    b'<!DOCTYPE r [<!ENTITY % x SYSTEM "file:///does-not-exist">%x;]><r>5</r>'):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(expat.ExpatError, 'external'): units_of(raw, {})
                view = Visible(raw, xml=True); self.assertEqual((view.certain, view.text), (False, ''))

    def test_internal_entities_and_literal_cdata_are_read_as_written(self):
        raw = b'<!DOCTYPE r [<!ENTITY unit "shares">]><r><n unit="&unit;">5 &unit;</n><p><![CDATA[not < zero]]></p></r>'
        self.assertEqual([u['text'] for u in units_of(raw, {})], ['5 shares', 'not < zero'])

    def test_markup_generated_by_an_entity_is_refused_not_placed_at_an_empty_span(self):
        raw = b'<!DOCTYPE r [<!ENTITY holding "<h unit=\'shares\'>5</h>">]><r>&holding;</r>'
        with self.assertRaisesRegex(expat.ExpatError, 'source position'): units_of(raw, {})
        view = Visible(raw, xml=True); self.assertEqual((view.certain, view.text), (False, ''))
        self.assertEqual([u['anchor'] for u in units_of(b'<r><a/><b>1</b><c></c></r>', {})], [{'byte_start': 7, 'byte_end_exclusive': 11}])  # an empty element is no such case

    def test_a_utf16_source_is_not_certified_and_a_utf8_one_places_each_character_at_its_bytes(self):  # the worktree asked for UTF-16 positions; since round 18 a character is placed at its own bytes or not at all
        for encoding, declaration in (('utf-16-le', 'UTF-16LE'), ('utf-16-be', 'UTF-16BE')):
            raw = f'<?xml version="1.0" encoding="{declaration}"?><r>\u20aca</r>'.encode(encoding)
            view = Visible(raw, xml=True); self.assertEqual((view.certain, view.text), (False, ''))
            self.assertEqual([u['text'] for u in units_of(raw, {})], ['\u20aca'])  # the route still reads it; the grader certifies nothing of it
        raw = '<?xml version="1.0" encoding="UTF-8"?><r>\u20aca</r>'.encode(); view = Visible(raw, xml=True); self.assertEqual((view.certain, view.text), (True, '\u20aca'))
        self.assertEqual([raw[a:b].decode() for a, b in zip(view.starts, view.ends)], ['\u20ac', 'a'])

    def test_a_document_that_does_not_parse_is_a_failed_route_not_a_stop(self):  # Codex G6-1 on the one-document call (the batch case stays with the grader's command line)
        for encoding in ('not-a-real-encoding', 'UTF-32', 'utf-7', 'shift_jis'):
            with self.subTest(encoding=encoding):
                raw = ('<?xml version="1.0" encoding="%s"?><r>1</r>' % encoding).encode()
                doc = convert(raw, 'first.xml', sha256(raw))
                self.assertEqual((doc['status'], doc['units'], doc['error'].startswith('XML parse failed')), ('FAILED', [], True))
        raw = b'<?xml version="1.0" encoding="UTF-8"?><r><n>2</n></r>'
        doc = convert(raw, 'second.xml', sha256(raw))
        self.assertEqual((doc['status'], [u['text'] for u in doc['units']], doc['route']['adapter']), ('OK', ['2'], 'driver/prepare/convert/xml_fields.py'))


class XmlElementTree(unittest.TestCase):
    def test_the_tree_is_the_standard_librarys_own_reading_with_every_element_at_its_start_tag(self):
        for encoding, declaration in (('utf-8', 'UTF-8'), ('utf-16-le', 'UTF-16LE'), ('utf-16-be', 'UTF-16BE')):
            with self.subTest(encoding=encoding):
                raw = STRUCTURE.replace('ENC', declaration).encode(encoding); elements, got = tree(raw)
                self.assertEqual(got, oracle(raw))
                self.assertEqual([e['parent'] for e in elements if not any(x == {'child': e['anchor']['byte_start']} for p in elements for x in p.get('content', []))], [None])  # only the root stands in no content
                self.assertEqual({(x['child'], p['anchor']['byte_start']) for p in elements for x in p.get('content', []) if isinstance(x, dict)}, {(e['anchor']['byte_start'], e['parent']) for e in elements if e['parent'] is not None})
                by = {e['anchor']['byte_start']: e for e in elements}
                for e in elements:
                    a, b = e['anchor']['byte_start'], e['anchor']['byte_end_exclusive']; local = e['name'].rsplit('}', 1)[-1]
                    self.assertTrue(raw[a:].decode(encoding).startswith('<' + local) and (raw[b:].decode(encoding).startswith('</') or raw[a:b].decode(encoding).endswith('/>')))
                    if e['parent'] is not None: self.assertTrue(by[e['parent']]['anchor']['byte_start'] < a < b <= by[e['parent']]['anchor']['byte_end_exclusive'])
        for raw in SOURCES[1:]: self.assertEqual(tree(raw)[1], oracle(raw))
        got = {e['name']: e for e in tree(SOURCES[0])[0]}  # values as the parser gives them: references replaced, white space normalized, an empty value kept
        self.assertEqual((got['{urn:a}r']['attributes'], got['{urn:a}t']['attributes'], got['{urn:a}t']['namespaces'], got['none']['namespaces']),
                         ({'x': 'A & B', 'e': ''}, {'{urn:other}k': ' a b ', 'w': '\n'}, {'u': 'urn:other'}, {'': ''}))
        self.assertEqual(got['{urn:a}note']['content'][2], ', a&b <c> .\n')  # one run: the comment and the instruction are not kept, CDATA is text
        self.assertEqual(tree(SOURCES[2])[0][0]['attributes'], {'d': 'declared'})  # a default the document's own DTD declares

    def test_root_ambiguity_pairs_differ_in_the_tree_while_their_units_stay_equal(self):
        pairs = [(b'<r><context id="c1"><period>2024</period></context><context id="c2"><period>2025</period></context><profit contextRef="c1" unitRef="USD">10</profit><profit contextRef="c2" unitRef="EUR">10</profit></r>',
                  b'<r><context id="c1"><period>2024</period></context><context id="c2"><period>2025</period></context><profit contextRef="c2" unitRef="EUR">10</profit><profit contextRef="c1" unitRef="USD">10</profit></r>'),
                 (b'<disclosure><waived/></disclosure>', b'<disclosure><denied/></disclosure>'),
                 (b'<r xmlns:p="urn:AAA"><member ref="p:item"/></r>', b'<r xmlns:p="urn:BBB"><member ref="p:item"/></r>')]
        for one, other in pairs:
            with self.subTest(one=one):
                self.assertEqual(units_of(one, {}), units_of(other, {}))
                self.assertNotEqual(tree(one)[1], tree(other)[1])
        self.assertEqual([e['attributes'] for e in tree(pairs[0][0])[0] if e['name'] == 'profit'], [{'contextRef': 'c1', 'unitRef': 'USD'}, {'contextRef': 'c2', 'unitRef': 'EUR'}])
        self.assertEqual([e['name'] for e in tree(pairs[1][1])[0]], ['disclosure', 'denied'])
        self.assertEqual([(e.get('namespaces'), e.get('attributes')) for e in tree(pairs[2][1])[0]], [({'p': 'urn:BBB'}, None), (None, {'ref': 'p:item'})])

    def test_each_repeated_child_keeps_its_own_place_in_mixed_content(self):
        raw = SOURCES[1]; elements, _ = tree(raw); units = units_of(raw, {})
        v = [u['anchor']['byte_start'] for u in units if u['name'] == 'v']
        self.assertEqual(elements[0]['content'], ['Revenue was ', {'child': v[0]}, ' in 2024 and ', {'child': v[1]}, ' in 2025.'])

    def test_the_units_and_the_old_call_do_not_change_and_kept_attributes_are_not_unread(self):
        for raw in SOURCES:
            with self.subTest(raw=raw[:30]):
                old, new = {}, {}; units = units_of(raw, old)
                self.assertEqual(units_of(raw, new, elements=[]), units); self.assertEqual(new, {'attribute_values': 0})
                doc = convert(raw, 'x.xml', sha256(raw))
                self.assertEqual((doc['units'], 'not_read' in doc, len(doc['xml_elements'])), (units, False, len(tree(raw)[0])))
        self.assertEqual(old, {'attribute_values': 2})  # the call without a tree still counts what it leaves unread (non-blank values)

    def test_no_tree_is_given_for_a_document_that_does_not_parse_completely(self):
        for raw in (b'<r><a x="1"><b>2</b>', b'<r>1</r><r>2</r>', b'<!DOCTYPE r [<!ENTITY x SYSTEM "file:///does-not-exist">]><r>&x;</r>',
                    b'<!DOCTYPE r [<!ENTITY holding "<h unit=\'shares\'>5</h>">]><r>&holding;</r>'):
            with self.subTest(raw=raw):
                elements = []
                with self.assertRaises(expat.ExpatError): units_of(raw, {}, elements=elements)
                doc = convert(raw, 'x.xml', sha256(raw))
                self.assertEqual((elements, doc['status'], 'xml_elements' in doc), ([], 'FAILED', False))


if __name__ == '__main__':
    unittest.main()
