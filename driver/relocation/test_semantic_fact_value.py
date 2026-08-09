"""#827 — THE VALUE COMES FROM THE FACT, not from the rendered page.

Reconciliation used to transform the RENDERER's `displayed` text: the visible
characters of whatever a browser lays out under the element. Inline XBRL 1.1
§§10.1.1-10.1.2 defines the value from the XML fact instead, and the gap between
those two let five different unlawful shapes bind:

    <ix:nonFraction><b>390</b></...>        markup rendered to the same glyphs
    <ix:nonFraction format="fixed-zero"/>   nothing at all, transformed to 0
    <...><!--comment--></...>               a comment counted as no child
    <... xsi:nil="true"/>                   a fact that asserts it HAS no value
    <...> with no decimals or precision     a numeric fact with no accuracy

Every one of them binds a graph row to a number the filing does not state.

WHAT IT COST, measured read-only over the WHOLE frozen cache before the rule was
written — 1,768 filings, 2,310,466 facts:

    leaf, non-empty text (lawful)      2,274,437   98.441%
    nested nonFraction (lawful)           31,373    1.358%
    xsi:nil, every one of them `true`      4,656    0.202%
    comment/PI child                           0
    other markup child                         0
    nested + stray text                        0
    nested format disagreement                 0
    both decimals AND precision                0

The 4,656 are the same facts under all three of empty-text, nil and
no-accuracy — genuinely nil, and a nil fact cannot supply the value a non-nil
graph row asserts. So the whole rule refuses 0.202% of real facts, all of them
correctly. The standard decides legality; the census only made the price
explicit before the code changed.

Spec sources:
  Inline XBRL 1.1 (Rec 2013-11-18) §10.1.1 nonFraction, §10.1.2 value
  https://www.xbrl.org/specification/inlinexbrl-part1/rec-2013-11-18/inlinexbrl-part1-rec-2013-11-18.html
  XBRL 2.1 (Rec 2003-12-31 + errata 2013-02-20) §4.6.3 decimals/precision
  XML Schema Part 1 §2.6.2 xsi:nil · Part 2 §3.2.2 boolean lexical space
  https://www.w3.org/TR/xmlschema-2/#boolean
"""
import pytest

from driver.relocation import inline_html
from decimal import Decimal
from driver.relocation.inline_html import bind_graph_fact, printed_value

_NS = ('xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
       'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
       'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
       'xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12" '
       'xmlns:other="http://example.org/a-different-registry" '
       'xmlns:us-gaap="http://fasb.org/us-gaap/2023" '
       'xmlns:iso4217="http://www.xbrl.org/2003/iso4217"')

SHARES = ('<xbrli:unit id="u2"><xbrli:measure>xbrli:shares'
          '</xbrli:measure></xbrli:unit>')


def _doc(inner, extra_units=''):
    return (f'<html {_NS}><body><ix:header><ix:resources>'
            f'<xbrli:context id="c1"><xbrli:entity>'
            f'<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
            f'</xbrli:identifier></xbrli:entity><xbrli:period>'
            f'<xbrli:startDate>2024-01-01</xbrli:startDate>'
            f'<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            f'</xbrli:context><xbrli:unit id="u1">'
            f'<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
            f'{extra_units}</ix:resources></ix:header>'
            f'<p>{inner}</p></body></html>')


def _fact(attrs='', body='390', eid='f1', acc='decimals="-6"'):
    """One fact. `acc` is the accuracy statement, separable because several
    cases below are precisely about it being wrong, absent or doubled."""
    return (f'<ix:nonFraction id="{eid}" name="us-gaap:A" contextRef="c1" '
            f'unitRef="u1" scale="6" {acc} {attrs}>{body}'
            f'</ix:nonFraction>')


#: `ixt:fixed-zero` returns 0 for ANY input, so it is the transform that turns
#: "no content at all" into a clean, reconcilable number. Every empty-content
#: attack below uses it for exactly that reason.
ZERO = 'format="ixt:fixed-zero" '

