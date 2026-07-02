# 99 · Codex Decision Audit

Status: historical audit / loss-prevention file.

Canonical plan: `FinalDesign` topic files (`01` through `09`, `90`, and
`95`). If this file conflicts with those topic files, the topic files win.

Purpose: preserve decisions surfaced during the Codex review so nothing discussed
there is lost. This is not a second source of truth.

## 0. How To Read This

Decision labels:

| Label | Meaning |
|---|---|
| Locked | Final target design. Implementation may still be pending. |
| Build gate | Final target is known, but tests or code still need to be done. |
| Owner decision | The design still needs explicit owner approval. |

Authority rule:

1. The newer `Consolidation` files win over older `.claude/plans/Drivers/WIP`
   and `plans/Drivers` files.
2. `.claude/plans/Drivers/WIP` is still important prior design context.
3. Older files are evidence, not final rules, when they conflict with newer files.
4. If two final-design notes conflict, keep the safer rule:
   avoid merging two different things into one.

## 1. Core Law

Locked:

- Over-merge is permanent damage. Never merge two different things.
- Over-split is fixable. When unsure, keep things separate.
- The LLM may assign a fact to an existing value or coin a new value.
- The LLM may mark something provisional.
- The LLM must never merge two existing identities.
- Code may merge only by exact or highly confident deterministic rules.
- Code may delete only from frozen, reviewed lists.
- A missing link is safer than a wrong merge.

Plain rule:

```text
Unsure -> keep separate.
```

## 2. DriverCatalog Decisions

### 2.1 What A Driver Is

Locked:

- A Driver is a reusable cause or topic that can move a stock.
- Examples:
  - `revenue`
  - `eps`
  - `same_store_sales`
  - `share_repurchase`
  - `ceo_succession`
- A Driver is not one event.
- A Driver is not one source quote.
- A Driver is not one company filing row.
- A Driver is not a unit container.

### 2.2 Driver fact_type

Locked:

- Every Driver has exactly one permanent `fact_type`.
- Owner review: approved name. Keep `fact_type`; do not rename to `driver_type`.
- Allowed values:

| fact_type | Plain meaning | Example |
|---|---|---|
| `metric` | A real number that can be read again | `revenue was $5B` |
| `guidance` | Company forecast | `we expect $6B revenue` |
| `surprise` | Actual versus expected | `revenue beat by $0.2B` |
| `action_event` | A discrete thing that happened | `CEO resigned` |

Locked:

- One Driver must not carry multiple fact_types.
- If the same topic appears as metric, guidance, and surprise, create separate
  Drivers and link them.

Example:

```text
revenue           fact_type=metric
revenue_guidance  fact_type=guidance
revenue_surprise  fact_type=surprise
```

### 2.3 Driver Name

Locked:

- Driver name stores the reusable cause only.
- Brand, segment, geography, product, customer, and channel usually do not go in
  the name. They go in the slice.

Examples:

| Source idea | Final Driver | Slice |
|---|---|---|
| China revenue | `revenue` | `geography:china` |
| iPhone revenue | `revenue` | `product:iphone` |
| Taco Bell same-store sales | `same_store_sales` | `segment:taco_bell` |

Locked exception:

- Keep the object in the Driver name only when the object itself is the cause, or
  stripping it leaves no reusable cause.

Examples:

| Source idea | Final Driver | Reason |
|---|---|---|
| iPhone demand | `iphone_demand` | iPhone itself moves other companies |
| GLP-1 pressure | `glp1_pressure` | GLP-1 itself is the market cause |
| TikTok ban | `tiktok_ban` | The ban itself is the cause |

Locked:

- When unsure between name and slice, use slice.
- Direction words do not go in the Driver name.
- Impact words do not go in the Driver name.
- Scale words do not go in the Driver name.

Examples of words not in name:

```text
rose, fell, growth, decline, beat, miss, headwind, pressure,
billion, million, percent, bps
```

### 2.4 Per-X Denominators

Locked:

- Source-stated per-X denominators stay in the Driver name.
- Final unit stays the base unit.
- Different per-X means different Driver.
- These Drivers must never be `SAME_AS`.

Examples:

| Source | Driver | Unit |
|---|---|---|
| oil at $80/barrel | `oil_price_per_barrel` | `usd` |
| dividend per share | `dividend_per_share` | `usd` |
| sales per square foot | `sales_per_square_foot` | `usd` |
| revenue per user | `revenue_per_user` | `usd` |

Locked:

- If the source says `$ / X` but the Driver name does not include `_per_X`, this
  is a naming failure.
- If the source does not state per-X, do not invent it.

Example:

```text
"oil prices rose" -> oil_price
not oil_price_per_barrel
```

### 2.5 Measurement Is Not Name

Locked:

- Accounting and number-version words belong in `measurement`, not Driver name.

Examples:

| Source | Driver | measurement |
|---|---|---|
| adjusted EPS | `eps` | `{adjusted}` |
| diluted EPS | `eps` | `{diluted}` |
| GAAP basic EPS | `eps` | `{basic, gaap}` |
| constant-currency revenue | `revenue` | `{constant_currency}` |
| core EPS | `eps` | `{core}` |

This replaces older rules that used names like:

```text
adjusted_eps
diluted_eps
core_eps
```

### 2.6 Benchmark Identity

Locked:

- Benchmark identity stays in the Driver name when it changes the reusable cause.

Examples:

```text
brent_oil_price
wti_oil_price
```

### 2.7 Driver Units

Locked:

- Driver nodes have no unit fields.
- Units belong on DriverUpdate values.

### 2.8 Metric, Guidance, Surprise Family

Locked:

- Metric, guidance, and surprise are separate Drivers.
- Guidance and surprise Drivers point to exactly one base metric Driver with
  `BASE_METRIC`.

Example:

```text
revenue_guidance -[:BASE_METRIC]-> revenue
revenue_surprise -[:BASE_METRIC]-> revenue
```

Locked:

- Every terminal `_guidance` Driver must have exactly one valid `BASE_METRIC`.
- Every terminal `_surprise` Driver must have exactly one valid `BASE_METRIC`.
- The base metric Driver must exist.
- It is OK if the base metric is latent at first and has no updates yet.
- Only a terminal suffix counts.

Examples:

| Driver | BASE_METRIC rule |
|---|---|
| `cost_guidance` | Must point to `cost` |
| `guidance_revision_cost` | Does not qualify by suffix |

Locked:

- `BASE_METRIC` is not `SAME_AS`.
- Forecasts, results, and surprises can move stocks in opposite directions on the
  same day, so they must not be merged.

### 2.9 action_event Drivers

Locked:

- action_event Drivers do not require `BASE_METRIC`.
- An action can affect many metrics.
- Its relationship to metrics comes from evidence in events over time.
- If action-to-metric links are later cached for speed, the cache must be derived,
  non-identity, and never used to merge numeric series.

### 2.10 Synonyms And SAME_AS

Locked:

- `SAME_AS` is only for the exact same reusable cause/class.
- Synonyms are handled among compatible Drivers, not by `BASE_METRIC`.

