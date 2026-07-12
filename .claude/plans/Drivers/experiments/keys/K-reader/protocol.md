# K-reader protocol — v3 (EXP-2 reader-qualification key)

**Status:** DRAFT for Fable finalization. This protocol + the **pre-registered v3 40-chunk sample** are written and pinned **BEFORE any kr_ record is drafted**. The reader-gold in `K-reader.v3.jsonl` is drafted against *this* text and the *v3* sample; the pins are recorded in `K-reader.v3.lock.json` (`protocol_sha256`, `sample_sha256`) at lock. A locked key + protocol + sample triple is immutable (WorkOrder §1.4). (Sample lineage: v1 → v2 → v3, all pre-drafting — §4.1.)

## 0. Purpose
K-reader is the gold key for **EXP-2 — reader qualification**. The blind chunk reader (`menu_build.js`, post-WP-FC-EDITS) coins candidate `driver_name`s from a chunk under NAME-01…19 + OD-3. K-reader pins **40 real frozen chunks** and, for each, the **gold set of admissible causes** a correct reader should coin. EXP-2 scores the reader's coined names against this gold (recall + precision), never by string match — matching is judged, with `acceptable_alt_names` guiding the grader.

## 1. Common WP-KEYS protocol (restated)
1. **Draft — DUAL-TIER UNION.** Two independent drafters — **Sonnet** and **Opus** — **each read all 40 pinned chunks at effort=high** and independently propose every admissible cause as `kr_` records (§2/§5/§6). Their two outputs are **UNIONED** (a cause proposed by either tier enters the draft set); neither tier sees the other's output or any gold. Drafting has not run at protocol-authoring time.
2. **Lint** — `harness/key_lint.py` validates schema + sample coverage (all 40 v3 chunks present; no chunk outside the pinned v3 sample) + evidence-locator quotes are verbatim substrings of the referenced chunk.
3. **Adjudicate** — **Fable adjudicates EVERY record** of the union (main session): prunes over-coined/duplicate/rule-breaking causes, adds any both tiers missed, fixes non-canonical names. Hard calls → `exhibits/ra_*.json`. Recorded in the sidecar, never in the reader-scored key.
4. **Lock** — `harness/sha_lock.py lock` writes `K-reader.v3.lock.json` (`locked_by: fable`) = sha256(key) + sha256(protocol) + sha256(sample) + counts. EXP-2 verifies all three shas before the first reader call; mismatch = abort. K-reader **locks before EXP-2**.

## 2. Record schema (`kr_` records — the reader-scored gold)
```jsonc
{"key_id":"kr_0001","source_id":"...","ticker":"...",
 "chunk_ref":{"file":"<frozen chunk filename, one of the pinned v3 40>"},
 "evidence_locator":{"quote":"<verbatim >=60 chars copied from that chunk's content>","occurrence":1},
 "gold_cause":{"proposed_name":"<NAME-01…19 + OD-3 canonical lower_snake_case>",
               "acceptable_alt_names":["<other names a correct reader could coin for the SAME cause>"],
               "slice_expected":null,"per_x":null},
 "rule_refs":["NAME-04","OD-3"],"hard":false}
```
- One `kr_` = one gold cause. A chunk with several admissible causes yields several `kr_`; a chunk that coins **no** admissible cause yields **zero** (a legitimate skip-test).

## 3. Blindness
The reader under test is shown **only the chunk file's real content**. It is **never** shown any `kr_` gold or the sidecar. K-reader is the answer key, applied by the scorer AFTER the reader coins blind. The two DRAFTERS (§1.1) are likewise never shown the gold or each other's output.

## 4. Chunk sample — 40, pre-registered v3 (`K-reader.v3.sample.json`, sha256 `41fbc82774a0bfcfa140301a9061fb1cd4eb0c6fe67512c1ebe846521b9e0291`)
**Universe:** frozen restaurant chunk files for the **10 Phase-1 tickers** (roster CAKE·DRI·MCD·YUM·CMG·SBUX·QSR·TXRH + hold-outs BLMN·SHAK; WING/CBRL/EAT/PZZA excluded) — **700** chunk files.
**Recipe (deterministic, 0-LLM, reproducible):**
- **Ticker stratum (equal): 4 chunks per ticker** (10 × 4 = 40).
- **Document cap:** at most **1 chunk per `primary_source_id` within a ticker** — each ticker's 4 chunks are **4 DISTINCT documents**.
- **Source_type stratum (within each ticker):** Hamilton-allocate the ticker's 4 across its primary source_types (per-file primary = max-content event's type, A-folded), proportional to the ticker's file mix; fill each cell with the top-ranked distinct-document files of that type.
- **Rank:** ascending **`sha256("K-reader.v3:" + filename)`** (hex, lexicographic). Seed = `K-reader.v3`. (v3 replaces the v2 h32 rank with sha256.)
- **Substitution:** if a source_type cell cannot be filled with distinct-document files of that type (runs out under the document cap), the shortfall is taken from the ticker's **next-ranked files of ANY type**, preserving the document cap. Every substitution is recorded (§4.2 / `K-reader.v3.sample.json.substitutions`).
- Final 40 sorted by (ticker, filename). Overall source_type mix: `transcript 13 · 10-K 10 · 8-K 9 · 10-Q 8`.

