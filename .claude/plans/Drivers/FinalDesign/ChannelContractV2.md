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
