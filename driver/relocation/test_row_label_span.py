"""#824 structural-span step — the raw-label offset comes from the SELECTED
CELL'S OWN structural span, never from searching the text for its string.

WHAT THE MEASUREMENT ACTUALLY SHOWED, recorded because it differs from the
stated concern. The audit's reason for removing `find()` was that "a label may
lawfully appear twice in one row". Probed directly, that case does NOT diverge:
`row_label` is by construction the FIRST word-bearing, non-hidden cell left of
the fact, so it is always the FIRST occurrence in the row, and a bounded
forward `find()` lands on it. Four separate shapes were tried — label twice, a
digits-only cell first, an earlier cell containing the label as a substring, and
the label repeated in an earlier HIDDEN cell — and all four agreed.

The shape that DOES diverge is a label cell carrying hidden markup. `_text()`
uses `get_text()`, which includes hidden descendants, while the pinned
representation excludes them: the cell reads "Net XX sales" but the document
reads "Net sales", so `find()` returns -1 and the span is silently dropped to
null. The defect is LOST evidence, not wrong evidence — and a structural span
cannot have it, because the cell's extent is recorded when the text is walked.
"""
import json
import os

import pytest

from driver.relocation.inline_html import _evidence_from, prepare

_HEAD = ('<html><body><xbrli:context id="c1"><xbrli:entity><xbrli:identifier>'
         '0000320193</xbrli:identifier></xbrli:entity><xbrli:period>'
         '<xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>'
         '2024-06-30</xbrli:endDate></xbrli:period></xbrli:context>'
         '<xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure>'
         '</xbrli:unit>')
_FACT = ('<ix:nonFraction id="fA" name="us-gaap:A" contextRef="c1" '
         'unitRef="u1" scale="6" format="">726</ix:nonFraction>')


def _ev(body):
    prep = prepare(_HEAD + body + '</body></html>')
    ev, why = _evidence_from(prep['elements']['fA'], prep)
    assert ev is not None, why          # premise: the probe reached the code
    return prep, ev


def test_the_SELECTED_CELL_owns_the_span_when_a_label_appears_twice():
    """THE CONTROL the audit asked for. Stated honestly: this is GREEN under
    string search too, because the selected label is the first occurrence. It is
    kept because it pins WHICH cell owns the span — if selection ever changes to
    a later cell, string position would quietly disagree and this would fail."""
    prep, ev = _ev('<table><tr><td>Total</td><td>Total</td>'
                   f'<td>{_FACT}</td></tr></table>')
    span = ev['row_label_span']
    assert prep['text'][span[0]:span[1]] == 'Total'
    # it is the FIRST 'Total', and it is that cell's own recorded extent
    assert span[0] == prep['text'].index('Total')
    second = prep['text'].index('Total', span[1])
    assert span[1] <= second, "the span must not run into the second cell"


def test_a_label_cell_with_HIDDEN_MARKUP_keeps_its_span():
    """THE REAL RED CASE. `_text()` reads 'Net XX sales' (hidden text included);
    the representation reads 'Net sales'. A string search for the former finds
    nothing and drops the label span to null — evidence that structurally
    exists, lost to a lookup. The structural span cannot miss it."""
    prep, ev = _ev('<table><tr><td>Net <span style="display:none">XX</span>'
                   f'sales</td><td>{_FACT}</td></tr></table>')
    span = ev['row_label_span']
    assert span is not None, "the label cell exists; its span must survive"
    assert prep['text'][span[0]:span[1]] == 'Net sales'
    # The old route searched for `_text(cell)` — the string WITH the hidden
    # words in it. Proving that string is absent from the representation is
    # what shows the span could only ever have been dropped, so this test
    # cannot pass for the wrong reason.
    from driver.relocation.inline_html import _text
    old_label = _text(prep['elements']['fA'].find_parent('tr')
                      .find_all(['td', 'th'], recursive=False)[0])
    assert old_label == 'Net XX sales'
    assert prep['text'].find(old_label, *ev['row_span']) == -1


def test_no_label_cell_yields_the_approved_null_rather_than_a_guess():
    prep, ev = _ev(f'<table><tr><td>{_FACT}</td><td>Total</td></tr></table>')
    assert ev['row_label'] == '' and ev['row_label_span'] is None


def test_a_prose_element_has_no_row_label_span():
    prep, ev = _ev(f'<p>Revenue was {_FACT} million.</p>')
    assert ev['row_label_span'] is None


