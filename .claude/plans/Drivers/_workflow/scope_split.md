# Scope Split — Driver CREATION layer vs Driver INGESTION layer

> Cartographer pass. Every E-item, Lever, validator, vocab-bank and schema-field in
> `CombinedPlan.md` (P1), `DriverOntology_Implementation.md` (P2) and `DriverImprovements.md` (P4)
> classified into **CREATION** (in scope — evidence → clean canonical name + companions, before write),
> **INGESTION** (out of scope — delegated to guidance-style writer reuse), or **STRADDLE**.
> All claims verified against current bytes on disk; line citations below.

---

## 0. The cut, in one diagram

```
EVIDENCE  ──►  [ CREATION LAYER  =  IN SCOPE ]                         ──►  input-JSON  ──►  [ INGESTION = OUT OF SCOPE ]
               ontology rules (R1-R11)                                     contract (E16)      guidance-style writer:
               canonicalize()/classify_token() PURE fn                     │                   MERGE, UNIQUE, PIT fields,
               slot grammar + §F vocab banks                               │                   supersession, two-phase
               standalone-shortcut path                                    │                   :EquivalenceToken Cypher,
               banned-content gate / new-token gate                        │                   :VocabToken store, 5 audit
               LLM author prompt + emission contract                       │                   labels, concurrency/race
               cold-start seed (the data)                                  │
               registry/vocab READ path  ◄──── SEAM ─────────────────────────────── reads what ingestion WROTE
```

The clean cut is **the input-JSON contract (E16)**. Everything that produces/validates a clean canonical
name + companion fields and then *hands E16 to the writer* is CREATION. Everything the writer does *with*
that JSON (MERGE, PIT visibility, supersession, promotion, audit rows, concurrency) is INGESTION.

---

## 1. E-item classification (E1..E30, E12 MOOT)

