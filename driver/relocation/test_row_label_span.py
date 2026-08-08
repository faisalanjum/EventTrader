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

_HEAD = ('<html xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:utr="http://example.org/utr" xmlns:us-gaap="http://example.org/us-gaap" xmlns:dei="http://example.org/dei" xmlns:srt="http://example.org/srt" xmlns:a="http://example.org/a" xmlns:x="http://example.org/x" xmlns:aapl="http://example.org/aapl" xmlns:slg="http://example.org/slg" xmlns:accd="http://example.org/accd" xmlns:ed="http://example.org/ed" xmlns:dvn="http://example.org/dvn" xmlns:fcx="http://example.org/fcx" xmlns:nog="http://example.org/nog" xmlns:inst="http://example.org/inst" xmlns:dimns="http://example.org/dimns" xmlns:nope="http://example.org/nope" xmlns:geo="http://example.org/geo" xmlns:eqt="http://example.org/eqt" xmlns:geography="http://example.org/geography" xmlns:seg="http://example.org/seg" xmlns:country="http://example.org/country"><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">'
         '0000320193</xbrli:identifier></xbrli:entity><xbrli:period>'
         '<xbrli:startDate>2024-01-01</xbrli:startDate><xbrli:endDate>'
         '2024-06-30</xbrli:endDate></xbrli:period></xbrli:context></ix:resources></ix:header>'
         '<ix:header><ix:resources><xbrli:unit id="u1"><xbrli:measure>iso4217:USD</xbrli:measure>'
         '</xbrli:unit></ix:resources></ix:header>')
_FACT = ('<ix:nonFraction id="fA" name="us-gaap:A" contextRef="c1" '
         'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction>')


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
    # The old route searched for the cell's LEAKY reading — the string WITH
    # the hidden words in it, which `get_text` still produces and `_text` no
    # longer does (#827 E made `_text` the visible walk). Proving that leaky
    # string is absent from the representation is what shows the span could
    # only ever have been dropped, so this test cannot pass for the wrong
    # reason. `.ren` is the RENDERER half of the bridged fact.
    cell0 = (prep['elements']['fA'].ren.find_parent('tr')
             .find_all(['td', 'th'], recursive=False)[0])
    leaky = ' '.join(cell0.get_text(' ', strip=True).split())
    assert leaky == 'Net XX sales'
    assert prep['text'].find(leaky, *ev['row_span']) == -1
    # ...and the ONE renderer-text owner now agrees with the representation:
    from driver.relocation.inline_html import _text
    assert _text(cell0) == 'Net sales'


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


@pytest.mark.parametrize('cp', [0x2010, 0x2011, 0x2012, 0x2013, 0x2015,
                                0x2014, 0x002D])
