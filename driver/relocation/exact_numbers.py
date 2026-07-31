"""exact_numbers — THE shared exact-value/date helpers for the locator engine (v5.5 §4/§5).

Pure functions, no I/O, no channel imports. Decimal-exact everywhere: floats are REJECTED at the
door because a float may have ALREADY lost the source value (same philosophy as the id law's
num_canon).

DATES — the three statements, kept apart because conflating them caused a false conflict
(corrected 2026-07-27): a FILING states inclusive dates · stored XBRL duration ends are EXCLUSIVE
(the claimed end plus one day — see `stored_period_end`) · `period_key` is NEUTRAL: it validates
and orders an ISO pair and applies no convention at all, so both of its sides must already be in
the same form. Comparison is normalize-once-by-known-format then EXACT — no ±1-day tolerance sets
(they accepted convention-inconsistent pairs; reproduced round 5). The earlier header sentence
called the storage convention "inclusive", which described the filing's dates, not storage.
"""
import decimal
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, localcontext


class ExactError(ValueError):
    """Bad input to an exact comparison — callers treat as non-matching / abstain."""


# ---------------------------------------------------------------------------
# THE Route-A semantic unit law — ONE definition, shared.
#
# It lived only in `locator.py`, which cannot be imported from the package path
# (its bare `import exact_numbers` fails), so the binder hand-rolled a weaker
# copy and every share/EPS fact stopped binding. Defined HERE, in the
# dependency-free module, and re-exported by `locator` so its pinned census test
# and the probe scripts keep working unchanged.
#
# The KEY is the GRAPH's own spelling: the graph drops the `xbrli:` namespace
# prefix and keeps every other one (census 2026-07-27 — 0 of 6,957 Unit nodes
# carry `xbrli:`; `iso4217:`, `utr:` and company prefixes are all preserved).
# The three entries ARE the ratified materializer whitelist (BUILD 8.2 P4c);
# anything else — `pure`, other currencies, utr units, other divides — is
# lawful XBRL that this route deliberately SKIPS.
ROUTE_A_SEM_UNIT = {('iso4217:USD', False): 'usd',
                    ('shares', False): 'count',
                    ('iso4217:USDshares', True): 'usd_per_share'}

# ONLY the exact graph strings. Python ints and bools ABSTAIN — `str(1)` is
# '1', so a `str(x) in ('0','1')` test silently accepted an int flag.
ROUTE_A_BOOLS = {'0': False, '1': True}

# THE unit-compatibility relation, ONE definition: which SEMANTIC readings a
# given canonical stored unit may lawfully state. It existed twice, written in
# opposite directions — `locator._ANCHOR_UNIT` (canonical -> semantic) and the
# v2 contract's own semantic -> canonical map. They agreed, which is exactly
# how a pair like that survives long enough to drift.
#
# `usd_per_share` sits under `usd` and NOT under `m_usd`: a stated per-X
# denominator lives in the NAME and the value keeps the base unit (NAME-13),
# so a per-share figure scaled to millions is the cents-on-aggregate mistake
# FINAL_DESIGN 6.1 hard-fails.
ROUTE_A_UNIT_COMPAT = {
    'usd':   frozenset({'usd', 'usd_per_share'}),
    'm_usd': frozenset({'usd'}),
    'count': frozenset({'count'}),
}

# ---------------------------------------------------------------------------
# THE CANDIDATE-FACT unit compatibility law (owner ruling 2026-07-27).
#
# THREE TABLES, THREE OWNERS — deliberately NOT unified, and a future reader
# should not "tidy" them together:
#   ROUTE_A_SEM_UNIT      the DORMANT no-AI XBRL materializer's whitelist
#                         (BUILD 8.2 P4c). Frozen; this expansion is not its.
#   ROUTE_A_UNIT_COMPAT   the locator's anchor accept-set.
#   CANDIDATE_XBRL_UNIT_COMPAT (here)  what an AI-interpreted candidate fact may
#                         lawfully claim, given the unit the graph records.
#
# The bug this fixes: the candidate path borrowed the MATERIALIZER's whitelist,
# so every `pure` fact was refused — 663,778 numeric facts across 10,322
# reports and 15,017 concepts (live census 2026-07-27).
#
# `pure` means DIMENSIONLESS. It does not itself choose the unit: the same
# `pure` fact can be a percentage, a plain count or a ratio, and only the
# source's own wording decides. Proven on real filings — 4,132,000 "shares of
# Sylvamo common stock" and "over 30 producers" are both `pure` COUNTS, while
# "2.6 %" is a `pure` PERCENT and "3.0 to 1.0" is a `pure` RATIO.
#
# CODE CHECKS COMPATIBILITY ONLY. It never infers the unit from the concept
# name — `RestructuringAndRelatedCostNumberOfPositionsEliminatedPeriodPercent`
# carries both "NumberOf" and "Percent" in one name.
_PERCENT_FAMILY = ('percent', 'percent_yoy', 'percent_sequential',
                   'percent_points', 'basis_points')

