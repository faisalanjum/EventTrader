> ⛔ **SUPERSEDED-FOR-EXECUTION (2026-07-21):** The locked `UniversalLocator_Design_2026-07-18.md` is the BASE contract; `UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md` is the SOLE current execution amendment/work order (Phase 0-7; Batch B/C/D FROZEN). Reading order: locked Design v5.5 base (unchanged rules) -> FinalPlan (changes + current steps) -> Review Record (history). This file is history/evidence only — follow no execution instruction in it.

# Universal Locator - Codex Review Handoff - 2026-07-20

> **Status: NON-AUTHORITATIVE CODEX RESUME SNAPSHOT.**
> This file exists only so a compacted or fresh Codex session can recover the whole
> Driver/Fiscal review state without relying on chat memory. It never overrides owner
> instructions, `AGENTS.md`, the locked Fiscal design, the approved WP2 plan, the append-only
> Fiscal review record, Core law, committed code, tests, or fresh repository evidence.
> If anything conflicts, re-read the authorities and current code, then correct this snapshot.

## 1. First actions after compaction

Do these before answering or changing anything:

1. Read `/home/faisal/EventMarketDB/AGENTS.md`.
2. Read this entire file.
3. Read, in this order:
   - `.claude/plans/Drivers/WIP/UniversalLocator_Design_2026-07-18.md`
   - `.claude/plans/Drivers/WIP/UniversalLocator_WP2_Plan_2026-07-19.md`
   - the tail of `.claude/plans/Drivers/WIP/UniversalLocator_ReviewRecord_2026-07-18.md`
   - current `git log`, `git status`, relevant diffs, code, and tests
4. Treat the newest user message as the active instruction.
5. Recheck all state claims from the live tree. Do not assume the commit/hash/state recorded
   here is still current.

## 2. Active owner instruction

**Focus only on Fiscal.ai now. Core is paused so the two tracks do not become confused.**

Until the owner explicitly changes this:

- Audit Fiscal's current WP2 corrective only.
- Do not ask Core to commit, run R8, or push.
- Do not edit Core files.
- Do not combine Core and Fiscal review messages.
- When Fiscal returns, inspect the actual commit/diff and reproduce every material claim.
- Do not rubber-stamp a green test count.

The last instruction sent to Fiscal was:

> GO with the corrective only. Follow the exact-unit guards and preserve all 130 correct
> cases. If none drop, finish independently and report back; otherwise stop. Do not build
> routes, regenerate, touch Core files, or push.

The fuller corrective guard sent to Fiscal was:

> The gate must prove exactly one target Fact, the correct accession, one nonblank raw unit
> ID, exactly one Unit link, and matching semantic unit/divide fields. When an exact raw unit
> ID exists, it is authoritative and cannot be vetoed by a broad money/non-money guess.
> Apply that guess only when no exact ID exists; opaque IDs must abstain, never be guessed.
> Preserve the old 130 correct cases by `(pair_key, target.fact_id)`. RED tests first.

**Pending communication state at this snapshot:** the exact-unit precedence/`Unit12` guard
was sent. The later independent audit found two additional proof details that may not yet
have reached Fiscal:

1. Graph `Fact.value` strings may contain commas (for example `200,000`), so they cannot be
   passed directly to `XN.dec`; avoid using them or normalize only inside one pinned graph
   truth assertion, never by silently broadening the production exact-number parser.
2. The chosen 150 cases are all semantic plain USD and do not exercise the real PSEG/EOG
   compound-unit case collision. Preserve the exact read-only query/output and add a focused
   RED matcher pin for that class.

After resume, inspect Fiscal's latest message/code first. If these details are not already
implemented and proven, send them before accepting the corrective.

## 3. Owner's goals and operating requirements

The goal is one dependable, automatic path from evidence to Core-ready raw facts:

```text
(period-free Driver anchor, one stored source, optional untrusted hints)
    -> zero or more source-proven raw items
    -> or an honest no_proven_match
```

Required qualities:

- Aim for 100% measured precision and 100% recall where evidence makes both possible.
- Precision is the hard deterministic release priority: never keep a questionable link to
  inflate recall.
- Push recall as high as safely possible before paying reader/LLM tokens.
- Honest abstentions remain available to the later reader; they are not silent losses.
- Measure precision and recall with truthful denominators. Zero observed errors is a release
  bar, not mathematical proof of zero future error.
- Maximize useful XBRL links, including for evidence originating in 8-Ks and transcripts,
  through safe source chaining when the source itself has no XBRL.
- No human decisions during normal operation. Human involvement is only for explicit owner
  gates: a certified baseline loss, a locked-design change, prompt/token approval, push,
  production activation, or any Neo4j write.
