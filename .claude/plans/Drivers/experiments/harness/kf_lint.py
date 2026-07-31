"""kf_ draft/key lint v4 (v2.0 contract) — machine-enforced exam-validity checker.

Modes:
  single (default): lint the given file's docs (still fails on EMPTY input).
  --arm:            a full arm's output — EXACTLY 36 docs, 36 unique source_ids,
                    each with a draft_inputs file; empty/short/extra = FAIL.

Per doc: keys == EXACTLY {source_id, facts}. Per fact: keys == EXACTLY
{fact_type, du_worthy, gold_item, gold_extra, quote, ambiguity_note}. gold_item
keys == EXACTLY the 37 MODEL-OWNED fields (NOT 39 — member_refs +
xbrl_concept_raw are source/code-owned on PreparedFactV1, never in gold_item;
fact_type rides at the fact level). `du_worthy` is a BOOL — false is the lawful
near-miss exemplar, never rejected. OUTER quote: non-blank, VERBATIM in the
event text (no length band — WO:173), IDENTICAL to gold_item.quote.
Mechanical enums ('none' is NOT legal — FINAL_DESIGN.md:238; null when
numberless). Shape↔hint coherence. NUMBERS ARE EXACT: drafts are parsed with
`parse_float=Decimal` and numerics accept int/Decimal ONLY — a raw float is a
lint error (production rejects floats; digits must never be lost in transport).
TYPE checks with clean per-field errors (never a crash): strings str ·
company_confirmed/has_favorability_wording nullable bool ·
sequential_evidence NON-null bool · polarity_proof nullable object ·
measurement_raw_spans/slice_parts NON-null list[str] (empty [] is a CLAIM, not
a default).
NOTE (v2.1, pending owner approval): the quote locator moves to an audit-only
`evidence_locator` (part_ref + occurrence_in_part) inside the item; the current
unique-span check is superseded once that patch is applied.
Exit 1 on any error. Usage:
  venv/bin/python harness/kf_lint.py <file.jsonl | dir> [--arm]"""
import json
import os
import sys
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, _REPO)
from driver.core.unit_resolver import (VALID_MONEY_MODE_HINTS,          # noqa: E402
                                       VALID_UNIT_KIND_HINTS)
from driver.core.driver_ids import valid_driver_name                    # noqa: E402
from driver.core.driver_validators import LANE_STATES                   # noqa: E402
from driver.core.driver_period_resolver import (PeriodResolutionError,  # noqa: E402
                                                ensure_driver_period)
from driver.core.prepared_fact import (PreparedFactV1, SchemaError,     # noqa: E402
                                       _num as _prod_num)

# THE ONE AUTHORITATIVE FIELD SOURCE. The 37 model-owned fields are DERIVED
# from the production record (PreparedFactV1) minus the two source/code-owned
# fields — never re-typed here, so the exam contract can never drift from
# production. fact_type rides at the FACT level, outside gold_item.
SOURCE_OWNED = ("member_refs", "xbrl_concept_raw")
FIELDS37 = [f for f in PreparedFactV1.FIELDS if f not in SOURCE_OWNED]
assert len(PreparedFactV1.FIELDS) == 39 and len(FIELDS37) == 37, (
    f"production record changed: {len(PreparedFactV1.FIELDS)} fields — the exam "
    f"contract must be re-reviewed, not silently re-derived")
DOC_KEYS = {"source_id", "facts"}
FACT_KEYS = {"fact_type", "du_worthy", "gold_item", "gold_extra", "quote",
             "ambiguity_note"}
SHAPES = {"point", "range", "floor", "ceiling", None}    # 'none' is NOT legal
ENUMS = {
    "level_shape_hint": SHAPES, "comparison_shape_hint": SHAPES,
    "surprise_basis_hint": {"actual", "guidance", None},
    "comparison_baseline": {"consensus", "prior_year", "sequential_period",
                            "previous_guidance", None},
    "period_scope": {"ytd", "ttm", None},                # producer-side ONLY
    "time_type": {"duration", "instant", None},
    "sentinel_class": {"short_term", "medium_term", "long_term", "undefined",
                       None},
    "level_unit_kind_hint": set(VALID_UNIT_KIND_HINTS) | {None},
    "change_unit_kind_hint": set(VALID_UNIT_KIND_HINTS) | {None},
    "level_money_mode_hint": set(VALID_MONEY_MODE_HINTS) | {None},
    "change_money_mode_hint": set(VALID_MONEY_MODE_HINTS) | {None},
}
NUMERIC = {"level_low", "level_high", "change_value", "comparison_low",
           "comparison_high"}
STRINGY = {"driver_name", "driver_state", "quote", "value_text", "conditions",
           "level_unit_raw", "change_unit_raw", "period_start_date",
           "period_end_date"}
DEFAULT_INPUTS = os.path.join(_HERE, "..", "keys", "K-fields", "draft_inputs")


