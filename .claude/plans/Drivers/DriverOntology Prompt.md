You are rewriting the driver-name ontology. This is a planning task: do not edit any file unless the user later gives explicit approval.

---

**POST-v10 PREAMBLE — MUST READ BEFORE DRAFTING (added after v10 fold):**

The ontology has evolved through a v6 → v10 fold (DriverImprovements.md v2–v10 levers folded into CombinedPlan.md §5.7 as E26–E29; E30 added separately). Any regeneration of `DriverOntology.md` MUST preserve the following decisions:

1. **R5 wording**: Use **"Standalone shortcut"** (NOT "Macro shortcut") — per E23 / OQ3, R5 covers macro, regulatory, corporate-action, and event shortcuts (multi-domain, not macro-only).
2. **`is_shortcut` discriminator (v8-1)**: Drivers carry an `is_shortcut: bool DEFAULT false` schema property. Shortcut Drivers are registered directly as `:Driver{name, is_shortcut: true}` per E27 Pattern B — NO parallel shortcuts store. Runtime shortcuts vocab = `SHORTCUTS_VOCAB` markdown seed (§F.1) PLUS live `:Driver` registry filtered by `is_shortcut=true`.
3. **E30 — producer scope**: Phase-1 driver producer is **LEARNER ONLY**; predictor is consumer-only (reads registry catalog, never writes). Predictor's `prediction/result.json` §7 `key_drivers[]` stays free-form analysis prose. Do NOT design rules that assume predictor emits canonical drivers.
4. **R6 / compound metrics ≠ shortcuts**: Compound metrics (§F.6 `COMPOUND_METRICS`) are derived multi-component measures (e.g., `gross_margin = revenue − cogs`). Event-shortcuts (e.g., `share_buyback`, `fda_approval`) live in §F.1 `SHORTCUTS_VOCAB`, not in `COMPOUND_METRICS`.
5. **PIT visibility**: Three Neo4j stores carry source-PIT-anchored visibility fields with MIN-on-MATCH backdate per L6:
   - `Driver.registry_visible_at` (per E5 + R11)
   - `:VocabToken{..., vocab_visible_at}` (per E10 + v9-1 + v10-1)
   - `:EquivalenceToken{..., equivalence_visible_at}` (per E27 + v4-7 + v10-2)
6. **`validation_status` is DROPPED**: per E2 / OQ1, the field is removed from `Driver` schema. All registered drivers are reusable. Do NOT reintroduce.
7. **No human curator** (L4): All ontology mechanisms must be runtime-deterministic. The `COLD_START_SEED_DRIVERS` Python constant + bootstrap-seed semantics replace any "curator" / "human review" / "provisional → validated" language.

Read these files fully before drafting:
1. /home/faisal/EventMarketDB/.claude/plans/Drivers/DriverOntology.md
2. /home/faisal/EventMarketDB/.claude/plans/Drivers/DriverNameRisks.md
3. /home/faisal/EventMarketDB/.claude/plans/Drivers/Neo4jXBRLDesign.md
4. /home/faisal/EventMarketDB/.claude/plans/Drivers/ConceptualRequirements.md
5. /home/faisal/EventMarketDB/.claude/plans/Drivers/CombinedPlan.md (NEW — operational source of truth post-v10 fold; E26–E30 are the locked Tier-6 entries that supersede the pre-v6 design)
6. /home/faisal/EventMarketDB/.claude/plans/Drivers/DriverOntology_Implementation.md (NEW — §F.1 vocab seeds + §J.1 Mirror Map + §J.2 Cold-start seed clause; the post-v10 canonicalize() reference implementation)

Goal: produce a complete proposed replacement for DriverOntology.md: one concise, deduplicated, deterministic rulebook that any weaker LLM can follow to reuse or create driver names across any producer type: news, learning, fiscal/KPI, or future sources. (Note: the predictor is consumer-only and does NOT emit canonical drivers — its `prediction/result.json` §7 `key_drivers[]` stays as free-form analysis prose. The ontology applies only to actual producers.)

Success contract:
Given the same evidence, PIT-visible Driver registry catalog, aliases, allowed_states, and reference banks, two independent LLMs must return the same existing driver_name, the same valid new-driver proposal, or the same deterministic rejection/omission reason. There is no human curator and no manual review. Fuzzy matching and embeddings never DECIDE a name or fold (canonicalize() stays pure code); an embedding search is permitted only as a PIT-filtered trigger that routes borderline cases to an isolated structured judge whose verdict is persisted and replayed deterministically by code, so the two-LLM-agreement guarantee holds against the frozen vocab snapshot.

