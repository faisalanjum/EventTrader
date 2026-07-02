# 08 · XBRL concept-linking

**What this is:** how a DriverUpdate gets linked to the one official XBRL accounting line a company reports for it — or to nothing. The locked recipe = **"Haiku + deterministic backstop + component-veto."**

> Every rule is **LOCKED** / **EVIDENCE** unless marked **⏳ RECOMMENDED**. Source = `Consolidation/XBRLConceptLinking.md`.
> **Still open here:** XC-16 (calc-hierarchy veto, recommended before full rollout). *(The menu PIT cutoff — XC-09 — is resolved: both the concept-link and slice menus are PIT, 2026-07-02.)*

---

## A. What & why

#### XC-01 — The goal: attach the one concept, or nothing  `[LOCKED]`
- **Plain:** Link a driver to the ONE XBRL line a company reports for it — or link nothing. A missing link is fine; a WRONG link is the only real failure.
- **Rule:** Attach the one exact XBRL concept the company reports (`revenue` → `us-gaap:RevenueFromContract…`), or NOTHING. ENRICHMENT: recoverable, never identity; a missing link is harmless, a WRONG link is the cardinal sin. Company-scoped (same metric = a different qname per company). Value NOT used at inference. Attaches to the DriverUpdate FACT, not the class (cross-ref FS-21).
- **Why:** A wrong link poisons a trade; a missing one just loses a bonus — so the design optimizes to never emit a wrong link.
- **Source:** XBRLConceptLinking.md §0/§1

#### XC-02 — Rejected alternatives (all tested)  `[EVIDENCE]`
- **Plain:** Four simpler approaches were tried and failed; menu-pick is what survived.
- **Rule:** Rejected: (a) match by the NUMBER (value+period) — dense space, right vs wrong indistinguishable (value-anchoring is the offline answer-key ONLY); (b) string/token match — "revenue" ⊆ "cost of revenue"; (c) curated dictionary — upkeep + misses extensions; (d) multi-method agreement — the two agree on the SAME wrong answer. What holds: guards + menu-pick-by-meaning + adversarial verify + deterministic backstop.
- **Why:** Each shortcut produces a confident wrong link — the one thing we must avoid.
- **Source:** XBRLConceptLinking.md §2
- **Replaces:** curated dictionary → menu-pick — 95_Supersession #13

## B. The pipeline + model

#### XC-03 — The pipeline (per driver)  `[LOCKED]`
- **Plain:** Guard → build the company's menu → LLM picks one (or null) → in-menu check → LLM adversarially verifies → deterministic backstop/veto → emit or abstain.
- **Rule:** `link()` per driver: GUARD (deterministic) → company MENU → LLM PICK one menu concept or null → in-menu check (never a hallucinated concept) → LLM VERIFY (adversarial: try to refute) → refuted/unsure ⇒ abstain → STRUCTURAL BACKSTOP + component-veto (deterministic) → emit qname else abstain.
- **Why:** Layered defense — each layer catches a different failure mode.
- **Source:** XBRLConceptLinking.md §0/§3.4

#### XC-04 — Model = Haiku (cheapest)  `[LOCKED]`
- **Plain:** The cheapest model (Haiku) is used; the deterministic structure makes it match a top model on precision.
- **Rule:** Use Haiku (the locked cheap path). Structure + the two deterministic fixes make Haiku match/beat a top model on precision at cheap cost. Documented alternatives: Opus/Sonnet (similar precision, higher cost); Haiku-pick + Opus-verify split (Opus-grade precision, ~90% recall).
- **Why:** The precision guarantee comes from the deterministic layers, not the model.
- **Source:** XBRLConceptLinking.md §0/§7

## C. Guards