Example:

```text
net_sales_guidance -[:BASE_METRIC]-> net_sales -[:SAME_AS]-> revenue
```

Locked:

- Missing a synonym is safer than a wrong merge.
- A missed synonym causes a missing comparison, not a corrupted numeric series.

### 2.11 Catalog Creation Contract

Locked:

- Catalog build creates or reuses Driver classes only.
- Catalog build never creates DriverUpdates.
- A Driver is born complete in the catalog run:
  - name
  - fact_type
  - optional links, only where safe and non-blocking
- Producers are the only creators of DriverUpdates.
- Historical backfill means running the same producer over old events.
- KPI-only evidence can create or reuse a Driver name only.
- KPI-only evidence never creates a DriverUpdate.
- No separate build-time seeder or change detector.
- No write-time recurrence rule such as ">2 events."
- A single event can create a valid DriverUpdate.

Reason:

- Mentions justify Driver names.
- DriverUpdates require producer-grade judgment about a real event-level fact.
- Two separate fact creators would become two sources of truth.

Approved preliminary producer split:

- We may have two kinds of producers.
- Final names are not locked yet.

| Plain role for now | What it writes | What it does not write |
|---|---|---|
| Fact-writing producer | Creates or updates a `DriverUpdate` | Does not write the verdict / `EXPLAINED_BY` stock-move judgment |
| Stock-move judgment producer | Writes the verdict / `EXPLAINED_BY` stock-move judgment, and may create the `DriverUpdate` if missing | Final create-only-when-responsible rule still needs approval |

Likely examples:

- `earnings-learner`
- `news-driver`

Still to clarify:

- Whether a stock-move judgment producer may create a missing `DriverUpdate` only
  when it judges that `DriverUpdate` actually explains the stock move.

### 2.12 Catalog Build Hierarchy

Locked:

- Build the catalog bottom-up:

```text
Company -> Industry -> Sector -> Global
```

- Raw name generation happens only at the leaf/company level.
- Higher levels consolidate; they do not raw-read sources.
- The same reconcile pattern runs at each level:
  - combine
  - dedupe same-meaning names
  - gate
  - Refute
  - deterministic write
  - validate
- Every merge is fail-close.
- Code assembles and validates structure.
- The LLM judges meaning only.

Locked:

- Same-name collisions are not silently auto-merged.
- Same-name review can return:
  - SAME
  - DIFFERENT
  - UNCLEAR
- SAME still needs Refute.
- DIFFERENT needs source-grounded split names and an assignment map.
- UNCLEAR is parked and not tradeable.
- Side lists such as skips and parked names are never used by consumers until
  resolved into the clean catalog.

### 2.13 Catalog Evidence And Chunking

Locked:

- Do not drop source text during catalog build.
- Fetch keeps full structured content.
- Chunking splits text to fit readers; it does not clip text.
- Chunking should prefer:
  - whole event
  - natural section or Q&A boundary
  - paragraph
  - sentence
  - char range as last resort
- Byte-exact conservation must prove every chunk reconstructs the original event
  text.
- Every chunk in the manifest must be processed.

Locked constants from the hierarchy plan:

```text
CHUNK_BUDGET_CHARS = 40000
SEED_MAX_RECORDS = 400
SEED_MAX_CHARS = 300000
RECONCILE_EVIDENCE_PER_RECORD = 20
```

These constants can be tuned later, but changing them should be explicit.

### 2.14 Catalog Record Shape

Locked target for catalog artifacts:

```text
driver_name
canonical_name
companies
evidence_refs
same_as_variants
fact_type
```

Locked:

- `same_as_variants` is a read-through aid for exact same-meaning names.
- Side lists are separate from the clean catalog:
  - skips
  - unresolved_rewrites
  - unresolved_same_name
- Clean consumers read only clean catalog records.

Needs alignment:

- Older catalog records had `optional_links`.
- Newer XBRL design moves concept/member enrichment to DriverUpdate facts.
- Final catalog artifact should not treat optional XBRL links as Driver identity.

### 2.15 Catalog Refresh

Locked:

- Append, not full rebuild, for normal refresh.
- Read only new source documents and new KPI names.
- Skip by source ID, not date.
- Late old-dated filings with new IDs must still be fetched.
- Old-to-old pairs stay frozen at every level.
- New-to-new pairs are judged normally.
- New-to-old seam pairs are judged carefully.
- At the seam, old Driver is canonical and immutable.
- Full re-judge is a fresh rebuild only, never append behavior.
- A single atomic pointer/state update should publish the branch.

Locked:

- Empty or all-skip deltas still advance the source ledger.
- Reject/skips learned during append should be carried forward so the same
  rejected evidence is not repeatedly re-judged.

Build gate:

- Verify Transcript ID immutability before first append.

### 2.16 Catalog Reader And Classifier Models

Locked from newest model notes:

- Use Opus 4.8 for reading documents into candidate Driver facts/names.
- Use Sonnet 5 for classifying what was found against the locked naming, slice,
  measurement, and fact_type rules.

Superseded:

- Older Fable reader plan.
- Older Opus two-pass reader plan.

## 3. DriverUpdate Decisions

### 3.1 What A DriverUpdate Is

Locked:

Owner review: approved.

- A DriverUpdate is one event-level fact about a Driver.
- It can be numeric or qualitative.
- It is not a mere mention.
- Every DriverUpdate is persisted, including a Driver's first appearance.
- Recurrence thresholds are read-time/display filters, never write-time gates.

Examples:

```text
Q1 revenue was $5B
revenue guidance was raised
Q1 EPS beat consensus
CEO resigned
```

### 3.2 Identity

Locked:

- Normal Event-sourced fact ID:

```text
event + driver + fact_scope
```

- Verdict ID:

```text
explained_target + driver + fact_scope + producer
```

Locked:

- Producer is not part of the fact ID.
- Producer is part of the verdict ID.
- Code builds IDs.
- The LLM never builds IDs.
- DriverUpdate facts do not store `evhash16` in the latest merged field design.
- DriverUpdate no-op reruns are detected by direct field comparison in the
  writer.
- Verdict / `EXPLAINED_BY` `evhash16` remains separate and tracks the verdict
  judgment.
- Macro/news DriverUpdate fact identity is not locked yet because its
  source/evidence shape is not locked yet.

Owner review: approved clarification.

- Producers may create or update `DriverUpdate` facts.
- A different producer does not create a separate `DriverUpdate` for the same
  fact.
- If event, Driver, and fact_scope are the same, it is the same `DriverUpdate`,
  even if more than one producer touched it.
- Producer identity only splits verdict / `EXPLAINED_BY` records.

### 3.2b Required Edges

Locked:

Owner review: approved, including `HAS_PERIOD` as period-bearing facts only.
Scope note: this block is the normal Event-sourced DriverUpdate shape. Macro/news
daily-company-move verdicts are covered separately in §3.17b.

