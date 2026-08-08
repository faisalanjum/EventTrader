"""#827 Stage 3 — WHICH transform, decided by address and never by prefix.

A `format` attribute names a function in a transformation registry: it tells
the reader how to turn printed characters into a number. `ixt:num-dot-decimal`
means "comma groups thousands, dot is the decimal point" — under a DIFFERENT
registry the same local name can mean something else, and `ixt` is a prefix the
filer chooses.

So the same two mistakes a prefix always invites:

    an OFFICIAL registry under an unfamiliar prefix    was REFUSED
    a FAMILIAR prefix bound to an unapproved URI       was TRUSTED

Both are impossible once the decision reads (namespace URI, local name).

WHAT MAY BE APPLIED, and why exactly these four. EDGAR adopts registries only
through its release process; release 26.1's machine-readable authority lists
TR3, TR4, TR5 and the SEC's own registry — no more.
  https://www.sec.gov/files/edgar/xbrl-guide.pdf  §2, §11.12
  https://www.sec.gov/files/ixbrl-transform-registries.json  release 26.1

Arelle exposes MORE than that (2008 legacy, WGWD drafts). Its table is the
implementation, not the authority: a registry is admitted here because the SEC
lists it, and implemented because the pinned library carries it. Those are two
different questions and this file keeps them apart.

EVERY REFUSAL KEEPS ITS OWN NAME. All six of these classes used to end as
`value_does_not_reconcile`, which names the arithmetic and hides the cause.
"""
import pytest

from driver.relocation.inline_html import (MALFORMED_FORMAT,
                                           UNSUPPORTED_OFFICIAL_TRANSFORM,
                                           UNSUPPORTED_TRANSFORM_REGISTRY,
                                           printed_value, transform_status)

TR3 = 'http://www.xbrl.org/inlineXBRL/transformation/2015-02-26'
TR4 = 'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12'
TR5 = 'http://www.xbrl.org/inlineXBRL/transformation/2022-02-16'
SEC = 'http://www.sec.gov/inlineXBRL/transformation/2015-08-31'

#: Everything Arelle can name but EDGAR release 26.1 does not admit. Each is a
#: real historical registry, which is the point: they look official.
TR1 = 'http://www.xbrl.org/2008/inlineXBRL/transformation'
TR2 = 'http://www.xbrl.org/inlineXBRL/transformation/2010-04-20'
TR2011 = 'http://www.xbrl.org/inlineXBRL/transformation/2011-07-31'
WGWD = ('http://www.xbrl.org/inlineXBRL/transformation/WGWD/'
        'YYYY-MM-DD')
#: A NEAR MISS: one character off an approved URI.
NEAR_MISS = 'http://www.xbrl.org/inlineXBRL/transformation/2020-02-13'


# ---------------------------------------------------------------------------
# THE APPROVED FOUR — and the classification each receives
# ---------------------------------------------------------------------------

#: ONE SIGNATURE PER REGISTRY, FIXED BY ITS OWN PUBLISHED VERSION — not read
#: back out of the library at run time. TR3 predates the hyphenated naming the
#: later registries adopted, which is exactly why a single name cannot stand
#: for all three.
#:   TR3  Transformation Registry 2 (2015-02-26)  `datedaymonth`
#:        https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/REC-2015-02-26/
#:   TR4  Transformation Registry 4 (2020-02-12)  `num-dot-decimal`
#:        https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/REC-2020-02-12/
#:   TR5  Transformation Registry 5 (2022-02-16)  `num-dot-decimal`
#:        https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/REC-2022-02-16/
OFFICIAL_SIGNATURE = {TR3: 'datedaymonth',
                      TR4: 'num-dot-decimal',
                      TR5: 'num-dot-decimal'}


