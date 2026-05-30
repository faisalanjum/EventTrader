# Driver Naming — Isolated Test Harness — BUILDER PROMPT  *(canonical / final)*

> **Who this is for:** a build bot/engineer with **NO prior context**. You build an isolated, fully-tested
> implementation of the **entire driver-CREATION layer** (everything up to — but NOT including — the real
> Neo4j ingestion write). A separate tester (Claude) + the project owner throw adversarial cases and real-LLM
> evidence at it and iterate with you. When everything passes, the core modules copy into production.
>
> **Repo:** `/home/faisal/EventMarketDB`  ·  **Build target:** `drivers_harness/` (repo root).
> Single canonical brief; supersedes the deleted `drivers_harness/BUILD_PROMPT.md`.

---

## 0. Mission + prime directive

Build the smallest thing that correctly turns evidence → a clean, canonical, validated driver name (reusing
an existing driver when one matches, proposing a new one only when justified) → a "would-write" decision.
Pure Python. No production wiring, no database. **Every component and every pass below is FULLY DEFINED
now**, so you can eventually build the whole infrastructure in isolation — you just build it in **4
checkpointed passes** and stop after each for review.

**PRIME DIRECTIVE — MINIMAL-FIRST + HARD STOP + FULLY-DEFINED. Four passes (STOP + await authorization after EACH):**
- **Pass 1** — deterministic CORE (§4 + §6) — **GATED 100%**. Build this first → STOP, report, WAIT.
- **Pass 2** — synonym-learner (§4 + bucket I) — **GATED 100%**.
- **Pass 3** — deterministic ACCUMULATION replay (§15A) + false-reject regression (§15C) — **GATED 100%**.
- **Pass 4** — real-LLM eval (§13 fixtures + §15B real-corpus accumulation) — **MEASURED**, emits `eval_report.json` GO/NO-GO.
- Each pass is **completely specified here** (contracts + tests). Do not invent scope; do not build a later
  pass early. Anything in **§8 OUT OF SCOPE** (real ingestion): never build.
- **100% reliable AND minimal:** smallest code that covers EVERY requirement — no dead code, no premature
  abstraction, no bloat (see §9 engineering standards).

---

## 0a. HARD BOUNDARIES (non-negotiable — a context-free bot must obey these)

