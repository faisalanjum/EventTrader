# RELIABILITY AUDIT — Driver CREATION Layer

> One adversarial lens: **reliability = mechanical determinism of `canonicalize()`/`classify_token()` +
> an emission contract that yields a clean name every time or fails closed.** Scope = CREATION only
> (evidence → clean canonical validated name + companion fields, BEFORE the writer). Ingestion judged
> only on clean hand-off (E16). Every claim verified against current bytes on disk; the plan's own
> ">=9 false-positive (stale-state)" history means nothing taken on the plan's word.

---

## VERDICT IN ONE LINE

The deterministic SPINE of the creation layer is real and mostly sound: shape regex (E7/§D), the banned/
state/stopword/dedup/length gates (§C steps 1,4,6,7,11), the reuse cascade (B3-B8), and the ambiguity-reject
gate (R11f) are genuinely mechanical and fail-closed. **But the single most accuracy-critical function —
`classify_token()`, which decides the slot of a NOVEL token — has NO defined body anywhere in P1/P2/P4, and
the slot order it feeds (`order_by_slot`) and the length count (`effective_slot_count`) are also undefined.**
On novel/unseen tokens the slot assignment is delegated to the LLM via R11(c) "position unambiguously
determines slot," which is NOT mechanically defined and is exactly the ~85%-capped LLM judgment that L3 says
to keep OUT of the determinism path. Two LLMs CAN diverge here. The plan's own "~96-98%" headline is an
unmeasured projection over a ≥90% enforced bar; the user's ~100% target is not mechanically demonstrated.

---

## A. THE DETERMINISTIC SPINE — what genuinely fails closed (NOT findings; clean)

These are mechanical and I emit NO finding for them:

- **Shape gate** §C step 1 + §D regex `^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$` (P2:120-121, 237). Pure regex, rejects `__`, edge `_`, digit-lead, single char. Fail-closed. (E7 verified.)
- **Stopword strip / dedup / empty checks** §C steps 4,6 (P2:131-151). Pure set ops. Fail-closed with named rejections.
- **Banned-content + state-in-name gate** §C step 7 (P2:154-158) against §F.7/§F.5 exact-match sets. Deterministic for *known* tokens.
- **Reuse cascade** B3-B8 (P2:41-69): exact-name → exact-alias → canonical-name → canonical-alias → sorted-token (gated on all-known tokens). Each step is an exact lookup; B8 explicitly SKIPs if any token unknown (P2:67). Fail-closed.
- **Ambiguity reject** R11f "if R1-R10 produce >1 unresolved candidate, reject as ambiguous" (R2:86) + B8 "zero or multiple matches → B9" (P2:69). This is the right fail-closed lever for ~100% accuracy.
- **Determinism via frozen VocabSnapshot** (P2:85-88): `canonicalize()` takes vocab as a parameter, zero DB reads. Same `(candidate, snapshot)` → same output. The purity claim holds on disk.
- **Clean hand-off** E16 (P2:545-582): self-contained JSON; no reverse dependency on writer internals. Verified by reuse-map. NOT a finding.

The findings below are the places where reliability is ASPIRATIONAL, not mechanical.

---

## FINDINGS

### REL-1 (BLOCKER) — `classify_token()` has no defined body; novel-token slot classification is undefined → not deterministic

`canonicalize()` step 9 calls `classify_token(t, vocab.slot_vocabs)` for EVERY token (P2:166), including novel
tokens. The function body is **never defined** in P1, P2, or P4 (grep: only the call site at P2:166 and the
Conformance-Index row P2:501). For a KNOWN token it is a dict lookup into `slot_vocabs` — deterministic. For a
NOVEL token (one not in any slot vocab, not in registry), there is no mechanical rule for what slot it gets.
The ONLY governing text is R11(c) / new-token-gate clause (c): *"token's slot is unambiguously determined by
its position in the proposed name relative to known tokens and SLOT_ORDER"* (P2:262, R2:83). "Unambiguously
determined by position" is asserted, never implemented — there is no algorithm that maps position → slot.

