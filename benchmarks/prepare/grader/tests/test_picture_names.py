"""A picture's identity is kept through the tool and through the linking: the scanner records where every picture tag writes its `src` (shown or hidden); the
EdgarTools adapter hands the tool the source with each name replaced by a code it cannot alter and no written name can impersonate (the source's own hash and
the tag's first byte); every unit names the tag its code stands for and is placed there if that tag is shown, else nowhere; the name is given back after. So a
tool that rewrites names (EdgarTools cleans the file's text before parsing: spaces, a space after a point before a capital, `&amp;amp;`, zero-width characters)
cannot put a picture at another picture's tag, a hidden copy of a resource cannot take the shown tag, and a picture from a tag the scanner does not list
(inside <template>) is placed nowhere (Codex G3-C2 and its follow-up)."""
import re
import unittest

from benchmarks.prepare.grader import anchor, grade
from benchmarks.prepare.grader.adapters import edgartools_html as adapter
from benchmarks.prepare.grader.tests.test_edgar_images import node

IMG = re.compile(rb'<img[^>]*?src="([^"]*)"')


def tool(given, keep=None, rewrite=lambda s: s):
    """A stand-in for the tool: one image node per <img> of the source it is given, in order — hidden and template ones too, as the real tool returns them —
    its name as the tool would rewrite it; `keep`: the indices it returns (the others lost)."""
    names = [m.group(1).decode() for m in IMG.finditer(given.encode() if isinstance(given, str) else given)]
    return adapter.dump(node('DocumentNode', children=[node('ImageNode', src=rewrite(s)) for k, s in enumerate(names) if keep is None or k in keep]))


def placed(raw, keep=None, rewrite=lambda s: s):
    """The adapter's own path: the reading, the coded source to the tool, the units back, linked. Returns [(name, the tag's bytes or the link error)]."""
    vis = anchor.Visible(raw); given = adapter.named(raw, vis, adapter.codes(raw, vis))
    units = adapter.route_for(tool(given, keep, rewrite), raw, 'f.htm', 'sha', 0, 'v', vis=vis)['units']
    return [(u['src'], raw[u['anchor']['byte_start']:u['anchor']['byte_end_exclusive']] if u.get('anchor') else u.get('link_error')) for u in units if u['kind'] == 'image']


