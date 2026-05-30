
---

# v6 → v10 Fold — Doubt-Resolution Map (added 2026-05-27)

This file collects 50+ doubts/questions raised pre-fold. The CombinedPlan v6 → v10 fold (E1-E30 + Tier-6 levers E26-E29 + v9/v10 PIT patches) **resolves a substantial subset**. Below is a mapping of which doubts have been answered by which E* / lever — read this before drafting follow-ups. Doubts marked OPEN are still active.

| Doubt # | Topic | Status | Resolved by |
|---|---|---|---|
| #14, #38, #42, #47, #49, #51 | "Non-exhaustive curated vocab" concern (SYNONYM_MAP, SHORTCUTS_VOCAB, ACRONYM_MAP, etc. can't be hand-curated exhaustively) | ✅ RESOLVED | **E10 + E27**: live `:VocabToken` + `:EquivalenceToken` Neo4j stores grow at runtime via `propose_new_drivers[]`. Markdown §F.1 is BOOTSTRAP SEED ONLY — never mutated at runtime. Pattern A1/A2/B per E27 handles synonyms/plurals/acronyms/shortcuts as runtime-mutable Neo4j rows. The "exhaustive curation" problem is replaced by "bootstrap seed + Pattern A/B organic growth". |
| #24 | "Should rejected proposals be fed back to LLM as examples?" | ✅ PARTIALLY RESOLVED | **E28 Lever #3** (the PRIMARY path: Pattern A = the producer (learner) self-corrects WITHIN ITS OWN session — after drafting driver tags it calls a deterministic validate tool (`driver_write_cli.py --dry-run` = canonicalize + validators), reads the exact per-tag rejection reasons, fixes ONLY the flagged tags, and re-validates — looping AT MOST 2-3 times, stopping if a rejection repeats (no progress), never contorting a name just to pass (drop+note instead). The orchestrator's write-path validation is the NON-NEGOTIABLE external authority/gate: it re-validates before MERGE, handles partial-failure audit/drop, and the learner cannot bypass it; the internal loop is a convenience, not the authority. Cost $0 (extra in-session turns on interactive OAuth; SDK / `claude -p` stay forbidden/metered). An optional single orchestrator-level fallback retry is DEFERRED (build only if post-launch audit shows many gate-failures worth recovering — same metrics-gated posture as the demoted Lever #1)). **E26 Lever #1** deterministic auto-repair is DEMOTED/DEFERRED (prefer Pattern A self-correct; revive only if post-launch metrics show many mechanically-recoverable rejects, and only for unambiguous strips). The `:DriverProposalRejection` audit row preserves rejections for forensic review IN ADDITION TO the in-loop self-correction above. |
| #25, #35 | `pit_cutoff` / `registry_visible_at` meaning + multi-source semantics | ✅ RESOLVED | **L6 + E5 + E10**: `Driver.registry_visible_at = MIN(DC.pit_cutoff)`; per-source `pit_cutoff` formula (predictor bundle, learner_result, news.created, fiscal filing); historical run filter `dc.pit_cutoff <= run.pit_cutoff`. |
| #36 | "Cold-start seed exception" — what is it, why exclude era-bound names | ✅ RESOLVED | **E9 + §J.2** (just added): two-tier PIT policy — TIER 1 timeless anchors get `EPOCH_SENTINEL`, TIER 2 modern drivers EXCLUDED from cold-start (must enter via `propose_new_drivers` at actual PIT). Prevents 1990-backfill seeing `iphone_china_sales`. |
| #37 | "Supersession" — how it works | ✅ RESOLVED | **R15 #1** (CombinedPlan): stable `source_id` across re-runs + separate `run_id` per run; `dc.superseded_at + superseded_pit_cutoff + superseded_by_run_id` triple on DCs that drop out across re-runs. Un-supersede if dropped DC reappears. |
| #39 | "Should predictor see prior driver_changes instead of registry catalog?" | ✅ RESOLVED | **E30**: predictor is consumer-only. Reads BOTH (a) registry catalog (PIT-filtered) and (b) prior `learner_result` driver_tags via `prior_reports_context`. Predictor never writes. |
| #42 | "Predictor proposing drivers is wrong — only learner should" | ✅ RESOLVED | **E30** (your intuition was correct): predictor consumer-only, learner sole Phase-1 producer. `prediction/result.json §7 key_drivers[]` stays free-form prose. |
| #43 | "Why learner uses `primary_driver + contributing_factors[]` instead of `key_drivers[]`?" | ✅ RESOLVED | **E21 amended by E30**: §8 (learner_result.v1) gets canonical-form migration; §7 (prediction_result.v1) stays free-form. The split reflects different LLM tasks: predictor authors a free-form bet; learner does post-outcome canonical attribution. |
| #1 | "Direction on edge (driver_change → event) vs property" | ⚠️ PARTIALLY | Direction lives on `FOR_COMPANY` edge per-company (per ChatGPT R2 #2 / R10 #1) — addresses cross-company asymmetric impact (`exposure_role` for news). Open sub-question: time-varying impact on same company across periods (#1, #28 last paragraph). |
| #2, #3, #4, #5, #6, #7, #10, #11, #12, #13, #15, #16, #17, #18, #20, #21, #22, #23, #26, #27, #28 (parts), #30, #31, #32, #33, #34, #40, #44, #45, #46, #48, #50 | Various design specifics, sub-mechanisms, examples, validation details | ⏸️ OPEN | Each requires a per-item answer; the fold did NOT auto-resolve these. Many will get implementation-time answers; some need user decisions before Day-1 build. |

