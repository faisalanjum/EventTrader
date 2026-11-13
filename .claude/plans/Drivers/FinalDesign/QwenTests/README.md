# Qwen tests — narrow task qualification plan

> **Out of date (note added 2026-11-12).** Kept as history only. The local model now
> defaults to `qwen3.8:27b-fast` at `localhost:11435`; current how-to:
> `.claude/plans/Drivers/FinalDesign/LeftOverSteps/QwenInference.md`.

> **Status: ACTIVE DIAGNOSTICS — 2026-07-24. QF-01 row-v3 passed its opened
> development set: 93/93 exact cells. This is not unseen certification. No
> graph write, production activation, or model-role change is authorized by
> this file.**
>
> This is a moving readiness map, not Driver law. Before any run, re-check the
> live files named in §8. On conflict, `FINAL_DESIGN.md`,
> `ChannelContract.md`, `BUILD_AND_OPERATIONS.md`,
> `STATUS_AND_HISTORY.md`, and the owning experiment/Fiscal plan win.

## 1. Goal and fixed boundary

The goal is to learn, one narrow task at a time, what the local Qwen model can
do with **observed 100% precision and 100% recall**.

Qwen will **never** be asked to discover new Drivers in unseen text. Frontier
models remain responsible for Driver discovery and for creating/adjudicating
hidden answer keys.

For every Qwen task, the input must already identify the target:

- a known Driver or cause;
- a specific evidence block, table, answer, or candidate pair; or
- a bounded menu of allowed choices.

The responsibility split remains:

```text
Fiscal: find and copy exact source evidence
   ↓
Core: name and interpret it, decide reuse/identity/type, then validate/store
```

A Fiscal reader never creates a Driver name or decides identity. Qwen may not
make an identity-changing decision in production merely because it passes a
diagnostic test; the owning experiment and activation gates still apply.

## 2. Qwen evaluation rules

1. **One task at a time.** Do not combine locating, naming, interpretation,
   routing, and identity into one score.
2. **No unrelated batching.** Each call starts with fresh, stateless context.
   For the table screen: one request plus its one complete source table per
   call. For identity: one pair per call. A complete source event may remain
   intact when splitting it would remove evidence needed for a correct answer.
   This is the diagnostic shape only; it does not silently amend Fiscal's
   planned production batching. If Qwen will later receive batches in
   production, that exact batch shape needs a fresh measured test.
3. **Do not test discovery.** A naming test must provide the known cause; a
   locator test must provide the known Driver/anchor.
4. **Freeze before looking at results.** Pin the exact model build, quant,
   runtime, prompt, system text, settings, input hashes, answer-key hash, and
   scorer hash.
5. **Initial settings:** reasoning off, temperature 0, one completed response
   per case. (The former EXP-5 Qwen P6 arm is WITHDRAWN as of 2026-07-25; these settings now govern the separate target-supplied diagnostics below.) A different
   setting is a separate pre-registered test, not a quiet retry.
6. **No semantic repair.** Code may parse, validate, re-pull source spans, and
   reject bad output. It may not change Qwen's chosen row, meaning, Driver,
   route, type, or concept. Any deterministic production wrapper is frozen as
   part of the system under test.
7. **No result retry.** Invalid or wrong completed output counts as failure.
   A transport failure with no usable response stops or resumes the run with
   the incident recorded; it never silently earns Qwen a second answer.
8. **Blindness:** the Qwen process receives only model inputs. Hidden answers,
   gold labels, family names, and scorer conclusions stay in the scorer
   process.
9. **Score once.** After a hidden set is opened for Qwen scoring, prompt
   changes may be developed from the failures, but the same cases cannot then
   certify the changed prompt. Certification needs fresh unseen cases.
10. **Report raw counts.** Always publish correct, wrong, abstained, invalid,
    and total, plus latency and the exact model fingerprint.

### What “100%” means here

It means **zero observed errors on this finite locked set**. It does not prove
that the true error rate is universally zero. Report the independent-case
count and the rule-of-three upper bound beside every zero-error result.

### Result labels

| Result | Meaning |
|---|---|
| `QWEN_ONLY_QUALIFIED` | Every answerable case correct; zero wrong, abstained, or invalid outputs. |
| `SAFE_FIRST_PASS_ONLY` | Zero wrong accepts, but one or more abstentions/misses. Qwen may reduce work only if code verifies accepts and another approved path handles every residual. It did **not** meet the 100% recall bar. |
| `NOT_SAFE_FOR_TASK` | Any wrong accept, wrong merge, invented evidence, or unsupported choice. |
| `NOT_MEASURED` | The key, prompt, runner, or sample is not ready or does not isolate the claimed task. |

