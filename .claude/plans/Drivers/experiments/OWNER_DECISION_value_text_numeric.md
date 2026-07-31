# OWNER DECISION REQUIRED — `_VALUE_TEXT_NUMERIC` (the last semantic regex in production)

> **Status: RULED 2026-07-25 — Option A APPROVED, with ownership the owner
> specified. Implementation lands with the run_event wiring; the regex is
> UNCHANGED until then.**
>
> **The ruling, precisely (and it corrects my write-up):** code enforces
> numeric-slot / `value_text` **mutual exclusion** — that is a necessary
> structural rule, *not* a proof of numberlessness, and I must not claim it is.
> The **model** decides whether the prose is genuinely numberless. **Hidden
> grading must ATTACK** the gap by planting numeric prose inside `value_text`
> with all numeric slots null. **Uncertainty ABSTAINS** rather than guesses.
> Together those four carry the law; the structural check alone does not.
> Surfaced 2026-07-25 by the `run_event` dependency audit — it could be neither
> silently kept (banned pattern class) nor silently deleted (it enforces real
> law), so it went to the owner.

## What the audit found

**CORRECTED 2026-07-25:** this section first reported a **12-module** closure.
That was produced by a walker filtering `if "driver" in module_name` — a name
heuristic, not real imports — which silently dropped `guidance_ids` and its
transitive tree. Following ACTUAL imports, the closure is **37 modules**. The
finding below is unchanged in substance (still exactly one semantic regex in
production), but the extra modules were audited too: `guidance_ids` (slugify,
whitespace, numeric-token split, XBRL count matcher), `utils` (XML entity
escaping) and `xbrl_reporting` (`<[^>]+>` tag stripping) — all MECHANICAL.

Within the core Driver modules there are **six** regexes. Five are FORMAT validators and
are unambiguously legitimate (they check the shape of strings *we* generate):

| Where | Pattern | Checks |
|---|---|---|
| `driver_ids.py:25` | `^[A-Za-z0-9._\-]+$` | source_id charset |
| `driver_ids.py:26` | `^[a-z][a-z0-9_]*$` | driver_name format (NAME-05) |
| `driver_ids.py:27` | `^gp_(ST\|MT\|LT\|UNDEF\|<dates>)$` | period id format |
| `driver_ids.py:28` | `^[0-9a-f]{64}$` | sha-256 shape |
| `driver_ids.py:29` | `^xbrlaxis_([0-9a-f]+)__([a-z0-9_]+)$` | our own sentinel format |

**The sixth is different** — `driver_validators.py:59`:

```python
_VALUE_TEXT_NUMERIC = re.compile(
    r"[$€£¥]\s*\d|\d+(?:\.\d+)?\s*%|\d+\.\d+|\b(?!(?:19|20)\d\d\b)\d+\b")
```

It answers a **meaning** question about text nobody has seen: *"does this
qualitative phrase secretly contain a number?"* That is the same class as the
exam's `_NUMY` regex we are retiring, and the same class as the `PERSHARE_HINT`
word list — patterns that decide semantics and therefore misfire silently on the
universe they were never tested against.

## Why it exists (the law it enforces)

`FINAL_DESIGN.md:244` — *"`value_text`: guidance-only, **numberless-only**,
normalized, ≤200 chars, **rejects stored numeric values**, allows date/period
anchors."*

So the requirement is real: `value_text` is the **qualitative** slot. A number
belongs in `level_*`/`change_value` where it is exact, canonicalised, and
comparable. A number smuggled into prose would be invisible to every numeric
check we have.

## Where it will misfire (why this is not theoretical)

The pattern is a hand-built list of number shapes, so it inherits every gap of
one:

- **Non-Latin / spelled-out numerals** — "revenue roughly **doubled**",
  "**half** of last year", "**ten** percent" pass as numberless.
- **Currencies outside `$€£¥`** — "₹500 crore", "CHF 20", "R$ 30" pass.
- **Continental decimals** — "1,5 %" is not `\d+\.\d+`.
- **False positives on lawful prose** — the `\b(?!19|20\d\d)\d+\b` arm rejects
  any bare integer, so "Q3", "top 5 markets", "our 3 segments", "Section 401(k)"
  are flagged as numeric even though they carry no measured value.

So today it **both** lets real numbers through **and** blocks lawful qualitative
text — precisely the silent, sample-invisible failure the generalisation rule
exists to prevent.

## The options

| # | Option | Effect | Cost |
|---|---|---|---|
| **A** | **Model decides, code verifies** *(recommended)* — the reader already states whether a fact is numberless (it fills `level_*` or leaves them null). Code then enforces the LAW mechanically: **if any numeric slot is populated, `value_text` must be null** — an exact structural check, no text pattern at all. Delete the regex. | Removes the last semantic regex from production; the rule becomes provable on all unseen input | The prose itself is no longer scanned — a number written into prose *while all numeric slots are null* would pass. Mitigated by the exam's own value/shape accuracy bar and adjudication |
| **B** | Keep the regex, accept the known misfires | Zero work | Retains a pattern we can prove wrong on ordinary inputs (₹, "doubled", "top 5"); contradicts the standing rule |
| **C** | Keep it as a **report-only** warning (never REJECT) | Keeps a signal without blocking lawful text | Two mechanisms for one rule; still a semantic pattern in the path |

**My recommendation: A.** It is strictly smaller code, it is exactly the
"structure, not string-guessing" boundary you set, and it converts an
unprovable heuristic into a rule that holds for every unseen filing. The residual
risk (prose numbers with all slots null) is a *meaning* judgment — which belongs
to the model and the graders, not to a regex.

**RULED (see the banner).** Option A approved with ownership split four ways —
code enforces mutual exclusion, the model judges numberlessness, hidden grading
attacks the gap, uncertainty abstains. My original framing above ("the residual
risk is mitigated by the accuracy bar") was too weak and is superseded by the
explicit grading-attack + abstention requirements. The regex stays UNCHANGED
until the run_event wiring implements the ruling; the gate carries it as
semantic debt with that disposition until then.