- No over-engineering. Use the smallest solution that fully handles observed and likely
  cases. No speculative frameworks, registries, abbreviation lists, fuzzy matchers, copied
  resolvers, new ledgers, or hypothetical edge-case machinery.
- TDD for behavior changes: reproduce RED, make the smallest fix, run focused and regression
  gates.
- For graph-dependent claims, run read-only Neo4j queries. Synthetic fixtures supplement,
  but never replace, live evidence.
- Neo4j writes always require explicit owner approval.
- Avoid unnecessary full regenerations. Run the expensive clean WP1 byte proof only when the
  final diff touches a WP1-reachable path or another required gate says it is necessary.
- User-facing explanations must be plain, short, and understandable without project history.

## 4. Responsibility boundary

### Fiscal owns

- The Universal Locator design, WP plans, review record, source recipes, locator code, and
  Fiscal adapters.
- Finding, fetching, and packaging source-faithful evidence.
- WP2: anchor rebuild and neutral one-source locator.
- WP3: manual source loop/adapters across 10-K/Q, amendments, complete 8-K accessions, and
  Transcript nodes.
- WP4: neutral reader request/result schema, owner-approved prompt, independent
  certification, and token-cost reporting.
- Read-only graph use for this work.

Fiscal does **not** own:

- Core law files.
- Final Driver identity, final fact period, canonical units, kernel admission, storage, or
  Neo4j writes.
- A new historical/live fiscal resolver.

### Core owns

- `.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md`
- `.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md`
- `.claude/plans/Drivers/FinalDesign/ChannelContract.md`
- `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md`
- `driver/core/`, the decomposer, identity/period/unit law, validators, kernel, writer,
  production runtime, and the only eventual Neo4j pen.
- PER-21 law, the Core-owned law commit, and the R8 reader certification.

### Neutral shared area

- `driver/relocation/` is channel-neutral.
- Fiscal is currently implementing the neutral locator there under the locked design.
- It must import zero Fiscal/channel code.
- Adapters may depend on the neutral locator; the neutral locator may not depend on them.

## 5. Locked architecture decisions and why

### 5.1 Source routing and periods

There are exactly two earnings 8-K authorities:

1. **Historical/backfill:** when the target 10-Q/10-K already exists, use the structured
   matcher in
   `.claude/skills/earnings-orchestrator/scripts/get_quarterly_filings.py`.
   `scripts/earnings/quarter_identity.py` contributes only its `AUTO_OK` trust check.
2. **Live:** before the target 10-Q/10-K exists, use
   `scripts/earnings/quarter_identity.py` alone.

Why:

- Historical work can match two documents that both exist; it need not predict a fiscal
  label.
- Fiscal labels and projected dates differ across companies and caused real wrong matches.
- Live work has no periodic filing to pair yet, so the live resolver is the only available
  answer.
- If historical matching fails, the item parks. It never falls through to the live predictor,
  because that would turn known historical uncertainty into a guessed match.
- No third matcher, fiscal-label join, projected-date join, filing-sequence substitute, or
  copied implementation is allowed.
- This routing decision is separate from Core resolving the fact's own exact period window.

### 5.2 Anchor

- The locator anchor is period-free.
- It carries stable Company/Driver/type/slice/measurement/unit/time identity and
  non-authoritative search wording.
- It is rebuilt on demand; no recipe registry is stored.
- Birth quotes are the primary wording. The stored fact quote is fallback only.
- One active ConceptResolution may supply a prior stored concept identifier for retrieval
  only.
- Prior XBRL axis/member pairs are never reused. Every new target source proves its own full
  address.
- Numeric status is derived from the five stored value fields; zero counts as numeric.
- Numeric facts require a real unit. A genuinely numberless fact requires all five fields
  explicitly present as `None` and `series_unit=None`.
- Corrupt/missing identity data fails closed with the smallest missing field named.

Why: the anchor is a search key, not copied truth. Period and dimensions are source-specific
and must be proven again.

### 5.3 XBRL identity and ambiguity

An XBRL identity is:

```text
exact concept identifier as stored in this source
+ complete (axis, member) pairs
+ exact period/time shape
+ exact filing-local raw unitRef
```

- A full qname remains full.
- A bare stored local name remains bare and is never promoted into a namespace.
- A prefixed clue may retrieve a bare stored name only on the route that then proves it from
  current-source text; this is retrieval, never identity proof.
- Any difference across concept, any axis/member pair, period/time shape, or unit means a
  different identity.
- Equal numeric values do not make different identities equivalent.
- Ties across identities abstain.
- Alphabetical/lexicographic selection is forbidden; ordering proves nothing.
- Total ordering is allowed only to make duplicate representations of the **same proven
  identity** deterministic.

Why: real filings repeat equal values under different segments, periods, concepts, and units.
Guessing among them creates silent false links.

