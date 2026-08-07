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
from types import MappingProxyType

from driver.xml_names import graph_qname_parts   # THE shared XML QName owner (#827 B8)


class IdLawError(ValueError):
    """An input violated the ID law. Never write anything built from it."""


_SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9._\-]+$")          # colon-free, case preserved
_DRIVER_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")          # NAME-05
#: Internal period ids are ASCII digits; `\d` would admit every other Unicode
#: decimal digit, and the id grammar must be exactly as wide as its contract.
_PERIOD_RE = re.compile(r"^gp_([0-9]{4}-[0-9]{2}-[0-9]{2})_([0-9]{4}-[0-9]{2}-[0-9]{2})$")  # dated ids ONLY —
# sentinel membership comes from PERIOD_SENTINEL_SCOPE below, never a second alternation.
# The four-digit year is the DELIBERATELY narrow internal contract (the owner-approved
# S3.1 ID law paper), not the full XML Schema xs:date language.

#: FINAL_DESIGN §6.2 (PER-01..21): the four sentinel horizons and their two-way stored
#: invariant — short_term<->gp_ST · medium_term<->gp_MT · long_term<->gp_LT ·
#: undefined<->gp_UNDEF; "gp_UNDEF is never a quiet fallback." BUILD_AND_OPERATIONS §5
#: carries the id grammar. THIS map is the ONE production spelling of the four pairs;
#: every other module derives its view from it.
PERIOD_SENTINEL_SCOPE = {"gp_ST": "short_term", "gp_MT": "medium_term",
                         "gp_LT": "long_term", "gp_UNDEF": "undefined"}
#: THE SEC CIK LEXICAL CONTRACT — one value, consumed by Python AND by Cypher.
#: Spelled as a whole-value match on purpose: Python's `$` also matches before a
#: final newline, so "0000320193\n" would pass a `re.match` of an unanchored
#: rule. The same string is passed to Cypher as a parameter rather than restated
#: there, because a second copy is a second owner.
#:
#:   * EDGAR Filer Manual (Volume II) v77, 2026-03-16, §7.3.3.2 — "The CIK field
#:     has a field length of up to 10 digits, 1234567890", and "EDGARLink Online
#:     inserts leading zeros before your input if the value is less than the
#:     field length".
#:   * SEC EDGAR Application Programming Interfaces — the entity spelling is
#:     "the entity's 10-digit central index key (CIK), including leading zeros".
#:   * SEC "The EDGAR Log File Data Set uses the following variables",
#:     `uri_path` — the archive form is "the integer representation of the CIK
#:     (leading zeros removed for the 10 digit CIK)". That is the NODE-id
#:     spelling; this constant is the COMPANY/Context spelling.
SEC_CIK_10_PATTERN = r"^[0-9]{10}$"
#: SEC EDGAR XBRL Guide 2026-06-29 §3.1.3 — all-zero is the K.SDR/L.SDR marker
#: for an entity that is NOT an EDGAR registrant. Lexically it is ten digits, so
#: the pattern alone accepts it, and every door here names an ACTUALLY MATCHED
#: Company. Scope note: not globally illegal XBRL, refused HERE.
NON_REGISTRANT_CIK = "0000000000"
_SEC_CIK_RE = re.compile(SEC_CIK_10_PATTERN)


def graph_cik(value):
    """A CIK held OUTSIDE the filing: accept the exact stored ten-digit ASCII
    spelling, repair nothing, refuse the non-registrant marker. None otherwise.
    """
    if not isinstance(value, str) or not _SEC_CIK_RE.fullmatch(value):
        return None
    return None if value == NON_REGISTRANT_CIK else value


_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
#: FINAL_DESIGN line 174: the code-only unknown-axis sentinel is "unknown:xbrlaxis_
#: <lowercase UTF-8 hex of exact axis qname>__<normalized_member_value>". THIS prefix
#: is the reserved marker's ONE spelling; the structural regex derives its head from it.
_UNKNOWN_AXIS_VALUE_PREFIX = "xbrlaxis_"
_SENTINEL_VALUE_RE = re.compile(
    "^" + _UNKNOWN_AXIS_VALUE_PREFIX + r"([0-9a-f]+)__([a-z0-9_]+)$")
_MEMBER_MARK = "|quote_hash="

#: FINAL_DESIGN §5.2 :169-178 — the SIX slice kinds; :174 — the code-only
#: unknown sentinel kind. Each frozen spelling appears ONCE, here; the two
#: frozen sets derive and every consumer asks these names (#827 B11).
SEGMENT_KIND = "segment"
PRODUCT_KIND = "product"
GEOGRAPHY_KIND = "geography"
CUSTOMER_KIND = "customer"
CHANNEL_KIND = "channel"
ENTITY_OWNERSHIP_KIND = "entity_ownership"
UNKNOWN_SLICE_KIND = "unknown"
KNOWN_SLICE_KINDS = frozenset({SEGMENT_KIND, PRODUCT_KIND, GEOGRAPHY_KIND,
                               CUSTOMER_KIND, CHANNEL_KIND,
                               ENTITY_OWNERSHIP_KIND})
