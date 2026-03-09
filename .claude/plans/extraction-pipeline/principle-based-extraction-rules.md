# Principle-Based Extraction Rules — Remove Hardcoded Examples

Replace enumerated positive/negative example tables across the extraction pipeline with abstract principles that generalize to any asset or extraction type without maintenance.

**Depends on**: `total-contagion-fix.md` (already landed, commit `84fc97f`)

**Scope**: Prompt-file-only changes. Zero script changes, zero query changes, zero runtime changes.

---

## Problem Statement

The contagion fix (`total-contagion-fix.md`) solved cross-asset contamination by moving type-specific content into intersection files (slot 4). However, it pushed **shared guidance knowledge** (What-to-Extract tables, Do-Not-Extract lists) down into per-asset intersection files, creating:

1. **Duplication**: The same derivation examples (explicit range, point, floor/ceiling, qualitative → No, past results → No) appear in all 6 intersection files with only the example sentence text changed. These tables are restatements of `core-contract.md` S5 (derivation taxonomy) that already defines every derivation type.

2. **Overfitting**: Enumerated positive examples ("We expect Q2 revenue of $94-98B") anchor the model to specific phrasings. Enumerated negative examples ("buyback authorizations, investment programs, facility plans") create a closed list — the model may extract unlisted items (stock splits, shelf registrations, restructuring charges) that share the same conceptual boundary.

3. **Hardcoded exception chains**: The corporate announcement rule says "Do NOT extract X — these belong to the `announcement` type. Dividend-per-share IS extractable." This is a negative rule + an exception to the negative rule + a reference to a type that doesn't exist yet. Three layers of complexity for one boundary case.

4. **Maintenance cost**: Adding a new asset type requires creating a new What-to-Extract table — which is 70% identical to existing ones — and remembering to add any new negative rules. The 10q/10k intersection files are 91% identical (5 lines differ in 53-line files).

### Root cause

The current design was **built bottom-up from observed errors**. Each time the model extracted something wrong (a buyback, an analyst estimate), a patch was added. Over time this produced enumerated example tables that work for known patterns but don't generalize.

The alternative is **top-down from definition**: if "guidance" is precisely defined, the model reasons from the definition to handle novel cases — including boundary cases it hasn't seen before.

---

## Design Principle

The word "guidance" in financial context already has a specific domain meaning: **management's stated expectations about future financial performance**. An Opus-tier model with financial domain training understands this meaning. The goal is to rely on the definition rather than enumerating cases.

**Key insight**: The derivation taxonomy (`core-contract.md` S5) already defines HOW guidance is expressed (explicit, point, implied, floor, ceiling, comparative, calculated). The quality filters should define WHEN to extract — as abstract principles, not worked examples.

---

## Changes

### Change 1: Replace `core-contract.md` S13 Quality Filters

**Current** (7 rules with examples and hardcoded negatives):

```markdown
| Filter | Rule |
|--------|------|
| **Forward-looking only** | Target period must be after source date. Past-period results are actuals, not guidance. |
| **Specificity required** | Qualitative guidance needs a quantitative anchor: "low single digits", "double-digit", "mid-teens". Skip vague terms ("significant", "strong") without magnitude. |
| **No fabricated numbers** | If guidance is qualitative, use `derivation=implied`/`comparative`. Never invent numeric values. |
| **Quote max 500 chars** | Truncate at sentence boundary with "..." if needed. |
| **100% recall priority** | When in doubt, extract it. False positives > missed guidance. |
| **Factors are conditions, not items** | If a forward-looking statement quantifies a factor affecting another guided metric (e.g., FX headwind, week count, commodity cost tailwind), capture it in that metric's `conditions` field — not as a standalone item. A factor already captured in a metric's `conditions` field is already extracted — do not also create a standalone item for it. |
| **Corporate announcements** | Do NOT extract capital allocation announcements (buyback authorizations, investment programs, facility plans) — these belong to the `announcement` extraction type. Dividend-per-share guidance IS extractable. |
```

**New** (8 principles, no examples, no type references):

