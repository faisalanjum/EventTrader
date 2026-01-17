#!/usr/bin/env python3
"""
Build Obsidian-compatible thinking index from Claude Code transcripts.

Reads CSV history files from earnings-prediction/attribution skills,
extracts thinking blocks from all sessions (primary + sub-agents),
generates combined markdown files per accession, and builds master index.

Updated 2026-01-16: Now extracts thinking from sub-agent transcripts
(forked skills in subagents/ directory), not just primary sessions.

Output: ~/Obsidian/EventTrader/Earnings/earnings-analysis/thinking/
"""

import json
import csv
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Paths
CLAUDE_DIR = Path.home() / ".claude" / "projects" / "-home-faisal-EventMarketDB"
SKILLS_DIR = Path("/home/faisal/EventMarketDB/.claude/skills")
OUTPUT_DIR = Path.home() / "Obsidian" / "EventTrader" / "Earnings" / "earnings-analysis" / "thinking"
RUNS_DIR = OUTPUT_DIR / "runs"
PREDICTIONS_CSV = Path("/home/faisal/EventMarketDB/earnings-analysis/predictions.csv")
COMPANIES_DIR = Path("/home/faisal/EventMarketDB/earnings-analysis/Companies")

# Shared CSV history file (both skills append here)
SHARED_HISTORY_CSV = Path("/home/faisal/EventMarketDB/.claude/shared/earnings/subagent-history.csv")


def find_sessions_for_accession(accession_no: str) -> list[Path]:
    """Find transcripts where earnings skill was actually invoked for this accession.

    Matches two types of invocations:
    1. Slash command format: <command-message> with <command-args>accession</command-args>
    2. SDK/natural language: "Run /earnings-prediction for ticker XXX, accession YYY"
    """
    if not accession_no:
        return []

    matches = []
    for t in CLAUDE_DIR.glob("*.jsonl"):
        try:
            for line in t.open():
                # Quick filter: accession must be present
                if accession_no not in line:
                    continue

                # Parse JSON to verify structure
                data = json.loads(line)
                if data.get('type') != 'user':
                    continue

                content = data.get('message', {}).get('content', '')
                if not isinstance(content, str):
                    continue

                # Method 1: Slash command format (CLI invocation)
                if content.startswith('<command-message>'):
                    if f'<command-args>{accession_no}</command-args>' in content:
                        matches.append(t)
                        break

                # Method 2: SDK/natural language format (K8s or programmatic)
                # Pattern: Message must START with "Run /earnings-" to be an actual invocation
                # This excludes conversations that just discuss/mention the accession
                if content.startswith('Run /earnings-') and accession_no in content:
                    matches.append(t)
                    break
        except:
            continue

    # Most recent first - only return most recent session to avoid pollution from old runs
    sorted_matches = sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)
    return sorted_matches[:1] if sorted_matches else []


# Skill detection patterns - add new skills here for future robustness
SKILL_PATTERNS = {
    # Neo4j skills
    'neo4j-report': ['neo4j-report', 'sec filing', '8-k', '10-k', '10-q'],
    'neo4j-xbrl': ['neo4j-xbrl', 'xbrl', 'financial statement'],
    'neo4j-entity': ['neo4j-entity', 'company info', 'ticker lookup'],
    'neo4j-news': ['neo4j-news', 'news article'],
    'neo4j-transcript': ['neo4j-transcript', 'earnings call', 'transcript'],
    # Data skills
    'filtered-data': ['filtered-data', 'filter protocol', 'filter agent'],
    'alphavantage-earnings': ['alphavantage', 'consensus estimate', 'earnings_estimates', 'analyst estimate'],
    # Perplexity skills
    'perplexity-search': ['perplexity-search', 'perplexity_search'],
    'perplexity-ask': ['perplexity-ask', 'perplexity_ask'],
    'perplexity-reason': ['perplexity-reason', 'perplexity_reason'],
    'perplexity-research': ['perplexity-research', 'perplexity_research'],
    # Earnings skills
    'earnings-prediction': ['earnings-prediction', 'predict stock direction', 'prediction analysis'],
    'earnings-attribution': ['earnings-attribution', 'stock move', 'attribution analysis'],
    'earnings-orchestrator': ['earnings-orchestrator', 'batch earnings'],
}


