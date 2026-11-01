# Proposed rule change: Driver families without empty base Drivers

**Status: proposal for independent review, not an approved rule change.** Written 2026-09-28 against `DRIVER_RULES.md` version 1.1, frozen 2026-09-26. No rule file, implementation, Notion page, or graph data was changed by this review.

Baseline: [Driver rules](../DriversFinal/DRIVER_RULES.md). Older source design, consulted for dependencies: [FINAL_DESIGN.md](../FinalDesign/FINAL_DESIGN.md). The proposed amendment is self-contained below; the baseline supplies the unchanged rules.

**The proposal:** every Driver must begin with its own first proven fact. A valid guidance or surprise Driver may exist without a base metric Driver. When the real base exists, link the real records after checking their names, types, and meaning. The ordinary naming check must consider existing metric, guidance, and surprise names so whichever arrives first can supply the common wording.

**The boundary:** this removes empty placeholders and their promotion process. It does **not**, by itself, authorize deleting the four standing labels or their error protections. The owner's wider goal is to remove those stages; the final section explains precisely what this amendment establishes and what it does not.

## 1. Background and terms

A **Driver** is one reusable meaning with a permanent type and original source evidence. A **DriverUpdate**, called a **fact** below, is one quoted occurrence of that meaning in a source document.

These remain separate Drivers:

| Name | Type | What its facts describe |
|---|---|---|
| `revenue` | metric | Reported revenue |
| `revenue_guidance` | guidance | The company's revenue forecasts |
| `revenue_surprise` | surprise | Revenue results or forecasts compared with expectations |

A **family link** (`BASE_METRIC`) connects a guidance or surprise Driver to its metric Driver. A **synonym link** (`SAME_AS`) says that two Drivers have the same meaning. The links serve different purposes; this proposal never substitutes one for the other.

**XBRL** is the machine-readable financial data in SEC filings. An XBRL link identifies a matching official line item; it is optional evidence enrichment, not a substitute for the source quote.

Here, **underlying name** means the guidance or surprise name after removing exactly one valid final suffix. It is a string used during naming and checking, not a new stored object, field, registry, or empty Driver.

## 2. What is wrong with the current requirement

Rules 1.18 and 2.26 require a base to exist even when no metric fact exists. The system therefore creates a hidden, empty metric Driver and later promotes it when a matching metric fact arrives. Rule 2.35 makes this the sole exception to creation with a first fact.

That machinery enforces a relationship shape; it does not supply an actual measurement. It also does not solve uncertain meaning: the guidance or surprise already has to prove the underlying measure under 2.23. An empty base has no additional actual evidence to contribute, and cannot supply the missing XBRL evidence under 6.2.

The simpler rule is: **a forecast proves that a measure is being forecast; it does not manufacture an observed value of that measure.** Store the real forecast and create the metric Driver only when a real metric fact is accepted.

There is one necessary naming change. Looking only among existing metric Drivers is insufficient. Guidance can arrive first with one wording, while an actual later receives a different wording. Strict suffix lookup then misses the relationship. The existing naming and independent meaning checks must consider the underlying measures of all three types, without merging the types.

## 3. Proposed replacement rules

The wording below is the requested amendment. Unmentioned rules remain in force. Cross-references point to the frozen rule file so the board can check each dependency.

### 1.18 — Families can have an absent base

Replace 1.18 with:

> Different types describing one underlying measure remain separate Drivers. A guidance or surprise Driver has zero or one active family link to a real, proven metric Driver. An action Driver has none. A missing base is valid and never requires an empty Driver. When a qualifying base exists, the shared core must assess and create the family link under 2.26 and 2.32. A failed or uncertain match never creates a link. Family links come only from a valid final suffix and independently checked meaning, never from a shared prefix alone. Results, forecasts, and surprises remain separate facts and signals.

“Zero or one active link” permits a missing or disabled relationship; it does not permit two active targets or permit a bad relationship to remain active. Historical repair records remain intact.