class PictureNames(unittest.TestCase):
    def test_the_scanner_records_where_each_picture_writes_its_name_shown_or_hidden(self):
        raw = b'<p>\xc3\xa9</p><img src="a.png"><IMG SRC=\'b.png\' alt=x><img src=c.png alt=y><img src=""><img alt="none"><div style="display:none"><img src="h.png"></div><img src="first.png" src="second.png"><svg></svg>'
        vis = anchor.Visible(raw); written = {start: raw[x:y] for start, ((x, y), _) in vis.picture_names.items()}
        self.assertEqual(sorted(written.values()), [b'', b'a.png', b'b.png', b'c.png', b'first.png', b'h.png'])  # the hidden one too; the first of two; none for the svg or the tag without a src
        self.assertEqual({raw[s:s + 4] for s in vis.picture_names}, {b'<img', b'<IMG'})
        self.assertEqual({name for _, name in vis.picture_names.values()}, {'', 'a.png', 'b.png', 'c.png', 'first.png', 'h.png'})
        self.assertEqual(len(vis.pictures), 7); self.assertNotIn(raw.index(b'<img src="h.png"'), dict(vis.pictures))
        self.assertIsNone(vis.picture_sources[raw.index(b'<img alt=')])
        cp = b'<p>\xe9</p><img src="z.png">'; v = anchor.Visible(cp); (x, y), _ = v.picture_names[cp.index(b'<img')]; self.assertEqual(cp[x:y], b'z.png')  # a cp1252 source: one byte per character

    def test_the_tool_is_not_shown_text_the_page_hides(self):  # a hidden "%" beside a value made "8.2 %" of "8.2" and a copy of the visible "%" cell (Codex C4)
        raw = b'<table><tr><td>8.2&#160;<font style="visibility:hidden">%</font></td><td>%</td></tr></table><div style="display:none">gone &amp; away</div><p hidden>no</p><p>stays</p><img src="x.png">'
        vis = anchor.Visible(raw); given = adapter.named(raw, vis, adapter.codes(raw, vis))
        self.assertEqual(re.sub(r'src="[^"]*"', 'src=""', given), '<table><tr><td>8.2&#160;<font style="visibility:hidden"></font></td><td>%</td></tr></table><div style="display:none"></div><p hidden></p><p>stays</p><img src="">')
        raw = b'<style>.x{display:none}</style><div class="x">unknown</div><p>stays</p>'; vis = anchor.Visible(raw); self.assertFalse(vis.certain)
        self.assertEqual(adapter.named(raw, vis, adapter.codes(raw, vis)), raw.decode())  # a reading that is not certain hides nothing from the tool

    def test_the_tool_is_shown_every_tag_the_source_has(self):  # an empty anchor may be laid out as a block and break the line (Codex R3-A); an inline-XBRL wrapper may carry presentation (R2-C1): neither is taken away. The headings they once cut short are read whole by the tool's own traversal (test_whole_headings)
        raw = b'<div>Item 1A. <a name="ra"></a>Risk Factors</div><div>Item 6. <A id="x"><!--Anchor--></A>Exhibits <a href="#x"></a></div><p>See <a href="#n3">Note 3</a>, <a id="k"> </a>and the <a title="a>b"></a>rest.</p><div>10<a style="display:block"></a>20</div><div style="font-weight:bold">For the quarterly period ended <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="c1">December 28, 2024</ix:nonNumeric></div><p>a<ix:nonFraction name="x">1</ix:nonFraction>b</p><img src="x.png">'
        vis = anchor.Visible(raw); self.assertEqual(re.sub(r'src="[^"]*"', 'src=""', adapter.named(raw, vis, adapter.codes(raw, vis))), re.sub(r'src="[^"]*"', 'src=""', raw.decode()))  # only the picture's name changes

    def test_the_codes_are_this_sources_own_and_the_tool_gets_nothing_but_them_changed(self):
        raw = b'<p>Before.</p><img src="chart.JPG"><p>Middle.</p><img src="a&amp;b.png"><p>After.</p>'
        vis = anchor.Visible(raw); codes = adapter.codes(raw, vis); given = adapter.named(raw, vis, codes).encode()
        self.assertEqual(re.sub(rb'src="[^"]*"', b'src=""', given), re.sub(rb'src="[^"]*"', b'src=""', raw))  # nothing but the names changes
        written = [m.group(1).decode() for m in IMG.finditer(given)]; self.assertEqual(written, list(codes))
        self.assertTrue(all(re.fullmatch(r'[a-z0-9]+', c) and c.startswith(grade.sha256(raw)[:16]) for c in written))
        self.assertEqual([codes[c] for c in written], [(raw.index(b'<img'), 'chart.JPG'), (raw.index(b'<img src="a&amp'), 'a&b.png')])
        self.assertNotEqual(adapter.codes(raw + b' ', anchor.Visible(raw + b' ')).keys(), codes.keys())  # another source, other codes
        self.assertNotIn('tag', adapter.to_units(tool(raw))[0])  # without this source's codes a unit names no tag: the linker's own rule applies (Docling)

    def test_a_tool_that_rewrites_names_cannot_move_a_picture(self):
        raw = b'<p>Before.</p><img src="chart.JPG"><p>Middle.</p><img src="chart. JPG"><p>After.</p>'
        rewrite = lambda name: re.sub(r'(\w{2})([.!?])(?=[A-Z])', r'\1\2 ', name)  # what the tool does to a name, standing in for the tool (a code has no point)
        tags = [b'<img src="chart.JPG">', b'<img src="chart. JPG">']
        for keep in ((0, 1), (0,), (1,)):
            with self.subTest(keep=keep): self.assertEqual(placed(raw, keep, rewrite), [(['chart.JPG', 'chart. JPG'][k], tags[k]) for k in keep])

    def test_a_hidden_copy_of_a_resource_never_takes_the_shown_tag(self):
        for hide in ('display:none', 'visibility:hidden', 'opacity:0'):
            for order in ('hidden first', 'shown first'):
                for text in (True, False):
                    parts = ['<div style="%s"><img src="x.png"></div>' % hide, '<img src="x.png">']
                    if order == 'shown first': parts.reverse()
                    raw = (('<p>Before.</p>' + parts[0] + '<p>Middle.</p>' + parts[1] + '<p>After.</p>') if text else (parts[0] + parts[1])).encode()
                    shown = 0 if order == 'shown first' else 1
                    for keep in ((0, 1), (0,), (1,)):
                        with self.subTest(hide=hide, order=order, text=text, keep=keep):
                            self.assertEqual(placed(raw, keep), [('x.png', b'<img src="x.png">' if k == shown else 'ambiguous_image_location') for k in keep])

    def test_a_shown_resource_repeated_stands_each_at_its_own_tag(self):
        raw = b'<img src="x.png"><p>Middle.</p><img src="x.png">'; a, b = raw.index(b'<img'), raw.rindex(b'<img')
        self.assertEqual([t for _, t in placed(raw)], [raw[a:a + 17], raw[b:b + 17]])
        self.assertEqual(placed(raw, (1,)), [('x.png', raw[b:b + 17])])  # the second alone is still the second

    def test_a_picture_the_scanner_does_not_list_is_placed_nowhere(self):
        rewrite = lambda name: re.sub(r'(\w{2})([.!?])(?=[A-Z])', r'\1\2 ', name)
        raw = b'<template><img src="chart.JPG"></template><img src="chart. JPG">'
        self.assertEqual(placed(raw, rewrite=rewrite), [('chart. JPG', 'ambiguous_image_location'), ('chart. JPG', b'<img src="chart. JPG">')])  # the template picture's name, rewritten into the shown one's, names no tag
        vis = anchor.Visible(raw); code = next(iter(adapter.codes(raw, vis)))
        raw2 = b'<template><img src="' + code.encode() + b'"></template><img src="actual.png">'  # a name shaped like a code of another source, or of a guess
        self.assertEqual(placed(raw2), [(code, 'ambiguous_image_location'), ('actual.png', b'<img src="actual.png">')])

    def test_an_unknown_code_keeps_the_tools_name_and_no_place(self):
        raw = b'<p>One</p><img src="a.png">'
        self.assertEqual(placed(raw, rewrite=lambda s: 'made-up.png'), [('made-up.png', 'ambiguous_image_location')])
        self.assertEqual(placed(raw, rewrite=lambda s: s.upper()), [(s.upper(), 'ambiguous_image_location') for s in adapter.codes(raw, anchor.Visible(raw))])  # a code the tool changed is no code

    def test_the_linker_places_a_unit_by_the_tag_the_adapter_names_and_drops_the_field(self):
        raw = b'<div style="display:none"><img src="h.png"></div><p>One</p><img src="a.png">'; shown, hidden = raw.rindex(b'<img'), raw.index(b'<img')
        link = lambda tag: anchor.link(raw, [{'id': 'u0', 'kind': 'text', 'text': 'One'}, {'id': 'u1', 'kind': 'image', 'text': '', 'src': 'c', 'tag': tag}])['units'][1]
        self.assertEqual((link(shown)['anchor'], 'tag' in link(shown)), ({'byte_start': shown, 'byte_end_exclusive': shown + 17}, False))
        for tag in (hidden, None, 5): self.assertEqual(link(tag).get('link_error'), 'ambiguous_image_location')
        two = anchor.link(raw, [{'id': 'u1', 'kind': 'image', 'text': '', 'src': 'c', 'tag': shown}, {'id': 'u2', 'kind': 'image', 'text': '', 'src': 'c', 'tag': shown}])['units']
        self.assertEqual([u.get('link_error') for u in two], [None, 'ambiguous_image_location'])  # one tag, one unit

    def test_the_linker_takes_the_reading_it_is_given(self):
        raw = b'<p>One</p><img src="a.png">'; units = lambda: [{'id': 'u0', 'kind': 'text', 'text': 'One'}, {'id': 'u1', 'kind': 'image', 'text': '', 'src': 'a.png'}]
        self.assertEqual(anchor.link(raw, units(), vis=anchor.Visible(raw)), anchor.link(raw, units()))
        other = anchor.Visible(b'<p>One</p><img src="b.png">'); self.assertEqual(anchor.link(raw, units(), vis=other)['units'][1].get('link_error'), 'ambiguous_image_location')

    def test_the_name_given_back_is_the_parsers_reading_of_that_tag(self):
        raw = b'<p>One</p><img src="a&amp;b.png"><img src="a&amp;b.png">'
        self.assertEqual([n for n, _ in placed(raw)], ['a&b.png', 'a&b.png'])


if __name__ == '__main__':
    unittest.main()
