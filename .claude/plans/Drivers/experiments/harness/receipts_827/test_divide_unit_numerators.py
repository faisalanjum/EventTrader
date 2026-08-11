"""#827 — the census accounting, driven by two hand-made declarations.

`tally` decides which bucket every declaration falls into and how the totals
add up. It was unreachable to any test while it lived inside `main` behind a
Neo4j query and a 1,769-filing cache, and that is precisely how two defects
survived review:

  * the graph query filtered `u.is_divide = '1'`, so the simple branch could
    never receive a row — its list would have been empty, and empty reads as
    "nothing to report" rather than "never ran";
  * `declarations_read` was incremented only on the divide path, so every
    valid SIMPLE declaration was classified and reported unread at once.

Neither is visible in a total. Both are obvious the moment one simple and one
divide row go in and the buckets are compared against each other.

`tally` is NOT pure, and this file does not pretend otherwise: it is graph-
free and writes no output file, but it still opens and parses cache files
lazily into `parsed`. Every test here pre-populates `parsed`, which is the
only reason no test touches the disk. `_emit` DOES write, so its test is given
a temporary path.
"""
import importlib.util
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import divide_unit_numerators as C                               # noqa: E402

ISO = 'http://www.xbrl.org/2003/iso4217'
XBRLI = 'http://www.xbrl.org/2003/instance'

#: What `inline_html.prepare(...)["units"]` yields for one simple and one
#: divide declaration. Written out rather than parsed so the expected buckets
#: are visible beside the input.
SIMPLE_UNIT = {'is_divide': False,
               'measures': ('iso4217:USD',),
               'expanded_measures': ((ISO, 'USD'),),
               'numerator': (), 'denominator': (),
               'expanded_numerator': (), 'expanded_denominator': ()}
DIVIDE_UNIT = {'is_divide': True,
               'measures': (),
               'expanded_measures': (),
               'numerator': ('iso4217:USD',), 'denominator': ('shares',),
               'expanded_numerator': ((ISO, 'USD'),),
               'expanded_denominator': ((XBRLI, 'shares'),)}


def _row(name, is_divide, acc, facts):
    return {'name': name, 'is_divide': is_divide, 'accession': acc,
            'unit_ref': 'u1', 'facts': facts, 'facts_numeric_nonnil': facts}


ROWS = [_row('iso4217:USD', '0', 'acc-simple', 7),
        _row('iso4217:USDshares', '1', 'acc-divide', 3)]
PARSED = {'acc-simple': {'u1': SIMPLE_UNIT},
          'acc-divide': {'u1': DIVIDE_UNIT}}
CACHED = {'acc-simple', 'acc-divide'}


@pytest.fixture
def t():
    return C.tally(list(ROWS), dict(PARSED), set(CACHED))


# ---------------------------------------------------------------------------
# BOTH BRANCHES, AND THE SUBTOTALS THAT PROVE IT
# ---------------------------------------------------------------------------

def test_BOTH_branches_are_reached(t):
    """The defect this exists for: with the old divide-only query the simple
    table stayed empty and nothing said so."""
    assert t['observed_simple'] and t['observed'], (
        f"simple={len(t['observed_simple'])} divide={len(t['observed'])}")


def test_each_subtotal_is_exact(t):
    assert t['routes']['read_simple'] == {'declarations': 1, 'facts': 7}
    assert t['routes']['read_divide'] == {'declarations': 1, 'facts': 3}


def test_the_general_total_equals_simple_plus_divide(t):
    r = t['routes']
    assert r['read_simple']['declarations'] + r['read_divide']['declarations'] == 2
    assert r['read_simple']['facts'] + r['read_divide']['facts'] == 10
    # EVERY ROW IN EXACTLY ONE ROUTE, both numbers.
    assert sum(v['declarations'] for v in r.values()) == t['totals']['declarations']
    assert sum(v['facts'] for v in r.values()) == t['totals']['facts']


