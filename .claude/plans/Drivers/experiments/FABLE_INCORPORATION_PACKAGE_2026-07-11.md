# Incorporation Package — v1

For item-by-item review; nothing edited.

All 20 items. Fields per item:

- W = exact proposed wording
- F = file/section
- R = replaces/amends
- Y = why
- K = locked-key/experiment impact
- M = new machinery

---

## Part 1 — Naming & slice rules

### INC-01 · NAME-16 #4 replacement (T1-03)

W: 4. the reporting company's own name/brand (redundant — the fact already
links to the company), and any incidental co-mentioned entity adding no causal
specificity (an analyst, executive, law firm, or counterparty named in
passing) [OK: an external company, platform, institution, or person whose own
independent action or state IS the stated cause (NAME-11 test 2): fed_rate,
opec_supply, fda_approval, walmart_price_cuts, aws_outage, tiktok_ban]

F: 02_DriverCatalog.md NAME-16, list item 4.

R: Replaces: 4. any ticker/legal/person name [OK: institutions/regulators as a
cause: fed_rate, opec_supply, fda_approval]

Y: Provable self-contradiction: NAME-11's locked customer pin blesses
walmart_price_cuts; NAME-16 #4's literal text bans it.

K: None on locked keys (K-reader v3 has zero self-naming leaks —
corpus-verified). Requires prompt re-sync (INC-19).

M: None. Reversal of locked text → 95 row (INC-18).

### INC-02 · 09 §7 series-key rider (T1-03 rider)

W: Insert period_scope after period: company · driver · fact_type · slice ·
period · period_scope · measurement · series_unit · time_type.

F: 09_DriverUpdate_Fields.md §7 read-contract sentence.

R: Amends the tuple that today omits period_scope.

Y: 12 FACT-33's key includes it; a builder reading 09 alone would reproduce
the quarter-vs-YTD collision FACT-33 exists to fix.

K: None.

M: None.

### INC-03 · New OD-17 row (T1-01 core)

W: OD-17 — Portion qualifiers stay in the NAME. A qualifier naming which
PORTION of the company's own measured quantity is counted — not one of the six
slice kinds, not a period window, not a measurement version — stays in the
Driver name (current_rpo, fee_earning_aum, funded_backlog). A
differently-qualified portion is a DIFFERENT Driver, never SAME_AS the bare
form. Unclear window-vs-portion → keep it in the name; never drop it.
Sub-rules: (a) aggregates population test, (b) residual buckets, (c)
accounting constructs — texts in 02 NAME-11 note. Back-ports: 02 NAME-11 +
NAME-14 mirror · 03 FS-25/FS-07/FS-10 · PIPE-16 re-sync · K-fields trap.

F: 66_IssuesToBeHandled.md §0.R (OD-9/OD-12 row format).

R: Pure addition.

Y: Nothing pins routing for portion words; producers fork or drop (drop =
permanent value over-merge).

K: Zero footprint in K-reader v3 (0/1,175) and K-pairs v1.3 (0 pairs —
coverage gap fixed via INC-20).

M: None.

### INC-04 · NAME-11 OD-17 note, four parts (T1-01 core + a/b/c)

W (core — tracker RECORDED text, survived panel): Portion qualifiers (OD-17):
a qualifier naming which portion of the company's own measured quantity is
counted — and that is not one of the six slice kinds, not a period window, and
not a measurement version — stays in the NAME (current_rpo, fee_earning_aum,
funded_backlog). Different portion = different driver, never SAME_AS the bare
form. If unclear whether a word is a window or a portion, keep it in the name;
never drop it.

W (a — my rewrite, owner-approved in principle): All-parts aggregates
(population test): a stated aggregate maps to FS-10's omitted slice ONLY when
its population is the consolidated reporting entity ("total company",
"consolidated", "group"). An aggregate crossing the ownership boundary or
curating a subset is NEVER the omitted slice: network/system aggregates
(systemwide_sales, gmv, total_payment_volume) are their own whole-phrase
Drivers (NAME-08 posture); curated subsets ("core operations", ex-items,
pro-forma combined) keep their qualifier — never mapped to the consolidated
series.

