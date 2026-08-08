"""The ONE shared fiscal period resolver (FINAL_DESIGN §6.2, PER-01..20; GuidancePeriod.md).

Wraps the PROVEN guidance period machinery BY REFERENCE (never copied):
  - pure math: guidance_ids.build_guidance_period_id -> fiscal_math (its 99.1% = date ->
    fiscal-QUARTER classification, 544/549 vs SEC focus tags — NOT exact-window accuracy;
    exact calendar windows come only from the date/SEC branches above the math fallback)
  - cascade:   existing-graph window -> SEC exact dates -> predicted quarter -> pure math
New-law deltas over the old substrate (each anchored): exact-date branch first + ytd/ttm
windows (GuidancePeriod.md) · calendar_override routed BEFORE any company lookup (BUILD §10
hazard) · time_type required, label hint never overrides (FACT-18) · no quiet gp_UNDEF, no
year-2000 months (FINAL §6.2 / BUILD §10) · 'long_range' scope retired -> exact_range (95 #23).

Resolution fails CLOSED: any ambiguity raises PeriodResolutionError -> the caller PARKS.
"""
import sys
from datetime import MAXYEAR, MINYEAR, date, timedelta
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / ".claude/skills/earnings-orchestrator/scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fiscal_math import _compute_fiscal_dates                      # the ONE calendar canon
from guidance_ids import build_guidance_period_id   # proven pure builder (the ONLY
# guidance_ids name Core consumes — the sentinel pairs live in driver_ids)

from driver.core.driver_ids import (IdLawError, PERIOD_SENTINEL_SCOPE,
                                    build_period_id, parse_period_id)
from driver.core.outcome_codes import require_known   # T1: mint-time consumption

# derived view of the ONE four-pair owner (driver_ids.PERIOD_SENTINEL_SCOPE):
# sentinel_class -> period id, inverted once here because this door receives the
# WORD spelling from callers (two uses below — membership and lookup).
_SENTINEL_ID_BY_CLASS = {word: pid for pid, word in PERIOD_SENTINEL_SCOPE.items()}
# THE ONE packet-derived period-item vocabulary (15_CandidateFactPacket.md :31,
# sha aa7239ed — the 11 names, ORDER-EXACT). Both door builders derive their
# extraction from this owner; the presence view below derives from it too.
# time_type IS a member: an item carrying only a time_type judgment is NOT
# periodless — it parks through the undefined-fields refusal, never None.
PERIOD_ITEM_KEYS = ("period_start_date", "period_end_date", "fiscal_year",
                    "fiscal_quarter", "half", "month", "long_range_start_year",
                    "long_range_end_year", "sentinel_class", "time_type",
                    "period_scope")


class PeriodResolutionError(ValueError):
    """The period is ambiguous or under-specified. Callers PARK — never guess."""


#: THE one scope-enum spelling set (P-O2: the resolver-vs-validators duplicate
#: spellings are folded HERE; validators consume the invariant, never a copy).
_DATED_SCOPES = frozenset({"quarter", "annual", "half", "monthly", "ytd",
                           "ttm", "exact_range"})
PERIOD_SCOPES = _DATED_SCOPES | frozenset(PERIOD_SENTINEL_SCOPE.values())