def test_the_tables_hold_exactly_what_the_subtotals_claim(t):
    """Summed FROM the tables, not from the counters that filled them — the
    only form of this check that can catch a declaration counted in one place
    and not the other."""
    held = lambda tbl: sum(v['declarations'] for seen in tbl.values()
                           for v in seen.values())
    assert held(t['observed_simple']) == t['routes']['read_simple']['declarations']
    assert held(t['observed']) == t['routes']['read_divide']['declarations']


def test_the_simple_row_is_classified_from_its_EXPANDED_measures(t):
    (_name, seen), = t['observed_simple'].items()
    (key, _tally), = seen.items()
    assert key == (('iso4217:USD',), ((ISO, 'USD'),))


# ---------------------------------------------------------------------------
# EACH DETECTOR MUST BITE ALONE
# ---------------------------------------------------------------------------

def test_dropping_the_simple_accounting_is_VISIBLE():
    """Feed only the divide row — as the old divide-only query effectively
    did — and the simple branch must be empty and its subtotal zero."""
    t = C.tally([ROWS[1]], dict(PARSED), set(CACHED))
    assert not t['observed_simple']
    assert t['routes']['read_simple'] == {'declarations': 0, 'facts': 0}
    assert t['routes']['read_divide']['declarations'] == 1


def test_an_UNKNOWN_is_divide_is_REJECTED_BEFORE_cache_filtering():
    """The row names an UNCACHED filing, so a check placed after the cache
    skip would never see it. That is exactly where the check used to sit."""
    with pytest.raises(SystemExit) as exc:
        C.tally([_row('x', 'maybe', 'never-cached', 1)], {}, set())
    assert 'unknown graph is_divide' in str(exc.value)


def test_the_all_row_flag_COUNTS_are_recorded(t):
    assert t['is_divide_counts'] == {'0': 1, '1': 1}


def test_a_graph_flag_that_DISAGREES_with_the_filing_is_recorded_not_filed():
    """Two independent statements about one declaration. If they disagree the
    declaration belongs in neither branch."""
    t = C.tally([_row('iso4217:USD', '1', 'acc-simple', 7)],
                dict(PARSED), set(CACHED))
    assert len(t['flag_disagreements']) == 1
    assert t['flag_disagreements'][0]['facts'] == 7
    assert not t['observed'] and not t['observed_simple']
    assert t['routes']['flag_disagreement'] == {'declarations': 1, 'facts': 7}


def test_a_REFUSED_DOCUMENT_gets_its_own_bucket_and_does_not_crash():
    """`prepare` returns no `units` key for a document it refuses, so the old
    `prepare(...)["units"]` raised KeyError and took the census down. At least
    one filing in the current population does this. It must be ACCOUNTED, not
    repaired and not special-cased."""
    refusal = 'document is not a well-formed XML Inline XBRL report'
    t = C.tally([_row('iso4217:USD', '0', 'acc-bad', 5)],
                {'acc-bad': refusal}, {'acc-bad'})
    assert t['document_refusals'] == {refusal: {'declarations': 1, 'facts': 5}}
    assert t['routes']['document_refused'] == {'declarations': 1, 'facts': 5}
    # AND IT IS NOT THE CACHE'S FAULT: the filing IS cached.
    assert t['routes']['uncached'] == {'declarations': 0, 'facts': 0}
    assert t['totals']['declarations'] == 1        # counted, never hidden