### 2.26 — Replace hidden placeholders with naming and linking of real Drivers

Replace the whole hidden-placeholder rule with:

> **Real family members only.** Never create an empty base Driver for guidance or surprise.
>
> **Propose first.** Read the source and propose its meaning before showing existing Driver names. Then use the ordinary naming and independent identity checks. The source must prove the new fact; an old Driver's evidence can support reuse of a name, but cannot supply the new fact's value, period, measurement, or missing source evidence.
>
> **Check names across the family.** When choosing the underlying name, consider eligible existing metric names and the underlying names of guidance and surprise Drivers. Only names and evidence visible at the source's public time may influence a historical decision. The catalog remains company-neutral. Existing catalog candidates may suggest wording under the current catalog rules, but are not graph Drivers or eligible family-link targets merely because their names are listed.
>
> **Reuse only when proved.** Reuse common wording only when the independent check proves the same underlying measure and the current naming rules permit that reuse. For this purpose, compare the underlying measure while retaining each Driver's separate permanent type. Preserve the exact object, population, mechanism, meaningful portion, benchmark, and stated denominator. Consider the original evidence on both sides; an exact name, similar words, company, popularity, or frequency never proves identity.
>
> **Keep the existing limits.** This does not enable fuzzy matching, token-subset matching, new synonym rules, aliases, or automatic word substitution. Rule 2.4's checked word-order allowance still requires the same words. Rules 2.14–2.17 and 2.45 still distinguish portions, denominators, and types. No broad name may be invented to force a match. Existing stored Drivers are never renamed to make a family fit.
>
> **Create the real fact and Driver.** Once the proposed Driver and its own first fact pass all admission rules, save them together. Missing actual data, or the absence of a base node, is not a reason to hold an otherwise valid guidance Driver. This does not waive the surprise home-fact requirement in 4.14.
>
> **Link in either arrival order.** When a guidance or surprise Driver is created, assess its real base if one exists. When a metric Driver receives its first accepted fact, assess existing guidance and surprise Drivers whose exact underlying name matches it. Apply 2.32 before linking. The same rules apply when the records are accepted in one source event. A base that never arrives leaves complete, standalone guidance or surprise records; there is no placeholder to promote and no “waiting for actuals” Driver stage.
>
> **No approval by absence.** If matching is uncertain, leave the records unlinked. If a name actually clashes with a different meaning or type, apply the existing specific-name, skip, hold, or rejection rules; optional linking is not permission to bypass a naming defect. A failed search or missing required evidence must not be reported as “no base exists.”

This extends the existing naming check; it does not add a second name generator or a second vocabulary. Discovering family candidates is not itself approval to link them.

### 2.32 — Exact family-link conditions

Replace 2.32 with:

> A family link may be active only when all of these hold:
>
> 1. Its source is an admitted guidance or surprise Driver with its own accepted fact.
> 2. Its target is a real Driver with permanent type `metric`, proven by the applicable fixed rule or the evidence test in 2.30, and with its own accepted metric fact. Both may be created in the same successful write.
> 3. Removing exactly one final `_guidance` or `_surprise` from the source name gives the target's exact stored name. Normal formatting rules apply; semantic substitutions do not.
> 4. An independent check confirms that the original evidence describes the same underlying measure. Exact spelling is necessary but insufficient.
> 5. Neither the relationship nor an endpoint is barred from the proposed use by the existing review and recovery rules. No second active family target is created.
>
> A guidance admission does not automatically prove a later base's metric type. A different-named synonym representative never replaces the exact family target merely to make the link succeed. If a separate, approved synonym link exists, readers may use it only under the existing synonym rules.

Rules 2.22–2.24 continue to reject stacked suffixes and require a source-grounded standing measure. Rule 2.25 still reuses the original suffix-admission decision: the arrival of a base requires checking a **new relationship**, not rerunning an unchanged admission until it gives a preferred answer.

### 2.35 — No empty-Driver exception

