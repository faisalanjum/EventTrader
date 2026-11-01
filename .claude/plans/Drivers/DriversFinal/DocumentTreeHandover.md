# Document tree — independent lead handover

Updated 10 October 2026. **New owner decision: investigate the document tree in a separate parallel workstream, with `document-tree1` and `document-tree2`. Extraction has its own lead and closeout. This handover does not reopen hierarchy work for the extraction lead or make extraction wait for the tree.**

## Mission and boundaries

Your main job is **strategy, orchestration and independent review**. You own priorities, design decisions, experiment gates and acceptance; the two Claude specialists supply bounded implementation and evidence. **Your first task is a deep independent diagnosis, not implementing this handover's recommendations.** Treat every result and explanation here as a claim to verify against the actual source, code and saved output. Confirm or refute the material findings, uncover additional issues if present, and understand causes before choosing fixes. Use earlier artifacts to avoid redundant experiments, not as unquestionable authority. Do not outsource direction to the agents.

The owner will feed filing content to future AI systems that identify financial drivers. They want to select a heading, its subheadings and their exact content automatically across past and future filings. One consumer may need a whole subsection; another a table or short passage with the necessary headings, units, period, notes and original citation. A wrong parent or content boundary can give that AI unrelated context or omit a qualifier even when every word survived extraction. Reliable structure should enable flexible future selection without a new parser for each downstream task; the tree itself must not infer financial drivers or impose a new topic taxonomy.

Preserve the existing extraction: text, numbers, tables, pictures, XML, order and original-source references. The tree is additional source-bound structure, not rewritten text. Downstream driver logic, a general chunking/packing framework, production deployment and final AI consumption are outside this workstream.

Target close to 99% **measured precision and recall and correct complete-section selection**, with no known material corruption accepted. A few good examples, valid JSON, native parent pointers, a high conditional score or all text retained at the root do not establish this. Keep source ambiguity and unsupported cases counted. Do not promise universal perfection from finite tests or silently narrow the goal to an easy subset.

Requirements in `PrepareTools.md` and repository `AGENTS.md` apply throughout:

- Fully automatic at scale; no per-filing manual setup or human production review.
- Minimal, generic, well-organized code. No issuer, title, filename, expected string, sample index, layout template or answer-key exceptions in runtime. Normal source indexing and standard parsing rules are not prohibited.
- Inspect the pinned library's actual native features, source and settings before custom work. Test the native path; record the demonstrated gap. No new CSS engine, semantic rule engine, general grader, transport framework or duplicate parser.
- Code preserves, binds and validates; it must not invent meaning. Preserve required context, table/picture membership, units/periods/notes and occurrence identity. Existing paragraph/group labels and taxonomy edges are evidence, not automatically semantic parents.
- Reuse tests, source binders and scorers. Reproduce a defect before changing behavior; test the class plus real valid controls. Preserve old results and all failed attempts. Do not regenerate expectations to favor a candidate.
- Work in a separate worktree or a uniquely named `prepare_work` folder. Do not edit main or extraction code/contracts without coordination with its lead. Main contains unrelated unsaved work. No commits, pushes, deployment, graph writes or paid infrastructure are authorized merely by this handover.
- **No interference with extraction:** read pinned copies of its outputs. Do not alter its runtime, tests, fixtures, answer keys, source store, shared dependencies/environments or workers; do not stop its jobs or compete with its integration slot. Any proved missing extraction evidence becomes a narrow written request to its lead, with a source example and impact. That lead owns whether/when to change extraction. Tree progress is never a prerequisite imposed on its closeout.
- Keep the extraction Test Agent's sealed sources/answers private. No access to `/home/faisal/prepare_work/validation_next_20261007/private/` or its restored copies. No extraction exam from this stream. Tree development references listed below are exposed research data, **not** the sealed extraction keys.

