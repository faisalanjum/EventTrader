"""PreparedFact v2 — 34 total / 32 model-owned item fields.

CHANGED FROM v1, and why each field left:
  * the four unit KIND / money-mode hints and the two raw-unit strings are gone:
    the reader now states the FINAL canonical unit outright, so a hint that only
    helped code guess a unit has nothing left to do;
  * `sequential_evidence` is gone: the reader states `percent_sequential`
    directly, so a boolean asking code to infer the basis is dead weight;
  * every numeric slot is now a `{value, scale_multiplier, unit_scale_evidence}`
    object rather than a bare scalar — the scale and its proof travel WITH the
    number instead of being re-derived downstream;
  * `fact_type`, the evidence locator (`part_ref` + `occurrence_in_part`) and
    `per_x` ride at FACT level, outside the item.

WHAT THIS FILE IS, AND IS NOT (corrected after review). It is the SCHEMA and
TRANSPORT boundary: field set, types, slot-object structure, evidence
membership, and the XBRL bundle's all-or-nothing rule. It is NOT a validator.
Lane matrix, states, shapes, periods, slice kinds, value_text, conditions,
movement and OD-21 all belong to `driver_validators` / `driver_period_resolver`
and are reached through `validate_via_production` — the first draft re-wrote
several of those rules here, which is precisely the "two rule engines" mistake
this program keeps refusing everywhere else.

TWO DOORS, deliberately:
  `from_dict`            - the MODEL boundary: exactly the 32 model-owned
                           fields. The two source/code-owned XBRL fields are
                           REFUSED here, so a reply can never assert verified
                           structured evidence about itself.
  `xbrl_attach.attach_event_xbrl`
                         - the TRUSTED code path, and the ONLY public XBRL
                           door. It now lives in its own module: everything that
                           TOUCHES the graph, the filing provider or the
                           certified binder moved out of here, leaving this file
                           the schema/transport contract it says it is.

STAGED: this lands BESIDE PreparedFactV1. Nothing imports it in the live path
until the owner's atomic-switch sign-offs (Part M, O-a..O-f).
"""
from dataclasses import dataclass, field

from types import MappingProxyType

from driver.core.driver_ids import split_terminal_suffix, valid_source_id
from driver.core.slot_convert import SlotConversionError, convert_slot, validate_slot

# W15 (#827): the DECLARED export surface is exactly the retained 11 — the 8
# with production consumers + the 3 inactive clean-v2 component doors. Export
# is a distribution decision; the input-inventory coverage surface is separate
# and unchanged (split_slice_part stays covered there).
__all__ = ["SchemaError", "ProductionValidationError", "SourceUnavailable",
           "OUTCOME_CLASSES", "NUMERIC_SLOTS",
           "PreparedFactV2", "RunInputV2", "ITEM_FIELDS",
           "verify_occurrence",
           "to_stored_fact", "validate_via_production"]

_PROOF_KEYS = ("polarity", "basis", "evidence", "sentence")

SOURCE_OWNED_FIELDS = ("member_refs", "xbrl_concept_raw")

# T7 (#827): the owner is driver_validators.NUMERIC_FIELDS — this name is an
# ALIAS for the door's public surface, never a second authored copy. The
# module-level import is the card's authorized acyclic edge (validators has
# zero references back to this module).
from driver.core.driver_validators import NUMERIC_FIELDS
NUMERIC_SLOTS = NUMERIC_FIELDS


def _unit_for_slot(name, level_unit, change_unit):
    """C6 (#827 F-UNITS): THE one private slot->unit routing author — the
    expression used to be written twice identically, so the same fact could
    validate under one unit and convert under another. PRIVATE deliberately:
    a public name would be auto-inventoried by _public_input_inventory and
    needlessly expand the contract. Consumes the T7-owned field list's
    semantics (change_value is the only change-unit slot); never re-authors
    the list."""
    return change_unit if name == "change_value" else level_unit

class SchemaError(ValueError):
    """The input violates PreparedFact v2. Reject — fix and resubmit."""

class ProductionValidationError(ValueError):
    """The fact could not be PREPARED for production validation (period
    unresolvable, id unbuildable, label normalizing to nothing), or the SOURCE's
    own shape is not one this route can bind. The CLI parks on exactly these;
    callers here do the same. Resubmitting the same input changes nothing, so
    this is never a contract rejection."""


