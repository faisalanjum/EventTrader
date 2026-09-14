# SOURCE_DEFECT_CLASS_2125

Bounded defect-class inventory of the live 33-source key, for Codex SEQ 2125.
Read-only: no call, no key or candidate edit, no grading, no publication.

Code enumerated the structured rows and copied a fixed adjacency window of the
same source part around each located quote. Every semantic judgement below is
mine, made against that copied source text, and each one names its evidence.

**Inputs**

| what | identity |
|---|---|
| live key, read through `F.v6_shards` + `F.read_shard` under the accepted owner | owner `2210a3eed623de9c3a53ebde529eb34d3e79643510977b50ef635c4807ba715a` |
| mechanical inventory | `core_inv2125_a/SOURCE_DEFECT_INVENTORY_2125.json`, `16fa94663269fdcab94b2c15de43cb236234328120c5de4d12d84cff93f18e26` |
| my dispositions | `core_inv2125_a/SOURCE_DEFECT_DISPOSITIONS_2125.json`, `9bc3b259a06a2db9582fcd5d9010de81c13130ee408b26bb75ef8f08f476efc2` |
| owning law | `FINAL_DESIGN.md` `4218d73abe6b98ef2ecd325aef8b5e49985101b122e457b39784dee677f32a0b` |

**Adjacency window.** 700 characters of the same source part on each side of
the located quote. I state it because 4.3 says *alongside / beside*, and that
is the span I actually read; a same-driver prior further away than that was not
inspected and is not claimed either way.

---

## 1. The reported-metric population

The complete key is 191 located rows and 163 facts: 107 metric, 22
action_event, 18 guidance, 16 surprise. Metric states are `increased` 52,
`reported` **35**, `decreased` 14, `unknown` 4, `persists` 1, `unchanged` 1.
Every one of the 191 located quotes was found in its own part (0 missing), so
no row was judged without its source.

**The population under review is those 35 reported metric facts.** Dispositions:

| disposition | count |
|---|---|
| current state supported | 31 |
| needs independent source correction | 3 |
| genuinely unresolved | 1 |

Affected event set: `0000898173-26-000006`, `BBY_2026-03-03T08.00`,
and `0001104659-25-102611` (the unresolved one).

### 1a. Needs independent source correction — 3

**`0000898173-26-000006#052`** (control, your Q1 acceptance) — target *Ending
domestic store count*. The quote ends at `6,447`; the next cells of the same
table line are `6,265  6,447  6,265` under the header naming Three Months Ended
and Year Ended, December 31, 2025 and 2024. Same driver, same slice. 4.3 routes
a source-stated prior value beside the value to `increased`/`decreased` before
the bare-value branch.

**`0000898173-26-000006#053`** (control) — target *Total shareholders' deficit*.
The quote ends at `(763,352)` and the next cell is `(1,370,961)` for the prior
December date named inside the quote's own header. On OD-12's signed axis the
stored `-763,352` against `-1,370,961` is `increased`.

**`BBY_2026-03-03T08.00#142`** — target *was better than planned*; the metric
home fact is the adjusted operating income rate of 5% for Q4. Two sentences
later the same source states the direction for the same driver and the same
period, with a magnitude: "Our adjusted operating income rate increased 10
basis points compared to last year." 4.3 takes a **stated direction** first, so
`reported` is not the first match. **Counter-consideration, recorded rather
than hidden:** the located target names the expectation comparison, and this
metric exists as the required TWIN home sibling rather than as the located
meaning itself — a reviewer who reads the target restriction as also scoping
the home sibling's state field would leave this one alone. I judge the state
field governed by 4.3 against the source, so I call it a correction; it is the
weakest of the three and I flag it as such.

### 1b. Genuinely unresolved — 1

**`0001104659-25-102611#096`** — target is the 85% failure-and-maintenance
sales mix. The next sentence states, for the same driver, both a flat reading
and a direction: "While we have not experienced any fundamental shifts in our
category sales mix as compared to previous years, we have seen a slight
decrease in mix of sales of the accessories category and a slight increase in
the maintenance and failure categories compared to the previous two years."
4.3 carries both a stated-direction branch and an explicit-flat branch and this
one sentence triggers both; further, the direction is stated against "the
previous two years", which is not a period this fact carries. I do not resolve
it and I do not propose a rule for it.

### 1c. Current state supported — 31

Each of the 31 was read the same way and none showed a same-driver
prior-period value or a stated direction inside the window. The recurring
reasons, which are the ones you asked me to respect rather than override:

- **different measurement, not a prior period** — a GAAP figure beside its
  non-GAAP sibling, or an adjusted figure beside a reported one;
- **different slice** — a domestic count beside an international one, a
  worldwide figure beside a digital-channel one, one vendor beside a class of
  products;
- **explicit target restriction** — `0001104659-26-027061#121` names
  *International (Company-operated)* inside a two-column table, so the single
  emitted fact is the target's own column, not an omission;