def test_a_refused_DOCUMENT_and_an_unusable_DECLARATION_cannot_COLLAPSE():
    """THE TWO BUCKETS MUST NOT MERGE. A document the parser refuses is NEUTRAL
    until its exact reason is adjudicated — `prepare()` also refuses on view
    disagreement, whose cause is not proven to be the filing's fault, so
    calling every refusal an expected source fact would decide the question in
    advance. An unusable declaration inside a filing that PARSED is a defect in
    this census.

    Collapsed into one bucket the receipt could never succeed: the known
    source refusal would permanently trip the rule that says every present-but-
    unread declaration is an implementation failure.
    """
    refusal = 'document is not a well-formed XML Inline XBRL report'
    t = C.tally([_row('iso4217:USD', '0', 'acc-bad', 5),
                 _row('iso4217:USD', '0', 'acc-missing-unit', 2)],
                {'acc-bad': refusal, 'acc-missing-unit': {}},
                {'acc-bad', 'acc-missing-unit'})
    assert t['document_refusals'] == {refusal: {'declarations': 1, 'facts': 5}}
    assert t['unreadable'] == {'absent': {'declarations': 1, 'facts': 2}}
    assert set(t['document_refusals']) & set(t['unreadable']) == set()
    assert t['routes']['document_refused']['declarations'] == 1
    assert t['routes']['declaration_unusable']['declarations'] == 1
    assert t['totals']['declarations'] == 2


def test_an_UNDOCUMENTED_prepare_shape_RAISES_rather_than_inventing_a_reason():
    """If `prepare` returns neither usable units nor its documented refusal
    that is a programmer/tool defect, not a fact about the filing. The earlier
    `.get(..., "document_refused")` fallback would have minted a reason and let
    the defect travel into the receipt looking like evidence."""
    with pytest.raises(SystemExit) as exc:
        C.tally([_row('iso4217:USD', '0', 'acc-weird', 1)],
                {'acc-weird': 12345}, {'acc-weird'})   # neither dict nor str
    assert 'neither units nor a documented refusal' in str(exc.value) or \
        'unknown' in str(exc.value)


def test_an_UNCACHED_filing_is_counted_but_not_read():
    t = C.tally([_row('iso4217:USD', '0', 'not-here', 4)], {}, set())
    assert t['routes']['uncached'] == {'declarations': 1, 'facts': 4}
    assert t['uncached_accessions'] == {'not-here'}
    assert not t['observed_simple'] and not t['observed']


# ---------------------------------------------------------------------------
# ALL SIX ROUTES AT ONCE — the shape no single-route test can prove
# ---------------------------------------------------------------------------

#: One row per route, every fact count DISTINCT. Identical counts would let a
#: row credited to the wrong route still balance every sum.
SIX = [_row('iso4217:USD',       '0', 'acc-simple',       11),   # read_simple
       _row('iso4217:USDshares', '1', 'acc-divide',       13),   # read_divide
       _row('iso4217:USD',       '0', 'acc-nowhere',      17),   # uncached
       _row('iso4217:USD',       '0', 'acc-bad',          19),   # doc refused
       _row('iso4217:USD',       '0', 'acc-missing-unit', 23),   # unusable
       _row('iso4217:USD',       '1', 'acc-simple',       29)]   # flag clash
REFUSAL = 'document is not a well-formed XML Inline XBRL report'
SIX_PARSED = {'acc-simple': {'u1': SIMPLE_UNIT},
              'acc-divide': {'u1': DIVIDE_UNIT},
              'acc-bad': REFUSAL,
              'acc-missing-unit': {}}
SIX_CACHED = {'acc-simple', 'acc-divide', 'acc-bad', 'acc-missing-unit'}


@pytest.fixture
def six():
    return C.tally(list(SIX), dict(SIX_PARSED), set(SIX_CACHED))


def test_EVERY_route_receives_its_own_row_and_nothing_else(six):
    """THE WHOLE MAPPING, not one route at a time. Six single-route tests can
    all pass while a seventh row silently lands in a route none of them looks
    at; this asserts the entire mapping in one comparison."""
    assert six['routes'] == {
        'read_simple':          {'declarations': 1, 'facts': 11},
        'read_divide':          {'declarations': 1, 'facts': 13},
        'uncached':             {'declarations': 1, 'facts': 17},
        'document_refused':     {'declarations': 1, 'facts': 19},
        'declaration_unusable': {'declarations': 1, 'facts': 23},
        'flag_disagreement':    {'declarations': 1, 'facts': 29}}