Why this breaks a hard condition: this is the exact accuracy-critical path. The plan ITSELF admits TIER-1
cold-start seed does NOT cover OBJECTS/CUSTOMERS/THEMES slot anchors (P1:177), so in early production the
novel tokens that most need classification have the fewest known-token anchors. With no mechanical
position→slot rule, two LLMs (or one LLM twice) can assign the same novel token to different slots → different
canonical name → either a duplicate Driver or a divergent reuse. That violates condition 1 (~100% accuracy) and
the determinism contract B-M1 (R2:5) the plan rests on.

Minimal fix: define `classify_token()` concretely. Either (a) a deterministic position→slot inference: "the
novel token takes the lowest-index unfilled slot in SLOT_ORDER that lies between its left known-neighbor's slot
and right known-neighbor's slot; if that interval is empty or contains >1 slot, REJECT as
`ambiguous_novel_token_slot`" — fail-closed; OR (b) require every `propose_new_drivers[]` entry to carry an
explicit slot per novel token and validate it. Without one of these, the "deterministic" claim is prose.

---

### REL-2 (MAJOR) — `order_by_slot()` and `effective_slot_count()` bodies undefined; the R3 "reorder = same name" determinism rests on them

`order_by_slot(classified)` (P2:169) and `effective_slot_count(reordered)` (P2:174) are invoked but never
defined. R3 (R2:45) makes strong determinism claims that depend entirely on these: "reorder = same name,"
"earlier slot wins on collision," "at most one token per slot," "two tokens to same slot = REJECT." The
canonicalize() pseudocode does NOT implement the collision check or the same-slot reject — step 10 just calls
`order_by_slot` and step 11 checks metric-presence + length, but there is no step that detects "two tokens
classified to the same slot → REJECT" (the R3 rule at R2:45 / DriverOntology.md:45). The reject only lives in
prose, not in the function.

Why major: if `order_by_slot` is a stable sort keyed on SLOT_ORDER it gives reorder-invariance for distinct
slots, but the same-slot-collision REJECT (a fail-closed lever) is missing from the executable path. An
implementer could silently keep both same-slot tokens (producing e.g. `revenue_sales` with two metrics) or
drop one non-deterministically. `effective_slot_count` undefined means R8's length bound (a deterministic
reject per R2:68) is also unspecified — does a compound metric count as 1 (R2:68 says yes) and does an unfilled
slot count as 0? Not pinned in code.

Minimal fix: add explicit canonicalize steps: after classify, "if any two tokens share a slot → REJECT
`two_tokens_same_slot`"; define `order_by_slot` as a stable sort on SLOT_ORDER index; define
`effective_slot_count` = number of distinct filled slots (compound metric = 1 slot). These mirror R3's prose
1:1 and make the reject fail-closed.

---

### REL-3 (MAJOR) — Step-2 multi-token substitution uses raw `str.replace()` (substring, not token-aware) → non-idempotent / order-sensitive; defeats R3's "order-independent" claim

§C step 2 (P2:123-125):
```
for k, v in sorted(vocab.multi_token_subs.items(), key=lambda kv: -len(kv[0])):
    candidate = candidate.replace(k, v)
```
This runs on the raw `candidate` string BEFORE tokenization (step 3), using Python `str.replace()` which is a
**substring** replace, not a token-boundary replace. Two concrete hazards:

1. **Partial-token corruption.** With `multi_token_subs = {data_center → datacenter, gross_profit →
   gross_margin}` (P2:333-335), a candidate like `metadata_center_revenue` would have `data_center` matched as a
   substring inside `metadata_center` → `metadatacenter_revenue`. Substring replace has no `_` boundary guard.
2. **Order/overlap sensitivity.** Longest-match-first ordering (P2:124) only partially mitigates this; with
   overlapping keys the result depends on replace order, and `str.replace` replaces ALL occurrences, so a key
   appearing twice transforms both — not necessarily what a token-level fold intends.

Why major: R3 (R2:45) and the v3-1 determinism claim (P2:85) promise canonicalize is order-independent and
idempotent. `str.replace` on the pre-tokenized string is neither boundary-safe nor guaranteed idempotent if a
substitution's output can itself contain another key's input. This is a latent divergence/corruption path that
the spec presents as deterministic.

Minimal fix: tokenize FIRST, then apply multi-token subs as a token-window match (match against `_`-joined
contiguous token runs, anchored at token boundaries), or require keys/values to be whole-token sequences and
match on the token list rather than the raw string. Add an idempotency assertion in tests:
`canonicalize(canonicalize(x)) == canonicalize(x)`.

