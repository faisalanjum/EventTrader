export const meta = {
  name: 'driver-gate-g2',
  description: 'G2 — INDEPENDENT admission gate (reusable). One test per candidate driver_name: is it a VALID, REUSABLE driver? Verdict = reuse / admit / rewrite / skip, per the FINAL_DESIGN §3 NAME rules, fail-closed (never delete/merge; err specific). No route bucket; no fundamental/news split (a producer concern, not a catalog one). Reusable in BATCH reconcile AND LIVE production (per new name, against the live catalog). Pass evidence-bearing candidates + catalog via args; defaults to the Restaurants seed.',
  phases: [ { title: 'Gate' } ],
}

const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})   // harness may stringify args
// Model slots (args-overridable; owner 2026-07-10): strong judge = sonnet @ effort high; clerk = sonnet engine-default. No haiku/opus defaults.
const _M = (A.models && typeof A.models === 'object') ? A.models : {}
const MODELS = { gate: _M.gate || 'sonnet', clerk: _M.clerk || 'sonnet' }
// PIPE-16: rulebook inlined verbatim below — from the now-archived 02_DriverCatalog.md, SYNCED to current law at NAME-17 (OD-21, 2026-07-16); current law = FINAL_DESIGN §3 NAME-01…19 (readers cannot fetch docs).
const RULEBOOK = `## Naming rules

### A. Core naming rules

#### NAME-01 — A driver name is the cause only  \`[LOCKED]\`
- **Rule:** The driver name is the reusable causal noun the evidence is about. What happened (the state), the direction, the size, the date, the company, the period, the units, and the raw quote all live in OTHER fields — never the name.

#### NAME-02 — One name per driver; no aliases list  \`[LOCKED]\`
- **Rule:** A driver stores exactly one name. Spelling, plural, acronym, and word-order variants of the same cause are the SAME canonical form — reuse it, never coin a duplicate. There is no "aliases" list on the driver. A true duplicate found later is joined to its canonical by a reversible "same-as" link, and each node keeps its own evidence.

#### NAME-03 — Open vocabulary  \`[LOCKED]\`
- **Rule:** Names use an open vocabulary. Every important noun in a name must come from the source material or an existing catalog driver — never a fixed, closed word-list.

#### NAME-04 — As specific as the evidence allows  \`[LOCKED]\`
- **Rule:** Name the cause as specific as the evidence allows. Never coin a broad or category name — breadth is not chosen; it emerges only when the same exact name is reused across events or companies.

#### NAME-05 — Name format  \`[LOCKED]\`
- **Rule:** A driver name has only lowercase ASCII letters, digits, and underscores; starts with a letter; never ends with an underscore; has no double underscores; and is at least 2 characters.

#### NAME-06 — Word order  \`[LOCKED]\`
- **Rule:** When coining a multi-part name, order the parts: concrete thing or actor → needed detail → metric or mechanism. ("Thing or actor" = a commodity, customer group, or policy body like the Fed / OPEC.) Brand/segment/place parts are sliced off first (NAME-10), so they don't appear here. Examples: \`hyperscaler_capex\`, \`restaurant_traffic\`, \`oil_price\`, \`fed_rate\`.
- **Note (singular-by-default — owner 2026-07-11):** SINGULAR BY DEFAULT — coin the singular form of a count noun (\`store_closure\` not \`store_closures\`, \`tariff\` not \`tariffs\`): the name is the cause CLASS; how many, how big, and how often live in the fact's fields, never the name. Keep the plural ONLY when (a) the plural is the standard financial/business term for that concept — the form it is normally reported under (\`earnings\`, \`bookings\`, \`sales\`, \`savings\`, \`futures\`, \`receivables\`) — or (b) the singular would name a DIFFERENT concept (\`product_returns\` — a "return" is an investment concept). The exception list is illustrative, never exhaustive — the two-part test decides (NAME-19). Locked whole phrases (NAME-08) are never singularized (\`same_store_sales\`).

#### NAME-07 — Familiar names win  \`[LOCKED]\`
- **Rule:** Use the familiar form: \`fed_rate\`, \`yield_curve\`, \`oil_price\`, \`tariff_policy\`, \`fda_approval\`. **Precedence (owner 2026-07-11):** the familiar short form applies only when the source does not itself distinguish a specific named sibling instrument or benchmark within that family; when the source names the sibling (SOFR vs the fed-funds family → coin \`sofr_rate\`), NAME-04 specificity wins. Familiarity is a fallback for undifferentiated mentions, never a license to flatten stated specificity. (Commodity benchmarks: already NAME-12(c).)

#### NAME-08 — Keep standard financial phrases whole  \`[LOCKED]\`
- **Rule:** \`gross_margin\`, \`free_cash_flow\`, \`net_interest_margin\`, \`same_store_sales\` stay whole.
- **Note (signed-driver pin — OD-12, owner 2026-07-06 · 66 §0.R OD-12):** a loss/deficit is the NEGATIVE region of the standard signed metric, not a separate cause — coin \`net_income\` / \`operating_margin\` / \`eps\`, never a loss-magnitude driver (\`net_loss\` / \`loss_margin\` / \`loss_per_share\`). The loss is stored as a negative value (09 §3), so two producers can't fork on \`loss_margin=+5\` vs \`operating_margin=−5\`. Consistent with NAME-15 (what-happened / size are not in the name).

#### NAME-09 — One cause per name (split multiples; short; a noun)  \`[LOCKED]\`
- **Rule:** A name carries exactly one cause. Two+ independent causes → a separate driver each, never bundled (\`asset_impairment_and_lease_termination\` → split). Keep names short; if it takes many words to be specific, it's probably two drivers. Reads as a noun.

### B. Name vs slice

#### NAME-10 — Own measured company parts → the slice, not the name  \`[LOCKED]\`
- **Rule:** Segment, geography, product, customer, channel, and entity_ownership are slices ONLY when the quote clearly frames them as the reporting company's own measured part. Stored slice kinds are FS-06's six kinds; "brand" is a source word, not a stored kind. Capture every such qualifier with FS-02 multi-slice. Examples: Apple reports iPhone sales → \`sales\` + \`slice=product:iphone\`; Nike revenue in China → \`revenue\` + \`slice=geography:china\`; supplier orders from Walmart → \`orders\` + \`slice=customer:walmart\`.

#### NAME-11 — External or unclear objects stay in the name  \`[LOCKED]\`
- **Rule:** Ask in order, stop at the first hit:
  - **0.** Strip freestanding direction/impact words first (rose, headwind, generic pressure…) — never in the name. Exception: a word like \`pressure\` may stay only when it is part of a specific reusable market force (\`glp1_pressure\`), not a generic effect word.
  - **1.** Is the qualifier clearly the reporting company's own measured part (segment/geography/product/customer/channel/entity_ownership)? → **SLICE** it under NAME-10.
  - **2.** Is the qualifier an external object, actor, platform, policy, event, or product causing the outcome? → keep it in the **NAME** (\`iphone_demand\`, \`aws_outage\`, \`china_lockdown\`, \`freight_cost_pressure\`, \`tiktok_ban\`).
  - **3.** Is the role unclear, or would stripping the qualifier leave only a vague fragment (\`demand\`, \`ban\`, \`pressure\`, \`outage\`)? → keep it in the **NAME**.
- **Customer pin:** \`customer:walmart\` is a slice only when the metric measures the reporting company's own business with Walmart (orders/revenue from Walmart). If Walmart's independent action is the cause, keep Walmart in the name (\`walmart_price_cuts\`).
- **Vendor pin:** Do not add a vendor slice kind here. A vendor/platform as an external cause stays in the name (\`aws_outage\`, \`aws_spending\`) unless a later owner rule creates a vendor slice.
- **Portion pin (OD-17):** a qualifier naming a PORTION of the measured quantity is never a slice — it stays in the name (see OD-17 below).

#### OD-17 — Portion qualifiers & non-population aggregates
- **Rule (core):** A qualifier naming which PORTION of the company's own measured quantity is counted — and that is not one of the six slice kinds, not a period window, and not a measurement version — stays in the NAME (\`current_rpo\`, \`fee_earning_aum\`, \`funded_backlog\`). Different portion = different driver, never SAME_AS the bare form. If unclear whether a word is a window or a portion, keep it in the name; never drop it.
- **(a) All-parts aggregates (population test):** a stated aggregate maps to FS-10's omitted slice ONLY when its population is the consolidated reporting entity ("total company", "consolidated", "group"). An aggregate crossing the ownership boundary or curating a subset is NEVER the omitted slice: network/system aggregates (\`systemwide_sales\`, \`gmv\`, \`total_payment_volume\`) are their own whole-phrase Drivers (NAME-08 posture); curated subsets ("core operations", ex-items, pro-forma combined) keep their qualifier — never mapped to the consolidated series.
- **(b) Residual buckets:** a company-stated residual ("Other", "Rest of World", "Corporate unallocated") is a LEGAL slice value of its stated kind (\`segment:other\`) — never a name token, never dropped. Residuals are company-specific and their composition may drift across periods: guards in 03 FS-07 note.
- **(c) Accounting constructs:** pure consolidation artifacts (eliminations, fair-value levels, reconciling items) are excluded as slice values AND as Driver names — never coin an eliminations Driver; drop-and-log (FS-20's log). An eliminations-driven mover is recorded as a fact on the AFFECTED reported metric (e.g. \`operating_income\`, lane state, quote carrying the eliminations mechanism) — evidence is never dropped.

### C. What's in / out of a name

#### NAME-12 — What's allowed IN the name  \`[LOCKED]\`
- **Rule:** In the name: (a) the cause; (b) per-X denominators (\`oil_price_per_barrel\`, \`dividend_per_share\`); (c) benchmark identity when a commodity has named, differently-priced benchmarks (\`brent_oil_price\` vs \`wti_oil_price\`); (d) terminal \`_guidance\` / \`_surprise\` suffixes under NAME-17. Nothing else.

#### NAME-13 — Per-X goes in the name (business AND physical)  \`[LOCKED]\`
- **Rule:** Transcribe whatever per-X the source states — business (\`per_share\`, \`per_square_foot\`) AND physical (\`per_barrel\`, \`per_tonne\`, \`per_hour\`), no judgment. Stated → oil at $80/barrel → \`oil_price_per_barrel\`; not stated → oil rose 8% → \`oil_price\`. Different per-X = a different driver (\`oil_price_per_barrel\` ≠ \`oil_price_per_tonne\`), never same-as. No per-X unit — the unit stays the base (usually \`usd\`/\`count\`).
- **Note:** Standard financial acronyms that already include the denominator keep their familiar name: \`eps\` is valid and does not need to become \`earnings_per_share\`.

#### NAME-14 — The version of a number is NOT in the name  \`[LOCKED]\`
- **Rule:** The version of a number (adjusted, diluted, basic, constant-currency, core, cash…) goes in the **measurement** slot INSIDE fact_scope — a sibling of the slice, NOT a 7th slice kind. \`adjusted eps\` → name=\`eps\`, measurement=\`{adjusted}\`. Store the specific stated word (case/whitespace/punctuation normalized); default empty (never assume gaap); gaap/non_gaap is a read-time view, never stored. A measurement word re-expresses the SAME quantity through a different lens; a word that changes WHICH portion is counted is never a measurement token — it belongs in the name (OD-17).

#### NAME-15 — What's kept OUT of the name  \`[LOCKED]\`
- **Rule:** Out of the name → into other fields: direction/impact (→ verdict), what-happened (→ driver_state), date/period (→ DriverPeriod), company (→ linked company), units & size (→ number fields), raw quote (→ quote). The name is only the cause.

#### NAME-16 — The full "banned inside a name" list  \`[LOCKED]\`
- **Rule:** None appear in a name (rejected even if the source uses them):
  1. state words → driver_state *[OK: stable nouns/metric phrases ending -ing/-ed: \`pricing\`, \`bookings\`, \`operating_margin\`]*
  2. direction/polarity → verdict
  3. motion/change nouns → driver_state
  4. the reporting company's own name/brand (redundant — the fact already links to the company), and any incidental co-mentioned entity adding no causal specificity (an analyst, executive, law firm, or counterparty named in passing) *[OK: an external company, platform, institution, or person whose own independent action or state IS the stated cause (NAME-11 test 2): \`fed_rate\`, \`opec_supply\`, \`fda_approval\`, \`walmart_price_cuts\`, \`aws_outage\`, \`tiktok_ban\`]*
  5. period tokens
  6. numbers/sizes/bare units (\`bps\`, \`percent\`, \`usd\`)
  7. source-type labels
  8. provider/vendor labels as metadata *[OK when the vendor/platform is the external cause under NAME-11: \`aws_outage\`, \`aws_spending\`]*
  9. XBRL prefixes
  10. metaphors/sentiment/effect-on-stock words *[OK only when the word is part of a specific reusable market force, e.g. \`glp1_pressure\`; generic "pressure" stays banned]*
  11. a bare category word alone (\`macro\`, \`sector\`, \`demand\`, \`sentiment\`)
  12. vague descriptors too broad to name a cause
  13. glue words (\`the\`, \`of\`, \`in\`, \`and\`, \`to\`, \`for\`)

### D. Family, gate & meta

#### NAME-17 — Metric-family suffix stays in the name  \`[LOCKED]\`
- **Rule:** Name metric + mechanism: \`{metric}_surprise\` (a delivered actual OR a promised guide compared with a cross-party expectation; ONE surprise driver holds all three surprise types: actual_vs_consensus, actual_vs_guidance, guidance_vs_consensus — OD-21, synced 2026-07-16), \`{metric}_guidance\` (forward outlook) — \`eps_surprise\`, \`revenue_guidance\`. Suffix stays in the name AND fact_type is a separate permanent field. The base \`{metric}\` is a separate driver linked by \`BASE_METRIC\` (never same-as). Beat/miss/raised → driver_state, never the name.

#### NAME-18 — The new-driver gate  \`[LOCKED]\`
- **Rule:** Propose a new driver only when ALL hold: (a) no existing name means the same cause; (b) it satisfies every naming rule; (c) each important noun comes from the source or an existing driver; (d) it's attached to ≥1 causal claim with real evidence; (e) it's a reusable CLASS, not bound to a single instance (\`government_shutdown\` OK even once; \`q1_2026_shutdown_effect\` rejected); (f) if the rules leave >1 candidate name → reject as ambiguous; (g) if the evidence is vague or names no reusable cause → skip, never invent.

#### NAME-19 — Rule changes use one general principle, never sector examples  \`[LOCKED]\`
- **Rule:** Any change to the naming rules must be a single general principle, not sector-specific examples. Examples overfit — named domains pass while unnamed ones break on held-out data.`
// args = { candidates: [{driver_name, evidence_refs:[{company,source_type,source_id,date,quote}]}], catalog: [..already-admitted names, for the reuse check..] }
const cands   = A.candidates || null
const catalog = A.catalog || []
if (!cands || !cands.length) throw new Error('gate.js requires args.candidates (the stale _menu_restaurants_seed.json default was removed — the file no longer exists).')

