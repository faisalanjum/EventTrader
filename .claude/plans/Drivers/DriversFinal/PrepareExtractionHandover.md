# Prepare extraction — new-session handover

**Owner-authorized scope, 10 October 2026: finish extraction, validate it, then close this phase. Park document-tree research, selection/packing wrappers and driver creation. Continue the existing implementation and evidence; do not restart the project.**

**Later owner clarification, Oct 10:** document-tree research now has a separate parallel lead with `document-tree1` and `document-tree2`; see [its handover](DocumentTreeHandover.md). “Park” in this extraction handover means outside **your extraction scope**, not a prohibition on that other lead. Preserve its read-only access to versioned outputs, coordinate narrow evidence requests, and do not delay extraction completion or expose sealed tests for its experiments. You retain ownership of extraction changes, integration and its final exam.

The owner processes thousands of SEC filings for future AI driver creation. The immediate product is faithful, reusable, source-linked content: text, numbers, tables, XML and picture readings, with originals and explicit uncertainty. Future consumers may need sentences, paragraphs, rows or larger selections; that packaging is deliberately deferred. Preserve the evidence needed to build it later without requiring a new extraction design now.

**Lead's primary job — owner clarification:** strategize, orchestrate and independently review. Own priorities, design choices and acceptance decisions; delegate bounded implementation and evidence collection to the existing specialists. Reassess after each milestone, prevent duplicate work and unnecessary complexity, and keep the whole extraction contract in view. Do not outsource strategy or accept an agent's success claim without checking its evidence.

**Target and acceptance standard:** aim for 100% extraction fidelity within the agreed scope, with fully generic, minimal and well-organized production code. Account for every required source element; our code must not silently lose, corrupt or invent content or relationships. Preserve the owner's separate acceptance of Chandra-origin reading errors, with those errors and unproved relationships visible. Measure correctness and coverage separately; passing samples cannot establish universal 100% accuracy. Minimalism must preserve correctness; generic means no document-specific exceptions, and organized means clear module ownership, shared rules implemented once and tests/evaluation kept outside runtime. Any unresolved material gap prevents declaring that part complete. Follow the bounded closeout sequence below rather than pursuing theoretical perfection indefinitely.

## Start here, in this order

1. Read this handover and [ExtractionSnapshot.md](ExtractionSnapshot.md). It answers what was measured, which samples were used and what remains unknown.
2. Read the top scope update and requirements in [PrepareTools.md](PrepareTools.md), plus `/home/faisal/EventMarketDB/AGENTS.md`. PrepareTools contains chronology: **the extraction-first decision here supersedes older hierarchy-first work orders**, not the standing correctness/minimalism requirements. Old instructions saying tests await migration or shared comparison is unmerged are obsolete.
3. Verify current git state and the latest gate linked below. Do not assume a later session has left main unchanged. Read only the relevant public evidence for the next bounded task.
4. Reconnect the existing agents using the methods below; get each agent's current task, exact code revision, evidence path and blocker before assigning work. Do not restart their completed tasks. Test Agent must remain independent and answer-private.
5. Give the owner a brief confirmed state and the first bounded action. Continue useful authorized work without repeated permission questions; ask only for a real unresolved scope/cost choice. No whole-transcript read is necessary.

**Owner's final clarification:** this is one lead orchestrator plus four existing specialists (Fable, OCR, Test Agent and local agent), not a request for 45 new agents. Start with a fresh independent review of extraction code, tests and saved evidence. Do not presume old green counts prove correctness, but do not redo completed migrations or reopen hierarchy research. The end of this work includes the final independent test using Test Agent's sealed sample after its prerequisites pass.

## Non-negotiable requirements

