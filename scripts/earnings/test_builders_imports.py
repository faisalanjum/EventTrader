"""4-path identity invariant — load-bearing regression guard.

After each move stage, every relocated symbol must resolve to the SAME Python
object via `is` from EVERY import path:
  1. Old bare path        (e.g. `from build_consensus import build_consensus`)
  2. Old qualified path   (e.g. `from scripts.earnings.build_consensus import build_consensus`)
  3. New qualified path   (e.g. `from scripts.earnings.builders.consensus import build_consensus`)

Stages 3, 5, 7, 9, 11, 13 each extend MODULE_PAIRS with rows for the symbols
their shim-stage relocates. Stage 15 promotes this test to permanent regression
guard with completeness asserts.
"""
from __future__ import annotations
import importlib
import sys
from pathlib import Path
import pytest

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent.parent

# Deterministic sys.path discipline — mirrors _paths.ensure_legacy_paths().
# remove-then-reinsert pattern guarantees the precedence order is:
#   skill-scripts > earnings-local > scripts/ > repo root
# even if any of these were ALREADY on sys.path at a different index.
LEGACY_PATHS = (
    # MUST mirror _paths.ensure_legacy_paths() exactly: 4 entries in this order.
    # Missing PROJECT_ROOT / "scripts" would cause `from sec_quarter_cache_loader
    # import refresh_ticker` (lives at scripts/sec_quarter_cache_loader.py) to
    # ImportError during identity tests of build_consensus / build_prior_financials.
    PROJECT_ROOT / ".claude/skills/earnings-orchestrator/scripts",
    PROJECT_ROOT / "scripts/earnings",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT,
)
for path in LEGACY_PATHS:
    s = str(path)
    while s in sys.path:
        sys.path.remove(s)
for path in reversed(LEGACY_PATHS):
    sys.path.insert(0, str(path))


# {old_module_bare: (new_module_qualified, [symbols])}
# Populated incrementally by Stages 3, 5, 7, 9, 11, 13.
MODULE_PAIRS: dict[str, tuple[str, list[str]]] = {
    "peer_earnings_snapshot": (
        "scripts.earnings.builders.peer_earnings_snapshot",
        ["build_peer_earnings_snapshot", "render_text", "main", "_parse_dt_for_pit"],
    ),
    "macro_snapshot": (
        "scripts.earnings.builders.macro_snapshot",
        ["build_macro_snapshot", "render_text", "main"],
    ),
    "build_consensus": (
        "scripts.earnings.builders.consensus",
        ["build_consensus", "main", "_parse_iso", "_normalize_session"],
    ),
    "build_prior_financials": (
        "scripts.earnings.builders.prior_financials",
        ["build_prior_financials", "classify_period", "is_target_period",
         "dedupe_facts", "main", "_parse_value"],
    ),
    "warmup_cache": (
        "scripts.earnings.builders.warmup_cache",
        ["build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
         "render_guidance_text", "render_inter_quarter_text",
         "run_warmup", "run_transcript", "run_mda", "run_8k", "main",
         "_parse_dt_for_pit", "_run_v2_regression_tests"],
    ),
    "builder_adapters": (
        "scripts.earnings.builders.adapters",
        [
            # Public adapter API (called by orchestrator + debug tools)
            "build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
            "build_peer_earnings_snapshot", "build_macro_snapshot",
            "build_consensus", "build_prior_financials",
            # Private adapter helpers — re-exported via globals().update() shim.
            # Lock in identity so future code can rely on the contract.
            "_SuppressStdout", "_enrich_packet", "_write_enriched",
            "_ensure_dir", "_derive_mode", "_now_iso",
        ],
    ),
}


def _flatten_pairs():
    """Flatten MODULE_PAIRS into parametrize-friendly tuples."""
    rows = []
    for old_bare, (new_qual, symbols) in MODULE_PAIRS.items():
        for sym in symbols:
            rows.append((old_bare, new_qual, sym))
    return rows


@pytest.mark.parametrize("old_bare,new_qual,symbol", _flatten_pairs())
def test_old_bare_equals_new_qualified(old_bare, new_qual, symbol):
    """Bare-name import (relies on PYTHONPATH=scripts/earnings) must resolve
    to the same object as the canonical qualified path."""
    bare_mod = importlib.import_module(old_bare)
    new_mod = importlib.import_module(new_qual)
    assert getattr(bare_mod, symbol) is getattr(new_mod, symbol), (
        f"IDENTITY BROKEN: {old_bare}.{symbol} ({id(getattr(bare_mod, symbol))}) "
        f"is not {new_qual}.{symbol} ({id(getattr(new_mod, symbol))})"
    )


