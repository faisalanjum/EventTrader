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
def _grp(n):
    neg = n.startswith('-'); n = n.lstrip('-'); out = ''
    while len(n) > 3:
        out = ',' + n[-3:] + out; n = n[:-3]
    return ('-' if neg else '') + n + out


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
def at_boundary(text, start, end, numeric=True):
    """THE single numeric-boundary rule. A number match is only real if it isn't glued into a
    bigger number OR a word on either side ('modelX86' / 'FY86' never print the value 86 —
    round-16, reviewer-confirmed live). Used by every matcher — do not duplicate this logic."""
    b = text[start-1] if start > 0 else ' '
    a = text[end] if end < len(text) else ' '
    nxt = text[end+1] if end+1 < len(text) else ' '
    if numeric and (b.isalnum() or b in '.,'):
        return False                       # glued to a preceding digit/letter/separator
    if a.isalnum():
        return False                       # glued into a longer number or word
    if a in '.,' and nxt.isdigit():
        return False                       # a thousands separator / decimal continues the number
    return True


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


_TRAIL = re.compile(r'(?:\s?(?:%|\)|percent\b|million\b|billion\b|thousand\b))*')


def _with_trail(t, end):
    """Extend a crop end to keep the value's IMMEDIATE trailing evidence — '%', ')', 'percent',
    scale words — so the sign/class/unit gates can see it (round-12: the crop used to cut off the
    very characters the gates check; '86' was accepted from '86%' and +123 from '(123)')."""
    return end + _TRAIL.match(t[end:end + 32]).end()


# round-13 scale evidence + round-14 tightening (reviewer-confirmed live): a bare SCALED print
# ('1,200' for 1.2B) may only bind when evidence of THE REQUIRED MULTIPLIER is present — the
# NEAREST preceding section declaration ('in millions'; 52 cohort text blocks carry MIXED
# markers, so any-marker-anywhere approved wrong amounts) or the tag riding immediately after the
# number — and 'million' can never prove a value that needs 'billion'. Full-magnitude prints and
# zero are self-evident. Measured on the wp1 cohort: 315/315 certified table binds sit in
# sections carrying the strict marker -> zero recall cost.
_SCALE_MARK = re.compile(r'(?i)in (millions|thousands|billions|trillions)')
_SCALE_TAIL = re.compile(r'\s?(million|billion|thousand|trillion)s?\b', re.I)
_WORD2DIV = {'thousand': 1e3, 'million': 1e6, 'billion': 1e9, 'trillion': 1e12}


def _required_div(form, value):
    """The multiplier this printed form NEEDS to reproduce the value (1e3/1e6/1e9/1e12), or None
    when the form is self-evident (full magnitude, zero, or a non-numeric core)."""
    s = form.lstrip('$( ').rstrip(')%').replace(',', '').strip()
    try:
        f = abs(float(s))
    except ValueError:
        return None                        # non-numeric-core forms carry their own words
    av = abs(float(value))
    if av == 0 or f == av:
        return None
    for d in (1e3, 1e6, 1e9, 1e12):
        if f > 0 and abs(f * d - av) / av < 0.001:
            return d
    return None                            # no clean multiplier -> exact_form decides elsewhere


def _tail_div(text, end):
    """The scale word IMMEDIATELY after a hit ('1.2 billion' -> 1e9), or None."""
    m = _SCALE_TAIL.match(text[end:end + 32])
    return _WORD2DIV[m.group(1).lower()] if m else None


