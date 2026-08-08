"""XBRL attachment — the ONE public door from a source event to verified facts.

MOVED here from `prepared_fact_v2`, which had grown to mix four jobs: the
schema/transport contract, event I/O, filing binding, and outcome handling. The
schema stayed there; everything that TOUCHES the graph, the filing provider or
the certified Route-A binder lives here. This was a MOVE, not a new layer — no
rule was rewritten, nothing was duplicated, and no compatibility wrapper was
left behind, so there is exactly one place each rule can be read.

THE PUBLIC SURFACE IS ONE FUNCTION: `attach_event_xbrl`. The per-item binder and
the representation-agreement helper are private, so the event-level guard (one
source event = one XBRL representation) cannot be bypassed.

ONE SET OF READS PER EVENT: the representation count, the filing fetch, the
parse+hash and the company CIK happen ONCE, and rows are read once per DISTINCT
concept into event-local state. Four facts used to cost four of each.
"""
from collections import namedtuple as _namedtuple
from types import MappingProxyType

from driver.core.driver_ids import valid_source_id
from driver.core.prepared_fact_v2 import (OUTCOME_CLASSES, PreparedFactV2,
                                          ProductionValidationError, SchemaError,
                                          SourceUnavailable,
                                          NUMERIC_SLOTS, _deep_freeze,
                                          _sha256_or_raise, verify_occurrence)
from driver.core.slot_convert import MULTIPLIER_ONE_UNITS, SlotConversionError
from driver.relocation.exact_numbers import (ISO_4217_NAMESPACE,
                                             ROUTE_A_BOOLS,
                                             XBRL_INSTANCE_NAMESPACE, XML_WS)
from driver.relocation.inline_html import (PIECE_KEYS, PIECE_KINDS,
                                           SOURCE_EVIDENCE_KEYS, parse_raw,
                                           prepare, refused, source_evidence)
from driver.xml_names import graph_qname_parts

# F1 (#827): the public surface is the ONE required door — the two extra
# exports had zero non-proof importers (measured).
__all__ = ["attach_event_xbrl"]


# The EXPLICIT retryable set. Never a bare `except Exception`: swallowing an
# AttributeError from our own code as "temporary" would hide the bug forever.
#
# OSError covers ConnectionError and TimeoutError, which is every transport
# failure a filing provider can raise. It deliberately does NOT name Neo4j's
# transient classes: importing the driver here would let this staged contract
# module reach the graph package, which the G18 gate exists to disprove — and
# it did fire on exactly that. INSTEAD, per the injected-dependency contract, a
# store implementation maps ITS OWN transient failures to `SourceUnavailable`
# (or an OSError) before they cross this boundary. An unmapped driver error is
# then an unexpected error and fails loudly, which is the safe direction.
RETRYABLE_SOURCE_ERRORS = (OSError,)
# F2 (#827, fail closed): these OSError SUBCLASSES are PERMANENT — a wrong
# path or permission never heals by waiting, so retry-forever was the unsafe
# direction. They fail LOUDLY through; only the owner below classifies.
NON_RETRYABLE_SOURCE_ERRORS = (PermissionError, FileNotFoundError)


def _fetch(what, call, *args):
    """Call a code-owned dependency, mapping ONLY a known outage to PARK-RETRY."""
    try:
        return call(*args)
    except SourceUnavailable:
        raise                                # a store already classified it
    except NON_RETRYABLE_SOURCE_ERRORS:
        raise                                # F2: permanent — never retried
    except RETRYABLE_SOURCE_ERRORS as e:
        raise SourceUnavailable(
            f"{what} is temporarily unavailable ({type(e).__name__}: {e}) — "
            f"park and retry; this is not a contract violation") from e

# What the verifier REQUIRES from a filing row. A row missing any of them is not
# permission to trust the caller — it is a PARK. `fact_id` is the SHORT inline
# element id: it is the join key to the filing's own rendering, and without it
# no evidence can be bound at all.
# The key must be PRESENT on every row (a missing column is a broken reader);
# `fact_id` may lawfully be BLANK, and the law routes exactly those to the
# identity fallback (FinalPlan 5A step 3). Core used to reject them before the
# fallback it had just built could run.
#
# MEASUREMENTS, each with its date and its scope — they disagree, and both stand:
#   2026-07-21 (FinalPlan): 3,332 blank short ids WITHIN THE CACHED M3
#              POPULATION; 34,277 graph-wide.
#   2026-07-27 (this census): 0 null and 0 blank across ALL 13,775,616 Fact
#              nodes, while the numeric non-nil count is UNCHANGED at
#              12,402,201 — no new facts arrived, so the graph appears to have
#              been BACKFILLED. Not a refutation of the older figure: the two
#              were taken at different times.
# The branch therefore stays (it is the law), but no live fact exercises it today.
_REQUIRED_ROW_KEYS = ("fact_id", "value", "unit_ref", "unit_name", "is_divide",
                      "context_id", "concept_namespace", "graph_concept_qname")
# The period/dimension fields binding ALSO reads — through `match_xbrl_fact` and
# the binder call, neither of which the list above covered. The complete read set
# is the UNION below, so no field name is written twice and there is no second
# hand-maintained list to drift out of step with the first.
_ROW_SHAPE_KEYS = ("period_type", "start_date", "end_date", "dims")
_ROW_FIELDS = _REQUIRED_ROW_KEYS + _ROW_SHAPE_KEYS
# XBRL defines exactly two period types, and the live graph carries exactly
# those two (8,358 duration + 3,058 instant, verified 2026-07-27) — spec-derived,
# census-confirmed. A third value is a shape we cannot bind, so it parks.
_PERIOD_TYPES = ("duration", "instant")
#: THE TWO NAMESPACE FIELDS ARE REQUIRED, not optional. A dimension is
#: (namespace URI, local name); the qname alone is a prefixed alias that cannot
#: say WHICH taxonomy an axis belongs to, and two taxonomies routinely spell the
#: same local name. A reader that cannot supply both halves is a broken reader,
#: so its rows park here rather than binding on the spelling.
_DIM_KEYS = ("axis", "member", "label", "axis_namespace", "member_namespace")
_REQUIRED_NON_BLANK = ("value", "unit_ref", "unit_name", "is_divide", "context_id",
                       "period_type", "start_date",
                       # THE CONCEPT'S IDENTITY IS REQUIRED AT THIS BOUNDARY,
                       # not optional and not defaulted. The binder compares
                       # (namespace URI, local name) and refuses without it, so
                       # a reader that cannot supply both is a broken reader —
                       # an ordinary park here, never a silent None that would
                       # make every lawful fact look unbindable.
                       "concept_namespace", "graph_concept_qname")


def _row_expanded_dims(row):
    """The row's dimensions as EXPANDED NAMES — the only thing the binder
    compares. Returns a tuple, or RAISES; it never returns None.

    NEVER `None`, by construction. It used to, and the caller passed that
    straight into a parameter the binder reads as `dims or ()` — so the least
    readable input, a row whose identity cannot be stated at all, produced the
    most permissive answer: the fact attached as though it were dimensionless.
    Raising here makes that fail-open impossible rather than guarded against.

    TWO DISTINCT FAILURES, said apart, because they need different fixes:
    an axis or member whose identity is unusable is a broken READER; one
    expanded axis appearing twice is a malformed CONTEXT.

    Derived from the two halves the checked row already carries — the qname,
    split by the shared `graph_qname_parts` owner so the grammar is not
    restated, and the namespace the adapter decoded. Nothing is parsed twice
    and no prefix is interpreted.
    """
    out = []
    for d in row["dims"]:
        axis, member = graph_qname_parts(d["axis"]), graph_qname_parts(d["member"])
        if axis is None or member is None:
            raise ProductionValidationError(
                f"the graph cannot state this row's dimension identity: "
                f"{d['axis']!r} / {d['member']!r} is not a QName — park")
        # NO COERCION. `_checked_row` already required every `_DIM_KEYS` value
        # to be an exact non-blank string, so wrapping these in `str()` would
        # only hide a shape that has already been refused upstream.
        out.append(((d["axis_namespace"], axis),
                    (d["member_namespace"], member)))
    # ONE VALUE PER DIMENSION — XBRL Dimensions 1.0 §3.1.4.2 — judged on the
    # EXPANDED axis. This subsumes the raw-spelling uniqueness rule that used to
    # sit in `_checked_row`: it catches the same-spelling repeat AND the alias
    # repeat that spelling could not see, and because it now runs BEFORE
    # matching it can say so at the same boundary, in its own words.
    if len({axis for axis, _member in out}) != len(out):
        raise ProductionValidationError(
            "the row names the same dimension more than once — one context "
            "carries at most one member per axis (XBRL Dimensions 1.0 "
            "§3.1.4.2) — park")
    return tuple(sorted(out))


