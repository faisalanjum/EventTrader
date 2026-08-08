"""#827 round 9 — the two views, and the bridge between them.

ONE set of bytes is read twice, on purpose:

  * a STRICT XML parse owns IDENTITY — expanded names and the namespaces in
    scope where each is written;
  * the ORIGINAL renderer parse owns APPEARANCE — visible text, rows, spans.

Neither may answer the other's question. These are the public controls for that
separation: every one of them goes through a public door (`prepare`,
`element_evidence`, `identity_fallback`, `bind_graph_fact`), never a private
helper, so they keep binding on any future rewrite of the internals.

EVERY REFUSAL HERE HAS A MUST-ALLOW TWIN. A rule that only ever refuses is a
rule that can be satisfied by refusing everything.
"""
import warnings

import pytest
from bs4 import XMLParsedAsHTMLWarning

# THE ONE EXPECTED WARNING, and only it. A blanket `ignore` would hide a real
# parser warning — including one raised by the very code under test.
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)

from driver.relocation.inline_html import (  # noqa: E402
    NOT_WELL_FORMED, VIEWS_DISAGREE, bind_graph_fact, element_evidence,
    identity_fallback, prepare, refused)

IX = 'http://www.xbrl.org/2013/inlineXBRL'
XBRLI = 'http://www.xbrl.org/2003/instance'
XBRLDI = 'http://xbrl.org/2006/xbrldi'
SRT = 'http://fasb.org/srt/2024'
GAAP = 'http://fasb.org/us-gaap/2024'
ISO = 'http://www.xbrl.org/2003/iso4217'
IXT = 'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12'
WRONG = 'http://example.invalid/not-inline-xbrl'


def doc(body, ix_prefix='ix', hidden_prefix=None, extra_ns='',
        ctx_id='c1', unit_id='u1', measure='iso4217:USD',
        cik='0000320193', scheme='http://www.sec.gov/CIK', member=None,
        hide_header=True):
    """A minimal but LAWFUL inline report.

    RESOURCES LIVE WHERE THE SPEC PUTS THEM. Inline XBRL 1.1 §14.1 fixes
    `ix:resources` content to the named resource children — `xbrli:context` and
    `xbrli:unit` among them — and §14.1.1 requires `ix:resources` to be a child
    of `ix:header`. This builder used to drop them inside `ix:hidden`, which is
    a container for FACT markup, not for resources; a fixture in the wrong shape
    certifies a parser that reads the wrong shape.

    The header is wrapped in a `display:none` div because that is what real
    filings do — the resources carry dates, a CIK and unit names that are not
    part of the page a reader sees.

    Every value the module reads as a SCHEMA-TYPED value is a parameter, so one
    table below can pad or break each of them in turn. The Inline XBRL prefix is
    a parameter for the same reason no prefix may be privileged: `ix` is a
    convention, not a name.
    """
    hp = hidden_prefix or ix_prefix
    # §9.1.1 puts `ix:hidden` inside `ix:header`, beside `ix:resources`.
    # `hide_header` exists so ONE test can prove `ix:hidden` does the hiding on
    # its own: real filings wrap the header in `display:none`, which would hide
    # the content by CSS whatever the parser did.
    open_div = '<div style="display:none">' if hide_header else ''
    close_div = '</div>' if hide_header else ''
    scen = (f'<xbrli:scenario><xbrldi:explicitMember dimension="{member[0]}">'
            f'{member[1]}</xbrldi:explicitMember></xbrli:scenario>'
            if member else '')
    return f'''<html xmlns="http://www.w3.org/1999/xhtml"
 xmlns:{ix_prefix}="{IX}" xmlns:xbrli="{XBRLI}" xmlns:xbrldi="{XBRLDI}"
 xmlns:iso4217="{ISO}" xmlns:us-gaap="{GAAP}" xmlns:srt="{SRT}"
 xmlns:ixt="{IXT}"{extra_ns}>
<body>
{open_div}<{ix_prefix}:header>
<{hp}:hidden><p>SECRET</p></{hp}:hidden>
<{ix_prefix}:resources>
<xbrli:context id="{ctx_id}"><xbrli:entity>
<xbrli:identifier scheme="{scheme}">{cik}</xbrli:identifier>
</xbrli:entity><xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate>
<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>{scen}</xbrli:context>
<xbrli:unit id="{unit_id}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>
</{ix_prefix}:resources></{ix_prefix}:header>{close_div}
{body}
</body></html>'''


def fact(prefix='ix', fid='f-1', name='us-gaap:Revenues', text='390', **attrs):
    """One inline fact. Every attribute is overridable and written EXACTLY once
    — a repeated attribute is not well-formed XML, and a fixture that produced
    one would be testing the parser's error path by accident."""
    # DECIMALS IS PART OF BEING LAWFUL. Inline XBRL 1.1 §10.1.1 requires
    # exactly one of `decimals` or `precision` on a non-nil numeric fact, and
    # this builder claimed to make lawful facts while omitting both. Overridable
    # exactly once, like every other attribute here.
    attrs = dict({'contextRef': 'c1', 'unitRef': 'u1', 'scale': '6',
                  'decimals': '0'}, **attrs)
    # `decimals=None` REMOVES it, which the precision cases need: a fact
    # carrying both is refused for a different reason than the one under test.
    attrs = {k: v for k, v in attrs.items() if v is not None}
    if fid:
        attrs['id'] = fid
    spelled = ''.join(f' {k}="{v}"' for k, v in attrs.items())
    return (f'<{prefix}:nonFraction name="{name}"{spelled}>{text}'
            f'</{prefix}:nonFraction>')


def row(cells):
    return '<table><tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr></table>'


# ---------------------------------------------------------------------------
# 1. NO PREFIX IS PRIVILEGED — the strict view names elements, not the spelling
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('prefix', ['ix', 'i', 'inline', 'IX', 'z9'])
def test_ANY_lawful_prefix_for_the_fact_element_still_binds(prefix):
    """MUST-ALLOW. A filing chooses its own prefixes; `ix` is one choice among
    infinitely many, and every one of them names the same element."""
    prep = prepare(doc(row(['Revenue', fact(prefix)]), ix_prefix=prefix))
    assert refused(prep) is None, refused(prep)
    ev, why = element_evidence(prep, 'f-1')
    assert why == 'ok', why
    assert ev['name_expanded'] == (GAAP, 'Revenues')
    assert ev['row_text'] == 'Revenue 390'      # the renderer half still works


@pytest.mark.parametrize('prefix', ['ix', 'i', 'hid'])
def test_ANY_lawful_prefix_for_hidden_still_hides(prefix):
    """MUST-ALLOW twin of the rule below: whatever it is spelled, a real
    ix:hidden container keeps its content out of the representation."""
    prep = prepare(doc(row(['Revenue', fact()]), hidden_prefix=prefix,
                       hide_header=False,
                       extra_ns=f' xmlns:{prefix}="{IX}"' if prefix != 'ix' else ''))
    assert refused(prep) is None, refused(prep)
    # THE HEADER IS NOT CSS-HIDDEN HERE, on purpose: otherwise `display:none`
    # would hide SECRET whatever the parser did, and this test would pass
    # without the rule it names ever running.
    assert 'SECRET' not in prep['text'], 'ix:hidden must hide on its own'
    assert 'Revenue 390' in prep['text']


