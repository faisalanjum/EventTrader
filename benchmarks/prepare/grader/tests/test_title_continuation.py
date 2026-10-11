"""A title printed once over a table continued on the next page (title-continuation-20261011, source-first, invented sources). The title is kept
when every table the route lists between the key's own title and its table is the source's own table at its own place, reading the source's own
words inside its own element: preservation only, never proof that the title governs the later part. Equal first rows are neither needed nor enough."""
import re
import unittest

from benchmarks.prepare.grader import grade

H, H2 = b'<h2>Harvest totals</h2>', b'<h2>Seed orders</h2>'
CONT = b'<p>Continued on next page</p><hr style="page-break-after:always"><p>Table continued</p>'
TOK, TR, TD = re.compile(rb'<(h2|p)>(.*?)</\1>|<table>(.*?)</table>'), re.compile(rb'<tr>(.*?)</tr>'), re.compile(rb'<td>(.*?)</td>')


def tab(*rows):
    return b'<table>' + b''.join(b'<tr>' + b''.join(b'<td>' + t + b'</td>' for t in row) + b'</tr>' for row in rows) + b'</table>'


A, B, C = tab([b'Crop', b'Count'], [b'Asters', b'12']), tab([b'Marigolds', b'9']), tab([b'Tulips', b'4'])
SPLIT = H + A + CONT + B  # one table over a page break; the next part does not repeat the header row


def span(m, g):
    return {'byte_start': m.start(g), 'byte_end_exclusive': m.end(g)}


def route(raw):
    """The faithful hand route of an invented source: headings, paragraphs and tables in source order, each cell anchored at its own words."""
    units = []
    for m in TOK.finditer(raw):
        if m.group(1):
            units.append({'id': 'u%d' % len(units), 'kind': 'heading' if m.group(1) == b'h2' else 'text', 'text': m.group(2).decode(), 'anchor': span(m, 2)})
            continue
        cells = [{'r': r, 'c': c, 'rs': 1, 'cs': 1, 'text': d.group(1).decode(), 'anchor': span(d, 1)}
                 for r, tr in enumerate(TR.finditer(raw, m.start(3), m.end(3))) for c, d in enumerate(TD.finditer(raw, tr.start(1), tr.end(1)))]
        units.append({'id': 'u%d' % len(units), 'kind': 'table', 'anchor': span(m, 0), 'source_table': {'claims': 1, 'tag_start': m.start()}, 'cells': cells})
    return units


def title(raw, units, value='9', anchored=True, support=None, pieces=('Harvest totals',)):
    """The table_title verdict for the value's cell in the last table that prints it, through the whole cell check."""
    tb = [u for u in units if u['kind'] == 'table' and any(c['text'] == value for c in u['cells'])][-1]
    v = next(c for c in tb['cells'] if c['text'] == value); n = raw.index(b'Harvest totals')
    t = {'key_id': 'syn/title', 'file_id': 'syn/t.htm', 'format': 'cell/htm', 'type': 'cell', 'split': 'development', 'anchor': v['anchor'], 'table_anchor': tb['anchor'],
         'alternatives': {}, 'excluded': set(), 'support': {'table_title': support or {'anchors': [{'byte_start': n, 'byte_end_exclusive': n + 14}]}} if anchored else {},
         'fields': {'printed_value': value, 'display_value': value, 'value_kind': 'number', 'sign': 'positive', 'footnote_markers': [], 'periods': None, 'table_title': list(pieces)}}
    g = grade.Grader(t, grade.RouteFile({'file_id': t['file_id'], 'units': units}, raw)); g.grade_cell()
    return next((r['verdict'], r.get('reason')) for r in g.rows if r['check'] == 'table_title')


def moved(units, i, j):
    """The route lists unit i at position j (a reordering the source does not print)."""
    out = [u for k, u in enumerate(units) if k != i]; out.insert(j, units[i]); return out


