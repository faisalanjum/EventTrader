"""#827 Stage 3 — the parity gate must be able to go RED.

WHY THIS FILE EXISTS. `24_arelle_ixt_parity.json` reports a three-field verdict
— `version_parity_proven`, `supported_scope_complete`, `gate_passed` — over the
supported registries and the frozen corpus. Those are worth nothing unless the
tool that wrote it would have said `false` had the versions actually differed —
and the FIRST version of that tool could not: it returned 0 on install failure,
on import failure and on a clean pass alike, so its green was indistinguishable
from its red.

So every judgement the tool makes is exercised in BOTH directions here: each
way it must fail, and — the half that is easy to forget — the matching case
where it must NOT fail. A detector that fires on everything is as useless as
one that fires on nothing.

NOTHING HERE TOUCHES THE NETWORK. An earlier version proved the install failure
with a real pip resolution against a version that does not exist, which made an
ordinary `pytest` run depend on PyPI being reachable — a test that fails on a
train is not a test of this code. The two REAL clean installs belong to the
explicit receipt run (`python arelle_ixt_parity.py`) and stay there; here the
same propagation is proved with a local subprocess whose exit status is chosen
deterministically, plus its passing twin.

The wiring test (does a failure actually reach the exit code) stubs
`build`/`probe`, because what it tests is the wiring, and it writes to a temp
file so the real receipt is never touched.
"""
import hashlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arelle_ixt_parity as P                      # noqa: E402

#: A minimal, internally consistent pair of probe results: everything the
#: comparison reads, and nothing it does not.
def _side(results=None, table=None, sec=False):
    table = table if table is not None else {ns: ['num-dot-decimal']
                                             for ns in P.SUPPORTED}
    return {'results': dict(results or {'k': ['ok', '1234']}),
            'function_table': dict(table),
            'sec_registry_implemented': sec}


NAMES = ('a', 'b')


def test_IDENTICAL_versions_pass___the_must_allow_twin():
    """Nothing here fires on a genuine agreement. Without this case every
    assertion below is satisfied by a comparison that always fails."""
    _keys, diffs, bad = P.compare(_side(), _side(), NAMES)
    assert diffs == [] and bad == []


def test_a_BEHAVIOURAL_difference_fails():
    a = _side({'k': ['ok', '1234']})
    b = _side({'k': ['ok', '1235']})
    _keys, diffs, bad = P.compare(a, b, NAMES)
    assert len(diffs) == 1
    assert any('behavioural differences' in s for s in bad)


def test_a_case_present_in_ONE_version_only_fails():
    """A function that exists in one version and not the other is a difference,
    not an absence to skip. The union of keys is what makes this bite."""
    _keys, diffs, bad = P.compare(_side({'k': ['ok', '1']}),
                                  _side({'k': ['ok', '1'], 'extra': ['ok', '2']}),
                                  NAMES)
    assert [d['case'] for d in diffs] == ['extra']
    assert bad


def test_a_MISSING_supported_registry_fails():
    """Both versions agreeing that a registry is gone is still a failure: they
    would agree perfectly and cover nothing."""
    short = {ns: ['num-dot-decimal'] for ns in P.SUPPORTED[:-1]}
    _keys, _diffs, bad = P.compare(_side(table=short), _side(table=short),
                                   NAMES)
    assert sum('does not implement supported registries' in s for s in bad) == 2
    assert P.SUPPORTED[-1] in ' '.join(bad)


def test_the_SEC_registry_is_not_in_the_gate():
    """Arelle does not implement it, so no Arelle-based parity statement about
    it is possible. The registries the product REFUSES are not listed here at
    all: the recorded outside set is derived per version from that
    installation's own table, so there is no second inventory to drift."""
    assert P.SEC_REGISTRY not in P.SUPPORTED


def test_a_version_CLAIMING_the_SEC_registry_fails():
    """The receipt's scope note rests on Arelle not implementing the SEC
    registry. If that ever became untrue the note would be a false statement,
    so the tool refuses rather than printing it."""
    _keys, _diffs, bad = P.compare(_side(sec=True), _side(), NAMES)
    assert any(P.SEC_REGISTRY in s for s in bad)