---

### REL-4 (MAJOR) — The `verb_form` ban regex `/^[a-z]+(ed|ing)$/` is an LLM-uncontrolled, vocab-dependent classifier that can both over- and under-reject novel tokens → non-deterministic across snapshots

§F.7 `verb_form` (P2:423-425): bans any token matching `/^[a-z]+(ed|ing)$/` UNLESS it is in OBJECTS ∪ METRICS ∪
COMPOUND_METRICS ∪ GEOGRAPHIES ∪ INSTITUTIONS ∪ THEMES ∪ CUSTOMERS ∪ ALLOWED_VERBAL_FORMS. This is the only
banned category that is a REGEX over arbitrary tokens rather than an exact-match set, so its behavior depends on
the live slot-vocab contents at snapshot time. Consequences:

- **Over-reject (false positive):** a legitimate novel object/theme token ending in `-ed`/`-ing` that is NOT
  yet in any slot vocab (e.g. a new product codename, `processing`, `bookings` is plural-mapped but
  `outsourcing`/`onshoring`-style theme nouns) gets banned, killing the tag — non-deterministic because whether
  it is banned depends on whether the token was previously promoted into a slot vocab (which is PIT- and
  history-dependent). The same evidence at two different registry states yields ban vs allow.
- **Under-reject (false negative):** a genuine state verb the author coined that does not end in `-ed`/`-ing`
  (e.g. `cut`, `beat`, `rose`, `fell`) is NOT caught by this regex at all — it relies on the exact-match
  STATES_VOCAB §F.5 to catch it, so any state verb outside §F.5 sails through into the name.

Why major: this defeats B-M1 determinism — the ban outcome for a novel `-ed/-ing` token is a function of mutable
vocab membership, so "same evidence + different registry state → different result" is possible, and that is the
one thing the determinism contract forbids. It is also an accuracy ceiling: state verbs not in §F.5 are
silently admitted into names.

Minimal fix: make the verb_form decision independent of mutable slot-vocab membership — gate it only against the
*frozen seed* allowlist (§F.9 ALLOWED_VERBAL_FORMS), and treat any *novel* `-ed/-ing` token (not in seed
allowlist, not in seed slot vocab) as a fail-closed REJECT requiring an explicit proposal, not a
runtime-vocab-dependent pass. Separately, expand §F.5 or add a morphological state-verb check so non-`-ed/-ing`
state verbs are caught.

---

### REL-5 (MAJOR) — R11(c) "slot unambiguously determined by position" is the ~85%-capped LLM judgment L3 says to exclude; no Python gate enforces "unambiguous"

The new-token gate clause (c) (P2:262, R2:83) is the admission rule for novel tokens. It says the slot must be
"unambiguously determined by its position." But there is no validator (V1-V15) and no canonicalize step that
COMPUTES whether the position is unambiguous and REJECTS when it is not. V14 (P2:287) just says "the §D
new-token gate passes" — circular, since the gate's (c) is the undefined part. So in practice the LLM author
decides the slot and the system trusts it. That is precisely the LLM-head canonicalization L3 forbids
("Canonicalization runs in Python, NEVER in LLM head. Determinism. LLM judgment caps at ~85%." — P1:25) and the
§7 rejected-suggestion "Just trust the smart LLM for canonicalize — Violates L3" (P1:457).

Why major: the plan's own architecture says slot assignment must be mechanical; for novel tokens it is not, so
the layer silently violates its own L3 lock exactly where accuracy is hardest. This is the mechanism behind
REL-1; called out separately because it is a *self-consistency* failure (the spec contradicts its own lock),
which an implementer must resolve before coding.

Minimal fix: same as REL-1 — implement a deterministic ambiguity test in Python; if the novel token's slot is
not uniquely pinned by its known neighbors, REJECT `ambiguous_novel_token_slot` (fail closed) and let Lever #3
informed-retry ask the LLM to re-phrase. Never let the LLM's slot choice be authoritative.

---

### REL-6 (MAJOR) — Standalone-shortcut admission has a known deadlock-driven recall/integrity trade-off that is NOT fail-closed; single emissions of a real new shortcut can mint a Driver on weak gates