class TitleOverAPageBreak(unittest.TestCase):
    def test_a_title_kept_over_a_page_break_without_a_repeated_header(self):
        self.assertFalse(grade.continued(route(SPLIT)[1], route(SPLIT)[-1]))  # the parts share no first row
        self.assertEqual(title(SPLIT, route(SPLIT)), ('pass', None))

    def test_a_repeated_header_part_still_passes(self):
        raw = H + A + CONT + tab([b'Crop', b'Count'], [b'Marigolds', b'9'])
        self.assertEqual(title(raw, route(raw)), ('pass', None))

    def test_every_later_part_of_a_table_over_several_pages_keeps_the_title(self):
        raw = SPLIT + CONT + C
        self.assertEqual(title(raw, route(raw), '4'), ('pass', None))
        changed = route(raw); changed[4]['cells'][0] = dict(changed[4]['cells'][0], text='Roses')  # the middle part misreads one cell: it moves nothing
        self.assertEqual(title(raw, changed, '4'), ('pass', None))
        self.assertEqual(grade.gates_for_file(grade.RouteFile({'file_id': 'syn/t.htm', 'units': changed}, raw), 'OK')['dishonest'], 1)  # the misreading is the honesty gate's fact, never silent

    def test_a_missing_or_changed_title_still_fails(self):
        units = route(SPLIT)
        self.assertEqual(title(SPLIT, units[1:]), ('fail', 'missing'))
        self.assertEqual(title(SPLIT, [dict(units[0], text='Unrelated tools')] + units[1:]), ('fail', 'text'))

    def test_a_table_from_elsewhere_listed_between_displaces_the_title(self):
        raw = SPLIT + H2 + tab([b'Crop', b'Count'], [b'Peonies', b'3'])
        units = route(raw)
        self.assertEqual(title(raw, units), ('pass', None))  # the source's own order: the later table stands after this one
        self.assertEqual(title(raw, moved(units, 6, 2)), ('fail', 'placement'))  # listed between the title and its table; its source place is after

    def test_a_title_moved_before_an_earlier_table_fails(self):
        raw = A + H + B
        units = route(raw)
        self.assertEqual(title(raw, units), ('pass', None))  # the source's own order: nothing between the title and its table
        self.assertEqual(title(raw, moved(units, 1, 0)), ('fail', 'placement'))  # the title listed before a table the source prints before it

    def test_a_part_not_bound_inside_its_own_element_proves_nothing(self):
        units = route(SPLIT); a = units[1]; i = SPLIT.index(b'Marigolds')
        unbound = dict(a, cells=[dict(a['cells'][2], anchor=None)] + a['cells'][:2] + a['cells'][3:])
        self.assertEqual(title(SPLIT, units[:1] + [unbound] + units[2:]), ('fail', 'placement'))
        foreign = dict(a, cells=[dict(a['cells'][2], text='Marigolds', anchor={'byte_start': i, 'byte_end_exclusive': i + 9})] + a['cells'][:2] + a['cells'][3:])  # reads the next part's words
        self.assertEqual(title(SPLIT, units[:1] + [foreign] + units[2:]), ('fail', 'placement'))

    def test_a_nested_table_between_or_holding_the_value_is_read_by_its_own_element(self):
        inner = tab([b'Asters', b'12']); raw = H + b'<table><tr><td>Region</td><td>' + inner + b'</td></tr></table>' + CONT + B
        o, i = raw.index(b'<table>'), raw.index(inner); oe = raw.index(b'</table></td>') + len(b'</table></td></tr></table>')
        at = lambda s: {'byte_start': raw.index(s), 'byte_end_exclusive': raw.index(s) + len(s)}
        outer = {'id': 'o', 'kind': 'table', 'anchor': {'byte_start': o, 'byte_end_exclusive': oe}, 'source_table': {'claims': 1, 'tag_start': o},
                 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Region', 'anchor': at(b'Region')}, {'r': 0, 'c': 1, 'rs': 1, 'cs': 1, 'text': '', 'anchor': None, 'tables': ['n']}]}
        nested = {'id': 'n', 'kind': 'table', 'anchor': {'byte_start': i, 'byte_end_exclusive': i + len(inner)}, 'source_table': {'claims': 1, 'tag_start': i},
                  'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Asters', 'anchor': at(b'Asters')}, {'r': 0, 'c': 1, 'rs': 1, 'cs': 1, 'text': '12', 'anchor': at(b'12')}]}
        rest = [u for u in route(raw) if u['kind'] != 'table' or u['anchor']['byte_start'] > oe]  # the heading, the two paragraphs and the next part
        units = rest[:1] + [outer, nested] + rest[1:]
        self.assertEqual(title(raw, units), ('pass', None))  # the outer table and its nested table stand at their own places between
        self.assertEqual(title(raw, units, '12'), ('fail', 'placement'))  # a value inside the nested table: the outer table encloses it, not before it — no new nested-scope credit (today's outcome)
        self.assertEqual(title(raw, units[:1] + [outer, dict(nested, cells=[dict(nested['cells'][0], anchor=at(b'Marigolds'), text='Marigolds')] + nested['cells'][1:])] + units[3:]), ('fail', 'placement'))  # a nested cell reading words outside its own element

    def test_an_uncertain_reading_or_a_title_found_by_text_alone_proves_nothing(self):
        raw = b'<style>.gone{display:none}</style>' + SPLIT  # a rule on a hiding property (unused here): the scanner certifies no reading
        self.assertFalse(grade.RouteFile({'file_id': 'syn/t.htm', 'units': []}, raw).vis.certain)
        self.assertEqual(title(raw, route(raw)), ('fail', 'placement'))  # stylesheet rules the scanner does not read: the part's reading is not proved
        self.assertEqual(title(SPLIT, route(SPLIT), anchored=False), ('fail', 'placement'))  # no key anchor: the title occurrence itself is not proved