```text
(:DriverUpdate)-[:OF_DRIVER]->(:Driver)
(:DriverUpdate)-[:FROM_SOURCE]->(:Event)
(:DriverUpdate)-[:HAS_PERIOD]->(:DriverPeriod)       when period exists
(:Event)-[:EXPLAINED_BY]->(:DriverUpdate)            when attributed
```

Locked:

- `OF_DRIVER` always exists exactly once.
- `FROM_SOURCE` always exists for the normal Event-sourced DriverUpdate path.
- `HAS_PERIOD` exists only for period-bearing facts.
- `EXPLAINED_BY` is optional.
- `FROM_SOURCE` and `EXPLAINED_BY` must not be collapsed into one edge.

Owner review: approved `EXPLAINED_BY` meaning.

Plain meaning:

| Edge | Meaning |
|---|---|
| `OF_DRIVER` | this fact is an instance of this Driver |
| `FROM_SOURCE` | this normal Event-sourced fact came from this Event |
| `EXPLAINED_BY` | this Event's stock move is attributed to this fact |

### 3.3 fact_scope

Locked:

Owner review: approved shape and order.

- `fact_scope` separates same-event facts for the same Driver.
- `fact_scope` is built from whichever structured parts exist:

```text
period + slice + measurement
```

Locked:

- If a period exists, fact_scope includes:

```text
period=<period_u_id>
```

- If a slice exists, fact_scope includes the slice.
- If measurement labels exist, fact_scope includes the sorted measurement set.
- `quote_hash` is only a fallback tie-breaker.
- Restatements with the same value should merge, not split by quote_hash.

Use `quote_hash` only when:

- the same event has more than one genuinely different fact,
- the structured slots cannot separate them,
- and the values are different enough that they must not merge.

### 3.4 DriverPeriod

Locked:

- Use `DriverPeriod`, not `GuidancePeriod`, for DriverUpdate periods.
- Use one edge:

```text
(:DriverUpdate)-[:HAS_PERIOD]->(:DriverPeriod)
```

Locked:

- Keep `gp_` IDs.
- Do not rename to `dp_`.

Example:

```text
gp_2025-01-01_2025-03-31
```

Locked:

- DriverPeriod means the calendar window the fact is about.
- It is not the event date.
- It is not the filing date.
- It is not a raw label like `Q1`.
- It does not say forecast versus actual.
- Forecast versus actual comes from `fact_type`.

Owner review: approved reuse of Guidance period machinery. Current Guidance
already has fiscal-to-calendar period math, calendar-to-fiscal helpers, SEC/FYE
lookup, `calendar_override`, and fail-closed missing-FYE behavior. Final Driver
work should share that machinery through `driver_period_resolver.py`, with
exact-date window support added for YTD, TTM, and cumulative facts.

### 3.5 Period Rules By fact_type

Locked:

Owner review: approved, then re-confirmed after checking the latest
Consolidation source.

| fact_type | Period rule |
|---|---|
| `guidance` | Period required |
| `metric` | Use period when stated, source-implied, or code-derivable |
| `surprise` | Use period when stated, source-implied, or code-derivable |
| `action_event` | Optional and rare; only when the action has a real stated window |

Locked:

- Do not force a period onto every fact.
- No real period window means no `HAS_PERIOD`.
- `gp_UNDEF` is only for undefined period-like wording.

Examples:

| Source | Period result |
|---|---|
| `FY2025 revenue guidance` | DriverPeriod required |
| `Q1 revenue was $5B` | DriverPeriod required |
| `Q1 EPS beat consensus` | DriverPeriod required |
| `CEO resigned` | no DriverPeriod |
| `going forward, margins should improve` | `gp_UNDEF` |
| `long-term margin target` | `gp_LT` |

### 3.6 Implied Reported Periods

Locked:

Owner review: approved, then re-confirmed after checking the latest
Consolidation source.

- For metric and surprise facts, the period may be implied by the source event.
- If the source event has exactly one clear reporting period, code may derive it.

Example:

```text
Q1 10-Q says "revenue grew 12%"
-> use the Q1 DriverPeriod
```

Locked:

- Do not guess from vague wording.
- If the source or event does not give exactly one clear period, do not attach a
  period.
- Exact source, SEC, or XBRL dates beat computed dates.

### 3.7 Exact-Date, YTD, And TTM Periods

Locked:

- Exact-date windows for YTD, TTM, and cumulative facts are approved.
- They do not break the Guidance period method because a period means the real
  calendar window the fact is about.
- Guidance keeps its current rule: only forward-looking guidance is extracted.
  Most YTD/TTM language in filings is actual or historical, so Guidance usually
  skips it. If a real future guidance item uses a cumulative window, exact-window
  support helps rather than hurts.
- Add exact-date period support to the shared period mechanism:

```text
period_start_date + period_end_date -> gp_<start>_<end>
```

Locked:

- YTD, TTM, and cumulative facts use exact windows when available.
- Do not collapse them into only the discrete quarter.
- Current Guidance code does not support `period_start_date` and
  `period_end_date` today, so this is a required Driver period extension.
- Use the clean `period_scope` value `exact_range` for exact start/end windows.
- Use exact windows only when the source, XBRL, or deterministic code gives a
  real start date and end date.
- For TTM, handle non-December fiscal year-ends and 52/53-week calendars
  carefully.
- Exact-window logic must run before normal quarter or annual logic so a
  cumulative period is not accidentally stored as one quarter.

Examples:

| Source | DriverPeriod |
|---|---|
| `nine months ended Sep 30, 2025` | `gp_2025-01-01_2025-09-30` if exact |
| `TTM ended Sep 30, 2025` | exact 12-month window |

Build gate:

- Prove YTD and TTM math for December and non-December fiscal year-end before
  wiring.

### 3.8 Period Node Properties

Locked:

- `DriverPeriod` stores only:

```text
id
u_id
start_date
end_date
```

Locked:

- DriverUpdate keeps source framing fields such as:

```text
fiscal_year
fiscal_quarter
period_scope
time_type
```

Reason:

- The same calendar window can be described differently by different companies or
  sources.

### 3.9 Period Consistency Validator

Locked:

- If DriverUpdate has `HAS_PERIOD -> DriverPeriod(id=X)`, then fact_scope must
  contain `period=X`.
- If fact_scope contains `period=X`, then DriverUpdate must have
  `HAS_PERIOD -> DriverPeriod(id=X)`.
- Do not hand-build duplicate period strings.

### 3.10 Slice

Locked:

Owner review: approved locked slice kinds and shape.

- Slice means which part of the company the fact is about.
- Slice is orthogonal to fact_type.
- Slices apply to all four fact_types.

Allowed slice kinds:

```text
segment
product
geography
customer
channel
entity_ownership
unknown
```

Locked:

- Brand is not a slice kind.
- A brand's kind comes from the XBRL axis or producer choice.
- Store type is `channel`, not its own kind.
- Period is not a slice.
- Multi-part slices keep every part and are code-sorted.

Example:

```text
segment:taco_bell;geography:china
```

Locked:

- `Total` is a real row only when the source explicitly says total, consolidated,
  or company-wide.
- Silence is not `Total`.
- If no clean part exists, use `quote_hash` only when needed to avoid merging
  different same-event facts.

