"""Standalone attribution_result.v3 validator — zero external dependencies.

Round 6 fresh-start cutover (2026-05-04, .claude/plans/LearnerLoopRevamp.md):
v3-only. Pre-cutover v2 files are wiped; this validator REJECTS any
schema_version other than ``attribution_result.v3``.

This is the SINGLE CANONICAL validator. Both the orchestrator Python and the
PreToolUse hook import from here. Only stdlib imports (plus a single
``config.canonical_sectors`` lookup) — no Neo4j, no builders, no SDK. This
ensures the hook never fails-open due to missing dependencies.

Layering:
  - ``validate_attribution_result`` — thin wrapper; dispatches by
    schema_version. v3-only after round 6.
  - ``_validate_common_core`` — rules independent of schema version
    (top-level required fields, ticker/quarter match, evidence_ledger,
    primary_driver, contributing_factors, prediction_comparison,
    array caps, global_observations scope-routing invariants, missing_inputs,
    data_sources_used, ref-field equality).
  - ``_validate_v3`` — v3-specific additions (LearnerLoopRevamp.md §8.3 +
    user clarification #3): structured ``predictor_lessons`` /
    ``global_observations`` (lesson + mechanism + applies_when + invalid_if
    each ≥30 chars, ``evidence_refs`` non-empty + IDs resolve in
    ``evidence_ledger``); ``lesson_audit[]`` shape (full enum coverage,
    ``evidence_refs`` non-empty + IDs resolve, ``replacement_lesson`` on
    ``action="refine"``).

Hook contract for ``lesson_audit``: structurally optional — if present, must
have valid shape; if absent, validator passes through. The orchestrator's
cross-file check (D19, see ``_validate_audit_against_prediction``) is the
authoritative coverage gate (it has access to the prediction file; this
hook does not).

Schema invariants enforced on ``global_observations[]`` (carried over from
v2 amendment 2026-04-17, per .claude/plans/learner.md Appendix A):

  - ``scope_key`` is REMOVED — rejected across ALL scopes.
  - ``scope="cross_ticker"`` REQUIRES non-empty ``related_tickers`` (uppercase
    alphabetic strings, 1-5 chars, max 8, no duplicates). ``target_sector``
    MUST NOT be present.
  - ``scope="sector"`` REQUIRES ``target_sector`` ∈ ``CANONICAL_SECTORS``.
    ``related_tickers`` MUST NOT be present.
  - ``scope="macro"`` rejects BOTH ``related_tickers`` and ``target_sector``.

Validator is the single authority for ``related_tickers`` dedupe (writer is a
pure pass-through — see orchestrator ``append_global_lessons``).
"""
from __future__ import annotations
from difflib import get_close_matches
from typing import Any

from config.canonical_sectors import CANONICAL_SECTORS


def _ok_ticker(t: object) -> bool:
    """Validate a single ticker symbol shape: uppercase alphabetic, 1-5 chars."""
    return isinstance(t, str) and t.isupper() and t.isalpha() and 1 <= len(t) <= 5


_MAX_RELATED_TICKERS = 8
_REJECTED_SCOPE_KEY_MSG = "scope_key has been removed from the schema; do not emit"
# Separator characters used to tokenize a malformed string-instead-of-list
# related_tickers value into a "did you mean [...]?" hint. Known separator set
# (str.translate + split — deliberately no regex).
_RELATED_TICKERS_SEPARATORS = "_ ,/|-"
_RELATED_TICKERS_SEP_TABLE = str.maketrans(
    {c: " " for c in _RELATED_TICKERS_SEPARATORS}
)

_ATTRIBUTION_REQUIRED_FIELDS = [
    "schema_version", "ticker", "quarter_label", "filed_8k", "accession_8k",
    "attributed_at", "model_version", "pit_mode", "pit_cutoff",
    "pit_boundary_source", "actual_return", "evidence_ledger",
    "primary_driver", "contributing_factors", "feedback",
    "global_observations", "missing_inputs", "data_sources_used",
    "context_bundle_ref", "prediction_result_ref",
]

