# Actionable recommendations — proposed design

- **Recommended: keep the four existing types and add `expectation` as a fifth for outside forecasts.** Record whose forecast it is; keep it separate from company guidance.
- **Record source-stated causes.** Meaning decides; no cue-word lists. Link accepted updates only when a small source passage supports both claims and their connection; use bounded nearby context or count a skipped link.
- **Support missing units and currencies.** Match by meaning, not symbol alone; use standard definitions plus evidenced custom units. Preserve source units and scales; allow exact rescaling, not assumed equivalences or FX conversion.
- **Preserve essential qualifiers.** Store text values, conditions, denials, participants and distinct dates when they affect meaning.
- **Clarify fact boundaries.** Separate one-off events from standing levels/conditions, planned actions from forecast levels, and predicted misses from observed misses. Count unclear facts; never force them into a type.
- **Share macro facts.** Reuse each source-backed macro release/comparison across affected companies, preserving its period and expectation source.
- **Fix inputs and enforce information cutoffs.** Check unreadable text, company attribution and source versions. Exclude the outcome being predicted from prediction inputs.
- **Validate coverage and usefulness.** Use fresh, independently labeled text to measure misses, errors and facts that fit nowhere. Then test predictive improvement on unseen events.

---

# Fact types — evidence handoff · 2026-09-30

**Goal:** “turn financial text into consistent, source-backed facts about reusable Drivers—so we can track changes, explain stock moves, learn what matters, and improve predictions.” Driver = one reusable cause or standing thing; DriverUpdate = source-backed occurrence.

**Scope:** whole design; releases decide activation. These are recommendations. [Canonical rules](DRIVER_RULES_Categorized.md), production code, Neo4j and Notion remain unchanged; current owner decisions take precedence.

## Evidence — reuse, do not restart discovery

- **Codex:** rules, 32 Notion pages, 321 frozen passages + 15 separate challenges across filings, calls, news and XBRL; all 11 sectors. One semantic reviewer.
- **Claude:** 873 pieces; 317 fact-bearing pieces; 510 labeled facts. **460/510 = 90.2%** labeled clean; filings **317/342 = 92.7%**. Sample judgments, not population coverage/extractor accuracy; do not pool audits.
- **Corrections:** two added ambiguities among **41 initially fact-bearing pieces**, not a labeling error rate. Another 98 random checks were initially non-facts. Across all 317 helper checks, helpers found facts where final labels had none in **10 pieces: 3 random, 7 flagged**; capture remains unmeasured. Helpers were primed on external forecasts. The `<0.34%` unseen-gap bound is invalid.
- **Verification:** 35-item review and this revision independently checked; 9,100 **source parts** rebuilt byte-identically; scans and live unit totals reproduced. Completeness and predictive improvement remain unproved.
- **Reproduced screens:** 98.6% of 12,432,556 tagged-unit links (including nil records) use USD, shares, pure or USD/share. Strict unit regex hits: **13.1%** of EX-99 exhibits (n=1,500), **44.2%** of Business/Properties sections (500), **18.5%** of prepared remarks (800). Price-target text: **1,933/4,000 news stories = 48.3%**. These are screens, not missing-fact rates. **Hand-check correction:** 113 saved excerpts contain at least six wrong number/unit pairings; no extractor accuracy is established.

## Recommended design

**Recommendation: retain four types, add `expectation` as a fifth, and design stated relations and broader units.** Codex’s earlier “price target → metric” answer was insufficient under 1.6/9.2.