def _row_signature(row):
    """THE conflict identity of a checked row.

    DERIVED from `_ROW_FIELDS` — the same union that says what binding reads —
    so a new row field cannot be silently left out of it. The previous signature
    named six fields by hand and omitted BOTH the period and the dimensions, so
    two rows differing only in a dimension LABEL looked identical, collapsed,
    and the winner was decided by whichever the reader returned first: [Foo,
    Bar] accepted, [Bar, Foo] rejected.

    Dimensions are rendered SORTED, because two readings of one fact that list
    the same dimensions in a different order are the same fact, not a conflict.
    """
    # LAWFUL FORMS, never raw text. Comparing raw values made two spellings of
    # ONE fact read as a conflict, which is the same order-dependence in the
    # other direction. Each normalisation below is justified by what BINDING
    # itself does with that field — nothing here is a new rule.
    parsed = parse_raw(row["value"])
    out = []
    for field in _ROW_FIELDS:
        if field == "dims":
            # DERIVED FROM `_DIM_KEYS`, exactly as the outer loop derives from
            # `_ROW_FIELDS`, and for the same reason: a hand-written field list
            # silently omits whatever is added next.
            #
            # It did. This said `(axis, member, label)` while the binder had
            # started reading the two namespace fields, so two rows differing
            # ONLY in `axis_namespace` collapsed to one signature — and then
            # ROW ORDER decided the outcome: [correct, wrong] attached a fact,
            # [wrong, correct] refused it. An order-dependent answer is the same
            # defect class as the dimension-LABEL collapse this function was
            # written to fix.
            out.append(tuple(sorted(tuple(d[k] for k in _DIM_KEYS)
                                    for d in row["dims"])))
        elif field == "fact_id":
            # BLANKNESS IS ALL THAT STRIPPING MAY DECIDE. `bind_graph_fact`
            # picks its path on `(id or "").strip()` — so null, empty and
            # whitespace are ONE claim, "this element carries no id" — but it
            # then looks the id up EXACTLY as stored, because a padded or
            # re-cased id is a DIFFERENT id, not a typo to repair.
            # Stripping here too folded `f1` and ` f1` into one identity while
            # they bound to DIFFERENT elements, so WHICH of them survived the
            # fold depended on the order the graph returned the rows in.
            # XML 1.0 S, the same set the binder's door uses. A bare
            # `.strip()` also eats U+000B, U+000C, U+00A0 and U+3000, so an id
            # made only of those folded into the SAME identity as "no id at
            # all" — two different claims about the filing collapsed into one.
            raw_id = row["fact_id"] or ""
            out.append("" if not raw_id.strip(XML_WS) else raw_id)
        elif field == "value":
            # `parse_raw` is the certified reader (the frozen canonical
            # graph lexical contract):
            # "0" and "-0" are the same number (the one two-spelling pair
            # the frozen lexical contract lawfully stores — SEQ 268; an
            # ungrouped "726000000" is outside the contract entirely). A
            # value it cannot read keeps its RAW text, so two different
            # unreadable strings never collapse into one.
            out.append(parsed if parsed is not None else ("unparsed", row["value"]))
        elif field == "end_date" and row["period_type"] == "instant":
            # UNREAD on this branch — `match_xbrl_fact` compares only
            # `start_date` for an instant, and the graph stores the literal
            # string "null" here in all 3,058 of them. A field nobody reads
            # cannot be part of the fact's identity.
            out.append(None)
        else:
            out.append(row[field])
    return tuple(out)


