# Prediction design · brainstorm 1

*Draft for discussion, 9 Nov 2026. Not approved.*
*Where this differs from the rulebook (`DRIVER_RULES_Categorized.md`), the rulebook wins until you change it.*
*Examples marked "made up" use invented numbers.*

## 1. The idea on one screen

**Goal.** At each company event, say before the price reacts: will the stock move, which way, and why. Get measurably better with every event.

**How.** Every event becomes a **sealed bet**: a prediction saved before the price is known.

```
facts ──▶ bet (before the price) ──▶ price moves ──▶ grade ──▶ after-note (hindsight)
  ▲                                                                  │
  └───────────── the next bet sees past cases and notes ◀────────────┘
```

**Three layers, never mixed**

| Layer | What it is | How far to trust it |
|---|---|---|
| Facts | What the source says, with the exact quote | Checked against the source |
| Bets | What the bot expected, written before the price | Graded by the price |
| After-notes | Why the bet missed, written after the price | A guess, and marked as one |

**Finding from today's check: most of this loop is already built.**

The earnings predictor and its Learner already bet, then explain. 12 bets and 1 after-note are saved on disk. What they lack is named facts:

| | Today | With Drivers |
|---|---|---|
| A reason inside a bet | A free sentence ("FY26 guide implies meaningful deceleration") | A pointer to a stored, quoted fact |
| Count how often a reason was right? | No | Yes |
| Reuse it for another company? | Only as written advice | Yes, by the shared Driver name |

So the work is to plug Drivers into the loop that exists, not to build a second loop.

## 2. Words used here

| Word | Meaning |
|---|---|
| Driver | A reusable name for a cause, shared across companies (`net_client_cash_flows`) |
| Update | One dated, quoted fact about a Driver |
| 8-K | A company's event filing; earnings press releases arrive this way |
| 10-Q / 10-K | The long quarterly / annual report |
| XBRL | The number tags the SEC requires inside filings |
| Sealed bet | A prediction saved before the price is known |
| Force | One fact the bot says is pushing the stock up or down |
| Watch item | A fact that could matter later but pushes nothing today |
| Net call | The bet's one final answer: up, down or flat, and roughly how much |
| After-note | A short hindsight note on why a bet was right or wrong |
| Case | One past event: the forces, the three price moves, the call, right or wrong |
| Bundle | The briefing pack the existing predictor reads before it bets |
| Rulebook | `.claude/plans/Drivers/DriversFinal/DRIVER_RULES_Categorized.md` |

## 3. The parts

```
source ─▶ 1 READ ─▶ 2 COMPARE ─┐
          3 CATCH UP ──────────┼─▶ 5 BET ─(price moves)─▶ 6 GRADE ─▶ 7 AFTER-NOTE
          4 RECALL ────────────┘                                          │
              ▲                                                           │
              └──────────────────── 8 MEMORY ◀────────────────────────────┘
          9 GUARDS (apply everywhere)        10 ROLLOUT (how we start)
```

| # | Part | Its job in one line | Built today | New work |
|---|---|---|---|---|
| 1 | Read | Turn a source into quoted facts | Saved originals with exact positions; rulebook | The AI reader |
| 2 | Compare | Say what changed against what we knew | Bundle does it loosely from raw text | Change lines from named facts |
| 3 | Catch up | What happened since the last report | Yes, in the bundle | Tie items to Driver names (later) |
| 4 | Recall | Show past cases before betting | Written lessons only | Case lookup |
| 5 | Bet | Forces, watch items, one net call, sealed | Predictor exists | Point at facts; strength; watch |
| 6 | Grade | Mark the net call right or wrong | Learner does it itself | Move it to code |
| 7 | After-note | Hindsight on what the bet missed | Learner exists | Miss type; deeper-read trigger |
| 8 | Memory | Keep the three layers apart but linked | Files + database | Link bets and notes to facts |
| 9 | Guards | Rules that keep it honest | Mostly in the rulebook | Two code checks |
| 10 | Rollout | Start small, prove it | Nothing | Hand test, then 30 companies |

Each part below has the same shape: **job · in → out · how · example · built · new · open questions.**

---

## Part 1 · Read

**Job.** Turn one source into facts the bot can trust.

