"""Neutral locator entrypoint (Universal Locator v5.5 §2-§3; WP2).

THREE responsibilities, all pure, no I/O, ZERO fiscal.ai/channel imports, ZERO Core imports:
1. PRODUCTION anchor rebuild (`rebuild_anchor`) — ids are DECODED here independently; only
   Core composes them. Anchors rebuilt on demand; nothing stored; no registry.
2. THE single strict XBRL dimension parser (`seg_parse`) — relocated verbatim from link_lib;
   both channel files import it from here.
3. THE single strict value-unknown fact matcher (`match_facts` / `match_facts_explain`) —
   pair-complete identity; xbrl_lane delegates to it as a thin adapter.

Anchor identity = the 7 fields: company (via the fact's OWN parsed source id looked up in a
TRUSTED edge map — the exactly-one graph-edge query's output) · driver · fact_type=metric ·
slice · measurement · series_unit · time_type.
Search clues (NON-authoritative, retrieval only, never proof): wording = the Driver's immutable
definitional_evidence.birth_quotes PRIMARY, the stored fact quote as fallback (LWW, hence
fallback only) · the PRIOR QNAME, supplied BY an ACTIVE ConceptResolution when exactly one
exists (the ConceptResolution is the carrier of the qname clue, not a separate clue kind).
NO prior (axis, member) pairs — old XBRL dimensions are never reused; each target source proves
its own complete address.

Prove-or-stop: any unreconstructable identity field raises ValueError naming the SMALLEST
missing piece — never patched with a registry, never guessed. Malformed inputs (non-mapping
containers, blank/padded ids) raise clean ValueError — never an anchor, never a crash.
"""
from collections.abc import Mapping

_ALLOWED_SLOTS = ("period", "slice", "measurement", "quote_hash")   # metric-only: surprise= forbidden
_TIME_TYPES = ("duration", "instant")
_VALUE_SLOTS = ("level_low", "level_high", "change_value",
                "comparison_low", "comparison_high")   # mirrors Core writer _NUMERIC_SIG (data
                                                       # shape only — no Core import); numeric-
                                                       # ness derives from STORED slots via
                                                       # `is not None` so a stored ZERO counts


