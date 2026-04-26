"""Surface inventory — every public name + private cross-export must be reachable.

This test is the SHIM CONTRACT — it codifies which symbols MUST survive the move.
Stages 2-13 each add bindings (via shim re-exports); none of them can ever
REMOVE a symbol from any path listed here.
"""
from __future__ import annotations
import importlib
import sys
from pathlib import Path
import pytest

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
sys.path.insert(0, str(THIS_DIR.parent.parent / ".claude/skills/earnings-orchestrator/scripts"))


# Module name -> {public: [...], private_exports: [...]}
EXPECTED_SURFACE: dict[str, dict[str, list[str]]] = {
    "build_consensus": {
        "public": ["build_consensus", "main"],
        "private_exports": ["_parse_iso", "_normalize_session"],
    },
    "build_prior_financials": {
        "public": ["build_prior_financials", "classify_period", "is_target_period",
                   "dedupe_facts", "main"],
        "private_exports": ["_parse_value"],
    },
    "macro_snapshot": {
        "public": ["build_macro_snapshot", "render_text", "main"],
        "private_exports": [],
    },
    "peer_earnings_snapshot": {
        "public": ["build_peer_earnings_snapshot", "render_text", "main"],
        "private_exports": ["_parse_dt_for_pit"],
    },
    "warmup_cache": {
        "public": ["build_8k_packet", "build_guidance_history",
                   "build_inter_quarter_context", "render_guidance_text",
                   "render_inter_quarter_text", "run_warmup", "run_transcript",
                   "run_mda", "run_8k", "main"],
        "private_exports": ["_parse_dt_for_pit", "_run_v2_regression_tests"],
    },
    "builder_adapters": {
        "public": ["build_8k_packet", "build_guidance_history",
                   "build_inter_quarter_context", "build_peer_earnings_snapshot",
                   "build_macro_snapshot", "build_consensus", "build_prior_financials"],
        "private_exports": [],
    },
}


@pytest.mark.parametrize("modname,spec", EXPECTED_SURFACE.items())
def test_module_exposes_expected_surface(modname, spec):
    mod = importlib.import_module(modname)
    for sym in spec["public"] + spec["private_exports"]:
        assert hasattr(mod, sym), f"{modname} missing required symbol {sym}"


@pytest.mark.parametrize("modname,spec", EXPECTED_SURFACE.items())
def test_no_unexpected_public_names_lost(modname, spec):
    mod = importlib.import_module(modname)
    for sym in spec["public"]:
        obj = getattr(mod, sym)
        assert obj is not None, f"{modname}.{sym} is None — shim missing real binding?"
