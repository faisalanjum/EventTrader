# 06 · Metric family (BASE_METRIC)

**What this is:** how the four flavors of a topic (a metric, its forecast, its surprise, a related action) are kept as **separate Drivers but linked** — related, never merged.

> Every rule is **LOCKED**. Source of truth = `DriverGraphSchema.md:225-232` + `Consolidation/README.md:52-60`; plain-English companion = `Consolidation/MetricGuidanceFamily.md`. (The full `fact_type` decider lives in the DriverUpdate section.)

---

#### MF-01 — The 4 flavors (fact_type)  `[LOCKED]`
- **Plain:** Every driver has one flavor: metric, guidance, surprise, or action_event. Set once, permanent.
- **Rule:** `fact_type` ∈ {**metric** (a standing variable **or condition**, numeric **or** qualitative, re-readable over time — "revenue was $5B", "consumer sentiment") · **guidance** (company forecast — "we expect $6B") · **surprise** (actual vs expected — "beat by $0.2B") · **action_event** (a one-off — "CEO resigned", "$2B buyback")}. Set once per driver, permanent. (Full decider — persistence test, dual framing — lives in the DriverUpdate section.)
- **Why:** The flavor routes which state words are legal + whether a guidance period / company_confirmed attaches.
- **Source:** MetricGuidanceFamily.md · DriverGraphSchema.md fact_type lock

#### MF-02 — Same topic, different flavors = separate but linked  `[LOCKED]`
- **Plain:** revenue, revenue_guidance, revenue_surprise are separate drivers joined by a link. Related, never merged.
- **Rule:** Same topic, different flavors = SEPARATE Drivers, LINKED (never one merged number). WHY SEPARATE: different tradeable signals that can move the stock opposite ways the same day ("beat this quarter, cut next year's guidance" → down) — merging loses which signal moved it. WHY LINKED: to ask "did revenue beat its OWN forecast?"
- **Why:** Over-merging flavors destroys the signal; linking preserves the comparison.
- **Source:** MetricGuidanceFamily.md §The decision

#### MF-03 — Exactly one BASE_METRIC, required  `[LOCKED]`
- **Plain:** Every _guidance/_surprise driver must point to exactly one base metric driver.
- **Rule:** Every `_guidance` and `_surprise` Driver has exactly one `BASE_METRIC` edge to its base metric (`revenue_guidance → BASE_METRIC → revenue`). A build-time validator enforces "exactly one" and catches an orphan (a `revenue_guidance` with no `revenue`).
- **Why:** The edge is what lets a validator enforce the family and catch orphans.
- **Source:** MetricGuidanceFamily.md §rules · DriverGraphSchema:225-232

#### MF-04 — Why an arrow, not name-guessing  `[LOCKED]`
- **Plain:** The link exists for integrity (enforce "exactly one" + catch orphans), NOT to solve synonyms.
- **Rule:** The `BASE_METRIC` arrow's real value is integrity (enforce exactly-one + catch orphans), NOT solving synonyms. Don't infer family from arbitrary name prefixes — only a terminal suffix (MF-06) creates it.
- **Why:** Only an explicit edge can be validated; name-guessing can't.
- **Source:** MetricGuidanceFamily.md §rules

#### MF-05 — Base must exist; may be latent/empty  `[LOCKED]`
- **Plain:** If the base metric doesn't exist yet, create it in the same run. Fine if it has zero facts.
- **Rule:** If the base metric Driver doesn't exist, create it in the same catalog run. The base may be a latent, empty folder (only ever forecast, never reported) — that's fine.
- **Why:** The family needs its anchor even before any metric fact lands.
- **Source:** MetricGuidanceFamily.md §rules · README "Do Not Forget"

#### MF-06 — Only the END suffix counts  `[LOCKED]`
- **Plain:** `cost_guidance` is family (base `cost`); `guidance_revision_cost` (guidance in the middle) is not.
- **Rule:** Only a terminal `_guidance`/`_surprise` suffix creates the `BASE_METRIC` relation. `cost_guidance` → family (base `cost`). `guidance_revision_cost` ("guidance" mid-name) → NOT family.
- **Why:** Mid-name occurrences aren't the family suffix; only the terminal suffix routes.
- **Source:** MetricGuidanceFamily.md §rules

