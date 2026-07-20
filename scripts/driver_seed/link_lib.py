"""Certified KPI->quote linking primitives (code tiers + gates).

Ported verbatim from the calibrated producer (session a0f165d5, 2026-07-10) that reached
100% precision on independent audit. Two gate bugs are baked in here and MUST stay:
  * numeric word-boundary  -> a number can't match inside a bigger number ("874" in "2,874")
  * lossless-form gate      -> reject coarse-rounded-only matches ("3.10" for 3,104,000)
Tier-1 additionally requires the XBRL concept be revenue/income-ish AND the dimension member
match the KPI's slice token (entity KPIs) or be undimensioned (aggregate KPIs).
"""
import re, json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'driver', 'relocation'))
import exact_numbers as XN     # THE shared exact-value helpers (Decimal-exact; no float round-trips)
from country_names import COUNTRY_NAME   # generated ISO-3166 table (country:XX member expansion)


# ---------- value-form generation (recall engine + oracle) ----------
# _grp: WP2 Chunk 1 — relocated to driver/relocation/locator.py (row_quote's closure);
# imported below with the other moved symbols.
def _round_forms(x):
    forms = set()
    for dec in (0, 1, 2, 3):
        forms.add(f"{x:.{dec}f}")
        f = math.floor(abs(x) * 10**dec) / 10**dec
        forms.add(f"{f:.{dec}f}")
    for f in list(forms):
        if '.' in f:
            forms.add(f.rstrip('0').rstrip('.'))
    return {f for f in forms if f not in ('', '-', '0', '-0')}


def value_forms(value, fmt='number', is_currency=1):
    """All plausible verbatim string forms of a reported value."""
    if value is None:
        return set()
    v = float(value); av = abs(v); forms = set()
    if v == 0:
        return {'0'}                       # a stated zero is a real value (WP1); boundary +
                                           # label-adjacency provide the precision, never magnitude
    if fmt == '%':
        integral = (av == int(av))
        for f in _round_forms(av):
            if not integral and '.' not in f:
                continue                   # 2.34 never accepts the integer-rounded print '2%'
                                           # (owner F2: the gray zone belongs to the reader lane)
            forms |= {f + '%', f + ' percent', f + ' percentage points', '(' + f + ')%', '(' + f + ')'}
        bps = av * 100
        if bps == int(bps):
            forms.add(f"{int(bps)} basis points")
        return forms
    ai = int(round(av))
    forms.add(_grp(str(ai))); forms.add(str(ai))
    p = XN.plain(XN.dec(str(value)).copy_abs())
    if '.' in p:
        forms.add(p)                       # the EXACT fractional print (38.3) — WP1; the old code
                                           # only made int-rounded + scaled forms, losing decimals
    for div, tag in ((1e3, 'K'), (1e6, 'M'), (1e9, 'B'), (1e12, 'T')):
        if av >= div / 10:
            scaled = av / div; si = int(round(scaled))
            if si >= 100:                # bare scaled int only when ≥3 digits — "20" for $20.372B would
                forms.add(_grp(str(si))); forms.add(str(si))   # match any stray "20"; "20 billion" kept below

            for f in _round_forms(scaled):
                if '.' in f or len(f) >= 3:   # bare scaled form needs a decimal or ≥3 digits ("20" for
                    forms.add(f)              # $20.372B matches any stray "20"; tagged forms below suffice)
                forms.add(f + tag)
                forms.add(f + ' ' + {'K': 'thousand', 'M': 'million', 'B': 'billion', 'T': 'trillion'}[tag])
    if is_currency:
        base = [f for f in forms if not f.startswith('$') and len(f) <= 12]
        forms |= {'$' + f for f in base}; forms |= {'$ ' + f for f in base}
    if v < 0:
        forms |= {'(' + f.lstrip('$ ') + ')' for f in list(forms)}
    return {f for f in forms if f and f not in ('0', '-0', '$0')}


# ---------- gates ----------
# at_boundary: WP2 Chunk 1 — relocated to driver/relocation/locator.py (row_quote's closure).
def bounded_hit(quote, form, forbid_pct=False):
    """form occurs in quote at a numeric word boundary (not glued inside a bigger number).
    forbid_pct: the occurrence must NOT be %-marked — a plain-number value never accepts a
    percent token ('86' vs '86%', '86 %', '86 percent'; round-12 widened past the bare '%')."""
    numeric = form[0].isdigit() or form[0] in '$('
    for m in re.finditer(re.escape(form), quote):
        if not at_boundary(quote, m.start(), m.end(), numeric):
            continue
        if forbid_pct and re.match(r'\s?(%|percent\b)', quote[m.end():m.end() + 9]):
            continue
        return True
    return False


# _TRAIL/_with_trail + the scale-evidence group (_SCALE_MARK/_SCALE_TAIL/_WORD2DIV/
# _required_div/_tail_div/_local_scale_divs): WP2 Chunk 1 — relocated to
# driver/relocation/locator.py (row_quote's closure); imported below.


