# WORKORDER_STATUS - FableExperimentWorkOrder v1.6 execution board

Bootstrap (WP-0) completed: 2026-07-09T01:05:17Z

## Bootstrap facts (WP-0)
- git HEAD: 30ccab394eef9110cd0ade8bdcf6729940bd501b (branch main)
- working tree at bootstrap: 352 uncommitted files (pre-existing; NOT touched by this program)
- plan_sha256: 51966848183e2a48ba3d4faac36c5b352027939fd962a90798a73e8cd2ed7472 (VERIFIED == work order header)
- workorder_sha256: 554529dde8e972b29a3e941b730b5eadf2e666d6769a27268886ffc6aa6cd164
- Neo4j read access: CONFIRMED via env-first creds; live counts at bootstrap: Fact=13775616 Report=42633
- OPENAI_API_KEY: present (env-first; embeddings lane; not used by EXP-1)
- ANTHROPIC_API_KEY: UNSET (billing guard 1.8.3 clean)
- Candidate model IDs (1.3): cheap=claude-haiku-4-5-20251001 | strong=<sonnet: resolve alias at run start> | escalation=claude-opus-4-8 | fable=claude-fable-5 (adjudication only)
- Runner: venv/bin/python3 (Python 3.10.12, neo4j-driver 5.28.1); env-first only (load_dotenv unreliable in venv)

## Live counts (use these, not stale work-order estimates)
- Fact total: 13775616 (work order estimate was ~9.9M; live figure governs, per P19)
- Report total: 42633

## Codex triage guardrail
- Durable Fable/Opus rulings must not live only in chat.
- If Fable/Opus already recorded the issue, Codex verifies the pointers and leaves it alone.
- If a durable issue is missing, Codex adds the smallest note to the right experiment artifact (exhibit, ambiguity register, O12 bundle, manifest, census binding, or this board).
- FinalDesign docs stay untouched unless owner/Fable explicitly ratifies a back-port.

## Status board (one row per package)

| Package | State | run_id | Gate | Blockers / notes |
|---|---|---|---|---|
| WP-0 bootstrap | DONE | - | - | tree + BUDGET.json + board created 2026-07-09T01:05:17Z |
| WP-FA corpus | PENDING | - | - | 0-LLM; O2 Fable sign-off pending |
| EXP-1 census | DONE | - | no-gate (descriptive) | 7 aggregates -> exp1_xbrl/census.json |
| EXP-1 dry-run | IN_PROGRESS (full materialization + determinism passed) | 2026-07-09T14-25-39Z_dryrun | - | 60 filings emitted 9,603 facts across all 12 companies; determinism PASS sha256 64518e74...60522c6; verifier/PIT/gate still pending |
| K-pairs.v1 | PENDING | - | - | protocol + Fable lock (pre EXP-0) |
| K-pairs.v2 | PENDING | - | - | needs FREEZE (mining) |
| K-reader | PENDING | - | - | needs frozen chunks |
| K-route | PENDING | - | - | needs FREEZE + candidate pool |
| K-fields | PENDING | - | - | needs O2-signed events + Fable |
| K-stamp | PENDING | - | - | needs F-C run records |
| EXP-0 graders | PENDING | - | - | needs K-pairs.v1 lock |
| WP-FC-EDITS | PENDING | - | - | 11 files; GATED on owner checkpoint |
| WP-FC-RUN | PENDING | - | - | needs EXP-2 decision |
| EXP-2 reader | PENDING | - | - | needs EXP-0 + FC-EDITS + K-reader |
| EXP-3 router | PENDING | - | - | needs FREEZE + K-route |
| EXP-4A judge | PENDING | - | - | needs K-pairs.v2 |
| EXP-4B stamp | PENDING | - | - | needs FC-RUN + K-stamp |
| F-C FREEZE | PENDING | - | - | needs EXP-4B |
| EXP-5 fields | PENDING | - | - | needs K-fields |
| EXP-6 twins | PENDING | - | - | needs EXP-1 + EXP-5 |

