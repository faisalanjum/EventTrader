# FISCAL ↔ CORE V2 — THE CHANGE-AND-TEST LIST (for review; NOTHING implemented)

Test half is FINAL below — it follows only from rulings already given, so it
does not wait on the contract. Change half is a SKELETON: every row is marked
with what the contract must confirm before a line is edited.

Rulings this is built on (orchestrator, 2026-08-10):
- the four retiring fields leave the ITEM allowlist; `{part, content}` records
  live at the EVENT level, never per item;
- removing `level_unit_raw` removes Fiscal's GUESS, not the scale risk — Core
  now owns that check, so the end-to-end double-scale tests STAY;
- missing XBRL is NOT an automatic park: for text facts the QUOTE is the
  authority; unit unclear → `unknown`; required scale wording missing → extend
  the quote or abstain;
- Qwen is entirely out of scope.

## A. THE CHANGE LIST (skeleton — no edits until the contract lands)

| # | Change | Confirm from contract |
|---|---|---|
| A1 | Drop `level_unit_raw`, `level_unit_kind_hint`, `level_money_mode_hint`, Fiscal's defaulted `level_shape_hint` from the item shape | exact final field set + whether `comparison_shape_hint`/`change_*` hints follow |
| A2 | Remove the same four from `public_contract.py:_ALLOWED` — it is a STRICT fail-closed allowlist, so this is required, not cosmetic | — |
| A3 | Add event-level `{part, content}` records = the exact text shown to the reader | key name, ordering, whether `part` is an enum |
| A4 | Keep UNCHANGED: signed displayed `value`, `fmt`, `is_currency`, `quote`, `period_evidence`, all raw `xbrl` evidence | that none are renamed in V2 |
| A5 | Connect the existing filing provider + XBRL evidence to Core's single V2 attachment door | the door's exact entry signature |
| A6 | NOT done by Fiscal: build Core's 32 meaning fields · guess unit/scale · duplicate Core's validation | — |

Surface (contract-edit only, NOT the full Fiscal-owned set):
`scripts/driver_seed/build_packets.py` (143 ln, 8 funcs) ·
`scripts/driver_seed/public_contract.py` (54 ln, 2 funcs).
The full import closure gets derived when the contract arrives, before the
later move to `driver/channels/fiscal_ai/`.

## B. THE TEST LIST — FINAL, failing-first

### B1 Regression: the 11 saved XBRL packet items still work
`data/driver_catalog_seed/wp3_ce_compliant/packets.jsonl` — 1 event, 4 items
`data/driver_catalog_seed/wp3_aci_stream/packets.jsonl`  — 3 events, 7 items
All 11 currently carry all four retiring fields, so they ARE the removal's
regression set. Assert: same values, signs, periods, quotes, XBRL evidence;
only the four fields absent.

### B2 Text path
- exact event text reaches Core as `{part, content}`;
- **zero XBRL access** on a text event (assert the provider is never called);
- **text-currency SUCCESS**: quote carries unit + scale, reader supplies both,
  and `unit_scale_evidence` is a verbatim string that **OCCURS INSIDE the
  quote** — assert containment, not mere presence;
- **non-adjacent scale**: the scale wording sits in a caption above the value →
  the quote is EXTENDED to cover it contiguously, and the containment assert
  still holds (this is the case the orchestrator ruled on 2026-08-10);
- **missing-scale ABSTENTION**: the wording cannot be brought inside the quote
  → abstain. Never stitched, never invented;
- **RED — evidence not in the quote**: a `unit_scale_evidence` string that is
  NOT a substring of `quote` is REFUSED (this is the fabricated-quote class,
  #824, arriving through a new door);
- unit unclear → `unknown` (a distinct outcome from both park and abstain).

### B3 XBRL path
- exact concept, period, dimensions, scale and source evidence all reach Core;
- **`unit_scale_evidence` IS NULL** on every XBRL fact — Core proves scale from
  the verified `ix.scale`, `unit_ref` and bound source evidence (pieces
  included), never from a text string;
- **RED — a non-null `unit_scale_evidence` on an XBRL fact is REFUSED**: the two
  paths must never borrow each other's proof;
- **scaling happens exactly once** — end-to-end, now proving CORE's guard;
- wrong scale → fails;
- wrong dimensions → fails;
- bad hash → fails;
- valid siblings → pass (not mistaken for drift).

### B4 Whole-run invariants
- no graph writes anywhere in the suite;
- no AI calls;
- `public_contract.to_public` stays pure + repeatable;
- an item carrying BOTH old and new spellings, or NEITHER, is refused.

## C. CLOSED — ruled 2026-08-10 (orchestrator)
`unit_scale_evidence` is a SEPARATE verbatim string that **must occur inside
the quote**. So option (1) stands as drafted: extend the quote contiguously to
cover the scale wording, and abstain when it cannot be. Nothing is stitched, so
`ChannelContract:34/67` and #824 are honoured by construction — the containment
check IS the anti-fabrication guard.

On the XBRL path the field is NULL and scale is proved from `ix.scale` +
`unit_ref` + bound source evidence. Two paths, two proofs, no borrowing.
Both are tested (B2, B3). No open rulings remain on this item.

## D. ORDER OF WORK (his, unchanged)
contract → mismatch report vs live V2 code (NO edits, never modify Core) →
full Fiscal caller/test inventory from live imports → failing tests first →
minimal changes → B1–B4 green → THEN the move to `driver/channels/fiscal_ai/`
as a separate move-only change → rerun everything.
STOP before: the live V2 switch · AI calls · Neo4j writes · commit · push.