Hard constraints:
- Do not modify DriverOntology.md, DriverNameRisks.md, Neo4jXBRLDesign.md, or ConceptualRequirements.md.
- Show the full proposed replacement in chat and wait for explicit user approval.
- Do not introduce new Driver, DriverChange, output, or proposal fields.
- Do not introduce propose_new_tokens[], propose_lexicon_extension[], or any token-only proposal path.
- Use only fields allowed by Neo4jXBRLDesign.md, including propose_new_drivers[] fields: name, label, base_label, segment, definition, allowed_states, aliases, `is_shortcut` (bool DEFAULT false; set `true` only for standalone-shortcut Drivers per Pattern B + R5 + the ≥2-token gate).
- Do not add driver categories, level fields, macro/sector/company buckets, confidence fields, magnitude fields, triggerability fields, or usage-scope fields.
- Do not change PIT, registry_visible_at, source_id, Driver, DriverChange, supersession, validation_status, or direction semantics.
- Do not rely on validation_status, provisional status, human review, curator review, or later cleanup to make a bad name safe.
- Do not use semantic similarity, fuzzy matching, embeddings, nearest-neighbor logic, closest-match language, or open-ended "same meaning" judgment **to DECIDE a driver name, fold equality, or auto-reject**. NARROW CARVE-OUT (execution layer, not this ontology contract): an embedding/top-K similarity search MAY be used as a PIT-filtered TRIGGER ONLY (only drivers with registry_visible_at <= run.pit_cutoff; never decides equality, never auto-rejects) to flag a near-duplicate that did NOT fold mechanically, which then routes to an isolated, structured, temperature-0 judge whose verdict is CACHED/PERSISTED (decide-once, replay-by-code). canonicalize() and the deterministic fold/grammar checks remain pure code and unchanged.
- Do not preserve conflicting or duplicate source rules. Resolve each conflict into one final rule or drop it with a reason.

Use DriverNameRisks.md as the acceptance test:
- Every non-duplicate atomic risk must be prevented by one primary clause: an algorithm step, grammar rule, reference bank, validator rule, or output contract.
- Merge duplicate risks across overlapping sections, but list all covered risk IDs/names in the coverage row.
- Assess coverage against the DEDUPED/canonical risk view, not the raw file. Per DriverNameRisks.md's own banner, the raw file is FOUR overlapping, un-deduplicated taxonomies, so a literal "100% coverage against it" is mathematically ambiguous. Therefore map each merged risk GROUP to its strongest preventing clause. Any genuinely uncovered risk must be DECLARED — deferred, or judge-domain per the LLM-vs-code boundary — not asserted as covered. Every merged risk group must be addressed-or-declared before showing the proposal.

Rewrite principles:
1. One Source Of Truth
   Collapse all overlapping drafts in DriverOntology.md into one ordered rule system with one ID space. Remove duplicate ID schemes, repeated examples, legacy analysis, broad claims, and non-operational prose.

2. Algorithm Before Rules
   Start with one numbered authoring algorithm. The LLM follows steps in order. Each step must have Action, Pass condition, Fail condition, and Next step. No step may ask the LLM to weigh, judge, prefer, choose the best, or use discretion.

3. Registry Reuse Before Creation
   Before proposing a new driver, check exact Driver.name, exact aliases, approved synonym/plural/acronym maps, canonical token order, and deterministic sorted-token comparison for known tokens only. If any check maps to one existing Driver, reuse that Driver.name exactly. If checks map to multiple Drivers or none, follow the deterministic rejection/proposal path; do not guess.

4. Closed Vocabulary Before Open Language
   Existing-driver reuse must use only registry tokens, aliases, approved maps, approved standalone shortcuts, and approved state verbs. A brand-new token may appear only inside an otherwise valid propose_new_drivers[] entry, never in a separate token-proposal field. The ontology must define a deterministic new-token gate: exact shape pass, no banned content, slot fixed by the name grammar, no exact conflict with existing names/aliases/maps, and same-emission evidence required.

