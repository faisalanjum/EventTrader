"""A native cached style belongs to its source, not to a later element or document."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[4]
PROBE = r'''
from dataclasses import asdict
import json, sys
from lxml.html import fromstring
from edgar.documents.config import ParserConfig
from edgar.documents.strategies.document_builder import DocumentBuilder
from edgar.documents.strategies.style_parser import StyleParser
from edgar.documents.utils import get_cache_manager
from driver.prepare.convert import anchor, edgartools_html as eh

case = sys.argv[1]
cache = get_cache_manager().style_cache
style = 'font-size:12px'
builder = lambda: DocumentBuilder(ParserConfig(), {})
element = lambda tag='p', extra='': fromstring(f'<{tag} style="{style}"{extra}>Words</{tag}>')

if case == 'preloaded':
    builder()._extract_style(element('p', ' align="center"'))
    assert StyleParser().parse(style).text_align == 'center'  # real dirty native cache, before setup

eh.whole_headings()
if case.startswith('semantic:'):
    tag, extra, field, value = {
        'bold': ('strong', '', 'font_weight', 'bold'),
        'italic': ('em', '', 'font_style', 'italic'),
        'underline': ('u', '', 'text_decoration', 'underline'),
        'align': ('p', ' align="center"', 'text_align', 'center'),
    }[case.split(':')[1]]
    first = builder()._extract_style(element()); before = asdict(first)
    changed = builder()._extract_style(element(tag, extra))
    later = builder()._extract_style(element())
    assert getattr(changed, field) == value, (field, asdict(changed))  # keep the real tag's style
    assert asdict(first) == before, ('earlier element changed', field, asdict(first))
    assert asdict(later) == before, ('later element polluted', field, asdict(later))
elif case == 'cache':
    first = StyleParser().parse(style); before = asdict(first)
    first.font_weight = '700'
    second = StyleParser().parse(style)
    assert asdict(second) == before, 'the cache miss returned its stored mutable value'
    second.text_align = 'right'
    assert asdict(StyleParser().parse(style)) == before, 'the cache hit returned its stored mutable value'
    explicit = StyleParser().parse('font-size:12px;font-weight:normal;text-align:left')
    assert (explicit.font_weight, explicit.text_align) == ('400', 'left')
    empty = StyleParser().parse(''); empty.text_align = 'center'
    assert StyleParser().parse('').text_align is None
elif case == 'preloaded':
    assert StyleParser().parse(style).text_align is None, 'pre-setup polluted entries survived'
elif case == 'idempotent':
    parser = StyleParser.parse
    cached = StyleParser().parse(style)
    stored = cache.get(style)
    eh.whole_headings()
    assert StyleParser.parse is parser and cache.get(style) is stored, 'setup ran again'
    cached.text_align = 'center'
    assert StyleParser().parse(style).text_align is None
elif case in ('within', 'order'):
    def route(body):
        raw = ('<!doctype html><html><body>' + body + '</body></html>').encode()
        result = eh.convert(raw, 'case.htm', anchor.sha256(raw))
        assert result['status'] == 'OK', result
        return result
    def heading_styles(result):
        return {u['text']:u['native_heading']['style'] for u in result['units'] if u.get('native_heading')}
    head = '<h2 style="font-size:12px">Stable heading</h2>'
    polluter = '<p style="font-size:12px" align="center">Other paragraph.</p>'
    if case == 'within':
        result = route(head + polluter + head.replace('Stable', 'Later'))
        found = heading_styles(result)
        assert found['Stable heading']['text_align'] is None and found['Later heading']['text_align'] is None, found
        assert all(t in ' '.join(u.get('text','') for u in result['units']) for t in ('Stable heading', 'Other paragraph.', 'Later heading'))
    else:
        before = heading_styles(route(head))
        route(polluter)
        after = heading_styles(route(head))
        assert before == after and before['Stable heading']['text_align'] is None, (before, after)
elif case == 'settings':
    assert eh.SETTINGS.get('style_values') == 'independent', 'old saved parses must not be reused'
else:
    raise AssertionError(case)
print('PASS', case)
'''


class NativeStyleOwnershipTests(unittest.TestCase):
    def probe(self, case):
        result = subprocess.run([sys.executable, '-B', '-c', PROBE, case], cwd=ROOT,
                                env=dict(os.environ, PYTHONPATH=''), capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_semantic_tags_and_alignment_do_not_mutate_other_elements(self):
        for kind in ('bold', 'italic', 'underline', 'align'):
            with self.subTest(kind=kind): self.probe('semantic:' + kind)

    def test_cache_hits_misses_and_explicit_styles_keep_independent_values(self):
        self.probe('cache')

    def test_preexisting_pollution_is_cleared_once_at_setup(self):
        self.probe('preloaded')

    def test_repeated_setup_keeps_the_native_cache(self):
        self.probe('idempotent')

    def test_production_conversion_keeps_earlier_and_later_heading_styles(self):
        self.probe('within')

    def test_production_conversion_is_independent_of_document_order(self):
        self.probe('order')

    def test_saved_parse_identity_changes_with_the_style_fix(self):
        self.probe('settings')
