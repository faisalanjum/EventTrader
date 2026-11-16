# Brief: extracting earnings-call guidance records with Perplexity Decider v1.3 only

All paths are relative to `/private/tmp/claude-501/-Users-faanjum-Developer-OGAI-ATH-FDE-Group/e991d174-51d6-4b28-9b58-7c680747e192/scratchpad/` unless absolute.

## Owner's requirements (verbatim intent)
- Near-100% extraction of complete, correct guidance records, in the most reliable way.
- Absolutely no over-engineering: no piles of heuristics or custom rules in code; minimalism, as long as all requirements are met.
- As fast as possible (but accuracy first). Accuracy must never drop silently.
- Use only the Decider for now (a generative "reader" model is a fallback only, not the hot path).

## The model and the official documentation (read these; they are the ground truth)
- Model card (official, revision 9c2ebb27, unchanged since 10 Nov 2026): `officialdocs/README.md`
- Blog "Perplexity Decider v1.3: Training, eval, and use cases" (12 Nov 2026), plain text: `officialdocs/blog.txt`
- Official source: `officialdocs/source/src/pplx_decider/{model,protocol,locate,fast,types}.py`; configs `officialdocs/decision_config.json`, `officialdocs/joint_config.json`, `officialdocs/locate-span/locate_config.json`
- Our local MLX runtime (a faithful port; inputs token-identical to the official code): `/Users/faanjum/Developer/local-llm/decider/decider_mlx.py`, guide `/Users/faanjum/Developer/local-llm/decider/USAGE.md`
- Question types: `noul` (P(yes), optional true/false descriptions), `choice` (1-255 options with optional descriptions), `score`, `locate` (verbatim spans with char offsets and scores). Modes: `separate` (official default; one sequence per question) and `isolated` (one sequence; state read once; the state attends to all questions).

## Existing downstream code (EventMarketDB, on another machine; do not need to read)
- `guidance_write_cli.py <items.json> --dry-run|--write`: takes items with label, low/mid/high, unit_raw, basis_norm (gaap|non_gaap|constant_currency|unknown), segment, qualitative, conditions, quote, section, derivation, period fields (fiscal_year, fiscal_quarter, half, long_range_start_year/end_year, time_type) plus top-level fye_month; computes deterministic IDs, period dates, canonical units/values, dedup by slot, validation.
- `_parse_numeric_with_scale(raw)` parses a single money amount like "$1.13B" only (not ranges, not "18.5%").

