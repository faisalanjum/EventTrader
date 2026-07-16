# 13 - Track C - Guidance Retirement & QA Evidence

> **STATUS (2026-07-04): v2.0 - ACTIVE DESIGN.** Owner decision: **do not production-replay old `GuidanceUpdate` nodes into new `DriverUpdate` facts.** The retired replay design is preserved in `13_Track_RetiredDesign.md`. This active Track C plan archives and retires the old guidance system, then uses old guidance only as QA/evaluation evidence for the new Driver pipeline.
>
> **Plain:** old guidance is not the new truth. The new truth is created fresh from source documents by the Driver system. Track C cleans up the old system without contaminating the new one.
>
> **Build note:** cross-doc propagation for the active live docs was applied 2026-07-04. Historical/audit files may still quote retired replay or `slice=total` wording, but they must be read only through their supersession notes.

---

## 0. Mission

- **GI-01 - One law.** Track C must retire old guidance cleanly and preserve its evidence. It must not mint production `Driver` or `DriverUpdate` records from old guidance rows.
- **GI-02 - What Track C owns.** Snapshot/archive old guidance data and code, retire old guidance graph/code/read seams, preserve old rows as QA evidence, and state the handoff to Track A/B/part 2.
- **GI-03 - What Track C does not own.** New Driver names are Track A. New `DriverUpdate` writer/read/rule machinery is Track B. The future live/update process that reads reports/transcripts/news and writes fresh `fact_type=guidance` facts is part 2 / update-process design.
- **GI-04 - No bridge.** Do not build `MAPS_TO_GUIDANCE`, `canonical_driver`, dual labels, `regenerated_from`, or a compatibility layer that lets old guidance remain a hidden production source.

## 1. Authority Boundary

| Need | Home |
|---|---|
| Driver naming, dedupe, `SAME_AS`, `BASE_METRIC`, final catalog | `10_BuildPipeline.md` / Track A |
| `DriverUpdate` IDs, writer, validator, unit/period/read rules | `12_TrackB_FactPipeline.md` / Track B |
| Old guidance archive, retirement, evidence preservation | This file |
| Live guidance producer and incremental/update process | Part 2 / update-process design |

Track C may cite Track A/B, but it does not rebuild them. Its job is to remove legacy guidance safely.

## 2. Live Legacy Census To Preserve

These counts describe what must be archived before deletion, not what must be converted.

| Legacy object | Exact state to archive |
|---|---|
| `GuidanceUpdate` | 8,432 nodes, 31 companies, 2023-01-04 to 2026-03-26 |
| Sources | 894 distinct sources: 532 `Report`, 362 `Transcript` |
| Guidance anchors | 548 `Guidance` nodes, 1:1 with legacy `label_slug` |
| Guidance periods | 237 `GuidancePeriod` nodes |
| Legacy source status props | `guidance_status` exists on only 24 of 894 sources, so it is not a reliable run ledger |
| Old concept/member evidence | 4,148 qnames and 460 member links, archive as answer-key evidence only |

## 3. Core Decision Changes From Retired v1.2

| Retired replay design | Active v2.0 design |
|---|---|
| Replay old rows into production `DriverUpdate` facts | Do not replay old rows into production facts |
| Build `legacy_name_map.json` for production writes | No production legacy name map |
| Scoped guidance mini-run creates real Drivers from old labels | No scoped production mini-run |
| Full old-vs-new replay gate decides retirement | Archive integrity + consumer-removal gates decide retirement |
| Old packet translator preserves prediction continuity | Prediction path moves to new Driver reads; old packet is retired |
| 8,416 eligible rows become new facts | All 8,432 rows become archive/QA evidence only |

## 4. Old Machinery Disposition

| Old file/family | Active disposition |
|---|---|
| `guidance_ids.py` | Keep only as shared substrate where Track B imports useful pure helpers; no `gu:` IDs survive in new facts |
| `fiscal_math.py` | Reuse as shared period math |
| `unit_resolver.py` / unit probe work | Reuse through Track B unit wiring |
| `guidance_writer.py`, `guidance_write_cli.py`, `guidance_write.sh` | Retire after archive and consumer cutover |
| `concept_resolver.py` | Retire; new concept work belongs to Track B enrichment |
| `extract/types/guidance/` and old guidance prompt profiles | Retire as production prompts. They may be archived as examples, not reused as authority |
| `builders/guidance_history.py`, `renderer/guidance.py` | Use as old-read reference during QA only; retire production use after prediction moves to Driver reads |
| `segment_aliases/` | Do not port. New grouping is deterministic member-anchored read grouping where links exist |
| `guidance_status` / `guidance_error` source props | Archive; leave inert or remove in a cosmetic cleanup. Never use as the new run ledger |

