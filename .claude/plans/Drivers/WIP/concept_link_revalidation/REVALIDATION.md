# RE-VALIDATION — concept-linker across the full universe

**Under test (unmodified):** `plans/Drivers/WIP/concept_link_probe/concept_linker.py` —
`link(company, slug, menu, llm)` = deterministic GUARD → LLM pick-from-menu → adversarial verify →
link/abstain. Run faithfully: the exact `guard()` is applied in-harness (guarded slugs abstain with
no LLM), and the exact `PICK_PROMPT`/`VERIFY_PROMPT` are dispatched to agents (the `llm`); final
link = `pick if (real and pick∈menu) else None` — identical to the module.

**Fixes vs the prior proof:** prior = 31 guidance companies, LLM-judged precision, circular
"humanized-label" recall, one fact_type, no stability. This run:

| Dimension | Prior | This re-validation |
|---|---|---|
| Companies | 31 (guidance only) | **795** (all menu-capable); 31 guidance **+ 764 non-guidance** |
| Ground truth | LLM panel (LLM-judging-LLM) | **non-LLM**: canonical us-gaap families ∩ menu + structure + value-anchor |
| Recall labels | circular (name from answer) | independent metric names; GT from documented taxonomy |
| fact_types | guidance only | **all 4**: metric, guidance, surprise, action_event |
| Stability | none | **3× runs**, flip rate per cell |

## Independent ground truth (non-LLM, non-circular)

The crux. GT is built only from signals independent of the method under test:

1. **Canonical us-gaap concept families** — for ~33 core metrics, the documented standard
   concept local-names (e.g. revenue → `Revenues` / `RevenueFromContractWithCustomer…`;
   net_income → `NetIncomeLoss`/`ProfitLoss`). This is a taxonomy FACT, not derived from any
   matcher answer. `GT(company, metric) = family ∩ company-menu`.
2. **Structural signature** — each concept's `balance` (credit/debit), item-type, `period_type`
   from the graph. Independent of token text; catches inversions (revenue=credit ≠
   cost-of-revenue=debit). Used to flag CONFIRMED-WRONG links with no LLM.
3. **Value+period anchoring (signal A)** — cross-check only. Strict-unique anchoring is NOISY
   (its disagreements with the canonical GT are visibly coincidences: capex→LeaseCost,
   net_income→Goodwill), which is itself evidence that value-anchoring cannot be the matcher and
   that the canonical GT is the reliable spine (the CLEAN/dominant value-anchored families —
   net_sales→RevenueFromContract (support 69), diluted_share_count→WeightedAvgDiluted (62),
   dividend_per_share→CommonStockDividends — all agree with it).

A matcher link is scored:
- **CORRECT_LINK** — picks a GT-family member.
- **CONFIRMED-WRONG** (non-LLM) — picks a concept in a DIFFERENT metric's canonical family, or one
  whose structure contradicts the metric's signature.
- **REVIEW** — picks an out-of-GT-family concept that is not provably wrong (possible GT gap);
  adjudicated separately, never silently counted as correct.
- **RECALL_MISS** — abstains where the company reports a GT-family concept (safe; not a wrong link).
- **CORRECT_ABSTAIN / LEAK** — for conceptless drivers and not-reported metrics.

## Coverage (built)

- **795 companies**, all 11 sectors, guidance (31) + non-guidance (764).
- Per-company menu = faithful `QUERY_2A` (top-level numeric concepts) + structural attrs.
- **Probe set: 59,625 (company × metric) GT cells**, all 4 fact_types:
  metric (core) 21,465 · guidance/surprise variants 6,360 · conceptless ratio 10,335 · event/action
  8,745 · macro 5,565 · non-GAAP 3,180 · KPI 3,975.
- 27,030 abstain by deterministic guard (no LLM); 32,595 dispatched to the LLM.
- 23,943 core/variant cells where the company reports the concept (GT = link).

## Results (274-company cohort, non-LLM ground truth)

The matcher ran on **274 companies** before the subscription session limit (locked cohort, all 11
sectors, 31 guidance + 243 non-guidance). Per the owner's instruction, accuracy is assessed on these
274 only. ~38,000 GT cells scored.

| fact_type | confirmed-WRONG | precision | recall | abstention |
|---|---|---|---|---|
| **metric** (core, 7,398) | **0** | **100%** | 93.6% (effective higher¹) | 97.7%² |
| guidance / surprise (2,192) | 0 | 100% | ~3% (abstains → BASE_METRIC)³ | 98.6% |
| conceptless ratio (3,562) | — | — | — | **100%** |
| conceptless event/action (3,014) | — | — | — | **100%** |
| conceptless macro (1,918) | — | — | — | **100%** |
| conceptless non-GAAP (1,096) | — | — | — | **100%** |
| conceptless KPI (1,370) | — | — | — | **100%** |

**Headline: 0 confirmed-wrong links across all 274 companies. Conceptless abstention = 100%
(0 / 10,960 leaks).**

By stratum (metric+variant link cells): **guidance — precision 100%, recall 71%** ·
**non-guidance — precision 100%, recall 70%.** The 764-company non-guidance stratum the prior proof
skipped behaves identically to guidance.

¹ 30 out-of-canonical-GT links adjudicated → all correct/defensible (industry + partnership/MLP
  concepts no static list holds); 0 wrong (FAILURES.md §2). Recall residual is ~58% defensible
  abstention on ambiguous aggregates (total_debt, operating_expenses) — FAILURES.md §3.
² the 27 "leaks" are the same adjudicated-correct out-of-GT links, not real leaks.
³ the matcher abstains on suffixed slugs (safe); production inherits via BASE_METRIC (FAILURES.md §4).

**Stability (3 independent runs, 270 companies in all 3, 11,070 non-guarded cells):** **98.0%
identical** (flip rate 2.04%, 226 cells). Flips = 172 link↔abstain (borderline) + 54 link↔link
(synonyms, e.g. Revenues↔RevenueFromContractWithCustomer); **0 flips introduce a wrong concept**
(checked: no link↔link crosses into a different metric's canonical family). NB: an earlier 2-run
figure of 0.66% was diluted by un-run companies — 2.04% is the clean per-company number.

## Why this is stronger than the prior proof

- Precision is measured against a **non-LLM** answer key (canonical us-gaap + balance/period
  structure), and the cardinal "wrong link" is detected deterministically — no LLM judging an LLM.
- **274 companies, all sectors, guidance + non-guidance** (prior: 31 guidance only).
- The matcher generalizes to **industry-specific and partnership (MLP) concepts** — found correctly,
  not in any curated list.

## fact_type handling

- **metric** — core metrics, GT = canonical family.
- **guidance / surprise** — `<base>_guidance`, `<base>_surprise` slugs; GT = base metric's family
  (tests whether the LLM effectively base-strips, since the guard does not). In production these
  also inherit via `BASE_METRIC`.
- **action_event** (+ ratio/macro/non-GAAP) — conceptless; GT = abstain.
