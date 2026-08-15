# Step 2 — Freeze the experiment conclusions

## Purpose

Turn all Step 1 results into one trustworthy build decision before any production reader or identity code is written.

Step 2 answers:

1. Did the exact Sonnet 5 high-effort configuration pass each role's existing
   gate?
2. Which experiment results are trustworthy?
3. Did any result expose an unclear or incorrect rule?
4. Does attaching to an existing business cause require a second independent
   Sonnet 5 check?
5. Did the text-versus-machine-tag comparison require any existing rule adjustment?
6. Which already-approved day-one features must be built now, and which remain off?
7. May Steps 3 and 4 begin, or must a failed area stop?

Step 2 does not redesign the system. The identity design is already approved. It only freezes measured settings, required corrections and build permission.

## Required starting state

Step 1 must have reached a signed result for both lanes.

Required evidence includes:

* locked K-fields answer key;
* signed EXP-5 result;
* signed EXP-6 result;
* frozen Restaurant test catalog;
* locked K-stamp key;
* signed type-stamping result;
* locked second identity-pair key;
* signed identity-judge result;
* locked routing key;
* signed routing result;
* all prompts, raw replies, scores, manifests and exhibits;
* complete call and cost ledger;
* exact commits and trees for every published package.

Also verify:

* the old public format remains active;
* the new format remains staged and inactive;
* no production reader or identity system was built;
* Neo4j writes remain disabled;
* every Step 1 commit is reachable from the new clean starting commit;
* no unresolved Step 1 file drift exists.

## Authority

Apply `FableExperimentPlan.md` and `FableExperimentWorkOrder.md` for the frozen
protocol, the current package-status board and signed run artifacts for results,
`FINAL_DESIGN.md` for product meaning, and `BUILD_AND_OPERATIONS.md` for what a
result may unblock. Current code and recomputed raw output prove mechanical
claims. Status prose, history, comments, commits, handovers, and scratch files
are leads only.

The 2026-08-14 owner ruling in `Steps.md` is binding: every still-unrun model
call uses Sonnet 5 at high effort, needs no separate call approval, and has no
automatic fallback. Earlier completed model comparisons remain evidence. A
role that this exact configuration fails remains stopped.

## Scope

This step reconciles evidence, freezes measured model roles and settings,
obtains only triggered owner rulings, and applies any approved wording change at
its one live owner. It does not build production code, change an active
contract, rerun a paid experiment, activate a feature, or write to Neo4j.

A signed failure is valid evidence, but it cannot authorize the affected production build.

## Roles

* Core implementer: collects and mechanically reconciles the evidence.
* Fable: reviews every dangerous merge, unclear rule, disputed grade and
  whether Sonnet 5 passed each role's gate. Any model-assisted review uses a
  separate blind Sonnet 5 high-effort call.
* Codex: independently verifies the denominator, raw evidence, calculations and proposed decisions.
* Owner: approves rule changes, triggered identity changes and publication;
  the model and effort are already fixed.

The call that produced an answer may not approve or grade that answer. Required
review uses a separate blind Sonnet 5 high-effort call and source-grounded
truth.

## Minimal output

Create only one new durable document:

/home/faisal/EventMarketDB/.claude/plans/Drivers/experiments/RESULTS_MEMO.md

It contains:

* the complete experiment conclusion;
* model-role table;
* identity-system settings;
* router decision;
* text-versus-machine-tag decision;
* unresolved or blocked items;
* owner rulings.

Reuse existing owners for everything else:

* raw evidence stays in its run directory;
* dangerous merges stay in existing wm_* exhibits;
* unclear rules stay in existing ra_* exhibits;
* calls and costs stay in BUDGET.json;
* package state stays in WORKORDER_STATUS.md;
* exact model identities stay in run manifests.

Do not create another dashboard, ledger, crosswalk or decision framework.

## Exact evidence denominator

Derive the inventory from the live board, manifests and run folders—not memory.

Account for:

1. every row in the current 20-row package-status board inside
   WORKORDER_STATUS.md, plus every visible current-board row Step 1 adds;
