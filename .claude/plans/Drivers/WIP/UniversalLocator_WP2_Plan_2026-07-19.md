# WP2 Plan — Anchor + one-source locator (v4, 2026-07-19)

v3 architecture APPROVED; v4 = the reviewer's final proof-tightening (7 points, every premise
verified before adoption: the lazy-import risk is REAL in this codebase — locate.py itself does
an in-function `import xbrl_lane`; the probe's four rejection cases exist and must survive the
migration; XN.period_key already rejects impossible/blank dates — the pins extend that law to
the FACT side; seg_parse is one parser today but homed channel-side — the move completes it).
v3 history: 11 pins verified, 2 owned v2 errors ("prior pairs" over-inclusion; phantom deferred
register). **CODE-GO GRANTED 2026-07-19** (reviewer final audit + the owner's standing words
"once committed and pushed you can start with WP2" — condition met at `80bae52`); the final
literal correction (10-K/Q item = tag+dimensions-or-[]; text-only 8-K item = NO XBRL context,
never `[]`) applied to the done-bar below. Zero-token WP.
**WP2 IS READ-ONLY: Neo4j reads only, ZERO writes — stated explicitly (standing owner law).**

## THE FLOW (approved, unchanged)
period-free anchor → scan the WHOLE target source → XBRL retrieves candidates (never proves) →
same-source text proves (value · label · period-as-printed · slice · verbatim quote) → emit ALL
proven items (Q / YTD / FY / instant / comparative — each bound to ITS OWN printed period
evidence; ambiguity → abstain) | no_proven_match. No printed quote → abstain to WP4.

## Steps (RED test first, every step)

