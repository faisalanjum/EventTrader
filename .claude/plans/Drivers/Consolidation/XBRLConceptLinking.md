# XBRL Concept Linking — production spec (self-contained)

**Audience:** an engineer/bot with ZERO prior context. This is everything needed to build the
DriverUpdate → XBRL Concept linker for production. Read top to bottom; nothing else required.

---

## 0. TL;DR — the locked recipe

**Goal:** attach the one exact XBRL concept a company reports for a driver (`revenue` →
`us-gaap:RevenueFromContractWithCustomer…`), or attach **nothing**. It is an **enrichment** link:
recoverable, never identity; a *missing* link is harmless, a *wrong* link is the only real failure.

**The pipeline (per driver):**
```
GUARD (drop ratios/ebitda/fcf/growth/events/macro/non-GAAP)   ← deterministic, no model
  → build company MENU (the concepts it actually reports)
  → LLM PICK one menu concept (or null)
  → in-menu check (no hallucinated concepts)
  → LLM VERIFY (adversarial: try to refute the pick) → refuted/unsure ⇒ abstain
  → STRUCTURAL BACKSTOP + component-veto (deterministic) → emit qname, else abstain
```

**Model:** **Haiku** (cheapest). The structure + two **deterministic** fixes make Haiku match/beat a
top model on precision at ~one cheap model's cost.

**Scorecard (274-company validation, non-LLM ground truth, strict wrong-count):**

| Strategy | Wrong | Recall | Conceptless abstention | Cost |
|---|---|---|---|---|
| All-Haiku, no fixes | 42 | 93.9% | 100% | cheap |
| Haiku + backstop | 18 | 93.7% | 100% | cheap |
| **Haiku + backstop + component-veto (LOCKED)** | **1** | **93.7%** | **100%** | **cheap** |
| Haiku + backstop + prompt abstain-rule (alternative) | 2 | 92.2% | 100% | cheap |
| All-Opus (alternative) | 4 | 93.6% | 100% | expensive |
| Split: Haiku-pick + Opus-verify (alternative) | 2 | 90.5% | 100% | mid |

**Why the veto, not the prompt-rule:** both fix the same scope errors, but the veto is **deterministic
and surgical** — 1 wrong, no recall cost. The prompt abstain-rule is model-dependent (can drift) and
**quietly drops 87 correct links globally** (eps/capex/debt) to avoid 1 wrong link — a bad trade on a
recoverable link. So the veto is locked; the prompt-rule is kept only as a documented alternative.

**Read this honestly (3 caveats):**
1. Validated on **272/274 ≈ 35% of the 795-company universe** — representative (all 11 sectors,
   guidance + non-guidance), so it generalizes, but a **full-universe run is still pending**.
2. The locked fixes (backstop + veto) are **deterministic** → no drift, no global recall cost. The
   only model-dependent part is the LLM pick/verify itself (Haiku); the deterministic layers are the
   precision guarantee.
3. **"1 wrong" is the tuning-set number.** The veto's 4-entry list is calibrated to the errors seen on
   these 274 companies — ~static accounting facts (a part ≠ the whole), not per-company upkeep, and a
   miss fails gracefully (one borderline link, never a systematic hole). BUT on held-out / the other
   521 companies, **new part-for-whole pairs will slip through until added**, and the structural
   monitor won't catch them (same balance/period). The general, deterministic fix is the data-driven
   us-gaap **calculation-hierarchy** veto (§9) — recommended before the full-universe rollout.

---

## 1. What & why (plain words)

A **Driver** is a named cause of a stock move (`revenue`, `capex`, `oil_price`, `ceo_resignation`).
Some map to a real reported XBRL line; many don't (`oil_price`, `gross_margin`, `ebitda`,
`ceo_resignation`). The link is **company-scoped** — the same metric is a different qname per company
(Apple `RevenueFromContractWithCustomerExcludingAssessedTax`; a utility
`RegulatedAndUnregulatedOperatingRevenue`; an MLP `…PerOutstandingLimitedPartnershipUnit`). The answer
is almost always a concept the company **itself reports**, so the model picks from that company's own
reported concepts ("the menu"). **Value is NOT used at inference.**

