"""Filed per-fact attributes survive separately from the native scaled value.

The current adapter dumps only Document.root; EdgarTools 5.60 stores facts on
Document.metadata instead. These small source statements are independent
expectations, including two identical printed numbers with different scales.
"""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from driver.prepare.convert import edgartools_html as eh
from driver.prepare import reconstruct


def route(body):
    raw = ('<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body>' + body + '</body></html>').encode()
    return raw, eh.convert(raw, 'own.htm', hashlib.sha256(raw).hexdigest())


class InlineFactMetadata(unittest.TestCase):
    def test_same_printed_number_keeps_its_own_scale_and_source_tag(self):
        body = ('<table><tr><td><ix:nonFraction name="x:Money" contextRef="c" '
                'unitRef="u" scale="6" decimals="-6">125</ix:nonFraction></td>'
                '<td><ix:nonFraction name="x:Shares" contextRef="c" '
                'unitRef="shares" scale="3">125</ix:nonFraction></td></tr></table>')
        raw, r = route(body)
        facts = r['source_facts']
        self.assertTrue(facts['read'], facts)
        a, b = facts['records']
        self.assertEqual((a['native']['value'], b['native']['value']), ('125000000', '125000'))
        self.assertEqual((a['native']['scale'], b['native']['scale']), ('6', '3'))
        self.assertEqual(a['native']['decimals'], '-6')
        self.assertEqual(a['native']['unit_ref'], 'u')
        self.assertEqual(a['native']['context_ref'], 'c')
        for rec, name in zip((a, b), (b'x:Money', b'x:Shares')):
            tag = raw[rec['source_tag']['byte_start']:rec['source_tag']['byte_end_exclusive']]
            self.assertIn(name, tag)
            self.assertEqual(rec['element_text'], '125')
        self.assertNotEqual(a['source_tag'], b['source_tag'])
        self.assertEqual([c['text'] for c in r['units'][0]['cells']], ['125', '125'])

    def test_absent_scale_stays_absent_and_zero_and_negative_are_distinct(self):
        for attr, want, value in [('', None, '7'), (' scale="0"', '0', '7'),
                                  (' scale="-3"', '-3', '0.007')]:
            with self.subTest(attr=attr):
                _, r = route('<p><ix:nonFraction name="x:N"' + attr + '>7</ix:nonFraction></p>')
                f = r['source_facts']['records'][0]
                self.assertEqual((f['native']['scale'], f['native']['value']), (want, value))
                self.assertEqual('scale' in f['attributes'], bool(attr))

    def test_native_lexical_precision_sign_and_format_issue_are_preserved(self):
        _, r = route('<p><ix:nonFraction name="x:N" scale="3" sign="-" '
                     'format="unsupported:format">9007199254740993</ix:nonFraction></p>')
        f = r['source_facts']['records'][0]
        self.assertEqual(f['native']['value'], '-9007199254740993000')
        self.assertEqual(f['element_text'], '9007199254740993')
        self.assertEqual(f['native']['sign'], '-')
        self.assertIn('format_issue', f['native']['metadata'])
        self.assertNotIn('numeric_value', f['native'])  # no float conversion

    def test_hidden_and_non_numeric_facts_keep_native_metadata(self):
        _, r = route('<ix:header><ix:hidden><ix:nonFraction name="x:H" scale="6">2</ix:nonFraction>'
                     '</ix:hidden></ix:header><p><ix:nonNumeric name="x:Note" continuedAt="tail">First</ix:nonNumeric>'
                     '</p><ix:continuation id="tail">last</ix:continuation>')
        a, b = r['source_facts']['records']
        self.assertEqual(a['native']['value'], '2000000')
        self.assertTrue(a['native']['metadata']['hidden'])
        self.assertEqual(b['native']['continued_at'], 'tail')
        self.assertEqual(b['native']['value'], 'First last')
        self.assertEqual(len(r['source_facts']['records']), 2)  # continuation is not a fact

    def test_no_facts_is_not_a_scale_assignment(self):
        _, r = route('<p>All amounts in millions.</p><table><tr><td>125</td></tr></table>')
        self.assertEqual(r['source_facts'], {'read': True, 'records': []})
        self.assertNotIn('scale', r['units'][-1]['cells'][0])

    def test_failure_is_unread_not_empty_success(self):
        from edgar.documents.strategies.xbrl_extraction import XBRLExtractor
        with patch.object(XBRLExtractor, 'extract_fact', side_effect=ValueError('fact failed')):
            _, r = route('<p><ix:nonFraction name="x:N" scale="6">125</ix:nonFraction></p>')
        self.assertFalse(r['source_facts']['read'])
        self.assertIn('fact failed', r['source_facts']['error'])
        self.assertEqual(r['status'], 'OK')  # adaptation succeeded; html_route reports the unread family after the other steps

    def test_saved_readback_carries_the_exact_metadata(self):
        _, r = route('<p><ix:nonFraction name="x:N" scale="6">125</ix:nonFraction></p>')
        saved = json.loads(json.dumps(reconstruct.readback(r)))
        inverse = reconstruct.inverse(saved)
        self.assertEqual(inverse['source_facts'], r['source_facts'])
        self.assertIn('source_facts', inverse)
        self.assertEqual(reconstruct.preserved(r, saved), [])
        for key in ('source_tag', 'attributes', 'native_element', 'native'):
            damaged = copy.deepcopy(saved)
            del damaged['not_composed']['source_facts']['records'][0][key]
            self.assertTrue(reconstruct.preserved(r, damaged), key)

    def test_full_route_reports_unread_metadata_after_preserving_independent_body_work(self):
        from driver.prepare.convert import html_route, screen_grid
        from edgar.documents.strategies.xbrl_extraction import XBRLExtractor
        from tests.driver.prepare.convert.test_html_route import shown
        raw = b'<p xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><ix:nonFraction name="x:N" scale="6">7</ix:nonFraction></p>'
        with patch.object(screen_grid, 'measure', return_value=({}, {}, shown(raw))):
            positive, positive_facts = html_route.prepare(raw, 'own.htm', hashlib.sha256(raw).hexdigest(), object())
        self.assertEqual(positive['status'], 'OK')
        self.assertEqual(positive['source_facts']['records'][0]['native']['value'], '7000000')
        with patch.object(screen_grid, 'measure', return_value=({}, {}, shown(raw))), \
             patch.object(XBRLExtractor, 'extract_fact', side_effect=ValueError('fact failed')):
            negative, facts = html_route.prepare(raw, 'own.htm', hashlib.sha256(raw).hexdigest(), object())
        self.assertEqual(negative['status'], 'PARTIAL')
        self.assertIn('inline XBRL: ValueError: fact failed', negative['error'])
        self.assertEqual(negative['units'], positive['units'])
        self.assertIn('screen', facts)
        self.assertIs(negative['text_proved'], False)

    def test_context_and_unit_are_native_resolutions_not_defaults(self):
        _, r = route('<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="own">123</xbrli:identifier>'
                     '</xbrli:entity><xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>'
                     '<xbrli:unit id="u"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
                     '<p><ix:nonFraction name="x:N" contextRef="c" unitRef="u" scale="6">1</ix:nonFraction></p>')
        f = r['source_facts']['records'][0]['native']
        self.assertEqual(f['unit'], 'USD')  # native representation; the filed unitRef remains "u"
        self.assertEqual(f['context']['instant'], '2025-12-31')
        self.assertEqual(f['context']['period_type'], 'instant')

    def test_hidden_source_reading_keeps_its_own_unread_metadata_visible(self):
        from driver.prepare.convert import html_route
        from edgar.documents.strategies.xbrl_extraction import XBRLExtractor
        raw = b'<html xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><body><p>Body</p><div style="display:none"><ix:nonFraction name="x:N" scale="6">7</ix:nonFraction></div></body></html>'
        pin = hashlib.sha256(raw).hexdigest()
        positive, _ = html_route.source_reading(raw, 'own.htm', pin, {'sha256': pin})
        self.assertEqual(positive['status'], 'OK')
        self.assertEqual(positive['source_facts']['records'][0]['native']['value'], '7000000')
        with patch.object(XBRLExtractor, 'extract_fact', side_effect=ValueError('fact failed')):
            negative, _ = html_route.source_reading(raw, 'own.htm', pin, {'sha256': pin})
        self.assertEqual(negative['status'], 'PARTIAL')
        self.assertIn('inline XBRL: ValueError: fact failed', negative['error'])
        self.assertEqual(negative['units'], positive['units'])

    def test_fact_like_text_in_comments_scripts_and_raw_text_is_not_a_fact(self):
        fake = '<ix:nonFraction name="x:Fake" scale="6">7</ix:nonFraction>'
        for body in ('<!--' + fake + '--><p>Real</p>', '<script>"' + fake + '"</script><p>Real</p>',
                     '<textarea>' + fake + '</textarea>', '<xmp>' + fake + '</xmp>'):
            with self.subTest(body=body): self.assertEqual(route(body)[1]['source_facts'], {'read': True, 'records': []})

    def test_actual_namespace_decides_not_the_prefix(self):
        _, r = route('<p xmlns:other="http://www.xbrl.org/2013/inlineXBRL">'
                     '<other:nonFraction name="x:N" scale="6">7</other:nonFraction></p>')
        self.assertTrue(r['source_facts']['read'])
        self.assertEqual(r['source_facts']['records'][0]['native']['value'], '7000000')
        _, other = route('<p xmlns:ix="urn:not-inline-xbrl"><ix:nonFraction name="x:N" scale="6">7</ix:nonFraction></p>')
        self.assertEqual(other['source_facts'], {'read': True, 'records': []})
        _, missing = route('<p><other:nonFraction name="x:N" scale="6">7</other:nonFraction></p>')
        self.assertFalse(missing['source_facts']['read'])
        self.assertIn('namespace is unbound', missing['source_facts']['error'])
        for ns in ('http://www.xbrl.org/2008/inlineXBRL', 'http://www.xbrl.org/2013/inlineXBRL'):
            for tag, declaration in [('q:nonFraction', 'xmlns:q'), ('nonFraction', 'xmlns')]:
                with self.subTest(namespace=ns, tag=tag):
                    _, bound = route('<' + tag + ' ' + declaration + '="' + ns + '" name="x:N" scale="3">7</' + tag + '>')
                    f, = bound['source_facts']['records']
                    self.assertEqual((f['namespace'], f['native']['value']), (ns, '7000'))

    def test_byte_address_is_not_character_offset_and_duplicate_ids_do_not_join(self):
        raw, r = route('<p>é <ix:nonFraction id="same" name="x:N" scale="3">7</ix:nonFraction> '
                       '<ix:nonFraction id="same" name="x:N" scale="6">7</ix:nonFraction></p>')
        a, b = r['source_facts']['records']
        self.assertEqual(a['source_tag']['byte_start'], raw.index(b'<ix:nonFraction'))
        self.assertNotEqual(a['source_tag'], b['source_tag'])
        self.assertEqual((a['native']['value'], b['native']['value']), ('7000', '7000000'))

    def test_resources_propagate_and_old_parse_never_claims_no_facts(self):
        from edgar.documents.strategies.xbrl_extraction import XBRLExtractor
        for exc in (MemoryError('memory'), OSError('disk'), ImportError('dependency')):
            with self.subTest(exc=type(exc).__name__), patch.object(XBRLExtractor, 'extract_fact', side_effect=exc):
                with self.assertRaises(type(exc)): route('<p><ix:nonFraction name="x:N">7</ix:nonFraction></p>')
        raw = b'<p>7</p>'
        r = eh.convert(raw, 'own.htm', hashlib.sha256(raw).hexdigest(),
                       parse=lambda raw, vis: ({'type': 'TextNode', 'text': '7'}, 0, 'old'))
        self.assertNotIn('source_facts', r)
        self.assertIn('inline_xbrl', eh.SETTINGS)

    def test_native_parser_wrapped_resource_failure_still_stops_the_caller(self):
        from edgar.documents.parser import HTMLParser
        raw = b'<p xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><ix:nonFraction name="x:N">7</ix:nonFraction></p>'
        self.assertTrue(eh.inline_facts(raw, HTMLParser())['read'])
        for exc in (MemoryError('memory'), OSError('disk'), ImportError('dependency')):
            with self.subTest(exc=type(exc).__name__), patch('edgar.documents.parser.lxml.html.fromstring', side_effect=exc):
                with self.assertRaises(type(exc)): eh.inline_facts(raw, HTMLParser())

    def test_unsupported_byte_tokenization_never_proves_an_empty_inventory(self):
        from edgar.documents.parser import HTMLParser
        text = '<p xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><ix:nonFraction name="x:N">7</ix:nonFraction></p>'
        self.assertTrue(eh.inline_facts(text.encode(), HTMLParser())['read'])
        for encoding in ('utf-16', 'utf-32'):
            with self.subTest(encoding=encoding):
                self.assertFalse(eh.inline_facts(text.encode(encoding), HTMLParser())['read'])

    def test_lost_or_duplicated_native_source_identity_never_matches_by_number(self):
        from edgar.documents.parser import HTMLParser
        raw = b'<p xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"><ix:nonFraction name="x:A" scale="3">7</ix:nonFraction> <ix:nonFraction name="x:B" scale="6">7</ix:nonFraction></p>'
        parser = HTMLParser()
        original = parser._parse_html
        def damaged(text, duplicate):
            tree = original(text)
            facts = [e for e in tree.iter() if isinstance(e.tag, str) and e.tag == 'ix:nonfraction']
            key = next(k for k in facts[0].attrib if k.startswith('data-prepare-fact-'))
            if duplicate: facts[1].set(key, facts[0].get(key))
            else: del facts[1].attrib[key]
            return tree
        self.assertTrue(eh.inline_facts(raw, parser)['read'])
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate), patch.object(parser, '_parse_html', side_effect=lambda text: damaged(text, duplicate)):
                result = eh.inline_facts(raw, parser)
                self.assertFalse(result['read'])
                self.assertIn('identity', result['error'])

    def test_mixed_per_share_unit_and_dashes_keep_their_own_attributes(self):
        _, r = route('<xbrli:unit id="eps"><xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:USD</xbrli:measure>'
                     '</xbrli:unitNumerator><xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure>'
                     '</xbrli:unitDenominator></xbrli:divide></xbrli:unit>'
                     '<table><tr><td><ix:nonFraction name="x:EPS" unitRef="eps" decimals="2">1.25</ix:nonFraction></td>'
                     '<td><ix:nonFraction name="x:Zero" format="ixt:zerodash">-</ix:nonFraction></td></tr></table>')
        a, b = r['source_facts']['records']
        self.assertEqual((a['native']['value'], a['native']['unit'], a['native']['scale']), ('1.25', 'USD/shares', None))
        self.assertEqual((b['element_text'], b['native']['format']), ('-', 'ixt:zerodash'))
        table, = [u for u in r['units'] if u['kind'] == 'table']
        self.assertEqual([c['text'] for c in table['cells']], ['1.25', '-'])

    def test_native_element_kind_and_fraction_components_are_not_flattened(self):
        _, r = route('<p><ix:fraction name="x:Ratio"><ix:numerator>2</ix:numerator>'
                     '<ix:denominator>3</ix:denominator></ix:fraction></p>')
        f, = r['source_facts']['records']
        self.assertEqual(f['native_element'], {'type': 'fraction', 'name': 'x:Ratio', 'numerator': '2', 'denominator': '3'})
        self.assertEqual(f['element_text'], '23')  # concatenated text is not the fraction's numeric meaning
        saved = json.loads(json.dumps(reconstruct.readback(r)))
        self.assertEqual(reconstruct.inverse(saved)['source_facts'], r['source_facts'])
        for key in ('type', 'numerator', 'denominator'):
            bad = copy.deepcopy(saved)
            del bad['not_composed']['source_facts']['records'][0]['native_element'][key]
            self.assertTrue(reconstruct.preserved(r, bad), key)

    def test_native_element_kind_keeps_numeric_and_non_numeric_distinct(self):
        _, r = route('<p><ix:nonFraction name="x:A">7</ix:nonFraction>'
                     '<ix:nonNumeric name="x:B">7</ix:nonNumeric></p>')
        self.assertEqual([f['native_element']['type'] for f in r['source_facts']['records']], ['nonFraction', 'nonNumeric'])

    def test_fraction_components_the_native_reader_cannot_qualify_stay_unread(self):
        # The native fraction lookup requires its own ix: child spelling; it
        # does not resolve an aliased child here, unlike the nonFraction path.
        # No new child parser or a concatenated-text numeric fallback.
        for body in ('<q:fraction name="x:R"><q:numerator>2</q:numerator><q:denominator>3</q:denominator></q:fraction>',
                     '<ix:fraction name="x:R"><ix:numerator>2</ix:numerator></ix:fraction>'):
            with self.subTest(body=body):
                _, r = route('<p xmlns:q="http://www.xbrl.org/2013/inlineXBRL">' + body + '</p>')
                self.assertFalse(r['source_facts']['read'])
                self.assertIn('fraction components not read', r['source_facts']['error'])

    def test_later_native_failure_keeps_earlier_complete_fact_records(self):
        from edgar.documents.strategies.xbrl_extraction import XBRLExtractor
        body = '<p><ix:nonFraction name="x:A">7</ix:nonFraction><ix:nonFraction name="x:B">8</ix:nonFraction></p>'
        _, positive = route(body)
        self.assertTrue(positive['source_facts']['read'])
        original = XBRLExtractor.extract_fact
        def failed(reader, element):
            if element.get('name') == 'x:B': raise ValueError('second fact unread')
            return original(reader, element)
        with patch.object(XBRLExtractor, 'extract_fact', failed):
            _, negative = route(body)
        self.assertFalse(negative['source_facts']['read'])
        self.assertEqual(negative['source_facts']['records'], positive['source_facts']['records'][:1])


if __name__ == '__main__': unittest.main()