# ---------------------------------------------------------------------------
# 1b. THE FOUR NAMESPACE ATTACKS — near-misses that must NOT be trusted
#
# Each is a way of ALMOST declaring something. A reader that matches on how a
# name LOOKS accepts all four; a reader that resolves names cannot. Every attack
# has a lawful twin differing in exactly one respect, so none of these rules can
# be satisfied by refusing everything.
# ---------------------------------------------------------------------------

OTHER = 'http://example.invalid/other'


def test_ATTACK_a_declaration_on_an_unrelated_SIBLING_is_not_in_scope():
    """A prefix declared on a SIBLING is not in scope for this element.

    Scope is ancestry, not proximity (Namespaces in XML §2.2). A walk that
    collected every `xmlns:` it could see anywhere in the document would accept
    this, and that is precisely the hand-written walk this round deleted."""
    body = (f'<div xmlns:zz="{OTHER}"><p>elsewhere</p></div>'
            + row(['R', fact(name='zz:Revenues')]))
    assert element_evidence(prepare(doc(body)), 'f-1') \
        == (None, 'malformed_concept_name')


def test_the_SAME_declaration_on_an_ANCESTOR_is_in_scope():
    """LAWFUL TWIN: identical declaration, moved to an ancestor, resolves."""
    body = f'<div xmlns:zz="{OTHER}">' + row(['R', fact(name='zz:Revenues')]) \
        + '</div>'
    ev, why = element_evidence(prepare(doc(body)), 'f-1')
    assert why == 'ok', why
    assert ev['name_expanded'] == (OTHER, 'Revenues')


def test_ATTACK_a_prefix_declared_only_in_ANOTHER_CASE_is_undeclared():
    """Prefixes are case-SENSITIVE. `xmlns:ZZ` does not declare `zz`."""
    body = row(['R', fact(name='zz:Revenues')])
    prep = prepare(doc(body, extra_ns=f' xmlns:ZZ="{OTHER}"'))
    assert element_evidence(prep, 'f-1') == (None, 'malformed_concept_name')


def test_the_SAME_declaration_used_in_ITS_OWN_case_resolves():
    """LAWFUL TWIN: one character of case is the whole difference."""
    body = row(['R', fact(name='ZZ:Revenues')])
    prep = prepare(doc(body, extra_ns=f' xmlns:ZZ="{OTHER}"'))
    ev, why = element_evidence(prep, 'f-1')
    assert why == 'ok' and ev['name_expanded'] == (OTHER, 'Revenues')


@pytest.mark.parametrize('near_miss,how', [
    (IX + '/', 'a trailing slash'),
    (IX.replace('inlineXBRL', 'INLINEXBRL'), 'changed case'),
    (IX.replace('http://', 'https://'), 'a different scheme'),
])
def test_ATTACK_a_NEAR_MISS_namespace_URI_is_a_different_namespace(near_miss,
                                                                  how):
    """A namespace URI is compared as a STRING, character for character.

    `…/inlineXBRL/` and `…/INLINEXBRL` are not "close enough" — they name other
    namespaces entirely, so an element under one of them is not an inline fact
    however familiar its spelling looks."""
    assert near_miss != IX, how
    prep = prepare(doc(row(['R', fact()]), ix_prefix='ix',
                       extra_ns='').replace(f'xmlns:ix="{IX}"',
                                            f'xmlns:ix="{near_miss}"'))
    assert refused(prep) is None, refused(prep)
    assert prep['elements'] == {}, f'{how} was treated as the real namespace'
    assert element_evidence(prep, 'f-1') == (None, 'unsupported_element_kind')


def test_the_EXACT_official_URI_is_a_fact():
    """LAWFUL TWIN of all three near-misses: the exact URI, and only it."""
    ev, why = element_evidence(prepare(doc(row(['R', fact()]))), 'f-1')
    assert why == 'ok' and ev['name_expanded'] == (GAAP, 'Revenues')


@pytest.mark.parametrize('where,markup', [
    ('script', "<script>var s = 'xmlns:zz=%s';</script>" % OTHER),
    ('comment', '<!-- xmlns:zz="%s" -->' % OTHER),
])
def test_ATTACK_xmlns_looking_TEXT_declares_nothing(where, markup):
    """Text that LOOKS like a declaration is text.

    A declaration is an attribute on an element, resolved by the parser. A
    string inside a script, or inside a comment, is neither — and a reader that
    searched the document for `xmlns:` would be fooled by both."""
    body = markup + row(['R', fact(name='zz:Revenues')])
    assert element_evidence(prepare(doc(body)), 'f-1') \
        == (None, 'malformed_concept_name'), where


def test_a_REAL_declaration_attribute_does_declare():
    """LAWFUL TWIN: the same characters, written where a declaration goes."""
    prep = prepare(doc(row(['R', fact(name='zz:Revenues')]),
                       extra_ns=f' xmlns:zz="{OTHER}"'))
    ev, why = element_evidence(prep, 'f-1')
    assert why == 'ok' and ev['name_expanded'] == (OTHER, 'Revenues')


def _moved_resources(html, where):
    """Take the context and unit OUT of ix:resources and put them `where`."""
    start = html.index('<xbrli:context')
    end = html.index('</xbrli:unit>') + len('</xbrli:unit>')
    resources, rest = html[start:end], html[:start] + html[end:]
    return rest.replace(where, where + resources, 1)


@pytest.mark.parametrize('where,label', [
    ('<ix:hidden>', 'inside ix:hidden, which is for FACT markup'),
    ('<body>', 'loose in the body, in no container at all'),
])
def test_ATTACK_a_context_or_unit_OUTSIDE_ix_resources_cannot_be_referenced(
        where, label):
    """Resources are read from ONE place, because the spec puts them in one place.

    Inline XBRL 1.1 (Recommendation 2013-11-18) §14.1 fixes `ix:resources`
    content to the named resource children — `xbrli:context` and `xbrli:unit`
    among them — and §14.1.1 requires `ix:resources` to be a child of
    `ix:header`. A declaration anywhere else is not a declaration this report
    makes, so a fact referring to it refers to nothing.

    Reading them from anywhere in the document meant a context buried in a
    `<div>`, or inside `ix:hidden` — a container for FACT markup, not for
    resources — was indexed and bound exactly like a real one."""
    html = _moved_resources(doc(row(['R', fact()])), where)
    prep = prepare(html)
    assert refused(prep) is None, refused(prep)
    assert element_evidence(prep, 'f-1') == (None, 'undefined_context'), label
    assert bind_graph_fact(html, **_bind_kw())[1] \
        == 'exact_id_undefined_context', label