Replace 2.35 with:

> Every new Driver is saved together with its own first proven fact. There are no empty-Driver exceptions. A forecast or surprise fact cannot serve as a metric Driver's first fact. A proposed catalog name is not a Driver until that Driver's own first fact is written.

Rule 2.37 is unchanged: a bare Driver's first fact needs a readable state; a suffixed guidance or surprise Driver may begin with an `unknown` state. `unknown` here describes a fact's movement, not an incomplete Driver.

### 4.14 — Preserve surprise home facts without requiring an empty base

A surprise's **home fact** is the ordinary result or forecast being compared with expectations, recorded separately from the comparison itself.

Retain the whole existing same-event home-fact requirement, and add:

> For `actual_vs_consensus` and `actual_vs_guidance`, the accepted home is a metric fact. Its real metric Driver therefore exists, or is created in the same successful write. The surprise must pass the family-link checks against that metric Driver.
>
> For `guidance_vs_consensus`, the accepted home is a guidance fact. The metric Driver may be absent. In that case, the guidance and surprise must have the same exact underlying name **and** pass an independent check that their source evidence concerns the same underlying measure. This establishes the required pairing without creating an empty metric or a new guidance-to-surprise link type.
>
> In both cases, the existing same-event, period, period-kind, slice, measurement, value/unit, and numberless-home checks remain mandatory. A held or rejected home never counts. If an existing family link contradicts the proposed pairing or has been disabled for that use, the pairing is not silently accepted by falling back to name stripping.

Rule 4.15 is unchanged: missing home evidence requires rereading the whole event. A generic unsupported “results beat” remains held, and an actual surprise before its period ends remains rejected. A new forecast versus the company's own prior forecast remains guidance movement, not surprise.

### 6.2 — Conditional XBRL inheritance

Retain direct links for metric facts only. Replace the placeholder-specific sentence with:

> Without an active, permitted family link to a real metric Driver with the required company-specific XBRL support, guidance and surprise inherit no XBRL link. Their own valid facts may still be stored and read. Never create a direct guidance/surprise XBRL link, an empty metric, or a metric fact to fill the gap. The existing measurement, company, source-time, and exact-line-item restrictions still apply; non-GAAP measurement still blocks inheritance.

### 6.23 — Preserve recovery; remove placeholder cleanup

Retain the existing protections for wrongly reused Drivers and their related links. Delete only the sentence requiring a hidden placeholder to be fixed or dropped. Add:

> When a base or family relationship is disabled, uses that depended on it remain paused under the existing recovery rules. Independently valid member facts remain on their original Drivers and may be read on their own where allowed. An absent base from initial creation is different from a known-bad relationship: treating both as an empty link must never erase the repair record or bypass a restriction. Restoring a relationship requires the approved independent recovery path and all current family-link checks.

This does not promise that every bad name can be repaired into a working family. The existing misnamed/mistyped-Driver problem in 10.2 remains unresolved; no renaming, retyping, or moving old facts is authorized here.

### 7.1 and 1.14 — Reads and time

Add to the read rules:

> A standalone guidance or surprise Driver is included in its own valid fact history even without a base link. An optional family relationship must not cause those rows to disappear from reads. Actual-versus-guidance views and inherited data require the appropriate proven real relationships and all normal series checks; a shared name alone never joins histories. An already accepted surprise remains readable from its own evidence and accepted home-fact pairing.
>
> A historical view may use a family relationship only when the evidence needed for its endpoints and meaning was public before that view's cutoff. Linking a metric today cannot make future actual data visible in an earlier forecast view. Late processing changes neither source publication times nor old fact identities. Existing tightening-only restrictions on known-bad links still apply to historical views.

Company, type, period, period kind, slice, measurement tags, series unit, time type, and surprise kind retain their current meanings. Family membership never means that all member values are numerically comparable.

### 8.15–8.16 — The missing-link trigger

Add to the running rules:

