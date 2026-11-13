# Cutting LLM document-processing cost without losing recall (cascades with guarantees, safe filters, skipping repeated filing text)

Researched 11 Nov 2026. "Recall" = share of true facts we find. "Proxy" = cheap model whose score decides what the expensive model sees. "Oracle" = the expensive model (or human) treated as ground truth. "Guarantee" below always means "target met with probability ≥ 1−δ", never "always".

Note on sources: items marked **(search summary)** were seen only through a search-result summary, not the full page. Items marked **(my calculation)** are arithmetic I did, not a published number.

## 1. Proxy-model filtering with guarantees (SUPG, BARGAIN, LOTUS, Abacus/Palimpzest, FrugalGPT, RouteLLM, Trust-or-Escalate)

### Takeaway
Only SUPG, BARGAIN, LOTUS cascades and "Trust or Escalate" give a stated statistical guarantee. BARGAIN (SIGMOD'26) is the current best. It uses a sample of ~400 oracle labels. Its "recall target" query is exactly our pre-filter problem: find every block that holds a fact, while sending as few blocks as possible to the smart model. But every published test used recall targets of 0.8–0.9, not ~1.0. BARGAIN also proves that with few positive examples, no method can both guarantee the target and save much. FrugalGPT, RouteLLM and Abacus report big savings (up to 98% / >2x / 10.8x) but give no per-item recall guarantee.

### Cited Findings
- **BARGAIN**: "Cut Costs, Not Accuracy: LLM-Powered Data Processing with Guarantees", by Zeighami, Shankar and Parameswaran. Posted 2 Sep 2025 (v2 12 Sep 2025), to appear at SIGMOD'26. Tested on 8 real datasets, it "reduces cost, on average, by up to 86% more than state-of-the-art" — [arXiv 2509.02896](https://arxiv.org/abs/2509.02896)
- How BARGAIN works: records whose proxy score is ≥ a threshold ρ are accepted by the proxy alone. ρ is chosen from candidates using labeled samples. The statistical test is the Waudby-Smith & Ramdas (2024) "betting" test. It adapts to the data's variance and stays valid even when sampling stops early. The naive baseline uses a Hoeffding bound instead. The guarantee holds per query, with probability taken "over runs of the algorithm". The user picks the failure chance δ — [BARGAIN full text §2.1–2.3, §4.2](https://arxiv.org/html/2509.02896v2)
- BARGAIN defaults: oracle-label budget **k = 400**, target **T = 0.9**, **δ = 0.1**. The adaptive recall variant (BARGAIN_R-A) "assigns half of the sampling budget to the binary search and half to find the cascade threshold"; it also sets β = 0.02 and r = 150 — [BARGAIN §5–6](https://arxiv.org/html/2509.02896v2)
- Datasets and positive rates (share of records that are true positives): Review 0.23, Court 0.59, Screen 0.22, Wiki 0.25, Onto 0.02, ImageNet 0.001, Tacred 0.02, NS 0.29. Sizes run from 855 to 973,085 records — [BARGAIN Table 4](https://arxiv.org/html/2509.02896v2)
- **Recall-target results at T = 0.9** (Table 5c). The number is precision: the share of records sent onward that really were positive, so higher means less waste. BARGAIN_R-A vs SUPG:
  - Review 39.7 vs 34.3
  - Court 82.0 vs 77.5
  - Screen 33.0 vs 27.9
  - Wiki 50.9 vs 45.9
  - Onto 28.0 vs 13.2 (SUPG **missed** its target here)
  - ImageNet 97.8 vs 90.3
  - Tacred 22.0 vs 11.1
  - NS 56.1 vs 45.3
  - The uniform-sampling variant BARGAIN_R-U collapses on the rare-positive sets: Onto 2.5, ImageNet 0.1, Tacred 2.4 — [BARGAIN Table 5c](https://arxiv.org/html/2509.02896v2)
- **Accuracy-target results at T = 0.9** (Table 5a): share of expensive-model calls avoided, BARGAIN_A-A vs SUPG:
  - Review 41.8% vs 3.2%
  - Court 48.0% vs 24.4%
  - Screen 0.0% vs 1.5%
  - Wiki 48.1% vs 4.4%
  - Onto 97.7% vs 73.5%
  - ImageNet 99.7% vs 84.7%
  - Tacred 97.0% vs 80.1%
  - NS 65.3% vs 7.5%
  - The text says "BARGAIN increases proxy model usage up to 10× over SUPG" — [BARGAIN Table 5a](https://arxiv.org/html/2509.02896v2)
- **Impossibility result** (Lemma B.11): when there are few positives, no method can guarantee the target and still be useful. To get past this, users can set β > 0, which "weaken[s] the theoretical guarantees". On Onto, BARGAIN_R-A stops meeting the target at β ≥ 0.05 — [BARGAIN §1, App. B](https://arxiv.org/html/2509.02896v2)
- Calibration: if the proxy's scores are badly calibrated, the guarantee still holds but the saving can be small — [BARGAIN §2.2](https://arxiv.org/html/2509.02896v2)
- **SUPG** ("Approximate Selection with Guarantees using Proxies", Kang, Gan, Bailis, Hashimoto, Zaharia; PVLDB 2020). Its algorithms "meet a minimum precision or recall target with high probability" and "improve query result quality by up to 30x" compared with earlier methods. Earlier methods "can catastrophically fail" to meet targets — [arXiv 2004.00827](https://arxiv.org/abs/2004.00827)
- BARGAIN's critique of SUPG: SUPG's guarantee relies on large-sample (central-limit) math, so it only holds in the limit. In an adversarial ImageNet test, "SUPG misses the target more than 75% of the times" even though δ = 0.1 allowed only 10% — [BARGAIN](https://arxiv.org/html/2509.02896v2)
- **LOTUS** (Patel et al., "Semantic Operators", v3 1 Mar 2025). Its optimizations speed up semantic filter, join, group-by and top-k "by up to 1,000×". It "reduces cost, while providing accuracy guarantees with respect to a gold algorithm". It runs "up to 3.6× faster than the highest-quality baselines" — [arXiv 2407.11418](https://arxiv.org/abs/2407.11418)
- LOTUS cascade settings (docs):
  - `recall_target` default 0.8 ("Increase this when missing true positives is costly")
  - `precision_target` default 0.8
  - `failure_probability` default 0.2
  - `sampling_percentage` default 0.1 ("Fraction of proxy-scored items sampled for threshold learning")
  - Two learned thresholds: positive and negative. Items in between go to the main LM.
  - Proxy is either a helper LM (default) or an embedding model.
  - The docs give no benchmark savings — [LOTUS docs: approximation cascades](https://lotus-ai.readthedocs.io/en/latest/approximation_cascades.html)
- **Abacus** (MIT, the cost-based optimizer inside Palimpzest). It optimizes quality, dollar cost or speed, under limits on the others, using "a minimal set of validation examples". v3 (PVLDB 19(5), 2026) reports 6.7%–39.4% better quality, 10.8x cheaper and 3.4x faster than the next best system. v1 had reported 18.7%–39.2% better quality and up to 23.6x lower cost. **(search summary)** — [arXiv 2505.14661](https://arxiv.org/abs/2505.14661v3)
- **FrugalGPT** (Chen, Zaharia, Zou, May 2023): a learned cascade of LLMs "can match the performance of the best individual LLM (e.g. GPT-4) with up to 98% cost reduction". This is average task accuracy; there is no per-item recall guarantee — [arXiv 2305.05176](https://arxiv.org/abs/2305.05176)
- **RouteLLM** (Ong et al., v4 Feb 2025): a router trained on human preference data picks a strong or weak model per query. It "significantly reduces costs-by over 2 times in certain cases-without compromising the quality of responses". No guarantee is stated — [arXiv 2406.18665](https://arxiv.org/abs/2406.18665)
- **Trust or Escalate** (Jung, Brahman, Choi; ICLR 2025). A cascade starts with a cheap judge and escalates to a stronger one when the cheap one is unsure. Confidence cut-offs are set on a small calibration set with fixed-sequence testing. The result: "guarantees over 80% human agreement with almost 80% test coverage" even when using Mistral-7B **(search summary)** — [arXiv 2407.18370](https://arxiv.org/abs/2407.18370)

### Inferences
- Our Jev pre-filter maps onto BARGAIN's recall-target query:
  - proxy = Jev's P(fact or label) per block
  - oracle = the smart LLM, or a human label
  - goal = keep recall ≥ T and drop as many "nothing" blocks as possible
- No published system was tested at T ≥ 0.99. At our target, the impossibility result means the threshold will be very low unless we label many positive blocks. Expect much smaller savings than the 0.9-target tables show.
- Low positive rates are where proxy savings were largest (Onto, Tacred, ImageNet: 97–99.9% of expensive calls avoided at T = 0.9). Our "nothing" share (~43% of press-release words) means positives are common, not rare. That makes a big proxy saving less likely than in those datasets.
- FrugalGPT- and RouteLLM-style routing optimizes *average* quality. Do not use it as a recall-safety argument for exhaustive extraction.

### Gaps
- No paper found that tests these methods at recall targets of 0.99–0.999.
- SUPG's exact sampling scheme and label budgets were not re-read here. My memory of "importance sampling weighted by proxy score" is unverified.
- DocETL (Shankar et al.) was not researched.
- The MOAR optimizer claim ("27% higher accuracy than ABACUS") came only from a search snippet. Unverified, and the source paper was not identified.

## 2. Estimating and certifying a recall target statistically

### Takeaway
To show "recall ≥ 99.5% with 95% confidence" with zero misses, the audit needs about **598 true facts**, and every one must be found. Allowing even one miss raises this to about **947 facts**. Our current Jev evidence (0 lost out of 119) only shows that loss is **≤ 2.5%** at 95% confidence. The e-discovery field (legal document review) has proven methods to certify recall by sampling, and a key lesson: overshooting the target costs more than a bigger audit sample.

### Cited Findings
- Rule of three: if 0 events occur in n trials, "the interval from 0 to 3/n is a 95% confidence interval for the rate". The general form is −ln(α)/n. For 99% confidence the numerator is 4.61; for 99.5% it is 5.3. The rule "is a good approximation" when n > 30 — [Wikipedia: Rule of three (statistics)](https://en.wikipedia.org/wiki/Rule_of_three_(statistics))
- **(my calculation, exact binomial):** number of true facts that must all be found, with zero misses:

  | Recall bound | 95% confidence | 99% confidence |
  |---|---|---|
  | ≥ 99% | 299 | 459 |
  | ≥ 99.5% | 598 | 919 |
  | ≥ 99.9% | 2,995 | 4,603 |

- **(my calculation, exact Clopper–Pearson bounds at 95%):**
  - 1 miss in 600 → miss rate ≤ 0.79%
  - 1 miss in 1,000 → ≤ 0.47%
  - 2 misses in 1,000 → ≤ 0.63%
  - With 1 miss allowed, ≥ 947 facts are needed to certify ≤ 0.5% misses
- **(my calculation):** our test had 0 of 119 fact/label blocks dropped. 95% upper bound = 1 − 0.05^(1/119) = **2.49%**; the rule of three gives 3/119 = 2.52%.
- Lewis, Yang and Frieder, "Certifying One-Phase Technology-Assisted Reviews" (CIKM 2021). "Technology-assisted review" is the legal-discovery practice of using a model to find relevant documents.
  - "Most stopping rules for one-phase TAR workflows lack valid statistical guarantees."
  - They give "the first broadly applicable and statistically valid sample-based stopping rules": QPET and QBCB, which work for any sample size and recall target.
  - Cormack and Grossman's Target rule is the one earlier valid rule, and it is a special case of QBCB.
  - Overshooting the recall target "is a major source of excess cost", and paying "a larger sampling cost to reduce excess recall leads to lower total cost" in almost all scenarios.
  - Sources: [arXiv 2108.12746](https://arxiv.org/abs/2108.12746); QBCB/QPET details from a **(search summary)**
- BARGAIN's guarantee is per run ("over runs of the algorithm") with a user-set δ. Default δ = 0.1, i.e. 90% confidence — [BARGAIN](https://arxiv.org/html/2509.02896v2)

### Inferences
- Count **facts**, not blocks. A block holding 3 facts that gets dropped is 3 misses.
- Stratify the audit by document type: 10-K, 10-Q, 8-K press release, transcript, news. Certify each type separately or weight the results. One mixed sample can hide a weak document type.
- An "elusion" audit (sampling only from what the filter removed) is cheaper than auditing everything. Sample n dropped blocks, have the smart LLM or a human read them, count facts found. Facts missed ≈ (rate found in the dropped sample) × (number of dropped blocks). Turn that into a recall bound using the total fact count.

### Gaps
- QBCB's actual sample-size tables were not retrieved.
- Facts per block and per document in our corpus are unknown, so the number of documents needed to collect ~600 facts is unknown.

## 3. Skipping text repeated from a company's earlier filings

### Takeaway
Filings are highly repetitive year over year:
- **Lazy Prices**: median word-frequency (cosine) similarity between a firm's consecutive filings = **0.947**; mean = **0.872**; 327,130 filing pairs.
- **Our measurement**: ~55% of sentences repeat (project figure, not from these sources).

The same paper shows the *changes* are where the price-moving information sits: a portfolio built on them earned up to 188 basis points (1.88%) per month. So "skip unchanged, read changed" points the work at the right text. The risk: an identical sentence can mean something new in a new period.

### Cited Findings
- **Lazy Prices** (Cohen, Malloy, Nguyen; Journal of Finance 75(3):1371–1415, 2020; NBER WP 25084). Data: US 10-Ks and 10-Qs, 1995–2014.
  - Shorting "changers" and buying "non-changers" earns "up to 188 basis points in monthly alphas" (excess return), "over 22% per year".
  - Changes to executive-team, litigation and risk-factor language are especially informative.
  - Sources: [NBER w25084](https://www.nber.org/papers/w25084); [PDF](https://www.nber.org/system/files/working_papers/w25084/w25084.pdf)
- Lazy Prices Table I, Panel B: similarity between consecutive filings, 327,130 pairs. Mean / median / 1st–99th percentile:
  - Sim_Cosine: 0.872 / 0.947 / 0.137–0.995
  - Sim_Jaccard: 0.395 / 0.411
  - Sim_MinEdit: 0.376 / 0.393
  - Sim_Simple: 0.146 / 0.117
  - Sources: [Lazy Prices PDF, Table I](https://www.nber.org/system/files/working_papers/w25084/w25084.pdf)
- Lazy Prices Table I, Panel A: average 10-K = 44,509 words (median 35,787); average 10-Q = 15,806 words (median 10,674). Comparison rules: a 10-K against the prior year's 10-K; a 10-Q against "the same quarter's 10-Q in the prior year". Changes were found with Unix `diff` or Word "Track Changes" — [Lazy Prices PDF](https://www.nber.org/system/files/working_papers/w25084/w25084.pdf)
- Lazy Prices: MD&A (management's discussion, 10-K Item 7 / 10-Q Item 2) has the lowest average year-to-year similarity of any section. Of the changes, 86% carry negative sentiment, measured with word-list scoring. CEO/CFO changes are mentioned in about 2–5% of reports — [Lazy Prices PDF](https://www.nber.org/system/files/working_papers/w25084/w25084.pdf)
- Dyer, Lang and Stice-Lawrence (Journal of Accounting and Economics 64:221–245, 2017), 10-Ks 1996–2013:
  - Length, boilerplate, "stickiness" (text carried over from earlier years) and redundancy all rose.
  - Specificity, readability and the relative amount of hard information fell.
  - Median length roughly doubled, from ~23,000 to ~50,000 words.
  - **(search summary)** — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jaecon/v64y2017i2p221-245.html)
- Example of a large change: Citigroup's 10-K Jaccard similarity fell from 0.72 (2006) to 0.50 (2007), while peer banks barely changed **(search summary)** — [Research Affiliates](https://media.researchaffiliates.com/1117_nlp_for_long_horizon_factor_investing_d39e26f476.pdf)

### Inferences
- Bag-of-words cosine overstates how much exact text repeats. Our ~55% exact-sentence repeat sits between Jaccard (~0.40) and cosine (~0.95), so it is believable.
- **Design rule:** diff each 10-Q against the same quarter last year *and* against the prior quarter. Diff each 10-K against last year's 10-K. Send changed sentences, plus a little unchanged text around them for context, to the smart LLM.
- Reuse earlier extraction results for unchanged sentences, keyed by an exact-text hash plus the company. Mark reused results as "carried forward", not as new updates.
- **Risks** for identical sentences:
  1. Words like "this quarter", "currently" or "as of the date of this report" make an identical sentence a new statement for a new period.
  2. A sentence can point to a table or number that changed ("as shown below").
  3. Repeating guidance unchanged can itself be a Driver update.
  4. A sentence can be identical while the text *around* it was deleted. Deletions are also signals: Lazy Prices counts deletions as changes.
- **Safest version:** skip only identical sentences that contain no number, date, period word or cross-reference. Process deletions as their own events.

### Gaps
- No public study found that measures extraction recall when unchanged text is skipped.
- No published tools found for incremental or diff-based LLM processing of SEC filings.
- Lazy Prices reports similarity of whole documents, not the share of identical sentences.

## 4. Safe pre-filters: rules vs models

### Takeaway
I found no published evidence that any filter removes text from financial filings with zero loss at scale. Exact-match rules are the only filters whose removals can be checked by hand. Model-based dropping or compression is measured by average task quality, not by recall of every verbatim fact. Our own trial confirms the risk: dropping single sentences with Jev broke meaning.

### Cited Findings
- **Prompt compression (LLMLingua-2**, Findings of ACL 2024): "compression ratios of 2x-5x", "3x-6x faster" than earlier compression methods, end-to-end speed-up "1.6x-2.9x". Tested on MeetingBank, LongBench, ZeroScrolls, GSM8K and BBH. The abstract gives no retention percentage and no verbatim-quote recall measure — [arXiv 2403.12968](https://arxiv.org/abs/2403.12968)
- Boilerplate and redundancy in 10-Ks rose from 1996 to 2013. That means more removable text, but it is spread through the document, not confined to labeled sections **(search summary)** — [Dyer et al. 2017](https://ideas.repec.org/a/eee/jaecon/v64y2017i2p221-245.html)
- Proxy-filter guarantees (Section 1) are the model-based alternative to rules. They hold only with probability 1−δ and only at the tested target — [BARGAIN](https://arxiv.org/html/2509.02896v2)

### Inferences
- Rule candidates that are verifiable by exact match:
  - page numbers and running headers
  - table of contents
  - exhibit index
  - signature block
  - certification exhibits (EX-31/32) — their text is fixed by rule
  - the standard forward-looking-statement (safe-harbor) paragraph, **only if** it exactly matches the company's own earlier version
  - transcript operator/logistics lines
- A safe-harbor paragraph can gain a new risk item. So match per company against last year's text, and send any changed version to the smart LLM.
- Our numbers **(my calculation)**:
  - ~43% of press-release words were labelled "nothing"; Jev caught 58 of 142 nothing-blocks (41%).
  - If block sizes are proportional, Jev removes about **17.6%** of words (0.43 × 58/142).
  - The rest of the 43% is a ceiling for what rules plus a stricter threshold could add.

### Gaps
- No public word-share breakdown of boilerplate per 10-K section.
- No study found of how much fact-free boilerplate is in 8-K press releases or call transcripts.

## 5. Using structured XBRL data that already exists

### Takeaway
Financial statements in 10-K and 10-Q filings are tagged fact by fact in XBRL (a machine-readable data format). The SEC's company-facts API serves this data free. For 8-Ks, the SEC requires tagging only for the **cover page**, so earnings press releases (Exhibit 99.1) are normally untagged. Research uses XBRL to check LLM extraction, but treats it as imperfect.

### Cited Findings
- 2019 FAST Act rules: "Registrants will be required to tag all cover page data for Forms 10-K, 10-Q, 8-K, 20-F, and 40-F in Inline eXtensible Business Reporting Language", phased in over three years — [SEC compliance guide](https://www.sec.gov/resources-small-businesses/small-business-compliance-guides/fast-act-modernization-simplification-regulation-s-k); [Release 33-10618](https://www.sec.gov/files/rules/final/2019/33-10618.pdf)
- SEC staff guidance (CDI): all Forms 8-K are subject to cover-page tagging, "not only those that contain financial statements for which XBRL data is required". The financial-statement data file (Rule 405) goes in Exhibit 101; the cover-page file (Rule 406) in Exhibit 104 — [SEC Interactive Data CDI](https://www.sec.gov/rules-regulations/staff-guidance/compliance-disclosure-interpretations/interactive-data-cdi)
- Example filing: Iron Mountain's earnings 8-Ks attach the press release as Exhibit 99.1, with only the cover page tagged — [Iron Mountain 8-K, Aug 2024](https://www.sec.gov/Archives/edgar/data/1020569/000102056924000208/irm-20240801.htm). This is one company's filings, not the rule itself.
- A NeurIPS 2026 paper checks LLM extraction from 10-K Item 8 against Inline XBRL facts. Eight open-weight models (8B–70B) covered only **47.7%** of XBRL values; a repair step raised this to **53.0%**. Coverage is not the same as accuracy **(search summary)** — [NeurIPS 2026](https://neurips.cc/virtual/2026/166661)
- FinTagging benchmark: LLMs extracting numeric facts from 10-Ks and linking them to US-GAAP concepts show "a substantial performance gap". Top models reach F1 > 0.69 on extraction; linking to the right concept is weaker **(search summary)** — [arXiv 2505.20650](https://arxiv.org/html/2505.20650v1)
- XBRL tagging errors are still common in SEC data (FinVerBench, per a search summary; the paper was not opened) **(search summary)**.

### Inferences
- For 10-K/10-Q statement line items:
  - Read values from XBRL instead of having the LLM read the tables.
  - Inline XBRL tags sit inside the filing's HTML, so the exact verbatim location of each tagged number is recoverable. That meets our exact-quote rule without the LLM.
  - Keep the LLM for narrative text (MD&A, risk factors, notes text).
  - Use XBRL as a cross-check on LLM-extracted numbers, not as a perfect ground truth.
- 8-K press releases, the main earnings-day source, get no XBRL help. Their numbers must still be extracted from text and tables.

### Gaps
- The token share of statement tables in a 10-K/10-Q was not found, so the saving is unknown. Measure it on our own documents.
- No practitioner write-up found on skipping LLM extraction because XBRL exists.

## 6. Cost levers for the expensive model (caching, batching, small-first, output length)

### Takeaway
- Prompt-cache reads cost **0.1x** normal input price (**0.05x** on Opus 5.5 and Sonnet 5.5). Cache writes cost 1.25x (5-minute life) or 2x (1-hour life).
- The Batch API halves all prices, and the two discounts stack.
- Output tokens cost **5x** input tokens on current models. So writing out verbatim quotes is expensive.
- On a subscription these dollar prices do not apply directly. How cache reads count against usage limits is unverified.

### Cited Findings
- Prompt caching:
  - "Cache write tokens with a 5-minute TTL are 1.25 times the base input tokens price"; 1-hour = 2x; "Cache read tokens are 0.1 times the base input tokens price".
  - Exceptions: Opus 5.5 and Sonnet 5.5 cache reads are "0.05x the base input price"; Fable/Mythos 5.1–5.2 are 0.025x.
  - Minimum cacheable prompt: 512 tokens (Opus 5.5, Sonnet 5.5, Haiku 5.5, among others); 4,096 tokens (Haiku 4.5, Opus 4.5/4.6). Shorter prompts are silently not cached.
  - The default life is 5 minutes, refreshed free on each use.
  - Caching "has no effect on output token generation".
  - The multipliers "stack with … the Batch API discount".
  - Source: [Claude prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- Batch API:
  - "All usage is charged at 50 percent of the standard API prices."
  - Up to 100,000 requests or 256 MB per batch; most finish within 1 hour; batches expire after 24 hours.
  - Cache hits inside batches are "best-effort … typically … 30 percent to 98 percent". Anthropic suggests the 1-hour cache for batches.
  - Source: [Claude batch processing docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing)
- Batch prices per million tokens (input / output):

  | Model | Batch input | Batch output |
  |---|---|---|
  | Opus 5.5 | $2 | $10 |
  | Sonnet 5.5 | $1 | $5 |
  | Haiku 5.5 (prompts ≤ 100K tokens) | $0.05 | $0.25 |
  | Haiku 5.5 (prompts > 100K tokens) | $0.25 | $1.25 |
  | Haiku 4.5 | $0.50 | $2.50 |

  Source: [Claude batch processing docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing). By the 50% rule, Haiku 5.5's standard input price would be $0.10/MTok **(inferred; I did not open the standard pricing page)**.
- Small model first, escalate when needed: FrugalGPT reports up to 98% cost cut at GPT-4-level average accuracy; RouteLLM over 2x. Neither gives a recall guarantee — [FrugalGPT](https://arxiv.org/abs/2305.05176); [RouteLLM](https://arxiv.org/abs/2406.18665)

### Inferences
- Make the shared instructions (extraction rules, Driver definitions, examples) a fixed, cache-marked prefix of at least 512 tokens. Put the document chunk after it.
- Output control: have the model return block IDs and character offsets instead of retyping quotes. Then rebuild the verbatim quote in code from the source text. This saves output tokens (5x price) and makes "exact verbatim" true by construction.
- Haiku 5.5 batch input ($0.05/MTok) is within ~1.2x of Jev's $0.042/MTok, and Haiku can write text. But Jev's output costs $0, Jev returns calibrated probabilities, and Jev bills a shared input once per many questions. Worth a head-to-head test as the cheap tagger.

### Gaps
- No source found on how prompt-cache reads count against Claude subscription usage limits. This matters because the user runs on a subscription.
- No published measure of output-token savings from offset-style output in extraction tasks.

## 7. Jev-style call cost at scale; cheaper classifier alternatives

### Takeaway
Jev costs **$0.042 per million input tokens** and **$0.00 for output**. Putting all questions in one request that shares one input was **12.2x cheaper and 11.8x faster** than one request per question (13 questions, ~54K-character article). At this price, one full pass over 100K documents costs about $100–$200 **(my calculation)**. So Jev's cost is small next to smart-LLM time. The real lever is how many smart-LLM tokens Jev lets us skip.

### Cited Findings
- Jev in brief:
  - "$42" "Per Billion input tokens"
  - "238x Lower input price than Claude Fable 5.1"
  - A workflow example: 0.114 s vs 8.566 s ("193.6x Faster, 444.6x Cheaper") on "System One tasks"
  - Source: [typesafe.ai](https://typesafe.ai)
- Jev takes a "state" (text, JSON or images) plus typed questions: choice, score, noul (0–1) and box. "Every question is evaluated in parallel and in isolation against the same state in one go." "Adding questions barely changes the response time." Billing for multi-question requests is not stated on that page — [TypeSafe docs intro](https://docs.typesafe.ai/introduction)
- Parallel-questions cookbook (averaged over 5 runs):
  - One call with 13 questions: $0.000497, 0.24 s
  - 13 single-question calls: $0.006090, 2.81 s
  - Price in code: `PRICE = (0.042, 0.00)` per million (input, output), "as of 2026-11"
  - "the 13 single-question calls re-send the article 13 times; the batched call sends it once"
  - "The bigger the document, the nearer that saving comes to a full Nx"
  - The page does not say how question text is billed.
  - Source: [TypeSafe parallel_questions cookbook](https://docs.typesafe.ai/cookbooks/parallel_questions.md)
- Free local option, ModernBERT (an encoder classifier, i.e. it scores text but does not generate it):
  - ~76.2K tokens/s on 512-token inputs in one benchmark (BERT 98.1K, RoBERTa 97.4K) — [BioClinical ModernBERT](https://arxiv.org/pdf/2506.10896)
  - ~60,000 tokens/s on an NVIDIA A10G for a financial token-classification variant — [Spatial ModernBERT](https://arxiv.org/pdf/2507.08865)
  - Processes 8,192-token sequences "almost two times faster than previous models" — [ModernBERT](https://arxiv.org/html/2412.13663v2)
  - These figures come from different hardware **(search summary)**.

### Inferences
- **Cost estimate (my calculation):** 100K docs × ~30K tokens average ≈ 3 billion tokens ≈ **$126 per full Jev pass** if the document is sent once. The 30K average is my assumption; a 10-K is ~105K tokens, an 8-K press release ~5.5K.
- Re-sending the document once per question multiplies that cost. This matches the project's finding that question wording dominated cost when each call carried little text.
- **Fix:** send one larger state (a group of blocks) and ask all questions about it at once. Keep question wording short and fixed.
- **Local option:** a fine-tuned ModernBERT-class model at ~60–76K tokens/s on one GPU would tag 3B tokens in ~11–14 GPU-hours. But it needs labeled training data. It also needs the same recall certification as Jev.

### Gaps
- Jev's rate limits, context length and throughput were not found in the docs read.
- Whether Jev bills question text once per question or once per request was not found.
- No head-to-head accuracy test of Jev vs Haiku vs a local encoder on our block types.

## 8. Implications for the design above

### Takeaway
The biggest *safe* savings come from cutting smart-LLM tokens without any model judgment:
1. Skip text that is identical to the company's earlier filings.
2. Return offsets instead of quotes.
3. Cache the instructions.
4. Remove blocks with exact-match rules.

Model-based filters (Jev, cheap-model-first) come last. They need an audit of ~600+ facts per document type before they can claim ≥ 99.5% recall.

### Cited Findings
- Evidence used here: Sections 1–7 above (BARGAIN k = 400 at T = 0.9 and the few-positives impossibility result; rule of three; Lazy Prices median cosine 0.947; caching 0.05–0.1x; output price = 5x input; Jev 12.2x saving from batching questions).

### Inferences
Ranking, with savings measured in smart-LLM tokens, as plain arrows:

| # | Lever | Expected saving | Risk to recall | Evidence / test needed |
|---|---|---|---|---|
| 1 | **Return offsets/IDs, rebuild quotes in code** | Most output tokens (output costs 5x input) | None; also removes misquotes | A/B on ~50 chunks: same facts found? |
| 2 | **Cache shared instructions** (≥ 512-token fixed prefix) | ~90–95% of instruction tokens | None | Measure instruction share of each call; confirm how the subscription counts cache reads (unverified) |
| 3 | **Skip text identical to earlier filings** (10-K vs last 10-K; 10-Q vs same quarter last year and prior quarter) | Up to ~55% of 10-K/10-Q tokens (our measure; Lazy Prices median cosine 0.947) | Medium: period words, cross-references, reaffirmed guidance, deletions | Skip only number-free, date-free, period-word-free sentences; elusion audit: smart LLM reads a random sample of skipped sentences; need 0 facts in ~600 to bound miss rate ≤ 0.5% at 95% |
| 4 | **Exact-match rules** (page numbers, table of contents, exhibit index, signatures, certifications, company-specific safe-harbor text identical to last time, call logistics) | Part of the ~43% "nothing" words in press releases; size unmeasured | Low (each rule checkable) | Run on hand-labelled set: 0 fact blocks removed; then elusion sample at scale |
| 5 | **XBRL for 10-K/10-Q statement numbers** | Statement-table tokens (share unmeasured) | Low–medium (XBRL errors; only covers tagged numbers; none for 8-K press releases) | Measure table token share; cross-check XBRL vs LLM on ~20 filings |
| 6 | **Jev "nothing" filter with certified threshold** (BARGAIN-style recall target) | ~17.6% of press-release words at today's setting (rough, my calculation); less at a 99.5% target | Medium until certified; today only "≤ 2.5% loss" is proved (0/119) | Per document type: ≥ 598 fact-bearing blocks with 0 drops (≥ 947 if 1 drop) for ≥ 99.5% at 95%; count facts, not blocks |
| 7 | **Cheap model reads first, smart model only on flagged chunks** (Haiku or local encoder) | Potentially large (FrugalGPT up to 98%, RouteLLM > 2x, both average-quality) | High: a cheap model misses facts silently; no recall guarantee in those papers | Treat it as a recall-target filter, same audit as #6; test Haiku 5.5 vs Jev head-to-head |
| 8 | **Sentence-level dropping/compression** (LLMLingua-style, the memory company's Jev method) | 2–5x compression; 58% in the memory company's case | High: meaning breaks; no verbatim-recall evidence | Not recommended for extraction |

Order of play: do #1 → #2 → #4 now (no recall risk). Then #3 with its audit. Then #5. Then #6/#7 only after the per-type audits pass.

- Jev's own cost (~$126 per pass, my estimate) is not worth optimizing beyond sharing one state across all questions per request. Spend effort on what Jev lets the smart LLM skip.
- Audit cost is fixed, not per document: ~600–1,000 labelled facts per document type, done once per threshold change. Lewis et al. found bigger samples usually *lower* total cost, because they cut the extra over-filtering that a cautious threshold needs.

### Gaps
- Five unmeasured inputs decide the real ranking. Each needs a small local measurement:
  - token share of statement tables (sizes #5)
  - token share removable by exact rules (sizes #4)
  - share of repeated sentences that contain no numbers or period words (sizes #3)
  - facts per block (sizes the audits)
  - how the subscription counts cache reads (sizes #2)
