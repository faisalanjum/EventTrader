"""Visible text of an original with byte spans, and the linker that places tool output back in it (anchor.py)."""
import time
import unittest

from benchmarks.prepare.grader import anchor

HTML = (b'<html><head><title>Sample</title><style>td{color:red}</style></head><body>\n'
        b'<!-- cover -->\n'
        b'<div style="font-weight:bold">Item 2. Management&#8217;s Discussion</div>\n'
        b'<p>S<span>tock</span>holder&nbsp;letter <s>not</s> final.<span style="display:none">HIDDEN <div>deep</div> text</span></p>\n'
        b'<div style="display:none"><div>inner</div>still hidden</div>\n'
        b'<ix:hidden><ix:nonNumeric>tagged</ix:nonNumeric></ix:hidden>\n'
        b'<table><tr><td>Free cash flow<sup>(1)</sup></td><td>$</td><td>(506</td><td>)</td></tr></table>\n'
        b'<p>(1) Note text.</p><p>4</p></body></html>')


class VisibleTextTests(unittest.TestCase):
    def test_inline_tags_add_no_space_and_entities_decode_once(self):
        v = anchor.Visible(HTML)
        self.assertIn('Stockholder letter not final.', anchor.norm(v.text))  # the struck "not" is read as its own word, so compare with whitespace collapsed
        self.assertIn('Management’s Discussion', v.text)

    def test_hidden_subtrees_head_comments_and_styles_are_not_visible(self):
        v = anchor.Visible(HTML)
        for gone in ('HIDDEN', 'deep', 'inner', 'still hidden', 'tagged', 'Sample', 'color:red', 'cover'):
            self.assertNotIn(gone, v.text, gone)

    def test_block_tags_separate_cells_by_one_space(self):
        v = anchor.Visible(HTML)
        self.assertIn('Free cash flow(1) $ (506 )', anchor.norm(v.text))

    def test_byte_spans_point_back_into_the_original(self):
        v = anchor.Visible(HTML)
        i = v.text.index('(506')
        self.assertEqual(HTML[v.starts[i]:v.ends[i + 3]], b'(506')

    def test_text_at_a_byte_range_returns_only_visible_characters_inside_it(self):
        v = anchor.Visible(HTML)
        a = HTML.index(b'<p>S<span>'); b = HTML.index(b'</p>', a) + 4
        self.assertEqual(anchor.norm(v.at(a, b)), 'Stockholder letter not final.')

    def test_invalid_utf8_falls_back_to_cp1252_with_byte_offsets(self):
        raw = b'<p>caf\xe9 \x93quoted\x94</p>'
        v = anchor.Visible(raw)
        self.assertEqual(anchor.norm(v.text), 'caf\xe9 "quoted"')
        self.assertEqual(raw[v.starts[v.text.index('q')]:v.ends[v.text.index('q')]], b'q')


class MemoryAndOffsetTests(unittest.TestCase):
    def test_multibyte_text_runs_keep_exact_byte_spans(self):
        raw = 'x<p>Caf\u00e9 \u2014 na\u00efve \u20ac5</p><p>plain ascii</p>'.encode('utf-8')
        v = anchor.Visible(raw)
        for ch in ('\u00e9', '\u2014', '\u20ac', 'p', 'a'):
            i = v.text.index(ch); self.assertEqual(raw[v.starts[i]:v.ends[i]].decode('utf-8'), ch)
        self.assertEqual(anchor.norm(v.at(raw.index(b'<p>plain'), len(raw))), 'plain ascii')

    def test_peak_memory_grows_with_visible_text_not_with_markup(self):
        import tracemalloc
        raw = (b'<div style="display:none">' + b'hidden ' * 20000 + b'</div>' + b'<span data-x="' + b'a' * 400000 + b'">v</span>') * 3
        tracemalloc.start(); v = anchor.Visible(raw); _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        self.assertEqual(v.text, 'vvv')
        self.assertLess(peak, 4 * len(raw))  # the decoded string and tokens, never one integer per source byte


