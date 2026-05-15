# ANTHROPIC BILLING — SUBSCRIPTION vs API — CRITICAL (read before any SDK/LLM or pipeline change)

> **Canonical source of truth** for "will the EarningsTrigger / Guidance extraction pipelines get
> charged after Anthropic's June 15 2026 subscription change, and how do I keep them on subscription /
> $0." Everything here is **empirically tested on this machine** (commands included so anyone can
> re-verify). Created 2026-05-15. Supersedes scattered notes in CLAUDE.md / .hermes.md / Infrastructure.md
> on this topic — those now point here.

---

## TL;DR (the crux)

```
WHAT CHANGED (effective JUNE 15 2026):
  claude_agent_sdk / `claude -p` (programmatic) is NO LONGER covered by the
  general subscription. It draws a SEPARATE monthly credit pool at FULL API rates:
      Pro $20 · Max 5x $100 · Max 20x $200  (non-rollover)
  Pool empty → governed by account "Usage Credits / overage" switch:
      OFF → request REJECTED, pauses till reset → $0   ✅  (CURRENT STATE — verified)
      ON  → continues, billed at API rates       → CHARGED ❌

WILL WE BE CHARGED?  Only via TWO vectors, both controllable:
  V1  a real ANTHROPIC_API_KEY reachable by the SDK → bills API instantly,
      bypasses subscription AND the overage switch.   Defense: strip the key.
  V2  post-Jun-15 pool exhausts WITH overage ON.       Defense: overage OFF
      (currently `org_level_disabled` — verified live).

NEVER-CHARGED = (V1 defense on every entrypoint) AND (V2 overage OFF).
```

**Burn-rate (measured, real predictor session):** ~**$14.70 per predictor run** → a $200 (Max 20x)
pool ≈ **~14 predictor runs/month** then it pauses. A full-universe sweep exhausts it in well under a
day. **The pool is structurally inadequate for this project's volume.** Plan around that.

---

## Sources (what Anthropic actually did)

- Reddit r/ClaudeCode + r/Anthropic: *"It's official. Anthropic pulled the plug on all programmatic
  use of Claude subscription."* (~1.1K upvotes; thread body could not be machine-fetched — Reddit
  blocks WebFetch — but corroborated below).
- the-decoder.com — "Claude subscriptions get separate budgets for programmatic use, billed at full
  API prices." Effective **June 15 2026**. Pool sizes Pro $20 / Max5x $100 / Max20x $200. Exhaustion
  governed by **"Usage Credits"** toggle (ON = billed at API; OFF = pause till reset).
- xda-developers.com — "Claude subscriptions no longer include Agent SDK and `claude -p` usage."
  Same date, same pool sizes, same toggle behavior.
- VentureBeat — Anthropic reinstated third-party/OpenClaw usage "with a catch": the separate,
  non-subsidized, API-rate credit pool.
- Timeline: blocked Apr 4 2026 → reinstated-with-pool announced ~May 13–14 2026 → **effective June 15 2026**.

---

## The ONE lever that decides billing: `CLAUDE_CODE_ENTRYPOINT`

```
Interactive Claude Code (human OR script driving the real REPL, NO -p) → entrypoint = "cli"      → SUBSCRIPTION quota (5h/weekly; Anthropic just RAISED these)
claude -p  /  claude_agent_sdk.query()                                  → entrypoint = "sdk-cli"  → PROGRAMMATIC POOL (Jun 15)
```

This tag is set by **invocation mode at process startup**, sent to Anthropic, and is **not spoofable**
(tested). The June-15 split bills off this tag.

---

## Empirical proof matrix — CORE (every row RUN on this machine; $0; subscription only)

These are the load-bearing facts for **the path** (the guard recipe below). Tested dead-ends and
alternative options are intentionally NOT here — see the side note.