## 3. The two next tests

### QF-01 — Fiscal 8-K table evidence screen (ALIGNED 2026-07-25, owner ruling Phase6 plan §6)

**Question:** Given one value-blind anchor and ONE rendered table, can Qwen
return the COMPLETE evidence-ID set stating that Driver — or `[]` to abstain?

**The aligned design (the live `table_evidence/qf01.py`; prepare→verify GREEN)**

- **19 set-based calls** — one per anchor family — covering **93 hidden cells**
  across **8 independent tables** from 7 filings; 93 and 8 are COVERAGE
  figures, never the call count;
- each call = one anchor (audited fixture units: usd / percent / count) + one
  rendered `[En]` table under THE 5×50 `table_solve_prompt`, response =
  `{request_id, evidence_ids}` with `[]` = abstain;
- CODE alone copies and verifies evidence (the 5×50 `verify_set`); the model
  re-types NOTHING — the old copied-label/period-header contract is REFUSED by
  the preflight gate on every command;
- hidden answers are SET-based (mechanically regrouped, fail-closed);
- pass gate: `correct=19, wrong=0, abstained=0, invalid=0`.

**Metrics**

```text
set precision = correct set answers / all non-abstain set answers   (of 19)
set recall    = correct set answers / 19 set calls
(93 appears ONLY as hidden-cell coverage; 8 as independent tables)
```

**What a pass proves:** Qwen can perform this small, bounded table-copy task on
the screen set.

**What it does not prove:** production certification, general 8-K prose
reading, true ambiguity abstention, Driver naming, fact interpretation, or
Core identity.

**Result:** owner-authorized QF-01 completed on 2026-07-24:
`correct=0`, `wrong=92`, `abstained=0`, `invalid=1`; strict precision and
recall were both 0%, so the verdict is `NOT_SAFE_FOR_TASK`. All 92 parseable
answers missed the exact period-header array, revealing a material input/output
design problem as well as real row/cell selection errors. The opened 93 cases
are now development data and cannot certify a tuned prompt. See
`table_evidence/REPORT.md`.

**Choice-v2 result:** `table_evidence/choice_v2/` removes copying and
formatting from Qwen's job. Real source HTML produces every numbered cell;
Qwen returns only a number or `null`; code reconstructs the exact evidence.
All 93 gold cells existed exactly once in the source-built menus. Qwen selected
75/93 exact cells (80.65%); therefore it is not safe alone. See
`table_evidence/choice_v2/REPORT.md`.

**Row-v3 development result:** `table_evidence/row_v3/` shows every source row
once. Qwen selects only the row; deterministic code applies the request's
explicit occurrence and copies the exact evidence. It scored 93/93 with no
wrong, abstained, or invalid result. These opened cases cannot certify the
changed interface; fresh unseen positive, ambiguous, and no-answer tables are
still required. See `table_evidence/row_v3/REPORT.md`.

### QC-01 — Core Driver identity diagnostic

**Question:** Given two already-proposed Drivers with evidence, can Qwen decide
whether they mean exactly the same thing?

**Existing locked preparation**

- `K-pairs.v1.3`: 160 Fable-locked planted pairs;
- 110 gold `DIFFERENT`, 50 gold `SAME`;
- 13 families, including hard low-word-overlap synonyms and dangerous
  high-word-overlap different meanings;
- the prompt contract uses object, scope, and mechanism, with
  default-`DIFFERENT` safety;
- existing blindness and scoring code.

**Qwen run shape**

- one pair per fresh call: 160 calls;
- expose only the two sides' names, quotes, slices, per-X, industry, and the
  three-check rule;
- require one `SAME|DIFFERENT` verdict plus source-grounded citations from both
  sides;
- no batching, answer repair, retry, or exposure of family/gold fields.

**Qualification gate**

```text
gold SAME:       50/50 predicted SAME
gold DIFFERENT: 110/110 predicted DIFFERENT
wrong SAME:       0
false refusal:    0
invalid:          0
```

Equivalently, `SAME` precision and `SAME` recall must both be 100%, with every
gold-different case also protected.

**What a pass proves:** Qwen is viable on this planted identity diagnostic.

**What it does not prove:** EXP-4 production qualification. `K-pairs.v1.3` was
built to qualify graders and includes synthetic-realistic cases. Full
identity-judge testing still needs `K-pairs.v2`, including mined real catalog
pairs and both production evidence shapes.

