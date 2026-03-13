#!/usr/bin/env python3
"""SubagentStop hook: capture agent output + full transcript to Obsidian vault."""
import sys, json, re, os, glob as _glob
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

# Ticker detection (whitelist approach — only tag known tickers)
_wl_path = os.path.join(os.environ.get('HOME', ''), 'Obsidian/EventTrader/Earnings/earnings-analysis/.ticker-whitelist.txt')
_known = set()
if os.path.exists(_wl_path):
    with open(_wl_path) as _f:
        _known = set(line.strip() for line in _f if line.strip())
tickers = set(re.findall(r'\b([A-Z]{1,5})\b', msg)) & _known
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


# --- Helpers ---

def _clean_tool_result(text):
    """Strip MCP envelope, clean persisted-output refs, mark errors."""
    # Strip MCP envelope: {"result":[{"type":"text","text":"ACTUAL",...}]}
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and 'result' in parsed:
            inner = parsed['result']
            if isinstance(inner, list) and inner and isinstance(inner[0], dict):
                text = inner[0].get('text', text)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        pass
    # Handle <persisted-output> — replace with size note
    po = re.search(r'<persisted-output>\s*Output too large \(([^)]+)\)', text)
    if po:
        return f'[output too large \u2014 {po.group(1)}]'
    # Handle <tool_use_error> — mark with prefix
    if '<tool_use_error>' in text:
        err = re.search(r'<tool_use_error>(.*?)</tool_use_error>', text, re.DOTALL)
        return f'ERROR: {err.group(1).strip()}' if err else text
    return text


def _downgrade_headings(text):
    """Shift #/##/### headings down 3 levels so agent text doesn't break note outline."""
    return re.sub(r'^(#{1,3}) ', lambda m: '#' * (len(m.group(1)) + 3) + ' ', text, flags=re.MULTILINE)


# --- Extract all blocks from agent's own transcript ---
thinking_blocks = []
text_blocks = []
tool_blocks = []  # each entry: {text, ts, result}
total_thinking_chars = 0
_pending_calls = {}  # tool_use id -> index in tool_blocks

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
                                call_id = block.get('id', '')
                                inp = block.get('input', {})
                                if name == 'Bash':
                                    summary = f"{name}: {inp.get('command', '')[:500]}"
                                else:
                                    summary = f"{name}({json.dumps(inp)[:500]})"
                                tool_blocks.append({'text': summary, 'ts': ts, 'result': None})
                                if call_id:
                                    _pending_calls[call_id] = len(tool_blocks) - 1
                    elif etype == 'user':
                        content = entry.get('message', {}).get('content', [])
                        if not isinstance(content, list):
                            continue
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_result':
                                call_id = block.get('tool_use_id', '')
                                result_content = block.get('content', '')
                                if isinstance(result_content, list):
                                    result_content = ' '.join(
                                        c.get('text', '') for c in result_content if isinstance(c, dict)
                                    )
                                text = _clean_tool_result(str(result_content))[:2000]
                                # Pair with its tool_use call
                                if call_id and call_id in _pending_calls:
                                    tool_blocks[_pending_calls[call_id]]['result'] = text
                                elif text.strip():
                                    tool_blocks.append({'text': f'\u21b3 {text}', 'ts': ts, 'result': None})
                except:
                    continue
    except:
        pass

# Fiscal quarter extraction — scans output + full transcript (text blocks + tool results).
# Primary agents have "Q2 FY2026" in output. Enrichment agents have "fiscal_quarter": 2 in Neo4j results.
_all_text = msg
_all_text += ' '.join(b['text'] for b in text_blocks)
_all_text += ' '.join(b['text'] for b in tool_blocks)
_all_text += ' '.join(b.get('result', '') or '' for b in tool_blocks)
fiscal_quarter = None
_fq_match = re.search(r'Q([1-4])\s*FY(\d{4})', _all_text)
if _fq_match:
    fiscal_quarter = f'Q{_fq_match.group(1)}FY{_fq_match.group(2)}'
else:
    # Fallback: Neo4j results — handles JSON ("gu.fiscal_year": 2026),
    # escaped JSON (\"gu.fiscal_year\": 2026), and plain text (fiscal_year: 2026)
    _fy = re.search(r'\\?"?(?:gu\.)?fiscal_year\\?"?\s*:\s*(\d{4})', _all_text)
    _fqn = re.search(r'\\?"?(?:gu\.)?fiscal_quarter\\?"?\s*:\s*(\d)', _all_text)
    if _fy and _fqn:
        fiscal_quarter = f'Q{_fqn.group(1)}FY{_fy.group(1)}'

# --- Pre-compute extraction metadata ---
_extract_source_id = None
_extract_result_file = None
_extract_bn = None
_is_extraction = agent_type in ('extraction-primary-agent', 'extraction-enrichment-agent')
_is_primary = agent_type == 'extraction-primary-agent'
_is_enrichment = agent_type == 'extraction-enrichment-agent'