_GRAPH = dict(inline_element_id='f1', concept='us-gaap:A', context_id='c1',
              unit_ref='u1', unit_name='iso4217:USD', is_divide='0',
              period_type='duration', start_date='2024-01-01',
              end_date='2024-07-01', dims=(), entity_cik='0000320193',
              concept_namespace='http://fasb.org/us-gaap/2023',
              graph_concept_qname='us-gaap:A')


def _bind(inner, raw_value='390,000,000', extra_units=''):
    return bind_graph_fact(_doc(inner, extra_units),
                           raw_value=raw_value, **_GRAPH)


def _why(inner, raw_value='390,000,000', extra_units=''):
    """The refusal reason, with the caller's path prefix removed so these
    assertions name the RULE rather than which door reached it."""
    bound, why = _bind(inner, raw_value, extra_units)
    assert bound is None, f'expected a refusal, got a binding: {why}'
    return why.replace('exact_id_', '')


# ---------------------------------------------------------------------------
# MUST-ALLOW — 99.799% of real facts, and the rule must not touch them
# ---------------------------------------------------------------------------

def test_a_plain_text_fact_binds():
    bound, why = _bind(_fact())
    assert bound is not None, why


def test_a_NESTED_fact_agreeing_on_every_property_binds():
    """31,373 real facts (1.358%) are shaped this way and NONE of them
    disagrees on anything. Refusing them would have been the expensive
    mistake — which is why this control is not optional."""
    bound, why = _bind(_fact(body=_fact(eid='n1')))
    assert bound is not None, why


def test_the_value_is_taken_UNSTRIPPED_for_the_transform_to_read():
    """Non-emptiness is judged after XML whitespace; the VALUE is not. A fact
    printing ` 390 ` still states 390, and deciding that is the transform's
    job, not this reader's."""
    bound, why = _bind(_fact(body=' 390 '))
    assert bound is not None, why


# ---------------------------------------------------------------------------
# MUST-REFUSE — one test per rule, each naming the rule it enforces
# ---------------------------------------------------------------------------

def test_a_MARKUP_CHILD_is_malformed_not_merely_unsupported():
    """The original defect: `<b>390</b>` renders as `390`, so the page-derived
    value reconciled perfectly. `malformed` is the truthful word — the Inline
    XBRL content model forbids this, so the markup is wrong. Calling it
    `unsupported` would say the filing is fine and we are just limited."""
    assert _why(_fact(body='<b>390</b>')) == 'malformed_fact_content_model'


@pytest.mark.parametrize('body,label', [
    ('', 'self-closed'),
    ('<!--nothing to see-->', 'comment only'),
    ('<?pi data?>', 'processing instruction only'),
], ids=lambda v: v if isinstance(v, str) and ' ' not in v else None)
def test_a_fact_with_NO_TEXT_CHILD_cannot_be_transformed_into_zero(body, label):
    """`ixt:fixed-zero` maps any input to 0, so an EMPTY fact reconciled
    against a graph 0. A comment or PI is a child node — filtering children to
    elements made these look childless, and `node.text or ''` then minted the
    empty text child the content model forbids."""
    assert _why(_fact(ZERO, body=body), raw_value='0') == \
        'malformed_fact_content_model'


def test_a_WHITESPACE_ONLY_leaf_is_ONE_text_node_and_is_NOT_refused_here():
    """MY OVER-CATCH, corrected. I first stripped the text before asking
    whether it existed, which made `<f>   </f>` "empty" and refused it. The
    content model counts CHILDREN, and three spaces are one text node exactly
    as `390` is. Whether spaces are a lawful INPUT belongs to the transform:
    `ixt:fixed-zero` accepts any string, so this may lawfully be zero.

    `<f/>` still refuses above — it has no text node at all — which is the
    distinction the strip destroyed."""
    bound, why = _bind(_fact(ZERO, body='   '), raw_value='0')
    assert bound is not None, why


