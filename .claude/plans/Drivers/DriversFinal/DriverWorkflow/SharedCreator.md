# Shared creator Incomplete

> **Status: not vetted, not built.** So far one core idea stands out: **one shared creator, a single interface that every caller (the 3 company stages, any bot) uses to turn a document into checked Driver updates.** Everything else below still needs a careful look; something useful may have been missed.

Part of [DriverWorkflow.md](DriverWorkflow.md). Several readers use [base + copies](BaseAndCopies.md).

## 1. Shared creator: 7 steps

**Why:** one creator for every caller (the 3 company stages, any bot), so creation rules never split into versions.

`Material + request → creator → checked proposals → separate save`

1. **Accept:** takes any report, transcript, news story or plain-text excerpt, plus a request saying which parts and which fact types.
   - Default: all parts, all qualified types. An empty or invalid request never becomes "all"; unsupported requests fail clearly.
   - Full context may come with a small request; an excerpt doesn't force extracting its whole report.
2. **Format:** shared code (not each caller) builds the reading view, reusing prepared units and [readback](../../../../../driver/prepare/reconstruct.py).
   - Keeps structure, references and known gaps. Plain text is a format, not automatically News.
   - Fetching sources happens outside; never invent missing provenance or context.
3. **Choose readers:** automatic. One Claude call if the answer fits; otherwise [base + copies](BaseAndCopies.md): each part goes to exactly one copy, and every copy sees all the material. The caller never picks reader count or model.
4. **Propose:** Claude proposes facts, Driver names/types and the fields it can support.
   - It doesn't see existing Driver names or slice lists. Source text is data, never instructions.
   - Add AI calls only for real dependencies, independent checks or a measured gain.
5. **Check** (inside the creator):
   - Find each fact's company, or confirm it's shared (unknown ≠ shared); look up calendars, slices, allowed prior guidance, units and line items as needed.
   - Past lookups follow time rules; matching to Drivers uses today's Driver list.
   - Identity, duplicate and family checks, matching, dependent fields and links all happen here.
   - The checker sees the evidence and the proposal, never the proposer's reasoning or an earlier verdict (8.2).