- **Fully automatic at corpus scale and for future documents. No human production review.** Human/AI source review while developing or validating is not the production workflow.
- **Minimal, generic, organized code.** No issuer, filename, title, expected string, sample index, hand-picked layout or document-specific branch in runtime. Ordinary input indexing and standards/library-defined parsing rules are legitimate; the ban is on fitting fixes to samples. Fix a demonstrated class at its owning boundary.
- **Native functionality first, every time.** Inspect the pinned package's actual APIs/settings/source (EdgarTools, Docling, Chandra, browser, XML parser) before implementing behavior. Test the relevant native path. Record the demonstrated gap and why the smallest custom glue is needed. No new HTML/CSS engine, scorer framework, cache framework or semantic correction layer.
- **Meaning and preservation before cosmetic exactness.** Values, signs, units, dates, entities, negation, qualifiers, labels, table/footnote/chart relationships and source evidence matter. Harmless layout/case differences should not cause extra machinery or model calls. Never assume a tense, case or mark is harmless without context, or silently rewrite printed text.
- **Keep originals and all raw reader results.** Preserve exact source identity, occurrence identity, reading order, cells/spans and existing context/style evidence. Unknown placement is not a guessed relationship. Failed, missing and partial content must remain visible, never count as a complete result.
- **Default OCR:** Chandra + PP-OCR/RapidOCR + OnnxTR; Sonnet optional, off. Off means no calls or cached-Sonnet influence. Do not reopen a reader-combination/model search. Chandra-origin reading mistakes are accepted as an external limitation for code closeout, still measured/reported. Do not claim our pipeline repairs them. Driver-stage verification is future work.
- **Orchestrator owns strategy and acceptance.** Fable/OCR may coordinate directly and challenge each other; require a durable report back. Do not accept counts on trust: reproduce important claims, inspect the exact patch and source evidence, test valid controls as well as failures, and reassess the smallest next step after each milestone.
- **Preserve tests and history.** A new defect gets a failing regression before the minimal fix. Review deliberate expectation changes, keep old baselines and frozen outputs, rerun relevant and full checks. No silent baseline regeneration. Tests reduce regression risk; they do not promise zero future defects.
- Keep experiments, audits, answer keys and large fixtures outside runtime. Runtime must not import `benchmarks` or `prepare_work`. Permanent tests belong in `tests/driver/prepare/`; retain existing scoring evidence until an archive and restoration are verified.
- Work in isolated checkouts; **one integrator on main** coordinated with Fable and OCR. Preserve unrelated edits. Stage named files only. Do not deploy, modify Neo4j, unseal answers, run the final exam, start paid infrastructure, or remove old work merely because this handover exists.
- For a small immaterial issue whose safe fix needs substantial code or effort, give the owner one concrete keep/defer choice. Do not turn extraction closeout into an unbounded pursuit of theoretical perfection.

## Verified starting state

Repository: `/home/faisal/EventMarketDB`.

| Item | At handover inspection |
|---|---|
| Local main | `cf01ed22b29087b1653e42e7d9cf152ad83d9e66` |
| Recorded `origin/main` | `5d22ac8d33afb1e118fd3d87b17c680b19cd5563`; local remote-tracking ref, not a fresh GitHub query |
| Difference | One approved resource-closure commit, `cf01ed22b`; no reader behavior change |
| Runtime/test working tree | No edits under `driver/prepare/`, `tests/driver/prepare/` or `benchmarks/prepare/grader/` at inspection |
| Other working-tree files | Many unrelated edits/deletions/untracked files; preserve them. This handover adds documentation only. |
| Latest accepted suites | **651 permanent + 402 retained grader tests**, no skips; saved replay unchanged on 506 inputs/both modes and 576 packets. These are prior exact-candidate receipts, not a new run by the handover writer. |
| Current independent-test status | **KEY_READY / SCORER_NOT_READY / EXAM_NOT_RUN** |

Latest code gate: `/home/faisal/prepare_work/packet_close_20261009/ROOT_GATE.md`. The prior complete image composition is `/home/faisal/prepare_work/picture_chain_preflight_20261009/ROOT_FINAL_GATE.md`. Prepared bytes, raw records and every occurrence are wired through the runtime; the proof uses fake readers and a test consumer, not the unbuilt final AI consumer.

## Code map and tests