def rebuild_anchor(fact_id, props, driver_node, edge_map, concept_resolutions=()):
    """(anchor, stripped_slots) rebuilt from ONE stored fact — or ValueError (fail closed).

    props            : stored fact node fields {fact_scope, series_unit, time_type,
                       level_low/level_high/change_value/comparison_low/comparison_high, quote}
    driver_node      : {name, fact_type, definitional_evidence: {birth_quotes: [...]}}
    edge_map         : {source_id: company_key} — the ONLY way a company enters
    concept_resolutions: ACTIVE ConceptResolution qnames for this Driver; >1 = ambiguous = fail;
                       a sole clue must be a nonblank string

    Numeric-ness is DERIVED from the stored value slots (never caller-asserted): any slot
    `is not None` → numeric → series_unit must be a NONBLANK string; all None → numberless →
    series_unit MUST be None (a unit on a numberless fact is a contradiction — fail closed).
    Wording fallback comes ONLY from the stored fact's props["quote"] (LWW) — there is no
    caller-supplied quote channel.
    """
    for ok, what in ((isinstance(fact_id, str), "fact_id must be a string"),
                     (isinstance(props, Mapping), "props must be a mapping"),
                     (isinstance(driver_node, Mapping), "driver_node must be a mapping"),
                     (isinstance(edge_map, Mapping), "edge_map must be a mapping")):
        if not ok:                             # the input-schema guard: malformed inputs
            raise ValueError(f"malformed input: {what}")   # raise cleanly, never crash
    seg = fact_id.split(":", 3)
    if len(seg) != 4 or seg[0] != "du":
        raise ValueError(f"bad id shape: {fact_id!r}")
    _, source_id, driver, scope = seg
    if not source_id.strip():
        raise ValueError(f"malformed id: blank source id in {fact_id!r}")
    if not driver.strip():
        raise ValueError(f"malformed id: blank driver name in {fact_id!r}")
    for key in ("fact_scope", "series_unit", "time_type") + _VALUE_SLOTS:
        if key not in props:                # ALL five value slots must be PRESENT — explicit
            raise ValueError(f"missing identity field: props[{key!r}]")   # None is the only
                                            # legal "no value"; absent keys = missing data,
                                            # never silently "numberless"
    if props["fact_scope"] != scope:
        raise ValueError(f"stored fact_scope != id suffix: {props['fact_scope']!r} vs {scope!r}")
    parsed = {}
    for slot in scope.split("|"):
        k, _, v = slot.partition("=")
        if k not in _ALLOWED_SLOTS:
            raise ValueError(f"metric-only decoder: forbidden/unknown slot {k!r}")
        if k in parsed:
            raise ValueError(f"duplicate slot {k!r}")
        parsed[k] = v
    if "period" not in parsed:
        raise ValueError("missing identity field: period slot")
    if driver_node.get("name") != driver:
        raise ValueError(f"Driver node name {driver_node.get('name')!r} != id driver {driver!r}")
    if driver_node.get("fact_type") != "metric":
        raise ValueError(f"not a metric Driver: {driver_node.get('fact_type')!r}")
    if props["time_type"] not in _TIME_TYPES:
        raise ValueError(f"missing identity field: time_type {props['time_type']!r} "
                         f"is not one of {_TIME_TYPES}")
    numeric = any(props.get(s) is not None for s in _VALUE_SLOTS)
    su = props["series_unit"]
    if numeric and (not isinstance(su, str) or not su.strip()):
        raise ValueError(f"numeric fact lacking nonblank series_unit (got {su!r}; "
                         f"series_unit=None is legal ONLY for numberless metrics)")
    if not numeric and su is not None:
        raise ValueError(f"numberless fact must carry series_unit=None, got {su!r} "
                         f"(a unit with no stored value slots is a contradiction)")
    company = edge_map.get(source_id)
    if company is None:
        raise ValueError(f"no company edge for THIS fact's source id {source_id!r} "
                         f"(cross-wired or missing edge)")
    if isinstance(company, str) and not company.strip():
        raise ValueError(f"blank company id for source {source_id!r} — corrupt edge, fail closed")
    if not isinstance(company, str) or company != company.strip():
        raise ValueError(f"malformed company id {company!r} — must be a nonblank, "
                         f"unpadded string")
    de = driver_node.get("definitional_evidence")
    if de is None:
        de = {}
    elif not isinstance(de, Mapping):
        raise ValueError(f"malformed input: definitional_evidence must be a mapping, "
                         f"got {type(de).__name__}")
    bq = de.get("birth_quotes", ())
    if not isinstance(bq, (list, tuple)):
        raise ValueError(f"malformed birth_quotes: expected list/tuple of nonblank strings, "
                         f"got {type(bq).__name__}")      # a bare string iterates into LETTERS
    if any(not isinstance(q, str) or not q.strip() for q in bq):
        raise ValueError("malformed birth_quotes: blank or non-string member")
    if bq:
        wording = tuple(bq)
    else:
        sq = props.get("quote")                      # the STORED fact quote (LWW) — the ONLY
        if isinstance(sq, str) and sq.strip():       # fallback; no caller-supplied channel
            wording = (sq,)
        else:
            raise ValueError("blank wording clues: no birth_quotes and no stored fact quote")
    if not isinstance(concept_resolutions, (list, tuple)):
        raise ValueError(f"malformed ConceptResolution clues: expected list/tuple, got "
                         f"{type(concept_resolutions).__name__}")   # a bare string iterates
                                                                    # into CHARACTERS; None crashes
    actives = tuple(concept_resolutions)
    if len(actives) > 1:
        raise ValueError(f"{len(actives)} ACTIVE ConceptResolutions — ambiguous, fail closed")
    if actives and (not isinstance(actives[0], str) or not actives[0].strip()):
        raise ValueError(f"malformed ConceptResolution clue: {actives[0]!r} "
                         f"(must be a nonblank string)")
    anchor = {
        "source_id": source_id,
        "company": company,
        "driver": driver,
        "slice": parsed.get("slice", ""),
        "measurement": parsed.get("measurement", ""),
        "series_unit": props["series_unit"],
        "time_type": props["time_type"],
        "fact_type": driver_node["fact_type"],
        "wording": wording,
        "concept_clue": actives[0] if actives else None,   # RETRIEVAL only — never proof
    }
    return anchor, sorted(k for k in ("period", "quote_hash") if k in parsed)


# ---------- THE single strict XBRL dimension parser (WP2 step 2: relocated VERBATIM from ----------
# ---------- link_lib — "one parser truly one"; link_lib AND xbrl_lane import from HERE ----------
def _nb(x):
    """nonblank UNPADDED string — the ONLY legal axis/member form (round-23: whitespace and
    numeric axes were binding; round-24: padded names are malformed storage, census 0/47,152)."""
    return isinstance(x, str) and bool(x.strip()) and x == x.strip()


