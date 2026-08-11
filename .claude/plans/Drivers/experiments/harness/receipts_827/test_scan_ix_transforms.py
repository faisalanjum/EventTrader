"""#827 Stage 3 — synthetic controls for the transform scanner.

WHY THIS FILE EXISTS. The scanner about to read 4.3 GB of filings has exactly
one job: say what is there. Its predecessor matched the literal bytes
`<ix:nonfraction`, which is a PREFIX — an alias any document may bind to
anything — and then verified itself with three controls that compared its regex
against its own regex. It could not have detected the one error that mattered,
and no amount of corpus would have revealed it, because the corpus happens to
use `ix:` everywhere.

So the inputs here are tiny documents written to be awkward on purpose. Each
control comes in BOTH directions: the case the scanner must catch, and the
lawful twin it must NOT catch. A rule that fires on everything is as useless as
one that fires on nothing, and only the pair pins the boundary.

Nothing in this file imports production code, for the same reason the scanner
does not: a census that asks the product to grade itself cannot find a class
the product mishandles.
"""
import hashlib
import json
import os
import sys

import pytest
from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import scan_ix_transforms as S                    # noqa: E402

IX11 = 'http://www.xbrl.org/2013/inlineXBRL'
IX10 = 'http://www.xbrl.org/2008/inlineXBRL'
TR4 = 'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12'


def _doc(body, ix_prefix='ix', ix_uri=IX11, extra=''):
    return (f'<html xmlns:{ix_prefix}="{ix_uri}" xmlns:ixt="{TR4}"{extra}>'
            f'<body>{body}</body></html>')


def _fact(text, fmt='ixt:num-dot-decimal', prefix='ix', attrs=''):
    fa = f' format="{fmt}"' if fmt is not None else ''
    return (f'<{prefix}:nonFraction name="us-gaap:Revenues" contextRef="c"'
            f' unitRef="u"{fa}{attrs}>{text}</{prefix}:nonFraction>')


def _run(tmp_path, *documents):
    """The REAL `main()` over a temp corpus, with a matching frozen manifest.

    Returns the census document. Building the manifest here is not the scanner
    certifying itself — the point is that the scanner must READ one, and these
    controls supply it exactly as the freeze would.
    """
    root, out = tmp_path / 'in', tmp_path / 'out'
    root.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, text in enumerate(documents):
        name = f'f{i}.htm'
        (root / name).write_text(text, encoding='utf-8')
        lines.append(f'{name} '
                     + hashlib.sha256(text.encode('utf-8')).hexdigest())
    manifest = out / '01b.txt'
    manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    S.ROOT, S.MANIFEST = str(root), str(manifest)
    S.OUT, S.OCCURRENCES = str(out / '01.json'), str(out / '01c.json')
    assert S.main() == 0
    return json.loads((out / '01.json').read_text(encoding='utf-8')), \
        json.loads((out / '01c.json').read_text(encoding='utf-8'))


# ---------------------------------------------------------------- identity

def test_a_DIFFERENT_PREFIX_for_inline_XBRL_is_still_counted(tmp_path):
    """THE BUG THE OLD SCANNER COULD NOT SEE. `ix:` is an alias; this document
    calls the very same namespace `inline:` and the facts are identical facts."""
    census, _ = _run(tmp_path, _doc(_fact('1,234', prefix='inline'),
                                    ix_prefix='inline'))
    assert census['counts']['facts_by_inline_namespace'][IX11] == 1


def test_the_ix_PREFIX_bound_to_SOMETHING_ELSE_is_not_counted(tmp_path):
    """The twin, and the other half of the same error: a document may bind
    `ix:` to an unrelated namespace, and the bytes still spell `ix:nonFraction`.
    Identity is the namespace, so this is not an inline-XBRL fact."""
    census, _ = _run(tmp_path, _doc(_fact('1,234'),
                                    ix_uri='http://example.invalid/not-ixbrl'))
    assert census['counts']['facts_by_inline_namespace'][IX11] == 0