**Readiness:** hidden key/prompt/scorer **READY**; local-Qwen
runner/manifest and Qwen-specific strict score summary **NOT YET BUILT**.
Qwen is not currently an authorized EXP-4 or production identity judge.

## 4. Full task and answer-key readiness map

`READY KEY` means the hidden answers are usable; it does not mean the Qwen
runner has been approved or run.

| ID | Narrow task | Owner | Qwen role | Answer-key/test status on 2026-07-24 |
|---|---|---|---|---|
| QF-01 | **ALIGNED 2026-07-25 (owner ruling, Phase6 plan §6): one anchor + one rendered [En] table → evidence-ID SET or [] to abstain; code copies/verifies** — 19 set-calls covering 93 hidden cells across 8 tables; every command preflight-gated; prepare→verify GREEN | Fiscal | Diagnostic only | History: the OLD per-cell task scored 0/93 (results/); row-v3 93/93 was development-set only. Fresh unseen cases still required; a model RUN needs its own owner GO. |
| QF-02 | 8-K prose: find exact sentence containing the known Driver's stated number and period | Fiscal | Candidate only after testing | **NOT READY:** 0/50 locked cases. |
| QF-03 | Prepared remarks: find exact spoken known-Driver update | Fiscal | Candidate only after testing | **NOT READY:** transcript corpus has 23 combined prepared-remarks/Q&A candidates, not accepted locked truth. |
| QF-04 | Transcript Q&A: find exact answer containing the known-Driver update | Fiscal | Candidate only after testing | **NOT READY:** shares the same 23 unaccepted candidates. |
| QF-05 | Numberless claim: copy exact sentence for a known claim | Fiscal | Candidate only after testing | **NOT READY:** 0/50 locked cases. |
| QF-06 | Correctly abstain when no unique evidence exists | Fiscal | Candidate only after testing | **NOT READY:** current 93 table requests are all answerable; genuine negative/unresolvable cases are missing. |
| QC-00 | Name a **known** cause under NAME-01..19 | Core decomposer | Intended future diagnostic | **NOT READY:** K-reader v3 has 1,175 locked discovery+name answers, but it does not isolate naming from discovery. A target-supplied naming key is required. |
| QC-01 | Decide whether two proposed Drivers mean exactly the same thing | Core kernel | Planned diagnostic; not production-authorized | **READY KEY:** K-pairs.v1.3 has 160 locked planted pairs. Qwen runner remains. Full K-pairs.v2 is pending. |
| QC-02 | Interpret DriverUpdate fields: meaning, slice, measurement, unit hints, period, state, and fact_type | Core decomposer | **Separate target-supplied diagnostic** (EXP-5 P6 arm WITHDRAWN 2026-07-25 — Qwen runs no EXP-5 discovery arm) | **DRAFTING:** K-fields protocol exists; about 150 gold facts over 36 events are being drafted/adjudicated. No lock yet; no EXP-5 run allowed yet. |
| QC-03 | Route a candidate to `ATTACH`, `ADOPT`, `CLAIM`, `CREATE`, `SKIP`, or `UNSURE` | Core admission router | Not authorized until separately measured | **NOT READY:** K-route files do not exist; needs the finished mini-catalog, candidate pool, and locked 150-case key. `PARK` is a later kernel/writer outcome, not a K-route gold arm. |
| QC-04 | Classify metric, guidance, surprise, or action and confirm base family | Core kernel | Not authorized until separately measured | **NOT READY:** K-stamp files do not exist; needs the Track-A mini-catalog run and locked ~100-case key. |
| QC-05 | Select and verify one XBRL concept from a bounded company menu, or abstain | Core enrichment | Not authorized until separately measured | **NOT READY for Qwen:** prior concept-link evidence/scripts exist, but there is no current locked, model-hidden Qwen key/runner. EXP-6 is mostly text↔XBRL fact-ID convergence; it is **not** a Qwen concept-selection qualification test. |
| QC-06 | Independently challenge a proposed identity/concept match before writing | Core safety/recovery | Never final-authority without its own safety gate | **PARTIAL ONLY:** K-pairs tests skeptical identity judgment; no standalone locked key covers the full safety/recovery challenge. Much of the falsifier is deterministic code, not AI. |
| QC-07 | Judge stock direction, rough force, and confidence for a move | Core verdict/prediction side | Not authorized | **NOT READY:** no locked answer key in the Driver experiment program; DCM/verdict build and some owner decisions remain open. This is separate from `du_worthy`. |
| QE-01 | Create, verify, and grade hidden answer keys | Evaluation infrastructure | **Never Qwen-authored for Qwen's own test** | Frontier-model duty. K-pairs/K-reader are locked; K-fields is drafting; K-route/K-stamp are absent; Fiscal truth expansion is mostly absent. |
| QA-01 | Discover new Drivers in unseen source text | Track A / frontier reader | **NEVER QWEN** | Existing K-reader/EXP-2 belongs to frontier discovery and is outside this Qwen program. |

