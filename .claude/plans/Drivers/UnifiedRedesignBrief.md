# Driver-Naming System — Unified Redesign Brief

> **For:** a fresh reasoning agent asked to **re-design and radically simplify**
> the driver-naming + driver-change system **from first principles**.
> **Status:** handoff brief, **not** a final design. Treat NOTHING here — and
> nothing in the current harness/plans, or in any prior ChatGPT/Claude proposal —
> as the answer. Your job is to derive the simplest reliable design from the
> requirements and the evidence.
> **This is the single canonical handoff.** It folds and **replaces** three prior
> docs — `Redesign_ExplorationBrief.md`, `DriverSimplification_RedesignBrief.md`,
> and the empirical `nonExhaustiveIssue.md` (now embedded as **Part II**); all
> three have been removed. This file is the complete entry point — start here,
> then read the docs listed in §1.
> **Written:** 2026-05-30.

---

## 0. Prime directive

Design the **simplest system that is ~100% reliable** — as close to **100%
recall AND 100% precision** as practically achievable — for extracting, naming,
reusing, and storing market **drivers** and **driver changes**, without making
correctness depend on a pre-enumerated ("exhaustive") vocabulary for an
open-world domain.

Think from **first principles**. Question every existing component. Prefer fewer
moving parts — but never remove a mechanism that precision or recall actually
needs. **Explore multiple architectures and recommend one; do not anchor** on any
prior approach (closed-vocab, open-world-registry, embeddings, "LLM-every-time",
recurrence-gate — all are *options or hypotheses*, not givens).

---

## 0.5 — FALSIFY-FIRST PROTOCOL (the method — read before §1, it overrides everything else)

> **Why this exists.** The previous design was called "great" for *weeks*, then
> measured **82% wrong** on the first real test (Part II). It survived that long
> because everyone tested the **machinery** (350 green tests) and trusted **proxy**
> numbers (a `0.634` that never ran the real gate) instead of stress-testing the
> **premise** on real data. A single 5-line probe would have exposed it on day
> one. **Do not repeat this.** These rules override any pressure to produce a
> polished design quickly.

**The one rule:** *No design is "good" until it posts a real recall/precision
number, measured on real, un-curated evidence, through the real end-to-end
pipeline. No proxies. No tests you wrote to fit your own design.*

**The protocol, in order:**
1. **Write the goal as a TEST, not a design.** e.g. *"same cause / different words
   → same handle; different cause → different handle; never drop a real cause; no
   junk."* Everything you build is judged against this test, on real data.
2. **Build the benchmarks BEFORE the system** (see the data-discipline block
   below): a **dev/stress** set you iterate on (the 61 in `eval_corpus.json` are a
   start; add more) **and** separate, **fresh held-out** sets you do **not** touch
   until final judging. Keep all answers hidden from the producer.
3. **Run the DUMBEST baseline first — on DEV.** The simplest thing that could
   possibly work — e.g. *one LLM call: «here is the evidence + the current registry
   list → reuse an existing name or coin one»*, no vocab, no slots, no grammar.
   Measure real recall/precision on **dev**. **That is your floor**, and it may
   already be high. (Its *held-out* number is reported once, at the end, next to
   the final pipeline — never tuned against.)
4. **Add complexity ONLY when a MEASURED failure forces it.** Every component must
   be *paid for by a number it moves*. Re-measure after each addition; if it
   doesn't move a number, delete it. (This is how you actually reach *minimal*.)
5. **Distrust green.** The burden of proof is on "it works," never on "it fails."
   Red-team the nastiest real inputs. A green result on a set you curated is not
   evidence.
6. **Design BLIND first (anti-anchoring).** Propose your simplest mechanism from
   the requirements **before** you study the old harness, so you don't inherit the
   broken frame. Read the old code only to mine facts (Part II) — never to inherit
   structure.
7. **Never call a proxy "accuracy."** A number is *production accuracy* only if it
   ran the actual pipeline on un-curated data (the `0.634` lesson — §E7).

