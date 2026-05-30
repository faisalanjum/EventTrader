"""S1 — render_catalog(registry, vocab) unit tests.

Covers S1 of the driver-naming harness (Harness_BuilderPrompt.md §4
`render_catalog.py`, §6 SEQUENCE point). The rendered catalog block is the
LLM-readable bundle the producer-LLM scans before deciding any driver name
(DriverProcess.html §C1.1 "What the bundle has — the Driver Registry Catalog
block"). Per DriverOntology_Implementation.md §A item 2, the per-Driver excerpt
the LLM sees is exactly `name · aliases[] · segment · allowed_states[] ·
definition`; per §A item 3 it also carries the §F vocab excerpt.

EXPECTED outcomes are derived from the SPEC, not guessed:
  - §A item 2 (Implementation, line 16): per-Driver fields = name, aliases,
    segment, allowed_states, definition.
  - DriverProcess.html §C1.1 (block layout): DRIVER REGISTRY CATALOG rows +
    a VOCAB EXCERPT with THEMES / OBJECTS / GEOGRAPHIES / METRICS + SHORTCUTS.
  - req_canonical.md B-F9 / B-R10(e): `definition` is EXACTLY one sentence
    describing the variable (a real companion field the catalog must surface).
  - Harness_BuilderPrompt.md §4 render_catalog: "Include `definition` — it is in
    the per-Driver set the LLM sees per §A; omitting it understates reuse."
  - doubt #18 (`base_label` purpose = V5 + CANONICAL_BASE_LABELS, an INTERNAL
    validator concern): base_label is NOT a §A item-2 LLM-visible catalog field,
    so render_catalog MUST NOT leak the base_label VALUE as a per-Driver line.

The catalog is loaded via the production seam: registry from the
registry_fake loader (fixtures/fake_registry.json) + the VocabSnapshot from
build_vocab_snapshot(). Pure offline, stdlib only, NO LLM.
"""

from __future__ import annotations

import json
import os

from registry_fake import Registry
from render_catalog import render_catalog
from vocab_seed import build_vocab_snapshot


# ── fixtures (module-level; render_catalog is pure so a shared block is fine) ──

_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "fake_registry.json"
)


def _registry() -> Registry:
    return Registry.from_fixture()


def _vocab():
    return build_vocab_snapshot()


def _catalog() -> str:
    return render_catalog(_registry(), _vocab())