- **Write scope:** WRITE only inside `drivers_harness/`. **NEVER** edit `scripts/`, `.env`, `~/.bashrc`, or
  any config; **NEVER** run `git`/commits; **NEVER** connect to Neo4j / Redis / any network in Layer 1.
  (`.env` and `~/.bashrc` are billing/secret landmines per the repo's `CLAUDE.md`.)
- **Billing fail-closed (CRITICAL):** Layer 1 uses **NO LLM**. The real-LLM layer (Pass 4) is driven
  **IN-SESSION by the interactive Claude Code session** (entrypoint `cli` = **subscription**, $0) — the tester
  spawns an in-session subagent/workflow as the producer-LLM and feeds its emission to the harness. **NEVER**
  make a standalone programmatic call: `claude -p` and `claude_agent_sdk.query()` are entrypoint `sdk-cli` =
  a **METERED pool at full API rates** (≈14 runs/mo on Max, per `.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md`);
  an API key bills pay-as-you-go. **NEVER** `import anthropic`, set `ANTHROPIC_API_KEY`, call `claude -p`, or
  call the Agent SDK. If tempted to automate an LLM call → STOP + `# TODO`; the tester runs it in-session.
- **Non-interactive STOP:** you cannot ask questions live. If blocked/ambiguous, do not guess or scope-creep —
  write it into `README.md` "OPEN QUESTIONS" + a `# TODO(ask)` and halt that piece.

---

## ⚖️ LLM-vs-CODE BOUNDARY — architecture principle (owner, 2026-05-29; REVISIT on the triggers below)

Do NOT use deterministic code where an LLM is more accurate. **LLM = semantic judgment** (meaning · novelty ·
ambiguity); **CODE = mechanical consistency** (exact-match · format · slot ORDER · length · validators · the
deterministic fold — $0, reproducible, can't fragment the graph). *"LLM decides meaning, code guarantees consistency."* **Governing rule:** *"Producer LLM handles semantics first. Isolated judge handles borderline/global/irreversible cases. Code persists, gates, and replays decisions deterministically. Gate strength scales with blast radius × irreversibility."*
- **Correctly LLM-led (do NOT code-ify):** reuse-from-catalog · K23/K30/K47/K52 · R9 granularity · Pass-4 accuracy.
- **Correctly code:** canonicalize formatting · exact-match vocab folds · slot order · length · validators V1–V14.
- **🟡 3 watch-spots + REVISIT TRIGGER each:**
  1. **New-word SLOT placement** (`resolve_unknown_slots` rejects an ambiguous novel token, `blackwell_revenue`→`slot_ambiguous`, Option-A). **REVISIT IF** Pass-4 shows false-rejects of legit new drivers → producer **DECLARES the slot in `propose_new`**; code = backstop, not judge.
  2. **Synonym DISCOVERY** (`uptake≈demand`) — equivalence comes from an LLM signal (caller supplies `to_token`); code = the N=2 gate + fold ONLY. **REVISIT IF** a candidate is code-guessed.
  3. **Banned-word completeness** (§F.7) — the LLM (taught R7) is the real defense; the list is a backstop. **REVISIT IF** Pass-4 shows banned words leaking.

**Recommended flow** (refined 2026-05-29): LLM emits → code dry-run validates → a same-learner **SELF-CORRECT loop (<=3 tries, stop-on-no-progress; orchestrator write-gate authoritative)** (§J Lever #3) → code re-validates → optional isolated LLM judge for semantic uncertainty → code writes/folds deterministically. **6 LLM-judgment uses:** informed-retry · semantic-reuse · synonym-discovery · new-token slot-declaration · evidence-SUPPORT · scope/granularity. (Keep code for identity/gates/graph-safety — the compiler half.)
Canonical: memory `feedback_llm_vs_code_boundary.md` (full refined list). Mirrored in `DriverOntology_Implementation.md` + `TESTER_HANDOFF.md`.

---

## 1. Source of truth for the RULES (read these; do NOT invent rules) — with the bloat-fence

> **PATH NOTE:** this doc lives in `.claude/plans/Drivers/Harness/`. All bare file refs below and throughout
> (e.g. `DriverOntology.md`, `_workflow/req_canonical.md`, `DoubtsInHTML.md`) are in the **parent** folder
> `.claude/plans/Drivers/` — resolve them as `../DriverOntology.md`, `../_workflow/req_canonical.md`, etc. (The
> harness CODE you build still goes in the repo-root `drivers_harness/` per §3 — unaffected by this move.)

1. **`_workflow/req_canonical.md` — SOURCE #1 + TEST SEED.** 27 reqs (A1–A27), the rule contract
   (B-F/B-N/B-R/B-M), and the **60 deduped risks K1–K60** (= the COMPLETE dedup of `DriverNameRisks.md`'s
   ~149 raw entries), each tagged `CREATION`/`INGESTION`/`HANDOFF`. Test the **CREATION-scoped** items only.
2. `DriverOntology.md` — rules **R1–R11**.
3. `DriverOntology_Implementation.md` — **UPDATED 2026-05-29.** Read **§C, §D, §D.1, §E, §F.1–§F.9 = RULES ONLY.**
   - ⛔ **IGNORE §F.10, §J, §K + anything `Neo4j`/`Cypher`/`MERGE`/`EquivalenceToken`/`VocabToken`/
     `supersession`/`*_visible_at`/audit-tables.** That is INGESTION, deliberately cut. **The authoritative
     CREATION-vs-INGESTION split is `_workflow/scope_split.md` — build ONLY what it tags CREATION.**
   - `§C canonicalize()` includes step **4.5** (`freeze_known_atoms` — v11-1 idempotency fix) + **8.5**
     (`rejoin_compound_metrics`) + **9.5** (`resolve_unknown_slots`) + a **slot-collision reject** in step 10.
     **`§D.1` defines the slot functions** — that code is the contract.
4. `DriverProcess.html` — plain-English walkthrough (§B, §C2.2 trace, §C4.3 seed, §C5.1 catalog render, §F7).
   Predates the §D.1 edit — on any conflict, the spec file wins; the spec file wins over THIS prompt's prose.
5. `_workflow/scope_split.md` — the verified CREATION-vs-INGESTION classification (the fence authority).
6. `_workflow/BEST_WAY_driver_creation.md` §3 — the verified MINIMAL component list (the lean-core check).
7. `ConceptualRequirements.md` — the upstream "what we need" (A-items); test the CREATION-binding ones (§6).
8. `DoubtsInHTML.md` — the owner's doubts; turn each testable one into a case + cite its doubt # (§6).

Ambiguous rule → best first-cut + `# TODO(harden-in-test)` + report it. **Never guess silently.**

---

## 2. THE PRODUCTION SEQUENCE this harness mirrors (build + test in THIS order)

Production runs these steps in order for every event. The harness reproduces **S1–S6 exactly** and stops
before the ingestion write (S7 = out of scope). **Each step is one component; the integration test runs them
in this same sequence** (point 6).

```
 S1  render_catalog(registry, vocab)     → catalog block (names/aliases/allowed_states)   [creation READ-path]
 S2  llm_emit(evidence, catalog)         → learner_result (tags); S2.5 adapter → emission JSON [LLM · Layer 2 only]
 S3  validate_emission_shape(emission)   → ok | shape errors                               [orchestrator pre-check]
 S4  per item: reuse_or_propose (B1–B10) → REUSE(name) | PROPOSE_NEW(canon) | REJECT(reason) [the cleaner]
 S5  per item/proposal: validators V1–V14→ ok | reject reason
 S6  decide(...)                         → "would-write" decision dict                      [decision; NO DB write]
 ─────────────────────────────────────────────────────────────────────────────────────────
 S7  writer MERGE → Neo4j                ⛔ INGESTION — OUT OF SCOPE (reuse the guidance writer in prod)
```

- **Layer 1 (deterministic, NO LLM):** exercises **S1, S3, S4, S5, S6** with hand-crafted emissions. Gated 100%.
- **Layer 2 (real LLM):** exercises the **full S1→S6 chain in order** on real evidence. Measured (not gated).

**Terminology (one mapping, used consistently):** the **build axis** is the **Pass** (1 core · 2 synonym-learner ·
3 deterministic accumulation + false-reject · 4 real-LLM eval). The **grading axis** is the **Layer**: *Layer 1 =
the deterministic, gated-100% passes (Passes 1–3)*; *Layer 2 = the measured real-LLM pass (Pass 4)*. So "Layer 2"
≡ "Pass 4" — same thing.

---

## 3. Folder layout (modules map 1:1 to the S-steps so the core copy-pastes later)

```
drivers_harness/
  driver_ids.py     # S4: slug, canonicalize, freeze_known_atoms, classify_token, resolve_unknown_slots,
                    #     order_by_slot, effective_slot_count, rejoin_compound_metrics   (per §C + §D.1)
  vocab_seed.py     # SLOT_VOCAB_SEEDS (§F.1–F.9) + CANONICAL_BASE_LABELS + COLD_START_SEED_DRIVERS
                    #     + build_vocab_snapshot() -> VocabSnapshot
  validators.py     # S5: V1–V14   (V15 = registry-global dedup = INGESTION; covered by B8 sorted-token reuse)
  registry_fake.py  # the ONLY stub — in-memory registry; production swaps it for the Neo4j-backed registry
  render_catalog.py # S1: registry -> LLM-readable catalog block  (mirrors prod bundle renderer; reads registry)
  reuse.py          # S4: the B1–B10 reuse/propose ladder over the registry
  run_one.py        # S3+S6: validate emission shape -> per item B1–B10 + V1–V14 -> decision dict ; NO db write
  run_sequence.py   # the S1→S6 chain (render -> [emit] -> run_one); Layer-2 integration entrypoint
  synonym_fold.py   # ⛔ RESERVED NAME — Pass 2. DO NOT CREATE in Pass 1.
  llm_emit.py       # ⛔ RESERVED NAME — Pass 4 (S2). DO NOT CREATE in Pass 1. Full spec §13.
  tests/
    test_canonicalize.py       # S4 unit
    test_validators.py         # S5 unit
    test_reuse.py              # S4 ladder
    test_render_catalog.py     # S1 unit
    test_edge_cases.py         # the adversarial/boundary set (§6) — the toughest cases
    test_idempotency.py        # bucket K
    test_sequence.py           # S1→S6 in production order (Layer-1: hand-crafted emission, no LLM)
    test_synonym_fold.py       # ⛔ RESERVED — Pass 2. DO NOT CREATE in Pass 1.
    test_llm_layer2.py         # ⛔ RESERVED — Pass 4. DO NOT CREATE in Pass 1.
    fixtures/
      fake_registry.json       # ~10 seed drivers incl. iphone_china_sales, oil_price, gross_margin, fda_approval
      evidence_samples.json    # ⛔ Pass 4 fixture — DO NOT CREATE in Pass 1 (spec in §13)
  README.md         # coverage proof: every test -> the K/A/doubt it proves
```

Run `pytest` from the harness folder (venv in §12). No network in Layer 1.

---

## 4. Module contracts (exact)

### `driver_ids.py`  (S4)
- `slug(text) -> str` — lowercase, non-alnum runs → `_`, strip edge `_`. **Re-implement in-harness** (don't
  import production); match `guidance_ids.slug` at `.claude/skills/earnings-orchestrator/scripts/guidance_ids.py:21`.
- `canonicalize(candidate, vocab) -> str | Rejection` — **PURE** (no I/O, network, clock, randomness). Implement
  the **§C steps EXACTLY**, incl. **step 3.5** `freeze_known_atoms` (freeze EVERY known multi-token atom =
  `vocab.frozen_atoms` = shortcuts ∪ compound_metrics ∪ slot_vocabs ∪ banned — **BEFORE the stopword-strip (v11-3)
  AND step-5 normalize**; steps 4–5 SKIP frozen atoms. **v11-2/v11-3 fix** → makes `us_gaap_revenue` REJECT,
  `vision_pro_sales` ACCEPT, and `cost_of_revenue`/`cost_of_goods_sold` ACCEPT (interior-stopword compounds survive);
  do NOT ship the old v11-1 shortcuts-only / freeze-after-stopword scope), **8.5** compound reassembly, **9.5**
  `resolve_unknown_slots`, step-10 slot-collision reject. **DETERMINISM:** sort explicitly; never rely on
  `set`/`dict` order. Shape gate fires on **direct** calls; in the pipeline B2 `slug()` normalizes first (see §6
  bucket A split).
- `freeze_known_atoms` / `classify_token` / `resolve_unknown_slots` / `order_by_slot` / `effective_slot_count` /
  `rejoin_compound_metrics` — **implement EXACTLY as §D.1 defines.** Don't paraphrase. Mark the new-token gate
  `# TODO(harden-in-test)`.
  - ⚠️ **CON-2 (`# TODO`):** the new-token gate's "known-token" range must include **§F.6 `COMPOUND_METRICS`**
    (else `gross_margin` is wrongly treated as a NEW token). Best first-cut: known = **§F.1 slot vocabs +
    §F.6 `COMPOUND_METRICS`** — **NOT** `CANONICAL_BASE_LABELS` (those are capitalized base-label values for
    V5, e.g. `Sales`, not lowercase name tokens).

### `vocab_seed.py`
- `SLOT_VOCAB_SEEDS` — the §F.1–§F.9 banks (slot vocabs + SYNONYM/PLURAL/ACRONYM maps + SHORTCUTS + BANNED +
  STOPWORDS + STATES + COMPOUND_METRICS + ALLOWED_VERBAL_FORMS). **`china`/`us`/`fed`/`opec` live HERE as slot
  tokens — they are NOT driver names.**
  - **SHORTCUTS_VOCAB seed completeness:** the seed MUST include every shortcut the tests reference —
    `oil_price`, `oil_supply`, `fed_rate`, `yield_curve`, `fda_approval`, `opec_supply`, **`forward_guidance`**
    (doubt #11 / F13). A referenced-but-unseeded shortcut has no defined expected output → the test is broken.
- **`BANNED_TICKERS` (offline ban-seed — REQUIRED for bucket B):** §F.7 defines identity-tickers as the
  *lower-cased `Company.ticker` from the Neo4j registry* (DB-sourced). The harness is OFFLINE, so it cannot know
  `aapl` is a ticker — provide a **static representative seed** `{aapl, nvda, tsla, msft, googl, amzn, meta, …}`
  so `aapl_iphone_sales → REJECT ticker` works. (Company + person names are already static §F.7 examples — only
  tickers are DB-sourced.) This is a **prod seam**: prod swaps the seed for the Neo4j Company registry (see §10).
- `CANONICAL_BASE_LABELS` — §F.6 holds BOTH `COMPOUND_METRICS` and `CANONICAL_BASE_LABELS`; expose the latter
  so **V5** can run.
- `COLD_START_SEED_DRIVERS` — the §C4.3 Tier-1 anchors that are **TIMELESS, VALID DRIVER NAMES only** (`oil_price`,
  `fed_rate`, `yield_curve`, `gross_margin`, `revenue`, `sales`, `eps`, …). **Do NOT put bare `china`/`fed` here**
  (they'd reject `no_metric`), and **do NOT put modern/era-bound drivers** (`iphone_china_sales`, `gpu_…`) here —
  per the PIT policy modern drivers are NOT cold-start seeded, and this constant **copies to prod unchanged (§10)**,
  so a leak here is a real production PIT bug. Static, always-visible (no PIT in the harness).
  - ⚠️ **SPLIT — two DISTINCT artifacts (do NOT conflate them into "one source"):**
    - `COLD_START_SEED_DRIVERS` = the timeless anchors above → **PROD-CORE, copies unchanged.**
    - `fixtures/fake_registry.json` = the **scenario registry for the reuse/accumulation tests** = the cold-start
      anchors **PLUS** modern scenario drivers (`iphone_china_sales` → {…, segment:"iPhone China", base_label:"Sales"},
      etc.) → **TEST-SCAFFOLD, never copies to prod.** The reuse-ladder / §15 tests load THIS, not the cold-start seed.
  - **Driver-row schema** (both artifacts) = `{name, aliases[], allowed_states[], segment, definition, base_label?,
    is_shortcut?}` — **include `definition`** (render_catalog renders it, §A); every `fake_registry.json` row MUST
    carry a one-sentence `definition`. ~10–12 rows (e.g. `oil_price` → {aliases:[],
    allowed_states:[accelerated,decelerated,stable,declined], segment:"Total", definition:"…", is_shortcut:true}).
    **Aliases are spelling/ORDER variants ONLY** — an alias MUST canonicalize TO the parent (V1), e.g.
    `china_iphone_sales`→`iphone_china_sales`. A SYNONYM (a *different word*, e.g. `crude_price`/`brent_price`
    for `oil_price`) is **NOT** an alias (it rejects `slot_ambiguous`); synonyms are the **Pass-2 synonym-learner's**
    job, never seed aliases. *(Corrected 2026-05-29 — the earlier `crude_price/brent_price` alias example was wrong.)*
  - **Bare-metric resolution (R3 vs §D):** `DriverOntology.md` R3 says a single-token name needs a shortcut or
    discriminator, but Implementation `§D` BNF (`:258`) allows `name ::= <metric>`. **The harness follows §D:**
    a bare valid metric (`revenue`/`sales`/`eps`) is an ACCEPTED canonical driver (bucket E). Its over-genericity
    is R9 *judgment*, NOT a canonicalize reject (see K19, §6).
- `build_vocab_snapshot() -> VocabSnapshot` — assemble the frozen snapshot from the seeds (mirrors prod
  `load_vocab_snapshot`, minus the Neo4j PIT read).

### `render_catalog.py`  (S1)
- `render_catalog(registry, vocab) -> str` — turn the registry's drivers **+ a VOCAB EXCERPT** into the
  **LLM-readable catalog block** the producer sees (per `DriverProcess.html §C1.1`): the driver rows
  (name · aliases · allowed_states · segment · **`definition`**) **and** a short vocab excerpt (THEMES/OBJECTS/GEOGRAPHIES/METRICS +
  SHORTCUTS) so the LLM has slot/shortcut hints. **Include `definition`** — it is in the per-Driver set the LLM
  sees per `DriverOntology_Implementation.md §A`; omitting it makes the catalog less production-faithful and
  understates reuse (the LLM has less to match on). Reads the registry (the seam) + the `vocab` snapshot; pure
  otherwise. In prod the registry read is PIT-filtered Neo4j — that swap is the seam. *(Signature matches §2.)*

### `validators.py`  (S5)
- **`V1`–`V14`** from §E, each `(ok, reason)`. **Do NOT build V15** (registry-global dedup = INGESTION; its
  concern is prevented by B8 sorted-token reuse).
- **`V_no_consecutive_underscores` OPTIONAL** (the §D shape regex already rejects `__`).
- ✅ **F5/F9 RESOLVED (2026-05-29 spec fix):** `restricted`/`accumulated` were REMOVED from §F.9
  ALLOWED_VERBAL_FORMS (they're §F.5 STATES → belong in `driver_state`, banned from names by step 7). No
  F5/F9 contradiction remains — no TODO here.

### `registry_fake.py`  ← the only stub
- In-memory driver dicts `{name, aliases[], allowed_states[], segment, definition, base_label?, is_shortcut?}`. Interface
  (prod reimplements with SAME names): `lookup_exact_name`, `lookup_by_alias`, `all_drivers`,
  `sorted_token_match`, `add_driver`. Load from `fixtures/fake_registry.json`.

### `reuse.py`  (S4)
- The **B1–B10 ladder**: B1 extract → B2 slugify → B3 exact name → B4 exact alias → B5 canonicalize → B6
  canonical name → B7 canonical alias → B8 sorted-token reuse (all-known-tokens gate) → B9 grammar+gate+
  validators → B10 new-driver gate (R11). Returns `REUSE` | `PROPOSE_NEW` | `REJECT(reason)`.
- **Auto-alias (per `DriverProcess.html §D2`):** when a new driver is accepted, or a reuse happens via canonical
  fold (B6/B7), store the ORIGINAL raw proposed string as an alias **IFF** it `canonicalize`s to the accepted
  name AND passes V1 (`alias→parent`). The next emission of that raw form then hits B4 (fast path). Test:
  propose `china_iphone_sales` (new) → accepted as `iphone_china_sales`, `china_iphone_sales` auto-added to aliases.

### `run_one.py`  (S3 + S6)
- `run_one(emission_json, registry, vocab) -> decision` — **S3** validate emission shape, then per item run
  **B1–B10 + V1–V14**, then **S6** return the `decision` shape in §5 (incl. the per-item records
  `{raw_name, canonical_name, status, reason, proposal_payload, aliases_added, new_slot_tokens}` that
  `apply_decision` (§15.0) needs). **No DB write.**
- **EMISSION-LEVEL pass (run ONCE over the whole emission, NOT inside the per-item loop — do NOT omit):**
  **V12** (no two `propose_new` share a name) · **V13** (`proposal_without_use` — every `propose_new` entry MUST be
  referenced by ≥1 item; an orphan proposal REJECTS, never passes silently) · **K53 self-consistency** (two
  items/proposals that canonicalize to the SAME name → flag/collapse — never silently emit two names for one driver).

### `run_sequence.py`  (S1→S6, production-order entrypoint)  ·  **TEST-SCAFFOLD** (prod = the orchestrator)
- `run_sequence(evidence_packet, registry, vocab, *, emission_json=None, emit_fn=None, context=None) -> decision`:
  - **S1** `catalog = render_catalog(registry, vocab)`
  - **S2** if `emit_fn`: `learner_result = emit_fn(evidence_packet, catalog)` (the in-session producer)
  - **S2.5** if a `learner_result` exists: `emission_json = learner_to_writer_input(learner_result, context)`
    (`context` is REQUIRED on this path — see §5 `RunContext`); else use the supplied `emission_json` directly
  - **S3–S6** `run_one(emission_json, registry, vocab)`
  Deterministic passes feed a hand-crafted `emission_json` (no LLM, no `context`). The real-LLM pass passes
  `emit_fn` (returns `learner_result`) + a `context`. **Pass 1: do NOT `import llm_emit`** — `emit_fn` arrives
  only as a parameter. Call order == production.

### `synonym_fold.py`  *(⛔ PASS 2 — DO NOT CREATE in Pass 1)*  — fully specified
- IGNORE the spec's §F.10 EquivalenceToken design. In-memory **per-candidate** `(kind, from_token, to_token) -> {observation_event_keys:set, status}` — competing candidate `to_token`s MAY coexist, each with its OWN count. Promote at `len(observation_event_keys) >= 2` (N=2 = the **eligibility** gate); count an observation only if `from_token` appears in that event's evidence; **synonyms only** (plurals/acronyms stay static §F.3/§F.4). **Conflict semantics (locked 2026-05-29 — NOT first-wins):** a 2nd, different `to_token` is NOT rejected — it coexists as a competing candidate. On a promotion attempt with competing candidates → **FREEZE** promotion + call the **injectable judge seam** `judge_fn(packet) -> verdict` (interface defined in §13; stubbed with fixed verdicts in Pass 1-3 so they stay deterministic; real in Pass 4). The `packet` carries the N=2-cleared competing candidates `[{to_token, observation_count, sample_evidence}]`; the `verdict.decision ∈ {promote (one to_token), no_global_rule, defer}`. **One PROMOTED `to_token` per `(kind, from_token)`** invariant; the judge may only approve a candidate that cleared N=2 (never a one-off because it "sounds better"). Keep the v11-4 evidence-gate-BEFORE-record (no poison). Promoted synonyms feed `build_vocab_snapshot`'s synonym map on the next run. **No** two-phase Cypher / race guards / PIT / audit (§8).

### `llm_emit.py`  *(⛔ PASS 4 / S2 — DO NOT CREATE in Pass 1)*  — fully specified in §13.

---

## 5. Contracts (shapes)

```
driver tag:         {driver_name, driver_state, direction("long"|"short"), evidence:[ "SRC:..." ]}
propose_new entry:  {name, label, base_label?, segment, definition, allowed_states:[...], aliases:[...], is_shortcut?}
learner_result:     { primary_driver: tag | null, contributing_factors:[tag...](may be empty), propose_new_drivers:[...] }
                    #   LEARNER's natural output (tags have NO ticker). primary_driver=null + [] = the no-driver case (F5).
RunContext:         { ticker, source_id, source_type, pit_cutoff, run_id, result_path, source_catalog:[ "SRC:..." ] }
                    #   the ORCHESTRATOR-STAMPED envelope (NOT LLM-authored); the adapter stamps these onto each item.
item (writer):      { ticker, driver_name, driver_state, direction("long"|"short"), exposure_role?, evidence:[ "SRC:..." ] }
                    #   exposure_role? = news-only PASSTHROUGH (E16); harness NEVER computes/validates it
                    #   (ingestion sets it on the FOR_COMPANY edge, §14) — carried only so the E16 handoff is shape-complete.
emission JSON:      { source_id, source_type ∈ {learner_result,news,fiscal_kpi}, pit_cutoff, run_id,
                      result_path, source_catalog:[ "SRC:..." ], items:[item...], propose_new_drivers:[...] }   # WRITER input — production-COMPLETE per E16
decision (run_one): { items:[ { raw_name, canonical_name|null, status ∈ {REUSE,PROPOSE_NEW,REJECT}, reason|null,
                                proposal_payload|null, aliases_added:[...], new_slot_tokens:[{slot,token}...] } ],
                      accepted:[...], rejected:[{name,reason}], proposed:[...], summary:{accepted_count, rejected_count} }
                    #   the per-item records are what apply_decision() (§15.0) needs to mutate the registry/vocab.
```

**Learner→writer adapter (production-faithful, doubt #43):** the learner LLM emits `learner_result`
(`primary_driver` + `contributing_factors[]`), **NOT** `items[]`. The adapter
`learner_to_writer_input(learner_result, context: RunContext) -> emission JSON` stamps the orchestrator-owned
envelope (ticker / source_id / pit_cutoff / run_id / result_path / source_catalog) onto each tag → `items[]` —
mirroring prod (learner emits → orchestrator adapts → writer). `learner_result` alone CANNOT synthesize that
envelope, so the **`context` arg is required**. Pass-4 `emit_fn` returns `learner_result`; `run_sequence` calls
the adapter with `context` (S2.5); the result feeds `run_one`. Deterministic passes may feed `emission JSON`
directly. Add ONE adapter unit test.
**PIN TO REALITY (standalone driver-emit prompt — live learner UNTOUCHED):** the Pass-4 producer prompt is a
**standalone driver-emission prompt/skill** (= `build_emit_prompt`, §13), **NOT** a clone or an edit of the live
`earnings-learner/SKILL.md`. So `learner_result` is pinned to *this* prompt's schema —
`{driver_name, driver_state, direction, evidence}` (+ `propose_new_drivers[]`); there is **no `{summary,category}`**,
and `category` is **dropped** (it collides with the no-category rule, §F.7). This **removes the old production
precondition**: NO live-`SKILL.md` edit is needed to run Pass 4. Integration is a **later, owner-authorised step** —
transplant the proven driver-emit block into the live `earnings-learner` (or point the orchestrator at the new
skill), then run a **small Pass-4-style smoke on the REAL integrated learner** (the integrated learner carries extra
lesson/attribution context, so **duplicate-green ≠ integrated-green**). The harness must **never edit the live skill**.

**`SRC:*` evidence convention** (per `DriverProcess.html`): `SRC:REPORT:<accession>#<section>` (8-K/10-K/10-Q) ·
`SRC:TR:<id>` (transcript) · `SRC:NEWS:<id>` · `SRC:FISCAL:<row>`. Every `evidence[]` entry MUST use one of these
**and** resolve against the emission's `source_catalog` (V10). The **`SRC:TR:` prefix is how a transcript-sourced
tag is marked separately** from an 8-K tag (doubt A15/TA2) — make `source_catalog` carry both `SRC:REPORT:` and
`SRC:TR:` IDs so this is testable.

---

## 6. Test plan — `req_canonical.md` IS the authoritative coverage list (the toughest cases included)

**Completeness mandate — Pass 1 must contain, with the source ID cited in each docstring:**
1. **One deterministic test per mechanically-checkable CREATION-scoped `K1`–`K60`** (= every risk in
   `DriverNameRisks.md`, deduped). The 4 LLM-judgment K's (**K23, K30, K47, K52**) get a **README deferral
   entry**, NOT a fake deterministic test — they're tested in Layer-2 as *"contained: reject-don't-guess."*
   **DO NOT MISS (the Pass-1 corrective set, folded in 2026-05-29 — a green suite WITHOUT these is FALSELY green):**
   the **multi-token banned** cases each REJECT `banned_token` — `us_gaap` (K15 xbrl) · `tim_cook`/`elon_musk`
   (K12 person) · `benzinga` (K14 provider) · `selloff` (K24 effect) · `collapse`/`surge` (K26 motion_change);
   the **multi-token OBJECT** cases ACCEPT — `vision_pro_sales` / `cloud_service_revenue`; **K17** stopword-strip
   (`empty_after_stopword_strip` + interior-stopword fold); **K53** same-canonical collision flagged. (All of these
   only pass with the v11-2 freeze + the emission-level V13/K53 pass above.)
   **Round-2/3 corrective set (folded in 2026-05-29):** **#1** the SAME atom-aware split (a shared
   `split_respecting_atoms(name, frozen_atoms)` helper) MUST be used **everywhere a name is re-split for a
   banned/known/slot check — NOT only canonicalize**: §E **V4 (both the name AND the `slug(segment)` side)**,
   **V14**, reuse **`_new_slot_tokens`** AND the reuse **B8 + B9 banned re-check** (`reuse.py`). NEVER a raw
   `name.split('_')` in those. PRODUCTION-PATH tests required (not just `canonicalize`): `reuse_or_propose("short_interest")`
   → PROPOSE_NEW (not `banned_token`); `V4("Vision Pro China","vision_pro_china_sales")` → PASS; `V4("Total",…)` → reject.
   (Symmetric label-vs-name compares + the freeze-internal splits stay raw — only one-sided banned/known/slot checks
   need the helper.) **#2** interior-stopword compounds ACCEPT
   (`cost_of_revenue`/`cost_of_goods_sold`, via freeze-before-stopword v11-3); **#3** bare direction/size words REJECT
   (`gpu_short_us_revenue`→`direction`, `gpu_large_us_revenue`→`magnitude_word`) WHILE seeded real compounds ACCEPT
   (`short_interest`/`long_term_debt`/`short_term_debt`, §F.6) — *"strict ban on loose words, explicit allow for real terms."*
2. **One test per CREATION-binding `A`-item** from `ConceptualRequirements.md` where mechanically checkable —
   e.g. **A2** (≥2 causal variables → ≥2 separate tags, never bundled), **A11/A20** (reuse-before-create / no
   driver without price-cause), **A14/A15** (learner emits primary + contributing; transcript-sourced tags
   tagged separately), **A22/A24** (determinism; granularity tension resolved). Skip deferred A's (news/
   fiscal/trading) — they are out of scope.
3. **The field contract `B-F1`–`B-F10`**, the **new-driver gate `B-R11a`–`B-R11g`**, and the worked examples
   **B-M4** (`opec_supply`+state) + **B-M5** (`china_iphone_sales`→reuse).
4. **Testable doubts from `DoubtsInHTML.md`** — at minimum **#13** (`china_japan_sales` two-geographies),
   **#11** (`iphone_guidance` vs `forward_guidance` specificity), **#44** (direction may be inferred, not
   verbatim — don't reject a tag solely for that). Cite the doubt # in the docstring.

**K19 (over-generic) — SPLIT, do NOT write a contradictory test:** the MECHANICAL part is the category-bare ban
(a standalone macro/sector/sentiment **bucket** word → REJECT via §F.7 `category`/banned). The "bare valid metric
is too generic" part is **R9 judgment** (Pass 4), NOT a canonicalize reject — so a bare valid metric (`revenue`)
**ACCEPTS** (bucket E). Do NOT write a "bare `revenue` → REJECT over-generic" test (it would contradict bucket E).

**Buckets A–H below are ORIENTATION examples, not the full list — `req_canonical.md` is.** CORE (Layer 1,
gated 100%) = the deterministic K's + A-items + bucket K + the sequence test + the adversarial bucket.

**A. Shape / format (K1–K6) — split by entry point:**
- **A1 · DIRECT `canonicalize()`** → REJECT `invalid_slug_shape`: `IPhoneChinaSales` · `iphone__sales` ·
  `_iphone_sales`/`iphone_sales_` · `iphone-china-sales` · non-ASCII.
- **A2 · `run_one`/reuse slug-normalization** → B2 `slug()` normalizes rough input FIRST: `"iPhone China Sales"`
  → `iphone_china_sales` → **REUSE** (NOT a shape reject).

**B. Banned content (K7–K17)** → REJECT with the named token: `opec_supply_cut`→state ·
`guidance_lowered`→state (correct form = `forward_guidance` + state `lowered`) · `aapl_iphone_sales`→ticker
(needs the `BANNED_TICKERS` offline seed — §4 vocab_seed) · `apple_china_sales`→company · `q3_revenue`→period ·
`100bps_margin`→magnitude · `bullish_guidance`→sentiment · `8k_guidance`→source · `headwind`→metaphor ·
`outlook`/`momentum`→vague (both ARE in §F.7; do **not** use `synergy` — it is not banned).

**C. Word-order/plural/format fold (K32–K33)** → canonical `iphone_china_sales`: `china_iphone_sales` ·
`sales_iphone_china` · `iphone_china_sale` · `iPhone-China-Sales`. Plus `china_iphones_topline`→`iphone_china_revenue`.

**D. Synonym/acronym/compound maps (K34–K35, R6)** — deterministic folds use ONLY pairs that exist in the
§F.2/§F.3/§F.4 maps: `topline`→`revenue` · `gm`→`gross_margin` · `gross_profit`→`gross_margin` ·
`data_center`→`datacenter` · `fcf`→`free_cash_flow`. Plus `cloud_gross_margin` valid (gross_margin = ONE metric slot).
*(K34 note: `req_canonical` lists `iphone_demand` vs `iphone_sales` as a K34 example, but `demand`/`sales` are
SEPARATE metrics with NO synonym-map entry → that pairing is **K47 semantic reuse (Layer-2 / Pass 4)**, NOT a
deterministic K34 fold. Do NOT write a `demand→sales` canonicalize test.)*

**E. Slot rules (K6, K22, K27, K29, R3/R8)**: `china_japan_sales`→REJECT **`slot_collision`** (two geographies,
one slot — doubt #13) · `iphone_china`→REJECT `no_metric` · `ai_datacenter_hyperscaler_us_capex`→REJECT
`too_many_slots` (**5 DISTINCT** slots: theme+object+customer+geography+metric) · `oil_price`→shortcut
early-return · bare `revenue`→ACCEPT.
*(Ordering matters: slot-collision fires at step 10, BEFORE the length check at step 11 — so use a
**5-DISTINCT-slot** name to hit `too_many_slots` and a **repeated-slot** name to hit `slot_collision`.)*

**F. Reuse ladder (registry has `iphone_china_sales`, `oil_price`, `gross_margin`) — K50–K51**: exact (B3) ·
alias (B4) · canonical (B6) · alias-of-canonical (B7) · sorted-token (B8) · genuinely new → PROPOSE_NEW.
*(K52 scope-fit is LLM-judgment → Layer-2.)*

**G. New-driver gate (R11/B-R11a–g, K58)**: a NEW token with evidence is acceptable **only when its slot is
positionally unambiguous** — `gpu_blackwell_us_revenue` (Blackwell pinned between `gpu`/`us`) with "Blackwell" in
evidence → ACCEPT · a **lone** new token before the metric (`blackwell_revenue`) → **REJECT `slot_ambiguous`**
(§D.1 fails closed — 5 free slots, never guess; the proposer must add a discriminator) · token NOT in evidence →
REJECT (hallucination) · all-unknown → REJECT `slot_anchor_unavailable` · one-off → REJECT (K18).
*(Spec §D.1 governs; the earlier `blackwell_revenue → ACCEPT` example was brief-prose error, corrected 2026-05-29
per owner decision "Option A — keep §D.1 fail-closed.")*

**H. Validators (K38–K49, K55–K57) — ALL of V1–V14, none skipped**: V1 alias→parent · V2 alias bridges · V3
label≠name · V4 segment · V5 base_label∉CANONICAL_BASE_LABELS · V6 mixed states · **V7 bad_definition (empty /
>1 sentence / token-only restatement of name)** · V8 state∉allowed · V9 direction enum · V10 empty/hallucinated
SRC · V11 unresolved name · **V12 duplicate_proposal (two `propose_new` with same name)** · **V13
proposal_without_use (a `propose_new` entry no tag references)** · **V14 new_token_gate_failed (unknown token
fails the §D new-token gate)**.

**K. Determinism (CORE)**: idempotency `canonicalize(canonicalize(x))==canonicalize(x)` over all inputs +
every `COLD_START_SEED_DRIVERS` name (valid names only). **The idempotency set MUST include the shortcut +
compound names** (`fda_approval`, `oil_price`, `oil_supply`, `yield_curve`, `forward_guidance`, `gross_margin`,
`cloud_gross_margin`) — each must round-trip to ITSELF.
- ✅ **RESOLVED in the spec (owner decision, 2026-05-29) — `§C step 4.5 freeze_known_atoms`.** These names MUST now
  round-trip and bucket K MUST be **green** — implement §C faithfully and it will be. Why it works: the seed
  deliberately has `margin` (SYNONYM key) ⊂ `gross_margin` (COMPOUND) and `approval` (PLURAL key) ⊂ `fda_approval`
  (SHORTCUT), so the maps can't be touched (deleting those keys would destroy real folds, and a blanket
  "disjointness" assertion is impossible). Instead, **`§C step 4.5` freezes any span that forms a known
  shortcut/compound into ONE atomic token BEFORE step-5 normalization**, and step 5 SKIPS frozen atoms — so
  `fda_approval`/`gross_margin`/`cloud_gross_margin` survive intact, while **bare `margin`/`approval` (not frozen)
  still fold.** Implement `freeze_known_atoms` + the step-4.5/step-5-skip wiring **exactly as `§C`/`§D.1` now define.**
- **If bucket K still reds on these → it's a BUILDER bug (step 4.5 missing/mis-implemented), NOT a spec/seed issue.**
  Fix the implementation to match §C. Do **NOT** edit §C, delete a seed fold, or force-green — that part of the
  surface-don't-fix rule still holds for everything else.
- The ONE assertion that IS safe to keep: the three normalize maps' KEY-sets are **pairwise disjoint** (they don't
  overlap *each other* — a separate, true property, unrelated to the shortcut/compound question above).

**ADVERSARIAL + BOUNDARY (CORE — the toughest, build these explicitly):**
- **Stacked violations:** one name that smuggles MULTIPLE bad things at once (`aapl_q3_iphone_china_sales_cut`
  → ticker+period+state) → REJECT with the first-fired reason; `weak_100bps_margin_decline` → REJECT.
- **Exact boundaries:** a name at **exactly 4 effective slots** → ACCEPT; **5** → REJECT `too_many_slots`;
  a compound-metric name where the compound makes it 4-not-5 (`ai_datacenter_us_gross_margin`) → ACCEPT.
- **Fold + dedup combos (exactly ONE expected result each — never assert "X or Y"):**
  `iphone_iphones_sales` → `iphone_sales` (plural `iphones`→`iphone`, then dedup) ·
  `iphone_iphones` → REJECT `no_metric` (dedup leaves `[iphone]`, no metric). Choose inputs whose §F.2/§F.3
  maps yield a single deterministic outcome.
- **Multi-variable (A2/K22):** an emission whose evidence names TWO causes → expect TWO separate tags, never
  one bundled name.

**SEQUENCE (CORE — point 6):** `test_sequence.py` runs **S1→S6 in production order** via `run_sequence` with a
hand-crafted emission (no LLM): render_catalog produces a block containing the seeded names → a hand emission
referencing one reuse + one propose-new → shape-validate → B1–B10 → V1–V14 → decision dict has the expected
accepted/proposed/rejected. Asserts the *order* and the hand-off shapes match production.

**I. Synonym-fold (⛔ PASS 2)**: seen 1× → candidate · 2× distinct events → promoted, folds on 3rd · evidence-
absent → not counted · conflicting `to_token` → **competing candidate (NOT first-wins)** → on a promotion attempt FREEZE + judge-seam resolves `{to_A, to_B, no-global-rule, defer}`; one PROMOTED `to_token` per `(kind, from_token)`.

**J. Real LLM (⛔ PASS 4 — full spec §13)**: full S1→S6 on real evidence; properties + pass-rate; `-m llm`; measured.

---

## 7. BILLING GUARDRAIL (CRITICAL — corrected)

Per `.claude/plans/ANTHROPIC_BILLING_SUBSCRIPTION_CRITICAL.md` (effective Jun 15 2026): `claude -p` and
`claude_agent_sdk.query()` are entrypoint **`sdk-cli` = a METERED pool at full API rates** (≈14 runs/mo on Max,
then pause/overage) — **NOT** the subscription. Only the **interactive** session (entrypoint `cli`) is
subscription. So:
- ✅ **The real-LLM layer is driven IN-SESSION** by the interactive Claude Code session (the tester): spawn an
  in-session **subagent / workflow** as the producer-LLM → it emits the driver tags → the harness consumes them
  via `run_sequence(emission_json=…)`. In-session subagents/workflows run on the subscription ($0).
- ✅ The harness therefore exposes only `run_sequence(…, emit_fn=…)`; in Pass 4 the **tester** supplies the
  emission (via `emit_fn` or by writing it into `evidence_samples.json` in-session). **The harness never makes
  the LLM call itself.** Gate Pass-4 tests with `pytest -m llm`.
- ❌ Do **NOT** build a standalone LLM caller: no `claude_agent_sdk.query()`, no `claude -p`, no
  `import anthropic`, no `ANTHROPIC_API_KEY` — all meter or bill API. If tempted → STOP + `# TODO`.
- Production parity: the production learner runs the same prompt via the orchestrator's **interactive TMUX
  transport (entrypoint `cli` = subscription)**, also NOT the metered SDK — so this design matches production.

---

## 8. OUT OF SCOPE (real ingestion — do NOT build; STOP+TODO if tempted)

- ❌ Neo4j/Cypher/any DB (S7). `registry_fake.py` is the only registry.
- ❌ `:EquivalenceToken` store, N=2 two-phase Cypher, race guards, conflict/collision audit tables.
- ❌ `:VocabToken` store, `vocab_visible_at`/`equivalence_visible_at` PIT-backdating.
- ❌ 5 audit tables — a plain in-memory rejection list suffices.
- ❌ **No writer-side auto-repair (no state-strip)** — `opec_supply_cut` REJECTS cleanly. (Auto-repair = deferred.)
- ❌ supersession, MERGE, graph edges, on-disk sidecars (return the dict).
- ❌ real PIT filtering — fake registry is always-visible.
- Deferred-but-MANDATORY ingestion item — the **reconciliation job**: merge two ALREADY-REGISTERED drivers when a late-learned equivalence or judge ruling proves them the same (relink DriverChanges + supersession; judge-confirmed; reversible/un-merge; PIT-honest effective date). Audited-not-silent until it ships.
- **TO SPECIFY at integration — embedding near-duplicate reuse trigger:** PIT-filtered top-K retrieval (registry_visible_at <= run.pit_cutoff), similarity threshold (tuned for RECALL), candidate-packet shape, judge input/output schema, persisted-verdict store. Cheaper deterministic floor: a token-overlap shortlist. Embedding is a TRIGGER ONLY — never decides equality, never auto-rejects.

These are the §1 IGNORE-fence sections (§F.10/§J/§K). Added later only when explicitly required.
**Nothing here is permanent:** every cut/deferral has an explicit **RESTORE TRIGGER** (an `eval_report.json`
symptom → the exact item to re-add) in `TESTER_HANDOFF.md §7B`. A cut goes back in **on evidence**, never
silently dropped.

---

## 9. Engineering standards (organized · minimal · efficient · isolated)

- **PROD-CORE vs TEST-SCAFFOLD partition (so prod-core copies in with ZERO changes — your constraint):**
  - **PROD-CORE — copies to production UNCHANGED, pure, imports nothing test-only:** `driver_ids.py`,
    `validators.py`, `vocab_seed.py` (banks + `build_vocab_snapshot`), `reuse.py`, `render_catalog.py`,
    `run_one.py`, `learner_to_writer_input()`.
  - **TEST-SCAFFOLD — stays in the harness, NEVER imported by prod-core:** `registry_fake.py`,
    `run_sequence.py`, `apply_decision()` + the cohort replay (§15), the eval corpus + report, the in-session
    LLM glue, the contract-test runner, all of `tests/`. (Production supplies these via Neo4j + the orchestrator.)
  - **Rule:** a PROD-CORE module that `import`s a TEST-SCAFFOLD module is a BUG — it breaks "copy in, no changes".
    Add one CI check: grep PROD-CORE files for imports of scaffold modules → must be empty.
- **Minimal:** stdlib only (no pandas/numpy unless justified in the report). Smallest code that covers every
  requirement; no dead code, no speculative abstraction, no feature not traced to a K/A/B/doubt or an S-step.
- **Pure + typed:** type hints on every public fn; `canonicalize` + the §D.1 fns are pure (no I/O). No hidden
  globals — pass `VocabSnapshot` + registry as arguments.
- **Organized:** one concern per module (§3), one assert-cluster per test, each fn ≤ the rule it implements.
- **Efficient:** exact-string/dict lookups (no fuzzy matching anywhere); compile regexes once.
- **Docstrings cite the source** (the K/A/B-rule/§-step) so the file is self-documenting + audit-traceable.

---

## 10. Production integration map (so it copies in cleanly once verified)

| Harness file | Production destination (provisional) | On integration |
|---|---|---|
| `driver_ids.py`, `validators.py`, `reuse.py`, `render_catalog.py`, `run_one.py` | `scripts/earnings/builders/` **or** `.claude/skills/earnings-orchestrator/scripts/` (guidance lives in the latter) | **copy unchanged** |
| `run_sequence.py` · `apply_decision()` · replay + eval harness | the orchestrator (sequencing) + the real writer (apply) | **TEST-SCAFFOLD — NOT copied** (prod = orchestrator + Neo4j writer); matches §9 |
| `vocab_seed.py` — static seeds + `COLD_START_SEED_DRIVERS` + `VocabSnapshot` dataclass | same | **copy unchanged** |
| `vocab_seed.build_vocab_snapshot()` — the loader | same | **EXTEND** — production wraps it to ALSO merge PIT-filtered Neo4j `VocabToken`/`EquivalenceToken` rows |
| `learner_to_writer_input()` adapter | same | **copy unchanged** (pure) |
| `registry_fake.py` | the real Neo4j-backed registry/writer (guidance clone) | **swap** — reimplement the SAME interface against Neo4j |
| `vocab_seed.BANNED_TICKERS` (static seed) | the Neo4j Company registry (`Company.ticker`) | **swap** — prod sources tickers from the DB (§F.7); harness uses the static seed |
| `llm_emit.py` prompt + parser | a **standalone driver-emit prompt** (NOT the live `earnings-learner` skill) | **transplant** the proven prompt INTO the live `earnings-learner` (owner-authorised) + run a post-integration smoke; production then runs it via the orchestrator's **interactive TMUX transport (entrypoint `cli` = subscription)** — NOT the metered SDK |

The whole point: **swaps = registry backend + ticker source + LLM transport; one extension = the vocab loader
(merges Neo4j rows); everything else is copy-paste.** Keep names identical so the diff is trivial.

---

## 11. Deliverable — Pass 1 (CORE) only

1. The folder builds cleanly under the repo venv. (Do NOT create the RESERVED Pass-2/4 files.)
2. **`pytest -q` green — INCLUDING bucket K:** the full completeness mandate (§6.1–§6.4) + bucket K + the
   ADVERSARIAL/BOUNDARY bucket + `test_sequence.py` (Layer 1, offline, NO LLM). Then **STOP and report.**
   - ✅ **The bucket-K shortcut/compound idempotency case is now FULLY GREEN-ABLE** — `fda_approval`, `gross_margin`,
     `cloud_gross_margin` round-trip because **`§C step 4.5 freeze_known_atoms`** (owner spec fix, 2026-05-29) freezes
     them before step-5 normalization. Implement `§C`/`§D.1` faithfully and bucket K passes. **If it reds, that's a
     builder bug in step 4.5 — fix the implementation to match §C** (still NEVER edit §C, delete a seed fold, or
     force-green; see §6 bucket K + `TESTER_HANDOFF.md §5`).
3. `README.md` coverage table: every test → the K/A/B/doubt it proves; plus a **deferral section** for
   K23/K30/K47/K52 (Layer-2).
4. A `# TODO(harden-in-test)` list (esp. new-token gate + CON-2 §F.6 range).

Report: file tree, pytest summary, TODO list. Do not cross §0a/§8 without a TODO + stop.

---

## 11B. Deliverable — Pass 2 (synonym-learner; build ONLY when authorized after Pass 1)

1. Build `synonym_fold.py` per the §4 contract + `test_synonym_fold.py` (bucket I). **Still offline / NO LLM**
   (Pass 2 is deterministic, gated 100%).
2. **Integration (the one wiring point):** a promoted synonym must feed `build_vocab_snapshot()`'s `synonym_map`
   on the **next** snapshot build, so `canonicalize` then folds it automatically. Test it: promote `uptake→demand`
   (2 distinct events, each with `uptake` in evidence) → rebuild snapshot → `canonicalize("datacenter_uptake")`
   now folds to the `…_demand` form.
3. **Pass criteria (all green):** 1 obs → stays a hidden candidate; 2 distinct events → promoted; an observation
   whose `from_token` is absent from that event's evidence is NOT counted **AND leaves NO record** (run the evidence
   gate BEFORE creating any record — v11-4; else a zero-evidence guess PINS a meaning and blocks a later real
   evidenced synonym: a meaning-conflict that shouldn't exist); a 2nd, different `to_token` for the
   same `(kind, from_token)` is NOT first-wins-rejected — it coexists as a competing candidate, and on a promotion attempt FREEZES promotion + the injectable judge seam (stubbed in Pass 1-3) resolves it to one of `{to_A, to_B, no-global-rule, defer}` (one PROMOTED `to_token` per key); plurals/acronyms are NOT learned (stay static §F.3/§F.4).
4. **Report** (same shape as Pass 1) → STOP; wait for Pass 3 authorization.

> **PASS-2 DESIGN ITEM (owner-approved 2026-05-29, zero-human-in-the-loop) — auto-learn NEW multi-token objects.**
> §C step 4.5 `freeze_known_atoms` protects multi-token atoms that are ALREADY seeded (v11-2). A *brand-new*
> multi-token OBJECT the system has never seen (e.g. a future two-word product) still splits → `slot_ambiguous`.
> To keep the owner's "no human adds words" requirement: when the producer LLM proposes a new driver it already
> sends a `propose_new` payload with `segment`/`label` — let it **DECLARE** the new multi-token token's slot, and
> the learner appends it to the slot vocab (the `:VocabToken` Pattern-A1 growth path, ingestion) so the NEXT
> snapshot's `frozen_atoms` includes it and it canonicalizes cleanly. Single-token new tokens already auto-learn
> this way; this extends it to multi-token. **Design + wire in Pass 2 / ingestion — NOT Pass 1.** Closes the
> "non-exhaustive vocab" fear (doubts #14/#38/#47/#49/#51) end-to-end with no manual maintenance.

---

## 12. Environment

`source venv/bin/activate` (pytest + `claude_agent_sdk` live there). Run `pytest -q` from `drivers_harness/`.
Register the `llm` marker so `pytest -m llm` works and Layer-2 stays out of the default run.

---

## 13. PASS 4 (part 1) — real-LLM single-event fixtures (FULLY DEFINED; runs WITH §15B; build only when authorized)

> Purpose: close the gap Layer-1 can't — *does a real LLM, reading real evidence, PRODUCE a good tag, and does
> the cleaner reliably fold whatever it produces?* Measured (LLM is non-deterministic + costs tokens), but
> **thorough** — this pass is REQUIRED, not optional; it's graded by pass-rate, not a hard green gate.

### `llm_emit.py` contract (S2) — **NO standalone API/SDK call** (the LLM runs IN-SESSION; see §7)
```
build_emit_prompt(evidence_packet, catalog_block) -> str        # the producer author-prompt
parse_emission(llm_text) -> learner_result (§5)                 # parse the model's reply (LEARNER shape)
   #   then learner_to_writer_input(learner_result, context) -> emission JSON  → feed run_one  (context = RunContext, §5)
   # evidence_packet = {evidence_text, source_catalog:[ "SRC:REPORT:…#MDA", "SRC:TR:…", … ]}
   # the LLM may ONLY cite SRC IDs present in source_catalog → V10 then meaningfully checks resolution.
   #   (Without a source_catalog the LLM hallucinates SRC:* and V10 either rejects everything or is untested.)
```
- **Prompt (`build_emit_prompt`):** R1–R11 author rules (from `DriverOntology.md`) + the `catalog_block` (from
  `render_catalog`) + `evidence_packet.evidence_text` + its `source_catalog` (the ONLY SRC IDs the LLM may cite);
  instruct: emit the **LEARNER shape** (`primary_driver` + `contributing_factors[]`) + `propose_new_drivers[]`,
  reuse-first, propose-new only if no match — **NOT `items[]`** (`parse_emission` → `learner_to_writer_input`
  produces `items[]`). **Each `propose_new_drivers[]` entry MUST carry ALL §5 fields, incl. a clean one-sentence
  `definition`** — **V7** rejects an empty / >1-sentence / name-restating definition, so a proposal that omits it
  reds at S5. **This prompt is the standalone driver-emit author-prompt** — later transplanted INTO the
  live learner (point 5 transplant), **NOT** an edit to the live skill while the harness runs.
- **The LLM call is made IN-SESSION by the tester** (interactive Claude Code = subscription, §7) — `llm_emit.py`
  must **NOT** call `claude_agent_sdk` / `claude -p` / any API. The tester wraps `build_emit_prompt` + `parse_emission`
  into an `emit_fn` (returns `learner_result`) driven by an in-session subagent, and calls
  `run_sequence(evidence_packet, registry, vocab, emit_fn=…, context=RunContext)` — `run_sequence` does S2.5
  (`learner_to_writer_input`) internally. `emit_fn` is the seam the tester injects the in-session producer through.
- **Isolated-judge seam (mirror of `emit_fn`):** the optional isolated Pattern B judge (the "optional isolated LLM judge" in the Recommended flow above; cheap cached model — gpt-4o-mini/haiku, temp 0, strict structured output, verdict cached/persisted = decide-once-replay-by-code) is itself an **INJECTABLE SEAM**. Passes 1-3 stub it with **fixed verdicts** so they stay deterministic and gated 100%. **HARNESS Pass 4 runs the judge IN-SESSION ($0) ONLY to (a) TEST its behavior and (b) COUNT its calls so it can PROJECT production cost** — it is NOT the real metered call there, it is the subscription session standing in for it to exercise + budget the seam (count budget ~80-120 isolated calls per 100 cold-start runs, decaying to ~12-30 mature). **In PRODUCTION the judge is an INDEPENDENT, METERED, cheap cached call** (gpt-4o-mini / haiku, temp 0, verdict cached) — **be honest: it is metered in prod** (a separate cheap-model API/billed call, not the in-session subscription), kept cost-trivial by the cheap model + caching + the low call volume above. (Do NOT claim the SAME call is both "$0 in-session" and "cheap model well under \$1" — those are two different runtimes: in-session-test = $0 measurement; production = a real metered cheap-model call.) The judge fires only on borderline/global/irreversible cases; canonicalize() and the V1-V14/fold/slot-order code stay deterministic regardless (the judge runs at vocab-GROWTH/write-time, its verdict persisted, and canonicalize stays deterministic GIVEN THE FROZEN VOCAB SNAPSHOT). The Pass-4 harness exercise of it runs IN-SESSION ($0) — NEVER `claude -p`/SDK.
- **Judge-seam INTERFACE (locked 2026-05-29) — `judge_fn(packet) -> verdict`:**
  - `packet = {kind: "synonym"|"plural"|"acronym", from_token: str, candidates: [{to_token: str, observation_count: int, sample_evidence: [str, ...]}, ...]}` — `candidates` are ONLY the **N=2-cleared** competitors (the eligibility gate is **code**, run BEFORE the judge — the judge never sees a sub-N=2 one-off).
  - `verdict = {decision: "promote"|"no_global_rule"|"defer", to_token: <a candidate's to_token>|null, reason: str}` — **promote** = fold `from_token → to_token` (exactly ONE promoted per `(kind, from_token)`); **no_global_rule** = token is context-dependent → no global synonym, handle via driver-level reuse only; **defer** = keep the `(kind, from_token)` FROZEN, re-judge when more evidence arrives.
  - Passes 1-3 inject a deterministic **fixed-verdict stub** (`judge_fn` is the injectable param); Pass 4 wires the real call. This structured form generalizes the `{to_A, to_B, no-global-rule, defer}` shorthand to ≥2 competing candidates.

### `fixtures/evidence_samples.json` — ≥12 snippets, each `{id, evidence_text, source_catalog:["SRC:…"], expected_property}`
(F1–F8 = core families; **F9–F12 = the 4 deferred LLM-judgment risks K23/K30/K47/K52** — §6 promised them here)
| id | evidence (paraphrase) | expected property after S1→S6 |
|---|---|---|
| F1 reuse | "iPhone unit sales in mainland China decelerated…" | REUSES `iphone_china_sales`; state∈allowed; dir `short`. |
| F2 propose | "Hyperscalers placed $42B in GPU orders, accelerating." | PROPOSE_NEW whose name canonicalizes to slot order (e.g. `gpu_hyperscaler_bookings`); no banned tokens. |
| F3 state-smuggle | "OPEC announced a 1M b/d supply cut." | final name `opec_supply` (NO `cut`); `cut`→driver_state. |
| F4 identity-strip | "Apple's Q3 revenue rose on services." | name has NO `apple`/`q3`; resolves to a `*_revenue` driver. |
| F5 no-driver | analyst opinion / pure sentiment, no company mechanism | **0 drivers** (or reject) — does NOT hallucinate. |
| F6 multi-variable | "China iPhone sales fell AND gross margin compressed." | **TWO** tags (`iphone_china_sales` + `gross_margin`), not bundled (A2/K22). |
| F7 synonym | "Topline came in light." | folds `topline`→`revenue`. |
| F8 one-off bait | "Q2 2026 keynote drove the stock." | REJECT/PROPOSE-clean — NOT a single-use name like `keynote_q2_2026`. |
| F9 mechanism-collision (K23) | "Oil **prices** jumped while OPEC **supply** was cut." | **TWO** drivers `oil_price` + `opec_supply` (OPEC-specific supply, per R5 / `DriverOntology.md:91`) — NOT merged, NOT `oil_supply`. |
| F10 wrong-discriminator (K30) | "Weakness driven by **hyperscaler** demand, not any one region." | name uses the **customer** slot (`hyperscaler_…`), NOT a geography. |
| F11 alias-undermatch (K47) | "iPhone **demand** in China softened." (registry has `iphone_china_sales`) | the LLM **semantically reuses** `iphone_china_sales` from the catalog — **NOT** a deterministic `demand→sales` fold (`demand` & `sales` are SEPARATE metrics, no such synonym exists). If it instead mints `iphone_china_demand`, that's the *contained* dup the Pass-2 synonym-learner would later fold. |
| F12 wrong-reuse / scope-fit (K52) | "China-specific iPhone weakness." (registry has BOTH `iphone_china_sales` AND `iphone_total_sales`) | REUSE the **China-scoped** `iphone_china_sales` — NOT `iphone_total_sales`. |
| F13 guidance granularity (doubt #11) | "Apple lowered guidance." (no product specified) | emits `forward_guidance` + state `lowered` — NOT `guidance_lowered` (state-in-name) and NOT `iphone_guidance` (no product in evidence). If evidence WERE product-specific ("lowered iPhone guidance") → `iphone_guidance` is acceptable. *(R9 granularity = judgment; `forward_guidance`'s exact §F form is a seed decision the builder confirms from the spec.)* |

### bucket J tests + the CORE real-LLM test
- **Per-fixture:** assert the property (not exact string) on the `run_sequence` output.
- **Consistency (the headline real-LLM test):** the **tester runs (in-session, subscription)** F1 (and F3)
  `N≥5` times AND across 2 in-session subagent models (e.g. haiku + sonnet); collect the varied raw
  `driver_name`s the LLM emits; assert **ALL fold to the SAME canonical driver** (reuse the same existing one /
  propose the same canonical form). This is "5 spellings → 1 name" proven with REAL LLM variance — the core
  guarantee. (No SDK/`-p` call — the emissions come from in-session subagents.)
- **Pass-rate:** report `passed/total`; **≥4/5 per-fixture** + **100% on the consistency test** are the health
  bars, but `-m llm` is MEASURED — never hard-fail the suite on token-flaky output. Always print raw vs cleaned
  for eyeballing.
- **Model note + the REAL readout (not just a lower bound):** the headline `eval_report.json` accuracy number MUST
  be produced with the **production-tier learner model** (the model the live learner will actually use) running the
  **§13 prompt** (which IS the production driver-emit prompt). A weaker model (e.g. `haiku`) is run too as a
  **robustness lower-bound / stress test** — but the GO/NO-GO readout is the production-tier run. (The ultimate
  check remains the later **integrated smoke on the REAL learner** per §5 — *duplicate-green ≠ integrated-green*.)

---

## 14. Doubt-coverage ledger — every doubt in `DoubtsInHTML.md`, tagged (nothing dropped silently)

Numbering follows the body of `DoubtsInHTML.md` (Things-to-add / questions **#1–#51**, gaps at 8/19/29/41,
plus the `Requirements`/`Issues`/`Agree`/`Resolved` blocks). Three tags:
- **TESTED-HERE** → a real Pass-1 test exists (already folded into §6; the builder MUST cover these).
- **RESOLVED-BY-DESIGN** → a settled decision/architecture answer — no test needed (do NOT build a test).
- **DEFERRED-TO-INGESTION** → out of scope for the harness (reused from the guidance writer); listed only so
  it is explicitly tracked, not silently dropped.

**A · TESTED-HERE** (each → a §6 test; cite the doubt # in the docstring):
| Doubt | Topic | Where tested |
|---|---|---|
| #5 | approve full `result.json` shape | §5 emission shape + S3 validate |
| #6 | sorted-token reuse, "no hardcoded examples" | B8 / bucket F |
| #10 | `allowed_states` not exhaustive / mis-categorized | V6+V8 / bucket H |
| #11 | `iphone_guidance` vs `forward_guidance` specificity | R9 granularity / §6.4 |
| #13 | `china_japan_sales` two geographies | bucket E |
| #14, #38, #47, #49, #51 | **the "non-exhaustive vocab" fear** (synonym/acronym/shortcut/compound/`oil_price`) | maps bucket D + new-token gate G + synonym-learner (Ph2) + **real-LLM consistency test (Ph3) proves it works without an NLP lib** |
| #15 | plural map scope | bucket D |
| #16 | aliases — flow/purpose | V1/V2 + reuse B4/B7 + auto-alias |
| #17 (field) | `segment` value correctness | V4 / bucket H |
| #18 | `base_label` purpose | V5 + CANONICAL_BASE_LABELS |
| #20, #21 | vocab-vs-registry + evidence-appears + ≥1 evidenced tag | new-token gate / bucket G |
| #22, #23 | segment↔name sub-dim; one state class | V4 / V6 / bucket H |
| #40 | where magnitudes go (banned in name → evidence) | bucket B |
| #44 | direction may be inferred, not verbatim | §6.4 |
| #45 | is the shape regex safe? | bucket A + idempotency bucket K |
| #46 | how the grammar works | buckets C/E |
| TA1(part), #12(reason) | ≥1 driver / multiple drivers; reject returns a named reason | A2 + bucket F6 multi-variable; decision dict reason |
| TA2(part) | transcript-sourced tags tagged separately | A15 |
| TA3 | exact sentence/quote in evidence | V10 evidence format |
| Issues#1(value) | `direction` ∈ {long,short} as a tag field | V9 |

**B · RESOLVED-BY-DESIGN** (settled — no test):
Req#1 (understand-each-unit-first = this staged harness) · Req#2 + Agree#1 (reuse guidance / shared
writer = §10) · Req#3 (minimal = §9) · TA4 (CLI not pod = Mode-1 architecture) · #9, #39, #42 (predictor is
**consumer-only**) · #43 (`primary_driver`+`contributing_factors` split) · #24 (rejections logged; in-loop
feedback = orchestrator, not creation) · #26 (`evhash16` dropped) · #31 (driver vs driver_change naming) ·
#48 (rejection reasons are short/named) · **#50 (LLM does NOT run canonicalize — Python does, post-hoc;
showcased by the Layer-1 vs Layer-2 split itself)**.

**C · DEFERRED-TO-INGESTION** (NOT built/tested here — reused from the guidance writer; tracked, not dropped):
#7/TA7 (`:DriverDriftAudit`) · #17(linking) + #33 (`MAPS_TO_CONCEPT`/`MAPS_TO_MEMBER`) · #25, #35, #36(PIT
part) (`pit_cutoff`/`registry_visible_at`/epoch-sentinel — note: the seed **contents** ARE tested in bucket K;
only the PIT visibility is deferred) · #27, #32 (`evidence_refs`/`CITES_EVIDENCE` edges) · #28, #30, #34
(`exposure_role` / direction-on-edge) · #37 (supersession) · TA1(part) (`primary_driver` bool on the edge) ·
Issues#1 + Resolved#1 (direction-on-edge placement + `FROM_SOURCE` / news multi-event linkage).

> **Builder:** act on **A** only. **B** and **C** require **no code** — if a B/C item seems to demand work,
> that's the §8 fence; STOP + `# TODO`. **Tester (Claude):** the **C** list is the checklist for the *second*
> harness (ingestion) later — keep it visible so the deferred doubts resurface at the right time.

---

## 15. Production-reality — accumulation replay + real-accuracy eval  *(TEST-SCAFFOLD only)*  ·  **§15A+§15C = PASS 3 (gated 100%) · §15B = PASS 4 part 2 (measured)**

> Single-event tests prove the gears. **This proves the engine survives a real run of events.** Production is
> NOT one event — it's hundreds in SEQUENCE, each accepted driver ACCUMULATING into the registry and getting
> REUSED by later events. The reuse/dedup guarantee and the real accuracy number **only exist across runs.**
> Everything here is **TEST-SCAFFOLD** (never imported by prod-core, §9).

### 15.0 — The missing piece: `apply_decision()` (the fake-writer "apply" step)
After `run_one` returns a would-write decision, **mutate the fake registry/vocab so the NEXT event sees it**
(in prod this is the Neo4j MERGE; here it's in-memory):
```
apply_decision(decision, registry_fake, vocab) -> (registry_fake', vocab')
  # reads decision.items[] (raw_name, canonical_name, status, proposal_payload, aliases_added, new_slot_tokens — §5):
  • status PROPOSE_NEW → registry_fake.add_driver(proposal_payload) + AUTO-ALIAS (raw_name, IFF it canonicalizes
                          to canonical_name) + add new_slot_tokens to the snapshot   (the VocabToken read-seam)
  • status REUSE       → no new driver; record the reuse (feeds the reuse-rate metric)
  • promoted synonym (Pass 2) → fold into the snapshot's synonym_map
```
Without `apply_decision`, run #2 can never reuse run #1's driver — the entire reuse story is untested.

### 15A — Layer-1 accumulation replay (DETERMINISTIC, GATED 100%)
A scripted ORDERED sequence of **~20–40 hand-crafted emissions** (multiple tickers · ≥2 quarters each · **both
learner AND news producers** (harness-generality — proves the shared writer is producer-agnostic; in production Phase-1 is learner-only per E30, news is Phase 2) · plus a **re-run** of an earlier event) with a KNOWN end-state. Loop:
`render_catalog(registry,vocab) → [scripted emission] → run_one → apply_decision → carry forward`. Assert the
**cross-run guarantees** (these are unreachable in single-event tests):
- same concept across events → exactly **ONE** driver; **0 duplicates** (no two drivers with equal sorted-canonical tokens);
- a driver coined at event #3 is **REUSED** (not re-proposed) at event #30;
- the registry grows by **EXACTLY** the # of distinct new concepts;
- a later emission of a folded form hits the **auto-alias fast-path** (B4);
- a **re-run of the same event** → **byte-identical** canonical names (event-level idempotency);
- a newly-accepted **novel token** is classified as a **known slot token** in a later event (VocabToken seam);
- **cross-producer:** news `oil_supply` and learner `oil_supply` resolve to the **SAME** driver.

### 15B — Layer-2 accumulation replay (REAL LLM, MEASURED — *this is the production-accuracy picture*)
Replay a **real, sizable corpus** in-session (subscription, §7) — NOT the §13 toy fixtures:
- **`eval_corpus.json` — GOLD-LABELED (this is what makes it ACCURACY, not just hygiene):** ≥40–60 RAW-ish
  snippets (actual 8-K MD&A / transcript Q&A / news wording — **noisy, not cleaned paraphrases**) across **≥8
  tickers × ≥2 quarters each** (so drivers RECUR). Each entry =
  `{id, evidence_text, source_catalog:["SRC:…"], gold:{expected_drivers:[{name,state,direction}], allowed_alternatives:[...], expected_rejections:[...]}, risk_tags:[K…], rationale}`.
  Without gold labels you measure consistency/hygiene, NOT accuracy.
- **CORPUS CONSTRUCTION RULES (so the number is REAL, not cherry-picked) — the tester builds this:**
  (a) **real source text** pulled from the actual graph/filings via the data sub-agents — NOT invented/cleaned
  paraphrases; (b) tickers/quarters chosen for **driver RECURRENCE** (same driver across quarters) **+ difficulty
  spread** (easy + hard + adversarial), not hand-picked easy ones; (c) **gold labels set BEFORE running the LLM**
  (pre-registered — never fit labels to the output); (d) each entry tagged with the **risk-class (K…)** it stresses,
  with ≥1 entry per CREATION-scoped risk family. Keep it lightweight (one tester, a pre-registered key) — NOT a
  multi-annotator pipeline.
- Same loop as 15A, emissions from the in-session producer-LLM; **context** stamped per event. **Start from the
  COLD-START registry and replay events in CHRONOLOGICAL order** (cold start → accumulate forward) — this is what
  makes 15B an honest *forward/live* accuracy number (§16); a pre-populated registry or out-of-order replay would
  fake-inflate reuse.
- **MEASURE + emit a machine-readable `eval_report.json`** (the GO/NO-GO artifact): **accuracy-vs-gold** (headline:
  cleaned output ∈ gold `expected_drivers`/`allowed_alternatives`; correct rejections counted) · reuse-rate ·
  duplication-rate · reject-rate · cross-run canonical-consistency · per-risk-class accuracy · **vocab-coverage**
  (% real tokens outside the banks) · false-reject count — benchmarked vs the plan's §H.9 targets, ending in an
  explicit **`GO` / `NO-GO`** verdict. **Scope the targets to harness scale:** the **≥70% within-ticker reuse
  after 5+** target IS reachable and is the headline bar. The **"≥85% once registry >150"** target is **N/A at
  harness scale** — a ≥40–60-snippet corpus can never push the registry past ~60 drivers, so the report MUST mark
  it **"N/A (production-scale target — unreachable in this harness)"** rather than score a `NO-GO` against it.

### 15C — False-reject regression set (Layer-1, GATED)
A corpus of **known-VALID names that MUST ALL pass** (false rejects silently destroy accuracy and are invisible
in "bad → reject" tests). Seed it from the §C/§D worked examples + every `COLD_START_SEED_DRIVERS` name + the
accepted forms produced in 15A.

### 15D — Registry-backend contract test (the swapped-out component)
`registry_fake` is swapped for Neo4j in prod; green here proves the reuse LOGIC given a *correct* backend, **not**
that Neo4j matches the fake's semantics (case-sensitivity · array-containment · null · ordering). Define the
reuse/contract tests so they run against **ANY** `Registry` implementation, and **run them against BOTH the fake
AND a throwaway Neo4j** in the ingestion harness. If Neo4j isn't available here, `eval_report.json` must state:
**"prod reuse behavior UNVALIDATED until the contract suite runs against Neo4j."** (Don't let the swap hide a mismatch.)

### Honest caveat (no overclaiming)
**15A CAN be 100%** (accumulation logic is deterministic). **15B gives a MEASURED rate, not a mathematical 100%**
(LLM is non-deterministic) — bigger/realer corpus → tighter read. A green `pytest` does NOT mean good accuracy;
**`eval_report.json` is the GO/NO-GO.** Pass-4/eval HARD-fails only on schema / source-integrity / infra (or with
`--enforce-llm`), never on a flaky property miss — but it **always** writes the report + verdict.

---

## 16. Structural blind spots — GREEN ≠ SAFE here (state them; do not assume-covered)

This harness **cannot** test the following — they belong to the ingestion harness / live monitoring, and a green
run says NOTHING about them:
- **Concurrency races** (two writers MERGE the same driver) — in-memory + single-threaded; ingestion-side (E11
  UNIQUE + retry). The 15D contract suite against real Neo4j is where this gets tested.
- **PIT-correct historical-backfill accuracy** — the harness has NO `registry_visible_at`, so a *backfill*
  accuracy number here would be **fake-inflated**. **Only LIVE/forward accuracy (15B) is honest in this harness.**
- **Evidence semantically SUPPORTS the claim** — V10 checks the `SRC:*` resolves, not that the source actually
  *says* it (LLM-judgment; only weakly observable in 15B).
- **Real Neo4j ≡ the fake's interface** — until 15D runs against Neo4j, prod reuse behavior is unvalidated.
