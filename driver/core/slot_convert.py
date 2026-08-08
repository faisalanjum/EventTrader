"""Multiply-only numeric-slot conversion — FINAL_DESIGN §6.1 in its rev-4 form.

THE SPLIT. The reader states, for every populated numeric slot, an exact
`{value, scale_multiplier, unit_scale_evidence}` object plus the slot group's
final canonical unit. Code then does exactly ONE arithmetic operation —
multiplication — and checks structure and evidence membership.

WHAT THIS FILE MUST NEVER DO, and why:
  * read scale WORDS ("million", "crore", "milliard") — a word list passes our
    samples and misfires silently on the filings it never saw;
  * see a driver name, quote, concept name, or raw unit text in the CONVERTER —
    it cannot misuse an input it never receives (the signature is the fence);
  * apply a magnitude heuristic. There is no 999-style guard on this path: a
    lawful "in hundreds" filing would park and a wrong-but-common 1e9 would
    pass, so the guard bought nothing and cost real facts.

Presence and membership prove STRUCTURE. Whether the multiplier is the RIGHT
reading of the source is the model's answer, measured by hidden grading under
the zero-confirmed-wrong gate — never assumed here.
"""
import decimal
from decimal import Decimal, localcontext

# The 10-unit law enum (FINAL_DESIGN §6.1). Declared here rather than imported
# from the hint-era resolver: that resolver is retired on this path, and the new
# converter must not depend on it.
CANONICAL_UNITS = ("usd", "m_usd", "percent", "percent_yoy", "percent_sequential",
                   "percent_points", "basis_points", "count", "x", "unknown")

SLOT_KEYS = ("value", "scale_multiplier", "unit_scale_evidence")

# Units whose numbers ARE the measure: points and basis points are UNITS, never
# scales, so a multiplier other than 1 means the reading is unsafe -> park.
MULTIPLIER_ONE_UNITS = ("percent", "percent_yoy", "percent_sequential",
                        "percent_points", "basis_points", "x")


def family_required_multiplier(unit):
    """THE one owner of the ratio-family multiplier rule — membership AND the
    required value together (exp5 REV5 Part C :508; F-STORE S4 cross-link).
    Returns Decimal(1) for the six ratio-family units (points and basis points
    are UNITS, never scales), None for every other unit (no family
    requirement — the caller's own arithmetic governs). Three doors consume
    this; none re-authors the value half (C3, #827 F-UNITS)."""
    if unit in MULTIPLIER_ONE_UNITS:
        return Decimal(1)
    return None

_CENTS = Decimal("0.01")
_MILLION_EXPONENT = 6          # m_usd is "dollars, in millions"


class SlotConversionError(ValueError):
    """A slot could not be converted or validated safely. Callers PARK."""


# A TECHNICAL representation bound — NOT a magnitude judgment and NOT a
# 999-style meaning heuristic. The canonical stored form is an exponent-free
# decimal string, so a value whose expansion is astronomically long cannot be
# written, hashed or compared without unbounded memory: `Decimal("1E+999999999")`
# survived conversion and then died with MemoryError inside the canonicalizer.
#
# THE CAP, AND WHAT IT IS NOT. 1024 is an explicit RESOURCE CONTRACT on how
# wide a single stored number may be — chosen, not derived from meaning.
#
# MEASURED CORPUS (read-only census 2026-07-27) — only the two figures that bear
# on how wide a stored number can get: the longest stored numeric text is
# 31 characters, and the `decimals` attribute reaches 96. The bound therefore
# sits about thirty times above the widest observed figure. No claim is made
# about filings we have never seen: a number wider than this PARKS, and parking
# is a lawful outcome rather than a truncation.
_MAX_STORED_CHARS = 1024


def stored_char_length(value):
    """EXACT length of the CANONICAL exponent-free form, computed from the digit
    tuple — the string itself is never built, because building it is the failure
    being prevented.

    CANONICAL means trailing fractional zeros are gone: `dec_canon` stores
    `1.000...0` as plain `1`, so counting the zeros rejected a perfectly
    storable value. The zeros are stripped HERE, arithmetically, rather than by
    `normalize()` — normalize is context-sensitive and rounding at the context
    precision is what corrupted matching in the first place."""
    t = value.as_tuple()
    digits, exponent = list(t.digits), t.exponent
    while exponent < 0 and digits and digits[-1] == 0:   # drop trailing zeros
        digits.pop()
        exponent += 1
    if not digits or set(digits) == {0}:
        return 1                           # ZERO in ANY exponent form, signed or
                                           # not, canonicalizes to the single
                                           # character "0" (the law maps -0 -> 0);
                                           # counting its exponent rejected a
                                           # perfectly storable zero
    n, sign = len(digits), (1 if t.sign else 0)
    if exponent >= 0:
        return sign + n + exponent
    frac = -exponent
    return sign + max(n - frac, 1) + 1 + frac


