# Reader packets (Codex block review, Oct 5), offline: no model calls. The AI reader gets ONE coherent reading - Chandra's
# blocks in its order, each with its place on the picture - plus the picture itself, and every block carries a status:
#   agree      - BLOCK agreement only: a second, independent whole-page reading (Sonnet) holds this block as whole elements of
#                its own, and the checker (rowcheck.compare: words, marks, uncertainty, unread text and, for a table, every cell
#                relationship) finds the two the same. Word alignment only proposes the pair; the checker decides. It is not a
#                check against the original, and a table's heading, unit, period and notes are blocks with their own status.
#   unresolved - otherwise: Chandra's text, its differences from Sonnet (all of them in the .json beside the packet), and
#                Sonnet's own reading of that region as a separate, unverified alternative with its source pointer.
#   visual     - Chandra's labels for pictures, charts and diagrams: Chandra's text there may be its own description or
#                estimates, so none of it is passed on; the region, and Sonnet's reading of that area as unverified.
# Tables pair by content only inside the place the surrounding text allows them, one best each way, never crossing.
# Every element of Sonnet's reading reaches the packet - inside an agreeing block, as an alternative, or as 'one reader only'
# in its place - and every Chandra block is shown (text outside Chandra's blocks is a block of its own); both are asserted.
# Saved free OCR (two simple tools) is shown as evidence at the same spot - conflicts and support - and never changes a status.
# packet() returns the text the AI reader receives and its record (complete differences, element pointers).
import collections, difflib, re
from html.parser import HTMLParser
from PIL import Image
from . import rowcheck as rc

VISUAL = {'Image', 'Figure', 'Diagram', 'Chemical-Block'}           # Chandra's labels for non-text regions (seen in our outputs)

TAB, VIS = '⟦table⟧', '⟦visual⟧'                 # one slot per table / visual block in the word line-up

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

WRAP = {'html', 'body', 'div', 'section', 'article', 'main'}         # containers whose children are the elements (not Chandra's block divs)

SHOWN = 4                                                            # two-reader differences shown per block (each reading is printed in full below); the rest are in the .json

toks = lambda x, fmt: rc._TOKEN.findall(rc.norm(rc.plain('\n'.join(rc.read(x, fmt)[0])))) if x else []

class _Top(HTMLParser):  # the top-level elements of a reading: raw spans, and whether a container around them is uncertain
    def __init__(self, html):
        super().__init__(convert_charrefs=True); self.h, self.out, self.stack, self.loose, self.wraps, self.at = html, [], [], None, [], [0]
        for line in html.split('\n'): self.at.append(self.at[-1] + len(line) + 1)
        self.feed(html); self.close(); self._loose(len(html))
        if self.stack: self.out.append(dict(self.unit, end=len(html), inner_end=len(html)))   # never closed: runs to the end
    def _pos(self): l, c = self.getpos(); return self.at[l - 1] + c
    def _loose(self, p):  # text outside every element: each of its lines is an element of its own (a reader's plain lines)
        q = self.loose
        while q is not None and q < p:
            e = self.h.find('\n', q, p); e = p if e < 0 else e
            if self.h[q:e].strip(): self.out.append(dict(tag=None, attrs={}, start=q, end=e, inner=q, inner_end=e, uncertain=any(flag for _, flag in self.wraps)))
            q = e + 1
        self.loose = None
    def handle_starttag(self, tag, attrs):
        if self.stack:
            if tag not in VOID: self.stack.append(tag)
            return
        p, a = self._pos(), dict(attrs); self._loose(p)
        if tag in WRAP and 'data-bbox' not in a: self.wraps.append((tag, 'data-uncertain' in a)); return
        u = dict(tag=tag, attrs=a, start=p, inner=p + len(self.get_starttag_text()), uncertain=any(flag for _, flag in self.wraps))
        if tag in VOID: self.out.append(dict(u, end=u['inner'], inner_end=u['inner']))
        else: self.unit, self.stack = u, [tag]
    def handle_startendtag(self, tag, attrs):
        if self.stack: return
        p = self._pos(); self._loose(p); e = p + len(self.get_starttag_text())
        self.out.append(dict(tag=tag, attrs=dict(attrs), start=p, end=e, inner=e, inner_end=e, uncertain=any(flag for _, flag in self.wraps)))
    def handle_endtag(self, tag):
        if not self.stack:
            self._loose(self._pos())
            if tag in (name for name, _ in self.wraps):
                while self.wraps.pop()[0] != tag: pass
            return
        if tag in self.stack:
            while self.stack.pop() != tag: pass
        if not self.stack:
            p = self._pos(); self.out.append(dict(self.unit, end=self.h.index('>', p) + 1, inner_end=p))
    def handle_data(self, d):
        if not self.stack and d.strip() and self.loose is None: self.loose = self._pos()