### 3.11 Measurement

Locked:

Owner review: approved sorted multi-label set.

- Measurement is a sorted set inside fact_scope.
- Sort measurement labels by normalized text in deterministic code order before
  serializing fact_scope; do not preserve source-word order.
- Store the specific stated label, normalized for format only.
- Do not stem or merge measurement labels by meaning.
- Default is empty or unspecified.
- Never assume GAAP.
- GAAP/non-GAAP is a read-time grouping view, not the stored key.

Examples:

```text
{adjusted}
{diluted, gaap}
{adjusted, constant_currency}
{core}
{cash}
```

### 3.12 driver_state

Locked:

Owner review: approved location on `DriverUpdate`.

- `driver_state` lives on DriverUpdate.
- It never goes in Driver name.
- It is chosen from the Driver's fact_type lane.
- The raw quote remains the truth.
- `unknown` is allowed but should be rare.

Allowed states:

Owner review: approved final state lists. Exact vocabulary matches `DriverGraphSchema.md`, which the latest Consolidation notes still rely on.

| fact_type | allowed `driver_state` values |
|---|---|
| `metric` | `increased`, `decreased`, `unchanged`, `mixed`, `reported`, `persists`, `unknown` |
| `guidance` | `introduced`, `raised`, `lowered`, `reaffirmed`, `withdrawn`, `unknown` |
| `surprise` | `beat`, `in_line`, `missed`, `unknown` |
| `action_event` | `at_risk`, `announced`, `occurred`, `continued`, `resolved`, `canceled`, `suspended`, `rumored`, `failed`, `unknown` |

Metric state rules:

- Pick `increased` or `decreased` when direction is stated for the named
  variable.
- Pick `mixed` only when the same Driver moved both up and down in different
  parts.
- Pick `unchanged` for explicit flat or same-as-before statements.
- Pick `persists` for an ongoing condition with no up/down.
- Pick `reported` for a bare value with no comparison and no direction.
- Pick `unknown` only for a real metric fact with no readable state.
- Good/bad does not decide state; it belongs in the verdict.

Guidance state rules:

- `introduced`: first time issued.
- `raised`: prior guide moved up.
- `lowered`: prior guide moved down.
- `reaffirmed`: kept the same.
- `withdrawn`: pulled.

Surprise state rules:

- `beat`, `in_line`, and `missed` are versus an expectation.
- Expectation can be market consensus or the company's own prior guide/target.
- Actual versus prior-period actual is a metric change, not surprise.

Action-event state rules:

- `announced`: company stated its own action before completion.
- `occurred`: action happened or completed.
- `continued`: prior action is still ongoing with no new stage.
- `resolved`: dispute or issue settled/ended.
- `canceled`: company ended its own committed action.
- `suspended`: paused but same attempt may resume.
- `rumored`: third-party reported possible action not confirmed by company.
- `failed`: involuntary block/rejection or unmet external condition.
- `at_risk`: specific current adverse threat not yet realized and not the
  company's own plan.
- Generic risk-factor boilerplate is a mention only and should not create a
  DriverUpdate.

Build gate:

- Runtime writer must hard-fail if `driver_state` is not valid for the Driver's
  fact_type.

### 3.13 Values And Units

Locked:

- Use shared V2-style unit resolver.
- Owner review: approved. This intentionally reuses the proven Guidance
  extraction V2 unit path, moved/shared so Guidance and DriverUpdate use the
  same unit logic instead of two separate implementations.
- Extract number exactly as printed.
- Extract `unit_raw` exactly as printed.
- Producer must emit:

```text
unit_raw
unit_kind_hint
money_mode_hint when unit_kind_hint = money
```

Allowed `unit_kind_hint` values:

```text
money
ratio
count
multiplier
unknown
```

Allowed `money_mode_hint` values:

```text
aggregate
price_like
unknown
```

Locked:

- Code decides final unit and scaling.
- DriverUpdate resolves level and change separately.
- Money facts must provide `money_mode_hint`; bare `$` without aggregate versus
  price_like is unsafe.

Example:

```text
margin rose 60 bps to 17.6%
level_unit = percent
change_unit = basis_points
```

Allowed final units:

```text
m_usd
usd
percent
percent_yoy
percent_points
basis_points
count
x
unknown
```

Locked:

- Reject any final unit outside the enum.
- Reject per-X units such as `usd_per_share` or `dollars_per_store`.
- Qualitative DriverUpdates with no number skip unit resolution.
- Unit tests must check scaled values, not only unit strings.
- Glued money scales such as `$B` must scale correctly or fail loudly.
- Cents-on-aggregate must surface an error.

### 3.14 Value Fields

Owner review: approved. Latest Consolidation confirms the DriverUpdate unit
behavior for all 4 fact types, the use of `level_unit` and `change_unit`, no
unit fields on Driver, no `comparison_unit`, and null numeric fields for
numberless facts.

Implementation review note: before coding these fields, re-check the full
DriverUpdate field shape against the latest design and validate that the fields
still make sense for real metric, guidance, surprise, and action_event examples.

Latest merged design amendment:

- `level_bound` is retired.
- A point fills both bands: `level_low == level_high`.
- Low-only means floor.
- High-only means ceiling.
- Producers provide temporary `level_shape_hint` and `comparison_shape_hint`;
  the writer checks them against the stored fields, hard-fails mismatches, and
  discards them.
- `value_text` is added for guidance-only, numberless stated values.

Locked DriverUpdate value fields:

```text
level_low
level_high
level_unit
change_value
change_unit
comparison_low
comparison_high
comparison_baseline
value_text
```

Locked:

- All numeric fields are nullable.
- If the fact has no numeric value, all numeric fields stay null.
- For guidance-only numberless stated values, use `value_text`.
- For metric, surprise, and action_event numberless facts, `value_text` is
  forbidden; quote and state carry the fact.
- The quote remains the source of truth.
- `level_low` holds the low end of a range, the value of a floor, or the point
  value when paired with the same `level_high`.
- `level_high` holds the high end of a range, the value of a ceiling, or the
  point value when paired with the same `level_low`.
- `level_unit` is required when any `level_*` or `comparison_*` number is
  present.
- `change_value` is the signed size of the move itself, not the resulting level.
- `change_unit` may differ from `level_unit`.
- `comparison_low` and `comparison_high` store the stated baseline only when the
  source states it.
- A single-value comparison baseline fills both comparison fields.
- Do not derive comparison values from other nodes.

Level shape:

| Shape | Fields |
|---|---|
| point | `level_low == level_high`, both set |
| range | `level_low < level_high`, both set |
| floor | `level_low` set, `level_high=null` |
| ceiling | `level_high` set, `level_low=null` |
| no number | level fields null |

Write-time hard rules:

- Never write a point as low-only.
- Low-only always means floor.
- High-only always means ceiling.
- `level_shape_hint` must match the final `level_low` / `level_high` shape.
- `comparison_shape_hint` must match the final `comparison_low` /
  `comparison_high` shape.