```markdown
| # | Principle | Rule |
|---|-----------|------|
| 1 | **Forward-looking** | Target period must be after source date. Statements about past periods are actuals, not guidance. |
| 2 | **From management** | Extract only guidance attributed to company management. Analyst estimates, consensus figures, and third-party projections are not company guidance. |
| 3 | **Quantitative anchor** | Every item needs a numeric value, range, or magnitude descriptor (e.g., "low single digits"). Vague sentiment without magnitude ("strong", "significant") is not extractable. |
| 4 | **Guidance, not actions** | Extract management's expectations about future performance. Management decisions already taken (authorizations, completed transactions, organizational changes) are not performance guidance unless they include a forward performance impact. |
| 5 | **Verbatim evidence** | No citation = no node. Every item MUST have `quote`, `FROM_SOURCE`, and `given_date`. Max 500 chars, truncate at sentence boundary. |
| 6 | **No fabrication** | If guidance is qualitative, use `derivation=implied`/`comparative`. Never invent numeric values. |
| 7 | **Factors are conditions** | If a statement quantifies a factor affecting a guided metric (FX headwind, week count), capture it in that metric's `conditions` field — not as a standalone item. |
| 8 | **Recall over precision** | When uncertain whether a statement qualifies as guidance under principles 1-7, extract it. False positives are recoverable at query time; missed guidance is not. |
```

**What each principle achieves:**

| # | Achieves | What it replaces |
|---|----------|------------------|
| 1 | Temporal boundary — separates actuals from guidance | Same as current "Forward-looking only" (unchanged) |
| 2 | Source attribution — prevents analyst estimate contamination | Was ONLY in `news-primary.md` as hardcoded phrase table. Now universal. Fills a gap for all assets. |
| 3 | Specificity threshold — prevents vague sentiment extraction | Same as current "Specificity required" but removes enumerated examples ("low single digits", "double-digit", "mid-teens"). Keeps one example as magnitude descriptor illustration. |
| 4 | Conceptual boundary — separates guidance from corporate actions | Replaces hardcoded "Do NOT extract buyback authorizations, investment programs, facility plans. These belong to the `announcement` extraction type. Dividend-per-share IS extractable." The principle is abstract: actions vs expectations. Dividends naturally pass (they're forward performance expectations). Buybacks naturally fail (they're decisions taken). No type coupling, no exception chain. |
| 5 | Evidence requirement — ensures every node has provenance | Consolidates current "Quote max 500 chars" (standalone) with the "No citation = no node" rule from S2. |
| 6 | Anti-hallucination — prevents invented numbers | Same as current (unchanged) |
| 7 | Prevents double-counting — factors stay as conditions | Same as current but slightly tightened wording |
| 8 | Confidence tie-breaker — when boundary case is uncertain, lean toward inclusion | Reframed from current "100% recall priority". Now explicitly scoped as a tie-breaker WITHIN principles 1-7, not an override. False positives are cheap (MERGE idempotent, query-time filtering) while false negatives are permanent. Multiple sources (transcript, 8-K, news) cover the same guidance, so a false positive from one source gets validated against others. |

**What is removed and why:**

| Removed | Why |
|---------|-----|
| Corporate announcement hardcoded negative + dividend carve-out | Replaced by principle #4 which covers all cases generically. No need to name specific announcement types or create exceptions. |
| Enumerated example phrases in "Specificity required" | "low single digits" kept as a single illustration of magnitude descriptors. Removed "double-digit", "mid-teens" — these anchor the model to specific phrases rather than the concept of magnitude. |

---

### Change 2: Simplify `primary-pass.md` Extraction Rules

**Current** (lines 60-84): Metric Decomposition + Basis Rules + Segment Rules + Quality/Acceptance Filters (7 bullets duplicating S13) + Numeric Value Rules

**New**: Remove the "Quality / Acceptance Filters" block entirely (lines 77-84). It is a verbatim duplicate of `core-contract.md` S13. The remaining sections (Metric Decomposition, Basis Rules, Segment Rules, Numeric Value Rules) stay — they are structural rules about HOW to fill fields, not WHEN to extract.

Add a single reference line:
```markdown
### Core Instruction

Extract all forward-looking guidance stated by management. Apply quality filters
from core-contract.md S13. The derivation taxonomy (core-contract.md S5) classifies
how guidance was expressed; the schema fields (S2) define what to capture.
```

**What this achieves**: Eliminates the second copy of quality filters. The agent loads both `primary-pass.md` (slot 2) and `core-contract.md` (slot 1) — it sees S13 from the contract. No information loss.

**Risk**: None. The quality filters are already in core-contract.md which is always loaded.

---

### Change 3: Remove What-to-Extract tables from intersection files (with exceptions)

**Files affected**: `8k-primary.md`, `news-primary.md`, `10q-primary.md`, `10k-primary.md`, `transcript-primary.md`, `transcript-enrichment.md`

**What is removed from each**:

