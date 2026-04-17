#!/usr/bin/env python3
"""CS1–CS3 canonical-sector consistency tests.

These tests enforce that the hardcoded CANONICAL_SECTORS enum in
``config/canonical_sectors.py``, the live Neo4j distinct-sector set,
AND the SKILL.md prose enumeration stay aligned. Required pre-commit.

If any test fails, it tells you exactly which file(s) to update in the same
commit. The tests are network-dependent (CS1 queries Neo4j); if Neo4j is
unreachable, CS1 aborts with a clear error — it does NOT pass silently.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]  # scripts/earnings/<this> → repo root
sys.path.insert(0, str(_REPO_ROOT))                      # for config.*
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "earnings"))  # for utils.*

from config.canonical_sectors import CANONICAL_SECTORS
from utils import neo4j_session


class CanonicalSectorConsistency(unittest.TestCase):

    # ── CS1: Neo4j ↔ module parity ──
    def test_CS1_canonical_sectors_match_neo4j(self):
        """Fail loudly with remediation if Neo4j sector set diverges from enum.

        Mirrors the runtime coalesce logic exactly — _lookup_company_sector in
        earnings_orchestrator.py uses ``coalesce(c.sector, sec.name)``, so this
        test must compute the identical set or drift between Industry-only and
        property-only tickers could go undetected.
        """
        with neo4j_session() as (session, err):
            self.assertFalse(err, f"Neo4j unavailable for CS1: {err}")
            self.assertIsNotNone(session, "Neo4j session is None")
            rows = session.run("""
                MATCH (c:Company)
                OPTIONAL MATCH (c)-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(sec:Sector)
                WITH coalesce(c.sector, sec.name) AS sector
                WHERE sector IS NOT NULL
                RETURN DISTINCT sector
            """).data()
            neo4j_set = {r["sector"] for r in rows}

        self.assertEqual(
            neo4j_set, set(CANONICAL_SECTORS),
            (
                f"\nNeo4j/enum drift detected.\n"
                f"  In Neo4j but not in CANONICAL_SECTORS: {neo4j_set - CANONICAL_SECTORS}\n"
                f"  In CANONICAL_SECTORS but not in Neo4j: {CANONICAL_SECTORS - neo4j_set}\n"
                f"Action: update config/canonical_sectors.py AND the prose enum in\n"
                f".claude/skills/earnings-learner/SKILL.md in the same commit."
            ),
        )

    # ── CS2: SKILL.md prose ↔ module parity ──
    def test_CS2_skill_md_lists_all_canonical_sectors(self):
        """Every value in CANONICAL_SECTORS must appear verbatim in SKILL.md."""
        skill_path = _REPO_ROOT / ".claude" / "skills" / "earnings-learner" / "SKILL.md"
        self.assertTrue(skill_path.exists(), f"SKILL.md not found at {skill_path}")
        skill_text = skill_path.read_text(encoding="utf-8")
        missing = sorted(s for s in CANONICAL_SECTORS if s not in skill_text)
        self.assertFalse(
            missing,
            (
                f"\nSKILL.md prose enum is missing canonical sectors: {missing}\n"
                f"Action: update the sector-enum prose paragraph in\n"
                f".claude/skills/earnings-learner/SKILL.md to mention every canonical label."
            ),
        )

    # ── CS3: CANONICAL_SECTORS module self-consistency ──
    def test_CS3_module_self_consistency(self):
        """Sanity check the constant shape: frozenset, non-empty, ASCII-clean strings."""
        from config import canonical_sectors as mod
        self.assertIsInstance(mod.CANONICAL_SECTORS, frozenset)
        self.assertGreater(len(mod.CANONICAL_SECTORS), 0, "CANONICAL_SECTORS must be non-empty")
        for s in mod.CANONICAL_SECTORS:
            self.assertIsInstance(s, str, f"non-string value in CANONICAL_SECTORS: {s!r}")
            self.assertEqual(s.strip(), s, f"whitespace in sector label: {s!r}")
            self.assertTrue(s.isascii(), f"non-ASCII sector label: {s!r}")
            self.assertTrue(s, "empty sector label")


if __name__ == "__main__":
    unittest.main(verbosity=2)
