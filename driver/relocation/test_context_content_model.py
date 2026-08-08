"""#827 Stage 3 — ONE content-model rule for `xbrli:segment` / `xbrli:scenario`.

XBRL 2.1 makes these OPEN context components (`xs:any`, namespace `##other`),
and XBRL Dimensions 1.0 §3.1.4.4 says in terms that not every element inside
them is a dimension element. So "only `explicitMember` or `typedMember`" is a
restriction the standard does not impose — but the container is not a free-for-
all either: its open content is declared `minOccurs="1"`, so PRESENT-AND-EMPTY
is malformed.

That gives one rule with four outcomes, and this file pins all four rather than
letting a separate empty-container check and a separate content check each
half-answer:

    absent                              -> allowed
    present and empty / whitespace-only -> malformed  (cardinality)
    present, supported dimensions       -> handled
    present, lawful open content        -> UNSUPPORTED, not malformed
    present, typed dimension            -> the existing typed reason

THE DISTINCTION THAT MATTERS: `malformed` accuses the filer of writing invalid
markup. `unsupported` says this product cannot represent lawful markup yet.
Reporting the second as the first is untrue, and it is the kind of untruth that
survives because nobody re-reads a refusal they agree with.

Refusing is right either way while the contract cannot carry non-XDT content —
and refusing must never become IGNORING, since dropping that content would
merge two genuinely different contexts into one.

Spec sources:
  XBRL 2.1 (Rec 2003-12-31 + errata 2013-02-20) — context content model
  https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html
  XBRL Dimensions 1.0 (Rec 2012-01-25) §3.1.4.4
  https://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html
  Segment and Scenario Filters 1.0 (Rec 2009-06-22) — non-XDT content
  https://www.xbrl.org/specification/segmentscenariofilters/rec-2009-06-22/segmentscenariofilters-rec-2009-06-22.html
"""
import pytest

from driver.relocation.inline_html import element_evidence

_NS = ('xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
       'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
       'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
       'xmlns:us-gaap="http://fasb.org/us-gaap/2023" '
       'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
       'xmlns:co="http://example.org/company"')

#: A dimension this product supports, and one it does not.
EXPLICIT = ('<xbrldi:explicitMember dimension="us-gaap:Ax">us-gaap:M'
            '</xbrldi:explicitMember>')
TYPED = ('<xbrldi:typedMember dimension="us-gaap:Tx"><co:D>x</co:D>'
         '</xbrldi:typedMember>')
#: Lawful open content — a company element that is not a dimension at all.
NON_XDT = '<co:BusinessUnit>Retail</co:BusinessUnit>'
#: A LAWFUL typed member whose value happens to nest an element sharing a name
#: the context parser also looks for. Its reason must come from the typed rule,
#: never from a descendant-name coincidence.
TYPED_NESTING_A_CHECKED_NAME = (
    '<xbrldi:typedMember dimension="us-gaap:Tx"><co:Range>'
    '<xbrli:startDate>2024-01-01</xbrli:startDate></co:Range>'
    '</xbrldi:typedMember>')


def _doc(*, segment=None, scenario=None):
    """One lawful filing; only the open containers vary."""
    seg = '' if segment is None else f'<xbrli:segment>{segment}</xbrli:segment>'
    if segment == '':                       # the self-closed form, exactly
        seg = '<xbrli:segment/>'
    scen = '' if scenario is None else (
        '<xbrli:scenario/>' if scenario == ''
        else f'<xbrli:scenario>{scenario}</xbrli:scenario>')
    return (f'<html {_NS}><body><ix:header><ix:resources>'
            f'<xbrli:context id="c1"><xbrli:entity>'
            f'<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
            f'</xbrli:identifier>{seg}</xbrli:entity><xbrli:period>'
            f'<xbrli:startDate>2024-01-01</xbrli:startDate>'
            f'<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>{scen}'
            f'</xbrli:context><xbrli:unit id="u1">'
            f'<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
            f'</ix:resources></ix:header>'
            f'<p><ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
            f'unitRef="u1" scale="6" decimals="-6">390</ix:nonFraction></p>'
            f'</body></html>')


def _reason(**kw):
    _ev, why = element_evidence(_doc(**kw), 'f1')
    return why


# ---------------------------------------------------------------------------
# MUST-ALLOW — without these the rule could refuse everything and look right
# ---------------------------------------------------------------------------

def test_an_ABSENT_segment_and_scenario_are_lawful():
    """Both containers are optional. This is the overwhelmingly common shape."""
    assert _reason() == 'ok'


def test_a_SUPPORTED_explicit_member_still_binds():
    assert _reason(segment=EXPLICIT) == 'ok'


# ---------------------------------------------------------------------------
# PRESENT AND EMPTY — a cardinality failure, and genuinely malformed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('empty', ['', '   ', '\n\t'],
                         ids=['self-closed', 'spaces', 'newline-tab'])
def test_an_EMPTY_segment_is_malformed(empty):
    """The container is optional; writing it empty is not. XBRL 2.1 declares
    the open content `minOccurs="1"`, so a present-but-empty `segment` states
    a dimension set it does not carry — and it currently ATTACHES."""
    assert _reason(segment=empty) == 'malformed_context_structure'


@pytest.mark.parametrize('empty', ['', '   '], ids=['self-closed', 'spaces'])
def test_an_EMPTY_scenario_is_malformed(empty):
    assert _reason(scenario=empty) == 'malformed_context_structure'


# ---------------------------------------------------------------------------
# LAWFUL OPEN CONTENT — refuse, but say the true thing
# ---------------------------------------------------------------------------

def test_lawful_NON_XDT_content_is_UNSUPPORTED_not_malformed():
    """The filing is well-formed and the markup is lawful; this product simply
    cannot represent it. Calling it malformed accuses the filer of an error
    they did not make."""
    assert _reason(segment=NON_XDT) == 'unsupported_non_xdt_context'


def test_lawful_non_XDT_BESIDE_a_supported_dimension_is_also_unsupported():
    """The dangerous shape: a real dimensional fact travelling with lawful open
    content. It must NOT be ignored — dropping the open content would merge two
    different contexts — and it must not be called malformed either."""
    assert _reason(segment=EXPLICIT + NON_XDT) == 'unsupported_non_xdt_context'


