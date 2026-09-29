# Jev findings (TypeSafe System One), 2026-09-29 (updated after round 3)

**Status: exploratory only. Nothing adopted.** The owner approved Jev tests on the fact-type task only. No repo, Neo4j or production change was made except this file. Any new Jev task needs fresh owner approval (§6).

## 1. Bottom line
- **Jev judges meaning well when the prompt states your rules explicitly.** Fact type (metric / guidance / surprise / action_event). Round 1: **257 of 258 (99.6%)** on facts the rules decide, 28 facts set aside as undecided. After two outside reviewers ruled on the undecided facts (proposed, **not owner-approved**), the recommended candidate **V6 gets 399–400 of 410 (97.3–97.6%)**; round 1's prompt gets 386 of 410 (94.1%) on the same items (§3.11).
- **Confidence works as a "review this" flag, never as a gate to write or merge** (rules 8.5, 8.6). V6: confidence < 0.9 flags 19% of facts and catches all 11 errors; < 0.75 flags 12% and catches 9 of 11.
- **Other tasks tested since (§3.12, §3.13):** surprise comparison kind 64/65, surprise state 39/41; metric state 92% raw (98% after ruling on the misses), unit 97–98%, span vs moment 94% raw. Errors concentrate in number and sign comparisons (leave to code) and growth-table headers. Keys are earlier-model labels or my own pre-run labels.
- **Baseline, horizon and slice kind (§3.14):** baseline 98% raw (99% after ruling), slice kind 81% raw with every decided item right, horizon right on explicit wording, and 47/49 once "over time" is ruled undefined (§3.15); the slice misses are the filer's own name (probably no slice at all) and airline groupings. Older `GuidanceUpdate` labels are not usable as keys.
- **The prompt was the problem, not the model.** First prompt: 81% raw match to earlier-model labels; rewritten: 99.6%.
- **Jev is only a judge.** It can't write names or quotes, read a whole filing, or do reliable math, dates or counting. It is **not perfectly repeatable**: identical prompt and input changed the answer on 2 of 288 items (low confidence). Cache decisions (rules 2.46, 5.4).
- **The added clauses mostly fix the classes the reviewers ruled on;** on fresh metric facts V6 gets 39/39 and round 1's prompt 37/39. Swings of ±1–3 items are inside Jev's run-to-run noise, so small differences between versions are not proof.
- **Owner has not decided** code-heavy vs Jev-heavy vs mixed (§4). Recommended: mixed.

## 2. Basics a new bot needs
- **API:** `POST https://api.typesafe.ai/v1/systemone`, `Authorization: Bearer $TYPESAFE_API_KEY`. Key is in `.env` line 29 only (not in the shell env). Model `jev-1.13.0` (`jev-latest` points to it today; pin the version). Docs index: `https://docs.typesafe.ai/llms.txt` (add `.md` to a page path).
- **Price and limits:** $0.042 per million input tokens, output free. 1,200 requests/min, 250k tokens/s (docs say limits change without notice). 64k tokens per request, 32k for state + longest question. Text only.
- **Types:** Noul = probability of yes (no confidence field). Choice = one of N options + probabilities + confidence. Score = ordered levels. Questions in one request run in parallel and can't see each other. Don't reuse a threshold across Noul and Choice.
- **Jev's documented weak spots (jev-1.13 "jaggedness" page):** reads literally; weak on math, dates, counting; indirection; large irrelevant state; instructions and criteria that disagree; can't generate text.
- **Measured cost:** ~280 input tokens minimum per call, +~21 per extra short question. The one-question prompt is ~1,050 tokens per fact with round 1's wording, ~1,460 with V6 (~$0.00006). 2,500 calls took 60 s with 8 threads.

## 3. The fact-type test

**3.1 Method (reuse this).**
1. Answer keys: earlier-model runs `experiments/runs/kf-*/*.raw.json` (1,470 typed facts, 628 unique quotes, only 3 filings of 2 airlines). Silver labels, not truth.
2. Source text: `experiments/fixtures/events/<accession>.json` (`text_parts`).
3. Run Jev, **read every miss with its source context against rule 1.5**, and rule it: Jev wrong / label wrong / undecided. Report undecided separately.
4. Fix the prompt from the failures, then retest on **sets the tuning never saw**.

Sets: DEV 115 (design), H1 40 (guidance quotes from 24 other companies from Neo4j `GuidanceUpdate`, labeled by Claude **blind**), H2 60, H3 31, H4 40 (fresh earlier-model facts), **H5 75** (35 more pool facts labeled by Claude before any Jev call + 40 unused metric facts; no unused action facts remain).

**3.2 What was wrong with the first prompt.**
- It left out the rule that a forecast framing overrides the persistence test.
- It put a yes/no test ("Yes means metric") inside a 4-option Choice (instructions vs criteria disagree).
- The 5-question variant had an indirect "ignoring forecast wording…" question, mixed Choice with Noul, and its forecast question grabbed announced future decisions.
- Input defects: collapsed whitespace (destroying paragraphs, headings, tables), windows starting mid-sentence, no text after the quote, page-header junk.

**3.3 Which fix mattered** (round 1, DEV, 104 decidable facts; one Choice / five stepped Noul):

| Prompt | Input | One Choice | Steps |
|---|---|---|---|
| old | old | 93 | 90 |
| old | clean | 92 | 94 |
| **new** | old | **103** | 98 |
| **new** | clean | **103** | 99 |

The prompt was the lever. Keep the clean input anyway. The five-question stepped pattern is worse; don't use it.

**3.4 Round 1 result:** DEV 103/104 · H1 35/35 · H2 52/52 · H3 31/31 (tuned) · H4 36/36 · all 257/258. Confidence < 0.8 flagged 13% of facts, including 19 of the 28 undecided ones. Rule 8.17 needs ~300 graded facts with none wrong; 71/71 on untouched sets supports only "under ~4% wrong". Ruled by Claude, mostly two airlines, no surprise examples in that round (surprise: §3.12).

**3.5 The 28 undecided facts → outside rulings (proposed interpretations).** Instructions that came with them: identify the precise claim first; split mixed claims; apply existing rules before calling something a new question; keep forecast assumptions distinct from observed values; bring back only what stays undecided.

| # | Facts | Ruling |
|---|---|---|
| 1 | Cash-flow amounts ("net purchases of short-term investments", repayments) | metric (a period total made of transactions is still a total) |
| 2 | Winter-storm revenue impact | action_event (an incident; a continuing condition or measured severity would be metric) |
| 3 | Forecast assumptions ($4.00/gal, expected recovery, expected expense increase) | guidance, kept as an assumption not an observed price |
| 4 | PFAS transition; scheduled profit-sharing payment; "do not plan to use exchange agreements" | action_event; action_event; guidance (expected volume) |
| 5 | Dividend per share | metric, **only under a per-share driver**; a declaration under `dividend` is an action (rules 1.7, 2.31) |
| 6 | One quote with two claims | split first (a balance and its expected use; past openings and future targets) |
| 7 | Standing arrangements / accounting method already in use | metric (not their creation) |
| 8 | Pay levels, reserve-adjustment amounts, revenue performance | metric; "nine record weeks" must not become a revenue amount of nine |

Main clarification (**needs owner approval; conflicts with the broad wording of rule 1.6**): a forecast of a measurement or condition is guidance; an announced action stays an action even when it happens later; the words "plan", "will", "recorded" don't decide the type alone.