def test_TEXT_BESIDE_a_comment_is_still_two_children():
    """`0<!--c-->junk` has two text nodes and a comment between them. The old
    reader saw one element-free node and returned `.text` — the `0` — while the
    filing plainly says something else."""
    assert _why(_fact(ZERO, body='0<!--c-->junk'), raw_value='0') == \
        'malformed_fact_content_model'


def test_a_TRUE_nil_fact_is_LAWFUL_but_states_no_value():
    """4,656 facts in the cache (0.202%) and every one is `true`. The filing is
    correct; it asserts the fact HAS no value. It therefore cannot supply the
    number a non-nil graph row claims, and the reason says exactly that instead
    of accusing the filer of malformed markup."""
    assert _why(_fact(ZERO + 'xsi:nil="true" ', body='', acc=''),
                raw_value='0') == 'nil_fact_has_no_value'


@pytest.mark.parametrize('lexical', ['TRUE', 'yes', '', 'True'])
def test_a_nil_claim_OUTSIDE_the_boolean_lexical_space_is_malformed(lexical):
    """`xsi:nil` is `xs:boolean`: exactly `true`/`false`/`1`/`0` after
    whitespace collapse. Treating anything else as false would silently read a
    misspelled nil claim as a real value."""
    assert _why(_fact(f'xsi:nil="{lexical}" ')) == 'malformed_nil'


@pytest.mark.parametrize('lexical', ['false', '0'])
def test_an_EXPLICIT_false_nil_is_a_normal_fact(lexical):
    """MUST-ALLOW twin of the rule above — without it the nil check could pass
    by refusing every fact that mentions nil at all."""
    bound, why = _bind(_fact(f'xsi:nil="{lexical}" '))
    assert bound is not None, why


@pytest.mark.parametrize('acc', ['decimals="-6"', 'precision="3"'])
def test_a_true_nil_fact_STATING_ACCURACY_is_MALFORMED_not_lawfully_empty(acc):
    """XBRL 2.1 §4.6.3 — a nil item asserts NO value, so it may bound no
    accuracy. My first version returned on `nil=true` before looking, so a
    self-contradicting fact was reported as a lawful empty one: a refusal that
    sounds like a fact about the filer's DATA when it is about their MARKUP."""
    assert _why(_fact(ZERO + 'xsi:nil="true" ', body='', acc=acc),
                raw_value='0') == 'malformed_decimals_or_precision'


@pytest.mark.parametrize('acc', ['decimals=" INF "', 'precision=" INF "',
                                 'decimals="INF "', 'decimals=" INF"'])
def test_a_PADDED_INF_is_MALFORMED_because_that_union_member_PRESERVES(acc):
    """XBRL 2.1 declares `decimalsType` as the union of `xs:integer` and a
    restriction of **`xs:string`** enumerated `INF`; `precisionType` the same
    over `xs:nonNegativeInteger`. `xs:string` PRESERVES whitespace — the very
    reason `sign` is excluded from `_COLLAPSED` — so ` INF ` is NOT the value
    `INF` and the filing is malformed.

    A schema validator agrees: `decimals=' INF '` INVALID, `decimals=' -3 '`
    VALID. `_COLLAPSED` collapsed the whole union, so the padded spelling
    arrived at `_accuracy_ok` as the exact string 'INF' and was accepted."""
    assert _why(_fact(acc=acc)) == 'malformed_decimals_or_precision'


@pytest.mark.parametrize('acc', ['decimals="INF"', 'precision="3"',
                                 'decimals=" -6 "', 'decimals="-6"',
                                 'precision=" 3 "'])
def test_the_INTEGER_member_still_collapses_and_exact_INF_still_binds(acc):
    """MUST-ALLOW twin. The integer member really does carry
    whiteSpace=collapse, so ` -6 ` is `-6`; and exact `INF` is the string
    member's own value. Without this the rule above could pass by refusing
    every accuracy statement."""
    bound, why = _bind(_fact(acc=acc))
    assert bound is not None, why


