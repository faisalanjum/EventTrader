# Driver contracts — public input and internal facts

**Current authority: Part I (V1). Part II (V2) remains staged.**

## How to use this document

This is the single file for the public and internal contracts. [Part I](#channel-v1) governs the
current V1 boundary; [Part II](#channel-v2) is the V2 candidate for Steps 3–5.
Only after Step 6 passes does Part II become active and Part I become historical.
The internal V1 contract is active in [Part III](#internal-contract). Public
input and Core-to-Core handoffs remain separate contracts, not a combined input
schema. `FINAL_DESIGN.md` remains the meaning owner. No code route or write
permission changes here.

**Lossless consolidation — owner-authorized 2026-09-15.** All three original texts
are preserved byte-for-byte between their BEGIN/END markers, including titles,
tables, examples, JSON, dated statements and old file-movement instructions.
Section numbers inside each part refer to that part only. Their old “this file”
banners describe the original files. This opening section supersedes their
packaging instructions: activate the appropriate part, never delete this combined
file. Old implementation-status statements are dated evidence, not a claim about
today's code. Preserve all original blocks when doing the later switch.

### Differences and work still required

These are recorded differences, not permission to mix the two versions or
silently choose a rule. Preserve current V1 behavior until the planned switch.

| Issue | Exact difference or gap | Required handling |
|---|---|---|
| Forbidden input | V1 §4 ignores and recomputes forbidden fields; V2 §2 rejects them. | Keep each version's rule separate; prove V2 rejection before Step 6. |
| Retry | V1 §6 promises retry when a blocker clears; V2 §9 promises it only for `SourceUnavailable / SOURCE_UNAVAILABLE`. | Apply the Step 2 outcome ruling and Step 10 retry work; do not promise retry for every parked result. |
| Guidance input | V1 §3 names `value_text` and `conditions`; V2 §2 preserves their meaning, but its raw-item JSON list omits those separate fields. | Step 5 must prove where this evidence enters and survives; do not silently add fields or drop meaning. |
| Validation and wiring | V2 §6 names `validate_via_production`; the staged event route uses its shared deterministic validation tail. V2 §§7/10 still describe occurrence checking/raw-boundary tests as unbuilt. | Resolve the named-owner mismatch in Step 5 and replace outdated status at Step 6; never add a second validator merely to match prose. |
| Result accounting | V2 §9 says one decision per input; later Step 5 requires complete input-to-fact/result accounting for split and combined facts. | Prove that relation in Step 5, then publish it at Step 6; no dropped input or produced fact. |
| V1 safeguards not explicit in V2 | V1 requires an existing source (or hold), the source's public timestamp, preservation of conflicting facts, and channel certification before live use. V2 does not explicitly repeat all four; “CERTIFIED locator upgrade” is not channel certification. | Account explicitly for each in the proved V2 contract under the unchanged design law before activation; retaining old text alone is not proof. |
| Who builds the internal object | Part III A says the channel “hands” Core the object; Part III C/D and the public boundary require raw evidence and shared Core interpretation. | Channels follow the public contract, not the internal field list. Step 6 must remove the ambiguity from the active V2 instructions while retaining V1 as history. |
| Internal V1 fields versus V2 | Part III retains raw units, unit-kind/money-mode hints and V1 scaling instructions; V2 requires model-stated units/scale evidence and deterministic arithmetic. | Keep the versions separate. Step 6 derives the internal V2 fields from the exact proved Step 5 code; do not send legacy V1 instructions to V2 producers. |
| Old completion claims | Part III contains dated “unbuilt,” “needs owner confirm” and completed-work statements. | They describe the original V1 record. Use STATUS_AND_HISTORY for current progress; this move proves preservation, not completion of the remaining build. |

### Step 6: activate, do not consolidate again

Follow [step6.md](LeftOverSteps/step6.md). After the required Step 5 proof,
activate the proved Part II, mark Part I historical, and update this opening
status. Resolve the table above through the already-assigned steps, refresh
Part II's staged/status wording, separately refreeze the internal contract in Part III, move
callers and remove V1-only code. Preserve the V1 text here as non-operational
history, and preserve Part III's original V1 block beneath the new active V2
internal contract. All existing safety, evidence, test and no-write gates still apply.

### Original identities and saved evidence

At commit `18f38be90bae6926b69b44fd1ce3a8d6c858d26c`, under
`.claude/plans/Drivers/FinalDesign/`:

| Preserved part | Original file | Original SHA-256 |
|---|---|---|
| I | `ChannelContract.md` | `1062e0fb1b58b4311bb4a03d0a4a42274288c460d22f74a8f75cc803bb04b0dd` |
| II | `ChannelContractV2.md` | `d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b` |
| III | `15_CandidateFactPacket.md` | `aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c` |

These hashes identify the original section bytes, not this combined file.
Active readers use this file; new manifests hash the file they actually read.
Historical manifests, prompts, answers, patches and receipts remain unchanged:
verify them using their recorded Git commit or preserved snapshot, not today's
document layout. A path-only consolidation does not require new AI calls.
The original V2 freeze in `STATUS_AND_HISTORY.md` now checks Part II's bytes.
The internal V1 pin checks only Part III's preserved block, never the combined
file hash. Historical rev-3/rev-4 patches and edit tables retain their original
paths: replay them against their recorded Git snapshot, not this document.
They do not replace Step 6's requirement to derive the internal V2 contract
from the proved Step 5 code. A7's prompt builder still reads its approved
prompt sections and code-owned fields, not this combined document.

<a id="channel-v1"></a>

## Part I — V1 (active)

<!-- BEGIN V1 -->
# CHANNEL CONTRACT v1.0 — the ONE input contract for every Driver channel
> **Status: ACTIVE (owner-directed 2026-07-15). THIS file is the sole public channel authority (one-copy law);
> its content derives from the frozen S2 packet spec (owner-approved 2026-07-14) as provenance, not a second
> authority. This file contains ONLY the contract. Every channel (fiscal.ai, guidance, learner, DCM, analyst
> news, action feed, future) reads THIS file. Changes only via owner amendment. Moves with the code at reorg.**
> **Amended 2026-07-15 (owner, one batch — pre-amendment bytes pinned in the Phase-1 freeze manifest):
> §3 XBRL row (exact context always + verified-empty `dimensions=[]`) · §3 guidance row (channels send
> company-confirmation EVIDENCE; the core derives the boolean) · banner provenance one-liner (Phase-4 seed,
> same owner batch).**
> **Amended 2026-07-18 (owner): §7 points earnings 8-K source completeness to PER-21 / BUILD §3's two
> canonical routes. No packet field or channel/core boundary changed.**

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
- For earnings 8-K source completeness, use only the two canonical routes in `FINAL_DESIGN.md` PER-21 /
  `BUILD_AND_OPERATIONS.md` §3. A channel never invents or copies an 8-K-to-periodic-filing matcher.
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
<!-- END V1 -->

<a id="channel-v2"></a>

## Part II — V2 (staged)

<!-- BEGIN V2 -->
# CORE V2 PUBLIC CHANNEL CONTRACT
> **STAGED — NOT LIVE UNTIL THE ATOMIC V1->V2 SWITCH.**
> `ChannelContract.md` (v1.0) is the LIVE public channel authority and
> `15_CandidateFactPacket.md` is the LIVE internal packet law. Both remain
> canonical and byte-identical; nothing here governs a running path.
> AT THE ATOMIC SWITCH, in one batch: this document is PROMOTED to
> `ChannelContract.md`; `15_CandidateFactPacket.md` is SEPARATELY re-frozen to
> its own V2 packet law — it is a distinct internal contract and is NOT replaced
> by a copy of this public one; the hash pins then move; and THIS FILE IS
> DELETED. Freezing this document performs no AI call, no fetch, no database
> read or write, and no live action.

## 1. What this is
The PUBLIC contract for EVERY channel. Fiscal is the first staged consumer, not
the only governed one. Core owns validation, identity, multiplication and
writing. A channel transports source evidence and records the outcomes it
receives; it never names a driver, never decides identity, never canonicalizes
units, never mints ids, and never writes to Neo4j.

## 2. Stage A — the CHANNEL RAW EVENT (this is the public input)
A channel SELECTS its source events, FETCHES the source evidence, and SUBMITS
ONE EVENT AT A TIME, chronologically per company.

**Event envelope:** `source_id` · `source_type` · `ticker` · `fye_month` ·
`event_time` · event-level ordered `text_parts`, each exactly `{part, content}`,
SUPPLIED ONCE for the event · the raw items.

**Required for ANY candidate:** `quote` and `raw_label_or_claim`. Value, period
and XBRL fields are present WHEN THE SOURCE OR LANE SUPPLIES THEM — optional
presence is not permission to send a field that is not in the published list.

**Raw items — preserve the source, never restate it:** verbatim `quote` and
`raw_label_or_claim` · the source-stated SIGNED, UNSCALED value with its
format/unit flags · stated period, cadence, and adjacent-period evidence ·
provenance · and the optional exact XBRL bundle.

**The XBRL raw bundle:** exact concept · context dates and type · unit ·
`ix.scale` / sign / format / `unit_ref` · `source_evidence` · and raw
`dimensions` whose entries carry EXACTLY `axis` and `member` (see §4).

**Guidance semantics, unchanged:** optional numberless value · `conditions` ·
verbatim company-attribution EVIDENCE. CORE derives `company_confirmed`; the
channel never sends the boolean.

**FOUR RETIRED FISCAL-AUTHORED FIELDS ARE NOT ACCEPTED AND NEVER DEFAULTED:**
`level_unit_raw` · `level_unit_kind_hint` · `level_money_mode_hint` ·
`level_shape_hint`. (`level_shape_hint` exists later only as READER OUTPUT, never
as channel input.)

**NEVER SEND — sending any of these FAILS CLOSED: the item is REJECTED, never
silently ignored.** The allowed spellings are an exact allowlist; an extra or
forbidden field is a contract violation to fix and resubmit. (Core computes its
own fields only AFTER accepting a lawful raw item; that is never authority to
accept a forbidden input.)
Never send: a final driver name,
identity or id · computed fiscal_year/quarter · measurement tokens · canonical
units · ANY derived or vendor-calculated number. NEVER fabricate or round a
number, NEVER trim or paraphrase a quote, NEVER assert two records are the same
driver, NEVER write to the graph — Core's CLI is the only pen.

**SOURCE COMPLETENESS:** a value-absent SKIP is legal ONLY against a clean
per-company-period source-completeness stamp; an incomplete search PARKS, it does
not skip. A skip reopens on exactly three triggers: a new source, a repaired
corpus, or a CERTIFIED locator upgrade. Earnings 8-K completeness uses the
existing `FINAL_DESIGN.md` PER-21 / `BUILD_AND_OPERATIONS.md` §3 routes — a
channel never invents or copies an 8-K matcher.

**`source_type` vocabulary, unchanged by this freeze:** `8k` · `transcript` ·
`10q` · `10k` · `news`.

**Channel duties that do not change:** keep your own ledger and cursor; keep the
per-company-period source-completeness stamp; late or duplicate arrivals at the
same event are LAWFUL and handled by Core; re-submission is idempotent; and the
channel consumes each FINAL outcome into its ledger and cursor.

## 3. Stage B — READER / CORE PREPARATION (not channel authority)
The reader produces the exact `PreparedFactV2` model fields, including FINAL
units and, for text, each numeric slot as
`{value, scale_multiplier, unit_scale_evidence}`.

CORE — never a channel — converts the raw XBRL `{axis, member}` evidence into the
trusted INTERNAL `member_refs` triples, and Core is the ONLY caller of the XBRL
trust door.

## 4. Dimension references — TWO STAGES, never conflated
These are DIFFERENT shapes at DIFFERENT boundaries, and collapsing them is the
error this section exists to prevent.

| stage | shape | who produces it |
|---|---|---|
| PUBLIC raw input `xbrl.dimensions` | entries carry EXACTLY `axis` and `member` | the CHANNEL |
| INTERNAL `member_refs` into the XBRL trust door | entries carry EXACTLY `axis`, `member` and `slice_part` | CORE enrichment |

A channel NEVER invents `slice_part`. Core derives the slice token from the
frozen axis and member-label owners, and `member_refs` is rechecked at the
internal boundary. At BOTH stages an empty list means VERIFIED-EMPTY dimensions
and never "not extracted"; every string is non-blank.

## 5. The two trust doors
The MODEL and TRUSTED-XBRL trust boundaries MUST REMAIN SEPARATE. A later single
public event pipeline may ROUTE to them, but may never merge or duplicate their
trust rules. `attach_event_xbrl` is CORE's sole XBRL trust door — it is not
channel-callable.

| door | purpose |
|---|---|
| `PreparedFactV2.from_dict` | the MODEL boundary — text/model facts. Accepts exactly the model-owned item fields and the fact-level keys; REFUSES the source-owned XBRL fields, so a reply can never assert verified structured evidence about itself. |
| `attach_event_xbrl` | CORE's SOLE XBRL trust door, called by Core only. Verified structured evidence enters here and nowhere else. |

## 6. The shared validator — staged vs current, stated exactly
`validate_via_production` is the ONE shared validation owner, and no second rule
engine, wrapper or heuristic may be created.

**CURRENT (staged, true today):** NEITHER door calls it. Each door constructs and
checks facts at its OWN trust boundary only.
**AT THE SWITCH (required):** the switched pipeline and scorer MUST route every
prepared fact through `validate_via_production` before any write.

## 7. Evidence locator — what is wired, and what is not
Event text parts are supplied ONCE per event. A fact refers to a part by
`part_ref`, plus its verbatim `quote` and the `occurrence_in_part` that
disambiguates a repeated quote.

**CURRENT:** the XBRL event door checks part_ref / quote / occurrence today. The
text constructor CANNOT — it receives no event parts.
**AT THE SWITCH (required):** the future CORE event pipeline — never a channel —
must run `verify_occurrence` against the named part before validation and write.
This is not wired now.

## 8. Scale proof differs by source
- **Text facts:** `unit_scale_evidence` is QUOTE-LOCAL. If the scale marker sits
  outside the quote, extend the quote CONTIGUOUSLY to include it, or abstain.
  Never cite a marker the quote does not contain.
- **XBRL facts:** `unit_scale_evidence` is NULL. Scale is proved JOINTLY by the
  verified `xbrl.ix.scale`, the verified `xbrl.ix.unit_ref`, and the bound
  `xbrl.source_evidence.pieces`. The scale fields live INSIDE the nested `ix`
  object — not at the top of the bundle and not on the pieces. Never by prose.

## 9. Stage C — what comes back — staged vs final, stated exactly
**CURRENT staged result:** `attach_event_xbrl` returns successful facts as
`(index, fact)` PAIRS carrying NO outcome row; only PREFLIGHT FAILURES produce a
row, whose fields are `index`, `fact_id`, `decision`, `codes`, `detail`.
`from_dict` returns a fact or raises. `written` and `merged` arrive only from the
later writer; `skipped` is the channel/reader abstention path.
**FINAL switched accounting:** every input item ends in exactly ONE of the five
public decisions.

RETRY, precisely: only `SourceUnavailable` with `SOURCE_UNAVAILABLE` means
automatic retry. Other production-validation and slot-conversion parks are NOT
promised an automatic retry when a blocker clears. Any error not listed in the
outcome classes propagates LOUDLY and is never converted into an item row.

## 10. Machine-readable surfaces
This block PUBLISHES the contract's enumerable surfaces. Every CURRENT
CODE-OWNED surface here is mechanically compared to its live owner by
`driver/core/test_v2_attacks.py`: if one moves in the code and this block is not
updated in the same breath, that test fails. The `staged_raw_channel` profile is
NOT compared to code — it is HASH-FROZEN by this document and later consumed by
Fiscal's own boundary tests. There is exactly ONE such block in this document.

SCOPE, stated honestly: these surfaces are the CURRENT V2 code boundary. The
Stage-A raw channel fields in §2 are NOT mechanically compared to code here —
that boundary is not built yet. Until Fiscal writes its own boundary tests, §2 is
owned by this document's hash freeze and by reviewer approval, not by a test.

```json CONTRACT-SURFACES
{
  "fact_keys": [
    "fact_type",
    "part_ref",
    "occurrence_in_part",
    "per_x",
    "item"
  ],
  "item_fields": [
    "driver_name",
    "driver_state",
    "quote",
    "level_low",
    "level_high",
    "change_value",
    "comparison_low",
    "comparison_high",
    "comparison_baseline",
    "value_text",
    "conditions",
    "company_confirmed",
    "level_unit",
    "change_unit",
    "level_shape_hint",
    "comparison_shape_hint",
    "measurement_raw_spans",
    "period_start_date",
    "period_end_date",
    "fiscal_year",
    "fiscal_quarter",
    "half",
    "month",
    "long_range_start_year",
    "long_range_end_year",
    "sentinel_class",
    "time_type",
    "period_scope",
    "slice_parts",
    "surprise_basis_hint",
    "has_favorability_wording",
    "polarity_proof"
  ],
  "source_owned_fields": [
    "member_refs",
    "xbrl_concept_raw"
  ],
  "run_input_fields": [
    "source_id",
    "facts",
    "calendar_override"
  ],
  "slot_keys": [
    "value",
    "scale_multiplier",
    "unit_scale_evidence"
  ],
  "canonical_units": [
    "usd",
    "m_usd",
    "percent",
    "percent_yoy",
    "percent_sequential",
    "percent_points",
    "basis_points",
    "count",
    "x",
    "unknown"
  ],
  "xbrl_attach_exports": [
    "attach_event_xbrl"
  ],
  "attach_event_xbrl_signature": "(items, *, source_id, store, filing_provider, text_parts, menu_tokens=frozenset())",
  "prepared_fact_v2_from_dict_signature": "(d)",
  "run_input_v2_from_dict_signature": "(d)",
  "validate_via_production_signature": "(fact, *, driver, source, fye_month, home_facts=None, source_id=None, calendar_override=False, lookups=None)",
  "verify_occurrence_signature": "(part_text, quote, occurrence_in_part)",
  "event_item_keys": [
    "fact",
    "concept",
    "member_refs",
    "source_evidence"
  ],
  "text_part_keys": [
    "part",
    "content"
  ],
  "attach_result_fields": [
    "source_id",
    "facts",
    "preflight_outcomes",
    "member_menu"
  ],
  "public_decisions": [
    "written",
    "merged",
    "parked",
    "skipped",
    "rejected"
  ],
  "preflight_outcome_row_fields": [
    "index",
    "fact_id",
    "decision",
    "codes",
    "detail"
  ],
  "source_evidence_keys": [
    "representation_sha256",
    "quote_span",
    "raw_label_span",
    "pieces"
  ],
  "piece_keys": [
    "kind",
    "text",
    "span"
  ],
  "piece_kinds": [
    "header",
    "section"
  ],
  "outcome_classes": {
    "SchemaError": "rejected",
    "ProductionValidationError": "parked",
    "SlotConversionError": "parked",
    "SourceUnavailable": "parked"
  },
  "staged_raw_channel": {
    "_note": "The FIRST-CONSUMER (Fiscal) raw profile, frozen by this document's hash. NOT compared to code: that boundary is unbuilt. Exact allowed spellings; lane-specific PRESENCE is described in prose, not implied here. Extra fields are not silently allowed.",
    "event_fields": [
      "source_id",
      "source_type",
      "ticker",
      "fye_month",
      "event_time",
      "text_parts",
      "items"
    ],
    "text_part_fields": [
      "part",
      "content"
    ],
    "item_fields_after_retirement": [
      "raw_label_or_claim",
      "value",
      "fmt",
      "is_currency",
      "period_end",
      "cadence",
      "quote",
      "period_evidence",
      "tier",
      "quote_source",
      "xbrl"
    ],
    "xbrl_fields": [
      "concept",
      "period_start",
      "period_end",
      "ptype",
      "unit",
      "ix",
      "source_evidence",
      "dimensions"
    ],
    "ix_fields": [
      "scale",
      "sign",
      "format",
      "unit_ref"
    ],
    "dimension_fields": [
      "axis",
      "member"
    ],
    "source_evidence_fields_ref": "see source_evidence_keys in this block",
    "piece_fields_ref": "see piece_keys in this block",
    "retired_fiscal_fields": [
      "level_unit_raw",
      "level_unit_kind_hint",
      "level_money_mode_hint",
      "level_shape_hint"
    ],
    "source_type_vocabulary": [
      "8k",
      "transcript",
      "10q",
      "10k",
      "news"
    ]
  }
}
```
<!-- END V2 -->

<a id="internal-contract"></a>

## Part III — Internal contract (V1 active)

For Core builders, not source collectors. The preserved V1 text below defines
internal handoffs and their source-evidence requirements; it is not an additional
public input shape. Its dated status and legacy fields remain V1-specific.
Step 6 must add and activate the proved internal V2 contract here, then mark
this V1 block historical without deleting or rewriting it.

<!-- BEGIN INTERNAL V1 -->
# S2 — the ONE candidate-fact packet + decomposition spec ❄️ FROZEN v1.0
> **AMENDED by OD-21 (owner-approved 2026-07-14, parallel surprise track · 66 §0.R OD-21 · 95 #42):** fact_scope
> gains an optional 4th slot `surprise=<actual_vs_consensus|actual_vs_guidance|guidance_vs_consensus>` after
> `measurement` — surprise lane ONLY, CODE-composed (basis_hint × comparison_baseline) pre-fusion, in the id +
> series key. Channels untouched (ChannelContract unchanged). Where this doc's fact_scope grammar shows three
> slots, read four per OD-21; 09/12 carry the binding wording.
**Status: FROZEN — OWNER-APPROVED 2026-07-14 ("Approved. Freeze S2"). Task #778 closed. Any change now requires
an explicit owner amendment. Scope: METRIC (fiscal.ai) + GUIDANCE worked; surprise/action slot in via owner's
parallel track without touching the frozen shape. Repo persistence (FinalDesign doc + DU-02 amendment + 95 rows)
= S6 back-port package, owner-approved batch.**
**Finding in one line: >99% of the packet already exists in locked law; it just was never assembled into ONE object. The genuine gaps are 2 conflicts + 2 missing bindings (Part C).**

---

## PART A — The ONE packet (assembled from existing law)

A channel never mints a name. It hands the shared core ONE object. That object has three blocks, and all three field-lists already exist in the locked design:

### Block 0 — ENVELOPE (per source event) — from 12 FACT-17b top-level
`source_id · source_type · ticker · fye_month` [+ optional `calendar_override`] · `event_time`
- One CLI invocation = ONE source event (the fusion/collision locality guarantee, FACT-17b).

### Block 1 — IDENTITY SIGNALS (per candidate) — from kernel §2 Stage-0 INPUT
`{proposed_name · slice_tokens[] · measurement_spans[] · per_x · quote · event_time}`
- These are the DECOMPOSITION OUTPUTS (Part B). The kernel Stage-0 consumes them to reuse/create/reject the Driver.
- `slice_tokens`, `measurement_spans`, `per_x` are TRANSIENT signals: the kernel folds per_x into the canonical name (NAME-13), measurement_spans into `fact_scope.measurement` (OD-9), slice_tokens into `fact_scope.slice`. They are NOT stored raw.

### Block 2 — THE PROVEN FACT (per candidate) — from 12 FACT-17b item + 09 fields
`driver_name · driver_state · quote` · value slots `level_low / level_high / change_value / comparison_low / comparison_high / comparison_baseline / value_text / conditions / company_confirmed`
- transients (propose-then-discard): `level_unit_raw / change_unit_raw` · 4 per-slot hints (`level_unit_kind_hint / level_money_mode_hint / change_unit_kind_hint / change_money_mode_hint`) · `level_shape_hint / comparison_shape_hint` · `measurement_raw_spans`
- period fields: `period_start_date / period_end_date / fiscal_year / fiscal_quarter / half / month / long_range_start_year / long_range_end_year / sentinel_class / time_type` (+ `period_scope ∈ {ytd,ttm}` on cumulative)
- `slice` = list of `kind:value` tokens or menu-pick refs
- Code (not the packet) builds: `id · fact_scope · series_unit · created · date` (09 §3 code-written 6).

### Block 3 — OPTIONAL Cat-2 VERDICT (per candidate, only when the fact explains a move) — from 07 DU-21..24
`explained_target ∈ {Event, DailyCompanyMoveEvent} · stock_impact ∈ {long,short} · weightage ∈ {0.1..1.0}|null · confidence ∈ {0..100 deciles} · produced_mode ∈ {live,backfill} · llm_producer`
- Cat-1 vs Cat-2 = birth SITUATION only, never stored (ratified). Cat-2 = this block is present.

### THE UNIFICATION (the one thing to state explicitly — missing-rule #3)
> kernel Stage-0 `evidence_atom` **≡** the Block-2 fact item (FACT-17b).
> So "every new Driver arrives WITH its first proven DriverUpdate" is mechanically ONE object: Block 1 (identity signals) + Block 2 (the proven fact) travel together; the kernel judges identity from Block 1+quote, and on CREATE the SAME packet's Block 2 becomes the driver's first DriverUpdate. This is exactly **born-complete admission** (kernel §5 / OD-7).

**Three consumers, one object:** kernel Stage-0 (Block 1) → reuse/create/reject · Track B writer (Block 2) → write the DriverUpdate · verdict_writer (Block 3) → write EXPLAINED_BY.

---

## PART B — The decomposition procedure (raw channel label → the packet's identity signals)
**This is "the one unbuilt bridge." The RULES all exist; they were never assembled into one ordered procedure. It is CHANNEL-INDEPENDENT (fiscal.ai label AND guidance label_slug run the same steps).**

INPUT: a raw label + context (company, quote, value, period, source, and — if present — the XBRL member).
OUTPUT: `{proposed_name, slice_tokens[], measurement_spans[], per_x}` + `fact_type` + unit.

Ordered (stop-at-first is not the pattern here; each step peels one thing off the label):
0. **Strip direction/impact words** (NAME-11 step 0): rose/headwind/pressure… never in the name (unless a specific reusable force like `glp1_pressure`).
1. **Measurement peel** (NAME-14 / FS-25 / OD-9): pull version/basis qualifiers (adjusted, diluted, constant-currency, core…) into `measurement_spans`. `"Adjusted EBITDA"` → spans=["Adjusted"], residual="EBITDA". Code normalizes spans; producer never invents the token; never assume gaap.
2. **Per-X peel** (NAME-13): a stated per-X denominator → `per_x` (goes IN the name; unit stays base). Not stated → none.
3. **Portion check** (OD-17): a portion qualifier (current / funded / fee-earning…) STAYS IN THE NAME — never a slice, never measurement. `"current RPO"` → name `current_rpo`.
4. **Name-vs-slice split** (NAME-10/11 · OD-3 / 95 #38): for each remaining qualifier, the LOCAL role test (from quote + this company only): own measured part {segment/geography/product/customer/channel/entity_ownership} → `slice_tokens`; external actor/cause or unclear role → stays in the NAME. `"iPhone Revenue"` → iPhone = own product → `slice=product:iphone`, residual "revenue".
   - **Slice KIND source:** XBRL member present → kind from the FROZEN axis table (FS-08/11/18, deterministic, code). Text-only → producer proposes kind via the FS-15 / FACT-26f ladder (menu-match → coin → `unknown:` when ≥2 kinds fit — never guess).
5. **Name assembly** (NAME-05/06/07/08/09 · singular-by-default): cause-only, lowercase_snake, familiar/standard phrases whole, one cause per name, + per_x. `"revenue"`.
6. **fact_type stamp** (DU-05/06/07 · OD-1/OD-2): metric / guidance / surprise / action_event; suffix-gate first, then DU-06 persistence test, C2 metric-proof if unclear. A reported KPI value → `metric`; a company forward outlook → `guidance`. Strong-tier, at admission (born-complete).
7. **Unit** (04 UNIT-01 · OD-10/OD-11 · unit_resolver): unit_raw + hints → 10-unit enum; code stamps `series_unit`.

Then Block 1 + Block 2 go to the kernel/writer.

### AUTHORITY SPLIT (the v1-death guardrail — missing-rule #4)
- **CODE (deterministic, never decides meaning):** format norm, measurement token normalization (OD-9), unit resolution, XBRL-member→slice-kind (frozen table), id/fact_scope build, ALL validators.
- **LLM (proposes the SEMANTIC parts only):** name-vs-slice role test, the cause-only name, a prose slice's kind, fact_type. Per NAME-03/19 + v1's death, the NAME is ALWAYS LLM-proposed — **never code-parsed from the label string** (that IS the closed-vocab death).
- **KERNEL (strong-judge, final identity authority):** reuse/create/reject, SAME_AS, fact_type/BASE_METRIC confirmation, establishment.

### Structured-channel nuance (needs owner confirm — folded into missing-rule #4)
For fiscal.ai T1-xbrl records the member is known → slice kind is deterministic (code). But the cause-only NAME and the name-vs-slice decision for TEXT-only records (T2/T3, ~52%) must stay LLM-propose + kernel-judge. Proposed rule: **code may fill format/unit/XBRL-member-slice; the NAME and any prose slice stay LLM-proposed + kernel-judged. No channel ever code-derives a Driver name from its label.**

---

## PART C — RESOLVED 2026-07-14 (owner rulings + Fable adjudication; supersedes the open list)

**① RULED YES, with the owner's wording correction (binding):** channels NEVER create anything. An authorized channel with real evidence SUBMITS a candidate fact; **the shared core validates it and decides** — through the existing kernel machinery (Stage 0–3, strong-judge tier) AND the experiment gate regime (EXP-0 graders · EXP-3 router · EXP-4 SAME_AS keys · fitness gate) per FableExperimentWorkOrder/Plan. DU-02 amendment wording (for the S6 back-port): "governed channels submit candidate-fact packets; the shared core alone admits/creates; on admission the Driver is created WITH its first fact." Lane nuance preserved: "value + period" required-ness stays the LANE MATRIX's job (numberless guidance legal via value_text; action periods rare) — the envelope never hard-requires them universally.

**② ADJUDICATED (Fable, non-rubber-stamp): born-complete STANDS; general name-only seeding REJECTED.**
- Why factless cards break the design: (a) the frozen birth-anchor machinery (kernel §6.3) judges every SAME_AS/ATTACH against birth QUOTES — a factless card is judge-blind and drift-unpinnable; (b) NAME-18(d) requires ≥1 causal claim with real evidence (locked); (c) "hand-seeded vocabulary" is an explicitly rejected death pattern (kernel §13; RavenPack-import rejection, 95 #14); (d) evidence-free cards pollute reuse retrieval — name-string gravity with no evidence mass = v2's death channel.
- Zero cost to us: every channel record arrives evidence-bearing, so "seeding the catalog" = feeding records through the kernel (each born-complete). The seed IS the fiscal.ai pilot.
- The narrow legitimate need ALREADY EXISTS in law — **latent BASE anchors**: when `revenue_guidance` is admitted before `revenue` has any fact, PIPE-25/OD-1 auto-mints an invisible placeholder base (never claim-eligible, never shown in reuse display, graduates exact-norm on first real evidence). No new machinery.
- If the goal is to SEE the name space early: run the decomposer DRY-RUN over labels (paper output, no catalog writes) — available anytime.

**③ RULED + SPEC: fiscal.ai harvest RECORD design UNCHANGED; the new piece is INGESTION ORDER.**
- Field-for-field the seed record already carries what the packet needs (Part D map; 2 trivial lookups: Report.created → event_time, fye_month).
- The adapter RE-SORTS KPI-major records into SOURCE-EVENT-major packets, submitted chronologically per company. **Unit of submission = ONE SOURCE EVENT** — not one KPI, and not one bare fact (FACT-17b one-invocation-one-event: fusion + collision detection see the whole submission). **CORRECTION (2026-07-14): arrival-together is the OPTIMAL case, not a safety requirement** — cross-time/cross-channel arrivals at the same event are the legislated OD-8 late-collision path; see ⑤.
- The KPI grouping carries ZERO identity authority — provenance only. The kernel judges each candidate item independently; series membership EMERGES at read (FACT-33 series key). This directly answers "seed facts may not truly belong to the same driver": the channel never asserts cross-record identity; record 1 of a series CREATEs (full judgment), later records ATTACH (cheap exact path) — the natural kernel flow, no special casing.
- Same-value multi-source records (8-K + 10-Q restating one number) = separate facts on separate events BY DESIGN; read-time collapse (8k > transcript > 10q > 10k > news) merges the view. No channel-side dedup.
- Bookkeeping: the channel keeps its own ledger (record → submitted item → outcome) for the catch-up cursor; NO new packet fields.

**④ RULED + DESIGN: decomposition is ONE SHARED component — the owner's "if only it were possible" is possible, and it's the minimal design.**
- Channels implement ONLY a thin adapter (Part D): enumerate events since cursor → emit RAW ITEMS. The shared decomposer (one prompt+code stack for ALL channels) produces the standard packet; kernel judges; writer writes. One test surface, one certification, six tenants.
- Robustness = already built: the fail-closed validator suite + park ledger + dry-run default (FACT-16/17) — malformed input cannot enter; every failure returns a machine-readable reason to the submitting channel.
- Honest caveat: one component ≠ one difficulty — a prose claim (learner/news) is harder than a KPI label; per-channel certification (EXP-5-class packet experiments) still required before a channel goes live.

**⑤ CROSS-CHANNEL SAME-EVENT LAW (owner Q 2026-07-14 · answer = existing OD-8 FINAL, owner-approved 2026-07-05 — ZERO new machinery).**
Two channels may hit the SAME source event at different times, for the same or different facts. Safe by three
existing layers, all in the shared writer (below every channel — channels need NO coordination):
1. **Same fact → same id → converge.** The id is code-built and producer-free (event+driver+fact_scope); the
   writer MERGEs in place; FACT-14b fills empties and never null-clobbers. Channel B's level+change item onto
   channel A's level-only node = COMPATIBLE → fill (cross-channel "fusion" via the id).
2. **Different fact, same slot, late arrival → OD-8 write rules run against the PRE-BATCH GRAPH STATE on every
   write** (sibling probe: `id = bare` OR `STARTS WITH bare+"|quote_hash="`): exact → merge; compatible → fill;
   CONFLICT (≥1 shared non-null signature slot disagrees) → **new hashed member + late-collision flag — NEVER
   overwrite** (OD-8 rule 8: signature-slot conflicts never overwrite as "correction"; true corrections only via
   explicit `--repair`). Late collisions are legal history (rule 9); ≤1 bare member per group invariant.
3. **Concurrent race** → equal-signature bare+hashed pair detected free by the next write's probe; reads treat
   equal-signature members as ONE fact (prefer oldest/bare); repair lane cleans (OD-8 rule 9 race pin).
Accepted residuals (all existing, measured): non-signature fields (driver_state, quote) keep last-write-wins
with log — cross-channel disagreement rate is exactly what the §12.5 dual-producer probe scores; WHICH member
holds the bare id is arrival-order cosmetic (reads treat members equally); extraction noise can mint a flagged
sibling — visible, over-split, confined to the collision class.
**Claim scope (narrowed 2026-07-14):** the guarantee is exactly "conflicting values never silently overwrite" —
NOT "over-merge impossible." Identity-level over-merge (wrong SAME_AS/ATTACH, upstream mis-decomposition landing
two facts on one id, same-signature restatement-merge-by-definition) is guarded by the kernel's judges +
falsifier + audits with MEASURED upper bounds — the kernel §16 doctrine: zero-by-construction is impossible;
zero-by-measurement with honest bounds is the enforceable promise.

## PART D — Channel adapter contract v0.1 (all a channel implements; everything else is shared)

1. **SELECT** — watch its source; enumerate new source events since its cursor (birth backfill = same enumeration over history, chronological per company).
2. **FETCH** — per event, emit RAW ITEMS: `{quote (verbatim) · raw_label_or_claim · stated value(s)/unit text · stated period fields · source cadence (the channel's own series membership, e.g. fiscal.ai quarterly-vs-annual — form alone is ambiguous: Q4 stated in a 10-K, FY in an 8-K) · adjacent period wording the locator saw (column header / "as of" phrase — transient evidence; the marker scan + time_type judgment need it when the bound quote lacks the header) · source_id/source_type · optional XBRL (when the record is XBRL-tagged, ALWAYS): concept qname + the EXACT context (start/end dates, instant-vs-duration type) + the dimension list — a VERIFIED-empty list asserted explicitly (`dimensions=[]`; a missed extraction must never masquerade as consolidated), every supplied dimension carrying BOTH axis and member, never fragments; the period row consumes the context verbatim and enrichment/backstop-A consume the concept *[OWNER AMENDMENT 2026-07-15, Q4 batch — pre-amendment bytes pinned in the Phase-1 freeze manifest]* · optional value_text/conditions + company-confirmation attribution EVIDENCE (guidance; the CORE derives the `company_confirmed` boolean, never the channel) *[OWNER AMENDMENT 2026-07-15, Q1 batch extension — same ruling as the ChannelContract guidance row]*}`.
3. **SUBMIT** — one packet per source event; consume per-item machine-readable outcomes into its ledger.

Shared side (core-owned, identical for all six): DECOMPOSER (LLM proposes name / prose-slice kind / fact_type; code does format, measurement normalization (OD-9), units, member→slice via frozen axis — Part B) → kernel Stage 0–3 → writer stack → read views. The adapter MAY memoize ONLY the LABEL-pure decomposition parts (name proposal, per_x, portion, the label's slice-token split) per identical (company, label, member) — and a cached result stays a PROPOSAL: each record's per-quote decomposer pass must confirm the cached proposal is consistent with ITS OWN quote (mismatch → fresh decomposition + flag; a label-matched cache must never sail past a quote about something else). Zero identity authority either way — the kernel judges every admission. QUOTE-dependent parts are NEVER memoized — measurement spans, time_type evidence, driver_state, and the marker scans run against EVERY record's own quote (OD-9's never-drop sink is per-quote by definition).

### D.2 — PRECISE fiscal.ai → packet conversion map v0.1 (owner Q2 2026-07-14)
Every row: exact source → exact transform → failure mode. NOTHING guesses; every ambiguity PARKS (arrival-retry).

| packet slot | exact source | transform (who) | on failure |
|---|---|---|---|
| `source_id` | `filing_id` (accession, e.g. 0000320193-24-000123) | look up the graph Report node by accession; id-safe via `canonicalize_source_id` (':'→'_'). *(Exact Report key property confirmed by one read-only query at adapter build.)* | Report not in Neo4j yet (graph runs ~1 qtr behind fiscal.ai) → **PARK-RETRY**, drains when filing ingests |
| `source_type` | `form` | 10-K→`10k` · 10-Q→`10q` (+ 8-K→`8k` when EX-99.1-sourced records appear in parts 2–4) (code map) | other form → PARK |
| `event_time` | Report.created (PIT stamp) | one Neo4j read per filing (batched per company) | missing → PARK |
| `fye_month` | Company record | one lookup per ticker (cached) | missing → PARK |
| **period** | T1: the matched `xbrl_fact` context (instant/duration + exact start/end) — AUTHORITATIVE, verbatim (~48% deterministic). T2/T3: `period` (end date) + `form` + **the channel's cadence signal** (quarterly-vs-annual series membership; form alone is ambiguous — Q4 in a 10-K, FY in an 8-K) + **raw period wording** (transient evidence for the marker scan/time_type when the quote lacks the header) → fiscal window via `fiscal_math` (52/53-wk safe). **`time_type` (duration vs instant) is a REQUIRED decomposer output — a semantic judgment, NEVER a default** (fixed 2026-07-14; the old "duration default for flows" line was a disguised guess — flow-vs-stock IS the meaning call): judged from label + quote ("amount over a window" = duration: revenue, costs, shipments · "standing amount at a date" = instant: subscribers, stores, backlog, headcount, balances), aided by two hints — (a) the SAME (ticker,kpi)'s own T1 siblings' XBRL period_type (deterministic borrow; conflict → PARK), (b) the substrate `KNOWN_INSTANT_LABELS` list (hint only, per FACT-18: `time_type` stays authoritative). **UNCLEAR → PARK** — and this park HAS real drains (unlike the window-marker case): a later T1 sibling of the KPI, or the driver's concept-link (menu carries `period_type`), resolves it → arrival-retry | code (shared resolver is the sole period authority — FACT-17b) | TWO tripwires, both → **PARK**, never trust either side silently: (a) T1-vs-form mismatch (e.g. 9-month context on a "quarterly" record = YTD leak); (b) **T2/T3 contradicting-marker scan** (added 2026-07-14): an explicit window marker in the quote/snippet ("nine/six months", "year-to-date", "trailing/twelve months", "fourth quarter" on an annual stamp) that contradicts the stamped window. Default derivation stays when no marker contradicts — NOT a guess: the harvest's certified Q-vs-YTD binding (#760 guard, 0 leaks) disambiguated with fuller context than the adapter has, and a no-marker record parked "for evidence" would never drain (nothing new arrives for a text record) = losing certified facts. Wrong time_type NETS (all existing law): the marker scan ("as of" on a duration stamp); concept-link **backstop A = the instant/duration veto** (FACT-29; menu carries `period_type`, FACT-30) — a duration-stamped fact whose driver links an instant concept = flag; FACT-16.15 (start==end duration = illegal input) |
| **unit + value** | `value` = the **source-stated SIGNED value, unscaled** (wording fixed 2026-07-14 — "absolute" meant unscaled/full-magnitude, NEVER math `abs()`; OD-12 signed value-space: losses/negatives stay negative — a demonstrated failure class here: the mini-exam truth int() bug turned EPS −0.2 → 0) + `fmt` + `is_currency` | adapter emits `level_unit_raw` (usd/percent/count from fmt) + `level_unit_kind_hint` (money/ratio/count) + `level_money_mode_hint` (aggregate; price_like only for per-X KPIs) + `level_shape_hint='point'`; shared resolver canonicalizes scale (money → the driver's one scale) — deterministic division, no LLM, **sign untouched**. **Free belt+braces: re-assert `value_ok(value, fmt, quote)`** before submit — SCOPE (2026-07-14): the gate guarantees the number appears in the quote at a numeric boundary, NOT that the binding is the correct KPI/period/slice (binding correctness = the binder+verify pass + per-part sample audits; cf. the 13 coincidental small-value mis-bindings found and removed in Part 1); value_ok's sign handling (parenthetical negatives "(0.2)") verified at adapter build | resolver error (cents-on-aggregate, pre-scaled), value_ok fail, or value↔quote SIGN mismatch → **hard-fail → PARK** |
| **measurement** | qualifier spans, grounded in this priority: (1) the QUOTE (the company's own text) · (2) the label ONLY when tier=T2 (T2 verified the label tokens sit next to the value in the filing) | decomposer copies exact spans → `measurement_raw_spans`; CODE normalizes (OD-9: lowercase → non-alnum runs→`_` → maximal contiguous spans = one token); plain KPIs → empty set (never assume gaap) | label-only qualifier with no quote/tier support (vendor wording, not source) → **PARK** — OD-9 is source-grounded; fiscal.ai's label is a vendor label |
| **slice** | T1: `xbrl_fact` → (axis_qname, member_qname, member label) | `classify(axis)` via the FROZEN table (code): SLICE_AXES → kind + normalized member label, emitted as a MENU-PICK REF (writer attaches MAPS_TO_MEMBER + slice_part free — FS-21); unknown axis → `unknown:xbrlaxis_<hex>__<member>` sentinel; multi-member → code-sort, join ';' | NON_SLICE axis or FS-20 elimination member → **PARK+log** (accounting construct — never silently consolidate, OD-17c) |
| | T2/T3 (no member): the label's own-part qualifier | decomposer ladder (NAME-10/11 local role test) + FS-15/FACT-26f kind ladder vs the company PIT menu: menu-match → pick · prose-clear → coin `kind:value` · ≥2 kinds fit → `unknown:<value>` · whole-company → omit slice | never guess a kind (guessed kind = fake axis-grade confirmation) |
| `proposed_name` | kpi label residual (after measurement/per-X/portion/slice peels) | decomposer LLM proposes (NAME-05..08 canonical coining); NEVER code-parsed from the label string (v1 death) | NAME-18(f/g) vague/ambiguous → SKIP |
| `driver_state` | — | `reported` (DU-09 rule 5: bare stated value, no comparison in a table cell) | quote states a comparison → decomposer judges per DU-09 ladder |
| `quote` | `quote` | verbatim, unchanged | empty → hard-fail (REQ all lanes) |
| channel ledger | (ticker, kpi, period) → submitted item → outcome | channel-local file; feeds the catch-up cursor + recall accounting | — |

Channel abstain-outcome mapping (fiscal.ai bot Q&A 2026-07-14): **vendor-calculated `% Chg` / `Common Size` rows
(~45K, ~62% of the universe) are SKIPPED AS SEED FACTS — never claimed recoverable en masse.** A growth/margin
figure EXPLICITLY STATED by the source ("revenue grew 12%") is a DIFFERENT fact and enters through the normal
stated path; otherwise growth/margins stay read-time calculations from stored levels (store-when-stated; the
`calculated` class is a DROP, 09 §5). Same for other fiscal.ai-COMPUTED rows (balancing plugs) → terminal SKIP,
counted · corpus_missing (filing not in Neo4j) →
PARK-RETRY · value-absent on a text record → SKIP **only after the expected source set for that company-period
(10-K/10-Q + earnings 8-K EX-99.1) was PRESENT and actually searched, with zero extraction errors** — an
incomplete search is corpus-incomplete → PARK-RETRY, not a skip. Value-absent SKIPs re-open on THREE triggers
(not just a new source class): (a) a new source — instance (late/amended filing) or class (transcripts added);
(b) a repaired corpus (a re-extracted/fixed section that was corrupt at search time); (c) a CERTIFIED locator
upgrade (precedent: the header-capture fix closed a 91%→100% binding gap — earlier locator versions missed
values later ones find; "certified" = passed the locked regression/A-B regime, no re-scan on uncertified tweaks). **The channel ledger
records a per-company-period source-completeness + extraction-status STAMP; SKIP is legal only against a clean
stamp** — auditable, not merely procedural. **COST NOTE (not a design blocker):** 8-K press releases state
rounded values, so exact-value yield from EX-99.1 packets will be limited — 10-Q/10-K remain the exact-value
backbone; PR packets add early availability only where they match.

**HONEST NUMBERS:** every precision figure quoted in this program so far belongs to a COMPONENT — the relocation
engine's certs (e.g. 97.2% pooled mini-exam) and the binder's sample audits. **END-TO-END seed → decomposer →
kernel → writer precision is UNMEASURED**; measuring it is exactly what the fiscal.ai pilot's pre-registered
gates are for (amendment A1). No component number may be quoted as the system number.

Guidance channel note: NO conversion map exists or is needed for old GuidanceUpdate rows — Track C law forbids
production replay; the guidance channel is FRESH extraction from source docs, so its "map" IS the decomposer
output spec. Old rows serve only as pilot/EXP test inputs.

---

## Worked examples (metric + guidance)

- **fiscal.ai "iPhone Revenue" (AAPL, $201,183M, FY2024, 10-K, member=IPhoneMember):**
  decomp → measurement=∅ · per_x=none · portion=none · name-vs-slice: iPhone=own product → `slice=product:iphone` (kind from frozen axis, member present) · name=`revenue` · fact_type=`metric` · unit=`m_usd`.
  packet → Block1{proposed_name=revenue, slice_tokens=[product:iphone]} + Block2{metric fact: level_low=level_high=201183, level_unit=m_usd, quote="iPhone $ 201,183", period FY2024}. Born-complete: first DriverUpdate rides in.
- **fiscal.ai "Adjusted EBITDA":** measurement peel → spans=["Adjusted"], name=`ebitda`, measurement=`{adjusted}` (the exact 95 #2 retired-defect class — proves the decomposition works). NOT `adjusted_ebitda`.
- **guidance label_slug "adjusted_ebitda" (old Neo4j regime):** SAME decomposition → name=`ebitda`, measurement=`{adjusted}`, fact_type=`guidance`. Confirms decomposition is channel-independent (guidance channel must run it too; old label_slugs are raw labels, not names).
<!-- END INTERNAL V1 -->
