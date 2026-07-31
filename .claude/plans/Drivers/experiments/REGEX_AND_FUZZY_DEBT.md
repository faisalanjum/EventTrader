# Regex / fuzzy-matching debt register — Driver experiments

> **Read this BEFORE editing any tool listed below.** Audited 2026-07-25 by
> grepping every `.py` under `experiments/harness/`. This is a *register*, not a
> work order: nothing here is scheduled. Each entry says what the pattern does,
> whether it is legitimate, and what to do when that tool is next touched.
>
> **The governing rule** (owner, P0): keep in CODE only what is provably correct
> across ALL unseen examples. Mechanical normalisation is fine. A pattern that
> *decides meaning* — a hidden word list, a similarity score — must be handed to
> the model instead, because it silently misfires on the universe it never saw.
> A green test suite does not clear it: our own samples are not the universe.

## The test that classifies every entry

| Kind | Example | Verdict |
|---|---|---|
| **Mechanical** — same answer for every input, no judgment | `re.sub('[^a-z0-9]+','_')` slugify · `^kp_\d+$` id format · extracting a path from a log line | legitimate, keep |
| **Semantic** — guesses what text *means* | "is this a per-share metric?" · "does this text contain money?" · "are these two quotes the same fact?" | must go to the model |

---

## A. EXP-5 exam path — 2 known, both already scheduled for deletion

These are tracked in `WORKORDER_STATUS.md` under the v2.1 work; listed here only
so this register is complete.

| File:line | Pattern | Kind | Disposition |
|---|---|---|---|
| ~~`scorers/score_exp5.py:186`~~ | ~~`_overlap(a, b, n=20)`~~ | **Semantic** | ✅ **DELETED 2026-07-25.** Replaced by `_ev_key()` — exact evidence identity (`evidence_locator`, else exact quote equality). Substring containment is no longer a match. The gate test asserts it stays deleted. |
| `scorers/fact16_checks.py:24` | `_NUMY` regex: `[$€£¥]\s?\d | \d+%  | bps | million|billion|thousand` — "does this text contain a number?" | **Semantic** | DIES with the duplicate-validator removal (v2.1). A hand-written money detector cannot generalise (no €/£ variants beyond these, no "crore", no "bn", no "1,5" decimal comma). |

## B. Other tools — NOT in the EXP-5 exam path

Untouched by the current work. When you next edit one of these, handle its row.

### B1. ⚠️ ONE genuine semantic word list — review before reuse

| File:line | Pattern | Why it matters |
|---|---|---|
| `xbrl_dryrun_materializer.py:40` | `PERSHARE_HINT = re.compile(r'pershare\|earningspershare\|(^\|[^a-z])eps([^a-z]\|$)', re.I)` | Guesses **"is this concept a per-share measure?"** from its NAME — a hidden word list. Misses unseen spellings (`PerADS`, `PerDilutedShare`, per-LP-unit) and false-positives on any name containing `eps`. |

**RECONCILED 2026-07-25 — earlier records were WRONG about what it does.** Some
notes described it as *"skip + count"*. It does **NOT** skip: the single use
(`:209`) only increments a diagnostic counter,
`ctr['usd_bare_pershare_suspect'] += 1`, and execution continues to
`convert_value` regardless. It is **diagnostic-only today** and changes no
outcome. Verified: `driver/` never imports this module, so it is outside the
`run_event` path entirely.

**FORBIDDEN — promotion into runtime.** This pattern must never move into a path
that decides identity, units, or triggers a write. If per-share-ness is ever
needed at runtime, take it from **declared XBRL units** (the unit ref / the
`iso4217:USD` + shares denominator already present on the fact) or from the
**Driver's own expected unit** — both are declared facts, not guesses about a
name. A rename of this counter or a new caller is a review trigger.

### B2. ⚠️ Structural risk — the same normaliser copied three times

| File:line | Pattern |
|---|---|
| `xbrl_dryrun_materializer.py:83` | `re.sub(r'[^a-z0-9]+','_', s.lower()).strip('_')` + `re.sub(r'_+','_')` |
| `xbrl_xxl0_verifier.py:42` | `v_slug()` — same logic, retyped |
| `build_fa_inputs.py:14-15` | same logic, retyped again |

Each copy is individually **mechanical and legitimate**. The risk is DRIFT: three
independent implementations of one rule can diverge silently — exactly the class
of bug that produced the `FIELDS37` duplication and the `_is_num`/`_dec` split
(both real defects found 2026-07-25). **When touching any of these, replace it
with the production normaliser** `driver.core.driver_ids.norm` rather than
editing a copy.

### B3. ✅ Mechanical — no action needed

| File:line | Pattern | Note |
|---|---|---|
| `xbrl_dryrun_materializer.py:153,155,158` · `period_convention_probe.py:57` | `form.startswith('10-K')` / `'10-Q'` | Form codes are a closed official set. **One thing to verify if touched:** prefix matching also captures amendments (`10-K/A`). Confirm that is intended rather than incidental. |
| `dualcik_scope.py:90` | `k.startswith('slice_')` | Internal key prefix, not source text. |
| `key_lint.py:34,197,260` | `_TOK=[a-z0-9]+` tokeniser · `^kp_\d+$` id format · `startswith("STRATA"/"ABORT")` on our own error codes | Format/id checks on strings we generate. |
| `key_lint.py:96` | `name_exact_equal` — casefolded EXACT equality | Equality, not similarity. Legitimate. |
| `audit_worker_access.py:29` | `_INPUT_RE` — pulls a `draft_inputs/*.json` path out of a transcript line | Parsing our own log format. |

*(`key_lint.py` serves the K-pairs answer key — a DIFFERENT key from K-fields. Do
not confuse it with `harness/kf_lint.py`.)*

---

## Bottom line

- **EXP-5 exam path:** after the two v2.1 items land, it contains **zero**
  semantic pattern-matching — only exact identity (locator), exact numbers
  (Decimal), and production's own validators.
- **Everything else:** one genuine word list (`PERSHARE_HINT`), one duplication
  risk (three slugify copies), and the rest mechanical.
- **Nothing here is urgent.** It is a register so the next person does not have
  to re-derive it — and does not accidentally promote a probe-grade heuristic
  into a path where it could decide identity or trigger a write.
