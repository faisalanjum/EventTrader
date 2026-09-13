# Bounded final grading review — Codex, 2026-09-13

Purpose: finish a trustworthy A7 measurement over the unchanged saved answers.
This is the shared review checklist, not a new product requirement. The latest
mailbox owns Core's one task. Update evidence/status after each affected pass.

Newest evidence checkpoint,10:38 Eastern: normally committed/pushed
1631fadde6d7cde591e16a1bee56209917f8a6a2, tree7fcb623d4e738c6906f75d916938c08c085a0495;
fresh remote matches. G2_PROGRESS_PUBLICATION_2111_B.json SHA80557b15 pins1169
verified files through G2 segment54, plus the already persisted G3 completion.
523 changed paths; all committed blobs match, index empty, unrelated work
untouched. Grader/inputs unchanged.80 primaries remain at this snapshot.

Evidence-only checkpoint,09:04 Eastern: committed and normally pushed
79e62c588a958570880829502750dc4156e290c3, treea2366e974361f1909fd1bd7c85da94096f0f7c64;
fresh remote matches. G2_PROGRESS_PUBLICATION_2111.json SHA2924a448 pins649
verified files, including G2 segments6–32 and G3's persisted completion.
Grader code and frozen collection inputs are unchanged.101 primaries remain
at this snapshot; Core continues Codex2110. This is not a final A7 result.

Post-publication status, 2026-09-13 07:04 Eastern: preparation is committed and
normally pushed as b86c9052267bcee86b9ca9bae4dac0ce513c712e, tree
e662a86844f3e4c6a6e9a956ad8aa7517af5d4a2. The remote commit was independently
checked. Manifest G2_FORMAT_PUBLICATION_2110.json
SHA68f53885427ca5b3eccd9b13a324462af11d51a6a21c6b377fdaa90c08511fe1
freezes2813 files. The real zero-call closure passed; no existing run bytes
changed. Codex2110 (95ab08348ecf9f093f15a4993017c3960658f1c536a27b0c5d046a02dde1687d)
now authorizes remaining G2 collection through the verified format/retry
connector. Core has completed the next primary;136 remain at this snapshot.
G3 is already verified. Actual G2 evidence review and final scoring remain;
no A7 score or PASS is implied. The pass log below preserves pre-publication
proof history; its former closure/publication blockers are resolved.

Collection review,11:24 Eastern: G2 segments6–70 independently replayed through
the original native/parser checks (REVIEWs SHAbcbef7be,2f949a42,dd226d67,
96690847,fb9869c9,4e99eb98,a66c8ac5,12596534,8a798ecf,843d3331,baf1e662,5c999c88,d36b6567,c4f2a534,b1b20563,70a942d7,8eb5fdac,d6c91ac0,02ca76c5,14671483,d1344a6c,691dd870,34de60c8,92397750,bd13f38f,117af5fa,972f798b,1aad1c25,e00e3cc5,c3f23e91,581193e1), and all272
durable native copies match their sources. The71 readings include24 original-
valid and47 recovered; exact retry-filter replays preserve every negative
judgment and require no retry. Two-reading segments17,24,27,36,49 and66 are verified.
G3's reviewed completion
is now saved through C.persist_g23 and reloaded: exact approved bytesad575661,
110 agreed/7 unresolved,147-file run unchanged. PERSISTED_G3 report11ed9654.
Neither this progress nor successful collection is a final score or PASS.

## Strategy and stopping rule

1. Trace the live path, not just test names: original raw/native reply → frozen
   request and whole-reply checks → original validity → explicit format-only
   recovery → existing attempt selection → two independent readers agreeing
   per question/aspect → persisted completion → exact population check → real
   no-write route and scorer → complete denominators and final gate.
2. Derive failures from those functions and the actual saved population.
   For each boundary prove a lawful control, its meaningful corruption, and
   the resulting refusal/zero credit. Do not infer correctness from exit0.
3. Reuse verified key, producer, G1, native-test fixtures and regression setup.
   Add tests only for the changed format/consumer boundary and gaps found by
   this trace. Preserve every old failure and every valid completed AI call.
4. Review the patch separately for duplication and unnecessary machinery.
   One existing parser owns schema; one existing reconciler owns agreement;
   one scorer owns credit. The new scoped recovery preserves frozen owners
   instead of rewriting historical files. It is not production runtime code.
5. Freeze exact reviewed code/rule/results, run affected checks and deliberately
   broken controls, then authorize the precise remaining collection operation.
   Score only from independently validated complete evidence, with the approved
   partial rule for genuinely exhausted invalids. Report limitations explicitly.

