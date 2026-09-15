# Core ↔ Codex communication

This file owns communication and session setup only. `Steps.md`, the active
step and its live authorities own project work; `STATUS_AND_HISTORY.md` owns
current progress and the working location. The owner's latest explicit pause,
stop or bounded task takes precedence over an older task or goal. Transport
success never authorizes a model call, database write, deployment or later step.
Only the owner may grant an approval the roadmap explicitly reserves.

## 1. Locations and roles

Start both sessions in `/home/faisal/EventMarketDB`. Core's working reply hook
is registered there in `.claude/settings.local.json`; another worktree does
not automatically inherit it. Before editing or testing, read
`.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md` and the latest valid
task to identify the actual worktree. Use explicit paths, a command working
directory or a subshell there; the session's launch location is not permission
to edit main. Do not copy settings or hooks between worktrees as a shortcut.

Core implements; Codex independently reviews and assigns one bounded task.
Explicit owner assignments may override that role split for a named task.
Codex never launches, signals or stops the Core session.

| Existing tmux session | Purpose |
|---|---|
| `driver-core` | Core's interactive session |
| `driver-codex` | Codex's interactive session |
| `core-mailwatch` | Persistent Codex-message archive loop |
| `codex-mailwatch` | Persistent Core-message event watcher |

A session such as `7` is outside this protocol; leave it alone. `(attached)`
means a terminal client is attached, not a duplicate watcher. Verify process commands,
not session names or creation dates. Core also has one **in-session notification
receiver** (§5); it is not another tmux archiver. Replacing an AI session does
not require replacing the two persistent tmux workers.

Mailboxes and immutable message archives:
`/home/faisal/.core827-orchestrator/`. Additional archives and the send gate:
`/home/faisal/.core827_backups/`, including `sendgate/`. The old `core827`
name and its old `PROTOCOL.md` task restrictions are historical, not Driver law.

## 2. Exact replacement prompts

The owner closes the old role's session before starting its replacement.
Launch from main as above. Copy the matching block and replace only its one
runtime-ID placeholder. Never put the peer's ID into it.

### Core

```text
You are replacement Core, the repository implementer. Your runtime session ID
is <CORE_SESSION_ID>. Read /home/faisal/EventMarketDB/AGENTS.md and
/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Orchestration.md
completely. Follow "Start or resume a Core session" exactly. Use the worktree
named in STATUS_AND_HISTORY.md and the latest valid task, not automatically
main. Do no project work until identity binding and notification delivery are
verified. Obey the owner's current stop state, the live roadmap and one bounded
Codex task; send one complete reply and wait.
```

### Codex

```text
You are replacement Codex, Core's read-only orchestrator and independent
reviewer. Your runtime thread ID is <CODEX_THREAD_ID>. Read
/home/faisal/EventMarketDB/AGENTS.md and
/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Orchestration.md
completely. Follow "Start or resume a Codex session" exactly. Do no project
review or work until identity binding and notification delivery are verified.
Reuse the existing watcher and this thread's existing goal where present.
Independently verify each Core result, assign only the next authorized bounded
task, and honor the owner's current pause or stop.
```

## 3. Message format and identity

Only Core writes `CORE_TO_CODEX.md`; only Codex writes `CODEX_TO_CORE.md`.
Each contains one complete message. Publish through a complete sibling
`.tmp` and atomic rename, never append or stream. Core uses the send gate
in §5. Never overwrite an unarchived outbound message.

```text
SEQ: <sender's next integer>
IN_REPLY_TO: <exact incoming peer SEQ>
FROM: Core | Codex
TO: Codex | Core
SESSION: <sender's own runtime ID>
ACTION: CONTINUE | WAIT | CHANGES_REQUIRED | VERIFIED
TYPE: <message purpose>
HEAD: <main HEAD>
RECOVERY_HEAD: <worktree HEAD, when the task uses another worktree>
INCOMING_SHA256: <SHA-256 of exact incoming peer-message bytes>
IDENTITY: <exact reviewed files, commit/tree or manifest and applicable hashes>
```

