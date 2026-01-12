# Claude Code CLI Skills - Complete Reference

> **Version**: 1.0 | **Updated**: 2026-01-03
> **Scope**: Claude Code CLI skills only (not API/SDK skills)

---

## Table of Contents

1. [What Are Skills?](#1-what-are-skills)
2. [SKILL.md Structure & Attributes](#2-skillmd-structure--attributes)
3. [Directory Structure & Locations](#3-directory-structure--locations)
4. [Progressive Disclosure Architecture](#4-progressive-disclosure-architecture)
5. [Tool Restrictions (allowed-tools)](#5-tool-restrictions-allowed-tools)
6. [Writing Effective Descriptions](#6-writing-effective-descriptions)
7. [Best Practices](#7-best-practices)
8. [Anti-Patterns to Avoid](#8-anti-patterns-to-avoid)
9. [Workflows & Feedback Loops](#9-workflows--feedback-loops)
10. [Testing & Validation](#10-testing--validation)
11. [Skill Development Lifecycle](#11-skill-development-lifecycle)
12. [Skills vs Other Claude Code Features](#12-skills-vs-other-claude-code-features)
13. [Complete Examples](#13-complete-examples)
14. [Troubleshooting](#14-troubleshooting)
15. [Checklist for Effective Skills](#15-checklist-for-effective-skills)

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
allowed-tools: Tool1, Tool2, Tool3
model: claude-opus-4-5-20251101
---

# Skill Title

## Instructions
Your markdown content here...
```

### All Frontmatter Attributes

| Attribute | Required | Type | Max Length | Description |
|-----------|----------|------|------------|-------------|
| `name` | **YES** | string | 64 chars | Skill identifier. **Must use lowercase letters, numbers, and hyphens only.** Cannot contain XML tags or reserved words ("anthropic", "claude"). Should match directory name. |
| `description` | **YES** | string | 1024 chars | What the Skill does and **when to use it**. Claude uses this for semantic matching. Cannot contain XML tags. This is the most critical field for triggering. |
| `allowed-tools` | No | comma-separated list | — | Tools Claude can use **without asking permission** when this Skill is active. Only supported in Claude Code. |
| `model` | No | model string | — | Specific Claude model to use (e.g., `claude-opus-4-5-20251101`). Defaults to conversation's current model. |

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

---

## 3. Directory Structure & Locations

### Skill Locations (Precedence Order)

| Location | Path | Applies To | Precedence |
|----------|------|------------|------------|
| **Enterprise** | Managed settings | All org users | Highest |
| **Personal** | `~/.claude/skills/{skill-name}/` | You, all projects | High |
| **Project** | `.claude/skills/{skill-name}/` | Anyone in repo | Medium |
| **Plugin** | `skills/{skill-name}/` (in plugin) | Plugin users | Lowest |

**Precedence rule**: If two Skills have the same name, the higher row wins.

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

## 6. Writing Effective Descriptions

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

## 7. Best Practices

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

## 8. Anti-Patterns to Avoid

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

## 9. Workflows & Feedback Loops

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

## 10. Testing & Validation

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

## 11. Skill Development Lifecycle

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

## 12. Skills vs Other Claude Code Features

| Feature | Trigger | Files | Use For |
|---------|---------|-------|---------|
| **Skills** | Automatic (semantic match) | Multiple + scripts | Specialized knowledge, complex workflows |
| **Slash Commands** | Manual (`/command`) | Single .md | Quick prompts, explicit invocation |
| **CLAUDE.md** | Always loaded | Single .md | Project rules, always-on context |
| **Subagents** | Manual/auto | Multiple | Isolated tasks, different permissions |
| **Hooks** | Tool events | Multiple | Automation, pre/post processing |
| **MCP** | Tool calls | External | External tools and data sources |

### When to Use Each

**Skills**: Claude should discover capability automatically; multiple files needed; complex workflows; team standardization

**Slash Commands**: Same prompt invoked repeatedly; single file; explicit control over when it runs

**CLAUDE.md**: Project-wide instructions; rules that apply to every conversation; codebase documentation

**Subagents**: Tasks need isolation; different tool access required; separate context window

**MCP**: Connect to external tools and data sources; Skills teach *how* to use those tools

---

## 13. Complete Examples

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
model: Opus 4.5
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

---

## 14. Troubleshooting

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

### View & Test Skills

Ask Claude: "What Skills are available?"

Then test with a matching request.

---

## 15. Checklist for Effective Skills

### Core Quality
- [ ] `name` is lowercase with hyphens only (max 64 chars)
- [ ] `description` is specific with trigger terms (max 1024 chars)
- [ ] `description` includes both WHAT it does and WHEN to use it
- [ ] Description written in third person
- [ ] SKILL.md body is under 500 lines
- [ ] Additional details are in separate reference files
- [ ] No time-sensitive information (or in "old patterns" section)
- [ ] Consistent terminology throughout
- [ ] File references are one level deep
- [ ] Progressive disclosure used appropriately

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

### Testing
- [ ] At least three test scenarios created
- [ ] Tested that Skill triggers correctly
- [ ] Tested with edge cases and out-of-scope requests
- [ ] Verified descriptions match user expectations
- [ ] Tool restrictions work as intended
- [ ] Supporting files link correctly

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
model: claude-opus-4-5-20251101
---
```

### Description Formula
```
[Capabilities] + [Trigger phrases] + [Key terms]
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

This reference was compiled from the following 13 official sources (accessed 2026-01-03):

### Official Documentation
1. https://code.claude.com/docs/en/skills - Claude Code CLI Skills Documentation
2. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices - Skill Authoring Best Practices
3. https://platform.claude.com/docs/en/build-with-claude/skills-guide - Using Agent Skills with the API
4. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/quickstart - Get Started with Agent Skills

### Engineering Blog
5. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills - Equipping Agents for the Real World

### GitHub Cookbooks
6. https://github.com/anthropics/claude-cookbooks/tree/main/skills - Skills Cookbook Repository
7. https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/02_skills_financial_applications.ipynb - Financial Applications Notebook
8. https://github.com/anthropics/claude-cookbooks/blob/main/skills/notebooks/03_skills_custom_development.ipynb - Custom Development Notebook

### Claude Blog Posts
9. https://claude.com/blog/skills - Skills Overview
10. https://www.claude.com/skills - Skills Landing Page
11. https://claude.com/blog/skills-explained - Skills: How They Work
12. https://claude.com/blog/building-skills-for-claude-code - Building Skills for Claude Code
13. https://claude.com/blog/how-to-create-skills-key-steps-limitations-and-examples - Creating Skills: Key Steps, Limitations, and Examples

---

*This reference compiled from official Claude Code documentation, Anthropic engineering blog, Claude Cookbooks, and best practices guides.*
