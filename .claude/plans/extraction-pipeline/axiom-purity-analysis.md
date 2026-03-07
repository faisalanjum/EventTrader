# Axiom Purity Analysis: TYPE x ASSET x PASS Decomposition

**Analyst**: Axiom Purity Auditor
**Date**: 2026-03-07
**Scope**: Design principle review of the 3-axis framework for organizing extraction instructions

---

## Executive Summary

The 3-axis decomposition (TYPE x ASSET x PASS) is **correct and near-optimal** for this system. It is the minimal decomposition that achieves full isolation of concerns given the constraints of the pipeline. The intersection files at TYPE x ASSET x PASS granularity are at the **right level** -- TYPE x ASSET (without PASS) would be insufficient because the two passes have genuinely different extraction rules for the same TYPE x ASSET combination. However, the framework has **two structural tensions** that deserve attention: (1) the PASS axis is not truly independent -- it is subordinate to TYPE, and (2) the boundary rules are airtight for the 4 current assets but would need extension for assets with >2 sections.

---

## Question 1: Is 3 the right number of axes?

### Analysis

The three axes represent three genuinely independent concerns:

| Axis | Question it answers | Example values |
|------|---------------------|----------------|
| **TYPE** | What are we extracting? | guidance, (future: analyst estimates, risk factors, ...) |
| **ASSET** | Where are we reading from? | transcript, 8k, 10q, news |
| **PASS** | Which phase of extraction? | primary, enrichment |

**Could 2 axes suffice?** No. Consider the alternatives:

- **TYPE x ASSET only (no PASS)**: The transcript has two structurally different content sections (prepared remarks and Q&A) that require different extraction strategies. The primary pass extracts from PR with speaker hierarchy priorities; the enrichment pass cross-references Q&A against existing items with a verdict taxonomy. These are not "the same rules applied twice" -- they are fundamentally different algorithms. Collapsing PASS into TYPE or ASSET would force a single file to contain both algorithms, recreating the very pollution the framework eliminates.

- **TYPE x PASS only (no ASSET)**: Each asset has genuinely different data structures (Transcript nodes with PreparedRemark/QAExchange children vs. Report nodes with ExhibitContent/Section children vs. single News nodes). The fetch order, fallback chains, field names, period derivation, and given_date sources differ per asset. These cannot be collapsed into TYPE.

- **ASSET x PASS only (no TYPE)**: The "what to extract" rules (accept/reject tables, speaker priorities, derivation logic) are completely type-specific. A future "analyst estimates" type would scan the same transcript but look for different signals. Without TYPE, the asset file must contain extraction rules for every type.

**Are there hidden 4th axes?**

- **Company-specific overrides**: Not currently present and correctly omitted. The system handles company variation through runtime data (FYE month, concept cache, member cache) rather than static instruction files. If a company required custom extraction rules, it would be better modeled as a TYPE variant or a runtime parameter than a 4th axis.

- **Temporal versions**: The plan uses version footers in files but does not formalize version as an axis. This is correct -- versioning is an operational concern (git commits), not a structural axis. If the extraction rules for guidance change over time, you change the files and the git history provides versioning. A formal version axis would add complexity without benefit.

- **Schema version**: core-contract.md defines the output schema. This is correctly modeled as a TYPE-level file (one schema per type), not as a separate axis. If a type's schema evolved, the core-contract would be updated alongside the pass files.

**Verdict**: 3 is the correct number. 2 is insufficient. 4 would introduce unnecessary complexity for concerns better handled by runtime data or git versioning.

---

## Question 2: Is the intersection at the right level?

### Analysis

The plan creates intersection files at TYPE x ASSET x PASS granularity: `types/{TYPE}/assets/{ASSET}-{pass}.md`. The question is whether TYPE x ASSET (one file for both passes) would be simpler without losing isolation.

**Why TYPE x ASSET x PASS is needed (not just TYPE x ASSET)**:

Consider the transcript guidance case. The two intersection files contain:

| `transcript-primary.md` (~38 lines) | `transcript-enrichment.md` (~54 lines) |
|--------------------------------------|----------------------------------------|
| Scan scope: "Process all prepared remarks" | Scan scope: "Process all Q&A" |
| Extraction Steps 1-5 for PR | Q&A Extraction Steps 1-4 |
| "What to Extract from PR" table | "Why Q&A Matters" rationale |
| [PR] quote prefix rule | "What to Extract from Q&A" table |
| | [Q&A] quote prefix rule |
| | Section Field Format |