def _fixture_rows() -> list:
    with open(_FIXTURE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ── per-Driver fields the LLM sees (§A item 2 + C1.1) ────────────────────────

def test_every_seeded_driver_name_present():
    """C1.1 / §A item 2: every seeded Driver `name` appears in the catalog so
    the producer-LLM can reuse it (DriverProcess.html §C1.3 reuse scan). The
    catalog lists the registry's drivers; a missing name = an unreusable name."""
    catalog = _catalog()
    for row in _fixture_rows():
        assert row["name"] in catalog, f"driver name {row['name']!r} missing from catalog"


def test_every_alias_present():
    """C1.1 / §A item 2 (`aliases[]`): each alias the registry carries must be
    rendered — aliases are the spelling/order variants the LLM matches on
    (req_canonical B-F5). e.g. iphone_china_sales -> china_iphone_sales,
    gpu_hyperscaler_bookings -> hyperscaler_gpu_bookings."""
    catalog = _catalog()
    seen_any_alias = False
    for row in _fixture_rows():
        for alias in row.get("aliases", []):
            seen_any_alias = True
            assert alias in catalog, f"alias {alias!r} of {row['name']!r} missing"
    # guard against a vacuous pass: the scenario fixture DOES have aliases.
    assert seen_any_alias, "fixture unexpectedly has no aliases to render"


def test_every_allowed_state_present():
    """C1.1 / §A item 2 (`allowed_states[]`): each driver's allowed_states must be
    rendered so the LLM picks driver_state from the right class (DriverProcess
    §C1.3 step 3; req_canonical B-F10 / B-R10(d)). e.g. yield_curve ->
    steepened/flattened/inverted/normalized."""
    catalog = _catalog()
    for row in _fixture_rows():
        for state in row.get("allowed_states", []):
            assert state in catalog, (
                f"allowed_state {state!r} of {row['name']!r} missing from catalog"
            )


def test_every_segment_present():
    """C1.1 / §A item 2 (`segment`): each driver's segment is rendered (Total or
    its sub-dimension label per req_canonical B-F7 / B-R10(c)). e.g.
    iphone_china_sales -> 'iPhone China', gpu_hyperscaler_bookings ->
    'GPU Hyperscaler', oil_price -> 'Total'."""
    catalog = _catalog()
    for row in _fixture_rows():
        segment = row.get("segment", "Total")
        assert segment in catalog, (
            f"segment {segment!r} of {row['name']!r} missing from catalog"
        )


def test_every_definition_present():
    """§A item 2 (`definition`) + Harness_BuilderPrompt.md §4 + doubt #18 context:
    the per-Driver definition MUST be in the rendered catalog. This is the
    load-bearing assertion the task calls out: the LLM sees the definition per
    §A, and "omitting it understates reuse" (the LLM has less to match on). Each
    fixture row carries a one-sentence definition (req_canonical B-F9). e.g.
    'The benchmark market price of crude oil.'"""
    catalog = _catalog()
    for row in _fixture_rows():
        definition = row["definition"]
        assert definition, f"fixture row {row['name']!r} has an empty definition"
        assert definition in catalog, (
            f"definition of {row['name']!r} missing from catalog: {definition!r}"
        )


def test_definition_label_rendered_per_driver():
    """§A item 2 + §4: the block uses a per-Driver `definition:` field label (not
    just the sentence floating free), so the LLM reads it as the driver's
    definition. There is one labelled definition line per seeded driver."""
    catalog = _catalog()
    n_drivers = len(_fixture_rows())
    assert catalog.count("definition:") == n_drivers, (
        f"expected {n_drivers} 'definition:' field lines, "
        f"got {catalog.count('definition:')}"
    )


def test_aliases_allowed_states_segment_field_labels_present():
    """C1.1 / §A item 2: the per-Driver excerpt surfaces aliases, allowed_states
    and segment as labelled fields (one each per driver) so the LLM-readable
    block carries the full companion-field set, not just the bare name."""
    catalog = _catalog()
    n_drivers = len(_fixture_rows())
    assert catalog.count("aliases:") == n_drivers
    assert catalog.count("allowed_states:") == n_drivers
    assert catalog.count("segment:") == n_drivers


# ── VOCAB EXCERPT headers + SHORTCUTS list (§A item 3 / C1.1) ────────────────

def test_vocab_excerpt_headers_present():
    """DriverProcess.html §C1.1 (VOCAB EXCERPT block) + §A item 3: the catalog
    contains a vocab excerpt with the THEMES / OBJECTS / GEOGRAPHIES / METRICS
    headers so the LLM has slot hints (Harness_BuilderPrompt.md §4)."""
    catalog = _catalog()
    for header in ("THEMES:", "OBJECTS:", "GEOGRAPHIES:", "METRICS:"):
        assert header in catalog, f"vocab-excerpt header {header!r} missing"


def test_shortcuts_header_and_list_present():
    """C1.1 (VOCAB EXCERPT) + §A item 3 + B-R5: the catalog renders a SHORTCUTS:
    list so the LLM knows the standalone-shortcut vocabulary
    (yield_curve / fda_approval / oil_price / opec_supply ...). Assert the header
    AND that the seeded shortcut tokens are listed."""
    catalog = _catalog()
    assert "SHORTCUTS:" in catalog, "SHORTCUTS header missing from vocab excerpt"
    vocab = _vocab()
    for shortcut in sorted(vocab.shortcuts):
        assert shortcut in catalog, f"shortcut {shortcut!r} missing from catalog"


def test_vocab_excerpt_slot_tokens_present():
    """§A item 3 / C1.1: the THEMES/OBJECTS/GEOGRAPHIES/METRICS lines actually
    list their slot tokens (not just empty headers). Spot the slot vocabs from
    build_vocab_snapshot() against the rendered block so the LLM has real slot
    hints, e.g. THEMES->ai, OBJECTS->iphone, GEOGRAPHIES->china, METRICS->revenue."""
    catalog = _catalog()
    vocab = _vocab()
    for slot in ("theme", "object", "geography", "metric"):
        for token in sorted(vocab.slot_vocabs[slot]):
            assert token in catalog, (
                f"{slot} vocab token {token!r} missing from catalog excerpt"
            )


def test_catalog_and_vocab_section_markers_present():
    """C1.1: the block is split into a driver catalog section and a vocab excerpt
    section (the two halves the LLM reads). render_catalog uses
    '=== DRIVER CATALOG ===' then '=== VOCAB EXCERPT ===' as the stable markers."""
    catalog = _catalog()
    assert "=== DRIVER CATALOG ===" in catalog
    assert "=== VOCAB EXCERPT ===" in catalog
    # the driver catalog section precedes the vocab excerpt (C1.1 ordering).
    assert catalog.index("=== DRIVER CATALOG ===") < catalog.index("=== VOCAB EXCERPT ===")


# ── doubt #18: base_label is NOT a leaked LLM-visible catalog field ──────────

def test_base_label_value_not_leaked_as_catalog_field():
    """doubt #18 (`base_label` purpose = V5 + CANONICAL_BASE_LABELS, an INTERNAL
    validator concern) + §A item 2 (LLM-visible fields = name/aliases/segment/
    allowed_states/definition — base_label is NOT listed). render_catalog must
    not surface a 'base_label:' field line; base_label stays internal to V5.

    NOTE: we assert no 'base_label:' FIELD LABEL is rendered (the leak we care
    about), not that the capitalized value string is wholly absent — several
    base_label values (e.g. 'Sales', 'Revenue') legitimately appear elsewhere as
    segment/definition substrings, so a raw substring check would be a false
    positive."""
    catalog = _catalog()
    assert "base_label:" not in catalog, (
        "base_label leaked as a per-Driver catalog field; §A item 2 limits the "
        "LLM-visible set to name/aliases/segment/allowed_states/definition"
    )


# ── determinism (Harness_BuilderPrompt.md §9: pure, byte-stable output) ──────

def test_render_is_deterministic():
    """§9 engineering standard (pure + deterministic): render_catalog is a pure
    function of (registry, vocab) — two renders of the same inputs produce a
    byte-identical block (no hidden state, sorted vocab excerpt)."""
    a = render_catalog(_registry(), _vocab())
    b = render_catalog(_registry(), _vocab())
    assert a == b


def test_returns_string():
    """§4 signature: render_catalog(registry, vocab) -> str (the bundle block is
    injected as markdown text into the LLM prompt, DriverProcess.html §C1.1)."""
    out = _catalog()
    assert isinstance(out, str)
    assert out  # non-empty
