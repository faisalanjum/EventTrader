# Verified current-key preparation — not a signature or score

The current key contains 165 accepted facts across 191 source rows/33 events.
The existing full gate reports no open issue or duplicate and all required
difficult-case floors met. Thirty-two source raw/origin pairs are unchanged;
the one new source result and its durable native state/transcript were proved
independently in SOURCE_RESULT_REVIEW_2147.json (dfecc9e55).

The first real candidate invocation failed closed because the current input
reached an older signature check. Its complete failure is retained under
unit_2020_codex_check/codex_authority2147_a (c75f8964).
The corrected invocation supplies each historical signature's own proved input
at the existing signature_accounting boundary and restores it afterwards.
It changes no signature, materializer or candidate validation rule.

## Completed checklist

| Pass | Change and actual verification |
|---|---|
| Generality | Use recorded candidate/input identities, not example words or guessed sibling paths. Exact finite history-map coverage asserted. |
| Full workflow | Actual existing C.build and full C.verify pass; full raw/origin, artifact, receipt/finalization, input round-trip and ledger comparisons pass. |
| Duplication and organization | Existing rule owners unchanged. The next lock/consumer must reuse this input boundary; no second signature validator. Historical failed caller remains evidence, not an alternate selected path. |
| Simplicity | Only one caller boundary changed; completed native preservation reused. No new signer, cache, score rule or production abstraction. |
| Verification | Four focused context/order/unknown/exception tests pass; removal of the input binding produces four intended assertion failures. Actual native candidate and no-repeat selector both exit0 with empty stderr. |

Evidence:

- Caller build_candidate_2148.py:
  0aab3a73b19fd8d1ed649ecaa906861f08967193230cf2da2b15e94513ea011f.
- CANDIDATE_COMMAND_2148.json and
  unit_1947/logs/attempt_codex_candidate2148_a preserve the exact command and
  raw result. CANDIDATE_PREPARATION.json:
  7d0d9a6f94fa7d97a0d3347ad581ae39ea94a4c573916c973942b035c750fef7.
- SIGNATURE_CONTEXT_CHECKS_2148.json preserves focused and mutation outputs;
  its in-progress line is historical and is closed by the native result above.
- Existing select_real_signer_2083.py is reused unchanged. Exact command in
  SIGNER_SELECT_COMMAND_2148.json, raw evidence in
  unit_1947/logs/attempt_codex_signselect2148_a: launch/null/null, no prior call.

The signer prompt was checked against its existing renderer and raw-shard
manifest. It checks completeness/accounting, not new source meaning. The
resolved-history head correctly distinguishes old disagreements from live
open issues. Manifest budget686 is the source/key chain; it is not all A7
grading calls. One independent primary sign-off remains; an invalid-only
retry is allowed only if separately authorized and proved by the same owner.
No signer, lock, corrected-key grading, score, production use or live local
model compatibility is claimed. Every final miss/wrong accept still needs its
source-backed cause, preserving genuine model errors and zero-credit gaps.
