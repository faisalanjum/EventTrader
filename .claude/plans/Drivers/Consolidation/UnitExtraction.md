## Guidance Units 
    
    a. Can we borrow exact methodology for extracting UNITS in DriverUpdate exactly as we did for GuidanceUpdates (not just for fact_type: guidance) but for all. Is there any downside to doing that? 

    b. if answer to above is yes, IS IT POSSIBLE TO EXTRACT (meaning create a new) function or seperate file of code or module or class or package so this process is independent and we can just try it now and test it as comprehensively as possible? 

    c. Do units apply to just DriverUpdates or to Driver nodes themselves

    d. A lot of DriverUpdate nodes will not have units since some of them are truly unit less ?

    e. In guidance extraction: ~19.8% of facts have unit=unknown


## Proposal (to be validated & understood)

1.

2. 

## To check (Claude)

Question checked:
- Can DriverUpdate borrow the Guidance unit methodology for all fact types?
- Can the unit logic become a standalone shared resolver?
- What must change on Driver Catalog vs DriverUpdate?

Method used:
- Imported the real `guidance_ids.py`; no reimplementation.
- First ran a 115-case cross-fact-type probe as baseline evidence.
- Then corrected stale per-X expectations and re-ran the probe as 117 cases through the real `unit_resolver.py`.
- Built `unit_resolver.py` as the shared wrapper and tested it separately.

Empirical scoreboard — the table below is the OLD pre-rule evidence (kept as the audit trail). ✅ RE-RUN DONE 2026-06-20 — corrected result is right after it:

```
┌────────────────────────┬──────────────┬────────────┬──────────────┬──────────────┬──────────────┬──────────────────────────────────────────┐
│ Path                   │ Overall      │ metric     │ surprise     │ guidance     │ action_event │ Status                                   │
├────────────────────────┼──────────────┼────────────┼──────────────┼──────────────┼──────────────┼──────────────────────────────────────────┤
│ V1 canonicalize_unit   │ 62/115 = 54% │ 21/48=44%  │ 14/20=70%    │ 17/25=68%    │ 10/22=45%    │ Old baseline; do not borrow V1           │
│ V2, no hints           │ 80/115 = 70% │ 26/48=54%  │ 19/20=95%    │ 21/25=84%    │ 14/22=64%    │ Old evidence; missing required hints     │
│ V2 + unit-kind hint    │108/115 = 94% │ 42/48=88%  │ 20/20=100%   │ 24/25=96%    │ 22/22=100%   │ Old evidence; superseded by 117/117 below│
└────────────────────────┴──────────────┴────────────┴──────────────┴──────────────┴──────────────┴──────────────────────────────────────────┘
```

✅ **Post-rule re-run (2026-06-20) — through the REAL `unit_resolver.py`; corpus now 117 cases (per-X flipped to `_per_X` + `usd`; `system_units 'x'` → count):**
- **Hints-on (production path) = 117/117 = 100%** units · 0 value failures · 0 lint failures (all 4 fact types 100%).
- Label-only (no hints): all must-pass sections green — per-X names 7/7, naming-lint 2/2, money-value ×1000 12/12, ratios 37/37; 29 cases fall to `unknown` label-only BY DESIGN (need the producer kind hint) — all 29 fixed once the hint is supplied.
- Adversarially verified: not circular (ratio-subtype / scaling / count / lint are real, hint-independent work); no fudged expectations; `€M → unknown` is the only true enum gap (safe under-merge).

Why the old table is stale (now corrected by the re-run above):
- The old probe expected `$ / X` physical prices to become `unknown`.
- Final rule changed that: source-stated per-X belongs in `driver_name`, and the final unit stays a base enum value, usually `usd`.
- Example: `oil_price $/barrel` should become `oil_price_per_barrel`, `level_unit = usd`.

Verdict:
- Yes, borrow the shared resolver approach for all fact types.
- Do not borrow V1 by itself.
- Use the V2-style resolver with producer hints: `unit_kind_hint` and `money_mode_hint`.
- Test DriverUpdate with both unit and scaled value checks, not unit-string checks only.

Keep from the old analysis:
- Extract number exactly as written.
- Extract `unit_raw` exactly as written.
- Require `unit_kind_hint`.
- Require `money_mode_hint` when `unit_kind_hint = money`.
- Let code decide final unit and scaling.
- Keep clean `unit_raw`; avoid glued `$1.5B`.
- Keep cents guard for aggregate money.
- No unit fields on Driver itself.
- DriverUpdate calls resolver separately for `level_*` and `change_*`.
- Qualitative DriverUpdates with no number skip unit resolution.
- Comparison values must share `level_unit` unless schema later adds `comparison_unit`.