def seg_parse(fc):
    """(pairs, complete) — THE single all-shapes segment parser (round-23: the strict form;
    relocated here WP2 step 2, body byte-identical).
    pairs = [(axis_qname, member_qname)] across ALL four storage shapes: {dimension,value},
    single explicitMember.$t, the multi-axis explicitMember-LIST, explicitMember-as-bare-string.
    complete = every entry (and every list element) parsed to >=1 pair AND every axis/member is a
    NONBLANK STRING. A nonempty segment with complete=False must NEVER bind anywhere — a missed
    extraction must not masquerade as consolidated (ChannelContract §3 / OD-17c), and a partially
    parsed fact's slice identity is unprovable. FETCH-only: raw axis+member; the shared
    decomposer classifies downstream."""
    seg = fc.get('segment')
    if not seg:
        return [], True
    items = seg if isinstance(seg, list) else [seg]
    out, complete = [], True
    for s in items:
        if not isinstance(s, dict):
            complete = False
            continue
        if 'value' in s and 'explicitMember' in s:
            complete = False               # round-24: an entry MIXING storage formats is
            continue                       # malformed (census 0/47,152 — zero real cost)
        got = 0
        if 'value' in s:
            if _nb(s.get('dimension')) and _nb(s.get('value')):
                out.append((s['dimension'], s['value'])); got += 1
            else:
                complete = False
        em = s.get('explicitMember')
        if isinstance(em, list):                         # multi-axis: explicitMember is a LIST
            for m in em:
                if isinstance(m, dict) and _nb(m.get('dimension')) and _nb(m.get('$t')):
                    out.append((m['dimension'], m['$t'])); got += 1
                else:
                    complete = False
        elif isinstance(em, dict):
            if _nb(em.get('dimension')) and _nb(em.get('$t')):
                out.append((em['dimension'], em['$t'])); got += 1
            else:
                complete = False
        elif isinstance(em, str):                        # bare string: the axis sits on `s`
            if _nb(s.get('dimension')) and _nb(em):
                out.append((s['dimension'], em)); got += 1
            else:
                complete = False
        elif em is not None:
            complete = False
        if got == 0:
            complete = False                             # an entry that yields nothing
    axes = [a for a, _ in out]
    if len(axes) != len(set(axes)):
        complete = False                   # round-24: a REPEATED AXIS is not a valid complete
                                           # dimension address (census 0/47,152)
    return out, complete


# ---------- THE quote-proof group (WP2 Chunk 1: row_quote's complete closure, relocated ----------
# ---------- VERBATIM from link_lib — one implementation each; link_lib re-exports)      ----------
import json
import re
import exact_numbers as XN


def _grp(n):
    neg = n.startswith('-'); n = n.lstrip('-'); out = ''
    while len(n) > 3:
        out = ',' + n[-3:] + out; n = n[:-3]
    return ('-' if neg else '') + n + out


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


def row_quote(texts, label_tokens, val, fmt, gap=90, scale_gate=False, with_context=False):
    """Cleanest verbatim quote: starts at THIS metric's label and runs through the value.
    Every label token must appear within `gap` chars before the value, and the value must sit at
    a numeric boundary. Returns the shortest such quote, or None.
    scale_gate (round-13, opt-in — certified benchmark callers keep legacy behavior): a bare
    SCALED form binds only with scale evidence (section _SCALE_MARK, or the tag immediately after
    the hit); %-format and full-magnitude/zero forms are exempt."""
    lt = [t.lower() for t in label_tokens if t]
    if not lt:
        return (None, None) if with_context else None
    forms = _tableforms(val, fmt)
    needy = ({f: _required_div(f, val) for f in forms if _required_div(f, val)}
             if scale_gate and fmt != '%' else {})
    best = None
    collected = []                         # round-25/26: (start, end, q, t) per qualifying occurrence
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
                if with_context:
                    # round-24/25: collect EVERY qualifying occurrence FIRST (the round-23 tie
                    # only compared IDENTICAL quote strings — a wording variant bypassed the law)
                    collected.append((m.start(), m.end(), q, t))
                elif best is None or len(q) < len(best) or (len(q) == len(best) and q < best):
                    best = q                      # certified default: byte-identical legacy
    if not with_context:
        return best
    if not collected:
        return None, None
    # round-25 SIGNATURE law (reviewer-reproduced: a comparative row prints TWO facts with
    # coincidence-equal values under one context — context-set equality wrongly bound): an
    # occurrence IS (full source text, value start, value end). EXACT duplicate signatures
    # (identical texts) may bind; >1 DISTINCT signature is unattributable -> ABSTAIN. The
    # round-24 overlap-merge is REMOVED as unused complexity (its premise was false:
    # _tableforms carries no dollar forms, so one printed number yields one match).
    sigs = {(t, s0, e0) for s0, e0, q, t in collected}
    if len(sigs) > 1:
        return None, None
    t, s0, e0 = next(iter(sigs))
    qs = [q for s, e, q, tt in collected if (tt, s, e) == (t, s0, e0)]
    return min(qs, key=lambda q: (len(q), q)), t[_snippet_start(t, s0, label_tokens): e0 + 80]


def _table_active_start(t, pos, cap=2600):
    """THE single 'is a table still open at pos' check (round-22): the last ##TABLE_START within
    cap chars before pos, provided no ##TABLE_END closed it before pos; else -1. Used by BOTH
    snippet/context windowing and candidate ranking — one law, no sibling logic."""
    ts = t.rfind('##TABLE_START', max(0, pos - cap), pos)
    if ts >= 0 and t.find('##TABLE_END', ts, pos) < 0:
        return ts
    return -1


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
    for tok in label_tokens:                          # (a) label-token reach — WHOLE WORDS
        tl = tok.lower()                              # (round-21: substring reach anchored on
        pat = re.compile(r'(?<![a-z0-9])' + re.escape(tl) + r'(?![a-z0-9])')   # 'net' inside
        if pat.search(near):                          # 'internet')
            continue
        region = low[max(0, hit_start - maxback):hit_start]
        last = None
        for mm in pat.finditer(region):
            last = mm
        if last is not None:
            start = min(start, max(0, hit_start - maxback) + last.start())
    ts = _table_active_start(t, hit_start, table_cap)  # (b) table-header reach — round-22: ONLY
    if ts >= 0:                                        # while that table is STILL OPEN; a closed
        start = min(start, ts)                         # table's heading never travels into prose
    return start


