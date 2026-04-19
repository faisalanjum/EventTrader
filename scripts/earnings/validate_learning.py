"""Standalone attribution_result.v2 validator — zero external dependencies.

This is the SINGLE CANONICAL validator. Both the orchestrator Python and the
PreToolUse hook import from here. Only stdlib imports — no Neo4j, no builders,
no SDK. This ensures the hook never fails-open due to missing dependencies.

Schema invariants enforced on ``global_observations[]`` (amendment 2026-04-17,
per .claude/plans/learner.md Appendix A):

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


def validate_attribution_result(payload: dict[str, Any],
                                expected_ticker: str,
                                expected_quarter: str) -> list[str]:
    """Validate learning/result.json (renamed from attribution/ per obsidian_thinking.md) against the attribution_result.v2 contract.

    Returns a list of error strings. Empty list = valid.
    This is the SINGLE CANONICAL validator — the PreToolUse hook calls it too.
    """
    errors: list[str] = []

    # ── Required top-level fields ──
    missing = [k for k in _ATTRIBUTION_REQUIRED_FIELDS if k not in payload]
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
        return errors  # bail early, remaining checks would fail

    # ── Schema version ──
    if payload["schema_version"] != "attribution_result.v2":
        errors.append(f"unexpected schema_version: {payload['schema_version']}")

    # ── Ticker / quarter match ──
    if str(payload["ticker"]).upper() != expected_ticker.upper():
        errors.append(f"ticker mismatch: {payload['ticker']} != {expected_ticker}")
    if payload["quarter_label"] != expected_quarter:
        errors.append(f"quarter_label mismatch: {payload['quarter_label']} != {expected_quarter}")

    # ── PIT fields ──
    if payload["pit_mode"] not in _VALID_PIT_MODES:
        errors.append(f"invalid pit_mode: {payload['pit_mode']}")
    if payload["pit_boundary_source"] not in _VALID_PIT_BOUNDARY_SOURCES:
        errors.append(f"invalid pit_boundary_source: {payload['pit_boundary_source']}")
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
        ledger_ids: set[str] = set()
    else:
        ledger_ids = set()
        for i, entry in enumerate(ledger):
            if not isinstance(entry, dict):
                errors.append(f"evidence_ledger[{i}] is not an object")
                continue
            for required_key in ("id", "claim", "value", "source", "date"):
                if required_key not in entry:
                    errors.append(f"evidence_ledger[{i}] missing '{required_key}'")
            if "id" in entry:
                ledger_ids.add(entry["id"])

    # ── Evidence refs resolution helper ──
    def _check_refs(obj: dict, label: str) -> None:
        refs = obj.get("evidence_refs", [])
        if not isinstance(refs, list):
            errors.append(f"{label}.evidence_refs must be a list")
            return
        for ref in refs:
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

        # Array caps
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
            if pc.get("predicted_direction") not in _VALID_DIRECTIONS:
                errors.append(f"prediction_comparison.predicted_direction invalid: {pc.get('predicted_direction')}")
            if pc.get("actual_direction") not in _VALID_ACTUAL_DIRECTIONS:
                errors.append(f"prediction_comparison.actual_direction invalid: {pc.get('actual_direction')}")
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

    # ── Global observations ──
    # Schema-v2 amendment (2026-04-17): scope_key REMOVED (rejected on every
    # scope). Structured routing fields: related_tickers (cross_ticker) and
    # target_sector (sector). See module docstring for full invariants.
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
            if scope not in _VALID_SCOPES:
                errors.append(f"global_observations[{i}].scope invalid: {scope}")

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
                    # Validator-authoritative dedupe (writer does NOT dedupe):
                    if len(set(rt)) != len(rt):
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
    if payload.get("context_bundle_ref") != "prediction/context_bundle.json":
        errors.append(f"context_bundle_ref must be 'prediction/context_bundle.json', got: {payload.get('context_bundle_ref')}")
    if payload.get("prediction_result_ref") != "prediction/result.json":
        errors.append(f"prediction_result_ref must be 'prediction/result.json', got: {payload.get('prediction_result_ref')}")

    return errors
