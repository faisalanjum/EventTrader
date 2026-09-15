# The changed-task preparation: selection, invocation and produced candidates

Core 5ae9b86b, 2026-09-15 UTC. Read-only. No model call, no run, no rerun, no
code/prompt/key/grade edit, nothing staged. Every published file is untouched.

**No defect found.** The job finished with raw exit 0 while this check was
running, so the produced candidates are verified too, from their own bytes.

## 0. Two corrections to me, both confirmed against the bytes

**My FINAL_DESIGN citation overreached.** Line 239's `it is stored ONLY when
the source states a non-derivable delta AND its arithmetic sign is
determinable` is prefixed on that same line by `On a SURPRISE,`. It governs
surprise facts, and I quoted it as if it governed the stored case generally.
The general clause earlier on the line - `Leave change_value=null when it could
merely be derived from a closed shape (derive at read)` - is the one that
carries the task change, and it alone is enough. Withdrawn as stated.

**My helper reports that boundary, it does not assert it.** In
check_null_delta_boundary_2171.py, `reachable_outside` is computed at line 141
and appears only in the counts and the printed summary; nothing raises on it. My
review said it "asserts that property... so a future record would fail it". That
was false about my own code. The observed zero stands as a measurement of the
finite live population, not as an enforced invariant. I am not republishing the
file, per your instruction; the correction is recorded here.

## 1. The frozen selection

| check | result |
|---|---|
| G2 / G3 questions listed | 31 / 7 = **38** |
| `expected_questions` matches the lists | yes |
| the populations regenerate exactly the listed ids | yes |
| listed ids equal my two frontiers (15 + 23) | **yes, exactly** |
| declared input version | the contract `23c36532...`, not the renderer |

## 2. Both baseline candidates

Each binds to the FULL population and to the same producer, G1 and key identity
the full candidate carries. G2's baseline is the original current-key candidate
and carries no input version, as a frozen-renderer build should. G3's baseline
is the `32e2f650` build and its `matched_population` is the full G2 pairs -
which is what gives its comparator pool the matched-only shape I measured in
2170.

## 3. The one risk I chased, and why it is closed

The payload compares new evidence against the G2 **original** candidate, but 2
of the 31 selected G2 questions - M24065e66c77fea00 and Mc17055ff4a7a52dd - were
actually graded on the **corrective** rendering. If the two surfaces differed for
them, the comparison would preserve the wrong evidence.

Across all **82** G2 questions rendered both ways: **77 byte-identical**, **5
differ only in `slice_parts`**, **0 differ anywhere else**. The five are exactly
the display owner's work - the original carries
`unknown:xbrlaxis_<hex>__spacenk` and the corrective carries the decoded
`unknown:us-gaap:BusinessAcquisitionAxis__spacenk` - which is the one
transformation the payload applies. **Both of the two selected questions are in
the byte-identical 77.** So the baseline choice loses nothing. The payload
relies on this rather than asserting it; I measured it.

Also load-bearing and measured, because the payload aborts otherwise: the
original G2 candidate renders **310** events of one question each, and the G3
baseline **116**, so `len(event['questions']) == 1` holds on both. The
corrective G2 run renders each question twice, once per grader lane, and I
required those two renderings to carry identical evidence rather than skipping
the duplicate - they do.

## 4. The invocation

`PREP` is the unchanged `50f9298c` preparer, called with **both** `V` and
`CORRECTED_RULES` bound in its own restoring scope - so the import-time drift I
named in 2165 cannot occur on this path. It is also caught transitively: if `V`
were ever bound to the renderer by mistake, the returned version would be
`32e2f650` and `version == selection['input_correction_sha256']` would fail.

The payload asserts, in order: the subset against the full population through
the existing owner; the regenerated question ids against the frozen list; every
baseline prompt hash; one question per event on both sides; the new candidate
equals a rebuild under the same version scope; the population equals the subset;
every new prompt hash and that each starts with the contract rules; **each new
event equals the baseline event after removing only the batch-local label**; the
seen ids equal the wanted ids; and the real bound-script size for every launcher
row at every permitted attempt. The report is written with `_write_new`, which
refuses to replace, and every input is re-pinned after the run.

## 5. The produced candidates, verified from their own bytes

| | G2 | G3 |
|---|---|---|
| population equals the selection subset | yes | yes |
| every prompt hash verifies | yes | yes |
| rendered ids equal the selection | yes | yes |
| questions | 31 | 7 |
| evidence identical to the baseline | **31 of 31** | **7 of 7** |
| corrected clauses served, per prompt | scope 1, headline 1, null-change 1 | same |
| input version | `23c36532...` | `23c36532...` |
| batches / launcher rows | 9 / 18 | 3 / 6 |
| made_calls | 0 | 0 |
| largest prompt | 424,280 B | 376,512 B |
| largest bound script (reported) | 439,520 B | 393,133 B |

None of the 38 needed the display decode at all - all 38 are byte-identical to
their baseline evidence, with no `slice_parts` difference. Every prompt carries
all three corrected clauses exactly once, so the null-change sentence rides in
with the two clause fixes as you said it would.

**Call ceiling: 24 primary lanes** (18 G2 + 6 G3), **24 invalid-only retries**,
so at most 48. Lane pins are the same as the earlier runs - sonnet, lean-probe,
high effort, 128000 output tokens.

Transport headroom: the contract rules are 390 bytes longer than the frozen G2
rules, and the largest bound script produced is 439,520 against the 524,288
limit, so nothing is near the edge.

## 6. The native job

`state finished exit 0`, raw exit `0`, stderr empty, stdout the two expected
lines, report present. When I began this check the job was still running with
`state running` and an empty output directory; it completed during the review,
so everything in section 5 is read from the finished artifacts, not predicted.

## 7. What this does not establish

Any verdict for any of the 38 - nothing was called, `made_calls` is 0 in both
candidates. That the corrected answers will differ or improve. Your caller
integration, call-ceiling approval and final scoring, which are yours. And I ran
none of your test suites; I read the live bytes of what I cite.

## Files

| File | What it is |
|---|---|
| REVIEW_2172.md | this review |
| CHANGED_PREPARATION_CHECK_2172.json | every measurement above, including the produced-candidate verification and the job state |
| check_changed_preparation_2172.py | the read-only check; pins the selection, the payload and both of my frontiers, and refuses on a duplicate or differing rendering |