## 5. What Old Guidance Can Still Do

Old guidance is useful as evidence, not as production truth.

- **QA recall set.** Use old rows to ask: when the new producer reads the same source document, did it find the same kind of guidance where the source really supports it?
- **Archive answer key.** Preserve old qnames/member links to evaluate future concept/member enrichment, but never copy them into new facts.
- **Regression corpus.** Keep source id, company, date, quote, period, value fields, old label, old unit, old slice, and old links so future tests can explain differences.
- **Coverage floor only.** Old guidance shows what the old extractor found. It does not cap what the new system may find, and it does not force the new system to copy old mistakes.
- **Weak evidence only.** Old rows are candidates for QA, not pass/fail truth. If old rows and new rules disagree, the source document plus new Driver rules win.
- **Archive-backed QA.** After retirement, QA reads old guidance from the offline archive unless the owner explicitly chooses an inert on-graph quarantine.

## 6. New Guidance Facts Are Created Fresh

Future `fact_type=guidance` facts must be created by the new Driver pipeline from source documents.

- The producer reads reports/transcripts/news/filings directly.
- It proposes or reuses a Driver through Track A/G1/G2 rules.
- It writes through Track B `driver_write_cli` and deterministic validators.
- Uncertain or unresolved facts park/fail closed.
- No human review is part of steady-state production.
- Any one-time human/owner review belongs only to design/bootstrap/evaluation, not runtime.
- Track C does not guarantee guidance coverage continuity. Until part 2 backfills the 894 historical sources, old 2023-2026 guidance exists for QA in the archive, not as production Driver facts.

## 7. Whole-Company Slice Rule

This rule belongs to the new system and must be made explicit across docs:

> Whole-company / consolidated / total-company / no stated segment = **omitted slice**. For metric/guidance/surprise, omitted slice means consolidated whole company, not missing or unknown. For action_event, omitted slice means no slice applies or no narrower business part is stated.

This intentionally reverses the older FS-10/FS-15 rule where explicit whole-company facts used `slice=total`; `95_Supersession.md` records that reversal before broader implementation.

Do not produce `slice=total` for whole-company facts. Store a slice only when the source names a real narrower part, such as geography, product, segment, channel, customer, or member. If the uncertainty is whether the source names a real narrower part, park/fail closed. This does not override the `unknown:value` path for a real slice whose kind/value is unknown.

For `action_event`, omitted slice means no slice applies or no narrower business part is stated. "Total" display is a metric/guidance/surprise read convention, not a claim that the action is a consolidated numeric reading.

## 8. Fact-Bearing Driver Immutability

Once any `DriverUpdate` points to a `Driver`, that Driver is fact-bearing.

- A fact-bearing `Driver.name` must not be renamed.
- A fact-bearing `Driver.fact_type` must not change.
- A fact-bearing Driver must not be deleted by later catalog sync.
- Later catalog work may add `SAME_AS` or `BASE_METRIC` links.
- Full Track A must import existing fact-bearing Driver names as protected inputs and hard-fail if a sync would orphan, rename, delete, or re-type them.

This is a general Driver-system rule, not a legacy-guidance-only rule.
It codifies existing permanent-identity rules: fact type is set once, fact ids are not re-keyed, and catalog sync must not mutate Drivers already used by facts.

## 9. Archive Contract

Before any deletion, export an offline archive with:

- all 8,432 `GuidanceUpdate` nodes and every property, including old ids, `created`, `evhash16`, values, period fields, quote, source ids, old units, old labels, old slices, and old qnames;
- all old edges: `UPDATES`, `FOR_COMPANY`, `FROM_SOURCE`, `HAS_PERIOD`, `MAPS_TO_CONCEPT`, `MAPS_TO_MEMBER`;
- all 548 `Guidance` anchors with `aliases`;
- all 237 `GuidancePeriod` nodes with properties;
- the old `concept_resolver.py` registry and old guidance prompt/profile files;
- a source manifest for the 894 old sources, including source node id, labels, company, date, source type/form, external locator such as accession/report/transcript id where available, content/text hash where available, and quote/span locator where available;
- checksums, counts, export timestamp, git commit, and Neo4j database identity.

The archive is the forensic record. It must be machine-readable and restorable into a scratch database from node exports, edge exports, manifest, and checksums. It is not a production input.

## 10. Retirement Runbook

