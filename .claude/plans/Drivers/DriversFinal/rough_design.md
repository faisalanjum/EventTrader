# Rough design: reading sources into Drivers

> **Partly superseded (2026-10-01):** for Step 1 · Prepare, [PrepareStep.md](PrepareStep.md) v5 and the updated rules win. The original files are the evidence record, not the stored text. The converter is chosen by test T1 (out of the box, no custom table code), not "printed PDF for the section map". Reads are smaller and shaped per task (rule 8.10). The decisions here are replaced by PrepareStep D1–D15.

*2026-09-30 · starting design from the owner, Claude and Codex; every claim checked against its source; revised after Codex's review · **nothing here is proven** · no rules, code or Neo4j changed; [fact_types.md](fact_types.md) and the [rules](DRIVER_RULES_Categorized.md) stay the authority.*

**In one line:** code cuts each source into pieces → a cheaper AI (to be tested) finds the facts → one smart AI proposes Driver names (order to be tested) → JEV fills most fields and verifies each stated relation → a separate check matches names to the catalog → code saves one source event at a time.

**Words.** *Driver* = one reusable name for a cause (`revenue`). *Fact* (DriverUpdate) = one quoted occurrence of it. *JEV* = a paid judge (TypeSafe) that answers yes/no, picks from a list or ranks; it never writes. *`CAUSED_BY` / `OFFSET_BY`* = a link from a result fact to a fact in the same source that drove it / pushed against it, carrying the quote that states the link (rule 3.53).

**Goals (owner):** close to 100% recall and precision · lowest cost · fastest · least code.

**Not chosen: a manager AI on top (Option 2).** Every sentence must be read anyway, so a manager adds its own cost and delay and could skip text silently; any benefit it brings (smarter cuts, links across sections) is unmeasured. Phase 6 also wants single-shot readers with no tools. Borrowed from it: heading paths, fetching referenced sections, one name check across all filings.

## Flow

| Step | Who | What | Guards |
|---|---|---|---|
| **1 Prepare** | code | Filings via Docling: HTML for text and table cells, printed PDF for the section map (Part → Item → subheads); to validate, including lining the two up. Transcripts: the stored remarks / Q&A split. News: one story = one piece. Cut at the source's own blocks (paragraphs, tables, Q&A exchanges), grouped by section; each block belongs to exactly one piece, with neighbours as read-only context. XBRL stays as today. | Prove no text is lost: every non-space character of the original lands in a piece or is logged as page furniture (FinalPlan Route D: "First shadow-prove that no evidence is lost"). Keep the original, parser version and frozen output. No stock returns in any input (1.14). |
| **2 Read** | cheapest approved model that passes (Phase 6) | Per piece: each fact with its exact quote (mixed quotes split); slice values from the company's list (3.17); marks a surprise and its home fact as a pair; proposes each stated relation between its facts as "A causes / offsets / is part of B"; flags references ("see Note 5", "as discussed above"). Sees no existing names (1.14). | Each quote must occur exactly in its stored source part (today's code checks this). Each piece returns facts or one stated reason for none (8.14): this accounts for pieces, not sentences. |
| **3 Name** | one smart model | Proposes a base name per fact (no `_guidance` / `_surprise` ending) from its quote and context, without seeing existing names (1.14). A surprise and its home fact share one base name (4.14). | **A proposal, not proven:** JEV did better *with* a name (96.4% vs 94.2% hidden), but those were earlier-model names, not fresh base names; the pilot tests this exact order. |
| **4 Judge** | JEV + code | With the base name as context: JEV picks fact type, state, unit (a small first choice: our 10 units + physical/time + other-money total + other-money per unit; then the relevant official list, split into branches if over 255 options; `unknown` in every list; untested), span, baseline, horizon, slice kind; code adds the type ending (2.19). Code finds candidate numbers; JEV picks the value and reads date parts (untested); code does all math and calendar work. JEV verifies each proposed relation (below). | Low confidence → an approved stronger model, or skip and count; confidence never permits a write (8.5). |
| **5 Match** | code + a separate blind call | Code shortlists candidates from the whole current catalog (2.43); a separate blind call approves reuse or a new name (8.2); JEV may only veto. Code records which catalog version the match saw. | Unsure → keep separate (1.12). A refusal is final (2.47). |
| **6 Save** | code | One source event per write (`plan_event_write`). Each verified relation becomes a `CAUSED_BY` or `OFFSET_BY` link between the two accepted facts, with the exact words stating the link as its quote, saved with them (3.53); if either end wasn't accepted, drop it and count. Inside the write, code re-checks that the source and every Driver it uses are unchanged, else nothing is written (5.8; today's writer does this). That alone misses Drivers added since this event's match, so: if the catalog changed since the match, the event is held, its new names are matched against just the added Drivers, and the save retries (5.8, 8.15; cached answers keep it cheap, 2.46). | A database rule refusing duplicate Driver names must exist before go-live: **absent today** (0 Drivers stored). It stops exact duplicates only; two words for one cause ("oil price", "crude price") depend on step 5. |