Finish this code review when every row below has proof or an exact blocker.
Do not keep adding hypothetical scenarios. No claim of zero possible future
errors follows from testing. No uncertainty or formatting fix may manufacture
an agreed judgment, erase an invalid, relax a passing bar or imply A7 PASS.

## Live rule and code owners

- `step1.md` A7: full producer accounting, independent grading, no-write route,
  recall/accuracy/safety/duplicate bars; A8 requires EXP-5 PASS.
- `FableExperimentPlan.md` §2 A7 amendment3–6: versioned correction/reuse,
  bounded missing-proof calls, no successful repeats, honest partial reporting.
- `FableExperimentWorkOrder.md` §1.5: independent qualified readers, bounded
  batches, one invalid-only retry, no silent coercion.
- `Steps.md` rules2–11: smallest complete owner-level deterministic fix,
  models decide meaning, test first, full affected class, no hypothetical work.
- `A7_MEANING_FORMAT_RULE_2105.md`: the owner's new exact-string recovery
  decision. G1, G3, producer contract, source truth and thresholds unchanged.
- Original owners: `raw_transport.parse_reply`; `G.preflight`,
  `G.audit_official_state`, `G.whole_answers`, `G.finalize_segment`;
  `C.evidence`, `C.select_attempt`, `C.complete_g23`, `C.load_g23`;
  `B.read_meaning_reply`, `B.reconcile_meaning`, `B._verdict_maps_from`,
  `B.official_tier_decision`; existing production no-write route/scorer.
  Here G/B/C are the unchanged2006/2008 owners in map_g23_transport_2103.tsv.
- New code under review: `a7_meaning_format_2105.py`: exact scalar recovery,
  original-evidence-first reporting scope, separately pinned recovery audit.

## Known issues and exact remaining decisions

- PROVED format class:3 of first4 G2 replies used exact quoted boolean/null
  values. Original parser correctly rejected them. A quoted template is a
  plausible cause, not proved causal attribution. No prompt is changed here.
- Original G2-000/G1b retry is spent. Original G2-001/G1a retry is published
  but uncalled (segment5). Do not repeat a successfully recovered reading.
  Resolve the published reservation through a lawful explicit instruction;
  never delete it, fake a native result or ignore a pending segment.
- Meaning is separate: false judgments, nulls, disagreements, the known G1
  missing reading and duplicate findings are not formatting errors to fix.
  They must survive into the result. No final score currently exists.
- G3 collection is independently VERIFIED:32 required primaries,33 calls,
  32 original-valid attempts and one original invalid followed by its valid
  retry. All10 segments replayed through native auditor and parser;86 durable
  native files rehashed against their sources. The existing completion owner
  derives110 agreed and7 disputed questions from117 required, with no dropped
  identity. Disagreements stay unresolved, not retry targets or code defects.
  `codex_g3completion2106_a/REVIEW.json`
  SHA5a9479df1fb2abbd32a237a51ad673cc8ca57cf0b584f4adffc7af69ea3ab570.

## Checklist / pass log

