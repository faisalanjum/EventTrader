# TMUX CLI Subscription Transport — Implementation Handoff

**Audience:** the bot that will turn this into concise, production-ready code.
**Status:** all claims below are empirically proven on **Claude Code CLI `2.1.144`** (2026-05-18/19), OAuth subscription (no API key). Do **not** re-run the experiments — cite this doc + the evidence files. Only write the production code.

**One-line purpose:** run real interactive Claude via the local `claude` CLI on the user's OAuth subscription (NOT the metered Anthropic API), driven through a tmux session, with optional safe mid-run nudges. Target production path is always `claude` with **NO `-p` / NO `--print` / NO SDK**.

---

## 0. Exact references to prior work (cite these, don't regenerate)

| Finding | Where it lives (durable, in-repo) |
|---|---|
| **Parallelism**: top-level prompt-embed can run sub-agents truly in parallel + the drop-in prompt pattern | `.claude/plans/Infrastructure.md` **line 3687**, section *"EMPIRICAL RETEST — top-level prompt-embed parallelism (2026-05-18, this CLI version)"* (ends just before *"Workarounds for parallel execution:"*) |
| Parallel test rig + raw proof | `.claude/plans/evidence/partest/` → `prompt.txt`, `run.sh`, `verify.py`, `out.json`, `DONE`, `parallel-session-transcript.jsonl` (session `493a0a61-6251-4992-ace1-3357892d4569`) |
| **Session-id pin + transcript path formula + OAuth headless** | `.claude/plans/evidence/partest/final-sessionpin-out.json` (session `a22812aa-cbc4-4285-a90e-31050cf349bd`) |
| **Nudge safety** (queue, no interrupt, no corruption) | This document, §4 — was conversation-only; this file is now the durable record |
| **Sub-agent spawn from interactive tmux** (access + TRUE parallel) | This document, §4b — sessions `d64f0ca5-…` (access) and `f2df9317-…` (parallel, 23.26s overlap) |
| Auth rules (subscription vs API key) | `CLAUDE.md` → "Anthropic API Key Handling"; `.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md` |
| Existing prompt/env code anchors (copy non-transport pieces only) | §8 of this document (exact `file:line` table) |

---

## 1. Two interactive transport profiles (this is the core contract)

There is **one transport, two profiles**. Both profiles launch real interactive Claude inside tmux using `claude` with **NO `-p` / NO `--print`**. Pick by whether the job needs a mid-run nudge/SLA loop.

| Clause | **Profile A — Interactive batch** (no planned nudge) | **Profile B — Interactive nudgeable** |
|---|---|---|
| Invocation | `claude` (NO `-p`); prompt sent after launch via `tmux send-keys` | Same launch; plus queued nudges via `tmux send-keys` |
| Use when | One-shot job with no planned mid-run interaction (historical predictor, learner, guidance) | You must inject messages while it works (live predictor SLA/time updates) |
| Completion signal | job-specific completion predicate: valid `result.json` + component `complete.json` where applicable; then kill/cleanup tmux | same, plus transcript-tail / idle detection for turn boundaries |
| Output capture | canonical artifacts + transcript jsonl; pane scrollback is never canonical | same |
| Nudge | Not planned; still technically possible but should not be used by Profile A jobs | ✅ see §4 |
| Session id | pin with `--session-id <uuid>`; transcript path is deterministic | same |

### Shared clauses (apply to BOTH — state once in code)

