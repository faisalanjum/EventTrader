"""PreparedFactV1 + RunInputV1 — the owner-locked §11.4 input schema (corrected round).

Pinned to the frozen Candidate Fact Packet (15_CandidateFactPacket.md, sha aa7239ed…)
Block 2, plus the lane transients the locked law requires the packet to carry:
per-slot unit hints (UNIT-04 effective) · surprise_basis_hint + has_favorability_wording
+ the transient polarity proof (OD-21/§4.3) · sequential_evidence (OD-11) ·
xbrl_concept_raw (transient UNIT-RESOLUTION evidence — feeds the resolver's kind/
money-mode inference; stored xbrl_qname stays enrichment-only and is NOT input). member_refs tri-state (owner Q4 amendment):
None = non-XBRL item · [] = XBRL item with VERIFIED-EMPTY dimensions · non-empty =
exact dimensions (each with axis+member+slice_part). Every non-None claim — []
included — is verified FACT-LEVEL against the current filing at step 7 (R12);
failures park MEMBER_LINK_INVALID. Validation runs in __post_init__ — EVERY
construction path rejects
floats, non-finite Decimals, blank required strings, and malformed shapes cleanly.
Changing FIELDS = a schema amendment (owner review).
"""
from dataclasses import dataclass, field
from decimal import Decimal

__all__ = ["SchemaError", "PreparedFactV1", "RunInputV1"]

_POLARITY_BASES = ("source_framing", "metric_meaning")
_PROOF_KEYS = ("polarity", "basis", "evidence", "sentence")


class SchemaError(ValueError):
    """The input violates PreparedFactV1/RunInputV1. Reject — fix and resubmit."""


def _num(name, v):
    if v is None:
        return
    if isinstance(v, bool):
        raise SchemaError(f"{name}: bool is not a number")
    if isinstance(v, float):
        raise SchemaError(f"{name}: float rejected — parse exactly (parse_float=Decimal)")
    if not isinstance(v, (int, Decimal)):
        raise SchemaError(f"{name}: must be int/Decimal, got {type(v).__name__}")
    if isinstance(v, Decimal) and not v.is_finite():
        raise SchemaError(f"{name}: non-finite Decimal rejected ({v})")


def _typed(name, v, kind):
    if v is None:
        return
    if isinstance(v, bool) is not (kind is bool) or not isinstance(v, kind):
        raise SchemaError(f"{name}: must be {kind.__name__}, got {type(v).__name__}")
    if kind is str and not v.strip():
        raise SchemaError(f"{name}: blank string — use None when absent")


