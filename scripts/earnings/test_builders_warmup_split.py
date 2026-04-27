"""Contract harness for the warmup_cache → 3-domain split.

Pre-split goldens captured in Stage 0 are compared against post-split
builder output to prove structural equality (Python dict `==` after `json.loads`,
modulo the stripped `assembled_at` field — NOT raw byte equality, since on-disk
JSON byte order depends on the encoder's settings).

Identity tests prove that every relocated symbol resolves to the SAME
Python object via `is` from BOTH the warmup_cache facade AND the canonical
domain module.

Tests are gated by intrinsic stage state (no marker file) so they activate
as the split progresses:
  - Stage-0 tests: harness loads, fixtures present, no-back-import static check
  - Stage-1.2 tests: skip until eight_k_packet.py exists, then activate
  - Stage-2.2 tests: skip until guidance_history.py exists, then activate
  - Stage-3.2 tests: skip until inter_quarter_context.py exists, then activate
  - Stage-5 tests: no-redefine assertion gated on `_all_reexport_blocks_present()` (activates at Stage 3.2 cutover, fails loudly on regression — does NOT self-disable on def re-introduction); size assertion + goldens gated on `_all_cutovers_complete()`
"""
from __future__ import annotations
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
FIXTURES = REPO / "scripts/earnings/builders/test_fixtures/warmup_split"
WC_PATH = REPO / "scripts/earnings/builders/warmup_cache.py"

pytestmark = pytest.mark.builders


# ── Cutover-detection helpers (shared by every stage-gated test) ────────
#
# CRITICAL: these are SKIP gates only. They detect whether a stage has happened
# yet — they do NOT replace the actual assertions. The assertion side of each
# gated test must FAIL loudly when the contract is violated, not silently skip.

def _wc_still_defines(sym: str) -> bool:
    """True iff warmup_cache.py still contains `def {sym}(` or `{sym} = ` at column 0.
    Used to skip facade-vs-canonical identity tests during COPY-only stages where
    both modules legitimately have their own def (different objects by design)."""
    if not WC_PATH.exists():
        return False
    src = WC_PATH.read_text()
    return bool(re.search(rf'^def {re.escape(sym)}\(|^{re.escape(sym)} = ',
                          src, re.MULTILINE))


def _domain_modules_exist() -> bool:
    """Skip-gate: all 3 domain modules created (Stages 1.1, 2.1, 3.1 done)."""
    builders = REPO / "scripts/earnings/builders"
    return all((builders / f"{m}.py").exists()
               for m in ("eight_k_packet", "guidance_history", "inter_quarter_context"))


def _all_cutovers_complete() -> bool:
    """Skip-gate: all 3 build_* defs REMOVED from warmup_cache.py (Stages 1.2/2.2/3.2 done).
    The static-no-redefine ASSERTION is separate (test_facade_has_no_relocated_function_defs)
    — it MUST fail loudly if a def reappears, not silently skip."""
    if not _domain_modules_exist() or not WC_PATH.exists():
        return False
    src = WC_PATH.read_text()
    return not any(f"def {fn}(" in src for fn in
                   ("build_8k_packet", "build_guidance_history", "build_inter_quarter_context"))


def _all_reexport_blocks_present() -> bool:
    """Skip-gate for the static no-redefine assertion. Detects "all 3 cutover commits
    have landed" by checking warmup_cache.py contains all 3 `from .X import` re-export
    blocks. Independent of whether someone later re-introduces a def — so it does NOT
    self-disable on regression. Use this for test_facade_has_no_relocated_function_defs;
    use _all_cutovers_complete() (which DOES short-circuit on def-presence) for skip-gates
    where the test is verifying byte-output (goldens) rather than absence-of-def."""
    if not WC_PATH.exists():
        return False
    src = WC_PATH.read_text()
    return all(f"from .{m} import" in src for m in
               ("eight_k_packet", "guidance_history", "inter_quarter_context"))


# ── Stage 0: harness sanity ─────────────────────────────────────────────

def test_fixtures_present():
    assert (FIXTURES / "8k_packet_FIVE.json").exists()
    assert (FIXTURES / "guidance_history_FIVE.json").exists()
    assert (FIXTURES / "inter_quarter_context_FIVE.json").exists()


