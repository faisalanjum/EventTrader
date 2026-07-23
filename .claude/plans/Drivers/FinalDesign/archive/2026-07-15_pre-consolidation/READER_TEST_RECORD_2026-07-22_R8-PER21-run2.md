# READER TEST RECORD — R8-PER21 RERUN ("run2" of the correction plan) — **PASS 10/10**

**This is the record named by STATUS §4's conditional discharge sentence.** It records PASS 10/10 with 7/7
unchanged pins at commit `8bc587e94c5a17bfccf5d4323e5b01d1394b7db0` — the pre-test correction/freeze commit
whose STATUS carries that sentence. By that sentence's own condition, the PER-21 R8 obligation is
DISCHARGED by this record with no further edit to any tested file (the run-15 pointer-before-record
mechanism). This commit adds ONLY this file.

## 1. The tested snapshot

- Commit `8bc587e…` = the law bytes of the PER-21 law commit `c87d81b` (FINAL_DESIGN, ChannelContract,
  BUILD, packet, Plan, WorkOrder all byte-identical — six pins equal) + the STATUS correction/conditional
  sentence (the only changed file vs `c87d81b`). The first run's PASS was withdrawn by the appended
  CORRECTION record; the original first-run record is preserved unedited.
- Test medium: detached worktree `scratchpad/per21-r8-run2-worktree`; HEAD verified `8bc587e…` and
  `git status --porcelain` = 0 lines PRE and POST run. Suites AT this commit, run pre-test: coverage
  **9 passed** · driver core **392 passed, 1 skipped** · Track A **266 passed, 1 skipped** · live
  read-only **10 passed**.

### 1.1 The seven pinned hashes (pinned BEFORE the reader; `sha256sum -c` re-verified before the retry
spawn AND after the run → 7/7 OK each time)

```
fd4971538d82da00ed79f52a25d50a842537e0e8fd3ac725b4390ccd2ee71507  FINAL_DESIGN.md
1062e0fb1b58b4311bb4a03d0a4a42274288c460d22f74a8f75cc803bb04b0dd  ChannelContract.md
b23e225a711a947091c2c64efd501a863dfb05fbb8e668c3e03eb837606f52d5  BUILD_AND_OPERATIONS.md
c842fe985d815ea8877a25853f18b42ceb636fcacbef7248f7c587cb2fbd1660  STATUS_AND_HISTORY.md
aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c  15_CandidateFactPacket.md
51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472  FableExperimentPlan.md
57a6b86090083560af476f23125a2f95bbce2e572bb93cc132e9ed6cdff9033e  FableExperimentWorkOrder.md
```

## 2. Execution trail — full disclosure