## 2. Why it's built this way (rejected alternatives — all tested)

| Rejected | Why it fails |
|---|---|
| Match by the reported **number** (value+period anchoring) | Dense fact space → some wrong concept always sits near any value by chance; right vs wrong indistinguishable. (Value-anchoring is used ONLY offline, to build the test answer key.) |
| Match by **string/token** similarity | "revenue" is inside "**cost of** revenue" → inverts meaning. |
| **Curated dictionary** metric→concept | Endless human upkeep; misses company-specific & extension concepts. |
| **Multi-method agreement** (numbers ∧ strings) | The two can agree on the *same* wrong answer (correlated failure). |

**What holds:** deterministic guards + LLM picks from the company's own menu by meaning + an
independent adversarial verify + a deterministic structural backstop. The only "knowledge" is each
company's reported concept labels (the taxonomy *as data*) — no curated matcher dict.

---

## 3. The algorithm — exact and reproducible

`link()` is the whole inference. **Value is withheld.**

### 3.1 Deterministic guards (pure Python, no LLM)

```python
import re
# G0 — events / macro-exogenous causes (in production: fact_type == action_event / exogenous).
G0 = re.compile(r"(resignation|appointment|acquisition_announcement|buyback_authoriz|"
                r"share_buyback|repurchase_authoriz|dividend_initiation|stock_split|downgrade|"
                r"upgrade|litigation|settlement|recall|breach|closure|strike|approval|"
                r"contract_award|refinanc|^oil_price|gas_price|interest_rates?$|exchange_impact|"
                r"commodity_costs?$|^inflation$|^tariffs?$|weather|freight_costs?$)")
# G1 — ratios / derived / growth (no exact GAAP line). NB tax_rate/effective_tax_rate are NOT here
#       (us-gaap:EffectiveIncomeTaxRate… is a real concept).
G1 = re.compile(r"(margin$|_margin|_growth|_yoy|_change$|_ratio$|^roic$|^roe$|^roa$|^roce$|"
                r"^ebitda|_ebitda|^fcf$|free_cash_flow|_per_square|_penetration|_mix$|_turns$)")
# G2 — non-GAAP / adjusted (value ≠ the GAAP concept's fact; base metric carries it via BASE_METRIC).
G2 = re.compile(r"^(adjusted_|non_gaap_|underlying_|core_|organic_|pro_forma_)")

def guard(slug):
    s = (slug or "").lower()
    if G2.match(s):   return "G2_nongaap"
    if G0.search(s):  return "G0_event_macro"
    if G1.search(s):  return "G1_derived_ratio"
    return None
```
Guards are **principles, not a dict** — they mirror the schema's `fact_type` routing + the
GAAP/non-GAAP rule. In production prefer routing by the driver's `fact_type`; the regexes are the
fallback for raw names.

### 3.2 The two LLM prompts (verbatim — matches `concept_linker.py`)

```python
PICK_PROMPT = """You are a precise XBRL concept matcher. Company {ticker}.
Menu (the ONLY allowed answers): {menu}
Metric: "{slug}"
Pick the ONE menu qname that IS exactly this metric (the same accounting line a filer tags), or null.
SAME metric only — a related-but-different line is NOT a match (cost-of-revenue≠revenue;
income-tax≠net-income; a subtotal≠the total; basic≠diluted). Two equal candidates → higher usage.
Output JSON: {{"qname": "us-gaap:..." or null}}"""

VERIFY_PROMPT = """STRICT XBRL link auditor — default to refuted when unsure (a wrong link is the
cardinal sin). Company {ticker}. Proposed: metric "{slug}" -> {qname} (label: "{label}").
Refute if the concept is a related-but-different line, a different value (GAAP vs non-GAAP, gross
vs net, subtotal vs total), the wrong statement, or a dimension instead of the consolidated line.
Output JSON: {{"real": true|false}}"""
```
`{menu}` = `"; ".join(f'{qname}|{label}')` over the menu rows. These are the original prompts (no
exact-scope instruction) — the scope-mismatch errors are handled deterministically by the §3.3 veto,
NOT by tightening the prompt (which would cost recall globally — §9). The prompt-level abstain-rule is
documented as an alternative in §9.