**AI-policy chronology matters.** An early owner restriction rejected routine per-document AI. The owner later explicitly authorized automatic, economical Haiku/Jev research, selected Haiku 5.5 for these trials, and authorized further bounded research calls without repeated permission. Do not repeat the obsolete blanket prohibition from older notes. This does not establish an affordable production method: long-report input grew substantially. A stronger model is allowed for a one-time research diagnostic/review, **never as a routine production mapper or fallback for this task**. Existing Opus helper sessions are reviewers, not a license to charge Opus for every filing. Check prior receipts before spending the later same-input stronger-model diagnostic; it was left pending during the SEC-API review. Preserve default picture OCR policy—Sonnet off—and do not restart OCR/model-selection experiments here.

## Read first, then only the evidence needed

1. This file, `PrepareTools.md`, and `/home/faisal/EventMarketDB/AGENTS.md`.
2. `/home/faisal/prepare_work/section_mapping_20261010/LIMITATIONS_CURRENT.md`.
3. The parent-accounting and repeatability reports linked in the results table below.
4. `/home/faisal/prepare_work/secapi_deep_review_20261010/REPORT.md`, especially the native-structure reuse proposal; its older combined roadmap is superseded by today's separate streams.
5. Inspect the exact native-tool or scorer files for the first chosen task. `PARENT_ONLY_PLAN.md` is chronological; its many old “next steps” are not simultaneous work orders.

Do not read the entire old conversation, every trial directory or private validation material. [Extraction handover](PrepareExtractionHandover.md) defines the other lead's responsibility; [extraction snapshot](ExtractionSnapshot.md) supplies its evidence without requiring its whole history.

## Three different capabilities

| Capability | What must actually be proved |
|---|---|
| Heading discovery | All required heading **occurrences**, including run-ins, with no ordinary labels promoted to headings. A contents-page title is not its body occurrence. |
| Immediate parents | Each detected heading belongs to the correct parent occurrence, not merely a plausible topic category. Parent linking cannot recover a heading that was never supplied. |
| Content ownership | A selection includes the right original text, tables, pictures and notes, including descendant headings, without unrelated material or silent omissions. Correct parents alone do not prove this. |

The last active diagnostic isolated **parent linking over fixed candidates**. Start by understanding that result and its instability, rather than claiming that heading discovery or section endings were solved. Fixed diagnostic candidates and per-case research configurations do not themselves prove a complete automatic input pipeline. Never supply reference headings/parents to the production path or patch a candidate from its answer key. Maintain separate denominators for these capabilities. Source binding and valid-tree checks are mechanical; semantic correctness comes from independently reviewed original-backed references, not the predictor judging itself.

## What was measured

The principal prior work is under `/home/faisal/prepare_work/section_mapping_20261009/` and `section_mapping_20261010/`. These are research artifacts; none is an adopted production tree.

| Evidence | Result and interpretation |
|---|---|
| Native comparison | 63 required headings plus 1 ambiguous across six regions of Yelp 10-K, Lincoln 10-Q and AMD 8-K. On AMD, native Docling PDF, Marker and Granite found 7/7 headings but 0/3 tested child-parent links; EdgarTools 2/7 and SEC-parser 6/7 headings, also 0/3 as exposed heading edges. SEC-parser did preserve one relationship as supplementary content. These are small diagnostic counts, not corpus scores. |
| Early complete-document inference | Three exposed 8-Ks: 16/16 headings, parents and sections. Broadridge 48-page 10-Q with Haiku: 92/97 headings, 81/97 parents, 89/97 boundaries. A separate Opus trial reached 91/97 boundaries; **that 94% was not the common Haiku method**. |
| Best original common parent pass | Across ten development documents: **836 canonical + 17 pre-frozen alternatives + 7 unsupported + 2 absent = 862 required occurrences; 853/862 (98.96%) source-supported**. Supplementary occurrence accounting explains title-address gaps; it is not a new algorithm or complete-section score. |
| Unchanged strict score | 755 canonical + 9 allowed alternatives + 7 unsupported + 91 address-unavailable = 862. Most address gaps have independently traced occurrences; title-extent and conflation faults still matter. Do not substitute a favorable denominator. |
| Exact-repeat reliability | Annual report **346–362/368** supported; first quarterly **126/128**; second quarterly **177–180/180**. Only **649/682 fixed candidate choices** stayed identical across three runs per source. Four wrong choices persisted. The first-pass 98.96% is not reproducibly established. |
| Broader inventory | 175 exposed documents/142 issuers inventoried; a 39-document panel with 10 reserves and 4 separate calibration cases was approved. Categories include K/Q/8-K and amendments, 425, 6-K, SC 14D9, SC TO-I and varied exhibits. **This is not 39 completed accuracy evaluations.** The ten-document parent result contains one K, three Qs, an earnings exhibit, a 425, a 6-K, two 8-Ks and an 8-K/A. The 6-K issuer breadth is limited. |

