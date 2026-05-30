"""In-memory fake Driver registry  (TEST-SCAFFOLD — the ONLY stub).

Mirrors the production Neo4j-backed registry INTERFACE (same method names);
production swaps this for the guidance-style Neo4j registry/writer
(Harness_BuilderPrompt.md §4 / §10). Loads driver rows from
``tests/fixtures/fake_registry.json`` via a path relative to THIS file
(os.path.dirname(__file__)) so it works regardless of cwd.

Driver row schema (Harness_BuilderPrompt.md §5 / §4):
  {name, aliases[], allowed_states[], segment, definition, base_label?, is_shortcut?}

NEVER imported by PROD-CORE (driver_ids / vocab_seed / validators / reuse /
render_catalog / run_one). stdlib only, no network.
"""

from __future__ import annotations

import json
import os
from typing import Optional


_FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "tests", "fixtures", "fake_registry.json"
)


class Registry:
    """In-memory driver registry. Production reimplements the SAME method names
    against Neo4j (Harness_BuilderPrompt.md §4 / §10 swap)."""

    def __init__(self, drivers: Optional[list] = None) -> None:
        # store rows as a list, preserving insertion order (determinism).
        self._drivers: list[dict] = []
        # index by exact name for O(1) lookup.
        self._by_name: dict[str, dict] = {}
        for row in (drivers or []):
            self.add_driver(row)

    # ── construction ────────────────────────────────────────────────────────

    @classmethod
    def from_fixture(cls, path: Optional[str] = None) -> "Registry":
        """Load the scenario registry from ``fake_registry.json`` (default path
        is relative to this module)."""
        p = path or _FIXTURE_PATH
        with open(p, "r", encoding="utf-8") as fh:
            rows = json.load(fh)
        return cls(rows)

    # ── the production INTERFACE (same names prod reimplements over Neo4j) ────

    def lookup_exact_name(self, name: str) -> Optional[dict]:
        """B3: return the driver dict whose ``name`` equals ``name``, else None."""
        return self._by_name.get(name)

    def lookup_by_alias(self, token: str) -> Optional[dict]:
        """B4 / B7: return the driver dict that lists ``token`` in its
        ``aliases``, else None. First match in insertion order."""
        for d in self._drivers:
            if token in d.get("aliases", []):
                return d
        return None

    def all_drivers(self) -> list:
        """Return all driver dicts (insertion order)."""
        return list(self._drivers)

    def sorted_token_match(self, tokens: list) -> Optional[dict]:
        """B8: return the driver whose ``sorted(name tokens)`` equals
        ``sorted(tokens)``, else None. Used by the sorted-token reuse rung."""
        key = sorted(tokens)
        for d in self._drivers:
            if sorted(d["name"].split("_")) == key:
                return d
        return None

    def add_driver(self, row: dict) -> dict:
        """Register a new driver row (in prod = the Neo4j MERGE). Returns the
        stored dict. Last-write-wins on duplicate name (the test harness never
        relies on this, but it keeps the index coherent)."""
        # normalize the row to carry the optional fields explicitly.
        stored = {
            "name": row["name"],
            "aliases": list(row.get("aliases", [])),
            "allowed_states": list(row.get("allowed_states", [])),
            "segment": row.get("segment", "Total"),
            "definition": row.get("definition", ""),
        }
        if "base_label" in row and row["base_label"] is not None:
            stored["base_label"] = row["base_label"]
        if "is_shortcut" in row:
            stored["is_shortcut"] = bool(row["is_shortcut"])
        existing = self._by_name.get(stored["name"])
        if existing is not None:
            # replace in place to preserve order
            idx = self._drivers.index(existing)
            self._drivers[idx] = stored
        else:
            self._drivers.append(stored)
        self._by_name[stored["name"]] = stored
        return stored
