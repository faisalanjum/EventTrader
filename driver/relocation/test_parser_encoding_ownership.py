"""#827 — WHOEVER MAKES THE BYTES OWNS THEIR ENCODING.

`_semantic_parse` is given already-decoded text and encodes it to UTF-8 itself.
Until this was pinned it did not tell lxml so, which left the choice of decoder
to whatever the document's XML declaration happened to say. A filing may
lawfully declare `encoding="ISO-8859-1"` — that statement describes the bytes
the FILER wrote, which we no longer hold by the time this function runs. Applied
to OUR bytes it is simply wrong, and it re-decodes them:

    é   U+00E9   ->  UTF-8  C3 A9  ->  read as ISO-8859-1  ->  Ã ©

Two different failures come out of that, and both are proved here because
fixing only the loud one would leave the dangerous one in place:

  LOUD   the mojibake is not a lawful XML name, so a WELL-FORMED filing is
         refused — we accuse the filer of an error we made ourselves;
  SILENT the mojibake is STILL a lawful name, so nothing raises and the
         dimension member's identity is quietly different.

The silent case is built on U+00B7 MIDDLE DOT (a lawful XML NameChar) because
its UTF-8 bytes C2 B7 read under ISO-8859-1 as U+00C2 + U+00B7 — both lawful
name characters. That is the whole trick, and it is why "no exception" was
never evidence that the identity survived.

Spec sources:
  XML 1.0 5e §4.3.3 (encoding declaration) and §2.3 (Name / NameChar)
  https://www.w3.org/TR/xml/#charencoding
  Namespaces in XML 1.0 3e §3 — identity is (namespace URI, local name)
  https://www.w3.org/TR/xml-names/#dt-expname
"""
import pytest

from driver.relocation import inline_html
from driver.relocation.inline_html import element_evidence

_NS = ('xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
       'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
       'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
       'xmlns:us-gaap="http://fasb.org/us-gaap/2023" '
       'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
       'xmlns:co="http://example.org/company"')

#: LAWFUL under ISO-8859-1 re-decoding: 'M·mbre' -> 'MÂ·mbre', still a name.
STABLE = 'M·mbre'
#: NOT lawful after re-decoding: 'Mémbre' -> 'MÃ©mbre', and U+00A9 is no
#: NameChar, so the document is refused instead of quietly changed.
BREAKING = 'Mémbre'

DECLARATIONS = {
    'none': '',
    'utf-8': '<?xml version="1.0" encoding="UTF-8"?>',
    'iso-8859-1': '<?xml version="1.0" encoding="ISO-8859-1"?>',
    'windows-1252': '<?xml version="1.0" encoding="windows-1252"?>',
}


def _doc(member, declaration, text='390'):
    """One lawful filing carrying ONE dimension member; only the declaration
    and the non-ASCII name vary."""
    return (DECLARATIONS[declaration] +
            f'<html {_NS}><body><ix:header><ix:resources>'
            f'<xbrli:context id="c1"><xbrli:entity>'
            f'<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
            f'</xbrli:identifier><xbrli:segment>'
            f'<xbrldi:explicitMember dimension="us-gaap:Ax">co:{member}'
            f'</xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
            f'<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
            f'<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            f'</xbrli:context><xbrli:unit id="u1">'
            f'<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
            f'</ix:resources></ix:header>'
            f'<p><ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
            f'unitRef="u1" scale="6" decimals="-6">{text}</ix:nonFraction></p>'
            f'</body></html>')


def _member(evidence):
    """The (namespace URI, local name) of the one member, from the expanded
    view that owns identity."""
    return evidence['dims_expanded'][0][1]


# ---------------------------------------------------------------------------
# THE SILENT FAILURE — no exception, different identity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('declaration', sorted(DECLARATIONS))
def test_the_MEMBER_IDENTITY_is_the_SAME_under_every_declaration(declaration):
    """THE DEFECT, stated as the law it broke: the declaration describes the
    filer's bytes, not ours, so it must not change what the filing MEANS.
    Under ISO-8859-1 this member silently became 'MÂ·mbre' and every downstream
    comparison — binder, census, packet — asked about a member no filing wrote.
    """
    evidence, why = element_evidence(_doc(STABLE, declaration), 'f1')
    assert why == 'ok', f'{declaration}: {why}'
    assert _member(evidence) == ('http://example.org/company', STABLE)