def test_the_SAME_context_and_unit_INSIDE_ix_resources_bind():
    """LAWFUL TWIN: byte-identical resources, in the place the spec names."""
    html = doc(row(['R', fact()]))
    assert element_evidence(prepare(html), 'f-1')[1] == 'ok'
    bound, why = bind_graph_fact(html, **_bind_kw())
    assert why == 'ok' and bound is not None, why


def test_ix_resources_must_itself_be_a_child_of_ix_header():
    """§14.1.1. `ix:resources` floating outside `ix:header` is not the report's
    resources container either — the ancestry is the rule, not the tag name."""
    html = doc(row(['R', fact()])).replace('<ix:header>', '').replace(
        '</ix:header>', '')
    prep = prepare(html)
    assert refused(prep) is None, refused(prep)
    assert element_evidence(prep, 'f-1') == (None, 'undefined_context')


def _bind_kw(**over):
    kw = dict(inline_element_id='f-1', concept='us-gaap:Revenues',
              context_id='c1', unit_ref='u1', unit_name='iso4217:USD',
              is_divide='0', period_type='duration', start_date='2026-01-01',
              end_date='2026-04-01', dims=(), entity_cik='0000320193',
              concept_namespace=GAAP, graph_concept_qname='us-gaap:Revenues',
              raw_value='390,000,000')
    kw.update(over)
    return kw


@pytest.mark.parametrize('measure_markup,label', [
    (f'<xbrli:measure xmlns="{XBRLI}">shares</xbrli:measure>',
     'the instance namespace as a local DEFAULT, value unprefixed'),
    ('<xbrli:measure>xbrli:shares</xbrli:measure>',
     'the conventional prefix'),
    (f'<xbrli:measure xmlns:inst="{XBRLI}">inst:shares</xbrli:measure>',
     'a lawful alternate prefix'),
])
def test_an_INSTANCE_measure_reaches_the_graph_as_its_LOCAL_NAME(measure_markup,
                                                                 label):
    """The graph stores an instance-namespace measure WITHOUT its prefix, and
    what it stores is the LOCAL NAME — which is not the same thing as "the text
    after a colon".

    An unprefixed value resolved through an in-scope DEFAULT namespace has no
    colon to slice, so slicing produced the empty string and the fact refused as
    `unit_name_not_the_filings_measure`. All three spellings below are the same
    measure and must reach the graph identically as `shares`."""
    body = row(['R', fact(unitRef='u1')])
    html = doc(body).replace(
        f'<xbrli:measure>{"iso4217:USD"}</xbrli:measure>', measure_markup)
    prep = prepare(html)
    assert refused(prep) is None, refused(prep)
    assert prep['units']['u1']['graph_measures'] == ('shares',), label
    assert prep['units']['u1']['expanded_measures'] == ((XBRLI, 'shares'),)
    bound, why = bind_graph_fact(html, **_bind_kw(unit_name='shares'))
    assert why == 'ok' and bound is not None, f'{label}: {why}'


def test_a_NON_instance_measure_keeps_its_prefix_exactly_as_written():
    """MUST-ALLOW twin of the rule above, in the other direction: the prefix is
    dropped ONLY for the instance namespace. A currency measure reaches the
    graph exactly as the filing wrote it, colon and all."""
    prep = prepare(doc(row(['R', fact()])))
    assert prep['units']['u1']['graph_measures'] == ('iso4217:USD',)
    assert bind_graph_fact(doc(row(['R', fact()])),
                           **_bind_kw(unit_name='iso4217:USD'))[1] == 'ok'


# ---------------------------------------------------------------------------
# 2. MIXED DOCUMENTS — a real element beside a lexical impostor
# ---------------------------------------------------------------------------

def test_a_wrong_URI_twin_of_a_fact_never_becomes_a_fact_and_the_real_one_binds():
    """THE MIXED CONTROL. One lawful fact and one element spelled EXACTLY the
    same way under a prefix rebound to another namespace.

    Both must hold at once: the impostor is not a fact, and the real fact still
    binds. A rule that refused the document would satisfy the first half by
    destroying the second."""
    body = (row(['Revenue', fact()])
            + f'<div xmlns:ix="{WRONG}">{fact(fid="f-impostor", name="us-gaap:Revenues")}</div>')
    prep = prepare(doc(body))
    assert refused(prep) is None, refused(prep)
    # the impostor is not a fact...
    assert 'f-impostor' not in prep['elements']
    assert element_evidence(prep, 'f-impostor')[1] == 'unsupported_element_kind'
    # ...and the real one is unharmed
    ev, why = element_evidence(prep, 'f-1')
    assert why == 'ok' and ev['row_text'] == 'Revenue 390'


def test_a_wrong_URI_twin_of_hidden_does_not_hide_and_the_real_one_still_does():
    """Same shape for the container. `ix:hidden` under a rebound prefix is an
    ordinary element: its text is VISIBLE, while the real container's is not."""
    body = (row(['Revenue', fact()])
            + f'<div xmlns:ix="{WRONG}"><ix:hidden><p>VISIBLE</p></ix:hidden></div>')
    prep = prepare(doc(body))
    assert refused(prep) is None, refused(prep)
    assert 'SECRET' not in prep['text'], "the real container must still hide"
    assert 'VISIBLE' in prep['text'], "a lexical twin has no power to hide"


# ---------------------------------------------------------------------------
# 3. THE TWO VIEWS MUST AGREE — and the reason is truthful when they do not
# ---------------------------------------------------------------------------

def test_a_document_that_is_not_well_formed_XML_is_refused_through_every_door():
    """A conforming Inline XBRL report is a well-formed XML document. This one
    is not, and every public door says the same thing — no parser exception
    reaches a caller."""
    prep = prepare('<html><body><p>never closed')
    assert refused(prep) == NOT_WELL_FORMED
    assert element_evidence(prep, 'f-1') == (None, NOT_WELL_FORMED)
    assert identity_fallback(prep, (GAAP, 'Revenues'), 'c1', 'u1') \
        == (None, NOT_WELL_FORMED)


def test_the_refusal_reason_is_OURS_and_identical_for_every_bad_document():
    """The public reason may never be derived from parser wording: two different
    syntax errors are one refusal, so nothing downstream can read a library's
    phrasing as a finding about the filing."""
    a = prepare('<html><body><p>never closed')
    b = prepare('<html><body attr=unquoted&amp;><p/></body></html>')
    assert refused(a) == refused(b) == NOT_WELL_FORMED


def test_a_lawful_document_is_NOT_refused():
    """MUST-ALLOW twin: the refusal path must be reachable ONLY by bad bytes."""
    prep = prepare(doc(row(['Revenue', fact()])))
    assert refused(prep) is None
    assert prep['text'] == 'Revenue 390'


