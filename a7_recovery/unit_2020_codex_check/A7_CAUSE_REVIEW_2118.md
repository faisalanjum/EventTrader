# Further A7 source dispositions — Codex, 2026-09-13

This continues2113/2114; it is not a new key, grader verdict or product rule.
Raw382 answers and the published baseline98a7a6ad remain unchanged. Source
quotes below are from the actual frozen event contexts, not outside data.
The live scorer trace0b4a3f62 supplies original item identities/verdicts.

## Four source checks completed

1. **BBY online sales mix — M8624b63494238990**, UNION,
   source0000764478-25-000057, gold3/produced8. Original promptG2-050 SHA
   b5eec38a55e5884b60d7a88e23b143c0fb62d458d36f235cf2424d3674191334;
   mdna SHAdbac58d3ebb2e5f2ab648317e173721569b489eac512d6cf377980e5615280ce.
   The Domestic table header at character16171 identifies the first two
   columns as the three months ended November1,2025 and November2,2024;
   the line around16881 is31.8/31.4. The source explicitly calls the current
   quarter fiscal2026 Q3; event_date2025-12-05/fye_month1 is consistent.
   Thus the period does NOT refute this record. Source supports the percent
   mix, domestic/online population and prior-year comparator. The original
   record_matches_source=false remains a concrete grading-error lead, not
   explained by an incorrect year or quarter. Identical key bytes alone were
   NOT used as proof. Do not replace the qualified verdict from this note.

2. **ORLY domestic store count — Mfdc3b99ab640f039**, P2,
   source0000898173-26-000006, gold3/produced3. PromptG2-028 SHA
   1ec77bb8a18df322e23ee9ba6fc0099dde94aae740918c544fc62a7b5027055e;
   exhibit SHA f09491bf95f2b0ccdd63e0e4bb601c3b7ca12705dc9e5fa78fa21b25d3b69bc2.
   Table around23298–24500 states current6447, prior6265 and beginning6406.
   FINAL_DESIGN4.3 explicitly says a source-stated prior value makes a metric
   directional rather than bare reported. The false state judgment and key's
   reported state require independent source-only key review, NOT a whole-
   record rescue. The separate US-versus-domestic population issue remains;
   the key notes Puerto Rico is included, which requires source checking and
   cannot be settled from the fact's short quote or a token label.

3. **DRI diluted continuing-operations EPS — M6d9dd25a44c4125e**, P1,
   source0000940944-26-000009, gold1/produced2. PromptG2-022 SHA
   7ca64052ec3a8c927402f233f0b37b944d1a43ca440a4784a52ff2cda57262f5;
   mdna SHA7c40db0be0eed2ff64f79e34e906c804c8b8b163b4d86a80317aa33f5d08b0d8.
   Full table around2151–3351 states diluted continuing-operations EPS2.68
   versus2.74 for the fiscal2026 third quarter, with(2.2)% beside it.
   The stored prior_year comparator is source-supported. Original G2 marks
   growth_basis and record_matches_source false. Investigate the exact
   omitted-change rule: FINAL_DESIGN7.1 says leave change_value null when
   derivable from closed operands; the served meaning contract only says
   stated differs from merely derivable, without that explicit precedence.
   This is a concrete input-contract completeness question, not permission
   to force all fields true or simply repeat an unchanged semantic answer.

4. **CAKE debt-extinguishment loss — M54c69cfbbfb770fe**, P2,
   source0001104659-25-105631, gold1/produced1. PromptG2-030 SHA
   259b71703500e262c3410e823f33c8417d55557154e4cb9347ecd74b31b7b3a3;
   mdna SHA6f9cf952e6c5e16f8221937056abe947b12c9bc0c5e877d6d17c1237c7101081.
   Source around28829–30029 says loss15.9 million:13.8 million premium
   plus2.1 million unamortized issuance costs, associated with276 million
   principal repurchased for289.8 million. Producer states positive15.9 as
   the action's value; that is not the signed loss nor the principal or
   transaction consideration. Keep record_matches_source=false; no input
   or grading fix is justified to rescue it. The source also states Q1FY2025;
   a window exists even though the producer left time_type null. The
   metric-versus-action interpretive ambiguity is separate from this amount
   error and does not make the positive amount correct.

## Complete non-guidance agreed-false inventory

Derived from every leg's actual `grader_verdicts` in trace0b4a3f62, joined to
candidatecc9d51f5's full G2 population:28 questions. These are cause-review
dispositions, NOT substitute graded verdicts. A genuine whole-record error
does not prove every individual negative aspect was justified. The14 other
agreed-false questions are guidance and remain under the2114 source review
and the corrected guidance contract. Missing aspects remain counted.