# ---------------------------------------------------------------------------
# THE LOUD FAILURE — a well-formed filing wrongly accused
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('declaration', sorted(DECLARATIONS))
def test_a_WELL_FORMED_filing_is_never_refused_for_its_declaration(declaration):
    """'Mémbre' re-decodes to a string containing U+00A9, which is no NameChar,
    so the member QName failed to resolve and the context was reported
    `malformed_context_structure`. The filing is lawful; the error was ours."""
    evidence, why = element_evidence(_doc(BREAKING, declaration), 'f1')
    assert why == 'ok', f'{declaration}: {why}'
    assert _member(evidence) == ('http://example.org/company', BREAKING)



# ---------------------------------------------------------------------------
# MUST-ALLOW — the fix must not have bought correctness by refusing more
# ---------------------------------------------------------------------------

def test_IMPORTING_the_module_changes_no_PROCESS_GLOBAL_warning_filter():
    """A module-level `warnings.filterwarnings` is process-wide. This module's
    `XMLParsedAsHTMLWarning` suppression sat at import time, so merely importing
    the parser silently changed how EVERY other library in the process reports
    that warning — including code with no connection to filings.

    Measured in a CLEAN interpreter so this file's own imports cannot mask it:
    the filter count before and after the import must be identical."""
    import os
    import subprocess
    import sys
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    probe = (
        "import warnings, sys\n"
        "before = len(warnings.filters)\n"
        "sys.path.insert(0, '.')\n"
        "import driver.relocation.inline_html\n"
        "print(before, len(warnings.filters))\n")
    out = subprocess.run([sys.executable, "-c", probe], capture_output=True,
                         text=True, cwd=root)
    assert out.returncode == 0, out.stderr[-400:]
    before, after = out.stdout.split()
    assert before == after, (
        f"importing the module moved warnings.filters {before} -> {after}")


def test_the_renderer_parse_stays_warning_CLEAN_without_that_global():
    """MUST-ALLOW twin. Removing the global must not start leaking the warning
    the suppression exists for: an XML-declared filing parsed as HTML is this
    parser's deliberate choice, not something to warn a caller about."""
    import warnings
    from driver.relocation.inline_html import _soup
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        _soup('<?xml version="1.0"?><html><body><p>x</p></body></html>')
    assert not seen, [str(w.message) for w in seen]


def test_a_plain_ASCII_filing_is_UNAFFECTED():
    """The overwhelmingly common shape. A rule that fixed the non-ASCII cases
    by changing anything here would be a worse defect than the one it closed."""
    evidence, why = element_evidence(_doc('Member', 'iso-8859-1'), 'f1')
    assert why == 'ok'
    assert _member(evidence) == ('http://example.org/company', 'Member')


def test_a_genuinely_MALFORMED_document_is_still_refused():
    """Declaring the encoding must not turn `recover=False` into a repair. An
    unclosed element is still not a well-formed XML report."""
    broken = _doc(STABLE, 'utf-8').replace('</body></html>', '<p>')
    _evidence, why = element_evidence(broken, 'f1')
    # The shared owner, not a copy of the sentence: reword the refusal and this
    # moves with it instead of passing on a string nothing produces any more.
    assert why == inline_html.NOT_WELL_FORMED


# ---------------------------------------------------------------------------
# THE ISOLATED MUTATION — remove ONLY the ownership, name what must flip
# ---------------------------------------------------------------------------