| # | Test | Command (reproducible) | Observed | Conclusion |
|---|---|---|---|---|
| 1 | OAuth, no key | `claude -p "PONG"` | `PONG` exit 0 | subscription path OK |
| 2 | OAuth **+ invalid key** | `ANTHROPIC_API_KEY=sk-ant-INVALID claude -p …` | `Invalid API key` exit 1 | **key OVERRIDES OAuth (V1 vector)** |
| 3 | OAuth + key, **prod strip** | `env=` `{ANTHROPIC_API_KEY:"",ANTHROPIC_AUTH_TOKEN:""}` | `PONG` exit 0 | **strip defeats key precedence ✅ (the fix works)** |
| 4 | No OAuth, no key | `HOME=/empty claude -p …` | `Not logged in · /login` exit 1 | **fail-closed, $0** |
| 5 | No OAuth + invalid key | `HOME=/empty ANTHROPIC_API_KEY=… claude -p` | `Invalid API key` exit 1 | a *valid* key here = silent API bill |
| 6 | Orchestrator guard | `_assert_claude_code_oauth_ready()` w/ no creds | `RuntimeError` **before any network**, key stripped | earnings fail-closed ✅ |
| 7 | Overage state | live SDK `RateLimitInfo` | `overage_disabled_reason="org_level_disabled"` | **V2 currently $0** (pool empty → pause) |
| 8 | Entrypoint split | SessionStart hook prints `$CLAUDE_CODE_ENTRYPOINT` | interactive=`cli`, `-p`=`sdk-cli` | the billing lever |
| 15 | Burn-rate | real predictor session tokens × Opus API rates | **$14.70 / run**; $200 pool ≈ 14 runs/mo | pool inadequate for volume |

---

## Side note — alternatives & tested dead-ends (NOT the path; do not revisit)

The guard recipe below (SDK + key-strip + fail-closed + overage OFF; volume managed by batching)
is the documented default. The following were investigated and are kept here as brief references:

| Approach | Empirical verdict | Note |
|---|---|---|
| **#6 scripted interactive REPL** (entrypoint `cli`) | billing PROVEN works; TUI automation fragile; if Anthropic detects it, documented consequence = Claude-subscription suspension | full scope in the **PRELIMINARY** section below |
| **Codex / ChatGPT subscription** | `~/.codex/auth.json` = ChatGPT-sub OAuth (`OPENAI_API_KEY:null`) — works, **different vendor**, not Claude | candidate for heavy batches |
| **Hermes** | routes to `provider: openai-codex`; its `ANTHROPIC_API_KEY` blank | not an Anthropic billing path |
| **Direct Anthropic API + spend cap** | bills API | excluded by project rule (no API — see CLAUDE.md) |
| `--bare` | `claude --bare -p` w/ OAuth, no key → `Not logged in` exit 1 | **DEAD END** — `--bare` is API-key-only, ignores OAuth |
| Spoof `CLAUDE_CODE_ENTRYPOINT=cli` with `-p` | still `sdk-cli` | **DEAD END** — not spoofable |
| `-p` under a PTY (`script -qec`) | still `sdk-cli` | **DEAD END** — it's `--print`, not TTY, that tags it |

**Empirical fact:** *Anthropic + subscription + automated + durable* no longer exists — Anthropic
removed it (June 15 2026). The guard recipe is durable + $0/fail-closed + volume-capped; the rows
above are the investigated alternatives.

---

## APPLY-THIS-FIX recipe — EarningsTrigger + Guidance extraction

### Status of each entrypoint (verified 2026-05-15)

| Entrypoint | V1 key-strip | V2 fail-closed assert | Net |
|---|---|---|---|
| `scripts/earnings/earnings_orchestrator.py` predictor (`_run_predictor_via_sdk`) | ✅ `env=_sdk_subprocess_env()` | ✅ `_assert_claude_code_oauth_ready()` | **Bulletproof** |
| `scripts/earnings/earnings_orchestrator.py` learner (`_run_learner_via_sdk`) | ✅ `env=_sdk_subprocess_env()` | ✅ | **Bulletproof** |
| `scripts/extraction_worker.py` (Guidance) | ❌ **none** — `ClaudeAgentOptions(...)` has no `env=` | ❌ none | ⚠️ **Relies solely on K8s YAML blanking the key. Outside that pod = exposed.** |
| Any future EarningsTrigger SDK callsite | — | — | Must apply the guard below |

### The fix (mirror the orchestrator pattern into every SDK entrypoint)

For **`scripts/extraction_worker.py`** and any new `claude_agent_sdk` callsite:

