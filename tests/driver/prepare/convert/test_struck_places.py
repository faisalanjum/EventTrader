"""The exact places of struck text (`struck_at`): the source's own decoration placed on the item's text, certified both ways; and the boundary gate's
redline join — a struck word printed glued to the next is two words when the item says where the strike is. Codex's worktree cases (test_source_richtext,
test_strike_boundaries) on this field, and this scanner's own uncertain shapes."""
import unittest

from driver.prepare.convert import anchor
from driver.prepare.convert import source_formatting


def item(raw, text, **more):
    return {'id': 'u', 'kind': 'text', 'text': text, 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, **more}


def formatted(raw, text, **more):
    x = item(raw, text, **more); source_formatting.apply(raw, [x]); return x


class StruckPlaces(unittest.TestCase):
    def test_a_repeated_word_is_placed_at_the_occurrence_the_source_strikes(self):
        raw = b'<p>The <strike>The</strike> The</p>'
        x = formatted(raw, 'The The The')
        self.assertEqual((x['text'], x['struck'], x['struck_at']), ('The The The', ['The'], [[4, 7]]))

    def test_a_redline_printed_as_one_run_keeps_its_text_and_says_where_the_strike_ends(self):
        for raw, text, end in [(b'<p><s>The</s>Except</p>', 'TheExcept', 3), (b'<p><s>18.12</s>18.13</p>', '18.1218.13', 5), (b'<p><s>1&amp;2</s>1&amp;2</p>', '1&21&2', 3)]:
            with self.subTest(raw=raw):
                x = formatted(raw, text); self.assertEqual((x['text'], x['struck_at']), (text, [[0, end]]))

    def test_a_struck_run_of_words_is_one_range_per_word_and_a_cell_has_places_too(self):
        raw = b'<table><tr><td>Total <s>net sales</s> (1)</td></tr></table>'
        t = {'id': 't', 'kind': 'table', 'anchor': {'byte_start': 0, 'byte_end_exclusive': len(raw)}, 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Total net sales (1)', 'anchor': {'byte_start': raw.index(b'Total'), 'byte_end_exclusive': raw.index(b'</td>')}}]}
        source_formatting.apply(raw, [t]); self.assertEqual(t['cells'][0]['struck_at'], [[6, 9], [10, 15]])

    def test_folded_characters_align_and_a_reported_mark_or_omitted_text_leaves_the_places_unsaid(self):
        raw = ('<p>Company\u2019s <s>old</s> plan</p>').encode(); x = formatted(raw, "Company's old plan"); self.assertEqual(x['struck_at'], [[10, 13]])
        raw = b'<p><s>The</s> missing The</p>'
        units = [item(raw, 'The The'), {'id': 'v', 'kind': 'text', 'text': 'The', 'struck': ['The'], 'anchor': None}, dict(item(raw, 'missing The'), markers=['The'])]
        source_formatting.apply(raw, units); self.assertEqual([u.get('struck_at') for u in units], [None, None, None])

    def test_plain_text_gets_no_places_and_uncertain_decoration_certifies_none(self):
        self.assertNotIn('struck_at', formatted(b'<p>The The The</p>', 'The The The'))
        for raw in [b'<style>s{text-decoration:none}</style><p><s>The</s></p>', b'<p><s style="display:contents">The</s></p>', b'<p><s style="letter-spacing:-1em">The</s></p>', b'<p><s style="color:transparent">The</s></p>']:
            with self.subTest(raw=raw): self.assertIsNone(anchor.struck_at(anchor.Visible(raw), item(raw, 'The')))
        x = formatted(b'<style>s{text-decoration:none}</style><p><s>The</s></p>', 'The', struck=['The'], struck_at=[[0, 3]]); self.assertNotIn('struck_at', x)  # plain is certain, the strike is not: no exact answer, the claim goes
        x = formatted(b'<p><s style="display:contents">The</s></p>', 'The', struck=['The'], struck_at=[[0, 3]]); self.assertEqual(x['struck_at'], [[0, 3]])  # nothing certified either way: the converter's own claim stands, as for `struck`

    def test_places_in_several_spans_are_read_in_order_and_overlapping_or_boxed_places_say_nothing(self):
        raw = b'<table><tr><td><s>Net</s></td><td>sales</td></tr></table>'; a, b = raw.index(b'<s>'), raw.index(b'sales')
        two = [{'byte_start': a, 'byte_end_exclusive': a + 10}, {'byte_start': b, 'byte_end_exclusive': b + 5}]; vis = anchor.Visible(raw)
        self.assertEqual(anchor.struck_at(vis, {'text': 'Net sales', 'anchor': two}), [[0, 3]])
        touching = [{'byte_start': a, 'byte_end_exclusive': a + 6}, {'byte_start': a + 6, 'byte_end_exclusive': a + 10}]  # `<s>Net` and `</s>`: places that touch do not overlap
        self.assertEqual(anchor.struck_at(vis, {'text': 'Net', 'anchor': touching}), [[0, 3]])
        self.assertIsNone(anchor.struck_at(vis, {'text': 'NetNet', 'anchor': [two[0], dict(two[0])]}))  # one place twice: no reading
        self.assertIsNone(anchor.struck_at(vis, {'text': 'Net', 'anchor': [two[0], {'page': 1, 'region': [0, 0, 1, 1]}]}))  # a box among the places: no reading

    def test_a_certified_strike_reading_is_a_certified_plain_reading(self):  # struck_at asks for struck_certain alone
        for sheet in (b'', b'<style>s{text-decoration:none}</style>', b'<style>p{text-decoration:line-through}</style>', b'<style>p{text-decoration:inherit}</style>', b'<style>p{color:red}</style>'):
            with self.subTest(sheet=sheet):
                vis = anchor.Visible(sheet + b'<p><s>The</s></p>'); self.assertTrue(not vis.struck_certain or vis.plain_certain)

    def test_places_name_the_texts_own_characters_whatever_marks_it_prints(self):  # Codex G5-1: the key's ~~ marks are dropped by the comparison form; the positions must still be the text's own
        for before, after in [('', ''), ('now ', ' plan'), ('“x” ', ' next'), ('~~now~~ ', ' ~~next~~')]:
            raw = ('<p>%s<s>old</s>%s</p>' % (before.replace('~~', ''), after.replace('~~', ''))).encode()
            for opening, closing in [('', ''), ('~~', '~~'), ('~~~~', '~~~~'), ('~~​', '​~~')]:
                text = before + opening + 'old' + closing + after; start = len(before) + len(opening)
                with self.subTest(text=text):
                    x = formatted(raw, text); self.assertEqual((x['struck_at'], [text[a:b] for a, b in x['struck_at']]), ([[start, start + 3]], ['old']))

    def test_a_tool_claim_of_places_is_dropped_where_the_source_shows_otherwise(self):
        x = formatted(b'<p>The The</p>', 'The The', struck_at=[[0, 3]]); self.assertNotIn('struck_at', x)
        x = formatted(b'<p><s>The</s> The</p>', 'The The', struck_at=[[4, 7]]); self.assertEqual(x['struck_at'], [[0, 3]])

    def test_the_step_names_itself_in_the_route_record(self):
        raw = b'<p><s>Old</s> New</p>'; route = {'route': {'name': 'r', 'settings': {'a': 1}}, 'units': anchor.link(raw, [{'id': 'u', 'kind': 'text', 'text': 'Old New'}])['units']}
        self.assertEqual(source_formatting.step(raw, route), 1)
        self.assertEqual((route['route']['name'], route['route']['settings'], route['units'][0]['struck']), ('r+source-formatting', {'a': 1, 'source_formatting': True}, ['Old']))


if __name__ == '__main__':
    unittest.main()