- **no temporal prior exists** — covenant thresholds, facility margins,
  ownership shares and one-off charges, where the adjacent numerals are
  limits, terms or different drivers;
- **an expectation, not a temporal prior** — an actual stated against prior
  guidance routes to the surprise lane by the served metric/surprise
  definitions, and leaves the home metric's own state alone.

The full per-row list with quote, driver, disposition and reason is in the
dispositions JSON.

---

## 2. The comparative-table period class

You scoped this to a selected table target carrying multiple stated period
observations. I read the finite multi-numeral set and selected by hand the rows
whose **located quote is itself a comparative table line** stating the same
driver for more than one period. That population is **five**, and it is the
whole of it:

| row | quote (abbreviated) | numerals | facts | prior column |
|---|---|---|---|---|
| `0000006201-26-000031#000` | Loss per common share: Basic and diluted `$ (0.58) $ (0.72)` | 2 | 1 | stored as `comparison_low=-0.72`, `prior_year`, state `increased` |
| `0000764478-25-000057#048` | Online revenue as a % of total segment revenue `31.8 31.4 32.1 31.2` | 4 | 2 | stored as `comparison_low` on each, `prior_year`, state `increased` |
| `0000940944-25-000038#056` | LongHorn Steakhouse `19.3% 18.4% 90 BP` | 3 | 1 | stored as `comparison_low=18.4`, `prior_year`, state `increased` |
| `0000940944-26-000009#067` | Earnings from continuing operations `$ 2.68 $ 2.74 (2.2)%` | 3 | 1 | stored as `comparison_low=2.74`, `prior_year`, state `decreased` |
| `0001104659-26-017090#115` | North Italia Comparable restaurant sales vs. prior year `(4)% 1% (2)% 2%` | 4 | 2 | **dropped**; `comparison_low=null` while `comparison_baseline=prior_year` |

**What this measures.** The key already has a single, consistent treatment of a
comparative table target, applied in four of five cases: one fact per
current-period column, the prior-period column stored as that fact's
`comparison_*` operand with `prior_year`, and the state taken from the
direction. `#048` is structurally identical to `#115` — four values, two
windows, two years — and it emits two facts. So the two-fact count at `#115` is
**not** an anomaly and I withdraw the suggestion in my 2124 that its period
count is open.

**What `#115` does differently** is drop the prior operand while still
asserting `comparison_baseline=prior_year`. That is lawful on its face — 7.1
says a baseline may be present with null comparison numbers — so I do **not**
call it a proved defect. It is the only one of the five that does it.

**The precise remaining question, which is an emission-policy question and not
an absent identity rule.** 5.1 makes `period` the first slot of `fact_scope`,
so two periods of one driver are two identities; 4.3 simultaneously assigns a
source-stated prior value beside the value the role of the current fact's
direction evidence, and 7.1 gives it the `comparison_*` slot. Both clauses
reach the same numeral. What no clause states is **whether a source-stated
prior-period value of the same driver that is consumed as a comparison operand
is ALSO to be emitted as its own period fact, or is consumed once and not
emitted again.** The key consumes it once, without re-emitting, in all five cases. Nothing I
read contradicts that, and nothing I read confirms it. This is general to every
comparative table target, not special to this row, so it cannot be settled from
this example.

**No case in this class needs independent correction on the period count.** The
four current-only targets in the class are legitimate and preserved, and the
complete existing answers stand.

---

## 3. The smallest generic source-task clarification

One procedural sentence, source-only, no company, number, expected state or
worked example, mapped to the clauses that already exist. The block below is
MY PROPOSED WORDING, not a quotation of anything:

> Where the source states a value for the same driver in more than one period,
> say whether a prior-period value consumed as the current fact's comparison
> operand is also emitted as its own period fact, or is consumed once and not
> emitted again.

It belongs with the located-target contract that already caps emission —
"Any one of them may yield more than one fact only where the RULES below
already require a split." — because that cap
and 5.1's identity slot are the two clauses in tension. It resolves the whole
class in one line. **I have not implemented it, and I propose no rule for the
unresolved row in 1b.**

---

## 4. Next-call justification

A next source call is justified for the **three** rows in 1a, on the named
input correction: the state field must be judged against the same-driver prior
value or stated direction that the source carries, which the located-target
wording alone does not convey. The affected population is the two ORLY rows and
the one BBY row, in **three** events at most — and only two events if the BBY
counter-consideration is upheld. That is the justification; it is not, and does
not rely on, the unused invalid-only retry allowance, and no valid source call
is repeated with unchanged instructions.

---

## 5. Scope

191 rows read structurally, 35 judged, 5 period-class rows judged. I inspected
the metric `driver_state` field and the comparative-table period class only. I
did not audit units, names, guidance, slices, surprises or any production code,
and I opened no new framework. Files written: this one and the two JSONs named
above.
