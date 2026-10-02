# Redesign scratchpad — Claude's working notes on the Driver design

*Started 2026-10-01. The owner asked for "a scratch pad, mental notes… keep referring to those and keep updating that as we talk." This file is my understanding, my reasoning and the open threads. **Nothing here is a decision.** The rules stay in `DRIVER_RULES_Categorized.md`, plus owner rulings. A number like (2.40) points to a rule in that file.*

**Before answering any Driver design question, re-read:** §0 · §11 (tensions) · §12 (open decisions) · §14 (how the owner wants it). Add to §15 (log) after each step.

---

## 0. The whole design in 10 lines

1. **Goal (owner, 2026-09-30):** "turn financial text into consistent, source-backed facts about reusable Drivers — so we can track changes, explain stock moves, learn what matters, and improve predictions." Loop: extract → explain moves → learn → predict → trade (1.3).
2. **Driver** = one reusable cause name (`revenue`, `oil_price_per_barrel`, `fed_rate`) + a fixed type + frozen birth evidence. It never changes and has no status (2.1, 2.2).
3. **Fact** (DriverUpdate) = one quoted occurrence of a Driver in one document. ID = document + Driver + scope (period · slices · measurement tags · surprise kind) (3.1, 3.2). 24 stored fields (3.3).
4. **Four types**, fixed per Driver: `metric` · `guidance` (name ends `_guidance`) · `surprise` (`_surprise`) · `action_event` (1.5).
5. **The one law:** merging two meanings is permanent damage; when unsure, keep separate (1.12).
6. **Nothing is fixed after saving** (6.20): all protection happens before the write.
7. **Quality bar:** fewer than 1% wrong *whole* facts, measured at launch on ~300 graded facts (8.17). **The owner's 5 priorities, in order** (Notion Code Flow page, 2026-10-01): ① prediction first — judge every piece by how much it helps explain moves → learn what matters → predict · ② near-100% recall and precision (exactly 100% not chased) · ③ lowest cost — cheapest worker that passes; subscription limits count as cost; the smart model reads as little as possible; **never re-read the same text** · ④ fastest run, Docling to save · ⑤ minimal, well-organized code.
8. **Who decides:** AI judges meaning; code does structure, math, dates, IDs and writing; whatever proposes never approves (8.1, 8.2).
9. **Today:** 221 rules sorted into 19 homes · Notion has the 19 pages as empty templates · Neo4j has 0 Drivers · the code checks facts and plans saves but cannot write.
10. **Newest proposal:** `rough_design.md` — Prepare → Read → Name → Judge → Match → Save. Unproven. On 2026-10-01 the owner said they had not understood it and asked for an explanation from the start.

---

## 1. Timeline (to refresh memory)

| When | What happened |
|---|---|
| ≤ 2026-09-15 | Old build: FINAL_DESIGN + ChannelContract + BUILD + owner rulings (`Steps.md`) + a 14-step roadmap. Experiment A7 (Sonnet fills all 24 fields on 33 real events) **failed**: recall 74.6% / 70.3%, strict 43%, wrong accepts. Owner: "paralysis by analysis". |
| 09-25/26 | **Restart:** keep only the decided rules, drop the old implementation → `DRIVER_RULES.md` v1.0 → v1.1 (frozen). |
| 09-27 | Notion `Drivers › Workflow` chart built (channels → propose → ◇ exists? → create / add). Decisions D1–D43. |
| 09-28 | D44 "no stages, no placeholder"; Revision 13 "no after-save process of any kind" → v2 = `DRIVER_RULES_Simplified.md`. |
| 09-29 | Rules sorted into 19 homes → `DRIVER_RULES_Categorized.md`; audit L1→L4 (D1, D3–D10 applied); Notion restructured into the 19 homes; owner: price moves (S5) **on** in release 1; P7 found; JEV tests start. |
| 09-30 | Fact-type study (90.2% clean; gaps: causes, outside forecasts, units) → `fact_types.md` (`expectation` as a 5th type, `caused_by`); owner: "the entire design, not release 1 vs 2", aim ~100%; Docling study; XBRL definitions pilot; JEV identity / XBRL / cause tests; "Option 1" reading chosen over a manager agent; `rough_design.md` written. The owner moved Simplified + JEV scripts into `Archive/`. |
| 10-01 | rough_design committed (`cff88cbb1`). Owner: "I haven't understood the rough design… start from the beginning." Another session began a from-zero walkthrough, then **built the Notion "Code Flow" page** (the run map): the owner's 5 priorities, "What comes in" (news · transcripts · SEC reports → *ingested* → 1 Cut), the 6 steps with who/trigger. Owner: "two use cases: creating these drivers from all the financial text, and updating them — we should be able to do both" → "one flow, two uses; step 5 decides". This session (in parallel): full re-read → this file. |

---

## 2. Words (plain)

| Word | Meaning |
|---|---|
| Driver | A reusable name for a cause or standing thing (`revenue`). |
| Fact / DriverUpdate | One quoted occurrence of a Driver in one document. |
| Source event | The one whole document a fact comes from: a filing (all sections + exhibits), a call transcript, or a news story. |
| Scope | The parts of a fact's ID besides document + Driver: period, slices, measurement tags, surprise kind, tie-breaker. |
| Slice | Which part of the company: `segment:taco_bell`, `geography:china`. None = the whole company. |
| Measurement tag | How a number was measured: `adjusted`, `diluted`, `constant_currency`. |
| Family | `revenue_guidance` and `revenue_surprise` belong to `revenue`. Read from the name, never stored. |
| Birth fact | The fact a Driver was created with. Its ID, quote and needed context are frozen on the Driver. |
| Catalog | The list of Driver names that new facts are matched against. |
| Held / skipped / rejected | Waits for a named trigger / a final, counted "not written" / broke a rule. |
| Verdict | A stored claim "this fact helps explain this price move" (`EXPLAINED_BY`). |
| Channel | Where candidate evidence comes from (Fiscal AI, Guidance pipeline, News, Predictor/Learner). |
| JEV | TypeSafe's paid judge model: yes/no, pick-one, or score. Never writes text. $0.042 per million input tokens. |
| Docling | A document parser that recovers sections, paragraphs and tables. |
| `caused_by` | Proposed field: on an effect fact, each cause its source states (cause fact ID, role, quote, amount). |
| Phase 6 pool | The owner-approved test pool of AI models: local model, Haiku, Sonnet 5, Luna. JEV is not in it. |
| Public time | When a document became public. Nothing published later may be used (no look-ahead). |
| ① ② ③ | Release numbers on the Notion chart. |

---

## 3. Files — what each is, and who wins

**`DriversFinal/` (current)**

| File | What it is | Status |
|---|---|---|
| `DRIVER_RULES_Categorized.md` | 221 rules in 19 homes; Neo4j pictures A/B/C + link tables; parking list P1–P7; 8 overlap pairs; Overview (Start here, design map) | **The rules.** Holds all 906 lines of the archived master + 118 heading lines (checked 2026-10-01) |
| `rough_design.md` | 6-step reading design, causes, safety nets, 10 owner decisions, pilot plan | Rough, unproven, not approved |
| `fact_types.md` | Recommendations: keep 4 types + add `expectation`; `caused_by`; units; boundaries; evidence | Recommendations; Codex maintains it; I give edits in chat only |
| `JEV.md` | Every JEV test: setup, results, open rulings, ideas, constraints, prompts | Exploratory; nothing adopted |
| `DRIVER_CODE_GUIDE.md` | What the `driver/` code does today, per home | Reference (2026-09-29) |
| `XBRL_Definitions.md` | Per-filing XBRL dictionary builder: 981/981 reports passed | Handoff; no database writes |
| `Dockling/docling.md` | What Docling returns + my 20-filing test | Pilot |
| `REDESIGN_SCRATCHPAD.md` | This file | My notes |

**`DriversFinal/Archive/` (history)**