| Questions | Disposition and next action |
|---|---|
| M292ac8520c3978ff | AAL -327 versus-530 is an increase on the signed axis; the producer says decreased. Genuine wrong state, retained as a negative control for the general signed-axis correction. |
| M0e085961f8057af7; Mb81fc1be7b290e6b | DAL CASM surprise leaves out the source-stated2.4% reading and non-fuel/non-GAAP qualifiers and sets favorability wording true for positional in-line wording. Real record faults remain; no whole-record rescue. |
| M6c722b0ca333185b | BBY Health is explicitly in the full source and the reversible menu. The encoded/display mismatch requires the planned corrected-input check. |
| Mde7d5e39712de0c7 | Same BBY claim but producer picks the whole company. That is not the named Health population; retain the real scope error. |
| M838398e01dc7b3d7 | Revenue is not revenue share. Naming a percentage mix as an amount loses the claim's denominator; retain the name/whole-record finding. |
| Md5b6d93a0e42868a; M53a1b3ba077cabd8 | DRI's sale closed July14 before the July18 source. An earlier announced quote does not override the source's later completed stage. Retain both findings. |
| M6d2b09a6d78a96e6; M6a52868797fca479 | DRI's -0.26 is an EPS reconciliation adjustment for the sale, not the transaction's value. No rescue of the action from that quantity or its forecast-table placement. |
| Md1b56847528f639c; M86be1a27f32dbaf2 | DRI -3.8 vs-0.3 decreases; DAL -26 vs-39 increases. Original negative state judgments conflict with the signed-axis rule; recheck only through the corrected instruction, preserving any other faults. |
| M6d9dd25a44c4125e | DRI EPS2.68 vs2.74 and fiscal2026Q3 are supported. Missing explicit closed-operand change precedence is investigated below; no forced true verdict. |
| Mc0fee81b5ffc9975; M884c4845393d55ce |79% is a share of units, not a unit count. Retain this genuine denominator/name error. |
| Mcb1fb316d377bb0a | Chipotlane's producer omits a period and time type. Its whole-record finding has a real period issue; the separate negative slice judgment is not established by that omission, since the key itself treats the cause/population role as unclear. Do not force a population to rescue one aspect. |
| Me9adff0c6d62ed44; M84f7bd7ab2bad82f; Mb6660dcce1356528 | All3 numberless trend records put percent_sequential in change_unit with change_value=null. The served contract already requires a change unit to accompany a change value; numberless growth may use level_unit instead. Retain the whole-record error; do not confuse sequential comparison with the underlying growth basis. |
| Mfdc3b99ab640f039 | ORLY state/key issue described above; also retain the independent domestic-versus-US population question. |
| Mc6c32dee91400e91 | DRI impairment's empty population, pretax measurement and the source's 'primarily' brand attribution must remain separate. Full-source recheck is needed; neither a bare brand mention nor the key alone proves the entire24.7 belongs to one brand. |
| M54c69cfbbfb770fe | CAKE15.9 positive debt-extinguishment amount is a genuine error; full source and exact amounts are above. |
| Mf91a92c59065852f; M02d957fa99800507 | AAL's 'less than10 percent' is not an exact point of10. Retain the shape error. |
| M8351d2825bae0891 | AAL's17 gates are a stated future project, not a delivered reported metric. Retain wrong lane/state. |
| M8624b63494238990 | BBY31.8/31.4 source and calendar do not explain the negative whole-record grade; preserve as a grading lead, not a key-calendar correction. |
| Ma31af1665347b9ec | YUM's 'nearly60%' record is numberless and leaves out a population while naming digital mix. Do not declare a source-faithful cautious numerical omission wrong merely to match the key; the population/name and approximation questions need the actual contract. Preserve the original finding pending that bounded adjudication, not a forced numeric60. |
| M89298db1b2082404 | CMG's combined group-occasion part may lawfully remain an unknown kind. The meaning of sales versus sales mix and instant versus duration is separate. Do not rubber-stamp the negative slice merely because another field may be wrong; keep this semantic uncertainty visible. |

The12 calendar/name/scope details above are read from the actual question
records, including their null defaults, rather than inferred from names.
Their raw prompt identities remain in the original frozen candidate. No
classifier or word-list implementation is created from this review table.

## Apparent missing-key claims: reuse the existing source reviews

