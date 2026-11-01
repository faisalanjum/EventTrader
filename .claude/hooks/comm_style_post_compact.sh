#!/bin/bash
# comm_style_post_compact.sh
# Re-states the User Communication Rules after a context compaction (and on session resume).
# Wired in .claude/settings.json to SessionStart(matcher: compact) only. The duplicate
# PostCompact registration was removed 2026-09-09: SessionStart(compact) was observed
# firing in a live session, PostCompact never was, and one reminder is enough.
# ADVISORY ONLY: always exit 0, never blocks the turn.
# NOTE: hooks do NOT live-reload — a NEW session is required after editing settings.json.
INPUT=$(cat 2>/dev/null) || INPUT=""
EVENT=$(printf '%s' "$INPUT" | jq -r '.hook_event_name // "SessionStart"' 2>/dev/null) || EVENT="SessionStart"
[ -z "$EVENT" ] && EVENT="SessionStart"
MSG="Reminder after compaction — follow the User Communication Rules at the TOP of CLAUDE.md before replying: crux first; plain common words (define any unavoidable term in ~5 words); a few sentences but keep ALL real information; small visuals (mini-tables, A -> B arrows, before/after) when faster than words; one idea per line; explain plainly before any writeup; and refresh my memory of earlier context before relying on it. Re-read that CLAUDE.md block now if unsure."
# Deliver via additionalContext JSON (documented injection path). If this build instead treats
# stdout as plain text, the readable MSG is still inside the object — so it reaches Claude either way.
printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$EVENT" "$MSG"
exit 0