SLICE_KINDS = KNOWN_SLICE_KINDS | {UNKNOWN_SLICE_KIND}
#: FINAL_DESIGN §5.1 :152 (OD-21): the surprise= slot's three values and the pair
#: law that composes them — basis (actual|guidance) x baseline (consensus|
#: previous_guidance). THIS immutable map is the ONE production spelling of the
#: pair->scope contract; the gate vocabulary and every consumer view derive from
#: it. The fourth pair is refused by the composer with the DU-05 :108 wording.
#: The four frozen-contract tokens of that pair law (FINAL_DESIGN :152) — the ONE
#: spelling each; the map keys are built from them and every basis/baseline
#: decision (F7 tense, home suffix, CLI guide wiring, DU-05 pair, lane cell)
#: asks these names, never a fresh literal.
ACTUAL_BASIS = "actual"
GUIDANCE_BASIS = "guidance"
CONSENSUS_BASELINE = "consensus"
PREVIOUS_GUIDANCE_BASELINE = "previous_guidance"
SURPRISE_SCOPE_BY_PAIR = MappingProxyType({
    (ACTUAL_BASIS, CONSENSUS_BASELINE): "actual_vs_consensus",
    (ACTUAL_BASIS, PREVIOUS_GUIDANCE_BASELINE): "actual_vs_guidance",
    (GUIDANCE_BASIS, CONSENSUS_BASELINE): "guidance_vs_consensus",
})
_SURPRISE_TYPES = frozenset(SURPRISE_SCOPE_BY_PAIR.values())
# 10-slot OD-8 signature order; indexes of the numeric slots (must be pre-canonical strings)
_SIGNATURE_SLOTS = 10
_NUMERIC_SLOT_INDEXES = (0, 1, 3, 5, 6)  # level_low, level_high, change_value, comparison_low/high


def valid_source_id(source_id):
    """THE one source-id predicate (BUILD §5: `^[A-Za-z0-9._-]+$`, colon-free,
    case preserved). Extracted from `build_id`'s inline check so every door —
    the id builder, the run input, the event door — asks the SAME law and no
    caller copies the regex."""
    return isinstance(source_id, str) and bool(_SOURCE_ID_RE.fullmatch(source_id))


#: FINAL_DESIGN NAME-17: "terminal `_guidance` and `_surprise` stay in the
#: name and also fix permanent fact_type … Only a terminal suffix counts;
#: strip it once." These two spellings are the frozen contract values; the
#: name-grammar owner (this module) is their ONE production home.
GUIDANCE_SUFFIX = "_guidance"
SURPRISE_SUFFIX = "_surprise"
_TERMINAL_SUFFIXES = (GUIDANCE_SUFFIX, SURPRISE_SUFFIX)


def split_terminal_suffix(name):
    """NAME-17 split: (base, matched_suffix_or_None) — recognizes only the
    two frozen terminal suffixes and removes EXACTLY one."""
    for suffix in _TERMINAL_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)], suffix
    return name, None


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


def build_period_id(start_text, end_text):
    """THE one dated period-id CONSTRUCTION spelling (#827 B13) — a PURE
    CONSTRUCTOR, never a validation boundary.

    It returns the frozen S3.1 `gp_<start>_<end>` CANDIDATE and makes no
    legality decision: `parse_period_id` remains the sole grammar, calendar and
    order validator, and each caller's existing boundary judges the candidate
    exactly where it does today. The spelling lived in four callers, so the two
    halves of one grammar could drift apart; only the spelling moves here.
    Sentinels are never built — they ARE the PERIOD_SENTINEL_SCOPE constants.
    """
    return f"gp_{start_text}_{end_text}"


def parse_period_id(period_id):
    """THE one period-id parser (#827 B7). Returns (start_text, end_text) for a valid
    dated id and (None, None) for a valid sentinel; raises IdLawError for every
    non-string, malformed, impossible-calendar or reversed id. The returned values are
    the CAPTURED canonical strings after calendar validation — never date objects,
    never a second scope representation. No caller may slice a period id."""
    if not isinstance(period_id, str):
        raise IdLawError(f"period id must be a string: {period_id!r}")
    if period_id in PERIOD_SENTINEL_SCOPE:
        return None, None
    m = _PERIOD_RE.fullmatch(period_id)
    if not m:
        raise IdLawError(f"bad period id: {period_id!r}")
    start_text, end_text = m.group(1), m.group(2)
    try:
        start, end = date.fromisoformat(start_text), date.fromisoformat(end_text)
    except ValueError:
        raise IdLawError(f"impossible calendar date in period id: {period_id!r}")
    # start == end is LEGAL: the proven instant form gp_X_X (owner amendment 2026-07-16).
    # A true DURATION input with equal dates is rejected upstream by the period resolver.
    if start > end:
        raise IdLawError(f"period start after end: {period_id!r}")
    return start_text, end_text