**3.6 Redo (round 2): method and results.** (Latest round: §3.11. V2b below is superseded by V6.)
- **Keys:** the 28 + the one clear round-1 error = 29 items; the 2 mixed quotes were split into exact sub-spans (4 claims) → 31 claims. All 288 round-1 items plus H5 were re-run.
- **Prompts:** V0 = round 1 · V1 = V0 + asks about the named driver · V2a = V1 + clarifications that touch no rule wording · **V2b = V2a + the rule-1.6 clarification (superseded by V6, §3.7)** · V3 = V2b + 2 more clauses (rejected).
- **Redo claims (31) / other 257 items:** V0 16 / 256 · V1 19 / 256 · V2a 24 / 255 · **V2b 24 / 255**.
- **By group under V2b:** cash-flow totals 6/6, storms 3/3, forecast assumptions 4/5, actions 2/2, expected volume 1/1, standing arrangements 1/4, mixed 3/4, pay/reserve/records 2/3, dividend 1/2. Of the 7 misses, 5 are undecided (below), 2 are real errors.
- **All 350 decided items** (9 undecided + 4 unclear set aside): V0 338 (96.6%) · V2b 344 (98.3%). Fresh H5 alone (67): V0 66, V2b 65.
- **Real errors under V2b (6):** a "despite a $4B expense increase" clause inside a forecast sentence; the projected non-GAAP tax-rate sentence (also undecided, §3.10 #2); a contract-minimums schedule called forecast; two explanations of a cost line's change called action; a financing-repayments total called action. Confidences 0.38 to 0.71.
- **Remove-one-clause test (350 items):** every clause helps more than it hurts (dropping "a total made of transactions" breaks 8; "incident even when its effect is stated" breaks 3; the rule-1.6 rewrite breaks 6 and fixes 2; the driver-name sentence breaks 6 and fixes 3). Swings of ±1–3 items are inside Jev's run-to-run noise.
- **Didn't work:** (a) a mixed-claim detector: broad version flags 107 of 288; the narrow one ("already true and also about the future") catches both known cases but flags 47 of 286 (16%), mostly announcements with a future date → **the reader must split claims, not Jev**. (b) V3's extra clauses swapped one error for another.

**3.7 Recommended prompt V6 (verbatim; not owner-approved).** One Choice `fact_type`, sent with the state in §3.8. Every clause beyond rule 1.5's locked wording needs owner approval (rule 1.9); §9 lists exactly what each version added and why, so any older version can be rebuilt.
```json
{
 "type": "choice",
 "instructions": {
  "question": "Which kind of fact does `quote` state about the driver `driver_name`?",
  "read": "Judge the specific claim `quote` makes about the driver, not merely its verb, its number or its date. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. The driver name shows which claim is meant, but the quote and its context must support the answer: the name alone never decides it. When two drivers cover one topic, one named for a per-unit amount and one for the decision or event, a quote that states the amount is a metric for the first, and a quote that states the decision is an action_event for the second.",
  "order": "A statement that compares with an outside expectation is a surprise. Otherwise the company's own forecast of a measured quantity or condition is guidance, even when it contains a number, a rate or a table row. Otherwise it is a metric if it describes a standing variable, or an action_event if it describes a single thing that happened."
 },
 "criteria": {
  "surprise": {
   "what": "A company value, delivered (an actual) or promised (a company forecast), compared with an expectation held by another party (analyst consensus or the Street), or an actual compared with the company's own earlier forecast.",
   "not_for": "A comparison with the prior period's actual, or a new forecast compared with the company's own earlier forecast."
  },
  "guidance": {
   "what": "The company's own forecast, expectation or stated assumption about how a measured quantity or condition will be in a future period, including a forecast range or estimate. The words expect, anticipate, target, plan and will do not decide the type by themselves: what matters is whether the statement forecasts a measurement or condition. A table row counts when its table or section is an outlook, guidance, forecast or estimate.",
   "not_for": "Something that already happened or is true now, a forecast made by someone other than the company, or an announced, committed or scheduled action (that is an action_event)."
  },
  "metric": {
   "what": "A standing variable that can be read again over time: a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand. A figure that a company reports for each period (revenue, an expense, income, a cash flow, a balance) is such a variable, even when the sentence describes it with a verb like recorded, increased or decreased. A total, count or amount measured for a period is such a variable even when it is made up of transactions. A method, policy or arrangement that is already in use and continues is a condition in force, not the moment it was created. A standing per-unit level is a metric. A change in a level, such as a pay increase, is a metric even when it takes effect on a stated date. A rate or assumption the company uses in its own current method or calculation is a condition in force; the word projected alone does not make it a forecast. When one sentence states both a standing per-unit amount and the decision that set it, the amount is a metric and the decision is a separate action_event.",
   "not_for": "A forecast (that is guidance) or a single thing that happened (that is an action_event)."
  },
  "action_event": {
   "what": "A discrete thing that happened: a decision, transaction, incident, approval or one-off charge. An incident counts even when the quote also states its effect on a result. A one-time decision to start, change or suspend a policy is an action_event. An announced, committed or scheduled action stays an action_event even when it happens later. A negotiation or implementation that is still underway is an action_event that continues. A milestone, such as a delivery or entry into service, is an action_event; a count of what exists now is a metric.",
   "not_for": "A standing variable or condition, or a forecast. A figure reported for each period is not an action_event just because the sentence uses a verb like recorded or increased. A continuing condition or a measured severity is a metric."
  }
 }
}
```

**3.8 Input format ("state").** Named fields: `where_it_appears`, `driver_name`, `text_before_quote`, `quote`, `text_after_quote`.
- `where_it_appears`: plain words with correct articles, e.g. "Management's Discussion and Analysis of a quarterly report (10-Q)" (round 1 had "of an quarterly" and raw names like "RiskFactors"; fixed).
- `driver_name`: underscores to spaces; **strip `_guidance` / `_surprise`** (it leaks the type). The question now asks about this driver, and some rulings depend on it (dividend).
- Before: ~520 characters starting at a sentence or paragraph start (never mid-sentence), keeping up to 3 heading lines above. If the quote is in a table, include the table start (title, column headers) and end. Remove page-header boxes ("Company | 2025 Form 10-K"). Rewrite `##TABLE_START/END` to `[Table]` / `[End of table]`.
- After: ~260 characters ending at a sentence end; drop trailing heading-only lines and unfinished tables (may be empty).
- Quote: exact; find it with a whitespace-insensitive match. **Never collapse whitespace.**
- 10-K / 10-Q sections keep paragraphs and `##TABLE` markers. **8-K exhibit text in the database is flat (no line breaks); table rows run together.** That's the source, not something to fix here.

**3.9 Traps.**
- `GuidanceUpdate` in Neo4j is **not** a guidance answer key: it labels dividend declarations as guidance, `source_key` is a section name, quotes start with "[8-K]" / "[PR]".
- **Never let a label field share a name with the input field** (§3.13): a builder overwrote the input with the answer and the first fact-card run scored a fake 100%. Assert the input before every run.
- The same sentence appears in several cuts, so misses overcount (one forecast table ×6, winter storms ×3, "$4.00 per gallon" ×3).
- Two earlier-model labels were wrong under the advised rulings (scheduled profit-sharing payment labeled metric).
- Older WIP notes say "Jev is DEFERRED". That was for finding why a name loses a cause (a producing task), not for judging.

**3.10 What is still open (after round 3).** The six round-2 questions were ruled by a second outside reviewer (§3.11); Jev agrees on most, not all:
1. **Counts of things opened during a period** ("opened 9 new stores and closed one"): reviewer says metric; Jev says action_event at 0.88.
2. **An agreement stated with "have agreed to make available"** (CRAF): reviewer says metric (in force); Jev says action_event (0.74).
3. **Pay increases with effective dates:** reviewer says metric; Jev flips between the two at ~0.5.
4. **A dividend declaration as a whole sentence** under a per-share driver: reviewer wants the amount and the decision split into two claims; as split claims Jev agrees 8 of 8.
5. **No key from either reviewer:** "expect to complete the U.S. implementation by the end of 2027" (guidance or action?), "we became subject to the EU ETS on January 1, 2024" (event or standing condition?), "We paid $1.4 billion in 2025 to our employees" (a payment made, or a period total?).
6. **Mixed quotes:** the shared core's reader separates the claims (rule 2.34, per the reviewer); a rule saying so should be written. Jev can't detect mixed quotes (§3.6).

**3.11 Round 3: second reviewer's rulings on the six open questions (proposed, not owner-approved).** Principle from the reviewer: classify the specific claim, not merely its verb, number or date; a proposed name alone must never force the answer (the quote and context must support it).

| Question | Ruling |
|---|---|
| Pay raises | metric (the pay change, "increased"); the effective date doesn't change it; a separate claim about approving the raise is an action |
| Projected 20% tax rate | metric: a rate used in the company's current non-GAAP method; "projected" alone doesn't make it guidance |
| Ongoing agreements | agreement in force → metric (`persists`); a negotiation or implementation underway → action (`continued`); CRAF = the first |
| Dividend declaration under a per-share driver | metric for the amount; the declaration is a separate action; don't type the whole sentence as an action under the per-share driver |
| "1,000th aircraft" | "received our 1,000th aircraft" = delivery milestone → action; "our fleet contains 1,000" = count → metric |
| Mixed quotes | the core's reader separates the claims; "opened 9 stores" = metric count, "expect to open 45" = guidance |

**Method.** Keys applied to 17 items (H2-043, LATAM joint venture, marked action by me because the reviewer didn't name it); 2 mixed quotes split into 4 claims; 2 claims left with no key. Ran prompts V0, V2a, V2b, V4, V5, V6 (two runs of V4/V5/V6) on 365 earlier items, plus 8 split dividend claims (amount under `dividend per share`, decision under `dividend`) and 40 fresh metric facts (H6). Also ran V2b with the driver name hidden. About 5,000 calls, ~$0.26.

**Results (decided items):**

| Prompt | All 410 | Newly ruled 17 | Split dividend claims 8 | Fresh H6 39 |
|---|---|---|---|---|
| V0 (round 1) | 386 (94.1%) | 10 | 4 | 37 |
| V2a | 394 (96.1%) | 11 | 7 | 38 |
| V2b | 392 (95.6%) | 9 | 6 | 36 |
| V4 | 395 (96.3%) | 11 | 4 | 38 |
| V5 | 391–394 (95.4–96.1%) | 11 | 4 | 39 |
| **V6** | **399–400 (97.3–97.6%)** | 13–14 | **8** | 39 |

**Findings.**
- **Driver name, hidden:** hiding it changes 18 of 365 answers (5%) and lowers accuracy from 96.4% to 94.2%. Changes happen mostly at confidence < 0.5; for dividend quotes the name moves Jev from action (1.00) to metric (~0.4). The name tips close calls but rarely forces a confident answer.
- **Split dividend test:** the decision claim is action_event at 1.00 in every prompt. The amount claim is metric **only when the prompt restates rule 1.7** (V6 8/8, V2a 7/8, V2b 6/8; V4 and V5 4/8). V4 removed that sentence to follow "the name never forces" and lost it; V6 restores it as "a quote that states the amount is a metric for the first driver, a quote that states the decision is an action_event for the second", which keeps the quote as the deciding evidence.
- **A mistake I had made:** V2b and V4 dropped "the company's own" from the guidance definition, so an EU legal schedule and a contract-minimums schedule were called guidance. V5 restores it (locked wording); V6 keeps it.
- **V6 errors (11):** the storm sentence ×3 (DEV-042/052/061, confidence 0.38–0.41; regressed from V5), H2-045, H4-007, H5M-018 (fragments about notes or a cost line's change, ≤ 0.49), DEV-085 (0.84), H1-013a (0.88), H1-035 (0.38), H2-039 (0.74), H2-048 (0.49). Confidence < 0.9 catches 11/11 at 19% of facts.
- **Run-to-run noise:** identical V6 runs differ on 3 of 413 items (all low confidence). Cash-flow totals (4–5 items) sit near 0.4 and flip between V4, V5 and V6.
- **Fresh metric set H6:** V6 39/39, V0 37/39. One quote set aside ("We paid $1.4 billion", §3.10 #5).

**Caveats.** I tuned V4–V6 on these items; H6 is fresh but has only metric facts (no unused action or guidance facts remain); keys come from two outside reviewers and me; V6's lead over V4/V5 is a few items out of 410, mainly the 4 split dividend claims, so treat it as a candidate, not a proof.

**3.12 Surprise test (2026-09-29).** Surprise had 0 of 413 test items before this, so its prompt option was untested.

**Data and labels.**
- 75 items sampled at random (seed 2026) from Neo4j, read-only: Benzinga news headlines with beat/miss/estimate wording (16,941 match), transcript prepared remarks about guidance (2,487) or consensus (289), 8-K exhibits mentioning consensus (255). News and transcripts are off in release 1 (rule 9.5), so this tests the language, not the release-1 source. Quotes are exact substrings (rule 8.8). Headlines were split into one comparison per claim (rules 4.1, 4.16).
- **Labels were frozen before any Jev call** (hash `b43d406630dce0a8`): **42 surprise claims** (20 actual_vs_consensus, 12 actual_vs_guidance, 10 guidance_vs_consensus; states beat 17, in_line 12, missed 11, unknown 1, unclear 1; 26 news, 16 transcript), **23 look-alike controls** (9 guidance movements or forecasts with no comparison, 7 comparisons with last year, 1 action, 6 where "consensus" means something else) and **10 unscored** (mixed headlines and "our expectations").
- Rules applied to the labels: 1.5 (a surprise compares a company value with an outside expectation, or an actual with the company's own earlier guide; **not** with a prior-period actual, **not** a new guide vs its own earlier guide), 4.1 table, 4.2, 4.3 (kind = basis + baseline, not whether the period ended), 4.10 (in_line: inside a closed range or on its edge with no good/bad words; a range containing the consensus is in line), 4.11–4.13 (beat/missed by meaning; "above/below" don't mean good/bad alone; expenses need the source's framing, else unknown), 3.52 (company target wording = previous_guidance).

**Run.** ~340 calls, $0.016: S1 fact type (V0 and V6), S2 which comparison, S3 beat / in_line / missed / unknown. S2 and S3 were written from the rules (verbatim below).

| Task | Result |
|---|---|
| **S2 comparison kind** | **64/65.** All 42 surprise claims right (20/20, 12/12, 10/10); controls answered "none" 22/23 (the miss was at 0.39) |
| **S3 state** | **39/41.** beat 17/17, missed 11/11, in_line 11/12, unknown 0/1; both misses at confidence < 0.5 (an estimate on the edge of a guided range; an expense "slightly below our guided range" that rule 4.12 wants as unknown) |
| **S1 fact type**, answered "surprise" | V0 39/42, V6 36–37/42; **every other answer was the home metric or guidance type** that rules 4.1 and 4.14 require alongside a surprise, so 42/42 are acceptable |
| **S1 controls** called surprise | 1/23 for both prompts ("a 3.5 penny increase over the midpoint of our August guidance", confidence 0.34–0.36); V6 also called "Raises Guidance" an action (0.59) |

**Findings.**
1. **One quote backs two facts.** "EPS $1.83 Beats $1.76 Estimate" supports a surprise and its metric home fact (4.14). With `_surprise` / `_guidance` stripped from the name (as in §3.8), the type Choice can't know which is meant, so answering the home type is not an error. **Use S2 (comparison with a "none" option) to detect surprises, not the type Choice.**
2. **V6 has no advantage here:** it answers "surprise" less often than V0 because it asks about the driver.
3. **Most items were easy:** 29 of 42 quotes contain explicit words (beat, miss, in line, above, exceeded) and 26 are templated news headlines. Harder cases: an estimate inside or on the edge of a range (numeric containment; code should do it) and expense direction (4.12).
4. **Mixed statements:** headlines that state a guidance change and a consensus comparison together (rule 4.16) get one label (mostly guidance, confidence 0.38–0.80). The reader must emit separate facts.
5. **"Exceeded our expectations"** (the company's own): Jev calls it a surprise with baseline consensus at 0.93–0.98 confidence on 3 of 4. That matches rule 3.52's wording ("'Exceeded expectations' on a surprise → consensus"), but no rule says whether the company's **own** expectations count. Open gap.
6. **Macro view vs consensus** ("our view is for above consensus global growth"): Jev says surprise (0.69); it is not a company value. Open gap.

**Caveats.** Labels are mine (frozen first); 42 claims, 26 from templated headlines; single run, nothing tuned this round; news is off in release 1.

**S2 prompt (verbatim, from rules 4.1–4.3):**
```json
{"comparison": {"type": "choice", "instructions": {"question": "Which comparison does `quote` make about the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. Decide whether the value is a reported result or a forecast from what the quote says, not from whether the period has ended."}, "criteria": {"actual_vs_consensus": {"what": "A result the company has reported, compared with what analysts, the Street or the market expected (the consensus or estimate).", "not_for": "A comparison with last year or last quarter, or with the company's own forecast."}, "actual_vs_guidance": {"what": "A result the company has reported, compared with the company's own earlier forecast, guidance, outlook or target range.", "not_for": "A comparison with analysts' expectations, or with last year or last quarter."}, "guidance_vs_consensus": {"what": "A forecast or outlook the company gives for a future period, compared with what analysts, the Street or the market expected.", "not_for": "A new forecast compared with the company's own earlier forecast."}, "none": {"what": "No company value is compared with an outside expectation or with the company's own earlier forecast. This includes a comparison with last year or last quarter, a new forecast compared with the company's own earlier forecast, a forecast or result with no comparison, and a statement that only mentions consensus or expectations.", "not_for": "Any of the three comparisons above."}}}}
```
**S3 prompt (verbatim, from rules 4.10–4.13):**
```json
{"state": {"type": "choice", "instructions": {"question": "Is the company's value in `quote` a beat, in line, or a miss against the expectation it is compared with, for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. Judge the whole phrase, including negation, direction and scope. The words above, below, exceeded and ahead of do not mean good or bad on their own, and a higher number is not always better."}, "criteria": {"beat": {"what": "The value is better than the expectation, judged by meaning: the source says beat, better than expected, or gives other words that frame the result as good.", "not_for": "A value that is only higher or lower with no sign that it is good."}, "in_line": {"what": "The value equals the expectation, sits inside a stated expectation range or on its edge, or the source says in line, and no words say good or bad.", "not_for": "A value clearly outside the range that the source frames as good or bad."}, "missed": {"what": "The value is worse than the expectation, judged by meaning: the source says miss, worse than expected, or gives other words that frame the result as bad.", "not_for": "A value that is only higher or lower with no sign that it is bad."}, "unknown": {"what": "The value is outside the expectation but the source gives no words saying good or bad, and a higher number is not clearly better for this driver (for example costs, capital spending, research spending, inventory, hiring or cash burn), or the comparison is unclear.", "not_for": "A comparison the source states as a beat, a miss or in line."}}}}
```

**3.13 Fact-card tests: metric state, unit, span vs single moment (2026-09-29).** A second task family, tested with ready-made keys.

**Data.** Answer keys = the earlier model's labels in `experiments/runs/kf-*` (960 unique facts; the labels agree across runs on 97–100% of them). Silver labels, not truth; mostly two airlines. Prompts written from rules 3.5 + 3.6 (state), 3.28–3.33 (unit), 3.47 (span vs moment). One prompt version each, nothing tuned. Two runs each, 4,932 calls, ~$0.21.

**Bug found and fixed (a trap):** my first run scored 100% on state and "unknown" on every unit. A label field named `state` had overwritten the input field `state`, so Jev was sent the answer. **Always assert the input is still the input** (now in the builder and the runner).

| Task | Facts | Raw match | After ruling on every miss (unclear set aside) | Strict (unclear = wrong) | Two identical runs differ |
|---|---|---|---|---|---|
| Metric state | 718 | 660 (91.9%) | **667/681 (97.9%)** | 92.9% | 2 |
| Unit of the value | 643 | 626 (97.4%) | **627/639 (98.1%)** | 97.5% | 1 |
| Unit of the change | 239 | 233 (97.5%) | **233/239 (97.5%)** | 97.5% | 4 |
| Span vs single moment | 866 | 815 (94.1%) | **827/827 (100%)** | 95.5% | 3 |

I read all 132 misses. Rulings (mine, against the rules): state = 14 Jev wrong, 7 label wrong, 37 unclear; value unit = 12 Jev wrong, 1 label wrong, 4 unclear; change unit = 6 Jev wrong; span = 0 clear Jev errors, 12 label wrong, 39 unclear.

**Findings.**
1. **State: the real Jev errors are number comparisons and fragments.** Negative numbers and losses ("Pre-tax margin (3.4)% (5.2)%" called decreased at 0.94; a loss that narrowed called decreased although the prompt says it counts as an increase; operating income $157 vs $38 called decreased), and fragments whose direction word is in the text before the quote ("4% effective June 1, 2025"). **Direction from two numbers should be computed by code** (rule 3.51 already checks the sign).
2. **State: 7 labels contradict rule 3.6.** Schedules that say "decreasing on an annual basis" were labeled `reported`, but the first row of 3.6 says a stated direction wins; Jev followed the rule.
3. **Sign convention is a rule gap.** "Net cash used in investing activities was $2.3B and $1.2B" and expense rows in parentheses like "Interest expense, net (400) (452)" flip between the earlier labels and Jev depending on whether the magnitude or the signed value is compared. Rule 3.34 says store the signed value, but the earlier labels are inconsistent with each other. 18 of the 37 unclear state items are this.
4. **Unit errors cluster on growth tables.** When the basis sits in a header ("Q2 2026E (vs. Q2 2025)", a change column like "10.7%"), Jev says plain `percent`; rule 3.33 says growth is never plain percent (year over year unless stated). A coupon in a note's name ("4.95% Notes due 2028") pulled a $1.0B money total to `percent` at 0.83. All 6 change-unit misses had confidence < 0.40.
5. **Span vs moment:** 95.9% on facts that carry a number, 84.1% on facts with no number (mostly actions). Rules don't define time_type for an action ("repaid in full $629 million", "proceeds received"). 12 labels were wrong ("scheduled maturities in 2026 are $1.4B", "we paid $1.4B in 2025", "prices ranging from $1.86 to $4.75 during the quarter" are durations).
6. **Confidence flags most misses:** state < 0.9 flags 19% of facts and catches 42 of 58; value unit < 0.9 flags 15%, catches 16 of 17; change unit < 0.6 flags 10%, catches 6 of 6; span < 0.9 flags 18%, catches 39 of 51.

**Open rule questions:** (a) the sign convention for measures written as "used" and for expense rows in parentheses; (b) time_type for action events without a value; (c) `persists` vs `reported` when an ongoing covenant or policy also states a value.

**Prompts (verbatim).** State (rule 3.6):
```json
{"state": {"type": "choice", "instructions": {"question": "Which state does `quote` give for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. Apply these in order and take the first that fits: a stated direction is increased or decreased; the same driver moving differently across parts is mixed; stated flat is unchanged; ongoing with no direction is persists; a bare value is reported, but a value that also states the prior value is increased or decreased; otherwise unknown. Good or bad news never decides the state."}, "criteria": {"increased": {"what": "The quote states an increase, or gives a value together with a lower prior value. A loss that narrows counts as an increase.", "not_for": "A bare value with no direction and no prior value."}, "decreased": {"what": "The quote states a decrease, or gives a value together with a higher prior value. A loss that widens counts as a decrease.", "not_for": "A bare value with no direction and no prior value."}, "mixed": {"what": "The same driver moves in different directions in different parts of the quote.", "not_for": "A single direction."}, "unchanged": {"what": "The quote states that the driver is flat or unchanged.", "not_for": "A small increase or decrease."}, "persists": {"what": "The quote says the driver is ongoing or continues, with no direction and no value.", "not_for": "A bare value, or a stated direction."}, "reported": {"what": "The quote gives a bare value with no stated direction and no prior value.", "not_for": "A value stated together with its prior value, or with a direction."}, "unknown": {"what": "None of the other states fits.", "not_for": "Anything the other states describe."}}}}
```
Unit of the value (rules 3.28–3.33); the change version differs only in its question, "What is the unit of the stated change (the increase, decrease or difference) in `quote` for the driver `driver_name`?":
```json
{"unit": {"type": "choice", "instructions": {"question": "What is the unit of the stated value in `quote` for the driver `driver_name`, ignoring any change or comparison amount?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title."}, "criteria": {"usd": {"what": "Money per unit: a price, a per-share amount or a per-barrel amount, in US dollars.", "not_for": "A money total."}, "m_usd": {"what": "A money total in US dollars (millions or billions of dollars).", "not_for": "Money per unit."}, "percent": {"what": "A percentage that is itself a level, such as a margin, a rate or a share of a total.", "not_for": "Growth against an earlier period, or a difference in percentage points."}, "percent_yoy": {"what": "Growth compared with a year earlier (year over year, comparable or annual growth). Growth is never plain percent.", "not_for": "Growth against the previous quarter, or a difference in points."}, "percent_sequential": {"what": "Growth compared with the immediately previous comparable period, for a period shorter than a year.", "not_for": "Growth against a year earlier."}, "percent_points": {"what": "A difference between two percentages, in percentage points. Points win over year-over-year or sequential wording.", "not_for": "Growth in percent."}, "basis_points": {"what": "A difference or move in basis points. Basis points win over year-over-year or sequential wording.", "not_for": "Growth in percent."}, "count": {"what": "A number of things, such as shares, stores, aircraft, employees or customers.", "not_for": "Money or a percentage."}, "x": {"what": "A multiple, such as 2.5x.", "not_for": "A percentage."}, "unknown": {"what": "The unit cannot be settled from the quote, for example money in a currency other than US dollars, growth over a vague horizon, or up or down X% on a metric that is itself a percentage with no points, basis points or \"to X%\".", "not_for": "A unit the quote states clearly."}}}}
```
Span vs single moment (rule 3.47):
```json
{"time_type": {"type": "choice", "instructions": {"question": "Does the value in `quote` for the driver `driver_name` cover a span of time or a single moment?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. Decide from the meaning of the value, never from a default."}, "criteria": {"duration": {"what": "The value covers a span of time, such as a quarter, a year or a year to date, for example revenue, expenses or cash flow for the period.", "not_for": "A balance or count measured as of a date."}, "instant": {"what": "The value is measured at a single moment, such as a balance, a count or a rate as of a date.", "not_for": "An amount earned or spent over a period."}}}}
```

**3.14 Baseline, horizon and slice-kind tests (2026-09-29).** Prompts written from rules 3.52, 3.40 and 3.13–3.15; one version each, nothing tuned; two runs each, ~2,140 calls, ~$0.08. Labels were frozen before any Jev call (hashes `ca1fa5c4364f6b7a` and `ad311b3a4e8e1105`).

| Task | Keys | Items | Raw | After ruling on the misses (unclear set aside) | Strict | Runs differ |
|---|---|---|---|---|---|---|
| **Comparison baseline** (3.52) | kf-run labels + my mapping of the frozen surprise labels | 581 | 570 (98.1%) | **573/577 (99.3%)** | 98.6% | 3 |
| **Horizon** (3.40), proper test | 49 real sentences, labeled by me from the rule and the wording | 49 | 39 (79.6%) | 39/39 on the 41 not touching "over time" | 79.6% | 0 |
| **Horizon**, first attempt (invalid) | older `GuidanceUpdate` period_scope | 148 | 76 (51%) | not usable | | 1 |
| **Slice kind** (3.13) | kf-run labels | 291 | 236 (81.1%) | **237/237 on the 237 the rules decide** | 81.4% | 6 |

**Baseline.** consensus 30/30, previous_guidance 22/24, sequential_period 9/11, prior_year 437/439, none 72/77. Of 11 misses: 3 labels wrong (a before/after amendment is not a prior period; a quote with no comparison), 4 Jev wrong (a table row without its column heading at 0.79; "$70M in 2025 … $5M in 2026" read as year over year at 0.90; the word "consensus" used in another sense), 4 unclear because one quote backs two facts ("up 17% year over year, exceeding the midpoint of our outlook" is prior_year for the metric and previous_guidance for the surprise).

**Horizon.** The first attempt used labels from the older guidance pipeline; they contradict rule 3.40 ("We continue to be in that range" labeled short_term) and half of the stated-window labels depended on context I did not show, so **it is not a valid test**. The proper test: stated_window 8/8, short_term 10/10, medium_term 8/9, long_term 8/9, **undefined 5/13**. The 8 undefined misses are all "over time" or "eventually" answered long_term at 0.90–1.00. **That is my prompt's fault:** I wrote "over time" into the long_term option, and rule 3.40 doesn't say where "over time" goes (it only says undefined = "going forward"). Rule gap. The other 2 misses: "over the next three to five years" (Jev: stated_window) and a sentence holding two horizons (my label error).

**Slice kind.** geography 73/73, segment 32/32, customer 7/7, product 89/113, entity_ownership 35/65. Of 55 misses: 1 label wrong ("sales to airline segment" is a customer group), **54 unclear**: 30 are the company's own legal entity (`americanairlinesinc`) that Jev calls unknown or segment; rule 3.13 says only joint ventures and part-owned companies are clean entity_ownership and "other entity rows are provisional". The other 24 are airline groupings the rules don't place: mainline and regional carriers (product or segment), cargo, MRO, passenger, corporate (channel or customer). No clear Jev error.

**Findings.**
1. **Baseline is solid**, including the rare kinds (consensus, own guidance), and confidence is not needed: only 7 of 11 misses are flagged at < 0.9.
2. **Horizon depends on your rule**, not on Jev. Explicit words (near term, medium term, long term, going forward, a named year) are read correctly; "over time" and "eventually" need a ruling.
3. **Slice kind needs the rules to decide the company's own entity and airline groupings** before it can be scored fairly. Strict 81%, but the misses are label and rule gaps, not Jev slips.
4. **Two data traps:** the older `GuidanceUpdate` period_scope is not a horizon answer key (it doesn't follow rule 3.40); the kf slice labels call the company's own legal entity entity_ownership, which rule 3.13 treats as provisional.

**Open rule questions:** (a) does "over time" / "eventually" mean long_term or undefined (3.40)? (b) what kind is the company's own legal entity or subsidiary (3.13, 3.15)? (c) are mainline and regional carriers segments or products; is a corporate customer group a customer or a channel?

**Caveats.** Silver labels for baseline and slices; my labels for the horizon test (a wording-based reading, since the rule gives no thresholds) and for the surprise-derived baselines; mostly two airlines; 49 horizon items.

**Prompts (verbatim).** Baseline (rule 3.52):
```json
{"baseline": {"type": "choice", "instructions": {"question": "What headline comparison does `quote` make for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. If the quote makes several comparisons, take the headline one."}, "criteria": {"consensus": {"what": "The value is compared with what analysts, the Street or the market expected.", "not_for": "The company's own forecast."}, "prior_year": {"what": "The value is compared with the same period a year earlier (year over year, versus last year, the year-ago period). If the quote also compares with the previous quarter, the year-ago comparison wins.", "not_for": "A comparison with the previous quarter only."}, "sequential_period": {"what": "The value is compared with the immediately previous comparable period, such as the previous quarter or month, and not with a year earlier.", "not_for": "A comparison with a year earlier."}, "previous_guidance": {"what": "The value is compared with the company's own earlier guidance, forecast, outlook or target.", "not_for": "Analysts' expectations."}, "none": {"what": "The quote makes no comparison, or compares with something else: peers, a fixed anchor year such as 2019, or a streak.", "not_for": "A comparison with a year earlier, the previous period, analysts or the company's own guidance."}}}}
```
Horizon (rule 3.40; note "over time" sits under long_term):
```json
{"horizon": {"type": "choice", "instructions": {"question": "Which time horizon does the forecast or goal in `quote` refer to, for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title."}, "criteria": {"stated_window": {"what": "The quote names a real window: a fiscal year, a quarter, a half, a month, a dated range or a year such as by 2030.", "not_for": "A horizon described only in words such as long term or going forward."}, "short_term": {"what": "The quote looks ahead to the near term or the coming months, in words, with no dates.", "not_for": "A dated window."}, "medium_term": {"what": "The quote looks ahead to the medium term or the next few years, in words, with no dates.", "not_for": "A dated window."}, "long_term": {"what": "The quote looks ahead to the long term, a long-range plan or over time, in words, with no dates.", "not_for": "A dated window."}, "undefined": {"what": "The quote looks ahead to a horizon that is implied but not defined, such as going forward, with no dates.", "not_for": "A dated window, or a horizon named as short, medium or long term."}}}}
```
Slice kind (rules 3.13–3.15; the state also carries a `slice_value` field):
```json
{"slice_kind": {"type": "choice", "instructions": {"question": "What kind of company part is `slice_value` in `quote`, for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. A brand is not a kind; the way the quote uses it decides."}, "criteria": {"segment": {"what": "A part the company operates as: a reporting segment or division.", "not_for": "Something the company sells, or a place."}, "product": {"what": "Something the company sells: a product, a service or a program.", "not_for": "A reporting segment, or a place."}, "geography": {"what": "A place the company operates in: a country, a region or a destination.", "not_for": "A product or a segment."}, "customer": {"what": "A group the company sells to.", "not_for": "A product or a place."}, "channel": {"what": "How the company sells or runs something, for example franchised or through partners.", "not_for": "A product or a customer group."}, "entity_ownership": {"what": "A stake the company owns. Joint ventures and part-owned companies are the strongest cases; other entity rows are provisional.", "not_for": "A product or a segment."}, "unknown": {"what": "The kind cannot be told from the quote.", "not_for": "A kind the quote makes clear."}}}}
```

**3.15 Rescore after my three proposed rulings (2026-09-29).** I proposed rulings for the three gaps in §3.14, changed the two prompts, rebuilt the keys from them (slice-key hash `0e425c40d60ac99c`, frozen before the run) and reran (680 calls). Because the keys follow my rulings, this shows whether Jev **follows a stated rule**, not fresh accuracy.

| Ruling | Prompt change | Result |
|---|---|---|
| 1. "over time" / "eventually" = undefined; long_term only when the source says long term, long-range or longer term | long_term `what` = "The quote itself says long term, long-range or longer term, in words, with no dates."; undefined `what` adds "over time, eventually or in the future" | **Works:** horizon 47/49 (95.9%) vs 39/49 with the old prompt; undefined 13/13. The 2 misses are my mixed-sentence label and "over the next three to five years" (called stated_window). |
| 2. The company's own legal entity = entity_ownership, provisional | entity_ownership `what` adds "Other entity rows, such as the company's own subsidiary reported on its own, are provisional." | **Not reproduced.** Jev never says entity_ownership for `americanairlinesinc` (0/30): unknown 20, segment 9, product 1. For real joint ventures and part-owned companies (Grupo Aeromexico, WestJet, Air France-KLM, Virgin Atlantic, LATAM, Hanjin KAL, Unifi, Endeavor) it is **35/35**. |
| 3. Unclear airline groupings = unknown (3.18); customer group = customer | unknown `what` adds "or the same name could fit several kinds and nothing says which" | **Not reproduced.** For mainline, regional carrier and MRO (14 rows, keyed unknown) Jev says segment on ~10 (mainline 5/5 segment), customer or channel on the rest. Cargo, passenger, loyalty program stay product 100% except 8 rows read as customer. |

**Slice kind:** 236/291 (81.1%), unchanged. Excluding the 30 own-entity rows it is 236/261 (90.4%); also excluding the 14 mainline/regional/MRO rows it is **235/247 (95.1%)**: refinery 27/27, airline 5/5, geography 71/73, JV/part-owned 35/35, customer 8/8.

**What this means.** (a) Ruling 1 was right and Jev follows it. (b) **Ruling 2 was probably wrong.** "American had $23.6 billion in long-term debt" is the filer or co-registrant talking about itself, which rules 2.14 and 3.15 treat as a whole-company fact with **no slice**. The earlier labeling invented an entity slice for the filer's own name. Suggested revision: no slice for the filer's own name; entity_ownership only for stakes in other entities. (c) **Ruling 3 was not supported** by Jev: "mainline" and "regional carriers" fit the 3.13 test "the company operates as it", so segment is the more natural reading than unknown. Both (b) and (c) need an owner decision; my proposals should not be adopted as they stand.

**Lesson:** rule proposals need a test before they are logged as decisions; two of my three did not survive one.

**Suggested rulings (recorded 2026-09-29 as suggestions only; the owner has not read or approved them; no test pending):**
1. "Over time" / "eventually" = **undefined**; only "long term", "long-range" or "longer term" = long_term. (Proven: horizon 47/49.)
2. The filer's own name ("American had $23.6B of debt") = **no slice**; entity_ownership only for stakes in other entities such as joint ventures. (Recommendation, based on rules 2.14 and 3.15 and Jev's answers.)
3. Mainline, regional carriers and MRO = **segment** (the company operates as them, rule 3.13). (Recommendation, based on Jev's answers and the 3.13 test.)
Next step if approved: draft exact rules-file wording for the owner to read. The rules file is not edited until that wording is approved.

## 4. Rules vs Jev (220 rules, my judgment, not measured)

| Bucket | Rules | Share |
|---|---|---|
| A: Jev makes the call | 48 | 22% |
| B: Jev judges part, code does the rest | 29 | 13% |
| C: code only | 86 | 39% |
| D: policy, off-for-now, open, constraints | 55 | 25% |
| E: needs a writer (2.24 naming text, 4.7 `value_text`) | 2 | 1% |

- **Jev fits 77 of the 79 rules that need a judgment about meaning.** A tier 1 (proven): 1.5 1.6 2.29 2.30 7.7. A tier 2 (same shape, expect high): 2.23 2.3 2.11 2.12 2.13 2.14 2.17 2.18 2.20 2.33 1.11 3.40 3.47 3.13 3.14 3.15 3.16 3.21 3.6 3.8 3.33 3.50 3.52 6.4 7.8 4.5 4.6 4.9 4.19 4.1 4.2 4.3 4.16. A tier 3 (harder, measure first): 6.13 6.14 2.26 2.32 2.40 2.47 6.1 6.5 4.11 A2.3. B tier 2: 2.6 2.8 2.9 2.10 2.15 2.16 1.13 3.36 3.37 3.39 3.18 3.25 3.26 3.28 3.34 3.48 3.49 9.1 4.4 4.8 4.18 4.21 8.16. B tier 3: 2.4 2.43 4.10 4.12 4.15 4.17.
- **The 86 code rules:** ~52 are the machine itself (saving, keys, immutability, views, retries: Jev can't replace them), ~26 are exact checks, dates and arithmetic (Jev is worse), ~8 are fixed shortcut lists (1.8, 2.19, 2.22, 2.27, 2.28, 2.45, 6.3, 6.6). Rule 8.6 already bans meaning-based code patterns, so little judging code exists.
- **Options:** (1) code-heavy, Jev only judges: safest. (2) Jev-heavy, Jev also does exact checks and math: **not recommended** (errors add up: 5 steps at 99% is ~95%, 10 steps ~90%, vs a bar of under 1% wrong per fact; 1,200 requests/min ceiling; each task needs its own qualification, rule 8.13; breaks rule 8.1). (3) **mixed, recommended:** Jev decides meaning and reads pieces out (e.g. date parts as a Choice), code compares, calculates, saves. Suggested ground-rule wording: "AI decides meaning; code decides exactness." **Not yet decided by the owner.**

## 5. Tasks to try next (all untested except #1)
1. Fact type (done). 2. **Fact card:** one request asks every type's questions speculatively (state 3.6/3.8, baseline 3.52, surprise kind 4.1–4.3, who said it 4.9, growth basis 3.33, value vs change 3.50/7.8/4.6, span vs moment 3.47, horizon 3.40); code uses the branch matching the type. **Partly tested (§3.13): state, unit, span vs moment.** Baseline (3.52), horizon (3.40) and slice kind (3.13) are tested in §3.14. Who said it (4.9), growth basis beyond §3.13, value vs change (3.50) and the identity, link and claim-checker tasks are still untested. 3. **Claim checker before saving:** "does the quote support this state / unit / sign / period / slice?" (1.11, 1.13, 8.17). 4. **Name inspector** (checks, never invents; also run over the 1,282 catalog names): 2.3, 2.6–2.18. 5. **Slice sorter** (3.13–3.15, 3.18) and one-time sorting of XBRL axes by members (3.16, 3.21). 6. **Identity judge:** five yes/no tests per candidate, family gate, Choice among K candidates + "none" (2.4, 2.26, 2.32, 2.40, 2.43, 2.47); highest stakes, test last. 7. XBRL line-item matcher (6.1, 6.4, 6.5). 8. Forecast bookkeeping: corrections, withdrawal scope (4.5, 4.18, 4.19, 4.21). 9. **Missed-fact sweep:** tag every sentence and table row, compare with the reader's output (8.14, and the ⚠ under 4.17). Whole-corpus estimate (~22–58M calls): 13–34 days at 1,200 requests/min, $0.5–3K depending on prompt length. 10. **Rule-gap finder:** low confidence flags ambiguous rules. 11. Second grader for the launch test (8.17, 8.18; must be qualified first). 12. Price-move verdicts: Choice long/short + Score weight + confidence (A2.3; separately approved source; multi-step, least likely to reach 99%). 13. Rename detection (6.13, 6.14). 14. Update spotting (8.16).

**Patterns worth combining:** speculative fan-out; Choice with a "none of these" option (pick, don't write); Jev as the independent checker from a different vendor (rule 8.2; fixes the ⚠ that all AI judges share one vendor); Jev tags used to audit the reader, not to feed it (1.14 anchoring); mixed probes (same question as Noul and as Choice, disagreement = hold; may conflict with S4 "no votes", needs owner OK).

## 6. Constraints from the rules
- **8.12:** AI calls are subscription-only; Jev is pay-per-use, so it needs separate owner approval. Phase 6 (in `WIP/UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md`) lists the approved test pool (local AI, Haiku, Sonnet 5, Luna); **Jev is not on it**.
- **8.5 / 8.6:** confidence is never permission to write or merge; any cutoff needs a frozen owner decision. Use it only to hold, skip or route.
- **S4:** no cascades, votes or fallbacks. **8.13:** each task needs its own qualification test; the fact-type result doesn't transfer. **8.17:** under 1% wrong at 95% confidence, ~300 graded facts.
- **8.10 / 8.8:** the reader sees the whole event and quotes are exact; Jev (64k window, non-generative) can be neither. **A2.1 / A2.5:** the Driver system never judges price moves and never shows the realized return.

## 7. Where things are
- Durable: `experiments/runs/kf-*` (labels), `experiments/fixtures/events/*.json` (source text). The repo venv `venv/bin/python3` has the `neo4j` driver (system python has none, and no pip).
- **Saved in `DriversFinal/JEV scripts/`** (copied 2026-09-29; see its `README.md` for the run order per test): input builder, all prompt versions, build/run/score scripts, the frozen labels and inputs, and the per-rule fit map. **Not saved** (regenerate for cents): `h1_raw.json` (`pull_h1.py`, needs Neo4j) and every `results_*.json` (rerun the `run_*.py`). The original working copy in `/tmp` will vanish.

## 8. Next decisions (owner)
1. Approve more Jev tasks (start with #2, then #3–#5)?
2. Rule the open items in §3.10 (counts of openings, agreements "agreed to", pay raises, the three quotes with no key).
3. Approve the prompt clauses in §3.7 (V6) and the matching rules edit (rules 1.5, 1.6, 1.7, 7.7 and the new interpretations)? Or keep round 1's locked-wording prompt (94.1% vs 97.3–97.6% on the tuned items; no difference on fresh data beyond 2 of 39).
4. Who splits mixed quotes (the reader), and add a rule for it. Also rule on the surprise gaps (§3.12): does the company's own "exceeded our expectations" count as a surprise and against what baseline; does a company's macro view vs consensus count?
5. Choose code-heavy / Jev-heavy / mixed (§4).
7. §3.14/§3.15 gaps: "over time" / "eventually" = undefined works (approve as a rule line?). Decide: no slice for the filer's own name (recommended, replaces my earlier ruling 2); mainline / regional carriers / MRO as segment or unknown; corporate customer vs channel.
6. Rule the fact-card gaps (§3.13): sign convention for "used" measures and parenthesized expense rows; time_type for action events; `persists` vs `reported` when a policy also states a value.

## 9. Prompt change log (fact-type prompt, oldest first)
Rule status: **verbatim** = your locked wording (1.5, 1.7, 7.7); **interpretation** = new wording no rule contradicts; **conflicts** = contradicts a rule's literal text. Verbatim text of the recommended V6 is in §3.7; each later version is the one before plus the changes listed.

| Version | What changed | Why | Evidence | Rule status |
|---|---|---|---|---|
| **v1** (round 1, first prompt) | One Choice. Question: "What kind of fact does the quote state about the driver? Between two events, is there a standing level or severity you could re-read? Yes means metric; no means action_event." Options = the four locked 1.5 definitions (guidance included "Outlook verbs (expect, anticipate, target, plan to) make it guidance, never a metric state"). | Start: copy the rules as written. | 93/104 (89%); guidance 20/30 (forecast table rows called metric). | verbatim |
| **v1-steps** | Three questions: a Choice for surprise kind, a Noul "forward-looking?", a Noul "standing level? (ignoring forecast wording)"; code applied the rules' order. | Try explicit rule-by-rule steps. | 90/104; action 25/34 (announced future decisions called guidance). Rejected. | verbatim |
| **v2** | Same prompts; input got 400 characters of flattened text before the quote. | Give context. | No gain (93 / 90). | n/a |
| **v3** | Question shortened to "Which kind of fact does `quote` state?". Yes/no persistence test removed from the question and folded into the metric and action_event definitions. Added a `read` note and an `order` sentence (surprise, then guidance even with a number or table row, then metric or action_event). Each option got `what` (locked wording) plus `not_for`. Guidance `what` gained "A table row counts when its table or section is an outlook, guidance, forecast or estimate." Steps variant rebuilt as five one-rule Noul questions. | v1 omitted the rule that a forecast framing overrides the persistence test, and put a yes/no test inside a 4-option Choice (instructions and criteria disagreed, a Jev docs warning). | 103/104 (99%); blind guidance 35/35. Steps 99/104, worse. | order sentence and `not_for` restate 1.5; table-row clause is an **interpretation** |
| **C4** (round-1 final) | Metric `what` + "A figure that a company reports for each period (revenue, an expense, income, a cash flow, a balance) is such a variable, even when the sentence describes it with a verb like recorded, increased or decreased." Action_event `not_for` + "A figure reported for each period is not an action_event just because the sentence uses a verb like recorded or increased." | Reported line items ("recorded an income tax benefit of $94 million", explanations of a cost line's change) were called action_event. | Set tuned on: 27/31 to 31/31. Untouched set: 35/36 to 36/36. | **interpretation** |
| **V1** | Question now asks about the named driver: "Which kind of fact does `quote` state about the driver `driver_name`?" | The rules type a fact per Driver (1.7, 2.31, 7.7), but C4 ignored the driver name that was already in the state. | 16 to 19 of the 31 redo claims. | verbatim in spirit (1.7) |
| **V2a** | Guidance `what` + "and an assumption the company states for its forecast". Metric `what` + "A total, count or amount measured for a period is such a variable even when it is made up of transactions. A method, policy or arrangement that is already in use and continues is a condition in force, not the moment it was created. A standing per-unit level is a metric." Action_event `what` + "An incident counts even when the quote also states its effect on a result. A one-time decision to start, change or suspend a policy is an action_event." Action_event `not_for` + "A continuing condition or a measured severity is a metric." `read` + "When two drivers cover one topic, the driver name tells which fact is meant: a driver named for a per-unit amount is a metric; a driver named for the decision or event is an action_event." | Encode the outside reviewer's rulings 1, 2, 3, 5, 7 (§3.5) and rules 1.7, 7.7. | 19 to 24 of 31; other 257 items 256 to 255. Less stable: identical runs differed on 2 answers. | per-unit and one-time-decision sentences **verbatim** (7.7); the rest **interpretation** |
| **V2b** (superseded by V6) | `order`: "a forecast of a measured quantity or condition is guidance" (was "a statement of the company's own forward outlook"). Guidance `what` rewritten: removed "Outlook verbs such as expect, anticipate, target and plan to make a statement guidance"; now "A forecast, expectation or stated assumption about how a measured quantity or condition will be in a future period… The words expect, anticipate, target, plan and will do not decide the type by themselves: what matters is whether the statement forecasts a measurement or condition." Guidance `not_for` + "or an announced, committed or scheduled action (that is an action_event)". Action_event `what` + "An announced, committed or scheduled action stays an action_event even when it happens later." | Reviewer's ruling 4: a scheduled payment or an implemented plan is an action; an expected volume is guidance. Expect / plan / will alone must not decide. | 24/31 redo claims, stable across repeat runs; 344/350 overall vs 338/350 for C4; fresh data no different. | **conflicts with 1.6** (needs owner approval and a matching rule edit) |
| **V3** (rejected) | Guidance `what` + "A clause inside a forecast sentence that states an expected change in a measured quantity belongs to the forecast." Guidance `not_for` + "or an amount already owed or committed under a contract (that is a metric)". Metric `what` + "An amount already owed or committed under a contract, including a schedule of such amounts, is such a variable, not a forecast." | Two remaining real errors (a "despite a $4B expense increase" clause; a contract-minimums schedule). | No net change: fixed one error, broke another. | interpretation |
| **V4** | (vs V2b) `read` rewritten: "Judge the specific claim `quote` makes about the driver, not merely its verb, its number or its date… The driver name shows which claim is meant, but the quote and its context must support the answer: the name alone never decides it." (replaced the rule-1.7 name sentence). Metric `what` + "A change in a level, such as a pay increase, is a metric even when it takes effect on a stated date. A rate or assumption the company uses in its own current method or calculation is a condition in force; the word projected alone does not make it a forecast. When one sentence states both a standing per-unit amount and the decision that set it, the amount is a metric and the decision is a separate action_event." Action_event `what` + "A negotiation or implementation that is still underway is an action_event that continues. A milestone, such as a delivery or entry into service, is an action_event; a count of what exists now is a metric." | Second reviewer's rulings (§3.11). | 395/410 (96.3%); newly ruled 11/17; split dividend amount claims fell to 4/8; H6 38/39. | **interpretation** (new rulings, in no rule) |
| **V5** | (vs V4) "the company's own" restored: `order` "Otherwise the company's own forecast of a measured quantity or condition is guidance"; guidance `what` starts "The company's own forecast, expectation or stated assumption…"; guidance `not_for` + "a forecast made by someone other than the company". | V2b and V4 had dropped "the company's own" by mistake: an EU legal schedule and a contract-minimums schedule were called guidance. | H6 39/39; 391–394/410 (same as V4 within noise). | **verbatim** (1.5 says "the company's own") |
| **V6** (recommended, not approved) | (vs V5) `read` + "When two drivers cover one topic, one named for a per-unit amount and one for the decision or event, a quote that states the amount is a metric for the first, and a quote that states the decision is an action_event for the second." | V4 and V5 lost the rule-1.7 disambiguation; split dividend amount claims fell to 4/8. The quote still has to state the claim. | 399–400/410 (97.3–97.6%); split dividend claims 8/8; newly ruled 13–14/17; H6 39/39. | verbatim in spirit (1.7, 7.7) |

**Diagnostic, not a prompt:** V2b with the driver name hidden (state without `driver_name`, question and read without the name) scored 94.2% vs 96.4%; see §3.11.

**Wording never changed:** the four locked definitions and the whole surprise option (verbatim 1.5).
**Input format changes** (separate from the prompt): see §3.8.
**Clause-by-clause effect** (remove-one test on 350 items): see §3.6.