2. every locked answer key and every record inside it;
3. every declared experiment arm;
4. every expected and actual model call;
5. every raw response;
6. every parsed response;
7. every retry and invalid response;
8. every score row and denominator;
9. every accepted, parked, skipped and rejected item;
10. every missing fact and duplicate emission;
11. every wm_* dangerous-merge exhibit;
12. every ra_* unclear-rule exhibit;
13. every failed or inconclusive case;
14. every triggered conditional arm;
15. every model identity and effort setting;
16. every budget entry;
17. every input, prompt, key, scorer and result identity;
18. every owner decision triggered by the results.

Expected current board baseline: 20 package rows. The append-only history below
that board is evidence, not additional package rows. If Step 1 adds a current
board row, the visible denominator must increase and the new row must be
included.

Nothing may disappear because it was inconvenient, invalid or later corrected.

## Work

### A. Freeze the exact result set

1. Start from a clean isolated folder containing all reviewed Step 1 commits.
2. Record the commit and tree.
3. Record every input, key, manifest, run directory, scorer and decision identity.
4. Confirm the staging area is empty.
5. Confirm no experiment artifact changed after its signed result.
6. Confirm every answer key remained immutable after locking.
7. Confirm every raw response predates its parsing and grading.
8. Confirm no model saw hidden truth, future evidence or another model’s reply.
9. Confirm Neo4j was not written.
10. Confirm production code did not import experiment code.

Any changed locked artifact invalidates the affected conclusion until explained.

### B. Reconcile calls and responses

For every run:

* expected calls = completed + failed + permitted retry + explicitly skipped conditional calls;
* every completed call has one raw-response identity;
* every raw response has one manifest entry;
* every parsed response points to one raw response;
* every score points to one parsed response;
* no response is overwritten or counted twice;
* every model alias resolves to one recorded exact model identity;
* every effort setting matches its approved manifest;
* every cost is recorded;
* rejected service attempts that produced no response are reported separately and never counted as completed work.

Any unexplained difference blocks the result.

### C. Recompute mechanical results

Using the existing scorers:

1. recompute every deterministic metric from the frozen raw and graded records;
2. compare the recomputed values with each saved scores.json and decision.json;
3. rerun existing scorer corruption and permutation controls;
4. verify one produced fact cannot credit two reviewed facts;
5. verify reordered inputs produce identical results;
6. verify a planted wrong merge fails;
7. verify a planted missing fact lowers recall;
8. verify a planted duplicate fails the reliability gate;
9. verify future evidence is excluded;
10. verify every “zero wrong in N” statement includes the 3/N upper risk bound.

Do not call graders again merely because a score is inconvenient. The experiments are graded once.

If a scorer defect is found:

* invalidate every result that used it;
* reproduce the defect with a failing test;
* make the smallest scorer-owner fix;
* prove it with lawful and corrupted controls;
* rerun only under the existing fresh-sample rule;
* never recalculate the old sample and call it an independent pass.

### D. Classify every observed problem

Every error must enter exactly one class:

| Class                     | Required action                                                 |
| ------------------------- | --------------------------------------------------------------- |
| Model weakness            | Stop that capability; do not select another model                |
| Missing model context     | Use only the already-tested context improvement that solved it  |
| Retrieval/display failure | Correct the one display owner; do not blame the identity model  |
| Unclear official rule     | Create one proposed amendment at the rule’s existing owner      |
| Incorrect answer key      | Version the key and rerun only on a fresh sample                |
| Scorer or harness defect  | Fix test-first, invalidate affected results and rerun properly  |
| Reliability failure       | Reject the arm; do not average it away                          |
| Real safety failure       | Stop the dependent production build                             |
| Recall loss               | First test whether an already-proved or smaller general owner-level correction recovers it without reducing precision; accept only the residual |
| Harmless diagnostic       | Record it without creating work                                 |

Never create an example-specific exception, list, pattern, regular expression or second rule engine.

### E. Review every dangerous merge

Fable reviews every wm_* exhibit individually.

For each exhibit, record:

* experiment and arm;
* candidate and chosen target;
* exact source evidence;
* whether the correct target was visible;
* reviewed truth;
* model decision;
* cause of the failure;
* whether the answer key was correct;
* affected business-cause family;
* required owner action;
* whether the affected production lane is stopped.

No aggregate total may replace this review.

Zero dangerous merges means zero observed in the measured sample—not proof of mathematical perfection.