These files have **zero content overlap** except for the speaker hierarchy table (which is deliberately duplicated because each agent runs in isolation). A single TYPE x ASSET file would force both agents to read both sets of rules -- reintroducing the exact pollution problem the framework solves.

The plan correctly identifies the concrete harm: the primary agent currently reads Q&A extraction rules it ignores (transcript.md lines 106-148), and the enrichment agent reads PR extraction steps it ignores. The per-pass intersection eliminates this noise.

**Would TYPE x PASS be sufficient?**

No. The intersection content is genuinely asset-specific within a type-pass. Consider what `transcript-primary.md` contains:

- "Locate CFO section -- this is the primary guidance source" -- transcript-specific (8-K has no CFO section)
- Speaker hierarchy table -- transcript-specific (news has no speakers)
- "What to Extract from Prepared Remarks" with derivation examples -- the examples reference transcript content patterns

A hypothetical `8k-primary.md` would have entirely different content (exhibit scan order, section priorities, table projection rules). These cannot be collapsed into a single primary-pass file per type.

**Is TYPE x ASSET (one file, both passes read it) a viable simplification?**

For 3 of 4 current assets (8k, 10q, news), only the primary pass runs (sections=full, no enrichment). These assets would have a single intersection file regardless. The per-pass distinction only matters for transcript (sections: prepared_remarks, qa). Having one `transcript.md` intersection file read by both agents would be simpler (1 file instead of 2), but:

1. It would force the primary agent to see Q&A extraction rules it ignores
2. It would force the enrichment agent to see PR extraction rules it ignores
3. It would make the scan scope instruction ambiguous (can't say both "Process all PR" and "Process all Q&A" in one file)

These are exactly the problems being fixed. The per-pass granularity is justified.

**Verdict**: TYPE x ASSET x PASS is the right intersection level. TYPE x ASSET alone loses pass-specific isolation for multi-section assets. TYPE x PASS alone loses asset-specific content targeting. The current level is minimal and necessary.

---

## Question 3: Does the framework hold universally?

### Assets with no enrichment pass (8k, 10q, news)

For these assets, `sections: full` means the enrichment gate fails at condition 1 (SKILL.md Step 3). No enrichment agent is spawned. Therefore:

- Only `types/guidance/assets/{ASSET}-primary.md` intersection files are needed
- No `-enrichment.md` files exist for these assets
- The framework handles this correctly through the "optional slot 4" pattern -- the file simply doesn't exist, and the agent skips it

The framework holds. The PASS axis doesn't create useless files for single-pass assets because intersection files are optional.

### Hypothetical asset with >2 sections

If a future asset had 3 content sections (e.g., a transcript with prepared_remarks, qa, and supplementary_materials), the current framework would need extension. The enrichment pass is defined as "secondary content" -- there's no concept of a tertiary pass. Two options:

1. **Extend enrichment to cover multiple secondary sections** -- the enrichment pass processes all non-primary sections. This is the simpler path and preserves the 2-pass model.
2. **Add a third pass** -- this would require a third agent shell, a third intersection file, and a third orchestrator step. The framework accommodates this (SKILL.md would spawn a third agent, the naming convention `{ASSET}-{pass}.md` extends naturally), but it's unnecessary complexity unless the sections require fundamentally different algorithms.

Option 1 is sufficient for any foreseeable case. The enrichment pass already handles "secondary content" generically.

### Hypothetical type that needs 3 passes

If a type required 3 passes (e.g., extract -> validate -> reconcile), the framework extends naturally:

- Add a third pass file: `types/{TYPE}/reconcile-pass.md`
- Add a third agent shell: `extraction-reconcile-agent.md`
- Add intersection files: `types/{TYPE}/assets/{ASSET}-reconcile.md`
- SKILL.md adds a Step 5 to spawn the third agent

The naming convention and file structure support this without ambiguity. The PASS axis is not hard-coded to {primary, enrichment} -- it's a convention. The only hard constraint is the SKILL.md orchestrator, which would need a new step.

### Cross-type interactions

If two types needed to share information (e.g., guidance extraction informing analyst-estimate extraction), the current framework has no mechanism for this. Each TYPE is a fully independent pipeline. This is correct -- cross-type dependencies would introduce coupling that violates the isolation principle. If needed, they should be handled at the orchestrator level (run type A, then pass results to type B), not within the instruction files.

**Verdict**: The framework holds for all current assets and extends naturally to foreseeable future cases. The >2 sections case is a known limitation but is addressable within the 2-pass model.

---

## Question 4: Are the boundary rules airtight?

### The 3 Boundary Rules

1. **Asset files never say what to extract** -- describe HOW to read data (shape, fields, fallbacks). Never what to extract.
2. **Pass files never have asset-specific rules** -- describe HOW a pass works (pipeline steps, quality filters, write rules). Never asset-specific rules.
3. **Intersection files bridge TYPE+ASSET** -- contain rules that depend on BOTH type AND asset knowledge.

### Stress-testing with adversarial scenarios

**Scenario A: Period identification**

Transcript period identification (calendar-to-fiscal mapping) is currently in `transcript.md`. Is this an asset rule or a type rule?

Analysis: Period mapping depends on the data format (transcripts use conference_datetime and fiscal year language), not on what's being extracted. A future "analyst estimates" type would need the same calendar-to-fiscal mapping when reading transcripts. This correctly stays in the asset file.

BUT: The `period_type` and `period_scope` fields are defined in the guidance core-contract. If a second type used different period semantics, the period identification table in the asset file would be misleading. The current table maps transcript language to `period_type` values (quarter, annual, half, long-range) -- and those values are defined by the guidance schema.

**This is a genuine boundary ambiguity.** The period identification table uses type-defined vocabulary (`period_type`) in an asset-level file. Currently harmless (only one type), but when type #2 arrives, this needs resolution. The fix would be to generalize the period patterns to asset-level (what the transcript says) and map to type-specific field names in the intersection file.

**Scenario B: Given_date and source_key**

These are currently in `transcript.md`: "given_date = t.conference_datetime", "source_key = 'full'". These are field-mapping rules -- the asset file tells the agent which data field provides which extraction field. The field names (given_date, source_key) are defined in the guidance schema, but the mapping is asset-specific.

This is correctly placed. Any type that extracts from transcripts would use the same datetime source. The field names might differ per type, but the mapping pattern (conference_datetime -> timestamp field) is genuinely asset-level knowledge.

**Scenario C: Basis switch trap**

"CFO may switch between GAAP and non-GAAP within the same paragraph" is in `transcript.md`. Is this asset knowledge or type knowledge? It's about how speakers structure their remarks in transcripts (asset behavior) and affects any extraction that cares about basis (type concern). This is a genuine intersection concern -- it's about HOW transcript data presents basis information, which matters to any type that has a basis field. It's correctly placed as an asset-level trap because it describes data behavior, not extraction logic.

**Scenario D: Empty-content handling**

"If prepared_remarks is null AND qa_exchanges is empty, try Q&A Section fallback (3C)" is in `transcript.md`. This is pure asset-level logic -- it describes data availability patterns and fallback strategies for reading transcript data. Any extraction type would follow the same fallback chain. Correctly placed.

**Scenario E: Content that is ambiguously both**

Consider a hypothetical rule: "When transcript prepared remarks are truncated, extract from Q&A but reduce confidence." This rule depends on:
- Asset knowledge: PR truncation is a transcript-specific data quality issue
- Type knowledge: "reduce confidence" implies type-specific quality modifiers
- Pass knowledge: This only applies to the primary pass's fallback behavior

Where does this go? Under the current rules, it belongs in the intersection file (`transcript-primary.md`) because it requires BOTH asset AND type knowledge. This is the correct placement -- the intersection files exist precisely for this case.

### Assessment

The boundary rules are **nearly airtight** but have one known weak point: the use of type-defined vocabulary (period_type values, field names like given_date/source_key) in asset files. This is a vocabulary coupling, not a logic coupling -- the asset file maps data to field names, and the field names happen to be defined by the current (only) type. When type #2 arrives with different field names, this vocabulary needs generalization.

**Verdict**: Boundary rules are airtight for logic separation. There is minor vocabulary coupling through type-defined field names in asset files. This is acceptable at the current scale (1 type) and has a clear fix path (generalize field names when type #2 is added).

---

## Question 5: Is the file-path convention minimal?

### Current convention

```
types/{TYPE}/assets/{ASSET}-{pass}.md
```

### Analysis

The convention needs to encode three pieces of information:
1. Which TYPE it belongs to
2. Which ASSET it specializes
3. Which PASS it targets

The current encoding:
- TYPE via directory path: `types/{TYPE}/`
- ASSET via filename prefix: `{ASSET}-`
- PASS via filename suffix: `{pass}.md`

**Could a simpler convention work?**

- **Flat file**: `{TYPE}-{ASSET}-{pass}.md` in a single directory. Simpler directory structure, but loses the organizational grouping of type-related files. When listing `types/guidance/`, you see all guidance files together. A flat directory with 4 types x 4 assets x 2 passes = 32 files would be harder to navigate.

- **Nesting ASSET as directory**: `types/{TYPE}/assets/{ASSET}/{pass}.md`. This adds an extra directory level for minimal benefit. The current convention is already unambiguous.

- **Dropping PASS from filename**: `types/{TYPE}/assets/{ASSET}.md` (one file per TYPE x ASSET, consulted by both passes). As analyzed in Question 2, this loses per-pass isolation. Not viable.

**Could it be shorter?**

The `assets/` subdirectory within `types/{TYPE}/` is the one element that could theoretically be dropped: `types/{TYPE}/{ASSET}-{pass}.md`. But this would mix intersection files with pass files in the same directory, creating ambiguity: is `primary-pass.md` a pass file or an intersection file for an asset called "primary"? The `assets/` subdirectory clearly signals "these are intersection files, not pass files."

**Collision analysis**: The current convention prevents collisions because:
- `{TYPE}` is unique across types
- `{ASSET}` is unique across assets
- `{pass}` is unique within a type's pass set
- The combination `{ASSET}-{pass}` is unique within a type

No collisions are possible with the current naming. The only potential issue is if an asset name contained a hyphen that could be confused with the pass delimiter (e.g., asset "8k-annual" with pass "primary" = "8k-annual-primary.md"). Current asset names (transcript, 8k, 10q, news) don't have this issue, but a naming convention doc should note that asset names should not contain hyphens, or use a different delimiter (underscore: `{ASSET}_{pass}.md`).

**Verdict**: The convention is minimal and collision-free for current and foreseeable asset names. The `assets/` subdirectory serves a valuable disambiguation purpose. One minor recommendation: document that asset names should not contain hyphens to prevent future parsing ambiguity.

---

## Question 6: Does the "optional slot 4" pattern create risks?

### The pattern

The agent shell instructs: "Read file X if it exists, skip if not." The agent uses the Read tool, which returns an error if the file doesn't exist, and the agent continues.

### Risk: Malformed intersection file

If someone creates a syntactically valid but semantically wrong intersection file (e.g., `types/guidance/assets/transcript-primary.md` with 8-K rules), the agent would follow wrong instructions. This is no different from any other instruction file being wrong -- there's no special risk from intersection files. The file path convention (`transcript-primary`) makes it clear what content belongs there.

### Risk: Missing file when expected

For the current 4 assets:
- transcript: intersection files ARE expected (guidance-specific content exists)
- 8k, 10q, news: intersection files MAY be expected if guidance-specific content is moved from asset files

If the pollution audit (asset-guidancePollutionAudit.md) identifies content that should move to intersection files for 8k/10q/news, those files must be created. If they're omitted, the agent loses guidance-specific instructions. The plan handles this risk through the verification checklist (per-agent content visibility checks).

The "optional" nature of slot 4 means an agent won't crash if the file is missing -- it will simply extract using only its pass brief's generic quality filters. For some TYPE x ASSET combinations, this may be sufficient (e.g., news guidance extraction might not need asset-specific guidance rules beyond what the primary-pass brief already says). For others (transcript), the intersection file is effectively required.

**Should slot 4 be "required" instead of "optional"?**

No. Making it required would force creation of empty intersection files for TYPE x ASSET combinations that don't need them (e.g., a future type that has identical rules across all assets). The optional pattern is more flexible. The risk of a missing-but-needed file is caught by the dry-run regression gate (Gate 2), not by the file-loading mechanism.

### Risk: Agent not reading slot 4

The agent's Step 0 is a numbered list of files to read. Adding a slot 4 with "optional -- skip if file does not exist" depends on the LLM correctly interpreting this conditional. Testing confirms the agent reads the file when it exists. But if the agent skips a file that exists (perhaps due to context pressure or instruction following issues), the extraction quality degrades silently.

Mitigation: The file count is logged. If the primary agent reads 7 files instead of 8 for a transcript job, the count mismatch is detectable.

### Risk: Proliferation

With 4 assets, 1 type, and 2 passes, the maximum intersection files needed is 5 (transcript x 2 passes + 8k + 10q + news, each x 1 primary pass). With N types and M assets, it's at most N x M x P files (where P is typically 1-2). This grows linearly with each axis, not exponentially, because most combinations need only a primary-pass intersection.

For 3 types and 4 assets: worst case ~20 intersection files. This is manageable. The key insight is that intersection files are optional -- many TYPE x ASSET combinations may not need one.

**Verdict**: The optional slot 4 pattern introduces acceptable risks that are mitigated by existing gates (dry-run regression, file count logging). Making it required would create unnecessary file bloat. The only actionable recommendation is to ensure the dry-run regression gate (Gate 2) is run for every new TYPE x ASSET combination, not just transcript.

---

## Overall Assessment

### What is optimal about this decomposition

1. **Minimal axes**: 3 axes is the minimum needed to isolate the three independent concerns (what, where, which phase). No axis can be removed without re-introducing pollution.

2. **Intersection at the right granularity**: TYPE x ASSET x PASS gives each agent exactly the rules it needs, no more. The per-pass level prevents agents from seeing irrelevant pass instructions.

3. **Scales linearly**: Adding a new type requires O(M) intersection files (one per asset that needs specialization), not O(M x P). Adding a new asset requires O(N) intersection files (one per type).

4. **Backward compatible**: The optional slot 4 means existing TYPE x ASSET combinations without intersection files continue working unchanged.

5. **Single-commit rollback**: The architecture change is contained in new files (intersection) plus minor edits (agent shells, asset file cleanups), rollable back with one git revert.

### What could be more elegant

1. **The PASS axis is not truly independent** -- it is subordinate to TYPE. A type defines which passes exist (guidance has primary + enrichment; a simpler type might have only primary). The PASS axis is better understood as a property of TYPE, not an independent dimension. The file tree reflects this correctly (pass files live under `types/{TYPE}/`), but the conceptual framing as "3 independent axes" slightly overstates the independence. More precisely, the decomposition is **TYPE x ASSET, where TYPE defines an ordered set of PASSES, and intersection files specialize per-pass**.

2. **Speaker hierarchy duplication**: The 15-line speaker hierarchy table is duplicated in both transcript intersection files. An alternative would be a shared `types/guidance/assets/transcript-common.md` loaded by both agents, with pass-specific files for the divergent content. This adds a 4th slot but eliminates duplication. The plan correctly rejects this as over-engineering for 15 lines, but the pattern should be noted for future reference if intersection files grow larger.

3. **Vocabulary coupling in asset files**: As noted in Question 4, asset files use type-defined field names (given_date, source_key, period_type values). This is a minor design debt that should be tracked for resolution when type #2 is added.

### Final verdict

**The 3-axis framework is the correct, minimal, and near-optimal decomposition.** No simpler alternative achieves the same isolation guarantees. The intersection at TYPE x ASSET x PASS is at the right level -- not too coarse (TYPE x ASSET would lose pass isolation) and not too fine (no hidden sub-axes needed). The boundary rules are airtight for logic, with minor vocabulary coupling that is acceptable at current scale. The optional slot 4 pattern handles sparse intersections elegantly.

The one structural nuance worth documenting: PASS is not an independent axis in the same sense as TYPE and ASSET. It is subordinate to TYPE (each type defines its own pass set). This doesn't change the implementation but refines the conceptual model from "3 equal axes" to "2 independent axes (TYPE x ASSET) with TYPE-defined phases (PASS) creating a third dimension for intersection specialization."

---

## Recommendations

1. **Document the PASS subordination**: Note in the architecture docs that PASS is defined by TYPE, not independently. This prevents confusion when adding a type that has different passes than guidance.

2. **Add asset naming constraint**: Document that asset names must not contain hyphens to prevent parsing ambiguity in intersection file names.

3. **Track vocabulary coupling**: Create a tech-debt note for generalizing type-specific field names (given_date, source_key, period_type values) in asset files when type #2 is added.

4. **Require Gate 2 for all new intersections**: Extend the dry-run regression gate to cover every new TYPE x ASSET combination, not just the transcript case documented in the plan.

5. **No structural changes needed**: The framework is sound. Proceed with implementation as designed.