# ---------------------------------------------------------------------------
# 4. PAIRING IS VERIFIED — every consumed attribute, not a chosen few
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('attr,key,written,read', [
    ('scale', 'scale', '3', 3),
    ('sign', 'sign', '-', '-'),
    ('format', 'fmt', 'iso4217:num-dot-decimal', 'iso4217:num-dot-decimal'),
])
def test_every_consumed_attribute_is_read_from_the_STRICT_view(attr, key,
                                                               written, read):
    """MUST-ALLOW. The renderer lower-cases every attribute name and would turn
    `contextRef` into `contextref`; the strict view keeps them exactly as
    written, and the evidence proves it by carrying each one through."""
    prep = prepare(doc(row(['Revenue', fact(**{attr: written})])))
    ev, why = element_evidence(prep, 'f-1')
    assert why == 'ok', why
    assert ev[key] == read
    assert ev['context_ref'] == 'c1' and ev['unit_ref'] == 'u1'


# ---------------------------------------------------------------------------
# 5. INDISTINGUISHABLE FACTS KEEP THEIR OWN, TRUTHFUL REASONS
# ---------------------------------------------------------------------------

def test_two_facts_sharing_an_id_still_report_duplicate_id():
    """NOT a document refusal. A repeated id is a per-fact condition with its
    own name, and replacing it with a blanket refusal would lose information."""
    prep = prepare(doc(row(['Revenue', fact() + fact()])))
    assert refused(prep) is None, refused(prep)
    assert element_evidence(prep, 'f-1') == (None, 'duplicate_id')


def test_two_idless_facts_with_ONE_identity_are_ambiguous_not_refused():
    """Likewise: the fallback's own ambiguity law owns this case."""
    prep = prepare(doc(row(['Revenue', fact(fid='') + fact(fid='')])))
    assert refused(prep) is None, refused(prep)
    assert identity_fallback(prep, (GAAP, 'Revenues'), 'c1', 'u1') \
        == (None, 'ambiguous_identity')


def test_ONE_idless_fact_still_binds_through_the_fallback():
    """MUST-ALLOW twin of the ambiguity rule."""
    prep = prepare(doc(row(['Revenue', fact(fid='')])))
    hit, why = identity_fallback(prep, (GAAP, 'Revenues'), 'c1', 'u1')
    assert why == 'ok' and hit is not None


def test_two_idless_facts_differing_in_a_consumed_field_do_not_cross_pair():
    """They share (name, contextRef, unitRef) but not everything, so the
    fallback still cannot choose between them — and says so, rather than
    silently taking the first. The DISTINCT scales prove the two were never
    merged into one."""
    prep = prepare(doc(row(['Revenue',
                            fact(fid='', scale='6') + fact(fid='', scale='3')])))
    assert refused(prep) is None, refused(prep)
    assert identity_fallback(prep, (GAAP, 'Revenues'), 'c1', 'u1') \
        == (None, 'ambiguous_identity')
    scales = sorted(f.sem.get('scale') for f in prep['noid_elements'])
    assert scales == ['3', '6'], "both facts survive as themselves"


# ---------------------------------------------------------------------------
# 6. XML NAMES COME FROM THE XML LIBRARY — including lawful Unicode
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('eid', ['f-1', '_x', 'a.b-c', 'Ünïcode', 'Wért'])
def test_a_LAWFUL_xml_id_is_accepted_including_Unicode(eid):
    """MUST-ALLOW. XML Names permits Unicode; the ASCII regex this replaces
    refused these lawful ids outright."""
    prep = prepare(doc(row(['Revenue', fact(fid=eid)])))
    assert element_evidence(prep, eid)[1] == 'ok'


@pytest.mark.parametrize('eid', ['1abc', 'a b', 'a:b', '-a', '.a'])
def test_an_UNLAWFUL_xml_id_is_still_refused(eid):
    """MUST-REFUSE twin, on ids that a well-formed document can actually carry:
    an XML ID is an NCName, so a colon, a space or a digit-first name is not
    one. The grammar is the library's — there is no second copy of it here."""
    prep = prepare(doc(row(['Revenue', fact(fid=eid)])))
    assert refused(prep) is None, "these documents ARE well formed"
    assert element_evidence(prep, eid) == (None, 'malformed_id')


# ---------------------------------------------------------------------------
# 7. QNAME RESOLUTION — the three standards states, kept apart
# ---------------------------------------------------------------------------

def test_an_undeclared_PREFIX_on_a_concept_names_nothing():
    """MUST-REFUSE. `zz:Revenues` binds no namespace, so it identifies no
    concept at all.

    THE DOCUMENT STAYS WELL FORMED, and that distinction is the point: namespace
    well-formedness constrains element and attribute NAMES, never attribute
    VALUES. The parser therefore cannot catch this one. It is caught where the
    value is read as a QName, and only that fact is refused — the rest of the
    filing remains perfectly readable."""
    prep = prepare(doc(row(['Revenue', fact(name='zz:Revenues', fid='f-z')])))
    assert refused(prep) is None, "the bytes ARE well-formed XML"
    assert element_evidence(prep, 'f-z') == (None, 'malformed_concept_name')


def test_an_undeclared_prefix_on_an_ELEMENT_name_refuses_the_document():
    """The other half of that distinction, written beside it so the two can
    never be confused: an undeclared prefix on a NAME *is* a namespace
    well-formedness error, and there the whole document is genuinely
    unreadable."""
    prep = prepare('<html xmlns="http://www.w3.org/1999/xhtml"><body>'
                   '<zz:context id="c1"/></body></html>')
    assert refused(prep) == NOT_WELL_FORMED


def test_a_QNAME_VALUE_resolves_in_ITS_OWN_scope_not_an_outer_one():
    """A prefix is scoped, and a document may rebind it at any depth.

    Two facts write the SAME text `us-gaap:Revenues`, but the second sits under
    a `<div>` that rebinds `us-gaap` to another namespace. They are therefore
    DIFFERENT concepts, and the only thing that can tell them apart is where
    each is written — the outer binding must not be used for the inner fact.

    This is the control the mutation `global_scope_qname` exists to defeat, and
    it was missing: nothing else here resolves a QName VALUE under a rebinding,
    so a resolver that ignored scope entirely could have stayed green."""
    other = 'http://example.invalid/other-taxonomy'
    body = (row(['Outer', fact(fid='f-out')])
            + f'<div xmlns:us-gaap="{other}">'
            + row(['Inner', fact(fid='f-in')]) + '</div>')
    prep = prepare(doc(body))
    assert refused(prep) is None, refused(prep)
    outer = element_evidence(prep, 'f-out')[0]
    inner = element_evidence(prep, 'f-in')[0]
    assert outer['name_expanded'] == (GAAP, 'Revenues')
    assert inner['name_expanded'] == (other, 'Revenues'), \
        "the inner fact must take the binding in force where IT is written"
    assert outer['name'] == inner['name'], \
        "...and the raw text is identical, so only scope can separate them"


def test_an_unprefixed_concept_takes_the_in_scope_DEFAULT_namespace():
    """MUST-ALLOW. XML Schema QName resolution: with a default namespace in
    scope, an unprefixed value resolves to it. Here that is XHTML — a lawful
    QName that simply is not the concept any graph target names."""
    prep = prepare(doc(row(['Revenue', fact(name='Revenues')])))
    assert refused(prep) is None, refused(prep)
    ev, why = element_evidence(prep, 'f-1')
    assert why == 'ok', why
    assert ev['name_expanded'] == ('http://www.w3.org/1999/xhtml', 'Revenues')
    assert ev['name_expanded'] != (GAAP, 'Revenues'), "and it matches nothing"


