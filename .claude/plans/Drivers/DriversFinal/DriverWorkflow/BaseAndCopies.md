# Base + copies (cached Claude reading)

**What it is:** load a document into Claude once (the "base"), then run copies that reuse it from cache. Each copy sees the whole document without paying to read it again. Used by step 3 of the [shared creator](SharedCreator.md).

## How to run it

- **Size:** count real input tokens (instructions, IDs, images) and leave room for reasoning and output. Never silently cut or compact evidence. Copies can't fix an oversized source: use a capable approved reader or report the limit (no automatic partial-view fallback).
- **Copies:** one reader needs no loading call. For several: load material + rules once, get a brief base reply, then run `claude -p --resume BASE_ID --fork-session` per assignment, always from the original base so answers never pile up.
- **Same settings:** pin the exact model version (an alias isn't a pin), prefix, effort, tools, instructions and folder; a different model/effort needs its own warmed base. Limit parallel copies; inspect cache fields. Tested copies kept cache for 1 hour; expiry means a fresh read, not lost history.
- **Billing:** subscription sign-in only, no API key or provider fallback, paid overage off. Cached input still fills context and uses quota; output, reasoning and retries cost too. No routine second pass or mandatory Jev/Qwen stage.

## What we tested (12–13 Nov 2026)

| Test | Result | Limit |
| --- | --- | --- |
| Cache test (Codex): AMG 8-K, 1 base + 25 copies, short quotes | 97% of input read from cache; same speed (~3.3 s each) and same answers as without cache; subscription only | tiny task (~17K tokens); usage meter only rough (+4 vs +10 points) |
| Mechanics (Fable) | 12 copies at once worked; a fixed system prompt also reuses (~96%); cache doesn't carry across models | expiry timing not measured |
| AMG extraction: 6 copies vs partial views vs 1 call | whole view 297/297 numbers in 33 s; partial views 293/297 (wrong cells); 1 call 297/297 in 115 s | one press release; numbers only |
| Autodesk 10-K: 1 / 4 / 12 readers | 12 readers 4× faster, slightly fewer numbers (520 vs 532 of 533), ~24% more cost | owner-reported; one run each |
| IBP 10-K: 1 / 4 / 12 readers | medium effort sometimes returned empty tables or hit a safety stop; 12 readers at high got all 1,366 table numbers; 4 readers at high got 143/150 sentence numbers | owner-reported; 1–2 runs each |

**Not tested:** full Driver facts, real image understanding, cache expiry, retries, steady throughput, exact subscription savings, more than 3 documents.

## Still open

Baseline: 1 reader, medium effort. Large-filing trial candidate: 4 Sonnet 5.5 readers, high effort (not proven best). Assignment sizes and other efforts are untested; don't routinely run both medium and high.

## Evidence

- Raw data: [Experiments/2026-11-12_base_and_copies_claude/](Experiments/2026-11-12_base_and_copies_claude/): `context_cache_probe` (Codex's cache test), `context_reader_followup` (review of Fable's first run), `fable_reader_tests_…_local` (Fable's raw runs, kept local, not in git).
- Full write-ups: [cache test](archive/DriverWorkflow_History.md#complete-independent-cache-experiment-record) · [follow-up review](archive/DriverWorkflow_History.md#complete-follow-up-experiment-review) · [Autodesk](archive/DriverWorkflow_History.md#reported-autodesk-10-k-reader-comparison) · [IBP](archive/DriverWorkflow_History.md#reported-installed-building-products-10-k-follow-up) · [all evidence](archive/DriverWorkflow_History.md#reference-only-evidence-and-history)