@pytest.mark.parametrize("old_bare,new_qual,symbol", _flatten_pairs())
def test_old_qualified_equals_new_qualified(old_bare, new_qual, symbol):
    """Old qualified path (e.g. scripts.earnings.build_consensus) must resolve
    to the same object as the canonical qualified path."""
    if old_bare == "warmup_cache":
        # warmup_cache lives outside scripts.earnings.* — no qualified old path
        pytest.skip("warmup_cache has no scripts.earnings.* qualified old path")
    old_qual = f"scripts.earnings.{old_bare}"
    old_mod = importlib.import_module(old_qual)
    new_mod = importlib.import_module(new_qual)
    assert getattr(old_mod, symbol) is getattr(new_mod, symbol), (
        f"IDENTITY BROKEN: {old_qual}.{symbol} is not {new_qual}.{symbol}"
    )


def test_classifier_singleton_across_paths():
    """build_consensus._classifier must be one cell across all import paths.
    If this fails, the module loaded twice and the lazy singleton split.

    Three import paths exist for build_consensus after Stage 7:
      1. `import build_consensus`                     (bare, via OLD-path shim)
      2. `import scripts.earnings.build_consensus`    (qualified, via OLD-path shim)
      3. `import scripts.earnings.builders.consensus` (canonical)

    All three MUST dispatch to the canonical _get_classifier() and return the
    SAME MarketSessionClassifier instance. The shim's globals().update() pins
    `_get_classifier` to the canonical function object; calling it from any
    path mutates the canonical module's `global _classifier` — a single cell.

    Without this guarantee, callers via different paths could see different
    classifier instances and inconsistent behavior. No external code imports
    `_classifier` directly today (verified by grep), but this test locks the
    invariant for the future.
    """
    import build_consensus as a
    import scripts.earnings.build_consensus as b
    import scripts.earnings.builders.consensus as c
    cls_a = a._get_classifier()
    cls_b = b._get_classifier()
    cls_c = c._get_classifier()
    # All three import paths must dispatch to the canonical _get_classifier
    # AND return the same singleton object.
    assert cls_a is cls_b is cls_c, (
        f"singleton split: a={id(cls_a)}, b={id(cls_b)}, c={id(cls_c)}"
    )
    # And the canonical module's _classifier global must point at the same
    # object (it's the cell that _get_classifier mutates via `global _classifier`).
    assert cls_a is c._classifier, "canonical module's _classifier mutation not visible from shim"


def test_classifier_singleton_attribute_access_across_paths():
    """Stage 7.1 REGRESSION GUARD for the shim mutable-snapshot bug.

    test_classifier_singleton_across_paths above proves the SINGLETON returned
    by `_get_classifier()` is identical across paths. This test goes one step
    further and proves DIRECT ATTRIBUTE ACCESS to `_classifier` also reflects
    canonical's current state across all paths.

    The bug fixed in Stage 7.1: the shim's eager-copy of `_classifier` at
    shim-import time captured the value `None`. After `_get_classifier()`
    mutated canonical's `_classifier`, the shim's `_classifier` snapshot
    stayed None — `build_consensus._classifier` and
    `scripts.earnings.build_consensus._classifier` returned None even though
    `scripts.earnings.builders.consensus._classifier` was the live instance.

    Fix: shim's PEP 562 `__getattr__` forwards `_classifier` (and any other
    name removed from shim globals) to canonical at access time. This test
    asserts the contract holds — direct attribute access yields the canonical
    singleton, not a stale snapshot.
    """
    import build_consensus as a
    import scripts.earnings.build_consensus as b
    import scripts.earnings.builders.consensus as c
    # Force initialization through any path
    cls = c._get_classifier()
    # Direct attribute access must return the canonical singleton from EVERY path.
    assert a._classifier is b._classifier is c._classifier is cls, (
        f"shim attribute stale: a={id(a._classifier)} "
        f"b={id(b._classifier)} c={id(c._classifier)} cls={id(cls)}"
    )


