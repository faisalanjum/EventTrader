

# Random Thoughts

1. Should we make predictor give exact predicted return so may be we can compare againt actual return and see the difference which may also be used to choose between different setups or for optimization? Pros & cons

2. This 30 chars limit seems arbitrary - any pros and cons of removing it? "validator rejects anything under 30 characters on the four narrative fields"?

3. Since some of these lessons are generic and may not apply for a very long time, it may make sense to not retre lessons based on how long has it been?

4. The predictor needs source context, but keep it outside `lesson_text` and mostly outside `mechanism`. `lesson_text` should stay the reusable rule; `mechanism` should stay the reusable cause-effect chain. When implementing this, update both learner mechanism instructions together: the `mechanism` field row and the standalone reweighting rule. Add a prompt-side invalid-lesson signal for source-only dates, event names, or case details that are not reusable or future-verifiable. `Context-Only` should carry an `L#` source map for every rendered lesson with source ticker, source quarter, learner_result, and source outcome / primary driver when available. Prefer stamping global lesson outcome / primary-driver fields at write time in `append_global_lessons` over renderer-time cross-file lookup.

5. Is there a reason we limit the number of lessons - as long as the quality of lessons is super high - so rather than limiting the number of lessons, we should focus on increasing the bar of top notch quality.



# Rules for Chanding Prediction & Learner Skill

1. We must NEVER include hardcoded examples  in skill since LLMs tend to over-anchor on these examples.

Learner:
2. Do not use numeric thresholds unless the evidence supports them but if you must include it, it should clearly be marked as opinionated or something.

3. Require every lesson to answer: 'What should the future predictor do differently?'


Predictor:
3.  We should steer the model to be super diligent as well as make use of its own reasoning by first collecting all relevant facts in an effort to maximize the usefulness of these lessons and never follow these lessons blindly.


# ToDo

1. Tighten lesson transfer. Promote a lesson beyond ticker scope only when the source bundle shows real transfer evidence, not because it sounds plausible.
   - `sector`: peer/sector evidence shows the same setup, or the mechanism is truly sector-wide.
   - `cross_ticker`: a named transmission link exists between specific tickers.
   - `macro`: only for true market-wide regime mechanics.
   - Otherwise keep it `ticker` scope.

2. Make the asymmetry explicit in learner guidance: over-broad lessons can mislead many future calls; under-broad lessons only reduce coverage. Default narrower when unsure.

3. Audit current global lessons for theoretical promotions. Any sector lesson promoted without peer evidence or multi-event proof should be narrowed or refined.


# Review by Faisal

### Page 2


1. I so wish mechanism was more structured - if this than that than that
  than that and so on but does that help our end goal? and should we try
  to do something like that and if yes, how be absolutely certain about
  this.


• Yes, it helps our end goal, if we do it lightly.

  I would not add a new schema field. I would only tighten the existing
  mechanism instruction.

  Best rule:

  `mechanism` should read as a short causal chain: observable setup →
  expectation/anchor change → market participant response → prediction
  implication. If any link is unclear, emit no lesson.

  Why this helps accuracy:

  - It forces real cause-effect, not story.
  - It makes applies_when and invalid_if easier to write.
  - It helps the predictor understand why the lesson matters, not just when
    it fires.

  What I would avoid:

  If X then Y then Z...

  as a literal required format everywhere. That can become robotic and
  overfit. The better version is the causal-chain requirement, not a rigid
  template.

  So my recommendation is: yes, add one minimal mechanism rule, no schema
  change, no examples.

2.


### Page 3



### Page 2


### Page 2


### Page 2


### Page 2


# Notebook LM suggestions:

To make the system smarter at learning by addressing current friction points like "lazy" predictors and slow lesson compounding, here are three finalized design suggestions:
1. Adversarial Predictor Debate (The "Anti-Lazy" Gate)
The current system allows the predictor to take a "cheap escape" by labeling lessons as "irrelevant" with the generic sentinel "no relevant evidence"
. To eliminate this, the Predict phase should be redesigned as a structured debate
.
Mechanism: For every lesson in the gauntlet, run parallel Claude prompts: a "Proponent" tasked with finding evidence of applicability and an "Adversarial Auditor" tasked specifically with proving the lesson is "irrelevant" or "contradicted" by citing the invalid_if triggers
.
Context: The orchestrator only accepts an "irrelevant" label if the Adversary can pinpoint a specific missing precondition (e.g., the warning was >6 weeks old)
. This forces the system to actively engage with the Mechanism field rather than passively skipping it
.

2. 2. Recursive Back-Attribution (Synthetic Hindsight)
Currently, new lessons are born into an "unproven" tier and must wait for future quarters to accumulate a track record
. This makes the system slow to compound memory
.
Mechanism: At the moment of Step 5 (Birth), the orchestrator should trigger a "Synthetic Audit"
. It automatically pulls context bundles from the previous four historical quarters and asks the Learner: "If this lesson had existed then, would it have helped or misled?"
.
Context: This allows a new lesson to enter the library as "proven" or "promising" on Day 1
. It turns linear time-based learning into recursive learning, ensuring that "units of memory" carry immediate, validated weight instead of starting as blank slates

3. MAY - Not vetted:
3. Signature-Based Micro-Regime Routing
The sources show that "neutral" audits often occur because a lesson is routed too broadly to a ticker or sector when it actually only applies to a specific "post-disaster" or "event" regime
.
Mechanism: Elevate the applies_when narrative into a hard machine-readable filter in Step 6 (Read)
. Instead of just matching by ticker or sector, the Build phase must identify a "Micro-Regime Signature" (e.g., a quantified 8-K warning within ~4 weeks) before the lesson is allowed to reach the predictor
.
Context: This prevents "stale-neutral" signal noise from cluttering the predictor's limited cap space
. By ensuring the predictor only sees contextually-specialized memory, you avoid penalizing good lessons for being irrelevant in the wrong environment
.


# Learner Loop Diagram