def test_DIFFERING_function_tables_fail():
    other = {ns: ['num-dot-decimal', 'fixed-zero'] for ns in P.SUPPORTED}
    _k, _d, bad = P.compare(_side(), _side(table=other), NAMES)
    assert any('function tables differ' in s for s in bad)


def test_a_NONZERO_subprocess_becomes_a_Failure___and_a_zero_one_does_not():
    """The install path's whole error handling is `_sh`. Proved with a local
    interpreter whose exit status is chosen here, so an ordinary test run needs
    no network; the two real clean installs stay in the receipt run.

    The passing twin is not decoration: a `_sh` that raised on everything would
    satisfy the first half and break the tool completely."""
    with pytest.raises(P.Failure) as exc:
        P._sh([sys.executable, '-c',
               'import sys; sys.stderr.write("boom"); sys.exit(3)'])
    assert 'exited 3' in str(exc.value) and 'boom' in str(exc.value)

    assert P._sh([sys.executable, '-c', 'print("fine")']).strip() == 'fine'


def _pkg(name, version, sha):
    return {'metadata': {'name': name, 'version': version},
            'download_info': {'url': 'file://local',
                              'archive_info': {'hashes': {'sha256': sha}}}}


def _install_report(tmp_path, version, resolved=None, sha=None, deps=()):
    """A pip `--report` file, written locally. No index is contacted."""
    path = tmp_path / f'install-{version}.json'
    path.write_text(json.dumps({'install': [
        _pkg('arelle-release', resolved or version, sha)] + list(deps)}),
        encoding='utf-8')
    return path


def _stub_build(monkeypatch):
    """ONE stand-in for `build`, in the CURRENT provenance shape.

    Two copies of this stub still carried `dependency_count`, the field the
    receipt no longer has — stale fixtures quietly asserting an old contract.
    Routing both through one helper means the shape can only be wrong once.
    """
    monkeypatch.setattr(P, 'build', lambda v, root: ('python', {
        'requested': v, 'resolved': v, 'url': 'test', 'sha256': 'x' * 64,
        'environment': [{'name': 'arelle-release', 'version': v,
                         'sha256': 'x' * 64}],
        'distributions_installed': 1}))


def test_EVERY_distribution_is_named_versioned_and_hashed(tmp_path,
                                                          monkeypatch):
    """The receipt recorded `dependency_count: 12` / `21`. A count cannot
    reproduce or audit an environment, and Arelle's behaviour depends on what
    sits beneath it."""
    _install_report(tmp_path, '2.35.0', sha='a' * 64,
                    deps=[_pkg('lxml', '5.2.1', 'b' * 64),
                          _pkg('isodate', '0.6.1', 'c' * 64)])
    monkeypatch.setattr(P, '_sh', lambda argv, **k: '')
    _py, prov = P.build('2.35.0', str(tmp_path))
    assert prov['distributions_installed'] == 3
    assert [d['name'] for d in prov['environment']] == [
        'arelle-release', 'isodate', 'lxml']          # sorted, all named
    assert all(len(d['sha256']) == 64 and d['version'] for d
               in prov['environment'])
    assert 'dependency_count' not in prov


def test_a_DEPENDENCY_without_a_hash_fails_too(tmp_path, monkeypatch):
    """Pinning Arelle while leaving what it runs on unpinned would name the
    environment without fixing it."""
    _install_report(tmp_path, '2.35.0', sha='a' * 64,
                    deps=[_pkg('lxml', '5.2.1', None)])
    monkeypatch.setattr(P, '_sh', lambda argv, **k: '')
    with pytest.raises(P.Failure, match='lxml'):
        P.build('2.35.0', str(tmp_path))


def _stub_sh(monkeypatch, tmp_path, version, **kw):
    _install_report(tmp_path, version, **kw)
    monkeypatch.setattr(P, '_sh', lambda argv, **k: '')