def test_the_reserved_xml_prefix_resolves_without_being_declared():
    """Namespaces in XML §3 binds `xml` by definition; it need not — and must
    not — be declared, so lxml reports it in no nsmap. Calling such a QName
    undeclared would be OUR error, not the filing's."""
    from lxml import etree

    from driver.relocation.inline_html import _qname
    el = etree.fromstring(b'<r/>')
    assert _qname('xml:lang', el) == ('http://www.w3.org/XML/1998/namespace',
                                      'lang')
    assert _qname('notaprefix:lang', el) is None, "no other prefix is implied"
    assert _qname(':lang', el) is None, "an empty prefix is not a PrefixedName"


def test_an_unprefixed_value_with_NO_default_namespace_is_absent_not_broken():
    """XML Schema QName resolution again: with no default in scope the
    namespace is ABSENT, which is a lawful value — distinct from this
    resolver's own failure, a bare None."""
    from lxml import etree

    from driver.relocation.inline_html import _qname
    el = etree.fromstring(b'<r/>')
    assert _qname('Widgets', el) == (None, 'Widgets')
    assert _qname('1nope', el) is None, "an unlawful name still fails"


# ---------------------------------------------------------------------------
# 8. A ROW OF NUMBERS IS NOT A HEADING — whatever prefix those numbers wear
# ---------------------------------------------------------------------------

def _table(*rows_html):
    return '<table>' + ''.join(rows_html) + '</table>'


def test_a_prior_row_carrying_an_ALTERNATE_PREFIX_fact_is_not_taken_as_a_section():
    """MUST-REFUSE. A row that reports numbers is data, not a heading, and the
    prefix those numbers happen to be written with cannot change that.

    This is the boundary error in miniature: the row is judged in the RENDERER
    tree, where `i:nonFraction` and `ix:nonFraction` are just two strings and
    neither means anything. The answer comes from the strict view instead, so
    an alternate prefix is recognised exactly as the conventional one is."""
    prep = prepare(doc(_table(
        '<tr><td>Acetyl Chain</td></tr>',              # a real heading
        f'<tr><td>Prior year</td><td>{fact(prefix="i", fid="f-prior", text="299")}</td></tr>',
        f'<tr><td>Revenue</td><td>{fact(prefix="i")}</td></tr>',
    ), ix_prefix='i'))
    assert refused(prep) is None, refused(prep)
    ev, why = element_evidence(prep, 'f-1')
    assert why == 'ok', why
    assert ev['section'] == 'Acetyl Chain', \
        "the numeric row must be skipped and the real heading found above it"


def test_a_prior_row_with_NO_fact_IS_taken_as_the_section():
    """MUST-ALLOW twin. Without the skip the rule would be untestable — a check
    that never lets anything through is satisfied by refusing everything."""
    prep = prepare(doc(_table(
        '<tr><td>Acetyl Chain</td></tr>',
        f'<tr><td>Revenue</td><td>{fact()}</td></tr>',
    )))
    ev, why = element_evidence(prep, 'f-1')
    assert why == 'ok' and ev['section'] == 'Acetyl Chain'


# ---------------------------------------------------------------------------
# 9. EVERY CONSUMED VALUE WHOSE TYPE COLLAPSES WHITESPACE
#
# The official schemas declare, for the values this module reads:
#   ix:nonFraction @id                       xs:NCName
#   ix:nonFraction @contextRef/@unitRef      restrictions of xs:NCName
#   ix:nonFraction @name/@format             xs:QName
#   ix:nonFraction @scale                    xs:integer
#   xbrli:context @id, xbrli:unit @id        xs:ID
#   xbrli:measure content                    xs:QName
#   xbrldi:explicitMember @dimension/content xs:QName
#   xbrli:identifier content                 xs:token
#   xbrli:identifier @scheme                 restricted xs:anyURI
#
# These do NOT all derive from xs:token — xs:ID and xs:NCName do; xs:QName,
# xs:integer and xs:anyURI do not. What they SHARE is the facet: each one
# independently carries whiteSpace=COLLAPSE (XML Schema Part 2 §4.3.6). So XML
# whitespace around such a value carries no meaning, while whitespace INSIDE it
# still breaks the value.
#
# `sign` restricts xs:string, whose facet is PRESERVE. It is the control that
# proves the collapse is applied by declared type and not to everything.
#
# EVERY ROW IS THREE ASSERTIONS: the plain value works, the PADDED value works
# identically, and a value broken by INNER space is refused under its own name.
# A collapse that accepted everything would pass the first two alone.
# ---------------------------------------------------------------------------

def _ev(html, eid='f-1'):
    return element_evidence(prepare(html), eid)


def _pad(value):
    """XML whitespace on both sides — the four characters XML calls space."""
    return f'\t {value} \n'


#: label, build(value) -> (evidence, why), lawful value, broken value, reason
_COLLAPSE_CASES = [
    ('fact @name',
     lambda v: _ev(doc(row(['R', fact(name=v)]))),
     'us-gaap:Revenues', 'us-gaap:Rev enues', 'malformed_concept_name'),
    ('fact @contextRef',
     lambda v: _ev(doc(row(['R', fact(contextRef=v)]))),
     'c1', 'c 1', 'malformed_context_ref'),
    ('fact @unitRef',
     lambda v: _ev(doc(row(['R', fact(unitRef=v)]))),
     'u1', 'u 1', 'malformed_unit_ref'),
    ('fact @format',
     lambda v: _ev(doc(row(['R', fact(format=v)]))),
     'ixt:num-dot-decimal', 'ixt:num dot', 'malformed_format'),
    ('fact @scale',
     lambda v: _ev(doc(row(['R', fact(scale=v)]))),
     '6', '6 0', 'malformed_scale'),
    ('context @id',
     lambda v: _ev(doc(row(['R', fact(contextRef='c1')]), ctx_id=v)),
     'c1', 'c 1', 'undefined_context'),
    # (a lawful scale of ANY length belongs to `xs:integer`; see the pair of
    #  tests below the table, which pin the length boundary explicitly)
    ('unit @id',
     lambda v: _ev(doc(row(['R', fact(unitRef='u1')]), unit_id=v)),
     'u1', 'u 1', 'undefined_unit'),
    ('measure content',
     lambda v: _ev(doc(row(['R', fact()]), measure=v)),
     'iso4217:USD', 'iso4217:U SD', 'malformed_unit_structure'),
    ('explicitMember @dimension',
     lambda v: _ev(doc(row(['R', fact()]),
                       member=(v, 'us-gaap:ProductMember'))),
     'srt:StatementGeographicalAxis', 'srt:State ment',
     'malformed_context_structure'),
    ('explicitMember content',
     lambda v: _ev(doc(row(['R', fact()]),
                       member=('srt:StatementGeographicalAxis', v))),
     'us-gaap:ProductMember', 'us-gaap:Product Member',
     'malformed_context_structure'),
    ('identifier content',
     lambda v: _ev(doc(row(['R', fact()]), cik=v)),
     '0000320193', '00003 20193', 'malformed_context_structure'),
    ('identifier @scheme',
     lambda v: _ev(doc(row(['R', fact()]), scheme=v)),
     'http://www.sec.gov/CIK', 'http://www.sec.gov/C IK',
     'malformed_context_structure'),
    # `decimals` AND `precision` HAVE LEFT THIS TABLE. This table asserts one
    # thing — "XML padding carries no meaning for this type" — and that is only
    # half true of them: they are UNIONS whose `INF` member restricts
    # `xs:string`, which PRESERVES, while the numeric member collapses. A row
    # here would have to claim padding is always harmless, which is exactly the
    # false rule that let ` INF ` through. Their two-sided behaviour is pinned
    # where it belongs, on the accuracy law itself, in
    # `test_semantic_fact_value.py`:
    #   test_a_PADDED_INF_is_MALFORMED_because_that_union_member_PRESERVES
    #   test_the_INTEGER_member_still_collapses_and_exact_INF_still_binds
    #   test_NON_XML_whitespace_is_not_whitespace_at_all
    # LAWFUL IS `false` HERE, deliberately: a `true` nil fact is well-formed but
    # refuses with its own reason, so it could never be this table's "ok" case.
    ('fact @{http://www.w3.org/2001/XMLSchema-instance}nil',
     lambda v: _ev(doc(row(['R', fact(**{'xsi:nil': v})]),
                       extra_ns=' xmlns:xsi="http://www.w3.org/2001/'
                                'XMLSchema-instance"')),
     'false', 'fal se', 'malformed_nil'),
]