1. Freeze and drain old guidance writers/workers/queues so no new legacy rows are created after the archive starts.
2. Run archive export and verify counts/checksums.
3. Run a code search for old production consumers of `GuidanceUpdate`, `Guidance`, `build_guidance_history`, `guidance_history.v1`, old guidance extraction profiles, guidance daemons/workers, and old guidance writer scripts.
4. Update the earnings prediction path to consume new Driver reads when the new Driver system is ready.
5. Confirm no production code path reads old guidance.
6. Delete old graph nodes and old DDL with owner-approved graph writes.
7. Retire old code seams: old writer, old CLI, old shell wrapper, old concept resolver, old guidance extraction profiles, worker guidance sidecars.
8. Keep only shared substrate that Track B explicitly owns.

Deletion target:

- delete `GuidanceUpdate` and `Guidance`;
- delete only orphan `GuidancePeriod` nodes with no `DriverPeriod` label and no incoming `DriverUpdate` links;
- drop old guidance constraints/indexes;
- do not relabel old `GuidancePeriod` nodes into `DriverPeriod` as a legacy transition shortcut.

## 11. Retirement Gates

Track C is green only when all are true:

- archive count matches old graph count: 8,432 updates, 548 anchors, 237 periods, 894 sources;
- archive edge counts match the old graph, including `UPDATES`, `FOR_COMPANY`, `FROM_SOURCE`, `HAS_PERIOD`, `MAPS_TO_CONCEPT`, and `MAPS_TO_MEMBER` counts;
- archive contains old concept/member evidence;
- old writer, extraction path, daemon/worker hooks, and old guidance queues are disabled or drained;
- no production code imports/calls old guidance writer/CLI paths, old guidance extraction profiles, or old guidance history builders/renderers;
- prediction does not depend on `guidance_history.v1`;
- prediction and earnings-learner consumers tolerate empty new-guidance reads without crashing, or deletion waits for part 2 backfill;
- retirement does not require new guidance history to be backfilled first; deleting old guidance means 2023-2026 guidance is archive-only until part 2 backfills it fresh, and the owner accepts that interim production gap;
- no enabled replay/LRP/old-guidance-to-Driver writer path exists or ran in production;
- the new Driver graph has no legacy replay markers such as `regenerated_from`;
- old guidance graph objects and DDL are removed or explicitly quarantined as inert archive-only residue.

## 12. Cross-Doc Updates Applied

- `95_Supersession.md`, `03_Slices_FactScope.md`, `09_DriverUpdate_Fields.md`, `11_TrackB_DriverUpdate_Census.md`, and `12_TrackB_FactPipeline.md`: record and align the slice-rule reversal so explicit whole-company/total facts also store omitted slice, not `slice=total`.
- `10_BuildPipeline.md` / Track A graph sync: add fact-bearing Driver immutability as a hard sync guard.
- `05_Periods.md`, `11_TrackB_DriverUpdate_Census.md`, `12_TrackB_FactPipeline.md`, `66_IssuesToBeHandled.md`, `90_OpenItems.md`, and `95_Supersession.md`: remove old replay/regeneration/rewire/both-label-transition expectations; Track C archives and retires old guidance instead.
- `00_Coverage.md`: list docs `11`, `12`, `13`, and `66`.
- `90_OpenItems.md`: Track C row should say archive/retire old guidance, not replay old nodes; move old field-map/reuse/member-company reconciliation wording to Track B, part 2, or archive-QA homes.
- Prediction/earnings skill docs: remove dependency on old `guidance_history.v1`; new guidance comes from Driver reads.
- Update-process plan: define the new per-source, per-fact-type run ledger. Do not reuse `guidance_status`.

## 13. What Track C Does Not Build

Track C does not build:

- the live guidance producer;
- incremental refresh;
- all-source backfill;
- new Driver catalog generation;
- `DriverUpdate` writer/read machinery;
- concept/member enrichment;
- old-to-new production replay;
- scoped production guidance mini-run;
- packet compatibility bridge;
- human-in-the-loop review flow.

Those belong to Track A, Track B, or the actual update-process design.

## 14. Minimalism Proof

The old replay path created extra machinery for little lasting value: `legacy_name_map`, scoped catalog mini-run, legacy replay producer, replay gates, packet translator, and many whitelist classes. Since old guidance is not production truth, all of that is removed from the active Track C plan.

The minimal Track C deliverable is now:

1. archive old guidance completely;
2. retire old guidance code and graph objects;
3. preserve old data as QA evidence;
4. keep new Driver production clean and source-document based.

## 15. Drafting Record

- **v1.2 retired:** production replay of old `GuidanceUpdate` rows into new `DriverUpdate` facts. Preserved in `13_Track_RetiredDesign.md`.
- **v2.0 active (2026-07-04):** owner decision reversed the center of Track C. Old guidance is archive/QA-only; real guidance facts are produced fresh by the new Driver pipeline.
