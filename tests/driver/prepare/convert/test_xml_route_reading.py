"""The XML route reads one document with the grader's parser: what stands outside it is refused, markup an entity generates gets no position
(Codex's worktree cases, `test_xml_evidence.py`, on this adapter); internal entities and CDATA read as written; a UTF-16 source is read by the adapter
but the scanner certifies none of its positions, while a UTF-8 source places each character at its bytes; the batch case (an unsupported encoding fails its own file and
the batch goes on, Codex G6-1) stays with the grader's command line."""
import unittest
import xml.parsers.expat as expat

from driver.prepare.convert.xml_fields import convert, units_of
from driver.prepare.convert.anchor import Visible, sha256


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


if __name__ == '__main__':
    unittest.main()
