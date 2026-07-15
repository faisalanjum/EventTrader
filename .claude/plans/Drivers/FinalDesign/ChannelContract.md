# CHANNEL CONTRACT v1.0 — the ONE input contract for every Driver channel
> **Status: ACTIVE (owner-directed 2026-07-15). THIS file is the sole public channel authority (one-copy law);
> its content derives from the frozen S2 packet spec (owner-approved 2026-07-14) as provenance, not a second
> authority. This file contains ONLY the contract. Every channel (fiscal.ai, guidance, learner, DCM, analyst
> news, action feed, future) reads THIS file. Changes only via owner amendment. Moves with the code at reorg.**
> **Amended 2026-07-15 (owner, one batch — pre-amendment bytes pinned in the Phase-1 freeze manifest):
> §3 XBRL row (exact context always + verified-empty `dimensions=[]`) · §3 guidance row (channels send
> company-confirmation EVIDENCE; the core derives the boolean) · banner provenance one-liner (Phase-4 seed,
> same owner batch).**

## 1. What a channel is (one line)
A channel FETCHES evidence and SUBMITS it. It never creates drivers, never names them, never decides identity —
the shared core validates and decides everything.

## 2. The flow
```
YOUR CHANNEL (fetch only) ──packet──▶ shared decomposer ──▶ kernel (identity) ──▶ writer (validate + store)
```

## 3. The packet — one submission = ONE source event
**Envelope (per event):**
| field | meaning |
|---|---|
| `source_id` | the graph event node's id (e.g. SEC accession) — must exist in Neo4j; not there yet → hold (PARK-RETRY) |
| `source_type` | `8k` \| `transcript` \| `10q` \| `10k` \| `news` — the TRUE document the quote came from (a press-release quote = the 8-K's own accession, never the 10-Q's) |
| `ticker`, `fye_month` | company + fiscal year-end month |
| `event_time` | the source's public timestamp (point-in-time discipline) |

**Raw items (per candidate fact, all AS STATED by the source):**
| field | rule |
|---|---|
| `quote` | REQUIRED, verbatim, never paraphrased |
| `raw_label_or_claim` | the source/vendor label or claim sentence, untouched |
| stated value(s) | **SIGNED** (negatives stay negative — never absolute-value), unscaled; + the raw unit text / format flags |
| period signals | stated end/start date · **your own cadence signal** (quarterly-vs-annual series — filing form alone is ambiguous) · **adjacent period wording** (column header / "as of" phrase you saw) · XBRL context verbatim when present (start/end dates + instant-vs-duration) |
| XBRL (when present) | concept qname + the EXACT context (start/end dates, instant-vs-duration) — ALWAYS. Assert a VERIFIED-empty dimension list explicitly (`dimensions=[]`); a missed extraction must never masquerade as consolidated. Every supplied dimension carries BOTH axis and member. Never fragments. |
| guidance lane only | `value_text` (numberless stated value) · `conditions` · company-confirmation EVIDENCE (verbatim who-said-it attribution; the CORE derives the `company_confirmed` boolean, never the channel) |

## 4. What you MUST NOT send (sent anyway ⇒ ignored and recomputed)
Final driver names · fact ids / fact_scope · fiscal_year/quarter you computed · measurement tokens ·
canonical units · ANY computed/derived number (only source-stated values ever enter — no vendor-calculated
ratios, % changes, or common-size rows as facts).

## 5. Submission rules
- One packet per source event; submit events **chronologically per company**.
- No coordination with other channels needed — late or duplicate arrivals at the same event are lawful and
  handled by the core (same fact converges; a conflicting fact gets its own flagged node; nothing is overwritten).
- Re-submission is idempotent (same input → same ids → merge in place).

## 6. What comes back per item (machine-readable)
`written` · `merged` (converged onto an existing fact) · `parked(reason)` (waits, auto-retries when its blocker
arrives) · `skipped(reason)` (terminal, counted) · `rejected(reason)` (contract violation — fix and resubmit).

## 7. Your ledger duties (channel-side, no packet fields)
- Keep your own ledger: record → submitted item → outcome. It drives your catch-up cursor.
- Keep a per-company-period **source-completeness + extraction-status stamp** (which expected sources were
  present and searched, zero extraction errors). A value-absent SKIP is legal ONLY against a clean stamp;
  an incomplete search is PARK-RETRY, not a skip.
- Value-absent SKIPs re-open on: a new source (instance or class) · a repaired corpus · a CERTIFIED locator
  upgrade. Nothing else.

## 8. Hard never-list
Never fabricate or round a number · never trim/paraphrase a quote · never assert two records are "the same
driver" (your grouping is provenance only — identity is decided per item by the core) · never write to Neo4j
yourself — the core's CLI is the only pen.

## 9. Onboarding a new channel
Implement three duties: SELECT (enumerate new source events since your cursor; backfill = same enumeration over
history) · FETCH (emit the §3 raw items) · SUBMIT (one packet per event, consume outcomes into your ledger).
Then pass your channel certification run before going live. That's the whole surface.

*Deep law (core builders only, channels don't need it): the frozen S2 packet spec · 12_TrackB_FactPipeline
FACT-17b · 09_DriverUpdate_Fields.*
