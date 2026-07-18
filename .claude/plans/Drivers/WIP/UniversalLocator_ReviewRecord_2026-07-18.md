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