Primary result records:

- [All 862 occurrences](../../../../../prepare_work/section_mapping_20261010/inventory/parent_full_occurrence_accounting_v1/REPORT.md), sibling `ACCOUNTING.json`: this handover recomputed all 862 row categories, matching the published counts.
- [Repeat stability](../../../../../prepare_work/section_mapping_20261010/inventory/parent_repeat_stability_evaluation_v1/REPORT.md).
- [Native review](../../../../../prepare_work/section_mapping_20261009/ROOT_NATIVE_REVIEW.md): read its later-policy warning; old restrictions inside are historical.
- [Approved panel](../../../../../prepare_work/section_mapping_20261010/ROOT_PANEL_APPROVAL.json), linked `inventory/PROPOSED_PANEL.json`: the proposal still says pending, but the separate approval is authoritative.

**Scale/cost correction:** the ten original parent invocations used 12 exported native requests, **723,359 input tokens including cache and 95,527 output tokens**; summed invocation durations were 353 seconds. This excludes discovery, rendering and other experiments. The recorded CLI `$6.626` has `costBasis: unknown`, not an invoice. The earlier `$71 Jev / $120 Haiku for 60k reports` illustration used tiny **incomplete** inputs and is not a budget for the current method. See [cost snapshot](../../../../../prepare_work/section_mapping_20261010/inventory/common_parent_cost_snapshot_v1/REPORT.md). Count complete automatic preparation, requests, syntax recovery, retries/failures and repeated work before judging affordability. These rich long-report inputs are not “a couple of heading lines.”

## Native tools: useful parts, actual gaps

These are versions and findings recorded in the October 9–10 studies, not a claim that the latest release will always behave identically. Production extraction still uses its separately pinned environment. Do not upgrade it as a research side effect.

| Existing mechanism | Reuse and measured limitation |
|---|---|
| Docling 2.137.0 / Core 2.101.1 | HTML, rendered PDF layout, `HeadingHierarchyModel`, numbering/style/bookmark paths, hierarchical chunks, serializers and Granite VLM were investigated. Native item references/traversal assemble supplied structure; hierarchy mainly relevels existing headings. It did not supply the required SEC parents or all run-ins. Native chunk paths agreed with the level stack; this was not merely a forgotten hierarchy setting. Picture serializer options are useful but not heading discovery. |
| EdgarTools 5.61.1 research; 5.60.0 production capture | Native nodes, child/paragraph identity, SEC/TOC sections and chunkers are useful. SEC Items do not give every inner heading. Production capture retained all 63 required candidate starts in the exposed regions, **among 1,013 candidates**; this proves availability, not heading precision. Native source/node ordering and section offsets require the existing original binder. |
| SEC-parser 0.58.1 | Real native tree builder; classification mostly depends on highlighted elements and style order. It cannot turn an omitted title into a correct heading by traversal alone. |
| Marker 2.0.0 / PageIndex Flash 0.2.22 | Tested paths did not solve the exposed parent relations. Do not equate PageIndex Flash without LLM with its untested Classic mode. |
| PageIndex Classic | Source-inspected, not accuracy-tested here. Uses full page text, multiple model checks and page-level boundaries; may merge away child hierarchies. It does not natively return exact original HTML heading spans or table/picture ownership. An internal pre-merge entry is not a ready exact-content solution. No trial justified solely by its marketing. |
| MinerU 4.0.11 title leveling | Accepts supplied title blocks and uses title-only model inference; fixed heading depths 1–5 do not faithfully represent all current candidates. No adapter or trial adopted. See the final fixed-heading feasibility decision, not only the earlier discovery objection. |
| SEC-API and existing Neo4j/Arelle | Standard K/Q/8-K Item text and financial statements already exist. Original XBRL TextBlock HTML and presentation networks are a **concrete remaining native-reuse hypothesis** for K/Q note structure. They do not prove arbitrary prose hierarchy, exhibits or images. Old graph TextBlocks were flattened; prefer original native structure. No new vendor accuracy comparison was run: the then-available API key was exhausted. |