| Required check | Status, change and evidence |
|---|---|
| Correct scope and rules | VERIFIED from live rules above; source/key/production audits are not reopened. |
| Preserve native identity and history | VERIFIED for four G2 calls: original auditor/parser replay exit0, 16 native copies byte-identical to sources. `codex_g2seg1to4review2105_a/REVIEW.json` SHA3785da62ce266c1a8f60ca022d6c01d28cb35b4b75c2d0ccf3e00c66aa597b73. |
| Exact scalar recovery, no meaning guess | FOCUSED VERIFIED: initialbehavior39fail/9pass →48pass; exact booleans/null, each field, mixed representations, malformed/extra/missing/duplicate/unknown inputs and all two-reader verdict combinations. Original raw still fails original parser. |
| Explicit recovery identity; original errors still refuse | FOCUSED VERIFIED: scope3fail/56pass →59pass. Wrong code/rule pins refuse; original evidence errors are not waived; G1/G3 unchanged; scope restoration verified. Unit doubles are not native proof. |
| Actual saved G2 replies recover correctly | VERIFIED: four externally pinned whole replies; three recovered, one originally valid; original parser errors and raw hashes unchanged. Independent JSON-literal calculation matches every verdict. Current code7aeabc6b is proved in `codex_formatreal2107_a/RECOVERY.json` SHA7b1307320e2c7528a101d78c3217962066025ade98af8176b1f844851f379f26; payloadexit0, empty stderr, zero calls. Earlier2105a report1a561676 remains proof of its earlier code revision, not a current-code pin. |
| Full original-record → recovery → actual scorer path | VERIFIED: `codex_formatnative2105_c/SCORING_CONNECTION.json` SHAbe7ddc2123c5722c8fd9c8272c8afc24636e220606119b1cc4448c8a7fba8c06.141 original-invalid TEST attempts retained,139 recovered;299 agreed/7 unresolved meaning questions;99 exact event-leg routes;163 gold per leg. Injected false yields1 confirmed wrong accept; all7 unknown/disputed/unusable questions remain missing judgments. Existing G1 gap/duplicate findings survive. Wrong completion hash and no-recovery consumer controls refuse. Exit0;4 existing guidance warnings, no traceback. NOT an A7 score. |
| Attempt/resume path and no repeated success | CODE VERIFIED: format68 + retry14 focused tests; six retry mutations caught/restored14-test control. Native TEST proof excludes139 recovered readings and retains the genuine invalid; actual segment4 CLI preserves false judgments and requires no retry. Real operator setup/selection blocks invoke the pinned filter; recoveredG2 chooses prepare, G3 unchanged, wrong rule pin stops (OPERATOR_CONNECTION SHA96c084dc). Core independently replayed the filter. Remaining-count helper now uses the EXACT served G5523c5b6 lane-state owner, not another history scan or the different2008 G copy: helperc3aa3a99, native/host14-test proof. It retains uncalled/refused rows and reports137G2/0G3. Closuree72647b3 passes Codex's51-check rerun and independent native/sidecar controls plus three caught mutations; exact306 question/batch outcomes and original-invalid audit verified (codex_unusedfinal2109_a/REVIEW.json SHA085ed22011df451914c427fbc25e300becaf734a78b6b7fa7b6f5088173a0bc1). Actual zero-call closure is now being applied through pinned callerc2cd24be; no AI call authorized yet. |
| Duplication, organization, simplicity | VERIFIED for format7aeabc6b, retry127bd6c0 and closuree72647b3: original strict parser, native auditor, finalizer, lane-state owner, reconciler, selector, completion and scorer retain their own rules. Exact JSON literals/G2 scope and external identity pins are required constants, not semantic hardcoding. One pinned recovery view preserves frozen owners; retry filtering subtracts recovered results from the original eligible set; zero-call closure reuses existing no-output/parent/state/accounting primitives. No cache, new parser/scorer, prompt change, production import or speculative configuration. Core's two non-findings (exception contract and a validity row already guaranteed by the finalizer) require no extra code. |
| Meaningful mutations and full affected regression | VERIFIED for format patch:12 in-memory mutations all caught by behavioral tests; restored68-test control passes, stderr0. `codex_formatmut2106_a/MUTATIONS.json` SHA730e41c3660642d98d6fa5c22c71ce035a58034a9d7c5065f398f4562ad4adf9. Full19-module result698pass/2named skips/0fail, combining `grader_formatnative2106_fixed` with unchanged ordinary `grader_formatordinary2105`. The rerun first exposed the trace test's fixed shared workflow name; canonical test now supplies one unique tag per test run to the existing collision-refusing helper (test SHAa518ce46b0e9061763add0be8615e727436088335a46226878157a0a5620bbc1).11-test focus and repeat full native suite pass; no validator weakened. Historical fixture/owner copies stay untouched; one explicit TEST overlay serves the corrected test. |
| Freeze, commit/push verified increment, score | PREPARATION VERIFIED; PUBLICATION IN PROGRESS. Actual zero-call closure is applied through callerc2cd24be:46 existing run files unchanged, exactly3 administrative artifacts added, zero new AI. Independent actual C.evidence/F.scope and W.next_admissible replay passes; four saved readings reused,137 primaries remain, nextG2-001/G1b. Applied review6703734b and manifest9954bb59 pin the result. No new model collection or A7 score yet. Current committed parent isfd4c9cba. |

Raw test logs are under `../unit_1947/logs/attempt_codex_format2105_*` and
`attempt_codex_formatscope2105_*`. The initialformat_red import failure is
setup evidence only; red2 is the actual failing behavior. Last focused runs
have payloadexit0 and empty stderr. Original collection files are unchanged.

Native proof development: attempt_a exposed a TEST assertion treating the
declared integer question count as a list; corrected the assertion, not code.
Attempt_b passed the actual tier-scoring checks but reached its300-second
limit while unnecessarily rerouting for negative controls. Attempt_c calls
the already-exercised completion consumer directly for those two negative
checks and passes without repeated routing. These are TEST-only setup/time
results, not model failures. The unused-retry closure and preparation are now
verified and pushed as recorded above; actual grading is not yet closed.