def _identify_skill_type_from_file(agent_file: Path) -> str:
    """Identify skill type by scanning file for command-name tag or prompt patterns.

    Strategy (in order of priority):
    1. Look for <command-name>skill-name</command-name> tag
    2. Look for .claude/skills/skill-name path
    3. Scan content for known skill patterns
    """
    import re
    try:
        content_sample = ""
        with open(agent_file, 'r') as f:
            for i, line in enumerate(f):
                if i > 10:  # Check first 10 lines
                    break
                content_sample += line

                # Priority 1: Check for command-name tag (most reliable)
                if '<command-name>' in line:
                    match = re.search(r'<command-name>([^<]+)</command-name>', line)
                    if match:
                        return match.group(1)

                # Priority 2: Check for skill directory in prompt
                if '.claude/skills/' in line:
                    match = re.search(r'\.claude/skills/([^/\s"\']+)', line)
                    if match:
                        return match.group(1)

        # Priority 3: Pattern matching on content
        content_lower = content_sample.lower()
        for skill_name, patterns in SKILL_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in content_lower:
                    return skill_name

    except Exception as e:
        print(f"  Warning: Could not identify skill type for {agent_file.name}: {e}")
    return 'unknown'


def _identify_skill_type(prompt: str) -> str:
    """Identify skill type from prompt content using pattern matching."""
    if not prompt:
        return 'unknown'
    prompt_lower = str(prompt).lower()

    # Check against all known patterns
    for skill_name, patterns in SKILL_PATTERNS.items():
        for pattern in patterns:
            if pattern.lower() in prompt_lower:
                return skill_name

    return 'unknown'


def discover_subagents(primary_session_id: str) -> list[dict]:
    """
    Discover all sub-agents spawned during a primary session.
    Returns list of {agent_id, agent_type, path} dicts.

    Handles two CLI version behaviors:
    - v2.1.3+: Agent files in {sessionId}/subagents/agent-*.jsonl
    - v2.1.1 and earlier: Agent files at ROOT level with sessionId in content
    """
    import re

    if not primary_session_id:
        return []

    # Find the full session ID if partial
    full_session_id = primary_session_id
    if len(primary_session_id) < 36:
        matches = list(CLAUDE_DIR.glob(f"{primary_session_id}*.jsonl"))
        if matches:
            full_session_id = matches[0].stem

    subagents = []

    # Method 1: Check subagents directory (CLI v2.1.3+)
    subagents_dir = CLAUDE_DIR / full_session_id / "subagents"
    if subagents_dir.exists():
        for agent_file in sorted(subagents_dir.glob("agent-*.jsonl")):
            agent_id = agent_file.stem.replace("agent-", "")
            subagents.append({
                'agent_id': agent_id,
                'agent_type': 'unknown',  # Will be filled in later
                'path': agent_file
            })

    # Method 2: Check ROOT-level agent files (CLI v2.1.1 and earlier)
    # These have sessionId in the file content, not in directory structure
    for agent_file in CLAUDE_DIR.glob("agent-*.jsonl"):
        try:
            with open(agent_file, 'r') as f:
                first_line = f.readline()
                data = json.loads(first_line)
                file_session_id = data.get('sessionId', '')
                # Match if sessionId matches and it's a sidechain (forked skill)
                if file_session_id == full_session_id and data.get('isSidechain'):
                    agent_id = data.get('agentId', agent_file.stem.replace("agent-", ""))
                    # Skip if already found in subagents directory
                    if not any(sa['agent_id'] == agent_id for sa in subagents):
                        # Try to identify skill type from prompt
                        prompt = data.get('message', {}).get('content', '')
                        if isinstance(prompt, str) and 'Warmup' in prompt:
                            continue  # Skip warmup agents
                        # Try to identify skill type from prompt, fallback to file scan
                        skill_type = _identify_skill_type(prompt)
                        if skill_type == 'unknown':
                            skill_type = _identify_skill_type_from_file(agent_file)
                        subagents.append({
                            'agent_id': agent_id,
                            'agent_type': skill_type,
                            'path': agent_file
                        })
        except (json.JSONDecodeError, IOError):
            continue

    if not subagents:
        return []

    # Parse primary transcript to map agent IDs to types
    # Two-pass: first collect Task calls with their tool IDs, then match with results
    pending_tasks = {}  # tool_use_id -> subagent_type
    agent_type_map = {}  # agent_id -> subagent_type

    primary_transcript = CLAUDE_DIR / f"{full_session_id}.jsonl"
    if primary_transcript.exists():
        try:
            with open(primary_transcript, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())

                        # Look for Task tool calls in assistant messages
                        if data.get('type') == 'assistant':
                            message = data.get('message', {})
                            content = message.get('content', [])
                            for block in content:
                                if isinstance(block, dict) and block.get('type') == 'tool_use':
                                    if block.get('name') == 'Task':
                                        inp = block.get('input', {})
                                        subagent_type = inp.get('subagent_type', 'unknown')
                                        tool_id = block.get('id', '')
                                        if tool_id:
                                            pending_tasks[tool_id] = subagent_type

                        # Look for toolUseResult in any message (contains agentId)
                        tool_result = data.get('toolUseResult', {})
                        if tool_result and 'agentId' in tool_result:
                            agent_id = tool_result.get('agentId', '')
                            # Find matching task by sourceToolAssistantUUID
                            source_uuid = data.get('sourceToolAssistantUUID', '')
                            # The tool_use_id is in the message path, try to match
                            # Actually, toolUseResult is at top level with the agentId
                            # We need to look up which task this belongs to

                        # Look at user messages with tool_result
                        if data.get('type') == 'user':
                            message = data.get('message', {})
                            content = message.get('content', [])
                            for block in content:
                                if isinstance(block, dict) and block.get('type') == 'tool_result':
                                    tool_id = block.get('tool_use_id', '')
                                    result_content = block.get('content', [])

                                    # content is a list of {type, text} blocks
                                    if isinstance(result_content, list):
                                        for rc in result_content:
                                            if isinstance(rc, dict) and rc.get('type') == 'text':
                                                text = rc.get('text', '')
                                                if 'agentId:' in text:
                                                    match = re.search(r'agentId:\s*([a-f0-9]+)', text)
                                                    if match:
                                                        agent_id = match.group(1)
                                                        subagent_type = pending_tasks.get(tool_id, 'unknown')
                                                        agent_type_map[agent_id] = subagent_type

                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"  Warning parsing primary transcript: {e}")

    # Update agent types from the type mapping
    # Don't replace subagents list - just update types for existing entries
    for sa in subagents:
        if sa['agent_type'] == 'unknown' and sa['agent_id'] in agent_type_map:
            sa['agent_type'] = agent_type_map[sa['agent_id']]

    return subagents


