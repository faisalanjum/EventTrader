# PHASE-6 READER SCREEN — APPROVAL PACKAGE v13 (2026-07-23; paper only, ZERO AI calls/spend)

**ONE plan only (v1/v2 superseded in full). This is a SCREEN — not production certification.**
Holds: Route C · 150-case exam (pre-harvest) · harvest · commit · push.

## 1. Boundary (binding)
The reader LOCATES and COPIES exact evidence from prepared blocks and PROPOSES a match to a
read-only anchor. Code re-pulls every quote by id and verifies span/Decimal/sign/unit. Core
alone interprets meaning, decides identity, writes. (ChannelContract v1.0 · FinalPlan §5D.)

## 2. The frozen screen set — v13 (answers separated; competitors included)
- VERSION: v13 — the SINGLE current version; every earlier figure superseded.
- MODEL INPUTS: `phase6_screen_call_1..3.json` (≤8 cases and ≤100KB each) — **19 fact rows from 8 independent tables · 7 filings · 4 companies (AA, AAL, ADM, AEE) — the honest independence unit is 8 tables** · 93 one-occurrence requests (93/93 cells span-mapped)
  Tables are SHARED (8 physical tables, deduplicated) and include EVERY row — headings
  like "Operating revenues:" live in the SOURCE, never in the ask (asks carry label +
  ordinal only). **No expected answers or truth locations appear anywhere in model inputs**
  (mechanically verified: leak check CLEAN).
- HIDDEN GRADER TRUTH: `phase6_screen_answers_HIDDEN.json` (sha `b4a26aa5e356…`) —
  grader-only, never sent to a model; expected occurrence id per request from audited
  truth v4.
- Ask disambiguation: label + section context + ORDINAL numeric position in the row —
  a stated SCREEN simplification (mechanical, value-blind); production asks will carry
  real column headers from the certified tracker.
- Unfinished categories: FOUR of five (8-K prose · prepared remarks · Q&A · numberless);
  tables stand at 19 rows / 8 independent tables of the 50-case target.
- Repeatable validator: `phase6_screen_validate.py` — 37 checks; response keys must EQUAL the allowed keys exactly (extra-field and abstention-extra-evidence attacks RED-pinned live and killed); call files = 37,110 + 50,932 + 29,958 = 118,000 bytes; output = len(json.dumps(full_batch)) = 27,589 bytes (37/37 PASS, unmasked exit 0).
- Manifest: `phase6_screen_manifest_v2.json` sha `05592af609a4f8da…` · hidden answers `b4a26aa5e356…` (refreshed LAST). Version v13; validator 37/37.

## 3. Prompt + I/O (exact)
The verbatim prompt is EMBEDDED in the batch file itself (its `prompt` field IS the law);
one occurrence per request; the batch file is the complete model input.

## 4. Cost — from the serialized model inputs on disk
3 call files (37,110 + 50,932 + 29,958 = 118,000 bytes) -> **118,000 input bytes = ~29k tokens + 27,589 output bytes = ~6.9k tokens per tier (both DERIVED from serialized files) · 3 calls/tier · 3 tiers ~ 88k input.** Reproducible: `wc -c` the batch files ÷ 4.
Recommended screen cap: **250k tokens**.

## 5. Grading + zero-wrong bar
FULL-FIELD grading per FinalPlan §5D (in the hidden file, per request): occurrence id AND block id must match; copied_label must equal the EXACT SOURCE label slice (source prints "Cargo" — never the vendor's "Cargo Revenue"); copied_period_evidence must EQUAL, as an exact array, the cell's audited aligned_headers_verbatim (80.6 -> ["3 Months Ended March 31,", "2025"]); every returned field incl. request_id AND anchor_id is graded; any wrong accept fails the
tier for this lane; abstains are counted, never penalized as wrong. Screen outcomes inform
the ladder; production certification remains a SEPARATE later package with the labeled
lanes and unseen cases.

## 6. Model ladder (cheapest-reliable; owner 2026-07-23)
approved local AI (OWNER TO SPECIFY) → Haiku, easy groups only (Haiku-first amendment
awaiting "record it") → Sonnet-5-low (default) → Luna (OWNER TO SPECIFY). Escalation =
explicit outer triggers only (invalid output · verifier conflict · ambiguity · no-match);
no /advisor (advisor.md:311-341); no metered API, ever.

## 7. Core validation — stated precisely
Core's writer CANNOT directly validate raw reader answers today: the existing check
(`driver_write_cli.py` dry-run FACT-16 validators, committed at c2f021a) consumes
PACKETS, not reader output. Screen answers are therefore graded channel-side only
(mechanical id-equality + the code quote-verification). Reader→packet flow and the
independent Core FALSIFIER are Core's Phase-6 deliverables and ENTRY CONDITIONS for
production certification — the screen makes no Core claim.

## 8. Billing transport (canonical: BILLING §"The ONE lever")
Interactive lane only (`cli` entrypoint = subscription); `claude -p`/SDK = `sdk-cli` =
metered pool — banned. At GO: record the observed entrypoint tag before the first call;
any `sdk-cli` observation = hard stop.

## 9. Owner decisions needed
1. Approve the screen (8 independent tables / 93 requests, ≤250k-token cap) — or hold for the labeled lanes first.
2. Ladder entries: confirm Sonnet-5-low + Haiku-low; supply or strike local-AI and Luna.
3. "Record it" on the saved Haiku-first amendment.
4. Approve the frontier-model key method for the FOUR unfinished categories (no-human ruling recorded; method held).


## 10. Existing-truth inventory (census of graded exam artifacts, zero AI)
Raw graded entries available for reuse triage (adjudication-quality filtering is the
next paper step — these are CANDIDATES, not yet accepted truth):
EXACT counts (his audit): exam_annual 44 + exam_mafresh 36 + exam_madrift 8 = 88 ·
exam_transcript 23. CATEGORY CORRECTION: the 88 are 10-K/Q relocation cases — they
CANNOT fill the unclear-8-K-TABLE category (they may seed a separate tagged-filing
lane if the owner wants one). Therefore: 8-K tables 8-of-50 independent (+42 tables to LABEL) · prepared
remarks + Q&A: 23 candidates toward 100 (rest labeled) · 8-K prose 0 · numberless 0
— the labeling session (double-labeling proposal §11) carries the bulk.

## 11. Truth expansion
See `Phase6_TruthExpansion_Plan_2026-07-23.md` — 50/category plan: audited-truth reuse first, blind Codex+Fable double-labeling proposal (frontier-model adjudication (owner no-human ruling; method held)), three review passes minimum. Owner GO required before any labeling call.
