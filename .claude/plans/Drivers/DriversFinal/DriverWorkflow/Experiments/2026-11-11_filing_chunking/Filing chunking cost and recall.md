# Let code cut, Claude read, Jev check

**The best strategy at scale: free code rules make almost every cut, the cheapest approved Claude model reads every block, and Jev acts as a cheap second opinion that decides where a stronger model takes a second look. Jev should never be a gate that deletes text.** Batched, Jev costs about **1 cent per 10-K**. Today's one-call-per-block wording costs about 5 cents. Jev cannot write, count or prove anything, and in our tests it leans toward keeping text, which is the safe side. The smart model is where the real usage goes. API prices stand in for subscription usage here: about **3–4 cents per 10-K for a Haiku-class read** and **57–87 cents for a Sonnet-class read**. So the biggest win is spending strong-model reads only where Jev and the cheap reader disagree, where the reader says "unclear", or where a code check fails. Single reads miss a lot, even with top models. In our test one read found about half of what several reads found together. Top models also miss 17–20% of figures in earnings releases. So near-100% recall has to come from layered, targeted second looks, not from a bigger model. "One Driver per chunk" cannot come from cutting text in order, because one Driver's facts are spread across a document. Get it by grouping the extracted updates by Driver afterwards. **100% recall can never be proven.** Zero misses in about 600 human-checked facts per document type only shows recall ≥ 99.5% with 95% confidence. And the current "union of runs" answer key overstates recall. The staged plan at the end starts with free code checks and a human answer key, then adds AI layers one at a time. Each layer has a pass bar and a cost.

**Plain-word key**

| Term | Meaning here |
|---|---|
| Block | One extracted unit: a paragraph, heading, whole table, picture or XML field, with its location |
| Chunk | The group of blocks that one smart-model call reads (target now about 8,000 characters) |
| Recall | Share of all true Driver updates that we find |
| Gold set | Answer key: every true Driver update in a document, found by people, not by the models under test |
| Union-of-runs gold | Answer key made from everything any model run found; it cannot contain facts that every run missed |
| Elusion audit | Read a random sample of what was skipped or marked "none", and count the facts hiding there |
| Capture-recapture | Compare two different reads; their overlap estimates how many facts both missed |
| Gleaning | Asking the reader once more on the same chunk: "what did you miss?" |
| Context-only line | A title, unit or speaker line copied into a chunk to explain it; never extracted as a new fact |

## Code does four of the seven steps; AI does three

The owner's draft design survives almost whole. What changes is where Jev and the smart model sit. Code places the cuts and copies the context. Jev tags every block once and flags trouble. The cheapest reader reads everything. The strong reader looks only where something fired.

```
Ordered blocks (already extracted, with byte locations)
  │
  ① CODE   drop exact-match boilerplate · mark text identical to the last filing (guarded) · find section starts
  │
  ② JEV    one batched pass: each block → fact / label / nothing (+ probability)
  │        yes/no "does B rely on A?" only at joints near a planned cut
  │
  ③ CODE   cut ≤ 8K chars at a section start, else at the latest safe joint · tables whole
  │        (row groups that repeat the header if a table is too big) · copy heading path,
  │        unit line, column heads and speaker as context-only · attach notes that markers point to
  │
  ④ CHEAP READER   every block → Driver update(s) with exact quote, or a short coded reason
  │
  ⑤ CODE   coverage · letter-for-letter quotes · unit words inside the evidence · failed call ≠ "none"
  │
  ⑥ STRONG READER  only on triggers: Jev "fact" vs reader "none" · "unclear" · failed checks · Jev unsure
  │
  ⑦ CODE   group updates by Driver · record the fact's period and the date recorded · cache by text hash + prompt version
```

Steps ①, ③, ⑤ and ⑦ are free and can be checked by hand. Step ② is measured as safe on seven documents (see below). Steps ④ and ⑥ are what the test plan has to settle.

Each document type has a natural unit and its own context to carry:

| Document | Natural unit | Context code copies in | Extra help |
|---|---|---|---|
| 10-K / 10-Q | Section, packed to ≤ 8K characters; tables whole | Heading path, unit/scale line, column heads (periods), one-line source header | Each note is one tagged XBRL text block, so "see Note 7" can be looked up; XBRL numbers as a cross-check; compare with last year's filing |
| 8-K press release (~22K chars → ~3 chunks) | Section or table, packed | Headline, dateline, table titles, unit lines, footnote markers → the note blocks they point to | None: SEC tagging covers only the 8-K cover page |
| Earnings-call transcript | Prepared remarks: one speaker turn. Q&A: one question plus its answers | Speaker name and role, call quarter, and the analyst's question carried with each answer | None |
| News | Whole article | Headline, date, source | Watch for later edits |

Tables kept whole and a new chunk at every title are standard in financial chunking work ([Source](https://arxiv.org/html/2402.05131v3)). Docling repeats header rows when it splits a table ([Source](https://docling-project.github.io/docling/concepts/chunking/)). A 2026 earnings-call study pairs each analyst question with the answer that follows it ([Source](https://arxiv.org/html/2611.14325)). SEC rules require tagging only the cover page of 8-Ks ([Source](https://www.sec.gov/rules-regulations/staff-guidance/compliance-disclosure-interpretations/interactive-data-cdi)). Notes in 10-K/10-Q statements are tagged as single text blocks ([Source](https://novaworks.knowledgeowl.com/help/what-are-the-requirements-for-xbrl-and-what-do-the-levels-of-tagging-mean)). That last source is a filing vendor; the SEC rule text itself was not checked.

## Code rules should place almost every cut; Jev only judges the leftovers

**Structure beats cleverness on financial text.** In one study, financial reports were cut so that each title starts a new chunk and each table stays whole. Q&A accuracy rose to **53.19%**, against 48.23% for 512-token chunks, using fewer chunks ([Source](https://arxiv.org/html/2402.05131v3)). On real documents, "smart" semantic chunking rarely beats simple cuts. Its gains show up mainly on artificially stitched multi-topic text ([Source](https://arxiv.org/html/2410.13070)). Filings already mark topic changes with headings, item numbers and tables, so code rules capture most of the value for free. One caveat: all of these studies measure search (retrieval), not exhaustive extraction. For us, a "bad" cut only hurts if it separates a fact from the context it needs. A chunk holding two topics costs extra tokens but loses nothing.

**Where Jev fits.** In our neighbour-pair test, Jev never split a real tie (**0 of 51**) but recognised only **30 of 55** real separations. That is the safe kind of error: merging too much costs tokens, not facts. So use one yes/no question per joint, with both blocks shown in full. A segmentation study found accuracy (F1) fell from 64.0 to **20.2** when the model saw only the text before a break ([Source](https://arxiv.org/pdf/2004.14535)). The wording should be narrow. TypeSafe's own cookbook found "does line B continue a sentence left unfinished in line A?" worked, while "same paragraph?" wrongly merged list items ([Source](https://docs.typesafe.ai/cookbooks/autoformat.md)). Ask only about joints near each planned cut, not every joint: a 10-K needs about 50 cuts, not 1,000 decisions. Avoid the draft's "pick the best cut among numbered blocks" form. Jev leans toward the first option in pick-one questions ([Source](https://docs.typesafe.ai/model-jaggedness.md)). The model-picks-the-cut method (LumberChunker) worked on only 1 of 5 datasets when run with a 7B open model ([Source](https://arxiv.org/html/2410.12788v1)).

**Supermemory's Jev chunker supports the question style, not the claim for filings.** Supermemory asked Jev, sentence by sentence, "continues the previous thought or starts a new one?" On their internal search test it scored **93%**, against 89% for recursive and 81% for embedding chunking. That test had **72 questions** and 320-character chunks, so the gap over recursive is about three questions. English scored only 67% in their multilingual check, and the method cost $0.080 per 1,000 documents against $0.008 for rules ([Source](https://supermemory.ai/blog/jev-memory-context-engineering)). No prompts or boundary-accuracy figures were published. Take from it the "does B continue A?" framing, which matches our own result. Do not take the 93% as evidence for 8K-character chunks of filings.

**Copy context with code, not with a model.** A Snowflake study covered about 23,000 10-K/10-Q filings. Adding simple document-level context lifted answer accuracy to **72–75%**. Model-written context for each chunk *lost* 0.4–5.8 points ([Source](https://www.snowflake.com/en/engineering-blog/impact-retrieval-chunking-finance-rag/)). Copying a ~200–400-character header onto an 8K chunk adds only about 2.5–5% input (my arithmetic).

The recommendation:
- Copy the whole label stack in scope: heading path, nearest unit line, table column heads, speaker.
- Each copied line keeps its home location, so the "supporting words" can cite it. That meets the rule that unit words must sit inside the evidence.
- Mark copied lines "context only", and take facts only from each block's home chunk.
- Skip the proposed Jev "which earlier labels still apply?" check by default. Dropping a needed label breaks meaning; keeping a spare one costs a few tokens.

**Distant notes need a lookup, not a search.** Code can follow markers like "(1)" or "see Note 7" and attach the note block as context-only. In the AMG release, the highlights table points to notes in blocks 38 and 43, so this case is real (project review, 11 Nov). Do not let Jev search the whole document for "needed" context. It wrongly called 25 of 55 separate pairs tied, and in that role every false "yes" eats the 8K budget.

**Oversized tables.** Split them into row groups that repeat the header rows, instead of recording them "not read". This needs row positions inside the table block, which should be checked in the extraction output.

**"One Driver per chunk" is a grouping job, not a cutting job.** A revenue Driver shows up in the headline, the table, the MD&A and the outlook, with other topics in between. Cutting by structure gives "one topic per stretch", such as a Q&A exchange or an MD&A subsection. "Every fact for one Driver" comes from grouping the updates after extraction. There is a stronger version. DocETL found that giving the model one narrow field at a time raised recall on contracts from **0.430 to 0.719** ([Source](https://arxiv.org/html/2410.12189v3)). The same idea applies to one Driver *type* per call. It multiplies calls, so keep it as a fix for any Driver type that tests show is under-found.

## Jev costs about a cent per 10-K, so spend it steering Claude, not trimming Claude's reading

The table compares Jev and the smart models per document at API prices. **Jev is real cash.** The Claude runs use the subscription, so their dollar figures stand only for usage limits and time.

| Step (per document) | 8-K press release (~5.5K tokens) | 10-K (~105K tokens) |
|---|---|---|
| Jev, today's one call per block (~1,170 tokens/block) | ≈ $0.003 | ≈ $0.05 |
| Jev, batched windows (text sent once, ~57 tokens per extra question) | ≈ $0.001 | ≈ $0.01 |
| Haiku-class full read (Haiku 5.5 prices) | ≈ $0.0035 | ≈ $0.03–0.04 |
| Sonnet-class full read (Sonnet 5.5 prices) | ≈ $0.07 | ≈ $0.57–0.87 |
| Opus-class full read (Opus 5.5 prices) | ≈ $0.14 | ≈ $1.15–1.74 |

How these were worked out (my arithmetic):
- Prices: Haiku 5.5 $0.10/$0.50, Sonnet 5.5 $2/$10, Opus 5.5 $4/$20 per million input/output tokens ([Source](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).
- Assumed guesses: about 1,000 blocks per 10-K, a 3K-token instruction block, and about 33K output tokens per 10-K.
- The low end of each Claude range assumes the instructions are cached.
- The ~57 tokens per extra question comes from TypeSafe's published numbers: 13 separate calls cost $0.006090 and one batched call cost $0.000497 ([Source](https://docs.typesafe.ai/cookbooks/parallel_questions.md)).
- The earlier puzzle ($0.033 vs $0.0135) is settled. The $0.033 covered every run, 791,658 tokens. One pass is about $0.0135.

**Batch Jev's questions.** Today's per-block wording costs about as much as Haiku reading the whole press release. TypeSafe measured 13 questions on one shared input as **12.2x cheaper and 11.8x faster** than separate calls, with answers moving at most 0.015 ([Source](https://docs.typesafe.ai/cookbooks/parallel_questions.md)). Batching pays only if the long definitions go once per window, not once per question. Jev's accuracy also drops as its input fills with unrelated text ([Source](https://docs.typesafe.ai/model-jaggedness.md)). So the window size (10, 30 or 100 blocks) must be re-tested against today's per-block answers.

**Do not delete text with Jev to save Haiku reading.** Removing "nothing" blocks saved only about 10% of words across our seven documents. At Haiku prices that saving is worth about what Jev costs. Jev pays off where it decides whether a Sonnet-class model needs to look at all. Re-reading the 10% of a 10-K that Jev flags costs roughly 6–9 cents, against 57–87 cents for a full second Sonnet read (my arithmetic). At scale, one text-only Jev pass over 100,000 documents of ~30K tokens is about $126 (my estimate). That is small next to the Claude usage it steers.

| Use Jev for | Why | Status |
|---|---|---|
| One batched pass per block: fact / label / nothing, with probabilities | The net that says where facts are; lost **0 of 119** fact/label blocks; 1 of 275 answers changed on a repeat run | Measured on 7 documents; not on a 10-K or table rows |
| Yes/no at joints near a planned cut | Never split a real tie (0/51) | Measured on pairs |
| Three probability bands: sure / unsure → strong reader / never delete | Thresholds live in code, not in Jev | Untested here |
| Ranking blocks or chunks for the second look | Supermemory found Jev "kept nothing" as a hard gate but worked as a sorter | Untested here |
| **Do not** use Jev to delete text before the reader | Small saving (~10%); proving it safe needs ~600 facts per type | Keep deferred |
| **Do not** use Jev to compress sentences | Supermemory: 58% fewer tokens, but meaning broke | Avoid |
| **Do not** use Jev for counting, math or picking one of many IDs | Known weak spots | Avoid |
| **Do not** let Jev search the whole document for context | Says "needed" too often (25/55) | Avoid |

## Recall comes from targeted second looks, not a bigger model

**Single reads miss a lot, and model size barely moves it.** In our test, Sonnet found **48.3%** and Opus **51.3%** of the union of all runs at 8K-character chunks. At 40K the figures were 40.4% and 42.4%. Outside studies agree:

| Study | Setting | Recall from one read |
|---|---|---|
| EarningsBench ([Source](https://www.financialdatasets.ai/blogs/earningsbench)) | 60 hand-checked earnings releases | Opus 4.6: **80–83%**, at 98.9–99.3% accuracy. Sonnet 4.6 with thinking: also 83% |
| LEDGER ([Source](https://arxiv.org/html/2606.13100)) | Annual reports, ~126K tokens, open-weight models only | No model above 80% |
| LongExtractionBench ([Source](https://www.micro1.ai/benchmark/long-extraction)) | Table-heavy documents, vendor-commissioned | Frontier models read directly: 48.6–70.7% |

A bigger model alone will not reach near-100%.

**What does raise recall:**
- **Smaller inputs.** GraphRAG extracted almost twice as many entities from 600-token chunks as from 2,400-token chunks ([Source](https://arxiv.org/html/2404.16130v2)).
- **Targeted rechecks.** In FinReflectKG, a check-and-retry step raised judged completeness from 36.3% to **48.1%**. Plain repeat passes *fell* to 15.6% ([Source](https://arxiv.org/html/2508.17906v2)).
- **Different passes merged together.** Google's LangExtract defaults to 1,000-character windows and offers multiple passes "for higher recall", but publishes no numbers ([Source](https://github.com/google/langextract/blob/main/langextract/extraction.py)).

Our 8K chunks (about 2K tokens) sit near the top of GraphRAG's range, so a 4K test is worth running.

**How to use the smart model:**
1. **First read.** The cheapest approved model that passes stage 3 of the plan reads every block of every chunk. It returns updates or a short coded reason.
2. **Second look on triggers only.** The table below lists them.
3. **One gleaning turn per chunk**, on the cached chunk, if stage 4 shows it finds new facts.
4. **One full second read** with shifted cuts or a different model, during measurement only. Keep it in production only if it keeps finding facts that the triggers miss.

| Trigger (code detects it) | Action |
|---|---|
| Jev says "fact" (above a low threshold) but the reader says "none" | Stronger model re-reads the block plus its context |
| Reader says "unclear" | Same |
| Quote fails the letter-for-letter check, or unit words are missing from the evidence | Retry once, then use the stronger model |
| Model call failed or timed out | Record "not read" and retry. Never record "none" |
| Jev's probability falls in the unsure band | Stronger model |

One unknown sets this layer's cost: how many blocks Jev calls "fact" that the reader rightly skips. Jev's "fact" is broader than "Driver update". It tagged conference-call details as facts, for example. Stage 4 measures this. If the set is large, use Jev's probabilities to rank it, then audit the rest by sampling.

**Wrong facts mostly come from wrong meaning, not fake quotes.** EarningsBench found most errors came from "choosing the wrong variant of a metric", such as segment vs total or monthly vs quarterly ([Source](https://www.financialdatasets.ai/blogs/earningsbench)). Our letter-for-letter check blocks invented quotes but not real quotes with the wrong meaning. Add typed checks in code:
- unit words sit inside the evidence;
- the period comes from the column head or the verified period;
- segment vs total is stated;
- for 10-K/10-Q, numbers are cross-checked against XBRL.

**Prompt and output levers:**
- **Cache the fixed instructions.** On the API, cache reads cost 0.05–0.1x the input price ([Source](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)).
- **Use short coded reasons, not sentences.** Output costs 5x input and is roughly 40–60% of a read's cost in my estimate.
- **Ask for quotes first.** Anthropic recommends this for long documents ([Source](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)).

**Subscription caveats:**
- The Batch API's 50% discount applies to the API only ([Source](https://platform.claude.com/docs/en/build-with-claude/batch-processing)).
- How cached reads count against subscription limits is unknown.
- "Whole 10-K cached plus a marked focus window" would cost about 3.8–6.4x the input of plain chunks, and about 32x on Haiku 5.5. The 32x is because a 105K-token prompt crosses its 100K price tier (my arithmetic). Long-input evidence also points to lower recall: Chroma found every model degrades as input grows ([Source](https://www.trychroma.com/research/context-rot)). Skip it unless an A/B test says otherwise.

## Free savings come first; model-based deleting comes last

The safest savings cut smart-model tokens without any model judgement. Ranked from safe to risky:

| Lever | Possible saving | Risk to recall | Status |
|---|---|---|---|
| Short coded reasons; maybe locations instead of retyped quotes | Large share of output | None | Untested |
| Cache the fixed instructions | ~90–95% of repeated instruction input (API) | None | Proven on API; unknown on subscription |
| Exact-match boilerplate rules: contents page, signatures, EX-31/32, exhibit index, safe-harbor text identical to last time, call logistics | Part of the ~43% "nothing" words in press releases | Low; each rule checkable | Size unmeasured |
| Skip sentences identical to the last filing, only if they hold no number, date, period word or cross-reference; reuse earlier results by text hash + prompt version | Up to ~55% of repeated sentences, less after the guards | Medium; needs an elusion audit | Unmeasured after guards |
| XBRL for 10-K/10-Q statement numbers and note lookups | Statement-table tokens | Low–medium; XBRL has errors; none for 8-K releases | Unmeasured |
| Jev "nothing" filter at a certified threshold | ~10% of words on our sample | Medium until ~600 facts audited | Measured saving small |
| Cheap model only; strong model only where flagged | Large | High; no recall guarantee | Avoid as the only reader |
| Sentence dropping or compression | 2–5x | High; meaning breaks | Avoid |

**Skipping repeated text aims the reader at what moves prices.** Lazy Prices compared 327,130 pairs of consecutive filings from the same company. The median word-overlap similarity was **0.947**. Firms that *changed* their filings earned up to **188 basis points a month** less than firms that did not, and MD&A changes the most ([Source](https://www.nber.org/system/files/working_papers/w25084/w25084.pdf)). An identical sentence can still be news when:
- it says "this quarter";
- it points to a table that changed;
- it reaffirms guidance;
- text around it was deleted.

Hence the guards, and deletions logged as events of their own.

**Model-based deleting pays little at a near-100% target.** BARGAIN is the strongest published method for filtering with guarantees. It was tested at 90% recall targets. It also proves that when true items are few, no method can both guarantee a target and save much ([Source](https://arxiv.org/html/2509.02896v2)). Legal-review research adds that overshooting a recall target is a major source of extra cost ([Source](https://arxiv.org/abs/2108.12746)). On our seven documents, Jev removed only about **10% of words**:

| Document | Words Jev removed |
|---|---|
| AMG press release | 16% (hand labels would remove 44%) |
| Equity Residential press release | 52% |
| Union Pacific MD&A | 1% |
| Costco Q&A | 0% |

Keep this deferred.

## Borrowed ideas: what the shared sources add

| Idea | Source | Verdict |
|---|---|---|
| Ask "does this continue the previous one?" | Supermemory blog | **Adapt**: block level, only near cuts |
| Jev failed as a delete gate but worked as a sorter; sentence dropping broke meaning | Supermemory blog | **Adopt the lesson**: rank and flag, never delete or compress |
| A hook decides whether a query needs memory | Supermemory blog | **Later**: whole-document gates (for example, a news article not about the company), only with an audit |
| Route each request to the cheapest capable tier, ~$0.00004 and 0.4 s per decision | User-shared Riley Brown write-up (no link) | **Adapt**: route the *second look*, not the first read. The price fits Jev on a ~1K-token input (my arithmetic). Routers such as FrugalGPT and RouteLLM aim at average quality with no recall guarantee ([Source](https://arxiv.org/abs/2305.05176), [Source](https://arxiv.org/abs/2406.18665)) |
| Thresholds and rules in code; a "check manually" band | User-shared Substack review (no link) | **Adopt**: three bands; the unsure band goes to the strong reader. LOTUS cascades use the same two-threshold idea ([Source](https://lotus-ai.readthedocs.io/en/latest/approximation_cascades.html)) |
| Score questions; ~7 questions per call; background put into the input | Substack review | **Adopt** batching, plus the source header and heading path in Jev's input. **Test** Score for ranking. No counting |
| Log model-vs-rule disagreements as a growing test set | Substack reader comment | **Adopt**: every resolved trigger becomes a labelled example |
| Pack within a section; never mix tables with text; split long tables into row groups that repeat the header; keep heading path and position | [ontogr/agentic-graphrag](https://github.com/ontogr/agentic-graphrag) (user-shared) | **Adopt**, except keep each table with its own title, unit and note lines |
| Cheap extractor on every chunk; a model reviews only the least-sure chunks, within a budget | agentic-graphrag | **Avoid as the main reader**: a budget cap means silent misses. Fine as a net |
| A schema decides what survives; every citation checked against fetched text | agentic-graphrag | **Adopt**: code validates fields. Quotes are already checked |
| Matching ladder: name → fuzzy → embedding → clustering → model; undecided ≠ rejected | agentic-graphrag | **Adopt** for linking updates to existing Drivers after extraction |
| Flag decisions when a cited document changes | agentic-graphrag | **Adopt** for amended filings and edited news (58% of news texts carry a later "updated" stamp, per the project) |
| Keep verbatim quotes; discard names not found in the source | [ontogr/ontogr-agent-memory](https://github.com/ontogr/ontogr-agent-memory) (user-shared) | **Adopt**: a Driver update whose key words are not in its evidence is rejected |
| A failed model call is kept apart from an empty result | ontogr-agent-memory | **Adopt**: this is critical for honest recall bookkeeping |
| Two clocks (when the fact was true vs when it was recorded); old versions closed, never overwritten | ontogr-agent-memory | **Adopt** |
| AI verdicts stored under input hash + prompt version, stale when either changes; redo work only when the text changes | ontogr-agent-memory | **Adopt**: makes repeat-text reuse and re-runs safe and cheap |
| Escalate only when set triggers fire; unknown labels handled in strict / preferred / open mode with human approval | ontogr-agent-memory | **Adopt**: the trigger table above, and owner approval for new Driver names |

The Reddit post on Jev clarifying queries (login wall) and the video transcript were not available. Nothing is drawn from them.

## Near-100% must be measured, and the yardstick matters

**No method can promise 100%. A sample can only cap the miss rate.** If you find zero misses in n checked facts, the miss rate is at most about 3/n with 95% confidence ([Source](https://en.wikipedia.org/wiki/Rule_of_three_(statistics))). The exact counts (my calculation):

| Claim, 95% confidence | Facts checked, none missed | If 1 was missed |
|---|---|---|
| Recall ≥ 99% | 299 | 473 |
| Recall ≥ 99.5% | 598 | 947 |
| Recall ≥ 99.9% | 2,995 | 4,742 |

For scale: Jev's 0 of 119 fact/label blocks lost shows only that its loss rate is **≤ 2.5%**. The same arithmetic applies to "zero wrong facts". For example, 0 wrong among 300 checked updates means at most 1% wrong.

**The current yardstick flatters recall.** A union-of-runs answer key contains only facts that some run found. Anything every run missed is invisible, so our 48–51% single-read figures are too high as a measure of true recall. A possible reading, not tested: readers may also disagree about what counts as a Driver update. If so, a tighter definition could raise recall as much as extra reads would.

Honest measurement has three parts:
1. **A human gold set.** Every block of a few whole documents, labelled independently of model runs.
2. **An elusion audit.** People read random samples of blocks every reader marked "none".
3. **A capture-recapture estimate** from two deliberately different reads. Total ≈ found₁ × found₂ ÷ found by both. It undercounts when some facts are hard for every reader ([Source](https://en.wikipedia.org/wiki/Lincoln_index)), so the human gold set stays the anchor.

Rules for the audit:
- Count facts, not blocks.
- Certify each document type separately.
- Report wrong-meaning errors (period, segment, unit) apart from wrong-quote errors.

## A staged test plan from free checks to certified recall

Each AI reader stage needs the owner's approval of model, prompt, fixtures and cost estimate, starting with the cheapest approved model (local AI or Haiku). Claude costs below are API-equivalent and stand for subscription usage.

| Stage | What it measures | Pass bar | Expected cost |
|---|---|---|---|
| **0. Human gold set** | Every Driver update in ~8 whole documents across 5 types: 2 press releases, 1 10-Q, key 10-K sections, 2 call transcripts, a few news articles. Also facts per document, which sizes stage 6 | Every block labelled, checked by a second person, frozen with a hash before any model run | No AI cost. The largest human-time cost in the plan. Start from the 275 labelled blocks |
| **1. Code-only dry run** | (a) How many of the 51 real ties the rules alone protect, and how many joints are left for Jev. (b) Chunks whose numbers have no unit line in scope. (c) Share of repeated sentences with no number, date or period word. (d) Boilerplate share removable by exact rules. (e) XBRL coverage of statement tables | (b) = 0 | $0 |
| **2. Jev batched + first 10-K** | Batched vs per-block answers on the 275 blocks and 106 pairs, in windows of 10, 30 and 100 blocks; "rely on" vs "new topic" wording; first full 10-K tagging; cost per 1,000 blocks | 0 fact/label blocks tagged "nothing"; 0 of 51 ties split; record separations caught | Under $0.10 in Jev cash (≈ $0.003 per batched run of the 275 blocks; ≈ $0.01–0.05 per 10-K) |
| **3. Baseline single read** | Recall against the human gold set (not the union) for the cheapest model, then a Sonnet-class model on the same chunks; wrong-quote vs wrong-meaning errors; "unclear" rate; output tokens per block | Record only; pick the first-read model | Gold set ≈ 100–200K tokens: ≈ $0.05 Haiku-class, ≈ $1–2 Sonnet-class |
| **4. Recall ladder** | Added recall and cost of each layer in turn: Jev-trigger re-reads; one gleaning turn; second read with shifted cuts or another model; 4K vs 8K chunks; capture-recapture estimate; size of the "Jev fact, reader none" set | Keep a layer only if it finds gold facts the earlier layers missed | ≈ 3–5x stage 3 (≈ $3–8 Sonnet-equivalent); Jev under $0.05 |
| **5. Savings audits** | Facts hiding in skipped text (guarded repeat-skip, boilerplate rules, optionally Jev "nothing" blocks), from random samples read in full | 0 facts in a sample sized as in stage 6 | Cents of AI; human checking time |
| **6. Certify per type** | Lower bound on recall and upper bound on wrong facts, per document type | ≥ 299 gold facts all found → ≥ 99%; ≥ 598 → ≥ 99.5% | Mainly labelling, about 600 facts × 5 types. AI cost = pipeline cost per document × documents needed (stage 0 gives facts per document) |
| **7. Run and keep checking** | Rolling elusion sample (a small random share of "none" blocks re-read by the strong model); growth of the disagreement log; cache reuse | Miss rate stays inside the certified bound | A few % extra strong-model reads |

## What is proven, what is likely, what is untested

| Status | Finding |
|---|---|
| **Proven** (measured on our data or repeated outside) | Smaller chunks find more (our 8K beat 40K; GraphRAG ~2x at 600 vs 2,400 tokens) |
| | Single reads miss 17–50% even with top models |
| | Jev lost 0 of 119 fact/label blocks and split 0 of 51 real ties, but caught only 30 of 55 separations and removed ~10% of words |
| | Per-block Jev wording costs ~1,170 tokens per block |
| | Batching questions on one input: 12.2x cheaper with the same answers |
| | Tables whole plus title-start cuts beat fixed cuts in financial Q&A (measured on search, not extraction) |
| | Filings repeat heavily, and the changes carry price information |
| | On the API, output costs 5x input and cache reads 0.05–0.1x |
| **Likely** (inferred from evidence) | Code rules can place most cuts, with Jev needed only at prose joints near a cut |
| | Code-copied context is as good as model-written context |
| | Jev-triggered re-reads capture most of a full second strong read at a fraction of the usage |
| | Guarded repeat-skip is safe |
| | XBRL note blocks resolve "see Note X" |
| | Wrong meaning is the main precision risk |
| **Untested** | Batched Jev accuracy at 30–100-block windows |
| | Jev routing between model tiers; Score questions for ranking |
| | Gleaning gain per round |
| | 4K vs 8K for extraction |
| | Returning locations instead of retyped quotes |
| | Whole-document-cached focus window (evidence leans against) |
| | Local boundary models such as Chonky, or perplexity dips |
| | Per-Driver-type prompts |
| | A certified Jev "nothing" filter |
| | Supermemory-style sentence chunking on filings |

## Conclusion

The economics turn the usual question around. Jev is so cheap that the question is not "how much Jev can we afford?" but "where should Jev send Claude?" Spending Jev to trim what Haiku reads roughly breaks even. Spending it to decide where a Sonnet-class model takes a second look can save most of a full second read. In this design Jev's job is to flag and rank; deleting text is left to code rules that a person can check, and Jev has no part in it.

The real bottleneck is measurement, not chunking. The human gold set is the costliest and most valuable item in the plan, because everything else, from chunk size to escalation rules to repeat-skip, is judged against it. The disagreement log turns everyday running into a growing answer key at almost no extra cost. One rule should govern every addition: a layer stays only if it finds gold facts the earlier layers missed. That rule, not any single model or cut size, is what moves recall toward 100% at the lowest cost.