> The first accepted metric fact is a concrete trigger to assess missing family links under 2.26. A new guidance or surprise Driver similarly triggers assessment of its existing real base. This is relationship completion, not a retry of already accepted facts, a reason to rewrite history, or a reason to rerun an unchanged refused meaning decision. Ordinary event completion or replay must account for concurrently committed family members, so two simultaneous births do not permanently miss a valid relationship merely because each earlier lookup saw no counterpart. Repeated processing must not duplicate Drivers, facts, or active links. A previously refused pair is reconsidered only under the existing specific evidence/state-change rule.

The existing metric-history backfill rule remains unchanged. This amendment does not introduce a background placeholder sweeper, a new retry queue, or a requirement to backfill every guidance Driver's metric history before accepting the forecast.

## 4. Complete edit map for the frozen rule file

The substantive replacement text is above. These additional references must agree with it if the owner approves the amendment; none has been edited now.

| Location | Required change or retained boundary |
|---|---|
| Start here, design-map row for §2 | Remove the hidden-placeholder exception to creation with a first fact. |
| §1 connection diagram and `BASE_METRIC` description | Show that the family link is optional; it only points to a real metric. |
| 1.18 | Replace mandatory exactly-one base with the assessed zero-or-one active real-base rule. |
| 1.19 | Keep family/synonym separation and existing synonym-chain behavior. Its standing-based representative choice is not changed by this amendment. |
| 2.1 | Describe the family link as optional; keep permanent type and immutable original evidence. |
| 2.4 | Add a reference to 2.26 for naming across types. Keep the existing variant restrictions. |
| 2.19 | Change unconditional family-link wording to linking under 2.26/2.32. Keep final suffix and fixed type. |
| 2.20, 2.22–2.25 | Retain naming/admission proof and cached decisions. A listed or predicted underlying name is not proof of a real metric fact. |
| 2.26, 2.32, 2.35 | Replace as above. |
| 2.30, 2.33–2.34, 2.36–2.47 | Retain metric proof, one-fact sufficiency, shared-core ownership, first-state rule, immutable identity, independent matching, safe splits, and restrictions on bad records. |
| §3, “What each fact type needs,” XBRL row | Say guidance/surprise may inherit only through an eligible real base; absence is valid. |
| 4.14 | Add the explicit guidance-home pairing without a metric; retain every existing home-fact check. |
| 4.1–4.13, 4.15–4.21 | Retain types of comparisons, guidance states, company confirmation, withdrawals, and whole-event missing-home handling. |
| 6.2 | Replace the placeholder condition with the absent/unusable real-base condition. |
| 6.23 | Remove placeholder cleanup; retain propagation of repair restrictions. |
| 7.1, 7.6, 7.11 and 1.14 | Clarify standalone reads and time-safe relationship use; do not broaden series grouping. |
| 8.15–8.16 | Add precise link-completion triggers, without relaxing refusal or retry rules. |
| Word list: Driver, base metric/family, family link | State that a real guidance/surprise Driver may have no base yet; no placeholder state. |
| Part A1, scope | Replace “never a hidden placeholder” with “a real metric Driver already admitted with its own fact.” The tagged-data route remains off. |
| Part A1, standing | Unchanged here. Removing the four standing labels would require a separate amendment to this row. |
| Part B, “No family link” rejection | Clarify that abolishing the family relationship or merging types is still rejected; allowing a genuinely absent base is the proposed narrow exception. |
| Part B, fuzzy-placeholder-matching rejection | Preserve the ban on fuzzy family matching; remove dependence on placeholders as a current mechanism. |
| Part C, crosswalk/version/parking list | Record the exact owner-approved supersession. Preserve the original rationale and evidence as history; do not leave two competing live versions. |

