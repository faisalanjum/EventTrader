# Boundary detection and topic segmentation: cheap, accurate ways to decide where to cut

Scope note: researched 11 Nov 2026. Almost every published result below measures **retrieval** (did the right chunk come up in a search?). Our task is **exhaustive extraction** (a smart model reads every chunk once, and recall must be near 100%). Each finding says which kind it is. Numbers are quoted from the source pages; anything I could not check against a primary page is marked **(unverified)**.

## 1. Supermemory blog: how Jev was used for chunking, with numbers and caveats

### Takeaway
Supermemory asked Jev, sentence by sentence, "does this continue the previous thought or start a new one?" and then used code to cut near a target size. On a small internal **retrieval** test this beat recursive and embedding chunking (93% vs 89% vs 81%). It cost about 10x more than rule-based chunking, and its English score in one test was 67%. No prompts, no public data and no boundary-accuracy metrics were published.

### Cited Findings
- Author and date: Dhravya Shah, "Jev changes a lot in memory & context engineering. Here's exactly how.", 24 Sep 2026, first posted on X. — [Supermemory blog](https://supermemory.ai/blog/jev-memory-context-engineering)
- Method: Jev is asked whether each **sentence** continues the previous thought or starts a new one, and those answers pick boundaries near a target size. Two variants are named, "jev continuation" and "jev boundary", but the post does not fully define how they differ. The exact question wording is not published. — [Supermemory blog](https://supermemory.ai/blog/jev-memory-context-engineering)
- Benchmark: internal and not public, covering messy, markdown and multilingual data. The metric is "top-chunk answer hit rate" over **72 questions** with **320-character chunks**. — [Supermemory blog](https://supermemory.ai/blog/jev-memory-context-engineering)
- Results (retrieval): Jev continuation **93%**, Jev boundary **93%**, recursive separators **89%**, embedding semantic chunking **81%**. — [Supermemory blog](https://supermemory.ai/blog/jev-memory-context-engineering)
- Multilingual test (answer retrieved within 640 characters): Jev boundary scored **100%** in Spanish, Arabic, Hindi, Japanese and Chinese, but **67% in English**. The post gives no reason. — [Supermemory blog](https://supermemory.ai/blog/jev-memory-context-engineering)
- Cost per 1,000 documents: rule-based **$0.008**, embedding semantic **$0.011**, Jev continuation **$0.080**, Jev boundary **$0.087**. The post calls Jev "much more expensive than other chunking methods" because the others are "essentially free". It does not give the document length. — [Supermemory blog](https://supermemory.ai/blog/jev-memory-context-engineering)
- Not published: Pk, WindowDiff, F1, latency, token counts, prompts, and any comparison with LLM chunking or fixed-size chunking. — [Supermemory blog](https://supermemory.ai/blog/jev-memory-context-engineering)

### Inferences
- With 72 questions, 93% vs 89% is about 67 vs 64 correct, a gap of roughly three questions. That is not strong statistical evidence.
- The 67% English result looks like 2 of 3 questions, which would mean a very small per-language sample. This is a guess: the post does not give the per-language question count.
- The method is sentence-level and tuned for retrieval with small (320-character) chunks. Our setting is block-level, with 8,000-character chunks and recall-first extraction, so the 93% does not transfer directly.
- The "continuation" framing matches TypeSafe's own structure-recovery cookbook (section 8). It suggests Jev answers "does B continue A?" more reliably than an abstract "is this a new topic?". That fits our own result (Jev never split a real tie, but missed many real separations).

### Gaps
- The exact Jev question wording, how the two variants differ, the per-language sample sizes and the document sizes behind "$ per 1k docs" are all unpublished.
- There are no boundary-level accuracy numbers (precision/recall of cuts), only end-to-end retrieval hit rate.

## 2. Meta-Chunking (Zhao et al., 2024): perplexity chunking and margin-sampling chunking with small models

### Takeaway
Meta-Chunking cuts text using a small LM's uncertainty. Perplexity (PPL) chunking cuts at dips in sentence perplexity. Margin sampling (MSP) asks a yes/no-style "split or keep these two sentences?" question and reads the probability gap. PPL chunking with Qwen2-1.5B beat similarity chunking on QA scores and took about 46% of the time. The pairwise MSP question, which is the closest academic version of our Jev pair question, was by far the slowest when run per sentence with a 7B model.

### Cited Findings
- Margin Sampling Chunking: margin = P(answer k1 | prompt) − P(answer k2 | prompt). The prompt offers "Split sentence1+sentence2 into sentence1 and sentence2 two parts;" vs "Keep sentence1+sentence2 unsplit in its original form;" and asks "Please answer 1 or 2." The threshold θ starts at 0 and is updated as the average of recorded margins. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- Perplexity Chunking: each sentence's PPL is its average token perplexity given the preceding text. Boundaries go at local minima of the PPL sequence that cross θ. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- Models: the main runs use Qwen2-1.5B, Internlm2-1.8B, Baichuan2-7B and Qwen2-7B. Sub-1B runs use Pythia-0.16B, Pythia-0.41B and Qwen2-0.5B. Qwen2-72B is a direct-chunking baseline. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- Accuracy (LongBench F1, retrieval-augmented QA):

  | Method | 2Wiki | Qasper | MultiFieldQA-en | MultiFieldQA-zh |
  |---|---|---|---|---|
  | Fixed (original) | 11.89 | 9.45 | 29.89 | 22.45 |
  | Similarity chunking | 12.00 | 9.93 | 29.19 | 22.39 |
  | Qwen2-1.5B PPL | 13.32 | 9.82 | 31.30 | 22.57 |
  | Qwen2-7B PPL | 13.41 | 9.39 | 32.35 | 22.81 |

  — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- MultiHop-RAG Hits@10: original 0.6027, similarity 0.7232, Qwen2-1.5B PPL 0.7366. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- LumberChunker run with Qwen2-7B scored 10.65 on Qasper only. The paper says it "failed to work effectively" on the other datasets. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- Time (seconds per dataset):
  - 2Wiki: fixed 0.21, Llama_index 8.12, similarity 416.45, Qwen2-1.5B PPL **190.93**, Qwen2-7B PPL 736.69, Qwen2-7B margin sampling (sentence-level) **7108.37**.
  - Qasper: similarity 307.05, LumberChunker (Qwen2-7B) 2883.43, Qwen2-7B margin sampling 5207.87.
  - The abstract's "45.8% of the time" is 190.93 / 416.45.

  — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- Smaller models cut run time but "often comes with a compromise in performance". Pythia is mainly English. Pythia-0.16B / 0.41B margin-sampling 2Wiki F1 was 13.14 / 11.86. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- Code: https://github.com/IAAR-Shanghai/Meta-Chunking. The paper is now at v3 (21 May 2025); the numbers above are from v1 (Oct 2024). — [arXiv abstract page](https://arxiv.org/abs/2410.12788); [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)

### Inferences
- PPL chunking needs only one forward pass over the text: no question wording, no generation. That makes it the cheapest "LM-aware" cut signal for a free local model. Its weakness is that it needs sentence-level text, while our tables and short label lines will give noisy perplexity values.
- Margin sampling is our design in academic form: a binary pairwise question with a probability gap. Its cost was high only because it ran per sentence with a 7B local model. Jev (or batched questions) changes that cost picture.
- All gains are small (about 1–2 F1 points) and all of them are retrieval-QA, not exhaustive extraction.

### Gaps
- I did not check whether v3 changed the numbers.
- No results on financial filings or tables. The hardware behind the timings was not captured.

## 3. LumberChunker (Duarte et al., 2024): LLM picks where the content shifts

### Takeaway
LumberChunker shows a group of paragraphs (about 550 tokens) to an LLM, asks which paragraph is the first where the content "clearly changes", and repeats from there. On narrative books it beat recursive chunking by 7.37 points DCG@20. It must run one call after another (no parallel calls), and it failed with a 7B open model in another team's tests.

### Cited Findings
- Method: paragraphs get IDs and are grouped until a group passes a token threshold θ. θ=550 worked best (450 and 650 were close, 1000 was worst). The prompt asks the LLM to "Find the first paragraph (not the first one)" where "the content clearly changes compared to the previous paragraphs"; the chosen ID starts the next group. The model was Gemini 1.0-Pro, and chunks averaged 334 tokens. — [LumberChunker HTML](https://arxiv.org/html/2406.17526)
- Benchmark GutenQA: 100 Project Gutenberg books, 3,000 question–answer pairs (30 per book), questions made by gpt-3.5-turbo-0125. — [LumberChunker HTML](https://arxiv.org/html/2406.17526)
- Retrieval results:

  | Method | DCG@1 | DCG@20 | Recall@1 | Recall@20 |
  |---|---|---|---|---|
  | Semantic | 29.50 | 44.74 | 29.50 | 64.51 |
  | Paragraph | 36.54 | 49.00 | 36.54 | 64.34 |
  | Recursive | 39.04 | 54.72 | 39.04 | 74.35 |
  | Proposition | 36.91 | 46.19 | 36.91 | 55.54 |
  | LumberChunker | 48.28 | 62.09 | 48.28 | 77.92 |

  — [LumberChunker HTML](https://arxiv.org/html/2406.17526)
- Runtime (average seconds per book):

  | Book | Recursive | LumberChunker | Semantic | Proposition |
  |---|---|---|---|---|
  | A Christmas Carol (710 paragraphs) | 0.1 | 95 | 212 | 633 |
  | Monte Cristo (14,339 paragraphs) | 0.6 | 1628 | 4978 | 10302 |

  — [LumberChunker HTML](https://arxiv.org/html/2406.17526)
- Limitations the authors state: it is more expensive and slower than recursive chunking, and it "cannot be optimized with asynchronous API calls" because each query depends on the previous answer. It was designed for narrative text and may be unnecessarily complex for structured text such as legal documents. It scales poorly with long documents. — [LumberChunker HTML](https://arxiv.org/html/2406.17526)
- An independent replication with Qwen2-7B worked on only 1 of 5 datasets. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)

### Inferences
- "Pick the first changed paragraph from a list" is a pick-one question over IDs. Jev supports this (Choice, up to 255 options), but Jev "leans toward the option that comes first" (section 8), which is a known bias for this exact format. The failure of the 7B model suggests small models handle this format worse than a yes/no per pair.
- Running one call after another conflicts with batching. Pairwise questions can all go in parallel.

### Gaps
- No dollar cost reported. No results on structured or financial text.

## 4. Is semantic or LLM chunking worth the cost? (Qu, Tu & Bao 2024; Chroma 2024; NVIDIA 2025)

### Takeaway
In retrieval studies, embedding-based semantic chunking beats fixed-size chunking mainly on artificially stitched, multi-topic documents. On real documents, fixed-size chunking is often as good or better. LLM chunkers give small recall gains (Chroma: 91.9 vs about 88–89.5). Financial-document studies favour structure-aware or page-level chunks over clever boundary detection.

### Cited Findings
- Qu, Tu & Bao (Vectara authors) compared fixed-size, breakpoint-semantic and clustering-semantic chunkers, with stella_en_1.5B_v5 as the main embedder. — [arXiv HTML 2410.13070](https://arxiv.org/html/2410.13070)
- Document retrieval F1@5 (Fixed / Breakpoint / Clustering):
  - Stitched sets: Miracl* 69.45 / **81.89** / 67.35; NQ* 43.79 / **63.93** / 41.01.
  - Real documents: HotpotQA **90.59** / 87.37 / 84.79; ConditionalQA **68.11** / 64.44 / 65.94; Qasper **90.99** / 89.27 / 90.77.

  — [arXiv HTML 2410.13070](https://arxiv.org/html/2410.13070)
- Evidence retrieval F1@5 was nearly flat, e.g. ExpertQA 47.11 / 47.08 / 46.87 and TechQA 28.98 / 28.49 / 27.96. — [arXiv HTML 2410.13070](https://arxiv.org/html/2410.13070)
- Answer generation (BERTScore) differed by at most 0.01. — [arXiv HTML 2410.13070](https://arxiv.org/html/2410.13070)
- Conclusion: gains "did not consistently justify the additional computational cost", and "fixed-size chunking remains a more efficient and reliable choice for practical RAG applications". — [arXiv HTML 2410.13070](https://arxiv.org/html/2410.13070)
- Chroma (July 2024) used token-level recall and IoU, with 5 chunks retrieved by text-embedding-3-large:

  | Chunker | Recall | IoU |
  |---|---|---|
  | LLMSemanticChunker (GPT-4o) | 91.9 | 3.9 |
  | ClusterSemanticChunker 400 | 91.3 | 4.5 |
  | Recursive 400/0 | 89.5 | 3.6 |
  | Recursive 200/0 | 88.1 | 6.9 |
  | KamradtSemanticChunker | 83.6 | 1.5 |

  Its corpora included a "Finance" set. — [Chroma research](https://www.trychroma.com/research/evaluating-chunking)
- Chroma's LLM chunker cut text into 50-token pieces wrapped in tags and asked the model to return indices to split after (e.g. "split_after: 3, 5"). Llama 3 8B Instruct also followed the format. An earlier "repeat the text with split markers" approach was "costly, slow, and prone to hallucinated text". LLM chunker runtime "can vary from almost instantaneous to tens of minutes". — [Chroma research](https://www.trychroma.com/research/evaluating-chunking)
- NVIDIA (18 Jun 2025): page-level chunking had the best average accuracy, 0.648 (SD 0.107), vs 0.603–0.645 for token sizes. — [NVIDIA blog](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/)
- NVIDIA results by dataset:
  - FinanceBench (10-K and earnings reports): 1,024 tokens 0.579 (best), page-level 0.566, 2,048 tokens 0.506. Section-level was "slightly better" than page-level, with no number given.
  - Internal "Earnings" set: 512 tokens 0.681 (best).

  Tables and charts were extracted whole and never chunked. — [NVIDIA blog](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/)

### Inferences
- The evidence says smart cuts matter most when topics change sharply and unpredictably. Filings are the opposite: headings, item numbers and tables already mark most topic changes. So rules capture most of the value, and model-decided cuts should be kept for the leftover cases.
- All of this is retrieval. In exhaustive extraction, a "bad" cut only hurts recall if it separates a fact from the context it needs. A chunk that holds two topics costs extra tokens but loses nothing. The metric that matters for us is "context-separation errors", not Pk or retrieval hit rate.

### Gaps
- No study found that measures chunking against exhaustive-extraction recall, which is our real metric.

## 5. Classic and neural text segmentation: accuracy and cost; financial text and transcripts

### Takeaway
Supervised local models are strong and cheap. Cross-segment BERT, with 128 tokens on each side of a candidate break, reached F1 66.0 on Wiki-727K, and a distilled 11M-parameter version still reached 63.0. Seeing **both sides** of the break is essential. Zero-shot LLM segmenters still trail fine-tuned models on standard metrics. I found no public topic-segmentation benchmark for SEC filings or earnings calls.

### Cited Findings
- Cross-segment BERT (Lukasik et al., EMNLP 2020) results:

  | Model | Wiki-727K F1 | Choi F1 | Choi Pk |
  |---|---|---|---|
  | Cross-segment BERT 128-128 | **66.0** (P 69.1, R 63.2) | 99.9 | 0.07 |
  | Hierarchical Bi-LSTM baseline (Koshorek 2018) | 57.7 | – | – |
  | SEGBOT | – | – | 0.33 |

  — [Lukasik et al. 2020 PDF](https://arxiv.org/pdf/2004.14535)
- Context matters: with 256 tokens on the left and **0 on the right**, F1 was **20.2**, vs 64.0 with 128 tokens on each side (BERT-Base). Replacing the running text with sorted token lists gave 39.1. The paper's conclusion: "it is crucial that the model sees both sides of the break." — [Lukasik et al. 2020 PDF](https://arxiv.org/pdf/2004.14535)
- Model size on Wiki-727K: 336M params F1 66.0; 110M 64.0; 13M 60.2; 2.6M 55.5. Distilled: 11M **63.0**, 5M 62.5. — [Lukasik et al. 2020 PDF](https://arxiv.org/pdf/2004.14535)
- Generative LLM segmentation (arXiv 2601.03276, Jan 2026): sentences are numbered in brackets and GPT-3.5-turbo-16k returns boundary indices, using overlapping windows plus recursive splitting.
  - GPT-3.5 "outperforms all other models" on its Human, Wiki and Synthetic sets, but BERT-based models were better on concatenated Wikipedia.
  - Failure mode: on messy documents GPT-3.5 "would sometimes get stuck" and return regular index patterns that run past the sentence count.
  - The authors ran out of budget and prefer the "boundary similarity" metric over Pk/WindowDiff.

  — [arXiv HTML 2601.03276v1](https://arxiv.org/html/2601.03276v1)
- (Unverified, search summary only) On a Chinese paragraph-level benchmark, zero-shot ChatGPT scored Pk 41.12 vs about 19–24 for fine-tuned models. — [arXiv 2305.14790](https://arxiv.org/pdf/2305.14790)
- (Unverified, search summary only) A 2025 master's thesis on podcast transcripts reports an LLM similarity-threshold method at F1 0.72, Pk 0.29, WindowDiff 0.31. — [Webis thesis PDF](https://downloads.webis.de/theses/papers/chaitanya-valaboju_2025.pdf)
- For speech transcripts, "Paragraph Segmentation Revisited" (LREC 2026) introduces the TEDPara and YTSegPara benchmarks. It uses constrained decoding so that LLMs insert breaks without changing the transcript text, and a compact model, MiniSeg, claims state-of-the-art accuracy at "minimal computational cost". I did not obtain the numbers. — [arXiv 2512.24517](https://arxiv.org/abs/2512.24517)
- Off-the-shelf local boundary model: Chonky (mirth/chonky_modernbert_base_1) is about 0.1B parameters. It is a token classifier ("O" vs "separator") trained on BookCorpus paragraphs at 1,024 tokens, and self-reports token F1 0.79 (P 0.83, R 0.75). It is Chonkie's default "NeuralChunker". — [Hugging Face model card](https://huggingface.co/mirth/chonky_modernbert_base_1); [Chonkie docs](https://docs.chonkie.ai/oss/chunkers/neural-chunker)
- Financial or transcript segmentation: no public topic-boundary dataset for earnings calls was found. FactSet's commercial Alexandria tags transcript sections with about 250 topics. — [FactSet](https://insight.factset.com/resources/at-a-glance-alexandria-transcripts)

### Inferences
- A pairwise "is there a break between A and B?" question with both sides visible is well supported, and small local models handle it well when fine-tuned. Our own 106 labelled pairs (51 tied, 55 separate) could seed a fine-tune or a calibration set, but that is far too few to train a BERT-class model from scratch.
- Chonky is trained on book paragraphs. Filings (tables, label lines, "(in millions)") are far from its training data, so it would need testing before any trust.

### Gaps
- No TextTiling or C99 numbers on modern benchmarks were captured; the classic baselines are known to be weaker, but I have no sourced figure.
- No segmentation results on 10-K/10-Q/8-K or earnings-call text.
- MiniSeg and TEDPara numbers were not obtained.

## 6. Proposition chunking ("one fact per unit"): does it give self-contained single facts, at what cost, and is it verbatim?

### Takeaway
Dense X Retrieval's propositions are single, self-contained facts. A distilled Flan-T5-Large model makes them with few errors (3.1% not stand-alone). They are **rewritten, not verbatim**: pronouns are replaced and context is added. So they cannot serve as exact quotes, and in LumberChunker's tests on narrative text they were the slowest method and had lower recall.

### Cited Findings
- Definition: propositions are "atomic expressions within text, each encapsulating a distinct factoid". They are minimal, one meaning each, contextualized and self-contained. — [Dense X Retrieval HTML](https://arxiv.org/html/2312.06648)
- Not verbatim: "the tower" becomes "the Leaning Tower of Pisa", and the prompt asks the model to replace pronouns and add modifiers. — [Dense X Retrieval HTML](https://arxiv.org/html/2312.06648)
- How the Propositionizer was built: GPT-4 seed set → 42,857 pairs → fine-tuned Flan-T5-Large, which reached dev F1 0.822. — [Dense X Retrieval HTML](https://arxiv.org/html/2312.06648)
- Error rates on 50 passages:

  | Error type | GPT-4 | Propositionizer |
  |---|---|---|
  | Not faithful | 0.7% | 1.3% |
  | Not minimal | 2.9% | 2.0% |
  | Not stand-alone | 4.9% | 3.1% |

  — [Dense X Retrieval HTML](https://arxiv.org/html/2312.06648)
- Cost: decomposing Wikipedia took about 500 GPU hours (P100). That produced 256.9M propositions, about 6x the passage count, with an index of about 768 GB. — [Dense X Retrieval HTML](https://arxiv.org/html/2312.06648)
- Gains (retrieval): unsupervised Recall@5 +12.0 (SimCSE) and +9.3 (Contriever). Supervised gains were small (DPR 57.3→59.9, GTR 65.2→68.0). Propositions struggle with multi-hop questions where the facts land in separate propositions. — [Dense X Retrieval HTML](https://arxiv.org/html/2312.06648)
- On narrative books, proposition-level chunking had Recall@20 **55.54** vs LumberChunker 77.92 and recursive 74.35. It was also the slowest: 633 s and 10,302 s per book. — [LumberChunker HTML](https://arxiv.org/html/2406.17526)
- MoC (2025) avoids rewriting by having chunkers output a regex of each chunk's start and end characters, plus edit-distance recovery to fix hallucinated expressions. The authors note GPT-4o "tends to alter the expressions used in the original text" and sometimes "generates fabricated content". Their fine-tuned Meta-chunker-1.5B roughly matched direct Qwen2.5-72B chunking (CRUD BLEU-1 0.3754 vs 0.3721). — [MoC HTML](https://arxiv.org/html/2503.09600v2)

### Inferences
- "One fact per unit" by rewriting breaks our exact-quote rule. Any method we use must only choose **boundaries** (indices or IDs) and never re-emit text. Chroma's index output, Jev's yes/no answers, PPL dips and MoC's regex-plus-recovery all keep the text verbatim.
- The owner's ideal, "each chunk holds everything about one Driver and nothing else", is not reachable by cutting text in order. One Driver (say, revenue) appears in the headline, the table, MD&A and the guidance section, with other topics in between. Cutting in order can give "one topic per stretch". "Everything about one Driver" needs grouping across the document after extraction (clustering by Driver), not boundary detection.

### Gaps
- No study found of verbatim (extractive) proposition units, i.e. "one fact per span" without rewriting, measured for recall.

## 7. Cost: API small models vs local small models for per-boundary decisions, and batching many questions in one call

### Takeaway
Batching all questions on one shared input is the big lever: TypeSafe measured 12.2x cheaper and 11.8x faster with no change in answers. On today's prices, Jev input costs $0.042/MTok and Claude Haiku 5.5 costs $0.10/MTok (prompts up to 100K tokens). The cut pass only saves money if it costs much less than having the smart model read more text. Local small-model throughput numbers found online were weak.

### Cited Findings
- TypeSafe "Parallel questions": 13 questions on a ~53,777-character article.
  - One batched call cost $0.000497 and took 0.24 s; 13 separate calls cost $0.006090 and took 2.81 s.
  - Answers moved by at most 0.015, and batched vs single means agreed within 0.004.
  - No tested limit on questions per input, and interference was not tested at larger scale.

  — [TypeSafe parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md)
- TypeSafe "Structure recovery" asked all adjacent line pairs in **one request** (16 pair questions, 0.24 s). Its second pass sent 62 questions on 17 blocks in one request (0.22 s). — [TypeSafe autoformat](https://docs.typesafe.ai/cookbooks/autoformat.md)
- TypeSafe "Line-by-line search": one Choice question over 218 line IDs (43,980 characters) in one request. Choice is capped at **255 options**. — [TypeSafe semantic_find](https://docs.typesafe.ai/cookbooks/semantic_find.md)
- Claude prices (per million tokens, input / output):

  | Model | Input | Output | Notes |
  |---|---|---|---|
  | Haiku 5.5 (prompts ≤100K) | $0.10 | $0.50 | cache hits $0.01 |
  | Haiku 5.5 (prompts >100K) | $0.50 | – | |
  | Haiku 4.5 | $1 | $5 | |
  | Sonnet 5.5 | $2 | $10 | |

  The Batch API halves these prices. — [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- Contextual Retrieval (Anthropic) costs $1.02 per million document tokens to add a context line to each 800-token chunk (with prompt caching). — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- Local timings (Meta-Chunking, hardware not captured): on 2Wiki, Qwen2-1.5B PPL took 190.93 s, Qwen2-7B PPL 736.69 s, and Qwen2-7B pairwise margin sampling 7108.37 s. Running pairwise questions on a generative 7B model locally was about 10x slower than PPL. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1)
- Local throughput (weak evidence, unverified): Qwen's speed page lists vLLM Qwen2.5-0.5B-Instruct BF16 at 311.55 tokens/s (input length 1) and 223.86 (6,144-token input), as overall generation speed. No reliable prefill-only benchmark was found. — [Qwen speed benchmark](https://qwen.readthedocs.io/en/v2.5/benchmark/speed_benchmark.html)
- Chonky (about 0.1B params) is an encoder classifier: one forward pass labels every token, with no generation. — [Hugging Face model card](https://huggingface.co/mirth/chonky_modernbert_base_1)

### Inferences
Worked arithmetic (my calculations):
- Reading a whole 10-K once (about 105K tokens):

  | Reader | Cost |
  |---|---|
  | Jev | 105,000 × $0.042/1M ≈ **$0.0044** |
  | Haiku 5.5 (in chunks under 100K) | ≈ **$0.0105** |
  | Sonnet 5.5 | ≈ **$0.21** |

- Our per-block Jev tagging: the project measured $0.033 for 275 blocks, about $0.00012 per block. **These numbers do not reconcile:** 275 × 1,170 tokens = 321,750 tokens, which at $0.042/MTok is $0.0135, not $0.033. Check what else was billed (repeat runs, other questions, a different price).
- At the measured $/block, a 10-K with about 1,000 blocks (my guess; not measured) would cost about $0.12 for the cut pass. That is roughly 10x the cost of Haiku 5.5 reading the whole 10-K, and about half of Sonnet 5.5 reading it. The cost comes from the about 1,170 tokens of question wording sent with each block.
- Batched design: send a window of blocks once and ask one pair question per joint (about 21 extra tokens each). For a 10-K that is about 105K tokens of text (plus overlap) + about 1,000 × 21 ≈ 21K tokens of questions, roughly $0.005–0.01, about 10–20x cheaper than per-block.
- The risk of batching is that Jev "accuracy falls as state grows with unrelated content". Mid-size windows (e.g. 10–30 blocks, a few thousand tokens) with many pair questions are the likely sweet spot. This needs testing.
- A local encoder (Chonky-style or a distilled cross-segment model) costs nothing per call once running, but needs a GPU or CPU host and validation on filings. A local generative 0.5–1.5B model used for PPL dips is also free per call, but has no evidence on tables or financial text.

### Gaps
- No trustworthy prefill tokens/second figures for 0.5B–8B models on our hardware. These would need measuring with `vllm bench`.
- TypeSafe gives no limit on questions per request and no tests of interference at hundreds of questions.

## 8. Failure mode: a cut separates a sentence or table from the title or unit line it needs. What avoids it?

### Takeaway
The best-supported fix is structural, not model-based. Start a new chunk at each title, keep each table whole with its caption, and never let a heading or label end a chunk. Element-based chunking of financial reports raised Q&A accuracy over fixed 512-token chunks with fewer chunks. Narrow "does B continue A?" wording beats broad "same topic?" wording for Jev.

### Cited Findings
- Element-based chunking of financial reports (FinanceBench, 141 questions over 80 documents) used these rules: elements under 2,048 characters merge with the following element; a new chunk starts at each **title** element; a **table starts a new chunk and is kept whole**. — [Financial Report Chunking HTML](https://arxiv.org/html/2402.05131v3)
- Its results:

  | Strategy | Q&A accuracy (manual) | Chunks |
  |---|---|---|
  | Base 128 tokens | 35.46% | – |
  | Base 512 tokens | 48.23% | – |
  | Element-based ("Keywords Chipper") | **53.19%** | – |
  | Base Aggregation | – | 112,155 |
  | Chipper Aggregation | – | 62,529 |

  Chipper Aggregation also had the best page-retrieval accuracy, 84.40 vs 83.69. — [Financial Report Chunking HTML](https://arxiv.org/html/2402.05131v3)
- NVIDIA kept tables and charts as whole units and never chunked them. — [NVIDIA blog](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/)
- Context loss is the core risk in financial text. Anthropic's example chunk, "The company's revenue grew by 3% over the previous quarter.", lacks the company and period.
  - Adding a model-written context line cut top-20 retrieval failures by 35% (5.7%→3.7%).
  - With contextual BM25 the cut was 49% (→2.9%); with reranking, 67% (→1.9%).

  — [Anthropic](https://www.anthropic.com/news/contextual-retrieval)
- Wording matters for Jev. In TypeSafe's structure-recovery cookbook:
  - The question that worked was "Does line {i} pick up mid-sentence, continuing a sentence left unfinished at the end of line {i-1}?", with explicit true/false criteria and both lines quoted in full.
  - Asking whether two lines are "part of the same paragraph" instead wrongly merged list items (13 blocks instead of 17).
  - Thresholds were set in code by context: join if p ≥ 0.2 after a line with no end punctuation, p ≥ 0.5 after `. ! ? : ;`.
  - The thresholds were hand-set on a single memo, and no labelled accuracy was reported.

  — [TypeSafe autoformat](https://docs.typesafe.ai/cookbooks/autoformat.md)
- Jev limitations relevant here:
  - It reads questions literally.
  - Accuracy drops with large or irrelevant input.
  - In Choice questions it leans toward the first option.
  - It is weak on counting, dates and math.
  - Mismatched phrasing hurts, e.g. a yes/no question where "true" means "no".

  — [TypeSafe model jaggedness](https://docs.typesafe.ai/model-jaggedness.md)
- Seeing both sides of a candidate break is essential: F1 20.2 with left context only vs 64.0 with both sides. — [Lukasik et al. 2020 PDF](https://arxiv.org/pdf/2004.14535)
- Methods that output indices or regex rather than text avoid hallucinated or altered quotes. — [Chroma research](https://www.trychroma.com/research/evaluating-chunking); [MoC HTML](https://arxiv.org/html/2503.09600v2)

### Inferences
- Most "orphaned title/unit line" errors can be removed by free code rules on our existing blocks:
  - headings, table captions and lines ending in ":" attach forward;
  - "(in millions…)" / unit lines attach to the next table;
  - a table is never split.
  The model is then only needed for prose-to-prose joints.
- Our Jev result (0 of 51 real ties split, 30 of 55 real separations found) is the safe kind of error for recall. Jev merges too much, which only costs tokens. The probability output should be thresholded on our labelled pairs (as the cookbook did), not taken as a hard yes/no.

### Gaps
- No published measurement of how often cuts orphan a unit line or table title in SEC filings.

## Implications for the design above

### Takeaway
Let **code rules make most cuts** (headings, tables, captions, unit lines, lead-ins ending in ":"). Use **Jev only on prose-to-prose joints, batched** (many pair questions per shared window), with narrow "does B depend on / continue A?" wording and a probability threshold tuned for zero tie-splits. A free local model is a reasonable thing to test later, but there is no evidence yet that it works on filings. Do not chase "one Driver per chunk" by cutting text in order; group by Driver after extraction instead.

### Cited Findings
- Structure rules (title starts a chunk, table kept whole) beat fixed-size chunks on financial reports: 53.19% vs 48.23% Q&A accuracy. — [Financial Report Chunking HTML](https://arxiv.org/html/2402.05131v3)
- On real documents, smart (semantic) chunking rarely beats simple chunking; gains appear on stitched, multi-topic text. — [arXiv HTML 2410.13070](https://arxiv.org/html/2410.13070)
- Jev's batched questions on one input are 12.2x cheaper with no change in answers. — [TypeSafe parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md)
- Narrow continuation wording beats broad "same paragraph" wording for Jev. — [TypeSafe autoformat](https://docs.typesafe.ai/cookbooks/autoformat.md)
- Supermemory's Jev chunker used a "continue vs new" question per sentence. It scored 93% on retrieval and cost about 10x rule-based chunking. — [Supermemory blog](https://supermemory.ai/blog/jev-memory-context-engineering)
- Pick-one-of-many formats (LumberChunker-style) failed with a 7B open model, and Jev's Choice has a first-option bias. — [Meta-Chunking v1 HTML](https://arxiv.org/html/2410.12788v1); [TypeSafe model jaggedness](https://docs.typesafe.ai/model-jaggedness.md)
- Haiku 5.5 input is $0.10/MTok (prompts ≤100K tokens), about 2.4x Jev's $0.042. — [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing)

### Inferences
**Who decides cuts:**

| Joint type | Decider | Why |
|---|---|---|
| heading / caption / unit line / ":" lead-in → next block | **rules (never cut)** | free; the main failure mode; strong evidence |
| table ↔ its title/notes | **rules (keep together)** | tables kept whole in both financial studies |
| prose ↔ prose under the same heading | **Jev, batched** | the only joints that need judgement |
| any joint, as an optional cheaper path | local model (PPL dip with Qwen 0.5–1.5B, or Chonky-style encoder) | free per call; unproven on filings |

**Best-supported question format for Jev:**
- Use a yes/no (Noul) per joint, not a pick-one over block IDs.
- Quote both blocks in full, so the model sees both sides of the break.
- Ask about dependence or continuation, not about "topic". For example: "Does block B rely on block A to be understood (A is its title, unit line, lead-in, or the same item it continues)?", with explicit true and false criteria.
- Pick the cut threshold from probabilities on our labelled pairs. Choose the threshold that keeps 0 of 51 ties split, then report how many of the 55 separations it catches.
- Optionally use a different threshold depending on how A ends (":" vs "."), as the cookbook did.

**Cost:**
- At the current ~1,170 tokens per block, a 10-K cut pass could cost about 10x what Haiku 5.5 would pay to read the whole 10-K. That uses my guess of about 1,000 blocks and the project's measured $0.00012 per block.
- Batching joints per window (about 21 tokens per extra question) should bring the cut pass to about $0.005–0.01 per 10-K.
- If the smart reader is Haiku 5.5, saving reading tokens with smarter cuts is worth at most a few cents per 10-K. **Recall, not cost, is the only reason to cut cleverly.**

**The owner's ideal ("one Driver per chunk"):** cutting text in order cannot deliver it, because one Driver's facts are spread across the document. Aim for "never separate a fact from its context" when cutting. Get "one Driver, all its facts" by grouping the extracted updates by Driver afterwards.

**What to test, in order:**
1. **Rules-only baseline.** On the existing labelled pairs (51 tied / 55 separate), how many ties do the code rules alone protect, and how many prose joints are left for a model?
2. **Wording A/B on Jev.** Compare "depends on / continues" with "starts a new topic", using probability curves (not yes/no). Measure the separation catch rate at a threshold with zero tie-splits.
3. **Batched vs per-block Jev.** Same questions in windows of 10, 30 and 100 blocks. Check whether answers drift (the large-input risk) and the cost per 1,000 blocks. Also reconcile the $0.033 vs $0.0135 discrepancy.
4. **Free local option.** Run PPL-dip scores (Qwen2.5-0.5B/1.5B via Meta-Chunking code) and Chonky on the same pairs. Report the same metric.
5. **End-to-end recall (the real test).** Extract Drivers from a few 8-Ks and 10-K sections with (a) fixed 8,000-character cuts with overlap, (b) rules-only cuts, and (c) rules + Jev cuts. Count missed updates and broken quotes. If (a) or (b) already reaches about 100% recall, the model cut pass is not worth its cost.

### Gaps
- There is no published evidence for any segmenter on SEC filings or earnings calls, so tests 1–5 above are the only way to settle the choice.
- I did not verify Jev's "~21 extra tokens per question" or the per-request and per-question context limits in TypeSafe docs. Those figures come from the project brief.
