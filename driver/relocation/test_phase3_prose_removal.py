"""Phase-3 pin (RED-first, reviewer order 2026-07-22): after the semantic prose
machinery is deleted, UNSUPPORTED PROSE must safely return no_proven_match —
never bind from flattened text. Routes B/C remain inactive.

The fixture is the route suite's own GREEN donor (test_1): a source the legacy
R1 prose walk binds TODAY (4 items) — this pin is RED until the cut lands."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import locator as LOC

ANCHOR = {
    "source_id": "SYN-PRIOR", "company": "C1", "driver": "revenue", "slice": "",
    "measurement": "", "series_unit": "m_usd", "time_type": "duration",
    "fact_type": "metric", "wording": ("Total widget revenue",),
    "concept_clue": None,
}


def test_unsupported_prose_returns_no_proven_match():
    xb = json.dumps({'us-gaap:Revenues': [
        {'value': '4000000000',
         'period': {'startDate': '2024-01-01', 'endDate': '2024-12-31'},
         'unitRef': 'U_USD'}]})
    source = {'source_id': 'SYN-SRC-1', 'source_type': '10k', 'xbrls': [xb],
              'texts': ["Total widget revenue was 4,000,000,000 for the year."]}
    out = LOC.locate(ANCHOR, source)
    assert out['items'] == [], out
    assert out['status'] == 'no_proven_match', out
