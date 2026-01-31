#!/usr/bin/env python3
"""
Build thinking files for guidance extraction from earnings-orchestrator sessions.

Pure filesystem discovery - no CSV dependency.
Extracts thinking from guidance-* agents: 8k, 10k, 10q, transcript, news, extract.

Usage:
    python build-guidance-thinking.py --ticker NOG           # Single ticker
    python build-guidance-thinking.py --ticker NOG --all-sessions  # All sessions for ticker
    python build-guidance-thinking.py --session <ID>         # Explicit session
    python build-guidance-thinking.py all                    # All tickers from all sessions

Output:
    Companies/{TICKER}/thinking/{QUARTER}/
    ├── _timeline.md
    └── guidance/
        ├── _summary.md
        └── {source_type}_{source_id_short}.md
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
CLAUDE_DIR = Path.home() / ".claude" / "projects" / "-home-faisal-EventMarketDB"
COMPANIES_DIR = Path("/home/faisal/Obsidian/EventTrader/Earnings/earnings-analysis/Companies")


def parse_guidance_prompt(prompt: str, description: str = '') -> dict:
    """Parse guidance agent prompt to extract ticker, source info, quarter, task_id.

    Handles formats like:
    - New: "TICKER REPORT_ID SOURCE_TYPE SOURCE_KEY QUARTER TASK_ID=N"
    - Old: "TICKER REPORT_ID QUARTER TASK_ID=N" (8k/news agents)
    """
    result = {'ticker': None, 'report_id': None, 'source_type': None,
              'source_key': None, 'quarter': None, 'task_id': None}

    # New unified guidance-extract format: TICKER REPORT_ID SOURCE_TYPE SOURCE_KEY QUARTER FYE=N TASK_ID=N
    match = re.match(
        r'(\w+)\s+(\S+)\s+(\w+)\s+(\S+)\s+(Q\d+_FY\d+)\s+FYE=\d+\s+TASK_ID=(\d+)',
        prompt
    )
    if match:
        result['ticker'] = match.group(1)
        result['report_id'] = match.group(2)
        result['source_type'] = match.group(3)
        result['source_key'] = match.group(4)
        result['quarter'] = match.group(5)
        result['task_id'] = match.group(6)
        return result

    # Old format: TICKER REPORT_ID QUARTER TASK_ID=N (used by guidance-8k, guidance-news)
    match = re.match(
        r'(\w+)\s+(\S+)\s+(Q\d+_FY\d+)\s+TASK_ID=(\d+)',
        prompt
    )
    if match:
        result['ticker'] = match.group(1)
        result['report_id'] = match.group(2)
        result['quarter'] = match.group(3)
        result['task_id'] = match.group(4)
        # Infer source_type from description like "8K guidance NOG ..." or "News guidance NOG ..."
        if 'news' in description.lower():
            result['source_type'] = 'news'
        elif '8k' in description.lower():
            result['source_type'] = '8k'
        elif '10k' in description.lower():
            result['source_type'] = '10k'
        elif '10q' in description.lower():
            result['source_type'] = '10q'
        elif 'transcript' in description.lower():
            result['source_type'] = 'transcript'
        return result

    # Fallback: extract task_id and quarter from anywhere in prompt
    match = re.search(r'TASK_ID=(\d+)', prompt)
    if match:
        result['task_id'] = match.group(1)
        # Try to get ticker from start of prompt
        ticker_match = re.match(r'(\w+)', prompt)
        if ticker_match:
            result['ticker'] = ticker_match.group(1)
        # Try to get quarter from anywhere in prompt
        quarter_match = re.search(r'(Q\d+_FY\d+)', prompt)
        if quarter_match:
            result['quarter'] = quarter_match.group(1)

    return result


def find_all_guidance_sessions() -> dict[str, list]:
    """
    Scan all transcripts to find sessions with guidance-* agents.

    Returns {ticker: [(session_id, mtime, agent_count), ...]}
    """
    results = defaultdict(list)

    for session_file in CLAUDE_DIR.glob("*.jsonl"):
        if session_file.name.startswith("agent-"):
            continue

        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        ticker_counts = defaultdict(int)

        try:
            with open(session_file) as f:
                for line in f:
                    if '"guidance-' not in line:
                        continue

                    data = json.loads(line)
                    if data.get('type') == 'assistant':
                        content = data.get('message', {}).get('content', [])
                        for block in content:
                            if isinstance(block, dict) and block.get('name') == 'Task':
                                inp = block.get('input', {})
                                subagent = inp.get('subagent_type', '')
                                if subagent.startswith('guidance-'):
                                    prompt = inp.get('prompt', '')
                                    parsed = parse_guidance_prompt(prompt)
                                    if parsed['ticker']:
                                        ticker_counts[parsed['ticker']] += 1
        except:
            continue

        for ticker, count in ticker_counts.items():
            results[ticker].append((session_file.stem, mtime, count))

    return results


def find_sessions_for_ticker(ticker: str, all_sessions: bool = False) -> list[str]:
    """
    Find sessions with guidance-* agents for a ticker.

    Returns list of session_ids (most recent first).
    """
    candidates = []

    for session_file in CLAUDE_DIR.glob("*.jsonl"):
        if session_file.name.startswith("agent-"):
            continue

        mtime = datetime.fromtimestamp(session_file.stat().st_mtime)
        agent_count = 0

        try:
            with open(session_file) as f:
                for line in f:
                    if '"guidance-' in line and f'"{ticker}' in line:
                        data = json.loads(line)
                        if data.get('type') == 'assistant':
                            content = data.get('message', {}).get('content', [])
                            for block in content:
                                if isinstance(block, dict) and block.get('name') == 'Task':
                                    inp = block.get('input', {})
                                    subagent = inp.get('subagent_type', '')
                                    if subagent.startswith('guidance-'):
                                        prompt = inp.get('prompt', '')
                                        if f'{ticker}' in prompt:
                                            agent_count += 1
        except:
            continue

        if agent_count > 0:
            candidates.append((session_file.stem, mtime, agent_count))

    if not candidates:
        return []

    candidates.sort(key=lambda x: x[1], reverse=True)

    if all_sessions:
        return [c[0] for c in candidates]
    else:
        return [candidates[0][0]]


def discover_agents(session_id: str, ticker_filter: str = None) -> list[dict]:
    """
    Discover all guidance-* sub-agents from a session.

    Returns list of agent metadata with transcript paths.
    """
    session_file = CLAUDE_DIR / f"{session_id}.jsonl"
    if not session_file.exists():
        print(f"ERROR: Session file not found: {session_file}")
        return []

    # Collect Task tool calls: tool_use_id -> {subagent_type, prompt, description}
    task_calls = {}
    # Collect agent progress: tool_use_id -> agentId
    agent_map = {}

    with open(session_file) as f:
        for line in f:
            try:
                data = json.loads(line)

                if data.get('type') == 'assistant':
                    content = data.get('message', {}).get('content', [])
                    for block in content:
                        if isinstance(block, dict) and block.get('name') == 'Task':
                            tool_id = block.get('id')
                            inp = block.get('input', {})
                            subagent_type = inp.get('subagent_type', '')
                            if subagent_type.startswith('guidance-'):
                                task_calls[tool_id] = {
                                    'subagent_type': subagent_type,
                                    'prompt': inp.get('prompt', ''),
                                    'description': inp.get('description', '')
                                }

                if data.get('type') == 'progress':
                    agent_data = data.get('data', {})
                    if agent_data.get('agentId'):
                        parent_tool_id = data.get('parentToolUseID')
                        agent_id = agent_data['agentId']
                        if parent_tool_id and parent_tool_id not in agent_map:
                            agent_map[parent_tool_id] = agent_id
            except json.JSONDecodeError:
                continue

    # Build agent list
    agents = []
    subagents_dir = CLAUDE_DIR / session_id / "subagents"

    for tool_id, info in task_calls.items():
        agent_id = agent_map.get(tool_id)
        if not agent_id:
            continue

        # Try session-level first (CLI v2.1.3+), then ROOT level (CLI v2.1.1)
        transcript_path = subagents_dir / f"agent-{agent_id}.jsonl"
        if not transcript_path.exists():
            transcript_path = CLAUDE_DIR / f"agent-{agent_id}.jsonl"
            if not transcript_path.exists():
                print(f"  WARNING: Transcript not found: agent-{agent_id}.jsonl")
                continue

        parsed = parse_guidance_prompt(info['prompt'], info.get('description', ''))

        if ticker_filter and parsed['ticker'] != ticker_filter:
            continue

        agents.append({
            'agent_id': agent_id,
            'subagent_type': info['subagent_type'],
            'ticker': parsed['ticker'],
            'report_id': parsed['report_id'],
            'source_type': parsed['source_type'],
            'source_key': parsed['source_key'],
            'quarter': parsed['quarter'],
            'task_id': parsed['task_id'],
            'transcript_path': transcript_path
        })

    return agents


def extract_blocks(transcript_path: Path, max_thinking_chars: int = 8000) -> list[dict]:
    """Extract thinking, tool_use, and text blocks from a transcript."""
    blocks = []

    if not transcript_path.exists():
        return blocks

    with open(transcript_path) as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('type') != 'assistant':
                    continue

                timestamp = data.get('timestamp', '')
                content = data.get('message', {}).get('content', [])

                for block in content:
                    if not isinstance(block, dict):
                        continue

                    block_type = block.get('type')

                    if block_type == 'thinking':
                        text = block.get('thinking', '')
                        length = len(text)
                        if length > max_thinking_chars:
                            text = text[:max_thinking_chars] + f"\n\n... [{length - max_thinking_chars} more chars]"
                        blocks.append({
                            'type': 'thinking', 'timestamp': timestamp,
                            'text': text, 'length': length
                        })

                    elif block_type == 'tool_use':
                        name = block.get('name', 'unknown')
                        inp = block.get('input', {})
                        if name == 'Bash':
                            text = f"{name}: {inp.get('command', '')[:100]}"
                        else:
                            text = f"{name}({json.dumps(inp)[:100]})"
                        blocks.append({
                            'type': 'tool_use', 'timestamp': timestamp,
                            'text': text, 'length': len(text)
                        })

                    elif block_type == 'text':
                        text = block.get('text', '').strip()
                        if text:
                            blocks.append({
                                'type': 'text', 'timestamp': timestamp,
                                'text': text[:2000], 'length': len(text)
                            })
            except json.JSONDecodeError:
                continue

    return blocks


def get_session_start(session_id: str) -> str:
    """Get earliest timestamp from session."""
    session_file = CLAUDE_DIR / f"{session_id}.jsonl"
    with open(session_file) as f:
        for line in f:
            try:
                data = json.loads(line)
                if ts := data.get('timestamp'):
                    return ts
            except:
                continue
    return datetime.now().isoformat()


def format_time(timestamp: str, start: str) -> str:
    """Format timestamp as +MM:SS relative to start."""
    try:
        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        st = datetime.fromisoformat(start.replace('Z', '+00:00'))
        secs = int((ts - st).total_seconds())
        if secs < 0:
            return timestamp[11:19]
        return f"+{secs // 60:02d}:{secs % 60:02d}"
    except:
        return timestamp[11:19] if len(timestamp) > 19 else "??:??"


def short_id(report_id: str) -> str:
    """Shorten report_id for filename."""
    if not report_id:
        return "unknown"
    # Keep last 8 chars for accession numbers, or first 20 for others
    if '-' in report_id and len(report_id) > 20:
        return report_id.split('-')[-1][:12]
    return report_id[:20].replace('/', '_').replace(':', '_')


def generate_source_file(agent: dict, ticker: str, session_start: str) -> str:
    """Generate markdown for one guidance source."""
    source_type = agent['source_type'] or 'unknown'
    source_key = agent['source_key'] or 'N/A'
    lines = [
        f"# {source_type} | {source_key}",
        "",
        f"**Report:** {agent['report_id'] or 'N/A'}  ",
        f"**Agent:** {agent['subagent_type']}  ",
        f"**Quarter:** {agent['quarter'] or 'UNKNOWN'}",
        "",
        "---",
        "",
    ]

    emoji = {'thinking': '💭', 'tool_use': '🔧', 'text': '📝'}
    blocks = extract_blocks(agent['transcript_path'])

    if not blocks:
        lines.append("*No blocks found*")
        return '\n'.join(lines)

    for i, b in enumerate(blocks, 1):
        t = format_time(b['timestamp'], session_start)
        lines.append(f"## {emoji.get(b['type'], '❓')} #{i} · {t}")

        if b['type'] == 'tool_use':
            lines.append("```")
            lines.append(b['text'])
            lines.append("```")
        else:
            lines.append(f"*{b['length']} chars*")
            lines.append("")
            lines.append(b['text'])
        lines.append("")

    return '\n'.join(lines)


def generate_summary(agents: list, ticker: str, quarter: str) -> str:
    """Generate summary table for a quarter's guidance sources."""
    lines = [
        f"# {quarter} Guidance Analysis",
        "",
        "| Source Type | Source Key | Report | Agent | Link |",
        "|-------------|------------|--------|-------|------|",
    ]

    # Group by source_type
    by_type = defaultdict(list)
    for a in agents:
        by_type[a['source_type'] or 'unknown'].append(a)

    for source_type in sorted(by_type.keys()):
        for a in by_type[source_type]:
            sid = short_id(a['report_id'])
            fname = f"{a['source_type'] or 'unk'}_{sid}.md"
            source_key = (a['source_key'] or 'N/A')[:20]
            lines.append(
                f"| {a['source_type'] or 'N/A'} | {source_key} | {sid} | "
                f"{a['subagent_type']} | [{fname}]({fname}) |"
            )

    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    return '\n'.join(lines)