- If `change_value` is present and state is directional, sign must match:
  - positive for increased, raised, beat
  - negative for decreased, lowered, missed
- A stated baseline with no matching enum still stores the number and leaves
  `comparison_baseline=null`.
- If multiple baselines are cited, store one primary baseline only.
- Other baselines stay in the quote.
- `change_value` is store-when-stated only.
- If level and comparison are present but no delta is stated, leave
  `change_value=null`.
- Ranged moves have no second slot; keep ranged move detail in quote.
- For rate/growth Drivers whose value is the rate itself, put the rate in
  `level_low`, not `change_value`.
- `value_text` is guidance-only, allowed only when every numeric value field is
  null, and should hold a short normalized stated value such as
  `low single digits`.

Allowed `comparison_baseline` values:

```text
consensus
prior_year
sequential_period
previous_guidance
null
```

- For `metric`, `consensus` is forbidden; consensus comparisons belong on the
  matching `_surprise` Driver.

### 3.14b Conditions

Locked by latest merged design:

- `conditions` is guidance-only for now.
- It is allowed only when the source states a real caveat or assumption.
- The same caveat must also remain inside the quote.
- Action-event `conditions` is only a future revisit trigger if real production
  data proves the field is needed there.

### 3.15 Comparison Values

Locked:

Owner review: approved.

- DriverUpdate has comparison values but no `comparison_unit`.
- Comparison values must use the same unit as `level_unit`.
- If the source compares against a different-unit value, keep that detail in the
  quote for now.
- Do not invent `comparison_unit` unless the schema changes later.

### 3.16 Direction And Impact

Locked:

Owner review: approved.

- Direction of the Driver belongs in `driver_state`.
- Impact on the company or stock belongs in the EXPLAINED_BY verdict.
- Direction or impact words do not belong in Driver name.

Example:

```text
"FX headwind"
Driver = foreign_exchange
driver_state = what FX did, if stated
negative impact = EXPLAINED_BY verdict
```

### 3.17 EXPLAINED_BY Verdict

Locked:

Scope note: this section covers the normal Event-sourced verdict. The macro/news
daily-company-move parallel is in §3.17b.

- The causal verdict is an edge, not a node.
- Edge direction:

```text
(:Event)-[:EXPLAINED_BY]->(:DriverUpdate)
```

- The fact can exist without a verdict.
- A verdict should exist only when a producer attributes the event's stock move
  to the DriverUpdate.

Owner review: approved.

Verdict fields:

| field | Meaning | Values |
|---|---|---|
| `stock_impact` | direction of the DriverUpdate's push on the event move | `long`, `short` |
| `weightage` | standalone force/importance, not a share | `0.1` to `1.0` in deciles, or null |
| `confidence` | certainty that attribution is true | `0` to `100` in deciles |
| `produced_mode` | whether judged live or later | `live`, `backfill` |
| `llm_producer` | producer identity | e.g. `earnings-learner`, `news-driver` |
| `id` | code-built verdict key | explained_target + driver + fact_scope + producer |
| `created` | write time | timestamp |
| `evhash16` | hash of judgment fields | excludes produced_mode |

Locked:

- `stock_impact`, `weightage`, and `confidence` are separate axes.
- `weightage` is not forced to sum across drivers.
- A lone DriverUpdate is not automatically weightage 1.0.
- `weightage=null` means direction judged but force not sized.
- `share_i = weightage_i / sum(weightage_j)` is read-time only.
- `signed_force = weightage * stock_impact` is read-time only.
- Realized stock return is never stored on the verdict.
- A live verdict beats a backfill verdict at the same key.
- Backfill must not overwrite live.
- Live may replace backfill.

Build gate:

- Writer must hard-fail invalid verdict fields.
- `weightage` and `confidence` must use deciles only.
- There is no sum constraint.

### 3.17b Macro / News Daily-Company-Move Verdicts

Locked:

Owner review: approved current parallel shape; source evidence details remain
open.

Core parallel:

```text
Normal event driver:
Event -[:EXPLAINED_BY]-> DriverUpdate -[:OF_DRIVER]-> Driver

Macro/news daily-move driver:
DailyCompanyMoveEvent -[:EXPLAINED_BY]-> DriverUpdate -[:OF_DRIVER]-> Driver
```

Use `DailyCompanyMoveEvent`, not plain `DailyMoveEvent`.

Meaning:

```text
DailyCompanyMoveEvent = one company + one date + one significant stock move
```

Full graph shape:

```text
(:DailyCompanyMoveEvent)-[:EXPLAINED_BY]->(:DriverUpdate)
(:DriverUpdate)-[:OF_DRIVER]->(:Driver)

(:DailyCompanyMoveEvent)-[:FOR_COMPANY]->(:Company)
(:DailyCompanyMoveEvent)-[:ON_DATE]->(:Date)

(:Date)-[:HAS_PRICE]->(:Company)
```

Important source rule:

- Do not assume `(:DriverUpdate)-[:FROM_SOURCE]->(:News)` for this path.
- Source evidence for macro/news DriverUpdates is not locked yet.

Why this is the true parallel:

| Part | Normal Event-sourced driver | Macro/news daily-company-move driver |
|---|---|---|
| Thing being explained | `Event` | `DailyCompanyMoveEvent` |
| Main verdict edge | `Event -[:EXPLAINED_BY]-> DriverUpdate` | `DailyCompanyMoveEvent -[:EXPLAINED_BY]-> DriverUpdate` |
| Driver fact | `DriverUpdate` | `DriverUpdate` |
| Reusable Driver | `DriverUpdate -[:OF_DRIVER]-> Driver` | `DriverUpdate -[:OF_DRIVER]-> Driver` |
| Company link | existing `Event -> Company` edge | `DailyCompanyMoveEvent -[:FOR_COMPANY]-> Company` |
| Date link | event timestamp / event date | `DailyCompanyMoveEvent -[:ON_DATE]-> Date` |
| Price data | return read from existing Event-to-Company return edge | raw price data stays on `Date -[:HAS_PRICE]-> Company` |
| Many drivers | one Event can have many `EXPLAINED_BY` edges | one DailyCompanyMoveEvent can have many `EXPLAINED_BY` edges |
| Many companies | current Events usually point to one Company | each company/date gets its own DailyCompanyMoveEvent |

Multi-company macro example:

```text
AAPL on 2026-06-30 -> DailyCompanyMoveEvent_AAPL_2026-06-30
MSFT on 2026-06-30 -> DailyCompanyMoveEvent_MSFT_2026-06-30
NVDA on 2026-06-30 -> DailyCompanyMoveEvent_NVDA_2026-06-30

All three DailyCompanyMoveEvent nodes may point to the same DriverUpdate.
```

Verdict key:

```text
explained_target + driver + fact_scope + producer
```

Where `explained_target` is:

- `Event` for normal Event-sourced verdicts.
- `DailyCompanyMoveEvent` for macro/news daily-company-move verdicts.

Reference skill: `.claude/skills/news-impact/SKILL.md` - eventually alter this
skill to match the locked design.

### 3.18 company_confirmed

Locked:

Owner review: approved boolean, guidance-only.

- Preserve `company_confirmed` for guidance facts created from or merged with
  Guidance extraction.
- Target location is DriverUpdate.
- It applies only to `fact_type=guidance` updates.
- It is absent on `metric`, `surprise`, and `action_event`.
- It is boolean:

```text
company_confirmed = true / false
```

- It does not live on Driver, because confirmation is event/source-specific.
- It is not part of DriverUpdate identity.

Current Guidance extraction pipeline check:

- Current `guidance_writer.py`, `guidance_write_cli.py`, `guidance_ids.py`, and
  the guidance extraction field schema do not write or require
  `company_confirmed`.
- Current guidance news rules extract only statements attributed to company
  management or the company itself.
- Current guidance news rules skip analyst, consensus, Street, price-target,
  rating-action, third-party, and ambiguous guidance claims.

Therefore:

```text
DriverUpdates generated from current GuidanceUpdate pipeline output
-> company_confirmed = true
```

Reserved future meaning:

```text
company_confirmed = false
```

means a future explicitly allowed guidance-like claim was not confirmed by the
company. The current Guidance extraction pipeline does not produce those rows.

Older WIP recommended enum values `confirmed` and `unconfirmed`. That is
superseded by the latest Consolidation boolean decision.

## 4. Guidance Integration Decisions

### 4.1 General Strategy

Locked:

- DriverCatalog and DriverUpdate should mirror Guidance and GuidanceUpdate as much
  as possible.
- Reuse proven Guidance mechanisms when they fit.
- Change only what must change for Driver.

### 4.2 Shared Period Resolver

Locked:

- Extract a shared period resolver for Guidance and DriverUpdate.
- Target module name:

```text
driver_period_resolver.py
```

Locked:

- Guidance writer and DriverUpdate writer should call the same shared resolver.
- The old Guidance period math should be reused, not reimplemented separately.
- Current status: Guidance has the proven fiscal/calendar foundation; the final
  shared Driver wrapper is still target design work, not yet built.

Build gate:

- Old Guidance `_ensure_period()` output must equal new
  `ensure_driver_period()` output on the same guidance item.

### 4.3 Shared Unit Resolver

Locked:

- Guidance and DriverUpdate should call the same shared unit resolver.
- Guidance calls it for guidance values/ranges.
- DriverUpdate calls it separately for level and change.

Build gate:

- Move resolver to final production location.
- Add permanent tests for:
  - 9-unit enum
  - value scaling
  - no per-X units
  - no unit fields on Driver
  - per-X naming lint

### 4.4 Guidance IDs

Locked:

- DriverUpdate should use the Guidance ID recipe:

```text
event + driver + fact_scope
```

Locked:

- No producer in fact ID.
- Producer goes in verdict ID.
- Code builds IDs.
- LLM does not build IDs.

### 4.5 GuidanceUpdate To DriverUpdate Mapping

Locked target:

- Unify is the target.
- Guidance becomes `fact_type=guidance` in the Driver process.
- Regenerate guidance through the Driver/guidance producer path.
- Do not re-key/migrate the existing live GuidanceUpdate nodes as the main
  strategy.
- Regenerate first, verify sample equivalence, then retire old nodes only after
  the replacement is proven.

Locked latest transition:

- Final target is `DriverUpdate` only for guidance facts.
- Regenerate guidance through the Driver/guidance producer path.
- Verify sample equivalence against old Guidance output.
- Retire old Guidance nodes only after the replacement is proven.
- Do not keep `GuidanceUpdate` as the final instance label.
- Do not dual-label `DriverUpdate:GuidanceUpdate` as the final model.

Remaining owner approval:

- Approve the latest DriverUpdate field amendments captured in
  `FinalDesign/09_DriverUpdate_Fields.md` §8.

Known target rules:

- Guidance facts become or align with `fact_type=guidance` DriverUpdates.
- Guidance periods become shared `DriverPeriod` links.
- Guidance units use the shared unit resolver.
- Guidance concept links inherit or align through the base metric where needed.
- Preserve `company_confirmed`.
- Guidance producer must read prior guidance value history before setting
  `introduced`, `raised`, `lowered`, or `reaffirmed`.

Optional bridge:

- A read-only Driver-to-Guidance bridge can be built as temporary scaffolding only
  if the predictor needs guidance before full unification.
- It should not be treated as final unification.
- If `canonical_driver` is written back to Guidance anchors, it must be derived
  from edges and set-replaced; it must not become a second source of truth.

### 4.6 Guidance, Surprise, And XBRL Concepts

Locked:

- Do not concept-match `_guidance` or `_surprise` names directly.
- Resolve the base metric Driver concept.
- Guidance and surprise inherit through `BASE_METRIC`.

Example:

```text
revenue_guidance -> BASE_METRIC -> revenue -> xbrl concept
```

### 4.7 Event Taxonomy And Amendments

Owner decision:

- Decide whether the old 24-tag Guidance 8-K event taxonomy is useful for
  Driver extraction.

Owner decision:

- Decide how amendments should be represented and reconciled.

### 4.8 Report Processing Scope

Owner decision:

- Decide whether DriverUpdates require reprocessing every 10-K and 10-Q.
- Possible target: process 8-Ks, transcripts, and news for DriverUpdates, while
  linking existing 10-K/10-Q/XBRL facts to Drivers for metric facts.
- This could save tokens, but needs a final design before build.

## 5. XBRL Decisions

### 5.1 XBRL Links Are Enrichment

Locked:

- XBRL links are optional enrichment.
- They are never identity.
- Missing links are acceptable.
- Wrong links are the danger.
- XBRL links attach to DriverUpdate, not Driver.

### 5.2 XBRL Member And Slice Linking

Locked:

- The member side uses frozen axis to kind lookup.
- Runtime classification:

```text
axis in SLICE_AXES      -> use kind
axis in NON_SLICE_AXES  -> skip
unknown axis            -> provisional slice
```

Locked:

- Unknown axes are never silently skipped.
- Unknown axes become provisional because over-splitting is safer than merging.

### 5.3 Slice Axis Kinds

Locked:

- The six slice dimensions are:

```text
segment
product
geography
customer
channel
entity_ownership
```

Plus:

```text
unknown
```

Locked:

- The actual axis table comes from `XBRL_SliceAxis_Catalog.md`.
- Axis names alone are not reliable.
- Classification must be based on members and verified data.

### 5.4 XBRL Member Menu

Locked:

Owner review: approved.

- Company menu includes:
  - XBRL members bucketed by frozen axis table.
  - values the catalog already used.

Locked:

- Menu must be point-in-time.
- Use only data available at or before the event time.
- No future data.
- For 8-Ks, transcripts, and news, usually use latest prior 10-Q/10-K member data
  unless the event itself has usable member data.

Producer outcomes:

| Case | Result |
|---|---|
| Value is on menu | Pick it |
| Real value is off menu | Coin in style |
| Real value has no known kind | Use `unknown:value` |
| Unknown XBRL axis | Carry axis in value, such as `axis:value` |
| No clean part | Use `quote_hash` only if needed |

