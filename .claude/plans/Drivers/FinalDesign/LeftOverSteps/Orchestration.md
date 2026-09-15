# Core ↔ Codex communication

This file defines transport only. The roadmap at
`/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Steps.md`,
the active step file it names, and that step's live authorities define the
work. The `core827` directory name is historical; its old `PROTOCOL.md` task
restrictions are not current Driver law.

## Exact replacement prompts

Copy one block unchanged and replace its single `<..._ID>` placeholder. Change
nothing else; live files supply the peer id, task, sequences, hashes, and HEAD.

### Core prompt

```text
You are replacement Core, the sole repository implementer and writer. Your
runtime session id is <CORE_SESSION_ID>. Read
/home/faisal/EventMarketDB/AGENTS.md and
/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Orchestration.md
completely, then execute "Start or resume a Core session" exactly. Do no project
work before the session handover is complete. After binding, obey only the live
roadmap and latest valid Codex message. Keep exactly one Core mailbox monitor,
honor the documented Codex stop command, reply once, and wait.
```

### Codex prompt

```text
You are replacement Codex, Core's read-only orchestrator and independent
reviewer. Your runtime thread id is <CODEX_THREAD_ID>. Read
/home/faisal/EventMarketDB/AGENTS.md and
/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Orchestration.md
completely, then execute "Start or resume a Codex session" exactly. Do no review
or work before the session handover is complete. After binding, independently
verify every Core reply, send one bounded next task, and keep the Codex goal and
single watcher active. Use only the documented stop message; never signal Core.
```

## Roles

* Core (Claude) implements and writes the repository.
* Codex independently reviews and orchestrates; it does not launch Core.
* Only the owner may approve actions that the live roadmap explicitly reserves.

## Mailboxes

Use `/home/faisal/.core827-orchestrator/`.

| File | Only writer | Reader |
|---|---|---|
| `CORE_TO_CODEX.md` | Core | Codex |
| `CODEX_TO_CORE.md` | Codex | Core |

Each file contains one complete current message. Publish by writing a complete
sibling `.tmp` file and atomically renaming it over the mailbox. Never append,
stream, or write the other side's file. Send one reply per received message;
otherwise a newer message can hide an unread one.

Every message begins with:

```text
SEQ: <this sender's next integer>
IN_REPLY_TO: <the other sender's exact SEQ>
FROM: Core | Codex
TO: Codex | Core
SESSION: <this sender's own runtime session id>
ACTION: <action>
TYPE: <short purpose>
```

The two senders have separate counters. `IN_REPLY_TO`, not matching counter
values, joins the conversation.

## Session binding

`FROM` names a role; `SESSION` names the exact process behind it. Without it a
replaced session is invisible to the other side.

Each side reads only its own nonempty runtime id:

* Core uses `CLAUDE_CODE_SESSION_ID`. It must equal line 1 of
  `G3_CONTINUOUS_RUN`. `CODEX_COMPANION_SESSION_ID` is Core's id despite its
  name and must never be used as Codex's id.
* Codex uses `CODEX_THREAD_ID`.

Each side verifies its own id from its runtime and launch prompt. It learns the
peer id only from a verified `SESSION_HANDOVER` or `SESSION_HANDOVER_ACK`; the
owner never inserts the peer id into either prompt.

Before a new session sends, it derives its next `SEQ` as one greater than the
highest `SEQ` header in its current outbound mailbox and every archive for its
role below `/home/faisal/.core827-orchestrator`,
`/home/faisal/.core827_backups`, and
`/home/faisal/.core827_backups/sendgate`. It never resets or reuses a number.
Its `IN_REPLY_TO` is the exact current peer `SEQ` it read.

Old archives without `SESSION` remain sequence history only. Every current and
new message without `SESSION` is invalid.

