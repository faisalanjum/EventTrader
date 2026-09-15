# Supplement to the 2169 review: the affected population, closed by identity

Core 5ae9b86b, 2026-09-15 UTC. Read-only. No model call, no scoring or native
rerun, no code/prompt/key/grade edit, nothing staged. The three published 2169
files are untouched; this version supersedes only the derivation method, and
the resulting changed/open population is unchanged.

## 1. The hole, and what closes it

The 2169 baseline frontier was found with five hand-chosen quote substrings and
`collect()` skipped any claim that matched none. That proved the 18 selected
questions and said nothing about the other 408. Two further objections are also
right: one quote can carry several facts, so proving a quote unique is not
proving a claim unique; and an absent produced `comparison_baseline` is not by
itself a reason to exclude a record.

This supplement replaces the selection with an enumeration:

| | 2169 | 2170 |
|---|---|---|
| baseline candidates | 5 quote substrings | every served record identity |
| skipped claims | silently continued | refuses unless every served claim is reviewed |
| disposition key | quote substring | exact `source_id \| sha256(quote)` |
| decision input | partly the record's own null field | what the SOURCE states, for every record |

## 2. What is actually served, and what is not

The current native score takes every G3 judgment from the CORRECTIVE rendering;
the original G3 contract serves neither clause, so it can decide nothing here.
G2 carries both clauses in both renderings, so its frontier does not depend on
the surface. Counting attempts and lanes separately, as required:

| | attempts | distinct lanes | invalid attempts |
|---|---|---|---|
| corrective G2 | 38 | 38 | 0 |
| corrective G3 | 61 | **60** | 1 (`G3-007/G1b` attempt 1, `X75b11760e0633d83 was not answered`) |

My 2165 message called this 61 G3 lanes. That was a lane/attempt conflation and
is corrected here: **60 lanes, 61 attempts, 1 invalid attempt.** The retry
serves byte-identical prompt bytes to the attempt it replaces
(`fac76e5519b724a44274b649c447e0011f314d678959ec21d6b5c0d619cf1808`), so the
invalid attempt changes which ANSWERS stand, never which evidence was served,
and the frontier is the same either way.

Identity enumeration over the selected surface:

* **426** distinct served produced-record identities. Every corrective G3
  comparator is also an asked record, so the comparator set adds none.
* **41** identities appear ONLY in the unused original G3 surface. They are
  listed and scored by nothing.
* **0** served comparators matched two byte-identical saved facts. Three such
  pairs exist in the run (P1 and P2 `BBY_2026-03-03T08.00`), the lookup is a
  multimap so they cannot be silently collapsed, and none of them is served as
  a comparator.

## 3. Every distinct claim's temporal comparison, reviewed once

122 distinct claims carry those 426 identities. Each is read once, keyed by its
exact `source_id | sha256(quote)`, and classified by what the SOURCE states -
never by what the record happens to leave null:

| category | claims | what the two texts do |
|---|---|---|
| `none` | 60 | no prior-year or sequential comparison is stated; neither text selects a temporal baseline |
| `prior_year` | 57 | only prior year is stated; the served both-stated tiebreak cannot fire, and the corrected headline is that same comparison |
| `sequential_period` | 2 | only sequential is stated; same reasoning |
| `both:prior_year` | 1 | both stated, prior year is the headline - **both** texts select prior year |
| `both:sequential_period` | **2** | both stated, sequential is the headline - served forces prior year, corrected keeps the headline |
| `both:undetermined` | 0 | none found |

Only `both:sequential_period` can move a required judgment. The exclusions are
therefore justified by category, not by prose repeated 120 times.

**The 7.6% case, decided from the source.** `Total unit revenue was 7.6% higher
year over year, improving sequentially each month in the quarter` states both
comparisons, and the headline is the quantified year-over-year one. FINAL_DESIGN
line 243 (DU-15) says *the home fact keeps exactly ONE primary baseline (e.g.
the prior-year headline)*, so the corrected text selects prior year - which is
what the served text selects too. It is unaffected because the SOURCE's headline
is the prior-year one, not because these records leave `comparison_baseline`
null. The same reading covers `increase sequentially up into March` and
`sequential improvement from the fourth quarter`: in each the co-stated growth
number carries no stated basis, so on either reading - one stated comparison, or
a prior-year headline - both texts select the same baseline.

## 4. The final minimal population

| | unaffected | affected | open |
|---|---|---|---|
| G2 (310) | 302 | 6 | 2 |
| G3 (116) | 109 | 4 | 3 |
| **426** | **411** | **10** | **5** |

**15 questions need a new answer.** They are the same 15 the 2169 review
proposed; what changed is that the other 411 are now proved rather than
unexamined.

