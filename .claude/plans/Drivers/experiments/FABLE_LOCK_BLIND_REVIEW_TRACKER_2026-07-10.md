# Fable Lock-Blind Review Tracker - 2026-07-10

Purpose: this is the owner's working checklist and Fable's task brief, now expanded (v2, same day) into the self-contained panel-review package the handoff section requested. It is not a design authority and does not replace the source documents or verbatim transcript (`FABLE_LOCK_BLIND_VERDICT_2026-07-10.md`).

## What This Review Is About

The Driver catalog gives reusable names to causes and company-reported metrics so the same cause can be found across companies and time. Each extracted statement or value is stored as a fact and attached to one Driver.

The central safety rule is asymmetric: an unnecessary split is undesirable but can be repaired later; an incorrect merge can permanently mix different meanings. The most serious case is a fact attached to the wrong Driver, because the stored fact id contains the Driver name and the current design never moves that fact. The proposals below therefore have two goals:

1. Prevent incorrect facts, names, or links before they become permanent.
2. Repair safe splits at read time without rewriting stored evidence.

The project also requires no routine human decision-maker in the production loop. A proposal that depends on a person maintaining meanings, approving facts, or resolving normal cases must be identified as conflicting with that requirement.

## Plain-Language Terms

- **Driver:** the reusable cause or metric name, such as `ebitda`, `current_rpo`, or `aws_outage`.
- **Fact:** one stored claim or value extracted from source evidence.
- **fact_scope:** the fact's identity string beyond the Driver name: period + slice + measurement (+ rare quote-hash tie-breaker).
- **ATTACH:** connect a new fact to an existing Driver instead of creating a new Driver.
- **Identity:** the decision that two facts or names describe the same underlying cause or metric.
- **Slice:** the company part a fact describes, such as a business segment, product, geography, customer group, channel, or legal entity.
- **Measurement:** a different lens on the same quantity, such as adjusted, diluted, organic, or constant-currency.
- **Portion qualifier:** a word that changes which part of a quantity is counted, such as current, funded, fee-earning, or to-be-recognized over NTM.
- **SAME_AS:** a reversible link saying two separately stored Driver names mean the same thing.
- **Reconciliation:** safely show separately stored items together when reading, without changing their stored ids.
- **Raw view:** the stored facts exactly as written.
- **Reconciled view:** a labeled read result that applies approved, reversible repairs.
- **XBRL:** structured financial-statement tags. An axis and member describe a company part; a qname is the exact XBRL tag name.
- **PIT:** point in time; only information available by the fact's event time may be used.
- **Judge or grader:** a model that checks a proposed name, attachment, or link.
- **Model-free check (falsifier):** code or structured evidence, such as XBRL, that can catch an error without another model opinion.
- **Key:** the fixed correct-answer set used to score an experiment.
- **`NAME-*`, `FS-*`, `OD-*`, `PIPE-*`, `DU-*`, `UNIT-*`, and `EXP-*`:** references to naming rules, fact-and-slice rules, owner decisions, pipeline rules, fact-contract rules, unit rules, and experiments in the design documents.
- **Kernel section references (`kernel S2`, `S6.1`, `S6.5`, `S6.6`, `S9.2`, `S9.5`, `S9.6`, `S10`, `S11.0`, `S15.0`, `S16`):** sections of `FableAdmissionKernelDesign.md` (v3.4 lock candidate).
- **Hard requirement:** an owner-approved direction that the panel must treat as fixed context while still reporting any contradiction or serious failure it finds.
- **Stress-test proposal:** an unapproved idea the panel must try to break before recommending adoption, rejection, or revision.

**Machinery glossary (needed to execute the decisions below):**

- **The four admission arms:** ATTACH (write the fact onto an existing exact-name Driver), CLAIM (propose a SAME_AS link to a differently-worded Driver - the fact still writes to its own wording node; the SYNCHRONOUS claim trigger ships OFF, while an ASYNC sweep proposes links from day 1 via a code suggester), CREATE (new Driver), SKIP (not a reusable cause). MERGE = the database write-or-update operation on one fact id.
- **Head:** the existing Driver node an ATTACH or link targets. **Frozen anchor:** the head's immutable birth quotes, the judge's fixed reference. **Seed:** the batch-built starting catalog (its links get a third grader).
- **Fact flavors (fact_type):** metric (a standing re-readable level), guidance (forward outlook), surprise (actual vs expectation), action_event (a one-time act such as a buyback or an outage).
- **Slice menu / frozen axis table:** at write time the producer is shown the company's PIT-cut list of known slice values, each pre-classified into a kind by a frozen owner-vetted table of XBRL axes (57 rows).
- **period_scope / series_unit / series key:** period_scope = the horizon word on a fact (quarter, annual, YTD, TTM, long-term...); series_unit = the code-stamped unit-axis tag facts group by; the series key = the full tuple a read groups on (company - driver - fact_type - slice - period - period_scope - measurement - series_unit - time_type).
- **LINK judge / G2 / Refute:** the strong-model checks - G2 admits names, the LINK judge decides SAME_AS pairs, Refute attacks proposed merges. **V14:** the recovery-integrity validator. **RecoveryEvent:** the immutable audit record every recovery emits.
- **GREEN / quality budget / rule-of-three:** GREEN is the pass verdict of the one-shot production go/no-go gate (PIPE-37, defined in `10_BuildPipeline.md`); the quality budget is its permanent-error allowance (0.1%); "0 wrong in n audited" implies a 95% upper bound of <= 3/n (the rule-of-three).
- **WP-* / EXP-* / K-*:** work packages and experiments of the pre-build program (`FableExperimentWorkOrder.md`): EXP-0 grader validation, EXP-2 readers, EXP-3 routing, EXP-5 extraction; K-pairs/K-reader/K-fields/K-route are their sha-locked answer keys.
- **Document short names:** `02` = `02_DriverCatalog.md`, `03` = `03_Slices_FactScope.md`, `05` = `05_Periods.md`, `07` = `07_DriverUpdate.md`, `09` = `09_DriverUpdate_Fields.md`, `10` = `10_BuildPipeline.md`, `12` = `12_TrackB_FactPipeline.md`, `66` = `66_IssuesToBeHandled.md` (its `§0.R` holds owner-decision OD rows). **Note:** `T12.9` is a section of doc `12` (member-anchored read-time grouping), NOT a tracker item - the `T` collision is unfortunate but historical.

## Panel Review Handoff (fulfilled by this package)

A reader who has not seen the prior conversation must be able to understand the current rule, the proposed change, the evidence, both choices' risks, and the decision being requested. Every Tier 1 and Tier 2 proposed-change item below carries nine numbered fields (Rejected Ideas, Honest Limits, and Experiment Effects use the shorter formats the classification rules assign them):

1. **Wording** - the exact proposed text and its target file/section. Text labeled `RECORDED` was previously supplied to the owner and is quoted from `FABLE_LOCK_BLIND_VERDICT_2026-07-10.md`; text labeled `NEW DRAFT` was written for this package and has never been agreed.
2. **Problem** - the concrete problem, example, or evidence that motivated the change.
3. **Why not already handled** - why the current design does not cover it.
4. **Risk if adopted.**
5. **Risk if rejected.**
6. **Interactions** - dependencies and conflicts with other items.
7. **Required changes** - every document, prompt, code, test, key, and experiment change; "none" stated explicitly.
8. **Classification** - `HARD REQUIREMENT` or `STRESS-TEST PROPOSAL`, with reason.
9. **Panel decision requested.**

Classification rules (unchanged from v1):

- `HARD REQUIREMENT`: only the owner-approved core of T1-01, plus T1-03, T1-04, and T1-05.
- T1-01's three exceptions, T1-01a through T1-01c, are not approved and remain separate `STRESS-TEST PROPOSAL` items.
- Every other unapproved proposed change defaults to `STRESS-TEST PROPOSAL`, even where Fable recommends adoption.
- T1-11 is not approved because a maintained idiom table conflicts with the no-human requirement; a no-human replacement design is included below (it answers Q-12) and must itself be stress-tested.
- Rejected ideas are proposed rejections for the panel to confirm, overturn, or modify.
- Honest limits are claims for the panel to challenge, not proposed rules.
- Experiment effects are consequences to verify, not independent design rules.

Do not silently combine, expand, or omit items. Do not edit design, experiment, key, prompt, or code files until the owner reviews the panel result. (This tracker file itself is the one file the handoff instructed Fable to expand.)

## Current-State Snapshot (verified on disk 2026-07-10)

- The design is pre-build: 0 Driver graph nodes exist; the PIPE-37 fitness/honesty gate has never run.
- The experiment program is LIVE: WP-0 bootstrap and the WP-FA corpus are DONE; EXP-1 census + dry-run are DONE (PASS); K-pairs.v1 is sha-LOCKED at v1.3 (Fable-signed 2026-07-09) and EXP-0 has produced three runs. K-reader, K-fields, and K-route keys are still PENDING - all new naming rules can bind to them at zero rework cost.
- A WP-FC-EDITS review baseline file exists (`WP_FC_EDITS_review_baseline_e9127c02.md`); before landing prompt notes, confirm whether the edit batch has already run (determines whether new rule text rides the planned edit or needs a one-block re-sync).
- Authority order: topic docs (`01`-`09`) + `95_Supersession` > `90`/`14` > lock candidates (`FableAdmissionKernelDesign.md`, `XBRLIntegrationDesign.md`) > context packs > this tracker.