# ---------- the value-proof gate (WP2 Chunk-2 corrective: value_ok closure, verbatim ----------
# ---------- from link_lib — ONE exact value-proof rule for sign/percent/scale/boundary) ------
import math

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


# ---------- THE strict value-unknown fact matcher (WP2: PAIR-COMPLETE, neutral home) ----------


def _fact_rows(xbrls):
    """(concept_key, fact_dict) across blobs — mirrors the certified iteration exactly
    (unparseable blobs skipped; dict-of-concept → list-or-single facts)."""
    for blob in xbrls:
        try:
            d = json.loads(blob)
        except (ValueError, TypeError):
            continue
        if isinstance(d, dict):
            for con, facts in d.items():
                for fc in (facts if isinstance(facts, list) else [facts]):
                    if isinstance(fc, dict):
                        yield con, fc


def _period_ok(fc, ps, pe, instant):
    """exactly ONE valid period shape; a fact carrying BOTH instant and duration dates is
    malformed and never a candidate (tier1 parity, round-29 law). A NON-MAPPING period
    container (string/int/list — the reproduced AttributeError crash class) never binds."""
    p = fc.get('period')
    if p is None:
        p = {}
    elif not isinstance(p, Mapping):
        return False
    mixed = (p.get('instant') is not None) and (p.get('startDate') is not None
                                                or p.get('endDate') is not None)
    if mixed:
        return False
    if instant:
        return p.get('instant') == ps
    return p.get('startDate') == ps and p.get('endDate') == pe


def _concept_ok(stored_key, req_prefix, con):
    """exact concept identifier AS STORED: local names compare exactly; prefixed request vs
    BARE storage matches by local name (the verified 109/109 storage convention); prefixed vs
    prefixed must be EXACT; a BARE request NEVER matches prefixed storage (a bare ask cannot
    verify a namespace — 'Revenues' must not accept 'evil:Revenues')."""
    c_prefix, _, c_local = stored_key.rpartition(':')
    if c_local != con:
        return False
    if c_prefix and not req_prefix:
        return False
    return not (c_prefix and req_prefix and c_prefix != req_prefix)


_BAD_UNIT = object()


def _norm_unit(u):
    """Unit ids are CASE-SENSITIVE (XBRL unitRef is an XML IDREF; corpus-live: PSEG carries
    usdPerMWh vs usdPerMwh as DIFFERENT units in one filing) — normalization is STRIP ONLY.
    None passes through (the caller decides whether unit-less is legal); any non-string or
    blank shape is MALFORMED → _BAD_UNIT (never a candidate; the list-unitRef crash class
    dies here)."""
    if u is None:
        return None
    if isinstance(u, str) and u.strip():
        return u.strip()
    return _BAD_UNIT


def _valid_pairs(pairs):
    """request-pair schema: a list/tuple of (axis, member) pairs — each a TUPLE OR LIST of
    exactly two nonblank unpadded strings (lists because JSON round-trips tuples into inner
    lists; canonicalized to tuples here) — with no repeated axis (which also kills duplicate
    pairs). Returns the canonical tuple list or None (malformed → the caller abstains
    'bad_request_pairs' — never a crash, never a silent frozenset collapse)."""
    if not isinstance(pairs, (list, tuple)):
        return None
    out = []
    for p in pairs:
        if not (isinstance(p, (tuple, list)) and len(p) == 2 and _nb(p[0]) and _nb(p[1])):
            return None
        out.append((p[0], p[1]))
    axes = [a for a, _ in out]
    if len(axes) != len(set(axes)):
        return None
    return out


