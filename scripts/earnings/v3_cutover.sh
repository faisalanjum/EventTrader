#!/usr/bin/env bash
# LearnerLoopRevamp.md §10.2 — round-6 fresh-start cutover.
#
# One-shot operational script — DO NOT run automatically. Invoke manually
# AFTER all 4 commits land + AFTER pausing the production pipeline (e.g.,
# `kubectl scale -n processing deployment/extraction-worker --replicas=0`
# or whatever stops live learner runs).
#
# Symlink note (commit 4.4 patch): ``earnings-analysis/Companies`` is a
# symlink to a sibling Obsidian-vault directory in production. Plain
# ``find earnings-analysis/Companies …`` does NOT traverse a symlink at
# the start path. All find invocations under Companies/ use ``find -H``
# (follows ONLY the command-line symlink — narrower than ``-L`` which
# would chase any nested symlink inside the tree; correct safety
# posture for a destructive delete script). Without ``-H`` the script
# silently misses every stale learning artifact under Companies/,
# defeating the entire fresh-start cutover. Pre-fix evidence: cutover
# #1 on a real production tree reported "deleted: 0 result.json files"
# while a stale attribution_result.v2 file remained at
# Companies/AVGO/events/Q4_FY2023/learning/result.json — the v3
# validator rejected it on the next learner run, exposing the bug.
#
# What it does:
#   1. Backs up existing learnings/ + every Companies/*/events/*/learning/
#      result.{json,md} into earnings-analysis/.pre-v3-cutover-backup/.
#      Backups stay for ~1 quarter (deletable once the v3 loop has
#      proven itself in production).
#   2. Wipes the learnings library (ticker/*.json + global.json + .lock).
#   3. Wipes every events/*/learning/{result.json, result.md, thinking.md,
#      subagents/} so the next learner run for that quarter regenerates
#      as v3 (the orchestrator's recovery path triggers on the existing
#      result.json — wiping forces a fresh learner invocation; the
#      thinking.md + subagents/ wipe ensures no v2-era reasoning bleeds
#      into the next run's audit trail).
#   4. Initializes an empty v3 global.json (validator-compatible).
#
# What it does NOT do:
#   * It does not touch events/*/prediction/result.json (existing v1
#     predictions are preserved — they have lesson_labels=[] which is
#     correct given the now-empty library).
#   * It does not regenerate context_bundle.json files. The next
#     prediction run will rebuild them with the empty learning_context.
#
# Per-ticker learnings/ticker/{TICKER}.json files are created on demand
# by append_ticker_lesson at first write (existing behavior).
#
# DRY-RUN procedure (recommended before production cutover):
#   1. Copy earnings-analysis/ to a sandbox directory.
#   2. Run this script with EARNINGS_ROOT pointing at the sandbox.
#   3. Verify: empty learnings/global.json with valid JSON, no
#      ticker/*.json files, no events/*/learning/result.json files,
#      events/*/prediction/result.json files preserved.
#
# Usage:
#   bash scripts/earnings/v3_cutover.sh                 # production tree
#   EARNINGS_ROOT=/tmp/sandbox bash scripts/earnings/v3_cutover.sh   # dry-run

set -euo pipefail

EARNINGS_ROOT="${EARNINGS_ROOT:-earnings-analysis}"
BACKUP_ROOT="${EARNINGS_ROOT}/.pre-v3-cutover-backup"

if [[ ! -d "${EARNINGS_ROOT}" ]]; then
  echo "ERROR: ${EARNINGS_ROOT} not found — run from repo root or set EARNINGS_ROOT" >&2
  exit 1
fi

echo "==> v3 cutover starting at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "    EARNINGS_ROOT=${EARNINGS_ROOT}"
echo "    BACKUP_ROOT=${BACKUP_ROOT}"
echo ""

# ── Step 1: Backup ───────────────────────────────────────────────────────
echo "==> Step 1/4: backing up learnings/ + events/*/learning/result.{json,md}"
mkdir -p "${BACKUP_ROOT}"

if [[ -d "${EARNINGS_ROOT}/learnings" ]]; then
  cp -a "${EARNINGS_ROOT}/learnings/" "${BACKUP_ROOT}/" 2>/dev/null || true
  echo "    backed up: ${EARNINGS_ROOT}/learnings/ → ${BACKUP_ROOT}/learnings/"
else
  echo "    skip: ${EARNINGS_ROOT}/learnings/ does not exist (fresh tree)"
fi

