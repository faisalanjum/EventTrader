# Qwen local inference — the single Qwen ledger and runbook

**Owner-facing status line: 2026-08-20. Qwen runs no Driver role today. It is not
authorized for the unfinished Step 1 run.**

---

## 1. Start here

Read in this order, completely, before any Qwen work:

1. `AGENTS.md` (repository root) — communication rules, scope discipline, evidence rules.
2. **This file**, top to bottom. It is the only *current* Qwen-specific document.
3. `config/local_llm.py` — the live client. Read the code, never trust a summary of it.
4. `.claude/plans/Drivers/FinalDesign/LeftOverSteps/Steps.md` §"Model-neutral AI-task rule"
   and §"First-release model ruling" — the authority that governs whether Qwen may run at all.
5. `.claude/plans/Drivers/FinalDesign/LeftOverSteps/promptStandard.md` — how prompts are built.

Every other Qwen README, handoff, runbook and investigation note is **historical evidence
only** and must never again be read as a current instruction. They are indexed in §15.

This file does not define Driver meaning. Each task's frozen packet is the meaning owner.
When doing real work, still open the exact live code, the frozen task packet and the named
result files; this ledger points at them, it does not replace them.

---

## 2. Current status — 2026-08-20

**Proven (development evidence, opened keys — diagnostic, not certification)**

| Suite | Result | Date |
|---|---|---|
| choice_v2 table cell choice, 93 cases | 93/93, precision 1.0 | 2026-08-16/17 |
| choice_v2 compact encoding, 93 cases | 93/93, precision 1.0, 5.3 min | 2026-08-17 |
| row_v3 row selection, 93 cases | 93/93, precision 1.0 | 2026-08-16 |
| qf01 aligned 5x50 contract, 19 set-calls | 19/19 (scorer emitted the historical label `QWEN_ONLY_QUALIFIED`) | 2026-08-17 |
| Identity judge, K-pairs v1.3, 160 pairs | 157/160; 0 wrong-SAME; gate PASS | 2026-08-17 |
| Reader EXP-2 proxy, 10 of 40 chunks | either-recall 50.0% vs Sonnet 45.3% | 2026-08-17 |

**Inactive** — no Qwen model is running any production or experiment role. Nothing is
scheduled. A model was **last recorded** resident on the Mac so that a future authorized run
would not pay a cold load. Whether it still is, is **UNKNOWN** until a read-only preflight
checks it.

**Blocked** — the client performs **no genuine pre-call token check** (§7, §13.1). Until a
later task measures the final frozen prompts and chooses the smallest safe pre-call check,
no run may accept an input near the capacity limit.

**Planned, not started** — one temporary, read-only transport check on the frozen K-fields
196-item packet: measure every exact prompt, report which fit the conservative safe limit,
and draft the smallest `L.generate()` adapter. Awaiting the packet paths and hashes from
Codex.

**UNKNOWN** — the 196-item packet paths, hashes and prompt sizes. A stale 168-item packet
exists and must not be used.

**Explicit next action:** wait for Codex to supply the frozen 196-item packet paths and
hashes. Take no other Qwen action.

**Parallel-work trigger (Codex ruling, 2026-08-20).** Qwen may begin working in parallel
**immediately after A4** — that is, once the detailed answer key **and** the Sonnet baseline
are independently locked. **Verify this; do not assume it.** A4 is complete when a locked key
and its lock file appear in `.claude/plans/Drivers/experiments/keys/K-fields/`, in the shape
`K-pairs.v1.3.jsonl` + `.lock.json` and `K-reader.v3.jsonl` + `.lock.json` already use. As of
2026-08-20 that directory holds only `protocol.md`, `drafting_wrapper.md`, `draft_inputs/` and
`draft_inputs.hashes.json` — **no key, no lock**, so the trigger has not fired.

Once it fires, in this order:

1. fix **and prove** the oversized-input pre-call blocker (§7, §13.3–13.4);
2. build the thin local adapter (§6);
3. run only the final prompts that fit the conservative safe limit (§7).

The standing prerequisites are not superseded by the trigger: the frozen 196-item packet and
its hashes must arrive first — never the stale 168-item packet — and a temporary read-only
transport check must measure every exact prompt before anything is built.

**Qwen is not currently authorized for the unfinished Step 1 run.** No diagnostic result
below changes that.

**Authority reminder:** under the 2026-08-14 first-release ruling, every still-unrun model
call in Steps 1–13 is Sonnet 5 at high effort. Qwen enters a role only through a later
owner ruling plus its own one-role-at-a-time qualification. A passing diagnostic does not
activate Qwen anywhere.

---

## 3. Machine ownership

**Minisforum `faisal@192.168.40.73` owns everything that is work.** Codex, Core, the
repository, all code, all harnesses, all documentation and all results live there.

- Development and experiments happen first in the shadow tree
  `/tmp/qwen38_bench/EventMarketDB` — a copy of the repo. After an independent review, the
  exact accepted code and its regressions may run in the real repository; exploratory or
  unreviewed work never does.
- The harness interpreter is `/home/faisal/EventMarketDB/venv/bin/python`.

**The Mac serves Ollama inference and nothing else.** Only these belong on the Mac:

- Ollama itself and its launchd plist `~/Library/LaunchAgents/com.faanjum.ollama.plist`;
- which model is resident, keep-alive, and parallelism;
- the autossh reverse tunnel that exposes `localhost:11434` on the Minisforum.

Mac scratch files are disposable. **No repository work happens on the Mac** — see §13.11,
where the old Mac-side exam recipes are retired.