def exact_form(form, value, fmt):
    """form reproduces value losslessly (grouped cell, long int, or decimal within 0.1%)."""
    if fmt == '%':
        return True
    s = form.lstrip('$( ').rstrip(')%').replace(',', '')
    try:
        f = abs(float(s))
    except ValueError:
        return False
    av = abs(float(value))
    if av == 0:
        return f == 0                      # a stated zero reproduces itself (WP1)
    if '.' not in s and s.isdigit() and len(s) >= 4:
        return True
    for sc in (1, 1e3, 1e6, 1e9, 1e12):
        if f > 0 and av > 0 and abs(f*sc - av)/av < 0.001:
            return True
    return False


def printed_negative(quote, form):
    """Does the quote print THIS number with accounting-negative NOTATION — '(123)' or '-123'?
    Notation ONLY. A sign carried by a word ("operating loss of 331") is a MEANING call the core owns
    (OD-12: the sign signal may be a noun, notation, or context) — code must never read words for sign.
    Requires the closing ')' so an ordinary parenthetical ("(500 employees)") can't be misread."""
    core = (form or '').lstrip('$( ').rstrip(')%').strip()
    if not core:
        return False
    for m in re.finditer(re.escape(core), quote or ''):
        pre, post = (quote[:m.start()]).rstrip(), (quote[m.end():]).lstrip()
        if pre.endswith('(') and post.startswith(')'):
            return True
        if re.search(r'(?<![\w.])[-−]\s*$', pre):
            return True
    return False


def _scale_tag_ok(quote, form, value):
    """Round-14: no bind survives on a form whose EVERY occurrence carries a scale tag that
    CONTRADICTS the claimed value ('1.2 million' never certifies 1.2 BILLION; '5,365 million'
    never certifies plain 5,365). An occurrence with the right tag — or no tag — keeps it alive."""
    req = _required_div(form, value)
    for m in re.finditer(re.escape(form), quote or ''):
        if not at_boundary(quote, m.start(), m.end()):
            continue
        td = _tail_div(quote, m.end())
        if td is None or td == req:
            return True
    return False


def value_ok(value, fmt, quote):
    """final deterministic self-check: value present at a real boundary AND losslessly, and the quote's own
    NOTATION does not contradict the value's sign.
    SCOPE (unchanged): this proves the NUMBER is in the quote — never that the KPI/period/slice binding is
    right (that is the binder + audits). The sign guard adds only the mechanical half: a value whose sign
    the quote's notation flatly contradicts is a wrong bind. A plain print asserts nothing about sign, so it
    is left to pass here and be judged where meaning lives — no keyword list, no guessed sign."""
    # '0' is a legal single-char form (a stated zero is a real value — WP1); everything else
    # keeps the >=2 guard against stray single digits.
    forms = {f for f in value_forms(value, fmt or 'number') if len(f) >= 2 or f == '0'}
    for div in (1e6, 1e9):
        xx = abs(float(value)) / div
        if xx >= 1:
            for d in (1, 2):
                forms.add(f"{xx:,.{d}f}")
    hits = [f for f in forms if bounded_hit(quote, f, forbid_pct=(fmt != '%'))]
    ok = [f for f in hits if exact_form(f, value, fmt)]
    if fmt != '%':                        # round-14: a printed scale tag that contradicts the
        ok = [f for f in ok if _scale_tag_ok(quote, f, value)]   # claimed value vetoes the bind
    if not ok:
        return False
    if float(value) > 0 and any(printed_negative(quote, f) for f in ok):
        return False                      # positive value vs a negative print -> wrong bind
    return True


# ---------- Step-0 emit gates: anti-hallucination + graded value presence (0 tokens) ----------
# Precision is STRUCTURAL, not trusted: an answer is emitted only if its quote is a verbatim substring
# of a code-located candidate AND the value actually appears in that quote. The grade records HOW
# exactly (exact | rounded | approx) so a downstream consumer never mistakes a rounded prose figure
# for an exact seed value. Shared by the seed pipeline (value known) and relocation (value read).
SCALE_WORD = {'thousand': 1e3, 'thousands': 1e3, 'million': 1e6, 'millions': 1e6,
              'billion': 1e9, 'billions': 1e9, 'trillion': 1e12, 'trillions': 1e12}
_HEDGE = re.compile(r'\b(about|approximately|approx|roughly|nearly|around|almost)\b|~', re.I)


def _parse_stated(vstr):
    """(negative, magnitude, decimals, scale-word-multiplier|None) from a printed number string."""
    s = (vstr or '').lower().strip()
    if not re.search(r'\d', s):
        return None
    neg = ('(' in s and ')' in s) or s.lstrip().startswith('-')
    mult = next((m for w, m in SCALE_WORD.items() if w in s), None)
    core = re.sub(r'[^0-9.]', '', s)
    if not re.search(r'\d', core) or core.count('.') > 1:
        return None
    return neg, float(core), (len(core.split('.')[1]) if '.' in core else 0), mult


