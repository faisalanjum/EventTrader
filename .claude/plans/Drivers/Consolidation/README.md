
# Basic Ideas IN BULLETS

1. Build Driver Catalog & DriverUpdate in such a way that it mimics Guidance/ GuidanceUpdate flow super closely (only changing what cannot fit our driver process easily but try hard)


3. ## Guidance Period (it is a seperate node):

    a. The calendar window the number is about, e.g. gp_2025-04-01_2025-06-30. Shared across companies.

    b. Issues: Period race — 10-Q/10-K can extract before XBRL lands → a duplicate period later (add a HAS_XBRL gate).


4. ## Guidance ID:

    a. Can this exact methodology be used for Driver.? What does Driver use currently and any downside or something I cannot see if we instead use Guidance ID based methodology to create ID's for Driver - infact which one is better and why? 


5. ## Model choice & number of runs per task

    a. For guidance (& specially for XBRL linking) Sonnet results were better but need to revalicate with newer models 

    b. Right model for the right task: cheaper models for news and do they need to be advised when in doubt or recheck anyway and frequency (daily once?)

    c. number of model runs per task (mostly different models?)


# Final Proposals (Validated/ Not validated):







# To Resolve:

1. what was the 24-tag event taxonomy for all 8-K events done in Guidance extraction and can it be useful for our purposes? 

2. How to deal with amendments?


# Issues:

Another issue to deeply think about is this - won't there be some Driver with fact_type = guidance which may also be applicable to other fact_types - how will we handle such things? 


# Do Not Forget:

- Future guidance consolidation: when `fact_type = guidance` is generated from/merged with Guidance extraction, preserve a `company_confirmed` boolean.
- Likely belongs on `DriverUpdate` (ONLY on `fact_type = guidance` updates — other fact_types don't carry it), not `Driver`, because confirmation is event/source-specific; decide during Guidance consolidation.
- Metric-family rule: every `<base>_guidance` and `<base>_surprise` Driver must point to exactly one `<base>` `fact_type=metric` Driver with a `BASE_METRIC` edge.
- Example: `revenue_guidance -> BASE_METRIC -> revenue`; `revenue_surprise -> BASE_METRIC -> revenue`. These are related siblings for read-time comparison, never `SAME_AS`, and never one merged numeric series.
- If `<base>` does not exist yet, create it in the same catalog run. It is OK if the base metric Driver is a latent class with zero metric updates at first.
- Synonyms use existing Driver identity machinery: if `net_sales` is truly the same metric as `revenue`, connect those metric Drivers via `SAME_AS`; then `net_sales_guidance -> BASE_METRIC -> net_sales -> SAME_AS -> revenue`. A missed synonym causes a missing comparison, not a wrong merged series.
- Only terminal `_guidance` / `_surprise` create this required `BASE_METRIC` relation. Do not infer family from arbitrary prefixes.
- Build-time validator: every `fact_type=guidance` / `fact_type=surprise` Driver must have exactly one valid `BASE_METRIC` target; `action_event` Drivers must have none.
- `action_event` Drivers are different: they are discrete actions/events, not another reading of a metric, so they are NOT part of metric family and never need a required base metric.
- Do not add a generic weak `RELATED_TO` edge as source of truth. Action-event-to-metric relationships come from evidence: actual `DriverUpdate`s connected to source `Event`s, sometimes across multiple events over time.
- If an action-event-to-metric relation is ever materialized for speed/search, it must be a derived cache from evidence, use a separate non-identity relation kind, and never be manually judged, `SAME_AS`, or a merged numeric series.
