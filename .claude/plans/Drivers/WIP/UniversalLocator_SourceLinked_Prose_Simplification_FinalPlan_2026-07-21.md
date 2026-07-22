# Universal Locator — Source-Linked and Prose Simplification Final Change Plan

**Date:** 2026-07-21

**Status:** owner-approved — **the SOLE CURRENT EXECUTION AMENDMENT / WORK ORDER over
the locked Locator Design v5.5 base** (NOT the sole source of all Locator law); **PHASE 1 CLOSED (final-accepted 2026-07-22) · PHASE 2 CLOSED (the combined M1–M4 package accepted + frozen 2026-07-22 — cost estimates, not reader/Route-B certification) · PHASE 3 EXECUTED (prose machinery deleted; close commit e64ce11 pending its audit + amend) — Phase 4 NOT started; push blocked; Route C held.** The locked Design v5.5 remains the
base contract for every rule not explicitly replaced here. This plan REPLACES exactly:
Corrective-5 Batch B/C/D · Design Round-14 §3 · the Batch-C rows of Design Round-14 §4 ·
Design Round-14 §5's old measurement sequence · the draft disposition table (now §16
here). It never overrides locked system law (FINAL_DESIGN, ChannelContract, PER-21,
BUILD_AND_OPERATIONS, Core ownership, News). Reading order: locked Design base →
this FinalPlan (changes + current steps) → Review Record (history).

**Scope:** Fiscal Universal Locator WP2–WP4 execution order. The active Channel Contract and
the locked identity/storage laws do not change.