Change from the old analysis:
- Remove the old "physical-unit prices -> unknown" conclusion.
- Remove the proposed `$ / physical -> unknown` guard.
- Add this guard instead: source has `$ / X` but `driver_name` lacks `_per_X` = naming failure / flag for rename.
- Catalog side is not "nothing about units" anymore: Driver still has no unit fields, but Catalog naming must preserve source-stated per-X in the name.
- Unit enum must be all 9: `usd`, `m_usd`, `percent`, `percent_yoy`, `percent_points`, `basis_points`, `count`, `x`, `unknown`.

Files / deliverables to keep in mind:
- `.claude/plans/Drivers/WIP/unit_probe/unit_resolver.py` = shared resolver wrapper.
- `.claude/plans/Drivers/WIP/unit_probe/test_unit_resolver.py` = focused tests.
- `.claude/plans/Drivers/WIP/unit_probe/run_probe.py` and `run_probe_hints.py` = the 117-case probes, NOW re-pointed to the real `unit_resolver.py` (label-only + hints-on); evidence/validation, not production code.
- `.claude/plans/Drivers/WIP/unit_probe/FINDINGS.md` = fuller empirical notes.
- `.claude/plans/Drivers/WIP/unit_probe/RESULTS.md` = raw run output; the old `$ / physical -> unknown` headline is now corrected by a 2026-06-20 banner at the top (post-rule numbers). Plus `.claude/plans/Drivers/WIP/naming_probe/` = the catalog-NAMING proof (3 blind Opus readers, 100%).

Rerun / Reverify — ✅ ALL DONE 2026-06-20:
- ✅ Probe expectations corrected (now 117 cases) + re-run through the real `unit_resolver.py`.
- ✅ `oil_price $/barrel` → `oil_price_per_barrel`, unit `usd`.
- ✅ `steel_cost $/ton` → `steel_cost_per_ton`, unit `usd`.
- ✅ `fuel_cost_per_barrel $/barrel` → unit `usd`.
- ✅ `system_units` `unit_raw='x'` → cleaned to `''` (the hard `x` multiplier surface beat even a count hint; it was a bad producer token, NOT a resolver bug).
- ✅ Read-time key confirmed to ignore the quote (`scripts/earnings/builders/guidance_history.py:340-341` keys on name + unit, not quote) — the reason per-X must live in the name.

Current run status (2026-06-20 — Steps 1-3 COMPLETE):
- `test_unit_resolver.py` passes **29/29 cases + 7 guard checks** (asserts unit AND scaled value; incl. the hint-blind naming lint, glued-`$B`→×1000, cents-on-aggregate→error, range→None).
- `run_probe_hints.py` = **117/117, 0 failures** (the old "7 failures" are FIXED — expectations corrected to the per-X rule). `run_probe.py` (label-only) also re-pointed to `unit_resolver.py`.
- Follow-on: the catalog-NAMING side (does the LLM reader actually coin `oil_price_per_barrel`?) was separately proven 2026-06-20 — see `WIP/naming_probe/RESULTS.md` (3 blind Opus readers, 100%, no flicker).



