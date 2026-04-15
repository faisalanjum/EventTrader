# Advisor Tool — Complete Reference

> **Standalone reference for Claude Code CLI advisor architecture, haiku binary patch bypass, SDK integration, risks, and production usage.**
> Extracted from Infrastructure.md Parts 8.8 & 8.9. This file is the single source of truth for all advisor-related content.
>
> Last updated: 2026-04-10 | CLI version: 2.1.100 | Patch status: WORKING

---

## Table of Contents

1. [What is the Advisor?](#1-what-is-the-advisor)
2. [Complete Binary Analysis](#2-complete-binary-analysis)
3. [Model Resolution Pipeline](#3-model-resolution-pipeline)
4. [Startup Flow](#4-startup-flow)
5. [Per-Query Flow](#5-per-query-flow)
6. [Built-In Advisor System Prompt & Invocation Control](#6-built-in-advisor-system-prompt--invocation-control)
7. [Valid Configurations (Unpatched)](#7-valid-configurations-unpatched)
8. [Settings Priority & Per-Session SDK Control](#8-settings-priority--per-session-sdk-control)
9. [K8s hostPath Implications](#9-k8s-hostpath-implications)
10. [API vs CLI Discrepancy](#10-api-vs-cli-discrepancy)
11. [Feature Flag: tengu_sage_compass2](#11-feature-flag-tengu_sage_compass2)
12. [ANTHROPIC_BASE_URL Catch-22](#12-anthropic_base_url-catch-22)
13. [Haiku Binary Patch Bypass](#13-haiku-binary-patch-bypass)
14. [10 Failed Approaches (Exhaustive)](#14-10-failed-approaches-exhaustive)
15. [Test Results](#15-test-results)
16. [SDK Iteration Proof](#16-sdk-iteration-proof)
17. [Production Usage](#17-production-usage)
18. [Valid Configurations (Patched)](#18-valid-configurations-patched)
19. [Multi-Task Model Switching](#19-multi-task-model-switching)
20. [Auto-Update Impact & Re-Patching](#20-auto-update-impact--re-patching)
21. [Patch Script Reference](#21-patch-script-reference)
22. [Risks, Gotchas & Caveats](#22-risks-gotchas--caveats)
23. [Research Agent Findings](#23-research-agent-findings)
24. [Files](#24-files)

---

## 1. What is the Advisor?

The advisor is a **server-side tool** — it does NOT appear in the client tool list (init message `tools` array). It's injected by the Anthropic API when the client sends `advisorModel` configuration. Think of it as a "second opinion" model that the base model can consult during complex reasoning.

**Officially supported since April 9, 2026.** The Anthropic API documentation and blog explicitly list haiku as a valid executor model:
- API docs: `advisor_20260301` tool type supports haiku, sonnet, and opus as executor
- Blog: *"The advisor strategy also works with Haiku as the executor"*
- The CLI restriction is a **product decision**, not a technical limitation

**Auto-assignment: NONE.** When `advisorModel` is not in settings, NO model gets an advisor. Tested all 3 base models with `advisorModel` absent — all returned "advisor not available."

---

## 2. Complete Binary Analysis

All functions below were extracted via `strings` + `grep -oP` from the CLI binary at `/home/faisal/.local/share/claude/versions/2.1.100`. The binary is a Node.js SEA (Single Executable Application), ELF 64-bit, 232 MB, with bundled, minified JavaScript.

### Core Gate Functions

```javascript
// WyH — BASE MODEL gate (the primary blocker for haiku)
// Checks if the base model string is allowed to use the advisor
// THIS is what the binary patch modifies
function WyH(H) {
    let $ = H.toLowerCase();
    return $.includes("opus-4-6") || $.includes("sonnet-4-6") || !1
}

// peH — ADVISOR MODEL gate
// Checks if the specified advisor model is valid (must be opus or sonnet)
// NOT modified by the patch — advisor models stay restricted to opus/sonnet
function peH(H) {
    let $ = H.toLowerCase();
    return $.includes("opus-4-6") || $.includes("sonnet-4-6") || !1
}

// Nb — MASTER ADVISOR ENABLE check
// ALL advisor functionality depends on this returning true
// If this returns false, advisor is dead — no WyH check even runs
function Nb() {
    return !pH(process.env.CLAUDE_CODE_DISABLE_ADVISOR_TOOL)
        && nq() === "firstParty"       // apiSource must be firstParty (not Bedrock/Vertex/3P)
        && Q6H()                        // additional auth check
        && !pH(process.env.CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS)
        && (R$("tengu_sage_compass2", {}).enabled ?? false)  // server-side feature flag
}

// PIK — PER-QUERY advisor resolver
// Called as PIK(A.advisorModel, A.model) on EVERY API request
// This is Gate 2 — runs every time, cannot be bypassed by config
function PIK(H, $) {
    if (!Nb() || !H) return;
    let q = u0(Z_(H));               // resolve advisor model to full ID
    if (!WyH($)) {                    // Gate 2: check BASE model
        N("[AdvisorTool] Skipping advisor - base model " + $ + " does not support advisor");
        return;
    }
    if (!peH(q)) {                    // check ADVISOR model
        N("[AdvisorTool] Skipping advisor - " + q + " is not a valid advisor model");
        return;
    }
    return q;                          // returns resolved advisor model ID
}

// WIK — Settings-based advisor reader
// Reads advisorModel from merged settings — NO WyH check on READ
// This is why settings path bypasses Gate 1 but not Gate 2
function WIK() {
    if (!Nb()) return;
    return P6().advisorModel           // reads from merged settings
}

// jw — firstParty detection
// Critical for understanding why proxy approaches fail
function jw() {
    let H = process.env.ANTHROPIC_BASE_URL;
    if (!H) return true;               // no override → firstParty
    try {
        let $ = new URL(H).host;
        return ["api.anthropic.com"].includes($)  // only api.anthropic.com is firstParty
    } catch { return false }
}

// GK7 — Base URL resolution for API calls
function GK7() {
    return process.env.ANTHROPIC_BASE_URL
        || process.env.CLAUDE_CODE_API_BASE_URL
        || "https://api.anthropic.com"
}

// mI7 — /advisor slash command handler
function mI7(H, $, q) {
    if (H === "off") {
        q(z => z.advisorModel === void 0 ? z : {...z, advisorModel: void 0});
        L6("userSettings", {advisorModel: void 0});
        return "Advisor disabled";
    }
    let K = u0(H);
    q(z => z.advisorModel === K ? z : {...z, advisorModel: K});
    L6("userSettings", {advisorModel: K});
    let _ = mx(K), A = mx($);
    let f = "Advisor set to " + _;
    if (!WyH($)) f += " ... (warning: current model doesn't support advisor)";
    return f;
}

// Valid advisor menu choices — only these two appear in /advisor picker
GyH = ["opus", "sonnet"]
```

---

## 3. Model Resolution Pipeline

```
User selects "haiku" → Z_("haiku") → x0() → jZH() → DN()
  DN() checks: ANTHROPIC_SMALL_FAST_MODEL env var first, then ANTHROPIC_DEFAULT_HAIKU_MODEL
  Falls back to: wD() → s1q() applies modelOverrides → returns default model config slot
  → returns "claude-haiku-4-5-20251001"

WyH("claude-haiku-4-5-20251001")
  → "claude-haiku-4-5-20251001".toLowerCase().includes("opus-4-6") → false
  → "claude-haiku-4-5-20251001".toLowerCase().includes("sonnet-4-6") → false
  → returns false → BLOCKED
```

Key functions in the pipeline:
```javascript
// Z_ — Master model resolver (short name → full model ID)
// Calls x0/jZH/DN which check env vars first, then wD() defaults

// x0()/jZH()/DN() — Per-tier model resolvers
// Check ANTHROPIC_DEFAULT_*_MODEL env vars FIRST, then fall back to wD()
// haiku: envVarPriority: ["ANTHROPIC_SMALL_FAST_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL"]
// sonnet: envVarPriority: ["ANTHROPIC_DEFAULT_SONNET_MODEL"]
// opus:   envVarPriority: ["ANTHROPIC_DEFAULT_OPUS_MODEL"]

// wD() — Default model config with modelOverrides applied
// s1q(H) applies modelOverrides: maps canonical IDs (e.g., "claude-opus-4-6") to
// provider-specific IDs (Bedrock ARNs, Vertex names). Keys must be canonical IDs.

// d6H() — Capabilities check for 3P providers
// Returns early if apiSource === "firstParty" — ANTHROPIC_DEFAULT_*_MODEL_SUPPORTED_CAPABILITIES
// env vars are 3P-only and have no effect on firstParty accounts

// URH() — Model validation function
// ANTHROPIC_CUSTOM_MODEL_OPTION skips validation (returns valid:true)
// BUT does NOT skip WyH — these are separate checks
```

---

## 4. Startup Flow

Complete flow traced from the binary:

```javascript
// Step 1: Resolve base model
let y9 = Z_(hq ?? YG());        // hq = --model flag value, YG() = default model function

// Step 2: Gate 1 — check --advisor flag
if (Nb()) {
    let v8 = D.advisor;          // D.advisor = --advisor CLI flag value
    if (v8) {
        N("[AdvisorTool] --advisor " + v8);
        if (!WyH(y9)) {
            process.stderr.write(red("Error: The model \"" + y9 + "\" does not support the advisor tool."));
            process.exit(1);     // HARD EXIT — no fallback
        }
    }
}

// Step 3: Read advisor from settings (no --advisor flag needed)
let L3 = v8 ?? WIK();           // WIK() reads P6().advisorModel with NO WyH check
// Note: WIK only checks Nb(), not WyH — settings path bypasses Gate 1

// Step 4: Include advisor in session config
let config = {
    model: y9,
    // ... other config ...
    ...Nb() && L3 && {advisorModel: L3}   // advisorModel sent to API if Nb() && L3
};
```

**Two independent gates:**
- **Gate 1 (startup)**: Only fires when `--advisor` CLI flag is used. `WyH(baseModel)` → `process.exit(1)` if false. Can be bypassed by using settings instead of `--advisor` flag.
- **Gate 2 (per-query)**: ALWAYS fires via `PIK()`. Cannot be bypassed by configuration. This is why all config-level approaches fail.

---

## 5. Per-Query Flow

```javascript
// Step 1: Resolve advisor for this query
let D = O ? PIK(A.advisorModel, A.model) : void 0;
// O = some condition (likely "is agentic query")
// PIK checks WyH(A.model) — Gate 2, runs on EVERY query

// Step 2: Build tool schemas
let S = [...A.extraToolSchemas ?? []];
if (D) {
    S.push({
        type: "advisor_20260301",        // API tool type identifier
        name: "advisor",                  // tool name the model calls
        model: D                          // resolved advisor model ID
    });
}
let F = [...V, ...S];  // merge with other tools

// Step 3: Build API request with advisor in tools array
let request = {
    model: u0(A.model),       // base model sent to API
    tools: F,                 // includes advisor tool if D was set
    // ... messages, system prompt, etc.
    ...D && {advisorModel: D} // also sent as top-level field
};
```

**Silent failure mode**: When advisor is blocked by Gate 2, `PIK` just returns `void` (undefined). No error, no exception, no user notification. The advisor tool is simply omitted from the tools array. The base model runs as normal, just without advisor capability.

---

## 6. Built-In Advisor System Prompt & Invocation Control

### Hardcoded System Prompt (Extracted from Binary)

When `advisorModel` is set, the CLI injects the following system prompt into every session. This text is **hardcoded in the binary** — it cannot be overridden, suppressed, or modified via settings, env vars, or SDK parameters.

```
# Advisor Tool

You have access to an `advisor` tool backed by a stronger reviewer model.
It takes NO parameters -- when you call advisor(), your entire conversation
history is automatically forwarded. They see the task, every tool call
you've made, every result you've seen.

Call advisor BEFORE substantive work -- before writing, before committing
to an interpretation, before building on an assumption. If the task requires
orientation first (finding files, fetching a source, seeing what's there),
do that, then call advisor. Orientation is not substantive work. Writing,
editing, and declaring an answer are.

Also call advisor:
- When you believe the task is complete. BEFORE this call, make your
  deliverable durable: write the file, save the result, commit the change.
  The advisor call takes time; if the session ends during it, a durable
  result persists and an unwritten one doesn't.
- When stuck -- errors recurring, approach not converging, results that
  don't fit.
- When considering a change of approach.

On tasks longer than a few steps, call advisor at least once before
committing to an approach and once before declaring done. On short
reactive tasks where the next action is dictated by tool output you just
read, you don't need to keep calling -- the advisor adds most of its
value on the first call, before the approach crystallizes.

Give the advice serious weight. If you follow a step and it fails
empirically, or you have primary-source evidence that contradicts a
specific claim (the file says X, the paper states Y), adapt. A passing
self-test is not evidence the advice is wrong -- it's evidence your test
doesn't check what the advice is checking.

If you've already retrieved data pointing one way and the advisor points
another: don't silently switch. Surface the conflict in one more advisor
call -- "I found X, you suggest Y, which constraint breaks the tie?"
The advisor saw your evidence but may have underweighted it; a reconcile
call is cheaper than committing to the wrong branch.
```

### Implications for Conditional Advisor Usage

The built-in prompt aggressively pushes the base model to call the advisor early and often:

| Built-in instruction | Effect |
|---|---|
| "Call BEFORE substantive work" | Advisor invoked before any writing/editing/interpreting |
| "Call when task is complete" | Advisor invoked as verification step at the end |
| "Call when stuck" | Advisor invoked on errors or non-convergence |
| "At least once before committing to an approach" | Minimum 1 call per multi-step task |
| "At least once before declaring done" | Minimum 1 call at completion |

**This means advisor invocation is all-or-nothing at the session level.** When `advisorModel` is set, the base model will typically call the advisor 1-3 times per session regardless of task complexity, driven by the built-in prompt. There is no "advisor on standby, call only when needed" mode.

### Can Custom Prompts Override the Built-In Instructions?

**Not reliably.** The built-in advisor prompt is injected as a system-level instruction at higher priority than user prompts. If you add a user-level instruction like "only call advisor when extracted values change by >10%", the model sees two conflicting instructions:

1. **System prompt** (high priority): "Call advisor BEFORE substantive work"
2. **User prompt** (lower priority): "Only call advisor when values change"

The system prompt generally wins. The model may sometimes follow the user instruction, but behavior is inconsistent and unpredictable.

### Practical Control Pattern

Since within-session advisor frequency cannot be reliably controlled, the decision must be made **before the session starts** in the Python orchestrator:

```
advisor ON  → built-in prompt drives 1-3 advisor calls → ~$0.40/session
advisor OFF → no advisor tool in array, no calls possible → ~$0.01/session
```

There is no middle ground without a second binary patch to replace the built-in prompt text. The orchestrator decides per-task whether the cost of advisor is justified.

### Theoretical: Patching the Built-In Prompt

The advisor system prompt could be replaced via a second binary patch (same technique as the WyH patch — find the string, overwrite with same-length custom text). This would allow custom invocation instructions like "only consult the advisor when you detect anomalies." **Not implemented** — the current all-or-nothing session-level control is sufficient for production use.

---

## 7. Valid Configurations (Unpatched)

| Base Model | Advisor Model | Works? | Reason |
|------------|---------------|--------|--------|
| haiku      | any           | **NO** | `WyH()` blocks — base model must contain `opus-4-6` or `sonnet-4-6` |
| sonnet     | sonnet        | YES    | Tested |
| sonnet     | opus          | YES    | Tested |
| opus       | sonnet        | YES    | Binary analysis |
| opus       | opus          | YES    | Tested |

---

## 8. Settings Priority & Per-Session SDK Control

```
User settings (~/.claude/settings.json)  >  --settings overlay  >  Project settings (.claude/settings.json)
```

**Critical finding**: If `advisorModel` exists in user settings, `--settings` overlay CANNOT override it. User settings always win. This means:
- **To enable per-session control**: REMOVE `advisorModel` from `~/.claude/settings.json`
- **To use a fixed advisor for everything**: SET `advisorModel` in `~/.claude/settings.json`

### How to Enable Per-Session Advisor in SDK

**Prerequisites:**

1. **Remove `advisorModel` from `~/.claude/settings.json`** — if present, it overrides ALL overlays
2. **Remove `advisorModel` from `.claude/settings.json`** — same reason
3. **Base model must be `sonnet` or `opus`** — haiku blocked by `WyH()` gate (unless binary is patched — see §13)
4. **Do NOT set `CLAUDE_CODE_DISABLE_ADVISOR_TOOL`** env var
5. **Do NOT set `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`** env var

**SDK invocation:**
```python
options = ClaudeAgentOptions(
    cli_path="/home/faisal/.local/bin/claude",
    setting_sources=["user", "project"],
    cwd=PROJECT_DIR,
    permission_mode="bypassPermissions",
    model="sonnet",                                    # base model (sonnet or opus ONLY)
    settings='{"advisorModel": "opus"}',               # per-session advisor
    max_turns=MAX_TURNS,
    max_budget_usd=MAX_BUDGET_USD,
)
```

**How `settings=` works** (from SDK source, `subprocess_cli.py:112-164`):
```
ClaudeAgentOptions(settings='{"advisorModel":"opus"}')
    → _build_settings_value() merges sandbox if present
    → _build_command() → cmd.extend(["--settings", '{"advisorModel":"opus"}'])
    → claude -p --settings '{"advisorModel":"opus"}'
```
The `--settings` flag applies as an overlay on top of loaded settings files.

**SDK `extra_args`** (from SDK source, `subprocess_cli.py:292-298`):
```python
# extra_args allows passing arbitrary CLI flags:
extra_args: dict[str, str | None] = field(default_factory=dict)
# Example: extra_args={"advisor": "opus"} → cmd.extend(["--advisor", "opus"])
# WARNING: --advisor flag triggers Gate 1 WyH check at startup — will exit(1) for haiku
```

---

## 9. K8s hostPath Implications

```
┌─────────────────────────────────────────────────────────────────┐
│                    minisforum (Host)                             │
│                                                                 │
│  ~/.claude/settings.json  ◄── SHARED via hostPath               │
│  │  MUST NOT contain "advisorModel"                             │
│  │  (would override all SDK overlays across all pods)           │
│                                                                 │
│  ┌──── Pod A ────┐  ┌──── Pod B ────┐  ┌──── Pod C ────┐      │
│  │ SDK: model=   │  │ SDK: model=   │  │ SDK: model=   │      │
│  │   sonnet      │  │   sonnet      │  │   opus        │      │
│  │ settings=     │  │ settings=     │  │ settings=     │      │
│  │   advisor=    │  │   advisor=    │  │   advisor=    │      │
│  │   opus        │  │   sonnet      │  │   opus        │      │
│  │               │  │               │  │               │      │
│  │ → subprocess  │  │ → subprocess  │  │ → subprocess  │      │
│  │   --model     │  │   --model     │  │   --model     │      │
│  │   sonnet      │  │   sonnet      │  │   opus        │      │
│  │   --settings  │  │   --settings  │  │   --settings  │      │
│  │   advisor=    │  │   advisor=    │  │   advisor=    │      │
│  │   opus        │  │   sonnet      │  │   opus        │      │
│  └───────────────┘  └───────────────┘  └───────────────┘      │
│                                                                 │
│  ✅ Each pod gets independent advisor — no cross-contamination  │
│  ✅ settings.json never mutated by any session                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. API vs CLI Discrepancy

The raw Anthropic API (`advisor_20260301` tool type) **officially supports haiku** as advisor executor. This is documented in:
- Anthropic API docs: haiku listed in valid executor/advisor pairings table
- Anthropic blog: *"The advisor strategy also works with Haiku as the executor"*
- API tool type: `advisor_20260301` (updated from `advisor_20250301`)

Claude Code CLI adds a client-side gate (`WyH()`) that restricts advisor to `opus-4-6` and `sonnet-4-6` base models only. This is a **product decision**, not a technical limitation. The restriction can be bypassed via binary patching (see §13).

---

## 11. Feature Flag: `tengu_sage_compass2`

The advisor is gated behind a server-side GrowthBook/Statsig feature flag called `tengu_sage_compass2`. This flag:
- Is fetched from Anthropic's servers at session start
- Cannot be overridden locally (no env var, no settings)
- Must have `.enabled === true` for ANY advisor functionality
- Is checked via `R$("tengu_sage_compass2", {}).enabled` inside `Nb()`
- A companion flag `tengu_advisor_command` tracks `/advisor` slash command usage

**If Anthropic disables this flag, ALL advisor functionality stops** — including the binary-patched haiku approach.

---

## 12. ANTHROPIC_BASE_URL Catch-22

A common instinct is to use a local proxy via `ANTHROPIC_BASE_URL` to intercept and modify API requests. This **does not work** because of the `jw()` function:

```javascript
// jw() determines if the API source is "firstParty" (Anthropic direct)
function jw() {
    let H = process.env.ANTHROPIC_BASE_URL;
    if (!H) return true;                    // no override → firstParty
    let $ = new URL(H).host;
    return ["api.anthropic.com"].includes($) // only exact match on api.anthropic.com
}
```

If `ANTHROPIC_BASE_URL` points to anything other than `api.anthropic.com`:
- `jw()` returns false → `nq() !== "firstParty"` → `Nb()` returns false → **advisor disabled entirely**
- This kills the advisor before WyH even runs
- Setting `CLAUDE_CODE_API_BASE_URL` doesn't help — it only affects `GK7()` (internal API), not the Anthropic SDK client constructor which reads `ANTHROPIC_BASE_URL` independently

### HTTPS_PROXY Alternative (Investigated, Not Implemented)

`HTTPS_PROXY` could intercept API traffic without changing `ANTHROPIC_BASE_URL` (so `jw()` stays true). However:
- Requires TLS MITM (mitmproxy + CA cert)
- Requires `NODE_EXTRA_CA_CERTS` for the CLI to trust the MITM CA
- More complex than binary patching for the same result
- The CLI binary does recognize `HTTPS_PROXY` and `https_proxy` env vars

---

## 13. Haiku Binary Patch Bypass

### Problem

Claude Code CLI blocks haiku from using the advisor tool via a hardcoded client-side gate function `WyH()`. The Anthropic API fully supports haiku+advisor (`advisor_20260301` tool type) — this is a CLI-only restriction, confirmed by Anthropic's own API documentation and blog.

```javascript
// Original WyH function (two identical copies in the binary)
function WyH(H) {
    let $ = H.toLowerCase();
    return $.includes("opus-4-6") || $.includes("sonnet-4-6") || !1
}
```

WyH is checked at two gates:
- **Gate 1 (startup)**: `--advisor` flag → `WyH(baseModel)` → `process.exit(1)` if false
- **Gate 2 (per-query)**: `PIK(advisorModel, baseModel)` → `WyH(baseModel)` → skip advisor if false

Both gates are **independently blocking** — bypassing Gate 1 via the settings path (`WIK()` reads `advisorModel` from settings without a WyH check) still fails at Gate 2 (PIK checks WyH per-query).

### Solution: Binary String Patch

Replace `"opus-4-6"` (8 bytes) with `"aiku-4-5"` (8 bytes) at the WyH function's first check. Same byte length — no binary structure changes. No size delta — clean in-place patch.

```
BEFORE: $.includes("opus-4-6") || $.includes("sonnet-4-6")
AFTER:  $.includes("aiku-4-5") || $.includes("sonnet-4-6")
```

`"claude-haiku-4-5-20251001".includes("aiku-4-5")` → **TRUE**

Two occurrences of WyH in the v2.1.100 binary (likely two copies of the same bundled JS module):
- **Offset 113767725** (first copy)
- **Offset 224360229** (second copy)

Both must be patched. The adjacent `peH` function (advisor model gate) is NOT modified — advisor models are still restricted to opus and sonnet, which is correct.

### Why "aiku-4-5" Specifically

| Candidate | Bytes | Same length as "opus-4-6"? | Matches haiku models? | Matches other models? |
|-----------|-------|---------------------------|-----------------------|-----------------------|
| `opus-4-6` | 8 | — (original) | NO | opus only |
| `aiku-4-5` | 8 | YES ✓ | YES ✓ (`claude-haiku-4-5-20251001`) | NO ✓ |
| `haiku-4-5` | 9 | NO ✗ (would shift offsets) | — | — |
| `claude-` | 7 | NO ✗ | — | — |
| `aiku-4-` | 7 | NO ✗ | — | — |

`"aiku-4-5"` is the unique 8-byte substring of haiku model IDs that doesn't collide with any other model family.

### Binary Context (verified via `dd`)

```
dd if=binary bs=1 skip=113767660 count=200:

...!1}function WyH(H){let $=H.toLowerCase();return $.includes("opus-4-6")||
$.includes("sonnet-4-6")||!1}function peH(H){let $=H.toLowerCase();return
$.includes("opus-4-6")||$.includes("sonnet-4-6")||...
```

After patch:
```
...!1}function WyH(H){let $=H.toLowerCase();return $.includes("aiku-4-5")||
$.includes("sonnet-4-6")||!1}function peH(H){let $=H.toLowerCase();return
$.includes("opus-4-6")||$.includes("sonnet-4-6")||...
                  ↑ peH unchanged — advisor model still restricted to opus/sonnet
```

### What the Patch Achieves

| Check | Before Patch | After Patch |
|-------|-------------|-------------|
| `WyH("claude-haiku-4-5-20251001")` | `false` (BLOCKED) | `true` (PASS — "aiku-4-5" found) |
| `WyH("claude-sonnet-4-6")` | `true` | `true` (second check "sonnet-4-6" still works) |
| `WyH("claude-opus-4-6")` | `true` | `false` (opus loses advisor — acceptable trade-off) |
| `peH(any)` | unchanged | unchanged (not patched) |

---

## 14. 10 Failed Approaches (Exhaustive)

Each approach was investigated through binary analysis AND empirical testing. These are documented as a record of the solution space — every configuration-level approach fails because the resolved model string is used for BOTH the WyH check AND the API request, and there's no way to have one string for the check and another for the API.

### 1. `modelOverrides` setting
**Theory**: Map haiku's model ID to a string containing "opus-4-6" or "sonnet-4-6".
**Why it fails**: `modelOverrides` is applied via `s1q()` BEFORE `Z_()` resolves the model → WyH checks the RESOLVED result. If you set `modelOverrides: {"claude-haiku-4-5-20251001": "fake-opus-4-6"}`, WyH sees "fake-opus-4-6" and passes, but the API request is sent with `model: "fake-opus-4-6"` which doesn't exist → API returns 404.
**Root cause**: modelOverrides changes what's sent to the API, not just what's checked locally.

### 2. `ANTHROPIC_DEFAULT_*_MODEL` env vars
**Theory**: Set `ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-sonnet-4-6` so "haiku" resolves to sonnet's model ID.
**Why it fails**: The env var IS checked first by `DN()`. If set, `Z_("haiku")` returns "claude-sonnet-4-6". WyH passes. But then you'd actually be running SONNET, not haiku.
**Root cause**: The resolved model ID is used for BOTH the WyH check AND the API request.

### 3. `ANTHROPIC_CUSTOM_MODEL_OPTION`
**Theory**: Set to a haiku-like model ID that contains "sonnet-4-6" to pass WyH.
**Why it fails**: Makes `URH()` return `{valid: true}` (skips model VALIDATION). But WyH is a SEPARATE check. Tested: `"claude-haiku-4-5-sonnet-4-6-proxy"` → WyH passes → but API rejects the model ID: *"There's an issue with the selected model... It may not exist or you may not have access to it."*
**Root cause**: Validation bypass ≠ WyH bypass ≠ API acceptance.

### 4. `ANTHROPIC_DEFAULT_*_MODEL_SUPPORTED_CAPABILITIES` env vars
**Theory**: Declare haiku has advisor capability.
**Why it fails**: `d6H()` returns EARLY if `NY() === "firstParty"`. Since we use Anthropic direct, these env vars are completely ignored. They're only for 3P providers (Bedrock, Vertex). And even on 3P, WyH doesn't check capabilities.
**Root cause**: Capabilities env vars are 3P-only and WyH ignores capabilities entirely.

### 5. Tricky model strings
**Theory**: Craft `"claude-haiku-4-5-sonnet-4-6-proxy"` containing "sonnet-4-6".
**Why it fails**: WyH passes! But the string is sent to the API, which rejects it — not a valid model ID.
**Tested**: `claude -p --model "claude-haiku-4-5-sonnet-4-6-proxy"` → `is_error: True`
**Root cause**: API server-side validation of model IDs is strict.

### 6. Settings `advisorModel` (WIK bypass)
**Theory**: Set `advisorModel` in settings instead of `--advisor` flag. `WIK()` reads from settings WITHOUT a WyH check.
**Why it partially works**: WIK() bypasses Gate 1 (startup). CLI starts successfully. Session config includes `advisorModel`.
**Why it ultimately fails**: Gate 2 (`PIK`) runs on EVERY query. `PIK(A.advisorModel, A.model)` calls `WyH(A.model)` → haiku fails → advisor silently skipped.
**Root cause**: Two independent gates. Bypassing one doesn't help.

### 7. `ANTHROPIC_BASE_URL` to local proxy
**Theory**: Redirect API traffic through a local proxy that changes model field.
**Why it fails**: `jw()` checks `ANTHROPIC_BASE_URL`. Non-`api.anthropic.com` → `jw()` false → `Nb()` false → ALL advisor disabled. Advisor killed before WyH even runs.
**Root cause**: firstParty check in Nb() prevents any proxy approach via ANTHROPIC_BASE_URL.

### 8. `CLAUDE_CODE_API_BASE_URL`
**Theory**: Use this env var instead of `ANTHROPIC_BASE_URL` to redirect without affecting `jw()`.
**Why it fails**: Only affects `GK7()` (Claude Code's internal file API). The Anthropic SDK client reads `ANTHROPIC_BASE_URL` independently via `XpH("ANTHROPIC_BASE_URL")`.
**Root cause**: Two separate base URL paths — internal API vs Anthropic SDK client.

### 9. `set_model()` mid-session (SDK control protocol)
**Theory**: Start with sonnet (passes WyH at startup), then `set_model("haiku")` mid-session.
**Why it fails**: `PIK()` checks `A.model` on EVERY query. When model changes to haiku, `A.model` becomes haiku. Next query: `WyH("claude-haiku-4-5-20251001")` → false → advisor silently skipped.
**Root cause**: Gate 2 is per-query, not per-session.

### 10. `ANTHROPIC_SMALL_FAST_MODEL`
**Theory**: This env var might bypass the standard model resolution pipeline.
**Why it fails**: Just the highest-priority env var for haiku resolution: `haiku: {envVarPriority: ["ANTHROPIC_SMALL_FAST_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL"]}`. Feeds into the same `DN()` → `Z_()` pipeline. Resolved string still checked by WyH.
**Root cause**: Just an alias in the resolution priority list, not a bypass mechanism.

### Summary of Why Config-Level Approaches Are Fundamentally Impossible

The architectural constraint is:
```
The SAME model string is used for:
  1. The WyH() client-side gate check
  2. The API request model field

There is no configuration that separates these two uses.
```

To make WyH pass for haiku, you'd need the string to contain "opus-4-6" or "sonnet-4-6". But that same string gets sent to the API, which only accepts real model IDs. You cannot have a string that both passes WyH and is a valid haiku model ID — unless you change WyH itself, which is what the binary patch does.

---

## 15. Test Results

All tests performed on 2026-04-10, v2.1.100.

```
T1: Patched binary version check        → PASS (2.1.100, not corrupted)
T2: Haiku + opus advisor (CLI)          → PASS (both models in modelUsage)
    modelUsage: haiku=$0.11, opus=$0.41
T3: Complex reasoning via advisor       → PASS (mislabeled boxes puzzle — correct answer)
    modelUsage: haiku=$0.04, opus=$0.43
T4: Haiku + opus advisor (SDK)          → PASS (iterations: message→advisor_message→message)
    Total cost: $0.39 (confirms opus pricing — haiku alone would be ~$0.01)
T5: Sonnet regression (unchanged)       → PASS (sonnet still matches "sonnet-4-6")
T6: Opus as base (advisor disabled)     → PASS (works without advisor — acceptable)
```

Full test output: `earnings-analysis/test-outputs/test-haiku-advisor-bypass.txt`

---

## 16. SDK Iteration Proof

From `ResultMessage.usage.iterations` (T4 test):

```json
[
  {
    "type": "message",
    "input_tokens": 10, "output_tokens": 120,
    "cache_creation_input_tokens": 9592
  },
  {
    "type": "advisor_message",
    "model": "claude-opus-4-6",
    "input_tokens": 72678, "output_tokens": 93
  },
  {
    "type": "message",
    "input_tokens": 1, "output_tokens": 39,
    "cache_read_input_tokens": 72028
  }
]
```

**Flow**: haiku processes prompt → calls advisor tool → opus provides deep reasoning → haiku synthesizes final answer.

**SDK stream format**: Iterations appear in `msg.usage.iterations` (array), NOT in a top-level `modelUsage` field. Each iteration has a `type` field: `"message"` for base model, `"advisor_message"` for advisor.

---

## 17. Production Usage

### SDK Invocation (Patched Binary)

```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    cli_path="/home/faisal/.local/share/claude/versions/2.1.100-haiku-patched",
    model="haiku",
    settings='{"advisorModel": "opus"}',
    setting_sources=["user", "project"],
    cwd=PROJECT_DIR,
    permission_mode="bypassPermissions",
    max_turns=MAX_TURNS,
    max_budget_usd=MAX_BUDGET_USD,
)

async for msg in query(prompt="your prompt here", options=options):
    # msg.type: "message" (haiku) or includes advisor_message in iterations
    ...
```

### CLI Invocation (Patched Binary)

```bash
/home/faisal/.local/share/claude/versions/2.1.100-haiku-patched \
    -p --model haiku \
    --settings '{"advisorModel":"opus"}' \
    --max-turns 5 \
    "your prompt here"
```

### K8s Extraction Pipeline

- Mount patched binary via hostPath (same as current setup)
- Set `cli_path` in `ClaudeAgentOptions` to patched binary path
- Per-session advisor via `settings='{"advisorModel": "opus"}'`

### Cost Comparison (typical extraction query)

| Configuration | Cost/query | Notes |
|---|---|---|
| sonnet + opus advisor | ~$0.50 | Current default |
| haiku + opus advisor | ~$0.40 | Haiku base cheaper, advisor cost same |
| haiku without advisor | ~$0.01 | No deep reasoning |

Cost reduction comes from haiku base ($0.80/1M in, $4/1M out) vs sonnet ($3/1M in, $15/1M out). Advisor cost is per-invocation at opus pricing regardless of base model.

---

## 18. Valid Configurations (Patched)

| Base Model | Advisor Model | Works? | Notes |
|---|---|---|---|
| haiku | opus | **YES** | Binary patch enables this |
| haiku | sonnet | **YES** | Binary patch enables this |
| sonnet | opus | YES | Unchanged (second WyH check "sonnet-4-6") |
| sonnet | sonnet | YES | Unchanged |
| opus | any | NO* | *Runs fine, just no advisor (opus doesn't need one) |

The patched binary is a **superset** — it supports every useful model+advisor combination. The only "loss" is opus-as-base losing advisor, which is irrelevant since opus IS the most capable model.

---

## 19. Multi-Task Model Switching

The patched binary supports all model+advisor combinations via Python parameters alone — no binary changes, no config changes, no restarts needed.

### How It Works

```
                  ONE patched binary on hostPath
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     Guidance Task    Prediction Task  Monitoring Task
            │              │              │
  model="sonnet"    model="haiku"   model="haiku"
  advisor="opus"    advisor="opus"  advisor="sonnet"
```

Each task is a separate SDK `query()` call with its own `ClaudeAgentOptions`. The `model` and `settings` parameters are per-session — completely independent. No global state is shared between sessions.

### Example: Three Tasks, Three Configurations

```python
# Task 1: Guidance extraction (high quality needed)
guidance_opts = ClaudeAgentOptions(
    cli_path=PATCHED_BINARY,
    model="sonnet",
    settings='{"advisorModel": "opus"}',
    ...
)

# Task 2: Prediction (cost-sensitive, still needs reasoning)
prediction_opts = ClaudeAgentOptions(
    cli_path=PATCHED_BINARY,
    model="haiku",
    settings='{"advisorModel": "opus"}',
    ...
)

# Task 3: Monitoring (cost-sensitive, lighter reasoning)
monitoring_opts = ClaudeAgentOptions(
    cli_path=PATCHED_BINARY,
    model="haiku",
    settings='{"advisorModel": "sonnet"}',
    ...
)
```

**Key point**: The binary is never changed. Only Python parameters differ. This is exactly the same pattern already used for the guidance extraction pipeline — just with more model options now available.

---

## 20. Auto-Update Impact & Re-Patching

Claude Code auto-updates overwrite the binary at `~/.local/share/claude/versions/<version>`. When a new version is installed:

1. The patched binary is **not overwritten** (it has a different filename: `*-haiku-patched`)
2. But the `claude` symlink now points to the NEW version
3. The SDK's `cli_path` must point to either:
   - The patched binary (won't get new features/fixes until re-patched)
   - Or the new version (must be re-patched first)

### Re-Patching Procedure

```bash
# After claude update:
./scripts/patch_claude_haiku_advisor.sh
# Script auto-discovers the latest version and patches it
# WyH offsets may change — script uses grep to find them dynamically
```

### Detection and Automation Options

| Strategy | How | Pros | Cons |
|---|---|---|---|
| Manual re-patch | Run script after each update | Simple | Easy to forget |
| Cron/systemd timer | `*/5 * * * * /path/to/patch_claude_haiku_advisor.sh` | Automatic | Patches may fire at bad time |
| Pre-task check | Python wrapper checks binary before SDK call | Reliable | Adds startup latency |
| Pin auto-updates | `"autoUpdatesChannel": "manual"` | No surprise changes | Miss bug fixes |

Current setting: `"autoUpdatesChannel": "latest"` — patches survive until the next update occurs.

### What Happens If You Forget to Re-Patch

The advisor **silently stops working**. No error, no crash. The CLI runs normally, haiku processes prompts, but advisor is just... absent. The only symptom is:
- `modelUsage` shows only haiku tokens (no opus/sonnet)
- Quality of complex reasoning degrades
- Cost drops unexpectedly (haiku alone is ~$0.01/query vs ~$0.40 with advisor)

This is the most dangerous failure mode — silent quality degradation that's hard to notice without monitoring.

---

## 21. Patch Script Reference

**Location**: `scripts/patch_claude_haiku_advisor.sh`

### What It Does (Step by Step)

1. **Finds the latest Claude Code binary** in `~/.local/share/claude/versions/` (sorts by modification time, picks newest matching `X.Y.Z` pattern)
2. **Searches for WyH function** via `grep -obUaP 'WyH\(H\)\{let \$=H\.toLowerCase\(\);return \$\.includes\("opus-4-6"\)'` on the binary
3. **Checks for already-patched state** — if the grep finds `"aiku-4-5"` instead, exits cleanly
4. **Creates a backup** (`<version>.original`) if one doesn't exist
5. **Copies to a new file** (`<version>-haiku-patched`) — avoids "Text file busy" error on running binary
6. **For each WyH occurrence** (typically 2):
   - Calculates byte offset: pattern start + 48 bytes = position of `"opus-4-6"` string
   - Verifies 8 bytes at that offset are literally `opus-4-6` (safety check)
   - Writes `aiku-4-5` at that offset via `dd conv=notrunc`
7. **Sets executable permission** on the patched copy
8. **Verifies the patch** by reading back the patched area
9. **Prints usage instructions** for CLI and SDK

### The "+48 Offset" Explained

The grep pattern finds the start of `WyH(H){let $=H.toLowerCase();return $.includes("`:
```
W y H ( H ) { l e t   $  =  H  .  t  o  L  o  w  e  r  C  a  s  e  (  )  ;  r  e  t  u  r  n     $  .  i  n  c  l  u  d  e  s  (  "  o  p  u  s  -  4  -  6
0 1 2 3 4 5 6 7 8 9 ...                                                                                                                      48 49 50 51 52 53 54 55
```
Position 48 is where `opus-4-6` starts. The `dd` writes 8 bytes (`aiku-4-5`) at `seek=offset+48`.

### Usage

```bash
./scripts/patch_claude_haiku_advisor.sh          # patch current CLI version
./scripts/patch_claude_haiku_advisor.sh --revert  # restore original binary
```

Idempotent: running on an already-patched binary detects it and exits cleanly.

---

## 22. Risks, Gotchas & Caveats

### Risk Matrix

| Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|
| Silent advisor failure | **HIGH** | Medium | Monitor `modelUsage` for advisor_message iterations |
| Forgot to re-patch after update | Medium | **HIGH** | Cron job or pre-task check |
| Cost surprise (opus advisor) | Medium | Low | `max_budget_usd` per-session cap |
| Binary integrity broken | Low | Low | Backup + version check in script |
| Anthropic disables feature flag | **HIGH** | Low | None — server-side kill switch |
| API removes haiku+advisor support | **HIGH** | Low | Monitor API changelog |
| ToS violation | Unknown | Unknown | See analysis below |
| Haiku doesn't call advisor naturally | Medium | Medium | Test with specific workload |

### Detailed Risk Analysis

#### 1. Silent Advisor Failure (Most Dangerous)
When advisor is blocked (unpatched binary, feature flag disabled, etc.), there is **no error, no warning, no log message visible to the user**. `PIK()` returns `void`, the advisor tool is simply omitted from the tools array, and the base model runs without it. Symptoms:
- Quality drops on complex reasoning tasks
- Cost drops (no advisor tokens)
- `modelUsage` shows only base model

**Mitigation**: After each SDK call, check `msg.usage.iterations` for `type: "advisor_message"`. If absent and advisor was expected, flag it.

#### 2. Forgot to Re-Patch After Update
Auto-updates install a new binary → `claude` symlink moves → old patched binary still exists but isn't used → SDK calls with `cli_path` pointing to old version work but miss new features. OR if `cli_path` follows the symlink → new unpatched binary → advisor silently fails.

**Mitigation**: Point `cli_path` to the `-haiku-patched` file (stable). Run patch script after updates. Consider a pre-task wrapper:
```python
import subprocess
result = subprocess.run([cli_path, "--version"], capture_output=True, text=True)
# Compare against expected version
```

#### 3. Cost Surprise
Advisor calls invoke opus/sonnet on every invocation — this adds $0.30-0.40 per query on top of the base model cost. If a task makes many advisor calls, costs accumulate.

**Mitigation**: Always set `max_budget_usd` in `ClaudeAgentOptions`. Monitor total spend.

#### 4. Binary Integrity
The `dd` patch modifies 16 bytes total (8 bytes × 2 occurrences). If the offset calculation is wrong, it could corrupt adjacent JavaScript, causing crashes or undefined behavior.

**Mitigation**: The script verifies the 8 bytes at the target offset are literally `opus-4-6` before writing. If they aren't, it aborts. The backup file allows full restoration.

#### 5. Anthropic Feature Flag Kill Switch
The `tengu_sage_compass2` GrowthBook flag is checked by `Nb()` before any advisor logic runs. Anthropic can disable this flag at any time. If disabled:
- ALL advisor functionality stops globally
- No local workaround possible (flag is fetched from Anthropic's servers)
- Binary patch becomes irrelevant

**Mitigation**: None. Accept this as an external dependency.

#### 6. API Changes
Anthropic could change the advisor API (e.g., remove `advisor_20260301` tool type, add server-side model restrictions, change model IDs). The binary patch only bypasses the client-side check — server-side changes are uncontrollable.

**Mitigation**: Monitor Anthropic API changelog and blog.

#### 7. Terms of Service
Binary modification of the Claude Code CLI may violate Anthropic's Terms of Service. The patch:
- Does NOT circumvent rate limits or billing
- Does NOT change what API calls are made (haiku+advisor is officially supported)
- Only removes a CLIENT-SIDE restriction that contradicts the API's official support
- Is functionally equivalent to calling the API directly with haiku+advisor

**Assessment**: Low risk given the API officially supports the combination. The CLI restriction appears to be a product decision (possibly for UX reasons) rather than a technical or policy constraint. However, this is not legal advice.

#### 8. Haiku Advisor Quality
Haiku's training may not optimize for advisor tool usage as well as sonnet/opus. In testing, haiku DID call the advisor correctly on all test cases, but:
- It may not know when to call vs. not call the advisor as well as larger models
- Complex multi-step reasoning might be less effective with haiku as orchestrator
- Extraction-specific prompts should be tested before production deployment

**Mitigation**: Run A/B comparisons on a representative sample of extraction tasks before switching production from sonnet to haiku base.

#### 9. Stale Binary
If you keep `cli_path` pointed at a patched binary while the CLI updates multiple times, you accumulate technical debt — missing bug fixes, security patches, new features.

**Mitigation**: Re-patch after every update. The script is fast (<1 second) and idempotent.

#### 10. WyH Function Renamed/Refactored
Future CLI versions could rename WyH, change its structure, or implement the gate differently. The patch script's grep pattern (`WyH\(H\)\{let \$=H\.toLowerCase\(\);return \$\.includes\("opus-4-6"\)`) would fail to find it.

**Mitigation**: If the script fails, re-analyze the binary:
```bash
strings /path/to/binary | grep -oP '.{0,30}includes.*opus-4-6.{0,30}'
```
This will find any function that does `.includes("opus-4-6")` regardless of the function name.

---

## 23. Research Agent Findings

Three research agents were deployed to search GitHub, Perplexity, and the binary for alternative approaches:

1. **GitHub research**: No open/closed issues about haiku+advisor in `anthropics/claude-code`. The advisor feature launched April 9, 2026 and is barely discussed. `ANTHROPIC_CUSTOM_MODEL_OPTION` was identified as "most promising" by the agent — but empirically confirmed to fail (approach #3 above).

2. **Perplexity research**: API key expired (401 Unauthorized). No results.

3. **Binary analysis agent**: Correctly identified all gate functions but incorrectly concluded binary patching was "impractical" and that the API would block haiku+advisor. **Disproven empirically** — the API officially supports haiku+advisor and the patch works perfectly.

---

## 24. Files

| File | Purpose |
|---|---|
| `/home/faisal/.local/share/claude/versions/2.1.100-haiku-patched` | Patched binary (v2.1.100) |
| `/home/faisal/.local/share/claude/versions/2.1.100.original` | Backup of unpatched binary |
| `scripts/patch_claude_haiku_advisor.sh` | Auto-patching script (run after each update) |
| `earnings-analysis/test-outputs/test-haiku-advisor-bypass.txt` | Full test results (6 tests, 10 failed approaches) |
| `earnings-analysis/test-outputs/test-sdk-advisor-isolation.txt` | SDK model isolation tests |
| `scripts/test_concurrent_model_isolation.py` | Model isolation test script (7 verdicts) |

### Test Evidence Summary

| Test | Skill/Script | Output File | Verdict |
|---|---|---|---|
| Haiku+advisor bypass (6 tests) | Manual CLI/SDK | `test-haiku-advisor-bypass.txt` | ALL PASS |
| SDK advisor isolation | `test_concurrent_model_isolation.py` | `test-sdk-advisor-isolation.txt` | ALL PASS |
| Interactive /advisor check | Manual | — | CONFIRMED: haiku blocked unpatched |