def test_a_version_pip_RESOLVED_DIFFERENTLY_fails(tmp_path, monkeypatch):
    """`arelle-release==2.35.0` resolving to anything else must fail: the
    receipt would otherwise name a version that was never installed."""
    _stub_sh(monkeypatch, tmp_path, '2.35.0', resolved='2.35.1', sha='a' * 64)
    with pytest.raises(P.Failure, match='resolved'):
        P.build('2.35.0', str(tmp_path))


@pytest.mark.parametrize('sha', [None, '', 'abc', 'A' * 64, 'g' * 64,
                                 'a' * 63, 'a' * 65])
def test_a_sha256_that_is_not_ONE_fails(tmp_path, monkeypatch, sha):
    """Missing, truncated, over-long, upper-case or non-hex — each would still
    print convincingly in the receipt, which is exactly the problem."""
    _stub_sh(monkeypatch, tmp_path, '2.35.0', sha=sha)
    with pytest.raises(P.Failure, match='sha256'):
        P.build('2.35.0', str(tmp_path))


def test_a_GOOD_install_report_is_accepted___the_must_allow_twin(
        tmp_path, monkeypatch):
    """Without this, every assertion above is satisfied by a `build` that
    rejects everything."""
    _stub_sh(monkeypatch, tmp_path, '2.35.0', sha='0123456789abcdef' * 4)
    _py, prov = P.build('2.35.0', str(tmp_path))
    assert prov['resolved'] == '2.35.0'
    assert prov['sha256'] == '0123456789abcdef' * 4
    # Only provenance that OUTLIVES the temp directory: a path inside a
    # directory about to be deleted proves nothing to a later reader.
    assert not any(str(tmp_path) in str(v) for v in prov.values())


#: The hash every synthetic excluded file carries, so the fixture manifest and
#: the receipt agree by construction.
_INVALID_SHA = 'd' * 64


def _occ_file(tmp_path, occurrences, complete=True, unread=(),
              manifest_body=None, manifest_sha=None, eligible=None, drop=None):
    """An occurrence file AND the REAL manifest it claims to be built from.

    The manifest is generated from the same parameters as the receipt — one
    parsed file plus a row for every excluded one — because the loader now
    binds each excluded entry to an actual manifest row. A placeholder body
    would fail as a malformed manifest rather than exercising the binding.
    """
    if manifest_body is None:
        rows = [b'good.htm ' + b'e' * 64]
        rows += [u.encode() + b' ' + _INVALID_SHA.encode() for u in unread]
        manifest_body = b'\n'.join(rows) + b'\n'
    (tmp_path / '01b.txt').write_bytes(manifest_body)
    path = tmp_path / P.OCCURRENCES
    doc = {
        'input_manifest_file': '01b.txt',
        'input_manifest_sha256': manifest_sha or hashlib.sha256(
            manifest_body).hexdigest(),
        'supported_scope_complete': complete,
        'n_files_in_manifest': 1 + len(unread),
        'n_files_parsed': 1,
        'files_not_well_formed': [{'file': u, 'sha256': 'd' * 64,
                                   'reason': 'not well-formed'} for u in unread],
        'eligible_facts': (sum(o['count'] for o in occurrences)
                           if eligible is None else eligible),
        'occurrences': occurrences}
    doc.pop(drop, None)
    path.write_text(json.dumps(doc), encoding='utf-8')
    return path


ONE_CASE = [{'registry': P.SUPPORTED[1], 'local': 'num-dot-decimal',
             'text': '1,234', 'count': 7}]


@pytest.mark.parametrize('field', ['supported_scope_complete', 'eligible_facts',
                                   'input_manifest_sha256', 'occurrences'])
def test_a_MISSING_scope_field_refuses(tmp_path, field):
    """This gate takes its whole population from `01c`. A malformed input
    would otherwise be built on silently."""
    path = _occ_file(tmp_path, ONE_CASE, drop=field)
    with pytest.raises(P.Failure, match=field):
        P.load_occurrences(str(path))