def _local_scale_divs(text, start):
    """The scale declarations GOVERNING this hit, as a set of divisors.
    Inside a table (a ##TABLE_START tag precedes the hit): every declaration between the table
    start and the hit — a real header names several scales for different columns ('(In millions,
    except shares in thousands)', AAPL's standard header; a single-nearest-word rule wrongly
    rejected the table's dominant scale). Outside tables: the single NEAREST preceding
    declaration. Empty set = no local evidence. Mixed-scale documents (52 cohort blocks) make
    any-marker-anywhere unsafe — locality is the whole point."""
    ts = text.rfind('##TABLE_START', 0, start)
    if ts >= 0:
        divs = {_WORD2DIV[m.group(1).lower().rstrip('s')]
                for m in _SCALE_MARK.finditer(text, ts, start)}
        if divs:
            return divs                    # the table declares its own scale(s) -> strict
        # a table that declares NOTHING inherits a preceding declaration ONLY when the text
        # declares exactly ONE scale overall (AA caption layout = reading convention). Round-16
        # (reviewer-confirmed hazard): a mixed-scale text must never lend a marker across tables.
    all_divs = {_WORD2DIV[m.group(1).lower().rstrip('s')]
                for m in _SCALE_MARK.finditer(text, 0, start)}
    return all_divs if len(all_divs) == 1 else set()


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
               'reportable', 'entities', 'operating', 'and', 'the', 'of', 'group'}


def slice_tokens(name):
    return {t.lower() for t in re.findall(r"[A-Za-z]{3,}", name) if t.lower() not in SLICE_STOP}


def seg_members(fc):
    """member value strings, supporting both {dimension,value} and explicitMember.$t shapes."""
    seg = fc.get('segment')
    if not seg:
        return []
    items = seg if isinstance(seg, list) else [seg]
    out = []
    for s in items:
        if not isinstance(s, dict):
            continue
        if isinstance(s.get('value'), str):
            out.append(s['value'])
        em = s.get('explicitMember')
        if isinstance(em, dict) and em.get('$t'):
            out.append(em['$t'])
        elif isinstance(em, str):
            out.append(em)
    return out


def seg_axis_members(fc):
    """[(axis_qname, member_qname)] for ALL four segment shapes — {dimension,value}, single
    explicitMember.$t, the multi-axis explicitMember-LIST, and explicitMember-as-bare-string — so it reads
    every shape oracle._members_all does. Completeness is load-bearing twice over: tier1's aggregate guard
    (`if seg_axis_members(fc)`) uses it to reject dimensioned facts, so a shape missed here becomes a
    segment value mis-bound as a consolidated total; and [] must mean VERIFIED-undimensioned, never
    parse-failure (ChannelContract §3 / OD-17c: a missed extraction must never masquerade as consolidated).
    FETCH-only: the raw XBRL axis+member the shared decomposer classifies into a slice kind."""
    seg = fc.get('segment')
    if not seg:
        return []
    items = seg if isinstance(seg, list) else [seg]
    out = []
    for s in items:
        if not isinstance(s, dict):
            continue
        if isinstance(s.get('value'), str):
            out.append((s.get('dimension', ''), s['value']))
        em = s.get('explicitMember')
        if isinstance(em, list):                         # multi-axis: explicitMember is a LIST
            out += [(m.get('dimension', ''), m['$t']) for m in em
                    if isinstance(m, dict) and m.get('$t')]
        elif isinstance(em, dict) and em.get('$t'):
            out.append((em.get('dimension', ''), em['$t']))
        elif isinstance(em, str) and em:                 # bare string: the axis sits on `s`, not on `em`
            out.append((s.get('dimension', ''), em))
    return out


def member_tokens(members):
    toks = set()
    for m in members:
        pre, _, local = str(m).rpartition(':')
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
    kt = slice_tokens(name)
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
                if (fc.get('period') or {}).get('endDate') != per:
                    continue
                members = sorted(seg_members(fc))   # round-18: canonicalized ONCE, so every
                                                     # emitted field (member text, quote, axes)
                                                     # is dimension-order-free
                # round-20 (reviewer-generalized from the country rule): FULL-SLICE PROOF
                # for EVERY dimension — the KPI's slice-token set must EQUAL the union of every
                # member's meaningful tokens (country codes expand via the ISO names; structural
                # members tokenize to ∅ = the exact already-proven class and change nothing).
                # [Alpha, Beta] never binds plain 'Alpha Revenue'; US+Canada never binds US;
                # identical member names under different axes still bind when the KPI names them.
                _need = set()
                _gate_fail = False
                for _mm in members:
                    _pre, _, _loc = str(_mm).rpartition(':')
                    if _pre == 'country':
                        _nm = COUNTRY_NAME.get(_loc.upper())
                        if not _nm:
                            _gate_fail = True
                            break
                        _need |= {w for w in re.findall(r"[A-Za-z]{3,}", _nm.lower())
                                  if w not in SLICE_STOP}   # both sides share ONE normalization
                    else:
                        _need |= member_tokens([_mm])
                if _gate_fail or (members and kt and _need != kt):
                    continue
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
                (c[4].get('period') or {}).get('endDate') or (c[4].get('period') or {}).get('instant'))
               for c in top}
    if len(structs) > 1:
        return None
    score, concept, mlabel, _, fc = cands[0]
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


