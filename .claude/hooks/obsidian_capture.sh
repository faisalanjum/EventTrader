#!/usr/bin/env bash
# SubagentStop hook: auto-capture agent output + thinking to Obsidian vault
#
# SubagentStop fields:
#   session_id, transcript_path (parent), agent_transcript_path (agent's own),
#   agent_id, agent_type, last_assistant_message, hook_event_name,
#   stop_hook_active, cwd, permission_mode

VAULT_DIR="$HOME/Obsidian/EventTrader/Earnings/earnings-analysis"
LOG_DIR="$VAULT_DIR/claude-logs"
mkdir -p "$LOG_DIR"

INPUT=$(cat)

# Single python call: extract fields, infer tags, extract thinking, write note
echo "$INPUT" | python3 -c "
import sys, json, re, os
from datetime import datetime

d = json.load(sys.stdin)
agent_type = d.get('agent_type', 'unknown')
agent_id = d.get('agent_id', '')[:8]
agent_transcript = d.get('agent_transcript_path', '')
msg = d.get('last_assistant_message', '')[:3000]

# Skip noise
if agent_type in ('', 'unknown') or any(x in agent_type for x in ('prompt_suggestion', 'compact', 'warmup')):
    sys.exit(0)

# --- Dynamic tag inference ---
tags = ['claude-log']
if agent_type:
    tags.append(agent_type.replace(' ', '-'))
for skill in ['prediction', 'attribution', 'orchestrator', 'extraction', 'guidance', 'news-driver']:
    if skill in agent_type:
        tags.append(skill)

# Ticker detection
tickers = set(re.findall(r'\b([A-Z]{1,5})\b', msg))
noise = {'THE','AND','FOR','NOT','BUT','ALL','ARE','WAS','HAS','HAD','ITS','CEO',
         'CFO','COO','CTO','SEC','ETF','IPO','GDP','EPS','USA','USD','API','SQL',
         'MCP','CLI','RAM','CPU','LLM','PDF','CSV','JSON','YAML','HTML','HTTP',
         'YES','THIS','THAT','WITH','FROM','THEY','WILL','BEEN','HAVE','DOES',
         'WHAT','WHEN','WHERE','WHICH','ABOUT','AFTER','BEFORE','BETWEEN','INTO'}
tickers -= noise
for t in sorted(tickers)[:5]:
    tags.append(t)

# Context tags
if any(w in msg.lower() for w in ['earnings', '8-k', '10-q', '10-k', 'filing']):
    tags.append('earnings')
if any(w in msg.lower() for w in ['guidance', 'outlook']):
    tags.append('guidance')
if any(w in msg.lower() for w in ['revenue', 'eps', 'margin']):
    tags.append('financials')
if any(w in msg.lower() for w in ['predict', 'forecast']):
    tags.append('prediction')

tags = list(dict.fromkeys(tags))

# --- Extract thinking from agent's own transcript ---
thinking_blocks = []
total_thinking_chars = 0

if agent_transcript and os.path.exists(agent_transcript):
    try:
        with open(agent_transcript) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get('type') != 'assistant':
                        continue
                    content = entry.get('message', {}).get('content', [])
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'thinking':
                            text = block.get('thinking', '')
                            total_thinking_chars += len(text)
                            thinking_blocks.append(text)
                except:
                    continue
    except:
        pass

# --- Build note ---
timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
date = datetime.now().strftime('%Y-%m-%d')
filename = f'{date}_{agent_type}_{agent_id}.md'
tickers_str = ', '.join(sorted(tickers)[:5])
tags_yaml = '[' + ', '.join(tags) + ']'

lines = []
lines.append('---')
lines.append(f'agent_type: {agent_type}')
lines.append(f'agent_id: {agent_id}')
lines.append(f'timestamp: {timestamp}')
if tickers_str:
    lines.append(f'tickers: [{tickers_str}]')
lines.append(f'thinking_blocks: {len(thinking_blocks)}')
lines.append(f'thinking_chars: {total_thinking_chars}')
lines.append(f'tags: {tags_yaml}')
lines.append('---')
lines.append('')
lines.append(f'# {agent_type} — {timestamp}')
lines.append('')
lines.append('| Field | Value |')
lines.append('|-------|-------|')
lines.append(f'| Agent | \`{agent_type}\` |')
lines.append(f'| ID | \`{agent_id}\` |')
lines.append(f'| Time | {timestamp} |')
if thinking_blocks:
    lines.append(f'| Thinking | {len(thinking_blocks)} blocks, {total_thinking_chars:,} chars |')
lines.append('')
lines.append('## Output')
lines.append('')
lines.append(msg)

# Add thinking section
if thinking_blocks:
    lines.append('')
    lines.append('## Thinking')
    lines.append('')
    written = 0
    for i, text in enumerate(thinking_blocks, 1):
        if written > 30000:
            remaining = len(thinking_blocks) - i + 1
            lines.append(f'*... {remaining} more blocks truncated ({total_thinking_chars - written:,} chars remaining)*')
            break
        display = text
        if len(text) > 5000:
            display = text[:5000] + f'\n\n*[truncated, {len(text) - 5000:,} more chars]*'
        lines.append(f'### Block {i}')
        lines.append('')
        lines.append(display)
        lines.append('')
        written += len(text)

vault = os.environ.get('HOME', '') + '/Obsidian/EventTrader/Earnings/earnings-analysis'
log_dir = vault + '/claude-logs'
os.makedirs(log_dir, exist_ok=True)
filepath = f'{log_dir}/{filename}'

with open(filepath, 'w') as f:
    f.write('\n'.join(lines) + '\n')

with open(f'{log_dir}/.capture.log', 'a') as f:
    f.write(f'[obsidian_capture] {filename} | {len(thinking_blocks)} thinking blocks, {total_thinking_chars} chars | tags: {tags_yaml}\n')
" 2>/dev/null
