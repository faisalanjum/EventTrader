# Fable Lock-Blind Verdict - 2026-07-10

Captured verbatim from the owner-provided Fable response. This is the current transcript for review.

FABLE SAID:  The lock-blind verdict

No architectural pillar should be replaced — and that's now a stress-tested
conclusion, not deference. All 15 agents independently tried replacement
candidates for every pillar (closed vocabulary, surrogate ids, LLM-merge,
code-deciding-meaning, collapsed fact_type) and every one loses on evidence,
mostly your own recorded deaths (v1's 82% valid-name rejection; v2's
99%-looks-clean/29%-actually-right). But the ideal design is NOT the current
design. After 3 adversarial rounds, 17 changes survive (11 identity-integrity,
6 recall-healing), 6 of my own candidates died (including 3 I proposed last
turn — P3, P4, P10 were net-harmful), and the deepest finding is one nobody
had stated plainly before:

▎ The design's one physically irreversible error is a mis-ATTACHed fact (fact
▎ ids embed the driver name; facts never move; SAME_AS edges are reversible
▎ but fact placement is not) — yet ATTACH is confirmed by the cheapest model
▎ in the pipeline, and §11.0's own locked law ("cheap never final-confirms
▎ identity") already forbids that if read honestly. Everything else in the
▎ change list follows from taking your goals literally: precision holes get
▎ pre-write guards, and recall holes get repair paths — because "over-split is
▎ cheap" is only true if the repair path actually exists, and today several
▎ don't.

The two rule wordings you asked for (red-team-amended, final)

FS-06a — Portion qualifiers (fail-closed to the name):

