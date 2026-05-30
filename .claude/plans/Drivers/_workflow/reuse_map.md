# Driver CREATION Layer — Guidance-Pipeline Reuse Map

> Scope: the **creation layer only** (evidence → clean canonical validated driver name + companion fields,
> BEFORE the Neo4j write). Ingestion (writer MERGE, PIT fields, supersession, EquivalenceToken/VocabToken
> promotion Cypher, audit labels, concurrency) is OUT OF SCOPE per the task — it is judged only on the
> hand-off contract (see §5).
>
> Every claim below was verified against the **current bytes on disk** of G1/G2/G3 (read in full),
> G4/G5/G6 (skimmed), and the spec files. Line cites are to the real code, not the plan's own claims.
> The plan's documented ">=9 false-positive (stale-state)" history means NOTHING here is taken on the plan's word.

Files verified (line counts from `wc -l`):
- G1 `guidance_ids.py` — **1000 LOC** (plan calls it "1000 LOC" ✓)
- G2 `guidance_writer.py` — **524 LOC** (plan calls it "524 LOC" ✓)
- G3 `guidance_write_cli.py` — **656 LOC** (plan calls it "656 LOC" ✓)
- concept_resolver.py — 442 LOC (E15 mirror target; public funcs verified)
- G4 extraction_worker.py — Mode-2 only, type-driven (`TYPE=guidance`), Redis `extract:pipeline`
- G5 `.claude/skills/extract/types/guidance/` — primary-pass.md / enrichment-pass.md / core-contract.md / guidance-queries.md (all present)
- G6 `.claude/skills/guidance-inventory/` — SKILL.md / QUERIES.md (7A at L480) present

---

## §1. THE HEADLINE FINDING (verify first — load-bearing)

**The single most-reused thing in the plan — `slug()` — is real and copy-paste-ready. Almost everything
else the creation layer needs is NET-NEW.** The guidance pipeline has NO canonicalization grammar, NO slot
classifier, NO token reorderer, NO banned-content gate, NO vocab snapshot, NO shortcut handler. Guidance's
"canonicalization" is entirely about UNITS and VALUES (`canonicalize_unit`, `canonicalize_value`), not about
NAMES. The driver creation layer's whole reason to exist (`canonicalize(candidate, vocab) -> name`) has zero
guidance equivalent.

So the honest split for the CREATION layer is roughly:
- **REUSABLE AS-IS:** ~1 function (`slug`, 6 lines) + 1 structural pattern (top-level builder shape, validate-then-assemble).
- **REUSABLE-WITH-CHANGES:** the CLI orchestration skeleton (G3 `main()`), the per-item validate loop (G2 `_validate_item`), concept_resolver (financial sliver only).
- **NET-NEW:** the entire `canonicalize()` body, `classify_token`, `order_by_slot`, `VocabSnapshot`, shape regex, new-token gate, banned/state gates, standalone-shortcut, the 15 validators V1-V15, cold-start seed.

---

## §2. Does guidance_ids.py already contain a slug()/canonicalize() the driver layer should mirror? (the task's direct question)

**YES for `slug()` — it should be mirrored verbatim. NO for `canonicalize()` — guidance has nothing the
name layer can reuse.**

### 2.1 `slug()` — REUSE VERBATIM. Quoted from G1 `guidance_ids.py:21-26`:

```python
def slug(text: str) -> str:
    """Lowercase, replace non-alphanumeric with _, collapse repeats, trim edges."""
    s = text.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s.strip('_')
```