def test_the_label_EQUALS_the_visible_text_at_its_own_span():
    """CORRECTED at the structural-evidence step. This used to assert the
    OPPOSITE — that the span length differs from the label length — which
    pinned the very defect Fiscal's audit then measured: the label carried
    hidden text its own span did not cover. The law is now that the two ARE the
    same text, so the old assertion was the law we had to fix, not a proof."""
    prep, ev = _ev('<table><tr><td>Net <span style="display:none">XX</span>'
                   f'sales</td><td>{_FACT}</td></tr></table>')
    a, b = ev['row_label_span']
    assert ev['row_label'] == prep['text'][a:b] == 'Net sales'


# --- the structural-evidence step: one visible-text rule for every field ----

def test_a_HIDDEN_ONLY_cell_cannot_become_the_label():
    """The sharpest of the three: a cell whose only text is hidden was eligible,
    so the label became a string that does not appear in the filing at all,
    carrying a span that covers nothing."""
    prep, ev = _ev('<table><tr><td><span style="display:none">GHOST</span></td>'
                   f'<td>Real</td><td>{_FACT}</td></tr></table>')
    assert 'GHOST' not in prep['text']
    assert ev['row_label'] == 'Real'
    a, b = ev['row_label_span']
    assert prep['text'][a:b] == 'Real'


def test_row_cells_exclude_hidden_descendants():
    """The hidden-percent row. The cell itself is visible, so it survived the
    cell-level hidden check, but its TEXT was read with `get_text` and carried
    the hidden word into evidence."""
    prep, ev = _ev('<table><tr><td>Margin <span style="display:none">HIDDEN'
                   f'</span>%</td><td>{_FACT}</td></tr></table>')
    assert not any('HIDDEN' in c for c in ev['row_cells']), ev['row_cells']
    assert ev['row_cells'][0] == 'Margin %'
    # every cell must be text the representation actually holds
    for c in ev['row_cells']:
        assert c in ev['row_text'], (c, ev['row_text'])