def test_the_scenario_container_follows_the_same_rule():
    assert _reason(scenario=NON_XDT) == 'unsupported_non_xdt_context'


#: An element in the XBRL INSTANCE namespace. `xs:any namespace="##other"`
#: admits any namespace EXCEPT the instance namespace itself, so this is not
#: lawful open content — it is markup where the schema forbids it.
INSTANCE_NS_CHILD = '<xbrli:notAMember>x</xbrli:notAMember>'


@pytest.mark.parametrize('container', ['segment', 'scenario'])
def test_an_INSTANCE_NAMESPACE_child_is_malformed_in_BOTH_containers(container):
    """`##other` MEANS OTHER. My first version of this rule treated every
    non-member child as lawful open content and would have called this
    `unsupported`; an existing attack case caught it. Both containers are
    driven here because they share one rule — proving it on `segment` alone
    would leave `scenario` asserting nothing."""
    assert _reason(**{container: INSTANCE_NS_CHILD}) == \
        'malformed_context_structure'


# ---------------------------------------------------------------------------
# TYPED DIMENSIONS — the existing truthful reason, and it must own the naming
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 827B12 — the context ATTRIBUTE / xsi:type / character-content shape law.
# Normative: XBRL 2.1 (Rec 2003-12-31 + errata 2013-02-20) §4.7 + the pinned
# instance schema (named types :602-666; forever = empty complexType :650-652).
# Every legality below was proven mechanically against that schema (lxml
# XMLSchema): ordinary attributes are unlicensed on ALL context elements;
# xsi:schemaLocation/noNamespaceSchemaLocation are lawful anywhere; xsi:nil is
# unlawful (nothing nillable); the exact own-type xsi:type spellings are lawful
# (incl. the date triad dateUnion/xs:date/xs:dateTime, any prefix alias); a
# RESOLVED custom-derived type is lawful XBRL this product cannot verify ->
# unsupported, never malformed; anonymous-typed elements admit no xsi:type.
# ---------------------------------------------------------------------------

_XNS = _NS + (' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
              ' xmlns:xs="http://www.w3.org/2001/XMLSchema"'
              ' xmlns:ALIAS="http://www.w3.org/2001/XMLSchema"'
              ' xmlns:XB2="http://www.xbrl.org/2003/instance"'
              ' xmlns:cust="http://example.org/cust"')


def _cdoc(ctx):
    """One filing whose whole <context id="c1"> markup is supplied verbatim."""
    return (f'<html {_XNS}><body><ix:header><ix:resources>'
            f'{ctx}<xbrli:unit id="u1">'
            f'<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
            f'</ix:resources></ix:header>'
            f'<p><ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
            f'unitRef="u1" scale="6" decimals="-6">390</ix:nonFraction></p>'
            f'</body></html>')


_ENT = ('<xbrli:entity{ea}><xbrli:identifier scheme="http://www.sec.gov/CIK"'
        '{ia}>0000320193</xbrli:identifier>{seg}</xbrli:entity>')
_PERD = ('<xbrli:period{pa}><xbrli:startDate{sa}>2024-01-01</xbrli:startDate>'
         '<xbrli:endDate{ea2}>2024-06-30</xbrli:endDate></xbrli:period>')


def _ctx(ca='', ea='', ia='', seg='', pa='', sa='', ea2='', per=None, scen=''):
    period = per if per is not None else _PERD.format(pa=pa, sa=sa, ea2=ea2)
    return (f'<xbrli:context id="c1"{ca}>'
            + _ENT.format(ea=ea, ia=ia, seg=seg) + period + scen
            + '</xbrli:context>')


def _rz(ctx):
    _ev, why = element_evidence(_cdoc(ctx), 'f1')
    return why


@pytest.mark.parametrize('ctx', [
    _ctx(ca=' bad="1"'), _ctx(ea=' bad="1"'), _ctx(ia=' bad="1"'),
    _ctx(seg=f'<xbrli:segment bad="1">{EXPLICIT}</xbrli:segment>'),
    _ctx(scen=f'<xbrli:scenario bad="1">{EXPLICIT}</xbrli:scenario>'),
    _ctx(pa=' bad="1"'), _ctx(sa=' bad="1"'), _ctx(ea2=' bad="1"'),
    _ctx(per='<xbrli:period><xbrli:instant bad="1">2024-06-30'
             '</xbrli:instant></xbrli:period>'),
], ids=['context', 'entity', 'identifier', 'segment', 'scenario', 'period',
        'startDate', 'endDate', 'instant'])
def test_827B12_an_ORDINARY_attribute_is_malformed_everywhere(ctx):
    assert _rz(ctx) == 'malformed_context_structure'


@pytest.mark.parametrize('ctx', [
    _ctx(seg=f'<xbrli:segment>junk{EXPLICIT}</xbrli:segment>'),
    _ctx(scen=f'<xbrli:scenario>junk{EXPLICIT}</xbrli:scenario>'),
    _ctx().replace('</xbrli:entity>', '</xbrli:entity>junk'),
    _ctx().replace('</xbrli:identifier>', '</xbrli:identifier>junk'),
    _ctx(per='<xbrli:period>junk<xbrli:startDate>2024-01-01'
             '</xbrli:startDate><xbrli:endDate>2024-06-30</xbrli:endDate>'
             '</xbrli:period>'),
], ids=['segment', 'scenario', 'context', 'entity', 'period'])
def test_827B12_direct_TEXT_beside_a_member_is_malformed(ctx):
    """Open to ELEMENTS, not arbitrary character text (schema-proven), in
    ALL FIVE element-only containers."""
    assert _rz(ctx) == 'malformed_context_structure'


@pytest.mark.parametrize('forever', [
    '<xbrli:forever>junk</xbrli:forever>',
    '<xbrli:forever>  \n </xbrli:forever>',
    '<xbrli:forever><xbrli:instant>2024-01-01</xbrli:instant></xbrli:forever>',
    '<xbrli:forever bad="1"/>',
    '<xbrli:forever><!-- c -->tail</xbrli:forever>',
    '<xbrli:forever xsi:type="xbrli:dateUnion"/>',
], ids=['text', 'ws-only-text', 'element-child', 'attribute',
        'comment-text-tail', 'xsi-type-on-anonymous'])