def _is_num(v):
    """THE production numeric rule, reused (not re-implemented): exact
    int/Decimal only — bool, float and non-finite Decimal all rejected. Drafts
    are parsed with parse_float=Decimal so JSON numbers arrive exact."""
    try:
        _prod_num("v", v)
        return v is not None
    except SchemaError:
        return False


def event_text(source_id, inputs_dir):
    p = json.load(open(os.path.join(inputs_dir, f"{source_id}.json")))
    return "\n".join(x["content"] for x in p["text_parts"])


def event_meta(source_id, inputs_dir):
    p = json.load(open(os.path.join(inputs_dir, f"{source_id}.json")))
    return p.get("fye_month"), p.get("event_date")


def _shape_err(low, high, hint):
    if not (low is None or _is_num(low)) or not (high is None or _is_num(high)):
        return False                     # typed elsewhere; no crash here
    has_l, has_h = low is not None, high is not None
    if hint == "point":
        return not (has_l and has_h and low == high)
    if hint == "range":
        return not (has_l and has_h and low < high)
    if hint == "floor":
        return not (has_l and not has_h)
    if hint == "ceiling":
        return not (has_h and not has_l)
    if hint is None:
        return has_l or has_h
    return True


def _types(w, gi, errors, lane=None, _fye=None):
    for k in NUMERIC:
        v = gi.get(k)
        if v is not None and not _is_num(v):
            errors.append(f"{w}: {k} must be a number or null, got "
                          f"{type(v).__name__}")
    for k in STRINGY:
        v = gi.get(k)
        if v is not None and not isinstance(v, str):
            errors.append(f"{w}: {k} must be a string or null, got "
                          f"{type(v).__name__}")
    for k in ("company_confirmed", "has_favorability_wording"):   # nullable bool
        v = gi.get(k)
        if v is not None and not isinstance(v, bool):
            errors.append(f"{w}: {k} must be bool or null")
    if not isinstance(gi.get("sequential_evidence"), bool):       # NON-null bool
        errors.append(f"{w}: sequential_evidence must be a bool (true/false)")
    v = gi.get("polarity_proof")
    if v is not None and not isinstance(v, dict):
        errors.append(f"{w}: polarity_proof must be an object or null")
    for k in ("measurement_raw_spans", "slice_parts"):    # NON-null list (empty = a claim)
        v = gi.get(k)
        if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
            errors.append(f"{w}: {k} must be a list of strings (not null)")
    # period validation = THE PRODUCTION RESOLVER, exactly (no invented caps,
    # no re-implemented combo rules): PeriodResolutionError verbatim = the
    # error. BASIC TYPES are gated FIRST so malformed AI output produces a
    # lint error, never a crash; the resolver is additionally belt-wrapped.
    pre_typed_ok = True
    for k in ("period_start_date", "period_end_date", "time_type",
              "period_scope", "sentinel_class"):
        v = gi.get(k)
        if not isinstance(v, (str, type(None))):
            pre_typed_ok = False              # already reported by type checks
    if (_fye is not None and pre_typed_ok
            and lane in ("metric", "guidance", "surprise", "action_event")):
        try:
            ensure_driver_period(gi, fact_type=lane, fye_month=_fye)
        except PeriodResolutionError as e:
            errors.append(f"{w}: period law: {e}")
        except (TypeError, ValueError, AttributeError) as e:
            errors.append(f"{w}: period fields malformed "
                          f"({type(e).__name__}: {str(e)[:60]})")


