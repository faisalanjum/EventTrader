# Structure-aware chunking and context carrying for financial documents

> Scope reminder: how to cut 10-K/10-Q/8-K, press releases, earnings-call transcripts and news into pieces ("chunks") that each carry the titles, "in millions" lines, period/date column heads, speaker and footnotes they need. Researched 11 Nov 2026.
>
> **The main caveat:** almost every number below comes from **retrieval** tests ("RAG" = search for a few chunks, then answer one question). Our engine **reads every chunk** and must extract **every fact**. Each finding is tagged:
> - **[R]** = retrieval-only. The gain comes from better search ranking.
> - **[T]** = plausibly transfers to "read everything and extract all".
> - **[X]** = measured on extraction itself.

---

## 1. Element/structure-based chunking of SEC filings (Jimeno Yepes et al. 2024 and follow-ups)

### Takeaway
On FinanceBench, chunks built from document elements (a new chunk at each title, each table as its own chunk) gave the best answer accuracy:
- 53.19% for element chunks vs 48.23% for 512-token chunks, roughly +5 points.
- They also needed far fewer chunks than token chunking.
- But element chunks **alone** found the right page *less* often than 256-token chunks.
- Later financial studies find chunking-method differences are small (a few points). Overlap and the parser matter as much as the method.

### Cited Findings
- **Method (Jimeno Yepes et al.).** The paper uses Unstructured's "Chipper" vision model to detect elements (Title, NarrativeText, ListItem, Table, Footer, Header, FigureCaption, …).
  - Elements under 2,048 characters are merged with the next element.
  - **A new chunk starts at every Title element.**
  - **Each table gets its own chunk, kept whole.**
  - Chunks were enriched with GPT-4 metadata: keywords, a summary, or a "prefix" (first two sentences, or a table description for tables).
  - [Jimeno Yepes et al., arXiv 2402.05131v3](https://arxiv.org/html/2402.05131v3)
- **Data.** FinanceBench subset: 141 questions over 80 recovered reports (10-K/10-Q/8-K). The average document is **102,444 tokens** (std 61,979; cl100k tokenizer). — [arXiv 2402.05131](https://arxiv.org/html/2402.05131v3)
- **Chunk counts (Table 3).**

  | Method | Total chunks | Chunks per doc (mean) | Notes |
  |---|---|---|---|
  | Base 128 tokens | 64,058 | 800.73 | |
  | Base 256 tokens | 32,051 | 400.64 | |
  | Base 512 tokens | 16,046 | 200.58 | |
  | Element (Chipper) | 20,843 | 260.57 | **96.20 tables per doc** on average |

  — [arXiv 2402.05131](https://arxiv.org/html/2402.05131v3) [T: tells you how table-heavy filings are]
- **Retrieval, Table 4** (page accuracy = right page among the top-10 retrieved chunks):
  - Base 128: 72.34
  - Base 256: 73.05
  - Base 512: 68.09
  - Keywords Chipper: 46.10
  - Summary Chipper: 62.41
  - Prefix & Table Description Chipper: 67.38
  - Base Aggregation (all three base sizes indexed together; 112,155 chunks): 83.69
  - **Chipper Aggregation** (all element variants together; 62,529 chunks): **84.40**
  - Element chunks alone were *worse* than 256-token chunks at finding the right page.
  - [arXiv 2402.05131](https://arxiv.org/html/2402.05131v3) [R]
- **Q&A accuracy, Table 5** (manual grading):

  | Method | Manual accuracy | "No answer" rate |
  |---|---|---|
  | Base 128 | 35.46% | 35.46% |
  | Base 256 | 36.88% | 25.53% |
  | Base 512 | 48.23% | 24.82% |
  | Keywords Chipper | **53.19%** | 22.70% |
  | Summary Chipper | 51.77% | 17.73% |
  | Prefix & Table Description Chipper | **53.19%** | 20.57% |

  - GPT-4 auto-grading scored 29–44%, lower than manual grading.
  - The authors claim state of the art ("50% vs 53.19%"). They say element chunking needs no chunk-size tuning and that 512-token chunks behaved most like it.
  - Setup: multi-qa-mpnet-base-dot-v1 embeddings, top-10 chunks, GPT-4 answers.
  - Limitations: only 80 of 150 documents were recovered, and the paper covers financial reports only.
  - [arXiv 2402.05131](https://arxiv.org/html/2402.05131v3) [R → partial T]
- **Follow-up: El Bachyr et al., ICSE-SEIP '26** ("Empirical Evaluation of PDF Parsing and Chunking for Financial QA with RAG", Apr 2026).
  - Grid: 6 PDF parsers × 6 chunkers (token, sentence, semantic, recursive, SDPM, neural; all capped at 512 tokens).
  - Tested on FinanceBench and **TableQuest**, a new set of 116 table-only questions built from FinanceBench PDFs.
  - The authors' reason for TableQuest: FinanceBench "evaluates a model almost exclusively on text-based questions."
  - **Results (pdfplumber + SPLADE retriever, 25% overlap; MRR = how high the right page ranks, 1.0 = always first):**

    | Chunker | FinanceBench MRR | TableQuest MRR |
    |---|---|---|
    | token | 0.647 | 0.806 |
    | sentence | 0.651 | 0.819 |
    | semantic | 0.606 | 0.795 |
    | recursive | 0.640 | 0.797 |
    | SDPM | 0.600 | 0.794 |
    | neural | **0.658** | **0.833** |

  - **Overlap mattered more than the method.** With the neural chunker, MRR went from 0.529 (0% overlap) to 0.658 (25%) to 0.647 (50%) on FinanceBench, and from 0.735 to 0.833 to 0.832 on TableQuest.
  - The "structure-driven" semantic and SDPM chunkers made **2–4× more chunks** (e.g. 5.79 vs 2.17 chunks/page) "without consistent accuracy gains."
  - Source: PDF text read via [arXiv 2604.12047](https://arxiv.org/abs/2604.12047) [R]
- **FinanceBench baseline:** "GPT-4-Turbo used with a retrieval system incorrectly answered or refused to answer 81% of questions." The authors say longer context windows help but add latency. — [Islam et al., arXiv 2311.11944](https://arxiv.org/abs/2311.11944) [R: shows retrieval is the main failure point, and our read-everything design skips that step]
- **Counter-evidence (small hobby study).** XBRL-generated questions on 10 10-Ks (~4,700 chunks, 64 questions).
  - Fixed 220-word windows + dense search reached Recall@10 = 81%.
  - Section-aware chunks (never crossing an Item) reached 69%.
  - Author: "Naive beat clever." Their guess at the reason: a numeric answer sits in a statement row, and structure does not make that row easier to match.
  - With the right chunks handed over directly ("oracle"), answer accuracy was 92% vs 56% with retrieval.
  - The author treats differences under ~15 points as noise (n = 64).
  - [CH4RL3I/footnote on GitHub](https://github.com/CH4RL3I/footnote) [R; low weight]

### Inferences
- The +5-point answer gain from element chunks likely comes from **keeping tables whole and not mixing sections**. That benefit transfers to extraction [T]: the reader sees whole tables with their head rows. The retrieval-ranking parts do not transfer.
- About 96 tables per 10-K-class document means roughly a third of all elements are tables. The "unit line / column head" problem is therefore the main case, not an edge case.
- 102K tokens per document ≈ 400K characters ≈ **~50 chunks of 8,000 characters** per 10-K. This assumes ~4 characters per token, which may be lower for table-heavy text.
- The chunking-method differences in 2026 work are small (≤ ~6 MRR points). Since we read everything, the method's main job is **self-sufficiency and attention**, not search ranking.

### Gaps
- I found no follow-up that re-ran element chunking on SEC filings for **exhaustive extraction recall**.
- I could not verify which earlier result the "50%" baseline in 2402.05131 refers to.
- The full per-parser tables of 2604.12047 were read only partially, through the main results quoted above.

---

## 2. How Unstructured, Docling, LlamaIndex and LangChain handle headings, tables and context

### Takeaway
- All four tools cut at headings, keep tables apart from text, and keep the heading path as **metadata**.
- **Only Docling's `contextualize()` and LlamaIndex nodes put headings back into the text**:
  - LangChain removes header lines from chunk text by default.
  - Unstructured does not document copying a section title into later chunks.
- None of them carries unit lines or distant footnotes. **Our "copy title/unit/date lines as context-only" step is an addition, not standard behaviour.**

### Cited Findings
- **Unstructured `chunk_by_title` / basic chunking**
  - `max_characters`, default **500**: "the hard maximum size for a chunk."
  - `new_after_n_chars`: a soft limit, default = `max_characters`. "A chunk that already exceeds this number of characters will not be extended, even if the next element would fit."
  - `combine_text_under_n_chars`: default = `max_characters`, so small sections are combined; set it to 0 to disable.
  - `overlap`: default 0, and only applies when splitting an oversized element. `overlap_all=False` by default, and the docs warn it may "pollute" chunks.
  - `multipage_sections`: default True, so a page break does not start a new chunk.
  - [Unstructured chunking docs](https://docs.unstructured.io/open-source/core-functionality/chunking)
- **Unstructured section and table rules**
  - "When a `Title` element is encountered, the prior chunk is closed and a new chunk started, even if the `Title` element would fit." A chunk never mixes two sections.
  - "A `Table` element is always isolated and never combined with another element." An oversized table "is divided into two or more `TableChunk` elements using text-splitting." **Repeating the table's head rows on split tables is not documented.**
  - "Information is naturally lost in this consolidation." Original elements are kept in `.metadata.orig_elements`.
  - The docs do not say a section title is copied into later chunks of the same section.
  - [Unstructured docs](https://docs.unstructured.io/open-source/core-functionality/chunking)
- **Unstructured `chunk_by_contextual`** (hosted platform node)
  - A "post-chunk enrichment step" that "prepends a short, LLM-generated context summary to each chunk's text."
  - It uses a surrounding window of `context_char_limit` (default **15,000** characters).
  - Chunk count and IDs are preserved. **No benchmarks are given.**
  - [Unstructured docs](https://docs.unstructured.io/api-reference/workflow/nodes/enhancement/chunker-chunk-by-contextual.md)
- **Docling HierarchicalChunker**
  - Creates "one chunk for each individual detected document element." By default it only merges list items.
  - Attaches "all relevant document metadata, including headers and captions."
  - [Docling chunking concepts](https://docling-project.github.io/docling/concepts/chunking/)
- **Docling HybridChunker**
  - Starts from the hierarchical chunks.
  - "splits chunks only when needed (i.e. oversized w.r.t. tokens)."
  - "merges chunks only when possible (i.e. undersized successive chunks with same headings & captions)" (`merge_peers=True`).
  - `repeat_table_header` (default **True**): "table headers are repeated at the beginning of each chunk when a table spans multiple chunks."
  - [Docling docs](https://docling-project.github.io/docling/concepts/chunking/)
- **Docling code details**
  - The heading path is a stack keyed by level; a new heading drops headings at the same or deeper level.
  - Headings are stored in chunk metadata (`headings = [heading_text_by_level[k] ...]`), not in `chunk.text`.
  - Table captions *are* added to table chunk text.
  - Tables are serialized as "row, column = value" triplets joined by ". ".
  - [docling-core hierarchical_chunker.py](https://raw.githubusercontent.com/docling-project/docling-core/main/docling_core/transforms/chunker/hierarchical_chunker.py)
- **Docling `contextualize()`** (base class)
  - JSON-encodes each metadata field not on the excluded list, then appends `chunk.text`, joined by `"\n"` (`DFLT_DELIM = "\n"`).
  - So the heading path ends up *in front of* the text when headings are a metadata field.
  - [docling-core base.py](https://raw.githubusercontent.com/docling-project/docling-core/main/docling_core/transforms/chunker/base.py)
- **LlamaIndex `MarkdownNodeParser`**
  - Splits at `#` headers and keeps the header line in the node text.
  - Adds `metadata["header_path"]`: the **ancestor** headers only, joined by "/" (e.g. "/header1/header2/").
  - Skips header detection inside code fences.
  - [llama_index markdown.py](https://raw.githubusercontent.com/run-llama/llama_index/main/llama-index-core/llama_index/core/node_parser/file/markdown.py)
- **LangChain `MarkdownHeaderTextSplitter`**
  - Signature: `headers_to_split_on` (required), `return_each_line=False`, **`strip_headers=True`**.
  - Headers are removed from `page_content` by default and kept as metadata keys.
  - A header stack drops headers at the same or deeper level.
  - [langchain markdown.py](https://raw.githubusercontent.com/langchain-ai/langchain/master/libs/text-splitters/langchain_text_splitters/markdown.py)

### Inferences
- The shared pattern across tools:
  1. Start a new chunk at a heading.
  2. Isolate tables.
  3. Merge small pieces up to a size.
  4. Split oversized pieces, and repeat the table head when doing so (Docling).

  Our safe-boundary rule ("cut where a new section's labels follow facts") matches steps 1–3.
- Gotcha for anyone reusing these tools: with LangChain's default, or Unstructured mid-section chunks, an LLM that reads only the chunk text **does not see the heading path**. You must add it back yourself, as Docling's `contextualize()` does.
- Docling's triplet table form ("Revenue, Q3 2026 = 1,234") makes each table cell self-contained. But it **rewrites the text**, so it cannot be the quoted evidence. At most it could be a side view mapped back to the original cell.

### Gaps
- I did not verify which fields Docling's `DocMeta` excludes from `contextualize()`. My understanding is that headings are included and internal item references are excluded, but I did not check this in the code this session.
- I found no tool that carries **unit/scale lines** ("in millions") or **period column heads** as a separate concept from headings.
- LlamaIndex's `HierarchicalNodeParser` and `UnstructuredElementNodeParser` (table summaries) were not checked.

---

## 3. Chunk-level context headers (Anthropic Contextual Retrieval, dsRAG AutoContext, others)

### Takeaway
Adding context in front of each chunk cuts search misses a lot:
- Anthropic: −35% to −67% retrieval failures.
- dsRAG: average score 4.72 → 6.04 with headers alone, 8.42 with headers plus segment extraction.

On SEC filings specifically (Snowflake), **cheap document-level context (company, form, date, section highlights) beat per-chunk LLM-written context**, which slightly *hurt*. Evidence is retrieval-only. The extraction-relevant lesson: deterministic, code-copied headers are at least as good as paid LLM summaries.

### Cited Findings
- **Anthropic Contextual Retrieval (Sept 2024).**
  - Claude 3 Haiku writes 50–100 tokens of "short succinct context to situate this chunk within the overall document," which is prepended before embedding and BM25 indexing.
  - Results (top-20 retrieval failure rate = share of questions where the right chunk is *not* in the top 20; average across codebases, fiction, ArXiv and science papers; Gemini Text 004 embeddings):
    - Contextual embeddings: 5.7% → 3.7% (**−35%**)
    - Plus contextual BM25: → 2.9% (**−49%**)
    - Plus reranking: → 1.9% (**−67%**)
  - Cost: "$1.02 per million document tokens" with prompt caching (assumes 800-token chunks and 8K-token documents).
  - Advice:
    - A domain prompt (e.g. with a glossary) may do better.
    - Tell the answering model which part of the input is context and which is the chunk.
    - Under ~200K tokens, putting the whole knowledge base in the prompt may be simpler than search.
  - **No financial dataset was included.**
  - [Anthropic engineering blog](https://www.anthropic.com/engineering/contextual-retrieval) [R]
- **dsRAG AutoContext ("contextual chunk headers", CCH).**
  - Prepends a document title (LLM-generated if missing), a document summary and section titles to each chunk. Section titles come from LLM "semantic sectioning", which marks section start and end lines.
  - KITE benchmark (4 datasets, 50 questions, 0–10 scale, GPT-4o grader):

    | Setup | Average score |
    |---|---|
    | Top-k baseline | 4.72 |
    | CCH + top-k | 6.04 |
    | Relevant Segment Extraction (RSE) alone | 6.73 |
    | **CCH + RSE** | **8.42** |

    RSE = merging neighbouring relevant chunks into longer segments.
  - Largest single gain: BVP Cloud, 2.6 → 6.3 with CCH alone.
  - FinanceBench: dsRAG "gets accurate answers 96.6% of the time" vs a 32% baseline in the authors' own re-run (19% in the original paper).
  - No CCH-only ablation is given on FinanceBench.
  - [dsRAG README](https://github.com/D-Star-AI/dsRAG) [R; vendor-reported]
- **Snowflake (2025), "Long-Context Isn't All You Need: Impact of Retrieval and Chunking on Finance RAG".**
  - Data: ~23,000 10-K/10-Q PDFs from top-1,000 Fortune companies over 5 years; ~3.2M chunks; ~500 annotated questions.
  - Findings:
    - 1,800-character chunks **plus document-level context** lifted accuracy from ~50–60% to **72–75%**.
    - **Per-chunk LLM context lost 5.8 points (Llama 3) and 0.4 points (Claude 3.5 Sonnet).**
    - Very large chunks (~14,400 characters) dropped performance ~10–20%.
    - Markdown-header chunking beat fixed-size or semantic splits by 5–10 points **only when no document context was added**.
    - With a strong pipeline, Llama 70B went from 40–50% to 70%+.
  - Note: chunk size is given as "1,800 characters" in the main text but "1,800-token" in the appendix, which is inconsistent.
  - [Snowflake engineering blog](https://www.snowflake.com/en/engineering-blog/impact-retrieval-chunking-finance-rag/) [R → partial T]
- **Zhou et al. (Feb 2026), "Beyond Chunk-Then-Embed".**
  - "Contextualized chunking improves in-corpus effectiveness but degrades in-document retrieval."
  - "simple structure-based methods outperform LLM-guided alternatives for in-corpus retrieval."
  - "LumberChunker performs best for in-document retrieval." (LumberChunker = an LLM picks the cut points.)
  - Only the abstract was available, with no numbers.
  - [arXiv 2602.16974](https://arxiv.org/abs/2602.16974) [R]

### Inferences
- For extraction [T], the header's job is not ranking. It is to give the reader the **company, period, section, unit and table head** so each fact can be stated correctly.
- Snowflake's result that document-level beats chunk-level context suggests the cheapest option, **code-copied titles and lines (no LLM)**, is not a compromise.
- Cost check: a ~200–400-character context header on an 8,000-character chunk adds ~2.5–5% input tokens. That is far below Anthropic's LLM-context step ($1.02/M document tokens on top of reading). This is my arithmetic, not a measured figure.

### Gaps
- No study measured context headers on **extraction recall or precision**.
- No study isolated the value of copying the **unit/scale line** specifically.

---

## 4. Benchmarks comparing chunking strategies (NVIDIA, Chroma, others)

### Takeaway
- Retrieval-QA tests show small, dataset-dependent differences.
- NVIDIA: page-level chunks were the most stable overall (0.648 average). On FinanceBench, 1,024-token chunks won (0.579), and **2,048-token chunks (~8K characters) dropped to 0.506**.
- Chroma: recall varied by up to ~9 points across chunkers.
- The only extraction-specific signals come from LangExtract (small windows plus multiple passes "for higher recall"; no numbers) and Chroma's "Context Rot" (accuracy drops as input grows, even on simple tasks).

### Cited Findings
- **NVIDIA (2025), answer accuracy, 0–1 scale.**
  - Overall:
    - Page-level average **0.648**, std 0.107 (the lowest spread).
    - Token-based averages 0.603–0.645 across 128–2,048 tokens with 15% overlap.
  - FinanceBench:
    - **1,024 tokens 0.579**
    - Page-level 0.566
    - **2,048 tokens 0.506**
  - "Earnings" (512 internal PDFs, 600+ questions):
    - 512 tokens **0.681**
    - 1,024 tokens 0.663
    - 2,048 tokens 0.651
  - Section-level (layout sections) was "slightly better" than page-level on FinanceBench only; no number given.
  - Setup: top-10, nemotron-70b generator.
  - Advice: for FinanceBench-like documents, try 512–1,024 tokens or section-level.
  - [NVIDIA technical blog](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/) [R]
- **Chroma (2024), token-level retrieval recall.** Five corpora, including a **Finance corpus of 166,177 tokens**; 472 questions; top-5 chunks.
  - Best recall: LLM-chosen boundaries (GPT-4o) **91.9**, and ClusterSemantic-400 **91.3**.
  - Recursive 200/0 (size/overlap): 88.1; Recursive 400/0: 89.5.
  - OpenAI-style TokenText 800/400: 87.9 recall, but very poor precision (1.4).
  - Kamradt semantic: 83.6.
  - Cutting overlap improves precision (fewer repeated tokens).
  - The LLM chunker can take "tens of minutes."
  - [Chroma research](https://www.trychroma.com/research/evaluating-chunking) [R]
- **Bhat et al. (2025), "Rethinking Chunk Size".** Best chunk size depends on answer type:
  - Small chunks are better for short fact answers.
  - Large chunks are better for long, spread-out answers.
  - Reported example: recall@1 4.2% at 64 tokens → 10.7% at 1,024 tokens on one dataset.
  - Read only via the search summary; not opened.
  - [arXiv 2505.21700](https://arxiv.org/abs/2505.21700) [R; secondary]
- **Chroma "Context Rot" (2025).** 18 models, including Claude Opus 4, Sonnet 4, Sonnet 3.7, Sonnet 3.5 and Haiku 3.5.
  - "performance grows increasingly unreliable as input length grows," even on simple tasks.
  - "Even a single distractor reduces performance."
  - "structural coherence consistently hurts model performance": models did *worse* on logically ordered haystacks than shuffled ones.
  - LongMemEval: focused prompts (~300 tokens) beat full prompts (~113K tokens) "significantly."
  - [Chroma research](https://www.trychroma.com/research/context-rot) [T: about reading, not search]
- **Google LangExtract** (open-source extraction library).
  - Combines "text chunking, parallel processing, and multiple passes for higher recall."
  - Example settings: `extraction_passes=3` ("Improves recall through multiple passes") and `max_char_buffer=1000` ("Smaller contexts for better accuracy").
  - Every extraction is mapped to its exact location in the source text; ungrounded ones get `char_interval = None`.
  - **No recall numbers are published on the page.**
  - [google/langextract](https://github.com/google/langextract) [X, but unmeasured]
- **FinReflectKG (2025), extraction from S&P 100 2024 10-Ks.**
  - Parsing: Docling (text mode). Tables are kept as markdown, and "any detected table in the markdown is retained as a single atomic chunk." Text is cut "at logical boundaries such as paragraphs or subsection headings," with `CHUNK_SIZE = 2048` tokens.
  - Extractor: Qwen2.5-72B. LLM-judged **comprehensiveness**:

    | Mode | Comprehensiveness | Triples per chunk |
    |---|---|---|
    | Single-pass | 36.3% | 13.3 |
    | Multi-pass | 15.6% | 12.4 |
    | Reflection | **48.1%** | 15.8 |

  - [arXiv 2508.17906](https://arxiv.org/html/2508.17906v2) [X]

### Inferences
- For our "read everything" design, NVIDIA's and Snowflake's drops at ~2K tokens / 14K characters are **partly a retrieval artefact**: big chunks crowd the top-10 context. They are also partly "context rot", which *does* transfer.
- 8,000 characters (~2K tokens) sits at the edge where retrieval studies start to lose accuracy. LangExtract's 1,000-character default plus 3 passes points the other way: smaller and repeated.
- The only way to settle size for **extraction** is our own sweep. Suggested: 4K / 8K / 16K characters on a gold set, measuring recall and wrong-fact rate per dollar.
- FinReflectKG shows that even with table-atomic, heading-bounded 2K-token chunks, a single pass by a strong open model missed a lot (36% judged comprehensive). A check-and-retry step raised that to 48%. Plain "multi-pass" *lowered* it. **A second look must be targeted, not blind repetition.**

### Gaps
- No public benchmark measures **exhaustive fact-extraction recall vs chunk size on SEC filings**.
- NVIDIA gives no number for section-level chunking.
- Chroma's Finance-corpus-only numbers were not broken out on the page I read.

---

## 5. Keeping tables, table titles, unit lines and footnotes attached; linking distant notes

### Takeaway
- **Tables:** standard practice is to keep each table whole as its own unit; if a table must be split, repeat the head rows (Docling).
- **Unit lines and nearby footnotes:** no tool handles these explicitly. The advice is "keep them with the table" or "store them as metadata."
- **Distant notes ("see Note 5"):** I found no measured method in the literature. **SEC filings already provide machine links**:
  - every note to the financial statements is tagged as one XBRL text block;
  - Inline XBRL has a formal fact-to-footnote link (`ix:relationship`).

### Cited Findings
- **Tables kept whole:**
  - Unstructured: "A `Table` element is always isolated and never combined with another element." — [Unstructured docs](https://docs.unstructured.io/open-source/core-functionality/chunking)
  - Jimeno Yepes et al.: tables get their own chunk, "preserving the entire table." — [arXiv 2402.05131](https://arxiv.org/html/2402.05131v3)
  - FinReflectKG: tables are "a single atomic chunk." — [arXiv 2508.17906](https://arxiv.org/html/2508.17906v2)
- **Split tables repeat their head** (`repeat_table_header=True`). — [Docling docs](https://docling-project.github.io/docling/concepts/chunking/)
- **Table captions:** Docling adds them to the table chunk text; captions are not added to non-table chunks. — [docling-core code](https://raw.githubusercontent.com/docling-project/docling-core/main/docling_core/transforms/chunker/hierarchical_chunker.py)
- **"Table description" chunk prefix:** generated by GPT-4. It tied for best Q&A accuracy (53.19%) in Jimeno Yepes et al. — [arXiv 2402.05131](https://arxiv.org/html/2402.05131v3)
- **Footnote advice (practitioner level, no benchmarks):**
  - LlamaParse docs warn that footnote definitions can be split from their reference markers. They suggest storing footnote metadata separately, or keeping each footnote with its first reference. Markers like "Total Liabilities (3)" can be parsed to link line items to footnotes. — [theneuralbase LlamaParse notes](https://theneuralbase.com/llamaparse/learn/beginner/footnote-references/) (secondary site; not the official LlamaIndex docs)
  - Daloopa (a vendor) argues element-based chunking keeps a table and its footnote references together. It also suggests detecting "see note" and continuation markers to merge tables split across pages. **No numbers.** — [Daloopa blog](https://daloopa.com/blog/analyst-best-practices/processing-tabular-financial-data-with-large-language-models)
- **S-1 benchmark (2026):** one question may need a financial-statement footnote, an MD&A paragraph and a risk factor together, and naive fixed-window chunking handles this poorly. — [arXiv 2606.23032](https://arxiv.org/html/2606.23032v3) (seen via search summary only)
- **Inline XBRL 1.1** replaced the older `footnoteLink` with a new element, `ix:relationship`, for fact-to-footnote and fact-to-explanatory-fact links; `ix:footnote` remains. — [XBRL International, Inline XBRL 1.1](https://www.xbrl.org/Specification/inlineXBRL-part1/REC-2013-11-18/inlineXBRL-part1-REC-2013-11-18.html) (seen via search summary; spec page not opened)
- **SEC detail tagging (Rule 405 of Regulation S-T; from June 15, 2012):**
  - Level 1: each note is tagged "as a single block of text" using a TextBlock element.
  - Level 4: "each amount that appears within the footnotes must be separately tagged."
  - Sources: [Novaworks (filing-agent)](https://novaworks.knowledgeowl.com/help/what-are-the-requirements-for-xbrl-and-what-do-the-levels-of-tagging-mean); SEC staff observations on Level 4 tagging at [sec.gov](https://www.sec.gov/structureddata/osd_staffobs_06-15-11). The level wording comes from vendors and was not checked against Rule 405 text.

### Inferences
- For 10-K/10-Q, "see Note 5" can be resolved **deterministically** using the Level 1 TextBlock for Note 5, which gives exact start and end in the filing. No AI is needed. The "XML field" blocks we already extract likely include these. Not verified in our data.
- **Unit/scale cross-check (from background knowledge, NOT verified this session):** Inline XBRL numeric facts carry a `scale` attribute (e.g. 6 = millions) plus period and unit context. Code could use it to confirm that the "in millions" wording a quote relies on matches the tagged fact.
- **Do not paste distant notes into every chunk.** It adds cost and breaks the "one Driver per chunk, nothing else" ideal. A lookup when a fact cites a note marker fits the evidence better.

### Gaps
- I found **no peer-reviewed method or benchmark** for linking distant footnotes or "see Note X" references to the text that cites them.
- I found nothing that measures what happens when unit lines ("in millions") get detached from tables.
- I could not open the Inline XBRL 1.1 spec page (the errata URL returned 404), so the `scale` and `continuedAt` details are unverified here.

---

## 6. Earnings-call transcripts and news

### Takeaway
Practice agrees on the unit:
- **One speaker turn** in prepared remarks.
- **One analyst question plus management's direct answer** in Q&A.
- Speaker name, role and the call's quarter go along as labels.

I found **no head-to-head evaluation** of transcript chunking. For news, nothing specific was found; articles are usually short enough to be a single chunk.

### Cited Findings
- **Point-in-Time Encoders for Earnings Calls (Nov 2026):** each analyst question directly followed by an executive turn forms one Q&A pair; pairs are kept only if both turns have ≥120 characters, which filters out greetings and thank-yous. — [arXiv 2611.14325](https://arxiv.org/html/2611.14325)
- **Open-source pipeline:** separates prepared remarks (split recursively) from Q&A (analyst question + executive answer as one retrieval unit). — [earnings-call-rag on GitHub](https://github.com/ajinkya252005/earnings-call-rag) [R; hobby project]
- **Analyst pragmatics paper (2019):** tells analysts from company speakers using speaker-label rules; defines a Q&A set as "two or more turns," one with the analyst's question(s) and the rest with company answers. — [arXiv 1906.02868](https://arxiv.org/pdf/1906.02868)
- **GraphRAG benchmark:** "the hierarchical structure of earnings calls aligns well with" a tree-based method (TREX) for single transcripts. — [arXiv 2503.02922](https://arxiv.org/pdf/2503.02922) (search summary) [R]
- **Another 2026 paper** splits long segments into ~600–800 tokens. — [arXiv 2608.11626](https://arxiv.org/pdf/2608.11626) (search summary)
- **NVIDIA's internal "Earnings" PDF set (not transcripts specifically):** 512-token chunks scored best (0.681). — [NVIDIA blog](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/) [R]

### Inferences
- For our engine:
  - A Q&A exchange is a natural "one Driver topic" unit.
  - The **speaker name and role** is the transcript equivalent of a table's unit line: copy it into any chunk that starts mid-turn.
  - The analyst's question is often needed to understand a management number ("we expect it to be about 2%"), so the question should travel with the answer.
- News: most articles are under 8,000 characters, so whole-article = one chunk with headline, date and source as context. This is my inference, not measured.

### Gaps
- No evaluation compares transcript chunking choices (turn vs exchange vs fixed size) for any task.
- No news-specific chunking evidence was found.

---

## 7. Retrieval-only vs transferable: summary table

| Finding | Retrieval-only? | Transfers to "read all, extract all"? |
|---|---|---|
| Element chunks give +5 points Q&A accuracy (2402.05131) | Mostly retrieval | **Partly**: whole tables and unmixed sections help any reader |
| Contextual headers cut retrieval failures by 35–67% (Anthropic) | Yes | **Partly**: headers make chunks self-sufficient; ranking gains do not transfer |
| Document-level beats chunk-level LLM context (Snowflake) | Yes | **Partly**: favours cheap deterministic headers |
| 25% overlap > 0% (2604.12047) | Yes | Weakly: our "context only" copy *is* a targeted overlap |
| Page-level or 512–1,024 tokens is best (NVIDIA) | Yes | Unclear; size must be re-tested for extraction |
| Accuracy decays with input length ("Context Rot") | No | **Yes** |
| Multiple passes for recall (LangExtract); reflection raises comprehensiveness 36% → 48% (FinReflectKG) | No | **Yes** (extraction) |
| Q&A pairs as units (transcripts) | Mostly | Yes, as a "one topic per chunk" unit |

### Gaps
- None beyond those listed above.

---

## Implications for the design above

Reminder of the design: Jev tags blocks → code cuts ~8,000-character chunks at safe boundaries and copies title/unit/date lines as "context only" → a Haiku/Sonnet-class model reads each chunk once → code checks quotes letter for letter.

Evidence strength: **Strong** = several independent sources, measured · **Moderate** = one measured study or consistent tool practice · **Weak** = vendor claim, hobby study or my inference.

**KEEP**
1. **Tables never split; each table is its own unit; if one must be split, repeat its head rows.** Unstructured, Docling (`repeat_table_header`), Jimeno Yepes and FinReflectKG all do this; element chunks gave +5 points Q&A accuracy. — *Moderate*
2. **Cut at section starts (new labels after facts) and never mix two sections** (Unstructured `by_title`, Jimeno Yepes). — *Moderate* for Q&A. One small study saw no gain for retrieving numeric rows (*weak* counter-evidence).
3. **Code-copied heading/unit/date lines, not LLM-written context.**
   - Snowflake on 10-K/10-Q: document-level context took accuracy to 72–75%, while per-chunk LLM context lost 0.4–5.8 points.
   - Docling `contextualize()` and LlamaIndex `header_path` do the same thing.
   - Costs ~2.5–5% extra input vs Anthropic's $1.02/M tokens for LLM context.
   - *Moderate* (retrieval-measured; the transfer is logical).
4. **Exact-quote checking by code.** LangExtract also grounds every extraction to character offsets and drops ungrounded ones. — *Moderate* as practice.

**CHANGE / TEST**
5. **Chunk size: 8,000 characters is not backed by any extraction study.**
   - Retrieval studies lose accuracy at ~2K tokens (NVIDIA FinanceBench 0.579 → 0.506) and at 14,400 characters (Snowflake −10–20%).
   - Context Rot shows decay with length.
   - LangExtract uses 1,000-character windows.
   - **Run a small sweep (4K / 8K / 16K characters) on a gold set and measure recall, wrong facts and dollars.** — *Weak* evidence for any single number.
6. **Label context clearly and make code reject quotes that match only the context-only lines.** Anthropic advises telling the model which part is context. Our own rule: a quote must map to the block's original location, and duplicated header lines must not create double facts. — *Moderate* (advice) + design logic.
7. **Add a targeted second look, not blind re-reads.**
   - FinReflectKG: reflection raised comprehensiveness 36.3% → 48.1%, but plain multi-pass *fell* to 15.6%.
   - LangExtract: multiple passes "for higher recall".
   - Suggestion: re-read only chunks where Jev said "fact" but the reader extracted nothing. — *Weak to moderate*

**ADD**
8. **Distant notes ("see Note 5") through XBRL, not text search.**
   - Each note is one TextBlock (Level 1 tagging), and Inline XBRL 1.1 has `ix:relationship` fact-to-footnote links.
   - Fetch the note on demand; do not paste it into every chunk.
   - *Weak* evidence that it helps (no study), but *strong* that the data exists in SEC filings.
9. **Use Inline XBRL `scale` / period / unit as a code cross-check that "in millions" and the period head match the quoted number.** — *Weak*: unverified this session; needs a check on our data.
10. **Transcripts: one chunk = one analyst question + management answer; prepared remarks by speaker turn; copy speaker name and role as context.** — *Weak to moderate* (consistent practice, no benchmark).
11. **News: one article = one chunk, with headline, date and source as context.** — *Weak* (inference only).
12. **Jev's "depends on block above" boundary tagging is a cheap version of LLM-chosen boundaries.**
    - Retrieval studies show small gains: Chroma 91.9 vs 88.1 recall; Zhou 2026 has LumberChunker best for in-document retrieval.
    - At $0.042 per million tokens, Jev is cheap enough.
    - Measure Jev's boundary mistakes directly. Each one shows up as a missing unit/period in a chunk that **code can detect**: a number with no unit line in scope.
    - *Weak*