def match_facts_explain(xbrls, concept_qname, pairs, period_start, period_end, unit_ref=None,
                        expected_unit=None):
    """(value|None, reason) for the FULL identity — exact concept identifier AS STORED +
    COMPLETE (axis,member) PAIRS + exactly one valid period shape + NORMALIZED unit + exact
    Decimal on the RAW stored value (floats are rejected by XN.dec — never laundered through
    str()). Reasons: ok · bad_request_pairs · bad_request_unit · bad_request_period ·
    nonnumeric_value · concept_missing (nothing matched the concept) · no_candidate (concept
    matched, later filters emptied) · ambiguous_values · unit_conflict. The wrong-axis class
    dies here: a right member under a wrong axis never matches."""
    req_prefix, _, con = concept_qname.rpartition(':')
    vp = _valid_pairs(pairs)
    if vp is None:
        return None, 'bad_request_pairs'          # malformed request address: never guess
    want = frozenset(vp)
    req_unit = _norm_unit(unit_ref)
    if req_unit is _BAD_UNIT:
        return None, 'bad_request_unit'           # malformed request-side unit: never guess
    try:
        ps, pe = XN.period_key(period_start, period_end)
    except XN.ExactError:
        return None, 'bad_request_period'
    instant = (ps == pe)
    vals, units = set(), set()
    hit_concept = False
    for c, fc in _fact_rows(xbrls):
        if not _concept_ok(c, req_prefix, con):
            continue
        hit_concept = True
        u = _norm_unit(fc.get('unitRef'))
        if u is None or u is _BAD_UNIT:
            continue                  # a NUMERIC candidate must carry a nonblank string unit
                                      # (census: 88,236 numeric gate facts, zero unit-less —
                                      # zero recall cost); malformed shapes likewise never bind
        if unit_ref is None:          # expected_unit is a HEURISTIC for unit_ref-less asks
            u_cf = u.casefold()       # only — an exact unit_ref is AUTHORITATIVE and must
            money_marked = 'usd' in u_cf or 'dollar' in u_cf        # never be vetoed by it.
            if expected_unit == 'money' and not money_marked:       # 'dollar' is graph-
                continue              # verified money (U_UnitedStatesOfAmericaDollarsShare =
                                      # 38,041 facts, ALL iso4217:USDshares; the global
                                      # dollar-sweep shows every dollar-named unit is
                                      # money-denominated). Opaque ids (Unit12/Unit1/Unit16,
                                      # 527 gate facts) fail every substring guess → abstain.
            if expected_unit == 'nonmoney' and (money_marked or 'share' not in u_cf):
                continue              # nonmoney needs POSITIVE share evidence (census: every
                                      # genuine nonmoney unit in the 88,236-fact gate corpus
                                      # is a shares variant) AND must exclude BOTH money
                                      # markers; foreign currencies (cny/eur/U_AUD) abstain.
        if not _period_ok(fc, ps, pe, instant):
            continue
        _pairs, _complete = seg_parse(fc)
        if not _complete:
            continue                  # unparseable/partial segments never pose as undimensioned
        if frozenset(_pairs) != want:
            continue                  # COMPLETE pairs — axis AND member must both match
        if unit_ref is not None and u != req_unit:
            continue
        try:
            v = XN.dec(fc.get('value'))           # RAW — XN.dec rejects floats/None (lossy)
        except XN.ExactError:
            return None, 'nonnumeric_value'       # non-numeric collision -> not resolvable
        vals.add(v)
        units.add(u)
    if not vals:
        return (None, 'concept_missing') if not hit_concept else (None, 'no_candidate')
    if len(vals) != 1:
        return None, 'ambiguous_values'           # unique or abstain
    if unit_ref is None and len(units) > 1:
        return None, 'unit_conflict'              # same value under conflicting units
    return next(iter(vals)), 'ok'


def match_facts(xbrls, concept_qname, pairs, period_start, period_end, unit_ref=None,
                expected_unit=None):
    """the value-only form of match_facts_explain (production callers)."""
    return match_facts_explain(xbrls, concept_qname, pairs, period_start, period_end,
                               unit_ref=unit_ref, expected_unit=expected_unit)[0]


# ---------- THE neutral locate entrypoint (WP2 Chunk 2: routes R1 + R2, v5.5 §3) ----------
def _wording_tokens(anchor):
    """retrieval-only label tokens from the anchor's wording clues — built from each clue's
    LABEL PORTION (the text BEFORE its first digit). Mechanical rule, no stop-word list."""
    toks = []
    for w in anchor.get('wording') or ():
        if isinstance(w, str):
            m = re.search(r'\d', w)
            label_part = w[:m.start()] if m else w
            for tk in re.findall(r"[A-Za-z]{3,}", label_part):
                tl = tk.lower()
                if tl not in toks:
                    toks.append(tl)
    return toks


def _ident_tokens(field):
    """identity tokens from an anchor slice/measurement field ('geography:united_states' ->
    united/states): alpha>=3 from the value part, '_'-split. Mechanical, no vocabulary."""
    if not isinstance(field, str) or not field.strip():
        return []
    val = field.split(':', 1)[-1]
    return [tk.lower() for tk in re.findall(r"[A-Za-z]{3,}", val.replace('_', ' '))]


def _fact_period(fc):
    """('duration'|'instant', ps, pe) for a VALID single-shape stored period, else None."""
    p = fc.get('period')
    if p is None or not isinstance(p, Mapping):
        return None
    inst, sd, ed = p.get('instant'), p.get('startDate'), p.get('endDate')
    if inst is not None and (sd is not None or ed is not None):
        return None
    try:
        if inst is not None:
            ps, pe = XN.period_key(inst, inst)
            return ('instant', ps, pe)
        if sd is not None and ed is not None:
            ps, pe = XN.period_key(sd, ed)
            return None if ps == pe else ('duration', ps, pe)
    except XN.ExactError:
        return None
    return None