def period_invariant(u_id, scope, time_type, start, end):
    """THE complete period invariant at ONE owner (P-O2, U-7). Returns a tuple
    of (code, message) verdicts — empty means lawful. Codes come from the T1
    vocabulary; both consumers map them (the resolver raises the first as a
    typed park; the validators append each as a REJECT).

    Owns, in one place: id/scope presence symmetry · the scope + time_type
    enums · id parse / sentinel pairing (F-IDLAW, via parse_period_id) ·
    canonical ISO validation · stored-date-to-id equality · the
    instant/duration window law. The preserved typed-outcome map holds:
    malformed stored date WITH a valid dated id -> ISO · malformed id ->
    PERIOD_SYM · sentinel/date conflict -> SCOPE_PAIR. The compact-date
    ordering is the T1 owner's COMPACT_DATE_IN_ID_ORDER: the id grammar
    judges an id-carried compact date (PERIOD_SYM), never the ISO rule."""
    out = []
    if (u_id is None) != (scope is None):
        out.append((require_known("PERIOD_SYM"), "period_u_id and period_scope must travel together"))
    if u_id is None:
        if start is not None or end is not None:
            out.append((require_known("PERIOD_SYM"), "period dates without a period_u_id"))
        return tuple(out)
    if scope is not None and scope not in PERIOD_SCOPES:
        out.append((require_known("SCOPE_PAIR"), f"period_scope {scope!r} not in the enum"))
    if time_type not in ("duration", "instant"):
        out.append((require_known("INSTANT"),
                    f"time_type required (duration|instant) with a period, got {time_type!r}"))
    try:
        pid_start, pid_end = parse_period_id(u_id)
    except IdLawError as e:
        out.append((require_known("PERIOD_SYM"), str(e)))
        return tuple(out)
    if pid_start is None:                      # a valid sentinel id
        if scope != PERIOD_SENTINEL_SCOPE.get(u_id):
            out.append((require_known("SCOPE_PAIR"),
                        f"sentinel {u_id} must pair with scope "
                        f"{PERIOD_SENTINEL_SCOPE.get(u_id)!r}"))
        if start is not None or end is not None:
            out.append((require_known("SCOPE_PAIR"), f"sentinel {u_id} stores null dates"))
        return tuple(out)
    if scope in PERIOD_SENTINEL_SCOPE.values():
        out.append((require_known("SCOPE_PAIR"), f"dated period {u_id} with sentinel scope {scope!r}"))
    for d in (start, end):
        if d is not None:
            try:
                date.fromisoformat(d)
            except (ValueError, TypeError):
                out.append((require_known("ISO"), f"bad ISO date {d!r}"))
                return tuple(out)
    # a dated period's stored dates ARE the gp_ id's dates — no divergence and
    # no absence, ever (PERIOD_SYM per the frozen 827B2 evidence: a compact
    # "20251231" parses under 3.11 but is not the canonical id spelling, and
    # the ID text is the canon — equality names it, the ISO rule does not).
    if (start, end) != (pid_start, pid_end):
        out.append((require_known("PERIOD_SYM"),
                    f"gp dates {start}..{end} do not match the period id {u_id}"))
        return tuple(out)
    if time_type == "instant" and pid_start != pid_end:
        out.append((require_known("INSTANT"), "instant must be a one-day window (gp_X_X)"))
    elif time_type == "duration" and pid_start == pid_end:
        out.append((require_known("INSTANT"), "duration with start == end is illegal input"))
    return tuple(out)


def _lawful_fye(v):
    """THE one fye_month gate (GuidancePeriod:357 law: int|None, 1..12).
    None passes — it parks later only where a computation actually needs it.
    Everything else must be a true int in 1..12: bool/str/float/out-of-range
    PARK here, typed, instead of escaping as a raw TypeError/IllegalMonthError
    deep in the calendar math. Validates the SUPPLIED boundary value and BOTH
    corrected-cache answers (§4: never silently discard, never silently trust)."""
    if v is not None and not (type(v) is int and 1 <= v <= 12):
        raise PeriodResolutionError(f"fye_month out of range: {v!r} — park")
    return v