This is EXACTLY what `DriverOntology_Implementation.md` §B2 ("slug() lowercases, replaces non-alphanumeric
runs with `_`, strips edge `_`") and §J.1 (`driver_ids.slug() <- guidance_ids.slug() (verbatim)`) describe.
**VERIFIED — the plan's "verbatim" claim is correct.**

One subtlety the driver layer must NOT miss: `slug()` does NOT enforce the driver shape regex. It happily
produces `1foo` (digit-leading) or single-char output. The driver layer's `SHAPE_REGEX`
(`^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$`, P2 §D / E7) is a SEPARATE downstream gate — `slug()` is only step B2;
the shape check is the C-step-1 gate. They are correctly kept distinct in the spec. Reusing `slug()` does
NOT get you shape validation for free.

### 2.2 `canonicalize_unit()` / `canonicalize_value()` — NOT REUSABLE for the name layer.

G1 has two functions with "canonicalize" in the name (`canonicalize_unit` L461, `canonicalize_value` L495)
plus a 3-axis resolver chain (`_resolve_kind` L254, `_resolve_money_mode` L302, `_resolve_ratio_subtype` L329).
**These operate on numeric UNITS (usd / m_usd / percent / basis_points / count), not on driver names.** They
share the WORD "canonicalize" with `driver_ids.canonicalize()` but ZERO logic. A reader skimming the plan
might assume the driver canonicalizer mirrors these; it does not and must not. The driver `canonicalize()`
(P2 §C, 95 lines of pseudocode) is a token-grammar pipeline (shape → multi-token sub → tokenize → stopword
strip → per-token synonym/plural/acronym map → dedup → banned/state gate → shortcut → classify_token →
order_by_slot → metric-presence/length bound → emit). None of those 12 steps exists in G1.

**Confirmed by grep:** `classify_token`, `order_by_slot`, `slot_order`, `effective_slot`, `SHAPE_REGEX`,
`VocabSnapshot` — ZERO hits anywhere in `earnings-orchestrator/scripts/`. All net-new.

---

## §3. REUSE MAP

### 3.1 REUSABLE AS-IS (copy directly)

| Driver-layer need | Guidance source (file:lines) | Notes |
|---|---|---|
| `slug()` | G1 `guidance_ids.py:21-26` | Verbatim. The one true verbatim reuse. Spec §J.1 row 1 = VERIFIED. |
| Top-level builder *shape* (single entry point: validate required fields → compute slugs → assemble IDs → assert prefixes → return dict) | G1 `build_guidance_ids()` `:814-1000` | Reuse the *structure* (validate→assemble→return dict), not the body. The body is unit/value resolution. `guidance_id = f"guidance:{label_slug}"` / `guidance_update_id = f"gu:{...}"` ID-assembly pattern (`:962-966`) is a good template for the driver slot-ID, but the driver ID is content-different (see §4 E15 row 2). |
| Dry-run-vs-write gating pattern | G2 `write_guidance_item()` `:396-407` (dry_run short-circuits before feature-flag) | Pattern reuse for the `driver_write_cli --dry-run` informed-retry loop (P2 §J Lever #3). |
| Per-item error-collecting CLI loop (collect `errors[]`, continue, emit sidecar JSON) | G3 `main()` `:502-554` + sidecar `:646-650` | Structural template for E16 sidecar `/tmp/dr_written_{source_id}_{run_id}.json` + E1 PARTIAL exit codes. |

### 3.2 REUSABLE-WITH-CHANGES (mirrors, but modify)

| Driver-layer component | Guidance source | Required modification |
|---|---|---|
| `driver_write_cli.py main()` orchestration | G3 `guidance_write_cli.py:456-652` | STRIP guidance-specific machinery: `fye_month`, `_ensure_period`/`build_guidance_period_id` (4-step fiscal cascade `:203-292`), `member_map`/`_apply_member_map` (`:405-453`), Redis fiscal cache (`:99-200`). Driver input JSON (P2 §J / E16) has NO period, NO fye_month, NO members. KEEP: arg parsing, JSON load, per-item try/except, sidecar write, exit-code emission. The plan's E16 "engineer copying guidance_write_cli would inherit guidance-specific assumptions (fye_month, period_u_id)" warning is CORRECT and well-founded — verified those assumptions are pervasive in G3. |
| `_validate_item()` per-item field guards | G2 `guidance_writer.py:59-158` | Guidance validates `REQUIRED_ITEM_FIELDS` + per-share/unit guards A–H. Driver layer mirrors the *idea* (validate before write, return `(ok, err)`) but the CHECKS are the 15 validators V1–V15 (P2 §E) — entirely different content (alias canonicalization, slot/segment consistency, allowed_states class, evidence SRC-catalog resolution). Reuse the harness; rewrite every check. |
| `create_guidance_constraints()` | G2 `guidance_writer.py:492-524` | MERGE-idempotent UNIQUE-constraint pattern is identical in shape. Driver layer = `create_driver_constraints()` with driver labels (`Driver.id` UNIQUE per E11, `:VocabToken`, `:EquivalenceToken`, 5 audit labels). Spec §J.1 maps this; E15 adds the row. **NOTE: this is mostly an INGESTION concern (out of scope here) — listed only because the creation layer's cold-start seed loader (P2 §J.2) shares the bootstrap-MERGE idiom.** |
| `concept_resolver.py` (financial-sliver reuse) | concept_resolver.py public funcs: `load_concept_cache` `:272`, `resolve_xbrl_qname` `:294`, `apply_concept_resolution` `:327`, `resolve_concept_family` `:408` | Driver layer reuses ONLY for `base_label → xbrl_qname` resolution on the financial-driver sliver (E15 / E17). Most drivers (macro/news/positioning/theme) have `xbrl_qname = null` → resolver not called. Conservative fail-closed design (exact local-name match, pass-through on unknown) is exactly what E17 "non-blocking" wants. Reuse with a null-guard wrapper. |

### 3.3 NET-NEW (no guidance equivalent — write from scratch)

These are the heart of the creation layer and have **zero** guidance source to copy:

| Net-new component | Spec location | Why no guidance equivalent |
|---|---|---|
| `canonicalize(candidate, vocab) -> str \| REJECTION` (12-step token grammar) | P2 §C `:118-182` | Guidance canonicalizes units/values, never names. Confirmed grep-empty. |
| `classify_token(t, slot_vocabs)` | P2 §C step 9 `:166` | No slot concept anywhere in guidance. |
| `order_by_slot()` / SLOT_ORDER (theme→object→customer→geography→institution→metric) | P2 §C step 10 `:169`, §D | Guidance has no multi-slot name grammar. |
| `VocabSnapshot` dataclass (synonym/plural/acronym/shortcuts/slot_vocabs/banned/stopwords/states/multi_token_subs/compound_metrics) | P2 §C `:88-116` | Guidance has unit alias dicts (`UNIT_ALIASES` G1:44), not a vocab snapshot. Different domain. |
| `SHAPE_REGEX` `^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$` | P2 §D `:237` / E7 | Guidance has no name-shape gate (slug is unconstrained). |
| New-token gate (a)–(e) | P2 §D `:258-264` | No guidance equivalent. |
| Banned-content + state-in-name gates | P2 §C step 7 `:154-158`, §F.7/§F.5 | No equivalent. |
| Standalone-shortcut handling (R5) | P2 §C step 8 `:161-163`, §F.1 | No equivalent. |
| 15 validators V1–V15 | P2 §E `:272-288` | Guidance's `_validate_item` is a different, smaller check set. |
| Cold-start seed `COLD_START_SEED_DRIVERS` | P2 §J.2 `:663-683` | Guidance has no seeded registry. |
| `load_vocab_snapshot(run_pit_cutoff)` bootstrap loader | P2 §C `:187-226` | Net-new (PIT read path — borrows query *idiom* from 7A, see §4). |
| LLM author prompt / emission contract (P5) | `DriverOntology Prompt.md` (179 lines) + DriverOntology.md | Guidance has its own extract passes (G5) but driver-NAME authoring is a different contract. |

---

## §4. PLAN-CLAIM CHECK (each reuse claim → VERIFIED / OVERSTATED / WRONG vs real code)

### Claim A — P1 L7 "Guidance pipeline reuse pattern: writer/IDs/MERGE/concept-resolver/member-map machinery REUSED" (CombinedPlan L29)
**VERDICT: PARTIALLY OVERSTATED for the creation layer.**
- "IDs ... REUSED" — only `slug()` is verbatim. The ID *builder* `build_guidance_ids` is a structural
  template, not reusable code (its body is unit/value resolution). VERIFIED-as-template, OVERSTATED-as-"reuse".
- "concept-resolver ... REUSED" — VERIFIED for the financial sliver (funcs exist, conservative design fits E17).
- "member-map ... REUSED" — **WRONG / N-A for creation layer.** Member-map (`_apply_member_map` G3:405,
  `_build_live_member_map` G3:426) is guidance-segment→XBRL-Member linking. The driver layer has NO member
  concept; E16 input JSON has no members. This is dead weight to "reuse" and must be STRIPPED, not mirrored.
  (L7 lumps it into the reuse list; for drivers it is a non-reuse.)
- "writer/MERGE ... REUSED" — INGESTION (out of scope). For the creation layer this matters only as the
  hand-off target (§5). The MERGE *pattern* (atomic per-item, ON CREATE/ON MATCH, MATCH-pre-existing) is
  genuinely mirror-able (G2 `_build_core_query` :163-259), but that is ingestion.

### Claim B — P2 §J.1 Mirror Map row `driver_ids.slug() <- guidance_ids.slug() (verbatim)`
**VERDICT: VERIFIED.** Exact-quoted above (G1:21-26). Correct.

### Claim C — P2 §J.1 Mirror Map row `driver_ids.driver_change_id() <- guidance_ids.guidance_change_id() (same 3-component slot ID pattern)`
**VERDICT: WRONG (references a function that does not exist).**
`grep` for `guidance_change_id` / `change_id` in G1 and G2 = **ZERO hits.** Guidance has NO `guidance_change_id()`.
The real guidance ID functions are `build_guidance_ids()` (G1:814) producing `guidance_id` (`guidance:{label_slug}`,
G1:962) and `guidance_update_id` (`gu:{source}:{label}:{period}:{basis}:{segment}`, G1:963-966). So:
- the *named* mirror source is fictional;
- the *real* mirror source is the `guidance_update_id` slot-concatenation pattern at G1:963-966 (which IS a
  multi-component slot ID — the plan's "3-component" count is also imprecise; `guidance_update_id` is 5-component).
This is exactly the kind of "engineer copies the mirror map verbatim → hits wrong file/name" hazard E15 itself
warns about, and the §J.1 map still contains a bad row. **Recommend: fix §J.1 to cite `guidance_update_id`
assembly (G1:963-966), drop the invented `guidance_change_id` name.**

### Claim D — P2 §J.1 / E15 row `registry+vocab loader <- bundle renderer's "guidance query 7A" pattern (PIT-filtered render ... NOT warmup_cache.py)`
**VERDICT: VERIFIED-with-caveat.**
- The E15 *correction itself* (replace the old "warmup_cache.py concept-cache loader" claim with "guidance
  query 7A") is SOUND: `warmup_cache.py` is verified to be an XBRL-concept warmup shim
  (`scripts.earnings.builders.warmup_cache`), NOT a registry/vocab loader — so the original claim WAS
  misleading and E15 correctly fixes it.
- Query 7A is REAL (G6 `guidance-inventory/QUERIES.md:480-487`) and IS a "feed existing labels to the LLM so
  it reuses canonical names" pattern — the right conceptual mirror.
- **CAVEAT (gap the plan glosses):** 7A returns only `DISTINCT g.label, g.id` and is **NOT PIT-filtered**.
  The driver loader needs aliases + segment + allowed_states + definition per Driver AND a
  `Driver.registry_visible_at <= run.pit_cutoff` filter (P2 §A item 2, E5). So 7A is a *shape* mirror only;
  the driver render is materially richer + PIT-gated. The plan does say "PIT-filtered render"; just don't
  expect 7A to provide it — it provides neither the fields nor the filter. Net-new query, 7A-shaped.

### Claim E — P2 §J.1 NET-NEW list (`merge_driver_change_with_supersession`, `write_vocab_token`, `write_equivalence_token`, `write_audit_row`)
**VERDICT: VERIFIED as net-new** (grep confirms none exist in guidance). BUT these are all **INGESTION**
components (writer/supersession/promotion/audit) — out of scope for the creation-layer judgement. The
creation layer correctly does NOT depend on them; it only must emit the input JSON they consume (§5).

### Claim F — §10 per-file LOC estimates
| Plan estimate (§10 `:556-593`) | Reality check | Verdict |
|---|---|---|
| `driver_ids.py ~500 LOC` "(mirror guidance_ids.py + canonicalize(candidate,vocab) + classify_token())" | guidance_ids is 1000 LOC but ~all of it (units/values/periods) is NOT mirrored. Real reuse from G1 ≈ `slug()` (6 LOC) + builder shape. The ~500 is ~95% NET-NEW (canonicalize grammar + classify_token + slot ID + VocabSnapshot). | **OVERSTATED as "mirror"** — the LOC number may be fine, but "mirror guidance_ids.py" mischaracterizes it; it is a from-scratch grammar engine that imports one helper. |
| `driver_writer.py ~430 LOC` "(mirror guidance_writer.py + Levers)" | Validator harness + constraint shape genuinely mirror G2; but V1-V15 bodies + Levers + supersession are net-new. Plausible LOC; "mirror" again over-credits reuse. | OVERSTATED-as-"mirror", LOC plausible. (Mostly ingestion anyway.) |
| `driver_write_cli.py ~400 LOC` | G3 is 656 LOC; after stripping period/member/fiscal-cache machinery the reusable skeleton is maybe ~150 LOC, rest net-new (input JSON E16, retry loop). | LOC plausible; reuse fraction lower than "mirror" implies. |
| `driver_concept_resolver.py ~150 LOC (financial sliver)` | concept_resolver is 442 LOC; a financial-sliver subset + null-guard ≈ 150 is reasonable. | **VERIFIED reasonable.** |
| `registry+vocab bundle renderer ~80 LOC` | 7A-shaped + PIT filter + richer fields. ~80 is plausible. | VERIFIED reasonable. |

### Claim G — Appendix A "Accuracy after applied: ~96-98% projection"
**VERDICT: OVERSTATED / UNSUPPORTED.** The plan's own hard bar is >=90% (§3), and §12 explicitly says the
reuse-rate numbers are "initial estimates pending real-data calibration." The 96-98% is a projection with no
measurement behind it; the plan even labels it "pending Q1 measurement." Flagging per the anti-overstatement
rule: this number should not be read as achieved accuracy. (Does not block the creation layer; it is a claim
hygiene issue.)

### Claim H — §3 / Goal "100% reuse of guidance pipeline templates"
**VERDICT: OVERSTATED.** As §1–§3 show, the creation layer is majority NET-NEW. The plan's *body* is actually
honest about this (the §10 "Honesty note: total engineering = ~2000 LOC" and the L7 "minimalism + leverage"
framing are measured), but any headline "100% reuse" / "maximum reuse" phrasing overstates what the
creation layer can borrow. Reuse is real but narrow: `slug()` + structural skeletons + concept_resolver sliver.

---

## §5. HAND-OFF CHECK (the only ingestion question in scope): does CREATION emit exactly the writer's input JSON, with no hidden ingestion dependency?

**VERDICT: CLEAN hand-off, with two cited consistency nits.**

The creation layer's output is the E16 input JSON (P2 §J `:547-581`): `{source_id, source_type ∈
{learner_result,news,fiscal_kpi}, pit_cutoff, result_path, run_id, source_catalog, items:[{ticker,
driver_name, driver_state, direction, exposure_role?, evidence}], propose_new_drivers:[{name, label,
base_label?, segment, definition, allowed_states, aliases, is_shortcut}]}`.

- **No reverse dependency:** `canonicalize()` takes `(candidate, VocabSnapshot)` as a PURE function (P2 §C,
  L3 locked: "NO Neo4j reads inside"). It does NOT read the writer, the MERGE, or any audit label. The
  VocabSnapshot is built by `load_vocab_snapshot()` (read-only Neo4j) BEFORE any canonicalize call. So
  creation does NOT secretly depend on ingestion internals. VERIFIED clean.
- **Mirrors guidance's CLI-is-sole-authority contract:** G3 recomputes IDs internally (`_ensure_ids` always
  overwrites pre-computed fields, G3:341-390) — driver `driver_write_cli` should do the same (canonicalize is
  authoritative, ignore any LLM-supplied canonical fields). Good pattern to mirror; it is a CREATION-side
  decision, not ingestion.
- **NIT 1 (in scope):** guidance writer keys on `source_type ∈ {8k,10q,10k,transcript,news}` (G2
  `SOURCE_LABEL_MAP` :42-48). Driver `source_type ∈ {learner_result, news, fiscal_kpi}` (E16). These are
  DISJOINT enums. A driver writer that "mirrors" `_validate_item`'s `SOURCE_LABEL_MAP` check must REPLACE the
  enum, not inherit it — else every driver item fails validation. The plan's E16 names the right enum;
  just flagging that the mirror must not copy G2:42-48 literally.
- **NIT 2 (in scope):** guidance items REQUIRE `period_u_id` + `quote` + `given_date` (G2
  `REQUIRED_ITEM_FIELDS` :52-56). Driver items have NONE of these. The creation→writer contract must not
  carry guidance's required-field list. Verified the E16 contract correctly omits them.

Conclusion: the creation layer hands off a self-contained, guidance-shaped JSON; a guidance-style writer can
consume it after swapping the source_type enum and required-field list. No leakage of ingestion internals
into creation.

---

## §6. BOTTOM LINE for the three hard conditions (creation layer only)

1. **~100% naming accuracy:** the mechanism that delivers determinism (`canonicalize()` + classify_token +
   gates + V1-V15) is NET-NEW and well-specified in P2 §C/§D/§E; reuse does not help or hurt accuracy here.
   The 96-98% projection is unsupported (Claim G) — treat the bar as the plan's own >=90%, accuracy TBD by
   measurement.
2. **Requirement-file coverage:** not re-judged here (separate dimension); this map only verifies reuse.
3. **Minimum incremental work / max reuse:** reuse is REAL but NARROW — `slug()` verbatim, structural
   skeletons (builder/CLI/validator-harness/constraints), concept_resolver financial sliver. The "mirror
   guidance" framing in §J.1 + §10 over-credits reuse; the creation layer is majority from-scratch. Two
   mirror-map defects to fix: the fictional `guidance_change_id` row (Claim C) and the member-map non-reuse
   buried in L7 (Claim A). Neither blocks the build; both would mislead an engineer copying the map.
