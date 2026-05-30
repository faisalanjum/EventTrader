"""S1 — render the registry + vocab excerpt into the LLM-readable catalog block
(PROD-CORE, pure).

Mirrors the production bundle renderer (DriverProcess.html §C1.1 / §C5.1 +
DriverOntology_Implementation.md §A item 2-3): per-Driver the LLM sees
``name · aliases · allowed_states · segment · definition`` PLUS a short vocab
excerpt (THEMES / OBJECTS / GEOGRAPHIES / METRICS + SHORTCUTS) so it has slot
and shortcut hints. ``definition`` is included per §A (it is in the per-Driver
set the LLM sees; omitting it understates reuse).

Reads the registry (the prod PIT-Neo4j seam) + the ``vocab`` snapshot; pure
otherwise — deterministic, sorted output. Imports only the foundation vocab type
indirectly (no test-only imports). NO LLM, stdlib only.
"""

from __future__ import annotations

from vocab_seed import VocabSnapshot


def _fmt_list(values) -> str:
    """Comma-join a list deterministically; '-' for empty."""
    vals = list(values)
    return ", ".join(vals) if vals else "-"


def render_catalog(registry, vocab: VocabSnapshot) -> str:
    """Render the catalog block the producer-LLM reads (S1).

    Layout (stable, human + LLM readable):

        === DRIVER CATALOG ===
        - <name>
            aliases: ...
            allowed_states: ...
            segment: ...
            definition: ...
        ...
        === VOCAB EXCERPT ===
        THEMES: ...
        OBJECTS: ...
        GEOGRAPHIES: ...
        METRICS: ...
        SHORTCUTS: ...

    Drivers are listed in the registry's insertion order (deterministic);
    vocab excerpt tokens are SORTED so the block is byte-stable across runs."""
    lines: list[str] = ["=== DRIVER CATALOG ==="]
    for d in registry.all_drivers():
        lines.append(f"- {d['name']}")
        lines.append(f"    aliases: {_fmt_list(d.get('aliases', []))}")
        lines.append(f"    allowed_states: {_fmt_list(d.get('allowed_states', []))}")
        lines.append(f"    segment: {d.get('segment', 'Total')}")
        lines.append(f"    definition: {d.get('definition', '')}")

    lines.append("=== VOCAB EXCERPT ===")
    lines.append(f"THEMES: {_fmt_list(sorted(vocab.slot_vocabs.get('theme', frozenset())))}")
    lines.append(f"OBJECTS: {_fmt_list(sorted(vocab.slot_vocabs.get('object', frozenset())))}")
    lines.append(f"GEOGRAPHIES: {_fmt_list(sorted(vocab.slot_vocabs.get('geography', frozenset())))}")
    lines.append(f"METRICS: {_fmt_list(sorted(vocab.slot_vocabs.get('metric', frozenset())))}")
    lines.append(f"SHORTCUTS: {_fmt_list(sorted(vocab.shortcuts))}")

    return "\n".join(lines)
