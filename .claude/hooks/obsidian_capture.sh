#!/usr/bin/env bash
# SubagentStop hook: auto-capture agent output + full transcript to Obsidian vault
#
# SubagentStop fields:
#   session_id, transcript_path (parent), agent_transcript_path (agent's own),
#   agent_id, agent_type, last_assistant_message, hook_event_name,
#   stop_hook_active, cwd, permission_mode

cat | python3 "$(dirname "$0")/obsidian_capture.py" 2>/dev/null
