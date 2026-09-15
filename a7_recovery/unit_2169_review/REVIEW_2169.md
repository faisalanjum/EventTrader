# Two corrected clauses: necessity, correctness, and their exact affected population

Core 5ae9b86b, 2026-09-15 UTC. Read-only. No model call, no scoring or native
rerun, no code/prompt/key/grade edit, nothing staged.

Pins re-measured here: FINAL_DESIGN.md
`4218d73abe6b98ef2ecd325aef8b5e49985101b122e457b39784dee677f32a0b`;
a7_grading_contract_2168.py
`23c36532b0629dc4a76a5ee34a0dcf9dbd9eaca6b8c3e57134d8a6b29fcaeba4`;
test_grading_contract_2168.py
`7e77a1a5d9be1b4f85c21c567ecae41be1712f4b4668fa0c866d4f7fa8e8acf8`;
a7_grading_input_correction_2114.py
`32e2f650f56cb77b20c89199bc8cf120181dbc7ff92bdd60014d7abc95a16a2d`;
a7_g23_candidate.json
`020f4550c47e0f4bbfb63aebe67854d5eb3efade92c674ae72fceb40f1d3050a`;
FINAL_SCORE_CAUSES_2168.md
`de85c8f6d23c6fea703e3160b6d5b23399aa83b0dc826c4802ba6eab82311ff3`;
CAUSE_REVIEW_PROGRESS_2165.md
`ca57754496caea83b1d7075fa72689fa7ef4d1330fd444956f69152aa14b2420`.

## 1. Both fixes are necessary and both are correctly stated

**Fix A - scope on an action.** FINAL_DESIGN 5.2, line 170, ends the slice
bullet with: `Omitted slice = consolidated whole-company (metric/guidance/
surprise) or no-applicable-part (action).` The served contract says, under
POPULATION AND MEASUREMENT, `leave it empty only for the whole company.` -
universally, with no fact-type split. The authority gives the ACTION case a
different meaning, so the served text contradicts it for one of the four fact
types. The replacement keeps the frozen sentence for metric, guidance and
surprise, gives the action its own meaning, and adds that a source-stated part
still belongs in the field - which 5.2 also requires, since `Slices apply to
all four fact types.` The replacement asserts nothing 5.2 does not.

**Fix B - which comparison is the baseline.** FINAL_DESIGN 7.1, line 243:
`Store the PRIMARY only - the source's HEADLINE comparison, tiebreak
prior_year > sequential_period`. The served contract says, under THE
COMPARISON BASELINE, `Keep the primary comparison; where prior year and
sequential are both stated, prior year is the baseline.` That converts a
TIEBREAK into an unconditional winner: the authority selects the headline
first and reaches prior_year only when the headline does not decide. The
replacement states exactly that and nothing more.

Neither replacement touches evidence, records, cards, grouping, vocabularies
or any scoring formula, and neither carries a company or example.

## 2. Which graders were actually served each clause - measured, not assumed

The clause text is not in every prompt, so this bounds the frontier before any
judgment. Counted over the served prompt bytes:

| Rendering | prompts | clause A | clause B |
|---|---|---|---|
| original G2 (candidate `020f4550`) | 71 -> 310 questions | 1 each | 1 each |
| original G3 (candidate `020f4550`) | 16 -> 116 questions | **0** | **0** |
| corrective G2 (2161 run, renderer `32e2f650`) | 38 lanes | 1 each | 1 each |
| corrective G3 (2161 run) | 61 lanes | 1 each | 1 each |

The original G3 contract is a 2103-character bucket contract that contains
neither clause. `a7_grading_input_correction_2114.extras_rules()` injects
`meaning_contract()` into the G3 rules, which is why the corrective G3 prompts
carry both. **Consequence: no ORIGINAL G3 answer can be changed by either
fix; every G3 entry below reaches the grader only through the corrective
rendering.** This is also why `a7_grading_contract_2168.extras_rules()`
resolves at all - `_replace_once` needs each frozen clause exactly once, and
it has that in 2114's G3 rules but would refuse against the frozen ones.

Two more measured facts about what a grader can see, over all 426 questions:

* A G2 question shows the produced record in full plus a reference card of
  exactly `quote`, `reference_name`, `values`. **No gold field is shown**, so
  neither fix can reach a G2 answer through the key row - only through the
  produced record. Asked-record identity matched the saved answers 426/426.