def test_inline_XBRL_1_0_is_counted_under_its_OWN_namespace(tmp_path):
    census, _ = _run(tmp_path, _doc(_fact('1,234'), ix_uri=IX10))
    assert census['counts']['facts_by_inline_namespace'][IX10] == 1
    assert census['counts']['facts_by_inline_namespace'][IX11] == 0


# ------------------------------------------------------------ format QName

def test_the_SAME_SPELLING_under_DIFFERENT_registries_is_TWO_identities(
        tmp_path):
    """`ixt:num-dot-decimal` is not a class. Two filings can spell a format
    identically and mean different registries; the old scanner counted them as
    one, which is the same prefix-for-address mistake one level down."""
    tr3 = 'http://www.xbrl.org/inlineXBRL/transformation/2015-02-26'
    census, _ = _run(
        tmp_path,
        _doc(_fact('1,234')),
        f'<html xmlns:ix="{IX11}" xmlns:ixt="{tr3}"><body>'
        f'{_fact("1,234")}</body></html>')
    assert census['by_format'] == {f'{TR4}|num-dot-decimal': 1,
                                   f'{tr3}|num-dot-decimal': 1}
    assert census['by_raw_format_spelling'] == {'ixt:num-dot-decimal': 2}


def test_an_UNPREFIXED_format_resolves_through_the_DEFAULT_namespace(tmp_path):
    """Lawful and previously rejected outright: an `xs:QName` value with no
    prefix takes the in-scope default namespace."""
    census, _ = _run(tmp_path,
                     f'<html xmlns="{TR4}" xmlns:ix="{IX11}"><body>'
                     f'{_fact("1,234", fmt="num-dot-decimal")}</body></html>')
    assert census['by_format'] == {f'{TR4}|num-dot-decimal': 1}
    assert census['counts']['facts_with_malformed_format_qname'] == 0


@pytest.mark.parametrize('spelled', ['a:b:c', 'ixt:', 'ixt: spaced', 'ixt:1st'])
def test_a_MALFORMED_format_QName_is_recorded_as_malformed(tmp_path, spelled):
    census, _ = _run(tmp_path, _doc(_fact('1,234', fmt=spelled)))
    assert census['counts']['facts_with_malformed_format_qname'] == 1
    assert census['counts']['facts_with_undeclared_format_prefix'] == 0


def test_an_UNDECLARED_prefix_is_UNRESOLVABLE___a_different_fault(tmp_path):
    """Well-formed as a name, but nothing here declares `nope:`. Merging this
    with the malformed bucket would hide one filing defect behind another."""
    census, _ = _run(tmp_path, _doc(_fact('1,234', fmt='nope:num-dot-decimal')))
    assert census['counts']['facts_with_undeclared_format_prefix'] == 1
    assert census['counts']['facts_with_malformed_format_qname'] == 0


def test_a_fact_with_NO_format_is_counted_and_never_replayed(tmp_path):
    census, occ = _run(tmp_path, _doc(_fact('1234', fmt=None)))
    assert census['by_format'] == {'<format absent>': 1}
    assert census['counts']['facts_with_a_format'] == 0
    assert occ['occurrences'] == []


# ------------------------------------------------- value, Inline XBRL 10.1.2

def test_the_LAWFUL_NESTED_nonFraction_chain_is_followed(tmp_path):
    """THE NESTED MUST-ALLOW. §10.1.1 permits exactly one child: a text node or
    one nested `ix:nonFraction`. The chain's innermost text is the value."""
    inner = _fact('1,234')
    census, occ = _run(tmp_path, _doc(_fact(inner)))
    assert census['counts']['addressed_facts_with_a_nested_nonFraction'] == 1
    # Both elements are facts; the outer one takes the inner's text.
    assert census['counts']['facts_by_inline_namespace'][IX11] == 2
    assert census['counts']['facts_eligible_for_replay'] == 2
    assert [o['text'] for o in occ['occurrences']] == ['1,234']
    assert occ['occurrences'][0]['count'] == 2


