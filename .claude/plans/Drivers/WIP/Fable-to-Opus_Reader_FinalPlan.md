# Fable → Opus Reader: Final Plan

**Status:** Proposal locked in principle, **NOT applied** to any production file. Date: 2026-06-14.
**Scope:** one step only — the per-chunk *reader* that extracts candidate driver names (`workflows/menu_build.js`, the single agent at ~line 144 that is `model:'fable'`). Everything else in the pipeline was already Opus.

---

## TL;DR (the decision)

Fable is gone → fall back to **Opus 4.8**. Opus, reading the same text, was missing ~half the drivers. We found **why** and a **minimal, reliable** fix:

> **Reader = Opus + a 3-sentence prompt add (no hardcoded examples) + read each chunk twice.**
> The second read is required *for reliability*, because Opus skips document regions at random.

### The COMPLETE change set — nothing else changes
1. **reader model:** `fable → opus`
2. **+3 sentences** to the Pass-1 reader prompt — 1 "be exhaustive" line + 2 "read the whole chunk" coverage lines (no hardcoded driver names).
3. **+ a Pass-2 re-read** — a second reader that returns ONLY what Pass 1 missed; merged (deduped) into the seed.
4. **+ a 1-line conditional → 1 read if the model is Fable, 2 reads for ANY other model.** Fable reads completely (no 2nd pass needed); every other model skips regions, so it gets the re-read. Flip one word (`'opus'`↔`'fable'`) and the pass count follows automatically.

The original **RULES (naming) block** and **all downstream stages** (reconcile / fold / repair) are **UNCHANGED**. No production code is touched yet — this file is the record; the exact edit is in §5, the conditional in §3c.

---

## 1. Plain-English: what & why

- A **"driver"** = a reusable cause of a stock move (e.g. `same_store_sales`, `oil_price`, `eps_surprise`). The reader's job: read one company document chunk and list every such cause it sees, with a verbatim quote.
- **Problem:** swapping Fable→Opus, Opus listed ~half as many real drivers on the *same* text.
- We spent the investigation finding the **true reason** (not patching prompts blindly) and then the smallest reliable fix.

---

## 2. The root cause (proven, not guessed)

**It's COVERAGE, not judgment.** Opus does not read the whole long chunk — it **skips entire regions** ("dead zones") where real drivers live, and **the skipped region is random each run**.

