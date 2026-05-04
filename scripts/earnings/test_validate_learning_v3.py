#!/usr/bin/env python3
"""attribution_result.v3 validator tests (LearnerLoopRevamp.md §8.3).

Replaces test_validate_attribution.py (v2 dispatch) — round 6 fresh-start
cutover removed v2 read-compat. Coverage:

  * Schema-version dispatch (v3-only; non-v3 rejected loudly)
  * Common-core scope-routing invariants ported from V1–V24 (still apply
    in v3; unchanged)
  * v3 structured ``predictor_lessons`` (D17 + N3): 4 fields × ≥30 chars +
    ``evidence_refs`` non-empty + IDs resolve
  * v3 structured ``global_observations`` (N3): same rules layered on top
    of common-core scope-routing
  * v3 ``lesson_audit[]`` shape (D8 + B3 + user clarification #3): full
    enum coverage, ``evidence_refs`` non-empty + IDs resolve,
    ``replacement_lesson`` on ``action="refine"``
  * Hook-level structural-optionality of ``lesson_audit`` (D19 enforces
    coverage at the orchestrator)
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root (config.*)
sys.path.insert(0, str(Path(__file__).resolve().parent))       # this dir

from validate_learning import validate_attribution_result


# ────────────────────────────────────────────────────────────────────────
# Skeleton helpers
# ────────────────────────────────────────────────────────────────────────

# Long-enough strings for the ≥30-char structured-field requirement.
_LONG = "x" * 40
_LONG2 = "y" * 40
_LONG3 = "z" * 40
_LONG4 = "w" * 40


def _global_obs(scope: str, **overrides):
    """Build a v3-shape global_observations entry. Defaults to a sector-scope
    entry with all required structured fields populated. Tests override
    fields as needed (or ``__delete__=[fields]`` to drop fields)."""
    base = {
        "scope": scope,
        "lesson": _LONG,
        "mechanism": _LONG2,
        "applies_when": _LONG3,
        "invalid_if": _LONG4,
        "evidence_refs": ["E1"],
    }
    if scope == "sector":
        base["target_sector"] = "Technology"
    elif scope == "cross_ticker":
        base["related_tickers"] = ["MSFT"]
    drops = overrides.pop("__delete__", [])
    base.update(overrides)
    for k in drops:
        base.pop(k, None)
    return base


def _predictor_lesson(**overrides):
    """Build a v3-shape predictor_lessons entry (structured dict)."""
    base = {
        "lesson": _LONG,
        "mechanism": _LONG2,
        "applies_when": _LONG3,
        "invalid_if": _LONG4,
        "evidence_refs": ["E1"],
    }
    drops = overrides.pop("__delete__", [])
    base.update(overrides)
    for k in drops:
        base.pop(k, None)
    return base


def _lesson_audit(idx: int = 0, **overrides):
    """Build a v3-shape lesson_audit entry. Defaults to a helped/keep audit
    on a confirmed/cited prior lesson at index 0."""
    base = {
        "lesson_index": idx,
        "lesson_text": "prior lesson body verbatim",
        "predictor_label": "confirmed",
        "was_cited": True,
        "review": "helped",
        "action": "keep",
        "comment": "evidence aligned with outcome",
        "evidence_refs": ["E1"],
    }
    drops = overrides.pop("__delete__", [])
    base.update(overrides)
    for k in drops:
        base.pop(k, None)
    return base


def _replacement(**overrides):
    """Build a v3-shape replacement_lesson dict for action=refine audits."""
    base = {
        "lesson": "refined " + _LONG,
        "mechanism": "refined " + _LONG2,
        "applies_when": "refined " + _LONG3,
        "invalid_if": "refined " + _LONG4,
        "evidence_refs": ["E1"],
    }
    drops = overrides.pop("__delete__", [])
    base.update(overrides)
    for k in drops:
        base.pop(k, None)
    return base


def _skeleton(global_observations=None,
              predictor_lessons=None,
              lesson_audit=None):
    """Minimal-valid attribution_result.v3 skeleton."""
    payload = {
        "schema_version": "attribution_result.v3",
        "ticker": "AAPL",
        "quarter_label": "Q1_FY2025",
        "filed_8k": "2025-05-01T16:30:00-04:00",
        "accession_8k": "0000320193-25-000055",
        "attributed_at": "2026-04-17T12:00:00-04:00",
        "model_version": "claude-opus-4-7",
        "pit_mode": "historical",
        "pit_cutoff": "2025-07-31T16:00:00-04:00",
        "pit_boundary_source": "next_quarter",
        "actual_return": {"daily_stock_pct": -5.28, "market_session": "after_hours"},
        "evidence_ledger": [
            {"id": "E1", "claim": "demo", "value": "x", "source": "test", "date": "2025-05-01"}
        ],
        "primary_driver": {
            "summary": "demo",
            "category": "guidance_change",
            "evidence_refs": ["E1"],
        },
        "contributing_factors": [],
        "feedback": {
            "prediction_comparison": {
                "predicted_direction": "long",
                "predicted_confidence_score": 50,
                "predicted_move_range_pct": [1.0, 3.0],
                "predicted_key_drivers": ["demo"],
                "actual_direction": "short",
                "direction_correct": False,
                "magnitude_error_pct": 6.28,
                "comment": "demo",
            },
            "what_worked": [],
            "what_failed": [],
            "why": "demo",
            "predictor_lessons": predictor_lessons if predictor_lessons is not None else [],
            "data_lessons": [],
        },
        "global_observations": global_observations if global_observations is not None else [],
        "missing_inputs": [],
        "data_sources_used": ["test"],
        "context_bundle_ref": "context_bundle.json",
        "prediction_result_ref": "prediction/result.json",
    }
    if lesson_audit is not None:
        payload["lesson_audit"] = lesson_audit
    return payload


def _validate(payload):
    return validate_attribution_result(payload, "AAPL", "Q1_FY2025")


# ────────────────────────────────────────────────────────────────────────
# Schema-version dispatch
# ────────────────────────────────────────────────────────────────────────

class SchemaVersionDispatchTests(unittest.TestCase):
    def test_v3_valid_passes(self):
        self.assertEqual(_validate(_skeleton()), [])

    def test_v2_rejected(self):
        payload = _skeleton()
        payload["schema_version"] = "attribution_result.v2"
        errors = _validate(payload)
        self.assertEqual(len(errors), 1)
        self.assertIn("unsupported schema_version", errors[0])
        self.assertIn("attribution_result.v3", errors[0])

    def test_missing_schema_version_rejected(self):
        payload = _skeleton()
        del payload["schema_version"]
        errors = _validate(payload)
        self.assertEqual(len(errors), 1)
        self.assertIn("unsupported schema_version", errors[0])

    def test_unknown_schema_version_rejected(self):
        payload = _skeleton()
        payload["schema_version"] = "attribution_result.v99"
        errors = _validate(payload)
        self.assertTrue(any("unsupported schema_version" in e for e in errors))


# ────────────────────────────────────────────────────────────────────────
# Common-core scope-routing invariants (ported from removed
# test_validate_attribution.py V1–V24)
# ────────────────────────────────────────────────────────────────────────

class ScopeRoutingTests(unittest.TestCase):
    """Pure ports — these rules live in _validate_common_core and apply to
    v3 just as they did to v2. Test entries use v3-shape global_obs entries."""

    # ── V1: zero global_observations ──
    def test_V1_valid_no_globals(self):
        self.assertEqual(_validate(_skeleton([])), [])

    # ── V2: cross_ticker valid ──
    def test_V2_cross_ticker_valid(self):
        errors = _validate(_skeleton([_global_obs("cross_ticker")]))
        self.assertEqual(errors, [], f"expected no errors, got {errors}")

    # ── V3: cross_ticker empty related_tickers ──
    def test_V3_cross_ticker_empty_list(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", related_tickers=[])
        ]))
        self.assertTrue(any("related_tickers" in e and "non-empty" in e for e in errors), errors)

    # ── V4: cross_ticker missing related_tickers ──
    def test_V4_cross_ticker_missing_rt(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", __delete__=["related_tickers"])
        ]))
        self.assertTrue(any("related_tickers" in e for e in errors), errors)

    # ── V5: cross_ticker lowercase tickers ──
    def test_V5_cross_ticker_lowercase(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", related_tickers=["msft"])
        ]))
        self.assertTrue(any("invalid tickers" in e for e in errors), errors)

    # ── V6: cross_ticker too-long ticker ──
    def test_V6_cross_ticker_toolong(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", related_tickers=["TOOLONG"])
        ]))
        self.assertTrue(any("invalid tickers" in e for e in errors), errors)

    # ── V7: cross_ticker duplicates ──
    def test_V7_cross_ticker_duplicates(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", related_tickers=["MSFT", "MSFT"])
        ]))
        self.assertTrue(any("duplicates" in e for e in errors), errors)

    # ── V8: cross_ticker exceeds 8-ticker cap ──
    def test_V8_cross_ticker_cap(self):
        nine = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", related_tickers=nine)
        ]))
        self.assertTrue(any("exceeds cap" in e for e in errors), errors)

    # ── V9: cross_ticker with target_sector present ──
    def test_V9_cross_ticker_has_target_sector(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", target_sector="Technology")
        ]))
        self.assertTrue(any("target_sector must not be present" in e and "cross_ticker" in e for e in errors), errors)

    # ── V10: sector valid ──
    def test_V10_sector_valid(self):
        errors = _validate(_skeleton([_global_obs("sector")]))
        self.assertEqual(errors, [], f"expected no errors, got {errors}")

    # ── V11: sector non-canonical ──
    def test_V11_sector_noncanonical(self):
        errors = _validate(_skeleton([
            _global_obs("sector", target_sector="semiconductors")
        ]))
        self.assertTrue(any("target_sector must be one of" in e for e in errors), errors)

    # ── V12: sector missing target_sector ──
    def test_V12_sector_missing_target(self):
        errors = _validate(_skeleton([
            _global_obs("sector", __delete__=["target_sector"])
        ]))
        self.assertTrue(any("target_sector must be one of" in e for e in errors), errors)

    # ── V13: sector with related_tickers present ──
    def test_V13_sector_has_related_tickers(self):
        errors = _validate(_skeleton([
            _global_obs("sector", related_tickers=["AAPL"])
        ]))
        self.assertTrue(any("related_tickers must not be present" in e and "sector" in e for e in errors), errors)

    # ── V14: macro valid (neither routing field) ──
    def test_V14_macro_valid(self):
        errors = _validate(_skeleton([_global_obs("macro")]))
        self.assertEqual(errors, [], f"expected no errors, got {errors}")

    # ── V15: macro with related_tickers ──
    def test_V15_macro_has_related_tickers(self):
        errors = _validate(_skeleton([
            _global_obs("macro", related_tickers=["AAPL"])
        ]))
        self.assertTrue(any("related_tickers must not be present" in e and "macro" in e for e in errors), errors)

    # ── V16: macro with target_sector ──
    def test_V16_macro_has_target_sector(self):
        errors = _validate(_skeleton([
            _global_obs("macro", target_sector="Technology")
        ]))
        self.assertTrue(any("target_sector must not be present" in e and "macro" in e for e in errors), errors)

    # ── V17: top-level missing-field rule still fires ──
    def test_V17_existing_rules_still_fire(self):
        bad = _skeleton([])
        del bad["evidence_ledger"]
        errors = _validate(bad)
        self.assertTrue(any("evidence_ledger" in e for e in errors), errors)

    # ── V18: unknown scope ──
    def test_V18_unknown_scope(self):
        errors = _validate(_skeleton([_global_obs("foo")]))
        self.assertTrue(any(".scope invalid" in e for e in errors), errors)

    # ── V19: scope_key rejected across all scopes ──
    def test_V19_scope_key_rejected_on_cross_ticker(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", scope_key="anything")
        ]))
        self.assertTrue(any("scope_key has been removed" in e for e in errors), errors)

    def test_V19_scope_key_rejected_on_sector(self):
        errors = _validate(_skeleton([
            _global_obs("sector", scope_key="anything")
        ]))
        self.assertTrue(any("scope_key has been removed" in e for e in errors), errors)

    def test_V19_scope_key_rejected_on_macro(self):
        errors = _validate(_skeleton([
            _global_obs("macro", scope_key="anything")
        ]))
        self.assertTrue(any("scope_key has been removed" in e for e in errors), errors)

    # ── V21–V24: null-injection rejection (key-presence vs is-not-None) ──
    def test_V21_macro_null_related_tickers_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("macro", related_tickers=None)
        ]))
        self.assertTrue(
            any("related_tickers must not be present" in e and "macro" in e for e in errors),
            errors,
        )

    def test_V22_macro_null_target_sector_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("macro", target_sector=None)
        ]))
        self.assertTrue(
            any("target_sector must not be present" in e and "macro" in e for e in errors),
            errors,
        )

    def test_V23_sector_null_related_tickers_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("sector", related_tickers=None)
        ]))
        self.assertTrue(
            any("related_tickers must not be present" in e and "sector" in e for e in errors),
            errors,
        )

    def test_V24_cross_ticker_null_target_sector_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", target_sector=None)
        ]))
        self.assertTrue(
            any("target_sector must not be present" in e and "cross_ticker" in e for e in errors),
            errors,
        )

    # ── Ref-field regression (post-2026-04-17 path migration) ──
    def test_context_bundle_ref_canonical(self):
        self.assertEqual(_validate(_skeleton()), [])

    def test_context_bundle_ref_pre_migration_value_rejected(self):
        payload = _skeleton()
        payload["context_bundle_ref"] = "prediction/context_bundle.json"
        errors = _validate(payload)
        self.assertTrue(any("context_bundle_ref" in e for e in errors), errors)

    # ── Did-you-mean hints ──
    def test_did_you_mean_for_string_rt(self):
        errors = _validate(_skeleton([
            _global_obs("cross_ticker", related_tickers="ROST_BURL")
        ]))
        self.assertTrue(any("non-empty" in e for e in errors), errors)
        self.assertTrue(any("did you mean" in e and "ROST" in e and "BURL" in e for e in errors), errors)

    def test_did_you_mean_for_near_miss_target_sector(self):
        errors = _validate(_skeleton([
            _global_obs("sector", target_sector="Technolgy")  # typo
        ]))
        self.assertTrue(any("did you mean" in e and "Technology" in e for e in errors), errors)


# ────────────────────────────────────────────────────────────────────────
# v3 structured predictor_lessons (D17 + N3)
# ────────────────────────────────────────────────────────────────────────

class StructuredPredictorLessonsTests(unittest.TestCase):
    def test_valid_structured_lesson_passes(self):
        errors = _validate(_skeleton(predictor_lessons=[_predictor_lesson()]))
        self.assertEqual(errors, [], errors)

    def test_predictor_lesson_string_in_v3_rejected(self):
        # v3 requires dict (was list[str] in v2); a bare string entry must fail.
        errors = _validate(_skeleton(predictor_lessons=["bare string lesson"]))
        self.assertTrue(any("predictor_lessons[0]" in e and "object" in e for e in errors), errors)

    def test_each_struct_field_required_lesson(self):
        for field in ("lesson", "mechanism", "applies_when", "invalid_if"):
            with self.subTest(field=field):
                errors = _validate(_skeleton(predictor_lessons=[
                    _predictor_lesson(__delete__=[field])
                ]))
                self.assertTrue(any(f"predictor_lessons[0].{field}" in e for e in errors), errors)

    def test_struct_field_too_short_rejected(self):
        errors = _validate(_skeleton(predictor_lessons=[
            _predictor_lesson(mechanism="too short")
        ]))
        self.assertTrue(any("predictor_lessons[0].mechanism" in e and "30 chars" in e for e in errors), errors)

    def test_struct_field_non_string_rejected(self):
        errors = _validate(_skeleton(predictor_lessons=[
            _predictor_lesson(applies_when=["list", "instead"])
        ]))
        self.assertTrue(any("predictor_lessons[0].applies_when" in e for e in errors), errors)

    def test_evidence_refs_missing_rejected(self):
        errors = _validate(_skeleton(predictor_lessons=[
            _predictor_lesson(__delete__=["evidence_refs"])
        ]))
        self.assertTrue(any("predictor_lessons[0].evidence_refs" in e and "non-empty" in e for e in errors), errors)

    def test_evidence_refs_empty_list_rejected(self):
        errors = _validate(_skeleton(predictor_lessons=[
            _predictor_lesson(evidence_refs=[])
        ]))
        self.assertTrue(any("predictor_lessons[0].evidence_refs" in e and "non-empty" in e for e in errors), errors)


# ────────────────────────────────────────────────────────────────────────
# v3 structured global_observations (N3) — content layer over scope routing
# ────────────────────────────────────────────────────────────────────────

class StructuredGlobalObservationsTests(unittest.TestCase):
    def test_each_struct_field_required(self):
        for field in ("lesson", "mechanism", "applies_when", "invalid_if"):
            with self.subTest(field=field):
                errors = _validate(_skeleton([
                    _global_obs("sector", __delete__=[field])
                ]))
                self.assertTrue(any(f"global_observations[0].{field}" in e for e in errors), errors)

    def test_struct_field_too_short_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("sector", invalid_if="short")
        ]))
        self.assertTrue(any("global_observations[0].invalid_if" in e and "30 chars" in e for e in errors), errors)

    def test_evidence_refs_missing_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("sector", __delete__=["evidence_refs"])
        ]))
        self.assertTrue(any("global_observations[0].evidence_refs" in e and "non-empty" in e for e in errors), errors)

    def test_evidence_refs_empty_list_rejected(self):
        errors = _validate(_skeleton([
            _global_obs("sector", evidence_refs=[])
        ]))
        self.assertTrue(any("global_observations[0].evidence_refs" in e and "non-empty" in e for e in errors), errors)


# ────────────────────────────────────────────────────────────────────────
# v3 lesson_audit shape (D8 + B3 + #3)
# ────────────────────────────────────────────────────────────────────────

class LessonAuditShapeTests(unittest.TestCase):
    def test_lesson_audit_absent_passes(self):
        # Hook-level: lesson_audit is structurally optional. D19 enforces
        # coverage in the orchestrator (with prediction-file access).
        self.assertEqual(_validate(_skeleton()), [])

    def test_lesson_audit_empty_list_passes(self):
        self.assertEqual(_validate(_skeleton(lesson_audit=[])), [])

    def test_lesson_audit_must_be_list(self):
        errors = _validate(_skeleton(lesson_audit={"not": "list"}))
        self.assertTrue(any("lesson_audit must be a list" in e for e in errors), errors)

    def test_audit_entry_must_be_dict(self):
        errors = _validate(_skeleton(lesson_audit=["string"]))
        self.assertTrue(any("lesson_audit[0]" in e and "object" in e for e in errors), errors)

    def test_each_required_field_checked(self):
        required = ("lesson_index", "lesson_text", "predictor_label",
                    "was_cited", "review", "action", "comment", "evidence_refs")
        for field in required:
            with self.subTest(field=field):
                errors = _validate(_skeleton(
                    lesson_audit=[_lesson_audit(__delete__=[field])]
                ))
                self.assertTrue(any(f"lesson_audit[0]" in e and field in e for e in errors), errors)

    def test_lesson_index_must_be_int(self):
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(lesson_index="zero")]
        ))
        self.assertTrue(any("lesson_index must be an int" in e for e in errors), errors)

    def test_lesson_text_must_be_string(self):
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(lesson_text=123)]
        ))
        self.assertTrue(any("lesson_text must be a string" in e for e in errors), errors)

    def test_was_cited_must_be_bool(self):
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(was_cited="true")]
        ))
        self.assertTrue(any("was_cited must be a bool" in e for e in errors), errors)

    def test_review_enum_invalid_rejected(self):
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(review="great")]
        ))
        self.assertTrue(any("review must be one of" in e for e in errors), errors)

    def test_action_enum_invalid_rejected(self):
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(action="delete")]
        ))
        self.assertTrue(any("action must be one of" in e for e in errors), errors)

    def test_predictor_label_enum_invalid_rejected(self):
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(predictor_label="maybe")]
        ))
        self.assertTrue(any("predictor_label must be one of" in e for e in errors), errors)

    def test_comment_must_be_string(self):
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(comment=42)]
        ))
        self.assertTrue(any("comment must be a string" in e for e in errors), errors)

    def test_evidence_refs_empty_list_rejected_on_audit(self):
        # User clarification #3: even neutral/unclear audits must cite ≥1 ID.
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(evidence_refs=[])]
        ))
        self.assertTrue(any("lesson_audit[0].evidence_refs" in e and "non-empty" in e for e in errors), errors)

    def test_evidence_refs_required_on_neutral_audit(self):
        # Same rule: neutral verdict must still cite the ledger entries that
        # support the not-applicable conclusion (per #3 + SKILL.md §9.1).
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(review="neutral", action="keep", evidence_refs=[])
        ]))
        self.assertTrue(any("lesson_audit[0].evidence_refs" in e and "non-empty" in e for e in errors), errors)


# ────────────────────────────────────────────────────────────────────────
# v3 lesson_audit positive coverage (every enum value, both boolean states)
# ────────────────────────────────────────────────────────────────────────

class LessonAuditPositiveTests(unittest.TestCase):
    def test_all_review_action_combos_pass(self):
        combos = [
            ("helped", "keep"),
            ("misled", "refine"),  # refine needs replacement_lesson
            ("misled", "retire"),
            ("outweighed", "keep"),
            ("missed", "refine"),
            ("neutral", "keep"),
            ("unclear", "keep"),
        ]
        for review, action in combos:
            with self.subTest(review=review, action=action):
                kw = {"review": review, "action": action}
                if action == "refine":
                    kw["replacement_lesson"] = _replacement()
                errors = _validate(_skeleton(lesson_audit=[_lesson_audit(**kw)]))
                self.assertEqual(errors, [], f"{review}/{action}: {errors}")

    def test_all_predictor_labels_pass(self):
        for label in ("confirmed", "contradicted", "irrelevant"):
            with self.subTest(label=label):
                errors = _validate(_skeleton(
                    lesson_audit=[_lesson_audit(predictor_label=label)]
                ))
                self.assertEqual(errors, [], f"{label}: {errors}")

    def test_was_cited_false_passes(self):
        errors = _validate(_skeleton(
            lesson_audit=[_lesson_audit(was_cited=False, predictor_label="irrelevant",
                                         review="neutral", action="keep")]
        ))
        self.assertEqual(errors, [], errors)


# ────────────────────────────────────────────────────────────────────────
# v3 replacement_lesson (action=refine)
# ────────────────────────────────────────────────────────────────────────

class ReplacementLessonTests(unittest.TestCase):
    def test_refine_without_replacement_rejected(self):
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(review="misled", action="refine")
        ]))
        self.assertTrue(any("replacement_lesson" in e for e in errors), errors)

    def test_refine_replacement_non_dict_rejected(self):
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(review="misled", action="refine", replacement_lesson="string")
        ]))
        self.assertTrue(any("replacement_lesson" in e and "object" in e for e in errors), errors)

    def test_each_replacement_struct_field_required(self):
        for field in ("lesson", "mechanism", "applies_when", "invalid_if"):
            with self.subTest(field=field):
                errors = _validate(_skeleton(lesson_audit=[
                    _lesson_audit(review="misled", action="refine",
                                  replacement_lesson=_replacement(__delete__=[field]))
                ]))
                self.assertTrue(any(f"replacement_lesson.{field}" in e for e in errors), errors)

    def test_replacement_field_too_short_rejected(self):
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(review="misled", action="refine",
                          replacement_lesson=_replacement(applies_when="short"))
        ]))
        self.assertTrue(any("replacement_lesson.applies_when" in e and "30 chars" in e for e in errors), errors)

    def test_replacement_evidence_refs_empty_rejected(self):
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(review="misled", action="refine",
                          replacement_lesson=_replacement(evidence_refs=[]))
        ]))
        self.assertTrue(any("replacement_lesson.evidence_refs" in e and "non-empty" in e for e in errors), errors)

    def test_keep_with_replacement_lesson_present_passes(self):
        # action=keep with a stray replacement_lesson is harmless — validator
        # only enforces replacement_lesson WHEN action==refine.
        errors = _validate(_skeleton(lesson_audit=[
            _lesson_audit(replacement_lesson=_replacement())
        ]))
        self.assertEqual(errors, [], errors)


# ────────────────────────────────────────────────────────────────────────
# Integration: full v3 payload with all v3 fields populated
# ────────────────────────────────────────────────────────────────────────

class FullV3PayloadTests(unittest.TestCase):
    def test_full_v3_with_all_fields_passes(self):
        payload = _skeleton(
            global_observations=[
                _global_obs("sector"),
                _global_obs("macro"),
                _global_obs("cross_ticker", related_tickers=["MSFT", "GOOGL"]),
            ],
            predictor_lessons=[_predictor_lesson(), _predictor_lesson(lesson=_LONG + "B")],
            lesson_audit=[
                _lesson_audit(0, review="helped", action="keep"),
                _lesson_audit(1, review="misled", action="refine",
                              replacement_lesson=_replacement()),
            ],
        )
        self.assertEqual(_validate(payload), [], _validate(payload))


if __name__ == "__main__":
    unittest.main(verbosity=2)
