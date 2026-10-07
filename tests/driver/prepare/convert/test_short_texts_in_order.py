"""A short text outside tables is placed in the tool's order with the long ones once the text before it has its place (accuracy-fable-1, OGE; Codex's
diagnostic, with the left neighbour's condition): of two signature blocks whose titles read alike, the tool split the first title into short runs and
read the second whole; the long whole title was placed before the short runs and took the first block's title (its order flags followed). A short text
whose left neighbour has no place yet (a table cell, a text not found) still waits for pass 3: there it took an untied table's cell before."""
import unittest

from driver.prepare.convert import anchor


def run(blocks):  # blocks: (source html, [the tool's unit texts]) in source order -> each unit: 'own' (inside its block) or where it stands, and its flag
    raw = ''.join(h for h, _ in blocks).encode(); texts = [t for _, ts in blocks for t in ts]; spans, at = [], 0
    for h, ts in blocks: spans += [(at, at + len(h.encode()))] * len(ts); at += len(h.encode())
    out = anchor.link(raw, [{'id': 'u%d' % i, 'kind': 'text', 'text': t} for i, t in enumerate(texts)], vis=anchor.Visible(raw))['units']
    return [('own' if u.get('anchor') and s <= u['anchor']['byte_start'] < e else (u.get('anchor') or {}).get('byte_start'), u.get('link_flag')) for u, (s, e) in zip(out, spans)]


def signature(name, title, split):  # a signature block; `split`: the tool read the title as two runs, its last two words apart
    head, tail = title.rsplit(' ', 2)[0], ' '.join(title.rsplit(' ', 2)[1:])
    t = ('<p><font>%s </font><font>%s</font></p>' % (head, tail), [head, tail]) if split else ('<p>%s</p>' % title, [title])
    return [('<p>By:</p>', ['By:']), ('<p>/s/ %s</p>' % name, ['/s/ ' + name]), ('<p>Name: %s</p>' % name, ['Name: ' + name]), t]


END = [('<p>[Signature page to the Indenture]</p>', ['[Signature page to the Indenture]'])]
TITLE, CFO = 'Title: Senior Vice President', 'Title: Chief Financial Officer'


class ShortTextsInOrder(unittest.TestCase):
    def test_a_whole_title_stands_at_its_own_block_not_at_an_earlier_split_one(self):  # each failed before: the whole title at the first block, five flags
        for name, blocks in (('the OGE shape', signature('Rachel Redd-Singleton', TITLE, True) + [('<p>ATTEST:</p>', ['ATTEST:'])] + signature('Mark McCoy', TITLE, False)[1:] + END),
                             ('another title, other names', signature('Dana Whitfield-Ortiz', CFO, True) + [('<p>WITNESS:</p>', ['WITNESS:'])] + signature('Al Roe', CFO, False)[1:] + END)):
            with self.subTest(case=name): self.assertEqual(run(blocks), [('own', None)] * len(run(blocks)))

    def test_whole_or_split_titles_in_either_order_read_as_before(self):
        for name, blocks in (('whole, then split', signature('Mark McCoy', TITLE, False) + [('<p>ATTEST:</p>', ['ATTEST:'])] + signature('Rachel Redd-Singleton', TITLE, True)[1:] + END),
                             ('both whole', signature('Rachel Redd-Singleton', TITLE, False) + signature('Mark McCoy', TITLE, False) + END),
                             ('both split', signature('Rachel Redd-Singleton', TITLE, True) + signature('Mark McCoy', TITLE, True) + END),
                             ('a long split title', signature('Ann Lee', 'Title: Executive Vice President and Chief Financial Officer', True) + signature('Bo Li', 'Title: Executive Vice President and Chief Financial Officer', False) + END)):
            with self.subTest(case=name): self.assertTrue(all(w == ('own', None) for w in run(blocks)))

    def test_a_short_text_after_a_cell_with_no_place_yet_waits_for_it(self):  # two copies of a table no adapter names (not tied), each with a heading that reads like a cell
        p0, p1 = '<p>The company reported its consolidated operating results for the year.</p>', '<p>Total revenue for the year rose because volumes and prices both increased.</p>'
        t, h = '<table><tr><td>Total</td><td>5</td></tr></table>', '<p>Total</p>'
        raw = (p0 + t + h + t + h + p1).encode(); vis = anchor.Visible(raw)
        table = lambda i: {'id': 't%d' % i, 'kind': 'table', 'cells': [{'r': 0, 'c': 0, 'rs': 1, 'cs': 1, 'text': 'Total'}, {'r': 0, 'c': 1, 'rs': 1, 'cs': 1, 'text': '5'}]}
        text = lambda s, i: {'id': 'u%d' % i, 'kind': 'text', 'text': s}
        out = anchor.link(raw, [text(p0[3:-4], 0), table(1), text('Total', 2), table(3), text('Total', 4), text(p1[3:-4], 5)], vis=vis)['units']
        own = lambda a: 'no place' if not a else next((k for k, tb in enumerate(vis.tables) if any(x <= a['byte_start'] < y for row in tb for x, y in row)), 'prose')
        self.assertEqual([[own(c['anchor']) for c in u['cells']] if u.get('cells') else own(u['anchor']) for u in out], ['prose', [0, 0], 'prose', [1, 1], 'prose', 'prose'])
        self.assertEqual([(out[k]['anchor'] or {}).get('byte_start') for k in (2, 4)], [raw.index(h.encode()) + 3, raw.rindex(h.encode()) + 3])  # each heading at its own <p>


if __name__ == '__main__':
    unittest.main()
