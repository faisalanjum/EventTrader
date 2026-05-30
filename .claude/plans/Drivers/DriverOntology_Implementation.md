# Driver Naming — Implementation & Enforcement

This file owns the executable mechanism behind `DriverOntology.md`. It contains the authoring algorithm, `canonicalize()` pseudocode, regex, vocab seeds, validator table, numerical thresholds, the Conformance Index that maps each ontology rule to its enforcing clauses, and the rev-trigger reference.

This file may evolve independently of `DriverOntology.md`. Vocab growth, regex tweaks, validator refactors, threshold tuning, and helper additions do NOT require an ontology rev. Only semantic changes (new slot type, new rule concept, new banned category, new output field, semantic flip of an existing rule) touch the ontology.

The LLM at runtime never sees this file. It sees `DriverOntology.md` + the §A runtime envelope.

---

## ⚖️ LLM-vs-CODE BOUNDARY — architecture principle (owner, 2026-05-29; REVISIT on the triggers below)

**Principle:** do NOT use deterministic code where an LLM is more accurate. **LLM = semantic judgment** (meaning ·
novelty · ambiguity); **CODE = mechanical consistency** (exact-match · format · slot ORDER · length · validators ·
the deterministic fold — $0, reproducible, can't fragment the graph). The whole architecture = *"LLM decides meaning,
code guarantees consistency."*

- **Correctly LLM-led (do NOT code-ify):** reuse-from-catalog · the 4 judgment risks K23/K30/K47/K52 · R9 granularity · Pass-4 accuracy.
- **Correctly code:** canonicalize formatting · exact-match vocab folds (§F.2–F.4) · slot order (§D.1) · length (§G) · validators V1–V14 (§E).
- **🟡 3 watch-spots (code may over-step into meaning) — each with a REVISIT TRIGGER:**
  1. **New-word SLOT placement** — `resolve_unknown_slots` (§D.1) rejects an ambiguous novel token (`blackwell_revenue`→`slot_ambiguous`, the Option-A call). **REVISIT IF** Pass-4 shows false-rejects of legit new drivers → move the slot call to the **LLM (producer DECLARES the slot in `propose_new`)**; code = deterministic backstop, not the judge.
  2. **Synonym DISCOVERY** (`uptake≈demand`) — must come from an LLM-shaped signal (the caller supplies `to_token`); code = the N=2 gate + fold ONLY (§F.10 Pattern A2). **REVISIT IF** any candidate gets code-guessed.
  3. **Banned-word completeness** (§F.7) — novel metaphor/sentiment can't be exhaustively listed → the **LLM (taught R7 at proposal) is the real defense**, the list is a backstop. **REVISIT IF** Pass-4 shows banned words leaking.

**Recommended flow** (refined 2026-05-29): LLM emits → code dry-run validates → same-learner **self-correct loop** (§J Lever #3 — the PRIMARY recovery path; Pattern A = the producer (learner) self-corrects WITHIN ITS OWN session: after drafting driver tags it calls a deterministic validate tool (`driver_write_cli.py --dry-run` = canonicalize + validators), reads the exact per-tag rejection reasons, fixes ONLY the flagged tags, and re-validates — looping AT MOST 2-3 times, stopping if a rejection repeats (no progress), never contorting a name just to pass (drop+note instead); the orchestrator's write-path validation is the NON-NEGOTIABLE external authority/gate that re-validates before MERGE and the learner cannot bypass it; cost $0 — extra in-session turns on interactive OAuth, SDK / `claude -p` stay forbidden/metered) → orchestrator code re-validates at the write gate → optional isolated, persisted, gated LLM judge for borderline/global/irreversible cases → code writes/folds deterministically. Deterministic Lever #1 auto-repair is DEMOTED below the self-correct loop (see §J). **6 LLM-judgment uses:** informed-retry · semantic-reuse · synonym-discovery · new-token slot-declaration · evidence-SUPPORT · scope/granularity. (Keep code for identity/gates/graph-safety — the compiler half.)
**Canonical:** memory `feedback_llm_vs_code_boundary.md` (full refined list). Mirrored in `Harness_BuilderPrompt.md` + `TESTER_HANDOFF.md`.

**Governing rule (canonical one-liner):** Producer LLM handles semantics first. Isolated judge handles borderline/global/irreversible cases. Code persists, gates, and replays decisions deterministically. Gate strength scales with blast radius × irreversibility.

---

## §A. Runtime Inputs (rendered into the LLM prompt)

Once per predictor/learner session (bundle context built at /run-prediction or /run-learning entry) OR once per `/extract` worker invocation (Phase 2 news), the orchestrator injects into the LLM prompt (per CombinedPlan E4 — NOT per emission; the LLM authors all of its driver tags within a single session, so the prompt cost is amortized once):

1. `DriverOntology.md` (static).
2. A PIT-visible Driver registry catalog excerpt — per Driver: `name`, `aliases[]`, `segment`, `allowed_states[]`, `definition`.
3. The current vocab excerpt — §F entries.
4. The current numerical thresholds — §G values.
5. The evidence text.

The runtime vocab MUST have a non-empty list for every banned-content category named in ontology R7 (state verbs and verb-derived forms, direction/polarity words, motion or change nouns, identity tokens, period tokens, numeric or qualitative magnitudes, source-type labels, provider labels, XBRL prefixes, metaphors, sentiment adjectives, effect-on-stock words, vague descriptors, stopwords). An empty list for any category is a configuration error and fails the runtime conformance check; no candidate is allowed to bypass R7 because of an empty category list.

---

## §B. Authoring Algorithm

Execute steps in numbered order per causal variable in evidence. Each step has Action / Pass / Fail / Next.

**B1. Extract.**
- Action: split evidence into `(noun_phrase, state_verb, direction, evidence_refs[])` where `noun_phrase` is the reusable causal variable. `noun_phrase` MUST exclude every token that ontology §3 places in another field. When evidence contains two or more independent causal variables, emit a separate driver tag per variable; never bundle.
- Pass: all four fields non-empty.
- Fail: emit no driver tag for this evidence; STOP.
- Next: B2.

**B2. Slugify.**
- Action: `candidate_slug = slug(noun_phrase)` where `slug()` lowercases, replaces non-alphanumeric runs with `_`, strips edge `_`.
- Pass: matches §D shape regex and is non-empty.
- Fail: STOP with rejection `empty_or_invalid_slug`.
- Next: B3.

**B3. Exact name match.**
- Action: lookup registry for `Driver.name == candidate_slug`.
- Pass: exactly one match → emit tag with `driver_name = matched.name`; STOP.
- Fail: zero matches → B4.

**B4. Exact alias match.**
- Action: lookup registry for `candidate_slug ∈ Driver.aliases`.
- Pass: exactly one match → emit tag with `driver_name = matched.name`; orchestrator may append `candidate_slug` to that Driver's aliases; STOP.
- Fail: zero matches → B5.

**B5. Canonicalize.**
- Action: `canonical = canonicalize(candidate_slug)` per §C.
- Pass: returns a string → B6.
- Fail: structured rejection → STOP with that reason.

**B6. Exact name match on canonical.**
- Action: lookup registry for `Driver.name == canonical`.
- Pass: exactly one match → REUSE; STOP.
- Fail: B7.

**B7. Exact alias match on canonical.**
- Action: lookup registry for `canonical ∈ Driver.aliases`.
- Pass: exactly one match → REUSE; STOP.
- Fail: B8.

**B8. Sorted-token reuse (gated on all-known tokens).**
- Action: tokenize `canonical` on `_`. If EVERY token appears in some `Driver.name`, some `Driver.aliases`, or as a key/value in §F.2–F.4 maps, compute `sorted(tokens)` and compare to `sorted(tokens(Driver.name))` for every registry Driver. If any token is unknown, SKIP.
- Pass: exactly one Driver matches → REUSE; STOP.
- Fail: zero or multiple matches → B9.

**B9. Grammar + banned-content validation.**
- Action: run `canonical` through §D grammar, §D new-token gate (when unknown tokens present), and the §E validator set scoped to `name`.
- Pass: all checks pass → B10.
- Fail: STOP with the matching §E rejection reason.

**B10. New Driver Gate.**
- Action: verify all conditions of ontology R11 against §F (vocab) and §G (thresholds).
- Pass: emit `propose_new_drivers[]` entry + driver tag; STOP.
- Fail: STOP with the failing condition as rejection reason.

---

## §C. canonicalize() — Pure Function

**Per v3-1**: `canonicalize()` takes the vocab snapshot as a PARAMETER. NO Neo4j reads inside. Writer-bootstrap loads markdown seed + PIT-filtered Neo4j tokens (per E10 amended + E27 + v9-1 + v10-1 + v4-7 + v10-2) into an immutable `VocabSnapshot`. Same `(candidate, vocab_snapshot)` input → identical output on any machine, today or future.

```python
@dataclass(frozen=True)
class VocabSnapshot:
    synonym_map: dict[str, str]            # §F.2 markdown seed + promoted :EquivalenceToken{kind:synonym}
    plural_map: dict[str, str]             # §F.3 markdown seed + promoted :EquivalenceToken{kind:plural}
    acronym_map: dict[str, str]            # §F.4 markdown seed + promoted :EquivalenceToken{kind:acronym}
    shortcuts: set[str]                    # §F.1 SHORTCUTS_VOCAB markdown seed +
                                            # Driver.name where is_shortcut=true
                                            # (per v5-5 Pattern B: shortcuts live as :Driver rows;
                                            #  bootstrap query filters Driver registry by
                                            #  is_shortcut=true per v8-1 schema field +
                                            #  PIT-filtered by Driver.registry_visible_at
                                            #  per E5)
    slot_vocabs: dict[str, set[str]]       # §F.1 markdown seed +
                                            # :VocabToken (E10 amended + v9-1 + v10-1)
                                            # PIT-filtered by vocab_visible_at
    banned: set[str]                       # §F.7 markdown seed (bounded English vocab)
    stopwords: set[str]                    # §F.8 markdown seed
    states: set[str]                       # §F.5 markdown seed
    multi_token_subs: dict[str, str]       # §F.2 SYNONYM_MAP multi-token section
                                            # (e.g. data_center → datacenter,
                                            #  gross_profit → gross_margin).
                                            # NOT §F.6 — §F.6 COMPOUND_METRICS is a SET of
                                            # canonical metric NAMES used by the grammar
                                            # (line 236 BNF: <metric> ∈ METRICS ∪ COMPOUND_METRICS),
                                            # not substitutions. Field renamed from `compounds`
                                            # to fix the pre-fix mislabeling.
    compound_metrics: set[str]             # §F.6 COMPOUND_METRICS set — used by grammar
                                            # to classify multi-underscore tokens as a
                                            # single metric slot (R6).
    frozen_atoms: set[str]                 # v11-2 (2026-05-29) — DERIVED at build time by
                                            # build_vocab_snapshot/load_vocab_snapshot: every
                                            # MULTI-token known atom (contains "_") across
                                            # shortcuts ∪ compound_metrics ∪ slot_vocabs ∪ banned.
                                            # §C step 4.5 freezes these so a known multi-token OBJECT
                                            # (vision_pro / cloud_service) and a multi-token BANNED
                                            # phrase (us_gaap / person names / basis_points) survive
                                            # the tokenize-split intact. SINGLE-token entries are
                                            # EXCLUDED by construction — they need no freezing, and
                                            # excluding them guarantees no single-token fold is ever
                                            # suppressed.

def canonicalize(candidate: str, vocab: VocabSnapshot) -> str | REJECTION:
    # 1. shape gate
    if not match(candidate, SHAPE_REGEX):
        return REJECTION_INVALID_SLUG_SHAPE

    # 2. multi-token compound substitution (longest-match first)
    for k, v in sorted(vocab.multi_token_subs.items(), key=lambda kv: -len(kv[0])):
        candidate = candidate.replace(k, v)

    # 3. tokenize
    tokens = candidate.split('_')

    # 3.5 FREEZE known atoms (v11-1 idempotency + v11-2 multi-token + v11-3 BEFORE-stopword, 2026-05-29)
    #     — runs BEFORE the stopword strip so a known atom that CONTAINS a stopword (`cost_of_revenue`,
    #     `cost_of_goods_sold`, `sell_the_news`) is matched WHOLE before `of`/`the` is stripped. Rejoin
    #     any adjacent span forming a KNOWN MULTI-TOKEN atom (`vocab.frozen_atoms` = every "_"-containing
    #     entry across shortcuts §F.1 / compound_metrics §F.6 / slot_vocabs §F.1 / banned §F.7) into ONE
    #     atomic token; return those atoms as `frozen` so steps 4–5 leave them untouched. This (a) stops
    #     step-5 maps mangling a shortcut/compound FRAGMENT (`approval`→`approvals` in `fda_approval`;
    #     `margin`→`gross_margin` in `gross_margin`/`cloud_gross_margin`); (b) keeps a multi-token OBJECT
    #     whole so step 9 classifies it (`vision_pro`/`cloud_service` → object, NOT split→slot_ambiguous);
    #     (c) keeps a multi-token BANNED phrase whole so step 7 catches it (`us_gaap`/person-names/
    #     `basis_points` → banned_token, closes the K15 gap); (d) v11-3: protects interior-stopword
    #     compounds from the strip below. A bare token NOT itself a member (lone `margin`/`approval`) is
    #     NOT frozen, so its deliberate fold still fires at step 5. See §D.1 freeze_known_atoms.
    #     ⚠️ The SAME frozen-atom-aware tokenization MUST be reused wherever a name is re-split into
    #     tokens — §E V4 (segment), V14 (new-token gate), new-slot-token extraction — NEVER a raw
    #     `name.split('_')`, else a multi-token object/ban is mis-handled outside canonicalize.
    tokens, frozen = freeze_known_atoms(tokens, vocab.frozen_atoms)

    # 4. strip stopwords — but NEVER strip a frozen atom (its interior stopwords are protected inside
    #    the joined token, e.g. `cost_of_revenue` keeps its `of`).
    tokens = [t for t in tokens if t in frozen or t not in vocab.stopwords]
    if len(tokens) == 0:
        return REJECTION_EMPTY_AFTER_STOPWORD_STRIP

    # 5. per-token normalization (exact-match maps) — SKIP frozen shortcut/compound atoms
    normalized = []
    for t in tokens:
        if t in frozen:                    # already-canonical shortcut/compound atom — do not normalize
            normalized.append(t)
            continue
        n = vocab.acronym_map.get(t, t)    # §F.4 — markdown + promoted acronym
        n = vocab.plural_map.get(n, n)     # §F.3 — markdown + promoted plural
        n = vocab.synonym_map.get(n, n)    # §F.2 — markdown + promoted synonym
        normalized.append(n)

    # 6. de-duplicate after normalization
    seen, deduped = set(), []
    for t in normalized:
        if t not in seen:
            deduped.append(t)
            seen.add(t)
    normalized = deduped
    if len(normalized) == 0:
        return REJECTION_EMPTY_AFTER_DEDUP

    # 7. banned-content check
    for t in normalized:
        if t in vocab.banned:              # §F.7
            return REJECTION_BANNED_TOKEN(t)
        if t in vocab.states:              # §F.5 — verbs belong in driver_state
            return REJECTION_STATE_IN_NAME(t)

    # 8. standalone shortcut (R5 renamed from "macro shortcut" per E23 / OQ3)
    if '_'.join(normalized) in vocab.shortcuts:    # §F.1 SHORTCUTS_VOCAB +
                                                    # Driver.name where is_shortcut=true
        return '_'.join(normalized)

    # 8.5 compound-metric reassembly (R6): re-join adjacent tokens that form a §F.6
    #     COMPOUND_METRICS entry into ONE metric token, so a compound metric occupies a single
    #     metric slot (and is not split / collision-rejected at step 9.5/10). See §D.1.
    #     NOTE (v11-1): step 4.5 freeze_known_atoms already froze compounds present BEFORE
    #     normalization; this 8.5 pass remains to catch compounds that only become adjacent/canonical
    #     AFTER step-5 folds (e.g. a synonym maps a token onto a compound component). Idempotent on
    #     already-frozen atoms (re-running on a joined list is a no-op) → a safe belt-and-suspenders net.
    normalized = rejoin_compound_metrics(normalized, vocab.compound_metrics)

    # 9. classify each token into one slot (uses vocab.slot_vocabs per E10 + v9-1 + v10-1)
    classified = [(t, classify_token(t, vocab.slot_vocabs)) for t in normalized]

    # 9.5 resolve UNKNOWN-slot tokens by position (R11 new-token gate (c); fail closed — see §D.1)
    classified = resolve_unknown_slots(classified)
    if isinstance(classified, REJECTION):
        return classified

    # 10. reorder by SLOT_ORDER (theme → object → customer → geography → institution → metric)
    #     + reject two tokens classifying to the same slot (R3) — see §D.1 order_by_slot
    reordered = order_by_slot(classified)
    if isinstance(reordered, REJECTION):
        return reordered

    # 11. metric-presence + length bound
    if not any(slot == 'metric' for (_, slot) in reordered):
        return REJECTION_NO_METRIC_TOKEN
    if effective_slot_count(reordered) > MAX_EFFECTIVE_SLOTS:   # §G
        return REJECTION_TOO_MANY_SLOTS

    # 12. emit
    result = '_'.join(t for (t, _) in reordered)
    if not match(result, SHAPE_REGEX):
        return REJECTION_INVALID_POST_REORDER
    return result
```

**Writer-bootstrap loader (NEW per E27 + v9-1 + v10-1 + v4-7 + v10-2)** — produces the VocabSnapshot once per run, BEFORE any canonicalize() call:

```python
def load_vocab_snapshot(run_pit_cutoff: Optional[datetime]) -> VocabSnapshot:
    seed = load_markdown_seed()                       # §F.1-§F.9 static
    promoted_eq = neo4j.read("""
        MATCH (et:EquivalenceToken)
        WHERE et.status = "promoted"
          AND ($run_pit_cutoff IS NULL
               OR et.equivalence_visible_at <= datetime($run_pit_cutoff))
                  // ↑ v4-7 + v10-2: PIT filter uses observation_pit anchor,
                  //   NOT wall-clock promoted_at. Backdates on each new obs
                  //   per v10-2 MIN-on-each-obs CASE in Phase 1 SET.
        RETURN et.kind, et.from_token, et.to_token
    """, run_pit_cutoff=run_pit_cutoff)
    promoted_vocab = neo4j.read("""
        MATCH (vt:VocabToken)
        WHERE ($run_pit_cutoff IS NULL
               OR vt.vocab_visible_at <= datetime($run_pit_cutoff))
                  // ↑ v9-1 + v10-1: PIT filter parallel to v4-7.
                  //   vocab_visible_at = MIN-on-MATCH backdate per v10-1.
        RETURN vt.slot, vt.token
    """, run_pit_cutoff=run_pit_cutoff)
    shortcuts_from_drivers = neo4j.read("""
        MATCH (d:Driver)
        WHERE d.is_shortcut = true
          AND ($run_pit_cutoff IS NULL
               OR d.registry_visible_at <= datetime($run_pit_cutoff))
        RETURN d.name
    """, run_pit_cutoff=run_pit_cutoff)
    return VocabSnapshot(
        synonym_map      = merge(seed.synonym, {e.from_token: e.to_token for e in promoted_eq if e.kind == 'synonym'}),
        plural_map       = merge(seed.plural,  {e.from_token: e.to_token for e in promoted_eq if e.kind == 'plural'}),
        acronym_map      = merge(seed.acronym, {e.from_token: e.to_token for e in promoted_eq if e.kind == 'acronym'}),
        shortcuts        = seed.shortcuts | {r.name for r in shortcuts_from_drivers},
        slot_vocabs      = merge_slot_vocabs(seed.slots, promoted_vocab),
        banned           = seed.banned,
        stopwords        = seed.stopwords,
        states           = seed.states,
        multi_token_subs = seed.multi_token_subs,   # §F.2 SYNONYM_MAP multi-token section
        compound_metrics = seed.compound_metrics,   # §F.6 COMPOUND_METRICS set
        frozen_atoms     = {a for a in (
                               (seed.shortcuts | {r.name for r in shortcuts_from_drivers})
                               | seed.compound_metrics
                               | {tok for toks in merge_slot_vocabs(seed.slots, promoted_vocab).values() for tok in toks}
                               | seed.banned
                            ) if "_" in a},   # v11-2 DERIVED — every "_"-containing known atom
                                              # (mirrors §D.1 freeze_known_atoms; SINGLE-token entries excluded)
    )
```

A reused Driver is invalid if `canonicalize(name, vocab) != name`. A proposal with any UNKNOWN-slot token must pass the §D new-token gate before that token is treated as a literal in its grammar slot. All substring matches against evidence text in §D (e) are case-insensitive.

---

## §D. Slug Shape + Grammar + New-Token Gate

**Shape regex** (per CombinedPlan E7 — tightened to reject consecutive underscores; DriverOntology §2 bans `__` but the pre-E7 form `^[a-z][a-z0-9_]*[a-z0-9]$` allowed it):

```
^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$
```

Equivalent to: starts with a-z, contains a-z/0-9/single-underscore-not-followed-by-underscore, ends with a-z/0-9, length ≥ 2. Rejects `a__b`, `_foo`, `foo_`, `1foo`, `foo__bar`.

**Grammar (BNF)**:
```
name ::=  <standalone_shortcut>
       |  <metric>
       |  <subject> "_" <metric>
       |  <subject> "_" <geography> "_" <metric>
       |  <subject_A> "_" <subject_B> "_" <metric>
       |  <subject_A> "_" <subject_B> "_" <geography> "_" <metric>

<subject>     ∈ THEMES ∪ OBJECTS ∪ CUSTOMERS ∪ INSTITUTIONS
<geography>   ∈ GEOGRAPHIES
<metric>      ∈ METRICS ∪ COMPOUND_METRICS
```

**Slot order (immutable)**: theme → object → customer → geography → institution → metric.

**New-token gate** — a token that is not present in any registry `Driver.name`, any `Driver.aliases`, or any §F.1–F.5 entry MAY be introduced only inside an otherwise-valid `propose_new_drivers[]` entry, and only if ALL true:

- (a) token matches the shape regex above.
- (b) token is not in §F.7 BANNED_CONTENT (identity, period, numeric, source_type, provider, xbrl_prefix, metaphor, sentiment, effect, category, stopword).
- (c) token's slot is unambiguously determined by its position in the proposed `name` relative to known tokens and SLOT_ORDER.
- (d) token does not exactly equal any existing `Driver.name`, any `Driver.aliases` entry, or any key/value in §F.1–F.5.
- (e) the same emission's driver tag using this name has non-empty `evidence[]` AND the token appears as a case-insensitive substring of the joined evidence text.

---

## §D.1 Slot classification + ordering (mechanical spec for §C steps 9–11)

Per CombinedPlan **COV-1 / COV-2**: §C steps 9–11 call `classify_token()`, `order_by_slot()`, and
`effective_slot_count()`, and §D(c) above describes unknown-token slot inference in prose only. The
following pins all four to deterministic code so any two implementers produce identical output. These
are PURE functions over the `VocabSnapshot.slot_vocabs` — no Neo4j reads. Same input → identical
output on any machine (idempotent + order-independent).

```python
# Immutable canonical slot order (R3 / §D). Index = canonical position.
SLOT_ORDER = ('theme', 'object', 'customer', 'geography', 'institution', 'metric')
SLOT_INDEX = {slot: i for i, slot in enumerate(SLOT_ORDER)}
# slot_vocabs keys = the 6 SLOT_ORDER names. slot_vocabs['metric'] = METRICS ∪ COMPOUND_METRICS
# (per the §D BNF: <metric> ∈ METRICS ∪ COMPOUND_METRICS).

def classify_token(token: str, slot_vocabs: dict[str, set[str]]) -> str:
    """Return the token's slot, or 'UNKNOWN' if in no slot vocab.
    COV-2 fix: precedence walks the FIXED SLOT_ORDER, never dict-iteration order — this makes
    R3 'if a token classifies to more than one slot, the earlier slot wins' a SPEC RULE, not an
    implementation accident. Pure exact-match membership."""
    for slot in SLOT_ORDER:                                   # earliest slot wins (R3)
        if token in slot_vocabs.get(slot, frozenset()):       # exact-match membership
            return slot
    return 'UNKNOWN'

def resolve_unknown_slots(classified: list[tuple[str, str]]):
    """classified = [(token, slot|'UNKNOWN')] in the ORIGINAL token order. Assign each UNKNOWN
    token the UNIQUE SLOT_ORDER position strictly between its nearest known left/right neighbours
    (per §D new-token gate (c) / R11). Fail closed:
        all tokens UNKNOWN (no anchor)        → REJECTION_SLOT_ANCHOR_UNAVAILABLE
        0 or >1 free slot fits the gap        → REJECTION_SLOT_AMBIGUOUS(token)
    Deterministic + idempotent: left/right anchors are read from the ORIGINAL known slots; unknowns
    are filled left-to-right, each taking the lowest free slot in its open interval, so the output
    depends only on the input. Assumes the proposer placed the new token in canonical slot order
    (the LLM is taught R3); the TRUE semantic slot of a novel token remains LLM-judgment — this rule
    only mechanically PLACES it and rejects when placement is not unique (see Reliability Ledger)."""
    if all(slot == 'UNKNOWN' for (_, slot) in classified):
        return REJECTION_SLOT_ANCHOR_UNAVAILABLE
    resolved = list(classified)
    occupied = {s for (_, s) in classified if s != 'UNKNOWN'}
    for i, (tok, slot) in enumerate(classified):
        if slot != 'UNKNOWN':
            continue
        left  = max((SLOT_INDEX[s] for (_, s) in classified[:i]   if s != 'UNKNOWN'), default=-1)
        right = min((SLOT_INDEX[s] for (_, s) in classified[i+1:] if s != 'UNKNOWN'), default=len(SLOT_ORDER))
        free  = [idx for idx in range(left + 1, right) if SLOT_ORDER[idx] not in occupied]
        if len(free) != 1:                                    # 0 or >1 → reject, never guess
            return REJECTION_SLOT_AMBIGUOUS(tok)
        chosen = SLOT_ORDER[free[0]]
        resolved[i] = (tok, chosen)
        occupied.add(chosen)
    return resolved

def order_by_slot(classified: list[tuple[str, str]]):
    """Reorder to canonical SLOT_ORDER and enforce R3 'at most one token per slot'.
    Pre-condition: no UNKNOWN remains (resolve_unknown_slots ran first)."""
    slots = [s for (_, s) in classified]
    if len(set(slots)) != len(slots):                         # two tokens, same slot → R3 reject
        return REJECTION_SLOT_COLLISION(next(s for s in slots if slots.count(s) > 1))
    return sorted(classified, key=lambda ts: SLOT_INDEX[ts[1]])

def effective_slot_count(reordered: list[tuple[str, str]]) -> int:
    """Number of occupied slots, for the R8 length bound. A compound metric occupies the single
    'metric' slot, so it counts as one (R6) — guaranteed by rejoin_compound_metrics() below,
    invoked at §C step 8.5 before classification."""
    return len({slot for (_, slot) in reordered})

def freeze_known_atoms(tokens: list[str], frozen_atoms: set[str]) -> tuple[list[str], set[str]]:
    """v11-1 IDEMPOTENCY FIX + v11-2 MULTI-TOKEN SCOPE (2026-05-29) — invoked at §C step 4.5, BEFORE
    per-token normalization. `frozen_atoms` (VocabSnapshot field, assembled once at build) = every
    KNOWN MULTI-TOKEN atom (contains "_") across `shortcuts` (§F.1) ∪ `compound_metrics` (§F.6) ∪
    `slot_vocabs` (§F.1 — e.g. object `vision_pro`, `cloud_service`) ∪ `banned` (§F.7 — e.g. `us_gaap`,
    person names, `basis_points`). Rejoin any adjacent token span that forms one of these into ONE
    atomic token, and return the set of those atoms as `frozen` so §C step 5 skips them. This:
      (a) stops step-5 acronym/plural/synonym maps mangling a shortcut/compound FRAGMENT before
          step-8/8.5 protects it (`approval`->`approvals` in `fda_approval`; `margin`->`gross_margin`
          in `gross_margin`/`cloud_gross_margin`) — the original idempotency guarantee;
      (b) keeps a multi-token OBJECT whole so step 9 classify_token sees `vision_pro` as one object
          instead of [vision, pro] -> two UNKNOWNs -> slot_ambiguous (the false-reject fix);
      (c) keeps a multi-token BANNED phrase whole so the step-7 ban matches `us_gaap` instead of
          [us, gaap] sliding past the per-token check (the K15 multi-token-ban-bypass fix).
    Greedy LONGEST-match, left to right (same machinery as rejoin_compound_metrics). A bare token NOT
    in `frozen_atoms` (lone `margin`, `approval`) is NOT frozen, so its deliberate step-5 fold still
    fires. SINGLE-token entries are EXCLUDED from `frozen_atoms` by construction, which guarantees
    freezing can never suppress a single-token synonym/plural/acronym fold. Deterministic + idempotent
    (re-running on a joined list is a no-op)."""
    members = frozen_atoms
    if not members:
        return tokens, set()
    max_span = max(len(m.split('_')) for m in members)
    out, frozen, i, n = [], set(), 0, len(tokens)
    while i < n:
        joined = None
        for span in range(min(max_span, n - i), 0, -1):       # longest adjacent window first, down to 1
            candidate = '_'.join(tokens[i:i + span])
            if candidate in members:
                joined = candidate
                i += span
                break
        if joined is None:
            out.append(tokens[i]); i += 1
        else:
            out.append(joined); frozen.add(joined)
    return out, frozen

def rejoin_compound_metrics(tokens: list[str], compound_metrics: set[str]) -> list[str]:
    """R6: re-join adjacent tokens that together form a §F.6 COMPOUND_METRICS entry into ONE
    metric token, so a compound like 'gross_margin' occupies a single metric slot instead of
    splitting across step 9.5/10 (which would reject it as slot-ambiguous or a slot collision).
    Greedy LONGEST-match, left to right. Deterministic + idempotent (re-running on an
    already-joined list is a no-op). Invoked at §C step 8.5, after the per-token maps + dedup +
    banned/state + shortcut checks, before classify_token(). NOTE (v11-1): step 4.5
    freeze_known_atoms() already pre-joins compounds present before normalization; this pass now only
    catches compounds that first become adjacent/canonical AFTER step-5 folds."""
    if not compound_metrics:
        return tokens
    max_span = max(len(cm.split('_')) for cm in compound_metrics)
    out, i, n = [], 0, len(tokens)
    while i < n:
        joined = None
        for span in range(min(max_span, n - i), 1, -1):       # try longest adjacent window first
            candidate = '_'.join(tokens[i:i + span])
            if candidate in compound_metrics:
                joined = candidate
                i += span
                break
        if joined is None:
            out.append(tokens[i]); i += 1
        else:
            out.append(joined)
    return out
```

**New rejection reasons** (register alongside the existing `REJECTION_*` set in §G):
- `REJECTION_SLOT_ANCHOR_UNAVAILABLE` — name has no known token to anchor unknown-slot inference
  (mirrors the existing `slot_anchor_unavailable` at §F.10).
- `REJECTION_SLOT_AMBIGUOUS(token)` — an unknown token's slot is not uniquely determined between its
  nearest known anchors (closes the COV-1 multi-anchor hole).
- `REJECTION_SLOT_COLLISION(slot)` — two tokens classify to the same slot (R3).

---

## §E. Validator Rules

Format: `ID | Owner field | Check | Rejection reason`. Validators catch what §B + §C don't catch (companion-field + emission-level cross-checks).

| ID | Owner | Check | Rejection reason |
|---|---|---|---|
| V1 | aliases | every alias entry passes `canonicalize(entry) == parent_driver.name` (per CombinedPlan E6 correctness fix — aliases are spelling/order VARIANTS of the parent driver's canonical name; they must canonicalize TO the parent name, NOT to themselves. The pre-E6 rule `== entry` would reject valid order variants like `china_iphone_sales` as alias of `iphone_china_sales`.) | alias_does_not_canonicalize_to_parent |
| V2 | aliases | no alias matches another Driver's `name` or any other Driver's `aliases` entry | alias_bridges_unrelated_drivers |
| V3 | label | `sorted(slug(label).split("_")) == sorted(name.split("_"))` | label_concept_mismatch |
| V4 | segment | (`segment == "Total"` AND `name` has no sub-dimension) OR (`segment` matches the geography/customer/object sub-token in `name`) | segment_inconsistent_with_name |
| V5 | base_label | `base_label IS NULL` OR `base_label ∈ CANONICAL_BASE_LABELS` (§F.6) | invalid_base_label |
| V6 | allowed_states | every entry ∈ §F.5 AND all entries drawn from ONE class AND `STATES_MIN ≤ len ≤ STATES_MAX` (§G) | invalid_allowed_states |
| V7 | definition | exactly one sentence-final punctuation; non-empty; not a token-only restatement of `name` | bad_definition |
| V8 | driver_state | `driver_state ∈ Driver.allowed_states` | state_not_in_allowed_states |
| V9 | direction | `direction ∈ {long, short}` | invalid_direction_enum |
| V10 | evidence | `len(evidence) ≥ EVIDENCE_MIN_PER_TAG` AND each entry follows the SRC catalog format AND each entry resolves against the emission's `source_catalog` (per CombinedPlan E18 stricter V10 — syntactic format alone is insufficient; catalog resolution prevents hallucinated SRC IDs) | empty_or_malformed_or_unresolved_src |
| V11 | emission | every `driver_name` used in producer fields (Phase 1 learner = `primary_driver` + `contributing_factors[]`; Phase 2 news = `items[]`; Phase 3 fiscal.ai = direct ingest) resolves to existing `Driver.name` OR a `propose_new_drivers[]` entry in the SAME emission. Predictor's `key_drivers[]` (Phase 1) is OUT OF SCOPE per E30 — it stays as free-form analysis prose, never written to registry. | unresolved_driver_name |
| V12 | emission | no two `propose_new_drivers[]` entries in the same emission share a `name` | duplicate_proposal |
| V13 | emission | for every `propose_new_drivers[]` entry, that `name` is used at least once in a tag with non-empty evidence | proposal_without_use |
| V14 | propose_new_drivers.name | for every token in `name` not present in registry/banks, the §D new-token gate passes | new_token_gate_failed |
| V15 | registry | no two existing Drivers may have `sorted(name.split('_'))` equal post-canonicalization | duplicate_sorted_token_drivers |

> **Note (validator scope):** V15 = registry-global dedup = INGESTION-layer (the harness covers its concern via B8 sorted-token reuse); the deterministic harness builds V1–V14.

---

## §F. Reference Banks (mutable data)

All banks are append-only and exact-match. The orchestrator appends entries through valid `propose_new_drivers[]` emissions only.

### §F.1 Slot vocab seeds + SHORTCUTS_VOCAB

```
THEMES        = {ai, ev, ip, semiconductor, cloud, autonomous, cybersecurity, biotech}
OBJECTS       = {iphone, mac, ipad, vision_pro, datacenter, gpu, cpu, cloud_service, advertising}
CUSTOMERS     = {hyperscaler, enterprise, consumer, government, smb}
GEOGRAPHIES   = {china, us, japan, india, eu, emea, apac, latam, mexico, canada}
INSTITUTIONS  = {fed, ecb, boj, opec, fda, sec, doj, ftc}
METRICS       = {revenue, sales, units, deliveries, capex, opex, supply, price, rate,
                 demand, inventory, backlog, bookings, subscribers, arpu, churn}
SHORTCUTS_VOCAB  = {yield_curve, fed_rate, ecb_rate, boj_rate, usd_index, vix, credit_spread,
                 oil_price, oil_supply, opec_supply, fda_approval, sec_enforcement,
                 treasury_yield, ig_spread, junk_spread, inflation_rate,
                 tariffs, sanctions, export_restriction, trade_policy,
                 share_buyback, forward_guidance}                  // per D2 — corporate-action
                                                                   // event-shortcut (NOT a
                                                                   // compound metric — a
                                                                   // compound metric is a
                                                                   // multi-component derived
                                                                   // measure like gross_margin
                                                                   // = revenue − cogs; share_buyback
                                                                   // is a discrete action a company
                                                                   // announces, matches semantics
                                                                   // of fda_approval / opec_supply)
```

### §F.2 SYNONYM_MAP

Single-token (applied at canonicalize step 5):
```
topline   → revenue
turnover  → revenue
margin    → gross_margin       (only when not paired with another metric token)
```

Multi-token (substring at canonicalize step 2, longest-match first):
```
data_center   → datacenter
gross_profit  → gross_margin
```

### §F.3 PLURAL_MAP

```
# metric/event singular → plural canonical
sale     → sales
tariff   → tariffs
order    → orders
ruling   → rulings
approval → approvals
delivery → deliveries
unit     → units
booking  → bookings

# object/customer plural → singular canonical
iphones      → iphone
macs         → mac
ipads        → ipad
vision_pros  → vision_pro
datacenters  → datacenter
hyperscalers → hyperscaler
gpus         → gpu
cpus         → cpu
```

### §F.4 ACRONYM_MAP

```
gm    → gross_margin
om    → operating_margin
nm    → net_margin
fcf   → free_cash_flow
ocf   → operating_cash_flow
eps   → eps           (short form wins)
capex → capex
opex  → opex
arpu  → arpu
```

### §F.5 STATES_VOCAB

```
financial_outcome:  beat, missed, inline, raised, lowered, reaffirmed, withdrawn
quantity_move:      cut, expanded, contracted, exhausted, built, cleared, accumulated
policy_action:      imposed, eased, lifted, restricted, approved, denied, lapsed
rate_curve:         steepened, flattened, inverted, normalized
event_lifecycle:    announced, initiated, completed, cancelled, delayed
trend_motion:       accelerated, decelerated, stable, declined, compressed
sentiment_motion:   improved, deteriorated
```

### §F.6 COMPOUND_METRICS + CANONICAL_BASE_LABELS

```
COMPOUND_METRICS       = {gross_margin, operating_margin, net_margin,
                          free_cash_flow, operating_cash_flow,
                          cost_of_revenue, cost_of_goods_sold,
                          effective_tax_rate,
                          capital_expenditure,
                          short_interest, long_term_debt, short_term_debt}
                          // share_buyback REMOVED per D2 — moved to §F.1 SHORTCUTS_VOCAB
                          // (it's a corporate-action event, not a derived multi-component
                          // metric formula).
                          // short_interest / long_term_debt / short_term_debt (added 2026-05-29,
                          // owner-approved): legit multi-token METRIC names that contain a
                          // bare-banned direction word (short/long, §F.7 `direction`). Seeded here
                          // so §C step-3.5 freeze keeps each WHOLE → the bare-`short`/`long` ban does
                          // NOT break them. Pattern = "strict ban on loose words, explicit allow for
                          // real terms": add any future such term here and freeze guards it.
CANONICAL_BASE_LABELS  = {Sales, Revenue, GrossMargin, OperatingMargin, NetMargin,
                          EPS, CapEx, OpEx, FreeCashFlow, OperatingCashFlow,
                          CostOfRevenue, EffectiveTaxRate}
```

### §F.7 BANNED_CONTENT (token-level)

```
identity:         tickers (lower-cased Company.ticker from Neo4j Company registry),
                  legal company names (lower-cased Company.name slugified, e.g. apple,
                  tesla, samsung, nvidia, microsoft, ...),
                  person names (well-known executive/political names, e.g. elon_musk,
                  tim_cook, ...)
period:           patterns /^(q\d|fy\d{2,4}|h\d|\d{4})$/ and tokens {quarter, year, fiscal}
numeric:          patterns /^\d/ and unit suffixes {pct, bps, x, percent, basis_points}
source_type:      {8k, 10k, 10q, transcript, news, report, filing, ex_99, item}
provider:         {fiscalai, bloomberg, refinitiv, factset, benzinga, polygon}
xbrl_prefix:      {us_gaap, ifrs, dei}
metaphor:         {headwind, tailwind, kitchen_sink, sell_the_news, ankle_biter}
sentiment:        {strong, weak, bullish, bearish, positive, negative, upside, downside,
                   rising, falling, concerning, exciting, disappointing}
effect:           {selloff, rally, reaction, disappointment, surprise_factor}
motion_change:    {collapse, surge, rebound, plunge, recovery, slump, spike, drop, jump, decline}
                  # R7 "motion or change nouns" (K26 seed, owner-approved 2026-05-29) — a movement,
                  # NOT a reusable cause; belongs in driver_state/direction, banned from a NAME.
                  # (`declined` the state verb ≠ `decline` the change-noun — different tokens.)
direction:        {long, short, up, down}
                  # R7 direction/polarity (K8 seed, owner-approved 2026-05-29) — trade direction
                  # (long/short) belongs in the `direction` FIELD, which-way (up/down) describes
                  # movement not a cause; NEVER a NAME token. `gpu_short_us_revenue` MUST reject.
                  # (`rising`/`falling` already under sentiment.)
magnitude_word:   {large, small, big, huge, tiny, minor, major, modest, slight, significant, substantial}
                  # R7 qualitative magnitudes (owner-approved 2026-05-29) — describe SIZE, not a
                  # reusable cause; banned from a NAME. `gpu_large_us_revenue` MUST reject.
category:         {macro, sector, sentiment, positioning, theme_only}
vague_descriptor: {update, performance, quality, situation, environment, outlook,
                   story, narrative, momentum, dynamics, picture}
verb_form:        any token matching /^[a-z]+(ed|ing)$/ that is NOT in OBJECTS ∪ METRICS
                  ∪ COMPOUND_METRICS ∪ GEOGRAPHIES ∪ INSTITUTIONS ∪ THEMES ∪ CUSTOMERS
                  ∪ ALLOWED_VERBAL_FORMS (§F.9)
```

### §F.8 STOPWORDS

```
{the, of, in, and, or, on, at, for, with, to, a, an, by, from, into}
```

### §F.9 ALLOWED_VERBAL_FORMS (exception allowlist for the §F.7 verb_form ban)

Tokens that end in `-ed` or `-ing` but are legitimate accounting/financial qualifiers and may appear in `name` (typically inside compound metrics).

```
{consolidated, diluted, weighted, deferred, accrued, retained, underwriting, lending}
# `restricted` + `accumulated` REMOVED (2026-05-29, F5/F9 fix): both are §F.5 STATES
# (policy_action `restricted`, quantity_move `accumulated`) → they belong in driver_state and
# are banned from names by canonicalize step 7. No seeded COMPOUND_METRIC / CANONICAL_BASE_LABEL
# uses either token, so removal costs nothing and resolves the §F.5-vs-§F.9 contradiction.
```

### §F.10 Live Token Stores (NEW per E10 amended + E27 + v6-4 Pattern split)

Per E27 + v6-4: live token growth follows THREE patterns, not five separate banks. Markdown §F.1-§F.9 above is BOOTSTRAP SEED ONLY (NEVER mutated at runtime per L5). Runtime growth lives in Neo4j.

**Pattern A1 — `:VocabToken` (per E10 amended + v9-1 + v10-1)**: slot-vocab growth via IMMEDIATE append. When a `propose_new_drivers` proposal introduces a token not in §F.1 slot vocabs and the Driver passes R11 + V1-V15, the token is appended to `:VocabToken{slot, token, added_at, source_driver_id, vocab_visible_at}` IMMEDIATELY at Driver-write time. NO N=2 gate. Rationale: the Driver itself already passed in-context validation (R11 + new-token gate); re-gating via N=2 would needlessly delay future slot classification.

- **vocab_visible_at** (PIT anchor):
  - ON CREATE: `= source_driver.registry_visible_at` at write time (= MIN of the Driver's DC pit_cutoffs at write time)
  - ON MATCH (token+slot already exists): BACKDATE via `MIN(existing, $source_pit)` — same L6 MIN-backdate pattern as `Driver.registry_visible_at = MIN(DC.pit_cutoff)`. Closes the out-of-order under-visibility scenario v9-1's set-once semantics left open (per v10-1 / Bot A finding 1.1 reversal of prior X3 deferral).
  - Read path: bootstrap loader PIT-filters via `WHERE ($run_pit_cutoff IS NULL OR vt.vocab_visible_at <= datetime($run_pit_cutoff))` parallel to `EquivalenceToken.equivalence_visible_at` filter per v4-7.
- **EDGE CASE**: if a proposal contains ZERO known tokens (no anchor for position-based slot inference), reject as `slot_anchor_unavailable`.

**Pattern A2 — `:EquivalenceToken` (per E27)**: transform-mapping growth (synonym / plural / acronym) via N=2 distinct-event promotion gate. Different blast radius than slot vocab: a wrong equivalence changes canonicalize behavior across MANY future emissions, so a stricter gate is required.

- **Schema fields**: `equivalence_id` UNIQUE per `(kind, from_token)` **for the PROMOTED entry** (v5-1); competing CANDIDATE to_tokens are tracked per `(kind, from_token, to_token)`, each with its OWN `observation_keys`/count so N=2 applies PER candidate (a later "loser" can still reach N=2) — exact key realization (extend candidate `equivalence_id` with `to_token`, or per-`to_token` sub-records) finalized at integration. `kind ∈ {synonym, plural, acronym}` (no `shortcut` per v5-5 — shortcuts go to Pattern B). `from_token`, `to_token`. `observation_keys[]` event-level dedup per v4-2 (strip producer prefix: `learner:AAPL:Q2` → `AAPL:Q2`). `observation_pit_cutoffs[]` parallel array. `status ∈ {candidate, promoted}`. `promoted_at` wall-clock AUDIT ONLY (v5-12). `equivalence_visible_at` PIT anchor per v4-7 + v10-2.
- **N=2 promotion gate**: `EQUIV_PROMOTE_N=2` is a HARDCODED Python constant in `driver_writer.py` (NOT runtime-env-tunable per v3-14 + L4).
- **Conflict semantics (locked, 2026-05-29)**: Multiple CANDIDATE to_tokens may EXIST (evidence-gated); only ONE may PROMOTE per `(kind, from_token)`; a conflict FREEZES promotion until one isolated judge call resolves it → persist exactly one of `{to_A, to_B, no-global-rule (→ driver-level reuse only), defer (stay frozen; re-judge when more evidence)}`; N=2 is the ELIGIBILITY gate (the judge may only approve a candidate that has cleared N=2 — never promote a one-off merely because it "sounds better"), judge confirms meaning once, code persists + replays. Post-promotion a later stray conflicting observation does NOT auto-demote a promoted rule (audit only; re-judge only if it independently clears N=2). _(builder: this changes synonym_fold.py conflict handling from block → judge-escalate; aligned at integration.)_
- **Judge-seam interface (mirrors Harness_BuilderPrompt §13)**: `judge_fn(packet) -> verdict`; `packet = {kind, from_token, candidates: [{to_token, observation_count, sample_evidence}]}` (N=2-cleared competitors only — eligibility gate is code, pre-judge); `verdict = {decision: promote|no_global_rule|defer, to_token, reason}`.
- **Two-phase Cypher write path (per v5-4 + v6-2)**: Python cannot interrupt a single Cypher statement midstream, so the promotion path splits into two Cypher queries with Python in between:
  - **Phase 0 (Python pre-check)**: query existing by equivalence_id; if exists AND `to_token != $to` → this is a CONFLICT: do NOT first-wins-reject the second `to_token`. Multiple CANDIDATE to_tokens may EXIST (each evidence-gated); only ONE may PROMOTE per `(kind, from_token)`. FREEZE promotion + judge-escalate per v5-1 sequential conflict: keep the competing candidate(s), hold promotion, and (once `>=2` evidence-backed `to_token`s have each cleared N=2 — gate runs FIRST) make ONE isolated Pattern B judge call that persists exactly one of `{to_token_A, to_token_B, NO-GLOBAL-RULE (token is context-dependent → handle via driver-level reuse only)}`. Code persists the single verdict + replays it deterministically forever. Record the FREEZE + judge-escalation in `:EquivalenceConflictAudit` (NOT a silent reject)
  - **Phase 1 (Cypher MERGE)**: single atomic statement. MERGE node + ON CREATE/ON MATCH + intra-MERGE `WITH et WHERE et.to_token = $to` guard per v9-2 (race protection between Phase 0 and Phase 1; loser's empty RETURN triggers Python `:EquivalenceConflictAudit` write — recording a FREEZE + judge-escalation, NOT a first-wins reject: the conflicting `to_token` stays a live candidate and feeds the same FREEZE/judge resolution as Phase 0) + compute-before-SET new arrays + SET observation arrays + v10-2 equivalence_visible_at MIN-backdate CASE + RETURN `would_promote` + `new_pit_cutoffs`
  - **Phase 2 (Python between Cypher queries)**: if `would_promote=true`, run collision recheck against current Driver registry per v4-6 (registry may have changed between candidate creation and promotion; collision → `:EquivalenceCollisionAudit` + status stays candidate)
  - **Phase 3 (Cypher SET — conditional)**: SET status='promoted' + promoted_at + equivalence_visible_at, with `WHERE et.status = "candidate"` guard so concurrent writers are race-safe — exactly ONE Phase 3 status transition succeeds per v10-3 (the second's WHERE filters out as no-op)
- **Candidates HIDDEN from LLM** (per v2 Fix #2): bundle renderer + canonicalize read path filter `WHERE et.status = "promoted"` only. Prevents fast-pass of the promotion gate via LLM self-reinforcement.

**Pattern B — Shortcut Drivers (per v5-5 + v8-1 + v7-2)**: shortcut growth via direct `:Driver` row registration with `is_shortcut: bool DEFAULT false` schema property (v8-1). `is_shortcut=true` proposals bypass slot grammar (canonicalize steps 9-11) and land DIRECTLY as `:Driver` rows on R11 evidence pass. NO parallel `:EquivalenceToken` record (v5-5 drops `kind:shortcut` from the enum). The registry IS the shortcut store.

- **Acceptance gates (v7-2 tightening)**: shape regex + banned-content + zero-slot-classifying-tokens + **≥2 underscore-separated tokens** (v7-2 mechanical gate — rejects single-word LLM hallucinations like `winter`, `crash`, `armageddon`) + R11 evidence + **MANDATORY isolated Pattern B judge (2026-05-29):** because `is_shortcut=true` BYPASSES the slot grammar (canonicalize steps 9-11), a new NON-seeded shortcut registration requires a persisted, gated judge verdict (cheap model, temp 0, structured output, verdict cached/replayed by code). Seeded shortcuts (§F.1 / §J.2 cold-start) stay code, no judge. The mechanical gates above remain code and run FIRST; the judge fires only on a candidate that clears them.
- **Why no N=2 for shortcuts**: deadlock — first emission of a real new shortcut has no Driver yet (not promoted, candidate-only), so the LLM at the next event would see no anchor in the catalog and emit the same shortcut form again, still no Driver, infinite loop. Current gate (R11 + shape + banned + zero-slot + ≥2-token + evidence) is the production trade-off. Documented + accepted recall/integrity trade-off; cleanup is code-time via `deprecated_at + replaced_by` if pollution emerges.
- **Read path**: bootstrap query filters `MATCH (d:Driver) WHERE d.is_shortcut = true AND d.registry_visible_at <= run.pit_cutoff` to populate `VocabSnapshot.shortcuts`. Future emissions of the shortcut form hit `Driver.name` via B3 (exact-match name lookup) directly — no canonicalize needed, no parallel store consulted.

**Backward-compat (v3-7 + v5-7)**: pre-promotion legacy split Drivers (e.g., `cloud_topline` + `cloud_revenue` both existing before `topline → revenue` was promoted) stay AS-IS. `Driver.name` is IMMUTABLE per Neo4jXBRLDesign §C3.1. A MANDATORY reconciliation job (production-trust; may be STAGED after the harness) merges two ALREADY-REGISTERED drivers when a late-learned equivalence or a judge ruling proves them the same: relink DriverChanges + record supersession; judge-confirmed only; audited with provenance; reversible (un-merge); PIT-HONEST (merge carries an effective date so historical/PIT queries still see what was true then). Until it ships, late duplicates are AUDITED debt (`:DriverDriftAudit`), never silently merged. `Driver.name` stays IMMUTABLE per Neo4jXBRLDesign §C3.1 (the reconciliation supersedes, it does not rename).

---

## §G. Numerical Thresholds (tunable; injected at runtime)

```
MAX_EFFECTIVE_SLOTS    = 4
STATES_MIN             = 2
STATES_MAX             = 8
EVIDENCE_MIN_PER_TAG   = 1
```

Tuning these values does NOT touch `DriverOntology.md`.

---

## §H. Conformance Index — Ontology → Implementation

Every rule in `DriverOntology.md` has at least one enforcing clause here. Audit this table on every implementation rev; any uncovered ontology rule is a drift signal.

| Ontology rule | Enforcing clauses |
|---|---|
| §2 driver_name shape (lowercase ASCII, no edge `_`, no consecutive `_`, ≥2 chars) | §D shape regex, B2 slugify, C step 1 |
| §2 canonical form definition | §C steps 2–10 (the function's output) |
| §3 Field Placement (all rows) | B1 extract rule, V3, V4, V5, V6, V7, V8, V9, V10 |
| R1 Reuse first | B3, B4, B6, B7, B8 |
| R2 Causal variable only | B1 extract rule, C step 7 STATES check, F.7 direction/sentiment/metaphor/effect, B1's "exclude every token §3 places elsewhere" |
| R3 Slot order is fixed | C step 10 order_by_slot, §D BNF grammar |
| R4 Closed vocabulary | C step 9 classify, F.1–F.8 banks, §D new-token gate |
| R5 Standalone shortcut (renamed from "Macro shortcut" per E23 / OQ3 — R5 covers macro AND regulatory AND corporate-action AND event shortcuts) | C step 4.5 freeze_known_atoms (protect before normalize, v11-1), C step 8, F.1 SHORTCUTS_VOCAB |
| R6 Compound metrics as one slot | C step 2 substitution, C step 4.5 freeze_known_atoms (v11-1), C step 8.5 rejoin_compound_metrics, F.6 COMPOUND_METRICS |
| R7 Banned content categories | C step 4.5 freeze_known_atoms (multi-token bans — us_gaap / person-names / basis_points — frozen so the per-token C-step-7 ban catches them, v11-2), C step 7, F.7 BANNED_CONTENT (every category mapped) |
| R8 Length bounded | C step 11 effective_slot_count, G MAX_EFFECTIVE_SLOTS |
| R9 Granularity | B1 extract rule (geography/customer/object sub-dim only if evidence-attributed) |
| R10 Companion field rules | V1, V2, V3, V4, V5, V6, V7 |
| R11 New driver gate | B10, V14, §D new-token gate, V10 evidence requirement, V13 same-emission use |
| §5 examples (illustrative only) | No enforcement clause needed — examples illustrate already-decided rules |

---

## §I. Rev-Trigger Reference

| Change type | Touches DriverOntology.md? |
|---|---|
| Grow OBJECTS / METRICS / GEOGRAPHIES / CUSTOMERS / THEMES / INSTITUTIONS / SHORTCUTS_VOCAB | ❌ No |
| Add entry to SYNONYM_MAP / PLURAL_MAP / ACRONYM_MAP | ❌ No |
| Add verb to STATES_VOCAB within an existing class | ❌ No |
| Add entry to COMPOUND_METRICS or CANONICAL_BASE_LABELS | ❌ No |
| Add specific tokens to a BANNED_CONTENT category | ❌ No |
| Tune MAX_EFFECTIVE_SLOTS, STATES_MIN/MAX, EVIDENCE_MIN_PER_TAG | ❌ No |
| Refactor `canonicalize()` internals (different algorithm, faster matching) | ❌ No |
| Tighten or relax the regex implementation (preserving the shape semantics) | ❌ No |
| Add a new validator that enforces an existing ontology rule more strictly | ❌ No |
| Reorder the §B reuse cascade (B3/B4 vs B6/B7 sequence) | ❌ No |
| Add a brand-new slot type (e.g., "protocol") | ✅ Yes — slot grammar is a rule |
| Add a brand-new rule concept | ✅ Yes — new R-rule |
| Add a brand-new banned-content category | ✅ Yes — §4 R7 lists categories |
| Add a new field on emitted driver tags | ✅ Yes — §3 Field Placement |
| Flip the semantics of an existing rule (e.g., "aliases may bridge" allowed) | ✅ Yes — semantic flip |
| Relax the slug shape constraint (allow digit prefix, allow hyphens, etc.) | ✅ Yes — §2 shape spec |
| Drop the determinism contract | ✅ Yes — §1 Purpose |
| Implement Lever #1 auto-repair wrapper (E26 fold) | ❌ No — writer-side mechanism, not ontology |
| Implement Lever #2 unified `:EquivalenceToken` + Pattern A1/A2/B (E27 fold) | ❌ No — implementation mechanism |
| Implement Lever #3 informed retry (E28 fold) | ❌ No — orchestrator mechanism [SUPERSEDED 2026-05-29: Pattern A is learner-self-correct, not orchestrator re-injection] |
| Add audit telemetry tables (E29 fold) | ❌ No — observability layer |
| Add `vocab_visible_at` MIN-on-MATCH backdate to `:VocabToken` (v9-1 + v10-1) | ❌ No — schema/mechanism |
| Add `equivalence_visible_at` MIN-backdate per observation to `:EquivalenceToken` (v10-2) | ❌ No — schema/mechanism |

---

## §J. Writer Contract + Informed Retry (NEW per E16 + E28 Lever #3 fold)

**Source-agnostic input JSON contract** (per E16, post-E30 + v7-1 + v10-6):

```
input JSON = {
    source_id:        string,
    source_type:      one_of {"learner_result", "news", "fiscal_kpi"},
                          // prediction_result REMOVED per E30 + v7-3 — predictor is
                          // consumer-only (permanent stance, not "for now")
    pit_cutoff:       ISO ts,
    result_path:      str,
    run_id:           str,
    source_catalog:   [str],    // SRC:* IDs available to this emission (per E18 V10)
    items: [
        {
            ticker:         str,
            driver_name:    str,
            driver_state:   str,
            direction:      "long" | "short",
            exposure_role?: one_of {"producer", "consumer", "supplier", "competitor", "neutral"},
                              // populated only when 1 DC affects multiple companies with
                              // non-uniform signs (news pipeline only per E14)
            evidence:       [str]    // SRC:* refs
        }
    ],
    propose_new_drivers: [
        {
            name:            str,
            label:           str,
            base_label?:     str,    // for XBRL family resolution (null for non-financial per E17)
            segment:         str,    // "Total" default per E25 / M4
            definition:      str,
            allowed_states:  [str],
            aliases:         [str],
            is_shortcut:     bool DEFAULT false    // v3-5 + v8-1: Pattern B discriminator
        }
    ]
}
```

**Sidecar JSON**: written at `/tmp/dr_written_{source_id}_{run_id}.json` per E16. `{accepted_count, rejected_count, per-driver outcomes}`.

**Exit codes** (per E1 PARTIAL policy):
- `0` = sentinel_fires (≥1 driver wrote, system OK)
- `1` = all_proposals_failed (no driver wrote; sentinel blocks)
- `2` = system_or_writer_failure (sentinel blocks)

**Lever #1 auto-repair wrapper (per E26 fold) — DEMOTED/DEFERRED below Lever #3 self-correct loop (2026-05-29):** the PRIMARY recovery path is the same-producer learner self-correct loop (Lever #3 below — the producer calls the validate tool, fixes flagged tags, re-validates <=3 tries, with the orchestrator write-gate authoritative); auto-repair is NOT removed but is deferred — revive it post-launch only if telemetry shows many mechanically-recoverable rejects, and then ONLY for unambiguous strips. When canonicalize() returns a structured rejection, the writer MAY attempt deterministic single-rule repairs (only if PROVABLY SAFE):

- `REJECTION_STATE_IN_NAME(t)` — if `driver_state` is empty OR case-insensitively equals `t` (v6 Fix #9): strip `t`, set driver_state=t, re-canonicalize. ON PASS + EXACT-MATCH existing Driver + repaired state ∈ Driver.allowed_states (v4-5 V8 post-repair): write + log `:DriverAutoRepair{repair_kind=state_to_driver_state}`. If V8 fails OR no exact match → DEFER to Lever #3 retry. v3-3 trend-partner preference: when stripping `trend_motion` verb, check registry for `{metric}_trend` partner first; prefer it (`repair_kind=state_to_trend_partner`). Only `_trend` suffix recognized per current ontology (per v4-16).
- `REJECTION_BANNED_TOKEN(t)` where t is period (q3/fy26/2025/h1): strip → re-canonicalize → MUST exact-match. Where t is magnitude per v3-2 NARROWED regex `/^\d+(pct|bps|x|percent|basis_points)$/` ONLY (do NOT strip bare `/^\d/` — would incorrectly remove `5g`, `10yr`, `3nm`). Where t is identity (ticker/company/person): final reject.
- `REJECTION_NO_METRIC_TOKEN` / `REJECTION_TOO_MANY_SLOTS`: no safe repair → reject.

Audit row `:DriverAutoRepair` with UNIQUE on `(source_id, item_index)` per v4-14 + v5-2 (item_index is a declared schema property per v9-4 — see §K).

**MECHANISM UPDATED 2026-05-29 — Pattern A is now LEARNER-SELF-CORRECT (producer calls the validate tool and fixes flagged tags, <=3 tries, orchestrator write-gate authoritative), NOT orchestrator-driven re-injection. The re-injection / prior-rejection-block / 3-stage-merge details below are SUPERSEDED; retained for reference pending the integration rewrite (SKILL.md + driver_write_cli.py).**

**Lever #3 informed retry (per E28 fold)** — within-session re-emission of the SAME learner LLM (per E20 + E30: NOT a second extraction pass; same producer, same bundle, same source_id, same TMUX transport per Final.md §5 Fix #5). Function `orchestrator.run_driver_write()` (transport-neutral name — drops legacy `_via_sdk` suffix per Fix #5; SDK target paths are forbidden per Final.md §5). Mirrors H2 informed-retry pattern at `orch.py:1347-1387` (production-validated).

**Flow**: learner writes result.json → orchestrator validates + `driver_write_cli --dry-run` → if FAIL with per-driver rejection_reasons: build prior-rejection block (per `orch.py:3118-3165` verbatim format) → ONE retry via TMUX → `--dry-run` AGAIN → PASS = write + outcome `SUCCEEDED_AFTER_RETRY`; STILL FAIL = per-driver final reject → `:DriverProposalRejection` + run continues per E1 PARTIAL policy.

**`DriverWriteOutcome` enum** (mirror `LearnerOutcome` at `orch.py:1066-1106`): `SUCCEEDED`, `SUCCEEDED_AFTER_RETRY`, `FAILED_VALIDATION_RETRY`, `FAILED_DRIFT_GUARD` (per v3-9 + v4-8), `FAILED_SCOPE_CREEP` (per v3-8), `FAILED_RETRY_SHAPE_VIOLATION` (per v4-9), `FAILED_SYSTEM`.

**3-stage merge logic on retry response** (per v3-8 + v3-9 + v4-8 + v4-9 + v4-15 + v5-9 + v5-11 + v6-1 + v10-6):

- **STAGE 1 — DRIFT GUARD (v4-8 inversion-whitelist)**: producer-specific `DRIVER_FIELDS` dispatch per v7-1 — for learner Phase 1 = `{primary_driver, contributing_factors, propose_new_drivers}` (NO `key_drivers` per v7-1 + v10-6 + E30 — predictor's free-form field is never in the retry path); for Phase 2 news = `{items, propose_new_drivers}`. `ORCHESTRATOR_STAMPED` = explicit Python-owned echo fields (`schema_version, ticker, quarter_label, predicted_at, attributed_at, model_version, sdk_session_id, pit_*, confidence_bucket, magnitude_bucket` — derived from LLM-authored `confidence_score`/`expected_move_range_pct` per Final.md §7, `actual_return_pct, context_bundle_ref, prediction_result_ref`). Diff R1 vs R2 across `(all_fields − DRIVER_FIELDS − ORCHESTRATOR_STAMPED)` — any drift = `FAILED_DRIFT_GUARD`; R1 rejected drivers stay rejected; field-diff logged to `:DriverDriftAudit`. Future-proof: new LLM-authored fields default-include in guard.
- **STAGE 2 — SURGICAL REPLACE BY TAG (v3-8 + v4-9 + v5-9 + v10-6)**: array length + order preserved (`R2.contributing_factors.length == R1.contributing_factors.length`). PASSED-in-R1 indices: R2 tuple `(driver_name, driver_state, direction, evidence)` MUST be IDENTICAL to R1 — else `FAILED_RETRY_SHAPE_VIOLATION`. FAILED-in-R1 indices: REPLACE with R2 at same index. v4-15: drop ORPHANED R1 proposals (R1 entries no longer referenced by any merged tag).
- **STAGE 3 — PROPOSE_NEW_DRIVERS GATE (v5-11 same-name replacement)**: CASE A — R2 entry has same `name` as R1 entry that FAILED V1-V15: ACCEPT as corrected version (re-run R11+V1-V15). CASE B — NEW name referenced by STAGE-2-replaced tag whose R1 rejection was `unresolved_driver_name`: ACCEPT (V11 carve-out). CASE C — NEW name with no carve-out: REJECT as `FAILED_SCOPE_CREEP`.
- **FINAL merge formula (v6-1 corrected)**: `final.propose_new_drivers = (R1 − replaced − orphaned) + STAGE-3-CASE-A-replacements + STAGE-3-CASE-B-additions`.

**One retry only**: learner pattern production-validated. More = drift + diminishing returns.

---

### §J.1 Mirror Map — Driver vs Guidance Machinery (per CombinedPlan E15)

Driver pipeline BORROWS guidance's machinery where structure is identical, REPLACES where driver-specific. This map disambiguates which guidance helper each driver helper mirrors.

```
DRIVER COMPONENT                                 ← BORROWS FROM
─────────────────────────────────────────────────────────────────────────────────
driver_ids.slug()                                ← guidance_ids.slug() (verbatim)
driver_ids.driver_change_id() (PLANNED — built with driver_write_cli.py at integration; mirrors guidance's build_guidance_ids(); NOT yet in the harness driver_ids.py)
                                                 ← guidance_ids.build_guidance_ids()
                                                    (borrows the deterministic slot-ID
                                                     PATTERN, not the arity: guidance id
                                                     is 5-part; driver_change_id is 3-part
                                                     = source_key:driver_slug:state_slug)
driver_concept_resolver.py                       ← concept_resolver.py
                                                    (financial-driver sliver only;
                                                     reuse for base_label → xbrl_qname
                                                     resolution when xbrl_qname is set)
driver_writer.create_driver_constraints()        ← guidance_writer.create_guidance_constraints()
                                                    (same MERGE-idempotent + UNIQUE
                                                     constraint pattern; driver-specific
                                                     node labels)
registry + vocab loader                          ← bundle renderer's `guidance query 7A`
                                                    pattern (PIT-filtered render at
                                                     bundle-build time — NOT warmup_cache.py;
                                                     warmup_cache is XBRL-specific and
                                                     does NOT apply to driver path)

NEW DRIVER COMPONENTS (no guidance equivalent):
─────────────────────────────────────────────────────────────────────────────────
driver_writer.merge_driver_change_with_supersession()
                                                  (R15 #1 — supersession of dropped DCs
                                                   across re-runs of the same source_id;
                                                   no guidance equivalent because guidance
                                                   schema doesn't re-run drop semantics)
driver_writer.write_vocab_token() (E10 + E27 + v9-1 + v10-1)
                                                  (live :VocabToken append with
                                                   vocab_visible_at MIN-on-MATCH backdate)
driver_writer.write_equivalence_token() (E27 + v5-4 + v6-2 + v9-2 + v10-2)
                                                  (two-phase Cypher with Python step
                                                   between for intra-MERGE to_token guard;
                                                   equivalence_visible_at MIN-backdate)
driver_writer.write_audit_row() (E29 telemetry)
                                                  (5 audit-label writers)
```

### §J.2 Cold-Start Seed Clause (per CombinedPlan E9 + E15 + E16)

The Driver registry is seeded at first-boot via a hardcoded Python constant `COLD_START_SEED_DRIVERS` in `driver_writer.py` (per OQ4=HARDCODED CONSTANT — L4 forbids runtime human curator; code-time constant is normal engineering, deterministic, inspectable, no runtime LLM dependency).

```python
# scripts/earnings/builders/driver_writer.py

COLD_START_SEED_DRIVERS: list[dict] = [
    # TIER 1 — TIMELESS (vocab_visible_at = EPOCH_SENTINEL): ~32 anchors
    # macros / universal compounds / timeless geographies/institutions/metrics
    # Examples (illustrative — full list per CombinedPlan E9):
    {"name": "oil_supply",      "is_shortcut": True,  "registry_visible_at": EPOCH_SENTINEL, ...},
    {"name": "opec_supply",     "is_shortcut": True,  "registry_visible_at": EPOCH_SENTINEL, ...},
    {"name": "yield_curve",     "is_shortcut": True,  "registry_visible_at": EPOCH_SENTINEL, ...},
    {"name": "fed_rate",        "is_shortcut": True,  "registry_visible_at": EPOCH_SENTINEL, ...},
    {"name": "gross_margin",    "is_shortcut": False, "registry_visible_at": EPOCH_SENTINEL, ...},
    # ... ~32 total TIER 1 entries
]

# TIER 2 — MODERN (per-driver date): EXCLUDED from cold-start seed by default.
#   Modern drivers (iphone_china_sales, hyperscaler_capex, ai_datacenter_us_capex, ev_sales,
#   etc.) MUST grow organically via propose_new_drivers[] at their actual PIT (registry_visible_at
#   = the source's pit_cutoff). Including TIER 2 in cold-start would PIT-leak: a 1990 backfill
#   would see `iphone_china_sales` in the catalog → vocabulary contamination → drift.
```

**PIT policy** (per E9 + L6):
- TIER 1 timeless anchors → `registry_visible_at = EPOCH_SENTINEL` (visible to all PIT cutoffs).
- TIER 2 modern drivers → EXCLUDED from cold-start; visible only after a real DC lands at their actual PIT (`Driver.registry_visible_at = MIN(all DC.pit_cutoff)` per L6).
- Bootstrap loader runs ONCE at first boot (idempotent — `MERGE` on `Driver.name`; re-running on populated registry is a no-op).
- L6 MIN-update rule does NOT apply to seed drivers at bootstrap (zero DCs). Seed drivers retain their `EPOCH_SENTINEL` until/unless explicitly recomputed.
- Slot vocab seeds (§F.1 THEMES/OBJECTS/CUSTOMERS) load into `:VocabToken` rows at bootstrap with SANE `vocab_visible_at` dates (reusing the EXISTING `vocab_visible_at` field — NOT a new mechanism): TIMELESS anchors (`oil_price`, `fed_rate`, `china`, `revenue`, …) use `vocab_visible_at = EPOCH_SENTINEL`; ERA-BOUND modern tokens (`iphone`, `datacenter`, `hyperscaler`, `ai`, `gpu`, `vision_pro`, …) carry realistic `vocab_visible_at` dates (err LATER = conservative) so the PIT-filtered hint excerpt excludes them on historical runs. (Code-time seed task per L4 = normal engineering; the date-assignment + render-filter are integration-phase work. Uses the EXISTING `vocab_visible_at` field — NOT a new mechanism.) **Slot-vocab PIT-safety** (D1 resolution) rests on EXISTING `visible_at` fields, not a new mechanism: (a) the LLM sees only a short slot/shortcut HINT EXCERPT rendered from the PIT-FILTERED vocab snapshot (`vocab_visible_at <= run.pit_cutoff`), so historical runs are ERA-SAFE — no future-coined tokens are shown; the FULL slot-vocab classification banks stay INTERNAL to `canonicalize()` (harmless + still deterministic given the frozen snapshot, because R11 ensures only evidence-present tokens are ever classified); (b) the Driver-registry PIT gate at `Driver.registry_visible_at <= run.pit_cutoff` blocks visibility at the LLM-facing layer; and (c) the R11 evidence-requirement (a token must appear in the evidence text) prevents proposing a name with a future-coined token under historical PIT — a 1990 source would not contain "iphone", so `propose_new_drivers[]` cannot surface it. The LLM's prompt accordingly receives `DriverOntology.md` + the PIT-filtered Driver registry catalog (filtered by `Driver.registry_visible_at`) + a PIT-filtered slot/shortcut HINT EXCERPT + numerical thresholds. Runtime-promoted `:VocabToken` entries inherit their MIN-backdated `vocab_visible_at` (v9-1 / v10-1 / v10-2 MIN-on-MATCH backdate), so the same PIT filter governs them too.

---

## §K. Audit Table Schemas (NEW per E29 fold — pure telemetry for observability)

**Critical scope clarification (per E29)**: PURE TELEMETRY. Self-heal does NOT require any seed edits — the system grows itself at runtime via the Neo4j `:EquivalenceToken` + `:VocabToken` stores. Audit data is NOT a feedback input to the markdown seed; engineers MAY OPTIONALLY use audit data for code-time cleanup (deprecating bad VocabToken entries via Cypher migration, reviewing aberrant promotion counts). Without these tables the system still self-heals; we just lose observability.

```
:DriverAutoRepair (Lever #1):
  source_id, run_id, item_index (v9-4 declared schema property),
  original_name, repaired_name, stripped_token,
  repair_kind ∈ {state_to_driver_state, state_to_trend_partner,
                  magnitude_strip, period_strip, deferred_to_retry},
  cascade_outcome ∈ {PASS, REJECTION_NO_METRIC_TOKEN, REJECTION_BANNED_TOKEN,
                      REJECTION_TOO_MANY_SLOTS, DEFERRED_TO_RETRY,
                      FINAL_REJECT_OTHER},
  evidence_refs, repaired_at
  CONSTRAINT: UNIQUE on (source_id, item_index) per v4-14 + v5-2 + v9-4
  RATIONALE: Re-runs of same emission slot overwrite (last-write-wins).
             Sidecar JSON + run_ledger preserve retry history separately
             (adding run_id to the key would bloat telemetry — push-back
             per v5 in §7 of CombinedPlan rejected suggestions)

:DriverProposalRejection (E1 PARTIAL policy + Lever #3 final rejects):
  source_id, run_id, proposed_name, rejection_reason, evidence_refs, rejected_at
  CONSTRAINT: MERGE on (source_id, run_id, proposed_name)

:EquivalenceConflictAudit (v5-1 acceptance-time + v9-2 race-time):
  equivalence_id, existing_to, proposed_to, source_id, item_index, froze_at,
  judge_verdict?  // {to_A, to_B, no-global-rule}; null until the isolated judge resolves
  RECORDS the FREEZE + judge-escalation (locked 2026-05-29), NOT a first-wins
  reject: the conflicting to_token stays a live candidate; promotion is held until
  one isolated judge call persists exactly one verdict (N=2 gate runs FIRST). A
  post-promotion stray conflicting observation is audited here too but does NOT
  auto-demote the promoted rule (re-judge only if it independently clears N=2).
  DISTINCT from :EquivalenceCollisionAudit (different mechanism per v8-5 test)

:EquivalenceCollisionAudit (v4-6 promotion-time Driver-registry collision):
  equivalence_id, conflict_driver_id, detected_at
  TRIGGER: registry changed between candidate creation and Nth observation;
           equivalence stays "candidate", promotion held

:DriverDriftAudit (direction flip across re-runs on :FOR_COMPANY edge):
  dc_id, ticker, old_direction, new_direction, revision_ts, reason?
```

See `Neo4jXBRLDesign.md` for the authoritative schemas + UNIQUE constraints.