The signed key's sidecar is7cc31690134040d453c3bb01dc36f810b62f18984e86b0f6cea59e5b12677b62,
at unit_2081_final_key_candidate/codex_cand2082_a/candidate/sidecar.json.
It records44 abstentions and10 explicit exclusions. Those records and the
original source were inspected, not a summary's key-miss label alone.

- MCD80million, P1/P2 source0000063908-26-000032/produced0, was already
  reviewed and explicitly excluded as packet#033: the source attributes the
  total only PRIMARILY to the named restructuring cause. Full source SHA
  f698f1d4f6e8f6112564db2c9e1fd031f03962f96b583f43dec6422af24bc113,
  around1836 and4829, confirms the aggregate qualification. P2 additionally
  drops pre-tax. A key_miss bucket does not make the producer's entire named
  cause amount correct. Do not commission a duplicate source-key review of
  this already answered issue or add its guessed per-cause amount.
- YUM40million, P1/P2 sourceYUM_2026-02-04T08.15/produced2, was likewise
  reviewed and explicitly excluded as packet#184. Full prepared remarks SHA
  06f2a48e4d029516332c7726847c21404da3d59ba1f73103a2a1d12022dd3d29,
  around13797, says40million of special expenses PRIMARILY related to the
  Pizza Hut review. Neither a review-cost name nor a Pizza Hut slice may claim
  the whole amount. Reuse that source review; no new key call is warranted
  by the erroneous key_miss classification alone.
- All4 ULTA P2 key_miss labels name claims already in its5 source cards:
  Space NK84 stores, coverage-ratio covenant, base-rate margin and SOFR margin.
  The known incomplete G1 reading does not erase the key. AAL's UNION pretax
  claim and AZO's P2 sales-change claims also have existing source cards;
  inspect record correctness separately instead of adding duplicate key rows.
- DAL85% in P2/UNION describes survey RESPONDENTS with an expectation, not an
 85% travel-spend level. Its source supports the former, not the latter claim;
  the key_miss label is not a reason to insert the latter as truth.
- CAKE P2 source0001104659-26-017090/produced4 and6 are the prior-year
  columns:1% Q4FY2024 and2% FY2024. The full table SHA
  fc7c756b3b8139d8ba4eb88b9cb2adf8dd955bb0b188cf78d8c5c17b04ccf94a,
  around16674–18224, proves those periods. The key explicitly omits those
  historical columns and keeps only-4% Q4FY2025 and-2% FY2025. Whether that
  exclusion is lawful under the selected-target benchmark and DU-03 needs
  source-only review; do not invent a current-period-only gate or declare the
  correctly dated2024 facts wrong solely because they are historical.

## Prompt-contract checks queued, not yet applied

Three focused RED tests in test_grading_contract_gaps_2118.py pass their
existing-owner controls then fail the missing instructions:3 failed in0.14s.
They prove instruction coverage, not a model's future semantic correctness.
FINAL_DESIGN7.1 explicitly gives closed-operand change omission precedence
and places percent-only guidance in level slots, with only the guide's own
revision in change_value. The current G2 prompt omits those precise clauses.
G3 currently has no declared-field/default/quantity/scope contract at all,
although it decides whether these full structured records are source-backed.
The smallest remedy is to reuse the existing meaning-contract owner in G3
and clarify those two existing numeric rules once for both kinds, not another
grader or schema. No example, company, desired answer or semantic code rule
belongs in the correction. Renderer95d1a5ae stays unchanged until Core's
currently frozen connection task reports, so that proof is not invalidated
mid-task. Preserve that version before applying a successor, then rerun the
affected input/fit/native checks and freeze the actual call population.

A preliminary STRUCTURAL inventory, not call authority:40 G2 guidance,
34 G2 metrics with a negative operand,5 encoded-population views and62 closed
level/comparison shapes overlap in122 distinct G2 questions. This is a
possible affected-class bound, not122 proved wrong judgments or permission
to reroll them. All117 G3 questions lack the field contract and full source
in the historical packets. Actual necessary reuse/recheck scope must be
frozen under Plan2 amendment4 before any call.

## Remaining scope

Finish the observed source/extra/missing-judgment inventory, not a new source
harvest. Fix only proved grading/input/key defects under Plan2 amendment3–6.
Existing qualified independent graders remain required for replacement
meaning verdicts. Key errata require a fresh source-only independent owner.
No output-informed review note above may be supplied to that key owner.
Freeze exact affected questions and a ceiling before necessary new calls.
