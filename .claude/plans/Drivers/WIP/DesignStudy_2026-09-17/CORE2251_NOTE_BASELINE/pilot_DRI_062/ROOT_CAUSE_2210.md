# Root cause — source / task-meaning audit of the first example (Codex 2210; read-only; zero calls; no prompt edits)

## Verdict (not claimed as 100%)
The FIRST divergence is between the SOURCE and OUR EXPECTED ANSWER, not between the instructions and the model. The
measurement token we required (`Earnings Before Income Tax`) is one key author's resolution of a question the live law
does not decide. By the official standard (OD-9 token-set equality) measurement has matched the key in **0 of 9** outputs
under EVERY instruction version — including N1, which I had been counting as the one hit. Rewording was therefore
aimed at a target the design never defined. What would settle it is a design ruling, not another reading.

## 1. What the source asserts (original HTML table; arithmetic re-computed)
"Fiscal Q3 Reported to Adjusted Earnings Reconciliation" reconciles FOUR measures (Earnings Before Income Tax · Income Tax
Expense · Net Earnings · Diluted Net EPS) from Reported to Adjusted. Each adjustment row states that item's add-back to
each measure. Target row: 24.7 · 6.2 · 18.5 · 0.16. Checks: 24.7 − 6.2 = 18.5; 18.5 / 115.8 diluted shares = 0.1598;
column sums reconcile (6.6+24.7 = 31.3; 1.6+6.2−7.1 = 0.7; 5.0+18.5+7.1 = 30.6; 356.8+31.3 = 388.1).
So the four cells are four DIFFERENT quantities — the charge, its tax effect, its net-earnings effect, its per-share
effect — not four measurement versions of one quantity. The impairment charge itself is 24.7: an expense recognised
above the tax line (the statement of earnings lists "Impairments and (gain) loss on disposal of assets, net 25.1" above
"Earnings before income taxes"). That an expense amount is a before-tax figure is INTRINSIC to what an expense is; the
after-tax figure is the derived one that needs a qualifier. The column heading names the measure being reconciled.

## 2. What the live law says — nothing on this point
- grep of FINAL_DESIGN.md, ChannelContract.md, BUILD_AND_OPERATIONS.md, step1.md for pre-tax / before tax / after-tax /
  net of tax / column header / header path / table cell: no rule (only a period-signal mention and a `reported` state row).
- FINAL §5.3 lines 188-192: measurement = an open source-grounded qualifier set; never-drop covers "any number modifier"
  — "modifier" is undefined and the one example (`ttm`) is a basis. NAME-14 (line 100) lists versions: adjusted, diluted,
  constant currency. OD-12's own worked impairment example — "impairment charge $2B" → point +2000 (line 214) — carries
  no basis token. OD-11's "a value stated on two or more bases SPLITS" (line 213) is about GROWTH bases.
- The originally served reader prompt (v1) has no rule about tables, column headings or tax basis.
- Single-versus-multiple facts: the one-item contract allows more than one fact "only where the RULES already require a
  sibling or a basis split"; no rule says whether a multi-measure row is one fact or one per measure.

## 3. The lawful interpretations and the exact missing decision
- **I1 charge-itself:** one fact = the impairment charge, 24.7; the heading names the reconciled measure, not a version of
  the charge; before-tax is intrinsic → measurement [] (footnote 3's `Non-cash` optional under keep-when-unsure).
- **I2 selected-cell:** the label carries four numbers; storing 24.7 without its heading loses which was stored; never-drop
  / when-unsure-keep → heading required. (By the same logic `Non-cash` is required too — the key omits it.)
- **I3 several facts** (one per measure): the law is silent; the key and all nine outputs chose one fact.
- **Missing decision:** for a row that reports ONE item's effect on SEVERAL earnings measures — is the item one fact
  carrying its own gross amount (no heading), or the selected cell with its column heading as a measurement qualifier,
  and are the other cells separate facts?

## 4. The key's own record shows a choice, not a rule
- Key fact #2 `ambiguity_note`: "One line shows the same charge in four columns (24.7 before income tax, 6.2 tax, 18.5
  net, 0.16 per share), so I stored the single pre-tax charge bound to its own column header …" — a resolution (and "the
  same charge in four columns" is itself imprecise, §1).
- Census of all 165 key facts (32 distinct measurement tokens): this is the ONLY column-heading token. The three other
  tax tokens are words inside the number's own phrase or row label ("pre-tax proceeds of $104 million", "pre-tax
  investment losses of $20 million", "Losses from discontinued operations, net of tax"). No convention exists to follow.
  (157 of 165 key facts carry an `ambiguity_note`; the field is routine, its content here is what matters.)
- TRACKER row 146 "real missing measurement qualifier … never-drop rule" is a reviewer judgment (2026-09-15) applying I2.

## 5. All nine outputs against the key and against I1 / I2
| output | instructions | name = key | slice = key | measurement | = key (set) | under I1 |
|---|---|---|---|---|---|---|
| hist P1 | v1, flattened source | yes | no (brand) | [] | no | slice wrong |
| hist P2 | v1, flattened | no (`asset_impairment`) | yes | [] | no | name wrong |
| ORIGINAL | v1, flattened | no | yes | [] | no | name wrong |
| CORRECTED | v1, readable table | no | no | [] | no | name + slice wrong |
| R8 | + reviewed Rule 8 | no | yes | [row label] | no | name + measurement wrong (label is not a qualifier under either reading) |
| N1 | + Rule 2 paragraph | yes | no | [Non-cash, heading] | no (extra Non-cash) | slice wrong; heading redundant |
| C1 | readable source, v3 | yes | no | [noun phrase, detached suffix] | no | slice + measurement wrong |
| C2 | Rule 7 reorder | yes | yes | [Non-cash, complete predicate] | no | lawful + one unresolved-boundary token |
| C3 | Rule 8 rewrite | yes | yes | [] | no | **complete and correct** |
Measurement [] in 5 of 9 outputs = exactly I1. Under I1 the pilot's first example was already read correctly by C3.

## 6. Which fault explains which observation (kept separate)
| observation | explanation | evidence | status |
|---|---|---|---|
| generic name `asset_impairment` (P2, ORIGINAL, CORRECTED, R8) | Rule 2's bare-root example anchors the name | with the Rule 2 paragraph 4/4 specific, without 1/5; one-sided Fisher p = 0.040 | supported, small n |
| brand slice (P1, CORRECTED, N1, C1) | Rule 7 ladder order | empty 2/2 after the reorder vs 3/7 before; p = 0.28 | CANNOT decide |
| measurement ≠ key | the expected answer encodes I2; the law and every served prompt are silent; readers mostly return I1 | 0/9 under all versions, incl. the readable table (CORRECTED) and four Rule 8 wordings | explained by task underdetermination; NOT shown to be a model lapse |
| flattened one-line source | real delivery defect (proved earlier) | CORRECTED (readable table) still returned [] and the generic name | real, but does not explain the measurement mismatch |
| owner-chat relay | real runtime contamination | only wf_2c09bf95-b8a has two user messages | explains that one non-answer only |
| stored dates gp_2025-12-01_2026-02-28 | downstream period lookup | reader emitted FY2026 Q3 with null endpoints (lawful) | separate, downstream of the reader |

## 7. Proved / not proved / what would distinguish
- PROVED from existing evidence: the row's arithmetic meaning; the law's silence; the key token's uniqueness (1 of 165);
  0/9 measurement matches; which outputs equal I1.
- NOT proved: that a reader told I2 explicitly would reliably produce the heading — no served prompt ever stated I2 (C1–C4
  only implied it through never-drop); and I do not propose a call to find out.
- The distinguishing fact is a DESIGN RULING on §3's missing decision. If I1: the first example's reader output (C3) is
  already correct and the key's token needs review through its own governed process. If I2: it must first exist as
  design law (it is a product default about financial tables, not a wording detail), and the key must then say why
  `Non-cash` is not also required. Until then, scoring this field against the key measures agreement with one author's
  choice, not reader correctness.
- My own errors to record: I asserted "pre-tax required" in five expectations (C1–C4) without tracing it to law; I counted
  N1 as a measurement hit although it does not equal the key; I treated repeated failure as evidence about the model.

---

# Follow-up and corrections (Codex 2211; read-only; zero calls). The text above is preserved as written.

## A. Corrections to my 2208 proof
| my 2208 statement | correction |
|---|---|
| "the ONLY column-heading token among 165 key facts … no convention existed" | My probe counted the LITERAL token only. Reading all 69 key measurement tokens in context, the key also binds structural qualifiers: a header LINE ("Diluted net earnings per share:" → `Diluted`, source …000009 key[1]) and row labels (`Basic and diluted`, `net of tax`, `Adjusted` debt, `excluding net special items`). The target is the only token taken from a COLUMN heading of a multi-column numeric table, but binding table-structure qualifiers is an established key practice. Also: where the NAME states the basis the key leaves it out of measurement (`pretax_income` … "Pre-tax loss excluding net special items" → measurement `excluding net special items`) — a coherent application of "not captured losslessly by the name". |
| "0 of 9 … including N1, which I had been counting as the one hit" | Two different metrics. "1 of 7" was pre-tax-HEADING PRESENCE, disclosed as such from the start (N1 also carried `Non-cash`). "0 of 9" is exact token-set equality with the key. Neither corrects the other, and 0/9 is not independent semantic proof. |
| Fisher p-values (0.04 / 0.28) used as causal support | Withdrawn. The variants are adaptive, change several factors at once and mix inputs and runtimes. Raw association only: specific name 4/4 with the Rule 2 paragraph vs 1/5 without; empty slice 2/2 after the Rule 7 reorder vs 3/7 before. |
| "CORRECTED still returned [] → flattening does not explain the mismatch" | It proves restoration ALONE was insufficient; it does not show layout cannot contribute. |
| "the law is silent" (zero grep hits; OD-12's impairment example has no basis token) | A word search cannot prove silence in an OPEN rule. §5.3 deliberately covers ANY number modifier not captured losslessly elsewhere and resolves doubt with "When unsure, keep"; it need not enumerate tax bases. OD-12's example is a SIGN encoding, not a statement about measurement. Withdrawn as evidence. |
| "before-tax is intrinsic to an expense amount" | That is an accounting CONVENTION. Under the law's own test — is the modifier captured losslessly by the NAME — `restaurant_closure_impairment` does not state a tax basis, and the source itself prints the same label at 24.7 and 18.5. The C2–C4 rule sentence I wrote ("a customary association does not carry it") cuts against my own argument. I1 is weaker than I presented it. |
| "Under I1 … C3 is complete and correct"; "the key's token needs review" | Withdrawn. Source and law do not establish either. |

## B. The pivotal proposition, tested against the governing meaning
Does `restaurant_closure_impairment` intrinsically carry "before income tax"? NO field value states it: the name states the
cause (NAME-01), the unit states dollars in millions, the period states the quarter, the slice is empty. The source gives
two amounts for the same label that differ only by the column heading. Under §5.3:191 that heading is a number modifier
not captured losslessly elsewhere, and "When unsure, keep" resolves residual doubt toward keeping it. So binding the
heading is an ORDINARY application of the open rule — a semantic judgment the design delegates to the reader — not a new
product default. My request for an owner ruling on "I1 vs I2" is withdrawn: the exact example need not be enumerated.
What the law does NOT decide is a different, narrower point the key owners themselves raised: WHICH column is the item's
canonical value (24.7, 18.5 or 0.16). Whichever is chosen, the same rule says its heading is kept.

## C. The key-author task, traced (public answers and notes only)
| stage | what the key author was served | public output for this row |
|---|---|---|
| old key (units 1773–1943) | — | `asset_impairment`, **25.1**, measurement `['net']` — the statement-of-earnings line, a different row |
| source-only key owner, unit_2001 (whole event; reader-format answer; hard-class tags with the FULL law text quoted) | row tagged `measurement_wording` with NAME-14 + complete §5.3 incl. "losslessly" and "When unsure, keep" | `asset_impairment`, 24.7, `['Earnings Before Income Tax']`, no slice — chosen UNPROMPTED, and logged as an OPEN ISSUE: "The located quote presents all four for the same line and no quoted rule selects one; I stored the pre-tax charge and named the column in measurement rather than resolving the choice silently." |
| review of that open issue (Codex closeout packet, unit_2065 `FINDINGS_BY_EVENT.json`, decision REVIEW, owning clause Rules 3/5/8 and 3/7) | — | q1: "Bind the stored value to its actual pre-tax/after-tax/per-share meaning and preserve its qualifier. Do not mix table columns …" · q2: "The footnote says primarily Bahama Breeze, not wholly. Preserve the supported whole amount without attributing all of it to that component …" |
| closeout key owner, unit_2066 (Opus, high; whole event; earlier answers shown; BOTH row-specific findings above in its input; same flattened one-line exhibit) | as above | `restaurant_closure_impairment`, 24.7, `['Earnings Before Income Tax']`, slice [], open_issues [] — then signed |
So the topic WAS adjudicated, and the token was first chosen by a key owner on the general law alone (with the full §5.3
text and a hard-class flag), then preserved under an explicit row-specific instruction.

## D. Key task versus reader task — what the comparison actually proves
| | key owners | original reader (P1/P2) | C3 reader |
|---|---|---|---|
| model / scope | Opus, whole event, earlier answers shown | Sonnet, one located item | Sonnet, one located item |
| measurement rule text | FULL §5.3 quoted ("losslessly", "When unsure, keep") + NAME-14 | shortened Rule 8: "Any number modifier not captured by name/period/unit/slice/basis stays here" — no "losslessly", no "when unsure keep" | rewritten Rule 8 with both |
| row-specific help | hard-class tag `measurement_wording` on this row; at closeout the two reviewer findings naming the pre-tax binding and the no-Bahama-Breeze slice | none | none |
| source form | flattened one-line exhibit | flattened | readable tables, linked footnotes |
PROVED: for the two fields the pilot has been chasing (measurement heading, empty slice) the final key value was produced
by an author who had, for this exact row, information no reader ever received (a hard-class flag, the complete law text,
and at closeout an explicit instruction for each field). Reader-versus-key disagreement on those two fields is therefore
CONFOUNDED: it cannot separate "reader lapse on a delegated judgment" from "reader was not given what produced the key".
NOT PROVED: that the missing information is WHY readers omit the heading. The unit_2001 owner reached the heading with no
row-specific finding, so the general law can suffice for some reader — but that owner differed from the readers in model
(Opus), scope (whole event), law text (full §5.3) and the hard-class flag, all at once.

## E. Strongest evidence for and against the expectation-defect explanation
FOR: two key owners publicly recorded that no rule selects the column and that "another column choice is defensible from
identical evidence"; the final key value was written under row-specific reviewer instructions absent from every reader
prompt; the old key chose a different row (25.1, `net`) for the same item; five of nine outputs return [].
AGAINST: §5.3's open never-drop rule plus "When unsure, keep" support keeping the selected cell's heading; no field value
states the tax basis; the key binds structural qualifiers elsewhere and omits the basis only where the name states it;
the first key owner chose the heading unprompted; the reviewer note cites existing Rules 3/5/8, not a new rule. The
key's token is a lawful application of the general rule. I do NOT label the key wrong and do NOT promote C3 to a pass.

## F. Earliest divergence defensible without assuming either interpretation — and what stays unproved
The earliest divergence I can defend is at the TASK-DEFINITION boundary: the key for this row and the reader answers
were produced under materially different tasks (section D). That is a fact about the experiment, established from the
served artifacts; it explains why reader-versus-key comparison on these two fields is not a clean measure of reader
correctness. It does NOT identify why six of seven readers omit the heading. **The root cause of the heading omission
remains UNPROVED.** The exact unresolved proposition: *given only the general rules a reader receives (no hard-class
flag, no row-specific finding), is binding the selected cell's column heading a judgment a Sonnet one-item reader can be
expected to make — so the omissions are reader lapses whose cause (model, scope, source form, rule text) is unknown — or
does the reader task lack information the key task had?* Existing evidence cannot decide it: every key answer was produced
WITH that information and every reader answer WITHOUT it, and the key owners also differed in model and scope. The fact
that would distinguish them is an answer produced with exactly one of those differences varied; I propose no call.

---

# Provenance correction (Codex 2212) — the REAL history of this one key answer

Everything above is preserved as written. This section corrects sections C and D only. Printer: `exec/key_chain_probe.py`
(read-only; native Workflow state files and child transcripts of session 5ae9b86b…; nothing rerun).

## G. What I got wrong in C and D

| My 2209 claim | Status | Fact |
|---|---|---|
| "source-only key owner, unit_2001" is the first owner | WRONG ARTIFACT | The unit_2001 script carries 2 `SYNTHETIC-CLOSURE-FIXTURE-2000` markers; of the 8 run ids stored there for this event only 1 exists natively. It is a test fixture. Its row-3 item is an exact copy of the real 2026-09-10 answer below (`synthetic` prints `2 | 1 of 8 | True`). |
| the row was served a hard-class tag `measurement_wording` | WRONG | No owner input attaches any tag to row 3 (`row3tag`: False ×5). The tag text served is the generic TAG RULES section. The per-row tag lists are the owners' OWN OUTPUT (`review[].hard_classes`). Later inputs do carry that tag, but on rows 1 and 2 of an earlier answer. |
| leads b1/b2 were Opus | WRONG | The capture files record the PARENT session model. The child transcripts record `claude-sonnet-5` for all three review-lead calls (`leadmodels`). |
| old key `asset_impairment` 25.1 `['net']` = "the same item, a different row" | UNPROVED, withdrawn | I never proved that fact was bound to THIS located item. It is a statement-of-earnings fact in an older key, nothing more. |

## H. The actual chain for this row (scan: 1,896 native Workflow state files; every run naming this event and this row label; time order)

"Served" = the heading appears as a measurement value anywhere in that run's input. All owners are whole-event (six rows), Opus/high,
`lean-probe`, one user message, zero tool calls, CLI 2.1.261, and all six got the SAME measurement-rule text (`rulesha`: 1 distinct
segment, with "losslessly" and "When unsure, keep").

| # | UTC | run | stage | child model | served heading | answer-specific help in input | name | value | slice | measurement | returned sha |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 09-10 19:09 | wf_edb6e1f8-060 | source-only key (unit_1997 ledger, hash matches) | opus-5 | no | none; NO leads at all | asset_impairment | 24.7 | — | **[Earnings Before Income Tax]** | 3cd2b64ed954 |
| 2 | 09-10 22:57 | wf_5a97f47b-3d5 | review lead b1 | sonnet-5 | no | none | asset_impairment | numberless | brand | — | 4e04d1ec9b2a |
| 3 | 09-10 23:02 | wf_a2c82924-5bb | review lead call (matches neither lead the owners describe; serving unproved) | sonnet-5 | no | none | asset_impairment | 24.7 | — | — | 0a9250750018 |
| 4 | 09-11 00:21 | wf_32c071d0-d98 | review lead b2 (attempt 2) | sonnet-5 | no | none | restaurant_closure_impairment | 24.7 | brand | — | ef991ce5286a |
| 5 | 09-11 04:55 | wf_2b8ca550-209 | source-only key (rebuild) | opus-5 | no | leads b1, b2 (neither has the heading) | restaurant_closure_impairment | 24.7 | — | **none** | 6bd81f43566b |
| 6 | 09-11 18:42 | wf_662c5c9f-6e2 | correction | opus-5 | no | #5's own answer + decisions ("PRESERVE" name and level) | same | 24.7 | — | **none** | 66ad104bd7ee |
| 7 | 09-12 06:16 | wf_6623c422-65b | final decision | opus-5 | no | #5 and #6 answers | same | 24.7 | — | **none** | 3dc5f87702d5 |
| 8 | 09-12 15:44 | wf_282cca7d-9a4 | final settlement | opus-5 | no | #7 answer + review lead "…the quarter column is taken and the choice recorded." | same | 24.7 | — | **[Earnings Before Income Tax]** | 34db06495c27 |
| 9 | 09-12 18:48 | wf_75188ad4-eb0 | closeout | opus-5 | **YES** | #8 answer + "Bind the stored value to its actual pre-tax/after-tax/per-share meaning and preserve its qualifier" | same | 24.7 | — | [Earnings Before Income Tax] | 2808b861cece |

The two later signature runs (09-13, 09-14) were served the heading and return a signature only.

**First real appearance:** run #1, 2026-09-10 19:09 UTC, an Opus whole-event owner with no leads, no review notes, no row tag, and no
heading in its input. Its note, in full: "The quote shows four side-by-side figures for this line (24.7 pre-tax, 6.2 tax, 18.5 net, 0.16 per share) with no
rule selecting one, and the brand attribution sits in a footnote outside this quote, so I took the pre-tax charge, marked its column in
measurement, and coined no slice." So the heading does NOT originate from review help.

## I. What this changes

1. **"The key author had help no reader got" — withdrawn as an explanation of the heading.** Run #1 produced it with none. Help
   (categories per Codex): source facts withheld from the reader — none found for this field (the heading is in the served packet; reading
   N1 copied it). General rule text — owners got §5.3 verbatim, readers a paraphrase. Source-derived answer-specific help — only
   runs #8 and #9, which a tested reader need not receive.
2. **The omission is not reader-specific.** Opus owners not served the heading: 5 → kept 2, dropped 3 (`counts`), under the verbatim
   law text. Sonnet one-item readers: kept 1 of 7. Different tasks, so the two rates are not compared.
3. **These five are NOT five independent samples.** #6 and #7 were shown the previous empty answer and repeated it; #8 switched in
   the same call that first carried the "choice recorded" lead. The only two owner runs with no earlier owner answer in view are
   #1 (kept) and #5 (dropped). They differ by #5 having two Sonnet leads, both without the heading. One against one proves nothing
   about why.
4. **Every owner saw the basis; the unstable step is writing it down.** All five unserved owner notes call the figure "pre-tax" in
   their own words, and all five raise an open issue on which column the fact should carry (wordings differ; none resolves it).
   In all six owner runs, the owner's own output tag `measurement_wording` on row 3 coincides exactly with keeping the heading
   (`owntags`: 3 tagged and kept, 3 untagged and dropped). That is a correlation between two outputs of one call, not a cause.
5. **The final key value is path-dependent:** kept, dropped ×3, kept after a review lead, then preserved under an explicit note.

## J. Root cause — still UNPROVED, now narrower

Ruled out as the sole cause by existing records: Sonnet versus Opus, one-item versus whole-event framing, reader paraphrase versus
verbatim law, and missing answer-specific help. What is common to every configuration that dropped the heading is only the law text
and this source shape: one row, four co-located figures, a column heading that selects which. The records cannot separate "the rule
decides this and both models apply it unreliably" from "the rule leaves this shape open". Codex's ruling stands that the open
never-drop clause supports keeping it. No record here shows why a reader omits it.

---

# Semantic audit (Codex 2213) — what object the record represents, and whether "before tax" is already in the name

Read-only. Printer: `exec/semantic_audit_probe.py`. Codex checks the accounting premise independently; I do not rest on it.
Codex's earlier never-drop reading is treated here as a hypothesis to be challenged, not as law.

## K. The object, settled separately from the choice of number

Source facts (served evidence only):
- K1. The table is "Fiscal Q3 Reported to Adjusted Earnings Reconciliation". Its four column headings are four EARNINGS MEASURES. Each
  adjustment row's cell is that row's adjustment to that column's measure (`arith`: reported + total adjustments = adjusted; the two
  Q3 adjustment rows sum to the total; 24.7 − 6.2 = 18.5).
- K2. One row has NO pre-tax cell at all: "Income tax adjustments and benefits | — | (7.1) | 7.1 | 0.06" (`taxrow`). So the columns are
  effects on measures. They are not, by construction, four versions of one row amount.
- K3. The row label and footnote 3 name CHARGES ("Non-cash asset impairment charges …"). The statement of earnings carries the
  impairment line among operating costs, above "Earnings before income taxes" (`statement`).
- K4. The source uses the same label for a non-gross figure: prose "$0.16 of impairment due to restaurant closures", and the outlook
  table row with that label = 0.16 (`label_uses`).

Law:
- The served role text: the item's `raw_label_or_claim` "names the one target meaning to interpret". The target is the labelled ROW
  meaning, not a cell. So "a selected table-cell assertion" is not the object handed to the reader.
- DU-05 (FINAL_DESIGN.md:113): "**action_event** = a discrete thing that happened (decision, transaction, incident, approval, one-off
  charge)"; DU-06 (:114) bare-root default "corporate_restructuring/asset_impairment → action_event". NAME-01 (:86): "the name contains
  the cause only". Per-lane matrix (:261): an action's level is stored "only when stated".

**Result:** the object is the one-off charge itself, as a happening; its level is the stated size of that happening. "The charge's
effect on a reported measure" is not a Driver object in this design (a measure such as pre-tax earnings is its own standing variable;
effect words are barred from names, :101). DU-05/06 with the one-target clause settle this. They do NOT settle which figure is "the
size", nor whether the size needs a basis word.

## L. Is "before tax" intrinsic to `restaurant_closure_impairment` = 24.7?

The test the law itself supplies: measurement is part of the full series key (:299), and §5.3 (:191) lets a modifier go only when it is
"captured losslessly by name, period, unit, slice, or sequential-basis logic". A modifier is carried by the name only if the name's
meaning fixes it, so that no second stated size of the same happening could sit under the same name, unit, period and slice.

**Strongest case that it IS intrinsic (empty measurement lossless).** K2 and K3: the charge is an operating expense recognised above
the tax line, so the charge's own amount IS 24.7. The 18.5 is not "the charge after tax"; it is the charge's effect on Net Earnings,
which is another measure, and effects are not stored under this Driver. Then no second size exists under this name, and the heading
names the reconciled measure, not a version of the charge. On this reading an empty field loses nothing.

**Strongest case that it is NOT carried (the basis must be kept).**
1. How the design lets a name carry accounting meaning is NAME-08 (:93): standard financial phrases kept whole (`net_income`,
   `operating_margin`, `earnings_per_share`). Control: `net_income` carries "after tax" because the phrase itself denotes it; yet
   `earnings_per_share` still needs `diluted` and `adjusted` in measurement (NAME-14, :100) because the phrase does not fix them. By that
   control a basis is intrinsic only when the standard phrase denotes it. "impairment" denotes WHAT happened (a write-down). It does
   not denote the tax basis at which a release sizes it.
2. K4: in this very source the label is applied to a non-gross figure. The label alone does not mean "gross amount" here.
   Limit: the per-share figure would take a per-share name (NAME-13, :99), so the only same-name, same-unit rival size is the 18.5.
3. The design's stated rule for an unmarked default: "Empty measurement is legal and never implies GAAP" (:191; NAME-14 :100 says the
   same). The customary basis is never to be inferred from emptiness. "Charges are sized pre-tax unless said otherwise" is exactly such
   a custom.
4. Control from other sources already in the locked key (`taxcontrols`): a one-off `minority_investment_sale` 104 carries `pre-tax`,
   and `investment_income` carries `pre-tax`, because those sources WROTE the basis ("pre-tax proceeds of $104 million"). Issuers state a tax basis on one-off amounts, so it
   is not redundant to them. This is a control on source behaviour, not an appeal to the key author.

**The decisive difference.** Whether a net-of-tax size of a one-off charge is a storable level of the SAME Driver. If yes, the tax basis
is a measurement version exactly like `diluted`, and never-drop applies. If no, nothing remains to keep. No live clause states this. The
law's own tie-break does apply to a reader who cannot tell: "When unsure, keep." (:191). So the strongest reading after challenge is
still KEEP, on points 1 to 3 and the tie-break. It is a reading, not a proof, and it is NOT 100%.

## M. Keeping the basis versus requiring the whole span

Support for keeping the basis is not support for the exact span. §5.3 (:189) has the reader copy exact source words; this source has no
word "pre-tax", so the basis can only be kept through the column heading. But (:190) "A maximal contiguous qualifier span = ONE token"
speaks of contiguous QUALIFIERS. In "Earnings Before Income Tax" the qualifier is "Before Income Tax" and "Earnings" is the column's
measure noun. The law does not say the noun must ride along. A reply of `Before Income Tax` would preserve the basis verbatim and would
still fail set equality with the key token, and no write-time merging exists (:192). Reading N1 kept the whole heading plus `Non-cash`
and also fails set equality. No grading change is proposed; this only bounds what a "miss" on this field means.

## N. Observed output inconsistency (kept apart from any hidden chronology)

`keypresence`: three reader replies (ORIGINAL, CORRECTED, C3 attempt 2) and three Opus owner replies leave the measurement key OUT of the
fact; the parser turns that into an empty list. Those three Opus replies say "pre-tax" in their public note. That proves one response
held information its own record omits. It does not show when, or whether, a decision about the field was made. Sparse defaults cannot
be the whole story: R8, C1 and C2 DID fill the field, with other words, and still left the basis out.