```text
driver/prepare/get/              verified package download/archive/member reading
driver/prepare/convert/          HTML/XML extraction, source formatting and browser evidence
  html_route.py                 prepare(raw, file_id, sha256, browser), caller-owned browser
  edgartools_html.py             native tree -> ordered source-linked units/cells/pictures
  anchor.py                     source scanning/location; bounded rendering limits remain
  screen_grid.py                existing browser geometry/spacing measurement
  source_formatting.py           source style/strike evidence
  xml_fields.py                 strict XML fields + complete parsed element inventory
driver/prepare/pictures/         preparation, reader identity, workers, raw evidence and packets
  join.py                       source-bound picture/archive/worker/packet composition
driver/prepare/compare.py        shared pure comparison rules; grader imports this
tests/driver/prepare/            permanent get/convert/pictures/shared/fixture regressions
benchmarks/prepare/grader/       retained scoring/evaluation, not production runtime
```

Read module docstrings/current code for exact contracts. IDs such as unit indexes and native paragraph groups are **document/version local**; a re-extraction can change them. Pin source hash + output version + occurrence/source anchor for references; do not promise IDs survive arbitrary code changes. Raw source retention lets a later tree add metadata without routinely rewriting extracted text.

**Actual backend gap:** the committed `readers.chandra(model, wheel)` imports `mlx_vlm`. This is the reviewed Mac path, not a qualified NVIDIA/vLLM implementation. When the production GPU is selected, inspect/reuse Chandra's native server client at the pinned version and fit it to the existing reader/result boundary; no new backend framework. Prove input/settings identity and behavior with the real-worker repeat. Do not describe this as already solved by offline tests.

Approved offline environment: `/home/faisal/prepare_work/venvs/prepare-tests/bin/python` (Linux CPython 3.11.10). Pins: `tests/driver/prepare/requirements.txt`. It includes EdgarTools 5.60.0, Playwright 1.59.0, required Chromium/fonts, RapidOCR 3.9.2, OnnxTR 0.9.0 and native helper dependencies. The application venv is not interchangeable. Isolated newer Docling/EdgarTools installations were research only.

```bash
cd /home/faisal/EventMarketDB
export PREPARE_TEST_DATA=/home/faisal/prepare_test_data
env -u PYTHONPATH /home/faisal/prepare_work/venvs/prepare-tests/bin/python \
  -m unittest discover -s tests/driver/prepare -t . -v
env -u PYTHONPATH /home/faisal/prepare_work/venvs/prepare-tests/bin/python \
  -m unittest discover -s benchmarks/prepare/grader/tests -t . -v
```

Run from the checkout being tested; clear exported PYTHONPATH so it cannot import main accidentally. Use a bounded process timeout and unique output folder; retain actual exit status. Missing dependencies/fixtures fail, never skip. No model/download/SEC call belongs in these offline tests. Permanent fixtures include the 506-input, 576-packet and worker/handoff checks; do not repeat every old research script automatically after a green suite.

Large fixtures: `/home/faisal/prepare_test_data`, hash-pinned by `tests/driver/prepare/fixtures/manifest.json`, loaded through existing `support.py` and get's blob format. Backup/restore record and exact commands are in `tests/driver/prepare/README.md`; its early test-count paragraphs are historical. **Known documentation gap:** `driver/README.md` links to a nonexistent `driver/prepare/README.md`; include this in the bounded documentation/organization pass, not as an extraction bug.

## Next work: sequential and bounded

