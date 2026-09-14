# SOURCE_CONTEXT_PROOF_2127

The minimal source-context wording renderer, implemented and verified at the
real seam. Codex SEQ 2127. No call, no key or candidate mutation, no grading,
no publication, no call preparation.

## What was built

`a7_source_context_2127.py` — one module, two public entries (`served_prefix`,
`provenance`). It takes the prefix `a4_source_taskv2` already builds and
replaces exactly ONE anchored span, using that module's own
`_replace_once` helper. It reads no fact, no answer, no finding and no grade;
its output is a pure function of the prefix it is given.

The inserted wording is Codex's approved sentence pair, unchanged:

> The target fixes which fact you review. For each permitted field, use the
> complete supplied source unless that field's rule restricts it to the quote,
> then apply the governing rules in their stated order.

It is wrapped to the width the served paragraph already uses (measured 84–87
on the live prefix), and a test asserts the wrap changes whitespace and no
word. The span anchors on the existing sentence `Interpret those targets only.`
plus the first line of the split cap, and that line is quoted from
`a4_source_taskv2.SPAN_A_NEW` rather than retyped, so a reworded owner makes
the anchor miss and this module refuse.

## What is verified

Proof run `core_ctx2127_c`, raw exit 0,
`SOURCE_CONTEXT_PROOF_2127.json` `5a584fc1408a29060987118075c226c5bc02e86c053f537d221acef878961528`.

| check | result |
|---|---|
| the prefix served today lacks the clarification, at the real seam | both events: **absent** |
| installed, the clarification is served exactly once | both events: **1** |
| exactly one span changes; every other byte identical | **true**, both |
| the `[INPUT]` body is byte-identical | **true**, both |
| with the install HELD, a nested prior-round read renders its recorded prompt | **byte-exact**, all 3 rounds |
| every recorded raw answer unchanged | **true** |

Install shape: the seam swap is held for ONE call, the way `a4_source_closeout`
installs `a4_source_taskv2`. That is what keeps it current-only — the three
historical rounds re-derive their recorded prompt hashes with the install
active. The seam already installed is captured before the swap; reading the
live attribute inside the replacement recurses forever, which I hit and fixed.

### Tests, both sides, asserted not merely recorded

The proof asserts the exit pattern `1, 0, 1, 0` and fails if it differs.

| suite | subject | exit | summary |
|---|---|---|---|
| `test_source_context_2127` | prefix served today | 1 | `FAILED (failures=1)` — the RED, on "the source-context sentence is served 0 times, not once" |
| `test_source_context_2127` | the candidate | 0 | `OK` — 12 of 12 |
| `test_prefix_spans_2063` | prefix served today | 1 | `FAILED (failures=3)` — its own documented RED |
| `test_prefix_spans_2063` | the candidate | 0 | `OK` |

The 12 focused tests: the RED; the missing-clarification statement; exactly one
span changed; every other served section byte-identical; the served wording is
the approved wording word for word; the renderer is a pure function of its
base; four anchor refusals — absent, duplicated, drifted, already-inserted —
each run after an intact positive control; a reworded split-cap owner makes the
anchor miss; and the key declaration over the real permitted body keys.

The declaration test builds its key sets **from the prefix's own declared keys
at run time** — the real set, a single-key set, the reversed set, and the real
set extended with unseen names derived from it — so unknown supported payload
values are data, never written-out cases.

Raw stdout and stderr of all four suites are kept beside the proof JSON and
hashed in it. I read them rather than the totals: the RED fails on the intended
property, and each of the twelve green tests is named in the raw output.

## The tenth state error

`SOURCE_DISPOSITION_ADDENDUM_2127.json`
`85d65d653045c6dd4e73c3b62fa9ac970b286a1eea595961b4e4ed8302e0be62`.

`0000027904-26-000020#021` moves from supported to **needs independent source
correction**, state required `increased`. Codex is right and the refutation is
inside my own 2126 evidence: sentence 42 is the Adjusted `1Q26 1Q25` table
carrying `Diluted earnings per share 0.64 0.45 0.19 44 %` — same driver, same
adjusted measurement, same quarter, prior and change stated — and sentence 100
independently carries the non-GAAP reconciliation for both quarters with the
same change. My 2126 note claimed only a GAAP per-share prior exists; that was
wrong. The cause was a truncated READING, not a truncated search: my targeted
probe required the measurement word within a fixed distance of "per share", and
the table header carries it far earlier.

Counts after the addendum: **25 supported, 10 needing independent source
correction, 0 unresolved**. The affected source set is **unchanged at seven** —
this event was already in it.

## What still awaits the root's history connection

Everything about running the corrections. This report verifies the wording
renderer only. Still outstanding and not begun here:

- the root's chronological-signature / cold-resume fix and its verified
  identity, which I did not touch and must not edit;
- the combined freeze of the seven-source call packet, which is the root's to
  assemble from the two verified pieces;
- any call preparation or collection, which is not authorised yet.

## Scope

Files written, all in `unit_2127_source_context`: the renderer, the focused
tests, this report, the proof JSON with the four suites' raw output, the
disposition addendum, and `probe_anchor_2127.py` — the read-only measurement
that established the anchor is unique and the clarification absent before any
of this was written. Nothing else was touched: the 2121 owner,
`unit_2020_codex_check`, the frozen 2063/2065/2069 prompts, the completed 2123
calls and every earlier report remain byte-identical.