### 5.4 Evidence and printed values

- Every emitted value must literally appear in its own quote.
- The quote must be an exact slice of the stored source.
- Context must come from the same occurrence in the same source.
- If equal value/label occurrences have distinct source signatures or distinct contexts, the
  deterministic path abstains.
- Exact-cell evidence can disambiguate a printed 10-K/Q table cell.
- Text-only 8-Ks and transcripts have no XBRL cell. They may emit text-proven items without
  XBRL context and can later chain to a related periodic filing for an XBRL identity.
- A text-only source must never emit `dimensions=[]`; that value asserts a real XBRL fact was
  checked and found undimensioned.

Why: number equality alone is common and unsafe. The saved evidence must prove the precise
source occurrence.

### 5.5 Reader and tokens

- Deterministic routes run first.
- The later semantic reader is WP4 and remains off.
- Reuse existing batch execution and verification machinery.
- The neutral anchor+source reader schema and its prompt are new artifacts.
- Prompt writing, model, fixtures, budget, and activation require separate owner approval.
- No new deterministic matcher is built merely to avoid the reader; reconsider only if
  measured WP4 recall or token cost proves one necessary.

Why: maximize free exact recovery without building endless brittle rules, then spend tokens
only on real residual meaning.

### 5.6 Other parked owner decisions

- Driver financial/non-financial classification: no stored field now. Derive exact
  observables such as company-specific XBRL linkage and monetary units. Revisit before the
  first production Driver only if a named consumer and testable definition exist.
- Measure the real XBRL-link rate for generic LLM-found drivers, especially transcripts and
  8-Ks, when WP2/WP3 makes that measurement meaningful.
- Direct XBRL exists mainly in 10-K/Q. Transcripts and text-only 8-Ks use printed evidence
  and may chain to the related periodic filing; this chaining belongs in WP2-WP3 and must be
  tested, not assumed.

## 6. Work-package map

```text
WP1 exactness + historical corpus correction    CLOSED and pushed
WP2 anchor + one-source neutral locator          IN PROGRESS
WP3 source loop and real adapters                NOT STARTED
WP4 reader + independent certification           NOT STARTED
```

WP3 and WP4 are not hidden inside WP2.

Broad Core S4 integration later needs stable real packets from Fiscal WP3. Core law closure
does not depend on WP2, but the owner has currently paused Core to keep focus on Fiscal.

## 7. WP1 frozen closure

- `origin/main` is `80bae52`.
- WP1 is closed and pushed.
- Final WP1 closure facts:
  - 183 emitted source records covering 170 raw items.
  - 13 items intentionally have both a filing record and an 8-K record.
  - T1 XBRL records: 76.
  - T2 text records: 107.
  - 8-K records: 40, included inside T2 rather than added on top.
  - residual: 499.
  - abstain: 997.
  - parks: 2.
  - battery: 149/149.
  - certified floors: 28/28.
  - verifier CHECK green.
- The ISO-code deletion cost zero cohort links.
- The final -11 was 11 AAL 8-K repeated-occurrence demotions, not the ISO deletion.
- Two AFL records upgraded from text to XBRL through dotted-initial handling.
- Old inflated counts were not preserved when their evidence was unsafe; demotions remain
  available to the reader.

Do not reopen WP1 casually. A WP1-reachable code change triggers the approved scratch-run
byte comparison before acceptance.

## 8. WP2 state at this snapshot

Snapshot taken 2026-07-20:

- Branch: `main`.
- `origin/main`: `80bae52`.
- Local `HEAD`: `814a15a`.
- Local branch is 11 Fiscal WP2 commits ahead of origin.
- No Fiscal corrective code after `814a15a` existed at snapshot time.
- Fiscal's latest reconciliation and corrective plan are appended to the review record as an
  **uncommitted** working-tree change.
- The intentional neutral-boundary RED test exists untracked and must remain uncommitted until
  the routes make it green.

Completed:

- WP2 Step 1 production `rebuild_anchor()` closed.
- Probe reached 26/26 at Step 1 close.
- Neutral `seg_parse` move completed and a full WP1 scratch comparison proved seven content
  outputs byte-identical; summary differed only by tag/folder text.
- Pair-complete matcher infrastructure exists.
- The durable gate currently selects 150 fixed seed-7 cases.

Current committed baseline at `814a15a`:

- focused matcher/dispatch/live-gate check: 21 passed in the latest independent rerun.
- broader battery previously: 171/171.
- certified floors: 28/28.
- live gate: 130 ok / 20 abstain / 0 wrong.
- boundary: intentionally RED because real R1/R2 `locator.locate()` routes do not exist yet.

Important: these green numbers do not certify the current matcher. `814a15a` contains known
unit, dispatch, validation, and gate defects described below.