Core reads its own nonempty `CLAUDE_CODE_SESSION_ID`; it must equal its launch
prompt and line 1 of `G3_CONTINUOUS_RUN`. Codex reads its own nonempty
`CODEX_THREAD_ID`. `CODEX_COMPANION_SESSION_ID` names Core, not Codex.
Never guess an ID or use a hash prefix as a full hash.

Counters are independent. Before sending, derive the next SEQ from the highest
SEQ header in that role's current outbound mailbox and **every outbound
archive** under both archive roots above. Do not infer it from filenames, the
peer's counter or memory. Old archives lacking SESSION count only as sequence
history. New messages require SESSION.

Before accepting a message, verify sender/recipient, bound session, exact
IN_REPLY_TO, incoming hash and available byte-identical archives. Reconstruct
missing links; do not guess. A changed SESSION without a handover is invalid.
Both peers perform these checks: the send gate validates supplied claims but
does not itself enforce every session, sequence or task rule.
When correcting a conclusion, name its archived message and state what changed.

### Binding a new session

The first send is `TYPE: SESSION_HANDOVER`, `ACTION: WAIT`. If answering the
peer's handover, use `SESSION_HANDOVER_ACK` instead; it also publishes the
sender's own identity. Each carries the headers above and the exact incoming
message hash. Learn the peer's ID only through a verified handover or its ACK.

An ACK names the exact handover SEQ. If handovers cross, each sends one exact
ACK before project work. Binding is complete only after each side has sent its
own ID and received the other's verified ID. An ordinary compaction of the
same already-bound pair does **not** require a new handover or reset counters.

Use the handover/ACK as the notification test: Core must receive its incoming
notice inside the current Core session, and Codex must receive the watcher
output through its attached terminal (§6). Seeing a tmux process or an archive
alone is not proof of delivery. Read the full mailbox and verify its hash after
the notice. If a receiver cannot be attached, report that communication is not
ready; do not start project work. Never repeat a successful project/model call
to test communication.

If the handover arrived before a receiver was attached, finish binding, then
Codex sends one `TRANSPORT_PROBE` with a unique nonce and `ACTION: WAIT`.
Core replies once with `TRANSPORT_PROBE_ACK`, that nonce and confirmation of
its in-session notice. Codex verifies the ACK through watcher output. This
tests delivery only; a missing notice is a communication blocker, not a pass.

## 4. Start or resume

### Start or resume a Core session

1. Verify your runtime ID against the launch prompt. For a replacement, put
   it on line 1 of `/home/faisal/.core827-orchestrator/G3_CONTINUOUS_RUN`,
   preserving other lines. Verify it freshly; do not claim the send linter
   proves this automatically.
2. Read, under `/home/faisal/EventMarketDB/.claude/plans/Drivers/`, in order:
   `WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md`,
   `FinalDesign/LeftOverSteps/Steps.md`, `FinalDesign/STATUS_AND_HISTORY.md`,
   the active step, `FinalDesign/LeftOverSteps/promptStandard.md`, then the
   live authorities needed by that step. Preserve a current owner STOP/WAIT.
3. Read both current mailboxes and enough archives to prove their full order.
   Record IDs, sequences, exact hashes, main HEAD and the task worktree HEAD.
   If the current Codex message lacks an archive, Core preserves it by atomic
   copy before setting a new archive-loop baseline. Never overwrite a
   conflicting archive; stop and report it.
4. Reuse the one archive loop; verify the reply hook and the current session's
   notification receiver (§5). Do not duplicate a worker or reuse a receiver
   bound to a closed session.
5. For a new pair, complete the binding and notification check (§3), using the
   gated send. For an unchanged bound pair, resume from the verified chain;
   read the current mailbox because downtime notices are not replayed.
