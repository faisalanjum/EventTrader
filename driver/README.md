# `driver/` — the Driver + DriverUpdate system (single home)

**What lives here (target layout — filled in gradually):**
```
driver/
├── core/          ← the shared core: ids, period, units, writer+validators, CLI, kernel, read views,
│                    and the SHARED DECOMPOSER (label/claim → identity signals; one for all channels,
│                    built when the pilot needs it). SINGLE-OWNER (Fable). Channels NEVER edit or
│                    import its internals.
├── channels/      ← one folder per proposer channel (fiscal_ai, guidance, learner, dcm, analyst_news,
│                    action_feed…). Each implements only: SELECT · FETCH · SUBMIT.
├── relocation/    ← the relocation engine (metric-lane update engine; serves all channels).
├── experiments/   ← (eventually) EXP keys, fixtures, gauntlet assets from .claude/plans/Drivers/experiments/.
└── docs/          ← (eventually) the design law moves here from .claude/plans/Drivers/.
```
Existing WIP code migrates here AT THE END (see the porting manifest); new code is born here.

## The three rules (binding on every bot)
1. **Write only inside your folder.** Cross-folder contact = the packet contract + the core CLI — never
   imports of another folder's internals.
2. **`core/` is single-owner.** Channels call the CLI; the CLI is the only pen that writes to Neo4j.
3. **The live guidance skill scripts** (`.claude/skills/earnings-orchestrator/scripts/`) **are read-only
   for everyone** — the core imports them (e.g. `fiscal_math.py`), never copies or edits them.

## Authority
**`.claude/plans/Drivers/FinalDesign/` is the design-law authority** for everything in this tree (record model,
naming, identity, validators, supersessions). The owner will eventually consolidate it into a few files — until
then rules and supersessions are added there on the fly; on any conflict, FinalDesign wins over code comments
and READMEs. Key entries: `15_CandidateFactPacket.md` (the frozen packet spec) · `ChannelContract.md` (the
channel input contract — the only file channel builders need) · `95_Supersession.md` (old→new rule reversals).

## The channel contract
One file, contract-only, read it before building any channel:
`.claude/plans/Drivers/FinalDesign/ChannelContract.md` (moves to `driver/CONTRACT.md` at the end-reorg).

## The flow (what triggers what)
```
TRIGGERS                          CHANNEL (SELECT·FETCH·SUBMIT)      FACT LANES it emits
new filing/transcript ingested → learner (post-8-K attribution)  → any lane (metric/guidance/surprise/action)
                               → guidance producer               → guidance (pre-earnings look-back cadence)
                               → action_event feed               → action_event (8-K item codes)
vendor refresh (weekly)        → fiscal_ai                       → metric (KPI facts)
significant unexplained move   → DCM investigation               → attribution verdicts (+ any lane evidence)
news/analyst filter            → analyst_news                    → evidence + attribution
        │
        ▼
ONE packet per source event → shared decomposer → kernel (reuse/create/reject) → writer (per-lane
validators) → graph.   UPDATES thereafter run by FACT-TYPE LANE, not by channel:
metric → relocation/ (re-finds known values in each new period/source) · guidance → the guidance
producer's own cadence · action_event → event-driven lifecycle · surprise → born at earnings only.
```
Channels own CREATION (who watches what, when). Fact-type lanes own VALIDATION + UPDATE semantics — they are
code inside `core/`, never folders. Sources (10-K/Q, 8-K, transcripts, news, external) are data each channel's
charter lists — never folders either.

## The 4 fact_types (owner ruling D2: updates organize by fact type, NOT by discovering channel)
A fact_type is a STAMP on every Driver (set once at admission, permanent) — never a folder. One writer serves
all four lanes; the lane decides which rules fire:

| fact_type | its rules in core | created by (channels) | updated how (the D2 matrix) |
|---|---|---|---|
| **metric** | state ladder (increased/decreased/…); consensus-comparison FORBIDDEN on this lane | fiscal_ai, learner | → `relocation/` re-finds known values in each new period/source |
| **guidance** | period required; `value_text`/`conditions` allowed here ONLY; raised/lowered derived at read | guidance channel, learner | → the guidance channel's own pre-earnings look-back cadence |
| **surprise** | born only from a stated actual-vs-expectation; code computes position, producer judges beat/miss | learner + guidance channel, at earnings | → never "updated" — each earnings mints new ones |
| **action_event** | the 10-state lifecycle ladder (rumored→announced→…→completed/failed); sentinel periods illegal | action_feed, learner | → event-driven: the next event advances the state |

Why lanes are not folders: the mapping is many-to-many — the learner emits ALL four lanes, and the metric lane
is fed by multiple channels. Lane folders would shred one bot across four directories and duplicate the writer.

## Status (2026-07-15)
- Design law FROZEN: S2 packet spec (owner-approved 2026-07-14) + FinalDesign 01–14/66/95 + kernel v3.4.
- `core/` build (S3) starts on owner GO — TDD, dry-run default, zero Neo4j writes during testing.
- Old exploration-era code: archived at `archive/drivers/` (see its ARCHIVED.md).