**Source conflicts found while assembling this package (reported, not silently resolved):**
- The verdict transcript's Q-01 catalog-size comparison table says portion names are "~10-15% more names in KPI-dense areas" and "~6 of 120 stress names"; the later measured figure (full-inventory grep) is ~55-60 of 3,170 operational names (~1.9%). The measured figure supersedes; the transcript records the earlier estimate.
- The verdict transcript presents T1-11 with "multi-word idioms as explicit entries" (a maintained table); the owner rejected that mechanism. The replacement design in T1-11 below supersedes the transcript's version.
- The "~57% of facts lack member links" figure (used in T2-01/T2-02 motivation) was VERIFIED during package review: `03_Slices_FactScope.md` FS-21 itself states the ~57% figure; the verdict transcript's Tier-2 paragraph repeats it.

---

# Foundations (verified context, not decisions)

## F0 - Overall verdict: keep every architectural pillar; the current design is not ideal

Fifteen review agents independently attempted replacements for each pillar: open-vocabulary cause-only names; variant-anchored storage + reversible SAME_AS edges; propose-first (coin blind, then see candidates); the code-decides-form / LLM-decides-meaning split; the 4-flavor fact_type; deterministic fact ids embedding the Driver name. Every replacement loses on recorded evidence: a closed vocabulary is how design v1 died (82% of valid names rejected); eager merging is how v2 died (string metrics ~99% while judged precision ~29%); surrogate ids break the deterministic producer-free text/XBRL twin dedup (X-XL1 >= 99% id-equality bar) and replace audited reversible SAME_AS with a mutable order-dependent binding. The panel should treat "keep all six pillars" as a strongly evidenced conclusion, and may attack it.

## F1 - The deep finding: a mis-ATTACHed fact is the one physically irreversible error

CLAIM and CREATE write facts to the fact's own wording node (variant-anchored storage) and merge only via reversible SAME_AS edges. Exact-name ATTACH is the single operation that places a fact onto an already-existing node; the fact id embeds the Driver name and facts never move, so a wrong ATTACH can be detected and flagged later but never un-placed. The kernel is internally inconsistent about who confirms it: S2 labels Stage-1 (which decides ATTACH) "the G2 router (ONE cheap call)" and S11.0 lists "route" as cheap-permitted work - yet S11.0's own "Current owner default" paragraph assigns "G2 decisions" to the STRONG-judge tier (Sonnet 5), and its locked law says a cheap tier may never final-confirm an identity-changing decision. The tension is inside one locked document, on its own text. Items T1-06, T1-07, and T1-09 exist to guard exactly this surface. The panel should verify the irreversibility chain itself (id embeds name -> no re-key -> no move) and the S2-vs-S11.0 wording tension before judging those three items.

---

# Tier 1 - Identity Integrity

## T1-01 - FS-06a portion qualifiers stay in the Driver name [HARD REQUIREMENT - owner-approved core]

1. **Wording (RECORDED; two notes).**
   Note under NAME-11 in `02_DriverCatalog.md`:
   > "Portion qualifiers (OD-17): a qualifier naming which portion of the company's own measured quantity is counted - and that is not one of the six slice kinds, not a period window, and not a measurement version - stays in the NAME (`current_rpo`, `fee_earning_aum`, `funded_backlog`). Different portion = different driver, never SAME_AS the bare form. If unclear whether a word is a window or a portion, keep it in the name; never drop it."
   Boundary sentence in `03_Slices_FactScope.md` (FS-25), mirrored in NAME-14:
   > "A measurement word re-expresses the SAME quantity through a different lens; a word that changes WHICH portion is counted is never a measurement token - it belongs in the name (OD-17)."
2. **Problem.** Words like current, fee-earning, funded, to-be-recognized-over-NTM select a sub-population of a quantity (current RPO is only part of all RPO). They are not one of the six slice kinds, not a period, and not a measurement lens - so two honest producers route them differently, or drop them (which silently merges the portion into the total: the forbidden over-merge). Measured scope in the FiscalAI KPI inventory: ~55-60 of 3,170 operational names (~1.9%), collapsing to roughly 15-20 portion Drivers around six base metrics - small by count but head-heavy ("RPO to be Recognized Over NTM" spans 31 companies, the #2 most-shared KPI in the inventory).
3. **Why not already handled.** NAME-11 step 3 ("role unclear -> keep in the name") is the catch-all these words fall through to, but NAME-14's open-ended measurement list and NAME-16's banned-word list can each plausibly claim words like "current"; nothing pins the routing.
4. **Risk if adopted.** More Driver names (over-split-safe); occasional window-vs-portion misreads still land in the name (safe direction by construction).
5. **Risk if rejected.** Producers fork on placement (series split) or drop the qualifier (permanent value-level over-merge into the total series).
6. **Interactions.** Ordering pin with T1-02: this portion test runs FIRST and owns the whole name; NAME-08a then canonicalizes only the bare-metric token inside it ("current portion of capex" -> `current_capex`, never a table entry). Token-subset auto-refusal (kernel S6.1) blocks `current_rpo` SAME_AS `rpo` for free TODAY - note: if T1-10 is adopted, that refusal becomes reconciliation-eligible rather than permanent, and the guarantee then rests on T1-10's portion-pair guard (gold-DIFFERENT stays DIFFERENT), which the panel must verify. Alternative placements: the measurement slot was examined and rejected on the record (Q-01 in the verdict file - four independent kill reasons: default-empty flips the failure direction to over-merge; measurement has zero identity machinery; concept-linking's GAAP-compatible guard would abstain on portion tokens and guidance/surprise inheritance would die; XBRL twin ids could never converge); a seventh slice kind was rejected in this package author's own synthesis (NOT an on-record analysis): portion words have no XBRL axis anchor, so a new kind would take free-text values with none of the menu/table machinery behind the six kinds, and kind lives inside fact ids.
7. **Required changes.** One OD row (OD-17) in `66 §0.R`; the two notes above; PIPE-16 prompt-block re-sync (or free ride on WP-FC-EDITS if not yet run); K-reader/K-fields draft under it; one K-fields trap class (portion word wrongly placed in measurement). No new field, slice kind, validator word list, id change, kernel change, XBRL change; nothing already run is invalidated. No 95_Supersession row (an addition, not a reversal).
8. **Classification.** HARD REQUIREMENT - owner approved the core rule (Q-01/Q-02); the panel treats it as fixed context but must report any contradiction it finds.
9. **Panel decision requested.** None on the core; verify the interaction pins (esp. the T1-02 ordering) and report contradictions.

## T1-01a - Exception (i): explicit all-parts aggregates use the omitted slice [STRESS-TEST PROPOSAL]

1. **Wording.** RECORDED core (verbatim from the verdict file): "explicit all-parts aggregates ('system-wide', 'total company') = the omitted slice." NEW DRAFT clarification sentence for the rule text: "Any stated all-parts-of-the-company aggregate maps to FS-10's existing omitted-slice rule, exactly like FS-10's own enumerated triggers (whole-company / consolidated / total-company)."
2. **Problem.** FS-10 ALREADY maps "whole-company / consolidated / total-company / no stated segment" to the omitted slice - so most explicit aggregates are covered today. The genuine residual is non-enumerated aggregate phrasings, above all "system-wide": it names the aggregate ACROSS operating models (franchised + company-operated), so a producer could misread it as a channel value (`channel:system_wide`) or keep it in the name instead of recognizing it as FS-10's omitted-slice case.
3. **Why not already handled.** FS-10's trigger list is enumerated wording; "system-wide" is not on it and, unlike "total company", reads as if it names parts.
4. **Risk if adopted.** An "aggregate" that is actually a sub-total (e.g. "Total Alumina EBITDA" = total OF a segment) must not match this rule - the wording must scope to all-parts-of-the-company aggregates only, else it over-merges a segment total into the consolidated series.
5. **Risk if rejected.** Same fact stored three ways (omitted slice / channel value / name token) -> series split.
6. **Interactions.** T1-01 (same OD-17 family); FS-10/FS-15 (extends their reading); R-06 (never resolves by dropping a stated qualifier - this rule maps it, not drops it).
7. **Required changes.** One sentence added to the OD-17 note + FS-10 cross-reference; one K-fields fixture. Nothing else.
8. **Classification.** STRESS-TEST PROPOSAL - owner chose to review the three exceptions separately (Q-02).
9. **Panel decision requested.** Approve / reject / rewrite; specifically test the segment-total counterexample in field 4.

## T1-01b - Exception (ii): "Other" and residual buckets are legal company-specific slice values [STRESS-TEST PROPOSAL]

