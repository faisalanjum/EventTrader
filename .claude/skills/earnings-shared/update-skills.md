# Skill Self-Improvement Protocol

> **Purpose**: After every attribution analysis, update this skill to capture learnings.
> **Goal**: The skill must be comprehensive enough to regenerate any output and reach the **same conclusion** (Primary Driver + Contributing Factors with ranked confidence) for any given accession number.

---

## Table of Contents
- [META: How to Write Good Rules](#meta-how-to-write-good-rules)
  - [Skill Philosophy](#skill-philosophy-from-boring-marketers-10-step-process)
  - [The 10-Step Process](#the-10-step-process)
  - [Specs Clarification](#specs-clarification-before-major-updates)
  - [Core Principles](#core-principles-always-follow)
- [When to Update](#when-to-update)
- [What to Capture](#what-to-capture)
- [Generic vs Specific](#generic-vs-specific)
- [Update Process (Propose → Confirm)](#update-process-propose--confirm)
- [SKILL.md Sections to Update](#skillmd-sections-to-update)
- [Updating neo4j_schema.md](#updating-neo4j_schemamd)
- [Validation: Can We Regenerate?](#validation-can-we-regenerate)
- [Anti-Bloat Rules](#anti-bloat-rules)
- [Advanced Patterns: Hooks and Sub-Agents](#advanced-patterns-hooks-and-sub-agents)
- [Examples of Good vs Bad Updates](#examples-of-good-vs-bad-updates)
- [Sources](#sources)

---

## META: How to Write Good Rules

> **This section teaches Claude HOW to write quality updates. Read this before proposing any changes.**

### Skill Philosophy (from Boring Marketer's 10-Step Process)

> "The trick to creating effective skills is to make your AI **think like an expert**, not just follow steps."

| Principle | What It Means |
|-----------|---------------|
| **Expert, not follower** | Embed decision-making logic, not just checklists |
| **Output, not docs** | Produce actual work product, not intermediate documents |
| **Practitioner, not documentation** | Sound like someone doing the work, not describing it |
| **Constrain ruthlessly** | Every section must earn its place |
| **Employee that knows you** | Skills should anticipate needs, not require constant direction |

### The 10-Step Process

> When updating a skill, follow this expert workflow—not just a checklist.

```
1. UNDERSTAND   → What problem does this skill solve? What's the desired output?
2. EXPLORE      → Read the current skill files. What's already there?
3. RESEARCH     → Query sources (Neo4j primary, Perplexity fallback). What patterns emerge?
4. SYNTHESIZE   → Combine findings into a coherent learning
5. DRAFT        → Write the proposed update (follow META principles)
6. SELF-CRITIQUE→ "Is this generic? Does it add value? Is it scannable?"
7. ITERATE      → Revise based on self-critique
8. TEST         → Can another instance regenerate the same conclusion?
9. FINALIZE     → Present proposal to user for approval
10. APPLY       → After approval, edit files and verify
```

**Key Insight**: Steps 5-8 form a loop. Draft → Critique → Iterate until quality threshold met.

### Specs Clarification (Before Major Updates)

> "Before writing, nail down the specs. Ambiguity is the enemy of good skills."

When proposing **significant** skill changes (new sections, restructuring, new patterns), consider asking clarifying questions:

| Question Type | Example |
|---------------|---------|
| **Scope** | "Should this pattern apply to all sectors or just retail?" |
| **Format** | "Table or bullet list for this pattern?" |
| **Depth** | "Include detailed Cypher examples or just descriptions?" |
| **Location** | "Add to SKILL.md or create separate reference file?" |
| **Priority** | "Is this higher priority than existing patterns?" |

**Note**: For routine post-analysis updates, skip extensive questioning—use the standard proposal format. Reserve clarification for architectural changes.

### Core Principles (ALWAYS follow)

| Principle | Description | Example |
|-----------|-------------|---------|
| **Use absolute directives** | "NEVER" or "ALWAYS" - no ambiguity | "ALWAYS use Perplexity when Neo4j lacks consensus estimates" |
| **Lead with WHY** | 1-3 bullets explaining the problem before the rule | "News gaps exist → Perplexity validates" |
| **One point per code block** | Don't pack multiple concepts into one example | Separate Cypher examples |
| **Prefer bullets over paragraphs** | Scannable > readable | Use `- ` not prose |
| **Include typical ranges** | Quantify when possible | "-3% to -6%" not "negative" |
| **Be concrete** | Specific numbers, not vague advice | "Book-to-bill < 1.0" not "low orders" |

### Rule Format Template

```markdown
### {Rule Name}

**Why**: {1-3 bullet points explaining the problem this solves}

**Rule**: {ALWAYS/NEVER + specific action}

**Example**:
```cypher
-- Correct pattern
{code}
```

**Typical Impact**: {quantified effect, e.g., "-3% to -6%"}
```

### Optional Enhancements (use strategically)

| Enhancement | When to Use |
|-------------|-------------|
| ❌/✅ examples | For subtle antipatterns that look correct but fail |
| "Warning Signs" | For gradual mistakes that compound |
| "General Principle" | For non-obvious abstractions |
| "Sector-Specific" tag | When rule only applies to certain industries |

### Quality Checklist for Each Rule

Before proposing a rule, verify:
```
- [ ] Could this be misunderstood? → Make it more specific
- [ ] Is this already covered? → Check existing rules first
- [ ] Will this bloat the file? → Consider merging with existing rule
- [ ] Is this truly generic? → Remove ticker/date references
- [ ] Does it include WHY? → Add context bullets
```

---

## When to Update

**After EVERY attribution analysis**, before marking the report as complete:

```
Analysis Progress:
- [ ] Steps 1-5: Complete attribution analysis
- [ ] Step 6: Output report to earnings-analysis/Companies/{TICKER}/{accession}.md
- [ ] Step 7: **PROPOSE SKILL UPDATES** ← You are here
- [ ] Step 8: Mark CSV as completed
```

**Step 7 is mandatory** - but only the PROPOSAL. Applying changes requires user approval and does not block analysis completion.

---

## What to Capture

Capture **full methodology evolution** across these categories:

| Category | What to Add | Where to Add |
|----------|-------------|--------------|
| **Surprise Calculation Edge Cases** | Unusual consensus formats, guidance range interpretations | SKILL.md → `## Step 6: Synthesize` |
| **Query Templates** | Cypher patterns that worked, edge cases handled | SKILL.md → `## Step N` sections |
| **Data Gaps** | Systematic gaps discovered (dates, tickers, data types) | data_gaps.md |
| **Analyst Themes** | Recurring Q&A topics that drive attribution | SKILL.md → `## Step 4: Query Neo4j` |
| **Conflict Resolution** | New source conflict scenarios and resolutions | SKILL.md → `## Conflict Resolution Guidelines` |
| **Driver Priority Learnings** | When EPS > Guidance, sector-specific drivers | SKILL.md → `## Conflict Resolution Guidelines` |
| **Data Quality Issues** | New guardrails needed, anomalies discovered | SKILL.md → `## Data Quality Guardrails` |
| **Evidence Extraction** | Edge cases in strict numeric evidence | SKILL.md → `## Evidence Extraction` |
| **Cypher Discoveries** | New query patterns, schema quirks, performance tips | **neo4j_schema.md** |
| **Cypher Issues** | Bugs, incorrect assumptions, failed queries | **neo4j_schema.md** → `## Data Type Alerts and Anomalies (Validated)` |

---

## Generic vs Specific

### The Golden Rule

> **If you remove the ticker and accession number, can this learning apply to other reports?**

### Examples

| Specific (DON'T add) | Generic (DO add) |
|----------------------|------------------|
| "ROK missed guidance by 3.56%" | "When guidance surprise is larger than EPS surprise, guidance typically dominates as primary driver" |
| "ROK's book-to-bill was 0.9x" | "Book-to-bill < 1.0 signals order weakness; analysts probe this aggressively" |
| "News missing for BJ Nov 2023" | "News coverage gaps common for mid-cap retail; always query Perplexity for consensus" |
| "CFO Laura Felice discussed..." | "CFO deflection on forward metrics = potential bearish signal; note management tone" |

### Generalization Formula

```
SPECIFIC: {TICKER} had {specific_value} in {specific_date}
    ↓
GENERIC: When {surprise_condition}, expect {driver_type} to dominate
         Key signals: {what_to_look_for}
         Typical magnitude: {return_range}
```

---

## Update Process (Propose → Confirm)

> **IMPORTANT**: Proposing updates is MANDATORY after every analysis. Applying changes requires user approval but does NOT block analysis completion. You can finish the analysis and propose updates without waiting.

### Step-by-Step Workflow

```
After completing analysis for {TICKER} / {accession_no}:

1. IDENTIFY new learnings:
   - Did I discover a new pattern? (e.g., "Beat-but-Deflation-Concerns")
   - Did I use a query that should be templated?
   - Did I hit a data gap that's likely systematic?
   - Did analysts focus on themes not in the skill?
   - Does this sector have unique attribution logic?
   - Did any Cypher query fail or need correction?

2. GENERALIZE each learning:
   - Remove ticker, dates, specific values
   - Extract the rule/formula/pattern
   - Add typical ranges (e.g., "-3% to -6%")
   - Follow META principles (absolute directives, lead with WHY)

3. PROPOSE changes:
   - Present each proposed update in a clear format
   - Show WHICH FILE and WHICH SECTION
   - Show the EXACT text to add
   - Explain WHY this learning matters

4. MARK ANALYSIS COMPLETE:
   - Analysis can proceed to Step 8 (mark CSV complete)
   - Proposed updates remain pending for user review
   - No blocking required

5. (LATER) APPLY if approved:
   - When user approves, apply the changes
   - Verify line count stays under limits
   - Log the update in Accumulated Learnings section
```

### Proposal Format

When proposing updates, use this exact format:

```markdown
## Proposed Skill Updates for {TICKER} | {ACCESSION}

### Update 1: {Category}
**File**: SKILL.md (or neo4j_schema.md)
**Section**: ## {Section Name}
**Action**: ADD (or MODIFY)

**Proposed Text**:
```
{exact text to add, following META principles}
```

**Rationale**: {1-2 sentences on why this matters}

---

### Update 2: {Category}
...

---

## Summary
- {N} updates proposed
- Files affected: {list}
- Estimated line additions: {number}

**Awaiting your approval to apply these changes.**
```

### User Response Options

After seeing the proposal, user can respond:
- **"Approved"** or **"Apply all"** → Apply all proposed changes
- **"Apply 1 and 3"** → Apply only specific updates
- **"Skip"** or **"No updates"** → Don't apply any changes
- **"Modify X to..."** → Revise a specific proposal before applying

---

## SKILL.md Sections to Update

### Existing Sections (append to these)

| Section | Add When... |
|---------|-------------|
| `## Step 4: Query Neo4j Sources` | New query pattern, analyst theme |
| `## Step 5: Query Perplexity` | New query principle that worked |
| `## Step 6: Synthesize` | Surprise calculation edge case |
| `## Evidence Extraction` | Strict numeric evidence edge case |
| `## Conflict Resolution Guidelines` | New conflict scenario or driver priority learning |
| `## Data Quality Guardrails` | New data quality issue discovered |
| `## Core Rules` | New validation rule |

### Reference Files to Update

| File | Add When... |
|------|-------------|
| `data_gaps.md` | Systematic data gap discovered |
| `neo4j_schema.md` | Cypher pattern or schema quirk |
| `output_template.md` | Report format refinement |
| `CHANGELOG.md` | Any SKILL.md update (with reasoning) |

---

## Updating neo4j_schema.md

**neo4j_schema.md must also evolve.** Update it when you discover:

### When to Update neo4j_schema.md

| Discovery Type | Action | Section to Update |
|----------------|--------|-------------------|
| **Query that worked** | Add as template with explanation | `## Query Cookbook (Copy/Paste)` |
| **Query that failed** | Document WHY it failed, add correct version | `## Data Type Alerts and Anomalies (Validated)` |
| **New relationship pattern** | Add to relationship map | `## Relationship Overview (Counts + Purpose)` |
| **Schema assumption wrong** | Correct it, add warning | `## Data Type Alerts and Anomalies (Validated)` |
| **Performance issue** | Add optimization tip | `## Advanced Patterns (Optional)` |
| **New node property discovered** | Add to node definition | `## Core Labels (Counts + Key Properties)` |

### neo4j_schema.md Update Example

```markdown
## Added to Data Type Alerts and Anomalies (Validated):

### Items Field is a JSON String
-- WRONG: WHERE 'Item 2.02' IN r.items  -- Fails!
-- CORRECT: WHERE r.items CONTAINS 'Item 2.02'
```

### Cypher Update Checklist

After each analysis, ask:

```
Cypher Learnings:
- [ ] Did any query fail or return unexpected results?
- [ ] Did I discover a schema quirk not documented?
- [ ] Did I write a useful query pattern worth templating?
- [ ] Did I find a performance issue or optimization?
- [ ] Did I discover a new node property or relationship?

If YES to any → Update neo4j_schema.md
```

---

## Validation: Can We Regenerate?

### The Regeneration Test

Before marking analysis complete, ask:

> "If I gave another Claude instance only this SKILL.md (and its references), could they reach the **same Primary Driver** and **same Contributing Factors** for this accession number?"

### Checklist

```
Regeneration Readiness:
- [ ] Surprise calculation methodology clear in ## Step 6
- [ ] All Cypher queries used are documented in neo4j_schema.md
- [ ] Perplexity query principles documented in ## Step 5
- [ ] Conflict resolution logic is clear for source types used
- [ ] Evidence extraction format followed (strict for numbers)
- [ ] Data quality guardrails applied where relevant
```

### What "Same Conclusion" Means

| Must Match | Can Vary |
|------------|----------|
| Primary Driver identification | Exact wording of summary |
| Contributing Factors | Order of evidence bullets |
| Confidence level (High/Medium/Insufficient) | Specific quote selection |
| Surprise calculations | Section formatting |
| Data sources used | Query syntax variations |

---

## Examples of Good vs Bad Updates

| Good (Generic) | Bad (Specific) |
|----------------|----------------|
| "Book-to-bill < 1.0 signals order weakness" | "ROK's book-to-bill was 0.9x" |
| "When guidance surprise > EPS surprise, guidance dominates" | "ROK dropped 5.03% on Nov 2" |
| "CFO deflection on forward metrics = bearish signal" | "Laura Felice said '...'" |
| "Consensus from multiple sources > single source" | "Perplexity said $13.22 on Oct 30" |

---

## Accumulated Learnings Log

Format: `### {DATE} | {TICKER} | {ACCESSION}` → Pattern, New Learning, Sections Updated

*(Append entries after each analysis)*

---

## Post-Update Verification

Check `wc -l SKILL.md` after updates. If >500 lines, extract to reference files.

---

## Anti-Bloat Rules

> **Quality > Quantity. The 10-Second Test**: Would this help in a quick scan?

| NEVER | ALWAYS |
|-------|--------|
| Duplicate rules | Merge similar rules |
| Paragraphs | Bullets, tables, code |
| Specific tickers/dates | Generic patterns |
| "Nice to know" | Decision-changing info only |

**File Limits**: SKILL.md <500, neo4j_schema.md <600, examples.md <300, update-skills.md <500

**Deprecation**: `<!-- DEPRECATED {date}: Replaced by "X" -->` → Delete after 3 months

---

## Active Hook: Skill Update Reminder

A **Stop hook** is configured in `.claude/settings.json` (project-level) that reminds Claude to propose skill updates after completing an earnings-attribution analysis.

**How it works**: When Claude finishes responding, the hook checks if this conversation analyzed stock movement after an 8-K filing and reminds to follow Step 7 (propose skill updates).

---

*This protocol ensures the earnings-attribution skill continuously improves while maintaining the ability to regenerate any analysis with the same conclusion.*

*Version 3.0 | 2026-01-04 | Aligned with surprise-based analysis; removed pattern/weight references; updated to ranked confidence approach*

---

## Sources

This self-improvement protocol incorporates patterns from:

1. [Self-Improving AI: One Prompt That Makes Claude Learn From Every Mistake](https://dev.to/aviad_rozenhek_cba37e0660/self-improving-ai-one-prompt-that-makes-claude-learn-from-every-mistake-16ek) - META rules, anti-bloat patterns
2. [How We Use Claude Code Skills to Run 1,000+ ML Experiments a Day](https://huggingface.co/blog/sionic-ai/claude-code-skills-training) - Failure-first documentation, specific triggers
3. [Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/) - Progressive disclosure, file limits
4. **Startup Ideas Podcast** - "Claude Code Skills Beginner's Guide" - Skill Philosophy, 10-Step Process, "Expert not follower" principles
5. **Boring Marketer** - Skills methodology: Draft → Self-critique → Iterate → Test workflow
