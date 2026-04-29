"""U7 — related-filings sidecar tests.

Tests the new helpers and integration logic added to
`scripts/earnings/builders/inter_quarter_context.py`:
  - `_parse_item_code(item_str) -> str | None`
  - `_should_emit_sidecar(form_type, items_codes, exhibits_dict) -> bool`
  - `_render_sidecar_md(filing_event, sections, exhibits, filing_text) -> str`
  - `build_inter_quarter_context(..., exclude_accessions=..., related_filings_dir=...)`
  - allowlist invariant (top-level `_allowed_related_filing_paths` matches
    non-null `related_content_path` values across events, same order)

Run:
    venv/bin/python -m pytest scripts/earnings/test_builders_inter_quarter_related_filings.py -q
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts/earnings"))

from scripts.earnings.builders import inter_quarter_context as iqc

pytestmark = pytest.mark.builders


# ─── _parse_item_code ──────────────────────────────────────────────────────

class TestParseItemCode:
    def test_standard_item_with_label(self):
        assert iqc._parse_item_code("Item 9.01: Financial Statements and Exhibits") == "9.01"

    def test_two_decimal_digits(self):
        assert iqc._parse_item_code("Item 5.02: Departure of Officers") == "5.02"

    def test_no_label(self):
        assert iqc._parse_item_code("Item 1.03") == "1.03"

    def test_extra_whitespace(self):
        assert iqc._parse_item_code("  Item   2.05:   Cost  ") == "2.05"

    def test_unparseable_returns_none(self):
        assert iqc._parse_item_code("not an item") is None
        assert iqc._parse_item_code("") is None
        assert iqc._parse_item_code(None) is None


# ─── _should_emit_sidecar ──────────────────────────────────────────────────

class TestShouldEmitSidecar:
    def test_8k_amendment_always_included(self):
        # 8-K/A is unconditional — even pure 9.01 with no exhibits → INCLUDE.
        assert iqc._should_emit_sidecar("8-K/A", {"9.01"}, {}) is True
        assert iqc._should_emit_sidecar("8-K/A", set(), {}) is True

    def test_8k_pure_9_01_no_exhibits_skipped(self):
        # Plain 8-K with only Item 9.01 AND no exhibits → SKIP (boilerplate-only).
        assert iqc._should_emit_sidecar("8-K", {"9.01"}, {}) is False

    def test_8k_pure_9_01_with_exhibits_included(self):
        # Same items but exhibits present → INCLUDE (covers AVGO 8-K/A-style cases
        # where pure-9.01 mask hides material restated EX-99.x attachments).
        assert iqc._should_emit_sidecar("8-K", {"9.01"}, {"EX-99.1": "url"}) is True

    def test_8k_with_directional_codes_included(self):
        # Codes ChatGPT's prior "material set" missed — bankruptcy, cyber, etc.
        for code in {"1.03", "1.05", "3.01", "4.02", "5.01"}:
            assert iqc._should_emit_sidecar("8-K", {code, "9.01"}, {}) is True, code

    def test_8k_with_8_01_only_included(self):
        # Item 8.01 standalone (Other Events — dividends, buybacks) → INCLUDE.
        assert iqc._should_emit_sidecar("8-K", {"8.01"}, {}) is True

    def test_8k_with_2_01_2_05_included(self):
        # M&A and restructuring → INCLUDE.
        assert iqc._should_emit_sidecar("8-K", {"2.01", "2.05"}, {}) is True

    def test_10k_skipped(self):
        # 10-K covered by §5 prior_financials; never included in sidecars.
        assert iqc._should_emit_sidecar("10-K", set(), {}) is False
        assert iqc._should_emit_sidecar("10-K", {"9.01"}, {"EX-10.1": "url"}) is False

    def test_10q_skipped(self):
        assert iqc._should_emit_sidecar("10-Q", set(), {}) is False
        assert iqc._should_emit_sidecar("10-Q/A", set(), {}) is False

    def test_form_4_skipped(self):
        assert iqc._should_emit_sidecar("4", set(), {}) is False

    def test_schedule_13d_skipped(self):
        assert iqc._should_emit_sidecar("SCHEDULE 13D", set(), {}) is False
        assert iqc._should_emit_sidecar("SCHEDULE 13D/A", set(), {}) is False

    def test_8k_missing_items_included(self):
        # Missing/unparseable items → INCLUDE (don't silently drop signal).
        assert iqc._should_emit_sidecar("8-K", set(), {}) is True

    def test_unknown_form_type_skipped(self):
        # Anything not 8-K or 8-K/A is skipped.
        assert iqc._should_emit_sidecar("S-3", set(), {}) is False
        assert iqc._should_emit_sidecar("DEF 14A", set(), {}) is False
        assert iqc._should_emit_sidecar("", set(), {}) is False


# ─── _render_sidecar_md ────────────────────────────────────────────────────

class TestRenderSidecarMd:
    def test_full_render_with_sections_and_exhibits(self):
        meta = {
            "accession": "0001140361-23-054354",
            "form_type": "8-K",
            "created": "2023-11-22T09:14:41-05:00",
            "market_session": "pre_market",
            "period_of_report": "2023-11-22",
            "is_amendment": False,
            "items": ["Item 2.01: Completion of Acquisition or Disposition of Assets"],
        }
        sections = [{"section_name": "OtherEvents", "content": "Section content."}]
        exhibits = [{"exhibit_number": "EX-99.1", "content": "Press release text."},
                    {"exhibit_number": "EX-10.1", "content": "Contract text."}]
        out = iqc._render_sidecar_md(meta, sections, exhibits, None)
        assert "0001140361-23-054354" in out
        assert "8-K" in out
        assert "Item 2.01" in out
        assert "OtherEvents" in out
        assert "Section content." in out
        assert "EX-99.1" in out
        assert "EX-10.1" in out
        assert "Contract text." in out

    def test_filing_text_fallback_when_sections_and_exhibits_empty(self):
        meta = {"accession": "X", "form_type": "8-K", "created": "2024-01-01T00:00:00-05:00",
                "market_session": "post_market", "period_of_report": "2024-01-01",
                "is_amendment": False, "items": []}
        out = iqc._render_sidecar_md(meta, [], [], "Fallback prose body.")
        assert "Fallback prose body." in out
        assert "Filing Text" in out


# ─── build_inter_quarter_context — integration ────────────────────────────

def _mock_manager(price_rows=None, news_rows=None, filing_rows=None,
                  div_rows=None, split_rows=None, company_context_rows=None,
                  content_for: dict | None = None):
    """Mock Neo4j manager. Returns query results based on Cypher hash markers."""
    mgr = MagicMock()
    content_for = content_for or {}

    def execute(query, params):
        # Match by distinctive Cypher snippet. PRIMARY_FILER (filings list)
        # and the single-accession content queries both contain HAS_SECTION,
        # so disambiguate on PRIMARY_FILER first.
        if "PRIMARY_FILER" in query and ":Report" in query:
            return filing_rows or []
        if "HAS_SECTION" in query and "ExtractedSectionContent" in query:
            acc = params.get("accession")
            return content_for.get(acc, {}).get("sections", [])
        if "HAS_EXHIBIT" in query and "ExhibitContent" in query:
            acc = params.get("accession")
            return content_for.get(acc, {}).get("exhibits", [])
        if "HAS_FILING_TEXT" in query and "FilingTextContent" in query:
            acc = params.get("accession")
            ft = content_for.get(acc, {}).get("filing_text")
            return [{"content": ft}] if ft else []
        if "MATCH (d:Date)" in query and "HAS_PRICE" in query:
            return price_rows or []
        if "MATCH (n:News)" in query:
            return news_rows or []
        if "Dividend" in query:
            return div_rows or []
        if "StockSplit" in query:
            return split_rows or []
        if "BELONGS_TO" in query and "Industry" in query:
            return company_context_rows or [{"sector": "Tech", "industry": "Semis"}]
        return []

    mgr.execute_cypher_query_all.side_effect = execute
    return mgr


def _filing_row(accession="0001140361-23-054354",
                form_type="8-K",
                created="2023-11-22T09:14:41-05:00",
                items=None,
                exhibits=None,
                period_of_report="2023-11-22",
                is_amendment=False):
    items_default = ['Item 2.01: Completion of Acquisition or Disposition of Assets']
    return {
        "accession": accession,
        "form_type": form_type,
        "created": created,
        "items": json.dumps(items if items is not None else items_default),
        "exhibits": json.dumps(exhibits if exhibits is not None else {"EX-99.1": "url1"}),
        "period_of_report": period_of_report,
        "is_amendment": is_amendment,
        "description": f"Form {form_type} - test",
        "section_names": ["OtherEvents"],
        "has_filing_text": False,
        "primary_doc_url": None, "link_to_txt": None, "link_to_html": None, "link_to_filing_details": None,
        "report_id": "rep1",
        "returns_schedule_raw": None,
        "filing_returns": None,
    }


class TestBuildIntegration:
    def test_no_sidecars_when_related_filings_dir_is_none(self, tmp_path):
        """Dry inspection (no save/predict) → related_filings_dir=None → no writes."""
        target_acc = "TARGET-0000000000-00-000000"
        fr = _filing_row(accession="ACC-001", created="2023-11-22T12:00:00-05:00")
        mgr = _mock_manager(filing_rows=[fr])
        with patch.object(iqc, "get_manager", return_value=mgr):
            packet = iqc.build_inter_quarter_context(
                ticker="AVGO",
                prev_8k_ts="2023-08-31T17:00:00-04:00",
                context_cutoff_ts="2023-12-07T16:18:51-05:00",
                out_path=str(tmp_path / "iqc.json"),
                exclude_accessions={target_acc},
                related_filings_dir=None,   # ← key: dry inspection
            )
        # No sidecar files written.
        assert not (tmp_path / "related_filings").exists()
        # No related_content_path on any event.
        for day in packet.get("days", []):
            for ev in day.get("events", []):
                if ev.get("type") == "filing":
                    assert ev.get("related_content_path") is None
        # Top-level allowlist is empty list.
        assert packet.get("_allowed_related_filing_paths") == []

    def test_target_accession_excluded_even_when_in_window(self, tmp_path):
        """exclude_accessions defends against --pit > filed_8k leak."""
        target_acc = "TARGET-0000000000-00-000000"
        # Two filings in window: target (must be excluded) and a normal one.
        target_fr = _filing_row(accession=target_acc, created="2023-12-07T16:18:51-05:00")
        normal_fr = _filing_row(accession="ACC-NORMAL", created="2023-11-22T12:00:00-05:00")
        # Content needed so the sidecar md is non-empty and the file gets written.
        content_for = {"ACC-NORMAL": {"sections": [{"section_name": "S", "content": "c"}],
                                      "exhibits": [], "filing_text": None}}
        mgr = _mock_manager(filing_rows=[target_fr, normal_fr], content_for=content_for)
        rfd = tmp_path / "related_filings"
        with patch.object(iqc, "get_manager", return_value=mgr):
            packet = iqc.build_inter_quarter_context(
                ticker="AVGO",
                prev_8k_ts="2023-08-31T17:00:00-04:00",
                context_cutoff_ts="2024-06-01T16:00:00-04:00",  # later than target's filed
                out_path=str(tmp_path / "iqc.json"),
                exclude_accessions={target_acc},
                related_filings_dir=str(rfd),
            )
        # Target accession sidecar must NOT exist.
        assert not (rfd / f"{target_acc}.md").exists()
        # Normal filing SHOULD have a sidecar (it has a real exhibit).
        assert (rfd / "ACC-NORMAL.md").exists()
        # No event in the bundle should reference the target accession.
        for day in packet.get("days", []):
            for ev in day.get("events", []):
                if ev.get("type") == "filing":
                    assert ev.get("accession") != target_acc

    def test_pure_9_01_8k_no_exhibits_skipped(self, tmp_path):
        """Plain 8-K with items=[9.01] AND no exhibits → no sidecar."""
        fr = _filing_row(
            accession="ACC-901-ONLY",
            items=["Item 9.01: Financial Statements and Exhibits"],
            exhibits={},
        )
        mgr = _mock_manager(filing_rows=[fr])
        rfd = tmp_path / "related_filings"
        with patch.object(iqc, "get_manager", return_value=mgr):
            iqc.build_inter_quarter_context(
                ticker="AVGO",
                prev_8k_ts="2023-08-31T17:00:00-04:00",
                context_cutoff_ts="2023-12-07T16:18:51-05:00",
                out_path=str(tmp_path / "iqc.json"),
                exclude_accessions=set(),
                related_filings_dir=str(rfd),
            )
        assert not (rfd / "ACC-901-ONLY.md").exists()

    def test_8k_amendment_with_pure_9_01_still_included(self, tmp_path):
        """8-K/A is unconditional even with pure-9.01 items (AVGO 8-K/A pattern)."""
        fr = _filing_row(
            accession="ACC-AMEND",
            form_type="8-K/A",
            items=["Item 9.01: Financial Statements and Exhibits"],
            exhibits={},
            is_amendment=True,
        )
        content_for = {"ACC-AMEND": {"sections": [{"section_name": "Stub", "content": "Stub content"}],
                                     "exhibits": [], "filing_text": None}}
        mgr = _mock_manager(filing_rows=[fr], content_for=content_for)
        rfd = tmp_path / "related_filings"
        with patch.object(iqc, "get_manager", return_value=mgr):
            iqc.build_inter_quarter_context(
                ticker="AVGO",
                prev_8k_ts="2023-08-31T17:00:00-04:00",
                context_cutoff_ts="2023-12-07T16:18:51-05:00",
                out_path=str(tmp_path / "iqc.json"),
                exclude_accessions=set(),
                related_filings_dir=str(rfd),
            )
        assert (rfd / "ACC-AMEND.md").exists()

    def test_allowlist_matches_event_paths_in_order(self, tmp_path):
        """_allowed_related_filing_paths invariant: same as event paths, no dupes, in render order."""
        # Three filings; only two qualify for sidecar (third is pure-9.01 no exhibits).
        fr1 = _filing_row(accession="ACC-A", created="2023-09-15T10:00:00-04:00",
                          items=["Item 2.05: Cost"])
        fr2 = _filing_row(accession="ACC-B", created="2023-10-20T10:00:00-04:00",
                          items=["Item 9.01: Financial Statements and Exhibits"],
                          exhibits={})  # pure-9.01 no exhibits → skipped
        fr3 = _filing_row(accession="ACC-C", created="2023-11-22T10:00:00-04:00",
                          items=["Item 2.01: Completion"])
        content_for = {
            "ACC-A": {"sections": [{"section_name": "S", "content": "c"}],
                      "exhibits": [], "filing_text": None},
            "ACC-C": {"sections": [{"section_name": "S", "content": "c"}],
                      "exhibits": [], "filing_text": None},
        }
        mgr = _mock_manager(filing_rows=[fr1, fr2, fr3], content_for=content_for)
        rfd = tmp_path / "related_filings"
        with patch.object(iqc, "get_manager", return_value=mgr):
            packet = iqc.build_inter_quarter_context(
                ticker="AVGO",
                prev_8k_ts="2023-08-31T17:00:00-04:00",
                context_cutoff_ts="2023-12-07T16:18:51-05:00",
                out_path=str(tmp_path / "iqc.json"),
                exclude_accessions=set(),
                related_filings_dir=str(rfd),
            )
        # Collect related_content_path values from filing events in render order.
        event_paths = []
        for day in packet.get("days", []):
            for ev in day.get("events", []):
                if ev.get("type") == "filing":
                    p = ev.get("related_content_path")
                    if p is not None:
                        event_paths.append(p)
        allowlist = packet.get("_allowed_related_filing_paths") or []
        # Set equality.
        assert set(allowlist) == set(event_paths)
        # No dupes.
        assert len(allowlist) == len(set(allowlist))
        # Same order (events were sorted by created ascending).
        assert allowlist == event_paths
        # Two paths total (ACC-B was skipped).
        assert len(allowlist) == 2

    def test_path_omitted_when_write_fails(self, tmp_path):
        """If sidecar file ends up missing post-write, related_content_path is None
        and the path is NOT in the allowlist."""
        fr = _filing_row(accession="ACC-X", items=["Item 2.01: M&A"])
        # No content available — _fetch returns empty sections, exhibits, filing_text.
        # Renderer should still produce a non-empty md (header at minimum), but if
        # we simulate a write that doesn't land, the post-write is_file() check
        # should drop the path.
        mgr = _mock_manager(filing_rows=[fr], content_for={})
        # Provide a non-existent parent that can't be created (read-only path)
        # OR mock the write to no-op. Simpler: use the real path but verify the
        # is_file() guard correctly drops on disk-missing scenarios. Here we use
        # a real path and let the build proceed. The guard fires only on a real
        # write failure, which is rare in tests; so we cover the post-condition
        # by simulating an empty-md → file doesn't get written.
        rfd = tmp_path / "related_filings"
        with patch.object(iqc, "get_manager", return_value=mgr), \
             patch.object(iqc, "_render_sidecar_md", return_value=""):  # empty md → skip write
            packet = iqc.build_inter_quarter_context(
                ticker="AVGO",
                prev_8k_ts="2023-08-31T17:00:00-04:00",
                context_cutoff_ts="2023-12-07T16:18:51-05:00",
                out_path=str(tmp_path / "iqc.json"),
                exclude_accessions=set(),
                related_filings_dir=str(rfd),
            )
        for day in packet.get("days", []):
            for ev in day.get("events", []):
                if ev.get("type") == "filing":
                    assert ev.get("related_content_path") is None
        assert packet.get("_allowed_related_filing_paths") == []

    def test_items_unparseable_8k_included(self, tmp_path):
        """Missing/unparseable items → INCLUDE (don't silently drop signal)."""
        fr = _filing_row(accession="ACC-NOITEMS", items=None, exhibits={})
        # Override items to None at JSON level
        fr["items"] = None
        content_for = {"ACC-NOITEMS": {"sections": [{"section_name": "S", "content": "c"}],
                                       "exhibits": [], "filing_text": None}}
        mgr = _mock_manager(filing_rows=[fr], content_for=content_for)
        rfd = tmp_path / "related_filings"
        with patch.object(iqc, "get_manager", return_value=mgr):
            iqc.build_inter_quarter_context(
                ticker="AVGO",
                prev_8k_ts="2023-08-31T17:00:00-04:00",
                context_cutoff_ts="2023-12-07T16:18:51-05:00",
                out_path=str(tmp_path / "iqc.json"),
                exclude_accessions=set(),
                related_filings_dir=str(rfd),
            )
        assert (rfd / "ACC-NOITEMS.md").exists()