### F. Resolve every unclear rule

Fable reviews every ra_* exhibit.

For each:

1. name the exact existing rule owner;
2. show the two competing lawful interpretations;
3. prove the current text does not settle them;
4. propose the smallest general clarification;
5. show the real failure it prevents;
6. list a lawful control that must remain accepted;
7. state whether the clarification changes an experiment answer or score;
8. state whether a fresh sample rerun becomes necessary.

Forbidden responses:

* adding an experiment-only exception;
* adding a vocabulary or regular expression;
* copying the rule into another document;
* treating the experiment’s answer as authority;
* silently choosing one interpretation.

If the owner has not ruled, the dependent build remains blocked.

### G. Freeze the Sonnet 5 role table

For every production role, record:

* role—not a hardcoded model choice inside semantic logic;
* exact tested Sonnet 5 runtime identity;
* high effort;
* experiment and arm supporting the choice;
* measured precision;
* measured recall;
* wrong-accept count;
* refusal or park rate;
* invalid-response rate;
* cost;
* `fallback: none` for the first release;
* behavior if the exact model becomes unavailable.

Roles to settle include:

* blind text reader;
* fact producer;
* routing proposer;
* permanent identity judge;
* grader;
* type/family judge;
* recovery judge;
* any independent Sonnet 5 high-effort reviewer required by a frozen proof.

Rules:

* every first-release semantic role uses Sonnet 5 at high effort and must pass
  that exact role's gate;

* any role that can change identity, family, type, linking, quarantine or
  recovery stops if Sonnet 5 at high effort does not qualify;

* preserve independent blind Sonnet 5 producers, judges, and graders where the
  proof requires them; the call that produced an answer never grades that same
  answer;

* do not add a weaker proposal stage, automatic escalation, provider
  substitution, vote, or fallback call;

* model identities are pinned in manifests, never selected by semantic code;

* aliases are never stored as final identities;

* unavailable or changed models stop the role until requalified;

* qualification transfers to no other model or Sonnet version;

* no effort setting inherits qualification from another effort setting.

Do not optimize model cost in Steps 2–13. Step 14 remains dormant unless a
future owner ruling permits a different model after Step 13 closes.

### H. Decide the router question

EXP-3 determines whether attaching to an existing cause needs an immediate
second independent Sonnet 5 confirmation.

Prepare one owner decision:

* Not triggered: measured routing had zero dangerous attachments under the frozen requirements; preserve the already-approved design.

* Triggered: a dangerous attachment occurred while the correct target was
  visible; require the existing Sonnet 5 high-effort identity judge before an
  attachment becomes permanent.

* Blocked: evidence or scoring is inconclusive; do not build the affected attachment path.

Do not add a new judge. Reuse the one qualified identity judge.

Record the decision even when no change is required.

### I. Settle the text-versus-machine-tag findings

Combine the already-signed machine-tagged filing result with EXP-6.

For every difference, record whether its owner is:

* period;
* slice;
* measurement;
* value or scale;
* machine-tag concept binding;
* answer-key error.

Then prepare the O12 decision:

* list each required pin adjustment;
* show its exact measured evidence;
* show whether it changes current meaning or only clarifies deterministic mechanics;
* record any systematic failure above 5%;
* state whether the suppression design must reopen;
* state whether later machine-tag automation remains blocked.

The machine-tag design was already approved in July. Step 2 does not approve it again. The owner only:

* accepts the measured pin adjustments;
* rejects them;
* or records that no adjustment is required.

No machine-tag automation is activated here.

### J. Freeze the smallest day-one identity build

Use the measured results to fill only the settings still awaiting evidence.

The already-approved day-one core remains:

* reuse, adopt, create, skip and park decisions;
* born-complete creation;
* one delayed same-meaning link mechanism;
* frozen birth evidence;
* establishment and broadness controls;
* existing validators;
* model-free warning signals;
* attachment audit;
* minimal calibration;
* quarantine and recovery;
* static seed checks;
* outage and retry discipline.

Choose only:

* exact model membership by role;
* router display size proven by EXP-3;
* full-evidence versus frozen-anchor judge input proven by EXP-4A;
* whether direct attachment needs immediate independent Sonnet 5 confirmation;
* reader model, chunk and run count;
* fact-producer model and run count;
* whether the simple seed checks are sufficient or the full planted set is required;
* whether no-machine-tag qualitative causes may launch.

Keep these off unless their exact experiment trigger fired:

* automatic claims;
* extra anchor enrichment;
* item-code hints;
* an additional “unsure” state;
* union preview;
* extra warning systems;
* model-result caching;
* multi-run voting;
* speculative thresholds;
* optional future tuning.

Qualitative-safety rule:

* day-one admission includes source-grounded proposals from certified prose and
  human-readable table evidence, including qualitative and action causes;

* the required independent qualitative warning system must ship before any
  such proposal may create a Driver; until it passes, that proposal parks.

Do not weaken this boundary to improve recall.

### J2. Apply the owner-frozen temporary rename-suggestion handoff

Owner ruling, 2026-08-14:

* Keep the existing per-item reader handoff.
* Extend its exact reply to exactly `source_id`, `facts`, `abstentions`, and
  one required top-level `continuity_hints` list.
* The list is always present, is empty when there is no proposal, and may hold
  zero or more proposals.
* Each proposal has exactly `kind`, `old`, `new`, `quote`, `part_ref`, and
  `occurrence_in_part`.
* `kind` is exactly `driver`, `slice_label`, or `measurement_token`.
  `old`, `new`, `quote`, and `part_ref` are exact nonblank strings.
* The proposal's quote must equal the current raw item's verbatim quote.
  `part_ref` and `occurrence_in_part` reuse the existing Core occurrence
  checker; no second locator exists.
* The existing reply rule remains: one or more facts or exactly one
  abstention, never both and never neither. Proposals are separate and may
  coexist with either lawful branch. A rename-only item therefore includes one
  ordinary abstention as well as its proposal; a proposal alone never satisfies
  item accounting.
* A malformed proposal invalidates the reply before anything is accepted. A
  structurally valid proposal later refused on meaning does not invalidate
  unrelated lawful facts.
* Repeated identical proposals are idempotent and may never create a second
  relationship.
* `FINAL_DESIGN.md` remains the meaning owner. Step 3 publishes the exact
  transport once in `ChannelContractV2.md` and its machine-readable surfaces;
  that contract becomes `ChannelContract.md` at the atomic switch. Core's one
  production response parser is the code owner.

Do not add a second model call to find proposals, hide one inside a fact,
create a second quote locator, add a response wrapper or compatibility branch,
or invent a standing rename detector. Step 4's dedicated continuity judge
still reviews every nonempty proposal. Record this ruling and its required
Step 3 regressions in the signed memo; do not ask the owner again.

### J3. Apply the owner-frozen cross-company reuse ruling

The owner ruled on 2026-08-14 that no `BROAD` Driver label or company-count
threshold exists. Record and propagate the smallest amendment before Step 4:

* Driver reuse across companies is decided only by the ordinary identity
  system;
* company count never coins, merges, ranks, establishes, validates, or selects
  a Driver;
* a cross-company read derives its eligible companies from current facts and
  naturally returns no comparison when fewer than two exist;
* no `BROAD` property, tag, cache, configuration, or replacement state is
  built;
* the existing meaning, evidence-coherence, quarantine, recovery, and native
  fact safeguards remain intact.

Replace the `BROAD` shorthand in the live owner documents through the normal
authority-amendment procedure. Do not add production code in this step and do
not ask the owner to decide this again.

### K. Produce the one signed result memo

The memo must contain:

1. exact starting and ending commit/tree;
2. complete package denominator;
3. key and sample identities;
4. every model, effort and call count;
5. exact budget;
6. every pre-registered requirement and measured result;
7. every precision, recall, park, skip and invalid rate;
8. every dangerous merge;
9. every unclear rule;
10. every failure or inconclusive result;
11. model-role table;
12. router decision;
13. machine-tag decision;
14. day-one identity settings;
15. features kept off;
16. every blocked production lane;
17. exact owner decisions still required;
18. proof of zero Neo4j writes;
19. the owner-frozen temporary rename-suggestion handoff;
20. the owner-frozen no-`BROAD`, natural cross-company reuse ruling;
21. explicit statement that no production code or activation occurred.