1. **Reconcile the extraction closeout contract from current output, without building a tree or wrapper.** Confirm original bytes, document/version/occurrence references, order, paragraphs, complete tables, XML context, raw OCR and available layout/style evidence survive serialization. Use existing test-consumer examples. Separate code loss from model error, scorer inability and deferred semantic hierarchy. Produce one short open list; do not revive superseded bugs.
2. **Finish only the necessary extraction-scoring coverage using existing checks.** Test Agent owns private keys and scorer implementation; root gates public changes. Start from accepted v15 and `public/SCORER_CLOSURE_INVENTORY_20261009.md`. The 256 XML-alias and 330 source-hash binding proposals already reached accepted v13/v14; do not redo them. The scalar XML adapter was rejected as unnecessary. The table-span guard is accepted, not a complete-grid comparator. Tables/picture text and their required source relationships still need an honest extraction assessment. Any split of extraction versus deferred tree/model duties must be explicitly documented; do not alter sealed answers or award unsupported duties a pass. If this cannot close minimally, present the exact scope choice to the owner rather than building another project.
3. **Make the bounded PDF coverage decision.** Use the existing 431-file census and saved PDF/native/OCR trials. A same-type HTML file is only a candidate equivalent. Establish actual unique required content and reuse the existing lane for necessary fallbacks. Keep unread sources counted. No whole-PDF rewrite or unbounded new tool bake-off.
4. **Resolve demonstrated material code-owned defects only, one class at a time.** Fable leads HTML/XML; OCR leads pictures; the other challenges preservation. Root checks sources and exact candidate, then integrates safely. Unknown fonts, unbound link ownership and difficult browser rendering have named limits; assess real meaning loss and native proof before extending code. No regression guarantee is possible; require no unexplained changes in the tested scope.
5. **Owner-guided output understanding, organization and optimization.** Keep the smallest runtime and one implementation of each shared rule. Remove duplicates only after test/fixture/archive reconciliation. Measure time/memory/storage on fixed inputs and keep output semantics exact. This is not permission to design downstream drivers or a generic chunking framework.
6. **Freeze → independent exam → actual-worker qualification/repeat → release decision.** The owner expressly requests the final Test Agent sample test at the end of extraction closeout. That is conditional authorization once the required code review, regressions, output/scoring scope and freeze are complete: record the exact candidate/settings/scorer/key and gate, then coordinate Test Agent to run it. Do not stop at regression success or ask the owner to repeat this instruction. Do not run early or waive an unmet scoring requirement; ask only if a real scope/compute/remaining-risk decision is unresolved. Builders do not see private answers beforehand. Afterward, actual NVIDIA Chandra and bounded CPU workers need model/file/provider/settings, real inference/resource, lock/restart and filesystem checks; repeat the same validation inputs to detect backend changes. The repeat is not a second unseen exam. No hidden human production step.

Completion means: required extraction behavior is demonstrated on the declared scope, every input/omission has an honest state, regressions and original-backed validation pass or their exceptions are explicitly accepted, actual workers are qualified, and code/docs are organized. It **does not mean** universal 100% correctness, a working semantic document tree, a completed final AI consumer, or corrected Chandra hallucinations.

## Existing agents and how to reach them

No new team or messaging daemon is needed. Confirm availability before assigning tasks. Root retains priorities, design choices and gates; builders can exchange technical evidence directly, copying the durable root inbox.

**How to orchestrate:** keep one short live task list with issue, owner, exact baseline, independent reviewer, next checkpoint and acceptance evidence. Give each assignee one self-contained work order: end use, all standing constraints, reproduced class, permitted scope, native functionality to check, tests/positive controls, exact deliverable and reply path. Start with Fable reviewing HTML/XML/image boundaries and OCR reviewing raw readings/workers/delivery; use cross-review only after each identifies a concrete finding. Root owns downloader/inventory and the combined contract, delegating a bounded inspection if useful. Test Agent receives public schema/scoring work only, never builder-side solution hints or requests to reveal chosen answers. Local agent gets only machine-dependent work with exact input/settings and a finite budget. Check activity before assignment, avoid duplicate corpus runs and overlapping edits, poll durable replies on 30–60-second intervals while active, and reassess at each milestone or contradiction. Root decides continue/fix/defer/close; a bot's confident report is evidence to inspect, not an instruction to obey. Communicate material results and blockers plainly to the owner.