@pytest.mark.parametrize('label,build,lawful,broken,reason',
                         _COLLAPSE_CASES,
                         ids=[c[0] for c in _COLLAPSE_CASES])
def test_a_collapse_faceted_value_ignores_XML_padding_but_not_inner_space(
        label, build, lawful, broken, reason):
    assert build(lawful)[1] == 'ok', f'{label}: the plain value must work'
    assert build(_pad(lawful))[1] == 'ok', \
        f'{label}: XML padding carries no meaning for this type'
    assert build(broken)[1] == reason, \
        f'{label}: inner space gave {build(broken)[1]!r}, wanted {reason!r}'


@pytest.mark.parametrize('digits', [4299, 4300, 4301, 5001, 20000])
def test_a_LAWFUL_scale_of_any_length_is_not_a_MALFORMED_filing(digits):
    """`ix:scale` is `xs:integer`, which XSD does not bound. `xml_integer`
    CONVERTS, so CPython's 4,300-digit string-conversion gate made it return
    None past that length and the reader reported `malformed_scale` — OUR
    runtime's limit, announced as a defect in the filing, and with the very
    same reason a genuinely broken `6.9` gets. No consumer could tell them
    apart.

    The value is never printed: `f"{huge}"` is the same string conversion, and
    stringifying it here would reproduce the defect inside its own test."""
    why = _ev(doc(row(['R', fact(scale='9' * digits)])))[1]
    assert why == 'ok', (
        f'a lexically lawful {digits}-digit scale reported {why!r}')


@pytest.mark.parametrize('scale', ['6.9', '1_0', '', '１２', '6 0'])
def test_a_GENUINELY_malformed_scale_still_says_so(scale):
    """MUST-CATCH twin. Widening the length must not widen the grammar: a
    non-integer, a Python underscore, an empty value, full-width digits and an
    inner space all stay `malformed_scale`."""
    assert _ev(doc(row(['R', fact(scale=scale)])))[1] == 'malformed_scale'


def test_the_table_above_covers_every_collapsed_attribute_the_CODE_declares():
    """DERIVED FROM LIVE CODE, so the table cannot fall behind it.

    If a new attribute is ever added to `_COLLAPSED` without a bad/good pair
    here, this fails — which is the only way a coverage claim stays true."""
    from driver.relocation.inline_html import _COLLAPSED
    covered = {label.split('@')[-1].split()[0] for label, *_ in _COLLAPSE_CASES
               if '@' in label}
    covered |= {'id'}          # 'context @id' / 'unit @id' / the fact-id tests
    # BOTH DIRECTIONS. One way only catches a new collapsed attribute with no
    # pair; it does NOT catch a pair left behind for an attribute the code has
    # stopped collapsing, which would keep asserting a rule that no longer
    # exists — a test passing for a reason its name no longer describes.
    assert _COLLAPSED - covered == set(), \
        f'no bad/good pair for {sorted(_COLLAPSED - covered)}'
    assert covered - _COLLAPSED == set(), \
        f'pairs remain for attributes the code no longer collapses: ' \
        f'{sorted(covered - _COLLAPSED)}'


def test_a_PADDED_element_id_is_the_same_id_the_schema_declares():
    """The fact's own @id, which the table cannot cover because padding it also
    changes the key the caller looks it up by.

    Measured at the other boundary before relying on this: across ALL
    13,775,616 graph Facts — a full server-side aggregate, read-only bracket
    lastCommittedTxn 9226081 unchanged either side — ZERO carry a padded or
    inner-spaced fact_id, context_id or unit_ref. So no live fact changes
    meaning either way."""
    ev, why = _ev(doc(row(['Revenue', fact(fid=_pad('f-1'))])), 'f-1')
    assert why == 'ok', why
    assert ev['row_text'] == 'Revenue 390'


def test_an_id_with_an_INNER_space_is_still_not_a_name():
    """BAD twin. Collapse removes padding; it does not join words."""
    assert _ev(doc(row(['Revenue', fact(fid='f 1')])), 'f 1') \
        == (None, 'malformed_id')


def test_sign_PRESERVES_whitespace_AT_THE_REAL_BIND_DOOR():
    """THE CONTROL that keeps the collapse honest, taken through `bind_graph_fact`
    rather than the evidence helper — a padded sign must not become a negation
    where the VALUE is actually computed.

    `sign` restricts xs:string, whose facet is PRESERVE, so ' -' is not '-'. The
    lawful '-' negates and reconciles; the padded one is not a lawful sign, so
    the value cannot be reproduced and the fact refuses instead of silently
    binding a number of the wrong sign."""
    common = dict(inline_element_id='f-1',
                  concept='us-gaap:Revenues', context_id='c1',
                  unit_ref='u1', unit_name='iso4217:USD', is_divide='0',
                  period_type='duration', start_date='2026-01-01',
                  end_date='2026-04-01', dims=(), entity_cik='0000320193',
                  concept_namespace=GAAP,
                  graph_concept_qname='us-gaap:Revenues')
    good, why = bind_graph_fact(doc(row(['R', fact(sign='-')])),
                                raw_value='-390,000,000', **common)
    assert why == 'ok' and good is not None, why
    bad, why2 = bind_graph_fact(doc(row(['R', fact(sign=' -')])),
                                raw_value='-390,000,000', **common)
    assert bad is None, "a padded sign must not negate"
    # THE EXACT PUBLIC REASON. `!= 'ok'` would pass on any refusal at all,
    # including one from an unrelated rule that happened to fire first.
    assert why2 == 'exact_id_malformed_sign', why2