1. **Wording.** RECORDED core (verbatim from the verdict file): "company-stated residual buckets ('Other', 'Rest of World') are legal slice values of their stated kind, kept out of cross-company grouping by FS-20/FS-24/FS-23." NEW DRAFT elaboration (each claim doc-verified, but this detail is NOT in the transcript): serialized as `segment:other` / `geography:rest_of_world`; the three guards unpacked are FS-20 (segment residuals -> PROVISIONAL/quarantined), FS-24 (provisional excluded until promoted), FS-23 (the unbuilt cross-company value layer's conservative bar); 'Corporate unallocated' is a NEW DRAFT additional example of the same class. **Boundary question for the panel (NEW):** whether 'International' belongs here at all - it is usually a real reported geography, not an accounting plug; the cleaner reading is a normal `geography:international` value unless the source states it as a residual complement of itemized regions.
2. **Problem.** Residual buckets are pervasive (11 of 40 sampled rows in the FiscalAI financial-breakdown section carry an "Other X" line) and rules point two ways: FS-07's business-population test arguably rejects a plug bucket, NAME-16 #11 bans vague category words (written for names, silent on slice values), yet these are real, recurring reported numbers.
3. **Why not already handled.** FS-06/FS-07 never say whether "other" is a legal slice value; FS-20 handles XBRL member residuals but not prose ones.
4. **Risk if adopted.** `segment:other` at company A is a different population than at company B - safe only while cross-company slice-value comparison stays conservative (FS-23 unbuilt; member-anchored grouping T12.9 is within-company). If a future layer naively compares residual values cross-company, this rule becomes an over-merge channel; the wording therefore names the three guards explicitly.
5. **Risk if rejected.** Producers fork between slicing, skipping, and naming; a recurring ~quarter of breakdown rows becomes noise.
6. **Interactions.** T1-01 (same family); T2-02 (residual values are excluded from SLICE_SAME_AS even WITHIN a company - an 'other' bucket's composition can change across quarters; T2-02 never crosses companies by construction); FS-20/23/24 (the cross-company guards - that over-merge risk binds the future FS-23 layer, not T2-02); L-02.
7. **Required changes.** One sentence in the OD-17 note + FS-07 clarification; one K-fields fixture (an "Other Revenue" row). Nothing else.
8. **Classification.** STRESS-TEST PROPOSAL (Q-02).
9. **Panel decision requested.** Approve / reject / rewrite; specifically test whether the three named guards actually block every cross-company read path today.

## T1-01c - Exception (iii): pure accounting constructs stay excluded, now explicitly [STRESS-TEST PROPOSAL]

1. **Wording (RECORDED from the FS-06a draft, exception iii).** "Pure accounting constructs (eliminations, fair-value levels) stay EXCLUDED per FS-07, dropped + logged." *(Citation note: FS-07 supplies the population test; the concrete dropped-from-menu-and-LOGGED mechanism lives in FS-20's HARD-EXCLUDE bucket.)*
2. **Problem.** "Eliminations from Revenue" is a real, recurring reported line with no home: it fails FS-07's population test (you cannot operate-as or sell "eliminations"), is not a measurement, and is not a portion of a business population (it is a consolidation artifact). A stress-test agent classed it "unrepresentable"; the truth is it is deliberately unrepresented - but no rule SAYS so, so adjudicators guess.
3. **Why not already handled.** FS-07 excludes accounting labels as slices but never addresses the whole-fact question (store, name, or drop) for elimination-style lines.
4. **Risk if adopted.** A rare mover story ("results swung on intercompany eliminations") would be droppable as a metric fact; it remains capturable as prose evidence/action_event if genuinely causal - the panel should confirm that fallback suffices.
5. **Risk if rejected.** Silent inconsistency: some producers store `segment:eliminations` (a fake population), others drop.
6. **Interactions.** T1-01b (residual buckets are LEGAL; eliminations are NOT - the wording must keep these visibly distinct); FS-07/FS-20.
7. **Required changes.** One sentence + the drop-and-log counter (log exists for skip classes already). Nothing else.
8. **Classification.** STRESS-TEST PROPOSAL (Q-02).
9. **Panel decision requested.** Approve / reject / rewrite; test the field-4 fallback claim.

## T1-02 - NAME-08a canonical financial spelling [STRESS-TEST PROPOSAL]

1. **Wording (RECORDED).**
   > "A universal, single-referent financial metric has exactly ONE canonical snake_case spelling, held in a small frozen table (~30-60 entries: eps, ebitda, ebit, ebt, capex, arr, rpo, aum, ...); coin that form under any source spelling. Three hard limits: (1) it rejects nothing - unlisted metrics coin normally, misses fall to dedup/SAME_AS; (2) it merges nothing beyond spelling - any narrowing-qualified form (net_, current_, fee_earning_) or window-prefixed form (dau/mau) is OUT of the table and owned by FS-06a / NAME-14 / period_scope; (3) consistency pin - where NAME-07/08 already fix a form (free_cash_flow, net_interest_margin), the table reuses that identical form, never a competing abbreviation. Tie-break: NAME-14 > (NAME-08 = NAME-08a) > open coinage - 'Adjusted EBITDA' is ebitda + measurement=adjusted, always."
2. **Problem.** `capex` vs `capital_expenditures`, `ebt` vs `pretax_income`: two producers coin different canonical forms for the SAME universal metric. These are lexically distant, so embedding/token dedup cannot reliably surface them as candidates, and the SAME_AS repair path is weakest exactly here: the synchronous CLAIM trigger ships OFF, and the day-1 async sweep depends on a code suggester (embeddings + token overlap) surfacing the pair - lexically distant spellings are precisely where suggesters miss. The split persists. NAME-07's familiar-name examples are macro-only; NAME-08's whole-phrase list has 4 entries; neither decides financial-statement spellings.
3. **Why not already handled.** No rule pins one canonical spelling for standard financial metrics; NAME-02 requires exactly one name per driver but nothing enforces convergence at coin time for this class.
4. **Risk if adopted.** A frozen table is curated data: the no-human rule is preserved only because it is rule-level (owner-ratified batches), rejects nothing, and misses degrade to today's behavior - but the panel must check the single-referent boundary (is `arr` universal or SaaS-jargon? is `net_revenue` in or out?) and the maintenance story. Over-merge risk exists only if a multi-referent term sneaks in (limit 2 exists to block that).
5. **Risk if rejected.** Permanent high-value series splits on the most-shared metrics; costly strong-tier SAME_AS adjudications later, through a repair path that must first FIND the pair (the suggester's weakest case).
6. **Interactions.** Runs AFTER T1-01's portion test (ordering pin); T1-04 never singularizes table forms; T1-06 uses the table as its cross-industry ATTACH exemption (adopting T1-06 without T1-02 removes that exemption and raises T1-06's cost); T2-03 uses the same "closed universal vocabulary" justification - if the panel rejects that justification here it must also reject T2-03's table.
7. **Required changes.** New NAME-08a in `02` + the seed table as a frozen owner-ratified artifact (same freeze discipline as the slice-axis table); PIPE-16 re-sync; K-reader gold names use table forms; EXP-2 reader rules block; WP-FC-RUN prompts. No code.
8. **Classification.** STRESS-TEST PROPOSAL - Fable's weakest substantive survivor (nearly cut in review); kept only because nothing else covers lexically-distant universal synonyms.
9. **Panel decision requested.** Approve / reject / rewrite; specifically attack the single-referent boundary and the frozen-table maintenance story against the no-human rule.

## T1-03 - NAME-16 #4 external-actor principle [HARD REQUIREMENT]

1. **Wording.** Principle owner-approved (Q-03); exact replacement sentence is NEW DRAFT:
   > "NAME-16 #4 (replaced): a company, platform, institution, or person name is ALLOWED in a Driver name when that entity is the EXTERNAL actor whose own independent action or state is the stated cause (the NAME-11 test-2 principle). Examples - from NAME-16 #4's own existing carve-out: `fed_rate`, `opec_supply`; from NAME-11's locked examples and pins: `walmart_price_cuts`, `aws_outage`, `tiktok_ban`. It is BANNED only when (a) it names the REPORTING company itself (redundant - the fact already links to the company), or (b) it is an incidental co-mention that adds no causal specificity (an analyst, executive, law firm, or counterparty named in passing)."
2. **Problem.** Current NAME-16 #4 bans "any ticker/legal/person name" with a carve-out only for "institutions/regulators" - yet NAME-11's own locked examples use plain commercial entities (`walmart_price_cuts`, `aws_outage`, `tiktok_ban`). Walmart, AWS, and TikTok are not institutions or regulators. Two locked, verbatim-inlined rules point opposite ways on the same concrete examples: a provable self-contradiction in the locked text, hence a provable producer-divergence channel.
3. **Why not already handled.** It is a drafting bug inside a locked rule; only a rule edit fixes it.
4. **Risk if adopted.** Slightly broader literal permission; "incidental co-mention" needs the two illustrative examples to stay sharp.
5. **Risk if rejected.** Producers keep diverging on the exact same locked sentence.
6. **Interactions.** PIPE-16/17 inline this text verbatim - re-sync required; no other item depends on it.
7. **Required changes.** NAME-16 #4 text swap; PIPE-16/17 re-sync; every reader/G2/Refute prompt from then on. Bundled doc-sync rider (same class of fix, NEW DRAFT): `09 §7`'s read-contract series-key sentence must add `period_scope` to match 12 FACT-33 (a builder reading 09 alone would reproduce the quarter-vs-YTD collision FACT-33 exists to fix).
8. **Classification.** HARD REQUIREMENT for the PRINCIPLE ONLY (owner approved, Q-03). The exact replacement sentence and the bundled 09 §7 period_scope rider are NEW DRAFT and classified STRESS-TEST - the panel must verify/approve them as text; treating them as fixed context would rubber-stamp never-agreed wording.
9. **Panel decision requested.** Two separate decisions: (1) approve/rewrite the NEW DRAFT replacement sentence as a faithful rendering of the approved principle; (2) approve/reject the 09 §7 rider after checking it against 12 FACT-33 (the rider is a doc-sync fix, never part of the Q-03 approval).

## T1-04 - Singular-by-default coining convention [HARD REQUIREMENT]

1. **Wording (RECORDED - reader rule + judge rule).**
   Reader rule (inlined RULES block):
   > "SINGULAR BY DEFAULT. Coin every noun in the driver name in its singular form: aws_outage not aws_outages, store_closure not store_closures, tariff not tariffs. The name is the cause CLASS - how many, how big, and how often live in the fact's fields, never the name. Exception - the plural IS the term. Keep the plural when the singular would name a different thing or is not how finance names the concept: earnings (an 'earning' is not a thing), bookings, sales, savings, futures, receivables, product_returns (a 'return' is an investment concept). The test: say the singular out loud - if it still names the exact same concept, use it; if it changes the meaning or reads as a different concept, keep the plural. Never touch locked whole phrases: NAME-08/NAME-08a forms stay exactly as written (same_store_sales is never singularized)."
   Judge rule (dedup / G2-rewrite / Refute prompts):
   > "A singular/plural pair naming the same concept is a wording variant, never two drivers - route it through rewrite-to-the-existing-form or dedup; when the pair might differ in meaning (booking/bookings), keep separate."
2. **Problem.** No rule pins singular vs plural; Stage-0 norm() rightly never stems (plural can change meaning: booking/bookings, future/futures) - so `aws_outage` vs `aws_outages` forks freely. The design docs themselves fork: the kernel writes `energy_costs` in one line, `resin_cost`/`freight_cost_pressure` in others.
3. **Why not already handled.** Deliberate absence of code stemming (correct - the v1 line) left the coin-time convention unwritten.
4. **Risk if adopted.** Borderline plurals (`job_cuts`) still fork occasionally - over-split direction, dedup-visible, repairable.
5. **Risk if rejected.** A high-frequency, fully preventable fork channel remains open, backstopped only by a repair lane that ships OFF.
6. **Interactions.** T1-02 (table forms exempt); code plural-folding experiment stays OFF (unchanged).
7. **Required changes.** One dated note under NAME-06 in `02`; PIPE-16 re-sync; K-reader/K-fields bind. No code.
8. **Classification.** HARD REQUIREMENT - owner approved (Q-04) with this exact wording.
9. **Panel decision requested.** None on the rule; report any meaning-changing singularization the exception test would miss.

## T1-05 - Slice-kind decision ladder (unknown when two or more kinds are plausible) [HARD REQUIREMENT]

1. **Wording (RECORDED - the FS-15 clarification ladder).**
   > "Slice-kind ladder (per stated company part): 1. Menu first. If the stated part matches a PIT slice-menu entry (same meaning - the producer judges the match; code never near-snaps), take the menu value and its kind. The kind came from the frozen axis table and is never reconsidered. 2. Menu-ambiguous. If the same normalized label appears under two or more kinds in the menu and the quote's own framing does not select one -> unknown:<value>. 3. Prose-only, kind clear. No menu match, but the quote's framing makes the kind plain ('our X segment', 'revenue in China', a named product) -> coin kind:value. 4. Prose-only, kind unclear. Two or more kinds remain reasonable -> unknown:<value> - the same honest constant as an unrecognized axis. Never guess; a guessed kind is a fake axis-grade confirmation (the rejected-P3 failure). unknown: values enter the company's menu like any other value, so later producers reuse them - one series per company, no fragmentation from honesty."
2. **Problem.** Prose-only parts ("Services Revenue") are plausible under two kinds (product vs segment); a guessed kind is byte-identical in the id to an axis-confirmed one, manufacturing a fake confirmation the future cross-company layer would trust. Additionally the same label can legitimately sit under two kinds in one company's menu (geographic segments: "Americas" on both the segment axis and a geography axis), so even menu picks can be ambiguous.
3. **Why not already handled.** FS-15's outcomes cover zero-kind unknowns; the >=2-plausible-kinds case and the menu-ambiguity case were unstated.
4. **Risk if adopted.** More `unknown:` values (deliberate, honest, reusable via the menu; promotion residual handled at T2-06/Q-06).
5. **Risk if rejected.** Silent kind forks inside fact ids; or a default-guess rule (rejected R-01) that fakes confirmation.
6. **Interactions.** Replaces R-01 (P3); T2-06 owns the promotion residual (Q-06); EXP-5 packets serve the menu.
7. **Required changes.** FS-15 clarification block; ladder verbatim in the Track-B producer contract (12 §7) and EXP-5 packet instructions; one K-fields trap (menu-ambiguous label). No code beyond the already-designed menu.
8. **Classification.** HARD REQUIREMENT - owner approved as scoped (Q-05).
9. **Panel decision requested.** None on the ladder; one verification task: confirm rung 2 against a real dual-axis case - e.g., a filer with geographic operating segments whose "Americas" member appears on BOTH the business-segment axis and a geography axis in its own XBRL (the panel sources the example from any such filer's filings).

## T1-06 - Strong confirmation before risky ATTACH writes [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).**
   > "ATTACH STRONG-CONFIRM: an exact-name ATTACH is confirmed by a synchronous strong-judge object/scope/mechanism 3-check BEFORE the fact is written whenever an ATTACH-risk flag fires at write time. The flag set = kernel S9.2's own deterministic pre-filter, applied synchronously (cross-industry exact-name attach; per-head industry-cluster count >= 2; scope/mechanism-qualifier divergence from the head's frozen anchor, same-industry heterogeneity included) PLUS one NEW criterion imported from S6.1: the head spans >= 8 companies (the HIGH_BLAST threshold, which today triggers a second skeptic only on SAME_AS/CLAIM links - extending it to ATTACH is an ADDITION, not a move of an existing S9.2 flag). EXEMPTION: heads whose name is a canonical universal metric (the NAME-08a table: eps, ebitda, revenue, ...) are cross-industry by design; for them only qualifier-heterogeneity triggers. Refused confirm -> the fact PARKS (never written to the head); the router's more-specific re-coin path applies. Wording fix in the same change: kernel S2/S11.0 stop classifying ATTACH/CLAIM discrimination as cheap 'routing' - it is identity confirmation work; CREATE/SKIP dispositions may stay cheap."
2. **Problem.** F1: mis-ATTACH is the one irreversible error, and S9.2's ATTACH audit already re-judges exactly these risk classes with a strong model - but only AFTER the write, when detection cannot un-place the fact. Moving the same ~100%-audited check before the write converts detection into prevention at near-zero net model cost.
3. **Why not already handled.** The kernel is in tension with ITSELF: S2 labels Stage-1 - which decides ATTACH - "the G2 router (ONE cheap call)" and S11.0 permits cheap "route" work, yet S11.0's own "Current owner default" paragraph assigns "G2 decisions" to the strong-judge tier (Sonnet 5), and its locked law forbids cheap final confirmation of identity-changing decisions. Fact placement is never explicitly named in S11.0's confirmation list; this item resolves the in-document wording tension in the strict direction and makes the pre-write check explicit.
4. **Risk if adopted.** Latency/cost on flagged attaches during earnings clustering; false refusals park facts (safe direction, drainable). Depends on T1-02 for the exemption - without it, common universal-metric attaches pay the tax. If T1-08 is ALSO adopted, a flagged ATTACH onto a no-XBRL head becomes a TWO-grader permanent-class approval - the combined cost is roughly double what this item alone implies.
5. **Risk if rejected.** High-blast wrong placements continue to be written permanently and only flagged later; the S2-vs-S11.0 wording tension stays unresolved.
6. **Interactions.** F1 (motivation); T1-02 (exemption source); T1-07 (covers the residual BELOW these flags); T1-08 (its catchability rule upgrades this confirm to two graders on no-XBRL heads - see field 4); T1-09 (isolates any caught residual); E-03 (EXP-3 must test confirm-by-default as a primary arm).
7. **Required changes.** Kernel S2, S9.2 (synchronous application), S6.1 (HIGH_BLAST threshold extended to ATTACH - a NEW criterion), S11.0 wording; EXP-3 arm design; no schema.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite (Q-07); specifically test the cost claim and whether the flag set is the right risk surface (young same-industry heads are BELOW it by design - see T1-07).

## T1-07 - Permanent uniform-random audit of unflagged links and attaches [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).**
   > "BASELINE AUDIT: every audit cycle draws a mandatory uniform-random sample of UNFLAGGED SAME_AS links and UNFLAGGED ATTACH placements, at a permanently non-zero, pre-registered rate (count fixed before the period from total volume, never adjusted after seeing flags - OD-6 discipline). Its result is published as its own population-wide floor bound (0 wrong in n => <=3/n at 95%), never blended with the risk-stratified bound."
2. **Problem.** S9.5's audit budget is risk-stratified ("blast-radius-weighted"); a published "0 wrong in n audited" therefore bounds only the already-suspected stratum. That is structurally the v2 failure: metrics that look clean because they measure the wrong population (~99% string-match while ~29% judged-correct). The volume-majority ATTACH case (young, small, same-industry heads) sits below every T1-06 flag AND below S9.2's pre-filter - today it has no bound at all.
3. **Why not already handled.** No mandatory unflagged-population sample exists anywhere in S9.5 or OD-6's live wiring.
4. **Risk if adopted.** Recurring strong-model cost with low hit-rate by design (that is what a floor bound costs).
5. **Risk if rejected.** "Zero-by-measurement" is honest only for the suspected stratum; the irreversible class stays unbounded exactly where it is least visible.
6. **Interactions.** T1-06 (covers what it exempts); T1-09 (routes what it catches); T1-08/E-04 (the same pre-registration discipline extends to PIPE-37); F1.
7. **Required changes.** Kernel S9.5 extension; OD-6 pre-registration wording extended from the one-shot gate to live ops; dashboard reporting split. No schema.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite (Q-08); test whether the rate can be pre-registered without becoming a tuning knob.

## T1-08 - Independent grading keyed to catchability [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).**
   > "CATCHABILITY RULE: every identity-PERMANENT approval on a card with NO model-free falsifier channel (no XBRL-concept backing - i.e., where no code check could ever catch a wrong merge) requires TWO independent graders regardless of head size; single-grader-below-K remains only for XBRL-backed heads where the falsifier is a real backstop. VENDOR DIVERSITY IS MEASURED, NEVER ASSUMED: the second grader slot uses a different model vendor only while the S9.6 calibration stream shows cross-vendor pairing yields a LOWER shared-miss rate on planted finance-identity pairs than the best same-vendor lens-split pairing; grader membership stays under the locked S11.0 experiment gate, never hard-coded. Cross-vendor unavailability PARKS the confirmation (safe direction), never downgrades to one grader. For seed links (3-grader), at least one grader is cross-vendor while the measurement supports it. PIPE-37's fitness-gate grader joins this rule: it must differ in vendor from both the producer and the LINK-judge vendor that built the catalog under test. GREEN WIRING: the calibration shared-miss rate becomes an enforced GREEN term - pre-register a ceiling C; inflate the rule-of-three bound by 1/(1 - shared_miss) before comparing to the quality budget; refuse GREEN above C. The planted calibration set rotates: fresh held-out pairs injected on the existing quarterly fresh-key cadence; exposed sets demote to regression-only."
2. **Problem.** The design's own stated deepest residual (kernel S16): all judges share one model vendor, and the model-free falsifier - the only independent channel - is blind on no-XBRL qualitative causes. Yet the current second-skeptic trigger is company-count (HIGH_BLAST >= 8), which has nothing to do with whether an error could ever be caught. Separately, S9.6 promises the shared-miss rate "discounts every confirmed clean" while OD-6's GREEN formula contains no such term - a promise never enforced; and PIPE-37, the single production go/no-go, only requires grader != producer, satisfiable within one vendor.
3. **Why not already handled.** Triggers are keyed to blast radius, not catchability; the GREEN formula predates the calibration-stream promise; PIPE-37's protocol predates the vendor concern.
4. **Risk if adopted.** Judge cost on qualitative claims (likely common); a second vendor lane is operational surface (mitigated by park-on-unavailability); cross-vendor diversity may prove to be theater (both vendors trained on similar finance corpora) - which is why the wording makes it measured, not mandated.
5. **Risk if rejected.** A vendor-wide blind spot can approve permanent merges AND pass the gate that unlocks production, with the promised discount never applied.
6. **Interactions.** T1-06 (its strong confirms join the permanent class); T1-07 (shared pre-registration discipline); E-04; L-01 (this rule bounds, does not remove, that floor); billing posture (a non-Anthropic grader is a metered lane - an owner ops decision, out of design scope but flagged).
7. **Required changes.** Kernel S6.1/S6.5/S9.6; OD-6 GREEN definition; PIPE-37 protocol; EXP-0-style calibration data informs vendor pairing. No schema.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Five separately decidable sub-parts (Q-09) - decide EACH: (a) the catchability trigger (2 graders on every identity-permanent approval lacking a model-free falsifier channel); (b) measured vendor diversity + park-on-unavailability; (c) the seed 3-grader cross-vendor slot; (d) PIPE-37's gate-grader vendor rule; (e) the GREEN shared-miss inflation term + rotating held-out pairs. Specifically attack whether cross-vendor diversity buys real independence (or is theater - both vendors train on similar finance corpora) and whether the GREEN inflation formula is well-posed at low sample counts.

## T1-09 - Fact-level disputed state [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).**
   > "DISPUTED FACT: a single fact confirmed mis-attached (by the S9.2 audit or any detector, through the existing RecoveryEvent + 2-grader machinery) may be marked `disputed=true` - excluding ONLY that fact from cross-company/history-weighted features while leaving the node's standing, its other facts, and event-level reads untouched. The fact never moves (id immutability holds); dispute is reversible edge-state-style metadata, emitting a RecoveryEvent, validated by V14."
2. **Problem.** Recovery today has two units: edge (SAME_AS quarantine) and whole node (homonym quarantine). A one-off mis-attach - a scoping error, not a systemic homonym - has no isolated fix: either leave it silently wrong or quarantine the whole Driver and drag every CORRECT sibling fact out of features.
3. **Why not already handled.** S10 was designed around link errors; fact-level granularity was simply missing (the review's kernel sweep rated this gap ARCHITECTURAL).
4. **Risk if adopted.** One more state for the feature/display layer to respect; a disputed fact still cannot be moved to the right node (true today for the whole-node case as well - strict narrowing, no new open question).
5. **Risk if rejected.** Every caught mis-attach forces a whole-node blast radius, making detection expensive to act on and discouraging quarantine.
6. **Interactions.** T1-06/T1-07 (they catch; this isolates); F1; X-IM proofs (E-series).
7. **Required changes.** Kernel S10 (new lane), S9.2 output routing, validator V14; one X-IM mutation test. One stored boolean per fact.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite (Q-10).

## T1-10 - TOKEN-SUBSET refusals become reconciliation-eligible; reconciliation is Day-1 work [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).**
   > "TOKEN-SUBSET LEDGER: the deterministic token-subset auto-refusal (kernel S6.1) stays exactly as-is on the fast path (free, correct for true genus/species). But every such refusal is RECORDED into the same deferred-pair/refuted-cache ledger judge refusals use, explicitly eligible for S6.6 batch-grade re-judgment once both sides are evidence-rich - demoting this one class from PERMANENT-BY-LOCKED-RULE to reconciliation-eligible. The other permanent auto-refusals (cross-flavor, terminal-suffix, per-X) stay permanent: they enforce locked rules, not a syntactic heuristic. COMPANION PIN: kernel S15.0's Day-1 core list explicitly gains 'S6.6 split-reconciliation lane (batch-grade, periodic, stated cadence)' - it is currently absent from BOTH the Day-1 and Deferred lists, yet the frozen-anchor design's own safety argument cites S6.6 as its recall-recovery twin."
2. **Problem.** Token containment is a syntactic test that can catch true synonyms: `comparable_same_store_sales` contains `same_store_sales` - the same cause, refused forever, with no ledger entry and no re-entry path. That is the design's one deterministic, unrepairable over-split, contradicting "over-split is cheap BECAUSE repairable". And if S6.6 ships late or never (the MVP-list gap), every frozen-anchor mutual-refusal also has no release valve.
3. **Why not already handled.** The v3.3 lock-read classified token-subset as permanent citing NAME-04; that is correct for genus/species but the rule fires on FORM, and form over-matches meaning.
4. **Risk if adopted.** Slightly wider S6.6 workload; a tiny chance the batch judge wrongly overturns a correct genus/species refusal (symmetric with every reconciliation risk already accepted).
5. **Risk if rejected.** True-synonym pairs matching token containment stay split forever with no record they were ever refused.
6. **Interactions.** T2-01 (S6.6 is name-layer reconciliation; T2-01 is read-layer - complementary, not overlapping); T1-01 (portion drivers are CORRECTLY refused vs their bare form - the ledger route must not re-litigate those: gold-DIFFERENT stays DIFFERENT; the batch judge's one-law bar applies).
7. **Required changes.** Kernel S6.1 (one classification change), S6.6 (intake), S15.0 (Day-1 list + cadence). No schema.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite (Q-11); test the field-6 concern that portion pairs could be wrongly reconciled.

## T1-11 - Deterministic measurement tokenization WITHOUT a maintained idiom table [STRESS-TEST PROPOSAL - replacement design; answers Q-12]

1. **Wording (NEW DRAFT - replaces the rejected idiom-table version).**
   > "SPAN = QUALIFIER: the unit of measurement tokenization is the producer-emitted span, one span per distinct stated qualifier - the producer (meaning's owner) decides what is ONE qualifier ('constant currency' = one span; 'adjusted, diluted' = two; 'adjusted diluted' = two), and code NEVER re-splits or re-joins spans. Code then normalizes each span independently (lowercase -> non-alphanumeric runs -> '_' -> trim -> collapse), code-sorts the resulting token set, and comma-joins - identically regardless of source punctuation. FORMAT LINT (code): a span containing a comma, semicolon, or the standalone word 'and' is rejected back to the producer as an invalid multi-qualifier span. The current 'maximal contiguous span = one token' merging assumption is retired."
2. **Problem.** Today's OD-9 normalization joins by source adjacency: "adjusted diluted EPS" -> one token `adjusted_diluted`, while "adjusted, diluted EPS" -> two tokens `adjusted,diluted`. Same semantics, different fact ids - a punctuation-driven identity fork. The obvious fix (an idiom table telling code which multi-word phrases are one token) was owner-rejected: a human-maintained meaning table violates the no-human rule and is the v1 pattern.
3. **Why not already handled.** OD-9 pinned code-only format normalization but inherited an adjacency assumption that quietly makes PUNCTUATION decide identity.
4. **Risk if adopted.** Producers may disagree on span boundaries for odd phrases - a fork, but in the over-split direction (two ids for one fact = duplicate-shaped, visible to the dual-producer probe and the value-level twin match); prompt cost of one instruction.
5. **Risk if rejected (and no alternative).** The punctuation fork stays; or the idiom table returns with its human maintainer.
6. **Interactions.** T2-03 (read-time SEMANTIC equivalence stays separate - this item is write-time FORMAT only; OD-9's no-write-time-synonym-merge rule is untouched); EXP-5 scoring compares measurement token SETS - binds to this recipe.
7. **Required changes.** OD-9/FS-25 tokenization paragraph; 12 FACT-17b producer-contract sentence; one code change in the (unbuilt) normalizer; EXP-5 fixtures (one punctuation-variant trap). No table, no humans.
8. **Classification.** STRESS-TEST PROPOSAL - the replacement design is new and untested.
9. **Panel decision requested.** Approve / reject / rewrite; specifically test whether span-boundary disagreement rates would be material (the dual-producer probe measures it) and whether the format lint is sufficient.

---

# Tier 2 - Recall Healing and Write Integrity

## T2-01 - One read-time reconciliation framework with raw/reconciled labels [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).**
   > "READ-TIME RECONCILIATION FRAMEWORK: all approved repair views (T2-02..T2-05) run under ONE framework: recomputed on every read, never touching a stored id, fact, or fact_scope; instantly reversible by disabling the instance; and every query result labeled `raw` or `reconciled` so no consumer mistakes a repaired view for stored truth. Any frozen table an instance uses lives under the same freeze/pre-registration discipline as the slice-axis table."
2. **Problem.** The asymmetry law ("over-split is cheap") holds only where a repair path exists. Today several split channels have NONE: measurement drift is split-by-design (66 E7), slice-label drift heals only via member anchors (~57% of facts carry no member link - FS-21's own stated figure, verified), `series_unit=unknown` buckets never rejoin. Without repair paths these are quiet permanent recall losses - the same failure class as over-merge, in slow motion.
3. **Why not already handled.** T12.9 (member-anchored grouping) proves the read-time pattern but covers only XBRL-anchored slice labels; nothing generalizes it.
4. **Risk if adopted.** Read-time compute per query; reconciled views can flip as new facts arrive (why labeling is mandatory); each instance adds an error channel in the reversible direction.
5. **Risk if rejected.** The minimalist position (also recorded in review): ship nothing until a consumer proves the loss - accepted cost is silent series fragmentation for the majority of facts.
6. **Interactions.** Parent of T2-02/03/04/05; distinct from kernel S6.6 (name-layer) and from T1-10; consumes T1-01b's guard (residual slice values never cross-company-fold).
7. **Required changes.** One read-layer design section (12 FACT-33 area); no write-path or schema change by construction.
8. **Classification.** STRESS-TEST PROPOSAL (Q-13).
9. **Panel decision requested.** Approve the framework shape (then judge instances individually), reject wholesale, or rewrite.

## T2-02 - SLICE_SAME_AS within company and kind [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).** "A candidate pair of slice-value strings under the SAME company + kind that plausibly denote the same real part may receive a reversible SLICE_SAME_AS link, gated by the existing LINK-judge machinery (2-grader confirm, quarantine, memo) - consumed ONLY by read-time reconciled views (T2-01). It never fires on stated-recast language (a recast means the composition CHANGED); it never crosses companies; residual values (T1-01b) are excluded."
2. **Problem.** "the Americas segment" (Q1) vs "our America segment" (Q3) with no XBRL member link: T12.9 cannot heal it; the series silently splits.
3. **Why not already handled.** The owner rejected the alias-file mechanism (D-3); T12.9 is the only approved healer and requires member links.
4. **Risk if adopted.** Judge cost; an over-merge inside one company's slice space (bounded blast radius; reversible edge); scope creep if ever read cross-company (explicitly forbidden in wording).
5. **Risk if rejected.** Prose-only slice drift stays permanently split - likely the majority case for transcript/news facts.
6. **Interactions.** T2-01 (instance); R-07 (RECAST_TO is its semantic opposite - adopting both without the never-on-recast guard folds genuinely different populations); T1-01b.
7. **Required changes.** One edge type + judge invocation surface (reuses LINK judge); FACT-35/T12.9 section extension; candidate generation bounded per (company, kind).
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite; test the D-3 boundary (is a judge-gated edge meaningfully different from the rejected alias layer? Fable's argument: alias files were curated data; this is the same evidence-judged, reversible machinery trusted for Driver names).

## T2-03 - Frozen measurement-equivalence table (read-time only) [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).** "A small frozen equivalence table (~10-20 rows: {adjusted = non_gaap = ex_items}, {gaap = reported = as_reported}, ...) builds an ADDITIONAL reconciled grouping view beside the exact-token series. Read-time only; never touches ids, the write path, or OD-9's no-write-time-merge rule; reversible by dropping the table; frozen under the same discipline as T1-02's table."
2. **Problem.** A company alternates "adjusted EBITDA" and "non-GAAP EBITDA" across quarters with identical calculation - two series forever, and measurement has NO healing path at all (no XBRL anchor exists for measurement).
3. **Why not already handled.** OD-9 deliberately forbids write-time synonym merging; nothing was designed for read time.
4. **Risk if adopted.** A company meaning something narrower by "adjusted" than "non-GAAP" in one quarter folds wrongly in the reconciled view (raw view unaffected; mitigation: table stays tiny and conservative). Same no-human tension as T1-02 - it is curated data, defended the same way (frozen, rejects nothing, rule-level ratification).
5. **Risk if rejected.** The most common measurement drift stays permanently split.
6. **Interactions.** T2-01 (instance); T1-11 (write-time format vs this read-time semantics - no overlap); T1-02 (the shared no-human JUSTIFICATION must be judged consistently, but the two tables are otherwise independent - write-time spelling vs read-time semantics - and may be decided separately on their other merits).
7. **Required changes.** Table artifact + read-view code; FS-25 note. No write path.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite.

## T2-04 - Fold unknown series_unit into one clean axis when uniquely safe [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).** "At read time only: if a Driver's established facts carry exactly ONE clean (non-unknown) series_unit, a reconciled view MAY fold its `unknown`-tagged facts into that axis provided nothing in each fact's own quote/values contradicts it; the moment a second clean axis appears, the fold stops (fail back to split)."
2. **Problem.** Early ambiguous facts get series_unit=unknown; later facts resolve cleanly; the two buckets never rejoin even when trivially compatible - an unhealable over-split by OD-10's strict-equality grouping.
3. **Why not already handled.** OD-10 deliberately forbids read-time unit family maps and unknown absorption at the STORED layer; a labeled reconciled VIEW was never considered.
4. **Risk if adopted.** A wrong fold if the single-clean-axis heuristic mis-fires (bounded: reconciled-view only; auto-stops on second axis); view instability as facts arrive (labeling mandatory).
5. **Risk if rejected.** unknown-bucket facts stay permanently invisible to series consumers.
6. **Interactions.** T2-01 (instance); OD-10 untouched at the stored layer.
7. **Required changes.** Read-view logic; 09 glue-rule-1 note. No write path.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite.

## T2-05 - Continue an explicitly declared rename [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).** "When a filing explicitly states label continuity ('we renamed Core operating margin to Underlying operating margin; no change in methodology'), the producer emits a transient `measurement_continuation_of=<old_token>` hint; a read-time view chains the two series. Evidence-gated only - never blind synonymy; never merges stored ids."
2. **Problem.** Self-declared renames are textually PROVEN continuity, yet today the series still splits forever.
3. **Why not already handled.** OD-9 forbids synonym merging generally; the self-declared case was not carved out.
4. **Risk if adopted.** Only catches declared renames (partial fix); one more rare extraction pattern.
5. **Risk if rejected.** Even textually proven continuity stays split.
6. **Interactions.** T2-01 (instance); T2-03 (general equivalence vs this specific declared case - complementary).
7. **Required changes.** Producer-contract hint + read-view chain. No stored schema (hint is transient; the chain lives in the view... NOTE for panel: if the chain must persist, it becomes a stored edge - decide which).
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Two decisions: (1) approve / reject / rewrite the rule; (2) decide the field-7 storage question (transient recompute vs a stored edge).

## T2-06 - Exact-qname backfill after slice-axis table refreshes (+ Q-06) [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).** "On each offline frozen-axis-table refresh, one mechanical backfill pass re-points stored `unknown:xbrlaxis_<hex>__<member>` slices whose hex-decoded axis now appears in the table with a confirmed kind - exact-qname match only, no LLM, no fuzzy matching. OPEN SUB-DECISION (Q-06): whether a PROSE-coined `unknown:<value>` (no axis qname) may be promoted by exact-NORMALIZED-LABEL match within the same company when a later filing tags that label on a confirmed axis, or stays raw and is healed only by read-time reconciliation. Fable's recommendation: read-time first; label-promotion only if the read-time path proves insufficient, and then company-scoped, exact-normalized, logged."
2. **Problem.** A 2024 fact written under an unrecognized axis stays PROVISIONAL forever even after the 2026 table refresh confirms that axis - identical units of information permanently poorer by write date (time-invariance loss).
3. **Why not already handled.** FS-13 refreshes the table; no rule addresses already-written facts (FS-20 gives HARD-EXCLUDE an auto-demote path; PROVISIONAL promotion has none).
4. **Risk if adopted.** A write-path mutation of an identity-bearing stored field (the slice-kind serialization inside fact_scope) - the only item that does so; T1-09 also persists stored per-fact state, but as reversible non-identity metadata (a boolean) that never changes the fact id. Must be exact-match, logged, and reversible (keep the original serialization recoverable). Label-promotion (Q-06 option) carries a small same-word-two-roles over-merge risk.
5. **Risk if rejected.** Permanent vintage inequality in the graph.
6. **Interactions.** T1-05 (produces the prose unknowns Q-06 covers); T2-01 (the alternative healer); FS-12/13/20.
7. **Required changes.** One offline batch job + FS-12/13 note; audit log.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Two decisions: (1) approve / reject / rewrite the qname backfill; (2) DECIDE Q-06 - label promotion vs read-time-only healing for prose-coined unknowns.

## T2-07 - Value-change ledger for same quote, different values [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).** "When a MERGE onto an existing fact id finds value-bearing fields differ while the source quote/event is UNCHANGED, the write PARKS to a value-change ledger (fact id, old, new, producer, timestamp) for the existing review lane instead of overwriting silently. When the quote itself changed (a corrective/restated document), overwrite freely - that is a legitimate change."
2. **Problem.** A re-run or newer model re-reading the SAME quote can flip stored values on the same fact id with zero forensic trace (`created` is on-create-only). Identity errors are heavily audited; value flips are invisible - failing the detectability requirement for the numbers the system trades on.
3. **Why not already handled.** The writer's field-diff exists only as a no-op-vs-write optimization; the no-null-clobber rule (12 FACT-14b) blocks null erasure but not non-null value flips.
4. **Risk if adopted.** Ledger volume (expected low); a tolerance band needed against trivial float formatting.
5. **Risk if rejected.** Silent value drift remains undetectable end to end.
6. **Interactions.** 12 FACT-14b (extends its philosophy); T1-07 (audit family); no id/schema change.
7. **Required changes.** Writer branch + ledger artifact; 09 §7 note; one synthetic fixture.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite.

## T2-08 - Axis-commitment hint on first percent-family fact [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).** "The FIRST fact for a (driver, scope, series_unit) whose value is percent/bps-flavored requires a transient, never-stored `axis_commitment_hint`: the producer asserts whether this driver's bare name denotes a RATE (its % is a level -> level fields) or an ABSOLUTE quantity (its % is a change -> change_value). Code cross-checks the routing against the hint - same propose-then-verify pattern as the existing shape/unit hints."
2. **Problem.** DU-16 rule 7 routes rate-vs-level deterministically off the driver's metric type - but the SEED fact of a brand-new lexically ambiguous driver ("membership_growth") has no established type; two producers can fork level_low=3 vs change_value=3 and split the series shape at birth.
3. **Why not already handled.** DU-16.7 presumes the driver's nature is known; the first-fact case is the one place it is not.
4. **Risk if adopted.** One more hint in an already hint-heavy contract; genuinely novel names can still be ambiguous (narrows, does not eliminate).
5. **Risk if rejected.** First-fact basis forks are caught only later, at read time, as shape conflicts.
6. **Interactions.** R-02 (this is the surviving residual of rejected P4 - P4's validator was order-dependent; this hint is not); 09 §3 hint discipline.
7. **Required changes.** Item-contract field (transient) + one FACT-16-style check + EXP-5 fixture.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite.

## T2-09 - Stated specificity beats a familiar umbrella name [STRESS-TEST PROPOSAL]

1. **Wording (NEW DRAFT).** "NAME-07 precedence clause: use the familiar short form only when the source does not itself distinguish a specific named instrument or benchmark within that family. If the evidence explicitly names a sibling instrument (`sofr` vs `fed_funds_rate`), NAME-04 specificity wins - coin the specific form. Familiarity is a fallback for undifferentiated mentions, never a license to flatten stated specificity. (Commodity benchmarks are ALREADY locked by NAME-12(c) - `brent_oil_price` vs `wti_oil_price` stay in the name; this clause extends the same posture to the non-commodity families NAME-12 does not cover.)"
2. **Problem.** NAME-07 ("familiar names win": fed_rate, oil_price) has no stated precedence against NAME-04 ("as specific as evidence allows"). A producer applying NAME-07 flatly coins `fed_rate` even when the source says SOFR - merging genuinely distinct instruments the kernel's own judge-territory list treats as distinct siblings. Note: NAME-12(c) already resolves COMMODITY benchmark identity (brent vs wti - a locked exception); the unresolved seam is non-commodity families (interest-rate benchmarks and similar), which NAME-12's commodity scope does not reach.
3. **Why not already handled.** Two locked rules with an unstated precedence; the sibling cases sit exactly on the seam.
4. **Risk if adopted.** Slightly more producer judgment per familiar-family mention.
5. **Risk if rejected.** Umbrella flattening of benchmark siblings - a within-rules over-merge channel on macro causes, the highest-blast-radius names in the catalog.
6. **Interactions.** NAME-04/NAME-07/NAME-12(c); kernel S6.1 sibling judge-territory; no other item.
7. **Required changes.** One clause in NAME-07 + PIPE-16 re-sync + one K-pairs-style fixture at next key version.
8. **Classification.** STRESS-TEST PROPOSAL.
9. **Panel decision requested.** Approve / reject / rewrite.

---

# Rejected Ideas (proposed rejections - confirm, overturn, or modify)

Each was proposed during this review and killed by it; the panel re-judges the kill.

## R-01 - Reject P3: default-to-segment kind guessing
When a slice kind is undecidable, pin it to `segment`. **Killed because:** it launders "undecidable" into a fake axis-grade confirmation, byte-identical in the id to a real one - a manufactured over-merge surface for the future cross-company layer, and it only governs the producer who KNOWS they are unsure (confident mis-readers still fork). Replaced by T1-05's `unknown:value` (HARD). **Decision:** confirm rejection.

## R-02 - Reject P4: rate-vs-level coherence validator
Park any percent fact whose level/change slot disagrees with the driver's established basis. **Killed because:** first-writer-wins is ORDER-DEPENDENT (backfill order changes outcomes - a reproducibility bug); it false-positives on a pattern DU-17's differing-unit allowance explicitly blesses (a bps change on a % level - DU-17 does not mention document sources; the 10-Q/8-K pairing is an illustration, not DU-17 text); the underlying fork was already closed deterministically by DU-16.7/OD-11. Surviving residual handled by T2-08. **Decision:** confirm rejection.

## R-03 - Reject P10: trigger-word escalation list
Inline a list of known-ambiguous qualifiers that force the ambiguity route. **Killed because:** it is a closed keyword list (the v1 death pattern; NAME-19 forbids example-list rules); off-list ambiguity gets false confidence; and it routes P1-valid drivers into NAME-18(f), which REJECTS (a recall hit). Redundant with T1-01's principle. **Decision:** confirm rejection.

## R-04 - Reject INSTANCE_OF / part-of roll-up edges
A judge-gated non-identity edge for genus/species or bucket/total roll-up. **Killed because:** no concrete consumer exists; identity-adjacent edges must earn their keep; doc 09 already rejected horizon collapsing (false change-flags); the real need it serves (cross-company exposure baskets) is served query-time or by the future FS-23 value layer. Its honest cost is recorded as L-02. **Decision:** confirm rejection (revisit ONLY on a named feature consumer, and then in the value layer, never as identity edges).

## R-05 - Reject NAME-13 exact-conversion unit table
Code-canonicalize physical per-X units with exact conversions (therm <-> MMBtu). **Killed because:** "exact" conversions hide grade/basis risk; a new frozen table + resolver surface for a rare class with no consumer; the one law prefers keeping them separate. **Decision:** confirm rejection.

## R-06 - Reject FS-09 coarsening nudge
When one source states an extra qualifier, default to the coarser existing slice. **Killed because:** it DROPS a stated qualifier - the forbidden over-merge direction; it contradicts FS-09's never-drop-a-part rule. (Fable overruled its own review agent here.) **Decision:** confirm rejection.

## R-07 - Defer/reject RECAST_TO edge
A stated-recast succession edge between old and new slice identities. **Killed/deferred because:** it fires only on explicit recast language (rare); member-anchored T12.9 already heals tagged recasts; and it is semantically OPPOSITE to T2-02 (recast = composition changed; SLICE_SAME_AS = same part, new words) - shipping both invites folding genuinely different populations. **Decision:** confirm deferral; if T2-02 is adopted, its never-on-recast-language guard is mandatory.

---

# Honest Limits (claims for the panel to challenge)

## L-01 - First qualitative homonym can evade correlated models
For a no-XBRL, qualitative cause, all falsifier channels are silent; the first wrong merge on a co-extensive-looking pair is caught by nothing model-free. A deliberate hunt for a model-free oracle (return signatures, co-occurrence, disagreement rates) found every candidate confounded. T1-07/T1-08 bound and measure this floor; nothing removes it. **Challenge invited:** find a non-confounded oracle.

## L-02 - Cross-company specificity differences stay split
`resin_cost` vs `raw_material_cost` vs `petrochemical_input_cost` for one real-world shock stay three Drivers (NAME-04: breadth only by same-name reuse; genus/species never merges). Exposure-basket questions are answered query-time (semantic search) or by the future FS-23 value layer - consciously unserved at identity level. **Challenge invited:** show a trading-critical query this breaks that query-time search cannot serve.

## L-03 - Silent adjective drift stays split without a declared rename
A company quietly shifting "core" to "underlying" with no continuity statement stays split (T2-05 catches only declared renames; T2-03 catches only table-listed equivalences). Safe direction; visible in series metrics. **Challenge invited:** quantify the expected frequency from real filings.

---

# Experiment Effects (consequences to verify, not design rules)

## E-01 - EXP-0 and K-pairs.v1 remain valid
K-pairs gold is SAME/DIFFERENT meaning truth; coining conventions (T1-01/02/04) change how names are SPELLED at birth, not whether two meanings are the same. Verify: no v1.3 record's gold flips under any adopted item.

## E-02 - Pending keys bind the new rules
K-reader, K-fields, K-route are undrafted; every adopted naming/slice rule binds at drafting time (zero rework). New trap classes staged: portion-in-measurement (T1-01), menu-ambiguous label (T1-05), punctuation-variant measurement span (T1-11), first-fact axis hint (T2-08).

## E-03 - EXP-3 gains confirm-by-default and ATTACH baseline measurement
If T1-06/T1-07 are adopted, EXP-3's arms must test synchronous-confirm as a primary shape (not only a failure fallback) and measure the unflagged-ATTACH baseline.

## E-04 - PIPE-37 gains cross-vendor grading and a shared-miss GREEN term
If T1-08 is adopted, the fitness-gate protocol and OD-6's GREEN formula change BEFORE the gate ever runs (it has never run - no invalidation).

---

# Interaction Map (one view; details in each item's field 6)

- **The ATTACH chain:** F1 -> T1-06 (prevent, flagged) -> T1-07 (bound, unflagged) -> T1-09 (isolate, caught) -> T1-08 (independent confirmation where uncatchable). Adopting T1-06 without T1-07 leaves the volume-majority unmeasured; T1-07 without T1-09 makes catches expensive to act on.
- **The coining order:** T1-01 portion test FIRST -> T1-02 spelling of the bare metric -> T1-04 singular form -> NAME-14 measurement strip (unchanged law: NAME-14 beats all whole-phrase claims).
- **The two tables:** T1-02 and T2-03 share one justification (closed universal vocabulary, rejects nothing, frozen) - accept or reject the justification consistently. T1-11 needs NO table (span-based).
- **Name-layer vs read-layer repair:** T1-10 (S6.6, Driver names) and T2-01..05 (facts/series) are complementary lanes; neither substitutes for the other.
- **Opposites guard:** T2-02 never fires on recast language; R-07 stays deferred.
- **Residual-value guard:** T1-01b residual values are excluded from T2-02 even WITHIN a company; the cross-company over-merge risk binds the future FS-23 value layer (T2-02 never crosses companies by construction).

# Owner Questions Register (updated)

- [x] Q-01..Q-05: settled; recorded in the verdict file and folded into T1-01/03/04/05 above.
- [ ] Q-06 -> decided inside T2-06.
- [ ] Q-07 -> T1-06. [ ] Q-08 -> T1-07. [ ] Q-09 -> T1-08. [ ] Q-10 -> T1-09. [ ] Q-11 -> T1-10.
- [x] Q-12 -> answered by T1-11's span-based replacement design (itself stress-test).
- [ ] Q-13 -> T2-01.

# Settled Incorporation Notes

(Unchanged from v1 - implementation records for the four HARD items: FS-06a portion qualifiers; NAME-16 external actors; singular/plural; FS-15 ladder. See v1 text below, kept verbatim.)

### FS-06a Portion Qualifiers

- Add one owner-decision row, `OD-17`, to `66 §0.R` through the normal verify/define/recommend process. This is an addition, so Fable says no `95_Supersession` row is needed.
- Add one dated portion-qualifier note under `NAME-11` in `02_DriverCatalog.md`: an otherwise-unrepresented word that changes which portion is counted stays in the Driver name; a differently qualified portion is a different Driver and is never `SAME_AS` the bare form; uncertainty stays in the name and is never dropped.
- Add one boundary sentence to `FS-25` and mirror it in `NAME-14`: measurement re-expresses the same quantity through a different lens; a word changing which portion is counted is never measurement and belongs in the Driver name.
- Reader and judge machinery does not change. After the document notes land, PIPE-16's existing verbatim rule block is re-synced if WP-FC-EDITS already ran.
- K-reader and K-fields draft under OD-17. Add one K-fields trap where a portion word is wrongly placed in measurement.
- Deliberately add no field, slice kind, validator word list, id change, kernel change, XBRL change, or invalidation of completed work.
- The three exceptions may enter OD-17 now or remain separate review items; owner decision pending (T1-01a/b/c).
- Measured scope: about 55-60 of 3,170 operational KPI names (~1.9%), collapsing to roughly 15-20 portion Drivers around six base metrics; small by count but concentrated in highly reused series.

### NAME-16 External Actors

- Replace `NAME-16 #4`'s confusing company/legal-name ban with the external-actor principle.
- Ban the reporting company's own name and incidental company mentions.
- Keep an outside company or platform in the Driver name when it is the actual cause.
- Re-sync `PIPE-16/17` and every reader, G2, and Refute prompt from that point forward.
- Fable identified no substantive downside.

### Singular and Plural Driver Names

- Reader rule: coin every noun singular by default because the name is the cause class; count, size, and frequency belong to fact fields.
- Keep the plural when singular changes the meaning or is not the financial term, including `earnings`, `bookings`, `sales`, `savings`, `futures`, `receivables`, and `product_returns`.
- Meaning test: say the singular; use it only when it still names the exact same concept.
- Never alter locked NAME-08/NAME-08a whole phrases such as `same_store_sales`.
- Judge rule: same-meaning singular/plural pairs are wording variants routed through rewrite or dedup; meaning-uncertain pairs stay separate.
- Place one dated note under NAME-06 in `02_DriverCatalog.md`; PIPE-16 then inlines it into reader/G2/dedup/Refute prompts; K-reader and K-fields bind to it.
- Keep code unchanged and ADOPT's plural-folding experiment off.
- Honest residual: borderline plurals can still over-split, but remain visible and repairable.

### FS-15 Slice-Kind Ladder

- Unique matching PIT menu entry: take its existing value and code-supplied kind; never reconsider the kind.
- Same normalized menu label under two or more kinds: use the quote's framing when it selects one; otherwise use `unknown:value`.
- No menu match with clear prose framing: coin `kind:value`.
- No menu match with two or more reasonable kinds: coin `unknown:value`; never guess.
- Add unknown values to the company menu so later producers reuse one honest series.
- Add the clarification block to FS-15 and place the ladder verbatim in the Track-B producer contract and EXP-5 packet instructions.
- Add one K-fields trap for a menu-ambiguous label.
- Deferred residual: a prose-coined unknown has no axis qname; exact-label promotion is decided later in the FS-12 backfill item (T2-06/Q-06) or left to read-time reconciliation.

# Final Consolidation Reminders

- [ ] FC-01: Before drafting the final reply, confirm the three separately reviewed FS-06a exceptions (T1-01a/b/c) and ask the owner whether any or all should be included in OD-17.
- [x] FC-02: Exact NAME-rule and judge wording for singular-by-default and standard-plural exceptions supplied and recorded.
- [ ] FC-03 (new): After the panel reports, verify no adopted item edits a design/experiment/key/prompt/code file without a fresh owner go-ahead.