def assert_storable(value):
    """Refuse a value whose canonical stored form cannot be materialised."""
    span = stored_char_length(value)
    if span > _MAX_STORED_CHARS:
        raise SlotConversionError(
            f"value needs {span} characters in canonical stored form (limit "
            f"{_MAX_STORED_CHARS}) — not storable; park. This is a resource "
            f"bound on representation, never a judgment about magnitude")
    return value


def exact_scaleb(value, exponent):
    """THE one power-of-ten shift, now owned by `exact_numbers` so the shared
    XBRL binder can reach it too — relocation cannot import core. This wrapper
    exists only to keep THIS module's error contract: callers here park on
    `SlotConversionError`. No arithmetic is duplicated."""
    from driver.relocation.exact_numbers import ExactError, exact_scaleb as _shift
    try:
        return _shift(value, exponent)
    except ExactError as e:
        raise SlotConversionError(str(e))


def exact_mul(a, b):
    """THE one exact multiplication. Precision is DERIVED from the operands, so
    nothing is ever rounded.

    A fixed cap is not exactness: an earlier version pinned 60 digits and
    silently truncated a 65-digit value, and shape comparisons running at the
    default 28-digit context let two DIFFERENT 29-digit numbers pass as equal.
    The exact product of an m-digit and an n-digit decimal needs at most m+n
    digits, so that is the precision used."""
    a = Decimal(a) if isinstance(a, int) else a
    b = Decimal(b) if isinstance(b, int) else b
    need = len(a.as_tuple().digits) + len(b.as_tuple().digits) + 1
    try:
        with localcontext() as ctx:
            ctx.prec = max(need, 28)
            ctx.Emax, ctx.Emin = decimal.MAX_EMAX, decimal.MIN_EMIN
            ctx.traps[decimal.Inexact] = True     # a silent rounding is a defect
            return a * b
    except (decimal.Overflow, decimal.Underflow, decimal.InvalidOperation,
            decimal.Inexact, ValueError) as e:
        raise SlotConversionError(
            f"{a} x {b} is not exactly representable ({type(e).__name__}) — "
            f"park, never a rounded guess")


def _exact(name, v, *, positive=False):
    """int/Decimal only — a float has already lost digits by the time we see it."""
    if isinstance(v, bool):
        raise SlotConversionError(f"{name}: bool is not a number")
    if isinstance(v, float):
        raise SlotConversionError(
            f"{name}: float rejected — parse exactly (parse_float=Decimal)")
    if not isinstance(v, (int, Decimal)):
        raise SlotConversionError(
            f"{name}: must be int/Decimal, got {type(v).__name__}")
    d = Decimal(v) if isinstance(v, int) else v
    if not d.is_finite():
        raise SlotConversionError(f"{name}: non-finite ({v})")
    if positive and d <= 0:
        raise SlotConversionError(
            f"{name}: must be a POSITIVE multiplier, got {d} — a zero or "
            f"negative scale has no reading in any filing")
    return d


def _structure(slot):
    """Shape + types only. No quote, no unit, no meaning."""
    from types import MappingProxyType
    if not isinstance(slot, (dict, MappingProxyType)):
        raise SlotConversionError(
            f"slot must be an object with {SLOT_KEYS}, got {type(slot).__name__}"
            f" — a bare number is the OLD scalar form and is rejected")
    if set(slot) != set(SLOT_KEYS):
        raise SlotConversionError(
            f"slot carries exactly {SLOT_KEYS}; got {sorted(slot)}")
    value = _exact("value", slot["value"])
    mult = _exact("scale_multiplier", slot["scale_multiplier"], positive=True)
    ev = slot["unit_scale_evidence"]
    if ev is not None and (not isinstance(ev, str) or not ev.strip()):
        raise SlotConversionError(
            "unit_scale_evidence: a non-blank verbatim span, or null")
    return value, mult, ev