#: An OPTIONAL attribute is ABSENT or LAWFUL — never present-and-empty; a
#: REQUIRED one is present and lawful before it is ever looked up. Each row
#: names the exact refusal, so a rule cannot be satisfied by a different one.
_ATTRIBUTE_LAW = [
    ('sign absent is the positive case', {}, 'ok'),
    ('sign present must be exactly "-"', {'sign': '-'}, 'ok'),
    ('sign present and empty is not lawful', {'sign': ''}, 'malformed_sign'),
    ('sign present and anything else', {'sign': '+'}, 'malformed_sign'),
    ('format absent means no transform', {}, 'ok'),
    ('format present must be a QName', {'format': 'ixt:num-dot-decimal'}, 'ok'),
    ('format present and empty', {'format': ''}, 'malformed_format'),
    ('format present but unbound prefix', {'format': 'nope:x'},
     'malformed_format'),
    ('contextRef present and lawful', {'contextRef': 'c1'}, 'ok'),
    ('contextRef present but not a name', {'contextRef': 'c 1'},
     'malformed_context_ref'),
    ('contextRef lawful but undeclared', {'contextRef': 'c-nope'},
     'undefined_context'),
    ('unitRef present and lawful', {'unitRef': 'u1'}, 'ok'),
    ('unitRef present but not a name', {'unitRef': 'u 1'},
     'malformed_unit_ref'),
    ('unitRef lawful but undeclared', {'unitRef': 'u-nope'}, 'undefined_unit'),
]


@pytest.mark.parametrize('label,attrs,expected', _ATTRIBUTE_LAW,
                         ids=[c[0] for c in _ATTRIBUTE_LAW])
def test_an_optional_attribute_is_absent_or_lawful_and_a_required_one_resolves(
        label, attrs, expected):
    """Every refusal here has a lawful twin in the same list, so none of these
    rules can be satisfied by refusing everything."""
    where = 'sign' if 'sign' in attrs else ('format' if 'format' in attrs
                                            else None)
    if where and attrs[where] == '':
        # present-and-empty has to be written into the markup by hand: the
        # helper omits an attribute whose value is empty, which is exactly the
        # lawful shape this row is contrasting with.
        html = doc(row(['R', fact().replace('>390', f' {where}="">390')]))
    else:
        html = doc(row(['R', fact(**attrs)]))
    assert element_evidence(prepare(html), 'f-1')[1] == expected, label


#: A REQUIRED reference fails in exactly three ways, and each has its own name.
#: Pinned through `bind_graph_fact` — the door production actually calls — so a
#: reason that only exists in the helper cannot pass for the real contract.
_REQUIRED_REFERENCE_STATES = [
    ('contextRef absent', 'contextRef', None, 'exact_id_missing_context_ref'),
    ('contextRef present but empty', 'contextRef', '',
     'exact_id_malformed_context_ref'),
    ('contextRef present but not a name', 'contextRef', 'c 1',
     'exact_id_malformed_context_ref'),
    ('contextRef lawful but undeclared', 'contextRef', 'c-nope',
     'exact_id_undefined_context'),
    ('unitRef absent', 'unitRef', None, 'exact_id_missing_unit_ref'),
    ('unitRef present but empty', 'unitRef', '', 'exact_id_malformed_unit_ref'),
    ('unitRef present but not a name', 'unitRef', 'u 1',
     'exact_id_malformed_unit_ref'),
    ('unitRef lawful but undeclared', 'unitRef', 'u-nope',
     'exact_id_undefined_unit'),
]

_BIND_KW = dict(inline_element_id='f-1', concept='us-gaap:Revenues',
                context_id='c1', unit_ref='u1', unit_name='iso4217:USD',
                is_divide='0', period_type='duration',
                start_date='2026-01-01', end_date='2026-04-01', dims=(),
                entity_cik='0000320193', concept_namespace=GAAP,
                graph_concept_qname='us-gaap:Revenues', raw_value='390,000,000')


@pytest.mark.parametrize('label,attr,value,expected',
                         _REQUIRED_REFERENCE_STATES,
                         ids=[c[0] for c in _REQUIRED_REFERENCE_STATES])
def test_a_REQUIRED_reference_names_which_of_its_three_states_failed(
        label, attr, value, expected):
    """Absent, unlawful and undeclared need three different fixes, so they may
    never share one reason. Each is exact — `!= "ok"` would pass on any refusal
    at all, including one from a rule that fired first for another cause."""
    if value is None:
        piece = fact()
        piece = piece.replace(f' {attr}="{"c1" if attr == "contextRef" else "u1"}"', '')
    else:
        piece = fact(**{attr: value}) if value else \
            fact().replace(f'{attr}="{"c1" if attr == "contextRef" else "u1"}"',
                           f'{attr}=""')
    assert bind_graph_fact(doc(row(['R', piece])), **_BIND_KW)[1] == expected, \
        label


def test_the_LAWFUL_twin_of_all_eight_states_binds():
    """MUST-ALLOW. Eight refusals above; one acceptance here, through the same
    door with the same graph row — otherwise the whole group could be satisfied
    by a door that refuses everything."""
    bound, why = bind_graph_fact(doc(row(['R', fact()])), **_BIND_KW)
    assert why == 'ok' and bound is not None, why


def test_NON_XML_whitespace_is_not_whitespace_and_is_never_collapsed():
    """U+00A0 and U+3000 are not among XML's four space characters, so an id
    padded with them is a DIFFERENT id, not a padded one. Python's own
    `.strip()`/`.split()` would eat them — exactly the confusion that made this
    module refuse and accept the wrong things before."""
    assert _ev(doc(row(['Revenue', fact(fid='\u00a0f-1\u3000')])), 'f-1') \
        == (None, 'id_not_found')


# ---------------------------------------------------------------------------
# 10. THE VIEWS DISAGREEING IS ITS OWN, NAMED OUTCOME
# ---------------------------------------------------------------------------

def test_VIEWS_DISAGREE_is_reachable_and_is_not_the_wellformedness_reason():
    """The two refusals are different questions and must never share a name:
    one says the bytes are not XML, the other says two readings of lawful bytes
    do not describe the same page."""
    assert VIEWS_DISAGREE != NOT_WELL_FORMED
    from driver.relocation.inline_html import _Fact, _bridge

    class N:
        def __init__(self, **kw):
            self.kw = kw

        def get(self, k):
            return self.kw.get(k)

    sem = [N(id='f-1', name='us-gaap:Revenues', contextRef='c1', scale='6')]
    assert _bridge(sem, []) is None, "a count mismatch abstains"
    # the differing-attribute abstention that was asserted here is GONE with
    # the deleted fingerprint (SEQ 264 §2d): pairing truth is source order.
    ok = _bridge(sem, [N(id='f-1', name='us-gaap:Revenues',
                         contextref='c1', scale='6')])
    assert ok is not None and isinstance(ok[0], _Fact), "and agreement pairs"


