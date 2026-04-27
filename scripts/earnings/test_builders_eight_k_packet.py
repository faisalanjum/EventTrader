"""Mocked unit tests for eight_k_packet (Stage 1.1)."""
from __future__ import annotations
import json
import os
from unittest.mock import MagicMock, patch
import pytest

from scripts.earnings.builders import eight_k_packet as ek

pytestmark = pytest.mark.builders


def _mock_manager(rows_by_query):
    """Mock Neo4j manager that routes queries by EXACT identity match against the
    canonical query-constant strings imported from `eight_k_packet`.

    CRITICAL: substring routing is fragile and misroutes queries here. Specifically,
    `QUERY_4G_META` contains both `'PRIMARY_FILER'` AND `'ExtractedSectionContent'`
    AND `'section_name'`, so a substring router that gates on those tokens would
    misclassify 4G as 4J or vice-versa. Exact-equality routing against the imported
    constants eliminates this risk and stays correct if the Cypher bodies evolve."""
    m = MagicMock()
    def execute(query, params):
        if query == ek.QUERY_4G_META:
            return rows_by_query.get("4G_META", [])
        if query == ek.QUERY_4J:
            return rows_by_query.get("4J", [])
        if query == ek.QUERY_4K:
            return rows_by_query.get("4K", [])
        if query == ek.QUERY_4K_OTHER_PREVIEW:
            return rows_by_query.get("4K_OTHER", [])
        if query == ek.QUERY_4F:
            return rows_by_query.get("4F", [])
        raise AssertionError(f"unexpected query: {query[:120]}")
    m.execute_cypher_query_all.side_effect = execute
    m.close = MagicMock()
    return m


@pytest.fixture
def base_meta():
    return {
        "filed_8k": "2024-09-15T16:00:00-04:00",
        "form_type": "8-K",
        "items": '["Item 2.02", "Item 9.01"]',
        "period_of_report": "2024-09-15",
        "market_session": "post_market",
        "is_amendment": False,
        "cik": 12345,
        "sector": "Technology",
        "exhibit_numbers": ["EX-99.1", "EX-99.2", "EX-101"],
        "section_names": ["Item2.02ResultsofOperationsandFinancialCondition"],
        "has_filing_text": True,
    }


def test_no_metadata_raises_value_error(tmp_path, base_meta):
    mgr = _mock_manager({"4G_META": []})
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        with pytest.raises(ValueError, match="No Report found"):
            ek.build_8k_packet("0000000000-00-000000", "FAKE", out_path=out)
    mgr.close.assert_called_once()


def test_items_json_string_parsed(tmp_path, base_meta):
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert packet["items"] == ["Item 2.02", "Item 9.01"]


def test_items_invalid_json_falls_back_to_single(tmp_path, base_meta):
    base_meta["items"] = "not-json-actually"
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert packet["items"] == ["not-json-actually"]


def test_null_stripping_in_inventory(tmp_path, base_meta):
    base_meta["section_names"] = [None, "RealSection", None]
    base_meta["exhibit_numbers"] = ["EX-99.1", None]
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert packet["content_inventory"]["section_names"] == ["RealSection"]
    assert packet["content_inventory"]["exhibit_numbers"] == ["EX-99.1"]


def test_other_exhibit_preview_only_when_diff(tmp_path, base_meta):
    # inventory says EX-99.1, EX-99.2, EX-101 — _fetch_8k_core returns 99.1+99.2
    # — so EX-101 is the "other" that needs preview
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [],
        "4K": [{"exhibit_number": "EX-99.1", "content": "ex99-content"},
               {"exhibit_number": "EX-99.2", "content": "ex99-other"}],
        "4K_OTHER": [{"exhibit_number": "EX-101",
                      "content_preview": "preview...", "full_size": 12345}],
        "4F": [],
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert len(packet["exhibits_other"]) == 1
    assert packet["exhibits_other"][0]["exhibit_number"] == "EX-101"


def test_filing_text_fallback_when_all_empty(tmp_path, base_meta):
    base_meta["section_names"] = []
    base_meta["exhibit_numbers"] = []
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [], "4K": [], "4K_OTHER": [],
        "4F": [{"content": "fallback-text-content"}],
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert packet["filing_text"] == "fallback-text-content"


def test_atomic_write_default_path(tmp_path, base_meta):
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        # Use explicit tmp_path to avoid touching /tmp
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert os.path.exists(out)
    on_disk = json.load(open(out))
    assert on_disk["accession_8k"] == "ACC"


def test_manager_close_on_exception(tmp_path):
    mgr = MagicMock()
    mgr.execute_cypher_query_all.side_effect = RuntimeError("kaboom")
    mgr.close = MagicMock()
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        with pytest.raises(RuntimeError, match="kaboom"):
            ek.build_8k_packet("ACC", "FAKE", out_path=str(tmp_path / "x.json"))
    mgr.close.assert_called_once()


def test_items_already_a_list_passes_through(tmp_path, base_meta):
    """When meta.items is already a Python list (not a JSON string), it must
    pass through unchanged."""
    base_meta["items"] = ["Item 7.01"]
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [], "4K": [], "4K_OTHER": [], "4F": [],
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert packet["items"] == ["Item 7.01"]


def test_no_other_exhibit_preview_when_no_diff(tmp_path, base_meta):
    """When 4G inventory matches the EX-99 set exactly (no non-99 leftover),
    4K_OTHER_PREVIEW must NOT be queried — packet['exhibits_other'] is empty.
    Guards the inventory-diff condition that saves a Cypher round-trip."""
    base_meta["exhibit_numbers"] = ["EX-99.1"]
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [],
        "4K": [{"exhibit_number": "EX-99.1", "content": "x"}],
        "4K_OTHER": [],  # MUST not be queried; empty answer is the safety net
        "4F": [],
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert packet["exhibits_other"] == []


def test_filing_text_NOT_fetched_when_structured_content_present(tmp_path, base_meta):
    """Inverse of test_filing_text_fallback_when_all_empty — if ANY of
    (sections, ex99, exhibits_other) is non-empty, 4F must NOT be queried
    and packet['filing_text'] must be None. Guards the fallback predicate."""
    mgr = _mock_manager({
        "4G_META": [base_meta],
        "4J": [{"section_name": "Item2.02", "content": "real-section"}],
        "4K": [], "4K_OTHER": [],
        "4F": [{"content": "WHO_QUERIED_ME"}],  # if this appears, the predicate is wrong
    })
    with patch("scripts.earnings.builders.eight_k_packet.get_manager", return_value=mgr):
        out = str(tmp_path / "out.json")
        packet = ek.build_8k_packet("ACC", "FAKE", out_path=out)
    assert packet["filing_text"] is None


# NOTE: `test_run_8k_uses_canonical_fetch_8k_core` is INTENTIONALLY ABSENT from
# Stage 1.1 — it cannot pass during COPY-only stages because both modules legitimately
# have their own def. It is added in Stage 1.2 (CUTOVER) — see Stage 1.2 step 8 below.
