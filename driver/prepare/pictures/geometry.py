# Table positions on the picture (from ideas_20261005/geometry_columns: geom.py, and plant.py's status()): the free OCR's
# word boxes place every cell of a reading's table, then rows, columns and headings must fit. Used by table_choice.
import collections, copy, difflib, itertools, re, statistics as st
from . import rowcheck as rc

TAG = re.compile(r'<div data-bbox="([\d.\s]+)" data-label="([^"]*)"[^>]*>')

def outside_tokens(html, skip_bb=None):
    """Tokens of the text Chandra set outside tables (titles, notes); blocks whose centre is inside skip_bb (0-1000) are left out."""
    ms = list(TAG.finditer(html)); out = set()
    for i, m in enumerate(ms):
        inner = html[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(html)]
        bb = [float(v) for v in m.group(1).split()]
        if skip_bb and skip_bb[0] <= (bb[0] + bb[2]) / 2 <= skip_bb[2] and skip_bb[1] <= (bb[1] + bb[3]) / 2 <= skip_bb[3]: continue
        for line in rc.read(inner)[2]: out |= set(toks(line))
    return frozenset(out)

def place(tb):
    """Cells on the grid by the checker's own placement (rowcheck.placed: row groups, spans, roles), with a map of the slots each
    covers; (None, None) when the checker cannot place the table as declared. Ported Oct 6 (Codex support review): one placement rule."""
    cells = rc.placed(tb)
    if cells is None: return None, None
    at = {}
    for x in cells:
        x['alone'] = False                                            # (the old lone-section-label fold is gone from the checker)
        for dr in range(x['rs']):
            for dc in range(x['cs']): at[(x['r'] + dr, x['c'] + dc)] = x
    return cells, at

# ---------------------------------------------------------------- boxes
def toks(text, strip='$'):
    return [t for t in (t.strip(strip) for t in rc._TOKEN.findall(rc.norm(rc.plain(text)))) if t and t not in ('.', ',', '..')]

def fracs(t):
    lens = [len(x) for x in t]; tot = sum(lens) + max(len(lens) - 1, 0); out, acc = [], 0
    for l in lens: out.append((acc / tot, (acc + l) / tot)); acc += l + 1
    return out

class Box:
    __slots__ = ('t', 't2', 'x0', 'y0', 'x1', 'y1', 'src', 'id', 'raw', 'frac')
    def __init__(s, raw, pts, src, id_):
        xs, ys = pts[0::2], pts[1::2]
        s.x0, s.x1, s.y0, s.y1 = min(xs), max(xs), min(ys), max(ys); s.src, s.id, s.raw = src, id_, raw
        s.t, s.t2 = toks(raw), toks(raw, '()$')
        s.frac = fracs(s.t)
    @property
    def yc(s): return (s.y0 + s.y1) / 2
    @property
    def xc(s): return (s.x0 + s.x1) / 2

def page_boxes(rec):
    return {src: [Box(b['t'], b['box'], src, i) for i, b in enumerate(rec[src])] for src in ('pp', 'ox')}

def inside(b, area):
    return area[0] <= b.xc <= area[2] and area[1] <= b.yc <= area[3]

def area_of(bb, W, H, margin=0.012):
    return (bb[0] / 1000 * W - margin * W, bb[1] / 1000 * H - margin * H, bb[2] / 1000 * W + margin * W, bb[3] / 1000 * H + margin * H)

# ---------------------------------------------------------------- locate a text among boxes
FOOT = re.compile(r'^\(\d{1,2}\)?$')

def sub_extent(b, i, n):
    f0, f1 = b.frac[i][0], b.frac[i + n - 1][1]
    return (b.x0 + (b.x1 - b.x0) * f0, b.y0, b.x0 + (b.x1 - b.x0) * f1, b.y1)

def union(bs):
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))