def test_the_six_routes_sum_to_the_INDEPENDENT_query_totals(six):
    """Both numbers, against totals accumulated on a different line of the
    loop — so a row in two routes, or in none, cannot balance."""
    r = six['routes']
    assert sum(v['declarations'] for v in r.values()) == 6 == \
        six['totals']['declarations']
    assert sum(v['facts'] for v in r.values()) == 11 + 13 + 17 + 19 + 23 + 29 \
        == six['totals']['facts']


def test_the_observed_tables_equal_the_two_READ_routes(six):
    """Summed from the tables themselves. With four non-read rows present, a
    classifier reached by a row that should have been routed elsewhere shows up
    here and nowhere else."""
    held = lambda tbl: {
        'declarations': sum(v['declarations'] for seen in tbl.values()
                            for v in seen.values()),
        'facts': sum(v['facts'] for seen in tbl.values()
                     for v in seen.values())}
    assert held(six['observed_simple']) == six['routes']['read_simple']
    assert held(six['observed']) == six['routes']['read_divide']


def test_the_uncached_ACCESSION_is_derived_not_assumed(six):
    """The scope statement names filings, and it must name the ones THIS run
    saw. A count copied from an older run was exactly the defect removed."""
    assert six['uncached_accessions'] == {'acc-nowhere'}


# ---------------------------------------------------------------------------
# THE RECEIPT — what `_emit` publishes, and what it must never conflate
# ---------------------------------------------------------------------------

TX = {'lastCommittedTxn': 7, 'databaseID': 'db-x'}


@pytest.fixture
def receipt(tmp_path, monkeypatch):
    """Four rows: the two read routes plus the two that used to be swept into
    the cache scope. `_emit` writes, so it gets a temporary path."""
    rows = [SIX[0], SIX[1], SIX[2], SIX[3]]          # simple/divide/uncached/refused
    t = C.tally(list(rows), dict(SIX_PARSED), set(SIX_CACHED))
    out = tmp_path / 'receipt.json'
    monkeypatch.setattr(C, 'OUT', str(out))
    C._emit(t, TX, dict(TX), True, SIX_CACHED)
    return json.loads(out.read_text())


def test_the_receipt_counts_BOTH_non_cache_reasons_as_unread(receipt):
    """Global coverage is a true statement about everything not read — the
    uncached row AND the refused document."""
    assert receipt['declarations'] == {'total': 4, 'read': 2, 'unread': 2}
    assert receipt['facts']['on_read_declarations'] == 24        # 11 + 13
    assert receipt['facts']['on_unread_declarations'] == 36      # 17 + 19


def test_the_SCOPE_LIMIT_names_the_CACHE_ONLY(receipt):
    """THE DEFECT THIS EXISTS FOR: the scope limit used to publish
    `total - read`, so a cached document refusal was reported as a filing
    missing from the cache. It must count the uncached route and nothing
    else — 1 declaration and 17 facts, NOT 2 and 36."""
    s = receipt['SCOPE_LIMIT']
    assert s['declarations_never_read'] == 1
    assert s['facts_on_them'] == 17
    assert s['uncached_accessions_seen'] == 1


def test_the_document_refusal_stays_SEPARATE_with_its_exact_reason(receipt):
    """Its own bucket, its own verbatim reason, its own counts — the only form
    in which it can be adjudicated afterwards rather than assumed."""
    assert receipt['document_refusals'] == {
        REFUSAL: {'declarations': 1, 'facts': 19}}
    assert receipt['routes']['document_refused'] == {'declarations': 1,
                                                     'facts': 19}
    assert receipt['declarations_present_but_unusable'] == {}


# ---------------------------------------------------------------------------
# MUTANTS — every check above must FAIL on a script that lost its subject
# ---------------------------------------------------------------------------
#
# A green test proves nothing until it is shown to go red. These break the
# script in a SCRATCH COPY, one edit at a time, and require the detector to
# notice. The live file is never touched.

