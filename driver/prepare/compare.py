"""Shared text and number comparison for preparation (picture reading now; HTML/XML conversion when Fable switches its
imports): the grader's own pure functions, copied unchanged so production never imports benchmark code. Sources:
benchmarks/prepare/grader/anchor.py (norm, squash) and grade.py (tokens, reading units, critical differences, spacing-only
test, word counts)."""
import difflib
import re
import unicodedata

# Character classes come from the Unicode database, never from hand-written lists:
#   whitespace = Unicode whitespace plus format marks (zero-width, soft hyphen, direction marks: category Cf);
#   E8 folding = quotation-mark glyphs to their class's ASCII mark (double stays double, single stays single: 6" is not 6'),
#   every dash (Pd) and the minus sign to a hyphen.
_CF = ''.join(chr(i) for i in range(0x110000) if unicodedata.category(chr(i)) == 'Cf')

_WS = re.compile('[\\s' + re.escape(_CF) + ']+')

_FOLD = str.maketrans({**{chr(i): ('"' if ('DOUBLE' in unicodedata.name(chr(i), '') or chr(i) == '"') else "'") for i in range(0x110000) if 'QUOTATION MARK' in unicodedata.name(chr(i), '')},
                       **{chr(i): '-' for i in range(0x110000) if unicodedata.category(chr(i)) == 'Pd' or unicodedata.name(chr(i), '') == 'MINUS SIGN'}})

def norm(s):
    """Comparison form: glyphs folded (E8), the key's ~~struck~~ marks dropped, whitespace runs -> one space."""
    return _WS.sub(' ', s.translate(_FOLD).replace('~~', '')).strip()

def squash(s):
    """Search form: norm without any whitespace."""
    return _WS.sub('', s.translate(_FOLD).replace('~~', ''))

_TOKEN_NUMBERS = re.compile(r'\d(?:[\d.,]*\d)?')  # a number keeps its separators

_TOKEN_WORDS = re.compile(_TOKEN_NUMBERS.pattern + r'|\w+')  # the words and numbers of a text, by Unicode category

def tokens(text):
    return _TOKEN_WORDS.findall(norm(text))

def boundary_equal(got, want):
    """Same characters and the same words and numbers: whitespace may move around punctuation and symbols (E12 reflow), but a
    boundary inside a word or a number may not appear or disappear."""
    return squash(got) == squash(want) and tokens(got) == tokens(want)

def spacing_only(got, want):
    """Same characters, a word or number boundary broken or glued by the tool."""
    return squash(got) == squash(want) and not boundary_equal(got, want)

NEG = {'not', 'no', 'never', 'none', 'nor', 'without', 'cannot'}  # negation: a closed grammatical class, read with the word it governs (E10 R4)

_TOKEN = re.compile(r"[(\-+]?\d(?:[\d,]|[./:-](?=\d))*%?\)?|[^\W\d_]+(?:'[^\W\d_]+)*|\S")  # a number with sign, parentheses, percent and separators between digits; a word; any other symbol alone

_digit = lambda w: any(c.isdigit() for c in w)

_symbol = lambda w: len(w) == 1 and unicodedata.category(w) in ('Sc', 'Sm')  # a currency or mathematical sign, by Unicode class, no list of ours

_neg = lambda w: w.lower() in NEG or w.lower().endswith("n't")

def reading_units(s):
    """Reading units of an approximate text: a currency or sign symbol joined to its number ('€20', '20%'), a number joined to the word that follows
    it — its unit or qualifier ('10 shares', '20 million'; deliberately also an ordinary word, so a changed word beside a number counts as critical),
    a negation joined to the word it governs ('not buy'); other words and symbols alone."""
    out = []
    for w in _TOKEN.findall(norm(s).replace('−', '-')):
        last = out[-1] if out else None
        if last is not None and ' ' not in last and ((_symbol(last) and _digit(w)) or (_digit(last) and (_symbol(w) or w[:1].isalpha())) or (_neg(last) and w[:1].isalpha())):
            out[-1] = last + ('' if _symbol(last) or _symbol(w) else ' ') + w
        else: out.append(w)
    return out

def critical(got, want):
    """Every ordered difference between an approximate (OCR) text and its reference, and which of them touch critical facts (E10 R4; Codex R13,
    R14-5). `edits`: the aligned spans that differ (reference tokens → output tokens), nothing filtered. `critical`: among them the tokens holding a
    digit, a currency or sign symbol, or a negation — compared position by position when both texts hold as many such tokens (two swapped values
    both show), by the alignment otherwise. `other`: the remaining differences, kept for review, never declared harmless."""
    crit = lambda w: _digit(w) or any(unicodedata.category(c) in ('Sc', 'Sm') for c in w) or _neg(w.split()[0])
    a, b = reading_units(want), reading_units(got); ca, cb = [w for w in a if crit(w)], [w for w in b if crit(w)]
    ops = [(op, a[i1:i2], b[j1:j2]) for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op != 'equal']
    miss, extra = [w for _, x, _ in ops for w in x], [w for _, _, y in ops for w in y]
    if len(ca) == len(cb) and ca != cb: cm, ce = [x for x, y in zip(ca, cb) if x != y], [y for x, y in zip(ca, cb) if x != y]
    else: cm, ce = [w for w in miss if crit(w)], [w for w in extra if crit(w)]
    return {'edits': [{'op': op, 'reference': x, 'output': y} for op, x, y in ops], 'critical': {'missing': cm, 'extra': ce},
            'other': {'missing': [w for w in miss if not crit(w)], 'extra': [w for w in extra if not crit(w)]}, 'reference_numbers': sum(1 for w in a if _digit(w))}

def wer_counts(got, want):
    """Word error rate with its parts: the substitutions, deletions and insertions of one minimal edit script that turns the output's words into
    the reference's, over the reference's words; `recovered` = reference words read as they are (0 for an empty output: zero recovery)."""
    x, y = norm(want).split(), norm(got).split(); n, m = len(x), len(y)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1): d[i][0] = i
    for j in range(1, m + 1): d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1): d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (x[i - 1] != y[j - 1]))
    s = dl = ins = 0; i, j = n, m
    while i or j:  # back along one minimal path: a match or substitution first, then a deletion, then an insertion
        if i and j and d[i][j] == d[i - 1][j - 1] + (x[i - 1] != y[j - 1]): s += x[i - 1] != y[j - 1]; i -= 1; j -= 1
        elif i and d[i][j] == d[i - 1][j] + 1: dl += 1; i -= 1
        else: ins += 1; j -= 1
    return {'reference': n, 'recovered': n - s - dl, 'substituted': s, 'deleted': dl, 'inserted': ins, 'rate': round((s + dl + ins) / max(1, n), 3)}
