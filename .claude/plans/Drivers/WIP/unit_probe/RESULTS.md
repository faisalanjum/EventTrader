# Unit-Canonicalization Borrow Probe — RESULTS

> **⏫ UPDATE 2026-06-20 — POST-RULE RE-RUN (supersedes the V1/V2 scoreboard below).**
> Both probes now run through the REAL shared `unit_resolver.py` (not the throwaway
> `unit_extract.py`), with the locked per-X-in-name rule applied to `cases.json` (now 117 cases).
> **Hints-on (production path) = 117/117 units · 0 value · 0 lint failures.** Label-only: all
> must-pass sections green (per-X names 7/7, lint 2/2, money-value 12/12, ratios 37/37); 29 cases
> fall to `unknown` label-only BY DESIGN (need the producer's coarse kind hint) — all 29 fixed once
> the hint is supplied. Adversarially verified: not circular on the parts that matter (ratio subtype,
> ×1000 scaling, count value, lint are all real, hint-independent); no expectations were fudged.
> The V1-vs-V2 analysis below is FROZEN history — it's why V2 was chosen; V2 is now locked.

**Goal in plain words:** can DriverUpdates reuse the *exact* guidance unit code
(turn a raw unit like "$", "%", "bps" into one of 9 canonical units) for ALL
four fact types — metric, surprise, guidance, action_event — not just guidance?

**Method:** imported the REAL production code (no re-implementation), ran 115
verified cases through BOTH entry points, compared the code's answer to a
human-derived expected unit.

## Import proof (the real code, at runtime)

```
canonicalize_unit.__module__ = guidance_ids
guidance_ids.__file__        = /home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/guidance_ids.py
slug.__module__              = guidance_ids
build_guidance_ids.__module__= guidance_ids
```

- V1 path = `canonicalize_unit(unit_raw, slug(driver_name))` + `canonicalize_value`
- V2 path = `build_guidance_ids(..., resolution_mode='v2')`, reading `resolved_*` fields
- Probe run with **NO LLM hints** by default → this measures the *label-only*
  borrow (the honest worst case). Hint-rescue confirmed separately below.

## Headline scoreboard (115 cases, all 4 fact types)

| Path | Matched | % |
|------|---------|---|
| V1 (`canonicalize_unit`) | 62/115 | 53.9% |
| **V2 (`build_guidance_ids`, production)** | **80/115** | **69.6%** |

### By fact_type

| fact_type | total | V1 match | V2 match |
|-----------|------:|---------:|---------:|
| metric | 48 | 21 | 26 |
| surprise | 20 | 14 | 19 |
| guidance | 25 | 17 | 21 |
| action_event | 22 | 10 | 14 |

### By trap_flag (V2 / production path)

| trap_flag | total | V1 match | V2 match |
|-----------|------:|---------:|---------:|
| normal | 35 | 32 | 31 |
| known-hard | 28 | 13 | 21 |
| generalization-trap | 12 | 6 | 8 |
| inherited-bug | 26 | 5 | 17 |
| enum-gap | 14 | 6 | 3 |

## The crux: NEITHER path is safe alone

- **V1-only misses (V1 wrong, V2 right): 34** — V1 cannot read glued `$B`/`$M`,
  cannot read `per share`/`cents`, cannot read embedded multipliers (`2.5x`), and
  treats per-unit prices (ASP/ADR/RevPAR) as aggregate `m_usd`. **Borrowing V1 is unsafe.**
- **V2 regressions (V1 right, V2 wrong): 16** — V2 has NO surface signal for bare
  count nouns, so `stores`/`employees`/`units`/`shares` (which V1 maps to `count`
  via its alias table) collapse to `unknown` in V2. V2 also over-claims money for
  `$/physical` units (`$/barrel` → `m_usd` or `usd`, human wants `unknown`).

So a clean borrow needs **V2's evidence resolver PLUS V1's count-alias table PLUS
a physical-denominator guard.** No single existing path covers all 4 fact types.

## What rescues the misses (confirmed separately, NOT in the default run)

The production design feeds V2 LLM hints (`unit_kind_hint`, `money_mode_hint`).
Re-ran the misses WITH hints:

| input | default V2 | + hint | result |
|-------|-----------|--------|--------|
| `total_headcount` / `employees` | unknown | `unit_kind_hint=count` | **count** ✅ |
| `store_count` / `stores` | unknown | `unit_kind_hint=count` | **count** ✅ |
| `subscriber_count` / `million` | unknown | `unit_kind_hint=count` | **count** ✅ |
| `layoffs` / `jobs` | unknown | `unit_kind_hint=count` | **count** ✅ |
| `dividend` / `$` | m_usd | `money_mode_hint=price_like` | **usd** ✅ |
| `special_dividend` / `$` | m_usd | `money_mode_hint=price_like` | **usd** ✅ |
| `oil_price` / `$/barrel` | m_usd | `money/aggregate` hint | **m_usd** ❌ (no physical guard) |

**Conclusion:** with hints, the count-noun and per-share-label misses self-correct.
The TWO irreducible gaps that NO hint fixes are: (1) physical-unit prices
(`$/barrel`, `$/ton`) — the 9-enum has no slot; (2) non-USD currency (`€M`) — no
currency axis. Both correctly want `unknown` but V2 confidently mislabels them.

## Borrow verdict per fact_type

| fact_type | borrowable? | conditions |
|-----------|-------------|------------|
| guidance | YES (home turf) | V2 + clean `unit_raw` (split `$ B`, not `$B`, or value mis-scales 1000x) |
| surprise | YES | V2; unit is delta-agnostic (beat/miss sign lives in value). Count surprises need a count hint. |
| metric | PARTIAL | V2 + count hint for count metrics; physical-unit prices fall to wrong money unit |
| action_event | PARTIAL | V2 + per-share routing (driver name or hint) + count hint; qualitative facts skip the code entirely |

**Net:** the methodology IS borrowable across all 4 fact types, but only the V2
resolver, only with the producer supplying `unit_kind_hint`/`money_mode_hint`, and
only if you add (a) a `$/physical` → `unknown` guard and (b) widen count-noun
coverage. The literal V1 function named in the mission (`canonicalize_unit`) is the
WRONG thing to borrow — it fails 53/115.

## Full mismatch list (V2 / production path) — 35 cases

| fact_type | driver_name | unit_raw | expected | V1 | V2 | suspected mode |
|-----------|-------------|----------|----------|----|----|----------------|
| metric | same_store_sales | (empty) | percent | unknown | unknown | unit-in-quote (no parser) |
| metric | commodity_cost | $/barrel | unknown | unknown | m_usd | inherited-bug |
| metric | steel_cost | $/ton | unknown | unknown | m_usd | inherited-bug |
| metric | subscriber_count | subscribers | count | unknown | unknown | enum-gap |
| metric | total_headcount | employees | count | count | unknown | enum-gap (V2 regress) |
| metric | store_count | stores | count | count | unknown | enum-gap (V2 regress) |
| metric | subscriber_count | million | count | m_usd | unknown | enum-gap |
| metric | active_users | million | count | m_usd | unknown | enum-gap |
| metric | employee_count | thousand | count | m_usd | unknown | enum-gap |
| metric | restaurant_count | restaurants | count | unknown | unknown | enum-gap |
| metric | restaurant_count | units | count | count | unknown | enum-gap (V2 regress) |
| metric | store_count | (empty) | count | unknown | unknown | enum-gap |
| metric | net_new_stores | stores | count | count | unknown | enum-gap (V2 regress) |
| metric | subscriber_count | K | count | m_usd | unknown | enum-gap |
| metric | drive_thru_lane_count | lanes | count | unknown | unknown | enum-gap |
| metric | loyalty_members | members | count | unknown | unknown | enum-gap |
| metric | system_units | x | count | x | x | hard-surface-wins (unfixable by hint) |
| surprise | subscriber_surprise | count | count | count | unknown | enum-gap (V2 regress; word 'count' has no surface) |
| guidance | share_count_guidance | M | count | m_usd | unknown | enum-gap |
| guidance | store_count_guidance | stores | count | count | unknown | enum-gap (V2 regress) |
| guidance | oil_price_realization_guidance | $/barrel | unknown | unknown | m_usd | inherited-bug |
| action_event | special_dividend | $ | usd | m_usd | m_usd | label-heuristic-misfire |
| action_event | dividend | $ | usd | m_usd | m_usd | label-heuristic-misfire |
| action_event | quarterly_dividend | per share | usd | unknown | unknown | enum-gap (per-share needs $ + label) |
| action_event | stock_repurchase | billion | m_usd | m_usd | unknown | bare-scale-word (V2 regress) |
| action_event | layoffs | jobs | count | unknown | unknown | enum-gap |
| action_event | workforce_reduction | employees | count | count | unknown | enum-gap (V2 regress) |
| guidance | dividend | $ | usd | m_usd | m_usd | label-heuristic-misfire |
| metric | oil_price | $/barrel | unknown | unknown | m_usd | inherited-bug |
| metric | oil_price | $ per barrel | unknown | unknown | usd | inherited-bug (formatting flips V2) |
| action_event | shares_repurchased | shares | count | count | unknown | enum-gap (V2 regress) |
| metric | weighted_average_basic_shares_outstanding | million | count | m_usd | unknown | enum-gap (_outstanding tail) |
| metric | diluted_shares_outstanding | billion | count | m_usd | unknown | enum-gap (_outstanding tail) |
| metric | fuel_cost_per_barrel | $/barrel | unknown | unknown | usd | inherited-bug (per_barrel→'per'→price_like) |
| action_event | store_openings | stores | count | count | unknown | enum-gap (V2 regress) |

## Files

- `unit_extract.py` — standalone wrapper, imports the real `guidance_ids`
- `cases.json` — 115 flattened verified cases
- `run_probe.py` — runner (table + summaries + mismatch list + import proof)
- Run: `/usr/bin/python3 /home/faisal/EventMarketDB/.claude/plans/Drivers/WIP/unit_probe/run_probe.py`

## Full raw stdout

```
==============================================================================
IMPORT PROOF (the REAL guidance_ids.py was imported, not re-implemented)
==============================================================================
  canonicalize_unit.__module__ = guidance_ids
  guidance_ids.__file__ = /home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/guidance_ids.py
  slug.__module__ = guidance_ids
  build_guidance_ids.__module__ = guidance_ids

==============================================================================
PER-CASE TABLE  (V1 = canonicalize_unit; V2 = build_guidance_ids v2 mode)
==============================================================================
  # fact_type    driver_name                            unit_raw       exp           V1            V2            V1?  V2? 
--------------------------------------------------------------------------------------------------------------------------
  1 metric       same_store_sales                       %              percent       percent       percent       OK   OK  
  2 metric       comparable_sales                       %              percent       percent       percent       OK   OK  
  3 metric       occupancy_rate                         %              percent       percent       percent       OK   OK  
  4 metric       interest_rate                          %              percent       percent       percent       OK   OK  
  5 metric       gross_margin                           %              percent       percent       percent       OK   OK  
  6 metric       gross_margin                           bps            basis_points  basis_points  basis_points  OK   OK  
  7 metric       gross_margin                           percentage poi percent_points percent_points percent_points OK   OK  
  8 metric       same_store_sales                       % yoy          percent_yoy   percent_yoy   percent_yoy   OK   OK  
  9 metric       comparable_sales                       %              percent_yoy   percent       percent_yoy   xx   OK  
 10 metric       same_store_sales                       (empty)        percent       unknown       unknown       xx   xx  
 11 metric       commodity_cost                         $/barrel       unknown       unknown       m_usd         OK   xx  
 12 metric       steel_cost                             $/ton          unknown       unknown       m_usd         OK   xx  
 13 metric       net_interest_margin                    %              percent       percent       percent       OK   OK  
 14 metric       average_daily_rate                     $              usd           m_usd         usd           xx   OK  
 15 metric       average_selling_price                  $              usd           m_usd         usd           xx   OK  
 16 metric       subscriber_count                       subscribers    count         unknown       unknown       xx   xx  
 17 metric       total_headcount                        employees      count         count         unknown       OK   xx  
 18 metric       store_count                            stores         count         count         unknown       OK   xx  
 19 metric       subscriber_count                       million        count         m_usd         unknown       xx   xx  
 20 metric       active_users                           million        count         m_usd         unknown       xx   xx  
 21 metric       employee_count                         thousand       count         m_usd         unknown       xx   xx  
 22 metric       restaurant_count                       restaurants    count         unknown       unknown       xx   xx  
 23 metric       restaurant_count                       units          count         count         unknown       OK   xx  
 24 metric       headcount                              (empty)        count         unknown       count         xx   OK  
 25 metric       store_count                            (empty)        count         unknown       unknown       xx   xx  
 26 metric       net_new_stores                         stores         count         count         unknown       OK   xx  
 27 metric       subscriber_count                       K              count         m_usd         unknown       xx   xx  
 28 metric       store_count_growth                     %              percent_yoy   percent       percent_yoy   xx   OK  
 29 metric       shares_outstanding                     million        count         count         count         OK   OK  
 30 metric       drive_thru_lane_count                  lanes          count         unknown       unknown       xx   xx  
 31 metric       loyalty_members                        members        count         unknown       unknown       xx   xx  
 32 metric       system_units                           x              count         x             x             xx   xx  
 33 surprise     eps_surprise                           $              usd           usd           usd           OK   OK  
 34 surprise     eps_surprise                           per share      usd           unknown       usd           xx   OK  
 35 surprise     eps_surprise                           cents          usd           unknown       usd           xx   OK  
 36 surprise     revenue_surprise                       $M             m_usd         unknown       m_usd         xx   OK  
 37 surprise     revenue_surprise                       $B             m_usd         unknown       m_usd         xx   OK  
 38 surprise     revenue_surprise                       %              percent       percent       percent       OK   OK  
 39 surprise     margin_surprise                        bps            basis_points  basis_points  basis_points  OK   OK  
 40 surprise     gross_margin_surprise                  pp             percent_points percent_points percent_points OK   OK  
 41 surprise     eps_surprise_pct                       %              percent       percent       percent       OK   OK  
 42 surprise     revenue_surprise                       €M             unknown       unknown       unknown       OK   OK  
 43 surprise     same_store_sales_surprise              %              percent       percent       percent       OK   OK  
 44 surprise     eps_beat_magnitude                     $              usd           usd           usd           OK   OK  
 45 surprise     revenue_miss                           $M             m_usd         unknown       m_usd         xx   OK  
 46 surprise     subscriber_surprise                    count          count         count         unknown       OK   xx  
 47 surprise     ebitda_surprise                        $M             m_usd         unknown       m_usd         xx   OK  
 48 surprise     eps_surprise_x                         x              x             x             x             OK   OK  
 49 guidance     revenue_guidance                       $ B            m_usd         unknown       m_usd         xx   OK  
 50 guidance     revenue_guidance                       $B             m_usd         unknown       m_usd         xx   OK  
 51 guidance     eps_guidance                           $              usd           usd           usd           OK   OK  
 52 guidance     operating_margin_guidance              %              percent       percent       percent       OK   OK  
 53 guidance     capex_guidance                         $ B            m_usd         unknown       m_usd         xx   OK  
 54 guidance     gross_margin_guidance                  %              percent       percent       percent       OK   OK  
 55 guidance     dividend_per_share_guidance            $              usd           usd           usd           OK   OK  
 56 guidance     free_cash_flow_guidance                $ M            m_usd         unknown       m_usd         xx   OK  
 57 guidance     revenue_growth_guidance                % yoy          percent_yoy   percent_yoy   percent_yoy   OK   OK  
 58 guidance     tax_rate_guidance                      %              percent       percent       percent       OK   OK  
 59 guidance     share_count_guidance                   M              count         m_usd         unknown       xx   xx  
 60 guidance     net_interest_margin_guidance           bps            basis_points  basis_points  basis_points  OK   OK  
 61 guidance     ebitda_margin_guidance                 percentage poi percent_points percent_points percent_points OK   OK  
 62 guidance     leverage_ratio_guidance                x              x             x             x             OK   OK  
 63 guidance     store_count_guidance                   stores         count         count         unknown       OK   xx  
 64 guidance     oil_price_realization_guidance         $/barrel       unknown       unknown       m_usd         OK   xx  
 65 action_event dividend_per_share                     $              usd           usd           usd           OK   OK  
 66 action_event special_dividend                       $              usd           m_usd         m_usd         xx   xx  
 67 action_event dividend                               $              usd           m_usd         m_usd         xx   xx  
 68 action_event quarterly_dividend                     per share      usd           unknown       unknown       xx   xx  
 69 action_event dividend_per_share                     cents          usd           unknown       usd           xx   OK  
 70 action_event share_repurchase                       $B             m_usd         unknown       m_usd         xx   OK  
 71 action_event buyback_authorization                  $              m_usd         m_usd         m_usd         OK   OK  
 72 action_event stock_repurchase                       billion        m_usd         m_usd         unknown       OK   xx  
 73 action_event asset_impairment                       $B             m_usd         unknown       m_usd         xx   OK  
 74 action_event goodwill_impairment                    $M             m_usd         unknown       m_usd         xx   OK  
 75 action_event restructuring_charge                   $              m_usd         m_usd         m_usd         OK   OK  
 76 action_event layoffs                                %              percent       percent       percent       OK   OK  
 77 action_event layoffs                                jobs           count         unknown       unknown       xx   xx  
 78 action_event workforce_reduction                    employees      count         count         unknown       OK   xx  
 79 action_event headcount_reduction                    %              percent       percent       percent       OK   OK  
 80 action_event debt_issuance                          $M             m_usd         unknown       m_usd         xx   OK  
 81 action_event senior_notes_offering                  $B             m_usd         unknown       m_usd         xx   OK  
 82 action_event dividend_yield                         %              percent       percent       percent       OK   OK  
 83 guidance     dividend                               $              usd           m_usd         m_usd         xx   xx  
 84 guidance     dividend_per_share                     $              usd           usd           usd           OK   OK  
 85 metric       oil_price                              $/barrel       unknown       unknown       m_usd         OK   xx  
 86 metric       oil_price                              $ per barrel   unknown       unknown       usd           OK   xx  
 87 metric       revpar                                 $              usd           m_usd         usd           xx   OK  
 88 metric       revpar_per_room                        $/room         usd           unknown       usd           xx   OK  
 89 metric       net_leverage                           x              x             x             x             OK   OK  
 90 metric       valuation_multiple                     2.5x           x             unknown       x             xx   OK  
 91 surprise     margin_beat                            bps            basis_points  basis_points  basis_points  OK   OK  
 92 guidance     operating_margin                       %              percent       percent       percent       OK   OK  
 93 guidance     margin_expansion                       percentage poi percent_points percent_points percent_points OK   OK  
 94 surprise     revenue_growth                         % yoy          percent_yoy   percent_yoy   percent_yoy   OK   OK  
 95 guidance     revenue                                €M             unknown       unknown       unknown       OK   OK  
 96 guidance     eps                                    $              usd           usd           usd           OK   OK  
 97 guidance     capex                                  $B             m_usd         unknown       m_usd         xx   OK  
 98 action_event buyback                                $B             m_usd         unknown       m_usd         xx   OK  
 99 action_event shares_repurchased                     shares         count         count         unknown       OK   xx  
100 metric       adjusted_eps_diluted                   $              usd           m_usd         usd           xx   OK  
101 metric       core_eps_basic                         $              usd           m_usd         usd           xx   OK  
102 metric       weighted_average_basic_shares_outstand million        count         m_usd         unknown       xx   xx  
103 metric       diluted_shares_outstanding             billion        count         m_usd         unknown       xx   xx  
104 metric       eps                                    per share      usd           unknown       usd           xx   OK  
105 metric       dividend_per_share                     cents          usd           unknown       usd           xx   OK  
106 guidance     net_leverage_ratio                     2.5x           x             unknown       x             xx   OK  
107 metric       headcount                              (empty)        count         unknown       count         xx   OK  
108 metric       revenue                                €M             unknown       unknown       unknown       OK   OK  
109 metric       fuel_cost_per_barrel                   $/barrel       unknown       unknown       usd           OK   xx  
110 metric       average_selling_price                  $              usd           m_usd         usd           xx   OK  
111 surprise     eps_surprise                           %              percent       percent       percent       OK   OK  
112 surprise     revenue_surprise                       bps            basis_points  basis_points  basis_points  OK   OK  
113 action_event share_repurchase_authorization         $B             m_usd         unknown       m_usd         xx   OK  
114 action_event store_openings                         stores         count         count         unknown       OK   xx  
115 guidance     organic_revenue_growth                 % yoy          percent_yoy   percent_yoy   percent_yoy   OK   OK  

==============================================================================
SUMMARY BY FACT_TYPE
==============================================================================
fact_type       total   V1 match   V2 match
------------------------------------------
metric             48         21         26
surprise           20         14         19
guidance           25         17         21
action_event       22         10         14
------------------------------------------
TOTAL             115         62         80

V1 (canonicalize_unit) : 62/115 matched (53.9%)
V2 (build_guidance_ids): 80/115 matched (69.6%)  <- PRODUCTION PATH

==============================================================================
SUMMARY BY TRAP_FLAG (V2 / production path)
==============================================================================
trap_flag               total   V1 match   V2 match
--------------------------------------------------
normal                     35         32         31
known-hard                 28         13         21
generalization-trap        12          6          8
inherited-bug              26          5         17
enum-gap                   14          6          3

==============================================================================
MISMATCH LIST — cases where the PRODUCTION (V2) path != expected
==============================================================================
V2 misses: 35 of 115

  [metric] same_store_sales  unit_raw=''
      expected=percent  V1=unknown  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=other  trap_flag=generalization-trap

  [metric] commodity_cost  unit_raw='$/barrel'
      expected=unknown  V1=unknown  V2=m_usd  (v2 kind=money, mode=aggregate)
      suspected_mode=inherited-bug  trap_flag=inherited-bug

  [metric] steel_cost  unit_raw='$/ton'
      expected=unknown  V1=unknown  V2=m_usd  (v2 kind=money, mode=aggregate)
      suspected_mode=inherited-bug  trap_flag=inherited-bug

  [metric] subscriber_count  unit_raw='subscribers'
      expected=count  V1=unknown  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [metric] total_headcount  unit_raw='employees'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=normal

  [metric] store_count  unit_raw='stores'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=normal

  [metric] subscriber_count  unit_raw='million'
      expected=count  V1=m_usd  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=known-hard

  [metric] active_users  unit_raw='million'
      expected=count  V1=m_usd  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=known-hard

  [metric] employee_count  unit_raw='thousand'
      expected=count  V1=m_usd  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=known-hard

  [metric] restaurant_count  unit_raw='restaurants'
      expected=count  V1=unknown  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [metric] restaurant_count  unit_raw='units'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=normal

  [metric] store_count  unit_raw=''
      expected=count  V1=unknown  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [metric] net_new_stores  unit_raw='stores'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=generalization-trap

  [metric] subscriber_count  unit_raw='K'
      expected=count  V1=m_usd  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=known-hard

  [metric] drive_thru_lane_count  unit_raw='lanes'
      expected=count  V1=unknown  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [metric] loyalty_members  unit_raw='members'
      expected=count  V1=unknown  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [metric] system_units  unit_raw='x'
      expected=count  V1=x  V2=x  (v2 kind=multiplier, mode=unknown)
      suspected_mode=other  trap_flag=generalization-trap

  [surprise] subscriber_surprise  unit_raw='count'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [guidance] share_count_guidance  unit_raw='M'
      expected=count  V1=m_usd  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [guidance] store_count_guidance  unit_raw='stores'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=generalization-trap

  [guidance] oil_price_realization_guidance  unit_raw='$/barrel'
      expected=unknown  V1=unknown  V2=m_usd  (v2 kind=money, mode=aggregate)
      suspected_mode=inherited-bug  trap_flag=inherited-bug

  [action_event] special_dividend  unit_raw='$'
      expected=usd  V1=m_usd  V2=m_usd  (v2 kind=money, mode=aggregate)
      suspected_mode=label-heuristic-misfire  trap_flag=inherited-bug

  [action_event] dividend  unit_raw='$'
      expected=usd  V1=m_usd  V2=m_usd  (v2 kind=money, mode=aggregate)
      suspected_mode=label-heuristic-misfire  trap_flag=inherited-bug

  [action_event] quarterly_dividend  unit_raw='per share'
      expected=usd  V1=unknown  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [action_event] stock_repurchase  unit_raw='billion'
      expected=m_usd  V1=m_usd  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=other  trap_flag=known-hard

  [action_event] layoffs  unit_raw='jobs'
      expected=count  V1=unknown  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=enum-gap

  [action_event] workforce_reduction  unit_raw='employees'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=known-hard

  [guidance] dividend  unit_raw='$'
      expected=usd  V1=m_usd  V2=m_usd  (v2 kind=money, mode=aggregate)
      suspected_mode=label-heuristic-misfire  trap_flag=inherited-bug

  [metric] oil_price  unit_raw='$/barrel'
      expected=unknown  V1=unknown  V2=m_usd  (v2 kind=money, mode=aggregate)
      suspected_mode=inherited-bug  trap_flag=enum-gap

  [metric] oil_price  unit_raw='$ per barrel'
      expected=unknown  V1=unknown  V2=usd  (v2 kind=money, mode=price_like)
      suspected_mode=inherited-bug  trap_flag=inherited-bug

  [action_event] shares_repurchased  unit_raw='shares'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=known-hard

  [metric] weighted_average_basic_shares_outstanding  unit_raw='million'
      expected=count  V1=m_usd  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=inherited-bug

  [metric] diluted_shares_outstanding  unit_raw='billion'
      expected=count  V1=m_usd  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=inherited-bug

  [metric] fuel_cost_per_barrel  unit_raw='$/barrel'
      expected=unknown  V1=unknown  V2=usd  (v2 kind=money, mode=price_like)
      suspected_mode=inherited-bug  trap_flag=enum-gap

  [action_event] store_openings  unit_raw='stores'
      expected=count  V1=count  V2=unknown  (v2 kind=unknown, mode=unknown)
      suspected_mode=enum-gap  trap_flag=normal

==============================================================================
V1-ONLY MISSES (V1 wrong, V2 correct) — why you must borrow V2, not V1
==============================================================================
count: 34
  [metric] comparable_sales unit_raw='%': exp=percent_yoy V1=percent V2=percent_yoy
  [metric] average_daily_rate unit_raw='$': exp=usd V1=m_usd V2=usd
  [metric] average_selling_price unit_raw='$': exp=usd V1=m_usd V2=usd
  [metric] headcount unit_raw='': exp=count V1=unknown V2=count
  [metric] store_count_growth unit_raw='%': exp=percent_yoy V1=percent V2=percent_yoy
  [surprise] eps_surprise unit_raw='per share': exp=usd V1=unknown V2=usd
  [surprise] eps_surprise unit_raw='cents': exp=usd V1=unknown V2=usd
  [surprise] revenue_surprise unit_raw='$M': exp=m_usd V1=unknown V2=m_usd
  [surprise] revenue_surprise unit_raw='$B': exp=m_usd V1=unknown V2=m_usd
  [surprise] revenue_miss unit_raw='$M': exp=m_usd V1=unknown V2=m_usd
  [surprise] ebitda_surprise unit_raw='$M': exp=m_usd V1=unknown V2=m_usd
  [guidance] revenue_guidance unit_raw='$ B': exp=m_usd V1=unknown V2=m_usd
  [guidance] revenue_guidance unit_raw='$B': exp=m_usd V1=unknown V2=m_usd
  [guidance] capex_guidance unit_raw='$ B': exp=m_usd V1=unknown V2=m_usd
  [guidance] free_cash_flow_guidance unit_raw='$ M': exp=m_usd V1=unknown V2=m_usd
  [action_event] dividend_per_share unit_raw='cents': exp=usd V1=unknown V2=usd
  [action_event] share_repurchase unit_raw='$B': exp=m_usd V1=unknown V2=m_usd
  [action_event] asset_impairment unit_raw='$B': exp=m_usd V1=unknown V2=m_usd
  [action_event] goodwill_impairment unit_raw='$M': exp=m_usd V1=unknown V2=m_usd
  [action_event] debt_issuance unit_raw='$M': exp=m_usd V1=unknown V2=m_usd
  [action_event] senior_notes_offering unit_raw='$B': exp=m_usd V1=unknown V2=m_usd
  [metric] revpar unit_raw='$': exp=usd V1=m_usd V2=usd
  [metric] revpar_per_room unit_raw='$/room': exp=usd V1=unknown V2=usd
  [metric] valuation_multiple unit_raw='2.5x': exp=x V1=unknown V2=x
  [guidance] capex unit_raw='$B': exp=m_usd V1=unknown V2=m_usd
  [action_event] buyback unit_raw='$B': exp=m_usd V1=unknown V2=m_usd
  [metric] adjusted_eps_diluted unit_raw='$': exp=usd V1=m_usd V2=usd
  [metric] core_eps_basic unit_raw='$': exp=usd V1=m_usd V2=usd
  [metric] eps unit_raw='per share': exp=usd V1=unknown V2=usd
  [metric] dividend_per_share unit_raw='cents': exp=usd V1=unknown V2=usd
  [guidance] net_leverage_ratio unit_raw='2.5x': exp=x V1=unknown V2=x
  [metric] headcount unit_raw='': exp=count V1=unknown V2=count
  [metric] average_selling_price unit_raw='$': exp=usd V1=m_usd V2=usd
  [action_event] share_repurchase_authorization unit_raw='$B': exp=m_usd V1=unknown V2=m_usd

==============================================================================
V2-REGRESSIONS (V1 correct, V2 wrong) — where borrowing V2 LOSES vs V1
==============================================================================
count: 16
  [metric] commodity_cost unit_raw='$/barrel': exp=unknown V1=unknown V2=m_usd
  [metric] steel_cost unit_raw='$/ton': exp=unknown V1=unknown V2=m_usd
  [metric] total_headcount unit_raw='employees': exp=count V1=count V2=unknown
  [metric] store_count unit_raw='stores': exp=count V1=count V2=unknown
  [metric] restaurant_count unit_raw='units': exp=count V1=count V2=unknown
  [metric] net_new_stores unit_raw='stores': exp=count V1=count V2=unknown
  [surprise] subscriber_surprise unit_raw='count': exp=count V1=count V2=unknown
  [guidance] store_count_guidance unit_raw='stores': exp=count V1=count V2=unknown
  [guidance] oil_price_realization_guidance unit_raw='$/barrel': exp=unknown V1=unknown V2=m_usd
  [action_event] stock_repurchase unit_raw='billion': exp=m_usd V1=m_usd V2=unknown
  [action_event] workforce_reduction unit_raw='employees': exp=count V1=count V2=unknown
  [metric] oil_price unit_raw='$/barrel': exp=unknown V1=unknown V2=m_usd
  [metric] oil_price unit_raw='$ per barrel': exp=unknown V1=unknown V2=usd
  [action_event] shares_repurchased unit_raw='shares': exp=count V1=count V2=unknown
  [metric] fuel_cost_per_barrel unit_raw='$/barrel': exp=unknown V1=unknown V2=usd
  [action_event] store_openings unit_raw='stores': exp=count V1=count V2=unknown

==============================================================================
JSON_SUMMARY_BEGIN
{"total": 115, "v1_matched": 62, "v2_matched": 80, "by_fact_type": {"metric": {"total": 48, "v1_matched": 21, "v2_matched": 26}, "surprise": {"total": 20, "v1_matched": 14, "v2_matched": 19}, "guidance": {"total": 25, "v1_matched": 17, "v2_matched": 21}, "action_event": {"total": 22, "v1_matched": 10, "v2_matched": 14}}, "v2_misses": 35, "v1_only_misses": 34, "v2_regressions": 16}
JSON_SUMMARY_END
```