A new session's first outbound message is `TYPE: SESSION_HANDOVER`; when its
first outbound is answering the peer's handover, it uses
`TYPE: SESSION_HANDOVER_ACK`, which also serves as its own handover. Both use
`ACTION: WAIT` and carry the sender's `SESSION`, derived `SEQ`, exact
`IN_REPLY_TO`, current repo HEAD, and SHA-256 of the exact incoming peer-message
bytes. An ACK must reply to the exact handover `SEQ`. No work starts until each
side has published its own id and read the other's id. If both handovers cross,
each side sends one exact ACK before work.

For every Core send, the send-gate claim must freshly read line 1 of
`G3_CONTINUOUS_RUN` and prove the `SESSION` value. Otherwise the send linter
must reject it.

After binding, a `SESSION` value that changes without a `SESSION_HANDOVER` is
reported, not answered: it means a session was replaced silently and the
conversation state may be wrong.

## Start or resume a Core session

1. Verify the id in the launch prompt is nonempty and equals
   `CLAUDE_CODE_SESSION_ID`. Put that exact id on line 1 of
   `/home/faisal/.core827-orchestrator/G3_CONTINUOUS_RUN`, preserving any other
   lines, and verify the two values match. Never use
   `CODEX_COMPANION_SESSION_ID` as Codex's id.
2. Read, in order,
   `/home/faisal/EventMarketDB/.claude/plans/Drivers/WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md`,
   `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Steps.md`,
   the active step identified by that roadmap and the mailbox chain,
   `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/promptStandard.md`,
   and every live authority that step names.
3. Read both current mailboxes and the archives needed to prove their complete
   order. Record both current `SEQ` values, each mailbox SHA-256, and repo HEAD.
   Reconstruct any missing link from archives; never guess.
4. Derive Core's next `SEQ` from every Core outbound location defined above.
5. Check the exact Core monitor below. Reuse one; start it only if absent.
   More than one is an error to report, never a reason to start another.
6. Through `send_gated.sh`, send `SESSION_HANDOVER` or acknowledge a peer
   handover with `SESSION_HANDOVER_ACK`. Do no step work until both current
   sessions are bound.
7. After binding, perform only the latest valid bounded Codex task. For
   communication, write only `CORE_TO_CODEX.md` through `send_gated.sh`. Send
   one complete reply and wait. Continue without owner input unless the live
   roadmap explicitly reserves approval.

## Start or resume a Codex session

1. Verify the id in the launch prompt is nonempty and equals
   `CODEX_THREAD_ID`.
2. Read, in order,
   `/home/faisal/EventMarketDB/.claude/plans/Drivers/WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md`,
   `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/Steps.md`,
   the active step identified by that roadmap and the mailbox chain,
   `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/LeftOverSteps/promptStandard.md`,
   and every live authority that step names.
3. Read both current mailboxes and the archives needed to prove their complete
   order. Record both current `SEQ` values, each mailbox SHA-256, and repo HEAD.
4. If Core's `IN_REPLY_TO` does not name Codex's current `SEQ`, reconstruct the
   missing chain from `archive_CORE_*.md` and `archive_CODEX_*.md`; do not guess.
5. Derive Codex's next `SEQ` from the current mailbox and all archives as
   defined above.
6. Check the Codex goal. Reuse the one active goal; if none exists, create one
   without a token budget using this exact objective: `Keep EventMarketDB
   Core-Codex coordination active: independently verify every Core reply, send
   exactly one lawful next message, and continue the ordered roadmap until it
   is complete, a stop explicitly required by the live roadmap is reached, or
   a genuine unresolved safety conflict blocks progress.`
7. Check the one event watcher below. Reuse it if present; start it only if
   absent. More than one is an error to report, not a reason to start another.
8. Complete or acknowledge the session handover. Do no review or work until the
   two sessions are bound.

## Codex watcher

Check it without matching the check command itself:

```bash
pgrep -af '^/home/faisal/EventMarketDB/venv/bin/python[^ ]* /home/faisal/EventMarketDB/venv/bin/watchmedo shell-command .*CORE_TO_CODEX.md'
```

Expected: exactly one row. If none exists, start this command in one persistent
background terminal:

```bash
/home/faisal/EventMarketDB/venv/bin/watchmedo shell-command \
  --quiet \
  --ignore-directories \
  --patterns='*/CORE_TO_CODEX.md' \
  --command='sed -n "1,360p" /home/faisal/.core827-orchestrator/CORE_TO_CODEX.md' \
  /home/faisal/.core827-orchestrator
```

This is the latest proven method. It reacts to the completed atomic rename and
does not repeatedly read the mailbox. The operating-system watcher itself uses
no model tokens while idle. Do not add hash loops, `tail` loops, timed polling,
or another watcher.

The watcher detects a change; it does not approve it. It also cannot wake a
closed Codex task. Keep the Codex task open while active coordination is
required. A new Codex task must always read the current mailbox first because
an event that occurred while the task was closed is not replayed to the model.

## Codex review and reply

On each event:

1. Read the complete `CORE_TO_CODEX.md` and verify its headers, new `SEQ`,
   `IN_REPLY_TO`, and hash.
2. Read the changed files, live code, tests, and raw results. Recompute every
   important identity; Core's summary and green test count are not proof.
3. Reply with exactly one of `CONTINUE`, `WAIT`, `CHANGES_REQUIRED`, or
   `VERIFIED`, tied to the exact reviewed identity and Core `SEQ`.
4. Write the complete reply to `CODEX_TO_CORE.md.tmp`, validate it, then rename
   it over `CODEX_TO_CORE.md`.
5. Name the next allowed task or the precise blocker. Silence is never
   approval.

Use this reply shape:

```text
SEQ: <next Codex integer>
IN_REPLY_TO: <Core SEQ reviewed>
FROM: Codex
TO: Core
SESSION: <Codex's own CODEX_THREAD_ID>
ACTION: CONTINUE | WAIT | CHANGES_REQUIRED | VERIFIED
TYPE: <short purpose>
IDENTITY: <exact reviewed commit, tree, manifest, or file hashes>

<plain ruling, independent checks, and next gate>
```

## Codex stop command

Codex may atomically publish a newer `CODEX_TO_CORE.md` before Core has replied ONLY with
`ACTION: CHANGES_REQUIRED` and `TYPE: INTERRUPT_CURRENT_TASK`. Before publishing it, Codex
proves that the mailbox being superseded already has a byte-identical `archive_CODEX_<SEQ>.md`,
that Core's session id is unchanged, and that the targeted task is live. The interrupt carries
`INTERRUPTS_CODEX_SEQ`, `INTERRUPTS_SHA256`, `TARGET_CORE_SESSION` and a concrete `REASON`; it
takes Codex's next derived SEQ and keeps `IN_REPLY_TO` at the current Core SEQ.

Codex uses this exact stop-message template:

```text
SEQ: <next Codex integer>
IN_REPLY_TO: <current Core SEQ>
FROM: Codex
TO: Core
SESSION: <Codex's own CODEX_THREAD_ID>
ACTION: CHANGES_REQUIRED
TYPE: INTERRUPT_CURRENT_TASK
INTERRUPTS_CODEX_SEQ: <superseded Codex SEQ>
INTERRUPTS_SHA256: <sha256 of byte-identical archive_CODEX_<SEQ>.md>
TARGET_CORE_SESSION: <currently bound Core SESSION>
REASON: <specific task and reason to stop>
IDENTITY: <proof of the archive, live Core session, and live target>

Validate the interrupt, stop only the exact cancel-safe task processes Core
owns, preserve all state, send one combined factual report, and wait.
```

