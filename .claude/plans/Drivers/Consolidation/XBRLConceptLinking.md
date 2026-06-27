# XBRL Concept Linking — production spec (self-contained)

**Audience:** an engineer/bot with ZERO prior context. This document is everything needed to build
the DriverUpdate → XBRL Concept linker for production. Read top to bottom; nothing else required.

> **⚠️ CORRECTIONS PENDING (2026-06-27 — from a cross-check of this doc vs the code + the run-of-record `VERDICT.md`). Resolve before treating this as "locked":**
> 1. **Stability is preliminary.** §9 shows flip-rate ≈0.66%, but that is the **2-run** figure; `concept_link_revalidation/VERDICT.md` still says STABILITY = **PENDING (runs 2–3)**. Treat 0.66% as provisional; finalize with the 3-run number.
> 2. **The menu query (§4) is NOT point-in-time** — this contradicts `Naming_Slices_XBRL.md` §7. `QUERY_2A` uses the *latest* 10-K with no `r.created <= $event_date` cutoff → lookahead on historical DriverUpdates. Add the event-date cutoff before production.
> 3. **Borderline scope-mismatches are KEPT, not abstained** (`sg_a→GeneralAndAdministrativeExpense` ×4, `total_debt→NotesPayable` ×1) — counted "defensible," so "0 wrong" includes them. Owner decision: keep, or abstain (cleaner). The §8.10 stability gate is optional and won't auto-abstain them.
> 4. **Coverage = 274 / 795** (representative: 11 sectors, 31 guidance + 243 non-guidance) — NOT the full universe; stability is on this cohort only.
> 5. **Code lives at a stray top-level `plans/Drivers/WIP/concept_link_probe/`** (not under `.claude/`); §9/§12 paths point there. Relocate into `.claude/` and fix the paths.
>
> Verified correct: **§3 matches `concept_linker.py` line-for-line**, and **all locked rules are present**.

---

## 1. What this does (plain words)