const GATE_SCHEMA = { type:'object', additionalProperties:false, required:['verdicts','counts'], properties:{
  verdicts:{type:'array', items:{type:'object', additionalProperties:false, required:['driver_name','verdict','reason'], properties:{
    driver_name:{type:'string'},
    verdict:{type:'string', enum:['reuse','admit','rewrite','skip'], description:'reuse | admit | rewrite | skip'},
    reuse_name:{type:'string', description:'existing catalog name to reuse, if verdict=reuse, else ""'},
    rewrite_to:{type:'string', description:'fixed name if verdict=rewrite (WORDING-ONLY), else ""'},
    reason:{type:'string'} }}},
  counts:{type:'object', additionalProperties:true} } }

phase('Gate')
// Step-0 BILLING GUARD (subscription-only, CLAUDE.md).
const _bg = await agent(`Run with Bash and report: test -z "$ANTHROPIC_API_KEY" && echo GUARD_OK || echo GUARD_FAIL. Return {ok:true} iff it printed GUARD_OK.`, {schema:{type:'object', additionalProperties:false, required:['ok'], properties:{ok:{type:'boolean'}}}, model:MODELS.clerk, label:'billing-guard', phase:'Gate'})
if (!_bg || !_bg.ok) throw new Error('BILLING-GUARD: ANTHROPIC_API_KEY present in env (or guard died) — refusing to run; subscription-only policy (CLAUDE.md).')
const candsClause = `Judge exactly these candidates — EACH carries its evidence_refs[{company,source_type,source_id,date,quote}]; judge from the evidence, NOT the bare name: ${JSON.stringify(cands)}.`
const catClause = catalog.length
  ? `EXISTING CATALOG (verdict=reuse if a candidate is the EXACT same cause as one of these): ${JSON.stringify(catalog)}.`
  : `(No prior catalog supplied — verdict=reuse only if two candidates are exact-same.)`

