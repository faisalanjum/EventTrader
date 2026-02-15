#!/usr/bin/env python3
"""
Build thinking files for news analysis from earnings-orchestrator sessions.

Pure filesystem discovery - no CSV dependency.
Extracts thinking from all 4 news-driver tiers: BZ, WEB, PPX, JUDGE.

Usage:
    python build-news-thinking.py --ticker NOG           # Single ticker
    python build-news-thinking.py --ticker NOG --all-sessions  # All sessions for ticker
    python build-news-thinking.py --session <ID>         # Explicit session
    python build-news-thinking.py all                    # All tickers from all sessions

Output:
    Companies/{TICKER}/thinking/{QUARTER}/
    ├── _timeline.md
    └── news/
        ├── _summary.md
        └── {date}.md
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Paths
CLAUDE_DIR = Path.home() / ".claude" / "projects" / "-home-faisal-EventMarketDB"
COMPANIES_DIR = Path("/home/faisal/Obsidian/EventTrader/Earnings/earnings-analysis/Companies")


def parse_prompt(prompt: str, description: str = '') -> dict:
    """Parse agent prompt to extract ticker, date, returns, task_id, quarter.

    Handles two formats:
    - BZ/WEB/PPX: "TICKER YYYY-MM-DD daily_stock daily_adj TASK_ID=N QUARTER=Q"
    - JUDGE: "TASK_ID=N" (ticker/date from description: "JUDGE TICKER YYYY-MM-DD")
    """
    result = {'ticker': None, 'date': None, 'daily_stock': None,
              'daily_adj': None, 'task_id': None, 'quarter': None}

    # Format 1: BZ/WEB/PPX full prompt
    # Handles: "TICKER DATE RETURN1 RETURN2 TASK_ID=N [WEB_TASK_ID=N...] [QUARTER=Q]"
    match = re.match(
        r'(\w+)\s+(\d{4}-\d{2}-\d{2})\s+([\d.-]+)\s+([\d.-]+)\s+TASK_ID=(\d+)',
        prompt
    )
    if match:
        result['ticker'] = match.group(1)
        result['date'] = match.group(2)
        result['daily_stock'] = match.group(3)
        result['daily_adj'] = match.group(4)
        result['task_id'] = match.group(5)
        # Extract QUARTER from anywhere in the prompt
        quarter_match = re.search(r'QUARTER=(\w+)', prompt)
        if quarter_match:
            result['quarter'] = quarter_match.group(1)
        return result

    # Format 2: JUDGE minimal prompt (get ticker/date from description)
    match = re.match(r'TASK_ID=(\d+)', prompt)
    if match:
        result['task_id'] = match.group(1)
        # Extract from description like "JUDGE validate NOG 2023-01-03" or "JUDGE NOG 2023-01-03"
        desc_match = re.match(r'JUDGE\s+(?:validate\s+)?(\w+)\s+(\d{4}-\d{2}-\d{2})', description)
        if desc_match:
            result['ticker'] = desc_match.group(1)
            result['date'] = desc_match.group(2)

    return result


def find_all_news_sessions() -> dict[str, list]:
    """
    Scan all transcripts to find sessions with news-driver agents.

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
                    if '"news-driver-' not in line:
                        continue

                    data = json.loads(line)
                    if data.get('type') == 'assistant':
                        content = data.get('message', {}).get('content', [])
                        for block in content:
                            if isinstance(block, dict) and block.get('name') == 'Task':
                                inp = block.get('input', {})
                                if 'news-driver' in inp.get('subagent_type', ''):
                                    prompt = inp.get('prompt', '')
                                    parsed = parse_prompt(prompt)
                                    if parsed['ticker']:
                                        ticker_counts[parsed['ticker']] += 1
        except:
            continue

        for ticker, count in ticker_counts.items():
            results[ticker].append((session_file.stem, mtime, count))

    return results