def test_827B12_a_NON_EMPTY_forever_is_malformed(forever):
    """`forever` is declared `<complexType/>`: empty content admits NO
    character item (XML whitespace included) and no attributes."""
    assert _rz(_ctx(per=f'<xbrli:period>{forever}</xbrli:period>')) \
        == 'malformed_context_structure'


@pytest.mark.parametrize('ctx', [
    _ctx(sa=' xsi:nil="true"'),
    _ctx(ia=' xml:lang="en"'),
    _ctx(pa=' xml:base="http://x/"'),
    _ctx(pa=' xsi:type="xbrli:contextEntityType"'),
    _ctx(ea=' xsi:type="nosuch:T"'),
    _ctx(ca=' xsi:type="xbrli:contextEntityType"'),
], ids=['xsi-nil', 'xml-lang', 'xml-base', 'wrong-official-type',
        'undeclared-prefix-type', 'xsi-type-on-anonymous-context'])
def test_827B12_unlicensed_special_attributes_are_malformed(ctx):
    assert _rz(ctx) == 'malformed_context_structure'


@pytest.mark.parametrize('ctx', [
    _ctx(per='<xbrli:period><xbrli:startDate xsi:type="xs:date">'
             '2024-01-01T00:00:00</xbrli:startDate><xbrli:endDate>2024-06-30'
             '</xbrli:endDate></xbrli:period>'),
    _ctx(per='<xbrli:period><xbrli:startDate xsi:type="xs:dateTime">'
             '2024-01-01</xbrli:startDate><xbrli:endDate>2024-06-30'
             '</xbrli:endDate></xbrli:period>'),
], ids=['xs-date-with-dateTime-value', 'xs-dateTime-with-date-value'])
def test_827B12_the_declared_TYPE_constrains_the_VALUE(ctx):
    """SEQ 373 B (XSD-proven): xsi:type selects ONE dateUnion member; a value
    of the OTHER member is invalid. Classified by the one shared
    parse_filing_boundary owner, never a second grammar."""
    assert _rz(ctx) == 'malformed_context_structure'


def test_827B12_a_NO_NAMESPACE_custom_type_parks_as_unsupported():
    """SEQ 373 A (reviewer-proven): a no-target-namespace schema can lawfully
    derive from the official base; xsi:type="MyEntity" with no default ns in
    scope resolves to (None, MyEntity) — RESOLVED, so unsupported, never
    malformed."""
    assert _rz(_ctx(ea=' xsi:type="MyEntity"')) == 'unsupported_context_type'


def test_827B12_a_MALFORMED_type_QName_is_malformed():
    assert _rz(_ctx(ea=' xsi:type="a:b:c"')) == 'malformed_context_structure'


def test_827B12_default_namespace_exact_type_is_lawful():
    """An unprefixed xsi:type takes the in-scope default namespace (the same
    _qname law as measures, XBRL 2.1 §4.8.2 erratum 62)."""
    assert _rz(_ctx(
        ea=' xmlns="http://www.xbrl.org/2003/instance"'
           ' xsi:type="contextEntityType"')) == 'ok'


def test_827B12_ws_padded_type_value_is_lawful():
    assert _rz(_ctx(ea=' xsi:type="  xbrli:contextEntityType\n"')) == 'ok'


@pytest.mark.parametrize('ctx', [
    _ctx(ca=' xsi:type="cust:MyContext"'),
    _ctx(ca=' xsi:type="MyContext"'),
    _ctx(ia=' xsi:type="cust:MyIdentifier"'),
    _ctx(ia=' xsi:type="MyIdentifier"'),
    _ctx(seg=f'<xbrli:segment xsi:type="cust:MySegment">{EXPLICIT}'
             f'</xbrli:segment>'),
    _ctx(seg=f'<xbrli:segment xsi:type="MySegment">{EXPLICIT}</xbrli:segment>'),
    _ctx(per='<xbrli:period><xbrli:forever xsi:type="cust:MyForever"/>'
             '</xbrli:period>'),
    _ctx(per='<xbrli:period><xbrli:forever xsi:type="MyForever"/>'
             '</xbrli:period>'),
], ids=['context-ns', 'context-no-ns', 'identifier-ns', 'identifier-no-ns',
        'segment-ns', 'segment-no-ns', 'forever-ns', 'forever-no-ns'])
def test_827B12_ANONYMOUS_typed_elements_admit_NO_xsi_type(ctx):
    """SEQ 374: XML Schema 1.0 Structures 2e §2.6.1/§3.3.4 — an asserted type
    must be validly derived FROM THE DECLARED TYPE. The pinned XBRL schema
    declares context/identifier/segment/forever with ANONYMOUS types, which no
    named type can reference or derive from, so NO replacement is possible:
    malformed, never the custom-derived park (which these wrongly reached)."""
    assert _rz(ctx) == 'malformed_context_structure'


def test_827B12_a_RESOLVED_custom_type_parks_as_unsupported():
    """Schema-proven: a custom type derived by extension from the official
    base VALIDATES — lawful XBRL this product cannot verify locally. The
    truthful answer is unsupported, never malformed."""
    assert _rz(_ctx(ea=' xsi:type="cust:MyEntity"')) \
        == 'unsupported_context_type'


def test_827B12_custom_type_is_judged_BEFORE_its_attributes():
    """A custom-typed element may lawfully carry attributes its type declares;
    this product cannot know them, so the unsupported verdict must come FIRST
    and the unknown attribute must not be mislabeled malformed."""
    assert _rz(_ctx(ea=' xsi:type="cust:MyEntity" bad="1"')) \
        == 'unsupported_context_type'