_FEEDBACK_REQUIRED_FIELDS = [
    "prediction_comparison", "what_worked", "what_failed",
    "why", "predictor_lessons", "data_lessons",
]

_FEEDBACK_CAPS = {
    "what_worked": 2,
    "what_failed": 3,
    "predictor_lessons": 3,
    "data_lessons": 3,
}

_PREDICTION_COMPARISON_REQUIRED = [
    "predicted_direction", "predicted_confidence_score",
    "predicted_move_range_pct", "predicted_key_drivers",
    "actual_direction", "direction_correct",
    "magnitude_error_pct", "comment",
]

_ACTUAL_RETURN_REQUIRED = ["daily_stock_pct", "market_session"]

_VALID_PIT_MODES = {"historical", "live"}
_VALID_PIT_BOUNDARY_SOURCES = {"next_quarter", "live_cycle", "invocation_time"}
_VALID_DIRECTIONS = {"long", "short", "no_call"}
_VALID_ACTUAL_DIRECTIONS = {"long", "short", "flat"}
_VALID_SCOPES = {"sector", "macro", "cross_ticker"}

# v3-only enums and field-length floor (LearnerLoopRevamp.md §5.3 / §5.4 / §8.3)
_REVIEW_VALUES = {"helped", "misled", "outweighed", "missed", "neutral", "unclear"}
_ACTION_VALUES = {"keep", "refine", "retire"}
_LESSON_LABEL_VALUES = {"confirmed", "contradicted", "irrelevant"}
_MIN_LESSON_FIELD_CHARS = 30
_LESSON_STRUCT_FIELDS = ("lesson", "mechanism", "applies_when", "invalid_if")


def validate_attribution_result(payload: dict[str, Any],
                                expected_ticker: str,
                                expected_quarter: str) -> list[str]:
    """Validate learning/result.json against attribution_result.v3.

    Round 6 fresh-start: v3-only. Anything else is rejected with a clear
    message. The PreToolUse hook calls this same function — the wrapper is
    the only schema-version gate.
    """
    sv = payload.get("schema_version")
    if sv != "attribution_result.v3":
        return [
            f"unsupported schema_version: {sv!r} — only attribution_result.v3 "
            f"is accepted (round 6 fresh-start cutover removed v2 read-compat)"
        ]
    return _validate_v3(payload, expected_ticker, expected_quarter)