* A G3 question shows the produced record, the event's reference cards, and
  `other_records`. In the ORIGINAL prompts `other_records` is every other
  produced row of the event (116/116); in the CORRECTIVE prompts it is the
  matched comparator pool (116/116, of which only 2 also equal every
  other row). The frontier is
  taken over both surfaces.

## 3. The exact affected population

Full population re-derived from the candidate's own `g2_pairs`/`g3_idxs`:
310 G2 + 116 G3 = 426, and all 426 identities regenerate from
`M|X + sha256("G2|leg|sid|gold|produced" or "G3|leg|sid|produced")[:16]` and
equal the candidate's `question_to_batch` keys exactly.

Empty action scope and multiple temporal comparisons were used ONLY to find
candidates; each candidate was then read against its own served quote.

| | frontier | affected | open | unaffected |
|---|---|---|---|---|
| Fix A (action scope) | 43 (24 G2 + 19 G3) | 4 | 4 | 35 |
| Fix B (headline comparison) | 18 (11 G2 + 7 G3) | 6 | 1 | 11 |
| union | 61 | 10 | 5 | 46 |

**15 questions need a new answer; 411 do not.** The two sets do not overlap.

### Fix A - affected and open (8)

| Question | leg / source | gold / produced | why |
|---|---|---|---|
| M43e87509e5cc819b | P1 0000027904-26-000013 | 6 / 5 | affected: an aircraft purchase option is neither a consolidated whole-company claim nor a business population the source names |
| Mabd80961830fa09a | P2 0000027904-26-000013 | 6 / 6 | affected: same claim |
| X99d7bc16850a9dde | UNION 0000027904-26-000013 | - / 5 | affected: same claim, asked record |
| Xe10aa94910fc4e7a | UNION 0000027904-26-000013 | - / 8 | affected: same claim, asked record |
| Mde7d5e39712de0c7 | P2 0000764478-25-000057 | 0 / 0 | OPEN: served quote is the consolidated table; the corrective rules send the grader to surrounding text where the impairment is attributed to Health |
| Xa0f9de09f3c55112 | UNION 0000764478-25-000057 | - / 5 | OPEN: same claim |
| Mc6c32dee91400e91 | P2 0000940944-26-000005 | 2 / 2 | OPEN: the footnote says primarily, not exclusively, Bahama Breeze |
| X24756096af610d6d | UNION 0000940944-26-000005 | - / 5 | OPEN: same claim |

The 35 unaffected all sit on claims where the source establishes a
company-level action - `the Company repurchased ... its common stock`,
consolidated income-tax special items, a consolidated non-GAAP reconciliation
of a single-brand company, `across the fleet`, a corporate credit agreement, a
debt-extinguishment charge, a consolidated LIFO charge, a consolidated
revenue impact. For those, whole-company and no-applicable-part are both
establishable, so the required answer does not move. Each carries its own
reason in the inventory.

Deliberately OUT of the frontier, and worth stating because your own table
names it: **Mcb1fb316d377bb0a** (Chipotlane) is a METRIC with an empty
population. Fix A leaves metric, guidance and surprise exactly as served, so
that row is untouched by this change.

### Fix B - affected and open (7)

| Question | leg / source | gold / produced | served baseline | why |
|---|---|---|---|---|
| M24065e66c77fea00 | P1 0000027904-26-000020 | 6 / 8 | sequential_period | affected |
| Mc17055ff4a7a52dd | P2 0000027904-26-000020 | 6 / 9 | sequential_period | affected |
| X6eea70137b9a2e63 | UNION 0000027904-26-000020 | - / 3 | sequential_period | affected |
| X73357410ba2d97a2 | UNION 0000027904-26-000020 | - / 5 | sequential_period | affected |
| X56415b76439cd6be | P2 0000027904-26-000020 | - / 8 | sequential_period | OPEN: reaches this question only as a comparator |
| Mf91a92c59065852f | P2 AAL_2026-04-23T08.30 | 8 / 7 | sequential_period | affected |
| M02d957fa99800507 | UNION AAL_2026-04-23T08.30 | 8 / 7 | sequential_period | affected |

The Delta rows sit on one table whose columns are March 31 2026, December 31
2025, March 31 2025 and December 31 2019, and whose ONLY stated change column
is `1Q26 vs 4Q25 $ Change`. Prior year and sequential are both stated, so the
served text forces prior year; the headline is explicitly the sequential
comparison, so the corrected text keeps it. Every served record on that claim
carries `sequential_period`; none carries `prior_year`.