Server environment — **last recorded** on 2026-08-17 from the plist, **not verified live**.
Every value below (plist contents, resident model, keep-alive, parallelism and the tunnel) is
**UNKNOWN until a read-only preflight confirms it**:

    OLLAMA_HOST=0.0.0.0:11434
    OLLAMA_NUM_PARALLEL=1
    OLLAMA_LOAD_TIMEOUT=30m
    OLLAMA_KEEP_ALIVE=-1
    OLLAMA_MAX_LOADED_MODELS=1

Apply changes with `launchctl bootout` then `bootstrap`. `launchctl kickstart -k` does not
reload environment variables. Restarting Ollama drops the whole prefix cache.

**Conditions for a long batch run on the Mac** (measured, and they matter):

- **Keep other apps light.** With the model resident (about 19–29 GiB depending on context)
  the Mac swaps heavily when much else is open; swap was 95% full on 2026-08-17 and 22.9 GiB
  during the 2026-08-18 capacity probe, which dropped prefill from the usual 95–110 tok/s to
  83. On a freshly restarted, idle machine decode reached 34.3 tok/s (2026-08-19).
- **Sleep the display.** Display sleep was disabled (`pmset displaysleep 0`) and the display
  stack was eating most of the adapter: charging went from 142 mA to 1,781 mA after
  `pmset displaysleepnow`. Run `pmset displaysleepnow` before a long batch.
- **Gate on battery.** Under GPU load the battery drains about 2%/min even while plugged into
  the undersized adapter, and identical calls ran up to 3.5x slower once the battery fell to
  5–16%. Batch jobs must be resumable and battery-gated, and every reported timing should
  carry a battery reading.

---

## 4. Allowed repository paths

A Qwen change may touch only:

1. `config/local_llm.py`
2. `.claude/plans/Drivers/FinalDesign/QwenTests/qwen38_optimization/`
3. `.claude/plans/Drivers/FinalDesign/LeftOverSteps/QwenInference.md` (this file)

No other path in the working tree may enter a Qwen change. The owner's working tree carries
unrelated modifications, so stage only the **exact, independently reviewed, changed files**
inside those three roots — by explicit path, never a whole directory, never `git add -A` or
`git add .`.

Staging, commit and push require a later explicit completion review (§14). The pre-migration
file was untracked; this ledger will be tracked when landed.

---

## 5. Single supported client

`config/local_llm.py` is the only local entry point. No other transport, wrapper, provider
SDK or compatibility layer may be introduced.

    path    config/local_llm.py
    sha256  836e5722ec01c5e1ef53b8eeb2675beb4fcb58d9e10b22570afc3c00daf80b66
    lines   388
    (hash verified 2026-08-20; re-verify before every run and record it)

The module contains no API key, no provider SDK and no external endpoint. `resolve_host()`
tries `LOCAL_LLM_HOST`, then `http://CA-K429CXLGF9.local:11434`, then
`http://192.168.40.147:11434`, and raises `ConnectionError` if none answer. That is host
resolution on the LAN, not provider substitution; there is no fallback arm.

**Freeze and record per run**, because every one of these can be changed by environment
variable or by the server (§13.8). The values below are **last recorded, not live** — resolve
them at run time:

| Identity | Where it comes from | Last recorded value |
|---|---|---|
| model | `LOCAL_LLM_MODEL` | `qwen3.8:27b-mlx` |
| host | `LOCAL_LLM_HOST` / mDNS / IP | resolved at call time |
| thinking default | `LOCAL_LLM_THINK` | `0` (off) |
| num_ctx default | `LOCAL_LLM_NUM_CTX` | `32768` |
| timeout default | `LOCAL_LLM_TIMEOUT` | `1800` s |
| Ollama version | server | `0.32.13` |
| engine / quant | server | MLX engine, nvfp4, dense 27.8B, arch `qwen3_5` |

A second model was **last recorded** on the server: `qwen3.8:27b-mtp-q4_K_M` (GGUF Q4_K_M). It
grammar-enforces a `format` schema, which MLX does not, at roughly 3x slower decode. Only
one model is resident at a time (48 GB machine). Switching models is a frozen-runtime
change and needs its own record.

Do not casually upgrade Ollama. 0.32.14 changes Qwen system-message handling; priming and
every suite result would need re-verification.

---

## 6. Exact graded-call contract

Use only `L.generate()`. Pass the frozen prompt and system text through unchanged.

```python
from config import local_llm as L

text, stats = L.generate(
    prompt,                    # the frozen packet prompt, byte-for-byte
    system=SYSTEM_TEXT,        # the frozen system text, or None if the packet has none
    think=False,               # explicit; the env default is not trustworthy
    temperature=0.0,           # explicit
    num_ctx=NUM_CTX,           # explicit, fixed for the entire run
    max_tokens=MAX_TOKENS,     # explicit, positive, fixed
    timeout=1800,              # explicit
    retries=0,                 # explicit; the default is 2 (§13.1)
    with_stats=True,
)
```

**Every one of those arguments is passed explicitly.** Defaults are unsafe or
environment-controlled.

Forbidden in a graded call:

- `structured()` — it rewrites the prompt, strips fences and retries (§13.2);
- `fast()` and `reason()` — extra wrappers; `reason()` turns thinking on;
- `format=` — a schema-behaviour difference from the comparison arm, and MLX does not
  enforce it anyway;
- any added instruction, altered schema, shortened context or hidden answer in the input;
- any API call, alternate provider, fallback, cascade or vote;
- any automatic retry of a completed answer.

These bans describe the **current MLX / 196-item configuration**. A different GGUF or
schema-enforced build, or one with reasoning on, is a **separate runtime** requiring its own
qualification and its own frozen record — never a fallback reached from inside this one.

