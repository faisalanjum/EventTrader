# News Extraction Profile

Per-source profile for Benzinga news items. Loaded by the extraction agent when `ASSET = news`.

## Asset Metadata
- sections: full
- label: News
- neo4j_label: News

## Data Structure

News is a flat, single-node source. There are no child content nodes and no hierarchical sections.

### Node Fields

| Field | Type | Description |
|-------|------|-------------|
| `n.id` | String | Canonical news ID (`bzNews_*`) |
| `n.title` | String | Headline text. Populated for all current News nodes. |
| `n.body` | String | Full article body. Empty on a meaningful minority of items. |
| `n.teaser` | String | Short summary. Supplemental text when present. |
| `n.created` | String (ISO) | Original publication timestamp. Use as the public point-in-time unless the type-specific contract says otherwise. |
| `n.updated` | String (ISO) | Latest revision timestamp. May be newer than `created`. |
| `n.url` | String | Canonical article URL. |
| `n.authors` | String (JSON array) | JSON-encoded list of author names. |
| `n.channels` | String (JSON array) | JSON-encoded Benzinga channel list. Routing hint only; not a truth source. |
| `n.tags` | String (JSON array) | JSON-encoded tag list. Editorial metadata, often sparse. |
| `n.market_session` | String | `in_market`, `pre_market`, `post_market`, or `market_closed`. |
| `n.returns_schedule` | String (JSON object) | JSON-encoded schedule for `hourly`, `session`, and `daily` return windows. |

### Relationship Context

News nodes usually carry contextual `INFLUENCES` edges:
- `(:News)-[:INFLUENCES]->(:Company)` - exactly 0 or 1 company in the current graph; there is one companyless outlier.
- `(:News)-[:INFLUENCES]->(:Sector)` - nearly universal.
- `(:News)-[:INFLUENCES]->(:Industry)` - nearly universal.
- `(:News)-[:INFLUENCES]->(:MarketIndex)` - almost universal; a small number of nodes lack macro context.

Use these edges for routing and context, but treat the article text as the authority for who said what.

### Current Graph Notes

- `title`, `created`, `updated`, `url`, `authors`, `channels`, `market_session`, and `returns_schedule` are populated on all current News nodes.
- `body` is empty on roughly 10% of current News nodes.
- `teaser` is supplemental summary text; the current graph does not show a `teaser-without-body` pattern.

---

## Content Fetch Order

### Step 1: Load the News payload

Use query 6A for a specific item. It returns the full flat payload needed by most extraction types.

### Step 2: Use discovery queries when batching

- Query 6B: all company news in a bounded date range
- Query 6C: optional channel-filtered slice with caller-supplied channels
- Query 6D: influence context by ID
- Query 6E: optional market-session slice

Channel selection and fulltext search terms are type-specific. Use query 6C for channel-based narrowing and common query 9F for News fulltext recall when a type defines those strategies.

### Step 3: Read the text fields in this order

1. `title` - always inspect
2. `body` - inspect when non-empty
3. `teaser` - use as supplemental summary; do not assume it adds distinct content beyond title/body

### Revision Semantics

- `created` is the publication timestamp.
- `updated` is revision metadata. Ingest preserves the newest title/body/teaser based on `updated`, while metadata fields are refreshed on every write.
- If a type needs point-in-time disclosure timing, default to `created` unless that type explicitly models revisions.

---

## Period Identification

News nodes carry no explicit fiscal-period fields. If a type needs period semantics, derive them from article text plus company context.

### Common Period Expressions in News

| Source Text | period_scope | Derivation |
|-------------|-------------|------------|
| "Q2 revenue" | quarter | quarter from text; fiscal year from text or company/FYE context |
| "full year 2025" | annual | fiscal year from text |
| "FY25" | annual | fiscal year from text |
| "second half" | half | half from text; fiscal year from surrounding context |
| "next quarter" | quarter | derive from `n.created` plus company/FYE context |
| "by 2027" | long_range | target year from text |

### given_date

Always `n.created` (the publication timestamp). This is the default point-in-time stamp for when the article became public.

### source_key

Use `"title"` as the canonical News document key. If a type tracks finer provenance, distinguish headline/body/teaser via its `section` field rather than changing the document key.

---

## Source Interpretation Traps

- News is a mixed-attribution source. Company statements, analyst commentary, reporter framing, and third-party quotes can appear in the same item.
- `channels` and `tags` are routing hints, not acceptance rules.
- Relationship context is useful but not sufficient for extraction attribution.
- The News node carries no embedded fiscal-period fields. Any period semantics must be derived from text by the type-specific logic.

---

## Empty Content Handling

| Scenario | Action |
|----------|--------|
| `title` non-empty, `body` empty, `teaser` empty | Process title only |
| `title` non-empty, `body` non-empty | Process title + body; use teaser only if helpful |
| `title` empty, `body` or `teaser` non-empty | Process available text fields |
| `title`, `body`, and `teaser` all empty | Return `EMPTY_CONTENT\|news\|full` |

---
*Version 1.3 | 2026-03-09 | Added minimal type-neutral source identity and period-expression guidance (`given_date`, `source_key`, common News period patterns). Kept channel selection, keywords, and write semantics out of the asset profile.*