def test_REMOVING_the_encoding_ownership_flips_the_SILENT_detector(tmp_path):
    """One character-for-character deletion of `encoding='utf-8'` in a scratch
    copy, and a NAMED expectation on both sides:

        the silent expanded-member check   green -> RED
        the lawful ASCII control           green -> green

    Not "some test fails". A mutation that reddened everything would be
    consistent with a fix that simply refuses more, which is the failure this
    whole file is guarding against.
    """
    import importlib.util
    import sys as _sys

    src = open(inline_html.__file__, encoding='utf-8').read()
    # The ownership moved into `_PARSER_OPTIONS`, the ONE policy the bounded
    # prolog pass and the semantic tree now share; the rule is unchanged and
    # the anchor is stronger, because a single dict cannot drift between the
    # two call sites the way two copied argument lists could.
    old = "no_network=True, encoding='utf-8')"
    new = 'no_network=True)'
    assert src.count(old) == 1, 'the ownership is stated exactly once'
    path = tmp_path / 'inline_html_mutant.py'
    path.write_text(src.replace(old, new), encoding='utf-8')

    spec = importlib.util.spec_from_file_location('ih_mutant', str(path))
    mutant = importlib.util.module_from_spec(spec)
    saved = list(_sys.path)
    try:
        spec.loader.exec_module(mutant)
    finally:
        _sys.path[:] = saved

    # RED: the member's identity silently changes, and NOTHING raises.
    evidence, why = mutant.element_evidence(_doc(STABLE, 'iso-8859-1'), 'f1')
    assert why == 'ok', 'the point is that it does not refuse — it lies'
    assert evidence['dims_expanded'][0][1] == \
        ('http://example.org/company', 'MÂ·mbre')

    # GREEN: the lawful ASCII filing is untouched, so the mutation is isolated.
    ascii_ev, ascii_why = mutant.element_evidence(
        _doc('Member', 'iso-8859-1'), 'f1')
    assert ascii_why == 'ok'
    assert ascii_ev['dims_expanded'][0][1] == \
        ('http://example.org/company', 'Member')


def test_EU039_the_parser_policy_never_expands_hidden_content():
    """EU-039 (#827): the security half of _PARSER_OPTIONS, pinned by
    BEHAVIOR — an internal-DTD entity stays UNRESOLVED under the product
    policy (no network, no DTD, no entity resolution at parse time; the
    #826 zero-network clean-lane law at the parse boundary). Under the
    mutant (resolve_entities/load_dtd flipped) the entity expands to its
    replacement text and this node fails."""
    from lxml import etree
    from inline_html import _PARSER_OPTIONS
    doc = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "boom">]><r>&x;</r>'
    opts = {k: v for k, v in _PARSER_OPTIONS.items() if k != "encoding"}
    root = etree.fromstring(doc, etree.XMLParser(**opts))
    assert root.text is None                      # nothing expanded in place
    assert b"boom" not in etree.tostring(root)    # the replacement text never appears


def test_EU131_a_foreign_renderer_parse_warning_refuses_typed():
    """EU-131 (FAIL-CLOSED): the renderer parse suppresses exactly ONE
    deliberate warning (XMLParsedAsHTMLWarning — parsing XML-declared
    filings as HTML is the function's stated choice). Every OTHER parser
    warning is a signal about the bytes and must refuse TYPED
    (SemanticParseError), never pass silently. Measured recall: 1,903
    frozen-corpus documents, zero refusals (g2_evid_recall_EU-131.txt).
    The locator-shaped input below provokes bs4's
    MarkupResemblesLocatorWarning — a real signal that the caller handed a
    URL, not markup."""
    import pytest as _pt
    from inline_html import SemanticParseError, _soup
    with _pt.raises(SemanticParseError, match="renderer parse warning"):
        _soup("http://example.com/not-markup.htm")
    assert _soup("<p>real markup</p>") is not None   # the lawful twin


def test_EU132_the_renderer_view_is_built_by_the_pinned_lxml_builder():
    """EU-132 (DERIVE-CITATION pin): the renderer view's parser choice is the
    bs4 'lxml' tree builder — Beautiful Soup 4.13.3 (installed pin),
    "Installing a parser" table, lxml's HTML parser, backed by libxml2 via
    lxml 6.0.2 (drift row 5.3.1->6.0.2 recorded). Pinned by the builder's
    own published identity plus one browser-grade repair behavior."""
    from inline_html import _soup
    soup = _soup("<p>x</p>")
    assert soup.builder.NAME == "lxml"
    assert _soup("<table><tr><td>a").find("td").get_text() == "a"


def test_EU126_the_identity_anchor_encodes_lone_surrogates_by_the_clause():
    """EU-126 (#827): the boundary clause's identity-anchor hash-encoding law
    — UTF-8 with 'surrogatepass', encoded ONCE — pinned on a LONE SURROGATE:
    the identity must neither crash nor silently collapse onto the
    'replace' spelling (a replaced surrogate would hash a DIFFERENT
    document as the same identity)."""
    import hashlib
    from driver.relocation.inline_html import sha256_text
    text = "before \ud83d after"                      # a lone high surrogate
    want = hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()
    got = sha256_text(text)
    assert got == want
    replaced = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()
    assert got != replaced, "a replaced surrogate must not share the identity"