Locked:

- Code validates format only.
- Code must never snap to a near-match.

Approved producer menu rule:

- Before writing a `DriverUpdate`, the producer should be shown a point-in-time
  company parts menu.
- If the source clearly refers to a menu item, the producer should reuse that
  exact menu value.
- If the real part is not on the menu, the producer may coin a new in-style
  slice value.
- The official XBRL member link is optional enrichment.
- Code supplies the official link when the picked value came from an XBRL menu
  row or can be matched safely.
- The XBRL member link is never the `DriverUpdate` identity.

### 5.5 Slice Reconciliation

Locked:

- First-written slice value wins.
- Slice values are immutable after write.
- Exact normalized XBRL member labels can fold into existing values.
- Producer can reuse existing menu values when source clearly names the same part.
- No fuzzy code merge.
- No match creates a new row.

### 5.6 Elimination Guard

Locked:

- Hard exclusions use a frozen exact-qname list.
- Every hard exclusion is logged.
- Regex elimination filters are forbidden.
- A hard-excluded qname that later shows real fact activity is demoted to
  provisional.

Locked:

- Corporate, other, unallocated, blended, raw intersegment, and reconciling rows
  are provisional, not deleted.
- Provisional rows are quarantined from cross-company comparison.

### 5.7 Entity Slice Caution

Locked:

- `entity_ownership` is the least clean slice bucket.
- Equity-method and JV cases are strongest.
- Other entity rows should be treated conservatively and often provisional.

### 5.8 Cross-Company Slice Value Comparison

Locked:

- Cross-company slice value matching is not part of this design yet.
- `International` or `Other` can mean different things at different companies.
- Provisional values are excluded from cross-company comparison.

Future layer:

- If built later, cross-company slice-value matching must use the same conservative
  merge rule: confident same only, else keep separate.

### 5.9 XBRL Concept Linking

Locked goal:

- Attach the exact XBRL concept a company reports for the DriverUpdate when one
  exists.
- Otherwise attach nothing.

Locked pipeline:

```text
guard
-> build company concept menu
-> LLM pick one menu concept or null
-> in-menu check
-> adversarial verify
-> deterministic backstop and veto
-> emit qname or abstain
```

Locked:

- Value is withheld from live inference.
- Value matching is only for offline tests.
- String/token matching is only proof or audit support.
- Curated dictionaries are rejected.
- The company menu is the source of allowed answers.
- Never emit a concept that is not in the menu.
- Unsure means abstain.

### 5.10 XBRL Concept Guards

Locked:

- Guards reject conceptless or unsafe classes before model calls.
- Prefer fact_type routing in production.
- Regex guards are fallback for raw names.

Guarded examples:

```text
action events
macro causes
ratios
margins
growth
EBITDA
free cash flow
non-GAAP
adjusted
```

Locked:

- `tax_rate` and `effective_tax_rate` are not rejected just because they are rates.
  They can have real XBRL concepts.

### 5.11 XBRL Concept Backstop

Locked:

- Deterministic backstop and veto run after LLM verify.
- It can only abstain.
- It must never create a link.

Backstop rules include:

- Instant share count must not map to duration weighted-average.
- Bare `eps` and `share_count` prefer diluted over basic by convention.
- Per-share metrics must not map to total-dollar concepts.
- Part-for-whole component mismatches are vetoed.

Build gate:

- Current hand deny set is incomplete.
- Before full-universe rollout, add or evaluate a calculation-hierarchy veto so
  part-for-whole errors can be caught generally.

### 5.12 XBRL Concept Model

Locked for concept linking:

- Use Haiku with deterministic guards, verify, backstop, and veto.

Caution:

- The "1 wrong" result is a tuning-set result, not a universal guarantee.
- Full-universe validation is still pending.

Different model decision:

- For DriverCatalog document reading, newer notes prefer Opus 4.8.
- For rule classification, newer notes prefer Sonnet 5.
- This is not a conflict: different steps use different models.

### 5.13 XBRL Concept Menu

Locked:

- Menu is company-scoped.
- Menu contains consolidated top-level numeric concepts the company reports.
- Segment facts are excluded from concept menu because slice/member linking is a
  separate problem.
- Historical DriverUpdates need point-in-time menu cutoff.
- Live resolution can use latest available data.

### 5.14 XBRL Concept Write

Locked:

- Store `DriverUpdate.xbrl_qname`.
- Also create:

```text
(:DriverUpdate)-[:MAPS_TO_CONCEPT]->(:Concept)
```

Locked:

- Write is best-effort.
- Write is non-blocking.
- Write is idempotent.
- No Concept match means no edge, but the DriverUpdate still writes.

### 5.15 XBRL Concept Routing By fact_type

Locked:

| fact_type | Concept-link rule |
|---|---|
| `metric` | Link the DriverUpdate fact when safe |
| `guidance` | Inherit base metric concept through `BASE_METRIC` |
| `surprise` | Inherit base metric concept through `BASE_METRIC` |
| `action_event` | Always abstain |

## 6. Read-Time Decisions

Locked:

- Consumers must not group by Driver alone.
- Consumers must not group by period alone.
- Consumers must group with enough identity to avoid mixing different facts.

Minimum safe grouping includes:

```text
company
driver
fact_type
slice
period
measurement
unit
time_type when relevant
BASE_METRIC family when comparing related facts
```

Locked:

- Do not strip `_guidance` or `_surprise` and merge those rows into the base
  metric numeric series.
- Guidance, metric, and surprise can share a period but remain different read
  buckets.

Example:

```text
revenue_guidance + gp_2025...  -> forecast bucket
revenue          + gp_2025...  -> actual bucket
revenue_surprise + gp_2025...  -> surprise bucket
```

## 7. Required Validators

### 7.1 Driver Validators

Build gates:

- Every Driver has exactly one allowed fact_type.
- Driver has no unit fields.
- Catalog build creates Driver only, not DriverUpdate.
- KPI-only evidence does not create DriverUpdate.
- Source-stated per-X appears in name.
- Measurement words do not become Driver name suffixes.
- Direction and impact words do not become Driver name words.
- Terminal `_guidance` and `_surprise` Drivers have exactly one `BASE_METRIC`.
- `action_event` Drivers have no required `BASE_METRIC`.
- SAME_AS never links metric to guidance or surprise as if they were the same
  numeric series.

### 7.2 DriverUpdate Identity Validators

Build gates:

- Fact ID uses event + driver + fact_scope.
- This fact ID rule is for normal Event-sourced DriverUpdates.
- Verdict ID adds producer.
- Producer is absent from fact ID.
- Every DriverUpdate has exactly one `OF_DRIVER`.
- Every normal Event-sourced DriverUpdate has exactly one `FROM_SOURCE`.
- Macro/news DriverUpdate `FROM_SOURCE` behavior is not locked yet.
- If period edge exists, fact_scope has the same period ID.
- If fact_scope has period ID, period edge exists.
- quote_hash is present only when structured scope cannot separate facts.
- Same value restatements do not split only because quote text differs.
- `driver_state` is valid for Driver.fact_type.
- Numberless facts keep numeric fields null.
- Guidance-only numberless stated values may use `value_text`; other lanes use
  quote and state.