@pytest.mark.parametrize('acc', ['decimals=" INF "',
                                 'decimals=" -6 "'])
def test_NON_XML_whitespace_is_not_whitespace_at_all(acc):
    """U+00A0 is not one of XML's four space characters, so neither union
    member may strip it. Both spellings stay malformed — the collapse fix must
    not reach for Python's `.strip()`."""
    assert _why(_fact(acc=acc)) == 'malformed_decimals_or_precision'


def test_a_NESTED_true_nil_is_MALFORMED():
    """Inline XBRL 1.1 §10.1.1 — a true-nil nonFraction MUST NOT sit below a
    nonFraction ancestor; the outer fact would have a child supplying nothing.

    EVERY OTHER PROPERTY IS DELIBERATELY IDENTICAL — no format on either, same
    scale, same unitRef — so no second rule can produce this refusal. My first
    probe differed on format and got `nested_fact_disagrees`, which would have
    'passed' while proving nothing about nesting."""
    nested = ('<ix:nonFraction id="n1" name="us-gaap:A" contextRef="c1" '
              'unitRef="u1" scale="6" xsi:nil="true"></ix:nonFraction>')
    outer = (f'<ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
             f'unitRef="u1" scale="6" decimals="-6">{nested}'
             f'</ix:nonFraction>')
    assert _why(outer) == 'malformed_nested_nil'


# ---------------------------------------------------------------------------
# ACCURACY IS JUDGED AS TEXT — no conversion, so no length ceiling
# ---------------------------------------------------------------------------

def test_an_ARBITRARY_LENGTH_accuracy_integer_is_LAWFUL_and_prompt():
    """`xml_integer` CONVERTED, so CPython's 4,300-digit ceiling refused text
    the schema permits — our runtime's limit reported as the filer's error.
    Arelle's `integerPattern` owns the official grammar and never converts."""
    import time
    big = '9' * 200_000
    start = time.time()
    assert inline_html._accuracy_ok(big, None) is True
    assert inline_html._accuracy_ok(None, big) is True
    assert time.time() - start < 5, 'must complete promptly, not merely finish'


@pytest.mark.parametrize('value,lawful', [
    ('-000', True),      # every spelling of zero IS non-negative
    ('-0', True),
    ('+0', True),
    ('0' * 50_000, True),
    ('-5', False),       # ...only a negative with a nonzero digit is not
    ('-' + '0' * 999 + '1', False),
])
def test_precision_NON_NEGATIVITY_is_decided_WITHOUT_converting(value, lawful):
    """`xs:nonNegativeInteger`, settled by sign plus the presence of a nonzero
    digit. Converting to compare against 0 would reintroduce the ceiling the
    pattern exists to avoid."""
    assert inline_html._accuracy_ok(None, value) is lawful


@pytest.mark.parametrize('bad', ['1_0', '١', '', ' ', '6.9', '1e3', 'inf'])
def test_accuracy_text_OUTSIDE_the_official_grammar_is_refused(bad):
    """Python's own int() accepts `1_0` and Arabic-Indic digits; XML Schema
    does not. `INF` is a union member and is case-sensitive."""
    assert inline_html._accuracy_ok(bad, None) is False


# ---------------------------------------------------------------------------
# ...AND THROUGH THE PUBLIC DOOR, because a private table only proves the
# helper. These prove the CALLER neither bypasses nor alters it.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('acc', ['decimals="{}"', 'precision="{}"'],
                         ids=['decimals', 'precision'])
def test_an_ARBITRARY_LENGTH_accuracy_BINDS_through_the_public_door(acc):
    """The whole reason for borrowing Arelle's pattern: 200,000 digits are
    lawful schema text, and converting them is our runtime's problem, not the
    filer's."""
    bound, why = _bind(_fact(acc=acc.format('9' * 200_000)))
    assert bound is not None, why