def stated_match(vstr, truth):
    """printed value == truth at the printed number's OWN precision, sign-aware, over the scale ladder.
    Accepts legitimate rounding ('24.6' for 24.644B) but rejects a genuinely different number."""
    p = _parse_stated(vstr)
    if p is None:
        return False
    neg, val, dec, mult = p
    if neg != (float(truth) < 0):
        return False
    at = abs(float(truth))
    return any(st >= 0.05 and (round(val, dec) in (round(st, dec), math.floor(st * 10**dec) / 10**dec)
               or (abs(val - st) <= 10**-dec * 1.0000001 and abs(val - st) / st <= 0.0015))
               for st in ([at / mult] if mult else (at, at / 1e3, at / 1e6, at / 1e9, at / 1e12)))
    # filers TRUNCATE as often as they round (ACM 4,151.2 for 4,151,251K) -> accept round OR floor; and
    # two prints of one fact can differ by ONE unit of the last printed digit when the REFERENCE itself
    # is rounded (XBRL decimals=-5: filing 3,277.1 vs tag 3,277.2) -> accept 1 ulp ONLY at <=0.15% error


def value_present_rounded(value, fmt, quote):
    """a form of value appears at a numeric boundary in quote, allowing lossy rounding (prose scale)."""
    return any(bounded_hit(quote, f) for f in value_forms(value, fmt or 'number') if len(f) >= 2)


def _hedged(quote, value, fmt):
    """a hedge word ('about', 'approximately', ...) sits just before the value in the quote."""
    for f in value_forms(value, fmt or 'number'):
        for m in re.finditer(re.escape(f), quote):
            if _HEDGE.search(quote[max(0, m.start() - 25):m.start()]):
                return True
    return False


def precision_grade(value, fmt, quote):
    """exact (lossless in quote) | rounded (present at its stated precision) | approx (hedged) | None."""
    if value_ok(value, fmt, quote):
        return 'approx' if _hedged(quote, value, fmt) else 'exact'
    if value_present_rounded(value, fmt, quote):
        return 'approx' if _hedged(quote, value, fmt) else 'rounded'
    return None


def quote_in_candidates(quote, candidates):
    """ANTI-HALLUCINATION: the emitted quote must be a verbatim substring of a code-located candidate."""
    q = _tidy(quote)
    return bool(q) and any(q in _tidy(c) for c in candidates)


def evidence_or_abstain(driver_name_raw, period, value, fmt, quote, candidates, source, period_evidence):
    """The SINGLE emit gate + FROZEN output schema. Returns the evidence record, or None to abstain.
    Same gate for value-known (seed) and value-read (relocation); the value is whatever we're emitting."""
    if not quote_in_candidates(quote, candidates):
        return None
    if fmt != '%' and re.search(r'%|percent', str(value), re.I):
        return None                       # unit gate: a percent-shaped answer to a non-percent metric
    grade = precision_grade(value, fmt, quote)
    if grade is None:
        return None
    return {'driver_name_raw': driver_name_raw, 'period': period, 'value': value, 'fmt': fmt,
            'quote': _tidy(quote), 'source': source, 'period_evidence': period_evidence, 'grade': grade}


# ---------- Tier-1: XBRL structured ----------
STOP = {'revenue', 'sales', 'the', 'and', 'of', 'by', 'other', 'net', 'income', 'operating',
        'gross', 'profit', 'for', 'from', 'inc', 'corp', 'company', 'revenues', 'change', 'due',
        'to', 'increase', 'decrease', 'number', 'average', 'a', 'an'}
SLICE_STOP = set(STOP) | {'total', 'geography', 'segment', 'ebit', 'type', 'margin', 'price',
                          'volume', 'growth'}
# structural tokens carried by XBRL member names that don't identify a slice
GENERIC_MEM = {'member', 'segment', 'segments', 'consolidation', 'consolidated', 'items', 'axis',
               'reportable', 'entities', 'operating', 'and', 'the', 'of', 'group',
               'sector', 'company'}


_INITIALS = re.compile(r'\b([A-Z](?:\.[A-Z])+\.?)(?!\w)')
_PAREN_ACRO = re.compile(r'([A-Za-z][A-Za-z, ]*?)\s*\(\s*([A-Z][A-Za-z.]*)\s*\)')


def _norm_initials(s):
    """Round-28/29 (reviewer; 289 dotted + 16 missing-final-dot rows): dotted uppercase
    initials collapse to their plain form — U.S. -> US, U.S -> US, U.S.A. -> USA, L.P. -> LP —
    ONE general rule applied to BOTH tokenizer sides; no name list."""
    return _INITIALS.sub(lambda m: m.group(1).replace('.', ''), s)


def _drop_redundant_acronym(s):
    """Round-29 (reviewer): remove a parenthetical acronym ONLY when it exactly repeats the
    initials of the immediately adjacent full phrase — 'United Kingdom (U.K.)' -> 'United
    Kingdom', 'Remaining Performance Obligations (RPO)' -> the phrase. General initials test,
    no abbreviation list; anything else in parentheses is untouched."""
    def repl(m):
        pre, acro = m.group(1), m.group(2)
        letters = re.sub(r'[^A-Za-z]', '', acro).upper()
        words = pre.strip().replace(',', '').split()
        if len(letters) >= 2 and len(words) >= len(letters) and \
                ''.join(w[0] for w in words[-len(letters):]).upper() == letters:
            return pre
        return m.group(0)
    return _PAREN_ACRO.sub(repl, s)