**Timing:** pieces and filings run in parallel through steps 1–5. An event is written only when all its pieces are done, one event at a time, in public-time order (1.14); today's lock turns a second writer away (`WRITER_BUSY`) rather than queueing it. Answers are cached by exact input, so a re-run changes nothing (2.46, 5.4).

## Causes
- **The reader proposes, JEV checks.** JEV re-checking its own answers caught few of its own mistakes (2 of 32 by claim check, 0 of 10 by re-asking; JEV.md §6.5), so it checks someone else's proposals (8.2).
- **JEV verifies the exact claim:** one yes/no per proposed relation, with direction and role in the text: *"Does this passage state that [A] offsets [B]?"* A plain "caused?" question would reject valid offsets and part-of links. Several causes → several claims ("prices **and** volumes"). Three tiny pilots found 46 of 46 real cause links with 0 false among 23 non-links, against one labeller's (Claude's) labels (36 items, 6 synthetic; JEV.md §6.11; Codex reproduced the first 31 pairs). Asked as "caused?", offsets scored 0.03–0.53, never clearly yes; asked as "offsets?" they are untested, as is part-of. JEV also counted an indirect cause (a cause of the cause) as a cause (0.94), so a direct-vs-indirect rule is needed. A pick-one question finds only one cause.
- **What JEV sees:** the smallest passage holding both facts and the link: 3 sentences, expanded once to 5 (fact_types.md); for a resolved reference, the referring sentences plus the target. A starting window, not a proven one; in pilot 3 a cause 3 sentences away was found only after the expansion. Still unclear, or the facts are farther apart with no reference → skip and count.
- **References:** "Item 7" → code fetches it from the section map ("Note 5": untested). A vague "above" outside the piece → one extra reader call gets the referring passage plus the relevant earlier text (its own section first; the outline may only suggest where else to look, since only actual text settles what "above" means), then proposes the relation for JEV to verify. Unresolved → skip and count.
- **Scope:** links stay inside one source event. `conditions` hold assumptions only. The Learner's guessed causes are stored separately, marked as guesses.

## Safety nets (pilot first; before saving, 6.20)
- **Missed links:** JEV also asks every other pair in each window which relation, if any, the passage states (untested). A relation only JEV finds needs one blind check by the reader model, or is skipped and counted.
- **Missed facts:** JEV tags every sentence (about $1.2K for the whole corpus, JEV.md §6.7). A sentence tagged as a fact that got no fact goes to a separate, stronger blind read that isn't told the tag. On 50 fresh facts the loose rule caught all 50 (lower bound 93%) while flagging 41% of text; its known blind spot is "explanation of a change" sentences, which are the cause sentences (§6.6).

## Decide before building (owner)

