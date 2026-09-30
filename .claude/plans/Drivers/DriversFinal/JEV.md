# Jev findings (TypeSafe System One)

*Tests of 2026-09-29: fact-type rounds 1–3 plus follow-up tasks. Reorganized the same day so a new agent can use it with no other context; no finding was dropped. §11 gives the pre-reorganization copy.*

## 0. Start here

**What Jev is.** Jev (TypeSafe "System One", model `jev-1.13.0`) is a pay-per-use API that **judges** text you send.
- It answers a multiple-choice question (Choice), a yes/no (Noul) or an ordered scale (Score), with probabilities.
- It never writes text.

**Why we tested it.** The Driver system turns company sources (filings, transcripts, news) into facts, called DriverUpdates, filed under named causes, called Drivers. Its rules sit in `.claude/plans/Drivers/DriversFinal/DRIVER_RULES_Simplified.md`, and `DRIVER_RULES_Categorized.md` uses the same rule numbers. Many rules need a judgment about meaning, for example: is this a forecast? Which unit? Compared with what? We tested whether Jev makes those calls reliably when the prompt states the rules.

**Status: exploratory only; nothing adopted.** Nothing changed in the repo, Neo4j or production except this file and `JEV scripts/`.

**How to read this file.** §0–§3 give the whole picture (read these first). Read §4–§5 before running anything. §6 has the evidence, §7–§11 are reference, and Appendix A holds the exact prompts.

**Before you do anything:**
- **Don't redo the fact-type test.** Start from V6 (§7, Appendix A.1) and `JEV scripts/README.md`, which gives the run order for every test.
- **Get the owner's OK before every new Jev test.** Pay-per-use was approved on 2026-09-29; the scope wasn't stated, so treat it as covering tests only. Each test costs cents; the whole session cost about $1.3.
- **Get owner approval for prompt clauses or rules edits.** That covers any clause beyond the rules' locked wording, and any change to the rules file.
- **Treat "rulings" in this file as proposals.** They come from two outside reviewers and from Claude, not from the owner (§3).

**Glossary**

| Term | Meaning |
|---|---|
| Rule 1.5, 3.6, … | Numbered rules in `DRIVER_RULES_Simplified.md` |
| Fact type | metric · guidance · surprise · action_event (rule 1.5) |
| kf runs | Earlier-model extraction runs, `.claude/plans/Drivers/experiments/runs/kf-*/*.raw.json`. Their labels are our main answer keys: "silver" (not truth), mostly 2 airlines. |
| DEV, H1–H6 | Fact-type test sets (§5.2) |
| V0–V6 | Fact-type prompt versions (§7). V6 is recommended; V0 = round 1's final prompt (also called C4, `QC4.json`) |
| Decided / undecided | Whether the rules settle a fact's answer. Undecided facts are reported separately. |
| Raw / after ruling / strict | Raw = match with the key. After ruling = Claude read every miss against the rules and set unclear items aside. Strict = unclear items counted as wrong. |
| Confidence | Jev's own certainty score for a Choice answer, 0 to 1 |
| Phase 6 | The approved AI test pool (local AI, Haiku, Sonnet 5, Luna) in `.claude/plans/Drivers/WIP/UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md`. Jev is **not** on it. |
| Video 1, Video 2 | Sources for the idea bank: "Every Jev Concept Explained" and Indie Dev Dan's "10 levels" |

## 1. Bottom line

- **Jev judges meaning well when the prompt states the rules explicitly.** On fact type, the first prompt matched earlier labels 81%. The rewritten prompt got **257/258 (99.6%)** on facts the rules decide, and 71/71 on sets never used for tuning. The prompt was the problem, not the model.
- **Recommended fact-type prompt: V6, 399–400 of 410 (97.3–97.6%)** after two outside reviewers ruled on the hard cases. Those rulings are proposals, not owner-approved.
  - Round 1's prompt gets 386/410 (94.1%) on the same items.
  - On fresh metric facts, V6 gets 39/39 and round 1's prompt 37/39.
  - V6's lead is a few items, mostly 8 split dividend claims. Swings of 1–3 items are run-to-run noise.
- **Where Jev fails:**
  - number and sign comparisons, and containment in a range (leave these to code);
  - growth-table headers;
  - places where the rules are silent: sign convention, "over time", the filer's own entity, airline groupings (§3.3).