## 9. Exact live evidence for the current corrective

Independent read-only checks reproduced:

- Fixed seed-7 set:
  - 150 unique `pair_key` values.
  - 150 unique target `Fact.id` values.
  - 144 target accessions.
- Every target ID resolves to:
  - exactly one `Fact`;
  - the pinned accession;
  - one nonblank string `f.unit_ref`;
  - exactly one `HAS_UNIT` edge;
  - semantic Unit name `iso4217:USD`;
  - `is_divide='0'`.
- Raw IDs are filing-local and not interchangeable with semantic names:
  - 128 `usd`;
  - 12 `U_USD`;
  - 2 `USD`;
  - the remainder include generated IDs, `Unit_USD`, and one opaque `Unit12`.
- `f.unit_ref` is not `u.unit_reference`: all 150 differed in the direct check. The target
  raw request value is `f.unit_ref`; `Unit.name` is semantic verification only.
- Strip-only, case-sensitive matching with each target's exact raw ID preserves exactly
  130/20/0.
- The 20 abstentions split:
  - 19 accessions have FinancialStatementContent blobs but the target concept is absent;
  - 1 has no FinancialStatementContent blob.
  The structured target Fact exists for all 20, so do not overclaim "missing XBRL globally."
- The full proposed selection identity (concept + complete pairs + semantic unit + divide)
  leaves the stable pool at 1,399.
- `(pair_key, target.fact_id)` is unique and is the carry-over key.

### Real unit-case collision

Raw XBRL `unitRef` is case-sensitive. Case-folding merges real different units:

- 7 PSEG filings contain both:
  - `usdPerMWh` -> `iso4217:USDutr:MWh`
  - `usdPerMwh` -> `iso4217:USDpseg:mwh`
- 2 EOG filings contain the analogous MMBTU pair.
- Total: 9 filings with a real within-filing case-only raw-ID collision.

Fiscal initially searched only FinancialStatementContent blobs, found zero, and incorrectly
claimed zero in the entire graph. The structured `(Fact)-[:HAS_UNIT]->(Unit)` layer proves the
claim. Fiscal withdrew the rejection and recorded the surface-scoping error.

Why the decision: XBRL/XML raw unit IDs are case-sensitive by specification, and live data
shows that case can distinguish meaning. Therefore identity normalization is `strip()` only,
never case-folding.

## 10. Current corrective - required narrow TDD packet

Fiscal is authorized to implement only this packet.

1. **Raw unit identity**
   - Replace case-folding with strip-only identity.
   - Reverse/delete the synthetic `U_USD == u_usd` assumption.
   - Add a RED case-sensitive collision test.
   - Stored numeric candidates require a nonblank string unit.
   - Malformed/unitless numeric candidates abstain cleanly.

2. **Exact target graph proof in the 150-case gate**
   - Fetch each exact target `Fact.id`.
   - Assert exactly one Fact.
   - Assert the pinned accession.
   - Assert one nonblank raw `f.unit_ref`.
   - Assert exactly one `HAS_UNIT` edge.
   - Assert semantic Unit name and divide flag match the committed truth.
   - Pass the target-local raw `f.unit_ref` to the matcher.
   - Never substitute semantic `Unit.name` for raw `unitRef`.

3. **Exact-unit precedence**
   - If exact `unit_ref` is supplied, it is authoritative.
   - `expected_unit` must not veto it.
   - Apply the broad expected money/non-money hint only when exact `unit_ref` is absent.
   - Local case-folding may classify recognizable text for that coarse hint, but must never
     change identity.
   - An opaque ID such as `Unit12` cannot safely be classified as money or nonmoney and must
     abstain when only the broad hint is available.
   - Add the live/synthetic `Unit12` precedence pin.
   - Do not build a unit registry or semantic resolver in the neutral matcher.

   Reproduced bug:
   - exact `unit_ref='Unit12'` returns the correct 93,100,000;
   - adding `expected_unit='money'` incorrectly returns no candidate;
   - the same opaque ID can be incorrectly accepted as nonmoney.

4. **Carry over the certified rows before re-keying**
   - Record each old verdict by `(pair_key, target.fact_id)`.
   - Preserve all old 130 ok rows.
   - Zero wrong.
   - Any old ok -> abstain/wrong stops before fixture rewriting and returns the keyed list to
     the owner.

5. **Selection and exact values**
   - Selection identity = exact concept + full axis/member pairs + semantic unit + divide.
   - Use `XN.dec` directly on committed-pool `target.value_raw` and FinancialStatementContent
     values.
   - Do not launder floats or containers through `str()`.
   - Graph `Fact.value` is formatted in live data (for example `200,000`); direct
     `XN.dec(graph f.value)` fails. Either avoid using graph value or apply one explicit,
     test-pinned graph-format normalization only for the truth assertion. Do not silently
     broaden the production exact-number parser or claim raw `XN.dec` on formatted graph
     text.