| File | Section removed | Lines removed |
|------|----------------|---------------|
| 8k-primary.md | "What to Extract from 8-K" table (10 rows) + "Do NOT Extract" list (4 rules) | ~20 lines |
| news-primary.md | "What to Extract from News" table (8 rows) + "Do NOT Extract > Analyst Estimates" heading + "Do NOT Extract > Other Exclusions" (4 lines) | ~12 lines |
| 10q-primary.md | "What to Extract from MD&A" table (10 rows) + "Do NOT Extract" list (4 rules) + "Forward-Looking Strictness Rule" (2 lines) | ~20 lines |
| 10k-primary.md | Same as 10q | ~20 lines |
| transcript-primary.md | "What to Extract from Prepared Remarks" table (7 rows) | ~12 lines |
| transcript-enrichment.md | Generic rows from "What to Extract from Q&A" table (rows that duplicate S5 derivation examples) | ~5 lines |

**What is KEPT — genuinely format-specific content that S5/S13 don't cover**:

| File | Kept sections | Why it must stay |
|------|--------------|-----------------|
| 8k-primary.md | Routing, Quote Prefix, Source Fields, Dedup Rule | Query routing is unique per asset. Dedup rule (exhibit vs section) is 8-K specific. |
| news-primary.md | Routing, Attribution Rule, Reaffirmation Handling, **Prior Period Values table**, Quote Prefix, Source Fields | Attribution ambiguity is a property of the news format. Prior Period Values (`"(Prior $X)" → extract new value ONLY`) is a news-specific edge case — without it the model may extract both old and new values, polluting the graph with stale guidance labeled as current. Reaffirmation verbs are common in news headlines. |
| 10q-primary.md | Routing, Signal-to-Noise Note, Quote Prefix, Source Fields | MD&A is predominantly backward-looking — the note sets expectations for low/zero yield. |
| 10k-primary.md | Same as 10q | Same rationale. |
| transcript-primary.md | Routing, Scan Scope, MCP Workaround, Speaker Hierarchy, Quote Prefix, Source Fields | Speaker hierarchy and two-pass scope are transcript-only concepts. |
| transcript-enrichment.md | Scan Scope, **Speaker Hierarchy** (NOT a duplicate — see note), Why Q&A Matters, Q&A Extraction Steps, **Consensus comfort row** + **Conditional guidance row** (from What-to-Extract table), Section Field Format, Analysis Log Format | Q&A-specific workflow is transcript-only. |

**Speaker hierarchy in transcript-enrichment.md — NOT a duplicate**:

The enrichment agent loads `transcript-enrichment.md` at slot 4. It does NOT load `transcript-primary.md` — that's a different pass's intersection file. Removing the speaker hierarchy from enrichment would cause the enrichment agent to lose it entirely. Both copies are required because they serve different agents.

**Consensus comfort + Conditional guidance rows — kept in transcript-enrichment.md**:

Two rows from the Q&A What-to-Extract table describe patterns unique to Q&A that S5 derivation rules don't naturally cover:

1. `"We're comfortable with where the Street is" → Yes: derivation=implied` — Management implicitly endorsing analyst estimates is a Q&A-specific guidance pattern. S5's `implied` definition ("qualitative or partial info") doesn't clearly describe this consensus-endorsement signal.
2. `"Assuming no FX headwinds, we'd see 2% higher growth" → Yes: note condition in conditions field` — Conditional guidance with explicit assumption framing is common in Q&A and benefits from an in-context anchor.

The remaining generic rows (explicit range, point guidance, etc.) are removed — they just restate S5.

**What this achieves**: Intersection files shrink to only content that describes HOW to read this specific source format — routing, field mappings, format-specific edge cases. The WHAT to extract (guidance definition, derivation rules, quality filters) lives exclusively in the type-level files where it belongs. The exceptions above are genuine format-specific patterns that the abstract principles don't cover.

---

### Change 4: News attribution — principle replaces phrase table

**Current** (`news-primary.md` lines 32-43): Analyst Estimates table with 6 rows enumerating specific phrases to skip:

```markdown
| "Est $X" | "Q2 EPS Est $1.43" | SKIP — analyst estimate |
| "versus consensus" | "vs consensus of $94.5B" | SKIP — analyst comparison |
| "consensus" | "Consensus expects $3.50 EPS" | SKIP — market estimate |
| "Street expects" | "The Street expects revenue of $95B" | SKIP — analyst aggregate |
| "analysts project" | "Analysts project 15% growth" | SKIP — analyst view |
| "according to estimates" | "Revenue of $95B, according to estimates" | SKIP — sourced from estimates |
```