| Area | Recommendation |
|---|---|
| External forecasts | Fifth type **`expectation`** preserves company-only `guidance`; broadening guidance with strict origin separation remains viable. Cover targets, estimates, consensus and event predictions; retain forecaster, subject, horizon and basis. Forecasters/rating issuers distinguish histories; reporters are provenance. Ratings remain metric/action. |
| Why something changed | Source-asserted fact→fact relations, separate from stock-price `EXPLAINED_BY`. Distinguish **causes/offsets** from **composition/contributions**; require accepted endpoints, evidence and attribution. Preserve stated amounts/conditions. “Includes” alone is not causality. Claude flagged causes in 46/317 fact-bearing pieces; Codex in 47/321 passages. |
| Units | Versioned [XBRL UTR](https://www.xbrl.org/utr/utr.xml) / [ISO 4217](https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html), plus evidenced custom units: UTR is not exhaustive. Match meaning: text `MT` can mean metric tons; UTR `MT` means million US tons. Preserve raw units, scale, denominators, measurement and growth basis. Exact rescaling is allowed; assumed equivalences/FX conversion are not. Unknown units remain ungrouped. |
| Values/time | Source-quoted metric text values; conditional payments/sensitivities; actor roles; allegations/negation. Separate publication, as-of, expected-event and maturity dates; preserve pro forma/KPI-definition differences. Reconcile current restrictions, including **9.8**. |
| Macro | One source-backed macro actual/comparison shared across companies’ verdicts. Extend company-only surprise wording; preserve consensus provenance and public-time cutoffs. |

**Cause links with small inputs — pilot proposal:** Keep source/version/locations; reuse nearby extracted facts as a menu. Start with **3 consecutive sentences, advancing by 1**; retain list lead-ins/context. This includes the PVH example’s earlier target. If context is insufficient, expand once to **5 sentences** (one before/after), within the existing reader cap; still unclear/missing → skip/count. Change sizes only on measured misses and cost. **Close to 100% link coverage is the owner’s target; the pilot measures what the window achieves.** A passage-level yes/no gate remains optional; a per-fact “why did this change?” gate can miss links. Admit Drivers sequentially; bind exact accepted DriverUpdates, deduplicate overlapping links, and save with facts in the event transaction. Separate runs without retained bindings stay unlinked. Valid IDs do not guarantee correct relationships. [Live counterexample](../../../../../driver_typology_audit_20260930/claude_revision_2_20260930/cause_gate_followup.json); [design](../../../../../driver_typology_audit_20260930/causal_links_chunked_design/design_review.json); [comparison review](../../../../../driver_typology_audit_20260930/claude_revision_2_20260930/concurrent_cause_review.json). [93 Claude labels](../../../../../.claude/projects/-home-faisal-EventMarketDB/backups/fact_types_study_2026-09-30/cause_link_locality/cause_link_item_labels.json) now reproduce exactly; they remain cue-selected author judgments. [Five-edit review](../../../../../driver_typology_audit_20260930/claude_revision_2_20260930/locality_labels/review.json).

## Boundaries and next work

- **Metric/action (17/50 labeled misfits):** separate period totals from discrete events, lawsuit steps from standing exposure, policy changes from policies in force (7.7), and forecast activity counts from actual counts. Fixed defaults take precedence (1.8/2.27); table location never decides type.
- **Forecasts/actions:** decompose planned acts and forecast levels; predicted misses are not observed surprises. Preserve likelihood and conditions for outside decisions; `pending` needs evidence of an actual process. A company’s prediction of someone else’s decision still needs an explicit typing rule; an outside decision-maker is not an outside forecaster.
- **Capture:** 2.33 drops boilerplate, bare mentions and non-facts. **Proposed clarification:** drop generic definitions and unsupported promotion, never specific facts merely because common. **In live use (2.30),** skip unclear items; count `no_type_fits` through existing outcomes. The narrow non-live action fallback retains its warning.
- **Comparisons:** dropping coverage does not automatically withdraw a specific target. Store movement only when stated; comparable reads may derive it (4.4). Computed surprises need a separate design; vendor-calculated figures remain forbidden by **1.13**. Claude’s mapping of 50 misfits is a projection, not a result.

Resolve PDF/encoded inputs, question-only exchanges and A154’s company/content inconsistency. Preserve table headings/cells; 1.17 requires original 8-K tables. News update timestamps do not prove content revisions; tags do not establish ownership. Exclude the target outcome even when stated inside source text (T003/T012/S16-084); past returns public before a later target are not automatically leakage. **P7:** Learner receives `ACTUAL_RETURN`. Owner enabled Predictor/Learner and price verdicts in release 1 despite stale 9.5/9.7.

**Rules to reconcile before building — entry points, not a complete migration:** expectation: 1.9–1.10, 2.19–2.24, 3.1–3.3, 4.4/4.9/9.2; links/reads: 3.9–3.12, 7.11; qualifiers: 9.8; units/currencies: 3.28–3.35, 9.1, A1; macro surprise: 1.9, 4.1–4.3; news ownership: 3.9/P4; releases: 9.5/9.7/P5. The chunked-input proposal also needs 8.9–8.10 reconciled: 8.10 currently requires whole-event reading.

Next: fresh neutral independent gold/adjudication; measure capture, meaning, identity, units/time and relation precision/recall per source. One piece/document does not eliminate clustering. Zero failures in 300 trials gives a <1% one-sided 95% bound **only for independent representative trials with valid gold**. Then compare raw text/current records/additions on unseen events with identical cutoffs.

## Evidence map

- [Codex report](../../../../../driver_typology_audit_20260930/report.html), [casebook](../../../../../driver_typology_audit_20260930/casebook.html): A/T IDs; adjacent sources, protocol, coverage and archived Notion pages.
- [Claude study](../../../../../.claude/projects/-home-faisal-EventMarketDB/backups/fact_types_study_2026-09-30/FACT_TYPES_STUDY_2026-09-30.md), [full review](../../../../../.claude/projects/-home-faisal-EventMarketDB/backups/fact_types_study_2026-09-30/CLAUDE_REVIEW_OF_fact_types.md), [errata](../../../../../.claude/projects/-home-faisal-EventMarketDB/backups/fact_types_study_2026-09-30/CLAUDE_ERRATA_2026-09-30.md): S IDs; adjacent labels, helper guide and scans.
- [Independent 35-item review](../../../../../driver_typology_audit_20260930/claude_review_20260930/review_findings.json): corrections, evidence, alternatives and statistical limits.
- **[Latest independent revision review](../../../../../driver_typology_audit_20260930/claude_revision_2_20260930/review_findings.json):** point-by-point decisions, reproduced scripts, 28 live source checks, unit census and official registries. Supersedes conflicting earlier claims; records the errata’s subsequent correction of 110/112 and preserves original audits.