def _span_days(shape):
    from datetime import date
    if shape[0] != 'duration':
        return None
    a = date.fromisoformat(shape[1][:10]); b = date.fromisoformat(shape[2][:10])
    return (b - a).days + 1


def _span_class(shape):
    d = _span_days(shape)
    if d is None:
        return None
    if d <= 100:
        return 'q'
    if d >= 350:
        return 'a'
    return None


def _unit_class(u):
    """corrective 2: the CLASS of a unit string, census/spec-earned markers only — share wins
    over money (dollars-PER-SHARE is not plain money); UNKNOWN (opaque ids) proves nothing:
    graph-verified, Unit12 alone maps to FIVE incompatible meanings (USD 41,984 · shares 506 ·
    pure 126 · employee 15) and U_EUR (1,229 facts) is money-but-not-USD."""
    if not isinstance(u, str):
        return None
    c = u.casefold()
    if 'share' in c:
        return 'share'
    if 'usd' in c or 'dollar' in c:
        return 'money'
    if 'percent' in c or 'pure' in c:
        return 'percent'
    if 'count' in c:
        return 'count'
    return None


_QUARTER_WORD = re.compile(r'(?<![a-z])(?:quarter|three months)(?![a-z])', re.I)
_ANNUAL_WORD = re.compile(r'(?<![a-z])(?:full year|annual|year ended|fiscal year|year)(?![a-z])', re.I)


def _value_span_in(text, q, val, fmt):
    """absolute (start, end) of the value's LAST bounded printed occurrence of q inside text,
    or None. q must be a slice of text (single-occurrence by the signature law)."""
    if q not in text:
        return None
    base = text.index(q)
    best = None
    for fo in sorted(_tableforms(val, fmt)):
        for m in re.finditer(re.escape(fo), q):
            if at_boundary(q, m.start(), m.end()) and (best is None or m.start() > best[0]):
                best = (m.start(), m.end())
    if best is None:
        return None
    return base + best[0], base + best[1]


def _period_word_class(text, vstart, vend):
    """corrective 2 — the printed-period signal for ONE value occurrence: within the value's
    own CLAUSE ([.;\n]-delimited), the NEAREST quarter-class or annual-class wording (either
    side of the value) decides; none present = no signal. Calendar-STRUCTURAL patterns only;
    the nearest-wins rule keeps certified two-clause window bleed harmless (both words in one
    clause -> the one beside the value governs)."""
    cs = max(text.rfind('.', 0, vstart), text.rfind(';', 0, vstart),
             text.rfind('\n', 0, vstart)) + 1
    ce_cands = [i for i in (text.find('.', vend), text.find(';', vend),
                            text.find('\n', vend)) if i >= 0]
    ce = min(ce_cands) if ce_cands else len(text)
    clause = text[cs:ce]
    best = None
    for cls, pat in (('q', _QUARTER_WORD), ('a', _ANNUAL_WORD)):
        for m in pat.finditer(clause):
            a0, a1 = cs + m.start(), cs + m.end()
            dist = (vstart - a1) if a1 <= vstart else (a0 - vend) if a0 >= vend else 0
            if best is None or dist < best[0]:
                best = (dist, cls)
    return best[1] if best else None


def _extend_label_start(ctx, q, known):
    """(extended_quote, extension_words) — extend the quote's start backward over
    IMMEDIATELY-PRECEDING words that are CAPITALIZED or (case-insensitively) match a KNOWN
    anchor token (wording/slice/measurement) — lowercase prose connectives never travel, but
    lowercase 'adjusted' satisfying an adjusted anchor does. Mechanical; exact slices."""
    if not ctx or q not in ctx:
        return q, []
    i = ctx.index(q)
    j = i
    while True:
        m = re.search(r"([A-Za-z][A-Za-z'-]*)\s+$", ctx[:j])
        if not m:
            break
        w = m.group(1)
        if not (w[0].isupper() or w.lower() in known):
            break
        j = m.start(1)
    ext = ctx[j:i]
    words = [w.lower() for w in re.findall(r"[A-Za-z]{3,}", ext)]
    return ((ext + q) if ext else q), words


def _row_label(q, val, fmt):
    """the printed ROW LABEL = the quote up to its (last bounded) value occurrence — an exact
    target-source slice, never anchor wording."""
    best = None
    for fo in sorted(_tableforms(val, fmt)):
        for m in re.finditer(re.escape(fo), q):
            if at_boundary(q, m.start(), m.end()) and (best is None or m.start() > best):
                best = m.start()
    if best is None:
        return None
    return q[:best].rstrip(" \t$:(\u2013\u2014-") or None


