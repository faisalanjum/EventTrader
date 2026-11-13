# Claude Cached Reads

Updated 13 November 2026 (America/Toronto, EST). The [Driver rules](DRIVER_RULES_Categorized.md) remain authoritative: a Driver is a reusable cause or measure; a Driver update is one stated fact about it. Cache reuse has been tested; complete Driver accuracy and the full output implementation have not.

The build plan comes first. [Reference only: evidence and history](#reference-only-evidence-and-history) contains the supporting record and unapproved alternatives.

## Final plan

**Next large-filing trial: four Sonnet 5.5 readers at high effort, each seeing the whole filing, with code checks and targeted retries.** This is a promising starting point, not a proven optimum. Use one reader when sufficient; bound assigned work by answer capacity. No routine second extraction/review pass is added for completeness; checks required by the Driver rules still apply.

### Reading workflow

1. **Reuse the saved source.** Use the existing extracted units and [readback](../../../../driver/prepare/reconstruct.py). Retain original content, IDs, files, order, source locations and versions in code.
2. **Check capacity.** Count actual tokens for instructions, source, IDs and images; reserve reasoning/output room. Do not silently truncate, omit content or rely on compaction for exact evidence. If the full source cannot be shown usefully, use an appropriate authorized larger reader or mark the work unresolved. No partial-view fallback is approved yet.
3. **Prepare the shared request.** Supply the shared task, applicable Driver rules and complete reading view. Treat source content as evidence, not instructions. A task that finishes in one call needs no separate loading call.
4. **Assign the work.** Use consecutive whole-unit ranges, each with one primary owner. For a chosen work-size target, use the nearest permitted unit gap and a consistent tie rule. Keep source IDs unchanged. A unit can contain many facts; one fact per input is unnecessary. If a unit's answer is too large, use existing finer addresses such as table rows while keeping the whole table visible. Do not add parsing just to hit a size target.
5. **For multiple assignments, load and freeze one base.** Supply the complete source and shared instructions, obtain a brief useful response such as source identity, and wait for completion. Each independent copy uses `claude -p --resume BASE_ID --fork-session` with its assignment. Always copy the original base; sibling answers must not accumulate. Every copy sees the whole source.
6. **Keep cache settings fixed.** Pin the same resolved model/version and identical shared prefix; keep effort, tools, instructions and working directory stable. A changing model alias is not a version pin. Use a separate warmed base for a different model or effort. Bound parallel calls and inspect response cache fields. The tested native CLI used one-hour writes; expiry can cause a fresh read without losing stored history.
7. **Keep usage explicit.** Preserve subscription sign-in, API-key/provider-fallback exclusion and paid-overage-off checks. Cached input still occupies context and consumes usage; output, reasoning and retries add work. Apply the result checks and validation below.

```text
One reader:   [ whole filing → all assigned facts ]
When needed:  [ fixed base: whole filing ]
                       ├─ copy A → part A's facts
                       └─ copy B → part B's facts
              Both copies can read every part.
```

### What the AI should see

| Show the AI | Keep in code |
| --- | --- |
| Original words/numbers in order, including titles, speakers, periods, scales, conditions and notes | Original content, file/version mapping and saved source locations |
| Short, unambiguous IDs; qualify by file where needed, e.g. `F1:u7` | Byte offsets, hashes, parser internals and storage paths |
| Complete tables: addressable cells, actual headers, merged spans, captions and note markers | Original cell records and coordinates |
| Actual source images with IDs in source order, or an extracted representation that preserves their needed content; explicit missing-content markers when unavailable | Image assets, their identity and source placement |
| Source-established relationships: caption ownership, table grouping, lists and paragraph continuation | Guessed `heading`/`text` kinds and guessed levels; hide these guesses, not the source words |
| Company, document identity, publication time and file boundaries once where needed | Repeated storage metadata |
| When XML/XBRL values are included: field/concept names and relevant entity, period, unit and dimension context | Raw bytes and storage details |

The exact display format is undecided; these are information requirements. Hiding metadata must not remove meaning or a known source gap. Publication time does not establish a fact's reporting period.

#### Example reading view

Fictional excerpt, not a finalized prompt format. The real input contains the full source plus shared instructions; an assignment follows that shared content.

```text
Company: ExampleCo
Document: 2025 annual report; published 2026-02-20
File F1: annual report

[F1:u1]
Demand increased in Europe during 2025.

[F1:u2]
Amounts in the following table are in USD millions.

[F1:t1]
     | c1               | c2   | c3   |
-----|------------------|------|------|
r1   | Measure          | 2025 | 2024 |
r2   | Revenue          | 100  | 90   |
r3   | Operating profit | 20   | 18   |

[F1:img1]
<actual source image supplied here>

Work assignment: all units in F1.
```

The image placeholder above stands for an actual image input. If unavailable, show `F1:img1 — image content unavailable` and retain unresolved coverage. Image delivery/cache behavior still needs validation.

A proposed 2025 revenue fact can cite `F1:t1/r2/c2` (`100`), `F1:t1/r2/c1` (`Revenue`), `F1:t1/r1/c2` (`2025`) and `F1:u2` (scale/currency). Code maps each reference to its original location and copies the fragments separately. A unit ID permits copying the whole unit; a shorter quotation needs an exact span or cell, not a code guess about which words matter.

### What remains undecided

- **Output contract — TBD:** the suggested first output is every eligible stated fact, its proposed Driver name and type together, evidence references, and source-stated subject, value/unit, period and conditions. Leave missing or ambiguous details explicit. Additional fields, catalog matching and XBRL links are undecided. This proposes updates; it does not approve a new Driver or match one automatically.
- **Model/settings:** no production winner is established. One-reader and medium-effort runs remain comparison baselines; do not routinely run both medium and high on each filing. Assignment size, parallelism for other source types and the exact table display remain open.
- **Other model roles:** Jev has no assigned stage; Qwen review remains postponed. Independent identity/duplicate checks required by rules 8.1–8.2 still apply. The proposing reader cannot approve its own identity.

### Evidence and result checks

These are **planned output checks**, not a completed checker or finalized schema. Reuse existing saved-input preservation checks; they do not certify model answers.

| Code check | Required behavior and limit |
| --- | --- |
| Effort diagnostics | Record configured effort and available runtime reasoning indicators. These do not prove correctness; absence of a visible thinking log alone is not a retry trigger. |
| References | Resolve IDs, cells and spans unambiguously against the saved file/version; reject missing references and out-of-bounds spans. A valid reference may still be irrelevant. |
| Exact evidence | Copy the referenced original text; compare any model-supplied quotation exactly. Keep separate fragments separate. Exact copying does not prove OCR fidelity or correct interpretation. |
| Missing work | Every source unit has an assignment and outcome: facts, no eligible fact, or unresolved. Flag missing responses and statement anchors outside the assignment. Supporting references may come from anywhere in the visible source. Unit coverage does not prove fact recall. |
| Repeated deliveries | Do not count the same job result twice after a retry; flag identical records for review. Several facts may cite one unit. Semantic duplicates need judgment. |
| Output/failures | Validate agreed fields/types; detect failed requests, output-limit stops and missing responses. Preserve valid work; use bounded retries only for failed, missing or unresolved work, then retain persistent failures explicitly. Reduce oversized assignments or use a suitable larger route. Never treat an incomplete answer as empty. |

**Safety-stop check:** inspect any reported safety-stop counter and unit coverage; a stop or missing required responses means incomplete even if status is `success`. Preserve available partial output; probe recovery later.

Unresolved cases need explanations; every empty unit does not. Source checks retain file identity, order and content. Model/reviewer checks must still establish:

- **Meaning:** subject, period, scale, conditions and the applicability of notes/definitions, including references on shared titles, headers and sections. Context may be distant or lack an explicit marker; one exhibit's scope does not automatically govern another.
- **Eligibility:** qualitative facts remain eligible under the Driver rules; no numbers is not a valid rejection by itself. Preserve existing admission requirements.
- **Ownership:** a spanning statement belongs where it begins, not to an earlier supporting heading/note. Choosing that anchor requires interpretation. Supporting copies create no new fact occurrences.

Report unresolved coverage separately and perform independent checks required by the rules. Neither exact quotes nor complete unit accounting proves complete fact recall, correct meaning or that every original published item was extracted.

### Next validation

1. Settle the output contract and freeze independent reference answers before candidate runs. Use fresh complete sources: an earnings filing, a longer real 10-K, a call and news. AMG is regression evidence, not an unseen holdout; retain disputed/unreadable cases.
2. Test the proposed setting on real structured input against the existing one-reader/medium baselines using the same source and requested output. Score complete facts: qualitative recall, names, qualifications, exact evidence, locations and duplicates. Check full dates/durations and point-in-time meaning, not just year strings; unresolved eligible facts count as misses.
3. Measure the complete workflow: loading, input/output, cache writes/reads, verification, retries, queues, completion time and sustained historical throughput. Use response-local usage so inherited base totals are not counted repeatedly. API price estimates are not subscription quota measurements.
4. Include distant qualifications, similar inapplicable notes, three-passage dependencies, continuous text, large tables and images, with positive controls. Preserve scope when moving text in test variants. Add a preparation stage or model role only for a demonstrated need; no finite test proves 100% accuracy on future sources.

## Reference only: evidence and history

Everything below supports review and traceability. It adds no build requirements; unapproved approaches remain unapproved.

**Owner-reported stop, not independently audited:** 212/679 pieces returned despite `success`; the same stop was 1/154 calls initially and 1/182 after later runs. Whether long answers increase risk remains unproven.

### Independent AMG check

Checked the linked [AMG extraction units](https://app.notion.com/p/416a0a3f3106818cb2e9c7a0341cfeb9) and the existing source-handling code on 12 November 2026, approximately 7:48 PM EST:

- Unit `u7` is labelled `heading (level 1)`, but its text introduces Jay C. Horgen as the speaker. Unit `u14`, “Capital Management,” is labelled `text`. Both examples are present as described. They show that the label is not a dependable semantic category; they do not prove that removing it improves model accuracy.
- The AUM scale is in `t23`, separately from tables `t24` and `t25`. Hiding kind/byte labels must not remove that title or its words.
- In `t54`, row 3 column 8 contains the dollar sign; column 9 contains `79.5`. The reader must be able to return the number's cell address, such as `F1:t54/r3/c9`. Above it are the original period heading and scale. The earlier partial-view experiment's wrong-column results are a reason to preserve clear cell references.
- The page shows image filenames/placeholders. That does not prove those images were supplied to a vision-capable reader. The prior cache tests did not test actual image understanding.
- The page's XML values include repeated dates, identifiers and booleans. Removing their field names/context would remove meaning, not just storage detail.
- Existing [readback](../../../../driver/prepare/reconstruct.py) already separates retained records from composed order and relationships. Its preservation check is about saved input; it does not certify that a new compact prompt is faithful or that the model interprets it correctly. The [HTML conversion code](../../../../driver/prepare/convert/edgartools_html.py) records parser heading evidence separately from source text and distinguishes source table-header markup from a header guess.

**Image correction:** “image” does not mean “the AI cannot read it.” It means there is image content to supply or explicitly account for as unavailable. [Claude's image documentation](https://platform.claude.com/docs/en/build-with-claude/vision) describes actual image inputs; it does not validate this plan's exact CLI image-caching setup. [TypeSafe's input guidance](https://docs.typesafe.ai/concepts/state) likewise distinguishes judgment content from the questions asked about it; it is not proof that any particular minimal payload is sufficient.

The source details and code were checked; equal or better extraction accuracy with slimmer labels remains unmeasured.

### Complete independent cache experiment record

Run 12 November 2026, 6:12–6:15 PM EST (America/Toronto); account snapshots span 6:10–6:15 PM EST. Raw UTC instants remain in the evidence. This was a cache/source-access experiment with short quotations.

#### Fixed setup

- Native Claude Code **2.1.323**, resolved model **claude-fable-5-2**, **low** effort, standard speed; no model fallback.
- Existing Claude Max 20x plan sign-in. Pre-run authentication reported `claude.ai` and `firstParty`; no API key was used. Live account snapshots showed extra usage disabled. Every response reported `isUsingOverage: false` and `overageDisabledReason: org_level_disabled`.
- Source: the existing AMG 8-K saved-unit display, accession 0001004434-23-000015, containing 68 press-release units and 50 XBRL field units. The source supplied was **34,460 characters**. It retained unit IDs and source locations. Images were placeholders; image understanding was not tested. This is not evidence that every file of the original filing was extracted.
- One base request supplied the source and returned only issuer name and filing date. Its input contained 16,798 tokens, including the source and request overhead.
- Twenty-five consecutive work assignments covered all 118 unit IDs once. Each request returned one short quotation from the first assigned non-image unit. This is deliberately much smaller output than full fact extraction.
- Each child used the native `--resume BASE_ID --fork-session` mechanism. No custom history-copying implementation was built. Every child started from the same base; no child output was fed to another.
- Native `--safe-mode`, no tools or MCP servers, fixed system prompt and working directory. Maximum four concurrent calls; one turn per request; no automatic retry. The first cached child was checked before running the remaining 24.
- The control used the same base, assignments, model and settings with `DISABLE_PROMPT_CACHING=1` in its child environment only. No global cache setting was changed.
- The first source read and 25 cached requests were followed by 25 uncached requests: **51 successful model requests total**.

The installed CLI's native help and current official documentation were inspected before running it. Native session copying and cache controls satisfied the task; only a temporary invocation/measurement script was needed.

#### Measured results

| Measure | 25 cached children | 25 cache-disabled children |
| --- | ---: | ---: |
| Successful requests | 25 | 25 |
| Total input tokens | 424,708 | 424,708 |
| Cache-read input tokens | 412,175 | 0 |
| Cache-write input tokens | 12,433 | 0 |
| Other input tokens | 100 | 424,708 |
| Input served from cache | 97.05% | 0% |
| Output tokens | 899 | 896 |
| Median wall time per request | 3.315 seconds | 3.336 seconds |
| Mean wall time per request | 3.318 seconds | 3.333 seconds |
| Correct requested unit ID | 25/25 | 25/25 |
| Exact quotation present in that unit | 25/25 | 25/25 |
| Requested maximum of 12 words respected | 24/25 | 24/25 |

Each cached child reported exactly **16,487 cache-read tokens**, rather than just a small common instruction prefix. Inspection of all 51 native transcripts confirmed that each contained the exact same complete source message once. No source truncation or source duplication was found in those histories. This is direct evidence of substantial source-prefix reuse; it does not assign individual cache tokens to particular words.

The initial base request took 3.458 seconds and wrote 16,796 tokens to cache. It is additional setup work and is excluded from the table's child-request totals. Counting it once, the cached setup plus children had 441,506 input tokens: 412,175 reused, 29,229 written to cache, and 102 other input tokens. Cache-write tokens have their own accounting; a lower count of newly processed tokens is not itself a subscription-discount formula.

The first cached child took 3.123 seconds as an isolated check; the remaining 24 finished in a 20.308-second batch. The uncached 25-request batch took 22.943 seconds. These batch shapes differ, so use the per-request times for the limited timing comparison. At this source size and short output, no meaningful speed improvement was demonstrated. Longer documents, different output volumes and queue conditions were not tested.

Both conditions' twelfth assignment returned the same exact 13-word quotation despite a 12-word instruction. That is a response-limit failure and remains recorded. The test proves source access and cache operation on these requests, not general instruction compliance or final fact accuracy.

#### Subscription meter observations

The existing `scripts/claude_usage_fetch.py` read the account's usage endpoint. These are fresh responses, not stale local cache results.

| Snapshot | Eastern time | Five-hour usage | Weekly usage | Paid overage |
| --- | --- | ---: | ---: | --- |
| Before setup and cached reads | 6:10 PM EST | 25% | 30% | Off |
| After setup and cached reads | 6:14 PM EST | 29% | 30% | Off |
| After uncached control | 6:15 PM EST | 39% | 31% | Off |

The observed movement was **+4 percentage points** for the first interval and **+10** for the second. The first includes setup and time spent preparing/inspecting the test. These meters are rounded and account-wide; other account use and reporting delay were not isolated. One other local Claude process existed outside the test. Therefore, do not claim a precise 60% saving, a per-token plan weight, or a stable weekly throughput figure from these deltas. They support investigating the observed reduction alongside the definitive cache-token records.

Response-local usage is used for token totals. Native child `modelUsage`, dollar estimates and API-duration fields inherited base-session totals; summing those would count the base repeatedly. API list-price estimates are not subscription charges.

#### Cache-lifetime correction

The base and all cached children wrote `ephemeral_1h_input_tokens`; none wrote five-minute cache tokens. Thus **these CLI `--resume --fork-session` copies used one-hour writes**. Do not assume that every operation called a “fork” is an in-process fork or subagent with the same default lifetime. Inspect the actual response fields. The 51-request test did not wait for expiry and does not experimentally establish expiration or renewal timing.

#### Scope and evidence

This experiment did not test full Driver facts, qualifications/naming, actual images, higher effort, expiry, retries, sustained throughput, compact packages or genuinely large sources. The CLI reported a 1,000,000-token context window and a 128,000-token output ceiling; only about 17,000 input tokens and short answers were exercised. The follow-up below covers some additional mechanics, not those general accuracy claims.

- [Manifest](research_notes/context_cache_probe_2026-11-12/manifest.json): frozen source hash, assignment IDs, settings and expected source units.
- [Results](research_notes/context_cache_probe_2026-11-12/results.json): all computed totals and fresh account snapshots.
- [Transcript checks](research_notes/context_cache_probe_2026-11-12/source_history_checks.json): exact source-message checks for all 51 native histories and their hashes.
- [Raw evidence archive](research_notes/context_cache_probe_2026-11-12/raw_evidence.tar.gz): original `run_probe.py`, source, prompts, response streams, summaries, source-copy checks and account snapshots; no credential files. The script is an experiment harness, not production code.
- [Checksums](research_notes/context_cache_probe_2026-11-12/SHA256SUMS.json): hashes of the preserved measurement files and archive.
- [Claude plan help](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan): the October 7 update states that plan sign-in keeps SDK/print runs on subscription limits; API-key usage uses the linked API arrangement.
- [Claude Code caching](https://code.claude.com/docs/en/prompt-caching): native prefix reuse and cache-disable controls.
- [Claude Code cost guidance](https://code.claude.com/docs/en/costs): session dollar estimates differ from subscription usage.

### Complete follow-up experiment review

Reviewed 12 November 2026, 7:05 PM EST (America/Toronto), with the later X/X2 evidence considered afterward. Existing results were read and preserved; no new model calls were made.

#### Evidence inspected and preserved

The supplied `mech_run1` contains 86 native CLI invocations: 84 resolved to Sonnet 5.5 and two to Opus 5.5. All 86 raw result streams agree with their summaries: successful CLI outcome, no API-key source, and response rate-limit records reporting no paid overage use. Some invocations include multiple turns or helper requests, so 86 is not the total count of underlying inference requests.

The frozen snapshot contains the two scripts and 493 files beneath `mech_run1`, preserved in [raw_evidence.tar.gz](research_notes/context_reader_followup_2026-11-12/raw_evidence.tar.gz), with hashes in [SHA256SUMS.json](research_notes/context_reader_followup_2026-11-12/SHA256SUMS.json). Eight additional X/X2 cross-model calls appeared while the temporary source was being reviewed. They are preserved separately from the original 86-call comparison and assessed below following the owner's additional message. The [audited results](research_notes/context_reader_followup_2026-11-12/audited_results.json) retain all 94 call measurements, all supplied extraction scores, and usage-only records from the four existing project helpers. Private project prompt histories from those four helpers were not copied into this archive; their source paths and hashes are recorded.

#### Mechanics and cache reuse

The native Sonnet cache-only exercises, including the larger repeated inputs, used Sonnet 5.5 at low effort. They establish client behaviour, not low-effort extraction quality; the other helper and mixed-model configurations are distinguished below.

| Setup | Observed result | Scope of conclusion |
| --- | --- | --- |
| Base session plus native copies | Approximately 97% input reuse; all 12 simultaneous copies succeeded | Supports the selected approach and this concurrency level on these requests; not a universal optimal concurrency |
| Source in a fixed system prompt | Five later independent runs reused 16,209 tokens each, about 96% of their input | A genuine alternative; the report does not establish a large cost gap between this and base copies |
| Source at the start of changing fresh user messages | Four changing tasks reported zero cache reads | Failed to reuse in this exact message arrangement; not universally impossible |
| Exact same fresh user message repeated | The second identical control reused 16,892 tokens | Direct counterexample to a blanket claim that separate fresh user messages cannot reuse source |
| In-process forks from a lead | Actual child messages reused 20,434 tokens with 572 written plus four other input tokens | Reuse works; the lead adds its own orchestration and response work |
| Ordinary clean helpers reading a file | Their source-reading turns wrote 17,660 fresh cache tokens each; some earlier instruction input was reused | They did not share the source read in this setup; zero source reuse is different from zero reuse of any input |
| Project-loaded helpers and named readers | Around 75,762 and 81,803–81,856 newly cached tokens across their two turns | Confirms substantial baggage in the tested project configuration; this is not an inherent minimum for all helpers or teams |
| Scripted named-reader attempt | The observed result was a subagent, not a teammate | Establishes what that invocation produced, not universal inability to create teams through any script or version |
| Five-minute base after an approximately 13-minute gap | The later child read zero tokens from cache and wrote 17,012 | Session history survived while cache reuse did not; expiry is a cost/performance event, not loss of the stored source |

Inherited message histories must not be counted as fresh child requests. The saved in-process helper histories include the parent's earlier response. The actual child usage is identified in the lead stream by `parent_tool_use_id`.

The larger tests repeated the same AMG material: 206,890 characters in six repeats and 1,000,025 in 29 repeats. The children reused 97,088 and 467,848 tokens respectively. This demonstrates capacity and cache operation on repeated content. It cannot show reliable extraction from a genuinely complex large filing, and identical repeated passages cannot prove that a quoted answer came from the requested copy.

#### Same-model requirement: X/X2 controls

The two additional groups each used a Fable 5.2 base and three Sonnet 5.5 copies, but their controls matter:

- X used a seed prompt whose bytes and SHA-256 exactly match the earlier A/A2 Sonnet seed. Its three Sonnet children each read 16,474 tokens from cache. This is consistent with hitting the already-warmed Sonnet prefix; it does not establish reuse of the Fable model's cache.
- X2 added a fresh run tag before the source. All three Sonnet children reported zero cache-read tokens and wrote 17,071–17,075 input tokens to cache, while still completing the source-reading task. This is the relevant cold-target-model control.

The controls distinguish a cache already warmed under the target model from transfer between models. Both mixed-model groups retained source access.

#### Extraction: scopes and reasoning effort

The ad hoc extraction task used 68 press-release units, six manually chosen ranges and its own instructions, not the complete Driver rules. The main whole-view six-job run, partial-view six-job comparison and single-call comparison all used **Sonnet 5.5 at medium effort**. All three answered 68/68 units. The whole-view jobs returned 297/297 selected pure-number cells in **33.4 seconds**, versus 293/297 with partial views and 297/297 in **115.2 seconds** for one call. Fewer calls therefore did not mean faster completion in this test.

The four partial-view misses are specific: in table `t54`, the numbers were returned with the dollar-marker column IDs instead of the adjacent numeric column IDs. This is a source-location error, not four omitted numerical values. Their raw results remain preserved.

Note-reference checks improved, but the later scopes were smaller:

- Original whole-view run: 4/14 selected note links across the complete 68-unit task.
- Clearer note rule at medium effort: 6/14 across two selected work ranges, covering 18 units.
- Sonnet 5.5 at **high** effort and Opus 5.5 at **medium** effort: each returned the eight expected highlights links in one selected 12-unit work range. Opus's archived command confirms medium. These were not complete-filing runs. No xhigh extraction run was tested here.
- The fallback's first stage selected 21 of 68 units as governing context. Its second stage scored 14/14 links across two selected work ranges, not a complete 68-unit fallback extraction. Its score field `calls: 2` excludes the six context-collection calls. Its reported wall time includes collection.

Full visibility made the notes available; the weaker settings still failed to cite many. Availability and correct use remain separate.

#### Corrections to the automatic scores

1. **“Zero period errors” means zero failures of a year-only check.** The grader searches for the expected year string; it does not establish the right quarter, exact date, duration or point-in-time meaning.
2. **“297/297” covers a selected numeric-cell domain.** The grader excludes prose-containing cells, column-zero cells and year-shaped text. It does not count all eligible facts or all numbers appearing in prose. Five `bad_pointer` entries in the whole-view/single-call runs refer to real `t4` cells containing prose and numbers that the numeric-only grader excludes; they are not nonexistent cell addresses.
3. **The original quotation check normalizes characters.** It removes backslashes, dollar signs and spaces, so its “exact” label is too strong. Independent [direct substring checks](research_notes/context_reader_followup_2026-11-12/strict_quote_checks.json) in this review found all 43 returned prose quotes across all eight saved arms exactly in their source units; that still establishes no prose recall denominator.
4. **“None” does not establish no eligible fact.** `W_job1` marks `u9` as none because it is “Qualitative outlook with no figures.” The single-call result says “No figures.” The Driver rules permit qualitative conditions and proposals from qualitative/action causes. Absence of a number is not a sufficient rejection rule; eligibility must be assessed under the actual rules.
5. **Citing a note is not proof of applying it correctly.** The note key is a small, hand-written set of expected IDs. It does not grade every qualification, complete meaning, Driver identity or final naming.
6. **Useful developmental evidence is not independent certification.** AMG has already been studied repeatedly. The code says these keys preceded these runs; that does not make the source an unseen holdout or establish independence from earlier AMG exploration.

The qualitative rule is in [DRIVER_RULES_Categorized.md](DRIVER_RULES_Categorized.md), including the metric definition and the rule permitting qualitative/action proposals subject to their existing admission requirements. This review does not relax those requirements.

#### Preserved files

The archive contains the original `probe.py` and `extract.py`. See the [manifest](research_notes/context_reader_followup_2026-11-12/manifest.json), [archived-file hashes](research_notes/context_reader_followup_2026-11-12/source_file_hashes.json) and linked results/checks above.

### Reported Autodesk 10-K reader comparison

**Owner-supplied side-run report; raw responses, scorer and timing were not independently audited in this review.** Source: Autodesk's real 10-K, approximately 417,000 characters. Every reader saw the whole report and used Sonnet 5.5 at medium effort. The task was to return numbers in the discussion section, not complete Driver updates. Each arm reported outcomes for 230/230 units.

| Readers | Reported run time | Numbers found, approximate denominator | Reader-stage price-list equivalent | Including reported $0.55 loading cost |
| --- | ---: | ---: | ---: | ---: |
| 1 | 76 seconds | 532/533 | $0.19 | $0.74 |
| 4 | 37 seconds | 521/533 | $0.24 | $0.79 |
| 12 | 19 seconds | 520/533 | $0.37 | $0.92 |

In this test, 12 readers were four times faster, found slightly fewer numbers and cost about twice as much **for the reading stage alone**. Including the same reported loading cost, the total was about 24% higher. These are price-list equivalents, not measured subscription quota charges. A standalone one-call route need not incur a separate loading call, so this comparison does not establish its total cost.

Limits: one run per setting; roughly 11 additional omissions in the multi-reader runs were reported in flattened table lines mixed with explanatory text. The database text did not preserve the actual extraction's table rows/columns, so this does not isolate the cause of the misses or predict results with the intended input. The denominator excluded 16 non-quantity numbers such as the `7` in `Item 7` and is approximate. Meaning, period, scale, Driver names/types and qualitative facts were not scored. This supports testing more readers for speed, not assuming better completeness; it does not prove that one reader is universally more accurate.

### Reported Installed Building Products 10-K follow-up

**Owner-supplied results; raw records and grading were not independently audited here.** Every Sonnet 5.5 reader saw the full report. The task covered 1,366 table numbers in the discussion and financial statements, not complete Driver updates. Counts below include the reported code repairs to column references; preserve raw and corrected scores separately when auditing.

| Readers / effort | Reported time | Table numbers returned | Reported issue |
| --- | ---: | ---: | --- |
| 1 / medium | 5 minutes | 267/1,366 | Safety stop |
| 1 / medium, repeat | 6.4 minutes | 1,366/1,366 | None in this check |
| 4 / medium | 2 minutes | 1,366/1,366 | None in this check |
| 4 / medium, repeat | 1.2 minutes | 1,311/1,366 | One empty table |
| 12 / medium | 30 seconds | 1,087/1,366 | Six empty tables |
| 12 / medium, repeat | 32 seconds | 1,240/1,366 | Four empty/skipped tables |
| 12 / high | 63 seconds | 1,366/1,366 | None in this check |

Reported follow-up: one focused retry per short table brought all four incomplete runs to 1,366/1,366; each retry took 21–37 seconds. Code repaired 33–245 wrong column references per run. Against company data tags, 1,209 checked numbers had no wrong values/scales but up to seven doubtful periods. Prose-number recall used a rough key: 88–92% with recorded thinking, 48–68% without. Empty-table calls were 4/30 without recorded thinking and 0/16 with it; all 12 high-effort calls recorded thinking. This association does not prove causation or guarantee that high effort will prevent omissions; absence of a visible thinking record does not establish absence of internal reasoning.

One chart in the base was reportedly visible and reused in three copies: about 276 read versus about 277 shown. This is limited evidence for approximate chart reading and image reuse, not exact visual extraction. Reported list-price equivalents were $0.79 to load, then $0.59–$0.88 per medium run or $1.30 for the 12-reader high run; these are not subscription charges. This earlier group covered one report/model, two runs per medium setting and one 12-reader high run. Retain raw records before temporary storage disappears; no location was supplied or new archive made in this review.

**Later owner-reported comparison:** about four high-effort readers, all with recorded thinking, returned 1,366/1,366 table numbers and 143/150 sentence numbers with no bad quotes. The many-reader comparison without recorded thinking returned 68/150 sentence numbers, empty tables and altered quotes. Seven of 150 sentence numbers were still missed (about 4.7%). The claimed comparable cost/best result has no separate timing or usage breakdown supplied here and is not independently verified. Trust remains one report/model and one or two runs per setting; recorded thinking is associated with these results, not a correctness guarantee. This supports the next trial and source-based spot-check proposal, not complete Driver validation.

**Spot-check proposal:** sample original passages per report with their context and independently identify eligible facts before comparing outputs. Checking returned answers alone cannot reveal omissions. Small samples give a noisy signal, not a per-report recall guarantee; audit cost and method remain to be settled.

**Proposals, not adopted implementation:** bound assigned work by expected answer size/completion time while retaining full-source visibility; no numeric limit is established. For a task requiring every table number, compare expected source-cell IDs with returned coverage, not just totals, and retry only missing work. Driver eligibility must be settled before every numeric cell can be treated as a required output. Repair a column reference only when the original row/value and other evidence identify exactly one cell; ambiguous cases need review. Matched totals and repaired references alone do not prove correct meaning or complete fact recall.

### If the whole source cannot be shown usefully

**Unapproved fallback idea:** broad consecutive views with neighbouring material; collect original passages that may govern other views, then reconsider every range, including ranges that initially produced no facts. Recheck combined context and applicability rather than blindly following package links. Overlap covers local continuity but does not guarantee distant context; a confidently missed passage or three-way dependency may remain invisible. This could cost more than whole-source reading. It needs design and validation only if the chosen whole-source route proves impractical.

### Suggested later model roles

Possible Jev work included source-grounded fixed-choice fields or checks such as whether a proposed type fits, or whether one fact explicitly caused/offset another. These require original evidence and can themselves be wrong; they cannot recover facts the first reader never proposed by themselves. Do not automatically make two models fill every field. Additional fields in the original read may save later calls but add reasoning/output and can require smaller assignments. A cache does not provide completed answers for free.

### Retired Jev packaging proposal

The 12 November 2026, 4:51 PM EST proposal used semantic boundary judgments near an 8,000-character target, then selected support units by comparing all package pairs. For N packages this is N(N−1)/2 pairs, not factorial. It was never validated as a complete workflow and is not part of the build.

Reasons it was not adopted:

- Pairwise comparisons do not establish complete context. A says “The portfolio returned 8%”; B says “Returns for Series X are before fees”; C defines “the portfolio” as Series X. A–B may miss the link without C, and A–C need not select B.
- Package links do not prove which support applies to which fact. Following all links can import unrelated notes or most of the document; attaching uncertainty cannot catch confident wrong exclusions.
- Work boundaries need not make passages self-sufficient when every reader sees the whole source. No generic structural rule was found for every semantic dependency: actual HTML caption ownership is usable; nearby text has no equivalent guarantee. Distant dependencies were not measured as less than 1%.

[TypeSafe batching](https://docs.typesafe.ai/cookbooks/parallel_questions) supports shared-state judgments and [Noul](https://docs.typesafe.ai/primitives/noul) provides yes/no probabilities, but neither validates this task or its thresholds. The [Qdrant](https://qdrant.tech/blog/jevjitsu/#semantic-chunking) and [Supermemory](https://supermemory.ai/blog/jev-memory-context-engineering/) articles concern retrieval, not complete context for every financial fact; the latter also describes meaning lost through sentence filtering.

The earlier [Astra](https://app.notion.com/p/416a0a3f310681b4a4bce916a873fb30), [Opus](https://app.notion.com/p/416a0a3f3106814fb4c2c5cf54c6c639) and [Fable](https://app.notion.com/p/416a0a3f310681d4b04df245e59a3210) AMG exercises used older Qwen runtimes and keys shaped after earlier outputs. They show selected successes, misses and broad direct support selection, not measured dependency closure, current Qwen performance or Jev's error rate. [AMG units](https://app.notion.com/p/416a0a3f3106818cb2e9c7a0341cfeb9) and the [rebuilt view](https://app.notion.com/p/416a0a3f3106813bae2ad0b1470b3cfb) remain examples; the 68-unit press release is one file, not the whole filing.

A compact-package comparison, including an oracle package built from known true evidence, was another suggested experiment. It omits real selection errors/cost and is not required before building the chosen workflow. Equal accuracy at lower total cost or time could still justify preparation; selector and reader accuracy percentages cannot generally be multiplied because their errors interact.

### Superseded settings and archived detail

The earlier 12-package 10-K default was replaced by one reader first and medium → high testing; the later IBP report prompted the current four-reader/high next trial. These are evolving trial choices, not demonstrated universal defaults. Six simultaneous copies was only a suggestion; xhigh is not in the current trial. More fields, Jev/Qwen roles and the [rough design](rough_design.md) were never adopted as a complete division of work.

Detailed retired boundary-search rounds, unused probability examples, old support questions and speculative cost tables were removed from this working document. They remain in the [previous committed revision](https://github.com/faisalanjum/EventTrader/blob/c580b68ec8d5a116db041d5c171f49380663fb3c/.claude/plans/Drivers/DriversFinal/ClaudeCachedReads.md#retired-jev-packaging-proposal).

### Related records and retention

- [DriverEngineScratchpad.md](DriverEngineScratchpad.md): separate history of input-code decisions, pending work, reader drafts and Jev experiments; retained, not another cached-reading plan.
- [rough_design.md](rough_design.md): older whole-pipeline proposal; retained unchanged. Neither overrides the current Driver rules.
- The two earlier ContextPackaging plan files were removed after consolidation. Evidence-folder READMEs are indexes to this file, not competing plans. Earlier wording remains in Git history.
- Keep the five Driver input tests: they check real acceptance/refusal and protect accepted inputs from mutation or consumption. Exploratory model runs are not a production test suite.
- The two evidence archives total about **1.06 MB** and preserve originals, measurements and failed controls. Three byte-identical loose experiment scripts were removed after comparison; their originals remain inside. Manifests, readable results and checksums remain beside the archives.