@pytest.mark.parametrize('count', [0, -1, 1.5, True, '3', None])
def test_a_MULTIPLICITY_that_is_not_a_positive_integer_refuses(tmp_path, count):
    """`True` is in this list on purpose: it is an `int` in Python and would
    sail through a naive check while meaning nothing as a fact count."""
    rows = [dict(ONE_CASE[0], count=count)]
    path = _occ_file(tmp_path, rows, eligible=1)
    with pytest.raises(P.Failure, match='positive integer'):
        P.load_occurrences(str(path))


def test_a_DUPLICATE_triple_refuses(tmp_path):
    """Two rows for the same input would double-count the multiplicity."""
    rows = [dict(ONE_CASE[0]), dict(ONE_CASE[0])]
    path = _occ_file(tmp_path, rows)
    with pytest.raises(P.Failure, match='duplicate occurrence'):
        P.load_occurrences(str(path))


def test_multiplicities_that_do_NOT_sum_to_eligible_facts_refuse(tmp_path):
    path = _occ_file(tmp_path, ONE_CASE, eligible=999)
    with pytest.raises(P.Failure, match='not the population it claims'):
        P.load_occurrences(str(path))


def test_BOTH_distinct_and_summed_populations_are_recorded(tmp_path):
    """Two different questions: how many DISTINCT inputs were replayed, and how
    many FACTS they stand for. The receipt must answer both."""
    rows = ONE_CASE + [{'registry': P.SEC_REGISTRY, 'local': 'numwordsen',
                        'text': 'two', 'count': 5}]
    _cases, b = P.load_occurrences(str(_occ_file(tmp_path, rows)))
    assert b['distinct_triples_total'] == 2
    assert b['distinct_triples_replayed'] == 1        # SEC one is out of scope
    assert b['fact_multiplicity_total'] == 12
    assert b['fact_multiplicity_replayed'] == 7


def test_a_STANDARDS_INVALID_file_is_ACCOUNTED_and_stays_NAMED(tmp_path):
    """CONTROL 6 at the loader.

    The original blocker was a receipt saying it covered "every occurrence in
    the frozen corpus" while its input recorded a file it never read. The fix
    first swung too far and called that INCOMPLETE COVERAGE — but a document
    that is not a valid Inline XBRL report has no lawful occurrence to replay,
    so leaving it out is the standard, not a gap.

    What must travel is the ACCOUNTING: the file is named, hashed, excluded,
    and the partition closes.
    """
    path = _occ_file(tmp_path, ONE_CASE, complete=True, unread=['broken.htm'])
    _cases, binding = P.load_occurrences(str(path))
    assert binding['supported_scope_complete'] is True
    assert binding['files_not_valid_inline_xbrl'] == [
        {'file': 'broken.htm', 'sha256': 'd' * 64}]
    assert binding['files_parsed'] == 1 and binding['files_in_manifest'] == 2


#: A manifest whose rows are real, so the invalid-file list can be bound to it.
_MANIFEST_ROWS = (b'broken.htm ' + b'd' * 64 + b'\n'
                  b'good.htm ' + b'e' * 64 + b'\n')


def test_a_MADE_UP_invalid_filename_refuses(tmp_path):
    """The forgery the binding closes: a plausible name with a well-shaped hash
    plus a reduced parsed count satisfied the partition equation and reported
    complete supported scope. A file the corpus does not contain cannot be
    excluded from it."""
    path = _occ_file(tmp_path, ONE_CASE, complete=True, unread=['invented.htm'],
                     manifest_body=_MANIFEST_ROWS)
    with pytest.raises(P.Failure, match='not in the frozen manifest'):
        P.load_occurrences(str(path))


def test_a_REAL_filename_with_the_WRONG_hash_refuses(tmp_path):
    path = _occ_file(tmp_path, ONE_CASE, complete=True, unread=['broken.htm'],
                     manifest_body=_MANIFEST_ROWS)
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['files_not_well_formed'][0]['sha256'] = 'f' * 64   # manifest pins d*64
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(P.Failure, match='that is a different file'):
        P.load_occurrences(str(path))