@pytest.mark.parametrize('ctx', [
    _ctx(),
    _ctx(sa=' xsi:type="xbrli:dateUnion"'),
    _ctx(sa=' xsi:type="xs:date"'),
    _ctx(sa=' xsi:type="ALIAS:date"'),
    _ctx(ea2=' xsi:type="xs:date"'),
    _ctx(per='<xbrli:period><xbrli:instant xsi:type="xs:date">2024-06-30'
             '</xbrli:instant></xbrli:period>'),
    _ctx(per='<xbrli:period><xbrli:instant xsi:type="xbrli:dateUnion">'
             '2024-06-30</xbrli:instant></xbrli:period>'),
    _ctx(per='<xbrli:period><xbrli:instant xsi:type="xs:dateTime">'
             '2024-06-30T00:00:00</xbrli:instant></xbrli:period>'),
    _ctx(ea2=' xsi:type="xbrli:dateUnion"'),
    _ctx(per='<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
             '<xbrli:endDate xsi:type="xs:dateTime">2024-06-30T00:00:00'
             '</xbrli:endDate></xbrli:period>'),
    _ctx(per='<xbrli:period><xbrli:startDate xsi:type="xs:dateTime">'
             '2024-01-01T00:00:00</xbrli:startDate><xbrli:endDate>2024-06-30'
             '</xbrli:endDate></xbrli:period>'),
    _ctx(seg=f'<xbrli:segment>  {EXPLICIT}\n\t</xbrli:segment>'),
    _ctx(scen=f'<xbrli:scenario>\n {EXPLICIT} </xbrli:scenario>'),
    _ctx(per='<xbrli:period><xbrli:forever><?pi d?></xbrli:forever>'
             '</xbrli:period>'),
    _ctx(ea=' xsi:type="xbrli:contextEntityType"'),
    _ctx(ea=' xsi:type="XB2:contextEntityType"'),
    _ctx(pa=' xsi:type="xbrli:contextPeriodType"'),
    _ctx(scen=f'<xbrli:scenario xsi:type="xbrli:contextScenarioType">'
              f'{EXPLICIT}</xbrli:scenario>'),
    _ctx(ca=' xsi:schemaLocation="http://x http://y"'),
    _ctx(ea=' xsi:noNamespaceSchemaLocation="http://y"'),
    _ctx(per='<xbrli:period>  <xbrli:startDate>2024-01-01</xbrli:startDate>'
             '\n\t<xbrli:endDate>2024-06-30</xbrli:endDate>  </xbrli:period>'),
    _ctx(per='<xbrli:period><!-- q --><xbrli:startDate>2024-01-01'
             '</xbrli:startDate><xbrli:endDate>2024-06-30</xbrli:endDate>'
             '</xbrli:period>'),
    _ctx(per='<xbrli:period><xbrli:forever/></xbrli:period>'),
    _ctx(per='<xbrli:period><xbrli:forever><!-- c --></xbrli:forever>'
             '</xbrli:period>'),
], ids=['plain-control', 'startDate-dateUnion', 'startDate-xs-date',
        'date-alias-prefix', 'endDate-xs-date', 'instant-xs-date',
        'instant-dateUnion', 'instant-xs-dateTime', 'endDate-dateUnion',
        'endDate-xs-dateTime', 'startDate-xs-dateTime',
        'segment-ws-beside-member', 'scenario-ws-beside-member',
        'forever-PI-only',
        'entity-own-type', 'entity-alias-own-type', 'period-own-type',
        'scenario-own-type', 'context-schemaLocation',
        'entity-noNamespaceSchemaLocation', 'ws-between-children',
        'comment-between-children', 'forever-empty', 'forever-comment-only'])
def test_827B12_MUST_ALLOW_every_lawful_shape(ctx):
    """The twins that keep the rule honest: exact own types (any prefix
    alias), the full date triad, both schema-location attributes, comments/
    PIs, XML whitespace, and the empty forever."""
    assert _rz(ctx) == 'ok'


# ---------------------------------------------------------------------------
# 827B14 — THE SHARED SIMPLE-CONTENT RULE (`_leaf`).
# XML 1.0 5e §2.5/§2.6: comments and processing instructions are NOT character
# data — a processor must not pass them as content — while XML Schema Part 1
# simple content admits character information items only, so an ELEMENT child
# is genuinely malformed. `_leaf` counted every child node, comments and PIs
# included, and therefore REFUSED lawful filings at six value doors. Proven
# mechanically against the pinned instance schema (measure/identifier/date with
# a comment or PI: VALID; with an element child: INVALID) and reproduced at the
# public door. The corpus count is zero in both directions; it prices the rule
# and does not create it.
# ---------------------------------------------------------------------------

def _ev(doc):
    ev, why = element_evidence(doc, 'f1')
    assert ev is not None, why
    return ev


@pytest.mark.parametrize('old, new, field, want', [
    pytest.param('>0000320193</xbrli:identifier>', '>00003<!--c-->20193</xbrli:identifier>',
                 'entity', '0000320193', id='identifier-comment'),
    pytest.param('>0000320193</xbrli:identifier>', '>00003<?p x?>20193</xbrli:identifier>',
                 'entity', '0000320193', id='identifier-PI'),
    pytest.param('<xbrli:startDate>2024-01-01</xbrli:startDate>',
                 '<xbrli:startDate>2024-<!--c-->01-01</xbrli:startDate>',
                 'period', ('2024-01-01', '2024-06-30'), id='startDate-comment'),
    pytest.param('<xbrli:startDate>2024-01-01</xbrli:startDate>',
                 '<xbrli:startDate>2024-<?p x?>01-01</xbrli:startDate>',
                 'period', ('2024-01-01', '2024-06-30'), id='startDate-PI'),
    pytest.param('<xbrli:endDate>2024-06-30</xbrli:endDate>',
                 '<xbrli:endDate>2024-<!--c-->06-30</xbrli:endDate>',
                 'period', ('2024-01-01', '2024-06-30'), id='endDate-comment'),
    pytest.param('<xbrli:endDate>2024-06-30</xbrli:endDate>',
                 '<xbrli:endDate>2024-<?p x?>06-30</xbrli:endDate>',
                 'period', ('2024-01-01', '2024-06-30'), id='endDate-PI'),
    # a LEADING comment: el.text is None, so every tail must carry the value
    pytest.param('>0000320193</xbrli:identifier>', '><!--c-->0000320193</xbrli:identifier>',
                 'entity', '0000320193', id='identifier-LEADING-comment'),
    pytest.param('<xbrli:startDate>2024-01-01</xbrli:startDate>',
                 '<xbrli:startDate><?p x?>2024-01-01</xbrli:startDate>',
                 'period', ('2024-01-01', '2024-06-30'), id='startDate-LEADING-PI'),
    # MANY interleaved nodes, order-sensitive: only in-order joining rebuilds it
    pytest.param('>0000320193</xbrli:identifier>',
                 '><!--a-->00<?p 1?>00<!--b-->32<?p 2?>0193</xbrli:identifier>',
                 'entity', '0000320193', id='identifier-INTERLEAVED'),
    pytest.param('<xbrli:startDate>2024-01-01</xbrli:startDate>',
                 '<xbrli:startDate>2<!--a-->0<?p 1?>2<!--b-->4-01-01</xbrli:startDate>',
                 'period', ('2024-01-01', '2024-06-30'), id='startDate-INTERLEAVED'),
])
def test_827B14_comments_and_PIs_are_ignored_and_the_VALUE_is_rebuilt(old, new,
                                                                     field, want):
    """The exact reconstructed semantic value, never merely reason 'ok'."""
    base = _doc()
    assert base.count(old) == 1, old
    assert _ev(base.replace(old, new))[field] == want