def test_section_TEXT_and_SPAN_come_from_the_SAME_cell():
    """Two cells, and the two outputs used DIFFERENT filters: the text skipped
    the digit-bearing cell, the span did not — so they described different
    cells."""
    prep, ev = _ev('<table><tr><td>Q1 2023</td><td>Segment detail</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    a, b = ev['section_span']
    assert prep['text'][a:b].strip(' —-') == ev['section'] == 'Segment detail'


def test_a_hidden_only_cell_does_not_COUNT_as_a_section_label():
    """The same visible-text rule, applied to the section's own selection.

    A section is taken only when the row has EXACTLY ONE eligible label cell.
    Reading hidden text made the ghost cell eligible, so the count came to two
    and a real section heading was lost — the hidden markup did not corrupt the
    answer, it suppressed it. The cell placement matters: the ghost sits AFTER
    the heading, because a hidden-only FIRST cell is an empty first cell under
    either rule and cannot tell the two apart."""
    prep, ev = _ev('<table><tr><td>Segment detail</td>'
                   '<td><span style="display:none">GHOST</span></td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    assert 'GHOST' not in prep['text']
    a, b = ev['section_span']
    assert prep['text'][a:b].strip(' —-') == ev['section'] == 'Segment detail'


# --- evidence exactness: stored text IS the slice, for every piece ----------
#
# Fiscal's full-corpus audit: 413 headers and 133 sections stored TRIMMED text
# beside an UNTRIMMED span. Trimming may decide whether a cell is worth keeping;
# it may never decide what gets stored, because the stored text is supposed to
# be the filing's own characters at that offset.

def test_a_header_with_a_LEADING_DASH_stores_the_EXACT_slice():
    prep, ev = _ev('<table><tr><td>Segment</td><td>— Americas</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    pairs = list(zip(ev['columns'], ev['column_spans']))
    assert pairs, "the header stack must still be selected"
    for text, span in pairs:
        assert span is not None
        assert text == prep['text'][span[0]:span[1]], (text, span)
    assert '— Americas' in ev['columns'], ev['columns']


def test_a_header_with_a_TRAILING_DASH_stores_the_EXACT_slice():
    prep, ev = _ev('<table><tr><td>Segment</td><td>Americas —</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    for text, span in zip(ev['columns'], ev['column_spans']):
        assert text == prep['text'][span[0]:span[1]], (text, span)
    assert 'Americas —' in ev['columns'], ev['columns']


def test_a_DASHES_ONLY_header_is_still_skipped():
    """SELECTION may trim — only selection. A cell that is nothing but a dash
    carries no header, and must stay skipped exactly as before."""
    prep, ev = _ev('<table><tr><td>Segment</td><td>—</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    assert '—' not in ev['columns'] and '' not in ev['columns'], ev['columns']


def test_a_header_with_hidden_markup_stores_only_visible_text():
    prep, ev = _ev('<table><tr><td>Segment</td>'
                   '<td>Amer<span style="display:none">ZZ</span>icas</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    assert 'ZZ' not in prep['text']
    for text, span in zip(ev['columns'], ev['column_spans']):
        assert text == prep['text'][span[0]:span[1]], (text, span)


def test_a_section_with_a_LEADING_DASH_stores_the_EXACT_slice():
    prep, ev = _ev('<table><tr><td>— Segment detail</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    a, b = ev['section_span']
    assert ev['section'] == prep['text'][a:b] == '— Segment detail'


def test_a_MARKER_PREFIXED_parenthetical_is_not_selected_as_a_section():
    """The parenthetical filter tested the UNTRIMMED text, so a leading dash
    walked a parenthetical straight past it. Markers are ignored for the
    SELECTION decision only."""
    prep, ev = _ev('<table><tr><td>— (Loss)</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    assert ev['section'] == '' and ev['section_span'] is None


def test_a_BARE_parenthetical_is_still_not_selected():
    """The pre-existing half of the same rule, pinned so the fix cannot be
    mistaken for the whole of it."""
    prep, ev = _ev('<table><tr><td>(Loss)</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    assert ev['section'] == '' and ev['section_span'] is None


def test_the_edge_marker_set_has_exactly_ONE_owner():
    """DERIVED from source. The set was about to be written a third time; a
    marker list with several authors drifts, and drift here silently changes
    which headings count as sections. The searched literal is built from
    fragments so this test can never match itself."""
    import pathlib
    marker = "' " + "—" + "-'"
    src = pathlib.Path('driver/relocation/inline_html.py').read_text()
    assert src.count(marker) == 1, (
        f"the edge-marker set appears {src.count(marker)}x — it has one owner")


def test_the_locator_compares_evidence_EXACTLY_not_after_trimming():
    """DERIVED from source: a comparison that trims before comparing accepts a
    stored string that is not what the span holds, which is the defect."""
    import pathlib
    src = pathlib.Path('driver/relocation/locator.py').read_text()
    banned = "strip(' " + "—-')"        # built from parts: never self-match
    assert banned not in src, "locator still trims before comparing evidence"


# --- the real-data parity proof -------------------------------------------

_PACKETS = ("data/driver_catalog_seed/wp3_ce_compliant/packets.jsonl",
            "data/driver_catalog_seed/wp3_aci_stream/packets.jsonl")
_CACHE = os.path.join("scripts", "driver_seed", "relocate_probe",
                      "inline_html_cache")


def _saved_items():
    out = []
    for path in _PACKETS:
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            if line.strip():
                pkt = json.loads(line)
                out += [(pkt["source_id"], it) for it in pkt["items"]]
    return out


@pytest.mark.skipif(not os.path.isdir(_CACHE), reason="filing cache absent")
def test_ALL_ELEVEN_saved_packet_label_spans_are_reproduced_EXACTLY():
    """Output parity on the pinned corpus: the structural span must reproduce
    every saved `raw_label_span` byte-for-byte, so the change cannot move a
    single published packet. Premises asserted first — 11 items, and each item's
    representation hash must reproduce from its cached filing, or nothing below
    is measuring the document the packet declares."""
    items = _saved_items()
    assert len(items) == 11, f"the pinned corpus is 11 items, got {len(items)}"
    checked = 0
    for source_id, it in items:
        path = os.path.join(_CACHE, f"{source_id}.htm")
        assert os.path.exists(path), source_id
        with open(path, encoding="utf-8", errors="replace") as fh:
            prep = prepare(fh.read())
        se = it["xbrl"]["source_evidence"]
        assert se["representation_sha256"] == prep["text_sha"], source_id
        want_row = tuple(se["quote_span"])
        # the element whose ROW is this item's quote row; every fact in that row
        # shares the row's label cell, which is the value under test
        spans = []
        for el in prep["elements"].values():
            ev, _why = _evidence_from(el, prep)
            if ev and ev.get("row_span") == want_row:
                spans.append((ev["row_label_span"],
                              (ev["section"], ev["section_span"])))
        assert spans, f"no element found on the saved row for {source_id}"
        saved = se["raw_label_span"]
        want = None if saved is None else tuple(saved)
        for got, _sec in spans:
            assert (None if got is None else tuple(got)) == want, \
                f"{source_id}: label span moved {want} -> {got}"
        # AND the section piece, because the same step changed how a section's
        # text and span are chosen. A saved section piece must still be produced
        # exactly — same text, same span.
        saved_sections = [p for p in se["pieces"] if p["kind"] == "section"]
        for piece in saved_sections:
            assert any(text == piece["text"] and list(span) == list(piece["span"])
                       for _lab, (text, span) in spans), \
                f"{source_id}: section piece moved: {piece}"
        checked += 1
    assert checked == 11