| Item | Bucket | One-line reason (cite) |
|---|---|---|
| **E1** Failed-proposal recipe / PARTIAL policy / exit codes | **STRADDLE → mostly INGESTION** | Sentinel/exit-code/`run_ledger` is writer↔orchestrator contract (P1:80-90). CREATION only needs the *handoff fact*: "reject one proposal, proceed with the rest." Exit-code semantics are ingestion. |
| **E2** Drop `validation_status` | **INGESTION** | Edits `Driver` schema in `Neo4jXBRLDesign.md`; promotion-at-write concern (P1:92-96). No effect on name-formation. |
| **E3** Purge curator/human language | **INGESTION** | Throughout `Neo4jXBRLDesign.md` (ingestion design doc) (P1:98-102). Policy hygiene on the writer/schema side. |
| **E4** §A vs §A.1 "per-session not per-emission" | **CREATION** | Defines WHEN the runtime envelope (ontology + registry catalog + vocab) is injected into the LLM author prompt (P1:104-108; P2:13). This is the producer's input contract. |
| **E5** PIT filter on bundle registry catalog | **STRADDLE → CREATION-facing read, INGESTION-sourced** | The *filter* `Driver.registry_visible_at <= run.pit_cutoff` is the registry READ path the producer needs (P1:112-116). But `registry_visible_at` is an INGESTION-written field. **HANDOFF SEAM #1.** |
| **E6** Fix alias validator V1 (`==parent.name`) | **CREATION** | V1 is a companion-field validator on `aliases` run before write (P1:118-122; P2:274). Pure name/alias logic. |
| **E7** Shape regex reject `__` | **CREATION** | `canonicalize()` step 1 / §D shape regex (P1:124-128; P2:234-240). Core name-shape gate. |
| **E8** Full STATES_VOCAB enumeration | **CREATION** | §F.5 state vocab is what `driver_state` is drawn from + the banned-in-name set (P1:130-158; P2:375-385). Drives canonicalize step 7. |
| **E9** Cold-start seed (two-tier PIT) | **STRADDLE → CREATION data + INGESTION load** | The *seed list* (`COLD_START_SEED_DRIVERS`, ~32 TIER-1 anchors) is creation-layer data the canonicalizer needs anchors from (P1:160-181; P2:659-690). The *epoch-sentinel `registry_visible_at` bootstrap MERGE* is ingestion. |
| **E10** Persist new-token slot mappings (`:VocabToken`) | **STRADDLE → CREATION reads, INGESTION writes** | Slot classification determinism is CREATION (canonicalize step 9 reads `slot_vocabs`). But the `:VocabToken` store + `vocab_visible_at` ON-CREATE/MIN-on-MATCH backdate + PIT-filter is INGESTION (P1:183-195; P2:443-453). **HANDOFF SEAM #2 — the biggest one.** |
| **E11** Concurrency safety (UNIQUE + transactional MERGE + retry) | **INGESTION** | `Driver.id` UNIQUE constraint + lookup-then-MERGE race handling (P1:197-201). Pure writer concern; explicitly in guidance-reuse target. |
| **E12** Predictor source-visibility | **MOOT (was CREATION)** | Superseded by E30; predictor is consumer-only so no driver-emission scope (P1:205-210). Not a live item. |
| **E13** Fiscal.ai consults registry + rejected-label handling | **STRADDLE → CREATION principle, INGESTION+Phase-3** | "All producers canonicalize before MERGE" is the CREATION reuse-before-create rule (ConceptReq §6). But it's a Phase-3 ingestion path; rejected-label store is ingestion (P1:223-227). |
| **E14** direction + exposure_role + source_id formula | **STRADDLE → CREATION emits, INGESTION persists** | `direction` is LLM-emitted (creation). `exposure_role`, the `source_id` STABLE-per-{ticker}:{quarter} formula, `superseded_by_run_id`, `CITES_EVIDENCE` edges are INGESTION/supersession (P1:229-235). CREATION just emits the per-item ticker+direction+evidence. |
| **E15** Mirror Map fixes | **STRADDLE → maps BOTH layers** | §J.1 map explicitly splits driver_ids (creation mirror of guidance_ids) vs driver_writer/constraints/supersession (ingestion mirror of guidance_writer) (P1:239-247; P2:616-657). Reference doc spanning the cut. |
| **E16** Shared writer-contract input JSON | **STRADDLE → THIS IS THE CUT LINE** | The input-JSON schema (`source_id, source_type, pit_cutoff, items[], propose_new_drivers[]`) IS the creation→ingestion handoff (P1:249-290; P2:545-582). CREATION must emit exactly this; the writer consumes it. **The clean cut lives here.** |
| **E17** XBRL/member linking non-blocking | **STRADDLE → INGESTION-leaning** | `xbrl_qname` resolution / member-match happens in `driver_concept_resolver` at write time (P1:292-296). But `base_label ∈ CANONICAL_BASE_LABELS` (V5) is a CREATION companion-field validator. |
| **E18** Evidence validation vs source catalog (V10) | **CREATION** | V10 validates `evidence[]` resolves against `source_catalog` before write (P1:298-302; P2:283). Emission-level validator; anti-hallucination on the produced tag. |
| **E19** Neo4j authoritative registry | **INGESTION** | Source-of-truth lock; JSON snapshots are derived cache (P1:304-308). Storage-authority decision. |
| **E20** Lock "Phase 1 = zero extraction-LLM" + per-mode routing | **CREATION** | Locks that canonicalization runs in Python not LLM head (L3) and that learner emits in-session, no 2nd extraction pass (P1:310-314). Core creation-architecture lock. |
| **E21** Final.md schema reconciliation | **STRADDLE → CREATION emission shape** | Migrates learner `§8 primary_driver/contributing_factors[i]` to `{driver_name, driver_state, direction, evidence}` (P1:316-320). This is the producer's emission schema = creation. §7 predictor stays free-form (not a producer). |
| **E22** Phase-2 dir KEEP SINGULAR | **INGESTION** | `types/driver/` directory naming for the Mode-2 `/extract` worker path (P1:324-328). Phase-2 ingestion routing. |
| **E23** R5 FULL rename Macro→Standalone, MACROS_VOCAB→SHORTCUTS_VOCAB | **CREATION** | Ontology R5 + §F.1 bank name + canonicalize step 8 (P1:330-338; P2:160,296-320,502). Pure naming-rule/vocab rename. |
| **E24** Inline writer doesn't invent missing propose_new_drivers | **CREATION** | V11: a tag referencing an unknown name with no proposal is rejected (P1:340-344; P2:284). Emission-integrity gate on the produced set. |
| **E25** allowed_states mismatch on reuse | **STRADDLE → CREATION rule, INGESTION audit** | "Registry wins; emission allowed_states ignored on reuse" is a CREATION reuse-semantics rule (P1:348-352; P2 V8/§E note). The drift-audit log is ingestion. |
| **E26** Lever #1 writer auto-repair wrapper | **STRADDLE → see §2** | Repair is writer-side (NOT inside pure canonicalize) but re-runs canonicalize + exact-match registry reuse — see Lever #1 row. |
| **E27** Lever #2 `:EquivalenceToken` store + N=2 promotion | **STRADDLE → see §2** | Synonym/plural/acronym folds feed canonicalize step 5 (creation), but the store/promotion/two-phase Cypher/PIT is ingestion — see Lever #2 row. |
| **E28** Lever #3 informed retry | **STRADDLE → mostly INGESTION/orchestration** | Re-emission of the same learner LLM is producer-adjacent, but the 3-stage merge + drift-guard + outcome enum live in orchestrator/writer — see Lever #3 row. **[SUPERSEDED 2026-05-29: E28 is now LEARNER SELF-CORRECT — the producer calls a `--dry-run` validate tool and fixes flagged tags in-session (≤3, stop-on-no-progress); the orchestrator write-gate is the authority. The orchestrator re-injection / 3-stage-merge / drift-guard described here is SUPERSEDED — see CombinedPlan §E28 + Harness_BuilderPrompt. This scratch file is analysis-only, not builder authority.]** |
| **E29** Audit telemetry tables (5 labels) | **INGESTION** | Pure observability on writer/self-heal behavior; "system self-heals without them" (P1:411-422; P2:694-729). No creation dependency. |
| **E30** Phase-1 producer = learner-only | **CREATION** | Defines WHO produces (learner) and who consumes (predictor) — scopes the entire creation layer to one producer + one emission schema (P1:212-221). |

