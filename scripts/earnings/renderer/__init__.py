"""Bundle renderer — extracted from earnings_orchestrator.py on 2026-04-25.

Public surface re-exported here so external consumers can use:
    from scripts.earnings.renderer import render_bundle_text
    from scripts.earnings.renderer import _render_header  # etc.

The orchestrator's own back-compat shim block uses submodule-direct imports
(NOT `from .renderer import X`), so this file is INDEPENDENT — it only exists
for the convenience of external consumers who want a single import path.

Internal helpers (_iq_*, _FINANCIAL_SECTIONS) are NOT re-exported — import
them directly from their submodule when needed.
"""
from __future__ import annotations

from .bundle import render_bundle_text
from ._formatters import _md_table, _fmt_num, _fmt_money, _fmt_pct
from .header import _render_header
from .results import _render_results_and_expectations, _render_reference
from .guidance import (
    _fmt_guidance_value, _compute_change, _fmt_metric_label,
    _guidance_target_key, _guidance_target_label, _is_segmented_label,
    _render_forward_guidance,
)
from .consensus import _render_consensus_history
from .financials import (
    _fmt_financial_cell, _fmt_split_pct,
    _render_revenue_splits, _render_prior_financials,
)
from .inter_quarter import _render_inter_quarter
from .peers import _render_peer_earnings
from .macro import _render_macro
from .lessons import _render_learning_context

__all__ = [
    "render_bundle_text",
    "_render_header",
    "_render_results_and_expectations",
    "_render_reference",
    "_render_forward_guidance",
    "_render_consensus_history",
    "_render_prior_financials",
    "_render_revenue_splits",
    "_render_inter_quarter",
    "_render_peer_earnings",
    "_render_macro",
    "_render_learning_context",
    "_md_table",
    "_fmt_num",
    "_fmt_money",
    "_fmt_pct",
    "_fmt_guidance_value",
    "_fmt_metric_label",
    "_fmt_financial_cell",
    "_fmt_split_pct",
    "_compute_change",
    "_guidance_target_key",
    "_guidance_target_label",
    "_is_segmented_label",
]
