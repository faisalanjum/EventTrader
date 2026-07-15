# Pre-consolidation freeze snapshot — 2026-07-15

**NON-AUTHORITY HISTORICAL RECORD.** This directory holds the Phase-1 freeze manifest for the
FinalDesign consolidation (plan: `../../CONSOLIDATION.md` §13). Nothing here is a rule source.

- `MANIFEST.json` — SHA-256, byte count, line count, and git provenance for all **33 source files**
  at freeze time (totals verified: 11,320 lines / 1,362,208 bytes). The three previously untracked
  sources were committed unchanged in `49f1cd8` immediately before this manifest was written.
- **Freeze rule:** from 2026-07-15 the 33 source files are not edited. They remain the rule
  authority (read via `CONSOLIDATION.md` first) until the four target files pass the §14 zero-loss
  checks; Phase 5 then moves the originals into this directory byte-for-byte, verified against
  this manifest.
- The only sanctioned future changes to live-continuing files (`ChannelContract.md`, the frozen
  packet) are the owner-approved amendments recorded in `CONSOLIDATION.md` §10.2 (rulings of
  2026-07-15), applied at the Phase-3 contract review — this manifest preserves their
  pre-amendment baseline.