if _is_extraction:
    _pass_type = 'primary' if _is_primary else 'enrichment'
    _all_candidates = _glob.glob(f'/tmp/extract_pass_*_{_pass_type}_*.json')

    # Prefer the candidate whose source_id appears in the agent's output
    for _c in _all_candidates:
        _bn = os.path.basename(_c)
        _parts = _bn.split(f'_{_pass_type}_', 1)
        _sid = _parts[1].rsplit('.json', 1)[0] if len(_parts) == 2 else None
        if _sid and _sid in msg:
            _extract_source_id = _sid
            _extract_result_file = _c
            _extract_bn = _bn
            break

    # Fallback: most recently modified
    if not _extract_source_id and _all_candidates:
        _c = max(_all_candidates, key=os.path.getmtime)
        _bn = os.path.basename(_c)
        _parts = _bn.split(f'_{_pass_type}_', 1)
        _extract_source_id = _parts[1].rsplit('.json', 1)[0] if len(_parts) == 2 else None
        _extract_result_file = _c
        _extract_bn = _bn

# Heading levels: extraction agents nest under ## Primary/Enrichment Pass
# Non-extraction agents use ## for content sections (unchanged from original)
_h2 = '###' if _is_extraction else '##'
_h3 = '####' if _is_extraction else '###'

# --- Build note ---
timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
date = datetime.now().strftime('%Y-%m-%d')
tickers_str = ', '.join(sorted(tickers)[:5])
tags_yaml = '[' + ', '.join(tags) + ']'

lines = []

# Frontmatter — primary extraction or non-extraction only (enrichment appends to existing file)
if not _is_enrichment:
    lines.append('---')
    lines.append(f'agent_type: {agent_type}')
    lines.append(f'agent_id: {agent_id}')
    lines.append(f'timestamp: {timestamp}')
    if tickers_str:
        lines.append(f'tickers: [{tickers_str}]')
    if fiscal_quarter:
        lines.append(f'fiscal_quarter: {fiscal_quarter}')
    if _extract_source_id:
        lines.append(f'source_id: "{_extract_source_id}"')
    lines.append(f'thinking_blocks: {len(thinking_blocks)}')
    lines.append(f'thinking_chars: {total_thinking_chars}')
    lines.append(f'text_blocks: {len(text_blocks)}')
    lines.append(f'tool_blocks: {len(tool_blocks)}')
    lines.append(f'tags: {tags_yaml}')
    lines.append('---')
    lines.append('')
    if _is_primary:
        lines.append(f'# Extraction \u2014 {_extract_source_id or agent_id}')
    else:
        lines.append(f'# {agent_type} \u2014 {timestamp}')
    lines.append('')

# Section header for extraction agents
if _is_extraction:
    _pass_label = 'Primary Pass' if _is_primary else 'Enrichment Pass'
    lines.append(f'## {_pass_label}')
    lines.append('')

# Info table — full table for non-extraction, compact line for extraction
if not _is_extraction:
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
else:
    lines.append(f'Agent: `{agent_type}` | ID: `{agent_id}` | Time: {timestamp}')
    lines.append('')

# Output — downgrade headings so agent text doesn't break note outline
lines.append(f'{_h2} Output')
lines.append('')
lines.append(_downgrade_headings(msg))

# Transcript trace
if text_blocks or tool_blocks or thinking_blocks:
    lines.append('')
    lines.append(f'{_h2} Transcript')
    lines.append('')

    # Skip the last text block if it duplicates the Output section
    _skip_last_text = False
    if text_blocks:
        _last = text_blocks[-1]['text'][:200].strip()
        _skip_last_text = bool(_last and _last in msg)

    # Merge all blocks, sort by timestamp
    all_blocks = []
    for b in thinking_blocks:
        all_blocks.append(('thinking', b['text'], b['ts'], None))
    for i, b in enumerate(text_blocks):
        if _skip_last_text and i == len(text_blocks) - 1:
            continue  # skip duplicate of Output section
        all_blocks.append(('text', b['text'], b['ts'], None))
    for b in tool_blocks:
        all_blocks.append(('tool', b['text'], b['ts'], b.get('result')))
    all_blocks.sort(key=lambda x: x[2])

    emoji = {'thinking': '\U0001f4ad', 'text': '\U0001f4dd', 'tool': '\U0001f527'}
    written = 0
    for i, (btype, text, ts, result) in enumerate(all_blocks, 1):
        if written > 40000:
            lines.append(f'*... {len(all_blocks) - i + 1} more blocks truncated*')
            break
        short_ts = ts[11:19] if len(ts) > 19 else ''
        lines.append(f'{_h3} {emoji.get(btype, "?")} #{i} {short_ts}')
        if btype == 'tool':
            lines.append('```')
            lines.append(text)
            if result:
                lines.append('')
                lines.append(f'\u2192 {result}')
            lines.append('```')
        elif btype == 'thinking':
            display = text[:5000]
            if len(text) > 5000:
                display += f'\n\n*[truncated, {len(text) - 5000:,} more chars]*'
            lines.append(f'*{len(text)} chars*')
            lines.append('')
            lines.append(display)
        else:
            lines.append(_downgrade_headings(text[:2000]))
        lines.append('')
        written += len(text)