```text
EVENT QUARTER N
====================================================================================================================

  1) BUILD
     earnings_orchestrator.py builds the prediction bundle for one ticker + quarter.

     Inputs on disk:
       - company event bundle / SEC filings / market data / transcript evidence
       - prior ticker lessons:
           earnings-analysis/learnings/ticker/{TICKER}.json
       - prior global lessons:
           earnings-analysis/learnings/global.json

     Two time boundaries exist by design:
       - predictor PIT cutoff:
           what the predictor is allowed to know before making the forecast
       - learner PIT cutoff:
           what the learner is allowed to know after the actual market reaction is known

     Same-quarter self-leak guard:
       - lessons born from the same ticker + same quarter are excluded from that quarter's prediction context


                                                |
                                                v


  2) READ PRIOR MEMORY
     build_learning_context(...) loads lessons from ticker and global stores.

     Stored lesson identity:
       lesson_id = "lsn_" + sha256(normalized lesson body | scope | routing_key)[:10]

     Storage:
       ticker lesson store:
         - keyed by source_ticker + quarter_label
         - stores ticker-scoped lessons
         - no file lock
         - atomic write

       global lesson store:
         - keyed by source_ticker + quarter_label
         - stores sector / macro / cross_ticker lessons
         - fcntl.flock lock
         - atomic write

     Each lesson can carry audit_history:
       - per-lesson list of future learner audits
       - each audit says how the lesson performed when later predictions used or ignored it


                                                |
                                                v


  3) FILTER + RANK + CAP
     Current coded gauntlet before lessons reach the predictor.
     Order matters — retired lessons must be dropped BEFORE caps,
     otherwise dead lessons quietly consume cap slots.

       [A] source PIT filter
           - historical lessons must have source_pit_cutoff <= predictor PIT cutoff
           - live mode may include live lessons

       [B] same-quarter self-leak prevention
           - current ticker + current quarter lessons are excluded

       [C] audit PIT filter
           - historical audit entries must have audit_pit_cutoff <= predictor PIT cutoff
           - future audits are invisible during replay

       [D] status state machine
           visible audit_history is reduced into:

             active:
               usable lesson

             watch:
               lesson had enough recent misled reviews to show caution

             retired:
               lesson is hidden from future predictor context
               (DROPPED here — never reaches scope routing or caps)

           Current thresholds:
             audit window: last 5 visible audits
             misled >= 2: watch
             misled >= 3: retired
             explicit learner action retire/refine: retired
             missed no longer penalizes status
               (predictor underuse is not lesson weakness)

       [E] scope routing  (globals only — ticker scope skips this stage)
           - sector lessons match ticker sector
           - macro lessons route broadly
           - cross_ticker lessons route only when current ticker is in routing key

       [F] recency ranking + caps
           current coded ranking is mostly newest source events first

           caps:
             ticker lessons:       8 source rows  (each row holds 1-3 lessons)
             sector global rows:   4
             macro global rows:    4
             cross-ticker rows:    2


                                                |
                                                v


  4) RENDER FUTURE LESSONS
     renderer/lessons.py turns surviving lessons into the predictor prompt.

     Predictor sees:
       - Lessons To Label:
           L1, L2, L3...
           each with:
             Lesson
             Mechanism
             Applies when
             Invalid if
             optional watch caution / audit counts

       - Context-Only Source Events:
           source quarter context, prior learner result paths, data lessons

     Predictor does NOT label context-only source events.
     Predictor labels only rendered L# lessons.


                                                |
                                                v


  5) PREDICT
     earnings-prediction skill must output prediction/result.json.

     Required lesson_labels shape:

       lesson_labels: [
         {
           "lesson_text": exact rendered Lesson body only,
           "label": "confirmed" | "contradicted" | "irrelevant",
           "bundle_evidence": "..."
         }
       ]

     Rules:
       - one label per rendered L#, in order
       - lesson_text must match the rendered lesson body
       - only confirmed lessons may be cited in cites_lesson_indices
       - contradicted / irrelevant must NEVER be cited
       - a confirmed lesson does not have to be cited
       - "no relevant evidence" sentinel is allowed only for irrelevant

     Current lazy failure:
       - predictor can mark all lessons irrelevant
       - can use "no relevant evidence" repeatedly
       - can cite zero lessons in key_drivers
       - validator catches shape and citation mechanics, but not deep engagement quality


                                                |
                                                v


  6) ACTUAL OUTCOME ARRIVES
     After the event, actual stock reaction and post-event evidence exist.

     Two hard gates fire BEFORE the learner is invoked:
       [1] prediction/result.json must exist
           else SKIPPED_NO_PREDICTION
       [2] Neo4j PRIMARY_FILER.daily_stock must be non-null
           else SKIPPED_NO_DAILY_STOCK

     Learner PIT fallback (only used when historical):
       [1] next quarter filed_8k boundary
       [2] live_state filed_8k boundary
       [3] invocation time


                                                |
                                                v


  7) LEARN
     earnings-learner skill writes learning/result.json.

     Important asymmetry between the two skills:
       - predictor runs in a FORKED skill (no Data SubAgent tools)
                  reads ONLY the bundle + allowlisted prior learner reports
       - learner runs as an SDK EMBED in the main session
                  has full Data SubAgent access — can fetch post-event
                  news, transcripts, XBRL, peer reactions, etc.

     It must:
       - explain why the stock moved
       - compare prediction vs actual
       - create new reusable lessons
       - audit every lesson_labels entry from the prediction

     Learner output includes:
       predictor_lessons:
         - new ticker-scoped reusable lessons (structured, see below)

       global_observations:
         - new sector / macro / cross_ticker reusable lessons (structured)

       data_lessons:
         - data / evidence collection improvements (plain list[str])

       lesson_audit:
         one audit entry per prediction lesson label, in the same order

     Each new lesson is a STRUCTURED 5-field object:
       lesson         >=30 chars   the rule the future predictor copies verbatim
       mechanism      >=30 chars   the causal chain (who reweights what, why)
       applies_when   >=30 chars   bundle preconditions
       invalid_if     >=30 chars   failure-mode triggers
       evidence_refs  >=1 ID, every ID must resolve in this run's evidence_ledger


                                                |
                                                v


  8) AUDIT PRIOR LESSONS
     lesson_audit is the learner's judgment of how each rendered prior lesson performed.

     review enum has 6 values:
       helped:
         predictor used the lesson AND the outcome aligned

       misled:
         lesson reasoning or trigger was bad — predictor used it on a wrong call
         OR falsely confirmed it when it should not have applied
         (this is the ONLY review value that drives status changes)

       outweighed:
         predictor used the lesson; mechanism was real;
         other forces dominated the move (does NOT penalize the lesson)

       missed:
         predictor labeled irrelevant / didn't cite,
         but hindsight shows the lesson actually applied

       neutral:
         predictor's per-lesson label was correct
         (e.g. labeled irrelevant AND lesson really didn't apply)

       unclear:
         hindsight cannot isolate the lesson's effect on the move

     action enum has 3 values:
       keep:
         leave lesson as-is

       refine:
         retire old lesson and add a replacement

       retire:
         hide lesson from future predictor context

     Cross-file gates:
       - audit count must equal prediction lesson_labels count
       - audit lesson_index must match rendered position
       - audit predictor_label must match prediction label
       - audit was_cited must match whether prediction cited that lesson
       - audit lesson_text must match the original lesson body


                                                |
                                                v


  9) MUTATE MEMORY
     Orchestrator appends new lessons and applies audits.

     For prior lessons:
       - matching lesson_id receives audit_history entry
       - reruns upsert by auditor_ticker + auditor_quarter_label
       - so the intent is append-only over time, but reruns replace the same audit slot

     For new lessons:
       - ticker predictor_lessons go to ticker/{TICKER}.json
       - global_observations go to global.json
       - lesson_id is computed from body + scope + routing
       - child replacement lessons get parent_id when action is refine

     Status is not permanently stored as truth.
     Status is recomputed at render time from PIT-visible audit_history.


                                                |
                                                v


  10) FUTURE QUARTER N+1
      The next prediction re-enters the same loop.

      Future predictor sees only:
        - source lessons allowed by predictor PIT cutoff
        - audit history allowed by predictor PIT cutoff
        - lessons whose recomputed status is not retired
        - lessons that survive scope routing and caps

      This makes replay possible:
        same historical PIT cutoff should reconstruct the same lesson view,
        excluding future audits and future lessons.


====================================================================================================================
CURRENT BIG WEAK SPOTS
====================================================================================================================

  - The predictor can be lazy:
      all irrelevant + repeated "no relevant evidence" + no lesson citations can pass structural validation.

  - Ranking is too recency-heavy:
      active lessons are not tiered by proven usefulness before caps are applied.

  - Audit comments are unstructured:
      hard to distinguish root causes like bad lesson, bad predictor use, missing evidence, or regime mismatch.

  - Sector promotion can be too broad:
      global sector lessons can be created from one ticker without enough transfer proof.

  - Provenance can be incomplete:
      Q4 FCX lessons exist in the libraries, but Q4 prediction/learning dirs are missing on disk.


====================================================================================================================
PROPOSED HARDENING FROM STEPS 14-16
====================================================================================================================

  Add trust tiers before caps:
    proven -> promising -> unproven -> stale-neutral -> risky -> retired

  Make lazy irrelevance harder:
    irrelevant must cite the missing applies_when condition or triggered invalid_if condition,
    not just say "no relevant evidence".

  Add root-cause audit prefixes:
    BAD_LESSON / BAD_USE / MISSING_DATA / REGIME_MISMATCH / OUTCOME_NOISE

  Add provenance caps / tags:
    lessons whose source learner artifact is missing should be visibly marked or capped.

  Tighten global promotion:
    sector / macro / cross_ticker lessons require real transfer evidence,
    otherwise default to ticker scope.

  Keep the architecture small:
    strengthen the existing Build -> Predict -> Learn -> Mutate -> Render loop,
    keep modular Python + JSON stores,
    avoid adding new infrastructure.
```