if [[ -d "${EARNINGS_ROOT}/Companies" || -L "${EARNINGS_ROOT}/Companies" ]]; then
  # ``-H`` follows ONLY the Companies/ symlink at the start path
  # (narrower than ``-L``). See header note — without ``-H`` the script
  # silently misses every stale learning artifact.
  #
  # Backup gate counts ALL artifact types we delete in Step 3 (commit 4.4
  # refinement). If only result.md were present (e.g., a partial wipe
  # left an Obsidian sidecar behind), we'd still want to back it up
  # before Step 3 nukes it.
  result_count=$(find -H "${EARNINGS_ROOT}/Companies" \
                  -path "*/events/*/learning/result.json" 2>/dev/null | wc -l)
  result_md_count=$(find -H "${EARNINGS_ROOT}/Companies" \
                  -path "*/events/*/learning/result.md" 2>/dev/null | wc -l)
  thinking_count=$(find -H "${EARNINGS_ROOT}/Companies" \
                  -path "*/events/*/learning/thinking.md" 2>/dev/null | wc -l)
  subagents_count=$(find -H "${EARNINGS_ROOT}/Companies" \
                  -path "*/events/*/learning/subagents" -type d 2>/dev/null | wc -l)
  if [[ "${result_count}" -gt 0 || "${result_md_count}" -gt 0 \
        || "${thinking_count}" -gt 0 || "${subagents_count}" -gt 0 ]]; then
    find -H "${EARNINGS_ROOT}/Companies" \
         -path "*/events/*/learning/result.json" \
         -exec cp --parents {} "${BACKUP_ROOT}/" \; 2>/dev/null || true
    find -H "${EARNINGS_ROOT}/Companies" \
         -path "*/events/*/learning/result.md" \
         -exec cp --parents {} "${BACKUP_ROOT}/" \; 2>/dev/null || true
    find -H "${EARNINGS_ROOT}/Companies" \
         -path "*/events/*/learning/thinking.md" \
         -exec cp --parents {} "${BACKUP_ROOT}/" \; 2>/dev/null || true
    # Subagent transcripts: backed up as a flat archive of file paths
    # (cp --parents preserves the relative tree under BACKUP_ROOT).
    find -H "${EARNINGS_ROOT}/Companies" \
         -path "*/events/*/learning/subagents/*" \
         -type f \
         -exec cp --parents {} "${BACKUP_ROOT}/" \; 2>/dev/null || true
    echo "    backed up: ${result_count} result.json, ${result_md_count} result.md, ${thinking_count} thinking.md, ${subagents_count} subagents/ trees"
  else
    echo "    skip: no events/*/learning/ artifacts found (fresh tree)"
  fi
fi

# ── Step 2: Wipe library ─────────────────────────────────────────────────
echo ""
echo "==> Step 2/4: wiping learnings/ library"
rm -f "${EARNINGS_ROOT}/learnings/ticker/"*.json
rm -f "${EARNINGS_ROOT}/learnings/global.json"
rm -f "${EARNINGS_ROOT}/learnings/global.lock"
echo "    wiped: ticker/*.json, global.json, global.lock"

# ── Step 3: Wipe pre-v3 attribution artifacts ────────────────────────────
# Symlink-aware — see header note. Wipes the full learning artifact set:
# result.json (the schema gate), result.md (Obsidian sidecar), thinking.md
# (learner's chain-of-thought), and subagents/ (data-fetch transcripts).
echo ""
echo "==> Step 3/4: wiping pre-v3 events/*/learning/{result.{json,md}, thinking.md, subagents/}"
del_result_json=$(find -H "${EARNINGS_ROOT}/Companies" \
              -path "*/events/*/learning/result.json" -delete -print 2>/dev/null | wc -l)
del_result_md=$(find -H "${EARNINGS_ROOT}/Companies" \
              -path "*/events/*/learning/result.md" -delete -print 2>/dev/null | wc -l)
del_thinking=$(find -H "${EARNINGS_ROOT}/Companies" \
              -path "*/events/*/learning/thinking.md" -delete -print 2>/dev/null | wc -l)
# subagents/ directory wipe — recurse files first, then the directory.
del_subagents=$(find -H "${EARNINGS_ROOT}/Companies" \
              -path "*/events/*/learning/subagents/*" -delete -print 2>/dev/null | wc -l)
find -H "${EARNINGS_ROOT}/Companies" \
     -path "*/events/*/learning/subagents" -type d -empty -delete 2>/dev/null || true
echo "    deleted: ${del_result_json} result.json, ${del_result_md} result.md, ${del_thinking} thinking.md, ${del_subagents} subagent transcripts"

# ── Step 4: Initialize empty v3 library ──────────────────────────────────
echo ""
echo "==> Step 4/4: initializing empty v3 global.json"
mkdir -p "${EARNINGS_ROOT}/learnings/ticker"
echo '{"schema_version":"global_lessons.v2","updated_at":null,"entries":[]}' \
  > "${EARNINGS_ROOT}/learnings/global.json"
echo "    wrote: ${EARNINGS_ROOT}/learnings/global.json (empty v3 entries)"

echo ""
echo "==> v3 cutover complete at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""
echo "Next steps:"
echo "  1. Verify: cat ${EARNINGS_ROOT}/learnings/global.json"
echo "  2. Resume the production pipeline (e.g., scale extraction-worker back up)"
echo "  3. Run §13.5 G2 (PIT leak) + G3 (full-loop) + G10 (real SDK smoke) gates"
echo "  4. Once production is healthy, ${BACKUP_ROOT}/ is deletable"
