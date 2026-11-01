# Independent Prepare validation — session work order

You are the independent answer-key custodian for EventMarketDB's document-preparation stage. You are not a converter builder. Prepare a fresh, source-backed validation package for HTML/XML and image OCR, independently review it, and leave it sealed for the final exam. Do not run the candidate pipelines until the release gate below exists.

## 1. First response, then autonomous work

First read the short scope/access references below and inspect inventory metadata only. Do not yet open selected document contents, label answers or run converters. In one concise response:

- Confirm the two lanes, your separation from their builders, the proposed sample sizes and what those samples can establish.
- Bundle any essential questions about source access, independent-reviewer access, workload or conflicting contracts. Recommend a default for each. Do not ask the owner to make routine technical choices.
- If nothing needs clarification, say "No blocking questions; ready to prepare the sealed keys."

Wait for the owner's reply once. After that, complete key preparation, review and packaging without intermediate approval requests; interrupt only for a genuine blocker. Save progress so a restart needs no conversational memory. Missing candidate readiness does not block finishing the keys: return `KEY_READY / EXAM_NOT_RUN` when they are complete.

## 2. What we are preparing, and why

The final consumer is an AI creating company drivers from SEC evidence. It needs understandable passages and facts with their headings, units, periods, qualifiers, footnotes, relationships and exact source locations. Layout may change; meaning and provenance must survive. This assignment tests preparation, not the later AI's financial reasoning or chunking.

- **HTML/XML:** EdgarTools with approved source-formatting/browser-geometry integration; a standard XML parser. Docling is retained for comparison, not an instruction to test every route again.
- **OCR default:** Chandra reads each informative picture; PP-OCR through RapidOCR and OnnxTR supply evidence and flags. **Sonnet is optional and OFF.** No second-reader answers, including cached ones, may influence the default result. Driver-stage fact verification is separate and is not yet evidence of extraction correctness.
- Dedicated PDF processing is paused. Images embedded in HTML remain in scope; record PDF and other unsupported inputs separately.

Apply four priorities throughout: fully automatic production; minimal generic library-based code; faithful meaning with harmless presentation differences distinguished; minimal unnecessary processing. No filing/company/string/coordinate exceptions, new grading framework, AI judge or human production queue. Source-specific answers belong in the key, never in production logic. Original-backed review during this one-time evaluation is required.

## 3. Necessary paths and access

Repository: `/home/faisal/EventMarketDB`. Read its `AGENTS.md` and `.claude/plans/Drivers/DriversFinal/PrepareTools.md` for current scope; do not follow unrelated historical work orders.

- **Reserved HTML/XML challenge set:** `/home/faisal/prepare_work/heldout_exam/NEXT_EXAM_RESERVATION.md`; selection `/home/faisal/prepare_work/step3_sample_20261002/selection_heldout2.json`, SHA-256 `a3e694c656a5c92d6ab66977e9525af0cb5516e73574cd6b936f476327f90560`. Preserve these 30 documents / 28 issuers. They are mostly difficulty-selected, not a representative random sample.
- **Approved contract reference:** `/home/faisal/prepare_work/step3_sample_20261002/bulk_20261002/FINAL_KEY_FOR_CODEX_20261006_1753/`: read `CONVERTER_COMPARISON.md`, the equivalence rules in `CLAUDE_KEY_README.md` and `CONTRACT_DECISIONS_R*.json`. Package 4 is reviewed; the repository pointer may still name package 3. Pin the contract actually used; never silently switch the live pointer or edit a frozen package.
- **Existing formats/checks:** `/home/faisal/EventMarketDB/benchmarks/prepare/golden/` and `benchmarks/prepare/grader/`. Read only schema, contract and verifier code as needed. Reuse them; they do not supply ground truth.
- **Source/inventory starting points:** `/home/faisal/prepare_work/step3_sample_20261002/` (`population.json`, `files.jsonl`, `report_metadata.json`, `export_sources.py`) and `/home/faisal/prepare_work/pdf_twin_census_20261004/ocr_bench/real575_20261005/` (`manifest.json`, `census_all.json`, selection manifests and `validation_20261006/VALIDATION_DRAW.json`). Inspect metadata, not saved OCR answers. These indexes may cover subsets: establish the full current saved-manifest population first.
- Originals are in the existing version/blob store on `minisforum2`, accessed read-only through the approved downloader in `driver/prepare/get/`. Reuse existing access/export mechanisms after inspecting them: older scripts have stale imports and `/tmp` destinations. No SEC requests, production-database writes or shared worker changes. Raise unavailable read-only source access in the first response.