def extract_execution_trace(filepath: Path, source: str = 'primary',
                           max_thinking_chars: int = 8000,
                           max_tool_result_chars: int = 2000) -> list[dict]:
    """Extract complete execution trace from a transcript file.

    Captures thinking, tool_use, tool_result, and text blocks to show
    the full execution flow: reasoning → action → result → conclusion.

    Args:
        filepath: Path to the JSONL transcript
        source: Agent identifier (e.g., 'primary', 'neo4j-report', 'filtered-data')
        max_thinking_chars: Max chars for thinking blocks
        max_tool_result_chars: Max chars for tool results (typically smaller)

    Returns:
        List of blocks with: timestamp, type, text, length, source, metadata
    """
    blocks = []
    if not filepath.exists():
        return blocks

    # Track tool_use IDs to match with results
    pending_tools = {}  # tool_id -> {name, input, timestamp}

    try:
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    msg_type = data.get('type')
                    timestamp = data.get('timestamp', 'unknown')

                    # Handle assistant messages (thinking, text, tool_use)
                    if msg_type == 'assistant':
                        message = data.get('message', {})
                        content = message.get('content', [])

                        if not isinstance(content, list):
                            continue

                        for block in content:
                            if not isinstance(block, dict):
                                continue

                            block_type = block.get('type')

                            if block_type == 'thinking':
                                text = block.get('thinking', '')
                                original_len = len(text)
                                if len(text) > max_thinking_chars:
                                    text = text[:max_thinking_chars] + f"\n\n... [truncated, {original_len - max_thinking_chars} more chars]"
                                blocks.append({
                                    'timestamp': timestamp,
                                    'type': 'thinking',
                                    'text': text,
                                    'length': original_len,
                                    'source': source
                                })

                            elif block_type == 'tool_use':
                                tool_name = block.get('name', 'unknown')
                                tool_id = block.get('id', '')
                                tool_input = block.get('input', {})

                                # Store for matching with result
                                if tool_id:
                                    pending_tools[tool_id] = {
                                        'name': tool_name,
                                        'input': tool_input,
                                        'timestamp': timestamp
                                    }

                                # Format tool call
                                input_str = _format_tool_input(tool_name, tool_input)
                                blocks.append({
                                    'timestamp': timestamp,
                                    'type': 'tool_use',
                                    'text': f"{tool_name}({input_str})",
                                    'length': len(input_str),
                                    'source': source,
                                    'tool_id': tool_id
                                })

                            elif block_type == 'text':
                                text = block.get('text', '')
                                if text.strip():  # Only include non-empty text
                                    original_len = len(text)
                                    if len(text) > max_thinking_chars:
                                        text = text[:max_thinking_chars] + f"\n\n... [truncated]"
                                    blocks.append({
                                        'timestamp': timestamp,
                                        'type': 'text',
                                        'text': text,
                                        'length': original_len,
                                        'source': source
                                    })

                    # Handle user messages (tool_result)
                    elif msg_type == 'user':
                        message = data.get('message', {})
                        content = message.get('content', [])

                        if not isinstance(content, list):
                            continue

                        for block in content:
                            if not isinstance(block, dict):
                                continue

                            if block.get('type') == 'tool_result':
                                tool_id = block.get('tool_use_id', '')
                                result_content = block.get('content', [])

                                # Get tool name from pending
                                tool_info = pending_tools.get(tool_id, {})
                                tool_name = tool_info.get('name', 'unknown')

                                # Extract result text
                                result_text = _format_tool_result(result_content, max_tool_result_chars)

                                if result_text:
                                    blocks.append({
                                        'timestamp': timestamp,
                                        'type': 'tool_result',
                                        'text': result_text,
                                        'length': len(result_text),
                                        'source': source,
                                        'tool_name': tool_name
                                    })

                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"  Warning reading {filepath}: {e}")

    return blocks