6. **Forward complete pairs**
   - `scripts/driver_seed/locate.py::locate_by_fingerprint` currently drops `req['pairs']`.
   - Forward complete pairs to the neutral matcher.

7. **One explicit dimension-address input**
   - `members=[]` plus `pairs` is still two inputs and must reject.
   - Input presence, not truthiness, decides whether it was supplied.
   - Require exactly one address mode:
     - validated `pairs` (including explicit verified-empty `[]`), or
     - legacy `members`.
   - Neither/both must not silently become dimensionless.
   - Validate list/tuple containers, pair shapes, nonblank unpadded strings, no duplicate
     pairs, and one member per axis.
   - Malformed or repeated axes abstain with a stable reason, never crash or collapse.

8. **Stored period validation**
   - Truthy string/int/list period containers currently crash.
   - Require a Mapping.
   - Require exactly one legal instant or duration shape.
   - Validate dates through `XN.period_key`.
   - Mixed, blank, partial, impossible, or malformed shapes abstain with a stable reason.

9. **Honest gate reasons**
   - Reconcile all 150.
   - Separate the 19 concept-missing-in-present-blob cases from the 1 missing-blob case.
   - Do not label every abstention generic `no_candidate`.
   - Keep reason logic small; no framework.

10. **Stale text and future route pin**
    - Fix `xbrl_lane` text that still describes deleted `discover_pairings`.
    - Fix `locate.py`'s dead oracle-cycle comment.
    - Record prefixed-clue -> bare-storage as retrieval-only and add its real route test when
      routes are built.

11. **Case-collision proof must be durable**
    - The 150 selected cases are all semantic plain USD and do not themselves exercise the
      PSEG/EOG compound-unit collision.
    - Add a focused case-sensitive matcher RED test.
    - Preserve the exact read-only evidence query/command or captured output in the review
      record/evidence.
    - Do not rely on prose alone.

No extra abstraction is justified. These are direct guards on existing inputs and the
existing gate.

## 11. Stop conditions for Fiscal

Fiscal must stop and return to the owner/reviewer before acceptance if:

- any of the old 130 ok cases becomes abstain or wrong;
- any wrong result appears;
- any of the 150 target Fact/raw-unit/Unit-edge/accession proofs is non-unique or false;
- the fixed 150 selection changes unexpectedly;
- the stable pool changes unexpectedly;
- a certified floor drops;
- a WP1 output changes;
- the correction changes locked design D1-D14;
- the work would require a new registry/list/fuzzy matcher/framework;
- a prompt, reader token spend, Neo4j write, production activation, commit/push permission, or
  Core file change is needed.

Allowed during this packet:

- RED tests for the reproduced defects.
- Small direct matcher, gate, dispatch, test, and stale-comment fixes.
- Read-only Neo4j verification.
- Focused tests, live 150 gate, battery, and 28 regression floors.
- A narrow corrective commit only after green, if already covered by the owner's current
  execution instruction; push remains forbidden.

Forbidden during this packet:

- R1/R2 routes.
- Quote-helper relocation.
- Regeneration.
- WP3/WP4 work.
- Core files.
- Neo4j writes.
- Push.

## 12. Fiscal next steps after this corrective is independently accepted

Only after the corrective commit is audited and accepted:

1. Move the smallest complete quote-proof helper group to the neutral side in one move.
2. Build neutral R1 own-source enumeration.
3. Build neutral R2 known-value/structural matching.
4. Add the transcript-shaped neutral payload fixture. It proves source-type neutrality but
   does not fetch real Transcript nodes; real Transcript integration is WP3.
5. Turn the real-call boundary test green and prove zero Fiscal/channel modules load.
6. Pass the full 150-case gate.
7. Pass real-source done bars:
   - one real XBRL 10-K/Q with a complete emitted item;
   - one real text-only 8-K with a complete emitted item and no XBRL context;
   - one honest `no_proven_match` negative.
8. Decide regeneration from the complete final WP2 diff.
9. If any WP1-reachable file changed, run one final WP1 scratch byte comparison.
10. Run the acronym census only (B2B/SaaS and EMEA/NAA classes). Count/examples only; no
    abbreviation list or code unless measured evidence and owner review later justify it.

Then WP2 can close. WP3 source loop follows. WP4 reader remains a separate owner-approved
package.

## 13. Core context - preserved but PAUSED

This section exists so the full project state survives compaction. Do not act on it while the
owner's Fiscal-only instruction is active.

### 13.1 What Core was preparing

Core independently reviewed the owner-ratified PER-21 wording:

- two authorities only;
- historical exact-accession pairing through `get_quarterly_filings.py`;
- `quarter_identity.py` only as historical `AUTO_OK` trust check;
- live `quarter_identity.py` alone;
- fiscal labels/projected dates banned as historical join keys;
- no third matcher;
- missing/ambiguous evidence parks.

Core also carries the owner-approved financial-classification status note: no stored field
now; revisit only with a named consumer and testable definition before first production
Driver creation.

### 13.2 Current Core working-tree snapshot

At this snapshot, Core changes are uncommitted and nothing is staged. Relevant modified files:

- `.claude/plans/Drivers/DriverDesign.html`
- `.claude/plans/Drivers/FinalDesign/BUILD_AND_OPERATIONS.md`
- `.claude/plans/Drivers/FinalDesign/ChannelContract.md`
- `.claude/plans/Drivers/FinalDesign/FINAL_DESIGN.md`
- `.claude/plans/Drivers/FinalDesign/STATUS_AND_HISTORY.md`
- `.claude/plans/Drivers/test_driver_design_coverage.py`
- `.claude/plans/Drivers/workflows/tests/test_rulebook_sync.py`

Core's earlier two coverage failures were:

- PER-21 absent from `DriverDesign.html`;
- coverage expected 42 supersession rows while STATUS contains 43.

Those two working-tree fixes now pass:

```text
test_driver_design_coverage.py + test_rulebook_sync.py = 15 passed
```

The new rulebook sync test alone was 6/6.

Core's independently reproduced broader suite claims:

- Core combined: 402 passed + 1 opt-in write-probe skip.
- The combined count is 392 unit tests + 10 live-read tests.
- Track A: 266 passed + 1 skip.
- live read-only: 10/10.

Remaining Core truthfulness work at snapshot time:

- The passing coverage test recognizes only Q1-Q5 and R6-R8. It is blind to R9-R13.
- `DriverDesign.html` does not properly cover R9-R13.
- Its footer totals are stale:
  - 71 rule IDs should reflect the current 72;
  - 42 reversals should be 43;
  - 8 rulings should be 13.
- STATUS still says Track A `265+1` in two places while the current suite is `266+1`.
- BUILD also retains the historical/currently misleading `265+1` count where the present
  status needs reconciliation.
- R13 still says the R8 "has not run yet." That sentence would become false immediately after
  R8. Before the law freeze it must be rewritten as snapshot-stable wording whose completion
  is owned by the later append-only R8 record.
- The new PER-21 sync test is not sufficient yet. It checks paths and a few phrases but does
  not fully pin:
  - the historical `AUTO_OK` trust requirement;
  - historical failure -> PARK with no live fallback;
  - source routing as separate from the fact's own period resolution.
- The old ten-question reader prompt does not explicitly ask the reader to recover PER-21.
  Its 8-K example does not state whether the route is historical or live, and a reader can
  answer it without explaining source routing. A paid R8 that never asks about PER-21 does
  not certify PER-21.
- Re-run every listed gate after those edits.

### 13.3 Core commit and R8 sequence when the owner later unpauses it

Required sequence:

1. Fix every Core defect above.
2. Re-run every gate.
3. Commit the four FinalDesign law files as one clean Core-owned law snapshot.
4. Commit the study-page/sync/coverage guards separately if preserving law-commit purity.
5. Run the blank-context R8 from a clean detached worktree at the **final committed
   certification SHA that includes the guards**, not at an earlier partial commit.
6. Require the reader to recover:
   - the historical route;
   - the live route;
   - failure parking with no fallback;
   - source routing as distinct from fact-period resolution.
7. Add the R8 record afterward without changing the seven tested files.
8. Push only on a later explicit owner word.

Standing R8 requirements:

- owner approves token spend first;
- estimated 250k-400k reader tokens (prior comparable actual about 236,676);
- one committed seven-file freeze;
- detached/clean snapshot;
- 10/10 reader questions;
- 7/7 exact pre-pinned and post-verified hashes;
- explicit command exit checks;
- definitive record names the freeze SHA;
- record is a separate append-only commit;
- the seven tested files are not changed after the run.
- first reader answer only; no repair conversation;
- the exact prompt/question set must make PER-21 testable rather than relying on incidental
  mention of an 8-K.

The seven reader files are:

- `FINAL_DESIGN.md`
- `ChannelContract.md`
- `BUILD_AND_OPERATIONS.md`
- `STATUS_AND_HISTORY.md`
- `15_CandidateFactPacket.md`
- `FableExperimentPlan.md`
- `FableExperimentWorkOrder.md`

Reference procedure:

`.claude/plans/Drivers/FinalDesign/archive/2026-07-15_pre-consolidation/READER_TEST_RECORD_2026-07-17_R8-recheck-R12.md`