#### XC-05 — Deterministic guards (G0/G1/G2)  `[LOCKED]`
- **Plain:** Before any LLM call, drop drivers that can't have an exact GAAP line — events/macro, ratios/derived, non-GAAP.
- **Rule:** Guards (pure Python, no LLM, ordered G2→G0→G1): **G0** = events/macro (resignation, buyback, oil_price, interest_rates, tariffs, weather…) · **G1** = ratios/derived/growth (margin, _growth, roic, ebitda, fcf, _per_square, _mix…) — tax_rate/effective_tax_rate are NOT here (real GAAP concepts) · **G2** = non-GAAP/adjusted — key on the **`measurement` set** (primary; since "adjusted"/"diluted" now live in `measurement`, not the name — reversal #2, per 09), keeping the name-prefix regex (adjusted_/non_gaap_/core_/organic_/pro_forma_) only as the **legacy-name fallback** for un-regenerated catalog names (e.g. old `adjusted_eps`). Guards are PRINCIPLES not a dict (mirror fact_type routing + GAAP/non-GAAP); prefer routing by fact_type, regex = raw-name fallback. Guarded drivers cost ZERO LLM calls.
- **Why:** Guards remove the no-concept pile for free and stop the model forcing a line where none exists.
- **Source:** XBRLConceptLinking.md §3.1

## D. The two prompts

#### XC-06 — The two prompts (kept loose)  `[LOCKED]`
- **Plain:** A PICK prompt (pick the exact concept or null) + a VERIFY prompt (strict auditor, defaults to "refuted" when unsure). Kept loose on purpose.
- **Rule:** PICK = "the ONE menu qname that IS exactly this metric, or null" (SAME metric only — cost-of-revenue≠revenue, subtotal≠total, basic≠diluted; two equal → higher usage). VERIFY = "STRICT auditor, default REFUTED when unsure; refute if related-but-different, GAAP vs non-GAAP, gross vs net, subtotal vs total, wrong statement, or a dimension instead of the consolidated line." Prompts are LOOSE (no exact-scope instruction) — scope is handled by the veto (XC-07), not by tightening the prompt (which costs recall). Parse default: no match ⇒ refuted.
- **Why:** Loose prompts preserve recall; the deterministic veto handles scope without a global recall cost.
- **Source:** XBRLConceptLinking.md §3.2

## E. Backstop + veto

#### XC-07 — The backstop + component-veto (deterministic)  `[LOCKED]`
- **Plain:** After the LLM verifies, a deterministic safety net can only ABSTAIN — never create/change a link. Fixes 4 known scope errors.
- **Rule:** Veto-only (can NEVER create a wrong link or change a correct one): **A** = a point-in-time share count must be `instant`, not a `duration` weighted-average · **B** = bare eps/share_count must not be the *Basic variant (convention = diluted) · **C** = a per-share metric must not map to a total-$ Cash concept · **D** = a 4-entry component-for-aggregate DENY set (a part ≠ the whole: sg_a→G&A, sg_a→S&M, operating_expenses→SG&A, total_debt→NotesPayable). Measured (274): A–C 42→18 wrong; +D → 1 wrong, NO recall cost. A no-op on a strong model.
- **Why:** The deterministic layer is the precision guarantee — removes scope errors without dropping correct links.
- **Source:** XBRLConceptLinking.md §3.3

#### XC-08 — Why the veto, not a prompt-rule  `[LOCKED]`
- **Plain:** Both a deterministic veto and a prompt instruction could fix scope errors — the veto wins (surgical, no recall cost).
- **Rule:** The veto and a prompt abstain-rule fix the same errors, but the veto is deterministic + surgical (1 wrong, no recall cost) while the prompt-rule is model-dependent (drifts) and quietly drops ~87 correct links globally (eps/capex/debt) to remove 1 wrong link — a bad trade on a recoverable link. Veto LOCKED; prompt-rule = documented alternative.
- **Why:** Sacrificing 87 correct links to remove 1 wrong one is the wrong trade on a recoverable enrichment link.
- **Source:** XBRLConceptLinking.md §0/§9

## F. The menu

#### XC-09 — The company menu (point-in-time)  `[LOCKED]`
- **Plain:** The menu = the consolidated numeric concepts the company actually reports; for a historical fact, only concepts available at the event date.
- **Rule:** menu = consolidated (no-segment) numeric concepts the company reports (`QUERY_2A`: latest 10-K + subsequent 10-K/10-Q, `is_numeric='1'`, empty `member_u_ids`). Carries {qname, label, period_type, balance, usage}; pass the WHOLE menu (don't pre-filter); ~150–530 concepts, LLM sees ~40 after guards. REQUIRED PIT cutoff for historical DriverUpdates: `r.created ≤ event_time` (latest 10-K ≤ T); live can use the latest 10-K. (Same cutoff as the slice menu, **FS-14** — both are PIT, resolved 2026-07-02.)
- **Why:** The answer is almost always a concept the company itself reports, so the menu IS the candidate set; PIT prevents look-ahead.
- **Source:** XBRLConceptLinking.md §4 · cross-ref FS-14

## G. Writing the link

#### XC-10 — Writing the link  `[LOCKED]`
- **Plain:** Store the concept's qname on the fact + create a MAPS_TO_CONCEPT edge; best-effort, self-healing.
- **Rule:** Store `DriverUpdate.xbrl_qname` (string, cross-taxonomy safe) AND `MERGE (du)-[:MAPS_TO_CONCEPT]->(con)` (MATCH by qname, `WITH…LIMIT 1` — a qname spans taxonomy years). Best-effort, non-blocking, idempotent, self-healing; no match → no edge, core write still succeeds. On the FACT, not the class.
- **Why:** An idempotent best-effort write means a missing/failed link never blocks the fact and self-heals.
- **Source:** XBRLConceptLinking.md §5

#### XC-11 — Subscription/OAuth, no API key  `[LOCKED]`
- **Plain:** The linker runs on the OAuth subscription, never a raw API key.
- **Rule:** Run via `claude_agent_sdk` with `cli_path="/home/faisal/.local/bin/claude"` (OAuth). Never pass/read `ANTHROPIC_API_KEY` (CLAUDE.md). Guards mean conceptless drivers cost ZERO LLM calls.
- **Why:** Subscription billing + guards keep cost near-zero.
- **Source:** XBRLConceptLinking.md §7 · CLAUDE.md billing rule

## H. fact_type routing

#### XC-12 — fact_type routing (all 4)  `[LOCKED]`
- **Plain:** metric → link it. guidance/surprise → don't link directly; inherit from the base metric. action_event → always abstain.
- **Rule:** metric → call `link()`. guidance/surprise → do NOT feed `<base>_guidance`/`<base>_surprise` to `link()` (it abstains on suffixed slugs by design, 96.6%); resolve the BASE metric's concept and INHERIT via `BASE_METRIC` (mandatory — else they silently get no link). action_event → ALWAYS abstain (G0 catches most names).
- **Why:** XBRL tags the underlying metric, not a forecast/surprise/action — so only the metric is matched.
- **Source:** XBRLConceptLinking.md §6 · cross-ref MF-10

## I. Evidence

#### XC-13 — Evidence (proof + re-validation)  `[EVIDENCE]`
- **Plain:** Proven twice: a 31-company build proof + a 274-company re-validation — 100% precision, zero wrong links.
- **Rule:** Build proof (`concept_link_probe/`, 31 guidance co, value-anchored + adversarial-panel key): 100% precision (0 wrong/249), 100% abstention (0/1,178), long-tail recall 99.4%; beat curated `concept_resolver.py` (21 leaks→0). Re-validation (`concept_link_revalidation/`, 274 co, 11 sectors, all 4 fact_types, NON-LLM ground truth): 100% precision / ~70% recall (guidance + non-guidance identical); 98.0% identical across 3 runs, 0 flips create a wrong link.
- **Source:** XBRLConceptLinking.md §9 · concept_link_probe/PROOF.md · concept_link_revalidation/VERDICT.md

#### XC-14 — The two error buckets  `[EVIDENCE]`
- **Plain:** Errors split two ways: model picked a worse concept that WAS in the menu (bucket 1), or NO exact concept existed and it approximated a part for the whole (bucket 2).
- **Rule:** Bucket 1 = model error (better concept was in the menu; shares_outstanding→WeightedAverage, eps→Basic) → backstop A–C. Bucket 2 = scope mismatch (no exact concept; sg_a→G&A, operating_expenses→SG&A) → veto D. Bucket 2 hits BOTH models (Opus's only 4 errors are bucket 2). Journey: Haiku 42 → backstop 18 → +veto D → 1.
- **Source:** XBRLConceptLinking.md §9

## J. Caveats + proper endpoint

#### XC-15 — Honest caveats on the "1 wrong"  `[EVIDENCE]`
- **Plain:** "1 wrong" is only on the 274 tuning companies; the 4-entry deny-set is a hand list, not a rule.
- **Rule:** (1) "1 wrong" is the TUNING-SET number — new part-for-whole pairs slip through on the other 521 companies + future filings until added (the residual `CCL cost_of_revenue→OperatingCostsAndExpenses` already shows the list is incomplete). (2) The deny-set is pattern-matched, not principled (denies `total_debt→NotesPayable` but keeps `total_debt→LongTermDebt` — same shape, opposite treatment). (3) The monitor does NOT catch new bucket-2 slips (same balance/period). (4) Coverage ≈ 35% of 795 — representative, but a full-universe run is pending.
- **Source:** XBRLConceptLinking.md §0/§9

#### XC-16 — The proper endpoint (calc-hierarchy veto)  `⏳ RECOMMENDED (before full rollout)`
- **Plain:** Before running all 795 companies, replace the hand 4-entry deny-list with the official us-gaap calculation hierarchy — a general, no-list veto.
- **Rule:** Replace the hand DENY set with the us-gaap CALCULATION LINKBASE (official parent/child structure): "the model picked a CHILD component of the metric's canonical concept" → veto — general (catches unseen pairs), deterministic, needs no list. The 4-entry list is the pragmatic lock for now; build the hierarchy veto before the full-universe rollout (or when the list needs additions).
- **Why:** Only the hierarchy makes bucket-2 both provable AND general — the hand list can't.
- **Source:** XBRLConceptLinking.md §9 · also in `90_OpenItems.md`

## K. Monitoring + scale

#### XC-17 — Monitoring  `[LOCKED]`
- **Plain:** A cheap non-LLM alarm: check the picked concept's balance/period vs what the metric should be; sample + audit.
- **Rule:** Sample emitted links, check the concept's balance/period_type vs the metric's expected signature (revenue = credit+duration; shares_outstanding = instant; eps = per-share); a contradiction = a wrong link. Track abstention by fact_type (conceptless ~100%). LIMIT: catches STRUCTURAL (bucket-1) slips only — NOT new SCOPE (bucket-2) mismatches (same balance/period) → need XC-16 or a periodic audit. Optional stability gate: run 2–3×, abstain on disagreement (~2% flips, all borderline, never create a wrong link).
- **Source:** XBRLConceptLinking.md §10

#### XC-18 — Production scale  `[LOCKED]`
- **Plain:** Resolve once per (company, base-metric driver) + store; batch one call/company; add a cache only if volume bites.
- **Rule:** Resolve `link()` once per (company, distinct base-metric driver) and store; re-runs self-heal. Batch one LLM call per company (~40 non-guarded metrics). At 796-co scale, OPTIONALLY cache an LLM metric→us-gaap-family map + intersect with each menu, calling the LLM only on ambiguous intersections (same precision, fewer calls). Per-company pick is simplest + proven; adopt the cache only if volume bites.
- **Source:** XBRLConceptLinking.md §11