def test_STYLING_MARKUP_inside_a_number_is_NOT_lawful_content(tmp_path):
    """THE MALFORMED MUST-REFUSE, and the correction that prompted it. An
    earlier draft applied the non-numeric exclude rule here and flattened
    `<span>1,2</span><b>34</b>` into `1,234` — inventing a printed value out of
    markup the numeric content model does not allow at all."""
    census, occ = _run(tmp_path, _doc(_fact('<span>1,2</span><b>34</b>')))
    assert census['counts']['addressed_facts_with_any_child_node'] == 1
    assert census['counts']['addressed_facts_with_a_nested_nonFraction'] == 0
    assert census['counts']['facts_with_content_not_lawful_under_10_1_1'] == 1
    assert census['counts']['facts_eligible_for_replay'] == 0
    assert occ['occurrences'] == []


@pytest.mark.parametrize('content, flattened, why', [
    ('1,2<!-- editorial -->34', '1,234', 'a comment is still an extra child'),
    ('1,23<ix:exclude>x</ix:exclude>4', '1,234', 'ix:exclude is not lawful here'),
    (_fact('1') + _fact('2'), '12', 'two nested facts, not one'),
    ('lead' + _fact('1,234'), 'lead1,234', 'text mixed with the nesting'),
    (_fact('1,234') + 'tail', '1,234tail', 'a tail after the nested element'),
])
def test_every_OTHER_content_shape_is_refused_not_flattened(
        tmp_path, content, flattened, why):
    """`flattened` is the string a text-concatenating walk would have invented
    for the OUTER element. It must appear nowhere.

    THE OUTER RULE IS ISOLATED DIRECTLY. In the nesting cases the INNER
    `nonFraction` is a lawful fact in its own right and its value IS replayed,
    so an assertion that the occurrence list is empty would have been demanding
    the wrong behaviour — my first draft did exactly that and failed. What is
    actually claimed here is narrower and exact: this one element yields no
    value, and the accounting still balances around it.
    """
    outer = etree.fromstring(_doc(_fact(content))).find(
        f'.//{{{IX11}}}nonFraction')
    assert S.fact_text(outer) is None, why

    census, occ = _run(tmp_path, _doc(_fact(content)))
    assert census['counts']['facts_with_content_not_lawful_under_10_1_1'] == 1, why
    assert all(o['text'] != flattened for o in occ['occurrences']), why
    assert (census['counts']['facts_eligible_for_replay']
            == census['counts']['facts_whose_format_resolved_to_an_address'] - 1)


def test_an_UNRESOLVED_ENTITY_is_refused_rather_than_guessed(tmp_path):
    """This parser deliberately does not fetch a DTD, so it cannot know what
    the entity stands for — and an entity node is an extra child regardless."""
    census, occ = _run(
        tmp_path,
        f'<!DOCTYPE html [<!ENTITY half "0.5">]><html xmlns:ix="{IX11}" '
        f'xmlns:ixt="{TR4}"><body>{_fact("1,23&half;")}</body></html>')
    assert census['counts']['facts_with_content_not_lawful_under_10_1_1'] == 1
    assert census['counts']['facts_eligible_for_replay'] == 0
    assert occ['occurrences'] == []


# ----------------------------------------------------- premise and accounting

def test_the_REPLAY_COUNTS_SUM_EXACTLY_to_the_eligible_facts(tmp_path):
    """Multiplicity, not just membership: the same printed text appearing three
    times is three occurrences, and the totals must reconcile."""
    census, occ = _run(tmp_path, _doc(_fact('1,234') * 3 + _fact('9')))
    assert census['counts']['facts_eligible_for_replay'] == 4
    assert census['counts']['distinct_replay_occurrences'] == 2
    assert sum(o['count'] for o in occ['occurrences']) == 4
    assert occ['eligible_facts'] == 4


def test_a_MISSING_manifest_refuses_rather_than_generating_its_own_premise(
        tmp_path):
    (tmp_path / 'in').mkdir()
    S.ROOT, S.MANIFEST = str(tmp_path / 'in'), str(tmp_path / 'absent.txt')
    with pytest.raises(RuntimeError, match='missing'):
        S.main()


