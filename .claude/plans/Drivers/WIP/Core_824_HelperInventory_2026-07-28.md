# #824 — the "eleven dead helpers": the record, and the correction

**Taken:** 2026-07-28 · **Status:** the original claim was WRONG and is retracted here.

## What I reported, and why it was wrong

While auditing #824 I reported "eleven other dead helpers" in `driver/`. That
came from a scan that counted only **bare-name calls** (`ast.Name`) and ignored
**attribute calls** (`XN.eq(...)`, `IH.find_by_identity(...)`, `mod.fn(...)`),
which is how most of this tree calls across modules. It is the same crude-check
habit logged repeatedly in this programme, and it produced a list of things that
are not dead at all.

Re-run counting BOTH call forms, `driver/` contains **zero** dead production
helpers. Nothing on that list should be deleted, and none of it is #826/#827
work.

## The eleven, individually, with real call counts

| helper | file | call sites (any form) | disposition |
|---|---|---|---|
| `row_quote` | `driver/relocation/locator.py` | 43 | **LIVE** — no action |
| `value_ok` | `driver/relocation/locator.py` | 33 | **LIVE** — no action |
| `eq` | `driver/relocation/exact_numbers.py` | 6 | **LIVE** — no action |
| `plain` | `driver/relocation/exact_numbers.py` | 7 | **LIVE** — no action |
| `is_instant` | `driver/relocation/exact_numbers.py` | 3 | **LIVE** — no action |
| `find_by_identity` | `driver/relocation/inline_html.py` | 1 | **LIVE** — no action |
| `validate_via_production` | `driver/core/prepared_fact_v2.py` | 2 | **LIVE** — no action |
| `pfact` | `driver/relocation/test_locator_routes.py` | 0 | test-local, unused; **#826** cosmetic |
| `outcome_of` | `driver/core/test_driver_writer.py` | 0 | test-local, unused; **#826** cosmetic |
| `store` | `driver/core/test_neo4j_adapter_readonly.py` | 0 | test-local, unused; **#826** cosmetic |
| `_outcome` | `driver/core/test_round10_event_boundary.py` | 0 | test-local, unused; **#826** cosmetic |

Only the last four are genuinely unreferenced, all are TEST-local, none is
production, and removing them changes no behaviour. They are recorded for #826
housekeeping rather than deleted mid-#824, because deleting test scaffolding on
the strength of a static scan is exactly what produced the wrong list above.

## What WAS deleted in #824, and why that was safe

| helper | file | reason |
|---|---|---|
| `door_evidence` | `driver/core/test_round10_event_boundary.py` | superseded by `filing_evidence`, the one fixture builder |
| `_sha_of` | `driver/core/test_v2_attacks.py` | superseded by the lawful-evidence path |

Both were verified to have zero callers in ANY form before removal, and the full
suite is green after it.

## The standing lesson

A call-graph claim built from `ast.Name` alone is not a call-graph claim. Any
future minimality sweep in this repo must count attribute calls, `getattr`
usage, and `__all__` exports, or it will report live code as dead — which is a
far more expensive mistake than missing a dead function.