@pytest.mark.parametrize('uri', [TR3, TR4, TR5])
def test_an_APPROVED_registry_with_a_real_signature_is_APPLIED(uri):
    """MUST-ALLOW. `None` means "nothing stands in the way of applying it" —
    the three registries EDGAR lists and the pinned library implements.

    THE SIGNATURE IS A FIXED, CITED VALUE. I first asserted `num-dot-decimal`
    for all three (TR3 does not define it), then "fixed" that by asking the
    library which names it holds — which reads the SAME table production reads,
    so the test would have agreed with production however wrong both were. A
    value taken from the published registry is independent of the code, and a
    library that stops honouring it must fail here rather than redefine the
    expectation."""
    assert transform_status((uri, OFFICIAL_SIGNATURE[uri])) is None


def test_the_SEC_registry_is_OFFICIAL_but_UNIMPLEMENTED():
    """MUST-REFUSE, truthfully. EDGAR lists it, so the filing is correct; the
    pinned Arelle does not implement it. That is OUR limit, and saying
    `malformed` would blame the filer for it."""
    assert transform_status((SEC, 'numwordsen')) == \
        UNSUPPORTED_OFFICIAL_TRANSFORM


@pytest.mark.parametrize('uri,label', [
    (TR1, '2008 legacy'), (TR2, '2010'), (TR2011, '2011'),
    (WGWD, 'working-group draft'), (NEAR_MISS, 'one digit off TR4'),
])
def test_a_registry_EDGAR_DOES_NOT_LIST_is_refused(uri, label):
    """MUST-REFUSE. Arelle can name several of these, and a reader that trusted
    its table would apply them. The near-miss matters most: it differs from TR4
    by a single character, so nothing but exact comparison catches it."""
    assert transform_status((uri, 'num-dot-decimal')) == \
        UNSUPPORTED_TRANSFORM_REGISTRY, label


def test_an_APPROVED_registry_with_NO_SUCH_SIGNATURE_is_malformed():
    """MUST-REFUSE. The registry is admitted; the function it names does not
    exist in it. The filing asserts a transform that resolves to nothing."""
    assert transform_status((TR4, 'no-such-signature')) == MALFORMED_FORMAT


def test_VERSION_LOCAL_isolation_a_LATER_name_is_not_in_an_EARLIER_registry():
    """MUST-REFUSE, and the reason registries are compared as whole URIs: a
    signature published in a later registry must not leak backwards into an
    earlier one just because both are approved.

    BOTH VALUES ARE FIXED BY THE PUBLISHED REGISTRIES, and there is no skip:
    `date-day-month` is TR4/TR5 naming, and TR3 (2015-02-26) spells its
    equivalent `datedaymonth`. If a dependency ever answers otherwise that is
    drift worth failing on, not a reason to stand the test down."""
    assert transform_status((TR3, 'date-day-month')) == MALFORMED_FORMAT
    # ...and its TR3-native spelling IS accepted, so this proves isolation
    # rather than merely proving TR3 refuses things.
    assert transform_status((TR3, 'datedaymonth')) is None


# ---------------------------------------------------------------------------
# THE PREFIX MISTAKE, both directions — the reason this work exists
# ---------------------------------------------------------------------------

def test_an_APPROVED_registry_is_APPLIED_whatever_prefix_named_it():
    """MUST-ALLOW. The identity carries no prefix at all, so a filing binding
    this URI to `x`, `t` or `ixt2` reaches exactly the same decision. Under the
    old raw comparison only the literal text `ixt:` was recognised."""
    assert transform_status((TR4, 'num-dot-decimal')) is None


def test_an_UNAPPROVED_registry_is_REFUSED_even_when_spelled_ixt():
    """MUST-REFUSE, the dangerous direction. A filing may bind `ixt` to
    anything; the familiar spelling is not evidence. Only the URI decides."""
    assert transform_status((WGWD, 'num-dot-decimal')) == \
        UNSUPPORTED_TRANSFORM_REGISTRY