# Future Experiment: Replay Tournament for Prompt and Knob Tuning

This is a separate evaluation idea to try after the learner-loop architecture is production-grade. It should not mutate the real lesson library while variants are being compared.

Core principle:

Run every prompt/knob variant from the same frozen snapshot of:
- context bundles
- prediction artifacts
- learning artifacts
- lesson libraries
- actual return labels

Snapshot mechanism:

Create an immutable replay directory for each experiment, such as `/tmp/eventmarketdb_replay_<timestamp>/`, by copying only the required bundles, artifacts, lesson libraries, and labels from the repo. Run variants against that copy or against read-only paths. Do not point tournament variants at production `earnings-analysis/` for writes.

Then compare outputs without allowing any variant to write back to production memory. Promote only the winning design after evaluation.

Why this matters:

1. Define the loss function first.
   - Direction accuracy, magnitude error, confidence calibration, citation quality, lesson engagement, and no-call discipline can trade off against each other.
   - Pick the primary metric and secondary guardrails before tuning, otherwise the optimization target becomes implicit and unstable.
   - For confidence calibration, use a named metric such as Brier score, expected calibration error, and reliability-bin plots so variants are scored consistently.

2. Account for LLM stochasticity.
   - Same prompt plus same snapshot can still produce different outputs.
   - Run each variant multiple times or compare distributions, otherwise one lucky run can look like an improvement.