def _slice_value(kind, raw_value):
    """THE three-state slice-value door (#827 B8, SEQ 340):
      1. ordinary unknown free text -> norm() as always (norm owns the type check);
      2. a VALID reserved `xbrlaxis_…__…` sentinel -> byte-identical;
      3. a MALFORMED attempt at the reserved code-only marker -> IdLawError — it must
         never fall through and normalize into a different value."""
    if (kind == UNKNOWN_SLICE_KIND and isinstance(raw_value, str)
            and raw_value.startswith(_UNKNOWN_AXIS_VALUE_PREFIX)):
        try:
            decode_unknown_axis(f"{UNKNOWN_SLICE_KIND}:{raw_value}")  # full sentinel grammar
        except IdLawError as e:
            raise IdLawError(
                f"malformed reserved unknown-axis sentinel: {raw_value!r}: {e} "
                f"— park, never guess") from e
        return raw_value  # pre-canonical unknown-axis sentinel; structural __ preserved
    value = norm(raw_value)
    if not value:
        raise IdLawError(f"slice value normalizes to nothing: {raw_value!r} — park, never guess")
    return value


def build_id(source_id, driver_name, *, period_id=None, slice_parts=(),
             measurement_tokens=(), surprise=None):
    """The ONE entry point. Returns (fact_id, fact_scope) — both canonical, immutable.
    Lane legality of `surprise=` (surprise facts only) is FACT-16's job, not identity's."""
    if not valid_source_id(source_id):
        raise IdLawError(f"bad source id (allowed [A-Za-z0-9._-]): {source_id!r}")
    if not valid_driver_name(driver_name):
        raise IdLawError(f"bad driver name (NAME-05): {driver_name!r}")

    slots = []
    if period_id is not None:
        parse_period_id(period_id)
        slots.append(f"period={period_id}")
    parts = set()
    for kind, raw_value in slice_parts:
        # string first: an unhashable non-string (list/dict/bytearray) must be
        # REFUSED, never crash the frozenset membership (#827 B11, SEQ 361)
        if not isinstance(kind, str) or kind not in SLICE_KINDS:
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
        # string first: an unhashable non-string (list/dict) must be REFUSED,
        # never crash the frozenset membership with TypeError (#827 B9 SEQ 351)
        if not isinstance(surprise, str) or surprise not in _SURPRISE_TYPES:
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
    """The complete unknown-axis slice PART: unknown:xbrlaxis_<hex of exact qname utf-8>__<norm(member)>.
    The axis must be a lawful stored QName — asked of THE shared XML owner
    (driver.xml_names.graph_qname_parts), never restated as a regex here."""
    if not isinstance(axis_qname, str):
        raise IdLawError(f"axis qname must be a string: {axis_qname!r}")
    if not isinstance(member_label, str):
        raise IdLawError(f"member label must be a string: {member_label!r}")
    if graph_qname_parts(axis_qname) is None:
        raise IdLawError(f"not a lawful XML QName: {axis_qname!r}")
    member = norm(member_label)
    if not member:
        raise IdLawError(f"cannot encode axis sentinel: {axis_qname!r} / {member_label!r}")
    return (f"{UNKNOWN_SLICE_KIND}:{_UNKNOWN_AXIS_VALUE_PREFIX}"
            f"{axis_qname.encode('utf-8').hex()}__{member}")


def decode_unknown_axis(part):
    """Round-trip: 'unknown:xbrlaxis_<hex>__<member>' -> (exact qname, normalized member).
    Fails CLOSED with a truthful IdLawError at every stage: type, structural form,
    hex, UTF-8, decoded QName (the shared XML owner), and member canonicality
    (equality against the one normalizer — never a second member law)."""
    if not isinstance(part, str):
        raise IdLawError(f"sentinel part must be a string: {part!r}")
    prefix, sep, value = part.partition(":")
    if not sep or prefix != UNKNOWN_SLICE_KIND:   # ONE public grammar — no bare-value path
        raise IdLawError(f"not an unknown-axis sentinel: {part!r}")
    m = _SENTINEL_VALUE_RE.fullmatch(value)
    if not m:
        raise IdLawError(f"not an unknown-axis sentinel: {part!r}")
    try:
        raw = bytes.fromhex(m.group(1))
    except ValueError:
        raise IdLawError(f"malformed lowercase UTF-8 hex in sentinel: {part!r}")
    try:
        qname = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise IdLawError(f"sentinel decoded bytes are not valid UTF-8: {part!r}")
    if graph_qname_parts(qname) is None:
        raise IdLawError(f"sentinel decodes to an unlawful QName: {qname!r}")
    member = m.group(2)
    if member != norm(member):
        raise IdLawError(f"sentinel member half is not normalized: {member!r}")
    return qname, member