def test_a_MANIFEST_ROW_COUNT_that_disagrees_with_the_receipt_refuses(tmp_path):
    path = _occ_file(tmp_path, ONE_CASE, complete=True, unread=['broken.htm'],
                     manifest_body=_MANIFEST_ROWS)
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['n_files_in_manifest'] = 3           # the manifest holds 2 rows
    doc['n_files_parsed'] = 2
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(P.Failure, match='do not describe the same corpus'):
        P.load_occurrences(str(path))


def test_an_EXACT_invalid_file_row_is_accepted___the_must_allow_twin(tmp_path):
    """Name and hash both matching a real manifest row. Without this, a check
    that rejected every exclusion would satisfy all three cases above."""
    path = _occ_file(tmp_path, ONE_CASE, complete=True, unread=['broken.htm'],
                     manifest_body=_MANIFEST_ROWS)
    _cases, binding = P.load_occurrences(str(path))
    assert binding['supported_scope_complete'] is True
    assert binding['files_not_valid_inline_xbrl'] == [
        {'file': 'broken.htm', 'sha256': 'd' * 64}]


def _manifest_of(n):
    """A real manifest with `n` distinct rows."""
    return b'\n'.join(f'f{i}.htm'.encode() + b' ' + bytes(str(i % 10), 'ascii')
                      * 64 for i in range(1, n + 1)) + b'\n'


def test_an_UNACCOUNTED_manifest_file_refuses(tmp_path):
    """CONTROL 2. A file that is neither parsed nor named standards-invalid is
    unexplained, and no receipt may describe a population it cannot account
    for. The manifest really does hold 9 rows here, so this targets the
    PARTITION rather than a row-count mismatch."""
    path = _occ_file(tmp_path, ONE_CASE, manifest_body=_manifest_of(9))
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['n_files_in_manifest'] = 9            # 1 parsed + 0 invalid != 9
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(P.Failure, match='scope does not add up'):
        P.load_occurrences(str(path))


def test_a_COMPLETE_corpus_reports_covered___the_must_allow_twin(tmp_path):
    _cases, binding = P.load_occurrences(str(_occ_file(tmp_path, ONE_CASE)))
    assert binding['supported_scope_complete'] is True
    assert binding['files_not_valid_inline_xbrl'] == []


def test_the_MANIFEST_BINDING_is_enforced_not_merely_copied(tmp_path):
    """Second defect found in my own pre-audit: the gate lifted
    `input_manifest_sha256` out of the occurrence file and printed it in the
    receipt without ever comparing it to the manifest on disk. Replay inputs
    built against a different corpus would have passed with a
    convincing-looking hash beside them."""
    path = _occ_file(tmp_path, ONE_CASE, manifest_sha='b' * 64)
    with pytest.raises(P.Failure, match='do not belong to this corpus'):
        P.load_occurrences(str(path))


def test_a_MATCHING_manifest_is_accepted___the_must_allow_twin(tmp_path):
    body = b'good.htm ' + b'e' * 64 + b'\n'
    _cases, binding = P.load_occurrences(str(
        _occ_file(tmp_path, ONE_CASE, manifest_body=body)))
    assert binding['input_manifest_sha256'] == hashlib.sha256(body).hexdigest()


def test_a_MISSING_manifest_refuses_rather_than_believing_the_hash(tmp_path):
    path = _occ_file(tmp_path, ONE_CASE)
    (tmp_path / '01b.txt').unlink()
    with pytest.raises(P.Failure, match='cannot be checked'):
        P.load_occurrences(str(path))


def test_ABSENT_in_BOTH_versions_is_not_counted_as_agreement():
    """Third gap from the same pre-audit. A transform neither version
    implements makes both sides record `absent`; they agree, and the case would
    slide into the pass count having exercised nothing."""
    side = lambda: _side({'k': ['absent', 'no such transform in this version']})
    _keys, diffs, bad = P.compare(side(), side(), NAMES)
    assert diffs == []                      # they DO agree...
    assert any('neither version implements' in s for s in bad)   # ...and that
    #                                                              is the point


