# Driver-value relocation probe — state

**What it does:** given a text metric locked from one period (its verbatim quote), blind-refetch its
exact value in a DIFFERENT period's filing — 100% precision is the hard rule; abstain > guess.
This is the "how locked text drivers get future/historical values" mechanism. ISOLATED test harness;
touches nothing in production seeding.

## Method (frozen, working)
1. `build_address` — from the lock filing: label tokens (KEEP metric-kind words), table caption
   (heading, not prose), sibling row-labels, unit, lock_row.
2. `locate` — candidate snippets in the target filing by structural overlap (siblings+caption+label),
   keep ~6 tables + prose windows.
3. `relocate.js` bind — LLM picks TABLE → LINE → COLUMN via the two-signal picker (period TYPE
   annual/quarter + DATE). No magnitude guard, no lock-value anchor (both removed as fragile).
4. verify — independent LLM re-check (right line + right period).
5. `grade.py` — leave-one-out oracle: build address from period A, blind-refetch period B, grade the
   picked number vs fiscal.ai's known B value (rounding-tolerant). Sources: 10-K/10-Q + 8-K EX-99.1.

## Results (blind, unseen companies; HONEST ruler = sign-aware stated-precision, 3-way CORRECT/MISBIND/UNGRADEABLE-REF)
| run | precision | recall | notes |
|---|---|---|---|
| 150-pair, pre-fix (honest ruler) | 94.8% | 76.9% | baseline before Phases 1a/2/3 |
| **150-pair CERTIFIED (Phases 1a+2+3)** | **97.8%** | **92.3%** | bind-only; 143 gradeable, 3 misbind, 7 ungradeable-ref |

Per type (certified): geography 100/95 · non-GAAP 100/91 · operational 98/94 · segment 94/88 · other 90/82 · percent 100/100.
Residual 3 misbinds = adjusted-vs-GAAP (CAG), sign flip (AFL), count off-by-2 (BJ) — known-hard ~2%; ~100% for real SEEDING (value-gate skips them).
NOTE: this is the harder no-value FUTURE-fetch case; annual only, A–D companies. Phases done: 0 (honest ruler), 1a (identity), 2 (retrieval), 3 (shape-neutral reader). Skipped: 4 (XBRL lane, 5% payoff). Next: 6 (news/transcript sources).

## Key findings
- The 5 precision misses are DEFINITIONAL near-misses: fiscal.ai stores an ADJUSTED number, the filing
  states GAAP (e.g. seg op profit 989.4 adj vs 1,017.0 GAAP); 3/5 fiscal.ai's value not in the filing.
  In production seeding (we HAVE the value + gate `value_ok`) these abstain → precision ~100%. The 95.8%
  is the harder no-value FUTURE-fetch case.
- Two bugs fixed 2026-07-13: (A) label stripped metric-kind words → `kpi_tokens` keeps them;
  (B) caption grabbed MD&A prose → `caption_of` takes the heading.
- Recall ceiling ~90%; misses are safe abstains or value not on the fetched pages.

## Phase 6 (B) — source generalization: TRANSCRIPTS (2026-07-13)
Same shape-neutral reader, candidates from earnings-call PreparedRemark+QAExchange text (fetch by
conference_datetime within 120d after period end; `prep_transcript.py`). 37 pairs, bind-only:
emitted 2 / CORRECT 2 / MISBIND 0 / **HALLUCINATIONS 0** / abstained 35 → precision 100%, and clean
abstention on the 35 where the number wasn't spoken. Reader correctly read SPOKEN ROUNDED prose
("51 million members", "$5.41 billion"). RECALL is source-limited: transcripts state only ~5% lossless
/ ~15% rounded of our ANNUAL SEGMENT metrics (calls discuss headline totals + narrative, not segment
tables) — same data-block pattern as XBRL (5%). CONCLUSION: reader is source-agnostic (precision +
abstention hold on filings AND spoken transcripts); segment-detail metrics belong to FILINGS; a proper
transcript/news RECALL test needs a HEADLINE-metric population (total rev / EPS / key counts), not built.