def test_a_file_that_CHANGED_since_the_freeze_fails(tmp_path):
    """The whole point of reading the manifest instead of writing one."""
    root, manifest = tmp_path / 'in', tmp_path / 'm.txt'
    root.mkdir()
    (root / 'f0.htm').write_text(_doc(_fact('1,234')), encoding='utf-8')
    manifest.write_text('f0.htm ' + 'a' * 64 + '\n', encoding='utf-8')
    S.ROOT, S.MANIFEST = str(root), str(manifest)
    with pytest.raises(RuntimeError, match='pinned hash'):
        S.main()


def test_an_UNPINNED_file_present_on_disk_fails(tmp_path):
    """A corpus that grew since the freeze is not the corpus that was frozen,
    even though every pinned file still matches."""
    root, manifest = tmp_path / 'in', tmp_path / 'm.txt'
    root.mkdir()
    body = _doc(_fact('1,234'))
    (root / 'f0.htm').write_text(body, encoding='utf-8')
    (root / 'sneaked-in.htm').write_text(body, encoding='utf-8')
    manifest.write_text(
        'f0.htm ' + hashlib.sha256(body.encode()).hexdigest() + '\n',
        encoding='utf-8')
    S.ROOT, S.MANIFEST = str(root), str(manifest)
    with pytest.raises(RuntimeError, match='unpinned'):
        S.main()


def test_a_file_that_is_NOT_VALID_INLINE_XBRL_is_ACCOUNTED_not_counted(
        tmp_path):
    """CONTROL 6, and the ruling that reshaped this whole test.

    Two earlier versions were wrong in opposite directions: the first RAISED,
    discarding four minutes of measurement and producing no receipt at all; the
    second wrote the receipt but called the run INCOMPLETE and exited 1.

    The second conflated two different facts. A document that is not a
    well-formed Inline XBRL report (Inline XBRL 1.1 §3.1, SEC EDGAR XBRL Guide
    June 2026 §11.2) has NO lawful transform occurrence for this product to
    replay, so excluding it is the standard being applied — not coverage being
    missed. What must hold is that every manifest file is ACCOUNTED FOR: parsed,
    or named and hashed as standards-invalid.

    So the run passes, and the invalid file stays named, hashed and excluded
    from every fact count.
    """
    root, out = tmp_path / 'in', tmp_path / 'out'
    root.mkdir(parents=True)
    out.mkdir(parents=True)
    good, bad = _doc(_fact('1,234')), '<html><body><unclosed></body></html>'
    (root / 'good.htm').write_text(good, encoding='utf-8')
    (root / 'bad.htm').write_text(bad, encoding='utf-8')
    (tmp_path / 'm.txt').write_text(
        f'bad.htm {hashlib.sha256(bad.encode()).hexdigest()}\n'
        f'good.htm {hashlib.sha256(good.encode()).hexdigest()}\n',
        encoding='utf-8')
    S.ROOT, S.MANIFEST = str(root), str(tmp_path / 'm.txt')
    S.OUT, S.OCCURRENCES = str(out / '01.json'), str(out / '01c.json')

    # CONTROL 1: the partition holds, so the run PASSES.
    assert S.main() == 0

    census = json.loads((out / '01.json').read_text(encoding='utf-8'))
    occ = json.loads((out / '01c.json').read_text(encoding='utf-8'))
    assert census['supported_scope_complete'] is True
    assert census['n_files_in_manifest'] == 2
    assert census['n_files_parsed'] == 1          # NEVER called "all files"
    [entry] = census['files_not_well_formed']
    assert entry['file'] == 'bad.htm'
    assert entry['sha256'] == hashlib.sha256(bad.encode()).hexdigest()
    assert entry['reason']
    # ...and it contributed NOTHING. The valid file's one fact is the whole
    # population; the invalid document is never transform evidence.
    assert census['counts']['facts_eligible_for_replay'] == 1
    assert census['counts']['facts_by_inline_namespace'][IX11] == 1
    assert sum(o['count'] for o in occ['occurrences']) == 1
    assert occ['n_files_parsed'] == 1
    assert [f['file'] for f in occ['files_not_well_formed']] == ['bad.htm']