---

## 2. The 3 Levers + audit tables (E26-E29) — detailed split

| Lever | Bucket | What is CREATION | What is INGESTION | Seam |
|---|---|---|---|---|
| **E26 / Lever #1** auto-repair wrapper | **STRADDLE** | Determines whether a state/period/magnitude-smuggled name can be *re-formed* into a clean canonical name (re-runs pure `canonicalize`); trend-partner preference; `≥2-token`/magnitude-narrow regex logic. (P4:219-361; P2:591-597) | Lives in `driver_writer.py` not canonicalize (L3 stays pure); commit decision is exact-match-against-registry (needs registry read) + writes `:DriverAutoRepair`. | Reads live registry to decide "exact-match existing Driver"; writes audit row. |
| **E27 / Lever #2** `:EquivalenceToken` + promotion | **STRADDLE** | The synonym/plural/acronym *maps* that `canonicalize()` step 5 folds with (creation determinism). Pattern-B shortcut `≥2-token` gate + R11 evidence gate is creation-side name admission. (P4:365-653; P2:443-470) | The `:EquivalenceToken` Neo4j store, N=2 promotion, two-phase Cypher (v5-4/v6-2), intra-MERGE to_token guard (v9-2), `equivalence_visible_at` MIN-backdate (v10-2), candidate-hiding, collision audits. | **SEAM #3:** promoted equivalences become creation-layer vocab via `load_vocab_snapshot()`. |
| **E28 / Lever #3** informed retry | **STRADDLE → INGESTION-leaning** | The retry *re-emits the same learner LLM* (producer re-run) — conceptually a creation retry. Prior-rejection-reason block is producer-input. (P4:657-705; P2:599-612) | 3-stage merge (drift guard / surgical replace / scope-creep block), `DriverWriteOutcome` enum, dry-run-via-writer loop, orch.py:1347 mirror — all orchestrator/writer machinery. | Retry fires off writer `--dry-run` rejection reasons (the E16 sidecar). |
| **E29** audit tables | **INGESTION** | (none) | All 5 labels (`:DriverAutoRepair`, `:DriverProposalRejection`, `:EquivalenceConflictAudit`, `:EquivalenceCollisionAudit`, `:DriverDriftAudit`) + UNIQUE/MERGE keys. Pure telemetry. (P4:316-359; P2:694-729) | none — self-heal works without them. |