def lint_doc(doc, errors, inputs_dir):
    if not isinstance(doc, dict) or set(doc) != DOC_KEYS:
        errors.append(f"doc keys must be EXACTLY {sorted(DOC_KEYS)}, got "
                      f"{sorted(doc) if isinstance(doc, dict) else type(doc).__name__}")
        return
    sid = doc["source_id"]
    try:
        text = event_text(sid, inputs_dir)
        fye, _ev_date = event_meta(sid, inputs_dir)
    except FileNotFoundError:
        errors.append(f"{sid}: NO draft_inputs file for this source_id")
        return
    if not isinstance(doc["facts"], list):
        errors.append(f"{sid}: facts must be a list")
        return
    for i, f in enumerate(doc["facts"]):
        w = f"{sid}#{i}"
        if not isinstance(f, dict) or set(f) != FACT_KEYS:
            errors.append(f"{w}: fact keys must be EXACTLY "
                          f"{sorted(FACT_KEYS)}")
            continue
        lane_v = f["fact_type"]
        if not isinstance(lane_v, str) or lane_v not in (
                "metric", "guidance", "surprise", "action_event"):
            errors.append(f"{w}: bad fact_type {lane_v!r}")
            lane_v = None                     # downstream checks skip cleanly
        if not isinstance(f["du_worthy"], bool):     # false = lawful near-miss exemplar
            errors.append(f"{w}: du_worthy must be a bool (true or false)")
        gi = f["gold_item"]
        if not isinstance(gi, dict):
            errors.append(f"{w}: gold_item must be an object")
            continue
        dn = gi.get("driver_name")
        if not isinstance(dn, str) or not valid_driver_name(dn):
            errors.append(f"{w}: driver_name {dn!r} fails the NAME-05 law "
                          f"(required, snake_case, non-null)")
        ds = gi.get("driver_state")
        if not isinstance(ds, str):
            errors.append(f"{w}: driver_state must be a non-null string, got "
                          f"{type(ds).__name__}")
        elif lane_v in LANE_STATES and ds not in LANE_STATES[lane_v]:
            errors.append(f"{w}: driver_state {ds!r} not in the {lane_v} lane "
                          f"vocabulary")
        missing = [k for k in FIELDS37 if k not in gi]
        extra = [k for k in gi if k not in FIELDS37]
        if missing:
            errors.append(f"{w}: MISSING keys {missing}")
        if extra:
            errors.append(f"{w}: EXTRA keys {extra}")
        q = f["quote"]
        if not isinstance(q, str) or not q.strip():
            errors.append(f"{w}: quote BLANK/absent")
        else:
            # v2.0: NO length band (WO:173) — verbatim + non-blank + UNIQUE span.
            if q not in text:
                errors.append(f"{w}: quote NOT verbatim: {q[:60]!r}")
            elif text.count(q) != 1:
                errors.append(f"{w}: quote NOT a unique span (occurs "
                              f"{text.count(q)}×; extend it or abstain)")
        if gi.get("quote") != q:
            errors.append(f"{w}: inner gold_item.quote != outer quote")
        _types(w, gi, errors, lane=lane_v, _fye=fye)
        for k, legal in ENUMS.items():
            v = gi.get(k)
            if not isinstance(v, (str, type(None))):
                errors.append(f"{w}: {k} must be a string or null, got "
                              f"{type(v).__name__}")
            elif k in gi and v not in legal:
                errors.append(f"{w}: {k}={v!r} not in enum")
        if _shape_err(gi.get("level_low"), gi.get("level_high"),
                      gi.get("level_shape_hint")):
            errors.append(f"{w}: level shape/hint incoherent")
        if _shape_err(gi.get("comparison_low"), gi.get("comparison_high"),
                      gi.get("comparison_shape_hint")):
            errors.append(f"{w}: comparison shape/hint incoherent")
        ge = f["gold_extra"]
        if not (isinstance(ge, dict)
                and set(ge) == {"expectation_comparison_present"}
                and isinstance(ge["expectation_comparison_present"], bool)):
            errors.append(f"{w}: gold_extra shape wrong")
        an = f["ambiguity_note"]
        if an is not None and not isinstance(an, str):
            errors.append(f"{w}: ambiguity_note must be string or null")


def lint_parsed(docs, inputs_dir=DEFAULT_INPUTS, arm=False):
    """Validate ALREADY-PARSED docs — the entry point the live pipeline uses.

    raw_transport parses the reply ONCE with parse_float=Decimal; handing the
    parsed object straight here avoids a re-serialize/re-parse round trip that
    would silently turn every exact Decimal back into a string (caught by the
    live hand-off test). Same contract as run(), applied to exact values.
    Returns an exit code: 0 clean, 1 on any error."""
    errors = []
    if not docs:
        errors.append("EMPTY input — nothing to lint is a FAILURE, never a pass")
    for doc in docs:
        lint_doc(doc, errors, inputs_dir)
    sids = [d.get("source_id") for d in docs if isinstance(d, dict)]
    if len(set(sids)) != len(sids):
        errors.append("DUPLICATE source_ids in the set")
    if arm:
        expected = sorted(x[:-5] for x in os.listdir(inputs_dir)
                          if x.endswith(".json"))
        if sorted(set(sids)) != expected or len(docs) != len(expected):
            errors.append(f"--arm requires EXACTLY the {len(expected)} events "
                          f"one doc each; got {len(docs)} docs / "
                          f"{len(set(sids))} unique")
    print(f"docs linted: {len(docs)}; errors: {len(errors)}")
    for e in errors[:40]:
        print(" ", e)
    return 1 if errors else 0


def run(target, arm=False, inputs_dir=DEFAULT_INPUTS):
    """File/dir entry point: read + EXACT-parse, then delegate to lint_parsed.
    Deliberately NO duplicated checking logic — one implementation only (the
    copy that used to live here is exactly the drift class that produced the
    FIELDS37 and _is_num/_dec defects)."""
    paths = ([os.path.join(target, x) for x in sorted(os.listdir(target))]
             if os.path.isdir(target) else [target])
    docs = []
    for p in paths:
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line:
                docs.append(json.loads(line, parse_float=Decimal))
    return lint_parsed(docs, inputs_dir, arm=arm)


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if a != "--arm"]
    sys.exit(run(argv[0], arm="--arm" in sys.argv))