_CANDIDATE_EXACT = {
    ('iso4217:USD', False):      frozenset({'usd', 'm_usd'}),
    ('shares', False):           frozenset({'count'}),
    # `unknown` is the EXISTING fail-safe — the source genuinely may not
    # distinguish a rate from a count from a ratio.
    ('pure', False): frozenset({'count', 'x', 'unknown'} | set(_PERCENT_FAMILY)),
}

_UNKNOWN = frozenset({'unknown'})
_XBRLI = 'xbrli:'


def _strip_xbrli(measure):
    return (measure[len(_XBRLI):]
            if measure.lower().startswith(_XBRLI) else measure)


def candidate_units_for(unit_name, is_divide, numerator=(), denominator=()):
    """Which canonical units an AI-interpreted candidate fact may claim, given
    the unit the GRAPH records. A FUNCTION, not a table, because the currency
    space is open-ended.

    NON-USD MONEY IS `unknown`, NOT A REFUSAL. FINAL_DESIGN:206 — "non-USD gaps
    may stay `unknown` (monitored)". Adding real `eur`/`cny` units remains an
    OPEN expansion; using the fail-safe that already exists is locked law. An
    earlier version made every foreign-currency fact abstain, and a test of
    mine cemented that as though it were intended — a test certifying a law
    violation is worse than the violation.

    Everything else (utr:*, custom units) has no compatible canonical unit on
    this route, so the caller refuses it. The empty set says exactly that.
    """
    # A DIVIDE UNIT IS JUDGED BY ITS STRUCTURED NUMERATOR, never by the graph
    # name, which is the measures CONCATENATED: `utr:galutr:M` (140 live facts)
    # cannot be split back reliably. The numerator fixes the BASE unit; the
    # denominator is the per-X, which NAME-13 puts in the driver NAME and the
    # model owns (validated later, at admission). One rule covers EPS
    # (USD/share) and oil (USD/barrel) alike, so EPS is no longer a special
    # row sitting beside the general one.
    if is_divide:
        nums = [_strip_xbrli(m) for m in numerator]
        if len(nums) != 1:
            return frozenset()          # unreadable shape -> park, never guess
        if nums[0] == 'iso4217:USD':
            return frozenset({'usd'})   # base unit; the per-X is in the name
        if nums[0].startswith('iso4217:'):
            return _UNKNOWN             # 620 CADshares, 481 EURshares, ...
        return frozenset()              # utr:gal/utr:M — not money at all
    key = (unit_name, is_divide)
    if key in _CANDIDATE_EXACT:
        return _CANDIDATE_EXACT[key]
    # `iso4217:` IS the ISO-4217 currency namespace — a namespace test, not a
    # guess about the concept: whatever the currency, the fact is money we do
    # not canonicalise, and `unknown` is the only honest carrier.
    if not is_divide and unit_name.startswith('iso4217:'):
        return _UNKNOWN
    return frozenset()


def graph_unit_spelling(measures, numerator, denominator, is_divide):
    """Render a FILING's declared measures in the GRAPH's own spelling.

    A divide unit's graph name is numerator+denominator CONCATENATED
    (`iso4217:USD` over `xbrli:shares` -> `iso4217:USDshares`); a plain unit's
    name is its single measure. Only the `xbrli:` prefix is dropped — see the
    census above. Returns None when the shape is not a single plain measure.
    """
    strip = lambda m: m[len(_XBRLI):] if m.lower().startswith(_XBRLI) else m
    if is_divide:
        return (''.join(strip(m) for m in numerator)
                + ''.join(strip(m) for m in denominator))
    return strip(measures[0]) if len(measures) == 1 else None