def test_no_warmup_cache_back_imports():
    """The new domain modules MUST NOT import warmup_cache (cycle prevention).

    Catches:
      - `import warmup_cache` (and `import warmup_cache as wc`)
      - `from warmup_cache import X`
      - `from .warmup_cache import X`
      - `from scripts.earnings.builders.warmup_cache import X`
      - `from . import warmup_cache` (alias-style)
      - `from scripts.earnings.builders import warmup_cache` (alias-style)
    """
    targets = [
        REPO / "scripts/earnings/builders/eight_k_packet.py",
        REPO / "scripts/earnings/builders/guidance_history.py",
        REPO / "scripts/earnings/builders/inter_quarter_context.py",
    ]
    any_present = False
    for path in targets:
        if not path.exists():
            continue
        any_present = True
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and "warmup_cache" in node.module:
                    pytest.fail(
                        f"{path.name}: ImportFrom module references warmup_cache "
                        f"({node.module}) — cycle"
                    )
                # ALSO check the names imported (`from . import warmup_cache`)
                for alias in node.names:
                    if "warmup_cache" in alias.name:
                        pytest.fail(
                            f"{path.name}: ImportFrom imports name 'warmup_cache' "
                            f"(from {node.module or '.'} import {alias.name}) — cycle"
                        )
            if isinstance(node, ast.Import):
                for n in node.names:
                    if "warmup_cache" in n.name:
                        pytest.fail(
                            f"{path.name}: import statement references warmup_cache "
                            f"({n.name}) — cycle"
                        )
    if not any_present:
        pytest.skip("no domain modules exist yet (pre-Stage-1.1)")


def test_no_cross_domain_imports():
    """The 3 domain modules MUST be PEERS — none imports another. Cross-imports
    create silent coupling that bypasses the facade-only contract. See §10.18.

    Catches `from .guidance_history import _format_value` placed in
    inter_quarter_context.py (or any analogous cross-coupling), AND alias-style
    `from . import guidance_history`."""
    targets = ["eight_k_packet", "guidance_history", "inter_quarter_context"]
    any_present = False
    for me in targets:
        path = REPO / f"scripts/earnings/builders/{me}.py"
        if not path.exists():
            continue
        any_present = True
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    for other in targets:
                        if other != me and other in node.module:
                            pytest.fail(
                                f"{me}.py imports from {node.module} — domain "
                                f"modules must be peers; share via the warmup_cache "
                                f"facade only"
                            )
                for alias in node.names:
                    for other in targets:
                        if other != me and alias.name == other:
                            pytest.fail(
                                f"{me}.py: ImportFrom imports '{alias.name}' "
                                f"(from {node.module or '.'}) — domain modules "
                                f"must be peers"
                            )
    if not any_present:
        pytest.skip("no domain modules exist yet (pre-Stage-1.1)")


# ── Stage 1.2: eight_k_packet identity + golden ─────────────────────────

_EIGHTK_SYMBOLS = [
    "build_8k_packet", "_fetch_8k_core",
    "QUERY_4J", "QUERY_4K", "QUERY_4G_META", "QUERY_4K_OTHER_PREVIEW", "QUERY_4F",
]


@pytest.mark.parametrize("sym", _EIGHTK_SYMBOLS)
def test_facade_reexports_match_eight_k_packet_canonical(sym):
    try:
        from scripts.earnings.builders import eight_k_packet as ek
    except ImportError:
        pytest.skip("eight_k_packet not yet created (pre-Stage-1.1)")
    # CRITICAL CUTOVER GATE: in Stage 1.1 (COPY-only), warmup_cache still has its
    # own `def build_8k_packet` etc. Both modules legitimately have their own
    # def — they're different objects BY DESIGN. The identity assertion only
    # makes sense AFTER Stage 1.2 cutover removes warmup_cache's local def.
    if _wc_still_defines(sym):
        pytest.skip(f"warmup_cache.py still defines {sym} — pre-Stage-1.2 cutover")
    from scripts.earnings.builders import warmup_cache as wc
    facade = getattr(wc, sym, None)
    canonical = getattr(ek, sym, None)
    if canonical is None:
        pytest.skip(f"{sym} not yet in eight_k_packet (pre-Stage-1.1)")
    if facade is None:
        pytest.fail(
            f"warmup_cache.{sym} missing — facade must re-export every "
            f"relocated symbol (Stage 1.2 must add the import block)"
        )
    assert facade is canonical, (
        f"IDENTITY BROKEN: warmup_cache.{sym} ({id(facade)}) is not "
        f"eight_k_packet.{sym} ({id(canonical)}) — facade must use direct "
        f"`from .eight_k_packet import {sym}`, NOT a wrapper function"
    )


# ── Stage 2.2: guidance_history identity ────────────────────────────────

_GUIDANCE_SYMBOLS = [
    "build_guidance_history", "render_guidance_text", "resolve_unit_groups",
    "_format_value", "_extract_given_day", "_normalize_qualitative",
    "_SOURCE_PRIORITY",
    "QUERY_GUIDANCE_HISTORY", "QUERY_GUIDANCE_HISTORY_PIT",
    "_run_v2_regression_tests",
]


