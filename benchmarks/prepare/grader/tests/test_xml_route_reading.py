"""The XML route reads one document with the grader's parser: what stands outside it is refused, markup an entity generates gets no position
(Codex's worktree cases, `test_xml_evidence.py`, on this adapter); internal entities and CDATA read as written; a UTF-16 source is read by the adapter
but the scanner certifies none of its positions, while a UTF-8 source places each character at its bytes; an unsupported encoding fails its own file and
the batch goes on (Codex G6-1)."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
import xml.parsers.expat as expat
from pathlib import Path
from unittest.mock import patch

from benchmarks.prepare.grader import grade
from benchmarks.prepare.grader.adapters import xml_fields
from benchmarks.prepare.grader.adapters.xml_fields import units_of
from benchmarks.prepare.grader.anchor import Visible


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

    def test_an_unsupported_encoding_fails_its_own_file_and_the_batch_goes_on(self):  # Codex G6-1: expat raises ValueError or LookupError there, not ExpatError
        for encoding in ('not-a-real-encoding', 'UTF-32', 'utf-7', 'shift_jis'):
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as td:
                folder = Path(td); first, second = folder / 'first.xml', folder / 'second.xml'
                first.write_bytes(('<?xml version="1.0" encoding="%s"?><r>1</r>' % encoding).encode()); second.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?><r><n>2</n></r>')
                sources = [dict(file_id=p.name, path=p, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), split='development') for p in (first, second)]
                with patch.object(grade, 'load_sources', return_value=sources), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(xml_fields.main(['--key', 'unused', '--split', 'development', '--out', str(folder / 'out')]), 0)
                failed, good = (json.loads((folder / 'out/route' / n).read_text()) for n in ('first.xml.json', 'second.xml.json'))
                self.assertEqual((failed['status'], failed['units'], bool(failed['error'])), ('FAILED', [], True))
                self.assertEqual((good['status'], [u['text'] for u in good['units']]), ('OK', ['2']))
                self.assertEqual(len(json.loads((folder / 'out/facts.json').read_text())['files']), 2)


if __name__ == '__main__':
    unittest.main()
