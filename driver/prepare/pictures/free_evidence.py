# Free OCR as evidence (Codex support review, Oct 6): what the saved free readers (PP-OCRv6 lines, OnnxTR words, each with its
# box) read at the same place as a block. Evidence only: it never changes a status and never chooses a reading by itself.
# The free words go to Chandra's blocks by GEOMETRY ALONE (the smallest block box holding the word's centre, else the nearest box
# within one word height, else no block). A spot is read only at one occurrence: its words plus one word of context on each side
# (or the block's edge), and that context window must occur exactly once in both readings (Codex: a value from a later row or
# year is not this occurrence).
import collections, difflib, statistics
from . import packets as p
rc, toks = p.rc, p.toks

def owner_of(boxes, w, h, reach):  # a free word's block by geometry alone (Chandra boxes 0-1000; picture pixels, y down)
    rects = [None if b is None else (b[0] * w / 1000, b[1] * h / 1000, b[2] * w / 1000, b[3] * h / 1000) for b in boxes]
    def owner(x, y):
        inside = [j for j, r in enumerate(rects) if r and r[0] <= x <= r[2] and r[1] <= y <= r[3]]
        if inside: return min(inside, key=lambda j: ((rects[j][2] - rects[j][0]) * (rects[j][3] - rects[j][1]), j))
        d, j = min((((max(r[0] - x, 0, x - r[2]) ** 2 + max(r[1] - y, 0, y - r[3]) ** 2) ** 0.5, j) for j, r in enumerate(rects) if r), default=(None, None))
        return j if d is not None and d <= reach else None
    return owner

def free_tokens(words, blocks, w, h, lines=False):  # {block: tokens of one free tool's words that belong to it} (lines: its text lines)
    if not words: return {}
    reach = statistics.median(max(b['box'][1::2]) - min(b['box'][1::2]) for b in words)
    own = owner_of([b['box'] for b in blocks], w, h, reach); mine = collections.defaultdict(list)
    for b in words: mine[own(sum(b['box'][0::2]) / len(b['box'][0::2]), sum(b['box'][1::2]) / len(b['box'][1::2]))].append(b)
    return {j: rc.boxes_to_lines(ws) if lines else toks('\n'.join(rc.boxes_to_lines(ws)), 'text') for j, ws in mine.items() if j is not None}

def mapping(x, f):  # x index -> f index, for tokens inside equal runs of the alignment
    return {a + k: b + k for op, a, a1, b, b1 in difflib.SequenceMatcher(None, x, f, autojunk=False).get_opcodes() if op == 'equal' for k in range(a1 - a)}

def read_at(x, a0, a1, f, m):  # what f holds at x's spot [a0, a1): the words between the matched context on each side; None = no context
    left = -1 if a0 == 0 else m.get(a0 - 1); right = len(f) if a1 == len(x) else m.get(a1)
    if left is None or right is None or right <= left: return None
    def unique(seq, part):
        return bool(part) and sum(seq[j:j + len(part)] == part for j in range(len(seq) - len(part) + 1)) == 1
    context_x = x[max(0, a0 - 1):min(len(x), a1 + 1)]
    context_f = f[max(0, left):min(len(f), right + 1)]
    if not unique(x, context_x) or not unique(f, context_f): return None
    return f[left + 1:right]

def backs(x, a0, a1, f):  # does f hold exactly x's words at this spot (with its context)?
    return read_at(x, a0, a1, f, mapping(x, f)) == x[a0:a1]

def disputes(c, s):  # the spots where Chandra's and Sonnet's readings differ: (c span, s span)
    return [((a0, a1), (b0, b1)) for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, c, s, autojunk=False).get_opcodes() if op != 'equal']

def conflicts(a, free):  # spots where BOTH free tools read the same other words than reading a: (a0, a1, a's words, theirs)
    if len(free) != 2: return []
    maps, out = [mapping(a, f) for f in free], []
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(None, a, free[0], autojunk=False).get_opcodes():
        if op == 'equal': continue
        r = [read_at(a, a0, a1, f, m) for f, m in zip(free, maps)]
        if r[0] is not None and r[0] == r[1] and r[0] != a[a0:a1]: out.append((a0, a1, ' '.join(a[a0:a1]), ' '.join(r[0])))
    return out

def support(c, s, free):  # per disputed spot: Chandra's words, Sonnet's words, and which reading BOTH free tools back there
    out = []
    for (a0, a1), (b0, b1) in disputes(c, s):
        bc = len(free) == 2 and all(backs(c, a0, a1, f) for f in free); bs = len(free) == 2 and all(backs(s, b0, b1, f) for f in free)
        out.append((' '.join(c[a0:a1]), ' '.join(s[b0:b1]), 'Chandra' if bc and not bs else 'Sonnet' if bs and not bc else None))
    return out