@pytest.mark.parametrize("sym", _GUIDANCE_SYMBOLS)
def test_facade_reexports_match_guidance_history_canonical(sym):
    try:
        from scripts.earnings.builders import guidance_history as gh
    except ImportError:
        pytest.skip("guidance_history not yet created (pre-Stage-2.1)")
    if _wc_still_defines(sym):
        pytest.skip(f"warmup_cache.py still defines {sym} — pre-Stage-2.2 cutover")
    from scripts.earnings.builders import warmup_cache as wc
    facade = getattr(wc, sym, None)
    canonical = getattr(gh, sym, None)
    if canonical is None:
        pytest.skip(f"{sym} not yet in guidance_history (pre-Stage-2.1)")
    if facade is None:
        pytest.fail(f"warmup_cache.{sym} missing after Stage 2.2 cutover")
    assert facade is canonical, (
        f"IDENTITY BROKEN: warmup_cache.{sym} is not guidance_history.{sym}"
    )


# ── Stage 3.2: inter_quarter_context identity ───────────────────────────

_IQ_SYMBOLS = [
    "build_inter_quarter_context", "render_inter_quarter_text",
    "_parse_dt_for_pit", "_is_price_pit_safe", "_build_forward_returns",
    "_iq_parse_json_field", "_norm_ret", "_fmt_vol", "_fmt_txn",
    "_safe_adj", "_event_ref", "_day_from_ts",
    "_cutoff_boundary_price_role", "_best_safe_horizon", "_report_summary",
    "_render_window_label_news", "_render_window_label_filing",
    "_render_horizon_line_filing", "_render_news_react_line",
    "QUERY_IQ_PRICES", "QUERY_IQ_NEWS", "QUERY_IQ_FILINGS",
    "QUERY_IQ_DIVIDENDS", "QUERY_IQ_SPLITS", "QUERY_IQ_COMPANY_CONTEXT",
]


@pytest.mark.parametrize("sym", _IQ_SYMBOLS)
def test_facade_reexports_match_inter_quarter_context_canonical(sym):
    try:
        from scripts.earnings.builders import inter_quarter_context as iq
    except ImportError:
        pytest.skip("inter_quarter_context not yet created (pre-Stage-3.1)")
    if _wc_still_defines(sym):
        pytest.skip(f"warmup_cache.py still defines {sym} — pre-Stage-3.2 cutover")
    from scripts.earnings.builders import warmup_cache as wc
    facade = getattr(wc, sym, None)
    canonical = getattr(iq, sym, None)
    if canonical is None:
        pytest.skip(f"{sym} not yet in inter_quarter_context (pre-Stage-3.1)")
    if facade is None:
        pytest.fail(f"warmup_cache.{sym} missing after Stage 3.2 cutover")
    assert facade is canonical, (
        f"IDENTITY BROKEN: warmup_cache.{sym} is not inter_quarter_context.{sym}"
    )


# NOTE: Stage 5 gating now uses TWO different helpers depending on the assertion's
# purpose:
#   - `_all_reexport_blocks_present()` for the no-redefine guard. Activates at
#     Stage 3.2 cutover (when all 3 `from .X import` blocks land in warmup_cache.py)
#     and KEEPS firing on regression (re-export blocks remain even if a stray def
#     is added back), so the assertion fails LOUDLY on def re-introduction.
#   - `_all_cutovers_complete()` for the facade-size assertion + live goldens
#     (these tests need the absence-of-build_*-defs as a real precondition).
# We previously had a single helper `_stage5_complete()` that combined skip-gate +
# assertion logic — but if it returned False because someone re-introduced a
# relocated def, the test SKIPPED instead of FAILING, masking the regression.
# Splitting + choosing the right gate per test fixes the self-disable.

# ── Stage 5: facade has NO relocated `def` blocks ───────────────────────

_RELOCATED_FUNCTIONS = {
    "build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
    "render_guidance_text", "render_inter_quarter_text",
    "_fetch_8k_core",
    "_format_value", "resolve_unit_groups", "_extract_given_day",
    "_normalize_qualitative", "_run_v2_regression_tests",
    "_parse_dt_for_pit", "_is_price_pit_safe", "_build_forward_returns",
    "_iq_parse_json_field", "_norm_ret", "_fmt_vol", "_fmt_txn",
    "_safe_adj", "_event_ref", "_day_from_ts",
    "_cutoff_boundary_price_role", "_best_safe_horizon", "_report_summary",
    "_render_window_label_news", "_render_window_label_filing",
    "_render_horizon_line_filing", "_render_news_react_line",
}


