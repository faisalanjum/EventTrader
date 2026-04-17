#!/usr/bin/env python3
"""R18 tests for ``_resolve_pit_mode`` — T1.5a bundle-PIT default + XOR guard.

Covers R18a–R18f per ``.claude/plans/learner.md`` §🔥 T1.5a. These tests
exercise the PIT-mode helper in isolation from argparse / run_core_flow;
they do not require Neo4j or SDK.
"""
from __future__ import annotations

import sys
import unittest
from argparse import Namespace
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

import earnings_orchestrator as orch


FILED_8K = "2023-03-02T16:16:43-05:00"
QI_VALID = {"filed_8k": FILED_8K, "quarter_label": "Q1_FY2023"}
QI_NO_FILED = {"quarter_label": "Q1_FY2023"}  # filed_8k missing


def _args(pit=None, live=False, predict=False, learn=False):
    """Build a minimal argparse.Namespace matching main()'s parsed args."""
    return Namespace(pit=pit, live=live, predict=predict, learn=learn)


class ResolvePITMode(unittest.TestCase):
    """T1.5a R18: _resolve_pit_mode(args, quarter_info) -> (pit_cutoff, mode)."""

    # ── R18a — historical default ──────────────────────────────────────
    def test_R18a_historical_default_on_predict(self):
        """--predict without --pit/--live defaults to filed_8k, historical."""
        pit, mode = orch._resolve_pit_mode(
            _args(predict=True), QI_VALID,
        )
        self.assertEqual(pit, FILED_8K)
        self.assertEqual(mode, "historical")

    def test_R18a_historical_default_on_learn(self):
        """--learn without --pit/--live also defaults to filed_8k, historical."""
        pit, mode = orch._resolve_pit_mode(
            _args(learn=True), QI_VALID,
        )
        self.assertEqual(pit, FILED_8K)
        self.assertEqual(mode, "historical")

    def test_R18a_historical_default_on_predict_and_learn(self):
        """--predict + --learn still defaults historical."""
        pit, mode = orch._resolve_pit_mode(
            _args(predict=True, learn=True), QI_VALID,
        )
        self.assertEqual(pit, FILED_8K)
        self.assertEqual(mode, "historical")

    # ── R18b — --live opt-in preserves pit_cutoff=None ────────────────
    def test_R18b_live_opt_in_with_predict(self):
        """--live + --predict → (None, 'live'). Intentional live mode."""
        pit, mode = orch._resolve_pit_mode(
            _args(live=True, predict=True), QI_VALID,
        )
        self.assertIsNone(pit)
        self.assertEqual(mode, "live")

    def test_R18b_live_opt_in_without_predict(self):
        """--live alone (no --predict/--learn) → (None, 'live')."""
        pit, mode = orch._resolve_pit_mode(_args(live=True), QI_VALID)
        self.assertIsNone(pit)
        self.assertEqual(mode, "live")

    # ── R18c — explicit --pit overrides default ───────────────────────
    def test_R18c_cli_override_wins(self):
        """Explicit --pit wins over filed_8k default."""
        explicit = "2024-06-01T00:00:00Z"
        pit, mode = orch._resolve_pit_mode(
            _args(pit=explicit, predict=True), QI_VALID,
        )
        self.assertEqual(pit, explicit)
        self.assertEqual(mode, "historical")

    def test_R18c_cli_override_without_predict(self):
        """--pit alone (no --predict/--learn) also honored."""
        explicit = "2024-06-01T00:00:00Z"
        pit, mode = orch._resolve_pit_mode(_args(pit=explicit), QI_VALID)
        self.assertEqual(pit, explicit)
        self.assertEqual(mode, "historical")

    # ── R18d — XOR guard: --live AND --pit is an error ────────────────
    def test_R18d_xor_guard_raises(self):
        """--live and --pit together → ValueError."""
        with self.assertRaises(ValueError) as ctx:
            orch._resolve_pit_mode(
                _args(pit="2024-06-01T00:00:00Z", live=True, predict=True),
                QI_VALID,
            )
        self.assertIn("mutually exclusive", str(ctx.exception).lower())

    def test_R18d_xor_guard_raises_even_without_predict(self):
        """XOR guard fires regardless of --predict/--learn."""
        with self.assertRaises(ValueError):
            orch._resolve_pit_mode(
                _args(pit="2024-06-01T00:00:00Z", live=True), QI_VALID,
            )

    # ── R18e — inspection mode preserved (no flags) ───────────────────
    def test_R18e_no_flags_stays_live(self):
        """No --pit, no --live, no --predict/--learn → (None, 'live').
        Preserves bundle-inspection mode (--save alone)."""
        pit, mode = orch._resolve_pit_mode(_args(), QI_VALID)
        self.assertIsNone(pit)
        self.assertEqual(mode, "live")

    # ── R18f — defensive: missing filed_8k when default would apply ──
    def test_R18f_missing_filed_8k_raises(self):
        """If default would apply but quarter_info lacks filed_8k → ValueError."""
        with self.assertRaises(ValueError) as ctx:
            orch._resolve_pit_mode(_args(predict=True), QI_NO_FILED)
        self.assertIn("filed_8k", str(ctx.exception))

    def test_R18f_missing_filed_8k_ok_with_live(self):
        """--live doesn't need filed_8k."""
        pit, mode = orch._resolve_pit_mode(
            _args(live=True, predict=True), QI_NO_FILED,
        )
        self.assertIsNone(pit)
        self.assertEqual(mode, "live")

    def test_R18f_missing_filed_8k_ok_with_explicit_pit(self):
        """--pit doesn't need filed_8k either."""
        pit, mode = orch._resolve_pit_mode(
            _args(pit="2024-06-01T00:00:00Z", predict=True), QI_NO_FILED,
        )
        self.assertEqual(pit, "2024-06-01T00:00:00Z")
        self.assertEqual(mode, "historical")


if __name__ == "__main__":
    unittest.main()