6. **Return:** checked proposals (fields, links, exact evidence, identity decisions), plus what was worked on and known problems.
   - No approved identity → nothing saveable. Add only required companions (e.g. a surprise's matching result).
   - Use the existing skipped/held/rejected labels and field-level `unknown`; unrequested work isn't "skipped"; never claim "saved".
   - The sender tracks completion; a small request can't mark the whole source done.
7. **Save:** a separate writer applies the rules, rechecks source, identity and links in one all-or-nothing write, and assigns IDs once identity is settled. Stock-move opinions stay separate ([EXPLAINED_BY](../EXPLAINED_BY.md)).

## 2. What the AI sees

| Show the AI | Keep in code |
| --- | --- |
| Original words and numbers in order, incl. titles, speakers, periods, scales, conditions, notes | Original content, file/version map, source locations |
| Short IDs, file-qualified when needed (`F1:u7`) | Byte offsets, hashes, parser internals, storage paths |
| Whole tables: addressable cells, real headers, merged spans, captions, note markers | Original cell records and coordinates |
| Real images in order with IDs (or a faithful representation); if missing, `F1:img1 — image content unavailable`, counted as uncovered | Image files, identity, placement |
| Source-proven links: caption ownership, table grouping, lists, paragraph continuation | Guessed heading/text kinds and levels (hide the guess, not the words) |
| Company, document, publication time and file boundaries, once | Repeated storage metadata |
| XML/XBRL: field names + entity, period, unit and dimension context | Raw bytes, storage details |

These are information needs; display format and field names are undecided. Hiding metadata must never remove meaning or a known gap. Publication time ≠ a fact's reporting period. Image delivery and caching still need testing.
**Example view** (fictional; an assignment follows the shared material and instructions):

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

Evidence (needs the rule changes below): revenue `100` cites cell `F1:t1/r2/c2` plus its label `r2/c1`, year `r1/c2` and scale note `F1:u2`; code copies each original fragment. A quote shorter than its unit/cell needs an exact span.

## 3. Checks (planned)

Reuse existing source-preservation checks; check the reading view's structure and locations, not just its words.

**Code checks**
- **References:** every ID/cell/span resolves in the saved file version; reject missing or out-of-range ones (valid ≠ relevant).
- **Exact evidence:** copy original source text, never display labels; compare model quotes exactly; keep fragments separate; check each number at its own address (an equal number elsewhere is no match).
- **Missing work:** every selected unit, turn, table row and image gets proposals or a reason for none, with problems kept. Flag missing replies and anchors outside the assignment (except required companions). Context may come from anywhere; one answered row ≠ all its facts found.
- **Duplicates:** never count a retried job twice; apply shared duplicate rules (several facts may cite one unit; meaning-level duplicates need judgment).
- **Output + failures:** validate fields, types and required links; detect failed requests, output-limit stops, safety stops (check the counter) and missing replies; any of these means incomplete even if status is `success`. Keep valid partial work; bound and log retries (8.12); test recovery later. A valid "no"/"unsure" is not a failure; shrink oversized assignments; never treat incomplete as empty.
- **Effort:** record configured effort and visible reasoning signs; they don't prove correctness, and a missing thinking log alone isn't a reason to retry.

**Model/reviewer checks**
- **Meaning:** subject, period, scale, conditions and whether notes/definitions apply (incl. shared titles/headers); context can be distant or unmarked; one exhibit's scope doesn't automatically govern another.
- **Eligibility:** qualitative facts count; "no number" alone is never a rejection. Admission rules still apply.
- **Ownership:** a statement spanning passages belongs where it begins, not to an earlier heading/note (needs judgment); supporting copies aren't new facts.

Exact quotes and full unit/row coverage don't prove complete recall, correct meaning, OCR fidelity or complete extraction.

## 4. Rule changes needed (awaiting your approval)

No rule is changed yet. Always keep source identity, exact evidence, eligibility and atomic saving.

| Rule | Proposed change |
| --- | --- |
| 1.17 | A number can be backed by its exact fragment plus separately located context from the same source version; the whole filing stays the source event. |
| 1.24 | Several exact fragments may together keep all meaning-changing words (instead of skipping when one quote can't); they must jointly apply. |
| 3.29 | A separately located unit/scale fragment is allowed if it applies; nearness alone isn't enough; exact scaling unchanged. |
| 3.3, 2.1, 3.53 | Evidence fields, frozen Driver evidence and stated-cause link evidence use fragments; names open; 8.8 (no rewritten quotes) stays. If reused, align ChannelContract Part II §§7–8 and quote validators. |
| 8.10 | A creator call may process selected pieces/types; the sender tracks whole-source coverage; context ≠ requested work. |
| 8.14 | Define outcomes for selected work (incl. table rows); separate creator proposals from writer outcomes; unrequested ≠ skipped; incomplete never shows as complete; atomic save per job. |
| 8.15 | Fit retries to selected pieces/types and the job boundary; reuse after a stale match is open; no matching-only retry. |
| 4.15 (keep 4.14) | A surprise request may return its required home fact without extracting everything else; if the home is missing, keep the full-event reread unless amended. |

## 5. Open decisions

- **First fact types and source kind:** qualify the real request/configuration (8.13); testing one type alone doesn't qualify a combination.
- **Input/output fields:** names and shape for evidence, work selection, identity decisions, gaps and links. Reuse rulebook fields and reviewed helpers; today's `Asset` and staged `PreparedFactV2` aren't drop-in.
- **Redoing an out-of-date match:** reuse a completed read only if its inputs and meaning still hold; trigger, kept state and retry scope still to agree.
- **Matching and batching:** matching search, judgment batching and cost need testing; no per-field service or model router; Jev/Qwen roles are unqualified. Reader count and effort: see [base + copies](BaseAndCopies.md#still-open).

## 6. Next tests

1. Settle the open decisions; freeze independent answer keys before model runs (8.13, 8.17). Use fresh sources per source kind, incl. full, partial and selected-type requests; AMG is regression evidence, not an unseen test.
2. Score full meaning, qualitative and numeric recall, names, subjects, periods, evidence and duplicates, incl. distant/inapplicable notes, three-passage dependencies, large tables, images, failures and positive controls. Count misses, refusals and unscorable cases.
3. Measure loading, cache/input/output, reasoning, checks, retries, queues and historical/live throughput, using per-reply usage (don't recount the base); list prices ≠ subscription charges. Add stages only for proven benefit; no finite test proves 100% future accuracy.