6. Perform only the latest authorized bounded task. Send one complete gated
   reply, including an honest blocked result when necessary, then wait.
   A receipt/ACK is not a request for an ACK-of-ACK.

### Start or resume a Codex session

1. Verify your own runtime ID against the launch prompt.
2. Follow Core's same ordered project reading and mailbox/HEAD checks above.
3. Inspect this thread's goal. Reuse it if present, including a paused or
   blocked goal; neither state means it is absent. Do not create a duplicate
   or mark unfinished work complete. Goal resumption is controlled by the
   owner/application, not by inventing a status update.
4. If there is no goal and continuing coordination is authorized, create one
   without a token budget: `Independently verify Core's results, send one
   authorized bounded next task, and follow the ordered Driver roadmap until
   the owner pauses/stops, a reserved approval or genuine safety conflict is
   reached, or the authorized work is complete.`
5. Reuse and attach to the existing event watcher (§6). For a new pair,
   complete binding and prove notification delivery (§3); for the same bound
   pair, retain the chain and read the current mailbox.
6. Independently review live bytes and raw evidence, not a green test count
   alone. Reply once with a bounded next task, a precise blocker or a stop.
   Write `CODEX_TO_CORE.md.tmp`, validate the complete message, then atomically
   rename it over `CODEX_TO_CORE.md`. Never write Core's mailbox.
7. Stay responsive while authorized coordination is active. A final WAIT
   receipt needs no ACK-of-ACK. At an owner stop, preserve the checkpoint and
   stop project work even if the old goal is unfinished.

## 5. Core archiving, notifications and sending

### Persistent archive loop — one in `core-mailwatch`

Run this check by itself so the checking shell does not match its own text:

```bash
pgrep -af '[C]ODEX_TO_CORE\.md.*archive_CODEX_.*sleep 30'
```

Exactly one row: reuse it. More than one: report, do not add or kill workers.
None: start the following in one persistent terminal named `core-mailwatch`
after checking that an existing pane is not still starting it.

```bash
mailbox=/home/faisal/.core827-orchestrator/CODEX_TO_CORE.md
monitor_log=/home/faisal/.core827_backups/mailbox_archiver.log
baseline=$(sha256sum "$mailbox" | cut -d' ' -f1)
while true; do
  if [ -r "$mailbox" ]; then
    current=$(sha256sum "$mailbox" | cut -d' ' -f1)
    if [ "$current" != "$baseline" ]; then
      seq=$(sed -n 's/^SEQ:[[:space:]]*//p' "$mailbox" | head -n 1)
      archive=/home/faisal/.core827-orchestrator/archive_CODEX_${seq}.md
      if [ -e "$archive" ]; then
        cmp -s "$mailbox" "$archive" || { echo "ARCHIVE_CONFLICT $archive" >&2; break; }
      else
        cp "$mailbox" "$archive.tmp" && mv "$archive.tmp" "$archive" || break
      fi
      cmp -s "$mailbox" "$archive" || { echo "ARCHIVE_MISMATCH $archive" >&2; break; }
      printf '%s CODEX MAILBOX CHANGED sha %s SEQ %s %s\n' \
        "$(date '+%F %T')" "${current:0:16}" "$seq" archived >> "$monitor_log"
      baseline=$current
    fi
  fi
  sleep 30
done
```

This loop archives; **it does not notify the Core AI session**.

### In-session notification receiver — one per current Core session

Use Core's `Monitor` tool with `persistent: true`,
`timeout_ms: 3600000`, and a description marking it **notify-only**.
Its `command` is the already-proven read-only receiver:

```bash
mb=/home/faisal/.core827-orchestrator/CODEX_TO_CORE.md
base=$(sha256sum "$mb" | cut -d' ' -f1)
while true; do
  sleep 15
  [ -r "$mb" ] || continue
  cur=$(sha256sum "$mb" 2>/dev/null | cut -d' ' -f1) || true
  [ -n "$cur" ] || continue
  if [ "$cur" != "$base" ]; then
    seq=$(sed -n 's/^SEQ:[[:space:]]*//p' "$mb" | head -n 1)
    echo "CODEX MAILBOX CHANGED SEQ $seq sha ${cur:0:16}"
    base=$cur
  fi
done
```