def slice_tokens(name):
    """THE global KPI slice-token set (round-27/28): dotted initials normalized, then long
    tokens PLUS standalone UPPERCASE two-letter tokens ('RV', 'US') — one set for the early
    check, exact full-slice equality, aggregate rejection, and scoring. No maintained list;
    extra qualifiers fail closed."""
    name = _norm_initials(_drop_redundant_acronym(name))
    toks = {t.lower() for t in re.findall(r"[A-Za-z]{3,}", name) if t.lower() not in SLICE_STOP}
    toks |= {t.lower() for t in re.findall(r'\b[A-Z]{2}\b', name)}
    return toks


# round-21/22 (reviewer): the STRUCTURAL exemption is the EXACT STANDARD us-gaap pair ONLY
# (census: 1,363 occurrences), never token-emptiness (the OtherNet class token-strips to nothing
# yet is a REAL slice -> abstain). Round-22 removed the filer-specific ACI pin (conservatism +
# no filer hardcoding); the reconciled measurements and the EXACT census queries live in the
# review record (round 23) — no unpinned counts here.
STRUCTURAL_PAIRS = frozenset({
    ('srt:ConsolidationItemsAxis', 'us-gaap:OperatingSegmentsMember'),
})


def seg_members(fc):
    """member value strings — DERIVED from seg_parse, THE single all-shapes parser
    (round-21: the local re-parse missed the explicitMember-LIST shape; CAG carries 519 such
    facts — matching and output now see every shape the axis parser sees)."""
    return [m for _, m in seg_parse(fc)[0]]


from locator import (seg_parse,            # WP2 step 2: THE single strict parser lives in
                     _grp, at_boundary, _TRAIL, _with_trail,          # driver/relocation
                     _SCALE_MARK, _SCALE_TAIL, _WORD2DIV,             # (neutral side).
                     _required_div, _tail_div, _local_scale_divs,     # WP2 Chunk 1: the
                     _tableforms, row_quote,                          # row_quote quote-proof
                     _table_active_start, _snippet_start)             # closure moved there —
                                           # one implementation each; this channel file
                                           # re-exports the SAME names so every existing caller
                                           # keeps working; dependency points channel→neutral


def seg_axis_members(fc):
    """the pairs half of seg_parse — kept for read-only consumers; BINDING code must use
    seg_parse and honor `complete` (round-23)."""
    return seg_parse(fc)[0]


def member_tokens(members):
    toks = set()
    for m in members:
        pre, _, local = str(_norm_initials(str(m))).rpartition(':')
        local = local or m
        # owner recall packet (measured 113-row miss class): XBRL tags geography as ISO codes
        # (`country:US`) while KPI names say 'United States' — expand via the generated ISO
        # table. Precision-safe: unknown code -> no extra tokens -> behaves exactly as before.
        if pre == 'country' and local.upper() in COUNTRY_NAME:
            toks.update(w for w in re.findall(r"[A-Za-z]{2,}", COUNTRY_NAME[local.upper()].lower())
                        if w not in GENERIC_MEM)
        base = re.sub(r'Member$', '', local)
        # round-17: acronym split ONLY for runs of >=2 capitals — 'EMEASegment' -> 'EMEA Segment'
        # but 'IPhone' stays whole (the round-16 union leaked 'phone'; a 'Phone Revenue' KPI could
        # bind IPhoneMember — reviewer-reproduced). Single tokenization, no union.
        v = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1 \2', base)
        v = re.sub(r'([a-z])([A-Z])', r'\1 \2', v)
        for w in re.findall(r"[A-Za-z]{2,}", v.lower()):
            if w not in GENERIC_MEM:
                toks.add(w)
    return toks


def concept_ok(con):
    cl = (con or '').lower()
    if not any(g in cl for g in ('revenue', 'sales', 'income', 'profit', 'margin', 'operating',
                                 'premium')):
        return False
    # round-14 REVERSAL of the round-13 name-token rate ban (reviewer-confirmed over-reject: the
    # certified pool's `awk:...GeneralRateCase...RevenuesApprovedAmount` is REAL money, 4 rows).
    # Names do not decide number-nature; UNIT IDENTITY does — tier1 skips 'pure'-unitRef facts.
    # reject genuine tax / equity / share concepts (specific substrings, so "AssessedTax"
    # inside a revenue concept name is not caught)
    bad = ('incometax', 'taxexpense', 'taxbenefit', 'deferredtax', 'taxespayable', 'taxreceivable',
           'equity', 'commonstock', 'pershare', 'dividend', 'sharesoutstanding', 'stockholders',
           'arrangement')
    return not any(b in cl for b in bad)


def concept_type_ok(name, concept):
    """concept must match the metric TYPE named in the KPI (revenue vs income vs margin)."""
    nl = name.lower(); cl = concept.lower()
    if any(w in nl for w in ('revenue', 'sales')):
        return 'revenue' in cl or 'sales' in cl
    if 'gross profit' in nl or 'gross margin' in nl:
        return 'grossprofit' in cl or 'grossmargin' in cl
    if any(w in nl for w in ('operating income', 'operating profit', 'operating loss', 'ebit')):
        return 'operatingincome' in cl or 'operatingprofit' in cl
    if 'premium' in nl:
        return 'premium' in cl
    if any(w in nl for w in ('income', 'earnings', 'profit')):
        return 'income' in cl or 'profit' in cl or 'earnings' in cl
    return True   # no strong type hint -> rely on concept_ok + value + member