def _format_tool_input(tool_name: str, tool_input: dict) -> str:
    """Format tool input for display, keeping it concise."""
    if not tool_input:
        return ""

    # Special handling for common tools
    if tool_name == 'Skill':
        skill = tool_input.get('skill', '')
        args = tool_input.get('args', '')
        if args:
            return f'"{skill}", args="{args[:100]}..."' if len(args) > 100 else f'"{skill}", args="{args}"'
        return f'"{skill}"'

    if tool_name == 'Task':
        desc = tool_input.get('description', '')
        subagent = tool_input.get('subagent_type', '')
        return f'{subagent}: "{desc}"'

    if tool_name in ('Read', 'Write', 'Edit', 'Glob', 'Grep'):
        # File operations - show path
        path = tool_input.get('file_path', tool_input.get('path', tool_input.get('pattern', '')))
        return f'"{path}"' if path else str(tool_input)[:100]

    if tool_name == 'Bash':
        cmd = tool_input.get('command', '')
        return f'"{cmd[:80]}..."' if len(cmd) > 80 else f'"{cmd}"'

    if 'mcp__neo4j' in tool_name or tool_name == 'mcp__neo4j-cypher__read_neo4j_cypher':
        query = tool_input.get('query', '')
        return f'"{query[:100]}..."' if len(query) > 100 else f'"{query}"'

    # Default: show truncated JSON
    s = json.dumps(tool_input)
    return s[:100] + '...' if len(s) > 100 else s


def _format_tool_result(result_content, max_chars: int) -> str:
    """Format tool result content, handling various formats."""
    if isinstance(result_content, str):
        text = result_content
    elif isinstance(result_content, list):
        # Extract text from content blocks
        texts = []
        for item in result_content:
            if isinstance(item, dict) and item.get('type') == 'text':
                texts.append(item.get('text', ''))
            elif isinstance(item, str):
                texts.append(item)
        text = '\n'.join(texts)
    else:
        text = str(result_content)

    # Truncate if too long
    original_len = len(text)
    if original_len > max_chars:
        text = text[:max_chars] + f"\n... [truncated, {original_len - max_chars} more chars]"

    return text


# Backwards compatibility alias
def extract_thinking_from_file(filepath: Path, source: str = 'primary', max_chars: int = 8000) -> list[dict]:
    """Legacy function - extracts only thinking blocks."""
    all_blocks = extract_execution_trace(filepath, source, max_thinking_chars=max_chars)
    return [b for b in all_blocks if b.get('type') == 'thinking']