The older source-design references affected are `FINAL_DESIGN.md` §0 (latent base), §3 NAME-17, §4.1 MF/OD-1/OD-2 family gates, §4.2 birth, §5.1 home facts, §5.4 recovery, §8 inheritance, and §9 reads. Older build procedures also assume mandatory bases, latent lists, and promotion. Their code or procedures must not be copied unchanged into the redesign. This proposal does not change the old documents or authorize their wholesale rewrite; the approval record must explicitly identify which former requirements it supersedes.

## 5. Behavior in the important cases

| What arrives | Required result |
|---|---|
| Valid guidance; no base exists | Create the guidance Driver with its own fact. No base node, no missing-base hold. |
| Another forecast or reaffirmation | Add/merge the fact under the usual identity rules. Do not create a new Driver merely because the amount, period, or movement changed. |
| First real metric fact arrives later | Independently prove the metric and check the existing family's evidence. Reuse permitted common wording; create metric plus fact, then form valid exact-name links. |
| Metric existed first | The new guidance/surprise uses the same naming and meaning checks; link the real endpoints. |
| Base never arrives | The member's valid facts remain usable on their own. There is no unfinished base to repair. |
| Guidance compared with consensus; no actual | Accept only with the same-event accepted guidance home and the checks in amended 4.14. No metric is invented. |
| Actual compared with expectations | Accept only with its real same-event metric home. That home supplies the real metric Driver. |
| Same spelling but different meaning/type | No family link. Use the existing specific-name or non-write outcome; do not let the spelling decide. |
| Different spelling, same apparent measure | Apply only permitted naming checks before creating a new Driver. Do not rename stored Drivers or silently point to a different-named base. Accepted splits remain possible. |
| Required evidence is missing or an independent check refuses | Use the existing held/skipped/rejected/separate outcome. Missing-base permission is not permission to accept unsupported meaning. |
| A base or relationship is later found wrong | Apply existing repair restrictions. Preserve records and valid standalone facts; no automatic reactivation or deletion. |

For simultaneous arrivals, exact duplicates must still converge and a failed write must leave no Driver without its first fact. Accepted near-synonym races may remain separate under 2.39. Equal underlying strings never bypass the relationship check, including when both Drivers are new in the same batch. This proposal does not promise perfect name convergence or introduce a new locking or reservation system.

## 6. Stress examples and evidence

These examples explain the general rules. They are not new sector-specific policies or gold labels for an automatic matcher.

For **Adjusted Cruise Costs Excluding Fuel Per ALBD**, an illustrative underlying name is:

`cruise_costs_excluding_fuel_per_available_lower_berth_day`

The alternative `cruise_excluding_fuel_costs_per_available_lower_berth_day` contains the same words in a different order. Neither is inherently safer. The permitted word-order check must settle on one wording before creation. An exact lookup of one spelling does not discover the other on its own.

The fuel exclusion and denominator preserve the measure. `adjusted` and any source-stated currency adjustment remain measurement tags. A growth forecast retains its growth basis and target period on the fact; a forecast that costs will rise is not automatically a raised forecast. Carnival's original release distinguishes capacity-based ALBDs from passenger days and distinguishes adjusted unit costs with and without fuel. This supports checking the actual definition, rather than trusting a similar label. [Official source](https://www.sec.gov/Archives/edgar/data/815097/000081509724000069/a20243qearningsrelease8-k.htm).

| Low-frequency legacy example | What the source review showed | General lesson |
|---|---|---|
| Net CapEx, 1 update | NFE defines net spending after specified asset-sale/financing proceeds. | Do not collapse a source-defined net measure into gross spending. |
| Net Sales per Active Customer, 2 updates; Net Sales per Square Foot, 2 | Different stated denominators. | Same subject does not mean same measure. |
| Call-off Volatility, 2 updates | A forecast describes a repeatable condition becoming lower, without a numeric level. | A valid qualitative guidance Driver does not need an earlier numerical actual. |
| Sponsored Ads Launch, 1 update | A plan to launch something, not automatically a forecast of a standing measure. | Future wording alone does not justify a metric family. Apply the existing type and suffix tests. |
| HSA Enhanced Rates Premium, 1 update | The stored answer alone is unclear; the original question supplies the 50–75 basis-point premium, and the preceding exchange identifies the product. | Include sufficient original source context. A legacy label cannot supply missing evidence. |

