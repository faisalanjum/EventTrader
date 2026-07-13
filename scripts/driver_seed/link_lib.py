"""Certified KPI->quote linking primitives (code tiers + gates).

Ported verbatim from the calibrated producer (session a0f165d5, 2026-07-10) that reached
100% precision on independent audit. Two gate bugs are baked in here and MUST stay:
  * numeric word-boundary  -> a number can't match inside a bigger number ("874" in "2,874")
  * lossless-form gate      -> reject coarse-rounded-only matches ("3.10" for 3,104,000)
Tier-1 additionally requires the XBRL concept be revenue/income-ish AND the dimension member
match the KPI's slice token (entity KPIs) or be undimensioned (aggregate KPIs).
"""
import re, json, math


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
    if fmt == '%':
        for f in _round_forms(av):
            forms |= {f + '%', f + ' percent', f + ' percentage points', '(' + f + ')%', '(' + f + ')'}
        bps = av * 100
        if bps == int(bps):
            forms.add(f"{int(bps)} basis points")
        return forms
    ai = int(round(av))
    forms.add(_grp(str(ai))); forms.add(str(ai))
    for div, tag in ((1e3, 'K'), (1e6, 'M'), (1e9, 'B'), (1e12, 'T')):
        if av >= div / 10:
            scaled = av / div; si = int(round(scaled))
            forms.add(_grp(str(si))); forms.add(str(si))
            for f in _round_forms(scaled):
                forms.add(f); forms.add(f + tag)
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
    bigger number on either side. Used by every matcher — do not duplicate this logic."""
    b = text[start-1] if start > 0 else ' '
    a = text[end] if end < len(text) else ' '
    nxt = text[end+1] if end+1 < len(text) else ' '
    if numeric and b in '0123456789.,':
        return False                       # glued to a preceding digit/separator
    if a.isdigit():
        return False
    if a in '.,' and nxt.isdigit():
        return False                       # a thousands separator / decimal continues the number
    return True


def bounded_hit(quote, form):
    """form occurs in quote at a numeric word boundary (not glued inside a bigger number)."""
    numeric = form[0].isdigit() or form[0] in '$('
    for m in re.finditer(re.escape(form), quote):
        if at_boundary(quote, m.start(), m.end(), numeric):
            return True
    return False


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
    if '.' not in s and s.isdigit() and len(s) >= 4:
        return True
    for sc in (1, 1e3, 1e6, 1e9, 1e12):
        if f > 0 and av > 0 and abs(f*sc - av)/av < 0.001:
            return True
    return False


def value_ok(value, fmt, quote):
    """final deterministic self-check: value present at a real boundary AND losslessly."""
    forms = {f for f in value_forms(value, fmt or 'number') if len(f) >= 2}
    for div in (1e6, 1e9):
        xx = abs(float(value)) / div
        if xx >= 1:
            for d in (1, 2):
                forms.add(f"{xx:,.{d}f}")
    hits = [f for f in forms if bounded_hit(quote, f)]
    return any(exact_form(f, value, fmt) for f in hits)


# ---------- Tier-1: XBRL structured ----------
STOP = {'revenue', 'sales', 'the', 'and', 'of', 'by', 'other', 'net', 'income', 'operating',
        'gross', 'profit', 'for', 'from', 'inc', 'corp', 'company', 'revenues', 'change', 'due',
        'to', 'increase', 'decrease', 'number', 'average', 'a', 'an'}
SLICE_STOP = set(STOP) | {'total', 'geography', 'segment', 'ebit', 'type', 'margin', 'price',
                          'volume', 'growth'}
# structural tokens carried by XBRL member names that don't identify a slice
GENERIC_MEM = {'member', 'segment', 'segments', 'consolidation', 'consolidated', 'items', 'axis',
               'reportable', 'entities', 'operating', 'and', 'the', 'of'}


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


def member_tokens(members):
    toks = set()
    for m in members:
        m = m.split(':')[-1]
        m = re.sub(r'Member$', '', m)
        m = re.sub(r'([a-z])([A-Z])', r'\1 \2', m)
        for w in re.findall(r"[A-Za-z]{2,}", m.lower()):
            if w not in GENERIC_MEM:
                toks.add(w)
    return toks


def concept_ok(con):
    cl = (con or '').lower()
    if not any(g in cl for g in ('revenue', 'sales', 'income', 'profit', 'margin', 'operating',
                                 'premium')):
        return False
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


def tier1(xbrls, name, val, per):
    """match an XBRL fact by value+period+dimension member. Deterministic; returns dict or None.
    Collects all facts equal in (concept-type, value, period); picks the best member match, and
    ABSTAINS if two different members tie (genuinely ambiguous)."""
    sval = str(int(round(float(val))))          # SIGNED: a -X KPI must not bind a +X fact
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
                if str(fc.get('value', '')).split('.')[0] != sval:
                    continue
                if (fc.get('period') or {}).get('endDate') != per:
                    continue
                members = seg_members(fc)
                mt = member_tokens(members)
                if kt:
                    score = _member_score(kt, mt)
                    if score is None:
                        continue
                else:
                    if members:              # aggregate KPI must be undimensioned
                        continue
                    score = 0
                mlabel = ", ".join(m.split(':')[-1] for m in members) or "total"
                mkey = frozenset(mt)
                cands.append((score, concept, mlabel, mkey, fc))
    if not cands:
        return None
    cands.sort(key=lambda c: -c[0])
    if kt and len(cands) > 1 and cands[0][0] == cands[1][0] and cands[0][3] != cands[1][3]:
        return None                          # ambiguous tie between different members
    score, concept, mlabel, _, fc = cands[0]
    pe = fc.get('period') or {}
    q = f'{concept} [{mlabel}] [{pe.get("startDate","")}..{pe.get("endDate","")}] = {fc.get("value")}'
    return {'member': mlabel, 'concept': concept, 'quote': q}


# ---------- Tier-2: strict same-row text label ----------
def _toks(n):
    return [t for t in re.findall(r"[A-Za-z]{3,}", n) if t.lower() not in STOP]


def _tableforms(v, fmt):
    s = set(); av = abs(float(v))
    if fmt == '%':
        for d in (0, 1):
            s.add(f"{av:.{d}f}")
        return s
    s.add(f"{int(round(av)):,}")
    for div in (1e6, 1e9):
        x = av / div
        if x >= 1:
            s.add(f"{int(round(x)):,}")
            for d in (1, 2):
                s.add(f"{x:,.{d}f}")
    return {x for x in s if len(x) >= 3}


def _tidy(s):
    """collapse whitespace/zero-width junk; content stays verbatim (same words, same numbers)."""
    return re.sub(r'\s+', ' ', s.replace('​', ' ')).strip()


def row_quote(texts, label_tokens, val, fmt, gap=90):
    """Cleanest verbatim quote: starts at THIS metric's label and runs through the value.
    Every label token must appear within `gap` chars before the value, and the value must sit at
    a numeric boundary. Returns the shortest such quote, or None."""
    lt = [t.lower() for t in label_tokens if t]
    if not lt:
        return None
    forms = _tableforms(val, fmt)
    best = None
    for t in texts:
        low = t.lower()
        for fo in forms:
            for m in re.finditer(re.escape(fo), t):
                if not at_boundary(t, m.start(), m.end()):
                    continue
                ws = max(0, m.start() - gap)
                seg = low[ws:m.start()]
                pos = [seg.find(tok) for tok in lt]
                if any(p < 0 for p in pos):
                    continue                      # some label token missing -> not this row
                q = _tidy(t[ws + min(pos): m.end()])
                if best is None or len(q) < len(best):
                    best = q                      # shortest = tightest crop around the row
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


def scan_text(texts, name, val, fmt, max_hits=20, keep=6):
    """(clean_label_anchored_quote_or_None, up_to_`keep` candidate snippets).
    Collects up to max_hits boundary-valid occurrences, each windowed back to its header/label,
    then RANKS so the identifying candidate wins: a snippet that carries a table header and/or the
    KPI's own label tokens ranks above a bare occurrence — because a shared value (e.g. a capex
    figure that also appears as a prior-year column elsewhere) must surface its header row, not just
    its first textual hit."""
    nt = _toks(name); ntl = [x.lower() for x in nt]
    strict = row_quote(texts, nt, val, fmt)
    forms = _tableforms(val, fmt)
    cands = []
    for t in texts:
        for fo in forms:
            for m in re.finditer(re.escape(fo), t):
                if not at_boundary(t, m.start(), m.end()):
                    continue
                ws = _snippet_start(t, m.start(), nt)
                snip = _tidy(t[ws:m.end()+80])
                low = snip.lower()
                score = (2 if '##TABLE_START' in snip else 0) + sum(1 for tk in ntl if tk in low)
                cands.append((score, len(snip), snip))
                if len(cands) >= max_hits:
                    break
            if len(cands) >= max_hits:
                break
        if len(cands) >= max_hits:
            break
    cands.sort(key=lambda c: (-c[0], c[1]))            # higher score first, then shorter
    return strict, [c[2] for c in cands[:keep]]


def is_derived(kpi):
    """fiscal.ai-computed rows (% change, common size). No filing states them -> never linkable."""
    return ('% Chg' in kpi) or ('%Chg' in kpi) or ('Common Size' in kpi)


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
        tt = _tidy(t)
        i = tt.find(quote)                            # quote came from _tidy(source) -> substring
        if i < 0:                                     # LLM may have reformatted; relocate by value
            i = -1
            for f in forms:
                for m in re.finditer(re.escape(f), tt):
                    if at_boundary(tt, m.start(), m.end()):
                        i = m.start(); break
                if i >= 0:
                    break
            if i < 0:
                continue
        ts = tt.rfind('##TABLE_START', 0, i)
        te = tt.find('##TABLE_END', i)
        if ts >= 0 and te >= 0 and (te - ts) < 6000:  # a real, bounded table
            return tt[ts:te + len('##TABLE_END')]
        return tt[max(0, i-1400):i + 500]             # no markers -> generous window
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
    print("link_lib self-check OK")