class SourceUnavailable(RuntimeError):
    """A KNOWN TEMPORARY failure reaching the graph or the filing provider —
    PARK-RETRY, which drains by itself when the dependency returns.

    Deliberately NOT a `SchemaError`: a channel must never be told to "fix and
    resubmit" because EDGAR was down. The three outcomes drive three different
    behaviours and therefore must be three different types:

        malformed input   -> SchemaError            (fix and resubmit)
        outage            -> SourceUnavailable      (park, retries itself)
        programming error -> propagates untouched   (a bug must stay loud)
    """


def _check_keys(supplied, expected, what, *, exact=True):
    """THE one key-set check. It NEVER sorts or echoes the caller's keys.

    Sorting the caller's `extra` set raised a raw `TypeError` the moment those
    keys mixed types (`{1, "zz"}`) — a crash inside the guard whose whole job is
    to prevent crashes, and it survived in three doors after being fixed in one.
    `missing` IS shown, because it is a subset of our own key list and therefore
    safely homogeneous; extras are reported by COUNT only.
    """
    have, want = set(supplied), set(expected)
    missing = sorted(want - have) if exact else []
    extra = len(have - want)
    if missing or extra:
        raise SchemaError(
            f"{what} must carry exactly {tuple(expected)}"
            + (f" — missing {missing}" if missing else "")
            + (f" — plus {extra} unexpected key(s)" if extra else ""))


def _typed(name, v, kind):
    if v is None:
        return
    if isinstance(v, bool) is not (kind is bool) or not isinstance(v, kind):
        raise SchemaError(f"{name}: must be {kind.__name__}, got {type(v).__name__}")
    if kind is str and not v.strip():
        raise SchemaError(f"{name}: blank string — use null when absent")

def split_slice_part(token):
    """`kind:value` per the locked packet law (:32). FIRST colon only, so a
    value that itself contains a colon survives intact. Kind VALIDITY is
    production's (build_id owns the frozen kind list) — this is wire format."""
    if not isinstance(token, str) or ":" not in token:
        raise SchemaError(f"slice part must be 'kind:value', got {token!r}")
    kind, value = token.split(":", 1)
    if not kind.strip() or not value.strip():
        raise SchemaError(f"slice part needs a non-blank kind and value: {token!r}")
    return kind, value

def verify_occurrence(part_text, quote, occurrence_in_part):
    """Pure string arithmetic against the named part. Returns None when the
    locator is sound, else the reason it is not.

    null iff the quote is unique in that part; otherwise 1 <= k <= count."""
    count = part_text.count(quote)
    if count == 0:
        return "quote does not occur in the named part (fabricated locator)"
    if count == 1:
        return None if occurrence_in_part is None else \
            "quote is unique in this part, so occurrence_in_part must be null"
    if occurrence_in_part is None:
        return f"quote occurs {count}x in this part — occurrence_in_part required"
    if type(occurrence_in_part) is not int:
        # EXACT int. `isinstance` admitted bool (hence the second clause this
        # replaces) and every other int subclass, which may carry any behaviour
        # it likes; a count of occurrences is an int and nothing else.
        return "occurrence_in_part must be an integer"
    if not 1 <= occurrence_in_part <= count:
        return f"occurrence_in_part {occurrence_in_part} outside 1..{count}"
    return None