The prior read-only review inventoried 552 distinct legacy labels and 8,432 GuidanceUpdate records. It read all saved quotes for 242 labels appearing in at most two distinct source documents: 378 records, including every one-update and two-update label. It also checked selected more frequent cruise examples and the original source material noted above. Document counts are not distinct earnings-event counts; legacy label counts are not proven distinct Driver meanings.

This was a design stress review, **not** an executed new naming system. No new-system acceptance/rejection rate, end-to-end reliability, or successful production migration was measured. Full original sources were not reread for all 8,432 records. The old Guidance data remains evidence/test input only; rule 8.11 still forbids copying those rows into new Driver facts.

Supporting review: `/tmp/guidance_family_stress_20260928/review.md`; full label inventory: `coverage.csv`; rare saved quotes and source IDs: `rare_evidence.md`; original Q&A extracts: `hqy_source_context.json` and `hqy_context_enhanced.json`, all in that directory. The proposal is self-contained; those files provide deeper evidence while available.

## 7. Why this can be safe, and what still needs proof

The safety argument is conditional on enforcing the rules above:

| Risk | Required protection |
|---|---|
| A forecast masquerades as an actual | Permanent separate types; every metric requires its own accepted metric fact. |
| A similar name joins different measures | Exact suffix structure **plus** independently checked source meaning; fixed exclusions remain. |
| The first guidance name anchors later extraction | Source-first proposal; catalog comparison happens afterward; existing quotes never fill new facts. |
| Adjusted values, portions, or denominators collapse | Existing naming, scope, tag, unit, and full-series checks remain. |
| An unsupported surprise is accepted | Same-event accepted home fact and all matching checks remain mandatory. |
| Future actuals alter an earlier view | Source-time limits apply to evidence, candidates, endpoints, and relationship use. |
| Missing links drop valid forecasts from results | Standalone reads retain valid facts; family-dependent results remain unavailable where proof is missing. |
| A discovered bad relationship keeps influencing later results | Existing independent recovery, restrictions on reuse, disputed-fact handling, and reversible link controls remain. |

The change removes a storage exception, not the evidence standard. It cannot guarantee that an LLM will always name or match correctly. The rulebook itself acknowledges wrong first encounters, missed matches, and undetectable qualitative mistakes. Initial checks do not replace later correction.

Before implementation is accepted, the implementing bot must:

1. Freeze the reviewed rules, code, inputs, and independently sourced expected answers. Derive the affected entry points and failure paths from live code, including readers and recovery; do not use this example list as the whole inventory.
2. Reproduce the relevant failure in a test before changing behavior, make the smallest general change at the owning boundary, then run focused and full regression suites. No word lists, cruise-specific branches, or duplicate rule engines.
3. Test both arrival orders, same-event creation, base never arriving, partial write failure, repeated input, concurrent duplicate births and concurrent births of different family members, conflicting names/types, suffix mutations, permitted word permutations, and uncertain identity. Negative cases need real positive controls.
4. Test both surprise-home paths, missing/held/rejected homes, before-period-end actual surprises, measurement/slice/period/unit mismatches, and numberless homes.
5. Test standalone reads, time-cutoff views, absent or disabled inheritance, and every affected recovery path. Verify that optional-base handling never relaxes a known-bad-record restriction.
6. Use the complete observed legacy label population as a coverage inventory, then retrieve original sources for independently judged cases. Count every accepted, held, skipped, rejected, missed, and unscorable category; add unseen examples for the open vocabulary. Old labels and old extracted fields are not their own answer key.
7. Preserve 8.17's existing launch bar and 8.13's exact-task qualification. Report semantic uncertainty and honest error bounds; a document review or green mechanical test suite is not certification.

