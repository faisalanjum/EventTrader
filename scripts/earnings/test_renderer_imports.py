"""Layer 4: import-shim integrity. Initially skipped — un-skipped in commit 19.

Asserts every old-path import (`from earnings_orchestrator import X`) resolves
to the SAME object as the new-path import (`from scripts.earnings.renderer.<m>
import X`). 37 parametrized cases — one per migrated symbol.
"""
from __future__ import annotations
import importlib
import sys
from pathlib import Path
import pytest

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

# pytestmark removed in commit 19 — shim contract is now testable.

# (symbol, old_module, new_module) — covers ALL 37 moved symbols
SHIM_TABLE = [
    # Top-level public
    ("render_bundle_text",            "earnings_orchestrator", "scripts.earnings.renderer.bundle"),
    # Section renderers
    ("_render_header",                "earnings_orchestrator", "scripts.earnings.renderer.header"),
    ("_render_results_and_expectations","earnings_orchestrator", "scripts.earnings.renderer.results"),
    ("_render_reference",             "earnings_orchestrator", "scripts.earnings.renderer.results"),
    ("_render_forward_guidance",      "earnings_orchestrator", "scripts.earnings.renderer.guidance"),
    ("_render_consensus_history",     "earnings_orchestrator", "scripts.earnings.renderer.consensus"),
    ("_render_prior_financials",      "earnings_orchestrator", "scripts.earnings.renderer.financials"),
    ("_render_revenue_splits",        "earnings_orchestrator", "scripts.earnings.renderer.financials"),
    ("_render_inter_quarter",         "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_render_peer_earnings",         "earnings_orchestrator", "scripts.earnings.renderer.peers"),
    ("_render_macro",                 "earnings_orchestrator", "scripts.earnings.renderer.macro"),
    ("_render_learning_context",      "earnings_orchestrator", "scripts.earnings.renderer.lessons"),
    # Generic formatters
    ("_md_table",                     "earnings_orchestrator", "scripts.earnings.renderer._formatters"),
    ("_fmt_num",                      "earnings_orchestrator", "scripts.earnings.renderer._formatters"),
    ("_fmt_money",                    "earnings_orchestrator", "scripts.earnings.renderer._formatters"),
    ("_fmt_pct",                      "earnings_orchestrator", "scripts.earnings.renderer._formatters"),
    # Guidance helpers
    ("_fmt_guidance_value",           "earnings_orchestrator", "scripts.earnings.renderer.guidance"),
    ("_fmt_metric_label",             "earnings_orchestrator", "scripts.earnings.renderer.guidance"),
    ("_compute_change",               "earnings_orchestrator", "scripts.earnings.renderer.guidance"),
    ("_guidance_target_key",          "earnings_orchestrator", "scripts.earnings.renderer.guidance"),
    ("_guidance_target_label",        "earnings_orchestrator", "scripts.earnings.renderer.guidance"),
    ("_is_segmented_label",           "earnings_orchestrator", "scripts.earnings.renderer.guidance"),
    # Financials helpers
    ("_fmt_financial_cell",           "earnings_orchestrator", "scripts.earnings.renderer.financials"),
    ("_fmt_split_pct",                "earnings_orchestrator", "scripts.earnings.renderer.financials"),
    ("_FINANCIAL_SECTIONS",           "earnings_orchestrator", "scripts.earnings.renderer.financials"),
    # Inter-quarter internal helpers (legacy importable)
    ("_iq_cell",                      "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_val",                       "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_bool",                      "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_join",                      "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_header",                    "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_days_table",                "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_adj_returns",               "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_news_table",                "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_filings_table",             "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_dividends_table",           "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    ("_iq_splits_table",              "earnings_orchestrator", "scripts.earnings.renderer.inter_quarter"),
    # Sibling utility
    ("_normalize_lesson_text",        "earnings_orchestrator", "scripts.earnings._text_utils"),
]


@pytest.mark.parametrize("symbol,old_module,new_module", SHIM_TABLE)
def test_old_path_equals_new_path(symbol, old_module, new_module):
    old_obj = getattr(importlib.import_module(old_module), symbol)
    new_obj = getattr(importlib.import_module(new_module), symbol)
    assert old_obj is new_obj, (
        f"{symbol}: old path {old_module} and new path {new_module} resolve to "
        f"different objects — shim is broken"
    )


def test_renderer_package_public_surface():
    """After commit 19, renderer/__init__.py must expose the public surface."""
    import scripts.earnings.renderer as r
    expected_public = {
        "render_bundle_text", "_render_header", "_render_results_and_expectations",
        "_render_reference", "_render_forward_guidance", "_render_consensus_history",
        "_render_prior_financials", "_render_revenue_splits", "_render_inter_quarter",
        "_render_peer_earnings", "_render_macro", "_render_learning_context",
        "_md_table", "_fmt_num", "_fmt_money", "_fmt_pct", "_fmt_guidance_value",
        "_fmt_metric_label", "_fmt_financial_cell", "_fmt_split_pct",
        "_compute_change", "_guidance_target_key", "_guidance_target_label",
        "_is_segmented_label",
    }
    for name in expected_public:
        assert hasattr(r, name), f"renderer package missing public symbol: {name}"


def test_fmt_financial_cell_identity_all_four_paths():
    """All four import paths for _fmt_financial_cell resolve to the SAME
    function object. This is the load-bearing invariant of the
    _fmt_financial_cell relocation (see .claude/plans/_formatters.md).

    The 4 paths:
      1. earnings_orchestrator._fmt_financial_cell        (legacy top-level)
      2. scripts.earnings.renderer._fmt_financial_cell    (package public surface, via __init__.py)
      3. scripts.earnings.renderer.financials._fmt_financial_cell  (back-compat re-export)
      4. scripts.earnings.renderer._formatters._fmt_financial_cell (canonical home)

    If this test fails, identity has been broken — likely someone added a
    parallel definition or wrapped the function. Revert immediately and
    investigate; the back-compat contract has been violated.
    """
    obj_orch = importlib.import_module("earnings_orchestrator")._fmt_financial_cell
    obj_pkg  = importlib.import_module("scripts.earnings.renderer")._fmt_financial_cell
    obj_fin  = importlib.import_module("scripts.earnings.renderer.financials")._fmt_financial_cell
    obj_fmt  = importlib.import_module("scripts.earnings.renderer._formatters")._fmt_financial_cell
    assert obj_orch is obj_pkg, "earnings_orchestrator vs renderer package: NOT same object"
    assert obj_orch is obj_fin, "earnings_orchestrator vs renderer.financials: NOT same object"
    assert obj_orch is obj_fmt, "earnings_orchestrator vs renderer._formatters: NOT same object"