def test_a_FULLY_VALID_corpus_reports_complete___the_must_allow_twin(
        tmp_path):
    census, _ = _run(tmp_path, _doc(_fact('1,234')))
    assert census['supported_scope_complete'] is True
    assert census['files_not_well_formed'] == []
    assert census['n_files_parsed'] == census['n_files_in_manifest'] == 1


def test_INLINE_XBRL_1_0_is_DETECTED_but_never_replayed(tmp_path):
    """CONTROL 4. The SEC route is 1.1-only. A 1.0 fact must be visible in the
    census — so a 1.0 document is not silently absent — and must contribute
    nothing to the supported replay population. Decided by NAMESPACE URI.

    Today the real corpus contains zero of these; this is about the day it
    does not, when an older lawful standard must not be mistaken for supported
    SEC input.
    """
    census, occ = _run(tmp_path, _doc(_fact('1,234'), ix_uri=IX10))
    assert census['counts']['facts_by_inline_namespace'][IX10] == 1
    assert census['counts']['facts_outside_product_inline_xbrl_version'] == 1
    assert census['counts']['product_inline_xbrl_namespace'] == IX11
    # Nothing about it reached the transform accounting or the replay set.
    assert census['counts']['facts_by_inline_namespace'][IX11] == 0
    assert census['counts']['facts_with_a_format'] == 0
    assert census['by_format'] == {} and census['by_raw_format_spelling'] == {}
    assert occ['occurrences'] == [] and occ['eligible_facts'] == 0


def test_a_1_1_fact_may_NOT_consume_a_nested_1_0_fact(tmp_path):
    """THE BOUNDARY LEAK THE DETECTION TUPLE CREATED.

    `fact_text` accepted any child in the inline-XBRL tuple — which gained the
    1.0 namespace when 1.0 counting was added. So a 1.1 fact wrapping a 1.0
    fact would have fed the inner text into the SUPPORTED replay population,
    widening the product boundary through the very tuple that exists only to
    make 1.0 visible. Production checks the 1.1 address at every level.
    """
    inner = (f'<old:nonFraction xmlns:old="{IX10}" name="us-gaap:Revenues"'
             f' contextRef="c" unitRef="u" format="ixt:num-dot-decimal">'
             f'9,999</old:nonFraction>')
    census, occ = _run(tmp_path, _doc(_fact(inner)))
    assert census['counts']['facts_outside_product_inline_xbrl_version'] == 1
    # The outer 1.1 fact is UNLAWFUL content, not a chain, and nothing replays.
    assert census['counts']['facts_with_content_not_lawful_under_10_1_1'] == 1
    assert census['counts']['addressed_facts_with_a_nested_nonFraction'] == 0
    assert census['counts']['facts_eligible_for_replay'] == 0
    assert occ['occurrences'] == []
    assert all('9,999' != o.get('text') for o in occ['occurrences'])


def test_a_1_1_chain_under_TWO_DIFFERENT_PREFIXES_is_replayed___the_twin(
        tmp_path):
    """Same shape, both elements in the PRODUCT namespace but spelled with
    different prefixes. Identity is the namespace, so this is lawful and must
    replay — otherwise the rule above is just "reject nesting"."""
    inner = (f'<alt:nonFraction xmlns:alt="{IX11}" name="us-gaap:Revenues"'
             f' contextRef="c" unitRef="u" format="ixt:num-dot-decimal">'
             f'1,234</alt:nonFraction>')
    census, occ = _run(tmp_path, _doc(_fact(inner)))
    assert census['counts']['facts_outside_product_inline_xbrl_version'] == 0
    assert census['counts']['addressed_facts_with_a_nested_nonFraction'] == 1
    assert census['counts']['facts_with_content_not_lawful_under_10_1_1'] == 0
    assert [o['text'] for o in occ['occurrences']] == ['1,234']
    assert occ['occurrences'][0]['count'] == 2      # outer and inner


