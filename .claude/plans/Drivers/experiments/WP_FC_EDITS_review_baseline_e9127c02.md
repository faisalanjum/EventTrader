# WP-FC-EDITS — Fable pre-edit baseline inventory + review checklist

Purpose: the design-compliance review instrument for Opus's WP-FC-EDITS diff (WorkOrder v1.8 §2.3, 11 items).
Prepared by Fable 2026-07-10, BEFORE any edit landed.

## Baseline facts (verified first-hand)
- Baseline commit: e9127c02759eb8540261e54aaad96e89d59b3809 (= repo HEAD at prep time; 2026-07-09 20:17:33 -0400).
- No commits after baseline touch `.claude/plans/Drivers/workflows/`.
- Live worktree byte-identical to baseline for ALL 34 workflow files (sha256 per file; verified after fixing a CRLF artifact in the first extraction — extract with `-c core.autocrlf=false`).
- Work order at baseline == v1.8 exactly (blob sha256 `1586761a4756...8501` — matches the pinned workorder_sha256).
- Byte-true baseline snapshot: scratchpad `baseline/.claude/plans/Drivers/workflows/` (git-archive of e9127c02, autocrlf=false).

## The 3 pre-edit Fable rulings (2026-07-10, recorded on WORKORDER_STATUS board)
1. **OD-3 source**: inline NAME-01…19 from `02_DriverCatalog.md` VERBATIM (rule text + pins/carve-outs/examples; drop Plain/Why/Source/Replaces scaffolding + HTML comment). The "OD-3 local-role rule" IS NAME-10 + NAME-11 (+ NAME-16 #10/#11 carve-outs) — verified: 66 §0.R RES·OD-3's decision + customer pin + vendor pin are all inside NAME-10/11; 95 #1 names NAME-10/OD-3/#38 as one lineage. NO splicing from 66/95 (ledgers, not prompt sources; DU-07 no-added-clauses). The 66-only sentence "never rewrite an exception name to its bare fragment" is enforced by NAME-16 #11 + the gate's rewrite-must-target-an-existing-coined-name rule — no extra prose needed. If Opus finds a load-bearing clause genuinely missing from 02 → STOP + ra_*, never author prompt prose from ledgers.
2. **MODELS + effort**: one args-overridable `MODELS` block per touched workflow; slot = role → {model alias, effort}. Defaults: reader = 'sonnet' (placeholder; WP-FC-RUN MUST pass EXP-2's adopted (model, effort) pair explicitly); judges (dedup/gate/refute incl. high-blast refute2/d5/repair pair-judge) = 'sonnet' @ effort='high'; clerks/util Bash-relay agents = 'sonnet' @ default effort (NOT opus — escalation is never a default per §1.3; NOT haiku — unvalidated + PIPE-31 relay caveat). Opus available via args only. Aliases in source; exact resolved model ids + effort recorded per run (manifest models map — PIPE-15/PIPE-32). Rationale for effort=high on judges: EXP-0 qualified the grader tier as the (model, effort) PAIR and proved verdicts shift with effort; engine identity judges adopt the only measured-safe execution point as default. This is a default, not a re-qualification; no bar changes.
3. **Fold-test coupling**: leaf-owned tests — old fields removed COMPLETELY (fixtures + assertions; deleting `test_first_xbrl_wins` sanctioned — its sole subject is the deleted path). Fold-owned tests (`test_validate_fold`, `test_fold_catalogs`, `test_fold_repair_review`) — drop fixture noise only where tests stay green against UNTOUCHED fold code; the 2 optional_links-conflict tests (test_fold_catalogs.py:456-477) may be DELETED (subject = retired field; pack §4 marks them) or kept intact on old fixtures — one policy, stated in the diff note; reverting a fixture edit that breaks a fold test is acceptable but every revert is RECORDED as residue for Track A's full PIPE-21 sweep; NEVER edit fold/tree code; never weaken a non-optional_links assertion; unresolvable → ra_* + STOP. Suite ends green; report the count delta vs the 261+1skip baseline line-item.

## Per-file checklist (baseline line anchors; verify each in the diff)

### 1. menu_build.js (169 ln)
MUST change:
- :29 `required` + :30 properties — drop `xbrl_or_null` from MENU_SCHEMA (keep schema null-tolerant — footgun 18; string-typed w/ "" conventions is the current contract).
- :40-47 RULES block → inlined 02 NAME-01…19 verbatim (kills :40 DriverOntology authority + :44 brand line).
- :142 prompt field list — drop `xbrl_or_null ("null" if none obvious)`.
- :144 `model:'fable'` → MODELS.reader.
- :79/:101/:109/:120/:157/:167 `model:'opus'` (resolve/fetch/chunk/resume-plan/build-seed/record clerks) → MODELS.clerks.
- Record-step manifest.json gains the resolved models(+effort) map.
MUST NOT change: :75 billing guard · :50 args shim · §8.7a fail-close (:145-148) · --expect/h32 relay discipline · A1/A2 notes.

### 2. build_seed.py (143 ln)
MUST change: :12 docstring line · :75-76 optional_links init (record literal :73-76) · :87-89 first-xbrl copy · :96 emit — ALL FOUR sites (§2.3's ":75-89" under-covers; :96 + :12 are extra) · delete :116-118 dead no-op loop ONLY (:115 `per_ticker = {}` is LIVE — used at :120-125).
MUST NOT: recall-floor ADD (Track A 10 §9 step 5, not this batch) · Stage-0 #2 coverage check · --expect logic.

### 3. resume_menus.py (191 ln)
MUST change: :35-36 CANDIDATE_FIELDS drops "xbrl_or_null" · docstring "all six string fields" → five (~:43-44). :63 loop adapts automatically via the tuple.
MUST NOT: fail-close menu_valid logic, verify_run import/behavior.

### 4. reconcile.js (299 ln)
MUST change:
- :15 ONT const → inlined 02 rules block (also :3 meta "per DriverOntology" wording).
- :80 dedup prompt — record-shape string drops `optional_links`; ONT swap.
- :84 "NEVER link names with different scopes, brands, segments, geographies, ..." — delete brand/segment/geography as separators (own-part = slice, PIPE-17/19); KEEP object/metric/mechanism rejection.
- :86 "(shortest standard form, R6 ...)" — stale DriverOntology rule id → NAME-06/08 wording.
- :88-97 gate prompt — ONT swap; :90 "(Brand/segment-specific names ARE valid drivers — admit them.)" delete; :96 "KEEP brand/segment-specific names" delete.
- :104 refute — "Different brand/segment vs company-wide → FALSE" → PIPE-19 scope lens (scope = cause's business population; own measured parts are slices, not separators; external causes separate).
- MF-02 inline into dedup + gate + refute prompts, §2.3 item-4 wording verbatim: "different flavors of one topic — base vs `_guidance` vs `_surprise` — are NEVER the same driver; never SAME_AS, never a cross-flavor rewrite target".
- :219 + :224 D5 prompts ("per DriverOntology") + :249 mini-gate "Read ONT" — rulebook swap.
- Judge pins → MODELS slots: :87 dedup · :97 gate · :109 refute · :158 refute2(high-blast→refute slot) · :227/:236/:243/:249 D5 quartet (d5 slot; mini-gate may map to gate — coherent mapping required). Clerk pins :51/:61/:142/:198/:289/:296 → MODELS.clerks.
MUST NOT: EXACT_MEANING_RULE default-refuse semantics (:16-22; :40-41 survives definitions) · h32/expect · blast-count relay integrity · D5 ref_idx/truncation rules · validator invocation. Do NOT import EXP-0's "unclear means conflict" pin into engine prompts (ra_0007's kernel-§6.1 review is a separate later gate, pre-K-pairs.v2).

### 5. gate.js (38 ln)
MUST change: ADD step-0 billing guard (menu_build :75 pattern — gate has NONE) · ADD args parse shim (has NONE — footgun 8) · ADD MODELS.gate (agent call :37 pins NOTHING) · :7 ONT + :28 "Read ${ONT}" → inlined 02 block · :32 "brand/segment metric is NOT the same..." + :33 "(Brand/segment-specific names ARE valid drivers — admit them.)" → NAME-10/11-consistent text (doc 10 §3 cites gate.js:32-33 as the pair) · :3 meta "per DriverOntology" wording.
MUST NOT: GATE_SCHEMA enums · fail-closed candidates guard (:11) · reuse/admit/rewrite/skip semantics beyond the brand fix.

### 6. assemble_catalog.py (520 ln)
MUST change: :104 ALL_NULL_LINKS constant deleted · :236 · :410 stop emitting `optional_links`. (Grep-verified: only these 3 sites.)
MUST NOT: 5-way precedence, STAR-flatten, D5 apply, --expect/h32.

### 7. repair_duplicates.py (555 ln)
MUST change: min_score 0.72→0.60 at :82, :110, **:150 (suggest() kwarg — MISSED by §2.3's list)**, :491 (CLI) · embeddings default ON (:489 `--use-embeddings` store_true + :150 `use_embeddings=False`; needs an off-switch, e.g. BooleanOptionalAction — py3.10 OK) · suggest limit default → 0 (:149 kwarg 2000 + :487 CLI 2000; :187 already treats <=0 as NO CAP).
MUST NOT: suggester channels, C5 plan/canary/apply, sidecar binding (require_validated), h32s.
Hazard: tests calling suggest() bare (or CLI without flags) now get embeddings=ON → NO test may hit the network; tests pass explicit False/stub; test_stage0_hardening.py:794 asserts use_embeddings False → lockstep update.

### 8. repair_duplicates.js (308 ln)
MUST change: all 16 `model:'opus'` pins (:83,:86,:88,:114,:127,:150,:158,:181,:190,:213,:240,:249,:294,:299,:305) → MODELS slots (pair-judge/refute2 = judge-role @ high; suggest/plan/show/apply/validate relays = clerks) · MF-02 into the pair-judge prompt **IN LOCKSTEP with ab_pair_judge.js** (test_repair_duplicates asserts prompt byte-identity between the two — both change identically or that test breaks) · verify the js→py call-site flags now yield effective {limit 0, embeddings ON, 0.60} for WP-FC-RUN.
MUST NOT: batched-lane AND-gate, 2% canary, fold-parent --review block.

### 9. ab_pair_judge.js (78 ln) — LOCKSTEP-ONLY touch
The shared pair-judge prompt block gains MF-02 identically (byte-identity with repair_duplicates.js preserved). Nothing else (its :48/:58/:74 pins may optionally become slots; not required this batch).

### 10. chunk_company_sources.py (233 ln)
MUST change: ADD `--budget-chars` as an ALIAS of the existing `--budget` (:222; capability already exists — §2.3 wants the exact spelling; EXP-2's rechunk will call `--budget-chars 8000`). Default 40000 unchanged; `--budget` keeps working (tests :137/:143/:151 use it).
MUST NOT: ladder, conservation proof, EX-99.1-iff-earnings.

### 11. resolve_driver_scope.py (74 ln)
MUST change: ADD `--exclude T1,T2` (industry mode; normalize/uppercase; subtract from tickers BEFORE payload/scope-file write — Stage-0 #8 code-to-code; 0-remaining → hard-error; excluded list echoed in payload for provenance).
MUST NOT: URI fallback (:21 — footgun 16 noted, out of scope) · --list/--sector modes.

### 12. tests/ (lockstep)
- test_build_seed.py — :25 cand() xbrl kwarg/default; :59-65 `test_first_xbrl_wins` DELETE.
- test_slice_seed.py — :31 fixture noise.
- test_assemble_catalog.py — :9 docstring, :38, :150 (assertion → absence-of-field), :211, :271.
- test_validate_catalog_d1.py — :30, :145.
- test_repair_duplicates.py — :25 fixture; embeddings/limit spots :190/:207/:419/:435 as needed (hermetic!).
- test_resume_menus.py — :39, :92, :94, :212, :225-231 (xbrl-validity assertion), :230, :239, :270.
- test_stage0_hardening.py — :55, :423 fixtures; :794 use_embeddings assertion.
- Fold tests per ruling 3: test_validate_fold :34 · test_fold_catalogs :40-46 rec() (+ :332/:378 keep-if-green) · :456-477 two conflict tests delete-or-keep · test_fold_repair_review :31-35.
- New tests for --budget-chars/--exclude: welcome, in scope.

### 13. MUST NOT TOUCH (byte-identical to baseline in the diff)
fold_catalogs.py · fold_catalogs.js · build_tree.js · catalog_first.js · rescue_review.py · fetch_company_sources.py · slice_seed.py · ab_stratum.py · ab_differ.py · test_ab_differ.py · test_ab_stratum.py · test_chunk_company_sources.py (unless adding --budget-chars tests) · validate_catalog.py LOGIC (:8 stale docstring one-liner tolerated if touched, nothing else).

## Review procedure when the diff lands
1. `git diff e9127c02..<new>` — file list must ⊆ {items 1-12 above (+ ab_pair_judge prompt block)}; fold/tree/dead files byte-identical (sha check).
2. Re-grep the edited tree: `xbrl_or_null|optional_links|DriverOntology|model:'fable'|0\.72` → hits ONLY in untouched fold/tree/dead files (+ validate docstring if left).
3. Diff the inlined RULES block against 02 NAME-01…19 rule text — verbatim (rule text + pins/examples; scaffolding dropped; nothing added — DU-07).
4. MF-02 wording == §2.3 item 4 verbatim; present in dedup/gate/refute + the shared pair-judge prompt; byte-identity test green.
5. MODELS defaults == ruling 2 (sonnet everywhere; judges effort=high; no opus/haiku defaults; no dated model ids in source); resolved ids+effort recorded per run.
6. Billing guards: gate.js gained one; menu_build/reconcile/repair kept theirs; NO new gaps.
7. Suite: green on server; count delta vs 261+1skip line-itemized (expected: −1 first_xbrl_wins, −0..2 fold conflict tests, +N new flag tests); prompt-mirror tests absent → note in status, not a blocker.
8. Null-tolerance regression check on MENU_SCHEMA (footgun 18).
