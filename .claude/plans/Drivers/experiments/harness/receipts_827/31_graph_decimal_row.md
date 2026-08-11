# 31 — GRAPH-DECIMAL: the graph number reader is XSD decimal, not a project grammar

**Row:** GRAPH-DECIMAL (#827) · **Authority:** XSD 1.0 §3.2.3 decimal, reached
through Arelle's pinned `decimalPattern`, plus the runtime's own canonical
grouped formatting · **Reviewer ruling:** Codex SEQ 925 (option a, with the
exact boundary), amended by SEQ 927, reachability cleared by SEQ 929.

## The defect

`driver/relocation/inline_html.parse_raw` gated graph values on a
project-authored regex, `_GRAPH_NUMBER`:

```python
_GRAPH_NUMBER = re.compile(
    r'-?(?:0|[1-9][0-9]{0,2}(?:,[0-9]{3})*)(?:\.[0-9]{0,2}[1-9])?\Z')
```

It filtered **presentation**, not numeric correctness. It refused exact finite
numbers — `1234`, `12345.6`, `0.0001`, and even the writer's own `1,234.50`
(a trailing fraction zero) — purely on spelling, while its own docstring
conceded the accepted language rested on "corpus evidence … compatibility, not
legality". A parser that carries digits, sign and point through untouched
cannot defend correctness by refusing digits.

## The rule now

A graph value READS when it is **either**:

1. an **XSD decimal** — Arelle's pinned `decimalPattern`. There is **no
   project-authored production regex**; the standards owner is reused; or
2. an **exact canonical grouped transport form** — comma-bearing text that
   round-trips exactly through the runtime's own grouped formatting at the
   input's stated precision.

A value that is **neither** refuses. The writer's habits and the corpus census
are compatibility evidence only, never legality, and never a reason to refuse a
spelling. `decimalPattern` must run BEFORE the exact finite-number owner because
`Decimal()` is not a lexical gate: it reads underscores (`1_0` → 10), full-width
and Arabic-Indic digits, exponents, Infinity, and sNaN.

## Proof — public path, pinned environment

| check | result |
|---|---|
| Pass 2 battery (mine) | lawful 14/14 accepted · hostile 26/26 refused · million-digit ok |
| Pass 2 battery (Codex, independent) | 55/55 |
| affected regression, 7 files | 881 passed, 0 failed |
| focused RED (`_GRAPH_NUMBER` reinstated in-process) | the lawful-respelling tests **FAIL** — they pin the fix |
| lawful control under the same mutation | the different-number refusal **still passes** — the arithmetic gate is untouched |

Probes: `~/.core827_backups/graph_decimal_pass2_full.py`,
`graph_decimal_red_control.py`.

## Live population, read-only

Full `Fact.value` population, 13,775,616 rows
(`graph_decimal_live_census.py`, artifact sha `dd04aa39…`):

| | count |
|---|---|
| accepted now | 12,464,276 |
| newly accepted (old grammar refused it) | 48,453 |
| refused now | 1,311,340 |

Refusal reasons: non-numeric text 320,927 · accounting parentheses 268,420 ·
XBRL duration/recurring date 248,946 · whitespace padding 222,984 ·
boolean/null 178,255 · other 39,983 · ISO date 31,723 · empty 100 ·
non-ASCII digits 2. Exponent and non-finite are **0**.

> A first classifier tested `[eE]` before testing for letters, so ordinary text
> ("Yes", "true", "December") was counted as an exponent and that bucket read
> 632,696. The order is fixed and the numbers above are the corrected pass.

## Reachability — the number that decides it

The census denominator is too broad: production filters before the reader ever
runs. Both live sources — `scripts/driver_seed/route_a_source.py:28` and
`driver_neo4j_adapter.get_xbrl_fact_dimensions` — require exactly
`f.is_numeric='1' AND f.is_nil='0'`.

Joined on that predicate (`graph_decimal_reachability.py`, artifact sha
`f53b4294…`):

| | count |
|---|---|
| accepted **and reachable** | **12,402,201** |
| accepted but excluded upstream | 62,075 |
| **newly accepted AND reachable** | **0** |
| **refused AND reachable** | **0** |
| newly accepted, all excluded | 48,453 |
| refused, all excluded | 1,311,340 |

**Both zeros are the finding.** No reachable numeric value lost recall, and no
newly-readable value entered the numeric path. The 48,453 additions are
four-digit years (`dei:DocumentFiscalYearFocus`, `us-gaap:OpenTaxYear`, …)
carrying `is_numeric='0'`, so they never reach numeric reconciliation. The
reachable population is exactly the long-standing 12,402,201, unchanged.

The old regex survives only inside the two scratch probes as comparison
evidence bound to the prior T. It is not production authority and no production
module can import it.

## Stale authority text closed

`graph_row_contract.py` value bullet · `inline_html.py` grammar block and
`parse_raw` docstring · `xbrl_attach.py` value comment and prose ·
`locator.py` call comment · `test_bind_graph_fact.py` Round-6 header, paren
docstrings and door table · `test_round12_exact_scale.py` preamble and
negative-scale paragraph · `test_round10_event_boundary.py` docstring ·
`test_v2_attacks.py` docstring. Surviving `_GRAPH_NUMBER` mentions are past
tense and explicitly corrected. Unrelated bool/unit/date/hash clauses untouched.

Two tests renamed to stop asserting a dead authority:
`…_outside_the_derived_grammar_is_refused` →
`…_a_value_NEITHER_XSD_decimal_NOR_grouped_transport_is_refused`, and
`…_every_form_the_graph_actually_stores` → `…_every_lawful_graph_number_input`.

Ten cases moved refused → MUST-ALLOW. The refusal battery still holds 27
genuine cases, the door keeps both real aliens (full-width digits, accounting
parentheses), and a control that did not exist before was added: same lawful
spelling shape, genuinely different number, must still refuse.