| Agent | Responsibility | Communication |
|---|---|---|
| **Fable**, Claude name `driver-helper` | HTML/XML, browser/native integration, converter regressions; independent challenge of OCR handoff | Existing Claude relay below. Old worktrees/branch names are historical; request current exact checkout/hash. |
| **OCR**, Claude name `driver-prepare` | Picture preparation, raw-reading preservation, worker/cache identity and OCR tests; challenge HTML image/context preservation | Same Claude relay. Do not confuse this name with this retiring Codex conversation, also titled `driver-prepare`. |
| **Test Agent**, Codex title `testing-agent` | Independent keys, public scorer contracts and final exam under its gate | `mcp__codex_tui__list_threads` then `send_message_to_thread`; current ID `01a116b6-2a99-7741-bf10-2b1065846661` (listed idle at handover). |
| **Local agent**, separate Mac session `local-agent` | Actual Mac/native Chandra installation and narrowly frozen machine diagnostics | SSH file outbox/inbox below. It was not listed on this Codex app server; writing a file does not guarantee an idle Mac session wakes. Owner can trigger it by pasting the read command. |

**Fable/OCR relay.** Read `/home/faisal/prepare_work/claude_relay_20261007/README.md`. The tested argv is in `roundtrip-6e245c0480/command.json`; send a prompt on stdin through `/home/faisal/.local/bin/claude -p` in a **fresh relay session**, using its existing restricted `ToolSearch,SendMessage` configuration. Use a unique relay/request name and capture the result. Ask native ToolSearch/ListAgents for the current recipient if necessary; never reuse an old `uds:` address, resume/take over a builder session or substitute Notion messaging.

Request shape: “Send this work order to native Claude agent `driver-helper` [or `driver-prepare`]: read `<public work-order path>`, acknowledge scope/current revision, and write your reply to `/home/faisal/prepare_work/claude_relay_20261007/inbox/<agent>-<UTC>-<request-id>.md`. Preserve old replies; include request ID, evidence paths and exact hashes. No private test material.” The one-shot relay may exit before a native reply arrives; **saved inbox files are the standard return path**. Poll them every 30–60 seconds during active work, reassess on a bounded timeout and report blockers. They do not wake an idle Codex turn automatically.

**Test Agent.** Discover tools by exact name if not initially exposed: `mcp__codex_tui__list_threads`, `mcp__codex_tui__send_message_to_thread`. The latter takes `{threadId, prompt}` with a maximum **1,000 UTF-8 bytes**; put longer work orders in an approved public file and send the path. Omit model overrides. Re-list to verify identity; do not create a second testing session. Request **public aggregate/status/schema replies only**. Do not broadly read its thread: it may contain private answer work. Never forward chosen sources, values or hints to builders.

This direct channel was verified on this app server. A new session on a different server must rediscover access; if unavailable, give the owner one short public message/path to relay. Do not claim a message was delivered without its tool receipt.

**Mac local agent.** Master is `faisal@192.168.40.73`, minisforum2/storage is `faisal@192.168.40.72`. Existing instruction channel:

```bash
ssh -o ConnectTimeout=10 faisal@192.168.40.73 \
  'cat /home/faisal/prepare_work/ocr_completeness_20261008/mac_outbox/<NEW_WORK_ORDER>.md'
```

Place a self-contained bounded instruction in that outbox: objective, installed-model/context facts, exact allowed sources/settings, controls, time/call budget and upload instructions. Agent uploads unique reports/manifests/hashes to `.../mac_inbox/`; use the existing `.part` → hash verification → atomic publication instructions in `MAC_PART_A_INSTRUCTIONS.md`. Root reads local inbox files; never treat a partial upload as complete. Original Part A/B instructions and `CODEX_ACTIVE_SCOPE_20261008.md` are **completed history, not permission to rerun**. Native recovery/preprocessing trials failed to recover all four selected failures and were not adopted; further GPU work belongs to chosen-worker qualification. Do not install/upgrade or restart Mac models just to establish contact.

**No direct Mac-session messaging connection is verified.** SSH here is the Mac agent reading/uploading files on the master, not proof that root can SSH into or wake the Mac. If it is already polling, the file exchange suffices; otherwise send the owner the one-line read command to paste locally. After that trigger, root can monitor uploads independently. Do not confuse this file channel with Test Agent's direct Codex messages.

## Independent-test protection

Public: `/home/faisal/prepare_work/validation_next_20261007/public/KEY_READY.md` and `SCORER_V15_ACCEPTED_20261009.md`.