def _deep_freeze(value):
    """Recursively copy into immutable form. A frozen dataclass only freezes its
    OWN attributes: the nested slot dicts stayed the CALLER'S objects, so
    mutating the input after verification changed what the fact stored — the
    390-million-to-0.000390 defect for the THIRD time, by a third route."""
    if isinstance(value, (dict, MappingProxyType)):
        return MappingProxyType({k: _deep_freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(v) for v in value)
    return value

# ONE member-ref shape rule. It was written out twice — here and in
# `_check_xbrl_bundle` — which is the same "two rule engines" duplication this
# contract exists to prevent, in miniature.
_REF_SHAPE = ("member_refs: each entry carries EXACTLY axis, member and "
              "slice_part, all non-blank strings ([] = verified-empty is legal)")


def _is_valid_ref(r):
    return (isinstance(r, (dict, MappingProxyType))
            and set(r) == {"axis", "member", "slice_part"}
            and all(isinstance(r[k], str) and r[k].strip() for k in r))




def _sha256_or_raise(value, what):
    """A representation hash is 64 lowercase hex characters — exactly. Not
    stripped: a padded hash is malformed input, the same reading applied to a
    padded element id and a padded sign."""
    from driver.core.driver_ids import sha256_hex_ok   # W4: the ONE owner
    if not sha256_hex_ok(value):
        raise SchemaError(
            f"{what}: expected a 64-character lowercase hex sha256, got "
            f"{value!r}")
    return value


# W3 (#827): the deferral mechanism is DELETED — no deferred helper
# remains; a future one must arrive with a caller, never a TODO-list slot.


def _outcome_classes():
    """THE EXHAUSTIVE outcome map: every exception this module lets escape, and
    the decision it becomes at the CLI boundary.

    Declared, not enumerated by hand at the call site — adding the fourth by
    hand is exactly how the fifth stayed hidden. A test walks the AST and fails
    if any raised-and-uncaught class is missing from here.

        rejected      the channel violated the contract; fix and resubmit
        parked        a lawful submission this route cannot bind YET; it drains
                      when the graph or the corpus catches up. Resubmitting
                      unchanged achieves nothing, so it is never a rejection.
        (unlisted)    a programming error — propagates and stays loud

    THE VALUES ARE THE FIVE PUBLIC DECISION WORDS AND NOTHING ELSE. This map
    used to answer `parked_retry` for `SourceUnavailable` — a sixth word the
    Channel Contract does not define, which would have reached the channel as
    a decision it cannot interpret. A known temporary outage IS an ordinary
    `parked`; that it retries by itself is carried by the exception CLASS and
    by the `SOURCE_UNAVAILABLE` code, never by a private decision word.
    """
    from driver.core.slot_convert import SlotConversionError
    return {SchemaError: "rejected",
            ProductionValidationError: "parked",
            SlotConversionError: "parked",
            SourceUnavailable: "parked"}


OUTCOME_CLASSES = _outcome_classes()


@dataclass(frozen=True)
class PreparedItemV2:
    """The 32 model-owned fields + the 2 source/code-owned ones.

    Validation here is SCHEMA ONLY (types, slot structure, evidence membership,
    XBRL all-or-nothing). Every judgement about lanes, states, shapes, periods,
    slices, value_text and conditions belongs to production's validator.
    """
    driver_name: str
    driver_state: str
    quote: str
    level_low: object = None
    level_high: object = None
    change_value: object = None
    comparison_low: object = None
    comparison_high: object = None
    comparison_baseline: str = None
    value_text: str = None
    conditions: str = None
    company_confirmed: bool = None
    level_unit: str = None
    change_unit: str = None
    level_shape_hint: str = None
    comparison_shape_hint: str = None
    measurement_raw_spans: list = field(default_factory=list)
    period_start_date: str = None
    period_end_date: str = None
    fiscal_year: int = None
    fiscal_quarter: int = None
    half: int = None
    month: int = None
    long_range_start_year: int = None
    long_range_end_year: int = None
    sentinel_class: str = None
    time_type: str = None
    period_scope: str = None
    slice_parts: list = field(default_factory=list)
    surprise_basis_hint: str = None
    has_favorability_wording: bool = None
    polarity_proof: dict = None
    # source/code-owned — never model input, never part of the text exam
    member_refs: list = None
    xbrl_concept_raw: str = None

    def __post_init__(self):
        # DEEP-FREEZE HERE, at the dataclass boundary — the ONE place every
        # construction path passes through. A frozen dataclass freezes only its
        # own attribute BINDINGS; the lists and dicts they point at stayed the
        # CALLER'S, so a direct `PreparedItemV2(...)` handed back an object that
        # changed when the caller edited its own inputs. Freezing in the two
        # doors instead left the direct constructor unprotected, and two freeze
        # sites is one rule with two authors.
        #
        # DERIVED from the dataclass's own fields, never a hand-listed set:
        # `_deep_freeze` returns scalars untouched, so this is safe for all of
        # them and cannot fall behind a new field.
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _deep_freeze(getattr(self, name)))
        # W9 (#827): the runtime attach SENTINEL is DELETED — the boundary is
        # proven STATICALLY instead (the alias-resolving AST node pins: one
        # constructor site, inside _build; one non-None _build caller, the
        # verified attach path; from_dict always None). A runtime token whose
        # value any reader of the source could obtain was a lock with the key
        # taped to it; the static proof has no key to steal.
        for req in ("driver_name", "driver_state", "quote"):
            v = getattr(self, req)
            if not isinstance(v, str) or not v.strip():
                raise SchemaError(f"{req}: required non-blank string")
        for k in ("comparison_baseline", "value_text", "conditions", "level_unit",
                  "change_unit", "level_shape_hint", "comparison_shape_hint",
                  "period_start_date", "period_end_date", "sentinel_class",
                  "time_type", "period_scope", "surprise_basis_hint",
                  "xbrl_concept_raw"):
            _typed(k, getattr(self, k), str)
        for k in ("fiscal_year", "fiscal_quarter", "half", "month",
                  "long_range_start_year", "long_range_end_year"):
            _typed(k, getattr(self, k), int)
        _typed("has_favorability_wording", self.has_favorability_wording, bool)
        _typed("company_confirmed", self.company_confirmed, bool)

        spans = self.measurement_raw_spans
        if not isinstance(spans, (list, tuple)) or any(
                not isinstance(s, str) or not s.strip() for s in spans):
            raise SchemaError(
                "measurement_raw_spans: list or tuple of non-blank strings "
                "([] legal)")
        parts = self.slice_parts
        if not isinstance(parts, (list, tuple)):
            raise SchemaError(
                "slice_parts: list or tuple of 'kind:value' strings "
                "([] legal)")
        for p in parts:
            if not isinstance(p, str):
                raise SchemaError(
                    f"slice_parts: each part is a 'kind:value' STRING per the "
                    f"locked packet law; got {type(p).__name__}")
            split_slice_part(p)

        self._check_xbrl_bundle()
        self._check_numeric_slots()
        self._check_proof()

    @property
    def xbrl_backed(self):
        """True only when code attached a verified XBRL bundle. Decides
        whether scale evidence must sit inside the quote: for an XBRL-backed
        fact the header legitimately lives outside the row, and the declared
        `ix.scale`/`unit_ref` metadata is the authority instead (W16: the
        text/xbrl token vocabulary is gone; the switch is this boolean)."""
        return self.xbrl_concept_raw is not None

    def _check_xbrl_bundle(self):
        """ALL-OR-NOTHING (owner 2026-07-17), restored: concept + dimensions
        ([] = verified-empty) + time_type + the exact date(s) travel together or
        not at all. A missed extraction must never masquerade as consolidated."""
        refs, concept = self.member_refs, self.xbrl_concept_raw
        if refs is None and concept is None:
            return
        if (refs is None) != (concept is None):
            raise SchemaError(
                "XBRL context is all-or-nothing: xbrl_concept_raw and member_refs "
                "([] = verified-empty) travel together")
        # THE ONE PLACE member_refs are judged. `_freeze_refs` used to do this
        # too — and wrap each ref in a MappingProxyType — which duplicated BOTH
        # the validation and the freezing the boundary now performs.
        if not isinstance(refs, (list, tuple)):
            raise SchemaError(
                f"member_refs must be a list or tuple ([] = verified-empty); "
                f"got {type(refs).__name__}")
        if any(not _is_valid_ref(r) for r in refs):
            raise SchemaError(_REF_SHAPE)
        from driver.core.slice_menu import axis_member_pairs
        if axis_member_pairs(refs) is None:
            raise SchemaError(
                "member_refs names the same axis more than once — one context "
                "carries at most one member per axis")          # THE one shape rule
        from driver.core.driver_period_resolver import PERIOD_TIME_TYPES
        if (self.time_type not in PERIOD_TIME_TYPES or not self.period_end_date
                or (self.time_type == "duration" and not self.period_start_date)):
            raise SchemaError(
                "XBRL context is all-or-nothing: needs time_type and the exact "
                "date(s) (end; start too when duration)")
        if self.time_type == "instant" and self.period_start_date is not None:
            raise SchemaError("XBRL context: an instant carries ONLY period_end_date")
        # F12 (#827): the slot-SET law, at the OWNER. An XBRL-backed fact
        # states ONE reported value: the level pair is required and every
        # other numeric slot is null. This lived only at the attach door, so
        # every OTHER v2 path skipped it (measured 2026-08-08: the owner
        # accepted level_low=None and a set change_value).
        for name in NUMERIC_SLOTS:
            slot_v = getattr(self, name)
            if name in ("level_low", "level_high"):
                if slot_v is None:
                    raise SchemaError(
                        f"an XBRL-backed fact states ONE reported value, so "
                        f"{name} is required")
            elif slot_v is not None:
                raise SchemaError(
                    f"{name} must be null on an XBRL-backed fact — the "
                    f"filing reports a single value")

    def _check_numeric_slots(self):
        xbrl_backed = self.xbrl_backed
        for name in NUMERIC_SLOTS:
            s = getattr(self, name)
            if s is None:
                continue
            unit = _unit_for_slot(name, self.level_unit, self.change_unit)
            try:
                validate_slot(name, s, stated_unit=unit, quote=self.quote,
                              xbrl_backed=xbrl_backed)
            except SlotConversionError as e:
                raise SchemaError(str(e))

    def _check_proof(self):
        proof = self.polarity_proof
        if proof is None:
            return
        if (not isinstance(proof, (dict, MappingProxyType))
                or set(proof) != set(_PROOF_KEYS)
                or any(not isinstance(proof[k], str) or not proof[k].strip()
                       for k in _PROOF_KEYS)):
            raise SchemaError(f"polarity_proof: exactly {_PROOF_KEYS}, non-blank")
        # W1 (#827): the basis enum is FROZEN product law (FINAL_DESIGN:134);
        # an invented basis is a contract violation, never a pass-through.
        if proof["basis"] not in ("source_framing", "metric_meaning"):
            raise SchemaError(
                "polarity_proof basis: source_framing | metric_meaning "
                f"(FINAL_DESIGN:134), got {proof['basis']!r}")
        # W11 (#827, owner-answered sheet row W11): the polarity token is the
        # owner's CLOSED PAIR — no third reading exists for a proof.
        if proof["polarity"] not in ("favorable", "unfavorable"):
            raise SchemaError(
                "polarity_proof polarity: favorable | unfavorable (the "
                f"owner's closed pair), got {proof['polarity']!r}")