**New** (`news-primary.md`):

```markdown
## Attribution Rule (News-Specific)

News articles mix company guidance with analyst commentary in the same text.
Apply quality filter #2 (from management) strictly: extract only statements
where the article attributes the guidance to company management. Skip any
values attributed to analysts, consensus, or third-party sources — regardless
of phrasing.

When attribution is ambiguous (passive voice, no clear source), skip the item.
Err toward precision over recall for attribution — news duplication with other
sources (8-K, transcript) provides a safety net for missed items.
```

**What this achieves**: The model applies the attribution principle to ANY phrasing it encounters — not just the 6 listed phrases. If Benzinga changes its formatting or introduces new analyst attribution patterns, the principle still works.

**Risk**: Slightly lower recall on news extraction if the model is too conservative with ambiguous attribution. Mitigated by: (a) the same guidance usually appears in the transcript or 8-K where attribution is unambiguous, (b) the principle explicitly says "attributed to... management" which is the positive case — the model extracts when it CAN attribute, not only when it sees a specific phrase.

---

## Risk Analysis

### Risk 1: Extraction quality regression on known boundary cases

**Severity**: Medium
**Cases**: Buyback authorizations, investment programs, dividend declarations

**Assessment**: Principle #4 ("Guidance, not actions") draws the same boundary as the current hardcoded rule, but abstractly. A buyback authorization is "a management decision already taken" — it fails principle #4. A dividend declaration stating future per-share payments IS "expectations about future performance" — it passes principle #4. The outcomes are identical but the reasoning path is different: from definition rather than from enumerated list.

**Mitigation**: After deploying, run extraction on the same sources used to test the contagion fix. Diff the outputs. If buybacks reappear as extracted items, tighten principle #4 wording — do not re-add hardcoded examples.

**Downside if risk materializes**: Some non-guidance items appear in extraction output until principle wording is refined. Severity is low because MERGE-based writes are idempotent — incorrect items can be cleaned up by re-running after wording fix.

### Risk 2: Reduced recall for semi-quantitative guidance

**Severity**: Low
**Cases**: "low single digits", "double-digit growth", "mid-teens"

**Assessment**: These are covered by principle #3 ("magnitude descriptor"). The current rule enumerated 3 examples; the new rule keeps "low single digits" as illustration and adds the generic term "magnitude descriptor" which covers all cases. The derivation taxonomy S5 already defines `derivation=implied` for exactly this class of guidance. Dual coverage (principle #3 + S5 `implied` definition) makes regression unlikely.

**Mitigation**: None needed — S5 is unchanged and is the primary reference the model uses for classification.

### Risk 3: News analyst contamination without phrase table

**Severity**: Medium (news is the highest-risk asset for this)
**Cases**: "Q2 EPS Est $1.43", "consensus expects $3.50"

**Assessment**: The phrase table gave the model explicit negative anchors for 6 common patterns. Without them, the model must apply principle #2 ("from management") and the news-specific attribution rule to each sentence. In most cases this works — "Est $X" is clearly not from management. But in sentences like "Revenue of $95B, according to estimates" the attribution is subtle.

**Mitigation**: The news-specific attribution rule explicitly says "when attribution is ambiguous, skip the item" and "err toward precision over recall for attribution." Quality filter #2 is now universal (was previously only in the news intersection file), so the PRINCIPLE is stronger than before. Prior Period Values table is kept in news-primary, preventing the separate risk of extracting stale prior values as current guidance.

**Downside if risk materializes**: Some analyst estimates extracted as guidance from news articles. Lower severity than it sounds because: (a) the same guidance usually exists in transcript/8-K with clean attribution, (b) deterministic IDs mean the analyst-sourced item occupies a different slot (different `source_id`), and (c) query-time filtering can exclude `source_type="news"` items when high precision is needed.

### Risk 4: Reduced organizational design quality

**Severity**: None

**Assessment**: This change strengthens the organizational design. The contagion fix established that content should flow downward (type → intersection, common → asset-specific). The current What-to-Extract tables violate this by putting type-level knowledge (derivation rules, quality filters) in asset-level files. Removing them completes the separation: type-level files define WHAT guidance is, asset-level files define HOW to read each source format.

### Risk 5: Reduced flexibility for new extraction types

**Severity**: None (improves flexibility)