def test_INLINE_XBRL_1_1_beside_it_IS_replayed___the_twin(tmp_path):
    """CONTROL 5, in the same shape as CONTROL 4 so the only difference is the
    namespace URI. A rule that dropped both would satisfy the case above."""
    census, occ = _run(tmp_path, _doc(_fact('1,234'), ix_uri=IX11))
    assert census['counts']['facts_by_inline_namespace'][IX11] == 1
    assert census['counts']['facts_outside_product_inline_xbrl_version'] == 0
    assert [o['text'] for o in occ['occurrences']] == ['1,234']


def test_TWO_IDENTICAL_RUNS_produce_BYTE_IDENTICAL_receipts(tmp_path):
    """No wall-clock stamp anywhere: "nothing changed" has to be provable by
    comparing the receipts, not by reading them.

    RAW BYTES, and BOTH receipts. Two earlier versions were weaker than their
    own name: one compared only the census JSON, and both parsed the JSON,
    removed a field and re-serialised — which proves SEMANTIC equality and
    would pass through any change in key order, spacing or encoding. The same
    input and output locations are used twice and the bytes are kept from run
    one, so nothing is normalised away.
    """
    root, out = tmp_path / 'in', tmp_path / 'out'
    root.mkdir(parents=True)
    out.mkdir(parents=True)
    body = _doc(_fact('1,234'))
    (root / 'f0.htm').write_text(body, encoding='utf-8')
    (out / '01b.txt').write_text(
        'f0.htm ' + hashlib.sha256(body.encode()).hexdigest() + '\n',
        encoding='utf-8')
    S.ROOT, S.MANIFEST = str(root), str(out / '01b.txt')
    S.OUT, S.OCCURRENCES = str(out / '01.json'), str(out / '01c.json')

    assert S.main() == 0
    first = ((out / '01.json').read_bytes(), (out / '01c.json').read_bytes())
    assert S.main() == 0
    second = ((out / '01.json').read_bytes(), (out / '01c.json').read_bytes())

    assert first[0] == second[0], 'the census receipt bytes are not stable'
    assert first[1] == second[1], 'the occurrence receipt bytes are not stable'


def test_the_XML_LIBRARY_validates_names___not_a_pattern_of_mine():
    """`expanded` must delegate name validity to lxml, and must judge the NAME
    before looking up the PREFIX.

    A combining acute may appear inside an XML name but cannot start one — the
    kind of distinction a hand-rolled character class routinely gets wrong. It
    is also unprefixed here, which pins the ORDER: an earlier draft resolved
    first and so reported this as "unresolvable prefix", blaming a missing
    declaration for a defect in the name itself.
    """
    default_ns = etree.fromstring(f'<a xmlns="{TR4}" xmlns:p="{TR4}"/>')
    no_default = etree.fromstring(f'<a xmlns:p="{TR4}"/>')
    ok = 'num-dot-decimal'
    # Each row is a PAIR: the lawful form and the one that differs from it in
    # exactly one respect. Single-sided cases cannot show where a rule stops.
    pairs = [
        # XSD `whiteSpace=collapse` trims XML space — and ONLY XML space.
        (no_default, f' \t\r\np:{ok}\n ', (TR4, ok)),
        (no_default, f' p:{ok}', S.MALFORMED),      # NBSP is not XML space
        # Both components are validated, so a broken PREFIX is malformed rather
        # than "a lawful prefix nobody declared".
        (no_default, f'1bad:{ok}', S.MALFORMED),
        (no_default, f'undeclared:{ok}', S.UNRESOLVABLE),
        # Unprefixed: the default namespace applies, or the name is lawfully in
        # no namespace at all — which is not a missing declaration.
        (default_ns, ok, (TR4, ok)),
        (no_default, ok, S.NO_NAMESPACE),
    ]
    for element, spelled, want in pairs:
        assert S.expanded(element, spelled) == want, spelled

    el = no_default
    assert S.expanded(el, 'p:áb') == (TR4, 'áb')
    assert S.expanded(el, '́ab') == S.MALFORMED
    assert S.expanded(el, 'undeclared:fine') == S.UNRESOLVABLE
