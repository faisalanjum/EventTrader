# ADDENDUM — R8-PER21 arc: corrected execution trail, both answer sets graded, full exit-coded battery

**Owner ruling (2026-07-22, Option A): the explicitly approved, model-pinned Fable run is the OFFICIAL R8
run; the unpinned Opus output remains disclosed as 9/10 evidence and is NOT the certification run.** This
addendum corrects the false/imprecise execution-trail statements in
`READER_TEST_RECORD_2026-07-22_R8-PER21-run2.md` (that file and all prior records stay unedited,
append-only law). This commit adds ONLY this file; no tested file is touched.

## 1. The corrected, verified timeline (session log + subagent transcripts; all UTC)

| Time | Event |
|---|---|
| 23:53:45 | Rerun reader spawned WITHOUT a model pin → harness default resolved to `claude-opus-4-8` |
| 23:59:57 | Its transcript's last record at that moment: an empty 2-token assistant message (API overload mid-retry). **Core read the file here and wrongly reported "terminated, zero answers"** |
| **00:01:46.983** | **The Opus reader's retry SUCCEEDED — complete ten-answer set (22,475 chars) landed** |
| 00:01:47.067 | Its completion (idle) ping fired. **Core dismissed it as a "delayed" notification without re-reading the file — the operative error (the standing verify-at-completion-marker rule, 2nd occurrence of this class)** |
| 00:02:38.520 | Owner GO for the Fable-pinned relaunch — **given while Core's stale "zero answers" statement stood uncorrected** |
| 00:03:05.636 | Fable reader spawned (model explicitly pinned; verified `claude-fable-5` from transcript metadata) |
| 00:11:08 | Fable reader completed its ten answers (19,556 chars) |

Mitigations of record, not excuses: the Fable pin was PROPOSED before 00:01:46 (before any Opus answers
existed — provable by message order), and the Fable reader was blank-context reading only the seven
worktree files, so no answer set influenced the other.

## 2. Both answer sets, graded under the locked rule (most-natural parse, no rescue readings)

- **Fable set (OFFICIAL, per the owner ruling): PASS 10/10** — grades as recorded in
  `…R8-PER21-run2.md` §3, re-affirmed on regrade. Q2 states the decisive point explicitly correctly:
  "no `MAPS_TO_MEMBER` (no axis+member supplied)".
- **Opus late set (disclosed evidence, NOT certification): 9/10 — Q2 FAIL.** Its write step ties
  `MAPS_TO_MEMBER` carrying `slice_part=product:iphone` to the text-only fixture, with no XBRL axis+member
  and under a citation (§4.1/§5.1) whose condition the fixture does not satisfy — the same clause the
  withdrawn first run failed.
- **⚠ CLARITY WARNING (recorded for the next law pass, no rule change made here):** two independent Opus
  readers failed the SAME clause the same way — asserting a member link for a text-only fact — while the
  Fable reader stated the exclusion explicitly. If a future owner pass wants weaker readers to hold this
  rule, the member-link enrichment wording (the "needs both axis and member, may be absent" clause vs
  §7.3's "zero-or-more on any lane") is the sentence pair to consider tightening. Empirical: Opus 0-for-2
  on this clause; Fable 1-for-1.

## 3. Trail corrections to the run2 record (each verified)

1. "terminated … ZERO answers" → FALSE as history: the Opus attempt COMPLETED all ten answers at
   00:01:46.983, before the Fable spawn. (True only of the mid-retry snapshot Core read.)
2. "12 tool uses" for the graded run → **11 Reads** (the Opus runs had 12 each; the number was copied from
   the wrong run).
3. Arc reader cost → **~760k tokens** (run1 240.4k + opus-rerun 238.6k + fable 281.0k, each = final
   context read + total output), not the ~720k reported in session (the Opus rerun was summed from its
   mid-run snapshot).
4. The owner's relaunch GO rested on the uncorrected "zero answers" statement — disclosed above with the
   exact timestamps.
5. Model-fidelity note re-affirmed: no explicit pre-run written rule mandated the reader model; the
   requirement rests on the "run-15 mechanics" reading (every certified record's reader was
   `claude-fable-5`) + the owner's explicit in-session pin approval, and the owner's Option-A ruling now
   settles it for this arc.

## 4. Corrected battery evidence — the COMPLETE run-15 battery, every command's own exit code

The session batteries behind the earlier records showed full pass-lines but piped through `tail -1`,
so per-command exit codes were not separately recorded — the run-15 requirement ("every check tests its
own exit status") was not met by those runs. Corrected 2026-07-22 at a fresh detached worktree,
HEAD `8bc587e94c5a17bfccf5d4323e5b01d1394b7db0`, 0 dirty lines, via the `ck` helper
(`out=$("$@" 2>&1); rc=$?`; script exits nonzero on any failure; script preserved at scratchpad
`per21_addendum_battery.sh`):

```
PASS (rc=0): 1. 7/7 pinned hashes (sha256sum -c, exit-checked)
PASS (rc=0): 2. Plan byte-pin (51966848...7472)
PASS (rc=0): 3. WorkOrder sha == board-recorded current sha AND appears on the board
PASS (rc=0): 4. Manifest 33/33 byte-verified (29 archive + 3 snapshots + Plan at root)
PASS (rc=0): 5. Root layout = exactly the 7 sanctioned files + archive/
PASS (rc=0): 6. Workflow drift-guard suite (Track A): exit 0 AND '266 passed, 1 skipped'
PASS (rc=0): 7. Driver core suite: exit 0 AND '392 passed, 1 skipped'
PASS (rc=0): 8. DriverDesign coverage gate: exit 0 AND '9 passed'
PASS (rc=0): 9. Live read-only suite: exit 0 AND '10 passed'
BATTERY: ALL 9 CHECKS GREEN   (script exit 0)
```

## 5. Standing-state correction

The session claim "Core's only remaining hold is the rehearsal harness" was misleading and is corrected:
substantial Core build work remains (~65% to full production by the owner-agreed planning number), and the
Fiscal FinalPlan Phase-5 four narrow Core gates require the owner's separate approval before any Core work
under that plan. Push remains blocked (owner order + the Fiscal FinalPlan standing hold).

**Net effect: the official R8 for the PER-21 law bytes stands as the Fable run's PASS 10/10 with 7/7
unchanged pins at `8bc587e` (the STATUS §4 conditional discharge condition), now with a truthful trail and
a fully exit-coded battery behind it.**