def test_a_DASH_ONLY_header_is_skipped_whatever_the_DASH_IS(cp):
    """The set was hand-written as three characters — space, EM DASH,
    HYPHEN-MINUS — so a cell holding only EN DASH survived the selection test
    and was counted as a column heading. Measured over the frozen manifest:
    3,050 heading decisions across 38 filings, every one a lone U+2013.

    Unicode's own `General_Category=Dash_Punctuation` is the standard that says
    which characters these are; the hand-written three were a sample."""
    dash = chr(cp)
    prep, ev = _ev(f'<table><tr><td>Segment</td><td>{dash}</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    assert dash not in ev['columns'] and '' not in ev['columns'], \
        f'U+{cp:04X} alone was counted as a heading: {ev["columns"]}'


def test_a_MINUS_SIGN_is_content_not_a_dash_marker():
    """MUST-ALLOW twin, and the honest limit of the rule. U+2212 MINUS SIGN is
    category `Sm`, not `Pd` — neither the old three characters nor the Unicode
    category treats it as a marker, so a cell holding one is real content and
    stays selected."""
    prep, ev = _ev('<table><tr><td>Segment</td><td>−</td></tr>'
                   f'<tr><td>Revenue</td><td>{_FACT}</td></tr></table>')
    assert '−' in ev['columns'], ev['columns']


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


@pytest.mark.parametrize('open_t,close_t', [
    ('<span>', '</span>'), ('<h2>', '</h2>'),
    ('<blockquote>', '</blockquote>'), ('', '')])
def test_a_fact_in_ANY_lawful_container_can_still_be_DESCRIBED(open_t, close_t):
    """`_evidence_from` reads `node.parent` when a fact has no `td`/`th` inside
    a `tr` and no `p`/`li`/`div` ancestor — but the walker was only ever asked
    to record those six tags, so that parent had no span, `block_span` came back
    None and `source_evidence` refused the fact ENTIRELY. Not a missing field: a
    lawful fact that cannot be described at all.

    Seen first on the official conformance document
    `PASS-relationship-with-xml-base.html`. The last case is direct body
    content, with no wrapper at all."""
    from driver.relocation.inline_html import source_evidence
    prep, ev = _ev(f'{open_t}Revenue {_FACT}{close_t}')
    assert ev['block_span'] is not None, 'the fact has no reproducible block'
    assert source_evidence(prep, ev) is not None, \
        'no lawful evidence can be built for this fact'


@pytest.mark.parametrize('open_t,close_t', [
    ('<p>', '</p>'), ('<div>', '</div>'), ('<li>', '</li>'),
    ('<table><tr><td>', '</td></tr></table>'),
    ('<table><tr><th>', '</th></tr></table>')])
def test_the_EXISTING_container_owners_are_untouched(open_t, close_t):
    """MUST-ALLOW twin: the six tags keep working exactly as before, so the
    change adds owners rather than replacing the rule."""
    from driver.relocation.inline_html import source_evidence
    prep, ev = _ev(f'{open_t}Revenue {_FACT}{close_t}')
    span = ev['row_span'] if ev['in_table'] else ev['block_span']
    assert span is not None
    assert source_evidence(prep, ev) is not None


def test_a_HIDDEN_fact_still_has_NO_visible_evidence():
    """MUST-REFUSE control. A fact inside a CSS-hidden block is not displayed,
    so it has no visible evidence and must not acquire one — the corpus's 6,091
    span-less facts are all of exactly this kind, and they are correct."""
    from driver.relocation.inline_html import source_evidence
    prep, ev = _ev(f'<div style="display:none">Revenue {_FACT}</div>')
    assert ev['block_span'] is None
    assert source_evidence(prep, ev) is None


# `test_the_edge_marker_set_has_exactly_ONE_owner` STOOD HERE and is DELETED,
# not replaced. It counted the literal `' —-'` in the source and required
# exactly one. That set no longer exists — the rule asks Unicode for the
# character's category — so the test was passing only because the retired
# literal still appears inside `_is_edge_marker`'s docstring, explaining its own
# removal. A test that green-lights on a comment is worse than no test. What
# proves the rule now is behavioural: the dash-only bad cases, the MINUS SIGN
# twin, and the final mutation battery.


def test_the_XML_S_production_has_exactly_ONE_owner():
    """DERIVED from source, and the same rule as the edge-marker pin above.

    XML 1.0 5e §2.3 defines S as exactly #x20, #x9, #xD, #xA. That set was
    written twice — `exact_numbers.XML_WS` and `inline_html.XML_S` — with
    `inline_html` importing the first while still declaring the second, and a
    comment above the import claiming there was only one owner. `xbrl_attach`
    imports one name and `inline_html` uses the other, so a change to either
    would silently move half the consumers.

    The literal is assembled from fragments so this test can never match
    itself.
    """
    import pathlib
    ws = " " + "\\" + "t" + "\\" + "r" + "\\" + "n"
    found = []
    for rel in ('driver/relocation/inline_html.py',
                'driver/relocation/exact_numbers.py'):
        src = pathlib.Path(rel).read_text()
        found += [rel] * (src.count('"' + ws + '"') + src.count("'" + ws + "'"))
    assert len(found) == 1, (
        f"the XML S production is declared {len(found)}x, in {found} — "
        "it must have exactly one owner")


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

# The seven speculative #827-D pins that stood here are DELETED with the
# half-applied D implementation they pinned (SEQ 220 §1): neither the
# three-shape nor the conservative geometry is approved, production is
# restored to the exact pre-D rule, and the final pins land only with the
# ruling the complete 49-file loss/change classification produces.


# --- #827 E: the inline-style visibility law (SEQ 220 §2, approved) ---------
# ONE tinycss2 declaration read at the one boundary. Per property the winner is
# (important, then later source order); the value must be the single ident;
# display:none and visibility:hidden|collapse hide. Inline style attributes and
# ancestry ONLY — no stylesheet or selector engine, and aria-hidden is an
# accessibility property, not a visual one (0 occurrences in 1,769 filings).

@pytest.mark.parametrize("style,want", [
    ("display:none", True),
    ("DISPLAY : NoNe", True),
    ("visibility:hidden", True),
    ("visibility:collapse", True),                 # CSS 2.2 §11.2 — the regex
    ("color:red;display:none", True),              # missed all 11,053 of these
    ("display:none !important; display:block", True),   # Cascade 4 §6.1
    ("display:none; display:block !important", False),  # important wins
    ("display:none !important; display:block !important", False),  # later wins
    ("visibility:hidden;visibility:visible", False),     # later source order
    ("display:none;display:block", False),
    ("--x:display:none", False),                   # custom property is not a decl
    ('content:"display:none"', False),             # a string is not the ident
    ("display:none-x", False),                     # an ident PREFIX is not none
    ("display:block", False),
    ('display: none "x"', False),                  # SEQ 221: a string BESIDE the
    ("visibility: hidden 1px", False),             # ident, or a dimension, means
                                                   # no supported hiding value
    ("display: /* why */ none /* not */", True),   # comments/space still hide
    # SEQ 222/224: an INVALID later declaration never enters the cascade, so
    # it cannot erase an earlier VALID winner — while a valid later one wins.
    ('display:none; display:none "x"', True),
    ("visibility:hidden; visibility:hidden 1px", True),
    ("display:none; display:block", False),        # the lawful override twin
])
def test_E_the_inline_style_law_decides_by_DECLARATION_not_substring(style, want):
    from bs4 import BeautifulSoup
    # the attribute is SET, never interpolated into markup: a style value that
    # itself contains quotes must reach the parser intact, not truncate the
    # HTML attribute it rides in
    cell = BeautifulSoup('<td>x</td>', 'lxml').td
    cell['style'] = style
    from driver.relocation.inline_html import _hidden_cell
    assert _hidden_cell(cell) is want, (style, want)


def test_E_aria_hidden_no_longer_pretends_to_be_CSS():
    """ARIA removes content from the accessibility tree; it is not a visual
    rendering rule, no frozen contract owns it, and the corpus count is zero."""
    from bs4 import BeautifulSoup
    from driver.relocation.inline_html import _hidden_cell
    cell = BeautifulSoup('<td aria-hidden="true">x</td>', 'lxml').td
    assert _hidden_cell(cell) is False
    hard = BeautifulSoup('<td hidden>x</td>', 'lxml').td   # the HTML attribute stays
    assert _hidden_cell(hard) is True


def test_E_displayed_EXCLUDES_a_hidden_descendant():
    """`displayed` used to read `get_text`, which leaks text the walker
    excludes — the two-normalizer split SEQ 220 closes: `_text` IS the visible
    walk now, honoring the hidden argument. The only LAWFUL hidden descendant
    a nonFraction can carry is a NESTED nonFraction (Inline XBRL 1.1 §10.1.1
    admits exactly one child, itself a nonFraction), so the twin nests one and
    hides it with CSS: the page shows nothing, and `displayed` must agree —
    the old reader reported the hidden '726'."""
    prep, ev = _ev('<table><tr><td>Revenue</td>'
                   '<td><ix:nonFraction id="fA" name="us-gaap:A" contextRef="c1"'
                   ' unitRef="u1" scale="0" decimals="0">'
                   '<ix:nonFraction id="fInner" name="us-gaap:A" contextRef="c1"'
                   ' unitRef="u1" scale="0" decimals="0"'
                   ' style="display:none">726</ix:nonFraction>'
                   '</ix:nonFraction></td></tr></table>')
    assert ev['displayed'] == '', repr(ev['displayed'])
    # the STRICT fact content is untouched by rendering: the value still reads
    assert ev['value_input'] == '726'


# --- #827 E final: the official-grammar state law (SEQ 227/229) -------------
# Owners: CSS Display Module Level 3 (CR Draft 5 June 2026) §1.2/§2 (display
# grammar, ||/&& order independence, legacy), §4 (visibility, including the
# visibility:visible descendant REVIVE under a hidden ancestor); CSS Cascade
# Level 5 §§4-7 (declaration filtering, cascade, CSS-wide keywords, `all`);
# CSS Containment Level 2 §4 (content-visibility, viewport-independent product
# reading: auto INCLUDES); HTML Living Standard §6.1 (the hidden attribute is
# an OVERRIDABLE presentational hint, not an absolute prune).

def _cellE(style=None, **attrs):
    from bs4 import BeautifulSoup
    cell = BeautifulSoup('<td>x</td>', 'lxml').td
    if style is not None:
        cell['style'] = style
    for k, v in attrs.items():
        cell[k] = v
    return cell


@pytest.mark.parametrize("style,want", [
    # two-keyword Display-3 values are LAWFUL and win by cascade order
    ("display:none; display:block flow", False),
    ("display:block flow; display:none", True),
    ("display:flow block", False),                 # || is order-independent
    ("display:list-item", False),
    ("display:block flow list-item", False),
    ("display:contents", False),
    # a DEFINITELY INVALID later declaration never erases an earlier winner
    ("display:none; display:block hidden", True),  # 'hidden' is not a display kw
    ("display:none; display:1px", True),
    # CSS-wide keywords, decidable locally (Cascade L5 §7)
    ("display:none; display:initial", False),      # initial display is inline
    ("display:none; display:unset", False),
    ("visibility:hidden; visibility:initial", False),
    ("visibility:hidden; visibility:unset", False),
])
def test_E2_the_display_grammar_is_the_SPEC_not_a_single_ident(style, want):
    from driver.relocation.inline_html import _hidden_cell
    assert _hidden_cell(_cellE(style)) is want, style


@pytest.mark.parametrize("style", [
    "display: var(--d)",            # substitution — winner unknowable here
    "display:none; display: var(--d)",
    "visibility: revert",           # rollback needs cascade state we do not own
    "visibility: revert-layer",
])
def test_E2_an_UNRESOLVABLE_winner_is_the_truthful_unsupported_lane(style):
    """Never silently visible, never silently invalid: the reader must answer
    'unsupported', and a FACT whose chain carries it must refuse with the one
    named reason rather than guess."""
    from driver.relocation.inline_html import _style_state
    st = _style_state(_cellE(style))
    assert st.get('unsupported'), st


def test_E2_content_visibility_official_values():
    """Containment L2 §4 + the frozen viewport-independent product reading:
    auto INCLUDES (all 714 real declarations), hidden PRUNES absolutely,
    visible includes."""
    from driver.relocation.inline_html import _hidden_cell
    assert _hidden_cell(_cellE("content-visibility:auto")) is False
    assert _hidden_cell(_cellE("content-visibility:visible")) is False
    assert _hidden_cell(_cellE("content-visibility:hidden")) is True


def test_E2_content_visibility_hidden_has_NO_revive():
    """Unlike visibility, a cv:hidden subtree is skipped absolutely —
    a descendant visibility:visible cannot bring it back."""
    prep, ev = _ev('<table><tr>'
                   '<td style="content-visibility:hidden">'
                   '<span style="visibility:visible">GONE</span>Revenue</td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert 'GONE' not in prep['text']
    assert ev['row_label'] == ''


def test_E2_the_hidden_ATTRIBUTE_is_overridable_per_HTML_LS():
    """HTML Living Standard §6.1: CSS can override the hidden state."""
    from driver.relocation.inline_html import _hidden_cell
    assert _hidden_cell(_cellE(None, hidden="")) is True          # bare: hidden
    assert _hidden_cell(_cellE("display:block", hidden="")) is False   # revealed
    assert _hidden_cell(_cellE("display:block; display:none",
                               hidden="")) is True                # author none wins
    from driver.relocation.inline_html import _style_state
    st = _style_state(_cellE(None, hidden="until-found"))
    assert st.get('unsupported'), st       # official case, zero incidence lane


def test_E2_visibility_visible_REVIVES_under_a_hidden_ancestor():
    """CSS Display 3 §4 — the walk carries inherited visibility state."""
    prep, ev = _ev('<table><tr>'
                   '<td style="visibility:hidden">dark '
                   '<span style="visibility:visible">LIT</span></td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert 'LIT' in prep['text']
    assert 'dark' not in prep['text']
    assert ev['row_label'] == 'LIT'


def test_E2_display_none_ancestor_prunes_with_NO_revive():
    prep, ev = _ev('<table><tr>'
                   '<td style="display:none">gone '
                   '<span style="visibility:visible">ALSO GONE</span></td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert 'ALSO GONE' not in prep['text'] and 'gone' not in prep['text']


def test_E2_a_vis_hidden_FACT_with_its_own_visible_is_not_hidden():
    prep = prepare(_HEAD + '<table><tr><td>Revenue</td>'
                   '<td style="visibility:hidden">'
                   '<ix:nonFraction id="fA" name="us-gaap:A" contextRef="c1" '
                   'unitRef="u1" scale="0" decimals="0" '
                   'style="visibility:visible">7</ix:nonFraction>'
                   '</td></tr></table></body></html>')
    ev, why = _evidence_from(prep['elements']['fA'], prep)
    assert ev is not None, why
    assert ev['hidden'] is False
    assert ev['displayed'] == '7'


def test_E2_an_UNRESOLVABLE_winner_parks_the_WHOLE_document():
    """SEQ 231 §3: doc-level, not span-level. An unresolvable style anywhere
    makes every visibility claim in the filing a guess — including a CLEAN
    fact whose LABEL SIBLING carries the bad style — so the document refuses
    once, truthfully, and nothing in it binds or quotes."""
    from driver.relocation.inline_html import refused
    # the fact itself carries the unresolvable winner
    prep = prepare(_HEAD + '<table><tr><td>Revenue</td>'
                   '<td style="display:var(--d)">'
                   '<ix:nonFraction id="fA" name="us-gaap:A" contextRef="c1" '
                   'unitRef="u1" scale="0" decimals="0">7</ix:nonFraction>'
                   '</td></tr></table></body></html>')
    assert str(refused(prep)).startswith('unsupported_style'), refused(prep)
    # THE SIBLING ATTACK: the fact's ancestry is clean; only the label cell
    # beside it is unresolvable. Guessed-visible label text must not attach.
    prep = prepare(_HEAD + '<table><tr>'
                   '<td style="display:attr(data-d)">Revenue</td>'
                   f'<td>{_FACT}</td></tr></table></body></html>')
    assert str(refused(prep)).startswith('unsupported_style'), refused(prep)


def test_E2_unset_INHERITS_for_visibility_per_Cascade_5():
    """Cascade 5 §7.3.3: unset = inherit for an inherited property. Under a
    hidden ancestor, visibility:unset STAYS hidden; visibility:initial (and a
    real visibility:visible) revive. `all:unset` behaves like unset."""
    prep, ev = _ev('<table><tr>'
                   '<td style="visibility:hidden">dark '
                   '<span style="visibility:unset">STILL DARK</span>'
                   '<span style="visibility:initial">BRIGHT</span>'
                   '<span style="all:unset">ALSO DARK</span></td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert 'STILL DARK' not in prep['text']
    assert 'ALSO DARK' not in prep['text']
    assert 'BRIGHT' in prep['text']


def test_E2_the_hidden_value_match_is_EXACT_ASCII_no_repair():
    """HTML enumerated attributes match keywords ASCII-case-insensitively with
    NO whitespace repair: UPPERCASE UNTIL-FOUND is the official state; a
    padded ' until-found ' is an INVALID VALUE and takes the invalid-value
    default — the Hidden state — never the unsupported lane."""
    from driver.relocation.inline_html import _style_state, _advance
    st = _style_state(_cellE(None, hidden="UNTIL-FOUND"))
    assert st.get('unsupported'), st
    prune, _vis, unsup = _advance('visible', _cellE(None, hidden=" until-found "))
    assert unsup is None and prune is True
    prune, _vis, unsup = _advance('visible', _cellE(None, hidden=" until-found"))
    assert unsup is None and prune is True


def test_E2_force_hidden_is_UNSUPPORTED_never_a_fallback():
    """CSS Display 4 §5: `visibility:force-hidden` denies descendant
    self-revive — a state this reader does not model. It must NOT be dropped
    so that an earlier `hidden` quietly wins (SEQ 232 §1), and no descendant
    `visibility:visible` may mint guessed evidence under it: the document
    takes the one truthful unsupported refusal."""
    from driver.relocation.inline_html import refused
    prep = prepare(_HEAD + '<table><tr>'
                   '<td style="visibility:hidden; visibility:force-hidden">'
                   'dark <span style="visibility:visible">TEMPTING</span></td>'
                   f'<td>{_FACT}</td></tr></table></body></html>')
    assert str(refused(prep)).startswith('unsupported_style'), refused(prep)


def test_E2_a_REVIVED_cell_can_still_be_a_column_header():
    """`_aligned_columns` no longer asks a standalone per-cell question: the
    slice owns visibility, so a header cell hidden by inheritance but revived
    by visibility:visible keeps its place in the stack."""
    prep, ev = _ev('<table>'
                   '<tr><td>a</td><td style="visibility:hidden">'
                   '<span style="visibility:visible">H1</span></td></tr>'
                   f'<tr><td>x</td><td>{_FACT}</td></tr></table>')
    assert 'H1' in ev['columns'], ev['columns']


def test_E2_the_all_shorthand_resets_both_properties():
    """Cascade L5: `all` accepts only CSS-wide keywords and feeds every
    property's cascade — including content-visibility."""
    from driver.relocation.inline_html import _hidden_cell
    assert _hidden_cell(_cellE("visibility:hidden; all:initial")) is False
    assert _hidden_cell(_cellE("all:initial; visibility:hidden")) is True
    assert _hidden_cell(_cellE("content-visibility:hidden; all:unset")) is False
    # `all` with a non-wide value is INVALID and erases nothing
    assert _hidden_cell(_cellE("visibility:hidden; all:none")) is True


# (SEQ 234: the assert-True "census pin" that stood here is DELETED — prose
# is not a test. The census lives in its receipts, not in a green checkmark.)


def test_E3_comments_scripts_and_declarations_are_NOT_text():
    """SEQ 234: `name is None` also matches Comment/CData/PI/Declaration/
    Doctype nodes, and HTML LS Rendering §15.3.1 defaults script/style/
    template (and friends) to display:none. None of it is displayed evidence."""
    prep, ev = _ev('<table><tr>'
                   '<td><!--COMMENT--><script>GHOST</script>'
                   '<style>.secret{display:none}</style>'
                   '<template>SPOOK</template>Label</td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert ev['row_label'] == 'Label', repr(ev['row_label'])
    for ghost in ('COMMENT', 'GHOST', '.secret', 'SPOOK'):
        assert ghost not in prep['text'], ghost


def test_E3_ua_defaults_are_NORMAL_origin_and_inline_display_overrides():
    """The MUST-ALLOW twin: `rp` is UA-hidden by §15.3.1, and a lawful inline
    display reveals it — a UA default never outranks an author declaration."""
    prep, ev = _ev('<table><tr>'
                   '<td><rp>HIDDEN RP</rp>'
                   '<rp style="display:inline">SHOWN RP</rp>Label</td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert 'HIDDEN RP' not in prep['text']
    assert 'SHOWN RP' in prep['text']
    assert ev['row_label'].startswith('SHOWN RP')


def test_E3_noscript_renders_because_this_reader_has_NO_scripting():
    """Stated, not guessed: with scripting disabled, HTML LS does not hide
    noscript — its contents are ordinary rendered text here."""
    prep, ev = _ev('<table><tr><td><noscript>NS</noscript>Label</td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert ev['row_label'] == 'NS Label'


# --- #827 SEQ 246: BeautifulSoup equality is NOT identity -------------------
# Tag.__eq__ is STRUCTURAL, so `.index()`/`in` on rows and cells can resolve a
# fact into a look-alike sibling: wrong headers, wrong spans, wrong column —
# shipping silently until the falsified-invariant crash exposed it on the
# real filing 0001193125-23-203780.htm (4 no-id facts, row 22-by-equality vs
# row 40-by-identity). Both tests target the LATER of two structurally equal
# twins through the PUBLIC id-less door and demand the fact's OWN geometry,
# never merely "no crash"; each carries a non-equal lawful twin beside it.

_EQ_FACT = ('<ix:nonFraction name="us-gaap:A" contextRef="c1" unitRef="u1" '
            'scale="0" decimals="0">7</ix:nonFraction>')


def test_SEQ246_equal_ROWS_the_later_fact_keeps_its_OWN_header_and_span():
    prep = prepare(_HEAD + '<table>'
                   '<tr><td>x</td><td>H-ONE</td></tr>'
                   f'<tr><td>lbl</td><td>{_EQ_FACT}</td></tr>'
                   '<tr><td>x</td><td>H-TWO</td></tr>'
                   f'<tr><td>lbl</td><td>{_EQ_FACT}</td></tr>'
                   '</table></body></html>')
    later = prep['noid_elements'][1]
    ev, why = _evidence_for(prep, later)
    assert ev is not None, why
    # ITS OWN header — the stack is COMPLETE near→far (SEQ 247), so H-ONE
    # farther above lawfully appears too; the pin is that H-TWO is NEAREST
    # (first) and that its stored span slices exactly its own characters.
    assert ev['columns'][0] == 'H-TWO', ev['columns']
    a, b = ev['column_spans'][0]
    assert prep['text'][a:b] == 'H-TWO', prep['text'][a:b]
    # ITS OWN row span — the twin rows hold identical text at different spans
    own_row = later.ren.find_parent('tr')
    assert ev['row_span'] == prep['node_spans'][id(own_row)], \
        (ev['row_span'], prep['node_spans'][id(own_row)])
    # the NON-EQUAL lawful twin beside it: distinct rows still attach normally
    prep2 = prepare(_HEAD + '<table>'
                    '<tr><td>x</td><td>H-A</td></tr>'
                    f'<tr><td>alpha</td><td>{_EQ_FACT}</td></tr>'
                    '<tr><td>x</td><td>H-B</td></tr>'
                    f'<tr><td>beta</td><td>{_EQ_FACT}</td></tr>'
                    '</table></body></html>')
    ev2, why2 = _evidence_for(prep2, prep2['noid_elements'][1])
    assert ev2 is not None, why2
    assert 'H-B' in ev2['columns'] and ev2['row_label'] == 'beta'


def test_SEQ246_equal_CELLS_the_later_fact_keeps_its_OWN_label_window():
    """The cell-level face of the same defect: `cells.index(cell)` by
    EQUALITY resolves the later twin cell to the earlier position, so the
    left-of-fact label window ends too early — the label between the twins
    vanishes. The window must end at the fact's OWN cell.

    THE LABEL WINDOW IS THE ONLY FACE THAT BITES THIS SITE. The aligned
    column stack receives the identity `cell` object and matches it with
    `is`, so a column-header pin passes in BOTH states (probed: the later
    twin already reports the fourth header pre-fix). And 'beta' is not a
    "nearest-cell" claim: the contract takes the FIRST ELIGIBLE cell of the
    window, and '1' has no letters, so `_words` rejects it — 'beta' is the
    first eligible of the CORRECTED window [1, fact, beta]."""
    prep = prepare(_HEAD + '<table><tr>'
                   f'<td>1</td><td>{_EQ_FACT}</td><td>beta</td>'
                   f'<td>{_EQ_FACT}</td></tr></table></body></html>')
    later = prep['noid_elements'][1]
    ev, why = _evidence_for(prep, later)
    assert ev is not None, why
    # ITS OWN window: 'beta' sits left of the LATER fact — equality cut the
    # window at the earlier twin (index 1) and returned no label at all
    assert ev['row_label'] == 'beta', repr(ev['row_label'])
    a, b = ev['row_label_span']
    assert prep['text'][a:b] == 'beta'
    # the NON-EQUAL lawful twin: distinct sibling cells keep their labels
    prep2 = prepare(_HEAD + '<table><tr>'
                    f'<td>1</td><td>{_EQ_FACT}</td><td>gamma</td>'
                    '<td><ix:nonFraction name="us-gaap:B" contextRef="c1" '
                    'unitRef="u1" scale="0" decimals="0">8</ix:nonFraction>'
                    '</td></tr></table></body></html>')
    ev2, why2 = _evidence_for(prep2, prep2['noid_elements'][1])
    assert ev2 is not None, why2
    assert ev2['row_label'] == 'gamma', repr(ev2['row_label'])


def _evidence_for(prep, fact):
    from driver.relocation.inline_html import evidence_for_element
    return evidence_for_element(prep, fact)


def test_E3_a_hidden_type_input_is_not_text():
    """No special case exists for it (SEQ 235: §15.3.1 marks it !important —
    not the overridable class — and an input carries no text anyway)."""
    prep, ev = _ev('<table><tr><td><input type="hidden" value="x"/>Label</td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert ev['row_label'] == 'Label'


def test_E3_template_represents_NOTHING_even_with_author_display():
    """HTML LS §4.12.3: template contents are not rendered children, so
    `style="display:block"` cannot leak them — unlike `rp`, whose reveal is
    the legitimate normal-UA-rule override (SEQ 235 MUST-REFUSE/MUST-ALLOW
    pair)."""
    prep, ev = _ev('<table><tr>'
                   '<td><template style="display:block">GHOST'
                   '<div>NESTED GHOST</div></template>Label</td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert 'GHOST' not in prep['text']
    assert ev['row_label'] == 'Label'


def test_E_zero_width_space_is_a_SEPARATOR_not_deleted():
    """U+200B ZERO WIDTH SPACE: the walk treats it as a token separator; the
    old `_text` DELETED it, silently fusing two tokens into one word."""
    zwsp = chr(0x200B)               # ZERO WIDTH SPACE, named — never invisible
    prep, ev = _ev(f'<table><tr><td>Total{zwsp}revenue</td>'
                   f'<td>{_FACT}</td></tr></table>')
    assert ev['row_label'] == 'Total revenue', repr(ev['row_label'])


def test_EU040_a_th_label_cell_is_a_cell_exactly_as_the_table_model_says():
    """_CELL_TAGS transcribes the WHATWG table model: td AND th are cells
    (4.9.9/4.9.10), so a HEADER-cell label is selected exactly like a
    data-cell label — dropping th would silently lose every header-labeled
    row's evidence."""
    prep, ev = _ev(f'<table><tr><th>Total</th><td>{_FACT}</td></tr></table>')
    span = ev['row_label_span']
    assert prep['text'][span[0]:span[1]] == 'Total'