**In → out.** A saved original (exact text positions) → Driver updates, each with its exact quote, plus the company's own cause links.

**How**

- A Driver is a shared cause name. An update is one dated, quoted fact about it.
- Four kinds of fact are on: a measured number, company guidance, a surprise, an action or event. Analyst forecasts are off (rule 9.11).
- **Cause links.** When the company itself writes "driven by X, partly offset by Y", the two facts are linked, with that sentence as proof (rule 3.53). Only inside one document, only in the company's words.
- Saving a fact never depends on whether the price moved (rule 2.33). Nothing real is dropped; ranking happens later.

**What gets read**

| Source | When | Why |
|---|---|---|
| Earnings press release + earnings call | Every company, every quarter | Short, and where prices move |
| XBRL numbers | Always, no AI | Free record of past values |
| 10-Q / 10-K text | Only when a miss or a watch item calls for it | Huge and costly to read |
| Other 8-Ks (deals, executive changes) | As catch-up first (Part 3); own bets later | Fewer, mixed importance |
| News | Catch-up only for now | Off as a fact source (rule 9.5) |

**Example** (AMG, Q1 2023 release; the earnings figure is real, checked today)

```
economic_earnings_per_share   $4.18       "Economic EPS of $4.18 in first quarter"
net_client_cash_flows         an outflow  (amount in the release's table)
dividend                      declared    "$0.01 per share ... payable May 25, 2023"
```

**Built.** Saved originals with exact positions ("Prepare", about 9,700 lines; three 8-Ks ran offline today in 8–12 seconds each). The rulebook for facts.

**New.** The AI reader (not built). Cause links (designed, not built).

**Cutting filings into AI-sized pieces ("label and cut").** Likely not needed for the first loop: a press release or a call should fit one read. My 1–2 Nov notes put AMG's whole 8-K at about 89K tokens (the unit AI reading is counted in) in the heaviest format. Needed once 10-Q/10-K reading starts.

**Open questions**

1. Does a release plus its call fit one read, with room left to think? Measure on three filings.
2. Reading only what changed in a 10-Q/10-K breaks rule 8.10 (read everything). Your call.
3. How do we prove under 1% wrong? Ideas so far: the SEC's own number tags as a free answer key for 10-Q/10-K; a hand-made key for press releases.
4. Which AI model reads (FinalPlan Phase 6 decides this).
5. Read quiet quarters too? I say yes; otherwise the bot never learns what does not move a stock.

---

## Part 2 · Compare ("what changed")

**Job.** Turn levels into changes. The bot bets on what changed, not on what is.

**In → out.** New facts + what we already knew → one change line per fact.

**Four yardsticks, each a plain lookup with no AI**

| Compared with | Example (made up) | Comes from | Today |
|---|---|---|---|
| The same Driver's last value | Outflows −$3.2B, was −$1.1B | Driver store, XBRL | XBRL is in the database; Driver store not built |
| The company's own earlier guidance | Guided $4.00–4.20, delivered $4.18 | Guidance facts | Bundle has a guidance section; it was empty in the WMT sample |
| What analysts expected | Expected $4.05 | An estimates feed | In the bundle, but the feed failed in the WMT sample; off in the Driver rules (9.11) |
| Never seen before | "One customer is 40% of sales" | Driver store | Not built |

**One change line** (made up)

```
net_client_cash_flows  −3.2B | last −1.1B (worse) | guidance: none | analysts: none | named in 9 of 12 past reports
```

**Built.** Bundle sections: Results & Expectations, Forward Guidance, Consensus History, Prior Financial Trends (8 quarters of XBRL in the WMT sample). They work from raw press-release text, not named facts.

**New.** Change lines built by code from named facts.

**Open questions**

1. Switch analyst expectations back on (rule 9.11)? Without them a bet cannot tell a beat from a miss.
2. Can we get past analyst estimates as they stood on the day? The WMT bundle warns its forward estimates are not safe for history runs.
3. Like with like: the same unit, period and definition must travel with every number.
4. Is "first time seen" judged per company, or across all companies?

---

## Part 3 · Catch up

**Job.** Know what happened between the last report and this one, so the bot knows what is already in the price.