## Final Driver Naming Rules

 # Driver Naming — Set-In-Stone Rules

  ## Rules

  0. fact_scope — same Driver, same event, more than one fact = which version of this driver-fact inside the event.
     Covers: period / segment / geography / store-type / quote-hash fallback (when no clean label).
     It separates same-event versions of the SAME Driver; it never replaces a different Driver name when the cause itself is different.
     Catches: Q1 vs April (period), US vs Europe (segment), domestic vs international (geography), company-owned vs franchise (store-type).
     Segment/geography — name vs fact_scope (the one judgment call): default → fact_scope (the read-time series partition already separates by segment and period). Use the name only when the source treats the segment as a standalone, recurring cause of its own (e.g. taco_bell_same_store_sales). When unsure → fact_scope — this applies to segment/geography ONLY; it never overrides Rule 2 (a source-stated per-X always goes in the name).

  1. Driver name must include any qualifier needed to identify the reusable measured cause/class.
     If removing a qualifier would mix facts that should stay separate, keep the qualifier in driver_name.
     This includes non-per-X qualifiers too — benchmark (brent/wti), accounting basis (adjusted/diluted/constant-currency), and geography/segment when it names a different cause.

  2. All source-stated per-X measurement bases go in the name — business AND physical, no special-casing:
     per_share, per_store, per_square_foot, per_available_room, per_user, per_barrel, per_tonne, per_pound, per_hour, per_container, …
     Transcribe the per-X the source states; never judge “physical vs business.”

  3. A different per-X basis = a different Driver.
     oil_price_per_barrel and oil_price_per_tonne are separate Drivers — never SAME_AS.

  4. There is no per-X unit. Units stay the base enum only — exactly these 9:
     usd, m_usd, percent, percent_yoy, percent_points, basis_points, count, x, unknown.

  5. Pure scale or number wording never enters the name:
     billion, million, %, bps, dollars, or shares/stores used as a count
     unit are value/unit only.

  6. If the source does not state the qualifier, do not invent it.
     “oil rose” → oil_price, not oil_price_per_barrel.

  7. fact_scope only separates multiple facts for the same Driver inside the same event. It never replaces Driver identity.

  8. SAME_AS only when two Driver names mean the exact same reusable measured cause/class.

  > Why per-X lives in the name: read-time series grouping uses structured
  > keys like name + unit and does not read the quote. A per-X left only in
  > the quote can silently merge non-comparable values.


  ## Build Note

  Related-family grouping can be added for discovery/retrieval, such as connecting `oil_price` and `oil_price_per_barrel`, but it must never behave like `SAME_AS` or merge numeric series.

  ## Examples (illustrative, non-exhaustive)

  **1. Stated physical per-X**
  - Source: oil at $80/barrel
  - driver_name: `oil_price_per_barrel`
  - Unit/scope: `level_unit = usd`
  - Decision: per-X goes in name

  **2. Different physical per-X**
  - Source: oil at $600/tonne
  - driver_name: `oil_price_per_tonne`
  - Unit/scope: `level_unit = usd`
  - Decision: separate Driver, never `SAME_AS`

  **3. No stated per-X**
  - Source: oil prices rose 8%
  - driver_name: `oil_price`
  - Unit/scope: `change_unit = percent_yoy`
  - Decision: do not invent basis

  **4. Business per-X**
  - Source: dividend per share
  - driver_name: `dividend_per_share`
  - Unit/scope: `level_unit = usd`
  - Decision: per-X defines metric

  **5. Store productivity**
  - Source: sales per square foot
  - driver_name: `sales_per_square_foot`
  - Unit/scope: `level_unit = usd`
  - Decision: per-X defines metric

  **6. User metric**
  - Source: revenue per user
  - driver_name: `revenue_per_user`
  - Unit/scope: `level_unit = usd`
  - Decision: per-X defines metric

  **7. Accounting qualifier**
  - Source: adjusted EPS
  - driver_name: `adjusted_eps`
  - Unit/scope: `level_unit = usd`
  - Decision: qualifier changes cause/class

  **8. Pure scale**
  - Source: revenue of $1.5B
  - driver_name: `revenue`
  - Unit/scope: `level_unit = m_usd`
  - Decision: scale stays out of name

  **9. Change unit**
  - Source: margin rose 60 bps
  - driver_name: `margin`
  - Unit/scope: `change_unit = basis_points`
  - Decision: bps is unit, not name

  **10. Same-event slices**
  - Source: Q1 comps +3%, April -1%
  - driver_name: `same_store_sales`
  - Unit/scope: two `fact_scope` values
  - Decision: scope separates same-event facts

  (fact_scope is fully defined as Rule 0 above.)


## Final Unit Resolution Notes

1. Use the Guidance V2-style resolver path, not legacy/V1: live Guidance evidence showed legacy/V1 had bad units, and the Driver-specific rerun now proves the shared resolver path works on the corrected 117-case probe.
V2 source: .claude/skills/extract/types/guidance/primary-pass.md:90 and implemented in .claude/skills/earnings-orchestrator/scripts/guidance_ids.py:254

  2. Borrow V2 unit method:
     1. Extract number exactly as written.
     2. Extract raw unit text exactly as written (`unit_raw`).
     3. Add hints: `unit_kind_hint` and `money_mode_hint`.
     4. Let code decide final unit and scaling.

3.   Driver Changes

  Catalog side:

  - Add/require fact_type on Driver.
  - Do not add units to Driver.
  - Preserve every source-stated per-X measurement basis in `driver_name`; never put it in the unit.
    Examples: `dividend_per_share`, `sales_per_square_foot`, `oil_price_per_barrel`, `revenue_per_user`.


  DriverUpdate side:

  *Reuse only the V2 resolver and test it on Driver examples.*

  - Use the existing fields **level_unit** and **change_unit** from DriverGraphSchema.md:279-281.
  - Feed the resolver separate raw inputs for level and change.
  - Example: margin “rose 60 bps to 17.6%” should resolve:
      - level_unit = percent
      - change_unit = basis_points

  Validate FINAL resolved units only: `level_unit` and `change_unit`. (while Guidance usually has one unit for one value/range)

  Allowed final units are exactly:
  `m_usd`, `usd`, `percent`, `percent_yoy`, `percent_points`, `basis_points`, `count`, `x`, `unknown`.