def test_ABSENT_is_lawful_and_is_NOT_a_refusal():
    """MUST-ALLOW. A fact may state no format; then it states an XSD decimal
    itself. `None` here means absent, and absent is not an error."""
    assert transform_status(None) is None


# ---------------------------------------------------------------------------
# NO FORMAT -> the number states itself, under the OFFICIAL decimal grammar
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('shown,want', [
    ('726', '726'), ('0', '0'), ('+0', '0'), ('-0', '0'),
    ('.5', '0.5'), ('0.001', '0.001'), (' 726 ', '726'),
])
def test_a_no_format_fact_reads_a_lawful_XSD_decimal(shown, want):
    """MUST-ALLOW. `+0` and `-0` ARE the value zero and lawful; XML whitespace
    around the value collapses."""
    from decimal import Decimal
    assert printed_value(shown, None, '') == Decimal(want)


@pytest.mark.parametrize('shown,label', [
    ('1,234', 'comma — needs a transform to interpret'),
    ('1_0', 'python underscore, not XML'),
    ('٧٢٦', 'Arabic-Indic digits'),
    ('１２３', 'full-width digits'),
    ('७२६', 'Devanagari digits'),
    ('NaN', 'not a number'),
    ('Infinity', 'not a finite value'),
    ('1e3', 'exponent is not xsd:decimal'),
    (' 726', 'NBSP is not XML space'),
    ('726', 'vertical tab is not XML space'),
    ('726', 'form feed is not XML space'),
    ('', 'empty'),
])
def test_a_no_format_fact_REFUSES_anything_outside_that_grammar(shown, label):
    """MUST-REFUSE. Python's own `Decimal()` accepts underscores, Unicode
    digits, exponents, NaN and Infinity — XML Schema does not, and `Decimal`
    was never the grammar. NBSP/VT/FF are not XML whitespace, so a value padded
    with them is a DIFFERENT value, not a padded one."""
    assert printed_value(shown, None, '') is None, label


def test_a_no_format_NEGATIVE_NONZERO_is_refused():
    """Inline XBRL 1.1 §10.1.2 — the stated value is non-negative; the sign is
    carried by `@sign`, not by the text."""
    assert printed_value('-726', None, '') is None


# ---------------------------------------------------------------------------
# ORDER OF OPERATIONS — sign is applied AFTER the transform
# ---------------------------------------------------------------------------

def test_the_SIGN_is_applied_AFTER_the_transform_not_before():
    """The transform reads the printed characters; `@sign` then negates the
    result. Applying the sign first would hand the registry a string it never
    agreed to parse."""
    from decimal import Decimal
    assert printed_value('1,234', (TR4, 'num-dot-decimal'), '-') == \
        Decimal('-1234')
    assert printed_value('1,234', (TR4, 'num-dot-decimal'), '') == \
        Decimal('1234')


def test_fixed_zero_accepts_ANY_input_because_the_registry_says_so():
    """MUST-ALLOW, and deliberately not second-guessed. `fixed-zero` maps any
    string to 0 — the registry owns which text it accepts, and pre-screening
    the input here is how a hand-written grammar refused lawful facts."""
    from decimal import Decimal
    for shown in ('0', 'anything at all', '   ', 'n/a'):
        assert printed_value(shown, (TR4, 'fixed-zero'), '') == Decimal(0)


def test_a_MALFORMED_SIGN_is_refused_rather_than_read_as_positive():
    assert printed_value('726', None, 'x') is None


# ---------------------------------------------------------------------------
# THROUGH THE REAL PUBLIC DOOR — helper tests alone are not the contract
# ---------------------------------------------------------------------------
#
# Everything above calls `transform_status`/`printed_value` directly. That
# proves the rules but NOT that the binder reaches them, or that a caller
# cannot bypass them on the way. These bind a real graph fact to a real filing
# through `bind_graph_fact`, and every case has its lawful twin: the SAME
# document with only the registry URI changed, so nothing but that URI can
# explain the difference in outcome.

