"""Canonical sector labels — hardcoded runtime enum, pre-commit-verified against Neo4j.

Single source of truth for:
  - the attribution validator's ``target_sector`` enum check
  - the ``.claude/skills/earnings-learner/SKILL.md`` prose enumeration
  - any future tooling that needs to know the sector universe

Runtime has **zero** Neo4j dependency — the validator runs inside a stdlib-only
PreToolUse hook, and any Neo4j-unreachable event must never silently permit
arbitrary sector strings. Instead, drift is caught by
``scripts/earnings/test_canonical_sectors_consistency.py`` (CS1), which runs
pre-commit, queries Neo4j's live distinct-sector set via
``coalesce(c.sector, sec.name)``, and fails loudly with a remediation message
if the two sets diverge.

Verified 2026-04-17 against Neo4j: 11 values, 796 companies with zero NULLs
within the intended universe.

If Neo4j's sector taxonomy ever changes, update this module AND the prose enum
in ``.claude/skills/earnings-learner/SKILL.md`` in the same commit — CS2 will
fail otherwise.
"""
from __future__ import annotations


CANONICAL_SECTORS: frozenset[str] = frozenset({
    "Technology",
    "Healthcare",
    "ConsumerCyclical",
    "Industrials",
    "FinancialServices",
    "ConsumerDefensive",
    "RealEstate",
    "Energy",
    "BasicMaterials",
    "CommunicationServices",
    "Utilities",
})
