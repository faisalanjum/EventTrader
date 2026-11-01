from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_lse_proxy_pilot import build_requests, read_api_key  # noqa: E402


def test_build_requests_deduplicates_shared_direct_and_stock_symbols():
    config = {
        "direct_candidates": {
            "A": [{"symbol": "NQ.F", "dataset": "futures"}],
            "B": [{"symbol": "NQ.F", "dataset": "futures"}],
        }
    }
    holdings = {
        "funds": {
            "A": {"holdings": [{"symbol": "NVDA"}]},
            "B": {"holdings": [{"symbol": "NVDA"}, {"symbol": "MSFT"}]},
        }
    }

    assert build_requests(config, holdings) == [
        {"symbol": "NQ.F", "dataset": "futures", "kind": "direct"},
        {"symbol": "MSFT", "dataset": "stocks", "kind": "constituent"},
        {"symbol": "NVDA", "dataset": "stocks", "kind": "constituent"},
    ]


def test_read_api_key_can_extract_key_from_a_larger_private_file(tmp_path):
    source = tmp_path / "private.html"
    source.write_text("before lse_live_abc123 after", encoding="utf-8")

    assert read_api_key("", source) == "lse_live_abc123"
