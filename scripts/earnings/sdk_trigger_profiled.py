#!/usr/bin/env python3
"""
SDK Trigger with Timing Profiler
================================
Usage:
    python scripts/earnings/sdk_trigger_profiled.py AAPL 2
    python scripts/earnings/sdk_trigger_profiled.py NVDA
"""
import asyncio
import sys
import os
import time
from datetime import datetime
from collections import defaultdict
from typing import Dict, Optional

os.chdir("/home/faisal/EventMarketDB")
from claude_agent_sdk import query, ClaudeAgentOptions

TIMING_DIR = "earnings-analysis/orchestrator-timing"

# === Profiler (inline) ===
class _Node:
    def __init__(self, name):
        self.name, self.t0, self.t1 = name, time.perf_counter(), None
    def stop(self): self.t1 = time.perf_counter()
    @property
    def elapsed(self): return (self.t1 or time.perf_counter()) - self.t0

class Profiler:
    C = type('C', (), {'R':'\033[91m','Y':'\033[93m','G':'\033[92m','B':'\033[94m','X':'\033[1m','D':'\033[2m','_':'\033[0m'})()

    def __init__(self, name):
        self.name = name
        self.t0 = time.perf_counter()
        self.nodes: list[_Node] = []
        self._active: Dict[str, _Node] = {}
        self._counts: Dict[str, int] = defaultdict(int)

    def track(self, msg) -> Optional[str]:
        if hasattr(msg, 'content'):
            for b in msg.content:
                if hasattr(b, 'name'):
                    tid = getattr(b, 'id', str(time.time()))
                    inp = getattr(b, 'input', {})
                    self._counts[b.name] += 1
                    if b.name == 'Task':
                        label = f"🤖 {inp.get('subagent_type','agent')}: {inp.get('description','')[:35]}"
                    elif b.name == 'Skill':
                        label = f"⚡ {inp.get('skill','skill')}"
                    elif b.name == 'Bash':
                        label = f"$ {inp.get('command','')[:40]}..."
                    else:
                        label = f"🔧 {b.name}"
                    node = _Node(label)
                    self.nodes.append(node)
                    self._active[tid] = node
                    return b.name
        if hasattr(msg, 'tool_use_id') and msg.tool_use_id in self._active:
            self._active.pop(msg.tool_use_id).stop()
            return 'done'
        if hasattr(msg, 'result'):
            return 'complete'

    def report(self, save_path: str = None):
        total = time.perf_counter() - self.t0
        C = self.C
        fmt = lambda e: f"{e*1000:.0f}ms" if e<1 else f"{e:.1f}s" if e<60 else f"{int(e//60)}m{int(e%60)}s"
        lines = []

        lines.append(f"{'═'*64}")
        lines.append(f"  {self.name}  [{fmt(total)}]")
        lines.append(f"{'═'*64}\n")

        # Group by start time (parallel = within 0.5s)
        nodes = sorted(self.nodes, key=lambda n: n.t0)
        groups, cur, last = [], [], 0
        for n in nodes:
            if cur and (n.t0 - last) > 0.5:
                groups.append(cur); cur = []
            cur.append(n); last = n.t0
        if cur: groups.append(cur)

        for g in groups:
            if len(g) > 1:
                wall = max(n.t1 or time.perf_counter() for n in g) - min(n.t0 for n in g)
                lines.append(f"  ┌─ Parallel ({len(g)} tasks, wall: {fmt(wall)})")
            for i, n in enumerate(g):
                pre = "  │ └── " if len(g)>1 and i==len(g)-1 else "  │ ├── " if len(g)>1 else "  "
                lines.append(f"{pre}{n.name[:45]}  {fmt(n.elapsed):>8}")
            if len(g) > 1:
                lines.append(f"  └─")
            lines.append("")

        lines.append(f"{'─'*64}")
        lines.append(f"  Tools: " + ", ".join(f"{k}={v}" for k,v in sorted(self._counts.items())))
        cpu = sum(n.elapsed for n in self.nodes)
        if total > 0:
            lines.append(f"  Parallelism: {cpu/total:.1f}x (CPU: {fmt(cpu)}, Wall: {fmt(total)})")

        # Print with colors
        for line in lines:
            if '═' in line: print(f"{C.X}{line}{C._}")
            elif '┌─' in line or '└─' in line: print(f"{C.B}{line}{C._}")
            else: print(line)

        # Save to file
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'w') as f:
                f.write('\n'.join(lines))
            print(f"\n  {C.G}Saved: {save_path}{C._}")


# === Main ===
async def run(ticker: str, sigma: str = "2"):
    start_time = datetime.now()
    profiler = Profiler(f"earnings-orchestrator {ticker} {sigma}")

    async for msg in query(
        prompt=f"Run /earnings-orchestrator {ticker} {sigma}",
        options=ClaudeAgentOptions(
            setting_sources=["project"],
            permission_mode="bypassPermissions",
            max_turns=50,
        )
    ):
        event = profiler.track(msg)
        if event and event not in ('done', 'complete'):
            print(f"  → {event}", flush=True)
        if hasattr(msg, 'result'):
            print(msg.result[-2000:])

    # Save: {TICKER}_{DATE}_{HH-MM-SS}_{SIGMA}sigma.txt
    filename = f"{ticker}_{start_time.strftime('%Y-%m-%d_%H-%M-%S')}_{sigma}sigma.txt"
    profiler.report(save_path=f"{TIMING_DIR}/{filename}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sdk_trigger_profiled.py TICKER [SIGMA]")
        sys.exit(1)
    asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "2"))