@pytest.mark.parametrize('acc,label', [
    ('decimals="1_0"', 'python-only underscore'),
    ('decimals="١"', 'Arabic-Indic digit'),
    ('precision="-5"', 'negative precision'),
    ('decimals="6.9"', 'not an integer'),
])
def test_accuracy_outside_the_grammar_REFUSES_through_the_public_door(acc,
                                                                      label):
    assert _why(_fact(acc=acc)) == 'malformed_decimals_or_precision', label


def test_the_TWO_accuracy_rules_are_SEPARATE_and_each_catches_its_own():
    """The grammar rule and the non-negativity rule are distinct, and the
    mutations below rely on that: `1_0` is refused by the grammar alone and
    `-5` by non-negativity alone, so neither can stand in for the other."""
    assert inline_html._accuracy_ok('1_0', None) is False      # grammar
    assert inline_html._accuracy_ok(None, '1_0') is False      # grammar
    assert inline_html._accuracy_ok('-5', None) is True        # lawful decimals
    assert inline_html._accuracy_ok(None, '-5') is False       # non-negativity


def test_NEITHER_decimals_nor_precision_is_refused():
    """XBRL 2.1 §4.6.3: a non-nil numeric fact states exactly one. With
    neither, nothing bounds how much of the number is asserted."""
    assert _why(_fact().replace(' decimals="-6"', '')) == \
        'malformed_decimals_or_precision'


def test_BOTH_decimals_and_precision_is_refused():
    assert _why(_fact('precision="3" ')) == 'malformed_decimals_or_precision'


def test_precision_accepts_INF_and_a_nonnegative_integer():
    """MUST-ALLOW twin: the accuracy rule must not become "decimals only"."""
    for attrs in ('precision="INF" ', 'precision="3" '):
        bound, why = _bind(_fact(attrs.replace('', '')).replace(
            ' decimals="-6"', '') if 'precision' in attrs else _fact())
        assert bound is not None, f'{attrs}: {why}'


# ---------------------------------------------------------------------------
# A NESTED FACT MUST AGREE — all three properties, each proved alone
# ---------------------------------------------------------------------------

def test_a_nested_fact_with_a_different_FORMAT_is_refused():
    """Compared as an EXPANDED name, because a prefix is only an alias. Two
    registries can both spell a transform `numdotdecimal` and mean different
    grammars."""
    assert _why(_fact('format="ixt:num-dot-decimal" ',
                      body=_fact('format="other:num-dot-decimal" ',
                                 eid='n1'))) == 'nested_fact_disagrees'


def test_a_nested_fact_with_a_different_SCALE_is_refused():
    """The nested fact contributes the number; a different power of ten makes
    it a different number."""
    assert _why(_fact(body=_fact(eid='n1').replace('scale="6"', 'scale="3"'))) \
        == 'nested_fact_disagrees'


def test_a_nested_fact_with_a_different_UNIT_REF_is_refused():
    assert _why(_fact(body=_fact(eid='n1').replace('unitRef="u1"',
                                                   'unitRef="u2"')),
                extra_units=SHARES) == 'nested_fact_disagrees'


def test_the_SAME_scale_written_differently_still_AGREES():
    """MUST-ALLOW twin of the scale rule: `06` and `6` are one scale, so the
    comparison is on the PARSED integer. A string comparison would refuse a
    lawful filing for its spelling."""
    bound, why = _bind(_fact(body=_fact(eid='n1').replace('scale="6"',
                                                          'scale="06"')))
    assert bound is not None, why


# ---------------------------------------------------------------------------
# THE TWO STRINGS MUST NOT BE SWAPPED BACK
# ---------------------------------------------------------------------------

def test_reconciliation_uses_the_FACT_and_evidence_keeps_the_PAGE():
    """The architectural point, asserted rather than trusted to a comment: the
    two strings differ here, the fact's own content is what reconciles, and the
    rendered text survives untouched for quoting."""
    inner = _fact(body='390') + '<span> and some other prose</span>'
    bound, why = _bind(inner)
    assert bound is not None, why
    assert bound['evidence']['value_input'] == '390'
    assert bound['evidence']['displayed'] == '390'
    assert 'other prose' in bound['evidence']['block']