Work in `/home/faisal/prepare_work/validation_next_20261007/`, separating `public/` handoff/counts from `private/` selections, originals, keys and review evidence. Never use `/tmp` for required records. Keep keys out of git and builder handoffs. This is procedural separation on a shared account, not a security guarantee; publish only an exclusion manifest of identifiers/hashes needed to prevent accidental use by builders.

## 4. Freeze a defensible sample before inspecting outputs

Keep the 30 reserved documents as a separate challenge cohort. Add probability samples from the current eligible corpus: **default 300 HTML/XML documents and 300 picture occurrences**, disjoint from the challenge cohort. In the first response, justify these sizes or propose a bounded alternative based on population, labeling effort and achievable statistical precision; fix the decision before drawing/opening sources. Do not expand or shrink the sample after seeing candidate scores.

- Include main reports and attachments, XML disclosure/supporting roles, ordinary and difficult pictures, and logos. Use a small number of source-defined strata where needed, with known selection probabilities. Compare the sample and population distributions for form, year, document role, format, size and images per filing. Rare-class oversampling is allowed with correct weights and separate reporting. Do not cross every attribute into hundreds of strata.
- Build exclusions from all prior development, control, released exams, OCR pilots and known failures. The 50 hard pages, 336 pictures and earlier 120-picture validation are **already used**. Exclude previously inspected source/image hashes and filings; keep issuer separation for the reserved challenge cohort and disclose issuer overlap in random cohorts. Identify unknown exposure; never call it proven unseen.
- Use full saved manifests, not only convenient local exports or the old screened/120-filing sample. Freeze eligibility, exclusions, random seed, selection algorithm, replacement policy and population counts. Calculate weights **after** exclusions. A fixed hash order must use a seed chosen without inspecting outcomes.
- Count image occurrences separately from unique image bytes; repeated bytes may reuse a reading but must retain each document's context. Record duplicate/issuer/filing clusters when estimating uncertainty. Inventory inline, external and unresolved image references as coverage gaps if the frame cannot include them.
- Failed/unavailable/unsupported selected inputs remain accounted for; no silent replacement by easier ones. Report how much of the total corpus the eligible frame excludes. Historical sampling supports estimates for that frame, not a guarantee about all future filings.

Three hundred units is a workload default, not a magic confidence threshold. About 300 independent, fully assessed units with zero errors would support only an approximately 1% upper error bound at 95% confidence; partial-document assessment, weighting and clustering change that inference. Never count thousands of correlated cells as thousands of independent documents.

## 5. Build answers from originals only

Freeze the target-selection rule and assessment coverage before reading candidate outputs. For HTML/XML, use source-only deterministic sampling of complete regions: a whole table with its context and a prose region for HTML where present; complete selected XML subtrees with ancestor/namespace/attribute context for XML. Record selection probabilities and why a region is absent. Add an independent whole-document block/table/image inventory to detect entirely missing sections. Do not claim every word of a document was checked when only selected regions were transcribed.

For each sampled picture, inspect the **whole original**, including its edges, captions, logos and small print; transcribe readable content and record table/chart relationships. Do not sample only blocks the tools found. Keep genuinely illegible content explicit without guessing, and account for it in the denominator.

Each answer needs the original SHA-256, document/image occurrence identity, reproducible source location, literal evidence and required context:

- Tables: every assessed value linked to its row and parent row group, all governing column headers/spans, units, periods, signs, qualifiers and notes.
- Prose/headings: complete scoped passage, meaningful order, references, cancellations/strikes and qualifications.
- XML: expanded names, attributes, hierarchy, repeated-element identity and the correct reporting entity; visible disclosure and supporting metadata accounted for separately.
- Pictures/charts: printed text versus visual description; labels, axes, legend/series and their value links. Bar length is not a printed exact value. Record source-readable qualitative relationships without inventing precision.
- Delivery: image bytes, containing document, occurrence, neighboring context and relevant cell/heading association. A matching filename or a path alone does not prove delivery.