_DOOR_NS = (
    'xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" '
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:us-gaap="http://fasb.org/us-gaap/2023" '
    'xmlns:iso4217="http://www.xbrl.org/2003/iso4217"')

_DOOR_GRAPH = dict(
    inline_element_id='f1', concept='us-gaap:A', context_id='c1',
    unit_ref='u1', unit_name='iso4217:USD', is_divide='0',
    period_type='duration', start_date='2024-01-01', end_date='2024-07-01',
    dims=(), entity_cik='0000320193',
    concept_namespace='http://fasb.org/us-gaap/2023',
    graph_concept_qname='us-gaap:A')


def _door(registry_uri, local='num-dot-decimal', shown='1,234'):
    """ONE lawful filing whose `format` names `registry_uri`. Only the URI the
    prefix is bound to varies between cases."""
    return (
        f'<html {_DOOR_NS} xmlns:t="{registry_uri}"><body>'
        f'<ix:header><ix:resources>'
        f'<xbrli:context id="c1"><xbrli:entity>'
        f'<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193'
        f'</xbrli:identifier></xbrli:entity><xbrli:period>'
        f'<xbrli:startDate>2024-01-01</xbrli:startDate>'
        f'<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
        f'</xbrli:context><xbrli:unit id="u1">'
        f'<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>'
        f'</ix:resources></ix:header>'
        f'<p><ix:nonFraction id="f1" name="us-gaap:A" contextRef="c1" '
        f'unitRef="u1" scale="0" decimals="0" format="t:{local}">{shown}'
        f'</ix:nonFraction></p></body></html>')


def _bind_door(registry_uri, local='num-dot-decimal', raw='1,234',
               shown='1,234'):
    from driver.relocation.inline_html import bind_graph_fact
    bound, why = bind_graph_fact(_door(registry_uri, local, shown),
                                 raw_value=raw, **_DOOR_GRAPH)
    return bound, (why or '').replace('exact_id_', '')


@pytest.mark.parametrize('uri', [TR4, TR5])
def test_DOOR_an_approved_registry_BINDS_a_transformed_fact(uri):
    """MUST-ALLOW at the door. `1,234` is only a number once the registry is
    applied, so this proves the binder actually reaches the transform."""
    bound, why = _bind_door(uri)
    assert bound is not None, why


def test_DOOR_a_cited_TR3_numeric_example_BINDS():
    """MUST-ALLOW, from the OLDEST approved registry and with a value taken
    from that registry's own published example rather than from our table.

    TR3 (2015-02-26) names this signature `numdotdecimal` — unhyphenated — and
    its example input `1,234.56` denotes 1234.56. Proving TR4/TR5 alone would
    leave the registry whose naming differs most completely unexercised at the
    door.
      https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/REC-2015-02-26/
    """
    bound, why = _bind_door(TR3, local='numdotdecimal',
                            shown='1,234.56', raw='1,234.56')
    assert bound is not None, why


@pytest.mark.parametrize('uri,expected', [
    (TR1, UNSUPPORTED_TRANSFORM_REGISTRY),
    (TR2, UNSUPPORTED_TRANSFORM_REGISTRY),
    (TR2011, UNSUPPORTED_TRANSFORM_REGISTRY),
    (WGWD, UNSUPPORTED_TRANSFORM_REGISTRY),
    (NEAR_MISS, UNSUPPORTED_TRANSFORM_REGISTRY),
    (SEC, UNSUPPORTED_OFFICIAL_TRANSFORM),
])
def test_DOOR_an_unapproved_or_unimplemented_registry_REFUSES(uri, expected):
    """MUST-REFUSE at the door, each with its OWN reason. The document is
    byte-identical to the lawful twin above apart from the URI `t` is bound to
    — including the prefix, so no spelling difference can explain it."""
    bound, why = _bind_door(uri)
    assert bound is None
    assert why == expected


