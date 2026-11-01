# ALGORITHM — DriverUpdate → XBRL Concept link

## Crux (plain words)

**Goal:** given a driver (a company + a metric name like "revenue"), find the exact XBRL
concept that company reports for it (e.g. `us-gaap:RevenueFromContractWithCustomer…`), or say
"no concept" — and never link the wrong one.

**The answer:** let an LLM pick the right concept from the company's **own list of reported
concepts** (its "menu") by meaning, then **independently try to prove that pick wrong**. Link
only what survives. Two cheap rule-guards abstain up front on the kinds of metrics that have no
exact concept. No hand-built dictionary anywhere — the only knowledge used is each company's own
reported concept labels.

```
driver (company, metric name)         value is NOT used at inference
        │
        ▼
  ┌─ GUARD ──────────────────────────────────────────────┐
  │ abstain if metric is:                                  │
  │   • an event/action (ceo_resignation, buyback)         │  ← schema fact_type=action_event
  │   • macro/exogenous (oil_price, fx, rates)             │
  │   • a ratio/derived (margin, ebitda, fcf, *_growth)    │  ← no exact GAAP line
  │   • non-GAAP (adjusted_*, non_gaap_*)                  │  ← value ≠ GAAP fact; base carries it
  └────────────────────────┬───────────────────────────────┘
                           ▼
  build company MENU  =  concepts it actually reports {qname, label, usage}   (QUERY_2A)
                           ▼
  LLM-PICK             pick the ONE menu concept that IS this metric, else NONE
                           ▼
  ADVERSARIAL VERIFY   independent LLM tries to REFUTE the pick; refuted → abstain
                           ▼
                 emit qname  (or abstain)
```

## Why this design (each loser ruled out by census evidence — see ATTEMPTS.md)

| Approach | Why it fails the 100%-precision bar |
|---|---|
| Value+period anchoring alone | Dense value space + forecast noise → a wrong concept always sits within tolerance; right vs wrong matches have the **same** closeness. Demoted to *auditor*, not matcher. |
| Deterministic label/token match | "revenue" ⊆ "**cost**of**revenue**" → semantic inversion. Strings can't see meaning. |
| 2-method agreement (numbers ∧ strings) | Their failures can **correlate** → false agreements (`net_income → IncomeTaxesPaidNet`). |
| LLM-pick alone | High precision/recall, but occasionally misses GAAP-vs-non-GAAP. Needs the guards + adversary. |
| **LLM-pick + guards + adversarial verify** | Semantics (cost≠revenue, GAAP≠non-GAAP) + a refuter that defaults to "wrong when unsure". **Winner.** |

## Why it meets the bar

- **Precision (cardinal):** every emitted link passed (a) a meaning-based pick, (b) an
  adversarial refute panel that abstains when unsure, and — for the proof — (c) independent
  confirmation by value-anchoring (numbers) and/or label-crosswalk (strings). Unsure → abstain.
- **Recall:** uses the company's real menu + general semantics, so it covers far more than a
  curated dict and even **company-extension concepts** (`aso:NumberOfNewStores`,
  `…:EmissionsTradingSchemeCostOfAllowances`) that no hand list would contain.
- **Abstention:** the two guards encode the schema's own `fact_type` routing + the GAAP/non-GAAP
  rule; ratios/derived/events/macro/non-GAAP get no link.
- **Autonomous & general:** no curated concept dict, no human approvals. Knowledge = the company's
  reported concept labels (the taxonomy *as data*) + the LLM. Works for any slug, any company.
- **Minimal:** menu + one LLM pick + one adversarial check + two regex guards. Nothing else.

## Autonomous answer key (zero human labels) — how it's proven

The test bed is the 8,432 real **GuidanceUpdate** nodes (stand-in DriverUpdate inputs: company +
metric + value + period). Ground truth is built from the 9.9M XBRL **Facts**, never a human:

1. **Value+period anchoring** (numbers): scale a guidance value, find the company's reported Fact
   with matching value+period → that Fact's concept. Independent of all semantic methods.
2. **Label-crosswalk** (strings): normalized token match of metric ↔ concept label/local-name.
3. **Adversarial 3-lens panel** (same-value / filer-intent / name-precision): ≥2-of-3 must confirm.
4. **Multi-method agreement = truth; disagreement = abstain.** A link is *proven correct* only with
   independent confirmation; conflicts are audited (and turn out to be value-anchor coincidences).
5. **Negative set** of conceptless drivers (events, macro, ebitda/fcf/margins/growth) → must abstain.
6. **Long-tail self-labeled** breadth: 1,395 reported concepts as their own answer → recall on
   metrics that provably have a concept.

## Production-scale note (this run = 31 companies)

Per-company LLM-pick is fine here. For 796 companies × ~1000 drivers, cache an LLM-generated
slug→candidate-concept-family map ONCE (from the us-gaap taxonomy), then intersect with each
company's menu; only call the LLM for ambiguous intersections. Same precision, far fewer calls.
The link attaches per-DriverUpdate (company-scoped qname); `guidance/surprise` drivers inherit
their base metric's concept via `BASE_METRIC`; `action_event` drivers never link.
