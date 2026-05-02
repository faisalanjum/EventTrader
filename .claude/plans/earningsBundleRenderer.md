# Earnings Bundle Renderer — Rendered-Primary Hybrid Architecture Plan

**Status**: Active audit — **18 commits shipped (17 main + 1 followup), 0 P0s open**, ~40 distinct fixes total. All 4 P0s + U45 + U22/U22a peer Option D + U61 assembled_at + U33 Yahoo session + U34 VIX live_mode + U35 SPY bars-provenance shipped 2026-05-01.
**Original date**: 2026-04-21. Last updated: 2026-05-01 (post U22+U22a+U23+U24+U26 ship; AVGO Q4 FY2023 historical smoke verified, all 4 §7 byte-equality goldens green).

**Math-semantic note (verified 2026-05-01 via live Cypher probe of `(:Report)-[pf:PRIMARY_FILER]->(:Company)`):** Peer sector/macro/industry fields on PRIMARY_FILER are RAW benchmark returns (e.g. `pf.daily_macro` = SPY's same-window return). There is no `*_adj` property on the relationship. Renderer computes adjusted values as `stock − benchmark` per horizon at render time; builder pre-computes `best_*_pct` from those ADJ values for predictor convenience.

**U22/U22a/U23/U24/U26 ship reference (commit `822d178`, 2026-05-01):** files = `scripts/earnings/builders/peer_earnings_snapshot.py` (Cypher OPTIONAL CALL with `pit_visible` boolean factoring + 4 helpers + per-horizon fail-CLOSED) and `scripts/earnings/renderer/peers.py` (per-peer Option D blocks with 3×3 matrix + defensive `_signed_pct`/`_sub`). Tests: `test_builders_peer_snapshot_u22a.py` (46), `test_render_peers.py` (48), 3 catalog regressions in `test_validate_prediction_u67.py`. Goldens: 4 fixtures × {bundle JSON, full render, sections/peers}. PIT semantics: historical mode is hard-gated everywhere (Cypher time filter + dual-gate periodic + per-horizon fail-CLOSED on returns); live mode passes through `pit_cutoff = now()` so all filed-before-now data is accessible, but per-peer `accession_periodic` still gated to peer's own filing time (matches U64 target behavior; deliberate design symmetry, not a restriction).

---

## Status Dashboard

**19 shipped commits** (all verifier-signed-off; 18 main + 1 followup):

| Commit | Section | Scope |
|---|---|---|
| `ff2e842` | §1.0 | header — accession_8k + prev_8k_ts + days-ago |
| `55829bd` | §1.1 | U1 fiscal-math is_current_quarter + 4-col Consensus Bar |
| `c392f52` | §1.1 | U7 related-filings sidecar + allowlist |
| `d6c6dc1` | §1.1 | U3 disambiguated empty-Consensus-Bar stubs (3 distinct messages) |
| `1ae9d5d` | §1.2 | U54 same-day cross-source guidance canonical collapse |
| `ed2cc32` | §1.3 | U8 forward_estimates schema + Δ columns |
| `fe2c2ce` | §1.4 | U12 derived_metrics derivation notes |
| `4adb5bb` | §1.1+§1.8 | U6 (items in 8-K) + U36 (Filing Metadata 4 fields) |
| `998b165` | cross | U64 mask post-PIT accession_periodic via Cypher gate (event-prefix preserves SEC date; +cross-check rejected as unsafe per corpus validator) |
| `b798e33` | cross | U65 scope context_bundle.json to save_dir, not save_dir.parent (one-line fix; no race in parallel runs) |
| `9f6749b` + `20d9ea2` + `ddf0df7` | cross | U67 event-scoped source_id grounding (Tier M+/C). Catalog walks real bundle structures (days[].events, catalysts pairs, series); rendered N{i}/F{i} aliases; macro `earlier` shape; `_close_run` gate on `prediction_validated`; legacy/offline markers in 5 external scripts |
| `5f4864f` | §1.10 cross | **U45+U66+U46+U48+U53 bundled**: ## Lessons To Label / ## Context-Only split + flat L1..Ln + verbatim-from-rendered SKILL.md (5 edits) + shared `iter_labeled_lessons` generator (drift-impossible by construction) + bundle.py empty-case fix caught by CRM smoke |
| `624317c` | §1.10 followup | **U45+U66 followup**: purged stale SKILL.md ref at line 112 (## Output section example block — separate from Phase 0 example caught in `5f4864f`); regen 13 degraded goldens after bundle.py empty-case behavior change; updated stale comments in `_degraded_fixtures.py`. Caught by ChatGPT post-commit review. |
| `822d178` | §1.6 cross | **U22+U22a+U23+U24+U26 bundled**: peer Option D renderer rewrite + builder backfill. Cypher OPTIONAL CALL with `pit_visible` boolean factoring (PIT-symmetric accession_periodic + form_type_periodic gates); 4 new builder helpers (`_parse_pit_safe`, `_extract_bz_id`, `_adj`, `_max_or_none`); per-horizon + whole-schedule fail-CLOSED PIT-nulling with `summary.gaps` emission; math-max `best_*_pct` from ADJ values (U23); FY-mismatch tag re-surfaced (U26); defensive `_signed_pct`/`_sub` renderer formatters. 97 new tests (46 builder + 48 renderer + 3 catalog). 4 fixture goldens surgically regen'd (peer-section-only diffs). |
| `aafc4af` | §1.0 | **U61 surface `assembled_at`**: §1.0 Mode line gains `\| Assembled: <UTC ISO seconds>Z`. Defensive `_format_assembled_at` helper parses ISO via `datetime.fromisoformat` (with `Z`-suffix shim), normalizes non-UTC offsets to UTC via `astimezone`, drops microseconds. Rejects naive datetimes (no fabricated timezone provenance). Returns None on missing/None/non-string/empty/unparseable → segment omitted. 16 new tests. 25 mechanical golden regens (4 section/header + 4 full + 4 sha256 + 13 degraded). Zero bundle JSON changes. |
| `d12bb66` | §1.7 | **U33 Yahoo session leak fix**: replaced `effective_session = 'post_market' if use_yahoo else market_session` with `effective_session = market_session` in `builders/macro_snapshot.py:406`. Live freshness still flows through minute bars; only the unsettled DAILY bar is no longer treated as settled for pre/in market. Live Yahoo probe at 2026-05-01 confirmed: pre-fix yahoo+pre_market → SPY today_return=+0.66% leaked from partial intraday close; post-fix → today_return=None. 3 new builder tests + 1 adapter-contract test. Polygon path unchanged. |
| `f4a45ce` | §1.7 | **U34+U35 macro polish**: U34 decouples VIX branch from `use_yahoo` to explicit `live_mode` parameter (`bool \| None = None` with backward-compat inference for legacy direct callers; adapter uses `kwargs.pop` pattern; CLI captures `original_pit` before `--pit now` conversion). U35 adds SPY-specific provenance annotation `Bars: SPY minute≤PIT−60s, SPY daily settled through DATE` under §1.7 header (new `last_settled_date` field on `market_now.spy`). 14 new tests across builder + adapter + CLI matrices. Bundle JSON surgical patch (deterministic dates, no API calls). 12 mechanical render golden regens. Zero Polygon rebuild risk. |
| _<U17 commit>_ | §1.5 | **U17 IQ news bz_id surfacing**: builder duplicates `_extract_bz_id` helper (mirror of peer_earnings_snapshot.py); news event dict gains additive `bz_id` field. Renderer (`renderer/inter_quarter.py:_iq_news_table`) Ref cell becomes `f"N{i} [bz:{bz}]"` when bz_id present; falls back to bare `f"N{i}"` when None. Closes the §1.5 gap that prevented cross-section narrative connection (e.g., same Benzinga article rendered in §1.6 peer headlines or §1.7 macro catalysts now visibly identifiable in §1.5). 9 new tests (4 builder + 4 renderer + 1 U67 regression pinning that no `#S6.news.bz:` aliases creep into catalog). Surgical bundle JSON patch (172 additive `bz_id` fields across 4 fixtures + 31 in FIVE warmup-cache fixture; pure function, zero API calls). 12 mechanical render goldens regen'd (4 inter_quarter section + 4 full + 4 sha256). Zero degraded fixtures touched (all have null IQ context). KLAC fresh-ticker production smoke confirmed: `N1 [bz:48511817]` rendered correctly, catalog clean of bz: drift, predictor cited 0 synthesized `#S6.news.bz:` source_ids. Architectural note: ChatGPT-proposed renderer fallback parse rejected as layer-violation; ChatGPT's sys.path.insert + utf-8 encoding nits accepted. |

**Open queue (principled order)**: **U32+U57** (macro gaps surfacing) → §1.5/§1.7/§1.12 walks → §1.11 final integration smoke → remaining MEDIUM/LOW follow-ons (U4/U10/U13/U14/U18-U21/U31/U55). All P0s + U45 + U22/U22a/U23/U24/U26 + U61 + U33/U34/U35 + U17 closed (shipped 2026-05-01). **U30 + U59 dismissed 2026-05-01** as editorial filtering of PIT-compliant data with no codebase precedent.

**Hybrid contract**: predictor receives both `RENDERED_BUNDLE_PATH` + `BUNDLE_PATH`; rendered = primary reasoning surface, JSON = verification-only.

**Production smokes (2026-05-01)** — 4 fresh-ticker production runs against shipped code:
- **U67 grounding** (3-ticker parallel): AAPL Q4 FY2023 (922 anchors, 18 ledger entries, 11 distinct source_ids, all 7 contract checks ✓) + CRM Q3 FY2024 (193 anchors, 29 entries, all ✓) + NVDA Q3 FY2024 (278 anchors, 28 entries, all ✓). AVGO ∩ AAPL ∩ CRM ∩ NVDA event-prefix overlap = 0.
- **U45+U66 lesson contract**: AVGO Q4 FY2023 (rich, 6 L# markers — predictor copied L1-L6 verbatim, all 8 contract checks ✓) + CRM Q3 FY2024 v2 (empty case after bundle.py fix, all 7 ✓ — caught + fixed empty-case render gap).
- **Smoke success definition**: "working exactly as desired" means **pipeline integrity first** — bundle builds, rendered text contains the expected sections/markers, validator contracts pass, no cross-run contamination, and gap/error surfaces are explicit. Direction accuracy, confidence calibration, and actual-return quality scoring are a **separate second pass** with an explicit rubric; do not mix subjective prediction quality into structural smoke acceptance.
- **Production-smoke builder gate**: fresh production smokes must have `builder_errors` empty/null. Renderer `[BUILDER ERROR: ...]` branches and degraded goldens prove graceful degradation, but they are not a passing bar for ordinary production smoke unless the smoke is explicitly a degraded-fixture test.
- **Production-smoke learn scope**: default smoke wave is `--predict` only. `--learn` uses post-actual-return attribution/quality surfaces and should run only in a separate learner/quality smoke when explicitly requested, even for historical fixtures where actuals already exist.

**Earlier 7-ticker E2E smoke (2026-04-30, archived)**: 8/8 renderer fixes ✅ across 70 section walks; 4/7 clean predictor outputs; 3/7 surfaced new P0s (U65 race, U66 hallucination, U67 validator gap) — **all four resolved in 5f4864f / 998b165 / b798e33 / 9f6749b chain**; U64 leak universal 7/7 — closed.

**Out-of-scope this audit**: `context_bundle.json` schema (only frozen-field-additions: U67 added `evidence_source_catalog`, U45 added `_allowed_learner_paths` — both scoped additions on builder-gap escalation); validator logic for non-U67 features (unless explicitly opened); learner skill body and learner pipeline (read-only); segment operating-income split (future pass).

**How to add new U#s post-compression**: every new U# gets a registry row (mandatory) + a detail block IF severity is HIGH or P0. LOW/COSMETIC = row only. Preserve any NEEDS-USER-INPUT flag and unique example inline.

**Active contract dependencies**: ~~§2 SKILL.md (active for U45+U66 bundle)~~ → done in `5f4864f` (5 edits) + `624317c` (one missed Output-section example caught by post-commit review); §3 orchestrator prompt — done implicitly via U67's `expected_source_ids` kwarg + U45's `expected_lesson_texts` already wired; §4 doc sync (this update); §5 hybrid test convention — preserved (**145/145 + 5 subtests passing** including the 13 degraded scenarios regen'd in `624317c`).

**Refactor handoff warning**: before any "lean codebase" or rearchitecture pass, read `/home/faisal/EventMarketDB/.claude/plans/refactor-safety-contract.md`. Many recent checks look removable in isolation but are load-bearing (U64 PIT masking, U67 source_id grounding/quarantine, U45/U66 lesson ordering, degraded goldens). A pure refactor must be behavior-preserving and golden-byte-identical unless the user explicitly approves an output change.

**New-bot first-action gate**: if you are a fresh agent with limited prior context, do not edit any file yet. First read `/home/faisal/EventMarketDB/.claude/plans/refactor-safety-contract.md` in full, then reply with: (a) a one-paragraph paraphrase of the U64 gate-only strategy and why the rejected PIT-bound/cross-check approach was unsafe, (b) the 4 smoke fixture tickers and what each exercises, (c) 5 high-risk items from the "Common Bad Refactors" list in your own words, and (d) the required order now that U22/U22a, U61, U33-U35 shipped and U30+U59 dismissed: U32+U57 → U17 → §1.5/§1.7/§1.12 walks → §1.11 → refactor. Wait for user approval before editing.

**Fresh-agent clarifications from 2026-05-01 doubt pass**:
- **U22a peer periodic must follow U64 gate-only semantics**, not the rejected hard-WHERE PIT strategy. Select the latest matching peer periodic by `periodOfReport`, return a PIT-gated `accession_periodic` via `CASE WHEN q.created <= peer_r.created AND q.created <= $pit_cutoff THEN q.accessionNo END`, and do **not** expose raw `matched_accession_periodic` in the peer bundle.
- **U30 + U59 dismissed 2026-05-01** — pre-results expectation articles are PIT-compliant context, not pollution. Editorial title-pattern filtering would be a new filter class with no codebase precedent (all existing filters are structural: PIT, channel taxonomy, schema gates). Do NOT reintroduce title-pattern filtering for peer headlines or IQ news without revisiting this decision.
- **U67 per-peer headline anchors are optional**. Existing `#S7.peer.<TICKER>` anchors are sufficient for event-scoped grounding; add finer `#S7.peer.<TICKER>.headline.bz:<id>` anchors only if implementation evidence shows predictor needs exact headline-level citations.
- **U65 follow-up footgun**: `get_learning_paths(save_dir=...)` still has the old symmetric branch because no current caller passes `save_dir`; do not introduce such a caller without applying the U65 scoping fix + test there.
- **Compatibility shims are intentional**: `earnings_orchestrator.py` re-exports `render_bundle_text` for legacy tests/A-B harnesses; do not delete that shim in a cleanup unless all callsites are migrated and tests pass.
- **`scripts/earnings/_text_utils.py` location is pinned** for now. `iter_labeled_lessons` is shared by renderer + U67 catalog; do not move or inline it during U22/U33 work.
- **Test layout is intentionally dual**: active tests live as `scripts/earnings/test_*.py`; fixtures/golden capture helpers live under `scripts/earnings/tests/`. Do not reorganize test paths during correctness work.
- **SKILL.md stale-pointer guard**: positive instructions to read lessons from `bundle.learning_context` or `predictor_lessons[i]` are forbidden; negative warnings ("do NOT pull") and `_allowed_learner_paths` equivalence are allowed.
- **U33 historical-safety depends on adapter source selection**: before simplifying macro source-selection code, verify the historical `pit_cutoff` path still forces Polygon and does not enter Yahoo's live `post_market` branch.
- **U61/R1 ✅ shipped 2026-05-01** (`aafc4af`): `assembled_at` surfaced in §1.0 line 4 as `| Assembled: <UTC ISO>Z`. §1.12 PIT provenance pass remains open for cross-section first-line annotations.

## Decisions (locked)

1. **Hybrid arch** — both paths in predictor prompt; neither dropped.
2. **Phase 0 source of truth** — `## Lessons To Label` rendered (NOT JSON; JSON-fallback re-introduces prefix-bashing).
3. **Learner links** — every lesson carries `learner_result:` line, path `earnings-analysis/Companies/{src_ticker}/events/{quarter_label}/learning/result.md` (relative); omit line if file missing; predictor MAY read.
4. **Current-quarter PIT-guard** — assert `(src_ticker, quarter_label) != (current_ticker, current_quarter_label)` before emitting any `learner_result:` link.
5. **Evidence-ledger citation** — `source: "learner_file:<path>"` when citing learner; validator allowlist extends.
6. **Peer earnings format** — per-peer block (Option D); 3 horizontal lines (raw / sector-adj / macro-adj).
7. **Global-lesson paths** — one path per lesson via `source_ticker` + `quarter_label`.
8. **Obsidian** — plain relative paths; NO `[[…]]` wiki-link syntax.
9. **R1** — surface `assembled_at` in rendered (REVERSED from earlier "never surface"); freshness signal + provenance anchor.
10. **R2** — segment revenue split DONE in §1.4.
11. **Intentional drops, do NOT add**: `schema_version`, `fye_month` (derivable), `quarter_identity_source`.
12. **Deferred (out of audit)**: segment operating-income split.
13. **R3 RESOLVED** (`5f4864f`) — 4 learner-output fields (`what_worked`, `what_failed`, `predicted_confidence_score`, `primary_driver_summary`) → `## Context-Only` compact sub-block under each ticker source event (per ChatGPT decision; one bullet per list item for `what_worked` / `what_failed` arrays).
14. **R4 — Empty `related_tickers`** (`5f4864f`) — cross_ticker scope with `related_tickers=[]` renders bare `L#.` (no `[cross:]` tag) — empty list is noise without info.
15. **R5 — Flat L# numbering** (`5f4864f`) — `lesson_labels[]` is one positional array; renderer emits `L1..Ln` flat across all lesson types (ticker → sector → macro → cross_ticker), shared with U67 catalog `#S10.lesson.L#` via `_text_utils.iter_labeled_lessons`.
16. **R6 — Empty-lessons rendering** (`5f4864f`) — `## Prior Lessons (from learner)` heading + `No prior lessons available` message ALWAYS renders, even when both lesson lists are empty (caught by CRM Q3 smoke). Predictor sees explicit "section was checked" signal.

## Design principles + Goal

- Don't pass both files as duplicated context; both available; rendered = primary, JSON = verification-only.
- **Goal**: rendered bundle is lossless for predictor's primary reasoning surface; JSON serves exact-precision verification of consensus precision, quarter_info, builder_errors.

## Known builder gaps

- **Peer-earnings JSON** missing `session_macro_pct`, `session_sector_pct`, `accession_periodic`, `is_amendment` (U22a backfills these).
- **Peer headlines + IQ news events**: only `news_id` with `bzNews_<n>` prefix; no separate `bz_id` (U17/U25 cluster).

---

## U-Entry Master Registry

Every U-item appears exactly once in this registry (the authoritative source). Detail blocks for HIGH+/P0 follow below. Shipped rows are self-contained — no `git show` dependency.

| ID | § | Sev | Status | Site | Action / Spec | Notes / Test |
|---|---|---|---|---|---|---|
| U1 | §1.1/§1.3 | HIGH | ✅ `55829bd` | builders/consensus.py:707 | Fiscal-math + 4-col table; new `_provider_fde_for_period(period_of_report, fye_month, form_type_periodic)` derives AV-convention FDE, pre-scans rows, falls back to strict equality. Adds 4-col `Estimate \| Actual \| Surprise` Consensus Bar. | Files: consensus.py, adapters.py, renderer/results.py, _formatters.py. 23 unit + 502 adapter + 10 retry tests green. **TODO 2026-04-30**: live-AV spot-check on AAPL/CSCO/ROST/ADBE (deferred — AV rate-limited 2026-04-29). |
| U2 | §1.1 | — | ⚪ DEFERRED-WONTFIX | renderer/results.py:28-43 | Naive `fwd[0]` would mislabel next quarter as current event — worse than stub. §1.3 forward-estimates table provides graceful degradation. | Code marker at fallback site; revisit if at-release-with-AV-lag becomes primary workflow. |
| U3 | §1.1 | HIGH | ✅ `d6c6dc1` | renderer/results.py:28-43 | 3 distinct stub messages: U1-fiscal-mismatch (now resolved by U1), U2-pre-event (deferred), AV-upstream-failure → `[Consensus unavailable — AV upstream failed: <reasons>]`. | 14 files +77/-21. AV-fail goldens regenerated. |
| U4 | §1.1 | MEDIUM | 🟡 OPEN | renderer/results.py | Surface `consensus.gaps[]` (currently §1.3 only). Print `Data notes: <reasons>` when current_row.revenueEstimate=null OR gaps include `missing_revenue_estimate` for current quarter. | Predictor cannot calibrate confidence on consensus completeness from §1.1 alone. |
| U5 | §1.1 | MEDIUM | 🟡 OPEN | renderer/results.py:53-54, :88-92 | EX-99.1 only in §1.1; non-EX-99.1 routes to §1.8. NVDA Q3 FY2025 has EX-99.2 (16KB segment recon). Two design options: (A) render all EX-99.x in §1.1; (B) emit pointer line `Note: additional financial data in §9 Reference (EX-99.2)`. **User to choose.** | Affects multi-exhibit tickers (NVDA, sometimes AVGO YE). |
| U6 | §1.1 | HIGH | ✅ `4adb5bb` (with U36) | renderer/results.py:83-98 | `Other items in this 8-K: Item 2.05 (Cost...), Item 8.01 (Other Events)` line between Consensus Bar and EX-99.1, only when items contains non-{2.02, 9.01}. Routine filings → line omitted. | Files: renderer/results.py. 7-ticker smoke verified: AVGO renders correctly; CRM/BURL/ADBE/NVDA/TSLA all routine, line correctly omitted. |
| U7 | §1.1 | HIGH | ✅ `c392f52` | builders/inter_quarter_context.py:169-280, :705-1148; renderer/inter_quarter.py:178,194,290-296 | Related-filings sidecar — pre-fetches sections + ALL exhibits + filing-text fallback for selected related 8-Ks; per-accession markdown to `events/{Q}/related_filings/{accession}.md`; §6 Content column + allowlist block. Filter rule: 8-K/A always include; 8-K include UNLESS items=={9.01} + no exhibits; missing/unparseable items → INCLUDE; non-8-K → SKIP. | Files: inter_quarter_context.py, adapters.py, orchestrator.py, renderer/inter_quarter.py, results.py, SKILL.md, test_builders_inter_quarter_related_filings.py (408 lines, 26 tests), 12 golden fixtures. `exclude_accessions={target}` prevents PIT leak. |
| U8 | §1.3 | CRITICAL | ✅ `ed2cc32` | renderer/consensus.py:69-89 | Renderer keys aligned to builder schema: `period→fiscalDateEnding`, `eps_estimate_current→epsEstimateAverage`, `eps_estimate_NdAgo→epsRevisionNdAgo`, `revenue_estimate_current→revenueEstimateAverage`. Added 60d column, Δ30d/Δ90d signed, EPS+Rev Analysts, period horizon tag `(Q)/(FY)`. | Files: renderer/consensus.py, _formatters.py (+_fmt_eps_delta). 6 new tests; 273 tests green. Pure-renderer fix; was 100% data loss in live mode pre-fix. |
| U9 | §1.3 | LOW | 🟡 OPEN | renderer/consensus.py:34-38 | Beat-streak summary off-by-one: `Summary: 8 EPS beats in last 8 quarters` while table shows 7 prior (current excluded post-U1). Fix: prior-only streak/count OR rephrase to "8/8 last-8-quarter beat streak (current incl.)". | Cosmetic. |
| U10 | §1.3 | MEDIUM | 🟡 OPEN | renderer/consensus.py:52-60 | `revenueSurpriseQuality` ("approximate" vs "live") + `reportedDate`/`reportTime` not rendered. Predictor treats historical PIT-approximate as exact at-release wire → over-confident. Fix: footer line per table or "(approximate)" tag; could fold into §1.12. | Calibration-lens-only Tier S. |
| U11 | §1.3 | LOW | 🟡 OPEN | renderer/consensus.py:78-80 | `gaps[]` not deduplicated. 4 missing-revenue-estimate quarters → 4 identical tokens. Fix: dedup by (type, reason); collapse with FDE list. | Edge case; not observed in fixtures. |
| U12 | §1.4 | HIGH | ✅ `fe2c2ce` | renderer/financials.py:91-124 (new `_render_derivation_notes`) | `### Derivation notes` block per quarter that has derivations. Source: `quarters[].derived_metrics` (NOT `_provenance` — see Ambiguity B). Format: `<metric>: derived via <method>, inputs: <role> from <accession> (<form>), …`. Quarters with no derivations omitted; all-empty section omitted. | Files: financials.py. 6 new tests; 12 fixtures regenerated (4 full + 4 sha256 + 4 financials sections). Plan §1.4 marquee. AVGO/AVGO Q4/CHRW/CXM each have 2/4/29/35 derived metrics. |
| U13 | §1.4 | MEDIUM | 🟡 OPEN | renderer/financials.py:143-144 | Empty/failed quarters render as silent `—` rows; `Data notes: 13 gaps in packet` collapses reasons. CRM Q4_FY2023 has 12 metrics with reason `Q4 derivation failed: annual=True, 9m_ytd=False`. Fix: group `gaps[]` by `period`; emit per-quarter notes. | Predictor can't calibrate which quarters are unreliable. |
| U14 | §1.4 | MEDIUM | 🟡 OPEN | renderer/financials.py:111-116 | Per-quarter `primary_source`/`primary_form`/`primary_accession` hidden; only aggregate `Sources: xbrl=5, fsc=2`. With `--allow-yahoo`, Yahoo quarters mix silently. Fix: column-header decoration `Q2_FY2024 (fsc)` or per-quarter source line. | Yahoo-fallback transparency; PIT-audit traceability. |
| U15 | §1.4 | COSMETIC | 🟡 NEEDS-USER-INPUT | builders/prior_financials.py revenue-split label derivation | Segment label spacing: AVGO `Subscriptionsand Services`; CRM `Subscriptionand Support`. `*Member` qnames space-stripped at ingest. Fix at XBRL ingestion or builder regex re-spacing. | Cosmetic. |
| U16 | §1.4 | COSMETIC | 🟡 NEEDS-USER-INPUT | builders/prior_financials.py segment_inventory builder | AVGO `segment_inventory.revenue.axes` includes `unknown_axis` mixing business+product members. Splits build correctly per `kind`; metadata partially miscategorized. | Observability only. |
| U17 | §1.5 | MEDIUM | ✅ SHIPPED 2026-05-01 | builders/inter_quarter_context.py + renderer/inter_quarter.py | Builder duplicates `_extract_bz_id` helper (mirror of `peer_earnings_snapshot.py:158-168`, identical body + docstring callout to source-of-truth); news event dict gains additive `bz_id` field at construction site (line ~885). Renderer `_iq_news_table` Ref cell now `f"N{i} [bz:{bz}]"` when `bz_id` present, falls back to bare `f"N{i}"` for None. Schema-additive only — no removed/renamed fields. Audit row's "broken cross-section refs `[N68 \| bz:35906540]`" claim was disproven during investigation (no renderer constructs cross-section links anywhere); U17 actual scope is §1.5/§1.6/§1.7 render consistency. ChatGPT-proposed renderer fallback parse REJECTED as layer-violation (would force renderer→builder helper import; §1.6/§1.7 don't fall back). U67 catalog explicitly NOT extended — predictor continues to cite via canonical `#S6.news.N{i}` form per SKILL.md:150. | Files: 2 production files. 9 new tests (4 builder + 4 renderer + 1 U67 catalog regression test pinning that no `#S6.news.bz:` aliases creep in). Surgical bundle JSON patch (172 fields across 4 audit fixtures + 31 across FIVE warmup-cache fixture; pure function, zero API calls; sys.path.insert pattern matches `macro_snapshot.py:51-54`). 12 mechanical render goldens regen'd (4 inter_quarter sections + 4 full + 4 sha256). Zero degraded fixtures touched (all have null IQ context). KLAC fresh-ticker production smoke (2026-05-01): `N1 [bz:48511817]` rendered, 0 catalog drift, predictor cited 0 synthesized `#S6.news.bz:` forms. Full pytest baseline 1131 → 1140 (exactly +9 new). |
| U18 | §1.5 | MEDIUM | 🟡 OPEN (DOWNGRADED scope 2026-04-30 — renderer-only) | builders/inter_quarter_context.py:38-39 (Cypher) + renderer/inter_quarter.py:90-110 | `industry_return` column missing from Trading Days. **2026-04-30 verification**: graph HAS 43,141 `Date-[HAS_PRICE]->Industry` rels (original audit's "no edges" claim was wrong). Renderer-only gap — possible builder Cypher join tightening if `(d:Date)-[:HAS_PRICE]->(ind:Industry)` doesn't reach correct industry node for ticker. | ~half original scope. |
| U19 | §1.5 | MEDIUM | 🟡 OPEN | renderer/inter_quarter.py:119-131 | Per-event `adj_sector`/`adj_industry` hidden in §6 News+Filing tables (only `adj_macro` extracted). Predictor cannot distinguish sector-cohort from idiosyncratic. Fix: append `(sec −X.XX%, ind −Y.YY%)` after adj_macro, or 3 more columns. | — |
| U20 | §1.5 | MEDIUM | 🟡 OPEN | renderer/inter_quarter.py:85-116 | `price_role` and cutoff prices unlabeled. Boundary day either renders prices (role=ordinary, PIT-safe) or `—` (role=reference_only, PIT-nulled). Fix: add `price_role` to header summary or annotation; markdown renderer parity with text path (L575-590). Affects BURL 2024-11-26. | Calibration-lens-only Tier S. |
| U21 | §1.5 | COSMETIC | 🟡 OPEN (DOWNGRADED from MEDIUM) | renderer/inter_quarter.py:74 | "67 trading days" in header vs 69 `Y` rows in table (67 ordinary + 2 boundaries). Cosmetic naming. | — |
| U22 | §1.6 | HIGH | ✅ SHIPPED 2026-05-01 | renderer/peers.py (full rewrite) | Per-peer Option D block format: H3 header (ticker/filed/session/accession + optional FY-mismatch tag) → optional Periodic line → optional [8-K/A amendment] marker → 3-line 3×3 matrix (Stock move / Sector-adj / Macro-adj × Day/Sess/Hour with Best on adjusted lines, computed via `_sub` at render time) → Headlines list with `[bz:<id>]` tags. Defensive `_signed_pct` and `_sub` helpers handle None/string/NaN gracefully. Math semantics: bundle stores RAW pf.* values; renderer subtracts at render time per the 2026-05-01 Cypher probe finding. | Files: renderer/peers.py. 48 new tests in test_render_peers.py. 4 §7 byte-equality goldens regen'd; only §7 region differs across full goldens (sha256 changes confirmed isolated). AVGO Q4 historical smoke matched fixture peers exactly. |
| U22a | §1.6 | HIGH | ✅ SHIPPED 2026-05-01 (with U22) | builders/peer_earnings_snapshot.py (Cypher + Python) | Cypher OPTIONAL CALL inserted between line 41 MATCH-WHERE and line 42 OPTIONAL MATCH (preserving r/peer scope). Adds: `pf.session_sector`, `pf.session_macro`, `r.isAmendment`, plus per-peer PIT-gated `accession_periodic` + `form_type_periodic` via `pit_visible` boolean factoring (gates symmetrically — release-blocker per ChatGPT review). Python adds 4 new helpers (`_parse_pit_safe`, `_extract_bz_id`, `_adj`, `_max_or_none`), per-horizon fail-CLOSED PIT-nulling, whole-schedule fail-CLOSED with `summary.gaps` emission, math-max `best_*_pct` from ADJ values, bz_id injection per headline. Does NOT expose `matched_accession_periodic` (peer-side intentionally drops the raw vs U64 target ticker). | Files: builders/peer_earnings_snapshot.py. 46 new tests in test_builders_peer_snapshot_u22a.py. Live AVGO Q4 builder run confirmed all 5 peers populate new fields correctly; gates correctly null accession_periodic when periodic 10-Q filed minutes after peer's 8-K. |
| U23 | §1.6 | MEDIUM | ✅ SHIPPED 2026-05-01 (with U22a) | builders/peer_earnings_snapshot.py:_max_or_none + _adj | `best_sector_pct` / `best_macro_pct` semantic switched from prefer-daily-fallback to math max across non-null ADJ horizons. Anti-zero-artifact: returns None (not 0.0) when all horizons null. NVDA AVGO-Q4 example: best_macro = max(daily_adj=-2.84, session_adj=+3.25, hourly_adj=+3.02) = +3.25. | Test `test_best_pct_computed_from_adjusted_values_not_raw` pins the semantic; ensures we're not just taking max of raw benchmark returns. |
| U24 | §1.6 | — | ✅ RESOLVED-BY U22 (vanished with rewrite) | renderer/peers.py | Misleading `AdjH%/AdjD%` column labels removed. New format has explicit row labels (`Stock move:`, `Sector-adj:`, `Macro-adj:`) and `Best` cell on adjusted lines only. | — |
| U25 | §1.6 | — | ⚪ DUPLICATE-OF U17 | builders/peer_earnings_snapshot.py | `bz_id` not separated from `news_id`. Same root cause as U17. macro_snapshot.py:551 already emits clean bz_id — peer builder follows same pattern. | — |
| U26 | §1.6 | LOW | ✅ SHIPPED 2026-05-01 (with U22) | renderer/peers.py | FY-mismatch tag added to per-peer block header: appended `(FY ends Jan)` / `(FY ends Sep)` etc. when peer's `fy_end_month` ≠ target's `quarter_info.fye_month`. Defensive: omitted when either side is None or unparseable. AVGO-Q4 smoke verified: NVDA (Jan), QCOM (Sep), AMD (Dec), TXN (Dec), ADI (Nov) — all 5 differ from AVGO's Oct, all 5 tags rendered. | Tested in 5 cases: matched (no tag), mismatched (tag), target fye None, peer fye None, peer fye unparseable. |
| U27 | §1.6 | LOW | 🟡 OPEN | peer_earnings_snapshot.py:217-219 | Peer-list pruning silently drops to <top_n on small industries. BURL Apparel-Retail returned 4/5. Fix: emit `peers_filtered_count`/`industry_universe_size`. | Observability. |
| U28 | §1.6 | COSMETIC | 🟡 OPEN (DOWNGRADED from MEDIUM) | `_parse_mkt_cap` | Naïve string compare; null/zero treated identically. Cypher pre-filters NULL so benign today. Latent. | — |
| U29 | §1.6 | LOW | 🟡 NEEDS-USER-INPUT | Cypher `BELONGS_TO->Industry` exact match | Industry-only similarity; cross-industry peers excluded (e.g. SoftwareApplication vs SoftwareInfrastructure for CRM). Design question. | Future enhancement. |
| U30 | §1.6 | MEDIUM | ❌ DISMISSED 2026-05-01 | peer_earnings_snapshot.py headlines query | Original framing: pre-filed "Likely To Report"-style articles leak into peer headlines via the 18h pre-window + broad "Earnings" channel; predictor mistakes speculation for reaction. **Dismissal rationale**: articles in the current window are PIT-compliant (all `n.created < $pit_cutoff`); pre-results expectation pieces are legitimate context (market's prior beliefs going into the print), not pollution. Predictor sees title + timestamp and can distinguish forward-looking speculation from a reaction. Codebase precedent: zero existing builders use editorial title-string filtering — all filters are structural (PIT, channel taxonomy, schema gates). Introducing English-text-pattern exclusion would be a new filter class with no prior art and would impose editorial judgment over genuine information. | Data probe (2026-05-01): ~6% of peer headlines are pre-results previews (3/50 in AVGO Q4 window). NXPI counter-example: legitimate result articles publish 13h BEFORE SEC filing via Business Wire — proves "post-filing only" rule is unsafe. Title-pattern alternative considered (6 patterns, ~1.4% FP rate) but rejected as editorial filtering with no codebase precedent. Same shape as U52 (lessons de-dup kept by design) and U18 (audit row premise wrong on data check). |
| U31 | §1.7 | LOW | 🟡 OPEN (NOT a duplicate of U17 — different fix path) | renderer/macro.py:119-149 | Macro Catalysts BzID column missing. Builder ALREADY emits clean `bz_id` (macro_snapshot.py:551). Renderer additive — append `BzID` to `cat_headers` + `_iq_val(h.get("bz_id"))` to each row. No builder change needed. | Plan §1.7 explicit requirement. |
| U32 | §1.7 | MEDIUM | 🟡 OPEN | renderer/macro.py:12-151 | `macro_snapshot.gaps[]` warnings never surfaced. AVGO Q4 fixture `gaps=[{"type":"missing_spy_data",…}]` but rendered §8 prints all 14 SPY cells `—`. Predictor reads "no movement" instead of "fetch failed". Fix: `Data notes: <reason>` line under header when gaps non-empty. | Calibration-critical. |
| U33 | §1.7 | CRITICAL (live pre_market) / LOW (historical) | ✅ SHIPPED 2026-05-01 | builders/macro_snapshot.py:406 | Removed `effective_session = 'post_market' if use_yahoo else market_session` override; replaced with `effective_session = market_session`. Live freshness still flows through minute bars (level_at_pit / open_to_pit / last_60m); only the unsettled daily bar is no longer treated as settled for pre/in market. **Live-data probe (2026-05-01 12:03 ET, real Yahoo)**: pre-fix yahoo+pre_market → SPY today_return=+0.66% (leaked yesterday→today partial close); post-fix → today_return=None, indicator+sector labels='last close'. Polygon path unchanged. | Files: builders/macro_snapshot.py. 3 new tests in test_builders_macro_snapshot.py (yahoo+pre/in/post matrix); 1 adapter-contract test in test_builders_adapters.py (defaults polygon historical, yahoo live). Zero golden changes (all 4 fixtures use polygon). |
| U34 | §1.7 | LOW | ✅ SHIPPED 2026-05-01 | builders/macro_snapshot.py + builders/adapters.py | VIX branch decoupled from `use_yahoo` and now keys on explicit `live_mode` parameter. Builder gains `live_mode: bool \| None = None` with backward-compat inference (`yahoo + no caller-supplied session → True`); adapter passes `live_mode = kwargs.pop("live_mode", pit_cutoff is None)`; CLI captures `original_pit` before `--pit now` conversion and propagates `live_mode=(original_pit == 'now')`. Defensive against caller routing `live_mode` via `**kwargs` (uses `kwargs.pop` pattern matching existing `source = kwargs.pop(...)`). Live Yahoo probe at 2026-05-01 confirmed: defensive case `(yahoo, historical pit, live_mode=False)` → vix_label='last settled close' (was 'live'); live case → vix_label='live' preserved. | Files: builders/macro_snapshot.py, builders/adapters.py. 12 new builder/adapter/CLI tests covering full live_mode × source × session matrix + backward-compat inference. Zero golden changes from U34 (label change only triggers in defensive path). |
| U35 | §1.7 | LOW | ✅ SHIPPED 2026-05-01 | builders/macro_snapshot.py + renderer/macro.py | `_compute_spy_now` now exposes `last_settled_date` (post_market → pit_date; pre/in_market → previous trading day; None when no daily bars). Renderer adds new SPY-specific provenance line under existing 4-line header: `Bars: SPY minute≤PIT−60s, SPY daily settled through {date}`. Defensive `or '—'` fallback when missing. Bundle JSON regen via surgical patch script (deterministic dates, zero API calls — no Polygon rebuild risk). | Files: builders/macro_snapshot.py, renderer/macro.py. 4 new tests pinning post/pre/in market dates + None defensive. 12 mechanical golden regenerations (4 section/macro + 4 full + 4 sha256). Zero degraded changes (degraded fixtures lack `market_now.spy`). |
| U36 | §1.8 | HIGH | ✅ `4adb5bb` (with U6) | renderer/results.py:137-154 | Filing Metadata block extended: `CIK: <cik> \| Periodic: <accession_periodic> (<form_type_periodic>) \| Amendment: <yes\|no>`. Reads `8k_packet.cik`, `is_amendment`; `quarter_info.accession_periodic`, `form_type_periodic`. | Files: renderer/results.py. 3 new tests. **U64 PIT leak active**: §1.8 currently surfaces future-filed accession_periodic; U64 fix patches. |
| U37 | §1.8 | LOW | 🟡 OPEN | Same site as U36 | `quarter_info.gaps` not surfaced (conditional). All 4 fixtures have `gaps=null`; untestable until gap-bearing fixture exists. | Needs fixture. |
| U38 | §1.8 | LOW | 🟡 OPEN | builders/eight_k_packet.py:47 (`ORDER BY s.section_name`) | Section ordering alphabetic ("C, F, O, R" — AVGO renders 2.05→9.01→8.01→2.02) instead of Item-number. Fix: parse leading `Item X.YY` from content and sort by it; or pass `r.items` JSON ordering through. | Related to U58. |
| U39 | §1.8 | COSMETIC | 🟡 OPEN | renderer/results.py:127 | `**ResultsofOperationsandFinancialCondition**` (CamelCase, no spaces). Source is Neo4j space-stripped node. Fix: strip leading "Item X.YY" line from content and use as heading, or insert spaces with regex. | — |
| U40 | §1.8 | COSMETIC | 🟡 OPEN (DOWNGRADED from MEDIUM) | renderer/results.py:101 | `content_inventory.has_filing_text` flag not surfaced. If true but section/exhibit fetch suppressed `filing_text` body, predictor never learns fallback exists. Rare trigger. | — |
| U41+U42+U43 | §1.8 | TEST-DEBT | 🟡 CONSOLIDATED (single task) | renderer/results.py:111-117, :130-133 | Coverage gaps: U41 `exhibits_other` preview path (need EX-10.x fixture); U42 `filing_text` fallback path (need sections+exhibits-empty fixture); U43 `is_amendment=true` filings (need 8-K/A fixture). | Single "add coverage fixtures" task. |
| U44 | §1.8 | — | ⚪ DUPLICATE-OF U6 | renderer/results.py:92-95 | `items_short` drops directional Item labels ("Item 2.02" only, not "Cost Associated with..."). Fully covered by U6 surfacing material events in §1.1. | — |
| U45 | §1.10 | HIGH | ✅ `5f4864f` (bundled with U66) | renderer/lessons.py | Renderer rewritten: `## Lessons To Label (verbatim, in order)` with flat `L1..Ln` markers (clean bodies, no inline prefix; optional `[sector: X]` / `[macro]` / `[cross: T1,T2]` scope tag in marker line; bare `L#.` when `related_tickers=[]`) + `## Context-Only (not labeled)` with per-ticker R3 sub-block (predicted_confidence, primary_driver, what_worked, what_failed) + data_lessons + why + learner_result paths + `### Global lesson source events` mapping. Tuple element 2 (`ordered_lesson_texts`) byte-identical to pre-U45 (validator preserved). Shared `_text_utils.iter_labeled_lessons` generator drives BOTH renderer's L# numbering AND U67 catalog `#S10.lesson.L#` (drift-impossible by construction). Empty-case fix in `renderer/bundle.py` (caught by CRM Q3 smoke): `_render_learning_context` now always called so `## Prior Lessons` + "No prior lessons available" message renders even when both lesson lists empty. |
| U46 | §1.10 | HIGH | ✅ `5f4864f` (folded into U45) | renderer/lessons.py:60, :64 | Inline `- Predictor:` / `- Data:` prefix removed; lesson body is now clean L# block content. |
| U47 | §1.10 | — | ✅ `5f4864f` (folded into U45) | renderer/lessons.py:91/103/116 | Inline `[scope:..] (SRC)` prefix removed; scope tag now ONLY in L# marker line (`L4. [sector: X]`); body is clean. |
| U48 | §1.10 | — | ✅ `5f4864f` (folded into U45) | renderer/lessons.py | `L1.`/`L2.`/.../`L#` flat sequential markers added per U45 spec. |
| U49 | §1.10 | LOW | 🟡 OPEN | renderer/lessons.py empty-context path | "No prior lessons available (first prediction for this ticker)" misleading — could be PIT-filtered, not first prediction. Reword under split. | — |
| U50 | §1.10 | LOW | 🟡 NEEDS-USER-INPUT | renderer/lessons.py — global lesson formatting | Cross-ticker `related_tickers` + `target_sector` placement under split. Currently inline prefix `[cross:AVGO,QCOM,AMD,TXN] (AVGO)`. Decide: structured Context-Only line per lesson? | — |
| U51 | §1.10 | LOW | 🟡 NEEDS-USER-INPUT | — | Per-lesson vs per-quarter L-numbering. `ticker_lessons[i].predictor_lessons[]` is N strings. Each gets own `L<n>` (current tuple-element-2 implies per-string), or whole quarter gets one marker? | — |
| U52 | §1.10 | LOW | 🟡 NEEDS-USER-INPUT | — | Lesson de-duplication across scopes. Same body in both ticker and global → renders twice. Tuple-element-2 has duplicates (validator depends). | — |
| U53 | §1.10 | — | ✅ `5f4864f` (canonicalized via shared generator) | renderer/lessons.py + _text_utils.py | Ordering inside `## Lessons To Label`: ticker_lessons (array order, walking predictor_lessons[]) → sector → macro → cross_ticker. Now canonical via `_text_utils.iter_labeled_lessons` (single source of truth shared with U67 catalog). |
| U54 | §1.2 | HIGH | ✅ `1ae9d5d` | builders/guidance_history.py:107-132 (`_canonical_numeric_signature`); :367-389 (ckey rewrite) | Same-day cross-source guidance updates not collapsed → spurious "maintained" priors. New canonical numeric signature: mid-only / l=m=h / l=h+no-mid → `('point', value)`; genuine ranges → `('range', l, m, h)`. ckey now `(period_start, period_end, fy, fq, given_day, signature)`. | Files: guidance_history.py. 7 new tests; 359 tests green. BURL Q3 FY2025 canonical: 41→35 collapsed, all `new` (no spurious `maintained`). |
| U55 | §1.2 | MEDIUM | 🟡 OPEN | renderer/guidance.py:298,309,318 | Stale-guidance signal absent — `given_day` of current update never rendered. Predictor can't tell whether `Q2 FY2023 \| ~$8.70B \| — \| new` was 6mo ago or yesterday. Fix: `Updated` column or inline `(YYYY-MM-DD)`. | "Guidance History" appendix only fires at ≥3 updates per target — never triggers in any fixture. |
| U56 | §1.2 | HIGH | 🟡 NEEDS-USER-INPUT (BLOCKS §1.2 walk) | plan §1.2 spec vs builders/guidance_history.py:49,254 | Plan says `derivation` ∈ {company, xbrl} and Source `8-K §2.02` etc. Builder's `derivation` actually takes 6+ values (`point`, `floor`, `ceiling`, `comparative`, `explicit`, `implied`, `calculated`); `sources` is `['8k']`/`['transcript']`/etc. with NO §-level granularity. **Plan-author resolution needed.** Recommend: `sources` as Source column (1-3 source_type tags); `derivation` verbatim as Type column; defer §-level granularity. | Blocks §1.2 spec items 3+4. = Ambiguity A. |
| §1.2 collateral | §1.2 | various | 🟡 OPEN | renderer/guidance.py | Other plan-spec items (post-U56): prior-disambiguation `(first update)`/`(prior value unavailable)` — every first-update row renders bare `—`; `metric_id` prefix never on Metric label; xbrl_qname (89% pop'd) + evhash16 (100% pop'd) both never rendered; `total_updates_raw`, `raw_unit_variants`, `member_qnames`, `period_start`/`period_end` for non-Other rows all hidden. | Collateral when §1.2 walk happens. |
| U57 (M1) | §1.7 | MEDIUM | 🟡 OPEN | renderer/macro.py:62-66 | Empty SPY trend renders all 14 cells `—` with no `[BUILDER ERROR]` branch. Polygon-fail vs flat-market collapse. Predictor reads "no movement". Broader than U32 (gaps[] surfacing); affects even when gaps[] empty. Fix: error-state branch. | — |
| U58 (M2) | §1.8 | LOW | 🟡 OPEN | builders/eight_k_packet.py:47 | `items` array (Item-number order) vs alphabetic sections create render mismatch. AVGO renders C/F/O/R but Items: 2.02,2.05,8.01,9.01. Related to U38. | — |
| U59 (M3) | §1.5 | LOW | ❌ DISMISSED 2026-05-01 | builders/inter_quarter_context.py:58-85 (news query) | Original framing: "same channel-filter issue as U30" — preview-style articles inflate `total_news` count and pollute IQ narrative. **Dismissal rationale**: (1) the audit row was misframed — IQ query has NO channel filter; it's a pure time-window between filings, so there's no "channel-filter issue" to fix. (2) IQ news is PIT-compliant by construction (`prev_8k_ts < n.created < context_cutoff_ts`). (3) Pre-results expectation pieces ("Earnings Preview: Broadcom") are legitimate IQ context — the market's evolving expectations between filings are part of what shaped the current event's setup, not noise. (4) Same codebase-precedent argument as U30: no editorial title-pattern filtering anywhere in production builders. | Data probe (2026-05-01): AVGO Q4 IQ window = 73 articles, ~7% aggregator listicles ("$100 Invested 15 Years Ago..."), ~8% broad-Earnings recaps, ~85% legitimate analyst/M&A/regulatory news. Bare "likely to" pattern would have caused ~12% FP rate in IQ scope (drops "Broadcom CEO Says Co Did Not Lose Apple Deal", "Why Broadcom Shares Are Diving Following Apple News", analyst rating changes). Decision aligned with U30 dismissal — same logical shape. |
| U60 (M4) | §1.3 | LOW | 🟡 OPEN | builders/consensus.py:_build_summary (~L919) | `eps_beat_streak` builder-side analog of U9: streak across 8 rows incl. current; renderer renders 7. Decision: include current quarter in streak? | — |
| U61 (M5) | §1.0 | MEDIUM | ✅ SHIPPED 2026-05-01 | renderer/header.py | `bundle.assembled_at` now appended to §1.0 line 4 as `\| Assembled: <UTC ISO seconds>Z`. Defensive parse-and-normalize helper handles `Z` suffix variants, normalizes non-UTC offsets, rejects naive datetimes (no fabricated timezone provenance), and omits the segment when missing/None/non-string/empty/unparseable. Live smoke confirmed: `Mode: historical \| PIT cutoff: ... \| Assembled: 2026-05-01T15:47:53Z`. | Files: renderer/header.py (+12 LOC: import + `_format_assembled_at` helper + Mode-line restructure). 16 new unit tests in test_render_header.py (8 helper + 8 integration). 25 mechanical golden regen (4 section/header + 4 full + 4 sha + 13 degraded). Zero bundle JSON changes. |
| U62 (M6) | §1.3 | LOW | 🟡 OPEN | renderer/consensus.py:69-75 | Some `forward_estimates[].epsRevisionDelta*` fields still hidden after U8: **Δ30d and Δ90d already rendered** (added by U8); **Δ7d and Δ60d remain hidden**. Builder pre-computes all four (current minus N-day-ago). Fix: surface remaining 2 delta columns. | — |
| U63 (M7) | cross | LOW | 🟡 OPEN | builders/adapters.py:260, :270 | Live `effective_cutoff_ts` semantics inconsistent across builders (peers/macro use `_now_iso()`; inter_quarter uses filed_8k; others null). Per N1, 3 different meanings. Fix: settle on one OR rename per-builder fields. | See N1. |
| U64 | cross | P0 | ✅ `998b165` | quarter_identity.py:45-58 (`_QUERY`) | Cypher CASE WHEN gate hides matched periodic accession when `q.created > r.created` (post-PIT); raw `matched_accession_periodic` returned for internal denylist/XBRL logic; preserved-SEC-date strategy (no period_of_report drift); cross-check rejected as unsafe per corpus validator data (Path A 94.85% < Path B 99.73% → fiscal_math veto would regress 104 corpus tickers). 7/7 smoke fixtures preserve their period_of_report exactly; future leaks closed. |
| U65 | cross | P0 | ✅ `b798e33` | earnings_orchestrator.py:387-397 (`get_quarter_dir`) | One-line fix: `Path(save_dir).parent` → `Path(save_dir)`. Each `--save-dir` is now ticker-scoped → no `/tmp/context_bundle.json` race. `get_learning_paths` symmetric branch was unreachable (only caller doesn't pass `save_dir`); deferred. |
| U66 | cross | P0 | ✅ `5f4864f` (bundled with U45) + `624317c` (followup) | `.claude/skills/earnings-prediction/SKILL.md` (6 edits across 2 commits) | Phase 0 source of truth → rendered `## Lessons To Label` (NOT JSON `learning_context`). 5 edits in `5f4864f` covered line 23 input parenthetical, lines 39-77 Phase 0 body, line 84 Phase 0 example placeholder, line 155 lesson_labels description. ChatGPT post-commit review caught one residual stale pointer in the **separate ## Output section example block** (line 112 — distinct from the Phase 0 example I had edited); fixed in `624317c`. Count-invariant + verbatim-copy + empty-case-via-rendered-marker. AVGO Q4 production smoke: predictor copied L1-L6 verbatim (all 6 byte-equal to ordered after normalize). |
| U67 | cross | P0 | ✅ `9f6749b` + `20d9ea2` + `ddf0df7` | earnings_orchestrator.py (`build_evidence_source_catalog` + `validate_prediction_result`) | Tier M+/C event-scoped source_id grounding. Aggregator walks days[].events for N{i}/F{i}, catalysts pairs (today/yesterday {date,headlines}, earlier list-of-pairs), guidance.series, lessons via shared `iter_labeled_lessons`; rendered N{i}/F{i} aliases match renderer enumeration; renderer emits `## Evidence Source IDs` block under §1.0 header; validator's `expected_source_ids` kwarg enforces set membership; empty `evidence_ledger` rejected in production; quarantine of result.json on validation failure (gated on `prediction_validated` to avoid moving valid output if post-validation `_close_run` fails); 5 external A/B harness scripts marked legacy/offline. AAPL ∩ CRM ∩ NVDA event-prefix overlap = 0; 3-ticker production smoke 100% pass. |
| U68 | cross | LOW | 🟡 OPEN | earnings_orchestrator.py:2552-2632 | Surface validation outcome inside result.json. Currently pass/fail is encoded only in file location (`result.json` vs `result.json.rejected`); post-hoc audit tooling has to crawl filesystem conventions instead of reading a JSON field. Fix: after `validate_prediction_result(...)` returns successfully, set `prediction["prediction_validated"] = True` and atomic-rewrite result.json. In the except branch, set `prediction["prediction_validated"] = False` and atomic-rewrite BEFORE renaming to `.json.rejected`. Honest placement is AFTER validation — NOT inside `finalize_prediction_result()` which runs before validation and would lie. ~5 LOC + 1 pinning test. | Surfaced by 3-ticker production smoke 2026-05-01 (KLAC/GM/GS) — all three result.json files lacked the boolean despite having passed validation. ChatGPT-validated 2026-05-01: low risk, low urgency, batch into next validator/orchestrator pass; do NOT schedule a standalone loop. |
| R1 | — | DECISION | ✅ RESOLVED in U61 (2026-05-01) | renderer/header.py + §1.12 | Surface `assembled_at` in rendered. Reversed from earlier "never surface". | §1.0 implementation shipped via U61. §1.12 cross-section first-line annotations remain open. |
| R2 | §1.4 | DECISION | ✅ DONE (Decision #10) | renderer/financials.py | Segment revenue split implemented. | Audit verifies still renders correctly. |
| R3 | §1.10 | DECISION | ✅ RESOLVED in `5f4864f` (Decision #13) | renderer/lessons.py | 4 learner-output fields → `## Context-Only` compact sub-block under each ticker source event (`### Ticker — <quarter>`). Format: `- predicted_confidence: <int>`, `- primary_driver: <summary>`, one bullet per item for `what_worked` / `what_failed` lists. NOT labeled — separated from `## Lessons To Label`. |

---

## P0 detail blocks (all 4 SHIPPED 2026-04-30 → 2026-05-01)

### U64 — quarter_identity._QUERY PIT bound + form_type_periodic decoupling [✅ SHIPPED `998b165`]

**Final shipped strategy** (deviated from original spec, simpler + safer):
- Cypher CASE WHEN gate hides matched accession when `q.created > r.created`. Periodic stays SELECTED for internal denylist/XBRL logic; only the externally-returned `accession_periodic` is masked.
- Returns BOTH `matched_accession_periodic` (raw) and `accession_periodic` (PIT-gated) — Python uses raw for `_resolve_fiscal_label` denylist + XBRL preference logic.
- **No `_derive_form_type_periodic` helper added** (original spec called for one). The gate-only approach preserves SEC `period_of_report` exactly (e.g. AVGO Q4 stays `2023-10-29`, not calendar `2023-10-31`); `form_type_periodic` from matched row stays populated.
- **No fiscal-label cross-check** added. Per corpus validator data (Path A 94.85% < Path B 99.73%), a fiscal_math veto would regress 104 corpus tickers. Live-mode pre-period-ingestion edge case (predictor runs before matching periodic exists in DB) tracked as separate concern.
- Renderer §1.8 micro-display: `Periodic: — (10-K expected)` when accession masked but form_type known.

**Verified**: 7/7 fixture tickers preserve `period_of_report` byte-identical to pre-fix; future-filed accessions hidden across all 4 audit goldens (AVGO Q3/Q4, CHRW Q4, CXM Q4) and 3 fresh production smokes (AAPL/CRM/NVDA Nov 2023 prints).

<details>
<summary>Original spec (now superseded — kept for history)</summary>

### U64 — quarter_identity._QUERY PIT bound + form_type_periodic decoupling [original spec]

**Site**: `scripts/earnings/quarter_identity.py:45-58` (`_QUERY` periodic resolution OPTIONAL CALL).

**Symptom**: Resolver filters periodic by `date(q.periodOfReport) < date(datetime(r.created))` but never checks `q.created`. For AVGO Q4 FY2023 (8-K filed 2023-12-07T16:18:51, predictor PIT = filed_8k):
- 10-K (FY2023) `q.created` ≈ 2023-12-22 (~15 days **after** PIT)
- Resolver returns it as `accession_periodic = 0001730168-23-000096`
- U36 (already shipped) renders this future-filed accession to predictor in §1.8: `Periodic: 0001730168-23-000096 (10-K)`
- Predictor citing it in evidence_ledger references a future filing → strict-PIT violation

**7-ticker smoke universal confirmation (2026-04-30)**:

| Ticker | Periodic-filed → PIT delta |
|---|---|
| NVDA | 10 minutes post-PIT (tightest) |
| CRM | 2.5 hours post-PIT |
| TSLA | 4h13m post-PIT |
| BURL | 9.5 hours post-PIT |
| AAPL | 14 hours post-PIT |
| AVGO | 15 days post-PIT |
| ADBE | 33 days post-PIT (worst) |

**Downstream blast radius**:
- **U1 (shipped, 55829bd)**: `consensus.py:_provider_fde_for_period` consumes `quarter_info.form_type_periodic`. Naive U64 fix returning None for `form_type_periodic` would re-introduce U1's strict-equality fallback bug.
- **U36 (shipped, 4adb5bb)**: §1.8 surfaces leaked accession to predictor.
- **U22a (pending)**: per-peer accession_periodic resolution would inherit the leak.

**Required fix spec**:

1. **Cypher PIT bound** in `quarter_identity._QUERY`:
   ```cypher
   AND datetime(q.created) <= datetime(r.created)   -- PIT bound (target's pit = its own filed_8k)
   ...
   ORDER BY datetime(q.created) DESC LIMIT 1        -- latest-filed within PIT (not latest-period)
   ```

2. **Decouple `form_type_periodic`** — new helper:
   ```python
   def _derive_form_type_periodic(period_of_report: str, fye_month: int | None) -> str | None:
       """Deterministic: '10-K' if period.month == fye_month, else '10-Q'. Pure (no DB)."""
       try:
           p = date.fromisoformat(str(period_of_report)[:10])
           return "10-K" if p.month == int(fye_month) else "10-Q"
       except (ValueError, TypeError):
           return None
   ```
   In `resolve_quarter_info()`: when resolver's `form_type_periodic` is None, substitute derived. `accession_periodic` stays None.

3. **Goldens regen** — 4 fixtures (AVGO Q3/Q4, CHRW Q4, CXM Q4). For fixtures where matched periodic was filed AFTER target 8-K's PIT: `accession_periodic` flips to None; §1.8 line changes accordingly. `form_type_periodic` stays populated (derived).

4. **Existing test update**: `scripts/earnings/test_quarter_identity.py:47` encodes leaked behavior. Must rewrite to assert PIT-bound: AVGO Q4 FY2023 `accession_periodic` is None at PIT=2023-12-07. Without rewrite, U64 commit regression-fails.

5. **§1.8 renderer micro-decision** (cosmetic): when `accession_periodic=None` but `form_type_periodic` derived, render either (A) `Periodic: —` or (B) `Periodic: not yet filed at PIT (10-K expected)`. Default A.

**TDD invariants**:
- AVGO Q4 FY2023 historical: `accession_periodic=None` at PIT=2023-12-07 (10-K filed 2023-12-22). Derived `form_type_periodic="10-K"` (period_of_report=2023-10-29, fye_month=10). U1's `_provider_fde_for_period` still returns `2023-10-31` — preserves 4-col Consensus Bar.
- Calendar-fiscal regression: tickers whose periodic was filed before target PIT → `accession_periodic` populated; no behavior change.
- Pure helper unit tests: `_derive_form_type_periodic` across (period, fye_month) combos including 13-week wobble and edge cases.

**Sequencing**: principled order is U64 → U22a → U22 (DRY: U22a inlines U64's pattern; U64 closes shipped-code U36 leak). Not a strict blocker.

</details>

### U65 — Orchestrator concurrency race on /tmp/context_bundle.json [✅ SHIPPED `b798e33`]

**One-line fix**: `Path(save_dir).parent` → `Path(save_dir)` in `get_quarter_dir`. Each `--save-dir <X>` is now ticker-scoped → bundle and rendered files land at `<X>/context_bundle.json` (not `<X>.parent/context_bundle.json`). 7 focused tests + 1 load-bearing parallel-uniqueness assertion (two distinct save_dirs produce distinct bundle paths). `get_learning_paths` symmetric branch unreachable from any current caller — deferred. Production default path (no `--save-dir`) byte-identical.

<details>
<summary>Original P0 detail (now shipped — kept for history)</summary>

### U65 — Orchestrator concurrency race on /tmp/context_bundle.json [original spec]

**Site**: `scripts/earnings/earnings_orchestrator.py:387-397` — `get_quarter_dir(save_dir)` returns `Path(save_dir).parent`.

**Symptom**: parallel `--save-dir /tmp/smoke_<TICKER>` runs all share parent `/tmp`, racing on `/tmp/context_bundle.json`. Predictor SDK reads whichever bundle was last written. Confirmed independently by 5 of 7 smoke agents (AVGO+ADBE got AAPL-content stamped with their own metadata; BURL+CRM+NVDA self-detected and worked around with deeper `--save-dir`).

**Empirical proof** (AVGO smoke): bundle saved 16:11; AAPL parallel orchestrator overwrote between 16:11 and 16:23; AVGO predictor at 16:23 read AAPL bundle. AVGO `result.json` cites `iPhone +5.5% YoY`, `Greater China $15.033B`, `Keybanc Downgrades Apple` — pure AAPL data.

**Fix options**:
1. **Preferred**: bundle path = `save_dir / "context_bundle.json"`, not `save_dir.parent`. Each `--save-dir` naturally unique.
2. Atomic write + PID check (overengineered).
3. Require callers to pass unique per-event save-dirs (caller burden).

**Workaround until patched**: pass `--save-dir <unique>/event/prediction/` so `q_dir.parent = <unique>/event/`. Validated by CRM+NVDA on retry.

**Blocks**: parallel CI/test/prediction harnesses unsafe until patched. Sequential runs unaffected.

</details>

### U66 — Predictor fabricates lesson_labels not present in bundle [✅ SHIPPED `5f4864f` (bundled with U45)]

SKILL.md rewritten end-to-end across 2 commits: `5f4864f` did 5 edits (line 23 input parenthetical, lines 39-77 Phase 0 body rewritten to point at rendered `## Lessons To Label`, line 84 Phase 0 example placeholder, line 155 lesson_labels description). Followup `624317c` caught the last stale pointer in the separate `## Output` section's JSON example block (line 112) — distinct from the Phase 0 example block — flagged by ChatGPT post-commit review. Empty-case wording: "if `## Lessons To Label` is absent or has zero L# markers, emit `lesson_labels: []`". Count invariant + verbatim-copy + no-fabricate explicit. AVGO Q4 production smoke confirmed predictor copied L1-L6 verbatim with byte-equal-after-normalize match to validator's `expected_lesson_texts`.

<details>
<summary>Original P0 detail (now shipped — kept for history)</summary>

### U66 — Predictor fabricates lesson_labels not present in bundle [original spec]

**Site**: `.claude/skills/earnings-prediction/SKILL.md:39` — Phase 0 instruction.

**Symptom**: BURL Q3 FY2024 smoke — bundle has 2 lesson entries; predictor returned 4 `lesson_labels`. Two real (AVGO-source macro lessons, correctly `irrelevant`); two fabricated ("2023-24 semiconductor reaction regime", "hyperscaler AI capex regime"). Validator at `earnings_orchestrator.py:544` caught count mismatch (4 vs 2) and rejected. Safety net works at runtime; first-pass output unsafe.

**Fix**: REPLACE existing JSON-source pointer at SKILL.md:39 (which currently tells Phase 0 to use `bundle.learning_context` from JSON) with verbatim-from-rendered instruction. REPLACE not ADD — dual-source ambiguity is the prefix-bashing problem U45 eliminates.

Replacement text:
> Label ONLY lessons that appear verbatim in the rendered `## Lessons To Label` section. Do NOT fabricate, paraphrase, or pull lessons from `bundle.learning_context` JSON. The count of `lesson_labels[]` MUST equal the count of L# markers. Each `lesson_text` MUST be a verbatim copy. Do not invent lessons from prior knowledge or pattern-matching against the cross-ticker lesson pool.

**Order-of-operations**: U45 (lessons split renders new format) and U66 (SKILL.md prompt rewrite) MUST land in single coordinated commit. Landing U45 alone leaves SKILL.md still pointing to JSON; landing U66 alone points to a §section that doesn't exist yet.

**Blocks**: validator catches count mismatch but predictor output fragile until prompt hardened.

</details>

### U67 — Validator doesn't check evidence_ledger content matches bundle ticker [✅ SHIPPED `9f6749b` + `20d9ea2` + `ddf0df7`]

**Final shipped strategy**: Tier M+/C event-scoped per-evidence source_id grounding (rejected sampling/numeric-token approaches as too heuristic). Three commits across the design iteration:
- `9f6749b` initial: aggregator + Cypher-side rendered catalog + validator kwarg + 5 external script markers.
- `20d9ea2` amend: aggregator walked NON-EXISTENT bundle paths (`news_events`, `macro_catalysts`, `quarterly/annual/other`); rewritten to walk real schemas (`days[].events`, `catalysts` with bucket-shape handling for `today/yesterday` dict + `earlier` list-of-pairs, `series[]`); added rendered N{i}/F{i} aliases matching renderer; render-order preserved (not sorted); strict bundle subscript; `result.json` quarantine on validation failure.
- `ddf0df7` gate: quarantine wrapped in `if not prediction_validated:` guard so post-validation `_close_run` failure can't move a valid result.json.

**Production smoke (3 fresh tickers)** — all 7 contract checks pass on AAPL Q4 FY2023 (922 anchors), CRM Q3 FY2024 (193), NVDA Q3 FY2024 (278); cross-ticker overlap = 0; predictor cited rendered N{i} aliases successfully (`#S6.news.N446`).

**Catalog↔renderer drift prevention**: U45+U66 rebuilt the lesson-anchor walk to use `_text_utils.iter_labeled_lessons` — both renderer's `## Lessons To Label` AND catalog's `#S10.lesson.L#` derive from the same generator, can never drift.

<details>
<summary>Original P0 detail (now shipped — kept for history)</summary>

### U67 — Validator doesn't check evidence_ledger content matches bundle ticker [original spec]

**Site**: `scripts/earnings/earnings_orchestrator.py:418` — `validate_prediction_result`.

**Symptom**: validator checks STRING metadata (ticker, quarter_label, schema_version). Does NOT verify `analysis` text or `evidence_ledger[].value` reference bundle's actual ticker. ADBE+AVGO smokes produced AAPL-content with their own metadata stamps — validator passed. Only U66's lesson-count anomaly caught BURL's case; AVGO+ADBE had matching counts so validator silent.

**Fix**: extend `validate_prediction_result`:
1. Sample 2-3 random `evidence_ledger[]` entries.
2. For each, look for cited `value` substring in `bundle.context_bundle.json` (or rendered text).
3. If <50% of samples found in bundle → reject.

Tighter alternative: require `evidence_ledger[].source` to reference a specific bundle path that exists.

**Blocks**: nothing strictly (U65 fix removes race that creates swap), but defense-in-depth.

</details>

---

## Open detail blocks (HIGH severity only — MEDIUM/LOW are registry-only)

### U22 — Peer Option D format never implemented [HIGH; principled-prereq U64]
Site: `renderer/peers.py:43-74`. Full renderer rewrite to per-peer block format. Required output:
```
### NVDA — filed 2023-11-21 (post_market), accession 0001045810-23-000244

Stock move:      Day -2.46%   Sess +3.99%   Hour +3.18%
Sector-adj:      Day -1.98%   Sess +4.20%   Hour +0.48%   Best +4.20%
Macro-adj:       Day -0.75%   Sess +3.12%   Hour +1.45%   Best +3.12%
Headlines:
- [N68 | bz:35906540] ...
```
3×3 matrix (3 horizons × 3 cohorts: stock-raw, sector-adj, macro-adj) + best_*_pct aggregates. PIT cross-cut: U22a's per-peer accession_periodic must use U64 gate-only semantics (select latest matching periodic by `periodOfReport`, then mask `accession_periodic` via CASE WHEN; do NOT expose raw matched accession in the bundle). Peer builder fail-OPEN bug if `returns_schedule` is missing/malformed → per-horizon fail-closed bundles into U22a. Ambiguity C: builder has 7 fields not 6; need 9 cells (3×3); 2 missing (`session_sector`, `session_macro`) come from U22a.

### U22a — Peer builder backfill [HIGH; BLOCKS U22]
Site: `builders/peer_earnings_snapshot.py:31-72`. RETURN additions (`pf.session_sector`, `pf.session_macro`, `r.isAmendment`, OPTIONAL CALL for PIT-gated `accession_periodic`) + session null-lines + bz_id parsing + fail-closed gate when returns_schedule missing/malformed. Per-peer periodic Cypher must preserve U64's gate-only invariant:
```cypher
OPTIONAL CALL (peer_r, peer_c) {
  MATCH (q:Report)-[:PRIMARY_FILER]->(peer_c)
  WHERE q.formType IN ['10-Q', '10-K']
    AND q.periodOfReport IS NOT NULL
    AND date(q.periodOfReport) < date(datetime(peer_r.created))
  WITH q, peer_r ORDER BY q.periodOfReport DESC LIMIT 1
  RETURN
    CASE
      WHEN q.created IS NOT NULL
       AND datetime(q.created) <= datetime(peer_r.created)
       AND datetime(q.created) <= datetime($pit_cutoff)
      THEN q.accessionNo
    END AS accession_periodic,
    q.formType AS form_type_periodic
}
```
Do not return raw `matched_accession_periodic` in `peer_earnings_snapshot.peers[]`; it is an internal U64-style concept and could be post-PIT. Pre-flight audit `a380c0e` validated existing 7-field PIT correctness. Before editing, run a Neo4j probe to confirm `pf.session_sector` and `pf.session_macro` exist on `PRIMARY_FILER`; if absent, stop and re-scope instead of inventing them in renderer code.

### U33 — Yahoo session leak [CRITICAL for live pre_market; LOW historical]
Site: `builders/macro_snapshot.py:406`. BURL 06:52 ET: `effective_session = 'post_market'` forced for Yahoo source → today_return=0.52 leaks post-PIT close-to-close. Fix: keep `effective_session` aligned with `market_session` for Yahoo, OR NULL today_return / sector last_return when not actually post_market. Live-mode pre-market only (adapter forces polygon for historical).

### U45 — Lessons-To-Label / Context-Only split [✅ SHIPPED `5f4864f`]
See registry row + Decisions #13-#16 (R3-R6) for shipped behaviour. Original spec retained below for history.

<details>
<summary>Original spec (now shipped)</summary>

### U45 — Lessons-To-Label / Context-Only split [HIGH; bundle with U66]
Site: `renderer/lessons.py`. Full structural rewrite per plan §1.10 spec:
- `## Lessons To Label (verbatim, in order)` — only labeled lesson bodies; `L1.`/`L2.` markers on own line; no inline prefix.
- `## Context-Only (not labeled)` — header metadata, `data_lessons`, `why`.
- Tuple element 2 (`ordered_lesson_texts`) byte-identical (validator depends).
- Per-lesson `learner_result:` line per Decisions #3+#4.
- Missing-file rule: omit line entirely.
- Current-quarter PIT-guard before emitting any path.

Pre-audit: learner-link plumbing FULLY landed (orchestrator `_allowed_learner_paths` invariant + decorator + PIT-guard; allowlist set-equality validated). **MUST land bundled with U66** (single coordinated commit).

</details>

### U46 — Lessons inline-prefix bug [✅ SHIPPED `5f4864f` (folded into U45)]
All three prefix patterns removed in `5f4864f`: `- Predictor:` / `- Data:` (lines 60/64) and `[scope:..] (SRC)` (lines 91/103/116). Lesson bodies now render clean under `L#.` markers; metadata moved to `## Context-Only`.

---

## Smoke results, Architecture nuances, Plan-spec ambiguities, NEEDS-USER-INPUT

### Smoke (2026-04-30, 7 tickers)
7 forked agents ran end-to-end `--predict` on AVGO/AAPL/TSLA/BURL/ADBE/CRM/NVDA + `compare_section.py` × 10 sections.
- **Renderer-side: 100% PASS** — 8/8 fixes verified across 70 section walks; no JSON↔rendered drift beyond environmental degradation (Polygon 429 / AV daily-quota).
- **Predictor-side: 4/7 clean** (AAPL/TSLA/CRM/NVDA cite ticker-correct evidence_ledger). 2/7 contaminated by U65 race (AVGO/ADBE consumed AAPL bundle). 1/7 hallucinated lessons (BURL — U66; validator caught).
- **U64 leak: 7/7 universal** (see U64 block table).
- **3-lens synthesis (2026-04-29)**: 3 forked agents ranked by direction-flip / confidence-calibration / frequency×signal. Notable disagreements: U45 demoted by L2 (productivity not calibration); U33 conditional on live pre_market only; U10/U20/U32/U61 calibration-only Tier S.

### Architecture nuances (informational; non-blocking)
- **N1** [adapters.py: 8k_packet/guidance/consensus/prior_financials → null; inter_quarter_context → filed_8k; peer/macro → _now_iso()]: `effective_cutoff_ts` has 3 different meanings in live mode. Document per-builder semantic in `adapters.py` if/when §1.12 lands. (See U63.)
- **N2** [consensus.py:1005-1018]: Yahoo fallback covers ~last 8 quarters from today. Running `--live` on AVGO Q4 FY2023 today → Yahoo returns 2024+ rows → fiscal_math's `target_fde="2023-10-31"` not in row set → all `is_current_quarter=False`. Not a U1 bug; live-only fallback issue. Mitigation: `--predict`/`--learn` default historical doesn't trigger Yahoo.
- **N3** [adapters.build_8k_packet]: no defensive `filed_8k <= pit_cutoff` validation. Not exploitable today (orchestrator defaults pit_cutoff=filed_8k); add assertion if code paths decouple.
- **N4** [adapters.py:192]: live-mode inter_quarter uses `filed_8k` as upper bound (`context_cutoff = pit_cutoff or filed_8k`). Consistent with "live = access freely" spirit; caller must supply sensible filed_8k for upcoming-event live predictions.
- **N5**: renderer-side PIT awareness partial. Surfaced in: header.py (top-level pit_cutoff), inter_quarter.py:68-69 (PIT line), peers.py:26 (window). NOT surfaced in: results.py (§1.1+§1.8), guidance.py, consensus.py (§1.3), financials.py, macro.py, lessons.py. Closes via §1.12.

### Plan-spec ambiguities (verifier-found 2026-04-29)
- **Ambiguity A** = U56. §1.2 Derivation/Source values diverge from builder schema. Plan-author resolves before §1.2 walk.
- **Ambiguity B** [§1.4 Provenance footer wording]: plan says "every derived metric" but `_provenance` is mixed-shape (exact-extract vs derived). U12 implementation correctly read `derived_metrics[]` (only derivations) — not `_provenance`. Recommend tightening plan §1.4 to "every entry where `_provenance[m].derived is True`".
- **Ambiguity C** [§1.6 Option D "all 6 returns + sector/macro adjusted"]: builder has 7 fields; desired matrix is 3×3=9 cells. **Missing 2** = `session_sector`, `session_macro` (per U22a). Recommend plan calls out 3×3 explicitly, marking which 2 cells need U22a backfill.
- **Ambiguity D** [§1.10 split — which `ticker_lessons[i]` keys go to Context-Only?]: plan says "header metadata, data_lessons, why" but ticker_lessons[i] also has `predicted_direction`, `actual_daily_pct`, `direction_correct`, `primary_driver_category`, `quarter_label`. Almost certainly Context-Only but plan doesn't enumerate. Recommend plan §1.10 enumerates explicitly. R3 surfaces 4 NEW fields but doesn't address the 5 current header-line fields.

### NEEDS-USER-INPUT panel (open decisions blocking work)
- **U15, U16**: segment cosmetic/observability (low-priority).
- **U29**: industry-only similarity — design for cross-industry peers.
- ~~U50, U51, U52: lessons design (cross-ticker placement / L-numbering / dedup) — needed before U45.~~ **✅ RESOLVED in `5f4864f` via U45 bundle**: U50 (cross-ticker placement) → `[cross: T1,T2]` tag in L# marker line, body clean (Decision #15); U51 (L-numbering) → flat L1..Ln per individual lesson (Decision #15); U52 (de-dup across scopes) → not deduped on purpose (validator's positional `expected_lesson_texts` allows duplicates by design — same lesson body appearing in both ticker and global scope is two distinct `lesson_labels[]` entries with potentially different `bundle_evidence` per scope).
- **U56**: §1.2 Derivation/Source ambiguity — **BLOCKS §1.2 walk**.
- ~~R3: 4 learner-output fields decision — needed at §1.10 implementation gate.~~ **✅ RESOLVED in `5f4864f` (Decision #13)**: 4 fields → `## Context-Only` compact sub-block under each ticker source event.
- **Ambiguities A/B/C/D**: plan wording resolutions.

**No U-items currently blocking U45/U66/U67 (all shipped). Open NEEDS-USER-INPUT items are out-of-cluster (peers, §1.2 walk) and orthogonal to the lessons + grounding work.**

---

## Active contract sections (§2-§5)

### §2 SKILL.md changes — VERBATIM TEXT FOR U45+U66 BUNDLE

**§2.1 Input section — rewrite**:

```
## Input

Read `RENDERED_BUNDLE_PATH` as your primary reasoning surface — it contains everything you need for prediction including the `## Lessons To Label` section for Phase 0. `BUNDLE_PATH` (JSON) is available for targeted verification only (e.g., exact numerical precision for consensus checks, structural fields, builder_errors) — do not use it as an alternative reading surface.

If a lesson or a Context-Only block includes a `learner_result:` path, you MAY Read that file for deeper context (what the prior learner judged the real driver, what it flagged as having worked or failed, full evidence ledger). This is OPTIONAL — follow a link only when the lesson body alone isn't enough to decide a label or ground a driver. When you cite material sourced from a learner result, use `source: "learner_file:<path>"` in your `evidence_ledger`.

Write your result to `RESULT_PATH`.
```

**§2.2 Phase 0 header — rewrite**:

> "**Source of truth**: the `## Lessons To Label` section of the rendered bundle. Copy each lesson text verbatim from the body that follows each label marker (L1, L2, ...) in the exact order they appear."

Update remaining Phase 0 wording — replace any references to JSON paths (`ticker_lessons[i].predictor_lessons[j]`, `global_lessons[i].lesson`) with references to the numbered markers in `## Lessons To Label`. Do NOT leave a JSON fallback — would reintroduce prefix-bashing.

### §3 Orchestrator prompt
Update the prompt string passed when invoking the predictor skill to clarify primary/secondary roles. Both paths still passed; comments inline indicate which is reasoning surface vs verification surface.

### §4 Plan doc sync
- `.claude/plans/predictor-revamp.md` (~L397-398): rewrite "both paths by design" → hybrid contract.
- `.claude/plans/learner.md` (~L2964, L2989, L3250): replace OLD-contract refs ("JSON as Phase 0 source", `bundle.learning_context` reads) with rendered-bundle pointers. Doc sweep only — no code effects.

### §5 Tests — hybrid convention
- **Golden**: update `test_renderer_golden_full.py` / `test_renderer_golden_sections.py` when renderer changes.
- **Targeted**: `test_render_<section>.py` (model: `test_render_learning_context.py`).
- ~~Specific: `test_render_learning_context.py:112-114` — rewrite to target `## Lessons To Label` / `## Context-Only` (hard break for U45 commit).~~ **✅ DONE in `5f4864f`**: full rewrite of the file (R1-R7, A1-A2 updated for new sections; 8 new tests added including `test_l_marker_body_round_trip_equals_ordered` — the load-bearing cross-surface invariant). Old line numbers no longer apply.
- New assertions: prior-disambig (3 cases), per-peer return decomp, derived_metrics provenance per quarter, industry_return column, `effective_cutoff_ts` + `assembled_at` per section, learner_result inline link, current-quarter PIT-guard, missing-file omission, validator accepts `source: "learner_file:<path>"`.

### §6/§7/§8 (compact)
- **§6 A/B scripts** (verify, don't rewrite): `run_ab_baseline.py`, `run_nvda_ab_sequential.py`, `run_burl_ab_sequential.py`, `run_calibration_sequential.py` — call `render_bundle_text(bundle)` and auto-pick-up. Audit for fixture-baked rendered-text substring assertions / MD5 hashes; update baselines if any.
- **§7 Smoke tests**: 7-ticker E2E executed 2026-04-30 (see Smoke section). Pass criteria: predictor doesn't bash JSON for lessons; validator passes lesson_labels; peer section shows all return decompositions.
- **§8 Downstream impact** (verified unaffected, 2026-04-21; re-verified post-shipment 2026-05-01): JSON schema unchanged at the predictor-output level; bundle JSON gained 2 frozen-field additions (`evidence_source_catalog` from U67, `_allowed_learner_paths` from U45); validator consumes byte-identical tuple-2; `_run_learner_via_sdk` reads JSON not rendered; obsidian integration (file-move only); hooks (`pit_gate.py`, `validate_learning_output.py`, `build_orchestrator_event_json.py` — JSON-only); migration/k8s/.github (no coupling). ~~Hard break still pending: `test_render_learning_context.py:112-114`.~~ **✅ DONE in `5f4864f`** (full file rewrite).

---

## Per-section spec quick-ref (§1.0-§1.12)

Audit walks in display order: §1.0 → §1.1 → §1.2 → §1.3 → §1.4 → §1.5 → §1.6 → §1.7 → §1.8 → §1.10 → §1.11 → §1.12. Per-section spec items not already in U-entries:

- **§1.0 header** — covered by `ff2e842` (accession_8k + prev_8k_ts + days-ago) + U61 (assembled_at, ✅ shipped 2026-05-01).
- **§1.1 results** — covered by U1, U2-U7.
- **§1.2 guidance** — 5 spec items: prior-disambig (`(first update)`/`(prior value unavailable)` — never bare `—`); `metric_id` prefix on Metric label; Derivation column (per U56 ambiguity); Source column (per U56); compact footer per metric (`xbrl_qname: ... | evhash16: ...`).
- **§1.3 consensus** — covered by U8-U11, U60, U62.
- **§1.4 financials** — Per-quarter `derived_metrics` derivation notes (✅ U12; sources from `quarters[].derived_metrics`, NOT `_provenance` — see Ambiguity B). Segment revenue split (R2 ✅). Segment operating-income deferred. (U13/U14/U15/U16 follow-on.)
- **§1.5 inter_quarter** — Industry-return column + `bz_id` per news event (U17/U18 cluster).
- **§1.6 peers** — HIGH IMPACT. Option D format (see U22 detail block for full example). `accession_periodic`, `is_amendment`, all 6 returns + sector/macro adjusted, `best_sector_pct`, `best_macro_pct`, per-headline news_id+bz_id. (See Ambiguity C — actually 3×3=9 cells.)
- **§1.7 macro** — `BzID` column on Macro Catalysts (today/yesterday/earlier). (U31/U32/U33/U34/U35.)
- **§1.8 reference** — `cik`, `accession_periodic`, `form_type_periodic`, `is_amendment`, conditional `quarter_info.gaps` (✅ U36). U37/U38/U39/U40/U41-43 follow-on.
- **§1.10 lessons** — ✅ DONE in `5f4864f` (U45+U66+U46+U48+U53 bundled). `## Lessons To Label (verbatim, in order)` flat L1..Ln + `## Context-Only` (R3 fields + data_lessons + why + learner_result paths). Tuple-element-2 byte-identical. Per-lesson `learner_result:`. Missing-file omit. Current-quarter PIT-guard. R3 resolved → Context-Only sub-block. Empty-case render preserved (bundle.py fix).
- **§1.11 final integration** — partial (`5f4864f` + `624317c` + `998b165` + `b798e33` + `9f6749b`+`20d9ea2`+`ddf0df7` runs `_capture_golden full + sections + degraded` and **145/145 tests + 5 subtests** + 4 fresh-ticker production smokes pass). Cross-section AST parse done for renderer/{header,results,reference,inter_quarter,bundle,lessons,_formatters}.py per commit. **Outstanding**: end-to-end run after U22+U22a peer rewrite + U33.
- **§1.12 PIT provenance** — applies to ALL renderers. First lines under each section header: `effective_cutoff_ts: <ts>`, `assembled_at: <ts>` (R1). Open.

---

## Verification checklist

- [x] §1.10 lessons split shipped (U45+U66) with byte-identity invariant preserved.
- [x] §2 SKILL.md edits applied (`5f4864f` — 5 edits + `624317c` — followup for the missed Output-section example).
- [x] §4 plan doc references updated (this update, 2026-05-01).
- [x] §5 tests: **145/145 + 5 subtests** pass (U64+U65+U67+U45/U66 + golden full/sections/**degraded** regression).
- [x] §7 smoke tests pass on AVGO + 3 fresh tickers (AAPL/CRM/NVDA) + AVGO Q4 rich-lessons + CRM Q3 empty-lessons.
- [x] `python3 -c "import ast; ast.parse(...)"` clean for every modified renderer file.
- [x] Diff review: every renderer change is additive at JSON-schema level — `evidence_source_catalog` (U67) and `## Lessons To Label`/`## Context-Only` (U45) added; no fields removed. `period_of_report` byte-identical for all 4 historical fixtures (U64 reject-criterion held).
- [x] R3 decision recorded in this plan (Decision #13 → RESOLVED `5f4864f`).
- [ ] §3 orchestrator prompt — implicitly covered (no separate prompt template; SKILL.md is the source of truth and was updated).
- [x] U22+U22a (peer Option D + builder backfill) — ✅ shipped 2026-05-01 (`822d178`).
- [ ] U33 (Yahoo session leak) — outstanding small item.
- [x] U61/R1 (`assembled_at` in §1.0 header) — ✅ shipped 2026-05-01. Implemented directly in header.py (not folded into §1.12).
- [ ] §1.5/§1.7/§1.12 walks — outstanding (mid-audit).
- [ ] Per-section discrepancies in remaining §1.5/§1.6/§1.7/§1.12 either resolved or escalated.