class InvisibleStyleTests(unittest.TestCase):
    def test_text_made_invisible_by_style_is_not_visible_text_but_is_counted(self):
        raw = (b'<p>shown</p><div style="visibility:hidden">gone</div><div style="opacity:0">clear &amp; gone</div>'
               b'<p style="font-size:8pt">small but shown</p>')
        v = anchor.Visible(raw)
        self.assertEqual(anchor.norm(v.text), 'shown small but shown')
        self.assertEqual(v.hidden_chars, len('gone') + len('clear&gone'))

    def test_a_visible_descendant_inside_a_hidden_parent_is_visible_but_display_none_cannot_be_undone(self):
        # CSS: visibility inherits and a descendant may set visibility:visible again (E16); display:none and opacity:0 cannot be undone
        raw = (b'<div style="visibility:hidden">gone <span style="visibility:visible">back</span> gone2</div>'
               b'<div style="display:none">never <span style="visibility:visible">still never</span></div><p>after</p>')
        v = anchor.Visible(raw)
        self.assertEqual(anchor.norm(v.text), 'back after')
        self.assertEqual(v.hidden_chars, len('gone') + len('gone2') + len('never') + len('stillnever'))

    def test_attribute_values_never_leak_into_text_and_only_the_style_attribute_hides(self):
        # checked against Chrome by the reviewer (R3): a ">" inside a quoted attribute, and CSS words in a non-style attribute
        self.assertEqual(anchor.norm(anchor.Visible(b'<p title="a > b">Revenue rose.</p>').text), 'Revenue rose.')
        v = anchor.Visible(b'<p title="display:none is a CSS rule">Revenue rose.</p>')
        self.assertEqual((anchor.norm(v.text), v.hidden_chars), ('Revenue rose.', 0))

    def test_display_in_the_style_attribute_decides_block_or_inline(self):
        self.assertEqual(anchor.norm(anchor.Visible(b'<span style="display:block">Revenue</span><span style="display:block">rose.</span>').text), 'Revenue rose.')
        self.assertEqual(anchor.norm(anchor.Visible(b'<div style="display:inline">Reve</div><div style="display: inline">nue</div>').text), 'Revenue')

    def test_stylesheet_rules_make_visibility_uncertain_instead_of_wrong(self):
        v = anchor.Visible(b'<style>.off {display:none}</style><p class="off">Hidden.</p><p>Revenue rose.</p>')
        self.assertFalse(v.certain)  # a class rule may hide text this scanner cannot see: the file is reported, not certified
        self.assertTrue(anchor.Visible(b'<p style="display:none">x</p><p>Revenue rose.</p>').certain)
        self.assertFalse(anchor.Visible(b'<link rel="stylesheet" href="a.css"><p>Revenue rose.</p>').certain)

    def test_attributes_are_parsed_and_the_last_display_declaration_wins(self):
        # Codex round 3, checked against Chrome: a style string inside another attribute's value is not a style; CSS keeps the last declaration
        self.assertEqual(anchor.norm(anchor.Visible(b'<p title="x style=\'display:none\'">Revenue rose.</p>').text), 'Revenue rose.')
        self.assertEqual(anchor.norm(anchor.Visible(b'<p style="display:none; display:block">Revenue rose.</p>').text), 'Revenue rose.')

    def test_important_and_case_do_not_defeat_the_style_parser(self):
        self.assertEqual(anchor.norm(anchor.Visible(b'<p STYLE="DISPLAY: none !important">Secret.</p><p>Visible.</p>').text), 'Visible.')
        self.assertEqual(anchor.norm(anchor.Visible(b'<p style=display:none>Secret.</p><p>Visible.</p>').text), 'Visible.')  # unquoted value

    def test_visibility_inherit_keeps_the_parents_state(self):
        raw = b'<div style="visibility:hidden">gone <span style="visibility:inherit">still gone</span> <span style="visibility:visible">back</span></div>'
        self.assertEqual(anchor.norm(anchor.Visible(raw).text), 'back')

    def test_struck_text_is_its_own_word(self):
        # a redline "94" beside a struck "93" renders as two numbers, not one: deleted or line-through runs are separated like blocks
        self.assertEqual(anchor.norm(anchor.Visible(b'<p>Rounding <ins>94</ins><del>93</del></p>').text), 'Rounding 94 93')
        self.assertEqual(anchor.norm(anchor.Visible(b'<p>Rounding <span>94</span><span style="text-decoration: line-through">93</span></p>').text), 'Rounding 94 93')
        self.assertEqual(anchor.norm(anchor.Visible(b'<p>Ma<b>nagement</b></p>').text), 'Management')  # plain emphasis is not a boundary

    def test_the_hidden_attribute_and_template_content_are_not_rendered(self):
        v = anchor.Visible(b'<p hidden>Secret.</p><p>Visible.</p>'); self.assertEqual((anchor.norm(v.text), v.hidden_chars), ('Visible.', len('Secret.')))
        self.assertEqual(anchor.norm(anchor.Visible(b'<template><p>Template.</p></template><p>Visible.</p>').text), 'Visible.')

    def test_a_stylesheet_that_sets_display_makes_boundaries_uncertain(self):
        v = anchor.Visible(b'<style>.block{display:block}</style><span class="block">Revenue</span><span class="block">rose.</span>')
        self.assertFalse(v.certain)  # a class rule can change block boundaries this scanner does not apply
        self.assertTrue(anchor.Visible(b'<style>p{color:red}</style><p>Revenue rose.</p>').certain)

    def test_repeated_blocks_are_placed_by_their_unique_neighbours_even_when_the_tool_reorders_headings(self):
        # three identical signature pages; only the lender names differ; the tool emits the second heading before the first body
        H, B = 'SIGNATURE PAGE TO THE REFINANCING AGREEMENT', 'The undersigned Lender hereby elects the cashless roll option.'
        names = ['Virtus Fixed Income Advisers, LLC', 'Seix Investment Advisors LLC', 'Black Diamond CLO 2022-1 Adviser']
        raw = ''.join(f'<h2>{H}</h2><p>{B}</p><p>By: {n}</p>' for n in names).encode()
        order = [H, H, B, 'By: ' + names[0], H, B, 'By: ' + names[1], B, 'By: ' + names[2]]
        units = [{'id': f'u{i}', 'kind': 'text', 'text': x} for i, x in enumerate(order)]
        out = anchor.link(raw, units)
        self.assertEqual(out['uncovered'], [])  # every copy of every block is covered exactly once
        starts = sorted(u['anchor']['byte_start'] for u in units)
        self.assertEqual(len(set(starts)), len(units))  # no two units share a copy

    def test_a_long_unit_the_exact_search_cannot_place_is_anchored_piecewise(self):
        # the tool skipped a page number the source interleaves, inserted a rule line and flattened a small table into the paragraph
        raw = (b'<p>The Companies make certain estimates and assumptions that affect reported amounts of assets and liabilities.</p><p>25</p>'
               b'<p>Dominion Energy maintains pension and other postretirement benefit plans for its employees and retirees.</p><table><tr><td>$341</td><td>$408</td></tr></table>'
               b'<p>Actual results could differ from those estimates in a material way for the periods presented.</p>')
        u = {'id': 'u', 'kind': 'text', 'text': 'The Companies make certain estimates and assumptions that affect reported amounts of assets and liabilities. '
             'Dominion Energy maintains pension and other postretirement benefit plans for its employees and retirees. \u2500\u2500\u2500\u2500 $341$408 '
             'Actual results could differ from those estimates in a material way for the periods presented.'}
        out = anchor.link(raw, [u]); u = out['units'][0]
        self.assertEqual((u['link_flag'], len(u['anchor']), u['inserted_chars']), ('pieced', 3, 4))
        self.assertEqual([x['text'] for x in out['uncovered']], ['25'])  # what the tool dropped stays uncovered; what it added is counted

    def test_inline_css_decides_visibility_the_way_chrome_renders_it(self):
        # expectations observed in headless Chrome (innerText), Codex round-4 browser probe: the cascade inside one attribute,
        # entities and comments in the attribute, invalid values ignored; a value this scanner does not evaluate makes the file uncertain
        cases = [('<p style="display:none!important;display:block">Secret.</p><p>Visible.</p>', 'Visible.', True),
                 ('<p style="display:none; display:block">Revenue rose.</p>', 'Revenue rose.', True),
                 ('<p style="display&#58;none">Secret.</p><p>Visible.</p>', 'Visible.', True),
                 ('<p style="display/*comment*/:none">Secret.</p><p>Visible.</p>', 'Visible.', True),
                 ('<p style="visibility:nonsense">Visible.</p>', 'Visible.', True),
                 ('<p style="visibility:hidden">Secret <span style="visibility:visible">Shown</span></p>', 'Shown', True),
                 ('<p style="--mode:none;display:var(--mode)">Secret.</p><p>Visible.</p>', None, False)]
        for src, text, certain in cases:
            v = anchor.Visible(src.encode())
            self.assertEqual((anchor.norm(v.text) if text is not None else None, v.certain), (text, certain), src)

    def test_alignment_stays_linear_on_repetitive_text(self):
        # Codex R4-4: a 20k-character repetitive paragraph with one inserted character made the character diff quadratic (killed at 2 s CPU)
        s = 'Revenue ' + 'abcde' * 4000 + ' end.'; raw = ('<p>' + s + '</p>').encode()
        u = {'id': 'u', 'kind': 'text', 'text': s[:10000] + 'X' + s[10000:]}
        t0 = time.monotonic(); anchor.link(raw, [u]); seconds = time.monotonic() - t0
        self.assertEqual((u['link_flag'], len(u['anchor']), u['inserted_chars']), ('pieced', 2, 1)); self.assertLess(seconds, 2.0)
        u = {'id': 'u', 'kind': 'text', 'text': s}; anchor.link(raw, [u]); self.assertNotIn('link_flag', u)  # unchanged text: exact, not pieced

    def test_tiny_or_white_text_is_still_visible_text_and_a_font_size_0_wrapper_hides_nothing(self):
        # font size is inherited and reset by children: a font-size:0 wrapper around real paragraphs hides none of them,
        # and 1pt text is rendered (Codex B9); only display/opacity/visibility hide a subtree
        raw = (b'<div style="font-size:0;margin-top:0.0pt"><span style="font-size:10pt">Section 1. Amendment.</span></div>'
               b'<font style="font-size:1pt;color:white">tiny</font><span style="font-size: 0px">zero</span>')
        v = anchor.Visible(raw)
        self.assertEqual(anchor.norm(v.text), 'Section 1. Amendment. tinyzero')  # font/span are inline: no space between them
        self.assertEqual(v.hidden_chars, 0)