## O. Plain statement

- **Proved by records:** the object is the one-off charge (DU-05/06). The table's columns are effects on four earnings measures. The
  source sizes this same labelled impairment at more than one basis. Both model tiers, under verbatim law, sometimes write the basis
  and sometimes do not, while showing in notes that they saw it. The key elsewhere stores a tax basis when a source writes one.
- **Hypothesis, not proved:** that the design means a net-of-tax size to be a version of the same Driver (so the basis must be kept).
  Equally unproved: that it means the gross charge only (so empty is lossless). Also unproved: WHY a given reply omits it.
- **What would distinguish them, without any model run:** one design-owner sentence on whether a one-off charge's net-of-tax amount is
  a storable level of the same Driver; and whether, when the only source words for a basis are a measure heading, the measure noun
  belongs in the span. Codex's accounting check bears on the first only if it shows issuers never size a charge net of tax.

---

# The claimed design gap, checked under existing rules (Codex 2214)

Read-only reasoning. No new printer. Nothing above is edited; where this section withdraws a sentence, the sentence stays as written.

## P. Withdrawn from sections K–O and from my 2210/2211 replies

- P1. "An effect on a reported measure is not a Driver object" and any gross-only limit on levels. NAME-15/16 (:101) bars effect WORDS IN
  NAMES only. DU-05/06 (:113–114) choose the lane. The matrix (:261) admits stated levels and defines no gross-only level. No clause
  entails the limit. It was mine.
- P2. My use of "never implies GAAP" (:100, :191) as a general rule against every unmarked basis. It fixes what an absent version token
  means with respect to GAAP. It does not stop a standard phrase from carrying intrinsic meaning (NAME-08, :93).
- P3. "Both model tiers under verbatim law." Checked prompt by prompt: the verbatim never-drop sentence and "When unsure, keep" are in the
  Opus owner prompts only. They are in none of the three Sonnet review-lead prompts and none of the seven valid reader prompts (from R8
  on the reader prompt carries a paraphrase containing the word "losslessly"). The two tasks must not be pooled.
- P4. The contaminated C3 attempt is a transport failure. It produced no reader fact and is not a measurement-key omission. Valid reader
  facts that leave the key out: three of seven (ORIGINAL, CORRECTED, C3 attempt two).
- P5. The `Before Income Tax` span argument in section M is HYPOTHETICAL. No reply returned that span and nothing tested it.
- P6. My control (d) in section L shows only that a basis word, when a source writes it, is storable. The existence of a qualified version
  does not settle what the unqualified name denotes. Withdrawn as evidence that the unqualified name is ambiguous.

## Q. Gross-only: required, allowed but unstated, or my addition?

Rules used together: one source-born cause (NAME-01 :86, NAME-03, NAME-09), stated level (:261), measurement versions (NAME-14 :100),
lossless preservation and unsure-keep (:191), per-share naming (NAME-13 :99), no write-time merging (:192).

- **As a limit on what may be stored as a level: my addition.** The source attributes all four cells to this one cause and states each.
  Nothing forbids storing the 18.5 as a level of the same action, qualified by its heading. The 0.16 would take a per-share name.
- **As the meaning of the UNQUALIFIED name: allowed but unstated.** The design has a mechanism for intrinsic meaning without literal words
  (NAME-08). Codex's accounting check (impairment measured as carrying amount above fair value; tax adjustments shown separately in
  non-GAAP reconciliations) and the source (impairment line above pre-tax earnings; a separate tax-adjustment row) support reading "the
  impairment" as the gross measured loss, with the tax consequence apart. They do not show issuers never size a charge net of tax, and
  no clause names this term.

Consequences for the two competing records of 24.7:
- **Headerless** is lawful IF the name carries the gross meaning, because then the heading restates carried meaning and the condition of
  :191 ("not captured losslessly by name") is not met, AND the reader is not unsure. The store stays consistent as long as any
  net-of-tax amount is stored qualified, which :191 requires anyway since net-ness is plainly not in the name.
- **Qualified** (24.7 plus the heading) is lawful under EITHER reading: if the meaning is already carried the token is redundant, not
  forbidden (open set, :188; unsure-keep, :191). It is the only record lawful under both readings.
- The two are different series keys for one fact (:192, :299); only a read-time view can join them.

So the key's token is a justified and always-lawful representation. Existing rules do not show it to be the uniquely required one, and
the exact span is the key owner's selection.

**Against headerless-sufficient, from the records themselves:** the three Opus replies that left the field out had the verbatim rule, and
their own public notes say another column is "defensible" as the stored value. A reply that holds that premise cannot also hold that the
name fixes the column; under the rule it was served, its own premise requires the token. That is an inconsistency between a reply's note
and its fact fields. It says nothing about when any decision was made, and it does not extend to the Sonnet readers.

## R. How far the records support each diagnosis

1. **An actual source-meaning error on the tax basis: not supported.** Every valid reply that stored a number stored 24.7 million dollars
   for this charge in the third quarter of fiscal 2026. That is what the source says under either reading. A headerless record is at
   most incomplete, never false. (Other words that R8, C1 and C2 put in the field are a separate, earlier-recorded matter.)
2. **An unsettled representation requirement: supported, in this exact form.** The general rule exists and applies: keep unless carried
   losslessly by the name; keep when unsure. What is unsettled is one semantic premise, whether the unqualified name denotes the gross
   amount. This is not a missing rule and I do not claim one.
3. **A raw output omission relative to a justified requirement: supported only for the three Opus owner replies** (verbatim rule served,
   own note concedes the column is a free choice, fact fields omit it). For the Sonnet reader replies it is not established: they never
   had the verbatim rule, they carry no notes, and the requirement is conditional.
4. **An exact-key mismatch without independently proved financial error: fully supported.** None of the seven valid readings equals the
   key's token set. N1 holds the key's token plus one more. None is shown financially wrong on the tax basis.

## S. Narrowest cause statement

On this item the grader's failure in the measurement field is an exact-key mismatch on a conditionally required qualifier: the replies
lack the key owner's column-heading token, the token is justified and always lawful, existing rules do not make it uniquely required,
and no reply is shown to misread the source.

**The unproved causal link:** why a given reply leaves the token out. The model may have judged the basis carried by the name, may never
have treated a column heading as a qualifier, or may have left a sparse field unset. Records show outputs and, for Opus, public notes;
they do not show that judgment. A new owner rule would set future requirements. It could not explain an earlier reply, and I do not
ask for one. My 2211 "what would distinguish" item is withdrawn as a route to the cause.

---

# What the saved failure evidence on this item actually is (Codex 2215)

Read-only trace of the real grader judgments behind the saved P1/P2 verdicts for packet #062 in `A7_CORRECTED_SCORE.json`. Native grader
runs are in session 5ae9b86b…; printer (claims helper, outside the pilot): `sendgate/g2_target_trace_2213.py`. Aspect order below:
name meaning · state · favorability · growth basis · lane · record matches source · slice.

## T. Two limits on section Q–S carried forward (both conditional until the premise is settled)

- An Opus note that another column is "defensible" may mean defensible WITH a qualifier. It does not logically prove the unqualified name
  lacks a fixed basis. My diagnosis R3 is therefore conditional, not established.
- "The qualified record is lawful under either reading" is not true of every served variant: the C3 (and staged C4) reader rule says "A
  header that only restates meaning already carried in those fields is not copied." Under that served rule, copying the heading is
  lawful only if the basis is NOT already carried.

## U. How the grader was built for this item

- Each question shows the judge ONE produced record plus a reference card holding only `quote`, `reference_name` ("Impairment due to
  restaurant closures3") and `values` (24.7). The card carries NO key name, slice or measurement (`card`). The role text is "judge ONE produced
  record against the reviewed record of the SAME claim, using only this event's evidence. Judge meaning only." The name aspect is judged
  against the card's reference name (the source's row label, not the key's driver name); slice and record-matches-source are judged
  against the source. Seven aspects, booleans only, no reasons.
- Two Sonnet judges (lanes G1a, G1b) answer the same prompt bytes. On this item the saved verdict keeps the aspects on which the two agree
  and omits the two on which they differ (the combining rule itself is in the scorer, which Codex is reading).
- The question object is bound to the saved answer exactly: produced record equals `answers[sid].facts[2]`, produced quote equals the card
  quote, and the P2 question is byte-identical in its first and last round (`binding`: True True True for both legs).
- No aspect names measurement. The only aspect that could reach an omitted tag is `record_matches_source` ("whether each field it leaves
  out is one whose declared default is true"). The judges' instructions carry no never-drop rule; their one measurement sentence is "An
  empty measurement list asserts nothing about an accounting standard." (`instr`).

## V. Evidence table

| Flag on this item | Actual deciding check | Served inputs and raw result | Independent conclusion | Remaining uncertainty |
|---|---|---|---|---|
| P1 "meaning incomplete" (state, record matches source absent) | Two Sonnet judges, lane G2-040, 2026-09-13 15:54 and 15:58 UTC; never re-asked | Record: specific name, Bahama Breeze slice, empty measurement, 24.7. G1a: all seven TRUE. G1b: state FALSE, record-matches-source FALSE, rest TRUE | The two absent aspects are a judge-versus-judge DISAGREEMENT on identical bytes. Not a finding against the reading. One judge accepted the whole record, empty measurement included | Which judge is right; no reasons exist |
| P1 slice TRUE although the key slice is empty | Same two judges, both TRUE; instruction predates the action-scope sentence | Judges decide whether the record's population "is the one the source names"; they never saw the key's slice | The semantic grader accepted the brand slice that the key rejects. A key-versus-judge conflict, unresolved. Not proof of a bad judge, stale cache, bad pairing or wrong key | Whether the later instruction would change it; not asked |
| P2 name FALSE, slice FALSE, record-matches-source FALSE, wrong-accept | Re-asked 2026-09-15 06:38 and 06:41 UTC, lane G2-004, instruction now says "For an action, empty means no applicable part; a source-stated applicable part still belongs in this field." Both judges identical. The 09-13 replies (returned as strings) also said slice false and record false | Record: broad name, EMPTY slice, empty measurement, 24.7 | Both judges call the empty slice wrong, while the corrected key has an empty slice: the same conflict from the other side. The record-level FALSE cannot be assigned to measurement, because name and slice are already false | No reasons exist |
| `measurement-OD-9` mismatch (both legs) | CODE token-set comparison of the record's tokens with the key's; my inventory diagnostic uses the scorer's own token function and reconciles with the official aggregate counter. The official score file holds no per-row measurement row | Produced `[]` versus key `[Earnings Before Income Tax]` | No model ever judged the tax-basis omission. It comes solely from token comparison | Codex's own read of the scorer |
| P1 value and slice field differences | Code comparison | Value differs only in the scale words ("in millions" versus "millions"); slice differs as above | Not a reading error about the amount | none |
| Seven fresh readings (ORIGINAL … C3 attempt two) | NO semantic grader. The pilot session ran reader workflows only (`fresh`: 6 workflow names, 0 grader). They were compared by code with the key, plus my manual notes | — | A manual expectation is not a model judgment, and neither is source truth | — |

## W. Does this change the diagnosis?

- **Tax basis: strengthened, same direction.** The failure is an exact-key mismatch produced by token comparison alone. No semantic
  judgment of the omission exists, and one judge returned record-matches-source TRUE on a record with empty measurement.
- **Slice: changed.** The pilot treated "empty slice" as the fixed target because the key says so. The established semantic grader judged
  the opposite in every raw answer on this item (brand slice true ×2; empty slice false ×4). The slice field mismatch on this item is a
  key-versus-judge conflict, not an established reader error.
- **P1's FAIL** rests on two judges disagreeing, which is a grader-repeatability matter.
- The only historical flag on this item where key and judges agree is P2's broad name (false in three of four raw answers; the specific
  name true in both).
- The causal link for the omission stays unproved. UNION-leg rows for this item (one recall miss, two extras classed key-miss) were not
  traced; they are outside the P1/P2 request.

---

# UNION path traced, and corrections to section U–W (Codex 2216)

Read-only. Existing bytes only; no scorer, route or model rerun. Claims helper (outside the pilot): `sendgate/union_target_trace_2214.py`.

## X. Corrections to sections U–W (the sentences above stay as written; these supersede them)

1. **Wording.** Correct statement: no tax-basis-SPECIFIC semantic finding or reason exists. I must not say "no judge ever judged the
   omission": `record_matches_source` explicitly reaches omitted defaults. A whole-record boolean cannot identify its reason. One TRUE
   covers the whole presented record; it does not establish the key wrong.
2. **P1.** The target's `meaning_incomplete` arises from state and whole-record disagreement. It carries no confirmed wrong-accept flag.
   It is NOT the cause of the whole P1 leg's FAIL. Codex's unchanged pure-comparator replay (his file ROOT_CAUSE_PILOT_CHECK_COVERAGE.json,
   not re-derived by me) finds 9 of 13 exact checks equal in P1 (two scale spans, scope, measurement differ) and 12 of 13 in P2
   (measurement differs); my inventory's field lists agree (four fields, one field). Both dry routes accepted. P2's wrong-accept is driven
   by its negative established meanings, separate from exact measurement equality.
3. **Scope.** Our empty-scope position was reasoned from the source, not copied from the key: footnote three says the charges are
   "primarily related" to Bahama Breeze closures, so assigning the ENTIRE 24.7 to that brand overstates. Judge disagreement does not settle
   that source question. Status: CONTESTED, with that rationale retained.
4. **Prompt versions.** Among the six G2 judge runs there are THREE distinct full prompt byte sequences and TWO instruction versions
   (`g2versions`: 3 2), not four versions. The instructions' POPULATION AND MEASUREMENT paragraph also carries the contiguous-qualifier
   rule (in all six), so the empty-list sentence is not their only measurement instruction. Full never-drop wording is absent from all six.
5. **My own error in W/V.** I wrote that no per-row measurement record exists. The trace's `counter_events` DO hold per-row events for this
   target: P1 `mismatch:value:level_low`, `mismatch:value:level_high`, `mismatch:slice`, `mismatch:measurement-OD-9`; P2
   `mismatch:measurement-OD-9`, `verdict:driver_name_meaning`, `verdict:slice_vs_menu` (`events`). They are code comparisons and saved verdicts.

## Y. The UNION path for this target

| Step | Exact evidence | What it establishes |
|---|---|---|
| 1. Combination | `origins`: union record 0 = P1#0 + P2#0 (identical, collapsed); records 1–3 = P1#1–3; records 4–6 = P2#1–3. Scorer `dedup_items` collapses only records with the same identity key | The two impairment records differ (name, slice), so BOTH are kept: union#2 (specific name, brand slice) and union#5 (broad name, empty slice). Deliberate non-combination of differing records |
| 2. Match question | G1 question Q838983db45a9db6d, gold 2, candidates 0,2,3,4,5,6; run wf_39c1eba1-65b, 2026-09-13 05:19 UTC, two blind Sonnet lanes. The instruction says "If several produced records attempt one claim, list them all." Both lanes returned `[2, 5]`. (In the single legs both lanes returned `[2]`.) | Both judges recognised BOTH records as attempts at the key's impairment claim. No source fact was lost and identity was not disputed |
| 3. Credit rule | `a7_g1_build.validate_merged`: only creditable isolated pairs become a ruling; every other gold row is projected as `None`, which the scorer documents as a decided miss. Two lanes equal and non-empty but one gold ↔ two records is the code's `non_bijective_contested_miss` branch (label read from code; not found saved) | Saved ruling gold 2 → `None`; trace row `recall_miss`, `ruling_present` true. The miss is created by the one-to-one credit rule meeting two kept records |
| 4. Extras | Both records were route-written and unmatched, so each became an extras question. Buckets offered: duplicate (only versus `other_records` = records this run PAIRED with a reviewed claim; here two, neither an impairment), key_miss, unsupported. The judges were shown the reviewed card "Impairment due to restaurant closures3". Raw buckets: union#2 unsupported ×2 (09-13), then key_miss ×2 (09-15 00:02/00:05, saved). union#5 duplicate ×2 (09-13), key_miss ×2 (09-15 00:59), key_miss ×2 (09-15 06:07/06:09, saved) | `key_miss` here does NOT show the key lacks the claim: the reviewed set visibly carries it. With the pair voided, "duplicate" had no eligible comparator and "unsupported" is false, so key_miss is what remained. The 09-13 answers differ from the later ones under a changed instruction |

Classification of the three UNION flags: none is loss of a source fact. All three follow from deliberate non-combination of two differing
records plus the one-to-one credit rule. None is a disputed comparison with the key's field values (no field comparison runs on an
unmatched pair). One underlying condition surfaces as three flags.

## Z. Causal table for this one example

| Where | Flag | Exact deciding condition | Status |
|---|---|---|---|
| Source input | flattened reconciliation table in the original served text | table geometry lost; re-rendered in attempt A1 | PROVEN input defect; not sufficient alone (A1 pair still failed) |
| P1 | meaning_incomplete | two judges differ on state and whole-record, identical bytes | grader disagreement; no wrong-accept; no reason recorded |
| P1 | exact-field differences (4 of 13) | code comparison: two scale spans, scope, measurement | scale words trivial; scope CONTESTED; measurement see below |
| P2 | meaning_false + wrong-accept | both later judges: name false, slice false, whole-record false | broad name: key and judges agree (name underspecificity OBSERVED). Slice: CONTESTED. Whole-record: reason unknown |
| P1, P2 | measurement-OD-9 | code token-set comparison, `[]` versus the key token | exact-key mismatch. Tax-basis NECESSITY unproved; omission CAUSALITY unproved |
| UNION | recall miss + two key_miss extras | two differing records kept → both judges link both → non-bijective → no credit → extras bucketed | scoring-rule consequence of non-combination; not a lost fact |
| Fresh readings (8 calls, 7 valid, 1 transport failure) | compared by code with the key plus manual notes; no semantic grader | specific name after the Rule 2 paragraph in 4 of 4 (before: 0 of 3); slice empty 4 of 7; heading present 1 of 7 | TESTED-INTERVENTION evidence for the name only (adaptive variants, not a controlled test). C2, C3 executed; C4 staged, unrun |
| Later | period lookup (FY2026 Q3 → wrong window) | separate consumer/data defect | separate, deferred |

No cause is confirmed merely by model agreement, key agreement or a correct schema. **Smallest remaining uncertainty:** whether the
unqualified name already carries the gross (pre-tax) meaning. Everything about the measurement flag turns on that one premise, and no
record here shows why any reply left the token out. This is a negative result on the "100% root cause": it is not established.

---

# Correction to section Y–Z: the extras labels were NOT forced (Codex 2217)

One bounded correction. Sections Y and Z stay as written; where they say or imply the following, this supersedes them.

## AA. What I overclaimed

- Withdrawn: "key_miss is what remained" and "one underlying condition surfaces as three flags", wherever they imply the labels were forced.
- The served extras instructions say "choose exactly one, or null", and "null is a lawful answer and you must never guess". They also say "the
  produced records of the OTHER questions in this event are NOT comparison records". The impairment reference card was present. So key_miss
  was not a required fallback. By its own definition it additionally needs "a real claim of this source that the reviewed set does not
  carry". The judges chose key_miss and gave no public reasons.
- Also withdrawn: "unsupported is false". The match step establishes that both records are ATTEMPTS at the same claim. It does not establish
  that every field of either record is correct, so it cannot prove that either.

## AB. The causal chain, as far as it is proven

differing records retained → a one-to-many match gets no recall credit → two unmatched records are sent for extras judgment → separate
historical model judgments return key_miss, reasons not recorded.

- PROVEN mechanism: the first three links (the recall flag, and why two extras QUESTIONS exist).
- SEPARATELY OBSERVED judgments: the two key_miss BUCKETS. They are not mechanically determined by the mechanism.
- No financial fact was absent from the reader outputs. That does not prove every returned field correct. Scope and tax basis stay
  contested and unproved, as recorded above; nothing here decides them.
- This is a proven match/credit mechanism plus separately observed judgments. It is not one proven cause for every flag.

Codex's own source-state reading, recorded as his: the reported third-quarter charge is distinct from the fourth-quarter closures still to
come, so `occurred` describes the charge. That is a source-based reading. It is not proof of why one P1 judge returned state false.

---

# Owner-ordered deep dive (owner order 2026-09-20; Codex 2218)

## AC. Disclosure: six think-aloud diagnostics were launched BEFORE Codex 2218 arrived

Under the owner's order I launched six Sonnet children at 2026-09-21 00:08 UTC from a clean notification turn. Codex 2218, which asks
for a different method, arrived after that. Method used: the served prompt plus ONE addendum placed before `[BOUNDARY]` asking for the
JSON first and then short answers to Q1–Q7 (neutral) or Q1–Q8 (Q8 asks about a column heading). Codex is right that this puts "JSON
plus prose" against a frozen request that says "Emit only the JSON object", so it alters the task. These six are therefore labelled
DIAGNOSTIC: not readings, never graded, not the baseline. Evidence: `diag_think_aloud_20260920/` (builder, launcher, prompt hashes,
`DIAG_LAUNCHES.json`) and `exec/evidence/<run>/`. Delivery checked for all six: claude-sonnet-5, CLI 2.1.278, one user message, no
owner-chat relay, zero tools, de-framed body equal to the built prompt. Native reader-style calls on this example: 8 → 14.

| identity | rules | name | slice | measurement |
|---|---|---|---|---|
| ORIG-N1 wf_849db539-6ac | original | asset_impairment | [] | [] |
| ORIG-N2 wf_d81fa75c-1ab | original | asset_impairment | brand | [] (also emitted period_end_date) |
| ORIG-P1 wf_a27505d8-dd5 | original | asset_impairment | brand | [] |
| C3-N1 wf_0873a0c8-d8a | C3 | restaurant_closure_impairment | [] | [Earnings Before Income Tax] |
| C3-N2 wf_6deddb56-2a2 | C3 | restaurant_closure_impairment | [] | [Earnings Before Income Tax] |
| C3-P1 wf_1090204b-5c8 | C3 | restaurant_closure_impairment | [] | [Earnings Before Income Tax] |

Under C3 plus the addendum all three equal the key on every compared field. The one clean C3 reading (no addendum) left measurement
empty. Whether the addendum caused the difference or the clean reading was one draw is NOT settled.

REPORTED justifications (what the children said; not proof of how the answer was generated):
- Which number: all six say no rule decides among the four co-stated figures; all chose 24.7 as the gross charge.
- Measurement, ORIGINAL rules: all three searched only for flavor adjectives near the row (adjusted, GAAP, non-cash). None listed the
  column heading as a candidate. Asked directly (Q8), ORIG-P1 said the heading "belongs in `level_low`/`level_high`": it selects the
  number and is then spent.
- Measurement, C3 rules: all three kept the heading and cited the C3 table sentences, while two flagged that a P&L-stage column label is
  not among the rule's flavor examples ("I extended the rule by analogy").
- Name: all three ORIGINAL children cite Rule 2's list "asset_impairment → action_event" as the canonical NAME.
- Slice: the split turns on whether evidence outside the fixed quote (footnote 3) may be used. Rules 5.6 and 8 say "inside your quote";
  the ROLE text says the complete event is context. The children say no rule settles it for slice.
- State: two children flagged that the footnote puts the closures in the fourth quarter while the charge is already reported; all chose occurred.

## AD. My own walk of the ORIGINAL served task, as the reader (source to answer)

1. ROLE: one target meaning, the labelled row; one fact unless a rule requires a sibling or basis split. Nothing requires one here.
2. Rule 1: a real one-off charge, so a fact. Rule 2: `action_event`; the text itself offers `asset_impairment` beside the lane.
3. Rule 3: 3.3 asks for all supported specificity, which the row label gives (restaurant closures). 3.4 sends an own brand to the slice.
   The Rule 2 list and Rule 3.3 pull in different directions for the name and nothing ranks them.
4. Rule 5: the item gives four figures for one label. No sentence says which is the fact's value. 5a allows one unit per fact, so one
   figure must be chosen; the first (24.7, millions) is the natural pick. In the ORIGINAL text the table is one flattened line, so the
   figure-to-heading link exists only by counting positions across a doubled eight-heading run.
5. Rule 6: fiscal 2026, third quarter, duration. The quarter label sits just outside the fixed quote.
6. Rule 7: outcome 4 is "empty list for a true whole-company fact". A closure charge tied by footnote to one brand is not obviously
   whole-company, and the menu offers that brand. The ORIGINAL rule has no action-lane notion of "no applicable part".
7. Rule 8: "measurement-flavor spans" with adjectival examples, copied VERBATIM. The tax basis here exists only as a column heading that
   names another measure. The source never says "pre-tax", so the reader cannot write it. The available moves are to copy another
   measure's name into a flavor field, or to leave the field at its default. The sparse-output rule makes the default the quiet path.
8. Output: JSON only, no place for a note. Any doubt about steps 4, 6 or 7 is invisible in the reply.

Remaining uncertainties of mine: whether the design intends a column heading to count as a measurement span at all (section L–Q above);
whether slice evidence may come from outside the fixed quote; which of the four figures is the fact's value. None is decided by the
served text.

## AE. The prepared fresh reading (PREPARED, NOT LAUNCHED)

`candidate_ORIGINAL2/direct_sonnet_DRI062_original2.js`, identity `A7-PILOT-DRI062-ORIGINAL-2`. The prompt constant equals
`ORIGINAL_PROMPT.txt` and equals the de-framed body that ORIGINAL-1 received. Same tail as the C3 attempt-two launcher: Sonnet, high
effort, lean-probe, Read disallowed. Full context record: `candidate_ORIGINAL2/PRECALL_PREPARED_ORIGINAL2.json`.

All context actually supplied to a child, beyond the task text:
- a harness frame line ("[Workflow harness — computed task] … carries no user authority …") and two-space indentation of every task
  line. Present in all pilot children; absent in the historical 2.1.261 children I checked. Already recorded in `RESULT.md`.
- attachments: environment, model, session_context, date, system prompt snapshot, and an `instructions` attachment holding FOUR files:
  the global CLAUDE.md, the project CLAUDE.md, one test rule file, and MEMORY.md (24,933 characters as delivered today).
- Token arithmetic (ORIGINAL versus C3 children) leaves about 14.8 thousand input tokens beyond the task text, against a system prompt
  of about 1.7 thousand characters. That is consistent with the instructions attachment reaching the model. It is an estimate.
