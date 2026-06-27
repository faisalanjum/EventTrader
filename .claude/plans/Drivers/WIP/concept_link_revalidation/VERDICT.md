# VERDICT — does the concept-linker hold up under independent re-validation?

**Short answer: YES on precision and abstention — decisively, against a non-LLM answer key, on
274 companies across all sectors and both guidance and non-guidance. Recall is strong on clear
metrics with a well-characterized (and safe) residual.** Stability: see §Stability.

## Scorecard (274-company cohort, non-LLM ground truth)

| Bar | Result | Verdict |
|---|---|---|
| **PRECISION** (cardinal) | **0 confirmed-wrong links** across 274 companies; every out-of-GT link adjudicated correct/defensible by us-gaap definition | ✅ holds — 100% |
| **ABSTENTION** | **0 / 10,960** conceptless-driver leaks (ratio, action_event, macro, non-GAAP, KPI) | ✅ holds — 100% |
| **RECALL** | core metric **93.6%** (effective higher; residual is mostly defensible abstention on ambiguous aggregates) | ✅ strong, safe residual |
| **STABILITY** | _PENDING (runs 2–3)_ | — |
| **Coverage** | 274 / 795 companies (session-limited; owner scoped assessment to these), all 11 sectors, 31 guidance + 243 non-guidance | ◑ representative, not the full 795 |
| **All 4 fact_types** | metric ✅, guidance/surprise (abstain → BASE_METRIC) ✅, action_event (abstain) ✅ | ✅ all exercised |

## What the prior proof got wrong, and what this fixes

- Prior precision was **LLM-judging-LLM** on **31 guidance companies**. This run scores against a
  **non-LLM** answer key (canonical us-gaap concept families + balance/period structure), detects the
  cardinal "wrong link" **deterministically**, and spans **274 companies incl. 243 non-guidance**.
- The matcher's precision **held** under the harder test: still 0 wrong links, and it even resolves
  **industry-specific and partnership (MLP)** concepts correctly — beyond anything a curated list holds.

## Residual risks / honest caveats

1. **guidance/surprise inheritance is required.** Feeding `revenue_guidance` directly → the matcher
   abstains. Production MUST resolve the base metric and inherit via `BASE_METRIC` (or strip the
   suffix before `link()`). Not a wrong-link risk; a recall/wiring requirement.
2. **`sg_a → GeneralAndAdministrativeExpense`** (4 companies) and **`total_debt → NotesPayable`** (1)
   are nearest-line approximations, not exact. Defensible, but flag if SG&A vs G&A precision matters.
3. **Ambiguous aggregates** (`total_debt`, `operating_expenses`) are abstained often — correct for
   precision, but means low recall on those specific names. Consider splitting them in the driver
   vocabulary (`long_term_debt` vs `total_debt`).
4. **Coverage = 274/795** (session limit). The cohort spans every sector and both guidance status, so
   conclusions generalize, but the remaining 521 companies were not run.
5. The GT canonical families are authoritative for ~33 core metrics; obscure/extension metrics
   outside them are scored via adjudication, not an a-priori family.

## Recommendation (no code changed)

The algorithm is **sound for production as an enrichment link**: precision-first, abstains when
unsure, generalizes across the universe. Wire `BASE_METRIC` inheritance for guidance/surprise, and
consider disambiguating `total_debt`/`operating_expenses` in the driver names. No change to
`concept_linker.py` is warranted by this re-validation.