# the 32 MODEL-owned fields: everything except the source/code-owned pair and
# any private machinery (a leading underscore is never part of the contract —
# a private machinery field once leaked in and made the count 33 until the
# arithmetic test caught it)
ITEM_FIELDS = tuple(k for k in PreparedItemV2.__dataclass_fields__
                    if k not in SOURCE_OWNED_FIELDS and not k.startswith("_"))

@dataclass(frozen=True)
class PreparedFactV2:
    """One fact: the lane, its evidence locator, its per-X signal, and the item."""
    fact_type: str
    part_ref: str
    occurrence_in_part: int
    per_x: str
    item: PreparedItemV2

    def __post_init__(self):
        # NO FREEZE LOOP HERE. Every field of this class is a scalar or the
        # already-frozen item, so the loop was a no-op — dead code pretending to
        # be a guard. The property it appeared to provide is proved instead by
        # the DERIVED class-inventory test, which walks every field of every
        # public v2 dataclass and would fail the day a mutable one is added.
        # T8: the ONE lane vocabulary, consumed FUNCTION-LOCALLY — G9's
        # one-entry-point law forbids pf2 carrying the validators' vocabulary
        # as a module attribute (a second importable home).
        from driver.core.driver_validators import LANE_STATES
        if self.fact_type not in LANE_STATES:
            raise SchemaError(f"fact_type: one of {tuple(LANE_STATES)}, "
                              f"got {self.fact_type!r}")
        if not isinstance(self.part_ref, str) or not self.part_ref.strip():
            raise SchemaError("part_ref: required — a missing locator is a "
                              "validation failure, never a fallback path")
        if self.occurrence_in_part is not None:
            if (not isinstance(self.occurrence_in_part, int)
                    or isinstance(self.occurrence_in_part, bool)
                    or self.occurrence_in_part < 1):
                raise SchemaError("occurrence_in_part: null, or a 1-based count")
        _typed("per_x", self.per_x, str)
        if not isinstance(self.item, PreparedItemV2):
            raise SchemaError("item: must be a PreparedItemV2")

    _FACT_KEYS = ("fact_type", "part_ref", "occurrence_in_part", "per_x", "item")

    @classmethod
    def _build(cls, d, verified_xbrl):
        """The shared constructor behind BOTH doors. `verified_xbrl` is either
        None (model output) or a bundle a VERIFIER has already proven."""
        if not isinstance(d, dict):
            raise SchemaError(f"fact must be an object, got {type(d).__name__}")
        # EXACT keys, not a subset: the prompt requires every field explicitly
        # present, so an OMITTED per_x or occurrence_in_part must fail rather
        # than silently become null (an omission and a stated null are
        # different claims about the source).
        _check_keys(d, cls._FACT_KEYS, "the fact-level keys")
        raw = d.get("item")
        if not isinstance(raw, dict):
            raise SchemaError("item: required object of the 32 model-owned fields")
        # W9c (#827): the source-owned PRECHECK is DELETED — proof by
        # construction: ITEM_FIELDS is derived as the dataclass fields MINUS
        # SOURCE_OWNED_FIELDS, so a source-owned key is necessarily
        # unexpected and the exact-key owner below refuses it regardless.
        _check_keys(raw, ITEM_FIELDS,
                    "the item (the 32 model-owned fields, null where absent)")
        # No freeze here: the dataclass boundary does it for EVERY path, so a
        # second call would be the same rule with two authors.
        kw = dict(raw)
        if verified_xbrl is not None:
            kw.update(verified_xbrl)
        try:
            item = PreparedItemV2(**kw)
        except TypeError as e:
            raise SchemaError(f"malformed item: {e}")
        return cls(fact_type=d["fact_type"], part_ref=d["part_ref"],
                   occurrence_in_part=d["occurrence_in_part"],
                   per_x=d["per_x"], item=item)

    @classmethod
    def from_dict(cls, d):
        """DOOR 1 — THE MODEL BOUNDARY: exactly the 32 model-owned item fields
        and exactly the 5 fact-level keys. Source-owned XBRL fields are refused,
        so a reply can never assert verified structured evidence about itself."""
        return cls._build(d, None)