The AAL rows sit on `... year over year quarter over quarter just versus the
fourth quarter was up ... less than 10 percent`: both bases are stated and the
only quantified one is sequential. **These two are already negative for a
different, unrelated reason** - your own table records the exact-10-percent
versus less-than-10-percent bound loss. Fix B can move their baseline aspect;
it does not cure the bound.

Three claims were candidates and are NOT affected, each for a stated reason:
`sequential improvement from the fourth quarter` (DAL) and `increase
sequentially up into March` (AAL) state one temporal comparison in the claim,
or an unanchored headline, so both texts select the same baseline; and `Total
unit revenue was 7.6% higher year over year, improving sequentially each month`
- every SERVED produced record on it carries no baseline at all, and neither
text speaks to an absent baseline. That is your rule applied literally: a
correctly supported prior-year headline is not changed because a sequential
number also appears.

## 4. Serving the new module to the existing preparer

`a7_correction_candidate_2118.prepare` reads `V` at CALL time for
`V.meaning_packet`, `V.extras_packet`, `V.batch_packet`,
`V.matched_inventory` and for `pin = G._sha_file(V.__file__)`, and the module
re-exports `record_view`, `matched_inventory` and `eligible_comparators`, so
rebinding `V` to the contract module serves all of those. The packet round
trip also closes: `_packet_builder` feeds contract-pinned packets into
`V.batch_packet`, which converts each back to the base pin, lets the frozen
`BASE.batch_packet` group the unchanged evidence, then re-versions the result.
`prepare`'s pin and the packets' `input_correction_sha256` then both equal the
contract module's own hash.

**One real connection problem inside 2118.** `CORRECTED_RULES = {'G2':
V.meaning_rules, 'G3': V.extras_rules}` is evaluated at IMPORT time, and
`versioned_candidate` installs `R.KIND_RULES = dict(CORRECTED_RULES)` at call
time. `R.kind_candidate` then computes `rules_block_sha256` from
`KIND_RULES[kind]()`. So a caller that rebinds only `V` gets prompts carrying
the corrected instructions and a rules pin naming the OLD ones - silently, and
that pin is the candidate's claim about the text its prompts carry. Smallest
remedy, no new mechanism: build the mapping from `V` inside
`versioned_candidate` (`R.KIND_RULES = {'G2': V.meaning_rules, 'G3':
V.extras_rules}`) so one rebinding cannot drift from the other.

**One real connection problem downstream.**
`score_corrected_grading_2162.validate_revision` refuses unless
`correction['input_correction_sha256'] == G._sha_file(V.__file__)` with `V`
imported as `a7_grading_input_correction_2114`. A candidate prepared through
the contract module carries the CONTRACT hash, so final scoring refuses it.
`a7_grading_revision_2115` does not have this problem - it only checks that
the candidate and the descriptor agree, so it is version-agnostic.
`a7_g2_key_reuse_2159` compares the selection's declared renderer path with
`V.__file__`; that stays satisfiable because the contract module does not
change `record_view`, but the selection must keep naming 2114 as the display
owner.

**No transport problem.** The two replacements are +155 and -13 bytes, +142
per prompt. The served limit is `SCRIPT_BYTE_LIMIT = 524288` and the largest
current prompt is 483,217 bytes, so no batch re-splits and the one-item
refusal path is not reached.

## 5. What this review does NOT establish

That any of the 15 will answer differently - nothing was called. That the 411
unaffected were graded correctly; unaffected means the two clauses do not move
their required answer, not that their verdict is right. That the module's own
23 cases and the 262-test regression pass - I read the module and the served
prompts, I ran no test of yours. That the metric-state clarity lead in
FINAL_DESIGN 4.3 is settled; it is outside these two fixes and I did not
widen into it. And the material effect of the 5 OPEN rows stays open: I have
not converted one of them into a call in order to shrink the number.

## Files

| File | What it is |
|---|---|
| REVIEW_2169.md | this review |
| AFFECTED_POPULATION_2169.json | every one of the 61 frontier questions with leg, source, gold/produced index, the claim it sits on, its role, which surface served it, and its reason |
| derive_affected_population_2169.py | the read-only derivation; needles only RECOGNISE a claim and the script refuses unless each names exactly one served quote |