[2026-07-21 status correction: the owner ACCEPTED this plan; it now actively replaces the
Corrective-5 Batch B/C/D prose-patching sequence and the superseded Round-14 prose
details. Claude-maintained files HAVE since been edited under audit orders (Design
supersession banners, Record entries, memory front door) — the original "no active
Claude file is edited by this plan" line described only the plan's own creation.]

---

## 1. Goal in plain words

Use the source's own structure whenever it can prove the answer. Use one batched reader for the
remaining meaning questions. Keep code responsible for exact source checks, not for trying to
understand arbitrary English with more sentence and connector rules.

Release target:

- zero observed wrong emitted facts in every approved test group, with denominators and error bounds;
- recall pushed as close to 100% as the source and evidence allow;
- no person in the normal runtime loop;
- the fewest reader tokens that can be saved **without** rebuilding a large prose parser;
- a materially smaller neutral locator.

Zero observed errors is the release bar. It is measured evidence, not a claim of mathematical
perfection.

---

## 2. Why the plan changes now

The flat-text route has shown the wrong cost curve:

- `driver/relocation/locator.py` grew from 756 lines at `7f052b0` to 1,808 lines now.
- `test_locator_routes.py` grew from 187 to 1,406 lines.
- The locator now contains 21 compiled patterns and 60 regex-use lines in total, including those
  pattern definitions.
- Thirteen audit rounds repeatedly found new interactions among number ownership, labels, units,
  periods, punctuation, and neighbouring values.

Those rounds were useful: they exposed the real failure classes. They also showed that flat prose
meaning is not a small set of safe text rules. Continuing Batch B/C would keep expanding that same
design.

The source-linked XBRL route has the opposite shape:

- 2,019,825 usable numeric graph facts in the cached filing corpus each resolve to exactly one
  displayed inline-XBRL element; zero were missing or duplicated.
- Of 3,332 facts with a missing/blank SHORT `Fact.fact_id` (inline_element_id) **within the
  cached M3 population** (globally the graph holds 34,277 such facts), 3,324 resolve uniquely
  by complete element identity and 8 are honestly ambiguous.
- The exact displayed element declares value formatting, scale, sign, context, and unit reference.
- 12,402,201 numeric non-nil graph facts have exactly one semantic Unit edge.

That lets us delete guesses instead of adding rules.

---

## 3. Corrections to the proposed four-lane idea

| Proposed idea | Final ruling |
|---|---|
| A later 10-Q/K makes old 8-K history easy | **Partly true.** The later fact may supply a retrieval clue during backfill, but the old 8-K must still prove its own quote, value, label, period, slice, and measurement. Future evidence is never proof for the earlier event. |
| Press-release tables can reuse the filing table reader | **Possible, not yet proven.** Current graph text has already lost HTML rows and headers. We must fetch the original exhibit HTML and measure coverage before building this shortcut. |
| Real-time prose should use a reader | **Yes, after certification.** The 8-K arrives before the 10-Q/K, so it cannot rely on a future tagged fact. |
| Contested flat prose should always abstain | **Not permanently.** Send it to the certified reader; abstain only when the reader plus source verifier cannot prove one answer. |
| Every 8-K level later gets a tagged twin | **False as stated.** Measured numeric overlap is partial. A later twin is a grading aid, never live evidence. |
| Most spoken percentages can be recomputed from tagged levels | **Unproven and often unsafe.** Organic, adjusted, constant-currency, and rounded percentages may not share the tagged definition. Measure exact-definition coverage first. Any calculation may only reject a contradiction; it never becomes a stored fact or proof. |

---

## 4. Final small architecture

```text
ONE source event, in public-time order
        |
        v
fetch once and preserve source structure
        |
        +--> tagged 10-Q/K element --> exact source-linked proof ----------+
        |                                                               |
        +--> native 8-K table row --> optional measured fast path --------+--> shared source verifier --> raw item
        |                                                               |
        +--> known-value old text --> optional measured fast path --------+
        |                                                               |
        +--> remaining 8-K/transcript prose --> one batched reader -------+
                                                                        |
                                                        cannot prove --> no_proven_match
```

The normal source order is:

```text
8-K / press release  ->  transcript  ->  later 10-Q or 10-K
```

Each event stands on its own. The later filing may grade earlier output after the fact, but it cannot
change what evidence was available when the earlier event was public.

News stays a separate channel. It may later reuse the block format, batching, and source verifier,
but Fiscal must not gain news-specific retrieval or meaning rules.

---

## 5. Route contracts

### Route A — exact tagged filing fact

For 10-Q/K inline XBRL:

1. Fetch the display `.htm` once. Never substitute the extracted `_htm.xml` instance.
2. Join the exact graph Fact to its exact inline element by **`inline_element_id` =
   graph property `Fact.fact_id`** — the SHORT inline-element id (e.g. `f-498`) that
   matches the display HTML element's `id=` attribute. **`graph_fact_id` = `Fact.id`/
   `u_id`** is the LONG canonical graph identity: it CONTAINS the short id as its
   suffix but is NEVER equal to the HTML id, and the HTML never contains it. (Existing
   artifacts confusingly call the long value `fact_id`; plan names are the unambiguous
   ones. Stored schemas are NOT renamed. Corrected 2026-07-21 — the reviewer's own
   earlier instruction inverted this; graph-verified: 13,775,616 Facts · long id on
   all · 34,277 short ids blank/null · all 13,741,339 usable long ids end with their
   short id · zero long==short.)
3. If the SHORT id (`Fact.fact_id`) is null/blank, use the complete
   `(name, contextRef, unitRef)` fallback only when unique.
4. Reconcile displayed text, format, scale, sign, and graph value with exact Decimal arithmetic.
5. Carry the exact row, aligned header stack, section caption, context, raw unitRef, and semantic
   Unit/divide meaning.
6. Use only this element-local evidence for anchor wording, slice, and measurement proof.
7. Missing, duplicate, hidden-without-local-evidence, malformed, or conflicting evidence abstains.

No raw-unit spelling classifier, scale guessing, document-wide sentence parser, or period-word
parser belongs in this route.

### Route B — optional native-table fast path

This route exists only if the measurement gate in §8 passes.

It may accept only a true source-native row with its complete header stack and an unambiguous cell.
It must use the original 8-K exhibit HTML, not the current flattened graph string. A flattened table,
PDF, missing header, multi-value row without a unique column, or disputed label goes to the reader.

Do not build a second table framework. Reuse the smallest suitable DOM row/header extractor already
used by the source-linked filing route.

### Route C — optional known-value fast path

This route also exists only if the shadow gate in §8 passes.

A hint is untrusted and must be stamped with this source. It may retrieve an exact printed value but
cannot prove meaning. Acceptance requires one source-native block that independently proves the full
stable identity and stated period, with one valid occurrence and no conflict. A later period's value
is never used as the target value for a new period.

If this contract needs sentence territory, connector lists, qualifier lists, fuzzy labels, or broad
period-language rules, cut the route and use the reader.

### Route D — batched semantic reader

For remaining press-release and transcript prose:

- fetch once and split only at source-native blocks: DOM paragraphs/list items/table rows,
  `PreparedRemark`, and individual `QAExchange` nodes;
- when one native block exceeds the reader cap, treat splitting as transport only: reuse the
  existing byte-exact chunker, keep absolute offsets/hashes, and include the neighbouring part for
  an occurrence at a cut. First shadow-prove that no evidence is lost; build no new language splitter;
- assign stable block ids and numeric occurrence ids;
- default to an exhaustive manifest of every numeric-bearing block in the source. Cheap retrieval may
  order blocks, but it may not silently filter them until an independent whole-source recall test
  certifies that filter;
- batch several anchors for one source, reusing the existing capped batch runner;
- ask the reader only which exact occurrence belongs to which anchor and why;
- require the reader to return `anchor_id`, `block_id`, `occurrence_id`, and exact copied label and
  period evidence;
- code takes the quote from the original source by id. It never trusts a model-written quote;
- the shared verifier checks source stamp, exact span, exact Decimal value, sign, printed unit/form,
  and conflicts;
- the locked Core gate independently tries to falsify the proposed identity and scope. Until that
  gate exists, no-XBRL admissions stay fenced;
- uncertain or unverifiable output abstains.

Start with one reader pass. Add a second model or escalation only if measured certification shows it
is required. No human decision is allowed in normal runtime.

Numberless anchors are a separate reader test group: they return an exact source span rather than a
numeric occurrence id. Routes A–C do not pretend to solve them.

### Route E — honest no match

Until a reader group is certified, unresolved prose returns `no_proven_match`. After certification,
the same result is used when the reader or verifier cannot prove a unique fact. Completeness and retry
rules remain those of the Channel Contract.

---

## 6. One shared verifier; exact limits on regular expressions

The verifier owns only mechanical facts:

- the source id and public time;
- the original block and exact byte/character span;
- exact numeric parsing, including commas and accounting negatives;
- exact printed value form, sign, and unit mark;
- stable block/occurrence identity;
- duplicate and conflict rejection;
- exact XBRL context and semantic Unit data when present.

Regular expressions are allowed only for small lexical jobs such as number forms, whitespace,
literal unit marks, and safe token boundaries. They must not decide:

- which neighbouring words belong to a number;
- metric, slice, or measurement meaning;
- period meaning in arbitrary prose;
- sentence ownership through connector or punctuation lists;
- concept/member meaning from spelling.

Source DOM/node boundaries and exact spans decide location. The reader and Core decide meaning.

---

## 7. Point-in-time law

For a fact emitted from source `S`, runtime proof may use only `S` plus the period-free anchor that
the design permits.

- The live 8-K cannot see its later 10-Q/K.
- Historical backfill may use a later-built Driver identity as one untrusted retrieval clue, but the
  old source must reconfirm everything itself.
- A later exact twin may grade or calibrate an earlier result. It never becomes evidence stamped on
  the earlier result.
- A computed percentage is never emitted because the Channel Contract forbids computed facts.
- All dry runs and comparisons process source events in public-time order.

---

## 8. Required no-token measurements before any prose implementation

These measurements use frozen inputs, exact population definitions, saved commands/queries, source
hashes, and independent truth. Synthetic tests may add attacks but cannot replace real data.

### M1 — source structure inventory

On the canonically selected earnings 8-Ks and Transcript nodes, report:

- exact source/event count and missing-source count;
- original exhibit HTML fetch success and stable hashes;
- numeric occurrences in real DOM tables versus paragraphs/lists;
- table occurrences with a complete row and header stack versus incomplete/ambiguous rows;
- HTML versus PDF and other unsupported forms;
- transcript occurrences by `PreparedRemark` and `QAExchange` block.

Classification must come from source structure, not text punctuation.

### M2 — minimal fast-path shadow

Run the proposed native-table and known-value contracts without production edits across:

- every current route-test family;
- the frozen real filing, press-release, and transcript exams;
- WP1 committed outputs;
- the 150-case live XBRL gate;
- the 28 regression floors.

Report exact correct, wrong, safe abstain, and newly recovered counts by source type. Every current
test gets a disposition: **keep**, **move to reader certification**, or **retire because the tested
heuristic is deleted**. No test disappears silently.

Keep an optional fast path only if it has zero observed wrong accepts, simplifies the final code,
and saves meaningful reader work. Otherwise cut it. If the result is a genuine cost/complexity
tradeoff, bring the owner one measured keep-or-cut question; recommend the smaller safe choice.

### M3 — later verification coverage

Measure two separate things; never combine them:

1. **Exact later twins:** an earlier source fact and a later tagged fact agree on company, metric,
   slice, measurement, period, unit, and value after explicit source scale. Numeric coincidence
   without identity does not count. Report exact equality separately from a tagged value that merely
   falls inside the interval implied by an explicitly rounded print.
2. **Exact-definition calculations:** a spoken percentage has all required tagged inputs with the
   same definition and compatible rounding.

Report denominators and misses by money/level, count, growth, margin, adjusted, organic, and other.
These are offline grading/falsifier measurements only. Build no calculation path unless it has useful
coverage and zero false rejection on an independent set.

### M4 — residual and reader cost

After Routes A and any earned fast path, report by 8-K table, 8-K prose, prepared remarks, and Q&A:

- anchors searched;
- on independently labelled strata: facts truly present, accepted, wrong, ambiguous, and absent;
- on the full unlabelled corpus: volume and residual counts only, never guessed truth labels;
- source blocks and characters sent;
- projected calls and input/output tokens with existing batching;
- tokens per searched anchor and per accepted fact;
- backfill and live-run cost ranges.

No paid reader run occurs during M1–M4.

---

## 9. Evidence already available

The graph and repository counts below were reproduced already; Claude must reproduce them before
relying on them in a new build. The final later-twin subsection is only a prior planning signal and
must be replaced by M3's saved population and query.

### Tagged filing facts

- Display-HTML cache: 1,722 files, 4,355,832,567 bytes.
- Usable numeric facts joined by id: 2,019,825 / 2,019,825 exactly once.
- Missing-`Fact.fact_id` (inline_element_id) fallback, cached population: 3,332 total; 3,324
  unique; 8 ambiguous; zero unmatched. (Global graph total of missing short ids: 34,277.)
- Inline numeric elements: 2,217,620; two malformed.
- Live gate: 146/150 cases cached across 140/144 accessions; four named uncached cases.
- Semantic Unit edge: 12,402,201 / 12,402,201 numeric non-nil facts exactly once.

### Current 8-K storage, independently checked on 2026-07-21

For all graph 8-K exhibits with stored content:

- 26,779 exhibit nodes;
- zero stored strings contain `<table`;
- zero contain `##TABLE_START`;
- zero contain a newline.

Therefore the current locator input is flattened and cannot prove row/header ownership.

For the broad inventory `formType STARTS WITH '8-K'`, `items` containing `2.02`, and exhibit number
`EX-99.1`, `EX-99`, or `99.1`:

- 10,274 distinct report/exhibit rows;
- all 10,274 have an exhibit URL in `Report.exhibits`;
- 10,248 URLs are HTML and 26 are PDF;
- all 10,274 stored exhibit strings are one line.

This inventory proves that original HTML is reachable in principle. It is not the final canonical
earnings-source denominator; M1 must use the approved source selector.

### Transcript storage, independently checked on 2026-07-21

- 9,608 Transcript nodes;
- 9,320 nonblank `PreparedRemark` blocks;
- 170,654 nonblank `QAExchange` blocks.

These are lawful source-native boundaries; no sentence parser is needed to create them.

### Existing reader evidence

- Fresh exam: 111 cases, 80 batched calls, 2.8M tokens.
- Pooled filing result: 171/176 precision = 97.2%; recall 171/188 = 91.0%.
- Transcript mini-exam: 4/5 correct accepted facts, with the adjusted-versus-GAAP trap still real.
- Existing caps: no more than 8 anchors or 100KB per call.

The reader is reusable machinery, not yet release-certified for this neutral route.

### Provisional later-twin evidence

In the existing 452-number transcript/news study, same-quarter numeric overlap with tagged facts was
partial: roughly 35–60% for money levels depending on coincidence controls, and much lower for
percentages. Percentages with at least three significant digits matched 0/11 transcript and 2/24
news cases. This is enough to reject the unsupported word **every**, but it is not the final coverage
measurement. M3 must reproduce it with exact identity and a saved executable population definition.

---

## 10. Keep, replace, delete

| Area | Action |
|---|---|
| Anchor rebuild and neutral import boundary | Keep. |
| Exact Decimal, value forms, sign handling, source stamps | Keep one shared copy. |
| Strict XBRL fact/context/dimension identity | Keep. |
| Fact-id to display-element join and local row/header extraction | Build/reuse as Route A. |
| Filing-declared semantic Unit/divide handoff | Build; it remains a WP2-close gate. |
| Raw unit-name tokenizer/classifier | Delete after Route A shadow passes. |
| Raw-versus-scaled candidate guessing | Delete from Route A. |
| Sentence/clause splitter, punctuation ownership, connector lists, value territories | Delete from the neutral semantic path. |
| Basis, qualifier, period-word, and camel-case context rules | Move meaning coverage to reader/Core certification; delete from the generic prose path. |
| R2's copied validator | Delete. One shared verifier only. |
| Native-table fast path | Conditional on M1/M2. Cut if it does not simplify and save meaningful reader work. |
| Known-value fast path | Conditional on M2. Keep only the small fully source-proven form. |
| Existing 13-round attack cases | Preserve as integrity tests or reader/falsifier certification cases; use a disposition ledger. |
| News-specific logic | Keep outside Fiscal. |

The final diff, not the estimated 713 lines, decides whether simplification succeeded.

---

## 11. Exact execution order

### Phase 0 — accept and freeze

1. Audit this plan and Claude's Round-14 source-linked package together.
2. Do not continue Corrective-5 Batch B, C, or D.
3. Do not write code until the owner gives GO on the combined pre-build package.
4. Pin the starting code state at `c2fc998` and record the four existing WP2 dirty paths. Do not
   reset, checkout, or overwrite them; preserve all unrelated working-tree changes.
5. Because the rejected prose work and accepted work are mixed in the same dirty files, audit in
   uncommitted chunks and stage only explicit accepted paths at final close.

### Phase 1 — source-linked tagged filing route

1. Write RED tests for exact element join, missing/blank inline_element_id (Fact.fact_id)
   uniqueness fallback, malformed/hidden cases, Decimal
   reconciliation, local row/header proof, semantic Unit/divide handoff, and source hashing.
2. Implement Route A with the smallest reuse of the pinned HTML extractor.
3. Delete only the R1 machinery made unreachable by Route A.
4. Run the old-versus-new shadows and every gate in §12.
5. Present the exact deletion/caller table and lawful test-flip ledger for audit.
6. Keep the accepted Route-A chunk uncommitted and frozen for the Phase-2 measurements. Do not
   accidentally commit the still-mixed prose work.

### Phase 2 — measure untagged sources

Run M1–M4 read-only, with zero reader tokens. Bring one evidence package containing exact queries,
source manifests/hashes, denominators, fast-path result, residual size, and token estimate.

### Phase 3 — remove the prose parser and add only earned fast paths

1. Implement Route B and/or C only if their measurement gate passed.
2. Move any accepted runtime logic out of `relocate_probe/phase2` into a clearly named production
   module in the existing architecture; production code must never import a probe or audit script.
3. Delete the superseded semantic prose machinery and R2 duplicate.
4. Migrate every old attack case to its recorded destination.
5. Re-run all gates and shadow comparisons.
6. Compare the complete final diff to `c2fc998`; it must contain only accepted final behaviour and
   records, not rejected intermediate prose patches.
7. Audit, then make the one close commit by explicit path. Do not push.

### Phase 4 — Fiscal-only chronological dry run

With the reader still off, run one or more companies through real event order:

```text
8-K -> transcript -> later 10-Q/K
```

Prove source-local evidence, no future leakage, retry outcomes, and the actual reader residual. Finish
all Fiscal work that does not require Core.

### Phase 5 — narrow Core integration gates

Only now unfreeze the minimum Core work required by the locked design:

1. an Adjusted anchor is born with `measurement=adjusted` or parks; it is never born plain;
2. create Driver -> rebuild anchor -> prove a second source;
3. exactly one backfill candidate reaches Core and old-source evidence reconfirms it;
4. an end-to-end gate confirms that Phase 1's semantic Unit/divide meaning reaches the neutral
   matcher for every available XBRL fact.

No broader Core work is authorized by this plan.

When the locked WP2 and WP3 done-bars and these blockers pass, close WP2/WP3 here. The semantic
reader is WP4; it must not silently enlarge WP2.

### Phase 6 — reader package and certification

1. Draft the new neutral request/result schema and prompt from the measured residual.
2. Reuse the current batching runner and source-prepared inputs.
3. Present model, prompt, frozen fixtures, strata, token budget, and cost estimate for separate owner
   approval.
4. Run independent unseen certification. Release a group only with zero observed wrong accepts,
   reported denominators/error bounds, and the required Core falsifier.
5. Add escalation only for a measured failing group; otherwise keep one pass.

**Owner reader policy (recorded 2026-07-22; binding for this phase):**
- No reader calls during M4.
- Zero-tool, single-shot, batched reader with minimal JSON output (zero-tool saving:
  `FinalDesign/NewsChannel.md:10`; harness-vs-single-shot cost:
  `experiments/EXP2_COST_QUALITY_ADDENDUM_2026-07-12.md:7-11,41-47`).
- Start with Sonnet 5 at low effort. Test Haiku-low ONLY on independently labelled
  easy groups. A cheaper group ships only with zero observed wrong answers AND
  meaningful savings.
- Prefer explicit OUTER escalation: Haiku → Sonnet only on ambiguity, invalid
  output, verifier conflict, or `no_proven_match`; otherwise abstain. Do NOT use
  the built-in /advisor — it is not reliably conditional
  (`.claude/plans/advisor.md:311-341`).
- Claude Code subscription only; no API key / API billing. BEFORE Phase 6 runs,
  reverify the exact allowed transport: SDK / `claude -p` is documented as a
  SEPARATE programmatic pool, not ordinary subscription usage
  (`.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md:53-101`).

### Phase 7 — WP4 activation and later News work

Activate only the independently certified reader groups. The complete final WP1 byte comparison must
be clean wherever required. News is designed and certified separately after Fiscal; shared mechanical
utilities may be reused without importing Fiscal meaning rules.

---

## 12. Required gates

Every behaviour change is RED first, then the smallest fix.

- focused route tests and exact scenario probes;
- full relocation battery;
- durable 150-case live gate, reconciling every case and preserving zero wrong;
- 28/28 regression floors;
- neutral import-and-execute boundary hash
  `81eca0aa4587d818ba7b0be6768f60f6b66157501ecb011507c9d8e59a82decb` unchanged unless
  explicitly owner-approved;
- live-gate fixture hash
  `d7d2f06849371a38e05d5ff781deb790c7b5250f3bae7a1c8ec85373607b2eec` unchanged unless
  explicitly owner-approved;
- at least one real 10-Q/K exact-element proof, one real native-table 8-K proof if Route B survives,
  one real prose 8-K or Transcript reader proof when certified, and honest negative cases;
- exact source substrings and source hashes;
- point-in-time order attacks;
- current correct-case carry-over plus a complete lawful-flip ledger;
- full WP1 scratch run and byte comparison if any WP1-reachable file changed;
- `git diff --check`, exact `numstat`, caller/dead-code search, and runtime import sweep;
- zero Neo4j writes.

Green counts alone are insufficient: read the live code and execute each important claimed case.

---

## 13. Stop rules and standing holds

Stop and report before continuing if:

- any wrong accept appears;
- a previously correct real case is lost without an explicit, independently justified ruling;
- the exact display element or original source block cannot be fetched and hash-pinned;
- the table or known-value shortcut requires new semantic regex, connector, territory, vocabulary,
  registry, or fuzzy-matching machinery;
- old and new paths duplicate meaning checks;
- the implementation does not materially reduce code;
- later evidence affects an earlier runtime decision;
- a reader group fails the zero-wrong release bar;
- a claimed corpus count lacks its executable population definition.

Standing holds remain: no Neo4j writes, no paid reader calls, no regeneration, no push, no news
implementation, and no Core edits before Phase 5 without separate owner approval.

---

## 14. Immediate instruction to Fiscal Claude — ✅ COMPLETED / HISTORICAL (2026-07-21)

✅ This instruction was fulfilled: all §9/§15 counts were independently reproduced EXACT
and the combined pre-build package was returned (Design doc ROUND 14b; Record rounds
14/14b/14c/14d/14e/14f). It is NO LONGER the next action. THE CURRENT NEXT ACTION (2026-07-22): Phases 1–2 CLOSED
(M1–M4 package accepted + frozen) · Phase 3 EXECUTED — awaiting the reviewer's audit of the
uncommitted closeout fixes, then ONE amend of e64ce11 · then Phase 4 (PIT chronological dry
run, reader off). Original text kept below as history only.

Do not code yet. Independently reproduce the new 8-K storage/URL and Transcript-block counts in §9,
then return one combined pre-build package that:

1. keeps the exact source-linked Route A design;
2. freezes Corrective-5 Batch B/C/D;
3. replaces the current prose patch sequence with M1–M4 and the conditional Route B/C decision;
4. corrects the later-twin and computed-percentage claims;
5. keeps News separate;
6. shows the revised exact keep/delete/test-migration table;
7. confirms all protected hashes and holds.

Any conflict with a pinned real case must be reported, not patched around. Code GO comes only after
that package and this plan pass audit.

---

## 15. Reproduction definitions for the new graph claims

Run against the existing Neo4j database, read-only. Record database time/snapshot with results.

### All stored 8-K exhibit shapes

```cypher
MATCH (r:Report)
WHERE r.formType STARTS WITH '8-K'
MATCH (r)-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE e.content IS NOT NULL
RETURN count(e) AS total,
       count(CASE WHEN toLower(e.content) CONTAINS '<table' THEN 1 END) AS html_table,
       count(CASE WHEN e.content CONTAINS '##TABLE_START' THEN 1 END) AS table_marker,
       count(CASE WHEN e.content CONTAINS '\n' THEN 1 END) AS multiline
```

Expected for the checked snapshot: `26779 / 0 / 0 / 0`.

### Broad earnings-8-K EX-99 inventory

```cypher
MATCH (r:Report)-[:HAS_EXHIBIT]->(e:ExhibitContent)
WHERE r.formType STARTS WITH '8-K'
  AND toString(r.items) CONTAINS '2.02'
  AND e.exhibit_number IN ['EX-99.1', 'EX-99', '99.1']
RETURN DISTINCT r.accessionNo AS accession,
       r.exhibits AS exhibits,
       e.exhibit_number AS exhibit,
       e.content AS content
```

Parse `r.exhibits` as JSON. Require the exact `e.exhibit_number` key, classify only the URL path's
final extension, and count a stored string as single-line only when neither `\n` nor `\r` is present.
Expected: 10,274 rows; 10,274 exact-key URLs; 10,248 HTML; 26 PDF; 10,274 single-line strings.

### Transcript native blocks

```cypher
MATCH (t:Transcript)
OPTIONAL MATCH (t)-[:HAS_PREPARED_REMARKS]->(p:PreparedRemark)
OPTIONAL MATCH (t)-[:HAS_QA_EXCHANGE]->(q:QAExchange)
RETURN count(DISTINCT t) AS transcripts,
       count(DISTINCT p) AS prepared_blocks,
       count(DISTINCT q) AS qa_blocks,
       count(DISTINCT CASE
         WHEN p.content IS NOT NULL AND trim(p.content) <> '' THEN p END) AS prepared_nonblank,
       count(DISTINCT CASE
         WHEN q.exchanges IS NOT NULL AND trim(toString(q.exchanges)) <> '' THEN q END) AS qa_nonblank
```

Expected: 9,608 transcripts; 9,320 prepared blocks, all nonblank; 170,654 Q&A blocks, all nonblank.

---

## 16. Authoritative six-item disposition table (frozen Batch B/C/D promises)

This is THE authoritative table (supersedes the draft in the Design doc). The full
per-test ledger remains scheduled for M2. A formerly-correct gold case must STILL BIND —
abstention is acceptable only where the gold case is genuinely ambiguous, with the
reason recorded in the ledger.

| Item | Old evidence/test reference | Final destination | Exact expected result | Phase/gate |
|---|---|---|---|---|
| ≥5-letter unexplained-qualifier rule | `_extend_label_start` zone law; test_46 docstring notes it blocks the YUM bind; round-14 probes ('In the quarter,' prefix false-abstains) | Deleted with the prose parser | Formerly-blocked VALID binds (clean label prefixes) BIND via Route A structure or certified reader; zero new wrong accepts | Phase 1/3 shadows + M2 ledger |
| YUM verbatim sentence (old Batch-B completion criterion) | test_46 (`_printed_basis` == set() law-level pin); Review Record round 2 | Reader-certification gold case | The 1% international same-store-sales percent BINDS with no stolen basis (gold is clear — abstention NOT acceptable) | Phase 6 zero-wrong certification |
| 'while' recall return | Review Record Batch-B order (test_28-r2/test_36 planned flips) | Route A structure (tagged) + certified reader (prose) | Formerly-correct 'while'-adjacent binds STILL BIND; only genuinely ambiguous golds abstain, each with a recorded reason | M2 dispositions + Phase 6 |
| Leading 'Q/Q' walk mutilation (deferred Batch-B) | Review Record deferred-items list; `_YOY_W/_SEQ_W` walk interaction | Retired with the label-walk machinery; Q/Q stays a verifier print/phrase form | Q/Q prints still recognized mechanically; previously-correct binds preserved; no walk exists to mutilate | Phase-1 shadow (zero wrong accepts) |
| R2 time law (old Batch C) | Review Record Batch-C order; FinalPlan §5 Route C | Route C contract: prove the stated period from source-native evidence or the route is CUT | No R2 emission without period proof under either outcome; formerly-correct R2 binds preserved via Route A/C/reader | M2 keep-or-cut gate + Phase 6 |
| pp×100 (was: pending one verified real pair) | Review Record round-4 scale law (pp RAW-only) | Retired from code — the element declares scale; prose pp forms stay RAW-only in verifier form families | Zero behavior change (never enabled); zero pinned-case dependence | M2 shadow confirms zero dependence |

Route-A implementation detail remains contracted in the Design doc ROUND-14 §§1–2 and
§6 (PIT law) — incorporated here by reference; those sections carry no execution
sequence of their own.

---

## 17. Compatibility crosswalk — locked law explicitly UNCHANGED by this plan

- **ChannelContract fetch-only raw packet:** unchanged. Graph/element IDs and semantic
  Unit/divide data are LOCATOR-INTERNAL PROOF ONLY — they never become public packet
  fields, canonical units, or derived values; no forbidden field is added.
- **PER-21:** the two approved 8-K routing authorities stand unchanged.
- **Runtime order:** 8-K → transcript → later 10-Q/K, public-time ordered, no future
  evidence leakage (this plan §7).
- **Core ownership:** naming, measurement, canonical units, identity, and ALL graph
  writes remain Core's; Phase 5 requests only the two locked narrow gates.
- **WP1 baseline:** untouched; the final WP1 byte comparison remains a required gate.
- **Protected gates:** 150-case live gate (fixture d7d2f068…), 28 floors, boundary hash
  81eca0aa…, full battery — all retained as §12 gates.
- **News:** a separate channel; Fiscal gains no news retrieval or meaning rules.

---

## 18. Phase-1 closeout notes (2026-07-22 — narrowly scoped; owner-approved)

- **`xbrl.source_evidence` (APPROVED, optional):** Route-A items may carry
  `{representation_sha256, quote_span, raw_label_span, pieces: [{kind: header|section,
  text, span}]}` inside the item's `xbrl` block. Every span reproduces the hash-pinned
  visible-text representation exactly; the quote text is never duplicated into
  `pieces`. **`period_evidence` remains a STRING** (an exact source slice; downstream
  substring consumers unchanged).
- **Phase-3 obligation:** move exact-Decimal serialization into THE one shared packet
  writer (during the already-required WP1 byte comparison) and DELETE the temporary
  test-only helper `route_a_source.write_packets_jsonl/read_packets_jsonl`.