@dataclass(frozen=True)
class PreparedFactV1:
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
    level_unit_raw: str = None
    change_unit_raw: str = None
    level_unit_kind_hint: str = None
    level_money_mode_hint: str = None
    change_unit_kind_hint: str = None
    change_money_mode_hint: str = None
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
    member_refs: list = None
    surprise_basis_hint: str = None
    sequential_evidence: bool = False
    has_favorability_wording: bool = None
    polarity_proof: dict = None
    xbrl_concept_raw: str = None

    FIELDS = None  # filled from the dataclass definition below (one source of truth)

    _NUMERIC = ("level_low", "level_high", "change_value",
                "comparison_low", "comparison_high")
    _STR = ("comparison_baseline", "value_text", "conditions", "level_unit_raw",
            "change_unit_raw", "level_unit_kind_hint", "level_money_mode_hint",
            "change_unit_kind_hint", "change_money_mode_hint", "level_shape_hint",
            "comparison_shape_hint", "period_start_date", "period_end_date",
            "sentinel_class", "time_type", "period_scope", "surprise_basis_hint",
            "xbrl_concept_raw")
    _INT = ("fiscal_year", "fiscal_quarter", "half", "month",
            "long_range_start_year", "long_range_end_year")

    def __post_init__(self):
        for req in ("driver_name", "driver_state", "quote"):
            v = getattr(self, req)
            if not isinstance(v, str) or not v.strip():
                raise SchemaError(f"{req}: required non-blank string")
        for k in self._NUMERIC:
            _num(k, getattr(self, k))
        for k in self._STR:
            _typed(k, getattr(self, k), str)
        for k in self._INT:
            _typed(k, getattr(self, k), int)
        _typed("company_confirmed", self.company_confirmed, bool)
        _typed("has_favorability_wording", self.has_favorability_wording, bool)
        if not isinstance(self.sequential_evidence, bool):
            raise SchemaError("sequential_evidence: must be bool")
        spans = self.measurement_raw_spans
        if not isinstance(spans, list) or any(
                not isinstance(s, str) or not s.strip() for s in spans):
            raise SchemaError("measurement_raw_spans: must be a list of non-blank strings")
        parts = self.slice_parts
        if not isinstance(parts, list) or any(
                not isinstance(p, (list, tuple)) or len(p) != 2
                or not all(isinstance(x, str) and x.strip() for x in p) for p in parts):
            raise SchemaError("slice_parts: must be a list of (kind, value) non-blank "
                              "string pairs")
        refs = self.member_refs
        if refs is not None:
            # tri-state: None = non-XBRL · [] = VERIFIED-empty dimensions · list = exact
            if not isinstance(refs, list) or any(
                    not isinstance(r, dict)
                    or set(r) != {"axis", "member", "slice_part"}
                    or not all(isinstance(r[x], str) and r[x].strip() for x in r)
                    for r in refs):
                raise SchemaError("member_refs: each entry carries EXACTLY axis, member, "
                                  "and slice_part, all non-blank strings ([] = "
                                  "verified-empty is legal)")
        # XBRL context is ALL-OR-NOTHING (owner 2026-07-17): concept + time_type + the
        # exact required date(s) + explicit dimensions ([] = verified-empty) travel
        # together or not at all. Exact dates ALONE stay legal for non-XBRL facts.
        has_concept, has_refs = self.xbrl_concept_raw is not None, refs is not None
        if has_concept or has_refs:
            if not (has_concept and has_refs):
                raise SchemaError("XBRL context is all-or-nothing: xbrl_concept_raw and "
                                  "member_refs ([] = verified-empty) travel together")
            if (self.time_type not in ("duration", "instant")
                    or not self.period_end_date
                    or (self.time_type == "duration" and not self.period_start_date)):
                raise SchemaError("XBRL context is all-or-nothing: needs time_type and "
                                  "the exact date(s) (end; start too when duration)")
            if self.time_type == "instant" and self.period_start_date is not None:
                raise SchemaError("XBRL context: an instant carries ONLY period_end_date")
        proof = self.polarity_proof
        if proof is not None:
            if (not isinstance(proof, dict) or set(proof) != set(_PROOF_KEYS)
                    or any(not isinstance(proof[k], str) or not proof[k].strip()
                           for k in _PROOF_KEYS)):
                raise SchemaError(f"polarity_proof: exactly the keys {_PROOF_KEYS}, "
                                  f"all non-blank strings")
            if proof["basis"] not in _POLARITY_BASES:
                raise SchemaError(f"polarity_proof.basis: must be one of "
                                  f"{_POLARITY_BASES}, got {proof['basis']!r}")
            if proof["polarity"] not in ("higher_favorable", "lower_favorable"):
                raise SchemaError(f"polarity_proof.polarity: exactly higher_favorable "
                                  f"or lower_favorable, got {proof['polarity']!r}")

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise SchemaError(f"fact must be an object, got {type(d).__name__}")
        unknown = set(d) - set(cls.FIELDS)
        if unknown:
            raise SchemaError(f"unknown field(s): {sorted(unknown)} — the CLI builds "
                              f"ids/scopes; stored enrichment fields are never input")
        kw = dict(d)
        if isinstance(kw.get("slice_parts"), list):
            kw["slice_parts"] = [tuple(p) if isinstance(p, list) else p
                                 for p in kw["slice_parts"]]
        try:
            return cls(**kw)
        except TypeError as e:
            raise SchemaError(f"malformed fact: {e}")


PreparedFactV1.FIELDS = tuple(PreparedFactV1.__dataclass_fields__)


@dataclass(frozen=True)
class RunInputV1:
    """One run = one stored source event + its prepared facts."""
    source_id: str
    facts: list
    calendar_override: bool = False

    def __post_init__(self):
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise SchemaError("source_id: required non-blank string")
        if not isinstance(self.calendar_override, bool):
            raise SchemaError("calendar_override: must be bool")
        if not isinstance(self.facts, list) or any(
                not isinstance(f, PreparedFactV1) for f in self.facts):
            raise SchemaError("facts: must be a list of PreparedFactV1")

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise SchemaError(f"run input must be an object, got {type(d).__name__}")
        unknown = set(d) - {"source_id", "facts", "calendar_override"}
        if unknown:
            raise SchemaError(f"unknown field(s): {sorted(unknown)} — source metadata "
                              f"is read from Neo4j, never duplicated in input")
        facts = d.get("facts")
        if not isinstance(facts, list):
            raise SchemaError("facts: required list")
        return cls(source_id=d.get("source_id"),
                   calendar_override=d.get("calendar_override", False),
                   facts=[PreparedFactV1.from_dict(f) for f in facts])
