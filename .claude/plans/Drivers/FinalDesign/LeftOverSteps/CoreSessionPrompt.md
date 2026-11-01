# Core session startup

ONE-USE HANDOVER NOTE. Not part of Step 0's frozen 21-file roadmap package, and
deliberately untracked. Its section 5 is temporary state that goes stale
immediately: verify every line of it before relying on it, and delete this file
once the handover is complete.

You are Core. You implement and write this repository. Codex independently
reviews and orchestrates. The owner approves the actions `Steps.md` reserves to
him.

Follow this file in order. It carries no Driver rules: the live documents it
names are the only authority, and where this file and a live document disagree,
the live document wins.

## 1. Bind this session

1. Verify `CLAUDE_CODE_SESSION_ID` is nonempty. Write that exact value as line 1
   of `/home/faisal/.core827-orchestrator/G3_CONTINUOUS_RUN`, keeping the
   remaining lines, then verify the two values match. Never use
   `CODEX_COMPANION_SESSION_ID` as Codex's id; despite its name, it identifies
   this Core session.
2. Confirm the exact incoming-mail monitor with
   `pgrep -af '[C]ODEX_TO_CORE\.md.*archive_CODEX_.*sleep 30'`. Exactly one row
   must appear. If none appears, start the exact monitor in `Orchestration.md`.
   If more than one appears, report it; never start another.

## 2. Read, in this order

1. `LeftOverSteps/Orchestration.md` — transport, session binding, sending.
2. `LeftOverSteps/Steps.md` — the roadmap and every reserved approval.
3. `LeftOverSteps/step0.md` — the active step.
4. `LeftOverSteps/promptStandard.md` — how to write any prompt you produce.
5. Both mailboxes in `/home/faisal/.core827-orchestrator/`, then the highest
   `archive_CORE_*.md` and `archive_CODEX_*.md`.

Record both current `SEQ` values and the repo HEAD before doing anything else.

## 3. Announce yourself before any work

Derive your next `SEQ` exactly as `Orchestration.md` requires. Send one
`TYPE: SESSION_HANDOVER` message through
`/home/faisal/.core827_backups/sendgate/send_gated.sh`, carrying your `SESSION`,
your derived `SEQ`, the last Codex `SEQ` as `IN_REPLY_TO`, the current HEAD, and
the incoming Codex-message hash. Add a send-gate claim that freshly reads line
1 of `G3_CONTINUOUS_RUN` and proves the `SESSION` value. Wait for an exact
`TYPE: SESSION_HANDOVER_ACK` carrying Codex's own `SESSION`. Until the binding
is complete, do no step work.

## 4. Your bounded task

Complete Step 0 sections B, C and D exactly as `step0.md` defines them, for
`.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md` only.

Section A is already satisfied and section 0A (the roadmap files) is already
published. Re-measure every identity yourself; do not trust the numbers recorded
in `step0.md` or below.

Prohibited until Codex returns `VERIFIED` on your exact staged tree: commit,
push, model call, source fetch, database read or write, test rerun, and any edit
to a second file. Preserve every unrelated working-folder change; stage exactly
one path.

## 5. State carried into this session

Verify each of these before relying on it.

* Bridge position: Core `SEQ 1005` (`ACTION: BLOCKED`) answered Codex
  `SEQ 1187` (`ACTION: CHANGES_REQUIRED`). Codex has not replied to 1005.
* The status document is unstaged and unpublished. Its pending edit is the
  correction `step0.md` requires: record that `Steps.md` pre-authorizes model
  calls bounded by a reviewed step, so no separate owner or spending approval is
  needed for them.
* That correction appears in FOUR places in the document, not one. Locate all
  four yourself and fix the class; fixing the first alone leaves the document
  self-contradicting.
* This environment's permission classifier DENIED that edit once, because
  removing "requires fresh owner approval" reads as an agent deleting its own
  spending gate. Do not route around it. If it blocks again, stop and put the
  decision to the owner.
* Evidence already gathered on that point: the commit adding `Steps.md` carries
  no `Claude-Session` trailer, which every agent commit in this repo carries, so
  the pre-authorization is the owner's own ruling and not an agent's.
* CORRECTION OWED TO CODEX, NOT YET SENT. In `SEQ 1005` I claimed the K-fields
  count of 72 drafting calls could not stand because it came from two model
  tiers. That was WRONG and Codex refuted it. `Steps.md` lines 22-24 define
  independence as "separate blind Sonnet 5 calls with no shared response or
  hidden answer", so the doubling comes from reading each event twice
  INDEPENDENTLY, not from tier diversity: 36 events x 2 blind readings = 72,
  now both Sonnet 5 at high effort. **72 stands.** Only the model identity
  changes. Send this correction explicitly; do not silently edit it away, and do
  not carry the wrong claim into the status document.
* Deferred by Codex until after Step 0: one bounded TDD task correcting the
  rule-owner gap in `repair_duplicates.js` and `ab_pair_judge.js`, which carry a
  company-count trigger and hard-coded model pins that conflict with current
  law. Do not start it before Step 0 is verified.

## 6. Stopping

End a turn only when your newest outbound declares `ACTION: BLOCKED`, naming
exactly what is needed and from whom, or when one line in `G3_STOP_REASON` names
`owner` or `codex` and what is needed. That file is single-use and is deleted
when read. Finishing a unit of work is not a stop; silence is never a report.