# ---------------------------------------------------------------------------
# ISOLATED MUTATIONS — each rule proved to bite ALONE
# ---------------------------------------------------------------------------

#: rule -> (exact source anchor, its removal, the shape that must return, the
#: graph value that shape reconciles against).
#:
#: EACH SHAPE IS CHOSEN SO NO OTHER RULE CAN CATCH IT. My first version proved
#: the child-count rule with a comment-ONLY fact, which the separate text-node
#: rule also refuses — so that mutation stayed red for the wrong reason and the
#: "proof" showed nothing. `0<!--c-->junk` is the honest probe: with comments
#: filtered away it looks like a lawful leaf holding `0`, so ONLY counting real
#: child nodes can reject it.
MUTANTS = {
    # Reading nil at all is the rule. Blind to it, a `true` nil fact carrying
    # accuracy and content reads as an ordinary lawful fact and BINDS — which
    # is precisely the value the filing says it does not have.
    'nil check': ('            nil = _nil_true(node)', '            nil = False',
                  lambda: _fact('xsi:nil="true" ', body='390'), '390,000,000'),
    'every child node counts': (
        '        kids = list(node)',
        '        kids = [c for c in node if isinstance(c.tag, str)]',
        lambda: _fact(ZERO, body='0<!--c-->junk'), '0'),
    # Restores the ORIGINAL defect verbatim — `or ''` minting an empty text
    # child for an element that has none — rather than merely skipping a check,
    # which would leave `None` travelling on and fail for an unrelated reason.
    'a text node must exist': (
        '            if node.text is None:\n'
        '                return None, MALFORMED_FACT_CONTENT\n'
        '            return node.text, None',
        "            return node.text or '', None",
        lambda: _fact(ZERO, body=''), '0'),
    'accuracy': ('        if not _accuracy_ok(dec, prec):', '        if False:',
                 lambda: _fact(acc=''), '390,000,000'),
    # Each pins the EXACT truthful outcome coming back, not merely "something
    # stopped attaching" — the shapes below violate no second rule, so only the
    # removed one can be what changed.
    'no accuracy on a nil fact': (
        '            if dec is not None or prec is not None:\n'
        '                return None, MALFORMED_FACT_ACCURACY',
        '            pass',
        lambda: _fact(ZERO + 'xsi:nil="true" ', body='', acc='decimals="-6"'),
        '0'),
    'no nil below a nonFraction': (
        '            if depth:\n'
        '                return None, MALFORMED_NESTED_NIL',
        '            pass',
        lambda: ('<ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
                 'unitRef="u1" scale="6" decimals="-6">'
                 '<ix:nonFraction id="n1" name="us-gaap:A" contextRef="c1" '
                 'unitRef="u1" scale="6" xsi:nil="true"></ix:nonFraction>'
                 '</ix:nonFraction>'),
        '390,000,000'),
    # THE TWO ACCURACY RULES, SEPARATELY. The broad "skip all accuracy"
    # mutation above proves only that SOMETHING checks accuracy; these prove
    # WHICH rule catches which text, and the cross-checks below prove neither
    # mutant can cover for the other.
    'accuracy lexical grammar': (
        '    if not _integer_pattern().fullmatch(collapsed):\n'
        '        return False',
        '    pass',
        lambda: _fact(acc='decimals="1_0"'), '390,000,000'),
    'precision non-negativity': (
        "    return not (raw.startswith('-') "
        "and any(c in '123456789' for c in raw))",
        '    return True',
        lambda: _fact(acc='precision="-5"'), '390,000,000'),
}

#: rule -> the shape it must NOT rescue. Removing the grammar must not make a
#: negative precision lawful, and removing non-negativity must not make
#: `1_0` a number. Without this each mutant only shows "a rule bit".
MUTANT_MUST_STILL_REFUSE = {
    'accuracy lexical grammar': lambda: _fact(acc='precision="-5"'),
    'precision non-negativity': lambda: _fact(acc='decimals="1_0"'),
}

