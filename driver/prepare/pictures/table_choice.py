# Table structure from the picture (Codex real336 review, task 1; development, not adopted). When Chandra and Sonnet read a
# table with the same values but a different structure, each complete reading is put on the picture with the existing position
# check (ideas_20261005/geometry_columns, ported to the checker's own placement): the free OCR's word positions must place every
# cell by its exact text (never a fuzzy or bracket-ignoring match), and rows, columns and headings must fit (status(); routing.py
# uses the same condition). A reading is chosen WHOLE only when
#   (a) it alone fits the picture (GREEN), or
#   (b) both fit and it keeps every number's links of the other (same value, row heading and row label) while adding column
#       headings the other lacks (for example a period row the other set outside its table).
# Otherwise - values differ, neither fits, or both fit with conflicting links - the table stays unresolved. Never mixed.
# Positions support placement, not every word: a reading that lacks words of the other (a dropped qualifier, a heading, a unit or
# period the other holds in its table) is not chosen - their links to its columns would be unproved.
import collections
from . import packets as p, geometry
rc = p.rc

def links(tb):  # each number cell -> (value, column headings, row headings, row label), from the checker's own facts
    F = rc.facts([tb]) or collections.Counter()
    return collections.Counter((f[6], f[7], f[8], f[9]) for f in F.elements() if f[5] == 'data' and any(ch.isdigit() for ch in f[6]))

def refines(a, b):  # a keeps every link of b (same value, row headings, row label) and its column headings include b's
    pool = list(a.elements())
    for v, ch, rh, lab in b.elements():
        m = next((x for x in pool if x[0] == v and x[2] == rh and x[3] == lab and set(ch) <= set(x[1])), None)
        if m is None: return False
        pool.remove(m)
    return True

def status(tb, bb, rec, boxes, known):  # the existing position check, GREEN only when every located cell's text was found exactly
    s, ck = geometry.status(tb, bb, rec, boxes, known)                    # (tiers 1-2); a fuzzy (3) or bracket-ignoring (x.5) match: GREY
    return 'GREY' if s == 'GREEN' and any(c['loc']['tier'] not in (1, 2) for c in ck['cells'] if c['key'] and c.get('loc')) else s

def one_table(html):  # the single table of a reading with its uncertainty, or None
    got = rc.read(html, 'html')
    return dict(got[1][0], uncertain=got[3]) if got[1] and len(got[1]) == 1 else None

def choose(page_html, blocks, i, st, el, rec):  # ('C' | 'S' | None, reason, the two position statuses)
    k = st[i][4]
    if k is None: return None, 'no Sonnet table paired at this place', None
    C, S = one_table(blocks[i]['html']), one_table(el[k]['raw'])
    if C is None or S is None: return None, 'not one table in each reading', None
    lc, ls = links(C), links(S)
    if collections.Counter(x[0] for x in lc.elements()) != collections.Counter(x[0] for x in ls.elements()): return None, 'the readings hold different numbers', None
    covered, rest = [i], collections.Counter(p.toks(el[k]['raw'], 'html')) - collections.Counter(p.toks(blocks[i]['html'], 'html'))
    for step in (-1, 1):                                               # + the neighbouring Chandra blocks whose words Sonnet's table holds
        j = i + step                                                   # (a heading or unit row Chandra set outside its table)
        while 0 <= j < len(blocks) and blocks[j]['box'] and blocks[j]['label'] not in p.VISUAL and blocks[j]['label'] != 'Table':
            w = collections.Counter(p.toks(blocks[j]['html'], 'html'))
            if not w or w - rest: break
            covered.append(j); rest -= w; j += step
    bc = list(blocks[i]['box']); bs = [f([blocks[j]['box'][q] for j in covered]) for q, f in ((0, min), (1, min), (2, max), (3, max))]
    return decide(C, S, bc, bs, page_html, rec, [blocks[j]['html'] for j in covered[1:]])

def decide(C, S, bc, bs, page_html, rec, near=()):  # the positions rule, then: the chosen reading holds every word the other has in
    who, why, st = by_positions(C, S, bc, bs, page_html, rec)            # its area (near: Chandra's neighbouring blocks Sonnet's table holds)
    if not who: return who, why, st
    words = lambda tb: collections.Counter(p.toks('\n'.join(' '.join(c['text'] for c in row) for row in tb['rows']), 'text'))
    other = words(S) if who == 'C' else sum((collections.Counter(p.toks(h, 'html')) for h in near), words(C))
    lack = other - words(C if who == 'C' else S)
    if lack: return None, why + '; but it lacks words of the other: ' + ' '.join(list(lack.elements())[:12]), st
    return who, why, st

def by_positions(C, S, bc, bs, page_html, rec):  # the rule itself, on two tables and their areas (0-1000) on one picture
    lc, ls = links(C), links(S)
    if collections.Counter(x[0] for x in lc.elements()) != collections.Counter(x[0] for x in ls.elements()): return None, 'the readings hold different numbers', None
    boxes = geometry.page_boxes(rec)
    sc = status(C, bc, rec, boxes, geometry.outside_tokens(page_html, bc))
    ss = status(S, bs, rec, boxes, geometry.outside_tokens(page_html, bs))
    if sc == 'GREEN' and ss != 'GREEN': return 'C', "only Chandra's table fits the picture", (sc, ss)
    if ss == 'GREEN' and sc != 'GREEN': return 'S', "only Sonnet's table fits the picture", (sc, ss)
    if sc == ss == 'GREEN':
        if refines(ls, lc) and not refines(lc, ls): return 'S', "both fit; Sonnet's keeps every link of Chandra's and adds headings", (sc, ss)
        if refines(lc, ls) and not refines(ls, lc): return 'C', "both fit; Chandra's keeps every link of Sonnet's and adds headings", (sc, ss)
        return None, 'both fit the picture' + (' with the same number links' if lc == ls else ' but their links conflict'), (sc, ss)
    return None, 'neither fits the picture', (sc, ss)
