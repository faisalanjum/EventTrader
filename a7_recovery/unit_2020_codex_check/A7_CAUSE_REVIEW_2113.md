# A7 cause review — 2026-09-13, Codex

Status: source review and minimal correction design OPEN. No original answer,
judgment, key, prompt or scorer changed. Baseline remains 98a7a6ad and published
recovery HEAD 86e742ee. This note records evidence, not new grading law.
The work order and current mailbox remain the shared task owners.

## Already proved

- Actual consumer binding: all306 G2 questions,70 prompt hashes, every native
  established/missing aspect reach the real scorer unchanged. See
  codex_scoretrace2112_a/MEANING_BINDING_CHECK.json, SHA648da353.
- Core2113's40 guidance rows correctly bind to14 sources and22 distinct
  record/context/reference-card combinations. Ten are repeated across legs;
  one record/aspect is decided both ways and12 are decided in one question
  but unresolved in another. Different question ids and batches remain; these
  were NOT byte-identical calls. See CORE_2113_INDEPENDENT_CHECK.json.
- Core's DRI midpoint objection is false. Exact midpoints are10.60 and10.62.
  The qa explicitly says the new midpoint is higher. Source
  DRI_2026-03-19T08.30, qa SHA
  bfe811b41dca273ab6f6eddb81ae7a34f0bb73abaabaeb04b2e6079a232d2ab4,
  character range28062–30172, prompt G2-026 SHA
  ec34f46ba0bbc1787b26ab1e9fbac9220da0033095ff928a925544e37672f15f.
  Keep the three raised-state judgments. Core's170 generic cannot_establish
  cells and its company-flag/empty-slice shortcuts do not complete source
  review. Codex2113 assigns the same scope, grouped to avoid duplicate reading.
- Guidance movement is revision against the company's own prior guide, not
  expected business growth. The served short sentence does not make that
  distinction explicit. A consistent alternative reading does not establish
  product-law correctness. FINAL_DESIGN4.3/6/9 own the distinction; a minimal
  correction belongs in the existing state contract, never a company word list.
- Actual G._display retains encoded unknown-axis population tokens, while the
  context menu uses A.readable_menu's reversible display.24 token occurrences
  exist across P1/P2/UNION (5/7/12), including6 in5 G2 questions. The existing
  decoder round-trips every one. See DISPLAY_GAP_2113.json. This proves a view
  mismatch, NOT which verdicts it caused. Preserve ordinary/off-menu unknown
  tokens and raw evidence; do not invent another decoder.
- UNION's reported144 duplicate violations adds54 G1 groups and90 G3 fact
  classifications;72 of those facts overlap the G1 groups. It is NOT a count
  of144 distinct facts. G1 connects attempts at the same claim even when fields
  are wrong; it does not establish exact duplicate emissions or correctness.
  PartD3/6 and Step1 distinguish exact emissions and unresolved answer groups.
  Do not select a group member arbitrarily or weaken a pass bar to fix a count.

## Source checks outside Core's guidance task

The following are cause-review findings, not permission to rewrite grades.
Full source is read from the frozen G2 event context, not from a key conclusion.

1. DRI divestiture,0000940944-25-000038,gold1: the business source first
   announces the deal but later explicitly says it closed July14,2025, before
   the July18 event. The latest stage is occurred. Producer announced is a
   genuine error; do not change the key from the short quote alone. Prompt
   G2-022 SHA7ca64052ec3a8c927402f233f0b37b944d1a43ca440a4784a52ff2cda57262f5;
   business SHAeb16f7d255f612ed77c37e46bc52b740bed566468f71a2bf6268a3958383084f.
2. Signed metrics: DRI0000940944-26-000009,gold0,P1 losses -3.8 vs -0.3
   decreased; DAL0000027904-26-000013,gold1,UNION losses -26 vs -39 increased.
   Those directions follow the signed axis, not business desirability. The
   corresponding false state verdicts are suspect/incorrect on that aspect;
   other record faults must remain. DAL promptG2-033
   SHA962eda67e48c1cc8033abfd9c6bc84689ed83f01e0c3b19891d000588d2a7929,
   mdnaSHAf61c10f7cf2e122b1a1745c81d7a34a9a8d9c1f7ab3915459e535195ef1435be.
   Positive error control: AAL0000006201-26-000032,P1 pretax loss -327 vs
   -530 was labelled decreased; that producer state really is wrong.
