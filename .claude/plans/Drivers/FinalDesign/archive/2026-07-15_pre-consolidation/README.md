# Pre-consolidation archive — frozen 2026-07-15, populated at Phase 5 (2026-07-16)

**NON-AUTHORITY HISTORICAL RECORD — EVIDENCE ONLY.** Nothing in this directory is a rule source.
Current design law lives in the four live files at the FinalDesign root:
`FINAL_DESIGN.md` (the front door — start here) · `ChannelContract.md` · `BUILD_AND_OPERATIONS.md` ·
`STATUS_AND_HISTORY.md`. The live root also keeps `15_CandidateFactPacket.md` (owner-frozen packet,
temporary fifth live file), plus the two experiment files `FableExperimentPlan.md` (byte-pinned) and
`FableExperimentWorkOrder.md` (edited at Phase-5 step 21c; its frozen original is archived here) —
SEVEN root files + this `archive/`.

## What is here

- `MANIFEST.json` — SHA-256, byte count, line count, and git provenance for all **33 source files**
  at the 2026-07-15 Phase-1 freeze (totals verified: 11,320 lines / 1,362,208 bytes). The three
  previously untracked sources were committed unchanged in `49f1cd8` immediately before the
  manifest was written.
- **The 29 archived originals** (byte-for-byte, each verified against `MANIFEST.json` at its move):
  the two ratified-design originals (`FableAdmissionKernelDesign.md`, `XBRLIntegrationDesign.md`,
  archived 2026-07-15 after integration + the archive-gate reader test) and the 27 remaining
  sources (archived 2026-07-16 at Phase 5, per the execution card).
- **Three pre-amendment / frozen-original snapshots** (manifest-verified): `ChannelContract.pre-amendment.md`
  and `15_CandidateFactPacket.pre-amendment.md` (the live copies carry the two 2026-07-15 owner
  amendments Q4/Q1-ext), plus `FableExperimentWorkOrder.md` (the pre-21c frozen original,
  sha `4911a22f…`).
- `CONSOLIDATION.md` — the full consolidation audit, migration map, owner-decision trail (§10.2),
  and the complete round-by-round verification record (§16). Archived at Phase-5 step 7; it remains
  the evidence trail, never a fifth rule source.
- `READER_TEST_RECORD_*.md` — durable blank-context reader-test records (append-only; a record is
  never overwritten — corrections are labeled additive addenda; each rerun writes a new file).
  The Phase-5 definitive record is `READER_TEST_RECORD_2026-07-16_phase5-final-run13.md`
  (all earlier runs' records are preserved beside it, append-only — each carries its own grade
  history and any withdrawal/regrade addenda; the banner-named file above is always the definitive one).

## Conventions

- **History is append-only:** archived originals are never edited or turned into pointer stubs;
  git history is preserved (files were `git mv`'d).
- **Versioned snapshots:** any LATER archival of a live-continuing file lands at a VERSIONED
  filename beside its earlier snapshot (e.g. `15_CandidateFactPacket.v1.1-post-amendments.md`) —
  an archived snapshot is never overwritten.
- **On any suspected conflict** between an archived original and the live files: the live files
  win; the owner rulings and named corrections are recorded in `CONSOLIDATION.md` §10.2/§16 and
  `STATUS_AND_HISTORY.md` §4.
