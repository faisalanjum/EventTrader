# Step 3 — Build the one shared production meaning reader

## Plain goal

Replace the saved test answers with one real production reader. It receives an
already-located source item, asks Sonnet 5 at high effort what it means, and
returns either:

* one or more exact candidate facts; or
* one clearly located abstention when meaning is uncertain.

Existing Core code remains responsible for checking evidence, periods, units, identities, and outcomes.

Channel finds and copies evidence
↓
One shared meaning reader — STEP 3
↓
Existing Core checks
↓
Identity decision system — STEP 4

## Required starting state

Do not begin until:

* Step 0 has frozen the exact starting code and test state.

* Step 1 experiments are complete.

* Step 2 has signed the results and confirmed the exact Sonnet 5 high-effort
  configuration, prompt rules, and permitted behavior.

* Every observed reader error is either resolved or explicitly excluded.

* The working tree is clean or its exact reviewed state is recorded.

* No unresolved contract disagreement affects the reader.

## Authority

Apply `FINAL_DESIGN.md` §§1–7 for meaning and evidence, the frozen staged
`ChannelContractV2.md` for the V2 candidate boundary, the active
`ChannelContract.md` and `15_CandidateFactPacket.md` only to preserve the
untouched V1 route, `BUILD_AND_OPERATIONS.md` §§5, 8.1, and 11 for the reader's
handoff and ownership limits, and the signed Step 2 memo for measured model and
prompt choices. Current production code and frozen EXP-5 vectors prove the
starting implementation. Status, this work order, comments, history, and
scratch files are leads only.

## Frozen company-rename suggestion handoff

The owner froze this internal handoff on 2026-08-14. Keep the existing
per-item reader call and make its exact reply:

`source_id` · `facts` · `abstentions` · `continuity_hints`

`continuity_hints` is a required list on every reply. It is empty when no
rename is proposed and may contain zero or more proposals. Each proposal has
exactly:

`kind` · `old` · `new` · `quote` · `part_ref` · `occurrence_in_part`

`kind` is exactly `driver`, `slice_label`, or `measurement_token`. `old`,
`new`, `quote`, and `part_ref` are exact nonblank strings. The quote must equal
the current raw item's verbatim quote. The existing Core occurrence owner
checks `part_ref` and `occurrence_in_part`; do not create another locator.

The existing fact branch is unchanged: one or more facts or exactly one
abstention, never both and never neither. Rename proposals are separate and may
coexist with either lawful branch. A rename-only item carries its proposal plus
the ordinary abstention stating that it produced no DriverUpdate fact; a
proposal alone never satisfies item accounting.

A malformed proposal invalidates the whole reader reply before anything is
accepted. A structurally valid proposal that Step 4 later refuses on meaning
does not invalidate unrelated lawful facts. Repeated identical proposals are
idempotent and may never create a second relationship.

`FINAL_DESIGN.md` remains the meaning owner. Publish the exact transport once
in `ChannelContractV2.md` and its machine-readable surfaces; that contract
becomes `ChannelContract.md` at the atomic switch. The one production response
parser under Core is the code owner. Do not add another model call to find
proposals, another reader, fact field, fact type, response wrapper,
compatibility branch, generic extension mechanism, source locator, or standing
rename detector. Step 4's dedicated judge still reviews every nonempty proposal.

Step 1 preserves the original zero-call kit as history, then amends and
re-freezes the EXP-5 reader door before its first call. Therefore every real
EXP-5 reader reply already has the four-field shape. K-fields gold drafts use a
different, non-production door and are never replayed as reader responses.
Production must reject the old three-field shape; do not build a compatibility
adapter or derived reply copy. At least one fresh amended raw reply must prove
a lawful nonempty proposal.

## Exact ownership

| Responsibility                                             | Owner                                 |
| ---------------------------------------------------------- | ------------------------------------- |
| Find and copy the exact source text or table entry         | Each source channel                   |
| Decide what the words mean                                 | Shared artificial-intelligence reader |
| Produce a possible rename suggestion                       | Same reader call                      |
| Check response structure                                   | Core                                  |
| Check quote, source part, and occurrence                   | Existing Core evidence owner          |
| Check periods, units, slices, names, and allowed fields    | Existing Core owners                  |
| Supply and verify structured filing numbers and dimensions | Existing structured-filing door       |
| Decide reuse, creation, separation, or refusal             | Step 4 identity system                |
| Plan or perform database writes                            | Existing writer; not enabled here     |