def generate_timeline(agents: list, ticker: str, quarter: str, session_start: str) -> str:
    """Generate full chronological timeline."""
    lines = [
        f"# {quarter} Guidance Timeline",
        "",
        f"**Ticker:** {ticker}  ",
        f"**Agents:** {len(agents)}",
        "",
        "---",
        "",
    ]

    all_blocks = []
    for agent in agents:
        for b in extract_blocks(agent['transcript_path']):
            b['source'] = agent['subagent_type'].replace('guidance-', '')
            b['source_type'] = agent['source_type'] or 'unknown'
            all_blocks.append(b)

    all_blocks.sort(key=lambda x: x.get('timestamp', ''))
    lines.append(f"**Blocks:** {len(all_blocks)}")
    lines.append("")

    emoji = {'thinking': '💭', 'tool_use': '🔧', 'text': '📝'}

    for i, b in enumerate(all_blocks, 1):
        t = format_time(b['timestamp'], session_start)
        lines.append(f"### #{i} · {emoji.get(b['type'], '❓')} · {b['source']} · {b['source_type']} · {t}")

        if b['type'] == 'tool_use':
            lines.append("```")
            lines.append(b['text'])
            lines.append("```")
        else:
            text = b['text'][:500]
            if len(b['text']) > 500:
                text += f"\n... [{b['length']} chars]"
            lines.append(text)
        lines.append("")

    return '\n'.join(lines)


