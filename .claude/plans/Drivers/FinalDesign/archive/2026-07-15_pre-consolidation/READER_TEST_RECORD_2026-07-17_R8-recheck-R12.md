# READER TEST RECORD — 2026-07-17 — R8 RECHECK for ruling R12 — **PASS 10/10**

**Why this run exists:** the standing R8 policy (STATUS §4, certified inside the run-15 freeze) requires a
rerun with run-15 mechanics whenever rules/contracts/operative mechanics change. **R12** (STATUS §4,
2026-07-17) changed operative law: FS-20 became code-authoritative (12 hard / 79 provisional observed-only
lists in `driver/core/slice_axis_frozen.py`; offline-only correction; the catalog's ~24/~241 counts made
HISTORICAL), supersession row 43 superseded automatic demotion, §11.4 gained the fact-level member-ref
verification text + the complete-list fusion rule and retired `MEMBER_LINK_DEFERRED` for
`MEMBER_LINK_INVALID`, and the §1 dashboard was refreshed (CLI + step 7 built). Owner GO for this paid run
given 2026-07-17 via the round relay ("choose option 2, with the exact order above"); cost stated in
advance (200–400k estimate; actual below); single reader.

- Grading law (LOCKED, unchanged): most-natural parse governs; a false fact on that parse = FAIL; no rescue
  readings; full accumulated checklist (every constructed fact names its driver_state; every stated value
  enumerated; no conditional-emphasis inversions; exact counts/locations never compressed; six-dimension
  home-match verification; cite the clause whose condition the fixture satisfies).
- Records are append-only; this file is new and unique; prior records preserved beside it untouched.

## 1. The tested snapshot — ONE fixed commit

- **Certification binds to commit `0d6c1d0d057f9b7c7a5cb4bcd31d714f09f06763`** = the S3 step-7 bundle
  (slice menu + FS-18/FS-20 in code + the R12 law amendments), committed BEFORE this run per the owner's
  ordered sequence (commit bundle → R8 at that exact SHA → commit record separately → push both).
- Test medium: detached git worktree at that commit (`scratchpad/r12-recheck-worktree`); HEAD verified
  pre- and post-run `0d6c1d0d…`; `git status --porcelain` clean pre- and post-run (0 lines).

### 1.1 The seven pinned hashes (sha256, pinned at the worktree BEFORE the run; `sha256sum -c` AFTER → 7/7 OK)

```
779b87b0de4e6aadd96ad512a4e2638666c3b6b37cd7d4449374a2bec84bbbd8  FINAL_DESIGN.md
9e6ffcbbcbc1a34e3792a1afa37469915ddfe02cbeac20c978cdd09b89292cea  ChannelContract.md
d097d048ac7f1037953c439b8088f74d4b8c453a72a19e442a9d6f3e77f41795  BUILD_AND_OPERATIONS.md
353ae5f942e1e810bad97e0f1ea6706f00557139329057e0f0ce80c7371a25b6  STATUS_AND_HISTORY.md
aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c  15_CandidateFactPacket.md
51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472  FableExperimentPlan.md
57a6b86090083560af476f23125a2f95bbce2e572bb93cc132e9ed6cdff9033e  FableExperimentWorkOrder.md
```

ChannelContract, the packet (`aa7239ed…`), the Plan (its standing byte-pin `51966848…7472`) and the
WorkOrder are byte-identical to the run-15/R11-recheck pins; FINAL_DESIGN/BUILD/STATUS differ from the
R11-recheck pins exactly by the R12 bundle (FS-20 rewrite · R12 ruling + row 43 + 43-labels + dashboard
refresh · §11.4 member-ref/fusion/code-list amendments) — the changed bytes are precisely what this
recheck certifies. The catalog (`Consolidation/XBRL_SliceAxis_Catalog.md`) is NOT among the reader's
seven permitted files and was not supplied, so it carries no pin here (its R12 banner is part of the
tested commit).

## 2. Execution trail

- Reader: ONE blank-context subagent (claude-fable-5), agent id `ab0637be620b36baa`, 236,676 tokens,
  11 tool uses (file reads only), 306.3s, **first answering attempt — graded on its first produced output**.
- Prompt: byte-identical to the run-15 official R7-amended set (§5 of the run-15 record) with `<DIR>` =
  the worktree's FinalDesign path. No other change.