def _tableforms(v, fmt):
    """Exact printed forms for table/row scanning. WP1: the value's EXACT form is ALWAYS included
    (zero, small ints, decimals — the old len>=3 filter silently killed them); a fractional value
    gets its 1-decimal companion but NEVER an integer-rounded print; big money keeps the grouped
    cell form + per-million/billion scaled forms (scaled bare ints only when >=3 digits — a bare
    '7' would match stray sevens). Precision comes from boundary + label adjacency (row_quote),
    never from magnitude or length."""
    av = abs(float(v))
    p = XN.plain(XN.dec(str(v)).copy_abs())
    s = {p}
    if fmt == '%':
        if '.' in p:
            s.add(f"{av:.1f}")             # 2.34 -> '2.3'; the integer print is the reader's call
        return s
    if '.' not in p:
        s.add(_grp(p))                     # grouped cell form ('5,365,000,000')
    for div in (1e3, 1e6, 1e9, 1e12):      # round-16: exact thousand + trillion forms too
        x = av / div
        if x >= 1:
            xi = int(round(x))
            if xi >= 100:
                s.add(f"{xi:,}")
            for d in (1, 2):
                s.add(f"{x:,.{d}f}")
    return {x for x in s if x}


def _tidy(s):
    """collapse whitespace/zero-width junk; content stays verbatim (same words, same numbers)."""
    return re.sub(r'\s+', ' ', s.replace('​', ' ')).strip()


def row_quote(texts, label_tokens, val, fmt, gap=90, scale_gate=False):
    """Cleanest verbatim quote: starts at THIS metric's label and runs through the value.
    Every label token must appear within `gap` chars before the value, and the value must sit at
    a numeric boundary. Returns the shortest such quote, or None.
    scale_gate (round-13, opt-in — certified benchmark callers keep legacy behavior): a bare
    SCALED form binds only with scale evidence (section _SCALE_MARK, or the tag immediately after
    the hit); %-format and full-magnitude/zero forms are exempt."""
    lt = [t.lower() for t in label_tokens if t]
    if not lt:
        return None
    forms = _tableforms(val, fmt)
    needy = ({f: _required_div(f, val) for f in forms if _required_div(f, val)}
             if scale_gate and fmt != '%' else {})
    best = None
    for t in texts:
        low = t.lower()
        for fo in sorted(forms):           # SET iteration is hash-random per process — sorted
                                           # + content tiebreaks make output fully deterministic
            req = needy.get(fo)
            for m in re.finditer(re.escape(fo), t):
                if not at_boundary(t, m.start(), m.end()):
                    continue
                if req:                    # round-14: evidence must name THE REQUIRED multiplier —
                    td = _tail_div(t, m.end())        # the immediate tag wins; else the CURRENT
                    if td is not None:                # table's (or nearest) declarations must
                        if td != req:                 # include it; wrong scale = no bind
                            continue
                    elif req not in _local_scale_divs(t, m.start()):
                        continue
                ws = max(0, m.start() - gap)
                seg = low[ws:m.start()]
                # round-16: tokens match WHOLE WORDS only ('net' never inside 'internet',
                # 'car' never inside 'oscar') — alnum lookarounds on the lowered window
                pos = []
                for tok in lt:
                    mt = re.search(r'(?<![a-z0-9])' + re.escape(tok) + r'(?![a-z0-9])', seg)
                    if not mt:
                        pos = None
                        break
                    pos.append(mt.start())
                if pos is None:
                    continue                      # some label token missing -> not this row
                q = t[ws + min(pos): _with_trail(t, m.end())]   # RAW slice incl. trailing evidence
                if best is None or len(q) < len(best) or (len(q) == len(best) and q < best):
                    best = q                      # shortest = tightest crop; content tiebreak
    return best