**Net**: of ~50 raised doubts, ~9 are explicitly resolved by the v6→v10 fold + ~1 is partially resolved + ~40 remain OPEN (mostly design specifics that the fold did not target). Read each OPEN doubt against the current `CombinedPlan.md` §5 + `DriverOntology_Implementation.md` §B/§C/§F/§J before re-raising — some may have implicit answers in the post-fold spec that aren't explicitly cross-linked here.

---

# Requirements

> **Note:** The body items below (#1-#51) are the ORIGINAL raw doubts list, captured before the v6 → v10 fold. Individual items are NOT marked resolved/open inline — see the "Doubt-Resolution Map" table at the top of this file for which doubts the fold answered (9 ✅ + 1 ⚠️ partial + ~40 ⏸ still open) and which spec section now answers each. Read body items through the lens of that map; don't take any individual numbered item as currently-open unless cross-checked.

1. For my own understanding breakdown each component in smallest possible unit and understand it. Clarify my doubts, propose changes iteratively and unless I don't understand everything no build stage.
2. My one requirement is after driver has been identified by earnings-leaner, we should make use of existing extraction pipeline template (of whcih guidance extraction pipeline is one example already working) so as to make task easier and also since guidance extraction pipleine has worked fine overall. 

3. How to make this as minimalistic system without losing reliability and functionality?

# Issues I see (need to think):
1. "direction":  "Long/short" -> Since the impact of a driver on a stock is not 100% deterministic (since LLM's create it), and the only thing we know for sure is what happened to stock prices for that event - would it make sense to have direction as a property on say the neo4j link connecting driver_change to an event. And maybe the way we will use is - later we could aggregate this direction across all events for that stock and see direction in an aggregate sense etc


# Things to add:
1. In learner skill -> we should ask it to not restrict itself to only one primary driver but also only include about what the LLM is certain about. Also it may make sense to also include in an event linking to driver_change - if it is the primary_driver bool

2. In learner skill: I think so far it correctly for the sake of being useful to only predictor only may be looking at 8-k drivers, but for future use and since it has entire quarter context, it should seperately also look and extract this specific quarter drivers from TRANSCRIPTS and also how about (10-q, 10k, any other reports - or should we omit this since fiscal.ai already gives  - upside/downside?) that appeared in the quarter. That said ofcourse what it presents to Future_checklist quatesions need to be only what next rpedictor can view although we could show him all quarters that are tagged to previous learners reports. 

3. One driver tag - should we have also include exact sentence just like guidance does - upside/downside?

4. writer = the Python CLI (driver_write_cli.py) that runs canonicalize + validators + MERGE — NOT a worker pod. Why not a worker pod or part of some process which is a worker pod?

5. Note and approve full shape of result.json with key_drivers[] + propose_new_drivers[] 

6. "sorted-token reuse (gated on all known tokens)"?  - remember no hardcoding of examples since they get outdated unless this emans something else?

7. :DriverDriftAudit  (when direction flips on re-run, when supersession fires) - meaning and how its handled?





9.A ssuming this means inject driverrs tagged to each previous learner report: ─ injects catalog excerpt into the next predictor LLM prompt


10. driver tag - driver_state. Issue is allowed states may not be exhaustive - how to ensure nothing gets missed or wrongly categorized? "Drawn from this driver's allowed_states"?

11. good is iphone_guidance versus just forward_guidance so as to make it specific - does our ontology differentiate between the 2?

12. What happens when a driver is rejected after canonicalize - does the producer get a feedback or is the created driver name "lost for ever"?

13. per the slot rule "At most one token per slot." say china_japan_sales, do we create 2 seperate drivers?

14. "Apply synonym map" - does this mean it can only be appled if we already ahve a curated list of drivers and synonyms or does the llm smart to see what already exists and then us ethat as a synonym - since otherwise this curated list smells of super bad design ? Same for "acronym map", "standalone shortcut", "macro shortcuts" and "stop words" and so on. - is there a NLP library which can resolve this with 100% accuracy?
- the primary issue is of using a non -exhaustive list of specific words which we dont want to curate in a deterministic layer. 
- same non exhaustive issue with "every shape + grammar + banned-content rule."

15. apply plural map - is the plural only applied to metric in 6 slots?

16. Who is responsible for aliases and how does it flow in the system and its purposes?


17. the segment - shouldn't that be part of XBRL member matching process downstream? The text says "Used downstream by the financial-sliver writer to MERGE :MAPS_TO_MEMBER edges to :Member nodes. Required, never null." but how does this help here ? and how did guidance extraction achive this - should we not do same process?


18. explain "base_label" and its purpose



20. qUESTIONS RELATED TO THIS SENTENCE: "Every token is in the runtime vocab/registry, OR the new-token gate passes (slot determined by position, not in banned content, appears in evidence text)"
    - what is vocab - and how is it different from registry of drivers.     
    - also "runtime" means here?
    - WHAT DOES evidence have to do with anaything "appears in evidence text"?

21. Not sure what this means: "Same emission attaches this driver to at least one tag with non-empty evidence.
"?

22. Not sure what this means and why?
    - segment matches name's sub-dim

23. I am assuminmg here it means we already have a list of classes that define all states inside that class - looks non exhaustive? "allowed_states from one class"?

24. ":DriverProposalRejection audit row": Would it make sense to pass these as examples of rejected proposals along with registry (in all next runs) to leaner/predictor so they understand the issue: 


25. Each DriverChange carries:
    pit_cutoff - this specific pit should ideally be related to when that event was released to the public. that said we can have another field which mentions not when the source ran but rather for what quarters or other id of predictor/learner/news/fiscal_ai. 

26. Look up properties of GuidanceUpdate in Neo4j - and see if anyone from there can be used as well and their purpose - such as for example: "evhash16", "quote?

27. Also note in GuidanceUpdate the reason for source_refs since it shows specific part of Transcript for example like " ["ASO_2023-11-30T10.00_pr"]" - for us what does evidence_refs mean since each DriverChange is anyway linked to a specific event? Unless later if we introduce internet-based search such as for example for News (which then would make sense).

28. While edge to Company from driver_change (and not driver) is fine (& sort of redundant but acceptable since GuidanceUpdate also uses it), as earlier mentioned the direction should be on Event to driver_change - not sure what exposure_role is all about and if required? "+ edge to :Company carrying direction + exposure_role?"?


30. "The exposure_role field — why it exists" - did not understand "This is populated only by the news pipeline (Mode 2) when one event has cross-company asymmetric impact."


31. Are driver and driver_change names expected to be same or no? examples?

32. CITES_EVIDENCE - Assuming it includes both evidence_ref "SRC:* ID " (GuidanceUpdate calls it source_ref i think not sure why we use different name) as well as "quote (same as GuidanceUpdate but again not sure why missing in here)?


33. MAPS_TO_CONCEPT & MAPS_TO_MEMBER - in case of GuidanceUpdate explain how this linking and matching works step by step and are we certain we can apply same methodology to driver_change and it will work perfectly?


34. exposure_role field: Yes I agree to this "ONE DriverChange for opec_supply + state=cut can carry MULTIPLE :FOR_COMPANY edges, each with its own direction + exposure_role (producer/consumer/supplier/competitor/neutral). This is populated only by the news pipeline (Mode 2) when one event has cross-company asymmetric impact." but how about when source is Learner/predictor etc - is it better to keep it seperate driver_change since for one atleast its timing may be seperate or can we think through all edge cases and then come up with the best decision?


35. "B10 · Add concept: PIT visibility" - "registry_visible_at". For pit_cut_off, there are 2 possible reasons for this:
    35.1: : so that we only allow those drivers whose linked events datetime is in accordance to the context. It means different things based on the source/producer:
    35.1.a: For predictor, its simply the pit cutoff date as passed inside earnings-prediction. 
    35.1.b: Same for learner 
    35.1.c: For news as some driver_changes will come from internet-based research but in this case the datetime of the return event (in our case when daily return calculation finished should be the driver_change date since thats how we are determining news_impact) - which also means each driver_change date needs to be maintained. 

For this usecase, PIT should match the dates of events and not neccessarily by producers like learners? whats the other purpose of "The date / quarter. Lives on the DriverChange's pit_cutoff property." 

    35.2: In html, i beelive the reasoning is for another usecase, "For historical backfill, LLM cannot reuse a name that "didn't exist yet" but whats the downside of this - as long as it only borrows from the future name and we don't make anything else visible since historical backfil will follow the integrity of the db.

    But may be I am missing some understanding so think through before rubber-stamping. 
    
36. Did not at all understand this issue "Cold-start seed exception": "Seed drivers (cold-start ~32 anchors like oil_price, fed_rate, fda_approval) have no real DC at bootstrap time.They carry registry_visible_at = 1970-01-01T00:00:00Z (the "epoch sentinel") — always visible, predate any conceivable real pit_cutoff. Era-bound seed candidates like iphone or ai_datacenter_us_capex are excluded from the seed (would leak into 1990 backfills)."? 

37. "superseded" while i understood a new run can supersede previous driver and agree with idea of having source_id as stable across re-runs while rund_id differ - few follow up questions:
    37.1: How is it possible to deterministically match old driver with new unless you mean LLMs do that?
    37.2: How about the driver_change linked to previous driver - are they transferred (relinked) to new driver and if not, do they become unreachable or irrelevant?
    37.3: how is different run_id calculated dynamically?
    37.4: Also I though the superseeded_at was a property of driver but below you mention dc.superseded_pit_cutoff so confused?

38. ═══ VOCAB EXCERPT ═══

should we instead be using an NLP librray for Vocab to get ~100% accuracy - upside, doenside ? and will it be able to cover all since we need to seed all these with exhaustive list for full deterministic matches? am i missing something? Also see the non-exhaustive issue in "Closed vocabulary. Every token must be in a vocab bank OR in a registry name/alias."
Also like DRIVER REGISTRY, is VOCAB EXCERPT specific to a company?

39. Also in case of predictor, it only sees driver tags next to each report - and at best instead of showing "Driver Registry Catalog block" to predictor for which it has no use (since its not creating enw drivers but consuimg), we may even show all previous driver_changes and their impact - just a thought?

40. what field does magnitudes belong to in driver_change? since even though we have this  -> Evidence (from a news article):
   "Hyperscalers committed $400B in AI datacenter capex through 2027."

so instead of magnitude we should have it in quote assumuing every figure/ (numeric value) will be in quotes whenever reported.



42. Again its learner who will be proposing driver names and driver change names not predictors: so this is wrong i guess (/prediction/result.json) unless you think its better for predictor to also propose new drivers - pros and cons? 

43. why is this the case (although i agree but ensuring why?) "For the learner, the schema is similar but uses primary_driver (single) + contributing_factors (list) instead of key_drivers. "?

44. In this I am assuming direction can still be inferred and not neccessarily need to be extracted verbatim since otherwise we will be rejecting perfectly valid drivers? "B1 EXTRACT evidence → (noun_phrase, state_verb, direction, evidence_refs) Reject if any field empty."

45. Is using regex 100% safe here since typically I dont like regex since they are not 100% reliable but not sure in this case? "slug(noun_phrase). Reject if shape regex fails."? although for specific conditions inside SHAPE_GATE such as lowercase? alphanumeric/underscore? no consecutive __? no leading or trailing _? " may work fine?

46. how does grammer work? "Run §D grammar + new-token gate + §E validators on name."

47. This is another issue of non-exhaustive (plus mainatenance etc without human intervention) list COMPOUND SUBSTITUTION since we can't possible have all these before hand?
    data_center  → datacenter
    gross_profit → gross_margin
    ACRONYM_MAP, PLURAL_MAP, SYNONYM_MAP, BANNED_CONTENT, SHORTCUTS_VOCAB, GEOGRAPHIES, OBJECTS, METRICS

    unless we use another LLM or a NLP model ?

48. "Fails with" rejection reason should be simplified so easily understood by LLM 

49. SHORTCUTS_VOCAB - yield_curve, fda_approval - again impossible to have an exhaustive determinisic list unless I am missing something. 

50. Also on another note is it possible for LLM to actually run their inputs through this entire canacolize function before suggesting final output?

51. Same non-exhaustive issue with things like "oil_price". 







# Agree (& to improve if possible):

1. All 3 modes share the SAME writer / canonicalize / MERGE. - Yes to this - can we ensure they share as much code/infra as possible so they can use same extraction templates as much as possible?

# Resolved:

1. Since each driver_change (similar to GuidanceUpdate has a seperate link to Company Node - we can have direction on that link seperately for each driver_change) so below is resolved:

Agree to this specially say in case of fiscal.ai when we don't know the exact event: ":FROM_SOURCE	DC → Report/Transcript/News/FiscalKPI	—	Only if source maps to an existing Neo4j node (file-backed sources don't get this edge)"

or even sometimes incase of News (see skill news-impact for context) when even though a specific news event may have annotated returns but the reason comes out to be different (based on say other internet-based research) so linking only one specific news event to driver_change may not be appropriate. In that case if there are multiple news - then we may ask LLM to link it to specific news event if appropriate (or leave it if none are correct) since essentially some will come from Internet or external research. In that case rethink what happens to my requirement of having direction property to be present on the link connecting event to driver_change since that won't be appropriate? My only issue with the alternative of having "direction property to be present on the link connecting company to driver_change" is at different points across time periods the driver change may impact company stock prices differently? 