**In → out.** News, other filings and daily prices since the last report → a short "since last report" list.

**How**

- Runs at event time, not as each item arrives. Every item keeps its own publish time, so reading late is safe for history runs (rule 1.14).
- Skim every headline. Open the full story only on days the stock moved notably: the price has already marked which days mattered.
- For Drivers that are just a number (oil, interest rates): read the number's change, not the stories about it.

**Why it matters.** If the company warned three weeks ago, the report confirming it will not move the stock.

**How much there is** (checked in the database)

| | |
|---|---|
| News items, 796 companies, since Jan 2021 | 348,669 |
| Typical company | about 15 per quarter |
| Heaviest company | about 470 per quarter |
| Items on days the stock moved 3+ points against the market | 110,929 (about a third) |

**Built (new finding).** This already exists as the bundle's "Inter-Quarter Events" section. In the WMT sample it covers 60 trading days, marks 6 as notable, and lists 85 news items and 4 filings, with the stock, market and sector move for each day. The "notable day" rule exists too: `scripts/earnings/get_significant_moves.py` (big in plain terms and big against the stock's usual swing).

**New (later).** Tie catch-up items to Driver names so they join the cases. Bets on news-day moves.

**Open questions**

1. News as stored facts stays off (rule 9.5), and a news story has no clear owner company (parked item P4). Until you decide, catch-up is background for the bet, not stored facts.
2. Does "skim all, open only notable days" miss slow-building items? Test in the hand trial.
3. Where do market-wide numbers come from (left open in rule 10.1)?

---

## Part 4 · Recall

**Job.** Before betting, show the bot what happened the last times.

**In → out.** The Drivers that changed → for each: past cases for this company, past cases for its industry, open watch items, past after-notes.

**A track record is a list of past cases. It is looked up when needed, never stored as a score.**

```
Delta × oil_price                                            (made up)
  2024-03 | oil up | stock −5 · airlines −5 · market 0  | call down, right
  2023-10 | oil up | stock −2 · airlines −1 · market +1 | call down, right
  2023-06 | oil up | stock +1 · airlines 0  · market 0  | call down, wrong
Airlines × oil_price:  oil up → stock down in 14 of 17 events
```

**Rules**

- **The record sits on the pair Driver × company**, with its direction. Never one global grade: oil up hurts Delta and helps Exxon, and one grade would cancel them out.
- **Always two lines:** the company's own cases and its industry's. Both counts are shown; there is no "enough history" cut-off.
- **A mixed industry line (say 5 of 10) means "don't borrow".** That handles refiners versus oil producers with no extra machinery.
- **Count events, not companies.** One oil shock that hits ten airlines is one case, not ten.
- **Each case shows both sides of the tug of war**, so the bot sees which force won against which.
- **Three plain moves side by side** (stock · industry · market), no subtraction. "Stock −5, airlines −5, market 0" reads at once as industry-wide.
- **A day-one signal that needs no prices:** "the company named this Driver as a cause in 9 of 12 reports" (from Part 1's cause links).
- **Past years are filled in by arithmetic** (fact × price move), not by AI judgment, because the AI may remember how old events turned out.

**Built.** Price moves at four levels (stock, industry, sector, market) on every filing in the database, for the first hour, the session and the day. Official industry groups. A library of written lessons with "helped / misled" counts, scoped to a company, a sector, the whole market or a named group (from the Learner).

**New.** The case lookup: one query, once facts and bets are stored.

**Open questions**

1. Is the official industry good enough as "companies like it"? Start there; add nothing until it proves too mixed.
2. How are arithmetic-only past cases (no bet was made) shown apart from real bets?
3. How many cases to show, and in what order?
4. Keep the written lessons next to the cases, or let cases replace them? My lean: keep both for now (cases are evidence, lessons are advice) and decide after the hand test.
5. What counts as "the same kind of change" for facts that are events, not numbers?

---

## Part 5 · Bet

**Job.** Commit to one call that can be wrong, before any price is shown.

**In → out.** Change lines (Part 2) + catch-up (Part 3) + past cases (Part 4) → one sealed bet.

**Shape** (made up)

```
AMG · Q1 2023 · sealed 07:05 ET, before the market opened
  pulling up:    earnings above guidance        weak
  pulling down:  client outflows                strong
  watch:         one client holds 12% of assets (no push today)
  net call:      down, about 2%
```

**Rules**

- **Every force points to a stored fact.** No free-sentence reasons.
- **Strength is weak, medium or strong.** The rulebook's scale is 0.1 to 1.0 (rule A2.3); three levels sit on it. Go finer only if the trial shows finer can be learned.
- **A strength is the bot's claim.** It is never a share of the move and never graded alone (rule A2.6).
- **Bet on the root cause, not the symptom.** Follow the company's own cause links: margin fell ← fuel cost rose ← jet fuel price rose. The force is the jet fuel price.
- **The call must agree with its own forces.** Code checks this (for example: only strong upward forces, yet a "down" call → rejected).
- **List every real force**, not only the top three.
- **Sealed:** saved with its time before the price, and the bot is never shown later prices (rules 1.14, A2.5).

**Why both sides, not one main reason**

| One main reason fails because | Example |
|---|---|
| It hides the override | Earnings beat, guidance cut, stock falls → "beat → fell" teaches the wrong lesson |
| It hides cancelling | Two strong forces that cancel look like "nothing mattered" |
| It loses the type of miss | You learn right or wrong, never why |

**Built.** The predictor (`.claude/skills/earnings-prediction/SKILL.md`). It already gives: long / short / no call; confidence 0–100; an expected move range; 1 to 3 reasons, each with a side; an evidence list; data gaps. It already asks "what's new", "what's already priced in" and "what's the strongest case against".

**New (small).** Reasons point at fact ids. Strength. Watch items. The agreement check.

**Two new proposals**

- **Add "flat" to the net call.** Your goal is "will it move". Today's choices are up, down or "no call" (don't know). "I expect no real move" is a different, gradable answer.
- **Make the bet's forces the rulebook's "explained by" records** (Part A2). They are written blind, which is exactly what rules 1.14 and A2.5 demand. That settles parked item P7: the predictor submits them, and the Learner (which sees the return) only writes after-notes.

