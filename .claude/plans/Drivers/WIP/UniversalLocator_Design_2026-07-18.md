> 📌 **AUTHORITY (2026-07-21):** This locked Design v5.5 remains **THE BASE CONTRACT for
> every rule it contains that has not been explicitly replaced.** The ONLY current
> execution amendment/work order is `UniversalLocator_SourceLinked_Prose_Simplification_
> FinalPlan_2026-07-21.md`, which replaces EXACTLY: Corrective-5 Batch B/C/D · this doc's
> Round-14 §3 · the Batch-C rows of Round-14 §4 · Round-14 §5's old measurement sequence ·
> the draft disposition table (now FinalPlan §16). Everything else here stands unchanged.
> Reading order: locked Design base → FinalPlan changes/current steps → Review Record
> history.

# Universal Locator — Operative Design v5.5

**Status:** v5.5 — architecture settled after 9 review rounds; D14-v3 owner-confirmed; the durable
zero-write schema probe green (13 tests incl. two live company edges + cross-wired-company
rejection). **LOCKED by the owner 2026-07-18** (reviewer-approved round 10) **+ THREE
OWNER-LOCKED AMENDMENTS 2026-07-20** (owner word "lock the amendments"; the marked
[OWNER-LOCKED AMENDMENT] blocks in §1 SOURCE SELECTION and §3 STATUS are the ONLY changes vs
the approved f98009b7… content).
History/verdicts/evidence: `UniversalLocator_ReviewRecord_2026-07-18.md`.

---

## 0. Goal

One operation: **(anchor, one source event, optional untrusted hints) → zero or more raw evidence
items, or an internal no_proven_match.** Over old stored sources = backfill; on each newly stored
source = forward updates. No recipe registry, no locator scheduler/retry, no new ledger.

> Honest goal: 100% measured precision among emitted items; recall pushed toward 100% among
> unambiguous facts the source actually states. Stated-ness of a miss is decided only by independent
> grading. Certification reports denominators and statistical upper error bounds — zero observed
> errors is the release bar, never proof.

Runtime honesty: channel ledger/cursor DUTIES are specified by the packet law but UNBUILT; **only
central orchestration remains undesigned.** Shared decomposer unbuilt · kernel OFF · Neo4j writes
disabled (CLI dry-run only) · public channel runtime unbuilt · ConceptResolution linker dormant.

---

## 1. Architecture (caller first)

```
THIN CALLER      select one source event → fetch it ONCE → rebuild the company's anchors →
                 run the locator per anchor → emit ONE packet per source event with ALL items
      ↓ uses
SOURCE EVENTS    a 10-K/10-Q · an amendment (source_type stays 10k/10q, own accession + own
                 public time) · one 8-K accession — fetch AND DEDUPLICATE all stored sections,
                 exhibits, and filing text for that accession (never EX-99-only; no "relevant
                 exhibit" classifier) · ONE Transcript node
SOURCE SELECTION (pinned): the universal loop enumerates REAL accessions directly (source-first).
                 The fiscal.ai period-keyed adapter selects candidate 8-Ks via the existing
                 quarter-identity matcher — used ONLY when `safety_action == AUTO_OK`; anything
                 else fails closed (that 8-K is dropped, the filing still searched). NEVER the old
                 5–75-day window. **This correction lands BEFORE WP1's single regeneration** so the
                 fresh baseline is never built on the unsafe guess.
                 **[OWNER-LOCKED AMENDMENT 2026-07-20 — the earnings-8-K TWO-FILE AUTHORITY
                 (supersedes the AUTO_OK-only wording above). Canonical law = Core's
                 FINAL_DESIGN PER-21 + BUILD_AND_OPERATIONS §3 — this design POINTS there and
                 copies no procedure. Lane rule: the target 10-Q/K EXISTS → the historical
                 lane; the target is ABSENT → the live lane; ANY failed historical match
                 PARKS — it NEVER falls through to the live lane.]**
      ↓ into
SHARED LOCATOR   (anchor, source, optional untrusted hints) → raw items[] | no_proven_match
```

**Reuse boundary (pinned):** the neutral locator imports ZERO fiscal.ai/channel code; adapters
depend on the locator, never the reverse.

