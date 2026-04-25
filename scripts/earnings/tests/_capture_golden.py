"""One-shot helper to capture renderer goldens. NOT a pytest test.

Usage (run from repo root):
    venv/bin/python -m scripts.earnings.tests._capture_golden full
    venv/bin/python -m scripts.earnings.tests._capture_golden sections
    venv/bin/python -m scripts.earnings.tests._capture_golden degraded
    venv/bin/python -m scripts.earnings.tests._capture_golden all
"""
from __future__ import annotations
import json
import hashlib
import sys
from pathlib import Path

# Repo root = parents[3] of this file:
# .../scripts/earnings/tests/_capture_golden.py → parents[3] = repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "earnings"))

from earnings_orchestrator import (
    render_bundle_text,
    _render_header,
    _render_results_and_expectations,
    _render_reference,
    _render_forward_guidance,
    _render_consensus_history,
    _render_prior_financials,
    _render_inter_quarter,
    _render_peer_earnings,
    _render_macro,
    _render_learning_context,
)

FIX = Path(__file__).parent / "fixtures"
BUNDLES = FIX / "golden_bundles"
FULL = FIX / "golden_renders" / "full"
SECTIONS = FIX / "golden_renders" / "sections"
DEGRADED = FIX / "golden_renders" / "degraded"

EVENTS = [
    ("CHRW", "Q4_FY2025"),
    ("AVGO", "Q3_FY2023"),
    ("AVGO", "Q4_FY2023"),
    ("CXM",  "Q4_FY2026"),
]

# (section_name, renderer_callable)
# Note: lessons handled separately because _render_learning_context returns tuple.
SECTION_RENDERERS = [
    ("header",        _render_header),
    ("results",       _render_results_and_expectations),
    ("guidance",      _render_forward_guidance),
    ("consensus",     _render_consensus_history),
    ("financials",    _render_prior_financials),
    ("inter_quarter", _render_inter_quarter),
    ("peers",         _render_peer_earnings),
    ("macro",         _render_macro),
    ("reference",     _render_reference),
]


def _load_bundle(ticker: str, quarter: str) -> dict:
    path = BUNDLES / f"{ticker}_{quarter}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def capture_full() -> None:
    FULL.mkdir(parents=True, exist_ok=True)
    for ticker, quarter in EVENTS:
        bundle = _load_bundle(ticker, quarter)
        rendered = render_bundle_text(bundle)
        (FULL / f"{ticker}_{quarter}.txt").write_text(rendered, encoding="utf-8")
        sha = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        (FULL / f"{ticker}_{quarter}.sha256").write_text(sha + "\n", encoding="utf-8")
        print(f"  full: {ticker} {quarter} → {len(rendered)} B")


def capture_sections() -> None:
    for section, _renderer in SECTION_RENDERERS:
        (SECTIONS / section).mkdir(parents=True, exist_ok=True)
    (SECTIONS / "lessons").mkdir(parents=True, exist_ok=True)

    for ticker, quarter in EVENTS:
        bundle = _load_bundle(ticker, quarter)
        for section, renderer in SECTION_RENDERERS:
            output = renderer(bundle)
            (SECTIONS / section / f"{ticker}_{quarter}.txt").write_text(
                output, encoding="utf-8"
            )
        # Lessons section: capture both the rendered text AND the ordered list
        lc = bundle.get("learning_context") or {}
        text, ordered = _render_learning_context(lc)
        (SECTIONS / "lessons" / f"{ticker}_{quarter}.txt").write_text(
            text, encoding="utf-8"
        )
        # Save ordered list as JSON for tuple-equality check.
        # Use indent=2 + ensure_ascii=False for human-readable diffs.
        (SECTIONS / "lessons" / f"{ticker}_{quarter}.json").write_text(
            json.dumps(ordered, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  sections: {ticker} {quarter}")


def capture_degraded() -> None:
    """Imports degraded fixture builders and captures their renderer output."""
    sys.path.insert(0, str(Path(__file__).parent))
    from _degraded_fixtures import DEGRADED_BUILDERS

    DEGRADED.mkdir(parents=True, exist_ok=True)
    for name, build in DEGRADED_BUILDERS:
        bundle = build()
        rendered = render_bundle_text(bundle)
        (DEGRADED / f"{name}.txt").write_text(rendered, encoding="utf-8")
        print(f"  degraded: {name} → {len(rendered)} B")


def main(arg: str) -> None:
    if arg == "full":
        capture_full()
    elif arg == "sections":
        capture_sections()
    elif arg == "degraded":
        capture_degraded()
    elif arg == "all":
        capture_full()
        capture_sections()
        capture_degraded()
    else:
        print(f"Usage: {sys.argv[0]} {{full|sections|degraded|all}}")
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
