#!/usr/bin/env bash
# SubagentStop hook: auto-capture agent output to Obsidian vault
# Fires every time a sub-agent completes.
#
# SubagentStop fields:
#   session_id, transcript_path (parent), agent_transcript_path (agent's own),
#   agent_id, agent_type, last_assistant_message, hook_event_name,
#   stop_hook_active, cwd, permission_mode
#
# Note: Thinking blocks are NOT in agent transcripts (stripped).
#       Only output + metadata captured here.

VAULT_DIR="$HOME/Obsidian/EventTrader/Earnings/earnings-analysis"
LOG_DIR="$VAULT_DIR/claude-logs"
mkdir -p "$LOG_DIR"

INPUT=$(cat)

# Single python call: extract fields + infer dynamic tags from content
eval "$(echo "$INPUT" | python3 -c "
import sys, json, shlex, re

d = json.load(sys.stdin)
agent_type = d.get('agent_type', 'unknown')
agent_id = d.get('agent_id', '')[:8]
msg = d.get('last_assistant_message', '')

# --- Dynamic tag inference ---
tags = ['claude-log']

# Agent type tag
if agent_type and agent_type != 'unknown':
    tags.append(agent_type.replace(' ', '-'))

# Skill-based tags (extract from agent_type like 'earnings-prediction')
for skill in ['prediction', 'attribution', 'orchestrator', 'extraction', 'guidance', 'news-driver']:
    if skill in agent_type:
        tags.append(skill)

# Ticker detection (uppercase 1-5 letter words that look like tickers)
tickers = set(re.findall(r'\b([A-Z]{1,5})\b', msg))
# Filter to known/likely tickers (exclude common words)
noise = {'THE','AND','FOR','NOT','BUT','ALL','ARE','WAS','HAS','HAD','ITS','CEO',
         'CFO','COO','CTO','SEC','ETF','IPO','GDP','EPS','USA','USD','API','SQL',
         'MCP','CLI','RAM','CPU','LLM','PDF','CSV','JSON','YAML','HTML','HTTP',
         'YES','THIS','THAT','WITH','FROM','THEY','WILL','BEEN','HAVE','DOES',
         'WHAT','WHEN','WHERE','WHICH','ABOUT','AFTER','BEFORE','BETWEEN','INTO'}
tickers -= noise
for t in sorted(tickers)[:5]:  # max 5 ticker tags
    tags.append(t)

# Context tags from content
if any(w in msg.lower() for w in ['earnings', '8-k', '10-q', '10-k', 'filing']):
    tags.append('earnings')
if any(w in msg.lower() for w in ['guidance', 'forward-looking', 'outlook']):
    tags.append('guidance')
if any(w in msg.lower() for w in ['revenue', 'eps', 'margin', 'profit']):
    tags.append('financials')
if any(w in msg.lower() for w in ['driver', 'attribution', 'moved because']):
    tags.append('attribution')
if any(w in msg.lower() for w in ['predict', 'forecast', 'expect']):
    tags.append('prediction')
if any(w in msg.lower() for w in ['neo4j', 'cypher', 'query']):
    tags.append('neo4j')
if any(w in msg.lower() for w in ['benzinga', 'perplexity', 'news']):
    tags.append('news')

# Deduplicate
tags = list(dict.fromkeys(tags))
tags_yaml = '[' + ', '.join(tags) + ']'

print(f'AGENT_TYPE={shlex.quote(agent_type)}')
print(f'AGENT_ID={shlex.quote(agent_id)}')
print(f'LAST_MSG={shlex.quote(msg[:3000])}')
print(f'TAGS_YAML={shlex.quote(tags_yaml)}')
print(f'TICKERS={shlex.quote(\", \".join(sorted(tickers)[:5]))}')
" 2>/dev/null)"

# Skip noise agents
case "$AGENT_TYPE" in
    prompt_suggestion*|compact*|warmup*|""|unknown) exit 0 ;;
esac

TIMESTAMP=$(date +%Y-%m-%dT%H:%M:%S)
DATE=$(date +%Y-%m-%d)
FILENAME="${DATE}_${AGENT_TYPE}_${AGENT_ID}.md"

cat > "$LOG_DIR/$FILENAME" << MARKDOWN
---
agent_type: ${AGENT_TYPE}
agent_id: ${AGENT_ID}
timestamp: ${TIMESTAMP}
tickers: [${TICKERS}]
tags: ${TAGS_YAML}
---

# ${AGENT_TYPE} — ${TIMESTAMP}

| Field | Value |
|-------|-------|
| Agent | \`${AGENT_TYPE}\` |
| ID | \`${AGENT_ID}\` |
| Time | ${TIMESTAMP} |

## Output

${LAST_MSG}
MARKDOWN

echo "[obsidian_capture] Wrote $LOG_DIR/$FILENAME (tags: $TAGS_YAML)" >> "$LOG_DIR/.capture.log"