@dataclass(frozen=True)
class RunInputV2:
    """One run = one stored source event + its prepared facts."""
    source_id: str
    facts: list
    calendar_override: bool = False

    def __post_init__(self):
        # VALIDATE THE INPUT FIRST, FREEZE LAST. Freezing first turned the list
        # into a tuple, so the check had to accept tuples — which silently
        # WIDENED the input contract from list-only. The tuple is a STORAGE
        # decision, never a licence to be handed one.
        if not valid_source_id(self.source_id):
            # THE one predicate (driver_ids). This ran only a non-blank-string
            # check while its own docstring claimed otherwise, so "x/y" was
            # accepted here and rejected by `build_id` much later.
            raise SchemaError("source_id is invalid")
        if not isinstance(self.calendar_override, bool):
            raise SchemaError("calendar_override: must be bool")
        if type(self.facts) is not list or any(
                not isinstance(f, PreparedFactV2) for f in self.facts):
            raise SchemaError("facts: must be a list of PreparedFactV2")
        # FACT COLLECTIONS ARE STORED AS TUPLES: `RunInputV2(facts=[])`
        # validated an empty list and the caller then appended a non-fact, so
        # the invariant just checked was FALSE on the frozen object.
        object.__setattr__(self, "facts", tuple(self.facts))   # only this one

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise SchemaError(f"run input must be an object, got {type(d).__name__}")
        _check_keys(d, ("source_id", "facts", "calendar_override"),
                    "the run input (source metadata is read from the graph, "
                    "never supplied)", exact=False)
        facts = d.get("facts")
        if not isinstance(facts, list):
            raise SchemaError("facts: required list")
        return cls(source_id=d.get("source_id"),
                   calendar_override=d.get("calendar_override", False),
                   facts=[PreparedFactV2.from_dict(f) for f in facts])

