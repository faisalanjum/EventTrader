# Global Lessons Schema — Structured Routing Permanent Fix

**Created**: 2026-04-17
**Status**: APPROVED — ready for single atomic-commit implementation
**Scope**: Replace the current `cross_ticker` stopgap (regex-based scope_key parsing + Neo4j-in-reader fallback) with a structured-schema permanent fix. Also fix the parallel silent-drop bug in the `sector` scope filter, and eliminate the `scope_key` "double duty" (routing + display) by adding `target_sector` + `related_tickers` as structured routing fields.

**Supersedes in `.claude/plans/learner.md`**: §8 (global_observations schema), §9 (`build_learning_context` filtering logic). Everything else in `learner.md` remains authoritative.

**Does NOT change**: the learner's invocation pattern (§10), PIT gating (§3), predictor contract, or any other subsystem.

**Interaction with `obsidian_thinking.md` (independent plan)** — orthogonal data domains. This plan touches `earnings-analysis/learnings/` (aggregate lessons); obsidian_thinking touches per-quarter artifacts under `earnings-analysis/Companies/*/events/*/` (thinking capture + artifact layout).

**Confirmed ship-order: THIS plan ships FIRST.** Rationale: (a) our post-commit wipe + 15-quarter re-run is safer against a quiet events tree, (b) obsidian_thinking's baseline migration is cleaner against a known-good learner dataset, (c) no shared function edits and no logical conflict.

**If obsidian_thinking ever ships first instead**, this plan's path literals, file names, and Python identifiers all need a coordinated find-replace pass (pure rename, no logic change). Full rename table — keep this synchronized with `.claude/plans/obsidian_thinking.md` if that plan mutates:

| This plan currently references | Rename to (if obsidian_thinking landed first) |
|---|---|
| `attribution/result.json` (path under `events/{Q}/`) | `learning/result.json` |
| `attribution/` (the per-quarter directory name) | `learning/` |
| `scripts/earnings/validate_attribution.py` | `scripts/earnings/validate_learning.py` |
| `.claude/hooks/validate_attribution_output.py` | `.claude/hooks/validate_learning_output.py` |
| `get_attribution_paths()` / `get_attribution_dir()` | `get_learning_paths()` / `get_learning_dir()` |
| `finalize_attribution_result()` | `finalize_learning_result()` |
| `prediction/context_bundle.{json,txt}` | `context_bundle.{json,txt}` (promoted to quarter root) |
| `prediction/ab_baseline/result_NO_LESSONS.json` | `experiments/prediction_no_lessons/result.json` |

See obsidian_thinking.md file-inventory section (lines ~245–260) for the authoritative rename list and motivation. The renames are mechanical — no logic change to any function or schema — so a ~15-minute coordinated pass (`sed -i` across this plan + the matching source-code files) is all that's required if ship-order reverses.

**Schema version policy (implementer-facing)**: `schema_version` in `attribution/result.json` stays at `"attribution_result.v2"` — NO bump. Rationale: (a) §5.1 audit confirms zero external consumers of this schema outside the repo; (b) the change is additive for new scopes plus a single removal (`scope_key`), not a breaking restructure; (c) clean-slate wipe eliminates all pre-amendment stored data, so there is no "mixed-version" read window. The validator at `scripts/earnings/validate_attribution.py` continues to hard-check `payload["schema_version"] == "attribution_result.v2"`; do NOT change that string. If a future change is genuinely breaking (e.g., removes a required routing field or changes semantics of an existing one), bump to `v3` at that point, not now.

---

## 0. TL;DR

Two silent-drop bugs in `scripts/earnings/earnings_orchestrator.py::build_learning_context`:

1. **`cross_ticker` scope** — originally `pass`-dropped every entry unconditionally (before codex's stopgap). Learner wrote them faithfully; storage preserved them; reader discarded them.
2. **`sector` scope** — used raw string equality `scope_key == sector`, which the learner routinely breaks by writing non-canonical labels (`"semiconductors"`, `"off_price_retail"`) while Neo4j returns canonical labels (`Technology`, `ConsumerCyclical`). Silently broken too.

Additionally, **`8k_packet.sector = None` on all 15 calibration bundles** (verified), so `build_prediction_bundle` could not know the current ticker's sector without an external lookup.

**Fix** (single atomic commit): introduce structured routing fields — `related_tickers` for `cross_ticker`, `target_sector` for `sector` — with validator enforcement and a canonical 11-value sector enum from Neo4j. **Remove `scope_key` entirely from the schema** (it was vestigial — not routed, not deduped, redundant with `lesson`). Keep `_lookup_company_sector` (Neo4j) for current-ticker sector resolution and for stamping `source_sector` audit metadata at write time. Add structured include/exclude observability counters. Wipe derived learnings (clean slate), re-run 15 quarters chronologically.

---

## 1. What codex already did (full record, so we can revert if needed)

Codex produced a **stopgap** before this plan. The plan REPLACES it atomically, so no explicit revert is needed — the new commit deletes the stopgap pieces while keeping the one independently-valuable improvement it introduced (the `8k_packet.sector=None` fallback). This section documents the exact current state so a revert is trivial if desired.

### 1.1 Files touched by codex

| File | State | Action under this plan |
|---|---|---|
| `scripts/earnings/earnings_orchestrator.py` | **Modified** — 90 additions, 15 deletions (uncommitted, `git status: M`) | Partially superseded. Delete regex/matcher machinery; keep sector-lookup helper + `build_prediction_bundle` fallback. |
| `scripts/earnings/test_learning_context.py` | **New file, untracked** (not in `git ls-files`) | **Rewrite entirely** against the new schema. |
| `scripts/earnings/utils.py` | Pre-existing (committed in `8eb6d3b`). Codex only added an import FROM it. | Unchanged. |

### 1.2 Exact content codex added to `earnings_orchestrator.py`

Captured verbatim from `git diff scripts/earnings/earnings_orchestrator.py`:

**Imports added (lines 15–25):**
```python
import re                                                     # ADDED
from functools import lru_cache                               # ADDED
from typing import Any, Callable                              # Callable ADDED
```
```python
from scripts.earnings.utils import neo4j_session              # ADDED
```

**Module-level constant added (~line 114):**
```python
_COMPANY_SECTOR_QUERY = """
MATCH (c:Company {ticker: $ticker})
OPTIONAL MATCH (c)-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(sec:Sector)
RETURN coalesce(c.sector, sec.name) AS sector
"""
```

**Four new module-level functions added (~lines 126–193):**
```python
@lru_cache(maxsize=512)
def _lookup_company_sector(ticker: str) -> str | None:
    """Best-effort sector lookup for learning-context filtering."""
    # ...full body as in current file...

def _normalize_sector(sector: str | None) -> str | None:
    # ...whitespace/case normalization...

def _extract_scope_key_tickers(scope_key: Any) -> list[str]:
    """Extract explicit uppercase ticker tokens from a cross_ticker scope key."""
    # ...regex [A-Za-z]{1,5} + .isupper() filter...

def _cross_ticker_matches(entry, current_ticker, current_sector, sector_lookup) -> bool:
    """Keep only cross_ticker lessons with an explicit same-sector ticker anchor."""
    # ...direct-ticker OR same-sector-via-peer-lookup...
```

**`build_prediction_bundle` change (~line 258):**
```python
# BEFORE:
sector = (results.get("8k_packet") or {}).get("sector")

# AFTER (codex):
sector = (results.get("8k_packet") or {}).get("sector") or _lookup_company_sector(ticker)
```

**`build_learning_context` signature + filter change (~lines 2096, 2144–2155):**
```python
# Signature gained sector_lookup optional parameter:
def build_learning_context(ticker: str, sector: str | None = None,
                           base_dir: Path | None = None,
                           sector_lookup: Callable[[str], str | None] | None = None) -> dict:

# Filter body changed from:
    elif scope == "cross_ticker" and sector:
        pass                                    # OLD: silent drop

# To:
    elif scope == "cross_ticker" and _cross_ticker_matches(e, ticker, sector, lookup):
        cross_entries.append(e)                 # CODEX: regex-anchored
```

### 1.3 What codex created: `scripts/earnings/test_learning_context.py`

New 149-line untracked file with three `unittest.TestCase` tests:

1. `test_cross_ticker_includes_same_sector_explicit_peer` — sector-lookup driven inclusion.
2. `test_cross_ticker_keeps_direct_ticker_match_without_sector` — direct-ticker-match path.
3. `test_build_prediction_bundle_falls_back_to_company_sector_lookup` — builder's Neo4j fallback.

### 1.4 Revert procedure (if ever needed)

If you want to revert codex entirely before or after this plan lands:

```bash
# 1. Revert the orchestrator change
git checkout HEAD -- scripts/earnings/earnings_orchestrator.py

# 2. Delete the untracked test file
rm scripts/earnings/test_learning_context.py

# 3. Verify clean state
git diff scripts/earnings/earnings_orchestrator.py   # should show no diff
ls scripts/earnings/test_learning_context.py         # should not exist
```

The revert returns `build_learning_context` to its pre-codex state (cross_ticker silently dropped via `pass`), with sector-scope filtering still broken per §2.2. **We do NOT recommend reverting without a replacement** — codex's patch is a strict improvement over pre-codex state on the cross_ticker channel, even if superseded by this plan.

### 1.5 What from codex survives into the permanent fix

- **`_lookup_company_sector`** + `_COMPANY_SECTOR_QUERY` + `neo4j_session` import — kept. Used at write-time (stamping `source_sector`) AND at bundle-build time (current-ticker sector when `8k_packet.sector` is None).
- **`_normalize_sector`** — kept. Used for all sector-string comparisons.
- **`build_prediction_bundle` fallback** (`or _lookup_company_sector(ticker)`) — kept. Required because `8k_packet.sector` is chronically None (§2.3).
- **`lru_cache`, `Callable` imports** — kept if still used.

### 1.6 What from codex gets DELETED by the permanent fix

- **`_extract_scope_key_tickers`** — obsolete; routing is by structured `related_tickers` field.
- **`_cross_ticker_matches`** — obsolete; reader logic is 5 lines inline.
- **`sector_lookup` parameter** on `build_learning_context` — obsolete; reader no longer does per-entry sector lookups.
- **`import re`** — delete if not used elsewhere in the module.
- **Codex's `test_learning_context.py`** — rewrite entirely against the new schema.

---

## 2. Problems solved (with concrete evidence)

### 2.1 Silent drop of every `cross_ticker` entry (pre-codex)

Reader code had `elif scope == "cross_ticker" and sector: pass` — every entry discarded. Writer and validator worked correctly; storage preserved entries; predictor never saw them.

**Direct evidence**: 10+ cross_ticker entries in the existing calibration corpus (AVGO, BURL) never reached any predictor. Examples:

- `Companies/AVGO/events/Q3_FY2023/attribution/result.json` → `scope_key="conglomerate_earnings"` (lesson about diversified-issuer veto-condition). Never reached TXN, MCHP, or ADI predictors.
- `Companies/BURL/events/Q1_FY2025/attribution/result.json` → `scope_key="ROST_BURL"` (lesson about peer-quality-match). Never reached ROST predictor.
- `Companies/BURL/events/Q2_FY2025/attribution/result.json` → `scope_key="sequential_beat_quality"` (cross-industry generalization). Never reached any predictor.

### 2.2 Silent drop on the `sector` scope via raw-equality match

Reader code: `if scope == "sector" and sector and e.get("scope_key") == sector`. Raw string equality.

**Direct evidence from real learner output**:
- AVGO Q3_FY2023 sector-scope: `scope_key="semiconductors"`. Neo4j sector for AVGO: `Technology`. `"semiconductors" != "Technology"` → silently dropped.
- AVGO Q4_FY2023 sector-scope: `scope_key="post_rally_earnings"`. Not a sector at all. Silently dropped.
- BURL Q1_FY2025 sector-scope: `scope_key="off_price_retail"`. Neo4j: `ConsumerCyclical`. Silently dropped.
- BURL Q2_FY2025 sector-scope: `scope_key="off_price_retail"`. Silently dropped.

The learner is using `scope_key` as an industry/theme tag, NOT as a canonical sector label. The plan never constrained it to be a canonical label. Result: sector-scope channel was nearly as broken as cross_ticker.

### 2.3 `8k_packet.sector = None` on all 15 calibration bundles

Verified via a script over every `prediction/context_bundle.json`:

```
AVGO: 5/5 quarters → sector=None
NVDA: 5/5 quarters → sector=None
BURL: 5/5 quarters → sector=None
```

**Root cause**: `builder_adapters.build_8k_packet` delegates to the legacy `warmup_cache.build_8k_packet`, which does not populate `sector`. `_enrich_packet` adds PIT metadata but not sector. This means `build_prediction_bundle` could NEVER know the current ticker's sector without an external Neo4j lookup — so codex's `or _lookup_company_sector(ticker)` fallback is load-bearing, not optional.

### 2.4 Observability: zero

No log, no metric, no test covered ANY of these silent drops. The only reason this bug was discovered was manual code review.

### 2.5 `scope_key` doing double duty

`scope_key` simultaneously (a) identifies the routing target (e.g., sector name) and (b) carries a human-readable theme tag. These are incompatible jobs. The cleanest fix is to introduce structured routing fields (`target_sector`, `related_tickers`) — and then **remove `scope_key` entirely**, because once routing is structured the field has no remaining job (it's not routed, not deduped, and duplicates information already carried by `lesson`).

---

## 3. Canonical sector enum — from Neo4j audit

Verified 2026-04-17 against the live Neo4j graph:

```
Technology              (n=162)
Healthcare              (n=145)
ConsumerCyclical        (n=121)
Industrials             (n=110)
FinancialServices       (n=54)
ConsumerDefensive       (n=44)
RealEstate              (n=36)
Energy                  (n=35)
BasicMaterials          (n=34)
CommunicationServices   (n=30)
Utilities               (n=25)
─────────────────────────────
TOTAL                   796 companies (zero NULLs within the universe)
```

- Both `Company.sector` property AND `Industry→Sector` relationship yield the same 11 values.
- `coalesce(c.sector, sec.name)` is robust — both paths return identical labels.
- Three FAANG tickers return None (`MSFT`, `GOOGL`, `META`) because they're OUT of the 796-company universe. Harmless: `source_ticker` in `append_global_lessons` is always a current-run ticker (which IS in the universe).

### 3.1 How the enum lives in code — `config/canonical_sectors.py` (NEW)

**Single hardcoded Python constant + pre-commit consistency test** — the best-of-both-worlds design.

- **Why hardcode**: validator runs inside a stdlib-only PreToolUse hook; adding Neo4j at validate-time would break the fail-closed invariant. SKILL.md must enumerate the list in prose for the LLM anyway. A Neo4j-unreachable event must never silently permit arbitrary sector strings.
- **Why not stale**: a pre-commit consistency test queries Neo4j and compares the live distinct-sector set against the hardcoded enum. Any drift fails CI loudly with a specific action ("update `config/canonical_sectors.py` and SKILL.md").

**Module:**

```python
# config/canonical_sectors.py  (new file)
"""Canonical sector labels — hardcoded runtime enum, CI-verified against Neo4j.

Single source of truth for the validator + SKILL.md prose list. Runtime
has zero Neo4j dependency. A pre-commit test (test_canonical_sectors_consistency.py)
fails loudly if Neo4j's distinct sector set ever diverges from this enum.
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
```

**Imported by** `validate_attribution.py` (single import, replaces the inline `_CANONICAL_SECTORS` block shown in §6.1).

**Hook compatibility note**: `config/canonical_sectors.py` lives at the repo root, not inside `scripts/earnings/`. The PreToolUse hook (`.claude/hooks/validate_attribution_output.py`) currently only adds `scripts/earnings` to `sys.path`. It MUST be modified to add `project_dir` itself first — otherwise `from config.canonical_sectors import CANONICAL_SECTORS` fails under hook execution, triggering fail-closed behavior and blocking every learner write. See §5 file inventory row 3.

### 3.2 `_lookup_company_sector` — only cache successes (anti-poisoning)

The existing helper (kept from codex) uses `@lru_cache(maxsize=512)`. This caches every return value — including `None` on transient Neo4j failures. For unmonitored runs, a single Neo4j hiccup at startup could poison the cache for the entire session.

**Fix**: replace `@lru_cache` with a manual dict cache that only stores successful lookups. Failed/None lookups re-query every time (bounded by LRU eviction would also be fine, but the manual dict is simpler and the universe is 796 entries).

```python
# scripts/earnings/earnings_orchestrator.py
_SECTOR_CACHE: dict[str, str] = {}  # module-level, successes ONLY

def _lookup_company_sector(ticker: str) -> str | None:
    """Sector lookup. Only successful results are cached — None results re-query
    on every call so transient Neo4j failures cannot poison the cache."""
    symbol = str(ticker or "").upper().strip()
    if not symbol:
        return None
    if symbol in _SECTOR_CACHE:
        return _SECTOR_CACHE[symbol]

    try:
        with neo4j_session() as (session, err):
            if err or session is None:
                log.warning("Sector lookup unavailable for %s: %s", symbol, err)
                return None  # NOT cached
            row = session.run(_COMPANY_SECTOR_QUERY, ticker=symbol).single()
    except Exception as e:
        log.warning("Sector lookup failed for %s: %s", symbol, e)
        return None  # NOT cached

    if not row:
        return None
    sector = (row.data().get("sector") or "").strip()
    if not sector:
        return None
    _SECTOR_CACHE[symbol] = sector  # successes only
    return sector
```

Behavior: successful lookup for AAPL caches `"Technology"`; subsequent calls O(1). If Neo4j is down when we first call for AAPL, we log + return None, and the next AAPL call actually retries. No session-long poisoning.

**pre-commit consistency tests** — see §7.5.

**This 11-value enum is frozen and shipped verbatim into SKILL.md + validator.** If Neo4j's sector list ever changes, the validator + SKILL.md must be updated together.

---

## 4. Final schema contract — every field, every scope

### 4.1 Learner-authored fields (in `attribution/result.json::global_observations[]`)

**`scope_key` is REMOVED from the schema** (amendment 2026-04-17). It was vestigial — not used by the router, the dedupe step, the validator's logic, or any predictor action. `lesson` is the content; routing fields are structured. Nothing made up, nothing unused.

#### `scope = "cross_ticker"`
```json
{
  "scope": "cross_ticker",
  "related_tickers": ["AAA", "BBB"],
  "lesson": "..."
}
```
- `related_tickers`: **REQUIRED, non-empty**, list of uppercase alphabetic strings, each 1–5 chars, **max 8 entries**. Duplicate rejection is **validator-authoritative** (writer does not dedupe — validator fails the write and triggers learner retry on duplicates).
- `target_sector`, `scope_key`: **MUST NOT be present.** Validator rejects if present.

#### `scope = "sector"`
```json
{
  "scope": "sector",
  "target_sector": "Technology",
  "lesson": "..."
}
```
- `target_sector`: **REQUIRED**, must be exactly one of the 11 canonical enum values in §3 (imported from `config.canonical_sectors`). Validator rejects any other value.
- `related_tickers`, `scope_key`: **MUST NOT be present.** Validator rejects if present.

#### `scope = "macro"`
```json
{
  "scope": "macro",
  "lesson": "..."
}
```
- `related_tickers`, `target_sector`, `scope_key`: **MUST NOT be present.** Validator rejects any of them.

### 4.2 Python-stamped fields (added by `append_global_lessons` to `learnings/global.json::entries[]`)

Applied uniformly to every entry regardless of scope:

| Field | Source | Purpose |
|---|---|---|
| `source_ticker` | `attribution_result.ticker` | Audit: which ticker's learner produced this lesson |
| `source_sector` | `_lookup_company_sector(source_ticker)` | Audit ONLY. **Not used for routing.** May be `None` if Neo4j lookup fails; that's fine — filter never reads it. |
| `quarter_label` | `attribution_result.quarter_label` | Audit |
| `attributed_at` | `attribution_result.attributed_at` | Used for recency sort at read time |

### 4.3 Reader routing logic (exact)

```python
normalized_current_sector = _normalize_sector(sector)

for e in entries:
    scope = e.get("scope")
    if scope == "sector":
        if normalized_current_sector and \
           _normalize_sector(e.get("target_sector")) == normalized_current_sector:
            sector_entries.append(e)
        else:
            excluded["sector_mismatch"] += 1

    elif scope == "macro":
        macro_entries.append(e)

    elif scope == "cross_ticker":
        if ticker in (e.get("related_tickers") or []):
            cross_entries.append(e)
        else:
            excluded["cross_ticker_not_listed"] += 1

    else:
        excluded["unknown_scope"] += 1
```

**Design invariants — MUST hold in every future change:**
- Routing fields are structured. No regex. No free-string matching. No Neo4j calls inside the per-entry filter.
- `scope_key` is NEVER read by the routing logic for any scope.
- `source_sector` is NEVER read by the routing logic.
- Every exclusion increments a named counter. No silent drops.

### 4.4 Per-scope caps (unchanged from current)

After recency sort and dedupe by lesson-text-normalized:
- `sector_entries[:4]`
- `macro_entries[:4]`
- `cross_entries[:2]`

Total: ≤10 global entries rendered into bundle Section 10.

### 4.5 Observability contract

Emitted once per `build_learning_context` call — ALWAYS (even when `global.json` is absent):

```
log.info(
    "learning_context %s(sector=%s): "
    "included[sector=%d macro=%d cross=%d] "
    "excluded[sector_mismatch=%d current_sector_unknown=%d "
    "cross_ticker_not_listed=%d cross_ticker_missing_related=%d "
    "unknown_scope=%d legacy_schema=%d]",
    ticker, sector,
    len(sector_entries), len(macro_entries), len(cross_entries),
    excluded["sector_mismatch"],
    excluded["current_sector_unknown"],
    excluded["cross_ticker_not_listed"],
    excluded["cross_ticker_missing_related"],
    excluded["unknown_scope"],
    excluded["legacy_schema"],
)
```

**Six named exclusion counters, all zero by default** (so the log line is fully populated even in the empty-file case):

| Counter | Fires when |
|---|---|
| `sector_mismatch` | Entry's `target_sector` is present and valid but does not match the current ticker's sector |
| `current_sector_unknown` | The current ticker's sector is None/empty, so sector-scope filtering cannot run |
| `cross_ticker_not_listed` | Entry's `related_tickers` is non-empty but does not contain the current ticker |
| `cross_ticker_missing_related` | Entry has `scope="cross_ticker"` but no `related_tickers` (legacy/malformed) |
| `unknown_scope` | Entry's `scope` is not one of `sector`/`macro`/`cross_ticker` |
| `legacy_schema` | Sector-scope entry missing `target_sector` (old-schema residue post-wipe) |

**Absent-file case**: when `global.json` does not exist (e.g., immediately post-wipe), the function still emits the log line with all counters at zero and all included counts at zero. This guarantees there is never a "silent silence" where nothing at all is logged — the operator can always see the filter fired.

Any future silent-drop regression appears immediately as an anomalous exclusion count.

---

## 5. File-by-file change inventory (single atomic commit)

| # | File | Action | Lines touched (approx) |
|---|---|---|---|
| 1 | `config/canonical_sectors.py` | **NEW** — single hardcoded `CANONICAL_SECTORS` frozenset. Imported by validator. Per §3.1. | +20 |
| 2 | `scripts/earnings/validate_attribution.py` | **Add** strict validation block per §6.1: required fields by scope, rejected fields by scope (including `scope_key` universally), enum check on `target_sector` via `from config.canonical_sectors import CANONICAL_SECTORS`, shape check + **duplicate rejection** on `related_tickers`. | +45 |
| 3 | `.claude/hooks/validate_attribution_output.py` | **Modify** — add `sys.path.insert(0, project_dir)` BEFORE the existing `scripts/earnings` insert so the validator can import `from config.canonical_sectors import CANONICAL_SECTORS` under hook execution. Without this, the hook fails-closed on import and blocks every learner write. | +1 |
| 4 | `scripts/earnings/earnings_orchestrator.py::append_global_lessons` | **Modify** — stamp `source_sector` via `_lookup_company_sector`; pass through `related_tickers` and `target_sector`; **drop `scope_key` pass-through**; **convert to upsert-by-`(source_ticker, quarter_label)`** per §6.2. | +12 |
| 5 | `scripts/earnings/earnings_orchestrator.py::append_ticker_lesson` | **Modify** — convert to upsert-by-`quarter_label` so re-runs don't duplicate entries. Per §6.2. | +5 |
| 6 | `scripts/earnings/earnings_orchestrator.py::build_learning_context` | **Modify** — replace filter body with §4.3 / §6.3 structured logic; add exclusion counters; drop `sector_lookup` parameter; normalize sector on both sides; **log on `except` paths** (no silent infrastructure failure). | +25 / −15 |
| 7 | `scripts/earnings/earnings_orchestrator.py` deletions | **Delete** `_extract_scope_key_tickers` + `_cross_ticker_matches`. Remove `import re` if no other use. Remove `Callable` from typing import if no other use. Remove `sector_lookup` callable threading anywhere else. | −40 |
| 8 | `scripts/earnings/earnings_orchestrator.py::_render_learning_context` | **Modify** — split single "### Cross-Ticker Insights" heading into three sub-sections; **drop all `scope_key` display references** (field removed from schema). | +15 / −8 |
| 9 | `scripts/earnings/earnings_orchestrator.py` — add observability log | Insert the §4.5 log line just before `return result`. Include the `excluded` dict initialization at start of filter block. | +8 |
| 10 | `.claude/skills/earnings-learner/SKILL.md` | **Modify** — update "Global observations" section per §6.7: **remove `scope_key` from required fields everywhere**; document `target_sector` enum (imported value list) and `related_tickers` shape rules. Add three worked examples. | +30 / −15 |
| 11 | `.claude/plans/learner.md` §8 + §9 | **Modify** — update schema JSON blocks and filter description to match new contract (no `scope_key`). Reference this plan as the authoritative source for global-lessons routing. | +20 / −30 |
| 12 | `scripts/earnings/test_learning_context.py` | **Rewrite entirely** — drop codex's regex-based tests. Add R1–R15 per §7.3, W1–W8 per §7.2, I1–I10 per §7.4 (I10 is the informed-retry H2 acceptance gate). | +270 / −149 |
| 13 | `scripts/earnings/test_validate_attribution.py` | **New file** — V1–V20 validator tests per §7.1 (including `scope_key`-rejection test V19 and duplicate-rejection test V20). | +200 |
| 14 | `scripts/earnings/test_canonical_sectors_consistency.py` | **New file** — CS1–CS3 per §7.5: Neo4j ↔ module parity, SKILL.md ↔ module parity, module self-consistency. Required in pre-commit checklist (§8.1); see §10 for CI-workflow status. | +60 |
| 15 | Data wipe | `cp -r earnings-analysis/learnings earnings-analysis/learnings.backup.$(date +%s)` then `rm earnings-analysis/learnings/global.json earnings-analysis/learnings/ticker/*.json`. NOT committed; operator action. | — |

**Net code change**: ~+520 / −260. Net +260 lines from today's state (adds tests, consistency checker, canonical module; deletes regex machinery and `scope_key` threading).

### 5.1 External consumer surface — audited and bounded

Grep across the repo for `global.json|learnings/ticker|related_tickers|source_sector|global_observations|target_sector|cross_ticker` confirms the ONLY code consumers of these schemas are:

- `scripts/earnings/earnings_orchestrator.py`
- `scripts/earnings/validate_attribution.py`
- `.claude/skills/earnings-learner/SKILL.md`
- `scripts/earnings/test_learning_context.py`

Docs-only references (no code impact):
- `.claude/plans/learner.md`, `.claude/plans/earnings-orchestrator.md`, `.claude/plans/obsidian_thinking.md`, `.claude/plans/trade-execution-system.md`
- `learning-loop-explainer.html`, `trade-system-explorer.html`

False-positive hits (unrelated):
- `eventReturns/polygonClass.py` — `related_tickers` is a local Polygon-API variable, not our schema
- `scripts/run_burl_ab_sequential.py`, `scripts/run_nvda_ab_sequential.py` — docstring mentions only
- `neograph/Neo4jInitializer.py` — irrelevant string match

**No hidden readers. Change surface fully enumerated.**

---

## 6. Implementation details (exact code snippets)

### 6.1 `validate_attribution.py` — new block

Imports from the single-source-of-truth module added in §3.1:

```python
from config.canonical_sectors import CANONICAL_SECTORS

def _ok_ticker(t: object) -> bool:
    return isinstance(t, str) and t.isupper() and t.isalpha() and 1 <= len(t) <= 5

_MAX_RELATED_TICKERS = 8
_REJECTED_SCOPE_KEY_MSG = "scope_key has been removed from the schema; do not emit"

# ... inside the loop over global_observations entries:
scope = obs.get("scope")
rt = obs.get("related_tickers")
ts = obs.get("target_sector")
sk = obs.get("scope_key")  # ← must never be present in the new schema

# scope_key removed from schema (amendment 2026-04-17). Reject if present,
# across ALL scopes, so learner output is forced to converge to the new shape.
if sk is not None:
    errors.append(f"global_observations[{i}].scope_key: {_REJECTED_SCOPE_KEY_MSG}")

if scope == "cross_ticker":
    if not isinstance(rt, list) or not rt:
        errors.append(f"global_observations[{i}].related_tickers must be a non-empty list for cross_ticker")
    else:
        if len(rt) > _MAX_RELATED_TICKERS:
            errors.append(f"global_observations[{i}].related_tickers exceeds cap {_MAX_RELATED_TICKERS} (got {len(rt)})")
        bad = [t for t in rt if not _ok_ticker(t)]
        if bad:
            errors.append(f"global_observations[{i}].related_tickers contains invalid tickers: {bad}")
        # Validator-authoritative dedupe (writer does NOT dedupe):
        if len(set(rt)) != len(rt):
            errors.append(f"global_observations[{i}].related_tickers contains duplicates")
    if ts is not None:
        errors.append(f"global_observations[{i}].target_sector must not be present for cross_ticker scope")

elif scope == "sector":
    if not isinstance(ts, str) or ts not in CANONICAL_SECTORS:
        errors.append(
            f"global_observations[{i}].target_sector must be one of "
            f"{sorted(CANONICAL_SECTORS)} (got {ts!r})"
        )
    if rt is not None:
        errors.append(f"global_observations[{i}].related_tickers must not be present for sector scope")

elif scope == "macro":
    if rt is not None:
        errors.append(f"global_observations[{i}].related_tickers must not be present for macro scope")
    if ts is not None:
        errors.append(f"global_observations[{i}].target_sector must not be present for macro scope")
```

**"Did you mean" hints (H3, amendment 2026-04-17)** — because the system runs unmonitored with no escape hatch, validator error messages must be actionable enough that the 1-retry path (H2) can self-correct. Use stdlib `difflib` only; no new dependencies:

```python
from difflib import get_close_matches

# For target_sector: if the value is a string but not in the enum, suggest canonicals:
if isinstance(ts, str) and ts not in CANONICAL_SECTORS:
    suggestions = get_close_matches(ts, CANONICAL_SECTORS, n=2, cutoff=0.5)
    hint = f" (did you mean: {', '.join(repr(s) for s in suggestions)}?)" if suggestions else ""
    errors.append(
        f"global_observations[{i}].target_sector must be one of "
        f"{sorted(CANONICAL_SECTORS)} (got {ts!r}){hint}"
    )

# For related_tickers: if a string is provided instead of a list, suggest the list form.
# REGEX-FREE: uses str.translate + split on a known separator set so the "no regex
# anywhere in the fix" invariant holds even in the error-hint path.
_RELATED_TICKERS_SEPARATORS = "_ ,/|-"
_RELATED_TICKERS_SEP_TABLE = str.maketrans({c: " " for c in _RELATED_TICKERS_SEPARATORS})

if scope == "cross_ticker" and isinstance(rt, str):
    normalized = rt.upper().translate(_RELATED_TICKERS_SEP_TABLE)
    tokens = [t for t in normalized.split() if _ok_ticker(t)]
    hint = f" (did you mean: {tokens!r}?)" if tokens else ""
    errors.append(
        f"global_observations[{i}].related_tickers must be a list, got string {rt!r}{hint}"
    )
```

**Regex policy in the final design — zero regex anywhere.** The deleted `_extract_scope_key_tickers` / `_cross_ticker_matches` machinery used regex as a routing oracle. That's gone. The validator's error-hint path that previously used `re.split` now uses `str.translate` + `str.split` on a known separator set — no regex, same behavior, cleaner invariant. After this commit, `grep -n '\bimport re\b\|\bre\.' scripts/earnings/validate_attribution.py scripts/earnings/earnings_orchestrator.py` MUST return nothing related to learning-context routing.

**Duplicate authority rule (clarified 2026-04-17)**: the validator is the SINGLE authority on `related_tickers` shape — non-empty, uppercase 1–5 char, max 8, **no duplicates**. The writer is a pure pass-through; it does NOT dedupe. Rationale: fail fast, retry the learner, converge to clean output. Silent writer-side dedupe would mask authoring errors instead of signaling them back for correction.

### 6.2 `append_global_lessons` — stamping additions

```python
for obs in observations:
    enriched.append({
        "scope":            obs.get("scope"),
        # NOTE: scope_key removed from schema (amendment 2026-04-17).
        #       Writer does NOT pass it through. Validator rejects it on writes.
        # Pass-through structured routing fields:
        "related_tickers":  obs.get("related_tickers"),   # may be None (non-cross_ticker)
        "target_sector":    obs.get("target_sector"),     # may be None (non-sector)
        # Existing audit fields:
        "source_ticker":    attribution_result.get("ticker"),
        # source_sector audit metadata (NOT routing):
        "source_sector":    _lookup_company_sector(attribution_result.get("ticker")),
        "quarter_label":    attribution_result.get("quarter_label"),
        "attributed_at":    attribution_result.get("attributed_at"),
        "lesson":           obs.get("lesson"),
    })
```

**Idempotent upsert (NEW, amendment 2026-04-17)** — the current append functions are pure-append; on derived-write recovery or any re-run they accumulate duplicate entries in `global.json` / `ticker.json`. Replace pure `.append` / `.extend` with **upsert-by-source-key**, AND **remove the early-return when `observations` is empty** so that a re-run producing zero global observations still deletes any stale entries for that quarter:

```python
# append_global_lessons — idempotent by (source_ticker, quarter_label).
# IMPORTANT: do NOT early-return when observations == []. A re-run that
# produces zero global_observations must still purge any prior entries
# for (source_ticker, quarter_label), otherwise stale entries survive forever.
observations = attribution_result.get("global_observations", [])
enriched = [
    {
        "scope":            obs.get("scope"),
        "related_tickers":  obs.get("related_tickers"),
        "target_sector":    obs.get("target_sector"),
        "source_ticker":    attribution_result.get("ticker"),
        "source_sector":    _lookup_company_sector(attribution_result.get("ticker")),
        "quarter_label":    attribution_result.get("quarter_label"),
        "attributed_at":    attribution_result.get("attributed_at"),
        "lesson":           obs.get("lesson"),
    }
    for obs in observations
]

path = LEARNINGS_DIR / "global.json"
path.parent.mkdir(parents=True, exist_ok=True)

lock_path = path.with_suffix(".lock")
with open(lock_path, "w") as lock_fd:
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = {"schema_version": "global_lessons.v1", "updated_at": None, "entries": []}

        # Upsert step — always runs, even when enriched is []:
        key = (attribution_result["ticker"], attribution_result["quarter_label"])
        data["entries"] = [e for e in data["entries"]
                           if (e.get("source_ticker"), e.get("quarter_label")) != key]
        data["entries"].extend(enriched)
        data["updated_at"] = attribution_result.get("attributed_at")
        _atomic_write_json(path, data)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
return path

# append_ticker_lesson — idempotent by quarter_label:
target_ql = entry["quarter_label"]
data["lessons"] = [l for l in data["lessons"]
                   if l.get("quarter_label") != target_ql]
data["lessons"].append(entry)
```

This converts "append" semantics to "upsert by source key." First write for a quarter: unchanged. Re-run producing the same set: replaced in place. Re-run producing zero observations: stale entries **purged**. Reader-side dedupe (`_dedupe` by normalized lesson text) still provides a defense-in-depth layer for routing correctness.

**Contract change (explicit)**: `append_global_lessons` used to be documented as *"Returns the path written, or None if no observations."* After this amendment, it **always** returns the path — including in the zero-observations case, where the function still performs the flock-protected upsert to purge any stale entries. Update the docstring to match. Any caller that checked `result is None` as an "empty observations" signal must be updated; a grep of the current repo shows `run_learner_for_quarter` is the only caller and it doesn't condition on the return value, so no caller-side change is needed beyond the docstring.

**Ground-truth note (verified 2026-04-17 by sanity-check read)**: the current `append_global_lessons` enrichment dict at lines 2060–2067 of `earnings_orchestrator.py` does NOT stamp `source_sector` at all — it only contains `scope, scope_key, source_ticker, quarter_label, attributed_at, lesson`. Adding `source_sector` is a pure **field addition**, not a replacement of an existing value; there is no prior source_sector to migrate. The `scope_key` drop is the only field removal. The return-type annotation `-> Path | None` stays as-is (the function can still return None if an exception propagates after the lock releases; the functional contract "always returns path on success" is documented in the docstring, not the type signature). Minimal-diff principle.

**`_lookup_company_sector` behavior**: see §3.2 — the `@lru_cache` decorator is replaced with a manual dict cache that stores ONLY successful lookups, and None-returning paths emit `log.warning`. Any reference to `@lru_cache` on this helper is an old-codex artifact; the authoritative spec is §3.2.

### 6.3 `build_learning_context` — full replacement for the global-filter block

```python
# ── Global lessons: structured-field routing, per-scope caps ──
# Counters are initialized to zero BEFORE the file-exists check so the
# log line at the end always fires with a full, consistent shape —
# even if global.json is absent (first-ever run, post-wipe state).
sector_entries = []
macro_entries = []
cross_entries = []
excluded = {
    "sector_mismatch": 0,
    "current_sector_unknown": 0,
    "cross_ticker_not_listed": 0,
    "cross_ticker_missing_related": 0,
    "unknown_scope": 0,
    "legacy_schema": 0,
}
normalized_current_sector = _normalize_sector(sector)

if global_path.exists():
    try:
        data = json.loads(global_path.read_text(encoding="utf-8"))
        entries = data.get("entries", [])

        for e in entries:
            scope = e.get("scope")

            if scope == "sector":
                ts = e.get("target_sector")
                if ts is None:
                    # Legacy/old-schema entry (pre-fix) — transparently excluded
                    excluded["legacy_schema"] += 1
                    continue
                if not normalized_current_sector:
                    # The CURRENT ticker's sector is unknown — cannot route sector-scope.
                    # (Not to be confused with legacy_schema, which is about the ENTRY.)
                    excluded["current_sector_unknown"] += 1
                    continue
                if _normalize_sector(ts) == normalized_current_sector:
                    sector_entries.append(e)
                else:
                    excluded["sector_mismatch"] += 1

            elif scope == "macro":
                macro_entries.append(e)

            elif scope == "cross_ticker":
                rt = e.get("related_tickers")
                if not rt:
                    # Legacy/old-schema entry OR learner error past validator — excluded
                    excluded["cross_ticker_missing_related"] += 1
                    continue
                if ticker in rt:
                    cross_entries.append(e)
                else:
                    excluded["cross_ticker_not_listed"] += 1

            else:
                excluded["unknown_scope"] += 1

        # Sort by recency, dedupe by normalized lesson text, apply caps
        for bucket in (sector_entries, macro_entries, cross_entries):
            bucket.sort(key=lambda x: x.get("attributed_at", ""), reverse=True)

        def _dedupe(items):
            seen = set()
            out = []
            for item in items:
                k = (item.get("lesson") or "").strip().lower()
                if k and k not in seen:
                    seen.add(k)
                    out.append(item)
            return out

        sector_entries = _dedupe(sector_entries)[:4]
        macro_entries  = _dedupe(macro_entries)[:4]
        cross_entries  = _dedupe(cross_entries)[:2]

        result["global_lessons"] = sector_entries + macro_entries + cross_entries
    except json.JSONDecodeError as e:
        # Amendment 2026-04-17: no silent failures, even on infrastructure errors.
        log.error("global.json malformed — no global lessons loaded for %s: %s", ticker, e)
    except OSError as e:
        log.error("global.json read failed — no global lessons loaded for %s: %s", ticker, e)

# Observability log — fires ALWAYS, even when global_path didn't exist.
# Names must match §4.5 contract exactly. Six exclusion counters, all initialized
# to zero so the log line shape is stable on any code path.
log.info(
    "learning_context %s(sector=%s): "
    "included[sector=%d macro=%d cross=%d] "
    "excluded[sector_mismatch=%d current_sector_unknown=%d "
    "cross_ticker_not_listed=%d cross_ticker_missing_related=%d "
    "unknown_scope=%d legacy_schema=%d]",
    ticker, sector,
    len(sector_entries), len(macro_entries), len(cross_entries),
    excluded["sector_mismatch"],
    excluded["current_sector_unknown"],
    excluded["cross_ticker_not_listed"],
    excluded["cross_ticker_missing_related"],
    excluded["unknown_scope"],
    excluded["legacy_schema"],
)
```

**Note**: the analogous `except` block on the ticker-lessons read block above this section must also log on failure. Both paths preserve the defensive "predictor bundle still builds even if lessons unavailable" semantics, but now log operator-visible errors instead of silently returning empty lessons. `log.error` is deliberate (not `warning`) — a corrupted `global.json` or disk read failure is an infrastructure incident, not a routine condition.

### 6.4 `_render_learning_context` — heading split (scope_key removed)

```python
# Replace the single-heading global section with three sub-sections.
# scope_key is no longer in the schema; rendering uses routing fields only.
if global_lessons:
    by_scope = {"sector": [], "macro": [], "cross_ticker": []}
    for entry in global_lessons:
        by_scope.setdefault(entry.get("scope"), []).append(entry)

    if by_scope["sector"]:
        parts.append(f"\n### Sector Lessons ({len(by_scope['sector'])} entries)\n")
        for entry in by_scope["sector"]:
            ts = entry.get("target_sector") or "?"
            src = entry.get("source_ticker") or "?"
            parts.append(f"- [sector:{ts}] ({src}) {entry.get('lesson','')}")

    if by_scope["macro"]:
        parts.append(f"\n### Macro Lessons ({len(by_scope['macro'])} entries)\n")
        for entry in by_scope["macro"]:
            src = entry.get("source_ticker") or "?"
            parts.append(f"- [macro] ({src}) {entry.get('lesson','')}")

    if by_scope["cross_ticker"]:
        parts.append(f"\n### Cross-Ticker Lessons ({len(by_scope['cross_ticker'])} entries)\n")
        for entry in by_scope["cross_ticker"]:
            rt = entry.get("related_tickers") or []
            src = entry.get("source_ticker") or "?"
            parts.append(f"- [cross:{','.join(rt)}] ({src}) {entry.get('lesson','')}")
```

### 6.5 Deletions

Remove entire function bodies:
- `_extract_scope_key_tickers` (lines ~160–171)
- `_cross_ticker_matches` (lines ~174–193)

Remove `sector_lookup` parameter from `build_learning_context` signature and all internal references (`lookup = sector_lookup or _lookup_company_sector` line).

Remove `import re` if no other occurrence in the file. Verify with grep.

Remove `Callable` from `typing import` if no other occurrence.

### 6.6 Informed-retry prompt (H2 — compensating hardening for no-escape-hatch design)

Because this pipeline runs unmonitored and has no permissive fallback, the 1-retry path in `run_learner_for_quarter` MUST be informed by the prior validation errors, not a blind re-run with the same prompt. This is the H2 hardening referenced in R1 mitigation (§9).

**Signature changes** — three functions gain one optional parameter each:

```python
# scripts/earnings/earnings_orchestrator.py

def _build_learner_prompt(
    skill_content: str,
    ticker: str,
    quarter_info: dict,
    actual_return: dict,
    pit_mode: str,
    pit_cutoff: str | None,
    pit_boundary_source: str,
    result_path: Path,
    prediction_result_path: Path,
    context_bundle_path: Path,
    prior_lessons_path: Path,
    prior_validation_errors: list[str] | None = None,  # NEW
) -> str:
    inputs_section = f"""--- INPUTS ---
TICKER: {ticker}
QUARTER: {quarter_info.get('quarter_label', 'UNKNOWN')}
...
"""
    if prior_validation_errors:
        numbered = "\n".join(f"  {i+1}. {e}" for i, e in enumerate(prior_validation_errors))
        retry_block = (
            "\n--- YOUR PRIOR OUTPUT WAS REJECTED ---\n"
            "The previous attempt failed schema validation with these errors:\n"
            f"{numbered}\n\n"
            "Fix these EXACT errors and re-emit attribution/result.json. "
            "Do not change other fields; only correct the listed shape issues.\n"
        )
        return f"{skill_content}\n\n{inputs_section}{retry_block}"
    return f"{skill_content}\n\n{inputs_section}"


async def _run_learner_via_sdk(
    ..., prior_validation_errors: list[str] | None = None,  # NEW
) -> str | None:
    ...
    prompt = _build_learner_prompt(..., prior_validation_errors=prior_validation_errors)
    ...


def run_learner_via_sdk(
    ..., prior_validation_errors: list[str] | None = None,  # NEW
) -> str | None:
    return asyncio.run(_run_learner_via_sdk(..., prior_validation_errors=prior_validation_errors))
```

**Retry call site change** in `run_learner_for_quarter` — the existing retry block:

```python
# BEFORE (blind retry):
if errors:
    log.error("Learner failed %s %s: validation errors: %s", ...)
    result_path.unlink(missing_ok=True)
    log.info("Retrying learner for %s %s (1 retry)", ...)
    run_learner_via_sdk(ticker=ticker, quarter_info=quarter_info, ...)  # same args

# AFTER (informed retry):
if errors:
    log.error("Learner failed %s %s: validation errors: %s", ticker, ql, "; ".join(errors[:3]))
    result_path.unlink(missing_ok=True)
    log.info("Retrying learner for %s %s (1 retry, feeding %d validation errors back)",
             ticker, ql, len(errors))
    run_learner_via_sdk(
        ticker=ticker,
        quarter_info=quarter_info,
        actual_return=actual_return,
        pit_mode=pit_mode,
        pit_cutoff=pit_cutoff,
        pit_boundary_source=pit_boundary_source,
        result_path=result_path,
        prediction_result_path=attr_paths["prediction_result_path"],
        context_bundle_path=attr_paths["context_bundle_path"],
        prior_lessons_path=learn_paths["ticker_lessons_path"],
        prior_validation_errors=errors,  # NEW — informs the retry
    )
```

**Why this is the real replacement for `STRICT_SCHEMA`**:

| Property | Escape hatch (rejected) | Informed retry (chosen) |
|---|---|---|
| Fail-safe if learner can't produce new schema | Silent permissive mode — pollutes data | Fails loudly; ticker chain stops |
| Observable | Might flip ON and stay on for weeks | Every retry logs exactly what was fed back |
| Reversible | Operator must remember to flip OFF | Stateless — nothing to forget |
| Improves over time | No | LLMs correct schema errors ~100% when shown the errors |

**Integration test coverage** — formal row added to the §7.4 matrix as **I10**: verifies a deliberately-malformed first attempt followed by an informed retry succeeds. This is the acceptance gate for H2 — the informed-retry mechanism is not optional prose, it is a required test in the atomic commit. See §7.4 row I10.

**Net change for H2**: ~15 lines across 3 function signatures + 1 block at the retry site. Zero new dependencies. Replaces the rejected `STRICT_SCHEMA` escape hatch with an active correction mechanism that makes the "must be perfect in first go" constraint structurally achievable.

**Ground-truth note (verified 2026-04-17 by sanity-check read)**: the H2 amendment applies to the FIRST retry only (lines 1912–1929 of `run_learner_for_quarter`). The existing SECOND-validation block at lines 1934–1946 (which checks the retry's output and returns None on further failure) is already correct fail-closed behavior and should NOT be modified. Informed retry is a one-shot recovery aid; persistent malformed output after one informed retry correctly stops the ticker chain per plan §2 failure policy. The first-call site at lines 1883–1894 also does NOT need `prior_validation_errors` — the default `None` is correct for the first attempt.

### 6.7 SKILL.md updates (key paragraphs)

In the "Global observations" section of `.claude/skills/earnings-learner/SKILL.md`, replace the current "0-3 entries. Each: `{scope, scope_key, lesson}`" paragraph with:

> **Global observations — 0–3 entries per attribution.**
>
> Each entry has exactly `scope`, `lesson` (1–2 sentences), and the scope-specific routing field below. **Do NOT emit `scope_key` — the field is removed; the validator rejects it.**
>
> - **`scope="sector"`** → REQUIRED `target_sector` with value from this canonical 11-value enum: `Technology`, `Healthcare`, `ConsumerCyclical`, `Industrials`, `FinancialServices`, `ConsumerDefensive`, `RealEstate`, `Energy`, `BasicMaterials`, `CommunicationServices`, `Utilities`. Do NOT include `related_tickers` or `scope_key`.
>
> - **`scope="macro"`** → include neither `target_sector`, `related_tickers`, nor `scope_key`.
>
> - **`scope="cross_ticker"`** → REQUIRED `related_tickers` as a non-empty list of uppercase ticker symbols (1–5 letters each, max 8 total, no duplicates). Do NOT include `target_sector` or `scope_key`.
>
> **Scope choice rule (mandatory):**
> - Use `cross_ticker` ONLY when the lesson is about specific named tickers. The lesson will only flow to those tickers' future predictions.
> - Use `sector` when the lesson generalizes across a whole sector (any company in `target_sector` will receive it).
> - Use `macro` for regime-wide observations (every future prediction receives it).
> - Sector-generalizable lessons written as `cross_ticker` are under-routed; prefer `sector` scope for broad lessons.

**Shape-only placeholder examples (amendment 2026-04-17)** — use abstract placeholders, NOT concrete content. LLMs exhibit strong content-anchor bias when shown specific example lessons: a concrete `"trade-tension regimes"` example primes the learner to find trade-tension framings in the current quarter even when none exist; a `["ROST", "BURL"]` pair biases peer selection; `"X dominates Y in attribution weight"` becomes a reusable phrasing template. Given we have NO escape hatch and validator semantics cannot catch template overfit, the examples must minimize content priming while preserving shape signal.

Concrete example content is explicitly rejected in Appendix C. The shape-placeholder form is:

```json
{
  "scope": "sector",
  "target_sector": "<one of the 11 canonical values listed above>",
  "lesson": "<1-2 sentences describing a causal mechanism observed in THIS quarter that plausibly generalizes to peers in target_sector; must be grounded in cited evidence, not boilerplate>"
}

{
  "scope": "cross_ticker",
  "related_tickers": ["<TICKER_A>", "<TICKER_B>"],
  "lesson": "<1-2 sentences explaining why THIS quarter's result ties these specific tickers together; the lesson should NOT apply to unrelated tickers — if it does, choose scope=sector instead>"
}

{
  "scope": "macro",
  "lesson": "<1-2 sentences; a regime-level observation that genuinely applies across sectors and is evidenced in THIS quarter's data, not a generic market truism>"
}
```

Front these with an explicit anti-anchor sentence: *"Shape examples — field layout ONLY. Do NOT copy the placeholder phrasings. Every `lesson` string must be generated from THIS quarter's specific evidence."* The placeholders are **self-describing** (they describe what content belongs in each slot rather than showing it), which preserves length/tone/specificity cues without exposing copyable content.

**Edge-case risk**: LLMs occasionally emit placeholder tokens like `<TICKER_A>` verbatim. If that happens, the validator's `_ok_ticker` check rejects them (underscore/bracket chars fail `.isalpha()`), the informed-retry (H2) fires with the exact error, and the second attempt corrects. Shape reliability thus stays high even in this failure mode.

**NOTE (consistency invariant)**: the 11-value enum in this SKILL.md MUST match `config/canonical_sectors.py::CANONICAL_SECTORS` exactly. The pre-commit test `test_canonical_sectors_consistency.py` (see §7.5) asserts both (a) the module matches the live Neo4j distinct-sector set and (b) SKILL.md's prose list mentions every value in the module. Any Neo4j sector change therefore requires updating both files in the same commit; CI catches drift on either side.

---

## 7. Test matrix

### 7.1 Validator tests — `scripts/earnings/test_validate_attribution.py` (NEW)

| # | Test | Expected |
|---|---|---|
| V1 | Full valid attribution with zero global_observations | no errors |
| V2 | `cross_ticker` with `related_tickers=["ROST"]` | no errors |
| V3 | `cross_ticker` with `related_tickers=[]` | error naming `related_tickers` |
| V4 | `cross_ticker` missing `related_tickers` field | error |
| V5 | `cross_ticker` with `related_tickers=["rost"]` (lowercase) | error |
| V6 | `cross_ticker` with `related_tickers=["TOOLONG"]` (7 chars) | error |
| V7 | `cross_ticker` with `related_tickers=["ROST","ROST"]` (duplicates) | error |
| V8 | `cross_ticker` with 9 related_tickers | error (cap=8) |
| V9 | `cross_ticker` with `target_sector="Technology"` present | error (must not have target_sector) |
| V10 | `sector` with `target_sector="Technology"` | no errors |
| V11 | `sector` with `target_sector="semiconductors"` (non-canonical) | error |
| V12 | `sector` with `target_sector` missing | error |
| V13 | `sector` with `related_tickers=["AAPL"]` present | error |
| V14 | `macro` with neither field | no errors |
| V15 | `macro` with `related_tickers=["AAPL"]` | error |
| V16 | `macro` with `target_sector="Technology"` | error |
| V17 | Required non-global fields missing (evidence_ledger etc.) | error (sanity check existing rules still fire) |
| V18 | Unknown scope value `"foo"` | error from existing `_VALID_SCOPES` check |
| V19 | Any scope with `scope_key="anything"` present | error (field removed; validator rejects across all scopes) |
| V20 | `cross_ticker` `related_tickers=["ROST","ROST"]` — duplicates | error (validator is dedupe authority; writer does NOT dedupe) |

### 7.2 Writer tests — extend `test_learning_context.py`

| # | Test | Expected |
|---|---|---|
| W1 | `append_global_lessons` for ticker with valid Neo4j sector (mocked) | entry has `source_sector` populated |
| W2 | `append_global_lessons` for ticker whose lookup returns None | `source_sector=None`, WARNING emitted |
| W3 | `related_tickers` and `target_sector` pass through untouched | stored fields equal input |
| W4 | Concurrent writes (two threads, different tickers) | both entries present, fcntl-protected, no corruption |
| W5 | Atomic write crash mid-write (force exception after temp file) | temp file cleaned up, `global.json` unchanged |
| W6 | `append_global_lessons` called twice with the same `(ticker, quarter_label)` | second call REPLACES prior entries for that key, not duplicates (upsert-by-source-key) |
| W7 | `append_ticker_lesson` called twice with the same `quarter_label` | second call REPLACES the prior entry; `lessons[]` contains exactly one entry for that quarter |
| W8 | `append_global_lessons` receives observation with `scope_key` field (learner error past validator) | writer does NOT pass it through (field dropped at enrichment time) |

### 7.3 Reader tests — rewrite `test_learning_context.py`

| # | Test | Expected |
|---|---|---|
| R1 | Empty `global.json` | both lessons arrays empty |
| R2 | File absent | both empty |
| R3 | One sector entry with matching `target_sector` | included |
| R4 | One sector entry with non-matching `target_sector` | excluded; counter `sector_mismatch=1` |
| R5 | Sector entry with current sector normalized (e.g., "technology" current, "Technology" target) | included |
| R6 | Sector entry lacking `target_sector` (legacy) | excluded; counter `legacy_schema=1` |
| R7 | Macro entry | always included |
| R8 | Cross-ticker entry with `related_tickers=["AAPL"]`, current ticker AAPL | included |
| R9 | Cross-ticker entry with `related_tickers=["MSFT"]`, current ticker AAPL | excluded; counter `cross_ticker_not_listed=1` |
| R10 | Cross-ticker entry lacking `related_tickers` (legacy) | excluded; counter `cross_ticker_missing_related=1` |
| R11 | 10 sector entries all matching | capped at 4, newest-first |
| R12 | 10 cross_ticker all matching | capped at 2 |
| R13 | Two entries identical lesson text | deduped to 1 |
| R14 | Unknown scope value entry | excluded; counter `unknown_scope=1` |
| R15 | Observability log emitted with exact field names, even when `global.json` absent | substring-asserted for each of the 6 counter keys + 3 included counts (no regex) |

### 7.4 Integration tests

| # | Test | Expected |
|---|---|---|
| I1 | Full `run_learner_for_quarter` with mocked SDK producing valid output | `global.json` has entries with all new fields populated |
| I2 | Same, but mocked output has cross_ticker without `related_tickers` | validator rejects, result.json deleted, retry triggered, re-fails → ticker chain stops per §2 failure policy |
| I3 | Predictor bundle render end-to-end with real post-fix `global.json` | Section 10 contains three correctly-labeled sub-sections |
| I4 | PreToolUse hook round-trip with malformed cross_ticker result.json content | hook blocks with reason containing `"related_tickers"` |
| I5 | `build_prediction_bundle` for a ticker with `8k_packet.sector=None` | sector populated via `_lookup_company_sector` fallback |
| I6 | Observability log at INFO level after one learner call | matches pattern with all counter names |
| I7 | Corrupted `global.json` on disk (force `json.JSONDecodeError`) during read | `log.error` emitted; predictor bundle builds with empty `global_lessons`; no crash |
| I8 | Unreadable `global.json` on disk (force `OSError`) during read | `log.error` emitted; predictor bundle builds with empty `global_lessons`; no crash |
| I9 | Derived-write recovery path re-runs an already-processed quarter | upsert fires — no duplicate entries in `global.json` or `ticker.json` after second run |
| I10 | **H2 acceptance gate** — informed retry: mocked SDK returns malformed output on attempt 1 (e.g., `cross_ticker` entry without `related_tickers`), then well-formed output on attempt 2 after receiving validation errors in the retry prompt | retry succeeds; final `attribution/result.json` validates; derived `global.json` / `ticker.json` contain the expected new-schema entry; log shows `"Retrying learner ... (1 retry, feeding N validation errors back)"` |

### 7.5 Canonical-sector consistency tests — `scripts/earnings/test_canonical_sectors_consistency.py` (NEW)

These tests enforce that the hardcoded enum, the live Neo4j set, AND the SKILL.md prose list stay aligned.

| # | Test | Expected |
|---|---|---|
| CS1 | `CANONICAL_SECTORS == {live Neo4j distinct-sector set}` | equal; test fails loudly with symmetric-difference breakdown if not |
| CS2 | SKILL.md prose mentions every value in `CANONICAL_SECTORS` | every label present; missing list reported on failure |
| CS3 | `CANONICAL_SECTORS` is frozen (no duplicates, non-empty, all str, no whitespace issues) | sanity check |

**Implementation sketch:**
```python
from config.canonical_sectors import CANONICAL_SECTORS
from scripts.earnings.utils import neo4j_session
from pathlib import Path

def test_canonical_sectors_match_neo4j():
    # Mirror the runtime coalesce logic exactly — _lookup_company_sector uses
    # coalesce(c.sector, sec.name), so the test must compute the same set or
    # drift between Industry-only-sector tickers and property-only tickers
    # could go undetected.
    with neo4j_session() as (s, err):
        assert not err, f"Neo4j unavailable: {err}"
        rows = s.run("""
            MATCH (c:Company)
            OPTIONAL MATCH (c)-[:BELONGS_TO]->(:Industry)-[:BELONGS_TO]->(sec:Sector)
            WITH coalesce(c.sector, sec.name) AS sector
            WHERE sector IS NOT NULL
            RETURN DISTINCT sector
        """).data()
        neo4j_set = {r["sector"] for r in rows}
    assert neo4j_set == CANONICAL_SECTORS, (
        f"Neo4j/enum drift detected.\n"
        f"  In Neo4j but not in CANONICAL_SECTORS: {neo4j_set - CANONICAL_SECTORS}\n"
        f"  In CANONICAL_SECTORS but not in Neo4j: {CANONICAL_SECTORS - neo4j_set}\n"
        f"Action: update config/canonical_sectors.py AND the prose enum in "
        f".claude/skills/earnings-learner/SKILL.md in the same commit."
    )

def test_skill_md_lists_all_canonical_sectors():
    skill = Path(".claude/skills/earnings-learner/SKILL.md").read_text(encoding="utf-8")
    missing = sorted(s for s in CANONICAL_SECTORS if s not in skill)
    assert not missing, (
        f"SKILL.md prose enum is missing canonical sectors: {missing}\n"
        f"Action: update the sector-enum prose paragraph in earnings-learner/SKILL.md."
    )
```

---

## 8. Rollout — single atomic commit

### 8.1 Pre-commit checklist

- [ ] Canonical sector enum in SKILL.md matches §3's 11 values exactly.
- [ ] `_lookup_company_sector` still returns expected values for AVGO, NVDA, BURL, ROST (quick manual Neo4j call).
- [ ] **All tests in §7 green** on the project venv, including the NEW consistency tests:
  ```bash
  venv/bin/python scripts/earnings/test_validate_attribution.py          && \
  venv/bin/python scripts/earnings/test_learning_context.py              && \
  venv/bin/python scripts/earnings/test_canonical_sectors_consistency.py
  ```
- [ ] `venv/bin/python -m py_compile` clean for every modified file, including `.claude/hooks/validate_attribution_output.py` and `config/canonical_sectors.py`.
- [ ] Grep confirms no remaining references to `_extract_scope_key_tickers`, `_cross_ticker_matches`, `scope_key` in code blocks of the plan, or `sector_missing_target`.
- [ ] Grep confirms no `import re` or `re\.` in the learning-context code path (validator + orchestrator) — zero regex invariant.

### 8.2 Commit contents

Single commit titled e.g. `feat(learner): structured routing for global lessons (cross_ticker + sector)`. The commit MUST contain:

- **NEW** `config/canonical_sectors.py` — hardcoded `CANONICAL_SECTORS` frozenset (§3.1).
- **MODIFIED** `scripts/earnings/validate_attribution.py` — validator additions (§6.1).
- **MODIFIED** `scripts/earnings/earnings_orchestrator.py` — writer upserts (§6.2), reader rewrite (§6.3), renderer split (§6.4), codex deletions (§6.5), informed-retry signature changes (§6.6), observability log, anti-poisoning sector cache (§3.2).
- **MODIFIED** `.claude/hooks/validate_attribution_output.py` — `sys.path.insert(0, project_dir)` added before existing insert (§5 row 3).
- **MODIFIED** `.claude/skills/earnings-learner/SKILL.md` — new schema, canonical enum, worked examples (§6.7).
- **MODIFIED** `.claude/plans/learner.md` — §8 + §9 synced with this plan.
- **NEW** `scripts/earnings/test_validate_attribution.py` — V1–V20 (§7.1).
- **REWRITTEN** `scripts/earnings/test_learning_context.py` — W1–W8, R1–R15, I1–I10 (§7.2–§7.4). I10 is the H2 acceptance gate (informed retry round-trip); commit is incomplete without it.
- **NEW** `scripts/earnings/test_canonical_sectors_consistency.py` — CS1–CS3 (§7.5).

Commit body should reference this plan file.

### 8.3 Post-commit operator steps (NOT in the commit) — SMOKE-BEFORE-WIPE order

**Rationale for ordering**: the smoke test proves the NEW pipeline (validator + informed retry + writer + reader) works against REAL data before any destructive operation. If smoke test fails, iterate SKILL.md without having destroyed anything. Only after smoke test passes do we wipe.

```bash
# ── STEP 1: Smoke test the new pipeline on 2–3 quarters BEFORE wiping ──
# These runs exercise:
#   - derived-write recovery hitting an old-schema attribution/result.json
#   - validator rejecting old schema → delete → learner re-runs with new schema
#   - informed retry (H2) if the learner's first new-schema attempt is imperfect
#   - upsert in append_global_lessons and append_ticker_lesson (idempotency)
#   - reader filtering mixed old+new schema (legacy_schema counter fires on old)
python3 scripts/earnings/earnings_orchestrator.py AVGO 0001730168-23-000053 --save --predict --learn
python3 scripts/earnings/earnings_orchestrator.py NVDA <accession> --save --predict --learn
python3 scripts/earnings/earnings_orchestrator.py BURL <accession> --save --predict --learn

# ── STEP 2: Inspect the smoke-test output ──
# For each smoke-tested quarter's attribution/result.json, confirm:
#   - Any cross_ticker observations have related_tickers populated (non-empty, UPPER, 1–5 letters)
#   - Any sector observations have target_sector from the canonical 11-value enum
#   - NO scope_key field anywhere
#   - Validator logged zero errors; if retry fired, it succeeded on attempt 2
# For global.json:
jq '.entries[] | select(.source_ticker=="AVGO" and .quarter_label=="Q1_FY2023")
    | {scope, related_tickers, target_sector, source_sector}' \
   earnings-analysis/learnings/global.json

# Smoke-test GATE: if any smoke quarter failed validation even after informed
# retry, DO NOT proceed to wipe. Iterate SKILL.md and re-run this step.

# ── STEP 3: Backup + wipe derived data (only after smoke passes) ──
# SAFETY CHECK: confirm the wipe path is not inside the Obsidian symlink tree
# managed by obsidian_thinking.md. earnings-analysis/learnings/ must be a
# real dir, NOT a symlink; otherwise the rm could nuke upstream vault content.
[ -L earnings-analysis/learnings ]                && { echo "ABORT: learnings/ is a symlink"; exit 1; }
[ -L earnings-analysis/learnings/global.json ]    && { echo "ABORT: global.json is a symlink"; exit 1; }
[ -L earnings-analysis/learnings/ticker ]         && { echo "ABORT: ticker/ is a symlink"; exit 1; }

cp -r earnings-analysis/learnings earnings-analysis/learnings.backup.$(date +%s)
rm earnings-analysis/learnings/global.json
rm earnings-analysis/learnings/ticker/*.json

# ── STEP 4: Verify empty state ──
ls earnings-analysis/learnings/ticker/      # should be empty
[ ! -f earnings-analysis/learnings/global.json ] && echo "global.json absent ✓"

# ── STEP 5: Full 15-quarter re-run chronologically per ticker ──
# (AVGO Q1→Q5, NVDA Q1→Q5, BURL Q1→Q5)
# The smoke-tested quarters re-run cleanly because their ticker.json/global.json
# entries were wiped in Step 3.

# ── STEP 6: Post-completion verification ──
jq '.entries[] | select(.scope=="cross_ticker") | {related_tickers, source_sector}' \
   earnings-analysis/learnings/global.json
jq '.entries[] | select(.scope=="sector") | {target_sector, source_sector}' \
   earnings-analysis/learnings/global.json
# Confirm scope_key has been fully purged from the rebuilt data:
! jq '.entries[] | select(has("scope_key"))' earnings-analysis/learnings/global.json | grep -q .

# ── STEP 7: Grep logs for one learning_context line per quarter re-run ──
#   (should show non-zero included counts on later-in-chronology quarters)
```

### 8.4 Operational gap caveat (user-approved)

Between STEP 3 (wipe) and completion of STEP 5 (~2–3 hours of sequential re-runs), `global.json` is progressively populated from empty. Predictor runs during this window see reduced/no global lessons **by design** per the user's "starting anew" directive. This is clean-slate behavior, NOT a regression. If zero gap is ever required, the fallback is to implement dual-read mode (reader accepts both old and new schema), but that is EXPLICITLY not in this plan.

**Gate enforcement**: STEP 3 is the destructive step. STEP 1 is the validating step. The ordering (validate → destroy → rebuild) is mandatory. Skipping STEP 1 forfeits the informed-retry safety net and violates the "must be perfect in first go" constraint that rules out an escape hatch.

---

## 9. Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Learner first-write under new SKILL.md omits `related_tickers` or `target_sector` → PreToolUse hook blocks every learner write → ticker chain stops at every quarter | Low | High if realized | **NO escape hatch** (amendment 2026-04-17 — runs unmonitored; any silent-permissive mode is ruled out). Three layers of compensating hardening: **(H1)** pre-commit smoke test is a MANDATORY GATE in §8.1 — must pass 2–3 quarters across different tickers BEFORE the wipe is performed; **(H2)** validation errors are fed back into the retry prompt so the 1-retry path is informed rather than blind (§6.6); **(H3)** validator error messages include `difflib`-based "did you mean" suggestions for `target_sector` and `related_tickers` (§6.1). Combined, these push first-attempt correctness + single-retry recovery to near-100%; any persistent failure is loud (ticker chain stops + log.error), NEVER silent. |
| R2 | Legacy `attribution/result.json` files with old-schema global_observations fail validation on re-run | Certain for 15 quarters | Low (time-bounded) | Derived-write recovery deletes invalid result.json and triggers learner re-run. Accepted cost: 15 re-runs, ~2–3h total, $0 (OAuth subscription). |
| R3 | `_lookup_company_sector` returns None for a current-run ticker (out-of-universe or bad Neo4j state) | Low (universe is 796 with zero NULLs) | Low | `source_sector=None` stamped, WARNING logged. Reader does NOT route on `source_sector` anyway, so lesson still flows correctly via `related_tickers` or `target_sector`. |
| R4 | Neo4j unreachable at append time → `source_sector=None` on every entry of the run | Low | Low | `_lookup_company_sector` returns None on any Exception. Entries still valid; `source_sector` is audit-only, not routing. Run proceeds. |
| R5 | Sector label drift in Neo4j (e.g., `Technology` renamed) | Very low | Medium | `CANONICAL_SECTORS` is hardcoded in `config/canonical_sectors.py` AND pre-commit test `test_canonical_sectors_consistency.py` queries Neo4j and fails loudly on any divergence (CS1). Mitigation is automated, not operator-dependent. Any Neo4j rename = loud pre-commit-test failure with specific remediation message → single commit updates module + SKILL.md + re-wipe if appropriate. |
| R6 | `normalize_sector` differs between write-time Neo4j value and validator enum (e.g., Unicode) | Very low | Low | Enum is ASCII-only canonical. Validator uses exact string membership. Reader uses `_normalize_sector` on both sides defensively. |
| R7 | Concurrent writer corruption of `global.json` | Low (existing fcntl.flock) | High | Unchanged from today. Atomic write + flock verified by W4. |
| R8 | Renderer token budget increase from sub-section headings | Negligible | Low | ~20 tokens extra. Predictor prompt tolerates easily. |
| R9 | Predictor SKILL.md assumes specific rendered-bundle heading strings | None (confirmed) | n/a | Verified: `/earnings-prediction/SKILL.md` reads bundle at `BUNDLE_PATH` as free text. No heading literals referenced. |
| R10 | A future regression reintroduces silent drop | Low | Medium | Observability log R15 test asserts all six counter names appear. Any filter change without corresponding test update fails CI. |
| R11 | Learner's judgment on scope=sector vs cross_ticker is wrong in a specific case | Medium | Low (soft failure) | Under-routed lesson is recoverable next quarter. Over-routed is not possible (no same-sector fallback). SKILL.md rule is explicit. |
| R12 | Backups accumulate under `.backup.*` | Certain over time | Negligible | Add `learnings.backup.*` to `.gitignore`. Operator can `rm -rf` at will. |
| R13 | Infrastructure errors (corrupt/unreadable `global.json` or `ticker.json`) silently suppressed | Low | Medium | Amendment 2026-04-17 adds `log.error` on every `except (json.JSONDecodeError, OSError)` path in the reader. Predictor still builds (defensive) but operator sees the incident in logs. |
| R14 | Derived-write recovery or accidental re-run inflates `global.json` / `ticker.json` with duplicate entries | Medium | Low (reader dedupes anyway, but file grows) | Amendment 2026-04-17 converts both append functions to upsert-by-source-key (§6.2). First write unchanged; re-runs replace in place. Tests W6, W7 verify. |

---

## 10. Out of scope / future work

This plan solves **global-lessons routing and storage correctness**. It does NOT address broader questions about whether the learner-predictor loop is net-helpful on prediction quality. Those remain open and are tracked separately:

- **§11 "labeled lesson consumption" mitigation** (from `learner.md`). Separate PR. Independent of this change. The core fix for template overfit.
- **Guidance data-freshness fix** (populate `guidance_history.series`). Independent PR, plausibly higher-EV than lesson-routing fixes — predictors on all 15 calibration quarters were inferring guide-vs-consensus from press-release prose because structured guidance was empty.
- **Fresh WITH-vs-WITHOUT A/B evaluation of learner uplift** post this fix. This plan rebuilds derived data but does NOT define a formal A/B harness. Needed before any claim that "the learner now helps prediction."
- **Fix `builder_adapters.build_8k_packet` to populate sector at source** — would eliminate `build_prediction_bundle`'s `_lookup_company_sector` fallback. Until fixed, fallback stays.
- **Industry-level routing** (finer-grained than the 11-sector enum). Requires a new `Industry` node chain. Not needed yet.
- **Dotted / hyphenated tickers** (`BRK-B`, `BF-B`, etc.). Validator's `_ok_ticker` enforces `.isalpha()` + 1–5 chars, so these shapes are rejected. Not a regression today — such tickers are not in the 796-company universe. If the universe ever expands to class-B/dotted symbols, relax `_ok_ticker` to allow `-` and `.` as intra-symbol punctuation and add corresponding validator tests. Tracked here so the limitation is not invisible.
- **CI workflow infrastructure**. This plan introduces three test files but there is currently no `.github/workflows/` CI pipeline in the repo. Enforcement is via the pre-commit checklist in §8.1, executed by the operator before merge. Treating these as "CI-enforced" would be over-claiming; the tests exist and must be run pre-commit, but nothing runs them automatically. A follow-up PR to add a minimal `pytest` workflow is the right next step if CI becomes available.
- **Dual-read migration mode** — explicitly declined. Clean-slate wipe accepted.
- **Predictor's side of labeled lesson consumption** — separate PR per `learner.md §11`.
- **Audit of actual learner adherence to the scope-choice rule** — run offline after 2+ weeks of production data (same-sector-eligible lessons written as cross_ticker would be visible via exclusion counters).
- **PIT correctness audits** — unchanged by this plan; tracked in `learner.md §3`.
- **Prediction-bundle quality defects** (missing consensus, wrong-horizon reasoning, etc.) — unchanged by this plan.

For a full concern-by-concern tracking of the open learner-utility questions, see §12.

---

## 11. Validation checklist for the user (pre-implementation sign-off)

Before greenlighting implementation, confirm:

- [ ] The single-commit atomicity is understood: schema, validator, writer, reader, renderer, SKILL.md, plan doc, tests all in one commit.
- [ ] The 2–3h operational gap during post-commit re-run is acceptable.
- [ ] Codex's revert procedure (§1.4) is understood as a safety net.
- [ ] The canonical 11-value sector enum in §3 will be frozen verbatim in the validator.
- [ ] The "no source_sector fallback for cross_ticker" design is understood — same-sector broadcasting is deliberately not a routing path.
- [ ] The "no dual-read mode" design is understood — legacy entries are transparently dropped post-wipe.
- [ ] **No escape hatch** — system is designed for unmonitored execution; compensating hardening is (H1) mandatory pre-commit smoke-test gate, (H2) informed retry with validation errors fed back into prompt, (H3) `difflib` suggestions in validator errors. Failure mode is fail-closed and loud, never silent.
- [ ] Pre-commit checklist (§8.1) and post-commit operator steps (§8.3) are actionable.

---

## Appendix A — Neo4j sector distribution (verified 2026-04-17)

```
Technology              162
Healthcare              145
ConsumerCyclical        121
Industrials             110
FinancialServices        54
ConsumerDefensive        44
RealEstate               36
Energy                   35
BasicMaterials           34
CommunicationServices    30
Utilities                25
                    ─────
TOTAL                   796 (zero NULLs within universe)
```

## Appendix B — Lessons dropped under the pre-codex bug (real evidence)

From `earnings-analysis/Companies/*/events/*/attribution/result.json`, never reached any predictor via the global channel until codex's stopgap:

- AVGO Q3_FY2023 `cross_ticker:conglomerate_earnings` — "veto-condition pattern for diversified issuers"
- AVGO Q4_FY2023 `cross_ticker:*` — VMware-AI-rerating cross-reads
- AVGO Q1_FY2024 `cross_ticker:*` — sub-segment composition-shift template
- BURL Q1_FY2025 `cross_ticker:ROST_BURL` — "quality match prerequisite for peer analog validity"
- BURL Q2_FY2025 `cross_ticker:sequential_beat_quality` — "doubt resolution premium" pattern
- BURL Q3_FY2025 `cross_ticker:margin_vs_sales_tradeoff_disclosure`
- BURL Q4_FY2025 `cross_ticker:*` — call-as-separate-catalyst pattern
- NVDA (multiple) — AI infrastructure cross-reads

Plus every sector-scope entry written with non-canonical `scope_key` (`semiconductors`, `off_price_retail`, `post_rally_earnings`, …) — silently dropped by the raw-equality filter. After this plan lands, all similar future entries route correctly.

## Appendix C — Decision log (considered and explicitly rejected)

| Alternative | Why rejected |
|---|---|
| Keep codex's regex-based cross_ticker matcher | False-positive hazard on English-word-shaped scope_keys (`LOW`, `ONE`, `AI`). Ambiguous semantics. Harder to audit. |
| Same-sector fallback for cross_ticker (route via `source_sector == current_sector`) | Reintroduces the template-overfit-at-sector-scale failure mode. If broad applicability is needed, `scope=sector` exists. ChatGPT simulation confirms ~162 Technology tickers would see every AVGO lesson under this policy. |
| Fix `builder_adapters.build_8k_packet` to populate sector, then drop `_lookup_company_sector` | Out of scope; legacy builder is brittle; unknown blast radius. Deferred to a separate PR. |
| Dual-read mode (accept old + new schema in the reader during transition) | User approved clean slate. Adds ~20 lines and a future cleanup task. Not worth the complexity for a 2–3h gap. |
| Schema version bump (`global_lessons.v1` → `v2`) | Only one reader. No external consumers. Additive fields don't require a bump. |
| Use `Industry` level instead of `Sector` for `target_sector` routing | Finer granularity is attractive but requires a larger enum and a new Neo4j query. Not required for current calibration. Future work. |
| Separate validator LLM run to label lessons ex-ante | Out of scope; belongs in `learner.md §11` mitigation. |
| Keep `scope_key` as the sector routing field but add a normalize+enum check | Still conflates display and routing. Asymmetric with cross_ticker. `target_sector` separation is strictly cleaner. |
| Keep `scope_key` as a vestigial display-only field | Added amendment 2026-04-17: it earns nothing (not routed, not deduped, not filtered, redundant with `lesson`), ~30 tokens of learner fluff per entry. Strictly better to delete. |
| Writer silently dedupes `related_tickers` | Added amendment 2026-04-17: hides authoring errors. Validator rejection + learner retry forces clean output. Writer is pure pass-through. |
| Fetch `CANONICAL_SECTORS` from Neo4j at validate-time | Breaks fail-closed design of the stdlib-only PreToolUse hook. Adds Neo4j failure mode to every learner write. pre-commit consistency test achieves same drift-protection without runtime coupling. |
| Pure-append without upsert in derived-write functions | Creates duplicate entries on any re-run; reader dedupe masks the correctness impact but files grow unbounded. Upsert-by-source-key is ~6 lines and fully eliminates the drift. |
| Concrete worked examples in SKILL.md (e.g., `"During elevated trade-tension regimes..."`) | Added amendment 2026-04-17 (post initial implementation): LLMs show strong content-anchor bias on concrete examples — they copy noun phrases, peer-ticker pairs, and phrasing templates into unrelated-quarter outputs. Compounding factor: template overfit is the specific failure mode the whole learner architecture tries to engineer out, and we have NO escape hatch. Shape-only placeholders with an explicit anti-anchor instruction (§6.7) preserve length/structure cues without exposing copyable content. Validator failure mode on routing fields (LLM emits `<TICKER_A>` verbatim) is cleanly handled by H2 informed retry. Strictly better trade-off. **Residual risk (honest caveat)**: the validator enforces `lesson` as a string but NOT semantically — an LLM that copies `"<1-2 sentences describing..."` verbatim into a `lesson` value would pass schema validation. The failure mode is rare in practice (LLMs read `<...>` as instructions, not literal text) but not zero; it is caught at the §8.3 STEP 2 smoke-inspection gate where the operator eyeballs the lesson content before the wipe. |

---

## 12. Known concerns OUTSIDE the scope of this plan

This plan is narrowly scoped to **routing/storage correctness for global lessons**. A broader earlier review raised numerous concerns about the learner's actual utility for prediction. Many of those are NOT addressed here. This section tracks them explicitly so future readers know what remains open.

**Addressed directly by this plan** (no further action needed here):

| Concern | Location |
|---|---|
| `cross_ticker` silent drop | §2.1, §4.3, §6.3 |
| `sector` scope silent drop via raw-equality | §2.2, §6.1, §6.3 |
| `8k_packet.sector = None` on all bundles | §2.3; fallback kept |
| No observability on filter behavior | §4.5, §6.3 (log line with include/exclude counters) |
| `scope_key` doing double duty | Removed entirely; §4.1, §6.1 (validator rejects), §6.2, §6.4, §6.7 |
| Misleading renderer heading | §6.4 (three sub-sections) |
| Validator duplicate-field ambiguity | §6.1 (validator authoritative; writer pass-through) |
| Silent `except: pass` on read failures | §6.3 (log.error on both paths) |
| Duplicate-append drift on re-runs | §6.2 (upsert-by-source-key) |
| Canonical-sector source-of-truth | §3.1 (module + CS1/CS2 pre-commit tests) |

**Deferred to a separate PR** (acknowledged here; not acted on):

| Concern | Rationale for deferring |
|---|---|
| Template overfit — predictor over-applies prior lesson without mechanism-check against current bundle | Requires §11 labeled-lesson-consumption mitigation in `learner.md`. Separate predictor-side change. Independent of routing. |
| `guidance_history.series = []` on all 15 calibration quarters | Higher-EV independent PR. Likely more impactful on prediction quality than any lesson-routing change. |
| `build_8k_packet.sector` not populated at source | Legacy builder; separate PR. Until then, fallback is load-bearing. |
| Industry-level routing (finer than sector) | Deferred until empirical need. |
| Predictor's side of labeled consumption | Part of the §11 mitigation; learner-edits does not touch predictor logic. |

**NOT mentioned at all in the earlier plan state** — fold in as a follow-up backlog (cross-referenced as C16–C29 from the session concern audit):

| ID | Concern | Recommended next step |
|---|---|---|
| C16 | Confidence-drift monitoring (BURL Q3_25: WITH=62 vs WITHOUT=58 on wrong call) | Offline audit script over `prediction_result.v1` files; not blocking. |
| C17 | Hindsight contamination — learner sees actual return and constructs causal narratives fitting outcome | Structural; consider separate label-only LLM (see §11 "alternative if labels dishonest"). |
| C18 | SKILL.md frontmatter vs runtime drift (frontmatter is documentation-only) | One-line note in SKILL.md; trivial follow-up. |
| C19 | A/B methodology confound (BURL on Opus 4.6/high vs 4.7/xhigh for AVGO/NVDA) | Phase 8.3 re-runs will use current prod config, which incidentally fixes this; call out in the re-run plan. |
| C20 | `data_lessons` conflates "fetch X" vs "weight X more" | Learner-output schema split; separate PR. |
| C21 | `model_version` override could mask silent model fallback | Already mitigated by `_assert_claude_code_oauth_ready` + `cli_path=` pin; low priority hardening. |
| C22 | `magnitude_error_pct` semantics for `no_call` | Minor validator tightening; separate PR. |
| C23 | Lesson refinement vs replacement — append-only ticker.json preserves old wrong lessons | Predictor SKILL.md instruction to prefer newer corrective lessons (adjacent to §11). |
| C24 | Predictor doesn't weight corrective lessons higher | Same as C23. |
| C25 | PIT tier-3 (`invocation_time`) non-stationarity on most-recent quarter | Design tradeoff in `learner.md §3`; may need revisit. |
| C26 | Lesson dominance in prompt budget (Section 10 placement, recency weight) | Indirect mitigation via caps; active control is future work. |
| C27 | Template-overfit rate monitoring | Offline metric after §11 lands. |
| C28 | Self-correction latency (always 1 quarter; no structural immunity) | Symptom of C9; mitigation is §11. |
| C29 | Thinking-token capture for audit of §11 label honesty | `include_partial_messages=True` in SDK options when §11 is being audited. |

**Honest framing**: after this plan lands, routing/storage correctness is solved and observable. Whether the learner ultimately improves prediction quality remains an open empirical question gated on §11 (template overfit mitigation), the guidance-history fix, and a fresh A/B harness. None of those are in this PR.

---

**End of plan.**

**Author**: Claude (session 2026-04-17), synthesizing verified findings from direct code/artifact inspection and incorporating ChatGPT-codex critiques on cross_ticker routing design, sector-structured routing, silent-failure paths in infrastructure reads, duplicate-dedupe authority, and vestigial-field removal. Every decision traceable to evidence in the repo at commit `aa3aaaa` or in the session transcript. Amendment set applied 2026-04-17 covers: `scope_key` removal, `config/canonical_sectors.py` + pre-commit consistency test, read-failure observability, validator-only duplicate authority, upsert-by-source-key idempotency, and §12 concern-tracking.
