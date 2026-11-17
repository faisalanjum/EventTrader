# Driver rules — still-open discrepancies

Reviewed November 16, 2026 (EST). **27 of the workflow's 63 claims still need work**, grouped into 25 entries below. The other 36 are settled, already governed by a rule, or implementation choices rather than rule conflicts. The workflow also contained D6, an already-dismissed layout suggestion; it is outside the 63.

Checked against the current [rulebook](DRIVER_RULES.md), [Categorized copy](DRIVER_RULES_Categorized.md), [archived Simplified copy](Archive/DRIVER_RULES_Simplified.md), [EXPLAINED_BY](EXPLAINED_BY.md), [News rules](NewsMultipleSymbols.md) and [workflow](DriverWorkflow/DriverWorkflow.md). Older designs were checked as background, not allowed to override current rules. Original review IDs appear in brackets. This list records problems, not proposed solutions or new approvals.

## Features included in the target but missing their design

The opening instruction already settles scope: features marked “off” or “later release” are included in the target. Their old off labels do not reverse that decision. Required evidence, tests and activation checks still apply.

1. **Outside forecasts have no complete fact format.** `expectation` is included in the target, but the naming rules, allowed states and field table cover only four types. Firm, analyst and forecast-setting date are draft fields only. [A1]
   - Source: rulebook opening instruction; 1.22, 2.19, 3.3, 3.5, 9.11; DriverWorkflow step 1.

2. **Unconfirmed guidance has no separate history design.** The target includes `company_confirmed=false`, but 9.2 explicitly requires a design for reading, ranking, comparisons and later confirmation. Under the current history keys, such claims can enter the company's own guidance series. Its boundary with the new `expectation` type is also unsettled. [A2]
   - Source: 1.5, 3.2, 4.4, 4.9, 7.1, 7.5, 9.2, 9.11.

3. **Metric text and action conditions still have guidance-only definitions.** The target includes both, but the field table forbids them on those types. The existing text-value definition describes a forecast, and its “tidied” wording differs from 9.8's exact-source-words condition. [A3]
   - Source: 3.3 field and per-type tables; 4.7–4.8; 9.8.

4. **The Driver's financial classification is undefined.** The target includes this field, but its meaning and allowed values are absent. Rule 9.6's named user and testable definition are not supplied; saved Driver records are otherwise frozen. [A4]
   - Source: 2.1–2.2; 9.6; Overview “What's on in the first release.”

5. **Comparing company parts across companies has no matching rule.** The target includes it, but 3.23 says no rule equates those parts, and 9.3's required design is absent. Identical labels alone do not establish identical business populations. [A5]
   - Source: 3.20–3.23; 7.11; 9.3.

6. **The intended use of 8-K item categories is undefined.** The target includes them, but 9.4 still permits item numbers only as information and forbids their use to type, rank or route facts. No replacement use is described. [A6]
   - Source: 2.34; 9.4; Overview off-items table.

7. **The explicitly deferred unknown-axis view remains unreconciled.** The opening instruction includes everything, while 7.10 separately says this view was reviewed and deferred and needs a fresh owner decision. Its behavior is not defined beyond “grouping by unknown XBRL axis.” [A9]
   - Source: opening instruction; 7.10; older FINAL_DESIGN §5.2. The schema scratchpad itself classifies this both as deferred and as a target-scope conflict.

8. **Facts made from tagged filing data do not fit the current save contract.** Part A1 requires origin/link/upgrade records absent from the fact table. It allows an in-place text-to-tagged upgrade without defining the changed fields, despite frozen values and source locations. It also skips a later conflicting value where 5.3 keeps an extra fact. [A10]
   - Source: 1.17; 3.3; 5.3, 5.5; 6.11–6.12; Part A1 “Text and tagged versions” and “Record.”

## Driver links and corrections

9. **SAME_AS has no agreed creation process.** It is included in the target, but 6.20 bars background creation and 9.9 requires a separate safety design for immediate linking. The final-check item acknowledges this; no replacement process is agreed. [I2]
   - Source: final-check item 2; 1.19; 2.4; 5.6; 6.20; 9.9.