Use original rendering/DOM or an independent standard XML reader to establish evidence. Do not use candidate conversion, Chandra, Sonnet, free-OCR output or the grader's scanner as the source of expected answers. Helpers may locate/copy original text, but rendered scope and image answers require original inspection. Reuse the existing key schema and decision/build/verify tools in a new package. Inventory unsupported assertions explicitly; they are scoring gaps to resolve under §6a, not silently omitted checks or completed automatic coverage. Do not build another general grading engine.

Preserve the approved comparison contract. Report literal differences and material differences separately; never silently correct printed typos. A presentation waiver requires preserved meaning and associations, not simply matching word counts. Picture `APPROXIMATE`, tool agreement, an error flag and a delivered original are different from correct extracted facts. No universal case/tense folding or waiver for logos, phone numbers or footnotes.

## 6. Independent review and sealing

Use a fresh independent reviewer with access only to originals and the same rubric; preferably a different model family. Isolated reviewer subagents are authorized for this job; no extra paid APIs/model deployments. If a separate reviewer cannot be provided, raise that in the first response. Self-review is not independent review.

Have the reviewer establish answers independently before reconciliation. Review every keyed region, including cases where the two readings agree; settle differences from source evidence, not majority vote. Record remaining source/contract ambiguities explicitly before scoring. Do not omit difficult cases or invent exclusions to achieve a perfect key.

Validate record completeness, source hashes/locations and schema compatibility. Check that the existing scorer distinguishes valid representations from planted value, sign, omission and row/column errors using synthetic or already released controls—not the new candidate outputs. If a checker gap remains, record it; do not rewrite production or secretly change the contract.

Freeze sources, sample/weights, key, rubric and reviewer decisions under a complete SHA-256 manifest. Preserve versions; later corrections need a reason and a new version with before/after reporting. Arrange a second durable copy and verify restoration/hashes; a link is not a backup. If backup access is unavailable, disclose that as a packaging limit.

## 6a. One automatic scoring command, independent of extractor changes — owner, Oct 7

**One-time evaluation-method exception — owner, Oct 10:** the owner approved existing automatic checks plus a complete, answer-private supplemental review by the independent Test Agent for every remaining required duty. This replaces only the fully automatic assessment prerequisite for this one frozen evaluation; use `HYBRID_METHOD_READY`, never mislabel the incomplete automatic scorer `SCORER_READY`. Expectations, calibration, coverage accounting, weights/uncertainty, private separation and all §7 release gates remain. Unassessed duties still block completion. Production stays fully automatic; fresh AI review judgments may vary and must be reported separately. This decision alone releases no early exam or model calls. [Exact owner decision and preparation boundaries](../../../../../prepare_work/extraction_closeout_20261010/OWNER_ASSESSMENT_METHOD_DECISION_20261010.md). The original automatic-method requirements below remain preserved.

Deliver one documented offline command that takes the sealed key, a frozen candidate-output manifest and a new result directory, and scores HTML, XML and pictures together with separate lane/cohort results. Reuse the existing reviewed graders/comparison functions and a minimal wrapper; no model calls, new AI judge, document exceptions or manual marking during the scoring run. This is scoring saved outputs, not permission to generate new candidate outputs on the sealed set.

- **Prove coverage:** map every required keyed assertion to an automatic check, including text/facts, omissions and additions, row/column/parent headings, chart relationships, source identity and image/context delivery. Preserve unavailable, ambiguous and unassessed cases with explicit denominators/statuses. A word score does not cover a relationship check. An unsupported required assertion blocks `SCORER_READY`; list the gap and the smallest generic reuse/fix needed. Clarify genuine contract gaps with Codex using public synthetic examples only, never selected answers or failure clues.
- **Separate identities:** pin sources/key/rubric/scorer/environment independently of the candidate code/settings/models and output manifest. Pin the scorer's transitive comparison/parser dependencies too; it must not silently import the live checkout's changing shared functions. Use a frozen evaluation copy, not a second implementation of production rules. Check pins and input completeness before scoring; missing/corrupt/stale inputs or unsupported schemas must not yield a successful complete assessment. Preserve explicit invalid/incomplete-run status separately from a completed assessment containing wrong answers.
- **Verify before the exam:** use synthetic or already released controls only. Demonstrate valid alternatives pass, material wrong values/signs/units/periods/negation/entity names and row/column/legend swaps fail, missing and extra content are counted, and source/context mismatches are detected. Include two different candidate code identities producing equivalent outputs: they must receive identical substantive scores under the same key/scorer. A changed output containing a planted regression must fail its check. These controls need no new model calls or sealed-set extraction.
- **Keep optimization independent:** extraction refactors may change code paths and performance without changing expected answers or scoring rules. Keep the agreed output contract stable; if an interface must change, version it and review only the smallest generic adapter, proving it preserves every assessed field on exposed controls. Never update expectations from candidate output or loosen rules to make an optimization pass. Key/rubric/scorer changes require a separately reviewed, versioned correction, with the old version preserved.
- **Reproducible receipt:** record all identities, expected/received/assessed/missing/unscored counts and per-assertion results; report accuracy and coverage separately. Two runs on identical saved inputs must give identical substantive results, written into separate directories without overwriting evidence.