Detailed sources: `section_mapping_20261009/native_options/native_reset_review_v1/REPORT.md`, `docling_native/production_native_evaluation_v1/REPORT.md`, `fable_native_edgar/CANDIDATE_v1.md`; `section_mapping_20261010/inventory/mineru_fixed_parent_feasibility_v1/ROOT_DECISION.md`; `secapi_deep_review_20261010/REPORT.md`.

Jev was genuinely tested, including complete choice population/batching and compact text transport. On the richer V4 regional trial, Haiku had 50 correct / 7 wrong / 6 unproved required parents; Jev 21 / 23 / 19. The cheap initial title-only successes did not generalize. Model/API limits and prices in those files are historical; reverify official documentation if proposing a new integration. Read the project's TypeSafe skill before changing a TypeSafe/Jev integration. Do not restart a broad model bake-off.

## Reuse this code and evidence

Use `/home/faisal/prepare_work/venvs/prepare-tests/bin/python` for the existing offline research dependencies. Trial freezes and actual imports remain authoritative; the app venv is not interchangeable. Repository main was `cf01ed22b29087b1653e42e7d9cf152ad83d9e66` at this review, with no working-tree changes under Prepare runtime/tests/grader; unrelated files are dirty. Recheck before work.

| Location | Purpose |
|---|---|
| `EventMarketDB/driver/prepare/convert/` and `pictures/` | Extraction owned by the other lead. Consume saved, versioned outputs; preserve them. |
| `section_mapping_20261009/docling_native/source_bound_outline_v1/binder.py` | Existing exact literal title-part binding to original holders, source order and valid open-parent ancestry. Keep raw content unchanged. |
| `section_mapping_20261009/compact_ai_review/source_bound_outline_v1/score_sources.py` and `compact_ai_review/production_native_v1/score_v3.py` | Existing source/member/parent/boundary evaluation. Mechanical code scores independently authored original-backed references. |
| `section_mapping_20261010/source_order_candidate_v1/` | Reviewed source-order candidate work; role, extent and discovery limitations remain. |
| `section_mapping_20261010/parent_only_v1/score_parent_only.py` and `global_review_v1/score_global.py` | Preserve fixed candidates; reuse binder/evaluator and public receipt checks. |
| `parent_presented_outline_v1/`, `parent_presented_p00_v1/`, `parent_broad_presented_v1/`, `parent_breadth_p31_p33_v1/` under October 10 | Exact donor prompts/schema/views/answers for the common ten-document baseline. `inventory/common_parent_cost_snapshot_v1/ROWS.json` identifies every donor and receipt. Do not combine winners from later variants. |
| `section_mapping_20261009/complete_input_diagnostic_v1/call.py` | Existing subscription caller. Historical main settings: `claude-haiku-5-5`, high, 300 seconds, structured output, no external retries. Match the actual trial's approved entry/contract before reuse. |
| `section_mapping_20261010/inventory/native_invocation_contract_v1/CONTRACT.md` | Bounded native JSON syntax recovery, with all attempts counted. Not permission for arbitrary repair, retry or input compaction. |
| `section_mapping_20261010/references_a/`, `references_b/READINESS.md`; October 9 `reference/`, development-reference folders | Exposed source-first annotation, cross-review, freeze and scorer recipes. Test fixtures can name real documents; runtime may not learn their exceptions. |