Routes, in order:
1. **Exact XBRL — own-source only.** A prior qname may only RETRIEVE candidates, never prove
   identity. Cross-source automatic XBRL reuse stays OFF until Core's ConceptResolution linker is
   built and activated.
2. **Exact structural / known-value match.** Hints (target-source label/value/period clues only)
   retrieve; source evidence proves. A prior period's value is never a hint for a new period.
3. **Batched semantic reader** — reuse the EXISTING batch execution + verification gates. **No new
   deterministic matcher is built in this work; reconsider only if WP4's measured recall or token
   cost proves it necessary.** Honest scope: the existing reader machinery does not yet speak "one
   neutral anchor + one source" — that request/result schema AND its prompt are NEW artifacts;
   **prompt writing is a separate owner approval.** (The relocation reader is value-unknown and
   transcript-tested; numberless anchors are unsupported today.) OFF until
   prompt+model+fixtures+budget+independent zero-wrong certification are approved per stratum.
   Core-side dependency: every newly admitted no-XBRL Driver (numeric or numberless) additionally
   requires the kernel's falsifier gate.
4. **no_proven_match** — internal, honest. Becomes a terminal `value_absent` SKIP only after the
   clean expected-source-completeness stamp; the three legal reopen triggers preserved.

Backfill submits oldest → newest. The two lifecycle triggers (first-accepted-fact → backfill;
new-source → relocate) are REQUIREMENTS on the future S4 running layer, not an implementation here.

---

## 2. The temporary anchor

**Stable identity (the series key minus period and period_scope):**

```
ANCHOR-ID  = stable Company id/CIK via the source→Company edge (never ticker) · Driver ·
             fact_type=metric · slice · measurement · series_unit · time_type
SEARCH CLUES (non-authoritative): PRIMARY wording = the Driver's law-required IMMUTABLE
             `definitional_evidence.birth_quotes` (BUILD §8.1.6) · fallback = the stored fact
             quote (LWW, hence fallback only) · an ACTIVE ConceptResolution when one exists
```

No second copy of anything is stored; anchors are rebuilt on demand. A bare number is not an
anchor (`insufficient_identity`). Unit/value-class matching kept. Numberless metrics are already
legal as quote-backed facts with all value slots and `series_unit = None` — no new storage field.