- Differences from ORIGINAL-1, effects not asserted: CLI 2.1.275 → 2.1.278; date; MEMORY.md content (it changes whenever Core writes
  memory, so a reader's real input is not frozen); one `<total_tokens>` line gone from the system prompt snapshot; two Core restarts.
- MEMORY.md contains no tax-basis words. It does contain pilot status lines. No answer key or pilot conclusion is added by any wrapper of mine.

## AF. Proposed separate follow-up (NOT launched)

Same-child continuation: not available by any means I can verify locally. `ListAgents` shows no reachable agent after fourteen completed
Workflow children, the Agent tool's `resume` parameter was removed (Infrastructure.md), and I found no continuation call in the
Workflow runtime notes. So I propose Codex's fallback: a SEPARATE reviewer child, clearly identified as an independent assessment, that
sees the exact original task and the saved returned answer.

Proposed reviewer text (generic; no tax token, key, verdict or preferred reading):

> You are reviewing another reader's finished answer. Below are (1) the exact task that reader received and (2) the exact JSON it
> returned. Do not redo the task and do not correct the answer. Using only the task's rules and its source evidence, explain concisely:
> (a) what the returned record asserts, field by field, in plain words; (b) for each field whose value is not obvious from the target
> line alone, which source words and which rule sentence support that value; (c) any place where the rules or the source leave more
> than one defensible value, naming the alternatives and the rule or source words that bear on each. Quote rule sentences and source
> words exactly. Where nothing in the rules decides a point, say so. This is an independent assessment of a finished answer; it is
> not a record of how that answer was produced.

Delivery: the same launcher shape with a new identity, the text above first, then the original task and the returned JSON as two
delimited blocks; launched only after the first result is saved and read, from a clean notification turn; Codex reviews the assembled
input first.

---

# The one reviewed exact-original reading (Codex 2219)

## AG. ORIGINAL-2: identities and delivery

Run `wf_ad86ec7e-70a`, identity `A7-PILOT-DRI062-ORIGINAL-2`, completed 2026-09-21 00:32:15 UTC, 83,667 ms, error none, stop reason
end_turn. Launched from a Monitor-notification turn. Pre-launch record `candidate_ORIGINAL2/PRECALL_LAUNCH_ORIGINAL2.json`: all five
reviewed input files, the launcher and the prompt matched Codex's hashes; output limit 128000; no API key in the Core process.
Post-call record `candidate_ORIGINAL2/POSTCALL_DELIVERY_ORIGINAL2.json`: one user message; no owner-chat relay; the de-framed body equals
`ORIGINAL_PROMPT.txt`; child model claude-sonnet-5; CLI 2.1.278; agent type lean-probe; zero tool calls; the delivered MEMORY is 24,933
characters with the same hash as the copy Codex reviewed (17cc4eea…), not the newer live file. Effort is set to high in the launcher; the
native meta record does not state effort. Evidence preserved with zero mismatches in `exec/evidence/wf_ad86ec7e-70a/`.
This is an unchanged request in the CURRENT runtime. It is not a reproduction of the historical 2.1.261 runtime (no harness frame then).

## AH. The returned record, inspected against the original rules and source

Returned text sha ca05cc64…, 644 bytes, and it is BYTE-IDENTICAL to the returned text of the clean C3 attempt-two reading.
`action_event` · `restaurant_closure_impairment` · `occurred` · level 24.7 × 1,000,000, evidence `millions`, point, `m_usd` · fiscal 2026,
quarter 3, duration · slice, measurement and every other optional field omitted.

- **Format validity:** one fenced JSON object; exactly the four top-level keys; one fact, no abstention, empty hints; only lawful item
  keys; `source_id` correct. No route repeat was run (not needed at this boundary).
- **Field equality with the key:** fact type and `per_x` equal; 16 of 17 compared item fields equal; the one difference is
  `measurement_raw_spans`, omitted (default empty) where the key has `Earnings Before Income Tax`.
- **Financial meaning against the source:** 24.7 is the row's first figure, under the pre-tax earnings column of the third-quarter 2026
  group; `millions` is inside the quote; the quarter and year are the table's own; a reported charge is an occurred one-off action.
  Nothing returned misstates the source. The record does not carry which of the row's four figures it is.
- **Name:** specific, under the UNCHANGED original prompt. Pilot readings under this exact prompt are now one broad (ORIGINAL-1) and one
  specific (ORIGINAL-2); the historical pair was one specific (P1) and one broad (P2). So the earlier before/after contrast for the
  Rule 2 paragraph is weaker than I recorded; `ATTEMPTS.json` is updated and the old wording preserved.
- **Remaining uncertainty:** unchanged. Whether the unqualified name carries the pre-tax meaning, hence whether the omitted heading is
  a loss; and why the field was left out. No hidden reason is inferred here.

## AI. Corrections from Codex 2219, carried

- Rule 2 owns `fact_type`; Rule 3 owns the name and its specificity. Rule 2 does not literally mandate the bare name, so the diagnostic
  explanations do not prove two conflicting naming orders. My section AD item 3 overstated that.
- Original Rule 8 contains NO inside-your-quote restriction. Rule 5.6 applies that restriction to scale evidence only. The full event is
  expressly supplied for interpretation. Diagnostic ORIG-N2 attributed a nonexistent quote restriction to Rule 8, and C3-N2 extended it
  to slice. Those are reported justifications, not design law. My sections AC and AD repeated that attribution; it is withdrawn.
- JSON-only still allows an abstention with a reason when a fact cannot be lawfully resolved, so my "doubt has no place to appear" was
  too strong.
- Open, source-grounded measurement law need not list every possible heading.
- A disk write to MEMORY.md does not immediately change a child's input: all seven children today received the same 24,933-character
  copy. Attachment presence and token arithmetic do not expose the complete serialized request.
- Process: the six diagnostics did not receive Codex's input review before launch, and their addendum also conflicts with Rule 0's
  never-restate instruction. Not to be repeated. No further requests for thought traces or candidate histories.

---

# One independent assessment of the finished ORIGINAL-2 answer (Codex 2220)

## AJ. Identities and delivery

Review input: `review_INDEPENDENT1/DRI_REVIEW1_PROMPT.txt`, 56,222 bytes, sha 1ae73ed5…, assembled and personally reviewed by Codex; the
durable copy equals the frozen file. Launcher `review_INDEPENDENT1/direct_sonnet_DRI062_independent_review1.js`, identity
`A7-PILOT-DRI062-INDEPENDENT-REVIEW-1`: one prompt entry whose decoded constant equals the frozen bytes; the embedded task equals
`ORIGINAL_PROMPT.txt` and the embedded answer equals ORIGINAL-2's returned text; the executable tail equals ORIGINAL-2's tail; one agent
call site; compiles. Pre-launch (`PRECALL_LAUNCH_REVIEW1.json`): all five reviewed context files matched Codex's hashes (live MEMORY
4476a653…); output limit 128000; no API key; Monitor-notification turn. Launched ONCE.
Run `wf_c932e727-4c9`, completed 2026-09-21 00:47:31 UTC, 146,214 ms, end_turn, error none. Post-call (`POSTCALL_DELIVERY_REVIEW1.json`):
one user message; no owner relay; de-framed body equals the frozen review input; claude-sonnet-5; CLI 2.1.278; effort high and
attribution agent lean-probe on the native final assistant record; zero tools; every context attachment has the same hash as ORIGINAL-2's,
including the delivered MEMORY (24,933 characters, 17cc4eea…). A separate review call: not a reading, not a semantic-grader update.

## AK. What the assessment says, and my audit of it

Returned text sha 9e93d30d…, 5,034 bytes, preserved untouched. In its own words the answer is "fully supported for what it claims",
with "two open uncertainties": whether the Bahama Breeze brand should have been a slice given the footnote link, and "the unstated
assumption that the pretax figure, not the net-of-tax or EPS figure, is the fact's canonical value". It also notes that the quarter label
sits just outside the pinned quote.

Audit against the actual task text (whitespace-folded):
- Exact: the Rule 2 pairing of asset_impairment with action_event; "`occurred` = completed" (Rule 4); Rule 5.6's smallest supporting
  span; the table heading "Fiscal Q3 Reported to Adjusted Earnings Reconciliation Q3 2026 Q3 2025", which does immediately precede the
  quoted run; footnote 3's sentence; the menu token for the brand; Rule 7's "empty list for a true whole-company fact".
- Altered by one word: it quotes the ROLE text as "interpret the target correctly"; the task says "interpret that target correctly".
- Loose: it says Rule 3.3 lets "a stated specific cause" beat the default name; Rule 3.3's words are "A stated specific instrument
  beats the familiar broad name".
- OMISSION: although asked to inspect "any omitted field whose declared default materially affects its meaning", the assessment never
  mentions the measurement field (zero occurrences of "measurement"). It treats the pre-tax question purely as which NUMBER was chosen,
  and supports that choice by "the ordinary-usage convention (the "impairment charge" headline figure is normally quoted pretax/gross)".
- Its slice point restates the open scope question; it does not settle it, and it says so.

What this is evidence of: one more independent Sonnet interpretation, under the ORIGINAL rules, that does not see the column heading as
something the measurement field should carry, and that names a CONVENTION as the basis for reading 24.7 as the charge. It is not ground
truth, it is not a recovered explanation of how ORIGINAL-2 was generated, and it does not decide the intrinsic-meaning question.

## AL. Two corrections from Codex 2220, carried

- ORIGINAL-2's effort IS natively evidenced: the final assistant record 9177a244-798b-4749-8c37-e37cfd489888 has effort high and
  attribution agent lean-probe. My post-call file quoted the usage of the first assistant chunk (9 output tokens); the final record reports
  7,849. Recorded in `candidate_ORIGINAL2/POSTCALL_DELIVERY_ORIGINAL2_CORRECTION.json`; the original file is left unedited.
- My sentence that the ORIGINAL-2 record "does not carry which of the row's four figures it is" must stay CONDITIONAL on the unresolved
  intrinsic-meaning question: 24.7 itself identifies a cell, and the tax-basis meaning is the very point under review. Supported positive
  field checks are not a settled whole-record verdict.
- Provenance limit noted by Codex: the historical P1/P2 reader children (wf_d383c00a-eb4) received the same task bytes with no harness
  frame, and their logs hold no instruction or system snapshots. Absence of recorded context is not proof that none was supplied.

---

# One focused independent assessment of the measurement default (Codex 2221)

## AM. Identities and delivery

Review input `review_INDEPENDENT2/DRI_REVIEW2_PROMPT.txt`, 56,466 bytes, sha 20273e58…, assembled and personally reviewed by Codex; the
durable copy equals the frozen file; its two evidence blocks are byte-identical to REVIEW-1's (the original task and ORIGINAL-2's returned
text). Launcher `review_INDEPENDENT2/direct_sonnet_DRI062_independent_review2.js`, identity `A7-PILOT-DRI062-INDEPENDENT-REVIEW-2`: one
prompt entry equal to the frozen bytes; tail equal to REVIEW-1's and ORIGINAL-2's; one call site; compiles. Pre-launch
(`PRECALL_LAUNCH_REVIEW2.json`): all five reviewed context files matched Codex's hashes (live MEMORY 9af73dc6…); limit 128000; no API key;
Monitor-notification turn. Launched ONCE.
Run `wf_0a5c0a49-024`, completed 2026-09-21 01:02:19 UTC, 115,859 ms, end_turn, error none. Post-call
(`POSTCALL_DELIVERY_REVIEW2.json`): one user message; no owner relay; de-framed body equals the frozen input; claude-sonnet-5; CLI
2.1.278; effort high and attribution agent lean-probe on the native FINAL assistant record (615db6bf…; 11,128 output tokens from that
final record); zero tools; every context attachment hash equals REVIEW-1's; delivered MEMORY 24,933 characters, 17cc4eea….

## AN. What the assessment says, and my audit

Returned text sha 32308c1d…, 3,630 bytes, preserved untouched. Conclusion in its words: "the empty `measurement_raw_spans` is NOT
truthful."

Its argument, in three parts that Codex asked me to keep distinct:
- EXISTENCE of the source phrase: "Earnings Before Income Tax" is "the column header governing the "24.7" the fact selected", and it
  "appears twice, verbatim, inside the supplied quote". AUDIT: true; the item quote contains the heading twice and ends "18.5 0.16".
- ROLE as a modifier: it "states which financial-statement stage the chosen number represents (pre-tax)", as distinct from the row's
  other three values under their own headers. AUDIT: this is the interpretive step. It is argued, not quoted from a rule.
- CARRIED ELSEWHERE?: not by `driver_name` ("names only the cause, per Rule 3.1"), not by `level_unit` ("conveys currency/scale, nothing
  about tax basis"), not by period, slice or a comparison baseline. AUDIT: Rule 3.1 does say "Name the CAUSE only"; Rule 5a.1 does define
  `m_usd` as aggregate dollars in millions. It does NOT consider whether a standard financial term could carry the basis intrinsically
  (Rule 3.9 keeps standard financial phrases whole); it treats the name as cause-only by Rule 3.1 and stops there.
- RULE applied: Rule 8's sentence "Any number modifier not captured by name/period/unit/slice/basis stays here". AUDIT: exact. It calls the
  clause "mandatory" and "unconditional"; the clause's own condition is non-capture, which it argues field by field.
- CONVENTION: it names the convention that impairment figures "are customarily quoted pre-tax", calls it "a convention, not something the
  record states", and adds that the source "explicitly lays out four parallel values side by side", so the pre-tax reading "was an
  explicit choice among stated alternatives". It separates two uses of the header: locating the digit (transient) and stating what the
  digit means (which "must survive into the record"); "Only the first happened here."
- UNSUPPORTED attribution: it says the footnote "cannot be pulled in" "under Rule 0/8" because it lies outside the fixed quote. The
  original Rule 8 has no quote restriction, and Rule 0 concerns instructions versus evidence. Its main conclusion does not rest on this.

What it is evidence of: a second independent Sonnet interpretation of the SAME finished answer under the SAME original rules. Asked about
the whole record (REVIEW-1), the field was not addressed. Asked about this one field (REVIEW-2), the original rule text was judged enough
to require the heading. That contrast is an observation about two review calls. It is NOT a complete pilot pass, NOT a confirmed
historical cause, and NOT a record of how ORIGINAL-2 was generated. The intrinsic-meaning rival (section L) is not engaged by it.

## AO. Corrections to my 2218 audit, from Codex 2221, carried

- Zero occurrences of "measurement" in REVIEW-1 proves only that no explicit measurement-field finding was REPORTED. It does not
  establish that the reviewer considered the field and decided no heading belongs there. My sentence that it "does not see the column
  heading as something the measurement field should carry" went beyond that and is withdrawn.
- Rule 3.3 begins "Use all the specificity the evidence supports; never a broader class to force reuse". The instrument sentence is not
  its only principle. REVIEW-1's cause-specific name rationale is supported by that clause and by Rule 3.1; my "loose" label was wrong.
- REVIEW-1's statement that the amount is brand-specific overstates footnote 3's "primarily related to". A linked footnote is supplied
  context for the same target, not automatically a new fact. The actual scope question is whether the WHOLE amount supports a brand
  population; it must not be replaced by a blanket inside-quote rule.

---

# One controlled comparison of four record meanings (Codex 2222)

## AP. Identities and delivery

Input `review_MEANING_MATRIX1/DRI_MEANING_MATRIX_PROMPT.txt`, 59,465 bytes, sha 2689f167…, assembled and personally reviewed by Codex;
durable copy equal to the frozen file; the original task is embedded byte-exact. Four hypothetical records with neutral labels, all
other fields equal to ORIGINAL-2: K7 = 24.7 with `Earnings Before Income Tax`; R8 = 24.7 with no qualifier (the parsed ORIGINAL-2 answer);
V4 = 18.5 with `Net Earnings`; M2 = 18.5 with no qualifier. Launcher `review_MEANING_MATRIX1/direct_sonnet_DRI062_meaning_matrix1.js`,
identity `A7-PILOT-DRI062-MEANING-MATRIX-1`: one prompt entry equal to the frozen bytes; tail equal to REVIEW-2's and ORIGINAL-2's; one
call site; compiles. Pre-launch (`PRECALL_LAUNCH_MATRIX1.json`): all five reviewed context files matched Codex's hashes (live MEMORY
b01cffec…); limit 128000; no API key; Monitor-notification turn. Launched ONCE.
Run `wf_6d1f9f81-30b`, completed 2026-09-21 01:18:32 UTC, 69,548 ms, end_turn, error none. Post-call (`POSTCALL_DELIVERY_MATRIX1.json`):
one user message; no owner relay; de-framed body equals the frozen input; claude-sonnet-5; CLI 2.1.278; effort high and attribution agent
lean-probe on the native FINAL assistant record (df0d934f…; 6,494 output tokens from that record); zero tools; every context attachment
hash equals REVIEW-2's; delivered MEMORY 24,933 characters, 17cc4eea….

## AQ. What the comparison says, and my audit

Returned text sha 6a08b64d…, 4,570 bytes, preserved untouched. Its verdicts, in its words:
- R8 (24.7, no qualifier): "clean and fully supported".
- K7 (24.7 with the heading): "reaches the same correct pre-tax quantity but adds a spurious, rule-inconsistent measurement span".
- M2 (18.5, no qualifier): "Unsupported as "the impairment charge""; 18.5 is "a genuinely different quantity".
- V4 (18.5 with `Net Earnings`): "Unsupported, same defect as M2", and the span is "the same Rule 8 misuse".

IS ITS ACCOUNT CONSISTENT ACROSS THE FOUR? Yes, internally. One premise decides both axes: the object is the gross charge. So the
figure 24.7 is supported and 18.5 is not, with or without a heading; and a column heading is provenance, not a measurement flavor, for
both figures. The two source-backed qualified records served as controls and it rejected the qualifier on both, not only on one.

Kept distinct, as Codex asked:
- SOURCE CORRESPONDENCE: it reads the four cells correctly, gives 24.7 − 6.2 = 18.5, and cites the statement-of-earnings line
  "Impairments and (gain) loss on disposal of assets, net 25.1". AUDIT: that line is in the supplied source; "in the same ballpark" is
  its own comparison, not an identity.
- LAWFUL REPRESENTATION: it says the heading is "not a measurement-flavor qualifier under Rule 8 (adjusted/GAAP/constant-currency-type
  wording)". AUDIT: Rule 8's flavor list is in the task. But the comparison never cites the SAME rule's catch-all sentence, "Any number
  modifier not captured by name/period/unit/slice/basis stays here", which is also in the task and on which REVIEW-2 rested.
- INFERRED REPORTING CONVENTION: it calls pre-tax sizing "Customary and definitional practice" and once "the rule that a charge is stated
  at its pre-tax/gross size". AUDIT: the rules zone of the task contains no pre-tax or gross wording at all. This is its accounting
  premise, stated as a rule. It also treats 18.5 as unstorable under this name, which is the gross-only restriction that no clause of the
  task or of the live design entails (section P1). It does not repeat REVIEW-2's false Rule 0/8 quote restriction.

## AR. What the three assessments together show, and what they do not

Same finished answer or its fields, same original rules, same model, same delivered context:

| call | asked | position on the empty qualifier | sentence of Rule 8 relied on |
|---|---|---|---|
| REVIEW-1 | whole record | not addressed; pre-tax figure supported by an "ordinary-usage convention" | none cited for this field |
| REVIEW-2 | this field only | "NOT truthful"; heading required | the catch-all sentence |
| MATRIX-1 | four candidates side by side | unqualified 24.7 "clean"; heading "spurious" | the flavor examples |

OBSERVATION: two sentences of the one original Rule 8 point in opposite directions for a column heading that names another measure, and
an independent reader lands on either side depending on how the question is framed. The same split appears in the extraction outputs
(heading kept in some runs, left out in others) and in the five unhelped Opus owner runs (kept twice, dropped three times).
NOT SHOWN: why any extraction reply left the field out; that either reviewer is right; that the key's token is wrong or required. A
changed assessment is observed behaviour, not proof of a historical cause. The intrinsic-versus-conventional premise is still unsettled:
REVIEW-2 treats the name as cause-only and never weighs intrinsic meaning; MATRIX-1 asserts intrinsic meaning as "definitional" without
any task text behind it.

---

# The financial-definition premise, settled against the source-defined target (Codex 2223)