Pattern B (P2:466-469) registers shortcut Drivers directly on `is_shortcut=true` with gates: shape +
banned-content + zero-slot-classifying-tokens + ≥2 underscore tokens (v7-2) + R11 evidence. The spec explicitly
documents (P2:469) that there is NO N=2 confirmation for shortcuts because of a deadlock ("first emission of a
real new shortcut has no Driver yet ... infinite loop"), and calls the current gate "the production trade-off
... Documented + accepted recall/integrity trade-off." So a shortcut Driver can be created from a SINGLE
emission if it clears those purely-syntactic gates — there is no semantic check that the multi-word phrase is
actually a standard macro/regulatory/corporate-action shortcut vs an LLM-invented bigram (e.g. `winter_demand`,
`china_tension` would pass shape + ≥2-token + evidence). The ≥2-token gate only blocks single-word
hallucinations (`winter`, `crash`), not plausible-looking 2-token inventions.

Why major: this is the one creation path that can mint a NEW Driver on the weakest gate in the system (no N=2,
no slot grammar, no synonym fold). It directly threatens the ~100% accuracy bar and registry pollution
(risk K59, durability gate B-R11e). The trade-off is *documented* but not *fail-closed* — it admits rather than
rejects under uncertainty.

Minimal fix: make shortcut admission fail-closed by adding a semantic anchor that does NOT deadlock — e.g.
require the exact shortcut phrase to appear verbatim (case-insensitive) in the evidence text (you already do this
for slot-token new-token gate clause (e), P2:264) AND require the phrase to NOT classify cleanly under the slot
grammar (already have zero-slot gate) — but ADD: if any token in the shortcut IS a known slot token, route to
the slot grammar instead of the shortcut path (prevents `china_tension` where `china` is a known geography from
becoming a shortcut). Document the residual recall loss as accepted, but reject-on-ambiguity rather than admit.

---

### REL-7 (MINOR) — Lever #1 auto-repair "exact-match-only commit" is fail-closed, but the period/magnitude strip can change the named variable's meaning without re-confirmation

Lever #1 (P2:593-595, P4:219-300) strips a smuggled period/magnitude/state token and re-canonicalizes, and
commits ONLY on an exact registry match (Fix #4) — that part is correctly fail-closed (new name → route to
retry, never auto-create). Good. The residual risk: the magnitude regex is narrowed to
`/^\d+(pct|bps|x|percent|basis_points)$/` (P2:594) to avoid stripping `5g`/`10yr`/`3nm`, which is sound, but the
strip-then-exact-match assumes the stripped token carried NO causal meaning. For a period strip
(`china_q3_sales` → `china_sales`) the exact-match guard protects integrity, but for a *state* strip where the
verb is genuinely part of a `_trend` semantic, the trend-partner preference (v3-3) only recognizes the `_trend`
suffix (P2:593) — any other legitimate level-vs-trend distinction is silently flattened to the bare metric.

Why minor: the exact-match-only commit prevents wrong Drivers from being *created*; worst case is a wrong
*reuse* of an existing bare-metric Driver when a trend Driver was meant, and only when that bare Driver already
exists. Bounded blast radius, fail-closed on creation.

Minimal fix: when a state strip would change level-vs-trend semantics and no `_trend` partner exists, route to
Lever #3 retry rather than committing the bare-metric exact match. (Largely already the behavior; tighten the
wording so "exact match on bare metric" does not auto-commit when the stripped verb was a `trend_motion` class.)

---

### REL-8 (MAJOR) — The "~96-98% accuracy" headline is an unmeasured projection over a ≥90% enforced bar; the user's ~100% target is not mechanically demonstrated (overstatement)

P1:883 states "Accuracy after applied: ~96-98% projection pending Q1 measurement (up from ~87% v8 baseline)."
The enforced hard condition is ">90% driver naming accuracy — credibly achievable, not aspirational" (P1:35),
and the production-smoke reuse rates are explicitly "initial estimates pending real-data calibration" (P1:742).
L3 caps LLM judgment at ~85% (P1:25) and the novel-token slot path (REL-1/REL-5) routes through exactly that
uncapped LLM judgment. So the 96-98% number is a forecast built on summed lever recoveries, none measured, over
a path that still contains undefined-and-LLM-delegated slot classification.

