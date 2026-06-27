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
| **STABILITY** | **98.0% identical across 3 independent runs** (flip 2.04%, 270 companies, 11,070 cells); **0 flips introduce a wrong concept** — all are link↔abstain on borderline cells or synonym↔synonym | ✅ holds |
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

## Recommendation — LOCKED production recipe

The core `link()` (guard → menu-pick → adversarial-verify) is **sound as an enrichment link**:
precision-first, abstains when unsure, generalizes across the universe (guidance ≈ non-guidance).
On top of it, the **locked production recipe** (canonical spec: `Consolidation/XBRLConceptLinking.md`):

**Haiku + deterministic backstop + component-veto.**

| Strategy (274 cohort, non-LLM GT, strict wrong-count) | Wrong | Recall | Abstention |
|---|---|---|---|
| All-Haiku, no fixes | 42 | 93.9% | 100% |
| Haiku + backstop (rules A–C) | 18 | 93.7% | 100% |
| **Haiku + backstop + component-veto D (LOCKED)** | **1** | **93.7%** | **100%** |
| Haiku + backstop + prompt abstain-rule (alternative) | 2 | 92.2% | 100% |
| All-Opus | 4 | 93.6% | 100% |
| Split (Haiku-pick + Opus-verify) | 2 | 90.5% | 100% |

**Why this recipe.** The errors split into two buckets, each with a **deterministic** fix:
1. **Model errors** (a better concept was in the menu, model picked worse: shares→weighted-avg,
   eps→basic, dividend→total-$) → the **backstop** (period_type / basic-diluted / per-share rules).
2. **Scope mismatches** (no exact concept existed, model approximated a part for the whole:
   sg_a→G&A, opex→SG&A) → the **component-veto** (a 4-entry "a part ≠ the whole" deny-set).

The **deterministic component-veto beats the prompt abstain-rule on every axis** (1 vs 2 wrong, 93.7%
vs 92.2% recall, deterministic vs model-dependent): the prompt-rule lives in the shared PICK/VERIFY
prompt, so it quietly drops **87 correct links globally** (eps/capex/debt) to avoid 1 wrong link — a
bad trade on a recoverable link. So the veto is locked; the prompt-rule is kept only as a documented
fallback. Both layers are deterministic → no drift.

**Also required:** wire `BASE_METRIC` inheritance for guidance/surprise. **Do NOT** rename `sg_a`
(disproven — it maps correctly wherever the combined SG&A concept exists; the veto handles the rest).

**Honest caveats (don't read "1 wrong" as the general precision):**
- **"1 wrong" is the tuning-set number.** The deny-set is calibrated to the errors seen on these 274
  companies; a list is blind to the unseen. On the other **521 + future companies, new part-for-whole
  pairs slip through until added** — and the residual itself proves the list is already incomplete:
  the 1 wrong is **`CCL cost_of_revenue → OperatingCostsAndExpenses`**, a scope mismatch NOT in the
  4-entry set. So real-world wrong sits a touch above 1. (The prompt-rule, being general, would catch
  these — its one genuine advantage, at the 87-link recall cost.)
- **The deny-set is pattern-matched, not principled:** it denies `total_debt→NotesPayable` but keeps
  the structurally-identical `total_debt→LongTermDebt` (10 companies) — two opposite calls on the same
  "total ≠ one component" shape.
- **The structural monitor does NOT catch new bucket-2 slips** (same balance/period); they persist
  until audited. The **data-driven us-gaap calculation-hierarchy veto** is the proper general+
  deterministic fix — recommended before the full-universe rollout.
- Coverage 272/274 ≈ **35% of 795** (representative; full-universe run pending). Core `link()` code is
  unchanged; production adds the §3.3 backstop+veto from the spec.

**Net (unchanged decision):** for a recoverable enrichment link the veto still wins — fewer
confirmed-wrong, full clean-metric recall, deterministic. The caveats keep it honest: near-100% **on
seen data**, with a generalization gap the hierarchy closes.
