# 05 · Periods (DriverPeriod)

**What this is:** how a fact gets a **time window**. `DriverPeriod` = the resolved calendar date window a DriverUpdate is about. It reuses the proven Guidance period math, extended to all fact-types.

> Every rule is **LOCKED** unless marked **⏳ BUILD-PENDING**. Source = `Consolidation/GuidancePeriod.md`.
> **Still open here:** PER-20 (build not done). PER-19 (transition) was **UPDATED 2026-07-04** by Track C v2.0.

---

## A. What DriverPeriod is

#### PER-01 — DriverPeriod = the resolved calendar window  `[LOCKED]`
- **Plain:** A DriverPeriod is just the real calendar date window a fact is about (`gp_2025-01-01_2025-03-31`).
- **Rule:** It means only "the calendar window this DriverUpdate is about." NOT the event/filing/source date, NOT a free-text "Q1", NOT forecast-vs-actual (that's fact_type), NOT a replacement for fact_scope.
- **Why:** A real calendar window (not "Q1") is the only thing that compares safely across companies + calendars.
- **Source:** GuidancePeriod.md §What DriverPeriod Means

#### PER-02 — One generic DriverPeriod for all 4 fact-types  `[LOCKED]`
- **Plain:** Periods aren't guidance-only anymore — the same resolved window attaches to any fact-type with a period.
- **Rule:** Replace the old guidance-only "GuidancePeriod" with a generic DriverPeriod for period-bearing metric, guidance, surprise, and rare action_event facts. Raw "Q1" is unreliable: Dec-FYE Q1 (Jan–Mar) ≠ Sep-FYE Q1 (Oct–Dec), so `period=Q1` can't compare across companies.
- **Why:** Guidance already solved this by resolving fiscal fields into a real window; every fact-type reuses it.
- **Source:** GuidancePeriod.md §Why This Changed
- **Replaces:** old "GuidancePeriod, guidance-only" — 95_Supersession #10

#### PER-03 — Node name = DriverPeriod; keep the gp_ prefix  `[LOCKED]`
- **Plain:** The node is DriverPeriod (not Period, not GuidancePeriod), and its id keeps the `gp_` prefix.
- **Rule:** Use DriverPeriod — not Period (the graph already has an XBRL Period label → would mix two pipelines) and not GuidancePeriod (no longer guidance-only). Keep the `gp_` ID prefix (`gp_2025-01-01_2025-03-31`); do NOT rename to `dp_` — `gp_` is what the proven Guidance code returns, so it avoids translation/migration.
- **Source:** GuidancePeriod.md §Node Name

## B. Graph + by fact-type

#### PER-04 — One edge: HAS_PERIOD  `[LOCKED]`
- **Plain:** There's just one edge, HAS_PERIOD; its meaning comes from the driver's fact_type.
- **Rule:** One edge: `(:DriverUpdate)-[:HAS_PERIOD]->(:DriverPeriod)`. No separate names (TARGETS_PERIOD/REPORTS_PERIOD/OCCURS_DURING). Meaning from fact_type: guidance → future target window · metric → reported window · surprise → actual-vs-expectation window · action_event → rare stated action window.
- **Why:** One edge is enough; fact_type already carries the "what kind of window" meaning.
- **Source:** GuidancePeriod.md §Graph Shape

#### PER-05 — By fact-type; never force a period  `[LOCKED]`
- **Plain:** Guidance always has a period; metric/surprise when one exists; action_event rarely. No window → no edge.
- **Rule:** guidance → REQUIRED. metric/surprise → used when the fact has a stated, source-implied, or code-derivable period. action_event → rare/optional, only when the action has a real stated window. Never force a period; no real window → no HAS_PERIOD. (For guidance, both `company_confirmed` true/false still require a period.)
- **Why:** Forcing periods onto periodless facts fabricates structure.
- **Source:** GuidancePeriod.md §By Fact Type

#### PER-06 — Implied reported periods  `[LOCKED]`
- **Plain:** If a metric/surprise sentence omits the period but the event/report clearly is (say) Q1, use that Q1.
- **Rule:** For metric/surprise with an omitted period, derive it from event/report metadata when the source gives exactly ONE clear period (a Q1 10-Q saying "revenue grew 12%" → the event's Q1 window, not gp_UNDEF, not no-period). Only when deterministic from the source; don't guess from vague wording; ambiguous market/news → no period unless dates are stated. For 10-Q/10-K prefer XBRL/SEC exact dates when available.
- **Why:** The period is really in the event even when the sentence doesn't restate it.
- **Source:** GuidancePeriod.md §Implied Reported Periods

## C. Exact dates + sentinels

#### PER-07 — Exact-date windows for YTD / TTM / cumulative  `[LOCKED]`
- **Plain:** Nine-month or trailing-12-month facts get their exact date window, not squashed into a single quarter.
- **Rule:** Don't collapse YTD/TTM/cumulative into the discrete quarter. Exact start+end available → `gp_<start>_<end>` (nine months ended Sep 30 → `gp_2025-01-01_2025-09-30`). Priority: exact source/XBRL dates FIRST → else FYE-aware computed → else no period. Code validates ISO dates + start ≤ end. Added to the SHARED mechanism, not a Driver-only system.
- **Why:** Exact dates win — 52/53-week calendars make month-boundary fiscal math slightly wrong.
- **Source:** GuidancePeriod.md §Exact-Date Windows

#### PER-08 — Periodless actions get no period  `[LOCKED]`
- **Plain:** A CEO resignation has no time window → no period, not even gp_UNDEF.
- **Rule:** Do NOT use gp_UNDEF for periodless actions (CEO resigned → no HAS_PERIOD; buyback/closure → no edge unless a real program window is stated). gp_UNDEF = "a period-like horizon exists but is undefined" (going-forward guidance); a resignation has none. Periodless action identity = event + driver + fact_scope.
- **Why:** Giving periodless actions gp_UNDEF would create fake structure.
- **Source:** GuidancePeriod.md §Periodless Actions

#### PER-09 — The 4 sentinels  `[LOCKED]`
- **Plain:** Four special period values for dateless horizons: short/medium/long term, and "undefined".
- **Rule:** Keep Guidance sentinels exactly: `gp_ST` (short-term), `gp_MT` (medium-term), `gp_LT` (long-term) — period-like, no dates; `gp_UNDEF` (a period-like horizon that's undefined). Not for facts with no time-window concept ("long-term target" → gp_LT; "going forward" → gp_UNDEF; "CEO resigned" → no DriverPeriod).
- **Why:** Sentinels capture real-but-dateless horizons without inventing a window.
- **Source:** GuidancePeriod.md §Sentinels

## D. Reuse + code-decides

#### PER-10 — Reuse the Guidance mechanism; one shared module  `[LOCKED]`
- **Plain:** Reuse Guidance's proven period code as-is, + ~15-20 lines for exact-date/YTD/TTM, in one shared module for new DriverUpdate writes.
- **Rule:** Reuse EXACTLY: `build_guidance_period_id()`, the `gp_` shape, the 4 sentinels, FYE math, `calendar_override`, `time_type`, instant collapse, existing-period lookup, SEC cache, prev-quarter prediction, SEC-corrected FYE, fail-closed on missing FYE. Add minimal extensions (exact-date input, `period_scope=ytd/ttm`, ~15-20 lines) to the SHARED mechanism. Extract the cascade into `driver_period_resolver.py`; new DriverUpdate writes call `ensure_driver_period(...)`. The old Guidance CLI may be used as a parity oracle before retirement, but Track C does not rewire it into the new system.
- **Why:** Reusing proven, tested fiscal math avoids a fork and re-deriving hard edge cases.
- **Source:** GuidancePeriod.md §Reusing Guidance Mechanism · §What Can Be Used As-Is

#### PER-11 — Code computes the id; the LLM only emits fields  `[LOCKED]`
- **Plain:** The AI sends period fields; code turns them into the final period id. The AI never writes the id.
- **Rule:** Code computes `period_u_id`; the LLM emits only period fields and never writes `period_u_id`. Producer routing is first-match-wins: exact dates → sentinel_class → long_range_end_year → month → half → fiscal_quarter → fiscal_year → gp_UNDEF fallthrough. Don't emit conflicting fields. Never silently default a missing FYE to December (`ensure_driver_period` returns None only when there's truly no period).
- **Driver-wrapper amendment (owner 2026-07-03 — 95 #23 · `12_TrackB_FactPipeline.md` §10.7):** for DriverUpdate items, fields-present-but-unresolvable with NO explicit `sentinel_class` HARD-FAILS as a producer bug (never a quiet gp_UNDEF); `action_event` sentinel outcomes hard-fail (only a real stated window — which resolves to dated periods — qualifies); guidance still requires a real resolved period OR an explicit sentinel. The gp_UNDEF fallthrough survives only inside the pure shared builder (Guidance parity).
- **Why:** Deterministic code-built ids keep identity stable and stop the LLM fabricating a window.
- **Source:** GuidancePeriod.md §Producer Input Contract · §Public API Shape

## E. Identity + properties

#### PER-12 — The period must also appear in fact_scope  `[LOCKED]`
- **Plain:** The resolved period id goes both on the HAS_PERIOD edge AND inside fact_scope — same id in both.
- **Rule:** DriverPeriod is an edge for traversal/date queries, but the period must ALSO be in fact_scope (`period=<period_u_id>`), because fact_scope is part of the identity key. Edge + fact_scope are composed from the SAME `period_u_id`. Never use raw Q1/FY2025/April as the identity token — resolve to `gp_...` first. Validator (both ways): `HAS_PERIOD→DriverPeriod(id=X)` ⇔ fact_scope contains `period=X`. No hand-built duplicates.
- **Why:** Identity lives in fact_scope, so the period must be there too; one shared id keeps edge + key consistent.
- **Source:** GuidancePeriod.md §DriverUpdate Identity

#### PER-13 — DriverPeriod stores dates only  `[LOCKED]`
- **Plain:** The period node holds just the dates. Fiscal framing (year/quarter, scope, time_type) stays on the fact.
- **Rule:** DriverPeriod stores dates only: `id, u_id, start_date, end_date`. Keep `fiscal_year, fiscal_quarter, period_scope, time_type` on the DriverUpdate (source framing) — the same window can be described differently by different companies. The authoritative grouping key = resolved `period_u_id` + DriverPeriod dates; never recompute grouping from raw fiscal_year/fiscal_quarter after write. *(The full `period_scope` enum — quarter/annual/half/monthly/ytd/ttm/exact_range + the 4 dateless sentinels; `long_range` stores as `exact_range` — is pinned in `09_DriverUpdate_Fields.md` §3.)*
- **Why:** The node is the shared date window; the fact keeps how its source framed it.
- **Source:** GuidancePeriod.md §Properties

## F. Read-time guards

#### PER-14 — Guard: never group by period alone  `[LOCKED]`
- **Plain:** A period doesn't say forecast vs actual — never merge all facts sharing a period into one series.
- **Rule:** DriverPeriod does NOT say forecast vs actual. Safe: `revenue_guidance` / `revenue` / `revenue_surprise` + gp_2025 → three separate buckets. UNSAFE: all facts with gp_2025 → one numeric series. Any read path using DriverPeriod must keep Driver / fact_type / BASE_METRIC family / company / unit / time_type. Do not strip `_guidance`/`_surprise` and merge those rows into the base metric series.
- **Why:** The period is shared across forecast, actual, and surprise — grouping by it alone blends them.
- **Source:** GuidancePeriod.md §Guard 1

#### PER-15 — Guard: market-wide facts use calendar mode  `[LOCKED]`
- **Plain:** Drivers with no company fiscal calendar (oil_price, fed_funds_rate) use plain calendar dates.
- **Rule:** Market-wide Drivers (oil_price, fed_funds_rate, commodity_price, minimum_wage) use calendar mode / `calendar_override = true` (forces FYE month to December); do not require a company FYE. `time_type`: duration = full window (`gp_2025-01-01_2025-12-31`); instant = one-day at period end (`gp_2025-12-31_2025-12-31`).
- **Why:** A market rate has no company fiscal year, so it resolves on the plain calendar.
- **Source:** GuidancePeriod.md §Guard 3

#### PER-16 — Guard: fail closed on missing fiscal-year-end  `[LOCKED]`
- **Plain:** If a company fact needs a fiscal-year-end and it's missing, raise an error — never guess December.
- **Rule:** If a period-bearing company fact needs FYE data and it is missing, RAISE. Do not guess December.
- **Why:** A wrong FYE silently makes wrong windows; failing closed catches it.
- **Source:** GuidancePeriod.md §Guard 4

#### PER-17 — Guard: instant ≠ duration; write-once caution  `[LOCKED]`
- **Plain:** An "instant" period and a "duration" period are different nodes, never merged. Period dates are write-once.
- **Rule:** Instant vs duration are intentionally DIFFERENT nodes (duration FY2025 = `gp_2025-01-01_2025-12-31`; instant FY2025 = `gp_2025-12-31_2025-12-31`) — never merge. Write-once caution: Guidance writes dates with `ON CREATE SET`, so a node first created with wrong dates will NOT self-correct on rerun — keep parity tests + a uniqueness constraint before production wiring.
- **Why:** Instant vs duration are genuinely different windows; a bad first-write date would silently persist.
- **Source:** GuidancePeriod.md §Guard 5 / §Guard 6

## G. Cypher + transition + status

#### PER-18 — Cypher shape  `[LOCKED]`
- **Plain:** MERGE the period by id (set dates on create), MERGE the edge, unique-constraint the id, pre-create sentinels.
- **Rule:** `MERGE (dp:DriverPeriod {id:$period_u_id}) ON CREATE SET u_id/start_date/end_date` · `MERGE (du)-[:HAS_PERIOD]->(dp)`. Unique constraint on `DriverPeriod.id`. Sentinels (gp_ST/MT/LT/UNDEF) merged with null dates.
- **Why:** MERGE-by-id makes the same window converge to one node; the constraint enforces it.
- **Source:** GuidancePeriod.md §Cypher Shape

#### PER-19 — Transition strategy  `[LOCKED — updated 2026-07-04]`
- **Plain:** Old guidance is archived and retired. New guidance facts are created fresh by the Driver pipeline, not replayed from old `GuidanceUpdate` rows.
- **Rule:** The transition is **DECIDED**: Track C archives and retires the old guidance graph/code path. It does not relabel old `GuidancePeriod` nodes, does not build a both-label lookup transition, and does not replay old guidance rows into production `DriverUpdate` facts. New `fact_type=guidance` DriverUpdates use `DriverPeriod` only. Old `GuidancePeriod` nodes remain old/archive objects until deletion or explicit inert quarantine.
- **Why:** This keeps the new Driver system source-document based and avoids building replay machinery around legacy guidance mistakes.
- **Source:** GuidancePeriod.md §Cypher Shape · **owner decision 2026-07-04** · `13_TrackC_GuidanceIntegration.md`
- **Replaces:** older regenerate/both-label transition wording — 95_Supersession #10 context plus active Track C v2.0

#### PER-20 — Status: design locked, build/verify pending  `⏳ BUILD-PENDING`
- **Plain:** The design is final; the code isn't built. A gate of 21 tests + a few hardening tasks before wiring.
- **Rule:** DESIGN LOCKED, BUILD/VERIFY PENDING. Gates: extract `driver_period_resolver.py` from the proven Guidance cascade; pass the 21 "Required Tests Before Wiring"; PROVE YTD/TTM math with Dec-FYE and non-Dec-FYE examples before coding (pseudocode unverified); write-once-date hardening (parity tests + constraints); ship the `HAS_XBRL` race guard as a producer eligibility check (not inside the resolver). This build does not rewire old Guidance as a Track C transition path.
- **Why:** These are build/verify gates, not redesigns — the target design above is locked.
- **Source:** GuidancePeriod.md §STATUS · §Required Tests · §Exactness Notes
