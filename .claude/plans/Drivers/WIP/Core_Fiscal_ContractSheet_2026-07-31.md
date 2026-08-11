# Core ↔ Fiscal contract sheet (#827 step 7)

One small, diffable sheet. It records what each side owns at the boundary as
the staged component stands today. **It edits nothing of Fiscal's and nothing
in `FinalDesign/`**, and it grants no approval: the Fiscal migration, the
atomic switch remain held; the EPS/per-X naming decision is RULED (2026-08-11, uniform spell-out).

Derived from the live code at commit `4d473822` plus this task's staged
changes — every name below is a real symbol, not a description of one.

## 1. What Fiscal sends, per event item

| key | meaning |
|---|---|
| `fact` | the PreparedFact payload (`fact_type`, `part_ref`, `occurrence_in_part`, `per_x`, `item`) |
| `concept` | the XBRL concept the item claims, e.g. `us-gaap:Revenues` |
| `member_refs` | the claimed `{axis, member, slice_part}` triples, `[]` when the fact is dimensionless |
| `source_evidence` | the four-key filing evidence (§2) |

Exactly those four keys — `xbrl_attach._EVENT_ITEM_KEYS`. An unknown key, a
missing key or a non-dict item is a CONTRACT rejection, never a crash.

**Event-level `text_parts`**: a sequence of `{part, content}`
(`_TEXT_PART_KEYS`) — the event view the model actually read. It is supplied
once per event, not per item.

## 2. `source_evidence` — exactly four keys

`inline_html.SOURCE_EVIDENCE_KEYS`:

| key | contract |
|---|---|
| `representation_sha256` | SHA-256 of the PREPARED text of the filing, taken at HARVEST time |
| `quote_span` | `[start, end)` — half-open, CHARACTER offsets into that prepared text |
| `raw_label_span` | `[start, end)` inside the quote span, or null |
| `pieces` | ordered list of `{kind, text, span}` |

`pieces` order is CARRIED, never chosen: aligned headers near→far, then the
single optional section. `kind` ∈ `('header', 'section')`
(`inline_html.PIECE_KINDS`); each piece's `span` must reproduce its own `text`
exactly. Core compares the sequence exactly; nothing may reorder it.

## 3. The filing provider

`filing_provider.get_filing_document(source_id)` → the filing document text.
Injected by the caller; Core never fetches. A channel with no XBRL supplies no
XBRL event at all — Core does not synthesise one.

## 4. What Core owns

- the graph XBRL representation COUNT for the source, and the company CIK —
  read from CORE's graph, never from the provider;
- row binding: concept + period + the COMPLETE dimension set;
- unit compatibility — `xbrl_attach.candidate_units_for`, which now lives in
  Core because the production caller census says Core is its only caller; the
  shared binder applies no candidate policy of its own;
- the exactness storage law (`slot_convert`);
- the filing period boundary: `exact_numbers.parse_filing_boundary` with
  `filing_boundary_graph_start` / `filing_boundary_graph_end` /
  `filing_duration_ordered`. BOTH boundaries are parsed: `xs:date` and
  `xs:dateTime`. A START means midnight of its own day, so no day is added.
  An END means the following midnight — but ONLY a date-only end adds a day;
  a `dateTime` end already IS the instant and adds none, so `2023-06-30` and
  `2023-07-01T00:00:00` are the same end and bind the same graph date. (The
  earlier wording here said every end adds a day, which is true of neither the
  law nor the code.) A duration must run FORWARDS,
  and a comparison that would need an invented timezone is indeterminate and
  parks; a timezone is never invented, a time never truncated, sub-microsecond
  precision and the calendar edge park rather than round or overflow;
  `<forever>` parks under its own named reason, never "malformed";
- **the LEXICAL admissibility of every joined name and id** (#827 round 7b).
  Core validates, and never repairs, on BOTH sides of the join:
  * an inline fact's `id` and a graph `fact_id` must be a lawful XML ID (an
    NCName). Stated once in `inline_html.element_evidence`, the door the binder
    and the locator share, so neither caller carries its own copy;
  * a concept `name` must be a QName whose prefix THIS document declares —
    checked in `_evidence_from`, the one funnel both the exact-id path and the
    identity-fallback path reach;
  * **blankness is XML 1.0 S (`" \t\r\n"`), never Python's `.strip()`**, which
    also consumes U+000B, U+000C, U+00A0 and U+3000. Blank means "this element
    carries no id" and selects the identity fallback; whitespace XML does not
    call space is a MALFORMED id, not an absent one. The same set decides the
    row identity in `xbrl_attach._row_signature`.
  Measured before shipping: 0 of 2,308,263 document fact ids, 0 of 13,775,616
  graph `fact_id`s and 0 of 13,775,616 graph `qname`s are refused; the only
  cost is 2 document concept names in one filing that carry a literal newline
  inside the attribute, which never matched a graph string and so never bound.
- every DECISION.

## 5. The five decisions, and nothing else

`xbrl_attach.PUBLIC_DECISIONS = ('written', 'merged', 'parked', 'skipped',
'rejected')`. `<forever>` and other lawful-but-undatable source values park
with a named detail — they never add a sixth word.

Each outcome row carries the item's ORIGINAL INDEX, its `codes`, and a
`detail`. Default codes (`_DEFAULT_CODES`): `SlotConversionError` →
`NOT_STORABLE`; `SourceUnavailable` → `SOURCE_UNAVAILABLE` (retryable —
`RETRYABLE_SOURCE_ERRORS` is the `OSError` family, so the caller may retry);
`SchemaError` → `XBRL_CONTRACT_INVALID` (a contract breach — do NOT retry);
`ProductionValidationError` → `XBRL_BINDING_UNAVAILABLE`.

## 6. What Core returns

`AttachResult(source_id, facts, preflight_outcomes, member_menu)`:
- `facts` — `(original_index, PreparedFactV2)` pairs, input order preserved;
- `preflight_outcomes` — the outcome rows, sorted by index, `()` on success;
- `member_menu` — EXACTLY two keys, `{folds, exclusions}`, deeply frozen;
  `exclusions` are the adapter's own audit, CARRIED once per concept and never
  recomputed. (This read `{folds, exclusions, ...}`; the trailing `...` invited
  a reader to expect an open-ended map, and a consumer written against that
  would be written against a contract the code does not offer.)

An item-local failure never erases a lawful sibling.

## 7. Still switch-gated (nothing here is approved by this sheet)

- Fiscal's own mapping onto these keys, and the `source_id` handoff;
- registering the CLI codes on the live path;
- deleting v1 (`prepared_fact.py`) and the duplicate rule engine;
- the Fiscal migration and the atomic switch (the EPS/per-X naming decision is RULED, 2026-08-11: uniform spell-out).

Fiscal receives this sheet after #827 acceptance and before the migration.
Neither side implements from a partly reviewed draft.
