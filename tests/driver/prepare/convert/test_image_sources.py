"""Image locations come from actual source tags, never chained empty gaps."""
import unittest
from driver.prepare.convert import anchor
from driver.prepare.convert.edgartools_html import to_units


class ImageSourcesTests(unittest.TestCase):
    def test_unique_source_image_is_anchored_to_its_tag(self):
        raw = b'<p>Before.</p><img src="plot.png" alt="x > y"><p>After.</p>'
        units = [{'id': 'a', 'kind': 'text', 'text': 'Before.'},
                 {'id': 'i', 'kind': 'image', 'text': ''},
                 {'id': 'b', 'kind': 'text', 'text': 'After.'}]
        image = anchor.link(raw, units)['units'][1]
        a = image['anchor']
        self.assertEqual(raw[a['byte_start']:a['byte_end_exclusive']], b'<img src="plot.png" alt="x > y">')

    def test_resource_identity_resolves_consecutive_images_without_guessing_order(self):
        raw = b'<img src="a.png"><img src="b.png">'
        units = [{'id': name, 'kind': 'image', 'src': name, 'text': ''} for name in ('b.png', 'a.png')]
        for u in anchor.link(raw, units)['units']:
            a = u['anchor']; self.assertIn(u['src'].encode(), raw[a['byte_start']:a['byte_end_exclusive']])

    def test_ambiguous_absent_or_hidden_image_location_is_explicitly_unknown(self):
        for raw in (b'<img src="a"><img src="b">', b'<p>no image</p>',
                    b'<!-- <img src="fake"> --><img style="display:none" src="hidden">'):
            u = anchor.link(raw, [{'id': 'i', 'kind': 'image', 'text': ''}])['units'][0]
            self.assertIsNone(u['anchor'])
            self.assertEqual(u['link_error'], 'ambiguous_image_location')

    def test_adapter_keeps_the_tools_resource_identity(self):
        self.assertEqual(to_units({'type': 'ImageNode', 'src': 'plot.png'})[0]['src'], 'plot.png')

    def test_missing_identity_is_not_guessed_by_eliminating_claimed_images(self):
        raw = b'<img src="a"><img src="b">'
        units = [{'id': 'a', 'kind': 'image', 'src': 'a', 'text': ''}, {'id': 'unknown', 'kind': 'image', 'text': ''}]
        self.assertIsNone(anchor.link(raw, units)['units'][1]['anchor'])

    def test_raw_text_contains_literal_markup_not_images(self):
        for tag in ('textarea', 'xmp', 'iframe', 'noembed', 'noframes'):
            raw = f'<{tag}><img src="fake"> &amp; a > b</{tag}><img src="real">'.encode()
            with self.subTest(tag=tag):
                v = anchor.Visible(raw)
                self.assertEqual([raw[a:b] for a,b in v.pictures], [b'<img src="real">'])
                if tag in ('textarea', 'xmp'):
                    self.assertIn('<img src="fake">', v.text)
                    self.assertIn('& a > b' if tag == 'textarea' else '&amp; a > b', v.text)

    def test_raw_text_does_not_consume_following_real_markup(self):
        raw = b'<xmp><script><img src="fake"></xmp><img src="real"></script>'
        v = anchor.Visible(raw)
        self.assertEqual([raw[a:b] for a,b in v.pictures], [b'<img src="real">'])
        self.assertIn('<script><img src="fake">', v.text)

    def test_unclosed_raw_text_cannot_create_pictures(self):
        for tag in ('textarea', 'title', 'xmp', 'script', 'style', 'iframe', 'template'):
            with self.subTest(tag=tag):
                self.assertEqual(anchor.Visible(f'<{tag}><img src="fake">'.encode()).pictures, [])

    def test_a_raw_opening_tag_that_ends_inside_a_quoted_attribute_certifies_no_inventory(self):
        for tag in ('script', 'style', 'title', 'template'):  # Chrome: the picture inside is text of the element, one picture is shown; this scanner does not follow such a tag and says so
            with self.subTest(tag=tag):
                self.assertFalse(anchor.Visible(f'<{tag} title="> </{tag}>"><img src="fake"></{tag}><img src="real">'.encode()).certain)
        raw = b'<head title="> </head>"><img src="fake"></head><img src="real">'; v = anchor.Visible(raw)  # Chrome: the parser ends the head at the first picture — both are shown
        self.assertEqual(([raw[a:b] for a, b in v.pictures], v.certain), ([b'<img src="fake">', b'<img src="real">'], True))