1. **Subscription auth, not API:** `unset ANTHROPIC_API_KEY` / `unset ANTHROPIC_AUTH_TOKEN` (and scrub them from any inherited/spawned env) before launch. OAuth creds live in the selected Claude profile home. Adding the key back = silent metered billing. (CLAUDE.md, critical.)
1b. **No programmatic pool path:** target code MUST NOT use `claude -p`, `--print`, `claude_agent_sdk.query`, or direct Anthropic API calls. Those are historical/current-code references only.
2. **CLI path:** use `/home/faisal/.local/bin/claude` explicitly (don't rely on PATH).
3. **cwd is meaningful:** run from a deliberate working dir. It determines (a) which project `.claude/agents` + settings resolve, (b) the transcript directory (see §3 formula). Use a clean/trusted cwd for isolated runs.
4. **Permission mode:** production uses `--permission-mode bypassPermissions` after user-approved launch policy. Without it, per-tool permission prompts can stall unattended workers.
5. **Model pin:** pass `--model claude-opus-4-7` (or the role's model) explicitly; don't inherit a default.
6. **Hard-timeout kill:** wrap with a timeout; on expiry `tmux kill-session -t <name>` AND ensure the child `claude` PID is killed (don't leak subprocesses).
7. **Capture discipline:** canonical outputs are result files + transcript jsonl. Do not rely on tmux pane scrollback for large outputs.

---

## 2. The launch-authorization blocker (DO NOT MISS — this is the real-world gotcha)

The classifier behaves **differently by form** — proven this session:

| Spawn form (agent-issued, via Bash) | Classifier |
|---|---|
| `claude -p … --permission-mode bypassPermissions` (non-interactive autonomous) | ❌ **FORBIDDEN TARGET PATH** — uses programmatic pool / sdk-cli |
| `claude` **interactive in tmux** `… --permission-mode bypassPermissions` | ✅ **ALLOWED** (proven 3×: nudge, agsmoke, agpar — all agent-launched, none blocked) |
| `claude -p` with **no bypass + no tools** (trivial) | ❌ **FORBIDDEN TARGET PATH** even if trivial; do not normalize `-p` in production |

**Contract requirement:** use the **interactive-tmux** form for every production Claude job. The easier `-p` / SDK path is deliberately rejected because it does not use the normal interactive subscription bucket.

---

## 3. Transcript path formula (proven)

```
~/.claude/projects/<CWD_WITH_SLASHES_AS_DASHES>/<session-id>.jsonl
```
Example (proven): cwd `/home/faisal/EventMarketDB` → `~/.claude/projects/-home-faisal-EventMarketDB/a22812aa-cbc4-4285-a90e-31050cf349bd.jsonl`. Leading `/` becomes a leading `-`. With `--session-id <uuid>` the filename is deterministic and known **before** launch — use this instead of scraping.

---

## 4. Nudge sub-protocol (Profile B only) — PROVEN SAFE

**Verdict: SAFE.** Test: a long *model-busy* turn (Claude streaming a 400-line no-tool generation). A nudge injected mid-stream:

- **Queued, did not interrupt.** UI showed the message under the prompt with *"Press up to edit queued messages"*.
- **Task ran to completion intact** — output stayed strictly monotonic 1→400, no restart, no corruption, no merge of nudge text into output.
- **Nudge answered at the NEXT turn boundary**, after the in-flight turn finished (`Acknowledged — safe to proceed.`).

**Rules (hard contract):**
- Send a nudge with **text + Enter only**: `tmux send-keys -t <session> '<message>' Enter`. That's keyboard input → it queues.
- **NEVER** send `Esc` or `C-c` to nudge — those are the interrupt path and WILL abort the running turn.
- Delivery is **next-turn, not real-time.** Fine for "acknowledge when safe / new instruction" style; not for hard real-time interrupts.

---

## 4b. Sub-agent spawning from a top-level tmux run — PROVEN (access + TRUE parallel)

Both proven in **interactive tmux**, top-level (non-fork), repo cwd, bypass on, **agent-launched** (not blocked):

- **Access** (session `d64f0ca5-…`): top-level session spawned `general-purpose` **and** real project DataSubAgent `neo4j-entity` via the `Agent` tool; both returned; bash token echoed back (real execution); `SMOKE_DONE` emitted.
- **TRUE parallel** (session `f2df9317-…`): 4 `general-purpose` agents each `date;sleep25;date`. In-agent epochs: latest START 1779191865.435, earliest END 1779191888.696 → **overlap 23.26s**, wall 26.75s vs ~100s serial. Live pane showed P1‖P2‖P3‖P4 all running at once.

**Key behavior:** the model emits **one spawn per assistant message** (~1s apart), NOT a single-message batch — yet they execute **concurrently** because spawns are non-blocking. So the lever for parallel is **independent self-contained sub-tasks + prompt says "spawn all N, don't wait for any result before issuing the next, collect after"**. Single-message batching is neither achieved nor needed. The `Agent` tool name = the Task/sub-agent spawner. Named DataSubAgents (`neo4j-*`) require **cwd = repo root**; `general-purpose` works from any cwd.

---

## 5. Proven, copy-paste-able command shape (use as the code's backbone)

**Profile A (interactive batch, no planned nudge):**
```bash
SID=$(python3 -c "import uuid;print(uuid.uuid4())")
tmux new-session -d -s <NAME> -x 220 -y 50
tmux send-keys -t <NAME> 'cd <WORKDIR> && unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN && \
  /home/faisal/.local/bin/claude --session-id '"$SID"' --model claude-opus-4-7 \
  --permission-mode bypassPermissions' Enter
# wait until ready, then send the whole job prompt:
tmux send-keys -t <NAME> '<TASK PROMPT>' Enter
# completion: poll job artifacts, e.g. valid result.json + complete.json where applicable.
# transcript: ~/.claude/projects/<cwd-mangled>/$SID.jsonl
# teardown: tmux kill-session -t <NAME>
```

**Profile B (interactive + nudge) — PROVEN safe:**
```bash
tmux new-session -d -s <NAME> -x 220 -y 50
tmux send-keys -t <NAME> 'cd <WORKDIR> && unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN && \
  /home/faisal/.local/bin/claude --session-id <UUID> --model claude-opus-4-7 \
  --permission-mode bypassPermissions' Enter
# ... wait until ready, then send the task:
tmux send-keys -t <NAME> '<TASK PROMPT>' ; tmux send-keys -t <NAME> Enter
# mid-run nudge (safe, queues):
tmux send-keys -t <NAME> 'NUDGE: <message>' ; tmux send-keys -t <NAME> Enter
# observe: tmux capture-pane -p -t <NAME>   AND/OR  the transcript jsonl
# teardown: tmux kill-session -t <NAME>
```
> Billing rule: both profiles are interactive Claude (`CLAUDE_CODE_ENTRYPOINT=cli`). `-p` / `--print` / SDK are forbidden target paths.

**Parallel sub-agents:** see §4b — independent self-contained sub-tasks + "spawn all N, don't wait, collect after". Single-message batching is NOT required/achieved; non-blocking + independence is the lever (also Infrastructure.md:3687).

---

## 6. What the new bot must BUILD (scope — keep it concise)

1. A single transport module exposing both interactive profiles behind one API: `run_interactive_batch(prompt, cwd, model, timeout, completion_predicate)` and `start_interactive(cwd, model) / send_prompt(session, text) / send_nudge(session, text) / read_progress(session)`.
2. Mandatory: env scrub (`ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` removed), explicit CLI path, explicit `--model`, `--session-id` pin, deterministic transcript path derivation (§3), timeout→kill (session + child), artifact validation, transcript capture.
3. A launch path that starts real interactive Claude under tmux; never implement production via `claude -p`, `--print`, SDK, or direct Anthropic API.
4. Nudge API enforces text+Enter only; must refuse to ever send Esc/Ctrl-C.
5. Completion detection: Profile A = job-specific artifact predicate; Profile B = artifact predicate + transcript-tail / idle detection for safe nudge timing.

**Non-goals / out of scope:** real-time interrupt of a running turn; multi-message single-turn batching; anything requiring the metered API key.

---

## 7. Evidence index (all in-repo, durable)

- `.claude/plans/Infrastructure.md:3687` — parallelism finding (authoritative).
- `.claude/plans/evidence/partest/prompt.txt|run.sh|verify.py` — parallel test rig.
- `.claude/plans/evidence/partest/out.json` + `parallel-session-transcript.jsonl` — parallel raw proof (8 spawns, overlapping 25s windows, 49s wall vs 100s+ serial). ⚠️ TRAP: `out.json`'s `.result` text contains the **model's own self-report** claiming "single message / concurrent" — that sentence is **DISPROVEN** (it actually emitted 8 separate assistant messages). Authoritative truth = the transcript + Infrastructure.md:3687 analysis, NOT the model's narration. Never trust model self-reports; parse the transcript.
- `.claude/plans/evidence/partest/final-sessionpin-out.json` — session-id pin + path formula + OAuth headless proof (result `TRANSPORT_OK`, session_id == pinned uuid).
- `.claude/plans/evidence/agent-spawn/access-session-d64f0ca5.jsonl` — interactive-tmux top-level spawned `general-purpose` + `neo4j-entity`, real bash token echoed, `SMOKE_DONE`.
- `.claude/plans/evidence/agent-spawn/parallel-session-f2df9317.jsonl` — 4 sub-agents, in-agent epochs prove 23.26s overlap (TRUE parallel), 1 spawn/msg.
- Nudge proof: §4 of this file (durable record; original interactive session transcript was ephemeral).

---

## 8. Existing code anchors — copy prompts/env guards, replace transport

The existing SDK code is a prompt-construction and env-scrub reference only; do **not** copy its transport. Exact `file:line` (verified 2026-05-19):

| Function | Location | What to copy |
|---|---|---|
| `_load_learner_skill_content()` | `scripts/earnings/earnings_orchestrator.py:3107` | load a SKILL/prompt file as the embed text |
| `_build_learner_prompt(...)` | `scripts/earnings/earnings_orchestrator.py:3118` | assemble `skill_content + INPUTS` into one positional prompt |
| `_run_learner_via_sdk(...)` | `scripts/earnings/earnings_orchestrator.py:3169` | current transport callsite to replace with interactive TMUX |
| `run_learner_via_sdk(...)` | `scripts/earnings/earnings_orchestrator.py:3248` | sync wrapper + existence guards to preserve/rename around the new transport |
| `_sdk_subprocess_env()` | `scripts/earnings/earnings_orchestrator.py:3319` | **env scrub** (strips `ANTHROPIC_API_KEY`) — copy verbatim |
| `_assert_claude_code_oauth_ready()` | `scripts/earnings/earnings_orchestrator.py:3340` | preflight: OAuth creds + cli_path resolution |
| `_build_predictor_prompt / _run_predictor_via_sdk` | `scripts/earnings/earnings_orchestrator.py:3599 / 3615` | predictor prompt builder + current transport callsite to replace |
| `LLMRole` / `as_sdk_kwargs()` / `PREDICTOR` / `LEARNER` | `config/llm_models.py:68 / 112 / 129 / 130` | model/effort/max-turn settings reference; translate into interactive CLI launch/prompt config |

Notes: that code uses the **Claude Agent SDK** (`claude_agent_sdk.query`) which is `claude -p` under the hood. That transport is forbidden in the target. Reuse only prompt assembly, model selection, env-scrub, output-path, validation, and wrapper patterns; replace the actual invocation with §5 interactive TMUX.

---

CLI version of record: **`2.1.144 (Claude Code)`**. Re-validate the contract if the CLI minor version changes (frontmatter/flag behavior is version-sensitive — see Infrastructure.md history).