@pytest.mark.parametrize('node', ['<!--c-->', '<?p x?>'], ids=['comment', 'PI'])
def test_827B14_measure_and_explicitMember_values_are_rebuilt(node):
    """The two remaining `_leaf` classes, asserted on their own value fields,
    each for BOTH ignorable kinds (the six-class matrix)."""
    import driver.relocation.inline_html as IH
    base = _doc(segment=EXPLICIT)
    got = _ev(base.replace('<xbrldi:explicitMember dimension="us-gaap:Ax">us-gaap:M',
                           '<xbrldi:explicitMember dimension="us-gaap:Ax">us-gaap:'
                           + node + 'M'))
    assert got['dims'] == (('us-gaap:Ax', 'us-gaap:M'),)
    doc = _doc().replace('<xbrli:measure>iso4217:USD</xbrli:measure>',
                         '<xbrli:measure>iso4217:' + node + 'USD</xbrli:measure>')
    _ev(doc)                                        # the fact must still bind
    assert IH.prepare(doc)['units']['u1']['measures'] == ('iso4217:USD',)


@pytest.mark.parametrize('node', ['<!--c-->', '<?p x?>'], ids=['comment', 'PI'])
def test_827B14_instant_value_is_rebuilt(node):
    """The sixth class: an INSTANT period, whose value field is the pair."""
    doc = _doc().replace('<xbrli:startDate>2024-01-01</xbrli:startDate>'
                         '<xbrli:endDate>2024-06-30</xbrli:endDate>',
                         '<xbrli:instant>2024-<!--X-->06-30</xbrli:instant>'
                         .replace('<!--X-->', node))
    assert _ev(doc)['period'] == ('', '2024-06-30')


# THE UNRESOLVED-ENTITY CASE THAT STOOD HERE IS SUPERSEDED, NOT DROPPED. It
# attacked `_leaf` with `&foo;` declared in a DOCTYPE internal subset. Packet 15
# refuses every DOCTYPE at the document boundary, so that document is now
# rejected before `_leaf` runs, and an UNDECLARED entity is an XML syntax error
# — the shape cannot be delivered by either public door. Its successors are
# `test_827B15_a_DOCTYPE_is_refused_at_the_document_boundary`, whose
# `entity-rewrites-contextRef` case carries the same attack, and the numeric
# reference twin below. Re-testing it here would need a hand-built element that
# no input can produce, which proves nothing about this program.


def test_827B14_a_numeric_character_reference_is_ordinary_content():
    """MUST-ALLOW twin: a numeric character reference is parsed character
    content, never a child node — no DOCTYPE, nothing to refuse, and the
    element-child rule must not over-catch it."""
    doc = _doc().replace('>0000320193</xbrli:identifier>',
                         '>000032019&#51;</xbrli:identifier>')
    assert _ev(doc)['entity'] == '0000320193'


@pytest.mark.parametrize('old, new, reason', [
    pytest.param('>0000320193</xbrli:identifier>',
                 '><b>0000320193</b></xbrli:identifier>',
                 'malformed_context_structure', id='identifier-element-child'),
    pytest.param('<xbrli:startDate>2024-01-01</xbrli:startDate>',
                 '<xbrli:startDate><b>2024-01-01</b></xbrli:startDate>',
                 'malformed_context_structure', id='startDate-element-child'),
    pytest.param('<xbrli:measure>iso4217:USD</xbrli:measure>',
                 '<xbrli:measure><b>iso4217:USD</b></xbrli:measure>',
                 'malformed_unit_structure', id='measure-element-child'),
    # THE ISOLATED GUARD CASE: an EMPTY foreign element whose TAIL carries the
    # whole value. Joining tails alone would rebuild '0000320193' and attach;
    # only the element-child guard refuses it.
    pytest.param('>0000320193</xbrli:identifier>',
                 '><b/>0000320193</xbrli:identifier>',
                 'malformed_context_structure', id='identifier-EMPTY-element-plus-tail'),
])
def test_827B14_an_ELEMENT_child_still_refuses(old, new, reason):
    base = _doc()
    assert base.count(old) == 1, old
    _ev_none, why = element_evidence(base.replace(old, new), 'f1')
    assert _ev_none is None and why == reason, why


def test_827B14_plain_lawful_twins_unchanged():
    ev = _ev(_doc(segment=EXPLICIT))
    assert ev['entity'] == '0000320193'
    assert ev['period'] == ('2024-01-01', '2024-06-30')
    assert ev['dims'] == (('us-gaap:Ax', 'us-gaap:M'),)


def test_a_typed_dimension_keeps_its_own_reason():
    assert _reason(segment=TYPED) == 'typed_dimensions_unsupported'


def test_a_typed_value_NESTING_a_checked_name_still_says_typed():
    """A descendant-name coincidence must not rename this refusal. The parser
    compares direct children against every same-named DESCENDANT; a lawful
    typed value nesting `xbrli:startDate` therefore reported
    `malformed_context_structure`, taking the naming decision away from the
    rule that owns it."""
    assert _reason(segment=TYPED_NESTING_A_CHECKED_NAME) == \
        'typed_dimensions_unsupported'