**One call at a time.** The client does not enforce this (§13.9). The caller runs strictly
sequentially, `workers=1`. `OLLAMA_NUM_PARALLEL=1` on the server is a backstop, not a
guarantee.

**Raw output is saved before anything parses it** (§8). The saved raw text then goes to the
one shared parser — plain JSON or a single whole-response fence — the same parser the
comparison arm uses. No provider-specific parser, no repair pass.

**A cut-off or incomplete output is invalid**, after its raw form has been preserved. With
`max_tokens` set explicitly, the client returns a truncated answer with
`stats["truncated_output"] = True` and does **not** raise (§13.7). The runner must check
that flag and `done_reason` itself and reject the answer.

Transport failure with no usable response is not an answer. `L.generate(retries=0)` is
**mandatory** — the library must never retry on its own. Separately, a frozen task **may**
authorize a bounded caller-level retry for a transport failure or an invalid output. Where it
does, the bound is fixed before the run, every attempt is recorded, and a **completed answer is
never re-asked**. Library retries and caller attempts are counted separately (§16).

---

## 7. Capacity and pre-call safety

**Two different numbers. Do not conflate them.**

| Figure | Meaning |
|---|---|
| **25,000 tokens** | the **conservative safe operating limit**; use this |
| **29,492 tokens** | a **single stress success**, evidence only, not a ceiling |

The 29,492-token result (2026-08-18): a 28,092-token prompt plus 1,400 generated tokens
completed at `num_ctx=32768` — wall 404.2 s, prefill 83.1 tok/s, decode 21.3 tok/s. It ran
while the Mac was swapping heavily (swap used peaked 22.9 GiB), which is why prefill sat
below the usual band. **One success is not a safe ceiling.** It does not authorize routine
calls at that size.

Supporting memory evidence: runner memory grows roughly 0.24 MB per prompt token — 13.7k
tokens reached 33.9 GiB peak, 23.5k reached 36.2 GiB, against a 37.4 GiB Metal budget on the
48 GB machine. A 70k-token prompt would need about 47 GiB and is impossible here.

**Open blocker — no genuine pre-call token check.** The current MLX client cannot refuse an
oversize input before calling:

- `trunc_in = (not _is_mlx(MODEL)) and pec >= budget - 8` — `_is_mlx("qwen3.8:27b-mlx")` is
  `True`, so this is always `False` and `TruncatedInputError` can never fire on the
  production model;
- even on the GGUF path the check reads `prompt_eval_count` **from the response**, so it
  detects truncation after the call, never before it;
- there is no tokenizer and no length check anywhere in the client.

**A transport may never truncate a frozen input and never split one** to make it fit. An input
that does not fit is refused before the call and counted as an unserved item. A task owner may
later design self-contained chunks as a **separately qualified task**; the transport cannot
invent them.

### Estimating size and cost before you call

```
call time  ~=  new_prompt_tokens / 95  +  output_tokens / 25    (seconds)
```

- Fresh, never-seen text: **95-110 tok/s** prefill; that is the GPU ceiling. Nothing makes a
  brand-new document faster except sending fewer tokens.
- Cached prefix (same bytes from position 0): effectively free, about 1 s per call.
- Decode: 22-29 tok/s with MTP speculative decoding on; 34.3 tok/s was measured once on an
  idle machine (2026-08-19). GGUF decodes roughly 3x slower.
- Measured cold examples: 6k-token table 65 s; 13.7k-token 8-K exhibit 145 s; 23.5k-token
  exhibit 261 s.
- **Rough token estimate before tokenizing:** numeric tables about **1.6 chars/token**, prose
  about **3.4 chars/token**. Every digit is its own token; indentation and separators are
  tokens too. This is an estimate for planning, never a substitute for the pre-call check
  the blocker above still needs.
- **Never send raw HTML** — the same exhibits run 10-20x the tokens of the rendered text.

**`num_ctx` per role, fixed for the whole run:** 16384 for tables and chunks up to about 12k
tokens; 32768 for whole exhibits (tested to 23.5k tokens). Never change it mid-run - it
reloads the model and drops the cache.

**Sending fewer tokens is the only software lever.** The encoding that produced 93/93 on the
table lanes: one header line `Source-derived choices. Every choice line is
choice|occurrence|value|headers:`, then per row `ROW n section="..." label="..."`, then choice
lines like `22|1|2,289|4Q24` with no indent, and the per-call target block last. Code applies
the occurrence; the model never counts. Dense encoding cut tokens 46% against verbose prompts,
and dropping the indent plus a single `cols` legend cut a further 16.7%. Reference
implementation (historical): `qwen38_optimization/harness/choice_v2_compact/choice_v2.py`.

**Do not prescribe tokenizer machinery yet.** A later task must first measure the final
frozen prompts, then choose the smallest pre-call check that is sufficient. That decision is
not made in this document.

---

## 8. Raw capture, parsing and accounting

1. **Raw first.** Write the model's exact reply to its own file before any parsing,
   stripping, normalising or validation. `L.generate()` returns the assistant text
   unmodified on this path.
2. **One strict shared parser.** The same parser, normalizer and validator used by the
   comparison arm. Plain JSON or one whole-response fence. Nothing provider-specific.
3. **No silent retry and no repaired answer.** Any caller retry authorized by the frozen
   packet (§6) is bounded, declared in advance and recorded; nothing retries silently. Code
   may parse, validate, re-pull source spans and reject. It may never change the model's
   chosen row, meaning, name, route, type or concept.
4. **Record every event**, per item: the call, any prime, transport failures, refusals,
   invalid answers, cut answers, and every unserved input. Report correct, wrong, abstained,
   invalid and missed as raw counts, never as a rate alone.