def decode_math(html):  # Chandra's declared math (<math>...</math>): plain symbol commands only (\\pm -> ±), by pylatexenc's own table.
    import html as H                                                   # Anything else in the element - a fraction, a group, an unknown
    from pylatexenc.latexwalker import LatexWalker, LatexCharsNode, LatexMacroNode   # command - keeps the whole element as written.
    from pylatexenc.latex2text import LatexNodes2Text, get_default_latex_context_db
    db, l2t = get_default_latex_context_db(), LatexNodes2Text()
    def one(m):
        try: nodes = LatexWalker(H.unescape(m.group(1)), tolerant_parsing=False).get_latex_nodes()[0]   # malformed math: kept as written
        except Exception: return m.group(0)
        out = []
        for n in nodes:
            if isinstance(n, LatexCharsNode): out.append(n.chars); continue   # characters kept exactly ("8 3/8" stays "8 3/8")
            if not (isinstance(n, LatexMacroNode) and db.get_macro_spec(n.macroname) and not (n.nodeargd and n.nodeargd.argnlist)): return m.group(0)
            t = l2t.nodelist_to_text([n])
            if not t.strip(): return m.group(0)
            out.append(t)
        return H.escape(''.join(out), quote=False)
    return re.sub(r'<math>(.*?)</math>', one, html, flags=re.S)

def box_of(a):  # a block's place: its reader's box on the 0-1000 scale, four integers in order; None when it gives none that can be placed
    m = re.fullmatch(r'(\d+) (\d+) (\d+) (\d+)', a.get('data-bbox', ''))   # (malformed, missing, reversed, empty or beyond the scale: the
    b = m and tuple(map(int, m.groups()))                                 # raw reading keeps what the reader wrote)
    return b if b and b[0] < b[2] <= 1000 and b[1] < b[3] <= 1000 else None

def blocks_of(html):  # Chandra's blocks: its data-bbox divs (box 0-1000 or None, label, inner HTML); anything else is an 'Unlabelled' block.
    out = []               # A block's own or inherited data-uncertain travels with its HTML to the checker (Codex r2 C1)
    for u in _Top(html).out:
        m = u['tag'] == 'div' and 'data-bbox' in u['attrs']
        h = html[u['inner']:u['inner_end']].strip() if m else html[u['start']:u['end']]
        h = decode_math(h)                                             # (the raw reading stays in the reader's saved file)
        if u['uncertain'] or (m and 'data-uncertain' in u['attrs']): h = f'<div data-uncertain>{h}</div>'
        out.append(dict(box=box_of(u['attrs']), label=u['attrs'].get('data-label', ''), html=h) if m else dict(box=None, label='Unlabelled', html=h))
    return out

def elements(html):  # Sonnet's elements: raw HTML (an uncertain container travels with it), char span, tokens (a table is one slot)
    out = []
    for u in _Top(html or '').out:
        raw = html[u['start']:u['end']]; raw = f'<div data-uncertain>{raw}</div>' if u['uncertain'] else raw
        out.append(dict(raw=raw, chars=(u['start'], u['end']), toks=[TAB] if u['tag'] == 'table' else toks(raw, 'html')))
    return out