def format_relative_time(timestamp: str, session_start: str) -> str:
    """Format timestamp as relative time from session start (e.g., '+02:34').

    Returns MM:SS for times under an hour, HH:MM:SS otherwise.
    """
    from datetime import datetime
    try:
        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        start = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
        delta = ts - start
        total_seconds = int(delta.total_seconds())

        if total_seconds < 0:
            # Before session start (shouldn't happen, but handle gracefully)
            return timestamp[11:19]  # Just return HH:MM:SS

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"+{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"+{minutes:02d}:{seconds:02d}"
    except:
        # Fallback to absolute time if parsing fails
        return timestamp[11:19] if len(timestamp) > 19 else timestamp


def collect_execution_trace(sessions: list[Path], all_subagents: list[dict],
                           include_all_types: bool = True) -> tuple[list[dict], str]:
    """Collect complete execution trace from primary sessions and sub-agents.

    Args:
        sessions: List of primary session transcript paths
        all_subagents: List of sub-agent info dicts
        include_all_types: If True, include all block types; if False, only thinking

    Returns:
        Tuple of (sorted blocks list, session_start timestamp)
    """
    all_blocks = []
    session_start = None

    # Extract from primary sessions
    for session_path in sessions:
        if include_all_types:
            blocks = extract_execution_trace(session_path, source='primary')
        else:
            blocks = extract_thinking_from_file(session_path, source='primary')
        all_blocks.extend(blocks)

        # Track earliest timestamp as session start
        for b in blocks:
            ts = b.get('timestamp', '')
            if ts and (session_start is None or ts < session_start):
                session_start = ts

    # Extract from sub-agents
    for sa in all_subagents:
        agent_type = sa['agent_type']
        agent_path = sa['path']
        if include_all_types:
            blocks = extract_execution_trace(agent_path, source=agent_type)
        else:
            blocks = extract_thinking_from_file(agent_path, source=agent_type)
        all_blocks.extend(blocks)

        # Also check sub-agent timestamps for session start
        for b in blocks:
            ts = b.get('timestamp', '')
            if ts and (session_start is None or ts < session_start):
                session_start = ts

    # Sort all blocks chronologically
    all_blocks.sort(key=lambda x: x.get('timestamp', ''))

    return all_blocks, session_start or ''


# Backwards compatibility alias
def collect_all_thinking_blocks(sessions: list[Path], all_subagents: list[dict]) -> tuple[list[dict], str]:
    """Legacy function - collects only thinking blocks."""
    return collect_execution_trace(sessions, all_subagents, include_all_types=False)


def extract_thinking_from_session(session_id: str, max_chars: int = 8000) -> list[dict]:
    """Extract thinking blocks from a session transcript."""
    if not session_id:
        return []

    # Try to find the transcript file
    transcript_path = CLAUDE_DIR / f"{session_id}.jsonl"
    if not transcript_path.exists():
        # Try partial match
        matches = list(CLAUDE_DIR.glob(f"{session_id}*.jsonl"))
        if matches:
            transcript_path = matches[0]
        else:
            return []

    blocks = []
    try:
        with open(transcript_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('type') != 'assistant':
                        continue

                    message = data.get('message', {})
                    content = message.get('content', [])

                    if not isinstance(content, list):
                        continue

                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'thinking':
                            thinking_text = block.get('thinking', '')
                            timestamp = data.get('timestamp', 'unknown')

                            # Truncate if too long
                            if len(thinking_text) > max_chars:
                                thinking_text = thinking_text[:max_chars] + f"\n\n... [truncated, {len(thinking_text) - max_chars} more chars]"

                            blocks.append({
                                'timestamp': timestamp,
                                'text': thinking_text,
                                'length': len(block.get('thinking', ''))
                            })
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"  Warning: Could not read {transcript_path}: {e}")

    return blocks