- `change_value` sign matches directional state when present.
- comparison fields are store-when-stated only.
- `comparison_baseline` is valid enum or null.

### 7.2b Verdict Validators

Build gates:

- EXPLAINED_BY edge key is explained_target + driver + fact_scope + producer.
- For normal Event-sourced verdicts, explained_target is the Event.
- For macro/news daily-company-move verdicts, explained_target is the
  DailyCompanyMoveEvent.
- `stock_impact` is `long` or `short`.
- `weightage` is null or one of `0.1` through `1.0` in deciles.
- `confidence` is one of `0, 10, ..., 100`.
- `produced_mode` is `live` or `backfill`.
- Backfill does not overwrite live.
- No sum constraint is applied to weightage.
- produced_mode is excluded from verdict evhash.

### 7.3 Period Validators

Build gates:

- Quarter, annual, half-year, month, exact-range, and sentinel periods work.
- `gp_ST`, `gp_MT`, `gp_LT`, `gp_UNDEF` work.
- instant periods collapse to one-day windows.
- `calendar_override=true` works.
- Missing required fiscal-year-end raises. No December default.
- Exact source/XBRL dates win over computed month-boundary dates.
- YTD, TTM, and cumulative exact windows create `gp_<start>_<end>`.
- metric/guidance/surprise with same period remain separate read buckets.
- Periodless action_event has no HAS_PERIOD.

### 7.4 Unit Validators

Build gates:

- Final unit is one of the 9 allowed units.
- No per-X units.
- `level_unit` and `change_unit` resolve separately.
- Numeric scaling is tested, not just unit strings.
- Qualitative facts have null numeric/unit fields.
- Cents-on-aggregate guard works.
- Glued money scales such as `$1.5B` scale correctly.
- Invalid producer unit hints fail closed.

### 7.5 Slice Validators

Build gates:

- Slice kind is one of six allowed kinds or unknown.
- Store type maps to channel.
- Brand is not a kind.
- Multi-part slices are sorted and complete.
- `Total` appears only on explicit total/company-wide source.
- Unknown XBRL axis becomes provisional.
- Code never near-match snaps slice values.
- Elimination hard-exclude uses exact qnames only.
- Every hard exclusion is logged.

### 7.6 XBRL Concept Validators

Build gates:

- Linker never emits a concept outside the company menu.
- Conceptless classes abstain.
- Guidance and surprise inherit through BASE_METRIC.
- action_event abstains.
- Historical menus use event-time cutoff.
- Backstop/veto can only abstain.
- Wrong-link sampling checks balance and period_type.
- Abstention rates are tracked by fact_type.
- Full-universe concept-link validation is run before production rollout.

### 7.7 Catalog Build Validators

Build gates:

- Every source chunk in `chunks_manifest.json` is processed.
- Byte-exact chunk reconstruction equals original event text.
- No catalog record appears in side lists at the same time.
- Side lists are excluded from consumer read-through.
- Every SAME_AS or rewrite in catalog output has an approved decision.
- Fold parent evidence equals exact child evidence union.
- Every child name is accounted for exactly once in fold output or side lists.
- same_as_variants mirrors approved SAME_AS links.
- Same-name split assignment maps assign every source ref exactly once.
- High-blast fusions carry required second Refute proof.
- Catalog assembly is deterministic code, not free-form LLM-written JSON.

## 8. Build Order

Recommended order:

1. Approve this final decision file.
2. Create topic files from this decision file:
   - `02_DriverCatalog.md`
   - `03_DriverUpdate.md`
   - `04_GuidanceIntegration.md`
   - `05_XBRL.md`
   - `06_BuildPlan.md`
3. Align old hierarchical catalog build with new required `fact_type`,
   measurement, and slice rules.
4. Extract shared unit resolver.
5. Extract shared period resolver.
6. Add naming, state, number, verdict, unit, period, fact_scope, and
   BASE_METRIC validators.
7. Wire DriverCatalog reader prompt to final naming/slice/measurement rules.
8. Wire DriverCatalog classifier to final fact_type and rule-classification
   model choice.
9. Wire DriverUpdate writer to shared period and unit resolvers.
10. Add XBRL member/slice menu logic with point-in-time cutoff.
11. Add XBRL concept linker with backstop/veto.
12. Re-run full restaurant Driver flow and validate every output.
13. Re-run XBRL slice-axis census on fresh graph snapshot.
14. Run full-universe concept-link validation.
15. Implement the decided GuidanceUpdate transition:
   regenerate as `DriverUpdate`, verify equivalence, then retire old
   Guidance nodes.
16. Reconcile append/incremental refresh with final catalog artifact shape.

## 9. Open Owner Decisions

Needs owner approval:

- Approve the DriverUpdate field amendment bundle in
  `FinalDesign/09_DriverUpdate_Fields.md` §8:
  - guidance-only `value_text`
  - self-describing point/range/floor/ceiling shape
  - retire `DriverUpdate.evhash16`
- Whether to build the temporary read-only guidance bridge before full unification.
- Whether to add `canonical_driver` back-pointer on Guidance anchors or stay
  edge-only.
- Whether to reuse the old 24-tag Guidance 8-K event taxonomy.
- Amendment handling.
- Whether to process every 10-K/10-Q for DriverUpdates, or link existing XBRL
  facts and reports to Drivers to save tokens.
- Whether calculation-hierarchy veto is mandatory before any production concept
  link rollout, or only before full-universe rollout.
- How final graph Driver/SAME_AS maps back to JSON catalog artifacts and
  `same_as_variants`.
- Final producer role names and the exact rule for when a stock-move judgment
  producer may create a missing `DriverUpdate`.
- Final source/evidence link shape for macro/news DriverUpdates.
- Exact macro/news DriverUpdate identity when source evidence is not one Event.
- Exact `DailyCompanyMoveEvent` identity fields.
- Exact `DailyCompanyMoveEvent` return fields, if any.
- Exact threshold rule for creating a `DailyCompanyMoveEvent`.

## 10. Decisions This File Replaces

Replaced:

- Brand or segment in Driver name by default.
- `store_type` as its own fact_scope kind.
- `adjusted_eps`, `core_eps`, and similar measurement-bearing names.
- Guidance-only period nodes.
- Raw period text in identity.
- Fake periods on periodless actions.
- Catalog-build seeding of DriverUpdates.
- Write-time recurrence thresholds.
- XBRL link as identity.
- XBRL concept link on Driver instead of DriverUpdate.
- Optional XBRL links as unchecked catalog identity fields.
- Live value-based concept matching.
- Live token/string concept matching.
- Direct concept matching for `_guidance` or `_surprise`.
- Fable reader as final model.
- Opus two-pass reader as final model.
- Unit V1.
- Physical `$ / X` becoming `unknown`.
- Per-X units.
- Fuzzy code merges.
- Axis-name-only slice classification.
- Regex elimination filtering.
- `Total` as default for missing slice.