Do not run old exclusive builders in place: many intentionally refuse existing outputs. Read the final `FROZEN.json`, approval and actual result, not only a preparation-era `REPORT.md`. Reuse one tested scorer core; the numerous historical experiment wrappers are evidence, not a production architecture to copy.

**Transport nuance:** a client's compaction *check that declined before changing input* was initially mislabeled and corrected. Actual source compaction occurred in later nested/half-output trials and invalidated those results. Two baseline cases used bounded native JSON syntax recovery; preserve their original first-request failures and count both actual requests. Public events do not prove the exact bytes of every second wire request. Do not read private reasoning, count only the last call, or silently trust a truncated source. Changes to the Claude client require rechecking the relevant existing contract, not installing another general guard framework.

## What failed — do not repeat without a new mechanism

- Native upgrade/settings alone, title-only inference and generic typography levels did not solve complete relationships.
- Adding geometry, changing formatting presentation, co-locating candidates, response vectors/nesting, higher effort, extra review, split outputs and smaller local context each had measured regressions, invalid/unavailable outputs or no net benefit. A 128/128 single-quarter max-effort result failed to generalize.
- An extra source-table-neighbor trial fixed five genuine parents but introduced three unsupported links; rejected. Its mechanics are reusable evidence, not an adopted inference policy.
- Comparing two model proposals fixed no required parent in its pilot and introduced two caption faults. Majority votes and best-repeat selection were not accepted.
- Native screenshot input was considered, but needed 188/198 report tiles, exceeded client media limits and lacked complete source registration. This is not a proven cheap visual shortcut.
- Existing authored DOM containment did not distinguish the remaining wrong immediate parents. Native taxonomy grouping is a different structure; do not relabel either as complete semantic truth.

Reasons and exact trials: `PARENT_ONLY_PLAN.md`, `LIMITATIONS_CURRENT.md` and their linked root decisions. Stop a failed pilot before broadening. A new experiment must identify a distinct evidence/mechanism gap, not just another prompt wording.

## First work order and reassessment gates

1. **Independently diagnose before building.** Confirm both specialist sessions and the extraction boundary, then trace actual originals → saved extraction/native structure → research inputs → predicted parents → binding/scoring → selected content. Inspect varied exposed cases and valid controls, not only the seven reported failures. Audit title-to-source occurrence, heading-to-parent, direct/descendant content and table/picture/context links; distinguish what is present natively from what our adapters discard, change or infer. Recompute important counts and reproduce the smallest relevant failures offline. Challenge reference ambiguity and scorer limitations as well as predictions. Classify each claim as verified, refuted, uncertain or untested, with its actual cause and reader impact. Produce one concise cause/impact ledger and prioritize it yourself. Give progress checkpoints without substituting a time limit for sufficient understanding; do not rerun every historical experiment or change runtime merely to investigate.
2. **Choose one discriminating native-reuse proof after that diagnosis.** A suggested hypothesis—not a prescribed answer—is the unperformed original XBRL/Arelle note-structure binding check described in the SEC-API review: inspect existing source-native identities on exposed K/Q reports and test what parent evidence they actually provide using the current binder/scorer. Do not build a mapper or assume these networks solve the seven known parents. If the required sources/structure are absent, reject this direction promptly with evidence; do not build a financial parser. Select a different, better-supported mechanism if your independent findings justify it.
3. **Freeze one useful hypothesis and its assessment before implementation/calls.** State the exact gap, native functionality checked, smallest change, varied source controls, reference versions, costs, success/failure conditions and stop point. One specialist prepares; the other challenges source truth and regressions. Root accepts or rejects. Stronger-model diagnostics may distinguish input insufficiency from model limits, but cannot become the production escape hatch.
4. **Pilot → independent review → repeat → breadth.** Count gains, regressions, absent/unavailable cases, ambiguous optional captions and request cost. No per-document winner. Reassess immediately after a contradiction, regression, excessive complexity or cost. Expand only for a useful common-method gain. Repeat identical hard inputs before claiming reliability, then use independently reviewed new exposed sources spanning the existing panel. Do not call nine reruns nine documents.
5. **Advance capabilities separately.** Keep parent diagnosis focused first; do not redefine it as the whole product. Discovery and complete-content ownership must subsequently pass their own checks, including unheaded returns and image-internal headings. If there is a fundamental tradeoff or irreducibly ambiguous source, present one concrete decision rather than an endless experiment chain. No deadline or “100%” instruction justifies invented certainty.