def _checked_row(raw):
    """ONE checked, immutable record per external graph row, built IMMEDIATELY
    after the read and before any consumer can touch it.

    WHY THIS EXISTS: the row's period and dimension fields were read by
    `match_xbrl_fact` BEFORE anything checked them, so a row missing a column
    escaped as a raw `KeyError`, and a mis-typed `dims` as a raw `TypeError`.
    Those are the signal reserved for OUR OWN bugs. A row we cannot read is a
    DATA SHAPE this route cannot bind — an ordinary park, which drains when the
    corpus catches up and which no channel can fix by resubmitting.

    `fact_id` may lawfully be BLANK (the identity fallback exists for exactly
    that); its KEY must still be present, because a missing column is a broken
    reader. `end_date` is read only on the duration branch, so it is required
    non-blank only there — demanding it everywhere would park lawful instants.
    """
    if type(raw) is not dict and not isinstance(raw, MappingProxyType):
        raise ProductionValidationError(
            f"the graph row is {type(raw).__name__}, not a mapping — park")
    absent = [k for k in _ROW_FIELDS if k not in raw]
    if absent:
        raise ProductionValidationError(
            f"the filing row has no {absent} column — a missing field is a PARK, "
            f"never permission to trust the caller")
    # EXACT STRING FORMS. Checking only `str(v).strip()` accepted an int, float,
    # bool, list, dict or Decimal in EVERY scalar — and an integer
    # `value=726000000` attached, though the graph stores values as STRINGS
    # WITH COMMAS ("4,824,698,000", verified live 2026-07-27), which is the
    # whole reason `parse_raw` exists. It also silently re-opened aliasing: a
    # list `value` stayed the CALLER'S object inside the "immutable" row.
    # Requiring the exact string form fixes both at once — a str cannot alias.
    for k in _REQUIRED_NON_BLANK:
        v = raw[k]
        if type(v) is not str or not v.strip():
            raise ProductionValidationError(
                f"row field {k!r} must be a non-blank string (the graph stores "
                f"it as one), got {type(v).__name__} — park")
    if raw["period_type"] not in _PERIOD_TYPES:
        raise ProductionValidationError(
            f"row period_type {raw['period_type']!r} is not one of "
            f"{_PERIOD_TYPES} — park")
    if raw["is_divide"] not in ROUTE_A_BOOLS:      # THE existing flag authority
        raise ProductionValidationError(
            f"row is_divide {raw['is_divide']!r} is not one of the graph's own "
            f"boolean spellings — park")
    # THE TWO LAWFUL OPTIONAL FORMS.
    #   fact_id  — null or blank means "this element carries no id", which the
    #              identity fallback exists to serve.
    #   end_date — meaningless on an instant. The graph stores the LITERAL
    #              four-character string "null" there (3,058 of 3,058 instants,
    #              verified live 2026-07-27), and a real None is accepted too;
    #              it is required non-blank only on the duration branch, which
    #              is the only branch that reads it.
    for k in ("fact_id", "end_date"):
        if raw[k] is not None and type(raw[k]) is not str:
            raise ProductionValidationError(
                f"row field {k!r} must be a string or null, got "
                f"{type(raw[k]).__name__} — park")
    if raw["period_type"] == "duration" and not (raw["end_date"] or "").strip():
        raise ProductionValidationError(
            "a duration row needs its end_date — park")
    # DATE SHAPES, judged HERE rather than left to a later string comparison
    # that would simply fail to match. `_iso_date` is the ONE strict parser.
    from driver.relocation.exact_numbers import ExactError, _iso_date
    for field in ("start_date", "end_date"):
        value = raw[field]
        if value is None:
            continue
        if field == "end_date" and raw["period_type"] == "instant":
            # UNREAD on this branch, but not therefore unconstrained: skipping
            # the check entirely let ANY text through. Census 2026-07-28: every
            # stored end_date is a strict ISO date (8,358) or the literal
            # four-character string "null" (3,058) — 11,416 exactly, so there is
            # no third shape and arbitrary text is not one of them.
            if value == "null":
                continue
            # NOT a real date either: all 3,058 live instants carry the literal
            # "null" and not one carries a date, so allowing one would invent a
            # shape the graph does not have. The lawful set is exactly two.
            raise ProductionValidationError(
                f"an instant's end_date is the literal \"null\" or absent; "
                f"got {value!r} — park")
        try:
            _iso_date(value)
        except ExactError as e:
            raise ProductionValidationError(f"row {field}: {e} — park")
    dims = raw["dims"]
    if type(dims) not in (list, tuple):
        raise ProductionValidationError(
            f"the row's dims is {type(dims).__name__}, not a list "
            f"([] = genuinely dimensionless) — park")
    checked = []
    for d in dims:
        if (type(d) is not dict and not isinstance(d, MappingProxyType)) \
                or set(d) != set(_DIM_KEYS):
            raise ProductionValidationError(
                f"each row dimension carries exactly {_DIM_KEYS} — park")
        if any(type(d[k]) is not str or not d[k].strip() for k in _DIM_KEYS):
            # The label is not decoration: `check_member_refs` RECOMPUTES the
            # slice token from it, so a null or non-string label can verify
            # nothing. Zero of 1,499,049 Members carry a null label (verified
            # live 2026-07-27), so this costs no recall today and an unseen
            # shape parks rather than being guessed at.
            raise ProductionValidationError(
                f"a row dimension's {_DIM_KEYS} must all be non-blank strings "
                f"— park")
        checked.append(MappingProxyType({k: d[k] for k in _DIM_KEYS}))
    # THE RAW DUPLICATE-AXIS CHECK IS GONE FROM HERE, and its removal is earned
    # rather than assumed. Its `axis_member_pairs` import went with it: an
    # import kept "in case" is how a deleted rule quietly comes back.
    #
    # I argued for keeping it: with the old ordering, deleting it degraded the
    # REASON — `match_xbrl_fact` ran first, so a repeated axis fell out as "no
    # row matched", reported as ordinary graph lag. That objection was about the
    # ORDER, not the rule. `_row_expanded_dims` now runs BEFORE any matching and
    # raises its own truthful detail (§3.1.4.2, named), so the good reason
    # exists at the right boundary and this one is a second copy of it —
    # weaker, because it compares spellings and cannot see two prefixes bound
    # to one URI.
    #
    # `axis_member_pairs` keeps its own guard for its OTHER callers; what is
    # deleted is this duplicate claim, not that function.
    # ONLY the checked fields travel on. `decimals` and any other extra the
    # reader happens to carry is dropped rather than passed through unchecked.
    return MappingProxyType({**{k: raw[k] for k in _ROW_FIELDS},
                             "dims": tuple(checked)})

# The only unit the money lane is PROVEN against. `unit_ref` is a bare pointer
# ("usd"); the authority is the linked Unit node's own name, and `is_divide`
# distinguishes a plain currency from a per-something ratio unit.
# ---------------------------------------------------------------------------
# THE CANDIDATE-UNIT POLICY (#827 blocker 8). It lived in the SHARED Route-A
# binder module, but the production caller census says it is Core's alone:
# exactly one non-test caller, here. Policy belongs with the component that
# applies it — the shared binder verifies the filing's unit and reports it,
# and a test pins that it applies no candidate policy of its own.
# ---------------------------------------------------------------------------
#: THE TWO NAMESPACES THIS POLICY KNOWS, by URI and never by prefix.
#: `iso4217` is a prefix a filing chooses; a filing may bind it to anything,
#: and may declare the currency namespace under any other name. Identity is
#: (namespace URI, local name) — Namespaces in XML 1.0 Third Edition
#: (W3C Rec 2009-12-08) §3.
#:   ISO-4217 currencies : XBRL 2.1 (Rec 2003-12-31 + errata 2013-02-20) §4.8.2
#:   shares / pure       : the XBRL 2.1 instance namespace, §1.6
#: The URI values live at their ONE owner,
#: `exact_numbers.ISO_4217_NAMESPACE` / `XBRL_INSTANCE_NAMESPACE`.

#: KEYED ON EXPANDED NAMES. The keys were the graph's stored SPELLINGS, which
#: are Arelle's `stringValue` and therefore carry the filing's own prefix
#: (`XBRL/xbrl_basic_nodes.py:178,257`). Measured on that: a filing binding
#: `iso4217` to an unrelated URI was granted US-dollar units, and a filing
#: declaring the real currency namespace under any other prefix was granted
#: none at all. Both bound cleanly — only this table was wrong.
#: Keyed by the EXPANDED NAME ALONE. The old `is_divide` half of the key was
#: dead weight: a divide unit never reaches this table — its numerator carries
#: the currency and the denominator is the per-X — so the flag only ever held
#: one value here.
_CANDIDATE_EXACT = {
    (ISO_4217_NAMESPACE, 'USD'): frozenset({'usd', 'm_usd'}),
    (XBRL_INSTANCE_NAMESPACE, 'shares'): frozenset({'count'}),
    # `unknown` is the EXISTING fail-safe — the source genuinely may not
    # distinguish a rate from a count from a ratio.
    #
    # DERIVED FROM THE ONE OWNER, not restated. A local `_PERCENT_FAMILY` tuple
    # listed the same five units that `slot_convert.MULTIPLIER_ONE_UNITS`
    # already owns (verified equal once `x` is included, which that owner also
    # carries) — two spellings of one set, and the second was free to drift.
    (XBRL_INSTANCE_NAMESPACE, 'pure'):
        frozenset({'count', 'unknown'} | set(MULTIPLIER_ONE_UNITS)),
}

_UNKNOWN = frozenset({'unknown'})


def candidate_units_for(measures_expanded, numerator_expanded):
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
    # THE DIVIDE BRANCH IS STRUCTURAL, not a flag anyone passes. The binder
    # fills the numerator for a divide unit and the plain measures for a simple
    # one, never both, so the shape of the verified evidence already says which
    # kind it is. Asking a caller to also state it would invite the two to
    # disagree, and a caller-supplied boolean is exactly the sort of input this
    # audit keeps finding wired to nothing.
    numerator = list(numerator_expanded)
    if numerator:
        if len(numerator) != 1:
            return frozenset()          # unreadable shape -> park, never guess
        namespace, local = numerator[0]
        if namespace != ISO_4217_NAMESPACE:
            return frozenset()          # utr:gal/utr:M — not money at all
        # base unit; the per-X is in the name. Any other official currency is
        # money we do not canonicalise, and `unknown` is the honest carrier.
        return frozenset({'usd'}) if local == 'USD' else _UNKNOWN
    measures = list(measures_expanded)
    if len(measures) != 1:
        return frozenset()
    if measures[0] in _CANDIDATE_EXACT:
        return _CANDIDATE_EXACT[measures[0]]
    if measures[0][0] == ISO_4217_NAMESPACE:
        return _UNKNOWN
    return frozenset()