# ---------------------------------------------------------------------------
# 827B15 — THE DOCUMENT-LEVEL DOCTYPE BOUNDARY.
# SEC EDGAR XBRL Guide June 2026 §11.1 (and EFM v49 December-2018 §5.2.5.1
# before it): an `.htm` attachment carrying a DOCTYPE declaration is not a
# valid Inline XBRL document. The declaration is refused at the DOCUMENT
# boundary — before any context, unit or fact is read — because the internal
# subset is a channel that changes what the filing appears to say: lxml
# expands internal entities inside ATTRIBUTE values even with
# `resolve_entities=False`, so `contextRef="&a;"` silently bound a fact to a
# context the markup never names. A DOCTYPE document can be perfectly
# well-formed, so `NOT_WELL_FORMED` would be a false reason; this rule owns
# its own.
# ---------------------------------------------------------------------------

def _prepare_reason(doc):
    import driver.relocation.inline_html as IH
    return IH.refused(IH.prepare(doc))


def _entity_ladder(levels, width=10, seed='c1'):
    """An internal subset whose top entity expands to `seed` repeated
    width**levels times — the classic amplification shape, built rather than
    pasted so the depth is a number a reader can vary."""
    decls = ['<!ENTITY e0 "%s">' % seed]
    for i in range(1, levels + 1):
        decls.append('<!ENTITY e%d "%s">' % (i, ('&e%d;' % (i - 1)) * width))
    return '<!DOCTYPE html [%s]>' % ''.join(decls), 'e%d' % levels


_LADDER_5, _LADDER_5_TOP = _entity_ladder(5)


@pytest.mark.parametrize('prologue, entity', [
    pytest.param('<!DOCTYPE html>', None, id='bare-declaration'),
    pytest.param('<!DOCTYPE html [<!ENTITY foo "x">]>', None,
                 id='unused-internal-subset'),
    pytest.param('<!DOCTYPE html [<!ENTITY a "c1">]>', 'a',
                 id='entity-rewrites-contextRef'),
    # NESTED entities in that same attribute. libxml2's entity amplification
    # limit fires WHILE THE ROOT ATTRIBUTE EXPANDS, so a boundary placed after
    # the parse never got to speak and the document was reported
    # NOT_WELL_FORMED — false, because it is forbidden by its DOCTYPE, not
    # malformed. The rule must therefore refuse at the DOCTYPE parse event,
    # before any expansion work is done on its behalf.
    pytest.param(_LADDER_5, _LADDER_5_TOP, id='nested-entity-amplification'),
])
def test_827B15_a_DOCTYPE_is_refused_at_the_document_boundary(prologue, entity):
    """Refused where it is declared, with its own truthful reason."""
    import driver.relocation.inline_html as IH
    doc = _doc()
    if entity:
        doc = doc.replace('contextRef="c1"', 'contextRef="&%s;"' % entity)
    doc = prologue + doc
    assert _prepare_reason(doc) == IH.DOCTYPE_FORBIDDEN
    ev, why = element_evidence(doc, 'f1')
    assert ev is None and why == IH.DOCTYPE_FORBIDDEN, why


def test_827B15_the_same_document_without_a_DOCTYPE_is_admitted():
    """MUST-ALLOW twin one: the identical markup, declaration removed."""
    assert _prepare_reason(_doc()) is None
    assert _ev(_doc())['context_ref'] == 'c1'


@pytest.mark.parametrize('old, new', [
    pytest.param('>0000320193</xbrli:identifier>', '>000032019&#51;</xbrli:identifier>',
                 id='numeric-character-reference'),
    pytest.param('</body>', '<p>a &amp; b</p></body>', id='predefined-reference'),
])
def test_827B15_ordinary_references_need_no_DOCTYPE_and_are_admitted(old, new):
    """MUST-ALLOW twins two and three: a numeric character reference and one of
    XML's five predefined references are character data — neither needs an
    internal subset, so the boundary must not touch them. (`&nbsp;` is NOT one
    of them; it is HTML, and would itself require a declaration.)"""
    doc = _doc().replace(old, new)
    assert _prepare_reason(doc) is None
    assert _ev(doc)['entity'] == '0000320193'


# ---------------------------------------------------------------------------
# 827B16 — THE UNIT SHAPE, judged by the SAME owner as the context shape.
# Derived from the pinned XBRL 2.1 instance schema and re-proven identical in
# the 2013 Inline-XBRL modified schema (both local official artifacts):
#
#   unit             ANONYMOUS complexType   attribute `id` (ID, required) ONLY
#   divide           ANONYMOUS complexType   no attributes
#   unitNumerator    NAMED xbrli:measuresType  no attributes
#   unitDenominator  NAMED xbrli:measuresType  no attributes
#   measure          NAMED xs:QName            no attributes
#
# The named/anonymous split decides `xsi:type` exactly as it does for contexts
# (XML Schema 1.0 Structures 2e §3.3.4, §2.6.1): nothing derives from an
# anonymous type, so an asserted type on `unit`/`divide` names something that
# cannot exist. On the three NAMED classes the declared type may be asserted,
# a DIFFERENT official type is malformed, and a resolved non-standard type is
# unsupported — we cannot prove its derivation locally, and saying "malformed"
# about a filing we merely cannot check would be a false finding.
# The frozen corpus prices this rule at ZERO (15,206 units, 2,085 divides,
# 17,291 measures; not one carries an xsi:type, a foreign attribute, or
# non-XML-whitespace text), so it disturbs no lawful filing.
# ---------------------------------------------------------------------------

_PLAIN_UNIT = ('<xbrli:unit id="u1">'
               '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>')
_XSI = 'http://www.w3.org/2001/XMLSchema-instance'


def _unit(inner, attrs=''):
    return '<xbrli:unit id="u1"%s>%s</xbrli:unit>' % (attrs, inner)