| Area | Decision | Rules |
|---|---|---|
| Reading | Replace "the reader sees the whole event" with: every block read once, with its heading path and neighbours, plus fetching of referenced sections (Route D is the precedent). Keeping it limits the local model (16–30k tokens per call) to shorter filings. Averages are roughly 44k tokens for a 10-Q and 108k for a 10-K (characters ÷ 4), but the share of filings over the limit is unmeasured; measure it with the model's own tokenizer. | 8.10, 8.9 |
| Evidence | Which text is the record: the stored source parts (quotes must match them exactly) or Docling's frozen output? 8-K tables count only in the original. | 1.17, 8.8 |
| JEV use | Production use: pay-per-use and another provider (the rule's example is a paid service that only *suggests*); qualified per task; not in the Phase 6 pool. | 8.12, 8.13 |
| JEV's final word | Fact type and slice kind shape identity: may JEV decide them? 3.16 says no AI judges a slice's kind at runtime (XBRL axes only?). Otherwise the reader proposes and JEV checks (JEV.md idea N). | 8.1, 8.2, 3.16 |
| Cutoffs | Each needs a frozen value: JEV pick confidence, the pair yes/no, tag weights and cutoff, identity veto (0.29). Low confidence: escalate or skip? | 8.6, 8.5 |
| Prompt wording | V6's extra clauses and the identity sentence (the 94% veto needs it; 77% without). | 1.9, 2.21, 2.44 |
| Cause links | ✅ Decided 2026-10-02: links between facts, `CAUSED_BY` and `OFFSET_BY` (3.53). Still open: are indirect causes stored? | 3.53 |
| Re-reads | The missed-fact net re-reads text the reader called fact-free; the vague-reference step adds a call. Phase 6 allows escalation only on ambiguity, invalid output, verifier conflict or no proven match. | 8.12, 8.15, S4 |
| Wording | The rules call the reader the step that proposes facts *and* names; here a separate model names. | glossary |
| Scope | Models from the Phase 6 pool (local AI, Haiku, Sonnet 5, Luna; a non-Anthropic model needs a ruling). Release 1 is fiscal.ai only; the Neo4j adapter reads filings only. Open rule gaps behind the low scores: sign, "over time", the filer's own name (JEV.md §3.3). | 9.5, 8.12 |

## Pilot (needs your OK)
- Answer key from whole passages, labelled blind and locked before any AI call; graders qualified first; about 300 graded facts for the under-1% bar (8.13, 8.17). Not the 93 cause-word labels: they can't show links written without cause words.
- Fields, three arms on the same key: JEV fills fields · the reader proposes and JEV checks · the reader alone, no JEV.
- Naming order, the exact flow: fresh base names before JEV · JEV given no name · the reader naming as it reads.
- Count: missed facts · wrong names · complete facts with every field right (measured directly) · relations never proposed · causes outside the window · wrong direction · wrong role (offsets and part-of included) · unsupported relations.
- Measure the share of filings over the local model's limit with its own tokenizer.
- Compare a cheap and a strong reader ("a cheap reader loses nothing" is unproven). Report tokens, calls and time separately from quality.

## Known risks
- **Whole-fact accuracy is unmeasured.** Per-field scores (about 80–99.6% raw, JEV.md §2) come from different test sets, so they can't be combined into a whole-fact figure; the pilot measures complete facts directly. Low-confidence flags caught 64–100% of misses by field; fact type's 11 of 11 was on tuned items, and a fresh fact-type error sat at 0.99. So confidence routing alone is not shown to reach the under-1% bar (8.17).
- **Docling:** 271 of 273 Item headings found in 13 10-K/10-Q filings, not proof of complete splitting; nesting was noisy on one 10-K (ADM). About 25–30 days for the corpus in one CPU process, PDF route only (HTML and 8-K main documents unmeasured; parallel and GPU untested).
- **Two names for one cause** are caught only by step 5. JEV as a veto was shown once, on one held-out half, with the unapproved sentence (ruled out 94% of different pairs, lost 3 of 73 real matches).
- **Close to 100% recall vs the skips:** links beyond 5 sentences, low-confidence answers and unresolved references are skipped and counted; the pilot measures how many.
- **The edge over Option 2** in cost and accuracy is reasoning, not measurement.

**Known costs so far:** JEV tags ≈ $1.2K and identity checks ≈ $1.1–1.9K for the corpus (extrapolated); JEV time 2–7 days at the observed rate (19 at the documented limit); Docling ≈ 25–30 days on one CPU. Reader cost: unmeasured.

**Sources:** [fact_types.md](fact_types.md) · [JEV.md](JEV.md) · [Dockling/docling.md](Dockling/docling.md) · [rules](DRIVER_RULES_Categorized.md) · Phase 6 and Route D in `../WIP/UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md` · `driver_reference/core/driver_writer.py`, `driver_write_cli.py`, `driver_neo4j_adapter.py`, `prepared_fact_v2.py` · discussion log: `Archive/WORKFLOW_SCRATCHPAD.md` (2026-09-30).