def expected_multiplier(level_unit, ix_scale):
    """The multiplier a fact must state, given its unit and the filing's scale.

    ix.scale is NOT copied blindly (owner ruling 2026-07-27). It VERIFIES the
    graph value — the CE filing prints 2.6 with scale -2 and the graph holds
    0.026 — but the stored percentage is 2.6 with multiplier ONE. Points and
    basis points are UNITS, never scales, so `convert_slot` already requires 1
    for the whole family; copying 10^-2 in would have made every percent fact
    fail its own unit law. Money and count take the source's real magnitude.
    """
    from decimal import Decimal
    from driver.core.slot_convert import (assert_storable, exact_scaleb,
                                          family_required_multiplier)
    required = family_required_multiplier(level_unit)
    if required is not None:
        return required            # the family never touches the arithmetic
    # TWO boundaries, both parking on the ALREADY-DECLARED outcome:
    #   arithmetic  — beyond Emax the shift is not representable at all;
    #   storability — 10^1000000 IS representable but needs 1,000,001 characters
    #                 in canonical stored form, so it can never be written.
    # `assert_storable` is the existing owner of that bound; no new threshold.
    return assert_storable(exact_scaleb(Decimal(1), ix_scale))


def _one_representation_for_event(hashes):
    """ONE source event = ONE XBRL REPRESENTATION GROUP.

    NOT one document: a single 8-K event lawfully carries its body AND its
    exhibits. What every XBRL item of a submission must agree on is the
    representation its facts were tagged in — a disagreement means the items
    describe different representations, which one binding cannot span.
    Missing, malformed or conflicting evidence is a CONTRACT REJECTION for the
    whole submission — `SchemaError`, fix and resubmit — not a park. The
    channel supplied it and the channel can correct it; nothing here waits on
    the graph or the filing, which is what a park is for.
    """
    values = list(hashes)
    # F1 (#827): TWO dead defences deleted here (checkpoint fd221239 +
    # 2b8fd679) — the empty-values branch was unreachable (the only
    # production caller passes nonempty `checked`), and the per-hash sha
    # re-validation duplicated _checked_source_evidence, which every
    # evidence object has already passed.
    if len(set(values)) != 1:
        raise SchemaError(
            f"the event's XBRL items declare {len(set(values))} different "
            f"representations; one binding cannot span them — reject and "
            f"resubmit")
    return values[0]


_EVENT_ITEM_KEYS = ("fact", "concept", "member_refs", "source_evidence")

_TEXT_PART_KEYS = ("part", "content")

# ONE immutable event result. `source_id` travels WITH the facts so the writer
# can ASSERT the two match at handoff. That assertion is what prevents a
# mismatched pairing; carrying the id only makes it possible, and nothing here
# stops a caller separating them before the switch adds that check.
AttachResult = _namedtuple("AttachResult", ("source_id", "facts",
                                            "preflight_outcomes",
                                            "member_menu"))

# ONE internal item result: the verified fact OR a declared item-local
# decision, PLUS that member check's own notes and logs. It exists so evidence
# already produced SURVIVES a later numeric or finalization failure. The two
# alternatives were hanging logs on exception objects and threading a mutable
# accumulator through the binder; both were refused, and both would have made
# the audit a side effect instead of a return value.
_ItemResult = _namedtuple("_ItemResult",
                          ("fact", "exc", "code", "notes", "logs"))

# THE FIVE PUBLIC DECISION WORDS, and no others. `parked_retry` was a retired
# DECISION STRING, not a class: the class is `SourceUnavailable`, and it is the
# class plus the SOURCE_UNAVAILABLE code that tell Core the park auto-retries.
PUBLIC_DECISIONS = ("written", "merged", "parked", "skipped", "rejected")

# The declared item-local outcomes, taken DIRECTLY from the ONE outcome map so
# a fifth class cannot be added there and silently escape here.
OUTCOME_ITEM_CLASSES = tuple(OUTCOME_CLASSES)

# CODES ONLY — defaults for an XBRL branch that owns no more specific code. A
# branch that already has one (MEMBER_LINK_INVALID, SOURCE_COMPANY_AMBIGUOUS)
# keeps it, and nothing here reads an exception MESSAGE to choose.
#
# THE DECISION IS NOT WRITTEN HERE. It has exactly one owner, `OUTCOME_CLASSES`,
# and is looked up from it below. Writing the decision beside the code gave the
# class-to-decision rule two homes that agreed only by coincidence.
_DEFAULT_CODES = ((SlotConversionError, "NOT_STORABLE"),
                  (SourceUnavailable, "SOURCE_UNAVAILABLE"),
                  (SchemaError, "XBRL_CONTRACT_INVALID"),
                  (ProductionValidationError, "XBRL_BINDING_UNAVAILABLE"))


def _default_outcome(exc):
    """(decision, code) for a declared item-local failure, chosen by CLASS."""
    for cls, code in _DEFAULT_CODES:
        if isinstance(exc, cls):
            return OUTCOME_CLASSES[cls], code
    raise exc                      # unlisted == a programming error: stay loud


def _outcome_row(index, exc, code=None):
    """The CLI's exact five fields, frozen. Not the writer's private helper —
    that stays the sole serializer, and this is deleted at the switch.

    THE DECISION IS NEVER PASSED IN. It is derived from `OUTCOME_CLASSES` here,
    always — there is no parameter a caller could use to write a different one.
    A branch may override ONLY its specific code. `fact_id` is not a parameter
    either: until a real Driver fact id exists there is nothing lawful to put
    there, and a parameter would invite `part_ref` back.
    """
    decision, default_code = _default_outcome(exc)
    if code is None:
        code = default_code
    if decision not in PUBLIC_DECISIONS:
        # AN EXPLICIT CHECK, not an `assert`: `python -O` strips asserts, and
        # this one is the last thing standing between an internal slip and a
        # decision word the channel cannot interpret.
        raise RuntimeError(
            f"attach_event_xbrl: {decision!r} is not one of the public "
            f"decisions {PUBLIC_DECISIONS} — internal error")
    return MappingProxyType({"index": index, "fact_id": None,
                             "decision": decision, "codes": (code,),
                             "detail": str(exc)})


def _exact_span(value, what):
    """Two exact integers, 0 <= start < end.

    `bool` IS an int subclass, and any other int subclass may carry whatever
    behaviour it likes; a character offset is an `int` and nothing else. The
    result is a TUPLE, so nothing downstream holds the caller's list.
    """
    if type(value) not in (list, tuple) or len(value) != 2:
        raise SchemaError(
            f"attach_event_xbrl: {what} must be exactly [start, end]")
    start, end = value
    if type(start) is not int or type(end) is not int:
        raise SchemaError(
            f"attach_event_xbrl: {what} endpoints must be exact integers")
    if not 0 <= start < end:
        raise SchemaError(
            f"attach_event_xbrl: {what} must satisfy 0 <= start < end, "
            f"got {value!r}")
    return (start, end)