def _divide(num='<xbrli:measure>iso4217:USD</xbrli:measure>',
            den='<xbrli:measure>xbrli:shares</xbrli:measure>',
            d_attrs='', n_attrs='', dn_attrs='', mid=''):
    """`mid` is character data DIRECTLY inside <divide>, between its two sides
    — the position that tests divide's OWN content row rather than a side's."""
    return ('<xbrli:divide%s><xbrli:unitNumerator%s>%s</xbrli:unitNumerator>%s'
            '<xbrli:unitDenominator%s>%s</xbrli:unitDenominator></xbrli:divide>'
            % (d_attrs, n_attrs, num, mid, dn_attrs, den))


_MEASURE = '<xbrli:measure>iso4217:USD</xbrli:measure>'
_DEN_MEASURE = '<xbrli:measure>xbrli:shares</xbrli:measure>'


def _at(position, text):
    """The same character data placed in each ELEMENT-ONLY container in turn,
    so every content row is exercised at its own element and no row can be
    proven only by a neighbour."""
    if position == 'unit':
        return _unit(text + _MEASURE)
    if position == 'divide':
        return _unit(_divide(mid=text))
    if position == 'unitNumerator':
        return _unit(_divide(num=_MEASURE + text))
    if position == 'unitDenominator':
        return _unit(_divide(den=_DEN_MEASURE + text))
    raise AssertionError(position)


_ELEMENT_ONLY = ['unit', 'divide', 'unitNumerator', 'unitDenominator']


def _unit_doc(unit):
    """One filing whose whole <unit id="u1"> markup is supplied verbatim, on
    the SAME extended namespace header the context battery uses so `xsi`, `xs`
    and `cust` are declared."""
    base = _cdoc(_ctx())
    assert base.count(_PLAIN_UNIT) == 1, 'the unit fixture moved'
    return base.replace(_PLAIN_UNIT, unit)


def _unit_reason(unit):
    _ev_none, why = element_evidence(_unit_doc(unit), 'f1')
    return why


# --- the two ANONYMOUS elements: ANY xsi:type is malformed ------------------

@pytest.mark.parametrize('unit', [
    pytest.param(_unit('<xbrli:measure>iso4217:USD</xbrli:measure>',
                       ' xsi:type="xbrli:unitType"'), id='unit-invented-type'),
    pytest.param(_unit('<xbrli:measure>iso4217:USD</xbrli:measure>',
                       ' xsi:type="xs:anyType"'), id='unit-official-type'),
    pytest.param(_unit(_divide(d_attrs=' xsi:type="xbrli:divideType"')),
                 id='divide-invented-type'),
    pytest.param(_unit(_divide(d_attrs=' xsi:type="xs:anyType"')),
                 id='divide-official-type'),
    # THE CASE THAT SEPARATES THE TWO DOORS. A RESOLVED custom type is
    # `unsupported` on a NAMED element — but on an ANONYMOUS one there is
    # nothing it could have derived from, so it stays malformed. Without this
    # the anonymous rows could be quietly non-empty and every other case here
    # would still pass, which a mutation proved.
    pytest.param(_unit('<xbrli:measure>iso4217:USD</xbrli:measure>',
                       ' xsi:type="cust:MyUnit"'), id='unit-resolved-custom'),
    pytest.param(_unit(_divide(d_attrs=' xsi:type="cust:MyDivide"')),
                 id='divide-resolved-custom'),
])
def test_827B16_an_xsi_type_on_an_ANONYMOUS_unit_element_is_malformed(unit):
    """Nothing can derive from an anonymous type, so the assertion names a type
    that cannot exist — malformed, never merely unsupported."""
    assert _unit_reason(unit) == 'malformed_unit_structure'


# --- the three NAMED classes: exact ok / other-official malformed /
#     resolved custom unsupported / unresolvable malformed -------------------

@pytest.mark.parametrize('unit, reason', [
    # the DECLARED type, asserted explicitly — lawful
    pytest.param(_unit(_divide(n_attrs=' xsi:type="xbrli:measuresType"')),
                 'ok', id='numerator-declared-type'),
    pytest.param(_unit(_divide(dn_attrs=' xsi:type="xbrli:measuresType"')),
                 'ok', id='denominator-declared-type'),
    pytest.param(_unit('<xbrli:measure xsi:type="xs:QName">iso4217:USD'
                       '</xbrli:measure>'), 'ok', id='measure-declared-type'),
    # a DIFFERENT official type
    pytest.param(_unit(_divide(n_attrs=' xsi:type="xs:string"')),
                 'malformed_unit_structure', id='numerator-other-official'),
    pytest.param(_unit('<xbrli:measure xsi:type="xbrli:measuresType">'
                       'iso4217:USD</xbrli:measure>'),
                 'malformed_unit_structure', id='measure-other-official'),
    # a DIFFERENT official type from the OTHER official namespace: a measure is
    # xs:QName and nothing else, so xs:string is wrong even though it is a
    # perfectly real type. A mutation proved the xbrli-namespace case alone did
    # not hold this row down.
    pytest.param(_unit('<xbrli:measure xsi:type="xs:string">iso4217:USD'
                       '</xbrli:measure>'),
                 'malformed_unit_structure', id='measure-other-official-xs'),
    # a RESOLVED non-standard type: we cannot prove the derivation locally
    pytest.param(_unit(_divide(n_attrs=' xsi:type="cust:MyMeasures"')),
                 'unsupported_unit_type', id='numerator-resolved-custom'),
    pytest.param(_unit(_divide(dn_attrs=' xsi:type="cust:MyMeasures"')),
                 'unsupported_unit_type', id='denominator-resolved-custom'),
    pytest.param(_unit('<xbrli:measure xsi:type="cust:MyQName">iso4217:USD'
                       '</xbrli:measure>'),
                 'unsupported_unit_type', id='measure-resolved-custom'),
    # an UNRESOLVABLE or malformed type QName names nothing at all
    pytest.param(_unit(_divide(n_attrs=' xsi:type="nobody:Nope"')),
                 'malformed_unit_structure', id='numerator-undeclared-prefix'),
    pytest.param(_unit('<xbrli:measure xsi:type="a:b:c">iso4217:USD'
                       '</xbrli:measure>'),
                 'malformed_unit_structure', id='measure-malformed-qname'),
])
def test_827B16_the_NAMED_unit_types_get_the_three_way_door(unit, reason):
    assert _unit_reason(unit) == reason


