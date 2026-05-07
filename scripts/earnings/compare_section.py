#!/usr/bin/env python3
"""Show JSON source + rendered output for one bundle section, side-by-side.

Usage: venv/bin/python scripts/earnings/compare_section.py <TICKER> <ACCESSION> [SECTION] [--live]

SECTION (default: header):
    header | results | guidance | consensus | prior | iq | peers | macro | ref | lessons | all

Default = historical PIT (PIT cutoff = filed_8k). Mirrors orchestrator's --predict
default per the T1.5a fix in .claude/plans/learner.md §🔥. This is what the
predictor actually saw for this event.

--live   = bypass PIT (PIT=None). All builders run in live mode. Use only if
           you want to audit lesson-corpus drift or live-mode behavior.

Pipe big sections to a pager:
    venv/bin/python scripts/earnings/compare_section.py AVGO 0001730168-23-000093 iq | less

─────────────────────────────────────────────────────────────────────────────
Related: save the full RENDERED_BUNDLE_PATH for a new accession (no SDK call)
─────────────────────────────────────────────────────────────────────────────

To inspect the exact text the predictor would read for a new accession, run
the orchestrator with --save (omit --predict so no SDK call fires):

    cd /home/faisal/EventMarketDB
    python scripts/earnings/earnings_orchestrator.py TICKER ACCESSION --save

Default output (per get_prediction_paths() in earnings_orchestrator.py):
    earnings-analysis/Companies/{TICKER}/events/{Q_label}/prediction/
      ├── context_bundle.json          # raw bundle JSON
      └── context_bundle_rendered.txt  # what the predictor reads

Mode flags (mutually exclusive):
    --pit 2025-02-26T17:00:00-05:00    historical PIT-safe
    --live                              live mode (no PIT gate)
    (omit both with --save only)        defaults to live

Custom location:
    --save-dir /tmp/myrun               redirect both files there

Example (historical PIT for AVGO Q4 FY2023, filed 2023-12-07 post-market):
    python scripts/earnings/earnings_orchestrator.py AVGO 0001730168-23-000093 \
        --save --pit 2023-12-07T16:30:00-05:00
"""
import sys, json
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
    "results":   (["consensus", "8k_packet"],    [build_consensus, build_8k_packet], _render_results_and_expectations),
    "guidance":  (["guidance_history"],          [build_guidance_history],        _render_forward_guidance),
    "consensus": (["consensus"],                 [build_consensus],               _render_consensus_history),
    "prior":     (["prior_financials"],          [build_prior_financials],        _render_prior_financials),
    "iq":        (["inter_quarter_context"],     [build_inter_quarter_context],   _render_inter_quarter),
    "peers":     (["peer_earnings_snapshot"],    [build_peer_earnings_snapshot],  _render_peer_earnings),
    "macro":     (["macro_snapshot"],            [build_macro_snapshot],          _render_macro),
    "ref":       (["8k_packet"],                 [build_8k_packet],               _render_reference),
}

def banner(t):
    bar = "=" * 72
    return f"\n{bar}\n  {t}\n{bar}"

def jdump(o):
    return json.dumps(o, indent=2, default=str, ensure_ascii=False)

live_mode = "--live" in sys.argv
positional = [a for a in sys.argv[1:] if a != "--live"]
ticker, accession = positional[0], positional[1]
section = positional[2] if len(positional) >= 3 else "header"

qi = resolve_quarter_info(ticker, accession)
pit = None if live_mode else qi["filed_8k"]

if section == "all":
    bundle = build_prediction_bundle(ticker, qi, pit)
    print(banner(f"JSON  full bundle  ({ticker} {qi['quarter_label']})"))
    print(jdump(bundle))
    print(banner("RENDERED  full bundle"))
    print(render_bundle_text(bundle))
elif section == "header":
    bundle = {"ticker": ticker, "quarter_info": qi, "pit_cutoff": pit}
    print(banner("JSON  ticker + quarter_info + pit_cutoff"))
    print(jdump(bundle))
    print(banner("RENDERED  §1 Header"))
    print(_render_header(bundle))
elif section == "lessons":
    lc = build_learning_context(ticker, sector=_lookup_company_sector(ticker), pit_cutoff=pit)
    print(banner(f"JSON  bundle.learning_context  ({ticker}, PIT={pit})"))
    print(jdump(lc))
    print(banner("RENDERED  §10 Prior Lessons"))
    text, _ = _render_learning_context(lc)
    print(text)
else:
    keys, builders, render_fn = SPEC[section]
    bundle = {"ticker": ticker, "quarter_info": qi, "pit_cutoff": pit, "builder_errors": {}}
    for k, b in zip(keys, builders):
        bundle[k] = b(ticker, qi, pit, f"/tmp/{k}.json")
    for k in keys:
        print(banner(f"JSON  bundle.{k}"))
        print(jdump(bundle[k]))
    print(banner(f"RENDERED  §{section}"))
    print(render_fn(bundle))