**Open questions**

1. Up / down / flat: where is the line for "flat"?
2. Size: a rough range, or buckets?
3. Keep the 0–100 confidence, or let the strengths carry it?
4. Which price window is the bet about: first hour, the session, or the day (rule 10.1)?
5. May the predictor be the approved source of "explained by" records (rule A2.1 needs your approval)?

---

## Part 6 · Grade

**Job.** After the move, mark the net call right or wrong. Done by code, not by AI.

**In → out.** A sealed bet + the stored price moves → right or wrong on direction; the size error is noted.

**Rules**

- **Only the net call is graded.** Direction first. Size is recorded, not graded yet.
- **Yardstick: the stock against the market.**
- **Quiet events are graded too**, so the bot learns what does not move a stock.
- **A big move with no bet, or with no force that explains it, is a miss.** It triggers Part 7's deeper read.

**Why "against the market" is enough** (checked: 11,201 8-K events where the stock moved 3% or more)

| | Events | Share |
|---|---|---|
| "Against industry" and "against market" point opposite ways | 102 | 0.9% |
| Industry itself moved 2+ points away from the market | 1,224 | 11% |

Direction is almost never affected; size is, more often. So grade direction on one yardstick, and show all three moves in every case line.

**Built.** The price moves (stock, industry, sector, market; hour, session, day). Today the Learner works out right or wrong itself, from the plain stock move.

**New (proposal).** A few lines of code do the grading instead, so no AI judgment sits in the score.

**Open questions**

1. Which window, and how big a move counts (rule 10.1)? The existing notable-move rule could be reused.
2. How is a "flat" call graded, and a "no call"?
3. Today's Learner grades on the plain stock move; this design says against the market. Pick one.

---

## Part 7 · After-note

**Job.** After grading, write a short hindsight note on what the bet got right or wrong.

**In → out.** The bet + its grade + the actual moves → one note, tied to the bet.

**Example** (made up)

```
Bet:        AMG down ~2%, because client outflows (strong)
Actual:     stock +4%
After-note: Call wrong. Type: missing force.
            The release also raised the share buyback; the bet didn't list it.
            Guess: the buyback outweighed the outflows.
```