const res = await agent(`You are an INDEPENDENT admission gate — judge each candidate driver_name FRESH and skeptically; do NOT assume whoever coined it was right.
NAMING RULES — authority = FINAL_DESIGN.md §3 (NAME-01…19); inlined verbatim from the archived 02_DriverCatalog.md, synced to current law at NAME-17 — OD-21 2026-07-16 (PIPE-16):
${RULEBOOK}
${candsClause}
${catClause}
THE ONE TEST: is this a VALID, REUSABLE, consistently-nameable Driver? Judge from the EVIDENCE (each name's evidence_refs), not the bare name string. For EACH name give ONE verdict:
- reuse = EXACT same cause AND scope as an existing catalog name (put it in reuse_name).
- admit = a valid reusable cause that follows every rule.
- rewrite = right driver, fixable WORDING-ONLY rule-break; give rewrite_to (must NOT change the meaning).
- skip = vague, rule-breaking, or tied to ONE specific event/date/quarter/headline (NOT a reusable class). Reusability is about the CLASS not the count: a reusable event class (e.g. government_shutdown, food_safety_incident, goodwill_impairment) is ADMITTED even if seen once; only a name bound to a single instance is skipped.
For any reuse or rewrite, first verify same object + same scope + same mechanism; if any is false or unclear, do NOT reuse/rewrite — keep separate / admit separately / skip. If a name's evidence is missing, vague, or MIXED (different meanings across companies), do not admit/reuse blindly — prefer keep-separate/skip; rewrite only if it is a pure wording fix.
Do NOT classify "fundamental vs news/trading" — that is a producer concern, not a catalog one; a valid reusable driver is admitted. Fail-closed: never delete or merge; err specific. Return GATE_SCHEMA.`, {schema:GATE_SCHEMA, model:MODELS.gate, effort:'high', label:'g2-gate', phase:'Gate'})
return res