- Suites at the tested commit (run pre-commit, main session): driver core **392 passed, 1 skipped**
  (opt-in probe); workflows Track A **265 passed, 1 skipped**; live read-only **10 passed**.

## 3. The reader's ten answers — VERBATIM

Preserved byte-identically in the session transcript (agent `ab0637be620b36baa` final output). Spliced
highlights that carry the R12-certified delta:

- Q9 HISTORICAL: "the **43 supersession rows'** dead rules kept once for audit (STATUS §3) · … ·
  **FS-20's ~24/~241 catalog counts (FD §5.2)**" — the reader classifies the old catalog counts as
  historical and reads the new row count, exactly the R12 change.
- Q10: "… OD-1..21, K2, **the 43 supersession rows**, Contract clauses §1-§9, packet blocks 0-3 …" —
  the amended ledger count again, in the crosswalk enumeration.
- Q2 write step: "dry-run is the DEFAULT — real writes need `ENABLE_DRIVER_WRITES` and **today writes
  are disabled** (BUILD §5/§11.4; STATUS §1)" — read from the refreshed dashboard row.
- All ten answers otherwise track the R11-recheck certified content (glossary/over-merge law, fixture
  walk with `product:iphone` + `percent_yoy` + `increased`, five lane examples each naming driver_state
  with six-dimension home matches, slot order + ten hashed slots + all hash cases, 24 fields 6/18,
  slices/names/portions with the OD-17 exceptions, absent-better-than-wrong links, submission-vs-packet,
  status inventory, and the §7/§7.1/§7.1b/§7.2/§8 maps).

## 4. Per-question grades (locked rule + full checklist applied)

1. PASS — Driver/DriverUpdate/asymmetric law with citations; nothing false.
2. PASS — full pipeline walk; every value enumerated (42,600 `m_usd`; 12 `percent_yoy`;
   `comparison_baseline=prior_year`); state named (`increased`); the OD-11 YoY clause cited as the
   mechanism its condition satisfies; bare-id ladder case correct; writes-disabled status correct.
3. PASS — five examples, each naming its own driver_state (`increased` · `raised` · `beat` · `in_line` ·
   `announced`); both surprise homes constructed (`reported`; `unknown`) with the six-dimension match
   shown; forbidden fields per lane enumerated; the P3 range-contains-consensus clause cited for
   `in_line`.
4. PASS — slot order exact; the ten hashed slots exact; every hash case stated incl. the pre-batch rule,
   all-hashed in-batch conflicts, compatible-but-not-exact PARKS, and the two-competitors park.
5. PASS — 24 fields exact (6 code / 18 semantic); `disputed` correctly outside the count.
6. PASS — NAME-10/11 local role test, NAME-16 carve-out, OD-17 portions with BOTH documented exceptions
   (residuals; eliminations drop-and-log keeping the affected real fact).
7. PASS — abstention ladder; wrong-worse-than-absent with the silent-damage rationale; XC-18 revocation
   correctly attributed as ratified-dormant.
8. PASS — boundary vs packet; forbidden channel fields; blocks 0-3; three consumers; frozen sha quoted.
9. PASS — all eight status buckets from the owning STATUS §2 lists, quoted faithfully; the R12 delta
   (43 rows; catalog counts historical) correctly placed. *Transparent grading note:* the reader lists
   "slice table materialization + PIT menu code" and "the whole Track B writer/validator/CLI/park-ledger
   stack" under FINAL/BUILD-PENDING — a faithful quote of STATUS §2, whose master list was not part of
   the ordered dashboard refresh and still carries the pre-step-7 wording. That is a document-sync
   residual of the tested snapshot, not a reader error (the grading law scores the reader's parse of the
   files as they stand). Logged for the next law pass.
10. PASS — §7 / §7.1 (+total-coverage law) / §7.1b / §7.2 / §8 all named with correct content; the
    MANIFEST byte facts exact (33 sources; 11,320 lines / 1,362,208 bytes; 32 source copies + evidence
    files).

## VERDICT: **PASS 10/10** — under the R7-amended official set, the locked grading rule, and the full checklist.

The R12 law changes read correctly to a blank-context engineer at commit `0d6c1d0d…`. One residual for the
next law pass (no rule meaning involved): STATUS §2's FINAL/BUILD-PENDING master list still carries
pre-step-7 wording for the Track B stack and the slice-table/PIT-menu items; §1's dashboard is current.