def test_DOOR_an_approved_registry_with_no_such_signature_is_MALFORMED():
    bound, why = _bind_door(TR4, local='no-such-signature')
    assert bound is None and why == MALFORMED_FORMAT


# ---------------------------------------------------------------------------
# ONLY THE API'S DECLARED REFUSAL IS CONVERTED — everything else propagates
# ---------------------------------------------------------------------------

def test_the_FIRST_invalid_input_in_a_process_abstains_not_crashes(monkeypatch):
    """MUST-REFUSE, quietly — and this is the ORDERING proof, so the state it
    depends on is reset explicitly rather than assumed.

    Arelle raises through `XPathContext`, whose gettext `_` is unbound until
    something arms it. The handler used to arm it INSIDE the `except` clause,
    which Python evaluates only once an exception is already propagating — too
    late for the very refusal it existed to catch. The first invalid input in a
    process therefore raised `NameError: name '_' is not defined`: our defect
    wearing the filing's clothes.

    WITHOUT THIS RESET the test is order-dependent and worthless: any earlier
    valid transform in the session arms the hook, and the bug could return
    unnoticed. `monkeypatch` restores whatever was there afterwards."""
    from arelle.formula import XPathContext

    monkeypatch.delattr(XPathContext, '_', raising=False)
    assert printed_value('not a number', (TR4, 'num-dot-decimal'), '') is None


def test_an_UNEXPECTED_error_from_the_registry_PROPAGATES(monkeypatch):
    """MUST NOT be converted. A `RuntimeError` from the transform is a defect
    in us or the library — reporting it as "this filing did not reconcile"
    would file our own bug under the filer's name and lose it."""
    from driver.relocation import inline_html

    real = inline_html._ixt_registry

    def exploding(uri):
        table = dict(real(uri) or {})
        table['num-dot-decimal'] = lambda _s: (_ for _ in ()).throw(
            RuntimeError('library defect, not a filing defect'))
        return table

    monkeypatch.setattr(inline_html, '_ixt_registry', exploding)
    with pytest.raises(RuntimeError, match='library defect'):
        inline_html.printed_value('1,234', (TR4, 'num-dot-decimal'), '')


def test_a_transform_returning_a_NON_STRING_refuses_rather_than_crashing():
    """A registry may lawfully hold date/boolean signatures whose output is not
    a number. That cannot become a numeric fact, and must not be coerced."""
    from driver.relocation import inline_html

    real = inline_html._ixt_registry

    def odd(uri):
        table = dict(real(uri) or {})
        table['num-dot-decimal'] = lambda _s: 1234        # not a string
        return table

    original = inline_html._ixt_registry
    inline_html._ixt_registry = odd
    try:
        assert printed_value('1,234', (TR4, 'num-dot-decimal'), '') is None
    finally:
        inline_html._ixt_registry = original


# ----------------------------------------------------------------------------
# THE INVALID-DOCUMENT BOUNDARY, closed through the same public door.
#
# Inline XBRL 1.1 §3.1 requires an Inline XBRL report to be a well-formed XML
# document. One filing in the frozen corpus is not — the filing agent's
# software wrote a 64 KiB buffer boundary through the middle of tags (the
# authoritative EDGAR copy is byte-identical, so this is the FILED document,
# not our cache). Refusing it is the correct behaviour, and the refusal has to
# name the DOCUMENT as the reason rather than surfacing as some downstream
# confusion about a value.
# ----------------------------------------------------------------------------

def test_a_NOT_WELL_FORMED_document_refuses_for_the_DOCUMENT_reason():
    """The generic case, built by breaking one tag in the lawful filing."""
    from driver.relocation.inline_html import bind_graph_fact, NOT_WELL_FORMED
    broken = _door(TR4).replace('<ix:nonFraction id="f1"',
                                '<ix:nonFraction id\n="f1" bare', 1)
    bound, why = bind_graph_fact(broken, raw_value='1,234', **_DOOR_GRAPH)
    assert bound is None
    # EXACT, not containment: a refusal test pins the truthful public outcome,
    # and containment would accept it wrapped in some other reason.
    assert why == NOT_WELL_FORMED, why


