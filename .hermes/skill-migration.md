# EventMarketDB Claude-to-Hermes Skill Migration

## Batch: top-level skills migrated on 2026-04-24/25 session

| Claude source | Hermes destination | Type | Dependencies | Verification | Status |
|---|---|---|---|---|---|
| `.claude/skills/evidence-standards/SKILL.md` | `software-development/eventmarketdb-evidence-standards` | Hermes skill | none | `skills_list`, `skill_view` | migrated |
| `.claude/skills/earnings-prediction/SKILL.md` | `software-development/eventmarketdb-earnings-prediction` | Hermes skill | `eventmarketdb-evidence-standards` | `skills_list`, `skill_view` | migrated |
| `.claude/skills/earnings-learner/SKILL.md` | `software-development/eventmarketdb-earnings-learner` | Hermes skill | `eventmarketdb-evidence-standards`, `eventmarketdb-earnings-prediction` | `skills_list`, `skill_view` | migrated |
| `.claude/skills/extract/SKILL.md` + `.claude/agents/extraction-primary-agent.md` + `.claude/agents/extraction-enrichment-agent.md` + extract support tree | `software-development/eventmarketdb-extract` | Hermes skill with linked references | `eventmarketdb-evidence-standards`; extraction support files under references | `skills_list`, `skill_view`, linked file read | migrated |

## Batch: foundational data-access micro skills migrated on 2026-04-25 session

| Claude source | Hermes destination | Type | Dependencies | Verification | Status |
|---|---|---|---|---|---|
| `.claude/skills/neo4j-schema/SKILL.md` | `software-development/eventmarketdb-neo4j-schema` | Hermes schema/reference skill | `eventmarketdb-evidence-standards`, `eventmarketdb-pit-envelope` | `skills_list`, `skill_view` | migrated |
| `.claude/skills/pit-envelope/SKILL.md` | `software-development/eventmarketdb-pit-envelope` | Hermes PIT contract skill | `eventmarketdb-evidence-standards`, `eventmarketdb-neo4j-schema` | `skills_list`, `skill_view` | migrated |
| `.claude/skills/entity-queries/SKILL.md` + `.claude/agents/neo4j-entity.md` | `software-development/eventmarketdb-neo4j-entity` | Hermes data-access skill with source refs | schema, PIT, evidence | `skills_list`, `skill_view` | migrated |
| `.claude/skills/report-queries/SKILL.md` + `.claude/agents/neo4j-report.md` | `software-development/eventmarketdb-neo4j-report` | Hermes data-access skill with source refs | schema, PIT, evidence | `skills_list`, `skill_view` | migrated |
| `.claude/skills/transcript-queries/SKILL.md` + `.claude/agents/neo4j-transcript.md` | `software-development/eventmarketdb-neo4j-transcript` | Hermes data-access skill with source refs | schema, PIT, evidence | `skills_list`, `skill_view` | migrated |
| `.claude/skills/news-queries/SKILL.md` + `.claude/agents/neo4j-news.md` | `software-development/eventmarketdb-neo4j-news` | Hermes data-access skill with source refs | schema, PIT, evidence | `skills_list`, `skill_view`, reference file check | migrated |
| `.claude/skills/xbrl-queries/SKILL.md` + `.claude/agents/neo4j-xbrl.md` | `software-development/eventmarketdb-neo4j-xbrl` | Hermes data-access skill with source refs | schema, PIT, evidence | `skills_list`, `skill_view` | migrated |
| `.claude/agents/neo4j-vector-search.md` | `software-development/eventmarketdb-neo4j-vector-search` | Hermes vector-search skill with source ref | news/transcript, PIT, evidence | `skills_list`, `skill_view`, reference file check | migrated |
| `.claude/skills/bz-news-api-queries/SKILL.md` + `.claude/agents/bz-news-api.md` + `.claude/references/neo4j-news-fields.md` | `software-development/eventmarketdb-bz-news-api` | Hermes wrapper skill with source refs | PIT, evidence | `skills_list`, `skill_view`, reference file check | migrated |
| `.claude/skills/alphavantage-earnings/SKILL.md` + `.claude/agents/alphavantage-earnings.md` | `software-development/eventmarketdb-alphavantage-earnings` | Hermes wrapper skill with source refs | PIT, evidence | `skills_list`, `skill_view` | migrated |

## Batch: Kubernetes operations skill migrated on 2026-04-25 session

| Claude source | Hermes destination | Type | Dependencies | Verification | Status |
|---|---|---|---|---|---|
| `.claude/agents/k8s-status.md` | `software-development/eventmarketdb-k8s-status` | Hermes Kubernetes ops skill with source ref | `eventmarketdb-k8s-queues` for queue/backlog questions | `skills_list`, `skill_view`, reference file check | migrated |