def test_parse_dt_for_pit_disambiguation():
    """Stage 11 SHADOW GUARD for the cross-module same-name collision.

    `_parse_dt_for_pit` exists in BOTH warmup_cache AND peer_earnings_snapshot
    as DIFFERENT functions. The shim mechanism preserves identity within each
    module's import paths, but must NOT cross-wire them.

    After Stage 11, all 4 paths must satisfy:
      - within-module: bare ≡ canonical for warmup_cache._parse_dt_for_pit
      - within-module: bare ≡ canonical for peer_earnings_snapshot._parse_dt_for_pit
      - cross-module distinctness: warmup_cache._parse_dt_for_pit IS NOT peer_earnings_snapshot._parse_dt_for_pit

    If the shim accidentally aliased one to the other (e.g. if MODULE_PAIRS
    used the same `new_qual` for both), this test fires.
    """
    import warmup_cache, peer_earnings_snapshot
    import scripts.earnings.builders.warmup_cache as wc_new
    import scripts.earnings.builders.peer_earnings_snapshot as pe_new
    # Within-module identity (already covered by parametrized identity tests, but assert here too):
    assert warmup_cache._parse_dt_for_pit is wc_new._parse_dt_for_pit, \
        "warmup_cache shim diverged from canonical for _parse_dt_for_pit"
    assert peer_earnings_snapshot._parse_dt_for_pit is pe_new._parse_dt_for_pit, \
        "peer_earnings_snapshot shim diverged from canonical for _parse_dt_for_pit"
    # Cross-module DISTINCTNESS — same name, different functions:
    assert warmup_cache._parse_dt_for_pit is not peer_earnings_snapshot._parse_dt_for_pit, (
        f"shadow violation: warmup_cache._parse_dt_for_pit ({id(warmup_cache._parse_dt_for_pit)}) "
        f"IS the SAME object as peer_earnings_snapshot._parse_dt_for_pit "
        f"({id(peer_earnings_snapshot._parse_dt_for_pit)}) — they should be DIFFERENT functions"
    )


def test_xbrl_exact_splits_lazy_import_works():
    """REGRESSION GUARD for build_prior_financials's lazy outbound import.

    `scripts/earnings/builders/prior_financials.py` line ~1593 (was line 1593 in
    OLD) does:
        from xbrl_exact_splits import extract_segment_splits, build_revenue_splits_section
    inside `_build_revenue_splits_section()`. This is a LAZY import that fires
    only when the builder is called — silent failure mode if `ensure_legacy_paths()`
    didn't put EARNINGS_DIR on sys.path correctly.

    The xbrl_exact_splits module STAYS at scripts/earnings/xbrl_exact_splits.py
    (NOT moved into builders/). Stage 9 promotes the lazy import to a tested
    invariant: must resolve to the EARNINGS_DIR file with the expected functions.
    """
    import xbrl_exact_splits
    assert hasattr(xbrl_exact_splits, "extract_segment_splits"), \
        "xbrl_exact_splits missing extract_segment_splits"
    assert hasattr(xbrl_exact_splits, "build_revenue_splits_section"), \
        "xbrl_exact_splits missing build_revenue_splits_section"
    # Must resolve to scripts/earnings/, NOT the canonical builders/ subdir.
    assert "scripts/earnings/xbrl_exact_splits.py" in xbrl_exact_splits.__file__, (
        f"xbrl_exact_splits resolved to wrong location: {xbrl_exact_splits.__file__}"
    )


