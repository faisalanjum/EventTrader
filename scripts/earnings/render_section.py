#!/usr/bin/env python3
"""Render one (or all) prediction bundle sections live.

Usage: venv/bin/python scripts/earnings/render_section.py <TICKER> <ACCESSION> [SECTION] [--live]
SECTION (default: all):
    header | results | guidance | consensus | prior | iq | peers | macro | ref | lessons | all

Default = historical PIT (mirrors orchestrator --predict). --live bypasses PIT.
"""
import sys
from pathlib import Path

# parents[2] = repo root; parents[1] = scripts/; parents[0] = scripts/earnings/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))                          # for `scripts.earnings.builders` qualified imports
sys.path.insert(0, str(_PROJECT_ROOT / "scripts/earnings"))     # for bare `quarter_identity`, `earnings_orchestrator` etc.

from quarter_identity import resolve_quarter_info
from scripts.earnings.builders import (
    build_consensus, build_8k_packet, build_guidance_history,
    build_prior_financials, build_inter_quarter_context,
    build_peer_earnings_snapshot, build_macro_snapshot,
)
from earnings_orchestrator import (
    build_prediction_bundle, build_learning_context, render_bundle_text,
    _render_header, _render_results_and_expectations, _render_forward_guidance,
    _render_consensus_history, _render_prior_financials, _render_inter_quarter,
    _render_peer_earnings, _render_macro, _render_reference, _render_learning_context,
    _lookup_company_sector,
)

SPEC = {
    "header":    ([],                          [],                              _render_header),
    "results":   (["consensus", "8k_packet"],  [build_consensus, build_8k_packet], _render_results_and_expectations),
    "guidance":  (["guidance_history"],        [build_guidance_history],        _render_forward_guidance),
    "consensus": (["consensus"],               [build_consensus],               _render_consensus_history),
    "prior":     (["prior_financials"],        [build_prior_financials],        _render_prior_financials),
    "iq":        (["inter_quarter_context"],   [build_inter_quarter_context],   _render_inter_quarter),
    "peers":     (["peer_earnings_snapshot"],  [build_peer_earnings_snapshot],  _render_peer_earnings),
    "macro":     (["macro_snapshot"],          [build_macro_snapshot],          _render_macro),
    "ref":       (["8k_packet"],               [build_8k_packet],               _render_reference),
}

live_mode = "--live" in sys.argv
positional = [a for a in sys.argv[1:] if a != "--live"]
ticker, accession = positional[0], positional[1]
section = positional[2] if len(positional) >= 3 else "all"

qi = resolve_quarter_info(ticker, accession)
pit = None if live_mode else qi["filed_8k"]

if section == "all":
    print(render_bundle_text(build_prediction_bundle(ticker, qi, pit)))
elif section == "lessons":
    lc = build_learning_context(ticker, sector=_lookup_company_sector(ticker), pit_cutoff=pit)
    text, _ = _render_learning_context(lc)
    print(text)
else:
    keys, builders, render_fn = SPEC[section]
    bundle = {"ticker": ticker, "quarter_info": qi, "pit_cutoff": pit, "builder_errors": {}}
    for k, b in zip(keys, builders):
        bundle[k] = b(ticker, qi, pit, f"/tmp/{k}.json")
    print(render_fn(bundle))