def test_facade_has_no_relocated_function_defs():
    """STAGE 3.2+ ASSERT (loud-fail): warmup_cache.py contains NO `def` for any relocated
    symbol — the facade's surface for these names comes from re-exports only.

    Skip-gate: `_all_reexport_blocks_present()` — TRUE only when all 3 cutover commits
    have landed (re-export blocks present in warmup_cache.py). CRITICAL: this gate must
    NOT use `_domain_modules_exist()` (true after Stage 3.1 COPY, BEFORE Stage 3.2 cutover
    removes the IQ defs — the test would FAIL spuriously during Stage 3.1's full matrix).
    It must NOT use `_all_cutovers_complete()` either (that one short-circuits on
    def-presence — would cause the test to silently SKIP if a maintainer re-introduces
    a def post-Stage-5, masking the regression).

    The chosen gate fires from Stage 3.2 onward AND keeps firing if a def reappears
    (re-export blocks remain even when a stray def is added back), so the assertion
    fails loudly on regression."""
    if not _all_reexport_blocks_present():
        pytest.skip("not all 3 re-export blocks present yet — pre-Stage-3.2 cutover")
    tree = ast.parse(WC_PATH.read_text())
    redefined = [
        n.name for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name in _RELOCATED_FUNCTIONS
    ]
    assert not redefined, (
        f"warmup_cache.py redefines relocated functions: {redefined} — "
        f"these must come from re-export only after Stage 5"
    )


def test_facade_size_after_cleanup():
    """STAGE 5 ASSERT (loud-fail): after import cleanup + def-removal, warmup_cache.py
    is < 800 lines (baseline 2066, target ~520). Skips until cutovers complete."""
    if not _all_cutovers_complete():
        pytest.skip("cutovers not complete — pre-Stage-3.2")
    lines = len(WC_PATH.read_text().splitlines())
    assert lines < 800, (
        f"warmup_cache.py is {lines} lines after cleanup — expected < 800 (target ~520). "
        f"Some relocated content may not have been actually removed."
    )


# ── Stage 5: golden structural-equality (post-split) ─────────────────────────

def _strip_volatile(d: dict) -> dict:
    d = dict(d)
    d.pop("assembled_at", None)
    return d


@pytest.mark.live
def test_golden_8k_packet_FIVE_byte_equal_post_split():
    if not _all_cutovers_complete():
        pytest.skip("cutovers not complete — goldens only meaningful post-Stage-3.2")
    golden = json.loads((FIXTURES / "8k_packet_FIVE.json").read_text())
    acc = golden["accession_8k"]
    out = "/tmp/post_split_8k_FIVE.json"
    subprocess.run(
        [PY, "-m", "scripts.earnings.builders.warmup_cache",
         "FIVE", "--8k-packet", acc, "--out-path", out],
        check=True, env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    actual = _strip_volatile(json.loads(Path(out).read_text()))
    assert actual == golden, "8k_packet golden mismatch — schema or behavior drift"


@pytest.mark.live
def test_golden_guidance_history_FIVE_byte_equal_post_split():
    if not _all_cutovers_complete():
        pytest.skip("cutovers not complete — goldens only meaningful post-Stage-3.2")
    golden = json.loads((FIXTURES / "guidance_history_FIVE.json").read_text())
    pit = golden.get("pit") or "<set-from-golden-or-skip>"
    if pit == "<set-from-golden-or-skip>":
        pytest.skip("golden has no pit — re-capture during Stage 0")
    out = "/tmp/post_split_guidance_FIVE.json"
    subprocess.run(
        [PY, "-m", "scripts.earnings.builders.warmup_cache",
         "FIVE", "--guidance-history", "--pit", pit, "--out-path", out],
        check=True, env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    actual = _strip_volatile(json.loads(Path(out).read_text()))
    assert actual == golden, "guidance_history golden mismatch"


@pytest.mark.live
def test_golden_inter_quarter_FIVE_byte_equal_post_split():
    if not _all_cutovers_complete():
        pytest.skip("cutovers not complete — goldens only meaningful post-Stage-3.2")
    golden = json.loads((FIXTURES / "inter_quarter_context_FIVE.json").read_text())
    prev = golden["prev_8k_ts"]
    cutoff = golden["context_cutoff_ts"]
    out = "/tmp/post_split_iq_FIVE.json"
    subprocess.run(
        [PY, "-m", "scripts.earnings.builders.warmup_cache",
         "FIVE", "--inter-quarter", "--prev-8k", prev,
         "--context-cutoff", cutoff, "--out-path", out],
        check=True, env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    actual = _strip_volatile(json.loads(Path(out).read_text()))
    assert actual == golden, "inter_quarter_context golden mismatch"