class NormTests(unittest.TestCase):
    def test_norm_collapses_whitespace_folds_glyphs_and_drops_struck_marks(self):
        self.assertEqual(anchor.norm('  Three\xa0Months\n\u200bEnded ~~not~~ \u2018a\u2019 \u2013 \u201cb\u201d '), 'Three Months Ended not \'a\' - "b"')

    def test_norm_keeps_case_signs_and_unit_case(self):
        self.assertEqual(anchor.norm('(506) MW mW -3%'), '(506) MW mW -3%')


UNITS = [
    {'id': 'u0', 'kind': 'heading', 'text': "Item 2. Management's Discussion"},
    {'id': 'u1', 'kind': 'text', 'text': 'Stockholder letter not final.'},
    {'id': 'u2', 'kind': 'table', 'cells': [
        {'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Free cash flow', 'markers': ['(1)']},
        {'r': 0, 'c': 1, 'rs': 1, 'cs': 1, 'text': '$'},
        {'r': 0, 'c': 2, 'rs': 1, 'cs': 1, 'text': '(506'},
        {'r': 0, 'c': 3, 'rs': 1, 'cs': 1, 'text': ')'}]},
    {'id': 'u3', 'kind': 'footnote', 'text': '(1) Note text.'},
    {'id': 'u4', 'kind': 'clutter', 'text': '4'},
]


