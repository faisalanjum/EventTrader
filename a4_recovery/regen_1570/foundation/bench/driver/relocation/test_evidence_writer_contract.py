"""EU-187 (#827): the evidence WRITER's contract, in its own module.

The primary suite (test_packet_items_through_the_door) rebuilds evidence
from the saved corpus AT IMPORT TIME, so a writer-key drift ERRORS its
collection (rc=4) instead of failing a node — it cannot host an
exit-1-exactly detector. The card's split-visibly clause applies: this
sibling file carries the one self-contained writer node.
"""
def test_EU187_the_evidence_writer_emits_exactly_the_sheets_four_keys():
    """EU-187 (#827): source_evidence() WRITES the contract-sheet section-2
    record — proven on a minimal synthetic element so the writer's own key
    spellings are pinned self-contained (the door suites consume this writer
    at module level, where a drift ERRORS collection instead of failing a
    node; this node fails cleanly)."""
    from driver.relocation.inline_html import (SOURCE_EVIDENCE_KEYS,
                                               source_evidence)
    text = "Revenue 726"
    prepared = {"text": text, "text_sha": "0" * 64}
    ev = {"in_table": False, "block": text, "block_span": [0, len(text)],
          "row_text": None, "row_span": None, "row_label_span": [0, 7],
          "columns": [], "column_spans": [], "section": None,
          "section_span": None}
    rec = source_evidence(prepared, ev)
    assert rec is not None
    assert set(rec) == set(SOURCE_EVIDENCE_KEYS), \
        "the writer emits EXACTLY the sheet's four keys"
    assert rec["quote_span"] == [0, len(text)]
    assert rec["representation_sha256"] == "0" * 64