## GAME PLAN (Fable-5-reviewed 2026-07-13) — remaining order to full certification
One pipeline: value-known (seed) = no-value (fetch) + the value gate. Code takes every 0-token exit; the
LLM owns ONE judgment ("is this snippet THIS driver's value for THIS period?"). ~35-50M tokens ≈ 3-4 sessions.
0. **DONE** — Freeze emit gates + output schema in `link_lib.py`: `quote_in_candidates` (anti-hallucination),
   `precision_grade` (exact|rounded|approx|None), `evidence_or_abstain` (frozen record), `stated_match` moved
   here. 0 tokens, self-checked; certified-150 re-grade UNCHANGED at 97.8/92.3 (no regression).
1. **DONE** — XBRL ORACLE (`oracle.py`): answer key = each filing's own UNAMBIGUOUS facts (0/1/**multi-axis**;
   duration 3-month vs YTD-183d picked; value unique within (concept,member,endDate)). Multi-axis INCLUDED
   (FS-09 req; reads all members locally — safe, oracle only READS not tier1-matches). Self-checked; 97% of
   oracle values appear verbatim in filing text (8 cos). `clean_facts(xbrls,kind)`, `series(session,tk,kind)`.
2. **DONE — QUARTERLY CERTIFIED 97.4% precision / 92.5% recall** (40 pairs, keep=12, faithful names,
   strict gates). **Q-vs-YTD GUARD PROVEN: 0 YTD-picks across ALL runs** (supersedes manual #760).
   Per type: headline 100% · segment 100% · "multi-axis" bucket 94% (1 miss = ACM VIE cross-tab).
   Journey: 71.8% (filer-label backfired, reverted) → 88.6% → 94.3 (faithful names) → **97.4 (keep=12)**.
   Root causes fixed en route (ALL were test-construction or checker bugs, reader was mostly right):
   `kind_word` substring buckets mis-named CostOfRevenue as "revenue" + collided sub-revenues (→ exact
   CANON map + full qname words + `drop_ambiguous` guard); `value_forms` bare 1-2 digit scaled forms
   ("20" for $20.372B) matched stray text (→ removed; annual cert IMPROVED to 98.5/93.0);
   `stated_match` rejected filer TRUNCATION 4,151.2 for 4,151.251M (→ accepts round OR truncate);
   percent-shaped answer for currency metric (→ unit gate in `evidence_or_abstain` + graders);
   locate keep 8→12 (right window lost rank race in big docs; ceiling 88→98%).
2b. TRANSCRIPT CERTIFIED (Step 3 half): **100% precision (7/7), 100% recall-of-present, 0 hallucinations,
   0 YTD leaks; 33 correct abstains incl. 3 look-alike traps refused** (buybacks/dividends/CapEx numbers
   that round-match a DIFFERENT metric — reader identity discipline is the real precision defence in prose).
   Transcripts state few exact numbers (~10/40 even for "headline" concepts) → per-source recall is
   SOURCE-BOUND; catalog recall comes from multi-source input, not one source.
2c. INDEPENDENT AUDIT (ChatGPT 2026-07-13, artifacts /tmp/regression_audit_axes.cHcqXo) — verified verdicts:
   TRUE: prep_oracle 'type' used len(member_TOKENS)>1 → my "multi-axis" bucket = word-count proxy, NOT true
   axis count (their census: 1,013 true 2+-axis series in 57 A-D cos — sizeable). TRUE: fallback lock
   (snips[0]) could lock a wrong row (ACMR "8.4%") → builders now STRICT-lock only. TRUE: on their 156-pair
   TRUE-multi-axis benchmark my locate ceiling = 130/153 @keep=8 → 133/153 @keep=12 — keep alone doesn't fix
   true multi-axis; root cause = XBRL member qnames ≠ printed row words ("AllOtherSegments" prints as
   "Other Business"). Their fix direction (identity from the LOCK ROW's printed words, not qname tokens)
   = the right next step IF multi-axis is un-parked; their 156-pair set = ready-made Step-6 stratum.
   ALREADY-DONE/MOOT: "never use old value as size hint" (removed long ago); ABT/ADM/ADBE examples were
   the old name-collision bug (fixed, now grade CORRECT/abstain).
3. TRANSCRIPT + NEWS on HEADLINE metrics — census News first (Cypher, 5 tickers); 20-40 pairs each; CODE
   period-stamp each candidate (call/article date) + one forward-looking-exclusion clause; window 120d→75d.
4. UNION = OPTIONAL MODE, NOT DEFAULT (user 2026-07-13): the engine's default input includes the SOURCE
   ({name, period, value, source}) and reads that source only — catalog wants each source's own value/quote.
   A try-other-sources flag can come later; no cascade built by default.
4b. REGRESSION MARKER (user 2026-07-13, BEFORE any cost work): frozen `benchmark/` + `regress.py` gate.
   **v2 (current)** = locate v2 artifacts, 4 sets, floors: annual 96.3/94.2 · quarterly 92.5/92.5/YTD0 ·
   headline 75/7.5 (n=4 emits) · multiaxis 90.8/82.1/YTD0. v1 (old locate) at commit 0ea0906.
4c. LOCATE V2 (ported from verified ChatGPT retriever, 2026-07-13): uniform overlapping 3.6KB chunks
   (whole doc = guaranteed coverage) + lock-word IDF + lock phrases + per-axis facet groups. TRUE-multi-axis
   findability 87→97-100%. RE-CERT (same reader, new locate, STRICT-lock rebuilt pairs): annual cell 97.8
   strict 96.3/94.2 (2 sign-pres; 3 real = 2×AEE GAAP-vs-adjusted same-sentence + BJ count) · quarterly
   cell 97.5 strict 92.5/92.5 (1 real = AEE sub-entity) · transcript 3/4 (1 real = ACMR call speaks
   NON-GAAP opex vs GAAP truth) · **multi-axis (UNPARKED, 156 true pairs, ChatGPT benchmark): cell 97.2
   strict 90.8/82.1, holdout 92/85, 3-axis 100%, 4 real errors**. RULER upgrADES en route (all verified
   artifact classes): SIGN-PRES class (parenthesized-subtraction presentation ≠ wrong number; catalog-side
   normalization decides sign), 1-ulp agreement (two prints of one fact differ by one last-digit step,
   ≤0.15% rel err — XBRL decimals rounding), ladder guard 0.5→0.05 (0.4M=400K). **RESIDUAL = ONE dominant
   class: GAAP-vs-ADJUSTED measurement twin** (AEE ×2, ACMR call; value-gate kills it in seed mode; fetch
   fix = carry measurement hint from lock context) + rare sub-entity/count. ChatGPT iXBRL exact-cell
   extraction (30+ layout test) pending verification for the lock side.
5. BATCH/cost — per-company-period reader, lean agent, warm cache; A/B bar = IDENTICAL outputs on ~100 pairs.
6. GRAND cert — stratified UNSEEN companies, all 5 sources × both periods, XBRL oracle + a fiscal.ai stratum
   (avoid tag-selection bias), ~50-quote LLM spot audit. **+ DRIFT TEST (user 2026-07-13, task #766):**
   pairs where the same XBRL concept+member persists but the PRINTED label changed across years
   ("same store sales" -> "comparable store sales"); lock OLD wording, relocate into NEW year; report
   found-despite-rename % / wrong-pick % (~0 required) / abstain %. + ChatGPT 156-pair true-multi-axis
   stratum (already adopted).
KEEP: the residual-audit lane (only belt that caught the 13 wrong Part-1 records). When grading vs the XBRL
oracle, EXCLUDE XBRL blobs from the reader's candidate corpus (else circular). CUT (over-engineering): hedge
detector (regex sets grade), relative-period as LLM skill (code stamps it), a new quarterly harness, news NER.

## GPT FINAL DESIGN — verified + landing (2026-07-13, commits f36dbcb/ab66cc1; work now on MAIN)
HEAD-TO-HEAD on their frozen 100 unseen-company TRUE-multi-axis cases (identical candidates):
their reader 100%/95% · **OUR certified reader + THEIR exact addresses 98%/96%** · our reader + our old
addresses 92%/85% → the win is the EXACT ADDRESS (row × column × section from the HTML grid), readers are
equivalent. Both our 2 misses = ADM segment-table rows (their reader abstained same cases). Artifacts +
FINAL_HANDOFF archived `benchmark/multiaxis_pool/final/` (SHAs match their declared snapshots).
LANDED: `xbrl_lane.py` (#767 step 1) — deterministic full-identity resolver, self-check 130/20-abstain/0-wrong
on 150 random pool pairs; abstains = OUR graph's missing facts (SEC fallback = future). REMAINING (#767):
step 2 port HTML grid extractor into lock flow (needs EDGAR inline-HTML fetch — new infra); step 3
`exact_section` reader TIE-BREAK (prompt change → bundle with twin-fix hardening, ONE re-cert bill).
DO NOT PORT: per-company axis map; naive explicitMember loop into tier1.

## COST/BATCHING (#770 DONE 2026-07-14, commit 1822a66)
BATCHING VALIDATED: `batch_groups.py` (group cases by company+period; merged deduped candidates;
HARD CAPS <=8 metrics + <=100KB per call, recursive split) + `relocate_batch.js` (one call binds all
group metrics, same 5 rules). A/B vs certified one-by-one: quarterly 40/40 IDENTICAL @ 45% cheaper;
multiaxis grouped 32/33 (1 id<->row slip in an 8-case group — production seed mode's value gate
neutralizes it). keep-trim REJECTED (24->16 saves 30% but loses 5 reachable values). Lever stack for
the production harvest (#771): XBRL lane (free) -> batching (45%+, denser on real fiscal.ai ~14 KPIs/co)
-> seed value gate -> lean agent (-37%, A/B folds into grand cert).
DRIFT CENSUS (#766 free half): 300 exact-cell pairs -> renames 2/270 extractable (0.7%), both soft
("Natural Gas Liquids"->"NGLs", footnote marker). drift_candidates.json committed. Scoring + the
annual-boundary variant = small grand-cert stratum.
PRODUCTION TRANSITION (#771, user goal): every driver x period x every source that states it
(news excluded -> its own track) -> frozen evidence record each, so part-2 writes DriverUpdates
without re-reading sources. Design-mandated (FROM_SOURCE per-source facts + collapse ranking).

## MINI-EXAM / GRAND CERT (#772 + #766 DONE 2026-07-14) — VERDICT: PASS
111 fresh cases (unseen companies / unseen pool pairs), batched (`batch_groups.py` caps 8/100KB) +
lean Read-only agents, 80 calls, **2.8M tokens actual** (vs 4-5M est). Strata (grade_quarterly, oracle truth):
- exam_annual 44: 36/38 = 94.7% strict (97.4% cell-level incl 1 sign-pres), recall 81.8%, YTD 0.
  1 real miss (DE: grabbed 61,251 from a messy segment table, period_evidence invalid — rule-3 lapse).
- exam_mafresh 36 (multi-axis, fresh holdout pool pairs): **100% precision (34/34), recall 94.4% = its ceiling**, YTD 0.
- exam_madrift 8 (renamed-label torture): mechanical 4/6; **adjudicated 6/6 — 0 real wrong picks.**
  The 2 mechanical misses are a FILER TAGGING ERROR (MDT 10-Q acc 0001613103-23-000149: inline-XBRL
  contexts row-shifted — (US,Diabetes)-tagged fact wraps the printed "Medical Surgical 963" cell;
  printed table sums correctly, reader picked the printed truth 217/740). Proof = filing's own ix
  contexts c-151/c-155 + segment-total sums. **Drift scan doubles as a filer-tagging-error detector.**
  3rd overturn was OUR truth bug: `int(float(-0.2))=0` — fixed (float), PSN regraded CORRECT.
- exam_transcript 23: 4/5 = 80%, recall-of-present 4/9, YTD 0. 1 miss = DAL call speaks ADJUSTED
  revenue unlabeled ($14.2B vs GAAP 15,854) — the known transcript adjusted-trap class (ACMR).
POOLED filing-source (annual+mafresh+madrift+banked gptholdout-100): **precision 171/176 = 97.2%
(97.7% cell-level), recall 171/188 = 91.0%, YTD-misbinds 0** — within the ±5pt bar of every floor.
Quote spot audit 25 random emits: 24/25 byte-verbatim, 1 reconstructed row with correct real value.
DRIFT CENSUS FINAL (#766): full pool ~1,490 pairs scanned -> 6 true soft renames + 2 filer-tag errors
(0.5%); renames relocate fine (EOG NGLs, PFE footnote, MTCH marker, PSN, AA reorder all CORRECT).
Levers certified in-exam: batching + lean agent + hybrid addresses. CLEARED FOR #771.

## ENGINE = ChatGPT/Codex for #771 harvest (A/B CERTIFIED 2026-07-14)
User has a bigger ChatGPT account -> bulk harvest bills that, not the Claude sub. `codex_reader.py`
runs the IDENTICAL relocate_batch prompt via `codex exec -m gpt-5.5 --output-schema` (strict JSON,
per-gid checkpoint/resume). A/B on the frozen 111-case exam (same inputs Claude passed):
- Format: 79/79 valid strict JSON, 0 parse fails (fix: OpenAI strict mode needs ALL fields in `required`).
- Quality GPT-5.5 vs Claude (pooled filing 88 cases): 95.2%/90.9% vs 94.9%/84.1% — GPT-5.5 EQUAL/BETTER
  (higher recall). Annual: GPT 0 real wrong picks + 93.2% recall (beat Claude's 1 miss + 81.8%). Its only
  extra soft miss (KMT) = a broken truth entry (percent stored 0 via old int() bug), not a real error.
  madrift + transcript IDENTICAL to Claude (same 2 benign MDT filer-tag cases, same DAL adjusted trap).
- Model ladder (user): GPT-5.6 Sol Ultra/Max = hard escalation only; **GPT-5.5 = default reader**;
  GPT-5.6 Luna Max = simple steps. Run 5.5 first, escalate only failing strata.
CENSUS (all 637 cos, 0 tokens): 148,112 raw KPI-instances -> 73,267 addressable (in-corpus) ->
free code tier resolves 11,301 (~15.5%; T1-xbrl 6,596 + T2-label 4,705); LLM residual 10,237 cases ->
~1,947 batched calls -> **~78-101M ChatGPT tokens** for the filing lane (latest ~2-3 periods fiscal.ai
fills). Abstains: 45,270 derived (no quote can exist) + 5,010 value-absent + 1,412 plug. PR lane +
transcripts not yet wired (free scan first; est. +30-60M PR, ~150M transcripts = decide later).

## NEWS TRACK (separate process — user decision 2026-07-14)
News is NOT part of the locked source ladder anymore. Rationale (3 facts): retrieval shape differs
(pick-the-article vs find-the-cell), secondary-source noise (estimates/prior-year adjacent to actuals),
and its catalog role is the SURPRISE lane (actual-vs-consensus) + day-0 headline, not level extraction.
LOCKED baseline to beat: precision 100% (5/5, 0 traps), recall-of-present 5/18 (benchmark `news` set +
floor stay in regress.py as evidence). Design inputs archived in `news_track/` (GPT taxonomy/risks,
census: Earnings channel 16% hit-rate vs 3% base -> RANK never filter; actuals live in title+lead of
beat/miss wires; 16/34 values structurally absent from news). Reader + gates + ruler stay SHARED;
only fetch/orchestration/record-shape are news-specific. Next: dedicated brainstorm session.

## Deferred (seed-side, NOT relocation) — do with a certified-pipeline regression check
- **XBRL member-parser bug** (`link_lib.seg_members`): `explicitMember` can be a LIST of `{dimension,$t}`
  (multi-axis, e.g. OperatingSegments × GroceryAndSnacks) — current code only reads a single dict, so
  multi-axis segment facts parse to `[]`. **The naive ~4-line "loop over the list" fix is NOT safe:
  tested 2026-07-13, it BROKE 50 / 1761 certified T1 records (~3%).** Reason: parsing the extra members
  makes previously-invisible multi-axis facts (that used to return `[]`) collide at the same value with
  the single-axis fact, so `tier1` sees an ambiguous member tie and ABSTAINS → loses the clean match.
  So the real fix needs a COMPANION ambiguity resolver (prefer the member set that best/most-specifically
  matches the KPI slice, or dedupe same-value facts across axis-decompositions) — not a one-liner. Only
  worth it for the SEED side (free Lane-0 count = 5% on the text-relocation residual). Regression harness:
  `scratchpad/t1_regression.py` (re-runs tier1 on all certified T1 records; must show 0 BROKE before merge).

## Alignment with the LOCKED FinalDesign (audited 2026-07-13, 3 Opus readers)
Verdict: probe `kind/slice/units` are **COMPATIBLE-BUT-CRUDER retrieval aids**, LOW risk — they enforce the
distinctions that matter (won't bind wrong-kind/measurement/slice) and NEVER write typed identity.
- **Units:** probe's currency/count/percent = a coarse hint like the design's `unit_kind_hint`; NOT the final
  10-value enum (`usd/m_usd/percent…`). Per-X → base unit matches UNIT-08. `locate()` doesn't even use it. Guard: never let this become the stored unit.
- **Slices:** design = typed `kind:value`, 6 kinds (segment/product/geography/customer/channel/entity_ownership + unknown);
  period is NOT a slice; total = OMITTED slice (not `slice=total`); LLM never merges (over-split-safe). Probe = untyped
  word-bag naming 4 of 6 kinds — benign because scope is same-company + same-KPI + cross-period only (the design's
  cross-company/cross-axis hazard FS-08/FS-23 is out of scope). Probe emits no typed slice → can't corrupt identity.
- **Kind:** there is NO `metric_family` field/taxonomy. Identity = separate fields: `name` (revenue vs profit) ·
  `unit` · `measurement` (adjusted/organic/GAAP — NOT the name; GAAP = empty, read-time view) · `slice` · `fact_type`.
  Adjusted vs GAAP = SAME driver, DIFFERENT facts (measurement token). Probe's "don't swap" = correct for retrieval.
- **REQUIRED HANDOFF (pipeline's job, not the probe's):** a decomposition step must split the raw fiscal.ai name into
  `name / measurement / slice`, stamp `fact_type` (else DU-12 reject), and resolve the enum unit BEFORE any write.
  NEVER store the raw fiscal.ai name as `Driver.name` (violates NAME-10/14; re-creates the retired `adjusted_eps` defect, 95 #2).

## Known limits / next
- Annual only (quarterly leave-one-out infeasible: fiscal.ai free + Neo4j lag too thin).
- A–D companies, recent periods (oracle = fiscal.ai free values).
- Deep audit (Fable-5) pending: source-agnostic generalization (news/transcript), simplification,
  XBRL identity-fetch for financial-segment metrics. Apply changes ITERATIVELY, small-sample-checked.