5. Field Separation Is Mandatory
   driver_name contains only the reusable causal noun variable.
   driver_state contains what happened to that variable.
   direction contains stock impact for the affected company: long or short only.
   evidence/source metadata contains quotes, SRC IDs, event IDs, source IDs, dates, magnitudes, provider names, and raw wording.
   aliases contain exact naming variants of the same Driver only.
   label is display text for name and must not add, drop, or reorder concept tokens relative to name.
   segment/base_label support XBRL/member resolution when applicable and must not contradict name.

6. Construction Before Prohibition
   Convert "do not include X" rules into positive placement rules whenever possible. Example: "state verbs go in driver_state" is stronger than only "do not put state verbs in driver_name". Keep negative rules only as validator checks.

7. Deterministic Name Grammar
   Define one canonical slug grammar, one token order, one max-token rule, one compound-metric rule, and one standalone shortcut rule. The grammar must be compact and code-checkable. It must not create 5+ token names unless the ontology explicitly treats a compound metric as one logical metric.

8. Exact Canonicalization Only
   Define canonicalize(candidate) as a pure function:
   - verify lower_snake_case ASCII shape or return rejection
   - split on underscores
   - normalize each token through approved acronym, plural, and synonym maps
   - classify existing tokens only through approved banks and tokens already present in registry names/aliases
   - apply standalone shortcut rule
   - reorder tokens using the fixed grammar
   - return canonical slug or structured rejection reason
   A reused driver is invalid if canonicalize(name) != name. A new proposal with a previously unseen token must pass the new-token gate before canonicalize(name) may treat that token as a literal token in its grammar slot.

9. New Driver Gate
   A new driver may be proposed only when all are true:
   - no existing Driver.name or alias matches after canonicalization
   - name passes every validator rule
   - current evidence directly supports the causal variable
   - the same emission also uses this driver_name in a DriverChange/key-driver item with non-empty evidence refs
   - the driver is reusable beyond one event, company-quarter, headline, vendor row, or raw source phrase
   - allowed_states are selected only from approved state verbs and are valid for this driver
   - aliases are exact variants of the same concept and pass alias rules

10. Plain-Language Determinism
   Define every technical term in simple words. Do not use vague terms such as appropriate, reasonable, similar, usually, generally, broadly, best, may depend, prefer, or closest. Replace them with exact checks.

11. Validator-Algorithm Dedup
   If a Section H validator V re-checks anything a Section D algorithm step already gates, DELETE V. Validators are the LAST line of defense for things the algorithm cannot catch (e.g. aliases bridging unrelated causal variables). They are NOT a restatement of the algorithm.

12. Examples Budget
   Examples are FORBIDDEN in every section except Section I. Section I is optional and has a hard cap of 5 examples — one per distinct risk class only when the example removes ambiguity that the rule text cannot remove more cleanly. Every example must cite the algorithm step or validator rule that decides it. Examples are NEVER hidden rules; they only illustrate already-decided rules. If a rule plus reference bank decides a case without an example, no example is added.

Required proposed DriverOntology.md structure:

Section A - Purpose And Success Contract
One short paragraph defining the file as the deterministic naming contract for Driver registry names.

Section B - Glossary
Simple definitions for driver, driver_name, slug, alias, registry, driver_state, direction, evidence, base_label, segment, allowed_states, and canonicalize.

Section C - Input And Output Contract
List allowed input context and only allowed output fields. State that unknown/new tokens are handled only through valid propose_new_drivers[] entries, never token-only proposals.

Section D - Authoring Algorithm
Numbered execution steps. Each step must include Action | Pass condition | Fail condition | Next step. Cover evidence extraction, registry reuse, alias reuse, normalization, canonicalization, new proposal, and rejection/omission.

Section E - Field Separation
A compact table showing what belongs in driver_name, driver_state, direction, evidence/source metadata, aliases, label, segment, base_label, definition, and allowed_states.

Section F - Canonical Name Grammar
Exact slug shape, max-token rule, token order, compound-metric rule, standalone shortcut rule, new-token gate, and canonicalize() pseudocode. Specify grammar in terms of token slots only. The grammar must enumerate the allowed shape patterns needed by the source files without naming specific exemplar drivers. The grammar itself must determine the output; named exemplars belong only in Section I if at all.

