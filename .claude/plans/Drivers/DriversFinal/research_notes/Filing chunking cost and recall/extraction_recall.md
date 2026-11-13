# Extraction recall and grounding in long-document LLM extraction (research notes, 11 Nov 2026)

Plain-word key used below:
- **Recall** = share of the true facts that were found. **Precision** = share of returned facts that are correct.
- **Gleaning** = asking the model again "you missed some, add them" on the same text.
- **Prompt caching** = re-sending an identical text prefix at a fraction of the normal input price.
- **Needle test** = hide known facts ("needles") in long filler text and check how many come back.
- Items marked **[unverified]** came from a search-engine summary or a page I could not open; treat their numbers with care.

---

## Q1. Chunk / context size vs extraction recall

### Takeaway
Every source found says the same thing: the more text a model reads at once, the more facts it silently drops, and dropping gets worse as the number of facts to find grows. Precision usually stays high while recall falls. This matches the project's own result (8K-character chunks beat 40K) and is consistent across 2023–2026 evidence, including the newest frontier models.

### Cited Findings
**Classic studies**
- Lost in the Middle (Liu et al.; TACL; arXiv v1 6 Jul 2023): "performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts, even for explicitly long-context models." The abstract gives no numbers. — [arXiv 2307.03172](https://arxiv.org/abs/2307.03172)
- RULER (COLM 2024): "We evaluate 17 long-context LMs with 13 representative tasks"; "While these models all claim context sizes of 32K tokens or greater, only half of them can maintain satisfactory performance at the length of 32K." — [arXiv 2404.06654](https://arxiv.org/abs/2404.06654)
- LangChain multi-needle test (13 Mar 2024, GPT-4 128K): "Performance degrades as the number of needles increases from 1 to 10" and "as the context increases from 1000 to 120,000 tokens." "GPT-4 consistently retrieves needles towards the end while ignoring needles at the beginning." The drop starts "around 25k tokens" with many needles versus "around 73k tokens" with one needle. With 10 needles in a 24,800-token context, the answer contained only 4 of 10, and they were "the last four needles placed in our context." Reasoning over the found needles scored below plain retrieval, so "retrieval may set an upper bound on reasoning performance." — [LangChain blog](https://www.langchain.com/blog/multi-needle-in-a-haystack)
- NoLiMa (ICML 2025; needles with no word overlap with the question): at 32K, 11 of 13 models fell below 50% of their short-context score; GPT-4o fell from 99.3% to 69.7%. Llama 3.3 70B on the hard subset fell from 98.3 to 8.9 at 32K. **[unverified: from search summary of the paper + dataset README; full paper not opened]** — [arXiv 2502.05167](https://arxiv.org/html/2502.05167v3); [HF README](https://huggingface.co/datasets/amodaresi/NoLiMa)

**"Context rot" (Chroma, 14 Jul 2025; Hong, Troynikov, Huber)**
- 18 models were tested, including Claude Opus 4, Sonnet 4, Sonnet 3.7, Sonnet 3.5, Haiku 3.5, o3, GPT-4.1, and Gemini 2.5 Pro/Flash. "model performance consistently degrades with increasing input length." — [Chroma report](https://www.trychroma.com/research/context-rot)
- "Even a single distractor reduces performance relative to the baseline (needle only)"; four distractors make it worse. (Distractor = a similar-looking but wrong fact.) — [Chroma](https://www.trychroma.com/research/context-rot)
- On LongMemEval, focused prompts average about 300 tokens and full prompts about 113K tokens: "Across all models, we see significantly higher performance on focused prompts compared to full prompts." "The Claude models exhibit the most pronounced gap between focused and full prompt performance," mostly because they **abstain** (decline to answer). — [Chroma](https://www.trychroma.com/research/context-rot)
- Surprisingly, "models perform better on shuffled haystacks than on logically structured ones." — [Chroma](https://www.trychroma.com/research/context-rot)

**Extraction-specific (closest to our task)**
- GraphRAG (Microsoft, 2024): with GPT-4 on HotPotQA, "GPT-4 extracted almost twice as many entity references when the chunk size was 600 tokens than when it was 2400"; "the LLM tends to extract few entities from chunks of larger size." — [arXiv 2404.16130](https://arxiv.org/html/2404.16130v2)
- Oolong (CMU, Nov 2025; long-context counting/aggregation): no model scores above 50% at 128K, including GPT-5, Claude Sonnet 4 and Gemini 2.5 Pro. At 1K–4K tokens no model exceeds 85%. **[unverified: search summary]** — [arXiv 2511.02817](https://arxiv.org/abs/2511.02817)
- LEDGER (11 Jun 2026): 4,999 corporate annual reports, average **126,274 tokens**, 31 KPIs each. The whole report is read in one pass. Best multi-KPI recall is 77.2 with 85.7 precision (Qwen3.6-27B). "no model exceeds 80% recall." Doing well on a single-value lookup "does _not_ transfer" to full extraction: Ministral went from 87.9 to 41.4 recall. Only open-weight models were tested. — [arXiv 2606.13100](https://arxiv.org/html/2606.13100)
- LongExtractionBench (micro1, 2026; **vendor-commissioned by Reducto, the winner**): 225 table-heavy documents averaging 358 pages, scored by a deterministic grader. Frontier models called directly had high precision but low recall (completed docs only):

  | System | Precision | Recall |
  |---|---|---|
  | GPT-5.5 | 95.8% | 52.7% |
  | Claude Opus 4.8 | 92.0% | 70.7% |
  | Gemini 3.1 Pro | 95.8% | 48.6% |
  | Reducto (dedicated pipeline) | 99.6% | 99.6% |

  On the 61 documents every system finished, frontier recall was 73.2–77.8%. Frontier failures came from "output-token limits, context overflow, and page caps." — [micro1 LongExtractionBench](https://www.micro1.ai/benchmark/long-extraction)
- "You don't need long context" (arXiv, 3 Nov 2026): keeping contexts short through selective reading and frequent compaction left accuracy "broadly flat." Relative to full input, Opus 4.5 ranged "from -0.4 to +40.0ppts" across seven long-input benchmarks, at "6.5x to 54.6x" lower estimated cost. "Later tokens are costlier to generate than earlier tokens," up to 7x on open-weight models. Per-benchmark tables were not read. — [arXiv 2611.05306](https://arxiv.org/html/2611.05306)

### Inferences
- The pattern "high precision, recall ~50–80%" appears in LongExtractionBench, LEDGER, and the KPI benchmark in Q7. It is the same as our own result (Sonnet 48.3% / Opus 51.3% of the union at 8K). A single read missing about half of what several reads find is normal, not a sign of a broken prompt.
- Recall loss grows with **how many facts** must be found, not only with length (LangChain 1→10 needles; Oolong aggregation). A 10-K section dense with metrics behaves like a many-needle test even inside a small chunk.
- Chroma's finding that Claude models abstain more in long context suggests a specific risk for the "reason for none" design: in a long input, a Claude reader may say "none" on blocks it did not really check. This is an inference, not measured for extraction.
- Distractors matter for filings: prior-year columns, segment vs total, and GAAP vs non-GAAP are natural distractors. More surrounding text means more of them.

### Gaps
- Exact Lost-in-the-Middle accuracy numbers: the abstract has none, and I did not open the full paper.
- No study found that sweeps chunk size (e.g. 2K/4K/8K/16K characters) for **exhaustive fact extraction** with frontier 2026 models. GraphRAG's 600-vs-2400-token result (GPT-4, 2024) is the only direct chunk-size-vs-extraction-count measurement found.
- NoLiMa and Oolong numbers are from search summaries.

---

## Q2. Google LangExtract: chunking, passes, parallelism, grounding

### Takeaway
LangExtract's recall recipe is: small chunks (default **1,000 characters**), several independent passes merged as a union, and many parallel workers. Grounding comes from mapping every extraction back to character offsets. Google publishes **no recall numbers**. The "85% / 93% / 96% recall for 1/2/3 passes" figures that circulate online come from an unsourced blog, not Google.

### Cited Findings
- From the source code (`extraction.py`): the defaults are `max_char_buffer: int = 1000` and `extraction_passes: int = 1`. The docstring says passes are "sequential extraction attempts to improve [recall]… merges non-overlapping results (first extraction wins for overlaps). WARNING: Each additional pass reprocesses tokens, potentially increasing API costs." — [langextract/extraction.py](https://github.com/google/langextract/blob/main/langextract/extraction.py)
- Merge rule (`annotation.py`, `_merge_non_overlapping_extractions`): "When extractions from different passes overlap in their character positions, the extraction from the earlier pass is kept (first-pass wins strategy). Only non-overlapping extractions from later passes are added." — [langextract/annotation.py](https://github.com/google/langextract/blob/main/langextract/annotation.py)
- Grounding statuses in code: `MATCH_EXACT`, `MATCH_GREATER`, `MATCH_LESSER`, `MATCH_FUZZY` (`AlignmentStatus` in `langextract/core/data.py`). If an extraction cannot be located, its `char_interval` is `None`. — [core/data.py](https://github.com/google/langextract/blob/main/langextract/core/data.py); [README](https://github.com/google/langextract)
- The README example uses `extraction_passes=3` ("Improves recall through multiple passes"), `max_workers=20` ("Parallel processing for speed") and `max_char_buffer=1000` ("Smaller contexts for better accuracy"). It claims the library handles the "needle-in-a-haystack" problem "by using an optimized strategy of text chunking, parallel processing, and multiple passes for higher recall." The example model id shown on 11 Nov 2026 is `gemini-3.5-flash`. — [README](https://github.com/google/langextract)
- Chunking "respect[s] text delimiters (such as paragraph breaks)." Each pass is an independent run: "Each pass uses identical parameters and processing." The Romeo and Juliet example (147,843 characters, about 44,000 tokens) produced 4,088 entities, with no recall measured. A footnote says "performance can vary in multi-fact retrieval scenarios." — [longer_text_example.md](https://github.com/google/langextract/blob/main/docs/examples/longer_text_example.md)
- The "~85% / ~93% / ~96% recall" figures for 1/2/3 passes come from a blog by G. P. Santopaolo (17 Dec 2025). It gives **no source or method**; its only measured check was 50 extractions for precision and position. — [genmind.ch](https://genmind.ch/posts/LangExtract-Production-LLM-Powered-Information-Extraction/)

### Inferences
- LangExtract's merge is a **union keyed on text position**. That suits our block design: a block already gives a stable location, so a union of passes keyed on (block, quote span) is simple.
- Its "first pass wins on overlap" rule means later passes can only **add** facts, never fix a wrong one. A precision guard still has to come from somewhere else; in our design that is the letter-for-letter quote check plus a semantic check.
- A 1,000-character default is about 8× smaller than our 8,000-character chunk. Google's own tool leans toward very small windows for recall.
- Our letter-for-letter check equals LangExtract's `MATCH_EXACT` only. LangExtract also accepts fuzzy and partial matches, so it is **looser** than our check.

### Gaps
- No published LangExtract recall or precision, and no published cost-per-pass curve.
- I did not find how LangExtract chooses chunk breaks beyond "respects delimiters."

---

## Q3. Microsoft GraphRAG "gleanings"

### Takeaway
Gleaning re-asks the model on the same chunk: first a forced yes/no "did you miss anything?", then "MANY entities were missed, add them." Microsoft says this lets larger chunks match small-chunk extraction counts, but published no numbers per gleaning round. Each round costs at least one more call per chunk. Independent measurements are thin; one ablation found little gain on explicit text.

### Cited Findings
- Chunks were 600 tokens with 100-token overlap (Podcast corpus: "1669 × 600-token text chunks"). "Longer text chunks require fewer LLM calls … (which reduces cost)" but recall degrades. — [arXiv 2404.16130](https://arxiv.org/html/2404.16130v2)
- The method: the model is asked whether all entities were extracted, "using a logit bias of 100 to force a yes/no decision." If it says some were missed, a continuation stating that "MANY entities were missed in the last extraction" asks for more, repeated "up to a specified maximum number of times." This "allows us to use larger chunk sizes without a drop in quality (Figure 3)." Figure 3 compares 600/1200/2400-token chunks; the paper text gives no numbers. — [arXiv 2404.16130](https://arxiv.org/html/2404.16130v2)
- Exact prompts in the current repo (`extract_graph.py`): CONTINUE_PROMPT = "MANY entities and relationships were missed in the last extraction. Remember to ONLY emit entities that match any of the previously extracted types. Add them below using the same format:" and LOOP_PROMPT = "It appears some entities and relationships may have still been missed. Answer Y if there are still entities or relationships that need to be added, or N if there are none. Please answer with a single letter Y or N." — [graphrag prompts](https://github.com/microsoft/graphrag/blob/main/packages/graphrag/graphrag/prompts/index/extract_graph.py)
- Config: `max_gleanings` is "The maximum number of gleaning cycles to use" (for both entity and claim extraction). — [GraphRAG config docs](https://github.com/microsoft/graphrag/blob/main/docs/config/yaml.md)
- Independent evidence: the CogCanvas ablation found "Gleaning provides minimal benefit on LoCoMo," likely because the text is explicit. Another write-up describes gleaning as adding "one LLM call per chunk per pass." **[unverified: search summaries]** — [CogCanvas arXiv 2601.00821](https://arxiv.org/html/2601.00821v2); [post-graph-rag arXiv 2608.24921](https://arxiv.org/pdf/2608.24921)
- DocETL measured that gleaning "doubles operation cost" in one task. — [DocETL arXiv 2410.12189](https://arxiv.org/html/2410.12189v3)

### Inferences
- Gleaning is a cheap form of "multiple passes": the second request re-sends the same chunk plus the first answer. With prompt caching, the re-sent chunk costs about 0.05–0.1× (Q5), so a gleaning round costs mainly **output tokens**.
- The yes/no gate stops paying for extra rounds when the model believes it is done. But a model that already missed facts may also wrongly answer "N", so the gate saves cost at some recall risk. Not measured.
- GraphRAG treats gleaning as a way to use **bigger** chunks at small-chunk recall. Whether gleaning on 8K-character chunks beats simply using 4K-character chunks is untested.

### Gaps
- No published recall gain per gleaning round (0 vs 1 vs 2) on any benchmark. GraphRAG's Figure 3 numbers are not in the text.
- The default value of `max_gleanings` was not verified in this session.

---

## Q4. DocETL (UC Berkeley): split / gather with peripheral context

### Takeaway
DocETL's Gather step gives each chunk a reconstructed **header path** (all section headings above it) plus chosen pieces of earlier and later chunks. Its optimizer's biggest recall gain on legal contracts (+67%) came from **splitting the task per field** ("isolated projection"), not from chunking the document. Accuracy gains came with 10–18× higher run cost than the plain pipeline.

### Cited Findings
- Split cuts by token count or delimiter. Gather attaches "peripheral" context: "previous" and "next" sections, each with optional "head", "middle" and "tail" parts. A `doc_header_key` rebuilds headings: the operation "examines the doc_header_key field for every chunk preceding the one being rendered" to recover the header hierarchy. Example: chunk 20 of a 74-page contract receives the latest heading at each level above it. — [arXiv 2410.12189 v3 (Appendix A, Fig. 6)](https://arxiv.org/html/2410.12189v3)
- Gleaning in DocETL is a validator loop: Map → (validate → improve) up to k rounds. — [arXiv 2410.12189](https://arxiv.org/html/2410.12189v3)
- Legal contracts (50 contracts, Table 2):

  | Pipeline | Precision | Recall | F1 | Hallucination | Run cost |
  |---|---|---|---|---|---|
  | DocETL optimized | 0.401 | 0.719 | 0.477 | 0.000 | $1.46 |
  | DocETL unoptimized | 0.341 | 0.430 | 0.379 | 0.072 | $0.08 |
  | LOTUS | 0.402 | 0.471 | 0.393 | 0.073 | $0.07 |

  The authors cite "a 67% improvement in recall over the unoptimized DocETL pipeline—with no hallucinations." Optimizer cost was $1.58. The optimizer "chose isolated projection" over document chunking, "suggesting that LLMs excel at focused extraction of small amounts of information." — [arXiv 2410.12189](https://arxiv.org/html/2410.12189v3)
- Declassified articles: distinct locations found rose from 298 to 435 (+46%) using a "batched fold" that lets "the LLM … incrementally process and track distinct locations." — [arXiv 2410.12189](https://arxiv.org/html/2410.12189v3)
- Police misconduct: split into 12,840-token chunks plus gather; accuracy was 1.34× the baseline; cost $1.35 vs $2.24 baseline; the optimizer itself cost about $100. — [arXiv 2410.12189](https://arxiv.org/html/2410.12189v3)
- Headline gain: the v3 abstract says "25 to 80% more accurate," while the body says "21 to 80%." The paper also says "233 distinct event types" in the text but 164 in Table 5. These are internal inconsistencies. — [arXiv abs](https://arxiv.org/abs/2410.12189); [HTML](https://arxiv.org/html/2410.12189v3)

### Inferences
- Our "section titles / unit lines carried as context only" equals DocETL's `doc_header_key` header path. DocETL adds optional pieces of the neighbouring chunks, which would cover a table whose unit line or caption sits just before the chunk break.
- "Focused extraction of small amounts of information" works better than "everything at once." That supports narrow per-block decisions (our design). It also suggests a further split by fact **type** (metrics / guidance / surprises / one-offs) if recall stays low. Each split multiplies cost, though.

### Gaps
- The paper does not isolate the effect of Split+Gather on recall versus whole-document input.
- No per-round gleaning gain is reported.

---

## Q5. "Whole document as cached context + extract only from a marked focus window," and caching economics

### Takeaway
I found **no published test** showing that "full document in context + extract only from a marked window" keeps small-chunk recall. The evidence that full context lowers recall (Chroma focused vs full; distractors; multi-needle) is a warning against it. With caching, this design costs about **3.8–6.4× the input cost** of plain chunking per 10-K, before output. On Haiku 5.5 it is about **32×**, because a 105K-token prompt crosses the 100K long-prompt price tier. The closest real-world use of the pattern is Anthropic's Contextual Retrieval, which writes chunk context for search, not extraction.

### Cited Findings
**Pattern evidence**
- Anthropic Contextual Retrieval (19 Sep 2024): the prompt contains "<document> {{WHOLE_DOCUMENT}} </document>" plus "Here is the chunk we want to situate within the whole document," with Claude 3 Haiku. "the one-time cost to generate contextualized chunks is $1.02 per million document tokens," "Assuming 800 token chunks, 8k token documents, 50 token context instructions, and 100 tokens of context per chunk." Search misses fell 35%, 49% and 67% (5.7% → 3.7% / 2.9% / 1.9%). — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- Anthropic long-context guidance (for 20K+ token inputs): "Place your long documents and inputs near the top of your prompt, above your query, instructions, and examples." "Queries at the end can improve response quality by up to 30 percent in tests, especially with complex, multidocument inputs." It also advises: "Ground responses in quotes … ask Claude to quote relevant parts of the documents first." — [Claude prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- Against: Chroma reports "significantly higher performance on focused prompts" (~300 tokens) than full prompts (~113K tokens), and that a single distractor lowers performance. — [Chroma](https://www.trychroma.com/research/context-rot)

**Caching rules and prices (raw docs read 11 Nov 2026)**
- Multipliers on base input price: 5-minute cache write 1.25×, 1-hour write 2×, cache read 0.1×. "Cache hits and refreshes on Claude Opus 5.5 and Claude Sonnet 5.5 are priced at 0.05x." Claude Fable/Mythos 5.x reads cost 0.025×. — [Prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- "Cache hits require 100 percent identical prompt segments … up to and including the block marked with cache control." There are up to 4 breakpoints, and the default TTL is 5 minutes, "refreshed for no additional cost each time the cached content is used." "a cache entry only becomes available after the first response starts. If you need cache hits for parallel requests, wait for the first response before sending subsequent requests." — [docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- Minimum cacheable length is 512 tokens for Opus 5.5 / Sonnet 5.5 / Haiku 5.5, 1,024 for Sonnet 4.6, and 4,096 for Haiku 4.5. — [docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- "On a model priced by prompt length, cache reads and cache writes count toward a request's prompt length." — [docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- Prices per million tokens:

  | Model | Input | 5m write | Cache read | Output |
  |---|---|---|---|---|
  | Opus 5.5 | $4 | $5 | $0.20 | $20 |
  | Sonnet 5.5 | $2 | $2.50 | $0.10 | $10 |
  | Sonnet 4.6 | $3 | $3.75 | $0.30 | $15 |
  | Haiku 5.5 (≤100K-token prompt) | $0.10 | $0.125 | $0.01 | $0.50 |
  | Haiku 5.5 (>100K-token prompt) | $0.50 | $0.625 | $0.05 | $2.50 |
  | Haiku 4.5 | $1 | $1.25 | $0.10 | $5 |

  — [docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

### Inferences
**Cost per 10-K, input side only.** This is my arithmetic. It assumes 105K tokens per 10-K, about 4 characters per token, so 8,000 characters ≈ 2K tokens ≈ 52 windows. Instructions and output are excluded.

| Model | A: plain 8K-char chunks (each token read once) | B: whole doc cached + 52 windows (1 write + 51 reads) | B ÷ A |
|---|---|---|---|
| Haiku 5.5 | $0.0105 | $0.333 (doc >100K tokens → long tier) | ~32× |
| Haiku 5.5, doc trimmed below 100K | $0.0105 | $0.067 | ~6.4× |
| Sonnet 5.5 | $0.21 | $0.80 | ~3.8× |
| Sonnet 4.6 | $0.315 | $2.00 | ~6.4× |
| Opus 5.5 | $0.42 | $1.60 | ~3.8× |
| Jev (one full pass, $0.042/M) | $0.0044 | n/a | n/a |

- **Output is probably the bigger cost in both designs.** Output costs 5× input on every listed model, and the "every block gets a reason" rule produces output for every block. Example: ~25 tokens per block ≈ 125 input-token-equivalents per block. Short coded reasons (an enum, not a sentence) cut this directly.
- **Instruction overhead in design A.** A ~3K-token instruction block repeated over 52 chunks is ~156K tokens, more than the 10-K itself. Caching the instruction prefix (≥512 tokens on 5.x models, ≥4,096 on Haiku 4.5) cuts it to about 0.05–0.1×. This is likely the cheapest real saving available in the current design. The instruction size is my assumption.
- **Fan-out timing.** Send the first window, wait for its response to start, then fan out the rest in parallel within the 5-minute TTL.
- **Recall risk in B.** Whole-document context brings back exactly the long-input conditions shown to lower recall and add distractors. It also creates a new error: quoting a fact from **outside** the window. Code would need to reject quotes not inside the window's blocks.
- **Cheaper alternative for distant context.** Distant footnotes and unit lines could use DocETL-style gather instead: a header path, plus a small neighbour slice, plus a code-side lookup of referenced notes (e.g. "see Note 7" → attach Note 7's first block). This is untested.

### Gaps
- No direct evidence, for or against, on extraction recall for "full cached context + marked focus window" vs plain small chunks. It needs our own A/B test on the same gold set.
- The Batch API discount stacks with caching, but its size was not verified here. The docs warn that cache hits in batches are "best-effort."

---

## Q6. Forcing exhaustiveness: enumeration, checklists, structured output, extract-then-verify, union of runs, cheap cross-checks

### Takeaway
The methods with real evidence of raising recall are: smaller inputs, more independent passes merged as a union, re-asking ("gleaning"), and splitting the task into narrow pieces. All of them multiply calls, and union raises recall at some precision cost. Verification steps (chain-of-verification, agreement filters, schema checks) mainly protect **precision**. Agreement between runs does not prove correctness.

### Cited Findings
- **Union of passes:** LangExtract unions passes ("first extraction wins for overlaps"), with no published gain per pass. — [extraction.py](https://github.com/google/langextract/blob/main/langextract/extraction.py)
- **Union cost to precision:** in a screening study, a liberal union of two LLM runs "would have recovered 276 verified eligible records (87.3%) while retaining 548 benchmark records (48.5%)." **[unverified: search snippet; paper not opened]** — [arXiv 2608.26885](https://arxiv.org/html/2608.26885)
- **Agreement ≠ correctness:** "high self-consistency does not prove clinical correctness," but low self-consistency shows sensitivity to sampling noise. **[search summary]** — [arXiv 2504.12326](https://arxiv.org/pdf/2504.12326)
- **Gleaning / re-ask:** GraphRAG's re-ask loop (Q3); DocETL's validator loop doubled cost (Q4). — [GraphRAG](https://arxiv.org/html/2404.16130v2); [DocETL](https://arxiv.org/html/2410.12189v3)
- **Narrow task decomposition:** DocETL's optimizer picked per-field "isolated projection," and recall went from 0.430 to 0.719 with zero hallucination. A "batched fold" that tracks found items incrementally raised distinct items found from 298 to 435. — [DocETL](https://arxiv.org/html/2410.12189v3)
- **Schema constraints:** in LEDGER, Nemotron's recall "recovers once schema constraints suppress its scaling error" (a unit-scaling error). — [LEDGER](https://arxiv.org/html/2606.13100)
- **Extract-then-verify:** Chain-of-Verification (2023) drafts an answer, plans verification questions, answers them "independently so the answers are not biased by other responses," and revises. It "decreases hallucinations across a variety of tasks, from list-based questions from Wikidata, closed book MultiSpanQA and longform text generation." The abstract gives no numbers. — [arXiv 2309.11495](https://arxiv.org/abs/2309.11495)
- **Selective reading:** short-context selective reading matched or beat full input (−0.4 to +40.0 points for Opus 4.5) at 6.5–54.6× lower cost. — [arXiv 2611.05306](https://arxiv.org/html/2611.05306)
- **Quote-first prompting** is recommended by Anthropic for long documents. — [Claude docs](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

### Inferences
- Our "every block gets an update or a stated reason for none" rule is a checklist enumeration. It turns silent skips into explicit, auditable claims. That is what makes cheap cross-checks possible (Jev "fact" vs reader "none").
- No source measures a cheap classifier used as a **recall net** for an LLM extractor. The closest proven practice is legal e-discovery (Q8): a cheap model ranks items, then humans sample the "discard" pile. Jev's yes/no tags fit that role. Its value depends on Jev's own recall on fact-bearing blocks, which must be measured.
- Union of runs is the most direct recall lever, but the gains overlap. Our own data (single read ≈ half the union) does not say how many more facts a 3rd or 4th read adds. That diminishing-returns curve is the key unknown for cost.
- Runs are more useful when they **differ** (different model, prompt, or chunk boundaries), because identical runs tend to miss the same items. This links to capture-recapture independence (Q8).

### Gaps
- No controlled study found that measures recall per extra pass for document fact extraction (1→2→3 passes).
- No measured numbers for per-sentence vs per-document prompting on extraction recall.
- No study measuring a cheap yes/no classifier as a second-chance recall check for an LLM extractor.

---

## Q7. Extraction from financial filings: accuracy now and what helped

### Takeaway
On financial documents, current frontier models are **accurate on what they return (~95–99%) but miss 17–27% of KPIs** in the best clean tests, and do worse on long reports. The dominant wrong-value error is picking the wrong **variant** of a metric (segment vs total, quarterly vs monthly), not inventing numbers. No benchmark found scores extraction of guidance or "surprise vs expectations" facts.

### Cited Findings
- **EarningsBench** (Financial Datasets, 29 Jun 2026; **vendor**; 60 earnings releases, 12 sectors, checked by hand):

  | Model | Accuracy | Recall | Cost per release |
  |---|---|---|---|
  | Opus 4.6 (thinking) | 99.3% | 80% | $0.249 |
  | Opus 4.6 | 98.9% | 83% | $0.200 |
  | Sonnet 4.6 (thinking) | 97.2% | 83% | $0.156 |
  | Sonnet 4.6 | 95.3% | 80% | $0.117 |
  | GPT 5.4 (high) | 98.4% | 80% | $0.210 |
  | GPT 5.4 (medium) | 97.2% | 73% | $0.132 |

  Most errors came from "choosing the wrong variant of a metric the release reported in more than one way," for example "segment vs. total, monthly vs. quarterly, consolidated vs. pro-rata." The authors say 99.3% "does not meet their 100% bar," so they add more validation before production. — [Financial Datasets](https://www.financialdatasets.ai/blogs/earningsbench)
- **LEDGER** (Jun 2026; annual reports averaging 126K tokens): best recall/precision 77.2/85.7; "no model exceeds 80% recall"; Ministral emitted "many hallucinated cells." — [arXiv 2606.13100](https://arxiv.org/html/2606.13100)
- **KPI extraction from earnings calls** (ACL Industry 2026): an LLM system for open-ended KPI extraction from call transcripts was "verified by human evaluation (79.7% precision)." ECB-A has "2,460 expert annotation groups"; "encoder-based models struggle with the domain shift." — [arXiv 2605.03147](https://arxiv.org/abs/2605.03147); [ACL Anthology](https://aclanthology.org/2026.acl-industry.100/)
- **Fin-RATE** (v4 Jun 2026): 17 LLMs on SEC filings; "accuracy dropping by 18.60% and 14.35% as tasks shift from single-document reasoning" to cross-company and across-time tasks, with "comparison hallucinations, temporal and entity mismatches." — [arXiv 2602.07294](https://arxiv.org/abs/2602.07294)
- **FinanceBench** (Nov 2023): "GPT-4-Turbo used with a retrieval system incorrectly answered or refused to answer 81% of questions." Long context windows helped but are "unrealistic for enterprise settings due to increased latency and cannot support larger financial documents." — [arXiv 2311.11944](https://arxiv.org/abs/2311.11944)
- **DocFinQA**: context grows "from under 700 words in FinQA to 123k words"; "models particularly struggle on these documents" (the longest ones). — [arXiv 2401.06915](https://arxiv.org/abs/2401.06915)
- Lead not opened: tracking guidance signals across S&P 100 transcripts (2010–2024) with Gemini 2.5 Pro. — [arXiv 2510.03195](https://arxiv.org/pdf/2510.03195)

### Inferences
- Even on short 8-K-style earnings releases (similar to our ~22K-character press releases), Opus-class models found about 80–83% of KPIs in one read. Our target of near-100% recall therefore **cannot come from model choice alone**; it needs multiple reads plus checks.
- The main precision risk for us is not a fabricated quote; our letter-for-letter check already blocks that. It is a **real quote attached to the wrong meaning**: wrong period, segment instead of total, or a scale/unit error. A quote check cannot catch this. It needs a typed check of period, unit and scope against the quote and nearby header.

### Gaps
- No benchmark found for extracting **guidance** (ranges, raises/cuts) or **surprise vs consensus** statements with exact quotes.
- No financial benchmark compares chunked vs whole-document extraction recall head-to-head.

---

## Q8. What is realistically achievable, and how to measure "near-100%"

### Takeaway
Nothing found guarantees 100% recall. The only ~99.6% recall figure comes from a dedicated pipeline on a benchmark its maker commissioned. Practitioners in legal e-discovery measure recall with **random-sample audits of the "nothing found" pile** ("elusion tests") and report a confidence range. Capture-recapture between two independent runs can estimate how many facts **no run** found. A union-of-runs gold set cannot see those facts, so it overstates recall.

### Cited Findings
- Best reported: Reducto 99.6% recall / 99.6% precision on LongExtractionBench, which "Reducto commissioned." Reducto also wrote parts of the method and grading harness. — [micro1](https://www.micro1.ai/benchmark/long-extraction)
- **Elusion test:** a random sample of items not selected for production. In one example, a 1,078-document sample containing 3 relevant documents gave a 95% interval for the elusion rate of 0.06% to 0.81%. Sample size needed "is inversely proportional to the prevalence." Typical practice uses 95% confidence with a 2–5% interval. **[search summaries of practitioner articles]** — [ACEDS part I](https://aceds.org/there-is-no-one-size-fits-all-sample-size-appropriate-for-tar-validation-part-i/); [ACEDS part II](https://aceds.org/there-is-no-one-size-fits-all-sample-size-appropriate-for-tar-validation-part-ii/); [arXiv 2106.09871](https://arxiv.org/pdf/2106.09871v1.pdf)
- **Capture-recapture (Lincoln index):** with two independent methods finding E1 and E2 items and S in common, total N ≈ E1·E2 / S. The Chapman correction is less biased. It fails "if there is a sub-population that is much more difficult to find," because both searches then look complete and accuracy is overestimated. — [Wikipedia: Lincoln index](https://en.wikipedia.org/wiki/Lincoln_index); [arXiv 1205.1150](https://arxiv.org/pdf/1205.1150)
- Applied to AI agents on 294 CUAD contracts, the estimate reportedly "landed within 2 points of true recall for most agents with a 10% hand audit." **[unverified: page returned 403; search snippet only]** — [Towards Data Science](https://towardsdatascience.com/how-to-estimate-the-recall-of-ai-agents-with-capture-recapture/)

### Inferences
- **Union-of-runs gold is biased.** Its denominator holds only facts some run found, so measured recall is an upper bound. Our 48–51% "single-read recall" is therefore an **overestimate** of true single-read recall.
- **Honest measurement needs three parts:**
  1. A small human-read gold set covering every block of a few whole documents (one 8-K, one 10-Q, one 10-K section, one transcript), independent of any model run.
  2. An elusion audit: random samples of blocks every reader marked "none", checked by a human.
  3. A capture-recapture estimate between deliberately **different** runs (different model, prompt, or chunk boundaries), to estimate facts nobody found.
- **Rule of three** (standard statistics, not fetched here): finding 0 misses in n random audited items gives a 95% upper bound on the miss rate of about 3/n. To claim "<1% missed" at 95% confidence takes about 300 audited fact-bearing items with zero misses.

### Gaps
- No public source reports a long-document LLM extraction system verified at ≥99% recall by an **independent** evaluator.
- The CUAD capture-recapture accuracy claim could not be opened.

---

## Implications for the design above

### Takeaway
Keep small chunks and the per-block "update or reason" rule; the evidence backs both. The cheapest recall gains are:
1. Cache the instruction prefix.
2. Add a second **different** read, plus targeted re-reads of blocks where Jev and the reader disagree.
3. Add gleaning on cached chunks.

Do **not** adopt "whole 10-K cached + focus window" without an A/B test. It costs about 3.8–32× more input, and the long-context evidence points to lower recall. Measure recall with a human gold set, an elusion audit and capture-recapture, not with the union of model runs.

### Cited Findings
- Smaller windows find more: GraphRAG found almost 2× more at 600 vs 2,400 tokens; LangExtract defaults to 1,000 characters; our own test found 8K-character chunks beat 40K. — [GraphRAG](https://arxiv.org/html/2404.16130v2); [LangExtract code](https://github.com/google/langextract/blob/main/langextract/extraction.py)
- Single reads miss 17–50% even for frontier models on financial documents. — [EarningsBench](https://www.financialdatasets.ai/blogs/earningsbench); [LEDGER](https://arxiv.org/html/2606.13100); [LongExtractionBench](https://www.micro1.ai/benchmark/long-extraction)
- Cache reads cost 0.05–0.1× input; output costs 5× input; Haiku 5.5's price jumps 5× above 100K-token prompts. — [Prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- The dominant wrong-value error is the wrong metric variant. — [EarningsBench](https://www.financialdatasets.ai/blogs/earningsbench)

### Inferences
**Recall gained per dollar, best first (my ranking from the evidence above; must be tested):**

| # | Change | Why it should help | Rough cost |
|---|---|---|---|
| 1 | Cache the fixed instruction + examples prefix | No recall change, but frees budget for extra reads | Cuts repeated-instruction input to 0.05–0.1× |
| 2 | Jev full pass + re-read only "Jev says fact, reader says none" blocks with a stronger model | Targets the misses; Jev costs ~$0.0044 per 10-K | Small: only disputed blocks re-read |
| 3 | One gleaning turn per chunk ("list any blocks you marked none that contain a metric/guidance/surprise/one-off"), with the chunk cached | Re-ask is the cheapest second look | Mostly output tokens |
| 4 | Second full read that **differs** (shifted chunk boundaries, or a different model tier) | Union across diverse reads is the main proven recall lever; diversity also enables capture-recapture | ~1× extra per read |
| 5 | Shorter coded "reason for none" (enum + optional short note) | Output is 5× input price and is spent on every block | Lowers cost |
| 6 | DocETL-style gather: header path + neighbour slice + code lookup of referenced notes ("see Note 7") | Covers distant footnotes and unit lines without the whole document | Small |
| 7 | Whole-doc cached + focus window | Untested for extraction; long-context evidence is against it | 3.8–6.4× input (≈32× on Haiku 5.5 for a 105K-token 10-K) |

**What to test first (same documents, same gold):**
1. Build an independent human gold set for a few whole documents, every block labelled.
2. On it, measure the recall curve for: 1 read → +gleaning → +Jev-disagreement re-read → +second shifted-boundary read. Record cost at each step to find where extra reads stop paying.
3. Measure Jev's own recall on fact-bearing blocks. If Jev misses facts too, it cannot be the safety net alone.
4. Run a 4K vs 8K character A/B. Small windows keep winning in the literature; 8K characters ≈ 2K tokens is already near GraphRAG's best range, so gains may be small.
5. Only then, if footnote/unit misses show up in the error list, A/B the focus-window design against cheaper gather-style context.

**How to report "near-100%" honestly:**
- Report recall against the **human** gold set with a confidence interval, not against the union of runs.
- Run an elusion audit on blocks marked "none" by every reader.
- Give a capture-recapture estimate of facts no reader found.
- State it as: "zero misses in n audited items → miss rate below ~3/n at 95% confidence."
- Track wrong-meaning errors (period / segment / unit) separately from wrong-quote errors. The quote check only catches the second kind.

### Gaps
- All rankings above are inferences. None of these combinations has published numbers for SEC filings; they need our own tests.
- Output token volume per block is unknown, so the true total cost split (input vs output) needs one measured run.