def _validate_common_core(payload: dict[str, Any],
                          expected_ticker: str,
                          expected_quarter: str) -> list[str]:
    """Schema-version-independent rules. Owned by both v3 and any future
    schema layers. Mirrors the v2 body MINUS the schema_version equality
    check (which the wrapper owns)."""
    errors: list[str] = []

    # ── Required top-level fields ──
    missing = [k for k in _ATTRIBUTION_REQUIRED_FIELDS if k not in payload]
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
        return errors  # bail early, remaining checks would fail

    # ── Ticker / quarter match ──
    if str(payload["ticker"]).upper() != expected_ticker.upper():
        errors.append(f"ticker mismatch: {payload['ticker']} != {expected_ticker}")
    if payload["quarter_label"] != expected_quarter:
        errors.append(f"quarter_label mismatch: {payload['quarter_label']} != {expected_quarter}")

    # ── PIT fields ──
    # Totality: enum membership (`x in SET`) raises TypeError when x is
    # unhashable (list/dict). Guard with isinstance(str) so a malformed
    # learner output produces a validation error rather than a crash, so
    # the orchestrator's H2 informed-retry loop can feed errors back to the
    # LLM rather than crashing the run. Same pattern applied to every
    # enum-membership check in this module (see commit 1.5).
    pit_mode_val = payload["pit_mode"]
    if not isinstance(pit_mode_val, str) or pit_mode_val not in _VALID_PIT_MODES:
        errors.append(f"invalid pit_mode: {pit_mode_val!r}")
    pbs_val = payload["pit_boundary_source"]
    if not isinstance(pbs_val, str) or pbs_val not in _VALID_PIT_BOUNDARY_SOURCES:
        errors.append(f"invalid pit_boundary_source: {pbs_val!r}")
    # PIT consistency: historical requires non-null cutoff, live requires null
    pit_mode = payload["pit_mode"]
    pit_cutoff = payload["pit_cutoff"]
    if pit_mode == "historical" and (pit_cutoff is None or not isinstance(pit_cutoff, str)):
        errors.append("pit_mode is 'historical' but pit_cutoff is null or not a string")
    if pit_mode == "live" and pit_cutoff is not None:
        errors.append(f"pit_mode is 'live' but pit_cutoff is not null: {pit_cutoff}")

    # ── actual_return shape ──
    ar = payload["actual_return"]
    if not isinstance(ar, dict):
        errors.append("actual_return must be an object")
    else:
        for key in _ACTUAL_RETURN_REQUIRED:
            if key not in ar:
                errors.append(f"actual_return missing required field: {key}")
        dsp = ar.get("daily_stock_pct")
        if dsp is not None and not isinstance(dsp, (int, float)):
            errors.append(f"actual_return.daily_stock_pct must be a number, got: {type(dsp).__name__}")
        ms = ar.get("market_session")
        if not isinstance(ms, str) or not ms.strip():
            errors.append("actual_return.market_session must be a non-empty string")

    # ── Evidence ledger (must be non-empty) ──
    ledger = payload["evidence_ledger"]
    if not isinstance(ledger, list) or len(ledger) == 0:
        errors.append("evidence_ledger must be a non-empty array")
    else:
        for i, entry in enumerate(ledger):
            if not isinstance(entry, dict):
                errors.append(f"evidence_ledger[{i}] is not an object")
                continue
            for required_key in ("id", "claim", "value", "source", "date"):
                if required_key not in entry:
                    errors.append(f"evidence_ledger[{i}] missing '{required_key}'")

    # Build ledger_ids once for downstream ref checks. ``isinstance(e["id"], str)``
    # is required for hashability — a non-string id would crash the set
    # comprehension. Non-string ids are caught later as ledger malformation;
    # for now we just exclude them from the resolvable-id set.
    ledger_ids: set[str] = {
        e.get("id") for e in (ledger if isinstance(ledger, list) else [])
        if isinstance(e, dict) and isinstance(e.get("id"), str)
    }

    # ── Evidence refs resolution helper ──
    # Totality: ``ref in ledger_ids`` raises TypeError when ref is unhashable
    # (e.g., dict, list). Guard with isinstance(str) so a malformed
    # evidence_refs entry produces a validation error rather than a crash.
    def _check_refs(obj: dict, label: str) -> None:
        refs = obj.get("evidence_refs", [])
        if not isinstance(refs, list):
            errors.append(f"{label}.evidence_refs must be a list")
            return
        for ref in refs:
            if not isinstance(ref, str):
                errors.append(
                    f"{label}.evidence_refs: item must be a string, "
                    f"got {type(ref).__name__}"
                )
                continue
            if ref not in ledger_ids:
                errors.append(f"{label}.evidence_refs: '{ref}' not found in evidence_ledger")

    # ── Primary driver ──
    pd = payload["primary_driver"]
    if not isinstance(pd, dict):
        errors.append("primary_driver must be an object")
    else:
        for key in ("summary", "category", "evidence_refs"):
            if key not in pd:
                errors.append(f"primary_driver missing '{key}'")
        _check_refs(pd, "primary_driver")

    # ── Contributing factors ──
    cf = payload["contributing_factors"]
    if not isinstance(cf, list):
        errors.append("contributing_factors must be an array")
    elif len(cf) > 3:
        errors.append(f"contributing_factors exceeds cap: {len(cf)} > 3")
    else:
        for i, factor in enumerate(cf):
            if not isinstance(factor, dict):
                errors.append(f"contributing_factors[{i}] is not an object")
                continue
            for key in ("summary", "category", "evidence_refs"):
                if key not in factor:
                    errors.append(f"contributing_factors[{i}] missing '{key}'")
            _check_refs(factor, f"contributing_factors[{i}]")

    # ── Feedback block ──
    fb = payload["feedback"]
    if not isinstance(fb, dict):
        errors.append("feedback must be an object")
    else:
        fb_missing = [k for k in _FEEDBACK_REQUIRED_FIELDS if k not in fb]
        if fb_missing:
            errors.append(f"feedback missing fields: {', '.join(fb_missing)}")

        # Array caps (lists only — element-shape checks live in _validate_v3)
        for field, cap in _FEEDBACK_CAPS.items():
            if field in fb:
                val = fb[field]
                if not isinstance(val, list):
                    errors.append(f"feedback.{field} must be a list")
                elif len(val) > cap:
                    errors.append(f"feedback.{field} exceeds cap: {len(val)} > {cap}")

        # Prediction comparison — validate all required sub-fields
        pc = fb.get("prediction_comparison")
        if pc is None:
            pass  # already caught by fb_missing check
        elif not isinstance(pc, dict):
            errors.append("feedback.prediction_comparison must be an object")
        else:
            pc_missing = [k for k in _PREDICTION_COMPARISON_REQUIRED if k not in pc]
            if pc_missing:
                errors.append(f"prediction_comparison missing fields: {', '.join(pc_missing)}")
            pd_val = pc.get("predicted_direction")
            if not isinstance(pd_val, str) or pd_val not in _VALID_DIRECTIONS:
                errors.append(f"prediction_comparison.predicted_direction invalid: {pd_val!r}")
            ad_val = pc.get("actual_direction")
            if not isinstance(ad_val, str) or ad_val not in _VALID_ACTUAL_DIRECTIONS:
                errors.append(f"prediction_comparison.actual_direction invalid: {ad_val!r}")
            if not isinstance(pc.get("direction_correct"), bool):
                errors.append("prediction_comparison.direction_correct must be a boolean")
            mep = pc.get("magnitude_error_pct")
            if mep is not None and not isinstance(mep, (int, float)):
                errors.append("prediction_comparison.magnitude_error_pct must be a number")
            pcs = pc.get("predicted_confidence_score")
            if pcs is not None and not isinstance(pcs, (int, float)):
                errors.append("prediction_comparison.predicted_confidence_score must be a number")
            pmr = pc.get("predicted_move_range_pct")
            if pmr is not None:
                if not isinstance(pmr, list) or len(pmr) != 2 or not all(isinstance(x, (int, float)) for x in pmr):
                    errors.append("prediction_comparison.predicted_move_range_pct must be a 2-number array")
            pkd = pc.get("predicted_key_drivers")
            if pkd is not None and not isinstance(pkd, list):
                errors.append("prediction_comparison.predicted_key_drivers must be a list")
            cmt = pc.get("comment")
            if cmt is not None and not isinstance(cmt, str):
                errors.append("prediction_comparison.comment must be a string")

        # why field
        why = fb.get("why")
        if why is not None and not isinstance(why, str):
            errors.append("feedback.why must be a string")

    # ── Global observations: scope routing invariants ──
    # Schema v2 amendment (2026-04-17): scope_key REMOVED (rejected on every
    # scope). Structured routing fields: related_tickers (cross_ticker) and
    # target_sector (sector). v3 adds mechanism/applies_when/invalid_if/
    # evidence_refs on top — those checks live in _validate_v3.
    go = payload["global_observations"]
    if not isinstance(go, list):
        errors.append("global_observations must be an array")
    elif len(go) > 3:
        errors.append(f"global_observations exceeds cap: {len(go)} > 3")
    else:
        for i, obs in enumerate(go):
            if not isinstance(obs, dict):
                errors.append(f"global_observations[{i}] is not an object")
                continue
            # ── Required fields: scope + lesson only (scope_key removed) ──
            for key in ("scope", "lesson"):
                if key not in obs:
                    errors.append(f"global_observations[{i}] missing '{key}'")
            scope = obs.get("scope")
            if not isinstance(scope, str) or scope not in _VALID_SCOPES:
                errors.append(f"global_observations[{i}].scope invalid: {scope!r}")

            rt = obs.get("related_tickers")
            ts = obs.get("target_sector")

            # ── scope_key: must NEVER be present (rejected across all scopes) ──
            if "scope_key" in obs:
                errors.append(
                    f"global_observations[{i}].scope_key: {_REJECTED_SCOPE_KEY_MSG}"
                )

            # ── Per-scope routing-field requirements ──
            if scope == "cross_ticker":
                if not isinstance(rt, list) or not rt:
                    errors.append(
                        f"global_observations[{i}].related_tickers must be a "
                        f"non-empty list for cross_ticker scope"
                    )
                    # "Did you mean [...]?" hint if a string was passed instead
                    # of a list. REGEX-FREE: str.translate + split on known
                    # separator set only.
                    if isinstance(rt, str):
                        normalized = rt.upper().translate(_RELATED_TICKERS_SEP_TABLE)
                        tokens = [t for t in normalized.split() if _ok_ticker(t)]
                        if tokens:
                            errors.append(
                                f"global_observations[{i}].related_tickers: "
                                f"did you mean {tokens!r}?"
                            )
                else:
                    if len(rt) > _MAX_RELATED_TICKERS:
                        errors.append(
                            f"global_observations[{i}].related_tickers exceeds "
                            f"cap {_MAX_RELATED_TICKERS} (got {len(rt)})"
                        )
                    bad = [t for t in rt if not _ok_ticker(t)]
                    if bad:
                        errors.append(
                            f"global_observations[{i}].related_tickers contains "
                            f"invalid tickers (must be uppercase alphabetic, "
                            f"1-5 chars): {bad}"
                        )
                    # Validator-authoritative dedupe (writer does NOT dedupe).
                    # Totality: ``set(rt)`` would crash if rt contained an
                    # unhashable element (e.g., a nested list). The bad-element
                    # check above already flags non-string entries; dedupe only
                    # cares about the string-typed subset.
                    str_tickers = [t for t in rt if isinstance(t, str)]
                    if len(set(str_tickers)) != len(str_tickers):
                        errors.append(
                            f"global_observations[{i}].related_tickers contains "
                            f"duplicates"
                        )
                # Key-presence check (amendment 2026-04-17): contract says the
                # field "MUST NOT be present". `is not None` would silently
                # permit an explicit-null injection like "target_sector": null
                # — which is still a form of presence. Use `in obs` so null
                # is also rejected, matching the scope_key check above.
                if "target_sector" in obs:
                    errors.append(
                        f"global_observations[{i}].target_sector must not be "
                        f"present for cross_ticker scope"
                    )

            elif scope == "sector":
                if not isinstance(ts, str) or ts not in CANONICAL_SECTORS:
                    # "Did you mean ..." hint via stdlib difflib (no new deps).
                    hint = ""
                    if isinstance(ts, str):
                        suggestions = get_close_matches(
                            ts, CANONICAL_SECTORS, n=2, cutoff=0.5
                        )
                        if suggestions:
                            hint = (
                                f" (did you mean: "
                                f"{', '.join(repr(s) for s in suggestions)}?)"
                            )
                    errors.append(
                        f"global_observations[{i}].target_sector must be one "
                        f"of {sorted(CANONICAL_SECTORS)} (got {ts!r}){hint}"
                    )
                # Key-presence rejection (see cross_ticker comment above).
                if "related_tickers" in obs:
                    errors.append(
                        f"global_observations[{i}].related_tickers must not be "
                        f"present for sector scope"
                    )

            elif scope == "macro":
                # Key-presence rejection (see cross_ticker comment above).
                if "related_tickers" in obs:
                    errors.append(
                        f"global_observations[{i}].related_tickers must not be "
                        f"present for macro scope"
                    )
                if "target_sector" in obs:
                    errors.append(
                        f"global_observations[{i}].target_sector must not be "
                        f"present for macro scope"
                    )

    # ── Simple type checks ──
    if not isinstance(payload["missing_inputs"], list):
        errors.append("missing_inputs must be an array")
    if not isinstance(payload["data_sources_used"], list):
        errors.append("data_sources_used must be an array")

    # ── Ref fields (must be canonical relative strings) ──
    if payload.get("context_bundle_ref") != "context_bundle.json":
        errors.append(f"context_bundle_ref must be 'context_bundle.json', got: {payload.get('context_bundle_ref')}")
    if payload.get("prediction_result_ref") != "prediction/result.json":
        errors.append(f"prediction_result_ref must be 'prediction/result.json', got: {payload.get('prediction_result_ref')}")

    return errors