▎ A stated qualifier that narrows which portion of the company's own measured
▎ quantity is counted — and is not one of the six slice kinds, not a period
▎ window, and not a measurement version — denotes a different quantity and
▎ therefore stays in the driver name (current_rpo, fee_earning_aum,
▎ funded_backlog, rpo_ntm). Different portion-qualifier = different driver;
▎ never SAME_AS the bare form. Fail-closed boundary: if it is unclear whether
▎ a word is a measurement window over a flow (→ period, per FS-25/OD-9) or a
▎ portion-selector on a balance (→ name), keep it in the name; never silently
▎ drop it (dropping merges the portion into the whole — the forbidden
▎ direction). State the principle only — no sector example lists (NAME-19).
▎ Exceptions: (i) explicit all-parts aggregates ("system-wide", "total
▎ company") = the omitted slice; (ii) company-stated residual buckets
▎ ("Other", "Rest of World") are legal slice values of their stated kind, kept
▎ out of cross-company grouping by FS-20/FS-24/FS-23; (iii) pure accounting
▎ constructs (eliminations, fair-value levels) stay excluded per FS-07,
▎ dropped + logged.

NAME-08a — Canonical financial spelling (canonicalization-only):

▎ A universal, single-referent financial metric has exactly ONE canonical
▎ snake_case spelling, held in a small frozen table (~30–60 entries: eps,
▎ ebitda, ebit, ebt, capex, arr, rpo, aum, …); coin that form under any source
▎ spelling. Three hard limits: (1) it rejects nothing — unlisted metrics coin
▎ normally, misses fall to dedup/SAME_AS; (2) it merges nothing beyond
▎ spelling — any narrowing-qualified form (net_, current_, fee_earning_) or
▎ window-prefixed form (dau/mau) is OUT of the table and owned by FS-06a /
▎ NAME-14 / period_scope; (3) consistency pin — where NAME-07/08 already fix a
▎ form (free_cash_flow, net_interest_margin), the table reuses that identical
▎ form, never a competing abbreviation. Tie-break: NAME-14 > (NAME-08 ≡
▎ NAME-08a) > open coinage — "Adjusted EBITDA" is ebitda +
▎ measurement=adjusted, always.

Tier 1 — identity integrity (adopt; each closes a permanent-error or
convergence hole)

#: 1
Problem → new rule: FS-06a above — portion qualifiers had no home (neither
slice kind, period, nor measurement); producers fork or drop the word (a
silent over-merge)
Cons: more driver names (over-split-safe)
Changes: 03 (new FS-06a), NAME-19-conformant
Experiments that must use it: K-reader/K-fields drafting (both still PENDING),
EXP-5 producer contract
────────────────────────────────────────
#: 2
Problem → new rule: NAME-08a above — lexically distant universal synonyms
(ebitda vs spelled-out) are the one synonym class embedding-dedup can't
surface, and SAME_AS repair ships OFF
Cons: table upkeep; boundary policing (weakest survivor — kept because nothing
else covers it)
Changes: 02 (new NAME-08a)
Experiments that must use it: K-reader gold names; EXP-2 reader rules block;
WP-FC-RUN prompts
────────────────────────────────────────
#: 3
Problem → new rule: NAME-16 #4 contradicts NAME-11's own examples (bans "any
legal name" while walmart_price_cuts/aws_outage/tiktok_ban are locked-valid)
— two honest producers diverge on the same locked text → replace carve-out
with the external-actor principle (ban only self-reference and incidental
co-mentions)
Cons: none of substance
Changes: NAME-16#4 + PIPE-16/17 re-sync
Experiments that must use it: every reader/G2/Refute prompt from now on
────────────────────────────────────────
#: 4
Problem → new rule: No singular/plural coining convention + norm() rightly
never stems → aws_outage vs aws_outages forks freely → coin singular by
default; standard-plural terms (earnings, bookings) stay whole
Cons: tiny prompt cost
Changes: new NAME rule
Experiments that must use it: K-reader, EXP-2, WP-FC-RUN
────────────────────────────────────────
#: 5
Problem → new rule: Undecidable slice kind: my P3 ("default to segment")
shipped a fake axis-grade confirmation → instead one line in FS-15: ≥2
plausible kinds = route to unknown:value (same constant → convergent AND
honest)
Cons: none
Changes: FS-15
Experiments that must use it: EXP-5 slice menus/scoring
────────────────────────────────────────
#: 6
Problem → new rule: ATTACH strong-confirm pre-write (amended P5): synchronous
strong 3-check whenever §9.2's risk flags fire (≥K companies, cross-industry,
OR scope/mechanism heterogeneity incl. same-industry), applied before the
write — §9.2's audit already covers these ~100% but only after the
irreversible placement. Exemption: NAME-08a universal metrics don't trigger
on cross-industry alone. Plus fix the §2/§11.0 wording: ATTACH/CLAIM
discrimination is confirmation work, not "routing"
Cons: latency/cost on flagged attaches
Changes: kernel §2, §9.2, §11.0
Experiments that must use it: EXP-3 must test the confirm-by-default shape (not
only as failure fallback)
────────────────────────────────────────
#: 7
Problem → new rule: Uniform-random baseline audit: risk-stratified auditing
bounds only the suspected stratum — the exact way v2 looked clean →
mandatory pre-registered random sample of UNFLAGGED links and attaches,
permanent non-zero rate, reported as its own population floor, never blended
Cons: recurring cost, low hit-rate by design
Changes: kernel §9.5, OD-6 discipline
Experiments that must use it: PIPE-37 and all live ops
────────────────────────────────────────
#: 8
Problem → new rule: Independence keyed to catchability (P6 rebuilt): the
2-grader/cross-vendor requirement fires on every identity-permanent approval
of a card with no model-free falsifier channel (no XBRL backing) — company
count is unrelated to catchability. Vendor diversity is a measured default
(calibration stream must show lower shared-miss than same-vendor lens-split),
never a hard-coded vendor rule; unavailability parks, never downgrades.
PIPE-37's gate grader joins the list, and the calibration shared-miss rate
gets wired into GREEN (§9.6 promises the discount; OD-6's formula never
applies it) + rotating held-out planted pairs
Cons: judge cost on qualitative claims; one more owner ceiling C
Changes: kernel §6.1/§6.5/§9.6, OD-6, PIPE-37
Experiments that must use it: EXP-0 informs vendor pairing; PIPE-37 protocol
────────────────────────────────────────
#: 9
Problem → new rule: Fact-level disputed flag: recovery units are edge and node
only — one caught mis-attach currently forces whole-node quarantine (dragging
correct sibling facts out of features) → per-fact exclusion via existing
RecoveryEvent/2-grader machinery
Cons: one more state
Changes: kernel §10, V14
Experiments that must use it: X-IM immune proofs
────────────────────────────────────────
#: 10
Problem → new rule: TOKEN-SUBSET refusals become reconciliation-eligible: real
synonyms can satisfy token containment (comparable_same_store_sales ⊃
same_store_sales) — a permanent refusal with no ledger entry is the design's
one deterministic unrepairable over-split → keep the free code refusal, route
it into the deferred-pair ledger for §6.6; and pin §6.6 into the Day-1 MVP
(it's absent from both MVP lists — yet the frozen-anchor safety argument
depends on it)
Cons: slightly wider §6.6 load
Changes: kernel §6.1, §6.6, §15.0
Experiments that must use it: S3/X-ladder scope
────────────────────────────────────────
#: 11
Problem → new rule: OD-9 tokenizer determinism: contiguous-vs-separated joining
makes adjusted_diluted vs adjusted,diluted — a punctuation-driven id fork →
uniform separator tokenization + code-sort always (multi-word idioms as
explicit entries); format-domain, so code may own it
Cons: idiom entries to maintain
Changes: 09 §3/OD-9, FS-25
Experiments that must use it: EXP-5 measurement scoring