A later session on AMG sees this and checks buybacks first.

**Rules**

- **Marked as hindsight. Never a fact.**
- **Three types of miss:** wrong side, wrong strength, or a missing force.
- **A missing force triggers a deeper read** around that date (10-Q text, other filings, news). What it finds is saved as a normal fact through Part 1. This is how a new Driver gets noticed.
- **The note writer may see the price. The bet writer never does.**
- **Future bets see notes as hints**, clearly labelled as guesses. Only graded bets count as evidence.

**Built.** The Learner (`.claude/skills/earnings-learner/SKILL.md`). It already writes: the main cause, up to 3 contributing causes, what worked, what failed, why, reusable lessons (each with "applies when" and "invalid if"), and a review of every earlier lesson (helped / misled / outweighed / missed / neutral / unclear). It has 1 saved result so far.

**New.** The type of miss. Pointing at Driver names instead of free labels. The deeper-read trigger.

**Open questions**

1. How do we stop hindsight stories from piling up as if they were knowledge? My lean: notes never change a count; only graded bets do.
2. Keep the Learner's lesson library as it is, or fold lessons into after-notes?
3. Who decides how deep a "deeper read" goes, and what it may cost?

---

## Part 8 · Memory (your "context graph")

**Job.** Keep the three layers apart but linked, so a new session can see what mattered before and how past reasoning failed.

| Layer | Holds | Written | Can it change? |
|---|---|---|---|
| Facts | Drivers, updates, cause links | When a source is read | Never repaired after saving (rulebook) |
| Bets | Forces, watch items, net call, saved reasoning | Before the price | Sealed |
| After-notes | Hindsight | After the price | Added to, never edited |

**How they link**

```
Company ── event (8-K) ── fact (update) ── Driver (name shared across companies)
               │               ▲   └─ caused by / offset by another fact (company's own words)
               └── bet ────────┘ force: side + strength   (= the rulebook's "explained by" record)
                    ├── grade
                    └── after-note
```

- **The Driver name is the only bridge** across documents and companies. Example: Delta's filing blames the jet fuel price; a news item about jet fuel carries the same Driver name; so the bot knows who has blamed it before, before they report.
- **No AI-guessed links are stored.** Only the company's stated causes (inside one document) and the bot's sealed forces.
- **Reasoning hangs off a graded bet.** The predictor already saves its reasoning per bet. Reasoning with no grade is stored opinion, and later sessions would inherit its mistakes.
- **Watch items live here:** open → became a force (with the date), or retired (with the reason). Never silently dropped.

**Built.** The database: companies, filings, prices, news, XBRL. Bets and notes saved as files per company and quarter (`earnings-analysis/Companies/<ticker>/events/<quarter>/`). The Driver store is designed in the rulebook, not built.

**New.** Forces saved as "explained by" records. Watch items. The link from an after-note to its bet.

**Open questions**

1. Bets and notes: stay as files, or move into the database? My lean: files for the hand test; the database once the case lookup needs it.
2. Must bets enter through the Driver system's single entry door (rule A2.1)?
3. Who may retire a watch item, and what counts as a good reason?

---

## Part 9 · Guards

Rules that apply to every part.

| Guard | Why |
|---|---|
| Facts, bets and after-notes never mix | Hindsight must not pass as fact |
| The bet writer never sees later prices; history runs see only what was public then (rules 1.14, A2.5) | Otherwise the test is fake |
| Past years build cases by arithmetic; only new events prove skill | The AI may remember how old events turned out |
| Never drop a fact, only rank | A cause can matter for the first time |
| The call must agree with its forces (code check) | Stops fence-sitting |
| Count events, not companies | One shock is not ten proofs |
| A company's stated cause is a claim | Management likes blaming weather and the economy; graded bets confirm it |
| AI calls run on subscription only (rule 8.12) | Cost |

**Open question.** How do we measure "the AI remembered"? One idea: compare skill on events before and after the AI model's training cut-off date.

---

## Part 10 · Rollout and proof