**The pinned 40 (v3):**

| # | ticker | chunk_file | primary | chars | sel | primary_source_id |
|---|---|---|---|---|---|---|
| 1 | BLMN | BLMN__chunk_007.json | 8-K | 29831 | primary | 0001546417-26-000006 |
| 2 | BLMN | BLMN__chunk_023.json | 10-Q | 22790 | primary | 0001546417-24-000160 |
| 3 | BLMN | BLMN__chunk_031.json | 10-K | 39798 | primary | 0001546417-24-000037 |
| 4 | BLMN | BLMN__chunk_075.json | transcript | 38427 | primary | BLMN_2023-04-28T08.15 |
| 5 | CAKE | CAKE__chunk_024.json | 10-Q | 39688 | primary | 0001410578-24-000636 |
| 6 | CAKE | CAKE__chunk_029.json | 10-K | 39937 | primary | 0001104659-24-027565 |
| 7 | CAKE | CAKE__chunk_033.json | 8-K | 29323 | primary | 0001104659-23-113409 |
| 8 | CAKE | CAKE__chunk_050.json | transcript | 10363 | primary | CAKE_2025-07-29T17.00 |
| 9 | CMG | CMG__chunk_029.json | 8-K | 27870 | primary | 0001058090-23-000026 |
| 10 | CMG | CMG__chunk_033.json | 10-K | 38195 | primary | 0001058090-23-000010 |
| 11 | CMG | CMG__chunk_049.json | transcript | 37930 | primary | CMG_2024-07-24T16.30 |
| 12 | CMG | CMG__chunk_058.json | transcript | 25309 | primary | CMG_2023-10-26T16.30 |
| 13 | DRI | DRI__chunk_002.json | 8-K | 20043 | primary | 0000940944-26-000005 |
| 14 | DRI | DRI__chunk_019.json | 10-K | 39572 | primary | 0000940944-24-000035 |
| 15 | DRI | DRI__chunk_041.json | transcript | 39797 | primary | DRI_2025-09-18T08.30 |
| 16 | DRI | DRI__chunk_047.json | transcript | 39378 | primary | DRI_2024-12-19T08.30 |
| 17 | MCD | MCD__chunk_019.json | 8-K | 35381 | primary | 0000063908-24-000029 |
| 18 | MCD | MCD__chunk_023.json | 10-Q | 39986 | primary | 0000063908-23-000076 |
| 19 | MCD | MCD__chunk_033.json | 10-K | 39913 | primary | 0000063908-23-000012 |
| 20 | MCD | MCD__chunk_039.json | transcript | 38228 | primary | MCD_2026-02-11T16.30 |
| 21 | QSR | QSR__chunk_005.json | 10-Q | 39724 | primary | 0001618756-25-000300 |
| 22 | QSR | QSR__chunk_025.json | 10-K | 39709 | primary | 0001618756-24-000020 |
| 23 | QSR | QSR__chunk_044.json | transcript | 39996 | primary | QSR_2025-02-12T08.30 |
| 24 | QSR | QSR__chunk_048.json | transcript | 37841 | primary | QSR_2024-08-08T08.30 |
| 25 | SBUX | SBUX__chunk_001.json | 8-K | 289 | primary | 0000829224-26-000064 |
| 26 | SBUX | SBUX__chunk_038.json | 10-K | 7676 | primary | 0000829224-23-000058 |
| 27 | SBUX | SBUX__chunk_046.json | 10-Q | 37954 | primary | 0000829224-23-000017 |
| 28 | SBUX | SBUX__chunk_065.json | transcript | 35212 | primary | SBUX_2024-01-30T17.00 |
| 29 | SHAK | SHAK__chunk_016.json | 10-Q | 39914 | primary | 0001620533-25-000029 |
| 30 | SHAK | SHAK__chunk_029.json | 8-K | 28107 | primary | 0001620533-24-000105 |
| 31 | SHAK | SHAK__chunk_056.json | 10-K | 39964 | primary | 0001620533-23-000015 |
| 32 | SHAK | SHAK__chunk_073.json | transcript | 38354 | primary | SHAK_2024-08-01T08.00 |
| 33 | TXRH | TXRH__chunk_010.json | 10-Q | 39872 | primary | 0001558370-25-010861 |
| 34 | TXRH | TXRH__chunk_023.json | 8-K | 23898 | primary | 0001558370-24-010176 |
| 35 | TXRH | TXRH__chunk_040.json | 10-K | 39139 | primary | 0001558370-23-001979 |
| 36 | TXRH | TXRH__chunk_045.json | transcript | 2656 | primary | TXRH_2025-08-07T17.00 |
| 37 | YUM | YUM__chunk_003.json | 10-K | 39553 | primary | 0001041061-26-000084 |
| 38 | YUM | YUM__chunk_046.json | 10-Q | 13881 | primary | 0001041061-23-000041 |
| 39 | YUM | YUM__chunk_048.json | 8-K | 3252 | primary | 0001041061-23-000037 |
| 40 | YUM | YUM__chunk_079.json | transcript | 5428 | primary | YUM_2023-08-02T08.15 |