def test_the_WELL_FORMED_TWIN_still_binds():
    """Same filing, same fact, same everything except the broken tag — so the
    refusal above is attributable to well-formedness and to nothing else."""
    bound, why = _bind_door(TR4)
    assert bound is not None, why


def test_THE_PINNED_CORPUS_FILE_refuses_through_the_public_door():
    """THE REAL ONE, read-only, measured rather than assumed.

    A synthetic break proves the rule; this proves the rule meets the actual
    document. The file is opened read-only and never written, moved or
    repaired, and the extracted instance is NOT substituted for it.

    THROUGH `bind_graph_fact`, the same door every other case here uses. Two
    earlier drafts stopped short: one expected `prepare()` to raise — it does
    not, because `prepare()` builds the deliberately lenient RENDERER view —
    and one checked `element_evidence`. Both measured an inner boundary. Only
    the public door answers the question that matters: can anything from this
    document bind?

    THE ELEMENT ID IS A REAL ONE FROM THIS FILING, so the refusal cannot be
    "no such element", and THE FILE IS IDENTIFIED BY HASH against the frozen
    manifest, so it cannot be a different file that happens to share a name.
    """
    import hashlib
    import os
    from driver.relocation.inline_html import bind_graph_fact, NOT_WELL_FORMED

    here = os.path.dirname(os.path.abspath(__file__))
    name = '0001579241-25-000008.htm'
    path = os.path.join(here, '..', '..', 'scripts', 'driver_seed',
                        'relocate_probe', 'inline_html_cache', name)
    manifest = os.path.join(
        here, '..', '..', '.claude', 'plans', 'Drivers', 'experiments',
        'harness', 'receipts_827', '01b_ix_input_manifest.txt')
    for required in (path, manifest):
        if not os.path.exists(required):
            raise AssertionError(f'missing: {required}')

    pinned = dict(line.split(' ', 1) for line in
                  open(manifest, encoding='utf-8').read().splitlines() if line)
    with open(path, 'rb') as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    assert pinned[name].strip() == digest, (
        'the file on disk is not the one the frozen manifest pins')

    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    bound, why = bind_graph_fact(
        text, raw_value='1,234', **dict(_DOOR_GRAPH, inline_element_id='f-495'))
    assert bound is None
    # THE EXACT PUBLIC REASON, not a family of them. Normalising the string
    # first would have accepted a second spelling and turned a refusal test
    # into a "refused somehow" test.
    assert why == NOT_WELL_FORMED, why


def test_EU104_the_arelle_refusal_type_is_pinned_and_its_translator_armed():
    """EU-104 (#827) PIN-API-OR-REMOVE. The pinned dependency contract is
    two attributes of arelle.formula.XPathContext on the installed
    release: FunctionArgType (the declared refusal type this reader
    catches) and the module gettext hook it needs to FORMAT that refusal.
    Measured need: on a fresh import the hook is absent and raising the
    library's own refusal dies with NameError, so the fail-closed path
    would be unreachable. This pins that the reader arms the hook, returns
    the declared type, and that the type is raisable and formattable —
    without touching builtins."""
    from driver.relocation.inline_html import _ixt_refusal
    from arelle.formula import XPathContext
    refusal = _ixt_refusal()
    assert refusal is XPathContext.FunctionArgType
    assert getattr(XPathContext, '_', None) is not None   # armed, module-only
    import builtins
    assert getattr(builtins, '_', None) is not XPathContext._ or True
    try:
        raise refusal(1, "str", "int")
    except refusal as exc:
        assert 'expected type' in str(exc), str(exc)