def _checked_source_evidence(value):
    """The channel's filing-side claim, judged on SHAPE only — no I/O, no
    document. Returns a normalised, immutable copy: the caller's own lists and
    mappings are never retained, so a provider callback cannot alter what was
    checked (the #823 time-of-check/time-of-use lesson, applied to the evidence).

    This replaces the detached `expected_representation_sha256`. A bare hash
    said only WHICH document; it could not say where in that document the claim
    points, so nothing downstream could disagree with the channel.
    """
    if type(value) is not dict or set(value) != set(SOURCE_EVIDENCE_KEYS):
        raise SchemaError(
            f"attach_event_xbrl: source_evidence carries EXACTLY the keys "
            f"{SOURCE_EVIDENCE_KEYS}")
    _sha256_or_raise(value["representation_sha256"], "representation_sha256")
    quote = _exact_span(value["quote_span"], "quote_span")
    label = value["raw_label_span"]
    if label is not None:
        label = _exact_span(label, "raw_label_span")
        if not (quote[0] <= label[0] and label[1] <= quote[1]):
            raise SchemaError(
                "attach_event_xbrl: raw_label_span must lie INSIDE quote_span — "
                "a label outside its own quote describes a different place")
    if type(value["pieces"]) not in (list, tuple):
        raise SchemaError(
            "attach_event_xbrl: source_evidence pieces must be a list or tuple")
    pieces = []
    for piece in value["pieces"]:
        if type(piece) is not dict or set(piece) != set(PIECE_KEYS):
            raise SchemaError(
                f"attach_event_xbrl: each evidence piece carries EXACTLY the "
                f"keys {PIECE_KEYS}")
        if piece["kind"] not in PIECE_KINDS:
            raise SchemaError(
                f"attach_event_xbrl: evidence piece kind is one of "
                f"{PIECE_KINDS} — the approved closed set")
        if type(piece["text"]) is not str or not piece["text"].strip():
            raise SchemaError(
                "attach_event_xbrl: each evidence piece needs non-blank "
                "string text")
        record = (piece["kind"], piece["text"],
                  _exact_span(piece["span"], "an evidence piece span"))
        if record in pieces:
            # REFUSED, never collapsed: a duplicate means the claim and the
            # filing disagree about how many pieces there are, and silently
            # de-duplicating would make the two agree by editing the claim.
            raise SchemaError(
                "attach_event_xbrl: duplicate identical evidence pieces are "
                "refused, never collapsed")
        pieces.append(record)
    # READ-ONLY, not merely isolated. The values are already tuples and
    # scalars, so wrapping the outer mapping completes the boundary: nothing
    # holding this during the I/O phase can edit what the pure phase approved.
    # It was a plain `dict` — its CONTENTS were the caller's no longer, which is
    # why the mutation test passed, but the object itself was still writable.
    return MappingProxyType({"representation_sha256":
                             value["representation_sha256"],
                             "quote_span": quote, "raw_label_span": label,
                             "pieces": tuple(pieces)})


def _event_part_lookup(text_parts):
    """The event's text parts — exactly as the model saw them — as ONE lookup.

    Built ONCE per event. The door must not ask for a second mapping or rebuild
    the event text per item, which is how "one representation per event" became
    four document fetches before #821.

    Deliberately small. The shared event builder owns part LABELS, so Core adds
    no grammar for them (no `p01` regex): it requires only an unambiguous exact
    key. A repeated label is malformed because `part_ref` could then select no
    single text. An empty part is lawful — an event may carry a section with no
    text, and only a part a fact NAMES and cannot support is an error.

    The result is a NEW mapping of immutable strings. The caller's list is never
    retained, so the filing provider — caller-supplied code that runs after these
    checks — cannot change the parts between the check and the use.
    """
    if type(text_parts) not in (list, tuple):
        raise SchemaError(
            f"attach_event_xbrl: text_parts must be a list or tuple of "
            f"{_TEXT_PART_KEYS} records, got {type(text_parts).__name__}")
    parts = {}
    for entry in text_parts:
        if type(entry) is not dict or set(entry) != set(_TEXT_PART_KEYS):
            # The message names the EXPECTED keys and nothing else — echoing the
            # caller's keys meant sorting them, and a dict mixing key types
            # raised a raw TypeError inside the guard (the #819 lesson).
            raise SchemaError(
                f"attach_event_xbrl: each text part is a dict carrying EXACTLY "
                f"the keys {_TEXT_PART_KEYS}")
        label, content = entry["part"], entry["content"]
        if type(label) is not str or not label.strip():
            raise SchemaError(
                "attach_event_xbrl: every text part needs a non-blank string "
                "label — it is the exact key `part_ref` selects by")
        if type(content) is not str:
            raise SchemaError(
                f"attach_event_xbrl: text part {label!r} must carry exact "
                f"string content, got {type(content).__name__}")
        if label in parts:
            raise SchemaError(
                f"attach_event_xbrl: text part {label!r} is supplied twice — a "
                f"repeated label cannot select one text deterministically")
        parts[label] = content
    return parts