Fields available from `with_stats=True`: `tok_s`, `eval_count`, `prompt_eval_count`,
`done_reason`, `truncated_input`, `truncated_output`, `total_s`, `host`. **These do not
include the model id, num_ctx, think or temperature** — record the resolved frozen identity
separately (§5, §13.6).

---

## 9. Caching and priming

**Layout rule: stable bytes first, the varying item last.** Ollama reuses a KV prefix only
when bytes match from position 0. Any changing token placed early — an id, a date, a nonce —
destroys reuse for everything after it.

**Cache affects speed only.** It changes no prompt bytes and no answer. Priming is a
transport step.

Priming is **optional**, happens **only after the capacity checks pass**, and is
**recorded**. Why it exists: the MLX runner creates a branch-point snapshot only during the
*second* request that diverges there, and this model's recurrent layers cannot be rewound,
so the first two calls on a shared document are otherwise both cold. Sending the shared
prefix alone first leaves a snapshot the first real call restores from.

```python
L.prime(shared_prefix, system=SYSTEM_TEXT, num_ctx=NUM_CTX)   # once per document
L.prime_for(prompts, system=SYSTEM_TEXT, num_ctx=NUM_CTX)     # computes the prefix
```

Conditions: same model, same system text, same `num_ctx` as the real calls; the prefix must
start at the beginning of the user content and end on a line boundary. Priming an
already-cached prefix costs about 0.1 s.

**One document batch at a time. No parallel calls.** The cache holds roughly 8 GiB of
snapshots; interleaving documents evicts them. Never change `num_ctx` mid-run — it reloads
the model and drops the entire cache.

**Which roles the cache actually helps** (assessment recorded 2026-08-17, not a fresh
measurement): of 7 real AI roles, **3 benefit** — the reader (many items per event), the
table/prose locator (many anchors per table), and the concept picker (many facts per company
menu). Those are the high-volume roles, so by call count roughly 70–80% of calls could be
cache-fast after each document's one cold read. The other 4 — catalog chunk reader (each chunk
read once), identity judge, continuity judge, and graders/reviewers — read each input once at
the plain rate; their inputs are small, so each still costs only seconds. By step, caching was
assessed to help Steps 3, 5, 8, 9 and 11.

Getting the cache costs no change to any question or answer: put the shared document **before**
the per-call part (a prompt-layout change, so re-freeze that prompt version) and add one
`L.prime()` call per document.

Measured effect (evidence, not a promise): one 6.2k-token table, 3 calls, 155 s → 78 s with
identical answers; full choice_v2 9.0 min → 5.3 min with compact encoding and table-level
priming; qf01 7.4 min → 3.4 min.

---

## 10. Model-neutral qualification

- **One canonical semantic packet per task.** Every runtime receives the same semantic
  instructions, the same complete context and item order, the same input identities and the
  same response contract.
- **The same hidden key, parser, validator, scorer and pass bars** apply to Sonnet,
  Codex-hosted models and Qwen alike. Only a thin transport differs. A transport may encode
  the packet; it may never shorten or change it.
- **The hidden key never enters a runtime input.**
- **Qualification is not transferable.** It belongs to the exact task, the exact model and
  runtime, the exact transport and configuration, and the tested input class. It never
  transfers automatically to another task, another model or another input class.
- **The runtime that produced an answer never grades that answer.**
- **Zero observed wrong accepted results is mandatory.** Count every refusal, every miss and
  every unserved item.
- Freeze one runtime, model, transport, configuration, reasoning setting, measured capacity
  and input class before every run. Drift, unsupported capacity or possible truncation
  refuses before the call rather than after it.

"100%" here means zero observed errors on a finite locked set. It does not prove a zero true
error rate. Report the independent-case count beside every zero-error claim — for the table
suites the honest independent count is **8 tables from 7 filings**, not 93 documents.

---

## 11. Complete task and result registry

### 11.1 Runs that happened

**QF-01 original per-cell contract — FAILED**
Date 2026-07-24 · purpose: one anchor + one rendered table → complete evidence-ID set ·
input class: rendered 8-K tables · model `qwen3.6:35b-a3b` GGUF Q4_K_M, digest
`07d35212591fc27746f0a317c975a6d68754fb38e9053d82e25f06057af28522`, Ollama 0.32.3 ·
settings: reasoning off, temperature 0, no completed-answer retries, 4 concurrent workers ·
key: opened after the run · 93 calls · **correct 0, wrong 92, abstained 0, invalid 1** ·
precision 0%, recall 0% · 43 min 31 s, 1,004,082 input tokens, 17,114 output tokens · zero
input truncations, one output truncation · verdict **`NOT_SAFE_FOR_TASK`** · report
`table_evidence/REPORT.md`. Every parseable answer missed the exact period-header array.
**Diagnostic. The 93 cases are now development data and can never certify a tuned prompt.**

**choice_v2 — development, opened key**
`test_id QF-01-CHOICE-V2-DEV` · model chooses a numbered cell or `null`, code reconstructs
the evidence · 93 cases, 8 independent tables, 7 filings, 93 calls · settings: reasoning
off, temperature 0, `num_ctx` 16384, `max_tokens` 512, timeout 1800, workers 1, completed-
answer retries 0.

