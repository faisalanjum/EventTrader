# 27 — Caller inventory (receipt evidence, one-off measurement)

**What this is.** A measured list of every call site of the locator/matcher
entry points, so the "dormant surface" claim can be checked instead of
believed. It is EVIDENCE, not a lint: nothing in the tree enforces it, and it
is re-measured when the code changes rather than left running as a rule.

**It corrects an earlier claim of mine.** The #827 decision log said these
entry points have *"NO active non-test caller"*. Measured precisely, that is
**wrong as stated** — see the correction at the bottom.

---

## Method

`ast`, **binding-aware**. A call counts only when the name it goes through was
bound by an import of the owning module. A first attempt matched call names
directly and "found" callers in `websockets/version.py` and
`more_itertools` — different functions that merely share a spelling. That is a
grep dressed as a parse, and it would have produced a confident wrong number.

Excluded: `.git`, `archive/`, `node_modules`, `__pycache__`, `site-packages`,
and every `*venv*` directory (vendored third-party code is not this repo).
"Non-test" means the file's basename does not contain `test`.

---

## Result

| entry point | call sites | non-test | non-test inside `driver/**` |
|---|---:|---:|---:|
| `driver/relocation/locator.py::locate` | 70 | **2** | 0 |
| `driver/relocation/locator.py::match_facts` | 3 | **2** | 0 |
| `driver/relocation/locator.py::match_facts_explain` | 9 | 0 | 0 |
| `driver/core/fact_match.py::match_facts` | 17 | 0 | 0 |
| `scripts/driver_seed/locate.py::locate` | 11 | 0 | 0 |
| `scripts/driver_seed/locate.py::locate_by_value` | 5 | **1** | 0 |
| `scripts/driver_seed/locate.py::locate_by_fingerprint` | **0** | 0 | 0 |
| `scripts/driver_seed/relocate_probe/xbrl_lane.py::resolve` | 9 | **1** | 0 |

### The six non-test call sites, in full

| caller | callee |
|---|---|
| `scripts/driver_seed/wp3_compliant_packet.py:54` | `locator.locate` |
| `scripts/driver_seed/wp3_compliant_packet.py:92` | `locator.locate` |
| `scripts/driver_seed/relocate_probe/xbrl_lane.py:50` | `locator.match_facts` |
| `scripts/driver_seed/relocate_probe/xbrl_lane.py:54` | `locator.match_facts` |
| `scripts/driver_seed/locate.py:129` | `xbrl_lane.resolve` |
| `scripts/driver_seed/run_code_tier.py:230` | `locate.locate_by_value` |

Each was opened and read; all six are live calls in ordinary control flow, not
comments, strings or dead branches.

---

## CORRECTION to the #827 decision log

The log recorded:

> `locate.locate` / `locate_by_fingerprint` / `xbrl_lane.resolve` /
> `match_facts` have **NO active non-test caller**. The only production entry
> is `run_code_tier.py:230 → locate.locate_by_value`.

Two things were wrong, and the second explains the first.

1. **It conflated two different modules that share function names.**
   `locate_by_fingerprint` and `locate_by_value` do **not exist** in
   `driver/relocation/locator.py` at all — they are defined only in
   `scripts/driver_seed/locate.py`. The production module's public surface is
   `rebuild_anchor · seg_parse · at_boundary · row_quote · value_forms ·
   bounded_hit · exact_form · printed_negative · value_ok · match_facts_explain
   · match_facts · locate`. Likewise there is no `driver/relocation/xbrl_lane.py`;
   `xbrl_lane` exists only under `scripts/driver_seed/relocate_probe/`.

2. **"No active non-test caller" is false.** There are six, listed above.

**The accurate statement**, which is what the earlier one was reaching for:

> No entry point above has a non-test caller **inside `driver/**`** — zero, for
> every one of them. Every live caller sits in the seed/probe layer under
> `scripts/driver_seed/**`. Exactly one function is called from nowhere at all:
> `scripts/driver_seed/locate.py::locate_by_fingerprint`.

That distinction matters for the ruling built on it: "dormant" was true of the
production package and not of the repository, and a decision to delete or
narrow any of these must account for the six seed-layer callers rather than
assume there are none.
