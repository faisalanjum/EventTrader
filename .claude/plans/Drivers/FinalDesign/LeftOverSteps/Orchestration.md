# Core ↔ Codex communication

This file defines transport only. `Steps.md`, the active step file, and the
live design documents define the work. The `core827` directory name is
historical; its old `PROTOCOL.md` task restrictions are not current Driver law.

## Roles

* Core (Claude) implements and writes the repository.
* Codex independently reviews and orchestrates; it does not launch Core.
* The owner approves the actions reserved in `Steps.md`.

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

Neither side reads, copies, or invents the other's id.

Before a new session sends, it derives its next `SEQ` as one greater than the
highest `SEQ` header in its current outbound mailbox and all archives for its
role under `.core827-orchestrator`, `.core827_backups`, and
`.core827_backups/sendgate`. It never resets or reuses a number. Its
`IN_REPLY_TO` is the exact current peer `SEQ` it read.

The current sessionless mailbox messages may be used once as the legacy record
from which the first bound messages continue. After that migration, a missing
`SESSION` is invalid.

A new session's first outbound message is `TYPE: SESSION_HANDOVER`; when its
first outbound is answering the peer's handover, it uses
`TYPE: SESSION_HANDOVER_ACK`, which also serves as its own handover. Both use
`ACTION: WAIT` and carry the sender's `SESSION`, derived `SEQ`, exact
`IN_REPLY_TO`, current repo HEAD, and hash of the incoming peer message. An ACK
must reply to the exact handover `SEQ`. No work starts until each side has
published its own id and read the other's id. If both handovers cross, each
side sends one exact ACK before work.

Core claims-backs every `SESSION` line passed through `send_gated.sh` by freshly
reading line 1 of `G3_CONTINUOUS_RUN`; otherwise the send linter correctly
rejects the unproved id.

After binding, a `SESSION` value that changes without a `SESSION_HANDOVER` is
reported, not answered: it means a session was replaced silently and the
conversation state may be wrong.

## Start or resume a Codex session

1. Read this file, `Steps.md`, the active step, and its named live authorities.
2. Read both current mailboxes before doing anything else.
3. Record both `SEQ` values, Core's `IN_REPLY_TO`, and the mailbox hashes.
4. If Core's `IN_REPLY_TO` does not name Codex's current `SEQ`, reconstruct the
   missing chain from `archive_CORE_*.md` and `archive_CODEX_*.md`; do not guess.
5. Derive Codex's next `SEQ` from the current mailbox and all archives as
   defined above; verify that `CODEX_THREAD_ID` is nonempty.
6. Complete or acknowledge the session handover. Do no review or work until the
   two sessions are bound.
7. Check the one event watcher below. Reuse it if present; start it only if
   absent. More than one is an error to report, not a reason to start another.

## Codex's proven cheap watcher

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

## Core side, verified

Core's existing rules are correct with one correction: Core polls its incoming
mailbox; Codex uses the event watcher above, so both sides do not poll.

* Core publishes only through
  `/home/faisal/.core827_backups/sendgate/send_gated.sh`; it validates claims,
  archives the message, renames atomically, and byte-checks delivery.
* Core keeps exactly one 30-second monitor on `CODEX_TO_CORE.md`, archives each
  new Codex message, and sends a factual heartbeat every ten minutes during
  long work. Check the exact monitor signature with:

  ```bash
  pgrep -af '[C]ODEX_TO_CORE\.md.*archive_CODEX_.*sleep 30'
  ```

  Expect exactly one row. The broader mailbox-only pattern can match an
  unrelated process. If no row exists, start exactly one copy in a persistent
  background terminal:

  ```bash
  cd /home/faisal/.core827-orchestrator
  last=$(sed -n 's/^SEQ:[[:space:]]*//p' CODEX_TO_CORE.md | head -n 1)
  while true; do
    cur=$(sed -n 's/^SEQ:[[:space:]]*//p' CODEX_TO_CORE.md | head -n 1)
    if [ -n "$cur" ] && [ "$cur" != "$last" ]; then
      cp CODEX_TO_CORE.md "archive_CODEX_${cur}.md"
      printf 'CODEX REPLIED SEQ %s: %s | %s\n' \
        "$cur" \
        "$(grep -m1 '^ACTION:' CODEX_TO_CORE.md)" \
        "$(grep -m1 '^TYPE:' CODEX_TO_CORE.md)"
      last=$cur
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

Keep the watcher and message cycle active until the current step is verified or
Core reports a precise blocker requiring the owner. Stop the watcher only when
no further Core coordination is planned.