| run | model | correct | wrong | precision | artifact identity |
|---|---|---|---|---|---|
| old model | `qwen3.6:35b-a3b` | 75/93 | 18 | 0.806 | raw `5e7aa705…` |
| verbose prompts | `qwen3.8:27b-mlx` | 89/93 | 4 | 0.957 | raw `ef292ce3…` |
| dense + occurrence labels | `qwen3.8:27b-mlx` | **93/93** | 0 | **1.0** | raw `b5bf1f2b…` |
| + family priming, 9.0 min | `qwen3.8:27b-mlx` | 93/93 | 0 | 1.0 | raw `013278c9…` |
| + table priming, 6.4 min | `qwen3.8:27b-mlx` | 93/93 | 0 | 1.0 | raw `3faa3aa4…` |
| compact encoding, 5.3 min | `qwen3.8:27b-mlx` | 93/93 | 0 | 1.0 | raw `da73a80d…` |

Abstained 0 and invalid 0 in every row; transport failures 0 except the first 93/93 run (2).
All marked `production_authorized: false`, `unseen_certification_required: true`.
Every qwen3.8 error before the fix was `WRONG:occurrence`.

**row_v3 — development, opened key**
`test_id QF-01-ROW-V3-DEV` · model selects a row only; code applies the explicit occurrence
and copies the evidence · 93 cases · `qwen3.8:27b-mlx` **93/93**, precision 1.0 (raw
`5e6ae72f…`); old `qwen3.6:35b-a3b` also 93/93 (raw `8be8187e…`). Easiest task by
construction. Needs no priming — the prompts within a family are identical.

**qf01 aligned 5x50 contract — development, opened key**
`test_id QF-01` · 19 set-based calls covering 93 hidden cells across 8 tables, 7 filings ·
`qwen3.8:27b-mlx` · **correct 19, wrong 0, abstained 0, invalid 0**, evidence precision and
recall 1.0, **historical scorer label** `QWEN_ONLY_QUALIFIED` — a string this scorer emits, it
confers no authority — scored 2026-08-17T05:13:24Z · 3.4 min
with table-first priming (was 7.4 min) · manifest `3bd50ef6…`, raw `cb725f4d…`, hidden key
`b4a26aa5…`. Old model 17/19. The manifest records that the 2026-07-24 run authorization was
consumed by the failed original run and **a new model run needs its own owner GO**.

**Identity judge / EXP-0 contract, QC-01 — development, opened key**
2026-08-17 · K-pairs v1.3, 160 planted pairs (110 DIFFERENT, 50 SAME, 89 hard, 13 families) ·
model **`qwen3.8:27b-mtp-q4_K_M` (GGUF, schema grammar-enforced)** — the MLX build answered
in prose and was invalid · 160 calls, one pair per call · **wrong_same 0, false_refusal 2,
invalid 1, correct 157** · rates: wrong-SAME 0.0, false refusal 0.04, invalid 0.0063 ·
`gate_pass: true` against wrong_same=0, false_refusal≤10%, invalid≤2% · citations verbatim
on both sides 159/160 · 4,541.6 s total, 28.39 s/pair. Baselines: Sonnet arm A 0/0/0, Sonnet
arm B 0 wrong-SAME / 1 false refusal / 0 invalid, Opus 0/0/0. All 3 non-perfect cases fell in
the `synonym` family; the single invalid was a 600-token output-cap artifact that returned a
valid DIFFERENT when re-asked at a 1,500-token cap.
**Diagnostic only. A perfect score would not activate Qwen as an identity judge; full
identity testing needs K-pairs v2 with mined real pairs.**

**Reader EXP-2 proxy — development, opened key, partial**
2026-08-17 · first **10 of 40** chunks, 296 gold facts · `qwen3.8:27b-mtp-q4_K_M`, grammar
mode, reasoning off, `max_tokens` 8000 · MLX with reasoning off returned empty; with
reasoning on it ran away past 8–12k tokens — grammar-enforced GGUF with reasoning off was the
only working mode.

| metric | Qwen | Sonnet | Opus |
|---|---|---|---|
| either-recall | **50.0%** (148/296) | 45.3% (134) | 52.4% (155) |
| exact-name recall | 32.8% (97) | 32.1% (95) | 35.5% (105) |
| hard-subset either | 39.8% (39/98) | 49.0% (48) | 48.0% (47) |
| quote verbatim | 145/148 (98.0%) | 120/120 (100%) | — |
| name well-formed | 148/148 | 120/120 | — |