def test_a_transform_BOTH_versions_implement_is_fine___the_must_allow_twin():
    _keys, diffs, bad = P.compare(_side(), _side(), NAMES)
    assert diffs == [] and bad == []


def test_a_MISSING_occurrence_file_refuses_rather_than_inventing_inputs(
        tmp_path):
    with pytest.raises(P.Failure, match='missing'):
        P.load_occurrences(str(tmp_path / P.OCCURRENCES))


def test_occurrences_OUTSIDE_the_supported_registries_leave_nothing_to_prove(
        tmp_path):
    """A corpus of only SEC-registry or TR1 occurrences supports no claim, and
    saying so is better than reporting a parity proven over zero cases."""
    path = _occ_file(tmp_path, [{'registry': P.SEC_REGISTRY, 'count': 1,
                                 'local': 'numwordsen', 'text': 'two'}])
    with pytest.raises(P.Failure, match='no occurrence'):
        P.load_occurrences(str(path))


def test_occurrences_are_FILTERED_to_supported_and_HASHED_from_the_bytes(
        tmp_path):
    path = _occ_file(tmp_path, [
        {'registry': P.SUPPORTED[1], 'local': 'num-dot-decimal',
         'text': '1,234', 'count': 2},
        {'registry': P.SEC_REGISTRY, 'local': 'numwordsen', 'text': 'two',
         'count': 1}])
    cases, binding = P.load_occurrences(str(path))
    assert cases == [(P.SUPPORTED[1], 'num-dot-decimal', '1,234')]
    assert binding['occurrences_total'] == 2
    assert binding['occurrences_in_supported_registries'] == 1
    # Measured from the bytes on disk, not copied from a field the file states
    # about itself.
    assert binding['occurrence_file_sha256'] == hashlib.sha256(
        path.read_bytes()).hexdigest()


def test_a_failure_REACHES_the_exit_code_and_the_receipt(tmp_path, monkeypatch):
    """The wiring, end to end: a difference must produce exit 1 AND a receipt
    that records it, because a red run is evidence too."""
    _stub_build(monkeypatch)
    sides = {P.VERSIONS[0]: _side({'k': ['ok', '1']}),
             P.VERSIONS[1]: _side({'k': ['ok', '2']})}
    seen = iter([sides[v] for v in P.VERSIONS])
    monkeypatch.setattr(P, 'probe', lambda py, cases: next(seen))
    occ = _occ_file(tmp_path, [{'registry': P.SUPPORTED[1], 'count': 1,
                                'local': 'num-dot-decimal', 'text': '1,234'}])

    dest = tmp_path / 'receipt.json'
    assert P.main(dest=str(dest), occurrences=str(occ)) == 1

    report = json.loads(dest.read_text(encoding='utf-8'))
    assert report['gate_passed'] is False
    assert report['failures'] and report['differences']
    assert 'NOT universal parity' in report['claim']
    # The two facts stay SEPARATE: the versions disagreed, but the corpus was
    # fully covered. One name for both would let either be read as the other.
    assert report['version_parity_proven'] is False
    assert report['supported_scope_complete'] is True


@pytest.mark.parametrize('mutate, expect', [
    ({'supported_scope_complete': 'false'}, 'JSON boolean'),
    ({'supported_scope_complete': 1}, 'JSON boolean'),
    ({'n_files_parsed': True}, 'not a positive|non-negative integer'),
    ({'n_files_parsed': -1}, 'non-negative integer'),
    ({'n_files_parsed': '1'}, 'non-negative integer'),
    ({'input_manifest_sha256': 'A' * 64}, 'lowercase sha256'),
    ({'input_manifest_file': ''}, 'one plain file name'),
    ({'files_not_well_formed': {}}, 'not a list'),
    ({'n_files_in_manifest': 9}, 'do not describe the same corpus'),
])
def test_a_SCOPE_FIELD_of_the_wrong_TYPE_or_VALUE_refuses(tmp_path, mutate,
                                                          expect):
    """The false-green the reviewer reproduced: `supported_scope_complete: "false"` is a
    non-empty string, so `bool(...)` read it as TRUE and the gate reported full
    coverage over 1 file of 9. Presence plus truthiness is not validation."""
    path = _occ_file(tmp_path, ONE_CASE)
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc.update(mutate)
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(P.Failure, match=expect):
        P.load_occurrences(str(path))