def exact_scaleb(value, exponent):
    """THE one power-of-ten shift — every caller in both layers routes here.

    It lived in `slot_convert` (core, unreachable from relocation), so the
    binder hand-rolled `Decimal(1).scaleb(int(...))` twice and Core once. The
    unguarded copies raised a raw `decimal.Overflow` on a legal-but-extreme
    `ix.scale`; an unrepresentable magnitude is a fact we cannot store — a PARK
    — never a crash. Moved here because this module is dependency-free and both
    layers can import it; each caller converts the error to ITS OWN park.

    A power-of-ten shift never changes the coefficient, so the precision is
    taken from the value and the result is exact; `Inexact` is trapped so a
    silent rounding can never pass. Emax/Emin are widened, so only genuinely
    unrepresentable magnitudes fail.

    The exponent must be a REAL `int`: `bool` is an int subclass, and a float or
    a numeric string would coerce a value we never verified.
    """
    if type(exponent) is not int:
        raise ExactError(
            f"scale exponent must be a real int, got {type(exponent).__name__}: "
            f"{exponent!r}")
    if not isinstance(value, Decimal):
        raise ExactError(f"exact_scaleb needs a Decimal, got {type(value).__name__}")
    if not value.is_finite():
        # NaN and +/-Infinity were shifted happily and returned unchanged. A
        # non-finite is never a source number — `dec()` above has always said
        # so, and the shift must agree rather than propagate it.
        raise ExactError(f"non-finite is never a source number: {value}")
    try:
        with localcontext() as ctx:
            ctx.prec = max(len(value.as_tuple().digits) + 1, 28)
            ctx.Emax, ctx.Emin = decimal.MAX_EMAX, decimal.MIN_EMIN
            ctx.traps[decimal.Inexact] = True
            return value.scaleb(exponent)
    except (decimal.DecimalException, ValueError, OverflowError) as e:
        raise ExactError(
            f"scaling {value} by 10^{exponent} is not exactly representable "
            f"({type(e).__name__}) — park, never a rounded guess")


def stored_period_end(iso):
    """THE stored-period-end rule, in ONE place.

    The graph keeps an XBRL duration's end date EXCLUSIVE — the claimed end
    PLUS ONE DAY — and stores an instant the same way (Fable ruling 2026-07-09,
    140/140 verified; `slice_menu.match_xbrl_fact` is the certified consumer).
    Proven again on real data 2026-07-27: the CE 726 fact is 2023-01-01..
    2023-06-30 in the filing and ..2023-07-01 in the graph.

    It existed as two byte-identical private copies (`inline_html._plus_day`
    and `slice_menu._plus_day`) — one law, two places to drift.

    (The header's three date statements settle this: a filing states inclusive
    dates, storage is exclusive, `period_key` applies no convention. There is
    no open question here — an earlier note in this docstring said there was,
    and pointed at a header line that had already been rewritten.)
    """
    return (_iso_date(iso) + timedelta(days=1)).isoformat()


_STRICT_ISO = __import__("re").compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _iso_date(d):
    """THE one date parser, STRICT. XML `xs:date` requires the hyphenated
    YYYY-MM-DD form, but `date.fromisoformat` also accepts the compact
    `20230630` and (3.11+) other ISO spellings — so a shape XBRL forbids would
    have been read as a date. The regex fixes the SHAPE; `date(...)` then does
    the real CALENDAR check, so `2024-02-30` fails as surely as `2024-13-01`.

    CENSUS 2026-07-28: 11,415 of 11,416 stored Periods already carry the strict
    form; the single exception is `224-04-01` (a 3-digit year), which a
    well-formed claim could never have matched anyway.
    """
    if not isinstance(d, str) or not _STRICT_ISO.fullmatch(d):
        raise ExactError(f"bad ISO date (need strict YYYY-MM-DD): {d!r}")
    try:
        return date(*(int(part) for part in d.split("-")))
    except (TypeError, ValueError):
        raise ExactError(f"impossible calendar date: {d!r}")


def dec(value):
    """Exact Decimal from str/int/Decimal. Floats REJECTED (already potentially lossy)."""
    if isinstance(value, bool) or isinstance(value, float):
        raise ExactError(f"floats are rejected (lossy): {value!r}")
    if isinstance(value, Decimal):
        d = value
    else:
        try:
            d = Decimal(str(value).strip())
        except (InvalidOperation, TypeError, ValueError):
            raise ExactError(f"not a decimal number: {value!r}")
    if not d.is_finite():
        raise ExactError(f"non-finite is never a source number: {value!r}")   # round-12: NaN/Inf
    return d


def eq(a, b):
    """Decimal-exact equality; trailing zeros are not a difference. Bad input -> ExactError."""
    return dec(a) == dec(b)


def _iso(d):
    return _iso_date(d).isoformat()          # ONE date parser, not two


def period_key(start, end):
    """Validated (start, end) ISO pair, EXACT — the one date rule. No tolerance of any kind."""
    s, e = _iso(start), _iso(end)
    if e < s:
        raise ExactError(f"period ends before it starts: {start!r}..{end!r}")
    return (s, e)


def plain(value):
    """Canonical plain string: no exponent, no trailing zeros, '-0' -> '0'."""
    out = format(dec(value), 'f')
    if '.' in out:
        out = out.rstrip('0').rstrip('.')
    return '0' if out in ('', '-0') else out


def is_instant(start, end):
    """True iff start == end — the law's proven instant form (gp_DATE_DATE)."""
    s, e = period_key(start, end)
    return s == e