def convert_slot(stated_unit, slot):
    """THE conversion. Two parameters, by design — no name, quote, qname, or raw
    text can reach it, so none of them can move a number.

    usd/count/unknown -> v x m   ·   m_usd -> v x m / 1e6   ·   ratio units keep
    the stated number (multiplier must be 1)   ·   a numberless slot is None.
    """
    if slot is None:
        return None
    value, mult, _ = _structure(slot)
    if stated_unit not in CANONICAL_UNITS:
        raise SlotConversionError(
            f"stated unit {stated_unit!r} is outside the 10-unit enum")
    required = family_required_multiplier(stated_unit)
    if required is not None:
        if mult != required:
            raise SlotConversionError(
                f"{stated_unit}: scale_multiplier must be 1 (points and basis "
                f"points are UNITS, not scales); got {mult}")
        return value
    scaled = exact_mul(value, mult)
    if stated_unit == "m_usd":
        scaled = exact_scaleb(scaled, -_MILLION_EXPONENT)
    return assert_storable(scaled)


def validate_slot(slot_name, slot, *, stated_unit, quote, lane="text"):
    """Structure + the lane's evidence law. Raises on anything unsafe.

    TEXT lane  — the evidence span must appear VERBATIM inside this fact's own
                 quote; a scale word elsewhere in the same part proves nothing
                 about THIS number, because one part may carry two different
                 scale words, so a part-wide search would attribute the wrong
                 one. (#827 finding 3: the dated corpus count that stood here
                 was an unmeasured guarantee inside runtime policy — a census
                 number belongs in a dated receipt, not in the rule. The RULE
                 does not depend on how many parts happen to do this.)
                 Evidence may be null ONLY when the multiplier is 1 and no unit
                 or scale marker exists.
    XBRL lane  — verified structured metadata (ix.scale, unit_ref,
                 source_evidence.pieces) replaces quote-local evidence: the
                 header legitimately sits OUTSIDE the row's own text.
    """
    if slot is None:
        return
    if lane not in ("text", "xbrl"):
        raise SlotConversionError(f"lane must be 'text' or 'xbrl', got {lane!r}")
    _, mult, ev = _structure(slot)
    if stated_unit is not None and stated_unit not in CANONICAL_UNITS:
        raise SlotConversionError(
            f"{slot_name}: stated unit {stated_unit!r} is outside the enum")
    if lane == "xbrl":
        return          # structured metadata is judged by the XBRL rules only
    # TEXT LANE ONLY. "a 0.01 multiplier means the source wrote cents" reads a
    # human quote. On the XBRL lane that same 0.01 IS `ix.scale = -2`, declared
    # by the filing itself, so this rule rejected lawful facts outright — an
    # `unknown` (non-USD) fact at scale -2 among them. It used to run BEFORE
    # the lane check above, which is what made it judge structured metadata.
    if mult == _CENTS and stated_unit != "usd":
        raise SlotConversionError(
            f"{slot_name}: a cents multiplier is lawful only with unit usd, "
            f"not {stated_unit!r}")
    if ev is None:
        if mult != 1:
            raise SlotConversionError(
                f"{slot_name}: multiplier {mult} with NO evidence — evidence may "
                f"be null only when the multiplier is 1 and no marker exists")
        return
    if not isinstance(quote, str) or ev not in quote:
        raise SlotConversionError(
            f"{slot_name}: unit_scale_evidence {ev!r} is not inside this fact's "
            f"quote — extend the quote to include the marker, or abstain")
    _required = family_required_multiplier(stated_unit)
    if _required is not None and mult != _required:
        raise SlotConversionError(
            f"{slot_name}: {stated_unit} requires scale_multiplier 1, got {mult}")


def check_xbrl_consistency(*, displayed, ix_scale, full_value):
    """The XBRL lane's own proof: displayed x 10^ix.scale == the full fact value.
    Both numbers exist in the filing, so double-scaling is structurally
    impossible — this equation, not a header search, is the authority."""
    d = _exact("displayed", displayed)
    full = _exact("full_value", full_value)
    scaled = exact_scaleb(d, ix_scale)          # the ONE shift — exact, or park
    if scaled != full:
        raise SlotConversionError(
            f"declared-scale mismatch: displayed {d} x 10^{ix_scale} = "
            f"{scaled}, but the fact value is {full}")