Compliance on Qwen's 148 candidates: output shape 100%, name syntax 100%, NAME-01 146/148,
verbatim 145/148, 60–200-character quotes 109/148. 2 of 10 chunks returned empty.
**Slip pattern from 10 reviewed failures (2026-08-17).** Name *syntax* is never wrong. The
slips are (a) direction or measure words creeping into names (`minimum_wage_increase` should be
`minimum_wage`; `headcount_growth` should be `headcount`); (b) breaking the 60-200-character
verbatim-quote rule, far more often too short than paraphrased (e.g. "unfavorable product cost
mix", 28 chars); and (c) naming the effect or measure instead of the underlying cause
(`foreign_currency_forward_contract_costs` should be `foreign_currency_forward_contract`;
`judicial_deposit` should be `brazil_tax_litigation`). Items (a) and (b) are mechanically
checkable by code; (c) is the genuine judgment gap. This is the same failure class predicted to
cost Qwen points on any quote-locator task.

**Not the official EXP-2 metric** — the official metric used Sonnet graders; this is strict
deterministic matching, with the Sonnet and Opus arms re-scored the same way, so it is a
relative comparison only. Precision was not measured.

### 11.2 Tasks with no Qwen run

From the readiness map. `READY KEY` means hidden answers exist; it never means a runner is
approved.

| ID | Task | Key status | Qwen |
|---|---|---|---|
| QF-02 | 8-K prose: find the exact sentence with the known Driver's number and period | NOT READY, 0/50 locked | not run |
| QF-03 | Prepared remarks: find the exact spoken update | NOT READY, 23 unaccepted candidates | not run |
| QF-04 | Transcript Q&A: find the exact answer | NOT READY, same 23 candidates | not run |
| QF-05 | Numberless claim: copy the exact sentence | NOT READY, 0/50 locked | not run |
| QF-06 | Abstain correctly when no unique evidence exists | NOT READY, no negative cases | not run |
| QC-00 | Name a known cause under NAME-01..19 | NOT READY, K-reader does not isolate naming | not run |
| QC-02 | Interpret DriverUpdate fields | K-fields **drafting**, no lock | not run; EXP-5 P6 arm withdrawn 2026-07-25 |
| QC-03 | Route ATTACH/ADOPT/CLAIM/CREATE/SKIP/UNSURE | NOT READY, K-route absent | not run |
| QC-04 | Classify metric/guidance/surprise/action | NOT READY, K-stamp absent | not run |
| QC-05 | Select one XBRL concept from a bounded menu | NOT READY for Qwen, no locked key | not run |
| QC-06 | Challenge a proposed identity/concept match | PARTIAL only | not run |
| QC-07 | Judge stock direction/force/confidence | NOT READY, no locked key | not authorized |
| QE-01 | Create, verify and grade hidden keys | frontier duty | **not currently qualified or authorized** for Qwen's own test |
| QA-01 | Discover new Drivers in unseen text | frontier duty | **not currently qualified or authorized** |

Locked keys that exist today: `K-pairs.v1.3` (160 pairs, lock `023fb1ce…`) and
`K-reader.v3` (1,175 records over 39/40 chunks, sha `cf87a09a…`, locked 2026-07-10).
`K-fields` has **no key** — it is being drafted; that drafting is what the 196-item packet
belongs to. The **remaining 30 K-reader chunks** are historical unused material inside an
existing locked key — **not authorized next work**.

### 11.3 Standing caveat on every row above

Every result in §11.1 came from a **development set whose answers were opened**. None is a
hidden qualification. Under the current unchanged production-shaped gate, all of them are
**diagnostic**. A fresh unseen holdout is required before any Qwen role is approved.

---

## 12. Historical chronology

**qwen3.6:35b-a3b (GGUF Q4_K_M, MoE 36B/3B-active, Ollama 0.32.3).** The original QF-01
per-cell contract failed outright — 0/93, `NOT_SAFE_FOR_TASK`. Diagnosis: the interface was
as guilty as the model. Occurrence markers split source headers, the flattened table did not
attach cells to full header paths, and the model was charged for retyping long identifiers
that code could have built. The redesign moved all deterministic copying into code.

**Redesign sequence.** choice_v2 (model returns a number, code reconstructs) reached 75/93 on
the old model — better, still not safe. row_v3 (model picks a row, code applies the
occurrence) reached 93/93 on both models, but is the easiest task by construction.

**Migration to qwen3.8:27b-mlx, 2026-08-15.** Dense 27.8B, nvfp4, MLX engine. Trade: roughly
4x slower decode than the old MoE build, but qf01-aligned went 17/19 → 19/19 and choice_v2
75/93 → 89/93. Both qwen3.6 tags were removed the same day.

**Performance investigation, 2026-08-15/17.** The original puzzle was that identical work
took 745 ms on one call and 7 minutes on another. Root causes found, in order:
`OLLAMA_NUM_PARALLEL=4` split `num_ctx` into four slots so a 7.5k-token prompt exceeded its
own slot (fixed to 1); `OLLAMA_LOAD_TIMEOUT` default 5m aborted any prefill over ~300 s
(fixed to 30m); the client's hardcoded 300 s timeout aborted real calls (now 1800 s); a LAN
path reaps connections idle ~320 s while the server completes and caches the work anyway.

**Accuracy sequence on choice_v2.** 75/93 (old model) → 89/93 (qwen3.8, verbose prompts) →
**93/93** with dense encoding plus explicit occurrence labels. Every qwen3.8 failure before
that fix was `WRONG:occurrence`; GGUF reproduced the same wrong answers, proving the weakness
was the model's, not the quantisation's.

**Speed sequence.** Dense encoding cut tokens 46%; compact encoding a further 16.7%. Prefix
priming removed the second cold prefill per document. Full choice_v2 at 100%: 25.2 min (old
model, 75/93) → 9.0 min → 6.4 min → **5.3 min**.

**Engine bake-off.** Ollama MLX cold prefill 84–110 tok/s, decode 22–29 tok/s with MTP
speculative decoding; llama.cpp b10450 Metal pp6144 81.57 tok/s, tg32 9.77–10.10; mlx-lm
0.31.3 84–88 tok/s and no MTP. Dense 27.8B prefill on a 16-core M4 Pro GPU is compute-bound
at roughly 85 tok/s. **No faster engine was found among the tested configurations** — the only
software lever for a brand-new document is sending fewer tokens.

**Power.** The machine is a 14-inch MacBook Pro, M4 Pro 12-core CPU / 16-core GPU, 48 GB,
which ships with a 70 W adapter. It was run on a 30 W charger, draining 2%/min under load and
throttling up to 3.5x; a 61 W adapter was attached later. Long batch runs must be
battery-gated and every reported timing should carry a battery reading.

**Explicitly disproved claims** (recorded so nobody re-derives them): "a cold 7.5k prompt
takes 400 s" measured a ~28k-token overflow, not prefill; "streaming turns 399 s into 1.0 s"
compared a cold prompt against a cached one; "qwen3.8 is 3x slower than qwen3.6" was
decode-only on a 17-token prompt; "prefill runs at 100–180 tok/s at the roofline" came from a
sweep whose cases shared a prefix; earlier notes describing a 16-inch machine or a 140 W
adapter were wrong; a "network middlebox idle timeout" was blamed before the real ~320 s
reset was understood.

Full chronological working, every measurement and every dead end:
`qwen38_optimization/notes/INVESTIGATION_LOG.md` (811 lines). **Historical evidence — not
current instruction.**

---

## 13. Known defects and retired advice

These are live defects in code or documentation. Each is a correction of something currently
stated or implied elsewhere.

1. **`generate()` defaults to two retries.** The signature is `retries: int = 2`, so a call
   that omits it may make up to three attempts. Graded work must pass `retries=0` explicitly.
2. **`structured()` modifies the prompt.** On the MLX path it appends
   `"Return JSON only - exactly one object matching the schema, no prose, no code fence."` to
   the prompt text, strips code fences from the reply, and retries up to three model calls.
   It must never be used for graded or compared work.
3. **MLX has no pre-call token guard.** There is no tokenizer and no length check in the
   client. See §7.
4. **`TruncatedInputError` is not a working pre-call MLX safety gate.** It is disabled for
   MLX models by construction and is evaluated from the response in any case. Any statement
   that the client refuses oversize input before the call is **false**; earlier versions of
   this document said exactly that.
5. **`python -m config.local_llm` is not a read-only health check.** Its `__main__` block
   performs a real model call. Use `L.health()` or the HTTP endpoints for a read-only check.
6. **The returned stats do not carry the full frozen identity.** `with_stats=True` yields
   `host` but not the model id, `num_ctx`, `think` or `temperature`. Record the resolved
   identity separately.
7. **Explicit `max_tokens` suppresses the output-truncation exception.** The raise is guarded
   by `max_tokens is None`, so with `max_tokens` set a cut answer comes back normally with
   `truncated_output=True`. The runner must reject it.
8. **Host, model and thinking defaults are environment-controlled.** `LOCAL_LLM_HOST`,
   `LOCAL_LLM_MODEL`, `LOCAL_LLM_THINK`, `LOCAL_LLM_NUM_CTX` and `LOCAL_LLM_TIMEOUT` are all
   read at import. Resolve and freeze them; never assume the documented default.
9. **The client does not enforce sequential execution.** No lock or semaphore exists. The
   caller owns it.
10. **The 29,492-token success is evidence, not a universal safe ceiling.** See §7.
11. **Mac-side repository commands are obsolete.** Earlier recipes ran the identity and
    reader exams on the Mac against `localhost`, and described copying keys and the client
    next to the exam scripts there. All repository work now belongs on the Minisforum.
12. **Stale docstring.** `config/local_llm.py` opens with "Local LLM client — Qwen3.6-35B
    served from the Mac over the LAN" while its own body correctly documents the 2026-08-15
    migration to `qwen3.8:27b-mlx`. No behavioural effect; do not trust the first line.

**Retained only as rejected history — never as current instruction:**

- The 2026-07-24 `LOCAL_QWEN_HANDOFF.md` advice: that `L.MODEL` defaults to
  `qwen3.6:35b-a3b`; that the input budget is "about 16,000 tokens / 55,000–60,000
  characters"; that four workers are acceptable; that aggregate throughput is ~50 tok/s
  regardless of concurrency; and its pointers to `config/run_qwen.py` and
  `config/preflight.py`. Both helper files still exist on disk (dated 2026-08-01) but are not
  part of the current contract.
- "Retry until success." The `scripts/autoresume.sh` pattern was **transport** retry against
  a harness that never re-asks a completed answer. It is not permission to retry an answer.
- Any "route to Sonnet on failure" or automatic fallback behaviour inside a runner.
- Any semantic word list, regular expression or keyword gate standing in for a meaning
  judgment.
- Reasoning ON for the reader — it ran away past 8–12k tokens. Reasoning stays off in the
  current configuration; enabling it would be a separate runtime needing its own
  qualification, never a fallback.
- `format=` as a validity guarantee on MLX. It is not enforced there.

---

## 14. Exact workflow

1. **Shadow first.** Make every change in `/tmp/qwen38_bench/EventMarketDB`. Never edit the
   real tree to try something out. Verify the artifact the run actually reads — prompts baked
   into `cases.jsonl` at prepare time and the shadow tree's own copy of the client have both
   silently defeated edits before.
2. **Review independently.** Produce the exact diff, the tests and the evidence. Read them as
   a reviewer, not as the author.
3. **Apply only the accepted change** to the real Minisforum repository, by hand, file by
   file. Never copy the whole shadow tree over the real one.
4. **Stage only the exact reviewed changed files** inside the three allowed roots in §4, by
   explicit path — never a whole directory.
5. **Commit and push only after an explicit completion review.** Never as part of doing the
   work.

---

## 15. Artifact index

### 15.1 Current — authoritative

| Artifact | Purpose | Path | Identity |
|---|---|---|---|
| This ledger | the only current Qwen document | `.claude/plans/Drivers/FinalDesign/LeftOverSteps/QwenInference.md` | pre-migration file was untracked; tracked when landed |
| Client | the only local entry point | `config/local_llm.py` | sha256 `836e5722…`, 388 lines |
| Server plist | Ollama launchd config (Mac) | `~/Library/LaunchAgents/com.faanjum.ollama.plist` | last recorded — verify before running; copy in `qwen38_optimization/server/` |
| Shadow tree | where development happens | `/tmp/qwen38_bench/EventMarketDB` | rebuilt as needed |

### 15.2 Current — evidence, referenced by §11

| Group | Path under `.claude/plans/Drivers/FinalDesign/QwenTests/qwen38_optimization/` | Status |
|---|---|---|
| choice_v2 harness + 6 result sets | `harness/choice_v2/`, `harness/choice_v2_compact/` | development evidence |
| row_v3 harness + 2 result sets | `harness/row_v3/` | development evidence |
| qf01 harness + 3 result sets | `harness/qf01/` | development evidence |
| Identity exam runner + results | `exams/identity_exam/` | development evidence |
| Reader exam runner + results | `exams/reader_exam/` | development evidence, 10 of 40 chunks |
| Engine bake-off | `bakeoff/llama_bench_b10450_pp6144.md` | measurement |
| Original client + diff | `client/` | reference |
| Experiment scripts, queues | `scripts/` | reference |

**Re-running a historical suite** (the harnesses still exist; this is reference, not
authorized work). Work in the shadow tree, use `/home/faisal/EventMarketDB/venv/bin/python`,
and copy the patched harness over the shadow's own copy — editing the real tree's copy has no
effect on a run, and prompts are baked into `cases.jsonl` at `prepare` time, so a prompt edit
needs a fresh `prepare`. Table suites run `prepare` → `run` → `score` with
`LOCAL_LLM_MODEL=qwen3.8:27b-mlx LOCAL_LLM_NUM_CTX=16384`; `run` is resumable after a
transport failure. The identity and reader exams run from
`qwen38_optimization/exams/*/`, need their key and input files copied or symlinked next to
the script (see each `README.txt`), and use the GGUF model
`qwen3.8:27b-mtp-q4_K_M` — the MLX build answers identity prompts in prose and returns
nothing on the reader. Expected wall-clock: choice_v2 about 5–6 min, row_v3 about 4 min,
qf01 about 3.5 min, identity about 28 s/pair, reader about 6.6 min/chunk.

Locked keys, never to be opened outside a scorer process:
`.claude/plans/Drivers/experiments/keys/K-pairs/K-pairs.v1.3.jsonl` (lock `023fb1ce…`) and
`.claude/plans/Drivers/experiments/keys/K-reader/K-reader.v3.jsonl` (sha `cf87a09a…`).
`keys/K-fields/` holds `draft_inputs/` and `protocol.md` only — **no key exists yet**.

### 15.3 Historical — non-authoritative, do not follow

Preserved as evidence. None of these may be treated as a current instruction. Do not delete
or rewrite them.

| Document | Lines | Why superseded |
|---|---|---|
| `QwenTests/qwen38_optimization/QWEN_INFERENCE_GUIDE.md` | 337 | previous canonical guide; superseded by this ledger; its §9 contains the false pre-call truncation claim (§13.4) |
| `QwenTests/README.md` | 299 | 2026-07-24 readiness map; §4 task table is reproduced in §11.2 |
| `QwenTests/LOCAL_QWEN_HANDOFF.md` | 97 | 2026-07-24 connection note; stale model, budget and worker advice (§13) |
| `QwenTests/table_evidence/REPORT.md` | 91 | the 0/93 failure report; still the best account of why the original design failed |
| `QwenTests/table_evidence/choice_v2/REPORT.md` | 69 | the 75/93 old-model report |
| `QwenTests/table_evidence/row_v3/REPORT.md` | 36 | old-model row_v3 report |
| `QwenTests/table_evidence/{choice_v2,row_v3}/README.md` | 34 / 32 | harness notes |
| `qwen38_optimization/notes/INVESTIGATION_LOG.md` | 811 | full chronological working behind §12 |
| `qwen38_optimization/notes/RUNBOOK.md` | 117 | v2 recipe, superseded by §§5–9 |
| `qwen38_optimization/notes/RUNBOOK_v1.md` | 63 | v1 recipe |
| `qwen38_optimization/notes/HANDOFF.md` | 22 | state summary at 2026-08-17 |
| `qwen38_optimization/README.md` | 45 | folder guide |
| `qwen38_optimization/harness/*/README_original.md`, `REPORT_original.md` | 34/69/32/36 | pre-change copies |
| `config/run_qwen.py`, `config/preflight.py` | — | 2026-08-01 helpers, outside the current contract |

---

## 16. Future update template

Every later Qwen task must update **§2 current status**, the **§11 task registry** and the
**§15 artifact index**, and append **one dated entry** in the form below.

```
### <YYYY-MM-DD> — <task name>

Purpose        : <one sentence>
Input class    : <what kind of input, and how many items>
Packet         : <path> sha256 <hash>
Prompt         : <assembled-prompt hash or per-item hash file> sha256 <hash>
Model/runtime  : <model id> · Ollama <version> · <engine/quant> · host <resolved>
Config         : think=<> temperature=<> num_ctx=<> max_tokens=<> timeout=<> retries=<>
Calls          : <n> issued · <n> primes · <n> transport failures
Library retries: 0 (mandatory — L.generate(retries=0))
Caller attempts: bound <n> authorized by the packet · <n> used · <n> items affected
Raw artifacts  : <path> sha256 <hash>
Score artifact : <path> sha256 <hash>
Key status     : <locked/opened/none> <key path> sha256 <hash>
Outcome        : correct <n> · wrong <n> · abstained <n> · invalid <n> · cut <n>
                 · refused-before-call <n> · unserved <n> · total <n>
Measured       : precision <> · recall <> (only where lawfully measurable; else UNKNOWN)
Runtime        : <wall> · <battery reading if on the Mac>
Decision       : <diagnostic | qualified for this exact task+runtime | failed>
Blocker        : <what still stands in the way, or none>
Next action    : <the single next permitted step>
```

Rules for an entry: no number without an artifact behind it; anything unproven is written
**UNKNOWN** and never inferred; a development set with opened answers is labelled diagnostic;
and a result never claims authority over any task, model or input class other than the exact
one tested.