#: The two nil mutations above cannot make their shape BIND — a nil fact still
#: has no value to reconcile. What must change is the REASON, so they are
#: checked by outcome rather than by attachment.
REASON_ONLY = {'no accuracy on a nil fact': 'nil_fact_has_no_value',
               'no nil below a nonFraction': 'nil_fact_has_no_value'}


@pytest.fixture(scope='module')
def source():
    return open(inline_html.__file__, encoding='utf-8').read()


@pytest.mark.parametrize('rule', sorted(MUTANTS))
def test_EACH_rule_is_load_bearing_ALONE(rule, source, tmp_path):
    """Remove ONE rule in a scratch copy and require its own shape to come
    back — while a lawful fact keeps binding, so a mutation that simply broke
    everything could not be mistaken for a rule that bites."""
    import importlib.util
    import sys as _sys

    old, new, shape, raw = MUTANTS[rule]
    assert source.count(old) == 1, f'{rule}: anchor appears {source.count(old)}x'
    path = tmp_path / f'mutant_{rule.replace(" ", "_")}.py'
    path.write_text(source.replace(old, new), encoding='utf-8')
    spec = importlib.util.spec_from_file_location('ih_value_mutant', str(path))
    mutant = importlib.util.module_from_spec(spec)
    saved = list(_sys.path)
    try:
        spec.loader.exec_module(mutant)
    finally:
        _sys.path[:] = saved

    bound, why_m = mutant.bind_graph_fact(_doc(shape()), raw_value=raw,
                                          **_GRAPH)
    if rule in REASON_ONLY:
        # A nil fact never binds, so attachment cannot be the signal. What the
        # rule OWNS is the truthful reason, and that is what must change.
        assert why_m.replace('exact_id_', '') == REASON_ONLY[rule], (
            f'{rule}: removing it must change the REASON to '
            f'{REASON_ONLY[rule]!r}, got {why_m!r}')
    else:
        assert bound is not None, \
            f'{rule}: removing it must let its own shape back in'

    # ...AND IT MUST NOT RESCUE THE OTHER RULE'S SHAPE. Without this, two
    # mutations could each "bite" while actually removing the same guard.
    other = MUTANT_MUST_STILL_REFUSE.get(rule)
    if other is not None:
        still, why_o = mutant.bind_graph_fact(_doc(other()),
                                              raw_value='390,000,000', **_GRAPH)
        assert still is None, \
            f'{rule}: its mutation also rescued another rule\'s shape'
        assert why_o.replace('exact_id_', '') == \
            'malformed_decimals_or_precision', why_o

    lawful, why_l = mutant.bind_graph_fact(_doc(_fact()),
                                           raw_value='390,000,000', **_GRAPH)
    assert lawful is not None, f'{rule}: the mutation broke a lawful fact ({why_l})'


def test_EU096_an_absent_scale_means_ten_to_the_zero():
    """Inline XBRL 1.1: a nonFraction with NO scale attribute is unscaled —
    the absent-scale default is 10^0 — so displayed 390 binds raw 390; any
    other default would silently multiply every unscaled fact in the
    corpus."""
    inner = ('<ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
             'unitRef="u1" decimals="0" '
             'format="ixt:num-dot-decimal">390</ix:nonFraction>')
    bound, why = _bind(inner, raw_value='390')
    assert bound is not None, why


def test_EU112_a_negative_no_format_value_never_binds():
    """Inline XBRL 1.1 section 10.1.2: a no-format fact states the number
    itself and it MUST be non-negative — the pattern admits a sign, so the
    zero bound is load-bearing: -0.5 refuses while the positive control
    binds."""
    neg = ('<ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
           'unitRef="u1" decimals="0">-0.5</ix:nonFraction>')
    bound, why = _bind(neg, raw_value='-0.5')
    assert bound is None
    pos = ('<ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
           'unitRef="u1" decimals="0">390</ix:nonFraction>')
    bound2, why2 = _bind(pos, raw_value='390')
    assert bound2 is not None, why2


