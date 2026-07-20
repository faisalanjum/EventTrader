"""THE NEUTRAL-BOUNDARY TEST (WP2 plan v4 step 2 — authored RED-first per the lock-correction
order; committed ONLY in the commit that turns it green with the routes).

Proves the boundary at RUNTIME, not import time (lazy in-function imports are a real pattern
in this codebase): a subprocess imports the ACTUAL locator entrypoint, EXECUTES one minimal
R1 call (XBRL-carrying source payload) and one minimal R2 call (text source + value-known
hint), then sweeps sys.modules — NO loaded module may live under scripts/driver_seed/ (the
fiscal.ai/channel side). Path-based sweep = general law, no module name list.

    venv/bin/python -m pytest driver/relocation/test_neutral_boundary.py -q
"""
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

_SCRIPT = r'''
import json, os, sys
HERE = %r
sys.path.insert(0, HERE)
import locator

anchor = {
    "source_id": "SYN-PRIOR", "company": "SYNCIK", "driver": "revenue",
    "slice": "", "measurement": "", "series_unit": "m_usd", "time_type": "duration",
    "fact_type": "metric", "wording": ("Total revenue $ 6,707",), "concept_clue": None,
}
xbrl_src = {"source_id": "SYN-SRC-X", "source_type": "10k",
            "xbrls": [json.dumps({"Revenues": [{"value": "6707000000",
                      "period": {"startDate": "2024-01-01", "endDate": "2024-12-31"},
                      "unitRef": "U_USD"}]})],
            "texts": ["Total revenue $ 6,707 for the year"]}
r1 = locator.locate(anchor, xbrl_src)                      # R1: own-source XBRL enumeration
assert isinstance(r1, dict) and "items" in r1 and "status" in r1, r1
text_src = {"source_id": "SYN-SRC-T", "source_type": "8k", "xbrls": [],
            "texts": ["Total revenue was $ 6,707 million in the quarter"]}
r2 = locator.locate(anchor, text_src,
                    hints={"source_id": "SYN-SRC-T", "value": 6707000000})   # R2: known-value
assert isinstance(r2, dict) and "items" in r2 and "status" in r2, r2

breaches = sorted({m.__name__ for m in list(sys.modules.values())
                   if getattr(m, "__file__", None)
                   and ("scripts" + os.sep + "driver_seed") in m.__file__})
assert not breaches, f"fiscal/channel code LOADED by the neutral locator: {breaches}"
print("BOUNDARY-OK: both routes executed; zero fiscal/channel modules loaded")
''' % _HERE


def test_neutral_boundary_executes_both_routes_with_zero_channel_imports():
    r = subprocess.run([sys.executable, "-c", _SCRIPT], capture_output=True, text=True,
                       cwd=_HERE, timeout=120)
    assert r.returncode == 0, f"boundary subprocess failed:\n{r.stdout}\n{r.stderr}"
    assert "BOUNDARY-OK" in r.stdout, r.stdout