### 13.4 Shared-branch risk

Local `main` already contains 11 unpushed Fiscal WP2 commits below any future Core commit.
A normal Core push would therefore publish unfinished Fiscal WP2 too.

Consequences:

- Core must not push independently.
- Do not give one combined "commit + R8 + push" GO.
- Core commit, R8 spend, record, and push are separate decisions.
- The simplest safe sequence after Fiscal focus ends is:
  1. reach a clean Fiscal pause;
  2. finish Core's small truthfulness fixes;
  3. owner approves Core law commit/R8;
  4. run and audit R8;
  5. resume/finish Fiscal WP2;
  6. owner approves the intended combined push only after all included commits are accepted.
- A separate worktree/cherry-pick route could isolate Core, but it is unnecessary complexity
  unless the owner explicitly requires a Core-only push.

### 13.5 Core work after Fiscal WP3

Core law closure does not depend on WP2. Broad Core S4 implementation does depend on stable
real Fiscal packets:

- shared decomposer;
- kernel admission/reuse/create/park;
- final Driver identity;
- exact fact period and units;
- `create_driver`;
- `backfill_candidate_driver_name` single-candidate handoff;
- first-accepted-fact -> backfill trigger;
- new-source -> relocate trigger;
- validators, writer, runtime, and eventual production activation.

Core is the only eventual graph-writing authority. Writes remain disabled and always require
explicit owner approval.

## 14. Dirty-worktree safety

The repository has many unrelated modified, deleted, and untracked files from other sessions.
Never:

- reset, restore, delete, stage, commit, or push unrelated changes;
- assume a dirty file belongs to this task;
- use destructive Git commands;
- include another owner's files in a commit.

Always:

- inspect exact path-scoped diffs;
- stage by exact path;
- verify the staged file list and staged diff;
- re-read the latest tree before acting because Fiscal/Core may be working concurrently.

Known unrelated dirty Fiscal-area files at the snapshot:

- `scripts/driver_seed/relocate_probe/codex_reader.py`
- `scripts/driver_seed/relocate_probe/relocate_batch.js`

Do not attribute or modify them without evidence.

## 15. How to audit Fiscal's next return

Do not accept the bot's summary alone. In order:

1. Confirm the newest commit and exact file list.
2. Read the complete diff and the surrounding production paths.
3. Confirm RED tests existed for every behavior change.
4. Reproduce the important cases directly:
   - case-sensitive raw unit collision;
   - exact-unit precedence over `expected_unit`;
   - opaque `Unit12`;
   - unitless/malformed numeric fact;
   - exact 150 target Fact/accession/raw-unit/one-Unit-edge proof;
   - all 130 prior ok rows carried by `(pair_key, target.fact_id)`;
   - pair forwarding;
   - neither/both dimension-address inputs;
   - malformed/repeated pairs;
   - malformed period containers and date shapes;
   - 19/1 honest abstention reasons.
5. Run the focused matcher/dispatch tests.
6. Run the live 150 gate. Graph unavailability may skip only for genuine unavailability;
   auth/config/query/missing pinned evidence must fail.
7. Run the full battery and 28 certified floors.
8. Check test counts before/after; test deletion is a known prior failure class.
9. Check stale claims/comments by grep.
10. Confirm no route, quote move, regeneration, Core file, graph write, or push entered the
    packet.
11. If any claim depends on Neo4j, run the read-only query independently.
12. Report findings first. Only say "accepted" if no material issue remains.

## 16. Snapshot hashes and commands

These hashes identify this handoff's observed files only. Recompute after resume:

```text
0b1525081ba4bc832e06a1df87a9ac9c226b9c815a60add20e838853e11a2159  UniversalLocator_Design_2026-07-18.md
4c25dfda31b0b1a51b03de0af942065d36bfda06af9f44c9d04a6f16db7e1417  UniversalLocator_WP2_Plan_2026-07-19.md
6b714e08a902671bedc3c32c9cf9cb1091495c22ee0131827964c9db438d5b75  UniversalLocator_ReviewRecord_2026-07-18.md
23b54fc0ffe20e90bc5db73a35073969fd11fc642906fec11895458363be687f  driver/relocation/locator.py
189083d66c6803d92ff9e444afced3fde5d253046a1d151b96e1eeaeb3c2547d  driver/relocation/test_match_facts.py
3991127300cca69c85cfd05b1b1264da6de3438de38f1324071f697d190ae225  scripts/driver_seed/locate.py
a13c41a0cfb848a2050c2261b74bb4a5953aafa54b1f08752b67c62fa66cea97  scripts/driver_seed/relocate_probe/xbrl_lane.py
a47c8dfccce72c60b6295563d778850ea631b209b9f9f4980cb4aae9c0456dc3  scripts/driver_seed/relocate_probe/test_xbrl_gate.py
d7d2f06849371a38e05d5ff781deb790c7b5250f3bae7a1c8ec85373607b2eec  scripts/driver_seed/relocate_probe/xbrl_gate_expected.json
```

