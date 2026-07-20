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
                 (supersedes the AUTO_OK-only wording above; canonical law = Core's FINAL_DESIGN
                 PER-21 + BUILD_AND_OPERATIONS §3): HISTORICAL/backfill pairing =
                 `get_quarterly_filings.match_8k_to_periodic` — the shared structured matcher,
                 exact target-accession equality; LIVE (no 10-Q/K exists yet) =
                 `quarter_identity` alone (AUTO_OK is trust-only). The lane RULE: the target
                 10-Q/K EXISTS → the historical lane; the target is ABSENT → the live lane.
                 ANY failed historical match PARKS — it NEVER falls through to the live lane.
                 Fiscal labels/calculated dates are never joined; no third matcher, ever.]**
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
  **[OWNER-LOCKED AMENDMENT 2026-07-20 — alias-ambiguity. Alias IDENTITY = concept qname +
  COMPLETE (axis,member) pairs + exact period/time shape + normalized unit. Equal VALUES under
  ANY difference in that identity are NEVER aliases of one quantity ("same value = same
  quantity" is FALSE across identities); any such difference among surviving candidates →
  ambiguous → abstain. No alias pick, no alphabetical or any other tie-break ACROSS
  identities (total-content ordering applies only WITHIN one identity).]**
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