def ensure_driver_period(item, *, fact_type, fye_month, ticker=None,
                         calendar_override=False, lookups=None):
    """Resolve one item's period. Returns {period_u_id, period_scope, time_type,
    gp_start_date, gp_end_date} or None when the fact truly has no period fields."""
    fye_month = _lawful_fye(fye_month)   # FIRST statement — before every bypass
    # P-O12 (M-2): the calendar flag is KEYWORD-ONLY (the frozen packet holds
    # calendar_override in the Block-0 envelope alone — the item route was a
    # superseded duplicate) and must be a true bool BEFORE every early return:
    # bool() coerced "false" and 1 to True, turning December-annual on under a
    # September FYE from either route.
    if type(calendar_override) is not bool:
        raise PeriodResolutionError(
            f"calendar_override must be a bool, got "
            f"{type(calendar_override).__name__} — park")
    if item.get("period_u_id") is not None:   # P-O2: a PRESENT id — falsey
        return _preserved(item)               # included — is JUDGED, never ignored
    if all(item.get(k) is None for k in PERIOD_ITEM_KEYS):  # is-not-None: zero VALUES (e.g.
        return None                                     # fiscal_quarter=0) get VALIDATED

    cal = calendar_override              # P-O12: keyword route ONLY, no coercion
    time_type = item.get("time_type")
    if time_type not in ("duration", "instant"):
        raise PeriodResolutionError(
            f"time_type is a required semantic judgment (got {time_type!r}) — park")
    _check_declared_fields(item)
    scope_in = item.get("period_scope")
    if scope_in not in (None, "ytd", "ttm"):
        raise PeriodResolutionError(f"input period_scope may only be ytd/ttm, got {scope_in!r}")

    # 1. exact source/XBRL dates ALWAYS win over computed math (test 20; 52/53-week safety)
    if item.get("period_start_date") or item.get("period_end_date"):
        return _exact_dates(item, time_type, scope_in)

    # 2. explicit sentinel
    sentinel = item.get("sentinel_class")
    if sentinel is not None:
        if sentinel not in _SENTINEL_ID_BY_CLASS:
            raise PeriodResolutionError(f"unknown sentinel_class: {sentinel!r}")
        return _result(_SENTINEL_ID_BY_CLASS[sentinel], sentinel, time_type, None, None)

    fye = 12 if cal else fye_month
    # every lookup call below sits behind a `ticker` guard, so the pure-math lane
    # (ticker=None / calendar mode) never triggers the heavy substrate import
    lk = lookups if lookups is not None else (_default_lookups() if ticker else None)

    # 3. ytd/ttm cumulative windows (fiscal math; exact dates already handled above)
    if scope_in in ("ytd", "ttm"):
        return _cumulative(item, scope_in, time_type, fye, cal, ticker, lk)

    # 4. proven cascade A/B/C — standard duration quarter/annual, company-fiscal only
    fy = item.get("fiscal_year")
    fq = item.get("fiscal_quarter")
    is_standard = (time_type == "duration" and not item.get("half") and not item.get("month")
                   and not item.get("long_range_end_year"))
    if is_standard and not cal and ticker and fy:
        # P-O3 (U-6): clean miss is `result is None` EXACTLY — a falsey
        # non-None result ({} included) is an affirmative answer and must be
        # lawful or PARK; nothing falls through on truthiness.
        want_scope = "quarter" if fq else "annual"
        found = lk["existing"](ticker, fy, fq)
        if found is not None:
            found = _lawful_hit("existing", found, want_scope, time_type)
            return _result(found["period_u_id"],
                           found.get("period_scope") or want_scope,
                           found.get("time_type") or "duration",
                           found.get("start_date"), found.get("end_date"))
        sec = lk["sec"](ticker, fy, f"Q{fq}" if fq else "FY")
        if sec is not None:
            sec = _lawful_hit("sec", sec, want_scope, time_type)
            return _result(build_period_id(sec["start"], sec["end"]),
                           want_scope, "duration",
                           sec["start"], sec["end"])
        if fq:
            pred = lk["predict"](ticker, fy, fq)
            if pred is not None:
                pred = _lawful_hit("predict", pred, "quarter", time_type)
                return _result(build_period_id(pred["start"], pred["end"]),
                               "quarter", "duration",
                               pred["start"], pred["end"])

    # 5. pure fiscal math (step D) with the new-law fail-closed guards
    if not cal and ticker:
        corrected = lk["corrected_fye"](ticker)
        if corrected is not None:
            fye = _lawful_fye(corrected)   # the cache's answer is validated too
    if fye is None:
        raise PeriodResolutionError(
            "fye_month required to compute a company fiscal period — never default December")
    if item.get("month") and not item.get("fiscal_year"):
        raise PeriodResolutionError("month without fiscal_year — the year-2000 mint is forbidden")

    built = build_guidance_period_id(
        fye_month=fye,
        fiscal_year=item.get("fiscal_year"),
        fiscal_quarter=item.get("fiscal_quarter"),
        half=item.get("half"),
        month=item.get("month"),
        long_range_start_year=item.get("long_range_start_year"),
        long_range_end_year=item.get("long_range_end_year"),
        calendar_override=cal,
        sentinel_class=None,          # handled above
        time_type=time_type,
        label_slug=None,              # hint only — never allowed to override time_type
    )
    if built["u_id"] == _SENTINEL_ID_BY_CLASS["undefined"]:   # the old quiet
        # fallthrough — forbidden now; the id spelling comes from the one owner
        raise PeriodResolutionError(f"period fields do not resolve: { {k: item.get(k) for k in PERIOD_ITEM_KEYS} }")
    scope = "exact_range" if built["period_scope"] == "long_range" else built["period_scope"]
    return _result(built["u_id"], scope, built["time_type"],
                   built["start_date"], built["end_date"])