def find_sessions_for_ticker(ticker: str, all_sessions: bool = False) -> list[str]:
    """
    Find sessions with news-driver agents for a ticker.

    Returns list of session_ids (most recent first).
    If all_sessions=False, returns only the most recent.
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
                    if '"news-driver-' in line and f'"{ticker} ' in line:
                        data = json.loads(line)
                        if data.get('type') == 'assistant':
                            content = data.get('message', {}).get('content', [])
                            for block in content:
                                if isinstance(block, dict) and block.get('name') == 'Task':
                                    inp = block.get('input', {})
                                    if 'news-driver' in inp.get('subagent_type', ''):
                                        prompt = inp.get('prompt', '')
                                        if prompt.startswith(f'{ticker} '):
                                            agent_count += 1
        except:
            continue

        if agent_count > 0:
            candidates.append((session_file.stem, mtime, agent_count))

    if not candidates:
        return []

    # Sort by modification time (most recent first)
    candidates.sort(key=lambda x: x[1], reverse=True)

    if all_sessions:
        return [c[0] for c in candidates]
    else:
        return [candidates[0][0]]


def discover_agents(session_id: str, ticker_filter: str = None) -> list[dict]:
    """
    Discover all news-driver sub-agents from a session.

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

                # Find Task tool calls
                if data.get('type') == 'assistant':
                    content = data.get('message', {}).get('content', [])
                    for block in content:
                        if isinstance(block, dict) and block.get('name') == 'Task':
                            tool_id = block.get('id')
                            inp = block.get('input', {})
                            subagent_type = inp.get('subagent_type', '')
                            if 'news-driver' in subagent_type:
                                task_calls[tool_id] = {
                                    'subagent_type': subagent_type,
                                    'prompt': inp.get('prompt', ''),
                                    'description': inp.get('description', '')
                                }

                # Find agent progress messages
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

        parsed = parse_prompt(info['prompt'], info.get('description', ''))

        # Apply ticker filter
        if ticker_filter and parsed['ticker'] != ticker_filter:
            continue

        agents.append({
            'agent_id': agent_id,
            'subagent_type': info['subagent_type'],
            'ticker': parsed['ticker'],
            'date': parsed['date'],
            'quarter': parsed['quarter'],
            'daily_stock': parsed['daily_stock'],
            'daily_adj': parsed['daily_adj'],
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


def generate_date_file(date: str, agents: list, ticker: str, session_start: str) -> str:
    """Generate markdown for one date's BZ→WEB→PPX chain."""
    sample = agents[0] if agents else {}

    lines = [
        f"# {date} | {sample.get('daily_stock', '?')}% stock | {sample.get('daily_adj', '?')}% adj",
        "",
        "## Result",
    ]

    # Sort by tier
    tier_order = {'news-driver-bz': 1, 'news-driver-web': 2, 'news-driver-ppx': 3, 'news-driver-judge': 4}
    sorted_agents = sorted(agents, key=lambda a: tier_order.get(a['subagent_type'], 99))

    tiers = ' → '.join(a['subagent_type'].replace('news-driver-', '').upper() for a in sorted_agents)
    lines.append(f"**Tiers:** {tiers}")
    lines.append("")
    lines.append("---")
    lines.append("")

    tier_names = {
        'news-driver-bz': 'Tier 1: Benzinga',
        'news-driver-web': 'Tier 2: WebSearch',
        'news-driver-ppx': 'Tier 3: Perplexity',
        'news-driver-judge': 'Tier 4: Judge'
    }
    emoji = {'thinking': '💭', 'tool_use': '🔧', 'text': '📝'}

    for agent in sorted_agents:
        lines.append(f"## {tier_names.get(agent['subagent_type'], agent['subagent_type'])}")
        lines.append("")

        blocks = extract_blocks(agent['transcript_path'])
        if not blocks:
            lines.append("*No blocks found*")
            lines.append("")
            continue

        for i, b in enumerate(blocks, 1):
            t = format_time(b['timestamp'], session_start)
            lines.append(f"### {emoji.get(b['type'], '❓')} #{i} · {t}")

            if b['type'] == 'tool_use':
                lines.append("```")
                lines.append(b['text'])
                lines.append("```")
            else:
                lines.append(f"*{b['length']} chars*")
                lines.append("")
                lines.append(b['text'])
            lines.append("")

        lines.append("---")
        lines.append("")

    return '\n'.join(lines)


def generate_summary(dates_data: dict, ticker: str, quarter: str) -> str:
    """Generate summary table for a quarter."""
    lines = [
        f"# {quarter} News Analysis",
        "",
        "| Date | Move | Tiers | Link |",
        "|------|------|-------|------|",
    ]

    for date in sorted(dates_data.keys()):
        agents = dates_data[date]
        move = agents[0].get('daily_stock', '?') if agents else '?'
        tiers = ' → '.join(sorted(set(
            a['subagent_type'].replace('news-driver-', '').upper() for a in agents
        ), key=lambda x: {'BZ': 1, 'WEB': 2, 'PPX': 3, 'JUDGE': 4}.get(x, 99)))
        lines.append(f"| {date} | {move}% | {tiers} | [{date}]({date}.md) |")

    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    return '\n'.join(lines)


def generate_timeline(agents: list, ticker: str, quarter: str, session_start: str) -> str:
    """Generate full chronological timeline."""
    lines = [
        f"# {quarter} Timeline",
        "",
        f"**Ticker:** {ticker}  ",
        f"**Agents:** {len(agents)}",
        "",
        "---",
        "",
    ]

    # Collect all blocks with source
    all_blocks = []
    for agent in agents:
        for b in extract_blocks(agent['transcript_path']):
            b['source'] = agent['subagent_type'].replace('news-driver-', '')
            b['date'] = agent['date']
            all_blocks.append(b)

    all_blocks.sort(key=lambda x: x.get('timestamp', ''))
    lines.append(f"**Blocks:** {len(all_blocks)}")
    lines.append("")

    emoji = {'thinking': '💭', 'tool_use': '🔧', 'text': '📝'}

    for i, b in enumerate(all_blocks, 1):
        t = format_time(b['timestamp'], session_start)
        lines.append(f"### #{i} · {emoji.get(b['type'], '❓')} · {b['source']} · {b['date']} · {t}")

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


def generate_ticker_index(ticker: str, existing_quarters: set) -> str:
    """Generate ticker-level index."""
    lines = [
        f"# {ticker} Thinking",
        "",
        "| Quarter | News | Guidance | Prediction | Attribution |",
        "|---------|------|----------|------------|-------------|",
    ]

    for q in sorted(existing_quarters, reverse=True):
        lines.append(f"| [{q}]({q}/_timeline.md) | [✓]({q}/news/_summary.md) | - | - | - |")

    lines.append("")
    lines.append(f"*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    return '\n'.join(lines)


def build(session_id: str, ticker: str):
    """Main build function."""
    print(f"Building thinking files for {ticker} from session {session_id[:8]}...")

    agents = discover_agents(session_id, ticker_filter=ticker)
    if not agents:
        print("ERROR: No news-driver agents found")
        return False

    print(f"Found {len(agents)} agents")
    session_start = get_session_start(session_id)

    # Group by quarter -> date
    # First, collect all agents by date and find best quarter for each date
    by_date = defaultdict(list)
    for agent in agents:
        by_date[agent['date']].append(agent)

    # For each date, find the quarter (from any agent that has it)
    date_quarter_map = {}
    for date, date_agents in by_date.items():
        quarter = 'UNKNOWN'
        for a in date_agents:
            if a['quarter']:
                quarter = a['quarter']
                break
        date_quarter_map[date] = quarter

    # Now group by quarter -> date with all agents for that date
    grouped = defaultdict(lambda: defaultdict(list))
    for date, date_agents in by_date.items():
        q = date_quarter_map[date]
        grouped[q][date] = date_agents

    ticker_dir = COMPANIES_DIR / ticker / "thinking"
    all_quarters = set()

    for quarter, dates_data in grouped.items():
        all_quarters.add(quarter)
        quarter_dir = ticker_dir / quarter
        news_dir = quarter_dir / "news"
        news_dir.mkdir(parents=True, exist_ok=True)

        print(f"  {quarter}: {len(dates_data)} dates")

        # Per-date files
        for date, date_agents in dates_data.items():
            content = generate_date_file(date, date_agents, ticker, session_start)
            path = news_dir / f"{date}.md"
            path.write_text(content)

        # Summary
        content = generate_summary(dates_data, ticker, quarter)
        (news_dir / "_summary.md").write_text(content)

        # Timeline
        quarter_agents = [a for agents in dates_data.values() for a in agents]
        content = generate_timeline(quarter_agents, ticker, quarter, session_start)
        (quarter_dir / "_timeline.md").write_text(content)

    # Find existing quarters
    for d in ticker_dir.iterdir():
        if d.is_dir() and d.name.startswith('Q'):
            all_quarters.add(d.name)

    # Ticker index
    content = generate_ticker_index(ticker, all_quarters)
    (ticker_dir / "_index.md").write_text(content)

    print(f"Done! Files at: {ticker_dir}")
    return True


def build_all():
    """Build thinking files for all tickers found in all sessions."""
    print("Scanning all transcripts for news-driver sessions...")
    all_sessions = find_all_news_sessions()

    if not all_sessions:
        print("No news-driver sessions found")
        return False

    print(f"Found {len(all_sessions)} tickers with news-driver agents")

    for ticker in sorted(all_sessions.keys()):
        sessions = all_sessions[ticker]
        # Sort by modification time, get most recent
        sessions.sort(key=lambda x: x[1], reverse=True)
        session_id = sessions[0][0]
        agent_count = sessions[0][2]

        print(f"\n{ticker}: session {session_id[:8]} ({agent_count} agents)")
        build(session_id, ticker)

    return True


def main():
    # Check for 'all' command
    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        success = build_all()
        sys.exit(0 if success else 1)

    parser = argparse.ArgumentParser(description='Build thinking files from earnings-orchestrator sessions')
    parser.add_argument('--ticker', '-t', help='Ticker symbol')
    parser.add_argument('--session', '-s', help='Session ID (auto-detected if not provided)')
    parser.add_argument('--all-sessions', action='store_true', help='Process all sessions for ticker (not just recent)')

    args = parser.parse_args()

    if not args.ticker:
        print("Usage:")
        print("  python build-news-thinking.py all                    # All tickers")
        print("  python build-news-thinking.py --ticker NOG           # Single ticker")
        print("  python build-news-thinking.py --ticker NOG --all-sessions  # All sessions")
        print("  python build-news-thinking.py --session <ID> --ticker NOG  # Explicit session")
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