Reuse an active receiver owned by this same Core session. A replacement needs
delivery to its new session, not merely a surviving old receiver process.
If the old receiver survives closure, report the ownership conflict; do not
start a duplicate or signal the old Core. If Monitor is unavailable or expires,
report/re-establish the receiver through Core's supported tool before resuming.
It writes no mailbox/archive and does not authorize work.

### Reply hook and gated send

Verify main's `.claude/settings.local.json` registers exactly one Stop hook
for `.claude/hooks/core827_keep_going.py`. Its existing rule is only:
current Codex SEQ must equal Core's IN_REPLY_TO before Core ends its turn.
A correctly replied WAIT or blocked report permits stopping. The hook does
not validate the whole message or demand further edits after a reply.
Do not edit settings/hooks as part of ordinary handover.

Before each send, freshly compare the draft SESSION, Core's runtime ID and
line 1 of G3_CONTINUOUS_RUN; include that comparison in the gated claims.
Read `sendgate/verify_claims.py` and `lint_message.py` for their existing
claim/ack format if needed. Do not bypass the gate:

```text
/home/faisal/.core827_backups/sendgate/send_gated.sh <draft> <claims.tsv> <ack-lines> <archive_copy> <dest>
```

Use exactly five arguments; `dest` is CORE_TO_CODEX.md. A failed check sends
nothing: correct the false claim or report the real blocker. Archive and
delivered bytes must match. Never invent a hash, quietly truncate it or retry
with a weaker check.

## 6. Codex event watcher and output attachment

Run this process check:

```bash
pgrep -af '^/home/faisal/EventMarketDB/venv/bin/python[^ ]* /home/faisal/EventMarketDB/venv/bin/watchmedo shell-command .*CORE_TO_CODEX.md'
```

Exactly one: reuse it. More than one: report, do not duplicate or kill.
Only if absent, start this in one persistent terminal named `codex-mailwatch`:

```bash
/home/faisal/EventMarketDB/venv/bin/watchmedo shell-command \
  --quiet --ignore-directories --patterns='*/CORE_TO_CODEX.md' \
  --command='sed -n "1,360p" /home/faisal/.core827-orchestrator/CORE_TO_CODEX.md' \
  /home/faisal/.core827-orchestrator
```

The existing worker reacts to atomic rename and prints the notice/message.
Attach its output to a persistent Codex terminal **with a PTY**:

```bash
env -u TMUX tmux attach-session -r -t codex-mailwatch
```

This is a read-only tmux client, not a new watcher. Keep that terminal handle
while coordinating; wait for its output rather than polling mailbox hashes.
Detach only this client with tmux's detach key (`Ctrl-b`, then `d` under the
default binding), not Ctrl-C on the watcher. Existing attached owner terminals
may remain. A new task always reads the current full mailbox first: old events
are not replayed, and this watcher cannot wake a closed Codex task.
Do not add hash loops, tail loops, timed mailbox polling or another watcher.

## 7. Interrupting a live Core task

Normally send no second instruction before Core replies. The sole exception
is the exact stop message below. First prove: the superseded instruction has
a byte-identical archive; the same Core session still owns a live task; and
the requested interruption targets that task only.

```text
SEQ: <next derived Codex integer>
IN_REPLY_TO: <current Core SEQ>
FROM: Codex
TO: Core
SESSION: <Codex's own runtime ID>
ACTION: CHANGES_REQUIRED
TYPE: INTERRUPT_CURRENT_TASK
HEAD: <main HEAD>
RECOVERY_HEAD: <task worktree HEAD, when applicable>
INCOMING_SHA256: <current Core-message hash>
INTERRUPTS_CODEX_SEQ: <superseded Codex instruction>
INTERRUPTS_SHA256: <hash of its byte-identical archive>
TARGET_CORE_SESSION: <bound Core session>
REASON: <specific live task and reason to stop>
IDENTITY: <proof of archive, session and live target>

Validate this interrupt. Stop only cancel-safe process groups Core owns for
this exact task. Preserve all files/results. Send one combined report naming
INTERRUPTED_CODEX_SEQ, stopped PIDs/PGIDs and remaining state, then WAIT.
```