def _exact_dates(item, time_type, scope_in):
    start, end = item.get("period_start_date"), item.get("period_end_date")
    if not end:
        raise PeriodResolutionError("exact-date input needs period_end_date")
    if time_type == "instant":
        if start and start != end:
            raise PeriodResolutionError(f"instant with two different dates: {start}..{end}")
        start = end
    elif not start:
        raise PeriodResolutionError("duration exact-date input needs period_start_date")
    elif start == end:
        raise PeriodResolutionError(f"duration with start == end is illegal input: {start}")
    if scope_in in ("ytd", "ttm") and time_type == "instant":
        raise PeriodResolutionError(f"{scope_in} is a cumulative window — cannot be instant")
    try:                          # real calendar dates only — a bad date PARKS, never crashes
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    except ValueError as e:
        raise PeriodResolutionError(f"invalid ISO date ({start!r}..{end!r}): {e} — park")
    scope = scope_in or _declared_scope(item)
    # INTERIM GUARD — NOT P14 (owner 2026-07-17). The ratified date-anchored classifier
    # (BUILD §8.2 P14) is DORMANT until the XBRL materializer enables; it will replace
    # ONLY these temporary labels/bands — the basic input validation above is permanent.
    # A declared label whose window length contradicts it PARKS (never guess). Bands are
    # sized so the KNOWN TESTED calendars pass: 52/53-week years (364/371d), 4-4-5 retail
    # months, irregular-quarter filers (KR 16-wk Q1 = 112d; COST 84d, 53-wk Q4 = 119d).
    if time_type == "duration":
        band = _INTERIM_SCOPE_DAYS.get(scope)
        if band and not band[0] <= days <= band[1]:
            raise PeriodResolutionError(
                f"{scope} declared but the window is {days} days ({start}..{end}) — "
                f"contradictory framing, park")
    return _result(build_period_id(start, end), scope, time_type, start, end)


_INTERIM_SCOPE_DAYS = {          # sized so the KNOWN TESTED calendars pass
    "monthly": (25, 35),         # 4-week retail month .. 5-week month
    "quarter": (75, 120),        # 11-week .. 17-week (KR 112d; COST 84d/119d)
    "half": (160, 210),          # 24-week .. 29-week (12-wk + 17-wk 53-yr half)
    "ytd": (1, 390),             # NO minimum — January-to-date is real; cap = 53-wk year
    "annual": (340, 390),        # 52-week (364d) .. 53-week (371d) with margin
    "ttm": (350, 380),
}                                # exact_range: unbounded by definition — no band


def _check_declared_fields(item):
    """The ONE strict period-shape check, on EVERY path. This is PERMANENT basic input
    validation — P14 later replaces only the temporary labels/bands, never this.
    Conflicting, mixed, incomplete, or out-of-range framing PARKS; never guess."""
    shapes = [k for k in ("fiscal_quarter", "half", "month", "long_range_end_year")
              if item.get(k) is not None]
    if len(shapes) > 1:
        raise PeriodResolutionError(f"conflicting period fields: {shapes} — park")
    # T4 (#827): the year bounds are DERIVED from the period owner's own
    # machinery — datetime.MINYEAR..MAXYEAR is exactly what the calendar canon
    # can compute — never a chosen product endpoint (the 1900..2200 literals
    # were unauthorized; P-D5's derive-from-standard tie stays open).
    for name, lo, hi in (("fiscal_quarter", 1, 4), ("half", 1, 2), ("month", 1, 12),
                         ("fiscal_year", MINYEAR, MAXYEAR),
                         ("long_range_start_year", MINYEAR, MAXYEAR),
                         ("long_range_end_year", MINYEAR, MAXYEAR)):
        v = item.get(name)
        if v is not None and not (type(v) is int and lo <= v <= hi):
            raise PeriodResolutionError(f"{name} out of range: {v!r} — park")
    lr_s, lr_e = item.get("long_range_start_year"), item.get("long_range_end_year")
    if lr_s is not None and lr_e is None:      # end-only IS legal ("by 2030" targets —
        raise PeriodResolutionError(           # proven substrate shape); start-only isn't
            "long-range start year without an end year — park")
    if lr_s is not None and lr_s > lr_e:
        raise PeriodResolutionError(f"long-range years reversed: {lr_s}..{lr_e} — park")
    if item.get("period_scope") in ("ytd", "ttm") and any(
            item.get(k) is not None for k in ("half", "month", "long_range_end_year")):
        raise PeriodResolutionError(
            f"{item['period_scope']} conflicts with half/month/long-range fields — park")
    if item.get("sentinel_class") is not None and any(
            item.get(k) is not None for k in
            ("period_start_date", "period_end_date", "fiscal_year", "fiscal_quarter",
             "half", "month", "long_range_start_year", "long_range_end_year",
             "period_scope")):
        raise PeriodResolutionError(
            "sentinel_class excludes every dated/fiscal/scope field — park")