# --- attributes: `id` on unit only, nothing anywhere else ------------------

@pytest.mark.parametrize('unit', [
    pytest.param(_unit('<xbrli:measure>iso4217:USD</xbrli:measure>',
                       ' order="1"'), id='unit-foreign-attr'),
    pytest.param(_unit(_divide(d_attrs=' order="1"')), id='divide-attr'),
    pytest.param(_unit(_divide(n_attrs=' order="1"')), id='numerator-attr'),
    pytest.param(_unit(_divide(dn_attrs=' order="1"')), id='denominator-attr'),
    pytest.param(_unit('<xbrli:measure order="1">iso4217:USD</xbrli:measure>'),
                 id='measure-attr'),
])
def test_827B16_an_UNLICENSED_attribute_is_malformed(unit):
    """The schema declares `id` on `unit` and no attribute at all elsewhere,
    with no wildcard anywhere — asserted against both official versions."""
    assert _unit_reason(unit) == 'malformed_unit_structure'


def test_827B16_the_required_id_stays_lawful_and_is_not_re_judged_here():
    """`unit/@id` is type="ID" use="required". It is owned by the existing
    resource-indexing door, not re-checked by the shape owner, so the lawful
    filing simply passes."""
    assert _unit_reason(_unit('<xbrli:measure>iso4217:USD</xbrli:measure>')) == 'ok'


# --- element-only content: XML whitespace is the ONLY blank ----------------

_XML_BLANKS = [pytest.param(' ', id='space'), pytest.param('\t', id='tab'),
               pytest.param('\r', id='CR'), pytest.param('\n', id='LF'),
               pytest.param(' \t\r\n', id='all-four')]
#: Characters Python calls blank that XML does not, and that ARE legal XML
#: characters — so they really do reach the shape owner as content.
_NOT_XML_BLANKS = [pytest.param('\xa0', id='NBSP'),
                   pytest.param('　', id='ideographic-space'),
                   pytest.param('​', id='zero-width-space'),
                   pytest.param('x', id='ordinary-text')]
#: VERTICAL TAB and FORM FEED are NOT legal XML 1.0 characters at all (XML 1.0
#: 5e §2.2 Char excludes them), so they never reach the shape owner: the
#: document boundary refuses them first, with its own truthful reason. Asserted
#: separately rather than folded in, because claiming the shape rule catches
#: them would be a false statement about which guard is load-bearing.
_ILLEGAL_XML_CHARS = [pytest.param('\x0b', id='vertical-tab'),
                      pytest.param('\x0c', id='form-feed')]


@pytest.mark.parametrize('position', _ELEMENT_ONLY)
@pytest.mark.parametrize('blank', _XML_BLANKS)
def test_827B16_XML_whitespace_between_unit_children_is_lawful(blank, position):
    """XML 1.0 §2.3 whitespace is exactly space, tab, CR and LF. Asserted at
    EVERY element-only container, so no container's content row is proven only
    by a neighbour's."""
    assert _unit_reason(_at(position, blank)) == 'ok'


@pytest.mark.parametrize('position', _ELEMENT_ONLY)
@pytest.mark.parametrize('text', _NOT_XML_BLANKS)
def test_827B16_NON_XML_whitespace_is_content_and_is_malformed(text, position):
    """Python's `str.strip()` treats NBSP and the ideographic space as blank;
    XML does not. These containers are element-only, so any of them is
    character content where none may appear — at each container in turn."""
    assert _unit_reason(_at(position, text)) == 'malformed_unit_structure'


def test_827B16_a_measure_carries_its_value_as_SIMPLE_content():
    """The opposite row, and the one that keeps the rest honest: a measure is
    xs:QName, so its characters ARE the value. If `measure` were treated as
    element-only, every lawful filing on earth would be refused."""
    import driver.relocation.inline_html as IH
    doc = _unit_doc(_unit(_MEASURE))
    ev, why = element_evidence(doc, 'f1')
    assert ev is not None, why
    assert IH.prepare(doc)['units']['u1']['measures'] == ('iso4217:USD',)


@pytest.mark.parametrize('text', _ILLEGAL_XML_CHARS)
def test_827B16_a_character_XML_forbids_is_refused_EARLIER(text):
    """Not the shape owner's catch, and saying otherwise would misplace the
    guard: these bytes cannot appear in a well-formed XML document at all."""
    import driver.relocation.inline_html as IH
    assert _unit_reason(_unit(text + '<xbrli:measure>iso4217:USD'
                              '</xbrli:measure>')) == IH.NOT_WELL_FORMED


# --- the lawful twins that must keep binding -------------------------------

def test_827B16_schema_location_is_licensed_on_unit_elements():
    """The same two xsi attributes the context shape already licenses."""
    for attr in ('xsi:schemaLocation="urn:x x.xsd"',
                 'xsi:noNamespaceSchemaLocation="x.xsd"'):
        assert _unit_reason(_unit('<xbrli:measure>iso4217:USD</xbrli:measure>',
                                  ' ' + attr)) == 'ok'


def test_827B16_a_COMPOUND_unit_still_binds():
    """A container may lawfully carry several measures. The shape rule must not
    quietly become a 1x1 rule."""
    import driver.relocation.inline_html as IH
    doc = _unit_doc(_unit('<xbrli:measure>iso4217:USD</xbrli:measure>'
                          '<xbrli:measure>xbrli:shares</xbrli:measure>'))
    ev, why = element_evidence(doc, 'f1')
    assert ev is not None, why
    assert IH.prepare(doc)['units']['u1']['measures'] == ('iso4217:USD',
                                                          'xbrli:shares')


def test_827B16_a_lawful_DIVIDE_still_binds():
    import driver.relocation.inline_html as IH
    doc = _unit_doc(_unit(_divide()))
    ev, why = element_evidence(doc, 'f1')
    assert ev is not None, why
    u = IH.prepare(doc)['units']['u1']
    assert u['is_divide'] and u['numerator'] == ('iso4217:USD',) \
        and u['denominator'] == ('xbrli:shares',)