@pytest.mark.parametrize('mutate, expect', [
    # Each of these was independently driven through the loader and either
    # leaked an AttributeError — a crash where a truthful refusal belongs — or
    # was accepted outright.
    ({'files_not_well_formed': ['broken.htm']}, 'not a record'),
    ({'occurrences': {}}, 'not a list'),
    ({'occurrences': ['x']}, 'not a record'),
    ({'input_manifest_file': '../01b.txt'}, 'one plain file name'),
    ({'input_manifest_file': 'sub/01b.txt'}, 'one plain file name'),
])
def test_a_MALFORMED_RECEIPT_raises_the_tools_own_Failure_never_a_crash(
        tmp_path, mutate, expect):
    path = _occ_file(tmp_path, ONE_CASE)
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc.update(mutate)
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(P.Failure, match=expect):
        P.load_occurrences(str(path))


def test_the_SAME_FILE_listed_unread_TWICE_refuses(tmp_path):
    """It satisfied the scope equation by being counted twice. The manifest
    holds three DISTINCT rows, so this targets the duplicate in the RECEIPT."""
    body = (b'good.htm ' + b'e' * 64 + b'\n'
            b'broken.htm ' + _INVALID_SHA.encode() + b'\n'
            b'other.htm ' + b'c' * 64 + b'\n')
    path = _occ_file(tmp_path, ONE_CASE, complete=True, manifest_body=body,
                     unread=['broken.htm', 'broken.htm'])
    with pytest.raises(P.Failure, match='unread more than once'):
        P.load_occurrences(str(path))


def test_FACTS_FROM_NO_FILES_refuse(tmp_path):
    """0 in the manifest, 0 read, 1 eligible fact. Every equation held — zero
    equals zero — and it was accepted as COMPLETE coverage of nothing."""
    path = _occ_file(tmp_path, ONE_CASE, manifest_body=b'')
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['n_files_in_manifest'] = doc['n_files_parsed'] = 0
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(P.Failure, match='cannot come from no corpus'):
        P.load_occurrences(str(path))


def test_a_LAWFUL_RECEIPT_still_loads___the_must_allow_twin(tmp_path):
    """Checks that refuse everything would satisfy every case above."""
    cases, binding = P.load_occurrences(str(_occ_file(tmp_path, ONE_CASE)))
    assert cases and binding['supported_scope_complete'] is True


def test_a_SCOPE_FLAG_that_contradicts_the_counts_refuses(tmp_path):
    """`supported_scope_complete` is not a field to be asserted independently
    of the files it describes: the counts decide, and the flag must match."""
    path = _occ_file(tmp_path, ONE_CASE)
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['supported_scope_complete'] = False    # ...while the partition holds
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(P.Failure, match='not a field to be asserted'):
        P.load_occurrences(str(path))


@pytest.mark.parametrize('row', [
    {'registry': 1}, {'local': None}, {'text': ['x']}])
def test_an_OCCURRENCE_ROW_that_does_not_identify_an_input_refuses(tmp_path,
                                                                   row):
    path = _occ_file(tmp_path, [dict(ONE_CASE[0], **row)])
    with pytest.raises(P.Failure, match='does not identify an input'):
        P.load_occurrences(str(path))


def test_an_UNREAD_FILE_must_still_be_identified(tmp_path):
    path = _occ_file(tmp_path, ONE_CASE, complete=False, unread=['broken.htm'])
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['files_not_well_formed'] = [{'file': 'broken.htm', 'sha256': 'nope'}]
    path.write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(P.Failure, match='must still be identified'):
        P.load_occurrences(str(path))