| File | Use it for |
|---|---|
| `DRIVER_RULES.md` (v1.1) | The *why*: Part B = 53 rejected ideas (don't reopen without new evidence); Part C1 = the source of every rule; C4 = which source wins |
| `DRIVER_RULES_Simplified.md` | Former master (same lines) |
| `AUDIT_1_to_4.md` | Proof that nothing was lost from design documents → rules; D1–D10 |
| `WORKFLOW_SCRATCHPAD.md` | Owner-message log (keep logging there), decisions D1–D44, Notion page IDs and chart conventions, the archived no-stages proposal |
| `JEV scripts/` | All JEV test code, frozen answer keys, results |

**When documents disagree:** the Categorized rules → (where silent) owner rulings in `Steps.md` → `FINAL_DESIGN.md` for meaning → ChannelContract / BUILD / the three step-9 documents → archive = evidence only (v1.1 C4). **Owner rulings made after the freeze** (scratchpad log, JEV.md §3.1) win over the rules text but are not written into it yet (§11).

**Older design sources** (`.claude/plans/Drivers/FinalDesign/`, `LeftOverSteps/`, `WIP/`): FINAL_DESIGN (meaning), ChannelContract (what channels send), BUILD_AND_OPERATIONS, STATUS_AND_HISTORY, Steps.md (Aug–Sep rulings). **Phase 6 and Route D** live in `WIP/UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md`:
- Route D = split a document at its own blocks (paragraphs, table rows, Q&A exchanges), keep neighbours, prove no evidence is lost, code copies quotes by ID.
- Phase 6 = start with the cheapest approved model; escalate only on ambiguity, invalid output, verifier conflict or no proven match; report quality and resource use separately.

---

## 4. Notion — `Drivers` (all 33 pages read 2026-10-01; Workflow last edited 2026-10-01 14:34 UTC by the other session)

```
Drivers
└─ Workflow  (main chart + legend + "Graph in Neo4j" link + GitHub link + folded "Box pages")
   ├─ Channels: Guidance pipeline ② · News ③ · Fiscal AI ① · Predictor/Learner ①
   │        └──────────────► propose Driver ("before seeing existing names") ─┐
   ├─ Update source: Filings & Transcripts ("update only") ───────────────────►◇ Driver already exists?
   │                                          No  ─► create Driver ▸   (1 · 2a [4 types] · 2b · 2c · 3 ⇒ first DriverUpdate)
   │                                          Yes ─► add DriverUpdate ▸ (U1a–U1d · U2a–U2c · U3a–U3b)
   ├─ side box "Rules for every step": System ▸ (S1–S5)
   ├─ side box "How it's built": Code Flow ▸ (under System; added 2026-10-01)
   └─ 🗺️ Graph in Neo4j (pictures A/B/C, stored and not-stored link tables, open points)
```

- **State:** every box is red (Open). The 19 home pages hold only: trail · Question · "Rules here" + GitHub link · overlaps / parking items. Flowchart, Examples, Watch-outs, Your design, Rules: **all empty**. Workflow has no comments.
- **Code Flow page** (`3eca0a3f310681678852e706a704604e`, built by the other session 2026-10-01; status "proposed, nothing agreed yet"; re-read 14:48 UTC, no comments):
  - 🎯 the owner's 5 priorities (§0 line 7), now a collapsed toggle with shortened wording ("nothing read twice");
  - "What comes in": News 348,670 · Transcripts 9,608 · SEC reports 42,633 (8-K 29,672 · 10-Q 7,301 · 10-K 2,993 · other 2,667: 425s, amendments, 13D, 6-K…) → **Ingested** (the trigger) → 1 · Cut;
  - "One flow, two uses: build Drivers from all past text (oldest first), then update them as new text arrives. Step 5 decides: new name → create; known name → add an update." ⚠ callout: this contradicts the Filings & Transcripts page; owner to decide;
  - 6 steps: 1 Cut (code + Docling) → 2 Read (cheap AI) → 3 Name (smart AI) → 4 Details 💡 (JEV + code; suggestion only) → 5 Match (code + AI check) → 6 Save (code); a table of action · who · trigger · example · status; source = rough_design.md; a change log.
- **The charts are study maps, not run order** (said on the create Driver and add DriverUpdate pages).
- **Box-page notes worth remembering:**
  - Guidance pipeline ②: reuse the existing guidance extraction (skill, worker, trigger daemon, writer).
  - News ③: "after the fact": pick days with extraordinary moves → find why → the reason becomes a Driver; drop filing-driven days; never tell the reader the move; source = Benzinga via Massive (subscription expired).
  - Fiscal AI ①: "creates once from its existing KPIs"; watch-outs 6.11, 1.13, 8.17.
  - Predictor/Learner ①: both might submit sources (⚠ think it through against 1.4 and 9.7); P7; to-do: separate them.
  - Filings & Transcripts: "filings never create Drivers; only channels do"; triage-agent idea (maybe JEV).
  - ◇ Driver already exists?: "an LLM checks by meaning, even with no exact name match".
- **Writers:** another Claude session is actively editing Notion (Code Flow) and the shared log today. I read only; re-fetch before any edit, and only with the owner's yes.
- **How to edit:** keep charts in Preview (the owner never wants to see chart code); change charts in place with `update_content`; links use `_top` (they still open new tabs); red border = open, green = resolved. Full page-ID table: `Archive/WORKFLOW_SCRATCHPAD.md` → "Chart conventions and page ids". Key IDs: Drivers `3e8a0a3f3106817da82cd9d50a6df263` · Workflow `3e8a0a3f310681a3842cca0225182c00` · System `3eaa0a3f310681329681cec325306e80` · Graph `3eba0a3f3106813497d2dc79a02cdb82`.

---

## 5. Live state (checked)

- **Neo4j (read-only, 2026-10-01):** Driver 0 · DriverUpdate 0 · DriverPeriod 0 · no constraints on them. Report 42,633 · Transcript 9,608 · News 348,670 · Company 796 · old GuidanceUpdate 8,432 (evidence only, 8.11). → **Greenfield: nothing to migrate.**
- **Code (`driver/`, per DRIVER_CODE_GUIDE):** finds filing evidence (fiscal.ai channel + relocation), checks proposed facts, combines pieces, plans saves. Real writes are blocked.
  - **Missing:** the reader, naming, identity/matching, the XBRL concept linker, read views, verdicts, withdrawal spreading.
  - Two input paths (V1 old, V2 new). The older paths still follow some old rules: growth defaults to year-over-year; an unknown-state birth fact is allowed; a wordless beat exactly at consensus is corrected only in the old path.
  - The writer stores exactly 24 fields. Its one-writer lock turns a second writer away (`WRITER_BUSY`); it does not queue.

---

## 6. The design in pictures

### 6a. What is stored

```
(:Driver)  name · fact_type · frozen birth evidence           ← company-neutral, never changes
   ▲ OF_DRIVER (exactly 1)
(:DriverUpdate)  one fact · 24 fields · id = source + Driver + scope
   ├─ FROM_SOURCE (exactly 1) ─► (:Report) | (:Transcript) | (:News)
   │      company = the document's owner (PRIMARY_FILER / HAS_TRANSCRIPT); news has only a tag (P4)
   ├─ HAS_PERIOD (0..1) ──────► (:DriverPeriod) start · end
   ├─ MAPS_TO_CONCEPT (0..1, metric only, not built) ─► (:Concept)
   └─ MAPS_TO_MEMBER (0..n) ──► (:Member)
(:Report | :Transcript | :News | :DailyCompanyMoveEvent) ─EXPLAINED_BY (verdict)─► (:DriverUpdate)   planned; P5, P7
(:Driver) ─SAME_AS─► (:Driver)        off for now
(:Driver) ─CONTINUES_AS─► (:Driver)   release 2 (declared renames)
Not stored: family (from the name) · a surprise's home fact (matched) · inherited XBRL line item (at read)
```

### 6b. One fact, end to end (the rules' worked example)

> "International revenue of $1.2 billion increased 0.5% versus last year." (Best Buy call, fiscal Q4 2026)

→ Driver `revenue` (metric) · slice `segment:international` · state `increased` · value 1,200 `m_usd` · change +0.5 `percent_yoy` · baseline `prior_year` (no number stated) · period = Best Buy's real fiscal Q4 2026 dates · the exact quote, with the transcript as source.

### 6c. Three vocabularies for one pipeline

| Rules (Categorized) | Notion Workflow | rough_design step | Old design / code |
|---|---|---|---|
| A source sends evidence (2.34, 8.9) | Channels / Update source | 1 Prepare | channel packet (built for fiscal.ai) |
| AI reader proposes facts *and* names, blind (1.14) | propose Driver | 2 Read + 3 Name | decomposer / A7 reader (not built) |
| Fill the fact's fields (§3–§4) | inside add DriverUpdate (U1–U3) | 4 Judge (JEV + code) | deterministic checks (built, dry run) |
| Same Driver or new? (2.40–2.47, 8.2) | ◇ Driver already exists? (2c) | 5 Match | admission kernel (not built) |
| Born with first fact (2.35); save (5.x, 8.14) | create Driver · U2a Saving | 6 Save | writer planner (writes blocked) |
| XBRL links (§6) | U2b | — not covered | concept linker (not built) |
| Reads (§7) | U2c | — not covered | read layer (not built) |
| Verdicts (A2) | S5 · Predictor/Learner | — not covered (Learner guesses only) | EXPLAINED_BY (not built) |
| — (new) | — | `caused_by` (Read → Judge → Save) | — |

- **Insight:** Notion homes = *where the rules live* (study map). rough_design → the Code Flow page = *what runs, in order, and who does it* (run map; now built). Each Code Flow step should list the homes it must satisfy, so the two maps stay tied — the page doesn't do that yet.
- **An order difference that matters:** Notion draws ◇ before the fields are filled; rough_design sets the type *before* matching. Matching needs the type, because `revenue` (metric) and `revenue_guidance` are different Drivers. Run order: type → full name → match.

---

## 7. The 19 homes — crux · why · open

*(n) = number of rules. The rule lists match the Notion "Rules here" lines.*

### System

**S1 · Ground rules (13)** — 1.12, 1.15, 1.16, 6.18, 6.20, 6.21, 8.1–8.7
- **Crux:** when unsure, keep separate · never delete or re-key · a missing link beats a wrong one · nothing reviews or fixes saved data (only release 2's rename checks switch links off) · AI = meaning, code = everything exact · proposer ≠ approver; the checker sees only the proposal + evidence · no person at runtime · smallest machinery · fail closed; confidence never permits a write · no meaning word-lists or thresholds unless an official standard or a frozen owner decision supplies them · fix the whole class.
- **Why:** a merged forecast and result can never be untangled (1.12); word patterns "pass our samples and misfire silently" (8.6: missed "₹500 crore" and "doubled").
- **⚠:** all AI judges come from one vendor; a wrong merge with no XBRL data has no tripwire — the biggest known risk.
- **Pressure:** JEV cutoffs need frozen owner values (8.6); "JEV alone decides causes" needs an 8.1/8.2 exception; the owner also bans word lists for causes.

**S2 · Purpose, sources & companies (10)** — 1.3, 1.4, 1.20, 1.21, 8.8–8.11, 9.4, 9.5
- **Crux:** the loop · sources: earnings reports, news (mostly macro), fiscal.ai; the predictor only reads · companies = official industry/sector eligibility (the count is an outcome, not a target) · quotes are exact source text · a source sends evidence only; if it sends names, IDs, fiscal periods, tags, units or computed numbers, the whole item is rejected · the reader sees the whole event · old Guidance data = evidence only · 8-K item numbers decide nothing · start with fiscal.ai only; each source is certified before going live.
- **Why:** services like RavenPack only list events; this system grades each cause against what the stock did (1.3).
- **Open:** P5 (release-1 text) · 8.10 vs reading in pieces · 8.9 assumes channels hand evidence to a core.

**S3 · Processing, timing & retries (5)** — 1.14, 8.14–8.16, 10.3
- **Crux:** no look-ahead: history runs see only what was public then · the reader proposes blind, then each proposal is checked against the whole current catalog · never show the realized return to whatever produces a fact or a verdict · five outcomes (written, merged, held, skipped, rejected); nothing vanishes · retry a hold only on a checkable trigger; a retry re-processes the whole event · when a metric Driver is born, search the company's earlier documents; search each new document for known Drivers · history work never starves live work.
- **Accepted hindsight:** history is matched against *today's* catalog (1.14).
- **Open:** P6 (fewer outcomes) · 10.3 service targets · live arrival untested (test data ends 2026-04-28).

**S4 · AI use & testing (4)** — 8.12, 8.13, 8.17, 8.18
- **Crux:** subscriptions only — no API billing, no switching providers, no silent fallback; any pay-per-use service needs its own owner approval · passing a test qualifies only that exact task + model + program + settings + input kind · <1% wrong whole facts at launch, with honest upper bounds (0 wrong in N ⇒ up to ~3/N) · go-live: fresh representative events, answer key locked before any AI call, graders qualified first, ~300 facts · judge on meaning, never on text matching (quote matching looked ~99% right; judged accuracy was ~29%).
- **⚠ (stale):** "one strong model per task, no cascades, votes or fallbacks" vs the owner's 2026-09-29 ruling "escalation to a generative model is allowed".
- **Open:** JEV in production (pay-per-use, another provider) · Luna (another provider) · cutoffs · test sets.

**S5 · Price-move explanations (10)** — 9.7, 10.1, A2.1–A2.8 · owner: on in release 1; the text still says off (P5)
- **Crux:** the Driver system never judges what moved a price; an approved producer submits verdicts, and the core only checks and stores them · verdict = a move target (a document, or a daily move event) → the fact that helps explain it; key = target + Driver + scope + producer · `stock_impact` long/short · `weightage` 0.1–1.0, an independent force, never a share · `confidence` 0–100 · shares are worked out when read · grade verdicts as a set · daily move event = one per company and trading day; a filing that day takes over · news is the source for macro facts; a daily move is never a source.
- **Open:** P3 (only significant moves; one macro fact may explain many companies' moves) · P7 (the Learner sees ACTUAL_RETURN) · 10.1 (move threshold, macro source, two independent causes) · with News in ③, release 1 has no source for macro facts.

### Driver

**1 · Driver record & relationships (17)** — 1.1, 1.2, 1.19, 2.1, 2.2, 2.38, 5.6, 6.13–6.17, 6.19, 9.6, 9.9, 9.10, 10.2
- **Crux:** the same cause keeps the same name across companies and years · a Driver is separate from its facts · Driver = name + type + frozen birth evidence (birth fact ID, exact quote, needed context; never an AI summary) · no status; never renamed, re-typed, re-keyed or deleted once it has facts · synonym links: none for now · declared renames ("continues as"): release 2 · no financial-classification field · no instant linking.
- **Why:** frozen evidence stops a Driver's meaning drifting "one small approval at a time" (2.1).
- **Open:** 10.2 (no fix for a mis-named or mis-typed Driver that has facts) · how the birth context is stored · overlap 2.2/2.38.

**2a · Fact type (17)** — 1.5–1.10, 2.19, 2.22–2.25, 2.27–2.31, 7.7
- **Crux:** persistence test: a standing level you can read again → metric, else action_event · a final `_guidance`/`_surprise` overrides it · forecast words → guidance · both framings may exist (`dividend` = action, `dividend_per_share` = metric) · fixed defaults for some bare names (1.8) · the locked wording is the meaning authority; a restatement adds no clause (1.9) · suffix: strip exactly one; admit only if the rest is a standing metric the source forecasts or compares · a bare name is a metric only with quoted proof, otherwise an action (with a warning); in live use, unclear → skip.
- **Why:** a false metric merges permanently; a false action fails safe (2.30). The four types were checked against all 1,282 catalog names (1.10).
- **Evidence:** JEV V6 97.3–97.6% (tuned); 99.6% on items the rules decide; study: 90.2% of real text fits cleanly.
- **Open:** 5th type `expectation` · V6's extra prompt clauses (1.9) · JEV §3.3 typing cases (stores opened in a period, "agreed to make available", dated pay rises, "expect to complete", "became subject to", "paid $1.4B to employees") · metric/action boundaries (fact_types) · overlaps 1.7/7.7, 2.19/4.2.

**2b · Name (16)** — 2.3, 2.5–2.18, 2.21
- **Crux:** the name holds the cause only (+ a stated "per X", a benchmark, a final suffix) · open vocabulary from the sources · all the specificity the evidence supports · format `a–z 0–9 _` · word order: thing → detail → metric · the familiar form unless a sibling or benchmark is stated · standard phrases stay whole (`ebitda`, `same_store_sales`) · name the signed measure (no "loss" Drivers) · one cause per name · the company's own parts → slice; outside actors → name (role test) · portions (`fee_earning`, systemwide) stay in the name · per-unit rules · measurement versions → tags · never-in-name list, with exceptions (`fed_rate`, `aws_outage`, `glp1_pressure`) · naming changes only by general principle, never by sector examples.
- **Why:** a closed vocabulary rejected ~82% of useful names (2.5); generic names merged three different demand stories (2.6).
- **⚠:** `restaurant_closures` (the cause) vs `restaurant_closure_impairment` (what was actually recorded) — the A7 example.
- **Open:** rough_design gives naming its own step and its own model.

**2c · Which name & family (12)** — 1.18, 2.4, 2.26, 2.32, 2.40–2.47
- **Crux:** family = the name minus one final suffix; nothing stored · one stored name = one meaning; no alias lists · family check (a gate): a new member must measure the same thing as every existing member, else it takes a more specific name or is skipped · a family's base must be a metric · identity = same object, same business scope, same mechanism (5 checks, evidence from both sides) · counts never decide · company-neutral · match against the whole current catalog, never filtered by company or industry · an unmatched fact is also tried against families missing that type · a surprise takes its home fact's base name · some pairs are always different; names that only share words (`brent_oil_price` vs `oil_price`) are never matched for now · a refusal is final.
- **⚠:** some wrong "same" calls can't be avoided; near-duplicates are accepted and never repaired.
- **Evidence:** JEV: no setting gave <1% wrong merges *and* <20% missed matches → use it as a veto only (cut 94% of different pairs, lost 3 of 73 same pairs; cutoff 0.29; with an unapproved extra sentence).
- **Open:** the 2.40 sentence (owner 2026-09-30: the same measure at two companies = one Driver) · who approves merges (a strong model; its error rate is untested) · a database unique-name rule (absent) · two names saved at the same moment.

**3 · Creating a Driver (7)** — 2.20, 2.33–2.37, 2.39
- **Crux:** create only if: no Driver has the same meaning, every naming rule passes, the nouns come from the source or the catalog, causal evidence exists, it is a reusable kind (not one instance), its meaning is unambiguous · one real fact is enough · drop boilerplate · storing a fact never depends on whether the stock moved · any authorized source may submit evidence, but only the core creates; Drivers proposed from prose wait until a duplicate check for wording-only Drivers exists · born complete, with its first proven fact · a catalog name is not a Driver · a bare-named Driver's first fact needs a readable state · submissions about the same event reach one identity.
- **⚠:** before text can create any Driver, two pieces must exist: the independent identity check and the wording-only duplicate check.
- **Open:** two creation routes (offline catalog vs live) · 2.33 boilerplate wording (fact_types) · overlap 2.34/6.11.

### DriverUpdate

**U1a · Record & evidence (10)** — 1.11, 1.13, 1.17, 3.1–3.3, 3.7, 3.9, 3.10, 3.12
- **Crux:** every fact needs a quote · store only what is stated (exact rescaling is fine; never vendor-calculated ratios) · evidence only from its own document; every stored number appears in its quote; an 8-K = the whole filing; 8-K tables count only as original tables · ID = document + Driver + scope; the extractor is never part of it · 24 fields; a per-type field matrix · only guidance may look at earlier facts · exactly one Driver link and one document link; the company comes from the document's owner, never from mentions.
- **Open:** P4 (a news story has a tag, not an owner) · `caused_by` · producer (P2).

**U1b · Period (12)** — 3.36–3.47
- **Crux:** a period = a real calendar window, not a label · guidance always needs its target period · actions get one only when stated · the filing type never says quarter vs year · exact ranges beat fiscal shorthand (52/53-week years) · vague horizons short/medium/long/undefined (never a quiet fallback) · one fiscal resolver; no fiscal-year end → fail · fill a missing end date only from matching evidence · dates from the filing beat cached windows · 8-K ↔ 10-Q/10-K pairing is exact and only routes the source · dates are write-once · `time_type` is always stated.
- **⚠:** stored fiscal windows can be wrong (Darden Q3: stored Dec 1–Feb 28; the filing says Nov 24–Feb 22).
- **Open:** "over time" = undefined? · separate publication / as-of / expected-event / maturity dates (fact_types).

**U1c · Slices & measurement tags (16)** — 3.13–3.27, 9.3
- **Crux:** slice = `kind:value`; kinds segment, product, geography, customer, channel, entity_ownership + `unknown` · a slice is a business population ("revenue from ___" makes sense) · a brand's kind comes from its axis or its role · keep every slice part · which XBRL axes are slices: decided offline from their members · a company's slice list = all members from its earlier 10-Q/10-K + values already used, cut at public time · order: reuse an exact value → a new grounded value → `unknown:value` → none · values join only on an exact `kind:value` match · eliminations: a fixed observed list · a stored slice never changes · never equate slices across companies · measurement tags: the exact qualifier words, sorted, never dropped, never merged when writing.
- **⚠:** an XBRL axis wrongly marked "not a slice" silently folds segment data into the company total (Agilent: 246 facts).
- **Open:** the filer's own legal entity = no slice? · airline groupings = segment? · a corporate customer group = customer or channel?

**U1d · States & amounts (18)** — 3.5, 3.6, 3.8, 3.28–3.35, 3.48–3.52, 9.1, 10.4
- **Crux:** a state list per type; good or bad news never decides a state · metric state table (the first matching row wins) · an action's state = its latest stage · 10 units · unit and scale proven inside the quote (widen the quote to a table heading; never search nearby text) · never infer a unit from a name or a number's size · value and comparison share `level_unit`; a change has its own unit · growth basis only when the quote establishes it, else `unknown` · signed values (a loss and a benefit are negative) · series unit · number shapes (point, range, floor, ceiling, numberless) · change and comparison only when stated · value-vs-change table (3.50: basis points = a change, a chosen reading) · sign check · comparison baselines · US dollars only.
- **Open:** physical units and other currencies · text values on metrics (9.8) · is a dash a zero? (10.4) · the sign of "used" amounts and bracketed expenses · `persists` vs `reported` · overlaps 3.50/7.8, 3.35/7.2.

**U2a · Saving (8)** — 3.4, 5.1–5.5, 5.7, 5.8
- **Crux:** after saving, identity, scope and the 10 value fields never change; an empty field may be filled by a compatible piece; other fields: last write wins, with a log; a blank never erases · combine pieces of one fact first (fill blanks only) · two values: compare the 10 value fields with the database as it stood *before* the batch (same / compatible / conflicting); conflicting → an extra fact with a tie-breaker; ambiguous → hold · an amendment is a new fact · save only if every check still holds at write time.
- **Open:** P1 (conflict-flag wording) · P2 (store the producer?) · P6 · `caused_by` entries would be add-only, unlike 5.5.

**U2b · Links to filing data (13)** — 3.11, 6.1–6.12 (+ A1, switched off)
- **Crux:** the exact company line item or nothing (a missing link fills itself in later; a wrong one does silent damage) · only base metrics link directly; guidance and surprise inherit at read; actions never link · GAAP-compatible tags only · never link events, macro causes, ratios, derived or non-GAAP figures (tax rates may link) · the same metric only; unsure → refuse · fixed refuse-only checks (cut wrong links from 42 to 1 on 274 companies) · candidates = the company's own consolidated items, cut at public time · 10-K/10-Q only · a member link needs axis + member + an exact tagged-fact match · XBRL never decides meaning; facts from tagged data are switched off (A1).
- **Evidence:** concept picks on 12 fresh companies: Luna xhigh 92.7% of correct links kept, 0 wrong after code checks; JEV + hand-written hints 95.0%, 4 wrong (all `ProfitLoss`); Haiku + verify + code 84.9%, 0 wrong; local Qwen 89.5%, 1 wrong.
- **Open:** which option · the `ProfitLoss` ruling · where a Driver's definition lives · members and axes untested · recall conflict (the rules say ~70%; an old verdict says 93.7%).

**U2c · Reading & comparing (10)** — 7.1–7.6, 7.8–7.11
- **Crux:** one history line = an exact match on company, Driver, type, slice, period, period kind, tags, series unit, time type (+ surprise kind) · an `unknown` series unit is never grouped · display order · same-day rank 8-K > transcript > 10-Q > 10-K > news, then the later timestamp · history reads see strictly before the as-of date; realized returns are never shown · "narrowed" is worked out when read · labels group by XBRL member only within one company · raw vs reconciled (release 2) · required views: raw, current, history, point-in-time, reconciled, cross-company/industry · every program reads through these views only.
- **Open:** mostly decided; the query and storage design is the owner's to make.

**U3a · Forecasts (12)** — 4.4–4.9, 4.18–4.21, 9.2, 9.8
- **Crux:** a stated movement is stored; otherwise `unknown`, and each read works it out by the midpoint rule against the previous winning value in the same series · a correction without business wording is never read as a raise or cut · value vs revision · `value_text` = a words-only forecast (≤200 characters, no numbers) · `conditions` (guidance only) · `company_confirmed` required; unclear who said it → skip · a withdrawal spreads only with an exact scope (the only fact the system writes on its own) · add only · only company-confirmed guidance is stored (9.2) · no text values on metrics, no conditions on actions (9.8).
- **⚠:** "costs to rise by more than $4B" is not the total fuel bill.
- **Open:** outside forecasts (`expectation` type) · `conditions` = assumptions only; causes → `caused_by`.

**U3b · Surprises (11)** — 4.1–4.3, 4.10–4.17
- **Crux:** what goes where (vs consensus or the company's own guidance = a surprise + its home fact; a new vs old own forecast = guidance movement; vs last year = a metric change) · one surprise Driver holds the 3 kinds; the kind is in the ID · `in_line` = inside or on a closed range, with no good/bad words · beat or miss = the meaning of the whole phrase; never "above = beat"; never from the sign · which direction is good needs a basis (capex, R&D, inventory, hiring and cash burn need the source's own framing) · every grounded surprise needs its home fact in the same event · an ungrounded "results beat" is held; a result surprise before its period ends is rejected · an expectation comparison is its own surprise fact · the surprise size is worked out when read.
- **Evidence:** JEV comparison kind 64/65; state 39/41; the type question can't separate a surprise from its home fact.
- **Open:** the company's own "exceeded our expectations" · a macro view vs consensus · computed surprises · macro surprises shared across companies.

---

## 8. How the pieces connect (chains)

1. **Identity chain — the dangerous one.** name (2b) → type and suffix (2a) → family (from the name) → match (2c) → the Driver inside every fact ID (3.1) → `caused_by` IDs resolved at save → history lines (7.1) → guidance movement (4.4) → surprise ↔ home fact (4.14) → verdict key (A2.2) → learning. One wrong merge poisons all of these, forever (6.20, 2.38, 10.2). **That is why 1.12 is "the one law", and why naming and matching deserve the strongest model.**
2. **Time chain.** public time → readers blind to later facts and to returns (1.14, A2.5) → slice list and XBRL candidates cut at public time (3.17, 6.7) → as-of reads (7.6) → P7 (the Learner sees the return).
3. **Evidence chain.** the whole document (1.17, 3.9) → exact quote (8.8) → every number inside the quote → unit/scale proof inside the quote (3.29) → 8-K tables only as original tables (1.17) → flattened text is a known risk (an A7 lead) → the Docling / "evidence of record" decision.
4. **Period chain.** fiscal-year end (3.41) → real window (3.36) → filing dates beat the cache (3.43, Darden) → the same window in the ID and the link (3.45) → history lines (7.1) → movement compares the same target period (4.4).
5. **Value chain.** unit (3.28–3.33) → series unit (3.35) → exact-equality grouping (7.2) → midpoint rule (4.4), in-line test (4.10), surprise size at read (4.17).
6. **Scope chain.** period · slices · tags · surprise kind · tie-breaker (3.2) → slice list from XBRL members (3.17) ← offline axis classification (3.16) ← eliminations list (3.21) → member links (6.9) → GAAP tags gate concept links (6.3).
7. **Write chain.** combine pieces (5.2) → compare the 10 value fields with the database before the batch (5.3) → tie-breaker or hold → save only if still valid (5.8) → one event at a time → the outcome recorded (8.14) → retry only on a trigger (8.15).
8. **Quality chain.** no repair after saving (6.20) → every check before saving must meet <1% (8.17) → independent checks (8.2) → qualified per task (8.13) → qualified graders → ~300 graded whole facts.

**Where the risk sits:** a wrong field value = one wrong fact. A wrong name, type or merge = a whole history wrong, permanently. Spend the effort (strong models, independent checks) where errors are permanent; let cheap judges and code fill the per-fact fields, failing closed to `unknown`.

---

## 9. Evidence collected since the rules froze (key numbers)

| Topic | Result | Caveat | Where |
|---|---|---|---|
| Old A7 (Sonnet fills 24 fields) | recall 74.6% / 70.3%, strict 43%, wrong accepts | 33 events | memory, STATUS |
| Fact-type fit (873 pieces) | 90.2% clean; filings 92.7%, calls 88.6%, news 82.0% | my labels + helpers | fact_types.md |
| Cause links in text | in ~15% of fact-bearing pieces (29% on calls) | cue-selected | fact_types.md |
| Outside forecasts | price targets in 48.3% of news stories; ~46% of stories are analyst items | screens | fact_types.md |
| Physical units | ≥1 physical-unit number in 13.1% of EX-99 exhibits, 44.2% of 10-K Business/Properties, 18.5% of prepared remarks | strict screens, not missing-fact rates | fact_types.md |
| JEV fact type | 99.6% on items the rules decide; V6 97.3–97.6% | silver keys, mostly 2 airlines, tuned | JEV §6.1 |
| JEV fields (raw) | metric state 92%; units ~97%; span 94%; baseline 98%; horizon 80% (96% after a ruling); slice kind 81% | different test sets | JEV §2 |
| JEV checking its own work | catches 2 of 32 of its own mistakes | — | JEV §6.5 |
| JEV identity | no setting <1% wrong AND <20% missed; as a veto: 94% of different pairs cut, 3/73 same lost | Sonnet-made keys | JEV §6.8 |
| XBRL concept pick (12 fresh companies) | Luna xhigh 92.7% / 0 wrong (with code); JEV + hints 95% / 4; Haiku + verify + code 84.9% / 0; Qwen 89.5% / 1 | one run each | JEV §6.9–6.10 |
| Cause links (JEV yes/no per pair) | 46/46 real links found, 0 false among 23 | 36 items, 1 labeller, 6 synthetic; offsets and part-of untested; an indirect cause counted as a cause | JEV §6.11 |
| Missed-fact screen (JEV tags) | 92–100% of facts caught on 240 fresh units, 31–41% of text flagged | blind spot: "explanation of a change" sentences | JEV §6.6 |
| Whole corpus | 33.1M units (sentences + table rows); JEV sweep $1.2K–4.5K; 2–7 days | extrapolated | JEV §6.7 |
| Docling | PDF route finds 271/273 Item headings (13 10-K/10-Q); HTML route finds 0 headings; ~25–30 days of CPU for the corpus | small sample | docling.md |
| XBRL definitions | 981/981 reports; 14.4% of entries have no documentation | no database writes | XBRL_Definitions.md |
| Document sizes | 10-Q ≈ 44k tokens, 10-K ≈ 108k (average); the local model takes 16–30k per call | characters ÷ 4 | rough_design |

---

## 9b. Docling for step 1 · Prepare (my tests, 2026-10-01; read-only; scripts + outputs in the session scratchpad `docling_x/`)

**Context:** Notion "1 · Prepare" (`3eca0a3f310681ffb36de687666c09f0`): A Get → B Convert (HTML text/tables; printed PDF for headings) → C Label (Part → Item → subheads) → D Cut → E Check. Scope: SEC reports only.

| # | Finding | Evidence | So what |
|---|---|---|---|
| D1 | **Items are already split in Neo4j**: 10-K 2,988/2,993 · 10-Q 7,297/7,301 · 8-K 29,591/29,672 have `HAS_SECTION` → `ExtractedSectionContent` (21 10-K Items, 11 10-Q Items, 8-K Items like ResultsofOperations…) | Cypher counts | The Part → Item map (the reason for the 25–30-day printed-PDF route) already exists |
| D2 | Stored text keeps paragraphs, but **tables are flattened** into one run of words (`##TABLE_START Name Age Positions Shantanu Narayen 59…`); 8-K exhibits are flat | sample + 831/3,000 sections have table markers | Docling's job = tables + exhibits, not Items |
| D3 | **HTML route speed (Docling 2.131, CPU):** 10-K 1.7–5.5 s · 10-Q 1.3–1.6 s · EX-99.1 0.2–0.9 s; mean 1.6 s (14 files) | `html_route_results.json` | Corpus ≈ 8–10 h on one core (vs 25–30 days PDF); trivially parallel |
| D4 | **0 of 14 files had any table header flagged** (SEC tables use `<td>`, not `<th>`); Docling's own triplet serializer then outputs garbage (`, 1 = . , 2 = .`); Markdown has empty spacer columns | `table_look.py` | Out-of-the-box LLM table text is unusable for SEC HTML |
| D5 | **4 structural rules fix it** (one value per real cell · glue `$ ( % )` to the number · header rows = rows above the first "label + number" row · drop empty columns): `Subscription and transaction fees (1) \| Three Months Ended September 30, / 2025 = $358,005`; `Beauty \| Volume = 3%` — right on 4 of 5 tables; the 5th was a table of contents (layout table) | `table_fix.py` (~40 lines) | Each number carries its row + column labels → kills A7's "column header never copied" failure class. Known gap: section rows above the first data row lose their prefix |
| D6 | **iXBRL tags sit on many 10-K/10-Q numbers:** 670–4,091 tagged numbers per filing, ~85–93% of them in tables; 28–134 note/policy **text blocks** per filing; EX-99.1 press releases: 0. **CORRECTED (raw-HTML recount, all 13 periodic filings, years and footnote marks excluded): median 67% (52–81%) of numeric table cells are tagged — my first "~90%" undercounted untagged cells; the other session's 51–81% / ~67% was right. Tables are all-or-nothing: tables with any tag have 98–100% of their numbers tagged; the untagged third sits in tables with no tag at all (MD&A/KPI tables, page numbers)** | `tag_share_raw.py` (supersedes `tagged_share.py`) | For tagged numbers, period/unit/scale/sign/segment are exact without AI (rule 3.29: "for XBRL-backed facts, the filing's own unit and scale data replaces quote evidence"); existing Route A code (`driver/relocation/inline_html.py`) already binds tags to visible text. Text blocks = exact boundaries of every financial-statement note |
| D7 | Docling **drops all iXBRL tags** (0 survive in its JSON) | grep of output | The tag link must come from Route A or a small pre-pass |
| D8 | **Docling text vs stored text:** using `orig` (not `text`), **91% of body paragraphs match the stored Items verbatim** (79% with `text`); `text` turns curly ’ into straight ' | SYNA 10-Q, 269 paragraphs | "Which text is the record?" may not need a choice: Docling for structure, stored text as the quote source; check the remaining 9% (table titles/cells, some note paragraphs) |
| D9 | **Most pieces fit whole** (chars ÷ 4): 8-K Items 7/64,473 > 16k tokens · EX-99.1 3.4% > 16k, 0.9% > 30k · EX-99.2 12% > 16k, 2.8% > 30k · 10-K Items 12.5% > 16k, 6.1% > 30k · 10-Q Items 10.2% > 16k, 2.8% > 30k | Cypher percentiles | Reading a whole Item at once (close to rule 8.10) works for ~90–99% of pieces; cut only the big 10-K/10-Q Items |
| D10 | **Picture-only exhibits:** EX-99.2 43/2,295 (1.9%) · EX-99.3 13/309 (4.2%) · EX-99.1 2/10,250 | regex scan of the exhibit cache | Small recall gap (slide decks); Docling OCR (RapidOCR; `ocrmac` on the Mac) + `fetch_images`/`source_uri`/`headers` can read them |
| D11 | Caches: **1,769** main 10-K/10-Q HTML (4.3 GB) **and 13,181 exhibits** (5.9 GB; 10,250 EX-99.1) | `ls` | Notion "A · Get" mentions only the 1,769 |
| D12 | Installed extras: 35 input formats incl. `audio`/`video` (Whisper incl. **MLX** builds for the Mac), `convert(url, headers=…)` (SEC User-Agent), `convert_string`, `TreeChunkExpander` / `PageChunkExpander` (expand a chunk to whole items = the "expand once" window), `LineBasedTokenChunker`, `HuggingFaceTokenizer` / `OpenAITokenizer` (exact token counts), `DocumentProfiler` (corpus stats), perf knobs `doc_batch_concurrency`, `page_batch_size` | introspection of the 2.131 venv | See the summary to the owner |
| D13 | Docling has **no** heading inference for HTML (no style-based option) and no SEC-specific code | `HTMLBackendOptions` fields; grep | Sub-headings inside big Items need another source |
| D14 | **Bold-line rule works:** marking short blocks whose visible text is all bold as `<h3>` (in memory, before Docling) gave 133 headings and 590 paragraphs nested under them (0 before) on the SYNA 10-Q. Noise: cover-page lines and repeated "COMPANY AND SUBSIDIARIES" banners | `bold_headings.py` (one filing) | A cheap, style-only route to sub-headings and heading paths without the PDF route. Also run on ADM 10-K (335 headings, 1,773 nested paragraphs; noisy cover/banners) and 2 press releases: Amgen → "Product Sales Performance · Oncology · … · 2024 Guidance · Cash Flow and Balance Sheet"; Paychex → "Business Highlights · Financial Position and Liquidity · Business Outlook · Non-GAAP Financial Measures" — exactly the context a reader needs |
| D16 | **Table fix robustness:** on all 148 numeric tables of 6 files, 135 (91%) came out with every number labeled on the first try; misses = tables of contents + one header shape (a year row whose first cell holds a label, e.g. "Three Months Ended March 31, \| 2023") — fixable with one more structural rule | `table_fix_eval.py` (crude check: "most values have a column label", not verified correct) | Good enough to pilot; correctness still needs a graded sample |
| D17 | **Size of the same tables (characters ≈ 4 per token):** Docling Markdown 68k–142k · DocTags 28k–59k · triplet lines ("row \| column = value") 30k–57k · **compact clean table 10k–13k** · today's flat words ~8k–9k (structure lost). Compact = the 4 rules + rule 5 "columns with the identical header path are one column", printed with headers once and one line per row: `\| Total revenue \| 395,741 \| 358,450 \|` under `Three Months Ended September 30, / 2025 \| … / 2024` | 3 files, 25 tables | Structure for ~1.2–1.5× today's size; Docling's own Markdown would cost 7–12× more reading |
| D15 | **Docling quirk:** adjacent styled spans get a space inserted (`<span>PA</span><span>RT I` → "PA RT I"), in `orig` too. **0 of 22,791 numeric table cells** affected | raw HTML + regex over 14 files | Exact quotes should come from the stored text (or raw HTML), with Docling used for structure |

### 9c. Owner's 3 questions on Prepare (2026-10-01) — my answers (the other Claude session answered the same; see the shared log)

- **Q1 Docling best?** For SEC HTML: not as-is. It loses exact characters (table cells normalized with no `orig`, "—" → "-" per its code; spaces inserted between styled spans), the iXBRL tags, and any link back to the source (no ids/offsets for HTML). Headers + headings need our rules anyway. For images/PDFs it is the best free umbrella (OCR, Heron layout trained partly on financial reports, VLM presets incl. MinerU). **Where I differ from the other session:** the bake-off must include a thin converter of our own (lxml; parts exist in `driver/relocation/`), not only sec-parser / doc2dict / edgartools — the deciding tests (exact characters, tags kept, source links) are where generic tools fail. Grade tables automatically with the tags (tagged tables = free answer key for number ↔ column/period).
- **Assumption (transcripts/news fine):** yes. Another session checked 50k news bodies: plain text, 0 tables, 9% empty. Transcripts already split (prepared remarks + Q&A). Note: no new transcripts since the subscription lapsed (May 2026).
- **Q2 every document/exhibit/image:** one shared output format; HTML → converter; text → split; images → OCR/vision models only (marked "read from image"); rare PDFs → Docling; XBRL already in DB. Convert everything (cheap), read selectively (EX-10 ≈ 1.5B chars; rules 8.10/1.17 say whole event → owner call). **New ruling needed:** may text read from images count as evidence? Rule 1.17 says a converted copy of an 8-K table does not.
- **Q3 at ingestion:** agree. Convert once on arrival, store beside the original (additive, versioned), backfill once (~10 h one core); all readers use it (Drivers, predictor, guidance). event-trader (ingestion) is currently down/Polygon-gated. To-do right after the converter passes its tests, not at the very end.

### 9d. Review of `DriversFinal/runningIdeas.md` (other session's Prepare proposal P1–P19, T1–T3, D1–D5), 2026-10-01

New evidence gathered for it (read-only): `driver/` is an empty new build (old code in `driver_reference/`, commit 722a93166) → there is no writer yet · stored DRI EX-99.1 (0000940944-26-000005) contains "restaurant closures3" and "10.674" (footnote digits glued into words and numbers) · the earnings predictor reads `ExhibitContent.content` for EX-99 (`scripts/earnings/builders/eight_k_packet.py:51–53`) · fully tagged tables = 4–18% of 10-K/10-Q text but 523–2,380 numeric cells per filing · 7.1% of paragraphs repeat across the exhibits of one filing (99 of 300 multi-exhibit filings) · Docling JSON = 2–12× the HTML (10-K 10–44 MB) · this machine = minisforum = control-plane node; worker minisforum2 (16 cores) idle per the cluster map.

My verdict: right shape (code-only, once, DB Items, labelled tables, tags, tag answer key, ingestion), not perfect. Must change: (1) D4/P13/P16/T3 → record = original + frozen prepared file; drop the stored-text mapping; (2) T1 → pass/fail gates (exact characters, footnotes apart from numbers, exact cell text, tags, pointers) + own thin converter arm + ≥300 hand cells + ~30 press releases graded via the later 10-Q's tags; (3) P11/P12/P17 → freeze blocks, build pieces at read time, pack small Items, neighbours only at split edges, compact JSON; (4) P19 → right after T2 (predictor benefits now). Should: EX-99.1 first; tags on prose + flag tagged tables (D7: XBRL route A1); P15 checks period/scale/sign/unit on all filings; exact cells + unlabelled fallback; dedupe repeated paragraphs; one Item-placement method; grade subheadings vs existing PDF headings; run the backfill on the worker node; T4 reader pilot. New decisions D6 (table quote), D7 (tagged tables via XBRL), D8 (601 XML forms).

### 9e. Merge of the three reviews of runningIdeas.md (bot 1 = me, bots 2 and 3 = others), 2026-10-01

Verified to settle disputes (read-only): news cap is real (`redisDB/NewsProcessor.py:99`, `max_words=3000`, also NFKC + spacing changes) but only 2 of 60,000 stored bodies hit it (p99 607 words) · DB `exhibits` holds only EX-99 (23,286) and EX-10 (15,765) → full file list needs each filing's EDGAR index · stored Items come from the paid sec-api ExtractorApi (`redisDB/ReportProcessor.py:9,32,40,101`, `get_section(url, id, "text")`) — also the source of flattened tables and glued footnotes · my table score re-scored strictly: 134/148 tables had every value labeled (91%), 95.1% of values labeled; correctness untested.

Merged result: Must = (1) evidence = originals + frozen prepared file, labels outside quotes, stored text only a compatibility check; (2) inventory everything, unread = "not read", never "no facts"; (3) structure from the original, DB Items as a cross-check (my "one method" withdrawn); (4) blocks + full read budget (instructions, context, answer space) + referenced notes; (5) test meaning (gates → associations → fresh filings → fixed-reader facts/causes/tokens); (6) one function, measured targets, live before backfill, ingestion right after tests, predictor's 8-K packet as first user. Should = EX-99.1 first; tags on prose; dedupe; subheadings vs PDF key; news/transcripts validated not converted. Decisions D6–D11 (table quote, tagged tables via XBRL, XML forms, images + OCR evidence, rule 8.10, drop sec-api extractor later).
- **D11 clarified (owner pushback 2026-10-01: "that's the one that has a WebSocket… how else will we do it?"):** the pipeline uses 4 sec-api parts — Stream/WebSocket (`secReports/sec_websocket.py`, new filings in real time), QueryApi (`secReports/sec_restAPI.py`, search/backfill), ExtractorApi (`redisDB/ReportProcessor.py`, Items as text), XbrlApi (same file, XBRL JSON). D11 means only the **ExtractorApi**; keep the stream, QueryApi and XbrlApi. Free fallback for the stream if ever needed: poll SEC's own latest-filings feed / per-company submissions JSON within 10 requests per second (≈ a minute's delay vs near-instant).
- **The three links (read 2026-10-01, docs + READMEs, no installs):** sec-parser 0.42.0 = NO (README: "This repository is no longer maintained"; last release 2023-11-29, beta; tables kept whole, not cell-parsed; nothing on tags/pointers). eventual.ai blog = NO as a tool (Datamule + Teraflop + Eventual built a plain-text dataset: 8M filings, 590 GB, 43B tokens, <24 h on 12 cores, ≈ $1.10; plain text = flattened tables, no tags) — but its parser **doc2dict** is worth a test slot (claims ~500 pages/s single-threaded HTML; table clean-up options: remove empty columns, detect fake tables, footnotes; "early stage"; Items via regex mapping dicts; exactness/tags unknown). edgartools = PARTLY YES (actively maintained, MIT, free; 10-K/10-Q/8-K Items + LLM-ready text; could replace the paid sec-api Extractor; exact text, pointers and tags unknown; fetches from SEC with an email identity) — keep in the test.
- **edgartools vs edgar.tools (owner asked "isn't that also paid?", 2026-10-01):** two products, same maintainer. The `edgartools` Python library = MIT, free, no key (only the email SEC requires in each request). `edgar.tools` / app.edgar.tools = a hosted web app + API with plans Free ($0, 100 API calls/day), Professional $24.99/mo, Analyst $79.99/mo, Enterprise (search result; the pricing page blocks automated reading, HTTP 403). We would only use the free library.

### 9f. Validation of runningIdeas.md v2 (2026-10-01, 169 lines; read-only checks)

- **Verified exactly:** F1 counts + sec-api source (key is *set* in .env; validity untested) · F2 (42,023 HTML / 601 XML / 9 missing; only EX-99/EX-10 listed) · F3 Darden split ("…$10.67" | "4" | ", including:"; raised `<font … top:-3.85pt>`) · F5 (median 67%; all-or-nothing; prose 26–649; text blocks 28–134) · F6 · F8 · F11 (earnings 8-K 7.04% avg / 4.77 median; 10-Q 4.78%; 10-K 3.71%) · node roles (minisforum control-plane, minisforum2 worker) · D12 (example.com placeholders) · D7 quote in A1 · rules 1.17, 8.8, 8.14, 8.16 · sec2md claims (PyPI 0.1.23, 2026-03-15, MIT, Alpha: element IDs → DOM nodes, iXBRL concepts, images, 10-K/10-Q/8-K Items) · rough.md exists.
- **Off:** F3 range "0.2–1.9 s" (3 files) → 0.2–5.5 s, mean 1.6 s (14 files) · F9 "32 10-Ks say MD&A is shown in Exhibit 13" → 57 tiny 10-K MD&A sections, 32 point elsewhere (appendix / annual report / incorporated by reference); only 1 (Carnival) names Exhibit 13; only 6 10-Ks mention Exhibit 13 anywhere · P21 numbers: my sample gives 12.1% of paragraphs in 2+ documents, 7.1% later repeats (= saving if read once) vs the file's 7.7% / ~4% · review-log row "A7 used a Best Buy 10-Q table" is half-right: A7's pilot #062 was Darden's 8-K press release.
- **New fact:** live ingestion is off — `event-trader` deployment in namespace processing is 0/0; report-enricher, edge-writer, xbrl-worker-heavy run; trade-ready crons complete.
- **My verdict:** agree with the big direction. Changes: F9 wording + P6 follow "incorporated by reference" to where the text lives · T1 drop sec-parser, gate-screen first, ≥ half press releases, score output size · D7 keep ❌ but T4 measures reader tokens on tagged tables · P8 link footnote markers to their footnote text · add "live ingestion off" fact · small: F1 "set", F3 range, F7 NFKC + news/transcripts record = stored text, P21 one measure, A7 row, T7 image sample, links (sec-parser out, doc2dict repo).

---

### 9g. rough.md (3 reviews of v2) checked against runningIdeas.md v3 (other session, 12:54), 2026-10-01; read-only

- **v3 already holds every rough.md point** (bots 1–3, ~38 points). Only gap: "retain raw news/transcripts before cleaning" sits in the review log, not in a P-item.
- **v3's new numbers reproduce:** F9 query = 32 (1 names Exhibit 13 / 22 "annual report" / 3 no exhibit) · F12 = 204 = 181 EX-99 in 120 filings + 23 EX-10 in 10 · F15 PyPI (Docling 92 releases in 12 months, last 2026-10-01, Production/Stable; edgartools 158, 2026-09-26, Beta; sec2md 22, 2026-03-15, Alpha; doc2dict 13, 2026-02-03; sec-parser 0, last 2024-06-09) · 13D/A PDF-only exhibits real (0001193125-26-167598: three PDFs, no HTML) · AMG index: official `amgq12023ex991.htm` + `courtesy.pdf`, both typed EX-99.1; DB map kept the PDF · Docling = LF AI & Data project since May 2025 · data.sec.gov submissions API: "typical processing delay of less than a second", no key.
- **NEW 1 — our exhibit cleaner deletes text.** `redisDB/ReportProcessor.py::_download_exhibit` runs `re.sub(r'<[^>]*>', ' ')` AFTER `inscriptis.get_text` has decoded `&lt;` → deletes from any "<" ("<1%", "<(100%)") to the next ">". Cached originals (13,181): 308 lose text, 76 lose >10%, 10 lose >50%, 1.29M non-space chars; all 74 filings losing >10% are earnings 8-Ks (Item 2.02, 38 companies). Coty 0001024305-25-000015: stored 23,502 chars vs ~100,900 in the original (≈77% gone); live DB confirms (kept phrase present, deleted phrase absent). Scripts: session scratchpad `docling_x/lt_gt_loss.py`, `lt_gt_share.py`, `lt_gt_probe.py`, rows `lt_gt_rows.json`. Same regex in `_extract_secondary_filing_content` (6-K, 13D…). News path (BeautifulSoup first) is not affected.
- **NEW 2 — every stored exhibit is one line:** 0 of 38,946 ExhibitContent contain a line break (sec-api sections: 19,958 of 20,000 sampled do).
- **NEW 3 — one root cause for F2/F9/F12:** `secReports/sec_schemas.py:192 _get_exhibits` = dict keyed by type, only types starting 'EX-10.'/'EX-99.' → EX-13 never stored (IBM 0000051143-24-000012: EX-13 = 4.7 MB iXBRL annual report with MD&A) and a later same-type file overwrites the earlier one (courtesy PDF over official HTML).
- **NEW 4 — PDF bytes by form:** EX-99: 8-K 41 exhibits / 27 filings (all Item 2.02) · 13D/A 114/82 · 13D 26/11; EX-10: 10-Q 16/5 · 8-K 3/2 · 13D/A 3/2 · 10-K 1/1.
- **NEW 5 — "35–60%" is mis-attributed:** measured on transcripts (47.2%) and news (44.4%), not 8-Ks (`WIP/UniversalLocator_Design_2026-07-18.md:340`). July M3 census (`WIP/UniversalLocator_ReviewRecord_2026-07-18.md` ~3945–3960), 40 8-K facts: money 28/28 had later same-value tag candidates (identity unproven), decimals 0/10, counts 0/2. Rules line 805 repeats the wrong attribution (separate fix).
- **NEW 6:** "38 PDF exhibits" (bot 3) = the July locator sample (ReviewRecord:3300; 12,182 HTML + 38 PDF in 9,788 events). DB-wide = 204.
- **NEW 7 — transcripts:** `form_qa_pairs` drops OPERATOR segments, UNKNOWN-role segments (no else branch) and executive answers before the first analyst; full text is stored only as a fallback when there are no Q&A pairs. Speaker roles come from an OpenAI model.
- **NEW 8 — news originals may be re-fetchable:** `BENZINGANEWS_API_KEY` is set and the repo has a historical fetch tool (bz-news-api → `pit_fetch.py`); untested, so "stored news = only copy" is unproven.
- **NEW 9:** 683 of 10,995 earnings 8-Ks have no stored exhibit; 2 sampled (CVS 0000064803-23-000003, Southwest 0000092380-23-000004) truly have none — results sit in the 8-K body (+ a graphic).
- **NEW 10:** Docling's PDF route silently drops table cells it can't place (AES 10-K log: "3 of 173 pdf cells … dropped"). PDF timings come from the 2026-09-30 scale run (AES 10-K, 266 pages, 284.7 s); no results file saved in DriversFinal.
- **Own correction:** my bot-1 "score output size" was weak — stored JSON size is storage only; priority ③ is reader tokens.
- Suggestions given in chat (this turn); runningIdeas.md not changed.

## 10. rough_design vs the rules

| Step | Who | Homes | Needs from the owner (rules it bends) |
|---|---|---|---|
| 1 Prepare | code + Docling | S2, U1a | 8.10 whole event → blocks + neighbours + referenced sections · evidence of record: stored text or Docling output (1.17, 8.8) |
| 2 Read | cheapest approved model | S2, S3, U1a, U1c, U3b | wording: the rules' reader also names · who splits mixed quotes (a rule is needed) |
| 3 Name | one smart model, blind | 2b | naming before JEV is a proposal (JEV did better *with* a name: 96.4% vs 94.2%) |
| 4 Judge | JEV + code | 2a, U1b–U1d, U3a–U3b | 8.12 (pay-per-use, another provider) · 8.13 · 8.5/8.6 cutoffs · 1.9 (V6 clauses) · 3.16 (slice kind) · S4 escalation |
| 5 Match | code shortlist + blind call; JEV veto only | 2c | 2.40 sentence · veto cutoff (8.6) · database unique-name rule |
| 6 Save | code | U2a, 3 | `caused_by` storage (24-field writer; 5.5) · hold and re-match if the catalog changed since matching (5.8, 8.15) |
| Causes | reader proposes, JEV checks | new | where `caused_by` lives · offsets / part-of / indirect · who decides (§11 T8) |
| Safety nets | JEV | S3, S4 | re-reads vs Phase 6 escalation limits |
| **Not covered** | — | U2b, U2c, S5 | XBRL linking, reads and verdicts are outside rough_design |

---

## 11. Tensions and contradictions (my analysis; nothing decided)

- **T1 · Release scope is out of date in the rules.** Rules: release 1 = fiscal.ai only; verdicts off (9.5, 1.4, 9.7, the Start-here table). Owner: ① = Fiscal AI + Predictor/Learner (D20) and price moves on (2026-09-29, P5); on 2026-09-30, "the entire design, not release 1 vs 2". The release lines need one rewrite.
- **T2 · Two architectures side by side.** Notion main chart: channels create; Filings & Transcripts only update ("filings never create Drivers", D32); D39 owner idea: filings are searched only for known Drivers. rough_design + Code Flow: every filing, call and story is read blind, and Match decides reuse or create. The rules allow both reading modes (1.14 blind proposal; 8.16 a targeted search that may name a Driver). **Owner's latest words (2026-10-01): "creating these drivers from all the financial text, and updating those drivers — we should be able to do both"** → leans to one flow; the main chart and the Filings & Transcripts page still say the opposite (flagged on the Code Flow page, owner to decide).
- **T3 · Two creation routes in the rules, one in the designs.** An offline catalog built and tested before go-live (2.30 "in live use", 2.36, 1.21, 8.17 "go-live bar for the catalog"; Fiscal AI page: "creates once from its KPIs") vs live creation (10.2). Notion and rough_design show only live creation.
- **T4 · Whole-event reading (8.10) vs pieces.** rough_design reads blocks with neighbours (Route D is the precedent); the local model takes 16–30k tokens, while a 10-K averages ~108k. 8.10 says the context is "never shortened".
- **T5 · Evidence of record.** Quotes must be exact source text (8.8); 8-K tables count only as original tables (1.17); 8-K exhibit text in Neo4j is flat (no line breaks). Docling gives structure, but it is a derived copy.
- **T6 · JEV vs the AI rules.** Pay-per-use and another provider (8.12) · qualified per task (8.13) · confidence never permits a write; any cutoff needs a frozen owner value (8.5, 8.6) · V6 adds prompt clauses (1.9) · independence (8.2). Luna is another provider too. The Phase 6 pool already lists Luna, so I read "no switching providers" as "no failover to another provider", not "one vendor only". Needs an owner ruling.
- **T7 · S4's "no cascades, votes or fallbacks"** vs the owner's 2026-09-29 ruling (escalation allowed), Phase 6 escalation, rough_design (low confidence → stronger model) and the XBRL options where two models must agree.
- **T8 · Who decides a cause link.** A: JEV alone + a sample check (cheapest; needs an 8.1/8.2 exception; the other session recommended A on 2026-10-01) vs B: the reader proposes, JEV confirms (rough_design's main path; fits the rules). Undecided.
- **T9 · `caused_by` has no home.** The writer stores exactly 24 fields; the entries would be add-only, but 5.5 makes other fields last-write-wins; it is not part of identity (3.1). Also, old GuidanceUpdate `conditions` mix assumptions and causes (4,413 of 8,432 filled).
- **T10 · 3.16 vs JEV picking slice kinds.** 3.16 ("no AI judges a slice's kind at runtime") sits under XBRL axes; 3.18 lets the AI pick a kind "when the kind is clear from the prose". My read: no conflict for prose slices. To confirm with the owner.
- **T11 · A fifth type.** `expectation` (fact_types) vs the locked four (1.5, 1.9, 1.10). 9.2 bars outside forecasts *as company guidance* and asks for their own design — a separate type may satisfy that.
- **T12 · Units and currencies.** 10 units + US dollars only (3.28, 9.1) vs physical units in 13–44% of some document kinds and the ~100% aim.
- **T13 · Qualitative metrics have no value field.** "Metric" includes sentiment, weather, policy in force, but 9.8 bans text values on metrics; only the state + quote carry them.
- **T14 · News design vs 2.33 and learning.** The News page reads only extraordinary-move days. 2.33 says storing never depends on whether the stock moved. For "learn what matters", Drivers that occurred *without* moving the stock would be missing (selection bias). Plus P4 (a story has a tag, not an owner).
- **T15 · S5 on in release 1, News in ③.** News is the only source of macro facts (A2.8), so release-1 macro verdicts have no source.
- **T16 · The Learner.** It sees ACTUAL_RETURN (P7), but verdict producers must be blind (1.14, A2.5). On 2026-09-30 it was also given cause-guessing (stored separately, as guesses). As a "channel" it clashes with 1.4 (the predictor only reads). Q5 is open.
- **T17 · 2.40 wording vs the 2.42 ruling.** "Same business population and ownership scope" makes judges call different companies different; the owner (2026-09-30): the same measure at two companies is one Driver. The clarifying sentence is not in the rules.
- **T18 · Rules from the channel era.** 8.9 (what a source may send), 8.16 (history and update searches), 3.44 (8-K pairing routes a source) and 1.13's vendor-ratio line come from the channel model. In a read-everything, time-ordered design some may be unnecessary (H2, H6).
- **T19 · Hindsight.** 1.14 accepts matching history against *today's* catalog. A time-ordered single pass (rough_design) matches against the catalog *as it grew*, which is closer to "what the system knew then". Which is wanted for backtests?
- **T20 · The hardest number.** <1% wrong *whole* facts, while each fact has ~10–15 judged parts. Per-field scores (≈80–99.6% raw) come from different test sets and can't be multiplied; whole-fact accuracy is unmeasured.
- **T21 · The owner's goals pull apart.** ~100% recall (read everything + safety nets) costs money and time; least code vs code for exactness; the owner dislikes code that needs exhaustive lists (8.6), yet exactness needs code.
- **T23 · "Never re-read the same text" (priority ③) vs re-reads the rules and rough_design require.** Rules: a retry re-processes the whole event (8.15); a missing surprise home fact means the whole event is read again (4.15); a new metric Driver triggers a search of the company's earlier documents (8.16). rough_design: the missed-fact net sends tagged-but-empty sentences to a stronger blind read; a vague "see above" gets one extra reader call; low confidence escalates to a stronger model. Each needs either an exception or a redesign (e.g. read once with enough context, then only JEV-style checks on already-read text).
- **T24 · "Prediction first" (priority ①) is a new yardstick the rules never used.** The rules aim for complete, faithful facts (2.33: store every real fact, whether or not it moved the stock). Priority ① asks how much each piece helps explain moves → learn → predict. Not a contradiction, but it can cut scope: features with no clear path to prediction (some fields, release-2 renames, extra dates) can wait.
- **T22 · Small stale bits.** The picture legend in Categorized says "see the top of this file" (meant Simplified's header); "folded Part A2" pointers; JEV.md still names Simplified as the rules file; the 8 overlap pairs.

---

## 12. Open decisions register (deduplicated)

*Grouped by theme. "T" = tension above. About 50 items; §13 H11 names the ~6 that decide most of the rest.*

| # | Decision | Rules | From |
|---|---|---|---|
| **A** | **Architecture & scope** | | |
| A1 | One picture: channels + update-only filings, or read every document blind and let Match decide (T2). Owner leaning (2026-10-01): one flow, both uses | 2.34, 8.16, 1.14 | Notion D28/D32/D39 (R4) vs rough_design / Code Flow |
| A6 | Re-reads vs priority ③ "never re-read the same text" (T23) | 8.15, 4.15, 8.16 | Code Flow priorities |
| A2 | Offline catalog first, live only, or both (T3) | 2.30, 2.36, 1.21, 8.17, 10.2 | rules |
| A3 | Release lines (T1) | 9.5, 1.4, 9.7, P5 | owner D20; 2026-09-29/30 |
| A4 | The role of fiscal.ai, the Guidance pipeline, News and the Learner in that picture | 1.4, 9.5, A2.8 | Notion box pages; Q5 |
| A5 | News ownership (P4) and selecting news by price moves (T14) | 3.9, 2.33 | P4; News page |
| **B** | **Reading** | | |
| B1 | Whole event (8.10), or blocks + neighbours + referenced sections | 8.10, 8.9 | rough_design |
| B2 | Evidence of record: stored text or Docling output; 8-K tables | 1.17, 8.8 | rough_design; docling.md |
| B3 | Mixed quotes: the reader splits them (a rule to write) | 2.34, 4.1 | JEV §3.2 #4 |
| B4 | Boilerplate vs fact boundary (2.33 clarification) | 2.33 | fact_types |
| B5 | Is a dash in a table a zero? | 10.4 | rules |
| B6 | Reader vs namer wording | glossary | rough_design |
| **C** | **Types** | | |
| C1 | Add `expectation` (outside forecasts, with "whose") | 1.5–1.10, 9.2 | fact_types |
| C2 | Approve V6's prompt clauses, or keep the locked wording | 1.9 | JEV §3.2 #2 |
| C3 | Typing cases: stores opened; "agreed to make available"; dated pay rises; splitting a dividend sentence; "expect to complete"; "became subject to"; "paid $1.4B" | 1.5, 7.7 | JEV §3.3 |
| C4 | Metric/action and forecast/action boundaries; a company predicting someone else's decision | 1.5, 1.8 | fact_types |
| **D** | **Names & identity** | | |
| D1 | 2.40 clarifying sentence (the same measure across companies) | 2.40, 2.42 | owner 2026-09-30 |
| D2 | Who approves merges; the JEV veto cutoff (0.29) | 8.2, 8.6 | JEV §6.8 |
| D3 | Database unique-name rule + same-moment race | 2.39, 5.8 | rough_design |
| D4 | A fix for a mis-named or mis-typed Driver that has facts | 10.2, 2.38 | rules |
| D5 | A regional slice vs the consolidated figure (identity) | 2.40 | JEV §3.2 #7 |
| **E** | **Fact fields** | | |
| E1 | Units: physical units, other currencies (UTR, ISO 4217) | 3.28, 9.1 | fact_types |
| E2 | Text values on metrics; qualifiers (denials, participants) | 9.8 | fact_types |
| E3 | Sign of "used" amounts and bracketed expenses | 3.34 | JEV §3.3 |
| E4 | `time_type` of actions with no value; `persists` vs `reported` | 3.47, 3.6 | JEV §3.3 |
| E5 | "Over time" = an undefined horizon | 3.40 | JEV §3.3 |
| E6 | The filer's own entity = no slice; airline groupings = segment; corporate customer group? | 3.13–3.15 | JEV §3.3 |
| E7 | 3.50 basis-point reading (value vs change) | 3.50 | rules |
| E8 | Extra dates (publication, as-of, expected event, maturity) | 3.36 | fact_types |
| **F** | **Forecasts & surprises** | | |
| F1 | The company's own "exceeded our expectations" → consensus? | 3.52 | JEV §3.3 |
| F2 | A macro view vs consensus; macro surprises shared across companies | 4.1–4.3 | JEV §3.3; fact_types |
| F3 | Computed surprises (a separate design) | 1.13, 4.17 | fact_types |
| **G** | **Causes** | | |
| G1 | Adopt `caused_by` at all; where it is stored | 3.1, 5.2–5.5, 5.8 | fact_types; rough_design |
| G2 | Offsets, part-of, indirect causes: links or not | — | JEV §6.11 |
| G3 | Who decides: JEV alone (A) or reader + JEV (B) | 8.1, 8.2 | 2026-10-01 |
| G4 | Window (3 → 5 sentences); references ("Note 5", "above") | 8.10 | fact_types |
| G5 | The Learner's guessed causes: where, how marked | 1.14 | fact_types |
| **H** | **Saving** | | |
| H1 | Fewer outcomes (P6) | 8.14 | owner Q8 |
| H2 | Conflict-flag wording (P1); store the producer? (P2) | 3.4, 5.3 | parking list |
| **I** | **XBRL links** | | |
| I1 | Concept-pick option (Haiku / Luna / JEV / two must agree) | 6.1–6.6, 8.12 | JEV §6.9 |
| I2 | `ProfitLoss` (A: `NetIncomeLoss` only) | 6.5, 6.6 | JEV §6.9 |
| I3 | A Driver-side definition (instead of hand-written hints) | 2.1, 1.9 | JEV §6.9 |
| **J** | **AI use & testing** | | |
| J1 | JEV in production; the meaning of "no switching providers" (Luna) | 8.12 | T6 |
| J2 | S4 wording vs the escalation ruling | S4 ⚠ | JEV §3.1 |
| J3 | Frozen cutoffs (confidence, pair yes/no, tag weights, veto) | 8.5, 8.6 | rough_design |
| J4 | Code-heavy / JEV-heavy / mixed (mixed recommended) | 8.1 | JEV §8 |
| J5 | Models per step from the Phase 6 pool; is a cheap reader enough? | 8.12, 8.13 | rough_design |
| J6 | Pilot: 3 arms, ~300 graded whole facts, key locked first | 8.17 | rough_design |
| **K** | **Price moves** | | |
| K1 | Rewrite 9.7 (P5) | 9.7 | owner 2026-09-29 |
| K2 | Learner blindness (P7) | 1.14, A2.5 | parking list |
| K3 | Significant moves only; one macro fact, many companies (P3) | A2.7 | parking list |
| K4 | Move threshold; macro source; two independent causes (10.1) | 10.1 | rules |
| **L** | **Running** | | |
| L1 | Service targets (10.3) | 10.3 | rules |
| L2 | Re-reads (missed-fact net, vague references) vs Phase 6 limits | 8.12, 8.15 | rough_design |
| **M** | **Process** | | |
| M1 | Code Flow page: **built** 2026-10-01. Still open: who edits it from now on (Claude or Codex) | — | 2026-10-01 |
| M2 | What "green" means: Code Flow's legend now says "agreed and tested"; the Workflow chart and the 19 homes still don't say (Q1) | — | Q1; Codex note §15 |
| M3 | Merge the 8 overlap pairs | — | Categorized header |
| M4 | Code Flow: add the prediction loop after Save (H15) and a "rules it must obey" column per step (H1) | — | Claude 2026-10-01 |

---

## 13. My redesign thoughts (hypotheses — to test or discard)

- **H1 · Two maps, tied together.** Notion homes = what must be true; Code Flow = what runs, in order, and who does it. Each Code Flow box lists the homes it must satisfy; each home lists the Code Flow steps that touch it. (The owner's idea; I would add the cross-reference.)
- **H2 · Reading everything shrinks the channels.** (The owner's 2026-10-01 "one flow, two uses" points this way.) If every filing, call and story is read blind (rough_design), "channels" become triggers + document lists. Fiscal.ai becomes a recall checklist (did we capture every KPI it lists?) and a source of XBRL tags; the Guidance pipeline stops being a separate creator (guidance is a type the reader already extracts; its code may still be reused); filings stop being "update only". A big simplification, but it changes the release plan and the go-live test. Owner decides.
- **H3 · Spend effort where errors are permanent.** Strongest model + independent check for name, type and merge; a cheap judge + code for per-fact fields; anything unclear fails closed to `unknown` or empty, which is not a "wrong claim" under 8.17. That is the realistic route to <1% wrong whole facts: fewer risky claims per fact, not only better ones.
- **H4 · Measure whole facts; never multiply field scores.** Pilot on complete facts; report raw and reviewed scores separately.
- **H5 · News without move-selection.** Read news broadly (or at least sample quiet days too); select by moves only for verdicts. Otherwise the Learner sees only Drivers that came with big moves.
- **H6 · 8.16's searches may become unnecessary** in a full, time-ordered pass (every earlier document is read anyway). Keep only a check for late or backdated documents.
- **H7 · A time-ordered single pass means less hindsight.** Matching against the catalog as it grew mirrors what the system knew then — better for honest backtests than 1.14's "today's catalog". Cost: saves are serial; matching waits for earlier events.
- **H8 · Decide JEV once, as a bundle.** One ruling covering 8.12 (billing, provider), 8.13 (qualification), 8.5/8.6 (cutoffs), 1.9 (prompt wording) and 8.2 (independence), instead of task by task.
- **H9 · One copy per rule.** Merge the 8 overlap pairs while studying the homes. Generate every served prompt from one field registry (JEV idea AA), so prompt text can't drift from the rules.
- **H10 · Trace each rule's "why" before keeping it.** Several rules exist because of the old channel model or a past failure (8.9, 8.16, 3.44, 2.30's live/non-live split, 6.6's fixed checks). Keep the ones whose reason still holds.
- **H11 · Fewer decisions, batched.** The register has ~50 items, but about 6 structural ones decide most of the rest: A1 (one picture), A2 (catalog route), B1 (reading unit), J1 + J3 (the JEV bundle), C1 (5th type), G1/G3 (causes). Settle these first; the rest follow or become small.
- **H12 · Greenfield advantage.** 0 Drivers in the database → no migration. Field lists, IDs and node shapes can change freely until the first write.
- **H13 · Use "prediction first" to cut scope.** For every proposed feature (5th type, `caused_by`, physical units, extra dates, XBRL links, renames), ask: how does it help explain a move or predict one? Build first what feeds the Learner/Predictor; park the rest. A cheap way out of paralysis.
- **H14 · "Read once" design.** To honour priority ③, give the one reading pass enough context to finish the job (heading path + neighbours + resolved references), and make every later step a cheap check on text already read (JEV yes/no, code) rather than a second read. Escalation = only the small failing piece goes to a stronger model, never the whole document again.
- **H15 · Code Flow stops at Save, but priority ① is prediction.** Nothing on the page yet shows saved facts → explaining moves (verdicts, S5) → the Learner → the Predictor. The run map should end in that loop, or the "prediction first" test can't be applied to any step.
- **H16 · Step 3 (smart AI names every fact) is probably the biggest cost.** Rough scale: ~7M candidate facts across the corpus (JEV.md §6.8 extrapolation: half of 13.6M flagged units). Levers to measure: name all facts of one document in one call; reuse the answer for identical input (2.46; whole-input repeats are only ~15–20%, JEV §6.7). Blind naming (1.14) rules out "look up the catalog first".

---

## 14. Working with the owner

- **Style:** crux first · plain words · short but complete · visuals (tables, arrows, before/after) · remind the owner of earlier findings · say what / why / proposal before any detail.
- **Reply shape:** "1. Explain in one line. 2. Acknowledge what I'm saying. 3. Tell me in one line."
- **Decision items:** what it is (1 line) · options + trade-off (2–3 bullets) · my recommendation + exact wording · "approve?". No history unless asked.
- **2026-10-01:** start from the beginning; don't assume what the owner already knows; one component at a time; one running example; heavy visuals.
- **Ask before ANY change** (files, Notion). "Check / verify / review" = report only. A yes covers only the listed edits.
- **Subagents:** never Fable; always pass `model: sonnet` or `haiku`; never fork.
- **Rules are breakable:** present a conflict as a trade-off (what the rule protects · what the idea gains · a cheap test), never as "not allowed".
- **Design questions:** trace the rule's why first (v1.1 Part C1 → sources); say what I read in full vs skimmed.
- **Independence:** never rubber-stamp Codex, or my own earlier answers.
- **No meaning word lists** (8.6; owner 2026-09-30).
- **Shared files:** Codex and other Claude sessions edit the same files and pages — Codex also writes notes into this scratchpad (§15); re-read before editing. The owner relays messages between us. Don't edit `fact_types.md` unless asked (Codex maintains it).
- **Logging:** every owner message goes into `Archive/WORKFLOW_SCRATCHPAD.md`, above "# Archived: approved no-stages proposal".
- **Stay on route:** the agreed study order is S1 → 1 → 2a → 2b → 2c → 3 → U1a … U3b → S2 … S5. Flag any drift in one line; the owner may override.
- **Anti-paralysis:** one thing at a time; small boxes; few decisions per sitting.

---

## 15. Log

- **2026-10-01 · created.**
  - Read in full: `DRIVER_RULES_Categorized.md` (1,343 lines), `rough_design.md`, `fact_types.md`, `DRIVER_CODE_GUIDE.md`, `Dockling/docling.md`, `XBRL_Definitions.md`, JEV.md §0–§3 and §6.7–§11, the scratchpad's decisions D1–D44 and its log for 2026-09-30 → 10-01, v1.1 Part B and C4, Phase 6 + Route D, all 32 Notion pages.
  - Skimmed: JEV.md §4–§6.6, the AUDIT outline, the Archive file list, my older memory digests of FINAL_DESIGN / BUILD / Steps.
  - Verified live: Neo4j counts and constraints; the Categorized file holds all 906 lines of the archived master + 118 heading lines.
  - Not read: the AUDIT body, the JEV scripts, FINAL_DESIGN / BUILD / Steps.md themselves.
  - Later the same day: found the other session's new Code Flow page and log entries (5 priorities, "one flow, two uses"); added them here (§0, §1, §4, T2, T23, T24, A1, A6, H13, H14).
  - Owner: "Can you read the code flow on my Notion page?" → re-read it (14:48 UTC); noted H15 (no prediction loop after Save), H16 (step 3 cost), M4.

- **2026-10-01 · Codex read the current Notion Code Flow directly at the owner's request.**
  - Source: [Code Flow](https://app.notion.com/p/3eca0a3f310681678852e706a704604e), last edited **2026-10-01 14:48:24 UTC**. The fetch returned the page body and diagrams, with no omitted-content marker; Notion marks the page unverified.
  - Priorities in order: prediction usefulness; near-100% recall and precision; lowest cost including subscription limits and avoiding repeated reading; fastest complete run; minimal organized code.
  - Input: news, earnings calls, and SEC reports. Trigger: a document is ingested. One proposed flow serves both historical creation (oldest first) and updates from new documents.
  - Six steps: **Cut** (code + Docling) → **Read** (cheap AI) → **Name** (smart AI) → **Details/check causes** (JEV + code) → **Match/reuse or new** (code + AI check) → **Save facts and links** (code).
  - All six steps are **open and proposed**. Step 4 is explicitly **suggestion only, not yet discussed**. The legend defines green as **agreed and tested**; no step is green.
  - The page explicitly keeps open the conflict with Workflow's "Filings & Transcripts only update" restriction. Reading all historical text to create Drivers changes that boundary.
  - Counts printed on the page: 348,670 news stories; 9,608 calls; 42,633 SEC reports (29,672 8-K, 7,301 10-Q, 2,993 10-K, 2,667 other). These are page-reported counts, not a fresh database query by Codex.
  - Refresh for the older register above: **M1's page creation is complete**; future editing ownership is separate. **M2's legend wording is now stated on the page**. Neither fact approves the processing design.
  - Only this local reading note was added. No Notion page, rule or implementation was changed.

- **2026-10-01 · Owner requested concise wording for the five priorities and suggestions for improvement.**
  - Owner's order: usefulness for automatic prediction; nearly complete and correct facts; lowest total cost including subscription capacity; shortest implementation time and complete running time; organized, efficient, minimal code.
  - Proposed wording: **Prediction value** — every part supports explaining price moves, learning which Drivers matter and predicting automatically. **Fact quality** — aim close to 100% recall and precision: capture relevant facts and keep accepted facts correct. **Lowest total cost** — use the cheapest capable mix of JEV, local models and Claude/OpenAI; minimize strong-model input and unnecessary rereading. **Fast to build and run** — minimize implementation time and time through the complete workflow. **Minimal, clear code** — keep code organized and efficient; add only what is needed.
  - Codex suggestions: explicitly include build time in priority 4; replace absolute "nothing read twice" with "avoid unnecessary rereading" so necessary evidence checks remain possible. The latter is proposed clarification, not an owner-approved rule change.
  - This request is for wording in chat. The Notion page has not been edited.

- **2026-10-01 · Owner clarified the priority wording.**
  - Keep context as small as possible without losing any information.
  - Priority 1 means keeping the final goal central: explain price moves, learn what matters and predict automatically. Intermediate steps may support that goal indirectly; they need not each show a direct prediction benefit.
  - Priority 2 is near-100% recall and precision across the **whole document**, not only correctness of already-extracted facts. This corrects the emphasis in Codex's previous proposed wording.
  - Owner accepts the heading **Lowest total cost** and wants its explanation shorter. Retain the substance (cheapest capable tools, small complete context, avoiding unnecessary repeat work) without listing every model or cost mechanism.
  - This is a local continuity note; revised wording remains a chat proposal. No Notion edit was requested.

- **2026-10-01 · Owner likes the revised five priorities and requests stronger conviction.**
  - Preserve their clarity and brevity, but restore the urgency and passion of the owner's original wording so bots treat them as instructions to follow in every decision.
  - Keep the substance: end goal first (indirect contributions count), whole-document recall and precision near 100%, lowest total cost with the smallest context that preserves information, fast implementation and processing, minimal organized code.
  - Strengthen the verbs and make the priority order explicit; do not turn the near-100% target into a guarantee. The new wording is for chat; no Notion edit was requested.

- **2026-10-01 · Owner approved publication: "Update the Notion."**
  - Updated the five priorities in Code Flow's existing blue collapsible section with the exact latest chat wording, including **Apply these priorities to every decision, in this order.**
  - Headings: **End goal first**, **Whole-document accuracy**, **Lowest total cost**, **Fast to build and run**, **Minimal, clear code**. The stronger wording is now owner-approved and published.
  - Re-fetched the page and confirmed the complete wording and toggle nesting. Other edits arrived concurrently (Cut → Prepare, step-page links and grouping); the targeted priority edit preserved them.

- **2026-10-01 · rough.md check:** v3 holds all three reviews and its numbers reproduce; new verified findings in §9g (exhibit cleaner deletes text in earnings releases; one root cause for F2/F9/F12; 35–60% mis-attributed). runningIdeas.md not changed.
- **2026-10-01 · owner: "why do we even need the later-report check? over-complicating? which part — Cut?"** → my answer: only in T1 (converter test, B · Convert); not needed for Prepare — the original file is the answer key for exact numbers and their printed labels; meaning checks belong later. Proposed dropping it from T1; awaiting owner yes.
- **2026-10-01 · later-report check script found:** `scripts/driver_seed/relocate_probe/phase2/m3_candidate_census.py` (143 lines, test 91, result json; inputs exist; imports `driver_reference.relocation.inline_html`). Not in driver_reference/ or drivers_harness/. Adapt ≈ 1–2 h; exact values only, unconfirmed matches, money only. My suggestion now: optional extra check in T1 for press-release dollar amounts.
- **2026-10-01 · owner: keep the later-10-Q cross-check for now; verify each part of reused code before using it.** Note added to runningIdeas.md under "Code home"; memory `feedback_verify_reused_code_before_use`.
