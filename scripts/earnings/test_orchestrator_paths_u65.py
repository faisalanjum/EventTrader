"""U65 — get_quarter_dir must scope bundle paths to save_dir, not save_dir.parent.

Pre-U65 bug: ``get_quarter_dir(ticker, qi, save_dir="/tmp/smoke_AVGO")`` returned
``Path("/tmp")`` (i.e. ``save_dir.parent``), causing parallel ``--save-dir
/tmp/smoke_<TICKER>`` runs to race on ``/tmp/context_bundle.json``.

Post-U65: ``get_quarter_dir`` returns ``Path(save_dir)`` directly when
``save_dir`` is supplied, so each parallel run gets its own bundle path.

Run:
    venv/bin/python -m pytest scripts/earnings/test_orchestrator_paths_u65.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from earnings_orchestrator import (  # noqa: E402
    get_quarter_dir,
    get_prediction_paths,
)


_QI = {
    "ticker": "AVGO",
    "accession_8k": "0001730168-23-000093",
    "filed_8k": "2023-12-07T16:18:51-05:00",
    "period_of_report": "2023-10-29",
    "quarter_label": "Q4_FY2023",
    "form_type_periodic": "10-K",
    "accession_periodic": "",
    "fye_month": 10,
    "market_session": "post_market",
    "prev_8k_ts": "2023-08-31T17:18:57-04:00",
    "quarter_identity_source": "matched_periodic_xbrl",
    "gaps": None,
}


class GetQuarterDirSaveDirTests(unittest.TestCase):
    """get_quarter_dir must NOT strip the save_dir scoping."""

    def test_save_dir_returned_unchanged(self):
        result = get_quarter_dir("AVGO", _QI, save_dir="/tmp/smoke_AVGO")
        self.assertEqual(result, Path("/tmp/smoke_AVGO"))
        # Pre-U65 regression guard: must NOT collapse to /tmp.
        self.assertNotEqual(result, Path("/tmp"))

    def test_save_dir_with_trailing_slash(self):
        result = get_quarter_dir("AVGO", _QI, save_dir="/tmp/smoke_AVGO/")
        self.assertEqual(result, Path("/tmp/smoke_AVGO"))

    def test_save_dir_relative_path(self):
        result = get_quarter_dir("AVGO", _QI, save_dir="smoke_AVGO")
        self.assertEqual(result, Path("smoke_AVGO"))

    def test_default_path_when_save_dir_none(self):
        result = get_quarter_dir("AVGO", _QI, save_dir=None)
        self.assertEqual(
            result,
            Path("earnings-analysis/Companies/AVGO/events/Q4_FY2023"),
        )


class GetPredictionPathsBundleScopingTests(unittest.TestCase):
    """End-to-end: bundle_path must live INSIDE save_dir."""

    def test_bundle_path_inside_save_dir(self):
        paths = get_prediction_paths("AVGO", _QI, save_dir="/tmp/smoke_AVGO")
        self.assertEqual(
            paths["bundle_path"],
            Path("/tmp/smoke_AVGO/context_bundle.json"),
        )
        self.assertEqual(
            paths["rendered_path"],
            Path("/tmp/smoke_AVGO/context_bundle_rendered.txt"),
        )

    def test_bundle_path_default_unchanged(self):
        paths = get_prediction_paths("AVGO", _QI, save_dir=None)
        self.assertEqual(
            paths["bundle_path"],
            Path("earnings-analysis/Companies/AVGO/events/Q4_FY2023/context_bundle.json"),
        )


class ParallelSaveDirsAreUniqueTests(unittest.TestCase):
    """Two parallel runs with distinct save_dirs must produce DISTINCT bundle
    paths. This is the load-bearing assertion for U65 — without it, parallel
    --predict runs corrupt each other's bundles via /tmp/context_bundle.json."""

    def test_two_save_dirs_produce_unique_bundle_paths(self):
        avgo = get_prediction_paths("AVGO", _QI, save_dir="/tmp/smoke_AVGO")
        aapl_qi = dict(_QI, ticker="AAPL", quarter_label="Q3_FY2024",
                       accession_8k="0000320193-24-000001")
        aapl = get_prediction_paths("AAPL", aapl_qi, save_dir="/tmp/smoke_AAPL")

        self.assertNotEqual(avgo["bundle_path"], aapl["bundle_path"])
        self.assertNotEqual(avgo["rendered_path"], aapl["rendered_path"])

        # And both are under their respective ticker-scoped dirs.
        self.assertTrue(str(avgo["bundle_path"]).startswith("/tmp/smoke_AVGO/"))
        self.assertTrue(str(aapl["bundle_path"]).startswith("/tmp/smoke_AAPL/"))


if __name__ == "__main__":
    unittest.main()