def pairs_of(a, b):  # (Chandra's words, Sonnet's words) wherever two token lists differ
    return [(' '.join(a[a0:a1]), ' '.join(b[b0:b1])) for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op != 'equal']

def statuses(blocks, other_html):  # {block: (status, differences, Sonnet elements near it, elements its agreement covers, paired table)}, Sonnet's elements
    el = elements(other_html); other, eo, mine, owner = [], [], [], []
    for k, e in enumerate(el): other += e['toks']; eo += [k] * len(e['toks'])
    for i, b in enumerate(blocks):
        t = [VIS] if b['label'] in VISUAL else [TAB] if b['label'] == 'Table' else toks(b['html'], 'html'); mine += t; owner += [i] * len(t)
    touch, clean, dif, amap = {i: set() for i in range(len(blocks))}, {i: True for i in range(len(blocks))}, {i: [] for i in range(len(blocks))}, {}
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, mine, other, autojunk=False).get_opcodes():
        if op == 'equal':                                             # (two table slots in line pair nothing: tables pair by content below)
            for k in range(a1 - a0):
                if mine[a0 + k] not in (TAB, VIS): touch[owner[a0 + k]].add(b0 + k); amap[a0 + k] = b0 + k
            continue
        near = set(owner[a0:a1]) if op != 'insert' else {owner[k] for k in (a0 - 1, a0) if 0 <= k < len(owner)}   # an edge insert unsettles both neighbours
        for i in near: clean[i] = False; dif[i].append((' '.join(mine[a0:a1]), ' '.join(other[b0:b1]))); touch[i] |= set(range(b0, b1))
    span = {i: {eo[x] for x in touch[i]} for i in range(len(blocks))}
    tc = {i: toks(b['html'], 'html') for i, b in enumerate(blocks) if b['label'] == 'Table'}
    ts = {k: toks(e['raw'], 'html') for k, e in enumerate(el) if e['toks'] == [TAB]}
    sim = {(i, k): difflib.SequenceMatcher(None, tc[i], ts[k], autojunk=False).ratio() for i in tc for k in ts}
    anchors, aslot, bslot = sorted(amap.items()), {owner[a]: a for a in range(len(mine)) if mine[a] == TAB}, {eo[b]: b for b in range(len(other)) if other[b] == TAB}
    def place(i):  # Sonnet's tables the surrounding text allows for Chandra's table i: between the nearest matched words before and after it
        lo = max((b for a, b in anchors if a < aslot[i]), default=-1); hi = min((b for a, b in anchors if a > aslot[i]), default=len(other))
        return {k for k in ts if lo < bslot[k] < hi}
    def one_best(cands, score):  # the single best candidate; none on a tie
        top = max((score(c) for c in cands), default=None); best = [c for c in cands if score(c) == top]
        return best[0] if len(best) == 1 else None
    near = {i: place(i) for i in tc}
    best_c = {i: one_best(near[i], lambda k: sim[i, k]) for i in tc}
    best_s = {k: one_best({i for i in tc if k in near[i]}, lambda i: sim[i, k]) for k in ts}
    pair = {i: k for i, k in best_c.items() if k is not None and best_s[k] == i}   # by content, inside its place, each the other's only best
    crossed = {i for i in pair for j in pair if (i < j) != (pair[i] < pair[j])}    # (Codex r2 C2: content names a candidate, not its occurrence)
    for i in crossed: del pair[i]
    for i in set(tc) - set(pair):                                     # unproved: unresolved, Sonnet's tables at that place shown, all candidates recorded
        span[i] |= near[i]
        why = 'crosses another pair' if i in crossed else 'no Sonnet table at its place' if not near[i] else 'tied or not mutual' if best_c[i] is None or best_s[best_c[i]] != i else ''
        cands = ', '.join(f"element {k} ({sim[i, k]:.2f}{'' if k in near[i] else ', outside its place'})" for k in sorted(ts, key=lambda k: -sim[i, k])[:3])
        dif[i].append((None, f'table placement unproved ({why}); content candidates: {cands or "none"}'))
    ok, covers = {}, {}
    for i, k in pair.items():                                         # a table: the checker on the paired table (words and every cell relationship)
        span[i].add(k); v = rc.compare(blocks[i]['html'], el[k]['raw'], 'html', 'html'); ok[i] = v['verdict'] == 'same'; covers[i] = {k}
        if not ok[i]: dif[i] = pairs_of(tc[i], ts[k]) + [(None, f"checker: {v['verdict']}" + (f" ({v['why']})" if v['why'] else ''))]
    groups, cur = [], None                                            # text: neighbouring blocks that share a Sonnet element are judged together
    for i, b in enumerate(blocks):                                    # (Chandra may cut one of Sonnet's lines into two blocks)
        if b['label'] in VISUAL or b['label'] == 'Table' or not clean[i]: cur = None; continue
        if cur and span[i] & cur['els']: cur['ids'].append(i); cur['els'] |= span[i]
        else: cur = dict(ids=[i], els=set(span[i])); groups.append(cur)
    for g in groups:
        els, ids = sorted(g['els']), g['ids']
        if els and sorted(x for i in ids for x in touch[i]) != [x for x in range(len(other)) if eo[x] in els]:
            for i in ids: dif[i].append((None, 'Sonnet divides this text differently: no whole-element pair, not compared'))
            continue
        v = rc.compare('\n'.join(blocks[i]['html'] for i in ids), '\n'.join(el[k]['raw'] for k in els), 'html', 'html')   # the checker decides
        for i in ids:
            ok[i], covers[i] = v['verdict'] == 'same', set(els)
            if not ok[i]: dif[i].append((None, f"checker: {v['verdict']}" + (f" ({v['why']})" if v['why'] else '') + (f' (judged with blocks {ids})' if len(ids) > 1 else '')))
    st = {i: ('visual' if b['label'] in VISUAL else 'agree' if ok.get(i) else 'unresolved', dif[i], sorted(span[i]), sorted(covers.get(i, ()) if ok.get(i) else ()), pair.get(i))
          for i, b in enumerate(blocks)}
    return st, el

