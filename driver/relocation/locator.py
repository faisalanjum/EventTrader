"""Neutral locator entrypoint (Universal Locator v5.5 §2-§3; WP2).

THREE responsibilities, all pure, no I/O, ZERO fiscal.ai/channel imports. The one
Core import is deliberate: the SEC CIK lexical rule has a single owner in
`driver.core.driver_ids`, and this module consumes it rather than restating it.
1. PRODUCTION anchor rebuild (`rebuild_anchor`) — ids are DECODED here independently; only
   Core composes them. Anchors rebuilt on demand; nothing stored; no registry.
2. THE single strict XBRL dimension parser (`seg_parse`) — relocated verbatim from link_lib;
   both channel files import it from here.
3. The value-unknown entry points (`match_facts` / `match_facts_explain`) — which no longer
   MATCH. They validate the request shape and then abstain: their identity was a prefixed
   concept string and an opaque unitRef, neither of which states identity (#827 Stage 3).
   Signatures kept; `xbrl_lane` still delegates. Route A (`locate`) is the route that can
   answer, because it holds the filing and therefore the namespaces in scope.

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
    out = ''
    while len(n) > 3:
        out = ',' + n[-3:] + out; n = n[:-3]
    return n + out


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


# THE scale table (#827 B6, SEQ 324/327) — the ONE owner of the display-scale
# identity: (word, divisor, short tag). Frozen product contract:
# .claude/plans/Drivers/WIP/UniversalLocator_ReviewRecord_2026-07-18.md —
# "Round 16 (ChatGPT, 2026-07-19)" item 4 (thousand + trillion exact forms under the
# same marker gate) with Round 13 item 3(c) and Round 14 item 2 owning the
# required-multiplier locality rule. Every word map, divisor ladder, tag map and
# regex alternation below derives from this table; link_lib consumes the derived
# names and recreates nothing.
_SCALES = (('thousand', 1e3, 'K'), ('million', 1e6, 'M'),
           ('billion', 1e9, 'B'), ('trillion', 1e12, 'T'))
_WORD2DIV = {w: d for w, d, _ in _SCALES}
_DIVS = tuple(d for _, d, _ in _SCALES)
# _TRAIL derives from ALL supported scale words (SEQ 325): its old missing 'trillion'
# was a REAL evidence-preservation defect — row_quote cropped the word off a lawful
# '1.2 trillion' bind — not a deliberate subset.
_TRAIL = re.compile(r'(?:\s?(?:%|\)|percent\b|'
                    + '|'.join(w + r'\b' for w, _, _ in _SCALES)
                    + r'))*')


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
# DISTINCT grammars, one vocabulary (derived from _SCALES above): a section header
# states 'in' + the PLURAL word (a column-wide declaration); an immediate tail accepts
# singular or plural after the number. Alternation order is match-irrelevant here
# (no scale word prefixes another).
_SCALE_MARK = re.compile(r'(?i)in (' + '|'.join(w + 's' for w, _, _ in _SCALES) + ')')
_SCALE_TAIL = re.compile(r'\s?(' + '|'.join(w for w, _, _ in _SCALES) + r')s?\b', re.I)


def _required_div(form, value):
    """The multiplier this printed form NEEDS to reproduce the value (1e3/1e6/1e9/1e12), or None
    when the form is self-evident (full magnitude, zero, or a non-numeric core)."""
    s = form.lstrip('( ').rstrip(')%').replace(',', '').strip()
    try:
        f = abs(float(s))
    except ValueError:
        return None                        # non-numeric-core forms carry their own words
    av = abs(float(value))
    if av == 0 or f == av:
        return None
    for d in _DIVS:
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


def _tableforms(v, fmt, padded=True):
    """Exact printed forms for table/row scanning. WP1: the value's EXACT form is ALWAYS included
    (zero, small ints, decimals — the old len>=3 filter silently killed them); a fractional value
    gets its 1-decimal companion but NEVER an integer-rounded print; big money keeps the grouped
    cell form + per-supported-scale forms (scaled bare ints only when >=3 digits — a bare
    '7' would match stray sevens). Precision comes from boundary + label adjacency (row_quote),
    never from magnitude or length."""
    av = abs(float(v))
    p = XN.plain(XN.dec(str(v)).copy_abs())
    s = {p}
    if fmt in ('x', 'bps', 'pp'):          # suffix-print classes route through ONE
        return _suffix_forms(v, fmt)       # measured form builder (corrective 5)
    if fmt == '%':
        if '.' in p:
            s.add(f"{av:.1f}")             # 2.34 -> '2.3'; the integer print is the reader's call
            if padded:                     # round 4: padded prints ('0.5' ↔ '0.500%', the CAG
                s |= {f"{av:.2f}", f"{av:.3f}"}   # corpus case) — STRICT verification only;
        elif padded:                       # padded=False = the capped reader-candidate scan,
            s.add(p + '.0')                # where '21.0' pulled an unrelated tax table ahead
                                           # of the true passage (the 3 ACI cases, Phase 4)
        s |= {f[1:] for f in s if f.startswith('0.')}   # round 5 (the VERIFIED Aflac
        return s                                        # pair): leading-zero-omitted
                                                        # prints ('.300 %')
    if '.' not in p:
        s.add(_grp(p))                     # grouped cell form ('5,365,000,000')
    for div in _DIVS:                      # round-16: exact thousand + trillion forms too
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
        y = abs(x) * 10 ** dec
        if not math.isfinite(y):
            continue                       # round 6: a huge-but-finite raw overflows the
        f = math.floor(y) / 10 ** dec      # scaled float — skip the rounded companion,
        forms.add(f"{f:.{dec}f}")          # never crash (reproduced on both routes)
    for f in list(forms):
        if '.' in f:
            forms.add(f.rstrip('0').rstrip('.'))
    return {f for f in forms if f not in ('', '-', '0', '-0')}

def _suffix_forms(value, fmt):
    """The MEASURED print forms of the suffix classes (corrective 5 rounds 1-3, his named
    variants + corpus counts): x → '8x'/'8X'/'8 x' + exact trailing-zero ('2.0x' for a
    stored 2); bps → 'basis points'/'bps'/no-space/'BPS'/hyphenated 'basis-point'
    compounds/singular; pp → 'percentage points'/'pp'/'ppt'/'ppts'/no-space/singular;
    plus the number-only accounting-paren print '(180) BPS' (recognized as NEGATIVE by
    printed_negative). Built from the value itself — never parsed from text."""
    d = XN.dec(str(value)).copy_abs()
    nums = {XN.plain(d), str(d)}           # canonical + lossless-decimal ('2.0') prints
    for p in list(nums):
        if '.' not in p:
            nums |= {p + '.0', p + '.00'}  # exact trailing-zero variants (2 ↔ 2.0x/2.00x)
        elif len(p.split('.')[1]) == 1:
            nums.add(p + '0')              # 2.9 ↔ 2.90X (his corpus form)
    out = set()
    for p in nums:
        if fmt == 'x':
            out |= {p + s for s in ('x', 'X', ' x', ' X', ' times')}
            out |= {'(' + p + ') x', '(' + p + ')x', '(' + p + ') X'}
        elif fmt == 'bps':
            base = {' basis points', ' bps', 'bps', ' BPS', 'BPS', ' BP', 'BP',
                    ' basis point', ' basis-point', '-basis-point'}
            out |= {p + s for s in base}
            out |= {'(' + p + ')' + s for s in (' bps', ' BPS', ' BP', ' basis points',
                                                ' basis point')}
        else:
            base = {' percentage points', ' pp', 'pp', ' ppts', ' ppt', 'ppts',
                    ' percentage point', ' percentage-point'}
            out |= {p + s for s in base}
            out |= {'(' + p + ')' + s for s in (' ppts', ' ppt', ' pp',
                                                ' percentage points')}
    return out


def value_forms(value, fmt='number'):
    """All plausible verbatim string forms of a reported value. No '$' twins are
    generated (#827 B6, SEQ 315/316): sign notation around decorated prints is the
    numeric-core owner's job (printed_negative's decoration law), and bounded_hit
    already matches the bare form beside a '$' — measured: zero results anywhere
    depended on a generated dollar form."""
    if value is None:
        return set()
    if fmt in ('x', 'bps', 'pp'):
        return _suffix_forms(value, fmt)
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
            forms |= {f + '%', f + ' %', f + ' percent', f + ' percentage points',
                      '(' + f + ')%', '(' + f + ')'}
            if f.startswith('0.'):
                forms |= {f[1:] + '%', f[1:] + ' %'}   # round 5 (the VERIFIED Aflac
                                                       # pair): '.300 %' prints
        bps = av * 100
        if math.isfinite(bps) and bps == int(bps):
            forms.add(f"{int(bps)} basis points")   # round 6: int(inf) crashed BOTH
        return forms                                # routes on a huge raw (reproduced)
    ai = int(round(av))
    forms.add(_grp(str(ai))); forms.add(str(ai))
    p = XN.plain(XN.dec(str(value)).copy_abs())
    if '.' in p:
        forms.add(p)                       # the EXACT fractional print (38.3) — WP1; the old code
                                           # only made int-rounded + scaled forms, losing decimals
    for word, div, tag in _SCALES:
        if av >= div / 10:
            scaled = av / div; si = int(round(scaled))
            if si >= 100:                # bare scaled int only when ≥3 digits — "20" for $20.372B would
                forms.add(_grp(str(si))); forms.add(str(si))   # match any stray "20"; "20 billion" kept below

            for f in _round_forms(scaled):
                if '.' in f or len(f) >= 3:   # bare scaled form needs a decimal or ≥3 digits ("20" for
                    forms.add(f)              # $20.372B matches any stray "20"; tagged forms below suffice)
                forms.add(f + tag)
                forms.add(f + ' ' + word)
    if v < 0:
        forms |= {'(' + f + ')' for f in list(forms)}
    return {f for f in forms if f and f not in ('0', '-0')}

def bounded_hit(quote, form, forbid_pct=False):
    """THIN boolean over _form_occurrences (#827 B6, SEQ 322): the exact form occurs at
    a numeric word boundary (not glued inside a bigger number).
    forbid_pct: the occurrence must NOT be %-marked — a plain-number value never accepts a
    percent token ('86' vs '86%', '86 %', '86 percent'; round-12 widened past the bare '%')."""
    for _s, e, _n in _form_occurrences(quote, form):
        if forbid_pct and re.match(r'\s?(%|percent\b)', quote[e:e + 9]):
            continue
        return True
    return False


# _TRAIL/_with_trail + the scale-evidence group (_SCALE_MARK/_SCALE_TAIL/_WORD2DIV/
# _required_div/_tail_div/_local_scale_divs): WP2 Chunk 1 — relocated to
# driver/relocation/locator.py (row_quote's closure); imported below.

def exact_form(form, value, fmt):
    """form reproduces value losslessly (grouped cell, long int, or decimal within 0.1%)."""
    if fmt in ('%', 'x', 'bps', 'pp'):     # suffix-print classes: forms are constructed from
        return True                        # the value itself — lossless by construction
    s = form.lstrip('( ').rstrip(')%').replace(',', '')
    try:
        f = abs(float(s))
    except ValueError:
        return False
    av = abs(float(value))
    if av == 0:
        return f == 0                      # a stated zero reproduces itself (WP1)
    if '.' not in s and s.isdigit() and len(s) >= 4:
        return True
    for sc in (1,) + _DIVS:
        if f > 0 and av > 0 and abs(f*sc - av)/av < 0.001:
            return True
    return False

# printed_negative's two pre-context laws (#827 B6, SEQ 315/316): between the '(' or the
# minus and the digits, only NON-WORD decoration may stand, and never a closing
# delimiter — so '($0.20)' and '-$0.20' read negative while '(-) $24.6' donates nothing.
# The code knows no currency symbol; '$' passes only because it is non-word decoration.
_PRE_PAREN = re.compile(r'\((?:[^\w)\]\}])*$')
_PRE_MINUS = re.compile(r'(?<![\w.])[-−](?:[^\w)\]\}])*$')


def _negative_at(quote, start, end, form):
    """THE sign owner at ONE exact-form occurrence (#827 B6, SEQ 322): negative iff the
    accounting wrap or minus marks the numeric token inside this span — read through
    generic non-word decoration, never across a closer — or the wrap encloses the whole
    form ('(20 million)'). No currency knowledge: '$'/'€' pass only as decoration."""
    tok = re.search(r'[0-9][0-9,.]*', form)
    if tok is None:
        return False
    ts, te = start + tok.start(), start + tok.end()
    pre, post = (quote[:ts]).rstrip(), (quote[te:]).lstrip()
    if (_PRE_PAREN.search(pre) and post.startswith(')')) or _PRE_MINUS.search(pre):
        return True
    pre_f, post_f = (quote[:start]).rstrip(), (quote[end:]).lstrip()
    return bool(_PRE_PAREN.search(pre_f) and post_f.startswith(')'))


def _form_occurrences(quote, form):
    """THE occurrence iterator (#827 B6, SEQ 322): every occurrence of the EXACT
    generated form at a real numeric boundary (at_boundary, the one owner) — yields
    (start, end, negative) with the sign _negative_at reads on that same span.
    Boundary, percent, scale and sign are all judged on the SAME occurrence; callers
    add the percent/scale filters they own. A plain '20' is never an occurrence of
    '(20)%' — forms are matched exactly, which is what stops cross-format laundering."""
    if not form:
        return
    # every generated form is numeric (first char is a digit, '(' or '.') — proven over
    # the full form domain after the dollar twins were deleted (SEQ 323), so at_boundary
    # runs with its strict numeric default: '.3%' never matches inside '1.3%'.
    for m in re.finditer(re.escape(form), quote or ''):
        if not at_boundary(quote, m.start(), m.end()):
            continue
        yield m.start(), m.end(), _negative_at(quote, m.start(), m.end(), form)


def printed_negative(quote, form):
    """Does the quote's notation assert THIS exact printed form is NEGATIVE — '(123)',
    '-123', '($0.20)' — with no plain print of the same form to contradict it? THE SIGN
    BELONGS TO THE OCCURRENCE (#827 B6, SEQ 319/322): a comparison lawfully prints '20'
    beside '(20)', and the plain occurrence keeps a positive value bindable; only a
    quote whose EVERY boundary occurrence of this form is negative asserts negative.
    Forms are matched EXACTLY — '(180) BPS' is itself a generated form, which retired
    the old suffixed-parentheses special case. Notation ONLY: a sign carried by a word
    ("operating loss of 331") is a MEANING call the core owns (OD-12) — code must never
    read words for sign. The closing ')' requirement keeps an ordinary parenthetical
    ("(500 employees)") from being misread."""
    occs = [neg for _s, _e, neg in _form_occurrences(quote, form)]
    return bool(occs) and all(occs)


def value_ok(value, fmt, quote):
    """final deterministic self-check: value present at a real boundary AND losslessly, and the quote's own
    NOTATION does not contradict the value's sign.
    SCOPE (unchanged): this proves the NUMBER is in the quote — never that the KPI/period/slice binding is
    right (that is the binder + audits). The sign guard adds only the mechanical half: a value whose sign
    the quote's notation flatly contradicts is a wrong bind. A plain print asserts nothing about sign, so it
    is left to pass here and be judged where meaning lives — no keyword list, no guessed sign.
    ONE PASS (SEQ 322): every exact-form occurrence is collected once with percent and
    scale judged on its own span; existence and sign are decided from that single set."""
    # '0' is a legal single-char form (a stated zero is a real value — WP1); everything else
    # keeps the >=2 guard against stray single digits.
    forms = {f for f in value_forms(value, fmt or 'number') if len(f) >= 2 or f == '0'}
    suffixed = fmt in ('x', 'bps', 'pp')
    plain = fmt not in ('%', 'x', 'bps', 'pp')
    if plain:
        # scale companions belong to the plain-number lane ONLY (SEQ 326): running them
        # for '%' laundered a scaled plain number ('1.2' for 1.2M) into percent evidence.
        # The ladder is the FULL frozen scale family (SEQ 327): UniversalLocator_Review
        # Record_2026-07-18.md, Round 16 (ChatGPT, 2026-07-19) item 4 adds thousand +
        # trillion under the same marker gate; Rounds 13 item 3(c) / 14 item 2 own the
        # required-multiplier locality rule that gates every companion occurrence.
        for div in _DIVS:
            xx = abs(float(value)) / div
            if xx >= 1:
                for d in (1, 2):
                    forms.add(f"{xx:,.{d}f}")
    quals = []
    for f in forms:
        if not exact_form(f, value, fmt):
            continue
        req = _required_div(f, value) if plain else None
        for _s, e0, neg in _form_occurrences(quote, f):
            if plain:
                if re.match(r'\s?(%|percent\b)', quote[e0:e0 + 9]):
                    continue               # percent-marked: a different fact's print
                td = _tail_div(quote, e0)  # round-14: a scale tag that contradicts the
                if not (td is None or td == req):
                    continue               # claimed value disqualifies THIS occurrence
            quals.append(neg)
    if not quals:
        return False
    if all(quals) and (float(value) > 0 or (float(value) == 0 and suffixed)):
        return False                       # every qualifying print is negative -> wrong
    return True                            # bind (suffix classes keep corrective-5's >=0)


# ---------- The value-unknown entry points — REQUEST VALIDATION, THEN ABSTAIN ----------
# Called "the strict value-unknown fact matcher" until #827 Stage 3. It matched on
# spellings, which is not strictness; the strictness was in the reasons it printed.


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
    """(None, 'insufficient_semantic_identity') — THIS ROUTE CANNOT AUTHORIZE A FACT.

    IT DOES NOT MATCH ANY MORE, AND THAT IS THE POINT. What it used to call
    "the FULL identity" was a prefixed request string compared against a stored
    prefixed string, plus — when no `unitRef` was given — a search for `usd`,
    `dollar` or `share` INSIDE an opaque unit id. Neither states identity:

      * a prefix is an alias (Namespaces in XML 1.0 3e §3), so `us-gaap:Revenues`
        matching `us-gaap:Revenues` only proved that two documents happened to
        choose the same short name. `evil:Revenues` under a rebound prefix was
        indistinguishable from the real concept;
      * a `unitRef` is an XML IDREF the filer picks. `fraud_usd_marker`,
        `dollarNotCurrency` and `shareholder_notes` all satisfied the substring
        rule and returned values. Independently reproduced, all three.

    THE REQUEST SHAPE CANNOT EXPRESS THE ANSWER. It carries a prefixed qname
    and an opaque unit id and no namespace at all, so there is nothing here to
    compare expanded names against — the fix is not a better matcher, it is a
    caller that supplies semantic identities. Until one exists this route says
    so, once, plainly.

    NOT DELETED, by ruling: the public entry points keep their signatures.
    Request-shape validation that is independently meaningful runs FIRST, so a
    malformed ask is still told it is malformed rather than being answered with
    the generic refusal.

    Caller inventory (#827): `run_code_tier` — the one production consumer —
    calls `locate_by_value`, never this. Nothing active reaches here.

    Reasons: bad_request_pairs · bad_request_unit · bad_request_period ·
    insufficient_semantic_identity.
    """
    # REQUEST-SHAPE VALIDATION SURVIVES, and only that: each says the ASK itself
    # is malformed, which is true whatever the route can go on to prove. Nothing
    # here authorizes or repairs. `unit_ref` is optional; present, it must be a
    # nonblank unpadded string. (Withdrawn-helper history: receipt 26 §G.)
    if _valid_pairs(pairs) is None:
        return None, 'bad_request_pairs'          # malformed request address: never guess
    if unit_ref is not None and not _nb(unit_ref):
        return None, 'bad_request_unit'           # malformed request-side unit: never guess
    try:
        XN.period_key(period_start, period_end)
    except XN.ExactError:
        return None, 'bad_request_period'
    # THE REQUEST IS WELL-FORMED AND STILL CANNOT STATE WHAT IT WANTS.
    #
    # Everything past this point used to be the matcher. It is deleted rather
    # than narrowed, because every one of its authorizing steps read a spelling:
    # the concept by prefix, the unit by substring. Neither can be repaired
    # from this request shape — a prefix has no namespace to expand, and an
    # opaque `unitRef` has no declaration attached — so a partially working
    # raw-string matcher is the one outcome worse than none: it answers.
    #
    # `Route A` (`locate`) is the route that CAN answer, because it holds the
    # filing document and therefore the in-scope namespace declarations.
    return None, 'insufficient_semantic_identity'


def match_facts(xbrls, concept_qname, pairs, period_start, period_end, unit_ref=None,
                expected_unit=None):
    """the value-only form of match_facts_explain (production callers)."""
    return match_facts_explain(xbrls, concept_qname, pairs, period_start, period_end,
                               unit_ref=unit_ref, expected_unit=expected_unit)[0]


# ---------- THE neutral locate entrypoint (WP2 Chunk 2: routes R1 + R2, v5.5 §3) ----------
def _wording_tokens(anchor):
    """retrieval-only label tokens from each wording clue's LABEL PORTION (before its first
    digit). Search clues ONLY — wording never authorizes slice or measurement identity."""
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
    """Identity tokens from a slice/measurement scope string. A slice field is
    ';'-joined complete kind:value parts — tokenize the VALUE of EVERY part
    separately, so a later part's kind word (e.g. 'segment') never becomes
    identity evidence (the multi-part anchor fix; single-part and comma-joined
    measurement behavior unchanged)."""
    if not isinstance(field, str) or not field.strip():
        return []
    toks = []
    for part in field.split(';'):
        val = part.split(':', 1)[-1]
        for tk in re.findall(r"[A-Za-z]{3,}", val.replace('_', ' ')):
            tl = tk.lower()
            if tl not in toks:
                toks.append(tl)
    return toks


def _fact_period(fc):
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


_PCT = frozenset({'percent'})
# Phase-3 closeout: the print-form / signal / basis fields served the deleted
# prose laws — the series-unit law is now ONLY the structural accept-set.
_ANCHOR_UNIT = {
    # the money/count rows are THE shared relation (one definition, in
    # exact_numbers); the percent family below is this law's own and is
    # unreachable from Route-A semantics.
    **XN.ROUTE_A_UNIT_COMPAT,
    'percent':            _PCT,
    'percent_yoy':        _PCT,
    'percent_sequential': _PCT,
    'percent_points':     _PCT,
    'basis_points':       _PCT,
    'x':                  _PCT,
}

# THE measured semantic tuple map + the graph-string boolean law. Both now have
# ONE definition, in `exact_numbers`, so the inline-XBRL binder can reach them
# from the package path (this module cannot be imported that way — its bare
# `import exact_numbers` above only resolves with driver/relocation on sys.path).
# Re-exported here unchanged: the pinned census test and the probe scripts
# import them from `locator`.
# `ROUTE_A_SEM_UNIT` IS GONE, here and at its source. It mapped the graph's own
# prefixed text to a semantic reading, which is the rule #827 Stage 3 replaced
# with the filing's expanded measures. The re-export is not kept "in case
# something imports it": a dead export is exactly how a retired rule comes back.
ROUTE_A_BOOLS = XN.ROUTE_A_BOOLS

def _anchor_unit_law(su):
    """The structural unit ACCEPT-SET for a LEGAL series-unit enum value;
    None (incl. 'unknown') → the anchor cannot prove a unit → insufficient_identity."""
    if not isinstance(su, str):
        return None
    return _ANCHOR_UNIT.get(su.strip().casefold())




def _finite(v):
    """THE one finite-number predicate (the WP1 round-13/14 1e309 class) — re-exported via
    link_lib and used by the neutral routes, locate.py, and run_code_tier alike."""
    try:
        return math.isfinite(float(v))
    except (OverflowError, ValueError):
        return False


def locate(anchor, source, hints=None):
    """(anchor, ONE source payload, optional UNTRUSTED hints — currently unused) →
    {'items': [...], 'status': None | 'no_proven_match' | 'ambiguous' |
    'insufficient_identity'}.
    POST-PHASE-3 CONTRACT (FinalPlan §11.3, 2026-07-22): Route A ONLY — when the
    payload carries the display inline HTML, every XBRL fact is proven by its own
    inline element (inline_element_id = graph Fact.fact_id) + element-local
    row/header/section evidence, with the exact-Decimal reconcile, semantic-unit
    tuple map, fail-closed entity law, exclusive(+1 day) period law and the locked
    ambiguity laws. Sources WITHOUT a display document are never text-parsed:
    they return the honest Route E result (no_proven_match). The legacy flat-text
    R1 walk, the R2 hint duplicate and every prose word-list are DELETED; prose
    belongs to the certified reader (Phase 6) or abstention. Routes B/C inactive."""
    if not isinstance(anchor, Mapping) or not isinstance(source, Mapping):
        return {'items': [], 'status': 'insufficient_identity'}
    tokens = _wording_tokens(anchor)
    if not tokens:
        return {'items': [], 'status': 'insufficient_identity'}
    want_ptype = anchor.get('time_type')
    slice_toks = _ident_tokens(anchor.get('slice'))
    meas_toks = _ident_tokens(anchor.get('measurement'))
    accept = _anchor_unit_law(anchor.get('series_unit'))
    if accept is None:
        return {'items': [], 'status': 'insufficient_identity'}
    clue = anchor.get('concept_clue')
    clue_local = clue.rpartition(':')[2] if isinstance(clue, str) and clue.strip() else None
    items, saw_ambiguous = [], False

    inline_doc = source.get('inline_html')
    if inline_doc is not None:
        import inline_html as IHM          # lazy: legacy callers never load bs4
        # THE OWNER DIRECTLY, not through IHM. Reaching it via the parser module
        # left a re-export: two import paths to one rule, so a later move would
        # silently keep working here and hide that this call site was missed.
        from driver.core.driver_ids import graph_cik
        # `ROUTE_A_SEM_UNIT` is no longer bound here: this route now reads the
        # unit from the filing's own expanded measures, so the graph-spelling
        # table has no consumer on the live path. It stays exported for the
        # dormant materializer and its pinned census, which is a different
        # question with a different owner.
        _BOOLS = ROUTE_A_BOOLS

        def _pa_period_ok(doc_period, shape):
            # THE one normalization, and it lives in ONE place: the shared
            # XBRL dateUnion parser (#827 finding 2). Graph end dates are
            # EXCLUSIVE, so the graph date must equal the filing boundary's
            # exclusive end EXACTLY — a date-only boundary adds a day, a
            # dateTime already is the instant and adds none.
            #
            # The private `_plus_one` that stood here is DELETED, not wrapped.
            # It called `date.fromisoformat`, which accepts the COMPACT
            # `20230630` that `xs:date` forbids (proven live: it returned
            # '2023-07-01' where the shared owner refuses). A lawful boundary
            # this graph cannot represent — a timezone, a time of day, an
            # unrepresentable year — yields None and simply fails to match,
            # rather than being repaired or having a zone invented for it.
            ds, de = doc_period
            try:
                end = XN.filing_boundary_graph_end(de)
                start = (None if shape[0] == 'instant'
                         else XN.filing_boundary_graph_start(ds))
            except XN.ExactError:
                return False
            if end is None:                 # lawful but unbindable -> no match
                return False
            if shape[0] == 'instant':
                return ds == '' and end == shape[2]
            # BOTH boundaries go through the shared parser, and the duration
            # must run forwards — the SAME law the binder applies (#827). The
            # start was compared as a RAW STRING here, so the locator rejected
            # a lawful midnight dateTime start that the binder accepted: two
            # answers to one question, which is the defect this whole finding
            # is about.
            if start is None:
                return False
            # THE FORWARD-ORDER CALL THAT STOOD HERE IS DELETED. It could never
            # change an answer: `_fact_period` builds every duration shape
            # through `period_key`, which RAISES on a backwards window, and
            # returns None when `ps == pe` — so `shape[1] < shape[2]` strictly,
            # and the equality below already implies the filing runs forwards.
            # Measured before removing it: 23 calls across the Route-A suite,
            # ZERO rejections; removing it changed no result. Kept as
            # "defence-in-depth" it was exactly the hypothetical-edge-case
            # machinery the minimalism rule forbids.
            return start == shape[1] and end == shape[2]

        prepared = IHM.prepare(inline_doc)   # ONE parse per filing, reused
        # THE RAW VALUE, unrepaired. `str(... or '')` minted a ten-digit
        # spelling the source never stated — the integer 1234567890 became the
        # string "1234567890" and BOUND, while the owner it was handed to says
        # a non-string refuses. The coercion made the gate a formality.
        want_cik = graph_cik(source.get('company_cik'))
        route_a_claims = {}
        # ONE TARGET PER STORED CONCEPT KEY, DERIVED BEFORE ANY FACT IS READ.
        # The envelope groups facts under a stored concept key; if that key maps
        # to two different expanded names, the envelope cannot say which
        # semantic concept it represents, and picking per row would let ORDER
        # decide meaning — the good row binding while the conflicting one is
        # quietly skipped. So every Concept identity recorded under a key is
        # collapsed first: identical records agree, and any missing, unusable or
        # disagreeing record leaves that key with NO target and abstains.
        # Measured: today's graph carries exactly one Concept edge per numeric
        # non-nil fact, so this fail-closed check costs no lawful current data.
        _rows = list(_fact_rows(source.get('xbrls') or ()))
        _by_concept = {}
        for _c, _fc in _rows:
            _by_concept.setdefault(_c, []).append(
                (_fc.get('concept_namespace'), _fc.get('graph_concept_qname')))
        _targets = {_c: IHM.one_concept_target(_c, _recs)
                    for _c, _recs in _by_concept.items()}
        for c, fc in _rows:
            if clue_local is not None and c.rpartition(':')[2] != clue_local:
                continue
            shape = _fact_period(fc)
            if shape is None or shape[0] != want_ptype:
                continue
            raw_unit = fc.get('unitRef')
            if not isinstance(raw_unit, str) or not raw_unit.strip():
                continue
            unit_name = fc.get('unit_name')
            is_divide = _BOOLS.get(fc.get('is_divide'))
            if not isinstance(unit_name, str) or is_divide is None:
                continue                     # declared-unit handoff: FAIL-CLOSED
            # THE FILING'S OWN DECLARATION DECIDES THE UNIT — not the graph's
            # spelling of it. This gate read `(Unit.name, is_divide)`, which is
            # prefixed text, so it made both mistakes a prefix always makes:
            # `cur:USD` bound to the official ISO-4217 URI was REFUSED, and
            # `iso4217:USD` under a filing that rebound `iso4217` to another URI
            # was ACCEPTED as money. The document is already parsed here, so the
            # expanded measures are in hand and no second resolver is needed.
            #
            # `unit_name`/`is_divide` stay above as the STORAGE-INTEGRITY check
            # they were: the graph and the filing must still agree that a unit
            # was declared at all. What they may no longer do is decide what it
            # MEANS.
            declared_unit = (prepared.get('units') or {}).get(raw_unit)
            if not isinstance(declared_unit, dict):
                continue                     # the filing declares no such unit
            # TWO INDEPENDENT STATEMENTS ABOUT ONE UNIT MUST AGREE — on its
            # STRUCTURE and on its STORED SPELLING. This is storage integrity,
            # NOT meaning, and the distinction is the whole point:
            #
            #   MEANING  comes from the filing's expanded measures (below), so
            #            `cur:USD` bound to the official ISO-4217 URI is dollars
            #            and `iso4217:USD` rebound to `urn:evil` is not;
            #   INTEGRITY is whether the graph is describing the SAME unit at
            #            all, and that is an exact comparison against the
            #            spelling the writer records — `XBRL/xbrl_basic_nodes`
            #            stores `unit.stringValue`, and `graph_unit_spelling`
            #            derives that same serialization from the filing BY
            #            NAMESPACE. No prefix is interpreted and the
            #            concatenated divide name is never split.
            #
            # I first dropped this check and asserted the mismatch was lawful.
            # It is not: without it a graph row labelled `unknownunit`, or one
            # claiming a per-share unit, bound against a filing declaring plain
            # dollars. Both halves are needed — spelling alone would refuse the
            # lawful alias, expansion alone lets an unrelated row through.
            if bool(declared_unit.get('is_divide')) != is_divide:
                continue
            spelled = (''.join(declared_unit.get('graph_numerator') or ())
                       + ''.join(declared_unit.get('graph_denominator') or ())
                       if is_divide else
                       XN.graph_unit_spelling(
                           declared_unit.get('graph_measures') or (),
                           (), (), False))
            if spelled != unit_name:
                continue
            sem_unit = XN.route_a_semantic_unit(declared_unit)
            if sem_unit not in accept:
                continue                     # semantic reading vs anchor accept-set;
                                             # everything unreadable abstains
            gctx = fc.get('context_id')
            # THE LEGACY `segment` BRANCH IS GONE (#827). It read raw prefixed
            # qnames — `srt:...`, `ce:...` — off the graph record and compared
            # them to this filing's dimensions. A bare prefix carries NO
            # namespace, so that comparison could only ever test whether two
            # documents happened to choose the same alias; it could not state
            # identity, and nothing may authorise a match on it.
            #
            # Censused before removal: the real producer
            # `scripts/driver_seed/route_a_source.py` returns the exact
            # `context_id` and never a `segment` (0 occurrences in the file),
            # and no other non-test caller of this lane supplies one. It was a
            # test-only law. The `context_id` path below is strictly stronger —
            # joining on the fact's OWN context makes the filing's own
            # dimensions authoritative by construction, with no prefix read at
            # all.
            if isinstance(gctx, str) and gctx.strip():
                pairs = None                 # graph stores no axis pairing; the
                                             # fact's OWN context_id must equal the
                                             # element's contextRef (checked below),
                                             # making the doc dims authoritative
            else:
                pairs = []                   # neither given: undimensioned claim —
                                             # a dimensioned element still mismatches
            graph_v = IHM.parse_raw(fc.get('value'))   # XSD decimal (Arelle decimalPattern) + grouped round-trip
            if graph_v is None or not _finite(graph_v):
                continue
            spairs_a = (tuple(sorted(tuple(p) for p in pairs))
                        if pairs is not None else None)
            fid_raw = fc.get('fact_id')
            if fid_raw is not None and not isinstance(fid_raw, str):
                continue                     # non-string id: REJECT, no fallback
            if isinstance(fid_raw, str) and fid_raw != fid_raw.strip():
                continue                     # padded id: REJECT, no fallback
            fid = (fid_raw or '').strip()
            # THE CONCEPT'S EXPANDED IDENTITY, agreed across every record under
            # this key and computed once above. A concept is a QName, so the
            # prefix in the graph's stored name is an alias: authorising a match
            # on that string both missed a filing that lawfully binds a second
            # prefix to the same taxonomy and could not separate two taxonomies
            # sharing a local name.
            target = _targets.get(c)
            if target is None:
                continue
            if fid and fid != 'null':
                ev, _why = IHM.element_evidence(prepared, fid)
            else:                            # missing/blank inline_element_id:
                ev = None                    # COMPLETE-identity fallback (both
                if isinstance(gctx, str) and gctx.strip():   # id'd and id-less
                    el2, w2 = IHM.identity_fallback(prepared, target,
                                                    gctx.strip(), raw_unit)
                    if w2 == 'ok':
                        e2, w3 = IHM.evidence_for_element(prepared, el2)
                        if w3 == 'ok' and not e2['hidden'] \
                                and _pa_period_ok(e2['period'], shape):
                            ev = e2
                            # THE ID IS AN XML ATTRIBUTE, so it is read off the
                            # SEMANTIC half of the bridged fact — the renderer
                            # half spells attribute names its own way and has no
                            # authority over identity.
                            fid = IHM.element_id(el2) \
                                or f'__noid__:{c}:{gctx.strip()}'
                if ev is None:
                    cands = []               # fixture path: no context pointer —
                    for eid in IHM.find_by_identity(prepared, target,
                                                    raw_unit):
                        e2, w2 = IHM.element_evidence(prepared, eid)
                        if w2 == 'ok' and not e2['hidden'] \
                                and _pa_period_ok(e2['period'], shape) \
                                and (spairs_a is None or e2['dims'] == spairs_a):
                            cands.append((eid, e2))
                    fid, ev = cands[0] if len(cands) == 1 else ('', None)
            # AUTHORISED BY IDENTITY, not by the stored prefix. The raw name
            # is kept on the evidence as display/storage detail only.
            if ev is None or ev['hidden'] or ev['name_expanded'] != target \
                    or ev['unit_ref'] != raw_unit:
                continue
            if not want_cik or not ev.get('entity') \
                    or ev['entity'] != want_cik:
                continue                     # entity law, FAIL-CLOSED: expected CIK
                                             # AND the element's entity must exist
                                             # and match EXACTLY
            if not _pa_period_ok(ev['period'], shape):
                continue
            if isinstance(gctx, str) and gctx.strip() \
                    and ev['context_ref'] != gctx.strip():
                continue                     # the graph fact's own context pointer
            if spairs_a is None:
                spairs_a = ev['dims']        # same context -> dims BY CONSTRUCTION
            elif ev['dims'] != spairs_a:
                continue
            if not slice_toks and spairs_a:
                continue                     # undimensioned anchor, dimensioned fact
            # THE FACT'S OWN CONTENT, exactly as the binder does. `displayed`
            # is the rendered page and stays below, where it is only quoted.
            # THE FORMAT'S EXPANDED IDENTITY, exactly as the binder uses it. A
            # prefix is the filer's alias: read raw, an official registry under
            # another prefix was refused and an imitation under `ixt` was
            # accepted. `ev['fmt']` stays the published spelling below.
            if IHM.transform_status(ev.get('fmt_expanded')) is not None:
                continue
            if not IHM.reconcile(ev['value_input'], ev.get('fmt_expanded'),
                                 ev['scale'], ev['sign'], fc.get('value')):
                continue
            pv = IHM.printed_value(ev['value_input'], ev.get('fmt_expanded'),
                                   ev['sign'])
            if pv is None:
                continue
            surface = ' '.join([*ev['row_cells'], *ev['columns'], ev['section'],
                                ev['block']]).lower()
            toks_a = list(tokens) + list(slice_toks) + list(meas_toks)
            if not all(re.search(r'(?<![a-z0-9])' + re.escape(tk)
                                 + r'(?![a-z0-9])', surface) for tk in toks_a):
                continue                     # identity ONLY from element-local
                                             # row/header-stack/section/block
            quote = ev['row_text'] if ev['in_table'] else ev['block']
            span = ev['row_span'] if ev['in_table'] else ev['block_span']
            if not quote or span is None \
                    or prepared['text'][span[0]:span[1]] != quote:
                continue                     # ELEMENT-SPECIFIC offsets: this row's
                                             # own recorded span must reproduce the
                                             # quote exactly (identical twin rows
                                             # get their OWN spans, never find())
            # The offsets and the label span are no longer computed here at all:
            # `IH.source_evidence` below derives every one of them from the same
            # element evidence, so the locator and Core cannot drift apart.
            # THE SEMANTIC IDENTITY, never the spellings. `c` and `spairs_a`
            # are the filing's own prefixed text: keying on them made two
            # lawful aliases for ONE namespace look like two different facts,
            # and left two DIFFERENT taxonomies sharing a local name looking
            # like one. `target` is the concept's expanded name and
            # `dims_expanded` the dimensions'; both were already computed
            # above, so this states identity with what the parse already knows
            # rather than inventing a second scheme.
            #
            # It travels on a PRIVATE key, popped before the boundary exactly
            # as `_element_id` is — the published shape is unchanged, and the
            # raw spellings still go out as the product's own wording.
            #
            # STAGE 3, now done: the unit joins the identity as the FILING's
            # expanded measure structure. `unitRef` is an id chosen by the
            # filer, so one filing may lawfully declare `usd` and `usd2` for the
            # SAME unit; keying on the id made one semantic series look like two
            # and reported a false `ambiguous`. Two ids that expand to one unit
            # are one unit here, and two ids that expand differently stay apart.
            unit_identity = (bool(declared_unit.get('is_divide')),
                             tuple(declared_unit.get('expanded_measures') or ()),
                             tuple(declared_unit.get('expanded_numerator') or ()),
                             tuple(declared_unit.get('expanded_denominator') or ()))
            identity = (target, ev['dims_expanded'])
            fact_key = (identity, shape, unit_identity, graph_v)
            seen_keys = route_a_claims.setdefault(fid, set())
            if fact_key in seen_keys:
                continue                     # identical XBRL identity: DEDUPLICATE
            seen_keys.add(fact_key)
            items.append({
                '_element_id': fid,
                '_identity': identity,
                '_unit_identity': unit_identity,
                'raw_label': ev['row_label'] or ev['section']
                             or (ev['columns'][0] if ev['columns'] else '')
                             or quote[:80],
                'value': pv, 'quote': quote,   # the SIGNED UNSCALED printed value
                'period_evidence': quote,      # STRING at the frozen boundary — an
                                               # EXACT slice (downstream parsers,
                                               # e.g. wp1_verify substring checks,
                                               # assume a string; the structured
                                               # disjoint slices stay INTERNAL
                                               # below pending ONE owner decision)
                'ix_evidence': {'scale': ev['scale'], 'sign': ev['sign'],
                                'format': ev['fmt'], 'unit_ref': raw_unit},
                'xbrl': {'concept': c, 'axis_members': list(spairs_a),
                         'period_start': ev['period'][0] or ev['period'][1],
                         'period_end': ev['period'][1],   # the HTML context's
                         'ptype': shape[0], 'unit': raw_unit,   # exact dates
                         'ix': {'scale': ev['scale'], 'sign': ev['sign'],
                                'format': ev['fmt'],
                                'unit_ref': raw_unit},    # ChannelContract line 36
                         # OWNER RULING (corrective-7). Built by the SHARED owner
                         # in inline_html so Core checks a submitted claim
                         # against the same construction that produced it — the
                         # locator's own copy of this is deleted.
                         'source_evidence': IHM.source_evidence(prepared, ev)},
            })
        # LOCKED AMBIGUITY LAWS: (a) one printed element claimed by DIFFERENT fact
        # identities → ambiguous; (b) one ANCHOR resolving to DIFFERENT surviving
        # series identities (concept + pairs + unit) → ambiguous — multiple PERIODS
        # of the SAME complete identity remain valid enumeration.
        clash = {eid for eid, keys in route_a_claims.items() if len(keys) > 1}
        if clash:
            items[:] = [it for it in items if it.get('_element_id') not in clash]
            saw_ambiguous = True
        # ONE SERIES IS ONE MEANING, so this counts expanded identities. Read
        # off the published spellings it split a single series in two whenever
        # a filing used two lawful prefixes for one namespace, and merged two
        # taxonomies that happen to share a local name.
        # ...and the UNIT is the filing's expanded structure for the same
        # reason: `unitRef` is an id the filer picks, so one filing declaring
        # `usd` and `usd2` for the SAME unit split one series into two and
        # reported a false `ambiguous`.
        series_ids = {(it['_identity'], it['_unit_identity'])
                      for it in items if it.get('_element_id') is not None}
        if len(series_ids) > 1:
            items[:] = [it for it in items if it.get('_element_id') is None]
            saw_ambiguous = True
        for it in items:
            it.pop('_element_id', None)

    # ─── Phase 3 (FinalPlan §11.3, 2026-07-22): the legacy flat-text R1 walk and
    # the R2 hint duplicate — the semantic prose machinery — are DELETED. Sources
    # without a display inline document produce no items here and fall through to
    # the honest Route E return below (no_proven_match). Routes B/C are inactive;
    # prose belongs to the certified reader (Phase 6) or abstention.
    grouped = {}
    for it in items:
        grouped.setdefault(it['quote'], []).append(it)
    kept = []
    for k, group in grouped.items():
        with_x = {}
        for it in group:
            if 'xbrl' in it:
                # SAME RULE AT THE LAST GROUPING. This is the third place the
                # filing's own spellings stood in for meaning; leaving it would
                # have kept one alias-split alive after the two above were
                # fixed. Items from routes that carry no identity keep their
                # own published fields — there is nothing to expand there.
                xk = (it['xbrl']['period_start'], it['xbrl']['period_end'],
                      it.get('_identity'), it.get('_unit_identity'))
                with_x.setdefault(xk, it)
        kept.extend(with_x.values() if with_x else group[:1])
    # THE INTERNAL IDENTITY NEVER CROSSES THE BOUNDARY. It exists to decide
    # sameness and stops here — the published item keeps only the filing's own
    # spellings, so the frozen contract is untouched (its field allowlist would
    # refuse an extra key outright, which is the check that proves this ran).
    for it in kept:
        it.pop('_identity', None)
        it.pop('_unit_identity', None)
    items = sorted(kept,
                   key=lambda i: (i.get('xbrl', {}).get('period_start', ''),
                                  i.get('xbrl', {}).get('period_end', ''),
                                  str(i['value']), i['raw_label']))
    if items:
        return {'items': items, 'status': None}
    return {'items': [], 'status': 'ambiguous' if saw_ambiguous else 'no_proven_match'}