def _declared_scope(item):
    """ONE field→scope mapping so the exact-dates path labels a window exactly as the
    SEC/prediction/pure-math paths would (reproduced: the same gp_ window got exact_range
    via XBRL dates but quarter via SEC → the OD-21 surprise↔home scope match broke).
    Fields, not date math: the window alone can't tell a 52/53-week quarter from an odd
    range, and the declared fiscal framing is the semantic truth (PER-11/13). Paths
    converge only when fiscal framing IS supplied; frameless exact dates honestly stay
    exact_range."""
    if item.get("fiscal_quarter") is not None:
        return "quarter"
    if item.get("half") is not None:
        return "half"
    if item.get("month") is not None:
        return "monthly"
    if item.get("long_range_end_year") is not None:
        return "exact_range"           # long_range retired -> exact_range (95 #23)
    if item.get("fiscal_year") is not None:
        return "annual"
    return "exact_range"               # undeclared framing stays honest


def _cumulative(item, scope, time_type, fye, cal, ticker, lk):
    if time_type != "duration":
        raise PeriodResolutionError(f"{scope} is a cumulative window — cannot be instant")
    if item.get("half") or item.get("month"):
        raise PeriodResolutionError(f"{scope} conflicts with half/month fields")
    fy = item.get("fiscal_year")
    if not fy:
        raise PeriodResolutionError(f"{scope} needs fiscal_year")
    if not cal and ticker:
        corrected = lk["corrected_fye"](ticker)
        if corrected is not None:
            fye = _lawful_fye(corrected)   # the cache's answer is validated too
    if fye is None:
        raise PeriodResolutionError("fye_month required for ytd/ttm fiscal math")
    # P-O8 (U-4): a missing quarter is a PARK, never a quiet Q4 default
    # (REVIEW_RULES §4 — never-quiet-defaults).
    q = item.get("fiscal_quarter")
    if q is None:
        raise PeriodResolutionError(
            f"{scope} without fiscal_quarter — the cumulative window's anchor "
            f"quarter is a semantic judgment, never defaulted — park")
    end = _compute_fiscal_dates(fye, fy, f"Q{q}")[1]
    if scope == "ytd":
        start = _compute_fiscal_dates(fye, fy, "Q1")[0]
    else:  # ttm: day after the same fiscal quarter's end one year earlier
        prior_end = _compute_fiscal_dates(fye, fy - 1, f"Q{q}")[1]
        start = (date.fromisoformat(prior_end) + timedelta(days=1)).isoformat()
    return _result(build_period_id(start, end), scope, "duration", start, end)


_HIT_KEYS = {
    # exact allowed key sets per callback kind (P-O3): unknown extras FAIL CLOSED
    "existing": (frozenset({"period_u_id", "start_date", "end_date"}),
                 frozenset({"period_scope", "time_type"})),
    "sec": (frozenset({"start", "end"}), frozenset()),
    "predict": (frozenset({"start", "end"}), frozenset()),
}