## What has been measured (Mac M4 Pro, 8-bit MLX port, High Power)
- Speed: ~85 input tokens/s per pass; short requests 1-4 s; a whole call (12-17k tokens) ~2.5-3.5 min per pass. Cost is linear in tokens read.
- Step "which speaker units contain guidance" (other session): whole call as state with a guidance DEFINITION and units tagged [U00].., one isolated request, 59 noul questions, 175 s (15.1k tokens), Cintas Mar-2026 call: all 8 units with saved guidance >= 0.5 (one exactly 0.5), 1 false positive among 50 negatives, 24/24 analyst questions rejected.
- Sentence-by-sentence classification with each sentence alone (523 requests, 30 min): missed "Q4 implied of 7.6" (0.23) and the ERP "100 basis points that you referenced" (0.44) / "something less than that" (0.29). Ablations showed the cause: referents live in other sentences (replacing "implied" with "guidance" -> 0.91; adding the analyst's question -> 0.75).
- Same 172 sentences asked in ONE isolated request with the whole call as state and sentence tags [S#]: 7.6 -> 0.84; ERP -> 0.61 / 0.42; the other 6 saved items' sentences >= 0.97; 27 of 172 sentences >= 0.5 (vs 32 alone); 268 s.
- Locate: abstract label ("text related to management guidance") on a whole call -> 3 of 8 saved items; after unit selection, still 3/8 strict; whole-call Locate with known metric descriptions -> exact values for 5 of 8 (missed tax rate 20% and organic 7.6). Short texts with concrete labels (percentages, money, dates, people, companies, places): 56 of 60 expected spans after a tokenization fix.
- Smoke test on a made-up two-sentence call: Locate "numbers, amounts, percentages and numeric ranges" returned "$1.2 billion to $1.3 billion" as one span; forecast yes/no, metric/period/basis choices all correct.

## Saved reference records (the comparison set; produced earlier by Claude Opus; NOT perfect)
- 6 calls, 54 records: `e2e/calls/<CALL>/snapshot.json` (key `guidance`; for CTAS_2026-03-25T10.00 the key is `records.guidance`), transcript units `e2e/calls/<CALL>/units.json`, text `e2e/calls/<CALL>/source.txt`. Prior (pre-call) metric names: `snapshot.json` key `prior_labels` (CTAS_2026-03-25 has none saved; approximate with the earlier CTAS calls' labels).
- Profile: 47 known metric names, 7 new; 44 numeric, 10 qualitative-only (e.g. "low double-digit", "towards the low end of the ranges for management solutions, PEO and insurance, and total revenue" = 3 records from one sentence); 24 with conditions (paraphrased by Opus); 8 non-Total segments; scopes annual 42, quarter 8, half 2, long/medium term 2; basis unknown 46, non_gaap 7, gaap 1; 4 records share a quote; 26 come from Q&A.

## Codex's plan (verbatim)
1. Preserve the full transcript. Number its existing speaker sections and Q&A exchanges. Keep questions with their answers; retain exact source positions.
2. Find relevant passages in one batch. With the whole transcript as context, ask whether each passage states, changes, reaffirms, withdraws or qualifies management guidance. Retain complete selected passages. Skip the additional sentence-filtering stage.
3. Use the Decider's existing functions to fill our existing fields. First use Locate to identify the forecasted measures, including unfamiliar ones. Then ask narrow questions about each forecast: its value or qualitative expectation, period, company/segment, units, basis and conditions. Use multiple choice for fixed categories, such as whether a number is an exact estimate, range or bound. Several forecasts in one passage must produce separate records, with their fields correctly associated.
4. Let existing code copy, assemble and check. Code preserves exact quotations and performs established normalization and validation. The model supplies the meaning. Missing or incorrectly associated fields count as extraction failures.
- Diagnostic: the official Locate runtime filters out spans below a score of 0.5; check whether correct spans are filtered out before building another span finder.
- Next experiment: step 3 (native Locate plus narrow decisions producing every field from complete passages), testing unfamiliar measures, multiple forecasts and conditions; then untouched transcripts.

## Draft algorithm under review ("value-first")
Per call:
0. Code: speaker units (each prepared-remark section, each analyst question, each management answer) with exact positions; exchange = question + all its answers; header line (company, call date, fiscal year and quarter).
1. Select units: ONE isolated request, whole call as state (definition + [Uxx] tags), one noul per unit (the tested wording). Keep p >= tau1 (recall-first, tuned). Store all probabilities.
2. For each kept unit (state = its whole exchange for Q&A, its section for prepared remarks, plus the header):
   2a. Locate (1 request): "Numbers, amounts, percentages and numeric ranges" and "Growth descriptors without a number (e.g. 'low double digits', 'low end of the range')". Keep spans inside the kept unit.
   2b. Decide (1 isolated request): per value, noul "Is '<value>' a forecast, target or outlook stated or confirmed by management?" with explicit true/false descriptions. Keep p >= tau2.
   2c. Decide (1 isolated request): per kept value, choices: metric (company's existing guidance names + "New measure"), period (options generated by code from the call's fiscal position, e.g. Q4 FY26 / H2 FY26 / FY26 / Q1 FY27 / FY27 / multi-year / unclear), basis (gaap / non_gaap / constant_currency / not stated), segment (Total + the company's known segments + "Other segment"), form (exact / approximately / range / at least / at most / qualitative).
   2d. Locate (1 request): per kept value, "Conditions or assumptions management attaches to the forecast '<value>'"; for "New measure"/"Other segment", the measure or segment name.
3. Code: numbers from the copied value span (one regex) -> low/high per form; unit_raw = the value span; quote = the sentence(s) holding the value (+ condition spans); period fields from the chosen option; existing writer `--dry-run` computes IDs, periods, units, dedup, validation.
4. Reliability: store every probability; auto-accept a record only if every field's top probability >= its tuned threshold; otherwise flag for review/fallback. Also flag kept units that yield no record, uncertain values, new names.
5. Thresholds tuned on a labelled development set; final score on untouched calls (new companies too).
Diagnostics folded into the first run: Locate cutoff (optional request field, default unchanged), a measure-first Locate label for comparison with Codex's anchor, isolated vs separate agreement on a sample.
Estimated cost: about 12-15 min per call (mostly reading text).