- **Confidence works only as a "review this" flag, never as permission to write or merge** (rules 8.5, 8.6). With V6, confidence < 0.9 flags 19% of facts and catches all 11 errors; < 0.75 flags 12% and catches 9.
- **Jev is only a judge.** It can't write names or quotes, read a whole filing, or do reliable math, dates or counting.
- **Jev is not perfectly repeatable.** Identical calls differ on about 1% of items (2/288, 3/413), always at low confidence, so cache decisions (rules 2.46, 5.4).
- **Detect surprises with the comparison-kind question (S2), not the type question.** One quote backs both a surprise and its home fact (§6.2).
- **The claim checker catches a different reader's errors, not Jev's own.** It flags planted wrong labels (97% state, 89% fact type) but only 2 of 32 real Jev mistakes (§6.5).
- **Recommended setup: mixed.** Jev decides meaning; code does exact checks, math and saving. The owner has not decided (§8).
- **How far to trust the numbers:** keys are silver (earlier-model labels, reviewer rulings, Claude's labels). The fact-card and claim-checker state tests come from 3 filings of 2 airlines, and V4–V6 were tuned on the same items, so industry coverage is untested and the scores are optimistic.
- **Recommended next step:** stop new capability tests, settle the rulings (§3), then run every task once on a fresh multi-industry test set with keys the owner approves, locked before any call (rule 8.17).

## 2. Results at a glance

Decided items. Keys are silver: earlier-model labels, reviewer rulings, or Claude's labels frozen before the run.

| Task (rules) | Result | Keys and caveats | § |
|---|---|---|---|
| Fact type, round 1 (1.5–1.9) | 257/258 (99.6%); untouched sets 71/71 | kf labels + Claude's rulings; mostly 2 airlines | 6.1 |
| Fact type, V6 (round 3) | 399–400/410 (97.3–97.6%); fresh H6 39/39 | Tuned on these items; reviewer rulings not approved | 6.1 |
| Surprise comparison kind (4.1–4.3) | 64/65 | Claude's frozen labels; 26 of 42 claims are templated headlines | 6.2 |
| Surprise state (4.10–4.13) | 39/41 | same | 6.2 |
| Metric state (3.5, 3.6) | 91.9% raw; 97.9% after ruling | kf labels | 6.3 |
| Unit of the value / of the change (3.28–3.33) | 97.4% / 97.5% raw; 98.1% / 97.5% after ruling | kf labels | 6.3 |
| Span vs single moment (3.47) | 94.1% raw; 827/827 after ruling | kf labels | 6.3 |
| Comparison baseline (3.52) | 98.1% raw; 99.3% after ruling | kf labels + surprise labels | 6.4 |
| Horizon (3.40) | 39/49; 47/49 once "over time" = undefined | Claude's labels | 6.4 |
| Slice kind (3.13–3.15) | 81.1% raw; 237/237 where the rules decide; 95.1% excluding two rule gaps | kf labels | 6.4 |
| Claim checker (idea H) | Planted wrong labels flagged: state 97%, fact type 89%. Real Jev mistakes flagged: 2/32. Re-classify and compare: 99.3% | Planted and real errors | 6.5 |

## 3. Waiting on the owner

### 3.1 Decided (owner, 2026-09-29)
- Escalation to a generative model is allowed. Rule S4's wording is not yet updated.
- A Jev flag is an available option. Nothing has been ruled on what a flag does.
- Confidence bars and raw probabilities come later.
- Jev pay-per-use is approved.

### 3.2 Decisions waiting
1. **What next?** Recommended: stop new capability tests; settle the rulings below; build one fresh multi-industry test set with owner-approved keys, locked before any call (8.17); run every task once on it. Other options:
   - run the claim checker against a different reader's real errors (needs Phase 6 approval for a reader model);
   - test the identity funnel (ideas B, C, L; §9.2), which first needs a same/different key we don't have.
2. **V6:** approve its clauses and the matching rules edit (rules 1.5, 1.6, 1.7, 7.7 and the new interpretations; §7)? Or keep round 1's locked-wording prompt? It scores 94.1% vs V6's 97.3–97.6% on tuned items, and differs by only 2 of 39 on fresh data.
3. **Reviewer proposals:** rule the proposals in §6.1 and the open questions in §3.3.
4. **Mixed quotes:** who splits them? Recommended: the reader, with a rule written for it.
5. **Architecture:** choose code-heavy, Jev-heavy or mixed (§8).
6. **Rule S4:** align its wording with the escalation ruling. This is a rules-file edit and has not been done.

### 3.3 Open rule questions (no ruling yet)

**Fact type (after round 3; the second reviewer's view vs Jev's):**
- **Counts of things opened during a period** ("opened 9 new stores and closed one"): the reviewer says metric; Jev says action_event (0.88).
- **"Have agreed to make available"** (the CRAF agreement): the reviewer says metric, because it is in force; Jev says action_event (0.74).
- **Pay increases with an effective date:** the reviewer says metric; Jev flips between the two at about 0.5.
- **A whole dividend-declaration sentence under a per-share driver:** the reviewer wants the amount and the decision split into two claims. Split that way, Jev agrees 8/8.
- **No key from either reviewer:**
  - "expect to complete the U.S. implementation by the end of 2027": guidance or action?
  - "we became subject to the EU ETS on January 1, 2024": an event or a standing condition?
  - "We paid $1.4 billion in 2025 to our employees": a payment or a period total?
- **Mixed quotes:** the reader separates the claims (rule 2.34, per the reviewer). A rule saying so should be written. Jev can't detect mixed quotes (§6.1).

**Surprise:**
- **The company's own "exceeded our expectations":** Jev calls it a surprise against consensus (0.93–0.98, on 3 of 4). Rule 3.52 says "'Exceeded expectations' on a surprise → consensus", but no rule says whether the company's own expectations count.
- **A macro view against consensus** ("our view is for above consensus global growth"): Jev says surprise (0.69), but it is not a company value.

**Fact card:**
- (a) The sign convention for measures written as "used", and for expense rows in parentheses.
- (b) time_type for action events that have no value.
- (c) `persists` vs `reported` when an ongoing covenant or policy also states a value.

**Horizon and slices.** These are Claude's suggested rulings; the owner has not read or approved them.
1. "Over time" and "eventually" = **undefined**; only "long term", "long-range" or "longer term" = long_term. Proven: horizon went to 47/49.
2. The filer's own name ("American had $23.6B of debt") = **no slice**; entity_ownership only for stakes in other entities, such as joint ventures (rules 2.14, 3.15).
   - This replaces Claude's earlier proposal (own entity = entity_ownership), which Jev did not reproduce (§6.4).
3. Mainline, regional carriers and MRO = **segment**, because the company operates as them (3.13).
   - Still open: is a corporate customer group a customer or a channel?

Next step if approved: draft exact rules-file wording for the owner. The rules file is not edited before that.

## 4. Using Jev

**API**
- **Endpoint:** `POST https://api.typesafe.ai/v1/systemone`, header `Authorization: Bearer $TYPESAFE_API_KEY`.
- **Key:** `TYPESAFE_API_KEY` is in `/home/faisal/EventMarketDB/.env` (line 29) only, not in the shell environment.
- **Model:** pin `jev-1.13.0`; `jev-latest` points to it today.
- **Docs index:** `https://docs.typesafe.ai/llms.txt`; add `.md` to a page path to read that page.

**Price and limits**
- **Price:** $0.042 per million input tokens; output is free.
- **Rate:** 1,200 requests/min and 250k tokens/s (the docs say limits change without notice).
- **Size:** 64k tokens per request, of which 32k for the state plus the longest question. Text only.
- **Option limits** (docs, checked 2026-09-29): a Choice takes at most **255** options, a Score at most **10** levels.
  - The docs' cookbooks use 182 and 218 options; we tested at most 4.
  - Over 255 needs a tree, a window or a shortlist (ideas B, C, L).

**Question types**
- **Noul:** the probability of yes. It has no confidence field.
- **Choice:** one of N options, with probabilities and a confidence.
- **Score:** ordered levels.
- Questions in one request run in parallel and can't see each other.
- Don't reuse a threshold across Noul and Choice.

**Documented weak spots** (jev-1.13 "jaggedness" page): reads literally; weak on math, dates and counting; indirection; large irrelevant state; instructions and criteria that disagree; can't generate text.

**Measured cost and speed**
- About 280 input tokens minimum per call, plus about 21 per extra short question.
- The fact-type prompt uses about 1,050 tokens per fact (round 1's wording) or about 1,460 (V6), roughly $0.00006.
- 2,500 calls took 60 s with 8 threads.

## 5. How to test

### 5.1 Method (reuse this)
1. **Answer keys:**
   - kf-run labels: 1,470 typed facts, 628 unique quotes, only 3 filings of 2 airlines. The fact-card fields cover 960 unique facts, whose labels agree across runs on 97–100%.
   - or Claude's own labels, **frozen before any Jev call**, with the hash recorded.
2. **Source text:** `.claude/plans/Drivers/experiments/fixtures/events/<accession>.json` (field `text_parts`).
3. **Run and rule:** run twice, to see the noise. **Read every miss with its source against the rule**, and rule it: Jev wrong, label wrong, or undecided/unclear. Report the unclear ones separately.
4. **Tune, then retest:** fix the prompt from the failures, then retest on sets the tuning never saw.
5. **Test rule proposals before logging them:** 2 of Claude's 3 slice and horizon proposals failed their first test (§6.4).

### 5.2 Fact-type test sets
| Set | Size | What |
|---|---|---|
| DEV | 115 | Design set |
| H1 | 40 | Guidance quotes from 24 other companies (Neo4j `GuidanceUpdate`), labeled by Claude blind |
| H2 | 60 | Fresh kf facts |
| H3 | 31 | Fresh kf facts (later used for tuning) |
| H4 | 40 | Fresh kf facts |
| H5 | 75 | 35 more pool facts, labeled by Claude before any Jev call, + 40 unused metric facts |
| H6 | 40 | Fresh metric facts (round 3) |

No unused action or guidance facts remain in the kf pool.

### 5.3 Input format ("state")
Built by `JEV scripts/jevlib.py`. Named fields: `where_it_appears`, `driver_name`, `text_before_quote`, `quote`, `text_after_quote`.
- **`where_it_appears`:** plain words with correct articles, for example "Management's Discussion and Analysis of a quarterly report (10-Q)". Round 1 had "of an quarterly" and raw names like "RiskFactors"; both are fixed.
- **`driver_name`:** underscores become spaces; **strip `_guidance` / `_surprise`**, which would leak the type. The question asks about this driver, and some rulings depend on it (dividend).
- **Before the quote:**
  - about 520 characters, starting at a sentence or paragraph start (never mid-sentence), with up to 3 heading lines above;
  - for a quote inside a table, include the table start (title, column headers) and its end;
  - remove page-header boxes ("Company | 2025 Form 10-K");
  - rewrite `##TABLE_START/END` as `[Table]` / `[End of table]`.
- **After the quote:** about 260 characters, ending at a sentence end. Drop trailing heading-only lines and unfinished tables; it may be empty.
- **Quote:** exact; find it with a whitespace-insensitive match. **Never collapse whitespace.**
- **Source formats:** 10-K / 10-Q sections keep paragraphs and `##TABLE` markers. **8-K exhibit text in the database is flat** (no line breaks; table rows run together). That is the source itself, not a bug to fix.

### 5.4 Traps
- **`GuidanceUpdate` in Neo4j is not an answer key.**
  - It labels dividend declarations as guidance.
  - Its `source_key` is a section name, and its quotes start with "[8-K]" / "[PR]".
  - Its `period_scope` doesn't follow rule 3.40, so a horizon test built on it is invalid (§6.4).
- **Never let a label field share a name with an input field.** A builder overwrote the input with the answer, and the first fact-card run scored a fake 100%. Labels are now `L_*`, and every runner asserts its input.
- **Misses overcount:** the same sentence appears in several cuts (one forecast table ×6, winter storms ×3, "$4.00 per gallon" ×3).
- **Earlier-model labels are sometimes wrong:**
  - a scheduled profit-sharing payment labeled metric;
  - 7 state labels that contradict rule 3.6;
  - 12 span labels;
  - the filer's own legal entity labeled entity_ownership.
- **Older WIP notes saying "Jev is DEFERRED"** refer to a producing task (finding why a name loses a cause), not to judging.

### 5.5 Lessons
- The prompt is the lever. State the rule that decides each close call; for example, restating rule 1.7 moved split dividend amounts from 4/8 to 8/8.
- Checking a single label is weaker than choosing among labels (§6.5).
- Freeze the labels and record their hash before the first call. Run twice to see the noise.
- Test a rule proposal before logging it as a decision.

## 6. Test details

### 6.1 Fact type (rounds 1–3)

**What fixed round 1** (DEV, 104 decidable facts):

| Prompt | Input | One Choice | Five stepped Noul questions |
|---|---|---|---|
| old | old | 93 | 90 |
| old | clean | 92 | 94 |
| **new** | old | **103** | 98 |
| **new** | clean | **103** | 99 |

The prompt was the lever. Keep the clean input anyway, and don't use the stepped pattern. What was wrong with the first prompt:
- It left out the rule that a forecast framing overrides the persistence test.
- It put a yes/no test ("Yes means metric") inside a 4-option Choice, so the instructions and criteria disagreed.
- Its 5-question variant had an indirect "ignoring forecast wording…" question, mixed Choice with Noul, and its forecast question grabbed announced future decisions.
- Its input was broken: collapsed whitespace (destroying paragraphs, headings and tables), windows starting mid-sentence, no text after the quote, and page-header junk.

**Round 1 result:**
- DEV 103/104 · H1 35/35 · H2 52/52 · H3 31/31 (tuned on) · H4 36/36, so 257/258 overall.
- 28 facts were set aside as undecided.
- Confidence < 0.8 flagged 13% of facts, including 19 of the 28 undecided.
- Rule 8.17 needs about 300 graded facts with none wrong; 71/71 on untouched sets supports only "under about 4% wrong".
- Ruled by Claude; mostly two airlines; no surprise examples in this round (see §6.2).

**First reviewer's rulings on the 28 undecided facts** (proposed interpretations). The instructions that came with them:
- identify the precise claim first;
- split mixed claims;
- apply existing rules before calling something a new question;
- keep forecast assumptions distinct from observed values;
- bring back only what stays undecided.

| # | Facts | Ruling |
|---|---|---|
| 1 | Cash-flow amounts ("net purchases of short-term investments", repayments) | metric: a period total made of transactions is still a total |
| 2 | Winter-storm revenue impact | action_event: an incident (a continuing condition or measured severity would be metric) |
| 3 | Forecast assumptions ($4.00/gal, expected recovery, expected expense increase) | guidance, kept as an assumption, not an observed price |
| 4 | PFAS transition; scheduled profit-sharing payment; "do not plan to use exchange agreements" | action_event; action_event; guidance (expected volume) |
| 5 | Dividend per share | metric **only under a per-share driver**; a declaration under `dividend` is an action (rules 1.7, 2.31) |
| 6 | One quote with two claims | split first (a balance and its expected use; past openings and future targets) |
| 7 | Standing arrangements / an accounting method already in use | metric (not their creation) |
| 8 | Pay levels, reserve-adjustment amounts, revenue performance | metric; "nine record weeks" must not become a revenue amount of nine |

Main clarification, which **needs owner approval because it conflicts with the broad wording of rule 1.6**:
- a forecast of a measurement or condition is guidance;
- an announced action stays an action even when it happens later;
- the words "plan", "will" and "recorded" don't decide the type on their own.

**Round 2 (redo with the first reviewer's rulings).**
- **Keys:** the 28 facts plus the one clear round-1 error made 29 items. The 2 mixed quotes were split into exact sub-spans (4 claims), giving 31 claims. All 288 round-1 items plus H5 were re-run.
- **Prompt versions tried:** V0 (round 1), V1, V2a, V2b, V3 (§7).
- **Results on the 31 redo claims / the other 257 items:** V0 16 / 256 · V1 19 / 256 · V2a 24 / 255 · V2b 24 / 255.
- **V2b by group:**
  - cash-flow totals 6/6, storms 3/3, forecast assumptions 4/5, actions 2/2, expected volume 1/1;
  - standing arrangements 1/4, mixed 3/4, pay/reserve/records 2/3, dividend 1/2;
  - of the 7 misses, 5 are undecided and 2 are real errors.
- **All 350 decided items** (9 undecided and 4 unclear set aside): V0 338 (96.6%), V2b 344 (98.3%). Fresh H5 alone (67): V0 66, V2b 65.
- **The 6 real errors under V2b** (confidences 0.38–0.71):
  - a "despite a $4B expense increase" clause inside a forecast sentence;
  - the projected non-GAAP tax-rate sentence;
  - a contract-minimums schedule called forecast;
  - two explanations of a cost line's change called action;
  - a financing-repayments total called action.
- **Remove-one-clause test** (350 items): every clause helps more than it hurts.
  - Dropping "a total made of transactions" breaks 8.
  - Dropping "incident even when its effect is stated" breaks 3.
  - The rule-1.6 rewrite breaks 6 and fixes 2.
  - The driver-name sentence breaks 6 and fixes 3.
- **What didn't work:**
  - **A mixed-claim detector.** The broad version flags 107 of 288. The narrow one ("already true and also about the future") catches both known cases but flags 47 of 286 (16%), mostly announcements with a future date. So **the reader must split claims, not Jev.**
  - **V3's extra clauses** swapped one error for another.

**Second reviewer's rulings (round 3; proposed, not owner-approved).** The reviewer's principle: classify the specific claim, not merely its verb, number or date; a proposed name alone must never force the answer.

| Question | Ruling |
|---|---|
| Pay raises | metric: the pay change ("increased"); the effective date doesn't change it. Approving the raise is a separate action. |
| Projected 20% tax rate | metric: a rate used in the company's current non-GAAP method; "projected" alone doesn't make it guidance |
| Ongoing agreements | in force → metric (`persists`); a negotiation or implementation underway → action (`continued`). CRAF is the first kind. |
| Dividend declaration under a per-share driver | the amount is metric; the declaration is a separate action. Don't type the whole sentence as an action under the per-share driver. |
| "1,000th aircraft" | "received our 1,000th aircraft" = delivery milestone → action; "our fleet contains 1,000" = count → metric |
| Mixed quotes | the core's reader separates the claims: "opened 9 stores" = metric count, "expect to open 45" = guidance |

**Round 3 method.**
- Keys applied to 17 items. H2-043 (a LATAM joint venture) was marked action by Claude because the reviewer didn't name it.
- 2 mixed quotes were split into 4 claims; 2 claims were left without a key.
- Prompts V0, V2a, V2b, V4, V5 and V6 (two runs each of V4, V5 and V6) were run on:
  - the 365 earlier items;
  - 8 split dividend claims (the amount under `dividend per share`, the decision under `dividend`);
  - 40 fresh metric facts (H6).
- V2b was also run with the driver name hidden.
- About 5,000 calls, about $0.26.

| Prompt | All 410 decided | Newly ruled 17 | Split dividend claims 8 | Fresh H6 39 |
|---|---|---|---|---|
| V0 (round 1) | 386 (94.1%) | 10 | 4 | 37 |
| V2a | 394 (96.1%) | 11 | 7 | 38 |
| V2b | 392 (95.6%) | 9 | 6 | 36 |
| V4 | 395 (96.3%) | 11 | 4 | 38 |
| V5 | 391–394 (95.4–96.1%) | 11 | 4 | 39 |
| **V6** | **399–400 (97.3–97.6%)** | 13–14 | **8** | 39 |

**Round 3 findings**
- **Driver name hidden:** 18 of 365 answers change (5%), and accuracy drops from 96.4% to 94.2%.
  - The changes are mostly at confidence < 0.5.
  - For dividend quotes, the name moves Jev from action (1.00) to metric (about 0.4).
  - So the name tips close calls but rarely forces a confident answer.
- **Split dividends:** the decision claim is action_event at 1.00 under every prompt.
  - The amount claim is metric **only when the prompt restates rule 1.7**: V6 8/8, V2a 7/8, V2b 6/8, V4 and V5 4/8.
  - V4 removed that sentence to follow "the name never forces" and lost it. V6 restores it in a form that keeps the quote as the deciding evidence.
- **A mistake Claude made:** V2b and V4 dropped "the company's own" from the guidance definition, so an EU legal schedule and a contract-minimums schedule were called guidance. V5 restores the locked wording; V6 keeps it.
- **V6's 11 errors**, all caught by confidence < 0.9 (19% of facts flagged):
  - the storm sentence ×3 (DEV-042/052/061; confidence 0.38–0.41; regressed from V5);
  - fragments about notes or a cost line's change: H2-045, H4-007, H5M-018 (≤ 0.49);
  - DEV-085 (0.84), H1-013a (0.88), H1-035 (0.38), H2-039 (0.74), H2-048 (0.49).
- **Noise:** identical V6 runs differ on 3 of 413 items, all at low confidence. Cash-flow totals (4–5 items) sit near 0.4 and flip between V4, V5 and V6.
- **Fresh H6:** V6 39/39, V0 37/39. One quote was set aside ("We paid $1.4 billion"; §3.3).
- **Caveats:**
  - V4–V6 were tuned on these items.
  - H6 contains only metric facts.
  - The keys come from two reviewers and Claude.
  - V6's lead is a few items, mainly the split dividend claims, so treat V6 as a candidate, not a proof.

**Files:** `variants.py` (V0–V6), `V6.json`, and the round scripts listed in `JEV scripts/README.md`.

### 6.2 Surprise (before this test, 0 of 413 items were surprises)

**Data**
- 75 items sampled at random (seed 2026) from Neo4j, read-only:
  - Benzinga news headlines with beat/miss/estimate wording (16,941 match);
  - transcript prepared remarks about guidance (2,487) or consensus (289);
  - 8-K exhibits mentioning consensus (255).
- News and transcripts are off in release 1 (rule 9.5), so this tests the language, not the release-1 source.
- Quotes are exact substrings (8.8). Headlines were split into one comparison per claim (4.1, 4.16).

**Labels**, frozen before any call (hash `b43d406630dce0a8`):
- **42 surprise claims:**
  - kinds: actual_vs_consensus 20, actual_vs_guidance 12, guidance_vs_consensus 10;
  - states: beat 17, in_line 12, missed 11, unknown 1, unclear 1;
  - sources: 26 news, 16 transcript.
- **23 look-alike controls:** 9 guidance movements or forecasts with no comparison, 7 comparisons with last year, 1 action, and 6 where "consensus" means something else.
- **10 unscored:** mixed headlines, and "our expectations".

**Rules applied to the labels**
- **1.5:** a surprise compares a company value with an outside expectation, or an actual with the company's own earlier guide. It is **not** a comparison with a prior-period actual, and **not** a new guide against its own earlier guide.
- **The 4.1 table, 4.2, and 4.3:** the kind = the basis + the baseline, not whether the period ended.
- **4.10:** in_line = inside a closed range or on its edge, with no good/bad words. A range that contains the consensus is in line.
- **4.11–4.13:** beat/missed are judged by meaning. "Above"/"below" don't mean good or bad on their own, and expenses need the source's framing, else unknown.
- **3.52:** company target wording = previous_guidance.

**Run:** about 340 calls, $0.016. Three questions: S1 fact type (V0 and V6), S2 which comparison, S3 beat / in_line / missed / unknown. S2 and S3 were written from the rules (Appendix A.2, A.3; `surprise_prompts.py`).

| Task | Result |
|---|---|
| **S2 comparison kind** | **64/65.** All 42 surprise claims right (20/20, 12/12, 10/10); controls answered "none" 22/23 (the miss at 0.39) |
| **S3 state** | **39/41.** beat 17/17, missed 11/11, in_line 11/12, unknown 0/1. Both misses are at confidence < 0.5: an estimate on the edge of a guided range, and an expense "slightly below our guided range" that rule 4.12 wants as unknown. |
| S1 fact type, answered "surprise" | V0 39/42, V6 36–37/42. **Every other answer was the home metric or guidance type**, which rules 4.1 and 4.14 require alongside a surprise, so 42/42 are acceptable. |
| S1 controls called surprise | 1/23 under both prompts ("a 3.5 penny increase over the midpoint of our August guidance", 0.34–0.36). V6 also called "Raises Guidance" an action (0.59). |

**Findings**
1. **One quote backs two facts.** "EPS $1.83 Beats $1.76 Estimate" supports both a surprise and its metric home fact (4.14). With the suffix stripped from the name, the type Choice can't know which is meant. **Use S2, with its "none" option, to detect surprises.**
2. **V6 has no advantage here.** It answers "surprise" less often than V0 because it asks about the driver.
3. **Most items were easy.** 29 of 42 quotes contain explicit words (beat, miss, in line, above, exceeded), and 26 are templated news headlines. The hard cases were an estimate inside or on the edge of a range (numeric containment, which code should do) and expense direction (4.12).
4. **Mixed statements:** headlines that state a guidance change and a consensus comparison together (4.16) get one label (mostly guidance, 0.38–0.80). The reader must emit separate facts.
5. **The company's own "exceeded our expectations"** and **a macro view against consensus** are open gaps (§3.3).

**Caveats:** Claude's labels (frozen first); 42 claims, 26 of them templated headlines; a single run; nothing tuned.

### 6.3 Fact card: metric state, unit, span vs moment

**Setup**
- Keys: kf-run labels (960 unique facts).
- Prompts written from rules 3.5 + 3.6 (state), 3.28–3.33 (unit) and 3.47 (span); one version each, nothing tuned (Appendix A.4–A.6; `card_prompts.py`).
- Two runs each: 4,932 calls, about $0.21.
- **Bug found:** the first run scored 100% on state and "unknown" on every unit, because a label field named `state` had overwritten the input field `state` (see §5.4).

| Task | Facts | Raw | After ruling | Strict | Two runs differ | Confidence flag |
|---|---|---|---|---|---|---|
| Metric state | 718 | 660 (91.9%) | **667/681 (97.9%)** | 92.9% | 2 | < 0.9 flags 19%, catches 42 of 58 misses |
| Unit of the value | 643 | 626 (97.4%) | **627/639 (98.1%)** | 97.5% | 1 | < 0.9 flags 15%, catches 16 of 17 |
| Unit of the change | 239 | 233 (97.5%) | **233/239 (97.5%)** | 97.5% | 4 | < 0.6 flags 10%, catches 6 of 6 |
| Span vs single moment | 866 | 815 (94.1%) | **827/827 (100%)** | 95.5% | 3 | < 0.9 flags 18%, catches 39 of 51 |

**All 132 misses read and ruled:**
- state: 14 Jev wrong, 7 label wrong, 37 unclear;
- value unit: 12 Jev wrong, 1 label wrong, 4 unclear;
- change unit: 6 Jev wrong;
- span: 0 Jev wrong, 12 label wrong, 39 unclear.

**Findings**
1. **State errors are number comparisons and fragments.**
   - Negatives and losses: "Pre-tax margin (3.4)% (5.2)%" called decreased at 0.94; a narrowing loss called decreased although the prompt says it counts as an increase; operating income $157 vs $38 called decreased.
   - Fragments whose direction word sits before the quote ("4% effective June 1, 2025").
   - **Code should compute direction from two numbers** (rule 3.51 already checks the sign).
2. **7 state labels contradict rule 3.6.** Schedules "decreasing on an annual basis" were labeled `reported`, but a stated direction wins; Jev followed the rule.
3. **The sign convention is a rule gap.** Examples: "Net cash used in investing activities was $2.3B and $1.2B", and rows in parentheses like "Interest expense, net (400) (452)". Rule 3.34 says to store the signed value, but the earlier labels are inconsistent with each other. 18 of the 37 unclear state items are this gap.
4. **Unit errors cluster on growth tables.**
   - When the basis sits in a header ("Q2 2026E (vs. Q2 2025)", a change column like "10.7%"), Jev says plain `percent`. Rule 3.33 says growth is never plain percent (year over year unless stated).
   - A coupon in a note's name ("4.95% Notes due 2028") pulled a $1.0B money total to `percent` at 0.83.
   - All 6 change-unit misses had confidence < 0.40.
5. **Span:** 95.9% on facts with a number, but 84.1% on facts without one (mostly actions).
   - The rules don't define time_type for an action ("repaid in full $629 million", "proceeds received").
   - 12 labels were wrong: "scheduled maturities in 2026 are $1.4B", "we paid $1.4B in 2025" and "prices ranging from $1.86 to $4.75 during the quarter" are durations.

**Open rule questions:** §3.3 (fact card a–c).

### 6.4 Baseline, horizon, slice kind (and a rescore)

**Setup**
- Prompts written from rules 3.52, 3.40 and 3.13–3.15; one version each, nothing tuned (Appendix A.7–A.9; `more_prompts.py`).
- Two runs each: about 2,140 calls, about $0.08.
- Labels frozen first: hash `ca1fa5c4364f6b7a` for the kf-based items, `ad311b3a4e8e1105` for horizon.

| Task | Keys | Items | Raw | After ruling | Strict | Runs differ |
|---|---|---|---|---|---|---|
| **Baseline** (3.52) | kf labels + Claude's mapping of the frozen surprise labels | 581 | 570 (98.1%) | **573/577 (99.3%)** | 98.6% | 3 |
| **Horizon** (3.40) | 49 real sentences labeled by Claude from the rule and the wording | 49 | 39 (79.6%) | 39/39 on the 41 not touching "over time" | 79.6% | 0 |
| Horizon, first attempt (**invalid**) | older `GuidanceUpdate` period_scope | 148 | 76 (51%) | not usable | — | 1 |
| **Slice kind** (3.13) | kf labels | 291 | 236 (81.1%) | **237/237 where the rules decide** | 81.4% | 6 |

**Baseline**
- By kind: consensus 30/30, previous_guidance 22/24, sequential_period 9/11, prior_year 437/439, none 72/77.
- 11 misses:
  - **3 labels wrong:** a before/after amendment is not a prior period; a quote with no comparison.
  - **4 Jev wrong:** a table row without its column heading (0.79); "$70M in 2025 … $5M in 2026" read as year over year (0.90); "consensus" used in another sense.
  - **4 unclear:** one quote backs two facts. For example, "up 17% year over year, exceeding the midpoint of our outlook" is prior_year for the metric and previous_guidance for the surprise.
- Confidence isn't needed here: only 7 of the 11 misses are flagged at < 0.9.

**Horizon**
- **The first attempt was invalid.** It used labels from the older guidance pipeline, which contradict rule 3.40 ("We continue to be in that range" labeled short_term), and half of its stated-window labels depended on context Jev wasn't shown.
- **The proper test:** stated_window 8/8, short_term 10/10, medium_term 8/9, long_term 8/9, **undefined 5/13**.
  - All 8 undefined misses are "over time" or "eventually", answered long_term at 0.90–1.00. **That was the prompt's fault:** Claude wrote "over time" into the long_term option, and rule 3.40 doesn't say where "over time" goes (it only says undefined = "going forward").
  - The other 2 misses: "over the next three to five years" (Jev said stated_window), and a sentence holding two horizons (a label error).
- Explicit words (near term, medium term, long term, going forward, a named year) are read correctly.

**Slice kind**
- By kind: geography 73/73, segment 32/32, customer 7/7, product 89/113, entity_ownership 35/65.
- 55 misses: 1 label wrong ("sales to airline segment" is a customer group) and **54 unclear**:
  - **30 are the company's own legal entity** (`americanairlinesinc`), which Jev calls unknown or segment. Rule 3.13 says only joint ventures and part-owned companies are clean entity_ownership, and that "other entity rows are provisional".
  - **24 are airline groupings the rules don't place:** mainline and regional carriers (product or segment?), cargo, MRO, passenger, corporate (channel or customer?).
- There is no clear Jev error.

**Rescore after Claude's three proposed rulings.**
- The two prompts were changed (`HORIZON2`, `SLICE2`), the keys rebuilt from the rulings (slice keys hash `0e425c40d60ac99c`, frozen before the run), and the tests rerun: 680 calls.
- Because the keys follow the rulings, this shows whether Jev **follows a stated rule**, not fresh accuracy.

| Ruling | Prompt change | Result |
|---|---|---|
| 1. "over time" / "eventually" = undefined; long_term only when the source says long term, long-range or longer term | long_term `what` = "The quote itself says long term, long-range or longer term, in words, with no dates."; undefined `what` adds "over time, eventually or in the future" | **Works:** horizon 47/49 (95.9%) vs 39/49; undefined 13/13. The 2 misses are the mixed-sentence label and "over the next three to five years" (stated_window). |
| 2. The company's own legal entity = entity_ownership, provisional | entity_ownership `what` adds "Other entity rows, such as the company's own subsidiary reported on its own, are provisional." | **Not reproduced.** Jev never says entity_ownership for `americanairlinesinc` (0/30: unknown 20, segment 9, product 1). For real JVs and part-owned companies (Grupo Aeromexico, WestJet, Air France-KLM, Virgin Atlantic, LATAM, Hanjin KAL, Unifi, Endeavor) it is **35/35**. |
| 3. Unclear airline groupings = unknown (3.18); customer group = customer | unknown `what` adds "or the same name could fit several kinds and nothing says which" | **Not reproduced.** For mainline, regional carrier and MRO (14 rows keyed unknown), Jev says segment on about 10 (mainline 5/5 segment) and customer or channel on the rest. Cargo, passenger and loyalty program stay product, except 8 rows read as customer. |

**Slice kind after the rescore:** 236/291 (81.1%), unchanged.
- Excluding the 30 own-entity rows: 236/261 (90.4%).
- Also excluding the 14 mainline/regional/MRO rows: **235/247 (95.1%)**. By kind: refinery 27/27, airline 5/5, geography 71/73, JV/part-owned 35/35, customer 8/8.

**What the rescore means**
- **Ruling 1 was right, and Jev follows it.**
- **Ruling 2 was probably wrong.** "American had $23.6 billion in long-term debt" is the filer (or co-registrant) talking about itself, which rules 2.14 and 3.15 treat as a whole-company fact with **no slice**. The earlier labeling invented an entity slice for the filer's own name.
- **Ruling 3 was not supported.** "Mainline" and "regional carriers" fit the 3.13 test "the company operates as it", so segment is the more natural reading.
- The revised suggestions are in §3.3.

**Caveats:** silver labels for baseline and slices; Claude's labels for horizon (a wording-based reading, since the rule gives no thresholds) and for the surprise-derived baselines; mostly two airlines; only 49 horizon items.

### 6.5 Claim checker (idea H)

**Setup**
- One Choice: `supports` / `contradicts` / `says_nothing` (the docs recipe `citation_check`).
- Jev sees only the claim and the source text (rule 8.2). A claim passes only on `supports`; anything else is a flag.
- The claim wording is rule text: fact type from 1.5 and table 2a, state from 3.6.

**Items**, frozen before any call:
- Every decided fact-type fact (411) and 299 metric-state facts, each as a right claim plus a wrong copy whose label was swapped by a hash of the id: 1,420 items, hash `acd17953e7f73adc`.
- Plus the 32 real mistakes that round 1's prompt (QC4) and V6 made on decided facts: hash `b9be454654fab3a5`.
- The v2 items use hash `c9be37d46f11ac99`.

**Run:** two runs, about $0.19 in all. Every state miss and every fact-type miss on the DEV set was read.

| Test | Wrong claims flagged (want high) | Right claims wrongly flagged (want low) |
|---|---|---|
| State, planted | 290/299 (97.0%); the 9 escapes are all arguable or rule-gap cases | 28/299 (9.4%): 9 sign-convention gap, 3 "persists" wording, 5 Jev wrong (read "net loss" or "outflows" as a direction), 11 doubtful labels |
| Fact type, planted, v1 wording | 328/411 (79.8%) | 3/411 |
| Fact type, planted, v2 wording, fresh sets only | 263/295 (89.2%) | 2/295 (two doubtful items) |
| Real Jev mistakes (32) | 2/32 (6%) | — |
| Comparator: re-classify with V6 and compare with the claimed type (fresh sets) | 293/295 (99.3%) | 7/295 (2.4%) |

**Findings**
- **Checking one label is weaker than choosing among labels.** "This is a metric" passes whenever its definition roughly fits (a discrete event with an amount looks like "a number"), while a four-way Choice forces a pick. For a closed list, re-classify and compare, at the cost of more false flags.
- **v2 wording** (written after reading v1's DEV misses only) adds two rule sentences: the persistence test (1.5) and forecast words (1.6).
  - On fresh sets, guidance claimed as metric went from 0/23 to 22/23 flagged.
  - Action_event claimed as metric stayed at 0/11.
- **Jev does not catch Jev's own kind of mistake.** 30 of the 32 real mistakes passed. Re-classifying with V6 caught all 22 made only by round 1's prompt, and none of the 10 V6 made. It helps against a different or weaker reader; how much it helps for the real reader is unmeasured.
- **The checker inherits every rule gap.**
  - Most state false flags come from the open sign question (a narrowing loss, cash "used", a tax benefit).
  - Most fact-type escapes rest on reviewer rulings (declared dividend, pay raise, ongoing agreement, projected tax rate).
- **Not tested:**
  - real state mistakes;
  - unit, baseline, horizon and slice claims;
  - a different reader's real errors (needs Phase 6 approval for a reader model).
- No bar or auto-pass is proposed (8.5, 8.6).

**Caveats:** the state items come from 3 filings of 2 airlines (American, Delta), so industry coverage is untested; v2 wording was written after reading v1's DEV misses; keys are silver; the 32 real mistakes come from Jev itself; there is no real-mistake test for state claims.

**Prompt text:** Appendix A.10. **Files:** `claim_prompts.py` (`CHECK`, `TYPE_DEF`, `TYPE_DEF_V2`, `STATE_DEF`), `build_claims.py`, `build_real.py`, `run_claims.py`, `score_claims.py`, `build_claims_v2.py`, `compare_claims.py`, `compare_reclassify.py`. Results: `results_claims*.json`, `results_real_reader.json`.

## 7. Fact-type prompt versions

**Where the texts are:**
- `JEV scripts/variants.py`: V0–V6, dict `VARS`;
- `V6.json`: V6 exactly as sent (one Choice named `fact_type`, sent with the state in §5.3), also Appendix A.1;
- `QC4.json`: V0, round 1's final;
- `old_prompts.py`: the first prompts.

Each version = the one before, plus the change listed. **Rule status:**
- **verbatim:** the owner's locked wording (1.5, 1.7, 7.7);
- **interpretation:** new wording that no rule contradicts;
- **conflicts:** contradicts a rule's literal text.

Every clause beyond the locked wording needs owner approval (rule 1.9).

| Version | Change | Why | Evidence | Rule status |
|---|---|---|---|---|
| v1 (first prompt) | One Choice. The question held a yes/no persistence test ("Yes means metric; no means action_event"); options = the four locked 1.5 definitions (guidance included "Outlook verbs (expect, anticipate, target, plan to) make it guidance, never a metric state") | Copy the rules as written | 93/104; guidance 20/30 (forecast table rows called metric) | verbatim |
| v1-steps | Three questions: a surprise-kind Choice, a Noul "forward-looking?", a Noul "standing level? (ignoring forecast wording)"; code applied the rules' order | Explicit steps | 90/104; action 25/34 (announced future decisions called guidance). Rejected. | verbatim |
| v2 (input only) | 400 characters of flattened text before the quote | Give context | No gain (93 / 90) | n/a |
| v3 | Question: "Which kind of fact does `quote` state?". Persistence test folded into the metric and action_event definitions. Added a `read` note and an `order` sentence (surprise, then guidance even with a number or table row, then metric or action_event); every option got `what` (locked wording) + `not_for`; guidance: "A table row counts when its table or section is an outlook, guidance, forecast or estimate." Steps variant rebuilt as five one-rule Noul questions. | v1 omitted "forecast framing overrides persistence" and put a yes/no test inside a 4-option Choice | 103/104; blind guidance 35/35. Steps 99/104, worse. | order and `not_for` restate 1.5; table-row clause = interpretation |
| **C4 = V0** (round 1 final) | Metric: "A figure that a company reports for each period (revenue, an expense, income, a cash flow, a balance) is such a variable, even when the sentence describes it with a verb like recorded, increased or decreased." Action_event `not_for`: "…is not an action_event just because the sentence uses a verb like recorded or increased." | Reported line items ("recorded an income tax benefit of $94 million", explanations of a cost line's change) were called action_event | Set tuned on: 27/31 → 31/31; untouched set: 35/36 → 36/36 | interpretation |
| V1 | Question asks about the named driver ("…about the driver `driver_name`?") | The rules type a fact per Driver (1.7, 2.31, 7.7) | Redo claims 16→19 of 31 | verbatim in spirit (1.7) |
| V2a | Guidance `what` + "and an assumption the company states for its forecast". Metric: period totals made of transactions; methods/arrangements in force; standing per-unit levels. Action: incidents even with a stated effect; one-time decisions to start/change/suspend a policy. Action `not_for`: continuing conditions or measured severity are metrics. `read`: the driver name tells which fact is meant when two drivers cover one topic. | Encode the first reviewer's rulings 1, 2, 3, 5, 7 and rules 1.7, 7.7 | 19→24 of 31; other items 256→255; less stable (2 answers differed between identical runs) | per-unit and one-time-decision sentences verbatim (7.7); the rest interpretation |
| V2b (superseded) | `order`: "a forecast of a measured quantity or condition is guidance" (was "a statement of the company's own forward outlook"). Guidance rewritten, removing "Outlook verbs such as expect, anticipate, target and plan to make a statement guidance": "expect, anticipate, target, plan and will do not decide the type by themselves"; `not_for` + announced, committed or scheduled actions; action + "An announced, committed or scheduled action stays an action_event even when it happens later." | The first reviewer's ruling 4 | 24/31, stable; 344/350 vs 338/350 for C4; no difference on fresh data | **conflicts with 1.6** |
| V3 (rejected) | Guidance: a clause inside a forecast sentence belongs to the forecast; amounts owed under a contract = metric | The two remaining real errors | Fixed one, broke another | interpretation |
| V4 | `read` rewritten: judge the specific claim, not its verb, number or date; the name alone never decides (replaced the 1.7 name sentence). Metric: a change in a level (pay increase) even with an effective date; a rate used in the company's current method ("projected" alone isn't a forecast); in a sentence with a per-unit amount and its decision, the amount is a metric. Action: an ongoing negotiation or implementation; a milestone (delivery, entry into service), while a count of what exists now is a metric. | The second reviewer's rulings | 395/410; newly ruled 11/17; split dividend 4/8; H6 38/39 | interpretation |
| V5 | "The company's own" restored in `order`, the guidance `what`, and the guidance `not_for` ("a forecast made by someone other than the company") | V2b and V4 had dropped it by mistake | 391–394/410; H6 39/39 | verbatim (1.5) |
| **V6** (recommended, not approved) | `read` + "When two drivers cover one topic, one named for a per-unit amount and one for the decision or event, a quote that states the amount is a metric for the first, and a quote that states the decision is an action_event for the second." | V4 and V5 lost the rule-1.7 disambiguation (split dividend amounts 4/8) | 399–400/410; split dividends 8/8; newly ruled 13–14/17; H6 39/39 | verbatim in spirit (1.7, 7.7) |

- **Never changed:** the four locked definitions, and the whole surprise option (verbatim 1.5).
- **Diagnostic, not a prompt:** V2b with the driver name hidden scored 94.2% vs 96.4% (§6.1).

## 8. Rules vs Jev

This covers 220 of the 221 rules; rule 5.8 is plain code with no Jev role. It is Claude's judgment, not measured. Per-rule map: `JEV scripts/rules_vs_jev.json` / `.md` (`classify.py`).

| Bucket | Rules | Share |
|---|---|---|
| A: Jev makes the call | 48 | 22% |
| B: Jev judges part, code does the rest | 29 | 13% |
| C: code only | 86 | 39% |
| D: policy, off-for-now, open, constraints | 55 | 25% |
| E: needs a writer (2.24 naming text, 4.7 `value_text`) | 2 | 1% |

**Jev fits 77 of the 79 rules that need a judgment about meaning.**
- **A, tier 1 (proven):** 1.5 1.6 2.29 2.30 7.7.
- **A, tier 2 (same shape, expect high):** 2.23 2.3 2.11 2.12 2.13 2.14 2.17 2.18 2.20 2.33 1.11 3.40 3.47 3.13 3.14 3.15 3.16 3.21 3.6 3.8 3.33 3.50 3.52 6.4 7.8 4.5 4.6 4.9 4.19 4.1 4.2 4.3 4.16.
- **A, tier 3 (harder, measure first):** 6.13 6.14 2.26 2.32 2.40 2.47 6.1 6.5 4.11 A2.3.
- **B, tier 2:** 2.6 2.8 2.9 2.10 2.15 2.16 1.13 3.36 3.37 3.39 3.18 3.25 3.26 3.28 3.34 3.48 3.49 9.1 4.4 4.8 4.18 4.21 8.16.
- **B, tier 3:** 2.4 2.43 4.10 4.12 4.15 4.17.

**The 86 code rules**
- About 52 are the machine itself: saving, keys, immutability, views, retries. Jev can't replace them.
- About 26 are exact checks, dates and arithmetic, where Jev is worse.
- About 8 are fixed shortcut lists: 1.8, 2.19, 2.22, 2.27, 2.28, 2.45, 6.3, 6.6.
- Rule 8.6 already bans meaning-based code patterns, so little judging code exists.

**The three options**
1. **Code-heavy**, where Jev only judges: the safest.
2. **Jev-heavy**, where Jev also does exact checks and math: **not recommended.**
   - Errors add up: 5 steps at 99% ≈ 95%, 10 steps ≈ 90%, against a bar of under 1% wrong per fact.
   - The 1,200 requests/min ceiling.
   - Each task needs its own qualification (8.13).
   - It breaks rule 8.1.
3. **Mixed (recommended):** Jev decides meaning and reads pieces out (for example date parts, as a Choice); code compares, calculates and saves. Suggested ground rule: "AI decides meaning; code decides exactness." **Not yet decided by the owner.**

## 9. Tasks and ideas (untested unless marked)

### 9.1 Candidate Jev tasks
| # | Task | Rules | Status / ideas |
|---|---|---|---|
| 1 | Fact type | 1.5–1.9 | Done (§6.1) |
| 2 | Fact card: one request asks every type's questions; code reads the matching branch | 3.6, 3.8, 3.52, 4.1–4.3, 4.9, 3.33, 3.50, 3.47, 3.40 | Tested: state, unit, span, baseline, horizon, slice kind (§6.3, §6.4). Untested: who said it, growth basis beyond §6.3, value vs change. Idea M |
| 3 | Claim checker before saving: does the quote support this state, unit, sign, period, slice? | 1.11, 1.13, 8.17 | H (tested, §6.5), N |
| 4 | Name inspector: checks, never invents; also over the 1,282 catalog names | 2.3, 2.6–2.18 | Q |
| 5 | Slice sorter; one-time sorting of XBRL axes by their members | 3.13–3.15, 3.18; 3.16, 3.21 | Slice kind tested (§6.4) |
| 6 | Identity judge: five yes/no per candidate, family gate, Choice among K candidates + "none" (K + none ≤ 255). Highest stakes; test last | 2.4, 2.26, 2.32, 2.40, 2.43, 2.47 | B, C, L, Z |
| 7 | XBRL line-item matcher | 6.1, 6.4, 6.5 | C |
| 8 | Forecast bookkeeping: corrections, withdrawal scope | 4.5, 4.18, 4.19, 4.21 | P |
| 9 | Missed-fact sweep: tag every sentence and table row, compare with the reader's output. Whole corpus: about 22–58M calls, 13–34 days at 1,200 requests/min, $0.5–3K | 8.14, ⚠ under 4.17 | D |
| 10 | Rule-gap finder: low confidence flags ambiguous rules | — | T |
| 11 | Second grader for the launch test (qualify it first) | 8.17, 8.18 | X |
| 12 | Price-move verdicts: Choice long/short + Score weight + confidence; separately approved source; multi-step, least likely to reach 99% | A2.3 | F |
| 13 | Rename detection | 6.13, 6.14 | — |
| 14 | Update spotting | 8.16 | P |

### 9.2 Idea bank
- **Sources:** the Jev docs (all patterns and cookbooks, read 2026-09-29) and Videos 1–2 (§0). Re-read the docs page before proposing a test.
- **Verdict:** each idea is checked against all 221 rules (§10). Rules can bend if the owner names a better goal.

| ID | Idea | Docs page | Rules it serves | Verdict and catch |
|---|---|---|---|---|
| A | Code finds candidate numbers; Jev picks the value, change or baseline and reads shape and sign; code copies the pick | `pre_parsed_value_extraction_cookbook` | 3.50, 4.6, 3.48, 3.34, 1.13, 1.17 | **Fits.** Jev can't pick a number code missed; number words need a frozen list (8.6); spans must lie inside the quote (3.29) |
| B | Broad to narrow: family, sub-group, driver (Choice ≤ 255 options) | `hierarchical_classification`, `classification_using_confidence` | Identity 2.40, 2.43 | **Needs OK.** Proposer only (8.2). If unsure, keep the fact's own name (1.12, 2.43), never join the parent family |
| C | Shortlist the top 3 (code or Jev), then one yes/no re-check each | `skill_suggestion`, `entity_alignment`, `rerank_typesafe` | Identity; XBRL 6.1, 6.5 | **Needs OK.** Paid embeddings need approval (8.12), BM25 is free; the approver never sees scores (8.2); a refusal is final (2.47) |
| D | Find the lines that state a driver; per-line yes/no | `semantic_find` | Missed-fact check (⚠ under 4.17, 8.14) | **Needs OK.** Before saving only (6.20); a flagged event needs an outcome rule (8.14, 8.15) |
| E | Rebuild headings from flat text | `autoformat` | Flat 8-K text | **Conflicts** with 1.17 (8-K tables: original only); can't rebuild tables anyway. Low value |
| F | Text to numeric features that predict returns | `autoresearch_feature_discovery` | Trading side (1.3, 1.4) | **Needs OK, outside the rules:** A2.1, A2.5, 1.14 (no returns shown to producers; walk forward), 9.5 |
| G | Jev reads date parts; code does the calendar math | `date_extraction_cookbook` | Periods 3.36–3.47 | **Fits.** The docs' relative dates don't occur here; ours are fiscal wording |
| H | Claim checker: code checks the quote exists; Jev says supports / contradicts / says nothing | `citation_check` | 1.11, 1.13, 8.17 (wrong = unsupported by its own source) | **Tested (§6.5).** No auto-pass (8.5); qualify first (8.13); the checker sees only proposal and evidence (8.2) |
| I | Screen text before the big model reads it | `classifying_rag_passages`; Video 2 | — | **Conflicts** with 8.10, 1.14, 8.14. After the reader only |
| J | Confidence lets a fact pass without review | `confidence-routing`; Video 1 | — | **Conflicts** with 8.5 |
| K | Design method: list the actions, write each trigger as a question, type follows the action, bar from the cost of a wrong answer | Video 1 | Designing any new task | **Fits** (8.4) |
| L | Over 255 options: chunks with a "none" each, top 5 per chunk, final pick, re-check | Owner idea; `semantic_find` windows | Identity | **Needs OK.** Measure top-5 recall; the whole catalog must be searched (2.43); 3 requests |
| M | Fact-card upgrades: "is this field stated?" per optional field; fact confidence = weakest field; currency Choice; "condition attached?" | `function_calling` | 3.30, 3.37, 3.49, 4.7, 4.8, 9.1 | **Fits** |
| N | Cheap reader; Jev asks per field "unsupported by the source?"; flagged facts go to a stronger model | `sde_cascade` | With H | **Allowed (owner).** S4 wording still to align; Phase 6 limits apply; an identity refusal is never escalated (2.47) |
| O | Code splits the source into sentences and rows; Jev picks the one that states the fact; code copies it | `pre_parsed_value_extraction_cookbook` | Quote check, with H | **Fits as a check.** Never repair or swap a quote (8.8); Jev is not the reader (8.10) |
| P | Fact-pair relation: same, update, correction or contradiction | Use-case map; `citation_check` | 4.5, 4.18–4.21; update spotting 8.16 | **Needs OK, narrow:** 3.7 (only guidance looks at earlier facts), 6.20 |
| Q | One yes/no per rule, also for the 2.20 and 2.23 conditions | Use-case map ("semantic code linting") | Names 2.3, 2.6–2.18, 2.20, 2.23 | **Fits.** Criteria = verbatim rule text (1.9, 2.21, 2.44) |
| R | Boilerplate or other-party statement detector | `llm_guardrails` | 2.33, 1.11, 3.8, 4.9, 9.2 | **Fits.** Ends as a skip with a stated reason (8.14) |
| S | Mixed-quote detector (does the quote state more than one fact?); also generic vs specific "results beat" (4.15) | Smart-home demo; Noul page | 4.1, 4.14–4.16, ⚠ under 4.17 | **Fits the rules, but round 2's detector failed** (broad version flags 107 of 288; narrow version 47 of 286 false flags, §6.1), so the reader splits. What works: the comparison-kind Choice for surprises, 64/65 (§6.2) |
| T | Better hold signals: top probability or top-2 margin instead of confidence | `confidence`, `consistency_choice` | 8.5, 8.17 | **Fits as measurement.** Bars later; needs raw probabilities saved |
| U | Stability check: repeat with a fresh noise field | `consistency_noul_cookbook` | 2.46, 5.4 | **Test-only** (8.12: never repeat a valid answer to get a different result) |
| V | Review order: Score "how much would a wrong fact matter", combined with confidence | `composite-scoring` | — | **Setup-only** (8.3); weights need a frozen decision (8.6) |
| W | Difficulty router: one Score picks which model reads an event | `intent-routing`; Video 2 | Phase 6 | **Needs OK.** 8.12 (no switching providers), 8.13 (qualified per input kind); assumes a cheap reader loses nothing (unproven ⚠) |
| X | Label accelerator: Jev pre-labels answer keys; people review low-confidence items and a sample | Use-case map | Keys; second grader (8.17) | **Setup-only.** Qualify graders first; a key made with Jev can't test Jev |
| Y | Qualifier check: does the quote hold a modifier the tags miss? | From the rules | 3.25, 3.26 | **Fits** |
| Z | Veto-only merge checker: the five identity yes/no (2.40); any "no" = keep separate | From the rules | 2.40, 1.12, ⚠ one vendor | **Fits.** More near-duplicates; qualify first (8.13) |

### 9.3 Combinations, checks and first tests

**Combinations**
1. Fact card = fan-out + M + T.
2. Identity funnel = code shortlist, tree (B), chunks (L), top-3 re-check (C), veto (Z); "none" = keep separate.
3. Select, don't write: code finds candidates (A, G, O), Jev picks, code copies.
4. Two-sided audit: missed facts (D) + wrong facts (H, N) on the same events, before saving or in the launch test.
5. Pre-write gate: H + R + Q + Y in one request (S left out: its detector failed, §6.1). A flag means skip or escalate, never a write.
6. Compound quote: the reader splits (Jev's detector failed, §6.1), then each half is judged.
7. Trading side: F + price-move verdicts (task 12).

Already in use:
- fan-out;
- a "none" option;
- Jev as the different-vendor checker (8.2);
- tags that audit the reader and never feed it (1.14).

Mixed probes (one question asked as yes/no and as Choice; disagreement = hold) may clash with S4's "no votes".

**Cost and speed checks to run:**
- Is a repeated identical options list billed less? The docs mention prefix caching but give no cached price.
- Does adding questions to a request change the answers? The docs say it does not.
- The Python SDK has an async client and retries.

**Claims to verify on our data:** "0.8 means right 8 times in 10" (Video 1); "42,000x cheaper" (Video 1); "available on OpenRouter" (Video 1; not in the docs). Every docs threshold is an illustration.

**Suggested first tests** (each costs cents):
1. H against a different reader's real errors (needs Phase 6 approval for a reader model).
2. T: a confidence-vs-accuracy table per task.
3. A and O on facts with known values and quotes.
4. The identity funnel (B, C, L): top-5 recall on drivers with known answers.
5. M, the weakest-link confidence.
6. U, stability.

**Docs**
- **Read:** 4 patterns, 18 cookbooks, the use-case map, build guide, state, Choice, Noul, Score, advanced, confidence, models, API limits, the smart-home demo, coding-agents.
- **Not read:** Quick Start, AI Primer, System One page, Agent Skill, Legal, SDK pages.

## 10. Constraints from the rules
1. **8.12, 8.13:** AI calls are subscription-only, but Jev is pay-per-use.
   - The owner approved the cost on 2026-09-29 (scope not stated; treat it as tests).
   - Jev is not in the Phase 6 pool.
   - Each task, prompt, configuration and kind of input is qualified separately; the fact-type result doesn't transfer.
2. **8.5, 8.6:** confidence is never permission to write or merge. Any cutoff needs a frozen owner decision (deferred). Use confidence only to hold, skip or route.
3. **8.3, no person at runtime:** the docs' "send to a person" has no home here.
   - An unsure answer goes to a stronger model (allowed) or ends as a skip or hold (8.14).
   - A hold retries only on a checkable trigger (8.15); low confidence alone is not one.
4. **S4 vs escalation:** S4 says "no cascades, votes or fallbacks", but the owner allowed escalation to a generative model; S4's wording is not yet updated.
   - Phase 6 limits escalation to a measured failing group, on ambiguity, invalid output, a verifier conflict or `no_proven_match`, and only to an approved model.
5. **8.2:** a checker sees the proposal, its source evidence and context only; never scores, earlier verdicts or the proposer's arguments.
6. **The reader:**
   - 8.10: it sees the whole event;
   - 1.14: no catalog names before it proposes;
   - 8.8: it never repairs or swaps a quote;
   - 1.17: 8-K tables are original only.
   - Jev (64k window, non-generative) can't be the reader; it works after the reader.
7. **6.20:** no audit or repair after saving; sweeps run before saving or in the launch test.
8. **3.7:** only guidance looks at earlier facts.
9. **A2.1, A2.5, 1.14:** price-move judgments come only from a separately approved source; realized returns are never shown.
10. **Identity:**
    - 2.41: counts never decide;
    - 2.43: the whole catalog is searched, no company or industry filter;
    - 2.45 and 1.12 also apply;
    - 2.47: a refusal is final.
11. **Wording (1.9, 2.21, 2.44):** no added clause or sector example without approval; keep one verbatim copy. V6's extra clauses need approval (§7).
12. **8.17:** "under 1% wrong at 95% confidence" needs about 300 graded facts.

## 11. Where things are
- **Data:**
  - labels: `.claude/plans/Drivers/experiments/runs/kf-*`;
  - source text: `.claude/plans/Drivers/experiments/fixtures/events/*.json`.
  - Neo4j reads need the repo venv, `/home/faisal/EventMarketDB/venv/bin/python3`; the system python has no `neo4j` driver and no pip.
- **`DriversFinal/JEV scripts/`** (start with its `README.md`, which gives the run order per test):
  - the input builder, every prompt version, and the build/run/score scripts;
  - the frozen labels and inputs, with their hashes;
  - the per-rule fit map;
  - the claim-checker results.
  - Not saved (regenerate for cents): `h1_raw.json` (`pull_h1.py`, needs Neo4j) and the other `results_*.json` (rerun that test's `run_*.py`). The original working copy in `/tmp` is gone.
- **Pre-reorganization copy of this file:** `~/.claude/projects/-home-faisal-EventMarketDB/backups/JEV.before-reorg-2026-09-29.md`. Git commit `424d2e5af` has an older draft.

## Appendix A. Prompts, verbatim

All are identical to the files named (checked by script, 2026-09-29). Each is sent together with the state in §5.3.

<details>
<summary>A.1 Fact type, V6 (recommended; not owner-approved) — <code>V6.json</code></summary>

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

</details>

<details>
<summary>A.2 Surprise comparison kind (S2) — <code>surprise_prompts.py</code> <code>S2</code></summary>

```json
{"comparison": {"type": "choice", "instructions": {"question": "Which comparison does `quote` make about the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. Decide whether the value is a reported result or a forecast from what the quote says, not from whether the period has ended."}, "criteria": {"actual_vs_consensus": {"what": "A result the company has reported, compared with what analysts, the Street or the market expected (the consensus or estimate).", "not_for": "A comparison with last year or last quarter, or with the company's own forecast."}, "actual_vs_guidance": {"what": "A result the company has reported, compared with the company's own earlier forecast, guidance, outlook or target range.", "not_for": "A comparison with analysts' expectations, or with last year or last quarter."}, "guidance_vs_consensus": {"what": "A forecast or outlook the company gives for a future period, compared with what analysts, the Street or the market expected.", "not_for": "A new forecast compared with the company's own earlier forecast."}, "none": {"what": "No company value is compared with an outside expectation or with the company's own earlier forecast. This includes a comparison with last year or last quarter, a new forecast compared with the company's own earlier forecast, a forecast or result with no comparison, and a statement that only mentions consensus or expectations.", "not_for": "Any of the three comparisons above."}}}}
```

</details>

<details>
<summary>A.3 Surprise state (S3) — <code>surprise_prompts.py</code> <code>S3</code></summary>

```json
{"state": {"type": "choice", "instructions": {"question": "Is the company's value in `quote` a beat, in line, or a miss against the expectation it is compared with, for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. Judge the whole phrase, including negation, direction and scope. The words above, below, exceeded and ahead of do not mean good or bad on their own, and a higher number is not always better."}, "criteria": {"beat": {"what": "The value is better than the expectation, judged by meaning: the source says beat, better than expected, or gives other words that frame the result as good.", "not_for": "A value that is only higher or lower with no sign that it is good."}, "in_line": {"what": "The value equals the expectation, sits inside a stated expectation range or on its edge, or the source says in line, and no words say good or bad.", "not_for": "A value clearly outside the range that the source frames as good or bad."}, "missed": {"what": "The value is worse than the expectation, judged by meaning: the source says miss, worse than expected, or gives other words that frame the result as bad.", "not_for": "A value that is only higher or lower with no sign that it is bad."}, "unknown": {"what": "The value is outside the expectation but the source gives no words saying good or bad, and a higher number is not clearly better for this driver (for example costs, capital spending, research spending, inventory, hiring or cash burn), or the comparison is unclear.", "not_for": "A comparison the source states as a beat, a miss or in line."}}}}
```

</details>

<details>
<summary>A.4 Metric state — <code>card_prompts.py</code> <code>STATE</code></summary>

```json
{"state": {"type": "choice", "instructions": {"question": "Which state does `quote` give for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. Apply these in order and take the first that fits: a stated direction is increased or decreased; the same driver moving differently across parts is mixed; stated flat is unchanged; ongoing with no direction is persists; a bare value is reported, but a value that also states the prior value is increased or decreased; otherwise unknown. Good or bad news never decides the state."}, "criteria": {"increased": {"what": "The quote states an increase, or gives a value together with a lower prior value. A loss that narrows counts as an increase.", "not_for": "A bare value with no direction and no prior value."}, "decreased": {"what": "The quote states a decrease, or gives a value together with a higher prior value. A loss that widens counts as a decrease.", "not_for": "A bare value with no direction and no prior value."}, "mixed": {"what": "The same driver moves in different directions in different parts of the quote.", "not_for": "A single direction."}, "unchanged": {"what": "The quote states that the driver is flat or unchanged.", "not_for": "A small increase or decrease."}, "persists": {"what": "The quote says the driver is ongoing or continues, with no direction and no value.", "not_for": "A bare value, or a stated direction."}, "reported": {"what": "The quote gives a bare value with no stated direction and no prior value.", "not_for": "A value stated together with its prior value, or with a direction."}, "unknown": {"what": "None of the other states fits.", "not_for": "Anything the other states describe."}}}}
```

</details>

<details>
<summary>A.5 Unit of the value — <code>card_prompts.py</code> <code>UNIT_LEVEL</code> (the change version <code>UNIT_CHANGE</code> differs only in its question: "What is the unit of the stated change (the increase, decrease or difference) in `quote` for the driver `driver_name`?")</summary>

```json
{"unit": {"type": "choice", "instructions": {"question": "What is the unit of the stated value in `quote` for the driver `driver_name`, ignoring any change or comparison amount?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title."}, "criteria": {"usd": {"what": "Money per unit: a price, a per-share amount or a per-barrel amount, in US dollars.", "not_for": "A money total."}, "m_usd": {"what": "A money total in US dollars (millions or billions of dollars).", "not_for": "Money per unit."}, "percent": {"what": "A percentage that is itself a level, such as a margin, a rate or a share of a total.", "not_for": "Growth against an earlier period, or a difference in percentage points."}, "percent_yoy": {"what": "Growth compared with a year earlier (year over year, comparable or annual growth). Growth is never plain percent.", "not_for": "Growth against the previous quarter, or a difference in points."}, "percent_sequential": {"what": "Growth compared with the immediately previous comparable period, for a period shorter than a year.", "not_for": "Growth against a year earlier."}, "percent_points": {"what": "A difference between two percentages, in percentage points. Points win over year-over-year or sequential wording.", "not_for": "Growth in percent."}, "basis_points": {"what": "A difference or move in basis points. Basis points win over year-over-year or sequential wording.", "not_for": "Growth in percent."}, "count": {"what": "A number of things, such as shares, stores, aircraft, employees or customers.", "not_for": "Money or a percentage."}, "x": {"what": "A multiple, such as 2.5x.", "not_for": "A percentage."}, "unknown": {"what": "The unit cannot be settled from the quote, for example money in a currency other than US dollars, growth over a vague horizon, or up or down X% on a metric that is itself a percentage with no points, basis points or \"to X%\".", "not_for": "A unit the quote states clearly."}}}}
```

</details>

<details>
<summary>A.6 Span vs single moment — <code>card_prompts.py</code> <code>TIMETYPE</code></summary>

```json
{"time_type": {"type": "choice", "instructions": {"question": "Does the value in `quote` for the driver `driver_name` cover a span of time or a single moment?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. Decide from the meaning of the value, never from a default."}, "criteria": {"duration": {"what": "The value covers a span of time, such as a quarter, a year or a year to date, for example revenue, expenses or cash flow for the period.", "not_for": "A balance or count measured as of a date."}, "instant": {"what": "The value is measured at a single moment, such as a balance, a count or a rate as of a date.", "not_for": "An amount earned or spent over a period."}}}}
```

</details>

<details>
<summary>A.7 Comparison baseline — <code>more_prompts.py</code> <code>BASELINE</code></summary>

```json
{"baseline": {"type": "choice", "instructions": {"question": "What headline comparison does `quote` make for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. If the quote makes several comparisons, take the headline one."}, "criteria": {"consensus": {"what": "The value is compared with what analysts, the Street or the market expected.", "not_for": "The company's own forecast."}, "prior_year": {"what": "The value is compared with the same period a year earlier (year over year, versus last year, the year-ago period). If the quote also compares with the previous quarter, the year-ago comparison wins.", "not_for": "A comparison with the previous quarter only."}, "sequential_period": {"what": "The value is compared with the immediately previous comparable period, such as the previous quarter or month, and not with a year earlier.", "not_for": "A comparison with a year earlier."}, "previous_guidance": {"what": "The value is compared with the company's own earlier guidance, forecast, outlook or target.", "not_for": "Analysts' expectations."}, "none": {"what": "The quote makes no comparison, or compares with something else: peers, a fixed anchor year such as 2019, or a streak.", "not_for": "A comparison with a year earlier, the previous period, analysts or the company's own guidance."}}}}
```

</details>

<details>
<summary>A.8 Horizon, as first tested — <code>more_prompts.py</code> <code>HORIZON</code> ("over time" sits under long_term; the post-ruling <code>HORIZON2</code> is described in §6.4)</summary>

```json
{"horizon": {"type": "choice", "instructions": {"question": "Which time horizon does the forecast or goal in `quote` refer to, for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title."}, "criteria": {"stated_window": {"what": "The quote names a real window: a fiscal year, a quarter, a half, a month, a dated range or a year such as by 2030.", "not_for": "A horizon described only in words such as long term or going forward."}, "short_term": {"what": "The quote looks ahead to the near term or the coming months, in words, with no dates.", "not_for": "A dated window."}, "medium_term": {"what": "The quote looks ahead to the medium term or the next few years, in words, with no dates.", "not_for": "A dated window."}, "long_term": {"what": "The quote looks ahead to the long term, a long-range plan or over time, in words, with no dates.", "not_for": "A dated window."}, "undefined": {"what": "The quote looks ahead to a horizon that is implied but not defined, such as going forward, with no dates.", "not_for": "A dated window, or a horizon named as short, medium or long term."}}}}
```

</details>

<details>
<summary>A.9 Slice kind, as first tested — <code>more_prompts.py</code> <code>SLICE</code> (the state also carries a <code>slice_value</code> field; the post-ruling <code>SLICE2</code> is described in §6.4)</summary>

```json
{"slice_kind": {"type": "choice", "instructions": {"question": "What kind of company part is `slice_value` in `quote`, for the driver `driver_name`?", "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them to see what `quote` refers to, including any heading or table title. A brand is not a kind; the way the quote uses it decides."}, "criteria": {"segment": {"what": "A part the company operates as: a reporting segment or division.", "not_for": "Something the company sells, or a place."}, "product": {"what": "Something the company sells: a product, a service or a program.", "not_for": "A reporting segment, or a place."}, "geography": {"what": "A place the company operates in: a country, a region or a destination.", "not_for": "A product or a segment."}, "customer": {"what": "A group the company sells to.", "not_for": "A product or a place."}, "channel": {"what": "How the company sells or runs something, for example franchised or through partners.", "not_for": "A product or a customer group."}, "entity_ownership": {"what": "A stake the company owns. Joint ventures and part-owned companies are the strongest cases; other entity rows are provisional.", "not_for": "A product or a segment."}, "unknown": {"what": "The kind cannot be told from the quote.", "not_for": "A kind the quote makes clear."}}}}
```

</details>

<details>
<summary>A.10 Claim checker (§6.5) — <code>claim_prompts.py</code> <code>CHECK</code>, <code>TYPE_DEF</code>, <code>TYPE_DEF_V2</code>, <code>STATE_DEF</code> (the claim is sent as a <code>claim</code> field of the state, next to the fields in §5.3)</summary>

Question, one Choice named `verdict`:

```json
{
 "verdict": {
  "type": "choice",
  "instructions": {
   "question": "Does `quote` support `claim`?",
   "read": "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them only to see what `quote` refers to, including any heading or table title."
  },
  "criteria": {
   "supports": {
    "what": "`quote` states the claim or directly implies that it is true."
   },
   "contradicts": {
    "what": "`quote` states the opposite of the claim or implies that it is false."
   },
   "says_nothing": {
    "what": "`quote` does not address what the claim asserts, either way."
   }
  }
 }
}
```

Fact-type claim, wording v1. Template: `The fact about {name} is {a or an} {type} fact: {definition}.` with these definitions (from 1.5 and the table in 2a):

```json
{
 "metric": "a standing variable readable again over time (a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand), not only a number",
 "guidance": "the company's own forward outlook, target or forecast",
 "surprise": "a company value, delivered (an actual) or promised (a company forecast), compared with an expectation held by another party (analyst consensus or the Street, or for an actual the company's own prior guide)",
 "action_event": "a discrete thing that happened (a decision, transaction, incident, approval or one-off charge)"
}
```

Fact-type claim, wording v2 = v1 plus two sentences that are already rule text (the persistence test in 1.5 and the forecast words in 1.6). Same template, these definitions:

```json
{
 "metric": "a standing variable readable again over time (a number, cost, price, rate, count or ratio, or a qualitative condition such as weather, sentiment, policy in force, labor or brand), not only a number. Test: between two events, is there a standing level you could read again? Yes means metric. Forecast words (expect, anticipate, target, plan to) make a fact guidance, never a metric.",
 "guidance": "the company's own forward outlook, target or forecast. Forecast words (expect, anticipate, target, plan to) make a fact guidance, never a metric.",
 "surprise": "a company value, delivered (an actual) or promised (a company forecast), compared with an expectation held by another party (analyst consensus or the Street, or for an actual the company's own prior guide)",
 "action_event": "a discrete thing that happened (a decision, transaction, incident, approval or one-off charge). Test: between two events, is there a standing level you could read again? No means action_event."
}
```

Metric-state claim (the rows of rule 3.6). `{n}` is the driver name:

```json
{
 "increased": "{n} increased (the quote states a direction: up, or gives a value with a lower prior value).",
 "decreased": "{n} decreased (the quote states a direction: down, or gives a value with a higher prior value).",
 "unchanged": "{n} is unchanged (the quote states it is flat).",
 "persists": "{n} persists (the quote says it is ongoing, with no direction).",
 "reported": "{n} is reported as a bare value (the quote gives a value with no direction and no prior value)."
}
```

</details>
