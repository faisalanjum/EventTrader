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
ACTION: <action>
TYPE: <short purpose>
```

The two senders have separate counters. `IN_REPLY_TO`, not matching counter
values, joins the conversation.

## Start or resume a Codex session

1. Read this file, `Steps.md`, the active step, and its named live authorities.
2. Read both current mailboxes before doing anything else.
3. Record both `SEQ` values, Core's `IN_REPLY_TO`, and the mailbox hashes.
4. If Core's `IN_REPLY_TO` does not name Codex's current `SEQ`, reconstruct the
   missing chain from `archive_CORE_*.md` and `archive_CODEX_*.md`; do not guess.
5. Check the one event watcher below. Reuse it if present; start it only if
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
  long work.
* Core's armed stop hook prevents that Core session from ending with the newest
  Codex instruction unanswered. The hook does not wake Codex.
* Core carries forward a superseded conclusion in the next message and names
  its archive, so one-mailbox replacement loses no decision.

## End condition

Keep the watcher and message cycle active until the current step is verified or
Core reports a precise blocker requiring the owner. Stop the watcher only when
no further Core coordination is planned.