## Strict scope

Build only:

1. one production-owned prompt and response builder;
2. one exact raw-response parser;
3. one shared reader callable from the existing V2 event path;
4. the smallest connection replacing injected fact answers;
5. focused tests and evidence required to prove those changes.

Do not build or change:

* source fetching or source-location code;
* separate readers for filings, calls, news, prose, or tables;
* the identity decision system;
* Driver creation;
* database writes;
* the V1-to-V2 switch;
* scheduling, retries, queues, monitoring, or recovery services;
* the catalog, read layer, or old-Guidance retirement;
* structured-filing binding rules;
* dependency versions;
* unrelated cleanup.

## Smallest design

* Keep run_event as the one event entry point. Do not add another public V2 wrapper.
* Keep the owner-frozen per-item reader handoff.
* Retain one narrow model-transport seam: exact prompt bytes in, exact raw reply bytes out.
* Tests may replace that transport with saved raw replies; they must no longer inject already-decided facts.
* Put the reusable reader under driver/core/.
* Production must never import from the experiment folder.
* The experiment tools may import the production prompt/parser owner.
* Move ownership; do not copy the experiment implementation.
* Delete the old duplicate builder only after exact equivalence is proven.
* Preserve historical experiment evidence and manifests; they are records, not runtime owners.

## Prompt ownership

The production prompt must be mechanically assembled from:

* the exact semantic rules approved in Step 2;
* Sonnet 5 at high effort, as confirmed for the exact role in Step 2;
* field names and allowed values read from their live Core owners;
* the exact response structure read from its single owner;
* one untrusted-evidence boundary;
* the supplied source event placed after that boundary.

Requirements:

* No second handwritten field list.

* No added examples, explanatory clauses, synonyms, or convenience rules.

* No company, industry, filing, table, or source-specific wording.

* No semantic regular expressions or word lists.

* No experimental file read at production runtime.

* Source text must remain data even when it resembles instructions.

* Given the frozen experiment vectors, the promoted builder must reproduce the previously frozen prompt bytes exactly, apart from the separately approved rename-suggestion amendment.

* Any approved amendment must be isolated and tested independently; it must not silently rewrite the proven fact-extraction rules.

## Reader input

The reader receives only the verified information required by the current V2 handoff:

* source identifier;
* source type;
* company symbol;
* fiscal-year-end month;
* source publication time;
* ordered source parts;
* one already-located raw item.

The reader must not receive or control the caller’s item position. It must receive independent copies so it cannot mutate the trusted event or audit record.

Tables use this same path: the channel supplies the exact table content as a named source part. The reader must not fetch, scrape, or reinterpret the original document structure.

## Reader output

For each lawful submitted item, return exactly the four top-level fields:

* `source_id`;
* `facts`;
* `abstentions`;
* `continuity_hints`.

The fact-accounting branch remains exactly:

* one or more facts; or
* exactly one abstention.

Never return both and never return neither.

`continuity_hints` is always a list and may be empty. Each entry has exactly
`kind`, `old`, `new`, `quote`, `part_ref`, and `occurrence_in_part`, with the
types, vocabulary, source binding, coexistence, and failure behavior frozen
above. A proposal never becomes a fact field and never changes fact identity.

Every fact must include:

* the exact fact type;
* the exact source-part name;
* the exact quote;
* the quote’s occurrence when repeated;
* the stated per-unit denominator when applicable;
* every field required by the live V2 fact owner.

Every abstention must include:

* the raw item’s exact quote;
* a nonblank reason;
* the exact source-part name;
* the quote’s occurrence when repeated.

Multiple facts are lawful only when the source item genuinely expresses multiple facts, such as an actual result and an expectation comparison. Nothing may disappear from accounting.

## Meaning versus mechanics

The model may decide:

* whether the item is a real fact;
* fact type;
* cause name and state;
* meaning of periods and units stated by the source;
* comparison basis;
* source-stated slices and measurement qualifiers;
* favourability meaning;
* whether a per-unit denominator is explicit;
* whether an explicit company rename deserves a temporary suggestion.

Code may perform only:

* exact JSON parsing;
* exact key and type checks;
* source-identifier comparison;
* quote and occurrence checks;
* exact decimal preservation;
* deterministic arithmetic;
* calls to existing period, unit, slice, identity, and validation owners;
* fail-closed routing.

Code must never infer meaning from words, concept names, company names, examples, or patterns.

## Text and structured-filing rules

For ordinary text:

* every scale marker must occur inside the exact quote;
* if more text is needed, extend the contiguous quote;
* if it cannot be supported exactly, abstain.

For a structured filing item:

* the reader may interpret the business meaning;

* it must not create or override the structured concept, dimensions, source proof, period, unit identity, or multiplier evidence;

* unit_scale_evidence remains null;

* verified structured metadata remains the evidence;

* the existing structured-filing door performs the final binding;

* both text and structured items continue through the same event route, not separate public systems.

## Exact response transport

Before parsing:

* preserve the model’s exact raw response bytes;
* bind them to the source, prompt hash, model identity, effort setting, and call identity;
* never overwrite an earlier response.

Parse using the existing exact-number behavior:

* fractional and exponent numbers become exact decimals;
* duplicate JSON keys reject;
* non-finite numbers reject;
* invalid JSON rejects;
* surrounding prose or code fences reject unless the frozen contract explicitly permits them;
* no floating-point conversion may occur.

Malformed output, timeout, truncation, wrong-source output, or transport failure must accept nothing. Do not invent a public result code or automatic retry; later operating work owns retries.

## Test-first implementation order

1. Freeze the starting tree, dependencies, prompt hashes, tests, and experiment evidence.

2. Derive an inventory of every current reader seam, prompt builder, response parser, reply branch, and exception outcome.

3. Add failing tests proving the production reader is absent and saved fact answers are still required.

4. Implement and test the owner-frozen rename-suggestion handoff.

5. Add failing prompt-ownership tests.

6. Promote the smallest production prompt owner.

7. Prove frozen prompt-byte and response-schema equivalence.

8. Redirect the experiment harness to that production owner.

9. Remove the duplicate experiment owner.

10. Add failing exact-transport tests.

11. Promote or reuse the existing raw-byte and exact-decimal behavior.

12. Add the shared reader using the Step 2 model settings.

13. Connect it to the existing V2 event route without adding a new public entry point.

14. Replay the saved four-field EXP-5 reader replies through the reader and
    real Core route. Never treat K-fields gold drafts as reader replies.

15. Run focused, affected, and full regression tests.

16. Freeze and review the exact final tree before any commit.

## Required tests

### Lawful controls

Cover:

* all four fact types;
* numeric and numberless facts;
* point, range, floor, and ceiling values;
* text prose and table text;
* every supported source type as an event shape;
* one item producing multiple lawful facts;
* one lawful abstention;
* unique and repeated quotes;
* identical quotes in different source parts;
* exact decimal values with many digits;
* text scale evidence inside the quote;
* structured-filing meaning with structured proof retained;
* explicit per-unit wording;
* uncertain per-unit wording causing abstention;
* a required empty `continuity_hints` list with a lawful fact;
* a required empty `continuity_hints` list with a lawful abstention;
* one lawful proposal with a fact and one with an abstention;
* a rename-only item carrying its ordinary abstention plus its proposal;
* several lawful proposals from one item;
* all three frozen proposal kinds;
* a unique rename quote and a repeated rename quote with its exact occurrence;
* the same saved four-field input and response producing identical parsed
  output.

### Hostile and boundary cases

Cover:

* missing, extra, misspelled, and wrongly typed fields;
* duplicate JSON keys at every nested level;
* non-finite and lossy numbers;
* wrong source identifier;
* facts and abstentions both populated;
* both empty;
* multiple abstentions for one item;
* missing, extra, misspelled, non-list, or null `continuity_hints`;
* a proposal missing a key, carrying an extra key, or using a wrong field type;
* an unknown proposal kind;
* a blank old endpoint, new endpoint, quote, or source-part name;
* a proposal quoting a different raw item;
* a proposal naming a missing part or wrong quote occurrence;
* a proposal with facts and abstentions both empty;
* rewritten or normalized quote;
* quote in the wrong source part;
* wrong occurrence number;
* scale evidence outside the quote;
* text attempting to supply structured-filing-owned fields;
* model-produced concept, member, or structured source proof;
* model attempt to mutate its input;
* source text containing prompt-like instructions;
* truncated, blank, invalid, or non-JSON responses;
* model timeout or transport exception;
* reordered independent inputs;
* repeated equivalent inputs;
* every response-validation and failure branch derived from the live code.

Every negative test needs a nearby lawful control. Expected answers must come from signed evidence or an independent calculation—not from the code being tested.

## Whole-class and real-data proof

* Test every signed Step 1 reader event suitable for replay with its exact
  hash-bound four-field raw reply.

* Test the complete current population of available V2 Fiscal events read-only.

* Account for every submitted item as facts, abstention, or an existing Core refusal.

* Report totals by source type, fact type, accepted facts, abstentions, refusals, and failure reason.

* Inspect every accepted mismatch and every unexpected abstention.

* Require zero observed confirmed-wrong accepted facts.

* Target complete recall wherever deleting an unnecessary restriction, reusing
  an existing owner, or making a smaller general correction recovers it without
  reducing precision. Measure any residual loss; never hide abstentions or add
  special-case machinery.

* Add permutation and mutation tests for every high-risk rule.

* Require 100% branch coverage for the new reader and changed connection code.

* Deliberately break prompt ownership, exact parsing, quote binding, and output accounting; each relevant test must fail.

* Use the saved four-field replies for ordinary testing. If none contains a
  lawful nonempty proposal, make the one fresh Sonnet 5 high-effort call
  required to prove that branch; freeze its exact input, prompt, count, retry
  rule, and ceiling first. No separate owner approval is required, and no
  synthetic response may prove that branch.

* Neo4j remains read-only and Driver/DriverUpdate counts must remain unchanged.

## Stop conditions

Stop and report one precise blocker if:

* Step 2 has not pinned the required model behavior;
* code, contract, prompt, or tests differ from the owner-frozen
  rename-suggestion handoff;
* a new semantic rule appears necessary;
* the live contract and live code disagree;
* exact prompt equivalence cannot be established;
* production would need to import experiment code;
* an existing owner cannot support required behavior;
* an unplanned or over-ceiling model call is needed;
* a database write would occur;
* a lawful input would be lost without an owner decision.

Do not patch around any of these with a list, regular expression, exception, fallback guess, or duplicate validator.

## Definition of done

Step 3 is complete only when:

* one production-owned reader serves every channel’s submitted prose and table items;
* production and experiments use one prompt and response owner;
* no production import points into the experiment folder;
* saved fact-answer injection is gone from the real V2 route;
* tests inject only the model transport or raw response bytes;
* every saved EXP-5 reader reply uses the four-field shape and no production
  compatibility path accepts the old shape;
* every lawful item yields one-or-more facts or exactly one abstention and
  always carries the required `continuity_hints` list;
* quotes, source parts, occurrences, numbers, and scale evidence are checked exactly;
* structured-filing proof remains owned by the existing structured door;
* zero or more approved rename proposals use the exact frozen shape, reuse the
  existing source locator, coexist lawfully, and never change fact identity;
* no semantic hardcoded string, list, number, threshold, regular expression, or example branch exists;
* every new behavior branch is tested and mutation-proven where material;
* real-data replay shows zero confirmed-wrong accepted facts and reports measured recall;
* focused and full regressions pass;
* the exact reviewed tree contains no unrelated changes;
* no database write, version switch, identity decision, activation, or
  unplanned model call occurred.

After review, commit this as a separate Step 3 change. Step 4 then builds the one system that decides whether each candidate reuses an existing Driver, creates a new one, remains separate, or is refused.