Useful recovery commands:

```bash
git rev-parse --short HEAD
git status --short --branch
git log --oneline origin/main..HEAD
git diff --name-only -- driver/relocation scripts/driver_seed/locate.py \
  scripts/driver_seed/relocate_probe \
  .claude/plans/Drivers/WIP/UniversalLocator_ReviewRecord_2026-07-18.md

venv/bin/python -m pytest driver/relocation/test_match_facts.py \
  scripts/driver_seed/test_locate.py \
  scripts/driver_seed/relocate_probe/test_xbrl_gate.py -q

venv/bin/python -m pytest \
  .claude/plans/Drivers/test_driver_design_coverage.py \
  .claude/plans/Drivers/workflows/tests/test_rulebook_sync.py -q
```

Do not blindly run a full regeneration on resume. First inspect what actually changed.

## 17. Truthfulness reminders

- "Green" is scoped to the exact tests run.
- A correct measurement on one graph surface does not justify a claim about the whole graph.
- Raw XBRL IDs and semantic Unit names are different fields.
- A gate can pass counts while selecting different rows; preserve stable row identity.
- Saved-output regrading is not a before/after matcher run.
- Truncated command output or shell exit zero is not proof that an inner gate passed.
- A test inside `if __name__ == '__main__'` is not collected by pytest unless explicitly
  wrapped.
- Test-file surgery must preserve test counts; compare before/after.
- No alphabetical tie-break can prove identity.
- Conservative abstention is correct only when the rejected row remains visible downstream
  and recall is measured honestly.

## 18. Post-snapshot event: Fiscal corrective `47b2ecf`

Fiscal committed the corrective after the earlier parts of this handoff were written.
Live Git state observed on 2026-07-20:

```text
HEAD = 47b2ecf
origin/main = 80bae52
main is 12 commits ahead
```

Commit `47b2ecf` changes exactly these eight files:

1. `.claude/plans/Drivers/WIP/UniversalLocator_ReviewRecord_2026-07-18.md`
2. `driver/relocation/locator.py`
3. `driver/relocation/test_match_facts.py`
4. `scripts/driver_seed/locate.py`
5. `scripts/driver_seed/relocate_probe/test_xbrl_gate.py`
6. `scripts/driver_seed/relocate_probe/xbrl_gate_expected.json`
7. `scripts/driver_seed/relocate_probe/xbrl_lane.py`
8. `scripts/driver_seed/test_locate.py`

The commit message claims:

- 130 prior correct cases remain correct;
- 20 prior abstentions remain abstentions;
- zero baseline losses;
- live gate 2/2;
- full battery 173/173;
- certified floors 28/28;
- no routes, quote-helper move, regeneration, Core edit, graph write, or push.

These are **Fiscal's claims, not an independent acceptance**. The first active task after
resume is a findings-first audit of the full `814a15a..47b2ecf` diff, surrounding call paths,
tests, and live graph evidence.

One material issue is already visible and must be reproduced, not assumed away:

```python
u_cf = u.casefold()
if expected_unit == 'money' and 'usd' not in u_cf:
    continue
if expected_unit == 'nonmoney' and 'usd' in u_cf:
    continue
...
if unit_ref is not None and u != req_unit:
    continue
```

In `driver/relocation/locator.py`, the broad money/non-money guess still runs before the exact
raw `unit_ref` check. Therefore an exact opaque raw ID such as `Unit12` can still be rejected
by `expected_unit='money'`, or accepted under a conflicting broad guess. The locked rule is:
**when an exact target-local raw unit ID exists, it is authoritative; the broad guess must not
veto it.** No durable `Unit12` precedence test was observed in
`driver/relocation/test_match_facts.py`. Reproduce this exact call before deciding the fix.

The audit must also verify:

- the gate independently proves the pinned accession, not only the `Fact.id` and unit edge;
- focused durable evidence covers the real PSEG/EOG case-sensitive compound-unit collision,
  rather than only a synthetic `U_USD`/`u_usd` pair;
- all 130 rows are preserved by stable `(pair_key, target.fact_id)`, not aggregate counts;
- the new abstention reasons are exact and the 19/1 split is real;
- malformed inputs abstain cleanly on every production path;
- no tests disappeared and no stale claims remain.

Do not edit the corrective until the owner asks for a fix after the audit. Do not resume Core,
run R8, push, or perform any Neo4j write.

*End of non-authoritative resume snapshot.*