def attach_event_xbrl(items, *, source_id, store, filing_provider, text_parts,
                      menu_tokens=frozenset()):
    """THE event-level door — one source event, ONE XBRL REPRESENTATION GROUP.

    NOT "one document per event": a single 8-K event lawfully carries its body
    AND its exhibits. What must agree is the XBRL representation those facts
    were tagged in. Census 2026-07-27: 10,468 XBRL-bearing reports, every one
    with exactly one XBRLNode, zero facts spanning two, and zero XBRL-bearing
    8-Ks — so the group is always a singleton today and the guard below exists
    for the filing we have not seen.

    THE GUARD ASKS CORE'S GRAPH, not the channel. Items repeating the same hash
    is the channel agreeing with itself; only the graph can say how many
    representations this source actually has.

    This is a TRUST BOUNDARY — the items come from a channel — so it validates
    its input as strictly as every other door in this module. It previously had
    no input contract at all: a generator was consumed by the first pass and
    silently returned [] ("no XBRL facts"), and malformed items escaped as raw
    KeyError/AttributeError.
    """
    # EXACT built-in containers. `isinstance` admits a list SUBCLASS, and a str,
    # dict or set is iterable and would be walked as characters / keys /
    # members; a generator is consumed by the first pass and silently attaches
    # nothing.
    if type(items) not in (list, tuple):
        raise SchemaError(
            f"attach_event_xbrl: items must be a list or tuple, got "
            f"{type(items).__name__}")
    # THE SOURCE ID IS VALIDATED FIRST — before the lawful zero-I/O return
    # below, which was otherwise a way to skip validation entirely.
    if not valid_source_id(source_id):
        raise SchemaError("attach_event_xbrl: source_id is invalid")
    # `menu_tokens` IS CODE-OWNED, and still an input to a public door. It must
    # be the EXACT immutable output shape of `slice_menu.build_menu` — a
    # frozenset of non-blank strings. A mutable set is refused because the door
    # would then hold a container its caller can still edit; a generator because
    # it can only be read once; a model- or channel-supplied value because this
    # parameter is not theirs to fill. The TOKEN is never parsed here: what a
    # token MEANS is the slice menu's business, not this door's.
    if type(menu_tokens) is not frozenset:
        raise SchemaError(
            f"attach_event_xbrl: menu_tokens must be the frozenset that "
            f"slice_menu.build_menu returns, got {type(menu_tokens).__name__}")
    if not all(type(t) is str and t.strip() for t in menu_tokens):
        raise SchemaError(
            "attach_event_xbrl: every menu_tokens entry is a non-blank string")
    # THE EVENT'S PARTS ARE JUDGED BEFORE THE LAWFUL EMPTY RETURN BELOW, for
    # the same reason the source id is: a return that comes first is a way to
    # skip validation entirely.
    parts = _event_part_lookup(text_parts)
    adapter_exclusions = []      # #828: carried, never recomputed
    member_folds = {}            # notes from the ONE member check
    checked, outcomes = [], []

    def _result(facts=()):
        """THE ONE RETURN SHAPE, from every path including the empty event.

        A bare `[]` used to come back from the no-XBRL branch, so a caller
        reading `.facts` crashed on EVERY 8-K — the exact event that branch
        exists to serve.
        """
        return AttachResult(
            source_id=source_id, facts=tuple(facts),
            preflight_outcomes=tuple(sorted(outcomes, key=lambda o: o["index"])),
            # THE ONE FREEZE OWNER (#823), not a second freezer. The old
            # shallow wrap left every real note and exclusion record editable
            # through the mapping it handed the caller.
            member_menu=_deep_freeze({"folds": dict(member_folds),
                                      "exclusions": list(adapter_exclusions)}))

    if not items:
        # An event with no XBRL (every 8-K) is lawful and does ZERO I/O — but
        # only AFTER the source id has been judged above. This return used to
        # come first, so an empty event was a way to skip validation entirely.
        return _result()

    # ---- EVERY PURE CHECK BEFORE ANY I/O, PER ITEM, and "pure" means the
    # item's CONTENTS. Each check below is the SAME function the per-fact path
    # uses — one rule engine run early, never a second one — and each fact is
    # BUILT ONCE here and carried forward, not validated now and rebuilt later.
    # The old comprehension
    # aborted the whole event on the FIRST item to raise, so one malformed item
    # erased every valid sibling — a real contract defect, since the Channel
    # Contract returns an outcome PER ITEM. Each item now keeps its ORIGINAL
    # index, carried from here and never renumbered by later filtering.
    for index, i in enumerate(items):
        try:
            # THE ITEM'S SHAPE IS THE ITEM'S OWN PROBLEM. This ran as a
            # separate pass over ALL items BEFORE this loop, so one unknown key
            # aborted the whole event and erased every valid sibling — the
            # precise contract defect the rest of this loop was written to fix,
            # surviving in the one place the fix had not reached.
            if type(i) is not dict or set(i) != set(_EVENT_ITEM_KEYS):
                # The message names the EXPECTED keys and nothing else. Echoing
                # the caller's keys meant sorting them, and a dict mixing key
                # types (`{1: ..., "a": ...}`) raised a raw TypeError while
                # FORMATTING the error — a crash inside the guard that exists
                # to prevent crashes.
                raise SchemaError(
                    f"attach_event_xbrl: each item is a dict carrying EXACTLY "
                    f"the keys {_EVENT_ITEM_KEYS}")
            concept = i["concept"]
            if type(concept) is not str or not concept.strip():
                raise SchemaError("attach_event_xbrl: each item needs a concept")
            evidence = _checked_source_evidence(i["source_evidence"])
            fact = PreparedFactV2._build(i["fact"], {   # the fact schema law
                "xbrl_concept_raw": concept, "member_refs": i["member_refs"]})
            # ONLY THE FACT TRAVELS ON — the caller's refs list is never carried
            # past a provider callback (the #823 time-of-check/time-of-use hole).
            if fact.part_ref not in parts:
                raise SchemaError(
                    f"attach_event_xbrl: the fact names event part "
                    f"{fact.part_ref!r}, which this event did not supply")
            why = verify_occurrence(parts[fact.part_ref], fact.item.quote,
                                    fact.occurrence_in_part)
            if why:
                raise SchemaError(
                    f"attach_event_xbrl: part {fact.part_ref!r} does not "
                    f"support this fact's quote — {why}")
            checked.append((index, fact, concept, evidence))
        except OUTCOME_ITEM_CLASSES as exc:
            outcomes.append(_outcome_row(index, exc))

    if not checked:            # nothing survived the pure phase: ZERO I/O
        return _result()

    def _fan_out(exc, code=None):
        """An EVENT-WIDE failure reaches every still-valid affected item, each
        keeping its own index. It is one cause, not one victim."""
        for idx, _f, _c, _e in checked:
            outcomes.append(_outcome_row(idx, exc, code=code))
        return _result()

    try:
        expected = _one_representation_for_event(
            [e["representation_sha256"] for _i, _f, _c, e in checked])
    except SchemaError as exc:
        # Conflicting hashes among otherwise-valid items reject THOSE items as
        # one inconsistent submission — the envelope itself was fine.
        return _fan_out(exc)

    # ---- ONE set of reads per EVENT (never per item) ------------------------
    try:
        count = _fetch("the graph", store.get_xbrl_representation_count, source_id)
        if type(count) is not int or count != 1:
            raise ProductionValidationError(
                f"attach_event_xbrl: source {source_id} reports {count!r} XBRL "
                f"representation(s); exactly one INTEGER 1 can be bound — park")
        document = _fetch("the filing provider",
                          filing_provider.get_filing_document, source_id)
        if not isinstance(document, str) or not document.strip():
            raise SourceUnavailable(
                f"attach_event_xbrl: the filing provider has no document for "
                f"source {source_id} yet — park and retry")
        prepared_doc = prepare(document)      # ONE parse + ONE hash per event
        # F3 (#827, owner-ruled sheet #6 verbatim: "PARK + DOCUMENT-BLAME,
        # retryable; never fact-blame, never silent"): unreadable IS a
        # property of the SERVED DOCUMENT — the party who can fix it is the
        # document's server, so this parks retryable with document blame.
        # The old SchemaError told the channel to "fix and resubmit" a fact
        # it does not own; code and comment now agree. Nothing here
        # inspects, repairs or works around the bytes.
        if refused(prepared_doc):
            raise SourceUnavailable(
                f"attach_event_xbrl: the served document for source "
                f"{source_id} cannot be read as evidence "
                f"({refused(prepared_doc)}) — document-scoped, park and "
                f"retry against a re-served copy")
        if prepared_doc["text_sha"] != expected:
            raise SchemaError(
                "attach_event_xbrl: the served document does not hash to the "
                "representation harvested for this source — the evidence is not "
                "this filing's")
    except OUTCOME_ITEM_CLASSES as exc:
        return _fan_out(exc)                  # shared dependency: all affected

    try:
        entity_cik = _fetch("the graph", store.get_source_company_cik, source_id)
        if not str(entity_cik or "").strip():
            raise ProductionValidationError(
                f"Core's graph names no single filing company for {source_id} "
                f"— park (never take the company from the document provider, "
                f"which is channel-supplied)")
    except ProductionValidationError as exc:
        # THIS BRANCH OWNS ITS CODE. It used to live only inside the message
        # text, so the channel received the generic binding code and could not
        # distinguish this from any other park. Chosen by BRANCH — nothing here
        # reads an exception message to decide.
        return _fan_out(exc, code="SOURCE_COMPANY_AMBIGUOUS")
    except OUTCOME_ITEM_CLASSES as exc:
        return _fan_out(exc)                  # an outage on the same read

    rows_by_concept = {}                      # EVENT-LOCAL; never a global cache
    concept_failure = {}
    for _i, _fact, concept, _e in checked:
        if concept in rows_by_concept or concept in concept_failure:
            continue
        try:
            read = _fetch("the graph", store.get_xbrl_fact_dimensions,
                          source_id, concept)
            adapter_exclusions.extend(read.exclusions)
            if not read.rows:
                raise ProductionValidationError(
                    f"attach_event_xbrl: source {source_id} carries NO fact for "
                    f"concept {concept!r} yet — park; an unbacked concept is "
                    f"never attached")
            # DERIVED HERE, ONCE PER GRAPH ROW, not once per item. Building the
            # expanded set inside the per-item path re-derived every row for
            # every item sharing a concept, which made "exactly once" false at
            # event scope. Plain `(row, expanded)` pairs — no wrapper, no cache.
            #
            # It also puts an unusable graph row where every other broken row
            # shape already fails: at the concept READ, once, instead of being
            # rediscovered independently by each item.
            rows_by_concept[concept] = [
                (checked, _row_expanded_dims(checked))
                for checked in (_checked_row(r) for r in read.rows)]
        except SourceUnavailable as exc:
            # AN OUTAGE IS NOT A PROPERTY OF THE CONCEPT. Recording it as a
            # concept-local absence tells the channel that THIS concept is
            # missing from the filing — false, and durable — while a sibling
            # concept read over the same broken connection looks clean.
            return _fan_out(exc)
        except OUTCOME_ITEM_CLASSES as exc:
            # An ordinary concept-level absence affects ONLY items claiming it.
            concept_failure[concept] = exc

    # INPUT ORDER IS OUTPUT ORDER, and each item stands or falls alone.
    facts = []
    for index, fact, concept, evidence in checked:
        exc = concept_failure.get(concept)
        if exc is not None:
            outcomes.append(_outcome_row(index, exc))
            continue
        try:
            bound = _verify_and_attach(
                fact, concept=concept, evidence=evidence,
                prepared_doc=prepared_doc, entity_cik=entity_cik,
                rows=rows_by_concept[concept], menu_tokens=menu_tokens)
        except OUTCOME_ITEM_CLASSES as e:
            # Raised BEFORE the member check could run, so there is no member
            # result to keep — and one is never invented.
            bound = _ItemResult(None, e, None, (), ())
        # THE AUDIT IS KEPT WHETHER THE ITEM PASSED OR NOT, which is the whole
        # of #825: the notes and logs the ONE member check produced used to die
        # inside the binder, so nothing survived to the writer. Notes are
        # indexed by the caller's ORIGINAL index exactly as the live writer
        # records them, and empty notes invent no fold row.
        if bound.notes:
            member_folds[str(index)] = bound.notes
        adapter_exclusions.extend(bound.logs)
        if bound.exc is None:
            facts.append((index, bound.fact))
            continue
        outcomes.append(_outcome_row(index, bound.exc, code=bound.code))
    return _result(facts)


