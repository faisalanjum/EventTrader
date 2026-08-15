# Step 0 — Protect and publish the starting point

## Purpose

Create one trustworthy starting version for all later work without absorbing anything from the heavily changed working folder.

Step 0 changes no behavior. It only:

1. publishes the exact reviewed roadmap as a documentation-only commit;
2. verifies the pending status-document update;
3. publishes that document in a second documentation-only commit;
4. freezes the exact starting code for Step 1.

## Current starting state

Measured from `git status --porcelain=v1` on 2026-08-14. Git may collapse an
untracked directory into one status entry, so the numbers below are status
entries, not a claim about the number of files inside those directories.

* Branch: main

* Local and saved remote commit: 0dd71956e942c889c70fede4e547f4737a39cff0

* Tree: 9f80af23f037f68d0a4233b1d752421963549011

* Staged files: 0

* Changed tracked status entries: 140

* Untracked status entries: 778

* Total visible working-folder status entries: 918

* Step 0 roadmap target: the 21 named roadmap files under
  `.claude/plans/Drivers/FinalDesign/LeftOverSteps/`—`Steps.md`,
  `promptStandard.md`, `step0.md` through `step14.md`, and
  `Archived/step1Done.md` through `Archived/step4Done.md`

* Step 0 status target:
  `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md`

* Published file identity: e2fe1a7566e7b75a137b01684ee19ce50e61da0c

* Pre-ruling proposed file identity:
  97dc26acdb921afdbaa938985a8665c670dcd0b8

* Pre-ruling proposed difference: 178 added lines and 12 removed lines.

The proposed status identity and difference must change only to record the
later Sonnet 5 master pre-authorization. Measure all identities and counts
again immediately before review and explain every other movement.

## Exact permitted scope

Step 0 has two exact publication packages:

1. the 21 roadmap files named above;
2. `/home/faisal/EventMarketDB/.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md`.

Review, commit and publish them separately. Everything else—including
production code, tests, contracts, experiments, settings and unrelated deleted
files—must remain untouched and unstaged.

## Authority order

Verify status claims against:

1. FINAL_DESIGN.md — system meaning.
2. ChannelContract.md and ChannelContractV2.md — old and staged-new public formats.
3. 15_CandidateFactPacket.md — current internal format.
4. BUILD_AND_OPERATIONS.md — build and release order.
5. FableExperimentPlan.md and FableExperimentWorkOrder.md — experiment rules.
6. Signed experiment results, exact Git objects, live code and raw test receipts.

STATUS_AND_HISTORY.md, handovers, comments and old reports cannot prove their own claims.

## Work

### 0A. Publish the reviewed roadmap first

1. Derive the exact 21-path manifest from the names above and reject any missing
   or extra path.
2. Confirm every path is documentation under `LeftOverSteps/`; no production,
   test, contract, status or unrelated path may enter the candidate.
3. Stage exactly those 21 files, record every staged file identity and the
   staged tree, and run reference, formatting and patch checks.
4. Send the exact path manifest, file identities and staged tree to Codex.
5. Codex must return either `VERIFIED` or one bounded `CHANGES_REQUIRED` verdict
   tied to that exact staged tree. Silence is never approval. After any change,
   restage and review the new exact identity.
6. Preserve the verified roadmap identity; do not commit or push it until the
   separate status package below is also verified.
7. Audit the status package separately against the live authorities.

Do not substitute an untracked or external copy: later clean sessions must be
able to recover the complete reviewed roadmap from the repository.

### A. Freeze the review input

1. Confirm main, local commit, local tree and origin/main.
2. Confirm the staging area is empty.
3. Record the complete working-folder status.
4. Record the current status-file identity and compare it with the pre-ruling
   97dc26ac… candidate; permit only the reviewed Sonnet 5 ruling update plus
   independently verified factual corrections.
5. Preserve every unrelated working-folder change.

If the commit, target file or staging area differs, stop and report the new identities.

### B. Audit every changed factual claim

Account for every added or modified claim in the status-document difference:

* commit and tree identities;
* contract identities and which format is active;
* completed, dormant, missing and pending components;
* test totals and test identities;
* experiment state and the Sonnet 5 high-effort master pre-authorization;
* database counts and their measurement date;
* graph-write state;
* Fiscal and Core publication identities;
* the remaining sequence;
* every recorded owner decision.

For every claim:

* prove it from the current authority, live code, exact Git object or hash-bound receipt;
* preserve the measurement date when evidence is historical;
* write unknown when current evidence is unavailable;
* remove or weaken any statement stronger than its evidence;
* stop if the proposed update creates or changes a rule instead of merely recording status.

Do not rerun old work merely to support a status sentence. Remove an unsupported sentence instead.

### C. Check the final document

Require all of the following:

* it records status and history only;
* it creates no new behavior, threshold, exception or build rule;
* it does not reopen completed work;
* it clearly says the new format is staged but inactive;
* it clearly says database writes remain disabled;
* it clearly says the language-reader exam kit is frozen but the paid exam has not run;
* every database number is marked as the dated August 12 measurement, not a current count;
* the next bounded model run is pre-authorized only for Sonnet 5 at high effort
  under `Steps.md`;
* file references exist;
* formatting checks pass;
* no application test is required because production behavior did not change.

### D. Freeze the publication candidate

Stage exactly the status document, then prove:

* staged path count: 1;
* staged path: exactly STATUS_AND_HISTORY.md;
* staged file identity equals the reviewed file identity;
* no production file, test, contract, roadmap file or unrelated content is staged;
* the staged difference has no whitespace or patch errors;
* the staged tree is recorded for independent review.

Core then sends the exact staged file identity, staged tree and difference
summary to Codex. Codex must return either `VERIFIED` or one bounded
`CHANGES_REQUIRED` verdict tied to that exact staged tree. Silence is never
approval. After any change, restage and review the new exact identity.

### E. Publish the completed step

After both packages are independently verified:

1. Restage the exact reviewed 21-file roadmap identity and create its
   documentation-only commit.
2. Stage the exact reviewed status-file identity and create its separate
   one-path documentation-only commit.
3. Confirm both commits and their order match the reviewed packages.
4. Push both normally to main under the standing completed-step ruling; never
   force-push.
5. Verify local HEAD, origin/main and the remote GitHub commit are identical.
6. Record:

   * commit identity;
   * tree identity;
   * status-file identity;
   * remote identity;
   * both exact path counts;
   * unchanged unrelated working-folder counts.

## Prohibited actions

* No production-code or test edits.
* No contract edits or plan edits after the roadmap candidate is verified.
* No model calls or filing downloads.
* No database reads or writes.
* No test-suite reruns.
* No cleanup, restoration or staging of unrelated files.
* No history rewrite.
* No start of Step 1.

## Completion condition

Step 0 is complete only when:

* every changed status claim is verified, dated, or honestly marked unknown;
* the exact 21-file roadmap is committed alone;
* the status document is committed alone in a second commit;
* local and remote identities match;
* all unrelated working-folder changes remain untouched;
* the new published commit and tree are recorded as Step 1’s starting point.

Before every later work package, repeat the shorter safety check: start from that latest published commit in a clean isolated folder, freeze inputs and allowed paths, and reject unexplained file drift.
