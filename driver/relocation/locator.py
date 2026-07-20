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


# ---------- THE strict value-unknown fact matcher (WP2: PAIR-COMPLETE, neutral home) ----------
import json
import exact_numbers as XN


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