def _prove(texts, tokens, val, fmt):
    """(quote, context, verdict) — verdict: 'ok' | 'ambiguous' | 'absent'. ONE row_quote
    implementation used twice + the ONE certified value-proof rule (value_ok) + the ported
    negative-notation sign law. Never a second matcher."""
    q, ctx = row_quote(texts, tokens, val, fmt, scale_gate=True, with_context=True)
    if q is not None:
        if not value_ok(val, fmt, q):
            return None, None, 'absent'
        if float(val) < 0:
            forms = value_forms(val, fmt or 'number')
            if not any(printed_negative(q, f) for f in forms if bounded_hit(q, f)):
                return None, None, 'absent'
        return q, ctx, 'ok'
    legacy = row_quote(texts, tokens, val, fmt, scale_gate=True)
    return None, None, ('ambiguous' if legacy is not None else 'absent')


def _nb_str(x):
    return isinstance(x, str) and bool(x.strip()) and x == x.strip()


_CAMEL = re.compile(r'[A-Z]?[a-z]+|[A-Z]+(?![a-z])')


def _context_tied(concept_local, q):
    """corrective 2: XBRL context may attach only when EVERY >=4-char camelCase token of the
    fact's OWN stored name appears in the quote (substring either direction) — one generic
    shared word ('operating', 'current') never carries a structured tag. Reduced attachment
    is the accepted cost: unattached items stay valid text evidence."""
    ql = q.lower()
    qwords = set(re.findall(r"[a-z]{4,}", ql))
    toks = [tk.lower() for tk in _CAMEL.findall(concept_local) if len(tk) >= 4]
    if not toks:
        return False
    return all(tl in ql or any(tl in w or w in tl for w in qwords) for tl in toks)


def _finite(v):
    """the WP1 round-13/14 invalid_value law: the 1e309 class is Decimal-finite but
    float-infinite — abstain cleanly, never crash or bind."""
    try:
        return math.isfinite(float(v))
    except (OverflowError, ValueError):
        return False