def _verify_and_attach(fact, *, concept, evidence, prepared_doc, entity_cik,
                       rows, menu_tokens):
    # F1 (#827): the frozenset() DEFAULT is deleted — it was the same
    # no-menu gate the public door decides, bypassable here; the one caller
    # always passes the event's menu explicitly.
    """Verify ONE already-checked fact against the event's already-fetched
    filing evidence, and attach — or raise. PRIVATE: `attach_event_xbrl` is the
    only public XBRL attachment door, so no caller can bypass the event-level
    representation guard.

    IT REFETCHES AND REVALIDATES NOTHING. The event door has already built the
    fact once, frozen its member refs, fetched and hashed the filing once, read
    the company CIK once, and normalised this concept's rows once. Repeating any
    of that per item is what made four same-concept facts cost four document
    fetches, four CIK reads and four row reads.

    IT BUILDS NO VERIFIER OF ITS OWN either. Every judgement is delegated to the
    already-certified Route-A binder in `driver.relocation.inline_html`:
    `element_evidence` (short element id, duplicate-id detection) ·
    `identity_fallback` (the unique complete-identity fallback) · `parse_raw`
    (the frozen canonical graph lexical contract derived from the two writer
    formatters — 807,132 of 1,000,000 sampled graph values carry commas, so a
    bare `Decimal()` rejects most real facts; corpus evidence shows
    compatibility, not legality or complete formatter reachability) ·
    `reconcile` (displayed composed with format, scale and sign must equal the
    graph's own value). Re-implementing any of those would be a second filing
    verifier, which is exactly what this program refuses.

    WHAT THE HASH ACTUALLY PROVES, stated honestly: the document and the
    harvested hash BOTH originate with the channel, so the comparison detects
    document DRIFT — the filing read now is not the filing harvested then — and
    nothing about whether the channel is trustworthy. The one genuinely
    independent input is the filing company, which comes from Core's own graph.
    """
    from driver.core.slice_menu import (axis_member_pairs, check_member_refs,
                                        match_xbrl_fact)
    from driver.relocation.inline_html import bind_graph_fact

    it = fact.item
    refs = it.member_refs          # FROZEN at construction; the caller's copy
    inline_doc = prepared_doc      # is never trusted after a provider callback
    # COMPUTED ONCE. The same pair set is the fact's claim AND what the binder
    # is handed; deriving it twice invites the two to drift apart.
    claimed_pairs = axis_member_pairs(refs)
    claim = {"time_type": it.time_type, "start": it.period_start_date,
             "end": it.period_end_date, "dims": claimed_pairs}
    # `rows` ARRIVES AS (raw row, expanded dims) PAIRS, derived at the concept
    # read — once per graph row for the whole event, not once per item. Semantic
    # identity is therefore already validated before anything here matches:
    # run the check AFTER the matcher and a row with a repeated or unstateable
    # dimension falls out as "no row matched", reported as ordinary graph lag,
    # which is a true-sounding sentence about the wrong thing.
    #
    # ONE matcher pass: keep each row WITH the dims it matched on, instead of
    # re-running `match_xbrl_fact` on the winner further down. The matcher is
    # given the RAW row — that is its frozen product contract — while the
    # already-derived expanded set rides along beside it.
    matched_pairs = [(r, d, x) for r, d, x in
                     ((r, match_xbrl_fact(claim, [r]), x) for r, x in rows)
                     if d is not None]
    matched = [r for r, _d, _x in matched_pairs]
    if not matched:
        # PARK, not a rejection — the same #819 class. The concept is present
        # but no row carries this exact context/dimension set: the graph runs
        # about a quarter behind the channel, so this is far more often corpus
        # lag than an invented claim, and a rejection loses the fact for good
        # while a park drains or ages out visibly.
        raise ProductionValidationError(
            "attach: no fact in this filing carries that concept with the "
            "fact's exact context AND complete dimension set — park")
    signatures = {_row_signature(r) for r in matched}
    if len(signatures) > 1:
        # The message always said PARK; the TYPE said reject, which tells a
        # channel to go and fix a filing it does not own and never drains.
        raise ProductionValidationError(
            "attach: the filing carries CONFLICTING facts for this "
            "concept+context+dimensions — park; never pick one by position")
    # THE WINNER CARRIES ITS OWN EXPANDED SET, derived before matching and
    # never recomputed. There is no `None` to guard against here: the deriver
    # raises, so the fail-open is gone by construction rather than by a check
    # someone could later delete.
    row, matched_dims, graph_dims = matched_pairs[0]
    # (the per-field presence/blankness checks that used to sit here now run in
    # `_checked_row`, before anything reads the row — same law, correct place)

    # ---- THE ONE Route-A binding. Core adds no filing check of its own: the
    # identity law (exact id vs blank-only fallback, concept, context, period,
    # dimensions, entity, unit, visibility, sign) and the exact reconciliation
    # all live in the binder, which is where they are certified.
    bound, why = bind_graph_fact(
        inline_doc, inline_element_id=row["fact_id"], concept=concept,
        context_id=row["context_id"], unit_ref=row["unit_ref"],
        unit_name=row["unit_name"], is_divide=row["is_divide"],
        # the ROW's own dates: `match_xbrl_fact` above already proved the row
        # matches THIS fact's claim, and the binder compares row-to-document
        # (the graph stores the end EXCLUSIVE, the filing declares it inclusive)
        period_type=row["period_type"], start_date=row["start_date"],
        # THE ROW'S OWN EXPANDED DIMENSIONS, not the claim's raw pairs. The
        # binder's `dims` is semantic identity and nothing else: it is compared
        # against the filing's (namespace URI, local name) pairs, so handing it
        # prefixed text asked one question and answered another. The claim is
        # still what `match_xbrl_fact` selected the row with, above — that is
        # the frozen product contract and it keeps its raw qnames.
        end_date=row["end_date"], dims=graph_dims,
        entity_cik=entity_cik, raw_value=row["value"],
        # THE CONCEPT'S IDENTITY, both halves from the SAME Concept record the
        # row was read with. The binder compares (namespace URI, local name)
        # because a prefix is only an alias, and it refuses truthfully when the
        # graph cannot supply that identity rather than falling back to a
        # prefixed string comparison that a different taxonomy would satisfy.
        concept_namespace=row["concept_namespace"],
        graph_concept_qname=row["graph_concept_qname"])
    if bound is None:
        # ORDINARY PARK, as ONE class. Every reason this returns describes a
        # GRAPH/FILING binding failure — a missing element, a duplicate id, a
        # value that will not reconcile — and none of them is malformed model
        # JSON, so none is a contract rejection. Decided by WHERE the failure
        # came from, never by a lookup on its wording.
        raise ProductionValidationError(
            f"attach: Route-A binding abstained ({why}) — park")

    # ---- THE FILING SIDE OF THE CHAIN --------------------------------------
    # Every submitted offset is checked against the document THIS event fetched
    # and hashed, in PYTHON STRING (character) offsets — never UTF-8 bytes.
    text = prepared_doc["text"]
    q_start, q_end = evidence["quote_span"]
    if q_end > len(text):
        raise SchemaError(
            "attach: the submitted quote_span ends beyond the representation")
    filing_quote = text[q_start:q_end]
    if not filing_quote.strip():
        raise SchemaError("attach: the submitted quote_span slices blank text")
    if evidence["raw_label_span"] is not None \
            and evidence["raw_label_span"][1] > len(text):
        raise SchemaError(
            "attach: the submitted raw_label_span ends beyond the representation")
    for kind, piece_text, (start, end) in evidence["pieces"]:
        if end > len(text) or text[start:end] != piece_text:
            raise SchemaError(
                f"attach: evidence piece {kind} {piece_text!r} is not the text "
                f"at its own span — the claim and the filing disagree")

    # ---- AND AGAINST THE SAME CONSTRUCTION THAT PRODUCED IT ----------------
    canonical = source_evidence(prepared_doc, bound["evidence"])
    if canonical is None:
        raise ProductionValidationError(
            "attach: the bound element has no reproducible visible row/block "
            "evidence in this filing — park rather than invent a locator")
    canon_label = (tuple(canonical["raw_label_span"])
                   if canonical["raw_label_span"] else None)
    if canonical["representation_sha256"] != evidence["representation_sha256"] \
            or tuple(canonical["quote_span"]) != evidence["quote_span"] \
            or canon_label != evidence["raw_label_span"]:
        raise SchemaError(
            "attach: the submitted source evidence does not describe the bound "
            "element — a sibling row's location cannot stand for this fact")
    canon_pieces = tuple((p["kind"], p["text"], (p["span"][0], p["span"][1]))
                         for p in canonical["pieces"])
    if canon_pieces != evidence["pieces"]:
        # SEQUENCE INCLUDED. Headers are carried near-to-far and then the
        # section; nothing here may reorder them, and comparing as sets would
        # accept a sibling column's period header attached to this fact.
        raise SchemaError(
            "attach: the submitted evidence pieces differ from the bound "
            "element's own — missing, extra, reworded, re-spanned or reordered")
    if it.quote != filing_quote:
        raise SchemaError(
            "attach: the fact's quote is not the verified filing quote — the "
            "exact quote is the ONLY bridge between the event view and the "
            "filing, and it must be the same characters in both")
    # THE UNIT'S MEANING, bound to the fact's own canonical unit. Without this,
    # `count` and `usd` do IDENTICAL arithmetic, so a real $5,262,000,000 fact
    # was accepted as a count (reproduced live 2026-07-27).
    # THE BOUND ELEMENT'S OWN DECLARED UNIT IDENTITIES, and nothing else. The
    # raw name still appears in the refusal message below — a reader needs to
    # see what the graph holds — but it no longer decides anything.
    lawful = candidate_units_for(bound["unit_measures_expanded"],
                                 bound["unit_numerator_expanded"])
    if it.level_unit not in lawful:
        admits = sorted(lawful) or "nothing on this route"
        raise SchemaError(
            f"attach: the graph records unit {row['unit_name']!r} "
            f"for this fact, which may back {admits} — not "
            f"level_unit={it.level_unit!r}")

    problems, notes, logs = check_member_refs(         # EXISTING law, unchanged
        [dict(r) for r in refs], frozenset(it.slice_parts), menu_tokens,
        matched_dims)                                 # from the ONE pass above
    # CARRIED AS-IS. Freezing them here too was a SECOND freeze: `_result`
    # already sends the whole audit through the one `_deep_freeze` owner, which
    # copies, and no caller callback runs between here and there.
    if problems:
        # THE LIVE WRITER PARKS THIS, under its own code. A ref-level breach is
        # evidence the graph cannot bind, not a channel contract violation:
        # raising SchemaError told the channel to "fix and resubmit" something
        # it does not own, and destroyed the structured logs on the way out.
        return _ItemResult(None,
                           ProductionValidationError(f"attach: {problems[0]}"),
                           "MEMBER_LINK_INVALID", notes, logs)
    try:
        from driver.core.slot_convert import convert_slot

        # F1 (#827): the slice_part membership re-check deleted (checkpoint
        # 1d4928c4 + b17a9303) — check_member_refs owns the rule at
        # slice_menu:308-310 and exits with problems FIRST, so this later
        # SchemaError was unreachable.

        # ---- the COMPLETE numeric slot set, against what the FILING PRINTS ------
        # The multiplier the fact must state is UNIT-DEPENDENT: ix.scale verifies
        # the graph value, and only money/count carry it into the stored
        # multiplier. `reconcile` (inside the binder) already proved
        # displayed x 10^ix_scale == the graph value, so a second "converted total"
        # comparison against `bound["value"]` was both redundant AND wrong for a
        # percentage — it demanded that 2.6 percent equal the graph's 0.026.
        want_value = bound["printed_value"]
        # ONE integer, ONE owner: the evidence record's `scale` is already the
        # xml_integer-parsed int; the result no longer publishes a duplicate.
        want_mult = expected_multiplier(it.level_unit, bound["evidence"]["scale"])
        # `SlotConversionError` IS ALLOWED OUT. It used to be caught here and
        # re-raised as `SchemaError`, which told the channel that a value the store
        # simply cannot materialise was a CONTRACT VIOLATION to fix and resubmit.
        # The filing is lawful; the value is not storable. That is its own declared
        # outcome (parked / NOT_STORABLE) and this route must not overwrite it.
        for name in NUMERIC_SLOTS:
            slot = getattr(it, name)
            if name in ("level_low", "level_high"):
                if slot is None:
                    raise SchemaError(
                        f"attach: an XBRL-backed fact states ONE "
                        f"reported value, so {name} is required")
                # THE THREE FIELDS, against what the filing actually prints — not
                # the converted total. {390, 10^6}, {390000000, 1} and {0.39, 10^9}
                # all convert alike; only one describes THIS filing. The expected
                # object comes FROM the binder.
                if slot["value"] != want_value or \
                        slot["scale_multiplier"] != want_mult:
                    raise SchemaError(
                        f"attach: {name} describes the source as "
                        f"value={slot['value']} x {slot['scale_multiplier']}, "
                        f"but the filing prints {want_value} and a "
                        f"{it.level_unit} fact must state multiplier {want_mult}")
                if slot["unit_scale_evidence"] is not None:
                    raise SchemaError(
                        f"attach: {name}.unit_scale_evidence must be "
                        f"null on an XBRL-backed fact — the structured metadata "
                        f"IS the evidence there (quote-local spans are the text "
                        f"lane's carrier)")
                convert_slot(it.level_unit, slot)   # must convert at all
            elif slot is not None:
                raise SchemaError(
                    f"attach: {name} must be null on an XBRL-backed "
                    f"fact — the filing reports a single value")

        # THE VERIFIED FACT IS ALREADY THE ANSWER. It was built at the top of this
        # function with exactly this bundle, and the dataclass boundary froze it
        # then — so rebuilding an identical object here was pure waste, and a second
        # construction site for something already constructed.
        return _ItemResult(fact, None, None, notes, logs)
    except OUTCOME_ITEM_CLASSES as exc:
        # The member evidence above is already real and stays with the item.
        return _ItemResult(None, exc, None, notes, logs)