def chains(T, boxes):
    """Boxes whose whole token lists are consecutive slices of T, neighbours in space (same line, or the next line)."""
    res = []
    def near(a, b):
        h = max(a.y1 - a.y0, b.y1 - b.y0)
        dy = abs(a.yc - b.yc)
        if dy <= 0.35 * h: return -0.5 * h <= b.x0 - a.x1 <= 3 * h   # same line: b follows a to the right
        return 0 < b.yc - a.yc <= 2.2 * h and (abs(a.xc - b.xc) <= 0.3 * (a.x1 - a.x0 + b.x1 - b.x0) or abs(a.x0 - b.x0) <= 0.8 * h)   # next line: centred under, or left-aligned with
    def rec(j, chain):
        if len(res) > 8: return
        if j == len(T): res.append(chain); return
        for b in boxes:
            if b in chain or not b.t or j + len(b.t) > len(T) or b.t != T[j:j + len(b.t)]: continue
            if chain and not near(chain[-1], b): continue
            rec(j + len(b.t), chain + [b])
    rec(0, [])
    return res

def fuzzy_chains(T, boxes):
    """Words (letters only) alike to 85% in one PP box or in boxes on consecutive lines (a wrapped label), the numbers of the text exactly the same."""
    isnum = lambda t: any(ch.isdigit() for ch in t)
    words = lambda t: ' '.join(w for w in t if w.isalpha()); nums = lambda t: sorted(w for w in t if isnum(w) and len(w) >= 2 and not FOOT.match(w))
    s = words(T); res = []
    if len(s) < 14: return res
    like = lambda a, b: difflib.SequenceMatcher(None, a, b).ratio()
    for b0 in boxes:
        w0 = words(b0.t)
        if not w0 or like(w0, s[:len(w0) + 2]) < 0.85: continue
        cur, best = [b0], None
        while True:
            tk = [t for b in cur for t in b.t]; w = words(tk); r_ = like(w, s)
            if r_ >= 0.85 and nums(tk) == nums(T) and (best is None or r_ >= best[0]): best = (r_, list(cur))
            if len(cur) >= 6 or len(w) >= len(s) + 3: break
            last = cur[-1]; h = last.y1 - last.y0
            nxt = [b for b in boxes if b not in cur and 0.5 * h <= b.yc - last.yc <= 2.2 * h and abs(b.x0 - last.x0) <= 4 * h and words(b.t)]
            nxt = [b for b in nxt if like(w + ' ' + words(b.t), s[:len(w) + 1 + len(words(b.t)) + 2]) >= 0.85]
            if not nxt: break
            cur.append(min(nxt, key=lambda b: b.yc - last.yc))
        if best: res.append(dict(ext=union([(b.x0, b.y0, b.x1, b.y1) for b in best[1]]), src='pp', tier=3, ids=tuple(('pp', b.id) for b in best[1])))
    return res

def candidates(T, area_pp, area_ox, fuzzy=True, relaxed=False, need=1):
    """Places the token sequence T can be seen, by tier (first tier that holds at least `need` places wins; else the largest found):
    1 inside one PP box (or a chain of PP boxes); 2 OnnxTR words (chains); 3 a long text read with small slips in one PP box."""
    n = len(T); isnum = lambda t: any(ch.isdigit() for ch in t)
    if relaxed:
        area_pp = [copy.copy(b) for b in area_pp]; area_ox = [copy.copy(b) for b in area_ox]
        for b in area_pp + area_ox: b.t = b.t2; b.frac = fracs(b.t2)
    ex = lambda b: (b.x0, b.y0, b.x1, b.y1)
    t1 = []
    for b in area_pp:
        if b.t == T: t1.append(dict(ext=ex(b), src='pp', tier=1, ids=(('pp', b.id),)))
        elif n == 1 and isnum(T[0]) and len(b.t) == 2 and T[0] in b.t and len(b.t[1 - b.t.index(T[0])]) == 1 and not b.t[1 - b.t.index(T[0])].isdigit():   # '$ 607.3' read as 's 607.3'; '523.6 $' as '523.6 S'
            t1.append(dict(ext=sub_extent(b, b.t.index(T[0]), 1), src='pp', tier=1, ids=(('pp', b.id),)))
        elif n == 1 and isnum(T[0]) and len(b.t) > 1 and all(isnum(t) for t in b.t) and T[0] in b.t:                      # two cells fused in one box
            t1.append(dict(ext=sub_extent(b, b.t.index(T[0]), 1), src='pp', tier=1, ids=(('pp', b.id),), fused=True))
    if n > 1 and len(t1) < need:
        t1 += [dict(ext=union([ex(b) for b in ch]), src='pp', tier=1, ids=tuple(('pp', b.id) for b in ch)) for ch in chains(T, area_pp)]
    tiers = [t1]
    if len(t1) < need: tiers.append([dict(ext=union([ex(b) for b in ch]), src='ox', tier=2, ids=tuple(('ox', b.id) for b in ch)) for ch in chains(T, area_ox)])
    if fuzzy and not any(tiers):   # a long text read with small slips (a footnote mark, a letter), over one or several lines
        tiers.append(fuzzy_chains(T, area_pp))
    def dedupe(C):   # the same text found twice in nearly the same place (two chains over one wrapped label)
        keep = []
        for c in C:
            a = c['ext']
            if not any(max(0, min(a[2], k['ext'][2]) - max(a[0], k['ext'][0])) * max(0, min(a[3], k['ext'][3]) - max(a[1], k['ext'][1])) > 0.5 * min((a[2] - a[0]) * (a[3] - a[1]), (k['ext'][2] - k['ext'][0]) * (k['ext'][3] - k['ext'][1])) for k in keep): keep.append(c)
        return keep
    tiers = [dedupe(t) for t in tiers]
    for t in tiers:
        if len(t) >= need: return t
    return max(tiers, key=len)