def _snippet_start(t, hit_start, label_tokens, base=320, maxback=2200, table_cap=2600):
    """Window start for a value hit. Default = base chars back. Then reach further back so the
    number's identifying header travels with it, two ways (take the earliest):
      (a) LABEL TOKENS — the nearest occurrence of any of the KPI's label tokens within maxback
          (catches prose and same-row/near-row segment labels);
      (b) TABLE HEADER — the nearest `##TABLE_START` marker within table_cap (catches tall/wide
          tables whose column header — often ABBREVIATED, e.g. 'VIU' for a full segment name — the
          label-token search can't match). The source text tags every table start, so this
          deterministically pulls in the column-header row."""
    default = max(0, hit_start - base)
    low = t.lower()
    near = low[default:hit_start]
    start = default
    for tok in label_tokens:                          # (a) label-token reach
        tl = tok.lower()
        if tl in near:
            continue
        region = low[max(0, hit_start - maxback):hit_start]
        p = region.rfind(tl)
        if p >= 0:
            start = min(start, max(0, hit_start - maxback) + p)
    ts = t.rfind('##TABLE_START', max(0, hit_start - table_cap), hit_start)  # (b) table-header reach
    if ts >= 0:
        start = min(start, ts)
    return start


def scan_text(texts, name, val, fmt, max_hits=20, keep=6, scale_gate=False):
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
    strict = row_quote(texts, nt, val, fmt, scale_gate=scale_gate)
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
                pre = snip[:m.start() - ws].lower()   # round-20: rank on the text BEFORE the
                score = (2 if '##TABLE_START' in snip else 0) + sum(   # value, WHOLE WORDS only —
                    1 for tk in ntl                                    # 'net' scores 0 inside
                    if re.search(r'(?<![a-z0-9])' + re.escape(tk) + r'(?![a-z0-9])', pre))  # 'internet'
                cands.append((score, len(snip), snip))
                if len(cands) >= max_hits * 4:          # round-19: BOUNDED MEMORY without blind
                    cands.sort(key=lambda c: (-c[0], c[1], c[2]))   # eviction — prune by RANK, so
                    del cands[max_hits:]                # 20 weak fills can never evict a stronger
                                                        # match found later (reviewer catch: the
                                                        # round-18 stop-at-N kept the first-N in
                                                        # canonical order, not the best-N)
    cands.sort(key=lambda c: (-c[0], c[1], c[2]))      # score, length, CONTENT — total order
    return strict, [c[2] for c in cands[:min(keep, max_hits)]]   # round-20: max_hits is honored


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
    assert tier1(xb, "New Vehicles Revenue", 2825640000, "2024-12-31"), "should match NewVehiclesMember"
    assert 'NewVehicles' in tier1(xb, "New Vehicles Revenue", 2825640000, "2024-12-31")['member']
    assert tier1(xb, "Used Vehicles Revenue", 1613849000, "2024-12-31"), "Used value -> UsedVehiclesMember"
    assert tier1(xb, "Total RV and Outdoor Retail Revenue", 5905399000, "2024-12-31"), "segment total"
    assert tier1(xb, "Operating Income", 2825640000, "2024-12-31") is None, "revenue value must not bind income KPI"
    # coincidental same-value under two different members -> ambiguous -> abstain
    xb2 = [json.dumps({"RevenueFromContractWithCustomerExcludingAssessedTax": [
        {"value": "999000000", "period": {"endDate": "2024-12-31"}, "segment": {"dimension": "d", "value": "co:NewVehiclesMember"}},
        {"value": "999000000", "period": {"endDate": "2024-12-31"}, "segment": {"dimension": "d", "value": "co:UsedVehiclesMember"}}]})]
    assert tier1(xb2, "New Vehicles Revenue", 999000000, "2024-12-31") is None, "same value/two members -> abstain"
    # signed match: a negative KPI value must not bind a positive fact
    xb3 = [json.dumps({"RevenueFromContractWithCustomerExcludingAssessedTax": [
        {"value": "500000", "period": {"endDate": "2025-09-30"}}]})]
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