A **Driver** is a named cause of a stock move — e.g. `revenue`, `capex`, `oil_price`,
`ceo_resignation`. Some drivers correspond to a real financial line a company reports in XBRL
(`revenue` → the company's `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` fact).
Many do not (`oil_price`, `ceo_resignation`, `gross_margin`, `ebitda`).

**Job:** given a driver for a company, attach the **one exact XBRL Concept** that company reports for
it — or attach **nothing** (abstain). The link is **enrichment**: it is never the driver's identity,
it is recoverable, and a missing link is harmless. A **wrong** link is the only real failure.

```
(company, driver_name)  ──►  exact us-gaap concept qname   (e.g. us-gaap:Revenues)
                        ──►  or ABSTAIN (no concept exists / unsure)
```

The link is **company-scoped**: the same metric maps to a different qname per company (Apple uses
`RevenueFromContractWithCustomerExcludingAssessedTax`, a utility uses
`RegulatedAndUnregulatedOperatingRevenue`). The answer is almost always a concept the company itself
reports — so we let the model pick from that company's **own reported concepts** ("the menu").

---

## 2. The core idea (why it is built this way)

Three things were tried and **rejected** (each empirically — see the WIP probe folders):

| Rejected approach | Why it fails |
|---|---|
| Match by the reported **number** (value+period anchoring) | Hundreds of facts per period → some wrong concept always sits near any value by chance; right vs wrong are indistinguishable by tolerance. (Use value-anchoring only OFFLINE, to build the test answer key — never at inference.) |
| Match by **string/token** similarity of names | "revenue" is a substring of "**cost of** revenue" → inverts the meaning. |
| **Curated dictionary** of metric→concept | Needs endless human upkeep; only covers listed labels; can't do company-specific or extension concepts. |

**The design that holds:** deterministic **guards** drop the kinds of metrics that have no exact
concept, then an **LLM picks the one matching concept from the company's own menu** by meaning, then
an **independent adversarial check tries to prove the pick wrong**. Link only what survives; abstain
otherwise. The only "knowledge" is each company's reported concept labels (the taxonomy *as data*) +
general semantics — no curated dict.

```
driver (company, name)            value is NOT used at inference
       │
       ▼
  GUARD ──abstain if──► ratio/margin/ebitda/fcf/*_growth · event/action · macro · non-GAAP(adjusted_/non_gaap_)
       │ (else)
       ▼
  build company MENU = concepts it actually reports {qname,label,usage}   (Cypher in §4)
       ▼
  LLM-PICK  → the ONE menu qname that IS this metric, or null
       ▼
  in-menu check (reject hallucinated qnames)
       ▼
  ADVERSARIAL VERIFY  → independent LLM tries to refute; refuted/unsure → abstain
       ▼
  emit qname  ·  else abstain
```

---

## 3. The algorithm — exact and reproducible

This is the literal contract. `link()` is the entire inference. **Value is withheld** (not an input).

### 3.1 Deterministic guards (pure Python, no LLM)

```python
import re

# G0 — events / macro-exogenous causes (in production these are fact_type == action_event, or an
# exogenous cause). No company line item IS the event.
G0 = re.compile(r"(resignation|appointment|acquisition_announcement|buyback_authoriz|"
                r"share_buyback|repurchase_authoriz|dividend_initiation|stock_split|downgrade|"
                r"upgrade|litigation|settlement|recall|breach|closure|strike|approval|"
                r"contract_award|refinanc|^oil_price|gas_price|interest_rates?$|exchange_impact|"
                r"commodity_costs?$|^inflation$|^tariffs?$|weather|freight_costs?$)")
# G1 — ratios / derived / growth. No exact GAAP line concept (a $ subtotal is a DIFFERENT metric).
# NB: effective/tax_rate is deliberately NOT here (us-gaap:EffectiveIncomeTaxRate… is a real concept).
G1 = re.compile(r"(margin$|_margin|_growth|_yoy|_change$|_ratio$|^roic$|^roe$|^roa$|^roce$|"
                r"^ebitda|_ebitda|^fcf$|free_cash_flow|_per_square|_penetration|_mix$|_turns$)")
# G2 — non-GAAP / adjusted. The adjusted value ≠ the GAAP concept's fact; the base metric carries
# the concept via BASE_METRIC.
G2 = re.compile(r"^(adjusted_|non_gaap_|underlying_|core_|organic_|pro_forma_)")

def guard(slug):
    """Return the guard name that abstains this slug, or None to proceed to the LLM."""
    s = (slug or "").lower()
    if G2.match(s):   return "G2_nongaap"
    if G0.search(s):  return "G0_event_macro"
    if G1.search(s):  return "G1_derived_ratio"
    return None
```

The guards are **principles, not a dictionary**: G0/G1/G2 mirror the schema's `fact_type` routing
(action_event/exogenous have no concept; ratios/derived have no exact GAAP line) and the GAAP/non-GAAP
rule. In production, prefer routing by the driver's `fact_type` where available; the regexes are the
fallback for raw names.

### 3.2 The two LLM prompts (verbatim — do not paraphrase)

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

`{menu}` is built as `"; ".join(f'{qname}|{label}')` over the menu rows.

### 3.3 The link function (the whole inference)

```python
def _parse_qname(txt):
    m = re.search(r'"qname"\s*:\s*"([^"]+)"', txt or "")
    return m.group(1) if m else None

def _parse_real(txt):
    m = re.search(r'"real"\s*:\s*(true|false)', (txt or "").lower())
    return m.group(1) == "true" if m else False        # default = refuted

def link(ticker, slug, menu, llm):
    """menu = [{"qname","label","usage"}]; llm = callable(prompt:str)->str. Returns qname or None."""
    if guard(slug):
        return None
    menu_str = "; ".join(f'{c["qname"]}|{c.get("label","")}' for c in menu)
    pick = _parse_qname(llm(PICK_PROMPT.format(ticker=ticker, slug=slug, menu=menu_str)))
    if not pick:
        return None
    if pick not in {c["qname"] for c in menu}:          # never emit a hallucinated concept
        return None
    label = next((c.get("label") for c in menu if c["qname"] == pick), "")
    real = _parse_real(llm(VERIFY_PROMPT.format(ticker=ticker, slug=slug, qname=pick, label=label)))
    return pick if real else None
```

That is the complete algorithm. Everything below is wiring, the graph, decisions, and proof.

---

## 4. Building the company menu (Cypher, read-only)

The menu = the consolidated (no-segment) numeric concepts the company has reported since its latest
10-K. This is the production `QUERY_2A` (verbatim — keep identical):

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
WITH con.qname AS qname, con.label AS label, count(f) AS usage
ORDER BY usage DESC
RETURN qname, label, usage
```

Graph shape used: `(Report)-[:PRIMARY_FILER]->(Company)`, `(Fact)-[:HAS_CONCEPT]->(Concept)`,
`(Fact)-[:IN_CONTEXT]->(Context)-[:FOR_COMPANY]->(Company)`,
`(Fact)-[:REPORTS]->(XBRLNode)<-[:HAS_XBRL]-(Report)`. `Concept` carries `{qname, label, balance,
type_local, period_type}`. Top-level facts have empty `ctx.member_u_ids` (segment facts are excluded
— the member/slice side is a separate, already-solved problem).

A typical menu is 150–530 concepts. Pass it whole to the LLM (do not pre-filter — that risks dropping
the answer). This is the SAME menu the guidance pipeline warms into `/tmp/concept_cache_{ticker}.json`.

---

## 5. Writing the link to the graph (per-company, best-effort)

The concept is company-scoped, so the link lives where the per-company answer lives — store the
`xbrl_qname` as a property AND create the edge, exactly like the guidance pipeline does for
`GuidanceUpdate` (the working reference pattern). For Drivers this attaches per the resolved
company-scoped fact (DriverUpdate-level, or a per-(Driver,company) record — see schema §9 note):

```cypher
// store the string (cross-taxonomy safe) on the node, e.g. DriverUpdate.xbrl_qname = $xbrl_qname
// then the edge (0..1), LIMIT 1 because a qname can exist across taxonomy years:
MATCH (du:DriverUpdate {id: $driver_update_id})
MATCH (con:Concept {qname: $xbrl_qname})
WITH du, con LIMIT 1
MERGE (du)-[:MAPS_TO_CONCEPT]->(con)
RETURN con.qname AS linked_qname
```

Rules (same discipline as guidance):
- **Best-effort, non-blocking, self-healing.** If the qname matches no `Concept` node, the MATCH
  fails → no edge → the core write still succeeds; a re-run repairs it.
- **Never gate on `was_created`** — keep it idempotent (`MERGE`) so transient failures self-heal.
- Store BOTH the `xbrl_qname` property (the string, survives taxonomy drift) and the edge.

---

## 6. fact_type routing (all 4 — REQUIRED)

`link()` only handles the `metric` case directly. Route by the driver's `fact_type`:

| fact_type | what to do |
|---|---|
| **metric** | call `link(company, name, menu, llm)`. |
| **guidance** / **surprise** | **Do NOT feed `<base>_guidance` / `<base>_surprise` to `link()` — it abstains on suffixed slugs by design (validated: 96.6% abstain).** Resolve the **base metric** Driver's concept (the `BASE_METRIC` edge points to it) and **inherit** that qname. The schema already mandates `<x>_guidance -[:BASE_METRIC]-> <x>` and `<x>_surprise -[:BASE_METRIC]-> <x>`, so the base metric is always present — link the base once, guidance/surprise reuse it. |
| **action_event** | **always abstain** — no concept. (Belt-and-suspenders: G0 also abstains most event names.) |

So in practice: resolve concepts for the **base `metric`** drivers only; guidance/surprise inherit via
`BASE_METRIC`; action_event never links. **This BASE_METRIC inheritance is mandatory** — without it,
every guidance/surprise driver silently gets no link (safe, but needless recall loss), because the
matcher deliberately abstains on the suffixed name rather than guess.

---

## 7. LLM wiring (subscription, NO API key)

`llm` must use the user's Claude Code **subscription via OAuth**, never a metered API key.
Use `claude_agent_sdk` with an explicit `cli_path`. Pattern (see
`scripts/earnings/earnings_orchestrator.py::_run_learner_via_sdk`):

```python
from claude_agent_sdk import query, ClaudeAgentOptions
opts = ClaudeAgentOptions(cli_path="/home/faisal/.local/bin/claude")  # OAuth subscription
# def llm(prompt): run query(prompt, options=opts), return the final text.
```

- **Do NOT** pass or read `ANTHROPIC_API_KEY` (that bills the metered pool). See CLAUDE.md
  "Anthropic API Key Handling". The model picks/refutes; no key is ever an input to `link()`.
- The deterministic guards mean conceptless drivers cost **zero** LLM calls.

---

## 8. Finalized design decisions (locked by two validation rounds)

1. **Value-withheld inference.** The model never sees the number. Value+period anchoring is used
   ONLY offline to build the test answer key/auditor — it is too noisy to be a matcher.
2. **Guards = principles, not a dict.** G0/G1/G2 = fact_type routing + GAAP/non-GAAP. `tax_rate` /
   `effective_tax_rate` are deliberately allowed (a real us-gaap concept).
3. **Menu-restricted pick + adversarial verify.** Precision comes from: pick from the company's own
   reported concepts + an independent refuter that abstains when unsure. Unsure → abstain.
4. **In-menu check** — never emit a concept the company doesn't report (no hallucination).
5. **Company-extension & industry concepts are allowed and expected.** The matcher correctly links
   `aso:NumberOfNewStores`, `EmissionsTradingSchemeCostOfAllowances`, REIT `OperatingLeaseLeaseIncome`,
   utility `RegulatedAndUnregulatedOperatingRevenue`, MLP `…PerOutstandingLimitedPartnershipUnit`.
6. **Bare `eps` / `share_count` → diluted** by industry convention (value can't separate basic vs
   diluted; the panel confirmed diluted).
7. **Multiple equally-valid concepts** (e.g. a company reports BOTH `Revenues` and
   `RevenueFromContractWithCustomer…`): the prompt says "higher usage". Recommended hardening:
   **canonicalize deterministically to the highest-`usage` family member** so the choice is stable
   (this also removes most run-to-run flips, see §10). Treat such synonyms as equivalent in any audit.
8. **non-GAAP / adjusted abstain** (G2). The base metric carries the concept via `BASE_METRIC` (§6).
9. **Ambiguous aggregates** (`total_debt`, `operating_expenses`) are abstained often (correct: a
   `LongTermDebt`-only company is not "total debt"). **Recommendation:** split these in the driver
   vocabulary (`long_term_debt` vs `total_debt`; name the specific expense line) to lift recall.
10. **Optional stability gate** (cheap insurance): run `link()` 2–3× and abstain if the runs
    disagree. Flips are ~0.66% and occur only on borderline cells (synonyms / ambiguous aggregates),
    so this never costs a correct stable link — it only converts borderline wobble into a safe abstain.
11. **No change to `concept_linker.py` is warranted** by either validation. The reference
    implementation below is production-ready as-is.

---

## 9. What is proven (two independent validations)

**Build proof** — `plans/Drivers/WIP/concept_link_probe/` (31 guidance companies, value-anchored +
adversarial-panel answer key):
- Precision **100%** (0 wrong / 249 emitted links); abstention **100%** (0 / 1,178 conceptless);
  long-tail recall **99.4%** (0 wrong / 1,395 self-labeled concepts). Beat the curated
  `concept_resolver.py` baseline (195 links, 21 abstention leaks) on recall, precision, and autonomy.

**Re-validation** — `.claude/plans/Drivers/WIP/concept_link_revalidation/` (**274 companies**, all 11
sectors, **31 guidance + 243 non-guidance**, all 4 fact_types, **non-LLM** answer key = canonical
us-gaap families + balance/period structure, with the cardinal "wrong link" detected
deterministically):

| Bar | Result |
|---|---|
| **Precision** | **0 confirmed-wrong links** across 274 companies; every out-of-canon link adjudicated correct/defensible by us-gaap definition |
| **Abstention** | **100%** (0 / 10,960 conceptless: ratio, action_event, macro, non-GAAP, KPI) |
| **Recall** (metric) | **93.6%** (residual ≈58% defensible abstention on ambiguous aggregates) |
| **Stratum** | guidance: 100% precision / 71% recall · **non-guidance: 100% precision / 70% recall** (the prior proof skipped non-guidance — it behaves identically) |
| **Stability** | flip rate **≈0.66%**; flips are only between equally-valid concepts or borderline abstains — **no flip introduces a wrong link** |

Both validations are reproducible from the harnesses in those folders (data is read-only Neo4j;
ground truth is built with zero human labels).

---

## 10. Residual risks & monitoring

- **guidance/surprise need `BASE_METRIC` inheritance** wired (§6) — don't feed suffixed slugs. If
  skipped, those drivers silently get no link (safe, but needless recall loss).
- **`sg_a → GeneralAndAdministrativeExpense`** and **`total_debt → NotesPayable`** are
  nearest-line approximations on a few companies — defensible, not wrong; flag if SG&A-vs-G&A
  precision matters.
- **Stability flips** concentrate on `net_sales`/`stock_based_compensation`/`restructuring_charges`
  (synonyms) and `total_debt`/`operating_expenses` (ambiguous). Mitigate with §8.7 (canonicalize by
  usage) and §8.9 (vocabulary split), or the §8.10 stability gate.
- **Monitoring:** the link is enrichment, so the production guardrail is simple — periodically sample
  emitted links and check the picked concept's `balance`/`period_type` against the metric's expected
  signature (credit/duration for revenue, etc.); a contradiction is the cheapest non-LLM wrong-link
  alarm. Track abstention rate by fact_type (conceptless must stay ~100% abstain).

---

## 11. Production scale & batching

- The link is per-company (the concept is company-scoped). Resolve `link()` once per
  **(company, distinct base-metric driver)** and store; re-runs self-heal.
- **Batching:** one LLM call per company can resolve all of that company's base-metric drivers
  against its menu (the validation ran exactly this way — faithful and efficient). Guards remove
  conceptless drivers for free, so the LLM only sees plausibly-linkable metrics (~40/company).
- **Cost:** ~2 LLM calls per linkable (company, metric); 0 for guarded ones. Subscription-billed (§7).
- **Optional speedup at full 796-company scale:** cache an LLM-generated `metric → candidate
  us-gaap family` map ONCE (from the taxonomy), intersect with each company's menu, and only call the
  LLM when the intersection is ambiguous. Same precision, far fewer calls. Per-company LLM-pick is
  simplest and already proven — adopt the cache only if call volume becomes a constraint.

---

## 12. Reference implementation & file map

The production module is `plans/Drivers/WIP/concept_link_probe/concept_linker.py` —
`link(company, slug, menu, llm)` plus `guard()` and a `demo()` self-check. It is exactly §3 above.
Copy it into the Drivers production package, wire `llm` per §7, the menu per §4, the write per §5,
and the fact_type routing per §6. Nothing else is required.

**For deeper context (all read-only):**
- `concept_link_probe/ALGORITHM.md · PROOF.md · ATTEMPTS.md` — the build + why each alternative lost.
- `concept_link_revalidation/REVALIDATION.md · FAILURES.md · VERDICT.md` — the wide non-LLM re-validation.
- `concept_link_probe/concept_linker.py` — the code (the literal §3).