Private: `/home/faisal/prepare_work/validation_next_20261007/private` and restored backup payloads. **Root/builders must not open them or search them.** Exclude private directories from broad searches. The final requested exam follows only after the recorded prerequisite gate; this handover does not authorize early sealed converter/OCR execution, answer inspection or answer-specific tuning. Test Agent owns the exam execution/evaluation boundary. If the exam exposes a defect, preserve its first result and exposure status; do not relabel a post-fix rerun as fresh blind validation.

The test has 300 probability-sampled documents + 30 challenges and 300 picture slots (292 available), independently source-reviewed and sealed. Keys are ready, complete automated scoring is not. Some challenge sources are exposed; selected document regions are not whole-document correctness. Source ambiguities, unavailable slots and repeated-image/filing clusters remain in reporting. See the snapshot for limits. Keep historical 78% held-out results separate from later 64/64 released regression results.

## Parked work and preserved knowledge

- **Document tree:** no production adoption. First common parent-method pass supported 853/862 across ten exposed documents, but repeat annual-report runs ranged 346–362/368; reliable 99% not established. Discovery, unheaded returns, image-internal headings, exact source addresses, full-input limits and source ambiguity remain separate. Read only when reopened: `/home/faisal/prepare_work/section_mapping_20261010/PARENT_ONLY_PLAN.md` and `LIMITATIONS_CURRENT.md`. The owner requires all remaining tree limitations explained together at that later closeout. No routine stronger model is authorized for this task; prior one-off diagnostic permission is not a new experiment mandate.
- **Vendor reuse:** `/home/faisal/prepare_work/secapi_deep_review_20261010/REPORT.md`. Item text and four-statement JSON are already in Neo4j; our Arelle network data already covers K/Q financial structures. SEC-API does not establish a complete document tree/general OCR replacement. Old stored flattened text is not the new Prepare output. Current key was exhausted in the audit. Do not repeat it or start a subscription integration.
- **Cost/model ideas:** `DataLabChandra.md` consolidates Chandra/API evidence; Runpod timing is projected until tested. Haiku OCR comparison and deciding whether both free readers are needed are deferred optimization ideas, not closeout prerequisites. Sonnet remains off.
- **PDF:** preserved work/census is linked from PrepareTools; a needed fallback must be decided before claiming complete extraction. News, transcripts, live-ingestion orchestration and downstream drivers remain separate; do not silently extend this task to them.

The handover writer ran no model, converter, regression suite or sealed exam, and made no code change, commit or push for this handover. Its new evidence is the readback of the named records, git state, sample counts and communication endpoints. Verify drift, reuse completed work and finish one bounded milestone at a time.

## Prompt for the new session

> Read `/home/faisal/EventMarketDB/.claude/plans/Drivers/DriversFinal/PrepareExtractionHandover.md`, its linked extraction snapshot, the latest scope in `PrepareTools.md`, and repository `AGENTS.md`.
>
> Your primary job is strategy, orchestration and independent review. You own priorities, design and acceptance. Freshly verify the current code and evidence, then coordinate Fable, OCR, Test Agent and the Mac local agent through their documented, different communication channels. Delegate bounded work and reassess after each milestone; keep Test Agent's answers private and independent.
>
> Finish extraction only: HTML, XML, picture/OCR integration and the bounded PDF coverage decision. No document-tree/hierarchy experiments, downstream wrappers or driver creation. Target complete extraction fidelity with fully generic, minimal, well-organized code. Inspect and reuse native library functionality first; no document-specific exceptions, duplicate machinery or speculative features. Preserve source content, required relationships, provenance, raw readings and explicit failures. Keep Chandra-origin errors separately reported under the owner's accepted limitation.
>
> Resolve demonstrated material code defects, retain regression evidence, complete required scoring coverage and the owner-guided organization/optimization pass, then freeze and have Test Agent run the final independent sample once all prerequisites pass. Complete actual-worker qualification and the same-input backend repeat before claiming production readiness. Never weaken expectations to pass or claim universal perfection from sample results.
>
> First report the verified starting state, essential clarification if any, and your first bounded action. Otherwise proceed autonomously, one reviewed milestone at a time, following the handover's acceptance and authorization boundaries.
