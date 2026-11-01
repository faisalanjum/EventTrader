# What does a name identify? Naming-referent audit (Codex 2299; read-only; zero calls)
The four candidate referents:
- (a) the located target: the recognized 24.7 charge;
- (b) an upstream event qualifying it: the restaurant closures;
- (c) the company's own measured population;
- (d) the target's occurrence/state.
Sources:
- served rules: NAMING_CAUSE_ENCODING_20260923/TASK_C.txt (68683764…), the same rules as every recent cohort;
- law: FINAL_DESIGN.md (497c21f5…).
Only public texts are used; no private thinking was read.

## 1. Law → served mapping
| law | served | what it says about the referent |
|---|---|---|
| Glossary FINAL:31: Driver = "one reusable, atomic cause or standing thing that can matter to a company or market" | NOT served (ROLE and Rules only) | "cause" = the thing that matters, i.e. the Driver itself, not the reason behind a target |
| NAME-01 FINAL:86 "the name contains the cause only. Event state, direction, size, time, company, unit, and quote live elsewhere" | Rule 3.1 TASK_C:67, same | excludes (d) and other slots; the word "cause" is left undefined in the served text |
| NAME-04 FINAL:89 "use all specificity the evidence supports" | Rule 3.3 TASK_C:70, plus "a stated specific instrument beats the familiar broad name" | the only clause that reaches (b): a stated qualifier is specificity; it does not say that a stated REASON FOR the target counts as its specificity |
| NAME-10/11 FINAL:95-96 | Rule 3.4 TASK_C:73 | separates (c) (own measured part → slice) from an "external actor, object, platform, policy, event, or product" that causes the outcome (→ name); "unclear role → keep it in the name" |
| NAME-15/16 FINAL:101 | Rule 3.10 TASK_C:102 | excludes state/direction/polarity (d) and "effect" words; carve-out only for an EXTERNAL actor whose own action is the cause |
| ROLE (served only) | TASK_C:1-10 | names "the one target meaning to interpret"; "Interpret that target only." → (a) |

- The law separates (c) and (d) from the name clearly.
- It does NOT state how (b) relates to (a) when (b) is the company's OWN event. The 3.4 and 3.10 keep/carve-out clauses are
  literally "external"; the closures are Darden's own planned action.
- So no clause says in so many words that "a reason the source gives for the target qualifies the target's name". Only NAME-04's
  general specificity duty reaches it.
- At the same time, 3.1 "Name the CAUSE only" and 3.10's ban on "effect" words can be read as pointing AT (b), with "impairment"
  read as an effect, while ROLE points at (a).
- Shortest generic distinction the law actually needs: the name identifies the located target; a stated reason that qualifies
  WHICH target it is (and is not an own measured part) is part of that target's specificity, not a second target. That is
  NAME-04 applied. It is written nowhere as a relation, and "cause" in 3.1 is not defined for the served reader.

Verdict: an UNDERSPECIFIED RELATION, not a literal conflict. The combined name is lawful and reachable under NAME-04 (the same
served text often yields it), but the text lets a reader frame the choice as (a) XOR (b). This is a hypothesis about the text,
not a proved defect. Confidence 7/10.

## 2. Existing public observations
SUPPORTING (the (a)-versus-(b) framing):
- ORIG-N1 (wf_849db539-6ac, text 1ea48ca6…; think-aloud, a CHANGED task rejected at 2218, labelled evidence only), Q5:
  "Alternatives considered: `restaurant_closures` (the stated cause phrase) vs `asset_impairment` (the effect being measured)."
  and "the row is reporting the impairment charge itself (the measured line item), while \"restaurant closures\" is the reason
  for it, not the thing recorded in this row." Two alternatives only; the combination is never considered.
- ORIG-P1 (wf_a27505d8-dd5, 48205ca0…), Q5: rejects `restaurant_closure_impairment` because "Rule 2 already supplies
  \"asset_impairment\" as the canonical bare-root name for this exact concept", and rejects `restaurant_closures` as "the closure
  action itself, not the impairment charge".