def _lawful_hit(kind, result, want_scope, want_time_type):
    """P-O3 (U-6): every AFFIRMATIVE lookup answer passes this ONE checker and
    is returned UNCHANGED — no normalization, no defaulting, no discarding.
    Anything unlawful PARKS typed; the callbacks' own contracts are the law
    (existing -> {period_u_id, start_date, end_date} [+ scope/time_type,
    equal-or-park]; sec/predict -> {start, end}). Date grammar goes through
    the F-IDLAW owner (build_period_id -> parse_period_id) — no second ISO
    rule exists here."""
    if not isinstance(result, dict) or not result:
        raise PeriodResolutionError(
            f"PERIOD_SYM: {kind} lookup returned a non-dict or empty answer "
            f"{result!r} — an affirmative result must be lawful, park")
    required, optional = _HIT_KEYS[kind]
    keys = frozenset(result)
    extra = keys - required - optional
    if extra:
        raise PeriodResolutionError(
            f"PERIOD_SYM: {kind} lookup answer carries unknown key(s) "
            f"{sorted(extra)} — park")
    missing = required - keys
    if missing or any(result.get(k) is None for k in required):
        raise PeriodResolutionError(
            f"PERIOD_SYM: {kind} lookup answer is missing {sorted(missing) or 'values'} "
            f"of its required shape — park")
    if kind == "existing":
        u_id = result["period_u_id"]
        if not isinstance(u_id, str):
            raise PeriodResolutionError(
                f"PERIOD_SYM: existing hit period_u_id must be a string, got "
                f"{type(u_id).__name__} — park")
        start, end = result["start_date"], result["end_date"]
        rebuilt = build_period_id(start, end)     # the F-IDLAW owner judges
        if rebuilt != u_id:
            raise PeriodResolutionError(
                f"PERIOD_SYM: existing hit dates {start}..{end} rebuild to "
                f"{rebuilt}, not the returned id {u_id} — park")
        got_scope = result.get("period_scope")
        if got_scope is not None and got_scope != want_scope:
            raise PeriodResolutionError(
                f"SCOPE_PAIR: existing hit scope {got_scope!r} conflicts with "
                f"the request's {want_scope!r} — park")
        got_tt = result.get("time_type")
        if got_tt is not None and got_tt != want_time_type:
            raise PeriodResolutionError(
                f"INSTANT: existing hit time_type {got_tt!r} conflicts with "
                f"the requested {want_time_type!r} — park")
    else:
        try:
            parse_period_id(build_period_id(result["start"], result["end"]))
        except IdLawError as e:
            raise PeriodResolutionError(
                f"ISO: {kind} lookup dates are not lawful ({e}) — park")
    return result


def _preserved(item):
    u_id = item["period_u_id"]
    # ONE parse through the existing IdLawError -> PeriodResolutionError boundary:
    # a sentinel returns (None, None), a dated id returns its exact captured text.
    start, end = _check(u_id)
    # P-O2: conflicting SUPPLIED fields are parks, never silently discarded —
    # a preserved id excludes every framing field, and supplied dates must
    # equal the id's own.
    for k in ("fiscal_year", "fiscal_quarter", "half", "month",
              "long_range_start_year", "long_range_end_year", "sentinel_class"):
        if item.get(k) is not None:
            raise PeriodResolutionError(
                f"SCOPE_PAIR: preserved period_u_id with conflicting supplied {k}"
                f"={item.get(k)!r} — park")
    for k, want in (("period_start_date", start), ("period_end_date", end)):
        if item.get(k) is not None and item.get(k) != want:
            raise PeriodResolutionError(
                f"PERIOD_SYM: supplied {k}={item.get(k)!r} disagrees with the "
                f"id {u_id} — park")
    return _result(u_id, item.get("period_scope"), item.get("time_type"),
                   start, end)


def _result(u_id, scope, time_type, start, end):
    # P-O2: EVERY exit consumes the one invariant (the validate kwarg is
    # DELETED — no path may opt out of the law).
    verdicts = period_invariant(u_id, scope, time_type, start, end)
    if verdicts:
        code, msg = verdicts[0]
        raise PeriodResolutionError(f"{code}: {msg} — park")
    return {"period_u_id": u_id, "period_scope": scope, "time_type": time_type,
            "gp_start_date": start, "gp_end_date": end}


def _check(u_id):
    """Parse the period id at THE one owner; returns its (start, end) pair —
    (None, None) for sentinels — with IdLawError mapped to the resolver's
    fail-closed boundary."""
    try:
        return parse_period_id(u_id)
    except IdLawError as e:
        raise PeriodResolutionError(str(e))


def _default_lookups():
    """The live cascade (Neo4j/Redis), imported LAZILY by reference from the read-only
    guidance substrate — never at module import, so tests and dry-runs stay pure.
    Transition note (GuidancePeriod.md): the existing-window lookup still searches the old
    guidance graph; it gains DriverPeriod once DriverUpdates exist (writer step, S3.4/5)."""
    import guidance_write_cli as g
    return {"existing": g._lookup_existing_period, "sec": g._lookup_sec_cache,
            "predict": g._predict_from_prev_quarter, "corrected_fye": g._get_sec_corrected_fye}