class PicturePlaceTests(unittest.TestCase):
    """Each condition of the rule (added in the merge; the cases above are the worktree's)."""
    image = staticmethod(lambda uid, src=None: dict({'id': uid, 'kind': 'image', 'text': ''}, **({'src': src} if src else {})))
    text = staticmethod(lambda uid, words: {'id': uid, 'kind': 'text', 'text': words})
    tag = staticmethod(lambda raw, u: raw[u['anchor']['byte_start']:u['anchor']['byte_end_exclusive']] if u.get('anchor') else None)

    def test_unnamed_pictures_on_either_side_of_a_text_stand_each_at_its_own_tag(self):
        raw = b'<img src="a.png"><p>Middle.</p><img src="b.png">'
        out = anchor.link(raw, [self.image('x'), self.text('m', 'Middle.'), self.image('y')])['units']
        self.assertEqual([self.tag(raw, out[0]), self.tag(raw, out[2])], [b'<img src="a.png">', b'<img src="b.png">'])

    def test_a_neighbour_without_a_place_bounds_nothing(self):
        raw = b'<p>Before.</p><img src="a.png"><p>After.</p>'
        units = [self.text('b', 'Before.'), self.text('n', 'words the source does not print'), self.image('i'), self.text('o', 'nor these'), self.text('a', 'After.')]
        self.assertEqual(self.tag(raw, anchor.link(raw, units)['units'][2]), b'<img src="a.png">')

    def test_a_named_picture_stands_at_its_tag_wherever_the_tool_lists_it_an_unnamed_one_only_between_its_neighbours(self):
        raw = b'<img src="a.png"><p>Before.</p><p>After.</p>'  # the picture stands before both texts; the tool lists it between them
        for src, want in (('a.png', b'<img src="a.png">'), (None, None)):
            with self.subTest(src=src):
                img = anchor.link(raw, [self.text('b', 'Before.'), self.image('i', src), self.text('a', 'After.')])['units'][1]
                self.assertEqual((self.tag(raw, img), img.get('link_error')), (want, None if want else 'ambiguous_image_location'))

    def test_a_resource_shown_twice_is_told_apart_by_the_units_neighbours(self):
        raw = b'<img src="logo.png"><p>Middle.</p><img src="logo.png">'
        out = anchor.link(raw, [self.image('x', 'logo.png'), self.text('m', 'Middle.'), self.image('y', 'logo.png')])['units']
        self.assertEqual([out[0]['anchor']['byte_start'], out[2]['anchor']['byte_start']], [raw.index(b'<img'), raw.rindex(b'<img')])

    def test_one_tag_is_one_units(self):
        out = anchor.link(b'<img src="a.png">', [self.image('x', 'a.png'), self.image('y', 'a.png')])['units']
        self.assertEqual([(u['anchor'] is not None, u.get('link_error')) for u in out], [(True, None), (False, 'ambiguous_image_location')])

    def test_a_resource_is_named_as_the_parser_reads_the_attribute_decoded_once(self):  # Codex G3-C1: the src was compared as written; the tool gives it decoded
        NOT, HAN = chr(0xac), chr(0x5716)
        for name, written in (('img?a=1&b=2.png', 'img?a=1&amp;b=2.png'), ('a"b.png', 'a&quot;b.png'), ('a>b.png', 'a&gt;b.png'), ('a&b.png', 'a&#38;b.png'), ('a&b.png', 'a&#x26;b.png'),
                              ('a&notit;b.png', 'a&notit;b.png'), ('x?a=1&not=1', 'x?a=1&not=1'), ('a' + NOT + 'it.png', 'a&not;it.png'), ('a&.png', 'a&amp.png'), ('a&amp;b.png', 'a&amp;amp;b.png'), (HAN + '.png', HAN + '.png')):
            with self.subTest(written=written):
                raw = ('<img src="%s">' % written).encode()
                self.assertEqual(self.tag(raw, anchor.link(raw, [self.image('i', name)])['units'][0]), raw)
        for name, written in (('a&b.png', 'a&amp;amp;b.png'), ('a' + NOT + 'it;b.png', 'a&notit;b.png'), ('a&amp;b.png', 'a&amp;b.png')):  # decoded twice, decoded where the parser does not, not decoded
            with self.subTest(wrong=name, written=written):
                raw = ('<img src="%s">' % written).encode()
                self.assertIsNone(anchor.link(raw, [self.image('i', name), self.image('j', name)])['units'][0]['anchor'])  # (two units: neither is "the only picture between its neighbours")

    def test_two_spellings_of_one_resource_are_one_resource_told_apart_by_neighbours(self):  # Codex G3-C1: the first picture was put at the second tag, the second left without a place
        raw = b'<img src="a&amp;b.png"><p>Middle.</p><img src="a&b.png">'
        out = anchor.link(raw, [self.image('x', 'a&b.png'), self.text('m', 'Middle.'), self.image('y', 'a&b.png')])['units']
        self.assertEqual([self.tag(raw, out[0]), self.tag(raw, out[2])], [b'<img src="a&amp;b.png">', b'<img src="a&b.png">'])

    def test_an_attribute_is_read_as_the_parser_reads_it(self):
        CR, LF, NUL, NOT, REPLACED = chr(13), chr(10), chr(0), chr(0xac), chr(0xfffd)
        for written, read in (('a&amp;b', 'a&b'), ('a&ampb', 'a&ampb'), ('a&amp=1', 'a&amp=1'), ('a&amp.png', 'a&.png'), ('a&amp', 'a&'), ('&notit;', '&notit;'), ('&not;it', NOT + 'it'), ('&#38;', '&'), ('&#x26', '&'),
                              ('a' + CR + LF + 'b' + CR + 'c', 'a' + LF + 'b' + LF + 'c'), ('&#13;', CR), ('&amp;amp;', '&amp;'), ('&unknown;', '&unknown;'), ('&', '&'), ('a' + NUL + 'b', 'a' + REPLACED + 'b'), ('', '')):
            with self.subTest(written=written): self.assertEqual(anchor.attribute_value(written), read)

    def test_a_picture_that_touches_its_neighbours_is_between_them(self):
        raw = b'<p>Before.<img src="x.png">After.</p>'
        self.assertEqual(self.tag(raw, anchor.link(raw, [self.text('b', 'Before.'), self.image('i'), self.text('a', 'After.')])['units'][1]), b'<img src="x.png">')