Tier 2 — recall healing (one framework, read-time-only, reversible by
construction)

The asymmetry law ("over-split is cheap") currently lacks repair paths for the
majority of facts: measurement drift is "split by design", slice-label drift
heals only via member anchors (~57% of facts have none), series_unit=unknown
buckets never rejoin. So: one read-time reconciliation framework — recomputed
per read, never touches a stored id, every view labeled reconciled vs raw —
with four instances: (a) SLICE_SAME_AS via the existing LINK judge scoped to
(company, kind); (b) a small frozen measurement-equivalence table
(adjusted≡non_gaap…); (c) series_unit unknown→single-clean-axis fold; (d)
self-declared rename continuation ("renamed Core to Underlying, no change") .
Plus three small write-side integrity pieces: FS-12 exact-qname backfill on
each axis-table refresh (2024 facts stop being permanently poorer than 2026
facts); a value-change ledger (same quote + different values = park, never
silent overwrite — values deserve the detectability identity already has); the
axis_commitment_hint on a driver's first percent-family fact (same
transient-hint pattern as shape hints); and the one-sentence NAME-07
precedence pin (stated specificity — sofr vs fed_funds — always beats the
familiar umbrella).

Rejected — including three of my own from last turn

P3 kind-guess (launders a guess into axis-grade truth) · P4 coherence
validator (order-dependent; false-positives on DU-17's legal %-level +
bps-change) · P10 trigger words (v1 closed-list reborn; routes valid FS-06a
drivers into a reject) · INSTANCE_OF/part-of roll-up edges (P7-amended stands;
honest cost recorded below) · NAME-13 exact-conversion unit table (conversion
"exactness" is itself a risk; no consumer) · FS-09 coarsening nudge (I
overruled my own coherence agent here — defaulting to the coarser slice drops
a stated qualifier, which is the forbidden over-merge direction) · RECAST_TO
edge (deferred; member anchors already heal tagged recasts, and it's
semantically opposite to SLICE_SAME_AS — a confusion hazard).

The honest floor (what no design can give you)

Literal 100/100 with no human is not achievable and the perfect design doesn't
pretend: (1) a first-encounter qualitative homonym judged wrong by correlated
models has no independent tripwire — the falsifier hunt confirmed every
candidate oracle is confounded (P8 stands; tier-1 #7/#8 exist precisely to
bound and measure this floor honestly); (2) cross-company specificity variance
(resin_costs vs raw_material_costs for one shock) stays split at identity
level — exposure baskets are consciously served query-time or by the future
FS-23 value layer, never by identity edges; (3) silent adjective drift with no
self-declaration stays split (safe direction, visible in metrics).

Ideal design vs. experiment history — cleanly separable