def get_session_duration(session_path: Path) -> str:
    """Calculate session duration from first to last timestamp.

    Returns duration as human-readable string like "19m 21s" or "N/A".
    """
    from datetime import datetime

    if not session_path.exists():
        return "N/A"

    try:
        first_ts = None
        last_ts = None

        with open(session_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    ts = data.get('timestamp')
                    if ts:
                        if first_ts is None:
                            first_ts = ts
                        last_ts = ts
                except:
                    continue

        if not first_ts or not last_ts:
            return "N/A"

        # Parse ISO timestamps
        start = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
        end = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))

        duration = end - start
        total_seconds = int(duration.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    except Exception as e:
        return "N/A"


def get_prediction_data(accession_no: str) -> dict:
    """Get prediction/actual data from predictions.csv."""
    if not PREDICTIONS_CSV.exists():
        return {}

    try:
        with open(PREDICTIONS_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('accession_no') == accession_no:
                    return {
                        'ticker': row.get('ticker', ''),
                        'filing_datetime': row.get('filing_datetime', ''),
                        'predicted_direction': row.get('predicted_direction', ''),
                        'predicted_magnitude': row.get('predicted_magnitude', ''),
                        'confidence': row.get('confidence', ''),
                        'primary_reason': row.get('primary_reason', ''),
                        'actual_direction': row.get('actual_direction', ''),
                        'actual_magnitude': row.get('actual_magnitude', ''),
                        'actual_return': row.get('actual_return', ''),
                        'correct': row.get('correct', ''),
                    }
    except Exception as e:
        print(f"  Warning: Could not read predictions.csv: {e}")

    return {}


def get_attribution_metadata(accession_no: str, ticker: str) -> dict:
    """Get metadata from attribution report if it exists."""
    if not ticker:
        return {}

    report_path = COMPANIES_DIR / ticker / f"{accession_no}.md"
    if not report_path.exists():
        return {}

    metadata = {}
    try:
        with open(report_path, 'r') as f:
            content = f.read()

            # Extract key fields from the report
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'Primary Driver' in line and ':' in line:
                    metadata['primary_driver'] = line.split(':', 1)[1].strip()
                elif 'Confidence' in line and ':' in line:
                    metadata['confidence'] = line.split(':', 1)[1].strip()
                elif 'daily_stock' in line.lower() and '%' in line:
                    # Try to extract return percentage
                    import re
                    match = re.search(r'([+-]?\d+\.?\d*)%', line)
                    if match:
                        metadata['return_pct'] = match.group(1) + '%'
    except Exception as e:
        print(f"  Warning: Could not parse {report_path}: {e}")

    return metadata


def load_history_csv(skill_filter: str = None) -> list[dict]:
    """
    Load history from shared CSV.
    Args:
        skill_filter: Optional filter for 'prediction' or 'attribution'. None = all.
    Returns:
        List of row dicts with 'primary' entries (unique sessions).
    """
    if not SHARED_HISTORY_CSV.exists():
        return []

    rows = []
    try:
        with open(SHARED_HISTORY_CSV, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Filter by skill if specified
                if skill_filter and row.get('skill') != skill_filter:
                    continue
                # Only return 'primary' entries (one per session)
                if row.get('agent_type') != 'primary':
                    continue
                # Map skill column to _skill_type for compatibility
                row['_skill_type'] = row.get('skill', '')
                row['updated_at'] = row.get('created_at', '')
                rows.append(row)
    except Exception as e:
        print(f"  Warning: Could not read {SHARED_HISTORY_CSV}: {e}")

    return rows


def generate_combined_thinking(accession_no: str, row: dict, metadata: dict) -> str:
    """Generate combined markdown file for one accession."""
    ticker = metadata.get('ticker', 'UNKNOWN')
    skill_type = row.get('_skill_type', 'unknown')
    filing_date = metadata.get('filing_datetime', row.get('updated_at', ''))[:10]

    lines = [
        f"# Thinking: {ticker} {accession_no}",
        "",
        f"**Filing Date**: {filing_date}  ",
        f"**Skill**: {skill_type}  ",
    ]

    # Add metadata
    if metadata.get('return_pct') or metadata.get('actual_return'):
        ret = metadata.get('return_pct') or metadata.get('actual_return', '')
        lines.append(f"**Return**: {ret}  ")

    if metadata.get('primary_driver') or metadata.get('primary_reason'):
        driver = metadata.get('primary_driver') or metadata.get('primary_reason', '')
        lines.append(f"**Primary Driver**: {driver}  ")

    if metadata.get('confidence'):
        lines.append(f"**Confidence**: {metadata['confidence']}  ")

    if metadata.get('predicted_direction'):
        lines.append(f"**Predicted**: {metadata['predicted_direction']} ({metadata.get('predicted_magnitude', '')})  ")

    if metadata.get('actual_direction'):
        correct = metadata.get('correct', '')
        correct_emoji = "✓" if correct.upper() == 'TRUE' else "✗" if correct else ""
        lines.append(f"**Actual**: {metadata['actual_direction']} {correct_emoji}  ")

    # Find sessions by content search (reliable - doesn't depend on CSV session ID)
    sessions = find_sessions_for_accession(accession_no)
    all_subagents = []
    total_duration_str = "N/A"

    # Calculate total duration from primary session(s)
    if sessions:
        durations = [get_session_duration(s) for s in sessions]
        # Use the first session's duration as the primary duration
        total_duration_str = durations[0] if durations else "N/A"

    lines.append(f"**Duration**: {total_duration_str}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Collect sub-agents from all sessions first
    if sessions:
        for session_path in sessions:
            session_id = session_path.stem
            subagents = discover_subagents(session_id)
            all_subagents.extend(subagents)

    if sessions:
        # Collect complete execution trace from primary + sub-agents
        all_blocks, session_start = collect_execution_trace(sessions, all_subagents, include_all_types=True)

        if all_blocks:
            # Show session info
            session_ids = [s.stem[:8] for s in sessions]
            lines.append(f"## Execution Timeline")
            lines.append(f"Sessions: {', '.join(f'`{sid}`' for sid in session_ids)}")

            # Count blocks by type and source for summary
            type_counts = {}
            source_counts = {}
            for b in all_blocks:
                btype = b.get('type', 'unknown')
                src = b.get('source', 'unknown')
                type_counts[btype] = type_counts.get(btype, 0) + 1
                source_counts[src] = source_counts.get(src, 0) + 1

            type_summary = ', '.join(f"{k}: {v}" for k, v in sorted(type_counts.items()))
            source_summary = ', '.join(f"{k}: {v}" for k, v in sorted(source_counts.items()))
            lines.append(f"Total: {len(all_blocks)} blocks ({type_summary})")
            lines.append(f"Sources: {source_summary}")
            lines.append("")

            # Type emoji mapping
            type_emoji = {
                'thinking': '💭',
                'tool_use': '🔧',
                'tool_result': '📊',
                'text': '📝'
            }

            # Output all blocks in chronological order with type-specific formatting
            for i, block in enumerate(all_blocks, 1):
                source = block.get('source', 'unknown')
                timestamp = block.get('timestamp', '')
                rel_time = format_relative_time(timestamp, session_start)
                block_type = block.get('type', 'unknown')
                emoji = type_emoji.get(block_type, '❓')
                length = block.get('length', 0)

                # Format: ### #15 · 💭 · neo4j-report · +02:34
                lines.append(f"### #{i} · {emoji} · {source} · {rel_time}")

                if block_type == 'tool_result':
                    # Use collapsible block for tool results
                    tool_name = block.get('tool_name', 'unknown')
                    lines.append(f"<details><summary>{tool_name} result ({length} chars)</summary>")
                    lines.append("")
                    lines.append("```")
                    lines.append(block['text'])
                    lines.append("```")
                    lines.append("</details>")
                elif block_type == 'tool_use':
                    # Tool calls on single line, code-formatted
                    lines.append(f"```")
                    lines.append(block['text'])
                    lines.append("```")
                else:
                    # thinking and text - show as regular markdown
                    lines.append(f"*{length} chars*")
                    lines.append("")
                    lines.append(block['text'])

                lines.append("")
        else:
            lines.append("*No execution trace found*")
            lines.append("")
    else:
        lines.append("*No sessions found for this accession*")
        lines.append("")

    # Summary of agents involved
    if all_subagents:
        types = sorted(set(sa['agent_type'] for sa in all_subagents))
        lines.append("---")
        lines.append("")
        lines.append(f"*Agents: primary + {len(all_subagents)} sub-agents ({', '.join(types)})*")
        lines.append("")

    return '\n'.join(lines)


def build_index(all_runs: list[dict]) -> str:
    """Build master index.md with table of all runs."""
    lines = [
        "# Thinking Index",
        "",
        "Extracted thinking tokens from earnings prediction and attribution runs.",
        "",
        "| Accession | Ticker | Date | Skill | Duration | Return | Correct | Primary | Sub-Agents | View |",
        "|-----------|--------|------|-------|----------|--------|---------|---------|------------|------|",
    ]

    for run in sorted(all_runs, key=lambda x: x.get('updated_at', ''), reverse=True):
        accession = run.get('accession_no', '')
        ticker = run.get('ticker', '')
        date = run.get('filing_datetime', run.get('updated_at', ''))[:10]
        skill = run.get('_skill_type', '')
        ret = run.get('return_pct', run.get('actual_return', ''))
        correct = run.get('correct', '')
        if correct:
            correct = '✓' if correct.upper() == 'TRUE' else '✗'

        # Find sessions by content search
        sessions = find_sessions_for_accession(accession)
        primary = sessions[0].stem[:8] if sessions else '-'

        # Calculate duration from primary session
        duration = get_session_duration(sessions[0]) if sessions else '-'

        # Discover sub-agents from all found sessions
        all_subagents = []
        for s in sessions:
            all_subagents.extend(discover_subagents(s.stem))
        if all_subagents:
            types = sorted(set(sa['agent_type'] for sa in all_subagents))
            subagent_summary = ', '.join(types)
        else:
            subagent_summary = '-'

        # Standard markdown link (works in Obsidian)
        link = f"[View](runs/{accession}.md)"

        lines.append(f"| {accession} | {ticker} | {date} | {skill} | {duration} | {ret} | {correct} | {primary} | {subagent_summary} | {link} |")

    lines.append("")
    lines.append(f"*Generated: {datetime.now().isoformat()}*")

    return '\n'.join(lines)


def build_for_accession(accession_no: str) -> bool:
    """Build thinking file for a single accession (called from skills)."""
    # Find the row in history CSV (most recent for this accession)
    row = None
    for r in load_history_csv():
        if r.get('accession_no') == accession_no:
            # Keep the most recent one
            if not row or r.get('updated_at', '') > row.get('updated_at', ''):
                row = r

    if not row:
        print(f"No history found for {accession_no}")
        return False

    # Get metadata
    pred_data = get_prediction_data(accession_no)
    ticker = pred_data.get('ticker', '')
    attr_data = get_attribution_metadata(accession_no, ticker)

    metadata = {**pred_data, **attr_data}

    # Ensure directories exist
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate and save combined thinking
    content = generate_combined_thinking(accession_no, row, metadata)
    output_path = RUNS_DIR / f"{accession_no}.md"

    with open(output_path, 'w') as f:
        f.write(content)

    print(f"Saved: {output_path}")

    # Rebuild index
    rebuild_index()

    return True


def rebuild_index():
    """Rebuild the master index from shared history CSV."""
    all_runs = []

    # Load all history rows (primary entries only)
    for row in load_history_csv():
        accession = row.get('accession_no', '')
        if not accession:
            continue

        # Get metadata
        pred_data = get_prediction_data(accession)
        ticker = pred_data.get('ticker', '')
        attr_data = get_attribution_metadata(accession, ticker)

        combined = {**row, **pred_data, **attr_data}
        all_runs.append(combined)

    # Deduplicate by accession (keep most recent)
    seen = {}
    for run in all_runs:
        acc = run.get('accession_no', '')
        if acc not in seen or run.get('updated_at', '') > seen[acc].get('updated_at', ''):
            seen[acc] = run

    # Build and save index
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    index_content = build_index(list(seen.values()))
    index_path = OUTPUT_DIR / "index.md"

    with open(index_path, 'w') as f:
        f.write(index_content)

    print(f"Index saved: {index_path}")


def build_all():
    """Build thinking files for all accessions in history."""
    # Load all history rows (primary entries only)
    all_rows = load_history_csv()

    # Deduplicate by accession (keep most recent)
    seen = {}
    for row in all_rows:
        acc = row.get('accession_no', '')
        if acc and (acc not in seen or row.get('updated_at', '') > seen[acc].get('updated_at', '')):
            seen[acc] = row

    print(f"Found {len(seen)} unique accessions")

    # Ensure directories exist
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    # Process each
    for accession, row in seen.items():
        print(f"\nProcessing: {accession}")

        pred_data = get_prediction_data(accession)
        ticker = pred_data.get('ticker', '')
        attr_data = get_attribution_metadata(accession, ticker)

        metadata = {**pred_data, **attr_data}

        content = generate_combined_thinking(accession, row, metadata)
        output_path = RUNS_DIR / f"{accession}.md"

        with open(output_path, 'w') as f:
            f.write(content)

        print(f"  Saved: {output_path}")

    # Build index
    rebuild_index()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python3 build-thinking-index.py all              # Build all from history")
        print("  python3 build-thinking-index.py <accession>      # Build for single accession")
        print("  python3 build-thinking-index.py index            # Rebuild index only")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'all':
        build_all()
    elif cmd == 'index':
        rebuild_index()
    else:
        # Assume it's an accession number
        build_for_accession(cmd)


if __name__ == "__main__":
    main()