3. ORLY0000898173-26-000006,gold3,P2 store count6447: the same full source
   table gives6265 for the prior year (and6406 beginning current quarter).
   Source-stated prior values support increased, not bare reported. This is a
   concrete key/state-review lead; key-owner source-only review must precede
   any key correction. PromptG2-028
   SHA1ec77bb8a18df322e23ee9ba6fc0099dde94aae740918c544fc62a7b5027055e,
   exhibit SHA f09491bf95f2b0ccdd63e0e4bb601c3b7ca12705dc9e5fa78fa21b25d3b69bc2,
   table around character23914.
4. BBY0000764478-25-000057,gold0,P1: source says impairment related to
   Best Buy Health and the exact decoded menu choice exists. The hex/raw view
   discrepancy is real. P2's empty population is not equivalent to this
   specific business. Do not automatically approve other fields. For gold3,
   UNION online domestic sales mix31.8 vs31.4 is supported by the source table,
   but the whole-record verdict still needs period/calendar review; agreement
   with the key alone is not proof. mdna
   SHAdbac58d3ebb2e5f2ab648317e173721569b489eac512d6cf377980e5615280ce.
5. G3 extras prompts omit full event context. They serve short reference cards
   and produced records. This cannot establish absent-source claims where a
   needed footnote or paragraph lies outside the served excerpts. Reuse the
   existing verified-event-context owner if a correction is required; do not
   build a second source reader. Missing context alone does not rescue a fact.
6. DRI0000940944-26-000005,UNION extra2: full footnote says impairment
   primarily relates to Bahama Breeze closures. That does NOT prove the whole
  24.7 belongs to that brand; also check pretax measurement. Do not overturn
   unsupported merely because the footnote mentions the brand. Source
   SHA5d5188563c00ee5f3b682211a00c785f447517ab74482af3297c03dbf5ca98d6;
   G3-001 SHA142ac89630fe28a0747b6143caf8a085439ac450fd63c21b861f6de224729690.
7. YUM0001041061-26-000084,UNION extra1: the full mdna confirms the2023
   Russia exit, but its11M net operating loss combines several items and is not
   automatically an exit transaction value. Do not approve the whole action
   merely because the exit occurred. Source is accessible in G2-063
   SHAd069f6c286f20ade07d27434f365e6470ad850ee4e489c0da3b42f2fe3670e77.
8. Some G3 key_miss classifications concern claims plainly already present in
   all served reference cards: ULTA0001104659-25-118458 has all5 cards, including
  84 Space NK stores; AAL0000006201-26-000032 has the pretax-loss claim. A
   missing/invalid G1 reading or no unique match is NOT a missing key claim.
   A legal null is better than forcing an inapplicable bucket. G3-000
   SHA16613a23f6a43a4886a4cdc5b334c83d578f6e936709887acd06530d5cd2618d;
   G3-009 SHA904148f38b414174acf348d30a1251e2c5766a49f18c650c858c0848d7dfa01e.
   Do not add rows to the key from these labels alone.

## Remaining bounded work

- Finish the source dispositions of observed false/unresolved judgments and
  extra classifications, retaining genuine producer errors and ambiguity.
- Settle the duplicate rule/count boundary; no second matcher or arbitrary
  best-answer selection. Preserve the measured original baseline.
- Reproduce necessary test defects first; make the smallest existing-owner
  corrections. Run focused positive/negative/mutation and affected regressions.
  Never edit/repin a frozen owner to make historical calls appear current.
- Freeze the exact correction population and task before any justified new
  grader/key evidence. Reuse successful saved382 producer answers and all valid
  unchanged grading evidence; do not reroll for a better score.
- Save the corrected report with every uncredited/refused/ambiguous event
  visible, then publish verified work. A low but correct score is acceptable;
  it does not authorize production or waive later gates.
- At the END only, offline A7-side model-selection/input-contract review against
  QwenInference.md and LOCAL_QWEN_HANDOFF.md; no local-engine changes or calls.
  Finish A7, then STOP AND WAIT. No A8 or later work.