- **Attempt 1 (dead, non-influencing):** spawned WITHOUT a model pin; the harness default resolved to
  `claude-opus-4-8` (spawn metadata). It read all seven files (~202k) then terminated during the final
  answer request (API overload; the CLI showed retry backoff; final assistant message = 2 tokens, ZERO
  answers). Under the run-15 precedent ("two earlier attempts produced NOTHING … neither influences
  grading") a zero-answer termination is a non-attempt; the first-attempt grading rule binds to the first
  PRODUCED answer set.
- **Model-fidelity disclosure (owed):** while diagnosing attempt 1, spawn metadata showed the FIRST run's
  reader (the withdrawn 07-22 PASS) had ALSO executed on `claude-opus-4-8`, though its record states
  "claude-fable-5" — a false statement in that record, made by copying precedent phrasing without
  verifying metadata. That record stays unedited (append-only); this disclosure corrects the trail. All
  certified R11/R12/run-15 readers ran `claude-fable-5`; run-15-mechanics fidelity therefore requires the
  fable reader, and the owner ordered the model pinned explicitly.
- **Attempt 2 (THE graded run):** owner GO; model EXPLICITLY pinned and verified from the transcript:
  `claude-fable-5`. ONE blank-context subagent, named `per21-r8-run3-reader`, transcript
  `subagents/agent-aper21-r8-run3-reader-3fa1ab3794693f3a.jsonl`; ~203,658 tokens read (cache-read max),
  77,297 output; 12 tool uses — ALL file reads confined to the seven permitted paths (access audit clean;
  it survived a mid-run API overload via the CLI's automatic retry). **First produced answer set — graded
  on that output**, spliced byte-identically from the transcript JSONL to scratchpad
  `per21-r8-run3-answers.md`; the reader was never re-asked.
- Prompt: byte-identical to the run-15 official R7-amended set, `<DIR>` = the worktree path. No hint of
  the first run's failure exists in any tested file (STATUS names the failure only at pointer level; the
  detail lives in archive/, which the prompt forbids the reader to open).

## 3. Grades (locked rule — most-natural parse, no rescue readings — + the full checklist)

1. PASS — Driver/DriverUpdate; born-complete WITH the latent-base-anchor exception stated; asymmetric law;
   quarantine recovery; zero-tolerance merge direction. Citations throughout.
2. **PASS — the decisive question.** Full walk with every value enumerated (42,600 `m_usd` via the
   glued-billions clause; +12 `percent_yoy` citing OD-11's explicit YoY clause; `prior_year`);
   `driver_state=increased` named; PER-21 placed upstream of fact-period resolution with BOTH routes and
   the no-third-matcher bar; identity/fusion/no-hash correct; **the write edge list is exactly
   `OF_DRIVER`/`FROM_SOURCE`/`HAS_PERIOD` with the member edge explicitly EXCLUDED — "no `MAPS_TO_MEMBER`
   (no axis+member supplied)" — the precise point the withdrawn run failed**; dry-run status read from
   STATUS §1; full nine-part series key.
3. PASS — five examples each naming driver_state (`increased` · `raised` · `beat` · `beat` · `announced`);
   both homes constructed with all six match dimensions enumerated; the bare-guide home correctly takes
   `driver_state=unknown` (no stated movement) with the §4.2 Q5 first-fact exemption cited; "ahead of"
   adjudicated through the OD-13 polarity mechanism whose condition the fixture satisfies; F7 tense noted;
   forbidden fields enumerated per lane.
4. PASS — slot order exact; the ten hashed slots exact; every mint and non-mint case incl. both park
   shapes; probe forms; invariants; late-history never re-keyed.
5. PASS — 24 = 6 code + 18 semantic, exact; `disputed` outside the count.
6. PASS — NAME-10/11 with the §5.2 population test; NAME-15/16 carve-out; no vendor kind;
   unclear→name; OD-17 portions incl. permanent-refusal supersets and eliminations dropped+logged.
7. PASS — abstention ladder; member link needs axis+member and may be absent; silent-damage asymmetry;
   revocation stops only future harm; the rejected-forever list.
8. PASS — boundary vs packet; forbidden channel fields; Blocks 0-3 with Block-1 transient/never-channel;
   frozen sha `aa7239ed…`; current-location vs destination distinguished; evidence_atom unification;
   three consumers.
9. PASS — all eight buckets quoted faithfully from the owning STATUS §2 lists AT this commit, including
   the PER-21 delta (pairing CLOSED · financial classification OPEN, NO field · the retired WP1-correction
   item absent) and the source-33 current-vs-destination distinction.
10. PASS — §7 / §7.1 (+ the coverage law) / §7.1b / §7.2 named with what each maps; §3 rows + §8 manifest
    as supporting maps; the live-at-root vs archive-destination cases distinguished.

## VERDICT: **PASS 10/10 · 7/7 unchanged pins — the STATUS §4 conditional discharge condition is MET.**

The PER-21 + financial-classification law changes read correctly to a blank-context engineer, on the
certified reader model, with the first run's failure point answered explicitly correctly. Push remains a
separate owner decision (the Fiscal FinalPlan standing hold also applies).
