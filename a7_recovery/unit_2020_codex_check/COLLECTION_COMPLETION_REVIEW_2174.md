# Final correction collection and reporting check

Codex, 2026-09-15 UTC. A7 only. This verifies evidence and mechanics, not
the correctness of every model judgment or a passing experiment.

## Actual evidence

Core2169/c7fb4c6229823cb712e67ab3f4e99d2fb1b5dc993533541b51c7f9f514349069
answers Codex2173/20ed85592528c96818131b86ec5500900d921b65d2744ecc97fd6130c29f1046.
Both archives, sessions, live heads and the reply chain match. The next outbound
sequence was derived from2,415 mailbox/archive records, not guessed. The existing
single watcher and observer were reused; Core received Codex2174/54ffb7d2.

COLLECTION_EVIDENCE_CHECK_2174.json records Root's independent checks of all
26 attempts across20 workflow returns and26 child transcripts. The required
24 lane identities exactly equal the frozen roots. Every preserved state,
returned payload, invocation, executed script and raw answer agrees byte for
byte. Child assistant metadata identifies claude-sonnet-5 with no worker tools.
Both second attempts followed invalid first replies; no valid reply was repeated.
All24 latest replies are valid. The native owner, not this audit, decides
response validity and constructs per-question judgments.

The two format failures remain preserved. The only nonzero collection-native
exit is core_prep2173_g3_05: stderr reports that every primary lane was already
called. It did not launch another primary and was followed only by the allowed
invalid retry. There is no refusal bypass or missing-evidence waiver.

Root independently re-derived, persisted and loaded both completion candidates
through unchanged persist_corrected_completion_2166.py/8ab3058e. Both raw exits
are0. G2 completion031b83b1 has25 agreed and6 unresolved questions; G3
completion2f689d06 has6 agreed and1 unresolved. All38 questions are covered by
valid readings, but only31 have an agreed judgment. These are distinct counts.

## The small reporting defect and fix

The original collection_progress_2173.py counted segment files as scheduled/
launched lanes and retained historical retry eligibility/problems after a retry
succeeded. Its exact bytesfc995493 and reported JSONbd30b30b are preserved in
snapshots_2174. Root changed it only after Core's completed report and WAIT.

Current helper38cbe4c2 counts distinct lane IDs from the existing invocation
records, and open retries/problems from the latest invalid outcomes and the
root's existing attempt limit. The native collector, parser and grader did not
change. Current report0e77ebf2 agrees with the independently bound raw evidence:
24 scheduled, launched, finalized and usable; zero waiting, invalid, exhausted
or retry-eligible;38 questions covered. Launched counts use durable returned-run
records, not a new live-process monitor. All calls in this final inventory have
returned. Earlier PROGRESS_2173.json remains historical diagnostic evidence,
not the current progress authority.

## Checklist after the correction pass

| Requirement | Change and verification |
|---|---|
| Generality | No semantic decision, issuer list or example-specific branch. Lane IDs and attempt limits come from frozen structured records; legitimate run paths stay fixed. |
| Complete workflow | All26 attempts independently bound; both native completions re-derived, persisted and loaded with raw exit0. Final calculation966d14bc completed99 routes and4 completion loads; FINAL_SCORE_FINDINGS_2174.md records all results and limits. |
| Duplication and organization | One current progress owner; historical scripts/reports retained as execution evidence. Existing completion, revision and scoring owners reused unchanged. |
| Simplicity | Only distinct-lane counting and current retry/problem accounting changed. No provider framework, scorer, parser, retry policy or new AI round. |
| Tests | Initial7 failures with2 passing controls; corrected9 focused tests plus4 actual reversion mutants pass. Full affected regression303 tests plus29subtests passes in3.17s. Live24-lane totals independently match raw evidence. |

The four mutants restore segment-based scheduled counting, segment-based
launched counting, stale retry eligibility and stale problems. Each executes
normally and produces the wrong result under an independent four-lane fixture;
an unrelated exception does not count as detecting the mutation. The focused
tests also cover one-lane segments, exhausted invalid attempts and the need
for both valid readings to cover a question.

The final map3f25cc28 retains every old map2161 row and adds only the two new
run bindings. Revision2174/e51b0702 preserves the original producer, G1 and
full-population identities and is applied AFTER the original82/116 correction.
The current candidate populations match the selected31 G2 and7 G3 questions;
the G3 comparator population still equals the full G2 population. No old answer,
key, successful judgment or score formula was replaced silently.

Final update: the calculation, full426-question comparison and Core's bounded
source check are done; FINAL_SCORE_FINDINGS_2174.md records the results and
semantic limitations. MODEL_REUSE_OFFLINE_REVIEW_2176.md completes the END-only
offline check without claiming local launch readiness. Final affected regression
is318 tests plus29subtests. Remaining: verified publication, then stop for the
owner. No A7 PASS, universal reliability or production qualification is claimed.