# ---- SEQ 264 §2a — the case-mangled-unknown MUST-ALLOW controls -----------
#
# The product scope is WELL-FORMED XML, not schema validation: an unknown
# attribute the strict view rightly ignores must not change an otherwise
# lawful fact. Today it does — the HTML view folds `Scale` to `scale`, the
# semantic side is absent, the seven-attribute comparison sees a mismatch,
# and the WHOLE door refuses a lawful document with VIEWS_DISAGREE. These
# controls state the lawful outcome and are RED until the reviewer-ruled
# correction lands; the distinct-fact twins beside them pin what a REAL
# cross-pair still must do.

@pytest.mark.parametrize('mangled', ['Scale="3"', 'Sign="-"', 'Format="x"'])
def test_a_case_mangled_UNKNOWN_attribute_does_not_refuse_a_lawful_fact(
        mangled):
    """MUST-ALLOW (SEQ 264 §2a): the lowercase semantic attribute is absent,
    the unknown mangled spelling is ignored by the strict view, and the fact
    must bind on its strict-view reading."""
    f = fact()
    if mangled.startswith('Scale'):
        f = f.replace(' scale="6"', '')
    f = f.replace(' decimals="0"', f' decimals="0" {mangled}')
    ev, why = _ev(doc(row(['R', f])))
    assert why == 'ok', f'{mangled}: lawful fact refused with {why!r}'


def test_two_DISTINCT_facts_pair_in_SOURCE_ORDER_never_crossed():
    """The anti-crossing law after SEQ 264 §2d: pairing truth is
    `_align_views`' proven source order. Two distinct facts come back
    first-with-first, second-with-second; crossing is closed UPSTREAM by
    the per-spelling totals (a view seeing different counts abstains), and
    indistinguishable pairs are refused BY NAME downstream (duplicate_id /
    ambiguous_identity) — never silently crossed here."""
    from driver.relocation.inline_html import _bridge

    class V:
        def __init__(self, tag):
            self.tag = tag

        def get(self, k):
            return None

    s1, s2, r1, r2 = V('s1'), V('s2'), V('r1'), V('r2')
    pairs = _bridge([s1, s2], [r1, r2])
    assert pairs is not None
    assert pairs[0].sem is s1 and pairs[0].ren is r1
    assert pairs[1].sem is s2 and pairs[1].ren is r2
    assert _bridge([s1, s2], [r1]) is None, 'length mismatch still abstains'


def test_foster_parenting_keeps_each_facts_OWN_evidence():
    """SEQ 265 row-3 closure §1 (name per SEQ 266 §4) — the foster/table
    vector, through the PUBLIC door: one fact sits DIRECTLY inside <table>
    (a position HTML repair is known to relocate) while a second follows
    the table. Two facts with distinct ids, distinct contexts and distinct
    visible values; each must keep ITS OWN renderer evidence. This pins
    the fact-to-evidence MAPPING for THIS vector — no claim is made about
    all reorderings."""
    inner = fact(fid='f-1', text='111')
    after = fact(fid='f-2', text='222', contextRef='c2')
    html = doc(f'<table><tr><td>x</td></tr>{inner}</table>'
               f'<p>after {after}</p>')
    html = html.replace(
        '<xbrli:context id="c1">',
        '<xbrli:context id="c2"><xbrli:entity>\n'
        '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
        '</xbrli:identifier>\n'
        '</xbrli:entity><xbrli:period><xbrli:startDate>2026-01-01'
        '</xbrli:startDate>\n'
        '<xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period>'
        '</xbrli:context>\n'
        '<xbrli:context id="c1">')
    prep = prepare(html)
    ev1, why1 = element_evidence(prep, 'f-1')
    ev2, why2 = element_evidence(prep, 'f-2')
    assert why1 == 'ok' and why2 == 'ok', (why1, why2)
    assert ev1['displayed'] == '111', ev1['displayed']
    assert ev2['displayed'] == '222', ev2['displayed']


# ---- CL-042 (EU-070 / EU-071 / EU-072): the visibility law's three pinned
# behaviors — each node is its member's mutation detector -------------------

def test_EU070_template_contents_are_never_rendered():
    """WHATWG HTML LS §4.12.3 (snapshot 2026-07-20): template contents are
    template contents, NOT rendered children — no author display reveals
    them. The unconditional prune is the spec, pinned by behavior."""
    prep = prepare(doc(row(['Revenue', fact()])
                       + '<template><p>TSECRET</p></template>'))
    assert 'TSECRET' not in prep['text']
    assert 'Revenue 390' in prep['text']


def test_EU071_content_visibility_hidden_prunes():
    """CSS Containment 2 content-visibility:hidden (census snapshot
    2026-07-20): the element's contents are skipped — pinned by behavior."""
    prep = prepare(doc(row(['Revenue', fact()])
                       + '<div style="content-visibility:hidden">CVSECRET'
                         '</div>'))
    assert 'CVSECRET' not in prep['text']
    assert 'Revenue 390' in prep['text']


def test_EU072_ua_hidden_elements_stay_hidden_by_the_named_api():
    """HTML LS Rendering §15.3.1 UA-default hidden elements (style among
    them) — recognizing them rides the PINNED bs4 Tag.name attribute
    (bs4 4.13.3): a wrong attribute name blinds every name-based
    visibility branch, and THIS node reddens."""
    prep = prepare(doc(row(['Revenue', fact()])
                       + '<style>CSSSECRET{}</style>'))
    assert 'CSSSECRET' not in prep['text']
    assert 'Revenue 390' in prep['text']


# ---- CL-090 (EU-137..EU-142): the style-state law's uncovered members ------

def test_EU138_an_important_earlier_winner_beats_a_later_plain_value():
    """CSS Cascade: !important beats a later normal declaration in the same
    style attribute — the (important, index) ordering key is load-bearing."""
    prep = prepare(doc(row(['Revenue', fact()])
                       + '<div style="display:none !important; '
                         'display:block">IMPSECRET</div>'))
    assert 'IMPSECRET' not in prep['text']
    assert 'Revenue 390' in prep['text']


def test_EU139_hidden_until_found_refuses_as_unsupported():
    """hidden=until-found is OUTSIDE the supported reader (SEQ 231 §2): the
    document REFUSES typed rather than silently hiding-or-showing content
    this reader cannot render faithfully."""
    prep = prepare(doc(row(['Revenue', fact()])
                       + '<div hidden="until-found">UFSECRET</div>'))
    assert prep.get('refused', '').startswith('unsupported_style')
    assert 'until-found' in prep['refused']


def test_EU141_the_all_shorthand_resets_an_earlier_display_none():
    """The 'all' shorthand (CSS Cascade 4 §3.3) with a wide local keyword
    resets display too — content an earlier display:none hid becomes
    visible; a dead 'all' branch would leave it hidden."""
    prep = prepare(doc(row(['Revenue', fact()])
                       + '<div style="display:none; all:initial">ALLTEXT'
                         '</div>'))
    assert 'ALLTEXT' in prep['text']
