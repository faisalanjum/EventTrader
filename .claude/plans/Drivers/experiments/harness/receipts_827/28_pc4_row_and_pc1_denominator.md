# PC-4 new row + PC-1 denominator movement — retained evidence

Recorded per reviewer SEQ 858. Both movements are visible, not silent.

## 1. Denominator: 263 -> 264 (PC-4 enters under Contract §9)

PC-4 is a DISTINCT proof-mechanism defect, not part of PC-1. The staged/live
gate helper `live_modules_importing_staged` decided its question with a raw
substring scan over file TEXT (`if mod in src`), so a module name appearing in
a comment or docstring counted as an import.

Measured on the candidate, the gate reported four live->staged edges. Three
were prose:

| reported edge | truth (AST) |
|---|---|
| driver_validators -> prepared_fact_v2 | prose only |
| graph_row_contract -> xbrl_attach | prose only |
| outcome_codes -> xbrl_attach | prose only |
| driver_validators -> slot_convert.CANONICAL_UNITS | **real**, required by closed C1+C10 |

Core's SEQ 711 repeated the gate's four-leak output without independently
checking the detector. The reviewer's AST re-measurement corrected it; Core
reproduced that correction before acting on it.

Fixed at the existing helper: it reads `Import` / `ImportFrom` nodes. The one
lawful edge is declared at SYMBOL granularity, so an alias of CANONICAL_UNITS
passes while a second slot_convert symbol, the whole module, a star-import, or
the same symbol from another live module all fail.

  commit 9ba82271 · STAGED_PATHS unchanged · no wrapper, no new module

## 2. PC-1 cardinality: 1 -> 6 (SAME row, measured denominator moves)

The card named one allowlist entry and claimed that made the gate green. The
gate's own ast-walk flags six. Reviewer ruling SEQ 858: PC-1 remains ONE row;
the five extra names do NOT become five new rows, because all six answer the
same proof question and all six derive from already-closed #827 owner rows.

| symbol | owner row | kind, re-checked at close |
|---|---|---|
| split_terminal_suffix | W3 | pure fn — `endswith`, `len` |
| sha256_hex_ok | W4 | pure fn — `re.fullmatch`, `isinstance`, `bool` |
| NUMERIC_FIELDS | T7 | static tuple literal |
| LANE_STATES | T8 | static dict literal |
| PERIOD_ITEM_KEYS | P-O10 | static tuple literal |
| PERIOD_TIME_TYPES | F-PERIOD owner | static tuple literal |

Why a top-of-file reading found one and the gate finds six: 13 of the module's
19 `driver.core` imports are function-local.

  commit cfcaec7d · allowlist 18 -> 24 names · no production file touched

## 3. Closing state

  PC-4  9ba82271   gate reaches check 3, fails only on PC-1's six
  PC-1  cfcaec7d   gate node GREEN, attacks green (5 passed)
  PC-3  0bed8f03   corpus-pinned node retired, 3 synthetic owners green

  harness suite 6 failed -> 5 failed / 110 passed; the node that turned IS the
  gate. The five remaining reds are pre-existing and unrelated.
  driver battery 2780 passed / 1 failed / 1 skipped (standing s4 pin).
  XBRL porcelain 0. No production code touched by any of the three rows.
