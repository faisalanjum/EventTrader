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
# ---------------------------------------------------------------------------
# THE THREE READINGS, KEYED ON IDENTITY.
#
# RETIRED IN #827 STAGE 3: `ROUTE_A_SEM_UNIT`, which keyed these same three
# readings on the GRAPH's own text `(Unit.name, is_divide)`. A prefix is only an
# alias, so that table answered the wrong question twice over:
#
#   `cur:USD`      a lawful filing binding `cur` to the official ISO-4217 URI
#                  states US dollars, and the table did not recognise it —
#                  a correct filing silently dropped;
#   `iso4217:USD`  a filing rebinding `iso4217` to `urn:evil` states no
#                  currency at all, and the table accepted it — a fabricated
#                  unit attached as money.
#
# These keys are (namespace URI, local name) pairs read from the FILING's own
# in-scope declarations, so neither mistake is expressible. The readings and the
# scope are unchanged: exactly the three the ratified materializer whitelist
# admits, and everything else still abstains.
#
# THE ONE OWNER of the two namespace URIs both layers share — this module is
# the dependency-free home every consumer already imports. Exact primary
# sources:
#   ISO_4217_NAMESPACE — XBRL 2.1 REC-2003-12-31 + corrected errata
#     2013-02-20, §4.8.2 (units for monetary items MUST use ISO 4217 measures
#     in this namespace; prefix association added by erratum 2.1.5).
#   XBRL_INSTANCE_NAMESPACE — same specification, §1.6 "Namespace Prefix
#     Conventions" (prefix xbrli).
ISO_4217_NAMESPACE = 'http://www.xbrl.org/2003/iso4217'
XBRL_INSTANCE_NAMESPACE = 'http://www.xbrl.org/2003/instance'
# EU-001 (#827): these three maps carry Route A step 5's "semantic
# Unit/divide meaning" under its closing law — "No raw-unit spelling
# classifier ... belongs in this route" (FinalPlan §5A Route A). The
# MEANING side is spelled in expanded names under the two spec-cited
# namespaces above; the CANONICAL side consumes C1's one vocabulary
# (slot_convert.CANONICAL_UNITS) — proven by the handoff-census pin
# (this module may not import Core, so the membership law lives in the
# suite, the F7 both-sides pattern). 'usd_per_share' is a route-local
# SEMANTIC reading, never a stored unit (NAME-13 / FD 6.1 below).
#: expanded MEASURES tuple -> reading, for a simple (non-divide) unit.
ROUTE_A_SEM_UNIT_SIMPLE = {
    ((ISO_4217_NAMESPACE, 'USD'),): 'usd',
    ((XBRL_INSTANCE_NAMESPACE, 'shares'),): 'count',
}
#: (expanded numerator, expanded denominator) -> reading, for a divide unit.
ROUTE_A_SEM_UNIT_DIVIDE = {
    (((ISO_4217_NAMESPACE, 'USD'),),
     ((XBRL_INSTANCE_NAMESPACE, 'shares'),)): 'usd_per_share',
}


def route_a_semantic_unit(declared):
    """The Route-A reading of ONE filing-declared unit, or None to abstain.

    `declared` is the unit record `inline_html.prepare` publishes for a
    `unitRef` — the filing's OWN measures, already resolved to expanded names in
    the scope where they are written. Nothing here reads a prefix, a graph
    string, or a concatenated `Unit.name`.

    None means "this route does not claim to read that unit", which is the same
    answer the spelling table gave for everything outside its three entries.
    """
    if not isinstance(declared, dict):
        return None
    # EU-033 (#827): the branch keys here are statement-level audited — a
    # missing or drifted key ABSTAINS (the .get falls to the empty lookup),
    # never misreads; the fail-closed stance's measured coverage is 93.25%
    # answered / 6.75% abstain (receipt g2_evid_recall_EU-033.txt). Reach
    # lane today: proof-only callers (locator :1096, call-trace v5).
    if declared.get('is_divide'):
        return ROUTE_A_SEM_UNIT_DIVIDE.get(
            (tuple(declared.get('expanded_numerator') or ()),
             tuple(declared.get('expanded_denominator') or ())))
    return ROUTE_A_SEM_UNIT_SIMPLE.get(
        tuple(declared.get('expanded_measures') or ()))