#### MF-07 — action_event gets NO base metric  `[LOCKED]`
- **Plain:** An action (buyback, CEO exit) touches many metrics, not one — so no BASE_METRIC.
- **Rule:** `action_event` Drivers have NO base metric (a buyback hits eps + share_count + cash — many-to-many). Their relation to metrics comes from EVIDENCE/events (the same Event, sometimes across multiple events over time), never an identity arrow. If ever materialized for search, a derived non-identity cache only — never `SAME_AS`, never a merged series. Validator: `action_event` has no `BASE_METRIC`.
- **Why:** An action isn't another reading of one metric, so a required base metric would be wrong.
- **Source:** MetricGuidanceFamily.md §rules · README "Do Not Forget"

#### MF-08 — Synonyms use SAME_AS, not BASE_METRIC  `[LOCKED]`
- **Plain:** If `net_sales` means the same as `revenue`, link those two metrics with `SAME_AS` (a different machine).
- **Rule:** Synonyms are a separate mechanism: if `net_sales` = `revenue`, tie those two METRICS by `SAME_AS` (not `BASE_METRIC`). Chain: `net_sales_guidance → BASE_METRIC → net_sales → SAME_AS → revenue`. Miss a synonym → a safe MISSING comparison, never a wrong merged number.
- **Why:** `BASE_METRIC` is family (guidance/surprise → base); `SAME_AS` is identity (two names, one metric) — different jobs.
- **Source:** MetricGuidanceFamily.md §rules

#### MF-09 — fact_type stays even with the _guidance suffix  `[LOCKED]`
- **Plain:** The `_guidance` suffix in the name and the `fact_type` field are both kept — not redundant.
- **Rule:** `fact_type` stays even though the name says `_guidance`. The suffix is readable text (bare `revenue` has none); `fact_type` is the machine-label that picks the state list + whether to attach a guidance period. Keep both.
- **Why:** The machine needs `fact_type` to route; the suffix is just human-readable.
- **Source:** MetricGuidanceFamily.md §rules · INDEX consistency (resolved)
- **Replaces:** old "suffix vs fact_type redundant?" open question — resolved: keep both

#### MF-10 — Only the base metric is XBRL-concept-matched  `[LOCKED]`
- **Plain:** `_guidance`/`_surprise` don't get their own XBRL concept — they inherit it from their base metric.
- **Rule:** Only the base metric Driver is XBRL-concept-matched. `_guidance`/`_surprise` INHERIT the concept via `BASE_METRIC` — never matched directly (XBRL tags the underlying metric, not a forecast/surprise; feeding `revenue_guidance` to the matcher correctly abstains). See the XBRL concept-link section.
- **Why:** A forecast/surprise has no XBRL tag of its own; the concept lives on the metric.
- **Source:** MetricGuidanceFamily.md §rules · XBRLConceptLinking.md §6

#### MF-11 — company_confirmed is guidance-only (DriverPeriod is not)  `[LOCKED — decided 2026-07-01]`
- **Plain:** A guidance fact also carries a "who said it" flag (`company_confirmed`). That flag is **guidance-only**. DriverPeriod is separate and applies to **all** fact-types.
- **Rule:** `company_confirmed` is a **GUIDANCE-ONLY boolean (`true`/`false`)** (boolean per 09 + README, not an enum), instance-level, property-only tag — never on metric/surprise/action_event, never in the fact key. A guidance fact is `true` when the company itself gave/reaffirmed it, `false` when a third party relays/rumors it (so **NOT** always confirmed). `action_event` expresses "unconfirmed" via its `rumored` state instead; metric/surprise are company-reported. (Full field spec in the DriverUpdate/Guidance section.) — Separately: **DriverPeriod applies to ALL fact-types** (see Periods) — it is NOT guidance-only.
- **Why:** Guidance is the only fact-type whose state lane can't express "rumored/unconfirmed", so it's the only place the flag is non-redundant.
- **Source:** GuidanceDriverConsolidation.md §7 · **owner decision 2026-07-01**
- **Replaces:** `MetricGuidanceFamily.md:70` stale line — DriverPeriod is all fact-types (not guidance-only; reversal #10), and guidance can be confirmed OR unconfirmed (not "always confirmed")

#### MF-12 — The principle: over-merge permanent, under-link recoverable  `[LOCKED]`
- **Plain:** Merging two related drivers into one number is permanent damage; forgetting to link them is easily fixed.
- **Rule:** Over-merging is permanent (merge a forecast + a result → the predictor can never untangle it → bad trades forever). Under-linking is recoverable (forget to link → a missed comparison → fix later). Always err toward separate, and add links (never merges).
- **Why:** The family's application of the one law (over-merge = permanent damage).
- **Source:** MetricGuidanceFamily.md §The one rule underneath