**Assessment**: A new extraction type (e.g., `announcement`, `forecast`, `actuals`) would currently need to decide whether to copy the What-to-Extract table pattern (creating more duplication) or diverge (creating inconsistency). With principle-based rules, a new type defines its own quality filters as principles in its own `core-contract.md` — no inheritance of guidance-specific examples, no need to create per-asset example tables. The intersection file for a new type × existing asset contains only routing and field mappings.

### Risk 6: Reduced flexibility for new assets

**Severity**: None (improves flexibility)

**Assessment**: Adding a new asset (e.g., `press-release`, `investor-day`) currently requires creating a ~50-line intersection file with a What-to-Extract table that's 70% copied from another asset. After this change, the intersection file is ~15-20 lines of routing + source field mappings + any genuinely unique format-specific rules. The type-level quality filters apply automatically.

---

## Implementation Order

| Phase | Files | Changes |
|-------|-------|---------|
| 1 | `core-contract.md` | Replace S13 quality filters table with 8 principles |
| 2 | `primary-pass.md` | Remove Quality/Acceptance Filters block (lines 77-84), add Core Instruction reference |
| 3 | `8k-primary.md`, `10q-primary.md`, `10k-primary.md`, `transcript-primary.md` | Remove What-to-Extract tables and Do-Not-Extract lists entirely |
| 4 | `transcript-enrichment.md` | Remove generic derivation rows from What-to-Extract table; KEEP consensus comfort + conditional guidance rows; KEEP speaker hierarchy |
| 5 | `news-primary.md` | Replace analyst phrase table with attribution principle; KEEP Prior Period Values table; remove generic What-to-Extract rows |
| 6 | Verify | Run extraction on 3+ sources, diff against baseline |

Single commit. All changes are prompt-file-only.

---

## Verification

After all changes:

```bash
# No hardcoded example tables in 8k/10q/10k/transcript-primary intersection files
grep -l "What to Extract" .claude/skills/extract/types/guidance/assets/8k-primary.md .claude/skills/extract/types/guidance/assets/10q-primary.md .claude/skills/extract/types/guidance/assets/10k-primary.md .claude/skills/extract/types/guidance/assets/transcript-primary.md
# Expected: 0 files

# transcript-enrichment still has kept rows (consensus comfort, conditional guidance)
grep -c "comfortable with\|Conditional guidance\|Assuming no" .claude/skills/extract/types/guidance/assets/transcript-enrichment.md
# Expected: >= 2 matches

# news-primary still has Prior Period Values
grep -c "Prior" .claude/skills/extract/types/guidance/assets/news-primary.md
# Expected: >= 1 match

# Speaker hierarchy present in BOTH transcript files (not deduplicated)
grep -l "Speaker Hierarchy" .claude/skills/extract/types/guidance/assets/transcript-primary.md .claude/skills/extract/types/guidance/assets/transcript-enrichment.md
# Expected: 2 files

# No corporate announcement hardcoded rule
grep -i "buyback\|announcement.*type\|capital allocation" .claude/skills/extract/types/guidance/*.md .claude/skills/extract/types/guidance/assets/*.md
# Expected: 0 matches

# No analyst phrase table
grep -i "Est \$\|consensus expects\|Street expects" .claude/skills/extract/types/guidance/assets/news-primary.md
# Expected: 0 matches

# Quality filters exist only in core-contract.md S13
grep -c "Forward-looking\|From management\|Quantitative anchor\|Guidance, not actions\|Verbatim evidence\|No fabrication\|Factors are conditions\|Recall over precision" .claude/skills/extract/types/guidance/core-contract.md
# Expected: 8 matches (one per principle)
```

---

## Estimated Reduction

| Metric | Before | After |
|--------|--------|-------|
| 8k-primary.md | 57 lines | ~20 lines |
| news-primary.md | 90 lines | ~45 lines (keeps Prior Period Values + attribution rule) |
| 10q-primary.md | 53 lines | ~15 lines |
| 10k-primary.md | 53 lines | ~15 lines |
| transcript-primary.md | 64 lines | ~30 lines |
| transcript-enrichment.md | 95 lines | ~75 lines (keeps speaker hierarchy + 2 Q&A rows) |
| primary-pass.md extraction rules | 25 lines | ~10 lines |
| Total lines removed | ~140 | |
| Total lines added | ~15 (Core Instruction + attribution principle) | |
| Net reduction | ~125 lines | |

---

*Plan created 2026-03-08, revised 2026-03-08 (regression review: kept speaker hierarchy in enrichment, kept Q&A-specific rows, kept Prior Period Values in news). Depends on: `total-contagion-fix.md` (landed). Scope: ~15 edits across 8 files, single commit.*
