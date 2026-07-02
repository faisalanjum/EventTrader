
> **STATUS (2026-06-26) — the slice / period / units / family design is now LOCKED.** Source-of-truth docs in this folder:
> `Naming_Slices_XBRL.md` (naming · slices · measurement · XBRL — the spec + 33 rules) · `XBRL_SliceAxis_Catalog.md` (the frozen slice-axis list + elimination guard) · `GuidancePeriod.md` (the period axis) · `UnitExtraction.md` (units + per-X) · `MetricGuidanceFamily.md` (the metric/guidance/surprise/action family).
> Items marked **✅** below are settled in those docs; unmarked items are guiding principles or **still open**.

# Basic Ideas IN BULLETS

1. Build Driver Catalog & DriverUpdate in such a way that it mimics Guidance/ GuidanceUpdate flow super closely (only changing what cannot fit our driver process easily but try hard)


3. ## DriverPeriod (resolved period node):   ✅ RESOLVED → `GuidancePeriod.md`

    a. Period-bearing DriverUpdates link to a shared `DriverPeriod` calendar window, e.g. `gp_2025-04-01_2025-06-30`; full target spec: [GuidancePeriod.md](GuidancePeriod.md).

    b. Reuse and extend the shared Guidance period mechanism: add exact-date windows plus `ytd`/`ttm`; write `DriverUpdate -[:HAS_PERIOD]-> DriverPeriod`; do not attach fake periods to facts with no real time window.


4. ## Guidance ID:   ✅ RESOLVED → `Naming_Slices_XBRL.md` §1 — fact ID = event + driver + fact_scope, reusing the guidance ID *recipe/pattern* (slug · period-builder · producer-less). Guidance-style wins; basis is NOT in the ID (it's `measurement`).

    a. Can this exact methodology be used for Driver.? What does Driver use currently and any downside or something I cannot see if we instead use Guidance ID based methodology to create ID's for Driver - infact which one is better and why? 


5. ## Model choice & number of runs per task

    a. For guidance (& specially for XBRL linking) Sonnet results were better but need to revalicate with newer models 

    b. Right model for the right task: cheaper models for news and do they need to be advised when in doubt or recheck anyway and frequency (daily once?)

    c. number of model runs per task (mostly different models?)

    d. ✅ Revalidated 2026-06-30 (isolated throwaway test, 12 real documents, Sonnet 5 vs Opus 4.8) — DriverCatalog reader step: single-pass Opus 4.8 beat every multi-pass/mixed-model variant on real judged precision (more passes only added junk: a 3rd pass was 82% junk for almost no new real candidates). For naming/slice/fact_type classification (the rules in `Naming_Slices_XBRL.md`), Sonnet 5 slightly beat Opus 4.8 on the spec's own worked examples (18/19 vs 17/19). **Opus for reading documents, Sonnet 5 for classifying what was found — a real mixture-of-models pipeline, not "pick one model for everything."**


# Final Proposals (Validated/ Not validated):







# To Resolve:

1. what was the 24-tag event taxonomy for all 8-K events done in Guidance extraction and can it be useful for our purposes? 

2. How to deal with amendments?


# Issues:

Another issue to deeply think about is this - won't there be some Driver with fact_type = guidance which may also be applicable to other fact_types - how will we handle such things? 
> ← **Already answered by the `BASE_METRIC` family in `# Do Not Forget` (✅ LOCKED): one topic = separate Drivers per fact_type (`revenue` / `revenue_guidance` / `revenue_surprise`) linked by `BASE_METRIC`, never one Driver carrying two fact_types. Only needs owner confirm.**


# Do Not Forget:   ✅ LOCKED rules — now also in `MetricGuidanceFamily.md` (the metric/guidance/surprise/action family + `company_confirmed`).

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



## fact_scope redesign:   ✅ RESOLVED → `Naming_Slices_XBRL.md` (spec) + `XBRL_SliceAxis_Catalog.md` (axis data). Answers to the 4 points below: (1) period → `GuidancePeriod.md`; (2) segment & geography & product → the **6 slice kinds** (segment · product · geography · customer · channel · entity), kind taken from the XBRL axis; (3) `store_type` → folded into `channel`, NOT a separate type; (4) NOT only 4 — **6 kinds + an `unknown` fallback**. (Original brief kept below for history.)

This is the most important part so ensure you think about it systematically and break down your reasoning as a first step into several subcomponent. Ensure you think through this problem over extended period of time and super thoroughly think through the entire design for this in as much depth as possible. We must deeply rethink fact_scope for all 4 fact_types Drivers. I will go over my justification, and you task is to validate each and every point in as much depth spawning as many sub agents which can bring us ABSOLUTE certainty beyond an ounce of doubt. Finally leave no stones unturned to understand every single nuance and every single detail as well as edge cases and then in the end for each point, tell me the plan which is 100% reliable, reuses as much structure mostly already proven by guidance extraction pipeline, is minimalistic and no over engineering. Also no v1 versus v2 since this is the final target design choice.
fact_scope
1.	period: RESOLVED in [GuidancePeriod.md](GuidancePeriod.md): use generic `DriverPeriod`; `fact_scope` stores `period=<period_u_id>` when a period exists; derive clear omitted metric/surprise periods from event/report metadata; exact source/XBRL dates win over computed dates; add exact-date + `ytd`/`ttm` support to the shared Guidance period mechanism; no fake period for periodless facts.
2.	Segment & geography & product: Again look at exactly ho we tried to solve it in Guidance/GuidanceUpdates since there segment and geography was used to link to its company XBRL by I believe first pulling the list of existing segments and geography for that company so we can have the exact enums for that company. 
3.	“store_type”: Not sure what is this 4th type inside fact_scope and why is it even required ?
4.	Are these only 4 types allowed inside fact_scope since we should lock this decisgn now? 


# Issue to resolve:
_(1) ✅ ADDRESSED → `Naming_Slices_XBRL.md` §9: the XBRL link is enrichment — ~57% missing is fine, never the ID. (2) ⬜ partly — identity/fact_scope reconciled in `Naming_Slices_XBRL.md`; full GuidanceUpdate ↔ DriverUpdate property mapping spans `DriverGraphSchema.md`. (3) ✅ RESOLVED → yes: the guidance ID recipe IS the fact_scope serializer (`Naming_Slices_XBRL.md` §1)._
 1. XBRL member and concept linking in Guidance/ GuidanceauPDATE EXTRACTION IS NOT 100% COMPLETE (REQUIRES SOME MANUAL UPDATES) so need to be thought through super throughly? (may also be related to # SUPER IMPORTANT (details to be fleshed out) below)
    > ✅ CONCEPT side now specced + census-validated: see [`XBRLConceptLinking.md`](XBRLConceptLinking.md) (guard → menu-pick → verify → backstop; Haiku + backstop + abstain-fix). Member side unchanged.

 2. GuidanceUpdate has different properties than DriverUpdate - how are we going to reconcile that? 

 3. See if we can use Guidance ID creation instead of fact_scope 


# SUPER IMPORTANT (details to be fleshed out)

-> Instead of updating every single Report for DriverUpdates, we could get by only updating 8-ks, transcripts and News if there was a way to link every 10-k, 10-Q, XBRL facts to these drivers & DriverFacts (mostly fact_type=metrics only). Since that would save us a lot of tokens and reuse existing machinery. 