# Extraction artifact capture
if _extract_source_id and _is_extraction and _extract_result_file:
    try:
        with open(_extract_result_file) as _rf:
            _result_json = _rf.read().strip()

        lines.append('')
        lines.append(f'{_h2} Artifacts')
        lines.append('')
        lines.append(f'**Pass**: `{_pass_type}` | **Source ID**: `{_extract_source_id}`')
        lines.append(f'**Result file**: `{_extract_bn}`')
        lines.append('')
        lines.append('```json')
        lines.append(_result_json)
        lines.append('```')

        # Warmup cache references (too large to embed — just list path + size)
        _ticker = sorted(tickers)[0] if tickers else None
        _cache_refs = []
        if _ticker:
            for _cf, _lbl in [
                (f'/tmp/concept_cache_{_ticker}.json', 'Concept cache'),
                (f'/tmp/member_cache_{_ticker}.json', 'Member cache'),
            ]:
                if os.path.exists(_cf):
                    _cache_refs.append((_lbl, os.path.basename(_cf), os.path.getsize(_cf)))
            # Filter transcript cache by source_id, not all ticker caches
            _tc_file = f'/tmp/transcript_content_{_extract_source_id}.json'
            if os.path.exists(_tc_file):
                _cache_refs.append(('Transcript content', os.path.basename(_tc_file), os.path.getsize(_tc_file)))

        if _cache_refs:
            lines.append('')
            lines.append(f'{_h3} Warmup Caches (on disk)')
            lines.append('')
            lines.append('| Cache | File | Size |')
            lines.append('|-------|------|------|')
            for _lbl, _fname, _sz in _cache_refs:
                lines.append(f'| {_lbl} | `{_fname}` | {_sz // 1024} KB |')
    except Exception:
        pass

# Post-write summary table (from CLI sidecar — shows actual canonical values, not agent interpretation)
if _is_extraction and _extract_source_id:
    _written_path = f'/tmp/gu_written_{_extract_source_id}.json'
    if os.path.exists(_written_path):
        try:
            with open(_written_path) as _wf:
                _written = json.load(_wf)
            if _written:
                lines.append('')
                lines.append(f'{_h2} Written Items (Post-Canonical)')
                lines.append('')
                lines.append('| Label | Segment | Unit | Low | Mid | High | Status |')
                lines.append('|-------|---------|------|-----|-----|------|--------|')
                for _w in _written:
                    _st = 'created' if _w.get('was_created') is True else (
                        'error' if _w.get('error') else (
                        'dry_run' if _w.get('was_created') is None else 'updated'))
                    _lo = _w.get('low') if _w.get('low') is not None else ''
                    _mi = _w.get('mid') if _w.get('mid') is not None else ''
                    _hi = _w.get('high') if _w.get('high') is not None else ''
                    lines.append(f"| {_w.get('label', '')} | {_w.get('segment', '')} | {_w.get('canonical_unit', '')} | {_lo} | {_mi} | {_hi} | {_st} |")
        except Exception:
            pass

# --- Write to vault ---
vault = os.environ.get('HOME', '') + '/Obsidian/EventTrader/Earnings/earnings-analysis'

# Folder routing by agent type
# Pipeline agents -> pipeline/{stage}, everything else -> agents/
FOLDER_ROUTING = {
    'extraction-primary-agent': 'pipeline/extractions',
    'extraction-enrichment-agent': 'pipeline/extractions',
    'earnings-prediction': 'pipeline/predictions',
    'earnings-attribution': 'pipeline/learner',
    'earnings-learner': 'pipeline/learner',
    'news-driver-web': 'pipeline/news-impact',
    'news-driver-bz': 'pipeline/news-impact',
    'news-driver-judge': 'pipeline/news-impact',
    'news-driver-ppx': 'pipeline/news-impact',
    'news-driver-final-judge': 'pipeline/news-impact',
}
subfolder = FOLDER_ROUTING.get(agent_type, 'agents')
log_dir = vault + '/' + subfolder
os.makedirs(log_dir, exist_ok=True)

# Extraction agents: one file per source_id, enrichment appends
# Non-extraction agents: one file per agent_id (unchanged)
if _is_extraction and _extract_source_id:
    filename = f'{date}_extraction_{_extract_source_id}.md'
    filepath = f'{log_dir}/{filename}'
    mode = 'w' if _is_primary else 'a'
else:
    filename = f'{date}_{agent_type}_{agent_id}.md'
    filepath = f'{log_dir}/{filename}'
    mode = 'w'

# Write (enrichment appends with blank line separator)
with open(filepath, mode) as f:
    content = '\n'.join(lines) + '\n'
    if _is_enrichment and mode == 'a':
        content = '\n' + content
    f.write(content)

with open(f'{log_dir}/.capture.log', 'a') as f:
    f.write(f'[obsidian_capture] {filename} | {len(thinking_blocks)} thinking, {len(text_blocks)} text, {len(tool_blocks)} tools | tags: {tags_yaml}\n')