**Net:** the three levers are the plan's accuracy push (~87% → claimed ~96-98%). Their *vocabulary effects*
(synonym folds, slot-vocab growth, shortcut admission) are genuinely creation-relevant; their *storage/promotion/
merge machinery* is ingestion. The creation review must judge the vocabulary-fold semantics and the name-admission
gates; it should NOT re-judge the Cypher/promotion/audit internals (those reuse guidance writer patterns).

---

## 3. Validators V1-V15 — split (P2 §E, lines 272-288)

| Validator | Bucket | Reason |
|---|---|---|
| V1 alias `canonicalize(entry)==parent.name` | **CREATION** | Companion-field correctness on produced aliases. |
| V2 alias doesn't bridge unrelated drivers | **CREATION** | Cross-driver alias integrity at emission. |
| V3 label tokens == name tokens (set) | **CREATION** | Companion `label` consistency. |
| V4 segment consistent with name | **CREATION** | Companion `segment` consistency. |
| V5 base_label ∈ CANONICAL_BASE_LABELS | **CREATION** | Companion `base_label` from §F.6 bank. |
| V6 allowed_states one class + size bound | **CREATION** | Companion `allowed_states` shape. |
| V7 definition one sentence, not tautology | **CREATION** | Companion `definition` shape. |
| V8 driver_state ∈ Driver.allowed_states | **STRADDLE → CREATION rule, reads registry** | Validates emitted `driver_state` against the *registry's* allowed_states — needs the registry read (seam). |
| V9 direction ∈ {long,short} | **CREATION** | Emitted-field enum. |
| V10 evidence resolves vs source_catalog | **CREATION** | Anti-hallucination on produced evidence (E18). |
| V11 every used name resolves to registry-or-proposal | **STRADDLE → CREATION rule, reads registry** | Emission integrity; "registry" side is an ingestion read. |
| V12 no dup proposal name in emission | **CREATION** | Within-emission integrity. |
| V13 every proposal used ≥1 tag | **CREATION** | Within-emission integrity. |
| V14 new-token gate passes | **CREATION** | Core new-token admission gate. |
| V15 no two Drivers share sorted tokens | **STRADDLE → INGESTION-leaning** | Registry-wide uniqueness invariant — enforced at write against the whole registry. |

**Read:** 11/15 validators are pure CREATION (companion-field + emission-level). V8, V11 straddle (they
validate produced fields *against the live registry* — a read seam). V15 is a registry-global invariant
(ingestion-leaning). None require ingestion *internals* beyond a registry read.

---

## 4. Vocab banks (P2 §F) + canonicalize steps (P2 §C) — all CREATION

| Bank / mechanism | Bucket | Note |
|---|---|---|
| §F.1 THEMES/OBJECTS/CUSTOMERS/GEOGRAPHIES/INSTITUTIONS/METRICS + SHORTCUTS_VOCAB | **CREATION** | Slot classification + standalone-shortcut source (P2:296-320). |
| §F.2 SYNONYM_MAP / §F.3 PLURAL_MAP / §F.4 ACRONYM_MAP | **CREATION** | canonicalize step 2+5 folds (P2:322-373). |
| §F.5 STATES_VOCAB | **CREATION** | banned-in-name + allowed_states source (P2:375-385). |
| §F.6 COMPOUND_METRICS + CANONICAL_BASE_LABELS | **CREATION** | R6 single-metric-slot + V5 base_label (P2:387-401). |
| §F.7 BANNED_CONTENT / §F.8 STOPWORDS / §F.9 ALLOWED_VERBAL_FORMS | **CREATION** | banned-content gate (canonicalize step 4+7) (P2:403-441). |
| `canonicalize()` 12 steps + `classify_token()` + `order_by_slot()` | **CREATION** | The pure name-formation function (P2:118-182). |
| §D shape regex + BNF grammar + new-token gate | **CREATION** | Name shape + slot grammar + token admission (P2:232-264). |
| §G thresholds (MAX_EFFECTIVE_SLOTS etc.) | **CREATION** | canonicalize length bound + V6 size (P2:476-485). |
| §H Conformance Index | **CREATION** | Rule→clause map for the name contract (P2:489-509). |
| **`load_vocab_snapshot()` writer-bootstrap loader** | **STRADDLE → THE SEAM** | Builds the `VocabSnapshot` canonicalize consumes, but **reads `:EquivalenceToken`/`:VocabToken`/`Driver.is_shortcut` from Neo4j with PIT filters** (P2:184-226). This is where CREATION reads INGESTION-written state. |