### 3.3 The structural backstop + component-veto (deterministic, always-on)

Veto-only → abstain; it can NEVER create a wrong link or change a correct one. Uses facts already in
the graph + a 4-entry static "a part ≠ the whole" set.

```python
INSTANT_STOCK = re.compile(r"shares_outstanding|shares_issued")
PERSHARE      = re.compile(r"per_share$|^eps$|dividend_per_share")
# component-for-aggregate mismatches: a part is NOT the whole (fixed accounting facts, ~static)
DENY = {("sg_a", "GeneralAndAdministrativeExpense"), ("sg_a", "SellingAndMarketingExpense"),
        ("operating_expenses", "SellingGeneralAndAdministrativeExpense"), ("total_debt", "NotesPayable")}

def backstop_ok(slug, qname, concept):     # concept = the menu row {period_type, ...}; False ⇒ abstain
    ln = qname.split(":")[-1]
    # A — a point-in-time share count must be `instant`, never a `duration` weighted-average.
    if INSTANT_STOCK.search(slug) and concept.get("period_type") == "duration":   return False
    # B — bare eps/share_count must not be the *Basic variant (convention = diluted).
    if slug in ("eps", "share_count", "shares") and "Basic" in ln:                 return False
    # C — a per-share metric must not map to a total-$ concept (e.g. DividendsCommonStockCash).
    if PERSHARE.search(slug) and "PerShare" not in ln and "Cash" in ln:           return False
    # D — component-for-aggregate veto (a part is not the whole). THE bucket-2 fix (§9).
    if (slug, ln) in DENY:                                                         return False
    return True
```
Measured (274 cohort): backstop A–C takes Haiku **42 → 18 wrong**; adding veto D → **1 wrong**, with
**no recall cost** (93.7% unchanged) — it only removes wrong links. A no-op on a strong model.

### 3.4 `link()` — the whole inference

```python
def _parse_qname(txt):
    m = re.search(r'"qname"\s*:\s*"([^"]+)"', txt or ""); return m.group(1) if m else None
def _parse_real(txt):
    m = re.search(r'"real"\s*:\s*(true|false)', (txt or "").lower())
    return m.group(1) == "true" if m else False                  # default = refuted

def link(ticker, slug, menu, llm):
    """menu = [{"qname","label","usage","period_type",...}]; llm = callable(str)->str. Returns qname or None."""
    if guard(slug):
        return None
    menu_str = "; ".join(f'{c["qname"]}|{c.get("label","")}' for c in menu)
    pick = _parse_qname(llm(PICK_PROMPT.format(ticker=ticker, slug=slug, menu=menu_str)))
    if not pick:
        return None
    concept = next((c for c in menu if c["qname"] == pick), None)
    if concept is None:                                          # never emit a hallucinated concept
        return None
    real = _parse_real(llm(VERIFY_PROMPT.format(ticker=ticker, slug=slug, qname=pick,
                                                label=concept.get("label", ""))))
    if not real:
        return None
    if not backstop_ok(slug, pick, concept):                     # deterministic safety net + veto
        return None
    return pick
```

---

## 4. Building the company menu (Cypher, read-only)

The menu = the consolidated (no-segment) numeric concepts the company reports. Base query
(`QUERY_2A`, from the guidance pipeline):

```cypher
MATCH (rk:Report)-[:PRIMARY_FILER]->(c:Company {ticker: $ticker})
WHERE rk.formType = '10-K'
WITH c, rk ORDER BY rk.created DESC LIMIT 1
WITH c, rk.created AS last_10k_date
MATCH (f:Fact)-[:HAS_CONCEPT]->(con:Concept)
MATCH (f)-[:IN_CONTEXT]->(ctx:Context)-[:FOR_COMPANY]->(c)
MATCH (f)-[:REPORTS]->(:XBRLNode)<-[:HAS_XBRL]-(r:Report)-[:PRIMARY_FILER]->(c)
WHERE r.formType IN ['10-K','10-Q'] AND r.created >= last_10k_date AND f.is_numeric = '1'
  AND (ctx.member_u_ids IS NULL OR ctx.member_u_ids = [])
WITH con.qname AS qname, con.label AS label, con.period_type AS period_type,
     con.balance AS balance, count(f) AS usage
ORDER BY usage DESC
RETURN qname, label, period_type, balance, usage
```