# ---------------------------------------------------------------------------
# THE BRIDGE TO PRODUCTION'S RULES. Pure data movement: the periods come from
# the production resolver, the ids from the production builder, and every
# judgement from `driver_validators.validate_fact`. No rule is restated here.
# ---------------------------------------------------------------------------

def to_stored_fact(fact, *, driver, source, fye_month, source_id=None,
                   calendar_override=False, lookups=None):
    """Map ONE PreparedFactV2 onto the stored-contract dict production
    validates. Raises ProductionValidationError where the CLI would PARK."""
    from driver.core.driver_ids import IdLawError, build_id, norm
    from driver.core.driver_period_resolver import (PERIOD_ITEM_KEYS,
                                                    PeriodResolutionError,
                                                    ensure_driver_period)
    from driver.core.driver_validators import compose_surprise_scope

    it = fact.item
    surprise = None
    if it.surprise_basis_hint is not None:
        try:
            surprise = compose_surprise_scope(it.surprise_basis_hint,
                                              it.comparison_baseline)
        except (ValueError, IdLawError) as e:
            raise ProductionValidationError(f"SURPRISE_COMPOSE: {e}")
    try:
        period = ensure_driver_period(
            {k: getattr(it, k) for k in PERIOD_ITEM_KEYS},
            fact_type=driver["fact_type"], fye_month=fye_month,
            ticker=source.get("ticker"), calendar_override=calendar_override,
            lookups=lookups)
    except PeriodResolutionError as e:
        raise ProductionValidationError(f"PERIOD_UNRESOLVED: {e}")

    values = {}
    try:
        for name in NUMERIC_SLOTS:
            unit = _unit_for_slot(name, it.level_unit, it.change_unit)
            values[name] = convert_slot(unit, getattr(it, name))
    except SlotConversionError as e:
        # `validate_slot` (at construction) checks STRUCTURE and evidence;
        # `convert_slot` does the ARITHMETIC, so an unstorable product escaped
        # here untyped. The CLI already has the code for it: NOT_STORABLE.
        raise ProductionValidationError(f"NOT_STORABLE: {e}")

    # NO surprise-state correction here, deliberately. F7 is owned by the
    # shared validator (driver_validators._actual_surprise_before_period_end,
    # reached through validate_fact on the stored `date`), so this adapter
    # carries no copy of it. The wordless beat/miss in_line correction
    # remains absent here and is the named divergence below; G9 stays gated
    # until V2 runs through the real run_event (or production extracts one
    # shared helper).

    try:
        slice_parts = [split_slice_part(p) for p in it.slice_parts]
        tokens = set()
        for s in it.measurement_raw_spans:
            token = norm(s)
            if not token:
                raise IdLawError(f"measurement span normalizes to nothing: {s!r}")
            tokens.add(token)
        fact_id, fact_scope = build_id(
            source_id or source.get("source_id"), it.driver_name,
            period_id=period["period_u_id"] if period else None,
            slice_parts=slice_parts, measurement_tokens=sorted(tokens),
            surprise=surprise)
    except IdLawError as e:
        raise ProductionValidationError(f"ID/LABEL: {e}")

    return {
        "driver_name": it.driver_name, "driver_state": it.driver_state,
        "quote": it.quote, "date": source["date"],
        "source_type": source["source_type"],
        "company_confirmed": it.company_confirmed,
        "level_low": values["level_low"], "level_high": values["level_high"],
        "level_unit": it.level_unit,
        "change_value": values["change_value"], "change_unit": it.change_unit,
        "comparison_low": values["comparison_low"],
        "comparison_high": values["comparison_high"],
        "comparison_baseline": it.comparison_baseline,
        "value_text": it.value_text, "conditions": it.conditions,
        "fiscal_year": it.fiscal_year, "fiscal_quarter": it.fiscal_quarter,
        "xbrl_qname": None,                    # enrichment-only, never from input
        "slice_parts": slice_parts, "measurement_tokens": sorted(tokens),
        "surprise_basis_hint": it.surprise_basis_hint, "surprise": surprise,
        "level_shape_hint": it.level_shape_hint,
        "comparison_shape_hint": it.comparison_shape_hint,
        "period_u_id": period["period_u_id"] if period else None,
        "period_scope": period["period_scope"] if period else None,
        "time_type": period["time_type"] if period else None,
        "gp_start_date": period["gp_start_date"] if period else None,
        "gp_end_date": period["gp_end_date"] if period else None,
        "id": fact_id, "fact_scope": fact_scope,
        # T10 (#827): the member_refs re-emission is DELETED — the clean path
        # discarded it (validate_fact never reads it); the optional legacy
        # lane builds its own dict and keeps its _ALLOWED_FIELDS door.
    }

# What the STAGED adapter still does NOT do that the real `run_event` does.

def validate_via_production(fact, *, driver, source, fye_month, home_facts=None,
                            source_id=None, calendar_override=False, lookups=None):
    """THE single validation entry point for v2 — production's own rules, run on
    a v2 fact. The scorer and `run_event` must both come through here so no
    second rule engine can ever drift into existence."""
    from driver.core.driver_validators import validate_fact
    stored = to_stored_fact(fact, driver=driver, source=source,
                            fye_month=fye_month, source_id=source_id,
                            calendar_override=calendar_override, lookups=lookups)
    return validate_fact(stored, driver=driver, home_facts=home_facts)