## Batch: Hermes self-improvement setup on 2026-04-24 session

| Source/context | Hermes destination | Type | Dependencies | Verification | Status |
|---|---|---|---|---|---|
| Hermes docs + EventMarketDB migrated skill inventory | `software-development/eventmarketdb-skill-maintainer` | Hermes maintenance skill | `hermes-agent`, `claude-to-hermes-skill-migration` | `skills_list`, `skill_view`, duplicate scan | created |
| Hermes docs on SOUL/skills/cron/memory/personality + live setup review | `software-development/eventmarketdb-workflow-router` | Hermes orchestration/routing skill | EventMarketDB focused skills | `skill_view` | created |
| Hermes docs on cron/operator setup + live EventMarketDB k8s skills | `software-development/eventmarketdb-operator-loop` | Hermes operations loop skill | `eventmarketdb-k8s-status`, `eventmarketdb-k8s-queues` | `skill_view` | created |
| `CLAUDE.md` critical rules + migrated skill routing | `/home/faisal/EventMarketDB/.hermes.md` | project context | EventMarketDB skills | file read; context precedence docs | created |

## Batch: skill patches on 2026-04-27 session

| Skill patched | Version | Patch source | Changes | Verification | Status |
|---|---|---|---|---|---|
| `software-development/eventmarketdb-k8s-queues` | 1.0.0 → 1.1.0 | live XBRL queue deep-dive + 9 AM weekly skill review | Added: (1) SELF-EXIT pod-restart triage procedure with manifest envs `SELF_EXIT_ENABLED`/`JOB_COUNT_THRESHOLD` and `[SELF-EXIT]` log signature; (2) throughput fallback via `Initializing XBRL processing` lines (TZ-aware awk cutoff across current + `--previous` containers) inside the ETA procedure; (3) four pitfall bullets explicitly labeled **By design — not a bug**: SELF-EXIT restarts, Neo4j cgroup-pinned 85–95% node memory with `restart_count=0`, `DNSConfigForming` warnings on host-net pods only, queue-composition-by-accession-year heuristic for backfill-vs-fresh | `skill_view` content check, frontmatter version | patched |
| `software-development/eventmarketdb-operator-loop` | 1.0.0 → 1.1.0 | follow-up patch after Claude/Hermes cross-review of cron template | Added OK / WATCH / ACTION format directive, "only exceptions" rule, and explicit benign-pattern filter list (clean XBRL SELF-EXIT restarts; planned calc-arcrole backfill if draining; DNSConfigForming host nameserver-limit noise; Neo4j fixed-100Gi allocation when Ready + restart_count=0). Updated cron prompt template inside skill to match. Cron job `74492cb30798` ("EventMarketDB weekday operator check") prompt updated via `hermes cron edit` to consume the new template. | `skill_view`, `hermes cron list` shows new prompt | patched |

## Notes

- These are Hermes-native adaptations, not blind copies.
- Original Claude source files are preserved as linked references under each Hermes skill.
- The extraction skill explicitly documents that Claude `Agent(...)` syntax is not available in Hermes and should be adapted through `delegate_task`, Claude Code CLI, or deterministic scripts.
- Extraction support files were copied from `.claude/skills/extract` excluding `__pycache__`/`.pyc` artifacts.
- The copied nested Claude `extract/SKILL.md` was renamed to `references/extract/source-claude-extract-skill.md` so Hermes does not discover it as a separate stale `extract` skill with Claude-only `Agent(...)` syntax.
- The existing generic Hermes `neo4j-entity` skill was left intact. For EventMarketDB work, prefer the new `eventmarketdb-neo4j-*` skills because they preserve the Claude query/agent references and PIT envelope routing.

## Created Hermes skill paths

- `/home/faisal/.hermes/skills/software-development/eventmarketdb-evidence-standards/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-earnings-prediction/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-earnings-learner/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-extract/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-neo4j-schema/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-pit-envelope/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-neo4j-entity/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-neo4j-report/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-neo4j-transcript/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-neo4j-news/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-neo4j-xbrl/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-neo4j-vector-search/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-bz-news-api/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-alphavantage-earnings/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-k8s-status/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-skill-maintainer/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-workflow-router/SKILL.md`
- `/home/faisal/.hermes/skills/software-development/eventmarketdb-operator-loop/SKILL.md`
- `/home/faisal/EventMarketDB/.hermes.md`

## Next suggested batch

Earnings orchestration / task setup skills:

- `earnings-task-setup`
- `earnings-planner`
- `earnings-orchestrator`
- `earnings-attribution`
- `guidance-inventory`
- optional: `yahoo-earnings`, `perplexity-*`, `news-driver-*`

These will make the migrated prediction/learner/data-access skills executable as full workflows.
