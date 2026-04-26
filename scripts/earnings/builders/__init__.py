"""scripts.earnings.builders — relocated builder modules.

Public surface: 7 adapter functions used by earnings_orchestrator.py.
Underlying builders remain reachable via their submodules
(e.g. scripts.earnings.builders.consensus.build_consensus).

Identity contract: package-root re-exports here MUST be the SAME function
objects as scripts.earnings.builders.adapters.X. Verified by
test_package_root_re_exports_identity_with_adapters_submodule.
"""
from __future__ import annotations

from .adapters import (
    build_8k_packet,
    build_guidance_history,
    build_inter_quarter_context,
    build_peer_earnings_snapshot,
    build_macro_snapshot,
    build_consensus,
    build_prior_financials,
)

__all__ = [
    "build_8k_packet",
    "build_guidance_history",
    "build_inter_quarter_context",
    "build_peer_earnings_snapshot",
    "build_macro_snapshot",
    "build_consensus",
    "build_prior_financials",
]