def test_EU168_a_nested_pair_that_both_omit_scale_agrees_at_ten_to_the_zero():
    """The absent-scale law (10^0) applies to the nested AGREEMENT test as
    well: an outer and an inner nonFraction that BOTH omit scale agree and
    bind — a drifted default would refuse this lawful pair as a
    disagreement."""
    inner = ('<ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
             'unitRef="u1" decimals="0" format="ixt:num-dot-decimal">'
             '<ix:nonFraction id="f2" name="us-gaap:A" contextRef="c1" '
             'unitRef="u1" decimals="0" format="ixt:num-dot-decimal">390'
             '</ix:nonFraction></ix:nonFraction>')
    bound, why = _bind(inner, raw_value='390')
    assert bound is not None, why


_NDD_ID = ('http://www.xbrl.org/inlineXBRL/transformation/2020-02-12',
           'num-dot-decimal')


def test_EU182_an_empty_display_never_becomes_a_value():
    """FAIL-CLOSED at the public function: nothing printed is not a value —
    an empty displayed string refuses under a real transform grammar (a
    fabricating default would mint a number out of nothing), while the
    same grammar reads a real one."""
    assert printed_value('', _NDD_ID, '') is None
    assert printed_value('390', _NDD_ID, '') == Decimal('390')


def test_EU183_an_absent_sign_is_the_positive_case():
    """Inline XBRL 1.1: @sign's only lawful value is '-' (the negation
    flag), so an ABSENT sign — which callers may hand through as None —
    means not negated, never negative."""
    assert printed_value('390', _NDD_ID, None) == Decimal('390')
    assert printed_value('390', _NDD_ID, '-') == Decimal('-390')


def test_EU189_a_zero_width_space_is_not_a_word_separator_in_the_walk():
    """EU-189 (#827) FIX-TO-STANDARD — the whitespace family's member inside
    the visible walk itself. U+200B has no width and is NOT a space character
    (Unicode 17.0 core spec §23.2.1); UAX #14 Table 1 gives it line-break
    class ZW, a break OPPORTUNITY and never a visible space; CSS Text 3 §3
    lists the collapsible white space as spaces, tabs and segment breaks,
    none of which ZWSP is. The walk used to substitute U+0020 for it, so
    `Total<ZWSP>revenue` entered the representation as TWO words that no
    filing displays. Measured before the change: ZERO U+200B in the frozen
    1,769-file corpus, so the reading moves no real filing.

    The suite's own `_doc` builder is used, and the assertion reads the
    representation through the module's public `prepare` — the walk's only
    published output — because this suite's other doors (`printed_value`,
    `bind_graph_fact`) report the FACT's value, which the walk never touches.

    THE CONTROL WAS WRONG AND IS REPLACED (SEQ 853). It read "two ELEMENTS,
    two tokens", which the cited standard disproves: CSS Text 3 §3 processes a
    block's content as a single inline box — "inline box boundaries are
    ignored" — so `<span>Total</span><span>revenue</span>`, with no source
    whitespace at all, renders Totalrevenue. The old control passed only
    because the token join fabricated a space at every element boundary. The
    honest control is the TWIN: identical markup, whitespace present or
    absent, which isolates the one thing that actually decides the answer.
    """
    text = inline_html.prepare(_doc('Total​revenue</p><p>'
                                    '<span>Costs</span><span>ales</span>'
                                    '</p><p>'
                                    '<span>Gross</span> <span>margin</span>'))['text']
    assert 'Totalrevenue' in text        # zero width: ONE word, as displayed
    # THE TWINS: the element boundary contributes nothing either way, so the
    # SOURCE whitespace is the only difference between these two lines. They
    # use DISTINCT words so neither assertion can be satisfied by the other's
    # output.
    assert 'Costsales' in text           # no source whitespace -> no space
    assert 'Gross margin' in text        # one source space -> one space

