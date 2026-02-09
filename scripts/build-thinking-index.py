#!/usr/bin/env python3
"""
Build Obsidian-compatible thinking index from Claude Code transcripts.

Pure filesystem discovery - NO CSV dependencies.
Captures ALL thinking from primary sessions and ALL subagents.

Output: ~/Obsidian/EventTrader/Earnings/earnings-analysis/thinking/
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Paths
CLAUDE_DIR = Path.home() / ".claude" / "projects" / "-home-faisal-EventMarketDB"
OUTPUT_DIR = Path.home() / "Obsidian" / "EventTrader" / "Earnings" / "earnings-analysis" / "thinking"
RUNS_DIR = OUTPUT_DIR / "runs"
COMPANIES_DIR = Path("/home/faisal/EventMarketDB/earnings-analysis/Companies")


# =============================================================================
# CORE DISCOVERY FUNCTIONS (Pure Filesystem)
# =============================================================================

def find_all_earnings_sessions() -> dict[str, dict]:
    """Scan all transcripts to find earnings skill invocations.

    Returns {accession_no: {session_path, skill_type, invocation_time}}
    """
    results = {}

    for t in CLAUDE_DIR.glob("*.jsonl"):
        try:
            with open(t) as f:
                for line in f:
                    # Quick filter
                    if '/earnings-' not in line and 'command-args' not in line:
                        continue

                    data = json.loads(line)
                    if data.get('type') != 'user':
                        continue

                    content = data.get('message', {}).get('content', '')
                    if not isinstance(content, str):
                        continue

                    timestamp = data.get('timestamp', '')

                    # Pattern 1: <command-args>accession</command-args>
                    match = re.search(r'<command-args>(\d{10}-\d{2}-\d{6})</command-args>', content)
                    if match:
                        acc = match.group(1)
                        skill = 'prediction' if 'prediction' in content else 'attribution' if 'attribution' in content else 'unknown'
                        if acc not in results or timestamp > results[acc].get('timestamp', ''):
                            results[acc] = {'session_path': t, 'skill': skill, 'timestamp': timestamp}
                        continue

                    # Pattern 2: Run /earnings-{skill} accession
                    match = re.match(r'^Run /earnings-(\w+)\s+(\d{10}-\d{2}-\d{6})', content)
                    if match:
                        skill, acc = match.groups()
                        if acc not in results or timestamp > results[acc].get('timestamp', ''):
                            results[acc] = {'session_path': t, 'skill': skill, 'timestamp': timestamp}
                        continue

                    # Pattern 3: /earnings-{skill} accession
                    match = re.match(r'^/earnings-(\w+)\s+(\d{10}-\d{2}-\d{6})', content)
                    if match:
                        skill, acc = match.groups()
                        if acc not in results or timestamp > results[acc].get('timestamp', ''):
                            results[acc] = {'session_path': t, 'skill': skill, 'timestamp': timestamp}
        except:
            continue

    return results


def find_session_for_accession(accession_no: str) -> Optional[Path]:
    """Find the primary transcript for an accession via content search."""
    if not accession_no:
        return None

    matches = []

    for t in CLAUDE_DIR.glob("*.jsonl"):
        try:
            with open(t) as f:
                for line in f:
                    if accession_no not in line:
                        continue

                    data = json.loads(line)
                    if data.get('type') != 'user':
                        continue

                    content = data.get('message', {}).get('content', '')
                    if not isinstance(content, str):
                        continue

                    # Pattern 1: <command-args>accession</command-args>
                    if f'<command-args>{accession_no}</command-args>' in content:
                        matches.append(t)
                        break

                    # Pattern 2: Run /earnings-{skill} accession
                    if re.match(rf'^Run /earnings-\w+ {re.escape(accession_no)}(\s|$)', content):
                        matches.append(t)
                        break

                    # Pattern 3: /earnings-{skill} accession
                    if re.match(rf'^/earnings-\w+ {re.escape(accession_no)}(\s|$)', content):
                        matches.append(t)
                        break
        except:
            continue

    if not matches:
        return None

    # Prefer sessions with subagents directory
    for m in matches:
        subagents_dir = CLAUDE_DIR / m.stem / "subagents"
        if subagents_dir.exists() and any(subagents_dir.glob("agent-*.jsonl")):
            return m

    return max(matches, key=lambda p: p.stat().st_mtime)


def get_task_agent_types(transcript_path: Path) -> dict[str, str]:
    """Extract agent_id -> subagent_type mapping from Task calls."""
    task_map = {}
    result_map = {}

    if not transcript_path.exists():
        return {}

    with open(transcript_path) as f:
        for line in f:
            try:
                d = json.loads(line)

                if d.get('type') == 'assistant':
                    content = d.get('message', {}).get('content', [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_use':
                                if block.get('name') == 'Task':
                                    inp = block.get('input', {})
                                    subagent_type = inp.get('subagent_type', '')
                                    tool_id = block.get('id', '')
                                    if tool_id and subagent_type:
                                        task_map[tool_id] = subagent_type

                if d.get('type') == 'user':
                    content = d.get('message', {}).get('content', [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_result':
                                tool_id = block.get('tool_use_id', '')
                                result_content = block.get('content', [])
                                if isinstance(result_content, list):
                                    for rc in result_content:
                                        if isinstance(rc, dict) and rc.get('type') == 'text':
                                            text = rc.get('text', '')
                                            if 'agentId:' in text:
                                                match = re.search(r'agentId:\s*([a-f0-9]+)', text)
                                                if match:
                                                    result_map[match.group(1)] = tool_id
            except:
                continue

    return {aid: task_map.get(tid, '') for aid, tid in result_map.items()}


def categorize_agent(agent_id: str, prompt: str, transcript_types: dict[str, str]) -> str:
    """Categorize an agent by type."""
    prompt_str = prompt if isinstance(prompt, str) else str(prompt)

    if 'prompt_suggestion' in agent_id:
        return 'prompt_suggestion'
    if 'compact' in agent_id:
        return 'compact'
    if prompt_str.strip() == 'Warmup' or prompt_str.startswith('Warmup'):
        return 'warmup'
    if agent_id in transcript_types and transcript_types[agent_id]:
        return f"task:{transcript_types[agent_id]}"
    if '.claude/skills/' in prompt_str:
        match = re.search(r'\.claude/skills/([\w-]+)', prompt_str)
        if match:
            return f"skill:{match.group(1)}"

    return 'unknown'


def discover_all_agents(session_id: str) -> list[dict]:
    """Discover ALL agents for a session."""
    if not session_id:
        return []

    primary_path = CLAUDE_DIR / f"{session_id}.jsonl"
    transcript_types = get_task_agent_types(primary_path)

    subagents_dir = CLAUDE_DIR / session_id / "subagents"
    if not subagents_dir.exists():
        return []

    agents = []

    for agent_file in sorted(subagents_dir.glob("agent-*.jsonl")):
        agent_id = agent_file.stem.replace("agent-", "")

        try:
            with open(agent_file) as f:
                first_line = json.loads(f.readline())
                prompt = first_line.get('message', {}).get('content', '')
        except:
            prompt = ''

        agent_type = categorize_agent(agent_id, prompt, transcript_types)

        agents.append({
            'agent_id': agent_id,
            'agent_type': agent_type,
            'path': agent_file
        })

    return agents


# =============================================================================
# THINKING EXTRACTION
# =============================================================================

def extract_thinking_blocks(filepath: Path, source: str = 'primary') -> list[dict]:
    """Extract all thinking blocks from a transcript file."""
    blocks = []

    if not filepath.exists():
        return blocks

    try:
        with open(filepath) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get('type') != 'assistant':
                        continue

                    timestamp = d.get('timestamp', '')
                    content = d.get('message', {}).get('content', [])

                    if not isinstance(content, list):
                        continue

                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'thinking':
                            text = block.get('thinking', '')
                            blocks.append({
                                'timestamp': timestamp,
                                'type': 'thinking',
                                'text': text,
                                'length': len(text),
                                'source': source
                            })
                except:
                    continue
    except Exception as e:
        print(f"  Warning reading {filepath}: {e}")

    return blocks


def collect_all_thinking(session_path: Path, agents: list[dict]) -> tuple[list[dict], str]:
    """Collect ALL thinking from primary + all agents."""
    all_blocks = []
    session_start = None

    blocks = extract_thinking_blocks(session_path, source='primary')
    all_blocks.extend(blocks)
    for b in blocks:
        ts = b.get('timestamp', '')
        if ts and (session_start is None or ts < session_start):
            session_start = ts

    for agent in agents:
        source = agent['agent_type']
        blocks = extract_thinking_blocks(agent['path'], source=source)
        all_blocks.extend(blocks)
        for b in blocks:
            ts = b.get('timestamp', '')
            if ts and (session_start is None or ts < session_start):
                session_start = ts

    all_blocks.sort(key=lambda x: x.get('timestamp', ''))

    return all_blocks, session_start or ''


# =============================================================================
# METADATA EXTRACTION (Pure Filesystem)
# =============================================================================

def extract_metadata_from_session(session_path: Path, accession_no: str) -> dict:
    """Extract ticker and filing date from session transcript."""
    metadata = {}

    if not session_path or not session_path.exists():
        return metadata

    try:
        with open(session_path) as f:
            content = f.read()

            # Look for ticker in tool results (common patterns)
            # Pattern: "ticker": "XYZ" or ticker: XYZ
            match = re.search(rf'{accession_no}.*?"ticker":\s*"([A-Z]+)"', content[:50000])
            if match:
                metadata['ticker'] = match.group(1)
            else:
                match = re.search(r'"ticker":\s*"([A-Z]+)"', content[:50000])
                if match:
                    metadata['ticker'] = match.group(1)

            # Look for filing datetime
            match = re.search(r'"filing_datetime":\s*"([^"]+)"', content[:50000])
            if match:
                metadata['filing_datetime'] = match.group(1)
            else:
                match = re.search(r'"created":\s*"(\d{4}-\d{2}-\d{2})', content[:50000])
                if match:
                    metadata['filing_datetime'] = match.group(1)
    except:
        pass

    return metadata


def get_attribution_metadata(accession_no: str, ticker: str) -> dict:
    """Get metadata from attribution report if exists."""
    if not ticker:
        return {}

    report_path = COMPANIES_DIR / ticker / f"{accession_no}.md"
    if not report_path.exists():
        return {}

    metadata = {}
    try:
        with open(report_path) as f:
            content = f.read()
            for line in content.split('\n'):
                if 'Primary Driver' in line and ':' in line:
                    metadata['primary_driver'] = line.split(':', 1)[1].strip()
                elif 'Confidence' in line and ':' in line:
                    metadata['confidence'] = line.split(':', 1)[1].strip()
                elif 'daily_stock' in line.lower() and '%' in line:
                    match = re.search(r'([+-]?\d+\.?\d*)%', line)
                    if match:
                        metadata['return_pct'] = match.group(1) + '%'
    except:
        pass
    return metadata


def get_session_duration(session_path: Path) -> str:
    """Calculate session duration from first to last timestamp."""
    if not session_path.exists():
        return "N/A"

    try:
        first_ts = None
        last_ts = None

        with open(session_path) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    ts = d.get('timestamp')
                    if ts:
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts
                except:
                    continue

        if not first_ts or not last_ts:
            return "N/A"

        start = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
        end = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
        total_seconds = int((end - start).total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m {total_seconds % 60}s"
        else:
            return f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"
    except:
        return "N/A"


def format_relative_time(timestamp: str, session_start: str) -> str:
    """Format timestamp as relative time from session start."""
    try:
        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        start = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
        total_seconds = int((ts - start).total_seconds())

        if total_seconds < 0:
            return timestamp[11:19] if len(timestamp) > 19 else timestamp

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"+{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"+{minutes:02d}:{seconds:02d}"
    except:
        return timestamp[11:19] if len(timestamp) > 19 else timestamp


# =============================================================================
# MARKDOWN GENERATION
# =============================================================================

def generate_thinking_markdown(accession_no: str, session_info: dict) -> str:
    """Generate combined markdown with ALL thinking from session."""
    session_path = session_info.get('session_path')
    skill = session_info.get('skill', '')

    # Get metadata from session and attribution reports
    session_meta = extract_metadata_from_session(session_path, accession_no)
    ticker = session_meta.get('ticker', '')
    attr_meta = get_attribution_metadata(accession_no, ticker)

    metadata = {**session_meta, **attr_meta}
    ticker = metadata.get('ticker', 'UNKNOWN')
    filing_date = metadata.get('filing_datetime', '')[:10]

    lines = [
        f"# Thinking: {ticker} {accession_no}",
        "",
        f"**Filing Date**: {filing_date}  ",
    ]

    if metadata.get('return_pct'):
        lines.append(f"**Return**: {metadata['return_pct']}  ")
    if metadata.get('primary_driver'):
        lines.append(f"**Primary Driver**: {metadata['primary_driver']}  ")
    if metadata.get('confidence'):
        lines.append(f"**Confidence**: {metadata['confidence']}  ")

    if not session_path:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*No session found for this accession*")
        return '\n'.join(lines)

    session_id = session_path.stem
    duration = get_session_duration(session_path)
    lines.append(f"**Skill**: {skill}  ")
    lines.append(f"**Duration**: {duration}  ")
    lines.append(f"**Session**: `{session_id[:8]}`  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    agents = discover_all_agents(session_id)
    all_blocks, session_start = collect_all_thinking(session_path, agents)

    if all_blocks:
        source_counts = {}
        source_chars = {}
        for b in all_blocks:
            src = b.get('source', 'unknown')
            source_counts[src] = source_counts.get(src, 0) + 1
            source_chars[src] = source_chars.get(src, 0) + b.get('length', 0)

        lines.append("## Thinking Summary")
        lines.append(f"Total: {len(all_blocks)} blocks, {sum(source_chars.values()):,} chars")
        lines.append("")
        lines.append("| Source | Blocks | Chars |")
        lines.append("|--------|--------|-------|")
        for src in sorted(source_counts.keys()):
            lines.append(f"| {src} | {source_counts[src]} | {source_chars[src]:,} |")
        lines.append("")

        lines.append("## Thinking Timeline")
        lines.append("")

        for i, block in enumerate(all_blocks, 1):
            source = block.get('source', 'unknown')
            timestamp = block.get('timestamp', '')
            rel_time = format_relative_time(timestamp, session_start)
            length = block.get('length', 0)
            text = block.get('text', '')

            if len(text) > 8000:
                text = text[:8000] + f"\n\n... [truncated, {len(text) - 8000} more chars]"

            lines.append(f"### #{i} · {source} · {rel_time}")
            lines.append(f"*{length:,} chars*")
            lines.append("")
            lines.append(text)
            lines.append("")
    else:
        lines.append("*No thinking blocks found*")

    if agents:
        lines.append("---")
        lines.append("")
        agent_types = sorted(set(a['agent_type'] for a in agents))
        lines.append(f"*Agents: primary + {len(agents)} subagents ({', '.join(agent_types)})*")

    return '\n'.join(lines)


# =============================================================================
# INDEX BUILDING
# =============================================================================

def build_index(all_sessions: dict[str, dict]) -> str:
    """Build master index.md."""
    lines = [
        "# Thinking Index",
        "",
        "Extracted thinking from earnings prediction and attribution runs.",
        "",
        "| Accession | Ticker | Date | Skill | Duration | Return | Primary | Sub-Agents | View |",
        "|-----------|--------|------|-------|----------|--------|---------|------------|------|",
    ]

    for accession in sorted(all_sessions.keys(), key=lambda a: all_sessions[a].get('timestamp', ''), reverse=True):
        info = all_sessions[accession]
        session_path = info.get('session_path')
        skill = info.get('skill', '')

        # Get metadata
        session_meta = extract_metadata_from_session(session_path, accession)
        ticker = session_meta.get('ticker', '')
        attr_meta = get_attribution_metadata(accession, ticker)

        date = session_meta.get('filing_datetime', info.get('timestamp', ''))[:10]
        ret = attr_meta.get('return_pct', '')

        primary = session_path.stem[:8] if session_path else '-'
        duration = get_session_duration(session_path) if session_path else '-'

        agents = discover_all_agents(session_path.stem) if session_path else []
        if agents:
            agent_types = sorted(set(a['agent_type'] for a in agents))
            subagent_summary = ', '.join(agent_types)
        else:
            subagent_summary = '-'

        link = f"[View](runs/{accession}.md)"
        lines.append(f"| {accession} | {ticker} | {date} | {skill} | {duration} | {ret} | {primary} | {subagent_summary} | {link} |")

    lines.append("")
    lines.append(f"*Generated: {datetime.now().isoformat()}*")
    return '\n'.join(lines)


# =============================================================================
# MAIN COMMANDS
# =============================================================================

def build_for_accession(accession_no: str) -> bool:
    """Build thinking file for a single accession."""
    print(f"Processing: {accession_no}")

    session_path = find_session_for_accession(accession_no)
    session_info = {
        'session_path': session_path,
        'skill': 'unknown'
    }

    # Try to determine skill type from session
    if session_path:
        try:
            with open(session_path) as f:
                content = f.read(10000)
                if 'earnings-prediction' in content:
                    session_info['skill'] = 'prediction'
                elif 'earnings-attribution' in content:
                    session_info['skill'] = 'attribution'
                elif 'earnings-orchestrator' in content:
                    session_info['skill'] = 'orchestrator'
        except:
            pass

    content = generate_thinking_markdown(accession_no, session_info)

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RUNS_DIR / f"{accession_no}.md"
    with open(output_path, 'w') as f:
        f.write(content)

    print(f"  Saved: {output_path}")
    return True


def build_all():
    """Build thinking files for all accessions found in transcripts."""
    print("Scanning transcripts for earnings sessions...")
    all_sessions = find_all_earnings_sessions()

    print(f"Found {len(all_sessions)} unique accessions")
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    for accession, info in all_sessions.items():
        print(f"\nProcessing: {accession}")

        content = generate_thinking_markdown(accession, info)
        output_path = RUNS_DIR / f"{accession}.md"

        with open(output_path, 'w') as f:
            f.write(content)
        print(f"  Saved: {output_path}")

    # Build index
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_content = build_index(all_sessions)
    index_path = OUTPUT_DIR / "index.md"

    with open(index_path, 'w') as f:
        f.write(index_content)
    print(f"\nIndex saved: {index_path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python3 build-thinking-index.py all              # Build all (scan transcripts)")
        print("  python3 build-thinking-index.py <accession>      # Build for single accession")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'all':
        build_all()
    else:
        build_for_accession(cmd)


if __name__ == "__main__":
    main()