- `Concept` carries `{qname, label, balance, type_local, period_type}` — `period_type`/`balance` feed
  the backstop and monitoring. Pass the whole menu to the LLM (don't pre-filter). Top-level facts have
  empty `ctx.member_u_ids` (segment facts excluded — member/slice is a separate, solved problem).
  Typical menu = 150–530 concepts.
- **⚠️ REQUIRED for historical DriverUpdates — point-in-time cutoff.** The query uses the *latest*
  10-K. For a DriverUpdate at event time `T`, add `AND r.created <= $event_time` (and pick the latest
  10-K with `rk.created <= $event_time`) so the menu reflects only data available at `T` — no
  look-ahead. Same PIT rule as `Naming_Slices_XBRL.md` §7. Live resolution can use the latest 10-K.

## 5. Writing the link (per-company, best-effort)

Store the `xbrl_qname` string AND create the edge, exactly like the guidance pipeline does for
`GuidanceUpdate` (the working reference):

```cypher
// DriverUpdate.xbrl_qname = $xbrl_qname  (string, cross-taxonomy safe), then the edge (0..1):
MATCH (du:DriverUpdate {id: $driver_update_id})
MATCH (con:Concept {qname: $xbrl_qname})
WITH du, con LIMIT 1                       // a qname can exist across taxonomy years
MERGE (du)-[:MAPS_TO_CONCEPT]->(con)
RETURN con.qname AS linked_qname
```
Best-effort, non-blocking, idempotent (`MERGE`), self-healing. No `Concept` match → no edge, core
write still succeeds. (Per `Naming_Slices_XBRL.md` §9 the link attaches to the **DriverUpdate** fact,
not the Driver class — enrichment, never identity.)

## 6. fact_type routing (all 4 — REQUIRED)

| fact_type | what to do |
|---|---|
| **metric** | call `link(company, name, menu, llm)`. |
| **guidance / surprise** | **Do NOT feed `<base>_guidance`/`<base>_surprise` to `link()` — it abstains on suffixed slugs by design (validated 96.6% abstain).** Resolve the **base metric** Driver's concept and **inherit** it via the `BASE_METRIC` edge (the schema mandates `<x>_guidance -[:BASE_METRIC]-> <x>`). **Mandatory** — else these silently get no link. |
| **action_event** | **always abstain** (no concept; G0 catches most names). |

## 7. Model & LLM wiring

- **Use Haiku** (the locked cheap path — §0). Drop-in alternatives: **Opus/Sonnet** for ~similar
  precision at higher cost; the **split** (Haiku-pick + Opus-verify) for Opus-grade precision but
  ~90% recall (its cost saving is real in production but masked in an agent harness by per-agent
  overhead — measure with direct SDK calls).
- **Subscription, NO API key.** `claude_agent_sdk` with `ClaudeAgentOptions(cli_path=
  "/home/faisal/.local/bin/claude")` (OAuth). Never pass/read `ANTHROPIC_API_KEY` (see CLAUDE.md).
  Guards mean conceptless drivers cost **zero** LLM calls.

---

## 8. Locked design decisions

1. **Value-withheld inference** (value-anchoring is offline GT only).
2. **Guards = principles, not a dict** (fact_type routing + GAAP/non-GAAP). `tax_rate` allowed.
3. **Menu-restricted pick + adversarial verify + deterministic backstop/veto.** Unsure ⇒ abstain.
4. **In-menu check** — never emit a concept the company doesn't report.
5. **Company-extension / industry / MLP concepts are expected and correct.**
6. **Bare `eps`/`share_count` → diluted** (backstop rule B enforces it).
7. **Scope mismatches (a part ≠ the whole) are vetoed deterministically** (backstop rule D), NOT by a
   prompt instruction — the veto is surgical (no global recall cost) and provable. (The prompt
   abstain-rule is the documented alternative, §9.)
8. **non-GAAP/adjusted abstain** (G2); base metric carries the concept via `BASE_METRIC`.
9. **DON'T rename `sg_a`.** Disproven against the cached menus: `sg_a → SellingGeneralAndAdministrative
   Expense` is correct on ~145 companies; the only failures are companies with **no combined SG&A
   concept** (e.g. BLMN = `[CostsAndExpenses, GeneralAndAdministrativeExpense]`) → the right answer
   there is **abstain**, handled by veto rule D — not a rename, not a bigger model.

---

## 9. Proof, model-robustness, and the two error buckets

**Build proof** (`concept_link_probe/`, 31 guidance companies, value-anchored + adversarial-panel key):
precision 100% (0 wrong / 249 links), abstention 100% (0/1,178), long-tail recall 99.4%
(0 wrong / 1,395 self-labeled). Beat the curated `concept_resolver.py` baseline (195 links, 21 leaks).

**Re-validation** (`concept_link_revalidation/`, **274 companies**, 11 sectors, 31 guidance + 243
non-guidance, all 4 fact_types, **non-LLM** ground truth = canonical us-gaap families + balance/period
structure, cardinal wrong-link detected deterministically): guidance 100% precision / 71% recall ·
**non-guidance 100% / 70%** (identical). Stability: **98.0% identical across 3 runs**; 0 flips create
a wrong link.

**Model robustness (the core finding).** Same algorithm, weak model (Haiku) vs strong (Opus). The
errors split cleanly into two buckets:

| Bucket | meaning | Opus | Haiku (raw) | fix |
|---|---|---|---|---|
| **1 — model error** | a better concept WAS in the menu, model picked worse (`shares_outstanding→WeightedAverage`, `eps→Basic`, `dividend→total-$`) | 0 | ~15 | **backstop A–C** (deterministic) |
| **2 — scope mismatch** | NO exact concept existed, model approximated a part for the whole (`sg_a→G&A`, `operating_expenses→SG&A`) | 4 | ~27 | **veto D** (deterministic) — or the prompt-rule alternative |

Bucket 2 happens in **both** models (Opus's only 4 errors are bucket 2) — so it's neither model
strength nor naming. **Journey: Haiku 42 → backstop → 18 → + veto D → 1 wrong (on the tuning set).**
The 1 residual is **`CCL cost_of_revenue → OperatingCostsAndExpenses`** — itself a part-for-whole
mismatch the 4-entry deny-set does NOT cover (a *narrower* metric mapped to a *broader* aggregate),
which already shows the list is incomplete even on the data it was built from.

**The bucket-2 fix — veto (locked) vs prompt-rule (alternative), measured:**

| approach | wrong | recall | reliability |
|---|---|---|---|
| **deterministic veto D (LOCKED)** | **1** | **93.7%** | deterministic, surgical |
| prompt abstain-rule (alternative) | 2 | 92.2% | model-dependent; **−87 correct links globally** |

The prompt abstain-rule (add "abstain if no exact-scope concept; never approximate to a narrower
component or broader aggregate" to PICK+VERIFY) is **general** — it can catch unseen mismatches with no
list — but it lives in the shared prompt, so it makes Haiku more conservative on **every** metric:
measured **−87 correct links** across 13 metrics (`interest_expense −24, eps −21, capex −16,
total_debt −16`) to remove 1 wrong link. That's a bad trade on a recoverable enrichment link, and it
can drift. **Use the veto.** Keep the prompt-rule documented only as a fallback for an
instruction-following model if the veto list ever feels too narrow.

**Honest caveats on the veto (do NOT read "1 wrong" as the general precision):**
1. **"1 wrong" is the tuning-set number.** The deny-set was calibrated to the errors seen on these
   274 companies — a list is blind to what it hasn't seen. On the other **521 companies + future
   filings, new part-for-whole pairs will slip through** until added (and the residual above —
   `cost_of_revenue→OperatingCostsAndExpenses` — proves the list is already incomplete on the tuning
   set). So real-world confirmed-wrong sits **a touch above 1** until the list grows. The prompt-rule,
   being a general instruction, would catch these unseen mismatches automatically — **the one thing
   it is genuinely better at** (at its 87-link recall cost).
2. **The deny-set is pattern-matched, not principled.** It denies `total_debt→NotesPayable` but
   **keeps `total_debt→LongTermDebt` (10 companies)** — structurally the same shape ("total ≠ one
   component"), treated two opposite ways. (LongTermDebt landed in the canonical GT family, so it
   reads as "correct"; that's also where part of the veto's recall edge comes from.) Two identical
   shapes handled differently = the list reflects observed errors, not a rule.
3. **The structural monitor (§10) does NOT catch new bucket-2 slips** — a part-for-whole mismatch has
   the *same* balance/period as the right concept (that's why it's hard), so an unseen one persists
   silently until found by audit. Bucket-1 (structural) slips it does catch.
4. Coverage 272/274 ≈ **35% of 795** — representative, generalizes, but a full-universe run is pending.

**The proper endpoint — data-driven hierarchy (recommended, not just "if the list grows").** Because
of caveats 1–3, the principled fix is to replace the hand `DENY` set with the us-gaap **calculation
linkbase**: it gives the official parent/child structure, so "the model picked a **child component**
of the metric's canonical concept" → veto — **general (catches unseen pairs), deterministic, and
needs no list**. It's the only way to make bucket-2 *both* provable *and* general. The 4-entry list is
the pragmatic lock for the known vocabulary; build the hierarchy before the full-universe rollout (or
when the list starts needing additions).

**Net (unchanged decision):** for a recoverable enrichment link the veto still wins — fewer
confirmed-wrong (1 vs 2 on tuning), full clean-metric recall (93.7%), deterministic, no drift. The
caveats just keep it honest: it's near-100% **on seen data**, with a known generalization gap that the
hierarchy closes.

## 10. Residual risks & monitoring

- **BASE_METRIC inheritance** must be wired for guidance/surprise (§6) or they silently get no link.
- **Conceptless abstention is model-robust (100%)** — the deterministic guards carry it.
- **Monitoring (cheapest non-LLM wrong-link alarm):** sample emitted links, check the picked concept's
  `balance`/`period_type` against the metric's expected signature (revenue = credit+duration,
  shares_outstanding = instant, eps = per-share); a contradiction is a wrong link. Track abstention
  rate by fact_type (conceptless must stay ~100%). **Limit:** this catches *structural* (bucket-1)
  slips only — it does NOT catch new *scope* (bucket-2) mismatches like `sg_a→G&A` (same
  balance/period). Those need the §9 calc-hierarchy veto or a periodic audit.
- **Stability gate (optional):** run `link()` 2–3× and abstain on disagreement (flips ~2%, all on
  borderline cells, never create a wrong link).

## 11. Production scale

Resolve `link()` once per **(company, distinct base-metric driver)** and store; re-runs self-heal.
Batch one call per company (the LLM only sees ~40 non-guarded metrics; guards remove the rest free).
At full 796-company scale, optionally cache an LLM-generated `metric → candidate us-gaap family` map
once and intersect with each menu, calling the LLM only on ambiguous intersections — same precision,
fewer calls. Per-company LLM-pick is simplest and proven; adopt the cache only if volume bites.

## 12. Reference implementation & evidence

- Code: `plans/Drivers/WIP/concept_link_probe/concept_linker.py` (`link/guard/demo`). §3.1/§3.2/§3.4
  are this module verbatim; **add the §3.3 backstop+veto** (validated in `concept_link_revalidation/
  struct_backstop_experiment.py`). (Folder sits at a stray top-level `plans/`; relocate under
  `.claude/` when convenient — cosmetic, paths still resolve.)
- Build: `concept_link_probe/ALGORITHM.md · PROOF.md · ATTEMPTS.md`.
- Re-validation: `concept_link_revalidation/REVALIDATION.md · FAILURES.md · VERDICT.md` + harness.
- All evidence reproducible: read-only Neo4j; ground truth built with zero human labels.