## Log
- 2026-07-09T01:05:17Z WP-0 bootstrap complete; EXP-1 schema-binding (step 0) started.
- 2026-07-09T01:34:55Z EXP-1 schema-binding: (a)/(c) CLEAN; (b) axis<->member = O13 (typed-dim misalignment: 2637 contexts, 1290 slice-touching) -> STOPPED, ra_0001 filed, handed to owner/Fable.
- 2026-07-09T02:50:49Z O13 RATIFIED (owner): binding (b) = explicit-dims positional pairing, drop typed dims, fail-closed skip+count residual. ra_0001 resolved. Census aggregates starting.
- 2026-07-09T13:34:44Z EXP-1 census DONE (census.json). comma-values 80.7% (strip confirmed); no-context 15109 (fail-closed skip cohort); null-pOR(COMPLETED)=0 AND multireg=0 corpus-wide -> P4f/P4h fixtures must be SYNTHETIC at dry-run (extends D6); unit whitelist live name = 'iso4217:USDshares'(is_divide=1). EXP-1 dry-run half remains (needs FA_selection-lite; 0-LLM).
- 2026-07-09T14:07:18Z EXP-1 dry-run: inputs built (FA_selection draft + fixture_resolutions); FS-18/O14 + fixture caveat recorded. STOPPED on first ambiguity ra_0002: value canonicalization (real canonicalize_value has no base-units->millions path; conflicts 'use real resolver' vs required m_usd millions). ambiguity_register.json opened. Handed to owner/Fable.
- 2026-07-09T14:35:00Z Fable ruling recorded by Codex while Opus was busy: ra_0002 CLOSED. Classification = implementation clarification of XBRL P4a/P4c, not UNIT-11/OD-10 amendment. XBRL facts do NOT call the text canonicalizer; materializer applies fixed table at emit time: iso4217:USD -> round(raw/1e6,6) m_usd; shares -> raw count; iso4217:USDshares(is_divide=1) -> raw usd; all else skip+count, plus usd_bare_pershare_suspect guard. ambiguity_register entries cleared; EXP-1 dry-run ready to resume with a fresh run dir + manifest.
- 2026-07-09T14:25:39Z EXP-1 dry-run RESUMED with named fix: Fable ruling accepted, ra_0002 closed (fixed P4c/P4a conversion table, no text canonicalizer). Run dir exp1_xbrl/runs/2026-07-09T14-25-39Z_dryrun. instant_off_pOR_by_one = observation counter only; P4b strict equality UNCHANGED.
- 2026-07-09T15:10:00Z Fable source-order / inference-gap ruling recorded in exp1_xbrl/o12_bundle_notes.json: Driver birth source must not affect XBRL linking/materialization; missing links are safe under-attribution gaps; add read-derived xbrl_link_status={active,revoked,none} as-of; no provisional materialization ever; add reporting-only bias splits for thin/no-10-K-Q evidence and twin_suspect_rate by birth source. No experiment bar changed.
- 2026-07-09T16:13:02Z Fable alignment pass: period-convention ruling FORMALIZED as binding (d) - stored Period dates are EXCLUSIVE; duration effective_end = end_date - 1d, instant effective = stored - 1d (starts UNSHIFTED per period_start_check.json STARTS_UNSHIFTED_OK_TO_APPLY); P4b/P14/gp_ids/build_known/P4h all run on EFFECTIVE dates; instants at effective==pOR are PRIMARY. SUPERSEDES the 14:25:39Z entry's "instant_off_pOR_by_one = observation counter only; P4b strict equality UNCHANGED" phrasing: that counter is RETIRED and P4b equality runs on effective dates. raw==pOR rows (exactly 1 LUV fact, report 0000092380-26-000004) -> SKIP + count period_end_convention_suspect + per-fact log; per-report tripwire >=5 or >1% suspect -> STOP; report_primary_window_missing warn counter added. ra_0003 filed + ambiguity_register updated (still 0 open entries). o12_bundle_notes.json completed to 7 entries (adds P4c conversion factors + binding (d); adds as-of rule for revocation transitions to xbrl_link_status). Run manifest aligned (skip_counters += period_end_convention_suspect; observation_counters instant_off_pOR_by_one -> report_primary_window_missing; write_reason promotion note now says EFFECTIVE period end). Consistency verified: no FinalDesign doc touched (grep clean); work order sha re-verified 554529dd...6164; no bars changed.

- 2026-07-09T16:35:13Z EXP-1 dual-CIK ruling APPLIED (Fable 2026-07-09): unresolved dim/member node after normalization -> skip whole fact + count slice_pairing_dualcik_unresolved; NO aliasing/qname-only/cross-CIK; AAL kept. Recorded ra_0004, ambiguity_register (closed), census binding_b.dualcik_subcase, o12_bundle (ingestion repair / future certified recovery). O13/P4f otherwise unchanged.
- 2026-07-09T16:41:17Z Work order bumped v1.6 -> v1.7 by Fable (owner instruction): O16 cheap-tier fallback policy added - optional DeepSeek V4 Flash via OpenRouter arm ('cheap_fallback', 1.3 registry + rule; 7; 8 O16; 9 budget row). Trigger = Haiku cheap-arm bar FAIL in EXP-2/3/5 or Fable-marked inconclusive; Fable authorizes; same key/sample/prompts/bars incl. invalid-rate gate; OPENROUTER_API_KEY = second conditional metered lane (key setup deferred; ANTHROPIC billing guard unchanged); cost cap 1.5x the failed arm's calls; Haiku stays default; none->Sonnet terminal rule unchanged; passing evidence informs PRODUCTION strategy only (workflow engine stays agent()-only in-program). NO BARS CHANGED. New workorder_sha256 = af491c3515c6fa04806de81d530622e9021c65c625a2c5ba3f558a29adb8599c. Manifests pin the sha at their own run time - the EXP-1 run's recorded v1.6 sha (554529dd...6164) stays historically correct; runs started from now record v1.7.
- 2026-07-09T16:55:00Z EXP-1 full materialization + determinism reported by Opus: 60 filings / 34,102 fixture facts seen; 9,603 emitted across all 12 companies; AAL dual-CIK skips counted as slice_pairing_dualcik_unresolved=2,633; generic slice_pairing_failclosed=0; entity_scoped_out=0; period_end_convention_suspect=0; report_primary_window_missing=0. Mid-pass implementation fix recorded in manifest: entity-scope must compare to registrant Company.cik, not accession/report-id prefix CIK. Determinism PASS: two full runs byte-identical, sha256 64518e7474c102ecdebf5cc9483504ab97822f161b9dafee8211009df60522c6. Remaining EXP-1 steps: X-XL0 independent verifier, PIT-menu proof, final gate.