def region(box, w, h): return 'unknown' if box is None else '%d,%d-%d,%d px' % (box[0] * w // 1000, box[1] * h // 1000, box[2] * w // 1000, box[3] * h // 1000)

def free_notes(bl, st, el, free):  # per block: what BOTH saved free OCR tools read at the same spot (evidence only, never a decision)
    from . import free_evidence as E                                          # (imported here: it reads this module's tokenizer)
    ft, out = [E.free_tokens(free[t], bl, free['w'], free['h']) for t in ('pp', 'ox')], {}
    boxes = [E.free_tokens(free[t], bl, free['w'], free['h'], lines=True) for t in ('pp', 'ox')]   # each tool's text boxes per block
    for i, b in enumerate(bl):
        s, _, span, _, k = st[i]
        c, fr = toks(b['html'], 'html'), [f.get(i, []) for f in ft]
        if s == 'visual':                                              # a chart, picture or diagram: the free tools' own text boxes there,
            pp, ox = ([x.strip() for line in t.get(i, []) for x in line.split('\t') if x.strip()] for t in boxes)   # whole and unchanged,
            different = toks('\n'.join(pp), 'text') != toks('\n'.join(ox), 'text')  # include deletion-only and empty alternatives too
            rd = collections.Counter(c) | collections.Counter(toks('\n'.join(el[e]['raw'] for e in span), 'html'))
            m = sum((rd & collections.Counter(fr[0]) & collections.Counter(fr[1])).values())   # an annotation only: words a reader also wrote here
            out[i] = dict(pp=pp, ox_other=ox if different else [], ox_differs=different, matching_words=m, reader_words_without_match=sum(rd.values()) - m); continue
        sx = toks(el[k]['raw'], 'html') if k is not None else toks('\n'.join(el[e]['raw'] for e in span if el[e]['toks'] != [TAB]), 'html')
        out[i] = dict(conflicts=[(x, y) for _, _, x, y in E.conflicts(c, fr)], support=[v for v in E.support(c, sx, fr) if v[2]] if s == 'unresolved' and el else [])
    return out

def packet(name, picture, html, other_html, other_src, free=None, picture_ref=None):  # (the exact text the AI reader receives, its record); free: saved free OCR;
    # picture_ref: what the packet names as its picture (src, record) where `picture` is only the file it is measured from; None names `picture` itself
    bl = blocks_of(html); st, el = statuses(bl, other_html); w, h = Image.open(picture).size; ev = free_notes(bl, st, el, free) if free else {}
    res = {}                                                           # disputed tables whose whole reading the picture's word positions support
    if free and other_html:                                            # table choice weighs two readings: only with a second one
        from . import table_choice                                     # (owner, Oct 6: loaded only when Sonnet is on and has read)
        for i, b in enumerate(bl):
            if b['label'] == 'Table' and st[i][0] == 'unresolved' and b['box']:   # positions weigh only a table with a place
                who, why, _ = table_choice.choose(html, bl, i, st, el, free)
                if who: res[i] = (who, why)
    n = {k: sum(v[0] == k for v in st.values()) for k in ('agree', 'unresolved', 'visual')}; n['unresolved'] -= len(res)
    q = lambda x: (lambda x: '"%s"' % (x if len(x) <= 80 else x[:77] + '...'))(x.replace(TAB, '[a table]')) if x else '(nothing)'
    whole = lambda x: '"%s"' % x.replace(TAB, '[a table]') if x else '(nothing)'   # free-OCR evidence is printed nowhere else: every item, whole
    side, done = f'packets/{name}.json', set()
    ref = picture if picture_ref is None else picture_ref
    out = [f'<picture id="{name}" src="{ref}" size="{w}x{h}">',
           f'Status: {n["agree"]} blocks agree between two readers; ' + (f'{len(res)} tables resolved by the picture\'s word positions; ' if res else '') + (f'{n["unresolved"]} unresolved; ' if other_html else f'{n["unresolved"]} read by Chandra only (single reader, not compared); ') + f'{n["visual"]} visual (charts, pictures, diagrams: reader text unverified; free-OCR evidence shown, unverified). '
           'Agreement is per block and is not a check against the original; a table\'s heading, unit, period and notes are separate blocks '
           'with their own status. Quote unresolved text only after looking at its region; an alternative is unverified.'
           + ('' if other_html else ' There is no second reading: nothing here is compared.')
           + (' FREE OCR lines: saved readings of this region, labelled by tool; evidence to weigh, never a decision.' if free else '')]
    pointer = lambda ks: f'source: {other_src}, elements {ks[0]}-{ks[-1]}, characters {el[ks[0]]["chars"][0]}-{el[ks[-1]]["chars"][1]}'
    def show(ks, title):                                              # Sonnet's elements, each printed once
        new = [k for k in ks if k not in done]; done.update(ks)
        if new: out.append(f'[{title} | {pointer(new)}]'); out.extend(el[k]['raw'] for k in new)
        elif ks: out.append(f'[{title}: already shown above, elements {ks[0]}-{ks[-1]}]')
    anchor, last = {}, -1                                             # Sonnet elements no block touches: shown after the last block before them
    for k in range(len(el)):
        hit = [i for i, v in st.items() if k in v[2]]
        if hit: last = max(hit)
        else: anchor.setdefault(last, []).append(k)
    def lonely(after):
        if anchor.get(after): show(anchor[after], 'ONE READER ONLY: Sonnet has this here, Chandra does not; unverified')
    lonely(-1)
    for i, b in enumerate(bl):
        s, d, span, covers, _ = st[i]; head = f'[{s.upper()} {b["label"]} | region {region(b["box"], w, h)}'
        shown = [f'Chandra {q(c)} / Sonnet {q(o)}' if c is not None else o for c, o in d if c != VIS]
        more = f' (+{len(shown) - SHOWN} more differences in {side}, block {i})' if len(shown) > SHOWN else ''
        if s == 'visual':
            out.append(head + '] A chart, picture or diagram: look at the region. Readers\' text for it is unverified: it may be a description, or values estimated from the drawing. The FREE-OCR EVIDENCE line shows what simple OCR tools read there: unverified. Which label goes with which value is not proved.')
            if b['html'].strip(): out += ['[Chandra\'s reading of this region, unverified]', b['html']]
            show(span, 'Sonnet\'s reading of this area, unverified')
            pr = ev.get(i)
            if pr and (pr['pp'] or pr['ox_other']): out.append('[FREE-OCR EVIDENCE here, unverified: what two simple OCR tools read in this region (both can misread alike, e.g. an icon read as "8"); one text box per piece, pieces not linked to each other: '
                + ('PP-OCR: ' + ' / '.join(pr['pp']) if pr['pp'] else 'PP-OCR: (nothing)') + ('; OnnxTR reads otherwise: ' + (' / '.join(pr['ox_other']) or '(nothing)') if pr['ox_differs'] else '')
                + f'; matching words in this region: {pr["matching_words"]} of the readers\' words also appear in both tools\' text (not proof of place or link)]')
        elif i in res:                                                 # a whole reading chosen; the other kept as the alternative
            who, why = res[i]; head = f'[RESOLVED BY POSITIONS {b["label"]} | region {region(b["box"], w, h)} | {why}; the picture\'s word positions support its cells, rows and headings, not a check of every word'
            if who == 'C': out += [head + ' | reading: Chandra]', b['html']]; show(span, 'ALTERNATIVE, not chosen: Sonnet\'s reading of this region')
            else: out.append(head + ' | reading: Sonnet]'); show(span, 'CHOSEN: Sonnet\'s reading of this region'); out += ['[ALTERNATIVE, not chosen: Chandra\'s reading of this region]', b['html']]
        elif s == 'agree':
            out += [head + ']', b['html']]; done.update(covers)
            show([k for k in span if k not in covers], 'ONE READER ONLY: Sonnet has this here, Chandra does not; unverified')
        elif not other_html: out += [f'[CHANDRA ONLY {b["label"]} | region {region(b["box"], w, h)}]', b['html']]   # single reader: nothing compared
        else:
            out += [head + ' | differ: ' + '; '.join(shown[:SHOWN]) + more + ']', b['html']]
            show(span, 'ALTERNATIVE: Sonnet\'s reading of this region, unverified')
        for c, o in ev.get(i, {}).get('conflicts', []): out.append(f'[FREE OCR conflict, unverified: this block has {whole(c)} where both free tools read {whole(o)}]')
        for c, o, who in ev.get(i, {}).get('support', []): out.append(f'[FREE OCR support, unverified: at Chandra {whole(c)} / Sonnet {whole(o)} both free tools read {who}\'s version]')
        lonely(i)
    assert done == set(range(len(el))), 'a Sonnet element is missing from the packet'
    record = dict(picture=ref, size=[w, h], second_reading=other_src, elements=[dict(chars=e['chars']) for e in el],
                  blocks=[dict(label=b['label'], box=b['box'], status=st[i][0], differences=st[i][1], sonnet_elements=st[i][2], agreement_covers=st[i][3], paired_table=st[i][4], free_ocr=ev.get(i), table_choice=res.get(i)) for i, b in enumerate(bl)])
    return '\n'.join(out + ['</picture>']), record
