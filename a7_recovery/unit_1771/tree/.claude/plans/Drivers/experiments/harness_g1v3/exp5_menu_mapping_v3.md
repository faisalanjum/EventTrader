# EXP-5 menu mapping v3 (COMPLETE — FOR REVIEW; owner ruling O-3 + reviewer refinements)

> Recomputed 2026-07-24 on the 36 frozen packets, BOTH measures recorded
> accurately (correcting my round-20 conflation):
> - `unknown:` sentinels = **81.2% of menu ENTRIES** (3,810 / 4,692)
> - `unknown:` sentinels = **95.0% of menu CHARACTERS** (416,233 / 438,058)
> The readable axes (geography · product · segment · entity_ownership · channel ·
> customer) are the other ~5% of characters. The opaque bulk is the code
> sentinel `unknown:xbrlaxis_<lowercase-hex-qname>__<normalized_member>`
> (FINAL_DESIGN.md:174). Base packets stay FROZEN; a pinned model-VIEW carries a
> DECODED, readable menu while the exact hidden token survives for mapping.

## 1. Two representations, one bijection

| layer | form | who sees it |
|-------|------|-------------|
| hidden token (frozen) | `unknown:xbrlaxis_<hex>__<member>` / `product:iphone` | never the model |
| display (view) | ONLY what the token actually carries, e.g. `[m07] product — iPhone` (known axis) / `[m41] <hex-decoded axis qname> — <member value>` (unknown axis) | the model |
| ref | `m07` | model cites in `slice_parts` |

HONEST DISPLAY (reviewer point — corrected; the frozen input contains NO human
labels). The builder shows ONLY content that already exists in the token:
- KNOWN-axis tokens (`geography:…`, `product:…` — ~5% of chars) already carry a
  readable `axis:value`; shown as-is.
- UNKNOWN-axis tokens (`unknown:xbrlaxis_<hex>__<member>` — ~95% of chars): the
  member VALUE is already readable and is shown; the axis is a HEX ENCODING of
  the source qname (FD:174), so it is DETERMINISTICALLY hex-DECODED back to that
  qname (reversible `bytes.fromhex`, NOT a lookup, NOT a hash) and shown as a
  technical axis name. These are the exact qname + member from the token — the
  view NEVER invents a friendly/human label the frozen data does not have.
The exact original token stays ONLY in the hidden `ref → token` map. (If a qname
does not usefully decode, the member value alone is shown; the model still
judges FS-15 on the readable member.)

## 2. Ref grammar (deterministic; no dates/randomness)

- Refs `m01…mNN`, zero-padded to the event's token count, assigned in the
  packet's existing `menu_tokens` order.
- Token uniqueness asserted per event (duplicate → build FAIL).
- Display line = `[mNN]  <axis>  —  <member value>`, where `<axis>` is the
  verbatim known axis or the hex-decoded qname for an unknown axis (§1). Nothing
  is shown that is not derivable from the token itself.

## 3. One-to-one expansion law (code side, mechanical)

- `"mNN"` in `slice_parts` → the exact original token → the production
  `(kind, value)` pair. Bijective per event; an unknown/malformed ref → lint
  FAIL, never a nearest-match snap. No filtering (every token is listed), no
  guessing.
- The FS-15 four outcomes the model may emit (C7): a menu ref · a clear
  source-grounded off-menu coin (`product:iphone` — kind clear) · `unknown:<value>`
  (kind unclear) · omit (whole-company). Off-menu coins and `unknown:` literals
  pass through VERBATIM — code never rewrites them.
- Empty `slice_parts` = unsliced (legal). A slice the model cannot resolve is an
  `abstentions[]` entry, never a fabricated ref.
- Expansion runs in normalization, BEFORE `PreparedFactV1.from_dict`.

## 4. Pinning

`view_manifest.json`: per event {source_id, base_packet_sha256 (from the frozen
manifest), ref_count, decoded_view_sha256 per role}, + the card sha + builder
version. Two consecutive builds must be byte-identical (the launch-manifest
generator's two-build proof). The launch manifest binds workers to VIEWS
(inline; the access-audit expectation = ZERO file reads per worker).

## 5. Scope

Gold drafts and producer output cite refs; the LOCKED KEY stores the EXPANDED
original tokens (keys outlive any ref renumbering). Ref tables live only in
views; grading compares expanded tokens. Structured XBRL dimensions
(`member_refs`) are code-owned and never pass through this menu — see the
scope-boundary note in `exp5_scoring_spec_v3.md` §8.
