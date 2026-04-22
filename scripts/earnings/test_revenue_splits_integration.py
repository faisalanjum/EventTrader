"""Integration tests for lean revenue_splits bundle/render wiring."""
from __future__ import annotations

import functools
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from build_prior_financials import build_prior_financials
from earnings_orchestrator import _render_prior_financials


@functools.lru_cache(maxsize=1)
def _chrw_packet() -> dict:
    qi = {
        "period_of_report": "2024-12-31",
        "filed_8k": "2025-04-01T00:00:00+00:00",
        "market_session": "pre_market",
        "quarter_label": "Q4 FY2024",
    }
    return build_prior_financials(
        "CHRW",
        qi,
        as_of_ts="2025-04-01T00:00:00+00:00",
        out_path="/tmp/test_revenue_splits_chrw.json",
    )


def test_build_prior_financials_emits_revenue_splits_section():
    pkt = _chrw_packet()
    rs = pkt.get("revenue_splits")
    assert isinstance(rs, dict)
    assert len(rs.get("quarters", [])) == 4
    assert rs.get("business_segment")
    assert rs.get("product_service")
    assert isinstance(rs.get("geography"), list)


def test_render_prior_financials_includes_revenue_mix_tables():
    pkt = _chrw_packet()
    rendered = _render_prior_financials({"prior_financials": pkt, "builder_errors": {}})
    assert "Revenue Mix — Business Segments" in rendered
    assert "Revenue Mix — Product / Service" in rendered
    assert "%" in rendered
