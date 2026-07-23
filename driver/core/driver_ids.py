"""Driver fact identity — the owner-approved ID law v1.0 (2026-07-16).

Law: no escaping anywhere. Every component is delimiter-free by validated grammar;
anything illegal raises IdLawError (the caller maps it to REJECT/PARK — fail closed).
Authority: FINAL_DESIGN §5.1 (OD-8, OD-21) + the approved S3.1 paper. Pure functions, no I/O.
"""
import hashlib
import json
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

__all__ = [
    "IdLawError", "norm", "dec_canon", "num_canon", "build_id", "signature_hash",
    "member_id", "probe_forms", "encode_unknown_axis", "decode_unknown_axis",
    "valid_driver_name",
]


class IdLawError(ValueError):
    """An input violated the ID law. Never write anything built from it."""


_SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9._\-]+$")          # colon-free, case preserved
_DRIVER_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")          # NAME-05
_PERIOD_RE = re.compile(r"^gp_(ST|MT|LT|UNDEF|\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2})$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_SENTINEL_VALUE_RE = re.compile(r"^xbrlaxis_([0-9a-f]+)__([a-z0-9_]+)$")
_MEMBER_MARK = "|quote_hash="

_SLICE_KINDS = frozenset(
    {"segment", "product", "geography", "customer", "channel", "entity_ownership", "unknown"}
)
_SURPRISE_TYPES = frozenset(
    {"actual_vs_consensus", "actual_vs_guidance", "guidance_vs_consensus"}
)
# 10-slot OD-8 signature order; indexes of the numeric slots (must be pre-canonical strings)
_SIGNATURE_SLOTS = 10
_NUMERIC_SLOT_INDEXES = (0, 1, 3, 5, 6)  # level_low, level_high, change_value, comparison_low/high


def valid_driver_name(name):
    """THE one NAME-05 predicate (extracted verbatim from build_id's check —
    one law, every consumer): lowercase [a-z][a-z0-9_]*, length >= 2, no '__',
    no trailing '_'. Validation only — never cleans or normalizes."""
    return (isinstance(name, str) and len(name) >= 2
            and bool(_DRIVER_NAME_RE.fullmatch(name))   # fullmatch: $ would
            and "__" not in name and not name.endswith("_"))   # pass 'x\n'


def norm(text):
    """THE one text normalizer (slice values, measurement tokens): ASCII-fold,
    casefold, non-[a-z0-9] runs -> '_', trim/collapse. May return '' — callers reject."""
    if not isinstance(text, str):
        raise IdLawError(f"norm() needs str, got {type(text).__name__}")
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", s.casefold()).strip("_")


def dec_canon(value):
    """THE one decimal canonicalizer: plain string, no exponent, no trailing
    fractional zeros, no trailing '.', -0 -> 0. Floats are banned (formatting drift)."""
    if isinstance(value, bool) or isinstance(value, float):
        raise IdLawError(f"dec_canon() takes str/int/Decimal, got {type(value).__name__}")
    try:
        d = Decimal(str(value)) if isinstance(value, int) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise IdLawError(f"not a decimal number: {value!r}")
    if not d.is_finite():
        raise IdLawError(f"not a finite number: {value!r}")
    out = format(d, "f")
    if "." in out:
        out = out.rstrip("0").rstrip(".")
    return "0" if out in ("-0", "") else out


def num_canon(value):
    """Canonical decimal string for identity/hash use. TERMINAL numeric regime (review
    round 7): floats are REJECTED here outright — a float may have ALREADY lost source
    digits at parse time (float('1.00000000000000000001') == 1.0), and no downstream
    check can prove preservation. Numbers must arrive exact: JSON parsed with
    parse_float=Decimal (ints are exact natively); the unit resolver's float outputs
    are exact-textified at the driver_units seam. int/Decimal/str go through the strict
    dec_canon unchanged."""
    if isinstance(value, bool):
        raise IdLawError("bool is not a number")
    if isinstance(value, float):
        raise IdLawError(
            "floats are banned at identity boundaries — parse exactly "
            "(parse_float=Decimal) and convert resolver outputs at the seam")
    return dec_canon(value)


def _validate_period_id(period_id):
    m = _PERIOD_RE.fullmatch(period_id or "")
    if not m:
        raise IdLawError(f"bad period id: {period_id!r}")
    if m.group(1) in ("ST", "MT", "LT", "UNDEF"):
        return
    try:
        start, end = (date.fromisoformat(d) for d in m.group(1).split("_"))
    except ValueError:
        raise IdLawError(f"impossible calendar date in period id: {period_id!r}")
    # start == end is LEGAL: the proven instant form gp_X_X (owner amendment 2026-07-16).
    # A true DURATION input with equal dates is rejected upstream by the period resolver.
    if start > end:
        raise IdLawError(f"period start after end: {period_id!r}")


def _slice_value(kind, raw_value):
    if kind == "unknown" and _SENTINEL_VALUE_RE.fullmatch(raw_value or ""):
        return raw_value  # pre-canonical unknown-axis sentinel; structural __ preserved
    value = norm(raw_value)
    if not value:
        raise IdLawError(f"slice value normalizes to nothing: {raw_value!r} — park, never guess")
    return value


def build_id(source_id, driver_name, *, period_id=None, slice_parts=(),
             measurement_tokens=(), surprise=None):
    """The ONE entry point. Returns (fact_id, fact_scope) — both canonical, immutable.
    Lane legality of `surprise=` (surprise facts only) is FACT-16's job, not identity's."""
    if not isinstance(source_id, str) or not _SOURCE_ID_RE.fullmatch(source_id):
        raise IdLawError(f"bad source id (allowed [A-Za-z0-9._-]): {source_id!r}")
    if not valid_driver_name(driver_name):
        raise IdLawError(f"bad driver name (NAME-05): {driver_name!r}")

    slots = []
    if period_id is not None:
        _validate_period_id(period_id)
        slots.append(f"period={period_id}")
    parts = set()
    for kind, raw_value in slice_parts:
        if kind not in _SLICE_KINDS:
            raise IdLawError(f"unknown slice kind: {kind!r}")
        parts.add(f"{kind}:{_slice_value(kind, raw_value)}")
    if parts:
        slots.append("slice=" + ";".join(sorted(parts)))
    tokens = set()
    for raw in measurement_tokens:
        token = norm(raw)
        if not token:
            raise IdLawError(f"measurement token normalizes to nothing: {raw!r}")
        tokens.add(token)
    if tokens:
        slots.append("measurement=" + ",".join(sorted(tokens)))
    if surprise is not None:
        if surprise not in _SURPRISE_TYPES:
            raise IdLawError(f"bad surprise type: {surprise!r}")
        slots.append(f"surprise={surprise}")

    fact_scope = "|".join(slots)
    return f"du:{source_id}:{driver_name}:{fact_scope}", fact_scope


def signature_hash(slots):
    """OD-8: sha256 over the compact ASCII JSON array of the 10 value slots.
    Numeric slots must already be canonical decimal STRINGS (tripwired here)."""
    slots = list(slots)
    if len(slots) != _SIGNATURE_SLOTS:
        raise IdLawError(f"signature needs exactly {_SIGNATURE_SLOTS} slots, got {len(slots)}")
    for i, s in enumerate(slots):
        if s is not None and not isinstance(s, str):
            raise IdLawError(f"slot {i} must be str or None, got {type(s).__name__}")
        if i in _NUMERIC_SLOT_INDEXES and s is not None and s != dec_canon(s):
            raise IdLawError(f"slot {i} not canonical: {s!r} != {dec_canon(s)!r}")
    preimage = json.dumps(slots, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(preimage.encode("ascii")).hexdigest()


def member_id(bare_id, quote_hash):
    """The OD-8 collision-member id. Never stacks onto an existing member."""
    if _MEMBER_MARK in bare_id:
        raise IdLawError(f"already a collision member: {bare_id!r}")
    if not _HASH_RE.fullmatch(quote_hash or ""):
        raise IdLawError(f"bad quote_hash: {quote_hash!r}")
    return f"{bare_id}{_MEMBER_MARK}{quote_hash}"


def probe_forms(bare_id):
    """OD-8 sibling probe: id = exact OR id STARTS WITH prefix."""
    return bare_id, f"{bare_id}{_MEMBER_MARK}"


def encode_unknown_axis(axis_qname, member_label):
    """The complete unknown-axis slice PART: unknown:xbrlaxis_<hex of exact qname utf-8>__<norm(member)>."""
    member = norm(member_label)
    if not axis_qname or not member:
        raise IdLawError(f"cannot encode axis sentinel: {axis_qname!r} / {member_label!r}")
    return f"unknown:xbrlaxis_{axis_qname.encode('utf-8').hex()}__{member}"


def decode_unknown_axis(part):
    """Round-trip: 'unknown:xbrlaxis_<hex>__<member>' -> (exact qname, normalized member)."""
    prefix, _, value = part.partition(":")
    m = _SENTINEL_VALUE_RE.fullmatch(value if prefix == "unknown" else part)
    if not m:
        raise IdLawError(f"not an unknown-axis sentinel: {part!r}")
    return bytes.fromhex(m.group(1)).decode("utf-8"), m.group(2)