The target final output is an additional, versioned map tied to exact source/extraction identity: literal heading occurrences, parent relationships, proved content ownership and explicit gaps. Reuse existing schema where it expresses those facts; extend only for a demonstrated missing fact. No body-text rewriting, downstream chunker or new storage system. Document/version-local unit IDs must not be treated as stable across extraction revisions.

## Communication and division of labor

The two requested Claude names are **`document-tree1` and `document-tree2`**, without spaces. They are separate from Fable (`driver-helper`) and OCR (`driver-prepare`). Do not send new tree work to the extraction specialists by default.

**Verified contact:** both wrote ACK files at 14:29:53/56 UTC on October 10 under `prepare_work/claude_relay_20261007/document-tree-20261010T142921Z-6990b98d/replies/`. The relay receives native delivery receipts; replies are shared files, not necessarily visible chat messages. Both subsequently reported being **new, available Opus 5.5 sessions with no tree work performed**. Their inherited Fable/OCR notes are second-hand and contain obsolete scope/AI restrictions. `document-tree1` was briefly unreachable at the 14:33 request, then reached successfully and explicitly confirmed availability at 14:40:37 UTC. **Refresh availability; an old ACK is not proof the session is still live.** Do not invent current status or take over a conversation.

Current status files/receipts: `/home/faisal/prepare_work/claude_relay_20261007/tree-handover-20261010T143324Z-04c7747d/` (`document-tree2`) and `/home/faisal/prepare_work/claude_relay_20261007/tree-handover-review-20261010T144023Z-81c041e8/` (`document-tree1`, plus tree2's handover review). These are the direct agent-status sources for this handover; old memories are not new measurements.

**Existing small assignment:** at 14:40 UTC, tree2 was asked to review this handover read-only for contradictions and missing prerequisites, with no experiments or code edits. Its expected reply is `replies/document-tree2.md` in the latter directory; it was still pending at the final handover check. Read it if it has arrived, independently judge its findings, and otherwise check that task before assigning overlapping work. Tree1 has no assigned research task. Neither session has implemented a new hierarchy method.

Use the existing relay mechanism:

1. Read `/home/faisal/prepare_work/claude_relay_20261007/README.md` and the request directory's `command.json` / `prompt.txt` for exact working invocation. Installed binary is `/home/faisal/.local/bin/claude`.
2. Launch a **fresh** small relay session with the same restricted native tool configuration (`ToolSearch,SendMessage`, safe mode, empty MCP configuration, `dontAsk`, stream JSON). Send only the intended messages; no resume/takeover of another session. A native name lookup failure may suggest currently reachable names. `ListAgents` was unavailable in our relay; do not assume it exists. Never reuse an old socket path.
3. Give each work order a unique request ID and unique reply path under `claude_relay_20261007/inbox/` or its own request folder. Ask for current task, exact patch/commit or artifact hashes, source evidence, limitations and next bounded check. This durable file is the return channel; a one-shot relay may have exited before a native reply arrives.
4. Inspect actual delivery receipts and reply files separately. “Delivered to inbox” is not “read” or “completed.” If a session remains unreachable, continue useful independent work and report the narrow need for the owner to reopen/name it; do not silently create a replacement.
5. While actively coordinating, use bounded waits and check progress about every five minutes; give useful user updates. File replies do not awaken an idle Codex session. No promise of unattended background work after your own turn ends without a live mechanism.

Suggested roles once availability is confirmed: tree1 prepares native evidence/minimal candidates; tree2 independently checks source truth, scoring and regressions. They may communicate directly, but report decisions to the lead. For new references, keep both reference authors blind to candidate predictions until source review/freeze. Do not assign self-review or duplicate experiments. Each receives this common handover plus one bounded task and acceptance rule; no need to copy the whole old conversation.

For extraction dependencies, use a public written contract request to its new lead, discovered through Codex thread metadata/owner-provided name. State the exact missing evidence and why existing output cannot supply it. Do not browse other conversations or sealed material to guess. Fable/OCR, Test Agent and Mac communication details live in `PrepareExtractionHandover.md`; they remain under the extraction lead. Tree work must not change its exam schedule, settings, test keys or runtime without explicit coordination.

## Limitations to explain together at closeout

| Open issue | Plain consequence |
|---|---|
| Missing/false/incomplete headings | Some real subsections are unreachable by their heading; a graphic label may become a false section. Repeated or conflated title occurrences cannot be rescued merely by matching words. |
| Wrong or unstable parents | A subsection may appear under the wrong Item/note; exact reruns currently disagree. Original styling can be identical for a parent and child. |
| Unheaded returns | A final subsection may be followed by broader-topic paragraphs/tables without a new heading. “End at next peer” wrongly includes them. Five documented witness groups contain 26 original items/seven tables; optional exact-source closure addresses are a proposal, not a completed automatic detector. See `references_a/unheaded_scope_design_v1/DESIGN_REVIEW.md`. |
| Image-only headings | One exposed image-based 425 has 12 required headings inside two images. Its small text layer is incomplete; saved image references alone do not make those headings selectable. |
| Table/object ownership | Layout tables, partial table scope, repeated picture occurrences and inline title/body fragments can require finer ownership than the current contract expresses. No silent object dropping or flattening. |
| Ambiguous originals | Some parents are not uniquely determined by the source. Preserve pre-frozen alternatives/uncertainty; do not manufacture a single “correct” map. |
| Input/scale/cost | Complete context may exceed request/media limits; recovery can change answers. Small or title-only trials do not price the full workflow. Unsupported categories, failures and unknowns remain in coverage. |

The owner asked for these together at the end, with fixed/open/untested status and examples. Keep `LIMITATIONS_CURRENT.md` current or link an explicitly superseding ledger. Completion needs a measured end-to-end development assessment, stable repeated results, independent held-out tree evaluation when separately arranged, source-preservation regressions, cost/resource evidence and a clear owner adoption decision. The extraction exam is not automatically a complete tree exam.

## Exact startup prompt

> Read `/home/faisal/EventMarketDB/.claude/plans/Drivers/DriversFinal/DocumentTreeHandover.md`, the latest scope in `PrepareTools.md`, and repository `AGENTS.md`.
>
> You are the separate document-tree lead. Your job is strategy, orchestration and independent review, using the existing Claude sessions `document-tree1` and `document-tree2` through the documented relay/reply-file channel. Verify their availability and give them bounded work; you own direction and acceptance.
>
> Develop a fully automatic, source-bound heading → subheading → content map so future AI consumers can select passages, subsections or tables with the right context and provenance. Keep code minimal, generic and organized; inspect native functionality first. Work in isolation from extraction. Do not alter its code, contracts, tests, fixtures, shared environments or workers, delay its closeout, inspect sealed validation answers, or build driver/chunking systems. Route any demonstrated extraction dependency to its lead.
>
> First perform a deep independent diagnosis: trace original sources through the actual code and saved outputs to heading discovery, source binding, parents and content/table/picture membership. Do not take this handover or any agent's claims for granted. Reproduce material failures, check valid controls, identify their causes and downstream effects, and report what you confirm, refute or newly discover. The 853/862 first-pass result is not repeatably achieved; do not call it finished or pool winning variants. Treat the native XBRL/Arelle suggestion as a hypothesis, not your assigned solution. Only then choose the smallest justified next step. Freeze bounded hypotheses, independently review evidence and reassess after every milestone; retain missing/ambiguous/failed cases and full costs.
>
> Follow the recorded model and permission limits. No stronger-model production fallback, per-document exceptions or invented semantic rules. First report the verified starting state, agent availability and your first bounded step; ask only essential unresolved questions, otherwise proceed autonomously. Target close to 99% measured quality and coverage without promising universal perfection.