DASH = set('-—–−_')

def lines_order(C):
    """Candidates in reading order: line by line (a new line when the vertical centre moves by more than half a text height), left to right."""
    C = sorted(C, key=lambda c: (c['ext'][1] + c['ext'][3]) / 2); lines, cur = [], []
    for c in C:
        yc, h = (c['ext'][1] + c['ext'][3]) / 2, c['ext'][3] - c['ext'][1]
        if cur and yc - st.mean((d['ext'][1] + d['ext'][3]) / 2 for d in cur) > 0.5 * h: lines.append(cur); cur = []
        cur.append(c)
    if cur: lines.append(cur)
    return [c for ln in lines for c in sorted(ln, key=lambda c: c['ext'][0])]

def locate(cells, bb, W, H, boxes, fuzzy=True, margin=0.012):
    """Put every non-empty cell on the picture: the free tools' box(es) holding exactly its text inside the table's area.
    A text written k times with k places seen is placed in reading order (grid order = reading order)."""
    area = area_of(bb, W, H, margin)
    pp = [b for b in boxes['pp'] if inside(b, area)]; ox = [b for b in boxes['ox'] if inside(b, area)]
    groups = collections.defaultdict(list)
    for x in cells:
        x['loc'] = None; x['why_not'] = None
        if x['key']: groups[tuple(toks(x['key']))].append(x)
    pending, later = [], []
    def settle(cs, C):
        if not C:
            for x in cs: x['why_not'] = 'not-seen'
        elif len(C) < len(cs):
            for x in cs: x['why_not'] = 'seen-fewer-than-written'
        elif len(C) == len(cs):
            for x, c in zip(cs, lines_order(C)): x['loc'] = c
        else: pending.append((cs, C))
    for T, cs in groups.items():
        k = cs[0]['key']; T = list(T)
        filler = all(t in DASH or t == '$' for t in rc._TOKEN.findall(k))
        if not T or filler:
            for x in cs: x['why_not'] = 'filler'
            continue
        C = candidates(T, pp, ox, fuzzy, need=len(cs))
        cs.sort(key=lambda x: (x['r'], x['c']))
        if len(C) < len(cs): later.append((T, cs, k)); continue
        settle(cs, C)
    taken = [x['loc']['ext'] for x in cells if x['loc']] + [c['ext'] for cs_, C_ in pending for c in C_]   # where the first pass put cells
    def free(b):
        a = (b.x0, b.y0, b.x1, b.y1)
        return not any(max(0, min(a[2], t[2]) - max(a[0], t[0])) * max(0, min(a[3], t[3]) - max(a[1], t[1])) > 0.5 * min((a[2] - a[0]) * (a[3] - a[1]), (t[2] - t[0]) * (t[3] - t[1])) for t in taken)
    for T, cs, k in later:   # second chance: brackets ignored (a '(2.2)' is not the same text as '2.2' - only where no other cell stands)
        free_pp = [b for b in pp if free(b)]; free_ox = [b for b in ox if free(b)]
        C = candidates(toks(k, '()$'), free_pp, free_ox, fuzzy, relaxed=True, need=len(cs))
        if len(C) < len(cs) and '⌃' in k:                          # free OCR reads a raised mark glued to its word ("Liquidity4",
            glued = [copy.copy(b) for b in free_pp + free_ox]           # "2029:3"): compare that one box's text with spaces ignored
            for b in glued: b.t = [''.join(b.t2)] if b.t2 else []; b.frac = fracs(b.t) if b.t else []
            C = candidates([''.join(toks(k.replace(' ⌃ ', ''), '()$'))], [b for b in glued if b.src == 'pp'], [b for b in glued if b.src == 'ox'], fuzzy, need=len(cs))
        for c in C: c['tier'] += 0.5
        settle(cs, C)
    # More places seen than written: keep the places that fit the grid built so far - on the line of the row's other cells
    # (a row is one line of text), a column heading above the cells it heads.
    yc = lambda c: (c['ext'][1] + c['ext'][3]) / 2
    mh0 = st.median([c['ext'][3] - c['ext'][1] for x in cells if x['loc'] for c in [x['loc']]] or [10])
    rowy = collections.defaultdict(list)
    for x in cells:
        if x['loc'] and x['rs'] == 1: rowy[x['r']].append(yc(x['loc']))
    ry = {r: st.median(v) for r, v in rowy.items()}
    def allowed(x, C):
        out = []
        for c in C:
            h = c['ext'][3] - c['ext'][1]
            if x['rs'] == 1 and x['r'] in ry and not (abs(yc(c) - ry[x['r']]) <= 0.4 * h if h <= 1.5 * mh0 else c['ext'][1] <= ry[x['r']] <= c['ext'][3]): continue
            if x['role'] == 'col':
                below = [y['loc']['ext'][1] for y in cells if y['loc'] and y['role'] == 'data' and y['r'] >= x['r'] + x['rs'] and y['c'] < x['c'] + x['cs'] and y['c'] + y['cs'] > x['c']]
                if below and c['ext'][3] > min(below) + 0.3 * h: continue
            out.append(c)
        return out
    for cs, C in pending:
        A = [allowed(x, C) for x in cs]
        if all({id(c) for c in a} == {id(c) for c in A[0]} and len(a) == len(cs) for a in A):   # the same places fit every cell: reading order
            for x, c in zip(cs, lines_order(A[0])): x['loc'] = c
        elif all(len(a) == 1 for a in A) and len({id(a[0]) for a in A}) == len(A):
            for x, a in zip(cs, A): x['loc'] = a[0]
        else:
            for x in cs: x['why_not'] = 'ambiguous'
    return area, pp, ox