W (b): Residual buckets: a company-stated residual ("Other", "Rest of World",
"Corporate unallocated") is a LEGAL slice value of its stated kind
(segment:other) — never a name token, never dropped. Residuals are
company-specific and composition may drift: see the FS-07 note for the guards.

W (c): Pure accounting constructs (eliminations, fair-value levels,
reconciling items) are excluded as slice values AND as Driver names — never
coin an eliminations Driver. Drop-and-log (FS-20's log). An
eliminations-driven mover is recorded as a fact on the AFFECTED reported
metric (e.g. operating_income, lane state, quote carrying the eliminations
mechanism) — evidence is never dropped.

F: 02_DriverCatalog.md, appended note under NAME-11 (same pattern as NAME-08's
OD-12 note).

R: Addition.

Y: (a) fixes the FATAL systemwide over-merge (MCD systemwide ~$130B vs
consolidated ~$25B); (b) 11/40 sampled breakdown rows are "Other"-type; (c)
closes the name-path hole NAME-18 wouldn't catch, and satisfies your
route-don't-drop requirement.

K: K-reader v3 already treats systemwide_sales as its own driver — (a)
confirms the locked gold; zero rework.

M: None.

### INC-05 · FS-25 boundary sentence + NAME-14 mirror

W (byte-identical in both places): A measurement word re-expresses the SAME
quantity through a different lens; a word that changes WHICH portion is
counted is never a measurement token — it belongs in the name (OD-17).

F: 03_Slices_FactScope.md FS-25 (after the OD-9 pins) and
02_DriverCatalog.md NAME-14 rule end.

R: Addition.

Y: NAME-14's open-ended list could otherwise claim "current".

K: None.

M: None.

### INC-06 · FS-10 cross-reference

W: An aggregate qualifies for the omitted slice only under OD-17's population
test (population = the consolidated reporting entity); cross-ownership network
aggregates and curated subsets never do.

F: 03_Slices_FactScope.md FS-10, after "…→ omitted slice."

R: Addition.

Y/K/M: as INC-04(a); none; none.

### INC-07 · FS-07 note (residual guards, honest version + eliminations plumbing)

W: Note (OD-17 b/c): company-stated residual buckets ("Other", "Rest of
World", "Corporate unallocated") ARE legal slice values of their stated kind.
Prose-coined residuals carry no PROVISIONAL flag (FS-20 classifies XBRL
members only); what keeps them safe today is company-in-key + the unbuilt
FS-23 layer — when FS-23 is built it MUST exclude residual values from
cross-company folding. A residual's composition may change as items are broken
out: read views label residual-value series non-continuous across periods.
Pure accounting constructs stay excluded — as slice values AND as Driver names
— dropped + logged via FS-20's existing log; the mover routes to the affected
reported metric (02 NAME-11 note c).

F: 03_Slices_FactScope.md FS-07 (+ the one FS-23 forward-requirement sentence
inline at FS-23).

R: Addition.

Y: The tracker's guard chain was partly fictional for prose residuals; this
states the real guards.

K: None.

M: None (labeling rides INC-16's read views).

### INC-08 · NAME-06 singular-by-default note (T1-04)

W: Tracker RECORDED reader-rule text verbatim (SINGULAR BY DEFAULT… say the
singular out loud…) plus one added sentence: The exception list is
illustrative, never exhaustive — the say-it-out-loud test decides (NAME-19:
the principle, not the examples, is the rule). Judge rule (tracker RECORDED)
lands beside PIPE-31/D5 in 10_BuildPipeline.md and in the dedup prompt.

F: 02_DriverCatalog.md NAME-06 note; 10_BuildPipeline.md judge-rule note.

R: Addition (NAME-02 already declares plural variants one canonical form; this
says which).

Y: Highest-frequency preventable fork; the added sentence prevents the
under-inclusive 7-word list from misreading accounts_payable-class names as
violations (corpus found 41 such borderline records).

K: K-reader v3 keeps its 79 plural canonicals — judged alt-aware scoring
unaffected (corpus-verified zero breakage); optional cosmetic v3.1 deferred.

M: None.

### INC-09 · FS-15 slice-kind ladder (T1-05)

W: Tracker RECORDED 4-rung ladder verbatim (menu-first → menu-ambiguous →
unknown:<value> → prose-clear → prose-unclear → unknown:<value>; never guess;
unknowns enter the menu).

F: 03_Slices_FactScope.md FS-15 clarification block; same text verbatim at 12
§7 FACT-26; plus add 12 §7 FACT-26 slice-kind ladder to the EXP-5 packet
verbatim-assembly list in FableExperimentWorkOrder.md (line ~629 — a genuine
gap the mapper found: the list doesn't cite the ladder today).

R: Addition.

Y: FS-15's four outcomes don't cover ≥2-plausible-kinds or dual-axis menu
labels; a guessed kind fakes an axis-grade confirmation inside the fact id.
Your menu question: confirmed — FS-14 pins the PIT-cut menu (≤ event time,
union of prior filings), FS-19 shows it existing-values-first.

K: K-fields trap at drafting.

M: None.

### INC-10 · NAME-07 precedence clause (T2-09)

W: Precedence: the familiar short form applies only when the source does not
itself distinguish a specific named sibling instrument or benchmark within
that family; when the source names the sibling (SOFR vs the fed-funds family),
NAME-04 specificity wins — coin the specific form. Familiarity is a fallback
for undifferentiated mentions, never a license to flatten stated specificity.
(Commodity benchmarks are already locked by NAME-12(c).)

F: 02_DriverCatalog.md NAME-07.

R: Addition (precedence was unstated).

Y: Closes a within-rules over-merge channel on the highest-blast macro names.

K: K-reader v3 already compliant (sofr_rate, shrimp_tariff); one
sibling-instrument gold pair added at K-pairs' next version (INC-20).

M: None.

### INC-11 · OD-9 contiguity clarification (replaces T1-11)

W (byte-identical in 66 OD-9 row and FS-25 pins): Contiguity defined:
qualifier words separated only by punctuation or whitespace form ONE
contiguous span ("adjusted, diluted" ≡ "adjusted diluted" → adjusted_diluted);
a span splits only where non-qualifier prose intervenes ("adjusted … on a
constant-currency basis" → two spans).

R: Clarifies OD-9's undefined "contiguous"; changes no behavior OD-9's
back-port note already pinned.

Y: Kills the last punctuation ambiguity with zero new mechanism; T1-11
rejected.

K: EXP-5 punctuation-variant fixture at drafting.

M: None.

## Part 2 — Kernel (FableAdmissionKernelDesign.md)

### INC-12 · ATTACH-ESCALATE (OD-18) — four coordinated edits + one OD row

W (§2 Stage-1 header): STAGE 1 — the G2 router (ONE batched call per event
≤400/≤300k; ATTACH/CLAIM discrimination is identity work on the strong-judge
tier per §11.0 — CREATE/SKIP dispositions may run cheap where experiments
prove no loss)

W (§9.2 addition): SYNCHRONOUS (OD-18): the deterministic pre-filter runs AT
WRITE TIME; a flagged ATTACH is confirmed BEFORE the write by a blind
strong-judge 3-check (same cause + same causal scope + same mechanism vs the
head's frozen anchor; code-assembled, batchable per head). CONFIRM → write.
REFUSE → never overturned toward the write. UNSURE → one blind escalation-tier
re-judge; only its CONFIRM writes; anything else → the more-specific re-coin
path (the fact CREATEs now under NAME-18; no coinable distinguisher → the
existing vague-evidence TERMINAL skip, counted). Flag scoping: on heads with
gauntlet/skeptic-earned ESTABLISHED standing, only qualifier-heterogeneity
fires; the ≥8-company HIGH_BLAST flag extends to ATTACH on non-ESTABLISHED
heads. The post-write sampled audit continues unchanged. Counters (P7): flag
rate · refuse rate · escalation-disagreement rate · re-coin-failure rate.

W (§11.0 protected list): insert fact placement (an exact-name ATTACH onto an
existing head) into the enumeration.

W (§9.5 honesty rider): A published "0 wrong in n audited" bounds the
flagged/audited strata only; the unflagged stratum is bounded pre-launch
(gauntlet + EXP-3 fixture families incl. same-industry mechanism-drift
homonyms + one pre-registered unflagged sample) and monitored by the §9
detectors.

R: Rewords §2's "ONE cheap call" (the F1 self-contradiction); §9.2
detection→prevention; §11.0 is a pure addition to the enumeration (my
judgment: no 95 row — flagged for your review); §9.5 addition.

Y: Mis-ATTACH is the one irreversible error; merge now requires zero refusals
(the one law dominates the escalation ladder); ESTABLISHED-badge scoping is
the no-list exemption.

K: EXP-3 arm + measurements (INC-20); nothing locked is touched.

M: No new components — a re-timing and scoping of existing checks, plus four
counters.

### INC-13 · Fact-level dispute (T1-09)

W (§10 new item): Fact-level dispute: a single fact confirmed mis-attached
(any §9 detector → the §10 two-grader blind confirm) is marked disputed=true —
a reversible, non-identity metadata boolean: that ONE fact is excluded from
cross-company/history-weighted features; the head, its other facts, and
event-level reads are untouched; the fact never moves. Set/unset only through
this lane; every flip emits a RecoveryEvent; V14 validates. Plus: V14 wording
extended to cover the boolean; one X-IM mutation test added in §12; one-line
note in 09 §3: disputed (boolean, recovery-lane metadata — set only by §10
machinery, never by producers; outside the producer contract).

R: Addition (S10 has edge and node lanes only — verified gap).

Y: Your "only the bad fact" requirement, met without touching the Driver.

K: None.

M: One stored boolean; zero new judges/lanes.

### INC-14 · Token-subset narrowing (OD-19, gated)

W (§6.1): delete the TOKEN-SUBSET bullet from the PERMANENT-BY-LOCKED-RULE
list; add to judge-territory: Token-subset pairs are judge territory: proposed
pairs go to the LINK judge immediately — never auto-refused, never deferred.
Upstream PERMANENT refusals unchanged: per-X, cross-flavor, terminal-suffix. A
portion-qualifier superset (OD-17 test) is always DIFFERENT — a locked judge
instruction. EFFECTIVE-WHEN: this narrowing takes production effect only after
K-pairs.v2's portion family passes EXP-0-style grading with wrong-same = 0.

R: Reversal of locked kernel text ("PERMANENT, no-judge-recourse") → 95 row
(INC-18).

Y: 25% of measured token-subset pairs are true synonyms frozen forever today,
contradicting "over-split is repairable"; no ledger, no recheck-later — pairs
are judged when proposed.

K: Gated on K-pairs.v2 (INC-20); nothing locked mutates.

M: None (removes a rule).

### INC-17 · §9.6 honesty reword

W: replace (and discounts every "confirmed clean" by exactly that rate) with
(measured and reported for interpretation and escalation; not automatically
applied as a discount in any gate — deliberate owner decision, T1-08 rejected
2026-07-11).

R: Amends one unenforced promise sentence.

Y: Doc must not promise math no gate performs.

K/M: None; none.

## Part 3 — Continuity & read views

### INC-15 · CONTINUES_AS (OD-20)

W (new subsection, proposed home 03_Slices_FactScope.md §J, cross-refs in 07
DU-20 and 12 §9): CONTINUES_AS — a company-scoped, directional, dated
continuity declaration: old → new, created ONLY when company text explicitly
asserts the old label/name continues as the new with composition/methodology
unchanged (a stated recast or any composition-change language BLOCKS it).
Judge-confirmed at creation (LINK-judge tier), evidence-anchored {company,
kind, old, new, evidence_quote, declaring_event, created}; reversible
(quarantinable). Storage: driver-name endpoints = a CONTINUES_AS relationship
between Driver nodes carrying the company scope; slice-label and
measurement-token endpoints = a reified per-company ContinuationClaim record
(strings inside fact_scope cannot anchor edges). Binds to the EXACT declared
endpoint only — never propagated across _guidance/_surprise, family, or
BASE_METRIC links (cross-flavor permanent refusal applies unchanged). FAN-IN
GUARD (deterministic): within one (company, kind), a second distinct old
declaring into the same new auto-refuses/quarantines both — suspected
undeclared recomposition; keep split. Consumed ONLY by labeled read-time
reconciled views, PIT-gated on the DECLARING event's date (< as_of). Where an
endpoint is XBRL-backed, the §9 falsifier runs as a tripwire across the
declared boundary; for no-XBRL endpoints the false-continuity residual is the
documented §16 class. Never a write-time merge; stored ids/facts untouched.
Subsumes tracker T2-02 and T2-05.

R: New definition (no existing anchor anywhere — verified).

Y: The only healer for the ~57% of facts with no XBRL member link and for
declared renames; your clarification validated with the four pins above.

K: None locked; future fixture at K-fields/EXP-5 drafting optional.

M: The one genuinely new machinery in the package: one edge type + one record
type + the fan-in check. Everything else it uses (judge, quarantine,
RecoveryEvent, PIT reads) exists.

### INC-16 · Narrowed read-view framework (T2-01 final)

W (12 §9, FACT-35 area): Reconciled read views (narrowed): every query result
is labeled raw or reconciled; reconciled views are deterministic at read (no
model calls), instantly disabled per instance, and PIT-cut (in backtest mode an
edge/claim applies only if its declaring event date < as_of). Exactly two
instances: (1) CONTINUES_AS chains (§J of 03); (2) deterministic qname→kind
grouping for unknown:xbrlaxis_<hex>__<member> slices whose hex-decoded axis now
sits in the frozen table — grouping only, the stored fact and id never change.
No other instance exists without a fresh owner decision. Plus a one-line
raw/reconciled label note at 09 §7.

R: Addition.

Y: Kills the T2-06 write-path fatality while healing vintage inequality; the
look-ahead leak is closed by the PIT-cut clause.

K: None.

M: Read-layer logic only; no write path, no schema.

## Part 4 — Process & bindings

### INC-18 · 95_Supersession rows (2)

W: one row: NAME-16 #4 old text → external-actor principle (INC-01); one row:
kernel §6.1 TOKEN-SUBSET permanent auto-refusal → judge territory, gated
(INC-14). Flagged judgment call for your review: §11.0's protected-list
insertion is a pure addition — I recorded no row.

### INC-19 · Prompt re-sync round ("WP-FC-EDITS-2")

W: regenerate the three inlined rulebook blocks — workflows/menu_build.js
(RULES), gate.js, reconcile.js (RULEBOOK) — from the edited 02, byte-identity
md5 re-verified, 260-test suite re-run, board entry. Touched by
INC-01/03/04/05/08/10 only.

Y: PIPE-16 makes this mandatory; it is the one hard blocker before EXP-2
restarts.

K: This is the EXP-2 prerequisite.

M: None.

### INC-20 · Experiment bindings (land at drafting, no current edits)

W: (a) trap_class enum in FableExperimentWorkOrder.md line ~415 gains
OD-17_portion and T1-05_menu_ambiguous; (b) EXP-3 gains the ATTACH-ESCALATE
primary arm + flag/refuse/disagreement/re-coin-failure measurement +
same-industry mechanism-drift fixtures + one pre-registered unflagged sample
(measurement, not a live gate); (c) K-pairs next version adds the portion
family (gold-DIFFERENT current_rpo/rpo, funded_backlog/backlog + one
window-vs-portion trap — gates INC-14) and one sibling-instrument pair
(INC-10); (d) K-fields/EXP-5 packets bind INC-09/INC-11 fixtures. K-reader v3:
no change (locked, verified valid; optional cosmetic v3.1 stays deferred).

---

## Impact summary

No locked key or completed experiment is touched by any item; the only
pre-EXP-2 blockers are the doc edits + INC-19.

Machinery summary: 18 of 20 items add zero components; INC-13 adds one
boolean; INC-15 is the package's single new mechanism (one edge + one record +
one deterministic guard).

Review at will — on owner approval (full or per-item), apply exactly the
approved subset, in the sequencing order already agreed, and nothing else.