def _mutant(tmp_path, old, new):
    """The census script with ONE exact substring replaced, loaded from a
    scratch copy. Its own `_REPO` guess is wrong from `/tmp`, which does not
    matter: importing the real module already put the repo root on `sys.path`,
    and `tally` opens no file when `parsed` is pre-populated."""
    src = open(C.__file__, encoding='utf-8').read()
    assert src.count(old) == 1, f'{old!r} appears {src.count(old)} times'
    path = tmp_path / 'mutant.py'
    path.write_text(src.replace(old, new), encoding='utf-8')
    spec = importlib.util.spec_from_file_location('mutant_827', str(path))
    mod = importlib.util.module_from_spec(spec)
    saved = list(sys.path)          # the mutant prepends its own two guesses,
    try:                            # one of which is `/`; leaking those would
        spec.loader.exec_module(mod)    # let this harness change how every
    finally:                            # later test in the process imports.
        sys.path[:] = saved
    return mod


ROUTES = ['read_simple', 'read_divide', 'uncached', 'document_refused',
          'declaration_unusable', 'flag_disagreement']


@pytest.mark.parametrize('name', ROUTES)
def test_DELETING_any_one_route_increment_is_CAUGHT(tmp_path, name, six):
    """One row is now accounted nowhere. Both halves of the proof must react:
    the mapping loses its entry AND the totals stop balancing."""
    m = _mutant(tmp_path, f'route("{name}", row)', 'pass')
    t = m.tally(list(SIX), dict(SIX_PARSED), set(SIX_CACHED))
    assert t['routes'] != six['routes']
    assert t['routes'][name] == {'declarations': 0, 'facts': 0}
    assert sum(v['declarations'] for v in t['routes'].values()) \
        != t['totals']['declarations']
    assert sum(v['facts'] for v in t['routes'].values()) != t['totals']['facts']


def test_MISROUTING_a_document_refusal_as_UNCACHED_is_CAUGHT(tmp_path):
    """THE MISATTRIBUTION THIS WHOLE CONTRACT EXISTS FOR — and the reason the
    sums alone are not enough. Every row is still counted exactly once, so BOTH
    totals still balance perfectly. Only the explicit mapping can tell that a
    cached document the parser refused has been reported as a filing missing
    from the cache."""
    m = _mutant(tmp_path, 'route("document_refused", row)',
                'route("uncached", row)')
    t = m.tally(list(SIX), dict(SIX_PARSED), set(SIX_CACHED))
    # THE SUMS ARE UNDISTURBED — proving they cannot detect this.
    assert sum(v['declarations'] for v in t['routes'].values()) \
        == t['totals']['declarations']
    assert sum(v['facts'] for v in t['routes'].values()) == t['totals']['facts']
    # THE MAPPING CATCHES IT.
    assert t['routes']['uncached'] == {'declarations': 2, 'facts': 17 + 19}
    assert t['routes']['document_refused'] == {'declarations': 0, 'facts': 0}


def test_publishing_GLOBAL_UNREAD_as_the_CACHE_SCOPE_is_CAUGHT(tmp_path):
    """The exact defect that was in the receipt: `total - read` published under
    a heading that says "not in our cache". Here it inflates 1 uncached
    declaration to 2 by absorbing the refused document."""
    m = _mutant(tmp_path,
                '"declarations_never_read": routes["uncached"]["declarations"],',
                '"declarations_never_read": unread,')
    t = m.tally([SIX[0], SIX[1], SIX[2], SIX[3]],
                dict(SIX_PARSED), set(SIX_CACHED))
    m.OUT = str(tmp_path / 'mutant_receipt.json')
    m._emit(t, TX, dict(TX), True, SIX_CACHED)
    scope = json.loads(open(m.OUT).read())['SCOPE_LIMIT']
    assert scope['declarations_never_read'] == 2        # the refusal swept in
    assert scope['uncached_accessions_seen'] == 1       # while only ONE exists