## 5. Corrections to avoid false claims

1. **The 8-K table set is a screen, not certification.** Its honest independent
   count is 8 tables, not 93 independent documents.
2. **The identity set is diagnostic, not EXP-4.** A perfect 160/160 does not
   activate Qwen as an identity judge.
3. **K-reader is not a naming-only test.** It asks a model to discover and name
   causes from long chunks, which the owner has excluded from Qwen's role.
4. **EXP-6 is not concept selection.** It mainly checks whether text-created and
   XBRL-created versions of the same fact converge to the same identity.
5. **K-fields is not stock-move attribution.** `du_worthy` means a real,
   source-stated, non-boilerplate DriverUpdate fact. Stock-move attribution is
   the separate `EXPLAINED_BY` verdict.
6. **The S4 15-item rehearsal is not a Qwen quality key.** It proved recorded
   answers flow through Core correctly; it made zero AI calls.
7. **The current Fiscal truth-expansion proposal includes human review during
   offline key building.** This file does not approve or silently replace that
   method. Runtime remains human-free. If key building must also be fully
   human-free, the owning truth-expansion plan needs a separate owner ruling.

## 6. Work that is not a Qwen task

Keep deterministic work in code:

- source/span/hash verification;
- numeric parsing, scaling, signs, units, period math, and slice
  normalization;
- IDs, exact matching, validators, fusion, writer idempotency, and graph
  constraints;
- XBRL materialization;
- read/history collapse;
- ledgers, schedules, cursors, retries, alerts, and recovery plumbing.

Qwen may choose among bounded semantic options only after the specific task
passes its own hidden test. Code must continue to verify everything it can.

## 7. Smallest next sequence

```text
QF-01 complete and failed
  → keep its 93 opened cases as development data only
  → choice-only redesign also failed: 75/93 exact cells
  → move source-provable rows to plain code; isolate genuine residual ambiguity
  → build a fresh unseen holdout before any Qwen qualification
  → separate owner GO: run QC-01 once (160 fresh calls)
  → classify Qwen per task: qualified / safe-first-pass / unsafe
  → later: the separate QC-02 target-supplied Qwen diagnostic only after its own key locks and a separate owner GO (no EXP-5 P6 arm)
```

If either first run fails, first separate model weakness from prompt,
formatting, context, and wrapper mistakes case by case. Do not rerun the same
hidden set to claim that a tuned prompt is newly certified; build a fresh
holdout.

## 8. Sources verified for this snapshot

- `FINAL_DESIGN.md` — naming, type, identity, XBRL, verdict, and safety law.
- `ChannelContract.md` — Fiscal fetch/copy duties and forbidden identity work.
- `15_CandidateFactPacket.md` — decomposer/Core field and ownership split.
- `BUILD_AND_OPERATIONS.md` — build state, model roles, experiment gates.
- `STATUS_AND_HISTORY.md` — live completion and pending-state summary.
- `FableExperimentPlan.md` and `FableExperimentWorkOrder.md` — EXP-0…6,
  K-pairs/K-route/K-fields/K-stamp, and the separate Qwen diagnostic authorization (no EXP-5 P6 arm).
- `../experiments/WORKORDER_STATUS.md` — current signed/pending experiment
  state.
- `../experiments/keys/K-pairs/CURRENT.md`,
  `K-pairs.v1.3.lock.json`, and `protocol.md` — 160-pair locked instrument.
- `../experiments/keys/K-reader/K-reader.v3.lock.json` — 1,175 combined
  discovery+naming records; not a naming-only test.
- `../experiments/keys/K-fields/protocol.md` — current drafting-only EXP-5 key.
- `../WIP/Phase6_ReaderApprovalPackage_2026-07-23.md`,
  `phase6_screen_call_1..3.json`, hidden answers, grader, validator, and
  manifest — Fiscal table screen.
- `../WIP/Phase6_TruthExpansion_Plan_2026-07-23.md` — missing five-category
  truth and proposed expansion route.
- `../WIP/concept_link_revalidation/` — earlier concept-link evidence and
  scripts; not a ready locked Qwen key.
- `config/local_llm.py` and `docs/LOCAL_LLM.md` — current uncommitted local
  transport work; exact runtime/model fingerprint must be re-checked after its
  owner finishes it.