10. **“Reversible” links have no general reversal permission.** SAME_AS and declared-rename links are called reversible, but 6.18 permits switch-offs only through the named mechanical rename checks. A wrong synonym link, or a false rename outside those checks, has no approved reversal path. [G1]
    - Source: 1.15, 1.19, 2.1, 5.6, 6.15–6.20. Archive/DRIVER_RULES.md's older repair rules do not override the current ban.

11. **Rename records lack a defined on/off representation.** Rules require disabling a rename without deleting it and ignoring it in every view. Neither displayed rename-record property list includes that state. [G2]
    - Source: 6.15–6.19; 7.10; “Stored relationships” rows for CONTINUES_AS and ContinuationClaim.

12. **The slice/tag rename record is only partly specified.** ContinuationClaim lists “kind, old, new …”, although dated reads need its public time and source evidence. Its company connection is also still an explicit owner decision. The fuller old-design record is background, not current approval. [G3]
    - Source: “To be decided” item 1; ContinuationClaim table row; 6.13–6.15; 7.10; older FINAL_DESIGN rename record.

13. **The warning overstates protection from tagged data.** “No automatic tripwire when there's no XBRL data” can imply wrong merges are checked when tagged data exists. The current after-save check covers declared renames only; 6.20 supplies no corresponding wrong-merge check. [I3]
    - Source: S1 red risk warning; 6.19–6.20. The older merge-check design was removed from the current rules.

14. **The wrong-name/type question remains explicitly parked.** Current rules already forbid renaming or retyping a saved Driver and provide a safe fallback of a more specific name or skipping. They do not close 10.2's separately deferred question about handling an already misnamed or mistyped Driver. [F2]
    - Source: 2.2; 2.38; 2.47; warning after 2.32; 6.20; 10.2.

## Facts and source evidence

15. **Forecasts of another party's decision still lack an agreed representation.** A statement such as “we expect FDA approval in Q3” has no settled guidance/action representation covering its time and conditions. Skipping and counting it is the agreed temporary behavior. [F1]
    - Source: 1.6; 2.23; 3.8; explicit open item 10.5.

16. **Whether facts store their producer is undecided.** Rule 5.3 mentions a producer, but the fact table has no such field. P2 still asks whether to store it and in what form; explanation-producer fields do not answer this fact-level question. [J6.4]
    - Source: 3.3; 5.3; parking item P2 and its note; A2.3.

17. **Transcript availability is unverified.** All 9,608 current transcripts have `created = updated = conference_datetime`. Those times do not establish when the full cited transcript became public, as required for a fact's public time and past trading views. [J5.3]
    - Source: 3.3 `date`; 1.14; “Public time” definition; EXPLAINED_BY §8 R4. Read-only database check repeated in this review.

18. **Older News evidence has no settled preservation path.** News edits replace text in place, while facts must remain tied to a checkable original version. The News rules correctly mark unavailable earlier text as unverified, but do not settle how a fact's previously cited version is retained and checked after replacement. [J7.2]
    - Source: 1.17; 3.3 `source_location` and `date`; 6.18; NewsMultipleSymbols “When a story changes” and “Before switching on”; EXPLAINED_BY §2.

19. **Reports held for a missing filer have no named retry trigger.** Rule 3.9 holds them, while 8.14–8.15 require a specific trigger. The current database has 390 Reports without PRIMARY_FILER, including 21 of the admitted base forms: 12 8-K, 8 10-K and 1 10-Q. [J7.1]
    - Source: 3.9; 8.14–8.15. Read-only count repeated in this review; this count alone does not prove every Report contains an otherwise writable fact.

## Operation and existing data

These are operating or data gaps, not reasons to invent different graph meanings.

20. **History limits remain unset.** History is included in the target, but its measured capacity limits and research budget are still open. The workflow's company-history step depends on them. [A8]
    - Source: 8.16; 10.1, 10.3; EXPLAINED_BY §7; DriverWorkflow company-workflow step 2.