Section G - Reference Banks
Minimal seed banks using only necessary normalizations from the source files:
- standalone shortcut names
- synonym map
- plural map
- acronym map
- approved state verbs
Banks are append-only and exact-match only. Do not invent a large taxonomy.

Section H - Consolidated Validator Rules
One sequential ID space only: V1, V2, V3...
Each row must use this format:
ID | Owner field | Check | Rejection reason
Every rule must be code-checkable. Delete any rule that duplicates a clearer algorithm step, grammar clause, reference bank, or output contract. Pass condition is implicit (inverse of Rejection reason). Bad-example and correct-handling columns are forbidden here — examples live only in Section I subject to the Examples Budget rule.

Section I - Examples
Optional bad-to-good example set, maximum 5 rows. Include an example only if it clarifies a distinct ambiguity not already clear from Sections B-H. Every example must cite the rule/step that decides it. Do not use examples as hidden rules.

Sections J and K are INTERNAL acceptance artifacts — execute privately to validate coverage, but do NOT include them in the final DriverOntology.md output. The output file contains only Sections A–I.

(Internal-only) Risk Coverage Index
Map every merged risk group from DriverNameRisks.md to the single strongest preventing clause. The risk column must list all covered source IDs/names from the risk file. Coverage is assessed against the DEDUPED/canonical risk view: per DriverNameRisks.md's own banner the raw file is FOUR overlapping, un-deduplicated taxonomies, so a literal "100% coverage / zero uncovered risks" against it is mathematically ambiguous. Each merged risk group maps to its strongest preventing clause; any genuinely uncovered risk must be DECLARED — deferred, or judge-domain per the LLM-vs-code boundary — not asserted as covered. Every merged risk group is addressed-or-declared.

(Internal-only) Source Consolidation Notes
One short table listing source material that was merged, dropped, or rewritten, with one-line reasons. Drop duplicates, human-review language, vague advice, fields not allowed by Neo4jXBRLDesign.md, and token-only proposal paths.

Internal mental walkthrough (do NOT appear in the final output file):
Pick 10 diverse candidate phrasings yourself. At least 3 of the 10 MUST be adversarial edge cases drawn from distinct risk groups in DriverNameRisks.md (e.g., one duplication-variant case, one state-in-name case, one companion-metadata case). The remaining 7 may mix clean and ambiguous phrasings. Run the algorithm mentally for each. Confirm each yields exactly ONE deterministic output: either registry reuse of an existing driver_name, a valid propose_new_drivers[] entry, or an explicit deterministic rejection reason. If ANY produces ambiguity or two plausible answers, revise the ontology before showing the proposal.

Final checks before showing the proposal:
- In the internal Risk Coverage Index, every merged risk GROUP from DriverNameRisks.md is addressed-or-declared. Coverage is assessed against the DEDUPED/canonical risk view: per DriverNameRisks.md's own banner the raw file is FOUR overlapping, un-deduplicated taxonomies, so a literal "100% coverage / zero uncovered risks" against it is mathematically ambiguous. Each merged group maps to its strongest preventing clause; any genuinely uncovered risk must be DECLARED — deferred, or judge-domain per the LLM-vs-code boundary — not asserted as 100% covered.
- Every final rule has one owner section and is not duplicated elsewhere.
- No final rule uses vague or subjective wording.
- No final rule depends on human review, curation, provisional review, or future cleanup.
- No final rule introduces fields outside Neo4jXBRLDesign.md.
- No final rule changes PIT or graph semantics.
- Every concrete bad example in DriverNameRisks.md either maps to the expected canonical name or returns a deterministic rejection reason.
- Every propose_new_drivers[] entry is tied to same-emission evidence.
- aliases never bridge two different causal variables.
- allowed_states are verbs and are valid for the driver.
- label, definition, base_label, segment, and aliases cannot contradict name.
- The 10 self-picked mental walkthrough scenarios each yield exactly one deterministic output.
- Section I contains 0-5 examples, only where needed, one per distinct risk class, each citing the rule it illustrates.
- Section H contains no rule that re-checks something the algorithm already gates.

Output only:

A. Full proposed replacement content for DriverOntology.md, including Sections A–I only. Sections J and K stay internal and are not in the output file.
B. Final acceptance-check results, PASS/FAIL only with one-line fixes already applied.
C. Truly blocking open questions, only if a deterministic decision is impossible from the source files.

Do not write any file. Wait for explicit approval before any edit.
