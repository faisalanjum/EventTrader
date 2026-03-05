# Claude Code CLI Skills - Complete Reference

> **Version**: 2.0 | **Updated**: 2026-03-04
> **Scope**: Claude Code skills following the [Agent Skills](https://agentskills.io) open standard (30+ compatible tools)

---

## Table of Contents

1. [What Are Skills?](#1-what-are-skills)
2. [SKILL.md Structure & Attributes](#2-skillmd-structure--attributes)
3. [Directory Structure & Locations](#3-directory-structure--locations)
4. [Progressive Disclosure Architecture](#4-progressive-disclosure-architecture)
5. [Tool Restrictions (allowed-tools)](#5-tool-restrictions-allowed-tools)
6. [Invocation Control](#6-invocation-control)
7. [String Substitutions & Arguments](#7-string-substitutions--arguments)
8. [Dynamic Context Injection](#8-dynamic-context-injection)
9. [Subagent Integration (context: fork)](#9-subagent-integration-context-fork)
10. [Skill Permissions](#10-skill-permissions)
11. [Writing Effective Descriptions](#11-writing-effective-descriptions)
12. [Best Practices](#12-best-practices)
13. [Anti-Patterns to Avoid](#13-anti-patterns-to-avoid)
14. [Workflows & Feedback Loops](#14-workflows--feedback-loops)
15. [Testing & Validation](#15-testing--validation)
16. [Skill Development Lifecycle](#16-skill-development-lifecycle)
17. [Skills vs Other Claude Code Features](#17-skills-vs-other-claude-code-features)
18. [Complete Examples](#18-complete-examples)
19. [Troubleshooting](#19-troubleshooting)
20. [Checklist for Effective Skills](#20-checklist-for-effective-skills)

---

## 1. What Are Skills?

Skills are **markdown files that teach Claude specialized capabilities**. They are:

| Property | Description |
|----------|-------------|
| **Model-invoked** | Claude automatically applies them when your request matches their description |
| **Composable** | Multiple skills can stack together; Claude coordinates their use |
| **Portable** | Work across Claude Code, Claude.ai, and the API using the same format |
| **Efficient** | Only load when needed through progressive disclosure |
| **Powerful** | Can include executable code for deterministic task execution |

Skills follow the [Agent Skills](https://agentskills.io) open standard, adopted by **31+ tools** including Cursor, VS Code, GitHub, Gemini CLI, OpenAI Codex, Junie (JetBrains), Roo Code, and others. A skills directory is available at `claude.com/connectors`.

> **Commands merged into skills.** Custom commands (`.claude/commands/`) now work as skills. Both locations are supported — if a skill and command share the same name, the **skill takes precedence**. Existing `.claude/commands/` files continue to work.

### Core Concept: Progressive Disclosure

Skills use a three-tier loading system to optimize context window usage:

```
Level 1: Metadata (~100 tokens)
├── name + description loaded at startup
├── Claude learns what skills exist
└── No full content loaded yet

Level 2: Full SKILL.md (<5k tokens)
├── Loads when task matches description
├── Contains core instructions
└── Links to reference files

Level 3: Supporting files (on-demand)
├── Reference docs loaded when needed
├── Scripts executed (not loaded)
└── Only relevant content enters context
```

### Bundled Skills

Claude Code ships with built-in skills:

| Skill | Description |
|-------|-------------|
| **`/simplify`** | Reviews recently changed files for code reuse, quality, and efficiency. Spawns three review agents in parallel. |
| **`/batch <instruction>`** | Orchestrates large-scale changes across a codebase. Decomposes work into 5–30 independent units, spawns one background agent per unit in isolated git worktrees, each implements its unit, runs tests, and opens a PR. |
| **`/debug [description]`** | Troubleshoots the current session by reading the session debug log. |

A bundled developer platform skill also activates automatically when code imports the Anthropic SDK.

### Extended Thinking

To enable extended thinking in a skill, include the word **"ultrathink"** anywhere in the skill content. Claude will use extended thinking tokens for deeper reasoning.

### When to Use Skills

**Use skills when:**
- Claude should discover capability automatically (vs. manual invocation)
- Multiple files or scripts needed
- Complex workflows with validation steps
- Team needs standardized, detailed guidance
- Reusable institutional knowledge across projects

**Examples:** PR review, PDF processing, database queries, earnings analysis

---

## 2. SKILL.md Structure & Attributes

### Complete File Format

```yaml
---
name: your-skill-name
description: What this Skill does and when to use it
allowed-tools: Read, Grep, Glob
model: claude-opus-4-6
context: fork
agent: Explore
argument-hint: "[issue-number]"
disable-model-invocation: true
user-invocable: true
hooks:
  PreToolUse:
    - matcher: Write
      command: echo "validated"
---

# Skill Title

## Instructions
Your markdown content here...
```

### All Frontmatter Attributes

| Attribute | Required | Type | Max Length | Description |
|-----------|----------|------|------------|-------------|
| `name` | Optional | string | 64 chars | Skill identifier. Lowercase letters, numbers, and hyphens only. Cannot contain XML tags or reserved words ("anthropic", "claude"). Defaults to directory name if omitted. |
| `description` | Recommended | string | 1024 chars | What the Skill does and **when to use it**. Claude uses this for semantic matching. Cannot contain XML tags. Most critical field for triggering. |
| `allowed-tools` | No | comma-separated list | — | Tools Claude can use **without asking permission** when this Skill is active. Only supported in Claude Code. |
| `model` | No | model string | — | Specific Claude model to use (e.g., `claude-opus-4-6`). Defaults to conversation's current model. |
| `argument-hint` | No | string | — | Hint shown during autocomplete to indicate expected arguments (e.g., `[issue-number]`). |
| `disable-model-invocation` | No | boolean | — | Set to `true` to prevent Claude from automatically loading the skill. Only the user can invoke via `/name`. Default: `false`. See [§6 Invocation Control](#6-invocation-control). |
| `user-invocable` | No | boolean | — | Set to `false` to hide from the `/` menu. Only Claude can invoke it. Default: `true`. See [§6 Invocation Control](#6-invocation-control). |
| `context` | No | string | — | Set to `fork` to run the skill in a forked subagent context. See [§9 Subagent Integration](#9-subagent-integration-context-fork). |
| `agent` | No | string | — | Which subagent type to use when `context: fork` is set (e.g., `Explore`, `Plan`, `general-purpose`, or custom agents from `.claude/agents/`). |
| `hooks` | No | object | — | Lifecycle hooks scoped to this skill. Same format as global hooks. |

**Open standard additional fields** (from [agentskills.io](https://agentskills.io)):

| Attribute | Type | Description |
|-----------|------|-------------|
| `license` | string | License name or reference to a bundled license file. |
| `compatibility` | string (max 500 chars) | Environment requirements (intended product, system packages, network access). |
| `metadata` | map (string→string) | Arbitrary key-value mapping for additional metadata (author, version, etc.). |

### Naming Conventions

Use **gerund form** (verb + -ing) for clarity:

```yaml
# GOOD - Gerund form (recommended)
name: processing-pdfs
name: analyzing-spreadsheets
name: reviewing-code

# ACCEPTABLE - Noun phrases
name: pdf-processing
name: code-review

# ACCEPTABLE - Action-oriented
name: process-pdfs
name: review-code

# BAD - Avoid these
name: helper          # Too vague
name: utils           # Too generic
name: claude-tools    # Reserved word
name: MySkill         # Must be lowercase
name: my_skill        # No underscores, use hyphens
```

### Skill Content Types

Skills fall into two categories:

| Type | Purpose | Typical Config |
|------|---------|----------------|
| **Reference** | Knowledge Claude applies to current work (conventions, patterns, style guides). Runs inline. | Default (both user and Claude can invoke) |
| **Task** | Step-by-step instructions for specific actions (deployments, commits). | Often paired with `disable-model-invocation: true` |

---

## 3. Directory Structure & Locations

### Skill Locations (Precedence Order)

| Location | Path | Applies To | Precedence |
|----------|------|------------|------------|
| **Enterprise** | Managed settings | All org users | Highest |
| **Personal** | `~/.claude/skills/{skill-name}/` | You, all projects | High |
| **Project** | `.claude/skills/{skill-name}/` | Anyone in repo | Medium |
| **Plugin** | `<plugin>/skills/{skill-name}/SKILL.md` | Plugin users | Lowest |

**Precedence rule**: If two Skills have the same name, the higher row wins.

> **Note**: Plugin skills are namespaced by their plugin directory. For example, a plugin at `my-plugin/skills/review/SKILL.md` is distinct from a project skill at `.claude/skills/review/SKILL.md`.

### Nested Directory Discovery (Monorepo Support)

When working with files in subdirectories, Claude Code automatically discovers skills from nested `.claude/skills/` directories. For example, editing files in `packages/frontend/` also looks for skills in `packages/frontend/.claude/skills/`. No special configuration needed.

### Skills from --add-dir

Skills defined in `.claude/skills/` within directories added via `--add-dir` are loaded automatically. Skills are picked up by live change detection — you can edit and add skills during a session without restarting.

### Minimal Skill (Single File)

```
my-skill/
└── SKILL.md
```

### Complex Skill (Multi-File)

```
earnings-attribution/
├── SKILL.md              # REQUIRED: overview, instructions (< 500 lines)
├── neo4j_schema.md       # Reference: loaded when needed
├── examples.md           # Reference: loaded when needed
└── scripts/
    ├── helper.py         # Utility: EXECUTED, not loaded into context
    └── validate.py       # Utility: EXECUTED, not loaded into context
```

### Domain-Specific Organization

For skills with multiple domains, organize content to avoid loading irrelevant context:

```
bigquery-skill/
├── SKILL.md                    # Overview and navigation
└── reference/
    ├── finance.md              # Revenue, billing metrics
    ├── sales.md                # Opportunities, pipeline
    ├── product.md              # API usage, features
    └── marketing.md            # Campaigns, attribution
```

**SKILL.md content:**
```markdown
## Available datasets

**Finance**: Revenue, ARR, billing → See [reference/finance.md](reference/finance.md)
**Sales**: Opportunities, pipeline → See [reference/sales.md](reference/sales.md)
**Product**: API usage, features → See [reference/product.md](reference/product.md)
```

Claude only loads the relevant reference file based on the user's query.

---

## 4. Progressive Disclosure Architecture

### How It Works

1. **Metadata pre-loaded**: At startup, only `name` and `description` from all Skills load into system prompt
2. **Files read on-demand**: Claude uses Read tool to access SKILL.md and other files when needed
3. **Scripts executed efficiently**: Utility scripts execute via bash without loading contents (only output consumes tokens)
4. **No context penalty for large files**: Reference files don't consume tokens until actually read

### Pattern 1: High-Level Guide with References

```markdown
---
name: pdf-processing
description: Extracts text and tables from PDF files, fills forms, merges documents.
---

# PDF Processing

## Quick start

Extract text with pdfplumber:
```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## Advanced features

**Form filling**: See [FORMS.md](FORMS.md) for complete guide
**API reference**: See [REFERENCE.md](REFERENCE.md) for all methods
**Examples**: See [EXAMPLES.md](EXAMPLES.md) for common patterns
```

### Pattern 2: Conditional Details

```markdown
# DOCX Processing

## Creating documents
Use docx-js for new documents. See [DOCX-JS.md](DOCX-JS.md).

## Editing documents
For simple edits, modify the XML directly.

**For tracked changes**: See [REDLINING.md](REDLINING.md)
**For OOXML details**: See [OOXML.md](OOXML.md)
```

### Critical Rules

| Rule | Reason |
|------|--------|
| **Keep SKILL.md under 500 lines** | Optimal performance and context efficiency |
| **Keep references one level deep** | Avoid SKILL.md → A.md → B.md chains |
| **Use forward slashes** | `scripts/helper.py` not `scripts\helper.py` |
| **Name files descriptively** | `form_validation_rules.md` not `doc2.md` |
| **Add TOC for files > 100 lines** | Helps Claude navigate large references |

### Table of Contents for Large Files

```markdown
# API Reference

## Contents
- Authentication and setup
- Core methods (create, read, update, delete)
- Advanced features (batch operations, webhooks)
- Error handling patterns
- Code examples

## Authentication and setup
...
```

---

## 5. Tool Restrictions (allowed-tools)

### How It Works

When a skill is active with `allowed-tools` specified:
- Claude can use listed tools **without permission prompts**
- Claude cannot use unlisted tools without your approval
- Only supported in Claude Code (not API)

### Syntax

```yaml
---
name: reading-files-safely
description: Read files without making changes
allowed-tools: Read, Grep, Glob
---
```

### Common Patterns

| Use Case | Tools | Why |
|----------|-------|-----|
| **Read-only analysis** | `Read, Grep, Glob` | Prevent accidental file writes |
| **PDF processing** | `Read, Bash(python:*)` | Run Python scripts, read files |
| **Git operations** | `Bash(git add:*), Bash(git status:*), Bash(git commit:*)` | Specific git commands only |
| **Security review** | `Read, Grep` | Inspect code without execution |
| **Database queries** | `Read, Bash(python:*)` | Query DBs, no shell access |

### Tool Names Reference

| Tool | Description |
|------|-------------|
| `Read` | Read file contents |
| `Write` | Write/create files |
| `Glob` | Find files by pattern |
| `Grep` | Search file contents |
| `Bash` | Execute shell commands |
| `Bash(python:*)` | Python commands only |
| `Bash(git*)` | Git commands only |
| `Bash(git add:*)` | Specific git subcommand |

**Tool names are case-sensitive.**

---

## 6. Invocation Control

Control who can invoke a skill and whether its description consumes context window space.

### Invocation Matrix

| Configuration | User can invoke? | Claude can invoke? | Description in context? |
|---------------|------------------|--------------------|------------------------|
| (default) | Yes | Yes | Yes — always loaded |
| `disable-model-invocation: true` | Yes | No | No — saves context budget |
| `user-invocable: false` | No | Yes | Yes — always loaded |

### When to Use Each

**Default (both enabled):** Most skills. Claude discovers them automatically, users can also invoke directly.

**`disable-model-invocation: true`:** Task-oriented skills that should only run on explicit user request. Examples: deployment scripts, destructive operations, one-off migrations. This also saves context budget since the description is not loaded at startup.

**`user-invocable: false`:** Internal/helper skills that Claude should use as building blocks but users shouldn't invoke directly. Examples: child skills called by a parent orchestrator, validation subroutines.

### Example

```yaml
---
name: deploy-production
description: Deploy the application to production. Use when asked to deploy or release.
disable-model-invocation: true
argument-hint: "[version]"
---

# Production Deployment

Only run when explicitly requested by the user.
...
```

---

## 7. String Substitutions & Arguments

Skills support variable substitution for arguments passed during invocation.

### Variables

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking the skill |
| `$ARGUMENTS[N]` | Access a specific argument by 0-based index |
| `$N` | Shorthand for `$ARGUMENTS[N]` (e.g., `$0`, `$1`) |
| `${CLAUDE_SESSION_ID}` | The current session ID |

**Fallback behavior:** If `$ARGUMENTS` is not present anywhere in the skill content, arguments are appended automatically as `ARGUMENTS: <value>`.

### Example: Component Migration

```yaml
---
name: migrate-component
description: Migrate a UI component from one framework to another.
argument-hint: "<component> <from-framework> <to-framework>"
---

# Migrate Component

Migrate the **$0** component from **$1** to **$2**.

1. Find the $0 component in the codebase
2. Analyze its $1 patterns and APIs
3. Rewrite using $2 equivalents
4. Update imports and tests
```

**Usage:** `/migrate-component SearchBar React Vue`

This substitutes `$0` → `SearchBar`, `$1` → `React`, `$2` → `Vue`.

### Example: Issue Fix

```yaml
---
name: fix-issue
description: Fix a GitHub issue by number.
argument-hint: "[issue-number]"
---

# Fix Issue $ARGUMENTS

Read the issue details and implement a fix:
```bash
gh issue view $ARGUMENTS
```
```

**Usage:** `/fix-issue 123` — substitutes `$ARGUMENTS` → `123`.

---

## 8. Dynamic Context Injection

Shell commands embedded in skill content are executed **during preprocessing** (before the skill is sent to Claude), and their output replaces the placeholder.

### Syntax

Use `` !`command` `` to inject command output:

```markdown
Current git branch: !`git branch --show-current`
```

### Example: PR Summary Skill

```yaml
---
name: pr-summary
description: Summarize changes in the current pull request.
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

# PR Summary

Analyze this pull request:

## PR diff
!`gh pr diff`

## PR comments
!`gh pr view --comments`

## Changed files
!`gh pr diff --name-only`

Summarize the changes, highlight risks, and suggest reviewers.
```

The `gh` commands execute when the skill loads, injecting their output into the skill content that Claude receives.

### Important Notes

- Commands execute during skill loading, **not** at Claude's runtime
- Command failures result in empty substitutions (no error propagated)
- Use for gathering context that changes between invocations (git state, PR info, environment)

---

## 9. Subagent Integration (context: fork)

Skills can run in isolated subagent contexts using `context: fork`. The skill content becomes the prompt for the subagent, and results are summarized back to the main conversation.

### How It Works

```yaml
---
name: codebase-explorer
description: Deep exploration of unfamiliar codebases.
context: fork
agent: Explore
---

# Explore Codebase

Analyze the project structure, key patterns, and entry points.
Report back with a summary of the architecture.
```

### Agent Types

| Agent | Use For |
|-------|---------|
| `Explore` | Read-only codebase exploration (cannot edit files) |
| `Plan` | Architecture planning (cannot edit files) |
| `general-purpose` | Full capabilities (read, write, execute) |
| Custom (`.claude/agents/*.md`) | Your own agent definitions |

### Skill vs Subagent Relationship

| Direction | Mechanism |
|-----------|-----------|
| **Skill → Subagent** | Set `context: fork` and `agent` in skill frontmatter. Skill content becomes the subagent prompt. |
| **Subagent → Skills** | Set `skills` field in agent frontmatter (`.claude/agents/*.md`). Agent auto-loads the named skills. |

### Example: Research Skill with Forked Agent

```yaml
---
name: research-topic
description: Deep research on a topic using web search.
context: fork
agent: general-purpose
argument-hint: "<topic>"
allowed-tools: WebSearch, WebFetch, Read, Write
---

# Research: $ARGUMENTS

Conduct thorough research on this topic:

1. Search for authoritative sources
2. Cross-reference at least 3 sources
3. Write a summary with citations to `research-output.md`
```

---

## 10. Skill Permissions

### Three Ways to Control Skill Access

**1. Disable all skills:** Deny the `Skill` tool in `/permissions`.

**2. Allow/deny specific skills** (in permission settings):
- `Skill(commit)` — exact match for `/commit`
- `Skill(test *)` — prefix match (matches `/test`, `/test-runner`, `/test-deploy`, etc.)

**3. Per-skill frontmatter:** Use `disable-model-invocation: true` to prevent Claude from auto-loading a skill. Use `user-invocable: false` to hide from the `/` menu.

### Character Budget

Skill descriptions consume context window space. The budget is:
- **2% of the context window** (dynamically scaled)
- **Fallback: 16,000 characters**
- Override with the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable

If you have many skills, some may be excluded from context. Run `/context` to check for warnings about excluded skills.

### Tips

- Use `disable-model-invocation: true` on rarely-used skills to save budget
- Keep descriptions concise — they directly consume the character budget
- Fewer, well-described skills are better than many vague ones

---

## 11. Writing Effective Descriptions

The description field is **the most critical element** for skill triggering. Claude uses semantic similarity to match your request against descriptions.

### Structure of an Effective Description

A good description has three parts:

```
[What it does] + [When to use it] + [Trigger keywords]
```

### Examples

**PDF Processing:**
```yaml
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
```

**Excel Analysis:**
```yaml
description: Analyze Excel spreadsheets, create pivot tables, generate charts. Use when analyzing Excel files, spreadsheets, tabular data, or .xlsx files.
```

**Git Commit Helper:**
```yaml
description: Generate descriptive commit messages by analyzing git diffs. Use when the user asks for help writing commit messages or reviewing staged changes.
```

**Earnings Attribution:**
```yaml
description: Analyzes why stocks moved after 8-K earnings filings. Use when asked to analyze stock movements, earnings reactions, or determine the primary driver of price changes following SEC filings.
```

### Description Rules

| Rule | Bad | Good |
|------|-----|------|
| **Be specific** | "Helps with documents" | "Extracts text from PDF files, fills forms" |
| **Include triggers** | "Processes data" | "Use when working with CSV files or data analysis" |
| **Write in third person** | "I can help you process PDFs" | "Processes PDF files and extracts text" |
| **Include key terms** | "Document helper" | "PDFs, forms, document extraction, pdfplumber" |
| **Avoid vague language** | "Data stuff" | "Analyze Excel spreadsheets and create pivot tables" |

### Testing Your Description

Ask yourself:
- "If a user says [typical request], will this description match?"
- "Are the key words users would say included?"
- "Is it clear WHEN to use this skill, not just what it does?"

---

## 12. Best Practices

### Conciseness

The **context window is a public good**. Your Skill shares context with:
- System prompt
- Conversation history
- Other Skills' metadata
- Your actual request

**Default assumption**: Claude is already very smart. Only add context Claude doesn't already have.

**Challenge each piece of information:**
- "Does Claude really need this explanation?"
- "Can I assume Claude knows this?"
- "Does this paragraph justify its token cost?"

**Good (50 tokens):**
```markdown
## Extract PDF text

Use pdfplumber for text extraction:
```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
```

**Bad (150 tokens):**
```markdown
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. There are many libraries available for PDF processing, but we
recommend pdfplumber because it's easy to use...
```

### Degrees of Freedom

Match specificity to task fragility:

| Freedom Level | When to Use | Example |
|---------------|-------------|---------|
| **High** (text instructions) | Multiple approaches valid, context-dependent | Code review guidelines |
| **Medium** (pseudocode/templates) | Preferred pattern exists, some variation acceptable | Report generation template |
| **Low** (exact scripts) | Operations fragile, consistency critical | Database migration commands |

**High freedom example:**
```markdown
## Code review process
1. Analyze the code structure and organization
2. Check for potential bugs or edge cases
3. Suggest improvements for readability
4. Verify adherence to project conventions
```

**Low freedom example:**
```markdown
## Database migration

Run exactly this script:
```bash
python scripts/migrate.py --verify --backup
```
Do not modify the command or add additional flags.
```

### Use Consistent Terminology

Choose one term and use it throughout:

| Good (consistent) | Bad (inconsistent) |
|-------------------|-------------------|
| Always "API endpoint" | Mix "API endpoint", "URL", "route", "path" |
| Always "field" | Mix "field", "box", "element", "control" |
| Always "extract" | Mix "extract", "pull", "get", "retrieve" |

### Provide Utility Scripts

Even if Claude could write a script, pre-made scripts offer advantages:
- More reliable than generated code
- Save tokens (no code in context)
- Save time (no generation required)
- Ensure consistency across uses

**Tell Claude to EXECUTE, not READ:**
```markdown
## Utility scripts

**analyze_form.py**: Extract all form fields from PDF
```bash
python scripts/analyze_form.py input.pdf > fields.json
```
```

---

## 13. Anti-Patterns to Avoid

### Windows-Style Paths

```yaml
# BAD
scripts\helper.py

# GOOD
scripts/helper.py
```

### Deeply Nested References

```markdown
# BAD - Too deep
SKILL.md → advanced.md → details.md → actual_info.md

# GOOD - One level deep
SKILL.md → advanced.md
SKILL.md → reference.md
SKILL.md → examples.md
```

### Too Many Options

```markdown
# BAD - Confusing
"You can use pypdf, or pdfplumber, or PyMuPDF, or pdf2image, or..."

# GOOD - Provide a default with escape hatch
"Use pdfplumber for text extraction:
```python
import pdfplumber
```
For scanned PDFs requiring OCR, use pdf2image with pytesseract instead."
```

### Time-Sensitive Information

```markdown
# BAD - Will become wrong
If you're doing this before August 2025, use the old API.
After August 2025, use the new API.

# GOOD - Use "old patterns" section
## Current method
Use the v2 API endpoint: `api.example.com/v2/messages`

## Old patterns
<details>
<summary>Legacy v1 API (deprecated 2025-08)</summary>
The v1 API used: `api.example.com/v1/messages`
</details>
```

### Punting Errors to Claude

```python
# BAD - Let Claude figure it out
def process_file(path):
    return open(path).read()

# GOOD - Handle explicitly
def process_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        print(f"File {path} not found, creating default")
        with open(path, 'w') as f:
            f.write('')
        return ''
```

### Magic Numbers

```python
# BAD - Why these values?
TIMEOUT = 47
RETRIES = 5

# GOOD - Self-documenting
# HTTP requests typically complete within 30 seconds
REQUEST_TIMEOUT = 30

# Three retries balances reliability vs speed
MAX_RETRIES = 3
```

### Assuming Tools Are Installed

```markdown
# BAD
"Use the pdf library to process the file."

# GOOD
"Install required package: `pip install pypdf`

Then use it:
```python
from pypdf import PdfReader
reader = PdfReader("file.pdf")
```"
```

---

## 14. Workflows & Feedback Loops

### Use Workflows for Complex Tasks

Break complex operations into clear, sequential steps with checklists:

```markdown
## PDF form filling workflow

Copy this checklist and check off items as you complete them:

```
Task Progress:
- [ ] Step 1: Analyze the form (run analyze_form.py)
- [ ] Step 2: Create field mapping (edit fields.json)
- [ ] Step 3: Validate mapping (run validate_fields.py)
- [ ] Step 4: Fill the form (run fill_form.py)
- [ ] Step 5: Verify output (run verify_output.py)
```

**Step 1: Analyze the form**
Run: `python scripts/analyze_form.py input.pdf`
This extracts form fields and their locations.

**Step 2: Create field mapping**
Edit `fields.json` to add values for each field.

**Step 3: Validate mapping**
Run: `python scripts/validate_fields.py fields.json`
Fix any validation errors before continuing.
```

### Implement Feedback Loops

**Pattern**: Run validator → fix errors → repeat

```markdown
## Document editing process

1. Make your edits to `word/document.xml`
2. **Validate immediately**: `python ooxml/scripts/validate.py unpacked_dir/`
3. If validation fails:
   - Review the error message carefully
   - Fix the issues in the XML
   - Run validation again
4. **Only proceed when validation passes**
5. Rebuild: `python ooxml/scripts/pack.py unpacked_dir/ output.docx`
```

### Conditional Workflows

```markdown
## Document modification workflow

1. Determine the modification type:

   **Creating new content?** → Follow "Creation workflow" below
   **Editing existing content?** → Follow "Editing workflow" below

2. Creation workflow:
   - Use docx-js library
   - Build document from scratch
   - Export to .docx format

3. Editing workflow:
   - Unpack existing document
   - Modify XML directly
   - Validate after each change
   - Repack when complete
```

---

## 15. Testing & Validation

### Build Evaluations BEFORE Documentation

Create evaluations before writing extensive documentation to ensure your Skill solves real problems:

1. **Identify gaps**: Run Claude on representative tasks without a Skill. Document specific failures.
2. **Create evaluations**: Build 3 scenarios that test these gaps
3. **Establish baseline**: Measure Claude's performance without the Skill
4. **Write minimal instructions**: Create just enough content to pass evaluations
5. **Iterate**: Execute evaluations, compare against baseline, refine

### Evaluation Structure

```json
{
  "skills": ["pdf-processing"],
  "query": "Extract all text from this PDF file and save it to output.txt",
  "files": ["test-files/document.pdf"],
  "expected_behavior": [
    "Successfully reads the PDF file using pdfplumber",
    "Extracts text content from all pages",
    "Saves extracted text to output.txt"
  ]
}
```

### Test with All Models You Plan to Use

| Model | Testing Consideration |
|-------|----------------------|
| **Claude Haiku** | Does the Skill provide enough guidance? |
| **Claude Sonnet** | Is the Skill clear and efficient? |
| **Claude Opus** | Does the Skill avoid over-explaining? |

What works for Opus might need more detail for Haiku.

### Three Test Scenarios

1. **Normal operations**: Typical requests the skill should handle
2. **Edge cases**: Incomplete or unusual inputs
3. **Out-of-scope requests**: Related tasks the skill shouldn't trigger for

### Observe How Claude Navigates Skills

Watch for:
- **Unexpected exploration paths**: Structure might not be intuitive
- **Missed connections**: Links might need to be more explicit
- **Overreliance on certain sections**: Content might belong in SKILL.md
- **Ignored content**: Bundled file might be unnecessary

---

## 16. Skill Development Lifecycle

### Step 1: Identify the Need

Start with real, repeated tasks (encountered 5+ times). Ask:
- What specific task does this solve?
- What triggers it?
- What does success look like?

### Step 2: Complete Task Without Skill

Work through a problem with Claude using normal prompting. Notice:
- What context you repeatedly provide
- What information Claude lacks
- What procedures you explain each time

### Step 3: Create the Skill

**Directory structure:**
```bash
# Personal skill
mkdir -p ~/.claude/skills/my-skill

# Project skill
mkdir -p .claude/skills/my-skill
```

**Write SKILL.md:**
```yaml
---
name: my-skill
description: [What it does]. Use when [triggers].
---

# My Skill

[Instructions...]
```

### Step 4: Test and Iterate

1. Exit and restart Claude Code to load the new Skill
2. Ask: "What Skills are available?"
3. Test with a matching request
4. Verify Claude asks to use the Skill
5. Check that it follows instructions correctly

### Step 5: Enhance with References

When SKILL.md approaches 500 lines:
1. Extract detailed content to reference files
2. Add links: `See [REFERENCE.md](REFERENCE.md) for details`
3. Add utility scripts for deterministic operations

### Step 6: Version and Document

```markdown
---
*Version 2.1 | 2026-01-02 | Added Perplexity integration*
```

### Iterative Development with Claude

**Creating:**
1. Complete a task without a Skill
2. Identify reusable patterns
3. Ask Claude to create a Skill: "Create a Skill that captures this pattern"
4. Review for conciseness
5. Test on similar tasks

**Improving:**
1. Use the Skill in real workflows
2. Observe where Claude struggles
3. Return to improve with specific observations
4. Apply and test changes
5. Repeat based on usage

---

## 17. Skills vs Other Claude Code Features

| Feature | Trigger | Files | Use For |
|---------|---------|-------|---------|
| **Skills** | Automatic (semantic match) or manual (`/skill`) | Multiple + scripts | Specialized knowledge, complex workflows |
| **CLAUDE.md** | Always loaded | Single .md | Project rules, always-on context |
| **Subagents** (`.claude/agents/`) | Manual/auto | Multiple | Isolated tasks, different permissions |
| **Hooks** | Tool events | Multiple | Automation, pre/post processing |
| **MCP** | Tool calls | External | External tools and data sources |
| **Plugins** | Package install | Multiple | Distributable skill bundles |
| **Memory** | Automatic | `MEMORY.md` + topic files | Persistent context across sessions |

> **Note:** Custom commands (`.claude/commands/`) have been merged into skills. Both locations work; skills take precedence on name conflicts.

### When to Use Each

**Skills**: Claude should discover capability automatically; multiple files needed; complex workflows; team standardization

**CLAUDE.md**: Project-wide instructions; rules that apply to every conversation; codebase documentation

**Subagents**: Tasks need isolation; different tool access required; separate context window

**MCP**: Connect to external tools and data sources; Skills teach *how* to use those tools

**Plugins**: Distribute skills as installable packages for other teams/projects

---

## 18. Complete Examples

### Example 1: Read-Only Analysis Skill

```yaml
---
name: explaining-code
description: Explains code with visual diagrams and analogies. Use when explaining how code works, teaching about a codebase, or when the user asks "how does this work?"
allowed-tools: Read, Grep, Glob
---

# Explaining Code

When explaining code, always include:

1. **Start with an analogy**: Compare to something from everyday life
2. **Draw a diagram**: Use ASCII art to show flow, structure, or relationships
3. **Walk through the code**: Explain step-by-step what happens
4. **Highlight a gotcha**: What's a common mistake or misconception?

Keep explanations conversational. For complex concepts, use multiple analogies.
```

### Example 2: Multi-File Financial Analysis Skill

**Directory structure:**
```
earnings-attribution/
├── SKILL.md
├── neo4j_schema.md
├── examples.md
└── scripts/
    └── helper.py
```

**SKILL.md:**
```yaml
---
name: earnings-attribution
description: Analyzes why stocks moved after 8-K earnings filings. Use when asked to analyze stock movements, earnings reactions, or determine the primary driver of price changes following SEC filings.
allowed-tools: Read, Grep, Glob
model: claude-opus-4-6
---

## Additional resources

- For Neo4j schema details, see [neo4j_schema.md](neo4j_schema.md)
- For usage examples, see [examples.md](examples.md)

## Utility scripts

To validate input files:
```bash
python scripts/helper.py input.txt
```

## Process Overview

```
Step 1: Get Report → Identify the move (direction, magnitude)
Step 2: Query News → Get beat/miss, guidance, analyst reactions
Step 3: Query Transcript → Get management commentary
Step 4: Query Perplexity → Validate and fill gaps (ALWAYS)
Step 5: Synthesize → One clear reason why stock moved
```

[... detailed instructions ...]
```

### Example 3: Data Warehouse Skill with Domain Organization

```
bigquery-skill/
├── SKILL.md
└── reference/
    ├── finance.md
    ├── sales.md
    ├── product.md
    └── marketing.md
```

**SKILL.md:**
```yaml
---
name: bigquery-analysis
description: Query and analyze BigQuery data warehouse. Use when analyzing company data, metrics, KPIs, or when working with BigQuery SQL.
allowed-tools: Read, Bash(python:*)
---

# BigQuery Data Analysis

## Quick start workflow

1. Clarify the exact question being asked
2. Check if a dashboard already answers this
3. Identify the right data source
4. Write and validate the query
5. Present results with context

## Available datasets

**Finance**: Revenue, ARR, billing → See [reference/finance.md](reference/finance.md)
**Sales**: Opportunities, pipeline → See [reference/sales.md](reference/sales.md)
**Product**: API usage, features → See [reference/product.md](reference/product.md)
**Marketing**: Campaigns, attribution → See [reference/marketing.md](reference/marketing.md)

## Standard filters (ALWAYS apply)

- Exclude test accounts: `WHERE account_type != 'test'`
- Use complete periods only: `WHERE date < CURRENT_DATE()`
- Filter deleted records: `WHERE is_deleted = FALSE`

## Quick search

Find specific metrics:
```bash
grep -i "revenue" reference/finance.md
grep -i "pipeline" reference/sales.md
```
```

### Example 4: Forked Subagent Skill with Dynamic Injection

```yaml
---
name: pr-review
description: Comprehensive pull request review with automated context gathering. Use when asked to review a PR.
context: fork
agent: general-purpose
allowed-tools: Read, Grep, Glob, Bash(gh *)
argument-hint: "[pr-number]"
---

# PR Review

## Context (auto-gathered)

### Changed files
!`gh pr diff --name-only`

### PR description
!`gh pr view`

### Full diff
!`gh pr diff`

## Review Instructions

Analyze the PR above. For each changed file:

1. **Correctness**: Logic errors, edge cases, off-by-one errors
2. **Security**: Injection, XSS, auth issues, secrets exposure
3. **Performance**: N+1 queries, missing indexes, unnecessary allocations
4. **Style**: Consistency with codebase conventions

Summarize findings as: APPROVE, REQUEST_CHANGES, or COMMENT with specific line references.
```

**Usage:** `/pr-review 456` — gathers PR context via `gh` commands, then runs a full review in a forked subagent.

---

## 19. Troubleshooting

### Skill Not Triggering

**Problem**: Created a Skill but Claude doesn't use it.

**Solution**: Review your description.
- Include specific actions and keywords
- Add "Use when..." trigger phrases
- Include terms users would naturally say

### Skill Doesn't Load

**Check file path** (case-sensitive):
```
Personal:  ~/.claude/skills/my-skill/SKILL.md
Project:   .claude/skills/my-skill/SKILL.md
```

**Check YAML syntax:**
- Start with `---` on line 1 (no blank lines before)
- End with `---` before Markdown content
- Use spaces (not tabs) for indentation

### Skill Has Errors

**Check dependencies:**
```bash
pip install pypdf pdfplumber
```

**Check script permissions:**
```bash
chmod +x scripts/*.py
```

**Check file paths:**
```
✓ scripts/helper.py
✗ scripts\helper.py
```

### Multiple Skills Conflict

**Problem**: Claude uses the wrong Skill.

**Solution**: Make descriptions distinct:
```yaml
# Instead of both saying "Data analysis"
Skill 1: "Analyzes sales data in Excel files and CRM exports"
Skill 2: "Analyzes log files and system metrics"
```

### Claude Doesn't See All My Skills

**Problem**: Some skills are missing from Claude's awareness.

**Cause**: Skill descriptions exceeded the character budget (2% of context window, ~16,000 chars fallback).

**Solutions**:
- Shorten descriptions of existing skills
- Use `disable-model-invocation: true` on rarely-used skills to exclude their descriptions from the budget
- Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable
- Run `/context` to check for excluded skills

### Skill Triggers Too Often

**Problem**: Claude auto-loads a skill when it shouldn't.

**Solution**: Add `disable-model-invocation: true` to the frontmatter. The skill will still be available via `/name` but Claude won't auto-invoke it.

### View & Test Skills

Ask Claude: "What Skills are available?"

Then test with a matching request.

---

## 20. Checklist for Effective Skills

### Core Quality
- [ ] `name` is lowercase with hyphens only (max 64 chars), or omitted (defaults to directory name)
- [ ] `description` is specific with trigger terms (max 1024 chars)
- [ ] `description` includes both WHAT it does and WHEN to use it
- [ ] Description written in third person
- [ ] SKILL.md body is under 500 lines
- [ ] Additional details are in separate reference files
- [ ] No time-sensitive information (or in "old patterns" section)
- [ ] Consistent terminology throughout
- [ ] File references are one level deep
- [ ] Progressive disclosure used appropriately

### Invocation & Arguments
- [ ] Invocation control configured appropriately (`disable-model-invocation` / `user-invocable`)
- [ ] `argument-hint` set if the skill accepts arguments
- [ ] String substitutions (`$ARGUMENTS`, `$0`, etc.) tested if used
- [ ] Dynamic injection (`` !`command` ``) tested if used

### Structure
- [ ] Uses forward slashes in all paths
- [ ] Files named descriptively
- [ ] TOC included for files > 100 lines
- [ ] Workflows have clear, numbered steps
- [ ] Examples are concrete, not abstract

### Code and Scripts
- [ ] Scripts solve problems rather than punt to Claude
- [ ] Error handling is explicit and helpful
- [ ] No magic numbers (all values documented)
- [ ] Required packages listed in instructions
- [ ] Scripts have clear execution instructions
- [ ] Validation/verification steps for critical operations
- [ ] Feedback loops included for quality-critical tasks

### Subagent Integration
- [ ] `context: fork` set if skill needs isolated execution
- [ ] `agent` field specifies appropriate subagent type
- [ ] Forked skills return concise results (subagent output is summarized)

### Testing
- [ ] At least three test scenarios created
- [ ] Tested that Skill triggers correctly
- [ ] Tested with edge cases and out-of-scope requests
- [ ] Verified descriptions match user expectations
- [ ] Tool restrictions work as intended
- [ ] Supporting files link correctly
- [ ] Character budget impact checked (run `/context`)

### Deployment
- [ ] Version documented in SKILL.md footer
- [ ] Ready for team sharing (if project skill)
- [ ] Team feedback incorporated

---

## Quick Reference Card

### File Structure
```
skill-name/
├── SKILL.md           # Required (< 500 lines)
├── reference.md       # Optional (loaded when needed)
└── scripts/
    └── helper.py      # Optional (executed, not loaded)
```

### Frontmatter Template
```yaml
---
name: lowercase-with-hyphens
description: What it does. Use when [triggers].
allowed-tools: Read, Grep, Glob
model: claude-opus-4-6
argument-hint: "[args]"
context: fork
agent: general-purpose
disable-model-invocation: false
user-invocable: true
hooks: {}
---
```

### Description Formula
```
[Capabilities] + [Trigger phrases] + [Key terms]
```

### String Substitutions
```
$ARGUMENTS          → all arguments
$ARGUMENTS[0], $0   → first argument
$ARGUMENTS[1], $1   → second argument
${CLAUDE_SESSION_ID} → session ID
!`command`           → dynamic injection (preprocessing)
```

### Invocation Control Quick Reference
```
default                          → user: yes, claude: yes
disable-model-invocation: true   → user: yes, claude: no
user-invocable: false            → user: no,  claude: yes
```

### Progressive Disclosure Pattern
```markdown
## Quick start
[Essential instructions]

## Advanced features
See [REFERENCE.md](REFERENCE.md) for details.

## Utility scripts
Run: `python scripts/helper.py input.txt`
```

---

## Sources

This reference was compiled from the following sources (accessed 2026-03-04):

### Official Documentation
1. https://code.claude.com/docs/en/skills - Claude Code CLI Skills Documentation
2. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices - Skill Authoring Best Practices
3. https://platform.claude.com/docs/en/build-with-claude/skills-guide - Using Agent Skills with the API
4. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/quickstart - Get Started with Agent Skills
5. https://code.claude.com/docs/en/sub-agents - Subagents Documentation

### Open Standard
6. https://agentskills.io - Agent Skills Open Standard
7. https://agentskills.io/specification - Agent Skills Specification
8. https://github.com/agentskills/agentskills - Agent Skills GitHub Repository

### Engineering Blog
9. https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills - Equipping Agents for the Real World (updated 2026-01-28)

### GitHub Cookbooks
10. https://github.com/anthropics/claude-cookbooks/tree/main/skills - Skills Cookbook Repository
11. https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/02_skills_financial_applications.ipynb - Financial Applications Notebook
12. https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/03_skills_custom_development.ipynb - Custom Development Notebook

### Claude Blog Posts
13. https://claude.com/blog/skills - Skills Overview (updated 2025-12-18)
14. https://claude.com/blog/skills-explained - Skills: How They Work (updated 2026-02-11)
15. https://claude.com/blog/building-skills-for-claude-code - Building Skills for Claude Code
16. https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples - Creating Skills: Key Steps, Limitations, and Examples

### Changelog
17. GitHub releases and Claude Code changelog

> **Note:** Some URLs originally at `anthropic.com/engineering/` now redirect to `claude.com/blog/`.

---

*This reference compiled from official Claude Code documentation, Agent Skills open standard, Anthropic engineering blog, Claude Cookbooks, and best practices guides.*