def _member_score(kt, mt):
    """how well member tokens match the KPI's slice tokens. None = no match."""
    if not mt:
        return None
    shared = {t for t in (kt & mt) if len(t) >= 4}
    if shared:
        return len(shared)
    if kt <= mt or mt <= kt:   # short-token fallback (e.g. abbreviations)
        return 1
    return None


def tier1(xbrls, name, val, per, is_currency=None):
    """match an XBRL fact by value+period+dimension member. Deterministic; returns dict or None.
    Collects all facts equal in (concept-type, value, period); picks the best member match, and
    ABSTAINS if two different members tie (genuinely ambiguous).
    is_currency (round-12 unit-class guard): 1 -> a fact tagged with a non-USD unitRef (e.g.
    shares) never binds; 0 -> a USD-tagged fact never binds; None/absent unitRef -> no opinion."""
    # SIGNED + Decimal-EXACT: a -X KPI must not bind a +X fact, and 2.34 must never bind a 2.01
    # fact (the old int-truncation conflated them — WP1 exactness fix).
    def _same_value(fc_value):
        try:
            return XN.eq(str(fc_value).strip(), str(val))
        except XN.ExactError:
            return False
    kt = slice_tokens(name)                # round-27: the ONE global set (uppercase shorts in)
    # a KPI with no slice tokens is only an aggregate if it actually says so; otherwise its
    # slice identity is unrecoverable (e.g. a residual "other" bucket) -> abstain
    if not kt and not any(w in name.lower() for w in ('total', 'consolidated')):
        return None
    cands = []   # (score, concept, members_label, member_key, fc)
    for b in xbrls:
        try:
            data = json.loads(b)
        except (ValueError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        for concept, facts in data.items():
            if not concept_ok(concept) or not concept_type_ok(name, concept):
                continue
            for fc in (facts if isinstance(facts, list) else [facts]):
                if not isinstance(fc, dict):
                    continue
                if not _same_value(fc.get('value', '')):
                    continue
                u = str(fc.get('unitRef') or '').lower()
                if 'pure' in u:
                    continue                      # round-14: a pure-unit fact (rate/ratio/percent)
                                                  # never binds this money/number lane — unit
                                                  # identity decides, never concept-name tokens
                if is_currency == 1 and u and 'usd' not in u:
                    continue                      # shares/other units never satisfy a money KPI
                if is_currency == 0 and 'usd' in u:
                    continue                      # a money fact never satisfies a non-money KPI
                _pe = fc.get('period') or {}
                if _pe.get('endDate') != per:
                    continue
                if not (isinstance(_pe.get('startDate'), str) and _pe['startDate'].strip()
                        and isinstance(_pe.get('endDate'), str)):
                    continue           # round-28: an INVALID duration shape (endDate-only etc.)
                                       # is never a candidate — shape before tie-breaking
                if 'instant' in _pe:
                    continue           # round-29: duration data ALSO carrying instant = malformed
                try:
                    XN.period_key(_pe['startDate'], _pe['endDate'])
                except XN.ExactError:
                    continue           # round-29: dates must survive the exact-date law
                _pairs, _complete = seg_parse(fc)      # round-23: THE single strict parser
                if not _complete:
                    continue           # any unparsed/blank/typed entry -> identity unprovable
                pairs = sorted(_pairs)
                members = [m for _, m in pairs]         # canonical ONCE for every emitted field
                # round-20 (reviewer-generalized from the country rule): FULL-SLICE PROOF
                # for EVERY dimension — the KPI's slice-token set must EQUAL the union of every
                # member's meaningful tokens (country codes expand via the ISO names; structural
                # members tokenize to ∅ = the exact already-proven class and change nothing).
                # [Alpha, Beta] never binds plain 'Alpha Revenue'; US+Canada never binds US;
                # identical member names under different axes still bind when the KPI names them.
                _contribs = []             # per-member token sets (attribution units)
                _gate_fail = False
                for _ax, _mm in pairs:
                    if (_ax, _mm) in STRUCTURAL_PAIRS:
                        continue           # exact graph-proven structural pins ONLY
                    _pre, _, _loc = str(_mm).rpartition(':')
                    if _pre == 'country':
                        # round-29 (reviewer safety find, reproduced + MEASURED): bare ISO codes
                        # collide with business abbreviations (IT≠Italy, NA≠North America,
                        # AI/GM/SA...) and ZERO live binds depended on the round-28 code
                        # shortcut (filer-named members carry their own tokens) — so codes are
                        # NEVER proof: country members bind on FULL-NAME tokens only.
                        _nm = COUNTRY_NAME.get(_loc.upper())
                        _tk = ({w for w in re.findall(r"[A-Za-z]{3,}", _nm.lower())
                                if w not in SLICE_STOP} if _nm else set())
                    else:
                        _tk = member_tokens([_mm]) - SLICE_STOP   # ONE shared normalization
                    if not _tk:
                        _gate_fail = True  # round-21: an UNKNOWN ∅-token member is a REAL,
                        break              # unprovable slice (OtherNet class) -> ABSTAIN
                    _contribs.append(_tk)
                if not _gate_fail:
                    for _i in range(len(_contribs)):
                        for _j in range(_i + 1, len(_contribs)):
                            if _contribs[_i] & _contribs[_j]:
                                _gate_fail = True   # round-21: overlapping members under
                                break               # different axes = ambiguous attribution
                        if _gate_fail:
                            break
                _need = set().union(*_contribs) if _contribs else set()
                if _gate_fail or (pairs and kt and _need != kt):
                    continue           # round-27: plain equality against the ONE global set
                mt = member_tokens(members)
                if kt:
                    score = _member_score(kt, mt)
                    if score is None:
                        continue
                else:
                    if seg_axis_members(fc):  # aggregate KPI binds ONLY an UNdimensioned fact (multi-axis-aware)
                        continue
                    score = 0
                mlabel = ", ".join(m.split(':')[-1] for m in members) or "total"
                mkey = frozenset(mt)
                cands.append((score, concept, mlabel, mkey, fc))
    if not cands:
        return None
    cands.sort(key=lambda c: -c[0])
    # round-17 (reviewer-reproduced): the round-16 rule RESTORED in full — among top-score
    # candidates, ANY difference (concept, slice, or period) ABSTAINS. The short-lived
    # concept-alias pick chose a coincidence-equal CostOfRevenue over Revenues purely by
    # alphabet; "same value+slice+period = same quantity" is FALSE across semantically
    # different concepts that pass the loose type filter. Identical duplicates still bind;
    # input order can never decide. (Measured: the alias pick contributed 0 of the +19 links.)
    top = [c for c in cands if c[0] == cands[0][0]]
    structs = {(c[1], tuple(sorted(tuple(p) for p in seg_axis_members(c[4]))),
                (c[4].get('period') or {}).get('startDate'),
                (c[4].get('period') or {}).get('endDate') or (c[4].get('period') or {}).get('instant'),
                str(c[4].get('unitRef') or '').strip().lower())   # round-28: equal NORMALIZED
               for c in top}                                      # units or no tie-break
    if len(structs) > 1:
        return None
    # round-27 (reviewer-reproduced: '999' vs '999.0' duplicates emitted by input order): equal-
    # identity candidates resolve by TOTAL content ordering — the database can never choose.
    score, concept, mlabel, _, fc = min(
        top, key=lambda c: (c[1], c[2], json.dumps(c[4], sort_keys=True)))
    pe = fc.get('period') or {}
    q = f'{concept} [{mlabel}] [{pe.get("startDate","")}..{pe.get("endDate","")}] = {fc.get("value")}'
    # raw XBRL context for the FETCH packet (concept + axis+member + exact period + instant/duration).
    # The shared decomposer/resolver consumes these; FETCH never interprets them.
    return {'member': mlabel, 'concept': concept, 'quote': q,
            'axis_members': sorted(tuple(p) for p in seg_axis_members(fc)),   # round-17: canonical
                                                     # order — storage dimension order never leaks
            'period_start': pe.get('startDate', ''),
            'period_end': pe.get('endDate') or pe.get('instant', ''),
            'ptype': 'instant' if 'instant' in pe else 'duration'}


# ---------- Tier-2: strict same-row text label ----------
def _toks(n):
    return [t for t in re.findall(r"[A-Za-z]{3,}", n) if t.lower() not in STOP]


# _tableforms: WP2 Chunk 1 — relocated to driver/relocation/locator.py (row_quote's closure).
def _tidy(s):
    """collapse whitespace/zero-width junk; content stays verbatim (same words, same numbers)."""
    return re.sub(r'\s+', ' ', s.replace('​', ' ')).strip()


# row_quote + _table_active_start + _snippet_start: WP2 Chunk 1 — relocated to
# driver/relocation/locator.py (THE quote-proof group's neutral home); imported below.
def scan_text(texts, name, val, fmt, max_hits=20, keep=6, scale_gate=False, with_context=False):
    """(clean_label_anchored_quote_or_None, up_to_`keep` candidate snippets).
    Collects up to max_hits boundary-valid occurrences, each windowed back to its header/label,
    then RANKS so the identifying candidate wins: a snippet that carries a table header and/or the
    KPI's own label tokens ranks above a bare occurrence — because a shared value (e.g. a capex
    figure that also appears as a prior-year column elsewhere) must surface its header row, not just
    its first textual hit.
    scale_gate (round-13): gates ONLY the strict auto-resolve result; candidate snippets stay
    permissive — the LLM tier re-verifies its own output."""
    nt = _toks(name) or re.findall(r"[A-Za-z0-9&]{2,}", name)   # pure-kind names ('revenue') must not
    ntl = [x.lower() for x in nt]                                # tokenize to EMPTY -> strict lock dies
    # round-21 Rule 2 (single path): the strict quote AND its supporting context come from the
    # SAME row_quote call. Round-23 (reviewer-reproduced leak): the context/conflict machinery
    # runs ONLY when the caller asked for context — certified default callers keep the exact
    # legacy strict result.
    if with_context:
        strict, strict_ctx = row_quote(texts, nt, val, fmt, scale_gate=scale_gate,
                                       with_context=True)
    else:
        strict, strict_ctx = row_quote(texts, nt, val, fmt, scale_gate=scale_gate), None
    forms = _tableforms(val, fmt)
    cands = []
    for t in sorted(texts):                # round-18: CANONICAL text order, so the bounded-work
                                           # cutoff below is input-order-free
        for fo in sorted(forms):           # deterministic scan order (sets are hash-random)
            for m in re.finditer(re.escape(fo), t):
                if not at_boundary(t, m.start(), m.end()):
                    continue
                ws = _snippet_start(t, m.start(), nt)
                snip = t[ws:m.end()+80]           # RAW slice — snippets are source text (WP1)
                vpos = m.start() - ws
                pre = snip[:vpos].lower()             # round-20: rank on the text BEFORE the value
                score = (2 if _table_active_start(snip, vpos, len(snip) + 1) >= 0 else 0) + sum(
                    1 for tk in ntl                    # round-22: ranking uses THE SAME
                    if re.search(r'(?<![a-z0-9])' + re.escape(tk) + r'(?![a-z0-9])', pre))
                                                       # active-table law as context windowing
                cands.append((score, len(snip), snip))
                if len(cands) >= max_hits * 4:          # round-19: BOUNDED MEMORY without blind
                    cands.sort(key=lambda c: (-c[0], c[1], c[2]))   # eviction — prune by RANK, so
                    del cands[max_hits:]                # 20 weak fills can never evict a stronger
                                                        # match found later (reviewer catch: the
                                                        # round-18 stop-at-N kept the first-N in
                                                        # canonical order, not the best-N)
    cands.sort(key=lambda c: (-c[0], c[1], c[2]))      # score, length, CONTENT — total order
    kept = [c[2] for c in cands[:min(keep, max_hits)]]           # round-20: max_hits is honored
    return (strict, kept, strict_ctx) if with_context else (strict, kept)


# is_derived moved to fiscal_ai_rules.py (2026-07-15) — it is a fiscal.ai VENDOR-label rule, not shared
# core; other channels must not inherit it. link_lib stays channel-agnostic.


def label_adjacent(kpi, value, fmt, quote, gap=40):
    """True if the KPI's own label sits within `gap` chars before the value in the quote — i.e. the
    quote proves itself. False => the value is in a bare row and needs full-table context."""
    toks = [t.lower() for t in _toks(kpi)]
    if not toks:
        return True                                   # aggregate/no distinctive label -> fine
    for f in _tableforms(value, fmt):
        for m in re.finditer(re.escape(f), quote):
            if not at_boundary(quote, m.start(), m.end()):
                continue
            if any(t in quote[max(0, m.start()-gap):m.start()].lower() for t in toks):
                return True
    return False


def expand_to_table(texts, quote, value, fmt):
    """Return the FULL table (##TABLE_START..##TABLE_END) that contains this quote/value, so the
    column header travels with the value. Falls back to a wide window if no table markers, or the
    original quote if it can't be relocated in the source. Deterministic, no LLM."""
    forms = sorted(_tableforms(value, fmt), key=len, reverse=True)
    for t in texts:
        i = t.find(quote)                             # quotes are RAW source slices (WP1)
        if i < 0:                                     # LLM may have reformatted; relocate by value
            i = -1
            for f in forms:
                for m in re.finditer(re.escape(f), t):
                    if at_boundary(t, m.start(), m.end()):
                        i = m.start(); break
                if i >= 0:
                    break
            if i < 0:
                continue
        ts = t.rfind('##TABLE_START', 0, i)
        te = t.find('##TABLE_END', i)
        if ts >= 0 and te >= 0 and (te - ts) < 6000:  # a real, bounded table
            return t[ts:te + len('##TABLE_END')]
        return t[max(0, i-1400):i + 500]              # no markers -> generous window
    return quote


if __name__ == '__main__':
    # gate bugs must stay closed
    assert not bounded_hit("APAC 3,360 3,060 2,874", "874"), "boundary: 874 inside 2,874"
    assert not bounded_hit("Asia Pacific 14.9", "4.9"), "boundary: 4.9 inside 14.9"
    assert not bounded_hit("iPhone $ 201,183", "201"), "boundary: 201 inside 201,183"
    assert bounded_hit("iPhone $ 201,183", "201,183")
    assert bounded_hit("Total net sales $ 143,756", "143,756")
    assert not exact_form("3.10", 3104000, 'number'), "lossy 3.10 vs 3.104M"
    assert exact_form("143,756", 143756000000, 'number'), "exact millions cell"
    assert exact_form("12877000000", 12877000000, 'number')
    assert value_ok(143756000000, 'number', "Total net sales $ 143,756")
    assert not value_ok(3104000, 'number', "Average restaurant sales (1) $ 3.10")
    # Tier-1 member matching (live {dimension,value} shape)
    xb = [json.dumps({"RevenueFromContractWithCustomerExcludingAssessedTax": [
        {"value": "2825640000", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"},
         "segment": [{"dimension": "srt:ProductOrServiceAxis", "value": "cwh:NewVehiclesMember"},
                     {"dimension": "us-gaap:StatementBusinessSegmentsAxis", "value": "cwh:RvAndOutdoorRetailMember"}]},
        {"value": "1613849000", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"},
         "segment": {"dimension": "srt:ProductOrServiceAxis", "value": "cwh:UsedVehiclesMember"}},
        {"value": "5905399000", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"},
         "segment": {"dimension": "us-gaap:StatementBusinessSegmentsAxis", "value": "cwh:RvAndOutdoorRetailMember"}}]})]
    # round-26: the OLD expectation here was STALE (pre-full-slice law): the fact carries the
    # RvAndOutdoorRetailMember co-member, so the PARTIAL label must ABSTAIN...
    assert tier1(xb, "New Vehicles Revenue", 2825640000, "2024-12-31") is None, \
        "partial label must abstain (RvAndOutdoorRetail co-member unnamed)"
    # ...and the FULL labels bind — incl. the standalone-uppercase 'RV' token (member-required)
    full = tier1(xb, "RV and Outdoor Retail New Vehicles Revenue", 2825640000, "2024-12-31")
    assert full and 'NewVehicles' in full['member'], "full label must bind NewVehiclesMember"
    # short-token SAFETY: unrelated short tokens never leak in; iPhone/Phone stays closed
    assert tier1(xb, "IT New Vehicles Revenue", 2825640000, "2024-12-31") is None, \
        "an unrelated short token must not bridge the slice equality"
    ip = [json.dumps({"Revenues": [{"value": "200", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"},
          "unitRef": "U_USD",
          "segment": [{"dimension": "us-gaap:ProductOrServiceAxis", "value": "aapl:IPhoneMember"}]}]})]
    assert tier1(ip, "Phone Revenue", 200, "2024-12-31", is_currency=1) is None, "Phone≠IPhone"
    assert tier1(xb, "Used Vehicles Revenue", 1613849000, "2024-12-31"), "Used value -> UsedVehiclesMember"
    assert tier1(xb, "Total RV and Outdoor Retail Revenue", 5905399000, "2024-12-31"), "segment total"
    assert tier1(xb, "Operating Income", 2825640000, "2024-12-31") is None, "revenue value must not bind income KPI"
    # round-26 (2nd stale expectation): under the FULL-SLICE IDENTITY law a same-value fact
    # under a DIFFERENT fully-named slice fails equality outright — it is a different fact,
    # not an ambiguity. The named slice binds cleanly.
    xb2 = [json.dumps({"RevenueFromContractWithCustomerExcludingAssessedTax": [
        {"value": "999000000", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"}, "segment": {"dimension": "d", "value": "co:NewVehiclesMember"}},
        {"value": "999000000", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"}, "segment": {"dimension": "d", "value": "co:UsedVehiclesMember"}}]})]
    r2 = tier1(xb2, "New Vehicles Revenue", 999000000, "2024-12-31")
    assert r2 and 'NewVehicles' in r2['member'], "exact-identity bind; Used is a different slice"
    # a TRUE tie — the SAME full identity under two different periods at one end date -> abstain
    xb2b = [json.dumps({"Revenues": [
        {"value": "999", "period": {"startDate": "2024-10-01", "endDate": "2024-12-31"}, "unitRef": "U_USD",
         "segment": {"dimension": "d", "value": "co:NewVehiclesMember"}},
        {"value": "999", "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"}, "unitRef": "U_USD",
         "segment": {"dimension": "d", "value": "co:NewVehiclesMember"}}]})]
    assert tier1(xb2b, "New Vehicles Revenue", 999, "2024-12-31") is None, "Q-vs-FY same end -> abstain"
    # signed match: a negative KPI value must not bind a positive fact
    xb3 = [json.dumps({"RevenueFromContractWithCustomerExcludingAssessedTax": [
        {"value": "500000", "period": {"startDate": "2025-07-01", "endDate": "2025-09-30"}}]})]
    assert tier1(xb3, "Total Revenue", -500000, "2025-09-30") is None, "-500k must not bind +500k"
    assert tier1(xb3, "Total Revenue", 500000, "2025-09-30"), "+500k binds +500k"
    # no slice tokens and no 'total' -> slice identity unrecoverable -> abstain
    assert tier1(xb3, "Other Revenue by Geography", 500000, "2025-09-30") is None, "'other' bucket -> abstain"
    # Step-0 emit gates: grade + anti-hallucination + frozen schema
    assert precision_grade(6115000000, 'number', "United States $ 6,115") == 'exact'
    assert precision_grade(24643957000, 'number', "EMEA 24.6") == 'rounded'          # rounded-consistent
    assert precision_grade(2000000000, 'number', "revenue was about $2 billion") == 'approx'   # hedged
    assert precision_grade(989400000, 'number', "$ 1,017.0") is None                 # different number
    assert stated_match("24.6", 24643957000) and not stated_match("1,017.0", 989400000)
    assert quote_in_candidates("United States $ 6,115", ["x Sales: United States $ 6,115 Australia y"])
    assert not quote_in_candidates("United States $ 9,999", ["x United States $ 6,115 y"])   # hallucinated
    assert evidence_or_abstain("US Revenue", "2025", 6115000000, 'number', "United States $ 6,115",
                               ["a United States $ 6,115 b"], "10-K", "FY2025")['grade'] == 'exact'
    assert evidence_or_abstain("US Revenue", "2025", 6115000000, 'number', "United States $ 6,115",
                               ["unrelated text"], "10-K", "FY2025") is None          # not in candidate
    print("link_lib self-check OK")
