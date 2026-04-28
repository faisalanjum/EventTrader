#!/usr/bin/env python3
"""Cross-surface equivalence test for learner_result paths.

Per .claude/plans/skill-md-proposal-approved-mossy-stroustrup.md §6.3 — the
rendered "### Allowed learner reports for this prediction" block MUST mirror
the JSON `_allowed_learner_paths` exactly: same set, same order, no dupes.

This is the cross-surface invariant the user explicitly required so the
SKILL.md instruction "listed in the rendered bundle and present in
learning_context._allowed_learner_paths" cannot drift between the two
surfaces.

Run:
    venv/bin/python -m pytest scripts/earnings/test_learner_paths_cross_surface.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))

from earnings_orchestrator import _render_learning_context


class CrossSurfaceAllowlistEquivalenceTest(unittest.TestCase):
    def test_rendered_allowlist_block_set_equals_json_allowlist(self):
        """Hand-craft a learning_context with mixed ticker + global lessons +
        an `_allowed_learner_paths` whose values are also reflected on the
        per-lesson `learner_result_path` keys. Render and parse the rendered
        allowlist block; assert exact list equality (which implies set equality
        AND ordering AND no dupes)."""
        p_aapl = "earnings-analysis/Companies/AAPL/events/Q1_FY2023/learning/result.md"
        p_msft = "earnings-analysis/Companies/MSFT/events/Q2_FY2024/learning/result.md"
        p_goog = "earnings-analysis/Companies/GOOG/events/Q3_FY2024/learning/result.md"

        lc = {
            "_allowed_learner_paths": [p_aapl, p_msft, p_goog],
            "ticker_lessons": [
                {
                    "quarter_label": "Q1_FY2023",
                    "direction_correct": True,
                    "actual_daily_pct": 1.0,
                    "predicted_direction": "long",
                    "primary_driver_category": "eps_surprise",
                    "predictor_lessons": ["pl1"],
                    "learner_result_path": p_aapl,
                },
            ],
            "global_lessons": [
                {"scope": "sector", "target_sector": "Technology",
                 "source_ticker": "MSFT", "lesson": "sector body",
                 "learner_result_path": p_msft},
                {"scope": "macro",
                 "source_ticker": "GOOG", "lesson": "macro body",
                 "learner_result_path": p_goog},
            ],
        }
        text, _ = _render_learning_context(lc)

        # Parse the rendered allowlist block: extract every line of the form
        # "- <path>" that follows the allowlist heading until the next heading
        # (line starting with `### `) or end of text.
        heading = "### Allowed learner reports for this prediction"
        self.assertIn(heading, text, "allowlist heading missing from rendered text")
        block_start = text.index(heading) + len(heading)
        rest = text[block_start:]
        # End of block is the next "### " heading or EOF
        end_marker = rest.find("\n### ")
        block = rest if end_marker == -1 else rest[:end_marker]

        parsed = []
        for line in block.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- "):
                parsed.append(stripped[2:].strip())

        # Set+order+dedupe: exact list match
        self.assertEqual(
            parsed, lc["_allowed_learner_paths"],
            "Rendered allowlist block must mirror JSON _allowed_learner_paths "
            "exactly (same set, same order, no dupes)",
        )
        # Belt-and-suspenders: explicit no-dupes check
        self.assertEqual(
            len(parsed), len(set(parsed)),
            "Rendered allowlist block contains duplicates",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