Read-only. No model call. Primary sources re-verified by me: `source_definition_check/README.md` (Darden FY2025 annual report, downloaded
and text-extracted; FASB 2026 taxonomy label read from Codex's local copy, sha 320b4eb0…). None of it was ever reader input.

## AS. Corrections to my 2220 report (section AR stays as written; this supersedes it where they conflict)

- Rule 8's illustrative flavor list and its general catch-all do NOT logically point in opposite directions. The two reviews APPLIED
  them differently. That is not a proved contradiction in the rules. Withdrawn.
- One differently framed call apiece does not isolate FRAMING as the cause of the different answers; ordinary output variation is not
  excluded. Withdrawn.
- The earlier key-owner revisions were dependent tasks that saw prior answers and reviews. They are not five independent unhelped
  trials (I had said this correctly in section I.3 and then misstated it in AR). Only runs #1 and #5 lacked an earlier owner answer.
- I must not infer that a reviewer did or did not consider a sentence solely because it did not quote it.

## AT. The argument, in the order Codex set

**(1) What the raw target plus its linked footnote names.** The target label is "Impairment due to restaurant closures3". The marker
inside the quote links footnote 3: "Non-cash asset impairment charges primarily related to the closures of Bahama Breeze locations
expected to occur in the fourth quarter of fiscal 2026." The ROLE text supplies the complete event so the target can be interpreted
correctly. So the source itself names the target: asset impairment CHARGES. The same release carries "Impairments and (gain) loss on
disposal of assets, net" among costs and expenses, above earnings before income taxes. Under DU-05/06 this is the one-off charge, an
action.

**(2) What an unqualified dollar level of that concept asserts, by definition.** An asset impairment charge is the write-down itself:
Darden's policy, published before this release, says "the recognized impairment is measured by the amount by which the carrying amount
of the assets exceeds their fair value"; the FASB taxonomy defines the charge as the "write down of long lived assets … due to the
difference between the carrying value and lower fair value". The measure has NO tax term. Tax basis is therefore not a free attribute
of the concept: "the impairment charge was 24.7" is a complete statement, and "the impairment charge was 18.5" would be false, because
18.5 is the charge's after-tax EFFECT on net earnings (24.7 less its 6.2 tax effect), a different quantity. That is a definition, not a
reporting custom. The custom is only that releases ALSO show the after-tax effect.

**(3) Rule 3.9 / NAME-08 and the non-capture condition of Rule 8 / FINAL §5.3.** A cause-only name can still contain a meaningful
financial concept: `restaurant_closure_impairment` contains "impairment", a standard financial concept that keeps its definition
(Rule 3.9; NAME-08, FINAL_DESIGN.md :93). Rule 8's sentence and §5.3's never-drop clause (:191) keep a number modifier only when it is
NOT captured by the name, period, unit, slice or basis. For this quantity the heading "Earnings Before Income Tax" names the earnings
measure being reconciled; that the charge enters that measure at its full amount follows from the definition. Nothing about 24.7 as an
impairment charge is left uncaptured, so the non-capture condition is not met. "Empty never implies GAAP" concerns the accounting-
standard version and does not strip intrinsic meaning from names. And the possibility of a QUALIFIED transformed amount under the same
cause (18.5 with its heading) does not make the bare concept ambiguous; I take no position on whether such a record should exist, and
I add no gross-only product rule.

This reverses the lean I recorded in section L. There I used the control "`earnings_per_share` still needs `diluted`": that control
fails here, because basic and diluted are two DEFINED variants of one named quantity, so the bare name is ambiguous between them,
whereas an impairment charge has ONE defined measure and the after-tax figure is not a variant of it but a consequence. My section K4
point (the prose "$0.16 of impairment …") shows the label being used for a per-share effect in an EPS sentence; the unit there signals
the transformation and it does not make the unqualified dollar level ambiguous.

## AU. Conclusions, with their exact scope

1. **Is ORIGINAL-2's record (24.7, empty measurement) truthful under the supplied task? YES.** Scope: for the measurement field and the
   level of THIS target. Within the task the support is footnote 3's "asset impairment charges", the statement-of-earnings placement
   and Rule 3.9's premise that a standard financial concept carries its meaning; the definition itself is evidenced by primary sources
   outside the task. This says nothing about the slice, which stays contested.
2. **Is adding the heading required, allowed but redundant, or wrong? NOT REQUIRED; allowed but redundant.** It does not misstate the
   source (24.7 is indeed the amount at which the charge enters pre-tax earnings), and "When unsure, keep" (:191) tolerates it. It adds
   no meaning, and it has a cost the design itself names: measurement is part of the series key (:299) and there is no write-time
   merging (:192), so the same fact stated in prose without a heading would land in a different series. I find no clause that makes a
   redundant token WRONG, so I do not call it wrong.
3. **What this establishes about the earlier failure.** The `measurement-OD-9` flag on this example compares the reader's tokens with a
   key token that is tolerated but not required. On this field the recorded failure is therefore an exact-key mismatch on a
   non-required token, not a reader error, for every reading that stored 24.7 with empty measurement. It does NOT establish why any
   reply left the field empty, it does not make the key's token wrong, and it proposes no grading change. It also does not touch the
   name or slice findings.

**What remains genuinely open, stated precisely:** nothing on the tax basis of the unqualified level. Open elsewhere: whether the WHOLE
24.7 supports a Bahama Breeze population given "primarily related to" (slice); and the separate, unneeded design question of whether a
qualified transformed amount is a storable level.

---

# The population question, and a complete-record audit of the saved ORIGINAL-2 answer (Codex 2224)

Read-only; no model call. Not used to decide anything here: inside-quote restrictions, brand mention alone, key equality, the judges' votes.

## AV. What the ENTIRE 24.7 measures

What the release asserts, in its own words:
- The row sits in "Fiscal Q3 Reported to Adjusted Earnings Reconciliation", whose first row is "Reported Earnings from Continuing
  Operations" and whose last is "Adjusted Earnings from Continuing Operations". These are Darden's consolidated earnings. So 24.7 is the
  amount the COMPANY reports, at the consolidated level, as its adjustment for "Impairment due to restaurant closures". The label names
  no brand.
- Footnote 3: "Non-cash asset impairment charges primarily related to the closures of Bahama Breeze locations expected to occur in the
  fourth quarter of fiscal 2026." This entails that Bahama Breeze closures are the principal contributor. It does not state a
  brand-level amount, and it does not state that the whole amount is Bahama Breeze. The release uses "Primarily" the same way in
  footnote 2, where it goes on to name a second component ("and other costs related to the strategic review …").
- Nowhere does the release size the IMPAIRMENT by brand (all six mentions of Bahama Breeze checked). The headline sentence is telling:
  it labels the $0.05 cost item with the brand ("costs related to the exploration of strategic alternatives for the Bahama Breeze
  brand") but labels the impairment generically, "$0.16 of impairment due to restaurant closures".

Alternative (b), the brand is the measured population of the whole figure. A slice asserts the population over which the stored amount
is measured (FINAL_DESIGN.md :174, "a business population for which "revenue/earnings from ___" makes sense"). Storing 24.7 with the
brand slice asserts that 24.7 is Bahama Breeze's. The source entails only "primarily". A world in which all of it is Bahama Breeze is
consistent with that word but is not established by it. Original Rule 7 ends "Never guess"; the live ladder says "Ambiguous prose must
not guess" (:178). So (b) asserts more than the release states. NOT truthful for the whole figure.

Alternative (a), empty. The original Rule 7 outcome (4) is "empty list for a true whole-company fact". The aggregate here is not
invented to fill a gap: the release itself places the amount in the consolidated reconciliation of the company's earnings. A
consolidated reporting aggregate is a whole-company figure even when few locations drive it; it does not assert that every brand was
impaired. Live law agrees and predates the task (both sentences entered FINAL_DESIGN on 2026-07-15): OD-17 (:97) "Omit the slice only for
the true consolidated reporting population", and :175 "Omitted slice = consolidated whole-company (metric/guidance/surprise) or
no-applicable-part (action)". The served ORIGINAL Rule 7 lacks that action clause; C2–C4 carry it, plus the sentence "A part mentioned
as a cause or as a partial explanation does not by itself make the whole amount that part's." Under either served text the same value
is truthful: EMPTY.

A third candidate, checked and rejected: the menu holds `unknown:us-gaap:ImpairedLongLivedAssetsHeldAndUsedByTypeAxis__restaurantsclosed`.
"Restaurants closed" is the CAUSE of this charge, an event, and Rule 3.4 / NAME-11 keep an event that causes the outcome in the name,
where it already is. It is an asset-type classification, not one of the six business-part kinds (:174 "Accounting labels are not slices").

What empty loses: the principal-contributor remark. The design has no field for a partial attribution, and none is invented here; the
remark stays in the source event the fact is drawn from. Because a truthful value exists, the abstention branch is NOT required.

**Result:** the release asserts a company-reported consolidated amount with a stated principal contributor. Empty is truthful; the brand
slice over-attributes. This settles the scope question for THIS target. It is a source-and-rule reading, not a vote.

## AW. Complete-record audit of the saved 644-byte ORIGINAL-2 answer (sha ca05cc64…), byte-identical to the clean C3 attempt-two answer

| field group | returned | source words and rule | under ORIGINAL task | under C3 task |
|---|---|---|---|---|
| type and name | `action_event`, `restaurant_closure_impairment` | a one-off charge (Rule 2); "Impairment due to restaurant closures" gives the cause; Rule 3.1 cause only, 3.3 all supported specificity, 3.10 no glue word, 3.11 order | correct | correct (same Rule 3, plus the paragraph that lane examples do not prescribe names) |
| state | `occurred` | the charge is inside Q3 reported earnings (it is reconciled FROM them; the Q3 statement carries impairments of 25.1); the fact is the CHARGE, already recognised, not the closures, which footnote 3 places in the fourth quarter; Rule 4 "`occurred` = completed" | correct | correct |
| amount, unit, scale span | 24.7, ×1,000,000, `millions`, point, `m_usd` | first figure of the row; header "in millions, except per share amounts" is inside the quote; Rule 5.6 asks for the SMALLEST supporting span, which is `millions`; Rule 5a.1 `m_usd`; low equals high is a point (Rule 5.2) | correct | correct |
| period | FY 2026, quarter 3, `duration`, no dates | table heading "Q3 2026" in the supplied event; a charge over a quarter is a flow (Rule 6); the release states only the quarter END (February 22, 2026), and an exact duration needs both endpoints (step1 A5 item 6), so the fiscal framing alone is the lawful form | correct | correct |
| population | omitted (empty) | section AV | correct | correct (C3's Rule 7 states the point explicitly) |
| measurement | omitted (empty) | section AU: truthful by definition of the charge | correct; the heading would be allowed but redundant | correct; C3's Rule 8 says a header that only restates carried meaning "is not copied", so under C3 the empty field is also the instructed one |
| applicable omitted fields | `per_x`, change, comparison, guidance-only and surprise-only fields all default | an aggregate dollar amount has no per-something denominator; no prior-year figure for this row is stated (outside the original quote; dashes in C3's); not guidance, not a surprise | correct | correct |
| envelope | four top-level keys, one fact, no abstention, empty hints, right `source_id` | A3 output contract | valid | valid |

**Result of this manual expected-versus-actual reading:** every field of the existing record is correct against the source and against
each served task. SCOPE, stated plainly: this is about ONE existing record. It is not evidence of reliability on unseen items (the same
unchanged prompt also produced the broad name and the brand slice in other runs), it is not proof that any prompt change caused the
result (ORIGINAL-2 used the unchanged original prompt), and it clears nothing else. Still standing, untouched: the historical P1 and P2
findings (P1 brand slice and a non-minimal scale span; P2 broad name), the combined-answer matching rule that denied credit to a
one-to-many match, and the downstream date-lookup defect. No production claim is made.

---

# Controlled name-example ablation, executed (Codex 2226)

Six reviewed diagnostic readings of the same first example. Inputs personally reviewed by Codex before launch. Question, judging rule and
interpretation of every pattern were written BEFORE any call (`diag_name_ablation/PREDECLARATION.md`). Task B is a diagnostic ablation of
the locked classifier text and is NOT an adopted change. Nothing here is pooled with any earlier run.

## AX. Execution and delivery

Launcher `diag_name_ablation/direct_sonnet_DRI062_name_ablation.js` (sha fdedaf90…). Fixed order A,B,B,A,A,B; strictly serial, each
child preserved (`exec/preserve_probe.py`, zero mismatches) and delivery-checked (`diag_name_ablation/postcall_check.py`, all six OK)
before the next was launched. Every child: claude-sonnet-5, CLI 2.1.278, effort high and agent lean-probe on the native FINAL assistant
record, one user message, no owner relay, de-framed body byte-equal to its task file, harness frame 8bb4f906…, zero tools, end_turn, all
context attachment hashes equal to the reviewed ones, delivered MEMORY 24,933 characters 17cc4eea… (the live file was not reloaded).
No retry, no failure, no departure. No memory or configuration file was edited between the calls.

| # | label | task | run | completed (UTC) | returned text sha |
|---|---|---|---|---|---|
| 1 | T27 | A | wf_f6716dcf-35a | 02:09 | 8983c6336aec |
| 2 | T64 | B | wf_3322ff97-be6 | 02:11 | 01b6cfb069c9 |
| 3 | T13 | B | wf_438325e7-517 | 02:14 | 90aa2f108f72 |
| 4 | T85 | A | wf_6614db88-ebd | 02:15 | b78e30047131 |
| 5 | T39 | A | wf_a35a7bbe-b35 | 02:18 | 67b5c4a34909 |
| 6 | T72 | B | wf_e08c9f7c-76d | 02:20 | c255c9bb9a4b |

## AY. Every returned record, read against source meaning

| label | task | name (by supported meaning) | population | period | scale span | other |
|---|---|---|---|---|---|---|
| T27 | A | `asset_impairment` — BROAD | Bahama Breeze brand | FY2026 Q3 duration | `in millions` (not the smallest span) | — |
| T85 | A | `asset_impairment` — BROAD | empty | FY2026 Q3 duration | `millions` | — |
| T39 | A | `restaurant_closure_impairment` — CAUSE-SPECIFIC | empty | FY2026 Q3 duration | `millions` | every field correct |
| T64 | B | `restaurant_closure_impairment` — CAUSE-SPECIFIC | empty | OMITTED entirely | `millions` | the stated quarter is lost |
| T13 | B | `asset_impairment` — BROAD | the XBRL "restaurants closed" member | FY2026 Q3 duration | `millions` | that member is the cause, not a business part (section AV) |
| T72 | B | `restaurant_closure_impairment` — CAUSE-SPECIFIC | Bahama Breeze brand | FY2026 Q3 duration | `millions` | — |

Constant across all six: `action_event`, `occurred`, 24.7 × 1,000,000, `m_usd`, point, empty measurement, valid envelope.

## AZ. Result, stated plainly

- **Names:** original task 1 of 3 cause-specific; list removed 2 of 3 cause-specific. The broad name ALSO appeared with the list absent
  (T13). This is the predeclared "no separation (both mixed)" pattern. It means the literal examples are NOT shown to be a material
  contributor at this sample size, and they are not necessary for the broad name. It does not exclude a small effect, and I do not
  alter the hypothesis after seeing the result. The anchoring hypothesis is weakened on this item, not refuted.
- **Fact type:** `action_event` in all six, so no lane difference arose and the limitation Codex named does not come into play.
- **Separate observations:** population empty 3 of 6, brand 2 of 6 (once in each arm), cause-as-slice 1 of 6; period complete 5 of 6;
  smallest scale span 5 of 6; measurement empty 6 of 6.
- **Whole records:** against the manual audit of section AW, 1 of 6 is fully correct (T39, the unchanged original task).
- **What the six DO show:** under one unchanged task, and equally under the ablated one, the name and the population vary from run to
  run. That variation, not any single sentence, is the observed problem on this example.
- **What they do NOT show:** the exclusive cause of any historical choice; reliability on unseen items; that any prompt change helps.
  No p-value is computed and nothing is pooled with the older adaptive runs.

---

# Round for Codex SEQ 2227 — read-only audit of the T13 field-allocation error (zero model calls, zero graph writes)

Evidence for this round: `t13_field_allocation_audit/NEO4J_QUERIES_AND_RESULTS.json` (CURRENT graph evidence, six read-only
lookups with their exact Cypher and rows), `t13_field_allocation_audit/HISTORICAL_MENU_RECEIPT.json` (HISTORICAL receipt taken
from pinned bytes), `t13_field_allocation_audit/graph_readonly_probe.py` (the script; session access mode READ).

## BA. Correction to section AZ (appended; AZ itself is left as written)

AZ ended: "That variation, not any single sentence, is the observed problem on this example." That sentence over-reads six
readings and is WITHDRAWN. The precise conclusion is:

- Original task (A): 1 of 3 cause-specific names. List removed (B): 2 of 3. This is MIXED / INCONCLUSIVE for the causal
  contribution of the list, with an observed difference in counts.
- The broad name appeared WITHOUT the list (T13). So the literal list is NOT NECESSARY for that failure, and removing it is NOT
  SUFFICIENT to prevent it.
- It does NOT prove that no sentence matters. It does NOT prove that an unspecified "model variation" is the root cause.
  Run-to-run variation is an OBSERVATION still to be explained, not an explanation.
- The missing-heading (tax basis) allegation stays closed; a lawful omission is not reopened.

## BB. Where the "restaurants closed" menu option really came from

Token as the reader saw it: `unknown:us-gaap:ImpairedLongLivedAssetsHeldAndUsedByTypeAxis__restaurantsclosed`.

**Historical receipt (pinned bytes, not a fresh read):**
- The pinned launch manifest `unit_2008/harness_g1v3/launch_kfields_drafts.manifest.json` (sha ff259bac…) records, for event
  0000940944-26-000005, 137 retained menu tokens and a 137-entry display→original map. Its packet #062 prompt sha is 54968bf6…,
  equal to `ORIGINAL_PROMPT.txt`. The served menu equals the map's display side.
- Menu make-up: 23 reviewed options (7 segment, 6 geography, 5 channel, 4 product, 1 entity_ownership) and **114 of 137
  `unknown:` options**, almost all accounting axes (debt instruments, hedges, award types, balance-sheet location, fair-value
  levels, …).
- The ORIGINAL stored token is the law's code-only sentinel (FINAL_DESIGN :179):
  `unknown:xbrlaxis_75732d67…41786973__restaurantsclosed` (hex of the exact axis qname). The pinned reader harness
  `a1_reader.py::readable_menu` (sha 98055e55…) deliberately and reversibly DECODES that hex for display. So the reader saw the
  accounting axis name in plain words. This is a designed display step, not an accident, and the pick is restored to the
  sentinel afterwards.
- The menu was built through production `driver.core.slice_menu.build_menu` (imported by `harness/slice_menu_probe.py`), cut
  at reports created ≤ event time, forms 10-K/10-Q(/A).

**Why it is in the menu at all (code + law):** the live classifier `driver.core.slice_menu.classify_axis` returns
`('unknown', None)` for `us-gaap:ImpairedLongLivedAssetsHeldAndUsedByTypeAxis`: it is in neither the 57 reviewed slice axes
(`CONFIRMED_AXES`) nor the 7 reviewed non-slice axes (`NON_SLICE_AXES`). An unreviewed axis follows the unknown→PROVISIONAL
path BY DESIGN: FINAL_DESIGN :176 "unknown axis → PROVISIONAL,
never silently dropped" and :179 "Unknown values enter the company menu for later reuse." Its presence in the menu is LAWFUL.
Lawful presence does not make it a valid slice for this fact.

**Current graph evidence (read 2026-09-20, read-only):**

| Lookup | Result |
|---|---|
| Member | `dri:RestaurantsClosedMember`, label "RestaurantsClosed" — a Darden EXTENSION member (taxonomies dri 2023-02-26, 2023-05-28, 2024-02-25, 2024-05-26) |
| Sits under | domain `us-gaap:ImpairedLongLivedAssetsHeldAndUsedAssetNameDomain`, axis "Impaired Long-Lived Assets Held and Used by Type [Axis]" |
| Facts carrying it | 7, ALL of one concept: `dri:NumberOfTangibleAssetsImpaired` ("Number Of Tangible Assets Impaired"), values 1–4. No dollar, sales or earnings fact carries it |
| Its only Darden sibling | `dri:RestaurantsWithProjectedCashFlowsLessThanCarryingValueMember`, 6 facts, same count concept, value 1 |
| Reports | 10-Q 0000940944-23-000019 (created 2023-04-04), 10-K -23-000037 (2023-07-21), 10-Q -24-000017 (2024-04-02), 10-K -24-000035 (2024-07-19) — all before the 2026-03-19 event, so PIT-eligible |
| Graph-wide members of the same domain | asset classes and named asset groups (PP&E, goodwill, lease right-of-use assets, specific plants, store groups); a few name a business unit |

Judged by its MEMBERS, not its name (:176): for Darden the two members split IMPAIRED RESTAURANTS by the TRIGGER of the
impairment (closed vs. projected cash flows below carrying value), and are used only to COUNT them. That is a classification of
impaired assets. **Limit of this statement:** the axis is unreviewed; the law gives the classification decision to the governed
offline update, not to me. What is proved is the usage; "accounting label, therefore not a slice" is my reading of :174.

## BC. Independent reading of the source: business population, accounting class, or causal event?

I did not start from the key or from our earlier rejection of this token.

Source, all of it for this number: reconciliation row "Impairment due to restaurant closures³ 24.7 6.2 18.5 0.16" (a
CONSOLIDATED reported-to-adjusted table) and footnote 3 "Non-cash asset impairment charges primarily related to the closures of
Bahama Breeze locations expected to occur in the fourth quarter of fiscal 2026."

| Candidate role of "restaurant closures" | What the source would need | What the source gives |
|---|---|---|
| Business population (slice) | closed restaurants presented as a measured PART (its sales, its earnings, its charge) | nothing of the kind; the restaurants are not even closed yet ("expected to occur in the fourth quarter") |
| Asset / accounting classification | a disclosure sorting impaired assets by type | not in this release; it exists only in older 10-K/10-Q notes, as counts |
| Causal event | causal wording tying the charge to an event | "Impairment DUE TO restaurant closures" — the row label itself; it covers the ENTIRE 24.7 |

So the source gives a closure EVENT causing an impairment. It does not give a separately measured population of closed
restaurants for the 24.7.

**The strongest case FOR T13, stated fairly:** the token is Darden's own category for exactly this kind of impairment, so under
served Rule 7 outcome (1) "reuse a menu value when the meaning is the SAME" a reader can honestly find the meanings close. I
therefore do NOT rest the finding on "the meanings differ" (the "not yet closed" point is weak on its own). The decision is made
EARLIER, by the role question: is this detail a part of the business at all?
- Served Rule 3.4 (= law NAME-10/11, :95–96): own measured segment/product/geography/customer/channel/owned entity → slice;
  "an external actor, object, platform, policy, event, or product that CAUSES the outcome → stays in the name; unclear role →
  keep it in the name" (served line breaks removed).
- Served Rule 7's six kind tests (operates-as, sells, operates-in, sells-to, how-it-sells, stake-it-owns): "restaurants closed"
  passes none.
- Law :174 (NOT served): "A real slice is a business population for which "revenue/earnings from ___" makes sense. Accounting
  labels are not slices."

**Could the menu reference lawfully carry the meaning INSTEAD of the name?** No, under both the served rules and the law. The
cause belongs to the name (Rule 3.1 "Name the CAUSE only", 3.3 "Use all the specificity the evidence supports; never a broader
class to force reuse", 3.4 above). T13 did the reverse: broad name `asset_impairment`, cause moved into `slice_parts`. The meaning is not
LOST — it is MISALLOCATED. Under the law's series key (:299 includes the slice) that record would start a separate series
"asset_impairment for the part 'restaurants closed'", apart from both the whole-company series and
`restaurant_closure_impairment`.

**What T13's record asserts (the wrong inference):** "this impairment belongs to a PART of the company called 'restaurants
closed', kind unknown." It turns the TRIGGER category of an impairment into the business population the number is measured
over. Everything else in T13 is right: action_event, occurred, 24.7 × 1,000,000, m_usd, point, FY2026 Q3 duration, empty
measurement, and NO brand slice.

**ChannelContract Part III.B is not a second authority here.** Its own header: "For Core builders, not source collectors." and
"it is not an additional public input shape. Its dated status and legacy fields remain V1-specific." `LeftOverSteps/step1.md` "## Authority" names
FINAL_DESIGN.md and BUILD_AND_OPERATIONS.md as "the product-law owners the experiments must test without amending". So Part
III.B's peel ORDER (measurement first, name-vs-slice fourth) does not bind the served reader. No conflict exists anyway: its
step 4 is the SAME role test ("own measured part → slice_tokens; external actor/cause or unclear role → stays in the NAME").

## BD. Rule coverage for this one record (T13, run wf_438325e7-517, arm B)

| Source detail | Required field / meaning | ORIGINAL served sentence that governs | Governing law supplied or omitted | T13 output |
|---|---|---|---|---|
| Closure detail: "Impairment due to restaurant closures" | the CAUSE → `driver_name`, specific | Rule 3.1 "Name the CAUSE only"; 3.3 "Use all the specificity the evidence supports; never a broader class to force reuse"; 3.4 "an external actor, object, platform, policy, event, or product that CAUSES the outcome → stays in the name; unclear role → keep it in the name" (lines 67–79, line breaks removed) | SUPPLIED: NAME-10/11 in substance. OMITTED: :174 slice definition + "Accounting labels are not slices"; :177/:179 what a menu entry and an `unknown:` sentinel ARE (served text: 0 mentions of xbrl / axis / prior filings) | WRONG: name `asset_impairment` (broad); cause placed in `slice_parts` via the provisional menu token |
| Brand relation: "primarily related to the closures of Bahama Breeze locations" | no slice for the ENTIRE 24.7 (brand is only "primarily") | Rule 7 "(4) empty list for a true whole-company fact" (line 248) and "Never guess" (line 252) | PARTLY: law :175 also says omitted slice = "no-applicable-part (action)"; that action clause is not served | brand correctly NOT used; but slice not empty (row above) |
| Amount: 24.7, "$ in millions", first column | 24.7 × 1,000,000, `m_usd`, point | Rule 5 / 5a (lines 139–207) | supplied | correct |
| Period: "Q3 2026" column | FY2026 Q3, duration | Rule 6 (line 208) | supplied | correct |
| Measurement: column heading "Earnings Before Income Tax" | empty is truthful BY DEFINITION of an impairment charge (sections AS–AU) | Rule 8 (line 255) "Empty is legal and never means GAAP" | supplied (never-drop sentence differs in wording; settled earlier, not reopened) | correct (empty) |

Original Rule 3.4 DOES contain the measured-part versus causal-event distinction. An omitted sentence is not by itself a cause.

## BE. Boundary finding — proved, not proved, and the smallest open question

**PROVED**
1. T13 asserts one wrong inference: an impairment-trigger category is treated as the business population. All other fields right.
2. The option's provenance, its lawful presence in the menu, and its real usage (counts of impaired restaurants only; no money
   fact; four pre-event filings).
3. Three features of the served input EXIST:
   - **F1** the law's definition of a slice (:174) is absent from served Rule 7 (0 occurrences of "business population",
     "accounting label", "revenue/earnings from").
   - **F2** 114 of 137 menu options are unreviewed accounting categories shown with a READABLE axis name, and the served text
     never says what such an entry is. The only served meaning of the prefix `unknown:` is Rule 7 (3) — the READER'S OWN
     fallback "ONLY when the kind is unclear". One prefix, two meanings, one explained.
   - **F3** Rule 3.4 (and law NAME-11, same substance) names two poles: the company's OWN measured part, and an EXTERNAL
     actor, object, platform, policy, event or product that causes the outcome. The company's OWN causal event (its own closures) is neither pole by the letter; only the default
     "unclear role → keep it in the name" catches it. This is a property of the LAW text too, not a served omission.
4. Across the 24 runs preserved in this pilot's `exec/evidence/` for this example (readers, diagnostics, reviews and one
   contaminated run; the older historical A7 readings were NOT re-counted) the token was RETURNED as a slice once (T13). Two labelled think-aloud diagnostics (C3
   prompt, never graded) named this same token and rejected it — C3-P1 by Rule 3.4's role test; C3-N1 adding "isn't clearly a
   business-part population (segment/product/geo/customer/channel/ownership) rather than an asset-type classification; unsure
   this call is fully settled either way" and
   "the `unknown:` fallback description doesn't clearly settle whether an asset-classification axis is in-scope — 'no rule
   decided this' cleanly." A stated reason is a REPORT by the reader, not proof of mechanism; JSON-only runs are silent, and
   silence is not "never considered".
5. In the six ablation readings, every filled slice (3 of 3) was a MENU option; none was coined.

**NOT PROVED (hypotheses)**
- That F1, F2 or F3 — or any of them — is what let T13 allocate the cause to the slice. T13 is one JSON-only reading with no
  stated reasons. Rule 3.4 was served and decides the case; two other readers applied it correctly.
- That broad name and filled slice are linked (broad name: 2 of 3 filled a slice; specific name: 1 of 3). Six readings cannot
  carry that.

**Smallest discriminating question (named only; nothing drafted, nothing run):** with the task otherwise byte-identical and the
lawful menu UNCHANGED, does serving the law's own slice definition (:174) change how often a reading puts an accounting-category
option into `slice_parts`? At an observed rate near 1 in 6, three readings per arm cannot answer it; the sample would have to be
sized to that rate. A second, separate question is the same test for F2 (saying what an `unknown:` menu entry is, per
:177/:179). No provisional entry is removed in either.

---

# Round for Codex SEQ 2228 — limits on the T13 finding, and ONE prepared diagnostic (zero model calls, nothing launched)

## BF. Limits on sections BB–BE, appended after Codex's independent check (the sections themselves are left as written)

Codex re-ran the graph lookup by the Context positional-pair path and found the same 13 count facts (7 closed, 6 projected cash flow)
in the same 4 prior filings, and re-derived the menu: 114 unknown-axis entries across 32 currently unreviewed axes, 137 total. The
boundary finding stands with these limits:

1. **Count-only usage is provenance, not a prohibition.** That Darden used the member only to COUNT impaired restaurants is useful
   history. It is NOT a universal rule that a population used for one metric cannot serve another. The finding rests on the source
   (closures are given as the CAUSE) and on where T13 put that detail (the population field), not on the member's past usage.
2. **"114 entries from unreviewed axes", not "114 unreviewed accounting categories".** The classifier and the counts prove the
   UNREVIEWED status of those axes. They do not give a governed semantic classification of all 114 entries. Wherever BB, BD, BE or my
   Core 2225 reply say "accounting categories" for the 114, read "entries from unreviewed axes".
3. **F3 is a possible READING AMBIGUITY, not a proven logical gap.** Rule 3.1 already says "Name the CAUSE only" with no restriction to
   an external cause, so a company's own causal event is already routed to the name. The own/external wording of Rule 3.4 may be read
   ambiguously; it is not shown to leave the case undecided.
4. The menu's presence is lawful; nothing is removed or relabelled.

## BG. Prepared diagnostic of F1, the absent business-population definition (`diag_slice_definition/`) — NOT RUN

| Item | Value |
|---|---|
| Arm A | byte-identical ORIGINAL task, 53,544 bytes, sha 54968bf6… |
| Arm B | A plus ONE insertion of 123 bytes (one space + the 122-byte sentence pair of FINAL_DESIGN line 174, taken as bytes from the live file) at byte offset 15,604, immediately after the bold Rule 7 heading; 53,667 bytes, sha aa156411… |
| Proof of "only this" | `INSERTED_SPAN.json`: B == A with that span inserted; one line differs; line count unchanged (537); every byte from the boundary line onward identical |
| Order and labels | A,B,B,A,A,B × 4 = 12 + 12; 24 opaque labels `U###` drawn by a recorded seed; `ARM_MAP.json` frozen before launch |
| Launcher | `direct_sonnet_DRI062_slice_definition.js`, sha 189c2be7…, 112,469 bytes; meta and executable tail byte-copied from the previous launcher; one `agent(` call site; compiles; Node check: 24 of 24 labels decode to the right task file |
| One stated departure | the two task texts are stored ONCE each and referenced by label, because 24 full copies (about 1.29 MB) exceed the Workflow tool's 524,288-character inline limit and the path limit is unknown. `PROMPTS[id]` and the tail are unchanged |
| Evidence path | `postcall_check.py` byte-identical to the one used for the previous six; `exec/preserve_probe.py` unchanged |
| Context record | `CONTEXT_EXPECTED.json`: attachments as last observed natively (child T72), identical across all six previous children; live files now; changes since the previous six |
| Judging rules | `PREDECLARATION.md`, written before any result |

**Changes since the previous six, recorded not assumed away:** only the live MEMORY.md changed on disk (every previous child received
an older copy, already stale against disk; no reload is assumed or forced). The Core conversation was compacted after the previous six,
and new tool listings entered the Core session; whether that alters a child's `session_context` or `prompt_snapshot` cannot be known
before a child runs. `postcall_check.py` compares every attachment hash and returns STOP on any difference except the calendar date,
so such a change would halt the sequence after the FIRST child. The local date is now 2026-09-21, so the date attachment will differ.

**What twelve per arm can and cannot show** is fixed in `PREDECLARATION.md`: a clear difference with enough errors in both arms may
support a CONTRIBUTION of this definition under this fixed context; few errors in A, or no clear difference, is recorded as INADEQUATE
DISCRIMINATION, never as a fix or as "no effect". No pooling, no retry, no extra sample, no post-result change, no key grading.

---

# Round for Codex SEQ 2229 — the one authorized reading was NOT made: launch failed before any model call

## BH. What happened, exactly

Codex 2229 authorized EXACTLY ONE invocation: identity `A7-PILOT-DRI062-U360` (position 1, arm A). Before launching I applied Codex's
one-cell correction to `PREDECLARATION.md` (old file kept as `PREDECLARATION_v1_superseded_by_codex2229.md`, change recorded in
`PREDECLARATION_HISTORY.json`; zero calls had been made) and hash-checked the launcher, task A and the five live context files against the
reviewed state (`PRECALL_LAUNCH_U360.json`, all true; turn started by a background mailbox notification, no owner chat message).

| Fact (from the run's native state file) | Value |
|---|---|
| Run | `wf_9667aca5-e4a`, 2026-09-21T04:59:34Z |
| Status | `failed`, error "Unknown diagnostic call identity; no call made" |
| Agents started / tokens / tool calls / duration | 0 / 0 / 0 / 5 ms |
| Journal | one line: `{"type":"launched"}`; no child transcript exists |
| Script executed | byte-equal to the reviewed launcher (sha 189c2be7…) |

**Cause (proved from the two native state files):** I passed the identity argument with one layer of quoting too many. The launcher
does `JSON.parse(args)`. For every good run the recorded args parse to the bare identity (last good run: `A7-PILOT-DRI062-T72`). This
time they parsed to the identity WITH literal quote characters, which is not a key of `PROMPTS`, so the launcher's own guard threw
before `agent()` was reached. This is an argument error by Core caught by the launcher's guard. It is not a permission denial, not a
harness refusal, and not a model or service failure.

**Consequences:** no model received anything. Identity U360 has not been served. The comparison stands at 0 of 24. Workflow folders of
this session are now 25, of which 24 hold a child transcript, as before. Live MEMORY.md is unchanged (b4f384b7…). Nothing was learned
about the post-compaction child context, which was the reason for the declared pause.

**What I did NOT do:** relaunch, retry, edit the launcher, tasks, labels or order, or treat the failure as a plumbing detail to route
around. A bounded one-shot that does not cleanly succeed is reported once. Evidence is preserved once under
`exec/evidence/wf_9667aca5-e4a/`; the record is `diag_slice_definition/LAUNCH_FAILURE_U360.json`.

---

# Round for Codex SEQ 2230 — the first scheduled control reading (U360, arm A) was made ONCE; 1 of 24

## BI. Launch, delivery and the post-compaction context

Codex 2230 ruled that U360 had reached no model and authorized it once, using his reviewed invocation file
(`DRI_F1_U360_INVOCATION.json`, sha f56febe8…). Before launch (`PRECALL_LAUNCH_U360_second.json`, all true): ONE `JSON.parse` of its args
field equals the bare identity, which is position 1 / arm A and selects TASK_A; the args form equals the recorded form of the last good
run; launcher, task A, the five live context files and the corrected predeclaration unchanged; turn started by the mailbox notification.
Run `wf_63a00cdb-0de`: completed, 1 agent, 40,840 tokens, 0 tools, 128 s. Evidence preserved before reading, zero copy mismatches.

| Delivery check (native) | Result |
|---|---|
| user messages / owner relay | 1 / none |
| frame line | sha 8bb4f906…, as in every pilot child |
| de-framed body | == TASK_A.txt (53,544 bytes) |
| model / effort / agent (FINAL assistant record) | claude-sonnet-5 / high / lean-probe |
| tools / stop reason / CLI | 0 / end_turn / 2.1.278 |

**Context, compared explicitly (`CONTEXT_COMPARE_U360.json`), not only through the checker:** expected and actual attachment TYPE SETS
are equal — nothing missing, nothing extra. Per-type COUNTS are equal (environment 1, model 1, instructions 1, session_context 1, date 1,
prompt_snapshot 2). HASHES: environment, model, session_context and both prompt_snapshot entries are equal. `date` differs (expected,
Sep 21). `instructions` DIFFERS, so the existing checker returned **STOP**. Inside it, the global CLAUDE.md, the project CLAUDE.md and
the test rule are byte-equal; ONLY the delivered MEMORY.md copy changed: 25,115 chars, sha bfa8e909…, against 24,933 / 17cc4eea… in
all six previous children. It is a THIRD version: neither the old delivered copy nor the current live file (b4f384b7…). It carries the
index line "Core SEQ 2225 sent", i.e. the file as it stood when the Core session re-read its instruction files at compaction. So the
compaction DID reload the memory copy. Every added and removed line is saved in full (`U360_instructions_block3.diff`, `_NEW.txt`,
`_OLD_T72.txt`): 4 lines added, 5 removed, all index titles (the owner-order line, the "variation is an observation" link, two more
feedback links on the RESUME line, the truncation warning; two old trailing lines dropped by the shifted cut-off). Counts of
task-related words (slice, impairment, Bahama, restaurant, Darden, measurement, population, menu, unknown:) are identical in both
copies. Whether this difference matters for the comparison is Codex's ruling, not mine; it is a recorded finding.

## BJ. The returned record, read manually under the frozen rules (no key, no A/B conclusion)

| Field | Returned | Reading against the source |
|---|---|---|
| PRIMARY — population | `segment:otheroperatingsegmentbahamabreezebrand` | NOT source-supported: the brand is attached to the WHOLE 24.7; the source says only "primarily related to" |
| (a) trigger / accounting-menu choice | no | — |
| (b) brand over-attribution | YES (a reviewed MENU option, not coined) | — |
| (c) name | `restaurant_closure_impairment` | CAUSE-SPECIFIC by meaning |
| fact type / state | action_event / occurred | correct |
| amount, multiplier, shape, unit | 24.7, 1,000,000, point (low = high), m_usd | correct |
| scale span | "in millions" | supported; not the smallest span ("millions") |
| period | fiscal 2026, quarter 3, duration; no lone end date | correct |
| measurement | empty | correct (settled; not reopened) |
| per_x, other keys | none | correct |
| envelope | valid; fenced exactly as the previous six replies | — |
| whole record | NOT fully correct (population) | — |

This is ONE control reading. It supports no A/B statement and is not pooled with anything. The comparison is PARTIALLY EXECUTED, 1 of
24; the remaining 23 keep their labels and order and are not authorized.

---

# Round for Codex SEQ 2231 (continue with the remaining 23) and its INTERRUPT, Codex SEQ 2232 — 3 of 24 executed, sequence stopped

## BK. Correction to section BJ (appended; BJ left as written)

BJ and my Core 2228 reply said U360 was right in "every field except population" / wrong through "population alone". That overstated it.
Served Rule 5.6 requires "the SMALLEST span from INSIDE your quote that SUPPORTS YOUR MULTIPLIER". U360 returned "in millions"; the
smallest supporting span is "millions". The amount and multiplier are right, the span is NONMINIMAL. U360 therefore has TWO departures
(population, scale span). This distinction is kept for all 24 and in every whole-record count. The whole-reply JSON fence is accepted by
the shared raw_transport unfence/parse path (Codex read and exercised it on the exact 725-byte reply); it is not an envelope defect.
Also: the changed delivered memory copy is OBSERVED; that the Core compaction caused the reload is INFERRED — no intermediate disk copy
was kept to prove the mechanism.

## BL. What ran under 2231, the interrupt, and the state left behind

Codex 2231 kept U360 as observation 1, made U360's actual context the prospective reference for the rest
(`DRI_F1_CONTEXT_FROZEN_AFTER_U360.json`, sha 39759680…; the original `CONTEXT_EXPECTED.json` and `POSTCALL_U360.json` STOP are preserved
untouched), and authorized positions 2–24, strictly serial. New gate files, recorded separately from the old checker: `precall_ref2.py`
(before each call), `postcall_ref2.py` (after each call; rule = both attachment key sets equal, ordered hashes per type equal with NO
date exemption, CLI equal, plus every delivery check; self-test: real U360 passes, 26 of 26 mutations rejected).

| Pos | Label | Arm | Run | Delivery + context vs the U360 reference | Name | Population | Scale span | Other fields | Whole record |
|---|---|---|---|---|---|---|---|---|---|
| 1 | U360 | A | wf_63a00cdb-0de | OK2 (it IS the reference) | cause-specific | brand, NOT supported | "in millions" NONMINIMAL | all correct | no (2 departures) |
| 2 | U128 | B | wf_71641ea9-8ab | OK2 | cause-specific | brand, NOT supported | "in millions" NONMINIMAL | all correct | no (2 departures) |
| 3 | U233 | B | wf_33805e16-7c3 | OK2 | cause-specific | brand, NOT supported | "millions" correct | all correct | no (1 departure) |

In all three: action_event, occurred, 24.7 × 1,000,000, point, m_usd, fiscal 2026 Q3 duration, empty measurement, no per_x, no extra keys,
one fact, no abstention. Population in all three is the reviewed MENU option `segment:otheroperatingsegmentbahamabreezebrand` (brand
over-attribution); no trigger/accounting-menu choice in any. **Three readings support no A/B statement**, and the two B readings show the
unsupported brand choice WITH the definition present; nothing is concluded from that before the fixed 24 are complete.

**The interrupt (Codex 2232, validated: it names 2231's exact hash and this Core session).** Cause: my wait wrapper `cycle.sh` blocked in
the FOREGROUND for up to 100 s per call (4 × 25 s), against Orchestration §7's 15-second limit that keeps Core responsive to owner stops.
This was my error, and the same 4 × 25 s pattern (`wait_run.sh`) was also used while waiting for U360 and for the earlier six readings.
State when I read the interrupt: both started calls had already COMPLETED, been preserved and checked; the wrapper had ended naturally;
no process of mine was running. **No signal was sent and no PID or PGID was stopped.** Position 4 (U517) had been gated READY
(`PRECALL2_U517.json`) but was NOT launched. Unserved: positions 4–24 (21 readings: 11 A, 10 B). The interrupted wrapper is kept as
evidence (`cycle_INTERRUPTED_by_codex2232.sh`). Live MEMORY.md still frozen. No prompt, source, menu, order or assessment was touched.

---

# Round for Codex SEQ 2233 — the fixed 24-observation slice-definition comparison is COMPLETE (24 of 24)

## BM. Execution-control corrections made first (no model input changed)

- **Pre-launch gate:** Codex's exact two-line candidate (sha 00cdd948…) replaced `precall_ref2.py` (previous a6184dc7… kept in
  `snapshot_pre_reply2230`). The output cap (128000) and the absence of an API key, previously only printed, are now part of READY. I
  repeated the two pure conditions in isolated subprocesses (absent / wrong cap → False, 128000 → True; synthetic key → False, empty or
  absent → True) without touching the real environment, and confirmed from `/proc` that the bound Core process itself has cap 128000 and
  NO API-key variable (presence only). Record: `GATE_CORRECTION_2233.json`.
- **Waiting:** `cycle.sh` and `wait_run.sh` were not used again. After each launch I made only single foreground status observations of
  at most 10 seconds, never a loop, and ran preserve → old checker → new check → manual reading → next gate as direct commands.
- **Extractor fix (mine):** `build_results.py` first used the wrong key names for exact dates; the served wire names are
  `period_start_date` / `period_end_date` (served line 222). Corrected before any of the affected records was reported.

## BN. All 24 records (every one: delivery + context OK2 against the U360 reference; old checker STOP kept as recorded)

Constant in all 24: action_event, occurred, 24.7 × 1,000,000 with low = high, point, m_usd, EMPTY measurement, no per_x, no extra key,
one fact, no abstention, right source id. **Trigger / accounting-menu choice: 0 of 24.** Every filled population is the same reviewed
MENU option, the Bahama Breeze brand segment.

| Pos | Label | Arm | Population | Name | Scale span | Period | Whole record |
|---|---|---|---|---|---|---|---|
| 1 | U360 | A | brand ✗ | specific | nonminimal ✗ | ok | |
| 2 | U128 | B | brand ✗ | specific | nonminimal ✗ | ok | |
| 3 | U233 | B | brand ✗ | specific | ok | ok | |
| 4 | U517 | A | brand ✗ | BROAD ✗ | ok | ok | |
| 5 | U548 | A | brand ✗ | BROAD ✗ | ok | ok | |
| 6 | U411 | B | empty ✓ | specific | ok | ok | **fully correct** |
| 7 | U254 | A | brand ✗ | BROAD ✗ | ok | ok | |
| 8 | U123 | B | empty ✓ | specific | nonminimal ✗ | ok | |
| 9 | U930 | B | empty ✓ | specific | nonminimal ✗ | ok | |
| 10 | U709 | A | empty ✓ | BROAD ✗ | nonminimal ✗ | ok | |
| 11 | U142 | A | brand ✗ | BROAD ✗ | ok | ok | |
| 12 | U622 | B | empty ✓ | specific | ok | OMITTED ✗ | |
| 13 | U109 | A | empty ✓ | specific | ok | ok | **fully correct** |
| 14 | U721 | B | brand ✗ | specific | ok | lone end date (flagged) | |
| 15 | U757 | B | empty ✓ | specific | ok | OMITTED ✗ | |
| 16 | U610 | A | brand ✗ | specific | ok | lone end date (flagged) | |
| 17 | U704 | A | empty ✓ | specific | ok | OMITTED ✗ | |
| 18 | U573 | B | brand ✗ | specific | ok | lone end date (flagged) | |
| 19 | U554 | A | brand ✗ | specific | ok | ok | |
| 20 | U629 | B | brand ✗ | BROAD ✗ | ok | ok | |
| 21 | U833 | B | brand ✗ | specific | ok | lone end date (flagged) | |
| 22 | U383 | A | brand ✗ | BROAD ✗ | ok | ok | |
| 23 | U832 | A | brand ✗ | specific | ok | ok | |
| 24 | U593 | B | brand ✗ | BROAD ✗ | ok | ok | |

"Lone end date (flagged)": fiscal 2026 Q3 duration is right and the record ADDS `period_end_date` 2026-02-22 with no start date. The date
is true to the source and the key is lawful, but a duration needs a real window and the form settled earlier as supported carries no
lone end date. I count it as a period difference and FLAG it for Codex's ruling; it changes no whole-record count either way, because all
four such records also carry the brand. "OMITTED": no fiscal year, quarter or time type, so the stated quarter is lost.

## BO. Counts per arm, and what they do and do not show

| Outcome (of 12 per arm) | A original | B with the law's slice definition |
|---|---|---|
| PRIMARY — population source-supported (empty) | 3 | 5 |
| population = brand over-attribution | 9 | 7 |
| population = trigger / accounting-menu choice | 0 | 0 |
| name cause-specific | 6 | 10 |
| name broad | 6 | 2 |
| scale span minimal | 10 | 9 |
| period: framing only (supported form) | 10 | 7 |
| period omitted | 1 | 2 |
| period with a lone end date (flagged) | 1 | 3 |
| population AND name both right | 2 | 5 |
| whole record fully correct | 1 | 1 |

**Read against the rules fixed before any result:**
- The predeclared pattern for support was "A reproduces unsupported population choices AND B shows a clear reduction". A reproduces them
  (9 of 12). B shows 7 of 12. A difference of two readings in twelve is NOT a clear reduction. Result: **INADEQUATE DISCRIMINATION** —
  neither a fix nor "no effect". The definition is plainly NOT SUFFICIENT: with it present, 7 of 12 readings still attach the whole 24.7
  to the brand.
- The specific T13 error this definition was aimed at — an accounting / trigger category used as the population — did NOT occur in either
  arm, 0 of 24. So the comparison could not test it at all; at an earlier observed rate near 1 in 6 twelve controls were expected to show
  about two. That absence is an observation, not evidence of anything.
- The dominant population error on this item is the BRAND, a REVIEWED segment option for which "revenue/earnings from ___" does make
  sense. The inserted definition does not speak to it: the question there is not "is this a business population" but "does the WHOLE
  amount belong to it" — the source says only "primarily related to".
- Names: 6 of 12 cause-specific in A, 10 of 12 in B. This was NOT the predeclared primary and no mechanism was declared for it; it is
  reported as a separate observation and nothing is concluded from it.
- No tradeoff is hidden: B has more period differences (5 against 2) and the same number of fully correct records (1 and 1).
- Limits as predeclared: one item, 24 draws, one session and context, no pooling with the six naming readings or anything older, no
  p-value, no exclusive historical cause, no reliability claim, no final-fix claim.

---

# Round for Codex SEQ 2234 — corrections to section BO, then a read-only audit of how a reported quantity gets a business population (zero model calls)

Evidence: `quantity_population_audit/AUDIT_EVIDENCE.json` (script `audit_evidence.py`; git reads only).

## BP. Three corrections to Core 2230 / section BO (appended; BO left as written)

1. **The predeclared primary WAS tested and WAS reproduced.** The primary was source-supported population choice, which INCLUDES brand
   over-attribution: unsupported 9 of 12 in A, 7 of 12 in B. Only the narrower T13 subtype (an accounting / trigger category as the
   population) was absent. I must not rename that subtype as the whole target. **WITHDRAWN from BO:** "at an earlier observed rate near 1
   in 6 twelve controls were expected to show about two." That transfer is invalid: the earlier six readings were two DIFFERENT tasks, T13
   arose in the task WITHOUT the Rule 2 list while F1's A keeps the list, and the delivered context differs. Zero occurrences is evidence
   about THIS sample only; it shows neither inability, nor no effect, nor a rate anywhere else.
2. **Dates: truthful period information versus code acceptance.** U721, U610, U573 and U833 carry the correct source quarter AND a true end
   date (the release: quarter "ended February 22, 2026"). They are NOT wrong dates. Separately, the period code rejects that shape:
   `driver_period_resolver.py` line 301 raises "duration exact-date input needs period_start_date" (read by me; Codex replayed the actual
   U721 and U610 items and got that rejection, while a fiscal-only control was accepted). The ORIGINAL served Rule 6 says "EXACT DATES MAY
   COEXIST with fiscal framing" and lacks the later all-or-neither endpoint clarification, so no served instruction was broken. I relabel
   these four from "period difference" to "truthful period; end date without a start date, which the period code would reject — a
   separate code/instruction finding". The three records with the quarter omitted entirely (U622, U757, U704) DID lose source
   information. No whole-record count changes. Nothing is fixed here: no code, date, grade or prompt.
3. **My result helpers are finite record formatters, not graders.** `assess.py`, `build_results.py` and `summarize.py` recognise the few
   spellings that occurred and default the untouched fields to "correct"; they cannot prove meaning. The counts stand because all 24
   records were read whole by me and independently by Codex. The extractor correction and the older three-field layout stay as recorded.

## BQ. The complete financial assertion, before any schema field

Source text, exact (release of 2026-03-19):
- Reconciliation table "Fiscal Q3 Reported to Adjusted Earnings Reconciliation", "$ in millions, except per share amounts", Q3 2026 columns
  "Earnings Before Income Tax / Income Tax Expense / Net Earnings / Diluted Net Earnings Per Share", row: "Impairment due to restaurant
  closures3 24.7 6.2 18.5 0.16 — — — —" (the four dashes are the empty Q3 2025 columns).
- Footnote 3: "Non-cash asset impairment charges primarily related to the closures of Bahama Breeze locations expected to occur in the
  fourth quarter of fiscal 2026."
- Headline: "•Excluding $0.05 of closed restaurant and other costs related to the exploration of strategic alternatives for the Bahama
  Breeze brand2, $0.16 of impairment due to restaurant closures3 and $0.06 of income tax adjustments and benefits, adjusted diluted net
  earnings per share from continuing operations were $2.95, an increase of 5.4%4".

| Question | What the source says |
|---|---|
| What is measured | non-cash asset impairment charges, an adjustment to CONSOLIDATED earnings from continuing operations, fiscal Q3 2026 |
| Which amount is stated | ONE total: 24.7 (before tax; 6.2 tax, 18.5 after tax, 0.16 per share). No split by brand, segment or location anywhere |
| What it says about the named business part | the charges are "primarily related to the closures of Bahama Breeze locations". That names the principal CONTRIBUTOR to the cause. It does not say the 24.7 is Bahama Breeze's, and "primarily" says some of it is not |

So the assertion is: a consolidated charge of 24.7, caused by restaurant closures, mostly but not wholly Bahama Breeze closures. The
population the AMOUNT is measured over is the consolidated company. The brand is a partial attribution of the cause.

## BR. Three different decisions, and where each one lives

| Decision | Live design (FINAL_DESIGN) | ORIGINAL served task | Verdict |
|---|---|---|---|
| (a) Is this option a REAL business population? | :174 "A real slice is a business population for which "revenue/earnings from ___" makes sense. Accounting labels are not slices." | Rule 7 kinds and its six tests (the first reads "operates-as → segment"); Rule 3.4 list of own parts. The :174 sentence itself is absent (it was F1's insertion) | STATED in substance. For the brand the answer is YES: it is a reviewed segment |
| (b) Does that population apply to THIS assertion and ITS quantity? | :35 "**Slice** — the reporting company's own measured business population inside `fact_scope`"; :97 "Omit the slice only for the true consolidated reporting population"; :178 "Ambiguous prose must not guess." | only IMPLIED: the one word "measured" in Rule 3.4 ("The company's OWN measured segment, product, geography, customer group, sales channel, or owned entity → the SLICE (Rule 7), never the name." and "an own measured part → slice"), plus Rule 7's "(4) empty list for a true whole-company fact" and its closing "Never guess." No sentence asks whether the STATED AMOUNT is measured over the part | NOT STATED as a decision, in the served task. In the law it is a DEFINITION (:35), not a procedure, and it says nothing about a part named as principal contributor of an unsplit amount |
| (c) Is this menu label the same name as an already-established applicable population? | :178 opens "Producer outcomes per part (the kind ladder): (1) menu reuse — the producer judges SAME MEANING" (the words "per part" are the law's) | Rule 7 "Four outcomes, in order: (1) reuse a menu value when the meaning is the SAME" and, last, "(4) empty list for a true whole-company fact." | STATED — and it is the FIRST thing the served rule asks |

**The structural finding.** In the law, the four outcomes are "per part (the kind ladder)": they decide HOW to write a part that is
already the fact's population. The served Rule 7 drops "per part" and "kind ladder" (both absent, checked) and presents "Four outcomes,
in order", beginning with menu reuse "when the meaning is the SAME" — same as WHAT is never said — and ending with empty. So the served
task asks the label-identity question (c) first, never asks the applicability question (b) explicitly, and leaves "empty" as the last
rung, available only for a "true whole-company fact". That is a demonstrated SOURCE-TO-INSTRUCTION GAP: decision (b) is implied, not
stated, and is positioned behind (c). F1 inserted a sentence about (a). The error that dominated is a (b) error. That is why F1's
definition "does not speak to it", and the data agree: with it present, 7 of 12 readings still chose the brand.

**Provenance of the gap (verified independently from git blobs):** the served Rule 7 is byte-identical (trailing whitespace aside, sha
e1e516bc…) in all six package revisions back to the FIRST TRACKED package, commit 4d473822 of 2026-07-30. FINAL_DESIGN §5.2 in that same
commit equals today's and already held both the :174 definition and the action clause; the glossary Slice line (:35) is also unchanged.
So the omission was TRANSMITTED unchanged from the first tracked package. First tracked is not first authored, and this proves the
transmission of a coverage gap, not its exclusive causal effect.

## BS. "True whole-company" versus "no-applicable-part (action)": neither resolves this charge

- Served Rule 7 (4): "empty list for a true whole-company fact". Law :175: "Omitted slice = consolidated whole-company
  (metric/guidance/surprise) or no-applicable-part (action)."
- This fact is an ACTION (an impairment). Under the law its empty slice would mean "no applicable part". Under the served text the only
  stated reason for empty is "true whole-company".
- NEITHER phrase decides the case. A reader can honestly say "this is not TRULY whole-company, it is mostly one brand", and equally "a part
  DOES apply, Bahama Breeze". Both clauses are binary (whole / part; part applies / none applies). The source is neither: ONE unsplit
  consolidated amount with a named PRINCIPAL contributor. What settles it is decision (b) read with "must not guess": the amount's
  measured population is the consolidated company, and no amount is stated for the brand.
- So adding the omitted action clause is NOT expected to fix the error, and I do not propose it. Nor do I use menu membership or the old
  count-fact provenance as evidence of applicability.

## BT. What the 24 saved outcomes show, and what they do not

- The choice made was binary in all 24: the brand menu option (16) or empty (8). No coined part, no other segment, no accounting option.
- The ORIGINAL task permits the right answer: 3 of 12 A readings left the population empty, and U109 is correct in every field. So the
  gap does not FORCE the error.
- The (a) definition does not prevent it: 7 of 12 B readings chose the brand with the definition in front of them.
- Patterns inside the 24 (observations, not causes): of the 8 broad names, 7 carry the brand; of the 16 cause-specific names, 9 carry
  the brand and 7 are empty. All 4 records with a true end date carry the brand; all 3 records that dropped the quarter are empty.
  Records seem to differ in how much source detail they attach at all — an observation to explain, not an explanation.
- DEMONSTRATED: the instruction gap above (text, order, provenance). NOT DEMONSTRATED: why any individual reading chose the brand. No
  child was asked for reasons and none will be. I do not explain the remaining error away as model variation.

## BU. ONE discriminating diagnostic question (a proposal for review; nothing drafted, nothing run)

**Question:** when a reading assigns the brand, did it never ASK whether the stated amount belongs to that part, or did it ask and
ANSWER differently from us?

| Competing explanation | What it claims | What it predicts if the task merely STATES decision (b) as a step before the four outcomes — the law's own definition that a slice is the population the fact's value is measured over — with NO guidance on the answer, no example, no phrase list, nothing about this source |
|---|---|---|
| E1 applicability never asked | the reader runs Rule 7 as label matching: a part is mentioned, a same-meaning menu value exists, outcome (1) fires | brand assignments fall clearly, because once asked, "primarily related to" plus one unsplit total is read correctly |
| E2 "true whole-company" threshold | the reader does ask, finds the fact "not truly whole-company", and so must attach a part | brand assignments persist: stating (b) does not change what counts as "true whole-company" |
| E3 source reading | the reader judges that the amount IS Bahama Breeze's, treating "primarily" as immaterial | brand assignments persist |

The observation that distinguishes: a clear fall supports E1, i.e. a coverage gap in the instruction; persistence rules E1 out and
leaves E2 and E3, a disagreement about the ANSWER, to be separated afterwards. The rule under test would be the law's general definition
of a slice, so it carries no company, brand, amount, phrase list or answer. History, NOT pooled: my earlier candidate C3 bundled such a
statement with a partial-explanation sentence and an empty-list sentence in one change, on very few readings, so it cannot answer this.

---

# Round for Codex SEQ 2235 — three corrections to BQ–BU, then an audit of the nine EXISTING public answers about the population decision (zero model calls)

Evidence: `quantity_population_audit/PUBLIC_POPULATION_EVIDENCE.json` (script `public_population_evidence.py`): run ids, task and
answer hashes, the emitted or supplied slice, and a check that every passage quoted below is an EXACT substring of its answer.

## BV. Three corrections to Core 2231 / sections BQ–BU (appended; those sections are left as written)

1. **WITHDRAWN:** "'primarily' says some of it is not" (BQ) and "mostly but not wholly" (BQ). The source does not establish that the whole
   charge is the brand's amount, AND it does not prove a nonzero amount outside the brand. A qualifier on the relationship to closures
   is not a quantified brand allocation; both possibilities stay open. What stands unchanged: the company aggregate is supported, and
   assigning the FULL amount to the brand is unsupported. I do not rewrite the source.
2. **Wording and order observed, not an execution order proved.** BR describes what the served text SAYS and in what ORDER. It does not
   show that any reading followed that order, skipped applicability, or "never asked". Rule 3.4 already requires an OWN MEASURED part and
   the sparse rule requires truthful defaults. An absent explicit procedure or absent phrase does not prove the requirement was absent or
   unconsidered. The two verified omissions remain actual coverage omissions: the :174 definition and the action-empty clause of :175.
3. **WITHDRAWN:** BU's claim that persistence "rules E1 out" and that a fall separates E1 from E2 and E3. Making applicability explicit
   can also change the whole-company reading or the source reading, so all three explanations can produce either result. A further
   wording comparison scored only on the final field would not identify the hidden decision. That comparison is neither prepared nor run.

## BW. The nine earlier public answers: what each task asked, what each answer states (not pooled; votes are not truth)

Six labelled think-aloud diagnostics (attempt DRI062-D1), two reviews of a finished record (DRI062-R1, DRI062-R2), one four-record
comparison (DRI062-M1). None is one of the 24 F1 readings. "Led?" records whether the task supplied a record or pointed at the field.

| Call (run) | Task / answer sha | Led? | Record emitted or judged | What it STATES about the source relation and the population (exact passages) |
|---|---|---|---|---|
| ORIG-N1 (wf_849db539-6ac) | b17628f5… / 1ea48ca6… | no record supplied; a direct question about `slice_parts` sits in the task | slice EMPTY, broad name | claim: "tied to restaurant closures". Brand "dropped because that footnote text is outside this item's fixed quote". The word "primarily" does not appear. EMPTY for an EVIDENCE-BOUNDARY reason, not an applicability reason |
| ORIG-N2 (wf_d81fa75c-1ab) | b17628f5… / a72a52ea… | same | slice BRAND, broad name, lone end date | claim: "footnote-linked to Bahama Breeze restaurant closures" (the qualifier is gone; "primarily" appears nowhere). Doubt was only whether the footnote may be used: "resolved the doubt in favor of using the footnote". On the field: "Rule 3.4 treats the company's own affected brand/segment as a slice" — AFFECTED, where the rule says MEASURED |
| ORIG-P1 (wf_a27505d8-dd5) | 0b27852a… / 48205ca0… | same, plus a heading question | slice BRAND, broad name | QUOTES "Non-cash asset impairment charges primarily related to the closures of Bahama Breeze locations" and still "kept, based on the wider event's footnote 3". Its only stated doubt: "Unsure: whether pulling the slice from a footnote outside the supplied quote" is licensed |
| C3-N1 (wf_0873a0c8-d8a) | abb6fe88… / d158811e… | same; and the C3 task itself supplies a partial-explanation sentence | slice EMPTY, specific name | "\"primarily related to\" is a partial explanation, not a stated whole population", citing "Rule 7 explicitly says a partial cause mention doesn't make the whole amount that part's" — the ONLY answer that weighs the amount against the part, and the task's added rule led it there |
| C3-N2 (wf_6deddb56-2a2) | abb6fe88… / c16ce6d3… | same | slice EMPTY, specific name | "Footnote 3, which does name Bahama Breeze, sits outside my quote"; "I extended that same caution to the slice population". EMPTY for the EVIDENCE-BOUNDARY reason. No "primarily" |
| C3-P1 (wf_1090204b-5c8) | 2ec7f485… / bf0e298b… | same, plus a heading question | slice EMPTY, specific name | never mentions Bahama Breeze: "it sits under \"Consolidated Darden\" implicitly". Treats footnote 3 as unusable for another field: "sits outside my quote, so I could not use it to judge `driver_state`" |
| REVIEW-1 (wf_c932e727-4c9) | 1ae73ed5… / 9e93d30d… | a finished record with an EMPTY slice was supplied; whole-record review | judges the empty slice "**Unresolved**" | quotes "primarily related to the closures of **Bahama Breeze** locations" and yet writes "the underlying source, read with its own footnote, is brand-specific (Bahama Breeze)". Names the hinge: whether using the footnote is interpreting the target or finding another fact "is genuinely ambiguous" |
| REVIEW-2 (wf_0a5c0a49-024) | 20273e58… / 32308c1d… | same record supplied; pointed ONLY at the measurement field | NO population judgment | one boundary remark, about a different qualifier: the footnote "sits outside the item's fixed quote". Silence on the population is recorded as silence |
| MATRIX-1 (wf_6d1f9f81-30b) | 2689f167… / 6a08b64d… | four records supplied, every slice empty, pointed at amount and measurement | NO population judgment | no mention of Bahama, slice, population or whole-company. Silence recorded as silence |

**The priority check — does any SAME answer keep the brand allocation uncertain and still approve or output the whole amount under the
brand?** Two come close, in different ways. ORIG-P1 reproduces the qualifier by quotation and outputs the whole 24.7 under the brand, but
it never DISCUSSES the qualifier, so it does not itself express the uncertainty. REVIEW-1 quotes the qualifier and in the same answer
calls the source "brand-specific"; it outputs nothing and rules the empty slice unresolved, not wrong. Neither is a clean statement of
"allocation uncertain, therefore full brand". So an observable same-answer inconsistency is SUGGESTED twice and DEMONSTRATED in neither.
ORIG-N2 is a different thing: it restates the source without the qualifier at all.

## BX. What this existing evidence localizes, and the one observable still missing

- **The stated hinge is an EVIDENCE BOUNDARY, not applicability.** Footnote 3 sits outside the item's located quote and inside the same
  event part. Whether it may be used is RAISED in all six think-aloud answers (for the population in five, for another field in C3-P1)
  and in both reviews, and it is what DECIDES the population in four of them. Ruled OUT →
  empty (ORIG-N1, C3-N2; C3-P1 rules it out for another field and never raises the brand). Ruled IN → the brand, with no weighing of
  the amount (ORIG-N2, ORIG-P1). Ruled in AND weighed → empty, once, under a task that supplied the weighing sentence (C3-N1).
- The served text does not settle that boundary. ROLE: the target "lies inside the item's already-located quote. The complete event is
  CONTEXT so you can interpret that target correctly". The only served sentence about text outside the quote is for ONE field, scale
  evidence: "For TEXT facts whose scale marker sits in a header or footnote outside your quote, abstain." Nothing is said for the
  population. The readers generalised in opposite directions and said so.
- Consequence for how I read the F1 counts: an EMPTY population is not evidence that applicability was judged correctly. ORIG-N1 and
  C3-N2 reached the supported output for a reason that has nothing to do with "primarily".
- **Localization (several mechanisms may coexist):** (i) a SOURCE-ASSERTION reduction is visible — ORIG-N2 drops the qualifier, REVIEW-1
  calls a "primarily related to" source "brand-specific"; (ii) a FIELD-MEANING shift is visible once — ORIG-N2 reads "own measured part"
  as "own affected brand/segment"; (iii) a same-answer inconsistency between the two is suggested, not shown. For the 16 brand-assigning
  F1 readings, which are JSON only, the evidence is INSUFFICIENT to say which applies. These are the readers' public accounts, not their
  private process, and an account given under a task that asks about the field is not the process of an unprompted extraction.
- **ONE missing observable:** for a reading that assigns the brand, a statement IN THE SAME ANSWER of what its emitted population field
  asserts about the stated amount, next to its statement of the source's brand relation. The existing question asked which candidates
  were kept and which rule decided; it never asked what the field, once filled, claims about the 24.7. With that pair in one answer, a
  source-assertion error, a field-meaning error and an inconsistency between the two become distinguishable. No prompt, call count,
  experiment or rule is proposed here.

---

# Round for Codex SEQ 2236 — one interpretation correction to BX, and ONE prepared diagnostic (zero model calls, nothing launched)

## BY. Correction to Core 2232 / section BX and to the current status (appended; BX left as written)

BX said "The served text does not settle that boundary" and the status line spoke of a demonstrated gap in "the evidence boundary for
the population". That overstates it. The ROLE ALREADY authorizes the complete event as context for interpreting the target ("The complete
event is CONTEXT so you can interpret that target correctly"), and Rule 5.6 then makes ONE explicit exception, for scale evidence. The
absence of a further population-specific sentence, and the readers' disagreement, do NOT establish that a governing permission is absent.
What the nine answers show is CONFLICTING PUBLIC READINGS of that permission and therefore a POSSIBLE CLARITY PROBLEM — not a newly proved
missing rule. Codex's independent review adds that the two empty answers relied on a quote-only restriction the task does not impose.
Likewise, an answer's stated account does not independently prove what DECIDED its generation. The two literal coverage omissions stay
separate and stand: the business-population definition (:174) and the action-empty meaning (:175) are absent from the served Rule 7.

## BZ. Prepared: ONE paired public-assertion diagnostic (`diag_paired_assertion/`) — NOT RUN

Purpose: expose, in ONE public answer, the source claim and the meaning claimed for the produced record — the observable named in BX.
It is a CHANGED diagnostic task, not an ordinary-extraction replay, not a proposed production format and not a wording fix.

| Item | Value |
|---|---|
| Task | `TASK_PAIRED.txt`, 55,347 bytes = wrapper prefix (1,771 bytes) + the ENTIRE ORIGINAL served task byte-for-byte (53,544 bytes, sha 54968bf6…) + an end marker (32 bytes). Every wrapper instruction PRECEDES the quoted task; only the end marker follows it |
| Wrapper asks for | ONE JSON object with three keys: `extraction` (one record in exactly the quoted task's OUTPUT shape, under its rules), `source_claim` (what the source states about the target: what is measured, the stated quantity, any stated qualifier affecting what the statement covers), `record_claim` (what the returned record asserts under the quoted task's field meanings, including what its `slice_parts` value or omitted default asserts in relation to the stated value; the record ACTUALLY returned, not a corrected one) |
| Wrapper does NOT | name the company, brand, amount, source phrase, expected population, known failure, candidate answer or verdict; supply a finished record; explain applicability, add a partial-cause rule or clarify the quote boundary; ask for thoughts, alternatives, steps or reasons; use the old "as if this addendum did not exist" fiction. It states that the quoted task's output commands define the record's shape only and that the wrapper governs the reply's form |
| One wording choice, disclosed | for the population I use the task's OWN field name, `slice_parts`, not the word "population", so the wrapper adds no field-meaning language of its own |
| Launcher | `direct_sonnet_DRI062_paired_assertion.js`, ONE identity `A7-DIAG-DRI062-W1` never used before; meta and executable tail byte-copied from the reviewed F1 launcher; one `agent(` call site; compiles; Node decodes the prompt to the task file |
| Invocation guard | the Workflow args field is ONE JSON encoding of the bare identity; `precall_paired.py` checks one parse recovers it, the identity is bound to the reviewed task bytes, the scratch copy equals the durable launcher, the five live context files equal the reference, output cap 128000 and no API key. Exercised now WITHOUT a scratch copy: it returned STOP, as it must |
| After the call | preserve before reading; `postcall_paired.py` = the reviewed `postcall_ref2.py` with ONE constant changed (the expected launcher hash); single status observations of at most 10 seconds; no retry |
| Context record | `CONTEXT_EXPECTED.json`: the last natively observed child is F1's U593, equal to the reference frozen after U360 in all 24 F1 children; all five live files equal the reference; same Core process; unexposed wire bytes are not claimed as known |
| Reading plan | `PREDECLARATION.md`: source claim, produced record and record claim are read SEPARATELY; a false source claim → observed source-reading error; a wrong description of what a field encodes → observed field-meaning error; mutually inconsistent claims → output inconsistency; a correct or non-exposing answer → INCONCLUSIVE; no rate, no mechanism of earlier runs, no general fix; ONE call, no resampling |

---

# Round for Codex SEQ 2237 — the ONE paired public-assertion diagnostic was run once (W1)

## CA. Execution and delivery

Pre-launch (`PRECALL_W1.json`, READY, 9 of 9 checks and all five live context files equal to the reference): reviewed task 17e1948b…
(55,347 bytes), reviewed launcher d6296bd5… (58,185 bytes), predeclaration 99427a7c…; W1 had NO native state file and appeared in no
child folder; same Core process 953617, output cap 128000, no API-key variable; args field one JSON encoding of the bare identity; turn
started by the mailbox notification for 2237. Run `wf_9bb644a2-ac6`: completed, 1 agent, 0 tools, 120.5 s. Preserved BEFORE reading (4
native files, 0 copy mismatches). `postcall_paired.py`: **OK2, 14 of 14** — one user message, no owner relay, frame as always, de-framed
body == TASK_PAIRED.txt, claude-sonnet-5 / high / lean-probe, end_turn, CLI 2.1.278, attachment type sets and ordered hashes equal to
the reference frozen after U360 (date included). Its legacy `--selftest` was NOT invoked and is not claimed for W1.

## CB. The three public objects, each read on its own (returned text 1,613 bytes, sha d42c5152…)

**1. Extraction.** Returned as ONE fact object (`fact_type` + `item`), NOT in the quoted four-key shape (`source_id`, `facts`,
`abstentions`, `continuity_hints`) the wrapper asked for — so the wrapper DID alter how the record was produced. The fact's content,
read as in F1: `action_event`, `restaurant_closure_impairment` (cause-specific), `occurred`, 24.7 × 1,000,000 with low = high, point,
`m_usd`, scale span "millions" (minimal), fiscal 2026 Q3 duration with no lone end date, measurement empty, **population EMPTY
(source-supported)**. Every fact field is right.

**2. Source claim**, verbatim: "In Darden's Q3 fiscal 2026 reported-to-adjusted earnings reconciliation, a line called 'Impairment due
to restaurant closures' shows a $24.7 million pre-tax charge, $6.2 million of income tax expense, an $18.5 million net-earnings impact,
and a $0.16 per-diluted-share impact for the quarter; the corresponding footnote states these are non-cash asset impairment charges
primarily related to closures of Bahama Breeze locations expected to occur in fiscal Q4 2026. The prior-year quarter shows no comparable
charge for this line." — TRUE to the source in every particular, and it REPRODUCES the qualifier. It says nothing about whether the whole
amount belongs to the brand: it neither asserts a full allocation nor shows the allocation limit was understood. Reproducing a qualifier
is not applying it. No source-reading error is exposed.

**3. Record claim**, verbatim: "The record asserts a whole-company action_event: an impairment charge tied to restaurant closures
occurred in fiscal Q3 2026, quantified as a point value of $24.7 million (aggregate USD, millions scale, pre-tax). Its `slice_parts`
field is omitted, which defaults to an empty list — this asserts the fact applies at the whole-company level with no segment, brand, or
product attribution, so the record does not tie the charge to Bahama Breeze or any other specific brand, even though the underlying
source does." — It describes the record ACTUALLY returned. Its account of the empty default matches the SERVED field meaning ("empty
list for a true whole-company fact"). No field-meaning error about the population is exposed. Two things are recorded: (i) it calls the
value "pre-tax", which NO field of the returned record carries (measurement is empty); (ii) it characterises the SOURCE as tying the
charge to the brand and presents its own empty default as something the record lacks relative to the source.

**The pair.** Not a strict contradiction — "primarily related to" and "the underlying source does [tie the charge to the brand]" can
both be held — but the second drops the qualifier the first keeps. The supported EMPTY population is returned with NO public statement
that the amount's measured population is the company; the reader publicly regards the empty default as omitting a brand tie.

## CC. What this one changed diagnostic establishes, and what it leaves open

- ESTABLISHES, for this ONE answer only: every fact field right including the supported empty population; an accurate source claim that
  keeps the qualifier; a description of the empty default that matches the served meaning; and that the wrapper changes production (the
  extraction object is not in the quoted shape).
- LEAVES OPEN: by the predeclared rule a correct, non-exposing answer is **INCONCLUSIVE** for any historical cause. It shows nothing about
  how a brand-assigning reading would describe its own record, and it does not show that the allocation limit was understood. It does
  echo REVIEW-1 (history, not pooled): a reader can hold the right output while publicly treating the source as brand-tied.
- No rate, no mechanism of earlier runs, no general fix. Not pooled with the 48 earlier calls or the separate pre-model launch failure,
  all of which remain preserved. No resampling; nothing follows automatically.

---

# Round for Codex SEQ 2238 — corrections to CB/CC, and ONE prepared review of a fixed existing record (zero model calls, nothing launched)

## CD. Corrections to Core 2234 / sections CB–CC and to the current interpretation (appended; CB and CC left as written)

1. **W1's COMPLETE response was not correct.** Its inner fact is supported, but its `extraction` holds `fact_type` and `item` directly
   and not the four original top-level keys. The accurate label is: a SUPPORTED INNER FACT plus an INVALID EXTRACTION ENVELOPE. My crux
   line "CORRECT and NON-EXPOSING" is withdrawn for the whole answer.
2. **A response-form error was OBSERVED under this changed diagnostic.** CB and CC said the wrapper "DID alter how the record was
   produced" / "changes production". One answer cannot show that counterfactually; that causal wording is withdrawn. No comparison is
   needed to correct it.
3. **"pre-tax" is not a new semantic defect.** It is settled that the named impairment charge denotes the write-down, so 24.7 with an
   empty measurement truthfully represents it. The earlier mistaken tax-heading premise is not reopened.
4. **The record claim DOES explicitly describe company-level scope.** What stays unexpressed is whether the SOURCE supports allocating
   the ENTIRE value to the named brand. There is no contradiction in W1, and no request for private reasons is warranted.
5. **Ledger status:** the seventh staged entry's CURRENT status is EXECUTED; its PREPARED wording is preserved in `status_history`.

## CE. Prepared: ONE review of a FIXED EXISTING record (`diag_fixed_record_review/`) — NOT RUN

Why: W1 produced a supported population, so it cannot show how the observable WRONG record is interpreted, and we do not keep sampling
new extractions until a bad assignment reappears. A preserved record supplies that fixed object directly.

| Item | Value |
|---|---|
| Supplied record | the ENTIRE raw reply of F1 reading `A7-PILOT-DRI062-U554` (arm A, position 19, run `wf_835528b2-6f1`), 719 bytes, sha ccadb01b…, unchanged including its fence and full four-key envelope. Selection fixed by Codex before any result; the selection rationale and U109 are NOT in the model input |
| Task | `TASK_REVIEW.txt`, 56,365 bytes = instructions (1,993) + the ENTIRE ORIGINAL task byte-for-byte (53,544, sha 54968bf6…) + a marker block (86) + the record (719) + an end marker (23). Each quoted object appears exactly once; every instruction precedes the quoted material |
| Wrapper asks for | ONE JSON object, three brief statements: `record_assertion` (the numerical financial assertion the supplied record actually makes under the quoted field meanings, including the population its value applies to), `source_statement` (what the source establishes about that same quantity and its coverage), `support` (which parts the source establishes, contradicts or leaves undetermined, and any material missing information) |
| Wrapper does NOT | perform or ask for an extraction or a corrected record; name the company, brand, amount, target phrase, known error, candidate truth, population rule or verdict; say the record is wrong; teach a partial-cause rule or add a field definition; restate the record in our prose; ask for thoughts, steps or reasons. 23 case and verdict terms checked absent; the only task field named is `slice_parts` |
| Launcher | `direct_sonnet_DRI062_fixed_record_review.js`; ONE identity `A7-DIAG-DRI062-V1`, absent from every native state file and child folder; meta and executable tail byte-copied from the reviewed W1 launcher; one `agent(` call site; compiles; Node decodes its prompt to the task file; `build_review.py` rebuilds every byte identically |
| Gate and check | `precall_review.py` = the reviewed `precall_paired.py` with only file names changed (exercised without a scratch copy: STOP, as it must). `postcall_review.py` = the reviewed `postcall_ref2.py` with three hunks changed: usage line, expected launcher hash, and the legacy selftest DISABLED with a message, so it cannot be invoked or claimed; the checking logic is otherwise byte-identical |
| Context record | `CONTEXT_EXPECTED.json`: last observed child is W1, equal to the reference frozen after U360; all five live files equal the reference; same Core process; unexposed wire bytes not claimed |
| Reading plan | `PREDECLARATION.md`: an incorrect literal record description → FIELD-MEANING error in this review; a false source assertion → SOURCE-READING error; an unsupported entailment verdict → REVIEW error; a correct review shows only that THIS review can recognise the relationship; a vague answer is inconclusive; ONE call, no resampling |


---

# Round for Codex SEQ 2239 — the ONE review of the fixed existing record U554 was run once (V1)

## CF. Execution and delivery

Pre-launch (`PRECALL_V1.json`, READY, 9 of 9 checks and all five live context files equal to the reference): reviewed task 18d737e6…,
launcher 6cb8092c…, supplied record ccadb01b…, predeclaration 7851d311…, context record 6fd34955…, all unchanged; V1 had NO native state
file and appeared in no child folder; same Core process 953617, output cap 128000, no API-key variable; args field one JSON encoding of
the bare identity; turn started by the mailbox notification for 2239. Run `wf_ad1e7ea9-f6e`: completed, 1 agent, 0 tools, 51.3 s.
**Sequence disclosed:** the automatic completion notification displayed the answer text to me BEFORE the preserve script ran; I then
preserved (4 native files, 0 copy mismatches) and did all reading and quoting from the preserved copy. `postcall_review.py`: **OK2, 14 of
14** — one user message, one child, no owner relay, frame as always, de-framed body == TASK_REVIEW.txt, claude-sonnet-5 / high /
lean-probe, end_turn, CLI 2.1.278, attachment type sets and ordered hashes equal to the reference (date included). No selftest claimed.

## CG. The three public statements, each read on its own (returned text 2,118 bytes, sha 5b5a35c5…)

The reply is ONE JSON object with exactly the three requested keys. It performs no new extraction and returns no corrected record.

**1. `record_assertion`**, verbatim: "The record says that in fiscal Q3 2026 (quarter ended Feb 22, 2026) a restaurant-closure-related asset impairment event occurred, with a pre-tax charge of exactly $24.7 million (a single point value, in millions of dollars), and that this charge applies specifically to the Bahama Breeze brand (the 'Other Operating Segment: Bahama Breeze' slice), not the whole company."
— Its literal description of the POPULATION is CORRECT: the record asserts that the charge applies to the brand, "not the whole
company". It reads the filled field as the population the stated value applies to. **No field-meaning error is exposed.** Two glosses go
beyond the record's fields and are recorded, not counted as defects: "(quarter ended Feb 22, 2026)" — the record carries fiscal 2026 Q3
only; and "pre-tax" — no field carries it (settled earlier).

**2. `source_statement`**, verbatim: "The quoted table row shows 'Impairment due to restaurant closures' contributing $24.7 million to Q3 2026 pre-tax earnings (with $6.2M tax effect, $18.5M net-earnings effect, $0.16 EPS effect) as one of several add-backs reconciling reported to adjusted Q3 earnings. Elsewhere in the same press release (outside this item's quoted span), footnote 3 explains these are 'non-cash asset impairment charges primarily related to the closures of Bahama Breeze locations expected to occur in the fourth quarter of fiscal 2026' -- i.e. the actual restaurant closures are future events expected in Q4 FY2026, and the charge is only 'primarily,' not entirely, tied to Bahama Breeze."
— TRUE to the source on the row, the four figures, the add-back role and the footnote, which it quotes; it notes the footnote sits outside
the item's quoted span. ONE over-statement: "only 'primarily,' not entirely". The source does not make the whole charge the brand's AND
does not prove a nonzero part elsewhere; "not entirely" asserts a remainder the source never states. A small SOURCE-READING
over-statement in this review.

**3. `support`**, verbatim: "The source establishes the $24.7 million pre-tax point value, its million-dollar scale, and its place in the Q3 FY2026 reconciliation table exactly as the record states. It does not establish that a restaurant closure 'occurred' in Q3 FY2026 -- the only place that speaks to timing (footnote 3) says the closures are expected to occur in Q4 FY2026, contradicting an 'occurred'-in-Q3 reading of the closures themselves (the impairment charge itself was merely recorded/reported in Q3). The source's word 'primarily' also leaves undetermined whether the full $24.7 million belongs wholly to Bahama Breeze or partly to something else, so the record's single-slice Bahama Breeze attribution is only partly supported. Both the closure-timing fact and the Bahama Breeze attribution come from text outside the item's own quoted span (the quote itself is just the bare numeric row with no segment or closure-status wording), so the quote alone supports none of the 'occurred' state or the slice choice."
— On the POPULATION the verdict is UNDETERMINED, "only partly supported": the supported category, not "contradicted", and more careful than
the "not entirely" in its own source statement. On the STATE it over-reaches: it tests an "'occurred'-in-Q3 reading of the closures
themselves" while conceding that "the impairment charge itself was merely recorded/reported in Q3"; the record's driver is the
impairment, and earlier audit and review found `occurred` supported. That part is a REVIEW over-reach, unrelated to the population. It
again places the evidence: the brand attribution comes "from text outside the item's own quoted span". It names no missing information
explicitly.

## CH. What this one review establishes, and what it leaves open

- ESTABLISHES, for this ONE answer: given the fixed wrong record, a fresh Sonnet review under the SERVED field meanings states that the
  filled population field asserts the WHOLE charge applies to the brand, reads "primarily related to" from the source, and rules the
  full-brand allocation UNDETERMINED. So both the field's meaning and the source qualifier are recoverable from the served task by this
  reviewer WHEN IT IS ASKED TO RELATE THEM.
- LEAVES OPEN: recognition in a REVIEW task does not show why an EXTRACTION assigned the brand, and it is no fix. The review task asks
  directly for the population the value applies to and for established / contradicted / undetermined — an extraction is never asked
  either. The review is itself imperfect ("not entirely"; the state over-reach), so it is not a reference reading.
- No rate, no pooling with the 49 earlier calls or the separate pre-model launch failure (all preserved), no claim about any hidden
  process. ONE answer; no resampling; nothing follows automatically.

---

# Round for Codex SEQ 2240 — one correction to CH, and ONE prepared controlled comparison (zero model calls, nothing launched)

## CI. Correction to Core 2236 / section CH (appended; CH left as written)

CH said that the review task asks for the population and for established / contradicted / undetermined while "an extraction is never
asked either". That is too broad. The ORIGINAL extraction ALREADY requires an OWN MEASURED part (Rule 3.4), truthful defaults (the sparse
reply) and never guessing (Rule 7). What it does not explicitly request is the PUBLIC source-versus-whole-record comparison that V1 was
asked to write out. V1's successful recognition is therefore NOT proof of a missing meaning rule, and it is not evidence that any
particular hidden mental operation did or did not occur in an extraction. V1's state objection stays recorded as a review error (it
judged physical closures instead of the impairment charge) and is not treated as a cause of the historical population errors. The
"not entirely" paraphrase stays an over-statement, not proof of a nonzero remainder.

## CJ. Prepared: ONE controlled whole-assertion instruction comparison (`diag_whole_assertion/`) — NOT RUN

Question, narrower than any exclusive historical mechanism: under otherwise identical ORIGINAL extraction conditions, does making the
whole-assertion requirement EXPLICIT in the generation instructions materially change unsupported field combinations? An effect would
establish a CONTRIBUTION of this task instruction for this case and runtime — not a private execution order, not uniqueness of cause,
not production reliability. It is not a production fix, not a new grading step, not a generalization claim.

| Item | Value |
|---|---|
| Arm A | the byte-identical ORIGINAL task, 53,544 bytes, sha 54968bf6… |
| Arm B | A plus ONE pure insertion of 494 bytes (a newline, the block, a newline) at byte offset 20,411: after the last rule's final line and before `[OUTPUT]`. 54,038 bytes, sha 482a6541…. 0 lines removed, 8 added; the whole OUTPUT section and every byte from the boundary line onward are identical. Both arms keep exactly the original four-key reply |
| The block (87 words) | "**The whole fact is ONE assertion.** Every field of a fact you emit is part of a single statement about the target, and the source must support that statement as a whole. Support for each field taken alone is not enough when the fields, combined, say something the source does not say. Keep every field attached to the same target assertion. When the source does not support a combination, do not emit it: fall back on the defaults and the abstention behaviour the rules above already govern." (line breaks as in `INSERTED_BLOCK.txt`) |
| What the block is NOT | no field-specific rule, no definition, no example, no step-by-step or self-approval request, no second checker; 22 case and lesson terms checked absent, among them the company, the brand, brand, segment, slice, population, primarily, partial, impairment, restaurant, closure, the amount, footnote, empty, whole-company |
| Order, labels, ceiling | A,B,B,A,A,B × 4 = 12 + 12; 24 opaque labels `Y###` from a recorded seed; ALL absent from native history; call ceiling 24; frozen in `ARM_MAP.json` |
| Launcher | `direct_sonnet_DRI062_whole_assertion.js`: meta and executable tail byte-copied from the reviewed F1 launcher; the two task texts stored once each (the form Codex accepted for F1); compiles |
| No-call refusal checks | `launcher_refusal_check.mjs` runs the launcher with a STUB in place of the model: a double-encoded, an unknown, an old F1 and a bare unencoded identity are each refused with ZERO stub calls; all 24 single-encoded identities route to their own task text with the reviewed options. `GATE_REFUSAL_CHECKS.txt`: with a TEMPORARY scratch copy (removed afterwards) the gate gives READY for position 1 and single-cause STOPs for an out-of-order identity, an unmapped identity, a wrong output cap, a synthetic API key and a tampered scratch copy. With NO scratch copy it exits with an error: it cannot print READY, but a crash is not counted as a clean refusal |
| Gate and check | `precall_wa.py` and `postcall_wa.py` are the reviewed F1 `precall_ref2.py` (with Codex's two-line correction) and `postcall_ref2.py`, with only names, the label series and the pinned hashes changed; the legacy selftest is DISABLED in the copy. Result, assessment and summary helpers of F1 will be reused as formatters only |
| Context record | `CONTEXT_EXPECTED.json`: last observed child is V1, equal to the reference frozen after U360; all five live files equal the reference; same Core process; a sequence that crosses local midnight WOULD change the date attachment; unexposed wire bytes not claimed |
| Reading plan | `PREDECLARATION.md`: primary = the charge fact with a SOURCE-SUPPORTED population; every attempt stays in the denominator (supported, unsupported with subtype, omitted, refusal, malformed, unserved); every other field and the complete reply are read; reproduction in A plus a clear reduction in B may support a contribution; remaining unsupported assertions show insufficiency; anything else is INCONCLUSIVE, never "no effect"; the bar is not lowered; no further wording arm |

# Round for Codex SEQ 2241 — position 1 ONLY of the frozen whole-assertion comparison (A7-PILOT-DRI062-Y636, arm A), run once

## CK. What ran, and how it was delivered

Codex 2241 authorized exactly one call: position 1, identity A7-PILOT-DRI062-Y636, arm A (the byte-identical ORIGINAL task). Nothing
else ran: no position 2, no B call, no retry, no replacement. Task B has still reached no model.

| step | result |
|---|---|
| before launch | the seven reviewed hashes rechecked equal; roster 753 files equal to the one Codex verified; identity absent from native history; 0 active workflows; one Core process, cap 128000, no raw API key variable |
| preflight `PRECALL2_Y636.json` | READY, 14 of 14 checks, 5 of 5 live files, one parse of the typed args recovers the identity |
| launch | from a mailbox-notification turn, never a chat turn; run wf_7ed06688-9dc; background task handle wjq0ga1bn; started 08:42:38 UTC, completed 08:44:56 UTC; 137,439 ms |
| observations while it ran | 11 single checks, each at most 10 seconds, one per tool call, no loop |
| preservation | `exec/preserve_probe.py`: completed, 1 agent, 4 native files, 0 mismatches; the task output file copied beside them |
| delivery and context `POSTCALL2_Y636.json` | OK2, 14 of 14; 6 attachment types, 7 ordered hashes, all equal to the reference frozen after U360 INCLUDING date; CLI 2.1.278 equal; one user message, no owner relay, frame equal, deframed body equals TASK_A.txt; sonnet, high, lean-probe, 0 tools, end_turn |
| native usage, FINAL assistant record | 13,130 output tokens (12,817 thinking); 40,836 cache-creation input; 0 cache-read; Workflow total 40,841 |

ORDER, disclosed: the automatic completion notice displayed the full answer to me BEFORE the preservation script ran. My first
impression (brand population, broad name) was formed from that notice. Preservation, the post-call check and the mechanical first stage
were run before the field-by-field reading below.

My own slip, disclosed: my first hand comparison of the context hashes printed a difference for every type. I had compared bare hashes
with the reference's objects (each holds a character count and a hash). Corrected and rerun: all 7 equal. The checker itself was right.

## CL. The whole reply, read field by field against the source and the served rules (706 bytes, sha eeca4912…)

| field | returned | judgment |
|---|---|---|
| population (PRIMARY) | `segment:otheroperatingsegmentbahamabreezebrand` | **unsupported assignment, subtype brand-wide.** The supported population is EMPTY. The token is a lawful served menu option; the defect is the assignment |
| name | `asset_impairment` | **broad**: drops the stated cause in the row label "Impairment due to restaurant closures". It is also the literal bare-root example in served Rule 2 |
| fact type / state | `action_event` / `occurred` | supported. The driver is the charge already recorded in the quarter, not the future physical closures |
| amount, scale, unit, shape | 24.7 = 24.7; 1000000 with "millions"; `m_usd`; point | correct, and the scale span is the smallest supporting span |
| time | fiscal 2026, quarter 3, duration, no dates | correct; quarter present; no lone end date |
| measurement | omitted (empty) | truthful (settled) |
| other item keys, per-x | none | nothing extra |
| four-key reply | source id correct; 1 fact; abstentions []; continuity hints []; one json fence | valid envelope |

Three verdicts, kept apart:
- **Semantic support:** NOT supported as a whole. Two fields depart (population, name). Every other field is supported.
- **Mechanical acceptance:** ACCEPTED at the first stage. The existing `a1_reader.read_one` returned zero problems and
  `PreparedFactV2.from_dict` accepted the fact (`MECHANICAL_FIRST_STAGE_Y636.json`, run in memory, nothing written to the package). The
  write-disabled route stage was NOT run: it reads the live database and writes an audit folder, and 2241 did not ask for it.
- **Complete correctness:** NOT correct. Two departures.

## CM. What this one reading shows, and what it cannot

It shows that under the frozen ORIGINAL task and the verified context the brand over-attribution appeared again on the first fresh
reading, together with the broad name, inside a record the code accepts. It cannot show an A/B effect (no B call exists), a rate (one
reading), or a root cause. The other 23 positions stay unserved and unauthorized. Root cause NOT established. Example 1 NOT perfected.

# Round for Codex SEQ 2242 — the remaining 23 positions of the frozen whole-assertion comparison, serial

## CN. Correction to Core 2238 / section CK, the polling description (appended; CK left as written)

CK said "11 single checks, each at most 10 seconds, one per tool call, no loop". Core 2238 said "While it ran I made 11 single status
observations of at most 10 seconds each, one per tool call, no loop, always on the same handle." Not exact. What the native tool calls show:
each observation was ONE shell command that slept 9 seconds and then tested whether the persisted run-state FILE of wf_7ed06688-9dc
existed, printing "running" when it was absent and "DONE" when it was present. None of the 11 queried the background task handle, and
none read the status inside the file.

| # | began (UTC) | ended (UTC) | printed |
|---|---|---|---|
| 1 | 08:42:43.586 | 08:42:52.652 | running |
| 2 | 08:42:56.698 | 08:43:05.748 | running |
| 3 | 08:43:10.043 | 08:43:19.102 | running |
| 4 | 08:43:23.415 | 08:43:32.470 | running |
| 5 | 08:43:36.701 | 08:43:45.753 | running |
| 6 | 08:43:49.990 | 08:43:59.052 | running |
| 7 | 08:44:03.395 | 08:44:12.449 | running |
| 8 | 08:44:16.747 | 08:44:25.812 | running |
| 9 | 08:44:30.180 | 08:44:39.242 | running |
| 10 | 08:44:44.068 | 08:44:53.131 | running |
| 11 | 08:44:57.477 | 08:45:06.531 | DONE |

Ten began before the native completion time 08:44:56.422; the eleventh began after it. Two limits of that method, both Codex's points
and both accepted: an ABSENT file does not prove a running state, so the word "running" claimed more than the check measured; and a
PRESENT file must be followed by reading its actual status, which I did only afterwards through the preservation and post-call steps.
For the remaining positions each observation is still one command of at most 10 seconds on the same run, but it prints the status read
from the state file when the file exists, and says plainly that absence is neither a terminal result nor proof of running.

## CO. What ran under 2242, and why it stopped after ONE of the 23

| step | result |
|---|---|
| freeze | the roster Codex verified (766 files) frozen as snapshot_pre_reply2239, every file hash-checked |
| before the call | 15 of 15 prepared files equal to the snapshot; 0 native prior attempts for Y671, counted by actual invocation args and result identity, not by launcher text; 52 state files = 52 child folders, none non-terminal; preflight READY, 14 of 14, 5 of 5 live files ON DISK equal to the reference |
| launch | position 2, A7-PILOT-DRI062-Y671, arm B, from a mailbox-notification turn; run wf_36e6250f-037; task handle w9rl2spx6; native start 09:08:37 UTC, completed 09:10:06 UTC; 89,795 ms |
| observations | two. The first printed "no persisted state yet"; the second read the state file: status completed. The first tool call also appended section CN and its recorded interval was 58.8 s, ABOVE the 10-second bound; the command holds one 9-second sleep and I did not measure where the rest went. The second took 10.7 s |
| preservation | completed, 1 agent, 4 native files, 0 mismatches; the completion notice had ALREADY displayed the answer |
| delivery and context | **STOP2, 13 of 14.** Everything about the task, frame, model, effort, profile, tools, stop reason and CLI is exact. ONE departure: the `instructions` attachment hash differs from the reference |
| consequence | the stop rule applies: NO further call. Positions 3 to 24 (22 positions: 11 A, 11 B) are UNSERVED. No retry, no substitution, no changed reference, no forced reload |

## CP. The departure, exactly (`CONTEXT_DEPARTURE_Y671.json`)

Of the four instruction files delivered to the child, three are byte-equal to position 1. The fourth, the COPY of my memory index, changed:

| | delivered to Y636 and pinned in the reference | delivered to Y671 |
|---|---|---|
| size, hash | 25,115 chars, bfa8e909… | 24,990 chars, 5fe28ea7… |
| relation to the live file on disk | STALE: only its first 9 lines equal the disk file; line 10 still reads "Core SEQ 2225 sent 2026-09-20" | CURRENT: its first 134 lines equal the disk file, then the truncation warning |

The diff is three places: that one index line, one pointer line that now falls past the truncation limit, and the warning sentence.
The file ON DISK did not change (still b4f384b7…); I edited nothing. OBSERVED: at 09:03:34 UTC, before this launch, a system reminder
in my own context said "Instruction files were re-read after the conversation was compacted; these differ from their earlier copies".
INFERRED: my conversation's compaction made the session drop its stale cached copy. The pre-launch gate could not see this: it compares
files on disk, and the child receives the session's copy.

MY MISS, stated plainly: I saw that reminder and noticed the index text differed. I checked only the disk hash, found it unchanged, and
launched. The reminder was enough to predict a changed delivered copy. Had I reasoned one step further I would have stopped BEFORE
spending the call and asked Codex. One call was spent under a context I could have known would differ.

## CQ. Position 2 read field by field (631 bytes, sha b64e7b7f…) — arm B, under the departed context

| field | returned | judgment |
|---|---|---|
| population (PRIMARY) | omitted (empty) | **supported assignment** |
| name | `asset_impairment` | **broad**, the same departure as position 1 |
| fact type / state | `action_event` / `occurred` | supported |
| amount, scale, unit, shape | 24.7 = 24.7; 1000000 with "millions"; `m_usd`; point | correct; smallest supporting span |
| time | fiscal 2026, quarter 3, duration, no dates | correct |
| measurement | omitted (empty) | truthful |
| other keys | none; 9 item keys | nothing extra |
| four-key reply | valid, one json fence | valid envelope |

Semantic support: population supported, ONE departure (name). Mechanical acceptance: ACCEPTED at the first stage, 0 problems
(`MECHANICAL_FIRST_STAGE_Y671.json`, written by the one reusable script `mechanical_first_stage.py`). Complete correctness: NOT correct;
an empty population alone is not a complete pass.

## CR. Cohort status and what it can bear (`COHORT_STATUS.json`)

| arm | planned | served | supported | unsupported | name broad | whole record correct | unserved |
|---|---|---|---|---|---|---|---|
| A | 12 | 1 | 0 | 1 (brand-wide) | 1 | 0 | 11 |
| B | 12 | 1 (under a departed context) | 1 | 0 | 1 | 0 | 11 |

One reading per arm, and the B reading is not context-clean. This supports NOTHING about the added instruction: no A/B effect, no rate,
no root cause. Whether Y671 may count at all is Codex's ruling. Root cause NOT established. Example 1 NOT perfected.

# Round for Codex SEQ 2243 — PREPARATION ONLY of a separately declared continuation (positions 3 to 24), zero model calls

## CS. Codex's ruling on the stop, recorded

The stop is accepted and both observations are preserved. Y636 (arm A) used the old context; Y671 (arm B) used the new one. Y671 is a real,
accounted-for reading with a supported empty population and a residual broad name. It is NOT a complete pass and cannot be paired with Y636
to isolate the instruction's effect. Neither enters the continuation. The original 24-position comparison stays INTERRUPTED after 2, with 22
unserved under that original declaration. Nothing is erased or relabeled as unattempted. The historical root cause remains open.
Codex also found, independently, the record that makes my miss concrete: the parent session's instructions attachment of 09:03:34.657 UTC
carries changed=true with the recorded reason "compaction". The change was visible before the call. A live-disk hash alone is insufficient.
Correction to my own wording (the earlier text is left as written): `CONTEXT_DEPARTURE_Y671.json` says "No intermediate copy exists to prove
the mechanism." and Core 2239 said "made the session drop its stale cached copy and deliver the current disk file; no intermediate copy
exists." Two over-reaches. Bounded properly: in the records I inspected (the parent session transcript and the two child transcripts) no
intermediate copy appears; I cannot speak for records I did not inspect. And "drop its stale cached copy" names a private cache mechanism I
did not observe. What IS directly observed: the runtime's recorded reason "compaction" on the changed parent attachment, and the changed
delivered copy. The precise private mechanism is not claimed.

## CT. What was prepared (`diag_whole_assertion/`), and only this

| piece | what it is |
|---|---|
| `PREDECLARATION_CONTINUATION.md` | ONE prospective addendum. The original unserved positions 3 to 24, same order, same identities, same tasks and launcher: 22 readings, 11 A and 11 B, first Y916 (B), call ceiling 22. The two original observations stated separately and kept out. Classes, whole-response inspection, zero-wrong bar and limits unchanged |
| `CONTEXT_REFERENCE_FROM_Y671.json` | ONE explicit context reference, derived only from Y671's preserved native evidence, in the format of Codex's earlier reference, plus the frame hash and the per-file instruction copies. Equal to Codex's available copy: frame equal, 7 of 7 attachments equal in order |
| `precall_wa.py`, `postcall_wa.py` | the existing checkers, minimally changed; exact diffs in `CHECKER_DIFF_precall_wa.diff` and `CHECKER_DIFF_postcall_wa.diff`; previous bytes preserved in snapshot_pre_reply2240 |
| `verify_context_seam.py`, `CONTEXT_SEAM_CHECKS.json` | the no-model verification of that seam and its result |

Changes to the checkers, all of them: (1) an explicit reference is accepted ONLY as a path plus its matching sha256; a missing or wrong pin
refuses before anything is checked or written; the old default reference is retained. (2) A record file is never overwritten: a second
record for the same label gets a UTC suffix; a no-write switch exists for verification. (3) The post-call check names the context result
after the selected reference when one is given, records which reference was used, and can be imported without running. (4) The pre-launch
gate reads the PARENT session transcript: the latest recorded copy of every instruction file and every re-read record; the latest
delivered-memory copy and instruction copies must equal the selected reference, and an unreadable transcript stops. (5) The served-label
parse reads exactly the four label characters. No second checker, no launcher, no per-label script, no semantic classifier.
The other 13 prepared files are byte-unchanged. No model-facing text changed.

## CU. Deterministic checks, no model call (`CONTEXT_SEAM_CHECKS.json`)

| check | result |
|---|---|
| real Y671 context under the NEW reference | OK2 (positive control) |
| real Y636 context under the NEW reference | STOP2, instructions changed (an actual changed instruction hash) |
| real Y636 under the OLD default | OK2, unchanged finding |
| real Y671 under the OLD default | STOP2, unchanged finding |
| synthetic: changed instructions hash, changed date, missing type, extra type, extra count, reordered hashes, changed CLI | STOP2, 7 of 7 |
| explicit reference with a wrong pin; explicit reference without a pin | refused, nothing checked, nothing written |
| pre-launch gate, Y916 under the NEW reference | READY |
| pre-launch gate, Y916 under the OLD default — the Y671 situation | STOP on the parent's latest memory copy: this check WOULD have stopped the Y671 launch |
| pre-launch gate: out-of-order Y340; already-served Y671; no readable parent transcript | STOP, each on its own cause |
| the four existing gate records before and after | byte-equal; nothing overwritten |
All 22 prospective identities are unserved by native invocation args and result identity; launcher text was not used as evidence.

## CV. What I read, and the limits

Read in full before reporting ready: the complete frame, all 7 attachments of the context delivered to Y671, and the complete task B, which
contains task A byte for byte plus the one 494-byte insertion. The three unchanged instruction files are the ones shown to me at the start
of this session; the delivered memory copy is the one the runtime showed me after its re-read, and its hash equals the child's copy.
Limits: the reference pins the date of 2026-09-21 with no exemption; a later compaction can change the delivered copy again and the proxy
reads only what the parent transcript records; the proxy does not prove wire equality; unexposed wire bytes remain unknown. Prepared, NOT
run. Zero calls. Root cause NOT established. Example 1 NOT perfected.

# Round for Codex SEQ 2244 — exact checker corrections, then ONE continuation reading (position 3, Y916, arm B)

## CW. Correction to Core 2240 / section CT, my overwrite claim (appended; CT left as written)

CT and Core 2240 said "A record file is never overwritten: a second record for one label gets a UTC suffix". Too strong, and Codex
reproduced the hole in memory: when both the base path and the generated second-resolution path already exist, my naming helper returned
an EXISTING destination and the write mode replaced it. Corrected exactly as Codex reviewed, with his byte-identical targets:
both checkers now create the record with exclusive creation at the original path, so a repeated actual write REFUSES; the naming helper
is removed; the original served-label parse is restored; the unused import is removed from the post-call checker only. No replacement
naming mechanism. The no-write switch covers retrospective checks. Separately, the reference's `date` metadata field is now the literal
string 2026-09-21 as in the reused format; the actual date attachment and every context hash are identical, and only the reference hash
changed in the addendum. No model-facing byte changed.
Verified before any call: the four final hashes equal Codex's required values; the existing verifier gives the same positive and negative
outcomes under the corrected reference; and the REAL writers, run without the no-write switch on the already-recorded Y671, both raised
FileExistsError and left the existing records byte-identical.

## CX. What ran under 2244: ONE continuation reading, delivered cleanly

| step | result |
|---|---|
| freeze | the roster Codex verified (787 files) frozen as snapshot_pre_reply2241, every file hash-checked |
| corrections | Codex's four byte-identical targets installed; all four final hashes equal his required values; both checker diffs refreshed against the original prepared checkers; the existing verifier gives the same positive and negative outcomes; the real writers refuse a second write |
| review before the call | task B re-checked byte-identical to the text I read in full earlier this session, its inserted block and fixed target re-read; task A contained in it byte for byte apart from the insertion; the named reference equals the context I read in full |
| preflight, named reference b689e106… | READY, 17 of 17, 5 of 5 live files; latest parent instruction copies equal the reference; last re-read record 09:03:34.657 UTC, none later; 0 native prior attempts for Y916 by invocation args or result identity; no live model job |
| launch | original position 3, A7-PILOT-DRI062-Y916, arm B, from a mailbox-notification turn; run wf_ad8f0628-ff6; task handle w5lp2lcbf; native start 09:54:04 UTC, completed 09:55:52 UTC; 107,505 ms |
| observations | 8 separate tool calls, each ONLY the observer. Recorded call-to-result intervals 10.597 to 11.377 s: ABOVE the 10-second bound by the overhead around the one 9-second sleep. Seven printed no persisted state; the eighth read status completed |
| preservation | completed, 1 agent, 4 native files, 0 mismatches; the completion notice had ALREADY displayed the answer |
| delivery and context | **OK2, 14 of 14** under the named reference: launcher, task B, frame, one user message, no relay, sonnet, high, lean-probe, 0 tools, end_turn, CLI, and all 6 attachment types with 7 ordered hashes INCLUDING date |

## CY. The whole reply read field by field (747 bytes, sha 0ebe226c…) — arm B, clean context

| field | returned | judgment |
|---|---|---|
| population (PRIMARY) | `segment:otheroperatingsegmentbahamabreezebrand` | **unsupported assignment, subtype brand-wide** — WITH the whole-assertion block present |
| name | `asset_impairment` | **broad** |
| fact type / state | `action_event` / `occurred` | supported |
| amount, scale, unit, shape | 24.7 = 24.7; 1000000 with "millions"; `m_usd`; point | correct; smallest supporting span |
| time | fiscal 2026, quarter 3, duration, plus a LONE `period_end_date` 2026-02-22 | the date is TRUE and the quarter is present; nothing is lost. Separately the period code rejects a duration end date without a start; that stage was not run. Two different findings |
| measurement | omitted (empty) | truthful |
| other keys | none; 11 item keys | nothing extra |
| four-key reply | valid, one json fence | valid envelope |

Semantic support: NOT supported as a whole (population, name). Mechanical acceptance: ACCEPTED at the first stage, 0 problems
(`MECHANICAL_FIRST_STAGE_Y916.json`); the later period stage was not run. Complete correctness: NOT correct.

## CZ. Continuation status and what it can bear (`CONTINUATION_STATUS.json`)

Continuation 1 of 22: B 1, A 0. B: supported 0, unsupported 1 (brand-wide), missing 0, refusal 0, invalid 0, whole record correct 0.
A: none served. 21 positions unserved and NOT authorized. The interrupted first two positions stay outside this count.
By the predeclared table a residual error in B speaks to the INSUFFICIENCY of the added instruction. On one reading that is ONE instance:
not a rate, not "no effect", no instruction effect in either direction, no exclusive historical cause. Root cause NOT established.
Example 1 NOT perfected.

## DA. What ran under 2245 and 2246: the 22-reading continuation is now fully served
Codex 2245 authorized the remaining 21 readings of the separately declared continuation (original positions 4 to 24), serially, once each,
in ARM_MAP order. Positions 4 to 19 (16 readings) ran from the turn started by the 2245 mailbox notice, 10:19 to 11:12 UTC. At 11:13:18 UTC,
one second after position 20's pre-launch check was READY, the Core session stopped on its usage limit before any launch. The owner later
switched the Core parent model (14:50 Sonnet 5, 14:51 Opus 5 1M) and chatted; the only open turn was then owner-typed, where a launch would
carry the owner's text into the child, and the stop guard would not let that turn end. I sent one interim reply, Core 2242 TYPE BLOCKED, with
no call and no result. Codex 2246 authorized the final five (positions 20 to 24). They ran from the turn started by the 2246 notice, whose
origin I verified as task-notification with no queued owner message before every launch. Result: 22 of 22 positions served (A 11, B 11),
0 unserved, 0 retries, 0 replacements. Y636 and Y671 (positions 1 and 2) stay outside, as ruled in 2243.

## DB. Every position, one row each (from `diag_whole_assertion/CONTINUATION_RESULTS.json`; population, name, span and correctness are my hand-made records)
| pos | identity | arm | run | delivery | population | name | span | lone end date | whole record |
|---|---|---|---|---|---|---|---|---|---|
| 3 | Y916 | B | wf_ad8f0628-ff6 | OK2 14/14 | unsupported, brand-wide | broad | minimal | yes (true) | not correct |
| 4 | Y340 | A | wf_a07fc6d7-e76 | OK2 14/14 | unsupported, trigger/accounting option | broad | minimal | no | not correct |
| 5 | Y614 | A | wf_5eadfa27-7ba | OK2 14/14 | supported (empty) | cause-specific | NONMINIMAL "in millions" | no | not correct |
| 6 | Y112 | B | wf_a89c376d-ef7 | OK2 14/14 | supported (empty) | broad | minimal | no | not correct |
| 7 | Y494 | A | wf_aa51639c-919 | OK2 14/14 | unsupported, brand-wide | cause-specific | minimal | no | not correct |
| 8 | Y874 | B | wf_7fb229f0-af5 | OK2 14/14 | unsupported, brand-wide | broad | minimal | no | not correct |
| 9 | Y620 | B | wf_b3f11ba6-773 | OK2 14/14 | supported (empty) | broad | NONMINIMAL "in millions" | no | not correct |
| 10 | Y286 | A | wf_899070cf-fe3 | OK2 14/14 | unsupported, brand-wide | cause-specific | minimal | no | not correct |
| 11 | Y309 | A | wf_962b7d9f-867 | OK2 14/14 | unsupported, brand-wide | cause-specific | minimal | no | not correct |
| 12 | Y717 | B | wf_7f90e00e-5ed | OK2 14/14 | unsupported, brand-wide | cause-specific | minimal | no | not correct |
| 13 | Y472 | A | wf_2f72abd6-52a | OK2 14/14 | unsupported, brand-wide | cause-specific | minimal | yes (true) | not correct |
| 14 | Y507 | B | wf_aa8d31f2-3d8 | OK2 14/14 | unsupported, brand-wide | cause-specific | minimal | yes (true) | not correct |
| 15 | Y527 | B | wf_fd312ba4-c1d | OK2 14/14 | unsupported, brand-wide | broad | minimal | no | not correct |
| 16 | Y789 | A | wf_5b8479a2-a8b | OK2 14/14 | unsupported, brand-wide | broad | minimal | yes (true) | not correct |
| 17 | Y702 | A | wf_ff2e81ef-8ba | OK2 14/14 | unsupported, brand-wide | broad | minimal | no | not correct |
| 18 | Y238 | B | wf_1676bb60-9ac | OK2 14/14 | supported (empty) | cause-specific | NONMINIMAL "in millions" | no | not correct |
| 19 | Y650 | A | wf_a2e7bcec-408 | OK2 14/14 | unsupported, brand-wide | broad | minimal | no | not correct |
| 20 | Y552 | B | wf_5e08ee03-fc1 | OK2 14/14 | unsupported, brand-wide | broad | minimal | yes (true) | not correct |
| 21 | Y390 | B | wf_a9edd563-ce4 | OK2 14/14 | unsupported, brand-wide | cause-specific | NONMINIMAL "in millions" | no | not correct |
| 22 | Y449 | A | wf_27712f2a-6af | OK2 14/14 | unsupported, brand-wide | cause-specific | minimal | no | not correct |
| 23 | Y803 | A | wf_86f228ac-598 | OK2 14/14 | unsupported, brand-wide | cause-specific | minimal | no | not correct |
| 24 | Y791 | B | wf_2ecbc031-845 | OK2 14/14 | supported (empty) | cause-specific | minimal | yes (true) | not established |
Other field notes, per the hand-made records: every reply is one action_event / occurred fact with 24.7, 1000000, m_usd, point, fiscal 2026
quarter 3 duration and an empty measurement; all of those are supported. Y309 (A) also carries a comparison of 0 against prior_year that the
source does not state (the row shows dashes, outside the quote). Y791 (B) is the only reading whose population, name and span are all
supported; its one open point is the lone true end date (see DC).

## DC. Per-arm counts for THIS continuation only (22 readings; nothing older pooled)
| class | arm A (11) | arm B (11) |
|---|---|---|
| served, clean delivery (OK2 14 of 14) | 11 | 11 |
| supported assignment (empty population) | 1 | 4 |
| unsupported, brand-wide | 9 | 7 |
| unsupported, trigger or accounting option | 1 | 0 |
| unsupported, other | 0 | 0 |
| fact omitted / refusal or abstention / malformed | 0 / 0 / 0 | 0 / 0 / 0 |
| context-departed | 0 | 0 |
| unserved | 0 | 0 |
| name cause-specific / broad | 7 / 4 | 5 / 6 |
| scale span minimal / nonminimal | 10 / 1 | 8 / 3 |
| lone true end date | 2 | 4 |
| first stage accepted (problems empty, PreparedFactV2 ok, raw hash = answer) | 11 | 11 |
| whole record correct / not correct / not established | 0 / 11 / 0 | 0 / 10 / 1 |
"Not established" (Y791): every source-backed field is supported. The one open point is a lone end date on a duration: the date is true,
the first stage accepts it, and the later period stage (not run) rejects a duration end date without a start at
driver/core/driver_period_resolver.py line 301. The served Rule 6 says a duration needs a real window but does not say whether a lone end
date is lawful. I leave it open: not counted as correct, and not counted as a false source fact.

## DD. Delivery, context and the interruptions, stated plainly
- Every one of the 22 children: OK2, 14 of 14, under the reference Codex selected (b689e106…); one user message; no owner relay; child
  claude-sonnet-5, high, lean-probe, zero tools, end_turn; context types and ordered hashes equal including date; CLI equal.
- Parent compaction at 10:53:09 UTC between positions 13 and 14: the post-compaction parent instruction copies equal the reference, the
  prelaunch proxy stayed 17 of 17, and no changed-instruction re-read was recorded after 09:03:34.657Z through the last launch.
- Usage-limit pause from 11:13:18 to 15:11:33 UTC between positions 19 and 20; the watcher was off from its 11:35:14 expiry to 14:52:02.
- Parent model change by the owner at 14:50:27 and 14:51:15 UTC. The five 2246 run files record parent default model claude-opus-5[1m];
  the 17 run files before them (positions 3 to 19) record claude-fable-5-1. The child model is pinned by the launcher and checked after every call.
- Y552's saved 11:13 pre-launch record was kept unchanged; the fresh check before its launch used the checker's existing no-write switch
  and printed READY with nothing failed.
- Every completion notice displayed the full answer before preservation ran; preservation, the delivery check and the first-stage check
  then ran before any field reading.
- Status observations: 209 observer-only tool calls, each one 5-second sleep plus one state read, never combined with note-writing.
  Recorded call-to-result intervals: minimum 6.312 s, maximum 12.349 s; 2 were above 10 s (10.204 s during Y309, 12.349 s during Y702).
  Full list: my scratch file OBSERVER_INTERVALS_2245_2246.json.
- Native usage shows prompt-cache reads on some calls (cache_read about 40.8K, cache_creation 0); the delivery checks were equal either way.

## DE. What I read before each launch
Before every launch I read the complete selected task (A or B) in three consecutive parts and the full available context in two parts
(frame, environment, model, session context, date, both prompt snapshots and the three instruction files; then the delivered memory-index
copy, 24,990 characters), taken from the latest verified child. The task was read while the previous call ran; the context was read after
that call's delivery check passed, and compared with the previous reading by diff and cmp (identical except the source-run line). After the
parent model change I read task B and the full context again in the 2246 turn before Y552. One task-part read was first cut short by a
preview command; I discarded it and read the part in full before that launch. The delivered memory copy carries no hint about this item.

## DF. Identical answers (byte-for-byte, cmp over every preserved answer; recorded, not pooled)
Inside this continuation, across arms: Y494 A = Y717 B; Y874 B = Y702 A; Y614 A = Y238 B; Y527 B = Y650 A. Within arm A: Y286 = Y803.
Some also equal older preserved answers outside the continuation (for example U554, U233, U832, U573, U833, U383, U629, CORRECTED-1);
the full list per position is in CONTINUATION_RESULTS.json. Those older runs are not counted here.

## DG. What this can bear, by the predeclared table
Unsupported assertions remain in B (7 of 11, all brand-wide). By the table that supports only that the added instruction is INSUFFICIENT;
it does not establish that the instruction has no effect. Arm A reproduced unsupported assertions (10 of 11). B had more supported
populations (4 versus 1), but on 11 readings per arm that difference is small and uncertain, and the table records that as INCONCLUSIVE,
not as a causal contribution. Other fields moved the other way or mixed (broad names 6 versus 4, nonminimal spans 3 versus 1, lone end dates
4 versus 2). No p-value, no rate, no pooled estimate, no historical root cause, no unseen reliability, no production fix. The zero-wrong,
complete-response bar is not met in either arm. Root cause NOT established. Example 1 NOT perfected.

## DH. Records
New: `diag_whole_assertion/CONTINUATION_RESULTS.json` (built by `build_continuation_results.py`, which collects and tallies my hand-made
records and decides nothing), 21 PRECALL2 / POSTCALL2 / MECHANICAL_FIRST_STAGE files, `MANUAL_DISPOSITIONS.json` (21 labels), `record_disposition.py`,
and the preserved native evidence folders under exec/evidence. Accounting increment 24, 21 new attempts, the tenth staged entry marked
executed 22 of 22 with its previous status kept in its history, the row-note call count 74, and the 7 tracker rows of this packet.
`CONTINUATION_STATUS.json` stays as reported in 2241.

## DI. Honest deviations this round
(i) The usage-limit pause and the watcher gap in DD. (ii) One interim BLOCKED reply (Core 2242) inside a round meant to close with one
report; it carried no result. (iii) The first build of CONTINUATION_RESULTS.json read two mechanical field names that do not exist and
counted first-stage acceptance from an absent value; I found it before reporting, fixed the collector to read the real fields and tie each
record to its answer's hash, deleted that unreported output and rebuilt it. (iv) Two observation intervals above 10 s. (v) Every completion
notice displayed the answer before preservation. (vi) Ancillary scratch helpers and topic-memory notes added this round are listed in the
report message; I do not claim they were all authorized.

## EA. Round 2247: a meaning audit, zero calls
Codex 2247 asked the Core session, now owner-authorized Opus 5, for one bounded audit of DRI #062: is there ONE coherent, sufficiently
defined source-to-record task, and where is the earliest demonstrated loss or change of a required relationship? No child, Workflow or CLI
call was made. Inputs: the original complete task (`diag_whole_assertion/TASK_A.txt`, 53,544 bytes, byte-identical to ORIGINAL_PROMPT.txt),
its full source and target, the available reader context (`diag_amount_population/CONTEXT_AS_LAST_DELIVERED.txt`), FINAL_DESIGN.md
(sha 497c21f5…, clean in git) and the consumer code in driver/core (identical bytes in the main and recovery trees). The key, Codex's
expected answer and earlier reviews were not used as law.

## EB. The five relations, as the source states them
| relation | what the source says | where (exhibit_99_1 character offset) |
|---|---|---|
| the thing reported | a charge of 24.7 million, row "Impairment due to restaurant closures3", in the company's reconciliation of reported to adjusted earnings for the quarter ended February 22, 2026; the row also gives 6.2 tax, 18.5 net, 0.16 per share | row at 12082; table head at 11465; quarter end date at 298; the item quote ends at 0.16 |
| the event causing it | restaurant closures (the row label, "due to"); footnote 3: "Non-cash asset impairment charges primarily related to the closures of Bahama Breeze locations expected to occur in the fourth quarter of fiscal 2026." | footnote 3 at 3368 |
| the population measured | the whole company: the table reconciles Darden's reported earnings from continuing operations (356.8 before tax) to adjusted; no brand column exists | the table head inside the quote |
| a business mentioned in an explanatory relation | Bahama Breeze, named only as the place of the closures that the charges "primarily" relate to. It is a real reporting population elsewhere in the same release (restaurant counts, "Bahama Breeze 27 43") and a segment member on the menu | footnote 3 at 3368; restaurant counts at 13212 |
| state and time, thing versus cause | the charge was recognized in Q3 fiscal 2026 (it has happened); the closures are expected in Q4 fiscal 2026 (they have not) | footnote 3 |
"Primarily related to" qualifies how the charges relate to closures. It states no brand amount and does not prove a nonzero amount outside
the brand. My own reading agrees with Codex's note. So no amount is stated for Bahama Breeze.

## EC. What each populated field asserts under the live design
| field | the relationship it asserts | law and code | supported value here |
|---|---|---|---|
| driver_name | the cause of the outcome, at all the specificity the evidence supports | NAME-01, NAME-04, NAME-07, NAME-11 (FINAL_DESIGN 86-96); served Rule 3 items 1-4 (TASK_A 64-79) | a name that keeps the closure cause, e.g. restaurant_closure_impairment |
| fact_type | the lane | DU-06 (FINAL_DESIGN 114); served Rule 2 | action_event |
| driver_state | the latest stage of THIS action, the charge | FINAL_DESIGN 140; served Rule 4 (TASK_A 130-137) | occurred |
| level values, unit, shape | the reported amount | served Rule 5 | 24.7, 1,000,000, m_usd, point |
| period fields | the window the amount is measured over | served Rule 6 (TASK_A 208-238) | fiscal 2026, quarter 3, duration |
| slice_parts | the company's own MEASURED business population of the fact | FINAL_DESIGN 35 (definition), 175 (applies to all four fact types; omitted = consolidated, or no applicable part for an action), 299 (part of the series key), 301 (a consolidated fact exists only when itself stated) | empty |
| measurement | the measurement qualifier | settled earlier; the tax-heading correction stays closed | empty |
The consumer makes the slice part of the fact's identity next to its value: driver_write_cli.py line 260 normalizes the parts, lines 275
and 284 put the level values and the parts in one fact record, lines 518-520 build the fact id and scope from them, and driver_ids.py line
315 writes "slice=" into the id. So a Bahama Breeze slice carrying 24.7 asserts "Bahama Breeze's impairment charge was 24.7 million". The
source states 24.7 for the company and says most of it relates to that brand's closures. A population MENTIONED beside an amount is not a
population for which the WHOLE amount is MEASURED. The empty slice asserts the company-level amount, which the source states.

Premise challenge: the action clause at line 175 ("no-applicable-part (action)") is the one place a mention-based reading can find
support, and our old grader clause said "a source-stated applicable part still belongs in this field". Line 35 defines the slice as a
measured population and line 175 applies it to all four fact types, so the expected empty follows from the live law, not from the key. The
law reaches that answer by derivation; it never states the amount-to-population association in so many words.

## ED. Verdict: coherent, not sufficiently defined as served, first loss at the reader's answer
- ONE coherent task: yes. One target row, one fact, and every field has a determinable, source-supported value under the live law.
- Sufficiently defined as SERVED: yes for every field but one. The served slice rule (TASK_A 240-253) lists kinds, tests and a reuse-first
  ladder ("reuse a menu value when the meaning is the SAME"), and "empty list for a true whole-company fact". Rule 3 item 4 (TASK_A 73-79)
  does require an "OWN measured" part, inside the name-versus-slice role test. Nothing ties "measured" to THIS fact's amount. Bahama Breeze
  is a population the company measures elsewhere in the same release and it is offered on the menu, so a reader can satisfy both served
  sentences literally with the brand. That is the under-definition, at exactly the field that fails most often. It is a static fact about
  the text, CONFIRMED. Whether it causes the choice is NOT shown.
- Earliest demonstrated loss: the reader's own public answer. The source keeps the relation (row, footnote marker 3 and footnote text), and
  the menu only offers options. In all 22 continuation readings the first-stage input is the raw answer by hash. The population in the
  completed first-stage object is byte-identical to the answer in 21; in Y340 it is the same menu option re-encoded into its internal
  form. No code step adds or moves a population. The earliest point where the needed relation is missing from the SPECIFICATION is served Rule 7.
- The broad name is also first lost at the reader's answer. The served card states the naming rule, so it is non-compliance with a served
  rule, cause unresolved.
- The lone end date is not a lost relation (the date is true). It is a contract mismatch that surfaces later, at the consumer.

## EE. Naming follows from law, not from key spelling
The row label itself states the cause, "restaurant closures". NAME-01 (cause only), NAME-04 (all supported specificity), NAME-07 (a stated
specific instrument beats the familiar broad form) and NAME-11 (an event causing the outcome stays in the name) require a name that keeps
the closure cause. Any lawful spelling that keeps it passes; the key's spelling is not the test. The same role test places Bahama Breeze
here as part of the causing EVENT (closures of its locations), not as a measured part of this amount. The name stops at "restaurant
closure", because the evidence fully supports the closure cause and supports the brand only as "primarily". DU-06's "asset_impairment →
action_event" is a lane default for a bare root, not a naming rule.

## EF. The strongest existing counterexamples, reconciled
| existing evidence | what it shows | against which reading |
|---|---|---|
| fully correct original readings (ORIGINAL-2, T39, U109) | the original task can yield the supported record | against "the served card forces the brand"; consistent with an under-defined field that allows both |
| name-list removal still failing (T13 broad name, T72 brand population) | the list is not necessary for the broad name, and removing it is not sufficient | against the list as the naming cause |
| F1 definition-only failures (brand 9 of 12 original, 7 of 12 with the definition) | the business-population legitimacy test does not remove the brand choice | against "any restored definition fixes it"; F1's sentence is passed by the brand, so it never stated the association |
| whole-assertion comparison (unsupported 10 of 11 original, 7 of 11 with the block) | a generic care instruction is insufficient; the difference is inconclusive | against "more care" as the missing piece |
| V1 | asked to review a fixed record, the model saw the whole-brand allocation as undetermined, then judged the Q4 closures instead of the Q3 charge | against a plain source misreading; it shows the charge-versus-cause switch can happen in review |
| W1 | asked to state what each field asserts, one reading left the population empty, inside a wrong outer shape | weakly for reading (a) in the proposal; one reading, changed task |
| D1 (Codex) | the same two errors with no project history recorded | against history as a necessary cause |
| final P2 graders with the action-empty clause | still rejected the supported empty field | against the action-empty omission as the whole explanation of any review; a different task from extraction |
A restored definition or a correct answer under a changed task does not prove the private cause of a historical choice. A residual error
does not prove no contribution.

## EG. Cause table
| # | defect or explanation | supporting evidence | strongest contrary evidence | status |
|---|---|---|---|---|
| 1 | the population error is first present in the reader's own answer | raw answer equals first-stage input by hash in all 22 continuation readings; population identical in 21, same option re-encoded in 1; source and menu keep the relation | none on location | CONFIRMED (location) |
| 2 | the served slice rule never ties the slice to the population for which THIS amount is measured; the brand satisfies "OWN measured" and the menu literally | TASK_A 73-79 and 240-253; FINAL_DESIGN 35, 175, 299; restaurant-count row; menu token | correct original readings; F1 and whole-assertion failures; graders erred with more text | CONFIRMED as a static gap; causal contribution UNRESOLVED |
| 3 | the live law states the association only by derivation; the action clause is the one mention-based foothold | FINAL_DESIGN 35 versus 175; our old grader clause | line 35 is explicit; line 175 applies it to all types | CONFIRMED text ambiguity; no model effect tested |
| 4 | the reader misreads "primarily related to" as a whole allocation | the brand assignments | V1 read it correctly when asked; W1's source statement was faithful | UNRESOLVED |
| 5 | menu pull: the brand token plus reuse-first ordering | brand and restaurants-closed token choices | untestable while the menu must stay unchanged | SUSPECTED, untested |
| 6 | project history | none needed | D1 reproduced both errors without it | NOT NECESSARY; influence not excluded |
| 7 | broad name and non-minimal scale span | served Rule 3 and Rule 5 state both requirements | many readings comply; list removal mixed | reader non-compliance; cause UNRESOLVED; no engineering defect shown |
| 8 | period contract mismatch: the served card and the first stage accept a true lone end date on a duration; the consumer rejects it | Codex's replay, DRI_WA_Y791_MECHANICAL_REVIEW.json; TASK_A 208-238 incl. 220-221; driver_period_resolver.py line 301 | none | CONFIRMED engineering defect, separate from the population |
| 9 | state | occurred is right for the Q3 charge (FINAL_DESIGN 140) | V1 judged the Q4 closures | SETTLED for extraction |
| 10 | tax heading | closed earlier | no new primary evidence | CLOSED |
| 11 | Y309's zero comparison against the prior year | the row's dashes | the dash meaning is unsettled | UNRESOLVED (see EI) |

## EH. The one proposed diagnostic (PREPARED, NOT RUN, no launcher built)
Open distinction: (a) the served task under-defines the slice, or (b) it is defined enough and the reader still assigns the mentioned
brand. One insertion of 275 bytes at the start of Rule 7 states the association; nothing else changes. Files in
`diag_amount_population/`: TASK_C.txt (53,819 bytes), INSERTED_TEXT.txt, INSERTED_SPAN.json (byte proof), DIFF_A_to_C.diff,
CONTEXT_AS_LAST_DELIVERED.txt, PREDECLARATION.md (question, design, judging, fixed outcome table, limits). Twelve fresh serial readings, one
arm, first call alone. 0 or 1 unsupported: supports a contribution; 2 to 5: inconclusive; 6 or more: insufficient. It cannot show whether
the sentence would drop a truly stated population on other items.

## EI. Corrections to 2243, by supersession (old texts kept)
Recorded in `diag_whole_assertion/MANUAL_DISPOSITION_SUPERSESSIONS.json`; MANUAL_DISPOSITIONS.json, CONTINUATION_RESULTS.json and the
sections above stay byte-unchanged.
- Y309: the zero comparison is an UNRESOLVED uncertainty, not a confirmed unsupported comparison. The dashes may state zero or an unstated
  value, and lying outside the quote does not reject it. The record stays not correct on its brand assignment.
- Y791: four separate findings. Source truth: every field supported, the date true. Served-prompt compatibility: ambiguous. First stage:
  accepted. Later consumer: rejected, per Codex's own replay of the actual ensure_driver_period with lookups forbidden; I executed no route.
  Complete-response bar: NOT MET. Arm B then reads correct 0, not correct 10, source-supported but consumer-rejected 1.
- Memory copy: narrowed. It carries project, pilot and owner-task status and instructions. No item-specific financial-answer leak is
  demonstrated; the wire is not exposed; contamination is not claimed as a cause.

## EJ. Records and deviations this round
New: `diag_amount_population/` (6 files), `diag_whole_assertion/MANUAL_DISPOSITION_SUPERSESSIONS.json`. Changed: these sections EA to EJ
appended, ATTEMPTS.json (one superseded entry appended, current interpretation and row note updated, staged candidate 11 added), accounting
increment 25 with 0 calls, the regenerated tracker and hash roster. Deviations: (i) my first diff file used folded lines; I replaced it
with a plain line diff before reporting. (ii) The supersession file's first write cited "body items" for what are line numbers; I corrected
it before reporting. (iii) I ran one read-only comparison of the session's latest context copies against reference b689e106…, which was
not asked for; it wrote nothing.

## EK. Codex 2248 corrections, recorded BEFORE the Z101 launch (they supersede wording in EB, EC, ED, EG and EH; those sections stay unchanged)
- The missing EXPLICIT amount-to-population statement is OBSERVED. Two phrases above are interpretations, not demonstrations: that the
  brand choice is literally compliant with the served sentences (ED, EG row 2), and that the live law is defective because it states the
  association only by derivation (EC, EG row 3). Rule 3 item 4 already says OWN measured. Causal contribution stays UNRESOLVED. Readings
  (a) and (b) in EH are neither exhaustive nor mutually exclusive.
- "Sufficiently defined as served for every field except the slice" (ED) overstates the evidence. The served period requirement for a
  true lone end date on a duration remains ambiguous (Rule 6; EI, Y791). That exception stands.
- The source's relation stays qualified. The charges are "primarily related to" the closures of Bahama Breeze locations "expected to
  occur in the fourth quarter of fiscal 2026". That is not a measured majority of the dollar amount, so EC's "says most of it relates to
  that brand's closures" is superseded. It does not certify that no closure has happened, so EB's "(they have not)" becomes "expected in
  Q4 fiscal 2026". No allocation of THIS 24.7 million charge is stated for the brand; EB's "no amount is stated for Bahama Breeze" is
  superseded by that narrower statement.
- The outcome table in PREDECLARATION.md and EH is withdrawn; see diag_amount_population/PREDECLARATION_SUPERSESSION_2248.md. Only one
  reading, Z101, is authorized. No omission, refusal, malformed answer or unserved call counts as a correction. One complete supported
  reading shows the clarified task can yield the right population, and nothing more. One unsupported reading shows the clarification was
  insufficient for that reading, not zero influence. Historical-arm counts are not a causal control.

## EL. Z101: the one authorized reading of the clarified task (Codex 2248)
One Workflow invocation, run wf_2a02fce6-4ef, 2026-09-21, from a notification-origin turn with no queued owner message. Codex's reviewed
launcher was copied unchanged to diag_amount_population/ and to the scratch launch folder (all three copies sha 34bdbbd9…). Its embedded
task decodes to TASK_C byte for byte. The pre-call receipt PRECALL_Z101.json was READY: launcher, task, context render and reference
pins; 5 of 5 live files and 4 of 4 latest parent instruction copies equal the reference; date, CLI 2.1.278, 128000 cap, no API key, no
provider-fallback variable, Z101 never served. Before launch I read the complete TASK_C in three consecutive parts and the complete
context render in two. Delivery check POSTCALL_Z101.json: 15 of 15, including the frame hash, the delivered body equal to TASK_C, one user
message, no owner relay, child claude-sonnet-5, high, lean-probe, zero tools, end_turn, and context types and ordered hashes equal to the
reference including the date. The parent default model was claude-opus-5[1m]. The completion notice displayed the public answer before
preservation ran; preservation (4 files, 0 mismatches) then ran before any check or field reading.

## EM. The whole answer (685 bytes, sha 874bbfe2…), field by field (MANUAL_DISPOSITION_Z101.json)
- Population: SUPPORTED. slice_parts is omitted, which is the empty, company-level value. No part is assigned to the 24.7 million charge.
- Name: restaurant_closure_impairment, which keeps the stated closure cause.
- Type and state: action_event, occurred; the Q3 charge, not the expected Q4 closures.
- Amount 24.7 low = high, 1,000,000, m_usd, point; smallest scale span "millions".
- Period: fiscal 2026, quarter 3, duration, plus a lone period_end_date 2026-02-22. The date is true. Served-prompt compatibility is
  ambiguous. The first stage accepts it. I ran no period stage; the completed item equals in value the Y791 item on which Codex ran the
  actual ensure_driver_period, which rejected it.
- Measurement empty (truthful); no comparison; one fact; envelope valid.
- First stage (MECHANICAL_FIRST_STAGE_Z101.json): read_one 0 problems, PreparedFactV2 ok; the loaded-code hashes are recorded and match the
  pins in Codex's Y791 replay record.
- The answer is byte-identical to Y791's (whole-assertion arm B, a different task). Recorded, not pooled.

## EN. What this one observation does and does not establish
It shows that the clarified task CAN yield the supported population, with the cause-specific name and the minimal span. It does NOT show a
contribution of the added sentence, a unique historical cause, reliability or unseen performance. The original task has also produced
the supported population (fully correct in ORIGINAL-2, T39 and U109; with a non-minimal span in Y614), and the whole-assertion task produced this same answer (Y791). The complete-response bar
is NOT met, because of the known lone-end-date contract mismatch. Root cause NOT established. Example 1 NOT perfected. No further call.

## EO. Records and deviations this round
New in diag_amount_population/: PREDECLARATION_SUPERSESSION_2248.md, DRI_AMOUNT_POPULATION_SINGLE_CALL.js (Codex's bytes),
PRECALL_Z101.json, POSTCALL_Z101.json, MECHANICAL_FIRST_STAGE_Z101.json, MANUAL_DISPOSITION_Z101.json; the native evidence folder
exec/evidence/wf_2a02fce6-4ef. Appended: sections EK to EO. ATTEMPTS.json: attempt 40 added, staged candidate 11 marked executed with its
history, and the current interpretation and row note updated with the 2247 wording preserved. Accounting increment 26 (1 call). Tracker and
roster regenerated. Deviations: (i) the completion notice displayed the answer before preservation. (ii) The existing first-stage and
delivery-check scripts are pinned to the whole-assertion arm map and launcher, so I ran the same functions and checks inline, with this
call's task and launcher; the delivery check lives in scratch as postcall_z101.py.

## EP. The fixed paired comparison (Codex 2249): original task A versus clarified task C, 12 serial readings, complete
Codex's reviewed plan, launcher and no-model check were copied unchanged to diag_amount_population/paired_compare/ (PLAN.json sha
8db691d0…, launcher.js sha 43215844…). Six consecutive pairs, order fixed in the plan before any call. One Workflow invocation and one
fresh child per identity, strictly in plan order, all from notification-origin turns with no queued owner message. Every position:
a pre-call receipt READY (task and launcher pins, reference b689e106…, 5 of 5 live files, 4 of 4 latest parent instruction copies, date,
CLI 2.1.278, cap 128000, no API key, no fallback variable), then the delivery check OK 15 of 15 (frame, delivered body equal to that
position's plan task, child claude-sonnet-5, high, lean-probe, zero tools, end_turn, context types and ordered hashes equal including the
date). 12 of 12 served; 0 unserved, 0 departed, 0 retries, 0 replacements. Z101 and all historical trials stay outside.

## EQ. Every position (my hand-made records MANUAL_Z2xx.json; tallies in PAIRED_RESULTS.json)
| pos | pair | label | arm | population | name | span | lone end date | whole record | first stage |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | Z201 | C | supported (empty) | cause-specific | minimal | no | CORRECT | accepted |
| 2 | 1 | Z202 | A | supported (empty) | cause-specific | non-minimal | no | not correct | accepted |
| 3 | 2 | Z203 | A | unsupported full brand | cause-specific | minimal | no | not correct | accepted |
| 4 | 2 | Z204 | C | supported (empty) | cause-specific | minimal | no | CORRECT | accepted |
| 5 | 3 | Z205 | A | unsupported full brand | cause-specific | minimal | yes (true) | not correct | accepted |
| 6 | 3 | Z206 | C | supported (empty) | broad | non-minimal | no | not correct | accepted |
| 7 | 4 | Z207 | A | unsupported full brand | broad | non-minimal | no | not correct | accepted |
| 8 | 4 | Z208 | C | supported (empty) | broad | minimal | no | not correct | accepted |
| 9 | 5 | Z209 | A | unsupported full brand | broad | minimal | no | not correct | accepted |
| 10 | 5 | Z210 | C | supported (empty) | cause-specific | non-minimal | yes (true) | not correct | accepted |
| 11 | 6 | Z211 | C | supported (empty) | cause-specific | non-minimal | no | not correct | accepted |
| 12 | 6 | Z212 | A | unsupported full brand | broad | minimal | no | not correct | accepted |
Every reply is one action_event / occurred fact for the Q3 charge with 24.7 point, 1,000,000, m_usd, fiscal 2026 quarter 3 duration,
empty measurement, no comparison and a valid four-key envelope. Every unsupported population is the full-brand menu token; no reading chose
the restaurants-closed option. Several answers are byte-identical to earlier preserved answers (listed per record); not pooled.

## ER. Arm counts and pairwise direction (this comparison only; historical arms are context, not a control)
| measure | C (6) | A (6) |
|---|---|---|
| supported retained charge (primary) | 6 | 1 |
| unsupported full brand | 0 | 5 |
| any other category (closure/accounting option, other, missing, refusal, malformed, unserved, departed, unresolved) | 0 | 0 |
| name cause-specific / broad | 4 / 2 | 3 / 3 |
| scale span minimal / non-minimal | 3 / 3 | 4 / 2 |
| lone true end date | 1 | 1 |
| whole record correct | 2 | 0 |
| first stage accepted | 6 | 6 |
Pairs: C supported and A not in 5 pairs (2 to 6); both supported in 1 (pair 1); A supported and C not in 0.

## ES. What this does and does not establish
Under the same recorded context, on this example, the clarified task gave the supported population in all 6 readings and the original
task gave the unsupported full brand in 5 of 6; no pair went the other way. That is finite evidence that the explicit amount-to-population
sentence changes the population result for this intervention on this example. It is not a unique historical private cause, not reliability
on other items, not a production fix, and it cannot show whether the sentence would drop a truly stated population elsewhere. The
clarification does not fix naming or spans: C still gave 2 broad names, 3 non-minimal spans and 1 lone end date, so only 2 of 6 C records
are whole-record correct (0 of 6 in A). The period contract mismatch remains separate. Example 1 NOT perfected.

## ET. Records and deviations this round
New in paired_compare/: PLAN.json, launcher.js and NO_MODEL_CHECK.json (Codex's bytes); 13 PRECALL receipts (12 positions plus Z202's
superseded first receipt); 12 each of POSTCALL, MECHANICAL_FIRST_STAGE and MANUAL records; PAIRED_RESULTS.json. Native evidence: 12 run
folders under exec/evidence. Deviations: (i) every completion notice displayed the answer before preservation. (ii) Z202's first pre-call
check printed STOP on "never served": my check searched native files as text, and Z201's saved launcher script lists every plan identity.
Z202 had no run, no args and no journal line. I kept that receipt, fixed the check to use run args and journal lines (controls: Z201, Z101
and Y791 read served; Z202 and Z212 not), and a second receipt PRECALL_Z202_R2.json was READY before launch. (iii) I read the complete
TASK_C before Z201 and the complete TASK_A before Z202; for positions 3 to 12 I relied on those readings after each position's task,
launcher and reference pins and latest parent copies were checked. The context was fully read before Z101; before each position a fresh
render from the latest verified child differed from it only in the source-run line. (iv) The delivery, first-stage and pre-call checks
are the Z101 checks adapted only for the plan's task mapping, in scratch.

## EU. Round 2250: Codex's verification and additions, recorded as his
- Codex verified the paired comparison and frames it as controlled finite evidence supporting a CONTRIBUTION of the explicit
  amount-to-population definition on this example. Correct original readings and residual errors do not disprove it. It is not a unique
  private or historical cause and not unseen reliability.
- Codex's measures: name specificity A 3, C 4; full financial meaning A 1, C 4; shortest span A 4, C 3; strict raw compliance A 0, C 2.
  The two C records (Z201, Z204) are correct at the raw-reader boundary, not verified end-to-end pipeline passes.
- Codex ran the actual completed Z205 and Z210 items through the pinned pure ensure_driver_period. Both are rejected with "duration
  exact-date input needs period_start_date" before any lookup; a same-source balance-sheet instant control accepts
  (DRI_PAIRED_ACTUAL_END_ONLY_PERIOD_REVIEW.json). This is the same separate, confirmed mismatch; no repair.
- The Z202 false STOP is accepted as a checker bug. Relying on earlier complete readings after per-position checks is accepted; I claim
  no fresh complete display at positions 3 to 12. The tax heading stays closed. "Primarily related to" stays qualified.

## EV. The name relationship, from law and source (legal interpretation, kept apart from observation)
Observed in the source: the target row "Impairment due to restaurant closures3 24.7" states a charge and its cause; footnote 3 says the
charges are "primarily related to the closures of Bahama Breeze locations expected to occur in the fourth quarter of fiscal 2026".
| what | owner | meaning here |
|---|---|---|
| the Driver name | glossary line 31 ("one reusable, atomic cause or standing thing"); NAME-01, NAME-04, NAME-06, NAME-07, NAME-11, NAME-12; served Rule 3 items 1-4 | the charge, qualified by its stated cause: a restaurant-closure impairment |
| the lane | served Rule 2 (action_event includes a one-off charge); the asset_impairment entry is a LANE default | action_event; the list decides lane, not name |
| state, time, amount | glossary line 32 (a DriverUpdate is one occurrence of a Driver); line 140 and served Rule 4 (latest stage of one action); served Rule 6 | this occurrence of the Driver: the charge, recognized in Q3 fiscal 2026 (occurred), 24.7 million |
| the closures | footnote 3 | a separate company action, expected in Q4; inside the name it is the cause detail, not the happening the state and time describe |
No live rule commands the broad name, and NAME-04 forbids a broader class to force reuse, so the specific-name expectation has no
authority conflict. One gap, as interpretation: the law never says that, when an action Driver's name contains another event as its
cause, the state and time describe the charge and not the embedded event. "Name the CAUSE only" can also be read two ways: the Driver as
the cause of interest (the charge), or the cause of the charge (the closures).

## EW. Direct observations bearing on the name (public texts only; none is a private cause)
- V1, a review of U554 whose name is restaurant_closure_impairment. Its record statement says "a restaurant-closure-related asset
  impairment event occurred" in fiscal Q3. Its support statement says: "It does not establish that a restaurant closure 'occurred' in Q3
  FY2026 -- the only place that speaks to timing (footnote 3) says the closures are expected to occur in Q4 FY2026, contradicting an
  'occurred'-in-Q3 reading of the closures themselves (the impairment charge itself was merely recorded/reported in Q3)." Within one
  review, the referent moved from the charge to the closures.
- Original-task think-aloud answers, all with the broad name. ORIG-N1: "Chose `asset_impairment` because Rule 2's own bare-root default
  list names exactly this pairing ("asset_impairment → action_event"), and the row is reporting the impairment charge itself (the measured
  line item), while "restaurant closures" is the reason for it, not the thing recorded in this row." ORIG-N2 and ORIG-P1 also cite the
  Rule 2 list. ORIG-P1 separately notes that the closures are expected in Q4 while the charge is already reported in Q3, and applies
  occurred to the charge. None gives timing as a reason for the name. The C3 think-aloud answers chose the specific name.
- Every preserved answer with the 24.7 target fact (81 of them) states occurred; 77 give quarter 3 and 4 give no quarter; none gives a
  closure-style state or a Q4 period, whichever name it uses (43 specific, 34 broad, 4 specific without a quarter).
- Broad names persisted in the paired comparison (A 3 of 6, C 2 of 6). Name-list removal was mixed, and broad names appeared without it.

## EX. The reference-switch hypothesis against the strongest counterexamples
Hypothesis (Codex's, held as a hypothesis): a cause-specific name makes a reader take the record's state and time as describing the
physical closures.
- For it: V1's observed switch in review.
- Against it in extraction: producers who write the specific name keep occurred and Q3 for the charge; producers who write the broad name
  do the same; the public broad-name reasons cite the Rule 2 list and the reason-versus-recorded-thing reading, not timing; ORIG-P1 saw
  the timing tension and resolved it on the charge while still choosing the broad name for a list reason.
- Untested: whether V1's switch depends on the name at all, since V1 had no broad-name contrast.
Status: the switch is observed once in review; its dependence on the name is untested; no existing public evidence ties it to a
producer's broad name. The Rule 2 list reading and the two senses of "cause" are the better-supported public explanations, still
explanations and not causes.

## EY. The one proposed diagnostic (PREPARED, NOT RUN; no launcher invoked)
diag_name_reference/: a blind fixed-record review pair, NR1 on Z208 (broad name) then NR2 on Z201 (specific name). The two tasks differ
only in the one name line (DIFF_NR1_NR2.diff). A generic wrapper wraps the byte-unchanged TASK_C and the one record, with one output
shape: `record_assertion`, `source_statement`, `rule_conformity`. The launcher is prepared from the reviewed paired launcher's meta and
tail and is not invoked. PREDECLARATION.md holds the two questions, the reading table, the positive control (NR2 on the raw-correct Z201)
and the limits. It adds a matched contrast that V1 lacked, and a fresh reader holding each record to the served naming rules. It cannot
show a producer's cause.

## EZ. Cause and uncertainty notes now; records; deviations
- Population: a CONTRIBUTION of the missing explicit amount-to-population statement is supported by controlled finite evidence on this
  example (paired comparison). Not a unique historical cause.
- Name: the broad-name error persists with or without that sentence. Public producer explanations point to the Rule 2 lane list read as
  a naming default and to "cause" read as excluding the charge's reason. The reference switch is observed once in review. All three stay
  UNRESOLVED as causes. The specific-name expectation has no authority conflict.
- Spans: non-minimal spans recorded separately (A 2 of 6, C 3 of 6); no span experiment now.
- Period: CONFIRMED prompt-consumer contract mismatch, now also shown on Z205 and Z210 by Codex.
Records: diag_name_reference/ (builder, two tasks, two records, wrapper parts, diff, prepared checks, launcher, predeclaration),
sections EU to EZ appended, ATTEMPTS (one superseded entry, current interpretation, row note, staged candidate 13 prepared and not run),
accounting increment 28 with 0 calls, tracker and roster regenerated.
Deviations: (i) my first wrapper used the verb "Name any meaning"; my own generic-wording check flagged "name", so I reworded it to
"Identify" and rebuilt, deleting the unreported first outputs. (ii) My first predeclaration quoted a think-aloud sentence with an
ellipsis and said none of the three answers mentions a timing conflict; ORIG-P1 does. I replaced the quote with the full sentence and
narrowed the claim before reporting.