3. Tune few knobs at a time.
   - Prompt wording, lesson caps, status thresholds, ranking weights, confidence buckets, char floors, sentinel rules, and scope rules cannot all be tuned jointly on a small sample.
   - Start with sensitivity analysis, then tune one variable at a time or only the top 2-3 variables that clearly matter.

4. Use temporal holdout, not random holdout.
   - Tune on earlier quarters and validate on later quarters.
   - Random splits can create look-ahead bias because lessons learned from later quarters can leak into earlier-quarter evaluation.

5. Compare against baselines.
   - Accuracy is meaningless without a baseline.
   - Compare against random direction, always-long, no-skill current prompt, no-lesson predictor, and any simple consensus-direction proxy available.

6. Use enough events.
   - Five companies is useful for smoke testing, but too noisy for real tuning.
   - Aim for at least 30 events before trusting directional improvements, and more if tuning multiple knobs.

7. Keep train and holdout separate.
   - Use a tuning set to select prompt/knob changes.
   - Use a later untouched holdout set once to estimate whether the selected design generalizes.

8. Measure more than prediction accuracy.
   - Track lesson citation rate, confirmed/contradicted/irrelevant distribution, sentinel rate, key-driver lesson usage, no-call rate, confidence calibration, learner audit usefulness, provenance gaps, and replay drift.

9. Prevent contamination.
   - Do not let a variant's learner output mutate the shared library before other variants run.
   - If testing learning over multiple quarters, each variant gets its own isolated copy of the library state.

10. Promote cautiously.
    - A winning variant should improve the primary metric without violating guardrails.
    - If a variant improves accuracy but worsens laziness, provenance, replayability, or calibration, reject or refine it.
    - Predeclare guardrail thresholds before running the tournament. Any guardrail regression beyond the threshold disqualifies the variant regardless of primary-metric improvement.

11. Require a real improvement margin.
    - Do not pick a winner from tiny deltas that fit inside noise.
    - Require an explicit confidence interval, standard-error check, or predeclared minimum effect size before promoting a variant.

12. Guard against survivorship bias.
    - A sample of companies with clean full histories can overrepresent survivors and underrepresent messy market reality.
    - Either acknowledge that bias explicitly or include edge cases such as restatements, mergers, distressed names, missing data, or delisted/bankrupt outcomes where available.

13. Isolate predictor vs learner tuning.
    - When tuning predictor prompts or predictor-facing knobs, freeze the learner prompt and prior learner artifacts.
    - When tuning learner prompts or audit behavior, freeze the predictor prompt and prediction artifacts.
    - Do not tune both halves at once unless the experiment is explicitly testing the coupled system, because otherwise attribution becomes muddy.