How we proved it (positional analysis — we located every driver's quote by position in the document):

| On CAKE's 10-Q chunk | Dead zones (doc tenths with drivers but the reader found none) |
|---|---|
| Opus, normal prompt | regions 0,1,3,9 (blind to the front 30%) |
| Opus, "coin EVERYTHING" prompt | **still** 0,1,3 — telling it *what* to find can't fix a region it never read |
| Opus, **read it twice** | **none** — the re-read covered the skipped regions |

The skipping is **stochastic**: the same prompt left `[1]` one run and `[0,1,9]` the next. That single fact drives the whole design: a single read *gambles* on coverage; a second independent read *reliably* patches whatever the first missed.

(Mechanism: the reader runs as a Claude **subagent**, and subagents run with extended thinking **off** — so one forward pass can't systematically guarantee it covered everything. See §7.)

---

## 3. The finalized fix (the design)

**Reader = Opus, with three small additions, run as two passes:**

1. **Model:** `fable` → `opus`.
2. **"Coin everything" line (1 sentence)** — tells it to list every cause, even minor ones (raises the amount it grabs *where it reads*).
3. **"Read everything" coverage line (2 sentences)** — tells it *how* to read: cover the whole chunk in order, skip nothing, self-check the beginning/middle/end. **No driver names, no categories** (those make the model over-copy and overfit).
4. **Two passes:** read, then a second targeted re-read that returns only what the first missed; union the two. This is the **reliability** mechanism for the random skipping.

### 3a. The exact prompt text (verbatim — paste-ready)

**Add to Pass 1 (the "coin everything" line) — KEEP this exact wording (the list is load-bearing for recall):**
> *Be EXHAUSTIVE, not selective: coin a SEPARATE candidate for EVERY distinct source-grounded cause, metric, cost or revenue line, segment or brand figure, and guidance item — even minor or routine ones; redundancy is safe (duplicates are merged later) and a cause you never coin here is lost forever.*

> **Confirm-tested 2026-06-14 (4 samples × CAKE_F3 + held-out BLMN_Q) — the OLD wording above is empirically the BEST of THREE variants; TWO rewrites were tested and REJECTED:**
> • **"tighter / valid-cause-only"** (drop the list, say "every cause the rules allow"): held-out recall **40.2 → 29.5/49 (−27%)**, dead zones 1.0→2.5, ~zero noise gain.
> • **"balanced / general type-list"** (operational/financial/segment/macro/capital-allocation/guidance, illustrative-not-exhaustive): held-out recall **40.2 → 30.5/49 (−24%)**, dead zones 1.0→2.8, noise 0.5→1.5 (worse).
> **Lesson:** the CONCRETE list is NOT harmful hardcoding — it lists *type-categories* (not driver names) and is a more **effective recall reminder** than abstract category words; Opus needs the concrete nudge to coin financial/segment items on UNFAMILIAR docs. Generalizing it *looks* cleaner but **costs recall + adds noise**. Macro/operational types are already covered by the existing prose line ("MINE THE PROSE… commodity costs, tariffs, labor/wages, traffic, demand, FX, products/segments"). **Reader intent (confirmed):** keeps full naming discipline (cause-only, specific, reusable, source-backed); only avoids *impact judgment* + *meaning-merging* (later stages). Small bad-form residual (~2–3/chunk, wording-independent) → deferred **#3 naming hygiene**, not the reader wording. **DECISION: OLD wording LOCKED.**

**Add to Pass 1 (the pure coverage lines — no hardcoded names):**
> *Read the chunk as ONE COMPLETE SWEEP from the first line to the last, giving every part equal attention; do not get selective or slow down after the most salient / narrative parts — the later, denser, and more routine parts are equally eligible.*
> *Before returning, verify you actually considered the BEGINNING, MIDDLE, and END of the chunk; a stretch may yield zero candidates only if it genuinely holds no concrete reusable cause — if you merely skimmed it, go back and read it.*

**Pass 2 (the re-read critic, its own agent, shares the same rules block):**
> *A first reader already coined a list (given). Read the chunk and return ONLY the distinct, source-grounded drivers it MISSED — nothing already there or a mere synonym.* (No driver-name examples; no category lists.)

### 3b. Why two passes (not a longer prompt)
A longer/"smarter" prompt does **not** fix coverage — proven (§2). Only a second read does. We confirmed on a 4-sample replication that a *single* pass on a hard 10-Q averages ~0.65 recall with 2–3 dead zones and **swings run-to-run**; the second pass removes the dead zones and stabilizes it.

### 3c. The conditional (run once for Fable, twice for others) — answer to "is a minimal line possible?"
**Yes — one line.** The reader's model is named in one place. Add a derived flag:
```
const READER_MODEL = 'opus'                      // was 'fable'
const NEEDS_SECOND_PASS = READER_MODEL !== 'fable'  // Fable reads completely; other models skip → need the re-read
```
Then gate the 2nd pass + the coverage line on `NEEDS_SECOND_PASS`. So if Fable ever returns, change one word (`'opus'`→`'fable'`) and it auto-reverts to **single, cheap reads**; any other model auto-gets the reliable 2-pass.

---

## 4. Before vs After (no jargon)

| | Before — with **Fable** | Now — proposed with **Opus** |
|---|---|---|
| Which AI reads each document chunk | Fable | Opus |
| How we tell it **what** to grab | normal | + "grab every cause, even small ones" |
| How we tell it **how** to read | normal | + "read the whole thing, skip nothing, check start-to-end" |
| **How many times** it reads each chunk | **1** | **2** (a 2nd read catches what the 1st skipped) |
| How complete the result is | full | ~same as Fable, **reliably** |
| Reading cost per chunk | 1× | ~2× |
| **Why the 2nd read** | not needed (Fable reads completely) | needed — **Opus randomly skips parts on one read** |
| Hardcoded example driver names in the prompt | none | **none** (on purpose — they overfit) |

---

## 5. Production change — NOT applied (exact edits for later)

In `workflows/menu_build.js`, the single reader agent (~line 144):
1. `model:'fable'` → `model:'opus'` (or via the `READER_MODEL` constant in §3c).
2. Insert the **MIN_A "coin everything" sentence** + the **2 pure coverage sentences** into that reader prompt (verbatim text in §3a). No other line changes.
3. Add the **Pass-2 critic** as a second reader stage that unions its misses into the seed, gated by `NEEDS_SECOND_PASS` (§3c).

Nothing else in the pipeline changes (reconcile / fold / repair are already Opus).

---

## 6. What we tested + key evidence (compact)

All on real CAKE chunks + a **held-out company BLMN** (so it's not tuned to one firm). Recall = how many of Fable's drivers the config also found.

- **Reader-model gap (the starting point):** transcript chunk — Fable 54 vs Opus 24; 10-K — Fable 28 vs Opus 21. Opus ≈ half.
- **Prompt-only fixes plateau:** "coin everything" lifted the transcript 29→~42 but **left the same dead zones**; adding more sentences (targeted/category) gave **no** further recall.
- **Hardcoding examples overfits:** a version with exact driver-name examples behaved like a *checklist* (copied the example names, incl. their bad form) — rejected. Category-types + "illustrative, use common sense" was equal recall and cleaner → preferred over hardcoding.
- **2-pass works:** union beat Fable in-sample (e.g. 10-Q 76 vs 40, transcript 66 vs 54) and removed dead zones; on held-out BLMN it filled most.
- **Coverage line confirmed the root cause:** single-pass coverage instruction filled dead zones that the "coin everything" prompt could not — but only **stochastically**.
- **"tables" word — settled by 4-sample replication:** no real effect (an early 64-vs-35 was run noise); **use the pure wording**.
- **Single-pass is unreliable on hard filings:** 4-sample mean ~0.65 recall, 2–3 dead zones, high variance → 2-pass needed for reliability.

---

## 7. Max-effort finding (thinking + Codex)

- **Claude subagents run with extended thinking HARD-OFF.** The reader must be a parallel subagent fan-out, so it can't "think." Fable ran the same way. This is *why* one read skips regions. (Online re-verification of any newer way to enable subagent thinking: **see RESULTS below — pending the research workflow.**)
- **Codex (your ChatGPT subscription) is not the answer.** It has the highest raw recall but ~⅓–⅔ of its output is junk/over-split; **xhigh made precision worse and timed out (>10 min)**. Usable only as an optional messy "union" booster, never the clean primary reader.

> **ONLINE RESEARCH — extended thinking in Claude Code (done 2026-06-14):**
> **Docs verdict (high confidence, official docs):** you CAN enable subagent thinking — via the **`effort` frontmatter** in the subagent's own definition file (`effort: xhigh`/`max`), because on Opus 4.7+/4.8 + Fable 5 **effort IS the extended-thinking control**. There is **no per-call Task-tool thinking parameter** (open issue #14321) — the lever lives in the agent definition (or `--agents` JSON). Global kill-switch (`MAX_THINKING_TOKENS=0` / `--thinking disabled`) overrides it. Sources: code.claude.com/docs sub-agents, model-config, env-vars; anthropics/claude-code CHANGELOG (v2.1.78/2.1.80).
> **Our empirical probe (2026-06-14):** **0 thinking blocks** across 8 recent reader-subagent transcripts — even though this session ran at `xhigh`. Ambiguous: either subagents aren't thinking, or they reason internally without serializing thinking blocks.
> **TESTED (2026-06-14, no new files): passing `effort:'xhigh'` to the workflow `agent()` opt had NO effect** — 0 thinking blocks AND dead zones unchanged (CAKE_F3 still [0,1,9] / [1]; BLMN_Q [6,7,9] vs no-effort [9]; counts 38/45/38, same range). Consistent with the docs: the supported lever is the agent-DEFINITION **frontmatter**, not a per-call opt, so the workflow opt was silently ignored.
> **The documented `effort: xhigh` frontmatter path remains UNTESTED** — it needs a `.claude/agents/*.md` config file + a restart, which is out of bounds under the owner's "no production/config changes" rule.
> **DECISION: lock the reliable 2-pass.** Every path that does NOT touch a config file has been tried; none removes the (stochastic) coverage skipping. The effort-frontmatter idea stays an OPTIONAL future experiment (gated: one temporary agent file + a restart); only if it ever fixed coverage single-pass would it replace the 2-pass.

---

## 8. Deferred — handle one at a time (owner's order)

1. **#3 Naming hygiene** — kill bad-form names the recall push surfaces: change-words (`supply_chain_disruption` → `supply_chain`), `*_growth`/`*_delays`, bundled-`and` (`asset_impairment_and_lease_termination` → split), one-off names (`los_angeles_fires` → `wildfire`), and balance-sheet noise (`net_indebtedness`, `liquidity`). These are existing ontology rules (R2/R6/R7/R9/R10); fix with a small cleanup nudge or the G2 gate.
2. **#2 Financial-tables + risk-factors as a fed list** (like `fiscal_kpis`) — for the *within-region density* misses (dense 10-K risk-factor paragraphs the reader under-coins even with full coverage). Structural change (an extractor feeds a list), not a prompt line.

---

## 9. What was NOT touched
- **Zero production files changed.** All experiments ran in a scratch folder (`runs/model_ab_20260613/`, ~1.7M, to be removed once locked).
- `menu_build.js`, the ontology, and all downstream stages are untouched.
- The model swap + prompt adds above are a **proposal awaiting your go-ahead**.
