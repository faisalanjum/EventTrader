#!/usr/bin/env python3
"""Coverage gate for DriverDesign.html.

The explainer must cover EVERY item extracted from the certified live files.
Extracts the inventory fresh each run, so a rule added to the law fails this
test until the page explains it.

  venv/bin/python3 -m pytest .claude/plans/Drivers/test_driver_design_coverage.py -q

Sources of truth (never the archive, never a WIP file):
  FINAL_DESIGN.md  -- sections + rule IDs
  STATUS_AND_HISTORY.md -- 42 supersessions, owner rulings, OD trail, retired list
"""
import re
import pathlib
import pytest

BASE = pathlib.Path(__file__).parent
FD = BASE / 'FinalDesign'
PAGE = BASE / 'DriverDesign.html'

FAMILIES = ('NAME', 'FS', 'UNIT', 'PER', 'MF', 'DU', 'XC', 'PIPE', 'FACT', 'OD')


def _num(x):
    m = re.search(r'-(\d+)', x)
    return (int(m.group(1)) if m else 0, x)


def _flat(html):
    """Page text with inline code tags dropped, so `foo` in the md matches <code>foo</code>."""
    return html.replace('<code>', '').replace('</code>', '')


@pytest.fixture(scope='module')
def page():
    return PAGE.read_text()


@pytest.fixture(scope='module')
def final():
    return (FD / 'FINAL_DESIGN.md').read_text()


@pytest.fixture(scope='module')
def status():
    return (FD / 'STATUS_AND_HISTORY.md').read_text()


def test_every_final_design_section_is_covered(page, final):
    """Each §N heading in the rulebook must appear on the page."""
    tops = re.findall(r'^## (\d+)\. ', final, re.M)
    assert len(tops) == 11, f'rulebook top sections changed: {len(tops)}'
    missing = [f'§{n}' for n in tops if f'§{n}' not in page]
    assert not missing, f'sections not covered: {missing}'


def test_every_rule_id_named_in_final_design_is_covered(page, final):
    """71 rule IDs at time of writing. A new one fails until explained."""
    ids = set()
    for m in re.finditer(r'\b(' + '|'.join(FAMILIES) + r')-(\d+[a-z]?)\b', final):
        ids.add(f'{m.group(1)}-{m.group(2)}')
    assert len(ids) >= 71, f'rule-ID count dropped to {len(ids)} — law changed?'
    missing = sorted(ids - {i for i in ids if i in page}, key=_num)
    assert not missing, f'rule IDs never mentioned on the page: {missing}'


def test_all_21_owner_decisions_covered(page, status):
    """OD-3 and OD-16 are named ONLY in STATUS -- the gap this test exists for."""
    ods = {f'OD-{n}' for n in re.findall(r'\bOD-(\d+)\b', status)}
    assert len(ods) == 21, f'expected OD-1..21, found {len(ods)}'
    missing = sorted(ods - {o for o in ods if re.search(rf'{o}\b', page)}, key=_num)
    assert not missing, f'owner decisions not covered: {missing}'


def test_all_42_supersession_rows_present(page, status):
    """Each row's subject text must appear -- the before/after ledger."""
    sec3 = re.search(r'^## 3\..*?(?=^## 4\.)', status, re.M | re.S).group(0)
    rows = re.findall(r'^\|\s*(\d+)\s*\|([^|]+)\|', sec3, re.M)
    assert len(rows) == 42, f'expected 42 supersession rows, found {len(rows)}'
    # the page renders the table generated from these rows: check subjects survived
    flat = _flat(page)
    missing = [n for n, subj in rows
               if subj.replace('`', '').strip().split(':')[0][:18] not in flat]
    assert not missing, f'supersession rows missing from page: {missing}'


def test_all_owner_rulings_covered(page, status):
    sec4 = re.search(r'^## 4\..*?(?=^## 5\.)', status, re.M | re.S).group(0)
    rulings = set(re.findall(r'\b(Q[1-5]|R[6-8])\b', sec4))
    assert rulings == {'Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'R6', 'R7', 'R8'}
    missing = [r for r in sorted(rulings) if not re.search(rf'>{r}<', page)]
    assert not missing, f'owner rulings not covered as chips: {missing}'


def test_all_13_retired_items_covered(page, status):
    ret = re.search(r'\*\*RETIRED \(never a production path\):\*\*(.*?)\n\n', status, re.S).group(1)
    items = [re.sub(r'\s+', ' ', x).strip(' .·\n') for x in ret.split('·')]
    assert len(items) == 13, f'expected 13 retired items, found {len(items)}'
    # match on a distinctive word from each entry
    keys = ['Guidance replay', 'fixed-vocabulary', 'eager-reuse', 'slice=total', 'alias layer',
            'long_range', 'gp_UNDEF', 'evhash16', 'FS-22', 'RavenPack', 'catalog-first',
            'SDK/OAuth', 'materialize-all']
    missing = [k for k in keys if k not in page]
    assert not missing, f'retired items not covered: {missing}'


def test_page_is_self_contained(page):
    """CSP-safe + portable: no external fetches of any kind."""
    bad = re.findall(r'(?:src|href)\s*=\s*["\'](https?:)?//', page)
    assert not bad, f'external references found: {bad}'


def test_page_never_cites_a_stale_source_as_law(page):
    """The WIP incremental-refresh file and the archive are evidence, never authority."""
    # It's fine to NAME the stale file (we do, to mark it stale) but it must be
    # labelled as not-law on the same page.
    if 'IncrementalRefresh_FinalDesign' in page:
        assert 'not</b> certified law' in page or 'not certified law' in page, \
            'the WIP file is cited without being marked non-authoritative'


def test_pinned_commit_recorded(page):
    assert '5d0bd41' in page, 'the page must record which certified commit it was built from'