Fable signs the evidence interpretation. Codex independently verifies the exact document and referenced identities.

### L. Obtain owner rulings

Present only genuine decisions:

The channel-proposal boundary is already settled and must not be presented
again: an authorized channel supplies evidence; the shared reader may propose
from prose or a human-readable table; Core alone decides identity; and
machine-tagged XBRL alone cannot create a Driver.

* any unclear rule amendment;
* router second-confirmation decision if triggered;
* machine-tag pin adjustments;
* day-one optional settings that evidence actually triggered;
* any residual measured recall loss after simple general recovery options are exhausted;
* any separately metered non-model service required for the next build.

Do not ask the owner to reapprove already-settled design.

For every decision, record:

* exact question;
* recommended smallest safe answer;
* alternative;
* measured impact;
* owner answer;
* date;
* affected owner document;
* whether a rerun is required.

### M. Apply approved authority changes

Only after the owner rules:

1. edit the single document that owns the rule;
2. add the smallest necessary wording;
3. update the status/history owner separately;
4. do not edit archived designs;
5. do not rewrite frozen experiment results;
6. record that results were measured under the earlier pinned version;
7. regenerate dependent prompts or manifests only when the approved rule actually changes them;
8. if the change affects the test truth, return to Step 1 with a fresh answer sample;
9. run the required document-reader check when rule meaning, mechanics, gates or owner decisions changed.

No production implementation belongs in this step.

## Result states

Step 2 must end in exactly one state:

### GO

All required experiments passed, every issue is settled, model roles are pinned and Steps 3 and 4 may begin.

### LIMITED GO

Only explicitly named production lanes have sufficient evidence. Other lanes remain disabled. The owner must approve this narrower build boundary.

### STOP

A required experiment failed, remained inconclusive or exposed an unresolved rule. The affected build must not begin.

Do not label STOP as “complete enough.”

## Tests and proof

Because Step 2 changes no production behavior:

* no production TDD is required;

* no full production regression is required unless an approved authority edit changes generated rules or guards;

* deterministic scorer, manifest, reference and document checks are required;

* any scorer correction requires TDD and fresh-sample handling;

* any rule amendment must name the future production regression it requires;

* no new proof framework may be added unless existing manifests and tests cannot establish a named requirement.

## Publication plan

Use separate reviewed commits:

1. result memo plus final experiment-board and budget updates;
2. each approved authority amendment, grouped only by its single owner;
3. status/history update.

Before each commit:

* stage only the named files;
* verify every staged identity;
* verify no production code is included;
* record the staged tree;
* obtain Codex review;
* obtain Codex `VERIFIED` on the exact staged identity;
* push normally, never force-push;
* verify local and remote identities match.

## Stop conditions

Stop immediately if:

* Step 1 artifacts are incomplete or changed;
* a raw response or answer-key row is missing;
* a score cannot be reproduced;
* an answer key changed after locking;
* a tested model helped approve its own role;
* an experiment result is being stretched beyond its measured population;
* an unclear rule lacks owner resolution;
* a candidate contradicts the owner-frozen rename-suggestion handoff;
* a failed result is being converted directly into code;
* a model name, threshold, pattern or exception is being invented;
* a second decision owner is proposed;
* a rule edit would silently invalidate the frozen experiment;
* any Neo4j write or production activation is attempted;
* an unapproved commit or push would occur.

## Completion condition

Step 2 is complete only when:

* every experiment package and arm is accounted for;
* every dangerous merge is individually reviewed;
* every unclear rule is resolved or explicitly blocks its lane;
* every failed or inconclusive result has an honest disposition;
* exact model roles and effort settings are pinned;
* every semantic role is pinned to Sonnet 5 at high effort and records no
  automatic fallback;
* the router decision is recorded;
* the machine-tag adjustment decision is recorded;
* the temporary rename-suggestion handoff is owner-frozen;
* the smallest day-one identity settings are owner-approved;
* all untriggered features remain off;
* the result memo is signed and independently verified;
* every required authority change is published;
* the final outcome is clearly GO, LIMITED GO or STOP;
* no production behavior, database data or active contract changed.

Only a GO—or the exact owner-approved portion of a LIMITED GO—may proceed to Step 3.