def locate(anchor, source, hints=None):
    """(anchor, ONE source payload, optional UNTRUSTED hints) →
    {'items': [...], 'status': None | 'no_proven_match' | 'ambiguous' |
    'insufficient_identity'} — v5.5 §3; reads ONLY the given payload. EVERY present anchor
    identity field is enforced: time shape filters candidacy; the UNIT-CLASS law requires the
    fact unit's class to EQUAL the series-unit class (unknown/opaque abstains); an EMPTY slice
    = the AGGREGATE series — dimensioned facts never bind it; slice/measurement tokens must
    appear in the quote; words the label-extension adds must be EXPLAINED by anchor tokens;
    printed period wording beside the value must not contradict the XBRL period (nearest
    period word in the value's clause decides; equal-valued Q/FY facts with separately printed
    occurrences resolve to two items via per-clause proof). Percent-class anchors prove in
    percent format. XBRL context attaches only on a full name-tie; bare names never promote.
    R2 hints: nonblank unpadded stamps both sides, text-proven, no xbrl, ambiguity abstains."""
    if not isinstance(anchor, Mapping) or not isinstance(source, Mapping):
        return {'items': [], 'status': 'insufficient_identity'}
    tokens = _wording_tokens(anchor)
    if not tokens:
        return {'items': [], 'status': 'insufficient_identity'}
    texts = [t for t in (source.get('texts') or ()) if isinstance(t, str) and t]
    want_ptype = anchor.get('time_type')
    slice_toks = _ident_tokens(anchor.get('slice'))
    meas_toks = _ident_tokens(anchor.get('measurement'))
    ident_toks = slice_toks + meas_toks
    known = set(tokens) | set(ident_toks)
    anchor_ucls = _unit_class(anchor.get('series_unit'))
    fmt = '%' if anchor_ucls == 'percent' else None
    clue = anchor.get('concept_clue')
    clue_local = clue.rpartition(':')[2] if isinstance(clue, str) and clue.strip() else None
    items, saw_ambiguous = [], False

    def emit(cand, q, ctx):
        c, spairs, shape, u = cand
        q2, ext_words = _extend_label_start(ctx, q, known)
        if any(w not in known for w in ext_words):
            return None              # an UNEXPLAINED leading qualifier is unproven identity
        low_q = q2.lower()
        if ident_toks and not all(
                re.search(r'(?<![a-z0-9])' + re.escape(tk) + r'(?![a-z0-9])', low_q)
                for tk in ident_toks):
            return None
        span = _value_span_in(ctx, q, v, fmt) if ctx and q in ctx else None
        if span is not None:
            wcls = _period_word_class(ctx, span[0], span[1])
            scls = _span_class(shape)
            if wcls and scls and wcls != scls:
                return None          # printed period wording contradicts the XBRL period
        lbl = _row_label(q2, v, fmt)
        if lbl is None:
            return None
        item = {'raw_label': lbl, 'value': v, 'quote': q2, 'period_evidence': ctx}
        prefix, _, local = c.rpartition(':')
        if prefix and _context_tied(local, q2):
            item['xbrl'] = {'concept': c, 'axis_members': list(spairs),
                            'period_start': shape[1], 'period_end': shape[2],
                            'ptype': shape[0], 'unit': u}
        return item

    by_value = {}
    for c, fc in _fact_rows(source.get('xbrls') or ()):
        if clue_local is not None and c.rpartition(':')[2] != clue_local:
            continue
        shape = _fact_period(fc)
        if shape is None or shape[0] != want_ptype:
            continue
        u = _norm_unit(fc.get('unitRef'))
        if u is None or u is _BAD_UNIT:
            continue
        if _unit_class(u) != anchor_ucls or anchor_ucls is None:
            continue                 # the unit-class law: positive class equality or abstain
        pairs, complete = seg_parse(fc)
        if not complete:
            continue
        if not slice_toks and pairs:
            continue                 # an EMPTY slice = the AGGREGATE series: dimensioned
                                     # facts never bind it (tier1's aggregate law, ported)
        try:
            v = XN.dec(fc.get('value'))
        except XN.ExactError:
            continue
        if not _finite(v):
            continue                 # the 1e309 large-number class
        key = (c, frozenset(pairs), shape, u)
        by_value.setdefault(v, {})[key] = (c, tuple(sorted(tuple(p) for p in pairs)), shape, u)
    for v in sorted(by_value, key=str):
        cands = by_value[v]
        q, ctx, verdict = _prove(texts, tokens, v, fmt)
        if verdict == 'ok':
            if len(cands) > 1:
                saw_ambiguous = True
                continue
            it = emit(next(iter(cands.values())), q, ctx)
            if it is not None:
                items.append(it)
            continue
        if verdict == 'ambiguous' and len(cands) == 2:
            # equal-valued Q and FY facts, SEPARATELY printed with their own period wording:
            # re-prove PER CLAUSE (row_quote REUSED on clause slices — never copied) and
            # attribute each proven clause by its period-word class; anything short of a
            # perfect one-to-one pairing stays ambiguous.
            by_cls = {_span_class(cand[2]): cand for cand in cands.values()}
            if set(by_cls) == {'q', 'a'}:
                found, clean = {}, True
                for t in texts:
                    pos = 0
                    for piece in re.split(r'(?<=[.;\n])', t):
                        if piece.strip():
                            qq, cctx, verd = _prove([piece], tokens, v, fmt)
                            if verd == 'ok':
                                span = _value_span_in(piece, qq, v, fmt)
                                wcls = (_period_word_class(piece, span[0], span[1])
                                        if span else None)
                                if wcls is None or wcls in found:
                                    clean = False
                                else:
                                    found[wcls] = (qq, cctx)
                        pos += len(piece)
                if clean and set(found) == {'q', 'a'}:
                    emitted = []
                    for wcls, (qq, cctx) in sorted(found.items()):
                        it = emit(by_cls[wcls], qq, cctx)
                        if it is None:
                            emitted = None
                            break
                        emitted.append(it)
                    if emitted:
                        items.extend(emitted)
                        continue
            saw_ambiguous = True
            continue
        if verdict == 'ambiguous':
            saw_ambiguous = True

    sid = source.get('source_id')
    if isinstance(hints, Mapping) and _nb_str(hints.get('source_id')) and _nb_str(sid) \
            and hints.get('source_id') == sid and hints.get('value') is not None:
        try:
            hv = XN.dec(hints.get('value'))
        except XN.ExactError:
            hv = None
        if hv is not None and _finite(hv):
            q, ctx, verdict = _prove(texts, tokens, hv, fmt)
            if verdict == 'ambiguous':
                saw_ambiguous = True
            elif verdict == 'ok':
                q2, ext_words = _extend_label_start(ctx, q, known)
                low_q = q2.lower()
                if all(w in known for w in ext_words) and (not ident_toks or all(
                        re.search(r'(?<![a-z0-9])' + re.escape(tk) + r'(?![a-z0-9])', low_q)
                        for tk in ident_toks)):
                    lbl = _row_label(q2, hv, fmt)
                    if lbl is not None:
                        items.append({'raw_label': lbl, 'value': hv, 'quote': q2,
                                      'period_evidence': ctx})

    grouped = {}                        # same-evidence dedup: R1+R2 on ONE occurrence
    for it in items:                    # collapse to the XBRL-backed item; equal-quote items
        grouped.setdefault(it['quote'], []).append(it)     # with DIFFERENT XBRL identities
    kept = []                           # (the resolved Q/FY pair) are different evidence and
    for k, group in grouped.items():    # both survive
        with_x = {}
        for it in group:
            if 'xbrl' in it:
                xk = (it['xbrl']['period_start'], it['xbrl']['period_end'],
                      it['xbrl']['concept'], tuple(it['xbrl']['axis_members']),
                      it['xbrl']['unit'])
                with_x.setdefault(xk, it)
        kept.extend(with_x.values() if with_x else group[:1])
    items = sorted(kept,
                   key=lambda i: (i.get('xbrl', {}).get('period_start', ''),
                                  i.get('xbrl', {}).get('period_end', ''),
                                  str(i['value']), i['raw_label']))
    if items:
        return {'items': items, 'status': None}
    return {'items': [], 'status': 'ambiguous' if saw_ambiguous else 'no_proven_match'}