| Step | What | Proves |
|---|---|---|
| 0 | By hand, no code: three earnings reports in a row from one company. List the facts, bet before looking at the price, then check what was missed and what was flagged for nothing. | The bet's shape works |
| 1 | The thin loop on about 30 companies: press releases and calls only | The loop runs end to end |
| 2 | A three-way trial on the same events: XBRL numbers only → plus release and call facts → plus full 10-Q/10-K reading | Whether mass-reading 10-Ks earns its cost |
| 3 | Widen: more companies, bets on news-day moves, cross-company reading | Scale |

**How we know it works**

- Direction right more often than today's predictor without Drivers, on new events.
- Fewer big moves that no bet explained.
- Watch items that later became real forces (the watch list is earning its place).

**Open questions**

1. Which company for step 0? AMG (we already ran its 8-K today), or AVGO / FCX (three saved bets each, so we can compare old against new directly)?
2. Which 30 companies, and which years?

---

## 4. How it gets smarter on its own

- **Grades sharpen the ranking.** Drivers that keep being right for a company rise; ones that never move anything sink, but are never deleted.
- **Misses trigger deeper reads**, which surface new Drivers.
- **Watch items get confirmed or fade.**
- **Cause links give a signal from day one**, before any bet has been graded.

## 5. Decisions that are yours

| # | Decision | Rule | Part |
|---|---|---|---|
| 1 | Switch analyst expectations back on? | 9.11 | 2 |
| 2 | Allow reading only what changed in a 10-Q/10-K? | 8.10 | 1 |
| 3 | How big a move counts, and over which time window? | 10.1 | 5, 6 |
| 4 | Predictor writes the "explained by" records; Learner writes only after-notes? | P7, A2.1 | 5, 7 |
| 5 | News: background only, or stored facts? | 9.5, P4 | 3 |
| 6 | Add "flat" to the net call? | new | 5 |
| 7 | Which company for the hand test? | new | 10 |

## 6. Ideas we tried and dropped (so we don't circle back)

| Idea | Why dropped | What replaced it |
|---|---|---|
| Save and AI-read everything, filter later | Too costly for 40–50K filings | Read short documents for all; long ones on demand |
| XBRL network alone | It holds what was reported; stocks move on what was unexpected | XBRL as the free baseline |
| One grade per Driver | Oil up hurts Delta and helps Exxon; they cancel | The record sits on Driver × company |
| A stored score | Hides the cases and invites formulas | A list of past cases, looked up |
| One main reason per bet | Hides overrides and cancelling | Tug of war: both sides, one net call |
| Explain the price after seeing it | Invites story-telling | Bet first; hindsight kept separate |
| Grade against the industry only | Hides industry-wide shocks | Show three plain moves; grade against the market |
| Read each news item as it arrives | Cost and noise; bets happen at report time | Catch up at event time |

## 7. Limits

- **Slow learning.** A company reports four times a year. The industry line and the cause links help; they do not remove the limit.
- **Only as good as what is fed in.** In the WMT sample the analyst feed failed, guidance was empty and no peers were found. That bet's confidence was 30 out of 100.
- **The loop has barely run:** 12 bets, 1 after-note.
- **The AI may remember old outcomes**, so past years cannot prove skill.

## 8. Suggested order for redoing the parts

Start from the end, as you said: the bet's shape decides what every earlier part must supply.

```
5 Bet → 6 Grade → 7 After-note → 4 Recall → 2 Compare → 3 Catch up → 1 Read → 8 Memory → 10 Rollout
```

Part 9 (Guards) is checked against each part as we go.

## 9. Where the numbers came from

| Number | Source | When |
|---|---|---|
| 12 bets, 1 after-note, 15 bundles on disk | File count under `earnings-analysis/Companies/` | 9 Nov |
| WMT sample (60 days, 6 notable, 85 news, 4 filings; feed failed; confidence 30) | `earnings-analysis/Companies/WMT/events/Q4_FY2025/` | 9 Nov |
| News counts | Database query | 9 Nov |
| 11,201 / 102 / 1,224 events | Database query | 9 Nov |
| Predictor and Learner outputs | Their two SKILL.md files | 9 Nov |
| Three 8-K test runs, 8–12 seconds | My offline runs | 9 Nov |
| AMG 8-K ≈ 89K tokens | My 1–2 Nov notes, not re-measured | 1–2 Nov |
| Rule numbers | Looked up in the rulebook | 9 Nov |