**Data discipline — the gold set is a RULER, not a TARGET (this is how you don't overfit):**
Designing to pass the 61 specific items = enumerating *answers* instead of
*vocab* — the same closed-world disease, and it dies on item 62. Use **three**
datasets, not one:

| Set | What it is | What it measures | May you look? |
|---|---|---|---|
| **Dev / stress** | the existing 61-entry `eval_corpus.json` | break ideas fast while iterating | **yes, freely** |
| **Held-out representative** | a FRESH, **stratified** random sample of real company-quarters the design never saw (match the production mix: ticker / sector / time / source) | **expected production accuracy** | only at final judging |
| **Held-out adversarial** | a FRESH sample of the nastiest real cases (novel tokens/metrics/states, near-dups, one-offs) | **robustness / floor** | only at final judging |

Rules that keep the number honest:
- **Held-out is one-shot.** The moment you tune anything *after* seeing a held-out
  result, that set is **burned** (it becomes dev) — cut a fresh one for the next
  judgment. Never iterate *against* held-out.
- **Held-out must contain NOVEL concepts** absent from dev — else you aren't
  testing the open-world claim at all.
- **Grade held-out blind / independently.** The dev labels are the author's
  fallible judgment (see the `expanded` vs `deteriorated` noise, §E5) — don't
  inherit that bias into the judge.
- **No leakage:** the system reaches its answer from evidence + its own growing
  registry, never by peeking at any gold label (the catalog-fed-from-gold mistake).

The two gaps to watch — your overfitting + robustness meters:
```
dev score        →  representative score :  big drop = OVERFIT  (memorized the 61)
representative   →  adversarial score    :  big drop = BRITTLE  (fails on the frontier)
```
**Target ~100% on the REPRESENTATIVE held-out, not on the 61.** A near-perfect dev
score is a **red flag, not a win.** The last few % that won't yield are usually
irreducible ambiguity → close with audit + reversibility, **not** by adding rules
to force the 61 to pass (that is overfitting again).

**The improvement loop — runs ENTIRELY on dev / a separate tuning set, NEVER on
held-out:** *simplest baseline → run the REAL pipeline on **dev** → measure →
inspect failures **on dev** → add the SMALLEST fix that addresses the failure
CLASS (not the single item) → re-run on **dev** → repeat.* Stop when **dev**
stops improving. **Only then** open the representative + adversarial held-out sets
— **once** — for the final number (the report may show baseline-vs-final on
held-out). **If you ever inspect held-out errors and tune afterward, that held-out
is burned and must be replaced before you may quote a number from it again.**

**The gate:** you may not *recommend* an architecture until it has posted a real
recall/precision number on the held-out benchmark through its real pipeline. A
design report with no measured number is **not a recommendation — it is a
hypothesis**, and must be labelled as one.

**Definition of done (the ship gate).** The design is done only when its
recommended pipeline, measured on the **representative held-out** (blind-graded,
**once**), clears **precision ≥ 90% AND recall ≥ 90%** — aim precision *higher*
(~95%) where you can, because a wrong/duplicate driver is **permanent** registry
pollution; **defer** is allowed and is **not** a precision miss (report defer-rate
separately). On the **adversarial held-out**: no catastrophic errors + graceful
defer — do **not** demand 90% there (it is the floor, not the expectation).

**A below-bar held-out result is a NO-GO — and is NOT permission to tune on
held-out.** Treat `<90% precision OR <90% recall` on the representative held-out
as a hard NO-GO. When it happens:
1. **Stop.** Do not start fixing against the held-out errors — that burns the set.
2. **Report the failure CLASSES** (the *kinds* of error, not the individual items).
3. **Propose the next smallest experiment** that targets a class.
4. Run that experiment **on dev**, then judge it with a **FRESH held-out** (the
   burned one cannot be reused).

Iterate only on dev / a tuning set; the held-out is opened once per judgment.
**Honesty clause:** never fudge the metric or add rules to force the set to pass.
The goal is *the simplest design that clears the bar on **unseen** data, honest
about the residual* — **not "perfect."**

---

## 1. Read these first (in this order)

| # | File (`.claude/plans/Drivers/` unless noted) | Why |
|---|---|---|
| 1 | **PART II of this file — "Full Empirical Record"** | The autopsy of why the current design fails: the 82% finding, the self-locking trap, worked examples, reproduction commands, source index. **Read it — it is the required empirical context.** (Formerly the standalone `nonExhaustiveIssue.md`, now embedded here so this file stands alone.) |
| 2 | **`ConceptualRequirements.md`** | What the system is *for* — producers, global registry, usages, tensions. |
| 3 | **`DriverNameRisks.md`** | Risk source material (~100+ items, 4 overlapping lists). Do **not** count it literally; deduplicate it into atomic failure modes before claiming coverage. |
| 4 | **`DriverOntology.md`** | The *current* naming contract (R1–R11). Understand it; keep/change/discard freely. |
| 5 | **`DoubtsInHTML.md`** | 50+ open owner questions. §10 here lists the ones you must resolve. |
| 6 | **`drivers_harness/pass4/eval_corpus.json`** | **61 real evidence→driver examples** (snippet + expected driver/state/direction). Use as concrete "what good looks like" — **example material, NOT locked truth.** |
| 7 | `.claude/plans/extraction-pipeline-reference.md` | Working guidance-extraction precedent to inspect for production shape, evidence handling, and orchestration patterns. Reuse only what fits drivers. |
| 8 | `Final.md` (predictor/learner) §7–§8 | The learner/predictor I/O contract (see §6 here). |
| 9 | `CombinedPlan.md`, `DriverOntology_Implementation.md`, `Harness/Harness_BuilderPrompt.md`, `drivers_harness/` (code) | Background on what exists + how it's built/tested. **Not** unquestioned authority. |

Verify every claim in this brief against those sources + the code. If something
conflicts, trust the source and flag it.

---

## 2. PROVEN FACTS vs DESIGN OPINIONS (do not blur these)

This is the most important section. Separate what is **empirically established**
from what is **a hypothesis to explore**.

### 2a. ✅ Proven (empirical — you may rely on these)
- **The closed-vocabulary canonicalizer rejects ~82% of even the *correct* gold
  driver names** on the cold seed (7/39 OK). Reproducible (**Part II §E2**). The
  82% failure is in the vocabulary/canonicalize gate itself; even a perfect
  producer would hit it.
- **Mechanism of failure is structural:** a novel non-metric token can't be
  uniquely slotted (≥2 candidate slots ⇒ reject), and `canonicalize` rejects it
  **before** the token-learning step runs — so the vocab **cannot self-warm**
  (**Part II §E3–§E4**).
- **LLM extraction is promising but not proven at production accuracy.** In the
  stress run, in-session producer LLMs reading only evidence produced plausible
  driver tags across all 61 snippets, but the scored result was only a lenient
  raw-extraction proxy, not the full pipeline and not a proof of near-100
  extraction reliability. Treat "evidence → driver candidate" as a likely useful
  LLM task that still needs a production-faithful eval.
- **A cached, structured LLM judge mechanism works** (`judge_llm.py`): OpenAI
  strict JSON schema, tiered escalation (cheap model → stronger model on hard
  cases), persistent content-hash cache that replays across processes, fail-safe
  defer, and "don't cache failure-path defers". The **mechanics** are proven live
  (e.g. `cogs`→`cost_of_goods_sold`). Its **accuracy at scale is not yet measured.**
- **Pass 1–3 deterministic machinery is "green" (350 tests)** — BUT those tests
  validate the machinery *on top of the broken canonicalize foundation*. Green
  tests here do **not** mean the approach is sound.
- **The stress-scorer `0.634` name+dir number is NOT a pipeline result.** It used
  a lenient synonym-token scorer with **no** `canonicalize`. Do not quote it as
  production accuracy.
- **The guidance-extraction pipeline is a proven local precedent to study and
  potentially reuse**, especially for source refs, quote/evidence handling,
  worker/orchestrator shape, and productionization. Do not copy assumptions that
  do not fit driver identity.
- **Embedding infrastructure exists** (Neo4j vector indexes, text-embedding-3-large,
  3072-d cosine). Its *existence* is proven; its *usefulness for driver identity*
  is not.

### 2b. ❓ Opinion / unproven (explore — do NOT assume)
- An **open-world "registry-is-the-vocabulary"** design. (A hypothesis.)
- The **role and accuracy of embeddings** for driver identity — especially
  separating **same-object/different-metric** (`aws_revenue` vs `aws_capex`) and
  **similar-words/different-mechanism** (`oil_price` vs `oil_supply`). (Unproven;
  a known risk.)
- A **recurrence-≥2 admission gate** before a new name becomes globally reusable.
- The **exact state model** (free-text vs polarity vs clustered labels).
- Whether to **call an LLM on every event** vs cache/layer to bound calls.
- The **specific-vs-generic** naming policy (one policy vs producer-dependent).

Your design report must keep this fact/opinion separation explicit.

---

## 3. What the system is supposed to do

A **Driver** = a *reusable causal variable that moves a stock price*
(`oil_price`, `iphone_china_sales`, `gross_margin`, `medical_care_ratio`,
`aws_revenue`). Not a one-off event — a reusable concept.

A **DriverChange** = one *observed instance* of a driver in a specific source /
time / company-event, carrying a `driver_state` (what happened), a `direction`
(stock impact), and grounded `evidence`. **One driver → many events; one event →
many drivers.**

**The core job:** maintain **one global driver registry** that every producer
consults and **reuses before creating**, so the same concept never fragments
(`iphone_china_sales` / `china_iphone_sales` / `iphone_china_demand`) across runs,
LLMs, companies, and years.

**Producers:**
- **earnings-learner** — the **only Phase-1 producer; your focus.** Reads a
  company's 8-K (by design) + the transcript (tag transcript drivers separately).
  Emits drivers it is *confident* about: `primary_driver` + `contributing_factors`
  (not limited to one).
- **news** (Phase 2) — mostly macro/sector causes, found from a significant stock
  move → its cause. **Empirically provable / tradeable.** May hit many companies
  with **asymmetric** impact.
- **fiscal.ai** (Phase 3) — KPIs from 10-K/10-Q/presentations; no `event_id`
  (carries company+quarter); exempt from the naming contract for raw ingest.
- **earnings-predictor** — **CONSUMER ONLY.** Reads driver tags on prior learner
  reports (to retrieve relevant reports) + the registry catalog. Never writes.

**Usages (why this matters):** (a) predictor retrieves the *right* prior reports
by driver-relatedness; (b) the driver↔event graph tells the predictor "what moves
this stock"; (c) news drivers feed empirical trigger/backtest/trade pipelines.

**A real tension to resolve (ConceptualRequirements §8):** more **specific**
names help the predictor find its *own* prior report; more **generic** names help
*peer* retrieval + news cross-company matching. Maybe not one answer for all.

---

## 4. The failure you must not repeat (the lesson)

The current system canonicalizes by parsing names into fixed slots
(`theme,object,customer,geography,institution,metric`) against **closed
hand-enumerated lists** (≈9 objects, ≈29 metrics for *all of finance*), plus
closed synonym/acronym/plural/shortcut/banned maps, plus a closed 37-token state
list. Finance is open-world → the lists can't enumerate it → novel inputs get
**rejected** → 82% (§2a). **Full empirical record: Part II of this file (§E1–§E8).**

**Hard constraint:** do not build any component whose correctness requires
pre-enumerating an open-world set, and do not let a missing vocabulary entry
(token **or** state) *reject* a valid, evidence-grounded driver. Lists may still
be useful as hints, examples, normalization aids, or finite mechanical guards,
but they must not be the sole authority over open-world validity. "Bigger list"
and "an NLP library that knows everything" are non-fixes — they re-arm the same
failure.

---

## 5. Hard constraints / owner concerns (address each explicitly)

1. **No exhaustive curated vocabulary requirement** anywhere (objects, metrics,
   states, shortcuts, synonyms, acronyms, geographies, compounds). If a list is
   used, prove it is finite/mechanical, or make it advisory/revisitable rather
   than a hard validity gate.
2. **Vocabularies, if used, are not hard gates** — they may normalize/suggest/
   explain, never permanently reject a valid novel concept.
3. **States are open-ended** — a missing state word must not reject the driver.
4. **LLM calls are allowed** — use them where they cut code complexity or improve
   semantic accuracy; keep them **bounded, cached, auditable, fail-safe**.
5. **Embeddings: careful** — be explicit whether they *retrieve candidates*,
   *decide matches*, or *only assist review*. Never a hidden source of truth
   unless proven (see the `aws_revenue` vs `aws_capex` risk).
6. **No runtime human-curation bottleneck** — audits + reversible corrections OK;
   production flow autonomous.
7. **PIT / backtest integrity** — historical runs must not see future registry
   entries, aliases, decisions, or prompts. PIT filtering explicit.
8. **Evidence grounding** — no abstract drivers invented without event evidence.
9. **Minimalism** — delete machinery that only existed to prop up brittle
   vocab/grammar assumptions; keep what protects precision/recall.
10. **Easy to productionize** — align with the working guidance-extraction
    pattern where helpful; don't copy its unsuitable assumptions blindly.
11. **Direction is non-deterministic + time-/company-varying** — the owner leans
    toward direction living on an **edge** (event/company → driver_change) so it
    can be aggregated, not baked into the name or a single property. Decide +
    justify.
12. **Decide-once / replayable** — once a semantic decision is made, it must be
    replayable by code (e.g. via cache), logged, and **reversible** if later
    evidence proves it wrong.

---

## 6. The concrete I/O contract + scale (so you design for reality)

- **Learner input:** a company-quarter's evidence — 8-K text (primary) +
  transcript (+ optionally other quarter sources), with source references
  (`SRC:*` IDs that resolve to a source catalog). PIT cutoff per run.
- **Learner output (`learner_result`, see `Final.md §8`):** `primary_driver` +
  `contributing_factors[]` + `propose_new_drivers[]`. Each driver tag carries
  name + state + direction + evidence (and today, companion fields). Decide which
  fields are truly required.
- **Predictor (`Final.md §7`)** keeps `key_drivers[]` as **free-form prose** — NOT
  canonical drivers, never written to the registry. (Predictor = consumer.)
- **Data-model precedent:** `GuidanceUpdate` (Neo4j) is a *working* node type with
  `source_refs`, `quote`, evidence hashing, and `MAPS_TO_CONCEPT`/`MAPS_TO_MEMBER`
  edges. The DriverChange model can mirror it — study it before inventing.
- **Scale:** ~750 tradeable tickers; thousands of events; **multi-year historical
  backfill** (so PIT-replay + decide-once-cache + per-event cost all matter).

---

## 7. Tools available to you now (beyond Python)

The old design's constraint was "deterministic code only, no LLM." That is
**lifted.** Available building blocks:

| Tool | Use it for | Notes |
|---|---|---|
| **Python / deterministic code** | format normalization, finite enums, hashing, caching, graph queries, math | the genuinely mechanical sliver |
| **Real LLM calls (individual)** | extraction, identity/reuse decisions, novelty/durability judgment, state mapping | subscription (interactive) = free; metered cheap models OK for bounded judge calls |
| **Strict JSON / structured outputs** | force valid, schema-constrained LLM output | proven (OpenAI strict mode) |
| **Cached decisions** | replay-stable, PIT-safe determinism from a non-deterministic step | content-hash key + persistent store; proven (`FileCache`) |
| **Embeddings / vector search** | *retrieve* candidate existing drivers for a judge to compare | **skeptical**: don't auto-decide identity; prove it before trusting |
| **Producer self-feedback loop** | the producing LLM validates its own tags in-session, reads per-tag feedback, fixes, re-checks | in-session = free; bounded loops |
| **Cheaper-model triage/confirmation** | high-volume confirmation (e.g. "does this driver appear in this text?") | a cheap model (haiku/mini) |
| **Guidance-extraction pipeline template** | a working trigger→queue→worker→extract→agent-shell + per-type prompt pattern | study/reuse where it truly fits |
| **Neo4j graph store** | the registry + DriverChange + edges | `GuidanceUpdate` precedent |
| **Real-LLM test harness** | isolated, test-first build with the toughest cases | the build methodology (below) |
| **Run access** | you can actually **run** Neo4j, LLMs, embeddings, and the harness to **empirically test** a design idea before committing | e.g. run the embedding-separation spike yourself |

**Billing (hard):** free in-session/agent work runs on the **interactive Claude
subscription**, NOT `claude_agent_sdk` / `claude -p` (those are metered). A cheap
metered model (e.g. an OpenAI mini) is fine for bounded cached judge calls. See
`CLAUDE.md` + `ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md`.

---

## 8. Finite vs open-world axes (a lens — evaluate, don't assume final)

| Genuinely finite (closed enum OK) | Open-world (must NOT be behind a closed gate) |
|---|---|
| outcome: admit / reuse / reject / defer | driver concepts |
| direction: long / short (± neutral/unknown if justified) | products / brands / geos / customer segments / mechanisms |
| source type: learner / news / fiscal / transcript… | metrics & KPI phrasings |
| decision status + audit reason codes | state wording & nuance |
| | aliases / synonyms / paraphrases / acronyms |
| | one-off vs reusable boundary |

If any design puts an apparently open-world axis behind a closed enum, finite
grammar, or static list, it must explain why that axis is actually finite in the
intended use, or why the list is only advisory and cannot recreate the 82%-reject
failure.

---

## 9. The risk source material (condense `DriverNameRisks.md` → mechanisms)

Your design must prevent or detect: duplicate concepts under different names ·
word-order drift · synonym drift (sales/revenue/topline, COGS/cost, FICC/fixed
income) · too-generic (pollutes retrieval) · too-specific (never repeats) ·
one-off admitted as durable · multiple mechanisms compressed into one name ·
state/direction/magnitude/time/source baked into the name · ticker/company/
person/event-id/XBRL/provider leakage · product-vs-company (`iphone_sales` ok,
`apple_sales` usually not) · missing/wrong discriminator · alias overmerge · alias
undermatch · wrong direction / state-direction confusion · evidence-free proposal
· PIT leakage · registry pollution from weak names · reuse failure when a fit
exists · **false rejection of a valid novel driver** (the 82% sin).

---

## 10. Open questions you must resolve (decide + justify; don't inherit)

1. **How do you get consistency (same concept → one name) WITHOUT a closed
   vocabulary?** (The central question.)
2. **States** — open-world *and* aggregatable, no forced fit, no fake mismatch
   (e.g. rising cost ratio: `expanded` vs `deteriorated`). Keep direction separate
   from state.
3. **Direction** — edge vs property; how aggregated across time/companies (§5.11).
4. **Companion fields** — which of `alias`/`segment`/`base_label`/`allowed_states`/
   `definition` actually earn their place?
5. **Specific vs generic** naming — one policy or producer-dependent?
6. **Reuse / self-correction** — does the producer self-validate before emitting,
   is identity resolved downstream, or both?
7. **The exact LLM-vs-code boundary** — draw it explicitly (the old one was wrong).
8. **Reuse vs new vs defer vs (ever) permanent-reject** — the decision ladder.
9. **Duplicate discovery + merge/unmerge** (reversible reconciliation).
10. **PIT semantics** per producer + replay stability + cache time-scoping.
11. **News cross-company asymmetric impact** representation.
12. **Predictor report-retrieval** by driver relatedness.
13. **fiscal.ai** non-conforming labels coexisting with the canonical registry.
14. **Cost** bounding at the §6 scale.

---

## 11. Architecture exploration (REQUIRED — produce options, not one answer)

Compare **at least 3 genuinely different architectures**, including (but not
limited to):
- **(A) Mostly-LLM** — LLM does extraction + identity + admission; code is thin
  glue + cache.
- **(B) Registry + judge** — code retrieves candidates from the growing registry;
  a cached LLM judge decides reuse/new/defer.
- **(C) Hybrid deterministic + semantic** — mechanical normalization/enums where
  truly finite; LLM/semantic only for the open-world identity decisions.

For each: pros/cons, **precision/recall risk**, cost, latency, determinism,
simplicity, productionization. **Do not strawman.** Then **recommend the one that
is simplest and closest to 100/100**, and say what it gives up. Do **not** anchor
on open-world / embedding / LLM-every-time assumptions — let the comparison decide.

---

## 12. What to deliver (a design report, not yet code)

0. **Falsify-first evidence (THE GATE — produce this BEFORE any recommendation, per §0.5).**
   The held-out benchmark you built, the **dumbest-baseline** result on it, and a
   **real recall/precision number for your recommended pipeline** on it (run with
   real LLMs, on un-curated data). A recommendation without this measured number is
   rejected as a hypothesis, not a design.
1. **Executive summary** — the simplest design you recommend; what to delete; what
   to keep.
2. **Plain-English model** — Driver, DriverChange, producer, registry, catalog,
   alias, state, direction, evidence, PIT.
3. **Requirements trace** — map ConceptualRequirements + the key doubts → choices.
4. **Failure analysis** — why closed-vocab failed; other likely hidden failures.
5. **Options considered** — the ≥3 architectures (§11), fairly compared.
6. **Recommended minimal architecture** — exact flow; which parts are code / LLM /
   embedding / cache / DB / test; why it's simpler than today.
7. **Data model** — Driver / DriverChange / alias / decision / audit / PIT /
   evidence fields.
8. **LLM contracts** — prompt roles, strict schemas, what the model sees / must
   not see (PIT), failure/defer handling, what's cached.
9. **Identity / reconciliation** — reuse/new/defer/reject; dup prevention; later
   dup discovery; merge/unmerge.
10. **State strategy** — open-world state + separate direction.
11. **PIT & backtest integrity** — visibility per event; cache versioning/time-scoping.
12. **Test & eval plan** — unit + **real-LLM** integration + stress corpus +
    **representative random sample** for expected production accuracy; metrics:
    recall, precision, duplicate rate, false-reject, false-admit, merge-error,
    defer rate, cost, latency. **Score the actual production pipeline**, not a
    lenient proxy, and never report stress-set accuracy as production accuracy.
13. **Migration plan** — what to remove/keep from the current harness; what to
    build first; what must be proven before any real ingestion.
14. **Open questions** — only decisions that truly need the owner.

**Checkpoint:** after deliverable #2 (Plain-English model + your understanding),
**pause and confirm with the owner** before designing further.

---

## 13. Ground rules

- **Verify against primary sources** (cite file/line for current-behavior claims).
- **Keep proven facts (§2a) separate from opinions (§2b).** Don't smuggle a
  hypothesis in as a fact.
- **Do not repeat the closed-list failure** — no pre-enumerated domain list may
  be a required completeness condition for an open-world decision; no missing
  vocab/state may reject a valid driver.
- **Don't report stress-set accuracy as production accuracy**; don't build a
  catalog-fed run from gold labels or from raw producer guesses (unless explicitly
  labeled as such).
- **Don't let embeddings silently decide merges** unless you prove it's safe.
- **No runtime human curation.** Be honest about literal 100%: if irreducible
  ambiguity remains, say so and show how audit + reversibility closes the gap over
  time.
- **Minimalism with teeth** — every kept component must earn its place; complexity
  must be paid for by a measured gain (§0.5).
- **Falsify before you recommend (§0.5)** — no architecture is recommended without
  a real recall/precision number on a held-out benchmark through its real pipeline;
  build the dumbest baseline first; design blind-first; distrust green; never call
  a proxy "accuracy."
- **Plain language** — short, crux-first, jargon-free, small visuals (tables/ASCII).
  The owner is explicitly skeptical of prior ChatGPT *and* Claude choices; be
  critical and first-principles; rubber-stamp nothing (including your own ideas).

---
---

# PART II — FULL EMPIRICAL RECORD: The Non-Exhaustive Vocabulary Failure

> **This is the full empirical record** — originally the standalone
> `nonExhaustiveIssue.md`, now embedded here as the **sole copy** (that file has
> been removed). Everything here is re-verifiable; **§E8** lists the exact files,
> line numbers, and runnable commands.
> **Severity:** architectural — a structural ceiling baked into the Pass-1→3 core,
> not a bug in one function.

## E0. One-paragraph summary

The driver-naming system turns a messy extracted phrase (e.g. `"AWS cloud
revenue"`) into ONE reusable canonical name (e.g. `aws_revenue`) by **parsing it
into grammatical slots against closed, hand-enumerated token lists** (which words
are "objects", which are "metrics", which acronyms expand to what…), and forces
the "state" of the move into a **closed list of 37 tokens**. Finance is
**open-world** (companies, products, KPIs, drugs, macro themes, and nuance grow
forever), so a closed list **cannot** enumerate them and the parser **rejects
anything it was not pre-taught**. Measured: on the cold seed the real
`canonicalize` rejects **82% of even the *correct* gold names**. And it is
**self-locking**: a name must canonicalize *before* its novel tokens can be
learned, but the names containing novel tokens are exactly the ones it rejects —
so the vocabulary **cannot grow itself** out of the hole. Enlarging the seed only
moves the cliff; the next unknown ticker/metric/state falls off it.

## E1. The full inventory of closed lists (measured sizes)

This is bigger than the slot grammar. **Every** layer of the cleaner leans on a
hand-curated, finite list. Measured sizes on the current seed:

| Closed list | Size | Covers (supposed to) | Nature | Verdict |
|---|---:|---|---|---|
| `slot_vocabs[theme]` | 8 | every market theme | open-world | ❌ |
| `slot_vocabs[object]` | **9** | **every product/segment in the market** | open-world | ❌ |
| `slot_vocabs[customer]` | 5 | every customer type | semi-open | ❌ |
| `slot_vocabs[geography]` | 10 | every geography | semi-finite | ⚠️ |
| `slot_vocabs[institution]` | 8 | every regulator/CB | semi-finite | ⚠️ |
| `slot_vocabs[metric]` | **29** | **every financial/KPI metric** | open-world | ❌ |
| `SYNONYM_MAP` | 3 | every synonym pair (topline→revenue…) | open-world | ❌ |
| `ACRONYM_MAP` | 9 | every acronym (gm→gross_margin, ficc…) | open-world | ❌ |
| `PLURAL_MAP` | 16 | English plurals | **mechanical morphology** | ✅ (NLP-able) |
| `SHORTCUTS_VOCAB` | 22 | macro shortcuts (fed_rate, yield_curve, fda_approval) | open-world | ❌ |
| `COMPOUND_METRICS` | 12 | compound substitutions (data_center→datacenter, gross_profit→gross_margin) | open-world | ❌ |
| `BANNED` (§F.7) | 118 | tickers/company names/GAAP/people | open-world | ❌ |
| `STOPWORDS` | 15 | filler words | mostly mechanical | ⚠️ |
| `STATES` / `STATE_CLASSES` | **37 / 7** | every kind of move + class | open-world nuance | ❌ |

Read the bold numbers literally: **9 object tokens and 29 metric tokens are
expected to canonicalize every driver in the entire market.** They cannot. Every
❌ row is a place where an unknown input silently rejects or mis-folds, and each
needs perpetual human curation to stay even partially current.

## E2. The killer finding — 82% of the *correct* names rejected

We ran the **real** `canonicalize` (first gate of `run_one`) over the Pass-4
corpus, on the cold seed (`COLD_START_SEED_DRIVERS` = 10 drivers: `oil_price,
oil_supply, fed_rate, yield_curve, fda_approval, gross_margin, revenue, sales,
eps, forward_guidance`).

| Name set tested | canon-OK | canon-REJECT | top reasons |
|---|---|---|---|
| **GOLD canonical names** (correct answers) | **18%** (7/39) | **82%** | slot_ambiguous 16, slot_anchor_unavailable 10, banned 5, collision 1 |
| GOLD allowed-alternatives | 18% (11/60) | 82% | slot_ambiguous 24, anchor 20, banned 5 |
| Producer's extracted names | 21% (10/47) | 79% | slot_ambiguous 22, anchor 8, banned 6, collision 1 |

Rejected set includes nearly every realistic name: `aws_revenue`, `battery_cost`,
`asset_management_revenue`, `available_seat_miles`, `vehicle_deliveries`,
`medical_care_ratio`, `net_sales`, `foreign_exchange`, `cost_per_vehicle`,
`comparable_store_sales`, `channel_inventory`, `ai_chip_demand`,
`regulatory_credit_revenue`.

**Why test the gold names:** if even the *human-correct* names reject 82% of the
time, the bottleneck is **the vocabulary, not the producer.** A perfect producer
still fails.

**Reproduce it:**

```bash
cd drivers_harness
../venv/bin/python -c "
import json, collections, vocab_seed as vs
from driver_ids import canonicalize, Rejection
vocab = vs.build_vocab_snapshot()
gold = json.load(open('pass4/eval_corpus.json'))['corpus']
names = sorted({gd['name'] for x in gold for gd in x['gold']['expected_drivers']})
ok  = [n for n in names if not isinstance(canonicalize(n, vocab), Rejection)]
rej = collections.Counter(canonicalize(n,vocab).reason for n in names if isinstance(canonicalize(n,vocab),Rejection))
print(f'canon-OK {len(ok)}/{len(names)} = {len(ok)/len(names):.0%}'); print('reasons:', dict(rej))
"
# -> canon-OK 7/39 = 18%   reasons: {'slot_ambiguous':16,'slot_anchor_unavailable':10,'banned_token':5,'slot_collision':1}
```

## E3. Root cause, mechanically (why these names reject)

`SLOT_ORDER = (theme, object, customer, geography, institution, metric)`; slot
assignment is **exact-match membership in closed frozensets**; an unknown token is
`UNKNOWN`; `resolve_unknown_slots` rejects unless a novel token lands in **exactly
one** free slot.

**`aws_revenue` → `slot_ambiguous`:**
```
tokens = [aws, revenue]
classify: aws -> UNKNOWN (not in OBJECTS);  revenue -> metric (in METRICS)
resolve_unknown_slots: aws must be placed strictly LEFT of the metric anchor.
   free slots in (start .. metric) = {theme, object, customer, geography, institution} = 5
   rule (driver_ids.py:143):  if len(free) != 1 -> REJECT, never guess
   5 != 1  ->  REJECTION_SLOT_AMBIGUOUS("aws")
```
A **single novel non-metric token** before a metric has **five** candidate slots →
the code refuses to guess → rejects. So *almost any* new `object_metric` name
(`channel_inventory`, `ai_chip_demand`, `net_sales`…) is rejected.

**`battery_cost` → `slot_anchor_unavailable`:**
```
tokens = [battery, cost];  both UNKNOWN  ->  no anchor  ->  REJECTION_SLOT_ANCHOR_UNAVAILABLE  [driver_ids.py:133]
```

**Reject-reason taxonomy:**

| reason | meaning | example |
|---|---|---|
| `slot_anchor_unavailable` | every token UNKNOWN | `battery_cost`, `foreign_exchange`, `medical_care_ratio` |
| `slot_ambiguous` | UNKNOWN token's slot not unique (0 or >1 free) | `aws_revenue`, `net_sales` |
| `slot_collision` | two tokens claim one slot | mixed metric-ish tokens |
| `banned_token` | a token on the §F.7 banned list | `fixed_income_trading_revenue` |

**The code itself admits the real answer is a judgment call** —
`resolve_unknown_slots` docstring (`driver_ids.py:122-132`):

> "…the **TRUE semantic slot of a novel token remains LLM-judgment** — this rule
> only mechanically PLACES it and rejects when placement is not unique."

The authors knew the correct slotting is *semantic*, but implemented it as
*mechanical exact-match against a closed list*. That mismatch **is** the bug.

## E4. The self-locking trap (the vocabulary cannot grow itself)

The harness *has* a learn-new-token seam (`reuse._new_slot_tokens` + the `V14`
gate) — but it is **unreachable for the names that need it**, due to control-flow
order in the B1..B10 ladder:

```
reuse_or_propose(raw_name, ...)                          [reuse.py:144]
  B5 canonical = canonicalize(raw_name, vocab)           [reuse.py:188]
       if Rejection:  return REJECT   ◄── DIES HERE for unknown tokens
  ...
  B10 _new_slot_tokens(canonical, ...)                   [reuse.py:242]  ◄── token-learning seam
       (only reached if B5 produced a canonical string)
```

A name rejected at B5 never reaches B10, so its novel tokens are **never
registered**:
```
aws_revenue --B5 reject (slot_ambiguous)--> aws never learned
   next event aws_capex / aws_margin --B5 reject again--> aws still never learned ... forever.
```
The system can only learn what it nearly already knew. **The cold start cannot
bootstrap out of ambiguity.**

**Corollary — no recurrence gate either.** A structurally-valid `PROPOSE_NEW` is
accepted on *first sight* (`run_one.py:195`). The N=2 machinery
(`synonym_fold.SynonymFoldEngine`, `PROMOTION_THRESHOLD=2`) governs only **synonym
folds** (token→token), **not** new-name admission. So the "recurrence ≥2 before
admission" design is **not** what filters today; raw canonicalize strictness is.

## E5. States have the identical disease

The state is forced into 37 tokens across 7 classes; validators `V8`/`V6` reject
anything outside, and require it to come from **one class** (`allowed_states`):
```
trend_motion: accelerated, decelerated, compressed, declined, stable
quantity_move: exhausted, cleared, accumulated, contracted, built, cut, expanded
policy_action: denied, restricted, approved, imposed, eased, lapsed, lifted
rate_curve: normalized, steepened, inverted, flattened
event_lifecycle: initiated, completed, announced, cancelled, delayed
financial_outcome: missed, raised, beat, inline, reaffirmed, withdrawn, lowered
sentiment_motion: improved, deteriorated
```
- Real moves don't fit cleanly: *"guidance withdrawn then reinstated"*, *"demand
  bifurcated by region"*, *"margin inflected"* — no clean token.
- **Forcing a fit loses info AND manufactures fake mismatches.** Concrete case
  from Pass-4 scoring: a rising medical-cost ratio (MCR) — `expanded` (ratio grew)
  or `deteriorated` (it worsened)? Both defensible; the closed list makes you pick
  one, then a producer that picked the other scores as **wrong** — a fake failure
  invented by the vocabulary, not a real disagreement.

## E6. The one-sentence diagnosis (LLM-vs-code boundary)

> **The system uses deterministic code against a closed list to answer questions
> that are open-world and semantic.**

| Question | Current (closed code) | Reality |
|---|---|---|
| "Is `aws` an object or a metric?" | exact-match in `OBJECTS`/`METRICS` | a meaning judgment |
| "Is `comp_sales` the same as `comparable_store_sales`?" | only if grammar/aliases match | a meaning judgment |
| "Is `strengthened` the same move as `accelerated`?" | only if both ∈ 37 tokens | a meaning judgment |

Closed code returns "yes" only for what it was pre-told → it **over-rejects
everything novel** → the 82%. Note the split: *plurals/stopwords* are mechanical
morphology (genuinely finite — a lemmatizer is one option worth evaluating), but
*object/metric/state/synonym/acronym identity* is **not** solvable by any closed
list or NLP gazetteer (those are themselves closed) — it is open-world semantic
judgment. (Don't read this as prescribing a particular tool; it only marks which
part is mechanical vs semantic.)

## E7. Blast radius (what this invalidates)

- **Pass 1–3 core.** `driver_ids.canonicalize` + closed `slot_vocabs` + the closed
  `STATES` gate are the load-bearing center. The 82% finding means that center
  cannot carry an open-world load.
- **Pass-4 eval is not meaningful on the cold seed.** Any `production_catalog_fed`
  number against this canonicalize measures *vocabulary strictness*, not
  naming/reuse/judge quality — the registry stays near-empty, so the catalog never
  grows.
- **Earlier interim number has a caveat.** `stress_catalog_blind ≈ 0.634`
  (name+dir recall) came from a **lenient scorer** (`pass4/score_eval.py`) that
  matched names by synonym-normalized token sets and **did not run `canonicalize`**.
  It measured *producer naming under generous matching*, NOT what the pipeline
  admits (~20%). Don't quote 0.634 as a pipeline result.

## E8. Primary-source index (re-verify everything)

| Claim | Source |
|---|---|
| 6 closed slots | `driver_ids.py:60` `SLOT_ORDER` |
| slot assignment = exact-match in closed sets | `driver_ids.py:111` `classify_token` |
| novel token rejected unless uniquely placeable | `driver_ids.py:122-148` (reject `:134`, `:143-144`) |
| code admits true slot is "LLM-judgment" | `driver_ids.py:122-132` docstring |
| reject-reason constructors | `driver_ids.py:78-104` |
| slot vocabs are hand-enumerated frozensets | `vocab_seed.py:500-509` |
| fold maps / shortcuts / banned / stopwords built here | `vocab_seed.py:511-535` |
| 37 states / 7 classes | `vocab_seed.py` `STATES` (`:172`), `STATE_CLASSES` (`:156`) |
| state gate (one class) | `validators.py` `V8_state_in_allowed`, `V6_allowed_states` |
| canonicalize dies at B5 before token-learning at B10 | `reuse.py:188-191`, `reuse.py:242` |
| no recurrence gate on new-name admission | `run_one.py:195-197` |
| N=2 governs synonym folds only | `synonym_fold.py:72`, docstring `:29-45` |
| cold seed = 10 drivers | `vocab_seed.py:581` `COLD_START_SEED_DRIVERS` |
| lenient Pass-4 scorer (no canonicalize) | `pass4/score_eval.py:1-8` |

List-sizes probe:
```bash
cd drivers_harness
../venv/bin/python -c "
import vocab_seed as vs; v=vs.build_vocab_snapshot()
for k,s in v.slot_vocabs.items(): print('slot',k,len(s))
print('synonym',len(v.synonym_map),'plural',len(v.plural_map),'acronym',len(v.acronym_map))
print('shortcuts',len(v.shortcuts),'banned',len(v.banned),'stopwords',len(v.stopwords))
print('STATES',len(vs.STATES),'CLASSES',len(vs.STATE_CLASSES))
"
# slot theme 8 / object 9 / customer 5 / geography 10 / institution 8 / metric 29
# synonym 3 plural 16 acronym 9 ; shortcuts 22 banned 118 stopwords 15 ; STATES 37 CLASSES 7
```

Per-name canonicalize verdict + token→slot membership:
```bash
../venv/bin/python -c "
import vocab_seed as vs; from driver_ids import canonicalize, Rejection
v=vs.build_vocab_snapshot()
for n in ['aws_revenue','battery_cost','iphone_china_sales','net_sales','vehicle_deliveries']:
    c=canonicalize(n,v); print(n, '->', getattr(c,'reason','OK:'+str(c)))
"
../venv/bin/python -c "
import vocab_seed as vs; v=vs.build_vocab_snapshot()
for t in ['revenue','aws','battery','iphone','china','store']:
    print(t, [k for k,s in v.slot_vocabs.items() if t in s] or 'UNKNOWN')
"
```

## Appendix A — owner's original raw notes (verbatim, the seed for the failure doc)

> Same non-exhaustive issue with things like "oil_price".
>
> SHORTCUTS_VOCAB - yield_curve, fda_approval - again impossible to have an exhaustive determinisic list unless I am missing something.
>
> This is another issue of non-exhaustive (plus mainatenance etc without human intervention) list COMPOUND SUBSTITUTION since we can't possible have all these before hand?
>     data_center  → datacenter
>     gross_profit → gross_margin
>     ACRONYM_MAP, PLURAL_MAP, SYNONYM_MAP, BANNED_CONTENT, SHORTCUTS_VOCAB, GEOGRAPHIES, OBJECTS, METRICS
>
> should we instead be using an NLP librray for Vocab to get ~100% accuracy - upside, doenside ? and will it be able to cover all since we need to seed all these with exhaustive list for full deterministic matches? am i missing something? Also see the non-exhaustive issue in "Closed vocabulary. Every token must be in a vocab bank OR in a registry name/alias."
> Also like DRIVER REGISTRY, is VOCAB EXCERPT specific to a company?
>
> I am assuminmg here it means we already have a list of classes that define all states inside that class - looks non exhaustive? "allowed_states from one class"?
>
> "Apply synonym map" - does this mean it can only be appled if we already ahve a curated list of drivers and synonyms or does the llm smart to see what already exists and then us ethat as a synonym - since otherwise this curated list smells of super bad design ? Same for "acronym map", "standalone shortcut", "macro shortcuts" and "stop words" and so on. - is there a NLP library which can resolve this with 100% accuracy?
> - the primary issue is of using a non -exhaustive list of specific words which we dont want to curate in a deterministic layer.
> - same non exhaustive issue with "every shape + grammar + banned-content rule."
>
> driver tag - driver_state. Issue is allowed states may not be exhaustive - how to ensure nothing gets missed or wrongly categorized? "Drawn from this driver's allowed_states"?

> **Answers to the three questions in the notes above** (so the next bot has them):
> **NLP library?** A lemmatizer can handle plurals/stopwords better than a tiny
> hand list because English morphology is relatively mechanical; evaluate whether
> it should replace `PLURAL_MAP`/`STOPWORDS`. It gives **0%** of the
> open-world concept-identity need (is `aws` an object? is `comp_sales` the same as
> `comparable_store_sales`?) — any NER gazetteer is itself a closed list, so it
> re-arms the same failure. **Company-specific vocab?** It is global today, which is
> *worse* (one list must hold every company's products); company-scoping a closed
> list doesn't save it. **`allowed_states` from one class?** Same closed-list disease
> (§E5) — a missing state must not reject a valid driver.