**Schema proof:** the durable zero-write probe `driver/relocation/test_anchor_schema_probe.py`
(13 tests; ids composed by Core's AUTHORITATIVE `driver_ids` pure law — test-only import — while
the decoder under test stays independent; strict metric-only decoder REJECTS `surprise=` and
unknown slots; Driver-name/type agreement asserted; stored `fact_scope` must equal the id suffix;
**the company binds ONLY via the source id parsed from the fact id**, looked up in a TRUSTED edge
map (the exactly-one graph-edge query's own output) — the probe rejects missing/cross-wired KEYS;
it does not authenticate a fabricated value under the correct key (that would duplicate graph
validation); fixtures use legal period forms but the probe
does NOT validate period legality — Core's validators own that and nothing here duplicates it;
**only the source→Company edges are loaded LIVE** (exactly one per pinned accession, else FAIL) —
quote/unit/Driver payloads are pinned fixtures; zero channel imports; skip only on genuine graph
unavailability — query errors and missing edges FAIL). **NOT proven — and stated:**
reconstruction from live graph nodes (none exist yet), birth_quotes persistence on real nodes,
locator accuracy from rebuilt anchors → **the full create_driver → rebuild → second-source proof
is a mandatory S4/WP2 integration gate.** Anchors are never built from pre-WP1 outputs.

**The Core backfill handoff (D14-v3 mechanics):** one OPTIONAL, CORE-ONLY
`backfill_candidate_driver_name` per internal fact (Driver.name IS the existing unique key —
no separate id exists), riding the existing item/fact provenance —
never a public packet field, never a registry. **Exactly one candidate may reach the kernel;
multiple candidates = ambiguous, fail closed.** The kernel reconfirms from old-source evidence
alone; mismatch never forces attachment. Its required test joins the S4/WP2 gate.

---

## 3. Locator contract

```
INPUT : anchor + one source event + optional UNTRUSTED hints (target-source label/value/period
        clues only — retrieve, never prove)
OUTPUT — ChannelContract-exact, ONE packet per source event:
  ENVELOPE once:  source_id · source_type · ticker · fye_month · event_time
  ITEMS, each:    verbatim quote (untouched corpus slice; cell evidence = audit data only)
                  · untouched raw label/claim
                  · ALL applicable stated-value shape fields — point / range / floor / ceiling /
                    comparison AND source-stated CHANGE/DELTA values with their units —
                    signed, unscaled, SOURCE-PRINTED (or numberless) + raw unit text / format flags
                  · source cadence + adjacent period wording + NON-XBRL stated period dates
                    exactly as printed
                  · exact XBRL context when present: concept qname + exact dates + time_type +
                    complete {axis, member} PAIRS, `[]` only as a verified-empty assertion
  STATUS (internal, empty-result cases only): no_proven_match | ambiguous | insufficient_identity
  **[OWNER-LOCKED AMENDMENT 2026-07-20 — alias-ambiguity. Alias IDENTITY = the exact concept
  identifier AS STORED in this source (full qname when present; otherwise bare local name,
  NEVER promoted) + COMPLETE (axis,member) pairs + exact period/time shape + normalized XBRL
  unitRef. Equal VALUES under ANY difference in that identity are NEVER aliases of one
  quantity ("same value = same quantity" is FALSE across identities); any such difference
  among surviving candidates → ambiguous → abstain. No alias pick, no alphabetical or any
  other tie-break ACROSS identities (total-content ordering applies only WITHIN one
  identity).]**
```

- The locator never emits final scope, resolved periods, Driver identity, or computed values —
  Core resolves period/units/identity/storage.
- **Printed-values-only:** the saved number must literally appear in its own quote; hints are
  never stored.
- **Dates:** normalize ONCE by the KNOWN input format, then compare EXACTLY; unknown or mixed
  conventions abstain; adapter-side normalization is COMPARISON-ONLY (packets retain exact source
  context). Values compare by exact Decimal.
- items[] unrolls before submission — each item its own candidate fact (quarter / YTD / annual /
  instant / comparative all separate; comparatives emitted per owner ruling).

---

## 4. Exactness (defect-driven; each reproduced or code-cited)

One shared exact-number utility (Decimal) + the one date rule (§3), born in `driver/relocation/`.
Fix list: `_tableforms` len≥3 drop · decimal loss · zero drop · `tier1`/`xbrl_lane` int-rounding ·
%-vs-plain class guard · integer-rounded forms for fractional values dropped · namespace-kept
concept compare · unit compare · instant support · raw-quote emission · adversarial mixed-window
and neighboring-period date cases.

---

## 5. Work packages

| WP | Content | Done-bar |
|---|---|---|
| **1. Exactness + fresh measurement** | Expanded RED battery FIRST → smallest fixes via shared exact utilities → **the fiscal.ai 8-K routing/fetch correction (AUTO_OK-gated quarter-identity selection, else fail closed; fetch + dedupe ALL stored text per accession) lands BEFORE the regeneration** → `item_id` stamped in residuals → the single 0-token REGENERATE on a wider set (removes all stale fabricated quotes) → honest measurement with true denominators. | Battery green; regress floors hold; fresh numbers with denominators. |
| **2. Anchor + one-source locator** | Anchor rebuild (§2) + routes 1–2 + the §3 contract; split seam in place (physical move stays end-reorg). **Enforces the neutral boundary:** the current chain `locate → xbrl_lane → oracle → run_code_tier → fiscal_ai_rules` is the exact breach the split removes; done-bar includes an IMPORT TEST proving `driver/relocation` loads with zero fiscal/channel imports. **Includes the mandatory S4/WP2 gate test set:** create_driver → rebuild → second-source proof · the `backfill_candidate_driver_name` single-candidate handoff test — both once Core components exist. | (anchor × source) → raw items or honest no_proven_match on real filings; import test green; tests + regress green. |
| **3. Source loop + adapters** | A MANUAL dry-run loop only (future trigger wiring = S4 work) over 10-K/Q, amendments, 8-Ks (all stored text per accession), Transcript nodes. | One ticker end-to-end to dry-run packets, 0 tokens. |
| **4. Reader wiring + independent certification** | Reuse the EXISTING batch execution + verification gates (no new deterministic matcher in this work; reconsider only if WP4's measured recall or token cost proves it necessary); author the NEW neutral anchor+source request/result schema and prompt (**prompt = separate owner approval**) → then certification: frozen unseen cases; **zero observed wrong accepts = release bar** with denominators + upper error bounds; minimum fixed strata + named high-risk intersections; reader activation per-stratum. **Token-cost reporting: tokens per searched item, per accepted fact, and projected backfill/forward cost.** | Owner GO + budget. |

---

## 6. Decision ledger (owner-authoritative; rationale in the record)

D1 stated-only recall · D2 codes and/or wording · D3 zero-wrong release bar + error bounds ·
D4 reuse proven behavior, replace demonstrated faulty code · D5 minimum complete identity ·
D6 scope never cross-binds (evidence + Core tripwires; locator stamps no scope) · D7 anchors
period-free · D8 source-first, two triggers (S4 requirements) · D9 printed-values-only ·
D10 reader off until package + per-stratum cert (+ kernel falsifier for every no-XBRL admission) ·
D11 comparatives emitted · D12 transcripts in scope per-node · D13 no stored recipe; anchors
rebuilt on demand · D14-v3 PIT backfill (owner-final): one internal untrusted candidate only,
Core reconfirms from the old source alone, nothing factual copied backward, dual honest
timestamps, source-date PIT views stand (system-state reproduction = run snapshots).

*End v5.5.*

---
## ADDENDUM (reviewer-ordered 2026-07-21) — MANDATORY WP2-CLOSE BLOCKER
"WP2 cannot close until the filing-declared semantic unit and divide meaning are passed
into the neutral matcher for every available XBRL fact. Raw unitRef remains identity.
This must recover eligible number and opaque unit IDs without spelling guesses,
registries, an LLM, or tokens."
(Recorded per the reviewer's round-4 order; the review record holds the full context.)

════════════════════════════════════════════════════════════════════════════════
ROUND 14 — SOURCE-LINKED PRE-BUILD PACKAGE (reviewer-ordered; NO code until audited)
════════════════════════════════════════════════════════════════════════════════

### §1 THE JOIN — structured Fact → its exact display element (fail-safe by enumeration)
One fetch/parse per filing (display inline .htm; the extracted _htm.xml is NEVER a
substitute — it drops element ids). Join key (CORRECTED law, round 14d — supersedes the
14c wording, which followed the reviewer's own inverted instruction): the HTML `id=`
attribute is indexed by **`inline_element_id` = `Fact.fact_id`** (the SHORT id, e.g.
'f-498'); **`graph_fact_id` = `Fact.id`/`u_id`** is the LONG canonical identity that
merely ENDS WITH the short id and never equals the HTML id. Graph-verified 2026-07-21:
13,775,616 facts · long id on all · 34,277 short blank/null · 13,741,339 suffix-
consistent · zero equal. The M2 resolver already used the correct field — verbatim from
m234_display.py: cypher `RETURN f.fact_id AS fid …` then `k = ids.get(fid)` where `ids`
counts the display-HTML `id="…"` attributes. Measured basis: 2,019,825/2,019,825 numeric non-nil usable-id facts resolve
EXACTLY ONCE across the 1,722-file cache (0 miss · 0 duplicate); all-facts superset
2,200,113 also 100%.
Fail-safe law (every branch abstains, never guesses):
- fact_id missing/'null' (3,332): identity fallback (name, contextRef, unitRef) binds
  IFF exactly one element matches (3,324); ≥2 (the 8) → ABSTAIN.
- id not found in the document, or found ≥2 times → ABSTAIN (measured zero; guarded).
- Malformed element (measured: exactly 2 — one attribute-less, one referencing the
  undefined context c-410) → ABSTAIN.
- Element inside ix:hidden → join succeeds, visibility=hidden carried; hidden elements
  provide NO display evidence (no row/headers); they may satisfy existence, never
  identity → identity unproven → ABSTAIN unless another lawful path proves it.
- Filing uncached → fetch once via the lock_cell.py convention; fetch failure → ABSTAIN.
- Value reconciliation: displayed text ∘ (ixt format, scale, sign) must equal
  Fact.value by EXACT Decimal arithmetic; mismatch → ABSTAIN.

### §2 ELEMENT-LOCAL PROOF — no document-wide text parser
Structured facts are proved ONLY from: their own element (+attrs) · their table row
(untouched) · the aligned column-header stack · the section caption — or, for prose-
embedded elements, the smallest enclosing structural block (<p>/<td>/<li>). Prototype
= the SHA-pinned extractor (lock_row_extract.py 38690c7b…; 144/146 gate rows handled,
2 need the generic parent-paragraph path). Anchor wording/slice/measurement tokens are
checked against THAT local evidence only; concept remains retrieval-only; missing
identity proof → ABSTAIN. Unit = raw unitRef + the semantic Unit node (12,402,201
verified 1:1) — raw-unit SPELLING classification is deleted. Period = the context's
declared dates (graph stores exclusive ends; normalize once; keep the printed date).
No sentence splitter, no territory, no scale competition, no cadence wording — the
element declares scale/sign/period. [Narrowed per round-14c audit: only SCALE/PRINT
competition for one exactly-joined Fact disappears (its element is unique). DIFFERENT
surviving Fact identities that each match an anchor still invoke the locked ambiguity
law — ambiguous → abstain, unchanged.]

### §3 THE PROSE ROUTE — ⛔ SUPERSEDED (round 14c) by FinalPlan §5 Routes B–E
⛔ THIS SECTION IS NOT ACTIVE. The FinalPlan (2026-07-21) replaces it: conditional
Routes B/C (measured-or-cut), Route D batched reader, Route E honest no_proven_match.
Batch C's R2 time law is FROZEN with Batch B/C/D. Kept below only as history.
Scope: sources without stickers (8-K EX-99.1 prose, transcripts, news, fiscal.ai) and
R2 value-hints. Kept core: exact print-form families (value_forms incl. the measured
vs./ppts. dotted forms via the form grammar — no registry) · local identity within the
containing block · printed unit signal · span-local sign · zero-intervening-word
adjacent basis phrases. Same-family contest inside the block (measured ≈27% of value
sentences) → route to the BATCHED READER: reader PROPOSES (occurrence + label), code
VERIFIES (verbatim byte-check · form cover · identity tokens · uniqueness); unverified
→ ABSTAIN. Reader batches are cost-approved by the owner before any run. R2's time law
remains Batch C; R2 stays explicitly incomplete until then.

### §4 DELETION TABLE — exact functions, callers, replacement (net = measured at diff)
External callers outside locator.py: NONE except test_locator_routes.py (verified).
| function (lines) | callers | fate |
| _unit_class (137) | _span_item | DELETE — semantic Unit node replaces spelling walk |
| _fact_scale_evidence (189) | R1 enumeration | DELETE — no competition vs a unique id |
| _span_item (172) | emit, competition | REPLACE with element-local proof (≈50-70 L) |
| _print_candidates (17) | _span_item | DELETE — scale attr declares the printed form |
| _hard_break/_pieces/_clause_bounds (63) | splitter consumers | DELETE from R1; prose
|   route uses source structural blocks, never sentence regex |
| territory block + next-label walk (inside _span_item) | — | DELETE |
| R2 inline copy (~40) | R2 | DELETE — one shared proof |
| _printed_basis (56) | basis law | ⛔ SUPERSEDED (14c): its contested-prose case class
|   routes to the reader (FinalPlan §5D); deleted with the prose parser in Phase 3;
|   pinned QSR/SBX/Chili's/JOINT cases → reader-certification set |
| _wcls/_cad_ok cadence | period law | R1: DELETE (context dates are exact);
|   ⛔ SUPERSEDED (14c): no "prose route until Batch C" — B/C/D frozen; prose period
|   meaning belongs to the reader (FinalPlan §6) |
| _suffix_forms/_tableforms/value_forms | print families | KEEP (prose route + R2) |
Net size: reported from the actual diff; ~713 lines is an ESTIMATE, NOT a target
(reviewer correction recorded). If the design fails to materially reduce code → STOP
and report, per order.

### §5 OLD-vs-NEW COMPARISON — ⛔ SUPERSEDED (round 14c) by FinalPlan §8 (M1–M4) + §11
⛔ THE MEASUREMENT SEQUENCE BELOW IS NOT ACTIVE. FinalPlan order governs: GO → Phase 1
(Route A build + its shadows/gates) → THEN Phase 2 = M1–M4. Kept below only as history.
Already-run (this round): the join over all cached facts (numbers above) · the 150-gate
graph existence (each case fetches its exact Fact.id; 130/20/0 green) · manifests/SHAs.
To run for the audit package (read-only, no production code): the SHA-pinned extractor
across the 146 cached gate cases and the cached corpus sample → row/header evidence
rates; old-route corpora reruns (battery 230 · floors 28 · WP1 outputs) with the
LAWFUL-FLIP REGISTER: synthetic pins whose expectations change BY RULING —
'United States 2024' → abstain unless structure/wording proves the year; 'Product 50'
→ binds only via its own wording token; flat-text territory pins → superseded by
element-local proof (each flip listed with its ruling citation, none silent).
Report: precision · recall · lawful losses · reader-queue volume (≈27% of contested
prose sentences; per-corpus counts) · token estimate for the batched reader.
PIT ordering (§6) is enforced inside every comparison.

### §6 POINT-IN-TIME LAW
Evidence for a fact located in source S comes ONLY from S itself (+ the anchor).
An earlier 8-K/transcript NEVER uses a later 10-Q/10-K as evidence. Retro-twin XBRL
checks (the later sticker confirming an earlier prose number) are CALIBRATION/grading
only — never stamped as evidence on the earlier source. Reader outputs obey the same
scope: the reader sees S and the anchor, nothing later.

════════════════════════════════════════════════════════════════════════════════
ROUND 14b — COMBINED PRE-BUILD PACKAGE (response to FinalPlan §14; NO code)
════════════════════════════════════════════════════════════════════════════════
GOVERNING DOCUMENT from this point: UniversalLocator_SourceLinked_Prose_Simplification_
FinalPlan_2026-07-21.md (sha256 e1825c567fc5…). Of this doc's ROUND-14 sections, ONLY §§1–2
(the Route-A join + element-local proof) and §6 (the point-in-time law) remain valid
detail; §3, the Batch-C rows of §4, and §5's measurement sequence are ⛔ SUPERSEDED and
so marked in place. Where anything differs, the FinalPlan wins. Specifically SUPERSEDED here:
my §3 line "R2's time law remains Batch C" — Batch B/C/D are FROZEN by FinalPlan Phase 0;
their promised items (≥5-rule deletion · YUM completion criterion · 'while' recall ·
leading-Q/Q · R2 time law · pp×100) each receive an explicit entry in the disposition
ledger (destination: reader-certification case, integrity test, or retired-with-ruling)
— nothing vanishes silently.

§14 CONFIRMATIONS (all seven):
1. Route A (source-linked) design kept exactly as specified (§1–§2 above + FinalPlan §5A).
2. Corrective-5 Batch B/C/D FROZEN.
3. The prose patch sequence is REPLACED by measurements M1–M4 + conditional Routes B/C;
   Route D (batched reader) + Route E (honest no_proven_match).
4. TWO OF MY OWN CLAIMS CORRECTED (his catch, supported by MY measurements): (a) "every
   8-K level later gets a tagged twin" is FALSE — my own redundancy study measured
   ~35–60% money-level overlap (47.2% transcripts / 44.4% news overall) — a later twin
   is a GRADING aid only; (b) "spoken percentages can be recomputed from tagged levels"
   is UNSAFE as stated — organic/adjusted/constant-currency/rounding definitions may not
   match; M3 measures exact-definition coverage; a calculation may only reject a
   contradiction, never prove or store a fact (ChannelContract forbids computed facts).
   Also REVISED my own prior: my "~70% of prose is deterministic at 0 tokens" estimate
   ignored that prose period proof usually needs period WORDS, which the new law removes
   from code — Route C's true coverage is UNKNOWN until M1/M4; conditional-and-cut is
   the correct stance.
5. News stays a separate channel; Fiscal gains no news retrieval/meaning rules.
6. Keep/delete/test-migration: FinalPlan §10 adopted verbatim + my exact caller map
   (round-14 §4 above; external callers = test_locator_routes.py ONLY — deletions are
   contained). Test disposition ledger: FAMILY-level now (per-test at Phase-1 audit):
   route/battery families → keep (Route-A behaviours) · flat-text ownership families
   (territory/competition/splitter/basis-ownership) → reader-certification + falsifier
   set · synthetic pins flipped by ruling (US-2024, Product-50, test_49 class) → the
   lawful-flip ledger with citations.
7. HOLDS CONFIRMED: HEAD c2fc998 · fixture d7d2f068 · boundary 81eca0aa · four dirty WP2
   paths preserved (never reset/checkout) · zero Neo4j writes · zero reader tokens ·
   no push · no Core edits before Phase 5 · news untouched.

§15 REPRODUCTIONS (all exact, my own runs, 2026-07-21):
- 8-K exhibits with content: 26,779 · 0 '<table' · 0 '##TABLE_START' · 0 multiline —
  stored 8-K text is FLATTENED; Route B must fetch original exhibit HTML.
- Earnings-8-K EX-99 inventory: 10,274 distinct rows · 10,274 exact-key exhibit URLs ·
  10,248 HTML · 26 PDF · 10,274 single-line.
- Transcripts: 9,608 · 9,320 PreparedRemark (all nonblank) · 170,654 QAExchange (all
  nonblank) — lawful source-native reader blocks exist.
- Line-growth anchor verified: locator.py at 7f052b0 = 756 lines (now 1,808);
  test_locator_routes.py 187 → 1,406.
- Prior reproductions stand: M1 12,402,201 · M2 2,019,825 exactly-once/0/0 · M3 8
  ambiguous · M4 2,217,620 with exactly 2 malformed (f-1762 → undefined c-410) · M5
  146/150 cached · manifests/SHAs.
STATUS (round 14d): ⛔ NO execution sequence lives in this document. The SOLE current
sequence is FinalPlan §11 (Phase 0–7); the AUTHORITATIVE disposition table is FinalPlan
§16. This doc remains the Route-A detail CONTRACT (§§1–2 + §6 PIT) and evidence/history.

SIX-ROW DISPOSITION TABLE — ⛔ SUPERSEDED DRAFT (round 14d): the authoritative,
correctly-formatted five-column table now lives in FinalPlan §16. Kept as history:
| item | destination | expected result | gate |
| ≥5-letter qualifier rule | DELETED with the prose parser (Phase 3) — Route A proves
|   identity from row/headers; prose → reader | its false abstains (e.g. 'In the
|   quarter,' prefixes) disappear; no wrong accepts appear | Phase-1/3 shadows +
|   lawful-flip ledger at M2 |
| YUM verbatim sentence (old Batch-B completion criterion) | reader-certification case
|   (contested prose by construction) | reader+verifier bind it or abstain honestly;
|   never a wrong basis | Phase-6 zero-wrong certification |
| 'while' recall return | SUPERSEDED — recall arrives via Route A structure (tagged) and
|   the reader (prose), not word rules | previously-lost 'while'-adjacent cases recovered
|   or honestly abstained | M2 dispositions + Phase 6 |
| leading 'Q/Q' walk mutilation | RETIRED with the label-walk machinery; Q/Q stays only
|   as a print/phrase FORM in the verifier | no walk exists to mutilate; form still
|   recognized mechanically | Phase-1 shadow (zero wrong accepts) |
| R2 time law (old Batch C) | SUPERSEDED by FinalPlan Route C contract: a known-value
|   fast path proves the stated period from source-native evidence or the route is CUT;
|   if cut, prose period meaning lives only in the reader | no R2 emission without
|   period proof under either outcome | M2 keep-or-cut gate + Phase 6 |
| pp×100 (was pending one verified real pair) | RETIRED from code — Route A reads the
|   element's declared scale; prose pp forms remain RAW-only in the verifier's form
|   families | no behavior change (never enabled); no pinned case depends on it | M2
|   shadow confirms zero dependence |