def build(session_id: str, ticker: str):
    """Main build function."""
    print(f"Building guidance thinking files for {ticker} from session {session_id[:8]}...")

    agents = discover_agents(session_id, ticker_filter=ticker)
    if not agents:
        print("ERROR: No guidance-* agents found")
        return False

    print(f"Found {len(agents)} agents")
    session_start = get_session_start(session_id)

    # Group by quarter
    grouped = defaultdict(list)
    for agent in agents:
        q = agent['quarter'] or 'UNKNOWN'
        grouped[q].append(agent)

    ticker_dir = COMPANIES_DIR / ticker / "thinking"
    all_quarters = set()

    for quarter, quarter_agents in grouped.items():
        all_quarters.add(quarter)
        quarter_dir = ticker_dir / quarter
        guidance_dir = quarter_dir / "guidance"
        guidance_dir.mkdir(parents=True, exist_ok=True)

        print(f"  {quarter}: {len(quarter_agents)} sources")

        # Per-source files
        for agent in quarter_agents:
            sid = short_id(agent['report_id'])
            fname = f"{agent['source_type'] or 'unk'}_{sid}.md"
            content = generate_source_file(agent, ticker, session_start)
            (guidance_dir / fname).write_text(content)

        # Summary
        content = generate_summary(quarter_agents, ticker, quarter)
        (guidance_dir / "_summary.md").write_text(content)

        # Timeline (includes both news and guidance if exists)
        content = generate_timeline(quarter_agents, ticker, quarter, session_start)
        existing_timeline = quarter_dir / "_timeline.md"
        # Append guidance timeline after news if exists
        if existing_timeline.exists():
            existing = existing_timeline.read_text()
            if "Guidance Timeline" not in existing:
                content = existing + "\n\n---\n\n" + content
                existing_timeline.write_text(content)
        else:
            (quarter_dir / "_timeline.md").write_text(content)

    print(f"Done! Files at: {ticker_dir}")
    return True