The current graph was queried read-only on 2026-09-28: **0 `Driver` nodes, 0 `DriverUpdate` nodes, and 0 `BASE_METRIC` relationships** in the configured database. Thus no live Driver-placeholder migration is presently demonstrated as necessary there. This says nothing about other databases or offline artifacts; check actual deployment inputs before an implementation. No database writes were made or authorized.

A limited code check found the existing surprise-home validator in `driver/core/driver_validators.py`, including `_expected_home_name` and `_home_mismatch`. Its own comment says the exact-name-only path is blocked beyond its pilot pending family integration. This is evidence of a dependency to review, not evidence that this proposal already works. No implementation or test suite was changed or certified here.

## 8. Relationship to the four Driver stages

The owner wants Drivers to be fully created once admitted and ideally to remove `young`, `established`, `frozen`, and `quarantined`. Two different questions must not be conflated:

- **Can valid guidance exist before an actual metric?** Yes, under this amendment, without an empty base or a waiting/promotion process.
- **Can every Driver be trusted forever after its first checks?** No such guarantee follows. The existing stages also govern review, reuse, and error containment, independently of placeholders.

This amendment leaves 2.2 unchanged. It does not create a new lifecycle. The exact remaining dependencies for a separate stage-removal decision are:

| Current dependency | Behavior that must have an explicit replacement before removing the labels |
|---|---|
| 2.2 young/established | Decide which evidence review is still required for reuse; never substitute a frequency threshold or an assumption of permanent correctness. |
| 1.19 representative selection | Replace “established beats young” with an approved selection rule that does not weaken identity checks. |
| 2.2 frozen; 6.22–6.25 | Preserve stopping unsafe history/cross-company uses while evidence is checked. |
| 2.47 and 6.20–6.24 quarantined/error handling | Preserve blocking known-bad reuse, flagging existing wrong facts, related-family protection, and independently approved recovery. |
| Part A1 standing | Specify how the dormant tagged-data route handles affected Drivers; do not silently enable it. |
| 9.9 | Keep instant synonym linking off; removing a standing label must not enable it. |
| 10.2 | Do not imply that naming/type errors on stored Drivers now have an approved repair. |

Removing the labels while preserving restrictions through existing repair records may be possible. That would remove a normal maturation workflow, **not** remove the need to remember a discovered error. Renaming a quarantine flag is not proof that all state disappeared. This document deliberately does not claim that the broader stage-removal design is already complete or safe.

## 9. Requested board verdict

Review the proposed **no-placeholder amendment** independently of the wider lifecycle goal. Report:

1. Whether valid guidance can safely be born without a metric Driver under these exact safeguards.
2. Any current rule or unnumbered requirement the edit map missed, with its location and a concrete failing case.
3. Whether the cross-type naming check preserves the source-first rule and all existing bans on unsafe matching.
4. Whether both surprise-home paths, historical reads, XBRL inheritance, and recovery remain safe with an absent base.
5. Whether any proposed machinery can be removed without losing required behavior. Recommend the smaller safe choice; do not add architecture for hypothetical cases.
6. Whether any claim here exceeds the evidence. In particular, do not equate this design review with semantic certification or with approval to remove all four standing labels.

Approval of this document would approve the specified rule amendment only. It would not authorize production writes, model spending, migration, activation, deletion, automatic cleanup, or unrelated changes. The owner must confirm any actual rule-file amendment before it is applied.

Source snapshot: `DRIVER_RULES.md` SHA-256 `11b08f1550ef1c73c5a275d57a735735a113360730c08400f964ca2071397096`; older `FINAL_DESIGN.md` SHA-256 `813d0af2419e5681d46e66fedbbe8b8e7b111508abba052a0d71bdd4eb79dccf`. The earlier graph evidence export is pinned by `/tmp/guidance_family_stress_20260928/manifest.json`, data SHA-256 `54c5a5ee1798b387cc51e6c3d35550f7bd3829b0edfd45318c6aa6f48d14653d`.
