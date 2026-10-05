"""Visible text of an original with byte spans, and the linker that places tool output back in it (anchor.py)."""
import json
from pathlib import Path
import time
import unittest

from benchmarks.prepare.grader import anchor

HTML = (b'<html><head><title>Sample</title><style>td{color:red}</style></head><body>\n'
        b'<!-- cover -->\n'
        b'<div style="font-weight:bold">Item 2. Management&#8217;s Discussion</div>\n'
        b'<p>S<span>tock</span>holder&nbsp;letter <s>not</s> final.<span style="display:none">HIDDEN <b>deep</b> text</span></p>\n'
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
                 ('<p style="visibility:hidden">Secret <span style="visibility:visible">Shown</span></p>', 'Shown', True),
                 ('<p style="--mode:none;display:var(--mode)">Secret.</p><p>Visible.</p>', None, False),
                 # Codex round 5 (Chrome): an invalid later value does not override a valid earlier one, revert keeps the inherited value, a comment splits tokens
                 ('<p style="display:none;display:nonsense">Secret.</p><p>Visible.</p>', None, False),
                 ('<p style="visibility:hidden;visibility:nonsense">Secret.</p><p>Visible.</p>', None, False),
                 ('<p style="visibility:nonsense">Visible.</p>', None, False),
                 ('<p hidden style="display:nonsense">Secret.</p><p>Visible.</p>', None, False),
                 ('<div style="visibility:hidden"><span style="visibility:revert">Secret.</span></div><p>Visible.</p>', 'Visible.', True),
                 ('<div style="visibility:hidden"><span style="visibility:revert-layer">Secret.</span></div><p>Visible.</p>', 'Visible.', True),
                 ('<p style="display/*x*/:none">Secret.</p><p>Visible.</p>', 'Visible.', True),
                 ('<p style="display:n/**/one">Visible.</p>', None, False),
                 ('<p style="dis/**/play:none">Visible.</p>', 'Visible.', True),
                 ('<p style="opacity:0 !important; opacity:1">Secret.</p><p>Visible.</p>', 'Visible.', True),
                 # Codex round 6 (Chrome, computed opacity): a declaration is the whole `name: value`; NaN/inf are not CSS numbers; opacity is clamped at 0;
                 # a stylesheet rule hidden behind a comment still makes the file uncertain
                 ('<p style="bad display:none">Shown.</p><p>Visible.</p>', 'Shown. Visible.', True),
                 ('<p style="opacity:0">Secret.</p><p>Visible.</p>', 'Visible.', True),
                 ('<p style="opacity:0;opacity:NaN">Secret.</p><p>Visible.</p>', None, False),
                 ('<p style="opacity:-0.1">Secret.</p><p>Visible.</p>', 'Visible.', True),
                 ('<style>.secret{display/**/:none}</style><p class="secret">Secret.</p><p>Visible.</p>', None, False),
                 ('<style>.plain{color:red}</style><p class="plain">Shown.</p>', 'Shown.', True),
                 # Codex round 7 (Chrome): '1.' is no CSS number; a ';' inside a quoted custom value splits nothing; an escaped property name in a
                 # stylesheet still makes the file uncertain; a new <p> closes an open one; a slash on <div> closes nothing; a hidden <br> breaks nothing
                 ('<p style="opacity:0;opacity:1.">Secret.</p><p>Visible.</p>', None, False),
                 ('<p style="--note:\'a;display:none;b\'">Visible.</p>', 'Visible.', True),
                 ('<style>.x{d\\69 splay:none}</style><p class="x">Secret.</p><p>Visible.</p>', None, False),
                 ('<p style="display:none">Secret.<p>Visible.</p>', 'Visible.', True),
                 ('<div style="display:none"/>Secret.</div><p>Visible.</p>', 'Visible.', True),
                 ('<span>12<br hidden>34</span>', '1234', True),
                 ('<span>12<br>34</span>', '12 34', True),
                 ('<p style="d\\69 splay:none">Secret.</p><p>Visible.</p>', 'Visible.', False),  # read as Chrome reads it, but a style string that holds a backslash is no longer certified (R18: CSS escapes follow rules of their own)
                 # a block opened inside an unclosed hidden inline element: the browser closes the <p> and rebuilds the hidden span around the block — not certifiable here
                 ('<p>Shown.<span style="display:none">HIDDEN <div>deep</div> text</span></p>', None, False),
                 # Codex round 8 (Chrome): a new <tr> closes the open <td> and <tr>; a block boundary after a hidden element still separates words;
                 # an escaped ; inside a value is not a separator; text straight inside a table skeleton is not certifiable
                 ('<table><tr style="display:none"><td>Secret.</td></tr><tr><td>Visible.</td></tr></table>', 'Visible.', True),
                 ('<table><tr style="display:none"><td>Secret.<tr><td>Visible.</table>', 'Visible.', True),
                 ('<table><thead style="display:none"><tr><td>Secret.<tbody><tr><td>Visible.</table>', 'Visible.', True),
                 ('<span>Before</span><p hidden>Secret.</p><p>After</p>', 'Before After', True),
                 ('<span>Before</span><p hidden>Secret.<p>After</p>', 'Before After', True),
                 ('<p style="--note:a\\;display:none">Visible.</p>', 'Visible.', False),
                 ('<table>stray<tr><td>Cell</td></tr></table>', None, False)]
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

    def test_a_literal_less_than_sign_is_text_and_keeps_the_arrays_aligned(self):
        # Codex R9-4 (Chrome): a < opens a tag only before a letter or a slash; `Cost < 1% and margin > 5%.` is text, so is a trailing <
        for raw, text in ((b'<p>Cost < 1% and margin > 5%.</p>', ' Cost < 1% and margin > 5%. '), (b'<p>Cost <1% and >5%.</p>', ' Cost <1% and >5%. '),
                          (b'<p>Cost &lt; 1% and margin &gt; 5%.</p>', ' Cost < 1% and margin > 5%. '), (b'<p>A <', ' A <'), (b'<p><s>A</s> <', '  A  <'), (b'<p>1 << 2</p><p>x</p>', ' 1 << 2  x ')):
            v = anchor.Visible(raw)
            self.assertEqual((v.text, v.certain), (text, True), raw)
            runs = [v.at(a, b) for a, b in v.struck_runs()]  # the strike flags stay aligned with the characters on every path
            self.assertEqual(runs, ['A'] if b'<s>' in raw else [], raw)
        self.assertEqual(anchor.Visible(b'<p>a</p><b>bold</b> <br/>x').text, ' a bold  x')  # real tags still are tags
        for raw in (b'<div hidden>Secret < 1</div><p>Shown</p>', b'<div style="display:none">Secret < 1</div><p>Shown</p>', b'<div style="visibility:hidden">Secret < 1</div><p>Shown</p>'):
            v = anchor.Visible(raw); self.assertEqual((v.text.strip(), v.certain, v.hidden_chars), ('Shown', True, 8), raw)  # Codex R10-3: a hidden literal < is hidden text like any other

    def test_struck_text_follows_the_cascade_and_the_propagation_rules_chrome_observed(self):
        # Codex R9-2A with headless Chrome: the last declaration wins, a tag's default yields to its own declaration, atomic boxes are not reached,
        # a child's `none` does not cancel a parent's strike; stylesheet rules and reopened formatting elements make struck text uncertain
        struck = lambda raw: ([anchor.Visible(raw).at(a, b) for a, b in anchor.Visible(raw).struck_runs()], anchor.Visible(raw).struck_certain)
        self.assertEqual(struck(b'<s>struck words</s> plain'), (['struck words'], True))
        self.assertEqual([struck(b'<p>x<%s>a</%s>y</p>' % (n, n)) for n in (b'strike', b'del', b's')], [(['a'], True)] * 3)
        # Round 18: struck text is set apart from its neighbours — a boundary at each end of the element, only next to a struck character, and no line break of the page
        # (Chrome's text of each page beside it, and its text once invisible in place for the zero opacity; codex_probes_live/r18/r18_grid3_facts.py, r18_targeted_facts.py)
        read = lambda raw: (anchor.norm(anchor.Visible(raw).text), anchor.Visible(raw).certain)
        self.assertEqual([read(b'<p>x<s>a</s>y</p>'), read(b'<p>x<s>a</s><s>b</s>y</p>'), read(b'<p>x<s></s>y</p>'), read(b'<p>x<s><span style="visibility:hidden">q</span></s>y</p>'), read(b'<p>x<img src="x.png" style="text-decoration:line-through">y</p>')],
                         [('x a y', True), ('x a b y', True), ('xy', True), ('xy', True), ('xy', True)])  # Chrome: xay, xaby, xy, xy, xy
        self.assertEqual([read(b'<p>x<s><span style="display:inline-block">.</span>q</s>y</p>'), read(b'<p>x<s>q<span style="display:inline-block">.</span></s>y</p>')], [('x.q y', True), ('x q.y', True)])  # Chrome: x.qy, xq.y — an inline box is not struck
        self.assertEqual([read(b'<div>x.<s> <div style="visibility:hidden"></div></s>y</div>')[1], read(b'<div>x.<s> <div style="opacity:0"></div></s>y</div>')[1]], [False, False])  # Chrome: x.y — the invisible block has no line to itself; it had one while the strike was read as a line break
        self.assertEqual([read(b'<p>x<s>a<s style="visibility:hidden">q</s>b</s>y</p>'), read(b'<p>x<s>a<span style="display:none"><s>q</s></span>b</s>y</p>')], [('x ab y', True)] * 2)  # an element that shows nothing sets nothing apart inside a struck run
        self.assertEqual([anchor.Visible(raw).struck_certain for raw in (b'<p>x<s style="visibility:hidden">a<span style="visibility:visible">b</span></s>y</p>', b'<p>x<span style="visibility:hidden">a<span style="visibility:visible">b</span></span>y</p>', b'<p>x<s style="visibility:hidden">a<b>q</b></s>y</p>')], [False, True, True])  # shown again inside invisible struck text: its strike is not certified (what stays invisible there changes nothing)
        self.assertEqual([anchor.Visible(raw).certain for raw in (b'<style a="b"c>p{color:red}</style><p>x</p>', b'<span style="display:inline-flex"> <b>a</b></span>')], [False, True])  # a sheet behind a tag that is not plain is not read (and stops nothing); white space alone before any character
        v = anchor.Visible(b'<p>x<s>a</s>y</p>'); raw = b'<p>x<s>a</s>y</p>'; self.assertEqual([raw[v.starts[i]:v.ends[i]] for i, c in enumerate(v.text) if c == ' ' and 0 < i < len(v.text) - 1 and v.text[i - 1] != ' ' and v.text[i + 1] != ' '], [b'<s>', b'</s>'])  # each boundary stands for its tag's bytes
        self.assertEqual(struck(b'<span style="text-decoration: line-through; text-decoration: none">plain</span>'), ([], True))
        self.assertEqual(struck(b'<span style="text-decoration: line-through; text-decoration-line: none">plain</span>'), ([], True))
        self.assertEqual(struck(b'<s style="text-decoration:none">plain</s>'), ([], True))
        self.assertEqual(struck(b'<s><span style="text-decoration: none">still struck</span></s>'), (['still struck'], True))
        self.assertEqual(struck(b'<s>x <span style="display:inline-block">atomic</span></s>'), (['x'], True))
        self.assertEqual(struck(b'<s>x<br><span style="float:left">floated</span></s>'), (['x'], True))  # a float on a line of its own
        self.assertEqual(struck(b'<s>x <span style="float:left">floated</span></s>'), (['x'], False))  # beside a word on its line the page sets it by its offsets: nothing is certified from that reading (R18)
        self.assertEqual(struck(b'<table style="text-decoration:line-through"><tr><td>cell words</td></tr></table>'), (['cell words'], True))
        self.assertEqual(struck(b'<span style="TEXT-DECORATION: LINE-THROUGH !important">loud</span>'), (['loud'], True))
        self.assertEqual(struck(b'<style>.gone{text-decoration:line-through}</style><span class="gone">by class</span>')[1], False)
        self.assertEqual(struck(b'<style>a{text-decoration:none}</style><s>x</s>')[1], False)  # Codex R10-1: a sheet rule can remove a strike, so a struck run is not certified...
        self.assertTrue(anchor.Visible(b'<style>a{text-decoration:none}</style><s>x</s>').plain_certain)  # ...but "nothing struck here" still is (that rule cannot add one)
        self.assertEqual((anchor.Visible(b'<style>.x{text-decoration:line-through}</style><p>y</p>').plain_certain, anchor.Visible(b'<style>.x{text-decoration:line-through}</style><p>y</p>').struck_certain), (False, False))
        self.assertEqual(struck(b'<s style="text-decoration:revert">kept</s>'), (['kept'], True))  # Chrome: revert restores the tag's default
        self.assertEqual(struck(b'<s style="text-decoration:initial">plain</s>'), ([], True))
        self.assertEqual(struck(b'<s style="text-decoration:bogus">x</s>')[1], False)  # an unevaluated value: uncertain, never a guess
        self.assertEqual(struck(b'<p style="text-decoration:line-through;text-decoration:bogus">x</p>'), (['x'], False))  # the resolved declaration stands, the file stays uncertain
        self.assertEqual(struck(b'<s style="text-decoration:line-through none">x</s>'), (['x'], True))  # invalid (none stands alone): dropped, the tag's default stands (R11-1 grammar)
        self.assertEqual(struck(b'<p><s>a b</p><p>next</p>')[1], False)  # the browser reopens the <s> in the next paragraph
        self.assertEqual(struck(b'<s style="text-decoration: var(--d)">x</s>')[1], False)

    def test_decoration_grammar_drops_invalid_declarations_and_inherit_copies_the_parents_own_line(self):
        # Codex R11-1 with headless Chrome: a style keyword in the line longhand, two styles or a repeated line keyword invalidate the declaration (dropped,
        # no uncertainty); an invalid later declaration leaves the earlier one in force; inherit copies the parent's own line even into an atomic box;
        # a sheet's inherit can add a strike, so neither reading of such a file is certified
        struck = lambda raw: ([anchor.Visible(raw).at(a, b) for a, b in anchor.Visible(raw).struck_runs()], anchor.Visible(raw).struck_certain, anchor.Visible(raw).plain_certain)
        self.assertEqual(struck(b'<p style="text-decoration-line:line-through solid">not</p>'), ([], True, True))
        self.assertEqual(struck(b'<p style="text-decoration:line-through solid dotted">not</p>'), ([], True, True))
        self.assertEqual(struck(b'<p style="text-decoration:line-through line-through">not</p>'), ([], True, True))
        self.assertEqual(struck(b'<p style="text-decoration:line-through;text-decoration-line:underline dotted">not</p>'), (['not'], True, True))
        self.assertEqual(struck(b'<p style="text-decoration:line-through solid">not</p>'), (['not'], True, True))
        self.assertEqual(struck(b'<p style="text-decoration:solid">not</p>'), ([], True, True))  # valid: the line part defaults to none
        self.assertEqual(struck(b'<p style="text-decoration:line-through"><span style="display:inline-block;text-decoration:inherit">not</span></p>'), (['not'], True, True))
        self.assertEqual(struck(b'<p><span style="display:inline-block;text-decoration:inherit">not</span></p>'), ([], True, True))
        self.assertEqual(struck(b'<style>.x{text-decoration:inherit}</style><p style="text-decoration:line-through"><span class="x" style="display:inline-block">not</span></p>')[1:], (False, False))
        self.assertEqual(struck(b'<style>.u{text-decoration:underline dotted}</style><p>y</p>')[1:], (False, True))  # that rule cannot add a strike
        self.assertEqual(struck(b'<p style="text-decoration:line-through red">x</p>')[1:], (False, False))  # a colour: not evaluated, uncertain either way

    def test_xml_text_is_the_strict_parsers_character_data(self):
        # Codex N1: CDATA is literal, references decode to their replacement (sharing the reference's bytes), attributes are not hiding instructions, a broken document certifies nothing
        v = anchor.Visible(b'<r><x><![CDATA[<b>literal</b>]]></x><y hidden="true" style="display:none">10 &amp; &lt; 1</y></r>', xml=True)
        self.assertEqual((anchor.norm(v.text), v.certain, v.plain_certain, v.hidden_chars), ('<b>literal</b>10 & < 1', True, True, 0))  # no space of ours at an element boundary (Codex R12-6)
        self.assertEqual(anchor.Visible(b'<r><note>1<b>2</b>3</note></r>', xml=True).text, '123')
        raw = b'<!DOCTYPE r [<!ENTITY unit "partnership units">]><r><note>10 &unit;</note></r>'; v = anchor.Visible(raw, xml=True)
        self.assertEqual(v.at(raw.index(b'<note>'), raw.index(b'</note>')), '10 partnership units')  # the replacement text sits at the reference's bytes
        self.assertEqual(v.at(raw.index(b'&unit;'), raw.index(b'&unit;') + 6), 'partnership units')
        self.assertEqual((anchor.Visible(b'<r><x>1</x>', xml=True).text, anchor.Visible(b'<r><x>1</x>', xml=True).certain), ('', False))

    def test_whitespace_quotes_dashes_and_brackets_come_from_unicode_categories_not_hand_lists(self):
        import unicodedata
        cf = [chr(i) for i in range(0x2000, 0x2070) if unicodedata.category(chr(i)) == 'Cf']  # zero-width/format marks
        self.assertEqual(anchor.squash('a' + ''.join(cf) + 'b'), 'ab')
        self.assertEqual(anchor.norm('x \u2015 y \u2e3a z'), 'x - y - z')              # horizontal bar, two-em dash: Pd
        self.assertEqual(anchor.norm('\u201e q \u201f \u2039 s \u203a "d" \u2018e\u2019 6" 6\u2032'), '"q" \'s\' "d" \'e\' 6" 6\u2032'.replace('"q"', '" q "').replace("'s'", "' s '"))  # same class folds together; single stays single, double stays double, primes untouched
        self.assertEqual(anchor.squash('\u2212 3'), '-3')                                   # minus sign

    def test_pages_the_browser_printed_are_read_as_it_printed_them_or_not_certified(self):
        # Round 18 mutation check: the scanner's layout rules and lists were held only by browser facts kept outside the repository. These pages were printed by
        # local offline Chrome (fixtures/browser_pages_r18.json: its text, white space folded); each tells the scanner from a one-change variant of it. A page marked
        # certain must be certified and read as Chrome's text (beside an inline table: Chrome's text with the table set as a block; with a zero opacity, a textarea or
        # ix:hidden: Chrome's text of the page rewritten in the browser to the agreed meaning); on the others a variant certified a text Chrome did not print, so the
        # scanner must say it is not sure
        facts = json.loads((Path(__file__).with_name('fixtures') / 'browser_pages_r18.json').read_text(encoding='utf-8'))
        self.assertGreater(len(facts['cases']), 100)
        for c in facts['cases']:
            with self.subTest(source=c['source']):
                v = anchor.Visible(c['source'].encode('utf-8')); self.assertIs(v.certain, c['certain'])
                if c['certain']: self.assertIn(anchor.norm(v.text), (c['browser'], c.get('browser_block_tables')))

    def test_strike_certainty_and_byte_offsets_stand_where_the_page_facts_cannot_show_them(self):
        # Round 18 mutation check: a page's printed text shows neither which bytes a character came from nor whether "struck" / "not struck" is certified
        V = anchor.Visible
        for raw in (b'<p>ab;</p>', b'<p>&;x</p>', b'<p>x &amp</p>'):  # only a complete reference shares its bytes among its characters: text that ends with ';' or holds a lone '&' is read byte by byte
            v = V(raw); self.assertEqual([raw[s:e].decode() for c, s, e in zip(v.text, v.starts, v.ends) if c.strip()], [c for c in v.text if c.strip()], raw)
        v = V(b'<p>a&amp;b</p>'); self.assertEqual([raw for raw in (b'<p>a&amp;b</p>'[s:e] for c, s, e in zip(v.text, v.starts, v.ends) if c == '&')], [b'&amp;'])
        flags = lambda raw: (V(raw).certain, V(raw).struck_certain, V(raw).plain_certain)
        self.assertEqual(flags(b'<body>x</body>'), (True, True, True))
        for style in ('line-through', 'inherit', 'underline line-through'):  # a decoration on the document's own elements is not followed: struck text is then not certified either way, the reading is
            self.assertEqual(flags(b'<body style="text-decoration:%s">x</body>' % style.encode()), (True, False, False), style)
            self.assertEqual(flags(b'<html style="text-decoration:%s"><body>x</body></html>' % style.encode()), (True, False, False), style)
        self.assertEqual((flags(b'<body style="text-decoration:none">x</body>'), flags(b'<body style="text-decoration:underline">x</body>')), ((True, True, True), (True, True, True)))  # one that strikes nothing changes nothing
        self.assertEqual(flags(b'x</body style="text-decoration:line-through">y'), (True, True, True))  # a closing tag's attributes mean nothing
        self.assertEqual(flags(b'<table><tr><td><s>a</td><td>b</td></tr></table>'), (True, False, False))  # a cell that ends with a strike element still open: the reading stands, what is struck after it is not certified
        self.assertEqual(flags(b'<table><s><tr><td>a</td></tr></s></table>'), (True, False, False))  # a strike element the parser moves out of a table
        self.assertEqual(flags(b'<p style="display:var(--x)">a</p><p><s>b</s></p>'), (False, False, False))  # an uncertain reading certifies nothing about strikes, either way
        self.assertEqual(flags(b'<style>s{text-decoration:none}</style><p><s>b</s></p>'), (True, False, True))  # a sheet rule on decorations that cannot add a strike: "struck" is not certified, "not struck" is
        self.assertEqual(flags(b'<style>p{text-decoration:line-through}</style><p>b</p>'), (True, False, False))
        v = V(b'<div style="text-decoration:inherit">x</div>'); self.assertEqual((v.struck_certain, list(v.struck_chars)), (True, [0] * len(v.text)))  # inherit with nothing above to inherit from strikes nothing

    def test_the_line_feed_the_parser_drops_after_a_start_tag_is_not_read(self):
        # Round 18 (random documents, wide:3:8852): the parser ignores a line feed that is the first thing after <pre>, <listing> or <textarea> (HTML tree construction).
        # A <textarea>'s text is not in the browser's page text: these are Chrome's own texts of the element (document.querySelector('textarea').textContent, 2026-10-04)
        V = anchor.Visible; inside = lambda body: V(b'<body>a<textarea>' + body + b'</textarea>b</body>').text[1:-1]
        for body, dom in ((b'\nx', 'x'), (b'\n\nx', '\nx'), (b'\r\nx', 'x'), (b'&#10;x', 'x'), (b'&#13;x', '\rx'), (b' \nx', ' \nx'), (b'x\n', 'x\n'), (b'\n', ''), (b'&NewLine;&amp;', '&')):
            self.assertEqual(inside(body), dom, body)
        for raw, at in ((b'<pre>\nxy</pre>', 6), (b'<pre>\r\nxy</pre>', 7), (b'<pre>&#10;xy</pre>', 10), (b'<listing>\rxy</listing>', 10)):  # what follows the dropped character keeps its own bytes
            v = V(raw); i = v.text.index('x'); self.assertEqual((v.starts[i], v.ends[i], v.starts[i + 1], v.text.strip(' ')), (at, at + 1, at + 1, 'xy'), raw)

    def test_bytes_beyond_ascii_are_certified_only_as_plain_utf8(self):
        # Round 18, independent review of the scanner (W10): the scanner decodes UTF-8, else windows-1252; the browser decodes by the byte-order mark, the <meta>, or a guess
        # of its own. Certified, and read as Chrome reads the same bytes from a local file (2026-10-04, document.characterSet beside each): ASCII whatever is declared,
        # and bytes that are UTF-8 with nothing declared against it. Every one of 22,483 real filing documents is ASCII (r18_census_encoding.py)
        u = '\u00e9t\u00e9 \u2014 \u00a7 x'.encode('utf-8'); V = anchor.Visible
        for raw, certain in ((b'<p>' + u + b'</p>', True),  # Chrome: UTF-8
                             (b'<p>\xc3\xa9</p>', True), (b'<p>' + b'word ' * 1000 + u + b'</p>', True), (b'<p>a\xc2\xa0b</p>', True),  # UTF-8 however short, however late
                             (b'<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8"><p>' + u + b'</p>', True), (b'<meta charset="utf-8"><p>' + u + b'</p>', True), (b"<meta charset = ' utf8'><p>" + u, True),
                             (b'<meta charset="windows-1252"><p>plain</p>', True),  # ASCII: every decoding is the same
                             (b'<p>caf\xe9 \x97 \xa7 x</p>', False),  # not UTF-8 (Chrome: windows-1252, as read here — its guess)
                             (b'\xef\xbb\xbf<p>' + u + b'</p>', False),  # a byte-order mark
                             (b'<meta charset="windows-1252"><p>' + u + b'</p>', False),  # Chrome: windows-1252 — other letters than these
                             (b'<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1"><p>' + u + b'</p>', False), (b'<meta charset=""><p>' + u, False),
                             (b'<meta charset="utf-8"><p>caf\xe9 x</p>', False), (b'\xef\xbb\xbf<p>a\xe9b</p>', False)):  # Chrome: UTF-8 with U+FFFD for the bad byte
            self.assertIs(V(raw).certain, certain, raw[:80])
        self.assertEqual(anchor.norm(V(b'<p>' + u + b'</p>').text), anchor.norm(u.decode('utf-8')))

    def test_a_reference_of_any_length_is_read_and_what_never_ends_is_one_token(self):
        # Round 18, independent review of the scanner (W9, C1, P1): a numeric reference is its digits only (`&#1a;` is U+0001 and then `a;`: not certified, never one reference);
        # one with more digits than Python converts crashed the scan; a tag or a raw-text element that never ends was looked for again from every later `<` (minutes for 100 KB)
        V = anchor.Visible
        for raw, chrome in ((b'<p>x&#1a;y</p>', 'x\x01a;y'), (b'<p>x&#127z;y</p>', 'x\x7fz;y'), (b'<p>x&#x1g;y</p>', 'x\x01g;y')):  # Chrome's text beside each
            v = V(raw); self.assertTrue(not v.certain or v.text.strip() == chrome, raw)
        self.assertEqual([anchor.text_reference(t) for t in ('&#' + '1' * 5000 + ';', '&#' + '0' * 4299 + '65;', '&#x' + '0' * 5000 + '41;', '&#x' + 'f' * 5000 + ';', '&#0;', '&amp;')], ['\ufffd', 'A', 'A', '\ufffd', '\ufffd', '&'])
        for raw in (b'<p>&#' + b'1' * 5000 + b';</p>', b'<p>&#' + b'1' * 5000 + b' x</p>', b'<p><span style="color:&#' + b'1' * 5000 + b';">x</span></p>', b'<textarea>&#' + b'1' * 5000 + b';</textarea>'): V(raw)  # no crash
        self.assertEqual(V(b'<p>a&#' + b'0' * 4299 + b'65;b</p>').text.strip(), 'aAb')
        for source, tokens in (('<p>' + '<a' * 16000, 2), ('<p>' + '<a "x" ' * 16000, 2), ('<p>' + '<template>' * 16000, 2), ('<p>x<script>' + 'var a;<script>' * 9, 3), ('<p>x<a title="y>z', 4)):
            self.assertEqual(len(list(anchor.html_tokens(source))), tokens, source[:30])  # the rest of the source is one token: nothing after it is looked for (the last: a `>` stands inside the open quote, so the text goes on — uncertain either way)
        self.assertEqual([(V(('<p>x' + rest).encode()).text.strip(), V(('<p>x' + rest).encode()).certain) for rest in ('<a href="y', '<script>var a;', '<title>var a;', '<template>t')], [('x', False), ('x', False), ('x', True), ('x', False)])  # (a script's page is not certified since round 19; an unclosed title shows the same reading certified)


    def test_an_attribute_the_scanner_does_not_decode_and_a_box_it_does_not_follow_are_not_certified(self):
        # Round 19 (Codex R18 N1, N2, and the page shape his strike finding led to). Chrome's text or paint beside each (local, offline, 2026-10-05)
        V = anchor.Visible
        for rel in ('&#115;tylesheet', 'style&#115;heet', 'style&#x73;heet', 'style&#115heet'):  # N1: the parser decodes a reference in an attribute, this scanner only in `style`: the link loads a sheet (Chrome prints operafter)
            v = V(f'<link rel="{rel}" href="data:text/css,p%7Bdisplay:none%7D"><span>oper</span><p>ating</p><span>after</span>'.encode()); self.assertEqual((v.certain, v.struck_certain, v.plain_certain), (False, False, False), rel)
        for tag, chrome in (('img', 'A B'), ('iframe', 'A B'), ('embed', 'A B'), ('input', 'AB')):
            for align in ('&#108;eft', 'l&#101;ft', '&#x72;ight'): v = V(f'A<{tag} align="{align}" width="10" height="10">B'.encode()); self.assertTrue(not v.certain or anchor.norm(v.text) == chrome, (tag, align))
        for raw in (b'<link rel="stylesheet" href="x.css"><p>A</p>', b'<link rel="StyleSheet" href="x.css"><p>A</p>'): self.assertFalse(V(raw).certain, raw)
        for raw in (b'<p>A</p>', b'<span style="display:n&#111;ne">X</span>A', b'<p title="A &amp; B">A</p>', b'<link rel="icon" href="x.png"><p>A</p>', b'<a rel="no&amp;follow">A</a>', b'<table><tr><td align="&#108;eft">A</td></tr></table>'):  # the guard is on the two attributes read, nowhere else
            v = V(raw); self.assertEqual((v.certain, anchor.norm(v.text)), (True, 'A'), raw)
        for tag in ('s', 'span', 'del', 'strike'):  # N2: an element with no box of its own paints no line of its own (Chrome's picture of each: plain)
            for dec in ('', ';text-decoration:line-through'):
                v = V(f'<div><{tag} style="display:contents{dec}">net</{tag}></div>'.encode()); self.assertFalse(v.struck_certain and any(v.struck_chars), (tag, dec)); self.assertTrue(v.certain)
        for raw, struck in ((b'<s>net</s>', True), (b'<s style="display:inline">net</s>', True), (b'<s><span style="display:contents">net</span></s>', True),  # painted struck: the line is its parent's
                            (b'<span style="display:contents">net</span>', False), (b'<s style="text-decoration:none">net</s>', False), (b'<s style="display:contents;text-decoration:none">net</s>', False)):
            v = V(raw); self.assertEqual((v.certain, v.struck_certain, v.plain_certain, any(v.struck_chars)), (True, True, True, struck), raw)
        # a writing mode other than its parent's makes an inline a box of its own lines: Chrome drops the white space inside its edges (xnety, where the plain inline prints x net y)
        # and paints none of its parent's strike on it. Not followed, inline or in a sheet, under any of the three names Chrome accepts (it does not list the -epub- one)
        for decl in ('writing-mode:vertical-rl', 'writing-mode:sideways-lr', 'writing-mode:tb-rl', 'writing-mode:horizontal-tb', '-webkit-writing-mode:vertical-lr', '-epub-writing-mode:vertical-rl', 'WRITING-MODE:VERTICAL-RL'):
            self.assertFalse(V(f'<p>x<span style="{decl}"> net </span>y</p>'.encode()).certain, decl); self.assertFalse(V(f'<style>span{{{decl}}}</style><p>x<span> net </span>y</p>'.encode()).certain, decl)
        for decl in ('text-orientation:upright', 'direction:rtl', 'font-family:writing-mode'): v = V(f'<p>x<span style="{decl}"> net </span>y</p>'.encode()); self.assertEqual((v.certain, anchor.norm(v.text)), (True, 'x net y'), decl)  # Chrome: x net y
        for raw, chrome in ((b'<div>x<div style="writing-mode:vertical-rl"> net </div>y</div>', 'x net y'), (b'<div style="writing-mode:vertical-rl">x<span> net </span>y</div>', 'x net y'), (b'<table><tr><td style="writing-mode:vertical-rl">a b</td><td>c</td></tr></table>', 'a b c'),
                            (b'<table><tr><td><div style="rotate:180deg;writing-mode:vertical-rl;width:100%"><p style="margin:0">Total net</p></div></td><td>x</td></tr></table>', 'Total net x')):  # a block reads the same in any writing mode (the last: how a real 10-K turns its table headings)
            v = V(raw); self.assertEqual((v.certain, anchor.norm(v.text)), (True, chrome), raw)
        # a table floated by `align` (the old way, as a picture): Chrome paints none of its parent's strike on it, as on any float
        struck = lambda raw: (lambda v: (v.struck_certain, bool(v.struck_chars[v.text.index('net')])))(V(raw))
        for raw, want in ((b'<s>a <table align="left"><tr><td>net</td></tr></table> b</s>', False), (b'<del>a <table align="RIGHT"><tr><td>net</td></tr></table></del>', False), (b'<s>a <table style="float:left"><tr><td>net</td></tr></table> b</s>', False),
                          (b'<s>a <table align="center"><tr><td>net</td></tr></table> b</s>', True), (b'<s>a <table><tr><td align="left">net</td></tr></table> b</s>', True), (b'<s>a <div align="left">net</div> b</s>', True)):
            self.assertEqual(struck(raw), (True, want), raw)
        self.assertFalse(V(b'<s>a <table align="&#108;eft"><tr><td>net</td></tr></table> b</s>').certain)
        # an instruction a <meta> hands the browser: a content security policy turns style attributes off (Chrome prints abc), a refresh sends it to another page (Chrome then prints
        # that page: 10 becomes 20 — Codex R19 N3; each page in a tab of its own). Neither is followed. The others change no reading (Chrome prints ac under each) and withdraw nothing
        for equiv, content, certain in (('Content-Security-Policy', "style-src 'none'", False), ('content-security-polic&#121;', "style-src 'none'", False), ('CONTENT-SECURITY-POLICY', "default-src 'none'", False),
                                        ('refresh', '0;url=https://review.invalid/new', False), ('Refresh', '100', False), ('re&#102;resh', '0;url=x.htm', False),
                                        ('Content-Security-Policy-Report-Only', "style-src 'none'", True), ('default-style', 'x', True), ('Content-Language', 'en-us', True), ('Content-Style-Type', 'text/css', True),
                                        ('X-UA-Compatible', 'IE=edge', True), ('Pragma', 'no-cache', True), ('Content-Type', 'text/html; charset=utf-8', True), ('content-type', 'text/html;charset=utf-8', True)):
            self.assertIs(V(f'<html><head><meta http-equiv="{equiv}" content="{content}"></head><body><p>a<span style="display:none">b</span>c</p></body></html>'.encode()).certain, certain, equiv)
        self.assertTrue(V(b'<meta name="viewport" content="width=device-width"><meta charset="utf-8"><p>a</p>').certain)
        # a script is not run (Chrome, each page in a tab of its own: the number 10 is printed 99; document.write adds zz; an onerror, an onload and a document set into the page rewrite it):
        # the page that carries one — a script element, an event attribute, a framed document — is not certified
        for raw in (b'<p>Revenue <span id="n">10</span></p><script>document.getElementById("n").textContent="99"</script>', b'<p>a</p><script>document.write("<p>zz</p>")</script><p>b</p>', b'<p>a</p><SCRIPT LANGUAGE="JavaScript">x()</SCRIPT>',
                    b'<p>a<img src="x.png" onerror="this.parentNode.textContent=\'gone\'">b</p>', b'<body onload="document.body.textContent=\'z\'"><p>a</p></body>', b'<div ONCLICK="x()">a</div>',
                    b'<p>a</p><iframe srcdoc="<script>parent.document.body.append(\'zz\')</script>"></iframe>', b'<p>a</p><iframe src="x.html"></iframe>', b'<p>a</p><embed src="x.html">', b'<p>a</p><script type="application/ld+json">{"x": 1}</script>'):
            self.assertFalse(V(raw).certain, raw)
        for raw, chrome in ((b'<p>a</p><iframe></iframe><p>b</p>', 'a b'), (b'<p><a href="javascript:void(0)">a</a> b</p>', 'a b'), (b'<p data-on="x" id="only" title="onclick=1">a</p>', 'a'), (b'<p>a</p><noscript>n</noscript><p>b</p>', 'a b')):  # nothing runs here when the page loads
            v = V(raw); self.assertEqual((v.certain, anchor.norm(v.text)), (True, chrome), raw)
        # a strike that may not be seen (Codex R19 N2; Chrome's picture of each page in the first list is the same with the strike and without). Its colour: a strike takes its own, else
        # its element's text colour (the fill colour where one is given), and the letters inside may be coloured again — a colour that may paint nothing, anywhere in the file, inline or
        # in a sheet, withdraws the strike certificates: `transparent`, an alpha that is not the literal 1 (Chrome reads -1, 0e0, 1e-999 as none), a form not evaluated.
        # Its length: struck letters set on one spot by a negative letter-spacing, or in a box `contain` gives no size, have no line — where struck text stands under such a declaration
        flags = lambda raw: (lambda v: (v.certain, v.struck_certain, v.plain_certain))(V(raw))
        for raw in (b'<p>x <s style="text-decoration-color:transparent">net</s> y</p>', b'<p>x <s style="color:transparent"><span style="color:#000">net</span></s> y</p>', b'<div style="color:rgba(0,0,0,0)">x <s><b style="color:#000">net</b></s> y</div>',
                    b'<p>x <s style="text-decoration-color:rgba(255,0,0,0)">net</s> y</p>', b'<p>x <s style="text-decoration-color:#0000">net</s> y</p>', b'<p>x <s style="text-decoration-color:rgb(0 0 0 / 0)">net</s> y</p>', b'<p>x <s style="COLOR: Transparent">net</s> y</p>',
                    b'<p>x <s style="color:hsla(0,0%,0%,0)"><b style="color:#000">net</b></s> y</p>', b'<p>x <s style="color:rgba(0,0,0,0.5)">net</s> y</p>', b'<div style="text-decoration-color:transparent"><s style="text-decoration-color:inherit">net</s></div>',
                    b'<p>x <s style="-webkit-text-fill-color:transparent"><span style="-webkit-text-fill-color:#000">net</span></s> y</p>', b'<p style="-webkit-text-fill-color:rgba(0,0,0,0)">x <s><span style="-webkit-text-fill-color:black">net</span></s> y</p>',
                    b'<style>s{color:transparent}</style><p>x <s><span style="color:#000">net</span></s> y</p>', b'<style>s{text-decoration-color:transparent}</style><p>x <s>net</s> y</p>', b'<style>s{-webkit-text-fill-color:transparent}</style><p>x <s>net</s> y</p>',
                    b'<p>x <s style="letter-spacing:-1em">net</s> y</p>', b'<div style="letter-spacing:-1em"><s>net</s></div>', b'<p>x <s><span style="letter-spacing:-1em">net</span></s> y</p>', b'<p style="letter-spacing:-9999px">x <s>net</s> y</p>',
                    b'<p>x <s style="font-size:1pt;letter-spacing:-0.6pt">net</s> y</p>', b'<p style="letter-spacing:-1em">x <s><span style="letter-spacing:inherit">net</span></s> y</p>', b'<s><div style="contain:strict">net</div></s>',
                    b'<div style="contain:strict">x <s>net</s> y</div>', b'<style>s{letter-spacing:-1em}</style><s>net</s>', b'<style>s{contain:strict}</style><s>net</s>'):
            self.assertEqual(flags(raw), (True, False, False), raw)
        for alpha in ('-1', '-20%', '-0', '+0', '0e0', '0.0e+2', '1e-999', '0', '0.0', '.0', '0%', '0.001'):  # Chrome paints none of these (his list, and the forms of zero)
            for prop in ('color', 'text-decoration-color'): self.assertEqual(flags(f'<s style="{prop}:rgba(0,0,0,{alpha})"><b style="color:black">net</b></s>'.encode()), (True, False, False), (prop, alpha))
        for raw in (b'<p>x <s style="text-decoration-color:#000000">net</s> y</p>', b'<p>x <s style="color:red">net</s> y</p>', b'<p>x <s style="color:rgba(255,0,0,1)">net</s> y</p>', b'<p>x <s style="color:rgb(255, 0, 0)">net</s> y</p>',
                    b'<p>x <s style="text-decoration-color:currentcolor">net</s> y</p>', b'<p>x <s style="text-decoration-color:initial;color:#0563c1">net</s> y</p>', b'<style>p{color:#333}</style><p>x <s>net</s> y</p>', b'<p style="background-color:transparent">x <s>net</s> y</p>',
                    b'<p>x <span style="text-decoration:line-through;color:#FF0000">net</span> y</p>', b'<p>x <s style="-webkit-text-fill-color:red">net</s> y</p>',  # the colours filings write: painted, certified
                    b'<p>x <s>net</s> <span style="letter-spacing:-1em">y</span></p>', b'<p style="letter-spacing:-.1pt">a</p><p>x <s>net</s> y</p>', b'<p>x <s style="letter-spacing:0.2em">net</s> y</p>', b'<p>x <s style="letter-spacing:normal">net</s> y</p>',
                    b'<div>x <s>net</s> y</div><div style="contain:strict">z</div>', b'<style>p{letter-spacing:.05pt}</style><p>x <s>net</s> y</p>', b'<p>x <s style="word-spacing:-9999px">net</s> y</p>'):  # a spacing that takes no room, or one that does not reach the struck letters (a real redline tightens other runs by a tenth of a point): painted, certified
            self.assertEqual(flags(raw), (True, True, True), raw)
        # where the spacing reaches struck text by a way the open elements do not show (Codex's quick follow-up to R19; Chrome paints no line on `net` in any page of the first list):
        # declared on the page's own elements, which open nothing here; or on a formatting element left open at the end of a paragraph, a list item or a table — the browser
        # opens it again for what follows. The strike certificates go; the text is read as before
        for raw in [f'<{root} style="{style}"><p><s>net</s></p></{root}>' for root in ('html', 'body') for style in ('font-size:60px;letter-spacing:-1em', 'contain:strict')] + \
                   [f'<p><{tag} style="letter-spacing:-1em">one{closing}<s>net</s></p>' for closing in ('</p><p>', '<p>') for tag in ('b', 'i', 'font')] + \
                   [f'<table><{tag} style="letter-spacing:-1em"><tr><td>one</td></tr></table><s>net</s>' for tag in ('b', 'i', 'font')] + \
                   ['<body><p>x <s>net</s> y</p><body style="letter-spacing:-1em">', '<ul><li><font style="letter-spacing:-1em">a<li>x <s>net</s> y</ul>', '<h3><em style="letter-spacing:-1em">a</h3><p>x <s>net</s> y</p>',
                    '<div><a style="letter-spacing:-1em" href="#">a</div><div>x <s>net</s> y</div>']:
            v = V(raw.encode()); self.assertEqual((v.struck_certain, v.plain_certain), (False, False), raw)
        for raw in ('<p><b style="letter-spacing:-1em">one</p><p><s>net</s></p>', '<ul><li><font style="letter-spacing:-1em">a<li>x <s>net</s> y</ul>', '<body style="letter-spacing:-1em"><p>x <s>net</s> y</p></body>'):
            self.assertTrue(V(raw.encode()).certain, raw)  # the words are not in doubt: only the strike is
        for raw in ('<body style="letter-spacing:0.2em"><s>net</s></body>', '<body style="letter-spacing:normal"><p>x <s>net</s> y</p></body>', '<body style="margin:0;font-size:10pt;color:#000"><p>x <s>net</s> y</p></body>', '<p style="letter-spacing:-1em">other</p><p><s>net</s></p>', '<p><b style="letter-spacing:-1em">other</b></p><p><s>net</s></p>',
                    '<div style="contain:strict">other</div><p><s>net</s></p>', '<p><b>one</p><p><s>net</s></p>', '<style>s{letter-spacing:0.2em}</style><p><s>net</s></p>',
                    '<p><span style="letter-spacing:-1em">a</p><p>x <s>net</s> y</p>', '<p><font style="letter-spacing:.1pt">a</p><p>x <s>net</s> y</p>', '<p>x <s>net</s> y</p></body style="letter-spacing:-1em">'):  # Chrome paints the line: a spacing that reaches no struck text, takes no room, ends with its element — or stands on an element the browser does not open again (a span), or on a closing tag
            v = V(raw.encode()); self.assertEqual((v.certain, v.struck_certain, v.plain_certain), (True, True, True), raw)

    def test_an_xml_reading_is_certified_only_complete_and_byte_for_byte(self):
        # Round 19 (Codex R18 N3 and its siblings): the XML reader certified a reading that lacked what an unread external declaration stands for, characters at
        # no bytes at all, characters of a UTF-16 or windows-1252 text at bytes that are not theirs, and crashed on an encoding the parser does not know
        X = lambda raw: anchor.Visible(raw, xml=True)
        for raw in (b'<!DOCTYPE r [<!ENTITY e SYSTEM "file:///not-fetched">]><r>&e;</r>', b'<!DOCTYPE r SYSTEM "https://invalid.example/not-fetched"><r>10</r>', b'<!DOCTYPE r PUBLIC "-//x" "x.dtd"><r>10</r>', b'<!DOCTYPE r SYSTEM ""><r>10</r>', b'<!DOCTYPE r PUBLIC "-//x" ""><r>10</r>',  # nothing external is ever fetched
                    b'<!DOCTYPE r [<!ENTITY x SYSTEM "file:///x"><!ENTITY e "a&x;b">]><r>&e;</r>',
                    b'<!DOCTYPE r [<!ENTITY % p SYSTEM "x.dtd"> %p;]><r>a&e;b</r>', b'<!DOCTYPE r [<!ENTITY % p SYSTEM "x.dtd"> %p; <!ENTITY e "v">]><r>a&e;b</r>', b'<!DOCTYPE r [<!ENTITY % p SYSTEM "x.dtd"> %p;]><r>ab</r>',  # an external parameter entity: left unread, the parser passed over `&e;` in silence (it read "ab")
                    b'<!DOCTYPE r [<!ENTITY % p ""> %p;]><r>a&x;b</r>',  # an entity nothing declares, passed over where the document has parameter entities
                    b'<?xml version="1.0" standalone="yes"?><!DOCTYPE a [<!ENTITY % p "<!ENTITY e \'A\'>"> %p; <!ENTITY e "B">]><a>&e;</a>',  # the parser left `%p;` unread and certified "B"; a parser that reads it prints "A" (libxml2). Read, the parser stops at it (a standalone document may not declare so)
                    b'<!DOCTYPE r [<!ENTITY e "two\nlines">]><r>&e;</r>', b'<!DOCTYPE r [<!ENTITY e "<h>5</h>">]><r>&e;</r>', b'<!DOCTYPE r [<!ENTITY e "a&#38;#10;b">]><r>&e;</r>', b'<!DOCTYPE r [<!ENTITY a "1"><!ENTITY e "x&a;y">]><r>&e;</r>',  # an expansion in several pieces, all at the reference's first byte
                    b'<!DOCTYPE r [<!ENTITY e "">]><r>a&e;b</r>',  # one that expands to nothing: the character before it would be given its bytes too
                    b'<?xml version="1.0" encoding="not-a-real-encoding"?><r>10</r>', b'<?xml version="1.0" encoding="UTF-32"?><r>10</r>', b'<?xml version="1.0" encoding="UTF-7"?><r>10</r>',
                    '<?xml version="1.0" encoding="windows-1252"?><r>€a</r>'.encode('cp1252'), '<?xml version="1.0" encoding="ISO-8859-1"?><r>café</r>'.encode('latin-1')):
            self.assertEqual((X(raw).certain, X(raw).text), (False, ''), raw)
        for enc in ('utf-16-le', 'utf-16-be'):
            for value in ('€a', 'a€', '€1', 'a€b€', '中2', 'ab', 'a'): self.assertFalse(X(f'<?xml version="1.0" encoding="{enc.upper().replace("-LE", "LE").replace("-BE", "BE")}"?><r>{value}</r>'.encode(enc)).certain, (enc, value))
        for raw, text in ((b'<r>10</r>', '10'), (b'<r>1&amp;2</r>', '1&2'), (b'<r><![CDATA[1<2]]></r>', '1<2'), (b'<!DOCTYPE r [<!ENTITY e "shares">]><r>&e; 5 &e;</r>', 'shares 5 shares'), (b'<r xmlns="urn:example"><v>10</v></r>', '10'),
                          (b'<r>a\r\nb\rc\nd&#10;e</r>', 'a\nb\nc\nd\ne'), ('<r>a€b中\U0001f600</r>'.encode('utf-8'), 'a€b中\U0001f600'), (b'\xef\xbb\xbf<r>a\xe2\x82\xac</r>', 'a€'),
                          (b'<?xml version="1.0" encoding="ISO-8859-1"?><r>ab cd</r>', 'ab cd'), (b'<?xml version="1.0" encoding="US-ASCII"?><r>ab</r>', 'ab'),  # ASCII under any declared encoding is its own bytes
                          (b'<!DOCTYPE a [<!ENTITY % p "<!ENTITY e \'A\'>"> %p; <!ENTITY e "B">]><a>&e;</a>', 'A'),  # a parameter entity inside the document is read where it stands: the first declaration of a name binds
                          (b'<!DOCTYPE r [<!ENTITY e SYSTEM "file:///x">]><r>ab</r>', 'ab'), (b'<!DOCTYPE r><r>ab</r>', 'ab')):  # an external entity that is declared and never referred to takes nothing away
            v = X(raw); self.assertEqual((v.certain, v.text), (True, text), raw)
            for c, a, b in zip(v.text, v.starts, v.ends):  # every character is read back from its own bytes, or shares one reference or one line ending
                self.assertTrue(a < b and (raw[a:b] == c.encode('utf-8') or (raw[a:b][:1] == b'&' and raw[a:b][-1:] == b';' and raw[a:b].count(b'&') == 1) or (c == '\n' and raw[a:b] in (b'\r\n', b'\r'))), (raw, c, raw[a:b]))


if __name__ == '__main__':
    unittest.main()