1. **ANCHOR.** ONE pure PRODUCTION `rebuild_anchor()` in `driver/relocation` — the probe's
   test-local `strict_decode` stays as schema pins, but reconstruction tests call the REAL
   function. Pure, no I/O; FAILS CLOSED on: missing identity field · blank wording clues ·
   MULTIPLE active ConceptResolutions · a numeric fact lacking series_unit (numberless stays
   legal with series_unit=None). Anchor clues = birth_quotes PRIMARY · stored fact quote
   fallback (LWW) · the prior qname supplied by the sole ACTIVE ConceptResolution
   (retrieval only, never proof).
   **NO prior (axis,member) pairs anywhere — old XBRL dimensions are never reused; each target
   source proves its own complete address.** Prove-or-stop: unreconstructable field → STOP,
   surface the smallest missing field. Pinned fixtures (live Driver nodes don't exist yet).
   **v4: the production-function tests RETAIN the probe's existing rejection pins — verified
   present today: cross-wired/missing source→company edge keys · fact_scope ≠ id suffix ·
   Driver-name/type disagreement · the time_type slot. No coverage lost in the migration
   (count before/after).**
   **Build-round-1 corrective laws (reviewer audit of `5f3aeb9`, all three bugs reproduced):
   numeric-ness is DERIVED from the five stored value slots (level_low/level_high/change_value/
   comparison_low/comparison_high — names verified against Core writer `_NUMERIC_SIG`) via
   `is not None` so a stored ZERO counts; numeric → nonblank series_unit, numberless → 
   series_unit=None, BOTH directions fail closed; wording fallback = the STORED props["quote"]
   ONLY (the caller-supplied fact_quote channel is removed and signature-pinned); birth_quotes
   must be a list/tuple of nonblank strings (a bare string iterates into LETTERS — rejected);
   a sole ConceptResolution clue must be a nonblank string.**
   **Build-round-2 laws (audit of `3e3e3d9`, all holes reproduced locally): ALL FIVE value
   keys must be PRESENT — explicit None is the only legal no-value, absent keys = missing
   data, never "numberless"; blank company ids rejected as corrupt edges; concept clues must
   arrive as a list/tuple (bare string/None = the letters-bug sibling) holding at most ONE
   nonblank string. Wording: the ACTIVE ConceptResolution SUPPLIES the prior qname — the
   carrier of the clue, not a separate clue kind; "reproduced live" is reserved for
   graph-backed runs ("locally" = synthetic calls); the 28/28 floors are run+recorded every
   build round.**
   **Build-round-3 law (ONE general input-schema guard, table-driven): props / driver_node /
   edge_map must be mappings; a present definitional_evidence must be a mapping; parsed
   source id and Driver name must be nonblank; company must be a nonblank, UNPADDED string.
   Malformed inputs raise clean ValueError — never an anchor, never a crash.**

2. **NEUTRAL BOUNDARY FIRST — and RED first at the STEP level (lock-correction round):
   AUTHOR the failing boundary test before anything else in Step 2; it stays RED through the
   parser relocation → the 150-case gate → the route build, and goes GREEN only at the end
   via real R1/R2 calls. A failing test is NEVER committed to main — it lands in the commit
   that turns it green with the routes.** The boundary test imports the ACTUAL locator
   entrypoint
   (`driver/relocation/locator.py`) in a subprocess **and EXECUTES one minimal R1 call and one
   minimal R2 call on fixture input BEFORE sweeping sys.modules** — import-only proof is
   insufficient because lazy in-function imports are a REAL pattern in this codebase
   (locate.py's own `import xbrl_lane` inside locate_by_fingerprint). Assert NO fiscal/channel
   module loaded after the calls. Fiscal modules become thin adapters; NO duplicated matching
   code.

3. **THE ONE STRICT XBRL PARSER/MATCHER lives in `driver/relocation`;** old
   `xbrl_lane.resolve` becomes a THIN ADAPTER delegating to it (no physical moves of existing
   files — R5 untouched). **v4 — "one parser" truly ONE: `seg_parse` relocates INTO the
   neutral module; BOTH link_lib/tier1 AND xbrl_lane import it from there (today it is defined
   in link_lib — channel-side — and xbrl_lane imports it from link_lib, the inverted
   dependency the seam removes). Pure move, behavior-identical — it touches link_lib, so the
   complete-final-diff regeneration check WILL run.** RED pins BEFORE the build: wrong axis
   for a right member · swapped pairs · pair-ORDER independence · malformed vs verified-empty
   dimensions (distinct) · mixed instant+duration dates abstain · a bare local tag NEVER
   invented into a full qname · exact Decimal end-to-end · **v4 fact-side period pins:
   start-only, end-only, blank, impossible-date (2024-13-45 / 2024-02-30 class), and mixed
   shapes all ABSTAIN in the value-unknown enumeration (XN.period_key verified to reject every
   one on the request side — the law extends to the FACT side, where enumeration has no
   request period to hide behind).**
   **The durable 150-case live gate:** FIXED pinned cases (exact row identities — no sampling
   drift), exact-Decimal comparison, ZERO wrong, deterministic output, CANNOT silently skip
   (an empty fetch FAILS). **v4: the gate RECONCILES EXACTLY ALL 150 — every case lands in
   exactly one bucket (ok / abstain-with-reason / owner-gated loss) and the buckets sum to
   150, else FAIL.** Any loss from the current 130-link baseline is explained case-by-case
   and OWNER-GATED before acceptance.

4. **ROUTES on the neutral core (§3 contract exact).**
   R1 own-source XBRL ENUMERATION across ALL periods present in THIS source; every emission
   text-proven with its verbatim quote; every quote AND raw label from the TARGET source;
   XBRL context emitted ONLY as stored-and-complete in THIS source (bare local names emit as
   quote-proven items WITHOUT promoted context).
   R2 exact structural / known-value: hints CARRY the current source_id — a hint stamped with
   any other source is REJECTED; hints retrieve, source evidence proves; a prior period's
   value is never a hint.
   ONE all-period test pins: Q, YTD, FY, instant, comparative, DEDUPLICATION (one fact in many
   blobs → one item), ambiguity → abstain.
   PLUS one small transcript-SHAPED neutral-payload test (fixture dict shaped like a Transcript
   source; no fetching, no tokens) proving source-type neutrality — real Transcript-node
   integration stays WP3.
   OUTPUT: proven value fields only — no new prose parser. no_proven_match internal; fetching/
   envelopes/completeness/terminal skips = WP3; identity/final periods/writes = Core.

5. **CENSUS-ONLY acronym work** (B2B/SaaS digit class · EMEA/NAA conjunction class): counts +
   examples to the owner. NO lists, NO code.

## S4-blocked items — real authorities only (v2's "existing deferred register" was a phantom)
create_driver → rebuild → second-source proof · `backfill_candidate_driver_name`
single-candidate handoff: their authority = the LOCKED locator design's own mandatory-gate
sentences (§2/§5) + Core's STATUS_AND_HISTORY (Core-owned; Fiscal never edits it). No
standalone register exists or will be built.

## Done-bar (design-verbatim + the reviewer's pins)
(anchor × source) → raw items or honest no_proven_match on REAL filings — including **one real
XBRL 10-K/Q AND one real text-only 8-K, with pinned source hashes and the exact commands in
the record** · **v4 + final correction: at least ONE COMPLETE emitted item from EACH of the
two real sources — every field checked: quote = exact source substring · raw label from THIS
source · period-as-printed; the real 10-K/Q item ADDITIONALLY carries the exact full XBRL tag
+ complete dimensions OR verified-empty `[]`; the real text-only 8-K item carries NO XBRL
context AT ALL — never `dimensions=[]` (an `[]` asserts a real XBRL fact was checked and
found undimensioned, impossible for a text source) — PLUS one honest NEGATIVE case that must
return no_proven_match and does (a run emitting nothing can never satisfy the bar)** ·
boundary import+execute test green · battery + regress floors green · the durable 150-case
gate green.

## Regeneration law for WP2
Decided from the COMPLETE final WP2 diff, not per-file arguments: the XBRL-gate file alone is
verified unreachable from WP1's output path (run_code_tier → locate_by_value only), but route/
adapter edits could touch shared files. If the final diff touches ANY WP1-reachable file →
scratch-run + byte-diff the committed WP1 outputs; any delta → owner decision BEFORE any
regeneration.

## Standing laws in force
Reproduce-first · owner rulings outrank the reviewer · laws-not-examples · no lists/registries/
over-engineering · design v5.5 byte-identical (doc-lock = the OWNER's word; Fiscal edits ONLY
its locator design + review record; FinalDesign law files = Core's alone) · commit/push =
owner words · grep-verify every patch · count tests before/after.