def test_a_COMPLETE_LAWFUL_INPUT_reaches_gate_passed___END_TO_END(
        tmp_path, monkeypatch):
    """THE MUST-ALLOW TWIN AT THE TOP LEVEL, and the one that was missing.

    Every other complete-coverage case stopped at `load_occurrences`, so a
    `main()` that always failed would have satisfied all of them. This drives
    the whole entry point with agreeing probes and a lawful input and requires
    exit 0 with all three fields true.
    """
    monkeypatch.setattr(P, 'build',
                        lambda v, root: ('python', {'resolved': v,
                                                    'sha256': 'x' * 64,
                                                    'url': 'test',
                                                    'requested': v,
                                                    'environment': [],
                                                    'distributions_installed': 1}))
    agree = iter([_side({'k': ['ok', '1']}), _side({'k': ['ok', '1']})])
    monkeypatch.setattr(P, 'probe', lambda py, cases: next(agree))
    occ = _occ_file(tmp_path, ONE_CASE)

    dest = tmp_path / 'receipt.json'
    assert P.main(dest=str(dest), occurrences=str(occ)) == 0

    report = json.loads(dest.read_text(encoding='utf-8'))
    assert report['version_parity_proven'] is True
    assert report['supported_scope_complete'] is True
    assert report['gate_passed'] is True
    assert report['failures'] == []
    # And no path from the deleted temp directory survived into the receipt.
    assert str(tmp_path) not in json.dumps(report['provenance'])
    assert 'function_ixt_file' not in json.dumps(report)


def test_A_STANDARDS_INVALID_FILE_does_NOT_block_the_gate___END_TO_END(
        tmp_path, monkeypatch):
    """CONTROL 1 in full: parsed + standards-invalid == manifest and the two
    versions agree, so the gate PASSES — while the invalid file stays named and
    hashed in the receipt.

    This is the ruling that replaced my earlier behaviour. I had the gate fail
    here, on the reasoning that an unread file meant incomplete coverage. It
    does not: an invalid Inline XBRL report has no lawful occurrence to replay,
    so its absence is the standard being applied.
    """
    _stub_build(monkeypatch)
    agree = iter([_side({'k': ['ok', '1']}), _side({'k': ['ok', '1']})])
    monkeypatch.setattr(P, 'probe', lambda py, cases: next(agree))
    occ = _occ_file(tmp_path, ONE_CASE, complete=True, unread=['broken.htm'])

    dest = tmp_path / 'receipt.json'
    assert P.main(dest=str(dest), occurrences=str(occ)) == 0

    report = json.loads(dest.read_text(encoding='utf-8'))
    assert report['version_parity_proven'] is True
    assert report['supported_scope_complete'] is True
    assert report['gate_passed'] is True
    assert report['failures'] == []
    # ...and it is still named, hashed and visible.
    assert report['corpus_binding']['files_not_valid_inline_xbrl'] == [
        {'file': 'broken.htm', 'sha256': 'd' * 64}]
    assert report['corpus_binding']['files_parsed'] == 1
    assert report['corpus_binding']['files_in_manifest'] == 2


def test_VERSION_DISAGREEMENT_fails_even_with_a_whole_manifest(
        tmp_path, monkeypatch):
    """CONTROL 3. The other half of `gate_passed`: scope can be perfect and the
    gate must still fail when the two versions differ."""
    _stub_build(monkeypatch)
    differ = iter([_side({'k': ['ok', '1']}), _side({'k': ['ok', '2']})])
    monkeypatch.setattr(P, 'probe', lambda py, cases: next(differ))
    occ = _occ_file(tmp_path, ONE_CASE)

    dest = tmp_path / 'receipt.json'
    assert P.main(dest=str(dest), occurrences=str(occ)) == 1

    report = json.loads(dest.read_text(encoding='utf-8'))
    assert report['supported_scope_complete'] is True
    assert report['version_parity_proven'] is False
    assert report['gate_passed'] is False