---

## 5. Schema fields (Neo4jXBRLDesign + scattered) — all INGESTION except where noted

| Field | Bucket | Note |
|---|---|---|
| `Driver.registry_visible_at` (MIN(DC.pit_cutoff)/epoch sentinel) | **INGESTION** | PIT visibility, written by writer; CREATION only *reads* it via E5 filter. |
| `Driver.is_shortcut: bool` (v8-1) | **STRADDLE** | Schema field (ingestion) but the *discriminator* canonicalize step 8 + bootstrap use to build `shortcuts` set (creation read). |
| `superseded_at / superseded_pit_cutoff / superseded_by_run_id` | **INGESTION** | Supersession triplet (L6) — pure writer/re-run semantics. |
| `:VocabToken.vocab_visible_at` | **INGESTION (written), CREATION (read)** | SEAM #2 field. |
| `:EquivalenceToken.equivalence_visible_at / status / observation_keys[]` | **INGESTION (written), CREATION (read promoted only)** | SEAM #3 field. |
| `DriverChange.pit_cutoff / result_path / source_id / run_id` | **INGESTION** | Persisted on write; CREATION emits the *values* via E16 but doesn't own the node. |
| `:FOR_COMPANY` edge `direction / exposure_role` | **STRADDLE** | `direction` emitted by creation; edge + exposure_role populated at write. |

---

## 6. CRITICAL — "creation" items that secretly depend on ingestion internals (the handoff seams)

These are the items the creation review MUST watch: they look like pure creation but read state that only
exists because ingestion wrote it. If ingestion is "out of scope," these are exactly where the clean hand-off
must be proven.