### 4.1 Supersession (v1, v2 → v3 — all pre-drafting, all frozen)
- **v1** (`K-reader.v1.sample.json`, sha `a0090b90fff9e58ae097423525f8419054341663b56d7dd8c09dcd87f4e551d1`) — **superseded-pre-drafting**: source-type-only stratification covered only 8/14 tickers, missed core companies CAKE/MCD/CMG/SBUX/TXRH, drew 13/40 from unused tickers.
- **v2** (`K-reader.v2.sample.json`, sha `050376fceca53cb0e31c989e7ee8c009034280a33c39966bceaec3ecb5cad9e8`) — **superseded-pre-drafting**: h32 rank; allowed >1 chunk per document within a ticker. Fable moved to sha256 rank + a strict 1-per-document cap + recorded substitution = v3.

Both remain **FROZEN** (unchanged bytes); **no reader/Sonnet/Opus drafting ran against either**; retained only as superseded records. All drafting/lint/lock use v3.

### 4.2 Substitutions (recorded)
None — every source_type cell filled within its type under the document cap.

## 5. Rulebook (what "admissible cause" means)
The gold uses the SAME authority the reader uses: **`02_DriverCatalog.md` NAME-01…19 + OD-3**, byte-inlined into `menu_build.js`'s RULES block at WP-FC-EDITS (commit 5db902f). A cause is admissible iff it passes the NAME-18 new-driver gate: a genuinely reusable, chunk-grounded, unambiguous, cause-only noun; vague text → no cause; own measured company parts → slice, not name. `acceptable_alt_names` = genuinely-equivalent alternatives (guides the judged match, never string equality).

## 6. Drafting instructions (for BOTH tiers at step 3)
**Sonnet and Opus each, independently, at effort=high**, read all 40 pinned v3 chunks and emit one `kr_` per admissible cause: canonical `proposed_name`, verbatim `evidence_locator.quote` (>=60 chars copied from THAT chunk), `acceptable_alt_names`, admitting `rule_refs`, `hard:true` only for genuinely hard calls. Default-skip vague content; never invent a cause without a quote. The two outputs are unioned by (chunk_ref.file, cause); Fable adjudicates the union at §1.3. Neither drafter sees the other's output or any gold.

## 7. Scoring reference (EXP-2, `score_exp2.py`)
The reader's coined names per chunk are matched (judged, `acceptable_alt_names`-aware) to the K-reader gold for that chunk: **recall** = admissible gold causes coined; **precision** = coined names that are admissible. Bars live in the EXP-2 section of the work order; this key fixes only the gold.

## 8. Fable sign-off (filled at lock)
- protocol_sha256: recorded in `K-reader.v3.lock.json` (self-referential: the lock file pins the sha of this final protocol)
- sample_sha256 (v3): `41fbc82774a0bfcfa140301a9061fb1cd4eb0c6fe67512c1ebe846521b9e0291`
- superseded (frozen, never drafted): v2 `050376fceca53cb0e31c989e7ee8c009034280a33c39966bceaec3ecb5cad9e8` · v1 `a0090b90fff9e58ae097423525f8419054341663b56d7dd8c09dcd87f4e551d1`
- key_sha256: `cf87a09af1c7b7c6f708c8df56d86bfc600edf8c1eaf6e41a8c6ab783b181736` (`K-reader.v3.jsonl`, 1175 records; adjudication sidecar `K-reader.v3.adjudication.json` sha256 `dacdea3c64afb3beac02a23cf918ab4b4ad732c917331a4ed688c0492adb51d7`)
- signed_off_by: `fable` at 2026-07-10T15:13:39Z — dual-tier union drafted (claude-sonnet-5 + claude-opus-4-8, both effort=high) → 1,326 union records → per-record Fable adjudication (every record ruled; union `fable{}` blocks back-filled per §8.1) → deterministic materialization → UTF-8 lint PASS (0 errors, 0 warnings) → locked in `K-reader.v3.lock.json`

---
*Generated 0-LLM at 2026-07-10T10:40:31+00:00. K-reader steps 1–2 (protocol + pinned v3 sample) only; no reader/Sonnet/Opus drafting has run.*


### 4.3 Thin/skip-test (lock-time addendum, non-blocking)
`SBUX__chunk_001.json` (289 chars, an item-only 8-K) is a **deliberate thin/skip-test**: a correct reader coins NO admissible cause from it. In the dual-tier draft, BOTH Sonnet and Opus returned zero causes for it — the expected outcome. It is retained in the pinned 40 as the negative/skip control.

### 8.1 drafted_by lineage (lock-time addendum, non-blocking)
At lock, `K-reader.v3.lock.json.drafted_by` MUST name BOTH exact model IDs and the effort: `{route:'dual-tier union', tiers:['claude-sonnet-5','claude-opus-4-8'], effort:'high'}`. The union in `K-reader.v3.draft_union.jsonl` records per-cause `draft_meta.proposed_by`; Fable's adjudication is filed in each record's `fable{}` block before lock.
