#!/usr/bin/env python3
"""SubagentStop hook: capture agent output + full transcript to Obsidian vault."""
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

# --- Extract all blocks from agent's own transcript ---
thinking_blocks = []
text_blocks = []
tool_blocks = []
total_thinking_chars = 0

if agent_transcript and os.path.exists(agent_transcript):
    try:
        with open(agent_transcript) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    etype = entry.get('type')
                    ts = entry.get('timestamp', '')
                    if etype == 'assistant':
                        content = entry.get('message', {}).get('content', [])
                        if not isinstance(content, list):
                            continue
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            btype = block.get('type')
                            if btype == 'thinking':
                                text = block.get('thinking', '')
                                total_thinking_chars += len(text)
                                thinking_blocks.append({'text': text, 'ts': ts})
                            elif btype == 'text':
                                text = block.get('text', '').strip()
                                if text:
                                    text_blocks.append({'text': text, 'ts': ts})
                            elif btype == 'tool_use':
                                name = block.get('name', 'unknown')
                                inp = block.get('input', {})
                                if name == 'Bash':
                                    summary = f"{name}: {inp.get('command', '')[:200]}"
                                else:
                                    summary = f"{name}({json.dumps(inp)[:200]})"
                                tool_blocks.append({'text': summary, 'ts': ts})
                    elif etype == 'user':
                        content = entry.get('message', {}).get('content', [])
                        if not isinstance(content, list):
                            continue
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_result':
                                result_content = block.get('content', '')
                                if isinstance(result_content, list):
                                    result_content = ' '.join(
                                        c.get('text', '') for c in result_content if isinstance(c, dict)
                                    )
                                text = str(result_content)[:500]
                                if text.strip():
                                    tool_blocks.append({'text': f'\u21b3 {text}', 'ts': ts})
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
lines.append(f'text_blocks: {len(text_blocks)}')
lines.append(f'tool_blocks: {len(tool_blocks)}')
lines.append(f'tags: {tags_yaml}')
lines.append('---')
lines.append('')
lines.append(f'# {agent_type} \u2014 {timestamp}')
lines.append('')
lines.append('| Field | Value |')
lines.append('|-------|-------|')
lines.append(f'| Agent | `{agent_type}` |')
lines.append(f'| ID | `{agent_id}` |')
lines.append(f'| Time | {timestamp} |')
if thinking_blocks:
    lines.append(f'| Thinking | {len(thinking_blocks)} blocks, {total_thinking_chars:,} chars |')
lines.append(f'| Text | {len(text_blocks)} blocks |')
lines.append(f'| Tools | {len(tool_blocks)} calls |')
lines.append('')
lines.append('## Output')
lines.append('')
lines.append(msg)

# Add full transcript trace
if text_blocks or tool_blocks or thinking_blocks:
    lines.append('')
    lines.append('## Transcript')
    lines.append('')

    # Merge all blocks, sort by timestamp
    all_blocks = []
    for b in thinking_blocks:
        all_blocks.append(('thinking', b['text'], b['ts']))
    for b in text_blocks:
        all_blocks.append(('text', b['text'], b['ts']))
    for b in tool_blocks:
        all_blocks.append(('tool', b['text'], b['ts']))
    all_blocks.sort(key=lambda x: x[2])

    emoji = {'thinking': '\U0001f4ad', 'text': '\U0001f4dd', 'tool': '\U0001f527'}
    written = 0
    for i, (btype, text, ts) in enumerate(all_blocks, 1):
        if written > 40000:
            lines.append(f'*... {len(all_blocks) - i + 1} more blocks truncated*')
            break
        short_ts = ts[11:19] if len(ts) > 19 else ''
        lines.append(f'### {emoji.get(btype, "?")} #{i} {short_ts}')
        if btype == 'tool':
            lines.append('```')
            lines.append(text)
            lines.append('```')
        elif btype == 'thinking':
            display = text[:5000]
            if len(text) > 5000:
                display += f'\n\n*[truncated, {len(text) - 5000:,} more chars]*'
            lines.append(f'*{len(text)} chars*')
            lines.append('')
            lines.append(display)
        else:
            lines.append(text[:2000])
        lines.append('')
        written += len(text)

vault = os.environ.get('HOME', '') + '/Obsidian/EventTrader/Earnings/earnings-analysis'
log_dir = vault + '/claude-logs'
os.makedirs(log_dir, exist_ok=True)
filepath = f'{log_dir}/{filename}'

with open(filepath, 'w') as f:
    f.write('\n'.join(lines) + '\n')

with open(f'{log_dir}/.capture.log', 'a') as f:
    f.write(f'[obsidian_capture] {filename} | {len(thinking_blocks)} thinking, {len(text_blocks)} text, {len(tool_blocks)} tools | tags: {tags_yaml}\n')