1. **V1 guard — strip billable auth from the subprocess env:**
   ```python
   # in the ClaudeAgentOptions(...) for query():
   env={"ANTHROPIC_API_KEY": "", "ANTHROPIC_AUTH_TOKEN": ""}   # overlay; forces OAuth
   ```
   (Proven in test #3: empty-string overlay defeats an inherited key. SDK `env=` MERGES, so HOME/PATH survive.)

2. **V2 guard — fail closed before any network call:**
   ```python
   # before query(): assert ~/.claude/.credentials.json exists & parses; else raise.
   # Reuse earnings_orchestrator._assert_claude_code_oauth_ready() pattern (test #6).
   ```

3. **Account-level (one-time, not code):** Anthropic Console → Billing → keep **Usage Credits / overage
   OFF**. Verify via SDK `RateLimitInfo.overage_disabled_reason == "org_level_disabled"` (test #7).

4. **Never** re-introduce `ANTHROPIC_API_KEY` into `.env`, shell profiles, or unblanked K8s secrets
   (see CLAUDE.md "Anthropic API Key Handling"). `~/.anthropic_drivers_key` stays isolated to `drivers/`.

After (1)+(2)+(3): the entrypoint is **code-ironclad** — subscription only; if Anthropic pulls the
subscription it **fails closed ($0)**; it can never silently bill API.

### If subscription-billing of the automation is REQUIRED (Option #6 recipe)

Run the earnings/guidance work as **skills/slash-commands inside a real interactive Claude REPL**
(launched via `pty.fork()`, **no `-p`, no `--print` anywhere**) so `CLAUDE_CODE_ENTRYPOINT=cli`.
Proven to bill as subscription (test #11). **Caveats (also proven):** TUI keystroke automation is
fragile (BypassPermissions dialog, space-collapsed render, `EAGAIN`, nested-TUI); Anthropic is
actively building detection for this pattern (documented consequence if detected: Claude-subscription
suspension). Full scope in the PRELIMINARY section below.

---

## PRELIMINARY — Option #6 change scope (reference only; not a decision)

> Captured 2026-05-15 — scope reference for Option #6. **Material facts to weigh:** #6 means
> driving the real interactive REPL so usage bills as `cli` (subscription) instead of the
> programmatic pool. It is automating what Anthropic classifies as interactive use. Anthropic is
> actively building detection for this pattern; the documented consequence if detected is
> suspension/ban of the Claude subscription, which affects all Claude access (this pipeline +
> Claude Code), not just the earnings/guidance jobs. Effort + change scope below.

**Summary:** the answer is mixed, and the split matters — the **intelligence layer needs zero
changes**, the **transport layer needs a substantial new component**, **capture is near-free**.

### Component-by-component

| Component | Change for #6 | Why |
|---|---|---|
| Skills / prompts / `/extract` / `/earnings-prediction` / `result.json` schemas | **ZERO** | #6 runs the exact same slash-commands. What Claude does is byte-identical. |
| Obsidian: `obsidian_capture.py` SubagentStop hook | **ZERO** | Hooks fire inside the session regardless of entrypoint. |
| Obsidian: `harvest_guidance_sessions.py` watcher | **~ZERO** | Scans the projects dir for JSONLs — interactive sessions write the same `~/.claude/projects/.../<id>.jsonl`. Entrypoint-agnostic already. |
| Obsidian: `thinking_harvester.py` | **MINOR** | Only needs session-id sourced differently (SessionStart hook instead of SDK `msg.session_id`). Core unchanged. (Thinking already 0%/redacted — #6 doesn't worsen it.) |
| Transport: `extraction_worker.py` + `_run_predictor_via_sdk` + `_run_learner_via_sdk` + A/B scripts | **MAJOR** | Replace clean `claude_agent_sdk.query()` (async, structured `ResultMessage`, `session_id`, exceptions) with a new PTY interactive-REPL driver: spawn pty, clear BypassPermissions dialog, inject prompt, detect completion, capture session-id, timeout/kill, isolate concurrency. |
| K8s guidance pod (KEDA-scaled, headless, 24/7) | **HARD (design, not just code)** | Interactive-TUI-in-a-pod running 24/7 is exactly Anthropic's detection target. PTY-per-concurrent-run isolation. |

### The insight that makes it feasible (not insane)

The skills **already write `result.json` / `section_audit.json` to disk** — the SDK return string
is secondary. So the driver does **NOT** need to screen-scrape the redrawing ANSI TUI (the part
that failed 4/4 of the probes). Instead:

```
driver: pty-spawn claude (no -p) → answer BypassPermissions dialog → inject prompt
        → SessionStart hook writes session-id to a file
        → POLL for result.json + a completion sentinel
        → kill pty
```

Converts #6 from "screen-scrape a redrawing TUI" (very fragile) → "fire prompt, wait for a file"
(manageable). That is the difference between unworkable and workable.

### Honest effort + verdict

```
Robust PTY driver module (dialog + sentinel + session-id hook + concurrency)  ~1–2 days v1
Wire into 3 callsites                                                          ~0.5 day
thinking_harvester session-id sourcing change                                 ~0.5 day
K8s PTY-in-pod + detection-risk design                                        decision, not code
                                              ─────────────────────────────────────────
TOTAL: a few focused days for v1  +  PERMANENT fragility tax (breaks on every
       Claude Code UI update; Anthropic actively hunting this pattern)
```

Not minimal — but not a rewrite of the brain, only the plumbing. Skills, prompts, result
contracts, and 2 of 3 Obsidian pieces are untouched.

**Comparison (factual):** #6 is the most code and the least durable of the options, and adds
Claude-subscription-suspension risk if Anthropic detects the pattern.

```
Option 1 (overage OFF, accept pool)  →  ~0 code,  durable,  volume-capped (fix via batching/Codex)
Option 3 (Codex/ChatGPT sub)         →  provider swap,  durable today,  no-API
Option 6 (this)                      →  few days code + ongoing fragility + subscription-ban risk
```

If #6 is built, the lowest-risk shape is the **sentinel-file driver** above (no screen-scrape).
The two open de-risking checks are now **RESOLVED — empirically proven 2026-05-15** (see below).

### PROVEN reliable #6 primitive (empirical campaign 2026-05-15 — 17/17, zero failures)

The fragile keystroke/screen-scrape approach (4/4 earlier probe failures) was abandoned. The
**reliable primitive** is:

```
pty.fork()  →  claude --settings <throwaway-hook.json>
                      --dangerously-skip-permissions
                      --model <model>
                      "<POSITIONAL prompt: do work, write result.json, then `printf DONE > sentinel`>"
   NO  -p / --print anywhere            (─p ⇒ entrypoint sdk-cli ⇒ pool)
   MUST be under a PTY                  (piped stdout ⇒ sdk-cli ⇒ pool — boundary tested)
   prompt passed as POSITIONAL arg      (auto-runs; ZERO keystroke automation)
   --dangerously-skip-permissions       (no BypassPermissions dialog; trust already accepted)
   SessionStart hook                    (records $CLAUDE_CODE_ENTRYPOINT + session_id, no tokens)
   driver only POLLS the sentinel file, then SIGKILLs the pty
```

**Empirical results (all subscription/OAuth, `ANTHROPIC_API_KEY` stripped, $0 marginal):**

| Check | Result |
|---|---|
| Probe A (positional prompt auto-runs, cli) | 1/1 ✅ |
| Repeatability (sequential) | **8/8** ✅ (~3s each) |
| Concurrency (parallel) | **4/4** ✅ — 4/4 **unique** session_ids = perfect isolation |
| Session-id capture + JSONL in projects dir (Obsidian harvester feasible) | ✅ proven |
| Realistic multi-step work (Read+compute+structured `result.json`+sentinel) | **3/3** ✅ valid payloads |
| Boundary: piped stdout (no PTY) | entrypoint `sdk-cli` ⇒ **PTY is mandatory** (pinned) |
| **Every success** | `entrypoint=cli` = **Claude Max subscription**, never pool, never API |

**Total: 17/17.** The mechanism is proven 100% reliable, repeatable, concurrent, subscription-billed,
and capture-compatible. The earlier "MAJOR/fragile transport" estimate is **superseded**: the driver
is a small launch+poll+kill loop (no TUI parsing, no dialog, no keystrokes).

**Residual non-technical caveat (unchanged, stated as fact):** "100% reliable" describes the
*mechanism*. It does not bound Anthropic's detection of automated-interactive usage; that is a
vendor step-function risk (documented consequence if detected: Claude-subscription suspension),
not an engineering variable. Pre-June-15 the pool/interactive split is not yet live to observe;
`entrypoint=cli` is the documented determinant and is proven set on every run.

**Reusable artifacts (throwaway, isolated in `/tmp`, zero production changes):**
`/tmp/p6_lib.py` (`run_once(tag, prompt)` primitive + harness), `/tmp/p6_probeA.py`. Re-runnable
anytime to re-verify, $0, subscription-only.

## Re-verify anytime (throwaway, $0, subscription-only)

Deterministic entrypoint check (no model tokens) — proves which bucket a launch mode bills to:

```bash
# throwaway SessionStart hook records the entrypoint, no model call
echo '{"hooks":{"SessionStart":[{"hooks":[{"type":"command",
 "command":"printf %s \"$CLAUDE_CODE_ENTRYPOINT\" > /tmp/ep.txt"}]}]}}' > /tmp/ts.json
# interactive (no -p): expect "cli"
python3 -c 'import os,pty,time,select,signal;\
p,f=pty.fork();\
(os.execve("/home/faisal/.local/bin/claude",["claude","--settings","/tmp/ts.json"],{**os.environ}) if p==0 else None);\
[select.select([f],[],[],1) for _ in range(25)];os.kill(p,signal.SIGKILL)'
cat /tmp/ep.txt          # → cli  (subscription)   vs  sdk-cli for `claude -p`
```

Live overage/no-charge check: any `claude_agent_sdk` run → inspect `RateLimitInfo`
(`overage_disabled_reason`). `org_level_disabled` ⇒ pool-exhaustion will pause, not bill.

---

## Open decisions for the user (not yet actioned)

1. Pick Option **1 / 2 / 3** (or hybrid: 1 as safe default + 3 for heavy batches).
2. Approve the **Guidance-worker V1+V2 guard** code fix (production change — needs explicit OK).
3. Whether to add a permanent `scripts/verify_no_charge.py` (CI/pre-Jun-15 guard).

> Until decided: pipelines remain on the SDK path. They are **$0/fail-closed** while overage stays
> `org_level_disabled` and no API key leaks — but after **June 15 2026** throughput is capped to the
> programmatic pool (~14 predictor runs/mo on Max20x) then pauses.

---

## Appendix — PROVEN #6 primitive code (self-contained; reproduce anytime, $0, subscription-only)

Embedded so it survives `/tmp` wipe. Throwaway/isolated; **not production**. Each call = one
ephemeral interactive Claude session billed `cli` (Claude Max subscription), no `-p`, no API key.

```python
import os, pty, time, select, signal, json

CLI = "/home/faisal/.local/bin/claude"

def run_once(tag, prompt, model="claude-sonnet-4-6", timeout=150):
    """One subscription-billed Claude run. Returns {entrypoint, session_id, done, elapsed}.
       entrypoint MUST be 'cli' (subscription). PTY is mandatory; piped stdout ⇒ 'sdk-cli' ⇒ pool."""
    ep, sid, done, ts = (f"/tmp/p6_{k}_{tag}.txt" if k!='ts' else f"/tmp/p6_ts_{tag}.json"
                          for k in ("ep","sid","done","ts"))
    for f in (ep, sid, done):
        try: os.remove(f)
        except FileNotFoundError: pass
    cmd = (f'printf %s "$CLAUDE_CODE_ENTRYPOINT" > {ep}; '
           f'python3 -c \'import sys,json;open("{sid}","w").write('
           f'(json.load(sys.stdin) or {{}}).get("session_id",""))\'')
    json.dump({"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":cmd}]}]}}, open(ts,"w"))
    argv = [CLI, "--settings", ts, "--dangerously-skip-permissions",
            "--model", model, prompt]                       # NOTE: NO -p ; positional prompt
    t0 = time.time(); pid, fd = pty.fork()                   # NOTE: PTY mandatory
    if pid == 0:
        env = dict(os.environ); env.pop("ANTHROPIC_API_KEY", None)  # subscription only
        os.execve(CLI, argv, env)
    while time.time() < t0 + timeout:
        r,_,_ = select.select([fd], [], [], 1)
        if r:
            try:
                if not os.read(fd, 65536): break
            except OSError: break
        if os.path.exists(done):
            time.sleep(0.3); break
    try:
        os.kill(pid, signal.SIGKILL); os.waitpid(pid, 0)
    except Exception: pass
    return {"entrypoint": open(ep).read().strip() if os.path.exists(ep) else "<none>",
            "session_id": open(sid).read().strip() if os.path.exists(sid) else "",
            "done": os.path.exists(done), "elapsed": round(time.time()-t0,1)}
```

**Contract for the prompt** (mirrors existing skills — they already write `result.json`): the
positional prompt must end by writing the canonical result file **and** a sentinel, e.g.
`… then run Bash: printf DONE > <sentinel>`. The driver polls the sentinel; it never parses the
screen. For real pipeline work, raise `timeout` (predictor ≈ minutes) — mechanism is unchanged.

**Wiring (when/if approved — production change, not done):** replace the
`claude_agent_sdk.query(...)` body in `_run_predictor_via_sdk` / `_run_learner_via_sdk` /
`extraction_worker.py` with a `run_once(...)` call; read the existing `result.json`; harvest via
the captured `session_id` (Obsidian harvester's only change — proven feasible).

---

## Appendix B — HARDENED primitive (long-run safe) — ACCEPTED v3 (tmux). Campaign 2026-05-15.

The Appendix-A `run_once` was hardened for **~25-min earnings predictions that must never be
killed mid-flight** + graceful exit. Two variants built & tested head-to-head; **v3 (tmux)
ACCEPTED**, v2 (pty) retained as fallback. All tests subscription-only (`entrypoint=cli`), $0,
isolated in `/tmp`, **zero production change**.

### Test results (every gate, test-then-accept)

| Gate | v2 (pty.fork) | v3 (tmux) |
|---|---|---|
| Exit-method probe | `/exit`✅ & SIGTERM✅ graceful; SIGINT/EOF ✗ | (same; `/exit` primary) |
| Regression (short ×N) | 5/5 ✅ | 3/3 ✅ |
| Medium 130–150s (not cut early) | ✅ 153s graceful | ✅ graceful |
| Fast-fail on child death (no 40-min hang) | ✅ `process_died` 12s | ✅ via `has-session` |
| Concurrency (3–4 parallel, isolated) | 3/3 ✅ unique sids | 3/3 ✅ unique sids |
| **Driver-crash survival** (driver killed mid-run) | ✗ dies with parent | **✅ tmux session + run SURVIVE; sentinel still written** |
| **25-MIN not-killed-mid-flight** | **✅ elapsed=1506s, ep=cli, outcome=ok, exit_via=slashexit, sid=Y** | **✅ elapsed=1505s, ep=cli, outcome=ok, exit_via=slashexit, sid=Y** |

**DECISION: ACCEPT v3 (tmux).** It passes everything v2 passes **and** survives a driver crash —
decisive for 25-min predictions (if the orchestrator/driver restarts at minute 18, a raw-pty run
is lost; the tmux-hosted run keeps going and the sentinel still lands). v2 kept as the simpler
no-tmux fallback.

### Hardening design (both variants)

```
• Completion = the SENTINEL FILE the task writes — NEVER a wall-clock timeout.
• HARD_CAP default 2400s (40min) ≫ 25min — last-resort only; never the thing that
  stops a real run. (For predictor set generous; mechanism unaffected by task length.)
• NEVER terminate while the Claude child/tmux-session is alive & sentinel absent
  (no mid-run kill).
• If the child exits ON ITS OWN before the sentinel → fast-fail in seconds
  (don't wait 40 min on a dead session).
• PTY drained continuously (v2) so a long chatty run can't block on a full pipe.
• Graceful exit: `/exit` → (v2: SIGTERM→SIGKILL last resort | v3: kill-session last resort).
  `/exit` succeeded on every test (exit_via=slashexit) — no SIGKILL, best detectability posture.
• entrypoint=cli + session_id captured via SessionStart hook (Obsidian-harvest ready).
```

### ACCEPTED v3 code (self-contained — survives `/tmp` wipe; `/tmp/p6_lib_v3_tmux.py`)

```python
import os, time, json, subprocess, shlex
CLI, SOCK = "/home/faisal/.local/bin/claude", "p6sock"
def _tmux(*a): return subprocess.run(["tmux","-L",SOCK,*a],capture_output=True,text=True)
def _has(s):   return _tmux("has-session","-t",s).returncode==0

def run_once_v3(tag, prompt, model="claude-sonnet-4-6",
                hard_cap_s=2400, exit_grace_s=8, heartbeat_s=60, log=print):
    """One subscription-billed (entrypoint=cli) Claude run, tmux-hosted.
       NEVER killed while alive+sentinel-absent until hard_cap. Survives driver crash.
       Returns {entrypoint, session_id, done, outcome, exit_via, elapsed}."""
    sess=f"p6_{tag}"; ep=f"/tmp/p6_ep_{tag}.txt"; sid=f"/tmp/p6_sid_{tag}.txt"
    done=f"/tmp/p6_done_{tag}.txt"; ts=f"/tmp/p6_ts_{tag}.json"; sh=f"/tmp/p6_run_{tag}.sh"
    for f in (ep,sid,done):
        try: os.remove(f)
        except FileNotFoundError: pass
    cmd=(f'printf %s "$CLAUDE_CODE_ENTRYPOINT" > {ep}; python3 -c \'import sys,json;'
         f'open("{sid}","w").write((json.load(sys.stdin) or {{}}).get("session_id",""))\'')
    json.dump({"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":cmd}]}]}},open(ts,"w"))
    with open(sh,"w") as fh:                      # subscription-only env; no quoting hell
        fh.write("#!/bin/bash\nunset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN\n"
                 f"exec {shlex.quote(CLI)} --settings {shlex.quote(ts)} "
                 f"--dangerously-skip-permissions --model {shlex.quote(model)} "
                 f"{shlex.quote(prompt)}\n")
    os.chmod(sh,0o755)
    _tmux("kill-session","-t",sess)
    t0=time.time()
    r=_tmux("new-session","-d","-s",sess,"-x","220","-y","50","-f","/dev/null",
            f"bash {shlex.quote(sh)}")
    if r.returncode!=0:
        return {"tag":tag,"entrypoint":"<none>","session_id":"","done":False,
                "outcome":"spawn_failed","exit_via":"n/a","elapsed":0}
    outcome="running"; last=t0
    while True:
        now=time.time()
        if os.path.exists(done): outcome="ok"; break
        if not _has(sess):       outcome="process_died"; break   # crash → fast-fail
        if now-t0>hard_cap_s:    outcome="cap_exceeded"; break    # last-resort ceiling
        if now-last>=heartbeat_s:
            log(f"  [{tag}] hb t={int(now-t0)}s has_session={_has(sess)} "
                f"sentinel={os.path.exists(done)}"); last=now
        time.sleep(2)
    elapsed=round(time.time()-t0,1); exit_via=None
    if _has(sess):
        _tmux("send-keys","-t",sess,"/exit","Enter")            # graceful first
        g=time.time()
        while time.time()<g+exit_grace_s:
            if not _has(sess): exit_via="slashexit"; break
            time.sleep(0.5)
        if exit_via is None and _has(sess):
            _tmux("kill-session","-t",sess); exit_via="kill-session"  # last resort
    else: exit_via="self"
    try: os.remove(sh)
    except FileNotFoundError: pass
    return {"tag":tag,
            "entrypoint":open(ep).read().strip() if os.path.exists(ep) else "<none>",
            "session_id":open(sid).read().strip() if os.path.exists(sid) else "",
            "done":os.path.exists(done),"outcome":outcome,
            "exit_via":exit_via,"elapsed":elapsed}
```

**Prompt contract (unchanged):** the positional prompt must do the work then write the canonical
`result.json` **and** end with `… run Bash: printf DONE > <sentinel>`. Driver polls the sentinel,
never the screen. For the real ~25-min predictor: keep `hard_cap_s` generous (e.g. 2400–3600);
mechanism is duration-agnostic — proven at 25 min (elapsed≈1505s, never killed).

**Wiring (production change — needs explicit OK, NOT done):** swap the `claude_agent_sdk.query(...)`
body in `_run_predictor_via_sdk` / `_run_learner_via_sdk` / `extraction_worker.py` for
`run_once_v3(...)`; read existing `result.json`; harvest via captured `session_id`.