| verdict | question | leg / source | gold / produced | clause | role |
|---|---|---|---|---|---|
| affected | M43e87509e5cc819b | P1 0000027904-26-000013 | 6 / 5 | scope | asked |
| affected | Mabd80961830fa09a | P2 0000027904-26-000013 | 6 / 6 | scope | asked |
| affected | X99d7bc16850a9dde | UNION 0000027904-26-000013 | - / 5 | scope | asked |
| affected | Xe10aa94910fc4e7a | UNION 0000027904-26-000013 | - / 8 | scope | asked |
| affected | M24065e66c77fea00 | P1 0000027904-26-000020 | 6 / 8 | baseline | asked |
| affected | Mc17055ff4a7a52dd | P2 0000027904-26-000020 | 6 / 9 | baseline | asked |
| affected | X6eea70137b9a2e63 | UNION 0000027904-26-000020 | - / 3 | baseline | asked |
| affected | X73357410ba2d97a2 | UNION 0000027904-26-000020 | - / 5 | baseline | asked |
| affected | Mf91a92c59065852f | P2 AAL_2026-04-23T08.30 | 8 / 7 | baseline | asked |
| affected | M02d957fa99800507 | UNION AAL_2026-04-23T08.30 | 8 / 7 | baseline | asked |
| open | Mde7d5e39712de0c7 | P2 0000764478-25-000057 | 0 / 0 | scope | asked |
| open | Xa0f9de09f3c55112 | UNION 0000764478-25-000057 | - / 5 | scope | asked |
| open | Mc6c32dee91400e91 | P2 0000940944-26-000005 | 2 / 2 | scope | asked |
| open | X24756096af610d6d | UNION 0000940944-26-000005 | - / 5 | scope | asked |
| open | X56415b76439cd6be | P2 0000027904-26-000020 | - / 8 | baseline | comparator only |

**Every exclusion category, justified.** Baseline: the five source categories
above. Scope: the clause re-defines an empty slice only on an ACTION, so every
metric, guidance and surprise record is untouched by construction, and an action
that carries a stated part is judged the same under either text because the
corrected sentence still requires that part. 30 served records are actions with
an empty slice; 22 of them sit on claims where the source establishes a
company-level action, 4 are affected and 4 are open.

`unaffected` here means **these two clauses do not move the required answer.**
It is not a claim that the judgment is correct; remaining cause analysis is not
mine.

## 5. Checking your reasoning, and one counterexample

Your four corrections hold and I verified each: the silent `continue`, the
quote-versus-claim distinction, the null-baseline point, and the 61-versus-60
lane count. I found no counterexample to any of them.

One thing your message does not cover. You resolve my first connection problem
by binding `PREP.V` and `PREP.CORRECTED_RULES` explicitly, which is fair. The
second one is still live in the bytes you edited at 00:59 today:
`score_corrected_grading_2162.py`
`92d94339341a24483a8c39775c4e163811a1745437f94b5db8655d9b342fc5a4`
line 48 still refuses unless the FIRST revision's `input_correction_sha256`
equals `G._sha_file(V.__file__)`, with `V` imported at line 21 as
`a7_grading_input_correction_2114`. A correction prepared through the contract
module carries the contract's hash, so as a FIRST revision it is refused.

It is not a blocker, and your chain is why: `run` validates only
`revision_ref` that way, and later revisions go through
`a7_grading_revision_chain_2169.scope`, which defers to the unchanged
`a7_grading_revision_2115` - and that owner only requires the candidate and its
descriptor to AGREE on the input version, so it is version-agnostic. So the
constraint, stated exactly: **the contract-based correction can only enter as a
LATER revision in the chain, never as the first.** If you intended it as the
first revision, that line is the counterexample.

## 6. Guards, and the red tests that prove they fire

The derivation refuses rather than skipping. Each guard was red-tested on a
tampered copy in scratch; the published file is unchanged.

| guard | red test | what it did |
|---|---|---|
| every served claim has a reading | renamed one claim's source | refused, naming `0000027904-26-000020\|1791c0a1...` |
| the table reviews nothing spare | added one unserved row | refused, naming the spare row |
| an empty-slice action has a scope reading | corrupted one scope key | refused |
| the served surface is a declared choice | pointed G3 at the original surface | refused on the first claim that surface adds |

## 7. What this does not establish

That any of the 15 will answer differently - nothing was called. That the 411
are graded correctly. That your 26 native, 17 focused, 279 regression or 28
native tests pass; I read the live bytes of the owners I cite and ran none of
your tests. The material effect of the 5 open rows stays open.

## Files

| File | What it is |
|---|---|
| SUPPLEMENT_2170.md | this supplement |
| IDENTITY_POPULATION_2170.json | 426 questions, 426 served record identities, 122 reviewed claims, the unused original-G3 identities, and every reason |
| derive_identity_population_2170.py | the read-only derivation; imports the published 2169 loader at its pin and refuses on any coverage gap |
