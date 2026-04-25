"""Top-level renderer — render_bundle_text.

Extracted from earnings_orchestrator.py (commit 18/20) — body copied verbatim
from the pre-renderer-extract baseline at line 1503. Imports every section
module's primary renderer.
"""
from __future__ import annotations

from .header import _render_header
from .results import _render_results_and_expectations, _render_reference
from .guidance import _render_forward_guidance
from .consensus import _render_consensus_history
from .financials import _render_prior_financials
from .inter_quarter import _render_inter_quarter
from .peers import _render_peer_earnings
from .macro import _render_macro
from .lessons import _render_learning_context


def render_bundle_text(bundle: dict) -> str:
    """Render the 7-item bundle as decision-ordered text for the predictor."""
    sections = []

    # 1. Header
    sections.append(_render_header(bundle))

    # 2. Results & Expectations (consensus bar + EX-99.1)
    sections.append(_render_results_and_expectations(bundle))

    # 3. Forward Guidance
    sections.append(_render_forward_guidance(bundle))

    # 4. Consensus History
    sections.append(_render_consensus_history(bundle))

    # 5. Prior Financial Trends
    sections.append(_render_prior_financials(bundle))

    # 6. Inter-Quarter Events
    sections.append(_render_inter_quarter(bundle))

    # 7. Peer Earnings
    sections.append(_render_peer_earnings(bundle))

    # 8. Macro Environment
    sections.append(_render_macro(bundle))

    # 9. Reference — other exhibits, 8-K sections, lower-signal content
    sections.append(_render_reference(bundle))

    # 10. Prior Lessons (from learner — if available)
    learning_ctx = bundle.get("learning_context")
    if learning_ctx and (learning_ctx.get("ticker_lessons") or learning_ctx.get("global_lessons")):
        _text, _ = _render_learning_context(learning_ctx)
        sections.append(_text)

    return "\n\n".join(sections)