Why major (not minor): the user's condition is "as close to 100% as mechanically achievable." The plan presents
96-98% as if mechanical, but the mechanical floor is the ≥90% bar and the gap above it depends on the
unimplemented `classify_token` + the ~85% LLM cap. Per the anti-overstatement rule this must be flagged: the
projection is not supported by any measurement and rests on the very functions REL-1/REL-2 show are undefined.

Minimal fix: relabel 96-98% everywhere as an unvalidated projection; state the mechanically-guaranteed floor
(shape/banned/dedup/length/ambiguity rejects are deterministic; novel-token slot accuracy is LLM-bounded at
~85% until REL-1's mechanical classifier lands). Make REL-1's deterministic classifier the gating work item for
any accuracy claim above the ≥90% bar.

---

### REL-9 (MINOR) — Idempotency / order-independence is CLAIMED (R3, v3-1) but never asserted by a test or proof; one concrete divergence path exists beyond REL-3

R3 (R2:45) claims reorder = same name and v3-1 (P2:85) claims same input → identical output. There is no
idempotency assertion (`canonicalize(canonicalize(x)) == canonicalize(x)`) and no order-independence proof in
the spec. Beyond the REL-3 substring hazard, a second divergence path: step 5 applies acronym → plural →
synonym maps in a FIXED per-token order (P2:138-140), but if a token is BOTH a plural-map key and a synonym-map
key with different targets, the outcome depends on that fixed order — fine as long as the maps are disjoint, but
nothing in the spec asserts disjointness of §F.2/§F.3/§F.4 key sets. Two independently-grown vocab snapshots
(from different observation orders via the N=2 promotion path) could have overlapping keys and diverge.

Why minor: the seed maps are currently disjoint by inspection (§F.2-F.4), and the PIT-filtered promoted folds
are gated; the risk is latent, not active at seed.

Minimal fix: add a snapshot-build invariant that the key sets of synonym/plural/acronym maps are pairwise
disjoint (reject snapshot build otherwise), and add the idempotency test to the Day 6-7 adversarial suite
(P1:800) which currently lists "canonicalize edge cases" but no idempotency check.

---

## COVERAGE OF THE TASK'S NAMED SUB-AREAS

| Sub-area the task names | Deterministic? | Finding |
|---|---|---|
| Slot classification of novel/unseen tokens | NO — `classify_token` body undefined | REL-1 (blocker), REL-5 |
| Position-based slot inference + zero-anchor reject | Partially — zero-anchor reject exists (`slot_anchor_unavailable` P2:453); position rule undefined | REL-1; zero-anchor reject itself is clean |
| Cold-start-seed dependency | Documented gap (no OBJECT/CUSTOMER/THEME anchors P1:177) | feeds REL-1/REL-8 |
| Standalone-shortcut gate | NO — accepted recall/integrity trade-off, not fail-closed | REL-6 |
| Plural/synonym/acronym at creation time | Mostly — exact-match maps; but substring-replace + non-disjoint-key hazards | REL-3, REL-9 |
| Compound-metric detection | Substring-replace hazard | REL-3 |
| ~85% LLM-judgment cap | Hit on novel-token slot path, contradicting L3 | REL-5, REL-8 |
| Ambiguity-rejection (R11f "more than one unresolved candidate → reject") | YES — fail-closed (R2:86, B8 P2:69) | clean (no finding) |
| canonicalize idempotent & order-independent (R3 claim) | CLAIMED, not proven; one substring path + one map-overlap path | REL-3, REL-9 |
| Where two LLMs diverge | Novel-token slot assignment; shortcut bigram invention | REL-1, REL-5, REL-6 |

## CLEAN (no finding emitted, with evidence)

- Shape regex E7/§D (P2:120,237) — deterministic, fail-closed.
- Banned/state/stopword/dedup exact-match gates §C 4,6,7 (P2:131-158) — deterministic for known tokens.
- Reuse cascade B3-B8 (P2:41-69), B8 all-known-token guard — fail-closed.
- R11f ambiguity reject (R2:86) + zero-anchor reject (P2:453) — fail-closed.
- Frozen-VocabSnapshot purity (P2:85-88) — verified.
- E16 hand-off (P2:545-582) — self-contained, no reverse ingestion dependency.