Adopting all of this invalidates nothing already run: K-pairs.v1 gold is
SAME/DIFFERENT truth, unchanged by coining conventions, so EXP-0's grader
qualification stands; the still-pending keys (K-reader, K-fields, K-route —
all luckily undrafted) are where the new rules must bind; EXP-3's design
changes most (confirm-by-default arm + ATTACH baseline measurement); PIPE-37
gains the cross-vendor grader + shared-miss GREEN term. No file changes made —
this is the substance for your draft, and per your flow I'd put the Tier-1
list (especially #6, #7, #8 — the three that guard the irreversible class) at
the top of it.

## Owner Question Q-01 - Portion Qualifiers in Measurement

FABLE SAID:

Verdict: REJECT — portion qualifiers must NOT go in the measurement slot. Your
suggestion doesn't survive, but attacking it sharpened one rule sentence.

Reminder of the two options: A = portion in the name (current_rpo is its own
driver — my FS-06a). B = your suggestion: driver stays rpo, portion goes in
measurement (which already separates versions like adjusted).

Your instinct is reasonable — measurement already separates "versions of a
number," and the series key includes measurement, so values wouldn't mix at
read time. But it fails the gauntlet on four independent grounds, any one of
which is disqualifying:

1. One-law direction flips (the decisive kill)

Measurement's default is empty — and empty means "the plain total number." A
producer who misses the qualifier under Option B silently writes a portion
value into the total series — an over-merge, permanently placed (fact ids are
irreversible). Under Option A the same mistake surfaces where the defense
machinery lives: the current_rpo card exists, retrieval shows both cards, and
the ATTACH mechanism-check can catch "your quote says current portion but
you're attaching to rpo." Option B legislates that check away — fee-earning
and total become the same driver by rule, so the judge is forbidden from
refusing. The easy mistake must be the cheap mistake; Option B makes the easy
mistake permanent.

2. Measurement has zero identity machinery — names have all of it

Names get the full defense stack: G2 gate, dedup, Refute, D5, SAME_AS + judge,
retrieval cards, quarantine, gauntlet fixtures. Measurement tokens get none
of it — by locked design (OD-9): open vocabulary, format-normalized only,
never synonym-merged, and drift "stays split by design" (66 E7). So
{fee_earning} vs {fee_paying} vs {feeearning} (companies use all three) become
silently different series with no judge, no SAME_AS, no repair path, and no
visibility at the catalog layer. You'd be storing the exact distinction where
homonym damage lives — in the one slot with no guards.

3. It breaks the XBRL lane and concept-linking — structurally, not marginally

- Concept-linking's G2 guard keys on the measurement set: only GAAP-compatible
sets (∅, gaap, basic, diluted…) get linked. measurement={current} ⇒ the
linker abstains ⇒ every portion fact loses its concept link, and
_guidance/_surprise inheritance dies too (any non-GAAP token ⇒ no inheritance,
09 §3). To fix that you'd have to widen the GAAP-compatible set with portion
words — destroying the guard's meaning.
- XBRL itself encodes current/non-current as separate concepts (e.g.
AssetsCurrent vs Assets). The materializer emits measurement=∅ by
construction. So text-lane rpo|{current} and XBRL-lane facts can never produce
equal twin ids — the ≥99% twin-convergence bar becomes unreachable for the
whole class. Under Option A both lanes converge on driver current_rpo cleanly.

4. "Will it work as efficiently?" — No, it's a small saving for a large loss

Catalog size
A: in the name: ~10–15% more names in KPI-dense areas (measured: portion cases
were ~6 of 120 stress names)
B: in measurement: smaller
────────────────────────────────────────
Cross-company reuse
A: in the name: works — 31 companies say "RPO over NTM" verbatim → same coined
name
B: in measurement: card quotes become a total/fee-earning/current soup → the
anchor spans mechanisms → the kernel's own check-5 flags the head
un-claimable (a manufactured gravity well — the v2 death shape)
────────────────────────────────────────
Dedup/D5 load
A: in the name: no extra load — current_rpo vs rpo are different strings; bad
SAME_AS is auto-refused free by token-subset
B: in measurement: no name traffic, but unguarded token fragmentation instead
────────────────────────────────────────
Precedent
A: in the name: matches per-X (NAME-13) and benchmark (brent vs wti) —
identity-bearing modifiers already go to the name
B: in measurement: contradicts both precedents

And your last question — what specific changes would make B perfect — is
itself the refutation. You'd need: split measurement into lens-vs-portion
sub-slots; rewrite the concept-link guard and inheritance rules; build
synonym/judge/quarantine machinery for portion tokens; teach the XBRL
materializer to emit portion tokens; redesign cards/anchors to show portion
facets. That is rebuilding the entire name layer inside fact_scope — the worst
possible minimalism outcome.

What your probe DID improve (way forward)

Keep FS-06a (portion → name), and add the boundary your question exposed, as
one sentence in NAME-14/FS-25:

▎ "A measurement word re-expresses the SAME quantity through a different lens
▎ (adjusted, diluted, constant-currency, organic). A word that changes which
▎ portion of the quantity is counted (current, fee-earning,
▎ to-be-recognized-over-NTM, funded) is never a measurement token — it belongs
▎ in the driver name (FS-06a)."

Plus one planted K-fields trap class
(portion-word-wrongly-placed-in-measurement) so EXP-5 measures whether
producers respect the boundary — K-fields is still undrafted, so this costs
nothing. Ledger updated: #1 REJECTED (portion-in-measurement), FS-06a stands,
NAME-14 gains the boundary sentence, K-fields gains one trap class. Next.

## Owner Question Q-01 - Minimal Incorporation Follow-up

FABLE SAID:

Minimal is genuinely small here, because the design almost already does this:
NAME-11's step 3 ("role unclear → keep in the name") is the catch-all these
words fall through to today — the problem is only that three rules (NAME-11,
NAME-14's open-ended list, NAME-16's banned words) can each plausibly claim
words like "current," so two producers route them differently. The fix is
routing clarity, not machinery. Five touch points, zero schema, zero code:

#: 1
Where: 66 §0.R
Change: One new OD row (say OD-17) via the standard verify→define→recommend
protocol — the single owner approval that carries everything below. It's an
addition, not a reversal → no 95_Supersession row needed (same as OD-1's
precedent).
────────────────────────────────────────
#: 2
Where: 02_DriverCatalog.md
Change: One dated note under NAME-11 (same mechanism as the OD-12 note under
NAME-08): "Portion qualifiers (OD-17): a qualifier naming which portion of
the company's own measured quantity is counted — and that is not one of the
six slice kinds, not a period window, and not a measurement version — stays
in the NAME (current_rpo, fee_earning_aum, funded_backlog). Different portion
= different driver, never SAME_AS the bare form. If unclear whether a word
is a window or a portion, keep it in the name; never drop it."
────────────────────────────────────────
#: 3
Where: 03_Slices_FactScope.md (FS-25) + mirrored in NAME-14
Change: The one boundary sentence: "A measurement word re-expresses the SAME
quantity through a different lens; a word that changes WHICH portion is
counted is never a measurement token — it belongs in the name (OD-17)."
────────────────────────────────────────
#: 4
Where: Reader/judge prompts
Change: Nothing new — PIPE-16 already inlines NAME rules verbatim at
WP-FC-EDITS time; land the doc notes first and the prompt block picks them up
in the same already-planned edit (if the edit batch has already run, it's a
one-block re-sync).
────────────────────────────────────────
#: 5
Where: Pending keys
Change: K-reader/K-fields (both still undrafted) draft gold under OD-17; add
one K-fields trap class: portion-word-wrongly-placed-in-measurement.

What deliberately does NOT change: no new field or slice kind, no validator
code (a deterministic "portion word" check would need a closed word list — the
v1 trap), no id recipe, no kernel change (token-subset auto-refusal already
blocks current_rpo SAME_AS rpo for free), no XBRL/concept-link change (portion
drivers now link cleanly as their own base metrics), and no invalidation of
anything already run (K-pairs.v1 gold is unaffected).

One scoping note: the full FS-06a from the big review also carried three
exceptions (system-wide ≡ omitted slice; "Other"-type residual buckets as
legal slice values; eliminations stay excluded). Those are separate
clarifications — they can ride in the same OD-17 row at zero extra process
cost, or stay queued as their own items in your one-by-one review. Your call
when we get there. Ready for #2.

## Owner Question Q-04 - Exact Singular/Plural Prompt Rule

OWNER: Singular or Plural Names - on this i agree but whats the exacr prompt rule?

FABLE SAID:

Quick gauntlet before the wording, because the exact text has one trap to
dodge: code must never do this (plural can change meaning: booking≠bookings,
future≠futures, return≠returns, saving≠savings — that's the v1 line, and why
norm() rightly excludes it). So it must be an LLM coining convention with a
decidable meaning test, not a word list (NAME-19), and its failure direction
must be over-split. The wording below satisfies all three — and note your own
docs prove the need: the kernel writes energy_costs in one line and
resin_cost/freight_cost_pressure in others.

The exact prompt rule (goes verbatim into the inlined RULES block):

▎ SINGULAR BY DEFAULT. Coin every noun in the driver name in its singular
▎ form: aws_outage not aws_outages, store_closure not store_closures, tariff
▎ not tariffs. The name is the cause CLASS — how many, how big, and how often
▎ live in the fact's fields, never the name.
▎ Exception — the plural IS the term. Keep the plural when the singular would
▎ name a different thing or is not how finance names the concept: earnings (an
▎ "earning" is not a thing), bookings, sales, savings, futures, receivables,
▎ product_returns (a "return" is an investment concept).
▎ The test: say the singular out loud — if it still names the exact same
▎ concept, use it; if it changes the meaning or reads as a different concept,
▎ keep the plural.
▎ Never touch locked whole phrases: NAME-08/NAME-08a forms stay exactly as
▎ written (same_store_sales is never singularized).

Plus one judge-side line (for the dedup / G2-rewrite / Refute prompts, so
leftovers get repaired instead of coexisting):

▎ A singular/plural pair naming the same concept is a wording variant, never
▎ two drivers — route it through rewrite-to-the-existing-form or dedup; when
▎ the pair might differ in meaning (booking/bookings), keep separate.

Placement (minimal, same OD-note pattern as #1): one dated note in
02_DriverCatalog.md (fits naturally under NAME-06, which already governs
canonical word form) → PIPE-16 inlines it into reader/G2/dedup/Refute prompts
at the already-planned WP-FC-EDITS → K-reader/K-fields drafting binds to it →
code stays untouched (ADOPT's plural-folding experiment stays OFF; this rule
prevents the fork at birth instead of folding it after).

Residual, stated honestly: borderline plurals (job_cuts?) will still
occasionally fork — but the miss direction is over-split, visible to dedup,
and repairable; today there is no rule at all. Ledger: #2 ADOPTED with exact
wording above. Next.

## Owner Question Q-05 - XBRL Menu Scope for Unknown Slice Kind

FABLE SAID:

Confirmed — your narrow scope is exactly right, and it matches machinery the
design already has. One caveat you missed, though, and it goes into the rule
text.

Gauntlet result, short version: Your understanding checks out against the
docs. The Track-B write path already serves producers a PIT slice menu
(FACT-26: the company's XBRL axis+member values ≤ event time, each classified
into a kind by the frozen 57-row axis table, ∪ values already used on prior
facts). Producer-pick validation is FORMAT-only with four outcomes (pick /
coin / unknown / omit). So: menu pick ⇒ kind inherited from the axis table,
and the model never re-decides it — that's FS-08 plus the code-decides-form
doctrine, already locked. My unknown:<value> rule was only ever for the coin
path. Your scoping survives.

The caveat my attack found: "menu pick ⇒ kind known" has one hole — the same
label can legitimately sit under two kinds in the same company's menu.
Companies with geographic segments tag "Americas" on both the business-segment
axis and a geography axis. If the quote says "our Americas segment" the
framing picks the entry; if it just says "revenue in the Americas grew," two
producers can pick different menu entries and the fork you're trying to kill
reappears inside the menu. So the rule needs a rung for that: menu-ambiguous =
undecidable.

The exact rule (FS-15 clarification, final form — a decision ladder, top rung
wins):

▎ Slice-kind ladder (per stated company part):
▎ 1. Menu first. If the stated part matches a PIT slice-menu entry (same
▎ meaning — the producer judges the match; code never near-snaps), take the
▎ menu value and its kind. The kind came from the frozen axis table and is
▎ never reconsidered.
▎ 2. Menu-ambiguous. If the same normalized label appears under two or more
▎ kinds in the menu and the quote's own framing does not select one →
▎ unknown:<value>.
▎ 3. Prose-only, kind clear. No menu match, but the quote's framing makes the
▎ kind plain ("our X segment", "revenue in China", a named product) → coin
▎ kind:value.
▎ 4. Prose-only, kind unclear. Two or more kinds remain reasonable →
▎ unknown:<value> — the same honest constant as an unrecognized axis. Never
▎ guess; a guessed kind is a fake axis-grade confirmation (the rejected-P3
▎ failure).
▎ unknown: values enter the company's menu like any other value, so later
▎ producers reuse them — one series per company, no fragmentation from
▎ honesty.

Two notes for the ledger:
- Recorded residual (don't solve here): a prose-coined unknown:foo has no axis
qname, so the already-adopted FS-12 exact-qname backfill can't promote it if
the company later tags "foo" on a real axis. Promotion for these needs an
exact-normalized-label match instead — decide that inside the FS-12 backfill
item (or leave to read-time reconciliation), not here.
- Way forward: one clarification block in FS-15 + the ladder verbatim in the
Track-B producer contract (12 §7) and EXP-5's packet instructions + one
K-fields trap case (menu-ambiguous label). K-fields is still undrafted, so all
of it is free.

Ledger: #3 ADOPTED-AS-SCOPED — your menu-first narrowing confirmed, plus the
menu-ambiguity rung added. Next.
