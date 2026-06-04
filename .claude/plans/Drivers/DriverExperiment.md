# Driver Experiment — run / resume guide

Operator guide for building **ONE shared Driver catalog** (used by all producers), industry by industry,
scaling toward ~1000 companies. This file = the WHY + the repeatable procedure + the reusable scripts + status.
For the full spec, read the two canonical files first:

- **`Drivers.md`** — the design, the creation process (G1/G2 gates), the experiment, the honesty gate.
- **`DriverOntology.md`** — the naming rules (a Driver name = one specific, reusable noun).

---

## Why these decisions (don't re-litigate)

- **v1 and v2 both died the same way:** the producer made an **unanchored semantic judgment** and either
  **over-merged** (demand themes collapsed into a generic `revenue_demand`) or flip-flopped names run-to-run.
- **Root cause = two judgment moments** that rules can narrow but never remove:
  1. *"Is this already named?"* (→ synonym fragmentation if missed)
  2. *"Is this a real, specific-enough driver?"* (→ scope drift / over-broad names)
- **So the method is:**
  - **Open vocabulary** — a closed vocab scored **82%-reject**; do **not** bring it back. Names come from the source.
  - **Anchor the producer with the catalog (G1)** — reuse before create; this is what makes two LLMs converge.
  - **An independent gate (G2)** before any new name enters the one shared catalog.
- **Fail-close invariant (the safety rail):** err **specific**; **link (SAME_AS), never merge/overwrite**; merge only on
  **exact same meaning**. *Aggressive merging = the v2 collapse. A tighter rulebook = v1 overfit/over-reject.* Stay here.
- **Cross-company peer grouping = retrieval** (same-industry + embeddings) at read time, **not** a coined generic name.
  That coined-generic was the exact thing that failed; the name stays specific.

---

## The repeatable procedure (per industry, then scale)

1. **Build menu (blind, parallel)** — 1 subagent per company: pull its fiscal.ai KPIs (rewrite each to a standard
   `driver_name` — raw labels are suggestions only) + its **>2%-move events**, then coin candidate names per
   `DriverOntology.md`. Output: `driver_name` + evidence quote + source type + company + date + optional
   XBRL concept/member link + optional Guidance/GuidanceUpdate link.
   *Blind/parallel is for the TEST only (measures raw convergence). Production is catalog-first (G1).*
   **Seed sources = filings + transcripts + fiscal.ai KPIs only — NO news**, all events with >2% daily_stock (no cap).
   News/macro drivers accrete **LIVE in production** (reuse-or-create + G2); there is **no separate news build**.
2. **Reconcile (G1 + G2)** — embeddings surface possible matches only; for exact-same-meaning, an independent
   gate **chooses a canonical + proposes reversible SAME_AS** (never merge/delete); an **independent** model rules each name → **reuse / admit / rewrite(broad→specific)
   / scope-route / skip**. Output: a review file.
3. **Honesty gate** — freeze the catalog → feed **fresh** events using only names/data visible on or before the event date → producer must reuse / create / skip; an
   **independent** grader scores against a **pre-written** key; **grade once** (see `Drivers.md` § Honesty gate).
4. **Human review → next industry.** Scale to ~1000 by repeating 1–3. Any rule change must be a **general principle**,
   never sector-specific examples (examples overfit — that's how v1 died).

`scope-route` = e.g. `analyst_rating` / `analyst_price_target` / `short_interest` → possible **news/trading** drivers,
**not** Phase-1 fundamentals (route, don't ban).

---

## Reusable artifacts (so a repeat = zero rework)

- **`workflows/menu_build.js`** — the blind per-company menu builder (Step 1). To repeat on another industry: edit the
  `TICKERS` list (or swap the company query) and re-run via the **Workflow** tool. *(Probe inside it auto-detects the
  returns query.)*
- **Data facts the builder relies on (verified):** returns live as **percent-point** properties on the event→Company
  edge — `(News|Transcript)-[:INFLUENCES]->(Company)` and `(Report)-[:PRIMARY_FILER]->(Company)`; fields
  `daily_stock` (raw) and `daily_macro` (market-relative). Threshold 2% = **2.0**, not 0.02. fiscal.ai KPIs:
  `data/fiscal_ai_segments/fiscal_segments.sqlite`, `section='Key Performance Indicators'` (no sqlite3 CLI → use python3).
- **`_menu_<industry>.json`** — per-industry review output (read-only; nothing is written to Neo4j during calibration).
- *(Reconcile script added once Step 2 runs.)*

---

## Status (2026-06-04)

- **DONE — Restaurants pilot** (14 cos, blind). Strong convergence: `eps_surprise` 14/14, `revenue_surprise` 14/14,
  `same_store_sales` 13/14; **traffic stayed separate from pricing** (v2's killer did not recur). Surfaced 13
  exact-meaning dup pairs + 12 scope flags. Output: `_menu_restaurants.json` (92 distinct names from 177 candidates).
- **NEXT — Step 2 reconcile** on those 92 → clean Restaurants catalog (canonical + proposed SAME_AS + scope-routes +
  skips), review-file only. Then the honesty gate. Then a 2nd industry. Then scale.

## Cost guard
Workflow subagents run **in-session (subscription)**. Embeddings = OpenAI (cheap, separate key). **Never** use
`claude -p` / `claude_agent_sdk` (metered).