The combined reply uses `IN_REPLY_TO: <interrupt SEQ>` and answers both the
superseded instruction and the interrupt; no separate older reply follows.
Core never stops itself, unrelated/ambiguous jobs or a non-cancel-safe external
call. Let such a call finish once, preserve its result, then stop further work.
An invalid interrupt signals nothing: pause new work, send one exact refusal,
and wait. Never repeat a successful call.

Commands expected to exceed 30 seconds use a named background process group;
Core records ownership and remains mailbox-responsive. Foreground waits while
work is in flight do not exceed 15 seconds. No new mailbox or watcher is added.

## 8. Pausing and closing

When the owner asks to pause, stop or hand over: preserve the current state,
send the one needed completion/blocked/WAIT report, and start no next task.
Likewise stop at a roadmap-reserved approval or genuine unresolved safety
conflict. An unfinished goal is not evidence that the project is complete.

Keep the persistent mailbox workers if replacement-session coordination is
planned. Detach only the current Codex client; each Core session manages only
its own notification receiver. Do not kill Core, delete archives or reset
counters. New sessions repeat the startup checks and honor the current
checkpoint before undertaking any project work.

### Owner commands: replace the AI sessions, keep their tmux names

Run these **from a separate terminal**, outside both sessions being closed.
First obtain Core's final WAIT report and preserve/finish any active jobs;
tmux termination is not the safe task-interrupt procedure in §7. Closing a
session ends its terminal but does not delete Git work or mailbox archives.
Start no replacement while its old AI or session-owned receiver is still alive.

```bash
tmux kill-session -t '=driver-core'
tmux kill-session -t '=driver-codex'
tmux new-session -d -s driver-core -c /home/faisal/EventMarketDB
tmux new-session -d -s driver-codex -c /home/faisal/EventMarketDB
tmux attach-session -t '=driver-core'
```

Start Core normally in that terminal and give it the §2 Core prompt with its
new runtime ID. Detach (`Ctrl-b`, then `d`), then run:

```bash
tmux attach-session -t '=driver-codex'
```

Start Codex normally and give it its own §2 prompt/ID. Both perform §4; do not
reuse an old ID just because the tmux name is unchanged. The `=` targets an
exact session name. If a session is already absent, skip its kill command;
if creation says it exists, inspect it rather than killing an unknown process.

### Owner commands: replace a broken watcher only when necessary

Normally keep both `*-mailwatch` sessions. If one worker is broken, pause both
AI sessions, preserve the mailboxes/archives, and inspect its pane and the
exact process check in §5 or §6. From the separate terminal, use **only the
matching row**, not both:

| Broken worker | Close its terminal | Recreate its empty terminal |
|---|---|---|
| Core archiver | `tmux kill-session -t '=core-mailwatch'` | `tmux new-session -d -s core-mailwatch -c /home/faisal/EventMarketDB` |
| Codex watcher | `tmux kill-session -t '=codex-mailwatch'` | `tmux new-session -d -s codex-mailwatch -c /home/faisal/EventMarketDB` |

Between closing and recreating, recheck the worker process: if it survived,
stop and report it; do not start a duplicate or guess which process to kill.

Attach to that terminal and start its exact §5 or §6 worker. An empty tmux
terminal is not a running watcher. Core re-establishes its own notification
receiver separately; Codex reattaches its output. Read current mailboxes and
prove delivery again under §3 before project work. Never use `tmux kill-server`
or remove session `7`, archives, counters, hooks or settings for this restart.