def two_places(raw, governing=True):
    """The key's search support for 'Harvest totals' printed twice: both listed places, the second declared governing (or plain anchors, no governing)."""
    o1, o2 = raw.index(b'Harvest totals'), raw.rindex(b'Harvest totals')
    if not governing: return {'anchors': [{'byte_start': o1, 'byte_end_exclusive': o1 + 14}, {'byte_start': o2, 'byte_end_exclusive': o2 + 14}]}
    return {'pieces': [{'text': 'Harvest totals', 'byte_ranges': [[o1, o1 + 14], [o2, o2 + 14]], 'governing': [[o2, o2 + 14]]}]}


class GoverningOccurrence(unittest.TestCase):
    """Root's decision (title-governing-20261011; grader DESIGN §3: a listed search occurrence counts for preservation, the governing one for
    association): the title's carriers come from the key's governing places; plain anchors keep today's reading."""
    def test_the_faithful_twin_keeping_both_titles_passes_by_its_governing_place(self):  # A1 twin
        raw = H + A + H + B
        self.assertEqual(title(raw, route(raw), support=two_places(raw)), ('pass', None))

    def test_a_lost_governing_place_fails_even_when_an_earlier_equal_title_survives(self):  # A1
        raw = H + A + H + B; units = route(raw)
        self.assertEqual(title(raw, units[:2] + units[3:], support=two_places(raw)), ('fail', 'missing'))  # the governing place is gone; the first table's equal title is no carrier

    def test_a_changed_non_governing_copy_does_not_decide_the_title(self):
        raw = H + A + H + B; units = route(raw)
        self.assertEqual(title(raw, [dict(units[0], text='Harvest totalz')] + units[1:], support=two_places(raw)), ('pass', None))  # that copy's own loss stays its own duty

    def test_plain_anchors_keep_todays_reading(self):  # decision 2: no governing information, no guessed nearest place
        raw = H + A + H + B; units = route(raw)
        self.assertEqual(title(raw, units, support=two_places(raw, governing=False)), ('fail', 'text'))  # both listed places read as one title, as today
        self.assertEqual(title(raw, units[:2] + units[3:], support=two_places(raw, governing=False)), ('fail', 'placement'))  # the later place lost: the source-order allowance refuses (lost listed place)

    def test_every_governing_piece_of_a_two_piece_title_must_match(self):
        raw = b'<h2>Garden report</h2>' + SPLIT; g, h = raw.index(b'Garden report'), raw.index(b'Harvest totals')
        support = {'pieces': [{'text': 'Garden report', 'byte_ranges': [[g, g + 13]], 'governing': [[g, g + 13]]}, {'text': 'Harvest totals', 'byte_ranges': [[h, h + 14]], 'governing': [[h, h + 14]]}]}
        two = lambda units: title(raw, units, support=support, pieces=['Garden report', 'Harvest totals'])
        self.assertEqual(two(route(raw)), ('pass', None))  # both pieces at their governing places before the first part
        self.assertEqual(two(route(raw)[1:]), ('fail', 'text'))  # the first piece lost: the remaining carrier does not read the whole title


class Counterexamples(unittest.TestCase):
    """OCR's independent public challenge (public_title_continuation_challenge_v1, A2-A3; A1 is in GoverningOccurrence), each with its faithful twin."""

    def test_one_source_table_split_by_the_route_is_no_table_between(self):  # A2, A3
        raw = H + tab([b'Crop', b'Count'], [b'Asters', b'12'], [b'Marigolds', b'9'])
        whole = route(raw); t = whole[1]; cut = raw.index(b'<tr><td>Marigolds')
        self.assertEqual(title(raw, whole), ('pass', None))  # twin: the source's one table
        first = dict(t, anchor={'byte_start': t['anchor']['byte_start'], 'byte_end_exclusive': cut}, cells=t['cells'][:4])
        second = dict(t, id='u2', anchor={'byte_start': cut, 'byte_end_exclusive': t['anchor']['byte_end_exclusive']}, cells=[dict(c, r=0) for c in t['cells'][4:]])
        twice = dict(t['source_table'], claims=2)
        self.assertEqual(title(raw, [whole[0], dict(first, source_table=twice), dict(second, source_table=twice)]), ('fail', 'placement'))  # A2: one source table claimed twice
        self.assertEqual(title(raw, [whole[0], first, dict(second, source_table={'claims': 1, 'tag_start': 0})]), ('fail', 'placement'))  # A3: a forged distinct tag the source has no table at


if __name__ == '__main__':
    unittest.main()
