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

    # 1b. U67 — Evidence Source IDs catalog. Predictor MUST copy one of
    # these IDs verbatim into every `evidence_ledger[i].source_id`. The
    # validator uses set-membership against the same in-memory catalog.
    catalog = bundle.get("evidence_source_catalog") or []
    if catalog:
        block = ["## Evidence Source IDs (copy verbatim into evidence_ledger[].source_id)"]
        for sid in catalog:
            block.append(f"- {sid}")
        sections.append("\n".join(block))

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

    # 10. Prior Lessons (from learner). Always render — _render_learning_context
    # handles empty/None internally and emits a "No prior lessons available"
    # marker so the predictor sees the section was explicitly checked.
    # Pre-U45+U66 the outer guard skipped this entirely in the empty case,
    # which left the predictor with no signal (caught by CRM Q3 smoke).
    _text, _ = _render_learning_context(bundle.get("learning_context") or {})
    sections.append(_text)

    return "\n\n".join(sections)
