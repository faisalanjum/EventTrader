# Universal Locator — Review Record (companion to the v5.3 operative design)

History + verdict evidence moved out of the operative doc per round-2 hygiene cut. Append-only.

## Round 1 (ChatGPT, 2026-07-18) — summary
14 accepted (incl. 2 precision bugs I reproduced live: `value_ok(2.34,'%','…2%')`→True;
`value_ok(86,'number','…86%')`→True; plus my own find: `tier1` L353 int-rounds decimals before
matching) · 4 modified (token-verbatim; split-early/move-late; 8-K fail-closed compose;
rounded-%→LLM) · 3 rejected with grounds. Full v3 table lived in the v3 doc (git history of the
design file). Baselines run live that day: regress 28/28 PASS; RED tests 3-fail/5-pass as expected.

## Round 2 (ChatGPT, 2026-07-18) — full verdicts

| # | Reviewer point | Verdict | Evidence / grounds |
|---|---|---|---|
| 1 | Locator belongs in shared `driver/relocation`; Fiscal supplies recipes+sources | **ACCEPT** (already the design's ownership); refinement adopted from `driver/README.md`: *existing* WIP migrates AT THE END, *new* modules are born in `driver/relocation/` | README read this session |
| 2 | "Every field optional" unsafe; require one complete identity; bare number rejected | **MODIFY**: minimum-complete-identity adopted; XBRL address completeness (+unit) adopted — it is already the engine's behavior (`xbrl_lane` exact member-set match) and unit is always known at birth. Text address: wording required + anchors-when-present, NOT the reviewer's mandatory caption+measurement+unit set — that would invalidate qualitative metrics (no unit) and prose metrics (no caption). Bare-number rejection = the owner's existing D5 abstain, same behavior, naming aligned. | DU-05 (qualitative metrics); xbrl_lane.py L41 |
| 3 | Process sources independently; no filing↔8-K pairing for acceptance; quarter_identity never proves acceptance | **MODIFY**: independence + acceptance-from-own-evidence adopted (it's D8's shape; pairing was only ever routing). quarter_identity demoted to candidate-narrowing/corroboration — but not banned: composed failure (0.24% label error × same-value-same-label coincidence in the wrong PR) is far below any measurable bar, and the free audit (window vs labels) decides whether to wire it at all. | quarter_identity.py benchmarks block |
| 4 | Amendments: never choose; both are events | **ACCEPT** — strictly simpler than the round-1 "defer a selection rule": there is no rule. Matches 15 D.2 (same value, two sources = two records). | |
| 5 | One exact Decimal utility + one date decoder; "certified code cannot be frozen unchanged" | **ACCEPT** — rounding defects verified (tier1 L353/L373; xbrl_lane L45; value_forms). D4 reworded: "reuse proven behavior and tests; replace demonstrated faulty code." | reproduced this session |
| 6 | Cut "rounded value → LLM decides"; output must be the printed number or abstain | **ACCEPT as restatement** (owner flag F2): ChannelContract L34/L41 already mandates only source-stated values enter. Vendor number = search hint only. The earlier owner confirm ("LLM judges") survives as: residuals ride the NORMAL reader lane when approved; any emission carries the printed value; no special recovery code. | ChannelContract.md L34, L41 |
| 7 | items[] envelope; a source states quarter+YTD+instant+comparatives | **ACCEPT shape** (envelope, all current-report occurrences — a 10-Q freshly states Q AND YTD; this is what scope-differentiation implies). **Comparatives stay deferred** — owner-confirmed same day; reviewer reversal request routed to owner flag F1 with my rec to keep the deferral. | |
| 8 | Token-verbatim conflicts with the verbatim law; return untouched quote | **ACCEPT-MODIFY**: prose = raw untouched slice (drop `_tidy` from the emission path; keep transiently for search); table rows = untouched cell texts joined, disclosed `quote_kind=table_row` (byte-identity to HTML is impossible for a constructed row; construction disclosed instead). | ChannelContract L63 |
| 9 | `not_stated` is unprovable by search; engine says `not_found` only | **ACCEPT** — taxonomy renamed; stated-ness decided by the cert's abstain audit. Zero cost, pure honesty. | |
| 10 | regress.py protects old cases; release evidence = frozen unseen labels | **ACCEPT** — already D3; wording sharpened (regress = necessary guardrail, never sufficient). | |
| C-A | Remove the standalone LLM-ID phase | **MODIFY**: the phase is gone; the 3-line `item_id` stamp stays in Phase A (residual format future-proofed; no LLM machinery built). | |
| C-B | Reader lane fully off until package approval | **ACCEPT** (D10, flag F3). | |
| C-C | Move history out of the operative doc | **ACCEPT** — this file exists because of it. | |
| C-D | Reword "never rewrite certified code" | **ACCEPT** (D4 reworded). | |
| Q4 | "One behavior-neutral split/move into final folders now" | **REJECT for existing code**: `driver/README.md` — "Existing WIP code migrates here AT THE END"; owner-locked; parallel core session active under `driver/`. **Adopted for new code**: new standalone modules born in `driver/relocation/` (same README, same line). | README L16 |

## Standing session facts (kept out of the operative doc)
- Live baselines 2026-07-18: `relocate_probe/regress.py` PASS 28/28 · Phase-0 RED tests 3-fail/5-pass.
- Real tier data (stale 07-15 smoke, part1): 19,469 instances → 3,066 code-resolved (57% XBRL / 43%
  text) · 2,787 residual · 13,616 not-found. Regenerate refreshes all of this.
- quarter_identity measured: warm 97.92 / 0.24 / 1.83; fail-closed classes beyond 52/53-wk (GIII ≈4.4%).
- Untouched dirty files: `relocate_probe/codex_reader.py`, `relocate_probe/relocate_batch.js`.
- Owner confirms 2026-07-18: bare-number→abstain · primary-period sweep (comparatives deferred) ·
  rounded-%→normal-residual-flow (restated per round 2, pending F2 wording confirm).

## Owner rulings on the round-2 flags (2026-07-18, later same day)
- **F1 REVERSED-ADOPTED by owner:** emit prior-year comparative columns too ("record the old columns…
  unless it breaks something or is heavy"). Verified before adopting: packet law makes the fact's own
  context authoritative (15_CandidateFactPacket.md L138 period row); the tripwires guard window-type
  mismatches, not old-year columns; engine gets SIMPLER (no primary-period filter). Residual checks:
  core-validator acceptance of period<source-period at integration + ~2-3× cert grading volume.
- **F3 CONFIRMED:** reader lane off until the owner approves one package (model+prompt+fixtures+budget).
- **F2:** pending owner confirm after re-explanation.
- **F2 CONFIRMED (owner, same day):** printed-values-only adopted with no exceptions — the saved
  number must literally appear in the quote; vendor numbers are search hints only; precision
  mismatch → not_found. All round-2 flags now resolved; v4 design CLOSED.

## Round 3 (ChatGPT, 2026-07-18) — verdicts after verification

Verified this round: `driver/core/driver_validators.py` ~L392 (value_text REJECTED outside guidance;
"producers never supply xbrl_qname — concept-link enrichment writes it") · the real abstain split
(below) · reader wrong-accepts consistent with live floors (pooled ≈171/176; transcript 4/5) ·
"Driver is global" — NO such wording found in FINAL_DESIGN (premise unverified).

**ACCEPTED (17):** value_text guidance-only resolution · stale-rate hygiene · reader = baseline w/
recorded wrong-accepts, per-stratum certification · NO stored recipe copy → temporary anchor rebuilt
from the Core-accepted fact (+ stop-and-report if rebuild fails) · ConceptResolution-only cross-source
XBRL reuse · keep unit/class matching · locator emits raw period evidence, never scope (Core resolves;
packet law L138) · table quotes = verbatim corpus slices, cell evidence = audit-only · no_proven_match
rename · transcripts in scope now per-node (restores the owner's original ask) · amendments simple ·
quarter_identity routing-only (corroboration wiring dropped) · two lifecycle triggers reusing the
existing ledger/cursor · rounded hints = retrieval-only (identical to owner F2) · four work packages ·
ChannelContract-shaped items[] with no identity/scope/computed fields · numberless metrics in design
with own reader stratum.

**MODIFIED (1):** "remove request-side period pins" → the pin stays as ROUTING + ledger key ONLY in
value-known harvest mode (the vendor worklist is period-keyed); never authoritative, never emitted.

**REJECTED/CORRECTED (1):** "Driver is global" — unverified premise (no such law text); the
no-stored-copy conclusion adopted anyway on independent grounds (no drift, zero new storage, all
anchor components already stored on the fact/edges).

**MY OWN ERROR, owned:** v4's "~70% of vendor rows found in no searched source" was materially wrong.
True part1 composition (counted from abstain.jsonl this session):
  19,469 instances = 12,011 derived_metric (vendor-computed %Chg/CommonSize — deliberately skipped,
  not searchable) + 379 plug-skips (rule since deleted; become searchable on regenerate) +
  3,066 code-resolved + 2,787 residual + **1,226 value_absent = 6.3% searched-and-not-found**.
XBRL = 1,761/19,469 ≈ 9.0% of raw rows (57% only of code-resolved). These are the true denominators.

## Round 4 (ChatGPT, 2026-07-18) — verdicts after verification

Verified this round: FINAL_DESIGN glossary L26 — **"Driver — … A class node: name + permanent
fact_type + SAME_AS/BASE_METRIC links + birth evidence"** (their claim RIGHT; my round-3
"premise unverified" note WRONG — I grepped the word "global" instead of checking the concept;
methodology error owned) · `driver_writer.py` L34 `_LWW_FIELDS` includes **"quote"** (quote is
last-write-wins on collision — NOT immutable birth evidence) · `raw_label` absent from the write
path (not stored) · ChannelContract envelope = source_id, source_type, **ticker, fye_month,
event_time** (v5's output shape was incomplete) · glossary L39: latent base anchor = "The only
legal empty Driver node" (their directive 14 is verbatim law).

**ADOPTED (16 of 18):** runtime honesty (ledger/cursor/hook = unbuilt S4 wiring; decomposer unbuilt,
kernel OFF, writes disabled, runtime unbuilt, linker dormant, ingestion down) · Driver-class
correction · anchor rebuildability = hypothesis + WP2-first 7-stratum reconstruction test
(prove-or-stop, smallest-missing-field, never a registry) · anchor key = series identity minus
period/scope, CIK never ticker · locator input = anchor + source only (Fiscal period key moves
outside) · prior-fact value hints removed · XBRL boundaries (own-source only; qname = candidate
retrieval; cross-source OFF until linker active) · contract-exact output shape · no_proven_match
internal + clean-stamp SKIP + reopen triggers · amendments as 10k/10q + oldest→newest backfill ·
born-with-fact/latent-base/unknown-state-parks · cert denominators + upper error bounds + minimal
strata · rates out of the operative doc · WP3 stops at dry-run packets · numberless needs kernel
falsifier too.

**MODIFIED (1):** directive 12 (dates) — the "one proven exclusive-end decode + exact equality"
swap REJECTED with evidence: per-fact convention is undetectable (filers tag either), and the
existing convention-set equality {date, date+1d} is the PROVEN mechanism (0 wrong / 150 live
pairs, xbrl_lane self-check). Adopted the spirit: the rule is now documented exactly; no other
tolerance anywhere; exact Decimal values.

**ROUTED TO OWNER (1):** directive 17 — the PIT backfill exception (later-learned identity as a
retrieval clue against older public sources; nothing factual copied backward; honest dual
timestamps). Reviewer recommends yes; I concur; awaiting owner ruling (design §10).

**Errors of mine owned this round:** (a) round-3 Driver-global note (weak word-grep verification);
(b) v5 "existing ledger/cursor/source-arrival hook are reused" — overstated design-law as built
runtime.
- **PIT backfill ruling (owner, 2026-07-18): YES → D14.** Later-learned identity = retrieval clue
  only; the older source independently proves the entire fact; nothing copied backward; dual honest
  timestamps. All round-4 items now closed; v5.1 has zero open items.

## Round 5 (ChatGPT, 2026-07-18) — verdicts after verification

**THE "FALSE APPROVAL" CHARGE — REJECTED WITH THE TIMELINE.** The owner's PIT ruling was given
IN-SESSION to this bot ("yes", 2026-07-18, after the bitcoin-example explanation) BEFORE the round-5
message existed. The reviewer's channel had not seen that exchange and inferred fabrication from the
doc alone. No fabrication occurred; the recording was authentic. HOWEVER the reviewer's round-5
wording ADDS constraints the original ruling did not contain (Core reconfirms identity on backfilled
facts · the stored fact is excluded from historical views dated before `created` · source-time-safe
menus) — so D14 stands as approved, and the REFINED text is put back to the owner as D14-v2
(recommend yes; the additions are Core-side and consistent).

**Verified this round (ran, not read):**
- Mixed-date acceptance REPRODUCED: a fact with startDate 2024-01-01 + endDate 2025-01-01 matches an
  inclusive request 2024-01-01→2024-12-31 through the ±1-day set logic. Real hole.
- Date census over the 1,523 certified truth-pool locks: 1,477 month-end vs 46 first-of-month —
  and the 46 pattern-match retail 52/53-week fiscal calendars (e.g. ASO 2025-02-01), not a second
  convention. Supports the reviewer's live finding (57,492 raw facts inclusive): raw storage is
  uniformly inclusive; the old tolerance guarded an IMPORTED assumption ("filers tag either") never
  measured against our data.

**MY ROUND-4 DATE REJECTION — REVERSED AND OWNED (methodology lesson #3):** I defended the certified
±1-day mechanism because it was certified, without testing whether the variance it tolerates exists
in our storage. "Certified" ≠ "necessary". New rule (v5.2 §3): normalize once by known input format →
exact equality; unknown/mixed → abstain; adversarial mixed-window + neighboring-period RED cases.

**ADOPTED (8 of 9 directives):** date rule (above) · locator input = anchor + source + optional
UNTRUSTED same-source hints (fixes v5.1's internal inconsistency: route 2 needed a value the input
forbade) · invented (series×period×source) future-ledger layout DELETED (running-layer contract =
undesigned/unbuilt; the packet spec's one-line ledger row is the only defined sketch) · kernel
falsifier extended to EVERY newly admitted no-XBRL Driver (numeric or numberless; Core-side
dependency recorded) · anchor split into stable identity vs replaceable clues (LWW quote never
called immutable) · packet = all applicable point/range/floor/ceiling/comparison shape fields +
exact {axis,member} pairs + ONE packet per source event · "1,226 not-found" RELABELED "old-pipeline
value_absent label" (it includes the number-form bugs' suppressed finds; true absence unmeasured
until fresh regenerate + independent grading) · operative doc stripped to design-only (runtime
status, standing ops rules, correction tables → this record).

**MODIFIED (1):** "run the seven-case reconstruction proof before lock" — ADOPTED as a pre-lock
gate, with scheduling note: the probe uses the dry-run writer's stored-ops output + a real read-only
source + existing packets (zero tokens, zero writes); ready to run on the owner's word. (The #804
stale-smoke fixture ban governs the S4 rehearsal's certification value, not this structural
storage-sufficiency probe; a post-WP1 rerun on fresh packets is cheap if wanted.)

**Standing session facts:** regress 28/28 PASS (2026-07-18) · RED tests 3-fail/5-pass · part1
composition: 12,011 derived-skip + 379 plug-skip + 3,066 resolved + 2,787 residual + 1,226
old-pipeline-labeled value_absent (true absence unmeasured) · XBRL = 1,761/19,469 ≈ 9.0% of raw
rows (57% of code-resolved only).
- **D14-v2 CONFIRMED (owner, 2026-07-18):** the three round-5 additions adopted verbatim — Core
  reconfirms identity on backfilled facts · backfilled facts excluded from historical views dated
  before `created` · source-time-safe menus. D14 final. Remaining open item: the pre-lock
  reconstruction probe run.

## PRE-LOCK RECONSTRUCTION PROBE — RUN 2026-07-18, PASSED (owner-authorized)

Method: static half = the writer's stored-field inventory read from `driver_writer.py`
(SIGNATURE_FIELDS 10 + _LWW_FIELDS 10 + fact_scope + id/created/series_unit = the counted 24;
company/driver/source/period on edges; Driver class node carries name + fact_type per glossary L26).
Dynamic half = real part1 records, real filings fetched from the live graph (READ-ONLY), anchors
rebuilt from STORED-ONLY data (label derived as the stored quote's words before the first digit),
re-run through the actual locator vs the original vendor label as control.

| Stratum | Verdict | Evidence |
|---|---|---|
| numeric text (T2) | **PASS (dynamic)** | AA "United States Revenue": rebuilt wording "United States" → SAME quote as control |
| dimensionless XBRL | **PASS (dynamic)** | A (Agilent) T1 w/ real text quote: rebuilt wording → SAME quote as control |
| dimensioned XBRL | **PASS (identity static + text dynamic)** | identity components all in fact_scope/edges; XBRL clue at birth absent — recorded dependency (enrichment dormant), not a rebuild failure |
| numberless | **PASS (static)** | anchor-ID rebuilds from node/edges; clue = stored quote; route is reader-gated anyway (D10) |
| collision | **PASS (static)** | id + fact_scope are IMMUTABLE fields (writer's own classification); identity unaffected |
| two series, one Driver | **PASS (static)** | distinct fact_scope (slice/measurement differ) → distinct ids → distinct anchors; wording-collision risk covered because measurement flavor rides fact_scope and the derived wording comes from each series' own quote |
| replaced (LWW) quote | **PASS (reasoned)** | the surviving quote is still a genuine printed instance of the SAME series → remains a valid retrieval clue; immutability matters for audit, not search |

**Key finding:** the "raw label not stored" gap is SELF-HEALING — the stored quote's prefix IS the
filer's label (row_quote crops from the label by construction). No missing stored field. No registry.

**Bonus finding:** 571 of the old smoke's 1,761 T1 records carry the stale FABRICATED
xbrl_fact-style quotes (not just the 19 packets previously noted) → anchors must never be built
from pre-WP1 outputs; the WP1 regenerate is a hard prerequisite for anchor use (now stated in §2).

Probe scripts were throwaway in-memory runs (heredocs); no temporary files were created; nothing
to clean. Zero writes, zero tokens.

## Round 6 (ChatGPT, 2026-07-18) — responded to v5.2 BEFORE the owner's D14-v2 confirm and
## before the first probe run (partially overtaken by events; processed with full verification)

**Timeline note:** the reviewer accepted the D14 timeline correction (no fabrication).

**ADOPTED (verified):**
- `definitional_evidence.birth_quotes` EXISTS in law as immutable (BUILD §415-418 "never
  rewritten") → the anchor's PRIMARY wording source; the LWW fact-quote demotes to fallback;
  my quote-prefix trick = secondary evidence. Cleanest resolution, zero invention.
- **Probe-claim correction — MY OVERCLAIM OWNED:** "PROBED AND PROVEN" overstated. The graph
  holds ZERO Driver/fact nodes (creation paper-only), so the first probe proved stored-SCHEMA
  sufficiency + wording recoverability only — not full anchor reconstruction, not locator
  accuracy. Doc §2 rewritten; the narrow zero-write schema probe (strict id/fact_scope decoder,
  strip only period+quote_hash, exact reconstruction of CIK/name/type/slice/measurement/
  series_unit/time_type, real-vs-synthetic fixture labels, cross-company isolation) is scheduled;
  the full create_driver→rebuild→second-source proof = mandatory S4/WP2 gate.
- **created-cutoff REVERSAL (their own v2 clause retracted — and they're right):** a 2023-public
  fact belongs in a 2024 public-information backtest; source-date PIT stands; old-database-state
  reproduction = run snapshots, not view logic. Folded into D14-v3 (pending owner).
- Paper corrections all adopted: 8-K accession+exhibits = one event · ledger duties
  specified-but-unbuilt + orchestration undesigned (trigger-implementation wording removed) ·
  reader wiring = explicit WP item, no new matcher · change/delta values+units + non-XBRL stated
  period dates added to items · adapter date normalization comparison-only · hints narrowed to
  target-source label/value/period clues · redundant `found` status dropped · token-cost
  reporting (per searched item, per accepted fact, projected backfill/forward) added to WP1/WP4.
- **SHA TYPO OWNED:** my paste-back abbreviated the v5.2 sha as "…5640"; the true ending is c640
  (a3977cc85243fb86de12df1e54c85ee7d7f6dc5b9d2575d1d5fe8ca34375c640). The post-probe doc sha had
  already moved to 3e7969f5… and moves again with v5.3.

**OVERTAKEN BY EVENTS (recorded, no action):** their "probe cannot run today" arrived after an
owner-authorized probe HAD run — but their scope critique applied to it and is adopted above;
their D14-v2 approval request arrived after the owner had already confirmed v2 in-session —
superseded by v3.

## NARROW ZERO-WRITE SCHEMA PROBE — RUN 2026-07-18 (round-6 spec), 8/8 PASS
Method: ids composed by `driver/core/driver_ids.py`'s PURE functions (throwaway probe only — no
production import), decoded by an INDEPENDENT strict parser written from the §5.1 grammar
(cross-implementation round-trip); anchor = company(edge) + driver + slice + measurement +
series_unit + time_type + fact_type + birth_quotes wording; ONLY period + quote_hash stripped.

| # | Case | Fixture | Verdict |
|---|---|---|---|
| 1 | numeric text (AA) — real accession; company resolved via LIVE source→PRIMARY_FILER→Company edge (cik 0001675149) | REAL-derived | PASS |
| 2 | dimensionless XBRL | REAL-derived | PASS |
| 3 | dimensioned XBRL (Agilent segment slice) | REAL-derived | PASS |
| 4 | numberless qualitative (wording = birth_quotes) | SYNTHETIC | PASS |
| 5 | collision member — quote_hash stripped; anchor == bare sibling | SYNTHETIC | PASS |
| 6 | two series under one Driver — measurement separates | SYNTHETIC | PASS |
| 7 | replaced LWW quote — wording drawn from immutable birth_quotes | SYNTHETIC | PASS |
| 8 | cross-company isolation — same driver name, distinct company edges → distinct anchors | SYNTHETIC | PASS |

Sample id: `du:0000950170-25-024242:revenue:period=gp_2024-01-01_2024-12-31|slice=geography:united_states`
NOT proven (recorded in the design): graph-node reconstruction (zero Driver/fact nodes exist),
birth_quotes persistence on real nodes, locator accuracy from rebuilt anchors → the full
create_driver→rebuild→second-source proof = mandatory S4/WP2 gate. Zero writes, zero tokens,
throwaway in-memory script (nothing to clean).
- **D14-v3 CONFIRMED by owner 2026-07-18** (the reviewer's six-point wording verbatim; v2's
  created-cutoff clause retracted).

## Round 7 (ChatGPT, 2026-07-18) — final evidence/sync pass. ALL findings verified TRUE and fixed.

**Their findings, all confirmed against my own artifacts (owned):**
1. Doc drift — title/footer still said v5.2, status still listed D14/probe as open, "relevant
   exhibits" wording present, reader-wiring + token-cost NOT in the WP table (I had claimed
   adoption in this record without syncing the operative doc). Grep-proven, now fixed: clean
   v5.3 rewrite; stale-wording grep exits clean.
2. My probe script errors — all four real: series_unit used the STRING 'none' not None; the
   decoder ACCEPTED `surprise=` (metric-only must reject); Driver-name/id agreement never
   asserted; case-8 company edges hand-injected instead of live-resolved. Plus: heredoc = not
   reproducible.

**Fixes shipped:**
- Durable probe: `driver/relocation/test_anchor_schema_probe.py` (new code born in
  driver/relocation per README) — 10 tests: the 8 cases with exact pinned inputs/assertions
  (real-derived pinned by source id incl. `du:0000950170-25-024242:revenue:period=…|slice=
  geography:united_states` cross-validated against driver_ids.build_id output 2026-07-18;
  composer local + grammar-faithful, NO core imports — the pinned strings are the contract),
  series_unit=None for numberless, `surprise=`/unknown-slot REJECTION, Driver-name-mismatch
  rejection, and cross-company isolation via TWO REAL source→Company edges read live
  (AA 0000950170-25-024242 vs AAPL 0000320193-24-000123; distinct CIKs asserted). Zero-write,
  zero-token; graph-unavailable → skip-with-reason. **Run: 10 passed in 0.82s** via
  `venv/bin/python -m pytest driver/relocation/test_anchor_schema_probe.py -q`.
  Test file sha256 a23cf2b0b11b2574c6960852be218b63529dbca6a5eaef2d166c083b60dc95ab.
- Core handoff defined (§2): optional CORE-ONLY `backfill_candidate_driver_id` per internal fact
  on existing provenance; exactly ONE candidate reaches the kernel, multiple = fail-closed
  ambiguous; kernel reconfirms from old-source evidence; mismatch never forces attachment;
  its test joins the S4/WP2 gate.
- Doc synced: v5.3 title/status/footer; caller-first diagram; 8-K = all stored text per accession
  (no exhibit classifier); ledger duties specified-but-unbuilt, ONLY orchestration undesigned;
  WP3 = manual dry-run loop; WP4 = wire the EXISTING reader before cert + token-cost reporting
  (per searched item, per accepted fact, projected backfill/forward); reuse boundary pinned
  (locator imports zero channel code); first-probe history + stale counts + D14 version history
  removed from the operative paper (live here only).
- Design sha256 4a47bbd76204f944e3b31028d54a932ad6cd15c26c36724690ecd655142b2053.

## Round 8 (ChatGPT, 2026-07-18) — narrow correction pass. All 7 findings verified; 6 fully true,
## 1 true-with-nuance. Five MORE probe defects of mine owned.

**Verified + fixed:**
1. "Neutral probe imports fiscal.ai code" — TRUE (test_10 imported run_code_tier for env loading;
   and the deeper chain locate→xbrl_lane→oracle:16→run_code_tier:24→fiscal_ai_rules is REAL,
   grep-verified). Probe now loads Neo4j neutrally from .env; grep proves zero channel imports;
   WP2 done-bar gains the import test.
2. Reader scope — TRUE-WITH-NUANCE: the harvest LLM tier is value-known fiscal.ai-shaped; the
   RELOCATION reader is value-unknown and transcript-tested (exam_transcript floors exist) but its
   schema/prompt are its own and numberless is unsupported. Adopted the prescribed wording: reuse
   batch execution + verification gates; the neutral anchor+source request/result schema AND
   prompt are NEW artifacts; prompt = separate owner approval.
3. Rename → `backfill_candidate_driver_name` — TRUE (Driver.name is the unique key; no separate id).
4. 8-K adapter — TRUE (current code still 5–75d + EX-99-only; that is the OLD harvest, pinned in
   §1 as replaced at WP3: enumerate real accessions; quarter-identity for selection routing;
   fetch + dedupe ALL sections/exhibits/filing text).
5. Illegal instants — TRUE, MINE: two fixtures paired multi-day periods with time_type=instant
   (Core's gp_X_X law violated). Fixed: instant fixtures use gp_DATE_DATE; the weather condition
   became a duration.
6. Error-swallowing skip — TRUE, MINE: any exception skipped. Fixed: skip ONLY on genuine
   unavailability (ServiceUnavailable/OSError/missing env); query errors and missing pinned edges
   FAIL; exactly-one-company-edge asserted.
7. Partial composer + fact_scope unverified — TRUE, MINE. Fixed: ids now composed by Core's
   AUTHORITATIVE driver_ids pure law (test-only import, reviewer-prescribed round 8 — reverses my
   round-7 pinned-string choice; a partial copy risks drifting from the law); the decoder stays
   independent; stored fact_scope == id suffix asserted (+ a drift-rejection test); company
   resolved from the PARSED source id; "real-derived" labels tightened — only fixtures whose
   evidence is loaded live (AA 0000950170-25-024242, AAL 0000006201-25-000010, both from part1
   harvest data) are called REAL; the rest SYNTHETIC. (Note: yesterday's "real" AAPL accession
   happened to be genuine, found in part1 — but I had not verified it; luck ≠ verification, owned.)

**Rerun:** `venv/bin/python -m pytest driver/relocation/test_anchor_schema_probe.py -q` →
**12 passed in 2.03s** (both live edges resolved; AA cik ≠ AAL cik asserted).
Channel-import grep on the probe: zero matches.

## Round 9 (ChatGPT, 2026-07-18) — final small pass. Both gaps verified TRUE; both wording fixes adopted.

1. **WRONG_COMPANY defect — TRUE, MINE (reproduced by reviewer, confirmed by inspection):**
   `strict_decode` took `edge_company` as a free caller argument — an AA fact accepted any injected
   company. FIXED: the decoder now takes an edge MAP keyed by source id and binds the company ONLY
   via the source id PARSED FROM THE FACT ID; a map lacking the fact's own source (or holding a
   different source's edge) raises. New test_12 pins the cross-wired rejection.
2. **Work-order flaw — TRUE:** WP1's regeneration would have used the unsafe 5–75-day 8-K guess.
   FIXED: the 8-K routing/fetch correction (quarter_identity used ONLY when
   `safety_action == AUTO_OK`, else fail closed; fetch + dedupe ALL stored text per accession)
   now lands BEFORE the single regeneration, inside WP1.
3. **Probe-claim narrowing adopted:** the probe uses legal period forms but does NOT validate
   period legality (Core's validators own it; nothing duplicated); only the source→Company edges
   are loaded live — quote/unit/Driver payloads are pinned fixtures.
4. **Wording adopted:** "no new matcher is ever built" → "No new deterministic matcher is built
   in this work; reconsider only if WP4's measured recall or token cost proves it necessary."
5. **CORRIGENDUM to the round-8 entry above:** its phrase "REAL fixtures = evidence loaded live
   and pinned" overstated — only the company EDGES were live; payloads were pinned fixtures.
   Also its "legal periods only" implied validation the probe never performed.

**Rerun:** `venv/bin/python -m pytest driver/relocation/test_anchor_schema_probe.py -q` →
**13 passed in 1.82s** (12 prior + the cross-wired-company rejection).

## Round 10 (ChatGPT, 2026-07-18) — DESIGN APPROVED ("lock-ready"; hashes + 13/13 independently
## verified by the reviewer). One wording-only honesty edit, adopted:
The edge map is TRUSTED internal output of the exactly-one graph-edge query. The probe proves
parsed-source lookup and rejects missing/cross-wired KEYS; it does NOT authenticate a fabricated
VALUE under the correct key ({AA source: WRONG_COMPANY} passes by design — the map is the graph's
answer, and duplicating graph validation in the decoder would be pointless).
**CORRIGENDUM to round 9 above:** its phrase "a company supplied for a DIFFERENT source must never
bind" stands, but the implied stronger claim ("injection impossible") is retracted — key-level
protection only. Probe docstring + design §2 corrected.

## Round 11 (ChatGPT, 2026-07-18) — WP1 PLAN corrections. All 9 verified TRUE (incl. two
## code-checked: `--tag`-alone selects no work [argparse]; regress.py only re-grades saved outputs).
Adopted into WP1 Plan v2: tests+fixes commit TOGETHER (main never red — the core session shares
it) · substring invariant fixed at the link_lib producers, not locate · full-qname + unit tests ·
8-K = enumerate REAL accessions (no window even for candidates) · dropped-8-K ⇒ completeness
stays incomplete (park, never SKIP) · pinned regenerate manifest with the exact --tickers command ·
honest report labels (mechanical compliance ≠ precision; three count bases) · item_id through all
three paths · frozen before/after locator A/B (regress alone cannot see locator changes).
GO given: execute independently, return at the gate or a named trigger.

## WP1 EXECUTION RECORD (2026-07-18) — 5 commits, all local main, UNPUSHED
- `2a59e49` Steps 1-2: exact_numbers.py (Decimal dec/eq/plain + one date rule) · tier1
  Decimal-exact · %-class guard · fractional-rounding ban (owner F2) · zero legal · _tableforms
  rewrite · RAW-slice quotes (_tidy search-only) · locate rung-1 corpus-quote + cell_evidence ·
  xbrl_lane exact dates/instant/unitRef/bare-local-names. A/B on pinned 3-ticker slice: +31
  resolved (all decimal/small), 0 lost. Battery 71/71 · regress 28/28 identical.
- `02d1f07` Step 3: fetch_earnings_8ks (Item-2.02 universe = quarter_identity's own), AUTO_OK
  gate, all-text dedupe, item_id. DEVIATIONS RECORDED: accession_periodic = PIT-safe PRIOR anchor
  (reviewer's literal join field wrong; intent implemented via the resolver's announced period) ·
  all-8-K enumeration crashed on non-earnings 8-Ks → Item-2.02 mirror.
- `88a4f19` Steps 4-5 (AMENDED honest): pinned manifest (10 tickers, 1,535 rows, sha 473bda9d…) ·
  INCIDENT: fetch_press_release deleted with 10 un-grepped consumers → regress FAILED → caught;
  an earlier commit falsely claimed 28/28 from tail-truncated output → amended; the legacy fetcher
  restored VERBATIM as LEGACY-BENCHMARK-ONLY (its window recipe is part of the frozen floor
  definitions).
- `28f2aeb` item_id per DISTINCT RAW ROW (reviewer catch confirmed 26/26: fiscal.ai repeats KPI
  labels across category variants — ACN geo1=23,000 vs geo2=45,029,043,000); whole-row hash;
  1,535 ids = 1,535 rows; a mid-write verification was caught via mtimes and redone.

## Round 12 (ChatGPT, 2026-07-18) — WP1 audit. SIX findings CONFIRMED by my own reproductions,
## TWO stale (already fixed in 28f2aeb). Corrective commit `1d4491d`:
1. 52/53-week drop (AAPL live accepted=0): _8k_gate joins on quarter_label(fy,q) ==
   period_to_fiscal(vendor period, fye, form) — the ≤5-day-rule fiscal math; never calendar ends.
   AAPL's true 8-K now selected; cohort pr_records 91→129.
2. 44/45 illegal skips (exact ledger count): build_packets parks sources_incomplete BEFORE the
   type-list check; ledgers carry item_id. Now 45 park / 0 illegal.
3. Trail-cut ('86' accepted from '86%'; +123 from '(123'): _with_trail keeps %/)/'percent'/scale
   words in the crop; percent-guard widened to ' %'/' percent'.
4. evil:Revenues + shares-for-USD: stored-prefix must match request-prefix when present (bare
   storage matches local — verified canonical form); expected_unit money/nonmoney in resolve;
   tier1 is_currency unit-class guard ('usd' substring — filer-local unitRefs make exact
   impossible), wired through locate.
5. NaN/Infinity rejected (is_finite).
6. 'or True' removed; uncertain cases properly pinned.
+ corpus_missing rows carry item_id · wp1_verify.py COMMITTED (completeness-vs-summary ·
  reconciliation by raw-row id 1,535=1,535 · both compliance checks · output sha256s → manifest).
Final: cohort 389 resolved (+37; T1 106→105 = one bind fewer, consistent with the unit guard;
prior outputs overwritten so no per-record diff — permanently fixed by manifest hashes) ·
verifier ALL ASSERTIONS PASSED · battery 82/82 · regress 28 [ok] PASS (full output).
STATE: 5 WP1 commits unpushed; holding push + WP2 for reviewer re-audit / owner word.

## Round 13 (ChatGPT, 2026-07-18) — post-1d4491d re-audit + two follow-ups (the "slimmer
## correction" supersedes the defensive first draft). NINE claims, ALL CONFIRMED by my own
## reproductions BEFORE any fix; one prescribed mechanism REJECTED with evidence (flagged).
Verification-first record (every claim reproduced live or code-cited before fixing):
1. **ACI future-8-K (CRITICAL) — CONFIRMED, worse than claimed.** Exactly 23 candidate snippets
   from `0001646972-26-000028` (created 2026-04-14) attached to ACI period 2025-02-22 residuals.
   Live gate run: math `period_to_fiscal(2025-02-22, fye=2, 10-K) = (2025, Q4)`; resolver labels
   (company convention, year-of-start): true announcer `-25-000040` = Q4_FY2024 → **other_period
   (wrongly rejected)**; future `-26-000028` = Q4_FY2025 → **accept (wrongly admitted)**. BOTH
   directions wrong; ACI 2026-02-28's true announcer was ALSO being rejected. Root cause exactly
   as reviewer said: `fiscal_math.py:28-40` documents AAP/ACI as unfixable ("Extreme 52-week
   calendar"; "Only mismatches: ACI (4, known edge case)"); `quarter_identity.py:195-225` documents
   the year-of-start vs year-of-end split (TRUST_XBRL_ADVANCE).
   **Fix:** `_8k_gate(info, target_fyq)` — resolver label must EQUAL the TARGET filing's OWN
   declared XBRL identity, read via the resolver's own `_XBRL_QUERY` (unique-or-null at the query
   level → conflict fails closed) + `parse_xbrl_fiscal_identity` (FY→Q4, garbage→None). Both sides
   are company-XBRL-convention BY THE RESOLVER'S CONSTRUCTION (prior-XBRL + advance; rule_h for the
   trusted year-of-end issuers; mixed-convention issuers FAIL_CLOSED) → numbering can never
   disagree. NO new resolver built; `period_to_fiscal` fully removed from the harvest join.
   Measured before building: 25/25 cohort targets carry a parseable dei identity.
   Live pins (reviewer-named accessions): AAPL target `0000320193-24-000123` selects EXACTLY
   `['0000320193-24-000120']`; ACI target `-25-000052` accepts `-25-000040`, rejects `-26-000028`.
2. **Global incompleteness — CONFIRMED by code.** `fetch_earnings_8ks` counted uncertain across
   the ticker's WHOLE 8-K history; live: every cohort ticker's FIRST-ever 8-K (no prior periodic)
   is FAIL_CLOSED and poisoned every period. **Fix:** `_uncertain_relevant(created, period)` —
   an 8-K filed BEFORE the period ended cannot announce it (results don't exist yet); pure
   impossibility, zero windows, zero new machinery.
   **FLAGGED DISAGREEMENT (kept mine):** the reviewer prescribed scoping to the unresolved 8-K's
   "matched filing cycle, using the existing historical pairing". VERIFIED: no such pairing exists
   for failed resolutions — `_attach_resolution_context` (accession_periodic) is attached ONLY on
   AUTO_OK paths (quarter_identity.py:632/706/734/781; FAIL_CLOSED returns bare `_result`).
   Building sequence-position pairing for 8-Ks the certified resolver REFUSED to place = building
   a new mini-resolver (their own "build no resolver" rule) + trusting an assumption fail-closed
   philosophy rejects (restatement 8-Ks exist — D11). The impossibility rule fixes the named
   defect (old 8-K no longer poisons later periods) at the cost of conservative parks for periods
   BEFORE a recent unresolved 8-K. Owner may overrule.
3. **Public locator (5 sub-claims, all CONFIRMED):** (a) `locate_by_fingerprint` dropped
   unit_ref/expected_unit (locate.py:114) → forwarded + monkeypatch test; (b) NO rate rejection
   existed anywhere ('…DiscountRatePercent' passed `concept_ok` via 'operating') → case-insensitive
   camel-token rejection {rate, percent, percentage, ratio}; substring ban avoided ('Corporate'
   survives, tested incl. ALLCAPS 'RATE'); (c) bare scaled prints ('1.2' / '1,200' for 1.2B)
   accepted with zero scale evidence → MEASURED FIRST: 315/389 resolved quotes are bare-scaled
   table rows, and 315/315 of their sections carry the strict 'in (millions|thousands|billions)'
   marker → section-marker OR immediate-tail OR full-magnitude evidence now required, as OPT-IN
   `scale_gate` (locate.py passes True; the five certified prep consumers keep byte-identical
   legacy behavior — consumer grep BEFORE design, lesson 3 applied); (d) 'N/A'/'-331x' crash
   live-reproduced (ValueError) → Decimal-parse guard at entry, clean abstain; malformed vendor
   values in the harvest PARK as `invalid_value` (visible channel-data defect, never a terminal
   skip); (e) full-qname overclaim = xbrl_lane MODULE docstring (function docstring was already
   honest) → wording fixed; behavior was already correct (round-12 prefix guard).
4. **Verifier not check-only — CONFIRMED by inspection.** Old code checked only raw−out (invented
   extra ids invisible) and UNCONDITIONALLY overwrote `output_sha256`. **Rewrite:** CHECK-ONLY
   default (recorded hashes REQUIRED + compared; writes nothing); `_reconcile` both directions;
   `--record` = explicit stamp mode. NEW explicit no-future-source proof: every ACCEPTED 8-K's
   label (now in the run's `sources_ledger.jsonl`) re-checked == its cp's target identity; every
   8-K-sourced record/candidate must trace to an accept row in its OWN cp. Unit tests for both
   helpers (RED first).
5. **Manifest — ALL CONFIRMED:** stale `02d1f07` (outputs were from the round-12-fix run) →
   `--record` stamps `git rev-parse` + dirty flag; company-periods + 49 consulted/used source
   accessions pinned; full-sheet duplicates counted EXACTLY as reviewer said (18 groups / 31
   extra occurrences, all BX-style byte-identical repeats) → `dedupe_rows` collapses at load
   (identical rows are ONE fact; whole-row id shared by construction; verifier dedupes the same
   way); the 1,400 denominator RESTORED and measured = unique (ticker,kpi,period) targets
   (1,426 with +value; 1,535 with +category = raw rows) — report now shows BOTH bases.
6. **0.24% honesty — CONFIRMED at quarter_identity.py:100-104** ("Warm-start (9878) | 97.92% |
   0.24% | 1.83%"; "structural ceiling"). Report + design now state: selection = AUTO_OK (0.24%
   documented ceiling) ∧ label==target-identity; zero-error is a MEASURED claim (WP4), never
   assumed. Reviewer's FCX live-lane pin: N/A to WP1 (historical lane always has the target
   filing; the slimmer correction dropped it; live resolver untouched per owner's accepted risk).
**Method:** RED battery first (13 new tests, exact failures confirmed incl. both live crashes) →
smallest fixes → 94/94 battery (was 82; one old gate test superseded by the new-join test) →
regress ALL 28 floors hold (full output, counted) → ONE pinned regenerate → `--record` → CHECK
mode green. Consumer greps before every signature change: `fetch_earnings_8ks`/`_8k_gate` have
zero outside consumers; `row_quote`/`scan_text`/`value_forms` feed 5 certified preps → opt-in
param. No scheduler, no retry framework, no Core change, no live waiting, resolver untouched.
**Fresh cohort (regenerated once, verified):** 391 resolved (T1 105 · T2 286; pr_records 131 —
ACI's two true announcers recovered) · 356 residual · 1006 abstain (961 derived skips + 45
value_absent; **parks 45→0 — CORRECT**: every non-ACI ticker's single uncertain 8-K is its
first-ever 8-K, filed BEFORE all cohort periods → irrelevant by impossibility → those 45 rows'
source sets are genuinely complete (accept=1 each) → truthful terminal skips; ACI's 3 relevant
post-period uncertains persist but its cps have no value-absent rows) · gate verdicts 24 accept /
271 other_period / 46 uncertain · compliance 2× 391/391 · reconciliation both-directions
1,535=1,535 · sources_ledger.jsonl now pins every enumerated 8-K verdict+label per cp.
STATE: round-13 corrective commit pending push word; WP2 still held.

## Round 14 (ChatGPT, 2026-07-18) — post-b7da386 re-audit. SEVEN claims, ALL CONFIRMED by my own
## reproductions — including TWO false claims of MY OWN exposed and owned. Code commit `50676a9`.
1. **WMS wrong pairing — CONFIRMED live; my round-13 "conventions can never disagree" claim was
   FALSE.** WMS's dei is inconsistent WITHIN the company ((2024,1)/(2025,2)/(2025,1) across
   consecutive quarters); for target 10-Q 2024-06-30 the dei join accepted the prior-year 8-K
   (-23-000033, label Q1_FY2024) and rejected the true announcer (-24-000029, Q1_FY2025).
   Round-14 replaced identities with a filing-sequence matcher (timeline + predecessor pairing +
   announcer window); the live battery immediately exposed a further edge I then had to
   special-case (AAPL's Q1-early 8-K files one day before its own 10-Q → prior == the target →
   ambiguous two-pass) — a smell the owner later called correctly.
2. **Scale multiplier/locality — CONFIRMED ×3 live** ('1.2 million' proved 1.2 BILLION; a
   thousands header proved a millions form; an unrelated earlier marker proved anything; 52
   cohort text blocks carry MIXED markers). Fix: evidence must name THE REQUIRED multiplier
   (tail == form's divisor; marker locality). **Regenerate #1 then dropped resolved 391→329 —
   measured before stamping: ablation isolated 12 casualties and exposed MY over-tight
   nearest-single-marker rule**: real headers declare SEVERAL scales ("(In millions, except
   number of shares, which are reflected in thousands…)" — AAPL's standard header; the nearest
   single word was 'thousands'). Fix: required multiplier ∈ the CURRENT TABLE's declarations
   (##TABLE_START region); outside tables the nearest declaration. Also `value_ok` now vetoes a
   printed tag that contradicts the claimed value — which caught one semantically-wrong OLD test
   fixture ('$ 9,876 million' for plain 9,876) that got corrected, not appeased.
3. **Rate-name ban — REVERTED (reviewer right, my round-13 rule over-rejected).** The certified
   truth pool carries `awk:PublicUtilitiesGeneralRateCaseAuthorizationsAnnualizedIncremental
   RevenuesApprovedAmount` (4 REAL USD rows). Unit identity decides instead: tier1 skips
   'pure'-unitRef facts in the money/number lane.
4. **Cycle-scoped uncertainty — ADOPTED; my round-13 "no pairing exists" rejection was WRONG**
   (the pairing MECHANISM is derivable for any 8-K even when labeling failed). ACI's annual
   stopped being poisoned by later unlabelable quarterlies.
5. **1e309 — CONFIRMED live** (Decimal-finite, float-infinite → OverflowError). Entry guards +
   `invalid_value` park.
6. **Verifier circularity + dangling commit — CONFIRMED.** The round-13 no-future-source check
   compared a label to a target identity computed by the code under test; the manifest pointed at
   an unreachable amend orphan. Fix: independent graph re-derivation per accepted 8-K + the
   two-commit procedure (clean CODE commit first → regenerate against it → artifacts commit).
7. **Unapproved locked-design edit — CONFIRMED, REVERTED** byte-identical to `ba0c629` (and my
   round-13 §1 text contained the false "can never disagree" claim anyway). Design amendments are
   owner-locked; the corrected mechanism went to the owner instead.

## Round 15 (owner + ChatGPT, 2026-07-18/19) — THE OWNER'S RULING. Option D: the two-file
## earnings-8-K authority. My round-14 sequence matcher RETIRED.
- **Owner interjected** rejecting round-14's ordering assumptions and proposing calendar-date
  comparison (convert the resolver's label to a calendar date; compare calendars). VERIFIED
  before adopting: the idea is right for ~everything EXCEPT the ACI-class — live-measured, the
  converter is year-convention-bound (ACI true announcer label Q4_FY2024 → projected 2024-02-29
  vs true 2025-02-22 → rejected; the FUTURE 8-K projected 2025-02-28 → accepted). The owner's
  52/53-week tolerance intuition was right; year-NAMES were the real blocker, and they re-enter
  through the conversion itself. Flagged honestly with a menu instead of implementing.
- **Reviewer round-15 surfaced the EXISTING production matcher** — real, verified by my own
  execution (I had rejected "existing pairing" too hard in round 13 without finding this file):
  `get_quarterly_filings.get_earnings_with_10q` pairs every 2.02 8-K to the original 10-Q/10-K
  covering the most recently ENDED period as of the 8-K's filing time, lag-validated within
  [-24h, +90d]. Ran its rule myself on 7 cases: ACI true→its 2025 10-K; ACI future→its OWN 2026
  10-K (accession equality rejects it for 2025 naturally); AAPL 52/53→pinned target; AAPL
  Q1-early→the Q1 10-Q (round-14's ambiguity DISSOLVES — no special case needed); WMS true /
  prior-year / reviewer-cited — all correct.
- **OWNER RULED (now owner-locked law: memory + FinalDesign PER-21 / BUILD §3):** historical
  8-K pairing = `get_quarterly_filings.py` exact target-accession equality + `quarter_identity`
  AUTO_OK as trust gate ONLY; live/new 8-K = `quarter_identity` alone; labels and calculated
  dates NEVER joined on; missing/ambiguous → PARK; no third matcher ever. Owner stopped the
  option-C universe sweep and ordered the full read-only pairing check before regeneration.
- **Extraction (reviewer refinement: one STRUCTURED matcher, never copy or parse pipe-text):**
  `match_8k_to_periodic()` extracted INSIDE get_quarterly_filings.py (+ pure `_lag_hours`/
  `lag_valid`; QUERY's daily_stock filter became a parameter — the tool keeps
  require_daily_stock=True; the harvest passes False so 163/10,994 8-Ks without return data are
  no longer silently hidden). `get_earnings_with_10q` rewired on top — output proven
  BYTE-IDENTICAL (4-ticker before/after snapshots; reviewer independently confirmed on 11).
  All 9 consumers audited (they import only unchanged names); earnings-pipeline suites 116/116;
  `quarter_identity.py` untouched (empty diff). Round-14's timeline/cycle/ambiguity machinery
  DELETED. Harvest gate: accession equality + AUTO_OK + lag; an unprovable 8-K poisons ONLY the
  target it matched (unlabelable true announcers and lag-invalid late supplements park AT their
  match — the reviewer's honest PHR gap is a counted park, never silent completeness).
- **Reviewer audited the file refactor: PASSED**, with two pre-commit chores, both done: (a) my
  "latent NameError" comment was FALSE — `lag_hours if valid_10q else 99999.0` short-circuits, so
  the crash I claimed could never fire; verified myself, owned, removed (unverified claims about
  old code are the same sin this arc polices); (b) durable pin test added
  (`scripts/earnings/test_get_quarterly_filings.py`: ds-filter scope, exact ±1s lag boundaries,
  nearest-lag dedupe, frozen output shape — 3 tests, pure/fake-session).
- **FULL READ-ONLY UNIVERSE PAIRING CHECK (owner + reviewer precondition) — 792 tickers /
  10,994 2.02 8-Ks: ZERO wrong pairings found.** 9,788 clean pairings (89%) · 1,050 fail-closed
  parks (unlabelable; park at their matched target) · 156 lag-invalid parks (early-2026 8-Ks
  whose next 10-Q isn't ingested yet — future reruns pair them correctly — plus documented slow
  filers, e.g. ADSK's 2024 delayed filing, +102d) · 9 label-vs-match flags = ALL false alarms of
  MY convention-free q-number cross-checker on the documented freak calendars (AAP×6 — its Q1 is
  16 WEEKS, ends late April, breaking the 3-month heuristic; ACI×2; NTNX×1): in each, the label
  AND the pairing are both correct; the checker's assumption is what failed. Zero errors.

## Round 15 — FINAL COHORT (Option D, stamped). Regeneration honesty: THREE regenerates this
## round, each cause-documented before proceeding (never silent): #1 exposed my over-tight
## nearest-single-marker rule via a −62 drop (measured, 12-case ablation, AAPL combined-header
## discovery); #2 (post-Option-D) dropped to 265 — ablation-attributed EXACTLY: 70 records to the
## table-region rule on AA/Alcoa's caption-above-table layout (scale declared ABOVE the
## ##TABLE_START tag) → the inherit-when-undeclared refinement recovered them, mixed-table
## strictness intact; #3 = the final. OWNED along the way: my "90-row divergence" scare was a
## MISREAD of the by-design resolved∩residual overlap (115 rows — the keep-candidates rule), and
## the network-flakiness hypothesis I briefly held was DISPROVEN by cache mtimes (0 fetches in
## 2h) before it could mislead. Determinism then PROVEN: two consecutive runs, identical counts.
**FINAL (produced against clean code commit `6e7f8b1`, stamped + check-verified):**
329 resolved (T1-xbrl 103 · T2-label 226 · 8-K records 81) · 410 residual (115 of them ALSO
resolved — multi-source by design) · 1006 abstain (961 derived skips + 45 value_absent) · parks 4
(sources_incomplete: AA×3 + ABT×1, 2025-12-31 — the designed lag-class behavior: each ticker's
early-2026 8-K matches the annual target with invalid lag because the next 10-Q isn't ingested
yet → the target parks; future reruns pair them cleanly) · verifier RECORD + CHECK both ALL
ASSERTIONS PASSED (both-direction reconciliation 1,535=1,535; compliance 2× 329/329; independent
inline-Cypher pairing + production-lag proof per accepted 8-K; zero fabricated) · battery 99/99 ·
regress 28/28 floors · earnings suites 119/119 · manifest code_commit `6e7f8b1-dirty` ('-dirty'
= the two standing out-of-scope dirty files only; the artifacts commit follows separately per the
two-commit procedure).
**Why 329 < the round-13 "391":** the 391 baseline was measured against a CONTAMINATED corpus
(the label-join's wrong/extra 8-K accepts, ACI-future included) and pre-veto scale rules; records
that lost their deterministic bind under the hardened gates DEMOTED to residual (the LLM tier
re-attempts them) — nothing wrong was kept for the sake of a bigger number. True P/R stays a WP4
measured claim.
STATE: WP1 code + evidence COMPLETE under the owner's two-file authority; push + WP2 remain
owner words; reviewer re-audit next.