# ONLY the exact graph strings. Python ints and bools ABSTAIN — `str(1)` is
# '1', so a `str(x) in ('0','1')` test silently accepted an int flag.
# EU-007 (#827): the accepted-spelling set is the graph stored-spelling
# clause at the F7 boundary owner (driver/core/graph_row_contract.py).
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
# TWO TABLES, TWO OWNERS — deliberately NOT unified, and a future reader should
# not "tidy" them together:
#   ROUTE_A_UNIT_COMPAT   the locator's anchor accept-set.
#   candidate_units_for   what an AI-interpreted candidate fact may lawfully
#                         claim given the unit the graph records — it lives in
#                         `driver/core/xbrl_attach.py`, NOT here. This block
#                         said "(here)" and then described its rules in
#                         detail, which stopped being true the moment the
#                         function moved to its one Core caller; the rules now
#                         live in that function's own docstring, where they
#                         can go stale only alongside the code they govern.
def graph_unit_spelling(measures, numerator, denominator, is_divide):
    """Render a FILING's declared measures in the GRAPH's own spelling.

    A divide unit's graph name is numerator+denominator CONCATENATED
    (`iso4217:USD` over `xbrli:shares` -> `iso4217:USDshares`); a plain unit's
    name is its single measure. Only the `xbrli:` prefix is dropped — see the
    census above. Returns None when the shape is not a single plain measure.
    """
    # NO PREFIX RULE LIVES HERE ANY MORE. `strip_xbrli` matched the literal,
    # case-folded text `xbrli:`, which is a prefix convention pretending to be
    # an identity: a filing may lawfully bind the instance namespace to any
    # prefix, and one that binds it to `i:` had every share and per-share fact
    # thrown away. The measures arriving here are ALREADY in the graph's
    # spelling, decided by NAMESPACE in `inline_html._graph_measure`, where the
    # in-scope declarations are known. This function now only concatenates.
    # EU-020 (#827): the empty-string JOIN is the graph's stored unit-name
    # spelling — the concatenation law of the F7 boundary owner's
    # stored-spelling clause (the graph writes iso4217:USDshares with no
    # separator; the census at the module head prices it, the clause owns it).
    if is_divide:
        return ''.join(numerator) + ''.join(denominator)
    return measures[0] if len(measures) == 1 else None


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

    EU-016 (#827), adjudicated: the trap enable is the RETAINED fail-closed
    safety net (the S8 precedent). It is unreachable today — coefficient
    preservation makes a scaleb inexactness impossible at value precision,
    measured across all four exactness suites (386/386 green with the trap
    off; receipt g2_evid_recall_EU-016.txt) — and it stays BECAUSE it is
    the statement of the law, not because an input reaches it.

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
            # THE VALUE'S OWN DIGIT COUNT, exactly. A power-of-ten shift moves
            # the exponent and never the coefficient, so this precision is
            # sufficient by construction; one lower silently shortens a
            # trailing-zero coefficient (Rounded, which is not trapped). The
            # old `max(len + 1, 28)` carried two uncitable numbers — proven
            # representation-identical to this across 5,456 cases before
            # removal (#827 bundle A), and the verbatim-coefficient pin lives
            # in the round-12 owner.
            ctx.prec = len(value.as_tuple().digits)
            ctx.Emax, ctx.Emin = decimal.MAX_EMAX, decimal.MIN_EMIN
            ctx.traps[decimal.Inexact] = True
            return value.scaleb(exponent)
    except (decimal.DecimalException, ValueError, OverflowError) as e:
        # THE MESSAGE NEVER PRINTS THE EXPONENT. `f"{n}"` is a string
        # conversion, which CPython refuses past 4,300 digits — so for exactly
        # the magnitudes this park exists to catch, building the park's own
        # message raised a raw `ValueError` and the crash escaped the guard
        # written to prevent it. The exponent is simply not interpolated: any
        # threshold for "short enough to show" would be a fixed value nobody
        # can cite, which is the class of rule this round exists to remove.
        raise ExactError(
            f"scaling {value} by the supplied exponent is not exactly "
            f"representable ({type(e).__name__}) — park, never a rounded guess")


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
    try:
        # EU-034 (#827): the +1 IS the exclusive-end stored form — the F7
        # boundary owner's stored-spelling clause (EU-007/018/019/029), at
        # its ONE shared implementation (the two private copies folded).
        return (_iso_date(iso) + timedelta(days=1)).isoformat()
    except OverflowError:
        # The day after `9999-12-31` is off the representable calendar. This
        # used to escape as OverflowError — which NO caller catches, so it
        # travelled all the way out through the live matcher
        # (`slice_menu.match_xbrl_fact`). Every caller already catches this
        # module's own refusal, so raising THAT needs no caller change.
        raise ExactError(f"the day after {iso!r} is outside the representable "
                         f"calendar, so it cannot be an exclusive end")


#: THE LAWFUL-AND-REPRESENTABLE INTERSECTION, and it is NOT the `xs:date`
#: grammar — `_DATE_RE` above is that, and it lawfully accepts an optional
#: minus, five-or-more year digits and a timezone. This is the graph/Core
#: boundary, where a date must be exactly the date-only four-digit spelling and
#: nothing is normalised. Two authorities, both needed:
#:   · XSD 1.0 2e §3.2.9.1 — a MINIMUM four-digit year, so `224-04-01` is not
#:     lawful `xs:date` at all;
#:   · CPython `date` — years 1..9999, so five-digit and negative years are not
#:     representable however lawful they are.
#: Their intersection is exactly four digits. The writer is NOT the authority:
#: `strftime('%Y')` is unpadded on this platform, so it CAN emit `224-04-01`,
#: and the graph holds one (1 of 11,416 Period nodes). This boundary refuses it
#: rather than padding a year the filing never wrote.
# EU-007 (#827): this strict shape is the graph stored-spelling clause at
# the F7 boundary owner (driver/core/graph_row_contract.py) — the XSD/
# CPython intersection derivation above is its authority chain.
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
        # EU-011 (#827): the '-' separator is the same boundary clause's
        # mechanics (graph_row_contract's stored-spelling clause; the shape
        # regex above already fixed it) — never a second grammar.
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
    # EU-031 (#827): the ordering rule is the verified XBRL 2.1 period
    # constraint (endDate must not precede startDate); the '..' below is
    # MESSAGE formatting only — never a stored spelling (the stored period
    # spellings live at the F7 boundary owner's clause). Proof-lane reach
    # (locator callers, call-trace v5).
    if e < s:
        raise ExactError(f"period ends before it starts: {start!r}..{end!r}")
    return (s, e)


def plain(value):
    """Canonical plain string: no exponent, no trailing zeros, '-0' -> '0'.

    EU-032 (#827): this IS the canonical-decimal-form law of the F7
    boundary owner's stored-spelling clause (graph_row_contract) — the
    same OD-8 canon dec_canon states Core-side; the format-code/strip/
    negative-zero mechanics below are that one clause's arithmetic, never
    a second grammar. Proof-lane reach (locator callers, call-trace v5).
    """
    out = format(dec(value), 'f')
    if '.' in out:
        out = out.rstrip('0').rstrip('.')
    return '0' if out in ('', '-0') else out


def is_instant(start, end):
    """True iff start == end — the law's proven instant form (gp_DATE_DATE)."""
    s, e = period_key(start, end)
    return s == e


# ---------------------------------------------------------------------------
# THE SHARED XBRL dateUnion PARSER (#827 finding 2).
#
# XBRL 2.1 §4.7.2 types the period children as `xbrli:dateUnion` — `xs:date`
# OR `xs:dateTime` — so BOTH are law, whatever a given corpus happens to
# contain. (Receipt 09 found 1,103,247 period values all date-only; that
# justified using only the standard library here, and NOT rejecting dateTime.)
#
# Callers: the inline-XBRL filing binder and the locator's Route-A branch.
# `stored_period_end` above keeps the graph/PreparedFact contract, which stays
# exact DATE-ONLY and is deliberately not widened.
#
# Two distinct outcomes, never merged:
#   * MALFORMED  -> ExactError. Not a lawful dateUnion lexical form at all.
#   * LAWFUL but unbindable -> a boundary carrying `.park`, a NAMED reason.
#     A timezone is never invented and a time is never truncated to fit the
#     graph's date-only convention.
# ---------------------------------------------------------------------------

from collections import namedtuple as _namedtuple  # noqa: E402

#: `lexical` (the raw text) was carried here and read by NOTHING — every park
#: reason already quotes what it needs. A record field nobody reads is the same
#: unearned machinery this round exists to remove, so it is gone.
FilingBoundary = _namedtuple("FilingBoundary",
                            ("kind", "moment", "has_timezone", "park"))

# `FOREVER_PARK_REASON` stood here and NOTHING in production ever read it —
# the binder returns its own `forever_or_undated_period`, and a test asserted
# on the constant, so the pair read as a proven rule while being two unrelated
# strings. Deleted rather than wired up: the binder's reason is the one the
# caller actually receives, so it is the one a test must assert.

# XML whitespace is SPACE, TAB, CR, LF and nothing else. NBSP, vertical tab,
# form feed and the Unicode space family are ordinary characters here, so a
# value padded with them is malformed rather than quietly trimmed.
#: PUBLIC because `inline_html` needs the same answer. It kept its own copy of
#: this string, which is two owners of one rule — the exact shape that produced
#: the `_plus_day` twins and the `strip_xbrli` lambda. Whitespace is not a
#: formatting preference here: it decides whether a padded value is lawful.
XML_WS = " \t\r\n"

_YEAR = r"-?(?:[1-9][0-9]{3,}|0[0-9]{3})"
_MD = r"-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])"
# ±14:00 is the XML Schema limit; 14:01 and beyond are not lawful.
_TZ = r"(?:Z|[+-](?:(?:0[0-9]|1[0-3]):[0-5][0-9]|14:00))"
# `:60` is admitted LEXICALLY and then parked as unrepresentable: XML Schema
# 1.0's own leap-second wording is ambiguous, and parking a value we cannot
# represent is the fail-visible reading.
#
# `24:00:00` IS REJECTED. XML Schema allows it, but XBRL 2.1 §4.7.2 forbids it
# in a period element — the end-of-day instant must be written as the next
# day's `00:00:00`. An earlier version of this parser accepted it and bound it
# to the following day, and my own test pinned that as law; the XBRL
# specification is narrower than XSD here and the narrower one governs.
_TIME = r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:(?:[0-5][0-9]|60)(?:\.[0-9]+)?"
_DATE_RE = __import__("re").compile(rf"{_YEAR}{_MD}({_TZ})?")
_DATETIME_RE = __import__("re").compile(rf"{_YEAR}{_MD}T{_TIME}({_TZ})?")


def parse_filing_boundary(raw):
    """One lawful `xbrli:dateUnion` boundary -> FilingBoundary.

    Raises ExactError for anything outside the lexical space. A LAWFUL value
    that cannot bind the graph's date-only contract comes back with `.park`
    set to a named reason instead of being repaired or rejected.
    """
    from datetime import datetime, timedelta as _td, timezone as _tz
    if not isinstance(raw, str):
        raise ExactError(f"period boundary must be a string: {raw!r}")
    text = raw.strip(XML_WS)
    if not text:
        raise ExactError("empty period boundary")
    m_dt = _DATETIME_RE.fullmatch(text)
    m_d = None if m_dt else _DATE_RE.fullmatch(text)
    if not (m_dt or m_d):
        raise ExactError(f"not a lawful xs:date or xs:dateTime: {raw!r}")
    kind = "dateTime" if m_dt else "date"
    tz_text = (m_dt or m_d).group(1)
    # THE YEAR IS NEVER CONVERTED WHOLE. XML Schema bounds neither the count of
    # year digits nor their value, and Python REFUSES to build an int from more
    # than 4,300 digits — so a lexically LAWFUL boundary crashed this parser
    # instead of parking (reproduced at 5,000 digits). Nothing here needs the
    # whole number:
    #   zero-ness      every digit is '0'
    #   the leap rule  depends only on year mod 400, and 10**4 is a multiple of
    #                  400, so the LAST FOUR DIGITS settle it for ANY year
    #   representable  a `date` needs 1..9999, which under XML Schema's
    #                  four-digit-minimum spelling is exactly "not negative and
    #                  not more than four digits"
    negative = text.startswith("-")
    year_digits = (text[1:] if negative else text).split("-")[0]
    if not any(d != "0" for d in year_digits):
        raise ExactError("year zero is forbidden by XML Schema 1.0")
    year_mod_400 = int(year_digits[-4:])          # bounded: four digits at most
    representable = not negative and len(year_digits) <= 4
    year = int(year_digits) if representable else None

    body = text[:-len(tz_text)] if tz_text else text
    d_part, _, t_part = body.partition("T")
    mo, dy = (int(p) for p in d_part.lstrip("-").split("-")[1:])

    # CALENDAR VALIDITY IS CHECKED FOR EVERY YEAR, representable or not. The
    # proleptic Gregorian leap rule is arithmetic, so `12023-02-30` is
    # IMPOSSIBLE (malformed) rather than merely "unrepresentable" — a value
    # must be lawful before the question of representability arises.
    # `year_mod_400` is CONGRUENT to the year modulo 400, and 4 and 100 both
    # divide 400, so every test inside `_days_in_month` gives the same answer
    # it would for the full year. The calendar rule therefore still applies to
    # every year, however large — parking an impossible date would launder it.
    if dy > _days_in_month(year_mod_400, mo):
        raise ExactError(f"impossible calendar date: {raw!r}")

    park = None
    if not representable:
        # the year is SHOWN, never re-expanded: formatting a 20,000-digit
        # number into a message is the same mistake in a different place.
        shown = ("-" if negative else "") + (
            year_digits if len(year_digits) <= 12
            else f"{year_digits[:6]}…({len(year_digits)} digits)")
        park = (f"year {shown} is lawful in XML Schema but not representable "
                f"by this runtime or the graph's date contract")

    # THE FRACTION IS READ AS DIGITS, NEVER AS A FLOAT (blocker 1). The old
    # `float("0."+digits) * 1e6` fed a rounding conversion into timedelta, so
    # `23:59:59.9999999` came back as the NEXT DAY's midnight and BOUND, and
    # `.0000004` silently became midnight. A boundary is an identity: it is
    # exact or it parks.
    micro, sub_micro, seconds = 0, False, 0
    if park is None and kind == "dateTime":
        hh, mm, ss_field = t_part.split(":")
        sec_digits, _, frac_digits = ss_field.partition(".")
        seconds = int(sec_digits)
        if seconds == 60:
            park = ("a leap second is not representable by this runtime — "
                    "parked rather than rounded")
        else:
            micro = int(frac_digits[:6].ljust(6, "0")) if frac_digits else 0
            sub_micro = any(d != "0" for d in frac_digits[6:])
            if sub_micro:
                park = ("the boundary states finer than microsecond "
                        "precision, which this runtime cannot hold exactly — "
                        "parked rather than truncated")

    moment = None
    if park is None:
        base = datetime(year, mo, dy)
        if kind == "dateTime":
            # INTEGER arithmetic only — nothing here can round — and it may
            # not escape as an exception at the calendar edge either.
            try:
                base = base + _td(hours=int(hh), minutes=int(mm),
                                  seconds=seconds, microseconds=micro)
            except OverflowError:
                return FilingBoundary(
                    kind=kind, moment=None,
                    has_timezone=bool(tz_text),
                    park=("this instant lies outside the representable "
                          "calendar — parked, never wrapped"))
        if tz_text:
            offset = (_td(0) if tz_text == "Z" else
                      (1 if tz_text[0] == "+" else -1)
                      * _td(hours=int(tz_text[1:3]), minutes=int(tz_text[4:6])))
            base = base.replace(tzinfo=_tz(offset))
        moment = base
        if tz_text:
            park = ("the boundary carries a timezone, and binding it to the "
                    "graph's timezone-less date would invent one")
        elif kind == "dateTime" and moment.time() != moment.min.time():
            park = ("the boundary carries a time of day, and binding it to "
                    "the graph's date would truncate that time")
        elif kind == "date":
            # A date-only boundary means the FOLLOWING midnight, so the graph
            # form needs one more day than the calendar can hold at its edge.
            # EU-029 (#827): the +1 here is the SAME exclusive-end law as
            # the F7 boundary owner's stored-spelling clause (EU-007/018/
            # 019) — this parser pre-checks representability for it.
            try:
                moment.date() + _td(days=1)
            except OverflowError:
                park = ("the following midnight this date-only boundary means "
                        "lies outside the representable calendar — parked, "
                        "never wrapped")
    return FilingBoundary(kind=kind, moment=moment,
                          has_timezone=bool(tz_text), park=park)


def _days_in_month(year, month):
    """Proleptic Gregorian month length, for ANY year — pure arithmetic, so a
    calendar check never depends on what `datetime` happens to represent."""
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    return 30 if month in (4, 6, 9, 11) else 31


def filing_boundary_graph_end(raw):
    """The graph's EXCLUSIVE end for one filing boundary, or None if it parks.

    A DATE-ONLY boundary means the following midnight, so it adds one day. A
    dateTime already IS the instant, so it adds nothing — the two spellings
    of the same moment therefore bind the same graph date.
    """
    b = parse_filing_boundary(raw)
    if b.park:
        return None
    # EU-018 (#827): the +1 day IS the exclusive-end stored form — the graph
    # period clause at the F7 boundary owner (graph_row_contract's
    # stored-spelling clause) and the contract sheet section 4 state it; a
    # dateTime adds nothing because it already IS the instant.
    if b.kind == "date":
        return (b.moment.date() + timedelta(days=1)).isoformat()
    return b.moment.date().isoformat()


def filing_boundary_graph_start(raw):
    """The graph's INCLUSIVE start for one filing boundary, or None if it parks.

    A START is not an END and does not share its rule: a date-only start means
    MIDNIGHT OF THAT DAY, so the graph keeps the date itself — no day is added.
    A dateTime start at exactly midnight is the same instant and binds the same
    date; one carrying any time of day, a timezone, or an unrepresentable year
    parks, because binding it would truncate or invent.

    Added because the binder compared the filing's start as a RAW STRING and so
    never validated it at all: a lawful `2024-01-01T00:00:00` could never match
    the graph's `2024-01-01`, and a malformed start was never refused.
    """
    b = parse_filing_boundary(raw)
    if b.park:
        return None
    return b.moment.date().isoformat()


def filing_duration_ordered(start_raw, end_raw):
    """True/False for start<end, or None when the comparison is INDETERMINATE.

    THE BOUNDARIES ARE COMPARED AS INSTANTS, NOT AS LEXICAL VALUES, and that
    distinction is the whole rule. XBRL's date-only START means midnight of
    its own day; a date-only END means THE FOLLOWING midnight. So a context
    with `startDate == endDate` is a lawful ONE-DAY period, not a zero-length
    one — 1,774 such contexts exist in a 400-filing sample of the live cache.
    A first version of this function compared the raw moments and refused
    every one of them; the corpus said otherwise.

    XML Schema orders timezone-aware against timezone-aware and naive against
    naive; a mixed pair has no total order without inventing a zone, so it
    parks. Unrepresentable boundaries are indeterminate too.
    """
    a, b = parse_filing_boundary(start_raw), parse_filing_boundary(end_raw)
    if a.moment is None or b.moment is None:
        return None
    start_instant = a.moment
    try:
        # EU-019 (#827): the same exclusive-end math as
        # filing_boundary_graph_end — the F7 boundary owner's stored-spelling
        # clause (EU-007/EU-018); the ordering law itself is XBRL 2.1
        # (endDate must not precede startDate), already cited verified.
        end_instant = (b.moment + timedelta(days=1) if b.kind == "date"
                       else b.moment)
    except OverflowError:
        # A date-only end means the FOLLOWING midnight; at the calendar edge
        # that midnight is not representable, so the comparison has no answer.
        # `None` already means exactly that here — the boundary parked for the
        # same reason, and this function must agree with it rather than crash.
        return None
    if a.has_timezone == b.has_timezone:
        return start_instant < end_instant
    return _xsd_before_across_timezone(start_instant, end_instant,
                                       left_is_aware=a.has_timezone)


#: XML Schema 1.0 §3.2.7.4 — an untimezoned value's true instant is unknown but
#: must lie within ±14:00 of its stated reading, so it spans a 28-hour window.
_XSD_TZ_LIMIT = timedelta(hours=14)


def _xsd_before_across_timezone(left, right, *, left_is_aware):
    """True/False/None for `left < right` when exactly ONE side carries a zone.

    EVERY mixed pair used to return None, which is not the standard: XML Schema
    orders the pair whenever the timezoned value lies OUTSIDE the untimezoned
    one's 28-hour window, and calls only an overlap indeterminate. Six months
    apart is not indeterminate.

    A `+14:00` reading is the EARLIEST possible instant (local time furthest
    ahead of UTC) and `-14:00` the LATEST, which is what makes the window.
    """
    from datetime import timezone as _tz
    if left_is_aware:
        earliest = right.replace(tzinfo=_tz(_XSD_TZ_LIMIT))
        latest = right.replace(tzinfo=_tz(-_XSD_TZ_LIMIT))
        if left < earliest:
            return True
        if left > latest:
            return False
        return None
    earliest = left.replace(tzinfo=_tz(_XSD_TZ_LIMIT))
    latest = left.replace(tzinfo=_tz(-_XSD_TZ_LIMIT))
    if latest < right:
        return True
    if earliest > right:
        return False
    return None