def linked(units=UNITS, raw=HTML):
    import copy
    return anchor.link(raw, copy.deepcopy(units))


class LinkTests(unittest.TestCase):
    def test_every_unit_gets_an_anchor_whose_visible_text_is_its_text(self):
        out = linked(); v = anchor.Visible(HTML)
        for u in out['units']:
            if u['kind'] == 'table':
                for c in u['cells']:
                    got = anchor.norm(v.at(c['anchor']['byte_start'], c['anchor']['byte_end_exclusive']))
                    self.assertEqual(got, anchor.norm(c['text'] + ''.join(c.get('markers', []))), c['text'])
            else:
                got = anchor.norm(v.at(u['anchor']['byte_start'], u['anchor']['byte_end_exclusive']))
                self.assertEqual(got, anchor.norm(u['text']), u['text'])
        self.assertEqual(out['uncovered'], [])

    def test_straight_quote_in_tool_text_matches_curly_quote_in_source(self):
        out = linked()
        self.assertIsNotNone(out['units'][0]['anchor'])

    def test_table_anchor_spans_its_cells(self):
        out = linked(); t = out['units'][2]
        self.assertEqual(t['anchor']['byte_start'], t['cells'][0]['anchor']['byte_start'])
        self.assertEqual(t['anchor']['byte_end_exclusive'], t['cells'][-1]['anchor']['byte_end_exclusive'])

    def test_altered_digit_is_left_unanchored_not_guessed(self):
        units = [dict(u) for u in UNITS]; units[2] = {'id': 'u2', 'kind': 'table', 'cells': [dict(c) for c in UNITS[2]['cells']]}
        units[2]['cells'][2] = dict(units[2]['cells'][2], text='(560')
        out = linked(units)
        self.assertIsNone(out['units'][2]['cells'][2]['anchor'])
        self.assertEqual(out['units'][2]['cells'][2]['link_error'], 'not_in_source')
        self.assertTrue(any('(506' in s['text'] for s in out['uncovered']))

    def test_dropped_paragraph_is_reported_as_uncovered_source_text(self):
        out = linked([u for u in UNITS if u['id'] != 'u1'])
        self.assertEqual([anchor.norm(s['text']) for s in out['uncovered']], ['Stockholder letter not final.'])
        self.assertEqual(HTML[out['uncovered'][0]['byte_start']:out['uncovered'][0]['byte_start'] + 1], b'S')

    def test_out_of_order_unit_is_anchored_and_flagged(self):
        units = [UNITS[1], UNITS[0]] + UNITS[2:]
        out = linked(units)
        self.assertIsNotNone(out['units'][1]['anchor'])
        self.assertEqual(out['units'][1].get('link_flag'), 'out_of_order')
        self.assertEqual(out['uncovered'], [])

    def test_image_unit_without_text_is_anchored_to_the_gap_between_its_neighbours(self):
        units = UNITS[:2] + [{'id': 'img', 'kind': 'image', 'text': 'words read from the picture'}] + UNITS[2:]
        out = linked(units); img = out['units'][2]
        self.assertEqual(img['anchor']['byte_start'], out['units'][1]['anchor']['byte_end_exclusive'])
        self.assertEqual(img['anchor']['byte_end_exclusive'], out['units'][3]['cells'][0]['anchor']['byte_start'])

    def test_text_absent_from_the_source_is_never_guessed_from_scattered_words(self):
        raw = b'<table><tr><td>Change</td><td>Years</td></tr><tr><td>Excluding</td><td>2019</td></tr><tr><td>Impact</td><td>2020</td></tr></table>'
        out = anchor.link(raw, [{'id': 't', 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'rs': 3, 'cs': 1, 'text': 'Change Excluding Impact'}]}])
        self.assertIsNone(out['units'][0]['cells'][0]['anchor']); self.assertEqual(out['units'][0]['cells'][0]['link_error'], 'not_in_source')
        self.assertEqual(anchor.norm(anchor.Visible(raw).at_any([{'byte_start': 15, 'byte_end_exclusive': 21}])), 'Change')

    def test_short_texts_are_placed_between_their_long_neighbours_never_far_ahead(self):
        raw = (b'<p>EXHIBIT 10.3</p><p>SIXTH AMENDMENT TO THE REVOLVING CREDIT AGREEMENT (the "Amendment"), by and among the parent company</p>'
               b'<p>WHEREAS the parties agreed to certain changes to the existing Loan Document, dated as of July 14, 2024 (the "Target")</p>'
               b'<p>NOW, THEREFORE, the Amendment and the Target and every other Loan Document shall be read together as one agreement.</p>')
        units = [{'id': 'syn', 'kind': 'heading', 'text': 'Document'},  # a synthetic title the tool made up
                 {'id': 'a', 'kind': 'text', 'text': 'EXHIBIT 10.3'},
                 {'id': 'b', 'kind': 'text', 'text': 'SIXTH AMENDMENT TO THE REVOLVING CREDIT AGREEMENT (the "'},
                 {'id': 'c', 'kind': 'text', 'text': 'Amendment'},
                 {'id': 'd', 'kind': 'text', 'text': '"), by and among the parent company'},
                 {'id': 'e', 'kind': 'text', 'text': 'WHEREAS the parties agreed to certain changes to the existing Loan Document, dated as of July 14, 2024 (the "'},
                 {'id': 'f', 'kind': 'text', 'text': 'Target'},
                 {'id': 'g', 'kind': 'text', 'text': '")'},
                 {'id': 'h', 'kind': 'text', 'text': 'NOW, THEREFORE, the Amendment and the Target and every other Loan Document shall be read together as one agreement.'}]
        out = anchor.link(raw, units)
        self.assertIsNone(out['units'][0]['anchor']); self.assertEqual(out['units'][0]['link_error'], 'not_in_source')
        starts = [u['anchor']['byte_start'] for u in out['units'][1:]]
        self.assertEqual(starts, sorted(starts))  # every piece sits in reading order
        self.assertEqual(raw[out['units'][3]['anchor']['byte_start']:out['units'][3]['anchor']['byte_end_exclusive']], b'Amendment')
        self.assertEqual(raw[out['units'][6]['anchor']['byte_start']:out['units'][6]['anchor']['byte_end_exclusive']], b'Target')
        self.assertFalse(any(u.get('link_flag') for u in out['units'])); self.assertEqual(out['uncovered'], [])


        out = linked(UNITS[:1] + [{'id': 'h', 'kind': 'text', 'text': 'HIDDEN text'}] + UNITS[1:])
        self.assertIsNone(out['units'][1]['anchor'])

    def test_a_mark_printed_before_or_after_its_text_is_covered_by_the_anchor(self):
        raw = b'<table><tr><td><sup>1</sup>Under the company name of</td><td>Total<sup>(2)</sup></td><td>Same<sup>3</sup> text</td></tr></table>'
        tb = {'id': 't', 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'text': 'Under the company name of', 'markers': ['1']},
                                                     {'r': 0, 'c': 1, 'text': 'Total', 'markers': ['(2)']},
                                                     {'r': 0, 'c': 2, 'text': 'Same text', 'markers': ['3']}]}
        anchor.link(raw, [tb]); v = anchor.Visible(raw)
        self.assertEqual(anchor.squash(v.at(tb['cells'][0]['anchor']['byte_start'], tb['cells'][0]['anchor']['byte_end_exclusive'])), '1Underthecompanynameof')  # mark before
        self.assertEqual(anchor.squash(v.at(tb['cells'][1]['anchor']['byte_start'], tb['cells'][1]['anchor']['byte_end_exclusive'])), 'Total(2)')  # mark after
        self.assertEqual((tb['cells'][2]['anchor'], tb['cells'][2]['link_error']), (None, 'not_in_source'))  # a mark cut out of the middle: the text is not in the source as printed

    def test_a_cells_leading_mark_is_not_taken_by_the_cell_before_it(self):
        raw = b'<table><tr><td><sup>2</sup>Unter der Firma Beispiel AG</td><td>&nbsp;</td><td><sup>2</sup>Under the company name of Example Ltd</td></tr></table>'
        tb = {'id': 't', 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'text': 'Unter der Firma Beispiel AG', 'markers': ['2']},
                                                     {'r': 0, 'c': 2, 'text': 'Under the company name of Example Ltd', 'markers': ['2']}]}
        anchor.link(raw, [tb]); v = anchor.Visible(raw)
        seen = [anchor.squash(v.at(c['anchor']['byte_start'], c['anchor']['byte_end_exclusive'])) for c in tb['cells']]
        self.assertEqual(seen, ['2UnterderFirmaBeispielAG', '2UnderthecompanynameofExampleLtd'])

    def test_marks_before_and_after_the_same_text_are_both_covered(self):
        raw = b'<p><sup>19</sup> million (in the case of the first such notice) or thereafter more than [__]<sup>20</sup> million less</p>'
        u = {'id': 'p', 'kind': 'text', 'text': 'million (in the case of the first such notice) or thereafter more than [__]', 'markers': ['19', '20']}
        anchor.link(raw, [u]); v = anchor.Visible(raw)
        self.assertEqual(anchor.squash(v.at(u['anchor']['byte_start'], u['anchor']['byte_end_exclusive'])), '19million(inthecaseofthefirstsuchnotice)orthereaftermorethan[__]20')

    def test_hidden_text_emitted_by_a_tool_cannot_be_anchored(self):
        out = linked(UNITS[:1] + [{'id': 'h', 'kind': 'text', 'text': 'HIDDEN text'}] + UNITS[1:])
        self.assertIsNone(out['units'][1]['anchor'])

    def test_empty_or_invisible_text_units_get_no_anchor_and_only_pictures_take_the_gap(self):
        out = linked(UNITS[:2] + [{'id': 'e', 'kind': 'text', 'text': ' \u200e\n'}] + UNITS[2:])
        self.assertIsNone(out['units'][2]['anchor']); self.assertEqual(out['units'][2]['link_error'], 'empty')
        self.assertEqual(out['uncovered'], [])

    def test_whitespace_quotes_dashes_and_brackets_come_from_unicode_categories_not_hand_lists(self):
        import unicodedata
        cf = [chr(i) for i in range(0x2000, 0x2070) if unicodedata.category(chr(i)) == 'Cf']  # zero-width/format marks
        self.assertEqual(anchor.squash('a' + ''.join(cf) + 'b'), 'ab')
        self.assertEqual(anchor.norm('x \u2015 y \u2e3a z'), 'x - y - z')              # horizontal bar, two-em dash: Pd
        self.assertEqual(anchor.norm('\u201e q \u201f \u2039 s \u203a "d" \u2018e\u2019 6" 6\u2032'), '"q" \'s\' "d" \'e\' 6" 6\u2032'.replace('"q"', '" q "').replace("'s'", "' s '"))  # same class folds together; single stays single, double stays double, primes untouched
        self.assertEqual(anchor.squash('\u2212 3'), '-3')                                   # minus sign


if __name__ == '__main__':
    unittest.main()