Decision:
- Do not add `percent_qoq` now. Keep the 9-unit enum stable unless later production evidence proves a new unit is required.


  Raw source wording like `"cents per share"`, `"million shares"`, `"$ per square foot"`, or `"$ per barrel"` is allowed as resolver input, but it must normalize into one of the final units above.

  This is sufficient for the planned Driver schema because source-stated per-X denominators live in `driver_name`, not in unit:
  `eps` / `dividend_per_share` → `usd`
  `sales_per_square_foot` → `usd`
  `oil_price_per_barrel` → `usd`
  `diluted_share_count` → `count`

  - Reject final units like `usd_per_share`, `shares`, `dollars_per_store`, or `bps_yoy`; they mean the resolver or prompt failed.
  - Reject anything outside the shared unit enum from .claude/skills/earnings-orchestrator/scripts/guidance_ids.py:31.
  - For no-number DriverUpdates like “dividend suspended,” leave numeric fields null. No unit resolver needed.

  Comparison nuance:
  Driver has `comparison_low` / `comparison_high`, but no `comparison_unit`. So comparison values must use the same unit as `level_unit`. If the source compares against a different-unit value, keep that detail in `quote` for now; do not invent `comparison_unit` unless schema changes later.

  Unification advice:
  Yes, unify the unit logic, but make it a shared unit resolver, not “Guidance unit code.”

  Guidance and DriverUpdate should both call the same resolver:
  - Guidance calls it for its guidance value/range.
  - DriverUpdate calls it separately for `level_*` and `change_*`.

  Extract it into a pure module so it can be tested without Neo4j, Redis, LLMs, or graph writes.

  Possible API:
  `resolve_unit_value(label, value, unit_raw, unit_kind_hint, money_mode_hint, quote=None, xbrl_qname=None)`







# To be included in prompt: Unit-specific only, "what must Driver tell the AI to send for units"


  **Verbatim from primary-pass.md:**

  ### V2 Unit Hint Fields (REQUIRED)

  Every extracted item MUST include these fields:

  - **`unit_kind_hint`**: REQUIRED. One of `money`, `ratio`, `count`, `multiplier`, `unknown`. Classifies what kind of thing the metric
  measures.
  - **`money_mode_hint`**: REQUIRED when `unit_kind_hint == "money"`. One of `aggregate`, `price_like`, `unknown`. Must be `null` or omitted for non-money kinds.
  - **`unit_raw`**: REQUIRED. Verbatim surface scale/unit text from source.
  Preserve denominator phrases when present, for example `"cents per share"` or `"$ per metric ton"`. Used for scale parsing and denominator-surface detection, not final semantic classification.

  ### Numeric Value Rules

  Copy the number and unit exactly as printed in the source text. `"$10.3 billion"` → `low=10.3, unit_raw="billion"`. `"4.94 billion shares"` → `low=4.94, unit_raw="billion"` for a share-count label such as `Diluted Share Count`. Never convert between units — the canonicalizer handles all  scaling.


 **Verbatim from secondary pass:**

  ### V2 Unit Hint Fields

 Preserve from 7E unless the Q&A changes it: ... `unit_raw` (when present), ... `resolved_kind`, `resolved_money_mode`, `resolved_ratio_subtype`, `resolution_version`.

 Enrichment output (this Step 6 payload) should use `payload_origin=extract_v2` at the top level because every emitted item was actively processed by the enrichment agent.

  For ALL items in the enrichment output (both modified readback and new secondary-only):

  - **`unit_kind_hint`**: REQUIRED. One of `money`, `ratio`, `count`, `multiplier`, `unknown`.
  - **`money_mode_hint`**: REQUIRED when `unit_kind_hint == "money"`. One of `aggregate`, `price_like`, `unknown`.
  - **`unit_raw`**: REQUIRED for numeric items. Verbatim surface scale/unit text. Preserve denominator phrases (e.g., `"cents per share"`).


## Next Steps After Unit + Naming Proofs

Status:
- Steps 1-3 proved the shared unit resolver in scratch: 117/117 production-path cases, value checks, and per-X naming lint passed.
- Step 4 proved the locked naming rules in scratch: 3 blind Opus runs, 33/33 cases each, no flicker.

Step 5 - Wire into real Driver pipeline:
- Add locked Rules 0-8 to the real reader/producer prompt.
- Fix stale examples so source-stated per-X becomes part of `driver_name`.
- Producer must emit `unit_raw`, `unit_kind_hint`, and `money_mode_hint`.
- Call shared resolver separately for `level_*` and `change_*`.
- Block invalid output: missed per-X, invented per-X unit, invalid unit, or unit fields on Driver nodes.

Step 6 - Full real replay:
- Re-run the full restaurant Driver flow.
- Validate every output, not samples: Driver names, per-X, units, values, `fact_scope`, and `SAME_AS`.
- Pass gate: 0 critical failures.

Step 7 - Lock permanently:
- Move resolver to final shared production location.
- Add permanent tests/validators for the 9-unit enum, per-X naming, no per-X units, no Driver unit fields, and value scaling.
- Update final docs only after Step 6 passes.
- Future Driver runs should fail if these rules break.
