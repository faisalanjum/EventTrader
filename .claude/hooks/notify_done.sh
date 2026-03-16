#!/usr/bin/env bash
# Plays a subtle chime when a task finishes.
# Used by Stop hook — fires when Claude finishes a response.
paplay /home/faisal/EventMarketDB/.claude/hooks/done.wav &>/dev/null &
