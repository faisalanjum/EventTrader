"""Focused M4 pins (combined-audit corrective item 7, 2026-07-22): visible vs
hidden text · leaf-div non-overlapping blocks · transcript grouping · 100K chunk
arithmetic · no-exhibit bodies included · PDFs listed as deferred.

    venv/bin/python -m pytest scripts/driver_seed/relocate_probe/phase2/test_m4_reader_residual.py -q
"""
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..')))

from driver.relocation import inline_html as IH
from m4_reader_residual import scan, MAX_CHARS, MAX_CASES

OUT = os.path.join(_HERE, 'm4_reader_residual.json')
CACHE = os.path.join(_HERE, '..', 'exhibit_html_cache')


def test_caps_match_batch_groups():
    sys.path.insert(0, os.path.join(_HERE, '..'))
    import batch_groups
    assert (MAX_CASES, MAX_CHARS) == (batch_groups.MAX_CASES,
                                      batch_groups.MAX_CHARS) == (8, 100_000)


def test_hidden_text_excluded_and_leaf_div_counted():
    import tempfile
    html = ('<div><div>Revenue was 5 million dollars this quarter and more '
            'words here</div><div style="display:none">HIDDEN 999</div>'
            '<p>plain 7 text</p></div>')
    p = os.path.join(tempfile.mkdtemp(), 'x.htm')
    open(p, 'w').write(html)
    rec = scan(p)
    # leaf blocks: inner div + p (outer div contains both → not a leaf)
    assert rec['prose_struct_blocks'] == 2
    assert rec['prose_lower_blocks'] == 1          # p only in the lower bound
    assert 'HIDDEN' not in str(rec)
    assert rec['prose_struct_numeric_chars'] > 0


def test_leaf_blocks_non_overlapping_on_real_file():
    rec = scan(os.path.join(CACHE, '0000002488-23-000074__EX-99.1.htm'))
    # leaves cannot double-count: structural chars never exceed the visible
    # non-table upper bound
    assert rec['prose_struct_chars'] <= rec['nontable_visible_chars_upper'] \
        + rec['table_row_chars']
    assert rec['prose_lower_blocks'] <= rec['prose_struct_blocks']
    assert rec['prose_lower_chars'] <= rec['prose_struct_chars']


def test_chunk_arithmetic_ceil_law():
    assert max(1, math.ceil(1 / MAX_CHARS)) == 1
    assert max(1, math.ceil(100_000 / MAX_CHARS)) == 1
    assert max(1, math.ceil(100_001 / MAX_CHARS)) == 2
    assert max(1, math.ceil(399_999 / MAX_CHARS)) == 4


def test_output_includes_noexhibit_bodies_and_transcript_grouping():
    o = json.load(open(OUT))
    assert o['8k_noexhibit_bodies']['events'] == 573
    assert o['8k_noexhibit_bodies']['bodies_on_disk'] > 0
    assert o['transcripts']['transcripts_with_numbers'] > 9000
    assert o['transcripts']['min_text_chunks_at_100k'] >= \
        o['transcripts']['transcripts_with_numbers']


def test_pdfs_listed_deferred_and_no_invented_output_tokens():
    o = json.load(open(OUT))
    assert o['pdfs']['count'] == 38 and 'DEFERRED' in o['pdfs']['status']
    assert 'UNAVAILABLE until Phase 5' in o['anchors_and_output_side']
    assert '100-300' not in json.dumps(o)
    assert 'UNEARNED_THEORETICAL_CEILING' in json.dumps(o)