def test_classifier_appears_in_dir_across_paths():
    """Stage 7.2 REGRESSION GUARD for shim __dir__ completeness.

    The Stage 7.1 fix DELETED `_classifier` from the shim's __dict__ so
    PEP 562 `__getattr__` could forward access to canonical. That fixed
    `hasattr()` and direct attribute access — but it also removed
    `_classifier` from `dir(shim)` because PEP 562 `__getattr__` does NOT
    fire on `dir()` (which lists __dict__, not attribute lookups).

    Result of the gap (pre-Stage-7.2): `hasattr(build_consensus, "_classifier")`
    returned True, but `"_classifier" in dir(build_consensus)` returned False.
    Diverged from canonical (where both are True). Code that introspects via
    dir() (autocomplete, IDEs, sphinx, dir-driven tests) would see a smaller
    surface than canonical.

    Fix: shim now defines PEP 562 `__dir__()` returning the union of shim's
    own globals and `dir(_impl)`. This test asserts `_classifier in dir(mod)`
    for all three import paths.
    """
    import build_consensus as a
    import scripts.earnings.build_consensus as b
    import scripts.earnings.builders.consensus as c
    for mod, label in [(a, "build_consensus (bare)"),
                       (b, "scripts.earnings.build_consensus (qualified shim)"),
                       (c, "scripts.earnings.builders.consensus (canonical)")]:
        assert "_classifier" in dir(mod), (
            f"{label}: '_classifier' missing from dir() — "
            f"shim __dir__ forward broken? dir-len={len(dir(mod))}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Stage 15 — Permanent identity-test guard finalization
# ─────────────────────────────────────────────────────────────────────────────


def test_builders_package_public_surface():
    """The scripts.earnings.builders package exposes the 7 adapter functions."""
    import scripts.earnings.builders as pkg
    expected = {
        "build_8k_packet", "build_guidance_history", "build_inter_quarter_context",
        "build_peer_earnings_snapshot", "build_macro_snapshot",
        "build_consensus", "build_prior_financials",
    }
    for name in expected:
        assert hasattr(pkg, name), f"package surface missing {name}"
    assert set(pkg.__all__) >= expected, f"__all__ missing entries: {expected - set(pkg.__all__)}"


def test_package_root_re_exports_identity_with_adapters_submodule():
    """Stage 14 makes orchestrator do `from scripts.earnings.builders import (...)`,
    which resolves through scripts.earnings.builders/__init__.py — the package
    root. The package's __init__ does `from .adapters import (...)`, so the 7
    adapter functions must be the SAME objects when accessed via the package
    root vs the adapters submodule.

    If __init__.py ever switches to wrap or copy the functions (e.g., via a
    decorator or assignment from a different module), identity breaks here.
    """
    import scripts.earnings.builders as pkg
    import scripts.earnings.builders.adapters as adapters_mod
    for name in ("build_8k_packet", "build_guidance_history",
                 "build_inter_quarter_context", "build_peer_earnings_snapshot",
                 "build_macro_snapshot", "build_consensus",
                 "build_prior_financials"):
        pkg_obj = getattr(pkg, name)
        adapter_obj = getattr(adapters_mod, name)
        assert pkg_obj is adapter_obj, (
            f"package root scripts.earnings.builders.{name} ({id(pkg_obj)}) "
            f"is NOT the same object as scripts.earnings.builders.adapters.{name} "
            f"({id(adapter_obj)}) — orchestrator's canonical import would "
            f"diverge from direct submodule access"
        )


def test_module_pairs_completeness():
    """MODULE_PAIRS must cover every public + private symbol from EXPECTED_SURFACE
    (defined in test_builders_surface.py).

    Excludes `main` (covered by CLI smoke, not identity) — the rest must all
    have an identity row. If a future EXPECTED_SURFACE addition isn't paired
    here, this test fires immediately.
    """
    from test_builders_surface import EXPECTED_SURFACE
    covered = {
        (mod, sym)
        for mod, (_, syms) in MODULE_PAIRS.items()
        for sym in syms
    }
    missing = []
    for modname, spec in EXPECTED_SURFACE.items():
        for sym in spec["public"] + spec["private_exports"]:
            if (modname, sym) not in covered:
                missing.append(f"{modname}.{sym}")
    # main is checked by CLI smoke, not identity — exclude
    missing = [m for m in missing if not m.endswith(".main")]
    assert not missing, f"MODULE_PAIRS missing rows: {missing}"


def test_concurrent_imports_preserve_identity():
    """Smoke-test concurrent imports of old bare, old qualified, and new canonical
    paths.

    Python's import lock should make this safe by language guarantee, but the
    orchestrator's ThreadPoolExecutor spawns ALL 7 builders in parallel — if
    any builder's import has a side-effect that races with another, it would
    surface here. Strategy: spawn N threads each importing a different module
    name; after join, identity tests still hold.
    """
    import threading
    import importlib

    mods_to_import = [
        # bare + qualified + canonical for each builder, plus adapters
        "build_consensus", "scripts.earnings.build_consensus",
        "scripts.earnings.builders.consensus",
        "build_prior_financials", "scripts.earnings.build_prior_financials",
        "scripts.earnings.builders.prior_financials",
        "macro_snapshot", "scripts.earnings.macro_snapshot",
        "scripts.earnings.builders.macro_snapshot",
        "peer_earnings_snapshot", "scripts.earnings.peer_earnings_snapshot",
        "scripts.earnings.builders.peer_earnings_snapshot",
        "warmup_cache",
        "scripts.earnings.builders.warmup_cache",
        "scripts.earnings.builders.eight_k_packet",
        "builder_adapters", "scripts.earnings.builder_adapters",
        "scripts.earnings.builders.adapters",
        "scripts.earnings.builders",
    ]
    errors: list = []

    def _worker(name: str):
        try:
            importlib.import_module(name)
        except Exception as e:
            errors.append((name, e))

    threads = [threading.Thread(target=_worker, args=(name,)) for name in mods_to_import]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not errors, f"Concurrent imports raised: {errors}"

    # After concurrent imports, identity invariant must STILL hold.
    # Pick one representative symbol per builder + the adapter facade.
    samples = [
        ("build_consensus", "scripts.earnings.builders.consensus", "build_consensus"),
        ("build_prior_financials", "scripts.earnings.builders.prior_financials", "_parse_value"),
        ("macro_snapshot", "scripts.earnings.builders.macro_snapshot", "build_macro_snapshot"),
        ("peer_earnings_snapshot", "scripts.earnings.builders.peer_earnings_snapshot", "_parse_dt_for_pit"),
        ("warmup_cache", "scripts.earnings.builders.warmup_cache", "build_8k_packet"),
        ("builder_adapters", "scripts.earnings.builders.adapters", "build_consensus"),
    ]
    for old_bare, new_qual, sym in samples:
        old_obj = getattr(importlib.import_module(old_bare), sym)
        new_obj = getattr(importlib.import_module(new_qual), sym)
        assert old_obj is new_obj, (
            f"IDENTITY BROKEN after concurrent imports: "
            f"{old_bare}.{sym} != {new_qual}.{sym}"
        )


def test_eight_k_packet_canonical_facade_identity():
    """Stage 1.2 facade contract: warmup_cache re-exports preserve identity
    with eight_k_packet canonical home."""
    import scripts.earnings.builders.warmup_cache as wc
    import scripts.earnings.builders.eight_k_packet as ek
    for sym in ("build_8k_packet", "_fetch_8k_core",
                "QUERY_4J", "QUERY_4K", "QUERY_4G_META",
                "QUERY_4K_OTHER_PREVIEW", "QUERY_4F"):
        f = getattr(wc, sym, None)
        c = getattr(ek, sym, None)
        assert c is not None, f"eight_k_packet missing {sym}"
        assert f is not None, f"warmup_cache facade missing {sym}"
        assert f is c, f"facade {sym} != canonical {sym}"


def test_run_8k_uses_canonical_fetch_8k_core():
    """Stage 1.2 LOAD-BEARING contract: warmup_cache.run_8k() and
    eight_k_packet.build_8k_packet() share the SAME _fetch_8k_core object.

    This is sufficient as identity-only — DO NOT add a `with patch(...)` block
    that patches `scripts.earnings.builders.eight_k_packet._fetch_8k_core` and
    calls `wc.run_8k(...)`. That patch would NOT take effect because:
    (a) `from .eight_k_packet import _fetch_8k_core` snapshots the binding into
        `warmup_cache.__dict__['_fetch_8k_core']` at import time;
    (b) `wc.run_8k` body does an unqualified `_fetch_8k_core(...)` lookup against
        `wc.run_8k.__globals__` (which IS `warmup_cache.__dict__`);
    (c) `mock.patch("scripts.earnings.builders.eight_k_packet._fetch_8k_core")`
        rebinds `eight_k_packet.__dict__['_fetch_8k_core']` ONLY — it does NOT
        reach into `warmup_cache.__dict__`.
    The identity assertion below is sufficient and correct."""
    import scripts.earnings.builders.warmup_cache as wc
    import scripts.earnings.builders.eight_k_packet as ek
    assert wc._fetch_8k_core is ek._fetch_8k_core, (
        f"shared-ownership BROKEN: wc._fetch_8k_core (id={id(wc._fetch_8k_core)}) "
        f"is not ek._fetch_8k_core (id={id(ek._fetch_8k_core)}) — "
        f"warmup_cache.py must use `from .eight_k_packet import _fetch_8k_core`, "
        f"NOT define its own def"
    )
    # Bonus: assert run_8k's __globals__ resolves _fetch_8k_core to the canonical
    # object — proves the function looks up the name in the right namespace
    assert wc.run_8k.__globals__["_fetch_8k_core"] is ek._fetch_8k_core, (
        "run_8k.__globals__['_fetch_8k_core'] is not the canonical eight_k_packet object"
    )