Core validates every one of those fields and the archive before acting. A valid interrupt stops
only cancel-safe process groups Core itself launched for that exact task; it never stops Core, an
unrelated or ambiguous process, or a non-cancel-safe external call. Such a call may finish once,
its result is preserved, and work stops immediately afterward. Core preserves all files and logs,
makes no further task changes, and sends one combined factual reply to the interrupt naming
`INTERRUPTED_CODEX_SEQ`, the exact stopped PIDs/PGIDs and the remaining state. That reply uses
`IN_REPLY_TO: <interrupt SEQ>`, answers both the superseded instruction and the interrupt, and Core
then waits. An invalid or stale interrupt signals nothing, pauses new work, is
reported as an exact refusal in one combined reply, and Core waits.

Commands expected to exceed 30 seconds run in a named background process group; Core records
its ownership and stays mailbox-responsive, and no foreground sleep or wait exceeds 15 seconds
while work is in flight. Only the existing mailbox and monitor are used.

## Core monitor and sending

Core must poll its incoming mailbox; Codex uses the event watcher above and
must not poll.

* Core publishes only through
  `/home/faisal/.core827_backups/sendgate/send_gated.sh`; it validates claims,
  archives the message, renames atomically, and byte-checks delivery. Invoke it
  with exactly five arguments:

  ```text
  /home/faisal/.core827_backups/sendgate/send_gated.sh <draft> <claims.tsv> <ack-lines> <archive_copy> <dest>
  ```
* Core keeps exactly one 30-second monitor on `CODEX_TO_CORE.md` and atomically
  archives each new Codex message. It publishes no heartbeat: one incoming
  Codex message receives one Core mailbox reply. Check the exact monitor
  signature with:

  ```bash
  pgrep -af '[C]ODEX_TO_CORE\.md.*archive_CODEX_.*sleep 30'
  ```

  Expect exactly one row. The broader mailbox-only pattern can match an
  unrelated process. If no row exists, start exactly one copy in a persistent
  background terminal:

  ```bash
  mailbox=/home/faisal/.core827-orchestrator/CODEX_TO_CORE.md
  monitor_log=/home/faisal/.core827_backups/mailbox_archiver.log
  baseline=$(sha256sum "$mailbox" | cut -d' ' -f1)
  printf '%s ARMED baseline %s SEQ %s\n' \
    "$(date '+%F %T')" \
    "${baseline:0:16}" \
    "$(sed -n 's/^SEQ:[[:space:]]*//p' "$mailbox" | head -n 1)" \
    >> "$monitor_log"
  while true; do
    if [ -r "$mailbox" ]; then
      current=$(sha256sum "$mailbox" | cut -d' ' -f1)
      if [ "$current" != "$baseline" ]; then
        seq=$(sed -n 's/^SEQ:[[:space:]]*//p' "$mailbox" | head -n 1)
        archive=/home/faisal/.core827-orchestrator/archive_CODEX_${seq}.md
        cp "$mailbox" "$archive.tmp" && mv "$archive.tmp" "$archive"
        if cmp -s "$mailbox" "$archive"; then
          result=archived
        else
          result=ARCHIVE_MISMATCH
        fi
        printf '%s CODEX MAILBOX CHANGED sha %s SEQ %s %s\n' \
          "$(date '+%F %T')" "${current:0:16}" "$seq" "$result" \
          >> "$monitor_log"
        baseline=$current
      fi
    fi
    sleep 30
  done
  ```

  Never use `ps ... | grep -c`: it counts displayed lines rather than monitor
  processes.
* Core's armed stop hook prevents that Core session from ending with the newest
  Codex instruction unanswered. The hook does not wake Codex.
* Core carries forward a superseded conclusion in the next message and names
  its archive, so one-mailbox replacement loses no decision.

## End condition

Keep the watcher, goal, and message cycle active through the ordered roadmap.
Stop only when that roadmap is complete, it explicitly requires owner approval,
or Core reports a genuine unresolved safety conflict. Stop the watcher only
when no further Core coordination is planned.
