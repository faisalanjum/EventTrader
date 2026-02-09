## Module Status & Implementation Order

### Readiness Matrix

| Module | Existing Asset | Plan Readiness | Gap Size | Key Blocker |
|--------|---------------|----------------|----------|-------------|
| **Planner** | No skill exists (`earnings-planner/` empty) | Spec ~90% done in `planner.md` + master `§2b` | **Small** | Prompt template + frontmatter only |
| **Predictor** | Skeleton `SKILL.md` (wrong output schema, allows `Task`/`Skill`/`filtered-data`) | Spec ~85% done in `predictor.md` + master `§2c` | **Medium** | Major skill rewrite: new `prediction_result.v1` schema, tool lockdown, rubric embedding |
| **Learner** | Old-design `SKILL.md` v2.2 (~10% aligned with new plan) | Scaffold in `learner.md` + master `§2d` | **Large** | Fundamental redesign: markdown-to-JSON output, new feedback contract, multi-model prep |
| **Guidance** | Working `SKILL.md` v1.6 + extraction agent + support files (QUERIES, OUTPUT_TEMPLATE, FISCAL_CALENDAR) | 18-section rebuild framework in `guidanceInventory.md` | **Small** | Integration spec (I5 bridge) + resolve G1-G8 |

### Open Questions by Module

| Module | P0 Open | P1 Open | P2 Open | Total Open |
|--------|---------|---------|---------|------------|
| Planner | 0 | 3 (P2-P4) | 0 | **3** |
| Predictor | 1 (R2) | 3 (R3-R5) | 0 | **4** |
| Learner | 0 | 3 (L3-L5) | 0 | **3** |
| Guidance | 3 (G1-G3) | 4 (G4-G7) | 1 (G8) | **8** |

**Total**: 4 P0 open (1 predictor + 3 guidance), 13 P1 open, 1 P2 open = **18 open questions**.

### Critical Path

```
Phase A: Interface Contracts ──── ALL 7 RESOLVED (I1-I7) ✓
    │
Phase B: Module Implementation (sequential)
    ├─ B1: Planner + Predictor (tightly coupled core loop)
    ├─ B2: Attribution/Learner (biggest redesign, depends on B1 outputs)
    └─ B3: Guidance Integration Hardening (parallel-safe with B2)
    │
Phase C: Final Consistency Pass
    ├─ C1: Skill-sync checklist (diff current vs required frontmatter)
    ├─ C2: File layout verification (cross-module path consistency)
    └─ C3: Implementation-ready checklist
```

### Dependency Chain

**DataSubAgents PIT layer** (owned by `DataSubAgents.md`) must be ready before planner can be tested with real data. All 11 existing agents need rework (PIT compliance, JSON envelope, `available_at` fields) and 3 planned agents (`web-search`, `sec-fulltext`, `presentations`) need to be built. Planner consumes this catalog but does not own it.