- ORIG-N2 (wf_d81fa75c-1ab, a72a52ea…): rejects `restaurant_closures`, citing 3.4 and 3.1 (reading them as "affected unit"), and
  chooses by the Rule 2 list.
- FF2 (NAMING_FOCUS_CONTRACT_20260922) returned `restaurant_closures` (WRONG_TARGET): the mirror image, choosing (b) and dropping
  (a).
- D01, D02 and E03 state the relation accurately (charge "primarily related to the closures of Bahama Breeze locations") yet name (a) only. D01 says no
  field encodes the reason; D02 and E03 point the reason at the population field (c).
- NR2 (review; MANUAL_NR2 R3): says the specific name "folds an effect/result word (impairment)". A reader applying 3.10's
  "effect words" to the target noun. It also misattributes the bare-root list to Rule 3.
- V1 (wf_ad1e7ea9-f6e, 5b5a35c5…; REVIEW of the supplied specific record U554): it reads `occurred` as possibly asserting that the
  physical closures happened in Q3 ("It does not establish that a restaurant closure 'occurred' in Q3 FY2026"). With the qualifier in the name, a reader re-attached the state (d) to (b). This shows how a record is
  READ; it is not a producer cause.

DISCONFIRMING / LIMITING:
- The same served text often gives the specific name (T39, E02, C02, D03, E01; the Codex-2285 name-only cohort 3/3; the Rule 4 ablation under Codex 2294, 6/6). So the text does not compel
  the XOR framing.
- The glossary Driver sentence, served verbatim (2288), did not help (C 4/12 vs D 1/12).
- Rule 2 list removal (T-series) and the "examples decide fact_type only" sentence (M-series D arm) were each not sufficient, and
  removal was not necessary. The list is a public tie-breaker in ORIG-N1/N2/P1, not a proved cause.
- ORIG-P1 applies `occurred` to the charge; no think-aloud names future closure timing as its reason, so (d) is not a shown
  producer reason.
- NR2's referent was UNCLEAR, and it raised no closure-timing objection.
- The think-aloud answers come from a changed task and do not show what an unchanged run did.

## 3. Hypothesis vs proved
- PROVED (public, bounded): readers can hold the accurate relation (b → a) and still name (a) alone (E03, D01, D02). Some public
  reasons frame naming as choosing (a) OR (b), and never the qualified target (ORIG-N1, ORIG-P1; FF2 shows the other side).
- HYPOTHESIS: the served text leaves the (b)-to-(a) relation undefined for an INTERNAL causing event. "CAUSE only" and the ban on
  "effect" words invite reading the target noun as an effect, and the Rule 2 bare-root list then breaks the tie toward (a). This
  is not proved as the cause of any run, and it is not unique: variation under identical bytes stays large.
- Not a violated clear constraint on the producer's side alone. NAME-04 is general, and the 3.4 keep clause is literally
  "external".

## 4. Is there a SINGLE untested generic boundary?
- Already tested, and NOT discriminating:
  - N1 (next/CORRECTED_N1_PROMPT.txt) added "Name the target fact under Rule 3 using its full source-supported specificity. Keep
    causal specificity in the name". It was bundled with the fact_type-only sentence and a measurement reminder, and read only
    once (N1-1: specific name, brand regression).
  - The fact_type-only sentence alone (M-series D) and the Driver glossary sentence (2288) were each tested.
- Untested in isolation: ONE referent sentence stating that the name identifies the located target, and that a reason the
  source states for that target is part of its specificity, not a separate target (and not an effect word to strip).
  - It is the only boundary that separates the (a)-XOR-(b) explanation from the plain-variation explanation.
  - It is NOT literal law text. It is a clarification of NAME-01/04 for internal causes. Under NAME-19 it would be a general
    principle, but adopting it is an owner/law decision.
  - I have not drafted it, per your instruction.
- Narrowest question before any treatment: should the law treat a source-stated reason for a target, when that reason is the
  company's own event, as part of the target's name (NAME-04), or as a separate Driver? The key assumes the former; no FINAL line
  says so.