def build_all():
    """Build thinking files for all tickers found in all sessions."""
    print("Scanning all transcripts for guidance-* sessions...")
    all_sessions = find_all_guidance_sessions()

    if not all_sessions:
        print("No guidance-* sessions found")
        return False

    print(f"Found {len(all_sessions)} tickers with guidance-* agents")

    for ticker in sorted(all_sessions.keys()):
        sessions = all_sessions[ticker]
        sessions.sort(key=lambda x: x[1], reverse=True)
        session_id = sessions[0][0]
        agent_count = sessions[0][2]

        print(f"\n{ticker}: session {session_id[:8]} ({agent_count} agents)")
        build(session_id, ticker)

    return True


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        success = build_all()
        sys.exit(0 if success else 1)

    parser = argparse.ArgumentParser(description='Build guidance thinking files from earnings-orchestrator sessions')
    parser.add_argument('--ticker', '-t', help='Ticker symbol')
    parser.add_argument('--session', '-s', help='Session ID (auto-detected if not provided)')
    parser.add_argument('--all-sessions', action='store_true', help='Process all sessions for ticker')

    args = parser.parse_args()

    if not args.ticker:
        print("Usage:")
        print("  python build-guidance-thinking.py all                    # All tickers")
        print("  python build-guidance-thinking.py --ticker NOG           # Single ticker")
        print("  python build-guidance-thinking.py --ticker NOG --all-sessions  # All sessions")
        print("  python build-guidance-thinking.py --session <ID> --ticker NOG  # Explicit session")
        sys.exit(1)

    ticker = args.ticker.upper()

    if args.session:
        session_ids = [args.session]
        print(f"Using provided session: {args.session}")
    else:
        print(f"Finding sessions for {ticker}...")
        session_ids = find_sessions_for_ticker(ticker, all_sessions=args.all_sessions)
        if not session_ids:
            print(f"ERROR: No sessions found for {ticker}")
            sys.exit(1)
        print(f"Found {len(session_ids)} session(s)")

    success = True
    for session_id in session_ids:
        print(f"\nProcessing session: {session_id[:8]}...")
        if not build(session_id, ticker):
            success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