# ---------------------------------------------------------------- geometric tests
def ov(a0, a1, b0, b1): return min(a1, b1) - max(a0, b0)

isval = lambda x: any(ch.isdigit() for ch in x['key']) or len(x['key'].replace(' ', '')) <= 4   # a number-like or very short cell (n/a): its whole extent is its column

def check(cells, P=None, pp=(), known=frozenset()):
    """The geometric rule on one located table. Returns dict(violations=[(test, detail)], unverified=[...], green=bool, stats).
    Rule (all lengths in units of the table's median text height mh):
      ROW   every two one-row cells of a grid row share a text line (vertical overlap >= half the smaller height);
            grid rows go down the picture in grid order.
      COL   the x-extents of the number-like cells of different grid columns do not overlap (c < c' => right(c) <= left(c') + eps), and
            a text cell contributes its left edge only (it may run into empty neighbours).
      HEAD  a column heading overlaps every column band its span covers and none of the others it does not (overlap share >= a / <= b);
            it sits above the cells it governs."""
    P = dict(dict(eps=0.5, rowov=0.5, margin=0.4, far=0.8, gap=3.0), **(P or {}))
    loc = [x for x in cells if x['loc']]; viol, unv = [], []
    hs = [x['loc']['ext'][3] - x['loc']['ext'][1] for x in loc if len(x['key'].split()) <= 2]
    mh = st.median(hs) if hs else 10
    E = lambda x: x['loc']['ext']
    # ROW
    rows = collections.defaultdict(list)
    for x in loc:
        if x['rs'] == 1: rows[x['r']].append(x)
    for r, xs in rows.items():
        for p, q in itertools.combinations(xs, 2):
            a, b = E(p), E(q)
            need = 0 if 'col' in (p['role'], q['role']) else P['rowov'] * min(a[3] - a[1], b[3] - b[1])   # heading cells may sit top, middle or bottom of a tall header row
            if ov(a[1], a[3], b[1], b[3]) < need - (0.25 * mh if need == 0 else 0): viol.append(('ROW', f"r{r} c{p['c']}/{q['c']}"))
    ry = [(st.median((E(x)[1] + E(x)[3]) / 2 for x in xs), r) for r, xs in sorted(rows.items())]
    for (y0, r0), (y1, r1) in zip(ry, ry[1:]):
        if y1 <= y0: viol.append(('ROWORDER', f"r{r0}/{r1}"))
    # ROWGAP: a vertical gap between neighbouring rows much larger than the usual row pitch is where one table ends and another starts
    if len(ry) >= 4:
        med = max(st.median(b[0] - a[0] for a, b in zip(ry, ry[1:])), 1e-6)
        for (y0, r0), (y1, r1) in zip(ry, ry[1:]):
            if y1 - y0 > P['gap'] * med: viol.append(('ROWGAP', f"r{r0}/{r1} {(y1 - y0) / med:.1f}x pitch"))
    # COL
    body = [x for x in loc if x['role'] in ('data', 'row') and x['cs'] == 1 and not x['alone']]
    VB, TXT = {}, set()
    for x in body:
        if x['key'] and isval(x) and x['c'] >= 1:
            e = E(x); b = VB.setdefault(x['c'], [e[0], e[2]]); b[0] = min(b[0], e[0]); b[1] = max(b[1], e[2])
        elif x['c'] > 0: TXT.add(x['c'])
    cs_ = sorted(VB)
    for a, b in itertools.combinations(cs_, 2):
        if VB[a][1] > VB[b][0] + P['eps'] * mh: viol.append(('COL', f"c{a}/{b} overlap {(VB[a][1] - VB[b][0]) / mh:.2f}"))
    # text cells in body columns: nothing here measures where they stand - unverified
    for x in body:
        if x['key'] and not isval(x) and x['c'] >= 1 and x['why_not'] != 'filler': unv.append(('TEXT-CELL', f"r{x['r']}c{x['c']} {x['key'][:25]}"))
    # HEAD. A heading is centred (or aligned the same way as its table's other headings) over its columns: calibrate the offset between
    # one-column headings and the number columns under them (median, same table), then a heading must sit closest to its own span of
    # columns - nearer than the spans one column wider/narrower at either end (a boundary moved) and nearer than another column.
    cen = {c: (b[0] + b[1]) / 2 for c, b in VB.items()}
    leaf = [(x, (E(x)[0] + E(x)[2]) / 2 - cen[x['c']]) for x in loc if x['role'] == 'col' and x['cs'] == 1 and x['c'] in cen and x['c'] > 0]
    delta = st.median(d for _, d in leaf) if len(leaf) >= 2 else None
    def dev(cH, cols): return abs(cH - delta - (cen[cols[0]] + cen[cols[-1]]) / 2)
    hd = collections.defaultdict(list); order = sorted(cen)
    for x in loc:
        if x['role'] != 'col': continue
        e = E(x); cols = list(range(x['c'], x['c'] + x['cs'])); cH = (e[0] + e[2]) / 2
        gov = [y for y in loc if y['role'] != 'col' and y['r'] >= x['r'] + x['rs'] and y['c'] < x['c'] + x['cs'] and y['c'] + y['cs'] > x['c']]
        if gov and e[3] > min(E(y)[1] for y in gov) + 0.5 * mh: viol.append(('HEADBELOW', f"r{x['r']}c{x['c']}"))
        if x['c'] == 0:                                           # over the label column: it must at least stand left of every number column
            if x['cs'] == 1 and cen and cH > min(VB[c][0] for c in VB) + P['eps'] * mh: viol.append(('HEAD0', f"r{x['r']} {x['key'][:25]} right of the numbers"))
            continue
        have = [c for c in cols if c in cen]
        if len(have) != len(cols):
            (unv if set(cols) - set(cen) - TXT or not set(cols) & TXT else unv).append(('HEAD-no-band' if not set(cols) & TXT else 'HEAD-text-column', f"r{x['r']}c{x['c']}+{x['cs']} {x['key'][:30]}")); continue
        if delta is None: unv.append(('HEAD-uncalibrated', f"r{x['r']}c{x['c']}+{x['cs']} {x['key'][:30]}")); continue
        d0 = dev(cH, cols); hd[x['r']].append((x['c'], cH))
        if len(order) >= 2 and d0 > P['far'] * st.median(b - a for a, b in zip([cen[c] for c in order], [cen[c] for c in order][1:])): viol.append(('HEADFAR', f"r{x['r']}c{x['c']}+{x['cs']} {d0 / mh:.1f}mh off"))
        if any(E(y)[3] < e[1] - 0.2 * mh for y in loc if y['role'] != 'col' and y['key'] and y['c'] < x['c'] + x['cs'] and y['c'] + y['cs'] > x['c'] and y['r'] < x['r']): viol.append(('HEADMID', f"r{x['r']}c{x['c']} heading below data"))
        alts = []
        moves = [(-1, -1), (1, 1)] if x['cs'] == 1 else [(-1, 0), (1, 0), (0, -1), (0, 1)]   # a column over, or one end of the span moved
        for lo, hi in moves:
            a_, b_ = cols[0] + lo, cols[-1] + hi
            if a_ <= b_ and a_ >= 1 and all(c in cen for c in range(a_, b_ + 1)): alts.append(list(range(a_, b_ + 1)))
        for alt in alts:
            shift = abs((cen[alt[0]] + cen[alt[-1]]) / 2 - (cen[cols[0]] + cen[cols[-1]]) / 2)
            if shift and dev(cH, alt) - d0 < P['margin'] * shift: viol.append(('HEADSPAN', f"r{x['r']}c{x['c']}+{x['cs']} not closer than c{alt[0]}+{len(alt)}"))
    for r, v in hd.items():
        v.sort()
        for (c0, x0), (c1, x1) in zip(v, v[1:]):
            if c0 < c1 and x0 >= x1: viol.append(('HEADORDER', f"r{r} c{c0}/{c1}"))
    # UNEXPLAINED: text the free tool sees inside the table's own extent that no cell accounts for (a title between two tables merged into
    # one, a note, a cell Chandra dropped). Single junk glyphs ($ read as s/S/5, dashes) do not count.
    if loc and pp:
        hx0, hy0 = min(E(x)[0] for x in loc), min(E(x)[1] for x in loc); hx1, hy1 = max(E(x)[2] for x in loc), max(E(x)[3] for x in loc)
        ext = [E(x) for x in loc]
        for b in pp:
            if not (hx0 <= b.xc <= hx1 and hy0 <= b.yc <= hy1): continue
            if sum(ch.isalnum() for ch in b.raw) < 2: continue   # one lone glyph: a $ read as 5 or S, a footnote mark - cannot tell
            if all(t in DASH or t == '$' for t in b.raw.split()): continue
            if b.t and all(t in known for t in b.t): continue   # text Chandra put outside the table (a title, 'Unaudited', a note)
            a = (b.x0, b.y0, b.x1, b.y1)
            if any(max(0, min(a[2], t[2]) - max(a[0], t[0])) * max(0, min(a[3], t[3]) - max(a[1], t[1])) > 0.3 * (a[2] - a[0]) * (a[3] - a[1]) for t in ext): continue
            viol.append(('UNEXPLAINED', b.raw[:30]))
    for x in cells:
        if x['key'] and not x['loc'] and x['why_not'] != 'filler': unv.append(('UNLOCATED', f"r{x['r']}c{x['c']} {x['why_not']} {x['key'][:30]}"))
    return dict(violations=viol, unverified=unv, green=not viol and not unv, mh=mh, bands=VB)

def status(tb, bb, rec, boxes, known, P=None):
    cells, at = place(tb)
    if cells is None or tb.get('uncertain'):                          # the checker cannot place it, or the reading is uncertain: never GREEN
        return 'GREY', dict(violations=[], unverified=[('PLACEMENT' if cells is None else 'UNCERTAIN', '')], green=False)
    area, pp, ox = locate(cells, bb, rec['w'], rec['h'], boxes)
    ck = check(cells, P, pp=pp, known=known); ck['cells'] = cells       # (the located cells, with the tier each text was found by)
    return ('GREEN' if ck['green'] else 'RED' if ck['violations'] else 'GREY'), ck