`KEY_READY`, `SCORER_READY` and `EXAM_NOT_RUN` are distinct states. Key preparation may finish while a scoring gap is being closed; complete the script and coverage proof as part of this assignment, and do not claim automatic validation is ready merely because the keys are sealed. The final exam still waits for §7's gate, after the owner's optimization/output-review pass. Later reruns can be regressions; they are not a new untouched exam.

## 7. Exam release and reporting

**No candidate-pipeline or OCR-engine calls during key preparation; original inspection and the authorized reviewer sessions are allowed.** Fable owns HTML/XML, the OCR bot owns pictures, and the coordinating Codex session owns their readiness gate. Do not send them answers, source crops, failure clues or suggested fixes from this set while they tune their code.

**Owner sequence, Oct 7:** key preparation and sealing may continue now. The builders first address known accuracy/completeness issues on exposed evidence; the owner then guides output review, code organization and optimization. Only after that pass and its regression replay is the candidate frozen for this exam. Do not treat an integration approval, merged commit or `KEY_READY` as permission to run it.

Run the final exam only after receiving a written gate naming immutable code/settings/model identities, the approved runtime environment, completed regressions and combined image/context/restart checks, and the sealed key hash. Model/compute execution authorization must be explicit; key preparation alone does not authorize GPU rental or model requests. Sonnet remains off. Missing gate: finish and hand off the key, do not run or wait indefinitely.

The exam uses the complete frozen extraction path from original bytes through delivered reader input. Freeze all outputs before scoring; no tuning, route selection from the answers, selective retries or test replacement. Predeclared operational retries must be logged and costed. Afterwards report separately:

- HTML, XML and OCR; random and challenge cohorts; assessed versus unassessed content.
- Correct/incorrect/missing/spurious facts and relationships, unresolved/illegible cases, full-table success, provenance and image/context delivery. Report precision/recall only where expected and emitted inventories support both denominators; word accuracy is not table accuracy.
- Corpus-weighted estimates with design-appropriate uncertainty, raw counts and cluster counts. No whole-corpus/future-production claim from challenge scores or selected regions.
- End-to-end cold/warm latency, memory, storage, failures, calls/tokens and actual compute conditions; missing measurements stay missing.

Target zero observed material errors and unexplained omissions on the assessed tests. Preserve explicit uncertainty: a flag does not repair an error, and supplying the original does not certify extracted text. Do not declare later driver-stage verification complete. If an exam fails, preserve it unchanged; only release its details for development after an explicit decision, and use new untouched evidence for a later generalization claim.

## 8. Deliverables; nothing else

- `public/KEY_READY.md`: counts, scope, limitations, reviewed/sealed status, opaque hashes, exact evaluation prerequisites/commands; no answers or selected content. State `KEY_READY` and `SCORER_READY` separately, including any open coverage gaps.
- One offline scoring command and its pinned dependencies, with a public coverage/control-test summary under §6a; no duplicate grading framework. Source-specific keys and per-assertion details remain private.
- `private/`: frozen selection/weights/exclusions, originals and assets, keys with source evidence, independent review/reconciliation, manifests and restoration proof.
- `RESUME.md`: brief progress, decisions, remaining work and reproducible commands.
- After an authorized exam only: immutable outputs plus a concise result report, preserving every failure and denominator.

Do not edit, merge, commit, push or deploy either implementation. Finish the independent validation work, not another converter or research project. Return the completed key handoff, or the final exam report if a release gate was supplied.