| # | Seam | Creation-side need | Ingestion-side dependency | Clean-cut requirement |
|---|---|---|---|---|
| **SEAM 1** | E5 PIT registry catalog filter | Producer's bundle must show only PIT-visible existing drivers (R1 reuse-first) | `Driver.registry_visible_at` (writer-computed MIN/sentinel) | CREATION may *read* `registry_visible_at`; must not compute or write it. The bundle renderer is the read boundary. |
| **SEAM 2** | E10 `:VocabToken` slot persistence | canonicalize step 9 `classify_token()` must be deterministic across runs | `:VocabToken` store + `vocab_visible_at` ON-CREATE/MIN-on-MATCH (v9-1/v10-1) PIT filter | `canonicalize()` stays PURE (takes `VocabSnapshot` param, v3-1). The *bootstrap loader* (`load_vocab_snapshot`) does the Neo4j read — that loader is the seam, NOT canonicalize. (P2:85, 184-226) |
| **SEAM 3** | E27 promoted equivalence folds | canonicalize step 5 synonym/plural/acronym maps must include runtime-promoted folds | `:EquivalenceToken` store + N=2 promotion + `equivalence_visible_at` + status=promoted filter | Same loader boundary as SEAM 2. Only `status="promoted"` + PIT-filtered rows enter the snapshot; candidates are hidden (v2 Fix #2). |
| **SEAM 4** | V8 / V11 registry-aware validators | Validate emitted `driver_state`/`driver_name` against the live registry | live `Driver.allowed_states` / `Driver.name` set | These run at write/dry-run time reading the registry. CREATION owns the *check*; the registry read is shared infra (guidance-reuse). |
| **SEAM 5** | E9 cold-start seed | canonicalizer needs slot anchors on day 1 (else ~80% accuracy, P1:162) | bootstrap MERGE of `COLD_START_SEED_DRIVERS` with epoch-sentinel `registry_visible_at` | The seed *list* (data) is creation; the *loading* (idempotent MERGE at first boot) is ingestion. Keep the list in `driver_writer.py` as a constant (OQ4=hardcoded). |
| **SEAM 6 (cut line)** | E16 input-JSON contract | CREATION must emit EXACTLY this JSON and nothing in name-formation may read writer internals | writer consumes JSON, does MERGE/PIT/supersession | This is the designed clean cut. Verified: creation emits `{source_id, source_type, pit_cutoff, items[], propose_new_drivers[]}`; writer owns everything downstream. (P2:545-582) |

**Verdict on the seams:** the architecture is *designed* to keep canonicalize pure (v3-1: vocab passed as a
frozen `VocabSnapshot` parameter, no DB reads inside — P2:85, 87-88, 636-645). All ingestion coupling is
funneled through ONE function, `load_vocab_snapshot()` (P2:184-226), plus the bundle renderer's PIT-filtered
registry read (E5). That is a *clean* seam: creation reads ingestion-written state through two well-defined
boundaries and never reaches into MERGE/promotion/supersession internals. This is a genuine design strength,
not a leak — confirmed against current bytes.

---

## 7. The minimal CREATION-LAYER component list

Files/functions the creation layer needs (and nothing more). Mirrors the guidance pipeline; "NEW" = no guidance equivalent.

| Component | New / Reuse | Role | Source-of-truth |
|---|---|---|---|
| `DriverOntology.md` (R1-R11, §F not here) | exists | The naming contract the LLM reads (rules only) | R2 verified |
| `DriverOntology_Implementation.md` §C `canonicalize()` + `classify_token()` + `order_by_slot()` | NEW (mirror `guidance_ids.canonicalize_unit` shape) | PURE name-formation fn; `(candidate, VocabSnapshot)→str\|REJECTION` | P2:83-182 |
| `driver_ids.slug()` + `driver_change_id()` (PLANNED) | reuse `guidance_ids.slug()` (verbatim) / mirror `build_guidance_ids()` PATTERN (`guidance_change_id()` does NOT exist; guidance id is 5-part, driver_change_id is 3-part) | slugify + slot ID | P2:622-626; G1 verified `slug()` @ guidance_ids.py:21 |
| `DriverOntology_Implementation.md` §D shape regex + BNF grammar + new-token gate | NEW | name shape + slot order + token admission | P2:232-264 |
| §F.1-§F.9 vocab banks (markdown SEED) | NEW (data) | THEMES/OBJECTS/.../SHORTCUTS_VOCAB/SYNONYM/PLURAL/ACRONYM/STATES/COMPOUND/BANNED/STOPWORDS/ALLOWED_VERBAL | P2:292-441 |
| §E validators V1-V14 (+V_no_consecutive_underscores) | NEW | companion-field + emission-level checks (V15 is registry-global → ingestion) | P2:268-288 |
| §G thresholds | NEW (constants) | length / states-size / evidence-min bounds | P2:476-485 |
| `load_vocab_snapshot(run_pit_cutoff)` **(THE SEAM)** | NEW | builds frozen `VocabSnapshot` from markdown seed + PIT-filtered Neo4j reads | P2:184-226 |
| Bundle/vocab renderer (registry catalog excerpt, PIT-filtered, candidates hidden) | reuse guidance "query 7A" render pattern | renders ontology + PIT registry catalog + vocab + thresholds + evidence into LLM prompt | P2:11-21; P1:635-639 |
| `COLD_START_SEED_DRIVERS` constant (the list, ~32 TIER-1) | NEW (data, code-time constant per OQ4) | day-1 slot anchors | P2:659-690 |
| `earnings-learner/SKILL.md` emission contract | edit existing | the LLM-author prompt: emit `{driver_name, driver_state, direction, evidence}` + `propose_new_drivers[]` incl. `is_shortcut`; reuse-before-create instruction | P1:580-584, 668-673; P5 = `DriverOntology Prompt.md` |
| Lever #1 *re-canonicalize* logic (the repair decision rules) | NEW (creation-relevant slice of E26) | decides if a smuggled name can be re-formed into a clean canonical name | P4:219-361 — note the *commit/audit* half is ingestion |
| Shortcut admission gate (Pattern B: ≥2-token + zero-slot + R11 evidence) | NEW (creation-relevant slice of E27) | name-admission gate for standalone shortcuts | P2:466-470; P4:449-457 |

**Out of the minimal creation set (delegated to guidance-style writer reuse):** `driver_writer.py` MERGE +
constraints + supersession, `:VocabToken`/`:EquivalenceToken` stores + promotion + two-phase Cypher, all 5
audit labels, `driver_write_cli.py` orchestration + dry-run + sidecar/exit-codes, Lever #3 3-stage merge,
concurrency/UNIQUE, `Driver.registry_visible_at`/`vocab_visible_at`/`equivalence_visible_at` computation.

---

## 8. Overstatements / findings (anti-false-positive bar applied)

1. **"~96-98% accuracy projection" is UNSUPPORTED as stated.** P1:883-884 and P4:5 label it a *projection
   pending Q1 measurement* up from ~87% baseline — but the headline §1 Goal (P1:5) and Appendix A present
   it without that hedge in places. The honest figure is: plan's *enforced bar* is ≥90% (P1:35); ~96-98%
   is an unmeasured forecast built on summed lever recoveries (Lever#1 ~3-4pp + Lever#2 ~5-7pp + Lever#3
   ~3-4pp, themselves "projections" per v3-12). The user's "~100%" target is NOT mechanically demonstrated;
   it rests on cold-start seed quality + LLM slot-classification of *novel* object/customer/theme tokens that
   TIER-1 seed explicitly does NOT cover (P1:177 slot-coverage gap). **Flag for the accuracy review.**

2. **"100% reuse of guidance pipeline" is not claimed — and correctly so.** P1:53 notes "3 of 5 bots flagged
   don't overclaim 100% extraction-pipeline reuse." The plan reuses `guidance_ids.slug`/`guidance_change_id`,
   `guidance_writer.create_*_constraints`+MERGE pattern, and the bundle-render pattern — but explicitly lists
   NEW logic (supersession, `:VocabToken`/`:EquivalenceToken` writers, audit writers, canonicalize itself).
   Verified the three guidance files exist at the cited LOC (1000/524/656). Reuse claim is honest.

3. **Cold-start seed count is internally consistent now** (E9 ~32 anchors; §12 ≥30 entries) — the Round-8
   "contradiction" was correctly rejected (P1:67). Verified: 11 macro + 6 compounds + 5 geo + 5 inst + 5
   metrics = 32 (P1:166-171). No false gap.

4. **ConceptReq coverage matrix (10 ✅ + 2 ⏸) is verifiable against the live file.** ConceptReq §3.3 IS
   rewritten to consumer-only (R1:61) matching E30 — the matrix's "§3.3 RESOLVED" claim (P1:533) holds against
   current bytes. The earlier "file missing" panic (Round 7) is stale; file is present (102 lines). No live gap.

5. **The L3 purity claim survives the seams.** Despite E5/E10/E27 reading ingestion state, `canonicalize()`
   itself takes a frozen `VocabSnapshot` and does zero DB reads (P2:85-88). The coupling is isolated to
   `load_vocab_snapshot()`. This is the single most important fact for the "clean hand-off" judgment, and it
   checks out on disk. NOT an overstatement.

6. **DriverNameRisks.md (R3, 419 lines) is NOT consumed by any creation mechanism in P1/P2/P4.** It is forensic
   scratch (4 un-deduped risk taxonomies). No E-item, validator, or vocab bank traces to it. Per scope it is a
   *requirement file to account for*, not a creation component — correctly absent from the component list. (Its
   coverage is a separate question for the requirements-coverage reviewer, not this scope split.)

---

## 9. Bottom line for the creation-layer review

- **IN SCOPE (judge on merits):** the ontology rules, `canonicalize()`/`classify_token()`, §D grammar +
  new-token gate, §F vocab banks, V1-V14 (V8/V11/V15 with the registry-read caveat), §G thresholds,
  standalone-shortcut path, banned-content gate, the learner emission contract / author prompt, the
  cold-start seed *list*, and the registry/vocab READ path (`load_vocab_snapshot` + bundle renderer).
- **OUT OF SCOPE (only verify clean hand-off):** writer MERGE/UNIQUE/constraints, PIT-visibility *field
  computation*, supersession triplet, `:EquivalenceToken`/`:VocabToken` stores + promotion + two-phase
  Cypher, 5 audit labels, concurrency/race, exit-code/sentinel/sidecar plumbing, Lever #3 3-stage merge.
- **The clean cut = E16 input-JSON contract** (P2:545-582). Verified: creation emits exactly that JSON;
  nothing in name-formation reaches into writer internals; the only ingestion coupling is two well-defined
  read boundaries (`load_vocab_snapshot` + PIT-filtered registry render), and `canonicalize()` stays pure.
- **Watch the 6 seams** (§6). They are clean by design, but they are exactly where a "creation is done" claim
  could hide an ingestion dependency.