def _validate_v3(payload: dict[str, Any],
                 expected_ticker: str,
                 expected_quarter: str) -> list[str]:
    """v3 additions: structured predictor_lessons / global_observations
    (LearnerLoopRevamp.md §8.3 + N3); lesson_audit shape (D8 + B3 + #3).

    Layered on top of ``_validate_common_core`` — common-core failures
    surface first, then v3-specific checks. The common-core fast-bail on
    missing top-level fields means an empty ``ledger_ids`` set never
    reaches us here (we'd already have an error list to return)."""
    errors = _validate_common_core(payload, expected_ticker, expected_quarter)

    # Build ledger_ids for v3-side ref checks. Mirror common-core hardening:
    # ledger must be a list (defensive — non-list would crash iteration);
    # only string ids enter the set (set() requires hashable elements, and
    # a non-string id is itself a malformation flagged elsewhere).
    ledger_raw = payload.get("evidence_ledger")
    ledger = ledger_raw if isinstance(ledger_raw, list) else []
    ledger_ids: set[str] = {
        e.get("id") for e in ledger
        if isinstance(e, dict) and isinstance(e.get("id"), str)
    }

    def _refs_nonempty_resolve(refs: object, label: str) -> None:
        """Validate evidence_refs is non-empty and all IDs resolve.
        Per N3 (predictor_lessons / global_observations) and #3
        (lesson_audit, replacement_lesson). Totality: a non-string ref
        produces a typed error rather than crashing the set membership
        check (unhashable types raise TypeError on ``ref in set``)."""
        if not isinstance(refs, list) or not refs:
            errors.append(f"{label}.evidence_refs must be a non-empty list")
            return
        for ref in refs:
            if not isinstance(ref, str):
                errors.append(
                    f"{label}.evidence_refs: item must be a string, "
                    f"got {type(ref).__name__}"
                )
                continue
            if ref not in ledger_ids:
                errors.append(f"{label}.evidence_refs: '{ref}' not found in evidence_ledger")

    def _check_lesson_struct(d: object, label: str) -> None:
        """Each of lesson/mechanism/applies_when/invalid_if must be a string
        with ≥30 non-whitespace chars."""
        if not isinstance(d, dict):
            errors.append(f"{label} must be an object")
            return
        for field in _LESSON_STRUCT_FIELDS:
            v = d.get(field)
            if not isinstance(v, str) or len(v.strip()) < _MIN_LESSON_FIELD_CHARS:
                errors.append(
                    f"{label}.{field} must be a non-empty string ≥{_MIN_LESSON_FIELD_CHARS} chars"
                )

    # ── Structured predictor_lessons (v3 — D17 + N3) ──
    # Totality: ``payload.get("feedback") or {}`` returns "bad" when feedback
    # is the truthy non-dict string "bad", and ``"bad".get(...)`` crashes.
    # Common-core already errored on the non-dict feedback; here we just
    # skip v3-feedback checks rather than re-error or crash.
    fb_raw = payload.get("feedback")
    fb = fb_raw if isinstance(fb_raw, dict) else {}
    pl = fb.get("predictor_lessons") or []
    if isinstance(pl, list):
        for i, lesson in enumerate(pl):
            label = f"feedback.predictor_lessons[{i}]"
            if not isinstance(lesson, dict):
                errors.append(f"{label} must be an object in v3 (was list[str] in v2)")
                continue
            _check_lesson_struct(lesson, label)
            _refs_nonempty_resolve(lesson.get("evidence_refs"), label)

    # ── Structured global_observations (v3 — N3) ──
    go = payload.get("global_observations") or []
    if isinstance(go, list):
        for i, obs in enumerate(go):
            label = f"global_observations[{i}]"
            if not isinstance(obs, dict):
                # already flagged in common-core
                continue
            _check_lesson_struct(obs, label)
            _refs_nonempty_resolve(obs.get("evidence_refs"), label)

    # ── lesson_audit (v3 — D8 full coverage; structurally optional at hook
    # level per §8.2; D19 enforces count alignment in the orchestrator) ──
    audits = payload.get("lesson_audit", [])
    if not isinstance(audits, list):
        errors.append("lesson_audit must be a list")
    else:
        for i, audit in enumerate(audits):
            label = f"lesson_audit[{i}]"
            if not isinstance(audit, dict):
                errors.append(f"{label} must be an object")
                continue

            # Required fields — presence
            required = (
                "lesson_index", "lesson_text", "predictor_label",
                "was_cited", "review", "action", "comment", "evidence_refs",
            )
            for field in required:
                if field not in audit:
                    errors.append(f"{label} missing required field: {field}")

            # Type / enum checks (only when the field is present)
            if "lesson_index" in audit and not isinstance(audit["lesson_index"], int):
                errors.append(f"{label}.lesson_index must be an int")
            if "lesson_text" in audit and not isinstance(audit["lesson_text"], str):
                errors.append(f"{label}.lesson_text must be a string")
            # Enum membership checks — guard isinstance(str) BEFORE ``x in SET``
            # so malformed values (list, dict, None, etc.) produce a typed
            # error rather than a TypeError("unhashable type") crash.
            if "predictor_label" in audit:
                pl_val = audit["predictor_label"]
                if not isinstance(pl_val, str) or pl_val not in _LESSON_LABEL_VALUES:
                    errors.append(
                        f"{label}.predictor_label must be one of "
                        f"{sorted(_LESSON_LABEL_VALUES)} (got {pl_val!r})"
                    )
            if "was_cited" in audit and not isinstance(audit["was_cited"], bool):
                errors.append(f"{label}.was_cited must be a bool")
            if "review" in audit:
                rv_val = audit["review"]
                if not isinstance(rv_val, str) or rv_val not in _REVIEW_VALUES:
                    errors.append(
                        f"{label}.review must be one of "
                        f"{sorted(_REVIEW_VALUES)} (got {rv_val!r})"
                    )
            if "action" in audit:
                ac_val = audit["action"]
                if not isinstance(ac_val, str) or ac_val not in _ACTION_VALUES:
                    errors.append(
                        f"{label}.action must be one of "
                        f"{sorted(_ACTION_VALUES)} (got {ac_val!r})"
                    )
            if "comment" in audit and not isinstance(audit["comment"], str):
                errors.append(f"{label}.comment must be a string")

            # evidence_refs: non-empty + IDs resolve (B3 + user clarification #3)
            if "evidence_refs" in audit:
                _refs_nonempty_resolve(audit["evidence_refs"], label)

            # action="refine" requires a structurally-valid replacement_lesson
            if audit.get("action") == "refine":
                rl_label = f"{label}.replacement_lesson"
                rl = audit.get("replacement_lesson")
                if rl is None:
                    errors.append(
                        f"{label}: action='refine' requires replacement_lesson "
                        f"with lesson + mechanism + applies_when + invalid_if + evidence_refs"
                    )
                elif not isinstance(rl, dict):
                    errors.append(f"{rl_label} must be an object")
                else:
                    _check_lesson_struct(rl, rl_label)
                    _refs_nonempty_resolve(rl.get("evidence_refs"), rl_label)

    return errors