21. **Past company membership is not supplied by the current graph.** Rule 7.11 requires the industry grouping at the viewed time, and 1.20 requires a recorded eligibility moment. The 922 current BELONGS_TO links have no properties; the current company/group records do not provide that history. The source of this past membership remains unspecified. [B6]
    - Source: 1.20–1.21; 2.42; 7.11; BELONGS_TO table row. Read-only relationship check repeated in this review.

22. **Saved daily returns disagree with their closing-price formula.** Across all 655,858 Company HAS_PRICE links, 655,047 have usable positive paired closes: 654,996 agree within 0.02 percentage points and 51 differ by more than 1 point. The remaining 811 lack such a pair. NFLX on July 23, 2025 gives −90.11% from stored closes 1,190.08 → 117.678, versus saved −1.12%. Which underlying inputs need correction remains unverified. [B3]
    - Source: A2.7; EXPLAINED_BY §8 and its existing gate in 10.1. Full read-only comparison repeated; NFLX arithmetic independently checked with decimal numbers. Positive control: the documented AAPL closes 150.82 → 154.50 give +2.44%.

23. **The reference period resolver still prefers old Guidance data over SEC evidence.** For DRI FY2026 Q3, its existing-period branch returns December 1–February 28 before consulting the SEC branch. The two filing period ends establish November 24–February 22. This conflicts with source-date priority and the ban on using old Guidance to fill Driver history. Current old Guidance readers/writers merely existing is not itself a discrepancy. [H1]
    - Source: 3.43; 8.11; EXPLAINED_BY §6.1's planned resolver reuse; `driver_reference/core/driver_period_resolver.py` existing-before-SEC branch and `_default_lookups`; `guidance_write_cli.py:_lookup_existing_period`.
    - Evidence: old period `gp_2025-12-01_2026-02-28`; Reports `0000940944-25-000071` and `0000940944-26-000009`. Rechecked read-only; native resolver reproduced the wrong branch with these database answers. Exact source dates passed as a positive control.

## Current picture and text corrections

24. **The pictures omit relevant connections already described elsewhere.** Picture C does not show Context's axis/member pair lists; FACT_DIMENSION alone is not the complete route to a figure's breakdown. Its filing labels also omit explicit mention of amendments covered by 6.7. Picture B omits the source-to-industry/sector/market INFLUENCES links listed in the relationship table. These are drawing corrections, not new rule decisions. [D3, D4]
    - Source: Pictures B–C; “Stored relationships”; 6.7, 6.9–6.10; NewsMultipleSymbols. A live AAPL context confirmed the paired list fields; the existing adapter already reads them.

25. **Some references and counts remain stale.** EXPLAINED_BY §7 and NewsMultipleSymbols still cite removed parking items P3/P4/P7 and completed reconciliation work. Several pointers still address the older working file or an old location. Rule 3.4 says 24 fields while the current table has 25. [D5, J6.2]
    - Source: EXPLAINED_BY introduction, §6.1 handoff and §7; NewsMultipleSymbols “Not in this change”; rulebook S2 “Out”, 8.17 and Overview historical-reference paths; 3.3–3.4. The new fact-flag policy is already answered in P1's “Resolved” column; its pending wording is not another open design question.

## Existing owner decision outside the 63 claims

- **Spreading withdrawals remains under review.** The current “To be decided” item 2 still reserves 4.18–4.21 for owner review. The broader target-scope instruction does not settle the explicitly listed question.

## Review boundary

No rulebook, picture, code or database change was made by this review. No additional graph node is required merely because the workflow asked where a catalog, log, saved decision or withdrawal record lives; the current rules leave storage implementation open.

Workflow evidence: `005fee79-b5fa-4d46-870f-6afb28f1b000/subagents/workflows/wf_3c05e77a-a86/journal.jsonl` under the owner's Claude project directory. The J/E verification and final completeness pass stopped at the subscription limit; their drafts were checked directly here. The separate picture proposal is from `wf_c6594caa-687`.

Reviewed rulebook SHA-256: `8e96e29725b319a545240ee2d554ac098eae45c73d2232c29eef60f498ae41c4`. This is a document review with focused native-code checks, not certification of the unfinished Driver build or of all price inputs.
